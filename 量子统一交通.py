import sys
import numpy as np
import pandas as pd
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QSlider, 
                             QComboBox, QSpinBox, QGroupBox, QTabWidget,
                             QTextEdit, QProgressBar)
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QPainter, QColor, QPen, QFont
import matplotlib
matplotlib.rc("font", family='Microsoft YaHei')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.animation as animation
from scipy import stats
import random
from collections import deque

class TrafficCell:
    """交通元胞类"""
    def __init__(self, position, road_type="highway"):
        self.position = position
        self.vehicle = None
        self.road_type = road_type
        self.traffic_light = None  # None, "red", "green"
        self.congestion_level = 0  # 0-1, 拥堵程度
        
class Vehicle:
    """车辆类"""
    def __init__(self, vehicle_id, max_speed=5):
        self.id = vehicle_id
        self.speed = 0
        self.max_speed = max_speed
        self.position = 0
        self.destination = None
        self.route = []
        self.type = random.choice(["car", "truck", "bus"])
        
class TrafficEntropyAnalyzer:
    """交通熵分析器"""
    def __init__(self):
        self.entropy_history = deque(maxlen=1000)
        self.congestion_history = deque(maxlen=1000)
        
    def calculate_traffic_entropy(self, road):
        """计算交通流熵值"""
        if len(road.cells) == 0:
            return 0
            
        # 速度分布熵
        speeds = [cell.vehicle.speed if cell.vehicle else 0 for cell in road.cells]
        speed_entropy = self._shannon_entropy(speeds)
        
        # 密度分布熵
        densities = self._calculate_local_density(road)
        density_entropy = self._shannon_entropy(densities)
        
        # 综合交通熵
        traffic_entropy = 0.6 * speed_entropy + 0.4 * density_entropy
        self.entropy_history.append(traffic_entropy)
        
        return traffic_entropy
    
    def _shannon_entropy(self, data):
        """计算香农熵"""
        if len(data) == 0:
            return 0
            
        # 归一化处理
        data = np.array(data)
        if np.sum(data) > 0:
            data = data / np.sum(data)
        
        # 计算熵值
        entropy = 0
        for value in data:
            if value > 0:
                entropy -= value * np.log2(value)
                
        return entropy
    
    def _calculate_local_density(self, road, window_size=5):
        """计算局部密度"""
        densities = []
        cells = road.cells
        
        for i in range(len(cells)):
            start = max(0, i - window_size // 2)
            end = min(len(cells), i + window_size // 2 + 1)
            
            local_cells = cells[start:end]
            vehicle_count = sum(1 for cell in local_cells if cell.vehicle)
            density = vehicle_count / len(local_cells)
            densities.append(density)
            
        return densities
    
    def predict_congestion(self, time_horizon=10):
        """预测未来拥堵情况"""
        if len(self.entropy_history) < 20:
            return "稳定"
            
        recent_entropy = list(self.entropy_history)[-20:]
        entropy_trend = np.polyfit(range(len(recent_entropy)), recent_entropy, 1)[0]
        
        if entropy_trend > 0.01:
            return "拥堵加剧"
        elif entropy_trend < -0.01:
            return "拥堵缓解"
        else:
            return "保持稳定"

class Road:
    """道路类"""
    def __init__(self, length=100, lanes=3):
        self.length = length
        self.lanes = lanes
        self.cells = []
        self.initialize_road()
        
    def initialize_road(self):
        """初始化道路"""
        self.cells = []
        for lane in range(self.lanes):
            for pos in range(self.length):
                self.cells.append(TrafficCell((pos, lane)))
                
    def add_vehicle(self, vehicle, position):
        """在指定位置添加车辆"""
        cell_index = position[1] * self.length + position[0]
        if 0 <= cell_index < len(self.cells) and self.cells[cell_index].vehicle is None:
            self.cells[cell_index].vehicle = vehicle
            vehicle.position = position
            return True
        return False
    
    def move_vehicle(self, vehicle, new_position):
        """移动车辆到新位置"""
        old_cell_index = vehicle.position[1] * self.length + vehicle.position[0]
        new_cell_index = new_position[1] * self.length + new_position[0]
        
        if (0 <= new_cell_index < len(self.cells) and 
            self.cells[new_cell_index].vehicle is None):
            
            self.cells[old_cell_index].vehicle = None
            self.cells[new_cell_index].vehicle = vehicle
            vehicle.position = new_position
            return True
            
        return False

class TrafficSimulation:
    """交通流模拟核心类"""
    def __init__(self, road_length=100, lanes=3, vehicle_density=0.2):
        self.road = Road(road_length, lanes)
        self.vehicles = []
        self.time_step = 0
        self.entropy_analyzer = TrafficEntropyAnalyzer()
        self.vehicle_density = vehicle_density
        self.max_speed = 5
        self.initialize_vehicles()
        
    def initialize_vehicles(self):
        """初始化车辆"""
        self.vehicles = []
        vehicle_count = int(self.road.length * self.road.lanes * self.vehicle_density)
        
        for i in range(vehicle_count):
            vehicle = Vehicle(i, self.max_speed)
            
            # 随机放置车辆
            placed = False
            attempts = 0
            while not placed and attempts < 100:
                lane = random.randint(0, self.road.lanes - 1)
                position = random.randint(0, self.road.length - 1)
                placed = self.road.add_vehicle(vehicle, (position, lane))
                attempts += 1
                
            if placed:
                self.vehicles.append(vehicle)
    
    def update(self):
        """更新模拟状态"""
        self.time_step += 1
        
        # 随机化车辆更新顺序
        random.shuffle(self.vehicles)
        
        for vehicle in self.vehicles:
            self.update_vehicle(vehicle)
            
        # 计算当前熵值
        current_entropy = self.entropy_analyzer.calculate_traffic_entropy(self.road)
        
        return current_entropy
    
    def update_vehicle(self, vehicle):
        """更新单个车辆状态"""
        current_x, current_lane = vehicle.position
        
        # 1. 加速
        if vehicle.speed < vehicle.max_speed:
            vehicle.speed += 1
            
        # 2. 减速（避免碰撞）
        gap = self.distance_to_next_vehicle(vehicle)
        if gap <= vehicle.speed:
            vehicle.speed = max(0, gap - 1)
            
        # 3. 随机慢化
        if random.random() < 0.1:  # 10%概率随机减速
            vehicle.speed = max(0, vehicle.speed - 1)
            
        # 4. 变道决策
        if self.should_change_lane(vehicle):
            new_lane = self.choose_best_lane(vehicle)
            if new_lane != current_lane and self.can_change_lane(vehicle, new_lane):
                current_lane = new_lane
                
        # 5. 移动
        if vehicle.speed > 0:
            new_x = (current_x + vehicle.speed) % self.road.length
            new_position = (new_x, current_lane)
            self.road.move_vehicle(vehicle, new_position)
    
    def distance_to_next_vehicle(self, vehicle):
        """计算到前车的距离"""
        current_x, lane = vehicle.position
        
        for distance in range(1, self.road.length):
            check_x = (current_x + distance) % self.road.length
            cell_index = lane * self.road.length + check_x
            
            if cell_index < len(self.road.cells) and self.road.cells[cell_index].vehicle:
                return distance - 1
                
        return self.road.length - 1
    
    def should_change_lane(self, vehicle):
        """判断是否需要变道"""
        current_gap = self.distance_to_next_vehicle(vehicle)
        return current_gap < vehicle.max_speed and random.random() < 0.3
    
    def choose_best_lane(self, vehicle):
        """选择最佳车道"""
        current_x, current_lane = vehicle.position
        best_lane = current_lane
        best_gap = self.distance_to_next_vehicle(vehicle)
        
        for lane_offset in [-1, 1]:
            test_lane = current_lane + lane_offset
            if 0 <= test_lane < self.road.lanes:
                # 临时检查目标车道的前后间隙
                test_vehicle = Vehicle(-1)  # 临时车辆用于计算
                test_vehicle.position = (current_x, test_lane)
                gap = self.distance_to_next_vehicle(test_vehicle)
                
                if gap > best_gap:
                    best_gap = gap
                    best_lane = test_lane
                    
        return best_lane
    
    def can_change_lane(self, vehicle, new_lane):
        """检查是否可以安全变道"""
        current_x, current_lane = vehicle.position
        
        # 检查目标车道位置是否有车
        target_cell_index = new_lane * self.road.length + current_x
        if (target_cell_index < len(self.road.cells) and 
            self.road.cells[target_cell_index].vehicle):
            return False
            
        return True

class TrafficCanvas(FigureCanvas):
    """交通可视化画布"""
    def __init__(self, simulation, width=10, height=6, dpi=100):
        self.fig, (self.ax1, self.ax2) = plt.subplots(2, 1, figsize=(width, height), dpi=dpi)
        super().__init__(self.fig)
        self.simulation = simulation
        self.setup_plots()
        
    def setup_plots(self):
        """设置绘图参数"""
        self.ax1.set_title('实时交通流模拟')
        self.ax1.set_xlabel('道路位置')
        self.ax1.set_ylabel('车道')
        self.ax1.set_xlim(0, self.simulation.road.length)
        self.ax1.set_ylim(-0.5, self.simulation.road.lanes - 0.5)
        
        self.ax2.set_title('交通熵变化趋势')
        self.ax2.set_xlabel('时间步')
        self.ax2.set_ylabel('熵值')
        self.ax2.grid(True)
        
    def update_plot(self):
        """更新绘图"""
        self.ax1.clear()
        self.ax2.clear()
        
        # 绘制道路和车辆
        road = self.simulation.road
        for cell in road.cells:
            x, lane = cell.position
            color = 'white'
            if cell.vehicle:
                if cell.vehicle.type == "car":
                    color = 'blue'
                elif cell.vehicle.type == "truck":
                    color = 'red'
                else:  # bus
                    color = 'green'
                    
            self.ax1.scatter(x, lane, c=color, s=100, marker='s')
            
        self.ax1.set_title(f'实时交通流模拟 (时间步: {self.simulation.time_step})')
        self.ax1.set_xlabel('道路位置')
        self.ax1.set_ylabel('车道')
        self.ax1.set_xlim(0, road.length)
        self.ax1.set_ylim(-0.5, road.lanes - 0.5)
        
        # 绘制熵变化曲线
        entropy_history = list(self.simulation.entropy_analyzer.entropy_history)
        if entropy_history:
            time_steps = range(len(entropy_history))
            self.ax2.plot(time_steps, entropy_history, 'b-', linewidth=2)
            self.ax2.set_title('交通熵变化趋势')
            self.ax2.set_xlabel('时间步')
            self.ax2.set_ylabel('熵值')
            self.ax2.grid(True)
            
        self.fig.tight_layout()
        self.draw()

class ControlPanel(QWidget):
    """控制面板"""
    def __init__(self, simulation):
        super().__init__()
        self.simulation = simulation
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 模拟控制组
        control_group = QGroupBox("模拟控制")
        control_layout = QVBoxLayout()
        
        self.start_btn = QPushButton("开始模拟")
        self.pause_btn = QPushButton("暂停")
        self.reset_btn = QPushButton("重置模拟")
        
        control_layout.addWidget(self.start_btn)
        control_layout.addWidget(self.pause_btn)
        control_layout.addWidget(self.reset_btn)
        control_group.setLayout(control_layout)
        
        # 参数设置组
        param_group = QGroupBox("模拟参数")
        param_layout = QVBoxLayout()
        
        # 车辆密度
        density_layout = QHBoxLayout()
        density_layout.addWidget(QLabel("车辆密度:"))
        self.density_slider = QSlider(Qt.Horizontal)
        self.density_slider.setRange(5, 80)
        self.density_slider.setValue(int(self.simulation.vehicle_density * 100))
        self.density_label = QLabel(f"{self.simulation.vehicle_density:.2f}")
        density_layout.addWidget(self.density_slider)
        density_layout.addWidget(self.density_label)
        param_layout.addLayout(density_layout)
        
        # 最大速度
        speed_layout = QHBoxLayout()
        speed_layout.addWidget(QLabel("最大速度:"))
        self.speed_spin = QSpinBox()
        self.speed_spin.setRange(1, 10)
        self.speed_spin.setValue(self.simulation.max_speed)
        speed_layout.addWidget(self.speed_spin)
        param_layout.addLayout(speed_layout)
        
        # 车道数量
        lanes_layout = QHBoxLayout()
        lanes_layout.addWidget(QLabel("车道数量:"))
        self.lanes_spin = QSpinBox()
        self.lanes_spin.setRange(1, 5)
        self.lanes_spin.setValue(self.simulation.road.lanes)
        lanes_layout.addWidget(self.lanes_spin)
        param_layout.addLayout(lanes_layout)
        
        param_group.setLayout(param_layout)
        
        # 状态信息组
        status_group = QGroupBox("实时状态")
        status_layout = QVBoxLayout()
        
        self.entropy_label = QLabel("当前熵值: 0.00")
        self.congestion_label = QLabel("拥堵预测: 稳定")
        self.vehicle_count_label = QLabel(f"车辆数量: {len(self.simulation.vehicles)}")
        
        status_layout.addWidget(self.entropy_label)
        status_layout.addWidget(self.congestion_label)
        status_layout.addWidget(self.vehicle_count_label)
        
        # 熵值进度条
        self.entropy_progress = QProgressBar()
        self.entropy_progress.setRange(0, 100)
        status_layout.addWidget(QLabel("熵值水平:"))
        status_layout.addWidget(self.entropy_progress)
        
        status_group.setLayout(status_layout)
        
        layout.addWidget(control_group)
        layout.addWidget(param_group)
        layout.addWidget(status_group)
        layout.addStretch()
        
        self.setLayout(layout)
        
        # 连接信号
        self.density_slider.valueChanged.connect(self.update_density)
        self.speed_spin.valueChanged.connect(self.update_speed)
        self.lanes_spin.valueChanged.connect(self.update_lanes)

    def update_density(self, value):
        density = value / 100.0
        self.density_label.setText(f"{density:.2f}")
        self.simulation.vehicle_density = density
        
    def update_speed(self, value):
        self.simulation.max_speed = value
        for vehicle in self.simulation.vehicles:
            vehicle.max_speed = value
            
    def update_lanes(self, value):
        self.simulation.road.lanes = value
        self.simulation.road.initialize_road()
        self.simulation.initialize_vehicles()

class MainWindow(QMainWindow):
    """主窗口"""
    def __init__(self):
        super().__init__()
        self.simulation = TrafficSimulation()
        self.init_ui()
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_simulation)
        self.is_running = False
        
    def init_ui(self):
        self.setWindowTitle("智能交通流熵分析系统")
        self.setGeometry(100, 100, 1400, 900)
        
        central_widget = QWidget()
        main_layout = QHBoxLayout()
        
        # 左侧控制面板
        self.control_panel = ControlPanel(self.simulation)
        main_layout.addWidget(self.control_panel)
        
        # 右侧可视化区域
        right_layout = QVBoxLayout()
        self.canvas = TrafficCanvas(self.simulation)
        right_layout.addWidget(self.canvas)
        
        # 信息显示区域
        self.info_text = QTextEdit()
        self.info_text.setMaximumHeight(150)
        self.info_text.setReadOnly(True)
        right_layout.addWidget(self.info_text)
        
        main_layout.addLayout(right_layout)
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)
        
        # 连接控制按钮
        self.control_panel.start_btn.clicked.connect(self.start_simulation)
        self.control_panel.pause_btn.clicked.connect(self.pause_simulation)
        self.control_panel.reset_btn.clicked.connect(self.reset_simulation)
        
        self.update_info("系统初始化完成，准备开始模拟...")
        
    def start_simulation(self):
        """开始模拟"""
        if not self.is_running:
            self.timer.start(100)  # 100ms更新一次
            self.is_running = True
            self.update_info("模拟开始运行...")
            
    def pause_simulation(self):
        """暂停模拟"""
        if self.is_running:
            self.timer.stop()
            self.is_running = False
            self.update_info("模拟已暂停")
            
    def reset_simulation(self):
        """重置模拟"""
        self.timer.stop()
        self.is_running = False
        
        # 重新初始化模拟
        road_length = self.simulation.road.length
        lanes = self.simulation.road.lanes
        density = self.simulation.vehicle_density
        max_speed = self.simulation.max_speed
        
        self.simulation = TrafficSimulation(road_length, lanes, density)
        self.simulation.max_speed = max_speed
        
        # 更新控制面板引用
        self.control_panel.simulation = self.simulation
        self.canvas.simulation = self.simulation
        
        self.canvas.update_plot()
        self.update_control_panel()
        self.update_info("模拟已重置")
        
    def update_simulation(self):
        """更新模拟状态"""
        current_entropy = self.simulation.update()
        
        # 更新可视化
        self.canvas.update_plot()
        
        # 更新控制面板状态
        self.update_control_panel(current_entropy)
        
        # 每50步更新一次信息
        if self.simulation.time_step % 50 == 0:
            congestion_pred = self.simulation.entropy_analyzer.predict_congestion()
            self.update_info(f"时间步 {self.simulation.time_step}: 熵值={current_entropy:.3f}, 预测={congestion_pred}")
            
    def update_control_panel(self, current_entropy=0):
        """更新控制面板显示"""
        self.control_panel.entropy_label.setText(f"当前熵值: {current_entropy:.3f}")
        
        # 更新进度条（假设熵值范围0-5）
        progress_value = min(100, int(current_entropy / 5.0 * 100))
        self.control_panel.entropy_progress.setValue(progress_value)
        
        # 更新拥堵预测
        congestion_pred = self.simulation.entropy_analyzer.predict_congestion()
        self.control_panel.congestion_label.setText(f"拥堵预测: {congestion_pred}")
        
        # 更新车辆数量
        vehicle_count = len(self.simulation.vehicles)
        self.control_panel.vehicle_count_label.setText(f"车辆数量: {vehicle_count}")
        
    def update_info(self, message):
        """更新信息显示"""
        timestamp = f"[{self.simulation.time_step:04d}] " if hasattr(self, 'simulation') else "[0000] "
        self.info_text.append(timestamp + message)

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()