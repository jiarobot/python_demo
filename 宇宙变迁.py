import sys
import numpy as np
import math
import random
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTabWidget, QGroupBox, QPushButton, 
                             QLabel, QSlider, QSpinBox, QDoubleSpinBox, 
                             QCheckBox, QComboBox, QProgressBar, QTextEdit,
                             QSplitter, QFileDialog, QMessageBox, QTreeWidget,
                             QTreeWidgetItem, QDockWidget, QListWidget,
                             QTableWidget, QTableWidgetItem, QHeaderView)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QDateTime
from PyQt5.QtGui import QFont, QPalette, QColor, QPen, QBrush, QPainter, QPainterPath
from PyQt5.QtChart import QChart, QChartView, QLineSeries, QScatterSeries, QValueAxis
import pyqtgraph as pg
import pandas as pd
from scipy.integrate import odeint
from scipy.constants import G, c, parsec, astronomical_unit


class UniverseObject:
    """宇宙天体基类"""
    def __init__(self, name, mass, position, velocity, radius, color, object_type):
        self.name = name
        self.mass = mass  # 质量 (kg)
        self.position = np.array(position, dtype=float)  # 位置 (m)
        self.velocity = np.array(velocity, dtype=float)  # 速度 (m/s)
        self.radius = radius  # 半径 (m)
        self.color = color  # 显示颜色
        self.object_type = object_type  # 天体类型
        self.trajectory = []  # 轨迹记录
        self.max_trajectory_points = 1000  # 最大轨迹点数
        
    def update_position(self, dt, forces=None):
        """更新天体位置"""
        if forces is not None:
            # 计算加速度
            acceleration = forces / self.mass
            # 更新速度 (使用简单的欧拉积分)
            self.velocity += acceleration * dt
        
        # 更新位置
        self.position += self.velocity * dt
        
        # 记录轨迹
        self.trajectory.append(tuple(self.position.copy()))
        if len(self.trajectory) > self.max_trajectory_points:
            self.trajectory.pop(0)
    
    def get_force_from(self, other_object):
        """计算来自另一个天体的引力"""
        r_vector = other_object.position - self.position
        r_mag = np.linalg.norm(r_vector)
        
        if r_mag == 0:
            return np.zeros(3)
        
        # 万有引力公式
        force_mag = G * self.mass * other_object.mass / (r_mag**2)
        force_vector = force_mag * r_vector / r_mag
        
        return force_vector


class Star(UniverseObject):
    """恒星类"""
    def __init__(self, name, mass, position, velocity, radius, temperature, luminosity):
        color = self._get_color_from_temperature(temperature)
        super().__init__(name, mass, position, velocity, radius, color, "Star")
        self.temperature = temperature  # 表面温度 (K)
        self.luminosity = luminosity  # 光度 (W)
        
    @staticmethod
    def _get_color_from_temperature(temperature):
        """根据温度获取恒星颜色"""
        if temperature < 3500:
            return (255, 100, 0)  # 红色
        elif temperature < 5000:
            return (255, 200, 100)  # 橙黄色
        elif temperature < 6000:
            return (255, 255, 150)  # 黄色
        elif temperature < 7500:
            return (255, 255, 255)  # 白色
        elif temperature < 10000:
            return (200, 220, 255)  # 蓝白色
        else:
            return (150, 200, 255)  # 蓝色


class Planet(UniverseObject):
    """行星类"""
    def __init__(self, name, mass, position, velocity, radius, albedo, has_atmosphere=True):
        color = (100, 150, 255) if has_atmosphere else (150, 100, 50)
        super().__init__(name, mass, position, velocity, radius, color, "Planet")
        self.albedo = albedo  # 反照率
        self.has_atmosphere = has_atmosphere
        self.orbital_period = 0  # 轨道周期


class Galaxy:
    """星系类"""
    def __init__(self, name, galaxy_type, center_mass, radius, num_stars):
        self.name = name
        self.galaxy_type = galaxy_type  # 星系类型 (spiral, elliptical, irregular)
        self.center_mass = center_mass
        self.radius = radius
        self.stars = []
        self.generate_stars(num_stars)
        
    def generate_stars(self, num_stars):
        """生成星系中的恒星"""
        for i in range(num_stars):
            # 根据星系类型生成不同的分布
            if self.galaxy_type == "spiral":
                # 螺旋星系 - 使用对数螺旋分布
                angle = random.uniform(0, 2 * math.pi)
                r = random.uniform(0.1, 1) * self.radius
                # 添加螺旋扰动
                spiral_factor = 0.3 * math.sin(2 * angle)
                r = r * (1 + spiral_factor)
                
                x = r * math.cos(angle)
                y = r * math.sin(angle)
                z = random.gauss(0, self.radius * 0.05)
            elif self.galaxy_type == "elliptical":
                # 椭圆星系 - 使用椭圆分布
                r = random.uniform(0, 1) * self.radius
                theta = random.uniform(0, math.pi)
                phi = random.uniform(0, 2 * math.pi)
                
                # 椭圆形状 (z轴压缩)
                x = r * math.sin(theta) * math.cos(phi)
                y = r * math.sin(theta) * math.sin(phi)
                z = r * math.cos(theta) * 0.3  # z轴压缩
            else:
                # 不规则星系 - 随机分布
                x = random.gauss(0, self.radius * 0.5)
                y = random.gauss(0, self.radius * 0.5)
                z = random.gauss(0, self.radius * 0.2)
            
            # 计算轨道速度 (近似开普勒运动)
            distance = math.sqrt(x**2 + y**2 + z**2)
            if distance > 0:
                orbital_speed = math.sqrt(G * self.center_mass / distance)
                # 速度方向垂直于位置向量
                vx = -orbital_speed * y / distance
                vy = orbital_speed * x / distance
                vz = 0
            else:
                vx, vy, vz = 0, 0, 0
            
            # 创建恒星
            mass = random.uniform(0.1, 10) * 1.989e30  # 太阳质量的0.1-10倍
            radius = random.uniform(0.5, 5) * 6.96e8  # 太阳半径的0.5-5倍
            temperature = random.uniform(3000, 30000)
            luminosity = mass**3.5 * 3.828e26  # 质量-光度关系近似
            
            star = Star(f"Star_{i}", mass, [x, y, z], [vx, vy, vz], 
                       radius, temperature, luminosity)
            self.stars.append(star)


class UniverseSimulation(QThread):
    """宇宙模拟线程"""
    simulation_updated = pyqtSignal(list)
    simulation_finished = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.objects = []
        self.time_step = 3600 * 24  # 默认时间步长: 1天
        self.is_running = False
        self.is_paused = False
        self.current_time = 0  # 模拟时间 (秒)
        self.simulation_speed = 1.0  # 模拟速度倍数
        
    def add_object(self, obj):
        """添加天体到模拟"""
        self.objects.append(obj)
        
    def set_time_step(self, dt):
        """设置时间步长"""
        self.time_step = dt
        
    def set_simulation_speed(self, speed):
        """设置模拟速度"""
        self.simulation_speed = speed
        
    def run(self):
        """运行模拟"""
        self.is_running = True
        self.is_paused = False
        
        while self.is_running:
            if not self.is_paused:
                self.update_simulation()
                self.simulation_updated.emit(self.objects)
                self.current_time += self.time_step * self.simulation_speed
                
                # 控制更新频率
                self.msleep(50)  # 约20fps
            
    def pause(self):
        """暂停模拟"""
        self.is_paused = True
        
    def resume(self):
        """继续模拟"""
        self.is_paused = False
        
    def stop(self):
        """停止模拟"""
        self.is_running = False
        self.wait()
        
    def update_simulation(self):
        """更新模拟状态"""
        # 计算每个天体受到的引力
        forces = {}
        for obj in self.objects:
            forces[obj] = np.zeros(3)
            
        # 计算所有天体间的引力
        for i, obj1 in enumerate(self.objects):
            for j, obj2 in enumerate(self.objects):
                if i != j:
                    force = obj1.get_force_from(obj2)
                    forces[obj1] += force
        
        # 更新每个天体的位置
        for obj in self.objects:
            obj.update_position(self.time_step * self.simulation_speed, forces[obj])


class UniverseViewer(QWidget):
    """宇宙3D可视化组件"""
    def __init__(self):
        super().__init__()
        self.setMinimumSize(800, 600)
        
        # 创建3D图形视图
        self.graph_widget = pg.GraphicsLayoutWidget()
        self.view = self.graph_widget.addViewBox()
        self.view.setAspectLocked(True)
        
        # 创建网格
        self.grid = pg.GridItem()
        self.view.addItem(self.grid)
        
        # 散点图用于显示天体
        self.scatter_plot = pg.ScatterPlotItem(size=10, pen=pg.mkPen(None), brush=pg.mkBrush(255, 255, 255, 120))
        self.view.addItem(self.scatter_plot)
        
        # 轨迹图
        self.trajectory_plots = {}
        
        # 布局
        layout = QVBoxLayout()
        layout.addWidget(self.graph_widget)
        self.setLayout(layout)
        
        # 视图控制
        self.view_scale = 1e16  # 初始视图尺度
        self.view_center = [0, 0]
        self.show_trajectories = True
        self.show_labels = True
        
    def update_view(self, objects):
        """更新视图显示"""
        positions = []
        sizes = []
        colors = []
        labels = []
        
        for obj in objects:
            # 计算屏幕位置 (只显示XY平面投影)
            x = obj.position[0] / self.view_scale
            y = obj.position[1] / self.view_scale
            
            # 计算显示大小 (对数尺度)
            size = max(2, math.log10(obj.radius / 1e6) * 3)
            
            # 颜色
            color = obj.color
            
            positions.append([x, y])
            sizes.append(size)
            colors.append(color)
            labels.append(obj.name)
            
            # 更新轨迹
            if self.show_trajectories and len(obj.trajectory) > 1:
                if obj not in self.trajectory_plots:
                    pen = pg.mkPen(color=color, width=1)
                    self.trajectory_plots[obj] = pg.PlotDataItem(pen=pen)
                    self.view.addItem(self.trajectory_plots[obj])
                
                # 提取轨迹点
                traj_points = np.array(obj.trajectory) / self.view_scale
                if len(traj_points) > 0:
                    self.trajectory_plots[obj].setData(traj_points[:, 0], traj_points[:, 1])
        
        # 更新散点图
        if positions:
            self.scatter_plot.setData(positions, size=sizes, brush=colors)
        
        # 更新视图范围
        if positions:
            pos_array = np.array(positions)
            x_min, x_max = pos_array[:, 0].min(), pos_array[:, 0].max()
            y_min, y_max = pos_array[:, 1].min(), pos_array[:, 1].max()
            
            # 添加边距
            margin = max((x_max - x_min) * 0.1, (y_max - y_min) * 0.1, 0.1)
            self.view.setRange(xRange=[x_min - margin, x_max + margin], 
                              yRange=[y_min - margin, y_max + margin])
    
    def set_view_scale(self, scale):
        """设置视图尺度"""
        self.view_scale = scale
        
    def clear_trajectories(self):
        """清除所有轨迹"""
        for trajectory_plot in self.trajectory_plots.values():
            self.view.removeItem(trajectory_plot)
        self.trajectory_plots = {}


class DataAnalysisWidget(QWidget):
    """数据分析组件"""
    def __init__(self):
        super().__init__()
        
        # 创建图表
        self.chart = QChart()
        self.chart.setTitle("天体物理数据分析")
        self.chart_view = QChartView(self.chart)
        
        # 数据表格
        self.data_table = QTableWidget()
        self.data_table.setColumnCount(5)
        self.data_table.setHorizontalHeaderLabels(["天体", "质量 (kg)", "速度 (km/s)", "距离 (AU)", "类型"])
        
        # 统计分析标签
        self.stats_label = QLabel("统计信息将在这里显示")
        self.stats_label.setWordWrap(True)
        
        # 布局
        layout = QVBoxLayout()
        layout.addWidget(self.chart_view)
        layout.addWidget(self.data_table)
        layout.addWidget(self.stats_label)
        self.setLayout(layout)
        
    def update_analysis(self, objects):
        """更新数据分析"""
        # 清空表格
        self.data_table.setRowCount(0)
        
        # 收集数据
        masses = []
        velocities = []
        distances = []
        
        for i, obj in enumerate(objects):
            # 计算速度大小
            velocity_mag = np.linalg.norm(obj.velocity) / 1000  # km/s
            
            # 计算距离原点距离
            distance = np.linalg.norm(obj.position) / astronomical_unit  # AU
            
            # 添加到表格
            self.data_table.insertRow(i)
            self.data_table.setItem(i, 0, QTableWidgetItem(obj.name))
            self.data_table.setItem(i, 1, QTableWidgetItem(f"{obj.mass:.2e}"))
            self.data_table.setItem(i, 2, QTableWidgetItem(f"{velocity_mag:.2f}"))
            self.data_table.setItem(i, 3, QTableWidgetItem(f"{distance:.2f}"))
            self.data_table.setItem(i, 4, QTableWidgetItem(obj.object_type))
            
            # 收集统计数据
            masses.append(obj.mass)
            velocities.append(velocity_mag)
            distances.append(distance)
        
        # 调整列宽
        self.data_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        # 更新统计信息
        if masses:
            mass_min, mass_max = min(masses), max(masses)
            vel_min, vel_max = min(velocities), max(velocities)
            dist_min, dist_max = min(distances), max(distances)
            
            stats_text = f"""
            <h3>统计摘要</h3>
            <b>质量范围:</b> {mass_min:.2e} - {mass_max:.2e} kg<br>
            <b>速度范围:</b> {vel_min:.2f} - {vel_max:.2f} km/s<br>
            <b>距离范围:</b> {dist_min:.2f} - {dist_max:.2f} AU<br>
            <b>天体总数:</b> {len(objects)}
            """
            self.stats_label.setText(stats_text)
        
        # 更新图表 (质量-速度关系)
        self.update_chart(masses, velocities)
    
    def update_chart(self, masses, velocities):
        """更新图表"""
        self.chart.removeAllSeries()
        
        series = QScatterSeries()
        series.setName("质量-速度关系")
        
        for mass, velocity in zip(masses, velocities):
            # 使用对数尺度
            log_mass = math.log10(mass / 1.989e30)  # 以太阳质量为单位
            series.append(log_mass, velocity)
        
        self.chart.addSeries(series)
        
        # 设置坐标轴
        axis_x = QValueAxis()
        axis_x.setTitleText("质量 (log10(M/M☉))")
        axis_x.setLabelFormat("%.1f")
        self.chart.addAxis(axis_x, Qt.AlignBottom)
        series.attachAxis(axis_x)
        
        axis_y = QValueAxis()
        axis_y.setTitleText("速度 (km/s)")
        axis_y.setLabelFormat("%.0f")
        self.chart.addAxis(axis_y, Qt.AlignLeft)
        series.attachAxis(axis_y)
        
        self.chart.legend().setVisible(True)


class ControlPanel(QWidget):
    """控制面板"""
    def __init__(self, simulation):
        super().__init__()
        self.simulation = simulation
        
        # 创建控件
        self.setup_ui()
        
    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout()
        
        # 模拟控制组
        sim_group = QGroupBox("模拟控制")
        sim_layout = QVBoxLayout()
        
        # 开始/暂停/停止按钮
        btn_layout = QHBoxLayout()
        self.start_btn = QPushButton("开始")
        self.pause_btn = QPushButton("暂停")
        self.stop_btn = QPushButton("停止")
        self.reset_btn = QPushButton("重置")
        
        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.pause_btn)
        btn_layout.addWidget(self.stop_btn)
        btn_layout.addWidget(self.reset_btn)
        
        sim_layout.addLayout(btn_layout)
        
        # 时间控制
        time_layout = QHBoxLayout()
        time_layout.addWidget(QLabel("时间步长:"))
        self.time_step_spin = QDoubleSpinBox()
        self.time_step_spin.setRange(3600, 3600*24*365)  # 1小时到1年
        self.time_step_spin.setValue(3600*24)  # 默认1天
        self.time_step_spin.setSuffix(" 秒")
        time_layout.addWidget(self.time_step_spin)
        
        sim_layout.addLayout(time_layout)
        
        # 模拟速度
        speed_layout = QHBoxLayout()
        speed_layout.addWidget(QLabel("模拟速度:"))
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setRange(1, 100)
        self.speed_slider.setValue(10)
        speed_layout.addWidget(self.speed_slider)
        self.speed_label = QLabel("1.0x")
        speed_layout.addWidget(self.speed_label)
        
        sim_layout.addLayout(speed_layout)
        
        sim_group.setLayout(sim_layout)
        layout.addWidget(sim_group)
        
        # 天体管理组
        obj_group = QGroupBox("天体管理")
        obj_layout = QVBoxLayout()
        
        # 添加预设系统
        preset_layout = QHBoxLayout()
        preset_layout.addWidget(QLabel("预设系统:"))
        self.preset_combo = QComboBox()
        self.preset_combo.addItems(["太阳系", "双星系统", "球状星团", "螺旋星系"])
        preset_layout.addWidget(self.preset_combo)
        self.add_preset_btn = QPushButton("添加")
        preset_layout.addWidget(self.add_preset_btn)
        
        obj_layout.addLayout(preset_layout)
        
        # 添加自定义天体
        custom_btn_layout = QHBoxLayout()
        self.add_star_btn = QPushButton("添加恒星")
        self.add_planet_btn = QPushButton("添加行星")
        self.clear_all_btn = QPushButton("清除所有")
        
        custom_btn_layout.addWidget(self.add_star_btn)
        custom_btn_layout.addWidget(self.add_planet_btn)
        custom_btn_layout.addWidget(self.clear_all_btn)
        
        obj_layout.addLayout(custom_btn_layout)
        
        obj_group.setLayout(obj_layout)
        layout.addWidget(obj_group)
        
        # 视图控制组
        view_group = QGroupBox("视图控制")
        view_layout = QVBoxLayout()
        
        # 视图尺度
        scale_layout = QHBoxLayout()
        scale_layout.addWidget(QLabel("视图尺度:"))
        self.scale_slider = QSlider(Qt.Horizontal)
        self.scale_slider.setRange(10, 24)  # 10^10 到 10^24 米
        self.scale_slider.setValue(16)  # 10^16 米
        scale_layout.addWidget(self.scale_slider)
        self.scale_label = QLabel("1e16 m")
        scale_layout.addWidget(self.scale_label)
        
        view_layout.addLayout(scale_layout)
        
        # 显示选项
        self.trajectory_cb = QCheckBox("显示轨迹")
        self.trajectory_cb.setChecked(True)
        self.labels_cb = QCheckBox("显示标签")
        self.labels_cb.setChecked(True)
        
        view_layout.addWidget(self.trajectory_cb)
        view_layout.addWidget(self.labels_cb)
        
        view_group.setLayout(view_layout)
        layout.addWidget(view_group)
        
        # 信息显示
        info_group = QGroupBox("模拟信息")
        info_layout = QVBoxLayout()
        
        self.time_label = QLabel("模拟时间: 0 秒")
        self.object_count_label = QLabel("天体数量: 0")
        
        info_layout.addWidget(self.time_label)
        info_layout.addWidget(self.object_count_label)
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        layout.addStretch()
        self.setLayout(layout)
        
        # 连接信号
        self.connect_signals()
    
    def connect_signals(self):
        """连接信号和槽"""
        self.start_btn.clicked.connect(self.start_simulation)
        self.pause_btn.clicked.connect(self.pause_simulation)
        self.stop_btn.clicked.connect(self.stop_simulation)
        self.reset_btn.clicked.connect(self.reset_simulation)
        
        self.time_step_spin.valueChanged.connect(self.update_time_step)
        self.speed_slider.valueChanged.connect(self.update_simulation_speed)
        
        self.add_preset_btn.clicked.connect(self.add_preset_system)
        self.add_star_btn.clicked.connect(self.add_custom_star)
        self.add_planet_btn.clicked.connect(self.add_custom_planet)
        self.clear_all_btn.clicked.connect(self.clear_all_objects)
        
        self.scale_slider.valueChanged.connect(self.update_view_scale)
        self.trajectory_cb.toggled.connect(self.toggle_trajectories)
        self.labels_cb.toggled.connect(self.toggle_labels)
    
    def start_simulation(self):
        """开始模拟"""
        self.simulation.start()
        self.start_btn.setEnabled(False)
        self.pause_btn.setEnabled(True)
        self.stop_btn.setEnabled(True)
    
    def pause_simulation(self):
        """暂停模拟"""
        if self.simulation.is_paused:
            self.simulation.resume()
            self.pause_btn.setText("暂停")
        else:
            self.simulation.pause()
            self.pause_btn.setText("继续")
    
    def stop_simulation(self):
        """停止模拟"""
        self.simulation.stop()
        self.start_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)
        self.pause_btn.setText("暂停")
    
    def reset_simulation(self):
        """重置模拟"""
        self.stop_simulation()
        self.simulation.objects.clear()
        self.simulation.current_time = 0
        self.update_info()
    
    def update_time_step(self):
        """更新时间步长"""
        self.simulation.set_time_step(self.time_step_spin.value())
    
    def update_simulation_speed(self):
        """更新模拟速度"""
        speed = self.speed_slider.value() / 10.0
        self.simulation.set_simulation_speed(speed)
        self.speed_label.setText(f"{speed:.1f}x")
    
    def add_preset_system(self):
        """添加预设系统"""
        preset = self.preset_combo.currentText()
        
        if preset == "太阳系":
            self.add_solar_system()
        elif preset == "双星系统":
            self.add_binary_system()
        elif preset == "球状星团":
            self.add_globular_cluster()
        elif preset == "螺旋星系":
            self.add_spiral_galaxy()
    
    def add_solar_system(self):
        """添加太阳系"""
        # 太阳
        sun = Star("太阳", 1.989e30, [0, 0, 0], [0, 0, 0], 
                   6.96e8, 5778, 3.828e26)
        self.simulation.add_object(sun)
        
        # 行星 (简化模型)
        planets_data = [
            ("水星", 3.301e23, 5.79e10, 47.4e3, 2.44e6, (200, 200, 200)),
            ("金星", 4.867e24, 1.082e11, 35.0e3, 6.05e6, (255, 200, 100)),
            ("地球", 5.972e24, 1.496e11, 29.8e3, 6.37e6, (100, 100, 255)),
            ("火星", 6.417e23, 2.279e11, 24.1e3, 3.39e6, (255, 100, 100)),
            ("木星", 1.898e27, 7.785e11, 13.1e3, 6.99e7, (255, 150, 100)),
            ("土星", 5.683e26, 1.433e12, 9.7e3, 5.82e7, (255, 200, 150)),
            ("天王星", 8.681e25, 2.877e12, 6.8e3, 2.54e7, (150, 200, 255)),
            ("海王星", 1.024e26, 4.503e12, 5.4e3, 2.46e7, (100, 150, 255)),
        ]
        
        for name, mass, distance, speed, radius, color in planets_data:
            planet = Planet(name, mass, [distance, 0, 0], [0, speed, 0], 
                           radius, 0.3, True)
            planet.color = color
            self.simulation.add_object(planet)
    
    def add_binary_system(self):
        """添加双星系统"""
        # 两颗质量相近的恒星
        star1 = Star("恒星A", 2e30, [-1e11, 0, 0], [0, 3e4, 0], 
                     7e8, 6000, 5e26)
        star2 = Star("恒星B", 1.8e30, [1e11, 0, 0], [0, -3e4, 0], 
                     6e8, 5500, 4e26)
        
        self.simulation.add_object(star1)
        self.simulation.add_object(star2)
    
    def add_globular_cluster(self):
        """添加球状星团"""
        # 中心大质量恒星
        central_star = Star("中心恒星", 1e31, [0, 0, 0], [0, 0, 0], 
                            1e9, 10000, 1e28)
        self.simulation.add_object(central_star)
        
        # 添加多颗小质量恒星
        for i in range(50):
            # 随机位置 (球状分布)
            r = random.uniform(1e12, 1e14)
            theta = random.uniform(0, math.pi)
            phi = random.uniform(0, 2 * math.pi)
            
            x = r * math.sin(theta) * math.cos(phi)
            y = r * math.sin(theta) * math.sin(phi)
            z = r * math.cos(theta)
            
            # 计算轨道速度
            orbital_speed = math.sqrt(G * central_star.mass / r)
            
            # 速度方向垂直于位置向量
            vx = -orbital_speed * y / r
            vy = orbital_speed * x / r
            vz = 0
            
            star = Star(f"星团恒星_{i}", random.uniform(0.5, 2) * 1.989e30,
                       [x, y, z], [vx, vy, vz],
                       random.uniform(0.5, 2) * 6.96e8,
                       random.uniform(4000, 10000),
                       random.uniform(0.1, 5) * 3.828e26)
            
            self.simulation.add_object(star)
    
    def add_spiral_galaxy(self):
        """添加螺旋星系"""
        galaxy = Galaxy("螺旋星系", "spiral", 1e40, 1e20, 100)
        for star in galaxy.stars:
            self.simulation.add_object(star)
    
    def add_custom_star(self):
        """添加自定义恒星"""
        # 在实际应用中，这里应该打开一个对话框让用户输入参数
        # 这里我们添加一个随机恒星作为示例
        mass = random.uniform(0.1, 10) * 1.989e30
        radius = random.uniform(0.5, 5) * 6.96e8
        temperature = random.uniform(3000, 30000)
        luminosity = mass**3.5 * 3.828e26
        
        # 随机位置和速度
        x = random.uniform(-1e15, 1e15)
        y = random.uniform(-1e15, 1e15)
        z = random.uniform(-1e14, 1e14)
        
        vx = random.uniform(-1e4, 1e4)
        vy = random.uniform(-1e4, 1e4)
        vz = random.uniform(-1e3, 1e3)
        
        star = Star(f"自定义恒星_{len(self.simulation.objects)}", 
                   mass, [x, y, z], [vx, vy, vz],
                   radius, temperature, luminosity)
        
        self.simulation.add_object(star)
    
    def add_custom_planet(self):
        """添加自定义行星"""
        # 在实际应用中，这里应该打开一个对话框让用户输入参数
        # 这里我们添加一个随机行星作为示例
        mass = random.uniform(0.1, 10) * 5.972e24
        radius = random.uniform(0.5, 5) * 6.371e6
        
        # 随机位置和速度
        x = random.uniform(-1e13, 1e13)
        y = random.uniform(-1e13, 1e13)
        z = random.uniform(-1e12, 1e12)
        
        vx = random.uniform(-1e4, 1e4)
        vy = random.uniform(-1e4, 1e4)
        vz = random.uniform(-1e3, 1e3)
        
        planet = Planet(f"自定义行星_{len(self.simulation.objects)}", 
                       mass, [x, y, z], [vx, vy, vz],
                       radius, random.uniform(0.1, 0.9), 
                       random.choice([True, False]))
        
        self.simulation.add_object(planet)
    
    def clear_all_objects(self):
        """清除所有天体"""
        self.simulation.objects.clear()
        self.update_info()
    
    def update_view_scale(self):
        """更新视图尺度"""
        scale = 10 ** self.scale_slider.value()
        self.scale_label.setText(f"1e{self.scale_slider.value()} m")
        # 在实际应用中，这里应该发射一个信号来更新视图
        # 例如: self.view_scale_changed.emit(scale)
    
    def toggle_trajectories(self, checked):
        """切换轨迹显示"""
        # 在实际应用中，这里应该发射一个信号
        # 例如: self.show_trajectories_changed.emit(checked)
        pass
    
    def toggle_labels(self, checked):
        """切换标签显示"""
        # 在实际应用中，这里应该发射一个信号
        # 例如: self.show_labels_changed.emit(checked)
        pass
    
    def update_info(self):
        """更新信息显示"""
        self.time_label.setText(f"模拟时间: {self.simulation.current_time:.2e} 秒")
        self.object_count_label.setText(f"天体数量: {len(self.simulation.objects)}")


class UniverseExplorer(QMainWindow):
    """宇宙探索者主窗口"""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("宇宙变迁系统 - 高级工具库")
        self.setGeometry(100, 100, 1600, 900)
        
        # 创建模拟器
        self.simulation = UniverseSimulation()
        
        # 创建UI组件
        self.setup_ui()
        
        # 连接信号
        self.simulation.simulation_updated.connect(self.on_simulation_updated)
        
    def setup_ui(self):
        """设置UI"""
        # 创建中央部件和布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        
        # 创建控制面板
        self.control_panel = ControlPanel(self.simulation)
        splitter.addWidget(self.control_panel)
        
        # 创建标签页
        self.tab_widget = QTabWidget()
        
        # 3D视图标签页
        self.universe_viewer = UniverseViewer()
        self.tab_widget.addTab(self.universe_viewer, "3D宇宙视图")
        
        # 数据分析标签页
        self.data_analysis = DataAnalysisWidget()
        self.tab_widget.addTab(self.data_analysis, "数据分析")
        
        # 信息标签页
        self.info_text = QTextEdit()
        self.info_text.setReadOnly(True)
        self.tab_widget.addTab(self.info_text, "系统信息")
        
        splitter.addWidget(self.tab_widget)
        
        # 设置分割器比例
        splitter.setSizes([300, 1300])
        
        # 主布局
        layout = QHBoxLayout()
        layout.addWidget(splitter)
        central_widget.setLayout(layout)
        
        # 创建菜单栏
        self.create_menus()
        
        # 创建状态栏
        self.statusBar().showMessage("就绪")
        
        # 初始信息
        self.update_info_text()
    
    def create_menus(self):
        """创建菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu("文件")
        
        new_action = file_menu.addAction("新建模拟")
        load_action = file_menu.addAction("加载模拟")
        save_action = file_menu.addAction("保存模拟")
        file_menu.addSeparator()
        exit_action = file_menu.addAction("退出")
        
        # 模拟菜单
        sim_menu = menubar.addMenu("模拟")
        
        start_action = sim_menu.addAction("开始模拟")
        pause_action = sim_menu.addAction("暂停模拟")
        stop_action = sim_menu.addAction("停止模拟")
        reset_action = sim_menu.addAction("重置模拟")
        
        # 视图菜单
        view_menu = menubar.addMenu("视图")
        
        view_3d_action = view_menu.addAction("3D视图")
        view_data_action = view_menu.addAction("数据分析")
        view_info_action = view_menu.addAction("系统信息")
        
        # 帮助菜单
        help_menu = menubar.addMenu("帮助")
        
        about_action = help_menu.addAction("关于")
        
        # 连接菜单动作
        exit_action.triggered.connect(self.close)
        start_action.triggered.connect(self.control_panel.start_simulation)
        pause_action.triggered.connect(self.control_panel.pause_simulation)
        stop_action.triggered.connect(self.control_panel.stop_simulation)
        reset_action.triggered.connect(self.control_panel.reset_simulation)
    
    def on_simulation_updated(self, objects):
        """当模拟更新时调用"""
        # 更新3D视图
        self.universe_viewer.update_view(objects)
        
        # 更新数据分析
        self.data_analysis.update_analysis(objects)
        
        # 更新控制面板信息
        self.control_panel.update_info()
        
        # 更新状态栏
        self.statusBar().showMessage(f"模拟运行中 - 天体数量: {len(objects)}")
    
    def update_info_text(self):
        """更新信息文本"""
        info = """
        <h1>宇宙变迁系统 - 高级工具库</h1>
        
        <h2>系统功能</h2>
        <ul>
            <li><b>3D宇宙模拟:</b> 基于物理定律的N体模拟</li>
            <li><b>多种天体类型:</b> 恒星、行星、星系等</li>
            <li><b>实时可视化:</b> 3D视图显示天体运动和轨迹</li>
            <li><b>数据分析:</b> 物理参数统计和图表分析</li>
            <li><b>预设系统:</b> 太阳系、双星系统、星团、星系等</li>
        </ul>
        
        <h2>物理模型</h2>
        <ul>
            <li><b>万有引力:</b> 使用牛顿万有引力定律计算天体间相互作用</li>
            <li><b>运动方程:</b> 使用数值积分方法求解天体运动</li>
            <li><b>恒星物理:</b> 包含质量-光度关系、温度-颜色关系等</li>
            <li><b>星系生成:</b> 基于数学模型生成不同类型的星系</li>
        </ul>
        
        <h2>使用说明</h2>
        <ol>
            <li>在控制面板中选择预设系统或添加自定义天体</li>
            <li>调整模拟参数（时间步长、模拟速度等）</li>
            <li>开始模拟并观察天体运动</li>
            <li>使用数据分析功能查看物理参数</li>
            <li>通过视图控制调整显示选项</li>
        </ol>
        
        <p><i>注意: 这是一个简化模型，用于教育和演示目的。真实的宇宙模拟需要更复杂的物理模型和计算资源。</i></p>
        """
        
        self.info_text.setHtml(info)


def main():
    """主函数"""
    app = QApplication(sys.argv)
    
    # 设置应用程序样式
    app.setStyle('Fusion')
    
    # 创建主窗口
    window = UniverseExplorer()
    window.show()
    
    # 运行应用程序
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()