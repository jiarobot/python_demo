import cv2
import numpy as np
import matplotlib
matplotlib.rc("font", family='Microsoft YaHei')
import matplotlib.pyplot as plt
from collections import deque, defaultdict
import time
import json
from datetime import datetime
import threading
from scipy.spatial import distance
from scipy import signal
import warnings
warnings.filterwarnings('ignore')

class DroneDetector:
    """无人机专用检测器"""
    
    def __init__(self):
        # 无人机特征参数
        self.min_size = 5
        self.max_size = 100
        self.aspect_ratio_range = (0.7, 1.3)  # 无人机通常接近正方形
        self.blink_frequency_range = (1, 20)  # 无人机LED闪烁频率(Hz)
        
        # 运动特征
        self.min_motion_magnitude = 2
        self.consistency_threshold = 0.7
        
        # 背景建模
        self.background_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=200, varThreshold=25, detectShadows=False
        )
        
        # 帧缓存用于闪烁检测
        self.frame_buffer = deque(maxlen=10)
        self.fps = 30
        
    def preprocess_frame(self, frame):
        """无人机专用预处理"""
        # 转换为灰度图
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # 多尺度高斯模糊
        blurred1 = cv2.GaussianBlur(gray, (3, 3), 0)
        blurred2 = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # 增强对比度
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        
        return enhanced, blurred1, blurred2
    
    def detect_moving_objects(self, frame):
        """检测运动物体"""
        # 应用背景减除
        fg_mask = self.background_subtractor.apply(frame)
        
        # 形态学操作
        kernel_open = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        kernel_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, kernel_open)
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, kernel_close)
        
        # 查找轮廓
        contours, _ = cv2.findContours(fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        detections = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if self.min_size < area < self.max_size:
                x, y, w, h = cv2.boundingRect(contour)
                
                # 检查宽高比
                aspect_ratio = w / h
                if self.aspect_ratio_range[0] <= aspect_ratio <= self.aspect_ratio_range[1]:
                    center = (x + w//2, y + h//2)
                    
                    detections.append({
                        'bbox': (x, y, w, h),
                        'center': center,
                        'area': area,
                        'aspect_ratio': aspect_ratio,
                        'contour': contour
                    })
        
        return detections, fg_mask
    
    def analyze_motion_pattern(self, current_frame, previous_frame):
        """分析运动模式"""
        # 计算光流
        flow = cv2.calcOpticalFlowFarneback(
            previous_frame, current_frame, None, 0.5, 3, 15, 3, 5, 1.2, 0
        )
        
        # 计算运动幅度和方向
        magnitude, angle = cv2.cartToPolar(flow[..., 0], flow[..., 1])
        
        return magnitude, angle, flow
    
    def detect_blinking_pattern(self, frame_buffer, detection_region):
        """检测LED闪烁模式"""
        if len(frame_buffer) < 5:
            return None
            
        x, y, w, h = detection_region
        intensity_history = []
        
        for frame in frame_buffer:
            # 提取检测区域
            roi = frame[y:y+h, x:x+w]
            if roi.size > 0:
                mean_intensity = np.mean(roi)
                intensity_history.append(mean_intensity)
        
        if len(intensity_history) < 5:
            return None
            
        # 计算FFT检测周期性
        intensities = np.array(intensity_history)
        fft = np.fft.fft(intensities - np.mean(intensities))
        freqs = np.fft.fftfreq(len(intensities), 1/self.fps)
        
        # 找到主要频率
        magnitude = np.abs(fft)
        valid_indices = (freqs > self.blink_frequency_range[0]) & (freqs < self.blink_frequency_range[1])
        
        if np.any(valid_indices):
            main_freq = freqs[valid_indices][np.argmax(magnitude[valid_indices])]
            return main_freq
        
        return None

class DroneTracker:
    """无人机跟踪器"""
    
    def __init__(self, max_distance=50, max_missing=15):
        self.max_distance = max_distance
        self.max_missing = max_missing
        self.next_id = 0
        self.tracks = {}
        
    def update(self, detections):
        """更新跟踪器"""
        # 更新现有轨迹
        for track_id, track in list(self.tracks.items()):
            track['missing'] += 1
            
            if track['missing'] > self.max_missing:
                del self.tracks[track_id]
                continue
                
            # 简单的速度预测
            if len(track['positions']) >= 2:
                last_pos = track['positions'][-1]
                prev_pos = track['positions'][-2]
                velocity = (last_pos[0]-prev_pos[0], last_pos[1]-prev_pos[1])
                predicted_pos = (last_pos[0] + velocity[0], last_pos[1] + velocity[1])
            else:
                predicted_pos = track['positions'][-1]
            
            # 寻找最近的检测
            if detections:
                centers = [det['center'] for det in detections]
                distances = [distance.euclidean(predicted_pos, center) for center in centers]
                min_distance = min(distances)
                min_index = distances.index(min_distance)
                
                if min_distance < self.max_distance:
                    detection = detections[min_index]
                    track['positions'].append(detection['center'])
                    track['missing'] = 0
                    track['bbox'] = detection['bbox']
                    track['last_seen'] = datetime.now()
                    
                    # 移除已匹配的检测
                    detections.pop(min_index)
        
        # 为剩余检测创建新轨迹
        for detection in detections:
            self.tracks[self.next_id] = {
                'positions': deque([detection['center']], maxlen=100),
                'bbox': detection['bbox'],
                'missing': 0,
                'created': datetime.now(),
                'last_seen': datetime.now(),
                'color': np.random.randint(0, 255, 3).tolist(),
                'classification': 'unknown'
            }
            self.next_id += 1
        
        return self.tracks

class RestrictedZone:
    """限制区域管理"""
    
    def __init__(self, zones_config=None):
        self.zones = zones_config or []
        self.alert_history = []
        
    def add_zone(self, name, polygon, alert_level="warning"):
        """添加限制区域"""
        self.zones.append({
            'name': name,
            'polygon': polygon,
            'alert_level': alert_level
        })
    
    def check_intrusion(self, position):
        """检查位置是否在限制区域内"""
        intrusions = []
        
        for zone in self.zones:
            if self._point_in_polygon(position, zone['polygon']):
                intrusions.append({
                    'zone': zone['name'],
                    'alert_level': zone['alert_level'],
                    'position': position,
                    'timestamp': datetime.now()
                })
        
        return intrusions
    
    def _point_in_polygon(self, point, polygon):
        """判断点是否在多边形内"""
        x, y = point
        n = len(polygon)
        inside = False
        
        p1x, p1y = polygon[0]
        for i in range(1, n + 1):
            p2x, p2y = polygon[i % n]
            if y > min(p1y, p2y):
                if y <= max(p1y, p2y):
                    if x <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or x <= xinters:
                            inside = not inside
            p1x, p1y = p2x, p2y
        
        return inside

class AlertSystem:
    """警报系统"""
    
    def __init__(self):
        self.alerts = deque(maxlen=100)
        self.alert_levels = {
            "info": (255, 255, 255),      # 白色
            "warning": (0, 255, 255),     # 黄色
            "critical": (0, 0, 255)       # 红色
        }
        
    def add_alert(self, message, level="info", track_id=None):
        """添加警报"""
        alert = {
            'timestamp': datetime.now(),
            'message': message,
            'level': level,
            'track_id': track_id
        }
        self.alerts.append(alert)
        
        # 控制台输出
        print(f"[{alert['timestamp'].strftime('%H:%M:%S')}] {level.upper()}: {message}")
        
        return alert
    
    def get_recent_alerts(self, count=10):
        """获取最近警报"""
        return list(self.alerts)[-count:]

class DroneSurveillanceSystem:
    """无人机监控系统主类"""
    
    def __init__(self, config_file=None):
        # 初始化组件
        self.detector = DroneDetector()
        self.tracker = DroneTracker()
        self.zone_manager = RestrictedZone()
        self.alert_system = AlertSystem()
        
        # 系统状态
        self.frame_count = 0
        self.processing_times = []
        self.is_running = False
        
        # 性能监控
        self.performance_stats = {
            'fps': [],
            'detection_count': [],
            'track_count': []
        }
        
        # 加载配置
        self.config = self._load_config(config_file)
        self._setup_zones()
        
        # 前一帧用于光流计算
        self.previous_frame = None
        
    def _load_config(self, config_file):
        """加载配置文件"""
        default_config = {
            "alert_zones": [
                {
                    "name": "核心禁区",
                    "points": [(100, 100), (700, 100), (700, 500), (100, 500)],
                    "alert_level": "critical"
                }
            ],
            "detection_params": {
                "min_size": 10,
                "max_size": 200
            }
        }
        
        # 这里可以扩展从文件加载配置
        return default_config
    
    def _setup_zones(self):
        """设置监控区域"""
        for zone_config in self.config["alert_zones"]:
            self.zone_manager.add_zone(
                zone_config["name"],
                zone_config["points"],
                zone_config["alert_level"]
            )
    
    def process_frame(self, frame):
        """处理视频帧"""
        start_time = time.time()
        
        # 预处理
        enhanced, blurred1, blurred2 = self.detector.preprocess_frame(frame)
        
        # 检测运动物体
        detections, motion_mask = self.detector.detect_moving_objects(enhanced)
        
        # 分析运动模式
        if self.previous_frame is not None:
            magnitude, angle, flow = self.detector.analyze_motion_pattern(
                self.previous_frame, enhanced
            )
        else:
            magnitude, angle, flow = None, None, None
        
        # 更新跟踪器
        tracks = self.tracker.update(detections.copy())
        
        # 检查区域入侵
        alerts = []
        for track_id, track in tracks.items():
            if track['missing'] == 0:  # 仅检查当前可见的目标
                position = track['positions'][-1]
                intrusions = self.zone_manager.check_intrusion(position)
                
                for intrusion in intrusions:
                    alert = self.alert_system.add_alert(
                        f"目标 {track_id} 进入 {intrusion['zone']}",
                        level=intrusion['alert_level'],
                        track_id=track_id
                    )
                    alerts.append(alert)
        
        # 分类目标
        self._classify_targets(tracks, detections)
        
        # 更新前一帧
        self.previous_frame = enhanced.copy()
        self.frame_count += 1
        
        # 计算处理时间
        processing_time = time.time() - start_time
        self.processing_times.append(processing_time)
        
        # 更新性能统计
        current_fps = 1.0 / processing_time if processing_time > 0 else 0
        self.performance_stats['fps'].append(current_fps)
        self.performance_stats['detection_count'].append(len(detections))
        self.performance_stats['track_count'].append(len(tracks))
        
        return {
            'frame': frame,
            'detections': detections,
            'tracks': tracks,
            'motion_mask': motion_mask,
            'alerts': alerts,
            'processing_time': processing_time,
            'fps': current_fps
        }
    
    def _classify_targets(self, tracks, detections):
        """分类目标类型"""
        for track_id, track in tracks.items():
            if len(track['positions']) > 10:
                positions = list(track['positions'])
                
                # 计算运动特征
                speeds = []
                directions = []
                
                for i in range(1, len(positions)):
                    dx = positions[i][0] - positions[i-1][0]
                    dy = positions[i][1] - positions[i-1][1]
                    speed = np.sqrt(dx**2 + dy**2)
                    direction = np.arctan2(dy, dx)
                    
                    speeds.append(speed)
                    directions.append(direction)
                
                if speeds:
                    avg_speed = np.mean(speeds)
                    speed_std = np.std(speeds)
                    direction_std = np.std(directions)
                    
                    # 基于特征分类
                    if avg_speed < 2:
                        classification = "静止物体"
                    elif 2 <= avg_speed < 10 and direction_std < 0.5:
                        classification = "鸟类"
                    elif avg_speed >= 5 and direction_std > 1.0:
                        classification = "无人机"
                    else:
                        classification = "未知飞行物"
                    
                    track['classification'] = classification
    
    def visualize_results(self, result):
        """可视化结果"""
        frame = result['frame'].copy()
        tracks = result['tracks']
        detections = result['detections']
        alerts = result['alerts']
        
        # 绘制限制区域
        for zone in self.zone_manager.zones:
            polygon = np.array(zone['polygon'], np.int32)
            color = self.alert_system.alert_levels[zone['alert_level']]
            cv2.polylines(frame, [polygon], True, color, 2)
            cv2.putText(frame, zone['name'], 
                       (polygon[0][0], polygon[0][1]-10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        
        # 绘制检测框
        for detection in detections:
            x, y, w, h = detection['bbox']
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
        
        # 绘制轨迹
        for track_id, track in tracks.items():
            if len(track['positions']) > 1:
                # 绘制轨迹线
                points = np.array(track['positions'], np.int32)
                cv2.polylines(frame, [points], False, track['color'], 2)
                
                # 绘制当前位置
                current_pos = track['positions'][-1]
                cv2.circle(frame, current_pos, 8, track['color'], -1)
                
                # 绘制ID和分类
                label = f"ID:{track_id} - {track['classification']}"
                cv2.putText(frame, label, 
                           (current_pos[0]+10, current_pos[1]),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, track['color'], 2)
                
                # 绘制边界框
                if 'bbox' in track:
                    x, y, w, h = track['bbox']
                    cv2.rectangle(frame, (x, y), (x+w, y+h), track['color'], 2)
        
        # 绘制警报信息
        recent_alerts = self.alert_system.get_recent_alerts(5)
        for i, alert in enumerate(recent_alerts):
            color = self.alert_system.alert_levels[alert['level']]
            alert_text = f"{alert['timestamp'].strftime('%H:%M:%S')}: {alert['message']}"
            cv2.putText(frame, alert_text, 
                       (10, 30 + i*25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        
        # 绘制性能信息
        fps_text = f"FPS: {result['fps']:.1f}"
        detection_text = f"检测: {len(detections)}"
        track_text = f"跟踪: {len(tracks)}"
        
        cv2.putText(frame, fps_text, (10, frame.shape[0]-60), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        cv2.putText(frame, detection_text, (10, frame.shape[0]-40), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        cv2.putText(frame, track_text, (10, frame.shape[0]-20), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        return frame

def create_test_video(output_path, duration=30, fps=30):
    """创建测试视频"""
    width, height = 800, 600
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    print("生成测试视频...")
    
    for frame_idx in range(duration * fps):
        # 创建背景
        frame = np.ones((height, width, 3), dtype=np.uint8) * 100
        
        # 添加一些纹理
        noise = np.random.randint(0, 30, (height, width, 3), dtype=np.uint8)
        frame = cv2.add(frame, noise)
        
        # 模拟无人机移动
        time_val = frame_idx / fps
        
        # 无人机1 - 直线飞行
        drone1_x = int(100 + time_val * 20)
        drone1_y = int(100 + np.sin(time_val) * 50)
        cv2.circle(frame, (drone1_x, drone1_y), 8, (0, 0, 255), -1)
        cv2.circle(frame, (drone1_x, drone1_y), 8, (255, 255, 255), 2)
        
        # 无人机2 - 圆形轨迹
        drone2_x = int(400 + 100 * np.cos(time_val))
        drone2_y = int(300 + 100 * np.sin(time_val))
        cv2.circle(frame, (drone2_x, drone2_y), 6, (255, 0, 0), -1)
        cv2.circle(frame, (drone2_x, drone2_y), 6, (255, 255, 255), 2)
        
        # 随机噪声目标
        if frame_idx % 30 == 0:
            noise_x = np.random.randint(0, width)
            noise_y = np.random.randint(0, height)
            cv2.circle(frame, (noise_x, noise_y), 4, (0, 255, 0), -1)
        
        out.write(frame)
    
    out.release()
    print(f"测试视频已生成: {output_path}")

def main():
    """主函数"""
    # 创建测试视频
    test_video_path = "drone_surveillance_test.avi"
    create_test_video(test_video_path, duration=20)
    
    # 初始化系统
    surveillance_system = DroneSurveillanceSystem()
    
    # 打开视频文件
    cap = cv2.VideoCapture(test_video_path)
    
    # 创建输出视频
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    out = cv2.VideoWriter('surveillance_output.avi', fourcc, 20.0, (800, 600))
    
    print("启动无人机监控系统...")
    print("按 'q' 退出, 'p' 暂停, 's' 保存截图")
    
    cv2.namedWindow('无人机监控系统', cv2.WINDOW_NORMAL)
    paused = False
    
    try:
        while True:
            if not paused:
                ret, frame = cap.read()
                if not ret:
                    print("视频结束")
                    break
                
                # 处理帧
                result = surveillance_system.process_frame(frame)
                
                # 可视化结果
                display_frame = surveillance_system.visualize_results(result)
                
                # 保存输出视频
                out.write(display_frame)
                
                # 显示结果
                cv2.imshow('无人机监控系统', display_frame)
                cv2.imshow('运动检测', result['motion_mask'])
            
            # 键盘控制
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('p'):
                paused = not paused
            elif key == ord('s'):
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                cv2.imwrite(f'screenshot_{timestamp}.jpg', display_frame)
                print(f"截图已保存: screenshot_{timestamp}.jpg")
    
    except KeyboardInterrupt:
        print("系统被用户中断")
    
    finally:
        # 释放资源
        cap.release()
        out.release()
        cv2.destroyAllWindows()
        
        # 生成报告
        generate_surveillance_report(surveillance_system)

def generate_surveillance_report(system):
    """生成监控报告"""
    print("\n" + "="*60)
    print("无人机监控系统运行报告")
    print("="*60)
    
    if system.processing_times:
        avg_fps = np.mean(system.performance_stats['fps'])
        avg_detection = np.mean(system.performance_stats['detection_count'])
        max_tracks = np.max(system.performance_stats['track_count'])
        
        print(f"运行时间: {system.frame_count / avg_fps:.1f} 秒")
        print(f"处理帧数: {system.frame_count}")
        print(f"平均FPS: {avg_fps:.1f}")
        print(f"平均检测目标: {avg_detection:.1f}")
        print(f"最大跟踪目标: {max_tracks}")
        print(f"总跟踪目标数: {system.tracker.next_id}")
    
    # 获取警报统计
    alerts = list(system.alert_system.alerts)
    if alerts:
        critical_alerts = [a for a in alerts if a['level'] == 'critical']
        warning_alerts = [a for a in alerts if a['level'] == 'warning']
        
        print(f"总警报数: {len(alerts)}")
        print(f"严重警报: {len(critical_alerts)}")
        print(f"警告警报: {len(warning_alerts)}")
    
    # 绘制性能图表
    plt.figure(figsize=(15, 10))
    
    plt.subplot(2, 3, 1)
    plt.plot(system.performance_stats['fps'])
    plt.title('处理帧率')
    plt.ylabel('FPS')
    plt.grid(True)
    
    plt.subplot(2, 3, 2)
    plt.plot(system.performance_stats['detection_count'])
    plt.title('检测目标数量')
    plt.ylabel('数量')
    plt.grid(True)
    
    plt.subplot(2, 3, 3)
    plt.plot(system.performance_stats['track_count'])
    plt.title('跟踪目标数量')
    plt.ylabel('数量')
    plt.grid(True)
    
    # 警报时间线
    plt.subplot(2, 3, 4)
    if alerts:
        alert_times = [a['timestamp'] for a in alerts]
        alert_levels = [a['level'] for a in alerts]
        
        colors = {'critical': 'red', 'warning': 'orange', 'info': 'blue'}
        for i, (time, level) in enumerate(zip(alert_times, alert_levels)):
            plt.scatter(time, i % 10, color=colors[level], label=level if i == 0 else "")
        
        plt.title('警报时间线')
        plt.xlabel('时间')
        plt.legend()
    
    plt.tight_layout()
    plt.savefig('surveillance_report.png', dpi=300, bbox_inches='tight')
    print("\n详细报告已保存为 'surveillance_report.png'")
    
    # 保存警报日志
    with open('alerts_log.json', 'w', encoding='utf-8') as f:
        alert_data = []
        for alert in alerts:
            alert_data.append({
                'timestamp': alert['timestamp'].isoformat(),
                'level': alert['level'],
                'message': alert['message'],
                'track_id': alert['track_id']
            })
        json.dump(alert_data, f, indent=2, ensure_ascii=False)
    
    print("警报日志已保存为 'alerts_log.json'")

if __name__ == "__main__":
    main()