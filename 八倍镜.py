import sys
import math
import numpy as np
import cv2
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QSlider, QLabel, QGroupBox,
                             QComboBox, QCheckBox, QSpinBox, QDoubleSpinBox, 
                             QTabWidget, QTextEdit, QFileDialog, QSplitter,
                             QProgressBar, QMessageBox, QToolBar, QAction, 
                             QDockWidget, QListWidget, QTreeWidget, QTreeWidgetItem)
from PyQt5.QtCore import Qt, QPoint, QRect, QTimer, pyqtSignal, QSize, QThread
from PyQt5.QtGui import (QPainter, QPen, QColor, QImage, QPixmap, QBrush, 
                         QConicalGradient, QFont, QIcon, QPolygon)


class VideoThread(QThread):
    """视频捕获线程"""
    frame_ready = pyqtSignal(np.ndarray)
    
    def __init__(self, source=0):
        super().__init__()
        self.source = source
        self.running = True
        self.cap = None
        
    def run(self):
        self.cap = cv2.VideoCapture(self.source)
        while self.running:
            ret, frame = self.cap.read()
            if ret:
                self.frame_ready.emit(frame)
            else:
                self.running = False
        if self.cap:
            self.cap.release()
            
    def stop(self):
        self.running = False
        self.wait()


class ImageProcessor:
    """图像处理类"""
    
    @staticmethod
    def apply_night_vision(image):
        """应用夜视效果"""
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        hsv[:, :, 1] = hsv[:, :, 1] * 0.3  # 降低饱和度
        night_vision = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
        # 添加绿色色调
        night_vision[:, :, 0] = night_vision[:, :, 0] * 0.3
        night_vision[:, :, 1] = night_vision[:, :, 1] * 1.5
        night_vision[:, :, 2] = night_vision[:, :, 2] * 0.3
        return np.clip(night_vision, 0, 255).astype(np.uint8)
    
    @staticmethod
    def apply_thermal_vision(image):
        """应用热成像效果"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        # 应用伪彩色映射
        thermal = cv2.applyColorMap(gray, cv2.COLORMAP_JET)
        return thermal
    
    @staticmethod
    def enhance_contrast(image, alpha=1.5, beta=0):
        """增强对比度"""
        return cv2.convertScaleAbs(image, alpha=alpha, beta=beta)
    
    @staticmethod
    def sharpen_image(image):
        """锐化图像"""
        kernel = np.array([[-1, -1, -1],
                           [-1, 9, -1],
                           [-1, -1, -1]])
        return cv2.filter2D(image, -1, kernel)
    
    @staticmethod
    def detect_edges(image, threshold1=100, threshold2=200):
        """边缘检测"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, threshold1, threshold2)
        return cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
    
    @staticmethod
    def stabilize_image(current_frame, previous_frame):
        """简单的图像稳定"""
        if previous_frame is None:
            return current_frame, np.zeros((2, 3), np.float32)
            
        # 计算光流
        prev_gray = cv2.cvtColor(previous_frame, cv2.COLOR_BGR2GRAY)
        curr_gray = cv2.cvtColor(current_frame, cv2.COLOR_BGR2GRAY)
        
        # 使用ORB特征检测和匹配
        orb = cv2.ORB_create()
        prev_kp, prev_des = orb.detectAndCompute(prev_gray, None)
        curr_kp, curr_des = orb.detectAndCompute(curr_gray, None)
        
        if prev_des is None or curr_des is None:
            return current_frame, np.zeros((2, 3), np.float32)
            
        # 使用BFMatcher进行特征匹配
        bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
        matches = bf.match(prev_des, curr_des)
        matches = sorted(matches, key=lambda x: x.distance)
        
        # 提取匹配点
        prev_pts = np.float32([prev_kp[m.queryIdx].pt for m in matches]).reshape(-1, 1, 2)
        curr_pts = np.float32([curr_kp[m.trainIdx].pt for m in matches]).reshape(-1, 1, 2)
        
        # 计算变换矩阵
        if len(prev_pts) > 4 and len(curr_pts) > 4:
            m, _ = cv2.estimateAffinePartial2D(prev_pts, curr_pts)
            if m is not None:
                # 应用变换
                rows, cols = current_frame.shape[:2]
                stabilized = cv2.warpAffine(current_frame, m, (cols, rows))
                return stabilized, m
                
        return current_frame, np.zeros((2, 3), np.float32)


class TargetTracker:
    """目标跟踪器"""
    
    def __init__(self):
        self.tracker = None
        self.bbox = None
        self.initialized = False
        
    def init(self, frame, bbox):
        """初始化跟踪器"""
        self.tracker = cv2.TrackerCSRT_create()
        self.bbox = bbox
        success = self.tracker.init(frame, bbox)
        self.initialized = success
        return success
        
    def update(self, frame):
        """更新跟踪器"""
        if self.initialized and self.tracker is not None:
            success, bbox = self.tracker.update(frame)
            if success:
                self.bbox = bbox
            return success, bbox
        return False, None


class SightingSystem(QWidget):
    """瞄准系统主窗口"""
    
    # 信号定义
    zoomChanged = pyqtSignal(float)
    frameProcessed = pyqtSignal(np.ndarray)
    targetLocked = pyqtSignal(QRect)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        # 初始化变量
        self.zoom_factor = 1.0
        self.max_zoom = 16.0
        self.crosshair_type = "advanced_cross"
        self.crosshair_color = Qt.green
        self.ruler_visible = True
        self.night_vision = False
        self.thermal_vision = False
        self.edge_detection = False
        self.image_stabilization = False
        self.contrast_enhancement = False
        self.sharpen_image = False
        self.original_frame = None
        self.processed_frame = None
        self.display_frame = None
        self.center_point = QPoint(0, 0)
        self.measurement_points = []
        self.measuring = False
        self.recording = False
        self.video_writer = None
        self.video_thread = None
        self.previous_frame = None
        self.transform_matrix = None
        self.target_tracker = TargetTracker()
        self.tracking = False
        self.measurement_history = []
        
        # 设置UI
        self.init_ui()
        
        # 启动视频捕获
        self.start_video_capture(0)
        
    def init_ui(self):
        """初始化UI"""
        self.setMinimumSize(800, 600)
        self.setMouseTracking(True)
        
    def start_video_capture(self, source):
        """启动视频捕获"""
        if self.video_thread:
            self.video_thread.stop()
            
        self.video_thread = VideoThread(source)
        self.video_thread.frame_ready.connect(self.process_frame)
        self.video_thread.start()
        
    def process_frame(self, frame):
        """处理视频帧"""
        self.original_frame = frame
        self.processed_frame = frame.copy()
        
        # 应用图像稳定
        if self.image_stabilization:
            self.processed_frame, self.transform_matrix = ImageProcessor.stabilize_image(
                self.processed_frame, self.previous_frame
            )
        
        # 应用图像增强
        if self.contrast_enhancement:
            self.processed_frame = ImageProcessor.enhance_contrast(self.processed_frame)
            
        if self.sharpen_image:
            self.processed_frame = ImageProcessor.sharpen_image(self.processed_frame)
            
        if self.night_vision:
            self.processed_frame = ImageProcessor.apply_night_vision(self.processed_frame)
            
        if self.thermal_vision:
            self.processed_frame = ImageProcessor.apply_thermal_vision(self.processed_frame)
            
        if self.edge_detection:
            self.processed_frame = ImageProcessor.detect_edges(self.processed_frame)
        
        # 更新目标跟踪
        if self.tracking:
            success, bbox = self.target_tracker.update(self.processed_frame)
            if success:
                # 发射目标锁定信号
                x, y, w, h = [int(v) for v in bbox]
                self.targetLocked.emit(QRect(x, y, w, h))
        
        # 保存当前帧作为下一帧的上一帧
        self.previous_frame = self.processed_frame.copy()
        
        # 更新显示
        self.update_display_frame()
        self.update()
        
        # 录制视频
        if self.recording and self.video_writer:
            self.video_writer.write(self.processed_frame)
            
        # 发射帧处理完成信号
        self.frameProcessed.emit(self.processed_frame)
        
    def update_display_frame(self):
        """更新显示帧"""
        if self.processed_frame is None:
            return
            
        # 计算缩放区域
        height, width = self.processed_frame.shape[:2]
        zoomed_width = int(width / self.zoom_factor)
        zoomed_height = int(height / self.zoom_factor)
        
        # 计算源矩形区域（以中心点为中心）
        source_x = max(0, self.center_point.x() - zoomed_width // 2)
        source_y = max(0, self.center_point.y() - zoomed_height // 2)
        source_x = min(source_x, width - zoomed_width)
        source_y = min(source_y, height - zoomed_height)
        
        # 提取缩放区域
        zoomed_frame = self.processed_frame[source_y:source_y+zoomed_height, 
                                           source_x:source_x+zoomed_width]
        
        # 调整到显示大小
        if zoomed_frame.size > 0:
            self.display_frame = cv2.resize(zoomed_frame, 
                                           (self.width(), self.height()),
                                           interpolation=cv2.INTER_LINEAR)
        else:
            self.display_frame = self.processed_frame
            
    def set_zoom(self, factor):
        """设置缩放因子"""
        self.zoom_factor = max(1.0, min(factor, self.max_zoom))
        self.update_display_frame()
        self.update()
        self.zoomChanged.emit(self.zoom_factor)
        
    def set_crosshair_type(self, ctype):
        """设置准星类型"""
        self.crosshair_type = ctype
        self.update()
        
    def start_recording(self, filename):
        """开始录制视频"""
        if self.processed_frame is None:
            return False
            
        height, width = self.processed_frame.shape[:2]
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        self.video_writer = cv2.VideoWriter(filename, fourcc, 20.0, (width, height))
        self.recording = True
        return True
        
    def stop_recording(self):
        """停止录制视频"""
        if self.video_writer:
            self.video_writer.release()
            self.video_writer = None
        self.recording = False
        
    def start_tracking(self, bbox):
        """开始目标跟踪"""
        if self.processed_frame is not None:
            success = self.target_tracker.init(self.processed_frame, bbox)
            self.tracking = success
            return success
        return False
        
    def stop_tracking(self):
        """停止目标跟踪"""
        self.tracking = False
        self.target_tracker = TargetTracker()
        
    def start_measurement(self):
        """开始测量"""
        self.measuring = True
        self.measurement_points = []
        
    def clear_measurement(self):
        """清除测量"""
        self.measurement_points = []
        self.measuring = False
        self.update()
        
    def save_measurement(self, note=""):
        """保存测量结果"""
        if len(self.measurement_points) < 2:
            return
            
        measurement = {
            "points": self.measurement_points.copy(),
            "distances": self.calculate_distances(),
            "time": datetime.now(),
            "note": note
        }
        self.measurement_history.append(measurement)
        
    def calculate_distances(self):
        """计算测量点之间的距离"""
        distances = []
        for i in range(len(self.measurement_points) - 1):
            p1 = self.measurement_points[i]
            p2 = self.measurement_points[i + 1]
            dx = p2.x() - p1.x()
            dy = p2.y() - p1.y()
            distance = math.sqrt(dx*dx + dy*dy)
            distances.append(distance)
        return distances
        
    def paintEvent(self, event):
        """绘制事件"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 绘制视频帧
        if self.display_frame is not None:
            # 转换OpenCV图像到QImage
            rgb_image = cv2.cvtColor(self.display_frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_image.shape
            bytes_per_line = ch * w
            q_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
            painter.drawImage(0, 0, q_image)
            
        # 绘制测量标尺
        if self.ruler_visible:
            self.draw_ruler(painter)
            
        # 绘制准星
        self.draw_crosshair(painter)
        
        # 绘制测量线和点
        if self.measurement_points:
            self.draw_measurements(painter)
            
        # 绘制目标跟踪框
        if self.tracking and self.target_tracker.bbox:
            self.draw_tracking_box(painter)
            
    def draw_ruler(self, painter):
        """绘制标尺"""
        width, height = self.width(), self.height()
        pen = QPen(QColor(255, 255, 255, 150), 1)
        painter.setPen(pen)
        
        # 水平标尺
        for i in range(0, width, 20):
            length = 10 if i % 100 != 0 else 20
            painter.drawLine(i, 0, i, length)
            painter.drawLine(i, height, i, height - length)
            
            if i % 100 == 0:
                painter.drawText(i - 10, 35, f"{i}")
                painter.drawText(i - 10, height - 40, f"{i}")
        
        # 垂直标尺
        for i in range(0, height, 20):
            length = 10 if i % 100 != 0 else 20
            painter.drawLine(0, i, length, i)
            painter.drawLine(width, i, width - length, i)
            
            if i % 100 == 0:
                painter.drawText(5, i + 5, f"{i}")
                painter.drawText(width - 30, i + 5, f"{i}")
                
    def draw_crosshair(self, painter):
        """绘制准星"""
        center = QPoint(self.width() // 2, self.height() // 2)
        pen = QPen(self.crosshair_color, 2)
        painter.setPen(pen)
        
        if self.crosshair_type == "simple_cross":
            # 简单十字准星
            size = min(self.width(), self.height()) // 4
            painter.drawLine(center.x() - size, center.y(), center.x() + size, center.y())
            painter.drawLine(center.x(), center.y() - size, center.x(), center.y() + size)
            painter.drawEllipse(center, 5, 5)
            
        elif self.crosshair_type == "advanced_cross":
            # 高级十字准星
            size = min(self.width(), self.height()) // 3
            # 绘制外圆
            painter.drawEllipse(center, size, size)
            # 绘制十字线
            painter.drawLine(center.x() - size, center.y(), center.x() + size, center.y())
            painter.drawLine(center.x(), center.y() - size, center.x(), center.y() + size)
            # 绘制内圆
            inner_size = size // 2
            painter.drawEllipse(center, inner_size, inner_size)
            # 绘制刻度
            for i in range(0, 360, 30):
                rad = math.radians(i)
                x1 = center.x() + int(size * math.cos(rad))
                y1 = center.y() + int(size * math.sin(rad))
                x2 = center.x() + int((size - 10) * math.cos(rad))
                y2 = center.y() + int((size - 10) * math.sin(rad))
                painter.drawLine(x1, y1, x2, y2)
            # 绘制中心点
            painter.drawEllipse(center, 3, 3)
            
        elif self.crosshair_type == "military":
            # 军用风格准星
            size = min(self.width(), self.height()) // 4
            # 绘制V型标记
            v_size = size // 2
            painter.drawLine(center.x() - v_size, center.y() - v_size, center.x(), center.y())
            painter.drawLine(center.x() + v_size, center.y() - v_size, center.x(), center.y())
            # 绘制水平线
            painter.drawLine(center.x() - size, center.y(), center.x() + size, center.y())
            # 绘制垂直线下半部分
            painter.drawLine(center.x(), center.y(), center.x(), center.y() + size)
            # 绘制圆圈
            painter.drawEllipse(center, size // 3, size // 3)
            
        elif self.crosshair_type == "sniper":
            # 狙击手风格准星
            size = min(self.width(), self.height()) // 3
            # 绘制细十字线
            pen.setWidth(1)
            painter.setPen(pen)
            painter.drawLine(center.x() - size, center.y(), center.x() + size, center.y())
            painter.drawLine(center.x(), center.y() - size, center.x(), center.y() + size)
            # 绘制同心圆
            for r in range(size, 0, -size // 4):
                painter.drawEllipse(center, r, r)
            # 绘制中心点
            painter.drawEllipse(center, 2, 2)
            
    def draw_measurements(self, painter):
        """绘制测量线和点"""
        pen = QPen(Qt.yellow, 2)
        painter.setPen(pen)
        
        # 绘制点
        for point in self.measurement_points:
            painter.drawEllipse(point, 4, 4)
            
        # 绘制线
        if len(self.measurement_points) > 1:
            for i in range(len(self.measurement_points) - 1):
                p1 = self.measurement_points[i]
                p2 = self.measurement_points[i + 1]
                painter.drawLine(p1, p2)
                
                # 显示距离
                dx = p2.x() - p1.x()
                dy = p2.y() - p1.y()
                distance = math.sqrt(dx*dx + dy*dy)
                mid_point = QPoint((p1.x() + p2.x()) // 2, (p1.y() + p2.y()) // 2)
                
                # 绘制距离标签
                painter.drawText(mid_point, f"{distance:.1f}px")
                
    def draw_tracking_box(self, painter):
        """绘制目标跟踪框"""
        if not self.target_tracker.bbox:
            return
            
        # 计算缩放后的bbox位置
        x, y, w, h = self.target_tracker.bbox
        zoomed_x = (x - self.center_point.x() + self.processed_frame.shape[1] // 2) / self.zoom_factor
        zoomed_y = (y - self.center_point.y() + self.processed_frame.shape[0] // 2) / self.zoom_factor
        zoomed_w = w / self.zoom_factor
        zoomed_h = h / self.zoom_factor
        
        # 绘制跟踪框
        pen = QPen(Qt.red, 2)
        painter.setPen(pen)
        painter.drawRect(int(zoomed_x), int(zoomed_y), int(zoomed_w), int(zoomed_h))
        
        # 绘制跟踪状态
        font = QFont("Arial", 12)
        painter.setFont(font)
        painter.drawText(10, 30, "跟踪中")
        
    def mousePressEvent(self, event):
        """鼠标点击事件"""
        if event.button() == Qt.LeftButton:
            if self.measuring:
                self.measurement_points.append(event.pos())
                self.update()
            elif self.tracking:
                # 设置跟踪区域
                size = 50  # 跟踪区域大小
                x = event.pos().x() - size // 2
                y = event.pos().y() - size // 2
                # 转换为原始图像坐标
                orig_x = int((x * self.zoom_factor) + self.center_point.x() - self.processed_frame.shape[1] // 2)
                orig_y = int((y * self.zoom_factor) + self.center_point.y() - self.processed_frame.shape[0] // 2)
                bbox = (orig_x, orig_y, size, size)
                self.start_tracking(bbox)
                
    def mouseMoveEvent(self, event):
        """鼠标移动事件"""
        if self.measuring and self.measurement_points:
            self.measurement_points[-1] = event.pos()
            self.update()
            
    def wheelEvent(self, event):
        """鼠标滚轮事件 - 缩放控制"""
        zoom_delta = 0.5 if event.angleDelta().y() > 0 else -0.5
        new_zoom = max(1.0, min(self.zoom_factor + zoom_delta, self.max_zoom))
        self.set_zoom(new_zoom)
        
    def resizeEvent(self, event):
        """窗口大小改变事件"""
        self.update_display_frame()
        super().resizeEvent(event)
        
    def closeEvent(self, event):
        """关闭事件"""
        if self.video_thread:
            self.video_thread.stop()
        if self.recording:
            self.stop_recording()
        super().closeEvent(event)


class SightingControlPanel(QWidget):
    """控制面板"""
    
    def __init__(self, sighting_system, parent=None):
        super().__init__(parent)
        self.sighting_system = sighting_system
        self.init_ui()
        
    def init_ui(self):
        """初始化UI"""
        main_layout = QVBoxLayout()
        
        # 创建标签页
        tab_widget = QTabWidget()
        
        # 基本控制标签页
        basic_tab = QWidget()
        basic_layout = QVBoxLayout()
        basic_tab.setLayout(basic_layout)
        
        # 缩放控制
        zoom_group = QGroupBox("缩放控制")
        zoom_layout = QVBoxLayout()
        
        self.zoom_slider = QSlider(Qt.Horizontal)
        self.zoom_slider.setMinimum(10)  # 1.0x
        self.zoom_slider.setMaximum(160)  # 16.0x
        self.zoom_slider.setValue(10)
        self.zoom_slider.valueChanged.connect(self.on_zoom_changed)
        zoom_layout.addWidget(self.zoom_slider)
        
        self.zoom_label = QLabel("1.0x")
        zoom_layout.addWidget(self.zoom_label)
        
        zoom_group.setLayout(zoom_layout)
        basic_layout.addWidget(zoom_group)
        
        # 准星控制
        crosshair_group = QGroupBox("准星设置")
        crosshair_layout = QVBoxLayout()
        
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("类型:"))
        self.crosshair_combo = QComboBox()
        self.crosshair_combo.addItems(["简单十字", "高级十字", "军用风格", "狙击风格"])
        self.crosshair_combo.currentTextChanged.connect(self.on_crosshair_changed)
        type_layout.addWidget(self.crosshair_combo)
        crosshair_layout.addLayout(type_layout)
        
        color_layout = QHBoxLayout()
        color_layout.addWidget(QLabel("颜色:"))
        self.color_combo = QComboBox()
        self.color_combo.addItems(["绿色", "红色", "蓝色", "黄色", "白色"])
        self.color_combo.currentTextChanged.connect(self.on_color_changed)
        color_layout.addWidget(self.color_combo)
        crosshair_layout.addLayout(color_layout)
        
        crosshair_group.setLayout(crosshair_layout)
        basic_layout.addWidget(crosshair_group)
        
        # 视频源控制
        source_group = QGroupBox("视频源")
        source_layout = QVBoxLayout()
        
        source_btn_layout = QHBoxLayout()
        self.webcam_btn = QPushButton("摄像头")
        self.webcam_btn.clicked.connect(lambda: self.on_source_changed(0))
        source_btn_layout.addWidget(self.webcam_btn)
        
        self.file_btn = QPushButton("文件")
        self.file_btn.clicked.connect(self.on_file_source)
        source_btn_layout.addWidget(self.file_btn)
        
        source_layout.addLayout(source_btn_layout)
        source_group.setLayout(source_layout)
        basic_layout.addWidget(source_group)
        
        basic_layout.addStretch()
        tab_widget.addTab(basic_tab, "基本控制")
        
        # 图像处理标签页
        processing_tab = QWidget()
        processing_layout = QVBoxLayout()
        processing_tab.setLayout(processing_layout)
        
        # 图像增强
        enhance_group = QGroupBox("图像增强")
        enhance_layout = QVBoxLayout()
        
        self.night_vision_cb = QCheckBox("夜视模式")
        self.night_vision_cb.stateChanged.connect(self.on_night_vision_changed)
        enhance_layout.addWidget(self.night_vision_cb)
        
        self.thermal_vision_cb = QCheckBox("热成像模式")
        self.thermal_vision_cb.stateChanged.connect(self.on_thermal_vision_changed)
        enhance_layout.addWidget(self.thermal_vision_cb)
        
        self.contrast_cb = QCheckBox("对比度增强")
        self.contrast_cb.stateChanged.connect(self.on_contrast_changed)
        enhance_layout.addWidget(self.contrast_cb)
        
        self.sharpen_cb = QCheckBox("锐化图像")
        self.sharpen_cb.stateChanged.connect(self.on_sharpen_changed)
        enhance_layout.addWidget(self.sharpen_cb)
        
        self.edge_detection_cb = QCheckBox("边缘检测")
        self.edge_detection_cb.stateChanged.connect(self.on_edge_detection_changed)
        enhance_layout.addWidget(self.edge_detection_cb)
        
        self.stabilization_cb = QCheckBox("图像稳定")
        self.stabilization_cb.stateChanged.connect(self.on_stabilization_changed)
        enhance_layout.addWidget(self.stabilization_cb)
        
        enhance_group.setLayout(enhance_layout)
        processing_layout.addWidget(enhance_group)
        
        processing_layout.addStretch()
        tab_widget.addTab(processing_tab, "图像处理")
        
        # 测量工具标签页
        measure_tab = QWidget()
        measure_layout = QVBoxLayout()
        measure_tab.setLayout(measure_layout)
        
        # 测量控制
        measure_control_group = QGroupBox("测量控制")
        measure_control_layout = QVBoxLayout()
        
        self.measure_btn = QPushButton("开始测量")
        self.measure_btn.setCheckable(True)
        self.measure_btn.clicked.connect(self.on_measure_changed)
        measure_control_layout.addWidget(self.measure_btn)
        
        self.clear_measure_btn = QPushButton("清除测量")
        self.clear_measure_btn.clicked.connect(self.on_clear_measurement)
        measure_control_layout.addWidget(self.clear_measure_btn)
        
        self.save_measure_btn = QPushButton("保存测量")
        self.save_measure_btn.clicked.connect(self.on_save_measurement)
        measure_control_layout.addWidget(self.save_measure_btn)
        
        measure_control_group.setLayout(measure_control_layout)
        measure_layout.addWidget(measure_control_group)
        
        # 测量历史
        history_group = QGroupBox("测量历史")
        history_layout = QVBoxLayout()
        
        self.history_list = QListWidget()
        history_layout.addWidget(self.history_list)
        
        history_group.setLayout(history_layout)
        measure_layout.addWidget(history_group)
        
        tab_widget.addTab(measure_tab, "测量工具")
        
        # 目标跟踪标签页
        tracking_tab = QWidget()
        tracking_layout = QVBoxLayout()
        tracking_tab.setLayout(tracking_layout)
        
        # 跟踪控制
        track_control_group = QGroupBox("目标跟踪")
        track_control_layout = QVBoxLayout()
        
        self.track_btn = QPushButton("开始跟踪")
        self.track_btn.setCheckable(True)
        self.track_btn.clicked.connect(self.on_tracking_changed)
        track_control_layout.addWidget(self.track_btn)
        
        self.stop_track_btn = QPushButton("停止跟踪")
        self.stop_track_btn.clicked.connect(self.on_stop_tracking)
        track_control_layout.addWidget(self.stop_track_btn)
        
        track_control_group.setLayout(track_control_layout)
        tracking_layout.addWidget(track_control_group)
        
        tracking_layout.addStretch()
        tab_widget.addTab(tracking_tab, "目标跟踪")
        
        main_layout.addWidget(tab_widget)
        self.setLayout(main_layout)
        
        # 连接信号
        self.sighting_system.zoomChanged.connect(self.update_zoom_label)
        self.sighting_system.targetLocked.connect(self.on_target_locked)
        
    def on_zoom_changed(self, value):
        zoom_factor = value / 10.0
        self.sighting_system.set_zoom(zoom_factor)
        
    def update_zoom_label(self, factor):
        self.zoom_label.setText(f"{factor:.1f}x")
        self.zoom_slider.setValue(int(factor * 10))
        
    def on_crosshair_changed(self, text):
        if text == "简单十字":
            self.sighting_system.set_crosshair_type("simple_cross")
        elif text == "高级十字":
            self.sighting_system.set_crosshair_type("advanced_cross")
        elif text == "军用风格":
            self.sighting_system.set_crosshair_type("military")
        elif text == "狙击风格":
            self.sighting_system.set_crosshair_type("sniper")
            
    def on_color_changed(self, text):
        if text == "绿色":
            self.sighting_system.crosshair_color = Qt.green
        elif text == "红色":
            self.sighting_system.crosshair_color = Qt.red
        elif text == "蓝色":
            self.sighting_system.crosshair_color = Qt.blue
        elif text == "黄色":
            self.sighting_system.crosshair_color = Qt.yellow
        elif text == "白色":
            self.sighting_system.crosshair_color = Qt.white
        self.sighting_system.update()
        
    def on_source_changed(self, source):
        self.sighting_system.start_video_capture(source)
        
    def on_file_source(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, "选择视频文件", "", "视频文件 (*.mp4 *.avi *.mov *.mkv)"
        )
        if filename:
            self.sighting_system.start_video_capture(filename)
            
    def on_night_vision_changed(self, state):
        self.sighting_system.night_vision = state == Qt.Checked
        if state == Qt.Checked:
            self.thermal_vision_cb.setChecked(False)
            
    def on_thermal_vision_changed(self, state):
        self.sighting_system.thermal_vision = state == Qt.Checked
        if state == Qt.Checked:
            self.night_vision_cb.setChecked(False)
            
    def on_contrast_changed(self, state):
        self.sighting_system.contrast_enhancement = state == Qt.Checked
        
    def on_sharpen_changed(self, state):
        self.sighting_system.sharpen_image = state == Qt.Checked
        
    def on_edge_detection_changed(self, state):
        self.sighting_system.edge_detection = state == Qt.Checked
        
    def on_stabilization_changed(self, state):
        self.sighting_system.image_stabilization = state == Qt.Checked
        
    def on_measure_changed(self, checked):
        if checked:
            self.sighting_system.start_measurement()
            self.measure_btn.setText("测量中")
        else:
            self.sighting_system.clear_measurement()
            self.measure_btn.setText("开始测量")
            
    def on_clear_measurement(self):
        self.measure_btn.setChecked(False)
        self.sighting_system.clear_measurement()
        self.measure_btn.setText("开始测量")
        
    def on_save_measurement(self):
        if not self.sighting_system.measurement_points:
            QMessageBox.warning(self, "警告", "没有测量数据可保存")
            return
            
        note, ok = QInputDialog.getText(self, "保存测量", "输入备注:")
        if ok:
            self.sighting_system.save_measurement(note)
            self.update_measurement_history()
            
    def update_measurement_history(self):
        self.history_list.clear()
        for i, measurement in enumerate(self.sighting_system.measurement_history):
            time_str = measurement["time"].strftime("%H:%M:%S")
            distances = ", ".join([f"{d:.1f}px" for d in measurement["distances"]])
            item_text = f"{i+1}. {time_str} - {distances}"
            if measurement["note"]:
                item_text += f" - {measurement['note']}"
            self.history_list.addItem(item_text)
            
    def on_tracking_changed(self, checked):
        if checked:
            self.track_btn.setText("跟踪中")
            # 跟踪将在下次鼠标点击时开始
        else:
            self.sighting_system.stop_tracking()
            self.track_btn.setText("开始跟踪")
            
    def on_stop_tracking(self):
        self.track_btn.setChecked(False)
        self.sighting_system.stop_tracking()
        self.track_btn.setText("开始跟踪")
        
    def on_target_locked(self, rect):
        # 目标锁定时的处理
        pass


class SightingSystemMainWindow(QMainWindow):
    """主窗口"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("高级瞄准镜系统")
        self.setGeometry(100, 100, 1200, 800)
        
        # 创建中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        main_layout = QHBoxLayout()
        central_widget.setLayout(main_layout)
        
        # 创建瞄准系统
        self.sighting_system = SightingSystem()
        
        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self.sighting_system)
        
        # 创建控制面板
        self.control_panel = SightingControlPanel(self.sighting_system)
        splitter.addWidget(self.control_panel)
        
        # 设置分割比例
        splitter.setSizes([800, 400])
        
        main_layout.addWidget(splitter)
        
        # 创建菜单栏
        self.create_menu()
        
        # 创建状态栏
        self.statusBar().showMessage("就绪")
        
        # 连接信号
        self.sighting_system.zoomChanged.connect(self.on_zoom_changed)
        
    def create_menu(self):
        """创建菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu("文件")
        
        record_action = QAction("开始录制", self)
        record_action.triggered.connect(self.on_record)
        file_menu.addAction(record_action)
        
        stop_record_action = QAction("停止录制", self)
        stop_record_action.triggered.connect(self.on_stop_record)
        file_menu.addAction(stop_record_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("退出", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 视图菜单
        view_menu = menubar.addMenu("视图")
        
        ruler_action = QAction("显示标尺", self)
        ruler_action.setCheckable(True)
        ruler_action.setChecked(True)
        ruler_action.triggered.connect(self.on_toggle_ruler)
        view_menu.addAction(ruler_action)
        
        # 工具菜单
        tools_menu = menubar.addMenu("工具")
        
        calibrate_action = QAction("校准", self)
        calibrate_action.triggered.connect(self.on_calibrate)
        tools_menu.addAction(calibrate_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu("帮助")
        
        about_action = QAction("关于", self)
        about_action.triggered.connect(self.on_about)
        help_menu.addAction(about_action)
        
    def on_zoom_changed(self, factor):
        self.statusBar().showMessage(f"当前放大倍数: {factor:.1f}x")
        
    def on_record(self):
        filename, _ = QFileDialog.getSaveFileName(
            self, "保存视频", "", "视频文件 (*.avi)"
        )
        if filename:
            success = self.sighting_system.start_recording(filename)
            if success:
                self.statusBar().showMessage(f"录制中: {filename}")
            else:
                self.statusBar().showMessage("录制失败")
                
    def on_stop_record(self):
        self.sighting_system.stop_recording()
        self.statusBar().showMessage("录制已停止")
        
    def on_toggle_ruler(self, visible):
        self.sighting_system.ruler_visible = visible
        self.sighting_system.update()
        
    def on_calibrate(self):
        QMessageBox.information(self, "校准", "请按照说明进行系统校准...")
        
    def on_about(self):
        QMessageBox.about(self, "关于", "高级瞄准镜系统\n版本 2.0\n基于PyQt和OpenCV开发")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SightingSystemMainWindow()
    window.show()
    sys.exit(app.exec_())