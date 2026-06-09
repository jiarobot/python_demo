# -*- coding: utf-8 -*-
"""
Created on Tue Jun 17 23:29:02 2025

@author: 10166
"""

import sys
import random
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
matplotlib.rc("font", family='Microsoft YaHei')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QTabWidget, QTableWidget, QTableWidgetItem,
                             QGroupBox, QComboBox, QSlider, QSplitter, QStatusBar, QHeaderView)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor, QFont

class Drone:
    def __init__(self, id, drone_type, capacity, speed):
        self.id = id
        self.type = drone_type
        self.capacity = capacity  # kg
        self.speed = speed  # km/h
        self.position = [random.uniform(0, 100), random.uniform(0, 100)]
        self.altitude = random.uniform(50, 200)
        self.battery = 100
        self.status = "Standby"
        self.route = []
        self.current_task = None
        self.economic_value = 0
        
    def update_position(self):
        if self.route:
            target = self.route[0]
            dx = target[0] - self.position[0]
            dy = target[1] - self.position[1]
            distance = np.sqrt(dx**2 + dy**2)
            
            if distance < 1:  # Reached waypoint
                self.route.pop(0)
                if not self.route:
                    self.status = "Task Completed"
                    return
                target = self.route[0]
                dx = target[0] - self.position[0]
                dy = target[1] - self.position[1]
                distance = np.sqrt(dx**2 + dy**2)
            
            step = self.speed * 0.1 / 3.6  # Convert km/h to m/s * time step (0.1s)
            if distance > 0:
                self.position[0] += dx/distance * step
                self.position[1] += dy/distance * step
                
            # Update battery (1% per km)
            self.battery = max(0, self.battery - step/1000)
            
            if self.battery < 20 and self.status != "Returning":
                self.status = "Low Battery"
                
    def assign_task(self, task):
        self.current_task = task
        self.status = "On Mission"
        self.route = task["waypoints"]
        self.economic_value = task["value"]

class LowAirspaceControlSystem(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("低空经济总指挥系统")
        self.setGeometry(100, 100, 1400, 800)
        
        # Initialize system
        self.drones = []
        self.airspace_zones = {
            "Commercial": {"coords": [(20, 20), (80, 20), (80, 80), (20, 80)], "color": "lightblue"},
            "Residential": {"coords": [(0, 0), (40, 0), (40, 40), (0, 40)], "color": "lightgreen"},
            "Restricted": {"coords": [(60, 60), (100, 60), (100, 100), (60, 100)], "color": "pink"}
        }
        self.tasks = []
        self.time_step = 0
        
        # Create main widgets
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget)
        
        # Create left control panel
        self.control_panel = QWidget()
        self.control_layout = QVBoxLayout(self.control_panel)
        self.control_layout.setContentsMargins(10, 10, 10, 10)
        
        # Create visualization area
        self.visualization_tabs = QTabWidget()
        self.map_tab = QWidget()
        self.econ_tab = QWidget()
        self.stats_tab = QWidget()
        
        self.visualization_tabs.addTab(self.map_tab, "空域监控")
        self.visualization_tabs.addTab(self.econ_tab, "经济分析")
        self.visualization_tabs.addTab(self.stats_tab, "运行统计")
        
        # Setup map visualization
        self.setup_map_tab()
        self.setup_econ_tab()
        self.setup_stats_tab()
        
        # Add widgets to main layout
        self.main_layout.addWidget(self.control_panel, 1)
        self.main_layout.addWidget(self.visualization_tabs, 3)
        
        # Setup control panel
        self.setup_control_panel()
        
        # Setup drones
        self.initialize_drones()
        
        # Setup simulation timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_simulation)
        self.timer.start(100)  # Update every 100ms
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("系统就绪 | 低空经济总指挥系统 v1.0")
        
    def setup_control_panel(self):
        # System controls
        sys_ctrl_group = QGroupBox("系统控制")
        sys_layout = QVBoxLayout(sys_ctrl_group)
        
        self.start_btn = QPushButton("启动系统")
        self.pause_btn = QPushButton("暂停")
        self.reset_btn = QPushButton("重置")
        self.add_drone_btn = QPushButton("添加无人机")
        self.add_task_btn = QPushButton("添加任务")
        
        sys_layout.addWidget(self.start_btn)
        sys_layout.addWidget(self.pause_btn)
        sys_layout.addWidget(self.reset_btn)
        sys_layout.addWidget(self.add_drone_btn)
        sys_layout.addWidget(self.add_task_btn)
        
        # Drone management
        drone_group = QGroupBox("无人机管理")
        drone_layout = QVBoxLayout(drone_group)
        
        self.drone_table = QTableWidget()
        self.drone_table.setColumnCount(6)
        self.drone_table.setHorizontalHeaderLabels(["ID", "类型", "位置", "高度", "电量", "状态"])
        self.drone_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        drone_layout.addWidget(self.drone_table)
        
        # Task management
        task_group = QGroupBox("任务管理")
        task_layout = QVBoxLayout(task_group)
        
        self.task_table = QTableWidget()
        self.task_table.setColumnCount(4)
        self.task_table.setHorizontalHeaderLabels(["ID", "类型", "价值", "状态"])
        self.task_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        task_layout.addWidget(self.task_table)
        
        # Add groups to control panel
        self.control_layout.addWidget(sys_ctrl_group)
        self.control_layout.addWidget(drone_group, 2)
        self.control_layout.addWidget(task_group, 1)
        
        # Connect buttons
        self.start_btn.clicked.connect(self.start_simulation)
        self.pause_btn.clicked.connect(self.pause_simulation)
        self.reset_btn.clicked.connect(self.reset_simulation)
        self.add_drone_btn.clicked.connect(self.add_drone)
        self.add_task_btn.clicked.connect(self.add_task)
        
    def setup_map_tab(self):
        layout = QVBoxLayout(self.map_tab)
        
        # Create matplotlib figure
        self.map_fig = Figure(figsize=(10, 8), dpi=100)
        self.map_ax = self.map_fig.add_subplot(111)
        self.map_canvas = FigureCanvas(self.map_fig)
        
        layout.addWidget(self.map_canvas)
        
        # Draw initial map
        self.draw_map()
        
    def setup_econ_tab(self):
        layout = QVBoxLayout(self.econ_tab)
        
        # Create matplotlib figure for economic analysis
        self.econ_fig = Figure(figsize=(10, 8), dpi=100)
        self.econ_ax = self.econ_fig.add_subplot(111)
        self.econ_canvas = FigureCanvas(self.econ_fig)
        
        layout.addWidget(self.econ_canvas)
        
        # Initial economic plot
        self.update_econ_plot()
        
    def setup_stats_tab(self):
        layout = QVBoxLayout(self.stats_tab)
        
        # Stats display
        stats_group = QGroupBox("实时统计")
        stats_layout = QVBoxLayout(stats_group)
        
        self.stats_labels = {}
        stats = [
            ("total_drones", "无人机总数"),
            ("active_drones", "执行任务无人机"),
            ("completed_tasks", "完成任务数"),
            ("total_value", "经济总价值"),
            ("avg_speed", "平均速度 (km/h)"),
            ("battery_health", "平均电量")
        ]
        
        for stat_id, stat_name in stats:
            label = QLabel(f"{stat_name}: 0")
            label.setFont(QFont("Arial", 10))
            stats_layout.addWidget(label)
            self.stats_labels[stat_id] = label
        
        # Utilization chart
        self.util_fig = Figure(figsize=(10, 4), dpi=100)
        self.util_ax = self.util_fig.add_subplot(111)
        self.util_canvas = FigureCanvas(self.util_fig)
        
        layout.addWidget(stats_group)
        layout.addWidget(self.util_canvas)
        
    def initialize_drones(self):
        # Create initial drone fleet
        drone_types = [
            ("物流无人机", 5, 60),
            ("巡检无人机", 2, 80),
            ("测绘无人机", 3, 50),
            ("应急无人机", 10, 70)
        ]
        
        for i in range(8):
            drone_type, capacity, speed = random.choice(drone_types)
            self.drones.append(Drone(i+1, drone_type, capacity, speed))
            
        # Create initial tasks
        for i in range(5):
            self.add_task()
            
        # Update tables
        self.update_drone_table()
        self.update_task_table()
            
    def draw_map(self):
        self.map_ax.clear()
        self.map_ax.set_title("低空空域监控图")
        self.map_ax.set_xlabel("经度 (km)")
        self.map_ax.set_ylabel("纬度 (km)")
        self.map_ax.grid(True)
        self.map_ax.set_xlim(0, 100)
        self.map_ax.set_ylim(0, 100)
        
        # Draw airspace zones
        for zone, data in self.airspace_zones.items():
            coords = data["coords"]
            x = [c[0] for c in coords]
            y = [c[1] for c in coords]
            x.append(coords[0][0])
            y.append(coords[0][1])
            self.map_ax.plot(x, y, 'k-')
            self.map_ax.fill(x, y, alpha=0.3, color=data["color"])
            self.map_ax.text(np.mean(x), np.mean(y), zone, 
                           ha='center', va='center', fontsize=10)
        
        # Draw drones
        for drone in self.drones:
            color = {
                "Standby": "gray",
                "On Mission": "blue",
                "Returning": "orange",
                "Low Battery": "red",
                "Task Completed": "green"
            }.get(drone.status, "black")
            
            self.map_ax.plot(drone.position[0], drone.position[1], 'o', 
                           markersize=10, color=color)
            self.map_ax.text(drone.position[0], drone.position[1]+2, 
                           f"ID:{drone.id}", fontsize=8)
            
            # Draw route if exists
            if drone.route:
                route_x = [drone.position[0]] + [p[0] for p in drone.route]
                route_y = [drone.position[1]] + [p[1] for p in drone.route]
                self.map_ax.plot(route_x, route_y, 'r--', linewidth=1)
                
        self.map_canvas.draw()
        
    def update_econ_plot(self):
        self.econ_ax.clear()
        
        # Simulate economic data
        time_points = np.arange(10)
        values = np.cumsum(np.random.randint(5, 20, size=10))
        
        self.econ_ax.bar(time_points, values, color='skyblue')
        self.econ_ax.set_title("低空经济价值趋势")
        self.econ_ax.set_xlabel("时间 (小时)")
        self.econ_ax.set_ylabel("经济价值 (千元)")
        self.econ_ax.grid(True, linestyle='--', alpha=0.7)
        
        self.econ_canvas.draw()
        
    def update_util_plot(self):
        self.util_ax.clear()
        
        # Calculate utilizations
        zones = list(self.airspace_zones.keys())
        utilizations = [random.randint(30, 90) for _ in zones]
        
        self.util_ax.bar(zones, utilizations, color=['lightblue', 'lightgreen', 'pink'])
        self.util_ax.set_title("空域资源利用率")
        self.util_ax.set_ylabel("利用率 (%)")
        self.util_ax.set_ylim(0, 100)
        self.util_ax.grid(True, axis='y', linestyle='--', alpha=0.7)
        
        self.util_canvas.draw()
        
    def update_stats(self):
        total_drones = len(self.drones)
        active_drones = sum(1 for d in self.drones if d.status == "On Mission")
        completed_tasks = sum(1 for t in self.tasks if t.get("completed", False))
        total_value = sum(d.economic_value for d in self.drones)
        avg_speed = np.mean([d.speed for d in self.drones]) if self.drones else 0
        battery_health = np.mean([d.battery for d in self.drones]) if self.drones else 0
        
        self.stats_labels["total_drones"].setText(f"无人机总数: {total_drones}")
        self.stats_labels["active_drones"].setText(f"执行任务无人机: {active_drones}")
        self.stats_labels["completed_tasks"].setText(f"完成任务数: {completed_tasks}")
        self.stats_labels["total_value"].setText(f"经济总价值: ¥{total_value:.2f}")
        self.stats_labels["avg_speed"].setText(f"平均速度 (km/h): {avg_speed:.1f}")
        self.stats_labels["battery_health"].setText(f"平均电量: {battery_health:.1f}%")
        
    def update_drone_table(self):
        self.drone_table.setRowCount(len(self.drones))
        
        for i, drone in enumerate(self.drones):
            self.drone_table.setItem(i, 0, QTableWidgetItem(str(drone.id)))
            self.drone_table.setItem(i, 1, QTableWidgetItem(drone.type))
            self.drone_table.setItem(i, 2, QTableWidgetItem(f"({drone.position[0]:.1f}, {drone.position[1]:.1f})"))
            self.drone_table.setItem(i, 3, QTableWidgetItem(f"{drone.altitude:.1f} m"))
            self.drone_table.setItem(i, 4, QTableWidgetItem(f"{drone.battery:.1f}%"))
            
            status_item = QTableWidgetItem(drone.status)
            if drone.status == "Low Battery":
                status_item.setBackground(QColor(255, 200, 200))
            elif drone.status == "On Mission":
                status_item.setBackground(QColor(200, 230, 255))
            elif drone.status == "Task Completed":
                status_item.setBackground(QColor(200, 255, 200))
                
            self.drone_table.setItem(i, 5, status_item)
            
    def update_task_table(self):
        self.task_table.setRowCount(len(self.tasks))
        
        for i, task in enumerate(self.tasks):
            self.task_table.setItem(i, 0, QTableWidgetItem(str(task["id"])))
            self.task_table.setItem(i, 1, QTableWidgetItem(task["type"]))
            self.task_table.setItem(i, 2, QTableWidgetItem(f"¥{task['value']:.2f}"))
            
            status = "已完成" if task.get("completed", False) else "进行中"
            status_item = QTableWidgetItem(status)
            status_item.setBackground(QColor(200, 255, 200) if status == "已完成" else QColor(200, 230, 255))
            self.task_table.setItem(i, 3, status_item)
            
    def add_drone(self):
        drone_types = [
            ("物流无人机", 5, 60),
            ("巡检无人机", 2, 80),
            ("测绘无人机", 3, 50),
            ("应急无人机", 10, 70)
        ]
        
        drone_type, capacity, speed = random.choice(drone_types)
        new_id = max(d.id for d in self.drones) + 1 if self.drones else 1
        self.drones.append(Drone(new_id, drone_type, capacity, speed))
        self.update_drone_table()
        
    def add_task(self):
        task_types = ["物流配送", "设备巡检", "地理测绘", "应急响应", "环境监测"]
        task = {
            "id": len(self.tasks) + 1,
            "type": random.choice(task_types),
            "value": random.uniform(100, 1000),
            "waypoints": [
                [random.uniform(10, 90), random.uniform(10, 90)],
                [random.uniform(10, 90), random.uniform(10, 90)]
            ],
            "completed": False
        }
        
        self.tasks.append(task)
        
        # Assign to available drone
        available_drones = [d for d in self.drones if d.status == "Standby"]
        if available_drones:
            drone = random.choice(available_drones)
            drone.assign_task(task)
            
        self.update_task_table()
        
    def start_simulation(self):
        if not self.timer.isActive():
            self.timer.start(100)
            self.status_bar.showMessage("模拟运行中...")
            
    def pause_simulation(self):
        if self.timer.isActive():
            self.timer.stop()
            self.status_bar.showMessage("模拟已暂停")
            
    def reset_simulation(self):
        self.timer.stop()
        self.drones = []
        self.tasks = []
        self.time_step = 0
        self.initialize_drones()
        self.draw_map()
        self.update_econ_plot()
        self.status_bar.showMessage("系统已重置")
            
    def update_simulation(self):
        self.time_step += 1
        
        # Update drones
        for drone in self.drones:
            drone.update_position()
            
            # Check task completion
            if drone.status == "Task Completed":
                task = drone.current_task
                if task:
                    task["completed"] = True
                drone.current_task = None
                
            # Handle low battery
            if drone.status == "Low Battery":
                if not drone.route or drone.route != [[0, 0]]:  # Add return home
                    drone.status = "Returning"
                    drone.route = [[0, 0]]  # Home base
                    
            # If returned home
            if drone.status == "Returning" and not drone.route:
                drone.status = "Standby"
                drone.battery = 100  # Recharge
        
        # Assign new tasks
        if self.time_step % 20 == 0 and random.random() > 0.7:
            self.add_task()
            
        # Update displays
        self.draw_map()
        if self.time_step % 10 == 0:
            self.update_econ_plot()
            self.update_util_plot()
            
        self.update_drone_table()
        self.update_task_table()
        self.update_stats()
        
        # Update status
        self.status_bar.showMessage(f"模拟运行中... | 时间步: {self.time_step} | 活跃无人机: {sum(1 for d in self.drones if d.status == 'On Mission')}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    # Set custom palette
    palette = app.palette()
    palette.setColor(palette.Window, QColor(240, 245, 255))
    palette.setColor(palette.WindowText, Qt.darkBlue)
    palette.setColor(palette.Button, QColor(200, 220, 255))
    app.setPalette(palette)
    
    window = LowAirspaceControlSystem()
    window.show()
    sys.exit(app.exec_())