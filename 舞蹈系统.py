import sys
import os
import cv2
import numpy as np
import json
import pickle
from datetime import datetime
from collections import deque
from scipy import signal
from scipy.spatial import distance
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d import Axes3D
import mediapipe as mp
import pandas as pd
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QSlider, 
                             QFileDialog, QGroupBox, QComboBox, QSpinBox,
                             QDoubleSpinBox, QCheckBox, QProgressBar, QSplitter,
                             QListWidget, QTabWidget, QMessageBox, QDockWidget,
                             QTreeWidget, QTreeWidgetItem, QHeaderView, QTableWidget,
                             QTableWidgetItem, QToolBar, QAction, QStatusBar,
                             QDialog, QLineEdit, QDialogButtonBox, QFormLayout,
                             QGridLayout, QSizePolicy, QTextEdit, QRadioButton,
                             QButtonGroup, QFrame, QScrollArea)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread, QSize, QPoint, QRect, QPointF
from PyQt5.QtGui import (QImage, QPixmap, QIcon, QPainter, QColor, QPen, QFont,
                         QBrush, QPalette, QMovie)


class VideoProcessor(QThread):
    """增强的视频处理线程，支持多视角和实时处理"""
    frame_processed = pyqtSignal(int, np.ndarray, list, dict)  # 视角ID, 帧, 关键点, 附加数据
    progress_updated = pyqtSignal(int, int)  # 视角ID, 进度
    processing_finished = pyqtSignal(int)  # 视角ID
    error_occurred = pyqtSignal(int, str)  # 视角ID, 错误信息
    
    def __init__(self, video_path, view_id=0, config=None):
        super().__init__()
        self.view_id = view_id
        self.video_path = video_path
        self.is_running = False
        self.is_paused = False
        self.current_frame = 0
        self.total_frames = 0
        self.pose_landmarks = []
        
        # 配置参数
        self.config = config or {}
        self.min_detection_confidence = self.config.get('min_detection_confidence', 0.5)
        self.min_tracking_confidence = self.config.get('min_tracking_confidence', 0.5)
        self.model_complexity = self.config.get('model_complexity', 1)
        self.enable_segmentation = self.config.get('enable_segmentation', False)
        self.smooth_landmarks = self.config.get('smooth_landmarks', True)
        
        # 初始化MediaPipe姿势检测
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            static_image_mode=False,
            model_complexity=self.model_complexity,
            smooth_landmarks=self.smooth_landmarks,
            min_detection_confidence=self.min_detection_confidence,
            min_tracking_confidence=self.min_tracking_confidence,
            enable_segmentation=self.enable_segmentation
        )
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles
        
        # 初始化MediaPipe holistic模型（用于手部和面部检测）
        self.mp_holistic = mp.solutions.holistic
        self.holistic = self.mp_holistic.Holistic(
            static_image_mode=False,
            model_complexity=self.model_complexity,
            smooth_landmarks=self.smooth_landmarks,
            min_detection_confidence=self.min_detection_confidence,
            min_tracking_confidence=self.min_tracking_confidence
        )
        
    def run(self):
        """处理视频的主循环"""
        try:
            cap = cv2.VideoCapture(self.video_path)
            if not cap.isOpened():
                self.error_occurred.emit(self.view_id, f"无法打开视频: {self.video_path}")
                return
                
            self.total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            self.is_running = True
            
            # 创建背景减法器（用于分割）
            if self.enable_segmentation:
                fgbg = cv2.createBackgroundSubtractorMOG2(history=500, varThreshold=50, detectShadows=False)
            
            while self.is_running and self.current_frame < self.total_frames:
                if not self.is_paused:
                    ret, frame = cap.read()
                    if not ret:
                        break
                        
                    # 处理帧
                    processed_frame, landmarks, additional_data = self.process_frame(frame, fgbg if self.enable_segmentation else None)
                    
                    # 发送处理后的帧和关键点
                    self.frame_processed.emit(self.view_id, processed_frame, landmarks, additional_data)
                    self.pose_landmarks.append(landmarks)
                    
                    # 更新进度
                    self.current_frame += 1
                    progress = int((self.current_frame / self.total_frames) * 100)
                    self.progress_updated.emit(self.view_id, progress)
                    
                    # 控制处理速度（根据原始视频的FPS）
                    if fps > 0:
                        self.msleep(int(1000 / fps))
        
            cap.release()
            self.processing_finished.emit(self.view_id)
            
        except Exception as e:
            self.error_occurred.emit(self.view_id, f"处理错误: {str(e)}")
    
    def process_frame(self, frame, fgbg=None):
        """处理单帧图像，检测姿势关键点和附加信息"""
        # 转换颜色空间 BGR到RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # 处理帧并获取姿势关键点
        results = self.pose.process(rgb_frame)
        holistic_results = self.holistic.process(rgb_frame)
        
        # 绘制姿势关键点
        annotated_frame = frame.copy()
        additional_data = {
            'holistic': {},
            'segmentation': None,
            'motion_vectors': None
        }
        
        # 绘制姿势关键点
        if results.pose_landmarks:
            self.mp_drawing.draw_landmarks(
                annotated_frame,
                results.pose_landmarks,
                self.mp_pose.POSE_CONNECTIONS,
                landmark_drawing_spec=self.mp_drawing_styles.get_default_pose_landmarks_style()
            )
            
            # 提取关键点坐标
            landmarks = []
            for idx, landmark in enumerate(results.pose_landmarks.landmark):
                landmarks.append({
                    'x': landmark.x,
                    'y': landmark.y,
                    'z': landmark.z,
                    'visibility': landmark.visibility
                })
        else:
            landmarks = []
        
        # 处理holistic结果（手部和面部）
        if holistic_results:
            # 绘制左手关键点
            if holistic_results.left_hand_landmarks:
                self.mp_drawing.draw_landmarks(
                    annotated_frame,
                    holistic_results.left_hand_landmarks,
                    self.mp_holistic.HAND_CONNECTIONS,
                    landmark_drawing_spec=self.mp_drawing_styles.get_default_hand_landmarks_style(),
                    connection_drawing_spec=self.mp_drawing_styles.get_default_hand_connections_style()
                )
                
                # 存储左手关键点
                left_hand_landmarks = []
                for idx, landmark in enumerate(holistic_results.left_hand_landmarks.landmark):
                    left_hand_landmarks.append({
                        'x': landmark.x,
                        'y': landmark.y,
                        'z': landmark.z
                    })
                additional_data['holistic']['left_hand'] = left_hand_landmarks
            
            # 绘制右手关键点
            if holistic_results.right_hand_landmarks:
                self.mp_drawing.draw_landmarks(
                    annotated_frame,
                    holistic_results.right_hand_landmarks,
                    self.mp_holistic.HAND_CONNECTIONS,
                    landmark_drawing_spec=self.mp_drawing_styles.get_default_hand_landmarks_style(),
                    connection_drawing_spec=self.mp_drawing_styles.get_default_hand_connections_style()
                )
                
                # 存储右手关键点
                right_hand_landmarks = []
                for idx, landmark in enumerate(holistic_results.right_hand_landmarks.landmark):
                    right_hand_landmarks.append({
                        'x': landmark.x,
                        'y': landmark.y,
                        'z': landmark.z
                    })
                additional_data['holistic']['right_hand'] = right_hand_landmarks
            
            # 绘制面部关键点
            if holistic_results.face_landmarks:
                self.mp_drawing.draw_landmarks(
                    annotated_frame,
                    holistic_results.face_landmarks,
                    self.mp_holistic.FACEMESH_CONTOURS,
                    landmark_drawing_spec=None,
                    connection_drawing_spec=self.mp_drawing_styles.get_default_face_mesh_contours_style()
                )
        
        # 应用背景分割
        if fgbg is not None:
            # 调整大小以提高性能
            small_frame = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)
            fgmask = fgbg.apply(small_frame)
            
            # 形态学操作去除噪声
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
            fgmask = cv2.morphologyEx(fgmask, cv2.MORPH_OPEN, kernel)
            fgmask = cv2.morphologyEx(fgmask, cv2.MORPH_CLOSE, kernel)
            
            # 调整回原始大小
            fgmask = cv2.resize(fgmask, (frame.shape[1], frame.shape[0]))
            
            # 将分割结果添加到附加数据
            additional_data['segmentation'] = fgmask
            
            # 在帧上绘制分割结果（半透明）
            colored_mask = cv2.applyColorMap(fgmask, cv2.COLORMAP_JET)
            annotated_frame = cv2.addWeighted(annotated_frame, 0.7, colored_mask, 0.3, 0)
        
        return annotated_frame, landmarks, additional_data
    
    def stop(self):
        """停止处理"""
        self.is_running = False
        self.wait()
    
    def pause(self):
        """暂停处理"""
        self.is_paused = True
    
    def resume(self):
        """恢复处理"""
        self.is_paused = False


class MultiViewSyncManager:
    """多视角同步管理器"""
    def __init__(self):
        self.view_processors = {}  # 视角ID -> 处理器
        self.view_data = {}  # 视角ID -> 数据
        self.sync_offset = 0  # 同步偏移（帧数）
        self.reference_view = 0  # 参考视角
        
    def add_view(self, view_id, processor):
        """添加视角处理器"""
        self.view_processors[view_id] = processor
        self.view_data[view_id] = {
            'frames': [],
            'landmarks': [],
            'timestamps': []
        }
    
    def remove_view(self, view_id):
        """移除视角处理器"""
        if view_id in self.view_processors:
            del self.view_processors[view_id]
        if view_id in self.view_data:
            del self.view_data[view_id]
    
    def update_view_data(self, view_id, frame, landmarks, additional_data):
        """更新视角数据"""
        if view_id not in self.view_data:
            self.view_data[view_id] = {
                'frames': [],
                'landmarks': [],
                'timestamps': []
            }
        
        timestamp = datetime.now().timestamp()
        self.view_data[view_id]['frames'].append(frame)
        self.view_data[view_id]['landmarks'].append(landmarks)
        self.view_data[view_id]['timestamps'].append(timestamp)
        self.view_data[view_id]['additional_data'] = additional_data
    
    def synchronize_views(self):
        """同步多视角数据"""
        # 简单实现：基于时间戳对齐
        # 更复杂的实现可以使用特征点匹配或运动分析
        
        if len(self.view_data) < 2:
            return self.view_data
        
        # 找到所有视角共有的时间范围
        min_time = max([data['timestamps'][0] for data in self.view_data.values()])
        max_time = min([data['timestamps'][-1] for data in self.view_data.values()])
        
        # 为每个视角创建插值函数
        synced_data = {}
        for view_id, data in self.view_data.items():
            # 创建时间轴
            times = np.array(data['timestamps'])
            frames = np.arange(len(times))
            
            # 创建同步后的时间轴
            synced_times = np.linspace(min_time, max_time, len(times))
            
            # 对每一帧数据进行插值
            synced_frames = []
            synced_landmarks = []
            
            for t in synced_times:
                # 找到最近的时间点
                idx = np.argmin(np.abs(times - t))
                synced_frames.append(data['frames'][idx])
                synced_landmarks.append(data['landmarks'][idx])
            
            synced_data[view_id] = {
                'frames': synced_frames,
                'landmarks': synced_landmarks,
                'timestamps': synced_times
            }
        
        return synced_data
    
    def calculate_3d_positions(self, synced_data):
        """基于多视角计算3D位置"""
        # 简单实现：使用两个视角的对应点计算3D位置
        # 更复杂的实现可以使用多个视角和三角测量
        
        if len(synced_data) < 2:
            return None
        
        # 获取视角ID
        view_ids = list(synced_data.keys())
        view1, view2 = view_ids[0], view_ids[1]
        
        # 假设我们已经有了相机参数（在实际应用中需要校准）
        # 这里使用简化的假设
        
        num_frames = min(len(synced_data[view1]['landmarks']), 
                         len(synced_data[view2]['landmarks']))
        
        all_3d_points = []
        
        for i in range(num_frames):
            landmarks1 = synced_data[view1]['landmarks'][i]
            landmarks2 = synced_data[view2]['landmarks'][i]
            
            if not landmarks1 or not landmarks2:
                all_3d_points.append([])
                continue
            
            # 确保两个视角有相同数量的关键点
            min_landmarks = min(len(landmarks1), len(landmarks2))
            frame_3d_points = []
            
            for j in range(min_landmarks):
                # 简化的三角测量（实际应用需要相机矩阵）
                x1, y1 = landmarks1[j]['x'], landmarks1[j]['y']
                x2, y2 = landmarks2[j]['x'], landmarks2[j]['y']
                
                # 假设基线距离和焦距（这些值应该来自相机校准）
                baseline = 0.5  # 假设两个相机之间的距离（米）
                focal_length = 1.0  # 假设焦距
                
                # 计算视差
                disparity = x1 - x2
                
                # 避免除零
                if abs(disparity) < 0.001:
                    disparity = 0.001
                
                # 计算深度
                depth = (baseline * focal_length) / disparity
                
                # 计算3D坐标（简化）
                x_3d = (x1 + x2) / 2 * depth
                y_3d = (y1 + y2) / 2 * depth
                z_3d = depth
                
                frame_3d_points.append({
                    'x': x_3d,
                    'y': y_3d,
                    'z': z_3d,
                    'visibility': min(landmarks1[j]['visibility'], landmarks2[j]['visibility'])
                })
            
            all_3d_points.append(frame_3d_points)
        
        return all_3d_points


class Pose3DVisualizer(FigureCanvas):
    """增强的3D姿势可视化组件"""
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        super().__init__(self.fig)
        self.setParent(parent)
        
        self.ax = self.fig.add_subplot(111, projection='3d')
        self.ax.set_xlabel('X')
        self.ax.set_ylabel('Y')
        self.ax.set_zlabel('Z')
        
        # 设置坐标轴范围
        self.ax.set_xlim3d([-1, 1])
        self.ax.set_ylim3d([-1, 1])
        self.ax.set_zlim3d([-1, 1])
        
        # 初始化空的散点图和连线图
        self.scatter = self.ax.scatter([], [], [], c='b', marker='o', s=50)
        self.lines = []
        self.annotation = None
        
        # 设置视角
        self.ax.view_init(elev=20, azim=135)
        
        self.fig.tight_layout()
    
    def update_pose(self, landmarks, highlight_joints=None, title=None):
        """更新3D姿势显示"""
        # 清除之前的连线和注释
        for line in self.lines:
            line.remove()
        self.lines = []
        
        if self.annotation:
            self.annotation.remove()
            self.annotation = None
        
        if not landmarks:
            self.draw()
            return
        
        # 提取坐标
        x = [lm['x'] for lm in landmarks]
        y = [lm['y'] for lm in landmarks]
        z = [lm['z'] for lm in landmarks]
        visibility = [lm.get('visibility', 1.0) for lm in landmarks]
        
        # 更新散点图
        colors = ['r' if highlight_joints and i in highlight_joints else 
                 ('b' if v > 0.5 else 'gray') 
                 for i, v in enumerate(visibility)]
        sizes = [100 if highlight_joints and i in highlight_joints else 
                (50 if v > 0.5 else 20) 
                for i, v in enumerate(visibility)]
        
        self.scatter._offsets3d = (x, y, z)
        self.scatter.set_color(colors)
        self.scatter.set_sizes(sizes)
        
        # 定义姿势连接关系 (MediaPipe姿势连接)
        connections = [
            # 身体主干
            (11, 12), (12, 24), (24, 23), (23, 11),
            # 左臂
            (11, 13), (13, 15), (15, 17), (15, 19), (15, 21),
            # 右臂
            (12, 14), (14, 16), (16, 18), (16, 20), (16, 22),
            # 左腿
            (23, 25), (25, 27), (27, 29), (27, 31),
            # 右腿
            (24, 26), (26, 28), (28, 30), (28, 32),
            # 面部 (简化)
            (0, 1), (1, 2), (2, 3), (3, 7),
            (0, 4), (4, 5), (5, 6), (6, 8)
        ]
        
        # 绘制连接线
        for connection in connections:
            start_idx, end_idx = connection
            if (start_idx < len(landmarks) and end_idx < len(landmarks) and
                visibility[start_idx] > 0.2 and visibility[end_idx] > 0.2):
                start = landmarks[start_idx]
                end = landmarks[end_idx]
                line = self.ax.plot(
                    [start['x'], end['x']],
                    [start['y'], end['y']],
                    [start['z'], end['z']],
                    'r-' if (highlight_joints and 
                            (start_idx in highlight_joints or end_idx in highlight_joints)) else 'b-',
                    linewidth=2 if (highlight_joints and 
                                  (start_idx in highlight_joints or end_idx in highlight_joints)) else 1
                )
                self.lines.extend(line)
        
        # 添加标题
        if title:
            self.ax.set_title(title)
        
        # 自动调整坐标轴范围
        if x and y and z:
            max_range = max(max(x) - min(x), max(y) - min(y), max(z) - min(z)) or 1
            mid_x = (max(x) + min(x)) * 0.5
            mid_y = (max(y) + min(y)) * 0.5
            mid_z = (max(z) + min(z)) * 0.5
            
            self.ax.set_xlim(mid_x - max_range * 0.6, mid_x + max_range * 0.6)
            self.ax.set_ylim(mid_y - max_range * 0.6, mid_y + max_range * 0.6)
            self.ax.set_zlim(mid_z - max_range * 0.6, mid_z + max_range * 0.6)
        
        self.draw()


class TimelineWidget(QWidget):
    """时间轴控件，用于显示和导航视频帧"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(60)
        self.setMaximumHeight(80)
        
        self.total_frames = 100
        self.current_frame = 0
        self.keyframes = []
        self.highlight_frames = []
        
        # 颜色设置
        self.background_color = QColor(50, 50, 50)
        self.progress_color = QColor(0, 150, 255)
        self.keyframe_color = QColor(255, 200, 0)
        self.highlight_color = QColor(0, 255, 100)
        self.text_color = QColor(255, 255, 255)
        
    def set_total_frames(self, frames):
        """设置总帧数"""
        self.total_frames = max(1, frames)
        self.update()
        
    def set_current_frame(self, frame):
        """设置当前帧"""
        self.current_frame = max(0, min(frame, self.total_frames - 1))
        self.update()
        
    def set_keyframes(self, keyframes):
        """设置关键帧"""
        self.keyframes = keyframes
        self.update()
        
    def set_highlight_frames(self, frames):
        """设置高亮帧"""
        self.highlight_frames = frames
        self.update()
        
    def paintEvent(self, event):
        """绘制时间轴"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 绘制背景
        painter.fillRect(self.rect(), self.background_color)
        
        # 计算可用宽度
        margin = 10
        available_width = self.width() - 2 * margin
        frame_width = available_width / max(1, self.total_frames)
        
        # 绘制高亮帧
        if self.highlight_frames:
            for frame in self.highlight_frames:
                if 0 <= frame < self.total_frames:
                    x = margin + frame * frame_width
                    highlight_rect = QRect(x - 2, 10, 4, self.height() - 20)
                    painter.fillRect(highlight_rect, self.highlight_color)
        
        # 绘制关键帧
        for frame in self.keyframes:
            if 0 <= frame < self.total_frames:
                x = margin + frame * frame_width
                painter.setPen(QPen(self.keyframe_color, 3))
                painter.drawLine(x, 15, x, self.height() - 15)
                
                # 绘制关键帧标记
                painter.setBrush(self.keyframe_color)
                painter.drawEllipse(QPoint(x, 10), 4, 4)
                painter.drawEllipse(QPoint(x, self.height() - 10), 4, 4)
        
        # 绘制进度条
        progress_width = margin + self.current_frame * frame_width
        progress_rect = QRect(int(margin), int(self.height() - 10), int(progress_width - margin), 5)
        painter.fillRect(progress_rect, self.progress_color)
        
        # 绘制当前帧指示器
        current_x = margin + self.current_frame * frame_width
        painter.setPen(QPen(QColor(255, 255, 255), 2))
        painter.drawLine(QPointF(current_x, 5), QPointF(current_x, self.height() - 5))
        
        # 绘制帧编号
        painter.setPen(self.text_color)
        painter.drawText(5, 15, f"{self.current_frame}/{self.total_frames}")
        
        # 绘制时间轴刻度
        for i in range(0, self.total_frames, max(1, self.total_frames // 10)):
            x = margin + i * frame_width
            painter.drawLine(QPointF(x, self.height() - 15), QPointF(x, self.height() - 5))
            painter.drawText(int(x - 10), int(self.height() - 20), 40, 15, Qt.AlignLeft, str(i))
    
    def mousePressEvent(self, event):
        """鼠标点击事件，用于跳转到特定帧"""
        if event.button() == Qt.LeftButton:
            margin = 10
            available_width = self.width() - 2 * margin
            frame_width = available_width / max(1, self.total_frames)
            
            x = event.pos().x()
            frame = int((x - margin) / frame_width)
            frame = max(0, min(frame, self.total_frames - 1))
            
            self.set_current_frame(frame)
            self.currentFrameChanged.emit(frame)
    
    # 自定义信号
    currentFrameChanged = pyqtSignal(int)


class EnhancedDanceAnalyzer:
    """增强的舞蹈分析工具类"""
    def __init__(self):
        self.pose_data = []
        self.reference_data = None
        self.motion_features = []
        
    def set_reference_data(self, reference_data):
        """设置参考数据（用于对比分析）"""
        self.reference_data = reference_data
        
    def extract_motion_features(self, pose_sequence):
        """提取运动特征"""
        features = []
        
        for i in range(1, len(pose_sequence)):
            if not pose_sequence[i] or not pose_sequence[i-1]:
                features.append({})
                continue
                
            # 计算速度（基于髋部中心）
            if len(pose_sequence[i]) > 23 and len(pose_sequence[i-1]) > 23:
                hip_center_current = self._get_hip_center(pose_sequence[i])
                hip_center_previous = self._get_hip_center(pose_sequence[i-1])
                
                velocity = self._point_distance(hip_center_current, hip_center_previous)
            else:
                velocity = 0
                
            # 计算能量（基于所有关节点速度的平方和）
            energy = 0
            valid_joints = 0
            
            for j in range(min(len(pose_sequence[i]), len(pose_sequence[i-1]))):
                if pose_sequence[i][j] and pose_sequence[i-1][j]:
                    joint_velocity = self._point_distance(pose_sequence[i][j], pose_sequence[i-1][j])
                    energy += joint_velocity ** 2
                    valid_joints += 1
                    
            energy = energy / max(1, valid_joints)
            
            # 计算流畅度（基于加速度变化）
            fluency = 0
            if i > 1 and len(pose_sequence[i]) > 23 and len(pose_sequence[i-1]) > 23 and len(pose_sequence[i-2]) > 23:
                hip_center_prev2 = self._get_hip_center(pose_sequence[i-2])
                velocity_prev = self._point_distance(hip_center_previous, hip_center_prev2)
                acceleration = abs(velocity - velocity_prev)
                fluency = 1.0 / (1.0 + acceleration)
                
            # 计算对称性
            symmetry = self._calculate_symmetry(pose_sequence[i])
            
            features.append({
                'velocity': velocity,
                'energy': energy,
                'fluency': fluency,
                'symmetry': symmetry,
                'frame': i
            })
            
        return features
    
    def _get_hip_center(self, landmarks):
        """计算髋部中心点"""
        if len(landmarks) > 24:
            left_hip = landmarks[23]
            right_hip = landmarks[24]
            return {
                'x': (left_hip['x'] + right_hip['x']) / 2,
                'y': (left_hip['y'] + right_hip['y']) / 2,
                'z': (left_hip['z'] + right_hip['z']) / 2
            }
        return {'x': 0, 'y': 0, 'z': 0}
    
    def _calculate_symmetry(self, landmarks):
        """计算身体对称性"""
        if len(landmarks) < 25:
            return 0
            
        # 左右肩对称性
        left_shoulder = landmarks[11]
        right_shoulder = landmarks[12]
        shoulder_symmetry = 1.0 - abs(left_shoulder['y'] - right_shoulder['y'])
        
        # 左右髋对称性
        left_hip = landmarks[23]
        right_hip = landmarks[24]
        hip_symmetry = 1.0 - abs(left_hip['y'] - right_hip['y'])
        
        # 左右肘对称性
        left_elbow = landmarks[13]
        right_elbow = landmarks[14]
        elbow_symmetry = 1.0 - abs(left_elbow['y'] - right_elbow['y'])
        
        # 左右膝对称性
        left_knee = landmarks[25]
        right_knee = landmarks[26]
        knee_symmetry = 1.0 - abs(left_knee['y'] - right_knee['y'])
        
        return (shoulder_symmetry + hip_symmetry + elbow_symmetry + knee_symmetry) / 4.0
    
    def analyze_rhythm(self, motion_features, music_beats=None):
        """分析舞蹈节奏"""
        if not motion_features:
            return {}
            
        # 提取能量序列
        energy_series = [f['energy'] for f in motion_features if 'energy' in f]
        
        if len(energy_series) < 10:
            return {}
            
        # 找到能量峰值（节奏点）
        peaks, _ = signal.find_peaks(energy_series, prominence=0.1, distance=5)
        
        # 计算节奏一致性
        if len(peaks) > 1:
            peak_intervals = np.diff(peaks)
            rhythm_consistency = 1.0 / (1.0 + np.std(peak_intervals))
        else:
            rhythm_consistency = 0
            
        # 如果提供了音乐节拍，计算舞蹈与音乐的同步性
        music_sync = 0
        if music_beats and len(music_beats) > 0:
            # 简单实现：计算舞蹈峰值与音乐节拍的平均时间差
            # 更复杂的实现可以使用动态时间规整(DTW)
            dance_beats = peaks
            total_diff = 0
            matched_beats = 0
            
            for dance_beat in dance_beats:
                # 找到最接近的音乐节拍
                closest_music_beat = min(music_beats, key=lambda x: abs(x - dance_beat))
                if abs(closest_music_beat - dance_beat) < 10:  # 允许10帧的误差
                    total_diff += abs(closest_music_beat - dance_beat)
                    matched_beats += 1
                    
            if matched_beats > 0:
                avg_diff = total_diff / matched_beats
                music_sync = 1.0 / (1.0 + avg_diff / 5.0)  # 归一化
                
        return {
            'beat_count': len(peaks),
            'rhythm_consistency': rhythm_consistency,
            'music_sync': music_sync,
            'energy_peaks': peaks
        }
    
    def compare_with_reference(self, performance_data, reference_data):
        """与参考数据对比"""
        if not reference_data:
            return {}
            
        # 确保数据长度一致
        min_len = min(len(performance_data), len(reference_data))
        performance_data = performance_data[:min_len]
        reference_data = reference_data[:min_len]
        
        # 计算姿态相似度
        pose_similarities = []
        for i in range(min_len):
            if performance_data[i] and reference_data[i]:
                similarity = self._calculate_pose_similarity(performance_data[i], reference_data[i])
                pose_similarities.append(similarity)
                
        avg_pose_similarity = np.mean(pose_similarities) if pose_similarities else 0
        
        # 计算运动轨迹相似度
        performance_trajectory = [self._get_hip_center(pose) for pose in performance_data if pose]
        reference_trajectory = [self._get_hip_center(pose) for pose in reference_data if pose]
        
        # 确保轨迹长度一致
        min_traj_len = min(len(performance_trajectory), len(reference_trajectory))
        performance_trajectory = performance_trajectory[:min_traj_len]
        reference_trajectory = reference_trajectory[:min_traj_len]
        
        # 计算轨迹距离（使用DTW会更好，这里使用简单欧氏距离）
        trajectory_errors = []
        for i in range(min_traj_len):
            error = self._point_distance(performance_trajectory[i], reference_trajectory[i])
            trajectory_errors.append(error)
            
        avg_trajectory_error = np.mean(trajectory_errors) if trajectory_errors else 0
        trajectory_similarity = 1.0 / (1.0 + avg_trajectory_error)
        
        # 计算节奏相似度
        performance_features = self.extract_motion_features(performance_data)
        reference_features = self.extract_motion_features(reference_data)
        
        performance_rhythm = self.analyze_rhythm(performance_features)
        reference_rhythm = self.analyze_rhythm(reference_features)
        
        rhythm_similarity = 0
        if performance_rhythm and reference_rhythm:
            beat_count_diff = abs(performance_rhythm.get('beat_count', 0) - reference_rhythm.get('beat_count', 0))
            rhythm_consistency_diff = abs(performance_rhythm.get('rhythm_consistency', 0) - reference_rhythm.get('rhythm_consistency', 0))
            
            rhythm_similarity = 1.0 / (1.0 + beat_count_diff / 10.0 + rhythm_consistency_diff)
            
        overall_similarity = (avg_pose_similarity + trajectory_similarity + rhythm_similarity) / 3.0
        
        return {
            'pose_similarity': avg_pose_similarity,
            'trajectory_similarity': trajectory_similarity,
            'rhythm_similarity': rhythm_similarity,
            'overall_similarity': overall_similarity,
            'frame_errors': trajectory_errors
        }
    
    def _calculate_pose_similarity(self, pose1, pose2):
        """计算两个姿势之间的相似度"""
        if not pose1 or not pose2:
            return 0
            
        min_joints = min(len(pose1), len(pose2))
        similarities = []
        
        for i in range(min_joints):
            # 只考虑可见性高的关节点
            if pose1[i].get('visibility', 1.0) > 0.5 and pose2[i].get('visibility', 1.0) > 0.5:
                distance = self._point_distance(pose1[i], pose2[i])
                similarity = 1.0 / (1.0 + distance)
                similarities.append(similarity)
                
        return np.mean(similarities) if similarities else 0
    
    def _point_distance(self, p1, p2):
        """计算两点之间的距离"""
        return np.sqrt((p1['x'] - p2['x'])**2 + (p1['y'] - p2['y'])**2 + (p1['z'] - p2['z'])**2)
    
    def cluster_movements(self, pose_sequence, n_clusters=5):
        """使用聚类分析将动作分组"""
        if not pose_sequence:
            return []
            
        # 提取特征向量（每个姿势的关节点坐标）
        feature_vectors = []
        valid_indices = []
        
        for i, pose in enumerate(pose_sequence):
            if pose and len(pose) >= 25:  # 确保有足够的关键点
                # 使用髋部相对坐标（减少全局位置的影响）
                hip_center = self._get_hip_center(pose)
                
                features = []
                for j, point in enumerate(pose):
                    if j < 25:  # 只使用前25个关键点（身体主要关节点）
                        # 相对坐标
                        rel_x = point['x'] - hip_center['x']
                        rel_y = point['y'] - hip_center['y']
                        rel_z = point['z'] - hip_center['z']
                        
                        features.extend([rel_x, rel_y, rel_z])
                
                feature_vectors.append(features)
                valid_indices.append(i)
        
        if len(feature_vectors) < n_clusters:
            return []
            
        # 标准化特征
        scaler = StandardScaler()
        scaled_features = scaler.fit_transform(feature_vectors)
        
        # 使用PCA降维（可选）
        pca = PCA(n_components=0.95) #保留95%的方差
        reduced_features = pca.fit_transform(scaled_features)
        
        # K-means聚类
        kmeans = KMeans(n_clusters=min(n_clusters, len(reduced_features)), random_state=42)
        clusters = kmeans.fit_predict(reduced_features)
        
        # 将聚类结果映射回原始帧索引
        result = [None] * len(pose_sequence)
        for idx, cluster_id in zip(valid_indices, clusters):
            result[idx] = cluster_id
            
        return result
    
    def generate_comprehensive_report(self, pose_sequence, motion_features, rhythm_analysis, comparison_result=None):
        """生成综合舞蹈分析报告"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "total_frames": len(pose_sequence),
            "valid_frames": sum(1 for p in pose_sequence if p),
            "motion_analysis": {},
            "rhythm_analysis": rhythm_analysis,
            "comparison_result": comparison_result,
            "performance_score": 0
        }
        
        # 运动分析
        if motion_features:
            velocities = [f.get('velocity', 0) for f in motion_features]
            energies = [f.get('energy', 0) for f in motion_features]
            fluencies = [f.get('fluency', 0) for f in motion_features]
            symmetries = [f.get('symmetry', 0) for f in motion_features]
            
            report["motion_analysis"] = {
                "avg_velocity": np.mean(velocities) if velocities else 0,
                "max_velocity": np.max(velocities) if velocities else 0,
                "avg_energy": np.mean(energies) if energies else 0,
                "max_energy": np.max(energies) if energies else 0,
                "avg_fluency": np.mean(fluencies) if fluencies else 0,
                "avg_symmetry": np.mean(symmetries) if symmetries else 0,
                "movement_variability": np.std(energies) if energies else 0
            }
        
        # 计算综合表现分数
        motion_quality = report["motion_analysis"]
        rhythm_quality = report["rhythm_analysis"]
        
        performance_score = (
            motion_quality.get("avg_energy", 0) * 0.2 +
            motion_quality.get("avg_fluency", 0) * 0.2 +
            motion_quality.get("avg_symmetry", 0) * 0.2 +
            rhythm_quality.get("rhythm_consistency", 0) * 0.2 +
            rhythm_quality.get("music_sync", 0) * 0.2
        ) * 100
        
        # 如果有对比结果，调整分数
        if comparison_result:
            performance_score *= comparison_result.get("overall_similarity", 1.0)
            
        report["performance_score"] = performance_score
        
        return report


class DanceMotionDatabase:
    """舞蹈动作数据库，用于存储和检索标准动作"""
    def __init__(self, db_path="dance_motions.db"):
        self.db_path = db_path
        self.motions = {}
        self.load_database()
        
    def load_database(self):
        """加载数据库"""
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, 'rb') as f:
                    self.motions = pickle.load(f)
            except:
                self.motions = {}
        else:
            self.motions = {}
            
    def save_database(self):
        """保存数据库"""
        with open(self.db_path, 'wb') as f:
            pickle.dump(self.motions, f)
            
    def add_motion(self, name, pose_sequence, features, metadata=None):
        """添加动作到数据库"""
        motion_id = len(self.motions)
        self.motions[motion_id] = {
            'id': motion_id,
            'name': name,
            'pose_sequence': pose_sequence,
            'features': features,
            'metadata': metadata or {},
            'created_at': datetime.now().isoformat()
        }
        self.save_database()
        return motion_id
        
    def find_similar_motions(self, query_sequence, max_results=5):
        """查找相似的动作"""
        if not self.motions:
            return []
            
        # 提取查询特征
        analyzer = EnhancedDanceAnalyzer()
        query_features = analyzer.extract_motion_features(query_sequence)
        
        similarities = []
        for motion_id, motion in self.motions.items():
            # 计算相似度
            similarity = analyzer.compare_with_reference(query_sequence, motion['pose_sequence'])
            similarities.append((motion_id, similarity['overall_similarity']))
            
        # 按相似度排序
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        # 返回前N个结果
        return [(self.motions[motion_id], similarity) for motion_id, similarity in similarities[:max_results]]


class VideoWidget(QLabel):
    """增强的视频显示组件，支持叠加信息显示"""
    def __init__(self, parent=None, view_id=0):
        super().__init__(parent)
        self.view_id = view_id
        self.setAlignment(Qt.AlignCenter)
        self.setText(f"视角 {view_id + 1} 预览区域")
        self.setMinimumSize(320, 240)
        self.setStyleSheet("border: 1px solid gray; background-color: black;")
        
        # 叠加信息
        self.overlay_info = {}
        self.show_overlay = True
        
    def set_overlay_info(self, info):
        """设置叠加信息"""
        self.overlay_info = info
        self.update()
        
    def set_show_overlay(self, show):
        """设置是否显示叠加信息"""
        self.show_overlay = show
        self.update()
        
    def paintEvent(self, event):
        """绘制事件，处理叠加信息显示"""
        # 先调用父类方法绘制图像
        super().paintEvent(event)
        
        if not self.show_overlay or not self.overlay_info:
            return
            
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 设置字体
        font = QFont("Arial", 10)
        painter.setFont(font)
        
        # 绘制视角ID
        painter.setPen(QPen(QColor(255, 255, 255), 2))
        painter.drawText(10, 20, f"视角 {self.view_id + 1}")
        
        # 绘制帧信息
        if 'frame' in self.overlay_info:
            painter.drawText(10, 40, f"帧: {self.overlay_info['frame']}")
            
        # 绘制姿态信息
        if 'pose_quality' in self.overlay_info:
            quality = self.overlay_info['pose_quality']
            color = QColor(0, 255, 0) if quality > 0.7 else QColor(255, 255, 0) if quality > 0.4 else QColor(255, 0, 0)
            painter.setPen(QPen(color, 2))
            painter.drawText(10, 60, f"姿态质量: {quality:.2f}")
            
        # 绘制运动信息
        if 'velocity' in self.overlay_info:
            painter.setPen(QPen(QColor(0, 200, 255), 2))
            painter.drawText(10, 80, f"速度: {self.overlay_info['velocity']:.2f}")
            
        # 绘制关节点
        if 'highlight_joints' in self.overlay_info:
            joints = self.overlay_info['highlight_joints']
            painter.setPen(QPen(QColor(255, 0, 0), 3))
            painter.setBrush(QBrush(QColor(255, 0, 0, 100)))
            
            for joint in joints:
                if 'x' in joint and 'y' in joint:
                    # 将归一化坐标转换为屏幕坐标
                    x = joint['x'] * self.width()
                    y = joint['y'] * self.height()
                    painter.drawEllipse(QPoint(x, y), 5, 5)


class EnhancedDanceSystemMainWindow(QMainWindow):
    """增强的舞蹈系统主窗口"""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("高级舞蹈分析系统 - 增强版")
        self.setGeometry(100, 100, 1920, 1080)
        
        # 初始化变量
        self.video_processors = {}  # 视角ID -> 处理器
        self.current_video_paths = {}  # 视角ID -> 路径
        self.pose_data = {}  # 视角ID -> 姿势数据
        self.multi_view_manager = MultiViewSyncManager()
        self.analysis_tools = EnhancedDanceAnalyzer()
        self.motion_database = DanceMotionDatabase()
        self.current_frame = 0
        self.is_playing = False
        
        # 创建UI
        self._create_ui()
        
        # 创建状态栏
        self.statusBar().showMessage("就绪")
        
        # 定时器用于播放控制
        self.play_timer = QTimer()
        self.play_timer.timeout.connect(self._play_next_frame)
    
    def _create_ui(self):
        """创建用户界面"""
        # 中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QHBoxLayout(central_widget)
        
        # 左侧面板 - 多视角视频
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # 多视角布局
        self.view_layout = QHBoxLayout()
        self.view_widgets = []
        
        # 创建两个视角（可根据需要扩展）
        for i in range(2):
            view_widget = VideoWidget(self, i)
            self.view_widgets.append(view_widget)
            self.view_layout.addWidget(view_widget)
        
        left_layout.addLayout(self.view_layout)
        
        # 时间轴
        self.timeline = TimelineWidget()
        self.timeline.currentFrameChanged.connect(self._on_timeline_frame_changed)
        left_layout.addWidget(self.timeline)
        
        # 控制按钮
        control_group = QGroupBox("视频控制")
        control_layout = QHBoxLayout(control_group)
        
        self.open_btn1 = QPushButton("打开视角 1")
        self.open_btn1.clicked.connect(lambda: self.open_video(0))
        
        self.open_btn2 = QPushButton("打开视角 2")
        self.open_btn2.clicked.connect(lambda: self.open_video(1))
        
        self.play_btn = QPushButton("播放")
        self.play_btn.clicked.connect(self.play_video)
        self.play_btn.setEnabled(False)
        
        self.pause_btn = QPushButton("暂停")
        self.pause_btn.clicked.connect(self.pause_video)
        self.pause_btn.setEnabled(False)
        
        self.stop_btn = QPushButton("停止")
        self.stop_btn.clicked.connect(self.stop_video)
        self.stop_btn.setEnabled(False)
        
        self.sync_btn = QPushButton("同步视角")
        self.sync_btn.clicked.connect(self.sync_views)
        self.sync_btn.setEnabled(False)
        
        control_layout.addWidget(self.open_btn1)
        control_layout.addWidget(self.open_btn2)
        control_layout.addWidget(self.play_btn)
        control_layout.addWidget(self.pause_btn)
        control_layout.addWidget(self.stop_btn)
        control_layout.addWidget(self.sync_btn)
        
        left_layout.addWidget(control_group)
        
        # 右侧面板 - 分析和可视化
        right_panel = QTabWidget()
        
        # 3D姿势标签页
        pose_tab = QWidget()
        pose_layout = QVBoxLayout(pose_tab)
        self.pose_visualizer = Pose3DVisualizer(self, width=6, height=5, dpi=100)
        pose_layout.addWidget(self.pose_visualizer)
        right_panel.addTab(pose_tab, "3D姿势")
        
        # 分析标签页
        analysis_tab = QWidget()
        analysis_layout = QVBoxLayout(analysis_tab)
        
        analysis_control_group = QGroupBox("分析控制")
        analysis_control_layout = QHBoxLayout(analysis_control_group)
        
        self.analyze_btn = QPushButton("分析舞蹈")
        self.analyze_btn.clicked.connect(self.analyze_dance)
        self.analyze_btn.setEnabled(False)
        
        self.compare_btn = QPushButton("对比分析")
        self.compare_btn.clicked.connect(self.compare_dance)
        self.compare_btn.setEnabled(False)
        
        self.export_btn = QPushButton("导出报告")
        self.export_btn.clicked.connect(self.export_report)
        self.export_btn.setEnabled(False)
        
        self.save_motion_btn = QPushButton("保存动作")
        self.save_motion_btn.clicked.connect(self.save_motion_to_db)
        self.save_motion_btn.setEnabled(False)
        
        analysis_control_layout.addWidget(self.analyze_btn)
        analysis_control_layout.addWidget(self.compare_btn)
        analysis_control_layout.addWidget(self.export_btn)
        analysis_control_layout.addWidget(self.save_motion_btn)
        analysis_layout.addWidget(analysis_control_group)
        
        # 结果显示
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        analysis_layout.addWidget(self.result_text)
        
        right_panel.addTab(analysis_tab, "分析结果")
        
        # 运动特征标签页
        features_tab = QWidget()
        features_layout = QVBoxLayout(features_tab)
        
        # 创建特征图表
        self.feature_canvas = FigureCanvas(Figure(figsize=(8, 6)))
        self.feature_ax = self.feature_canvas.figure.subplots(2, 2)
        self.feature_toolbar = NavigationToolbar(self.feature_canvas, self)
        
        features_layout.addWidget(self.feature_toolbar)
        features_layout.addWidget(self.feature_canvas)
        
        right_panel.addTab(features_tab, "运动特征")
        
        # 添加到主布局
        main_layout.addWidget(left_panel, 2)
        main_layout.addWidget(right_panel, 1)
        
        # 创建工具栏
        self._create_toolbar()
        
        # 创建菜单栏
        self._create_menu()
    
    def _create_toolbar(self):
        """创建工具栏"""
        toolbar = QToolBar("主工具栏")
        self.addToolBar(toolbar)
        
        # 添加工具栏动作
        open_action = QAction(QIcon("icons/open.png"), "打开视频", self)
        open_action.triggered.connect(lambda: self.open_video(0))
        toolbar.addAction(open_action)
        
        play_action = QAction(QIcon("icons/play.png"), "播放", self)
        play_action.triggered.connect(self.play_video)
        toolbar.addAction(play_action)
        
        pause_action = QAction(QIcon("icons/pause.png"), "暂停", self)
        pause_action.triggered.connect(self.pause_video)
        toolbar.addAction(pause_action)
        
        analyze_action = QAction(QIcon("icons/analyze.png"), "分析", self)
        analyze_action.triggered.connect(self.analyze_dance)
        toolbar.addAction(analyze_action)
        
        toolbar.addSeparator()
        
        settings_action = QAction(QIcon("icons/settings.png"), "设置", self)
        settings_action.triggered.connect(self.show_settings)
        toolbar.addAction(settings_action)
    
    def _create_menu(self):
        """创建菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu("文件")
        
        open_action = QAction("打开视频", self)
        open_action.triggered.connect(lambda: self.open_video(0))
        file_menu.addAction(open_action)
        
        export_action = QAction("导出报告", self)
        export_action.triggered.connect(self.export_report)
        file_menu.addAction(export_action)
        
        exit_action = QAction("退出", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 视图菜单
        view_menu = menubar.addMenu("视图")
        
        overlay_action = QAction("显示叠加信息", self)
        overlay_action.setCheckable(True)
        overlay_action.setChecked(True)
        overlay_action.triggered.connect(self.toggle_overlay)
        view_menu.addAction(overlay_action)
        
        # 分析菜单
        analysis_menu = menubar.addMenu("分析")
        
        analyze_action = QAction("分析舞蹈", self)
        analyze_action.triggered.connect(self.analyze_dance)
        analysis_menu.addAction(analyze_action)
        
        compare_action = QAction("对比分析", self)
        compare_action.triggered.connect(self.compare_dance)
        analysis_menu.addAction(compare_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu("帮助")
        
        about_action = QAction("关于", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def open_video(self, view_id):
        """打开视频文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, f"打开视角 {view_id + 1} 视频", "", 
            "视频文件 (*.mp4 *.avi *.mov *.mkv)"
        )
        
        if file_path:
            self.current_video_paths[view_id] = file_path
            
            # 更新UI
            if view_id == 0:
                self.open_btn1.setText(f"视角 1: {os.path.basename(file_path)}")
            else:
                self.open_btn2.setText(f"视角 2: {os.path.basename(file_path)}")
                
            # 如果有至少一个视频，启用播放按钮
            if len(self.current_video_paths) > 0:
                self.play_btn.setEnabled(True)
                self.sync_btn.setEnabled(True)
                
            self.statusBar().showMessage(f"已加载视角 {view_id + 1}: {os.path.basename(file_path)}")
    
    def play_video(self):
        """播放视频"""
        if not self.current_video_paths:
            QMessageBox.warning(self, "警告", "请先打开至少一个视频")
            return
            
        # 停止任何正在运行的处理器
        self.stop_video()
        
        # 为每个视角创建处理器
        for view_id, video_path in self.current_video_paths.items():
            processor = VideoProcessor(video_path, view_id)
            processor.frame_processed.connect(self.update_video_frame)
            processor.progress_updated.connect(self.update_progress)
            processor.processing_finished.connect(lambda vid=view_id: self.processing_finished(vid))
            processor.error_occurred.connect(self.handle_error)
            
            self.video_processors[view_id] = processor
            self.pose_data[view_id] = []
            
            # 添加到多视角管理器
            self.multi_view_manager.add_view(view_id, processor)
            
            # 启动处理器
            processor.start()
        
        self.is_playing = True
        self.play_btn.setEnabled(False)
        self.pause_btn.setEnabled(True)
        self.stop_btn.setEnabled(True)
        
        # 设置时间轴
        if self.video_processors:
            first_processor = next(iter(self.video_processors.values()))
            self.timeline.set_total_frames(first_processor.total_frames)
    
    def pause_video(self):
        """暂停视频"""
        for processor in self.video_processors.values():
            processor.pause()
            
        self.is_playing = False
        self.play_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        
        # 停止播放定时器
        self.play_timer.stop()
    
    def stop_video(self):
        """停止视频"""
        for processor in self.video_processors.values():
            processor.stop()
            
        self.video_processors.clear()
        self.is_playing = False
        self.play_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)
        
        # 停止播放定时器
        self.play_timer.stop()
        
        # 重置当前帧
        self.current_frame = 0
        self.timeline.set_current_frame(0)
    
    def processing_finished(self, view_id):
        """视频处理完成"""
        if view_id in self.video_processors:
            del self.video_processors[view_id]
            
        # 如果所有处理器都完成了
        if not self.video_processors:
            self.is_playing = False
            self.play_btn.setEnabled(True)
            self.pause_btn.setEnabled(False)
            self.stop_btn.setEnabled(False)
            
            # 启用分析按钮
            has_pose_data = any(self.pose_data.values() and 
                               any(frame_data for frame_data in self.pose_data.values()))
            self.analyze_btn.setEnabled(has_pose_data)
            self.compare_btn.setEnabled(has_pose_data)
            self.save_motion_btn.setEnabled(has_pose_data)
            
            self.statusBar().showMessage("处理完成")
    
    def update_video_frame(self, view_id, frame, landmarks, additional_data):
        """更新视频帧显示"""
        # 存储姿势数据
        if view_id not in self.pose_data:
            self.pose_data[view_id] = []
        self.pose_data[view_id].append(landmarks)
        
        # 更新多视角管理器
        self.multi_view_manager.update_view_data(view_id, frame, landmarks, additional_data)
        
        # 更新当前帧
        if view_id == 0:  # 以第一个视角为参考
            self.current_frame = len(self.pose_data[view_id]) - 1
            self.timeline.set_current_frame(self.current_frame)
        
        # 转换OpenCV图像为Qt图像
        rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qt_image)
        
        # 缩放图像以适应标签大小
        scaled_pixmap = pixmap.scaled(
            self.view_widgets[view_id].size(), 
            Qt.KeepAspectRatio, 
            Qt.SmoothTransformation
        )
        self.view_widgets[view_id].setPixmap(scaled_pixmap)
        
        # 更新叠加信息
        overlay_info = {
            'frame': self.current_frame,
            'pose_quality': np.mean([lm.get('visibility', 0) for lm in landmarks]) if landmarks else 0,
            'highlight_joints': landmarks if landmarks else []
        }
        
        # 如果有运动特征数据，添加到叠加信息
        if hasattr(self, 'motion_features') and self.motion_features and self.current_frame < len(self.motion_features):
            overlay_info['velocity'] = self.motion_features[self.current_frame].get('velocity', 0)
            
        self.view_widgets[view_id].set_overlay_info(overlay_info)
        
        # 更新3D姿势可视化（使用第一个视角的数据）
        if view_id == 0 and landmarks:
            self.pose_visualizer.update_pose(landmarks)
    
    def update_progress(self, view_id, progress):
        """更新进度条"""
        # 只更新第一个视角的进度（假设所有视角进度大致相同）
        if view_id == 0:
            self.timeline.set_current_frame(int(progress * self.timeline.total_frames / 100))
    
    def _play_next_frame(self):
        """播放下一帧（用于手动播放模式）"""
        if self.current_frame < self.timeline.total_frames - 1:
            self.current_frame += 1
            self.timeline.set_current_frame(self.current_frame)
            self._on_timeline_frame_changed(self.current_frame)
        else:
            self.play_timer.stop()
            self.play_btn.setEnabled(True)
            self.pause_btn.setEnabled(False)
    
    def _on_timeline_frame_changed(self, frame):
        """时间轴帧改变事件"""
        self.current_frame = frame
        
        # 更新所有视角的显示
        for view_id, data in self.multi_view_manager.view_data.items():
            if frame < len(data['frames']):
                # 转换OpenCV图像为Qt图像
                frame_data = data['frames'][frame]
                if isinstance(frame_data, np.ndarray):
                    rgb_image = cv2.cvtColor(frame_data, cv2.COLOR_BGR2RGB)
                    h, w, ch = rgb_image.shape
                    bytes_per_line = ch * w
                    qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
                    pixmap = QPixmap.fromImage(qt_image)
                    
                    # 缩放图像以适应标签大小
                    scaled_pixmap = pixmap.scaled(
                        self.view_widgets[view_id].size(), 
                        Qt.KeepAspectRatio, 
                        Qt.SmoothTransformation
                    )
                    self.view_widgets[view_id].setPixmap(scaled_pixmap)
                
                # 更新叠加信息
                landmarks = data['landmarks'][frame] if frame < len(data['landmarks']) else []
                overlay_info = {
                    'frame': frame,
                    'pose_quality': np.mean([lm.get('visibility', 0) for lm in landmarks]) if landmarks else 0,
                    'highlight_joints': landmarks if landmarks else []
                }
                
                # 如果有运动特征数据，添加到叠加信息
                if hasattr(self, 'motion_features') and self.motion_features and frame < len(self.motion_features):
                    overlay_info['velocity'] = self.motion_features[frame].get('velocity', 0)
                    
                self.view_widgets[view_id].set_overlay_info(overlay_info)
        
        # 更新3D姿势可视化
        if 0 in self.multi_view_manager.view_data and frame < len(self.multi_view_manager.view_data[0]['landmarks']):
            landmarks = self.multi_view_manager.view_data[0]['landmarks'][frame]
            if landmarks:
                self.pose_visualizer.update_pose(landmarks)
    
    def sync_views(self):
        """同步多视角"""
        self.statusBar().showMessage("正在同步多视角...")
        
        # 同步视角
        synced_data = self.multi_view_manager.synchronize_views()
        
        # 计算3D位置
        if len(synced_data) >= 2:
            self.three_d_positions = self.multi_view_manager.calculate_3d_positions(synced_data)
            if self.three_d_positions:
                self.statusBar().showMessage("多视角同步完成，3D位置已计算")
                
                # 更新3D可视化
                if self.current_frame < len(self.three_d_positions):
                    self.pose_visualizer.update_pose(
                        self.three_d_positions[self.current_frame],
                        title="多视角重建的3D姿势"
                    )
            else:
                self.statusBar().showMessage("多视角同步完成，但3D位置计算失败")
        else:
            self.statusBar().showMessage("需要至少两个视角才能进行同步")
    
    def analyze_dance(self):
        """分析舞蹈动作"""
        if not self.pose_data:
            QMessageBox.warning(self, "警告", "没有可分析的姿势数据")
            return
        
        self.statusBar().showMessage("正在分析舞蹈...")
        
        # 使用第一个视角的数据进行分析
        pose_sequence = self.pose_data[0]
        
        # 提取运动特征
        self.motion_features = self.analysis_tools.extract_motion_features(pose_sequence)
        
        # 分析节奏
        rhythm_analysis = self.analysis_tools.analyze_rhythm(self.motion_features)
        
        # 生成报告
        report = self.analysis_tools.generate_comprehensive_report(
            pose_sequence, self.motion_features, rhythm_analysis
        )
        
        # 显示分析结果
        result_text = f"""
        <h2>舞蹈分析报告</h2>
        <p><b>分析时间:</b> {report['timestamp']}</p>
        <p><b>总帧数:</b> {report['total_frames']} (有效帧: {report['valid_frames']})</p>
        <p><b>表现评分:</b> {report['performance_score']:.2f}/100</p>
        
        <h3>运动分析</h3>
        <p><b>平均速度:</b> {report['motion_analysis'].get('avg_velocity', 0):.4f}</p>
        <p><b>最大速度:</b> {report['motion_analysis'].get('max_velocity', 0):.4f}</p>
        <p><b>平均能量:</b> {report['motion_analysis'].get('avg_energy', 0):.4f}</p>
        <p><b>最大能量:</b> {report['motion_analysis'].get('max_energy', 0):.4f}</p>
        <p><b>流畅度:</b> {report['motion_analysis'].get('avg_fluency', 0):.4f}</p>
        <p><b>对称性:</b> {report['motion_analysis'].get('avg_symmetry', 0):.4f}</p>
        <p><b>动作变化性:</b> {report['motion_analysis'].get('movement_variability', 0):.4f}</p>
        
        <h3>节奏分析</h3>
        <p><b>节奏点数量:</b> {report['rhythm_analysis'].get('beat_count', 0)}</p>
        <p><b>节奏一致性:</b> {report['rhythm_analysis'].get('rhythm_consistency', 0):.4f}</p>
        <p><b>音乐同步性:</b> {report['rhythm_analysis'].get('music_sync', 0):.4f}</p>
        """
        
        self.result_text.setHtml(result_text)
        self.export_btn.setEnabled(True)
        
        # 可视化运动特征
        self.visualize_motion_features(self.motion_features, rhythm_analysis)
        
        # 动作聚类分析
        clusters = self.analysis_tools.cluster_movements(pose_sequence, n_clusters=5)
        if clusters:
            # 在时间轴上高亮显示不同的动作簇
            cluster_frames = [[] for _ in range(max(clusters) + 1)]
            for i, cluster in enumerate(clusters):
                if cluster is not None:
                    cluster_frames[cluster].append(i)
                    
            # 为每个簇选择一种颜色
            colors = [QColor(255, 0, 0), QColor(0, 255, 0), QColor(0, 0, 255), 
                     QColor(255, 255, 0), QColor(255, 0, 255)]
            
            # 在时间轴上添加高亮
            for cluster_id, frames in enumerate(cluster_frames):
                if frames:
                    color = colors[cluster_id % len(colors)]
                    self.timeline.set_highlight_frames(frames)
                    # 短暂暂停以显示高亮
                    QApplication.processEvents()
                    QTimer.singleShot(1000, lambda: self.timeline.set_highlight_frames([]))
        
        self.statusBar().showMessage("分析完成")
    
    def compare_dance(self):
        """对比分析舞蹈动作"""
        if not self.pose_data:
            QMessageBox.warning(self, "警告", "没有可分析的姿势数据")
            return
            
        # 选择参考动作
        ref_path, _ = QFileDialog.getOpenFileName(
            self, "选择参考动作文件", "", 
            "动作文件 (*.json *.pkl)"
        )
        
        if not ref_path:
            return
            
        try:
            # 加载参考数据
            if ref_path.endswith('.json'):
                with open(ref_path, 'r') as f:
                    ref_data = json.load(f)
                ref_pose_sequence = ref_data.get('pose_sequence', [])
            else:
                with open(ref_path, 'rb') as f:
                    ref_data = pickle.load(f)
                ref_pose_sequence = ref_data.get('pose_sequence', [])
                
            # 设置参考数据
            self.analysis_tools.set_reference_data(ref_pose_sequence)
            
            # 使用第一个视角的数据进行对比
            pose_sequence = self.pose_data[0]
            
            # 执行对比分析
            comparison_result = self.analysis_tools.compare_with_reference(pose_sequence, ref_pose_sequence)
            
            # 生成报告
            motion_features = self.analysis_tools.extract_motion_features(pose_sequence)
            rhythm_analysis = self.analysis_tools.analyze_rhythm(motion_features)
            
            report = self.analysis_tools.generate_comprehensive_report(
                pose_sequence, motion_features, rhythm_analysis, comparison_result
            )
            
            # 显示对比结果
            result_text = f"""
            <h2>舞蹈对比分析报告</h2>
            <p><b>参考动作:</b> {os.path.basename(ref_path)}</p>
            <p><b>表现评分:</b> {report['performance_score']:.2f}/100</p>
            
            <h3>对比结果</h3>
            <p><b>姿态相似度:</b> {comparison_result.get('pose_similarity', 0):.4f}</p>
            <p><b>轨迹相似度:</b> {comparison_result.get('trajectory_similarity', 0):.4f}</p>
            <p><b>节奏相似度:</b> {comparison_result.get('rhythm_similarity', 0):.4f}</p>
            <p><b>总体相似度:</b> {comparison_result.get('overall_similarity', 0):.4f}</p>
            """
            
            self.result_text.setHtml(result_text)
            
            # 在时间轴上显示误差
            if 'frame_errors' in comparison_result:
                errors = comparison_result['frame_errors']
                # 找到误差较大的帧
                avg_error = np.mean(errors) if errors else 0
                high_error_frames = [i for i, err in enumerate(errors) if err > avg_error * 1.5]
                self.timeline.set_highlight_frames(high_error_frames)
                
            self.statusBar().showMessage("对比分析完成")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载参考数据失败: {str(e)}")
    
    def visualize_motion_features(self, motion_features, rhythm_analysis):
        """可视化运动特征"""
        if not motion_features:
            return
            
        # 清除之前的图表
        for ax in self.feature_ax.flatten():
            ax.clear()
        
        # 提取数据
        frames = [f.get('frame', i) for i, f in enumerate(motion_features)]
        velocities = [f.get('velocity', 0) for f in motion_features]
        energies = [f.get('energy', 0) for f in motion_features]
        fluencies = [f.get('fluency', 0) for f in motion_features]
        symmetries = [f.get('symmetry', 0) for f in motion_features]
        
        # 绘制速度图表
        self.feature_ax[0, 0].plot(frames, velocities, 'b-')
        self.feature_ax[0, 0].set_title('速度')
        self.feature_ax[0, 0].set_xlabel('帧')
        self.feature_ax[0, 0].set_ylabel('速度')
        self.feature_ax[0, 0].grid(True)
        
        # 绘制能量图表
        self.feature_ax[0, 1].plot(frames, energies, 'r-')
        self.feature_ax[0, 1].set_title('能量')
        self.feature_ax[0, 1].set_xlabel('帧')
        self.feature_ax[0, 1].set_ylabel('能量')
        self.feature_ax[0, 1].grid(True)
        
        # 标记节奏点
        if 'energy_peaks' in rhythm_analysis:
            peaks = rhythm_analysis['energy_peaks']
            peak_energies = [energies[p] for p in peaks if p < len(energies)]
            self.feature_ax[0, 1].plot(peaks, peak_energies, 'ro')
        
        # 绘制流畅度图表
        self.feature_ax[1, 0].plot(frames, fluencies, 'g-')
        self.feature_ax[1, 0].set_title('流畅度')
        self.feature_ax[1, 0].set_xlabel('帧')
        self.feature_ax[1, 0].set_ylabel('流畅度')
        self.feature_ax[1, 0].grid(True)
        
        # 绘制对称性图表
        self.feature_ax[1, 1].plot(frames, symmetries, 'm-')
        self.feature_ax[1, 1].set_title('对称性')
        self.feature_ax[1, 1].set_xlabel('帧')
        self.feature_ax[1, 1].set_ylabel('对称性')
        self.feature_ax[1, 1].grid(True)
        
        # 调整布局
        self.feature_canvas.figure.tight_layout()
        self.feature_canvas.draw()
    
    def export_report(self):
        """导出分析报告"""
        if not hasattr(self, 'current_report'):
            QMessageBox.warning(self, "警告", "没有可导出的报告")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存报告", "", "JSON文件 (*.json)"
        )
        
        if file_path:
            with open(file_path, 'w') as f:
                json.dump(self.current_report, f, indent=4)
            
            self.statusBar().showMessage(f"报告已保存: {file_path}")
    
    def save_motion_to_db(self):
        """保存动作到数据库"""
        if not self.pose_data:
            QMessageBox.warning(self, "警告", "没有可保存的动作数据")
            return
            
        # 获取动作名称
        name, ok = QInputDialog.getText(self, "保存动作", "请输入动作名称:")
        if not ok or not name:
            return
            
        # 使用第一个视角的数据
        pose_sequence = self.pose_data[0]
        motion_features = self.analysis_tools.extract_motion_features(pose_sequence)
        
        # 添加到数据库
        motion_id = self.motion_database.add_motion(
            name, pose_sequence, motion_features,
            {
                'created_at': datetime.now().isoformat(),
                'frames': len(pose_sequence),
                'performance_score': self.current_report.get('performance_score', 0) if hasattr(self, 'current_report') else 0
            }
        )
        
        self.statusBar().showMessage(f"动作已保存到数据库，ID: {motion_id}")
    
    def toggle_overlay(self, show):
        """切换叠加信息显示"""
        for widget in self.view_widgets:
            widget.set_show_overlay(show)
    
    def show_settings(self):
        """显示设置对话框"""
        dialog = QDialog(self)
        dialog.setWindowTitle("设置")
        dialog.setModal(True)
        dialog.resize(400, 300)
        
        layout = QFormLayout(dialog)
        
        # 添加设置控件
        confidence_spin = QDoubleSpinBox()
        confidence_spin.setRange(0.0, 1.0)
        confidence_spin.setSingleStep(0.1)
        confidence_spin.setValue(0.5)
        layout.addRow("检测置信度:", confidence_spin)
        
        tracking_spin = QDoubleSpinBox()
        tracking_spin.setRange(0.0, 1.0)
        tracking_spin.setSingleStep(0.1)
        tracking_spin.setValue(0.5)
        layout.addRow("跟踪置信度:", tracking_spin)
        
        complexity_combo = QComboBox()
        complexity_combo.addItems(["轻量", "标准", "复杂"])
        complexity_combo.setCurrentIndex(1)
        layout.addRow("模型复杂度:", complexity_combo)
        
        segmentation_check = QCheckBox()
        segmentation_check.setChecked(False)
        layout.addRow("启用背景分割:", segmentation_check)
        
        # 添加按钮
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addRow(button_box)
        
        if dialog.exec_() == QDialog.Accepted:
            # 保存设置
            self.settings = {
                'min_detection_confidence': confidence_spin.value(),
                'min_tracking_confidence': tracking_spin.value(),
                'model_complexity': complexity_combo.currentIndex(),
                'enable_segmentation': segmentation_check.isChecked()
            }
            
            self.statusBar().showMessage("设置已保存")
    
    def show_about(self):
        """显示关于对话框"""
        QMessageBox.about(self, "关于", 
                         "高级舞蹈分析系统 - 增强版\n\n"
                         "一个基于PyQt和MediaPipe的舞蹈分析工具，"
                         "支持多视角同步、动作分析、节奏分析等功能。\n\n"
                         "版本: 2.0\n"
                         "发布日期: 2025-10-15")
    
    def handle_error(self, view_id, error_msg):
        """处理错误"""
        self.statusBar().showMessage(f"视角 {view_id + 1} 错误: {error_msg}")
        QMessageBox.warning(self, "处理错误", f"视角 {view_id + 1}: {error_msg}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = EnhancedDanceSystemMainWindow()
    window.show()
    sys.exit(app.exec_())