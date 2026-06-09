import sys
import cv2
import torch
import numpy as np
from collections import deque, defaultdict
import time
import pandas as pd
from datetime import datetime
from ultralytics import YOLO
from shapely.geometry import Polygon, Point, LineString
import matplotlib.pyplot as plt
from sklearn.cluster import DBSCAN
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QPushButton, QComboBox, QSlider, QSpinBox, QDoubleSpinBox,
                             QTextEdit, QGroupBox, QCheckBox, QFileDialog, QMessageBox, QTabWidget,
                             QTableWidget, QTableWidgetItem, QSplitter, QProgressBar)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QMutex, QWaitCondition
from PyQt5.QtGui import QImage, QPixmap, QFont, QColor
import json
import os
import paho.mqtt.client as mqtt
import threading
from queue import Queue

# MQTT配置
MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
MQTT_TOPIC_EVENTS = "drone_traffic/events"
MQTT_TOPIC_STATS = "drone_traffic/stats"
MQTT_TOPIC_CONFIG = "drone_traffic/config"

class MQTTClient:
    """MQTT客户端"""
    def __init__(self):
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.connected = False
        self.message_callbacks = {}
        
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.connected = True
            print("MQTT连接成功")
            # 订阅配置主题
            self.client.subscribe(MQTT_TOPIC_CONFIG)
        else:
            print(f"MQTT连接失败，错误码: {rc}")
            
    def on_message(self, client, userdata, msg):
        topic = msg.topic
        payload = msg.payload.decode()
        
        if topic in self.message_callbacks:
            for callback in self.message_callbacks[topic]:
                try:
                    data = json.loads(payload)
                    callback(data)
                except json.JSONDecodeError:
                    callback(payload)
    
    def connect(self, broker, port):
        try:
            self.client.connect(broker, port, 60)
            self.client.loop_start()
            return True
        except Exception as e:
            print(f"MQTT连接异常: {e}")
            return False
            
    def disconnect(self):
        self.client.loop_stop()
        self.client.disconnect()
        self.connected = False
        
    def publish(self, topic, message):
        if self.connected:
            if isinstance(message, dict):
                # 转换NumPy数据类型为Python内置类型
                message = self._convert_numpy_types(message)
                message = json.dumps(message)
            self.client.publish(topic, message)

    def _convert_numpy_types(self, obj):
        """递归地将NumPy数据类型转换为Python内置类型"""
        if isinstance(obj, dict):
            return {k: self._convert_numpy_types(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_numpy_types(v) for v in obj]
        elif isinstance(obj, (np.integer, np.int32, np.int64)):
            return int(obj)
        elif isinstance(obj, (np.floating, np.float32, np.float64)):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        else:
            return obj
            
    def add_message_callback(self, topic, callback):
        if topic not in self.message_callbacks:
            self.message_callbacks[topic] = []
        self.message_callbacks[topic].append(callback)

class FrameBuffer:
    """帧缓冲区，用于平衡视频读取和处理的速率"""
    def __init__(self, max_size=10):
        self.buffer = deque(maxlen=max_size)
        self.mutex = QMutex()
        self.not_empty = QWaitCondition()
        self.not_full = QWaitCondition()
        self.closed = False
        
    def put(self, frame):
        self.mutex.lock()
        while len(self.buffer) == self.buffer.maxlen and not self.closed:
            self.not_full.wait(self.mutex)
        
        if not self.closed:
            self.buffer.append(frame)
            self.not_empty.wakeAll()
        self.mutex.unlock()
        
    def get(self):
        self.mutex.lock()
        while len(self.buffer) == 0 and not self.closed:
            self.not_empty.wait(self.mutex)
            
        if self.closed:
            self.mutex.unlock()
            return None
            
        frame = self.buffer.popleft()
        self.not_full.wakeAll()
        self.mutex.unlock()
        return frame
        
    def close(self):
        self.mutex.lock()
        self.closed = True
        self.not_empty.wakeAll()
        self.not_full.wakeAll()
        self.mutex.unlock()

class VideoReader(QThread):
    """视频读取线程"""
    frame_ready = pyqtSignal(np.ndarray)  # 添加帧就绪信号
    finished = pyqtSignal()
    
    def __init__(self, video_path, buffer_size=10):
        super().__init__()
        self.video_path = video_path
        self.cap = None
        self.is_running = False
        self.buffer = FrameBuffer(buffer_size)
        
    def run(self):
        """运行视频读取循环"""
        try:
            self.cap = cv2.VideoCapture(self.video_path)
            if not self.cap.isOpened():
                print("无法打开视频文件")
                return
                
            self.is_running = True
            while self.is_running:
                ret, frame = self.cap.read()
                if not ret:
                    break
                    
                # 将帧放入缓冲区
                self.buffer.put(frame)
                # 发出帧就绪信号
                self.frame_ready.emit(frame)
                
                # 控制帧率，避免过快读取
                time.sleep(0.03)  # 大约30fps
                
        except Exception as e:
            print(f"视频读取错误: {e}")
        finally:
            if self.cap:
                self.cap.release()
            self.finished.emit()
            
    def stop(self):
        """停止读取"""
        self.is_running = False
        self.buffer.close()


class VideoProcessor(QThread):
    """视频处理线程"""
    frame_processed = pyqtSignal(QImage, dict)
    analysis_updated = pyqtSignal(dict)
    event_detected = pyqtSignal(dict)
    status_update = pyqtSignal(str)
    
    def __init__(self, weights_path):
        super().__init__()
        self.weights_path = weights_path
        self.model = None
        self.cap = None
        self.is_running = False
        self.is_paused = False
        self.current_frame = None
        self.detector = None
        self.frame_skip = 0  # 跳帧处理
        self.process_every_n_frame = 1  # 每n帧处理一次
        self.mqtt_client = None
        self.reader = None
        self.inference_worker = None
        self.buffer = None
        self.initialized = False  # 添加初始化状态标志
        self.initialization_failed = False  # 添加初始化失败标志
        
    def set_mqtt_client(self, mqtt_client):
        """设置MQTT客户端"""
        self.mqtt_client = mqtt_client
        
    def initialize(self):
        """初始化检测器 - 修改为异步方式"""
        try:
            # 使用线程池异步加载模型
            from concurrent.futures import ThreadPoolExecutor
            self.status_update.emit("正在加载模型，请稍候...")
            
            def load_model():
                try:
                    self.detector = EnhancedDroneEventDetector(self.weights_path)
                    self.detector.set_mqtt_client(self.mqtt_client)
                    self.model = self.detector.model
                    
                    # 启用GPU加速（如果可用）
                    if torch.cuda.is_available():
                        self.model = self.model.cuda()
                        print("使用GPU加速")
                    else:
                        print("使用CPU")
                    
                    self.initialized = True
                    self.status_update.emit("模型加载完成")
                    return True
                except Exception as e:
                    self.initialization_failed = True
                    self.status_update.emit(f"模型加载失败: {str(e)}")
                    return False
            
            # 使用线程池执行加载任务
            self.executor = ThreadPoolExecutor(max_workers=1)
            self.future = self.executor.submit(load_model)
            return True
            
        except Exception as e:
            print(f"初始化失败: {e}")
            self.initialization_failed = True
            return False

    def run(self):
        """开始处理视频 - 修改运行逻辑"""
        # 等待模型初始化完成
        while not self.initialized and not self.initialization_failed and self.is_running:
            time.sleep(0.1)  # 短暂等待

        if self.initialization_failed:
            self.status_update.emit("模型初始化失败，无法处理视频")
            return

        if not self.is_running:
            return

        # 创建推理工作器
        self.inference_worker = InferenceWorker(self.model, self.buffer)
        self.inference_worker.result_ready.connect(self.handle_inference_result)

        self.is_running = True
        self.status_update.emit("开始处理视频")

        # 启动读取器和推理工作器
        self.reader.start()
        self.inference_worker.start()

        # 等待处理完成
        while self.is_running:
            time.sleep(0.01)  # 减少等待时间，提高响应性

        # 清理资源
        self.reader.stop()
        if self.reader.isRunning():
            self.reader.wait()
        self.inference_worker.stop()
        if self.inference_worker.isRunning():
            self.inference_worker.wait()

        # 关闭线程池
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=False)
    
    def load_video(self, video_path):
        """加载视频"""
        try:
            # 创建帧缓冲区
            self.buffer = FrameBuffer(max_size=15)

            # 创建视频读取器
            self.reader = VideoReader(video_path)
            # 连接帧就绪信号
            self.reader.frame_ready.connect(self.handle_frame)
            self.reader.finished.connect(self.on_video_finished)

            # 获取视频信息
            self.cap = cv2.VideoCapture(video_path)
            self.fps = self.cap.get(cv2.CAP_PROP_FPS)
            self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
            self.cap.release()

            return True, "视频加载成功"
        except Exception as e:
            return False, f"加载视频时出错: {e}"
    
    def handle_frame(self, frame):
        """处理从读取器接收到的帧"""
        if self.is_paused or not self.is_running:
            return
            
        # 将帧放入缓冲区供推理使用
        self.buffer.put(frame)
        
    def handle_inference_result(self, frame, results):
        """处理推理结果"""
        if self.is_paused or not self.is_running:
            return
            
        start_time = time.time()
        
        # 处理帧
        processed_frame, analysis_data = self.detector.process_frame(frame, results)
        processing_time = time.time() - start_time
        
        # 转换为QImage
        rgb_image = cv2.cvtColor(processed_frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        
        # 发送信号
        self.frame_processed.emit(qt_image, analysis_data)
        
        # 每30帧发送一次分析数据
        if self.detector.frame_count % 30 == 0:
            analysis_data = self.detector.get_analysis_data()
            self.analysis_updated.emit(analysis_data)
            
            # 通过MQTT发送统计数据
            if self.mqtt_client and self.mqtt_client.connected:
                stats = {
                    'timestamp': datetime.now().isoformat(),
                    'traffic_counts': analysis_data.get('traffic_flow', {}),
                    'total_vehicles': analysis_data.get('traffic_flow', {}).get('total', 0),
                    'events_count': len(analysis_data.get('events', [])),
                    'fps': analysis_data.get('fps', 0)
                }
                self.mqtt_client.publish(MQTT_TOPIC_STATS, stats)
        
        # 检测到事件时发送信号
        if self.detector.new_events:
            for event in self.detector.new_events:
                self.event_detected.emit(event)
                
                # 通过MQTT发送事件
                if self.mqtt_client and self.mqtt_client.connected:
                    self.mqtt_client.publish(MQTT_TOPIC_EVENTS, event)
            
            self.detector.new_events.clear()
    
    def on_video_finished(self):
        """视频播放完成"""
        self.stop()

    def stop(self):
        """停止处理"""
        self.is_running = False
        if self.reader:
            self.reader.stop()
        if hasattr(self, 'inference_worker') and self.inference_worker:
            self.inference_worker.stop()
    
    def pause(self):
        """暂停处理"""
        self.is_paused = True
    
    def resume(self):
        """继续处理"""
        self.is_paused = False

class InferenceWorker(QThread):
    """推理工作线程"""
    result_ready = pyqtSignal(object, object)
    
    def __init__(self, model, buffer, conf_thresh=0.5, iou_thresh=0.5):
        super().__init__()
        self.model = model
        self.buffer = buffer
        self.model.conf = conf_thresh
        self.model.iou = iou_thresh
        self.is_running = False
        
    def run(self):
        """执行推理"""
        self.is_running = True
        while self.is_running:
            frame = self.buffer.get()
            if frame is None:
                break
                
            # 执行推理
            results = self.model.track(frame, persist=True, verbose=False)
            self.result_ready.emit(frame, results)
            
    def stop(self):
        """停止推理"""
        self.is_running = False



class EnhancedDroneEventDetector:
    """增强版无人机事件检测器"""
    def __init__(self, weights_path, conf_thresh=0.5, iou_thresh=0.5):
        # 加载YOLOv8模型
        self.model = YOLO(weights_path)
        self.model.conf = conf_thresh
        self.model.iou = iou_thresh
        
        # 使用GPU加速（如果可用）
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        if torch.cuda.is_available():
            self.model.model.to(self.device)
        
        # 定义类别和颜色映射
        self.class_names = self.model.names
        self.colors = self._generate_colors(len(self.class_names))
        
        # 事件检测参数
        self.collision_distance_thresh = 50
        self.overturn_aspect_ratio = 2.0
        self.tailgating_time_thresh = 15
        self.speed_threshold = 10
        self.min_tracking_frames = 5  # 最小跟踪帧数
        
        # 闯入检测区域
        self.intrusion_zone = None
        self.roi_zones = []  # 多个ROI区域
        
        # 交通流量统计
        self.counting_lines = []
        self.crossed_objects = defaultdict(set)
        self.traffic_counts = defaultdict(int)
        self.traffic_data = []
        
        # 跟踪数据
        self.track_history = defaultdict(lambda: deque(maxlen=30))
        self.event_log = []
        self.new_events = []  # 新检测到的事件
        
        # 分析结果存储
        self.analysis_results = {
            'events': [],
            'traffic_flow': defaultdict(int),
            'peak_times': [],
            'anomalies': [],
            'frame_count': 0,
            'processing_time': 0
        }
        
        # 性能监控
        self.frame_count = 0
        self.start_time = time.time()
        
        # 可视化设置
        self.show_trajectories = True
        self.show_detections = True
        self.show_counting = True
        self.show_intrusion_zone = True
        self.show_roi_zones = True
        
        # MQTT客户端
        self.mqtt_client = None
        
        # 优化设置
        self.last_anomaly_detection = 0
        self.anomaly_detection_interval = 30  # 每30帧检测一次异常
        
        # 添加车辆分类
        self.vehicle_classes = ['car', 'truck', 'bus', 'motorcycle']
        self.person_classes = ['person']
        self.animal_classes = ['animal']
        
    def set_mqtt_client(self, mqtt_client):
        """设置MQTT客户端"""
        self.mqtt_client = mqtt_client
        
    def _generate_colors(self, n):
        """生成随机颜色"""
        return [tuple(np.random.randint(0, 255, 3).tolist()) for _ in range(n)]
    
    def set_intrusion_zone(self, zone_points):
        """设置闯入检测区域"""
        self.intrusion_zone = Polygon(zone_points)
    
    def add_roi_zone(self, zone_points):
        """添加ROI区域"""
        self.roi_zones.append(Polygon(zone_points))
    
    def add_counting_line(self, start_point, end_point):
        """添加交通计数线"""
        self.counting_lines.append((start_point, end_point))
    
    def process_frame(self, frame, results=None):
        """处理单帧图像"""
        self.frame_count += 1
        
        # 如果未提供结果，则进行检测
        if results is None:
            results = self.model.track(frame, persist=True, verbose=False)
        
        # 提取检测信息
        detections = self._extract_detections(results)
        
        # 更新跟踪历史
        self._update_tracking(detections)
        
        # 检测事件
        self._detect_events(frame, detections)
        
        # 统计交通流量
        self._count_traffic(frame, detections)
        
        # 分析交通模式 (减少频率以提高性能)
        if self.frame_count % 60 == 0:
            self._analyze_traffic_patterns()
        
        # 绘制结果
        processed_frame = self._visualize_results(frame.copy(), detections, results)
        
        # 准备分析数据
        analysis_data = {
            'traffic_counts': dict(self.traffic_counts),
            'event_count': len(self.analysis_results['events']),
            'frame_count': self.frame_count,
            'fps': self.frame_count / (time.time() - self.start_time) if time.time() > self.start_time else 0
        }
        
        return processed_frame, analysis_data
    
    def _extract_detections(self, results):
        """从YOLO结果中提取检测信息"""
        detections = {}
        
        if results[0].boxes is not None and results[0].boxes.id is not None:
            boxes = results[0].boxes.xyxy.cpu().numpy()
            track_ids = results[0].boxes.id.cpu().numpy().astype(int)
            confidences = results[0].boxes.conf.cpu().numpy()
            class_ids = results[0].boxes.cls.cpu().numpy().astype(int)
            
            for i, (box, track_id, conf, cls_id) in enumerate(zip(boxes, track_ids, confidences, class_ids)):
                x1, y1, x2, y2 = box
                center_x, center_y = (x1 + x2) / 2, (y1 + y2) / 2
                
                detections[track_id] = {
                    'bbox': (x1, y1, x2, y2),
                    'center': (center_x, center_y),
                    'class_id': cls_id,
                    'class_name': self.class_names[cls_id],
                    'confidence': conf,
                    'timestamp': time.time()
                }
        
        return detections
    
    def _update_tracking(self, detections):
        """更新对象跟踪历史"""
        current_time = time.time()
        
        # 更新跟踪历史
        for track_id, detection in detections.items():
            self.track_history[track_id].append({
                'center': detection['center'],
                'timestamp': current_time,
                'bbox': detection['bbox']
            })
        
        # 清理过期的跟踪记录
        expired_tracks = [
            track_id for track_id in self.track_history
            if current_time - self.track_history[track_id][-1]['timestamp'] > 5.0
        ]
        for track_id in expired_tracks:
            del self.track_history[track_id]
            if track_id in self.crossed_objects:
                for line_id in list(self.crossed_objects.keys()):
                    if track_id in self.crossed_objects[line_id]:
                        self.crossed_objects[line_id].remove(track_id)
    
    def _detect_events(self, frame, detections):
        """检测各种事件"""
        # 检测闯入事件
        self._detect_intrusions(frame, detections)
        
        # 检测车辆事件
        vehicle_detections = {
            k: v for k, v in detections.items() 
            if v['class_name'] in self.vehicle_classes
        }
        
        # 单车事件检测
        for track_id, detection in vehicle_detections.items():
            self._detect_vehicle_events(frame, track_id, detection)
        
        # 车辆间事件检测
        self._detect_vehicle_interactions(frame, vehicle_detections)
        
        # 异常行为检测 (减少频率以提高性能)
        if self.frame_count - self.last_anomaly_detection > self.anomaly_detection_interval:
            self._detect_anomalies(frame, detections)
            self.last_anomaly_detection = self.frame_count
            
        # 检测停车事件
        self._detect_parking_events(frame, detections)
    
    def _detect_parking_events(self, frame, detections):
        """检测违章停车事件"""
        if not self.roi_zones:
            return
            
        for track_id, detection in detections.items():
            if detection['class_name'] not in self.vehicle_classes:
                continue
                
            if track_id not in self.track_history or len(self.track_history[track_id]) < 10:
                continue
                
            # 检查车辆是否在ROI区域内静止
            center_point = Point(detection['center'])
            in_roi = any(zone.contains(center_point) for zone in self.roi_zones)
            
            if in_roi:
                # 检查车辆是否静止
                history = list(self.track_history[track_id])
                recent_positions = [h['center'] for h in history[-10:]]
                movement = np.std(recent_positions, axis=0).mean()
                
                if movement < 2.0:  # 低移动量表示静止
                    # 检查是否已经记录了停车事件
                    event_exists = any(
                        e['type'] == 'illegal_parking' and e['track_id'] == track_id 
                        for e in self.analysis_results['events']
                    )
                    
                    if not event_exists:
                        event_msg = f"ILLEGAL_PARKING: Vehicle {track_id} parked in restricted area"
                        event_data = {
                            'type': 'illegal_parking',
                            'object_type': detection['class_name'],
                            'timestamp': datetime.now().isoformat(),
                            'location': detection['center'],
                            'track_id': track_id,
                            'duration': 0,  # 初始持续时间
                            'message': event_msg
                        }
                        
                        self.event_log.append(event_msg)
                        self.analysis_results['events'].append(event_data)
                        self.new_events.append(event_data)
                        
                        # 发送MQTT通知
                        if self.mqtt_client and self.mqtt_client.connected:
                            self.mqtt_client.publish(MQTT_TOPIC_EVENTS, event_data)
    
    def _detect_intrusions(self, frame, detections):
        """检测闯入事件"""
        if self.intrusion_zone is None:
            return
            
        for track_id, detection in detections.items():
            if detection['class_name'] in self.person_classes + self.animal_classes:
                center_point = Point(detection['center'])
                
                if self.intrusion_zone.contains(center_point):
                    # 记录闯入事件
                    event_msg = f"INTRUSION: {detection['class_name']} detected in restricted area"
                    event_data = {
                        'type': 'intrusion',
                        'object_type': detection['class_name'],
                        'timestamp': datetime.now().isoformat(),
                        'location': detection['center'],
                        'track_id': track_id,
                        'message': event_msg
                    }
                    
                    if event_msg not in self.event_log:
                        self.event_log.append(event_msg)
                        self.analysis_results['events'].append(event_data)
                        self.new_events.append(event_data)
                        
                        # 发送MQTT通知
                        if self.mqtt_client and self.mqtt_client.connected:
                            self.mqtt_client.publish(MQTT_TOPIC_EVENTS, event_data)
    
    def _detect_vehicle_events(self, frame, track_id, detection):
        """检测单车事件"""
        if track_id not in self.track_history or len(self.track_history[track_id]) < self.min_tracking_frames:
            return
            
        history = list(self.track_history[track_id])
        current = history[-1]
        prev = history[-2]
        
        # 计算速度
        time_diff = current['timestamp'] - prev['timestamp']
        if time_diff > 0:
            dx = current['center'][0] - prev['center'][0]
            dy = current['center'][1] - prev['center'][1]
            speed = np.sqrt(dx**2 + dy**2) / time_diff
            
            # 检测异常速度
            if speed > self.speed_threshold:
                event_msg = f"SPEED_ANOMALY: Vehicle {track_id} moving at abnormal speed: {speed:.2f} px/frame"
                event_data = {
                    'type': 'speed_anomaly',
                    'object_type': detection['class_name'],
                    'timestamp': datetime.now().isoformat(),
                    'location': detection['center'],
                    'speed': float(speed),
                    'track_id': track_id,
                    'message': event_msg
                }
                
                if event_msg not in self.event_log:
                    self.event_log.append(event_msg)
                    self.analysis_results['events'].append(event_data)
                    self.analysis_results['anomalies'].append(event_data)
                    self.new_events.append(event_data)
                    
                    # 发送MQTT通知
                    if self.mqtt_client and self.mqtt_client.connected:
                        self.mqtt_client.publish(MQTT_TOPIC_EVENTS, event_data)
        
        # 检测侧翻事件
        x1, y1, x2, y2 = detection['bbox']
        width = x2 - x1
        height = y2 - y1
        
        if width > 0 and height > 0:
            aspect_ratio = max(width, height) / min(width, height)
            if aspect_ratio > self.overturn_aspect_ratio:
                event_msg = f"OVERTURN: Vehicle {track_id} may have overturned"
                event_data = {
                    'type': 'overturn',
                    'object_type': detection['class_name'],
                    'timestamp': datetime.now().isoformat(),
                    'location': detection['center'],
                    'aspect_ratio': aspect_ratio,
                    'track_id': track_id,
                    'message': event_msg
                }
                
                if event_msg not in self.event_log:
                    self.event_log.append(event_msg)
                    self.analysis_results['events'].append(event_data)
                    self.new_events.append(event_data)
                    
                    # 发送MQTT通知
                    if self.mqtt_client and self.mqtt_client.connected:
                        self.mqtt_client.publish(MQTT_TOPIC_EVENTS, event_data)
    
    def _detect_vehicle_interactions(self, frame, vehicle_detections):
        """检测车辆间交互事件"""
        vehicle_ids = list(vehicle_detections.keys())
        
        for i in range(len(vehicle_ids)):
            for j in range(i + 1, len(vehicle_ids)):
                id1, id2 = vehicle_ids[i], vehicle_ids[j]
                
                if id1 not in self.track_history or id2 not in self.track_history:
                    continue
                    
                det1, det2 = vehicle_detections[id1], vehicle_detections[id2]
                history1 = list(self.track_history[id1])
                history2 = list(self.track_history[id2])
                
                # 计算当前距离
                center1, center2 = det1['center'], det2['center']
                distance = np.sqrt((center1[0] - center2[0])**2 + (center1[1] - center2[1])**2)
                
                # 检测碰撞事件
                if distance < self.collision_distance_thresh:
                    event_msg = f"COLLISION: {det1['class_name']} {id1} and {det2['class_name']} {id2}"
                    event_data = {
                        'type': 'collision',
                        'objects': [det1['class_name'], det2['class_name']],
                        'timestamp': datetime.now().isoformat(),
                        'location': [(center1[0] + center2[0])/2, (center1[1] + center2[1])/2],
                        'distance': distance,
                        'track_ids': [id1, id2],
                        'message': event_msg
                    }
                    
                    if event_msg not in self.event_log:
                        self.event_log.append(event_msg)
                        self.analysis_results['events'].append(event_data)
                        self.new_events.append(event_data)
                        
                        # 发送MQTT通知
                        if self.mqtt_client and self.mqtt_client.connected:
                            self.mqtt_client.publish(MQTT_TOPIC_EVENTS, event_data)
                
                # 检测追尾事件
                self._detect_tailgating(id1, id2, det1, det2, history1, history2)
    
    def _detect_tailgating(self, id1, id2, det1, det2, history1, history2):
        """检测追尾事件"""
        if len(history1) < self.tailgating_time_thresh or len(history2) < self.tailgating_time_thresh:
            return
            
        # 计算最近几帧的平均距离
        recent_distances = []
        for i in range(1, self.tailgating_time_thresh + 1):
            pos1 = history1[-i]['center']
            pos2 = history2[-i]['center']
            dist = np.sqrt((pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2)
            recent_distances.append(dist)
        
        avg_distance = np.mean(recent_distances)
        
        # 检查是否长时间保持近距离
        if avg_distance < self.collision_distance_thresh * 2 and np.std(recent_distances) < 5:
            # 检查方向是否一致
            dir1 = np.array(history1[-1]['center']) - np.array(history1[-5]['center'])
            dir2 = np.array(history2[-1]['center']) - np.array(history2[-5]['center'])
            
            if np.linalg.norm(dir1) > 0 and np.linalg.norm(dir2) > 0:
                dir1_norm = dir1 / np.linalg.norm(dir1)
                dir2_norm = dir2 / np.linalg.norm(dir2)
                similarity = np.dot(dir1_norm, dir2_norm)
                
                if similarity > 0.8:
                    event_msg = f"TAILGATING: {det1['class_name']} {id1} following {det2['class_name']} {id2} too closely"
                    event_data = {
                        'type': 'tailgating',
                        'objects': [det1['class_name'], det2['class_name']],
                        'timestamp': datetime.now().isoformat(),
                        'location': det1['center'],
                        'avg_distance': avg_distance,
                        'direction_similarity': similarity,
                        'track_ids': [id1, id2],
                        'message': event_msg
                    }
                    
                    if event_msg not in self.event_log:
                        self.event_log.append(event_msg)
                        self.analysis_results['events'].append(event_data)
                        self.new_events.append(event_data)
                        
                        # 发送MQTT通知
                        if self.mqtt_client and self.mqtt_client.connected:
                            self.mqtt_client.publish(MQTT_TOPIC_EVENTS, event_data)
    
    def _detect_anomalies(self, frame, detections):
        """检测异常行为"""
        vehicle_positions = []
        vehicle_ids = []
        
        for track_id, detection in detections.items():
            if detection['class_name'] in self.vehicle_classes:
                vehicle_positions.append(detection['center'])
                vehicle_ids.append(track_id)
        
        if len(vehicle_positions) > 5:
            clustering = DBSCAN(eps=100, min_samples=3).fit(vehicle_positions)
            labels = clustering.labels_
            
            unique_labels, counts = np.unique(labels, return_counts=True)
            
            for label, count in zip(unique_labels, counts):
                if label == -1:
                    event_msg = f"TRAFFIC_ANOMALY: Vehicles are abnormally dispersed"
                    event_data = {
                        'type': 'dispersion_anomaly',
                        'timestamp': datetime.now().isoformat(),
                        'vehicle_count': count,
                        'anomaly_type': 'dispersion',
                        'message': event_msg
                    }
                    
                    if event_msg not in self.event_log:
                        self.event_log.append(event_msg)
                        self.analysis_results['anomalies'].append(event_data)
                        self.new_events.append(event_data)
                        
                        # 发送MQTT通知
                        if self.mqtt_client and self.mqtt_client.connected:
                            self.mqtt_client.publish(MQTT_TOPIC_EVENTS, event_data)
                
                elif count > 10:
                    event_msg = f"TRAFFIC_CONGESTION: Large vehicle cluster detected ({count} vehicles)"
                    event_data = {
                        'type': 'congestion',
                        'timestamp': datetime.now().isoformat(),
                        'vehicle_count': count,
                        'cluster_label': label,
                        'message': event_msg
                    }
                    
                    if event_msg not in self.event_log:
                        self.event_log.append(event_msg)
                        self.analysis_results['anomalies'].append(event_data)
                        self.new_events.append(event_data)
                        
                        # 发送MQTT通知
                        if self.mqtt_client and self.mqtt_client.connected:
                            self.mqtt_client.publish(MQTT_TOPIC_EVENTS, event_data)
    
    def _count_traffic(self, frame, detections):
        """统计交通流量"""
        current_time = datetime.now()
        
        for line_idx, (start_point, end_point) in enumerate(self.counting_lines):
            counting_line = LineString([start_point, end_point])
            
            for track_id, detection in detections.items():
                if detection['class_name'] not in self.vehicle_classes:
                    continue
                
                if track_id not in self.track_history or len(self.track_history[track_id]) < 2:
                    continue
                
                current_pos = Point(detection['center'])
                prev_pos = Point(self.track_history[track_id][-2]['center'])
                
                movement_path = LineString([prev_pos, current_pos])
                
                if movement_path.intersects(counting_line) and track_id not in self.crossed_objects[line_idx]:
                    self.crossed_objects[line_idx].add(track_id)
                    vehicle_type = detection['class_name']
                    
                    self.traffic_counts[vehicle_type] += 1
                    self.traffic_counts['total'] += 1
                    
                    traffic_record = {
                        'timestamp': current_time.isoformat(),
                        'vehicle_type': vehicle_type,
                        'line_id': line_idx,
                        'direction': self._get_direction(prev_pos, current_pos)
                    }
                    self.traffic_data.append(traffic_record)
                    
                    self.analysis_results['traffic_flow'][vehicle_type] += 1
                    
                    # 发送MQTT通知
                    if self.mqtt_client and self.mqtt_client.connected:
                        traffic_event = {
                            'type': 'traffic_count',
                            'vehicle_type': vehicle_type,
                            'line_id': line_idx,
                            'direction': traffic_record['direction'],
                            'total_count': self.traffic_counts['total'],
                            'vehicle_count': self.traffic_counts[vehicle_type],
                            'timestamp': current_time.isoformat()
                        }
                        self.mqtt_client.publish(MQTT_TOPIC_EVENTS, traffic_event)
    
    def _get_direction(self, prev_pos, current_pos):
        """获取车辆移动方向"""
        dx = current_pos.x - prev_pos.x
        dy = current_pos.y - prev_pos.y
        
        if abs(dx) > abs(dy):
            return 'east' if dx > 0 else 'west'
        else:
            return 'south' if dy > 0 else 'north'
    
    def _analyze_traffic_patterns(self):
        """分析交通模式"""
        if not self.traffic_data:
            return
        
        df = pd.DataFrame(self.traffic_data)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['time_window'] = df['timestamp'].dt.floor('5min')
        
        flow_by_window = df.groupby(['time_window', 'vehicle_type']).size().unstack(fill_value=0)
        
        for vehicle_type in flow_by_window.columns:
            flow_series = flow_by_window[vehicle_type]
            if len(flow_series) > 1:
                mean_flow = flow_series.mean()
                std_flow = flow_series.std()
                
                peak_windows = flow_series[flow_series > mean_flow + 2 * std_flow]
                for time_window, count in peak_windows.items():
                    peak_info = {
                        'vehicle_type': vehicle_type,
                        'time_window': time_window.isoformat(),
                        'count': count,
                        'mean_flow': mean_flow,
                        'std_flow': std_flow
                    }
                    self.analysis_results['peak_times'].append(peak_info)
                    
                    # 发送MQTT通知
                    if self.mqtt_client and self.mqtt_client.connected:
                        peak_event = {
                            'type': 'peak_traffic',
                            'vehicle_type': vehicle_type,
                            'time_window': time_window.isoformat(),
                            'count': count,
                            'mean_flow': mean_flow,
                            'std_flow': std_flow
                        }
                        self.mqtt_client.publish(MQTT_TOPIC_EVENTS, peak_event)
    
    def _visualize_results(self, frame, detections, results):
        """可视化结果"""
        if self.show_detections:
            for track_id, detection in detections.items():
                x1, y1, x2, y2 = detection['bbox']
                class_name = detection['class_name']
                conf = detection['confidence']
                color = self.colors[detection['class_id']]
                
                cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), color, 2)
                
                label = f"{class_name} {conf:.2f} #{track_id}"
                cv2.putText(frame, label, (int(x1), int(y1)-10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
                
                if self.show_trajectories and track_id in self.track_history:
                    history = list(self.track_history[track_id])
                    # 只绘制最近10个点以提高性能
                    for i in range(max(1, len(history)-10), len(history)):
                        pt1 = (int(history[i-1]['center'][0]), int(history[i-1]['center'][1]))
                        pt2 = (int(history[i]['center'][0]), int(history[i]['center'][1]))
                        cv2.line(frame, pt1, pt2, color, 2)
        
        if self.show_counting:
            for i, (start_point, end_point) in enumerate(self.counting_lines):
                cv2.line(frame, start_point, end_point, (0, 255, 255), 2)
                cv2.putText(frame, f"Count Line {i}", 
                           (start_point[0], start_point[1]-10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)
        
        if self.show_intrusion_zone and self.intrusion_zone is not None:
            zone_points = np.array(self.intrusion_zone.exterior.coords, dtype=np.int32)
            cv2.polylines(frame, [zone_points], True, (0, 0, 255), 2)
            cv2.putText(frame, "Restricted Zone", (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        
        if self.show_roi_zones:
            for i, zone in enumerate(self.roi_zones):
                zone_points = np.array(zone.exterior.coords, dtype=np.int32)
                cv2.polylines(frame, [zone_points], True, (255, 0, 0), 2)
                cv2.putText(frame, f"ROI Zone {i}", 
                           (zone_points[0][0], zone_points[0][1]-10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
        
        # 显示交通计数
        y_offset = 60
        for vehicle_type, count in self.traffic_counts.items():
            if vehicle_type != 'total':
                cv2.putText(frame, f"{vehicle_type}: {count}", 
                           (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                y_offset += 25
        
        cv2.putText(frame, f"Total: {self.traffic_counts.get('total', 0)}", 
                   (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        
        # 显示FPS
        elapsed_time = time.time() - self.start_time
        fps = self.frame_count / elapsed_time if elapsed_time > 0 else 0
        cv2.putText(frame, f"FPS: {fps:.2f}", 
                   (frame.shape[1] - 150, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        # 显示事件警报
        y_offset = frame.shape[0] - 30
        for event in self.event_log[-3:]:
            cv2.putText(frame, event, (10, y_offset), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
            y_offset -= 25
        
        return frame
    
    def get_analysis_data(self):
        """获取分析数据"""
        self.analysis_results['frame_count'] = self.frame_count
        self.analysis_results['processing_time'] = time.time() - self.start_time
        return self.analysis_results
    
    def generate_report(self):
        """生成分析报告"""
        report = {
            'summary': {
                'total_frames_processed': self.frame_count,
                'processing_time': time.time() - self.start_time,
                'average_fps': self.frame_count / (time.time() - self.start_time) if time.time() > self.start_time else 0,
                'total_events_detected': len(self.analysis_results['events']),
                'total_vehicles_counted': self.traffic_counts.get('total', 0)
            },
            'traffic_analysis': dict(self.analysis_results['traffic_flow']),
            'events_detected': self.analysis_results['events'],
            'anomalies_detected': self.analysis_results['anomalies'],
            'peak_times': self.analysis_results['peak_times']
        }
        
        return report

class MainWindow(QMainWindow):
    """主窗口"""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("无人机视角事件检测与交通分析系统")
        self.setGeometry(100, 100, 1600, 900)
        
        # 初始化变量
        self.video_processor = None
        self.video_path = None
        self.weights_path = None
        self.is_processing = False
        self.mqtt_client = MQTTClient()
        
        # 创建UI
        self.create_ui()
        
        # 加载默认配置
        self.load_default_config()
        
        # 连接MQTT
        self.connect_mqtt()
    
    def create_ui(self):
        """创建用户界面"""
        # 中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QHBoxLayout(central_widget)
        
        # 左侧控制面板
        control_panel = QWidget()
        control_panel.setMaximumWidth(400)
        control_layout = QVBoxLayout(control_panel)
        
        # MQTT连接组
        mqtt_group = QGroupBox("MQTT连接")
        mqtt_layout = QVBoxLayout(mqtt_group)
        
        mqtt_status_layout = QHBoxLayout()
        mqtt_status_layout.addWidget(QLabel("状态:"))
        self.mqtt_status_label = QLabel("未连接")
        self.mqtt_status_label.setStyleSheet("color: red;")
        mqtt_status_layout.addWidget(self.mqtt_status_label)
        mqtt_status_layout.addStretch()
        mqtt_layout.addLayout(mqtt_status_layout)
        
        self.connect_mqtt_btn = QPushButton("连接MQTT")
        self.connect_mqtt_btn.clicked.connect(self.connect_mqtt)
        mqtt_layout.addWidget(self.connect_mqtt_btn)
        
        control_layout.addWidget(mqtt_group)
        
        # 视频控制组
        video_group = QGroupBox("视频控制")
        video_layout = QVBoxLayout(video_group)
        
        self.load_video_btn = QPushButton("加载视频")
        self.load_video_btn.clicked.connect(self.load_video)
        video_layout.addWidget(self.load_video_btn)
        
        self.load_weights_btn = QPushButton("加载模型")
        self.load_weights_btn.clicked.connect(self.load_weights)
        video_layout.addWidget(self.load_weights_btn)
        
        self.start_btn = QPushButton("开始处理")
        self.start_btn.clicked.connect(self.start_processing)
        self.start_btn.setEnabled(False)
        video_layout.addWidget(self.start_btn)
        
        self.pause_btn = QPushButton("暂停")
        self.pause_btn.clicked.connect(self.pause_processing)
        self.pause_btn.setEnabled(False)
        video_layout.addWidget(self.pause_btn)
        
        self.stop_btn = QPushButton("停止")
        self.stop_btn.clicked.connect(self.stop_processing)
        self.stop_btn.setEnabled(False)
        video_layout.addWidget(self.stop_btn)
        
        control_layout.addWidget(video_group)
        
        # 参数设置组
        params_group = QGroupBox("检测参数")
        params_layout = QVBoxLayout(params_group)
        
        # 置信度阈值
        conf_layout = QHBoxLayout()
        conf_layout.addWidget(QLabel("置信度阈值:"))
        self.conf_spin = QDoubleSpinBox()
        self.conf_spin.setRange(0.0, 1.0)
        self.conf_spin.setSingleStep(0.05)
        self.conf_spin.setValue(0.5)
        self.conf_spin.valueChanged.connect(self.update_detector_params)
        conf_layout.addWidget(self.conf_spin)
        params_layout.addLayout(conf_layout)
        
        # IoU阈值
        iou_layout = QHBoxLayout()
        iou_layout.addWidget(QLabel("IoU阈值:"))
        self.iou_spin = QDoubleSpinBox()
        self.iou_spin.setRange(0.0, 1.0)
        self.iou_spin.setSingleStep(0.05)
        self.iou_spin.setValue(0.5)
        self.iou_spin.valueChanged.connect(self.update_detector_params)
        iou_layout.addWidget(self.iou_spin)
        params_layout.addLayout(iou_layout)
        
        # 碰撞距离阈值
        collision_layout = QHBoxLayout()
        collision_layout.addWidget(QLabel("碰撞距离阈值:"))
        self.collision_spin = QSpinBox()
        self.collision_spin.setRange(10, 200)
        self.collision_spin.setValue(50)
        self.collision_spin.valueChanged.connect(self.update_detector_params)
        collision_layout.addWidget(self.collision_spin)
        params_layout.addLayout(collision_layout)
        
        # 速度阈值
        speed_layout = QHBoxLayout()
        speed_layout.addWidget(QLabel("速度阈值:"))
        self.speed_spin = QSpinBox()
        self.speed_spin.setRange(1, 50)
        self.speed_spin.setValue(10)
        self.speed_spin.valueChanged.connect(self.update_detector_params)
        speed_layout.addWidget(self.speed_spin)
        params_layout.addLayout(speed_layout)
        
        control_layout.addWidget(params_group)
        
        # 可视化设置组
        vis_group = QGroupBox("可视化设置")
        vis_layout = QVBoxLayout(vis_group)
        
        self.show_detections_cb = QCheckBox("显示检测框")
        self.show_detections_cb.setChecked(True)
        self.show_detections_cb.stateChanged.connect(self.update_visualization_settings)
        vis_layout.addWidget(self.show_detections_cb)
        
        self.show_trajectories_cb = QCheckBox("显示轨迹")
        self.show_trajectories_cb.setChecked(True)
        self.show_trajectories_cb.stateChanged.connect(self.update_visualization_settings)
        vis_layout.addWidget(self.show_trajectories_cb)
        
        self.show_counting_cb = QCheckBox("显示计数线")
        self.show_counting_cb.setChecked(True)
        self.show_counting_cb.stateChanged.connect(self.update_visualization_settings)
        vis_layout.addWidget(self.show_counting_cb)
        
        self.show_intrusion_zone_cb = QCheckBox("显示闯入区域")
        self.show_intrusion_zone_cb.setChecked(True)
        self.show_intrusion_zone_cb.stateChanged.connect(self.update_visualization_settings)
        vis_layout.addWidget(self.show_intrusion_zone_cb)
        
        control_layout.addWidget(vis_group)
        
        # 区域设置组
        zone_group = QGroupBox("区域设置")
        zone_layout = QVBoxLayout(zone_group)
        
        self.set_intrusion_zone_btn = QPushButton("设置闯入区域")
        self.set_intrusion_zone_btn.clicked.connect(self.set_intrusion_zone)
        zone_layout.addWidget(self.set_intrusion_zone_btn)
        
        self.add_roi_zone_btn = QPushButton("添加ROI区域")
        self.add_roi_zone_btn.clicked.connect(self.add_roi_zone)
        zone_layout.addWidget(self.add_roi_zone_btn)
        
        self.add_counting_line_btn = QPushButton("添加计数线")
        self.add_counting_line_btn.clicked.connect(self.add_counting_line)
        zone_layout.addWidget(self.add_counting_line_btn)
        
        self.clear_lines_btn = QPushButton("清除计数线")
        self.clear_lines_btn.clicked.connect(self.clear_counting_lines)
        zone_layout.addWidget(self.clear_lines_btn)
        
        control_layout.addWidget(zone_group)
        
        # 统计信息组
        stats_group = QGroupBox("实时统计")
        stats_layout = QVBoxLayout(stats_group)
        
        self.stats_text = QTextEdit()
        self.stats_text.setMaximumHeight(200)
        stats_layout.addWidget(self.stats_text)
        
        control_layout.addWidget(stats_group)
        
        # 事件日志组
        events_group = QGroupBox("事件日志")
        events_layout = QVBoxLayout(events_group)
        
        self.events_text = QTextEdit()
        self.events_text.setMaximumHeight(200)
        events_layout.addWidget(self.events_text)
        
        control_layout.addWidget(events_group)
        
        # 报告按钮
        self.report_btn = QPushButton("生成报告")
        self.report_btn.clicked.connect(self.generate_report)
        control_layout.addWidget(self.report_btn)
        
        # 添加到主布局
        main_layout.addWidget(control_panel)
        
        # 右侧视频和标签区域
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        # 视频显示标签
        self.video_label = QLabel()
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setMinimumSize(640, 480)
        self.video_label.setText("视频将在这里显示")
        self.video_label.setStyleSheet("border: 1px solid black;")
        right_layout.addWidget(self.video_label)
        
        # 分析结果标签
        self.analysis_label = QLabel()
        self.analysis_label.setAlignment(Qt.AlignLeft)
        self.analysis_label.setText("分析结果将在这里显示")
        right_layout.addWidget(self.analysis_label)
        
        main_layout.addWidget(right_widget)
    
    def connect_mqtt(self):
        """连接MQTT代理"""
        if not self.mqtt_client.connected:
            if self.mqtt_client.connect(MQTT_BROKER, MQTT_PORT):
                self.mqtt_status_label.setText("已连接")
                self.mqtt_status_label.setStyleSheet("color: green;")
                self.connect_mqtt_btn.setText("断开MQTT")
            else:
                self.mqtt_status_label.setText("连接失败")
                self.mqtt_status_label.setStyleSheet("color: red;")
        else:
            self.mqtt_client.disconnect()
            self.mqtt_status_label.setText("未连接")
            self.mqtt_status_label.setStyleSheet("color: red;")
            self.connect_mqtt_btn.setText("连接MQTT")
    
    def load_default_config(self):
        """加载默认配置"""
        # 尝试加载配置文件
        try:
            with open('config.json', 'r') as f:
                config = json.load(f)
                self.conf_spin.setValue(config.get('confidence_threshold', 0.5))
                self.iou_spin.setValue(config.get('iou_threshold', 0.5))
                self.collision_spin.setValue(config.get('collision_distance', 50))
                self.speed_spin.setValue(config.get('speed_threshold', 10))
        except FileNotFoundError:
            # 使用默认值
            pass
    
    def save_config(self):
        """保存配置"""
        config = {
            'confidence_threshold': self.conf_spin.value(),
            'iou_threshold': self.iou_spin.value(),
            'collision_distance': self.collision_spin.value(),
            'speed_threshold': self.speed_spin.value()
        }
        
        with open('config.json', 'w') as f:
            json.dump(config, f, indent=2)
    
    def update_detector_params(self):
        """更新检测器参数"""
        if self.video_processor and self.video_processor.detector:
            self.video_processor.set_detector_parameter('collision_distance_thresh', self.collision_spin.value())
            self.video_processor.set_detector_parameter('speed_threshold', self.speed_spin.value())
            
            # 更新模型参数 - 添加检查确保模型存在
            if hasattr(self.video_processor, 'model') and self.video_processor.model is not None:
                self.video_processor.model.conf = self.conf_spin.value()
                self.video_processor.model.iou = self.iou_spin.value()
    
    def update_visualization_settings(self):
        """更新可视化设置"""
        if self.video_processor and self.video_processor.detector:
            self.video_processor.detector.show_detections = self.show_detections_cb.isChecked()
            self.video_processor.detector.show_trajectories = self.show_trajectories_cb.isChecked()
            self.video_processor.detector.show_counting = self.show_counting_cb.isChecked()
            self.video_processor.detector.show_intrusion_zone = self.show_intrusion_zone_cb.isChecked()
    
    def load_video(self):
        """加载视频"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择视频文件", "", "视频文件 (*.mp4 *.avi *.mov *.mkv)"
        )
        
        if file_path:
            self.video_path = file_path
            QMessageBox.information(self, "成功", f"已加载视频: {file_path}")
    
    def load_weights(self):
        """加载模型权重"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择模型权重文件", "", "权重文件 (*.pt)"
        )
        
        if file_path:
            self.weights_path = file_path
            QMessageBox.information(self, "成功", f"已加载模型: {file_path}")
            
            # 检查是否可以启用开始按钮
            if self.video_path and self.weights_path:
                self.start_btn.setEnabled(True)
    
    def start_processing(self):
        """开始处理视频 - 修改为异步方式"""
        if not self.video_path or not self.weights_path:
            QMessageBox.warning(self, "错误", "请先加载视频和模型权重")
            return
        
        # 创建视频处理器
        self.video_processor = VideoProcessor(self.weights_path)
        
        # 设置MQTT客户端
        self.video_processor.set_mqtt_client(self.mqtt_client)
        
        # 连接信号
        self.video_processor.frame_processed.connect(self.update_video_display)
        self.video_processor.analysis_updated.connect(self.update_analysis_display)
        self.video_processor.event_detected.connect(self.add_event_log)
        self.video_processor.status_update.connect(self.update_status)
        
        # 初始化处理器 - 异步方式
        self.statusBar().showMessage("正在初始化模型...")
        self.video_processor.initialize()
        
        # 加载视频
        success, message = self.video_processor.load_video(self.video_path)
        if not success:
            QMessageBox.warning(self, "错误", message)
            return
        
        # 使用定时器检查初始化状态
        self.init_check_timer = QTimer()
        self.init_check_timer.timeout.connect(self.check_initialization_status)
        self.init_check_timer.start(100)  # 每100毫秒检查一次
        
    def check_initialization_status(self):
        """检查初始化状态"""
        if self.video_processor.initialization_failed:
            self.init_check_timer.stop()
            QMessageBox.warning(self, "错误", "处理器初始化失败")
            return

        if self.video_processor.initialized:
            self.init_check_timer.stop()

            # 在初始化后设置模型参数 - 确保模型已存在
            if hasattr(self.video_processor, 'model') and self.video_processor.model is not None:
                self.video_processor.model.conf = self.conf_spin.value()
                self.video_processor.model.iou = self.iou_spin.value()

            # 加载视频
            success, message = self.video_processor.load_video(self.video_path)
            if not success:
                QMessageBox.warning(self, "错误", message)
                return

            # 更新按钮状态
            self.start_btn.setEnabled(False)
            self.pause_btn.setEnabled(True)
            self.stop_btn.setEnabled(True)
            self.is_processing = True

            # 启动处理线程
            self.video_processor.start()
    
    def update_status(self, message):
        """更新状态信息"""
        self.statusBar().showMessage(message)

    def pause_processing(self):
        """暂停处理"""
        if self.video_processor and self.is_processing:
            if self.video_processor.is_paused:
                self.video_processor.resume()
                self.pause_btn.setText("暂停")
            else:
                self.video_processor.pause()
                self.pause_btn.setText("继续")
    
    def stop_processing(self):
        """停止处理"""
        if self.video_processor and self.is_processing:
            self.video_processor.stop()
            self.video_processor.wait()
            
            # 更新按钮状态
            self.start_btn.setEnabled(True)
            self.pause_btn.setEnabled(False)
            self.stop_btn.setEnabled(False)
            self.pause_btn.setText("暂停")
            self.is_processing = False
    
    def update_video_display(self, image, analysis_data):
        """更新视频显示"""
        print("更新视频显示")
        if image.isNull():
            print("接收到空图像")
            return
            
        pixmap = QPixmap.fromImage(image)
        if pixmap.isNull():
            print("转换后的QPixmap为空")
            return
            
        self.video_label.setPixmap(pixmap.scaled(
            self.video_label.width(), 
            self.video_label.height(),
            Qt.KeepAspectRatio
        ))
        
        # 更新统计信息
        frame_count = analysis_data.get('frame_count', 0)
        fps = analysis_data.get('fps', 0)
        event_count = analysis_data.get('event_count', 0)
        traffic_counts = analysis_data.get('traffic_counts', {})

        stats_text = f"帧数: {frame_count}\n"
        stats_text += f"FPS: {fps:.2f}\n"
        stats_text += f"事件总数: {event_count}\n"
        stats_text += "交通流量:\n"

        for vehicle_type, count in traffic_counts.items():
            if vehicle_type != 'total':
                stats_text += f"  {vehicle_type}: {count}\n"

        stats_text += f"  总计: {traffic_counts.get('total', 0)}"
        
        self.stats_text.setPlainText(stats_text)
    
    def update_analysis_display(self, analysis_data):
        """更新分析显示"""
        text = f"处理帧数: {analysis_data['frame_count']}\n"
        text += f"处理时间: {analysis_data['processing_time']:.2f}秒\n"
        text += f"平均FPS: {analysis_data['frame_count'] / analysis_data['processing_time']:.2f}\n"
        text += f"检测到事件: {len(analysis_data['events'])}个\n"
        text += f"检测到异常: {len(analysis_data['anomalies'])}个\n"
        
        self.analysis_label.setText(text)
    
    def add_event_log(self, event_data):
        """添加事件到日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {event_data['message']}"
        
        current_text = self.events_text.toPlainText()
        if current_text:
            new_text = current_text + "\n" + log_entry
        else:
            new_text = log_entry
            
        self.events_text.setPlainText(new_text)
        
        # 自动滚动到底部
        self.events_text.verticalScrollBar().setValue(
            self.events_text.verticalScrollBar().maximum()
        )
    
    def set_intrusion_zone(self):
        """设置闯入区域"""
        if not self.is_processing:
            QMessageBox.warning(self, "错误", "请先开始处理视频")
            return
        
        # 在实际应用中，这里应该实现一个交互式区域选择功能
        # 这里简化为固定区域
        zone_points = [(100, 100), (500, 100), (500, 500), (100, 500)]
        self.video_processor.set_intrusion_zone(zone_points)
        QMessageBox.information(self, "成功", "已设置闯入区域")
    
    def add_roi_zone(self):
        """添加ROI区域"""
        if not self.is_processing:
            QMessageBox.warning(self, "错误", "请先开始处理视频")
            return
        
        # 在实际应用中，这里应该实现一个交互式区域选择功能
        # 这里简化为固定区域
        zone_points = [(200, 200), (600, 200), (600, 600), (200, 600)]
        self.video_processor.detector.add_roi_zone(zone_points)
        QMessageBox.information(self, "成功", "已添加ROI区域")
    
    def add_counting_line(self):
        """添加计数线"""
        if not self.is_processing:
            QMessageBox.warning(self, "错误", "请先开始处理视频")
            return
        
        # 在实际应用中，这里应该实现一个交互式线选择功能
        # 这里简化为固定线
        start_point = (0, self.video_processor.height // 2)
        end_point = (self.video_processor.width, self.video_processor.height // 2)
        self.video_processor.add_counting_line(start_point, end_point)
        QMessageBox.information(self, "成功", "已添加计数线")
    
    def clear_counting_lines(self):
        """清除计数线"""
        if self.video_processor:
            self.video_processor.clear_counting_lines()
            QMessageBox.information(self, "成功", "已清除所有计数线")
    
    def generate_report(self):
        """生成报告"""
        if not self.video_processor or not self.video_processor.detector:
            QMessageBox.warning(self, "错误", "没有可用的分析数据")
            return
        
        report = self.video_processor.detector.generate_report()
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存报告", "", "JSON文件 (*.json)"
        )
        
        if file_path:
            with open(file_path, 'w') as f:
                json.dump(report, f, indent=2)
            
            QMessageBox.information(self, "成功", f"报告已保存到: {file_path}")
            
            # 通过MQTT发送报告
            if self.mqtt_client and self.mqtt_client.connected:
                self.mqtt_client.publish(MQTT_TOPIC_STATS, report)
    
    def closeEvent(self, event):
        """关闭事件"""
        if self.is_processing:
            self.stop_processing()
        
        if self.mqtt_client.connected:
            self.mqtt_client.disconnect()
        
        self.save_config()
        event.accept()

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()