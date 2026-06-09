import sys
import random
import json
import datetime
import numpy as np
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QGridLayout, QGroupBox, QLabel, 
                            QProgressBar, QPushButton, QTabWidget, QFrame,
                            QSlider, QTextEdit, QSplitter, QComboBox,
                            QTableWidget, QTableWidgetItem, QHeaderView,
                            QLineEdit, QSpinBox, QDoubleSpinBox, QCheckBox,
                            QRadioButton, QButtonGroup, QFileDialog, QMessageBox,
                            QTreeWidget, QTreeWidgetItem, QToolBar, QStatusBar,
                            QToolButton, QMenu, QDialog, QDialogButtonBox,
                            QFormLayout, QListWidget, QListWidgetItem)
from PyQt6.QtCore import QPointF, QTimer, Qt, pyqtSignal, QDateTime, QSize, QThread, pyqtSignal
from PyQt6.QtGui import (QFont, QPalette, QColor, QPainter, QLinearGradient,
                        QPen, QBrush, QAction, QIcon, QPixmap, QFontDatabase)
from PyQt6.QtCharts import QChart, QChartView, QLineSeries, QValueAxis, QSplineSeries, QAreaSeries
import sqlite3
import logging
from dataclasses import dataclass
from enum import Enum
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

# 系统状态枚举
class SystemStatus(Enum):
    OFFLINE = 0
    STANDBY = 1
    OPERATIONAL = 2
    WARNING = 3
    CRITICAL = 4
    EMERGENCY = 5

# 数据模型
@dataclass
class BloodSystemData:
    energy_level: float = 85.0
    flow_rate: float = 70.0
    temperature: float = 37.5
    pressure: float = 120.0
    oxygen_level: float = 95.0
    waste_level: float = 15.0
    pump_speed: int = 1500
    cooling_status: bool = True
    
@dataclass
class SkinSystemData:
    chemical_sensitivity: float = 85.0
    tactile_sensitivity: float = 92.0
    temperature_sensitivity: float = 88.0
    humidity_sensitivity: float = 75.0
    pressure_sensitivity: float = 90.0
    neural_processing_load: float = 45.0
    reaction_time: float = 12.5
    pattern_recognition_rate: float = 98.7

@dataclass
class VisionSystemData:
    processing_fps: float = 60.0
    object_detection_accuracy: float = 96.3
    depth_perception_accuracy: float = 94.7
    low_light_performance: float = 88.5
    motion_tracking_accuracy: float = 97.2

@dataclass
class AISystemData:
    neural_network_load: float = 65.0
    inference_speed: float = 245.0
    learning_rate: float = 0.001
    memory_usage: float = 72.5
    training_progress: float = 45.8

@dataclass
class LanguageSystemData:
    response_time: float = 85.0
    speech_recognition_accuracy: float = 95.8
    language_translation_accuracy: float = 92.4
    contextual_understanding: float = 89.7
    emotion_recognition: float = 87.3

@dataclass
class MotionSystemData:
    hydraulic_pressure: float = 78.5
    joint_flexibility: float = 85.0
    power_efficiency: float = 92.0
    balance_stability: float = 96.5
    movement_precision: float = 94.2

# 数据库管理
class DatabaseManager:
    def __init__(self):
        self.conn = sqlite3.connect('robot_system.db', check_same_thread=False)
        self.create_tables()
        
    def create_tables(self):
        cursor = self.conn.cursor()
        
        # 系统状态表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_status (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                system_name TEXT,
                status INTEGER,
                value REAL,
                message TEXT
            )
        ''')
        
        # 警报记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                system_name TEXT,
                alert_level INTEGER,
                message TEXT,
                acknowledged BOOLEAN DEFAULT FALSE
            )
        ''')
        
        # 性能指标表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS performance_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                metric_name TEXT,
                value REAL
            )
        ''')
        
        self.conn.commit()
    
    def log_system_status(self, system_name, status, value, message):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO system_status (system_name, status, value, message)
            VALUES (?, ?, ?, ?)
        ''', (system_name, status, value, message))
        self.conn.commit()
    
    def log_alert(self, system_name, alert_level, message):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO alerts (system_name, alert_level, message)
            VALUES (?, ?, ?)
        ''', (system_name, alert_level, message))
        self.conn.commit()
    
    def get_recent_alerts(self, limit=50):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM alerts 
            ORDER BY timestamp DESC 
            LIMIT ?
        ''', (limit,))
        return cursor.fetchall()

# 数据采集线程
class DataCollectionThread(QThread):
    data_updated = pyqtSignal(dict)
    system_alert = pyqtSignal(str, int, str)
    
    def __init__(self):
        super().__init__()
        self.running = True
        self.db_manager = DatabaseManager()
        
    def run(self):
        counter = 0
        while self.running:
            # 模拟数据采集
            data = {
                'timestamp': datetime.datetime.now(),
                'blood_system': self._generate_blood_data(),
                'skin_system': self._generate_skin_data(),
                'vision_system': self._generate_vision_data(),
                'ai_system': self._generate_ai_data(),
                'language_system': self._generate_language_data(),
                'motion_system': self._generate_motion_data()
            }
            
            # 发射数据更新信号
            self.data_updated.emit(data)
            
            # 随机生成警报
            if random.random() < 0.05:  # 5% 几率生成警报
                system = random.choice(['blood_system', 'skin_system', 'vision_system', 
                                      'ai_system', 'language_system', 'motion_system'])
                level = random.randint(1, 3)  # 1: 警告, 2: 严重, 3: 紧急
                message = f"系统 {system} 检测到异常状态"
                self.system_alert.emit(system, level, message)
                self.db_manager.log_alert(system, level, message)
            
            self.msleep(1000)  # 1秒更新间隔
            counter += 1
    
    def _generate_blood_data(self):
        return BloodSystemData(
            energy_level=80 + 20 * random.random(),
            flow_rate=60 + 30 * random.random(),
            temperature=35 + 10 * random.random(),
            pressure=100 + 40 * random.random(),
            oxygen_level=90 + 10 * random.random(),
            waste_level=10 + 20 * random.random(),
            pump_speed=1000 + 1000 * random.random(),
            cooling_status=random.random() > 0.1
        )
    
    def _generate_skin_data(self):
        return SkinSystemData(
            chemical_sensitivity=80 + 15 * random.random(),
            tactile_sensitivity=85 + 10 * random.random(),
            temperature_sensitivity=80 + 15 * random.random(),
            humidity_sensitivity=70 + 25 * random.random(),
            pressure_sensitivity=85 + 10 * random.random(),
            neural_processing_load=30 + 50 * random.random(),
            reaction_time=10 + 10 * random.random(),
            pattern_recognition_rate=95 + 5 * random.random()
        )
    
    def _generate_vision_data(self):
        return VisionSystemData(
            processing_fps=50 + 30 * random.random(),
            object_detection_accuracy=90 + 10 * random.random(),
            depth_perception_accuracy=90 + 10 * random.random(),
            low_light_performance=80 + 20 * random.random(),
            motion_tracking_accuracy=95 + 5 * random.random()
        )
    
    def _generate_ai_data(self):
        return AISystemData(
            neural_network_load=40 + 50 * random.random(),
            inference_speed=200 + 100 * random.random(),
            learning_rate=0.001,
            memory_usage=60 + 30 * random.random(),
            training_progress=30 + 50 * random.random()
        )
    
    def _generate_language_data(self):
        return LanguageSystemData(
            response_time=80 + 20 * random.random(),
            speech_recognition_accuracy=90 + 10 * random.random(),
            language_translation_accuracy=85 + 15 * random.random(),
            contextual_understanding=85 + 15 * random.random(),
            emotion_recognition=80 + 20 * random.random()
        )
    
    def _generate_motion_data(self):
        return MotionSystemData(
            hydraulic_pressure=70 + 25 * random.random(),
            joint_flexibility=80 + 15 * random.random(),
            power_efficiency=85 + 15 * random.random(),
            balance_stability=90 + 10 * random.random(),
            movement_precision=90 + 10 * random.random()
        )
    
    def stop(self):
        self.running = False
        self.wait()

# 自定义控件
class SystemIndicator(QWidget):
    def __init__(self, system_name, parent=None):
        super().__init__(parent)
        self.system_name = system_name
        self.status = SystemStatus.STANDBY
        self.value = 0
        self.setMinimumSize(120, 80)
        self.setMaximumSize(120, 80)
        
    def set_status(self, status, value):
        self.status = status
        self.value = value
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 根据状态设置颜色
        if self.status == SystemStatus.OFFLINE:
            color = QColor(100, 100, 100)
        elif self.status == SystemStatus.STANDBY:
            color = QColor(255, 255, 0)
        elif self.status == SystemStatus.OPERATIONAL:
            color = QColor(0, 255, 0)
        elif self.status == SystemStatus.WARNING:
            color = QColor(255, 165, 0)
        elif self.status == SystemStatus.CRITICAL:
            color = QColor(255, 0, 0)
        else:  # EMERGENCY
            color = QColor(255, 0, 0)
            
        # 绘制背景
        gradient = QLinearGradient(0, 0, self.width(), 0)
        gradient.setColorAt(0, QColor(40, 40, 40))
        gradient.setColorAt(1, QColor(70, 70, 70))
        painter.fillRect(self.rect(), gradient)
        
        # 绘制状态圆
        center_x = self.width() // 2
        center_y = self.height() // 3
        radius = 15
        
        painter.setBrush(QBrush(color))
        painter.setPen(QPen(QColor(200, 200, 200), 2))
        painter.drawEllipse(center_x - radius, center_y - radius, radius * 2, radius * 2)
        
        # 绘制文本
        painter.setPen(QColor(255, 255, 255))
        font = QFont("Arial", 8, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(0, self.height() - 20, self.width(), 20, 
                        Qt.AlignmentFlag.AlignCenter, self.system_name)
        
        # 绘制数值
        value_font = QFont("Arial", 9)
        painter.setFont(value_font)
        painter.drawText(0, self.height() - 40, self.width(), 20,
                        Qt.AlignmentFlag.AlignCenter, f"{self.value:.1f}%")

class RealTimeChart(QChartView):
    def __init__(self, title, series_count=1, parent=None):
        super().__init__(parent)
        self.chart = QChart()
        self.chart.setTitle(title)
        self.chart.legend().setVisible(True)
        self.chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
        self.setChart(self.chart)
        
        self.series = []
        self.colors = [
            QColor(255, 0, 0),    # 红色
            QColor(0, 255, 0),    # 绿色
            QColor(0, 0, 255),    # 蓝色
            QColor(255, 255, 0),  # 黄色
            QColor(255, 0, 255),  # 紫色
        ]
        
        for i in range(series_count):
            series = QSplineSeries()
            series.setName(f"Series {i+1}")
            series.setColor(self.colors[i % len(self.colors)])
            self.series.append(series)
            self.chart.addSeries(series)
        
        # 设置坐标轴
        self.axis_x = QValueAxis()
        self.axis_x.setTitleText("时间")
        self.axis_x.setRange(0, 100)
        self.axis_x.setLabelFormat("%d")
        
        self.axis_y = QValueAxis()
        self.axis_y.setTitleText("数值")
        self.axis_y.setRange(0, 100)
        
        self.chart.addAxis(self.axis_x, Qt.AlignmentFlag.AlignBottom)
        self.chart.addAxis(self.axis_y, Qt.AlignmentFlag.AlignLeft)
        
        for series in self.series:
            series.attachAxis(self.axis_x)
            series.attachAxis(self.axis_y)
        
        self.data_points = 0
        self.max_points = 100
        
    def add_data_points(self, *values):
        for i, value in enumerate(values):
            if i < len(self.series):
                self.series[i].append(QPointF(self.data_points, value))
        
        # 限制数据点数量
        if self.data_points > self.max_points:
            for series in self.series:
                if series.count() > 0:
                    series.remove(0)
            self.axis_x.setRange(self.data_points - self.max_points, self.data_points)
        else:
            self.axis_x.setRange(0, self.max_points)
            
        self.data_points += 1

class MatplotlibChart(FigureCanvas):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        super().__init__(self.fig)
        self.setParent(parent)
        
        self.axes = self.fig.add_subplot(111)
        self.fig.tight_layout()
        
    def plot_data(self, x_data, y_data, title="", xlabel="", ylabel="", legend=None):
        self.axes.clear()
        
        if isinstance(y_data[0], (list, tuple)):
            for i, y in enumerate(y_data):
                label = legend[i] if legend and i < len(legend) else f"Series {i+1}"
                self.axes.plot(x_data, y, label=label)
            self.axes.legend()
        else:
            self.axes.plot(x_data, y_data)
            
        self.axes.set_title(title)
        self.axes.set_xlabel(xlabel)
        self.axes.set_ylabel(ylabel)
        self.axes.grid(True, alpha=0.3)
        
        self.draw()

# 系统面板类
class BloodSystemPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.data = BloodSystemData()
        self.init_ui()
        
    def init_ui(self):
        main_layout = QHBoxLayout()
        
        # 左侧 - 状态显示
        left_widget = QWidget()
        left_layout = QVBoxLayout()
        
        # 能量循环状态
        energy_group = QGroupBox("能量循环状态")
        energy_layout = QGridLayout()
        
        self.energy_level = QProgressBar()
        self.energy_level.setFormat("能量水平: %p%")
        
        self.flow_rate = QProgressBar()
        self.flow_rate.setFormat("循环流速: %p%")
        
        self.temperature = QProgressBar()
        self.temperature.setFormat("系统温度: %p%")
        
        self.pressure = QProgressBar()
        self.pressure.setFormat("液压压力: %p%")
        
        self.oxygen_level = QProgressBar()
        self.oxygen_level.setFormat("氧合水平: %p%")
        
        self.waste_level = QProgressBar()
        self.waste_level.setFormat("废物浓度: %p%")
        
        energy_layout.addWidget(QLabel("液态电池状态:"), 0, 0)
        energy_layout.addWidget(self.energy_level, 0, 1)
        energy_layout.addWidget(QLabel("循环网络:"), 1, 0)
        energy_layout.addWidget(self.flow_rate, 1, 1)
        energy_layout.addWidget(QLabel("热管理:"), 2, 0)
        energy_layout.addWidget(self.temperature, 2, 1)
        energy_layout.addWidget(QLabel("系统压力:"), 3, 0)
        energy_layout.addWidget(self.pressure, 3, 1)
        energy_layout.addWidget(QLabel("气体交换:"), 4, 0)
        energy_layout.addWidget(self.oxygen_level, 4, 1)
        energy_layout.addWidget(QLabel("废物处理:"), 5, 0)
        energy_layout.addWidget(self.waste_level, 5, 1)
        
        energy_group.setLayout(energy_layout)
        
        # 实时图表
        self.blood_chart = RealTimeChart("血液系统参数趋势", 3)
        
        left_layout.addWidget(energy_group)
        left_layout.addWidget(self.blood_chart)
        left_widget.setLayout(left_layout)
        
        # 右侧 - 控制面板
        right_widget = QWidget()
        right_layout = QVBoxLayout()
        
        # 泵控制
        pump_group = QGroupBox("循环泵控制")
        pump_layout = QFormLayout()
        
        self.pump_speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.pump_speed_slider.setRange(500, 3000)
        self.pump_speed_slider.setValue(1500)
        
        self.pump_speed_label = QLabel("1500 RPM")
        
        self.pump_power_slider = QSlider(Qt.Orientation.Horizontal)
        self.pump_power_slider.setRange(0, 100)
        self.pump_power_slider.setValue(70)
        
        self.pump_power_label = QLabel("70%")
        
        pump_layout.addRow("泵转速:", self.pump_speed_slider)
        pump_layout.addRow("", self.pump_speed_label)
        pump_layout.addRow("泵功率:", self.pump_power_slider)
        pump_layout.addRow("", self.pump_power_label)
        pump_group.setLayout(pump_layout)
        
        # 温度控制
        temp_group = QGroupBox("温度管理")
        temp_layout = QFormLayout()
        
        self.cooling_btn = QPushButton("激活主动冷却")
        self.cooling_btn.setCheckable(True)
        self.cooling_btn.setChecked(True)
        
        self.temp_target = QDoubleSpinBox()
        self.temp_target.setRange(20.0, 50.0)
        self.temp_target.setValue(37.5)
        self.temp_target.setSuffix(" °C")
        
        temp_layout.addRow("目标温度:", self.temp_target)
        temp_layout.addRow(self.cooling_btn)
        temp_group.setLayout(temp_layout)
        
        # 能量管理
        energy_control_group = QGroupBox("能量管理")
        energy_control_layout = QVBoxLayout()
        
        self.energy_boost_btn = QPushButton("能量增压模式")
        self.energy_conserve_btn = QPushButton("节能模式")
        self.auto_optimize_btn = QPushButton("自动优化")
        
        energy_control_layout.addWidget(self.energy_boost_btn)
        energy_control_layout.addWidget(self.energy_conserve_btn)
        energy_control_layout.addWidget(self.auto_optimize_btn)
        energy_control_group.setLayout(energy_control_layout)
        
        right_layout.addWidget(pump_group)
        right_layout.addWidget(temp_group)
        right_layout.addWidget(energy_control_group)
        right_layout.addStretch()
        right_widget.setLayout(right_layout)
        
        # 连接信号
        self.pump_speed_slider.valueChanged.connect(self.update_pump_speed)
        self.pump_power_slider.valueChanged.connect(self.update_pump_power)
        
        main_layout.addWidget(left_widget)
        main_layout.addWidget(right_widget)
        self.setLayout(main_layout)
    
    def update_data(self, data: BloodSystemData):
        self.data = data
        self.energy_level.setValue(int(data.energy_level))
        self.flow_rate.setValue(int(data.flow_rate))
        self.temperature.setValue(int(data.temperature))
        self.pressure.setValue(int(data.pressure))
        self.oxygen_level.setValue(int(data.oxygen_level))
        self.waste_level.setValue(int(data.waste_level))
        
        # 更新图表
        self.blood_chart.add_data_points(
            data.energy_level, 
            data.flow_rate, 
            data.temperature
        )
    
    def update_pump_speed(self, value):
        self.pump_speed_label.setText(f"{value} RPM")
    
    def update_pump_power(self, value):
        self.pump_power_label.setText(f"{value}%")

class SkinSystemPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.data = SkinSystemData()
        self.init_ui()
        
    def init_ui(self):
        main_layout = QHBoxLayout()
        
        # 左侧 - 感知状态
        left_widget = QWidget()
        left_layout = QVBoxLayout()
        
        # 多模态感知状态
        sense_group = QGroupBox("多模态感知状态")
        sense_layout = QGridLayout()
        
        self.chemical_sense = QProgressBar()
        self.chemical_sense.setFormat("化学感知: %p%")
        
        self.tactile_sense = QProgressBar()
        self.tactile_sense.setFormat("触觉感知: %p%")
        
        self.temp_sense = QProgressBar()
        self.temp_sense.setFormat("温度感知: %p%")
        
        self.humidity_sense = QProgressBar()
        self.humidity_sense.setFormat("湿度感知: %p%")
        
        self.pressure_sense = QProgressBar()
        self.pressure_sense.setFormat("压力感知: %p%")
        
        sense_layout.addWidget(self.chemical_sense, 0, 0)
        sense_layout.addWidget(self.tactile_sense, 0, 1)
        sense_layout.addWidget(self.temp_sense, 1, 0)
        sense_layout.addWidget(self.humidity_sense, 1, 1)
        sense_layout.addWidget(self.pressure_sense, 2, 0)
        
        sense_group.setLayout(sense_layout)
        
        # 神经形态计算
        neuro_group = QGroupBox("神经形态计算")
        neuro_layout = QGridLayout()
        
        self.process_load = QProgressBar()
        self.process_load.setFormat("处理负载: %p%")
        
        self.reaction_time = QLabel("反应延迟: -- ms")
        self.pattern_recognition = QLabel("模式识别: --%")
        self.neural_efficiency = QLabel("计算效率: --%")
        
        neuro_layout.addWidget(QLabel("处理负载:"), 0, 0)
        neuro_layout.addWidget(self.process_load, 0, 1)
        neuro_layout.addWidget(self.reaction_time, 1, 0, 1, 2)
        neuro_layout.addWidget(self.pattern_recognition, 2, 0, 1, 2)
        neuro_layout.addWidget(self.neural_efficiency, 3, 0, 1, 2)
        
        neuro_group.setLayout(neuro_layout)
        
        # 感知图表
        self.skin_chart = RealTimeChart("感知系统性能趋势", 3)
        
        left_layout.addWidget(sense_group)
        left_layout.addWidget(neuro_group)
        left_layout.addWidget(self.skin_chart)
        left_widget.setLayout(left_layout)
        
        # 右侧 - 控制面板
        right_widget = QWidget()
        right_layout = QVBoxLayout()
        
        # 感知控制
        control_group = QGroupBox("感知控制")
        control_layout = QFormLayout()
        
        self.sensitivity = QSlider(Qt.Orientation.Horizontal)
        self.sensitivity.setRange(0, 100)
        self.sensitivity.setValue(75)
        
        self.chem_filter = QComboBox()
        self.chem_filter.addItems(["全谱感知", "危险品检测", "环境监测", "医疗诊断", "食品分析"])
        
        self.neural_mode = QComboBox()
        self.neural_mode.addItems(["高性能模式", "节能模式", "学习模式", "诊断模式"])
        
        control_layout.addRow("全局灵敏度:", self.sensitivity)
        control_layout.addRow("化学过滤器:", self.chem_filter)
        control_layout.addRow("神经模式:", self.neural_mode)
        control_group.setLayout(control_layout)
        
        # 校准面板
        calibrate_group = QGroupBox("系统校准")
        calibrate_layout = QVBoxLayout()
        
        self.auto_calibrate_btn = QPushButton("自动校准")
        self.manual_calibrate_btn = QPushButton("手动校准")
        self.sensor_test_btn = QPushButton("传感器测试")
        
        calibrate_layout.addWidget(self.auto_calibrate_btn)
        calibrate_layout.addWidget(self.manual_calibrate_btn)
        calibrate_layout.addWidget(self.sensor_test_btn)
        calibrate_group.setLayout(calibrate_layout)
        
        # 数据分析
        analysis_group = QGroupBox("感知数据分析")
        analysis_layout = QVBoxLayout()
        
        self.pattern_analysis_btn = QPushButton("模式分析")
        self.chemical_analysis_btn = QPushButton("化学分析")
        self.environment_report_btn = QPushButton("环境报告")
        
        analysis_layout.addWidget(self.pattern_analysis_btn)
        analysis_layout.addWidget(self.chemical_analysis_btn)
        analysis_layout.addWidget(self.environment_report_btn)
        analysis_group.setLayout(analysis_layout)
        
        right_layout.addWidget(control_group)
        right_layout.addWidget(calibrate_group)
        right_layout.addWidget(analysis_group)
        right_layout.addStretch()
        right_widget.setLayout(right_layout)
        
        main_layout.addWidget(left_widget)
        main_layout.addWidget(right_widget)
        self.setLayout(main_layout)
    
    def update_data(self, data: SkinSystemData):
        self.data = data
        self.chemical_sense.setValue(int(data.chemical_sensitivity))
        self.tactile_sense.setValue(int(data.tactile_sensitivity))
        self.temp_sense.setValue(int(data.temperature_sensitivity))
        self.humidity_sense.setValue(int(data.humidity_sensitivity))
        self.pressure_sense.setValue(int(data.pressure_sensitivity))
        self.process_load.setValue(int(data.neural_processing_load))
        self.reaction_time.setText(f"反应延迟: {data.reaction_time:.1f} ms")
        self.pattern_recognition.setText(f"模式识别: {data.pattern_recognition_rate:.1f}%")
        self.neural_efficiency.setText(f"计算效率: {100 - data.neural_processing_load:.1f}%")
        
        # 更新图表
        self.skin_chart.add_data_points(
            data.chemical_sensitivity,
            data.tactile_sensitivity,
            data.neural_processing_load
        )

# 其他系统面板（简化实现）
class VisionSystemPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.data = VisionSystemData()
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 视觉处理状态
        processing_group = QGroupBox("视觉处理状态")
        processing_layout = QGridLayout()
        
        self.processing_rate = QProgressBar()
        self.processing_rate.setFormat("处理帧率: %p FPS")
        
        self.object_detection = QLabel("目标检测准确率: --%")
        self.depth_perception = QLabel("深度感知准确率: --%")
        self.low_light_performance = QLabel("低光性能: --%")
        self.motion_tracking = QLabel("运动跟踪准确率: --%")
        
        processing_layout.addWidget(QLabel("处理性能:"), 0, 0)
        processing_layout.addWidget(self.processing_rate, 0, 1)
        processing_layout.addWidget(self.object_detection, 1, 0, 1, 2)
        processing_layout.addWidget(self.depth_perception, 2, 0, 1, 2)
        processing_layout.addWidget(self.low_light_performance, 3, 0, 1, 2)
        processing_layout.addWidget(self.motion_tracking, 4, 0, 1, 2)
        
        processing_group.setLayout(processing_layout)
        
        # 视觉图表
        self.vision_chart = RealTimeChart("视觉系统性能", 2)
        
        layout.addWidget(processing_group)
        layout.addWidget(self.vision_chart)
        self.setLayout(layout)
    
    def update_data(self, data: VisionSystemData):
        self.data = data
        self.processing_rate.setValue(int(data.processing_fps))
        self.object_detection.setText(f"目标检测准确率: {data.object_detection_accuracy:.1f}%")
        self.depth_perception.setText(f"深度感知准确率: {data.depth_perception_accuracy:.1f}%")
        self.low_light_performance.setText(f"低光性能: {data.low_light_performance:.1f}%")
        self.motion_tracking.setText(f"运动跟踪准确率: {data.motion_tracking_accuracy:.1f}%")
        
        self.vision_chart.add_data_points(
            data.processing_fps,
            data.object_detection_accuracy
        )

class AISystemPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.data = AISystemData()
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # AI状态
        ai_group = QGroupBox("神经网络状态")
        ai_layout = QGridLayout()
        
        self.neural_load = QProgressBar()
        self.neural_load.setFormat("神经网络负载: %p%")
        
        self.inference_speed = QLabel("推理速度: -- FPS")
        self.learning_rate = QLabel("学习速率: --")
        self.memory_usage = QLabel("内存使用: --%")
        self.training_progress = QLabel("训练进度: --%")
        
        ai_layout.addWidget(QLabel("网络负载:"), 0, 0)
        ai_layout.addWidget(self.neural_load, 0, 1)
        ai_layout.addWidget(self.inference_speed, 1, 0, 1, 2)
        ai_layout.addWidget(self.learning_rate, 2, 0, 1, 2)
        ai_layout.addWidget(self.memory_usage, 3, 0, 1, 2)
        ai_layout.addWidget(self.training_progress, 4, 0, 1, 2)
        
        ai_group.setLayout(ai_layout)
        
        # AI图表
        self.ai_chart = RealTimeChart("AI系统性能", 3)
        
        layout.addWidget(ai_group)
        layout.addWidget(self.ai_chart)
        self.setLayout(layout)
    
    def update_data(self, data: AISystemData):
        self.data = data
        self.neural_load.setValue(int(data.neural_network_load))
        self.inference_speed.setText(f"推理速度: {data.inference_speed:.0f} FPS")
        self.learning_rate.setText(f"学习速率: {data.learning_rate}")
        self.memory_usage.setText(f"内存使用: {data.memory_usage:.1f}%")
        self.training_progress.setText(f"训练进度: {data.training_progress:.1f}%")
        
        self.ai_chart.add_data_points(
            data.neural_network_load,
            data.memory_usage,
            data.training_progress
        )

class LanguageSystemPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.data = LanguageSystemData()
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 语言处理状态
        language_group = QGroupBox("语言处理状态")
        language_layout = QGridLayout()
        
        self.response_time = QProgressBar()
        self.response_time.setFormat("响应时间: %p ms")
        
        self.speech_recognition = QLabel("语音识别准确率: --%")
        self.translation_accuracy = QLabel("翻译准确率: --%")
        self.context_understanding = QLabel("上下文理解: --%")
        self.emotion_recognition = QLabel("情感识别: --%")
        
        language_layout.addWidget(QLabel("响应性能:"), 0, 0)
        language_layout.addWidget(self.response_time, 0, 1)
        language_layout.addWidget(self.speech_recognition, 1, 0, 1, 2)
        language_layout.addWidget(self.translation_accuracy, 2, 0, 1, 2)
        language_layout.addWidget(self.context_understanding, 3, 0, 1, 2)
        language_layout.addWidget(self.emotion_recognition, 4, 0, 1, 2)
        
        language_group.setLayout(language_layout)
        
        # 对话界面
        conversation_group = QGroupBox("对话系统")
        conversation_layout = QVBoxLayout()
        
        self.conversation_log = QTextEdit()
        self.conversation_log.setMaximumHeight(200)
        
        input_layout = QHBoxLayout()
        self.input_field = QLineEdit()
        self.send_btn = QPushButton("发送")
        
        input_layout.addWidget(self.input_field)
        input_layout.addWidget(self.send_btn)
        
        conversation_layout.addWidget(self.conversation_log)
        conversation_layout.addLayout(input_layout)
        conversation_group.setLayout(conversation_layout)
        
        layout.addWidget(language_group)
        layout.addWidget(conversation_group)
        self.setLayout(layout)
        
        # 初始对话
        self.conversation_log.append("系统: 语言系统已就绪，等待输入...")
    
    def update_data(self, data: LanguageSystemData):
        self.data = data
        self.response_time.setValue(int(data.response_time))
        self.speech_recognition.setText(f"语音识别准确率: {data.speech_recognition_accuracy:.1f}%")
        self.translation_accuracy.setText(f"翻译准确率: {data.language_translation_accuracy:.1f}%")
        self.context_understanding.setText(f"上下文理解: {data.contextual_understanding:.1f}%")
        self.emotion_recognition.setText(f"情感识别: {data.emotion_recognition:.1f}%")

class MotionSystemPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.data = MotionSystemData()
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 运动状态
        motion_group = QGroupBox("运动系统状态")
        motion_layout = QGridLayout()
        
        self.hydraulic_pressure = QProgressBar()
        self.hydraulic_pressure.setFormat("液压压力: %p%")
        
        self.joint_flexibility = QLabel("关节柔顺度: --%")
        self.power_efficiency = QLabel("能量效率: --%")
        self.balance_stability = QLabel("平衡稳定性: --%")
        self.movement_precision = QLabel("运动精度: --%")
        
        motion_layout.addWidget(QLabel("液压系统:"), 0, 0)
        motion_layout.addWidget(self.hydraulic_pressure, 0, 1)
        motion_layout.addWidget(self.joint_flexibility, 1, 0, 1, 2)
        motion_layout.addWidget(self.power_efficiency, 2, 0, 1, 2)
        motion_layout.addWidget(self.balance_stability, 3, 0, 1, 2)
        motion_layout.addWidget(self.movement_precision, 4, 0, 1, 2)
        
        motion_group.setLayout(motion_layout)
        
        # 运动图表
        self.motion_chart = RealTimeChart("运动系统性能", 3)
        
        layout.addWidget(motion_group)
        layout.addWidget(self.motion_chart)
        self.setLayout(layout)
    
    def update_data(self, data: MotionSystemData):
        self.data = data
        self.hydraulic_pressure.setValue(int(data.hydraulic_pressure))
        self.joint_flexibility.setText(f"关节柔顺度: {data.joint_flexibility:.1f}%")
        self.power_efficiency.setText(f"能量效率: {data.power_efficiency:.1f}%")
        self.balance_stability.setText(f"平衡稳定性: {data.balance_stability:.1f}%")
        self.movement_precision.setText(f"运动精度: {data.movement_precision:.1f}%")
        
        self.motion_chart.add_data_points(
            data.hydraulic_pressure,
            data.joint_flexibility,
            data.power_efficiency
        )

# 警报管理面板
class AlertPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.db_manager = DatabaseManager()
        self.init_ui()
        self.load_alerts()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 警报工具栏
        toolbar = QHBoxLayout()
        self.refresh_btn = QPushButton("刷新")
        self.clear_btn = QPushButton("清除已确认")
        self.export_btn = QPushButton("导出报告")
        
        toolbar.addWidget(self.refresh_btn)
        toolbar.addWidget(self.clear_btn)
        toolbar.addWidget(self.export_btn)
        toolbar.addStretch()
        
        # 警报表格
        self.alert_table = QTableWidget()
        self.alert_table.setColumnCount(5)
        self.alert_table.setHorizontalHeaderLabels([
            "时间", "系统", "级别", "消息", "状态"
        ])
        self.alert_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        
        layout.addLayout(toolbar)
        layout.addWidget(self.alert_table)
        
        self.setLayout(layout)
        
        # 连接信号
        self.refresh_btn.clicked.connect(self.load_alerts)
        self.clear_btn.clicked.connect(self.clear_acknowledged)
    
    def load_alerts(self):
        alerts = self.db_manager.get_recent_alerts(100)
        self.alert_table.setRowCount(len(alerts))
        
        for row, alert in enumerate(alerts):
            alert_id, timestamp, system, level, message, acknowledged = alert
            
            # 设置级别显示
            level_text = ""
            if level == 1:
                level_text = "警告"
            elif level == 2:
                level_text = "严重"
            else:
                level_text = "紧急"
            
            # 设置状态显示
            status_text = "已确认" if acknowledged else "待处理"
            
            self.alert_table.setItem(row, 0, QTableWidgetItem(timestamp))
            self.alert_table.setItem(row, 1, QTableWidgetItem(system))
            self.alert_table.setItem(row, 2, QTableWidgetItem(level_text))
            self.alert_table.setItem(row, 3, QTableWidgetItem(message))
            self.alert_table.setItem(row, 4, QTableWidgetItem(status_text))
    
    def clear_acknowledged(self):
        # 实现清除已确认警报的逻辑
        pass
    
    def add_alert(self, system, level, message):
        self.db_manager.log_alert(system, level, message)
        self.load_alerts()

# 系统配置面板
class ConfigPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 系统设置
        system_group = QGroupBox("系统设置")
        system_layout = QFormLayout()
        
        self.robot_name = QLineEdit("未来机器人 v2.0")
        self.operation_mode = QComboBox()
        self.operation_mode.addItems(["自动模式", "手动模式", "诊断模式", "维护模式"])
        
        self.safety_protocol = QCheckBox("启用安全协议")
        self.safety_protocol.setChecked(True)
        
        self.auto_backup = QCheckBox("自动数据备份")
        self.auto_backup.setChecked(True)
        
        system_layout.addRow("机器人名称:", self.robot_name)
        system_layout.addRow("操作模式:", self.operation_mode)
        system_layout.addRow(self.safety_protocol)
        system_layout.addRow(self.auto_backup)
        
        system_group.setLayout(system_layout)
        
        # 性能设置
        performance_group = QGroupBox("性能设置")
        performance_layout = QFormLayout()
        
        self.max_power = QSlider(Qt.Orientation.Horizontal)
        self.max_power.setRange(0, 100)
        self.max_power.setValue(80)
        
        self.response_priority = QComboBox()
        self.response_priority.addItems(["安全性优先", "性能优先", "平衡模式"])
        
        self.learning_enabled = QCheckBox("启用在线学习")
        self.learning_enabled.setChecked(True)
        
        performance_layout.addRow("最大功率:", self.max_power)
        performance_layout.addRow("响应优先级:", self.response_priority)
        performance_layout.addRow(self.learning_enabled)
        
        performance_group.setLayout(performance_layout)
        
        # 保存按钮
        save_btn = QPushButton("保存配置")
        
        layout.addWidget(system_group)
        layout.addWidget(performance_group)
        layout.addWidget(save_btn)
        layout.addStretch()
        
        self.setLayout(layout)

# 主界面
class FutureRobotControl(QMainWindow):
    def __init__(self):
        super().__init__()
        self.data_collector = DataCollectionThread()
        self.db_manager = DatabaseManager()
        self.current_data = {}
        self.init_ui()
        self.setup_connections()
        self.data_collector.start()
        
    def init_ui(self):
        self.setWindowTitle("未来机器人集成控制系统 - 机体系统 v2.0")
        self.setGeometry(100, 100, 1600, 1000)
        
        # 设置深色主题
        self.set_dark_theme()
        
        # 创建菜单栏
        self.create_menu_bar()
        
        # 创建工具栏
        self.create_tool_bar()
        
        # 创建状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("系统就绪")
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # 顶部状态栏
        top_layout = QHBoxLayout()
        self.system_indicators = {}
        
        systems = [
            ("视觉系统", SystemStatus.OPERATIONAL),
            ("AI大脑", SystemStatus.OPERATIONAL),
            ("语言模型", SystemStatus.OPERATIONAL),
            ("循环网络", SystemStatus.OPERATIONAL),
            ("运动系统", SystemStatus.OPERATIONAL),
            ("感知皮肤", SystemStatus.OPERATIONAL)
        ]
        
        for system_name, initial_status in systems:
            indicator = SystemIndicator(system_name)
            indicator.set_status(initial_status, 85.0)
            self.system_indicators[system_name] = indicator
            top_layout.addWidget(indicator)
            
        main_layout.addLayout(top_layout)
        
        # 创建标签页
        self.tabs = QTabWidget()
        
        # 血液系统标签页
        self.blood_tab = BloodSystemPanel()
        self.tabs.addTab(self.blood_tab, "🩸 循环功能网络")
        
        # 皮肤系统标签页
        self.skin_tab = SkinSystemPanel()
        self.tabs.addTab(self.skin_tab, "👃 分布式感知皮肤")
        
        # 视觉系统标签页
        self.vision_tab = VisionSystemPanel()
        self.tabs.addTab(self.vision_tab, "👁️ 机器视觉")
        
        # AI系统标签页
        self.ai_tab = AISystemPanel()
        self.tabs.addTab(self.ai_tab, "🧠 神经网络")
        
        # 语言系统标签页
        self.language_tab = LanguageSystemPanel()
        self.tabs.addTab(self.language_tab, "🗣️ 大语言模型")
        
        # 运动系统标签页
        self.motion_tab = MotionSystemPanel()
        self.tabs.addTab(self.motion_tab, "🤖 液压运动系统")
        
        # 警报管理标签页
        self.alert_tab = AlertPanel()
        self.tabs.addTab(self.alert_tab, "🚨 警报管理")
        
        # 系统配置标签页
        self.config_tab = ConfigPanel()
        self.tabs.addTab(self.config_tab, "⚙️ 系统配置")
        
        main_layout.addWidget(self.tabs)
        
        # 添加系统启动日志
        self.log_message("系统启动: 未来机器人机体系统初始化完成")
        self.log_message("循环功能网络: 液态电池在线, 液压系统加压中")
        self.log_message("分布式感知皮肤: 神经形态芯片激活, 多模态传感器校准")
        self.log_message("系统集成: 各子系统协同运行模式启动")
        
    def create_menu_bar(self):
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu('文件')
        
        new_action = QAction('新建', self)
        save_action = QAction('保存', self)
        export_action = QAction('导出报告', self)
        exit_action = QAction('退出', self)
        
        file_menu.addAction(new_action)
        file_menu.addAction(save_action)
        file_menu.addAction(export_action)
        file_menu.addSeparator()
        file_menu.addAction(exit_action)
        
        # 视图菜单
        view_menu = menubar.addMenu('视图')
        dashboard_action = QAction('仪表盘', self)
        alerts_action = QAction('警报中心', self)
        reports_action = QAction('性能报告', self)
        
        view_menu.addAction(dashboard_action)
        view_menu.addAction(alerts_action)
        view_menu.addAction(reports_action)
        
        # 工具菜单
        tools_menu = menubar.addMenu('工具')
        calibrate_action = QAction('系统校准', self)
        diagnostics_action = QAction('系统诊断', self)
        maintenance_action = QAction('维护工具', self)
        
        tools_menu.addAction(calibrate_action)
        tools_menu.addAction(diagnostics_action)
        tools_menu.addAction(maintenance_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu('帮助')
        about_action = QAction('关于', self)
        docs_action = QAction('文档', self)
        
        help_menu.addAction(about_action)
        help_menu.addAction(docs_action)
    
    def create_tool_bar(self):
        toolbar = QToolBar("主工具栏")
        self.addToolBar(toolbar)
        
        # 系统控制按钮
        start_btn = QToolButton()
        start_btn.setText("启动系统")
        start_btn.setCheckable(True)
        
        stop_btn = QToolButton()
        stop_btn.setText("停止系统")
        
        emergency_btn = QToolButton()
        emergency_btn.setText("紧急停止")
        emergency_btn.setStyleSheet("background-color: red; color: white;")
        
        toolbar.addWidget(start_btn)
        toolbar.addWidget(stop_btn)
        toolbar.addWidget(emergency_btn)
        toolbar.addSeparator()
        
        # 模式选择
        mode_combo = QComboBox()
        mode_combo.addItems(["自动模式", "手动模式", "诊断模式", "训练模式"])
        toolbar.addWidget(QLabel("操作模式:"))
        toolbar.addWidget(mode_combo)
        
    def set_dark_theme(self):
        """设置深色主题"""
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(30, 30, 30))
        palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.Base, QColor(25, 25, 25))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(35, 35, 35))
        palette.setColor(QPalette.ColorRole.ToolTipBase, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.ToolTipText, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.Button, QColor(50, 50, 50))
        palette.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.Highlight, QColor(142, 45, 197).lighter())
        palette.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.black)
        self.setPalette(palette)
        
    def setup_connections(self):
        """连接信号和槽"""
        self.data_collector.data_updated.connect(self.handle_data_update)
        self.data_collector.system_alert.connect(self.handle_system_alert)
        
    def handle_data_update(self, data):
        """处理数据更新"""
        self.current_data = data
        
        # 更新各系统面板
        if 'blood_system' in data:
            self.blood_tab.update_data(data['blood_system'])
            
        if 'skin_system' in data:
            self.skin_tab.update_data(data['skin_system'])
            
        if 'vision_system' in data:
            self.vision_tab.update_data(data['vision_system'])
            
        if 'ai_system' in data:
            self.ai_tab.update_data(data['ai_system'])
            
        if 'language_system' in data:
            self.language_tab.update_data(data['language_system'])
            
        if 'motion_system' in data:
            self.motion_tab.update_data(data['motion_system'])
        
        # 更新系统指示器
        self.update_system_indicators(data)
        
        # 更新状态栏
        timestamp = data['timestamp'].strftime("%Y-%m-%d %H:%M:%S")
        self.status_bar.showMessage(f"系统运行正常 - 最后更新: {timestamp}")
    
    def update_system_indicators(self, data):
        """更新系统状态指示器"""
        system_mapping = {
            '视觉系统': ('vision_system', 'processing_fps'),
            'AI大脑': ('ai_system', 'neural_network_load'),
            '语言模型': ('language_system', 'response_time'),
            '循环网络': ('blood_system', 'energy_level'),
            '运动系统': ('motion_system', 'power_efficiency'),
            '感知皮肤': ('skin_system', 'pattern_recognition_rate')
        }
        
        for display_name, (system_key, metric_key) in system_mapping.items():
            if system_key in data and hasattr(data[system_key], metric_key):
                value = getattr(data[system_key], metric_key)
                status = SystemStatus.OPERATIONAL
                
                # 根据数值确定状态
                if value < 50:
                    status = SystemStatus.WARNING
                elif value < 30:
                    status = SystemStatus.CRITICAL
                    
                self.system_indicators[display_name].set_status(status, value)
    
    def handle_system_alert(self, system, level, message):
        """处理系统警报"""
        # 显示警报对话框
        alert_levels = {1: "警告", 2: "严重", 3: "紧急"}
        
        msg_box = QMessageBox()
        msg_box.setWindowTitle(f"系统警报 - {alert_levels.get(level, '未知')}")
        msg_box.setText(f"系统: {system}\n级别: {alert_levels.get(level, '未知')}\n消息: {message}")
        
        if level == 3:  # 紧急警报
            msg_box.setIcon(QMessageBox.Icon.Critical)
        elif level == 2:  # 严重警报
            msg_box.setIcon(QMessageBox.Icon.Warning)
        else:  # 警告
            msg_box.setIcon(QMessageBox.Icon.Information)
            
        msg_box.exec()
        
        # 记录警报
        self.log_message(f"警报: {system} - {message}")
        
        # 更新警报面板
        self.alert_tab.add_alert(system, level, message)
    
    def log_message(self, message):
        """记录系统消息"""
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        # 这里可以实现日志记录到文件或数据库
        print(f"[{timestamp}] {message}")
    
    def closeEvent(self, event):
        """应用程序关闭事件"""
        reply = QMessageBox.question(self, '确认退出',
                                   '确定要退出未来机器人控制系统吗？',
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                   QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            # 停止数据采集线程
            self.data_collector.stop()
            event.accept()
        else:
            event.ignore()

def main():
    # 设置日志
    logging.basicConfig(level=logging.INFO, 
                       format='%(asctime)s - %(levelname)s - %(message)s')
    
    app = QApplication(sys.argv)
    
    # 设置应用程序字体
    font = QFont("Arial", 10)
    app.setFont(font)
    
    # 设置应用程序样式
    app.setStyle('Fusion')
    
    window = FutureRobotControl()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()