import sys
import numpy as np
import cv2
from PyQt5.QtWidgets import (QApplication, QButtonGroup, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QSlider, QLabel, QComboBox, QGroupBox, QSpinBox,
                             QDoubleSpinBox, QFileDialog, QMessageBox, QSplitter, QFrame,
                             QTabWidget, QProgressBar, QCheckBox, QTextEdit, QListWidget,
                             QListWidgetItem, QScrollArea, QSizePolicy, QGridLayout)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread, pyqtSlot, QPoint, QRect
from PyQt5.QtGui import QImage, QPixmap, QPainter, QPen, QColor, QFont, QIcon
import matplotlib
matplotlib.rc("font", family='Microsoft YaHei')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import json
import os
from datetime import datetime
import time
from scipy import ndimage
from sklearn.cluster import KMeans
import pandas as pd
from collections import deque


class MassagePatternGenerator:
    """按摩模式生成器"""
    
    @staticmethod
    def generate_circular_path(center, radius, points=50):
        """生成圆形路径"""
        path = []
        for i in range(points):
            angle = 2 * np.pi * i / points
            x = int(center[0] + radius * np.cos(angle))
            y = int(center[1] + radius * np.sin(angle))
            path.append((x, y))
        return path
    
    @staticmethod
    def generate_spiral_path(center, max_radius, points=100):
        """生成螺旋路径"""
        path = []
        for i in range(points):
            angle = 4 * np.pi * i / points
            radius = max_radius * i / points
            x = int(center[0] + radius * np.cos(angle))
            y = int(center[1] + radius * np.sin(angle))
            path.append((x, y))
        return path
    
    @staticmethod
    def generate_grid_path(rect, rows=10, cols=10):
        """生成网格路径"""
        x1, y1, x2, y2 = rect
        path = []
        
        # 水平线
        for i in range(rows + 1):
            y = y1 + i * (y2 - y1) // rows
            for j in range(cols + 1):
                x = x1 + j * (x2 - x1) // cols
                path.append((x, y))
        
        # 垂直线
        for j in range(cols + 1):
            x = x1 + j * (x2 - x1) // cols
            for i in range(rows + 1):
                y = y1 + i * (y2 - y1) // rows
                path.append((x, y))
                
        return path
    
    @staticmethod
    def generate_sinusoidal_path(rect, amplitude=50, frequency=0.1, points=200):
        """生成正弦波路径"""
        x1, y1, x2, y2 = rect
        center_y = (y1 + y2) // 2
        path = []
        
        for i in range(points):
            x = x1 + i * (x2 - x1) // points
            y = center_y + int(amplitude * np.sin(frequency * i))
            path.append((x, y))
            
        return path


class AdvancedImageProcessing:
    """高级图像处理工具类"""
    
    @staticmethod
    def load_image(file_path):
        """加载图像"""
        image = cv2.imread(file_path)
        if image is not None:
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        return image
    
    @staticmethod
    def detect_edges_advanced(image, method='canny'):
        """高级边缘检测"""
        if image is None:
            return None
            
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        
        if method == 'canny':
            edges = cv2.Canny(gray, 50, 150)
        elif method == 'sobel':
            sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=5)
            sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=5)
            edges = np.sqrt(sobelx**2 + sobely**2)
            edges = np.uint8(edges)
        elif method == 'laplacian':
            edges = cv2.Laplacian(gray, cv2.CV_64F)
            edges = np.uint8(np.absolute(edges))
        
        return cv2.cvtColor(edges, cv2.COLOR_GRAY2RGB)
    
    @staticmethod
    def detect_skin_advanced(image, method='hsv'):
        """高级皮肤检测"""
        if image is None:
            return None
            
        if method == 'hsv':
            hsv = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)
            lower_skin = np.array([0, 20, 70], dtype=np.uint8)
            upper_skin = np.array([20, 255, 255], dtype=np.uint8)
            mask = cv2.inRange(hsv, lower_skin, upper_skin)
        elif method == 'ycbcr':
            ycbcr = cv2.cvtColor(image, cv2.COLOR_RGB2YCrCb)
            lower_skin = np.array([0, 133, 77], dtype=np.uint8)
            upper_skin = np.array([255, 173, 127], dtype=np.uint8)
            mask = cv2.inRange(ycbcr, lower_skin, upper_skin)
        
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        
        result = cv2.bitwise_and(image, image, mask=mask)
        return result
    
    @staticmethod
    def detect_muscle_tension(image):
        """肌肉紧张度检测"""
        if image is None:
            return None
            
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        
        # 使用Gabor滤波器检测纹理（模拟肌肉紧张度）
        kernels = []
        for theta in range(4):
            theta = theta / 4. * np.pi
            kernel = cv2.getGaborKernel((21, 21), 5.0, theta, 10.0, 0.5, 0, ktype=cv2.CV_32F)
            kernels.append(kernel)
        
        accum = np.zeros_like(gray, dtype=np.float32)
        for kernel in kernels:
            filtered = cv2.filter2D(gray, cv2.CV_32F, kernel)
            accum += filtered
        
        # 归一化并转换为热力图
        accum = cv2.normalize(accum, None, 0, 255, cv2.NORM_MINMAX)
        heatmap = cv2.applyColorMap(np.uint8(accum), cv2.COLORMAP_JET)
        heatmap = cv2.cvtColor(heatmap, cv2.COLOR_BGR2RGB)
        
        # 叠加到原图
        result = cv2.addWeighted(image, 0.7, heatmap, 0.3, 0)
        return result
    
    @staticmethod
    def detect_acupoints(image):
        """穴位检测（模拟）"""
        if image is None:
            return None
            
        result = image.copy()
        height, width = image.shape[:2]
        
        # 模拟穴位点（实际应用中需要使用专业的穴位检测算法）
        points = []
        for i in range(10):
            x = np.random.randint(50, width-50)
            y = np.random.randint(50, height-50)
            points.append((x, y))
            
        for point in points:
            cv2.circle(result, point, 10, (255, 0, 0), -1)
            cv2.circle(result, point, 15, (0, 255, 255), 2)
            
        return result
    
    @staticmethod
    def analyze_pressure_points(image, paths):
        """分析压力点分布"""
        if image is None or not paths:
            return None
            
        result = image.copy()
        height, width = image.shape[:2]
        
        # 创建压力分布图
        pressure_map = np.zeros((height, width), dtype=np.float32)
        
        for path in paths:
            for i, (x, y) in enumerate(path):
                if 0 <= x < width and 0 <= y < height:
                    # 路径中间部分压力更大
                    pressure = 1.0 - abs(i - len(path)/2) / (len(path)/2)
                    cv2.circle(pressure_map, (x, y), 20, pressure, -1)
        
        # 应用高斯模糊
        pressure_map = cv2.GaussianBlur(pressure_map, (51, 51), 0)
        
        # 转换为热力图
        pressure_map = cv2.normalize(pressure_map, None, 0, 255, cv2.NORM_MINMAX)
        heatmap = cv2.applyColorMap(np.uint8(pressure_map), cv2.COLORMAP_JET)
        heatmap = cv2.cvtColor(heatmap, cv2.COLOR_BGR2RGB)
        
        # 叠加到原图
        result = cv2.addWeighted(result, 0.6, heatmap, 0.4, 0)
        return result
    
    @staticmethod
    def segment_body_parts(image):
        """身体部位分割"""
        if image is None:
            return None
            
        # 使用K-means进行简单分割
        pixel_values = image.reshape((-1, 3))
        pixel_values = np.float32(pixel_values)
        
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 100, 0.2)
        k = 4
        _, labels, centers = cv2.kmeans(pixel_values, k, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS)
        
        centers = np.uint8(centers)
        segmented_data = centers[labels.flatten()]
        segmented_image = segmented_data.reshape(image.shape)
        
        return segmented_image


class MassageAITrainer(QThread):
    """AI按摩训练器线程"""
    progress_updated = pyqtSignal(int)
    training_completed = pyqtSignal(dict)
    
    def __init__(self, massage_data):
        super().__init__()
        self.massage_data = massage_data
        self.is_running = True
        
    def run(self):
        """模拟AI训练过程"""
        # 模拟训练过程
        for i in range(101):
            if not self.is_running:
                return
                
            time.sleep(0.05)  # 模拟计算时间
            self.progress_updated.emit(i)
        
        # 生成模拟的训练结果
        results = {
            'optimal_intensity': np.random.randint(3, 8),
            'optimal_frequency': np.random.randint(20, 60),
            'recommended_duration': np.random.randint(5, 20),
            'effectiveness_score': np.random.uniform(0.7, 0.95),
            'suggestions': ['增加背部按摩时间', '降低肩部按摩强度', '添加颈部放松模式']
        }
        
        self.training_completed.emit(results)
        
    def stop(self):
        self.is_running = False


class EnhancedImageCanvas(QLabel):
    """增强版图像画布，支持多种绘制模式"""
    pointSelected = pyqtSignal(int, int)
    pathCompleted = pyqtSignal(list)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(640, 480)
        self.setAlignment(Qt.AlignCenter)
        self.setText("请加载图像")
        self.setStyleSheet("border: 2px solid #3498db; border-radius: 5px;")
        
        self.image = None
        self.massage_paths = []
        self.current_path = []
        self.drawing = False
        self.draw_mode = "freehand"  # freehand, straight, circle, rectangle
        self.start_point = None
        self.brush_size = 3
        
    def set_image(self, image):
        """设置显示的图像"""
        if image is None:
            return
            
        self.image = image
        self.update_display()
        
    def set_draw_mode(self, mode):
        """设置绘制模式"""
        self.draw_mode = mode
        self.current_path = []
        self.start_point = None
        
    def set_brush_size(self, size):
        """设置画笔大小"""
        self.brush_size = size
        
    def clear_paths(self):
        """清除所有按摩路径"""
        self.massage_paths = []
        self.current_path = []
        self.start_point = None
        self.update_display()
        
    def mousePressEvent(self, event):
        """鼠标按下事件"""
        if self.image is None:
            return
            
        img_x, img_y = self.get_image_coordinates(event.pos())
        if img_x is None or img_y is None:
            return
            
        if event.button() == Qt.LeftButton:
            self.drawing = True
            self.start_point = (img_x, img_y)
            
            if self.draw_mode == "freehand":
                self.current_path = [(img_x, img_y)]
            else:
                self.current_path = []
                
            self.pointSelected.emit(img_x, img_y)
            
    def mouseMoveEvent(self, event):
        """鼠标移动事件"""
        if self.drawing and self.image is not None:
            img_x, img_y = self.get_image_coordinates(event.pos())
            if img_x is None or img_y is None:
                return
                
            if self.draw_mode == "freehand":
                self.current_path.append((img_x, img_y))
                self.update_display()
            else:
                self.current_path = [self.start_point, (img_x, img_y)]
                self.update_display()
                
    def mouseReleaseEvent(self, event):
        """鼠标释放事件"""
        if event.button() == Qt.LeftButton and self.drawing:
            self.drawing = False
            img_x, img_y = self.get_image_coordinates(event.pos())
            
            if self.draw_mode in ["straight", "circle", "rectangle"] and self.start_point:
                if img_x is not None and img_y is not None:
                    # 生成相应的路径
                    if self.draw_mode == "straight":
                        path = self.generate_straight_path(self.start_point, (img_x, img_y))
                    elif self.draw_mode == "circle":
                        radius = int(np.sqrt((img_x-self.start_point[0])**2 + (img_y-self.start_point[1])**2))
                        path = MassagePatternGenerator.generate_circular_path(self.start_point, radius)
                    elif self.draw_mode == "rectangle":
                        path = self.generate_rectangle_path(self.start_point, (img_x, img_y))
                    
                    self.massage_paths.append(path)
                    self.pathCompleted.emit(path)
                    
            elif self.draw_mode == "freehand" and len(self.current_path) > 1:
                self.massage_paths.append(self.current_path.copy())
                self.pathCompleted.emit(self.current_path.copy())
                
            self.current_path = []
            self.start_point = None
            self.update_display()
            
    def get_image_coordinates(self, pos):
        """获取图像坐标"""
        pixmap = self.pixmap()
        if not pixmap:
            return None, None
            
        img_rect = pixmap.rect()
        img_rect.moveCenter(self.rect().center())
        
        if img_rect.contains(pos):
            rel_x = pos.x() - img_rect.x()
            rel_y = pos.y() - img_rect.y()
            
            img_x = int(rel_x * self.image.shape[1] / img_rect.width())
            img_y = int(rel_y * self.image.shape[0] / img_rect.height())
            
            return img_x, img_y
            
        return None, None
        
    def generate_straight_path(self, start, end, points=50):
        """生成直线路径"""
        path = []
        for i in range(points):
            t = i / (points - 1)
            x = int(start[0] + t * (end[0] - start[0]))
            y = int(start[1] + t * (end[1] - start[1]))
            path.append((x, y))
        return path
        
    def generate_rectangle_path(self, start, end):
        """生成矩形路径"""
        x1, y1 = start
        x2, y2 = end
        
        path = []
        # 上边
        for x in range(min(x1, x2), max(x1, x2), 5):
            path.append((x, min(y1, y2)))
        # 右边
        for y in range(min(y1, y2), max(y1, y2), 5):
            path.append((max(x1, x2), y))
        # 下边
        for x in range(max(x1, x2), min(x1, x2), -5):
            path.append((x, max(y1, y2)))
        # 左边
        for y in range(max(y1, y2), min(y1, y2), -5):
            path.append((min(x1, x2), y))
            
        return path
        
    def update_display(self):
        """更新显示，绘制按摩路径"""
        if self.image is None:
            return
            
        display_image = self.image.copy()
        
        # 绘制所有按摩路径
        for i, path in enumerate(self.massage_paths):
            color = self.get_path_color(i)
            for j in range(1, len(path)):
                cv2.line(display_image, path[j-1], path[j], color, self.brush_size)
                
                # 在路径上标记方向
                if j % 10 == 0:
                    dx = path[j][0] - path[j-1][0]
                    dy = path[j][1] - path[j-1][1]
                    angle = np.arctan2(dy, dx)
                    arrow_len = 15
                    end_x = int(path[j][0] - arrow_len * np.cos(angle))
                    end_y = int(path[j][1] - arrow_len * np.sin(angle))
                    cv2.arrowedLine(display_image, (end_x, end_y), path[j], color, 2)
                
        # 绘制当前路径
        if self.current_path:
            color = (255, 0, 0)  # 红色表示当前路径
            for j in range(1, len(self.current_path)):
                cv2.line(display_image, self.current_path[j-1], self.current_path[j], color, self.brush_size)
                
        self.display_image(display_image)
        
    def get_path_color(self, index):
        """获取路径颜色"""
        colors = [
            (0, 255, 0),    # 绿色
            (255, 255, 0),  # 黄色
            (0, 255, 255),  # 青色
            (255, 0, 255),  # 紫色
            (255, 165, 0),  # 橙色
        ]
        return colors[index % len(colors)]
        
    def display_image(self, image):
        """显示图像"""
        height, width, channel = image.shape
        bytes_per_line = 3 * width
        q_img = QImage(image.data, width, height, bytes_per_line, QImage.Format_RGB888).rgbSwapped()
        self.setPixmap(QPixmap.fromImage(q_img).scaled(
            self.width(), self.height(), Qt.KeepAspectRatio, Qt.SmoothTransformation))


class AdvancedMassageParameterPanel(QWidget):
    """高级按摩参数控制面板"""
    parametersChanged = pyqtSignal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.presets = self.load_presets()
        self.init_ui()
        
    def load_presets(self):
        """加载预设参数"""
        return {
            "放松模式": {"intensity": 3, "frequency": 25, "temperature": 38, "pressure": 4},
            "治疗模式": {"intensity": 7, "frequency": 45, "temperature": 42, "pressure": 7},
            "深度按摩": {"intensity": 9, "frequency": 60, "temperature": 45, "pressure": 9},
            "舒缓模式": {"intensity": 2, "frequency": 20, "temperature": 36, "pressure": 3}
        }
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 预设选择
        preset_group = QGroupBox("快速预设")
        preset_layout = QHBoxLayout()
        self.preset_combo = QComboBox()
        self.preset_combo.addItems(["自定义"] + list(self.presets.keys()))
        self.preset_combo.currentTextChanged.connect(self.apply_preset)
        preset_layout.addWidget(QLabel("预设:"))
        preset_layout.addWidget(self.preset_combo)
        preset_layout.addStretch()
        preset_group.setLayout(preset_layout)
        layout.addWidget(preset_group)
        
        # 按摩模式选择
        mode_group = QGroupBox("按摩模式")
        mode_layout = QGridLayout()
        
        self.mode_buttons = {}
        modes = [
            ("指压", "缓解肌肉紧张"), 
            ("揉捏", "促进血液循环"),
            ("敲击", "放松深层组织"), 
            ("振动", "缓解神经紧张"),
            ("推拿", "传统中医手法"),
            ("刮痧", "活血化瘀"),
            ("热石", "热疗放松"),
            ("冷敷", "消炎镇痛")
        ]
        
        for i, (mode, desc) in enumerate(modes):
            btn = QPushButton(mode)
            btn.setToolTip(desc)
            btn.setCheckable(True)
            btn.clicked.connect(self.on_mode_changed)
            mode_layout.addWidget(btn, i//2, i%2)
            self.mode_buttons[mode] = btn
            
        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)
        
        # 强度控制
        intensity_group = QGroupBox("强度控制")
        intensity_layout = QVBoxLayout()
        
        self.intensity_slider = QSlider(Qt.Horizontal)
        self.intensity_slider.setMinimum(1)
        self.intensity_slider.setMaximum(10)
        self.intensity_slider.setValue(5)
        self.intensity_label = QLabel("强度: 5")
        
        intensity_layout.addWidget(self.intensity_label)
        intensity_layout.addWidget(self.intensity_slider)
        intensity_group.setLayout(intensity_layout)
        layout.addWidget(intensity_group)
        
        # 频率控制
        frequency_group = QGroupBox("频率控制")
        frequency_layout = QVBoxLayout()
        
        self.frequency_slider = QSlider(Qt.Horizontal)
        self.frequency_slider.setMinimum(1)
        self.frequency_slider.setMaximum(100)
        self.frequency_slider.setValue(30)
        self.frequency_label = QLabel("频率: 30 Hz")
        
        frequency_layout.addWidget(self.frequency_label)
        frequency_layout.addWidget(self.frequency_slider)
        frequency_group.setLayout(frequency_layout)
        layout.addWidget(frequency_group)
        
        # 高级参数
        advanced_group = QGroupBox("高级参数")
        advanced_layout = QGridLayout()
        
        # 温度控制
        advanced_layout.addWidget(QLabel("温度:"), 0, 0)
        self.temperature_spin = QSpinBox()
        self.temperature_spin.setRange(30, 50)
        self.temperature_spin.setValue(40)
        self.temperature_spin.setSuffix(" °C")
        advanced_layout.addWidget(self.temperature_spin, 0, 1)
        
        # 压力灵敏度
        advanced_layout.addWidget(QLabel("压力灵敏度:"), 1, 0)
        self.pressure_spin = QSpinBox()
        self.pressure_spin.setRange(1, 10)
        self.pressure_spin.setValue(5)
        advanced_layout.addWidget(self.pressure_spin, 1, 1)
        
        # 按摩深度
        advanced_layout.addWidget(QLabel("按摩深度:"), 2, 0)
        self.depth_slider = QSlider(Qt.Horizontal)
        self.depth_slider.setRange(1, 5)
        self.depth_slider.setValue(3)
        advanced_layout.addWidget(self.depth_slider, 2, 1)
        
        advanced_group.setLayout(advanced_layout)
        layout.addWidget(advanced_group)
        
        # 时间控制
        time_group = QGroupBox("时间控制")
        time_layout = QGridLayout()
        
        time_layout.addWidget(QLabel("总时长:"), 0, 0)
        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(1, 120)
        self.duration_spin.setValue(15)
        self.duration_spin.setSuffix(" 分钟")
        time_layout.addWidget(self.duration_spin, 0, 1)
        
        time_layout.addWidget(QLabel("间隔时间:"), 1, 0)
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(0, 10)
        self.interval_spin.setValue(2)
        self.interval_spin.setSuffix(" 秒")
        time_layout.addWidget(self.interval_spin, 1, 1)
        
        time_group.setLayout(time_layout)
        layout.addWidget(time_group)
        
        # 控制按钮
        control_layout = QHBoxLayout()
        self.start_btn = QPushButton("开始按摩")
        self.start_btn.setStyleSheet("QPushButton { background-color: #27ae60; color: white; font-weight: bold; }")
        self.pause_btn = QPushButton("暂停")
        self.pause_btn.setEnabled(False)
        self.stop_btn = QPushButton("停止")
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("QPushButton { background-color: #e74c3c; color: white; }")
        
        control_layout.addWidget(self.start_btn)
        control_layout.addWidget(self.pause_btn)
        control_layout.addWidget(self.stop_btn)
        layout.addLayout(control_layout)
        
        layout.addStretch()
        self.setLayout(layout)
        
        # 连接信号
        self.connect_signals()
        
    def connect_signals(self):
        """连接信号"""
        self.intensity_slider.valueChanged.connect(
            lambda v: self.intensity_label.setText(f"强度: {v}"))
        self.frequency_slider.valueChanged.connect(
            lambda v: self.frequency_label.setText(f"频率: {v} Hz"))
            
        # 参数变化信号
        sliders = [self.intensity_slider, self.frequency_slider, self.depth_slider]
        spins = [self.temperature_spin, self.pressure_spin, self.duration_spin, self.interval_spin]
        
        for slider in sliders:
            slider.valueChanged.connect(self.emit_parameters)
        for spin in spins:
            spin.valueChanged.connect(self.emit_parameters)
            
    def on_mode_changed(self):
        """模式选择变化"""
        sender = self.sender()
        for mode, btn in self.mode_buttons.items():
            if btn != sender:
                btn.setChecked(False)
                
        self.emit_parameters()
        
    def apply_preset(self, preset_name):
        """应用预设"""
        if preset_name != "自定义" and preset_name in self.presets:
            preset = self.presets[preset_name]
            self.intensity_slider.setValue(preset["intensity"])
            self.frequency_slider.setValue(preset["frequency"])
            self.temperature_spin.setValue(preset["temperature"])
            self.pressure_spin.setValue(preset["pressure"])
            
    def emit_parameters(self):
        """发射参数变化信号"""
        params = {
            "intensity": self.intensity_slider.value(),
            "frequency": self.frequency_slider.value(),
            "temperature": self.temperature_spin.value(),
            "pressure": self.pressure_spin.value(),
            "depth": self.depth_slider.value(),
            "duration": self.duration_spin.value(),
            "interval": self.interval_spin.value(),
            "mode": self.get_selected_mode()
        }
        self.parametersChanged.emit(params)
        
    def get_selected_mode(self):
        """获取选中的模式"""
        for mode, btn in self.mode_buttons.items():
            if btn.isChecked():
                return mode
        return "指压"
        
    def get_parameters(self):
        """获取当前参数"""
        return {
            "intensity": self.intensity_slider.value(),
            "frequency": self.frequency_slider.value(),
            "temperature": self.temperature_spin.value(),
            "pressure": self.pressure_spin.value(),
            "depth": self.depth_slider.value(),
            "duration": self.duration_spin.value(),
            "interval": self.interval_spin.value(),
            "mode": self.get_selected_mode()
        }


class RealTimeVisualization(FigureCanvas):
    """实时可视化组件"""
    def __init__(self, parent=None):
        self.fig = Figure(figsize=(8, 6), dpi=100)
        super().__init__(self.fig)
        self.setParent(parent)
        
        # 创建子图
        self.ax1 = self.fig.add_subplot(211)  # 力度和频率
        self.ax2 = self.fig.add_subplot(212)  # 压力分布
        
        self.setup_plots()
        
        self.time_data = deque(maxlen=200)
        self.intensity_data = deque(maxlen=200)
        self.frequency_data = deque(maxlen=200)
        self.pressure_data = deque(maxlen=200)
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_plots)
        self.timer.start(50)  # 20Hz更新频率
        
    def setup_plots(self):
        """设置图表"""
        # 第一个图表：力度和频率
        self.ax1.set_title("按摩参数实时监测", fontsize=12, fontweight='bold')
        self.ax1.set_ylabel("强度/频率")
        self.ax1.grid(True, alpha=0.3)
        
        self.line_intensity, = self.ax1.plot([], [], 'r-', linewidth=2, label="力度")
        self.line_frequency, = self.ax1.plot([], [], 'b-', linewidth=2, label="频率")
        self.ax1.legend(loc='upper right')
        
        # 第二个图表：压力分布
        self.ax2.set_title("压力分布热力图", fontsize=12, fontweight='bold')
        self.ax2.set_xlabel("时间 (s)")
        self.ax2.set_ylabel("压力等级")
        
        # 初始化热力图数据
        self.pressure_heatmap = self.ax2.imshow(
            np.random.rand(10, 50), 
            cmap='hot', 
            aspect='auto',
            interpolation='nearest'
        )
        self.fig.colorbar(self.pressure_heatmap, ax=self.ax2, label='压力强度')
        
        self.fig.tight_layout()
        
    def update_plots(self):
        """更新图表"""
        if len(self.time_data) > 0:
            # 更新线图
            self.line_intensity.set_data(self.time_data, self.intensity_data)
            self.line_frequency.set_data(self.time_data, self.frequency_data)
            
            # 更新热力图
            if len(self.pressure_data) > 0:
                heatmap_data = np.array(list(self.pressure_data)[-50:]).reshape(10, -1)
                if heatmap_data.size > 0:
                    self.pressure_heatmap.set_data(heatmap_data)
                    self.pressure_heatmap.set_clim(vmin=0, vmax=10)
            
            # 调整坐标轴
            if len(self.time_data) > 1:
                self.ax1.set_xlim(max(0, self.time_data[0]), self.time_data[-1])
                max_val = max(max(self.intensity_data or [0]), max(self.frequency_data or [0]))
                self.ax1.set_ylim(0, max(10, max_val * 1.2))
                
            self.draw()
            
    def add_data(self, time, intensity, frequency, pressure):
        """添加数据点"""
        self.time_data.append(time)
        self.intensity_data.append(intensity)
        self.frequency_data.append(frequency)
        self.pressure_data.append(pressure)


class MassageSessionManager:
    """按摩会话管理器"""
    def __init__(self):
        self.sessions = []
        self.current_session = None
        
    def start_new_session(self, image_path, parameters):
        """开始新会话"""
        session = {
            'id': len(self.sessions) + 1,
            'start_time': datetime.now(),
            'image_path': image_path,
            'parameters': parameters,
            'paths': [],
            'duration': 0,
            'effectiveness': 0
        }
        self.current_session = session
        self.sessions.append(session)
        return session
        
    def add_path(self, path):
        """添加按摩路径"""
        if self.current_session:
            self.current_session['paths'].append(path)
            
    def end_session(self, effectiveness=0):
        """结束会话"""
        if self.current_session:
            self.current_session['end_time'] = datetime.now()
            self.current_session['duration'] = (
                self.current_session['end_time'] - self.current_session['start_time']
            ).total_seconds()
            self.current_session['effectiveness'] = effectiveness
            self.current_session = None
            
    def get_session_history(self):
        """获取会话历史"""
        return self.sessions
        
    def save_sessions(self, filename):
        """保存会话到文件"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.sessions, f, indent=2, default=str)
            return True
        except Exception as e:
            print(f"保存会话失败: {e}")
            return False
            
    def load_sessions(self, filename):
        """从文件加载会话"""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                self.sessions = json.load(f)
            return True
        except Exception as e:
            print(f"加载会话失败: {e}")
            return False


class EnhancedMassageSystem(QMainWindow):
    """增强版按摩系统主窗口"""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("高级智能视觉按摩系统 v2.0")
        self.setGeometry(100, 100, 1600, 1000)
        
        self.current_image = None
        self.current_image_path = None
        self.massage_timer = QTimer()
        self.massage_time_elapsed = 0
        self.is_massage_running = False
        self.is_massage_paused = False
        
        self.session_manager = MassageSessionManager()
        self.ai_trainer = None
        
        self.init_ui()
        self.connect_signals()
        
    def init_ui(self):
        """初始化UI"""
        # 中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QHBoxLayout(central_widget)
        
        # 左侧面板
        left_panel = QVBoxLayout()
        left_panel.setContentsMargins(5, 5, 5, 5)
        
        # 图像处理工具栏
        image_toolbar = self.create_image_toolbar()
        left_panel.addLayout(image_toolbar)
        
        # 绘图工具工具栏
        draw_toolbar = self.create_draw_toolbar()
        left_panel.addLayout(draw_toolbar)
        
        # 图像画布
        self.image_canvas = EnhancedImageCanvas()
        left_panel.addWidget(self.image_canvas)
        
        # 右侧面板（使用选项卡）
        right_panel = QTabWidget()
        right_panel.setMaximumWidth(400)
        
        # 参数控制选项卡
        param_tab = QWidget()
        param_layout = QVBoxLayout(param_tab)
        self.param_panel = AdvancedMassageParameterPanel()
        param_layout.addWidget(self.param_panel)
        right_panel.addTab(param_tab, "参数控制")
        
        # 可视化选项卡
        viz_tab = QWidget()
        viz_layout = QVBoxLayout(viz_tab)
        self.visualization = RealTimeVisualization()
        viz_layout.addWidget(self.visualization)
        right_panel.addTab(viz_tab, "实时监测")
        
        # AI分析选项卡
        ai_tab = QWidget()
        ai_layout = QVBoxLayout(ai_tab)
        ai_layout.addWidget(self.create_ai_panel())
        right_panel.addTab(ai_tab, "AI分析")
        
        # 会话历史选项卡
        history_tab = QWidget()
        history_layout = QVBoxLayout(history_tab)
        history_layout.addWidget(self.create_history_panel())
        right_panel.addTab(history_tab, "会话历史")
        
        # 添加到主布局
        main_layout.addLayout(left_panel, 70)
        main_layout.addWidget(right_panel, 30)
        
        # 状态栏
        self.statusBar().showMessage("就绪")
        
        # 应用样式
        self.apply_styles()
        
    def create_image_toolbar(self):
        """创建图像处理工具栏"""
        toolbar = QHBoxLayout()
        
        # 图像加载
        self.load_btn = QPushButton("加载图像")
        self.load_btn.setIcon(self.style().standardIcon(getattr(self.style(), 'SP_FileIcon')))
        
        # 图像处理按钮
        processing_buttons = [
            ("边缘检测", "SP_FileDialogContentsView"),
            ("皮肤检测", "SP_FileDialogDetailedView"),
            ("肌肉分析", "SP_ComputerIcon"),
            ("穴位检测", "SP_DirHomeIcon"),
            ("压力分析", "SP_FileDialogInfoView"),
            ("身体分割", "SP_DirIcon"),
            ("图像增强", "SP_FileDialogBackIcon")
        ]
        
        for text, icon in processing_buttons:
            btn = QPushButton(text)
            if hasattr(self.style(), icon):
                btn.setIcon(self.style().standardIcon(getattr(self.style(), icon)))
            toolbar.addWidget(btn)
            
        toolbar.addWidget(self.load_btn)
        toolbar.addStretch()
        
        # 连接信号（在connect_signals方法中完成）
        return toolbar
        
    def create_draw_toolbar(self):
        """创建绘图工具工具栏"""
        toolbar = QHBoxLayout()
        
        toolbar.addWidget(QLabel("绘图模式:"))
        
        draw_modes = [
            ("自由绘制", "freehand"),
            ("直线", "straight"),
            ("圆形", "circle"),
            ("矩形", "rectangle")
        ]
        
        self.draw_mode_group = QButtonGroup(self)
        for text, mode in draw_modes:
            btn = QPushButton(text)
            btn.setCheckable(True)
            btn.setProperty("mode", mode)
            self.draw_mode_group.addButton(btn)
            toolbar.addWidget(btn)
            
        # 设置自由绘制为默认选中
        self.draw_mode_group.buttons()[0].setChecked(True)
        
        toolbar.addWidget(QLabel("画笔大小:"))
        self.brush_slider = QSlider(Qt.Horizontal)
        self.brush_slider.setRange(1, 10)
        self.brush_slider.setValue(3)
        toolbar.addWidget(self.brush_slider)
        
        self.clear_btn = QPushButton("清除路径")
        self.clear_btn.setStyleSheet("QPushButton { background-color: #e74c3c; color: white; }")
        toolbar.addWidget(self.clear_btn)
        
        toolbar.addStretch()
        return toolbar
        
    def create_ai_panel(self):
        """创建AI分析面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # AI训练按钮
        self.ai_train_btn = QPushButton("开始AI分析")
        self.ai_train_btn.setStyleSheet("QPushButton { background-color: #9b59b6; color: white; font-weight: bold; }")
        
        # 进度条
        self.ai_progress = QProgressBar()
        self.ai_progress.setVisible(False)
        
        # 结果显示
        self.ai_results = QTextEdit()
        self.ai_results.setReadOnly(True)
        self.ai_results.setMaximumHeight(200)
        
        layout.addWidget(self.ai_train_btn)
        layout.addWidget(self.ai_progress)
        layout.addWidget(QLabel("分析结果:"))
        layout.addWidget(self.ai_results)
        layout.addStretch()
        
        return panel
        
    def create_history_panel(self):
        """创建历史记录面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # 会话列表
        self.session_list = QListWidget()
        
        # 控制按钮
        history_controls = QHBoxLayout()
        self.save_history_btn = QPushButton("保存历史")
        self.load_history_btn = QPushButton("加载历史")
        self.clear_history_btn = QPushButton("清空历史")
        
        history_controls.addWidget(self.save_history_btn)
        history_controls.addWidget(self.load_history_btn)
        history_controls.addWidget(self.clear_history_btn)
        
        # 会话详情
        self.session_details = QTextEdit()
        self.session_details.setReadOnly(True)
        
        layout.addWidget(QLabel("按摩会话历史:"))
        layout.addWidget(self.session_list)
        layout.addLayout(history_controls)
        layout.addWidget(QLabel("会话详情:"))
        layout.addWidget(self.session_details)
        
        return panel
        
    def apply_styles(self):
        """应用样式"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #cccccc;
                border-radius: 5px;
                margin-top: 1ex;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QPushButton {
                padding: 5px 10px;
                border: 1px solid #cccccc;
                border-radius: 3px;
                background-color: white;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
            QPushButton:pressed {
                background-color: #d0d0d0;
            }
            QTabWidget::pane {
                border: 1px solid #cccccc;
                border-radius: 3px;
            }
            QTabBar::tab {
                padding: 8px 12px;
                background-color: #e0e0e0;
                border: 1px solid #cccccc;
                border-bottom: none;
                border-top-left-radius: 3px;
                border-top-right-radius: 3px;
            }
            QTabBar::tab:selected {
                background-color: white;
                border-bottom: 1px solid white;
            }
        """)
        
    def connect_signals(self):
        """连接信号"""
        # 图像处理按钮
        self.load_btn.clicked.connect(self.load_image)
        
        # 获取图像处理按钮（跳过加载按钮）
        processing_buttons = self.image_toolbar_parent().children()[1:7]  # 调整索引根据实际情况
        processing_functions = [
            self.apply_edge_detection,
            self.apply_skin_detection,
            self.apply_muscle_analysis,
            self.apply_acupoint_detection,
            self.apply_pressure_analysis,
            self.apply_body_segmentation,
            self.apply_enhancement
        ]
        
        for btn, func in zip(processing_buttons, processing_functions):
            btn.clicked.connect(func)
            
        # 绘图工具
        for btn in self.draw_mode_group.buttons():
            btn.clicked.connect(lambda checked, b=btn: 
                               self.image_canvas.set_draw_mode(b.property("mode")))
                               
        self.brush_slider.valueChanged.connect(self.image_canvas.set_brush_size)
        self.clear_btn.clicked.connect(self.image_canvas.clear_paths)
        
        # 按摩控制
        self.param_panel.start_btn.clicked.connect(self.start_massage)
        self.param_panel.pause_btn.clicked.connect(self.pause_massage)
        self.param_panel.stop_btn.clicked.connect(self.stop_massage)
        self.param_panel.parametersChanged.connect(self.on_parameters_changed)
        
        # AI分析
        self.ai_train_btn.clicked.connect(self.start_ai_analysis)
        
        # 会话历史
        self.session_list.itemClicked.connect(self.show_session_details)
        self.save_history_btn.clicked.connect(self.save_session_history)
        self.load_history_btn.clicked.connect(self.load_session_history)
        self.clear_history_btn.clicked.connect(self.clear_session_history)
        
        # 定时器
        self.massage_timer.timeout.connect(self.update_massage)
        
        # 画布信号
        self.image_canvas.pathCompleted.connect(self.on_path_completed)
        
    def image_toolbar_parent(self):
        """获取图像工具栏的父部件"""
        return self.load_btn.parent()
        
    def load_image(self):
        """加载图像"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "打开图像", "", 
            "图像文件 (*.png *.jpg *.jpeg *.bmp *.tiff);;所有文件 (*)")
            
        if file_path:
            self.current_image = AdvancedImageProcessing.load_image(file_path)
            self.current_image_path = file_path
            self.image_canvas.set_image(self.current_image)
            self.statusBar().showMessage(f"已加载图像: {os.path.basename(file_path)}")
            
            # 开始新的会话
            self.session_manager.start_new_session(
                file_path, self.param_panel.get_parameters())
            
    def apply_edge_detection(self):
        """应用边缘检测"""
        if self.current_image is not None:
            processed = AdvancedImageProcessing.detect_edges_advanced(self.current_image, 'canny')
            self.image_canvas.set_image(processed)
            self.statusBar().showMessage("已应用边缘检测")
            
    def apply_skin_detection(self):
        """应用皮肤检测"""
        if self.current_image is not None:
            processed = AdvancedImageProcessing.detect_skin_advanced(self.current_image, 'hsv')
            self.image_canvas.set_image(processed)
            self.statusBar().showMessage("已应用皮肤检测")
            
    def apply_muscle_analysis(self):
        """应用肌肉分析"""
        if self.current_image is not None:
            processed = AdvancedImageProcessing.detect_muscle_tension(self.current_image)
            self.image_canvas.set_image(processed)
            self.statusBar().showMessage("已应用肌肉紧张度分析")
            
    def apply_acupoint_detection(self):
        """应用穴位检测"""
        if self.current_image is not None:
            processed = AdvancedImageProcessing.detect_acupoints(self.current_image)
            self.image_canvas.set_image(processed)
            self.statusBar().showMessage("已应用穴位检测（模拟）")
            
    def apply_pressure_analysis(self):
        """应用压力分析"""
        if self.current_image is not None and self.image_canvas.massage_paths:
            processed = AdvancedImageProcessing.analyze_pressure_points(
                self.current_image, self.image_canvas.massage_paths)
            self.image_canvas.set_image(processed)
            self.statusBar().showMessage("已应用压力分布分析")
            
    def apply_body_segmentation(self):
        """应用身体分割"""
        if self.current_image is not None:
            processed = AdvancedImageProcessing.segment_body_parts(self.current_image)
            self.image_canvas.set_image(processed)
            self.statusBar().showMessage("已应用身体部位分割")
            
    def apply_enhancement(self):
        """应用图像增强"""
        if self.current_image is not None:
            # 使用原始的实现
            from ImageProcessing import ImageProcessing
            processed = ImageProcessing.enhance_image(self.current_image)
            self.image_canvas.set_image(processed)
            self.statusBar().showMessage("已应用图像增强")
            
    def start_massage(self):
        """开始按摩"""
        if len(self.image_canvas.massage_paths) == 0:
            QMessageBox.warning(self, "警告", "请先绘制按摩路径!")
            return
            
        self.param_panel.start_btn.setEnabled(False)
        self.param_panel.pause_btn.setEnabled(True)
        self.param_panel.stop_btn.setEnabled(True)
        
        self.massage_time_elapsed = 0
        self.is_massage_running = True
        self.is_massage_paused = False
        self.massage_timer.start(1000)  # 每秒更新一次
        
        self.statusBar().showMessage("按摩进行中...")
        
    def pause_massage(self):
        """暂停/继续按摩"""
        if self.is_massage_paused:
            self.massage_timer.start(1000)
            self.param_panel.pause_btn.setText("暂停")
            self.statusBar().showMessage("按摩继续...")
        else:
            self.massage_timer.stop()
            self.param_panel.pause_btn.setText("继续")
            self.statusBar().showMessage("按摩已暂停")
            
        self.is_massage_paused = not self.is_massage_paused
        
    def stop_massage(self):
        """停止按摩"""
        self.massage_timer.stop()
        self.is_massage_running = False
        self.is_massage_paused = False
        
        self.param_panel.start_btn.setEnabled(True)
        self.param_panel.pause_btn.setEnabled(False)
        self.param_panel.stop_btn.setEnabled(False)
        self.param_panel.pause_btn.setText("暂停")
        
        # 结束会话
        effectiveness = np.random.uniform(0.7, 0.95)  # 模拟效果评分
        self.session_manager.end_session(effectiveness)
        
        self.statusBar().showMessage("按摩已停止")
        QMessageBox.information(self, "完成", f"按摩已完成! 效果评分: {effectiveness:.2f}")
        
    def update_massage(self):
        """更新按摩状态"""
        self.massage_time_elapsed += 1
        
        # 获取当前参数值
        params = self.param_panel.get_parameters()
        intensity = params["intensity"]
        frequency = params["frequency"]
        pressure = params["pressure"]
        
        # 更新可视化
        self.visualization.add_data(
            self.massage_time_elapsed, intensity, frequency, pressure)
        
        # 检查是否达到预定时间
        duration = params["duration"] * 60  # 转换为秒
        if self.massage_time_elapsed >= duration:
            self.stop_massage()
            
    def on_parameters_changed(self, params):
        """参数变化处理"""
        if self.is_massage_running and not self.is_massage_paused:
            self.statusBar().showMessage(
                f"参数已更新: {params['mode']}模式, 强度{params['intensity']}")
                
    def on_path_completed(self, path):
        """路径完成处理"""
        self.session_manager.add_path(path)
        self.statusBar().showMessage(f"已添加按摩路径，包含{len(path)}个点")
        
    def start_ai_analysis(self):
        """开始AI分析"""
        if self.current_image is None:
            QMessageBox.warning(self, "警告", "请先加载图像!")
            return
            
        # 模拟AI训练数据
        massage_data = {
            'image_path': self.current_image_path,
            'paths': self.image_canvas.massage_paths,
            'parameters': self.param_panel.get_parameters()
        }
        
        self.ai_trainer = MassageAITrainer(massage_data)
        self.ai_trainer.progress_updated.connect(self.update_ai_progress)
        self.ai_trainer.training_completed.connect(self.on_ai_training_completed)
        
        self.ai_train_btn.setEnabled(False)
        self.ai_progress.setVisible(True)
        self.ai_progress.setValue(0)
        
        self.ai_trainer.start()
        self.statusBar().showMessage("AI分析进行中...")
        
    def update_ai_progress(self, value):
        """更新AI分析进度"""
        self.ai_progress.setValue(value)
        
    def on_ai_training_completed(self, results):
        """AI分析完成"""
        self.ai_train_btn.setEnabled(True)
        self.ai_progress.setVisible(False)
        
        # 显示结果
        result_text = f"""AI分析完成!
        
优化建议:
- 推荐强度: {results['optimal_intensity']}
- 推荐频率: {results['optimal_frequency']} Hz
- 建议时长: {results['recommended_duration']} 分钟
- 预期效果: {results['effectiveness_score']:.1%}

具体建议:
"""
        for suggestion in results['suggestions']:
            result_text += f"• {suggestion}\n"
            
        self.ai_results.setText(result_text)
        self.statusBar().showMessage("AI分析完成")
        
    def show_session_details(self, item):
        """显示会话详情"""
        session_id = int(item.text().split(":")[0])
        session = next((s for s in self.session_manager.sessions if s['id'] == session_id), None)
        
        if session:
            details = f"""会话 #{session['id']}
开始时间: {session['start_time']}
持续时间: {session['duration']:.1f} 秒
按摩模式: {session['parameters']['mode']}
效果评分: {session['effectiveness']:.2f}

路径数量: {len(session['paths'])}
图像文件: {os.path.basename(session['image_path'])}
"""
            self.session_details.setText(details)
            
    def save_session_history(self):
        """保存会话历史"""
        filename, _ = QFileDialog.getSaveFileName(
            self, "保存会话历史", "", "JSON文件 (*.json)")
            
        if filename:
            if self.session_manager.save_sessions(filename):
                QMessageBox.information(self, "成功", "会话历史已保存!")
            else:
                QMessageBox.warning(self, "错误", "保存会话历史失败!")
                
    def load_session_history(self):
        """加载会话历史"""
        filename, _ = QFileDialog.getOpenFileName(
            self, "加载会话历史", "", "JSON文件 (*.json)")
            
        if filename:
            if self.session_manager.load_sessions(filename):
                self.update_session_list()
                QMessageBox.information(self, "成功", "会话历史已加载!")
            else:
                QMessageBox.warning(self, "错误", "加载会话历史失败!")
                
    def clear_session_history(self):
        """清空会话历史"""
        reply = QMessageBox.question(
            self, "确认", "确定要清空所有会话历史吗?",
            QMessageBox.Yes | QMessageBox.No)
            
        if reply == QMessageBox.Yes:
            self.session_manager.sessions = []
            self.update_session_list()
            
    def update_session_list(self):
        """更新会话列表"""
        self.session_list.clear()
        for session in self.session_manager.sessions:
            item = QListWidgetItem(
                f"{session['id']}: {session['start_time']} "
                f"(时长: {session['duration']:.1f}s)")
            self.session_list.addItem(item)
            
    def closeEvent(self, event):
        """关闭事件处理"""
        if self.is_massage_running:
            reply = QMessageBox.question(
                self, "确认退出", "按摩正在进行中，确定要退出吗?",
                QMessageBox.Yes | QMessageBox.No)
                
            if reply == QMessageBox.No:
                event.ignore()
                return
                
        if self.ai_trainer and self.ai_trainer.isRunning():
            self.ai_trainer.stop()
            self.ai_trainer.wait(2000)  # 等待2秒
            
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("高级智能视觉按摩系统")
    app.setApplicationVersion("2.0")
    
    # 设置字体
    font = QFont("Microsoft YaHei", 9)
    app.setFont(font)
    
    window = EnhancedMassageSystem()
    window.show()
    
    sys.exit(app.exec_())