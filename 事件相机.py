import numpy as np
import cv2
from collections import deque
import matplotlib.pyplot as plt
from scipy import ndimage
from sklearn.ensemble import IsolationForest
import time

class EventCameraSimulator:
    """事件相机模拟器 - 将传统视频流转换为事件流"""
    
    def __init__(self, temporal_resolution=0.001):
        self.temporal_resolution = temporal_resolution
        self.last_frame = None
        self.last_time = 0
        self.event_queue = []
        
    def frame_to_events(self, frame, current_time):
        """将帧转换为事件流"""
        events = []
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if len(frame.shape) == 3 else frame
        
        if self.last_frame is not None:
            # 计算亮度变化
            diff = gray_frame.astype(np.float32) - self.last_frame.astype(np.float32)
            
            # 生成事件（只记录显著变化）
            threshold = 5  # 事件触发阈值
            positive_events = np.where(diff > threshold)
            negative_events = np.where(diff < -threshold)
            
            # 添加正事件（亮度增加）
            for y, x in zip(positive_events[0], positive_events[1]):
                events.append({
                    'x': x, 'y': y, 
                    'timestamp': current_time,
                    'polarity': 1  # 正事件
                })
            
            # 添加负事件（亮度减少）
            for y, x in zip(negative_events[0], negative_events[1]):
                events.append({
                    'x': x, 'y': y,
                    'timestamp': current_time, 
                    'polarity': -1  # 负事件
                })
        
        self.last_frame = gray_frame.copy()
        self.last_time = current_time
        return events

class SpatioTemporalFeatureExtractor:
    """时空特征提取器"""
    
    def __init__(self, window_size=50):
        self.window_size = window_size
        self.event_buffer = deque(maxlen=window_size)
        self.feature_vectors = []
        
    def add_events(self, events):
        """添加事件到缓冲区"""
        self.event_buffer.extend(events)
        
    def extract_motion_histogram(self, frame_shape, temporal_bins=8, spatial_bins=4):
        """提取运动直方图特征"""
        if len(self.event_buffer) == 0:
            return None
            
        # 创建时空直方图
        height, width = frame_shape
        spatial_height = height // spatial_bins
        spatial_width = width // spatial_bins
        
        # 初始化直方图
        histogram = np.zeros((spatial_bins, spatial_bins, temporal_bins, 2))  # 2 for polarity
        
        # 计算时间窗口
        if len(self.event_buffer) > 0:
            max_time = max(ev['timestamp'] for ev in self.event_buffer)
            min_time = min(ev['timestamp'] for ev in self.event_buffer)
            time_range = max_time - min_time if max_time > min_time else 1
            
            for event in self.event_buffer:
                # 空间分bin
                spatial_x = min(event['x'] // spatial_width, spatial_bins - 1)
                spatial_y = min(event['y'] // spatial_height, spatial_bins - 1)
                
                # 时间分bin
                time_normalized = (event['timestamp'] - min_time) / time_range
                temporal_bin = min(int(time_normalized * temporal_bins), temporal_bins - 1)
                
                # 极性分bin
                polarity_idx = 0 if event['polarity'] > 0 else 1
                
                histogram[spatial_y, spatial_x, temporal_bin, polarity_idx] += 1
        
        return histogram.flatten()
    
    def extract_trajectory_features(self):
        """提取手势轨迹特征"""
        if len(self.event_buffer) < 10:
            return None
            
        events = list(self.event_buffer)
        
        # 计算质心运动
        positive_events = [ev for ev in events if ev['polarity'] > 0]
        if len(positive_events) < 5:
            return None
            
        # 按时间分片计算质心
        centroids = []
        time_slices = np.linspace(events[0]['timestamp'], events[-1]['timestamp'], 5)
        
        for i in range(len(time_slices)-1):
            slice_events = [ev for ev in positive_events 
                          if time_slices[i] <= ev['timestamp'] < time_slices[i+1]]
            if slice_events:
                avg_x = np.mean([ev['x'] for ev in slice_events])
                avg_y = np.mean([ev['y'] for ev in slice_events])
                centroids.append((avg_x, avg_y))
        
        if len(centroids) < 3:
            return None
            
        # 计算轨迹特征
        centroids = np.array(centroids)
        displacements = np.diff(centroids, axis=0)
        
        features = {
            'total_distance': np.sum(np.linalg.norm(displacements, axis=1)),
            'avg_speed': np.mean(np.linalg.norm(displacements, axis=1)),
            'direction_changes': self.calculate_direction_changes(displacements),
            'curvature': self.calculate_curvature(centroids)
        }
        
        return features
    
    def calculate_direction_changes(self, displacements):
        """计算方向变化次数"""
        if len(displacements) < 2:
            return 0
            
        directions = displacements / (np.linalg.norm(displacements, axis=1, keepdims=True) + 1e-8)
        dot_products = np.sum(directions[1:] * directions[:-1], axis=1)
        direction_changes = np.sum(dot_products < 0.7)  # 角度变化大于45度
        
        return direction_changes
    
    def calculate_curvature(self, points):
        """计算轨迹曲率"""
        if len(points) < 3:
            return 0
            
        # 使用三点法计算曲率
        curvatures = []
        for i in range(1, len(points)-1):
            v1 = points[i] - points[i-1]
            v2 = points[i+1] - points[i]
            
            if np.linalg.norm(v1) > 0 and np.linalg.norm(v2) > 0:
                cos_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
                # 防止数值误差
                cos_angle = np.clip(cos_angle, -1, 1)
                angle = np.arccos(cos_angle)
                curvatures.append(angle)
        
        return np.mean(curvatures) if curvatures else 0

class GestureRecognizer:
    """基于传统机器学习的手势识别器"""
    
    def __init__(self):
        self.gesture_templates = {}
        self.isolation_forest = IsolationForest(contamination=0.1)
        self.feature_history = []
        
    def define_gesture_template(self, name, expected_trajectory, speed_range, curvature_range):
        """定义手势模板"""
        self.gesture_templates[name] = {
            'expected_trajectory': expected_trajectory,
            'speed_range': speed_range,
            'curvature_range': curvature_range
        }
    
    def recognize_gesture(self, trajectory_features, motion_histogram):
        """识别手势"""
        if trajectory_features is None:
            return "Unknown"
        
        best_match = "Unknown"
        best_score = 0
        
        for gesture_name, template in self.gesture_templates.items():
            score = self.calculate_similarity_score(trajectory_features, template)
            if score > best_score and score > 0.6:  # 相似度阈值
                best_score = score
                best_match = gesture_name
        
        return best_match
    
    def calculate_similarity_score(self, features, template):
        """计算与模板的相似度得分"""
        score = 0
        
        # 速度匹配
        if template['speed_range'][0] <= features['avg_speed'] <= template['speed_range'][1]:
            score += 0.3
        
        # 曲率匹配
        if template['curvature_range'][0] <= features['curvature'] <= template['curvature_range'][1]:
            score += 0.3
        
        # 方向变化匹配（简化版）
        if features['direction_changes'] < 5:  # 简单手势方向变化少
            score += 0.2
        
        # 总距离匹配
        if 50 <= features['total_distance'] <= 300:  # 合理的手势移动距离
            score += 0.2
            
        return score
    
    def detect_anomaly(self, features):
        """使用孤立森林检测异常手势"""
        if len(self.feature_history) < 10:
            self.feature_history.append([features['avg_speed'], features['curvature']])
            return False
        
        # 训练异常检测模型
        X = np.array(self.feature_history)
        self.isolation_forest.fit(X)
        
        current_feature = np.array([[features['avg_speed'], features['curvature']]])
        prediction = self.isolation_forest.predict(current_feature)
        
        return prediction[0] == -1

class EventBasedGestureSystem:
    """完整的事件相机手势识别系统"""
    
    def __init__(self, frame_shape=(480, 640)):
        self.event_simulator = EventCameraSimulator()
        self.feature_extractor = SpatioTemporalFeatureExtractor()
        self.gesture_recognizer = GestureRecognizer()
        self.frame_shape = frame_shape
        
        # 初始化手势模板
        self.initialize_gesture_templates()
        
        # 可视化
        self.visualization_buffer = np.zeros(frame_shape, dtype=np.uint8)
        
    def initialize_gesture_templates(self):
        """初始化预定义手势模板"""
        # 挥手手势 - 水平快速移动
        self.gesture_recognizer.define_gesture_template(
            "Wave", "horizontal", (80, 200), (0.1, 0.5)
        )
        
        # 圆圈手势 - 圆形轨迹
        self.gesture_recognizer.define_gesture_template(
            "Circle", "circular", (50, 150), (1.5, 2.5)
        )
        
        # 点击手势 - 短距离垂直移动
        self.gesture_recognizer.define_gesture_template(
            "Click", "vertical", (30, 100), (0.8, 1.5)
        )
    
    def process_frame(self, frame, timestamp):
        """处理每一帧"""
        # 转换为事件流
        events = self.event_simulator.frame_to_events(frame, timestamp)
        
        if events:
            # 提取特征
            self.feature_extractor.add_events(events)
            motion_histogram = self.feature_extractor.extract_motion_histogram(self.frame_shape)
            trajectory_features = self.feature_extractor.extract_trajectory_features()
            
            # 更新可视化
            self.update_visualization(events)
            
            # 识别手势
            if trajectory_features:
                gesture = self.gesture_recognizer.recognize_gesture(
                    trajectory_features, motion_histogram
                )
                
                # 异常检测
                is_anomaly = self.gesture_recognizer.detect_anomaly(trajectory_features)
                
                return gesture, trajectory_features, is_anomaly
        
        return "No Gesture", None, False
    
    def update_visualization(self, events):
        """更新事件可视化"""
        # 确保缓冲区是正确类型
        if self.visualization_buffer.dtype != np.uint8:
            self.visualization_buffer = np.zeros(self.frame_shape, dtype=np.uint8)
        
        # 事件衰减
        self.visualization_buffer = (self.visualization_buffer * 0.95).astype(np.uint8)
        
        for event in events:
            if 0 <= event['y'] < self.frame_shape[0] and 0 <= event['x'] < self.frame_shape[1]:
                if event['polarity'] > 0:
                    self.visualization_buffer[event['y'], event['x']] = 255  # 正事件 - 白色
                else:
                    self.visualization_buffer[event['y'], event['x']] = 100  # 负事件 - 灰色
    
    def get_visualization(self):
        """获取可视化图像"""
        # 确保图像是8位无符号整数类型
        if self.visualization_buffer.dtype != np.uint8:
            vis_buffer = np.clip(self.visualization_buffer, 0, 255).astype(np.uint8)
        else:
            vis_buffer = self.visualization_buffer
        
        # 确保是单通道图像
        if len(vis_buffer.shape) == 3:
            # 如果是三通道，转换为单通道
            vis_buffer = cv2.cvtColor(vis_buffer, cv2.COLOR_BGR2GRAY)
        
        # 应用颜色映射
        return cv2.applyColorMap(vis_buffer, cv2.COLORMAP_JET)

# 使用示例和测试代码
def main():
    """主测试函数"""
    # 初始化系统
    gesture_system = EventBasedGestureSystem()
    
    # 模拟摄像头输入
    cap = cv2.VideoCapture(0)
    
    print("事件相机手势识别系统启动...")
    print("支持手势: Wave(挥手), Circle(画圈), Click(点击)")
    print("按'q'退出")
    
    start_time = time.time()
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # 调整帧大小
        frame = cv2.resize(frame, (640, 480))
        current_time = time.time() - start_time
        
        # 处理帧
        gesture, features, anomaly = gesture_system.process_frame(frame, current_time)
        
        # 获取可视化
        event_visualization = gesture_system.get_visualization()
        
        # 显示结果
        result_frame = np.hstack([frame, event_visualization])
        
        # 添加文本信息
        cv2.putText(result_frame, f"Gesture: {gesture}", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        
        if features:
            cv2.putText(result_frame, f"Speed: {features['avg_speed']:.1f}", (10, 70), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
            cv2.putText(result_frame, f"Curvature: {features['curvature']:.2f}", (10, 110), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
        
        if anomaly:
            cv2.putText(result_frame, "ANOMALY DETECTED!", (10, 150), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)
        
        cv2.imshow('Event-based Gesture Recognition', result_frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()

def performance_analysis():
    """性能分析函数"""
    print("\n=== 系统性能分析 ===")
    print("技术优势:")
    print("1. 超低延迟: 事件相机响应时间<1ms")
    print("2. 高动态范围: 140dB vs 传统相机的60dB")
    print("3. 低功耗: 仅处理变化像素")
    print("4. 无运动模糊: 微秒级时间分辨率")
    print("5. 隐私保护: 不传输原始图像")
    
    print("\n应用场景:")
    print("• AR/VR手势交互")
    print("• 智能家居控制")
    print("• 车载手势识别")
    print("• 工业机器人控制")
    print("• 隐私敏感环境")

if __name__ == "__main__":
    main()
    performance_analysis()