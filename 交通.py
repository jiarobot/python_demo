import sys
import cv2
import numpy as np
import json
import time
from datetime import datetime
from collections import defaultdict, deque
from shapely.geometry import Point, Polygon, LineString
from shapely.ops import nearest_points
from scipy.spatial import distance
from sklearn.linear_model import LinearRegression
import pandas as pd

# 导入必要的库
try:
    from ultralytics import YOLO
    import torch
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                                QHBoxLayout, QPushButton, QLabel, QComboBox, 
                                QSpinBox, QDoubleSpinBox, QTextEdit, QTabWidget,
                                QGroupBox, QSlider, QCheckBox, QFileDialog, QProgressBar,
                                QSplitter, QFrame, QTableWidget, QTableWidgetItem, QHeaderView)
    from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QSettings
    from PyQt5.QtGui import QImage, QPixmap, QFont, QIcon, QColor
    import paho.mqtt.client as mqtt
except ImportError as e:
    print(f"缺少必要的库: {e}")
    print("请使用以下命令安装: pip install PyQt5 ultralytics paho-mqtt shapely scikit-learn scipy")
    sys.exit(1)

# 增强版交通分析器
class AdvancedTrafficAnalyzer:
    def __init__(self, model_path='car.pt', tracker_config='botsort.yaml'):
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        print(f"使用设备: {self.device}")
        
        self.model = YOLO(model_path)
        
        # 存储跟踪历史和轨迹
        self.track_history = defaultdict(lambda: deque(maxlen=100))
        self.trajectories = defaultdict(lambda: [])
        self.crossing_events = []
        self.lane_change_events = []
        self.speeding_events = []
        self.stop_events = []
        self.wrong_way_events = []
        self.congestion_events = []
        
        # 跟踪器配置
        self.tracker_config = tracker_config
        
        # 定义虚拟检测线
        self.lines = [
            [(100, 100), (600, 100)],
            [(100, 300), (600, 300)]
        ]
        
        # 定义检测方向
        self.line_directions = [1, -1]
        
        # 定义车道线
        self.lane_lines = [
            [(50, 0), (50, 500)],
            [(300, 0), (300, 500)],
            [(550, 0), (550, 500)]
        ]
        
        # 定义兴趣区域
        self.roi_polygons = [
            [(100, 100), (600, 100), (600, 400), (100, 400)]
        ]
        
        # 定义禁止停车区域
        self.no_stop_zones = [
            [(200, 200), (400, 200), (400, 300), (200, 300)]
        ]
        
        # 存储每个对象的最后位置和方向状态
        self.last_positions = {}
        self.crossing_states = defaultdict(lambda: defaultdict(lambda: False))
        self.lane_assignment = {}
        self.inside_roi = defaultdict(lambda: defaultdict(lambda: False))
        
        # 颜色映射
        self.colors = {}
        
        # 车速计算相关
        self.speed_estimates = defaultdict(lambda: [])
        self.pixel_to_meter_ratio = 0.05
        self.speed_limit = 60
        
        # 变道检测相关
        self.lane_change_threshold = 30
        self.lane_history = defaultdict(lambda: deque(maxlen=15))
        
        # 停车检测相关
        self.stop_threshold = 5
        self.stop_frames = defaultdict(int)
        self.stop_frame_threshold = 30
        
        # 性能优化相关
        self.last_processed_time = time.time()
        self.processing_times = deque(maxlen=30)
        self.frame_scale = 1.0
        
        # 计数相关
        self.vehicle_count = defaultdict(int)
        self.line_cross_count = defaultdict(int)
        
        # 轨迹预测相关
        self.motion_models = defaultdict(lambda: LinearRegression())
        self.position_history = defaultdict(lambda: deque(maxlen=10))
        
        # 白线检测相关
        self.white_line_threshold = 180
        self.white_line_min_length = 20
        self.white_lines = []
        
        # 拥堵检测相关
        self.congestion_threshold = 5  # 同一区域内的车辆数量阈值
        self.congestion_zones = [
            [(200, 200), (400, 200), (400, 300), (200, 300)]
        ]
        self.zone_vehicle_count = defaultdict(int)
        
        # MQTT相关
        self.mqtt_client = None
        self.mqtt_topic = "traffic/analysis"
        
    def set_mqtt_client(self, client, topic="traffic/analysis"):
        """设置MQTT客户端和主题"""
        self.mqtt_client = client
        self.mqtt_topic = topic
        
    def publish_event(self, event):
        """通过MQTT发布事件"""
        if self.mqtt_client and self.mqtt_client.connected:
            try:
                payload = json.dumps(event)
                self.mqtt_client.publish(self.mqtt_topic, payload)
                print(f"已发布事件到MQTT: {event['type']}")
            except Exception as e:
                print(f"MQTT发布错误: {e}")
                
    def detect_congestion(self, frame_idx):
        """检测交通拥堵"""
        events = []
        
        for zone_id, zone in enumerate(self.congestion_zones):
            vehicle_count = 0
            vehicle_ids = []
            
            # 计算当前区域内的车辆数量
            for track_id, positions in self.last_positions.items():
                if self.is_inside_polygon(positions, zone):
                    vehicle_count += 1
                    vehicle_ids.append(track_id)
            
            # 更新区域车辆计数
            prev_count = self.zone_vehicle_count[zone_id]
            self.zone_vehicle_count[zone_id] = vehicle_count
            
            # 检测拥堵开始
            if vehicle_count >= self.congestion_threshold and prev_count < self.congestion_threshold:
                event = {
                    'zone_id': zone_id,
                    'vehicle_count': vehicle_count,
                    'vehicle_ids': vehicle_ids,
                    'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'type': 'congestion_start',
                    'frame_idx': frame_idx
                }
                events.append(event)
                self.congestion_events.append(event)
                self.publish_event(event)
                
            # 检测拥堵结束
            elif vehicle_count < self.congestion_threshold and prev_count >= self.congestion_threshold:
                event = {
                    'zone_id': zone_id,
                    'vehicle_count': vehicle_count,
                    'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'type': 'congestion_end',
                    'frame_idx': frame_idx
                }
                events.append(event)
                self.congestion_events.append(event)
                self.publish_event(event)
                
        return events
        
    def set_detection_lines(self, lines, directions=None):
        self.lines = lines
        if directions is None:
            self.line_directions = [0] * len(lines)
        else:
            self.line_directions = directions
            
    def set_lane_lines(self, lane_lines):
        self.lane_lines = lane_lines
        
    def set_roi_polygons(self, roi_polygons):
        self.roi_polygons = roi_polygons
        
    def set_no_stop_zones(self, no_stop_zones):
        self.no_stop_zones = no_stop_zones
        
    def set_congestion_zones(self, congestion_zones, threshold=5):
        self.congestion_zones = congestion_zones
        self.congestion_threshold = threshold
        
    def detect_white_lines(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        _, binary = cv2.threshold(blurred, self.white_line_threshold, 255, cv2.THRESH_BINARY)
        edges = cv2.Canny(binary, 50, 150)
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=50, 
                               minLineLength=self.white_line_min_length, maxLineGap=10)
        
        white_lines = []
        if lines is not None:
            for line in lines:
                x1, y1, x2, y2 = line[0]
                white_lines.append([(x1, y1), (x2, y2)])
                
        return white_lines
        
    def is_crossing_line(self, point1, point2, line):
        line1 = LineString([point1, point2])
        line2 = LineString(line)
        
        if line1.intersects(line2):
            intersection = line1.intersection(line2)
            if intersection.geom_type == 'Point':
                return True, (int(intersection.x), int(intersection.y))
            elif intersection.geom_type == 'MultiPoint':
                point = nearest_points(line1, line2)[0]
                return True, (int(point.x), int(point.y))
                
        return False, None
        
    def is_inside_polygon(self, point, polygon):
        poly = Polygon(polygon)
        return poly.contains(Point(point))
        
    def detect_line_crossing(self, track_id, prev_point, current_point):
        events = []
        
        for i, line in enumerate(self.lines):
            if self.crossing_states[track_id][i]:
                continue
                
            is_crossing, cross_point = self.is_crossing_line(prev_point, current_point, line)
            
            if is_crossing:
                direction = 1 if current_point[1] > prev_point[1] else -1
                
                if self.line_directions[i] == 0 or direction == self.line_directions[i]:
                    event = {
                        'track_id': track_id,
                        'line_id': i,
                        'direction': direction,
                        'cross_point': cross_point,
                        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        'type': 'line_crossing'
                    }
                    events.append(event)
                    self.crossing_events.append(event)
                    self.line_cross_count[i] += 1
                    self.crossing_states[track_id][i] = True
                    self.publish_event(event)
                    
        return events
        
    def detect_lane_change(self, track_id, current_point, frame_idx):
        self.lane_history[track_id].append((current_point[0], frame_idx))
        
        if len(self.lane_history[track_id]) < 5:
            return False, None
        
        recent_points = list(self.lane_history[track_id])
        x_coords = [p[0] for p in recent_points]
        frames = [p[1] for p in recent_points]
        
        if len(x_coords) >= 5:
            X = np.array(frames).reshape(-1, 1)
            y = np.array(x_coords)
            
            try:
                model = LinearRegression().fit(X, y)
                slope = model.coef_[0]
                
                if abs(slope) > self.lane_change_threshold / 100:
                    direction = "right" if slope > 0 else "left"
                    
                    event = {
                        'track_id': track_id,
                        'direction': direction,
                        'slope': slope,
                        'start_frame': frames[0],
                        'end_frame': frames[-1],
                        'start_x': x_coords[0],
                        'end_x': x_coords[-1],
                        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        'type': 'lane_change'
                    }
                    
                    self.lane_change_events.append(event)
                    self.publish_event(event)
                    return True, event
            except:
                pass
        
        return False, None
        
    def detect_speeding(self, track_id, speed):
        if speed > self.speed_limit:
            event = {
                'track_id': track_id,
                'speed': speed,
                'speed_limit': self.speed_limit,
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'type': 'speeding'
            }
            self.speeding_events.append(event)
            self.publish_event(event)
            return True, event
        
        return False, None
        
    def detect_stop(self, track_id, current_point, frame_idx):
        if track_id not in self.last_positions:
            return False, None
        
        prev_point = self.last_positions[track_id]
        move_distance = distance.euclidean(prev_point, current_point)
        
        if move_distance < self.stop_threshold:
            self.stop_frames[track_id] += 1
        else:
            self.stop_frames[track_id] = 0
            
        in_no_stop_zone = any(self.is_inside_polygon(current_point, zone) for zone in self.no_stop_zones)
        
        if self.stop_frames[track_id] >= self.stop_frame_threshold and in_no_stop_zone:
            event = {
                'track_id': track_id,
                'position': current_point,
                'stop_frames': self.stop_frames[track_id],
                'in_no_stop_zone': in_no_stop_zone,
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'type': 'illegal_stop'
            }
            self.stop_events.append(event)
            self.stop_frames[track_id] = 0
            self.publish_event(event)
            return True, event
            
        return False, None
        
    def detect_wrong_way(self, track_id, prev_point, current_point, lane_id):
        direction = 1 if current_point[1] > prev_point[1] else -1
        
        expected_direction = -1 if lane_id in [0, 1] else 1
        
        if direction != expected_direction:
            event = {
                'track_id': track_id,
                'direction': direction,
                'expected_direction': expected_direction,
                'lane_id': lane_id,
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'type': 'wrong_way'
            }
            self.wrong_way_events.append(event)
            self.publish_event(event)
            return True, event
            
        return False, None
        
    def assign_lane(self, point):
        x, y = point
        
        for i, lane in enumerate(self.lane_lines):
            if i < len(self.lane_lines) - 1:
                left_line = self.lane_lines[i]
                right_line = self.lane_lines[i+1]
                
                if left_line[0][0] <= x <= right_line[0][0]:
                    return i
                    
        return -1
        
    def estimate_speed(self, track_id, current_point, fps):
        if track_id not in self.last_positions:
            return 0
        
        prev_point = self.last_positions[track_id]
        pixel_distance = np.sqrt((current_point[0] - prev_point[0])**2 + 
                                (current_point[1] - prev_point[1])**2)
        
        distance_m = pixel_distance * self.pixel_to_meter_ratio
        speed_mps = distance_m * fps
        speed_kmh = speed_mps * 3.6
        
        self.speed_estimates[track_id].append(speed_kmh)
        
        if len(self.speed_estimates[track_id]) > 5:
            return np.mean(list(self.speed_estimates[track_id])[-5:])
        
        return speed_kmh
        
    def predict_position(self, track_id, frames_ahead=5):
        if track_id not in self.position_history or len(self.position_history[track_id]) < 5:
            return None
            
        positions = list(self.position_history[track_id])
        X = np.arange(len(positions)).reshape(-1, 1)
        y_x = np.array([p[0] for p in positions])
        y_y = np.array([p[1] for p in positions])
        
        try:
            model_x = LinearRegression().fit(X, y_x)
            model_y = LinearRegression().fit(X, y_y)
            
            future_frame = len(positions) + frames_ahead
            pred_x = model_x.predict([[future_frame]])[0]
            pred_y = model_y.predict([[future_frame]])[0]
            
            return (int(pred_x), int(pred_y))
        except:
            return None
            
    def detect_and_track(self, video_path, output_path='output.mp4', show_video=True, save_video=True):
        cap = cv2.VideoCapture(video_path)
        
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        if self.frame_scale != 1.0:
            width = int(width * self.frame_scale)
            height = int(height * self.frame_scale)
        
        if save_video:
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        
        frame_idx = 0
        
        ret, first_frame = cap.read()
        if ret:
            self.white_lines = self.detect_white_lines(first_frame)
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        
        while cap.isOpened():
            success, frame = cap.read()
            
            if not success:
                break
                
            if self.frame_scale != 1.0:
                frame = cv2.resize(frame, (width, height))
                
            start_time = time.time()
            
            # 绘制检测线
            for i, line in enumerate(self.lines):
                color = (0, 255, 0)
                if self.line_directions[i] == 1:
                    color = (0, 0, 255)
                elif self.line_directions[i] == -1:
                    color = (255, 0, 0)
                    
                cv2.line(frame, line[0], line[1], color, 2)
                cv2.putText(frame, f"Line {i}", (line[0][0], line[0][1]-10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            
            # 绘制车道线
            for i, lane in enumerate(self.lane_lines):
                cv2.line(frame, lane[0], lane[1], (255, 255, 0), 2)
                cv2.putText(frame, f"Lane {i}", (lane[0][0], lane[0][1]-10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 2)
            
            # 绘制兴趣区域
            for i, roi in enumerate(self.roi_polygons):
                pts = np.array(roi, np.int32).reshape((-1, 1, 2))
                cv2.polylines(frame, [pts], True, (0, 255, 255), 2)
                cv2.putText(frame, f"ROI {i}", (roi[0][0], roi[0][1]-10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)
            
            # 绘制禁止停车区域
            for i, zone in enumerate(self.no_stop_zones):
                pts = np.array(zone, np.int32).reshape((-1, 1, 2))
                cv2.polylines(frame, [pts], True, (0, 0, 255), 2)
                cv2.putText(frame, f"No Stop {i}", (zone[0][0], zone[0][1]-10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
            
            # 绘制拥堵区域
            for i, zone in enumerate(self.congestion_zones):
                pts = np.array(zone, np.int32).reshape((-1, 1, 2))
                cv2.polylines(frame, [pts], True, (255, 0, 255), 2)
                cv2.putText(frame, f"Congestion {i}", (zone[0][0], zone[0][1]-10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 255), 2)
                # 显示当前区域车辆数量
                cv2.putText(frame, f"Vehicles: {self.zone_vehicle_count[i]}", 
                           (zone[0][0], zone[0][1]-30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 255), 2)
            
            # 绘制检测到的白线
            for i, line in enumerate(self.white_lines):
                cv2.line(frame, line[0], line[1], (255, 255, 255), 2)
                cv2.putText(frame, f"White {i}", (line[0][0], line[0][1]-10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
            
            # 使用YOLO进行跟踪
            results = self.model.track(
                frame, 
                persist=True,
                tracker=self.tracker_config,
                verbose=False,
                device=self.device,
                imgsz=640,
                conf=0.3,
                iou=0.5
            )
            
            # 获取检测结果
            if results[0].boxes is not None and results[0].boxes.id is not None:
                boxes = results[0].boxes.xywh.cpu()
                track_ids = results[0].boxes.id.int().cpu().tolist()
                class_ids = results[0].boxes.cls.int().cpu().tolist()
                confidences = results[0].boxes.conf.cpu().tolist()
                
                annotated_frame = results[0].plot()
                
                for track_id in track_ids:
                    if track_id not in self.colors:
                        self.colors[track_id] = tuple(np.random.randint(0, 255, 3).tolist())
                
                for box, track_id, class_id, confidence in zip(boxes, track_ids, class_ids, confidences):
                    x, y, w, h = box
                    center = (int(x), int(y))
                    
                    class_name = self.model.names[class_id]
                    self.vehicle_count[class_name] += 1
                    
                    lane_id = self.assign_lane(center)
                    self.lane_assignment[track_id] = lane_id
                    
                    for i, roi in enumerate(self.roi_polygons):
                        is_inside = self.is_inside_polygon(center, roi)
                        if is_inside and not self.inside_roi[track_id][i]:
                            self.inside_roi[track_id][i] = True
                        elif not is_inside and self.inside_roi[track_id][i]:
                            self.inside_roi[track_id][i] = False
                    
                    if track_id in self.last_positions:
                        prev_center = self.last_positions[track_id]
                        
                        events = self.detect_line_crossing(track_id, prev_center, center)
                        
                        lane_change_detected, lane_event = self.detect_lane_change(track_id, center, frame_idx)
                        
                        speed = self.estimate_speed(track_id, center, fps)
                        
                        speeding_detected, speed_event = self.detect_speeding(track_id, speed)
                        
                        stop_detected, stop_event = self.detect_stop(track_id, center, frame_idx)
                        
                        wrong_way_detected, wrong_way_event = self.detect_wrong_way(
                            track_id, prev_center, center, lane_id)
                        
                        for event in events:
                            cv2.circle(annotated_frame, event['cross_point'], 8, (0, 0, 255), -1)
                            cv2.putText(annotated_frame, f"Cross! ID:{track_id}", 
                                       (event['cross_point'][0]+10, event['cross_point'][1]), 
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                        
                        if lane_change_detected:
                            cv2.putText(annotated_frame, f"Lane Change! ID:{track_id}", 
                                       (int(x - w/2), int(y - h/2 - 30)), 
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 255), 2)
                        
                        if speeding_detected:
                            cv2.putText(annotated_frame, f"Speeding! {speed:.1f}km/h ID:{track_id}", 
                                       (int(x - w/2), int(y - h/2 - 60)), 
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)
                        
                        if stop_detected:
                            cv2.putText(annotated_frame, f"Illegal Stop! ID:{track_id}", 
                                       (int(x - w/2), int(y - h/2 - 90)), 
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                        
                        if wrong_way_detected:
                            cv2.putText(annotated_frame, f"Wrong Way! ID:{track_id}", 
                                       (int(x - w/2), int(y - h/2 - 120)), 
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
                    
                    self.last_positions[track_id] = center
                    self.track_history[track_id].append(center)
                    self.position_history[track_id].append(center)
                    self.trajectories[track_id].append({
                        'frame': frame_idx,
                        'center': center,
                        'class_id': class_id,
                        'confidence': confidence,
                        'lane_id': lane_id,
                        'speed': self.estimate_speed(track_id, center, fps) if track_id in self.last_positions else 0
                    })
                    
                    points = np.array(self.track_history[track_id], dtype=np.int32)
                    if len(points) > 1:
                        cv2.polylines(annotated_frame, [points], isClosed=False, 
                                     color=self.colors[track_id], thickness=2)
                    
                    future_pos = self.predict_position(track_id, frames_ahead=10)
                    if future_pos:
                        cv2.circle(annotated_frame, future_pos, 5, (0, 255, 255), -1)
                        cv2.line(annotated_frame, center, future_pos, (0, 255, 255), 2)
                    
                    label = f"ID:{track_id} {self.model.names[class_id]}:{confidence:.2f}"
                    cv2.putText(annotated_frame, label, (int(x - w/2), int(y - h/2 - 10)), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, self.colors[track_id], 2)
                    
                    if lane_id >= 0:
                        cv2.putText(annotated_frame, f"Lane:{lane_id}", 
                                   (int(x - w/2), int(y + h/2 + 20)), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                    
                    if track_id in self.last_positions:
                        speed = self.estimate_speed(track_id, center, fps)
                        cv2.putText(annotated_frame, f"{speed:.1f} km/h", 
                                   (int(x - w/2), int(y + h/2 + 40)), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)
            else:
                annotated_frame = frame
                
            # 检测拥堵
            congestion_events = self.detect_congestion(frame_idx)
            for event in congestion_events:
                zone_id = event['zone_id']
                zone = self.congestion_zones[zone_id]
                center_x = sum(p[0] for p in zone) // len(zone)
                center_y = sum(p[1] for p in zone) // len(zone)
                
                if event['type'] == 'congestion_start':
                    cv2.putText(annotated_frame, f"Congestion Start! Zone:{zone_id}", 
                               (center_x - 100, center_y), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 255), 2)
                else:
                    cv2.putText(annotated_frame, f"Congestion End! Zone:{zone_id}", 
                               (center_x - 100, center_y), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 255), 2)
                
            processing_time = time.time() - start_time
            self.processing_times.append(processing_time)
            avg_processing_time = np.mean(self.processing_times) if self.processing_times else 0
            
            # 显示统计信息
            cv2.putText(annotated_frame, f"Frame: {frame_idx}/{frame_count}", (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(annotated_frame, f"Crossing Events: {len(self.crossing_events)}", (10, 60), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            cv2.putText(annotated_frame, f"Lane Changes: {len(self.lane_change_events)}", (10, 90), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 255), 2)
            cv2.putText(annotated_frame, f"Speeding: {len(self.speeding_events)}", (10, 120), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)
            cv2.putText(annotated_frame, f"Illegal Stops: {len(self.stop_events)}", (10, 150), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            cv2.putText(annotated_frame, f"Wrong Way: {len(self.wrong_way_events)}", (10, 180), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
            cv2.putText(annotated_frame, f"Congestion: {len(self.congestion_events)}", (10, 210), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 255), 2)
            cv2.putText(annotated_frame, f"FPS: {1/avg_processing_time:.1f}", (10, 240), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
            
            y_offset = 270
            for i, (class_name, count) in enumerate(self.vehicle_count.items()):
                if i < 5:
                    cv2.putText(annotated_frame, f"{class_name}: {count}", (10, y_offset), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                    y_offset += 30
            
            y_offset = 270
            for i, count in self.line_cross_count.items():
                if i < 5:
                    cv2.putText(annotated_frame, f"Line {i}: {count}", (width - 200, y_offset), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                    y_offset += 30
            
            if show_video:
                cv2.imshow("Advanced Traffic Analyzer", annotated_frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            
            if save_video:
                out.write(annotated_frame)
                
            frame_idx += 1
            print(f"处理进度: {frame_idx}/{frame_count}帧, FPS: {1/avg_processing_time:.1f}", end='\r')
        
        cap.release()
        if save_video:
            out.release()
        cv2.destroyAllWindows()
        
        print(f"\n视频处理完成! 共处理{frame_idx}帧, 检测到{len(self.crossing_events)}次压线事件, "
              f"{len(self.lane_change_events)}次变道事件, {len(self.speeding_events)}次超速事件, "
              f"{len(self.stop_events)}次违规停车事件, {len(self.wrong_way_events)}次逆行事件, "
              f"{len(self.congestion_events)}次拥堵事件")
        
    def get_trajectories(self):
        return dict(self.trajectories)
    
    def get_crossing_events(self):
        return self.crossing_events
    
    def get_lane_change_events(self):
        return self.lane_change_events
    
    def get_speeding_events(self):
        return self.speeding_events
    
    def get_stop_events(self):
        return self.stop_events
    
    def get_wrong_way_events(self):
        return self.wrong_way_events
    
    def get_congestion_events(self):
        return self.congestion_events
    
    def get_speed_estimates(self):
        return {k: np.mean(v) if v else 0 for k, v in self.speed_estimates.items()}
    
    def get_vehicle_counts(self):
        return dict(self.vehicle_count)
    
    def get_line_cross_counts(self):
        return dict(self.line_cross_count)
    
    def save_data(self, trajectories_path='trajectories.json', events_path='events.json', 
                 speeds_path='speeds.json', counts_path='counts.json'):
        trajectories = {str(k): v for k, v in self.get_trajectories().items()}
        with open(trajectories_path, 'w') as f:
            json.dump(trajectories, f, indent=2)
        
        all_events = {
            'crossing_events': self.crossing_events,
            'lane_change_events': self.lane_change_events,
            'speeding_events': self.speeding_events,
            'stop_events': self.stop_events,
            'wrong_way_events': self.wrong_way_events,
            'congestion_events': self.congestion_events
        }
        with open(events_path, 'w') as f:
            json.dump(all_events, f, indent=2)
            
        speeds = {str(k): np.mean(v) if v else 0 for k, v in self.speed_estimates.items()}
        with open(speeds_path, 'w') as f:
            json.dump(speeds, f, indent=2)
            
        counts = {
            'vehicle_counts': self.vehicle_count,
            'line_cross_counts': self.line_cross_count
        }
        with open(counts_path, 'w') as f:
            json.dump(counts, f, indent=2)
            
        print(f"轨迹数据已保存到: {trajectories_path}")
        print(f"事件数据已保存到: {events_path}")
        print(f"速度数据已保存到: {speeds_path}")
        print(f"计数数据已保存到: {counts_path}")
        
    def load_data(self, trajectories_path='trajectories.json', events_path='events.json',
                 speeds_path='speeds.json', counts_path='counts.json'):
        with open(trajectories_path, 'r') as f:
            trajectories = json.load(f)
        self.trajectories = defaultdict(lambda: [], {int(k): v for k, v in trajectories.items()})
        
        with open(events_path, 'r') as f:
            all_events = json.load(f)
        self.crossing_events = all_events.get('crossing_events', [])
        self.lane_change_events = all_events.get('lane_change_events', [])
        self.speeding_events = all_events.get('speeding_events', [])
        self.stop_events = all_events.get('stop_events', [])
        self.wrong_way_events = all_events.get('wrong_way_events', [])
        self.congestion_events = all_events.get('congestion_events', [])
            
        with open(speeds_path, 'r') as f:
            speeds = json.load(f)
        self.speed_estimates = defaultdict(lambda: [], {int(k): [v] for k, v in speeds.items()})
        
        with open(counts_path, 'r') as f:
            counts = json.load(f)
        self.vehicle_count = defaultdict(int, counts.get('vehicle_counts', {}))
        self.line_cross_count = defaultdict(int, counts.get('line_cross_counts', {}))
            
        print(f"已从文件加载数据")
        
    def generate_report(self, output_path='traffic_report.html'):
        html_content = f"""
        <html>
        <head>
            <title>交通分析报告</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1, h2 {{ color: #333; }}
                table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                .summary {{ background-color: #f9f9f9; padding: 15px; border-radius: 5px; }}
            </style>
        </head>
        <body>
            <h1>交通分析报告</h1>
            <div class="summary">
                <h2>摘要</h2>
                <p>总车辆数: {sum(self.vehicle_count.values())}</p>
                <p>压线事件: {len(self.crossing_events)}</p>
                <p>变道事件: {len(self.lane_change_events)}</p>
                <p>超速事件: {len(self.speeding_events)}</p>
                <p>违规停车事件: {len(self.stop_events)}</p>
                <p>逆行事件: {len(self.wrong_way_events)}</p>
                <p>拥堵事件: {len(self.congestion_events)}</p>
            </div>
            
            <h2>车辆类型统计</h2>
            <table>
                <tr><th>车辆类型</th><th>数量</th></tr>
        """
        
        for class_name, count in self.vehicle_count.items():
            html_content += f"<tr><td>{class_name}</td><td>{count}</td></tr>"
            
        html_content += """
            </table>
            
            <h2>线交叉统计</h2>
            <table>
                <tr><th>线ID</th><th>交叉次数</th></tr>
        """
        
        for line_id, count in self.line_cross_count.items():
            html_content += f"<tr><td>{line_id}</td><td>{count}</td></tr>"
            
        html_content += """
            </table>
            
            <h2>速度统计</h2>
            <table>
                <tr><th>车辆ID</th><th>平均速度 (km/h)</th></tr>
        """
        
        speeds = self.get_speed_estimates()
        for track_id, speed in speeds.items():
            html_content += f"<tr><td>{track_id}</td><td>{speed:.1f}</td></tr>"
            
        html_content += """
            </table>
        </body>
        </html>
        """
        
        with open(output_path, 'w') as f:
            f.write(html_content)
            
        print(f"交通分析报告已保存到: {output_path}")
        
    def visualize_trajectories(self, output_path='trajectories_visualization.png'):
        plt.figure(figsize=(16, 12))
        trajectories_copy = dict(self.trajectories)
        for i, line in enumerate(self.lines):
            x_values = [line[0][0], line[1][0]]
            y_values = [line[0][1], line[1][1]]
            
            if self.line_directions[i] == 1:
                color = 'red'
                label = f'Line {i} (Down)'
            elif self.line_directions[i] == -1:
                color = 'blue'
                label = f'Line {i} (Up)'
            else:
                color = 'green'
                label = f'Line {i} (Both)'
                
            plt.plot(x_values, y_values, color=color, linewidth=3, label=label)
        
        for i, lane in enumerate(self.lane_lines):
            x_values = [lane[0][0], lane[1][0]]
            y_values = [lane[0][1], lane[1][1]]
            plt.plot(x_values, y_values, color='cyan', linewidth=2, linestyle='--', label=f'Lane {i}' if i == 0 else "")
        
        for i, roi in enumerate(self.roi_polygons):
            x_values = [p[0] for p in roi] + [roi[0][0]]
            y_values = [p[1] for p in roi] + [roi[0][1]]
            plt.plot(x_values, y_values, color='yellow', linewidth=2, linestyle=':', label=f'ROI {i}' if i == 0 else "")
        
        for i, zone in enumerate(self.no_stop_zones):
            x_values = [p[0] for p in zone] + [zone[0][0]]
            y_values = [p[1] for p in zone] + [zone[0][1]]
            plt.plot(x_values, y_values, color='red', linewidth=2, linestyle='-.', label=f'No Stop {i}' if i == 0 else "")
        
        for i, zone in enumerate(self.congestion_zones):
            x_values = [p[0] for p in zone] + [zone[0][0]]
            y_values = [p[1] for p in zone] + [zone[0][1]]
            plt.plot(x_values, y_values, color='purple', linewidth=2, linestyle=':', label=f'Congestion {i}' if i == 0 else "")
        
        for track_id, points in trajectories_copy.items():  # 使用副本而不是原始字典
            if not points:
                continue
                
            x_coords = [p['center'][0] for p in points]
            y_coords = [p['center'][1] for p in points]
            
            # 获取颜色并转换为 matplotlib 接受的格式
            color = self.colors.get(track_id, (128, 128, 128))  # 默认灰色
            # 将 0-255 的 RGB 转换为 0-1 的浮点数
            color = (color[0] / 255.0, color[1] / 255.0, color[2] / 255.0)
            
            plt.plot(x_coords, y_coords, color=color, 
                    alpha=0.7, linewidth=1, label=f'ID {track_id}')
            
            plt.scatter(x_coords[0], y_coords[0], color='green', s=50, marker='o')
            plt.scatter(x_coords[-1], y_coords[-1], color='red', s=50, marker='s')
        
        for event in self.crossing_events:
            plt.scatter(event['cross_point'][0], event['cross_point'][1], 
                       color='yellow', s=100, marker='*', edgecolors='black')
            plt.text(event['cross_point'][0]+10, event['cross_point'][1], 
                    f"ID:{event['track_id']}", fontsize=8)
        
        for event in self.lane_change_events:
            track_points = self.trajectories[event['track_id']]
            frame_points = [p for p in track_points if event['start_frame'] <= p['frame'] <= event['end_frame']]
            if frame_points:
                x_coords = [p['center'][0] for p in frame_points]
                y_coords = [p['center'][1] for p in frame_points]
                plt.plot(x_coords, y_coords, color='purple', linewidth=3, alpha=0.7)
                plt.text(x_coords[len(x_coords)//2], y_coords[len(y_coords)//2], 
                        f"Lane Change ID:{event['track_id']}", fontsize=8, color='purple')
        
        for event in self.speeding_events:
            track_points = self.trajectories[event['track_id']]
            if track_points:
                point = track_points[-1]['center']
                plt.scatter(point[0], point[1], color='orange', s=150, marker='X')
                plt.text(point[0]+10, point[1], f"Speeding ID:{event['track_id']}", fontsize=8, color='orange')
                
        for event in self.congestion_events:
            zone_id = event['zone_id']
            zone = self.congestion_zones[zone_id]
            center_x = sum(p[0] for p in zone) // len(zone)
            center_y = sum(p[1] for p in zone) // len(zone)
            
            if event['type'] == 'congestion_start':
                plt.scatter(center_x, center_y, color='red', s=200, marker='X')
                plt.text(center_x+10, center_y, f"Congestion Start Zone:{zone_id}", fontsize=8, color='red')
            else:
                plt.scatter(center_x, center_y, color='green', s=200, marker='X')
                plt.text(center_x+10, center_y, f"Congestion End Zone:{zone_id}", fontsize=8, color='green')
        
        plt.xlabel('X Coordinate')
        plt.ylabel('Y Coordinate')
        plt.title('Traffic Analysis: Object Trajectories and Events')
        plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        plt.grid(True, alpha=0.3)
        plt.gca().invert_yaxis()
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.show()
        
        print(f"轨迹可视化已保存到: {output_path}")


# MQTT客户端类
class MQTTClient:
    def __init__(self, client_id="traffic_analyzer"):
        self.client = mqtt.Client(client_id=client_id)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.connected = False
        self.subscribed_topics = []
        
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print("MQTT连接成功")
            self.connected = True
            # 重新订阅所有主题
            for topic in self.subscribed_topics:
                self.client.subscribe(topic)
        else:
            print(f"MQTT连接失败，错误代码: {rc}")
            self.connected = False
            
    def on_message(self, client, userdata, msg):
        print(f"收到消息: {msg.topic} {str(msg.payload)}")
        
    def connect(self, host="test.mosquitto.org", port=8082, keepalive=60):
        try:
            self.client.connect(host, port, keepalive)
            self.client.loop_start()
            return True
        except Exception as e:
            print(f"MQTT连接错误: {e}")
            return False
            
    def disconnect(self):
        self.client.loop_stop()
        self.client.disconnect()
        self.connected = False
        
    def publish(self, topic, payload, qos=0, retain=False):
        if self.connected:
            result = self.client.publish(topic, payload, qos, retain)
            return result.rc == mqtt.MQTT_ERR_SUCCESS
        return False
        
    def subscribe(self, topic, qos=0):
        if self.connected:
            result = self.client.subscribe(topic, qos)
            if result[0] == mqtt.MQTT_ERR_SUCCESS:
                if topic not in self.subscribed_topics:
                    self.subscribed_topics.append(topic)
                return True
        return False


# 视频处理线程
class VideoProcessor(QThread):
    # 定义信号
    frame_processed = pyqtSignal(np.ndarray)
    processing_finished = pyqtSignal()
    progress_updated = pyqtSignal(int, int)
    stats_updated = pyqtSignal(dict)
    
    def __init__(self, analyzer, video_path, output_path, show_video, save_video):
        super().__init__()
        self.analyzer = analyzer
        self.video_path = video_path
        self.output_path = output_path
        self.show_video = show_video
        self.save_video = save_video
        self.is_running = False
        
    def run(self):
        self.is_running = True
        cap = cv2.VideoCapture(self.video_path)
        
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        if self.analyzer.frame_scale != 1.0:
            width = int(width * self.analyzer.frame_scale)
            height = int(height * self.analyzer.frame_scale)
        
        if self.save_video:
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(self.output_path, fourcc, fps, (width, height))
        
        frame_idx = 0
        
        ret, first_frame = cap.read()
        if ret:
            self.analyzer.white_lines = self.analyzer.detect_white_lines(first_frame)
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        
        while self.is_running and cap.isOpened():
            success, frame = cap.read()
            
            if not success:
                break
                
            if self.analyzer.frame_scale != 1.0:
                frame = cv2.resize(frame, (width, height))
                
            start_time = time.time()
            
            # 绘制检测线和区域
            for i, line in enumerate(self.analyzer.lines):
                color = (0, 255, 0)
                if self.analyzer.line_directions[i] == 1:
                    color = (0, 0, 255)
                elif self.analyzer.line_directions[i] == -1:
                    color = (255, 0, 0)
                    
                cv2.line(frame, line[0], line[1], color, 2)
                cv2.putText(frame, f"Line {i}", (line[0][0], line[0][1]-10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            
            for i, lane in enumerate(self.analyzer.lane_lines):
                cv2.line(frame, lane[0], lane[1], (255, 255, 0), 2)
                cv2.putText(frame, f"Lane {i}", (lane[0][0], lane[0][1]-10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 2)
            
            for i, roi in enumerate(self.analyzer.roi_polygons):
                pts = np.array(roi, np.int32).reshape((-1, 1, 2))
                cv2.polylines(frame, [pts], True, (0, 255, 255), 2)
                cv2.putText(frame, f"ROI {i}", (roi[0][0], roi[0][1]-10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)
            
            for i, zone in enumerate(self.analyzer.no_stop_zones):
                pts = np.array(zone, np.int32).reshape((-1, 1, 2))
                cv2.polylines(frame, [pts], True, (0, 0, 255), 2)
                cv2.putText(frame, f"No Stop {i}", (zone[0][0], zone[0][1]-10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
            
            for i, zone in enumerate(self.analyzer.congestion_zones):
                pts = np.array(zone, np.int32).reshape((-1, 1, 2))
                cv2.polylines(frame, [pts], True, (255, 0, 255), 2)
                cv2.putText(frame, f"Congestion {i}", (zone[0][0], zone[0][1]-10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 255), 2)
                cv2.putText(frame, f"Vehicles: {self.analyzer.zone_vehicle_count[i]}", 
                           (zone[0][0], zone[0][1]-30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 255), 2)
            
            for i, line in enumerate(self.analyzer.white_lines):
                cv2.line(frame, line[0], line[1], (255, 255, 255), 2)
                cv2.putText(frame, f"White {i}", (line[0][0], line[0][1]-10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
            
            # 使用YOLO进行跟踪
            results = self.analyzer.model.track(
                frame, 
                persist=True,
                tracker=self.analyzer.tracker_config,
                verbose=False,
                device=self.analyzer.device,
                imgsz=640,
                conf=0.3,
                iou=0.5
            )
            
            annotated_frame = frame.copy()
            
            if results[0].boxes is not None and results[0].boxes.id is not None:
                boxes = results[0].boxes.xywh.cpu()
                track_ids = results[0].boxes.id.int().cpu().tolist()
                class_ids = results[0].boxes.cls.int().cpu().tolist()
                confidences = results[0].boxes.conf.cpu().tolist()
                
                annotated_frame = results[0].plot()
                
                for track_id in track_ids:
                    if track_id not in self.analyzer.colors:
                        self.analyzer.colors[track_id] = tuple(np.random.randint(0, 255, 3).tolist())
                
                for box, track_id, class_id, confidence in zip(boxes, track_ids, class_ids, confidences):
                    x, y, w, h = box
                    center = (int(x), int(y))
                    
                    class_name = self.analyzer.model.names[class_id]
                    self.analyzer.vehicle_count[class_name] += 1
                    
                    lane_id = self.analyzer.assign_lane(center)
                    self.analyzer.lane_assignment[track_id] = lane_id
                    
                    for i, roi in enumerate(self.analyzer.roi_polygons):
                        is_inside = self.analyzer.is_inside_polygon(center, roi)
                        if is_inside and not self.analyzer.inside_roi[track_id][i]:
                            self.analyzer.inside_roi[track_id][i] = True
                        elif not is_inside and self.analyzer.inside_roi[track_id][i]:
                            self.analyzer.inside_roi[track_id][i] = False
                    
                    if track_id in self.analyzer.last_positions:
                        prev_center = self.analyzer.last_positions[track_id]
                        
                        events = self.analyzer.detect_line_crossing(track_id, prev_center, center)
                        
                        lane_change_detected, lane_event = self.analyzer.detect_lane_change(track_id, center, frame_idx)
                        
                        speed = self.analyzer.estimate_speed(track_id, center, fps)
                        
                        speeding_detected, speed_event = self.analyzer.detect_speeding(track_id, speed)
                        
                        stop_detected, stop_event = self.analyzer.detect_stop(track_id, center, frame_idx)
                        
                        wrong_way_detected, wrong_way_event = self.analyzer.detect_wrong_way(
                            track_id, prev_center, center, lane_id)
                        
                        for event in events:
                            cv2.circle(annotated_frame, event['cross_point'], 8, (0, 0, 255), -1)
                            cv2.putText(annotated_frame, f"Cross! ID:{track_id}", 
                                       (event['cross_point'][0]+10, event['cross_point'][1]), 
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                        
                        if lane_change_detected:
                            cv2.putText(annotated_frame, f"Lane Change! ID:{track_id}", 
                                       (int(x - w/2), int(y - h/2 - 30)), 
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 255), 2)
                        
                        if speeding_detected:
                            cv2.putText(annotated_frame, f"Speeding! {speed:.1f}km/h ID:{track_id}", 
                                       (int(x - w/2), int(y - h/2 - 60)), 
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)
                        
                        if stop_detected:
                            cv2.putText(annotated_frame, f"Illegal Stop! ID:{track_id}", 
                                       (int(x - w/2), int(y - h/2 - 90)), 
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                        
                        if wrong_way_detected:
                            cv2.putText(annotated_frame, f"Wrong Way! ID:{track_id}", 
                                       (int(x - w/2), int(y - h/2 - 120)), 
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
                    
                    self.analyzer.last_positions[track_id] = center
                    self.analyzer.track_history[track_id].append(center)
                    self.analyzer.position_history[track_id].append(center)
                    self.analyzer.trajectories[track_id].append({
                        'frame': frame_idx,
                        'center': center,
                        'class_id': class_id,
                        'confidence': confidence,
                        'lane_id': lane_id,
                        'speed': self.analyzer.estimate_speed(track_id, center, fps) if track_id in self.analyzer.last_positions else 0
                    })
                    
                    points = np.array(self.analyzer.track_history[track_id], dtype=np.int32)
                    if len(points) > 1:
                        cv2.polylines(annotated_frame, [points], isClosed=False, 
                                     color=self.analyzer.colors[track_id], thickness=2)
                    
                    future_pos = self.analyzer.predict_position(track_id, frames_ahead=10)
                    if future_pos:
                        cv2.circle(annotated_frame, future_pos, 5, (0, 255, 255), -1)
                        cv2.line(annotated_frame, center, future_pos, (0, 255, 255), 2)
                    
                    label = f"ID:{track_id} {self.analyzer.model.names[class_id]}:{confidence:.2f}"
                    cv2.putText(annotated_frame, label, (int(x - w/2), int(y - h/2 - 10)), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, self.analyzer.colors[track_id], 2)
                    
                    if lane_id >= 0:
                        cv2.putText(annotated_frame, f"Lane:{lane_id}", 
                                   (int(x - w/2), int(y + h/2 + 20)), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                    
                    if track_id in self.analyzer.last_positions:
                        speed = self.analyzer.estimate_speed(track_id, center, fps)
                        cv2.putText(annotated_frame, f"{speed:.1f} km/h", 
                                   (int(x - w/2), int(y + h/2 + 40)), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)
            
            # 检测拥堵
            congestion_events = self.analyzer.detect_congestion(frame_idx)
            for event in congestion_events:
                zone_id = event['zone_id']
                zone = self.analyzer.congestion_zones[zone_id]
                center_x = sum(p[0] for p in zone) // len(zone)
                center_y = sum(p[1] for p in zone) // len(zone)
                
                if event['type'] == 'congestion_start':
                    cv2.putText(annotated_frame, f"Congestion Start! Zone:{zone_id}", 
                               (center_x - 100, center_y), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 255), 2)
                else:
                    cv2.putText(annotated_frame, f"Congestion End! Zone:{zone_id}", 
                               (center_x - 100, center_y), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 255), 2)
                
            processing_time = time.time() - start_time
            self.analyzer.processing_times.append(processing_time)
            avg_processing_time = np.mean(self.analyzer.processing_times) if self.analyzer.processing_times else 0
            
            # 显示统计信息
            cv2.putText(annotated_frame, f"Frame: {frame_idx}/{frame_count}", (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(annotated_frame, f"Crossing Events: {len(self.analyzer.crossing_events)}", (10, 60), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            cv2.putText(annotated_frame, f"Lane Changes: {len(self.analyzer.lane_change_events)}", (10, 90), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 255), 2)
            cv2.putText(annotated_frame, f"Speeding: {len(self.analyzer.speeding_events)}", (10, 120), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)
            cv2.putText(annotated_frame, f"Illegal Stops: {len(self.analyzer.stop_events)}", (10, 150), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            cv2.putText(annotated_frame, f"Wrong Way: {len(self.analyzer.wrong_way_events)}", (10, 180), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
            cv2.putText(annotated_frame, f"Congestion: {len(self.analyzer.congestion_events)}", (10, 210), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 255), 2)
            cv2.putText(annotated_frame, f"FPS: {1/avg_processing_time:.1f}", (10, 240), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
            
            y_offset = 270
            for i, (class_name, count) in enumerate(self.analyzer.vehicle_count.items()):
                if i < 5:
                    cv2.putText(annotated_frame, f"{class_name}: {count}", (10, y_offset), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                    y_offset += 30
            
            y_offset = 270
            for i, count in self.analyzer.line_cross_count.items():
                if i < 5:
                    cv2.putText(annotated_frame, f"Line {i}: {count}", (width - 200, y_offset), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                    y_offset += 30
            
            if self.save_video:
                out.write(annotated_frame)
                
            # 发送处理后的帧和统计信息
            self.frame_processed.emit(annotated_frame)
            self.progress_updated.emit(frame_idx, frame_count)
            
            stats = {
                'crossing_events': len(self.analyzer.crossing_events),
                'lane_change_events': len(self.analyzer.lane_change_events),
                'speeding_events': len(self.analyzer.speeding_events),
                'stop_events': len(self.analyzer.stop_events),
                'wrong_way_events': len(self.analyzer.wrong_way_events),
                'congestion_events': len(self.analyzer.congestion_events),
                'fps': 1/avg_processing_time if avg_processing_time > 0 else 0
            }
            self.stats_updated.emit(stats)
                
            frame_idx += 1
        
        cap.release()
        if self.save_video:
            out.release()
            
        self.processing_finished.emit()
        self.is_running = False
        
    def stop(self):
        self.is_running = False


# PyQt主窗口
class TrafficAnalyzerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.analyzer = AdvancedTrafficAnalyzer()
        self.mqtt_client = MQTTClient()
        self.video_processor = None
        self.current_video_path = ""
        self.is_processing = False
        
        self.init_ui()
        self.load_settings()
        
    def init_ui(self):
        self.setWindowTitle("高级交通分析系统")
        self.setGeometry(100, 100, 1600, 900)
        
        # 中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QHBoxLayout(central_widget)
        
        # 左侧控制面板
        control_panel = QFrame()
        control_panel.setFrameShape(QFrame.StyledPanel)
        control_panel.setFixedWidth(400)
        control_layout = QVBoxLayout(control_panel)
        
        # 视频控制组
        video_group = QGroupBox("视频控制")
        video_layout = QVBoxLayout(video_group)
        
        self.video_path_label = QLabel("未选择视频文件")
        video_layout.addWidget(self.video_path_label)
        
        browse_btn = QPushButton("选择视频文件")
        browse_btn.clicked.connect(self.browse_video)
        video_layout.addWidget(browse_btn)
        
        self.process_btn = QPushButton("开始处理")
        self.process_btn.clicked.connect(self.toggle_processing)
        video_layout.addWidget(self.process_btn)
        
        self.save_video_cb = QCheckBox("保存处理后的视频")
        self.save_video_cb.setChecked(True)
        video_layout.addWidget(self.save_video_cb)
        
        control_layout.addWidget(video_group)
        
        # 分析设置组
        settings_group = QGroupBox("分析设置")
        settings_layout = QVBoxLayout(settings_group)
        
        settings_layout.addWidget(QLabel("速度限制 (km/h):"))
        self.speed_limit_spin = QSpinBox()
        self.speed_limit_spin.setRange(0, 200)
        self.speed_limit_spin.setValue(60)
        self.speed_limit_spin.valueChanged.connect(self.update_speed_limit)
        settings_layout.addWidget(self.speed_limit_spin)
        
        settings_layout.addWidget(QLabel("帧缩放比例:"))
        self.frame_scale_spin = QDoubleSpinBox()
        self.frame_scale_spin.setRange(0.1, 1.0)
        self.frame_scale_spin.setValue(1.0)
        self.frame_scale_spin.setSingleStep(0.1)
        self.frame_scale_spin.valueChanged.connect(self.update_frame_scale)
        settings_layout.addWidget(self.frame_scale_spin)
        
        settings_layout.addWidget(QLabel("拥堵检测阈值:"))
        self.congestion_threshold_spin = QSpinBox()
        self.congestion_threshold_spin.setRange(1, 20)
        self.congestion_threshold_spin.setValue(5)
        self.congestion_threshold_spin.valueChanged.connect(self.update_congestion_threshold)
        settings_layout.addWidget(self.congestion_threshold_spin)
        
        control_layout.addWidget(settings_group)
        
        # MQTT设置组
        mqtt_group = QGroupBox("MQTT设置")
        mqtt_layout = QVBoxLayout(mqtt_group)
        
        mqtt_layout.addWidget(QLabel("MQTT服务器:"))
        self.mqtt_host_edit = QTextEdit()
        self.mqtt_host_edit.setMaximumHeight(30)
        self.mqtt_host_edit.setText("broker.emqx.io")
        mqtt_layout.addWidget(self.mqtt_host_edit)
        
        mqtt_layout.addWidget(QLabel("端口:"))
        self.mqtt_port_spin = QSpinBox()
        self.mqtt_port_spin.setRange(1, 65535)
        self.mqtt_port_spin.setValue(1883)
        mqtt_layout.addWidget(self.mqtt_port_spin)
        
        mqtt_layout.addWidget(QLabel("主题:"))
        self.mqtt_topic_edit = QTextEdit()
        self.mqtt_topic_edit.setMaximumHeight(30)
        self.mqtt_topic_edit.setText("traffic/analysis")
        mqtt_layout.addWidget(self.mqtt_topic_edit)
        
        self.mqtt_connect_btn = QPushButton("连接MQTT")
        self.mqtt_connect_btn.clicked.connect(self.toggle_mqtt_connection)
        mqtt_layout.addWidget(self.mqtt_connect_btn)
        
        self.mqtt_status_label = QLabel("状态: 未连接")
        mqtt_layout.addWidget(self.mqtt_status_label)
        
        control_layout.addWidget(mqtt_group)
        
        # 数据分析组
        data_group = QGroupBox("数据分析")
        data_layout = QVBoxLayout(data_group)
        
        self.save_data_btn = QPushButton("保存数据")
        self.save_data_btn.clicked.connect(self.save_data)
        data_layout.addWidget(self.save_data_btn)
        
        self.load_data_btn = QPushButton("加载数据")
        self.load_data_btn.clicked.connect(self.load_data)
        data_layout.addWidget(self.load_data_btn)
        
        self.generate_report_btn = QPushButton("生成报告")
        self.generate_report_btn.clicked.connect(self.generate_report)
        data_layout.addWidget(self.generate_report_btn)
        
        self.visualize_btn = QPushButton("可视化轨迹")
        self.visualize_btn.clicked.connect(self.visualize_trajectories)
        data_layout.addWidget(self.visualize_btn)
        
        control_layout.addWidget(data_group)
        
        # 统计信息组
        stats_group = QGroupBox("实时统计")
        stats_layout = QVBoxLayout(stats_group)
        
        self.stats_text = QTextEdit()
        self.stats_text.setReadOnly(True)
        stats_layout.addWidget(self.stats_text)
        
        control_layout.addWidget(stats_group)
        
        control_layout.addStretch()
        
        # 右侧视频显示区域
        video_display_layout = QVBoxLayout()
        
        self.video_label = QLabel()
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setMinimumSize(640, 480)
        self.video_label.setText("视频将在这里显示")
        self.video_label.setStyleSheet("border: 1px solid gray;")
        video_display_layout.addWidget(self.video_label)
        
        # 进度条
        self.progress_bar = QProgressBar()
        video_display_layout.addWidget(self.progress_bar)
        
        # 事件表格
        self.events_table = QTableWidget()
        self.events_table.setColumnCount(4)
        self.events_table.setHorizontalHeaderLabels(["时间", "类型", "ID", "详情"])
        self.events_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        video_display_layout.addWidget(self.events_table)
        
        main_layout.addWidget(control_panel)
        main_layout.addLayout(video_display_layout, 1)
        
        # 状态栏
        self.statusBar().showMessage("就绪")
        
    def load_settings(self):
        settings = QSettings("TrafficAnalyzer", "App")
        self.mqtt_host_edit.setText(settings.value("mqtt_host", "localhost"))
        self.mqtt_port_spin.setValue(int(settings.value("mqtt_port", 1883)))
        self.mqtt_topic_edit.setText(settings.value("mqtt_topic", "traffic/analysis"))
        self.speed_limit_spin.setValue(int(settings.value("speed_limit", 60)))
        self.frame_scale_spin.setValue(float(settings.value("frame_scale", 1.0)))
        self.congestion_threshold_spin.setValue(int(settings.value("congestion_threshold", 5)))
        
    def save_settings(self):
        settings = QSettings("TrafficAnalyzer", "App")
        settings.setValue("mqtt_host", self.mqtt_host_edit.toPlainText())
        settings.setValue("mqtt_port", self.mqtt_port_spin.value())
        settings.setValue("mqtt_topic", self.mqtt_topic_edit.toPlainText())
        settings.setValue("speed_limit", self.speed_limit_spin.value())
        settings.setValue("frame_scale", self.frame_scale_spin.value())
        settings.setValue("congestion_threshold", self.congestion_threshold_spin.value())
        
    def browse_video(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择视频文件", "", "视频文件 (*.mp4 *.avi *.mov *.mkv)"
        )
        if file_path:
            self.current_video_path = file_path
            self.video_path_label.setText(file_path.split("/")[-1])
            
    def toggle_processing(self):
        if not self.is_processing:
            if not self.current_video_path:
                self.statusBar().showMessage("请先选择视频文件")
                return
                
            output_path = self.current_video_path.replace(".", "_processed.")
            self.video_processor = VideoProcessor(
                self.analyzer, 
                self.current_video_path, 
                output_path,
                False,  # 不在单独窗口中显示
                self.save_video_cb.isChecked()
            )
            
            self.video_processor.frame_processed.connect(self.update_video_display)
            self.video_processor.progress_updated.connect(self.update_progress)
            self.video_processor.stats_updated.connect(self.update_stats)
            self.video_processor.processing_finished.connect(self.processing_finished)
            
            self.video_processor.start()
            self.is_processing = True
            self.process_btn.setText("停止处理")
            self.statusBar().showMessage("正在处理视频...")
        else:
            if self.video_processor:
                self.video_processor.stop()
            self.is_processing = False
            self.process_btn.setText("开始处理")
            self.statusBar().showMessage("处理已停止")
            
    def toggle_mqtt_connection(self):
        if not self.mqtt_client.connected:
            host = self.mqtt_host_edit.toPlainText()
            port = self.mqtt_port_spin.value()
            topic = self.mqtt_topic_edit.toPlainText()
            
            if self.mqtt_client.connect(host, port):
                self.mqtt_client.subscribe(topic)
                self.analyzer.set_mqtt_client(self.mqtt_client, topic)
                self.mqtt_connect_btn.setText("断开MQTT")
                self.mqtt_status_label.setText("状态: 已连接")
                self.statusBar().showMessage("MQTT连接成功")
            else:
                self.statusBar().showMessage("MQTT连接失败")
        else:
            self.mqtt_client.disconnect()
            self.mqtt_connect_btn.setText("连接MQTT")
            self.mqtt_status_label.setText("状态: 未连接")
            self.statusBar().showMessage("MQTT已断开")
            
    def update_video_display(self, frame):
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = frame_rgb.shape
        bytes_per_line = ch * w
        qt_image = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qt_image)
        self.video_label.setPixmap(pixmap.scaled(
            self.video_label.width(), 
            self.video_label.height(),
            Qt.KeepAspectRatio
        ))
        
    def update_progress(self, current, total):
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        
    def update_stats(self, stats):
        stats_text = f"""
        压线事件: {stats['crossing_events']}
        变道事件: {stats['lane_change_events']}
        超速事件: {stats['speeding_events']}
        违规停车: {stats['stop_events']}
        逆行事件: {stats['wrong_way_events']}
        拥堵事件: {stats['congestion_events']}
        处理速度: {stats['fps']:.1f} FPS
        """
        self.stats_text.setPlainText(stats_text)
        
        # 更新事件表格
        all_events = []
        all_events.extend(self.analyzer.crossing_events[-5:])
        all_events.extend(self.analyzer.lane_change_events[-5:])
        all_events.extend(self.analyzer.speeding_events[-5:])
        all_events.extend(self.analyzer.stop_events[-5:])
        all_events.extend(self.analyzer.wrong_way_events[-5:])
        all_events.extend(self.analyzer.congestion_events[-5:])
        
        # 按时间排序
        all_events.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        self.events_table.setRowCount(min(20, len(all_events)))
        for i, event in enumerate(all_events[:20]):
            self.events_table.setItem(i, 0, QTableWidgetItem(event.get('timestamp', '')))
            self.events_table.setItem(i, 1, QTableWidgetItem(event.get('type', '')))
            self.events_table.setItem(i, 2, QTableWidgetItem(str(event.get('track_id', ''))))
            
            details = ""
            if event['type'] == 'line_crossing':
                details = f"线 {event.get('line_id', '')}, 方向 {event.get('direction', '')}"
            elif event['type'] == 'lane_change':
                details = f"方向 {event.get('direction', '')}, 斜率 {event.get('slope', 0):.2f}"
            elif event['type'] == 'speeding':
                details = f"速度 {event.get('speed', 0):.1f} km/h, 限速 {event.get('speed_limit', 0)} km/h"
            elif event['type'] == 'illegal_stop':
                details = f"位置 {event.get('position', (0, 0))}, 帧数 {event.get('stop_frames', 0)}"
            elif event['type'] == 'wrong_way':
                details = f"方向 {event.get('direction', '')}, 预期 {event.get('expected_direction', '')}"
            elif event['type'] in ['congestion_start', 'congestion_end']:
                details = f"区域 {event.get('zone_id', '')}, 车辆 {event.get('vehicle_count', 0)}"
                
            self.events_table.setItem(i, 3, QTableWidgetItem(details))
            
    def processing_finished(self):
        self.is_processing = False
        self.process_btn.setText("开始处理")
        self.statusBar().showMessage("视频处理完成")
        
    def update_speed_limit(self, value):
        self.analyzer.speed_limit = value
        
    def update_frame_scale(self, value):
        self.analyzer.frame_scale = value
        
    def update_congestion_threshold(self, value):
        self.analyzer.congestion_threshold = value
        
    def save_data(self):
        options = QFileDialog.Options()
        base_name = self.current_video_path.split("/")[-1].split(".")[0]
        
        trajectories_path, _ = QFileDialog.getSaveFileName(
            self, "保存轨迹数据", f"{base_name}_trajectories.json", "JSON文件 (*.json)", options=options
        )
        
        if trajectories_path:
            events_path = trajectories_path.replace("trajectories", "events")
            speeds_path = trajectories_path.replace("trajectories", "speeds")
            counts_path = trajectories_path.replace("trajectories", "counts")
            
            self.analyzer.save_data(trajectories_path, events_path, speeds_path, counts_path)
            self.statusBar().showMessage("数据已保存")
            
    def load_data(self):
        options = QFileDialog.Options()
        trajectories_path, _ = QFileDialog.getOpenFileName(
            self, "加载轨迹数据", "", "JSON文件 (*.json)", options=options
        )
        
        if trajectories_path:
            events_path = trajectories_path.replace("trajectories", "events")
            speeds_path = trajectories_path.replace("trajectories", "speeds")
            counts_path = trajectories_path.replace("trajectories", "counts")
            
            self.analyzer.load_data(trajectories_path, events_path, speeds_path, counts_path)
            self.statusBar().showMessage("数据已加载")
            self.update_stats({
                'crossing_events': len(self.analyzer.crossing_events),
                'lane_change_events': len(self.analyzer.lane_change_events),
                'speeding_events': len(self.analyzer.speeding_events),
                'stop_events': len(self.analyzer.stop_events),
                'wrong_way_events': len(self.analyzer.wrong_way_events),
                'congestion_events': len(self.analyzer.congestion_events),
                'fps': 0
            })
            
    def generate_report(self):
        options = QFileDialog.Options()
        base_name = self.current_video_path.split("/")[-1].split(".")[0] if self.current_video_path else "report"
        
        report_path, _ = QFileDialog.getSaveFileName(
            self, "生成报告", f"{base_name}_report.html", "HTML文件 (*.html)", options=options
        )
        
        if report_path:
            self.analyzer.generate_report(report_path)
            self.statusBar().showMessage("报告已生成")
            
    def visualize_trajectories(self):
        options = QFileDialog.Options()
        base_name = self.current_video_path.split("/")[-1].split(".")[0] if self.current_video_path else "visualization"
        
        image_path, _ = QFileDialog.getSaveFileName(
            self, "保存可视化", f"{base_name}_visualization.png", "PNG图像 (*.png)", options=options
        )
        
        if image_path:
            self.analyzer.visualize_trajectories(image_path)
            self.statusBar().showMessage("可视化已保存")
            
    def closeEvent(self, event):
        self.save_settings()
        if self.mqtt_client.connected:
            self.mqtt_client.disconnect()
        if self.video_processor and self.video_processor.isRunning():
            self.video_processor.stop()
            self.video_processor.wait()
        event.accept()


# 主函数
def main():
    app = QApplication(sys.argv)
    window = TrafficAnalyzerApp()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()