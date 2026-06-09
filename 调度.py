import sys
import numpy as np
import pandas as pd
import random
import math
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QPushButton, QComboBox, QSlider, QSplitter, QTableWidget,
                             QTableWidgetItem, QHeaderView, QGroupBox, QTabWidget)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor, QFont
from collections import deque
import networkx as nx
import folium
from folium.plugins import HeatMap
from io import BytesIO
from PIL import Image

class Drone:
    def __init__(self, drone_id, capacity=5, speed=15):
        self.id = drone_id
        self.capacity = capacity  # 最大载货量(kg)
        self.speed = speed  # 飞行速度(m/s)
        self.battery = 100  # 电池百分比
        self.location = (0, 0)  # 当前位置
        self.destination = None  # 目标位置
        self.path = []  # 飞行路径
        self.status = "idle"  # idle, charging, flying, delivering
        self.payload = 0  # 当前载货量
        self.deliveries = []  # 当前配送任务
        self.log = deque(maxlen=100)  # 操作日志
        
    def assign_delivery(self, delivery):
        if self.payload + delivery.weight <= self.capacity:
            self.deliveries.append(delivery)
            self.payload += delivery.weight
            self.log.append(f"Assigned delivery {delivery.id}")
            return True
        return False
    
    def start_delivery(self, path):
        if self.deliveries:
            self.destination = self.deliveries[0].destination
            self.path = path
            self.status = "flying"
            self.log.append(f"Started delivery to {self.destination}")
    
    def update_position(self):
        if self.status == "flying" and self.path:
            # 移动到路径中的下一个点
            self.location = self.path.pop(0)
            
            # 消耗电池 (基于距离和载重)
            battery_drain = 0.05 * (1 + self.payload/self.capacity)
            self.battery = max(0, self.battery - battery_drain)
            
            # 如果到达目的地
            if not self.path:
                self.status = "delivering"
                self.log.append(f"Arrived at destination")
                # 模拟交付时间
                QTimer.singleShot(3000, self.complete_delivery)
    
    def complete_delivery(self):
        if self.deliveries:
            delivery = self.deliveries.pop(0)
            self.payload -= delivery.weight
            self.log.append(f"Completed delivery {delivery.id}")
            
            if self.deliveries:
                # 还有更多配送任务
                self.status = "flying"
                self.log.append(f"Moving to next delivery")
            else:
                self.status = "returning"
                self.log.append(f"Returning to base")
    
    def return_to_base(self, base_location):
        self.destination = base_location
        # 简单直线返回路径
        self.path = self.calculate_straight_path(self.location, base_location)
        self.status = "flying"
    
    def calculate_straight_path(self, start, end):
        """生成两点间的直线路径"""
        path = []
        steps = 20
        for i in range(steps + 1):
            lat = start[0] + (end[0] - start[0]) * i / steps
            lon = start[1] + (end[1] - start[1]) * i / steps
            path.append((lat, lon))
        return path
    
    def charge(self):
        if self.status == "charging":
            self.battery = min(100, self.battery + 1)
            if self.battery == 100:
                self.status = "idle"
                self.log.append("Fully charged and ready")

class Delivery:
    def __init__(self, delivery_id, origin, destination, weight, priority=1):
        self.id = delivery_id
        self.origin = origin  # 起始位置 (lat, lon)
        self.destination = destination  # 目标位置 (lat, lon)
        self.weight = weight  # 重量(kg)
        self.priority = priority  # 优先级 (1-5)
        self.status = "pending"  # pending, assigned, in_progress, delivered
        self.assigned_drone = None
        self.create_time = pd.Timestamp.now()
        self.complete_time = None

class EnvironmentMap:
    def __init__(self, center=(30.2672, -97.7431), size=(10, 10)):
        self.center = center
        self.size = size  # 区域大小 (km)
        self.obstacles = self.generate_obstacles()
        self.charging_stations = self.generate_charging_stations()
        self.no_fly_zones = self.generate_no_fly_zones()
        self.delivery_points = self.generate_delivery_points()
        
    def generate_obstacles(self):
        """生成障碍物（建筑物）"""
        obstacles = []
        for _ in range(15):
            lat = self.center[0] + random.uniform(-0.05, 0.05)
            lon = self.center[1] + random.uniform(-0.05, 0.05)
            obstacles.append((lat, lon, random.uniform(50, 200)))  # (lat, lon, height)
        return obstacles
    
    def generate_charging_stations(self):
        """生成充电站"""
        stations = []
        for _ in range(4):
            lat = self.center[0] + random.uniform(-0.08, 0.08)
            lon = self.center[1] + random.uniform(-0.08, 0.08)
            stations.append((lat, lon))
        return stations
    
    def generate_no_fly_zones(self):
        """生成禁飞区"""
        zones = []
        for _ in range(3):
            lat = self.center[0] + random.uniform(-0.07, 0.07)
            lon = self.center[1] + random.uniform(-0.07, 0.07)
            radius = random.uniform(0.005, 0.015)
            zones.append((lat, lon, radius))
        return zones
    
    def generate_delivery_points(self):
        """生成配送点"""
        points = []
        for _ in range(30):
            lat = self.center[0] + random.uniform(-0.09, 0.09)
            lon = self.center[1] + random.uniform(-0.09, 0.09)
            points.append((lat, lon))
        return points
    
    def is_valid_path(self, start, end):
        """检查路径是否避开禁飞区"""
        for zone in self.no_fly_zones:
            zone_center = (zone[0], zone[1])
            radius = zone[2]
            if self.distance_to_line(start, end, zone_center) < radius:
                return False
        return True
    
    def distance_to_line(self, p1, p2, p3):
        """计算点到线段的距离"""
        # 将经纬度转换为平面坐标（简化处理）
        x1, y1 = p1[1], p1[0]
        x2, y2 = p2[1], p2[0]
        x3, y3 = p3[1], p3[0]
        
        # 计算点到直线的距离
        numerator = abs((y2-y1)*x3 - (x2-x1)*y3 + x2*y1 - y2*x1)
        denominator = math.sqrt((y2-y1)**2 + (x2-x1)**2)
        return numerator / denominator

class DroneScheduler:
    def __init__(self, drones, environment):
        self.drones = drones
        self.env = environment
        self.delivery_queue = []
        self.completed_deliveries = []
        self.performance_metrics = {
            "total_deliveries": 0,
            "avg_delivery_time": 0,
            "total_distance": 0,
            "energy_consumed": 0
        }
        
    def add_delivery(self, delivery):
        self.delivery_queue.append(delivery)
        self.assign_deliveries()
    
    def assign_deliveries(self):
        """分配配送任务到无人机"""
        # 按优先级和等待时间排序
        self.delivery_queue.sort(key=lambda d: (d.priority, d.create_time))
        
        for delivery in self.delivery_queue[:]:
            if delivery.status != "pending":
                continue
                
            # 寻找合适的无人机
            best_drone = None
            best_score = float('inf')
            
            for drone in self.drones:
                if drone.status in ["idle", "charging"] and drone.battery > 20:
                    # 简单评分：距离 + 当前负载
                    distance = self.calculate_distance(drone.location, delivery.origin)
                    score = distance * (1 + drone.payload/drone.capacity)
                    
                    if score < best_score:
                        best_score = score
                        best_drone = drone
            
            if best_drone and best_drone.assign_delivery(delivery):
                delivery.status = "assigned"
                delivery.assigned_drone = best_drone.id
                # 规划路径
                path = self.plan_path(best_drone.location, delivery.origin, delivery.destination)
                if path:
                    best_drone.start_delivery(path)
                    self.delivery_queue.remove(delivery)
    
    def plan_path(self, start, via, end):
        """规划路径：起点 -> 取货点 -> 送货点"""
        # 简单直线路径规划（实际应用中应使用A*等算法）
        path1 = self.calculate_straight_path(start, via)
        path2 = self.calculate_straight_path(via, end)
        return path1 + path2
    
    def calculate_straight_path(self, start, end):
        """计算两点间的直线路径"""
        path = []
        steps = 20
        for i in range(steps + 1):
            lat = start[0] + (end[0] - start[0]) * i / steps
            lon = start[1] + (end[1] - start[1]) * i / steps
            path.append((lat, lon))
        return path
    
    def calculate_distance(self, p1, p2):
        """计算两点间的大致距离（米）"""
        # 简化的Haversine公式实现
        lat1, lon1 = p1
        lat2, lon2 = p2
        
        R = 6371000  # 地球半径(米)
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)
        
        a = math.sin(delta_phi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(delta_lambda/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c
    
    def update_metrics(self, delivery):
        """更新性能指标"""
        self.performance_metrics["total_deliveries"] += 1
        delivery_time = (delivery.complete_time - delivery.create_time).total_seconds() / 60
        self.performance_metrics["avg_delivery_time"] = (
            self.performance_metrics["avg_delivery_time"] * (self.performance_metrics["total_deliveries"] - 1) + 
            delivery_time) / self.performance_metrics["total_deliveries"]
        
        # 估算距离
        distance = self.calculate_distance(delivery.origin, delivery.destination)
        self.performance_metrics["total_distance"] += distance
        
        # 估算能耗 (假设每米消耗0.1%电池)
        self.performance_metrics["energy_consumed"] += distance * 0.001

class SimulationVisualization(FigureCanvas):
    def __init__(self, parent=None, width=8, height=6, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        super().__init__(self.fig)
        self.setParent(parent)
        
        self.ax = self.fig.add_subplot(111)
        self.ax.set_title("Low-Altitude Economy Drone Operations")
        self.ax.set_xlabel("Longitude")
        self.ax.set_ylabel("Latitude")
        self.ax.grid(True, alpha=0.3)
        
        self.drone_scatter = None
        self.delivery_scatter = None
        self.obstacle_scatter = None
        self.station_scatter = None
        self.zone_circles = []
        self.path_lines = []
        
    def update_plot(self, scheduler, environment):
        self.ax.clear()
        self.ax.set_title("Low-Altitude Economy Drone Operations")
        self.ax.set_xlabel("Longitude")
        self.ax.set_ylabel("Latitude")
        self.ax.grid(True, alpha=0.3)
        
        # 绘制禁飞区
        self.zone_circles = []
        for zone in environment.no_fly_zones:
            circle = plt.Circle((zone[1], zone[0]), zone[2], color='red', alpha=0.2)
            self.ax.add_patch(circle)
            self.zone_circles.append(circle)
        
        # 绘制障碍物
        obs_x = [o[1] for o in environment.obstacles]
        obs_y = [o[0] for o in environment.obstacles]
        self.obstacle_scatter = self.ax.scatter(obs_x, obs_y, c='gray', s=50, marker='s', alpha=0.7, label='Buildings')
        
        # 绘制充电站
        station_x = [s[1] for s in environment.charging_stations]
        station_y = [s[0] for s in environment.charging_stations]
        self.station_scatter = self.ax.scatter(station_x, station_y, c='green', s=100, marker='^', label='Charging Stations')
        
        # 绘制配送点
        delivery_x = [d[1] for d in environment.delivery_points]
        delivery_y = [d[0] for d in environment.delivery_points]
        self.delivery_scatter = self.ax.scatter(delivery_x, delivery_y, c='blue', s=30, marker='o', alpha=0.5, label='Delivery Points')
        
        # 绘制无人机
        drone_x = [d.location[1] for d in scheduler.drones]
        drone_y = [d.location[0] for d in scheduler.drones]
        drone_colors = []
        for drone in scheduler.drones:
            if drone.status == "flying":
                drone_colors.append('orange')
            elif drone.status == "delivering":
                drone_colors.append('red')
            elif drone.status == "charging":
                drone_colors.append('purple')
            else:
                drone_colors.append('blue')
                
        self.drone_scatter = self.ax.scatter(drone_x, drone_y, c=drone_colors, s=80, marker='D', edgecolors='black', label='Drones')
        
        # 绘制无人机路径
        self.path_lines = []
        for drone in scheduler.drones:
            if drone.path:
                path_x = [p[1] for p in drone.path]
                path_y = [p[0] for p in drone.path]
                line, = self.ax.plot(path_x, path_y, '--', linewidth=1, alpha=0.7)
                self.path_lines.append(line)
        
        # 添加图例
        self.ax.legend(loc='upper right')
        
        # 设置合适的坐标范围
        min_lon = min([d[1] for d in environment.delivery_points] + [d.location[1] for d in scheduler.drones])
        max_lon = max([d[1] for d in environment.delivery_points] + [d.location[1] for d in scheduler.drones])
        min_lat = min([d[0] for d in environment.delivery_points] + [d.location[0] for d in scheduler.drones])
        max_lat = max([d[0] for d in environment.delivery_points] + [d.location[0] for d in scheduler.drones])
        
        self.ax.set_xlim(min_lon - 0.01, max_lon + 0.01)
        self.ax.set_ylim(min_lat - 0.01, max_lat + 0.01)
        
        self.draw()

class DroneControlPanel(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Low-Altitude Economy Drone Logistics System")
        self.setGeometry(100, 100, 1600, 900)
        
        # 初始化模拟环境
        self.environment = EnvironmentMap()
        self.drones = [Drone(i) for i in range(1, 6)]
        # 设置无人机初始位置为充电站
        for drone, station in zip(self.drones, self.environment.charging_stations):
            drone.location = station
        
        self.scheduler = DroneScheduler(self.drones, self.environment)
        self.delivery_counter = 1
        
        # 创建主界面
        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)
        self.main_layout = QHBoxLayout(self.main_widget)
        
        # 创建左侧控制面板
        self.control_panel = QWidget()
        self.control_layout = QVBoxLayout(self.control_panel)
        self.control_layout.setAlignment(Qt.AlignTop)
        
        # 创建右侧可视化区域
        self.visualization_tabs = QTabWidget()
        self.simulation_visual = SimulationVisualization(self)
        self.visualization_tabs.addTab(self.simulation_visual, "Simulation")
        
        # 添加分割器
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.addWidget(self.control_panel)
        self.splitter.addWidget(self.visualization_tabs)
        self.splitter.setSizes([400, 1200])
        self.main_layout.addWidget(self.splitter)
        
        # 创建控制面板组件
        self.create_control_panel()
        
        # 创建状态监控表格
        self.create_status_table()
        
        # 创建性能指标显示
        self.create_performance_metrics()
        
        # 创建日志显示
        self.create_log_display()
        
        # 设置定时器
        self.simulation_timer = QTimer(self)
        self.simulation_timer.timeout.connect(self.update_simulation)
        self.simulation_timer.start(1000)  # 每秒更新一次
        
        # 配送生成定时器
        self.delivery_timer = QTimer(self)
        self.delivery_timer.timeout.connect(self.generate_delivery)
        self.delivery_timer.start(5000)  # 每5秒生成一个配送
        
    def create_control_panel(self):
        # 标题
        title_label = QLabel("Drone Logistics Control Panel")
        title_label.setFont(QFont("Arial", 16, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        self.control_layout.addWidget(title_label)
        
        # 添加无人机按钮
        add_drone_btn = QPushButton("Add Drone")
        add_drone_btn.clicked.connect(self.add_drone)
        self.control_layout.addWidget(add_drone_btn)
        
        # 添加配送按钮
        add_delivery_btn = QPushButton("Add Delivery")
        add_delivery_btn.clicked.connect(self.add_delivery)
        self.control_layout.addWidget(add_delivery_btn)
        
        # 速度控制滑块
        speed_label = QLabel("Simulation Speed:")
        self.control_layout.addWidget(speed_label)
        
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setRange(1, 10)
        self.speed_slider.setValue(5)
        self.speed_slider.valueChanged.connect(self.adjust_speed)
        self.control_layout.addWidget(self.speed_slider)
        
        # 天气控制
        weather_group = QGroupBox("Weather Conditions")
        weather_layout = QVBoxLayout(weather_group)
        
        self.weather_combobox = QComboBox()
        self.weather_combobox.addItems(["Clear", "Light Wind", "Strong Wind", "Rain"])
        weather_layout.addWidget(self.weather_combobox)
        
        self.control_layout.addWidget(weather_group)
        
    def create_status_table(self):
        # 无人机状态表格
        self.drone_table = QTableWidget()
        self.drone_table.setColumnCount(6)
        self.drone_table.setHorizontalHeaderLabels(["ID", "Status", "Battery", "Payload", "Location", "Deliveries"])
        self.drone_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.control_layout.addWidget(QLabel("Drone Status:"))
        self.control_layout.addWidget(self.drone_table)
        
    def create_performance_metrics(self):
        # 性能指标显示
        metrics_group = QGroupBox("Performance Metrics")
        metrics_layout = QVBoxLayout(metrics_group)
        
        self.metrics_labels = {}
        metrics = ["total_deliveries", "avg_delivery_time", "total_distance", "energy_consumed"]
        for metric in metrics:
            label = QLabel(f"{metric.replace('_', ' ').title()}: 0")
            self.metrics_labels[metric] = label
            metrics_layout.addWidget(label)
        
        self.control_layout.addWidget(metrics_group)
        
    def create_log_display(self):
        # 日志显示
        log_group = QGroupBox("System Log")
        log_layout = QVBoxLayout(log_group)
        
        self.log_text = QLabel()
        self.log_text.setWordWrap(True)
        self.log_text.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.log_text.setMinimumHeight(150)
        self.log_text.setStyleSheet("background-color: #f0f0f0; padding: 5px;")
        
        log_layout.addWidget(self.log_text)
        self.control_layout.addWidget(log_group)
        
    def update_status_table(self):
        self.drone_table.setRowCount(len(self.drones))
        
        for i, drone in enumerate(self.drones):
            self.drone_table.setItem(i, 0, QTableWidgetItem(str(drone.id)))
            self.drone_table.setItem(i, 1, QTableWidgetItem(drone.status))
            
            # 根据电量设置颜色
            battery_item = QTableWidgetItem(f"{drone.battery}%")
            if drone.battery < 20:
                battery_item.setBackground(QColor(255, 200, 200))
            elif drone.battery < 50:
                battery_item.setBackground(QColor(255, 255, 200))
            self.drone_table.setItem(i, 2, battery_item)
            
            self.drone_table.setItem(i, 3, QTableWidgetItem(f"{drone.payload}/{drone.capacity} kg"))
            self.drone_table.setItem(i, 4, QTableWidgetItem(f"{drone.location[0]:.4f}, {drone.location[1]:.4f}"))
            self.drone_table.setItem(i, 5, QTableWidgetItem(str(len(drone.deliveries))))
        
    def update_performance_metrics(self):
        metrics = self.scheduler.performance_metrics
        for metric, label in self.metrics_labels.items():
            value = metrics[metric]
            if metric == "avg_delivery_time":
                label.setText(f"Avg Delivery Time: {value:.1f} min")
            elif metric == "total_distance":
                label.setText(f"Total Distance: {value/1000:.1f} km")
            elif metric == "energy_consumed":
                label.setText(f"Energy Consumed: {value:.1f} kWh")
            else:
                label.setText(f"{metric.replace('_', ' ').title()}: {value}")
                
    def update_log_display(self):
        # 收集所有无人机的日志
        all_logs = []
        for drone in self.drones:
            all_logs.extend(drone.log)
        
        # 按时间排序（简化处理）
        all_logs.sort(reverse=True)
        
        # 显示最近的10条日志
        log_text = "<br>".join(all_logs[:10])
        self.log_text.setText(log_text)
        
    def add_drone(self):
        new_id = max(drone.id for drone in self.drones) + 1
        new_drone = Drone(new_id)
        # 放置在随机充电站
        station = random.choice(self.environment.charging_stations)
        new_drone.location = station
        self.drones.append(new_drone)
        self.scheduler.drones = self.drones
        self.log_event(f"Drone {new_id} added at station {station}")
        
    def add_delivery(self):
        # 随机选择一个配送点作为起点和终点
        origin = random.choice(self.environment.delivery_points)
        destination = random.choice([p for p in self.environment.delivery_points if p != origin])
        
        delivery = Delivery(
            self.delivery_counter,
            origin,
            destination,
            weight=random.uniform(0.1, 3.0),
            priority=random.randint(1, 5)
        )
        self.scheduler.add_delivery(delivery)
        self.delivery_counter += 1
        self.log_event(f"Added delivery {delivery.id} from {origin} to {destination}")
        
    def generate_delivery(self):
        # 自动生成配送任务
        if random.random() < 0.7:  # 70%的概率生成新任务
            self.add_delivery()
        
    def update_simulation(self):
        # 更新所有无人机
        for drone in self.drones:
            if drone.status == "flying":
                drone.update_position()
            elif drone.status == "returning" and not drone.path:
                # 返回基地充电
                station = random.choice(self.environment.charging_stations)
                drone.return_to_base(station)
            elif drone.status == "charging":
                drone.charge()
        
        # 更新调度器
        self.scheduler.assign_deliveries()
        
        # 更新UI
        self.update_status_table()
        self.update_performance_metrics()
        self.update_log_display()
        self.simulation_visual.update_plot(self.scheduler, self.environment)
        
    def adjust_speed(self):
        speed = self.speed_slider.value()
        interval = 1100 - speed * 100  # 1000ms到100ms
        self.simulation_timer.setInterval(interval)
        
    def log_event(self, message):
        timestamp = pd.Timestamp.now().strftime("%H:%M:%S")
        for drone in self.drones:
            drone.log.append(f"{timestamp} - {message}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DroneControlPanel()
    window.show()
    sys.exit(app.exec_())