import cv2
import numpy as np
import time
import random
import threading
from collections import deque
import os
from scipy import ndimage

class AdvancedAntiTrackingSystem:
    def __init__(self):
        # 初始化参数
        self.detection_threshold = 0.7
        self.max_tracking_points = 50
        self.min_tracking_duration = 2.0  # 秒
        
        # 跟踪点历史
        self.tracking_history = deque(maxlen=100)
        self.suspicious_regions = []
        
        # 状态变量
        self.alert_level = 0
        self.counter_measures_active = False
        self.last_alert_time = 0
        
        # 初始化检测器
        self.setup_detectors()
        
    def setup_detectors(self):
        """设置多种检测器"""
        # 运动检测
        self.background_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=500, varThreshold=16, detectShadows=True)
        
        # 特征检测器
        self.orb = cv2.ORB_create(nfeatures=1000)
        self.sift = cv2.SIFT_create()
        
        # 光流参数
        self.lk_params = dict(
            winSize=(15, 15),
            maxLevel=2,
            criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 10, 0.03)
        )
        
    def multi_scale_motion_detection(self, frame):
        """多尺度运动检测"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # 多尺度处理
        scales = [1.0, 0.75, 0.5]
        motion_masks = []
        
        for scale in scales:
            if scale != 1.0:
                scaled_frame = cv2.resize(gray, None, fx=scale, fy=scale)
            else:
                scaled_frame = gray.copy()
                
            # 背景减除
            fg_mask = self.background_subtractor.apply(scaled_frame)
            _, fg_mask = cv2.threshold(fg_mask, 244, 255, cv2.THRESH_BINARY)
            
            # 形态学操作
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
            fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, kernel)
            fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, kernel)
            
            if scale != 1.0:
                fg_mask = cv2.resize(fg_mask, (gray.shape[1], gray.shape[0]))
                
            motion_masks.append(fg_mask)
        
        # 合并多尺度结果
        combined_mask = np.zeros_like(motion_masks[0])
        for mask in motion_masks:
            combined_mask = cv2.bitwise_or(combined_mask, mask)
            
        return combined_mask
    
    def detect_suspicious_patterns(self, frame, motion_mask):
        """检测可疑跟踪模式"""
        contours, _ = cv2.findContours(motion_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        suspicious_regions = []
        current_time = time.time()
        
        for contour in contours:
            if cv2.contourArea(contour) < 500:  # 过滤小区域
                continue
                
            x, y, w, h = cv2.boundingRect(contour)
            
            # 计算运动特征
            region_data = {
                'bbox': (x, y, w, h),
                'center': (x + w//2, y + h//2),
                'area': cv2.contourArea(contour),
                'timestamp': current_time,
                'persistence': 1
            }
            
            # 检查是否为持续跟踪
            region_data = self.check_tracking_persistence(region_data)
            
            if region_data['persistence'] > self.min_tracking_duration:
                suspicious_regions.append(region_data)
                
        return suspicious_regions
    
    def check_tracking_persistence(self, current_region):
        """检查跟踪持续性"""
        current_time = time.time()
        current_center = current_region['center']
        
        # 查找历史中的匹配区域
        matched = False
        for history in self.tracking_history:
            hist_center = history['center']
            distance = np.sqrt((current_center[0] - hist_center[0])**2 + 
                             (current_center[1] - hist_center[1])**2)
            
            if distance < 50:  # 距离阈值
                current_region['persistence'] = history['persistence'] + 1
                matched = True
                break
                
        if not matched:
            current_region['persistence'] = 1
            
        # 添加到历史
        self.tracking_history.append(current_region.copy())
        
        return current_region
    
    def optical_flow_analysis(self, prev_frame, current_frame, prev_points):
        """光流分析检测跟踪行为"""
        if prev_points is None or len(prev_points) == 0:
            # 检测新的特征点
            prev_points = cv2.goodFeaturesToTrack(
                prev_frame, maxCorners=100, qualityLevel=0.3, minDistance=7, blockSize=7)
            
        if prev_points is not None:
            # 计算光流
            current_points, status, error = cv2.calcOpticalFlowPyrLK(
                prev_frame, current_frame, prev_points, None, **self.lk_params)
            
            # 筛选好的点
            if current_points is not None:
                good_old = prev_points[status == 1]
                good_new = current_points[status == 1]
                
                return good_new, good_old
                
        return None, None
    
    def apply_counter_measures(self, frame, suspicious_regions):
        """应用反跟踪措施"""
        protected_frame = frame.copy()
        alert_triggered = False
        
        for region in suspicious_regions:
            x, y, w, h = region['bbox']
            persistence = region['persistence']
            
            # 根据持续时间和威胁级别应用不同对策
            if persistence > 5:
                # 高强度对策：视觉干扰
                protected_frame = self.visual_interference(protected_frame, (x, y, w, h))
                alert_triggered = True
                self.alert_level = max(self.alert_level, 2)
                
            elif persistence > 3:
                # 中强度对策：区域模糊
                protected_frame = self.region_obfuscation(protected_frame, (x, y, w, h))
                alert_triggered = True
                self.alert_level = max(self.alert_level, 1)
                
            elif persistence > 1:
                # 低强度对策：警告标记
                protected_frame = self.warning_overlay(protected_frame, (x, y, w, h))
                
        if alert_triggered:
            self.last_alert_time = time.time()
            self.counter_measures_active = True
            
        return protected_frame, alert_triggered
    
    def visual_interference(self, frame, bbox):
        """视觉干扰对策"""
        x, y, w, h = bbox
    
        # 方法1: 强光闪烁干扰
        overlay = frame.copy()
        cv2.rectangle(overlay, (x, y), (x+w, y+h), (255, 255, 255), -1)
        alpha = 0.3 + 0.2 * np.sin(time.time() * 10)  # 闪烁效果
        cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)
        
        # 方法2: 图案干扰
        pattern = self.generate_interference_pattern(w, h)
        frame[y:y+h, x:x+w] = cv2.addWeighted(
            frame[y:y+h, x:x+w], 0.7, pattern, 0.3, 0)
        
        # 方法3: 数字噪声
        noise = np.random.randint(0, 64, (h, w, 3), dtype=np.uint8)
        frame[y:y+h, x:x+w] = cv2.add(frame[y:y+h, x:x+w], noise)
        
        return frame
    
    def generate_interference_pattern(self, width, height):
        """生成干扰图案"""
        pattern = np.zeros((height, width, 3), dtype=np.uint8)
        
        # 创建多种干扰图案
        for i in range(3):
            # 随机条纹
            stripe_width = random.randint(5, 20)
            for x in range(0, width, stripe_width*2):
                color = [random.randint(200, 255) for _ in range(3)]
                pattern[:, x:x+stripe_width] = color
            
            # 随机点阵
            dot_size = random.randint(2, 8)
            for _ in range(width * height // 50):
                px = random.randint(0, width-1)
                py = random.randint(0, height-1)
                color = [random.randint(200, 255) for _ in range(3)]
                cv2.circle(pattern, (px, py), dot_size, color, -1)
                
        return pattern
    
    def region_obfuscation(self, frame, bbox):
        """区域模糊和混淆"""
        x, y, w, h = bbox
        
        # 高斯模糊
        blurred_region = cv2.GaussianBlur(frame[y:y+h, x:x+w], (25, 25), 0)
        
        # 像素化效果
        pixel_size = 10
        h, w = blurred_region.shape[:2]
        temp = cv2.resize(blurred_region, (w//pixel_size, h//pixel_size), 
                         interpolation=cv2.INTER_LINEAR)
        pixelated = cv2.resize(temp, (w, h), interpolation=cv2.INTER_NEAREST)
        
        frame[y:y+h, x:x+w] = pixelated
        
        return frame
    
    def warning_overlay(self, frame, bbox):
        """警告叠加"""
        x, y, w, h = bbox
        
        # 绘制警告框
        cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 0, 255), 2)
        cv2.putText(frame, "TRACKING DETECTED", (x, y-10),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        
        return frame
    
    def behavioral_analysis(self, frame, suspicious_regions):
        """行为模式分析"""
        analysis_results = {
            'threat_level': 0,
            'tracking_patterns': [],
            'recommended_actions': []
        }
        
        if len(suspicious_regions) == 0:
            return analysis_results
            
        # 分析跟踪模式
        persistent_count = sum(1 for r in suspicious_regions 
                             if r['persistence'] > 3)
        
        if persistent_count >= 2:
            analysis_results['threat_level'] = 2
            analysis_results['recommended_actions'].extend([
                "激活高级干扰模式",
                "建议改变行进路线",
                "启用环境感知规避"
            ])
        elif persistent_count >= 1:
            analysis_results['threat_level'] = 1
            analysis_results['recommended_actions'].append("保持警惕，监控情况")
            
        return analysis_results
    
    def run_anti_tracking(self, video_source=0):
        """主运行函数"""
        cap = cv2.VideoCapture(video_source)
        if not cap.isOpened():
            print("无法打开视频源")
            return
        
        prev_frame = None
        prev_points = None
        current_points = None  # 添加这行初始化
        frame_count = 0
        
        print("启动前瞻性视觉反跟踪系统...")
        print("系统状态: 运行中")
        print("威胁等级: 监控模式")
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
                
            frame_count += 1
            
            # 预处理帧
            current_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # 运动检测
            motion_mask = self.multi_scale_motion_detection(frame)
            
            # 检测可疑模式
            suspicious_regions = self.detect_suspicious_patterns(frame, motion_mask)
            
            # 光流分析
            if prev_frame is not None:
                current_points, prev_points = self.optical_flow_analysis(
                    prev_frame, current_gray, prev_points)
            else:
                current_points = None  # 确保在第一次循环时设置为None
            
            # 行为分析
            behavior_analysis = self.behavioral_analysis(frame, suspicious_regions)
            
            # 应用反跟踪措施
            protected_frame, alert_triggered = self.apply_counter_measures(
                frame, suspicious_regions)
            
            # 更新显示
            display_frame = self.create_display_frame(
                protected_frame, motion_mask, suspicious_regions, behavior_analysis)
            
            cv2.imshow('Advanced Anti-Tracking System', display_frame)
            
            # 打印系统状态
            if frame_count % 30 == 0:  # 每30帧更新一次状态
                self.print_system_status(behavior_analysis, len(suspicious_regions))
            
            # 更新前一帧数据
            prev_frame = current_gray.copy()
            if current_points is not None:
                prev_points = current_points.reshape(-1, 1, 2)
            
            # 退出条件
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
                
        cap.release()
        cv2.destroyAllWindows()
    
    def create_display_frame(self, frame, motion_mask, suspicious_regions, behavior_analysis):
        """创建显示帧"""
        # 调整大小为显示
        display_frame = cv2.resize(frame, (800, 600))
        
        # 添加系统状态信息
        status_text = [
            f"threat_level: {behavior_analysis['threat_level']}",
            f"suspicious_regions: {len(suspicious_regions)}",
            f"counter_measures_active: {'激活' if self.counter_measures_active else '待机'}",
            f"alert_level: {self.alert_level}"
        ]
        
        for i, text in enumerate(status_text):
            cv2.putText(display_frame, text, (10, 30 + i*25),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        # 添加建议行动
        if behavior_analysis['recommended_actions']:
            for i, action in enumerate(behavior_analysis['recommended_actions']):
                cv2.putText(display_frame, f"建议: {action}", (10, 150 + i*25),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
        
        return display_frame
    
    def print_system_status(self, behavior_analysis, region_count):
        """打印系统状态"""
        print(f"\n--- 系统状态更新 [{time.strftime('%H:%M:%S')}] ---")
        print(f"检测到可疑区域: {region_count}")
        print(f"当前威胁等级: {behavior_analysis['threat_level']}")
        print(f"反跟踪状态: {'激活' if self.counter_measures_active else '监控中'}")
        
        if behavior_analysis['recommended_actions']:
            print("建议行动:")
            for action in behavior_analysis['recommended_actions']:
                print(f"  - {action}")

# 使用示例
if __name__ == "__main__":
    # 创建反跟踪系统实例
    anti_tracker = AdvancedAntiTrackingSystem()
    
    # 启动系统
    # 使用摄像头 (0) 或视频文件路径
    try:
        anti_tracker.run_anti_tracking(0)  # 0 表示默认摄像头
    except KeyboardInterrupt:
        print("\n系统安全关闭")
    except Exception as e:
        print(f"系统错误: {e}")