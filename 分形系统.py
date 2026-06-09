import sys
import math
import numpy as np
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QSlider, 
                             QComboBox, QSpinBox, QDoubleSpinBox, QCheckBox,
                             QGroupBox, QTabWidget, QFileDialog, QMessageBox,
                             QSplitter, QFrame, QProgressBar)
from PyQt5.QtCore import QRect, Qt, QTimer, QThread, pyqtSignal
from PyQt5.QtGui import QPainter, QColor, QPen, QImage, QPixmap, QPalette
import matplotlib
matplotlib.rc("font", family='Microsoft YaHei')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.colors import LinearSegmentedColormap
import time
import json
import os


class FractalWorker(QThread):
    """后台计算分形的线程"""
    progress_updated = pyqtSignal(int)
    fractal_completed = pyqtSignal(np.ndarray)
    
    def __init__(self, fractal_type, width, height, params):
        super().__init__()
        self.fractal_type = fractal_type
        self.width = width
        self.height = height
        self.params = params
        self.is_running = True
        
    def run(self):
        """运行分形计算"""
        if self.fractal_type == "mandelbrot":
            fractal_data = self.calculate_mandelbrot()
        elif self.fractal_type == "julia":
            fractal_data = self.calculate_julia()
        elif self.fractal_type == "newton":
            fractal_data = self.calculate_newton()
        elif self.fractal_type == "sierpinski":
            fractal_data = self.calculate_sierpinski()
        elif self.fractal_type == "koch":
            fractal_data = self.calculate_koch()
        else:
            fractal_data = np.zeros((self.height, self.width))
            
        if self.is_running:
            self.fractal_completed.emit(fractal_data)
            
    def stop(self):
        """停止计算"""
        self.is_running = False
        
    def calculate_mandelbrot(self):
        """计算曼德勃罗集"""
        max_iter = self.params.get('max_iter', 100)
        escape_radius = self.params.get('escape_radius', 2.0)
        x_min, x_max = self.params.get('x_range', (-2.0, 1.0))
        y_min, y_max = self.params.get('y_range', (-1.5, 1.5))
        
        fractal = np.zeros((self.height, self.width))
        
        for y in range(self.height):
            if not self.is_running:
                break
                
            # 更新进度
            self.progress_updated.emit(int(100 * y / self.height))
            
            for x in range(self.width):
                zx, zy = 0, 0
                cx = x_min + (x / self.width) * (x_max - x_min)
                cy = y_min + (y / self.height) * (y_max - y_min)
                
                iteration = 0
                while zx*zx + zy*zy < escape_radius*escape_radius and iteration < max_iter:
                    zx, zy = zx*zx - zy*zy + cx, 2*zx*zy + cy
                    iteration += 1
                
                fractal[y, x] = iteration
        
        return fractal
    
    def calculate_julia(self):
        """计算朱利亚集"""
        max_iter = self.params.get('max_iter', 100)
        escape_radius = self.params.get('escape_radius', 2.0)
        cx, cy = self.params.get('c', (-0.7, 0.27))
        x_min, x_max = self.params.get('x_range', (-1.5, 1.5))
        y_min, y_max = self.params.get('y_range', (-1.5, 1.5))
        
        fractal = np.zeros((self.height, self.width))
        
        for y in range(self.height):
            if not self.is_running:
                break
                
            # 更新进度
            self.progress_updated.emit(int(100 * y / self.height))
            
            for x in range(self.width):
                zx = x_min + (x / self.width) * (x_max - x_min)
                zy = y_min + (y / self.height) * (y_max - y_min)
                
                iteration = 0
                while zx*zx + zy*zy < escape_radius*escape_radius and iteration < max_iter:
                    zx, zy = zx*zx - zy*zy + cx, 2*zx*zy + cy
                    iteration += 1
                
                fractal[y, x] = iteration
        
        return fractal
    
    def calculate_newton(self):
        """计算牛顿分形"""
        max_iter = self.params.get('max_iter', 100)
        tolerance = self.params.get('tolerance', 1e-6)
        x_min, x_max = self.params.get('x_range', (-2.0, 2.0))
        y_min, y_max = self.params.get('y_range', (-2.0, 2.0))
        
        fractal = np.zeros((self.height, self.width))
        
        # 定义多项式和其导数: z^3 - 1 = 0
        def f(z):
            return z**3 - 1
        
        def df(z):
            return 3*z**2
        
        roots = [1, -0.5 + 0.8660254j, -0.5 - 0.8660254j]
        
        for y in range(self.height):
            if not self.is_running:
                break
                
            # 更新进度
            self.progress_updated.emit(int(100 * y / self.height))
            
            for x in range(self.width):
                z = complex(
                    x_min + (x / self.width) * (x_max - x_min),
                    y_min + (y / self.height) * (y_max - y_min)
                )
                
                iteration = 0
                while iteration < max_iter:
                    if abs(df(z)) < 1e-10:  # 避免除以零
                        break
                    
                    z_new = z - f(z) / df(z)
                    
                    if abs(z_new - z) < tolerance:
                        # 找到最近的根
                        distances = [abs(z_new - r) for r in roots]
                        closest_root = np.argmin(distances)
                        fractal[y, x] = closest_root + iteration / max_iter
                        break
                    
                    z = z_new
                    iteration += 1
                else:
                    fractal[y, x] = max_iter
        
        return fractal
    
    def calculate_sierpinski(self):
        """计算谢尔宾斯基三角形"""
        fractal = np.ones((self.height, self.width))
        max_depth = self.params.get('max_depth', 6)
        
        # 递归绘制谢尔宾斯基三角形
        def draw_triangle(x, y, size, depth):
            if depth == 0:
                # 填充三角形
                for i in range(int(size)):
                    for j in range(i+1):
                        px = int(x - i/2 + j)
                        py = int(y + i)
                        if 0 <= px < self.width and 0 <= py < self.height:
                            fractal[py, px] = 0
                return
            
            new_size = size / 2
            draw_triangle(x, y, new_size, depth-1)  # 上三角形
            draw_triangle(x - new_size/2, y + new_size, new_size, depth-1)  # 左下三角形
            draw_triangle(x + new_size/2, y + new_size, new_size, depth-1)  # 右下三角形
        
        # 从顶部中心开始
        start_x = self.width / 2
        start_y = 0
        triangle_size = min(self.width, self.height) * 0.9
        
        draw_triangle(start_x, start_y, triangle_size, max_depth)
        
        self.progress_updated.emit(100)
        return fractal
    
    def calculate_koch(self):
        """计算科赫雪花"""
        fractal = np.ones((self.height, self.width))
        
        # 绘制科赫曲线的函数
        def koch_curve(x1, y1, x2, y2, depth):
            if depth == 0:
                # 绘制直线
                self.draw_line(fractal, x1, y1, x2, y2)
                return
            
            # 计算科赫曲线的四个点
            dx = x2 - x1
            dy = y2 - y1
            
            # 三个等分点
            x3 = x1 + dx / 3
            y3 = y1 + dy / 3
            x4 = x2 - dx / 3
            y4 = y2 - dy / 3
            
            # 计算凸起的点
            angle = math.atan2(dy, dx)
            length = math.sqrt(dx*dx + dy*dy) / 3
            x5 = x3 + math.cos(angle - math.pi/3) * length
            y5 = y3 + math.sin(angle - math.pi/3) * length
            
            # 递归绘制四个线段
            koch_curve(x1, y1, x3, y3, depth-1)
            koch_curve(x3, y3, x5, y5, depth-1)
            koch_curve(x5, y5, x4, y4, depth-1)
            koch_curve(x4, y4, x2, y2, depth-1)
        
        # 绘制科赫雪花（三个科赫曲线组成）
        size = min(self.width, self.height) * 0.8
        center_x = self.width / 2
        center_y = self.height / 2
        
        # 等边三角形的三个顶点
        x1 = center_x
        y1 = center_y - size/2
        x2 = center_x - size * math.sqrt(3)/4
        y2 = center_y + size/4
        x3 = center_x + size * math.sqrt(3)/4
        y3 = center_y + size/4
        
        depth = self.params.get('depth', 4)
        
        koch_curve(x1, y1, x2, y2, depth)
        koch_curve(x2, y2, x3, y3, depth)
        koch_curve(x3, y3, x1, y1, depth)
        
        self.progress_updated.emit(100)
        return fractal
    
    def draw_line(self, fractal, x1, y1, x2, y2):
        """在分形数组上绘制直线（Bresenham算法）"""
        x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
        dx = abs(x2 - x1)
        dy = abs(y2 - y1)
        sx = 1 if x1 < x2 else -1
        sy = 1 if y1 < y2 else -1
        err = dx - dy
        
        while True:
            if 0 <= x1 < self.width and 0 <= y1 < self.height:
                fractal[y1, x1] = 0
                
            if x1 == x2 and y1 == y2:
                break
                
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x1 += sx
            if e2 < dx:
                err += dx
                y1 += sy


class ColorMapManager:
    """颜色映射管理器"""
    
    def __init__(self):
        self.colormaps = {
            "热力图": self.heat_colormap,
            "冷色调": self.cool_colormap,
            "彩虹": self.rainbow_colormap,
            "灰度": self.grayscale_colormap,
            "等离子": self.plasma_colormap,
            "紫红": self.magma_colormap,
            "蓝绿": self.viridis_colormap
        }
    
    def apply_colormap(self, fractal_data, colormap_name, max_iter=100):
        """应用颜色映射到分形数据"""
        if colormap_name in self.colormaps:
            return self.colormaps[colormap_name](fractal_data, max_iter)
        else:
            return self.heat_colormap(fractal_data, max_iter)
    
    def heat_colormap(self, data, max_iter):
        """热力图颜色映射"""
        normalized = data / max_iter
        r = np.minimum(1.0, normalized * 3.0)
        g = np.minimum(1.0, np.maximum(0.0, normalized * 3.0 - 1.0))
        b = np.maximum(0.0, normalized * 3.0 - 2.0)
        
        # 将RGB组合成图像
        rgb = np.stack([r, g, b], axis=2)
        return (rgb * 255).astype(np.uint8)
    
    def cool_colormap(self, data, max_iter):
        """冷色调颜色映射"""
        normalized = data / max_iter
        r = normalized
        g = 1.0 - normalized
        b = 1.0
        
        rgb = np.stack([r, g, b], axis=2)
        return (rgb * 255).astype(np.uint8)
    
    def rainbow_colormap(self, data, max_iter):
        """彩虹颜色映射"""
        normalized = data / max_iter
        r = np.sin(normalized * 2 * np.pi + 0) * 0.5 + 0.5
        g = np.sin(normalized * 2 * np.pi + 2 * np.pi / 3) * 0.5 + 0.5
        b = np.sin(normalized * 2 * np.pi + 4 * np.pi / 3) * 0.5 + 0.5
        
        rgb = np.stack([r, g, b], axis=2)
        return (rgb * 255).astype(np.uint8)
    
    def grayscale_colormap(self, data, max_iter):
        """灰度颜色映射"""
        normalized = 1.0 - (data / max_iter)
        rgb = np.stack([normalized, normalized, normalized], axis=2)
        return (rgb * 255).astype(np.uint8)
    
    def plasma_colormap(self, data, max_iter):
        """等离子颜色映射"""
        normalized = data / max_iter
        # 简化的等离子色映射
        r = np.sqrt(normalized)
        g = normalized ** 2
        b = np.sin(normalized * np.pi)
        
        rgb = np.stack([r, g, b], axis=2)
        return (rgb * 255).astype(np.uint8)
    
    def magma_colormap(self, data, max_iter):
        """紫红色映射"""
        normalized = data / max_iter
        r = normalized ** 0.5
        g = normalized ** 3
        b = normalized
        
        rgb = np.stack([r, g, b], axis=2)
        return (rgb * 255).astype(np.uint8)
    
    def viridis_colormap(self, data, max_iter):
        """蓝绿色映射"""
        normalized = data / max_iter
        r = normalized ** 0.5
        g = normalized
        b = normalized ** 2
        
        rgb = np.stack([r, g, b], axis=2)
        return (rgb * 255).astype(np.uint8)


class FractalCanvas(QWidget):
    """分形显示画布"""
    
    def __init__(self):
        super().__init__()
        self.setMinimumSize(600, 600)
        self.fractal_image = None
        self.zoom_rect = None
        self.dragging = False
        self.drag_start = None
        self.drag_end = None
        
        # 设置背景色
        palette = self.palette()
        palette.setColor(QPalette.Window, QColor(240, 240, 240))
        self.setPalette(palette)
        self.setAutoFillBackground(True)
    
    def set_fractal_image(self, image):
        """设置分形图像"""
        self.fractal_image = image
        self.update()
    
    def paintEvent(self, event):
        """绘制事件"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 绘制分形图像
        if self.fractal_image is not None:
            # 缩放图像以适应窗口
            img = self.fractal_image.scaled(
                self.width(), self.height(), 
                Qt.KeepAspectRatio, 
                Qt.SmoothTransformation
            )
            
            # 居中显示
            x = (self.width() - img.width()) // 2
            y = (self.height() - img.height()) // 2
            painter.drawImage(x, y, img)
        
        # 绘制缩放矩形
        if self.zoom_rect:
            pen = QPen(QColor(255, 255, 0))
            pen.setWidth(2)
            painter.setPen(pen)
            painter.drawRect(self.zoom_rect)
    
    def mousePressEvent(self, event):
        """鼠标按下事件"""
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.drag_start = event.pos()
            self.drag_end = event.pos()
            self.zoom_rect = None
            self.update()
    
    def mouseMoveEvent(self, event):
        """鼠标移动事件"""
        if self.dragging:
            self.drag_end = event.pos()
            self.zoom_rect = self.calculate_zoom_rect()
            self.update()
    
    def mouseReleaseEvent(self, event):
        """鼠标释放事件"""
        if event.button() == Qt.LeftButton and self.dragging:
            self.dragging = False
            if self.zoom_rect.width() > 10 and self.zoom_rect.height() > 10:
                # 发送缩放信号
                self.zoom_requested.emit(self.zoom_rect)
            self.zoom_rect = None
            self.update()
    
    def calculate_zoom_rect(self):
        """计算缩放矩形"""
        if not self.drag_start or not self.drag_end:
            return None
        
        # 确保矩形是正方向的
        x1 = min(self.drag_start.x(), self.drag_end.x())
        y1 = min(self.drag_start.y(), self.drag_end.y())
        x2 = max(self.drag_start.x(), self.drag_end.x())
        y2 = max(self.drag_start.y(), self.drag_end.y())
        
        return QRect(x1, y1, x2 - x1, y2 - y1)
    
    # 定义信号
    zoom_requested = pyqtSignal(QRect)


class FractalSystem(QMainWindow):
    """分形系统主窗口"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("高级分形系统工具库")
        self.setGeometry(100, 100, 1200, 800)
        
        # 初始化变量
        self.fractal_data = None
        self.fractal_type = "mandelbrot"
        self.color_map = "热力图"
        self.max_iter = 100
        self.escape_radius = 2.0
        self.julia_c = (-0.7, 0.27)
        self.x_range = (-2.0, 1.0)
        self.y_range = (-1.5, 1.5)
        self.animation_timer = QTimer()
        self.animation_phase = 0
        self.is_animating = False
        
        # 初始化管理器
        self.color_manager = ColorMapManager()
        self.worker = None
        
        # 创建UI
        self.create_ui()
        
        # 初始计算
        self.calculate_fractal()
    
    def create_ui(self):
        """创建用户界面"""
        # 中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QHBoxLayout(central_widget)
        
        # 左侧控制面板
        control_panel = self.create_control_panel()
        main_layout.addWidget(control_panel, 1)
        
        # 右侧分形显示区域
        fractal_display = self.create_fractal_display()
        main_layout.addWidget(fractal_display, 3)
    
    def create_control_panel(self):
        """创建控制面板"""
        panel = QFrame()
        panel.setFrameStyle(QFrame.StyledPanel)
        panel.setMaximumWidth(300)
        
        layout = QVBoxLayout(panel)
        
        # 分形类型选择
        fractal_group = QGroupBox("分形类型")
        fractal_layout = QVBoxLayout(fractal_group)
        
        self.fractal_combo = QComboBox()
        self.fractal_combo.addItems(["曼德勃罗集", "朱利亚集", "牛顿分形", "谢尔宾斯基三角形", "科赫雪花"])
        self.fractal_combo.currentTextChanged.connect(self.on_fractal_changed)
        fractal_layout.addWidget(self.fractal_combo)
        
        layout.addWidget(fractal_group)
        
        # 分形参数
        params_group = QGroupBox("分形参数")
        params_layout = QVBoxLayout(params_group)
        
        # 迭代次数
        iter_layout = QHBoxLayout()
        iter_layout.addWidget(QLabel("迭代次数:"))
        self.iter_spin = QSpinBox()
        self.iter_spin.setRange(10, 1000)
        self.iter_spin.setValue(100)
        self.iter_spin.valueChanged.connect(self.on_params_changed)
        iter_layout.addWidget(self.iter_spin)
        params_layout.addLayout(iter_layout)
        
        # 逃逸半径
        escape_layout = QHBoxLayout()
        escape_layout.addWidget(QLabel("逃逸半径:"))
        self.escape_spin = QDoubleSpinBox()
        self.escape_spin.setRange(1.0, 10.0)
        self.escape_spin.setValue(2.0)
        self.escape_spin.setSingleStep(0.1)
        self.escape_spin.valueChanged.connect(self.on_params_changed)
        escape_layout.addWidget(self.escape_spin)
        params_layout.addLayout(escape_layout)
        
        # 朱利亚集参数
        self.julia_layout = QHBoxLayout()
        self.julia_layout.addWidget(QLabel("C值:"))
        self.julia_real = QDoubleSpinBox()
        self.julia_real.setRange(-2.0, 2.0)
        self.julia_real.setValue(-0.7)
        self.julia_real.setSingleStep(0.01)
        self.julia_real.valueChanged.connect(self.on_params_changed)
        self.julia_layout.addWidget(self.julia_real)
        
        self.julia_imag = QDoubleSpinBox()
        self.julia_imag.setRange(-2.0, 2.0)
        self.julia_imag.setValue(0.27)
        self.julia_imag.setSingleStep(0.01)
        self.julia_imag.valueChanged.connect(self.on_params_changed)
        self.julia_layout.addWidget(self.julia_imag)
        params_layout.addLayout(self.julia_layout)
        
        # 递归深度（用于分形几何）
        self.depth_layout = QHBoxLayout()
        self.depth_layout.addWidget(QLabel("递归深度:"))
        self.depth_spin = QSpinBox()
        self.depth_spin.setRange(1, 10)
        self.depth_spin.setValue(4)
        self.depth_spin.valueChanged.connect(self.on_params_changed)
        self.depth_layout.addWidget(self.depth_spin)
        params_layout.addLayout(self.depth_layout)
        
        layout.addWidget(params_group)
        
        # 颜色映射
        color_group = QGroupBox("颜色映射")
        color_layout = QVBoxLayout(color_group)
        
        self.color_combo = QComboBox()
        self.color_combo.addItems(["热力图", "冷色调", "彩虹", "灰度", "等离子", "紫红", "蓝绿"])
        self.color_combo.currentTextChanged.connect(self.on_color_changed)
        color_layout.addWidget(self.color_combo)
        
        layout.addWidget(color_group)
        
        # 动画控制
        anim_group = QGroupBox("动画")
        anim_layout = QVBoxLayout(anim_group)
        
        self.anim_check = QCheckBox("启用动画")
        self.anim_check.toggled.connect(self.on_animation_toggled)
        anim_layout.addWidget(self.anim_check)
        
        anim_speed_layout = QHBoxLayout()
        anim_speed_layout.addWidget(QLabel("速度:"))
        self.anim_speed = QSlider(Qt.Horizontal)
        self.anim_speed.setRange(1, 100)
        self.anim_speed.setValue(50)
        anim_speed_layout.addWidget(self.anim_speed)
        anim_layout.addLayout(anim_speed_layout)
        
        layout.addWidget(anim_group)
        
        # 操作按钮
        button_layout = QHBoxLayout()
        
        self.calc_btn = QPushButton("计算分形")
        self.calc_btn.clicked.connect(self.calculate_fractal)
        button_layout.addWidget(self.calc_btn)
        
        self.save_btn = QPushButton("保存图像")
        self.save_btn.clicked.connect(self.save_fractal)
        button_layout.addWidget(self.save_btn)
        
        layout.addLayout(button_layout)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        layout.addStretch()
        
        # 初始隐藏朱利亚集参数
        self.julia_layout.parentWidget().setVisible(False)
        self.depth_layout.parentWidget().setVisible(False)
        
        return panel
    
    def create_fractal_display(self):
        """创建分形显示区域"""
        display_widget = QWidget()
        layout = QVBoxLayout(display_widget)
        
        # 分形画布
        self.fractal_canvas = FractalCanvas()
        self.fractal_canvas.zoom_requested.connect(self.on_zoom_requested)
        layout.addWidget(self.fractal_canvas)
        
        return display_widget
    
    def on_fractal_changed(self, fractal_name):
        """分形类型改变事件"""
        # 更新分形类型
        fractal_map = {
            "曼德勃罗集": "mandelbrot",
            "朱利亚集": "julia",
            "牛顿分形": "newton",
            "谢尔宾斯基三角形": "sierpinski",
            "科赫雪花": "koch"
        }
        self.fractal_type = fractal_map.get(fractal_name, "mandelbrot")
        
        # 显示/隐藏相关参数
        is_julia = fractal_name == "朱利亚集"
        is_geometric = fractal_name in ["谢尔宾斯基三角形", "科赫雪花"]
        
        self.julia_layout.parentWidget().setVisible(is_julia)
        self.depth_layout.parentWidget().setVisible(is_geometric)
        
        # 重新计算分形
        self.calculate_fractal()
    
    def on_params_changed(self):
        """参数改变事件"""
        # 更新参数
        self.max_iter = self.iter_spin.value()
        self.escape_radius = self.escape_spin.value()
        self.julia_c = (self.julia_real.value(), self.julia_imag.value())
        
        # 重新计算分形
        self.calculate_fractal()
    
    def on_color_changed(self, color_name):
        """颜色映射改变事件"""
        self.color_map = color_name
        self.update_fractal_display()
    
    def on_animation_toggled(self, checked):
        """动画开关事件"""
        self.is_animating = checked
        if checked:
            self.animation_timer.timeout.connect(self.animate_fractal)
            interval = int(1000 // (self.anim_speed.value() / 10))
            self.animation_timer.start(interval)
        else:
            self.animation_timer.stop()
    
    def on_zoom_requested(self, rect):
        """缩放请求事件"""
        # 计算新的坐标范围
        canvas_width = self.fractal_canvas.width()
        canvas_height = self.fractal_canvas.height()
        
        # 计算图像在画布上的实际显示区域
        if self.fractal_canvas.fractal_image:
            img = self.fractal_canvas.fractal_image
            img_width = img.width()
            img_height = img.height()
            
            # 计算缩放比例
            scale_x = img_width / canvas_width
            scale_y = img_height / canvas_height
            
            # 计算图像在画布上的偏移
            offset_x = (canvas_width - img_width) / 2
            offset_y = (canvas_height - img_height) / 2
            
            # 将画布坐标转换为图像坐标
            x1 = (rect.x() - offset_x) * scale_x
            y1 = (rect.y() - offset_y) * scale_y
            x2 = (rect.x() + rect.width() - offset_x) * scale_x
            y2 = (rect.y() + rect.height() - offset_y) * scale_y
            
            # 确保坐标在图像范围内
            x1 = max(0, min(img_width, x1))
            y1 = max(0, min(img_height, y1))
            x2 = max(0, min(img_width, x2))
            y2 = max(0, min(img_height, y2))
            
            # 计算新的坐标范围
            x_min, x_max = self.x_range
            y_min, y_max = self.y_range
            
            new_x_min = x_min + (x1 / img_width) * (x_max - x_min)
            new_x_max = x_min + (x2 / img_width) * (x_max - x_min)
            new_y_min = y_min + (y1 / img_height) * (y_max - y_min)
            new_y_max = y_min + (y2 / img_height) * (y_max - y_min)
            
            # 更新坐标范围
            self.x_range = (new_x_min, new_x_max)
            self.y_range = (new_y_min, new_y_max)
            
            # 重新计算分形
            self.calculate_fractal()
    
    def calculate_fractal(self):
        """计算分形"""
        # 如果已有计算在进行，先停止
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait()
        
        # 准备参数
        params = {
            'max_iter': self.max_iter,
            'escape_radius': self.escape_radius,
            'c': self.julia_c,
            'x_range': self.x_range,
            'y_range': self.y_range,
            'depth': self.depth_spin.value()
        }
        
        # 创建并启动工作线程
        self.worker = FractalWorker(
            self.fractal_type, 
            800, 800,  # 固定分辨率，可根据需要调整
            params
        )
        self.worker.progress_updated.connect(self.on_progress_updated)
        self.worker.fractal_completed.connect(self.on_fractal_calculated)
        
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.calc_btn.setEnabled(False)
        
        self.worker.start()
    
    def on_progress_updated(self, progress):
        """进度更新事件"""
        self.progress_bar.setValue(progress)
    
    def on_fractal_calculated(self, fractal_data):
        """分形计算完成事件"""
        self.fractal_data = fractal_data
        self.update_fractal_display()
        
        self.progress_bar.setVisible(False)
        self.calc_btn.setEnabled(True)
    
    def update_fractal_display(self):
        """更新分形显示"""
        if self.fractal_data is not None:
            # 应用颜色映射
            colored_fractal = self.color_manager.apply_colormap(
                self.fractal_data, self.color_map, self.max_iter
            )
            
            # 转换为QImage
            height, width, _ = colored_fractal.shape
            bytes_per_line = 3 * width
            q_image = QImage(
                colored_fractal.data, 
                width, height, 
                bytes_per_line, 
                QImage.Format_RGB888
            )
            
            # 显示图像
            self.fractal_canvas.set_fractal_image(q_image)
    
    def animate_fractal(self):
        """动画分形"""
        if self.fractal_type == "julia":
            # 对朱利亚集进行动画：旋转C值
            angle = self.animation_phase * 0.1
            r = 0.7885  # 固定半径，产生有趣的效果
            self.julia_c = (r * math.cos(angle), r * math.sin(angle))
            
            self.julia_real.setValue(self.julia_c[0])
            self.julia_imag.setValue(self.julia_c[1])
            
            self.animation_phase += 1
            if self.animation_phase >= 100:
                self.animation_phase = 0
                
            # 更新动画速度
            interval = 1000 // (self.anim_speed.value() / 10)
            self.animation_timer.setInterval(interval)
    
    def save_fractal(self):
        """保存分形图像"""
        if self.fractal_canvas.fractal_image is None:
            QMessageBox.warning(self, "警告", "没有分形图像可保存")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存分形图像", "", "PNG图像 (*.png);;JPEG图像 (*.jpg);;所有文件 (*)"
        )
        
        if file_path:
            success = self.fractal_canvas.fractal_image.save(file_path)
            if success:
                QMessageBox.information(self, "成功", "图像已保存")
            else:
                QMessageBox.warning(self, "错误", "保存图像时出错")


# 运行应用程序
if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 设置应用程序样式
    app.setStyle("Fusion")
    
    # 创建并显示主窗口
    window = FractalSystem()
    window.show()
    
    sys.exit(app.exec_())