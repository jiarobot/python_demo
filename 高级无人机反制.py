import sys
import math
import random
import time
import numpy as np
from datetime import datetime
from threading import Thread, Timer
from collections import deque

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QGridLayout, QLabel, QPushButton, QComboBox, QSlider, 
                            QProgressBar, QTabWidget, QGroupBox, QTextEdit, QTableWidget,
                            QTableWidgetItem, QHeaderView, QSplitter, QFrame, QMessageBox)
from PyQt6.QtCore import QPointF, Qt, QTimer, pyqtSignal, QThread, QPoint, QRectF, QObject
from PyQt6.QtGui import QFont, QPalette, QColor, QPainter, QPen, QBrush, QLinearGradient
from PyQt6.QtCharts import QChart, QChartView, QLineSeries, QValueAxis, QSplineSeries


# 无人机类型和属性
DRONE_TYPES = {
    "侦查型": {"speed": 8, "range": 300, "threat_base": 0.3, "color": "#64C8FF", "icon": "🕵️"},
    "攻击型": {"speed": 12, "range": 200, "threat_base": 0.8, "color": "#FF6464", "icon": "💥"},
    "快递型": {"speed": 6, "range": 150, "threat_base": 0.2, "color": "#64FF64", "icon": "📦"},
    "蜂群型": {"speed": 10, "range": 100, "threat_base": 0.6, "color": "#FFC864", "icon": "🐝"},
    "未知型": {"speed": 7, "range": 250, "threat_base": 0.5, "color": "#C8C8C8", "icon": "❓"}
}

# 干扰模式
JAMMING_MODES = {
    "全频段干扰": {"power": 90, "range": 400, "effectiveness": 0.9, "color": "#FF6464"},
    "定向干扰": {"power": 70, "range": 600, "effectiveness": 0.95, "color": "#64C8FF"},
    "智能干扰": {"power": 60, "range": 500, "effectiveness": 0.85, "color": "#64FF64"},
    "欺骗干扰": {"power": 50, "range": 300, "effectiveness": 0.75, "color": "#FFC864"}
}

# 模拟无人机数据
class SimulatedDrone:
    def __init__(self, id):
        self.id = id
        self.type = random.choice(list(DRONE_TYPES.keys()))
        self.attributes = DRONE_TYPES[self.type]
        
        # 初始位置和速度
        angle = random.uniform(0, 2 * math.pi)
        distance = random.uniform(100, 800)
        self.position = np.array([
            distance * math.cos(angle),
            distance * math.sin(angle),
            random.uniform(50, 300)
        ])
        
        # 朝向目标点
        self.target = np.array([0.0, 0.0, 100.0]) # 默认朝向系统位置
        self.velocity = np.array([0.0, 0.0, 0.0])
        self.acceleration = np.array([0.0, 0.0, 0.0])
        
        # 状态属性
        self.threat_level = random.uniform(0.1, 0.8)
        self.detected = False
        self.interfered = False
        self.jamming_type = None
        self.signal_strength = random.uniform(0.3, 0.9)
        self.health = 100  # 无人机健康度
        self.battery = random.uniform(30, 100)  # 电池电量
        self.last_update = time.time()
        self.trajectory = [self.position.copy()]  # 轨迹记录
        self.communication_active = True
        self.stealth_mode = random.random() < 0.3  # 30%的无人机有隐身模式
        
        # AI行为参数
        self.aggressiveness = random.uniform(0.1, 0.9)
        self.avoidance_skill = random.uniform(0.3, 0.9)
        
        # 通信数据
        self.packet_loss = random.uniform(0.01, 0.2)
        self.data_rate = random.uniform(1.0, 10.0)  # Mbps
        
    def update(self, counter_system):
        current_time = time.time()
        dt = current_time - self.last_update
        self.last_update = current_time
        
        # 更新电池
        self.battery -= dt * 0.1
        if self.battery <= 0:
            self.battery = 0
            # 电池耗尽，无人机坠落
            self.velocity[2] -= dt * 2  # 重力加速度
        
        # AI决策：选择目标和行为
        self.ai_decision(counter_system)
        
        # 计算朝向目标的加速度
        direction = self.target - self.position
        distance = np.linalg.norm(direction)
        
        # 将 max_speed 的定义移到条件语句外部
        max_speed = self.attributes["speed"]
        
        if distance > 0.1:
            direction = direction / distance
            # 根据无人机类型调整速度
            desired_velocity = direction * max_speed
            
            # 转向力
            steering = desired_velocity - self.velocity
            steering = np.clip(steering, -2.0, 2.0)
            
            self.acceleration = steering * 0.5
            
            # 躲避其他无人机
            self.avoid_collisions(counter_system.drones)
            
            # 躲避干扰
            if self.interfered:
                # 尝试逃离干扰源
                escape_direction = self.position / np.linalg.norm(self.position)
                self.acceleration += escape_direction * 2.0
        
        # 更新速度和位置
        self.velocity += self.acceleration * dt
        self.velocity = np.clip(self.velocity, -max_speed, max_speed)
        self.position += self.velocity * dt
        
        # 限制高度
        self.position[2] = max(10, min(500, self.position[2]))
        
        # 记录轨迹（限制长度）
        self.trajectory.append(self.position.copy())
        if len(self.trajectory) > 100:
            self.trajectory.pop(0)
        
        # 更新威胁等级
        self.update_threat_level(counter_system)
        
        # 干扰效果
        if self.interfered:
            self.signal_strength -= dt * 0.2
            self.communication_active = random.random() > 0.3  # 70%概率通信中断
            self.packet_loss += dt * 0.05
            self.data_rate = max(0.1, self.data_rate - dt * 0.5)
        else:
            self.signal_strength += dt * 0.1
            self.communication_active = True
            self.packet_loss = max(0.01, self.packet_loss - dt * 0.01)
            self.data_rate = min(10.0, self.data_rate + dt * 0.1)
            
        self.signal_strength = np.clip(self.signal_strength, 0.1, 1.0)
        self.packet_loss = np.clip(self.packet_loss, 0.01, 0.5)
        self.data_rate = np.clip(self.data_rate, 0.1, 10.0)
        
        # 健康度更新
        if self.interfered and random.random() < 0.1:
            self.health -= 1
            
    def ai_decision(self, counter_system):
        # 根据威胁等级和距离决定行为
        distance_to_target = np.linalg.norm(self.position)
        
        if self.threat_level > 0.7 and distance_to_target < 300:
            # 高威胁，接近目标
            self.target = np.array([0, 0, 100])
        elif self.threat_level > 0.5:
            # 中等威胁，徘徊
            angle = time.time() * 0.5 + self.id
            radius = 200 + math.sin(time.time() * 0.3) * 50
            self.target = np.array([
                radius * math.cos(angle),
                radius * math.sin(angle),
                150
            ])
        else:
            # 低威胁，远离
            direction = self.position / distance_to_target
            self.target = direction * 500
        
        # 随机改变目标（增加不确定性）
        if random.random() < 0.02:
            self.target = self.target + np.array([random.uniform(-100, 100), 
                                            random.uniform(-100, 100), 
                                            random.uniform(-50, 50)])
    
    def avoid_collisions(self, other_drones):
        avoidance_force = np.array([0.0, 0.0, 0.0])
        
        for other in other_drones:
            if other.id != self.id:
                diff = self.position - other.position
                distance = np.linalg.norm(diff)
                
                if distance < 50 and distance > 0.1:
                    avoidance_force += (diff / distance) * (50 - distance) * 0.1
        
        self.acceleration += avoidance_force
    
    def update_threat_level(self, counter_system):
        base_threat = self.attributes["threat_base"]
        distance_factor = max(0, 1 - np.linalg.norm(self.position) / 1000)
        behavior_factor = self.aggressiveness
        
        # 干扰状态影响威胁等级
        if self.interfered:
            threat_reduction = 0.3
        else:
            threat_reduction = 0
            
        new_threat = (base_threat * 0.4 + distance_factor * 0.3 + 
                     behavior_factor * 0.3) - threat_reduction
        
        # 平滑变化
        self.threat_level += (new_threat - self.threat_level) * 0.1
        self.threat_level = np.clip(self.threat_level, 0.1, 0.95)


# 反制系统类 - 现在继承自QObject
class CounterDroneSystem(QObject):
    update_signal = pyqtSignal()
    
    def __init__(self):
        super().__init__()  # 初始化QObject
        self.drones = [SimulatedDrone(i) for i in range(12)]  # 增加无人机数量
        self.selected_drone = None
        self.system_active = True
        self.auto_mode = True
        self.jamming_mode = "智能干扰"
        self.interference_power = JAMMING_MODES[self.jamming_mode]["power"]
        self.detection_range = 600
        self.interference_range = JAMMING_MODES[self.jamming_mode]["range"]
        self.threat_threshold = 0.5
        self.alert_level = 0
        self.detection_history = deque(maxlen=100)
        self.spectrum_data = np.zeros(100)
        self.last_spectrum_update = time.time()
        self.system_log = deque(maxlen=50)
        self.resources = {"cpu": 0, "memory": 0, "network": 0, "power": 100}
        self.camera_view = "overview"
        self.zoom_level = 1.0
        self.rotation_angle = 0
        self.emergency_mode = False
        self.ai_analysis = {"pattern_detection": 0, "threat_prediction": 0}
        
        # 3D摄像头位置
        self.camera_pos = [0, -800, 300]
        self.camera_target = [0, 0, 0]
        
        # 启动系统更新线程
        self.update_thread = SystemUpdateThread(self)
        self.update_thread.start()
        
        # 启动资源监控线程
        self.monitor_thread = ResourceMonitorThread(self)
        self.monitor_thread.start()
        
        self.log_event("系统初始化完成", "INFO")
        
    def update(self):
        if not self.system_active:
            return
            
        # 更新所有无人机状态
        for drone in self.drones:
            drone.update(self)
            
        # 检测无人机
        self.detect_drones()
        
        # 自动反制逻辑
        if self.auto_mode:
            self.auto_counter_measure()
            
        # 更新频谱数据
        self.update_spectrum()
        
        # 更新检测历史
        self.detection_history.append(len([d for d in self.drones if d.detected]))
        
        # 更新AI分析
        self.update_ai_analysis()
        
        # 更新警报级别
        self.update_alert_level()
        
        # 发出更新信号
        self.update_signal.emit()
    
    def detect_drones(self):
        for drone in self.drones:
            distance = np.linalg.norm(drone.position)
            
            # 隐身模式降低检测概率
            stealth_factor = 0.3 if drone.stealth_mode else 1.0
            detect_prob = (0.8 * (1 - distance / self.detection_range) * 
                          drone.signal_strength * stealth_factor)
            
            # 随机检测结果
            was_detected = drone.detected
            drone.detected = (random.random() < detect_prob and 
                             distance < self.detection_range and
                             drone.health > 0)
            
            # 记录检测事件
            if drone.detected and not was_detected:
                self.log_event(f"检测到无人机 ID:{drone.id} 类型:{drone.type}", "DETECTION")
    
    def auto_counter_measure(self):
        threatened_drones = [d for d in self.drones 
                           if d.detected and d.threat_level > self.threat_threshold]
        
        # 按威胁等级排序
        threatened_drones.sort(key=lambda x: x.threat_level, reverse=True)
        
        # 根据干扰能力限制同时干扰的数量
        max_simultaneous = 3 if self.jamming_mode == "全频段干扰" else 5
        active_jamming = 0
        
        for drone in threatened_drones:
            if active_jamming >= max_simultaneous:
                drone.interfered = False
                continue
                
            distance = np.linalg.norm(drone.position)
            if distance < self.interference_range:
                if not drone.interfered:
                    self.log_event(f"开始干扰无人机 ID:{drone.id}", "JAMMING")
                drone.interfered = True
                drone.jamming_type = self.jamming_mode
                active_jamming += 1
            else:
                drone.interfered = False
                
        # 停止干扰低威胁无人机
        for drone in self.drones:
            if (drone.interfered and 
                (drone.threat_level <= self.threat_threshold or 
                 not drone.detected)):
                drone.interfered = False
                self.log_event(f"停止干扰无人机 ID:{drone.id}", "JAMMING")
    
    def manual_counter_measure(self, drone_id):
        if 0 <= drone_id < len(self.drones):
            drone = self.drones[drone_id]
            distance = np.linalg.norm(drone.position)
            if distance < self.interference_range:
                drone.interfered = True
                drone.jamming_type = self.jamming_mode
                self.log_event(f"手动干扰无人机 ID:{drone.id}", "JAMMING")
    
    def release_counter_measure(self, drone_id):
        if 0 <= drone_id < len(self.drones):
            drone = self.drones[drone_id]
            drone.interfered = False
            self.log_event(f"释放干扰无人机 ID:{drone.id}", "JAMMING")
    
    def set_jamming_mode(self, mode):
        if mode in JAMMING_MODES:
            self.jamming_mode = mode
            self.interference_power = JAMMING_MODES[mode]["power"]
            self.interference_range = JAMMING_MODES[mode]["range"]
            self.log_event(f"切换干扰模式: {mode}", "SYSTEM")
    
    def emergency_protocol(self):
        self.emergency_mode = True
        self.jamming_mode = "全频段干扰"
        self.interference_power = 100
        self.interference_range = 800
        
        # 干扰所有检测到的无人机
        for drone in self.drones:
            if drone.detected:
                drone.interfered = True
        
        self.log_event("紧急协议启动！全频段干扰激活", "CRITICAL")
        
        # 10秒后恢复正常
        Timer(10.0, self.reset_emergency).start()
    
    def reset_emergency(self):
        self.emergency_mode = False
        self.jamming_mode = "智能干扰"
        self.interference_power = JAMMING_MODES[self.jamming_mode]["power"]
        self.interference_range = JAMMING_MODES[self.jamming_mode]["range"]
        self.log_event("紧急协议结束，恢复正常模式", "SYSTEM")
    
    def update_spectrum(self):
        current_time = time.time()
        if current_time - self.last_spectrum_update > 0.1:
            self.last_spectrum_update = current_time
            
            new_data = np.zeros(100)
            for drone in self.drones:
                if drone.detected:
                    center = int(drone.id * 8 + 10)
                    width = 5 + int(drone.signal_strength * 10)
                    height = drone.signal_strength * 0.8
                    
                    for i in range(max(0, center-width), min(100, center+width)):
                        dist = abs(i - center)
                        if dist < width:
                            value = height * (1 - dist/width)
                            new_data[i] += value
            
            # 添加干扰信号
            if self.system_active and any(d.interfered for d in self.drones):
                jamming_center = 50
                jamming_width = 30
                jamming_height = 0.5 * (self.interference_power / 100)
                
                for i in range(max(0, jamming_center-jamming_width), 
                             min(100, jamming_center+jamming_width)):
                    dist = abs(i - jamming_center)
                    if dist < jamming_width:
                        value = jamming_height * (1 - dist/jamming_width)
                        new_data[i] += value
            
            noise = np.random.normal(0, 0.03, 100)
            self.spectrum_data = np.clip(new_data + noise, 0, 1)
    
    def update_ai_analysis(self):
        # 模拟AI分析结果
        detected_count = len([d for d in self.drones if d.detected])
        threat_ratio = len([d for d in self.drones if d.detected and d.threat_level > 0.7]) / max(1, detected_count)
        
        # 模式检测（基于无人机行为）
        pattern_score = 0
        for drone in self.drones:
            if drone.detected and len(drone.trajectory) > 10:
                # 分析轨迹规律性
                recent_positions = drone.trajectory[-10:]
                movements = [np.linalg.norm(recent_positions[i] - recent_positions[i-1]) 
                           for i in range(1, len(recent_positions))]
                if np.std(movements) < 2.0:  # 规律移动
                    pattern_score += 0.1
        
        self.ai_analysis["pattern_detection"] = min(1.0, pattern_score)
        self.ai_analysis["threat_prediction"] = threat_ratio
    
    def update_alert_level(self):
        threat_drones = [d for d in self.drones 
                        if d.detected and d.threat_level > self.threat_threshold]
        
        base_threat = len(threat_drones) * 0.15
        proximity_threat = sum(max(0, 1 - np.linalg.norm(d.position)/300) 
                              for d in threat_drones) * 0.2
        ai_threat = self.ai_analysis["threat_prediction"] * 0.3
        
        self.alert_level = min(1.0, base_threat + proximity_threat + ai_threat)
        
        if self.alert_level > 0.8 and not self.emergency_mode:
            self.emergency_protocol()
    
    def log_event(self, message, event_type):
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {event_type}: {message}"
        self.system_log.append(log_entry)


# 系统更新线程
class SystemUpdateThread(QThread):
    def __init__(self, system):
        super().__init__()
        self.system = system
        self.running = True
        
    def run(self):
        while self.running:
            if self.system.system_active:
                self.system.update()
            time.sleep(0.033)  # 约30fps
            
    def stop(self):
        self.running = False


# 资源监控线程
class ResourceMonitorThread(QThread):
    def __init__(self, system):
        super().__init__()
        self.system = system
        self.running = True
        
    def run(self):
        while self.running:
            # 模拟系统资源使用
            base_usage = 20 + len([d for d in self.system.drones if d.detected]) * 3
            jamming_usage = len([d for d in self.system.drones if d.interfered]) * 5
            
            self.system.resources["cpu"] = min(100, base_usage + jamming_usage + random.randint(-5, 5))
            self.system.resources["memory"] = min(100, 40 + random.randint(-10, 10))
            self.system.resources["network"] = min(100, 30 + random.randint(-5, 5))
            
            # 电源消耗
            power_drain = 0.5 + jamming_usage * 0.1
            self.system.resources["power"] = max(0, self.system.resources["power"] - power_drain)
            
            time.sleep(2)
            
    def stop(self):
        self.running = False


# 雷达显示组件
class RadarWidget(QWidget):
    def __init__(self, system):
        super().__init__()
        self.system = system
        self.setMinimumSize(400, 400)
        self.scan_angle = 0
        
        # 扫描动画定时器
        self.scan_timer = QTimer()
        self.scan_timer.timeout.connect(self.update_scan)
        self.scan_timer.start(50)  # 20fps
        
    def update_scan(self):
        self.scan_angle = (self.scan_angle + 2) % 360
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 绘制雷达背景
        center = QPoint(self.width() // 2, self.height() // 2)
        radius = min(self.width(), self.height()) // 2 - 20
        
        # 绘制雷达圆盘
        gradient = QLinearGradient(center.x() - radius, center.y() - radius, 
                                  center.x() + radius, center.y() + radius)
        gradient.setColorAt(0, QColor(10, 30, 50))
        gradient.setColorAt(1, QColor(20, 40, 70))
        painter.setBrush(QBrush(gradient))
        painter.setPen(QPen(QColor(40, 80, 120), 2))
        painter.drawEllipse(center, radius, radius)
        
        # 绘制同心圆和网格线
        painter.setPen(QPen(QColor(60, 100, 140), 1))
        for i in range(1, 4):
            r = radius * i // 4
            painter.drawEllipse(center, r, r)
            
        # 绘制坐标轴
        painter.drawLine(center.x() - radius, center.y(), center.x() + radius, center.y())
        painter.drawLine(center.x(), center.y() - radius, center.x(), center.y() + radius)
        
        # 绘制扫描线
        scan_rad = math.radians(self.scan_angle)
        end_x = center.x() + radius * math.cos(scan_rad)
        end_y = center.y() + radius * math.sin(scan_rad)
        
        painter.setPen(QPen(QColor(100, 255, 100, 150), 2))
        painter.drawLine(QPointF(center.x(), center.y()), QPointF(end_x, end_y))
        
        # 绘制扫描扇形
        painter.setBrush(QBrush(QColor(100, 255, 100, 30)))
        painter.setPen(QPen(QColor(100, 255, 100, 80), 1))
        painter.drawPie(int(center.x() - radius), int(center.y() - radius), 
                       int(radius * 2), int(radius * 2), 
                       (90 - self.scan_angle - 15) * 16, 30 * 16)
        
        # 绘制无人机
        scale = 0.8 * radius / self.system.detection_range
        for drone in self.system.drones:
            if drone.detected:
                # 将3D位置转换为2D雷达显示 (忽略高度)
                pos_x = center.x() + drone.position[0] * scale
                pos_y = center.y() + drone.position[1] * scale
                
                # 只显示在雷达范围内的无人机
                if math.sqrt((pos_x - center.x())**2 + (pos_y - center.y())**2) <= radius:
                    # 设置颜色基于威胁等级
                    if drone.threat_level > self.system.threat_threshold:
                        color = QColor(255, 100, 100)
                    else:
                        color = QColor(100, 255, 150)
                        
                    # 绘制无人机点
                    size = 6 + int(drone.threat_level * 10)
                    painter.setBrush(QBrush(color))
                    painter.setPen(QPen(QColor(255, 255, 255), 1))
                    painter.drawEllipse(QPoint(int(pos_x), int(pos_y)), size, size)
                    
                    # 如果被干扰，绘制干扰效果
                    if drone.interfered:
                        painter.setPen(QPen(QColor(255, 50, 50), 2))
                        painter.drawEllipse(QPoint(int(pos_x), int(pos_y)), size + 5, size + 5)
                        painter.setPen(QPen(QColor(255, 50, 50), 1))
                        painter.drawEllipse(QPoint(int(pos_x), int(pos_y)), size + 10, size + 10)
                        
                    # 绘制无人机ID
                    painter.setPen(QPen(QColor(255, 255, 255)))
                    painter.drawText(int(pos_x) + size + 5, int(pos_y) + 5, f"ID:{drone.id}")


# 频谱显示组件
class SpectrumWidget(QWidget):
    def __init__(self, system):
        super().__init__()
        self.system = system
        self.setMinimumHeight(150)
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 绘制背景
        painter.fillRect(self.rect(), QColor(25, 40, 60))
        painter.setPen(QPen(QColor(40, 70, 100), 1))
        painter.drawRect(self.rect().adjusted(0, 0, -1, -1))
        
        # 绘制网格线
        for i in range(1, 5):
            y = i * self.height() // 5
            painter.drawLine(0, y, self.width(), y)
            
        # 绘制频谱
        bar_width = self.width() / len(self.system.spectrum_data)
        for i, value in enumerate(self.system.spectrum_data):
            bar_height = value * self.height() * 0.9
            color_value = int(100 + value * 155)
            color = QColor(100, color_value, 255)
            
            painter.fillRect(int(i * bar_width), int(self.height() - bar_height), 
                           int(max(1, bar_width - 1)), int(bar_height), color)
            
        # 绘制标题
        painter.setPen(QPen(QColor(220, 220, 255)))
        painter.drawText(10, 20, "射频频谱监测")
        
        # 绘制频率标签
        for i in range(0, 11):
            freq = i * 2.4
            painter.drawText(i * self.width() // 10, self.height() - 5, f"{freq:.1f}GHz")


# 系统状态面板
class StatusPanel(QWidget):
    def __init__(self, system):
        super().__init__()
        self.system = system
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 系统状态组
        status_group = QGroupBox("系统状态")
        status_layout = QGridLayout()
        
        self.alert_label = QLabel("警戒级别: 0.00")
        self.detected_label = QLabel("检测到目标: 0/0")
        self.interfered_label = QLabel("反制中目标: 0")
        self.mode_label = QLabel("工作模式: 自动")
        self.power_label = QLabel("干扰功率: 0%")
        self.threshold_label = QLabel("威胁阈值: 0.50")
        
        status_layout.addWidget(self.alert_label, 0, 0)
        status_layout.addWidget(self.detected_label, 1, 0)
        status_layout.addWidget(self.interfered_label, 2, 0)
        status_layout.addWidget(self.mode_label, 3, 0)
        status_layout.addWidget(self.power_label, 4, 0)
        status_layout.addWidget(self.threshold_label, 5, 0)
        
        status_group.setLayout(status_layout)
        layout.addWidget(status_group)
        
        # 资源使用组
        resource_group = QGroupBox("资源使用")
        resource_layout = QVBoxLayout()
        
        self.cpu_bar = QProgressBar()
        self.cpu_bar.setFormat("CPU使用: %p%")
        self.memory_bar = QProgressBar()
        self.memory_bar.setFormat("内存使用: %p%")
        self.network_bar = QProgressBar()
        self.network_bar.setFormat("网络负载: %p%")
        self.power_bar = QProgressBar()
        self.power_bar.setFormat("电源剩余: %p%")
        
        resource_layout.addWidget(self.cpu_bar)
        resource_layout.addWidget(self.memory_bar)
        resource_layout.addWidget(self.network_bar)
        resource_layout.addWidget(self.power_bar)
        
        resource_group.setLayout(resource_layout)
        layout.addWidget(resource_group)
        
        # AI分析组
        ai_group = QGroupBox("AI分析")
        ai_layout = QVBoxLayout()
        
        self.pattern_label = QLabel("模式检测: 0%")
        self.threat_pred_label = QLabel("威胁预测: 0%")
        
        ai_layout.addWidget(self.pattern_label)
        ai_layout.addWidget(self.threat_pred_label)
        
        ai_group.setLayout(ai_layout)
        layout.addWidget(ai_group)
        
        self.setLayout(layout)
        
    def update_status(self):
        # 更新系统状态
        alert_color = "#64FF64" if self.system.alert_level < 0.5 else "#FF6464"
        self.alert_label.setText(f'警戒级别: <font color="{alert_color}">{self.system.alert_level:.2f}</font>')
        
        detected_count = len([d for d in self.system.drones if d.detected])
        self.detected_label.setText(f"检测到目标: {detected_count}/{len(self.system.drones)}")
        
        interfered_count = len([d for d in self.system.drones if d.interfered])
        self.interfered_label.setText(f"反制中目标: {interfered_count}")
        
        self.mode_label.setText(f"工作模式: {'自动' if self.system.auto_mode else '手动'}")
        self.power_label.setText(f"干扰功率: {self.system.interference_power}%")
        self.threshold_label.setText(f"威胁阈值: {self.system.threat_threshold:.2f}")
        
        # 更新资源使用
        self.cpu_bar.setValue(self.system.resources["cpu"])
        self.memory_bar.setValue(self.system.resources["memory"])
        self.network_bar.setValue(self.system.resources["network"])
        self.power_bar.setValue(int(self.system.resources["power"]))
        
        # 更新AI分析
        self.pattern_label.setText(f"模式检测: {self.system.ai_analysis['pattern_detection']*100:.0f}%")
        self.threat_pred_label.setText(f"威胁预测: {self.system.ai_analysis['threat_prediction']*100:.0f}%")


# 无人机详情面板
class DroneDetailsPanel(QWidget):
    def __init__(self, system):
        super().__init__()
        self.system = system
        self.current_drone = None
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        self.title_label = QLabel("无人机详情")
        self.title_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        layout.addWidget(self.title_label)
        
        # 无人机信息
        info_layout = QGridLayout()
        
        self.type_label = QLabel("类型: -")
        self.threat_label = QLabel("威胁等级: -")
        self.signal_label = QLabel("信号强度: -")
        self.distance_label = QLabel("距离: -")
        self.position_label = QLabel("位置: -")
        self.status_label = QLabel("状态: -")
        self.counter_label = QLabel("反制状态: -")
        self.battery_label = QLabel("电池电量: -")
        self.health_label = QLabel("健康度: -")
        self.packet_loss_label = QLabel("丢包率: -")
        self.data_rate_label = QLabel("数据速率: -")
        
        info_layout.addWidget(self.type_label, 0, 0)
        info_layout.addWidget(self.threat_label, 1, 0)
        info_layout.addWidget(self.signal_label, 2, 0)
        info_layout.addWidget(self.distance_label, 3, 0)
        info_layout.addWidget(self.position_label, 4, 0)
        info_layout.addWidget(self.status_label, 5, 0)
        info_layout.addWidget(self.counter_label, 6, 0)
        info_layout.addWidget(self.battery_label, 7, 0)
        info_layout.addWidget(self.health_label, 8, 0)
        info_layout.addWidget(self.packet_loss_label, 9, 0)
        info_layout.addWidget(self.data_rate_label, 10, 0)
        
        layout.addLayout(info_layout)
        
        # 威胁指示器
        self.threat_bar = QProgressBar()
        self.threat_bar.setTextVisible(False)
        layout.addWidget(QLabel("威胁等级:"))
        layout.addWidget(self.threat_bar)
        
        # 手动控制按钮
        control_layout = QHBoxLayout()
        self.jam_button = QPushButton("干扰此无人机")
        self.release_button = QPushButton("释放干扰")
        self.jam_button.clicked.connect(self.jam_drone)
        self.release_button.clicked.connect(self.release_drone)
        
        control_layout.addWidget(self.jam_button)
        control_layout.addWidget(self.release_button)
        layout.addLayout(control_layout)
        
        self.setLayout(layout)
        
    def set_drone(self, drone):
        self.current_drone = drone
        if drone:
            self.update_display()
            
    def update_display(self):
        if not self.current_drone:
            return
            
        drone = self.current_drone
        drone_type = DRONE_TYPES[drone.type]
        
        # 更新标题
        self.title_label.setText(f"{drone_type['icon']} 无人机详情 (ID: {drone.id})")
        
        # 更新信息
        self.type_label.setText(f"类型: {drone.type}")
        
        threat_color = "#FF6464" if drone.threat_level > self.system.threat_threshold else "#64FF64"
        self.threat_label.setText(f'威胁等级: <font color="{threat_color}">{drone.threat_level:.2f}</font>')
        
        self.signal_label.setText(f"信号强度: {drone.signal_strength:.2f}")
        
        distance = np.linalg.norm(drone.position)
        self.distance_label.setText(f"距离: {distance:.1f}米")
        
        self.position_label.setText(f"位置: ({drone.position[0]:.1f}, {drone.position[1]:.1f}, {drone.position[2]:.1f})")
        
        status_color = "#64FF64" if drone.detected else "#C8C8C8"
        status_text = "已检测" if drone.detected else "未检测"
        self.status_label.setText(f'状态: <font color="{status_color}">{status_text}</font>')
        
        counter_color = "#FF6464" if drone.interfered else "#C8C8C8"
        counter_text = "反制中" if drone.interfered else "未反制"
        self.counter_label.setText(f'反制状态: <font color="{counter_color}">{counter_text}</font>')
        
        battery_color = "#64FF64" if drone.battery > 30 else "#FF6464"
        self.battery_label.setText(f'电池电量: <font color="{battery_color}">{drone.battery:.1f}%</font>')
        
        health_color = "#64FF64" if drone.health > 70 else "#FFC864" if drone.health > 30 else "#FF6464"
        self.health_label.setText(f'健康度: <font color="{health_color}">{drone.health}%</font>')
        
        self.packet_loss_label.setText(f"丢包率: {drone.packet_loss*100:.1f}%")
        self.data_rate_label.setText(f"数据速率: {drone.data_rate:.1f} Mbps")
        
        # 更新威胁指示器
        self.threat_bar.setValue(int(drone.threat_level * 100))
        
        # 更新按钮状态
        self.jam_button.setEnabled(drone.detected and not drone.interfered)
        self.release_button.setEnabled(drone.interfered)
        
    def jam_drone(self):
        if self.current_drone:
            self.system.manual_counter_measure(self.current_drone.id)
            
    def release_drone(self):
        if self.current_drone:
            self.system.release_counter_measure(self.current_drone.id)


# 无人机列表表格
class DroneTableWidget(QTableWidget):
    def __init__(self, system):
        super().__init__()
        self.system = system
        self.init_ui()
        
    def init_ui(self):
        # 设置表格列
        self.setColumnCount(8)
        self.setHorizontalHeaderLabels(["ID", "类型", "距离", "威胁等级", "状态", "反制", "电池", "操作"])
        
        # 设置列宽
        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Stretch)
        
        # 设置行高
        self.verticalHeader().setDefaultSectionSize(30)
        
        # 不显示垂直表头
        self.verticalHeader().setVisible(False)
        
        # 设置选择行为
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        
    def update_table(self):
        detected_drones = [d for d in self.system.drones if d.detected]
        self.setRowCount(len(detected_drones))
        
        for row, drone in enumerate(detected_drones):
            drone_type = DRONE_TYPES[drone.type]
            distance = np.linalg.norm(drone.position)
            
            # ID
            self.setItem(row, 0, QTableWidgetItem(f"{drone.id}"))
            
            # 类型
            type_item = QTableWidgetItem(f"{drone_type['icon']} {drone.type}")
            type_item.setForeground(QColor(drone_type['color']))
            self.setItem(row, 1, type_item)
            
            # 距离
            self.setItem(row, 2, QTableWidgetItem(f"{distance:.1f}米"))
            
            # 威胁等级
            threat_item = QTableWidgetItem(f"{drone.threat_level:.2f}")
            if drone.threat_level > self.system.threat_threshold:
                threat_item.setForeground(QColor("#FF6464"))
            else:
                threat_item.setForeground(QColor("#64FF64"))
            self.setItem(row, 3, threat_item)
            
            # 状态
            status_item = QTableWidgetItem("已检测")
            status_item.setForeground(QColor("#64FF64"))
            self.setItem(row, 4, status_item)
            
            # 反制状态
            counter_item = QTableWidgetItem("反制中" if drone.interfered else "未反制")
            counter_item.setForeground(QColor("#FF6464" if drone.interfered else "#C8C8C8"))
            self.setItem(row, 5, counter_item)
            
            # 电池
            battery_item = QTableWidgetItem(f"{drone.battery:.1f}%")
            if drone.battery > 70:
                battery_item.setForeground(QColor("#64FF64"))
            elif drone.battery > 30:
                battery_item.setForeground(QColor("#FFC864"))
            else:
                battery_item.setForeground(QColor("#FF6464"))
            self.setItem(row, 6, battery_item)
            
            # 操作按钮
            if not self.system.auto_mode:
                if drone.interfered:
                    button = QPushButton("释放干扰")
                    button.clicked.connect(lambda checked, id=drone.id: self.system.release_counter_measure(id))
                else:
                    button = QPushButton("干扰")
                    button.clicked.connect(lambda checked, id=drone.id: self.system.manual_counter_measure(id))
                
                self.setCellWidget(row, 7, button)


# 检测历史图表
class HistoryChartWidget(QChartView):
    def __init__(self, system):
        self.system = system
        self.chart = QChart()
        self.chart.setTitle("目标检测历史")
        self.chart.setTheme(QChart.ChartTheme.ChartThemeDark)
        self.chart.legend().setVisible(False)
        
        self.series = QSplineSeries()
        self.series.setName("检测数量")
        self.series.setColor(QColor(100, 200, 255))
        
        self.chart.addSeries(self.series)
        
        # 设置坐标轴
        self.axis_x = QValueAxis()
        self.axis_x.setTitleText("时间")
        self.axis_x.setRange(0, 100)
        
        self.axis_y = QValueAxis()
        self.axis_y.setTitleText("数量")
        self.axis_y.setRange(0, len(self.system.drones) + 1)
        
        self.chart.addAxis(self.axis_x, Qt.AlignmentFlag.AlignBottom)
        self.chart.addAxis(self.axis_y, Qt.AlignmentFlag.AlignLeft)
        
        self.series.attachAxis(self.axis_x)
        self.series.attachAxis(self.axis_y)
        
        super().__init__(self.chart)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        
    def update_chart(self):
        self.series.clear()
        
        for i, value in enumerate(self.system.detection_history):
            self.series.append(i, value)
            
        if len(self.system.detection_history) > 0:
            self.axis_x.setRange(0, max(100, len(self.system.detection_history)))


# 系统日志面板
class LogPanel(QTextEdit):
    def __init__(self, system):
        super().__init__()
        self.system = system
        self.setReadOnly(True)
        self.setMaximumHeight(150)
        
        # 设置字体和颜色
        font = QFont("Consolas", 9)
        self.setFont(font)
        
    def update_log(self):
        self.clear()
        
        for log_entry in self.system.system_log:
            # 根据日志类型设置颜色
            if "CRITICAL" in log_entry:
                self.setTextColor(QColor("#FF6464"))
            elif "WARNING" in log_entry:
                self.setTextColor(QColor("#FFC864"))
            elif "DETECTION" in log_entry:
                self.setTextColor(QColor("#64C8FF"))
            elif "JAMMING" in log_entry:
                self.setTextColor(QColor("#64FF64"))
            else:
                self.setTextColor(QColor("#C8C8C8"))
                
            self.append(log_entry)


# 控制面板
class ControlPanel(QWidget):
    def __init__(self, system):
        super().__init__()
        self.system = system
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 系统控制组
        system_group = QGroupBox("系统控制")
        system_layout = QVBoxLayout()
        
        self.power_button = QPushButton("启动系统")
        self.power_button.setCheckable(True)
        self.power_button.setChecked(self.system.system_active)
        self.power_button.clicked.connect(self.toggle_system)
        
        self.auto_button = QPushButton("自动模式")
        self.auto_button.setCheckable(True)
        self.auto_button.setChecked(self.system.auto_mode)
        self.auto_button.clicked.connect(self.toggle_mode)
        
        self.emergency_button = QPushButton("紧急干扰")
        self.emergency_button.clicked.connect(self.system.emergency_protocol)
        self.emergency_button.setStyleSheet("QPushButton { background-color: #FF6464; color: white; }")
        
        system_layout.addWidget(self.power_button)
        system_layout.addWidget(self.auto_button)
        system_layout.addWidget(self.emergency_button)
        
        system_group.setLayout(system_layout)
        layout.addWidget(system_group)
        
        # 干扰模式组
        mode_group = QGroupBox("干扰模式")
        mode_layout = QVBoxLayout()
        
        self.mode_buttons = {}
        for mode, props in JAMMING_MODES.items():
            button = QPushButton(mode)
            button.setCheckable(True)
            button.setChecked(mode == self.system.jamming_mode)
            button.clicked.connect(lambda checked, m=mode: self.set_jamming_mode(m))
            mode_layout.addWidget(button)
            self.mode_buttons[mode] = button
            
        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)
        
        # 威胁阈值调节
        threshold_group = QGroupBox("威胁阈值")
        threshold_layout = QVBoxLayout()
        
        self.threshold_slider = QSlider(Qt.Orientation.Horizontal)
        self.threshold_slider.setRange(10, 90)
        self.threshold_slider.setValue(int(self.system.threat_threshold * 100))
        self.threshold_slider.valueChanged.connect(self.set_threshold)
        
        self.threshold_label = QLabel(f"{self.system.threat_threshold:.2f}")
        
        threshold_layout.addWidget(self.threshold_slider)
        threshold_layout.addWidget(self.threshold_label)
        
        threshold_group.setLayout(threshold_layout)
        layout.addWidget(threshold_group)
        
        # 检测范围调节
        range_group = QGroupBox("检测范围")
        range_layout = QVBoxLayout()
        
        self.range_slider = QSlider(Qt.Orientation.Horizontal)
        self.range_slider.setRange(300, 1000)
        self.range_slider.setValue(self.system.detection_range)
        self.range_slider.valueChanged.connect(self.set_detection_range)
        
        self.range_label = QLabel(f"{self.system.detection_range}米")
        
        range_layout.addWidget(self.range_slider)
        range_layout.addWidget(self.range_label)
        
        range_group.setLayout(range_layout)
        layout.addWidget(range_group)
        
        self.setLayout(layout)
        
    def toggle_system(self):
        self.system.system_active = not self.system.system_active
        self.power_button.setChecked(self.system.system_active)
        self.power_button.setText("关闭系统" if self.system.system_active else "启动系统")
        
    def toggle_mode(self):
        self.system.auto_mode = not self.system.auto_mode
        self.auto_button.setChecked(self.system.auto_mode)
        self.auto_button.setText("手动模式" if not self.system.auto_mode else "自动模式")
        
    def set_jamming_mode(self, mode):
        for m, button in self.mode_buttons.items():
            button.setChecked(m == mode)
        self.system.set_jamming_mode(mode)
        
    def set_threshold(self, value):
        self.system.threat_threshold = value / 100.0
        self.threshold_label.setText(f"{self.system.threat_threshold:.2f}")
        
    def set_detection_range(self, value):
        self.system.detection_range = value
        self.range_label.setText(f"{value}米")


# 主窗口
class DroneCountermeasureSystem(QMainWindow):
    def __init__(self):
        super().__init__()
        self.system = CounterDroneSystem()  # 现在CounterDroneSystem继承自QObject
        self.init_ui()
        
        # 连接系统更新信号
        self.system.update_signal.connect(self.update_ui)
        
    def init_ui(self):
        self.setWindowTitle("高级PX4无人机反制系统 v3.0 - PyQt6")
        self.setGeometry(100, 100, 1600, 900)
        
        # 设置应用样式
        self.setStyleSheet("""
            QMainWindow {
                background-color: #0a141e;
                color: #dcdcff;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #284670;
                border-radius: 5px;
                margin-top: 1ex;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #70a2ff;
            }
            QPushButton {
                background-color: #4682ff;
                color: white;
                border: none;
                padding: 5px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #5a96ff;
            }
            QPushButton:pressed {
                background-color: #3a6ad4;
            }
            QPushButton:checked {
                background-color: #ff6464;
            }
            QProgressBar {
                border: 1px solid #284670;
                border-radius: 3px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #4682ff;
                border-radius: 2px;
            }
            QTableWidget {
                background-color: #192840;
                alternate-background-color: #1e2e50;
                gridline-color: #284670;
                selection-background-color: #4682ff;
            }
            QHeaderView::section {
                background-color: #284670;
                color: white;
                padding: 5px;
                border: none;
            }
            QTextEdit {
                background-color: #192840;
                border: 1px solid #284670;
            }
        """)
        
        # 创建中央部件和主布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        
        # 左侧面板
        left_panel = QVBoxLayout()
        
        # 系统状态面板
        self.status_panel = StatusPanel(self.system)
        left_panel.addWidget(self.status_panel)
        
        # 控制面板
        self.control_panel = ControlPanel(self.system)
        left_panel.addWidget(self.control_panel)
        
        # 添加到主布局
        main_layout.addLayout(left_panel)
        
        # 中央区域 - 使用分割器
        center_splitter = QSplitter(Qt.Orientation.Vertical)
        
        # 雷达和频谱
        radar_spectrum_widget = QWidget()
        radar_spectrum_layout = QVBoxLayout(radar_spectrum_widget)
        
        self.radar_widget = RadarWidget(self.system)
        radar_spectrum_layout.addWidget(self.radar_widget)
        
        self.spectrum_widget = SpectrumWidget(self.system)
        radar_spectrum_layout.addWidget(self.spectrum_widget)
        
        center_splitter.addWidget(radar_spectrum_widget)
        
        # 历史图表
        self.history_chart = HistoryChartWidget(self.system)
        center_splitter.addWidget(self.history_chart)
        
        # 无人机列表和日志
        bottom_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 无人机详情
        self.drone_details = DroneDetailsPanel(self.system)
        bottom_splitter.addWidget(self.drone_details)
        
        # 日志面板
        self.log_panel = LogPanel(self.system)
        bottom_splitter.addWidget(self.log_panel)
        
        center_splitter.addWidget(bottom_splitter)
        
        # 设置分割器比例
        center_splitter.setSizes([400, 200, 200])
        bottom_splitter.setSizes([300, 200])
        
        main_layout.addWidget(center_splitter)
        
        # 右侧面板 - 无人机列表
        self.drone_table = DroneTableWidget(self.system)
        main_layout.addWidget(self.drone_table)
        
        # 设置主布局比例
        main_layout.setStretchFactor(left_panel, 1)
        main_layout.setStretchFactor(center_splitter, 3)
        main_layout.setStretchFactor(self.drone_table, 1)
        
    def update_ui(self):
        # 更新所有UI组件
        self.status_panel.update_status()
        self.radar_widget.update()
        self.spectrum_widget.update()
        self.history_chart.update_chart()
        self.drone_table.update_table()
        self.log_panel.update_log()
        
        # 更新无人机详情（如果已选择）
        if self.system.selected_drone is not None:
            drone = self.system.drones[self.system.selected_drone]
            self.drone_details.set_drone(drone)
        else:
            self.drone_details.set_drone(None)
            
    def closeEvent(self, event):
        # 停止所有线程
        self.system.update_thread.stop()
        self.system.monitor_thread.stop()
        
        # 等待线程结束
        self.system.update_thread.wait()
        self.system.monitor_thread.wait()
        
        event.accept()


# 启动应用
if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 设置应用程序字体
    font = QFont("Microsoft YaHei", 9)
    app.setFont(font)
    
    window = DroneCountermeasureSystem()
    window.show()
    
    sys.exit(app.exec())