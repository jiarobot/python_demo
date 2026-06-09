import numpy as np
import cv2
import pandas as pd
from scipy import ndimage
from scipy.spatial import distance
from scipy.optimize import linear_sum_assignment
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler
import matplotlib
matplotlib.rc("font", family='Microsoft YaHei')
import matplotlib.pyplot as plt
from collections import deque, defaultdict
import json
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

class SpatioTemporalCounter:
    """
    基于多模态特征融合的密集人群动态计数系统
    """
    
    def __init__(self, config_path=None):
        # 初始化参数
        self.config = {
            'temporal_window': 30,  # 时间窗口大小
            'spatial_cluster_eps': 50,  # 空间聚类参数
            'motion_threshold': 0.1,  # 运动检测阈值
            'density_estimation_radius': 100,  # 密度估计半径
            'tracking_max_distance': 80,  # 跟踪最大距离
            'feature_fusion_weights': {  # 特征融合权重
                'optical_flow': 0.3,
                'texture_density': 0.25,
                'motion_consistency': 0.25,
                'spatial_distribution': 0.2
            }
        }
        
        # 状态变量
        self.frame_buffer = deque(maxlen=self.config['temporal_window'])
        self.tracks = {}
        self.next_track_id = 0
        self.counting_regions = {}
        self.historical_counts = deque(maxlen=1000)
        self.feature_vectors = []
        
        # 加载预计算模型（如果有）
        if config_path:
            self.load_config(config_path)
    
    def load_config(self, config_path):
        """加载配置文件"""
        try:
            with open(config_path, 'r') as f:
                saved_config = json.load(f)
                self.config.update(saved_config)
        except:
            print("使用默认配置")
    
    def multi_scale_feature_extraction(self, frame):
        """
        多尺度特征提取
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        features = {}
        
        # 1. 多尺度梯度特征
        scales = [1, 2, 4]
        gradient_maps = []
        for scale in scales:
            resized = cv2.resize(gray, 
                               (gray.shape[1]//scale, gray.shape[0]//scale))
            grad_x = cv2.Sobel(resized, cv2.CV_32F, 1, 0, ksize=3)
            grad_y = cv2.Sobel(resized, cv2.CV_32F, 0, 1, ksize=3)
            magnitude = cv2.resize(np.sqrt(grad_x**2 + grad_y**2), 
                                 (gray.shape[1], gray.shape[0]))
            gradient_maps.append(magnitude)
        
        features['multi_scale_gradient'] = np.mean(gradient_maps, axis=0)
        
        # 2. 纹理密度特征
        lbp = self.local_binary_pattern(gray)
        features['texture_density'] = self.compute_texture_density(lbp)
        
        # 3. 频域特征
        fft = np.fft.fft2(gray)
        fft_shift = np.fft.fftshift(fft)
        magnitude_spectrum = np.log(np.abs(fft_shift) + 1)
        features['frequency_domain'] = magnitude_spectrum
        
        return features
    
    def local_binary_pattern(self, image, radius=3, neighbors=24):
        """
        计算局部二值模式纹理特征
        """
        height, width = image.shape
        lbp_image = np.zeros_like(image, dtype=np.float32)
        
        for y in range(radius, height-radius):
            for x in range(radius, width-radius):
                center = image[y, x]
                binary_pattern = 0
                
                # 圆形邻域采样
                for i in range(neighbors):
                    angle = 2 * np.pi * i / neighbors
                    x_offset = int(x + radius * np.cos(angle))
                    y_offset = int(y - radius * np.sin(angle))
                    
                    if (0 <= x_offset < width and 0 <= y_offset < height):
                        neighbor = image[y_offset, x_offset]
                        if neighbor >= center:
                            binary_pattern |= (1 << i)
                
                lbp_image[y, x] = binary_pattern
        
        return lbp_image
    
    def compute_texture_density(self, lbp_image):
        """
        基于纹理特征计算密度
        """
        # 计算纹理复杂度作为密度指标
        kernel = np.ones((15, 15), np.float32) / 225
        texture_density = cv2.filter2D(lbp_image.astype(np.float32), -1, kernel)
        return texture_density
    
    def optical_flow_analysis(self, prev_frame, current_frame):
        """
        改进的光流分析 - 结合多尺度金字塔
        """
        prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
        curr_gray = cv2.cvtColor(current_frame, cv2.COLOR_BGR2GRAY)
        
        # 多尺度光流计算
        flow = cv2.calcOpticalFlowFarneback(
            prev_gray, curr_gray, None,
            pyr_scale=0.5, levels=3, winsize=15,
            iterations=3, poly_n=5, poly_sigma=1.2, flags=0
        )
        
        # 计算运动一致性
        magnitude, angle = cv2.cartToPolar(flow[..., 0], flow[..., 1])
        motion_consistency = self.compute_motion_consistency(flow, magnitude)
        
        return {
            'flow': flow,
            'magnitude': magnitude,
            'angle': angle,
            'consistency': motion_consistency
        }
    
    def compute_motion_consistency(self, flow, magnitude):
        """
        计算运动一致性特征
        """
        # 使用局部运动方向方差作为一致性度量
        flow_x, flow_y = flow[..., 0], flow[..., 1]
        
        # 计算局部方向方差
        kernel_size = 7
        kernel = np.ones((kernel_size, kernel_size))
        
        # 局部方向统计
        local_mean_x = ndimage.convolve(flow_x, kernel) / (kernel_size**2)
        local_mean_y = ndimage.convolve(flow_y, kernel) / (kernel_size**2)
        
        local_var_x = ndimage.convolve((flow_x - local_mean_x)**2, kernel)
        local_var_y = ndimage.convolve((flow_y - local_mean_y)**2, kernel)
        
        motion_consistency = 1 / (1 + np.sqrt(local_var_x + local_var_y))
        return motion_consistency
    
    def spatiotemporal_clustering(self, features, optical_flow):
        """
        时空聚类分析
        """
        height, width = features['multi_scale_gradient'].shape
        points = []
        feature_descriptors = []
        
        # 生成候选点
        grid_size = 8
        for y in range(0, height, grid_size):
            for x in range(0, width, grid_size):
                if (features['multi_scale_gradient'][y, x] > self.config['motion_threshold'] and
                    features['texture_density'][y, x] > np.mean(features['texture_density'])):
                    
                    # 创建特征描述符
                    descriptor = [
                        features['multi_scale_gradient'][y, x],
                        features['texture_density'][y, x],
                        optical_flow['magnitude'][y, x],
                        optical_flow['consistency'][y, x],
                        x / width,  # 归一化位置
                        y / height
                    ]
                    
                    points.append([x, y])
                    feature_descriptors.append(descriptor)
        
        if len(points) < 2:
            return [], []
        
        # 基于多特征聚类
        feature_array = np.array(feature_descriptors)
        scaler = StandardScaler()
        features_normalized = scaler.fit_transform(feature_array)
        
        # DBSCAN聚类
        clustering = DBSCAN(
            eps=self.config['spatial_cluster_eps']/1000,  # 归一化距离
            min_samples=3
        ).fit(features_normalized)
        
        clusters = []
        for cluster_id in set(clustering.labels_):
            if cluster_id != -1:  # 忽略噪声点
                cluster_points = np.array(points)[clustering.labels_ == cluster_id]
                if len(cluster_points) > 0:
                    centroid = np.mean(cluster_points, axis=0)
                    clusters.append({
                        'centroid': centroid,
                        'points': cluster_points,
                        'size': len(cluster_points),
                        'cluster_id': cluster_id
                    })
        
        return clusters, points
    
    def multi_feature_fusion_counting(self, clusters, features, optical_flow):
        """
        多特征融合计数算法
        """
        if not clusters:
            return 0
        
        region_counts = []
        
        for cluster in clusters:
            centroid = cluster['centroid']
            x, y = int(centroid[0]), int(centroid[1])
            
            # 1. 基于光流的运动特征
            flow_magnitude = optical_flow['magnitude'][y, x] if y < optical_flow['magnitude'].shape[0] and x < optical_flow['magnitude'].shape[1] else 0
            
            # 2. 基于纹理的密度特征
            texture_density = features['texture_density'][y, x]
            
            # 3. 运动一致性特征
            motion_consistency = optical_flow['consistency'][y, x] if y < optical_flow['consistency'].shape[0] and x < optical_flow['consistency'].shape[1] else 0
            
            # 4. 空间分布特征
            spatial_density = cluster['size'] / (len(clusters) + 1e-6)
            
            # 特征融合
            weights = self.config['feature_fusion_weights']
            fused_score = (
                weights['optical_flow'] * flow_magnitude +
                weights['texture_density'] * texture_density +
                weights['motion_consistency'] * motion_consistency +
                weights['spatial_distribution'] * spatial_density
            )
            
            # 自适应计数估计
            base_count = max(1, cluster['size'] // 5)
            adjusted_count = base_count * (1 + fused_score)
            
            region_counts.append(adjusted_count)
        
        # 使用稳健统计方法过滤异常值
        if region_counts:
            counts_array = np.array(region_counts)
            Q1 = np.percentile(counts_array, 25)
            Q3 = np.percentile(counts_array, 75)
            IQR = Q3 - Q1
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR
            
            filtered_counts = counts_array[
                (counts_array >= lower_bound) & (counts_array <= upper_bound)
            ]
            
            total_count = int(np.sum(filtered_counts))
        else:
            total_count = 0
        
        return total_count
    
    def update_tracking(self, clusters, current_frame):
        """
        多目标跟踪更新
        """
        current_centroids = [cluster['centroid'] for cluster in clusters]
        
        if not self.tracks:
            # 初始化跟踪
            for centroid in current_centroids:
                self.tracks[self.next_track_id] = {
                    'centroid': centroid,
                    'path': [centroid],
                    'lost_count': 0,
                    'active': True
                }
                self.next_track_id += 1
            return
        
        # 计算成本矩阵进行数据关联
        track_ids = list(self.tracks.keys())
        current_points = np.array(current_centroids)
        
        if len(current_points) == 0:
            # 没有检测到目标，增加丢失计数
            for track_id in track_ids:
                self.tracks[track_id]['lost_count'] += 1
            return
        
        cost_matrix = np.zeros((len(track_ids), len(current_points)))
        
        for i, track_id in enumerate(track_ids):
            track_centroid = self.tracks[track_id]['centroid']
            for j, current_point in enumerate(current_points):
                cost_matrix[i, j] = distance.euclidean(track_centroid, current_point)
        
        # 使用匈牙利算法进行匹配
        row_ind, col_ind = linear_sum_assignment(cost_matrix)
        
        matched_tracks = set()
        matched_detections = set()
        
        # 处理匹配
        for i, j in zip(row_ind, col_ind):
            if cost_matrix[i, j] < self.config['tracking_max_distance']:
                track_id = track_ids[i]
                self.tracks[track_id]['centroid'] = current_points[j]
                self.tracks[track_id]['path'].append(current_points[j])
                self.tracks[track_id]['lost_count'] = 0
                matched_tracks.add(track_id)
                matched_detections.add(j)
        
        # 处理未匹配的跟踪
        for i, track_id in enumerate(track_ids):
            if track_id not in matched_tracks:
                self.tracks[track_id]['lost_count'] += 1
        
        # 创建新跟踪
        for j in range(len(current_points)):
            if j not in matched_detections:
                self.tracks[self.next_track_id] = {
                    'centroid': current_points[j],
                    'path': [current_points[j]],
                    'lost_count': 0,
                    'active': True
                }
                self.next_track_id += 1
        
        # 清理丢失的跟踪
        tracks_to_remove = []
        for track_id, track in self.tracks.items():
            if track['lost_count'] > 10:  # 连续10帧丢失
                tracks_to_remove.append(track_id)
        
        for track_id in tracks_to_remove:
            del self.tracks[track_id]
    
    def process_frame(self, frame, frame_count):
        """
        处理单帧图像
        """
        self.frame_buffer.append(frame.copy())
        
        if len(self.frame_buffer) < 2:
            return 0, {}
        
        # 特征提取
        features = self.multi_scale_feature_extraction(frame)
        
        # 光流分析
        optical_flow = self.optical_flow_analysis(self.frame_buffer[-2], frame)
        
        # 时空聚类
        clusters, interest_points = self.spatiotemporal_clustering(features, optical_flow)
        
        # 多特征融合计数
        count = self.multi_feature_fusion_counting(clusters, features, optical_flow)
        
        # 更新跟踪
        self.update_tracking(clusters, frame)
        
        # 记录历史数据
        timestamp = datetime.now()
        self.historical_counts.append({
            'timestamp': timestamp,
            'count': count,
            'frame_count': frame_count,
            'active_tracks': len(self.tracks)
        })
        
        results = {
            'count': count,
            'clusters': clusters,
            'interest_points': interest_points,
            'optical_flow': optical_flow,
            'active_tracks': len(self.tracks),
            'features': features
        }
        
        return count, results
    
    def visualize_results(self, frame, results, display=True):
        """
        可视化结果
        """
        vis_frame = frame.copy()
        
        # 绘制兴趣点
        for point in results.get('interest_points', []):
            cv2.circle(vis_frame, (int(point[0]), int(point[1])), 
                      2, (0, 255, 255), -1)
        
        # 绘制聚类中心
        for cluster in results.get('clusters', []):
            centroid = cluster['centroid']
            cv2.circle(vis_frame, (int(centroid[0]), int(centroid[1])), 
                      8, (0, 0, 255), -1)
            cv2.putText(vis_frame, f"{cluster['size']}", 
                       (int(centroid[0])+10, int(centroid[1])), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # 绘制跟踪轨迹
        for track_id, track in self.tracks.items():
            if len(track['path']) > 1:
                points = np.array(track['path'], dtype=np.int32)
                cv2.polylines(vis_frame, [points], False, (255, 0, 0), 2)
            
            current_pos = track['centroid']
            cv2.putText(vis_frame, str(track_id), 
                       (int(current_pos[0]), int(current_pos[1])-10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        
        # 显示计数结果
        count = results.get('count', 0)
        cv2.putText(vis_frame, f"Count: {count}", (20, 40), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
        cv2.putText(vis_frame, f"Tracks: {len(self.tracks)}", (20, 80), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
        
        if display:
            cv2.imshow('Spatio-Temporal Counting', vis_frame)
        
        return vis_frame
    
    def get_statistical_analysis(self):
        """
        获取统计分析结果
        """
        if not self.historical_counts:
            return {}
        
        counts = [data['count'] for data in self.historical_counts]
        
        analysis = {
            'mean_count': np.mean(counts),
            'median_count': np.median(counts),
            'std_count': np.std(counts),
            'min_count': np.min(counts),
            'max_count': np.max(counts),
            'total_frames': len(self.historical_counts),
            'trend': self.compute_trend(counts),
            'peak_hours': self.analyze_peak_patterns()
        }
        
        return analysis
    
    def compute_trend(self, counts):
        """
        计算人数变化趋势
        """
        if len(counts) < 2:
            return "stable"
        
        x = np.arange(len(counts))
        slope = np.polyfit(x, counts, 1)[0]
        
        if slope > 0.1:
            return "increasing"
        elif slope < -0.1:
            return "decreasing"
        else:
            return "stable"
    
    def analyze_peak_patterns(self):
        """
        分析峰值模式
        """
        if not self.historical_counts:
            return {}
        
        # 简单的峰值检测
        counts = [data['count'] for data in self.historical_counts]
        mean_count = np.mean(counts)
        std_count = np.std(counts)
        
        peaks = [i for i, count in enumerate(counts) 
                if count > mean_count + std_count]
        
        return {
            'peak_count': len(peaks),
            'peak_ratio': len(peaks) / len(counts),
            'average_peak_value': np.mean([counts[i] for i in peaks]) if peaks else 0
        }

# 使用示例和测试代码
def main():
    """
    主函数 - 演示系统使用
    """
    # 初始化计数器
    counter = SpatioTemporalCounter()
    
    # 测试视频文件或摄像头
    video_source = 0  # 0 表示默认摄像头，或提供视频文件路径
    
    cap = cv2.VideoCapture(video_source)
    
    if not cap.isOpened():
        print("无法打开视频源")
        return
    
    frame_count = 0
    counting_data = []
    
    print("开始时空计数分析...")
    print("按 'q' 退出，按 's' 保存统计结果")
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # 处理帧
            count, results = counter.process_frame(frame, frame_count)
            
            # 可视化结果
            vis_frame = counter.visualize_results(frame, results)
            
            # 记录数据
            counting_data.append({
                'frame': frame_count,
                'count': count,
                'timestamp': datetime.now()
            })
            
            frame_count += 1
            
            # 显示帧率
            cv2.putText(vis_frame, f"Frame: {frame_count}", 
                       (20, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
            
            cv2.imshow('Spatio-Temporal Counting', vis_frame)
            
            # 键盘控制
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('s'):
                # 保存统计结果
                analysis = counter.get_statistical_analysis()
                print("\n=== 统计分析结果 ===")
                for key, value in analysis.items():
                    print(f"{key}: {value}")
                
                # 保存到文件
                df = pd.DataFrame(counting_data)
                df.to_csv(f'counting_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv', index=False)
                print("结果已保存到CSV文件")
    
    except KeyboardInterrupt:
        print("程序被用户中断")
    
    finally:
        cap.release()
        cv2.destroyAllWindows()
        
        # 最终统计分析
        if counting_data:
            analysis = counter.get_statistical_analysis()
            print("\n=== 最终统计分析 ===")
            for key, value in analysis.items():
                print(f"{key}: {value}")
            
            # 绘制统计图表
            plt.figure(figsize=(12, 8))
            
            plt.subplot(2, 2, 1)
            counts = [data['count'] for data in counting_data]
            plt.plot(counts)
            plt.title('人数变化趋势')
            plt.xlabel('帧数')
            plt.ylabel('人数')
            
            plt.subplot(2, 2, 2)
            plt.hist(counts, bins=20, alpha=0.7, edgecolor='black')
            plt.title('人数分布直方图')
            plt.xlabel('人数')
            plt.ylabel('频率')
            
            plt.subplot(2, 2, 3)
            # 移动平均平滑
            window_size = 30
            moving_avg = pd.Series(counts).rolling(window=window_size).mean()
            plt.plot(moving_avg)
            plt.title(f'{window_size}帧移动平均')
            plt.xlabel('帧数')
            plt.ylabel('平均人数')
            
            plt.subplot(2, 2, 4)
            # 累积分布
            sorted_counts = np.sort(counts)
            cdf = np.arange(1, len(sorted_counts)+1) / len(sorted_counts)
            plt.plot(sorted_counts, cdf)
            plt.title('累积分布函数')
            plt.xlabel('人数')
            plt.ylabel('CDF')
            
            plt.tight_layout()
            plt.savefig('counting_analysis.png', dpi=300, bbox_inches='tight')
            plt.show()

if __name__ == "__main__":
    main()