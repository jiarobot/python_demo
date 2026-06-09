import sys
import os
from PyQt5.QtWidgets import QDialog
import cv2
import numpy as np
import time
import threading
import json
import math
import logging
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, asdict
from typing import List, Dict, Tuple, Optional, Any
import queue

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QPushButton, QLabel, QTabWidget, 
                            QGroupBox, QTextEdit, QSlider, QCheckBox,
                            QSpinBox, QDoubleSpinBox, QComboBox, QProgressBar,
                            QFileDialog, QMessageBox, QSplitter, QFrame,
                            QTableWidget, QTableWidgetItem, QHeaderView,
                            QTreeWidget, QTreeWidgetItem, QListWidget,
                            QLineEdit, QDial, QToolBar, QAction, QStatusBar,
                            QDockWidget, QFormLayout, QProgressDialog, 
                            QGridLayout, QScrollArea, QSizePolicy)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread, QSettings, QPointF, QRectF, QSize
from PyQt5.QtGui import (QImage, QPixmap, QFont, QPalette, QColor, QPen, 
                        QBrush, QPainter, QIcon, QKeySequence, QMouseEvent,
                        QFontDatabase)
import matplotlib
matplotlib.rc("font", family='Microsoft YaHei')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d import Axes3D
import matplotlib.patches as patches

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ==================== 增强的计算机视觉模块 ====================
class EnhancedCV:
    @staticmethod
    def detect_aruco_markers(frame, dictionary=cv2.aruco.DICT_4X4_50):
        """检测ArUco标记"""
        try:
            aruco_dict = cv2.aruco.getPredefinedDictionary(dictionary)
            parameters = cv2.aruco.DetectorParameters()
            detector = cv2.aruco.ArucoDetector(aruco_dict, parameters)
            
            corners, ids, rejected = detector.detectMarkers(frame)
            return corners, ids, rejected
        except Exception as e:
            logger.error(f"ArUco检测错误: {e}")
            return None, None, None
    
    @staticmethod
    def estimate_pose_single_marker(corners, marker_size, camera_matrix, dist_coeffs):
        """估计单个标记的姿态"""
        try:
            rvecs, tvecs, _ = cv2.aruco.estimatePoseSingleMarkers(
                corners, marker_size, camera_matrix, dist_coeffs)
            return rvecs, tvecs
        except Exception as e:
            logger.error(f"姿态估计错误: {e}")
            return None, None
    
    @staticmethod
    def optical_flow_lk(prev_frame, current_frame, points, win_size=(15, 15)):
        """Lucas-Kanade光流"""
        if prev_frame is None or points is None or len(points) == 0:
            return None, None, None
            
        try:
            prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
            curr_gray = cv2.cvtColor(current_frame, cv2.COLOR_BGR2GRAY)
            
            new_points, status, error = cv2.calcOpticalFlowPyrLK(
                prev_gray, curr_gray, points, None, winSize=win_size, maxLevel=3)
            
            return new_points, status, error
        except Exception as e:
            logger.error(f"光流计算错误: {e}")
            return None, None, None
    
    @staticmethod
    def feature_matching(frame1, frame2, method='ORB'):
        """特征点匹配"""
        try:
            if method == 'ORB':
                detector = cv2.ORB_create(nfeatures=1000)
            elif method == 'SIFT':
                detector = cv2.SIFT_create()
            elif method == 'AKAZE':
                detector = cv2.AKAZE_create()
            else:
                detector = cv2.ORB_create(nfeatures=1000)
            
            kp1, des1 = detector.detectAndCompute(frame1, None)
            kp2, des2 = detector.detectAndCompute(frame2, None)
            
            if des1 is None or des2 is None:
                return [], [], []
            
            if method == 'SIFT':
                matcher = cv2.BFMatcher(cv2.NORM_L2, crossCheck=True)
            else:
                matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
            
            matches = matcher.match(des1, des2)
            matches = sorted(matches, key=lambda x: x.distance)
            
            return kp1, kp2, matches
        except Exception as e:
            logger.error(f"特征匹配错误: {e}")
            return [], [], []
    
    @staticmethod
    def estimate_homography(kp1, kp2, matches, min_matches=10):
        """估计单应性矩阵"""
        if len(matches) < min_matches:
            return None
        
        try:
            src_pts = np.float32([kp1[m.queryIdx].pt for m in matches]).reshape(-1, 1, 2)
            dst_pts = np.float32([kp2[m.trainIdx].pt for m in matches]).reshape(-1, 1, 2)
            
            H, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
            return H
        except Exception as e:
            logger.error(f"单应性矩阵估计错误: {e}")
            return None
    
    @staticmethod
    def depth_from_motion(frame1, frame2, camera_matrix):
        """从运动中估计深度"""
        try:
            kp1, kp2, matches = EnhancedCV.feature_matching(frame1, frame2)
            
            if len(matches) < 8:
                return None
            
            src_pts = np.float32([kp1[m.queryIdx].pt for m in matches]).reshape(-1, 1, 2)
            dst_pts = np.float32([kp2[m.trainIdx].pt for m in matches]).reshape(-1, 1, 2)
            
            E, mask = cv2.findEssentialMat(src_pts, dst_pts, camera_matrix, method=cv2.RANSAC, prob=0.999, threshold=1.0)
            
            if E is None:
                return None
            
            _, R, t, mask = cv2.recoverPose(E, src_pts, dst_pts, camera_matrix)
            points_4d = EnhancedCV.triangulate_points(src_pts, dst_pts, R, t, camera_matrix)
            
            return points_4d
        except Exception as e:
            logger.error(f"深度估计错误: {e}")
            return None
    
    @staticmethod
    def triangulate_points(pts1, pts2, R, t, camera_matrix):
        """三角测量得到3D点"""
        try:
            P1 = np.hstack((np.eye(3), np.zeros((3, 1))))
            P2 = np.hstack((R, t))
            
            P1 = camera_matrix @ P1
            P2 = camera_matrix @ P2
            
            points_4d = cv2.triangulatePoints(P1, P2, pts1.reshape(-1, 2).T, pts2.reshape(-1, 2).T)
            points_3d = points_4d[:3] / points_4d[3]
            
            return points_3d.T
        except Exception as e:
            logger.error(f"三角测量错误: {e}")
            return None
    
    @staticmethod
    def detect_objects_yolo(frame, net, classes, conf_threshold=0.5, nms_threshold=0.4):
        """使用YOLO进行目标检测"""
        try:
            height, width = frame.shape[:2]
            
            # 准备输入
            blob = cv2.dnn.blobFromImage(frame, 1/255.0, (416, 416), swapRB=True, crop=False)
            net.setInput(blob)
            
            # 前向传播
            outputs = net.forward()
            
            boxes = []
            confidences = []
            class_ids = []
            
            for output in outputs:
                for detection in output:
                    scores = detection[5:]
                    class_id = np.argmax(scores)
                    confidence = scores[class_id]
                    
                    if confidence > conf_threshold:
                        center_x = int(detection[0] * width)
                        center_y = int(detection[1] * height)
                        w = int(detection[2] * width)
                        h = int(detection[3] * height)
                        
                        x = int(center_x - w / 2)
                        y = int(center_y - h / 2)
                        
                        boxes.append([x, y, w, h])
                        confidences.append(float(confidence))
                        class_ids.append(class_id)
            
            # 非极大值抑制
            indices = cv2.dnn.NMSBoxes(boxes, confidences, conf_threshold, nms_threshold)
            
            results = []
            if len(indices) > 0:
                for i in indices.flatten():
                    x, y, w, h = boxes[i]
                    results.append({
                        'class_id': class_ids[i],
                        'class_name': classes[class_ids[i]],
                        'confidence': confidences[i],
                        'bbox': (x, y, w, h)
                    })
            
            return results
        except Exception as e:
            logger.error(f"YOLO检测错误: {e}")
            return []

# ==================== 高级路径规划模块 ====================
class AdvancedPathPlanner:
    def __init__(self):
        self.obstacles = []
        self.boundaries = [(-10, 10), (-10, 10), (0, 10)]
        self.grid_size = 0.5
        self.safety_margin = 0.3
        
    def set_obstacles(self, obstacles):
        """设置障碍物"""
        self.obstacles = obstacles
    
    def set_boundaries(self, boundaries):
        """设置边界"""
        self.boundaries = boundaries
    
    def a_star_path(self, start, goal):
        """A*路径规划算法"""
        open_set = {start}
        closed_set = set()
        g_score = {start: 0}
        f_score = {start: self.heuristic(start, goal)}
        came_from = {}
        
        while open_set:
            current = min(open_set, key=lambda x: f_score.get(x, float('inf')))
            
            if self.distance(current, goal) < 0.5:  # 到达目标阈值
                return self.reconstruct_path(came_from, current)
            
            open_set.remove(current)
            closed_set.add(current)
            
            for neighbor in self.get_neighbors(current):
                if neighbor in closed_set or self.is_collision(neighbor):
                    continue
                
                tentative_g_score = g_score[current] + self.distance(current, neighbor)
                
                if neighbor not in open_set:
                    open_set.add(neighbor)
                elif tentative_g_score >= g_score.get(neighbor, float('inf')):
                    continue
                
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g_score
                f_score[neighbor] = g_score[neighbor] + self.heuristic(neighbor, goal)
        
        return None
    
    def rrt_path(self, start, goal, max_iterations=1000):
        """RRT路径规划算法"""
        tree = {start: None}
        
        for i in range(max_iterations):
            # 随机采样（90%朝向目标，10%完全随机）
            if np.random.random() < 0.9:
                sample = goal
            else:
                sample = self.random_sample()
            
            nearest = self.find_nearest(tree, sample)
            new_node = self.steer(nearest, sample, step_size=1.0)
            
            if not self.is_collision(new_node) and not self.is_collision_edge(nearest, new_node):
                tree[new_node] = nearest
                
                if self.distance(new_node, goal) < 0.5:
                    return self.reconstruct_path(tree, new_node)
        
        return None
    
    def find_nearest(self, tree, point):
        """在树中找到最近的点"""
        min_dist = float('inf')
        nearest = None
        
        for node in tree:
            dist = self.distance(node, point)
            if dist < min_dist:
                min_dist = dist
                nearest = node
        
        return nearest
    
    def steer(self, from_node, to_node, step_size):
        """从from_node向to_node方向移动step_size距离"""
        direction = np.array(to_node) - np.array(from_node)
        distance = np.linalg.norm(direction)
        
        if distance <= step_size:
            return to_node
        
        direction = direction / distance
        new_point = np.array(from_node) + direction * step_size
        
        return tuple(new_point)
    
    def is_collision_edge(self, point1, point2):
        """检查两点之间的边是否碰撞"""
        # 在两点之间采样多个点进行检查
        num_samples = max(3, int(self.distance(point1, point2) / self.grid_size))
        
        for i in range(num_samples + 1):
            alpha = i / num_samples
            sample_point = (
                point1[0] + alpha * (point2[0] - point1[0]),
                point1[1] + alpha * (point2[1] - point1[1]),
                point1[2] + alpha * (point2[2] - point1[2])
            )
            
            if self.is_collision(sample_point):
                return True
        
        return False
    
    def heuristic(self, a, b):
        """启发式函数"""
        return math.sqrt((a[0]-b[0])**2 + (a[1]-b[1])**2 + (a[2]-b[2])**2)
    
    def distance(self, a, b):
        """两点间距离"""
        return self.heuristic(a, b)
    
    def get_neighbors(self, point):
        """获取邻居点"""
        neighbors = []
        for dx in [-self.grid_size, 0, self.grid_size]:
            for dy in [-self.grid_size, 0, self.grid_size]:
                for dz in [-self.grid_size, 0, self.grid_size]:
                    if dx == 0 and dy == 0 and dz == 0:
                        continue
                    
                    neighbor = (
                        point[0] + dx,
                        point[1] + dy,
                        point[2] + dz
                    )
                    
                    if self.is_in_boundaries(neighbor):
                        neighbors.append(neighbor)
        
        return neighbors
    
    def random_sample(self):
        """随机采样点"""
        x = np.random.uniform(self.boundaries[0][0], self.boundaries[0][1])
        y = np.random.uniform(self.boundaries[1][0], self.boundaries[1][1])
        z = np.random.uniform(self.boundaries[2][0], self.boundaries[2][1])
        
        return (x, y, z)
    
    def is_in_boundaries(self, point):
        """检查点是否在边界内"""
        return (self.boundaries[0][0] <= point[0] <= self.boundaries[0][1] and
                self.boundaries[1][0] <= point[1] <= self.boundaries[1][1] and
                self.boundaries[2][0] <= point[2] <= self.boundaries[2][1])
    
    def is_collision(self, point):
        """检查是否与障碍物碰撞"""
        for obstacle in self.obstacles:
            if len(obstacle) >= 4:  # (x,y,z,radius) 格式
                if self.distance(point, obstacle[:3]) < obstacle[3] + self.safety_margin:
                    return True
        return False
    
    def reconstruct_path(self, came_from, current):
        """重建路径"""
        path = [current]
        while current in came_from:
            current = came_from[current]
            path.append(current)
        path.reverse()
        return path

# ==================== 增强的PID控制器 ====================
class EnhancedPIDController:
    def __init__(self, kp, ki, kd, setpoint=0, output_limits=(-1, 1), 
                 integral_windup_guard=20.0, dt=0.01):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.setpoint = setpoint
        self.output_limits = output_limits
        self.integral_windup_guard = integral_windup_guard
        self.dt = dt
        
        self.integral = 0
        self.previous_error = 0
        self.previous_time = time.time()
        self.previous_output = 0
        
        # 低通滤波器用于微分项
        self.alpha = 0.8  # 滤波系数
        
    def update(self, current_value, dt=None):
        """更新PID控制器"""
        if dt is None:
            current_time = time.time()
            dt = current_time - self.previous_time
            self.previous_time = current_time
        
        if dt <= 0:
            return self.previous_output
        
        error = self.setpoint - current_value
        
        # 比例项
        proportional = self.kp * error
        
        # 积分项（带抗饱和）
        self.integral += error * dt
        self.integral = max(min(self.integral, self.integral_windup_guard), -self.integral_windup_guard)
        integral = self.ki * self.integral
        
        # 微分项（带滤波）
        derivative = (error - self.previous_error) / dt
        filtered_derivative = self.alpha * derivative + (1 - self.alpha) * self.previous_error / dt
        derivative_term = self.kd * filtered_derivative
        
        # 计算输出
        output = proportional + integral + derivative_term
        
        # 限制输出
        output = max(self.output_limits[0], min(self.output_limits[1], output))
        
        # 更新状态
        self.previous_error = error
        self.previous_output = output
        
        return output
    
    def set_setpoint(self, setpoint):
        """设置目标值"""
        self.setpoint = setpoint
    
    def reset(self):
        """重置控制器"""
        self.integral = 0
        self.previous_error = 0
        self.previous_time = time.time()
        self.previous_output = 0

# ==================== 飞行器状态和数据类 ====================
class DroneState(Enum):
    DISCONNECTED = 0
    CONNECTED = 1
    TAKING_OFF = 2
    HOVERING = 3
    FLYING = 4
    LANDING = 5
    EMERGENCY = 6
    RETURNING_HOME = 7

@dataclass
class DroneStatus:
    state: DroneState
    battery: float
    position: Tuple[float, float, float]
    velocity: Tuple[float, float, float]
    orientation: Tuple[float, float, float]  # 欧拉角 (roll, pitch, yaw)
    timestamp: float
    home_position: Tuple[float, float, float] = (0, 0, 0)
    
    def to_dict(self):
        return asdict(self)

# ==================== 高级飞行器控制器 ====================
class AdvancedDroneController:
    def __init__(self, simulation=True):
        self.simulation = simulation
        self.status = DroneStatus(
            state=DroneState.DISCONNECTED,
            battery=100.0,
            position=(0.0, 0.0, 0.0),
            velocity=(0.0, 0.0, 0.0),
            orientation=(0.0, 0.0, 0.0),
            timestamp=time.time(),
            home_position=(0.0, 0.0, 0.0)
        )
        
        # PID控制器
        self.x_pid = EnhancedPIDController(0.8, 0.02, 0.15)
        self.y_pid = EnhancedPIDController(0.8, 0.02, 0.15)
        self.z_pid = EnhancedPIDController(1.0, 0.03, 0.2)
        self.yaw_pid = EnhancedPIDController(0.5, 0.01, 0.08)
        
        # 路径规划器
        self.path_planner = AdvancedPathPlanner()
        self.current_path = []
        self.path_index = 0
        self.following_path = False
        
        # 任务系统
        self.task_queue = queue.Queue()
        self.current_task = None
        self.task_thread = None
        self.task_running = False
        
        # 视觉系统
        self.camera_matrix = np.array([
            [800, 0, 320],
            [0, 800, 240],
            [0, 0, 1]
        ], dtype=np.float32)
        self.dist_coeffs = np.zeros((4, 1))
        
        # 数据记录
        self.flight_data = []
        self.log = []
        
        # 安全参数
        self.max_altitude = 10.0
        self.max_speed = 2.0
        self.safe_distance = 1.0
        
        # 控制线程
        self.control_thread = None
        self.control_running = False
        
    def connect(self):
        """连接飞行器"""
        try:
            if self.simulation:
                time.sleep(1)
                self.status.state = DroneState.CONNECTED
                self.status.home_position = self.status.position
                self.log_event("飞行器已连接（模拟模式）", "INFO")
                return True
            else:
                # 实际连接代码
                pass
        except Exception as e:
            self.log_event(f"连接失败: {e}", "ERROR")
            return False
    
    def disconnect(self):
        """断开连接"""
        self.stop_control_loop()
        self.stop_task_execution()
        self.status.state = DroneState.DISCONNECTED
        self.log_event("飞行器已断开连接", "INFO")
    
    def start_control_loop(self):
        """开始控制循环"""
        if self.control_running:
            return
        
        self.control_running = True
        self.control_thread = threading.Thread(target=self._control_loop, daemon=True)
        self.control_thread.start()
        self.log_event("控制循环已启动", "INFO")
    
    def stop_control_loop(self):
        """停止控制循环"""
        self.control_running = False
        if self.control_thread:
            self.control_thread.join(timeout=2)
        self.log_event("控制循环已停止", "INFO")
    
    def _control_loop(self):
        """控制循环"""
        while self.control_running:
            try:
                self.update_control()
                time.sleep(0.01)  # 100Hz控制频率
            except Exception as e:
                self.log_event(f"控制循环错误: {e}", "ERROR")
                time.sleep(0.1)
    
    def takeoff(self, altitude=2.0):
        """起飞到指定高度"""
        if self.status.state != DroneState.CONNECTED:
            return False
        
        if altitude > self.max_altitude:
            self.log_event(f"起飞高度超过限制: {altitude}m > {self.max_altitude}m", "WARNING")
            return False
        
        self.status.state = DroneState.TAKING_OFF
        self.z_pid.set_setpoint(altitude)
        self.log_event(f"开始起飞到 {altitude} 米", "INFO")
        
        if self.simulation:
            def takeoff_process():
                start_time = time.time()
                while time.time() - start_time < 3:
                    progress = (time.time() - start_time) / 3
                    current_altitude = min(altitude, progress * altitude)
                    
                    self.status.position = (
                        self.status.position[0],
                        self.status.position[1],
                        current_altitude
                    )
                    time.sleep(0.1)
                
                self.status.state = DroneState.HOVERING
                self.status.position = (self.status.position[0], self.status.position[1], altitude)
                self.log_event("起飞完成", "INFO")
            
            threading.Thread(target=takeoff_process, daemon=True).start()
        
        return True
    
    def land(self):
        """降落"""
        if self.status.state not in [DroneState.HOVERING, DroneState.FLYING]:
            return False
        
        self.status.state = DroneState.LANDING
        self.z_pid.set_setpoint(0)
        self.log_event("开始降落", "INFO")
        
        if self.simulation:
            def land_process():
                start_altitude = self.status.position[2]
                start_time = time.time()
                
                while self.status.position[2] > 0.1:
                    elapsed = time.time() - start_time
                    progress = elapsed / (start_altitude / 0.5)  # 以0.5m/s速度下降
                    
                    if progress >= 1:
                        break
                    
                    self.status.position = (
                        self.status.position[0],
                        self.status.position[1],
                        max(0, start_altitude * (1 - progress))
                    )
                    time.sleep(0.1)
                
                self.status.state = DroneState.CONNECTED
                self.status.position = (self.status.position[0], self.status.position[1], 0.0)
                self.log_event("降落完成", "INFO")
            
            threading.Thread(target=land_process, daemon=True).start()
        
        return True
    
    def goto_position(self, x, y, z, yaw=0):
        """飞到指定位置"""
        if self.status.state not in [DroneState.HOVERING, DroneState.FLYING]:
            return False
        
        # 安全检查
        if z > self.max_altitude:
            self.log_event(f"目标高度超过限制: {z}m > {self.max_altitude}m", "WARNING")
            return False
        
        # 设置PID目标
        self.x_pid.set_setpoint(x)
        self.y_pid.set_setpoint(y)
        self.z_pid.set_setpoint(z)
        self.yaw_pid.set_setpoint(yaw)
        
        self.status.state = DroneState.FLYING
        self.log_event(f"飞往位置 ({x:.2f}, {y:.2f}, {z:.2f}), 偏航角 {yaw:.2f}", "INFO")
        return True
    
    def follow_path(self, path):
        """跟随路径"""
        if not path or len(path) < 2:
            return False
        
        self.current_path = path
        self.path_index = 0
        self.following_path = True
        
        self.goto_position(*path[0])
        self.log_event(f"开始跟随路径，共 {len(path)} 个点", "INFO")
        return True
    
    def return_to_home(self):
        """返回起飞点"""
        home_pos = self.status.home_position
        self.goto_position(home_pos[0], home_pos[1], home_pos[2])
        self.status.state = DroneState.RETURNING_HOME
        self.log_event("返回起飞点", "INFO")
    
    def emergency_stop(self):
        """紧急停止"""
        self.status.state = DroneState.EMERGENCY
        self.following_path = False
        self.stop_task_execution()
        self.log_event("紧急停止", "CRITICAL")
        
        # 在模拟中立即悬停
        if self.simulation:
            self.status.state = DroneState.HOVERING
    
    def update_control(self):
        """更新控制"""
        if self.status.state not in [DroneState.FLYING, DroneState.TAKING_OFF, 
                                   DroneState.LANDING, DroneState.RETURNING_HOME]:
            return
        
        # 计算控制输出
        x_output = self.x_pid.update(self.status.position[0])
        y_output = self.y_pid.update(self.status.position[1])
        z_output = self.z_pid.update(self.status.position[2])
        yaw_output = self.yaw_pid.update(self.status.orientation[2])
        
        # 模拟飞行器运动
        if self.simulation:
            dt = 0.01
            
            # 更新位置（简化模型）
            new_x = self.status.position[0] + x_output * dt
            new_y = self.status.position[1] + y_output * dt
            new_z = self.status.position[2] + z_output * dt
            new_yaw = self.status.orientation[2] + yaw_output * dt
            
            # 限制速度
            dx = new_x - self.status.position[0]
            dy = new_y - self.status.position[1]
            dz = new_z - self.status.position[2]
            
            speed = math.sqrt(dx**2 + dy**2 + dz**2) / dt
            if speed > self.max_speed:
                scale = self.max_speed / speed
                dx *= scale
                dy *= scale
                dz *= scale
            
            self.status.position = (
                self.status.position[0] + dx,
                self.status.position[1] + dy,
                self.status.position[2] + dz
            )
            self.status.orientation = (0, 0, new_yaw)
            
            # 路径跟随
            self._update_path_following()
        
        # 记录数据
        self._record_flight_data()
    
    def _update_path_following(self):
        """更新路径跟随"""
        if self.following_path and self.path_index < len(self.current_path):
            current_target = self.current_path[self.path_index]
            distance = math.sqrt(
                (self.status.position[0] - current_target[0])**2 +
                (self.status.position[1] - current_target[1])**2 +
                (self.status.position[2] - current_target[2])**2
            )
            
            if distance < 0.2:  # 到达阈值
                self.path_index += 1
                if self.path_index < len(self.current_path):
                    self.goto_position(*self.current_path[self.path_index])
                    self.log_event(f"到达路径点 {self.path_index-1}，前往点 {self.path_index}", "INFO")
                else:
                    self.following_path = False
                    self.status.state = DroneState.HOVERING
                    self.log_event("路径跟随完成", "INFO")
    
    def start_task_execution(self):
        """开始任务执行"""
        if self.task_running:
            return
        
        self.task_running = True
        self.task_thread = threading.Thread(target=self._task_execution_loop, daemon=True)
        self.task_thread.start()
        self.log_event("任务执行已启动", "INFO")
    
    def stop_task_execution(self):
        """停止任务执行"""
        self.task_running = False
        with self.task_queue.mutex:
            self.task_queue.queue.clear()
        self.current_task = None
        self.log_event("任务执行已停止", "INFO")
    
    def _task_execution_loop(self):
        """任务执行循环"""
        while self.task_running:
            try:
                if self.current_task is None:
                    # 获取新任务
                    try:
                        self.current_task = self.task_queue.get(timeout=0.1)
                        self._execute_task(self.current_task)
                    except queue.Empty:
                        continue
                else:
                    # 检查当前任务是否完成
                    if self._is_task_completed(self.current_task):
                        self.task_queue.task_done()
                        self.current_task = None
                    time.sleep(0.1)
            except Exception as e:
                self.log_event(f"任务执行错误: {e}", "ERROR")
                time.sleep(0.1)
    
    def add_task(self, task_type, **params):
        """添加任务"""
        task = {
            'type': task_type,
            'params': params,
            'status': 'pending',
            'created': time.time(),
            'id': len(self.flight_data)  # 使用飞行数据长度作为ID
        }
        
        self.task_queue.put(task)
        self.log_event(f"添加任务: {task_type} - {params}", "INFO")
    
    def _execute_task(self, task):
        """执行任务"""
        task['status'] = 'executing'
        task['started'] = time.time()
        
        task_type = task['type']
        params = task['params']
        
        self.log_event(f"开始执行任务: {task_type}", "INFO")
        
        if task_type == 'takeoff':
            self.takeoff(params.get('altitude', 2.0))
        elif task_type == 'land':
            self.land()
        elif task_type == 'goto':
            self.goto_position(
                params.get('x', 0),
                params.get('y', 0),
                params.get('z', 2),
                params.get('yaw', 0)
            )
        elif task_type == 'follow_path':
            self.follow_path(params.get('path', []))
        elif task_type == 'hover':
            task['hover_end_time'] = time.time() + params.get('duration', 5)
        elif task_type == 'return_home':
            self.return_to_home()
        elif task_type == 'emergency_stop':
            self.emergency_stop()
    
    def _is_task_completed(self, task):
        """检查任务是否完成"""
        task_type = task['type']
        
        if task_type == 'takeoff':
            return self.status.state == DroneState.HOVERING
        elif task_type == 'land':
            return self.status.state == DroneState.CONNECTED
        elif task_type == 'goto':
            target_pos = (
                task['params'].get('x', 0),
                task['params'].get('y', 0),
                task['params'].get('z', 2)
            )
            distance = math.sqrt(
                (self.status.position[0] - target_pos[0])**2 +
                (self.status.position[1] - target_pos[1])**2 +
                (self.status.position[2] - target_pos[2])**2
            )
            return distance < 0.2 and self.status.state == DroneState.HOVERING
        elif task_type == 'follow_path':
            return not self.following_path
        elif task_type == 'hover':
            return time.time() >= task.get('hover_end_time', 0)
        elif task_type in ['return_home', 'emergency_stop']:
            return True
        
        return False
    
    def _record_flight_data(self):
        """记录飞行数据"""
        data_point = {
            'timestamp': time.time(),
            'position': self.status.position,
            'orientation': self.status.orientation,
            'battery': self.status.battery,
            'state': self.status.state.name
        }
        self.flight_data.append(data_point)
        
        # 限制数据量
        if len(self.flight_data) > 10000:
            self.flight_data = self.flight_data[-5000:]
    
    def log_event(self, message, level="INFO"):
        """记录事件"""
        timestamp = datetime.now()
        log_entry = {
            'timestamp': timestamp,
            'level': level,
            'message': message,
            'position': self.status.position,
            'state': self.status.state.name
        }
        self.log.append(log_entry)
        
        # 限制日志量
        if len(self.log) > 1000:
            self.log = self.log[-500:]
        
        # 输出到控制台
        if level == "ERROR":
            logger.error(f"{timestamp} - {message}")
        elif level == "WARNING":
            logger.warning(f"{timestamp} - {message}")
        elif level == "CRITICAL":
            logger.critical(f"{timestamp} - {message}")
        else:
            logger.info(f"{timestamp} - {message}")
    
    def get_status_dict(self):
        """获取状态字典"""
        return self.status.to_dict()
    
    def save_flight_data(self, filename=None):
        """保存飞行数据"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"flight_data_{timestamp}.json"
        
        try:
            with open(filename, 'w') as f:
                json.dump(self.flight_data, f, indent=2)
            self.log_event(f"飞行数据已保存: {filename}", "INFO")
            return True
        except Exception as e:
            self.log_event(f"保存飞行数据失败: {e}", "ERROR")
            return False

# ==================== 高级3D可视化组件 ====================
class Advanced3DViewer(QWidget):
    update_signal = pyqtSignal()
    
    def __init__(self, drone_controller):
        super().__init__()
        self.drone = drone_controller
        self.figure = Figure(figsize=(8, 6))
        self.canvas = FigureCanvas(self.figure)
        self.ax = self.figure.add_subplot(111, projection='3d')
        
        # 可视化数据
        self.trajectory_points = []
        self.obstacles = []
        self.path_points = []
        self.view_angle = (30, -45)  # elev, azim
        
        # 初始化视图
        self.init_3d_view()
        
        # 布局
        layout = QVBoxLayout()
        
        # 控制面板
        control_layout = QHBoxLayout()
        self.reset_view_btn = QPushButton("重置视图")
        self.toggle_trajectory_btn = QPushButton("隐藏轨迹")
        self.save_view_btn = QPushButton("保存视图")
        
        self.reset_view_btn.clicked.connect(self.reset_view)
        self.toggle_trajectory_btn.clicked.connect(self.toggle_trajectory)
        self.save_view_btn.clicked.connect(self.save_view)
        
        control_layout.addWidget(self.reset_view_btn)
        control_layout.addWidget(self.toggle_trajectory_btn)
        control_layout.addWidget(self.save_view_btn)
        control_layout.addStretch()
        
        layout.addLayout(control_layout)
        layout.addWidget(self.canvas)
        
        self.setLayout(layout)
        
        # 定时更新
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_view)
        self.timer.start(100)  # 10Hz更新
        
        self.show_trajectory = True
    
    def init_3d_view(self):
        """初始化3D视图"""
        self.ax.clear()
        self.ax.set_xlabel('X (m)')
        self.ax.set_ylabel('Y (m)')
        self.ax.set_zlabel('Z (m)')
        self.ax.set_xlim(-5, 5)
        self.ax.set_ylim(-5, 5)
        self.ax.set_zlim(0, 10)
        self.ax.set_title('飞行器3D视图')
        self.ax.view_init(*self.view_angle)
    
    def update_view(self):
        """更新视图"""
        try:
            self.ax.clear()
            
            # 获取飞行器状态
            status = self.drone.status
            
            # 绘制飞行器
            x, y, z = status.position
            roll, pitch, yaw = status.orientation
            
            # 飞行器模型（简化的四旋翼）
            self.draw_drone_model(x, y, z, roll, pitch, yaw)
            
            # 绘制轨迹
            if self.show_trajectory and self.drone.flight_data:
                trajectory = np.array([data['position'] for data in self.drone.flight_data[-100:]])  # 最近100个点
                if len(trajectory) > 1:
                    self.ax.plot(trajectory[:, 0], trajectory[:, 1], trajectory[:, 2], 
                                'b-', alpha=0.7, linewidth=2, label='轨迹')
            
            # 绘制路径
            if self.drone.current_path:
                path_array = np.array(self.drone.current_path)
                self.ax.plot(path_array[:, 0], path_array[:, 1], path_array[:, 2], 
                            'g--', linewidth=2, label='计划路径')
                self.ax.scatter(path_array[:, 0], path_array[:, 1], path_array[:, 2], 
                               c='green', marker='o', s=50, alpha=0.7)
            
            # 绘制障碍物
            for obstacle in self.obstacles:
                if len(obstacle) >= 4:
                    x_obs, y_obs, z_obs, r_obs = obstacle
                    u = np.linspace(0, 2 * np.pi, 20)
                    v = np.linspace(0, np.pi, 20)
                    X = r_obs * np.outer(np.cos(u), np.sin(v)) + x_obs
                    Y = r_obs * np.outer(np.sin(u), np.sin(v)) + y_obs
                    Z = r_obs * np.outer(np.ones(np.size(u)), np.cos(v)) + z_obs
                    self.ax.plot_surface(X, Y, Z, color='red', alpha=0.3)
            
            # 绘制起飞点
            home = status.home_position
            self.ax.scatter(home[0], home[1], home[2], c='yellow', 
                           marker='*', s=200, label='起飞点')
            
            self.ax.set_xlabel('X (m)')
            self.ax.set_ylabel('Y (m)')
            self.ax.set_zlabel('Z (m)')
            self.ax.set_xlim(-5, 5)
            self.ax.set_ylim(-5, 5)
            self.ax.set_zlim(0, 10)
            self.ax.legend()
            self.ax.view_init(*self.view_angle)
            
            self.canvas.draw()
        except Exception as e:
            logger.error(f"3D视图更新错误: {e}")
    
    def draw_drone_model(self, x, y, z, roll, pitch, yaw):
        """绘制飞行器模型"""
        # 机身
        self.ax.scatter(x, y, z, c='blue', marker='o', s=100, label='飞行器')
        
        # 方向指示
        arrow_length = 0.5
        dx = arrow_length * math.cos(yaw) * math.cos(pitch)
        dy = arrow_length * math.sin(yaw) * math.cos(pitch)
        dz = arrow_length * math.sin(pitch)
        
        self.ax.quiver(x, y, z, dx, dy, dz, color='red', 
                      length=arrow_length, arrow_length_ratio=0.3)
        
        # 旋翼（简化的十字形）
        arm_length = 0.3
        angles = [0, math.pi/2, math.pi, 3*math.pi/2]
        
        for angle in angles:
            arm_dx = arm_length * math.cos(yaw + angle)
            arm_dy = arm_length * math.sin(yaw + angle)
            
            self.ax.plot([x, x + arm_dx], [y, y + arm_dy], [z, z], 
                        'k-', linewidth=2)
    
    def set_obstacles(self, obstacles):
        """设置障碍物"""
        self.obstacles = obstacles
    
    def reset_view(self):
        """重置视图"""
        self.view_angle = (30, -45)
        self.init_3d_view()
    
    def toggle_trajectory(self):
        """切换轨迹显示"""
        self.show_trajectory = not self.show_trajectory
        if self.show_trajectory:
            self.toggle_trajectory_btn.setText("隐藏轨迹")
        else:
            self.toggle_trajectory_btn.setText("显示轨迹")
    
    def save_view(self):
        """保存当前视图"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"3d_view_{timestamp}.png"
            self.figure.savefig(filename, dpi=300, bbox_inches='tight')
            logger.info(f"3D视图已保存: {filename}")
        except Exception as e:
            logger.error(f"保存3D视图失败: {e}")

# ==================== 增强的视频处理线程 ====================
class EnhancedVideoThread(QThread):
    frame_signal = pyqtSignal(np.ndarray)
    processing_data_signal = pyqtSignal(dict)
    detection_signal = pyqtSignal(dict)
    
    def __init__(self, camera_source=0):
        super().__init__()
        self.camera_source = camera_source
        self.running = False
        self.cap = None
        
        # 处理参数
        self.process_enabled = True
        self.detection_enabled = False
        self.aruco_enabled = False
        self.optical_flow_enabled = False
        self.feature_matching_enabled = False
        self.yolo_enabled = False
        
        # 相机参数
        self.camera_matrix = np.array([
            [800, 0, 320],
            [0, 800, 240],
            [0, 0, 1]
        ], dtype=np.float32)
        self.dist_coeffs = np.zeros((4, 1))
        
        # 光流跟踪
        self.prev_frame = None
        self.prev_points = None
        
        # YOLO模型
        self.yolo_net = None
        self.yolo_classes = []
        self.load_yolo_model()
    
    def load_yolo_model(self):
        """加载YOLO模型"""
        try:
            # 这里需要YOLO的配置文件和权重文件
            # 你可以从 https://pjreddie.com/darknet/yolo/ 下载
            config_path = "yolov3-tiny.cfg"
            weights_path = "yolov3-tiny.weights"
            classes_path = "coco.names"
            
            if os.path.exists(classes_path):
                with open(classes_path, 'r') as f:
                    self.yolo_classes = [line.strip() for line in f.readlines()]
                
                if os.path.exists(config_path) and os.path.exists(weights_path):
                    self.yolo_net = cv2.dnn.readNetFromDarknet(config_path, weights_path)
                    logger.info("YOLO模型加载成功")
                else:
                    logger.warning("YOLO配置文件或权重文件不存在")
            else:
                logger.warning("COCO类别文件不存在")
        except Exception as e:
            logger.error(f"加载YOLO模型失败: {e}")
    
    def run(self):
        """主循环"""
        self.running = True
        
        try:
            self.cap = cv2.VideoCapture(self.camera_source)
            if not self.cap.isOpened():
                logger.error("无法打开摄像头")
                return
            
            logger.info("视频线程开始运行")
            
            while self.running:
                ret, frame = self.cap.read()
                if not ret:
                    logger.warning("读取帧失败")
                    time.sleep(0.1)
                    continue
                
                processed_frame = frame.copy()
                processing_data = {}
                
                if self.process_enabled:
                    # 图像预处理
                    processed_frame = self.preprocess_frame(processed_frame)
                    
                    # ArUco标记检测
                    if self.aruco_enabled:
                        aruco_data = self.detect_aruco(processed_frame)
                        processing_data['aruco'] = aruco_data
                        processed_frame = self.draw_aruco(processed_frame, aruco_data)
                    
                    # YOLO目标检测
                    if self.yolo_enabled and self.yolo_net is not None:
                        yolo_data = EnhancedCV.detect_objects_yolo(
                            processed_frame, self.yolo_net, self.yolo_classes)
                        processing_data['yolo'] = yolo_data
                        processed_frame = self.draw_yolo_detections(processed_frame, yolo_data)
                        if yolo_data:
                            self.detection_signal.emit({'yolo': yolo_data})
                    
                    # 光流计算
                    if self.optical_flow_enabled:
                        flow_data = self.calculate_optical_flow(processed_frame)
                        processing_data['optical_flow'] = flow_data
                        processed_frame = self.draw_optical_flow(processed_frame, flow_data)
                
                # 发送处理后的帧
                self.frame_signal.emit(processed_frame)
                self.processing_data_signal.emit(processing_data)
                
                time.sleep(0.03)  # 约30fps
                
        except Exception as e:
            logger.error(f"视频线程错误: {e}")
        finally:
            if self.cap:
                self.cap.release()
            logger.info("视频线程结束")
    
    def preprocess_frame(self, frame):
        """图像预处理"""
        try:
            # 调整大小
            frame = cv2.resize(frame, (640, 480))
            
            # 对比度增强
            lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            cl = clahe.apply(l)
            limg = cv2.merge((cl, a, b))
            frame = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)
            
            return frame
        except Exception as e:
            logger.error(f"图像预处理错误: {e}")
            return frame
    
    def detect_aruco(self, frame):
        """检测ArUco标记"""
        try:
            corners, ids, rejected = EnhancedCV.detect_aruco_markers(frame)
            
            markers = []
            if ids is not None:
                for i, corner in enumerate(corners):
                    marker_id = ids[i][0]
                    center = corner[0].mean(axis=0)
                    
                    rvecs, tvecs = EnhancedCV.estimate_pose_single_marker(
                        corner, 0.1, self.camera_matrix, self.dist_coeffs)
                    
                    markers.append({
                        'id': marker_id,
                        'corners': corner,
                        'center': center,
                        'rvec': rvecs[0] if rvecs is not None else None,
                        'tvec': tvecs[0] if tvecs is not None else None
                    })
            
            return {'markers': markers, 'rejected': rejected}
        except Exception as e:
            logger.error(f"ArUco检测错误: {e}")
            return {'markers': [], 'rejected': []}
    
    def draw_aruco(self, frame, aruco_data):
        """绘制ArUco标记"""
        try:
            for marker in aruco_data['markers']:
                cv2.polylines(frame, [np.int32(marker['corners'])], True, (0, 255, 0), 2)
                
                center = marker['center']
                cv2.putText(frame, str(marker['id']), 
                           (int(center[0]), int(center[1])), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                
                if marker['rvec'] is not None and marker['tvec'] is not None:
                    cv2.drawFrameAxes(frame, self.camera_matrix, self.dist_coeffs,
                                     marker['rvec'], marker['tvec'], 0.1)
            
            return frame
        except Exception as e:
            logger.error(f"绘制ArUco错误: {e}")
            return frame
    
    def draw_yolo_detections(self, frame, detections):
        """绘制YOLO检测结果"""
        try:
            for detection in detections:
                x, y, w, h = detection['bbox']
                label = f"{detection['class_name']}: {detection['confidence']:.2f}"
                
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                cv2.putText(frame, label, (x, y - 10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            
            return frame
        except Exception as e:
            logger.error(f"绘制YOLO检测结果错误: {e}")
            return frame
    
    def calculate_optical_flow(self, frame):
        """计算光流"""
        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            if self.prev_frame is None:
                self.prev_frame = gray
                self.prev_points = cv2.goodFeaturesToTrack(gray, 100, 0.3, 7)
                return {'points': None, 'flow': None}
            
            new_points, status, error = EnhancedCV.optical_flow_lk(
                self.prev_frame, gray, self.prev_points)
            
            if new_points is None:
                return {'points': None, 'flow': None}
            
            good_new = new_points[status == 1]
            good_old = self.prev_points[status == 1]
            
            self.prev_frame = gray.copy()
            self.prev_points = good_new.reshape(-1, 1, 2)
            
            return {
                'points': (good_old, good_new),
                'flow': (good_new - good_old) if len(good_new) > 0 else None
            }
        except Exception as e:
            logger.error(f"光流计算错误: {e}")
            return {'points': None, 'flow': None}
    
    def draw_optical_flow(self, frame, flow_data):
        """绘制光流"""
        try:
            if flow_data['points'] is None:
                return frame
            
            good_old, good_new = flow_data['points']
            
            for i, (new, old) in enumerate(zip(good_new, good_old)):
                a, b = new.ravel()
                c, d = old.ravel()
                cv2.line(frame, (int(a), int(b)), (int(c), int(d)), (0, 255, 0), 2)
                cv2.circle(frame, (int(a), int(b)), 3, (0, 0, 255), -1)
            
            return frame
        except Exception as e:
            logger.error(f"绘制光流错误: {e}")
            return frame
    
    def stop(self):
        """停止线程"""
        self.running = False
        self.wait(2000)  # 等待2秒

# ==================== 主界面 ====================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.drone = AdvancedDroneController(simulation=True)
        self.video_thread = None
        
        self.init_ui()
        self.setup_connections()
        
        # 启动控制循环
        self.drone.start_control_loop()
        self.drone.start_task_execution()
        
        # 启动状态更新定时器
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_status_display)
        self.status_timer.start(100)  # 10Hz更新
    
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("高级单目飞行器控制系统")
        self.setGeometry(100, 100, 1600, 900)
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QHBoxLayout(central_widget)
        
        # 左侧面板（视频和3D视图）
        left_panel = QVBoxLayout()
        
        # 视频显示
        self.video_label = QLabel()
        self.video_label.setMinimumSize(640, 480)
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setText("视频未启动")
        self.video_label.setStyleSheet("border: 1px solid gray;")
        
        # 3D视图
        self.view_3d = Advanced3DViewer(self.drone)
        
        # 视频控制
        video_control_layout = QHBoxLayout()
        self.start_video_btn = QPushButton("启动视频")
        self.stop_video_btn = QPushButton("停止视频")
        self.camera_combo = QComboBox()
        self.camera_combo.addItems(["0", "1", "2", "3"])
        
        video_control_layout.addWidget(QLabel("摄像头:"))
        video_control_layout.addWidget(self.camera_combo)
        video_control_layout.addWidget(self.start_video_btn)
        video_control_layout.addWidget(self.stop_video_btn)
        video_control_layout.addStretch()
        
        left_panel.addLayout(video_control_layout)
        left_panel.addWidget(self.video_label)
        left_panel.addWidget(self.view_3d)
        
        # 右侧面板（控制和状态）
        right_panel = QTabWidget()
        
        # 飞行控制标签页
        flight_tab = self.create_flight_control_tab()
        right_panel.addTab(flight_tab, "飞行控制")
        
        # 视觉处理标签页
        vision_tab = self.create_vision_control_tab()
        right_panel.addTab(vision_tab, "视觉处理")
        
        # 任务计划标签页
        task_tab = self.create_task_planning_tab()
        right_panel.addTab(task_tab, "任务计划")
        
        # 状态监控标签页
        status_tab = self.create_status_monitor_tab()
        right_panel.addTab(status_tab, "状态监控")
        
        # 添加到主布局
        main_layout.addLayout(left_panel, 2)
        main_layout.addWidget(right_panel, 1)
        
        # 状态栏
        self.statusBar().showMessage("系统就绪")
        
        # 菜单栏
        self.create_menu_bar()
    
    def create_flight_control_tab(self):
        """创建飞行控制标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 连接控制
        connection_group = QGroupBox("连接控制")
        connection_layout = QHBoxLayout()
        self.connect_btn = QPushButton("连接")
        self.disconnect_btn = QPushButton("断开")
        self.emergency_btn = QPushButton("紧急停止")
        self.emergency_btn.setStyleSheet("background-color: red; color: white;")
        
        connection_layout.addWidget(self.connect_btn)
        connection_layout.addWidget(self.disconnect_btn)
        connection_layout.addWidget(self.emergency_btn)
        connection_group.setLayout(connection_layout)
        
        # 基本飞行控制
        basic_group = QGroupBox("基本飞行控制")
        basic_layout = QGridLayout()
        
        self.takeoff_btn = QPushButton("起飞")
        self.land_btn = QPushButton("降落")
        self.hover_btn = QPushButton("悬停")
        self.return_home_btn = QPushButton("返航")
        
        basic_layout.addWidget(self.takeoff_btn, 0, 0)
        basic_layout.addWidget(self.land_btn, 0, 1)
        basic_layout.addWidget(self.hover_btn, 1, 0)
        basic_layout.addWidget(self.return_home_btn, 1, 1)
        basic_group.setLayout(basic_layout)
        
        # 位置控制
        position_group = QGroupBox("位置控制")
        position_layout = QFormLayout()
        
        self.x_spin = QDoubleSpinBox()
        self.y_spin = QDoubleSpinBox()
        self.z_spin = QDoubleSpinBox()
        self.yaw_spin = QDoubleSpinBox()
        self.goto_btn = QPushButton("前往位置")
        
        self.x_spin.setRange(-10, 10)
        self.y_spin.setRange(-10, 10)
        self.z_spin.setRange(0, 10)
        self.yaw_spin.setRange(-180, 180)
        
        position_layout.addRow("X:", self.x_spin)
        position_layout.addRow("Y:", self.y_spin)
        position_layout.addRow("Z:", self.z_spin)
        position_layout.addRow("Yaw:", self.yaw_spin)
        position_layout.addRow(self.goto_btn)
        position_group.setLayout(position_layout)
        
        # 添加到主布局
        layout.addWidget(connection_group)
        layout.addWidget(basic_group)
        layout.addWidget(position_group)
        layout.addStretch()
        
        return tab
    
    def create_vision_control_tab(self):
        """创建视觉处理标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 处理开关
        processing_group = QGroupBox("视觉处理")
        processing_layout = QGridLayout()
        
        self.aruco_check = QCheckBox("ArUco检测")
        self.optical_flow_check = QCheckBox("光流计算")
        self.feature_matching_check = QCheckBox("特征匹配")
        self.yolo_check = QCheckBox("YOLO检测")
        
        processing_layout.addWidget(self.aruco_check, 0, 0)
        processing_layout.addWidget(self.optical_flow_check, 0, 1)
        processing_layout.addWidget(self.feature_matching_check, 1, 0)
        processing_layout.addWidget(self.yolo_check, 1, 1)
        processing_group.setLayout(processing_layout)
        
        # 参数设置
        params_group = QGroupBox("参数设置")
        params_layout = QFormLayout()
        
        self.confidence_spin = QDoubleSpinBox()
        self.confidence_spin.setRange(0.1, 1.0)
        self.confidence_spin.setValue(0.5)
        
        params_layout.addRow("置信度阈值:", self.confidence_spin)
        params_group.setLayout(params_layout)
        
        layout.addWidget(processing_group)
        layout.addWidget(params_group)
        layout.addStretch()
        
        return tab
    
    def create_task_planning_tab(self):
        """创建任务计划标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 任务列表
        self.task_list = QListWidget()
        
        # 任务控制
        task_control_layout = QHBoxLayout()
        self.add_task_btn = QPushButton("添加任务")
        self.remove_task_btn = QPushButton("删除任务")
        self.clear_tasks_btn = QPushButton("清空任务")
        self.execute_tasks_btn = QPushButton("执行任务")
        
        task_control_layout.addWidget(self.add_task_btn)
        task_control_layout.addWidget(self.remove_task_btn)
        task_control_layout.addWidget(self.clear_tasks_btn)
        task_control_layout.addWidget(self.execute_tasks_btn)
        
        # 任务状态
        self.task_status = QLabel("就绪")
        
        layout.addWidget(QLabel("任务队列:"))
        layout.addWidget(self.task_list)
        layout.addLayout(task_control_layout)
        layout.addWidget(self.task_status)
        layout.addStretch()
        
        return tab
    
    def create_status_monitor_tab(self):
        """创建状态监控标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 状态显示
        status_group = QGroupBox("飞行器状态")
        status_layout = QFormLayout()
        
        self.state_label = QLabel("DISCONNECTED")
        self.battery_label = QLabel("100%")
        self.position_label = QLabel("(0.00, 0.00, 0.00)")
        self.orientation_label = QLabel("(0.00, 0.00, 0.00)")
        
        status_layout.addRow("状态:", self.state_label)
        status_layout.addRow("电池:", self.battery_label)
        status_layout.addRow("位置:", self.position_label)
        status_layout.addRow("姿态:", self.orientation_label)
        status_group.setLayout(status_layout)
        
        # 数据记录
        data_group = QGroupBox("数据记录")
        data_layout = QVBoxLayout()
        
        self.save_data_btn = QPushButton("保存飞行数据")
        self.clear_data_btn = QPushButton("清空数据")
        
        data_layout.addWidget(self.save_data_btn)
        data_layout.addWidget(self.clear_data_btn)
        data_group.setLayout(data_layout)
        
        layout.addWidget(status_group)
        layout.addWidget(data_group)
        layout.addStretch()
        
        return tab
    
    def create_menu_bar(self):
        """创建菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu('文件')
        
        load_config_action = QAction('加载配置', self)
        save_config_action = QAction('保存配置', self)
        exit_action = QAction('退出', self)
        
        file_menu.addAction(load_config_action)
        file_menu.addAction(save_config_action)
        file_menu.addSeparator()
        file_menu.addAction(exit_action)
        
        # 工具菜单
        tools_menu = menubar.addMenu('工具')
        
        calibrate_camera_action = QAction('相机标定', self)
        settings_action = QAction('设置', self)
        
        tools_menu.addAction(calibrate_camera_action)
        tools_menu.addAction(settings_action)
        
        # 连接动作
        exit_action.triggered.connect(self.close)
    
    def setup_connections(self):
        """设置信号连接"""
        # 连接控制
        self.connect_btn.clicked.connect(self.drone.connect)
        self.disconnect_btn.clicked.connect(self.drone.disconnect)
        self.emergency_btn.clicked.connect(self.drone.emergency_stop)
        
        # 飞行控制
        self.takeoff_btn.clicked.connect(lambda: self.drone.takeoff(2.0))
        self.land_btn.clicked.connect(self.drone.land)
        self.hover_btn.clicked.connect(lambda: self.drone.status.state == DroneState.HOVERING)
        self.return_home_btn.clicked.connect(self.drone.return_to_home)
        self.goto_btn.clicked.connect(self.goto_position)
        
        # 视频控制
        self.start_video_btn.clicked.connect(self.start_video)
        self.stop_video_btn.clicked.connect(self.stop_video)
        
        # 视觉处理
        self.aruco_check.toggled.connect(self.toggle_aruco)
        self.optical_flow_check.toggled.connect(self.toggle_optical_flow)
        self.yolo_check.toggled.connect(self.toggle_yolo)
        
        # 任务控制
        self.add_task_btn.clicked.connect(self.show_task_dialog)
        self.remove_task_btn.clicked.connect(self.remove_task)
        self.clear_tasks_btn.clicked.connect(self.clear_tasks)
        self.execute_tasks_btn.clicked.connect(self.execute_tasks)
        
        # 数据记录
        self.save_data_btn.clicked.connect(self.save_flight_data)
        self.clear_data_btn.clicked.connect(self.clear_flight_data)
    
    def goto_position(self):
        """前往指定位置"""
        x = self.x_spin.value()
        y = self.y_spin.value()
        z = self.z_spin.value()
        yaw = self.yaw_spin.value()
        
        self.drone.goto_position(x, y, z, yaw)
    
    def start_video(self):
        """启动视频"""
        if self.video_thread and self.video_thread.isRunning():
            return
        
        camera_source = int(self.camera_combo.currentText())
        self.video_thread = EnhancedVideoThread(camera_source)
        self.video_thread.frame_signal.connect(self.update_video_display)
        self.video_thread.start()
        
        self.statusBar().showMessage("视频已启动")
    
    def stop_video(self):
        """停止视频"""
        if self.video_thread:
            self.video_thread.stop()
            self.video_thread = None
            self.video_label.setText("视频已停止")
            self.statusBar().showMessage("视频已停止")
    
    def update_video_display(self, frame):
        """更新视频显示"""
        try:
            # 转换BGR到RGB
            rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_image.shape
            bytes_per_line = ch * w
            
            qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(qt_image)
            
            # 缩放显示
            scaled_pixmap = pixmap.scaled(self.video_label.width(), 
                                         self.video_label.height(),
                                         Qt.KeepAspectRatio)
            self.video_label.setPixmap(scaled_pixmap)
        except Exception as e:
            logger.error(f"更新视频显示错误: {e}")
    
    def toggle_aruco(self, enabled):
        """切换ArUco检测"""
        if self.video_thread:
            self.video_thread.aruco_enabled = enabled
    
    def toggle_optical_flow(self, enabled):
        """切换光流计算"""
        if self.video_thread:
            self.video_thread.optical_flow_enabled = enabled
    
    def toggle_yolo(self, enabled):
        """切换YOLO检测"""
        if self.video_thread:
            self.video_thread.yolo_enabled = enabled
    
    def show_task_dialog(self):
        """显示任务对话框"""
        dialog = TaskDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            task_type, params = dialog.get_task()
            self.add_task(task_type, params)
    
    def add_task(self, task_type, params):
        """添加任务"""
        display_text = f"{task_type}: {params}"
        self.task_list.addItem(display_text)
        self.drone.add_task(task_type, **params)
    
    def remove_task(self):
        """删除任务"""
        current_row = self.task_list.currentRow()
        if current_row >= 0:
            self.task_list.takeItem(current_row)
    
    def clear_tasks(self):
        """清空任务"""
        self.task_list.clear()
        self.drone.stop_task_execution()
    
    def execute_tasks(self):
        """执行任务"""
        self.task_status.setText("执行中...")
        # 任务执行由后台线程处理
    
    def save_flight_data(self):
        """保存飞行数据"""
        filename, _ = QFileDialog.getSaveFileName(
            self, "保存飞行数据", "", "JSON文件 (*.json)")
        if filename:
            self.drone.save_flight_data(filename)
    
    def clear_flight_data(self):
        """清空飞行数据"""
        self.drone.flight_data.clear()
        self.statusBar().showMessage("飞行数据已清空")
    
    def update_status_display(self):
        """更新状态显示"""
        status = self.drone.status
        
        self.state_label.setText(status.state.name)
        self.battery_label.setText(f"{status.battery:.1f}%")
        self.position_label.setText(f"({status.position[0]:.2f}, {status.position[1]:.2f}, {status.position[2]:.2f})")
        self.orientation_label.setText(f"({status.orientation[0]:.2f}, {status.orientation[1]:.2f}, {status.orientation[2]:.2f})")
    
    def closeEvent(self, event):
        """关闭事件"""
        self.stop_video()
        self.drone.disconnect()
        event.accept()

# ==================== 任务对话框 ====================
class TaskDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("添加任务")
        self.setModal(True)
        self.init_ui()
    
    def init_ui(self):
        layout = QFormLayout()
        
        self.task_type = QComboBox()
        self.task_type.addItems([
            "takeoff", "land", "goto", "hover", 
            "return_home", "emergency_stop"
        ])
        self.task_type.currentTextChanged.connect(self.update_params)
        
        # 参数控件
        self.altitude_spin = QDoubleSpinBox()
        self.altitude_spin.setRange(0.5, 10.0)
        self.altitude_spin.setValue(2.0)
        
        self.duration_spin = QDoubleSpinBox()
        self.duration_spin.setRange(1, 60)
        self.duration_spin.setValue(5)
        
        self.x_spin = QDoubleSpinBox()
        self.y_spin = QDoubleSpinBox()
        self.z_spin = QDoubleSpinBox()
        self.yaw_spin = QDoubleSpinBox()
        
        self.x_spin.setRange(-10, 10)
        self.y_spin.setRange(-10, 10)
        self.z_spin.setRange(0.5, 10)
        self.yaw_spin.setRange(-180, 180)
        
        # 按钮
        button_layout = QHBoxLayout()
        ok_btn = QPushButton("确定")
        cancel_btn = QPushButton("取消")
        
        ok_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(ok_btn)
        button_layout.addWidget(cancel_btn)
        
        layout.addRow("任务类型:", self.task_type)
        self.update_params(self.task_type.currentText())
        layout.addRow(button_layout)
        
        self.setLayout(layout)
    
    def update_params(self, task_type):
        """更新参数显示"""
        # 清除现有参数行（保留任务类型和按钮行）
        for i in range(self.layout().rowCount() - 2, 0, -1):
            self.layout().removeRow(i)
        
        if task_type == "takeoff":
            self.layout().insertRow(1, "高度 (m):", self.altitude_spin)
        elif task_type == "hover":
            self.layout().insertRow(1, "持续时间 (s):", self.duration_spin)
        elif task_type == "goto":
            self.layout().insertRow(1, "X:", self.x_spin)
            self.layout().insertRow(2, "Y:", self.y_spin)
            self.layout().insertRow(3, "Z:", self.z_spin)
            self.layout().insertRow(4, "Yaw:", self.yaw_spin)
    
    def get_task(self):
        """获取任务信息"""
        task_type = self.task_type.currentText()
        params = {}
        
        if task_type == "takeoff":
            params['altitude'] = self.altitude_spin.value()
        elif task_type == "hover":
            params['duration'] = self.duration_spin.value()
        elif task_type == "goto":
            params['x'] = self.x_spin.value()
            params['y'] = self.y_spin.value()
            params['z'] = self.z_spin.value()
            params['yaw'] = self.yaw_spin.value()
        
        return task_type, params

# ==================== 主程序 ====================
def main():
    # 创建应用
    app = QApplication(sys.argv)
    app.setApplicationName("高级单目飞行器控制系统")
    app.setApplicationVersion("1.0")
    
    # 设置样式
    app.setStyle('Fusion')
    
    # 创建主窗口
    window = MainWindow()
    window.show()
    
    # 运行应用
    try:
        sys.exit(app.exec_())
    except Exception as e:
        logger.error(f"应用运行错误: {e}")

if __name__ == '__main__':
    main()