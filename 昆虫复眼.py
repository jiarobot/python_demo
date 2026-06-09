import numpy as np
import cv2
import matplotlib.pyplot as plt
from scipy import ndimage
from scipy.signal import convolve2d
import time
from collections import deque
import warnings
warnings.filterwarnings('ignore')

class BioInspiredMotionDetector:
    """
    基于昆虫复眼原理的生物启发式运动检测器
    """
    
    def __init__(self, num_ommatidia=8, temporal_window=5):
        """
        初始化参数
        
        Args:
            num_ommatidia: 模拟的小眼数量（方向通道）
            temporal_window: 时间窗口大小
        """
        self.num_ommatidia = num_ommatidia
        self.temporal_window = temporal_window
        self.frame_buffer = deque(maxlen=temporal_window)
        
        # 创建方向选择性的Gabor滤波器组
        self.gabor_filters = self._create_gabor_filters()
        
        # 运动检测参数
        self.motion_threshold = 0.1
        self.adaptation_rate = 0.01
        
        # 结果存储
        self.motion_maps = []
        self.direction_maps = []
        
    def _create_gabor_filters(self):
        """创建多方向Gabor滤波器模拟小眼方向选择性"""
        filters = []
        angles = np.linspace(0, np.pi, self.num_ommatidia, endpoint=False)
        
        for theta in angles:
            # Gabor滤波器参数
            ksize = 9
            sigma = 2.0
            lambd = 5.0
            gamma = 0.5
            psi = 0
            
            # 创建Gabor核
            gabor_kernel = np.zeros((ksize, ksize))
            
            for x in range(ksize):
                for y in range(ksize):
                    x_ = x - ksize//2
                    y_ = y - ksize//2
                    
                    x_theta = x_ * np.cos(theta) + y_ * np.sin(theta)
                    y_theta = -x_ * np.sin(theta) + y_ * np.cos(theta)
                    
                    gabor_kernel[x, y] = np.exp(-0.5 * (x_theta**2 + gamma**2 * y_theta**2) / sigma**2) * \
                                        np.cos(2 * np.pi * x_theta / lambd + psi)
            
            # 归一化
            gabor_kernel = gabor_kernel - np.mean(gabor_kernel)
            gabor_kernel = gabor_kernel / np.sum(np.abs(gabor_kernel))
            
            filters.append(gabor_kernel)
            
        return filters
    
    def _temporal_highpass_filter(self, frame_sequence):
        """时间高通滤波 - 模拟昆虫视觉系统的时间特性"""
        if len(frame_sequence) < 2:
            return frame_sequence[-1]
        
        # 简单的时间差分
        filtered = frame_sequence[-1].astype(float) - frame_sequence[-2].astype(float)
        return np.clip(filtered, 0, 255).astype(np.uint8)
    
    def _lateral_inhibition(self, feature_map):
        """侧抑制机制 - 增强对比度"""
        # 创建墨西哥帽滤波器（中心兴奋，周边抑制）
        size = 5
        x, y = np.mgrid[-size//2+1:size//2+1, -size//2+1:size//2+1]
        sigma1, sigma2 = 1.0, 2.0
        
        dog_filter = (1/(2*np.pi*sigma1**2)) * np.exp(-(x**2+y**2)/(2*sigma1**2)) - \
                    (1/(2*np.pi*sigma2**2)) * np.exp(-(x**2+y**2)/(2*sigma2**2))
        
        dog_filter = dog_filter / np.sum(np.abs(dog_filter))
        
        # 应用侧抑制
        inhibited = convolve2d(feature_map, dog_filter, mode='same', boundary='symm')
        return np.maximum(inhibited, 0)
    
    def _compute_motion_energy(self, current_features, previous_features):
        """计算运动能量 - Reichardt运动检测器原理"""
        motion_energy = np.zeros_like(current_features[0])
        direction_selectivity = np.zeros((current_features[0].shape[0], 
                                        current_features[0].shape[1], 
                                        self.num_ommatidia))
        
        for i in range(self.num_ommatidia):
            # 时间相关性检测运动
            motion_correlation = current_features[i] * np.roll(previous_features[i], 2, axis=1)
            
            # 双向运动检测
            motion_forward = np.abs(motion_correlation)
            motion_backward = np.abs(current_features[i] * np.roll(previous_features[i], -2, axis=1))
            
            # 方向选择性输出
            direction_energy = motion_forward - motion_backward
            direction_selectivity[:, :, i] = self._lateral_inhibition(direction_energy)
            
            # 总运动能量
            motion_energy += motion_forward + motion_backward
        
        # 应用侧抑制增强运动边界
        motion_energy = self._lateral_inhibition(motion_energy)
        
        return motion_energy, direction_selectivity
    
    def _extract_motion_contours(self, motion_energy):
        """从运动能量中提取运动轮廓"""
        # 阈值处理
        threshold = np.mean(motion_energy) + 2 * np.std(motion_energy)
        binary_motion = (motion_energy > threshold).astype(np.uint8) * 255
        
        # 形态学操作
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        binary_motion = cv2.morphologyEx(binary_motion, cv2.MORPH_CLOSE, kernel)
        
        # 轮廓提取
        contours, _ = cv2.findContours(binary_motion, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        return contours, binary_motion
    
    def _adaptive_thresholding(self, motion_energy):
        """自适应阈值 - 模拟视觉系统的适应性"""
        global_mean = np.mean(motion_energy)
        local_means = ndimage.uniform_filter(motion_energy, size=10)
        
        # 基于局部对比度的自适应阈值
        adaptive_threshold = local_means + 0.5 * (global_mean - local_means)
        self.motion_threshold = 0.99 * self.motion_threshold + 0.01 * np.mean(adaptive_threshold)
        
        return motion_energy > self.motion_threshold
    
    def process_frame(self, frame):
        """处理单帧图像"""
        if len(frame.shape) == 3:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        else:
            gray = frame.copy()
        
        # 添加到时间缓冲区
        self.frame_buffer.append(gray)
        
        if len(self.frame_buffer) < 2:
            return np.zeros_like(gray), np.zeros((gray.shape[0], gray.shape[1], 3))
        
        # 时间高通滤波
        temporal_filtered = self._temporal_highpass_filter(self.frame_buffer)
        
        # 多方向特征提取
        current_features = []
        previous_features = []
        
        for gabor_filter in self.gabor_filters:
            current_feature = convolve2d(temporal_filtered, gabor_filter, mode='same', boundary='symm')
            previous_feature = convolve2d(self.frame_buffer[-2], gabor_filter, mode='same', boundary='symm')
            
            current_features.append(current_feature)
            previous_features.append(previous_feature)
        
        # 运动能量计算
        motion_energy, direction_selectivity = self._compute_motion_energy(current_features, previous_features)
        
        # 运动轮廓提取
        motion_contours, binary_motion = self._extract_motion_contours(motion_energy)
        
        # 方向编码可视化
        direction_visual = self._visualize_directions(direction_selectivity)
        
        # 存储结果
        self.motion_maps.append(motion_energy)
        self.direction_maps.append(direction_selectivity)
        
        return binary_motion, direction_visual
    
    def _visualize_directions(self, direction_selectivity):
        """可视化方向选择性"""
        h, w, d = direction_selectivity.shape
        
        # 找到每个像素的主要方向
        dominant_direction = np.argmax(direction_selectivity, axis=2)
        
        # 创建HSV颜色映射：色相表示方向，饱和度表示强度
        hsv = np.zeros((h, w, 3), dtype=np.uint8)
        
        # 方向到色相的映射
        hue = (dominant_direction * (180 // self.num_ommatidia)).astype(np.uint8)
        
        # 强度归一化
        max_intensity = np.max(direction_selectivity, axis=2)
        saturation = (255 * (max_intensity / (np.max(max_intensity) + 1e-6))).astype(np.uint8)
        value = (255 * (max_intensity > self.motion_threshold)).astype(np.uint8)
        
        hsv[:, :, 0] = hue
        hsv[:, :, 1] = saturation
        hsv[:, :, 2] = value
        
        # 转换回BGR
        direction_visual = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
        
        return direction_visual
    
    def analyze_motion_patterns(self, num_frames=10):
        """分析运动模式"""
        if len(self.motion_maps) < num_frames:
            num_frames = len(self.motion_maps)
        
        recent_motion = self.motion_maps[-num_frames:]
        
        if not recent_motion:
            return {}
        
        # 计算运动统计
        motion_array = np.array(recent_motion)
        
        analysis = {
            'total_motion_energy': np.sum(motion_array),
            'mean_motion_intensity': np.mean(motion_array),
            'motion_variance': np.var(motion_array),
            'dominant_direction': self._get_dominant_direction(),
            'motion_coherence': self._calculate_motion_coherence(motion_array)
        }
        
        return analysis
    
    def _get_dominant_direction(self):
        """获取主导运动方向"""
        if not self.direction_maps:
            return 0
        
        recent_directions = self.direction_maps[-1]
        direction_histogram = np.sum(recent_directions, axis=(0, 1))
        dominant_idx = np.argmax(direction_histogram)
        
        return dominant_idx * (360 / self.num_ommatidia)
    
    def _calculate_motion_coherence(self, motion_array):
        """计算运动一致性"""
        if len(motion_array) < 2:
            return 0
        
        # 计算帧间相关性作为一致性度量
        correlation_sum = 0
        for i in range(len(motion_array) - 1):
            corr = np.corrcoef(motion_array[i].flatten(), motion_array[i+1].flatten())[0, 1]
            correlation_sum += corr if not np.isnan(corr) else 0
        
        return correlation_sum / (len(motion_array) - 1)

class MultiScaleMotionAnalyzer:
    """多尺度运动分析器"""
    
    def __init__(self, scales=[1.0, 0.5, 0.25]):
        self.scales = scales
        self.detectors = [BioInspiredMotionDetector() for _ in scales]
    
    def process_frame(self, frame):
        """多尺度处理"""
        results = {}
        
        for scale, detector in zip(self.scales, self.detectors):
            # 缩放图像
            if scale != 1.0:
                scaled_frame = cv2.resize(frame, None, fx=scale, fy=scale)
            else:
                scaled_frame = frame
            
            # 处理每个尺度
            motion_map, direction_map = detector.process_frame(scaled_frame)
            
            # 缩放回原尺寸
            if scale != 1.0:
                motion_map = cv2.resize(motion_map, (frame.shape[1], frame.shape[0]))
                direction_map = cv2.resize(direction_map, (frame.shape[1], frame.shape[0]))
            
            results[f'scale_{scale}'] = {
                'motion': motion_map,
                'direction': direction_map,
                'analysis': detector.analyze_motion_patterns()
            }
        
        # 融合多尺度结果
        fused_motion = self._fuse_scales(results)
        
        return results, fused_motion
    
    def _fuse_scales(self, results):
        """融合多尺度检测结果"""
        motion_maps = [data['motion'] for data in results.values()]
        
        # 简单最大值融合
        fused = np.zeros_like(motion_maps[0])
        for motion_map in motion_maps:
            fused = np.maximum(fused, motion_map)
        
        return fused

def demo_real_time():
    """实时演示"""
    cap = cv2.VideoCapture(0)  # 使用摄像头
    
    if not cap.isOpened():
        print("无法打开摄像头")
        return
    
    # 创建多尺度分析器
    analyzer = MultiScaleMotionAnalyzer()
    
    print("开始实时运动检测...")
    print("按 'q' 键退出")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # 处理帧
        start_time = time.time()
        results, fused_motion = analyzer.process_frame(frame)
        processing_time = time.time() - start_time
        
        # 显示结果
        display_frame = frame.copy()
        
        # 叠加运动检测结果
        motion_overlay = cv2.applyColorMap(fused_motion, cv2.COLORMAP_JET)
        cv2.addWeighted(motion_overlay, 0.5, display_frame, 0.5, 0, display_frame)
        
        # 显示方向信息
        direction_display = results['scale_1.0']['direction']
        
        # 显示处理时间
        cv2.putText(display_frame, f'FPS: {1/processing_time:.1f}', 
                   (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        
        # 显示运动分析结果 - 添加安全检查
        analysis = results['scale_1.0']['analysis']
        
        # 检查分析结果是否为空
        if analysis:  # 如果字典不为空
            total_energy = analysis.get('total_motion_energy', 0)
            dominant_direction = analysis.get('dominant_direction', 0)
            motion_coherence = analysis.get('motion_coherence', 0)
        else:
            total_energy = 0
            dominant_direction = 0
            motion_coherence = 0
        
        cv2.putText(display_frame, f'Motion: {total_energy:.0f}', 
                   (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        # 显示方向
        cv2.putText(display_frame, f'Direction: {dominant_direction:.1f}°', 
                   (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        # 显示运动一致性
        cv2.putText(display_frame, f'Coherence: {motion_coherence:.2f}', 
                   (10, 130), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        # 合并显示 - 修复宽度不匹配问题
        # 确保两个图像宽度相同
        if display_frame.shape[1] != direction_display.shape[1]:
            direction_display = cv2.resize(direction_display, 
                                         (display_frame.shape[1], direction_display.shape[0]))
        
        top_row = np.hstack([display_frame, direction_display])
        
        # 显示多尺度结果
        scale_results = []
        for scale_name, result in results.items():
            scale_display = cv2.resize(result['motion'], (200, 150))
            scale_display = cv2.applyColorMap(scale_display, cv2.COLORMAP_JET)
            cv2.putText(scale_display, scale_name, (10, 20), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            scale_results.append(scale_display)
        
        # 修复底部行宽度不匹配问题
        if scale_results:
            # 计算需要多少个200x150的图像来匹配顶部行的宽度
            target_width = top_row.shape[1]
            num_needed = max(1, target_width // 200)
            
            # 如果现有的图像数量不够，复制最后一个图像
            while len(scale_results) < num_needed:
                scale_results.append(scale_results[-1])
            
            # 如果图像数量超过需要，截断
            scale_results = scale_results[:num_needed]
            
            # 调整每个图像的宽度，使总宽度匹配
            if num_needed > 0:
                individual_width = target_width // num_needed
                resized_scales = []
                for scale_img in scale_results:
                    resized = cv2.resize(scale_img, (individual_width, 150))
                    resized_scales.append(resized)
                
                # 如果还有余数，调整最后一个图像的宽度
                if target_width % num_needed != 0:
                    last_width = target_width - (individual_width * (num_needed - 1))
                    resized_scales[-1] = cv2.resize(scale_results[-1], (last_width, 150))
                
                bottom_row = np.hstack(resized_scales)
            else:
                bottom_row = np.zeros((150, target_width, 3), dtype=np.uint8)
            
            # 确保底部行宽度与顶部行完全匹配
            if bottom_row.shape[1] != top_row.shape[1]:
                bottom_row = cv2.resize(bottom_row, (top_row.shape[1], 150))
            
            final_display = np.vstack([top_row, bottom_row])
        else:
            final_display = top_row
        
        cv2.imshow('Bio-inspired Motion Detection', final_display)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()

def demo_video_file(video_path):
    """视频文件演示"""
    cap = cv2.VideoCapture(video_path)
    analyzer = MultiScaleMotionAnalyzer()
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        
        results, fused_motion = analyzer.process_frame(frame)
        
        # 显示结果（类似实时演示）
        display_frame = frame.copy()
        motion_overlay = cv2.applyColorMap(fused_motion, cv2.COLORMAP_JET)
        cv2.addWeighted(motion_overlay, 0.5, display_frame, 0.5, 0, display_frame)
        
        cv2.imshow('Video Motion Detection', display_frame)
        
        if cv2.waitKey(25) & 0xFF == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    # 选择演示模式
    print("选择演示模式:")
    print("1. 实时摄像头")
    print("2. 视频文件")
    
    choice = input("输入选择 (1 或 2): ")
    
    if choice == "1":
        demo_real_time()
    elif choice == "2":
        video_path = input("输入视频文件路径: ")
        demo_video_file(video_path)
    else:
        print("使用默认的实时摄像头演示")
        demo_real_time()