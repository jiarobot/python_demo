import sys
import math
import random
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QLabel, QPushButton, QGroupBox, QListWidget, QSlider, QSplitter,
                            QTabWidget, QStatusBar, QAction, QMenu, QFileDialog, QMessageBox)
from PyQt5.QtCore import QPointF, Qt, QTimer, QSize, QPoint
from PyQt5.QtGui import QPainter, QPainterPath, QPen, QColor, QFont, QBrush, QLinearGradient, QIcon, QPixmap
import matplotlib
matplotlib.rc("font", family='Microsoft YaHei')
matplotlib.use("Qt5Agg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import numpy as np

# 八卦定义
BAGUA = {
    "乾": (1, 1, 1),
    "兑": (1, 1, 0),
    "离": (1, 0, 1),
    "震": (1, 0, 0),
    "巽": (0, 1, 1),
    "坎": (0, 1, 0),
    "艮": (0, 0, 1),
    "坤": (0, 0, 0)
}

# 卦象解释
BAGUA_EXPLANATION = {
    "乾": "天 - 创造、领导、主动飞行模式",
    "坤": "地 - 接收、跟随、自动降落模式",
    "震": "雷 - 行动、启动、加速飞行",
    "巽": "风 - 渗透、巡航、平稳飞行",
    "坎": "水 - 危险、规避、避障模式",
    "离": "火 - 光明、探索、目标追踪",
    "艮": "山 - 静止、悬停、位置保持",
    "兑": "泽 - 喜悦、沟通、数据采集模式"
}

# 无人机状态类
class Drone:
    def __init__(self, id=0):
        self.id = id
        self.x = 400
        self.y = 300
        self.altitude = 10.0
        self.speed = 0.0
        self.heading = 0.0  # 0-360 degrees
        self.battery = 100
        self.status = "待命"
        self.flight_mode = "坤"
        self.flight_log = []
        self.trajectory = []
        self.target = None
        self.obstacles = []
        self.generate_obstacles()
        self.color = self.random_drone_color()
        self.name = f"无人机-{id+1}"
    
    def random_drone_color(self):
        colors = [
            (255, 100, 100),  # 红色
            (100, 200, 100),  # 绿色
            (100, 150, 255),  # 蓝色
            (255, 200, 50),   # 黄色
            (200, 100, 255)   # 紫色
        ]
        return colors[self.id % len(colors)]
    
    def generate_obstacles(self):
        self.obstacles = []
        for _ in range(8):
            x = random.randint(50, 750)
            y = random.randint(50, 550)
            size = random.randint(20, 50)
            self.obstacles.append((x, y, size))
    
    def update(self, mode):
        self.flight_mode = mode
        mode_exp = BAGUA_EXPLANATION[mode]
        
        # 根据卦象更新状态
        if mode == "乾":  # 主动飞行
            self.speed = min(self.speed + 0.5, 8.0)
            self.heading = (self.heading + random.uniform(-5, 5)) % 360
        elif mode == "坤":  # 自动降落
            self.speed = max(self.speed - 0.2, 0)
            self.altitude = max(self.altitude - 0.5, 5)
        elif mode == "震":  # 加速飞行
            self.speed = min(self.speed + 1.0, 12.0)
            self.heading = (self.heading + random.uniform(-10, 10)) % 360
        elif mode == "巽":  # 平稳飞行
            self.speed = 5.0
            self.heading = (self.heading + random.uniform(-2, 2)) % 360
        elif mode == "坎":  # 避障模式
            self.speed = 4.0
            # 简单避障逻辑
            for obs in self.obstacles:
                dx = obs[0] - self.x
                dy = obs[1] - self.y
                dist = math.sqrt(dx*dx + dy*dy)
                if dist < 150:
                    self.heading = (self.heading + 15) % 360
        elif mode == "离":  # 目标追踪
            if self.target:
                dx = self.target.x() - self.x
                dy = self.target.y() - self.y
                angle = math.degrees(math.atan2(dy, dx))
                angle_diff = (angle - self.heading + 180) % 360 - 180
                self.heading = (self.heading + angle_diff * 0.1) % 360
                self.speed = min(self.speed + 0.3, 6.0)
        elif mode == "艮":  # 悬停
            self.speed = 0.0
        elif mode == "兑":  # 数据采集
            self.speed = 3.0
            self.heading = (self.heading + 0.5) % 360
        
        # 更新位置
        if self.speed > 0:
            rad = math.radians(self.heading)
            self.x += self.speed * math.cos(rad)
            self.y += self.speed * math.sin(rad)
            
            # 边界检查
            self.x = max(50, min(750, self.x))
            self.y = max(50, min(550, self.y))
        
        # 记录轨迹
        self.trajectory.append((self.x, self.y))
        if len(self.trajectory) > 200:
            self.trajectory.pop(0)
        
        # 更新电池
        self.battery -= 0.02 * self.speed
        if self.battery < 0:
            self.battery = 0
            self.status = "电量耗尽"
        
        # 记录日志
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{self.name}] {timestamp} - 模式:{mode} 速度:{self.speed:.1f}m/s 航向:{self.heading:.1f}°"
        self.flight_log.append(log_entry)
        if len(self.flight_log) > 50:
            self.flight_log.pop(0)
        
        return mode_exp

# 八卦符号绘制类
class BaguaWidget(QWidget):
    def __init__(self, hexagram, active=False, parent=None):
        super().__init__(parent)
        self.hexagram = hexagram
        self.active = active
        self.setMinimumSize(120, 180)
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        width = self.width()
        height = self.height()
        size = min(width, height) // 2
        
        # 设置颜色
        yin_color = QColor(100, 180, 255)
        yang_color = QColor(255, 200, 50)
        highlight_color = QColor(0, 200, 255)
        text_color = QColor(220, 220, 220)
        
        # 绘制背景
        if self.active:
            gradient = QLinearGradient(0, 0, width, height)
            gradient.setColorAt(0, QColor(30, 50, 70))
            gradient.setColorAt(1, QColor(20, 30, 50))
            painter.setBrush(QBrush(gradient))
            painter.setPen(QPen(highlight_color, 2))
            painter.drawRoundedRect(0, 0, width, height, 10, 10)
        else:
            painter.setBrush(QBrush(QColor(25, 40, 60)))
            painter.setPen(QPen(QColor(60, 80, 100), 1))
            painter.drawRoundedRect(0, 0, width, height, 10, 10)
        
        # 绘制卦名
        painter.setFont(QFont("Microsoft YaHei", 14, QFont.Bold))
        painter.setPen(QPen(highlight_color if self.active else text_color))
        painter.drawText(0, 20, width, 30, Qt.AlignCenter, self.hexagram)
        
        # 绘制卦象解释
        explanation = BAGUA_EXPLANATION[self.hexagram]
        painter.setFont(QFont("Microsoft YaHei", 9))
        painter.setPen(QPen(text_color))
        painter.drawText(0, 40, width, 30, Qt.AlignCenter, explanation.split(" - ")[0])
        
        # 绘制三爻
        lines = BAGUA[self.hexagram]
        line_height = size // 3
        line_width = size * 1.5
        y_start = height // 2 - size // 2
        
        for i, line in enumerate(lines):
            line_y = y_start + i * line_height
            if line == 1:  # 阳爻 (实线)
                painter.setBrush(QBrush(yang_color))
                painter.setPen(QPen(yang_color.darker(150), 1))
                painter.drawRect(width//2 - line_width//2, line_y, line_width, line_height // 2)
            else:  # 阴爻 (虚线)
                painter.setBrush(QBrush(yin_color))
                painter.setPen(QPen(yin_color.darker(150), 1))
                painter.drawRect(width//2 - line_width//2, line_y, line_width, line_height // 3)
                painter.drawRect(width//2 - line_width//2, line_y + 2 * line_height // 3, line_width, line_height // 3)

# 无人机显示区域
class DroneDisplay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.drones = []
        self.active_drone_idx = 0
        self.hexagram_history = ["坤"]
        self.setMinimumSize(800, 600)
        self.setMouseTracking(True)
        self.target_point = None
        
        # 添加初始无人机
        self.add_drone()
        self.add_drone()
        
    def add_drone(self):
        new_drone = Drone(len(self.drones))
        self.drones.append(new_drone)
        return new_drone
    
    def get_active_drone(self):
        if self.drones:
            return self.drones[self.active_drone_idx]
        return None
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        width = self.width()
        height = self.height()
        
        # 绘制背景
        gradient = QLinearGradient(0, 0, width, height)
        gradient.setColorAt(0, QColor(10, 20, 30))
        gradient.setColorAt(1, QColor(15, 30, 45))
        painter.fillRect(0, 0, width, height, QBrush(gradient))
        
        # 绘制网格
        painter.setPen(QPen(QColor(40, 60, 80), 1))
        for x in range(0, width, 40):
            painter.drawLine(x, 0, x, height)
        for y in range(0, height, 40):
            painter.drawLine(0, y, width, y)
        
        # 绘制障碍物
        if self.drones:
            active_drone = self.get_active_drone()
            for x, y, size in active_drone.obstacles:
                painter.setBrush(QBrush(QColor(180, 80, 80)))
                painter.setPen(QPen(QColor(220, 50, 50), 2))
                painter.drawEllipse(QPoint(x, y), size, size)
        
        # 绘制目标点
        if self.target_point:
            painter.setBrush(QBrush(QColor(50, 200, 100)))
            painter.setPen(QPen(QColor(0, 255, 150), 2))
            painter.drawEllipse(self.target_point, 15, 15)
            painter.drawEllipse(self.target_point, 10, 10)
        
        # 绘制无人机和轨迹
        for drone in self.drones:
            if drone == self.get_active_drone():
                # 绘制轨迹
                if len(drone.trajectory) >= 2:
                    painter.setPen(QPen(QColor(255, 50, 50, 150), 2))
                    # 创建路径而不是单独的点
                    path = QPainterPath()
                    # 移动到第一个点
                    path.moveTo(QPointF(drone.trajectory[0][0], drone.trajectory[0][1]))
                    # 添加所有其他点
                    for x, y in drone.trajectory[1:]:
                        path.lineTo(QPointF(x, y))
                    # 绘制整个路径
                    painter.drawPath(path)
            
            # 绘制无人机
            self.draw_drone(painter, drone)
        
        # 绘制当前卦象
        if self.drones:
            current_hex = self.hexagram_history[-1]
            painter.setFont(QFont("Microsoft YaHei", 16, QFont.Bold))
            painter.setPen(QPen(QColor(0, 200, 255)))
            painter.drawText(width - 150, 20, 130, 30, Qt.AlignCenter, f"当前卦象: {current_hex}")
            
            explanation = BAGUA_EXPLANATION[current_hex]
            painter.setFont(QFont("Microsoft YaHei", 10))
            painter.drawText(width - 150, 50, 130, 50, Qt.AlignCenter, explanation)
    
    def draw_drone(self, painter, drone):
        # 绘制无人机
        color = QColor(*drone.color)
        active = drone == self.get_active_drone()
        
        # 绘制机身
        painter.setBrush(QBrush(color))
        painter.setPen(QPen(color.darker(150), 2))
        painter.drawEllipse(QPoint(int(drone.x), int(drone.y)), 20, 20)
        
        # 绘制机头指示器 - 修复部分
        rad = math.radians(drone.heading)
        end_x = drone.x + 20 * math.cos(rad)
        end_y = drone.y + 20 * math.sin(rad)
        painter.setPen(QPen(Qt.white, 3))
        # 使用 QPointF 或者将坐标转换为整数
        painter.drawLine(QPointF(drone.x, drone.y), QPointF(end_x, end_y))
        
        # 绘制螺旋桨
        for angle in [0, 90, 180, 270]:
            rad = math.radians(angle)
            prop_x = drone.x + 25 * math.cos(rad)
            prop_y = drone.y + 25 * math.sin(rad)
            painter.setBrush(QBrush(QColor(200, 200, 220)))
            painter.setPen(QPen(QColor(150, 150, 180), 1))
            painter.drawRect(int(prop_x - 3), int(prop_y - 10), 6, 20)
        
        # 绘制无人机ID和状态
        painter.setFont(QFont("Microsoft YaHei", 9))
        painter.setPen(QPen(Qt.white))
        painter.drawText(int(drone.x - 30), int(drone.y - 30), 60, 20, Qt.AlignCenter, drone.name)
        
        # 如果是活动无人机，绘制高亮边框
        if active:
            painter.setPen(QPen(QColor(0, 200, 255), 3))
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(QPoint(int(drone.x), int(drone.y)), 30, 30)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.target_point = event.pos()
            if self.drones:
                self.get_active_drone().target = self.target_point
            self.update()
        
        # 检查是否点击了无人机
        for i, drone in enumerate(self.drones):
            dx = event.x() - drone.x
            dy = event.y() - drone.y
            dist = math.sqrt(dx*dx + dy*dy)
            if dist < 30:
                self.active_drone_idx = i
                self.update()
                break
    
    def update_drone(self, mode):
        if self.drones:
            drone = self.get_active_drone()
            mode_exp = drone.update(mode)
            self.hexagram_history.append(mode)
            if len(self.hexagram_history) > 20:
                self.hexagram_history.pop(0)
            self.update()
            return mode_exp
        return ""

# 卦象图表
class HexagramChart(FigureCanvas):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.ax = self.fig.add_subplot(111)
        super().__init__(self.fig)
        self.setParent(parent)
        
        self.hexagram_history = ["坤"]
        self.update_chart()
    
    def update_chart(self, history=None):
        if history:
            self.hexagram_history = history
        
        self.ax.clear()
        
        # 准备数据
        hexagrams = list(BAGUA.keys())
        counts = [self.hexagram_history.count(h) for h in hexagrams]
        
        # 设置颜色
        yin_color = (100/255, 180/255, 255/255)
        yang_color = (255/255, 200/255, 50/255)
        highlight_color = (0/255, 200/255, 255/255)
        
        colors = []
        for i, h in enumerate(hexagrams):
            if counts[i] > 0:
                if self.hexagram_history and h == self.hexagram_history[-1]:
                    colors.append(highlight_color)
                else:
                    colors.append(yang_color)
            else:
                colors.append(yin_color)
        
        # 绘制柱状图
        bars = self.ax.bar(hexagrams, counts, color=colors)
        
        # 设置图表样式
        self.ax.set_title('卦象使用频率', color='white', fontsize=12)
        self.ax.set_ylabel('使用次数', color='white')
        self.ax.tick_params(axis='x', colors='white', rotation=45)
        self.ax.tick_params(axis='y', colors='white')
        
        # 设置背景色
        self.fig.patch.set_facecolor('#0a141e')
        self.ax.set_facecolor('#0a141e')
        
        for spine in self.ax.spines.values():
            spine.set_color('gray')
        
        self.draw()

# 主窗口
class DroneControlSystem(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("易经八卦飞行控制系统")
        self.setGeometry(100, 100, 1200, 800)
        self.setWindowIcon(QIcon(self.create_icon()))
        
        # 创建主部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # 左侧控制面板
        control_panel = QGroupBox("飞行控制")
        control_layout = QVBoxLayout()
        
        # 八卦控制按钮
        self.bagua_buttons = []
        hexagrams = list(BAGUA.keys())
        for i, hexagram in enumerate(hexagrams):
            btn = QPushButton(hexagram)
            btn.setMinimumHeight(60)
            btn.setStyleSheet(self.get_bagua_button_style(hexagram))
            btn.clicked.connect(lambda _, h=hexagram: self.set_flight_mode(h))
            self.bagua_buttons.append(btn)
            control_layout.addWidget(btn)
        
        # 其他控制按钮
        control_layout.addSpacing(20)
        self.random_btn = QPushButton("随机卦象")
        self.random_btn.setStyleSheet(self.get_button_style("#6a89cc"))
        self.random_btn.clicked.connect(self.set_random_mode)
        control_layout.addWidget(self.random_btn)
        
        self.reset_btn = QPushButton("重置系统")
        self.reset_btn.setStyleSheet(self.get_button_style("#f8c291"))
        self.reset_btn.clicked.connect(self.reset_system)
        control_layout.addWidget(self.reset_btn)
        
        self.add_drone_btn = QPushButton("添加无人机")
        self.add_drone_btn.setStyleSheet(self.get_button_style("#78e08f"))
        self.add_drone_btn.clicked.connect(self.add_drone)
        control_layout.addWidget(self.add_drone_btn)
        
        control_panel.setLayout(control_layout)
        control_panel.setMaximumWidth(250)
        
        # 右侧显示区域
        display_panel = QWidget()
        display_layout = QVBoxLayout()
        
        # 无人机显示区域
        self.drone_display = DroneDisplay()
        
        # 状态面板
        status_panel = QGroupBox("飞行状态")
        status_layout = QHBoxLayout()
        
        # 无人机信息
        drone_info = QGroupBox("无人机状态")
        drone_layout = QVBoxLayout()
        self.drone_name = QLabel("无人机-1")
        self.drone_name.setStyleSheet("font-size: 16px; font-weight: bold; color: #00c8ff;")
        drone_layout.addWidget(self.drone_name)
        
        self.mode_label = QLabel("模式: 坤 - 地 - 自动降落模式")
        self.altitude_label = QLabel("高度: 10.0 m")
        self.speed_label = QLabel("速度: 0.0 m/s")
        self.heading_label = QLabel("航向: 0.0°")
        self.battery_label = QLabel("电量: 100%")
        self.status_label = QLabel("状态: 待命")
        
        for label in [self.mode_label, self.altitude_label, self.speed_label, 
                     self.heading_label, self.battery_label, self.status_label]:
            label.setStyleSheet("font-size: 14px; color: #e0e0e0;")
            drone_layout.addWidget(label)
        
        drone_info.setLayout(drone_layout)
        
        # 电池指示器
        battery_panel = QGroupBox("电池状态")
        battery_layout = QVBoxLayout()
        self.battery_bar = QSlider(Qt.Horizontal)
        self.battery_bar.setRange(0, 100)
        self.battery_bar.setValue(100)
        self.battery_bar.setEnabled(False)
        battery_layout.addWidget(self.battery_bar)
        
        self.battery_percent = QLabel("100%")
        self.battery_percent.setStyleSheet("font-size: 24px; font-weight: bold; color: #00c8ff;")
        self.battery_percent.setAlignment(Qt.AlignCenter)
        battery_layout.addWidget(self.battery_percent)
        battery_panel.setLayout(battery_layout)
        
        status_layout.addWidget(drone_info)
        status_layout.addWidget(battery_panel)
        status_panel.setLayout(status_layout)
        
        # 选项卡
        tab_widget = QTabWidget()
        
        # 飞行日志
        log_tab = QWidget()
        log_layout = QVBoxLayout()
        self.log_list = QListWidget()
        self.log_list.setStyleSheet("""
            QListWidget {
                background-color: #15202b;
                color: #e0e0e0;
                border: 1px solid #2c3e50;
                font-size: 12px;
            }
            QListWidget::item {
                padding: 5px;
                border-bottom: 1px solid #2c3e50;
            }
            QListWidget::item:selected {
                background-color: #1a5276;
            }
        """)
        log_layout.addWidget(self.log_list)
        log_tab.setLayout(log_layout)
        
        # 卦象图表
        chart_tab = QWidget()
        chart_layout = QVBoxLayout()
        self.chart = HexagramChart()
        chart_layout.addWidget(self.chart)
        chart_tab.setLayout(chart_layout)
        
        tab_widget.addTab(log_tab, "飞行日志")
        tab_widget.addTab(chart_tab, "卦象分析")
        
        # 组装显示区域
        display_layout.addWidget(self.drone_display)
        display_layout.addWidget(status_panel)
        display_layout.addWidget(tab_widget)
        display_panel.setLayout(display_layout)
        
        # 主布局
        main_layout.addWidget(control_panel)
        main_layout.addWidget(display_panel)
        
        # 状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("系统已就绪")
        
        # 菜单栏
        self.create_menu()
        
        # 更新定时器
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_system)
        self.timer.start(100)  # 每100ms更新一次
        
        # 初始化状态
        self.update_status()
    
    def create_icon(self):
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 绘制八卦背景
        painter.setBrush(QBrush(QColor(30, 50, 80)))
        painter.drawEllipse(0, 0, 64, 64)
        
        # 绘制无人机
        painter.setBrush(QBrush(QColor(255, 100, 100)))
        painter.drawEllipse(32, 32, 10, 10)
        
        # 绘制卦象
        painter.setBrush(QBrush(QColor(0, 200, 255)))
        painter.drawRect(25, 15, 14, 4)
        painter.drawRect(25, 25, 14, 4)
        painter.drawRect(25, 35, 14, 4)
        
        painter.end()
        return pixmap
    
    def create_menu(self):
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu("文件")
        
        new_action = QAction("新建", self)
        new_action.setShortcut("Ctrl+N")
        file_menu.addAction(new_action)
        
        save_action = QAction("保存日志", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.save_log)
        file_menu.addAction(save_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("退出", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu("帮助")
        
        about_action = QAction("关于", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def get_bagua_button_style(self, hexagram):
        colors = {
            "乾": "#f6b93b",  # 黄色
            "兑": "#4a69bd",  # 蓝色
            "离": "#e55039",  # 红色
            "震": "#78e08f",  # 绿色
            "巽": "#82ccdd",  # 浅蓝
            "坎": "#1e3799",  # 深蓝
            "艮": "#b71540",  # 深红
            "坤": "#3c6382"   # 深灰蓝
        }
        
        color = colors.get(hexagram, "#4a69bd")
        return f"""
            QPushButton {{
                background-color: {color};
                color: white;
                font-size: 24px;
                font-weight: bold;
                border: none;
                border-radius: 5px;
                padding: 10px;
            }}
            QPushButton:hover {{
                background-color: {self.lighten_color(color)};
            }}
            QPushButton:pressed {{
                background-color: {self.darken_color(color)};
            }}
        """
    
    def get_button_style(self, color):
        return f"""
            QPushButton {{
                background-color: {color};
                color: white;
                font-size: 16px;
                font-weight: bold;
                border: none;
                border-radius: 5px;
                padding: 10px;
            }}
            QPushButton:hover {{
                background-color: {self.lighten_color(color)};
            }}
            QPushButton:pressed {{
                background-color: {self.darken_color(color)};
            }}
        """
    
    def lighten_color(self, hex_color, amount=30):
        # 简化处理，实际应用中需要更精确的颜色操作
        return hex_color
    
    def darken_color(self, hex_color, amount=30):
        # 简化处理，实际应用中需要更精确的颜色操作
        return hex_color
    
    def set_flight_mode(self, mode):
        if self.drone_display.drones:
            mode_exp = self.drone_display.update_drone(mode)
            self.status_bar.showMessage(f"已切换到 {mode} 模式: {mode_exp}")
            self.update_status()
            self.chart.update_chart(self.drone_display.hexagram_history)
    
    def set_random_mode(self):
        hexagrams = list(BAGUA.keys())
        mode = random.choice(hexagrams)
        self.set_flight_mode(mode)
    
    def reset_system(self):
        self.drone_display = DroneDisplay()
        self.centralWidget().layout().itemAt(1).widget().layout().itemAt(0).widget().setParent(None)
        self.centralWidget().layout().itemAt(1).widget().layout().insertWidget(0, self.drone_display)
        self.update_status()
        self.log_list.clear()
        self.chart.update_chart(self.drone_display.hexagram_history)
        self.status_bar.showMessage("系统已重置")
    
    def add_drone(self):
        new_drone = self.drone_display.add_drone()
        self.log_list.addItem(f"[系统] 已添加 {new_drone.name}")
        self.status_bar.showMessage(f"已添加 {new_drone.name}")
        self.update_status()
    
    def update_system(self):
        if self.drone_display.drones:
            # 保持当前模式更新
            mode = self.drone_display.hexagram_history[-1]
            mode_exp = self.drone_display.update_drone(mode)
            
            # 更新状态显示
            self.update_status()
            
            # 更新日志
            active_drone = self.drone_display.get_active_drone()
            if active_drone.flight_log:
                last_log = active_drone.flight_log[-1]
                if not self.log_list.count() or self.log_list.item(self.log_list.count()-1).text() != last_log:
                    self.log_list.addItem(last_log)
                    self.log_list.scrollToBottom()
    
    def update_status(self):
        if self.drone_display.drones:
            drone = self.drone_display.get_active_drone()
            self.drone_name.setText(drone.name)
            self.mode_label.setText(f"模式: {drone.flight_mode} - {BAGUA_EXPLANATION[drone.flight_mode]}")
            self.altitude_label.setText(f"高度: {drone.altitude:.1f} m")
            self.speed_label.setText(f"速度: {drone.speed:.1f} m/s")
            self.heading_label.setText(f"航向: {drone.heading:.1f}°")
            self.battery_label.setText(f"电量: {drone.battery:.1f}%")
            self.status_label.setText(f"状态: {drone.status}")
            
            # 更新电池显示
            self.battery_bar.setValue(int(drone.battery))
            self.battery_percent.setText(f"{drone.battery:.1f}%")
            
            # 根据电量设置颜色
            if drone.battery > 70:
                color = "#00c8ff"
            elif drone.battery > 30:
                color = "#f6b93b"
            else:
                color = "#e55039"
            
            self.battery_percent.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {color};")
    
    def save_log(self):
        if not self.drone_display.drones:
            return
        
        filename, _ = QFileDialog.getSaveFileName(
            self, "保存飞行日志", "", "文本文件 (*.txt)"
        )
        
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write("易经八卦飞行控制系统 - 飞行日志\n")
                    f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write("=" * 50 + "\n\n")
                    
                    for i in range(self.log_list.count()):
                        f.write(self.log_list.item(i).text() + "\n")
                
                self.status_bar.showMessage(f"日志已保存到: {filename}")
            except Exception as e:
                QMessageBox.critical(self, "保存错误", f"保存日志时出错:\n{str(e)}")
    
    def show_about(self):
        about_text = """
        <h2>易经八卦飞行控制系统</h2>
        <p>版本: 1.0.0</p>
        <p>基于易经八卦原理设计的无人机控制系统</p>
        <p>八卦对应八种飞行模式，结合传统智慧与现代科技</p>
        <p>© 2023 智能飞行科技公司</p>
        """
        QMessageBox.about(self, "关于", about_text)

# 运行应用
if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 设置应用样式
    app.setStyle("Fusion")
    
    # 设置调色板
    palette = app.palette()
    palette.setColor(palette.Window, QColor(20, 30, 45))
    palette.setColor(palette.WindowText, QColor(220, 220, 220))
    palette.setColor(palette.Base, QColor(25, 40, 60))
    palette.setColor(palette.AlternateBase, QColor(30, 50, 70))
    palette.setColor(palette.ToolTipBase, QColor(0, 200, 255))
    palette.setColor(palette.ToolTipText, Qt.white)
    palette.setColor(palette.Text, Qt.white)
    palette.setColor(palette.Button, QColor(40, 60, 80))
    palette.setColor(palette.ButtonText, Qt.white)
    palette.setColor(palette.BrightText, QColor(0, 200, 255))
    palette.setColor(palette.Highlight, QColor(0, 150, 200))
    palette.setColor(palette.HighlightedText, Qt.white)
    app.setPalette(palette)
    
    window = DroneControlSystem()
    window.show()
    sys.exit(app.exec_())