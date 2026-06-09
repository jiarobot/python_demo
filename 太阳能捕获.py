import sys
import random
import numpy as np
import psutil
import platform
import pandas as pd
from datetime import datetime, timedelta
import matplotlib
matplotlib.rc("font", family='Microsoft YaHei')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QTabWidget, QPushButton, QLabel, QLineEdit, QTextEdit,
                             QComboBox, QSpinBox, QDoubleSpinBox, QSlider, QProgressBar,
                             QGroupBox, QGridLayout, QSplitter, QTableWidget, QTableWidgetItem,
                             QHeaderView, QMessageBox, QFileDialog, QAction, QToolBar,
                             QStatusBar, QDockWidget, QFrame, QSizePolicy, QCheckBox,
                             QSystemTrayIcon, QMenu, QStyle)
from PyQt5.QtCore import Qt, QTimer, QDateTime, QSize, QThread, pyqtSignal
from PyQt5.QtGui import QIcon, QFont, QPalette, QColor, QPainter
import json
import logging
from logging.handlers import RotatingFileHandler
import socket
import requests
from io import StringIO

# 设置日志记录
def setup_logging():
    logger = logging.getLogger('SolarSystem')
    logger.setLevel(logging.DEBUG)
    
    # 创建文件处理器，最多保留5个10MB的日志文件
    file_handler = RotatingFileHandler('solar_system.log', maxBytes=10*1024*1024, backupCount=5)
    file_handler.setLevel(logging.DEBUG)
    
    # 创建控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # 创建格式化器
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # 添加处理器到日志器
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

logger = setup_logging()

class DashboardTab(QWidget):
    """系统仪表盘标签页"""
    
    def __init__(self, data_simulator):
        super().__init__()
        self.data_simulator = data_simulator
        self.historical_data = data_simulator.get_historical_data(24)
        self.init_ui()
        self.update_data()
        
        # 设置定时器定期更新数据
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_data)
        self.timer.start(5000)  # 每5秒更新一次
    
    def init_ui(self):
        """初始化UI"""
        main_layout = QHBoxLayout()
        
        # 左侧指标面板
        metrics_frame = QFrame()
        metrics_frame.setFrameStyle(QFrame.Box)
        metrics_layout = QVBoxLayout()
        
        # 创建指标卡片
        self.irradiance_card = self.create_metric_card("光照强度", "W/m²", "#FF6B6B")
        self.temperature_card = self.create_metric_card("温度", "°C", "#4ECDC4")
        self.power_card = self.create_metric_card("功率输出", "W", "#45B7D1")
        self.efficiency_card = self.create_metric_card("转换效率", "%", "#96CEB4")
        self.battery_card = self.create_metric_card("电池电量", "%", "#FFEAA7")
        self.load_card = self.create_metric_card("负载消耗", "W", "#DDA0DD")
        
        metrics_layout.addWidget(self.irradiance_card)
        metrics_layout.addWidget(self.temperature_card)
        metrics_layout.addWidget(self.power_card)
        metrics_layout.addWidget(self.efficiency_card)
        metrics_layout.addWidget(self.battery_card)
        metrics_layout.addWidget(self.load_card)
        
        metrics_frame.setLayout(metrics_layout)
        metrics_frame.setMaximumWidth(300)
        
        # 右侧图表
        right_layout = QVBoxLayout()
        
        # 图表选择控件
        chart_controls = QHBoxLayout()
        chart_controls.addWidget(QLabel("显示图表:"))
        self.chart_selector = QComboBox()
        self.chart_selector.addItems(["功率输出", "光照强度", "温度", "转换效率"])
        self.chart_selector.currentTextChanged.connect(self.update_chart)
        chart_controls.addWidget(self.chart_selector)
        
        period_selector = QComboBox()
        period_selector.addItems(["最近6小时", "最近12小时", "最近24小时", "最近48小时"])
        period_selector.currentTextChanged.connect(self.change_period)
        chart_controls.addWidget(period_selector)
        chart_controls.addStretch()
        
        right_layout.addLayout(chart_controls)
        
        # 图表画布
        self.canvas = MplCanvas(self, width=8, height=6, dpi=100)
        right_layout.addWidget(self.canvas)
        
        # 添加到主布局
        main_layout.addWidget(metrics_frame)
        main_layout.addLayout(right_layout)
        
        self.setLayout(main_layout)

    def create_metric_card(self, title, unit, color):
        """创建指标卡片"""
        card = QGroupBox(title)
        card_layout = QVBoxLayout()
        
        value_label = QLabel("0")
        value_label.setAlignment(Qt.AlignCenter)
        value_label.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {color};")
        
        unit_label = QLabel(unit)
        unit_label.setAlignment(Qt.AlignCenter)
        unit_label.setStyleSheet("font-size: 14px; color: #555;")
        
        card_layout.addWidget(value_label)
        card_layout.addWidget(unit_label)
        card.setLayout(card_layout)
        
        # 存储值标签以便更新 - 使用英文名称而不是中文标题
        # 将中文标题映射到英文属性名
        title_map = {
            "光照强度": "irradiance",
            "温度": "temperature",
            "功率输出": "power",
            "转换效率": "efficiency",
            "电池电量": "battery",
            "负载消耗": "load"
        }
        
        # 使用映射获取正确的属性名
        attr_name = f"{title_map[title]}_label"
        setattr(self, attr_name, value_label)
        
        return card
    
    def update_data(self):
        """更新数据"""
        current_data = self.data_simulator.get_current_data()
        
        # 更新指标卡片
        self.irradiance_label.setText(f"{current_data['irradiance']:.1f}")
        self.temperature_label.setText(f"{current_data['temperature']:.1f}")
        # 将 'power' 改为 'power_ac'
        self.power_label.setText(f"{current_data['power_ac']:.1f}")
        self.efficiency_label.setText(f"{current_data['efficiency']*100:.1f}")
        self.battery_label.setText(f"{current_data['battery_level']:.1f}")
        self.load_label.setText(f"{current_data['load_consumption']:.1f}")
        
        # 更新历史数据（添加新数据点）
        self.historical_data.append(current_data)
        # 保持最近24小时数据
        if len(self.historical_data) > 24:
            self.historical_data = self.historical_data[-24:]
        
        # 更新图表
        self.update_chart()

    def update_chart(self):
        """更新图表"""
        chart_type = self.chart_selector.currentText()
        
        if chart_type == "功率输出":
            # 确保颜色参数正确传递
            self.canvas.plot_data(self.historical_data, 'power_ac', '功率输出随时间变化', '功率 (W)', '#45B7D1')
        elif chart_type == "光照强度":
            self.canvas.plot_data(self.historical_data, 'irradiance', '光照强度随时间变化', '光照强度 (W/m²)', '#FF6B6B')
        elif chart_type == "温度":
            self.canvas.plot_data(self.historical_data, 'temperature', '温度随时间变化', '温度 (°C)', '#4ECDC4')
        elif chart_type == "转换效率":
            # 转换效率需要乘以100显示为百分比
            efficiency_data = [{'timestamp': d['timestamp'], 'efficiency': d['efficiency'] * 100} for d in self.historical_data]
            self.canvas.plot_data(efficiency_data, 'efficiency', '转换效率随时间变化', '效率 (%)', '#96CEB4')
    
    def change_period(self, period_text):
        """更改显示的时间周期"""
        hours = 6
        if period_text == "最近12小时":
            hours = 12
        elif period_text == "最近24小时":
            hours = 24
        elif period_text == "最近48小时":
            hours = 48
        
        self.historical_data = self.data_simulator.get_historical_data(hours)
        self.update_chart()

class PowerManagementThread(QThread):
    """电源管理线程，用于监控和优化笔记本电脑的电源使用"""
    
    # 信号：电源状态更新
    power_status_updated = pyqtSignal(dict)
    # 信号：优化建议
    optimization_suggestion = pyqtSignal(str)
    
    def __init__(self, solar_system):
        super().__init__()
        self.solar_system = solar_system
        self.running = True
        
    def run(self):
        logger.info("电源管理线程启动")
        while self.running:
            try:
                # 获取系统电源信息
                power_info = self.get_power_info()
                
                # 获取太阳能系统状态
                solar_data = self.solar_system.get_current_data()
                
                # 根据太阳能可用性优化电源设置
                self.optimize_power_usage(power_info, solar_data)
                
                # 发送更新信号
                self.power_status_updated.emit(power_info)
                
                # 休眠一段时间（使用毫秒为单位）
                self.msleep(5000)  # 5秒
            except Exception as e:
                # 使用安全的字符串格式化方式
                logger.error("电源管理线程错误: %s", str(e))
                
    def get_power_info(self):
        """获取笔记本电脑电源信息"""
        battery = psutil.sensors_battery()
        power_info = {
            'plugged': battery.power_plugged if battery else False,
            'percent': battery.percent if battery else 100,
            'secsleft': battery.secsleft if battery else 0,
            'cpu_usage': psutil.cpu_percent(interval=1),
            'memory_usage': psutil.virtual_memory().percent,
            'disk_usage': psutil.disk_usage('/').percent,
            'process_count': len(psutil.pids()),
            'timestamp': datetime.now()
        }
        return power_info
    
    def optimize_power_usage(self, power_info, solar_data):
        """根据太阳能可用性优化电源使用"""
        suggestions = []
        
        # 如果太阳能充足
        if solar_data['power'] > 100:  # 超过100W
            if not power_info['plugged']:
                suggestions.append("太阳能充足，建议连接笔记本电脑充电")
            
            # 放宽性能限制
            if power_info['cpu_usage'] < 50:
                suggestions.append("太阳能充足，可以运行高性能任务")
        
        # 如果太阳能不足
        elif solar_data['power'] < 50:  # 低于50W
            if power_info['plugged']:
                suggestions.append("太阳能不足，建议断开充电以节省电池循环")
            
            # 建议节能措施
            if power_info['cpu_usage'] > 70:
                suggestions.append("太阳能不足，建议关闭非必要程序以节省电力")
            
            if power_info['memory_usage'] > 80:
                suggestions.append("太阳能不足，建议释放内存以降低功耗")
        
        # 发送优化建议
        for suggestion in suggestions:
            self.optimization_suggestion.emit(suggestion)
            # 使用安全的字符串格式化方式
            logger.info("优化建议: %s", suggestion)
    
    def stop(self):
        """停止线程"""
        self.running = False
        self.wait()

class SolarDataSimulator:
    """增强版太阳能数据模拟器，支持更多参数和真实环境模拟"""
    
    def __init__(self, location=None, panel_config=None):
        # 默认位置：北京
        self.location = location or {
            'latitude': 39.9042,
            'longitude': 116.4074,
            'timezone': 'Asia/Shanghai'
        }
        
        # 默认面板配置：2kW系统
        self.panel_config = panel_config or {
            'capacity': 2.0,  # kW
            'efficiency': 0.18,
            'area': 10.0,  # m²
            'tilt_angle': 30,  # 度
            'orientation': 180  # 度 (南向)
        }
        
        # 电池配置
        self.battery_config = {
            'capacity': 5.0,  # kWh
            'efficiency': 0.95,
            'max_charge_rate': 1.0,  # kW
            'max_discharge_rate': 2.0  # kW
        }
        
        # 环境参数
        self.weather_conditions = {
            'cloud_cover': 0.2,  # 云覆盖率 (0-1)
            'temperature': 25.0,  # 摄氏度
            'humidity': 0.6,  # 湿度 (0-1)
            'albedo': 0.2  # 地面反射率
        }
        
        # 历史数据存储
        self.historical_data = []
        self.max_history_hours = 72  # 保留72小时历史数据
        
        logger.info("太阳能数据模拟器初始化完成")
    
    def update_weather_conditions(self, cloud_cover=None, temperature=None, 
                                 humidity=None, albedo=None):
        """更新天气条件"""
        if cloud_cover is not None:
            self.weather_conditions['cloud_cover'] = max(0, min(1, cloud_cover))
        if temperature is not None:
            self.weather_conditions['temperature'] = temperature
        if humidity is not None:
            self.weather_conditions['humidity'] = max(0, min(1, humidity))
        if albedo is not None:
            self.weather_conditions['albedo'] = max(0, min(1, albedo))
    
    def calculate_solar_irradiance(self, timestamp):
        """计算太阳辐照度，考虑地理位置、时间和天气条件"""
        # 简化模型：实际应用中应使用更精确的太阳位置算法
        hour = timestamp.hour + timestamp.minute / 60.0
        day_of_year = timestamp.timetuple().tm_yday
        
        # 计算太阳高度角
        lat_rad = np.radians(self.location['latitude'])
        declination = 23.45 * np.sin(np.radians(360 * (284 + day_of_year) / 365))
        declination_rad = np.radians(declination)
        
        hour_angle = np.radians(15 * (hour - 12))
        sun_altitude = np.arcsin(
            np.sin(lat_rad) * np.sin(declination_rad) + 
            np.cos(lat_rad) * np.cos(declination_rad) * np.cos(hour_angle)
        )
        
        # 计算大气透射率（简化模型）
        air_mass = 1 / (np.sin(sun_altitude) + 0.50572 * (6.07995 + np.degrees(sun_altitude)) ** -1.6364)
        atmospheric_transmittance = 0.7 ** air_mass  # 经验公式
        
        # 考虑云层影响
        cloud_factor = 1 - 0.75 * self.weather_conditions['cloud_cover'] ** 3
        
        # 计算总辐照度
        solar_constant = 1361  # W/m²
        irradiance = solar_constant * atmospheric_transmittance * cloud_factor * np.sin(sun_altitude)
        
        return max(0, irradiance)
    
    def get_current_data(self):
        """获取当前模拟数据"""
        timestamp = datetime.now()
        
        # 计算太阳辐照度
        irradiance = self.calculate_solar_irradiance(timestamp)
        
        # 考虑面板效率和配置
        effective_irradiance = irradiance * (1 + self.weather_conditions['albedo'])
        power_dc = effective_irradiance * self.panel_config['area'] * self.panel_config['efficiency']
        
        # 考虑温度影响
        temperature_effect = 1 - 0.004 * (self.weather_conditions['temperature'] - 25)
        power_dc *= temperature_effect
        
        # 转换为交流电（假设逆变器效率为95%）
        inverter_efficiency = 0.95
        power_ac = power_dc * inverter_efficiency
        
        # 模拟电池状态（简化模型）
        battery_level = 50 + 30 * np.sin(timestamp.hour / 24 * 2 * np.pi)  # 昼夜变化
        
        # 模拟负载消耗
        base_load = 100  # W
        variable_load = random.uniform(0, 200)  # 随机变化
        load_consumption = base_load + variable_load
        
        # 创建数据点
        data_point = {
            'timestamp': timestamp,
            'irradiance': irradiance,
            'temperature': self.weather_conditions['temperature'],
            'power_dc': power_dc,
            'power_ac': power_ac,
            'efficiency': self.panel_config['efficiency'] * temperature_effect,
            'battery_level': battery_level,
            'load_consumption': load_consumption,
            'cloud_cover': self.weather_conditions['cloud_cover'],
            'humidity': self.weather_conditions['humidity']
        }
        
        # 保存到历史数据
        self.historical_data.append(data_point)
        
        # 限制历史数据大小
        if len(self.historical_data) > self.max_history_hours:
            self.historical_data = self.historical_data[-self.max_history_hours:]
        
        return data_point
    
    def get_historical_data(self, hours=24):
        """获取历史数据"""
        if hours <= len(self.historical_data):
            return self.historical_data[-hours:]
        
        # 如果请求的历史数据多于当前存储的数据，生成模拟历史数据
        historical_data = []
        current_time = datetime.now()
        
        for i in range(hours):
            timestamp = current_time - timedelta(hours=i)
            
            # 使用与当前数据相同的方法生成历史数据点
            irradiance = self.calculate_solar_irradiance(timestamp)
            
            effective_irradiance = irradiance * (1 + self.weather_conditions['albedo'])
            power_dc = effective_irradiance * self.panel_config['area'] * self.panel_config['efficiency']
            
            temperature_effect = 1 - 0.004 * (self.weather_conditions['temperature'] - 25)
            power_dc *= temperature_effect
            
            inverter_efficiency = 0.95
            power_ac = power_dc * inverter_efficiency
            
            battery_level = 50 + 30 * np.sin(timestamp.hour / 24 * 2 * np.pi)
            
            base_load = 100
            variable_load = random.uniform(0, 200)
            load_consumption = base_load + variable_load
            
            data_point = {
                'timestamp': timestamp,
                'irradiance': irradiance,
                'temperature': self.weather_conditions['temperature'],
                'power_dc': power_dc,
                'power_ac': power_ac,
                'efficiency': self.panel_config['efficiency'] * temperature_effect,
                'battery_level': battery_level,
                'load_consumption': load_consumption,
                'cloud_cover': self.weather_conditions['cloud_cover'],
                'humidity': self.weather_conditions['humidity']
            }
            
            historical_data.append(data_point)
        
        return sorted(historical_data, key=lambda x: x['timestamp'])

class MplCanvas(FigureCanvas):
    """增强版Matplotlib画布，支持更多图表类型和交互功能"""
    
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_subplot(111)
        super().__init__(self.fig)
        self.setParent(parent)
        
        FigureCanvas.setSizePolicy(self, QSizePolicy.Expanding, QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)
        
        # 启用鼠标交互
        self.setFocusPolicy(Qt.ClickFocus)
        self.setFocus()
    
    def plot_data(self, data, data_keys, title, ylabel, colors=None, plot_type='line'):
        """绘制数据，支持多种图表类型"""
        self.axes.clear()
        
        # 如果 colors 是字符串，将其转换为列表
        if isinstance(colors, str):
            colors = [colors]
        
        if not colors:
            colors = ['b', 'g', 'r', 'c', 'm', 'y', 'k']
        
        if data:
            timestamps = [d['timestamp'] for d in data]
            
            if not isinstance(data_keys, list):
                data_keys = [data_keys]
            
            for i, key in enumerate(data_keys):
                values = [d[key] for d in data]
                color = colors[i % len(colors)]
                
                if plot_type == 'line':
                    self.axes.plot(timestamps, values, color=color, marker='o', linestyle='-', label=key)
                elif plot_type == 'bar':
                    self.axes.bar(timestamps, values, color=color, alpha=0.7, label=key)
                elif plot_type == 'scatter':
                    self.axes.scatter(timestamps, values, color=color, label=key)
            
            self.axes.set_title(title)
            self.axes.set_ylabel(ylabel)
            self.axes.grid(True)
            
            # 添加图例
            if len(data_keys) > 1:
                self.axes.legend()
            
            # 格式化x轴日期显示
            self.fig.autofmt_xdate()
        
        self.draw()
    
    def clear_plot(self):
        """清除图表"""
        self.axes.clear()
        self.draw()

class PowerManagementTab(QWidget):
    """笔记本电脑电源管理标签页"""
    
    def __init__(self, solar_system):
        super().__init__()
        self.solar_system = solar_system
        self.power_manager = PowerManagementThread(solar_system)
        self.power_status = {}
        self.init_ui()
        
        # 连接信号和槽
        self.power_manager.power_status_updated.connect(self.update_power_status)
        self.power_manager.optimization_suggestion.connect(self.add_suggestion)
        
        # 启动电源管理线程
        self.power_manager.start()
    
    def init_ui(self):
        """初始化UI"""
        main_layout = QVBoxLayout()
        
        # 电源状态组
        status_group = QGroupBox("笔记本电脑电源状态")
        status_layout = QGridLayout()
        
        # 电池状态
        status_layout.addWidget(QLabel("电池状态:"), 0, 0)
        self.battery_status = QLabel("获取中...")
        status_layout.addWidget(self.battery_status, 0, 1)
        
        status_layout.addWidget(QLabel("电池电量:"), 1, 0)
        self.battery_percent = QProgressBar()
        self.battery_percent.setRange(0, 100)
        status_layout.addWidget(self.battery_percent, 1, 1)
        
        status_layout.addWidget(QLabel("剩余时间:"), 2, 0)
        self.battery_time = QLabel("获取中...")
        status_layout.addWidget(self.battery_time, 2, 1)
        
        # 系统资源使用
        status_layout.addWidget(QLabel("CPU使用率:"), 3, 0)
        self.cpu_usage = QProgressBar()
        self.cpu_usage.setRange(0, 100)
        status_layout.addWidget(self.cpu_usage, 3, 1)
        
        status_layout.addWidget(QLabel("内存使用率:"), 4, 0)
        self.memory_usage = QProgressBar()
        self.memory_usage.setRange(0, 100)
        status_layout.addWidget(self.memory_usage, 4, 1)
        
        status_layout.addWidget(QLabel("磁盘使用率:"), 5, 0)
        self.disk_usage = QProgressBar()
        self.disk_usage.setRange(0, 100)
        status_layout.addWidget(self.disk_usage, 5, 1)
        
        status_layout.addWidget(QLabel("进程数量:"), 6, 0)
        self.process_count = QLabel("获取中...")
        status_layout.addWidget(self.process_count, 6, 1)
        
        status_group.setLayout(status_layout)
        
        # 电源优化组
        optimization_group = QGroupBox("电源优化建议")
        optimization_layout = QVBoxLayout()
        
        self.suggestions_list = QTextEdit()
        self.suggestions_list.setReadOnly(True)
        optimization_layout.addWidget(self.suggestions_list)
        
        optimization_group.setLayout(optimization_layout)
        
        # 电源设置组
        settings_group = QGroupBox("电源设置")
        settings_layout = QGridLayout()
        
        settings_layout.addWidget(QLabel("性能模式:"), 0, 0)
        self.performance_mode = QComboBox()
        self.performance_mode.addItems(["节能", "平衡", "高性能"])
        settings_layout.addWidget(self.performance_mode, 0, 1)
        
        settings_layout.addWidget(QLabel("屏幕亮度:"), 1, 0)
        self.screen_brightness = QSlider(Qt.Horizontal)
        self.screen_brightness.setRange(0, 100)
        self.screen_brightness.setValue(80)
        settings_layout.addWidget(self.screen_brightness, 1, 1)
        self.brightness_label = QLabel("80%")
        self.screen_brightness.valueChanged.connect(lambda v: self.brightness_label.setText(f"{v}%"))
        settings_layout.addWidget(self.brightness_label, 1, 2)
        
        settings_layout.addWidget(QLabel("自动优化:"), 2, 0)
        self.auto_optimize = QCheckBox("根据太阳能可用性自动优化")
        self.auto_optimize.setChecked(True)
        settings_layout.addWidget(self.auto_optimize, 2, 1)
        
        settings_group.setLayout(settings_layout)
        
        # 添加到主布局
        main_layout.addWidget(status_group)
        main_layout.addWidget(optimization_group)
        main_layout.addWidget(settings_group)
        
        self.setLayout(main_layout)
        
        # 初始更新
        self.update_power_status({})
    
    def update_power_status(self, status):
        """更新电源状态显示"""
        self.power_status = status
        
        if status:
            # 更新电池状态
            plugged_text = "已连接电源" if status['plugged'] else "使用电池"
            self.battery_status.setText(plugged_text)
            
            self.battery_percent.setValue(int(status['percent']))
            
            # 计算剩余时间
            if status['secsleft'] == psutil.POWER_TIME_UNLIMITED:
                time_text = "不限"
            elif status['secsleft'] == psutil.POWER_TIME_UNKNOWN:
                time_text = "未知"
            else:
                hours = status['secsleft'] // 3600
                minutes = (status['secsleft'] % 3600) // 60
                time_text = f"{hours}小时{minutes}分钟"
            
            self.battery_time.setText(time_text)
            
            # 更新系统资源使用
            self.cpu_usage.setValue(int(status['cpu_usage']))
            self.memory_usage.setValue(int(status['memory_usage']))
            self.disk_usage.setValue(int(status['disk_usage']))
            self.process_count.setText(str(status['process_count']))
    
    def add_suggestion(self, suggestion):
        """添加优化建议"""
        timestamp = QDateTime.currentDateTime().toString("hh:mm:ss")
        self.suggestions_list.append(f"[{timestamp}] {suggestion}")
    
    def closeEvent(self, event):
        """关闭事件处理"""
        self.power_manager.stop()
        super().closeEvent(event)

class AdvancedAnalysisTab(QWidget):
    """高级分析标签页，包含预测和优化功能"""
    
    def __init__(self, data_simulator):
        super().__init__()
        self.data_simulator = data_simulator
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        main_layout = QVBoxLayout()
        
        # 控制栏
        controls_layout = QHBoxLayout()
        
        controls_layout.addWidget(QLabel("分析类型:"))
        self.analysis_type = QComboBox()
        self.analysis_type.addItems([
            "发电预测", 
            "能耗分析", 
            "效率优化", 
            "经济效益分析",
            "系统健康度"
        ])
        controls_layout.addWidget(self.analysis_type)
        
        controls_layout.addWidget(QLabel("时间范围:"))
        self.date_range = QComboBox()
        self.date_range.addItems(["最近24小时", "最近7天", "最近30天", "自定义"])
        controls_layout.addWidget(self.date_range)
        
        self.analyze_btn = QPushButton("开始分析")
        self.analyze_btn.clicked.connect(self.perform_analysis)
        controls_layout.addWidget(self.analyze_btn)
        
        self.export_btn = QPushButton("导出报告")
        self.export_btn.clicked.connect(self.export_report)
        controls_layout.addWidget(self.export_btn)
        
        controls_layout.addStretch()
        
        main_layout.addLayout(controls_layout)
        
        # 结果展示区域
        results_layout = QHBoxLayout()
        
        # 左侧 - 统计信息和预测
        stats_group = QGroupBox("分析结果")
        stats_layout = QVBoxLayout()
        
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        stats_layout.addWidget(self.results_text)
        
        stats_group.setLayout(stats_layout)
        stats_group.setMaximumWidth(400)
        
        # 右侧 - 图表
        chart_group = QGroupBox("分析图表")
        chart_layout = QVBoxLayout()
        
        self.analysis_canvas = MplCanvas(self, width=8, height=6, dpi=100)
        chart_layout.addWidget(self.analysis_canvas)
        
        chart_group.setLayout(chart_layout)
        
        results_layout.addWidget(stats_group)
        results_layout.addWidget(chart_group)
        
        main_layout.addLayout(results_layout)
        
        self.setLayout(main_layout)
    
    def perform_analysis(self):
        """执行分析"""
        analysis_type = self.analysis_type.currentText()
        
        if analysis_type == "发电预测":
            self.power_prediction_analysis()
        elif analysis_type == "能耗分析":
            self.energy_consumption_analysis()
        elif analysis_type == "效率优化":
            self.efficiency_optimization_analysis()
        elif analysis_type == "经济效益分析":
            self.economic_analysis()
        elif analysis_type == "系统健康度":
            self.system_health_analysis()
    
    def power_prediction_analysis(self):
        """发电预测分析"""
        # 获取历史数据
        historical_data = self.data_simulator.get_historical_data(24)
        
        # 简单预测模型（实际应用中应使用更复杂的模型）
        timestamps = [d['timestamp'] for d in historical_data]
        power_values = [d['power_ac'] for d in historical_data]
        
        # 生成预测（简单线性外推）
        future_hours = 12
        future_timestamps = [timestamps[-1] + timedelta(hours=i) for i in range(1, future_hours+1)]
        
        # 使用最后6小时数据的趋势进行预测
        last_6h_power = power_values[-6:]
        if len(last_6h_power) >= 2:
            # 简单线性回归
            x = list(range(len(last_6h_power)))
            y = last_6h_power
            coefficients = np.polyfit(x, y, 1)
            trend_line = np.poly1d(coefficients)
            
            # 预测未来值
            future_power = [trend_line(len(last_6h_power) + i) for i in range(future_hours)]
            # 确保预测值不为负
            future_power = [max(0, p) for p in future_power]
        else:
            future_power = [power_values[-1] for _ in range(future_hours)]
        
        # 创建预测数据
        forecast_data = []
        for i in range(future_hours):
            forecast_data.append({
                'timestamp': future_timestamps[i],
                'power_ac': future_power[i],
                'type': 'forecast'
            })
        
        # 组合历史和预测数据
        combined_data = historical_data + forecast_data
        
        # 更新图表
        self.analysis_canvas.plot_data(
            combined_data, 
            'power_ac', 
            '发电功率历史与预测', 
            '功率 (W)', 
            plot_type='line'
        )
        
        # 更新结果文本
        avg_power = np.mean(power_values)
        max_power = np.max(power_values)
        min_power = np.min(power_values)
        total_energy = np.sum(power_values) / 1000  # kWh
        
        forecast_avg = np.mean(future_power)
        forecast_total = np.sum(future_power) / 1000  # kWh
        
        result_text = f"""
        === 发电预测分析 ===
        
        历史数据统计 (最近24小时):
        - 平均功率: {avg_power:.2f} W
        - 最大功率: {max_power:.2f} W
        - 最小功率: {min_power:.2f} W
        - 总发电量: {total_energy:.2f} kWh
        
        未来12小时预测:
        - 预测平均功率: {forecast_avg:.2f} W
        - 预测总发电量: {forecast_total:.2f} kWh
        - 趋势: {'上升' if forecast_avg > avg_power else '下降'}
        
        建议:
        - 预测发电量 {'充足' if forecast_avg > 100 else '不足'}
        - {'可以运行高性能任务' if forecast_avg > 150 else '建议节能模式运行'}
        """
        
        self.results_text.setPlainText(result_text)
    
    def energy_consumption_analysis(self):
        """能耗分析"""
        # 获取历史数据
        historical_data = self.data_simulator.get_historical_data(24)
        
        # 提取能耗数据
        timestamps = [d['timestamp'] for d in historical_data]
        power_values = [d['power_ac'] for d in historical_data]
        load_values = [d['load_consumption'] for d in historical_data]
        
        # 计算能效比
        efficiency_ratio = []
        for i in range(len(power_values)):
            if power_values[i] > 0:
                ratio = load_values[i] / power_values[i]
            else:
                ratio = 0
            efficiency_ratio.append(ratio)
        
        # 更新图表
        self.analysis_canvas.plot_data(
            historical_data, 
            ['power_ac', 'load_consumption'], 
            '发电与能耗对比', 
            '功率 (W)', 
            colors=['b', 'r'],
            plot_type='line'
        )
        
        # 更新结果文本
        avg_power = np.mean(power_values)
        avg_load = np.mean(load_values)
        avg_efficiency = np.mean(efficiency_ratio)
        
        result_text = f"""
        === 能耗分析 ===
        
        统计结果 (最近24小时):
        - 平均发电功率: {avg_power:.2f} W
        - 平均负载功率: {avg_load:.2f} W
        - 平均能效比: {avg_efficiency:.2f}
        
        分析:
        - 发电利用率: {(avg_load / avg_power * 100 if avg_power > 0 else 0):.2f}%
        - {'发电充足，有余电' if avg_power > avg_load else '发电不足，需要电网或电池补充'}
        
        建议:
        - {'可以考虑增加负载或存储多余电能' if avg_power > avg_load else '建议减少负载或增加发电能力'}
        - 优化用电时间以匹配发电高峰
        """
        
        self.results_text.setPlainText(result_text)
    
    def efficiency_optimization_analysis(self):
        """效率优化分析"""
        # 获取历史数据
        historical_data = self.data_simulator.get_historical_data(24)
        
        # 提取效率相关数据
        timestamps = [d['timestamp'] for d in historical_data]
        efficiency_values = [d['efficiency'] * 100 for d in historical_data]  # 转换为百分比
        irradiance_values = [d['irradiance'] for d in historical_data]
        temperature_values = [d['temperature'] for d in historical_data]
        
        # 更新图表 - 效率vs辐照度
        self.analysis_canvas.axes.clear()
        scatter = self.analysis_canvas.axes.scatter(irradiance_values, efficiency_values, 
                                                   c=temperature_values, cmap='viridis', alpha=0.7)
        self.analysis_canvas.axes.set_title('效率 vs 辐照度 (颜色表示温度)')
        self.analysis_canvas.axes.set_xlabel('辐照度 (W/m²)')
        self.analysis_canvas.axes.set_ylabel('效率 (%)')
        self.analysis_canvas.axes.grid(True)
        
        # 添加颜色条
        plt.colorbar(scatter, ax=self.analysis_canvas.axes, label='温度 (°C)')
        
        self.analysis_canvas.draw()
        
        # 更新结果文本
        avg_efficiency = np.mean(efficiency_values)
        max_efficiency = np.max(efficiency_values)
        min_efficiency = np.min(efficiency_values)
        
        # 计算效率与温度和辐照度的相关性
        efficiency_np = np.array(efficiency_values)
        irradiance_np = np.array(irradiance_values)
        temperature_np = np.array(temperature_values)
        
        corr_irradiance = np.corrcoef(efficiency_np, irradiance_np)[0, 1] if len(efficiency_np) > 1 else 0
        corr_temperature = np.corrcoef(efficiency_np, temperature_np)[0, 1] if len(efficiency_np) > 1 else 0
        
        result_text = f"""
        === 效率优化分析 ===
        
        统计结果 (最近24小时):
        - 平均效率: {avg_efficiency:.2f}%
        - 最高效率: {max_efficiency:.2f}%
        - 最低效率: {min_efficiency:.2f}%
        
        相关性分析:
        - 效率与辐照度的相关性: {corr_irradiance:.3f}
        - 效率与温度的相关性: {corr_temperature:.3f}
        
        优化建议:
        - {'面板角度可能需要调整以捕获更多阳光' if corr_irradiance < 0.7 else '面板角度良好'}
        - {'考虑增加冷却措施以提高效率' if corr_temperature < -0.5 else '温度影响在可接受范围内'}
        - 清洁面板可能提高效率 {max(0, (max_efficiency - avg_efficiency)):.2f}%
        """
        
        self.results_text.setPlainText(result_text)
    
    def economic_analysis(self):
        """经济效益分析"""
        # 获取历史数据
        historical_data = self.data_simulator.get_historical_data(24)
        
        # 提取发电数据
        power_values = [d['power_ac'] for d in historical_data]
        
        # 计算总发电量 (kWh)
        total_energy = np.sum(power_values) / 1000  # 转换为kWh
        
        # 经济参数（可配置）
        electricity_price = 0.15  # 每kWh电费（美元）
        panel_cost = 2000         # 假设面板成本（美元）
        maintenance_cost = 100    # 年维护成本（美元）
        system_lifetime = 25      # 系统寿命（年）
        
        # 计算经济效益
        daily_savings = total_energy * electricity_price
        annual_savings = daily_savings * 365
        payback_period = panel_cost / annual_savings  # 年
        lifetime_savings = annual_savings * system_lifetime - panel_cost - maintenance_cost * system_lifetime
        
        # 更新图表 - 经济效益预测
        years = list(range(system_lifetime + 1))
        cumulative_savings = [annual_savings * y - panel_cost - maintenance_cost * y for y in years]
        
        self.analysis_canvas.axes.clear()
        self.analysis_canvas.axes.plot(years, cumulative_savings, 'g-', marker='o')
        self.analysis_canvas.axes.axhline(y=0, color='r', linestyle='--', label='盈亏平衡点')
        self.analysis_canvas.axes.set_title('经济效益预测')
        self.analysis_canvas.axes.set_xlabel('年')
        self.analysis_canvas.axes.set_ylabel('累计节省金额 ($)')
        self.analysis_canvas.axes.grid(True)
        self.analysis_canvas.axes.legend()
        
        self.analysis_canvas.draw()
        
        # 更新结果文本
        result_text = f"""
        === 经济效益分析 ===
        
        每日发电统计:
        - 总发电量: {total_energy:.2f} kWh
        - 电费节省: ${daily_savings:.2f}
        
        年度预测:
        - 年发电量: {total_energy * 365:.2f} kWh
        - 年节省电费: ${annual_savings:.2f}
        - 年维护成本: ${maintenance_cost:.2f}
        - 年净节省: ${annual_savings - maintenance_cost:.2f}
        
        投资回报:
        - 系统成本: ${panel_cost:.2f}
        - 投资回收期: {payback_period:.2f} 年
        - {system_lifetime}年总节省: ${lifetime_savings:.2f}
        - 投资回报率: {(lifetime_savings / panel_cost * 100 if panel_cost > 0 else 0):.2f}%
        
        环保效益:
        - 年CO2减排: {total_energy * 365 * 0.5:.2f} kg (假设0.5kg/kWh)
        """
        
        self.results_text.setPlainText(result_text)
    
    def system_health_analysis(self):
        """系统健康度分析"""
        # 获取历史数据
        historical_data = self.data_simulator.get_historical_data(24)
        
        # 提取系统参数
        efficiency_values = [d['efficiency'] * 100 for d in historical_data]
        irradiance_values = [d['irradiance'] for d in historical_data]
        
        # 计算性能比（实际发电/理论最大发电）
        performance_ratio = []
        for d in historical_data:
            theoretical_max = d['irradiance'] * self.data_simulator.panel_config['area'] * 0.21  # 假设21%为理论最大效率
            if theoretical_max > 0:
                pr = d['power_ac'] / theoretical_max
            else:
                pr = 0
            performance_ratio.append(pr)
        
        # 更新图表 - 性能比趋势
        self.analysis_canvas.plot_data(
            historical_data, 
            performance_ratio, 
            '系统性能比趋势', 
            '性能比', 
            plot_type='line'
        )
        
        # 更新结果文本
        avg_performance_ratio = np.mean(performance_ratio)
        min_performance_ratio = np.min(performance_ratio)
        max_performance_ratio = np.max(performance_ratio)
        
        # 系统健康度评分（0-100）
        health_score = avg_performance_ratio * 100
        
        result_text = f"""
        === 系统健康度分析 ===
        
        性能比统计 (最近24小时):
        - 平均性能比: {avg_performance_ratio:.3f}
        - 最低性能比: {min_performance_ratio:.3f}
        - 最高性能比: {max_performance_ratio:.3f}
        
        系统健康度评分: {health_score:.1f}/100
        - {'优秀' if health_score >= 80 else '良好' if health_score >= 70 else '一般' if health_score >= 60 else '需要关注'}
        
        诊断建议:
        - 性能比低于0.75可能表明系统存在问题
        - {'系统运行良好' if health_score >= 75 else '建议检查面板清洁度和连接'}
        - {'逆变器效率正常' if avg_performance_ratio > 0.8 else '建议检查逆变器状态'}
        - 定期维护可以提高系统性能和寿命
        """
        
        self.results_text.setPlainText(result_text)
    
    def export_report(self):
        """导出分析报告"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存报告", "", "PDF文件 (*.pdf);;文本文件 (*.txt);;HTML文件 (*.html)"
        )
        
        if file_path:
            try:
                # 获取当前分析结果
                report_content = self.results_text.toPlainText()
                
                # 简单实现：保存为文本文件
                if file_path.endswith('.txt'):
                    with open(file_path, 'w') as f:
                        f.write(f"太阳能系统分析报告\n")
                        f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                        f.write("="*50 + "\n")
                        f.write(report_content)
                
                # 对于其他格式，可以添加更多实现
                QMessageBox.information(self, "成功", f"报告已导出到: {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导出报告时出错: {str(e)}")

class ControlTab(QWidget):
    """系统控制标签页"""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        main_layout = QHBoxLayout()
        
        # 左侧 - 设备控制
        control_group = QGroupBox("设备控制")
        control_layout = QVBoxLayout()
        
        # 电池控制
        battery_group = QGroupBox("电池管理")
        battery_layout = QGridLayout()
        
        battery_layout.addWidget(QLabel("充电模式:"), 0, 0)
        charge_mode = QComboBox()
        charge_mode.addItems(["自动", "最大充电", "均衡充电", "浮充"])
        battery_layout.addWidget(charge_mode, 0, 1)
        
        battery_layout.addWidget(QLabel("充电限制:"), 1, 0)
        charge_limit = QSlider(Qt.Horizontal)
        charge_limit.setRange(0, 100)
        charge_limit.setValue(80)
        battery_layout.addWidget(charge_limit, 1, 1)
        charge_limit_label = QLabel("80%")
        charge_limit.valueChanged.connect(lambda v: charge_limit_label.setText(f"{v}%"))
        battery_layout.addWidget(charge_limit_label, 1, 2)
        
        battery_group.setLayout(battery_layout)
        
        # 负载控制
        load_group = QGroupBox("负载管理")
        load_layout = QGridLayout()
        
        load_layout.addWidget(QLabel("负载优先级:"), 0, 0)
        load_priority = QComboBox()
        load_priority.addItems(["正常", "高优先级", "低优先级", "关键负载优先"])
        load_layout.addWidget(load_priority, 0, 1)
        
        load_layout.addWidget(QLabel("负载开关:"), 1, 0)
        load_switch = QComboBox()
        load_switch.addItems(["全部开启", "部分开启", "紧急模式", "全部关闭"])
        load_layout.addWidget(load_switch, 1, 1)
        
        load_group.setLayout(load_layout)
        
        # 逆变器控制
        inverter_group = QGroupBox("逆变器设置")
        inverter_layout = QGridLayout()
        
        inverter_layout.addWidget(QLabel("工作模式:"), 0, 0)
        inverter_mode = QComboBox()
        inverter_mode.addItems(["并网", "离网", "混合模式"])
        inverter_layout.addWidget(inverter_mode, 0, 1)
        
        inverter_layout.addWidget(QLabel("输出电压:"), 1, 0)
        output_voltage = QComboBox()
        output_voltage.addItems(["220V", "230V", "240V"])
        inverter_layout.addWidget(output_voltage, 1, 1)
        
        inverter_layout.addWidget(QLabel("输出频率:"), 2, 0)
        output_frequency = QComboBox()
        output_frequency.addItems(["50Hz", "60Hz"])
        inverter_layout.addWidget(output_frequency, 2, 1)
        
        inverter_group.setLayout(inverter_layout)
        
        control_layout.addWidget(battery_group)
        control_layout.addWidget(load_group)
        control_layout.addWidget(inverter_group)
        
        # 控制按钮
        button_layout = QHBoxLayout()
        apply_btn = QPushButton("应用设置")
        apply_btn.clicked.connect(self.apply_settings)
        reset_btn = QPushButton("重置")
        reset_btn.clicked.connect(self.reset_settings)
        
        button_layout.addWidget(apply_btn)
        button_layout.addWidget(reset_btn)
        control_layout.addLayout(button_layout)
        
        control_group.setLayout(control_layout)
        
        # 右侧 - 系统状态
        status_group = QGroupBox("系统状态")
        status_layout = QVBoxLayout()
        
        # 状态指示器
        status_grid = QGridLayout()
        
        status_grid.addWidget(QLabel("太阳能阵列:"), 0, 0)
        solar_status = QLabel("正常")
        solar_status.setStyleSheet("color: green; font-weight: bold;")
        status_grid.addWidget(solar_status, 0, 1)
        
        status_grid.addWidget(QLabel("电池状态:"), 1, 0)
        battery_status = QLabel("充电中")
        battery_status.setStyleSheet("color: blue; font-weight: bold;")
        status_grid.addWidget(battery_status, 1, 1)
        
        status_grid.addWidget(QLabel("逆变器:"), 2, 0)
        inverter_status = QLabel("运行中")
        inverter_status.setStyleSheet("color: green; font-weight: bold;")
        status_grid.addWidget(inverter_status, 2, 1)
        
        status_grid.addWidget(QLabel("负载:"), 3, 0)
        load_status = QLabel("正常")
        load_status.setStyleSheet("color: green; font-weight: bold;")
        status_grid.addWidget(load_status, 3, 1)
        
        status_layout.addLayout(status_grid)
        
        # 系统日志
        log_group = QGroupBox("系统日志")
        log_layout = QVBoxLayout()
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)
        log_group.setLayout(log_layout)
        
        status_layout.addWidget(log_group)
        status_group.setLayout(status_layout)
        
        # 添加到主布局
        main_layout.addWidget(control_group)
        main_layout.addWidget(status_group)
        
        self.setLayout(main_layout)
        
        # 存储控件引用以便后续访问
        self.charge_mode = charge_mode
        self.charge_limit = charge_limit
        self.load_priority = load_priority
        self.load_switch = load_switch
        self.inverter_mode = inverter_mode
        self.output_voltage = output_voltage
        self.output_frequency = output_frequency
        
        # 初始化日志
        self.log_message("系统控制界面初始化完成")
    
    def apply_settings(self):
        """应用设置"""
        self.log_message("应用系统设置")
        self.log_message(f"充电模式: {self.charge_mode.currentText()}")
        self.log_message(f"充电限制: {self.charge_limit.value()}%")
        self.log_message(f"负载优先级: {self.load_priority.currentText()}")
        self.log_message(f"负载开关: {self.load_switch.currentText()}")
        self.log_message(f"逆变器模式: {self.inverter_mode.currentText()}")
        self.log_message(f"输出电压: {self.output_voltage.currentText()}")
        self.log_message(f"输出频率: {self.output_frequency.currentText()}")
        
        QMessageBox.information(self, "成功", "系统设置已应用")
    
    def reset_settings(self):
        """重置设置"""
        self.charge_mode.setCurrentIndex(0)
        self.charge_limit.setValue(80)
        self.load_priority.setCurrentIndex(0)
        self.load_switch.setCurrentIndex(0)
        self.inverter_mode.setCurrentIndex(0)
        self.output_voltage.setCurrentIndex(0)
        self.output_frequency.setCurrentIndex(0)
        
        self.log_message("系统设置已重置为默认值")
    
    def log_message(self, message):
        """添加日志消息"""
        timestamp = QDateTime.currentDateTime().toString("yyyy-MM-dd hh:mm:ss")
        self.log_text.append(f"[{timestamp}] {message}")

class SettingsTab(QWidget):
    """系统设置标签页"""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        main_layout = QHBoxLayout()
        
        # 左侧 - 系统设置
        settings_group = QGroupBox("系统设置")
        settings_layout = QVBoxLayout()
        
        # 基本设置
        basic_group = QGroupBox("基本设置")
        basic_layout = QGridLayout()
        
        basic_layout.addWidget(QLabel("系统名称:"), 0, 0)
        self.system_name = QLineEdit("太阳能系统1")
        basic_layout.addWidget(self.system_name, 0, 1)
        
        basic_layout.addWidget(QLabel("系统容量:"), 1, 0)
        self.system_capacity = QDoubleSpinBox()
        self.system_capacity.setRange(0.1, 1000)
        self.system_capacity.setValue(2.0)
        self.system_capacity.setSuffix(" kW")
        basic_layout.addWidget(self.system_capacity, 1, 1)
        
        basic_layout.addWidget(QLabel("电池容量:"), 2, 0)
        self.battery_capacity = QDoubleSpinBox()
        self.battery_capacity.setRange(0.1, 1000)
        self.battery_capacity.setValue(5.0)
        self.battery_capacity.setSuffix(" kWh")
        basic_layout.addWidget(self.battery_capacity, 2, 1)
        
        basic_layout.addWidget(QLabel("地理位置:"), 3, 0)
        location_layout = QHBoxLayout()
        self.latitude = QDoubleSpinBox()
        self.latitude.setRange(-90, 90)
        self.latitude.setValue(39.9)
        self.latitude.setSuffix("° N")
        self.longitude = QDoubleSpinBox()
        self.longitude.setRange(-180, 180)
        self.longitude.setValue(116.4)
        self.longitude.setSuffix("° E")
        location_layout.addWidget(self.latitude)
        location_layout.addWidget(self.longitude)
        basic_layout.addLayout(location_layout, 3, 1)
        
        basic_group.setLayout(basic_layout)
        
        # 高级设置
        advanced_group = QGroupBox("高级设置")
        advanced_layout = QGridLayout()
        
        advanced_layout.addWidget(QLabel("数据记录间隔:"), 0, 0)
        self.log_interval = QSpinBox()
        self.log_interval.setRange(1, 60)
        self.log_interval.setValue(5)
        self.log_interval.setSuffix(" 分钟")
        advanced_layout.addWidget(self.log_interval, 0, 1)
        
        advanced_layout.addWidget(QLabel("数据保留时间:"), 1, 0)
        self.data_retention = QSpinBox()
        self.data_retention.setRange(1, 365)
        self.data_retention.setValue(365)
        self.data_retention.setSuffix(" 天")
        advanced_layout.addWidget(self.data_retention, 1, 1)
        
        advanced_layout.addWidget(QLabel("报警阈值:"), 2, 0)
        self.alarm_threshold = QComboBox()
        self.alarm_threshold.addItems(["低", "中", "高"])
        advanced_layout.addWidget(self.alarm_threshold, 2, 1)
        
        advanced_group.setLayout(advanced_layout)
        
        settings_layout.addWidget(basic_group)
        settings_layout.addWidget(advanced_group)
        
        # 按钮
        button_layout = QHBoxLayout()
        save_btn = QPushButton("保存设置")
        save_btn.clicked.connect(self.save_settings)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.cancel_changes)
        default_btn = QPushButton("恢复默认")
        default_btn.clicked.connect(self.restore_defaults)
        
        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(default_btn)
        
        settings_layout.addLayout(button_layout)
        settings_group.setLayout(settings_layout)
        
        # 右侧 - 系统信息
        info_group = QGroupBox("系统信息")
        info_layout = QVBoxLayout()
        
        info_text = QTextEdit()
        info_text.setReadOnly(True)
        info_text.setPlainText("""太阳能捕获利用系统 v2.0

系统特性:
- 实时监控太阳能发电数据
- 智能控制系统运行
- 数据分析与报表生成
- 远程访问与控制

硬件要求:
- 太阳能光伏板
- 充电控制器
- 蓄电池组
- 逆变器
- 数据采集设备

支持协议:
- Modbus RTU/TCP
- SNMP
- HTTP REST API

版权信息:
© 2025 太阳能系统公司. 保留所有权利。""")
        
        info_layout.addWidget(info_text)
        info_group.setLayout(info_layout)
        
        # 添加到主布局
        main_layout.addWidget(settings_group)
        main_layout.addWidget(info_group)
        
        self.setLayout(main_layout)
    
    def save_settings(self):
        """保存设置"""
        QMessageBox.information(self, "成功", "系统设置已保存")
    
    def cancel_changes(self):
        """取消更改"""
        self.system_name.setText("太阳能系统1")
        self.system_capacity.setValue(2.0)
        self.battery_capacity.setValue(5.0)
        self.latitude.setValue(39.9)
        self.longitude.setValue(116.4)
        self.log_interval.setValue(5)
        self.data_retention.setValue(365)
        self.alarm_threshold.setCurrentIndex(1)
        
        QMessageBox.information(self, "提示", "更改已取消")
    
    def restore_defaults(self):
        """恢复默认设置"""
        self.system_name.setText("太阳能系统")
        self.system_capacity.setValue(3.0)
        self.battery_capacity.setValue(10.0)
        self.latitude.setValue(39.9)
        self.longitude.setValue(116.4)
        self.log_interval.setValue(10)
        self.data_retention.setValue(180)
        self.alarm_threshold.setCurrentIndex(0)
        
        QMessageBox.information(self, "提示", "已恢复默认设置")       

class SolarEnergySystem(QMainWindow):
    """增强版太阳能捕获利用系统主窗口"""
    
    def __init__(self):
        super().__init__()
        self.data_simulator = SolarDataSimulator()
        self.init_ui()
        
        # 创建系统托盘图标
        self.create_system_tray()
        
        logger.info("太阳能系统主窗口初始化完成")
    
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle('高级太阳能捕获利用系统')
        self.setGeometry(100, 100, 1400, 900)
        
        # 创建中心部件和标签页
        self.central_widget = QTabWidget()
        self.setCentralWidget(self.central_widget)
        
        # 创建各个标签页
        self.dashboard_tab = DashboardTab(self.data_simulator)
        self.control_tab = ControlTab()
        self.analysis_tab = AdvancedAnalysisTab(self.data_simulator)
        self.power_tab = PowerManagementTab(self.data_simulator)
        self.settings_tab = SettingsTab()
        
        # 添加标签页
        self.central_widget.addTab(self.dashboard_tab, "仪表盘")
        self.central_widget.addTab(self.control_tab, "控制系统")
        self.central_widget.addTab(self.analysis_tab, "高级分析")
        self.central_widget.addTab(self.power_tab, "电源管理")
        self.central_widget.addTab(self.settings_tab, "系统设置")
        
        # 创建菜单栏
        self.create_menu_bar()
        
        # 创建工具栏
        self.create_tool_bar()
        
        # 创建状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage('系统就绪')
        
        # 添加状态栏组件
        self.status_cpu_label = QLabel("CPU: --%")
        self.status_memory_label = QLabel("内存: --%")
        self.status_solar_label = QLabel("太阳能: -- W")
        self.status_battery_label = QLabel("电池: --%")
        
        self.status_bar.addPermanentWidget(self.status_cpu_label)
        self.status_bar.addPermanentWidget(self.status_memory_label)
        self.status_bar.addPermanentWidget(self.status_solar_label)
        self.status_bar.addPermanentWidget(self.status_battery_label)
        
        # 设置定时器更新状态栏
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_status_bar)
        self.status_timer.start(5000)  # 每5秒更新一次
        
        # 设置样式
        self.apply_styles()
        
        # 初始更新
        self.update_status_bar()
    
    def create_system_tray(self):
        """创建系统托盘图标"""
        if not QSystemTrayIcon.isSystemTrayAvailable():
            logger.warning("系统托盘不可用")
            return
        
        # 创建托盘图标
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.style().standardIcon(QStyle.SP_ComputerIcon))
        
        # 创建托盘菜单
        tray_menu = QMenu()
        
        show_action = tray_menu.addAction("显示窗口")
        show_action.triggered.connect(self.show)
        
        hide_action = tray_menu.addAction("隐藏窗口")
        hide_action.triggered.connect(self.hide)
        
        tray_menu.addSeparator()
        
        quit_action = tray_menu.addAction("退出")
        quit_action.triggered.connect(QApplication.quit)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.tray_icon_activated)
        
        # 显示托盘图标
        self.tray_icon.show()
        
        logger.info("系统托盘图标已创建")
    
    def tray_icon_activated(self, reason):
        """托盘图标激活处理"""
        if reason == QSystemTrayIcon.DoubleClick:
            if self.isVisible():
                self.hide()
            else:
                self.show()
                self.activateWindow()
    
    def create_menu_bar(self):
        """创建菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu('文件')
        
        new_action = QAction('新建项目', self)
        new_action.setShortcut('Ctrl+N')
        file_menu.addAction(new_action)
        
        open_action = QAction('打开项目', self)
        open_action.setShortcut('Ctrl+O')
        file_menu.addAction(open_action)
        
        save_action = QAction('保存项目', self)
        save_action.setShortcut('Ctrl+S')
        file_menu.addAction(save_action)
        
        file_menu.addSeparator()
        
        export_action = QAction('导出数据', self)
        file_menu.addAction(export_action)
        
        report_action = QAction('生成报告', self)
        file_menu.addAction(report_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction('退出', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 视图菜单
        view_menu = menubar.addMenu('视图')
        
        dashboard_action = QAction('仪表盘', self)
        dashboard_action.triggered.connect(lambda: self.central_widget.setCurrentIndex(0))
        view_menu.addAction(dashboard_action)
        
        control_action = QAction('控制系统', self)
        control_action.triggered.connect(lambda: self.central_widget.setCurrentIndex(1))
        view_menu.addAction(control_action)
        
        analysis_action = QAction('高级分析', self)
        analysis_action.triggered.connect(lambda: self.central_widget.setCurrentIndex(2))
        view_menu.addAction(analysis_action)
        
        power_action = QAction('电源管理', self)
        power_action.triggered.connect(lambda: self.central_widget.setCurrentIndex(3))
        view_menu.addAction(power_action)
        
        settings_action = QAction('系统设置', self)
        settings_action.triggered.connect(lambda: self.central_widget.setCurrentIndex(4))
        view_menu.addAction(settings_action)
        
        view_menu.addSeparator()
        
        fullscreen_action = QAction('全屏', self)
        fullscreen_action.setShortcut('F11')
        fullscreen_action.triggered.connect(self.toggle_fullscreen)
        view_menu.addAction(fullscreen_action)
        
        # 工具菜单
        tools_menu = menubar.addMenu('工具')
        
        data_manager_action = QAction('数据管理', self)
        tools_menu.addAction(data_manager_action)
        
        report_generator_action = QAction('报表生成器', self)
        tools_menu.addAction(report_generator_action)
        
        system_diagnosis_action = QAction('系统诊断', self)
        tools_menu.addAction(system_diagnosis_action)
        
        remote_access_action = QAction('远程访问', self)
        tools_menu.addAction(remote_access_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu('帮助')
        
        help_action = QAction('帮助文档', self)
        help_menu.addAction(help_action)
        
        update_action = QAction('检查更新', self)
        help_menu.addAction(update_action)
        
        about_action = QAction('关于', self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def create_tool_bar(self):
        """创建工具栏"""
        toolbar = QToolBar()
        toolbar.setIconSize(QSize(24, 24))
        self.addToolBar(toolbar)
        
        # 添加工具栏动作
        dashboard_action = QAction('仪表盘', self)
        dashboard_action.triggered.connect(lambda: self.central_widget.setCurrentIndex(0))
        toolbar.addAction(dashboard_action)
        
        control_action = QAction('控制', self)
        control_action.triggered.connect(lambda: self.central_widget.setCurrentIndex(1))
        toolbar.addAction(control_action)
        
        analysis_action = QAction('分析', self)
        analysis_action.triggered.connect(lambda: self.central_widget.setCurrentIndex(2))
        toolbar.addAction(analysis_action)
        
        power_action = QAction('电源', self)
        power_action.triggered.connect(lambda: self.central_widget.setCurrentIndex(3))
        toolbar.addAction(power_action)
        
        toolbar.addSeparator()
        
        refresh_action = QAction('刷新', self)
        toolbar.addAction(refresh_action)
        
        export_action = QAction('导出', self)
        toolbar.addAction(export_action)
        
        settings_action = QAction('设置', self)
        settings_action.triggered.connect(lambda: self.central_widget.setCurrentIndex(4))
        toolbar.addAction(settings_action)
    
    def update_status_bar(self):
        """更新状态栏信息"""
        try:
            # 获取系统资源信息
            cpu_percent = psutil.cpu_percent()
            memory_percent = psutil.virtual_memory().percent
            
            # 获取太阳能信息
            solar_data = self.data_simulator.get_current_data()
            solar_power = solar_data['power_ac']
            
            # 获取电池信息
            battery = psutil.sensors_battery()
            battery_percent = battery.percent if battery else 100
            
            # 更新状态栏
            self.status_cpu_label.setText(f"CPU: {cpu_percent}%")
            self.status_memory_label.setText(f"内存: {memory_percent}%")
            self.status_solar_label.setText(f"太阳能: {solar_power:.1f} W")
            self.status_battery_label.setText(f"电池: {battery_percent}%")
            
        except Exception as e:
            logger.error(f"更新状态栏时出错: {e}")
    
    def toggle_fullscreen(self):
        """切换全屏模式"""
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()
    
    def apply_styles(self):
        """应用样式表"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QTabWidget::pane {
                border: 1px solid #d0d0d0;
                background: white;
                top: -1px;
            }
            QTabBar::tab {
                background: #e8e8e8;
                border: 1px solid #d0d0d0;
                padding: 8px 12px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background: white;
                border-bottom-color: white;
            }
            QTabBar::tab:hover:!selected {
                background: #f0f0f0;
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
                background-color: #4CAF50;
                border: none;
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
            QPushButton:disabled {
                background-color: #a0a0a0;
            }
            QTableView, QTableWidget {
                gridline-color: #ddd;
                alternate-background-color: #f9f9f9;
            }
            QHeaderView::section {
                background-color: #f0f0f0;
                padding: 4px;
                border: 1px solid #ddd;
            }
            QStatusBar::item {
                border: none;
            }
        """)
    
    def show_about(self):
        """显示关于对话框"""
        about_text = """
        <h2>高级太阳能捕获利用系统</h2>
        <p>版本: 3.0</p>
        <p>这是一个强大的太阳能系统监控与管理工具，提供实时数据监控、系统控制、高级分析和电源管理功能。</p>
        <p>特性:</p>
        <ul>
            <li>实时太阳能数据监控</li>
            <li>系统控制和优化</li>
            <li>高级分析和预测</li>
            <li>笔记本电脑电源管理</li>
            <li>经济效益分析</li>
            <li>系统健康度监测</li>
        </ul>
        <p>© 2023 太阳能科技有限公司. 保留所有权利。</p>
        """
        QMessageBox.about(self, "关于", about_text)
    
    def closeEvent(self, event):
        """关闭事件处理"""
        # 停止所有后台线程
        if hasattr(self, 'power_tab') and hasattr(self.power_tab, 'power_manager'):
            self.power_tab.power_manager.stop()
        
        # 隐藏到系统托盘而不是直接退出
        if self.tray_icon.isVisible():
            QMessageBox.information(self, "信息", "程序将继续在系统托盘中运行")
            self.hide()
            event.ignore()
        else:
            event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setApplicationName("高级太阳能捕获利用系统")
    app.setApplicationVersion("3.0")
    
    # 设置应用程序样式
    app.setStyle('Fusion')
    
    window = SolarEnergySystem()
    window.show()
    
    sys.exit(app.exec_())