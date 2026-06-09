import cv2
import numpy as np
import argparse
import time
import threading
from collections import deque, defaultdict
import json
import os
from datetime import datetime

class RobustMotionDetector:
    def __init__(self, use_knn=True, min_area=1000, show_mask=True, 
                 enable_tracking=True, stability_threshold=0.8,
                 adaptive_learning_rate=0.001, motion_consistency_frames=5):
        """
        鲁棒性运动检测器 - 解决曝光变化和物体分割问题
        
        参数:
            use_knn: 使用KNN背景减除器（对光照变化更鲁棒）
            min_area: 最小轮廓面积阈值
            show_mask: 是否显示前景掩模
            enable_tracking: 是否启用物体跟踪
            stability_threshold: 稳定性阈值，过滤短暂变化
            adaptive_learning_rate: 自适应学习率
            motion_consistency_frames: 运动一致性检测帧数
        """
        # 使用KNN背景减除器（对光照变化更鲁棒）
        self.backSub = cv2.createBackgroundSubtractorKNN(
            history=1000,           # 更长的历史以获得更稳定的背景
            dist2Threshold=600,     # 更高的距离阈值
            detectShadows=True
        )
        
        self.min_area = min_area
        self.show_mask = show_mask
        self.enable_tracking = enable_tracking
        self.stability_threshold = stability_threshold
        self.adaptive_learning_rate = adaptive_learning_rate
        self.motion_consistency_frames = motion_consistency_frames
        
        # 形态学内核 - 优化以连接物体区域
        self.kernel_open = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        self.kernel_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
        self.kernel_dilate = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
        
        # 物体跟踪和稳定性检测
        self.track_history = defaultdict(lambda: deque(maxlen=30))
        self.object_stability = defaultdict(int)
        self.object_ids = {}
        self.next_object_id = 0
        self.track_colors = {}
        
        # 曝光变化检测
        self.brightness_history = deque(maxlen=10)
        self.last_brightness = 0
        self.exposure_change_detected = False
        
        # 帧缓存用于一致性检查
        self.frame_buffer = deque(maxlen=motion_consistency_frames)
        self.mask_buffer = deque(maxlen=motion_consistency_frames)
        
        # 统计信息
        self.stats = {
            'total_frames': 0,
            'stable_motion_frames': 0,
            'detected_objects': 0,
            'false_positives': 0,
            'processing_times': deque(maxlen=100)
        }
        
        print(f"鲁棒性运动检测器初始化完成")
        print(f"稳定性阈值: {stability_threshold}")
        print(f"自适应学习率: {adaptive_learning_rate}")

    def detect_exposure_change(self, frame):
        """检测曝光变化"""
        # 计算帧的平均亮度
        if len(frame.shape) == 3:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        else:
            gray = frame
            
        current_brightness = np.mean(gray)
        self.brightness_history.append(current_brightness)
        
        # 检测亮度突变
        if len(self.brightness_history) > 1:
            brightness_change = abs(current_brightness - self.last_brightness)
            self.last_brightness = current_brightness
            
            # 如果亮度变化超过阈值，认为是曝光变化
            if brightness_change > 30:  # 经验阈值
                self.exposure_change_detected = True
                return True
            else:
                self.exposure_change_detected = False
                
        return False

    def adaptive_background_learning(self, exposure_changed):
        """自适应背景学习率调整"""
        # KNN背景减除器没有setBackgroundRatio方法
        # 我们通过调整apply方法中的learningRate参数来实现类似效果
        if exposure_changed:
            # 曝光变化时，暂时降低学习率以避免背景模型过快更新
            self.adaptive_learning_rate = 0.0005
        else:
            # 正常情况下的学习率
            self.adaptive_learning_rate = 0.001

    def advanced_morphological_processing(self, fg_mask):
        """高级形态学处理 - 专门解决物体分割问题"""
        # 1. 初始二值化
        _, binary_mask = cv2.threshold(fg_mask, 200, 255, cv2.THRESH_BINARY)
        
        # 2. 开运算去除小噪声（使用较大的核）
        binary_mask = cv2.morphologyEx(binary_mask, cv2.MORPH_OPEN, self.kernel_open)
        
        # 3. 闭运算连接相邻区域（关键步骤 - 使用大核连接分割的物体部分）
        binary_mask = cv2.morphologyEx(binary_mask, cv2.MORPH_CLOSE, self.kernel_close)
        
        # 4. 膨胀操作进一步连接区域
        binary_mask = cv2.dilate(binary_mask, self.kernel_dilate, iterations=2)
        
        # 5. 面积滤波 - 去除小区域
        binary_mask = self.area_filtering(binary_mask)
        
        return binary_mask

    def area_filtering(self, binary_mask):
        """基于面积的区域过滤"""
        # 查找所有轮廓
        contours, _ = cv2.findContours(binary_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # 创建空白掩模
        filtered_mask = np.zeros_like(binary_mask)
        
        # 只保留足够大的轮廓
        for contour in contours:
            area = cv2.contourArea(contour)
            if area > self.min_area:
                cv2.drawContours(filtered_mask, [contour], -1, 255, -1)
                
        return filtered_mask

    def motion_consistency_check(self, current_mask):
        """运动一致性检查 - 过滤短暂噪声"""
        self.mask_buffer.append(current_mask)
        
        if len(self.mask_buffer) < self.motion_consistency_frames:
            return current_mask
            
        # 计算多帧的一致性
        consistent_mask = np.zeros_like(current_mask)
        for mask in self.mask_buffer:
            consistent_mask = cv2.bitwise_or(consistent_mask, mask)
            
        # 只保留在多帧中都稳定的区域
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        consistent_mask = cv2.morphologyEx(consistent_mask, cv2.MORPH_OPEN, kernel)
        
        return consistent_mask

    def hierarchical_contour_analysis(self, binary_mask):
        """分层轮廓分析 - 解决物体过度分割问题"""
        # 查找轮廓
        contours, _ = cv2.findContours(binary_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            return []
        
        # 计算所有轮廓的特征
        contour_features = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < self.min_area:
                continue
                
            # 计算轮廓的几何特征
            x, y, w, h = cv2.boundingRect(contour)
            aspect_ratio = w / h if h > 0 else 0
            solidity = area / (w * h) if w * h > 0 else 0
            
            moments = cv2.moments(contour)
            if moments["m00"] != 0:
                cx = int(moments["m10"] / moments["m00"])
                cy = int(moments["m01"] / moments["m00"])
            else:
                cx, cy = x + w // 2, y + h // 2
                
            contour_features.append({
                'contour': contour,
                'bbox': (x, y, w, h),
                'center': (cx, cy),
                'area': area,
                'aspect_ratio': aspect_ratio,
                'solidity': solidity
            })
        
        # 轮廓合并：基于空间 proximity 和相似性
        merged_contours = self.merge_contours(contour_features)
        
        return merged_contours

    def merge_contours(self, contour_features):
        """合并相邻且相似的轮廓"""
        if not contour_features:
            return []
            
        merged = []
        used = set()
        
        for i, feat1 in enumerate(contour_features):
            if i in used:
                continue
                
            current_group = [feat1]
            used.add(i)
            
            for j, feat2 in enumerate(contour_features):
                if j in used or i == j:
                    continue
                    
                # 检查两个轮廓是否应该合并
                if self.should_merge_contours(feat1, feat2):
                    current_group.append(feat2)
                    used.add(j)
            
            # 合并组内的所有轮廓
            if len(current_group) > 1:
                merged_contour = self.merge_contour_group(current_group)
                merged.append(merged_contour)
            else:
                merged.append(feat1)
        
        # 处理未合并的轮廓
        for i, feat in enumerate(contour_features):
            if i not in used:
                merged.append(feat)
        
        return merged

    def should_merge_contours(self, feat1, feat2):
        """判断两个轮廓是否应该合并"""
        x1, y1, w1, h1 = feat1['bbox']
        x2, y2, w2, h2 = feat2['bbox']
        
        # 计算边界框之间的距离
        center1 = feat1['center']
        center2 = feat2['center']
        distance = np.sqrt((center1[0]-center2[0])**2 + (center1[1]-center2[1])**2)
        
        # 计算边界框重叠情况
        overlap_x = max(0, min(x1+w1, x2+w2) - max(x1, x2))
        overlap_y = max(0, min(y1+h1, y2+h2) - max(y1, y2))
        overlap_area = overlap_x * overlap_y
        
        area1 = w1 * h1
        area2 = w2 * h2
        min_area = min(area1, area2)
        
        # 合并条件：距离近或有重叠，且面积相似
        distance_threshold = min(w1, h1, w2, h2) * 1.5
        area_similarity = abs(area1 - area2) / min_area < 2.0
        
        return (distance < distance_threshold or overlap_area > 0) and area_similarity

    def merge_contour_group(self, contour_group):
        """合并一组轮廓"""
        all_points = []
        total_area = 0
        
        for feat in contour_group:
            all_points.extend(feat['contour'])
            total_area += feat['area']
        
        # 创建合并后的轮廓
        merged_contour = np.array(all_points)
        
        # 计算凸包以获得更平滑的形状
        if len(merged_contour) >= 3:
            merged_contour = cv2.convexHull(merged_contour)
        
        # 计算新的边界框和中心
        x, y, w, h = cv2.boundingRect(merged_contour)
        moments = cv2.moments(merged_contour)
        
        if moments["m00"] != 0:
            cx = int(moments["m10"] / moments["m00"])
            cy = int(moments["m01"] / moments["m00"])
        else:
            cx, cy = x + w // 2, y + h // 2
        
        return {
            'contour': merged_contour,
            'bbox': (x, y, w, h),
            'center': (cx, cy),
            'area': total_area,
            'aspect_ratio': w / h if h > 0 else 0,
            'solidity': total_area / (w * h) if w * h > 0 else 0,
            'merged': True
        }

    def stable_object_tracking(self, current_centers, current_bboxes):
        """稳定性增强的对象跟踪"""
        if not self.enable_tracking:
            return {i: i for i in range(len(current_centers))}
            
        object_matches = {}
        used_centers = set()
        
        # 第一阶段：匹配现有轨迹
        for obj_id, history in list(self.track_history.items()):
            if len(history) > 0:
                last_center = history[-1]
                last_bbox = self.object_ids.get(obj_id, {}).get('last_bbox', (0,0,0,0))
                
                min_distance = float('inf')
                best_match = None
                
                for i, (center, bbox) in enumerate(zip(current_centers, current_bboxes)):
                    if i in used_centers:
                        continue
                        
                    # 使用综合距离度量（中心距离 + 形状相似性）
                    center_distance = np.sqrt((center[0]-last_center[0])**2 + (center[1]-last_center[1])**2)
                    
                    # 形状相似性（基于边界框）
                    x1, y1, w1, h1 = last_bbox
                    x2, y2, w2, h2 = bbox
                    shape_similarity = abs(w1 - w2) + abs(h1 - h2)
                    
                    combined_distance = center_distance + shape_similarity * 0.1
                    
                    if combined_distance < min_distance and combined_distance < 150:  # 综合阈值
                        min_distance = combined_distance
                        best_match = i
                
                if best_match is not None:
                    object_matches[obj_id] = best_match
                    used_centers.add(best_match)
                    self.track_history[obj_id].append(current_centers[best_match])
                    
                    # 更新稳定性计数器
                    self.object_stability[obj_id] += 1
        
        # 第二阶段：为新检测创建轨迹（只有稳定的检测才创建新ID）
        for i, (center, bbox) in enumerate(zip(current_centers, current_bboxes)):
            if i not in used_centers:
                # 只有在一定时间内持续出现的检测才分配新ID
                if self.is_stable_detection(center, bbox):
                    new_id = self.next_object_id
                    self.next_object_id += 1
                    object_matches[new_id] = i
                    self.track_history[new_id].append(center)
                    self.object_stability[new_id] = 1
                    
                    # 生成随机颜色
                    self.track_colors[new_id] = (
                        np.random.randint(50, 255),
                        np.random.randint(50, 255),
                        np.random.randint(50, 255)
                    )
        
        # 清理丢失的轨迹
        self.cleanup_lost_tracks()
        
        return object_matches

    def is_stable_detection(self, center, bbox):
        """检查检测是否稳定"""
        # 简单的稳定性检查：基于面积和位置
        x, y, w, h = bbox
        area = w * h
        
        # 面积不能太小
        if area < self.min_area * 2:
            return False
            
        # 位置合理性检查（不能在图像边缘等）
        if x < 10 or y < 10:
            return False
            
        return True

    def cleanup_lost_tracks(self):
        """清理丢失的轨迹"""
        current_time = time.time()
        lost_tracks = []
        
        for obj_id in list(self.track_history.keys()):
            if self.object_stability.get(obj_id, 0) < 3:  # 稳定性阈值
                lost_tracks.append(obj_id)
        
        for obj_id in lost_tracks:
            if obj_id in self.track_history:
                del self.track_history[obj_id]
            if obj_id in self.object_stability:
                del self.object_stability[obj_id]
            if obj_id in self.track_colors:
                del self.track_colors[obj_id]

    def process_frame_robust(self, frame):
        """鲁棒性帧处理"""
        start_time = time.time()
        
        # 检测曝光变化
        exposure_changed = self.detect_exposure_change(frame)
        
        # 自适应背景学习率调整
        self.adaptive_background_learning(exposure_changed)
        
        # 应用背景减除
        fg_mask = self.backSub.apply(frame, learningRate=self.adaptive_learning_rate)
        
        # 高级形态学处理
        processed_mask = self.advanced_morphological_processing(fg_mask)
        
        # 运动一致性检查
        consistent_mask = self.motion_consistency_check(processed_mask)
        
        # 分层轮廓分析
        contour_features = self.hierarchical_contour_analysis(consistent_mask)
        
        # 提取特征
        centers = [feat['center'] for feat in contour_features]
        bboxes = [feat['bbox'] for feat in contour_features]
        
        # 稳定性增强的跟踪
        object_matches = self.stable_object_tracking(centers, bboxes)
        
        # 绘制结果
        result_frame = frame.copy()
        motion_detected = self.draw_robust_detections(result_frame, contour_features, object_matches)
        
        # 显示掩模
        if self.show_mask:
            mask_display = cv2.cvtColor(consistent_mask, cv2.COLOR_GRAY2BGR)
            
            # 在掩模上绘制检测结果
            for feat in contour_features:
                x, y, w, h = feat['bbox']
                cv2.rectangle(mask_display, (x, y), (x + w, y + h), (0, 255, 0), 2)
            
            result_frame = np.hstack((result_frame, mask_display))
        
        # 性能统计
        processing_time = time.time() - start_time
        self.stats['processing_times'].append(processing_time)
        self.stats['total_frames'] += 1
        
        if motion_detected and len(contour_features) > 0:
            self.stats['stable_motion_frames'] += 1
            
        self.stats['detected_objects'] = len(contour_features)
        
        return result_frame, motion_detected, len(contour_features), exposure_changed

    def draw_robust_detections(self, frame, contour_features, object_matches):
        """绘制鲁棒性检测结果"""
        motion_detected = False
        
        for obj_id, contour_idx in object_matches.items():
            if contour_idx < len(contour_features):
                feat = contour_features[contour_idx]
                contour = feat['contour']
                bbox = feat['bbox']
                center = feat['center']
                
                x, y, w, h = bbox
                
                # 获取跟踪颜色
                color = self.track_colors.get(obj_id, (0, 255, 0))
                
                # 绘制边界框
                cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
                
                # 绘制中心点和ID
                cv2.circle(frame, center, 5, color, -1)
                cv2.putText(frame, f'ID:{obj_id}', (x, y-10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                
                # 绘制轨迹
                if obj_id in self.track_history:
                    points = list(self.track_history[obj_id])
                    for i in range(1, len(points)):
                        thickness = int(3 * (i / len(points))) + 1
                        cv2.line(frame, points[i-1], points[i], color, thickness)
                
                # 显示稳定性信息
                stability = self.object_stability.get(obj_id, 0)
                cv2.putText(frame, f'Stable:{stability}', (x, y+h+20), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
                
                motion_detected = True
        
        return motion_detected

    def get_performance_stats(self):
        """获取性能统计"""
        if len(self.stats['processing_times']) > 0:
            avg_time = np.mean(self.stats['processing_times'])
            fps = 1.0 / avg_time if avg_time > 0 else 0
        else:
            avg_time = 0
            fps = 0
            
        return {
            'fps': fps,
            'avg_processing_time': avg_time * 1000,
            'total_frames': self.stats['total_frames'],
            'stable_motion_frames': self.stats['stable_motion_frames'],
            'motion_ratio': (self.stats['stable_motion_frames'] / self.stats['total_frames'] * 100) 
                            if self.stats['total_frames'] > 0 else 0,
            'current_objects': self.stats['detected_objects'],
            'active_tracks': len(self.track_history)
        }

def main():
    parser = argparse.ArgumentParser(description='鲁棒性实时运动检测系统')
    parser.add_argument('--input', type=str, default='0', 
                       help='输入源: 摄像头ID (如0,1) 或视频文件路径')
    parser.add_argument('--min_area', type=int, default=1000,
                       help='最小检测区域面积 (默认: 1000)')
    parser.add_argument('--use_mog2', action='store_true',
                       help='使用MOG2背景减除器 (默认使用KNN)')
    parser.add_argument('--no_mask', action='store_true',
                       help='不显示前景掩模')
    parser.add_argument('--no_tracking', action='store_true',
                       help='禁用物体跟踪')
    parser.add_argument('--stability_threshold', type=float, default=0.8,
                       help='稳定性阈值 (0-1)')
    parser.add_argument('--output_dir', type=str, default='output',
                       help='输出目录')
    
    args = parser.parse_args()
    
    # 初始化视频源
    try:
        input_source = int(args.input)
    except ValueError:
        input_source = args.input
    
    cap = cv2.VideoCapture(input_source)
    
    if not cap.isOpened():
        print(f"错误: 无法打开视频源 {args.input}")
        return
    
    # 设置合适的分辨率
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    
    # 获取实际分辨率
    actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    
    print(f"视频源: {args.input}")
    print(f"分辨率: {actual_width}x{actual_height}")
    print(f"FPS: {fps}")
    
    # 初始化鲁棒性检测器
    detector = RobustMotionDetector(
        use_knn=not args.use_mog2,  # 默认使用KNN（对光照变化更鲁棒）
        min_area=args.min_area,
        show_mask=not args.no_mask,
        enable_tracking=not args.no_tracking,
        stability_threshold=args.stability_threshold
    )
    
    # 性能监控
    performance_history = deque(maxlen=100)
    start_time = time.time()
    exposure_change_count = 0
    
    print("\n=== 鲁棒性实时运动检测系统 ===")
    print("专门解决曝光变化和物体分割问题")
    print("快捷键:")
    print("  'q' - 退出")
    print("  'p' - 暂停/继续")
    print("  'r' - 重置背景模型")
    print("  'c' - 清除跟踪历史")
    print("  'd' - 切换调试显示")
    
    paused = False
    show_debug = True
    
    try:
        while True:
            if not paused:
                ret, frame = cap.read()
                if not ret:
                    print("无法读取帧，退出...")
                    break
                
                # 处理帧
                processed_frame, motion_detected, num_objects, exposure_changed = detector.process_frame_robust(frame)
                
                if exposure_changed:
                    exposure_change_count += 1
                
                # 获取性能统计
                stats = detector.get_performance_stats()
                performance_history.append(stats['fps'])
                
                # 显示统计信息
                if show_debug:
                    stats_text = [
                        f'FPS: {stats["fps"]:.1f}',
                        f'Processing: {stats["avg_processing_time"]:.1f}ms',
                        f'Frames: {stats["total_frames"]}',
                        f'Stable Motion: {stats["stable_motion_frames"]} ({stats["motion_ratio"]:.1f}%)',
                        f'Objects: {stats["current_objects"]}',
                        f'Tracks: {stats["active_tracks"]}',
                        f'Exposure Changes: {exposure_change_count}',
                        f'Min Area: {args.min_area}'
                    ]
                    
                    for i, text in enumerate(stats_text):
                        # 背景阴影
                        cv2.putText(processed_frame, text, (12, 35 + i * 25), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 3)
                        # 前景文字
                        cv2.putText(processed_frame, text, (10, 33 + i * 25), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                
                # 显示状态
                status = "STABLE MOTION" if motion_detected else "NO MOTION"
                color = (0, 255, 0) if motion_detected else (0, 0, 255)
                cv2.putText(processed_frame, status, (actual_width-200, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
                
                # 显示结果
                cv2.imshow('Robust Motion Detection', processed_frame)
            
            # 键盘输入处理
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('p'):
                paused = not paused
                print("暂停" if paused else "继续")
            elif key == ord('r'):
                # 重新初始化背景减除器
                if not args.use_mog2:  # 使用KNN
                    detector.backSub = cv2.createBackgroundSubtractorKNN(
                        history=1000,
                        dist2Threshold=600,
                        detectShadows=True
                    )
                else:  # 使用MOG2
                    detector.backSub = cv2.createBackgroundSubtractorMOG2(
                        history=1000,
                        varThreshold=16,
                        detectShadows=True
                    )
                print("背景模型已重置")
            elif key == ord('c'):
                detector.track_history.clear()
                detector.object_stability.clear()
                detector.next_object_id = 0
                print("跟踪历史已清除")
            elif key == ord('d'):
                show_debug = not show_debug
                print("调试显示:" + ("开启" if show_debug else "关闭"))
    
    except KeyboardInterrupt:
        print("\n程序被用户中断")
    
    finally:
        # 释放资源
        cap.release()
        cv2.destroyAllWindows()
        
        # 打印最终统计
        total_time = time.time() - start_time
        final_stats = detector.get_performance_stats()
        
        print(f"\n=== 最终统计 ===")
        print(f"总运行时间: {total_time:.2f}秒")
        print(f"处理帧数: {final_stats['total_frames']}")
        print(f"平均FPS: {final_stats['fps']:.2f}")
        print(f"稳定运动帧数: {final_stats['stable_motion_frames']}")
        print(f"稳定运动比例: {final_stats['motion_ratio']:.2f}%")
        print(f"曝光变化次数: {exposure_change_count}")
        print(f"最大跟踪物体数: {final_stats['active_tracks']}")
        
        # 保存统计信息
        os.makedirs(args.output_dir, exist_ok=True)
        stats_filename = os.path.join(args.output_dir, f"robust_stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(stats_filename, 'w') as f:
            json.dump({
                'total_time': total_time,
                'total_frames': final_stats['total_frames'],
                'stable_motion_frames': final_stats['stable_motion_frames'],
                'motion_ratio': final_stats['motion_ratio'],
                'avg_fps': final_stats['fps'],
                'exposure_changes': exposure_change_count,
                'max_tracked_objects': final_stats['active_tracks'],
                'min_area': args.min_area
            }, f, indent=2)
        
        print(f"统计信息已保存: {stats_filename}")

if __name__ == "__main__":
    main()