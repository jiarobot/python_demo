import sys
import math
import numpy as np
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                             QWidget, QSlider, QLabel, QGroupBox, QPushButton,
                             QCheckBox, QSpinBox, QDoubleSpinBox, QComboBox,
                             QTabWidget, QSplitter, QTextEdit, QProgressBar,
                             QTableWidget, QTableWidgetItem, QHeaderView, QTreeWidget,
                             QTreeWidgetItem, QListWidget, QListWidgetItem, QToolBar,
                             QStatusBar, QAction, QFileDialog, QMessageBox, QDockWidget)
from PyQt5.QtCore import QTimer, Qt, QPointF, QRectF, QSize, QPropertyAnimation, pyqtProperty
from PyQt5.QtGui import (QPainter, QColor, QPen, QBrush, QFont, QRadialGradient,
                         QLinearGradient, QPalette, QIcon, QPixmap, QFontMetrics)
import matplotlib
matplotlib.rc("font", family='Microsoft YaHei')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import matplotlib.cm as cm
from scipy import integrate
from collections import deque
import random
import time
from skimage import measure

class AdvancedTeslaCoil:
    def __init__(self):
        # 基本参数
        self.primary_voltage = 10000  # V
        self.secondary_voltage = 500000  # V
        self.frequency = 250000  # Hz
        self.primary_capacitance = 0.1e-6  # F
        self.secondary_capacitance = 30e-12  # F
        self.primary_inductance = 100e-6  # H
        self.secondary_inductance = 0.1  # H
        self.coupling_coefficient = 0.2
        self.resistance_primary = 0.1  # Ω
        self.resistance_secondary = 100  # Ω
        
        # 高级参数
        self.q_factor_primary = 50
        self.q_factor_secondary = 200
        self.spark_gap_breakdown_voltage = 20000  # V
        self.atmospheric_pressure = 101325  # Pa
        self.humidity = 50  # %
        self.temperature = 20  # °C
        
        # 状态变量
        self.current_time = 0
        self.primary_current = 0
        self.secondary_current = 0
        self.primary_charge = 0
        self.secondary_charge = 0
        self.spark_active = False
        self.spark_length = 0
        self.power_input = 0
        self.efficiency = 0
        
        # 历史数据
        self.time_history = deque(maxlen=1000)
        self.voltage_history = deque(maxlen=1000)
        self.current_history = deque(maxlen=1000)
        self.power_history = deque(maxlen=1000)
        
    def calculate_resonant_frequency(self):
        """计算共振频率"""
        f_primary = 1 / (2 * math.pi * math.sqrt(self.primary_inductance * self.primary_capacitance))
        f_secondary = 1 / (2 * math.pi * math.sqrt(self.secondary_inductance * self.secondary_capacitance))
        return f_primary, f_secondary
    
    def calculate_impedance(self):
        """计算阻抗"""
        omega = 2 * math.pi * self.frequency
        z_primary = complex(self.resistance_primary, 
                           omega * self.primary_inductance - 1/(omega * self.primary_capacitance))
        z_secondary = complex(self.resistance_secondary, 
                             omega * self.secondary_inductance - 1/(omega * self.secondary_capacitance))
        return abs(z_primary), abs(z_secondary)
    
    def calculate_field_strength(self, x, y, z, tower_position):
        """计算三维场强分布"""
        dx = x - tower_position[0]
        dy = y - tower_position[1]
        dz = z - tower_position[2]
        distance = math.sqrt(dx**2 + dy**2 + dz**2)
        
        if distance < 0.1:
            return 0, 0, 0
            
        # 偶极子辐射场计算
        k = 2 * math.pi * self.frequency / 3e8  # 波数
        theta = math.acos(dz / distance) if distance > 0 else 0
        phi = math.atan2(dy, dx)
        
        # 近场和远场分量
        near_field = (self.secondary_current * self.secondary_inductance * 
                     math.sin(theta) / (4 * math.pi * distance**2))
        far_field = (k * self.secondary_current * self.secondary_inductance * 
                    math.sin(theta) / (4 * math.pi * distance))
        
        total_field = near_field + far_field
        
        # 转换为笛卡尔坐标
        ex = total_field * math.sin(theta) * math.cos(phi)
        ey = total_field * math.sin(theta) * math.sin(phi)
        ez = total_field * math.cos(theta)
        
        return ex, ey, ez
    
    def calculate_spark_breakdown(self):
        """计算火花击穿条件"""
        # Paschen定律简化版
        pressure_distance = self.atmospheric_pressure * self.spark_length
        breakdown_voltage = (self.spark_gap_breakdown_voltage * 
                           (1 + 0.01 * (pressure_distance - 760 * 0.01) / (760 * 0.01)))
        
        # 湿度修正
        humidity_factor = 1 + 0.1 * (self.humidity - 50) / 50
        
        return breakdown_voltage * humidity_factor
    
    def update(self, dt):
        """更新物理状态"""
        self.current_time += dt
        
        omega = 2 * math.pi * self.frequency
        
        # 计算电路状态
        v_primary = self.primary_voltage * math.sin(omega * self.current_time)
        
        # 微分方程求解（简化为稳态解）
        i_primary = (v_primary / self.calculate_impedance()[0] * 
                    math.sin(omega * self.current_time - math.pi/2))
        i_secondary = i_primary * self.coupling_coefficient * math.sqrt(
            self.secondary_inductance / self.primary_inductance)
        
        self.primary_current = i_primary
        self.secondary_current = i_secondary
        
        # 火花状态
        breakdown_voltage = self.calculate_spark_breakdown()
        self.spark_active = (self.secondary_current * 
                           self.calculate_impedance()[1] > breakdown_voltage)
        
        # 功率和效率
        self.power_input = abs(v_primary * i_primary)
        power_output = abs(self.secondary_current**2 * self.resistance_secondary)
        self.efficiency = power_output / self.power_input if self.power_input > 0 else 0
        
        # 记录历史
        self.time_history.append(self.current_time)
        self.voltage_history.append(v_primary)
        self.current_history.append(i_primary)
        self.power_history.append(self.power_input)

class MultiCoilSystem:
    def __init__(self):
        self.coils = []
        self.coupling_matrix = None
        
    def add_coil(self, position, parameters):
        """添加线圈到系统"""
        coil = {
            'position': position,
            'parameters': parameters,
            'current': 0,
            'voltage': 0,
            'phase': 0
        }
        self.coils.append(coil)
        self.update_coupling_matrix()
    
    def update_coupling_matrix(self):
        """更新耦合矩阵"""
        n = len(self.coils)
        self.coupling_matrix = np.zeros((n, n))
        
        for i in range(n):
            for j in range(i+1, n):
                pos1 = self.coils[i]['position']
                pos2 = self.coils[j]['position']
                distance = math.sqrt(sum((a - b)**2 for a, b in zip(pos1, pos2)))
                
                # 简化的距离相关耦合系数
                coupling = 0.3 / (1 + (distance / 5)**2)
                self.coupling_matrix[i, j] = coupling
                self.coupling_matrix[j, i] = coupling
    
    def calculate_system_field(self, x, y, z):
        """计算多线圈系统的总场强"""
        total_ex, total_ey, total_ez = 0, 0, 0
        
        for i, coil in enumerate(self.coils):
            ex, ey, ez = coil['parameters'].calculate_field_strength(
                x, y, z, coil['position'])
            
            # 考虑相位差
            phase_shift = coil['phase']
            ex *= math.cos(phase_shift)
            ey *= math.cos(phase_shift)
            ez *= math.cos(phase_shift)
            
            total_ex += ex
            total_ey += ey
            total_ez += ez
        
        return total_ex, total_ey, total_ez

class RealTimePlot(FigureCanvas):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi, facecolor='#2b2b2b')
        super().__init__(self.fig)
        self.setParent(parent)
        
        self.data_buffer = deque(maxlen=500)
        self.setup_plot()
    
    def setup_plot(self):
        self.ax = self.fig.add_subplot(111)
        self.ax.set_facecolor('#1e1e1e')
        
        # 设置颜色
        self.ax.tick_params(colors='white')
        self.ax.xaxis.label.set_color('white')
        self.ax.yaxis.label.set_color('white')
        self.ax.title.set_color('white')
        
        self.line, = self.ax.plot([], [], 'c-', linewidth=2, alpha=0.8)
        self.ax.grid(True, alpha=0.3, color='gray')
    
    def update_plot(self, new_data):
        self.data_buffer.append(new_data)
        x_data = range(len(self.data_buffer))
        
        self.line.set_data(x_data, self.data_buffer)
        self.ax.relim()
        self.ax.autoscale_view()
        self.draw()

class Field3DVisualization(FigureCanvas):
    def __init__(self, parent=None, width=6, height=5, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi, facecolor='#2b2b2b')
        super().__init__(self.fig)
        self.setParent(parent)
        
        self.simulation = None
        self.setup_plot()
    
    def setup_plot(self):
        self.ax = self.fig.add_subplot(111, projection='3d')
        self.ax.set_facecolor('#1e1e1e')
        
        # 设置颜色
        self.ax.tick_params(colors='white')
        self.ax.xaxis.label.set_color('white')
        self.ax.yaxis.label.set_color('white')
        self.ax.zaxis.label.set_color('white')
        self.ax.title.set_color('white')
    
    def update_visualization(self, simulation, multi_coil_system=None):
        self.ax.clear()
        
        # 生成3D网格
        x = np.linspace(-8, 8, 20)
        y = np.linspace(-8, 8, 20)
        z = np.linspace(0, 12, 15)
        X, Y, Z = np.meshgrid(x, y, z, indexing='ij')
        
        # 计算场强幅值
        E_magnitude = np.zeros_like(X)
        
        for i in range(len(x)):
            for j in range(len(y)):
                for k in range(len(z)):
                    if multi_coil_system:
                        ex, ey, ez = multi_coil_system.calculate_system_field(
                            X[i,j,k], Y[i,j,k], Z[i,j,k])
                    else:
                        ex, ey, ez = simulation.calculate_field_strength(
                            X[i,j,k], Y[i,j,k], Z[i,j,k], (0, 0, 6))
                    
                    E_magnitude[i,j,k] = math.sqrt(ex**2 + ey**2 + ez**2)
        
        try:
            # 绘制等值面
            threshold = np.percentile(E_magnitude, 70)
            verts, faces, _, _ = MarchingCubes(E_magnitude, threshold)
            
            # 检查是否有有效的等值面数据
            if len(verts) > 0 and len(faces) > 0:
                # 缩放和移动等值面以匹配坐标
                verts[:,0] = (verts[:,0] / len(x)) * 16 - 8
                verts[:,1] = (verts[:,1] / len(y)) * 16 - 8
                verts[:,2] = (verts[:,2] / len(z)) * 12
                
                self.ax.plot_trisurf(verts[:,0], verts[:,1], faces, verts[:,2],
                                alpha=0.6, cmap='plasma', linewidth=0.5)
            else:
                # 如果没有等值面数据，绘制简单的点云
                points = []
                colors = []
                for i in range(len(x)):
                    for j in range(len(y)):
                        for k in range(len(z)):
                            if E_magnitude[i,j,k] > threshold:
                                points.append([x[i], y[j], z[k]])
                                colors.append(E_magnitude[i,j,k])
                
                if points:
                    points = np.array(points)
                    colors = np.array(colors)
                    scatter = self.ax.scatter(points[:,0], points[:,1], points[:,2], 
                                            c=colors, cmap='plasma', alpha=0.6)
        
        except Exception as e:
            print(f"3D可视化错误: {e}")
            # 如果等值面提取失败，绘制简单的散点图
            points = []
            for i in range(0, len(x), 3):
                for j in range(0, len(y), 3):
                    for k in range(0, len(z), 3):
                        points.append([x[i], y[j], z[k]])
            
            if points:
                points = np.array(points)
                self.ax.scatter(points[:,0], points[:,1], points[:,2], 
                            c='blue', alpha=0.3, s=20)
        
        # 绘制线圈位置
        self.ax.scatter([0], [0], [6], c='red', s=100, marker='^', label='特斯拉塔')
        
        if multi_coil_system:
            for coil in multi_coil_system.coils:
                pos = coil['position']
                self.ax.scatter([pos[0]], [pos[1]], [pos[2]], c='blue', s=80, marker='o')
        
        self.ax.set_xlabel('X (m)')
        self.ax.set_ylabel('Y (m)')
        self.ax.set_zlabel('Z (m)')
        self.ax.set_title('3D电磁场分布')
        self.ax.legend()
        
        self.draw()

    # 简化的Marching Cubes实现（用于3D等值面）


def MarchingCubes(data, level):
    try:
        # 使用scikit-image的marching cubes算法
        verts, faces, normals, values = measure.marching_cubes(data, level)
        return verts, faces, normals, values
    except ImportError:
        # 回退到简化版本
        n_points = 100
        verts = np.random.rand(n_points, 3) * 10 - 5
        faces = np.array([[i, i+1, i+2] for i in range(0, n_points-2, 3)])
        normals = np.random.rand(n_points, 3)
        values = np.random.rand(n_points)
        return verts, faces, normals, values
    except Exception as e:
        print(f"MarchingCubes错误: {e}")
        return np.array([]).reshape(0, 3), np.array([]).reshape(0, 3), np.array([]).reshape(0, 3), np.array([])

class AdvancedTowerWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(400, 500)
        
        self.coils = []
        self.sparks = []
        self.field_lines = []
        self.animation_phase = 0
        
        # 初始化默认线圈
        self.add_default_coil()
    
    def add_default_coil(self):
        self.coils.append({
            'position': (0, 0, 6),
            'voltage': 500000,
            'current': 0.1,
            'frequency': 250000,
            'active': True
        })
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        width = self.width()
        height = self.height()
        
        # 绘制渐变背景
        self.draw_background(painter, width, height)
        
        # 绘制坐标网格
        self.draw_grid(painter, width, height)
        
        # 绘制所有线圈
        for coil in self.coils:
            if coil['active']:
                self.draw_tesla_coil(painter, width, height, coil)
        
        # 绘制场力线
        self.draw_field_lines(painter, width, height)
        
        # 绘制火花
        self.draw_sparks(painter, width, height)
        
        # 绘制信息面板
        self.draw_info_panel(painter, width, height)
    
    def draw_background(self, painter, width, height):
        # 创建渐变背景
        gradient = QLinearGradient(0, 0, 0, height)
        gradient.setColorAt(0, QColor(20, 25, 45))
        gradient.setColorAt(1, QColor(10, 15, 30))
        painter.fillRect(0, 0, width, height, QBrush(gradient))
    
    def draw_grid(self, painter, width, height):
        painter.setPen(QPen(QColor(60, 60, 80), 1))
        
        # 水平线
        for y in range(0, height, 20):
            painter.drawLine(0, y, width, y)
        
        # 垂直线
        for x in range(0, width, 20):
            painter.drawLine(x, 0, x, height)
    
    def draw_tesla_coil(self, painter, width, height, coil):
        center_x = width // 2 + coil['position'][0] * 10
        base_y = height - 100 + coil['position'][1] * 10
        tower_height = 120 + coil['position'][2] * 5
        
        # 塔基
        painter.setPen(QPen(QColor(180, 180, 180), 3))
        painter.setBrush(QBrush(QColor(120, 120, 120)))
        painter.drawRect(center_x - 30, base_y, 60, 15)
        
        # 塔身
        painter.setPen(QPen(QColor(220, 220, 220), 2))
        tower_width = 15
        height_steps = 8
        
        for i in range(height_steps):
            y = base_y - (i * tower_height // height_steps)
            width_factor = 1.0 - (i / height_steps) * 0.8
            current_width = tower_width * width_factor
            
            painter.drawLine(QPointF(center_x - current_width, y), 
                           QPointF(center_x + current_width, y))
            
            if i < height_steps - 1:
                next_y = base_y - ((i + 1) * tower_height // height_steps)
                painter.drawLine(QPointF(center_x - current_width, y), 
                               QPointF(center_x - tower_width * (1.0 - ((i + 1) / height_steps) * 0.8), next_y))
                painter.drawLine(QPointF(center_x + current_width, y), 
                               QPointF(center_x + tower_width * (1.0 - ((i + 1) / height_steps) * 0.8), next_y))
        
        # 顶部球体
        top_center = QPointF(center_x, base_y - tower_height)
        self.draw_torus(painter, top_center, 25, coil)
    
    def draw_torus(self, painter, center, radius, coil):
        # 绘制环形线圈
        voltage_factor = min(1.0, coil['voltage'] / 1000000)
        intensity = 100 + 155 * voltage_factor
        
        # 动态发光效果
        pulse = (math.sin(self.animation_phase * 2) + 1) / 2
        glow_intensity = intensity * (0.7 + 0.3 * pulse)
        
        # 绘制发光效果
        for r in range(radius + 10, radius, -2):
            alpha = 30 * (radius + 10 - r) // 10
            painter.setPen(QPen(QColor(255, 255, 200, alpha), 3))
            painter.drawEllipse(center, r, r)
        
        # 绘制主线圈
        painter.setPen(QPen(QColor(255, 255, 0), 3))
        painter.setBrush(QBrush(QColor(255, 255, 100, 100)))
        painter.drawEllipse(center, radius, radius)
        
        # 绘制电流方向指示器
        segments = 12
        for i in range(segments):
            angle = 2 * math.pi * i / segments + self.animation_phase
            dx = radius * math.cos(angle)
            dy = radius * math.sin(angle)
            
            arrow_x = center.x() + dx
            arrow_y = center.y() + dy
            
            painter.setPen(QPen(QColor(255, 100, 100), 2))
            painter.drawLine(center, QPointF(arrow_x, arrow_y))
    
    def draw_field_lines(self, painter, width, height):
        painter.setPen(QPen(QColor(100, 200, 255, 100), 1))
        
        lines = 24
        max_length = 150
        
        for i in range(lines):
            angle = 2 * math.pi * i / lines
            center_x = width // 2
            center_y = height - 250
            
            # 场力线路径
            path_points = []
            x, y = center_x, center_y
            segment_length = 5
            
            for segment in range(30):
                # 模拟场力线弯曲
                field_angle = angle + 0.3 * math.sin(segment * 0.3 + self.animation_phase)
                dx = segment_length * math.cos(field_angle)
                dy = segment_length * math.sin(field_angle)
                
                new_x = x + dx
                new_y = y + dy
                
                path_points.append((x, y, new_x, new_y))
                x, y = new_x, new_y
                
                # 距离衰减
                segment_length *= 0.95
            
            # 绘制场力线
            for start_x, start_y, end_x, end_y in path_points:
                painter.drawLine(QPointF(start_x, start_y), QPointF(end_x, end_y))
    
    def draw_sparks(self, painter, width, height):
        if len(self.sparks) == 0:
            # 生成随机火花
            for _ in range(8):
                angle = random.uniform(0, 2 * math.pi)
                length = random.uniform(30, 100)
                duration = random.uniform(0, 2 * math.pi)
                self.sparks.append({
                    'angle': angle,
                    'length': length,
                    'duration': duration,
                    'speed': random.uniform(0.05, 0.2)
                })
        
        center_x = width // 2
        center_y = height - 250
        
        for spark in self.sparks:
            spark['duration'] += spark['speed']
            phase = (math.sin(spark['duration']) + 1) / 2
            
            if phase > 0.3:
                current_length = spark['length'] * phase
                
                end_x = center_x + current_length * math.cos(spark['angle'])
                end_y = center_y + current_length * math.sin(spark['angle'])
                
                # 绘制锯齿状火花
                segments = int(current_length / 3)
                prev_x, prev_y = center_x, center_y
                
                painter.setPen(QPen(QColor(255, 255, 100), 2))
                
                for seg in range(segments):
                    seg_frac = seg / segments
                    next_frac = (seg + 1) / segments
                    
                    # 添加随机扰动
                    mid_x = center_x + current_length * (seg_frac + next_frac) / 2 * math.cos(spark['angle'])
                    mid_y = center_y + current_length * (seg_frac + next_frac) / 2 * math.sin(spark['angle'])
                    
                    mid_x += random.uniform(-3, 3)
                    mid_y += random.uniform(-3, 3)
                    
                    next_x = center_x + current_length * next_frac * math.cos(spark['angle'])
                    next_y = center_y + current_length * next_frac * math.sin(spark['angle'])
                    
                    painter.drawLine(QPointF(prev_x, prev_y), QPointF(mid_x, mid_y))
                    painter.drawLine(QPointF(mid_x, mid_y), QPointF(next_x, next_y))
                    
                    prev_x, prev_y = next_x, next_y
    
    def draw_info_panel(self, painter, width, height):
        # 绘制半透明信息面板
        painter.setBrush(QBrush(QColor(0, 0, 0, 180)))
        painter.setPen(QPen(QColor(255, 255, 255, 200)))
        painter.drawRect(10, 10, 200, 120)
        
        # 绘制信息文本
        painter.setFont(QFont("Arial", 9))
        info_lines = [
            "系统状态: 运行中",
            f"线圈数量: {len(self.coils)}",
            f"总电压: {sum(c['voltage'] for c in self.coils)/1000:.0f} kV",
            f"频率: {self.coils[0]['frequency']/1000:.0f} kHz",
            f"动画相位: {self.animation_phase:.2f}"
        ]
        
        for i, line in enumerate(info_lines):
            painter.drawText(20, 30 + i * 18, line)
    
    def update_animation(self):
        self.animation_phase += 0.1
        if self.animation_phase > 2 * math.pi:
            self.animation_phase = 0
        
        # 随机更新一些火花
        for spark in self.sparks:
            if random.random() < 0.1:
                spark['length'] = random.uniform(30, 100)
        
        self.update()

class AdvancedControlPanel(QWidget):
    def __init__(self, simulation, tower_widget, field_3d_viz):
        super().__init__()
        self.simulation = simulation
        self.tower_widget = tower_widget
        self.field_3d_viz = field_3d_viz
        
        self.multi_coil_system = MultiCoilSystem()
        
        self.init_ui()
        self.setup_connections()
    
    def init_ui(self):
        main_layout = QVBoxLayout()
        
        # 创建标签页
        tab_widget = QTabWidget()
        
        # 基本参数标签页
        basic_tab = self.create_basic_controls()
        tab_widget.addTab(basic_tab, "基本参数")
        
        # 高级参数标签页
        advanced_tab = self.create_advanced_controls()
        tab_widget.addTab(advanced_tab, "高级参数")
        
        # 多线圈控制标签页
        multi_coil_tab = self.create_multi_coil_controls()
        tab_widget.addTab(multi_coil_tab, "多线圈系统")
        
        # 环境参数标签页
        environment_tab = self.create_environment_controls()
        tab_widget.addTab(environment_tab, "环境参数")
        
        main_layout.addWidget(tab_widget)
        
        # 添加控制按钮
        button_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("启动仿真")
        self.start_btn.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; }")
        button_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("停止仿真")
        self.stop_btn.setStyleSheet("QPushButton { background-color: #f44336; color: white; }")
        button_layout.addWidget(self.stop_btn)
        
        self.reset_btn = QPushButton("重置系统")
        self.reset_btn.setStyleSheet("QPushButton { background-color: #FF9800; color: white; }")
        button_layout.addWidget(self.reset_btn)
        
        main_layout.addLayout(button_layout)
        
        # 添加状态显示
        status_group = QGroupBox("系统状态")
        status_layout = QVBoxLayout()
        
        self.efficiency_label = QLabel("效率: 0%")
        status_layout.addWidget(self.efficiency_label)
        
        self.power_label = QLabel("输入功率: 0 W")
        status_layout.addWidget(self.power_label)
        
        self.frequency_label = QLabel("共振频率: 0 Hz")
        status_layout.addWidget(self.frequency_label)
        
        self.status_label = QLabel("状态: 就绪")
        status_layout.addWidget(self.status_label)
        
        status_group.setLayout(status_layout)
        main_layout.addWidget(status_group)
        
        self.setLayout(main_layout)
    
    def create_basic_controls(self):
        widget = QWidget()
        layout = QVBoxLayout()
        
        # 电压控制
        voltage_group = QGroupBox("电压控制")
        voltage_layout = QVBoxLayout()
        
        self.create_slider_control(voltage_layout, "初级电压 (kV):", 
                                 0, 50, 10, self.update_primary_voltage)
        self.create_slider_control(voltage_layout, "次级电压 (kV):", 
                                 100, 2000, 500, self.update_secondary_voltage)
        
        voltage_group.setLayout(voltage_layout)
        layout.addWidget(voltage_group)
        
        # 频率控制
        frequency_group = QGroupBox("频率控制")
        frequency_layout = QVBoxLayout()
        
        self.create_slider_control(frequency_layout, "工作频率 (kHz):", 
                                 50, 2000, 250, self.update_frequency)
        self.create_slider_control(frequency_layout, "耦合系数:", 
                                 1, 100, 20, self.update_coupling)
        
        frequency_group.setLayout(frequency_layout)
        layout.addWidget(frequency_group)
        
        widget.setLayout(layout)
        return widget
    
    def create_advanced_controls(self):
        widget = QWidget()
        layout = QVBoxLayout()
        
        # 电路参数
        circuit_group = QGroupBox("电路参数")
        circuit_layout = QVBoxLayout()
        
        self.create_slider_control(circuit_layout, "初级电感 (μH):", 
                                 10, 500, 100, self.update_primary_inductance)
        self.create_slider_control(circuit_layout, "次级电感 (H):", 
                                 1, 500, 100, self.update_secondary_inductance)
        self.create_slider_control(circuit_layout, "初级电容 (nF):", 
                                 10, 1000, 100, self.update_primary_capacitance)
        self.create_slider_control(circuit_layout, "次级电容 (pF):", 
                                 10, 100, 30, self.update_secondary_capacitance)
        
        circuit_group.setLayout(circuit_layout)
        layout.addWidget(circuit_group)
        
        widget.setLayout(layout)
        return widget
    
    def create_multi_coil_controls(self):
        widget = QWidget()
        layout = QVBoxLayout()
        
        # 线圈列表
        coil_list_group = QGroupBox("线圈管理")
        coil_list_layout = QVBoxLayout()
        
        self.coil_list = QListWidget()
        coil_list_layout.addWidget(self.coil_list)
        
        # 线圈控制按钮
        coil_btn_layout = QHBoxLayout()
        
        add_coil_btn = QPushButton("添加线圈")
        add_coil_btn.clicked.connect(self.add_coil)
        coil_btn_layout.addWidget(add_coil_btn)
        
        remove_coil_btn = QPushButton("移除线圈")
        remove_coil_btn.clicked.connect(self.remove_coil)
        coil_btn_layout.addWidget(remove_coil_btn)
        
        coil_list_layout.addLayout(coil_btn_layout)
        coil_list_group.setLayout(coil_list_layout)
        layout.addWidget(coil_list_group)
        
        # 线圈位置控制
        position_group = QGroupBox("线圈位置")
        position_layout = QVBoxLayout()
        
        self.create_slider_control(position_layout, "X 位置:", -10, 10, 0, self.update_coil_position)
        self.create_slider_control(position_layout, "Y 位置:", -10, 10, 0, self.update_coil_position)
        self.create_slider_control(position_layout, "Z 位置:", 0, 12, 6, self.update_coil_position)
        
        position_group.setLayout(position_layout)
        layout.addWidget(position_group)
        
        widget.setLayout(layout)
        return widget
    
    def create_environment_controls(self):
        widget = QWidget()
        layout = QVBoxLayout()
        
        # 大气参数
        atmosphere_group = QGroupBox("大气参数")
        atmosphere_layout = QVBoxLayout()
        
        self.create_slider_control(atmosphere_layout, "大气压力 (kPa):", 
                                 80, 110, 101, self.update_pressure)
        self.create_slider_control(atmosphere_layout, "湿度 (%):", 
                                 0, 100, 50, self.update_humidity)
        self.create_slider_control(atmosphere_layout, "温度 (°C):", 
                                 -10, 40, 20, self.update_temperature)
        
        atmosphere_group.setLayout(atmosphere_layout)
        layout.addWidget(atmosphere_group)
        
        # 火花参数
        spark_group = QGroupBox("火花参数")
        spark_layout = QVBoxLayout()
        
        self.create_slider_control(spark_layout, "击穿电压 (kV):", 
                                 10, 100, 20, self.update_breakdown_voltage)
        
        spark_group.setLayout(spark_layout)
        layout.addWidget(spark_group)
        
        widget.setLayout(layout)
        return widget
    
    def create_slider_control(self, layout, label, min_val, max_val, default_val, callback):
        control_layout = QHBoxLayout()
        
        control_layout.addWidget(QLabel(label))
        
        slider = QSlider(Qt.Horizontal)
        slider.setRange(min_val, max_val)
        slider.setValue(default_val)
        slider.valueChanged.connect(callback)
        control_layout.addWidget(slider)
        
        value_label = QLabel(str(default_val))
        slider.valueChanged.connect(lambda v: value_label.setText(str(v)))
        control_layout.addWidget(value_label)
        
        layout.addLayout(control_layout)
        
        # 保存引用以便后续访问
        setattr(self, f"slider_{label.replace(' ', '_').replace('(', '').replace(')', '').replace(':', '')}", slider)
        setattr(self, f"label_{label.replace(' ', '_').replace('(', '').replace(')', '').replace(':', '')}", value_label)
    
    def setup_connections(self):
        self.start_btn.clicked.connect(self.start_simulation)
        self.stop_btn.clicked.connect(self.stop_simulation)
        self.reset_btn.clicked.connect(self.reset_simulation)
    
    def update_primary_voltage(self, value):
        self.simulation.primary_voltage = value * 1000
        self.update_status()
    
    def update_secondary_voltage(self, value):
        self.simulation.secondary_voltage = value * 1000
        self.update_status()
    
    def update_frequency(self, value):
        self.simulation.frequency = value * 1000
        self.update_status()
    
    def update_coupling(self, value):
        self.simulation.coupling_coefficient = value / 100
        self.update_status()
    
    def update_primary_inductance(self, value):
        self.simulation.primary_inductance = value * 1e-6
        self.update_status()
    
    def update_secondary_inductance(self, value):
        self.simulation.secondary_inductance = value * 1e-3
        self.update_status()
    
    def update_primary_capacitance(self, value):
        self.simulation.primary_capacitance = value * 1e-9
        self.update_status()
    
    def update_secondary_capacitance(self, value):
        self.simulation.secondary_capacitance = value * 1e-12
        self.update_status()
    
    def update_pressure(self, value):
        self.simulation.atmospheric_pressure = value * 1000
        self.update_status()
    
    def update_humidity(self, value):
        self.simulation.humidity = value
        self.update_status()
    
    def update_temperature(self, value):
        self.simulation.temperature = value
        self.update_status()
    
    def update_breakdown_voltage(self, value):
        self.simulation.spark_gap_breakdown_voltage = value * 1000
        self.update_status()
    
    def update_coil_position(self, value):
        # 更新选中线圈的位置
        pass
    
    def add_coil(self):
        new_coil = AdvancedTeslaCoil()
        position = (random.uniform(-5, 5), random.uniform(-5, 5), random.uniform(4, 8))
        self.multi_coil_system.add_coil(position, new_coil)
        
        # 更新3D可视化
        self.field_3d_viz.update_visualization(self.simulation, self.multi_coil_system)
        
        # 更新线圈列表
        item = QListWidgetItem(f"线圈 {len(self.multi_coil_system.coils)} - 位置: {position}")
        self.coil_list.addItem(item)
    
    def remove_coil(self):
        current_row = self.coil_list.currentRow()
        if current_row >= 0:
            self.coil_list.takeItem(current_row)
            if current_row < len(self.multi_coil_system.coils):
                self.multi_coil_system.coils.pop(current_row)
                self.multi_coil_system.update_coupling_matrix()
    
    def start_simulation(self):
        self.status_label.setText("状态: 运行中")
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
    
    def stop_simulation(self):
        self.status_label.setText("状态: 已停止")
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
    
    def reset_simulation(self):
        self.simulation = AdvancedTeslaCoil()
        self.multi_coil_system = MultiCoilSystem()
        self.status_label.setText("状态: 已重置")
        self.update_status()
    
    def update_status(self):
        f_primary, f_secondary = self.simulation.calculate_resonant_frequency()
        self.efficiency_label.setText(f"效率: {self.simulation.efficiency*100:.1f}%")
        self.power_label.setText(f"输入功率: {self.simulation.power_input:.0f} W")
        self.frequency_label.setText(f"共振频率: 初级={f_primary/1000:.1f} kHz, 次级={f_secondary/1000:.1f} kHz")

class DataAnalysisWidget(QWidget):
    def __init__(self, simulation):
        super().__init__()
        self.simulation = simulation
        
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 创建标签页
        tab_widget = QTabWidget()
        
        # 实时数据标签页
        realtime_tab = self.create_realtime_tab()
        tab_widget.addTab(realtime_tab, "实时数据")
        
        # 频谱分析标签页
        spectrum_tab = self.create_spectrum_tab()
        tab_widget.addTab(spectrum_tab, "频谱分析")
        
        # 效率分析标签页
        efficiency_tab = self.create_efficiency_tab()
        tab_widget.addTab(efficiency_tab, "效率分析")
        
        layout.addWidget(tab_widget)
        self.setLayout(layout)
    
    def create_realtime_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()
        
        # 电压电流图
        self.voltage_plot = RealTimePlot(self, width=6, height=3)
        self.voltage_plot.ax.set_title("电压波形")
        self.voltage_plot.ax.set_ylabel("电压 (V)")
        
        # 功率图
        self.power_plot = RealTimePlot(self, width=6, height=3)
        self.power_plot.ax.set_title("功率变化")
        self.power_plot.ax.set_ylabel("功率 (W)")
        
        layout.addWidget(self.voltage_plot)
        layout.addWidget(self.power_plot)
        
        widget.setLayout(layout)
        return widget
    
    def create_spectrum_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()
        
        self.spectrum_plot = RealTimePlot(self, width=6, height=4)
        self.spectrum_plot.ax.set_title("频率频谱")
        self.spectrum_plot.ax.set_xlabel("频率 (Hz)")
        self.spectrum_plot.ax.set_ylabel("幅度")
        
        layout.addWidget(self.spectrum_plot)
        
        # 频谱分析控制
        spectrum_controls = QHBoxLayout()
        spectrum_controls.addWidget(QLabel("FFT 点数:"))
        fft_points = QSpinBox()
        fft_points.setRange(64, 2048)
        fft_points.setValue(256)
        spectrum_controls.addWidget(fft_points)
        spectrum_controls.addStretch()
        
        layout.addLayout(spectrum_controls)
        
        widget.setLayout(layout)
        return widget
    
    def create_efficiency_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()
        
        self.efficiency_plot = RealTimePlot(self, width=6, height=4)
        self.efficiency_plot.ax.set_title("效率趋势")
        self.efficiency_plot.ax.set_ylabel("效率 (%)")
        
        layout.addWidget(self.efficiency_plot)
        
        # 效率统计
        stats_layout = QHBoxLayout()
        
        self.max_efficiency_label = QLabel("最大效率: 0%")
        stats_layout.addWidget(self.max_efficiency_label)
        
        self.avg_efficiency_label = QLabel("平均效率: 0%")
        stats_layout.addWidget(self.avg_efficiency_label)
        
        self.min_efficiency_label = QLabel("最小效率: 0%")
        stats_layout.addWidget(self.min_efficiency_label)
        
        layout.addLayout(stats_layout)
        
        widget.setLayout(layout)
        return widget
    
    def update_plots(self):
        # 更新实时数据图
        if len(self.simulation.voltage_history) > 0:
            self.voltage_plot.update_plot(self.simulation.voltage_history[-1])
            self.power_plot.update_plot(self.simulation.power_history[-1])
            self.efficiency_plot.update_plot(self.simulation.efficiency * 100)

class AdvancedTeslaSimulator(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.simulation = AdvancedTeslaCoil()
        self.simulation_timer = QTimer()
        self.simulation_timer.timeout.connect(self.update_simulation)
        
        self.init_ui()
        self.setup_menu()
        self.setup_statusbar()
        
        # 启动仿真计时器
        self.simulation_timer.start(50)  # 20 Hz update rate
    
    def init_ui(self):
        self.setWindowTitle("高级特斯拉线圈仿真系统")
        self.setGeometry(100, 100, 1600, 900)
        
        # 设置应用样式
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2b2b2b;
                color: white;
            }
            QTabWidget::pane {
                border: 1px solid #555;
                background-color: #353535;
            }
            QTabBar::tab {
                background-color: #404040;
                color: white;
                padding: 8px 16px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: #505050;
            }
            QGroupBox {
                color: #88ccff;
                font-weight: bold;
                border: 1px solid #555;
                margin-top: 1ex;
                padding-top: 1ex;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout()
        central_widget.setLayout(main_layout)
        
        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        
        # 左侧：可视化区域
        left_widget = QWidget()
        left_layout = QVBoxLayout()
        left_widget.setLayout(left_layout)
        
        # 3D塔可视化
        self.tower_widget = AdvancedTowerWidget()
        left_layout.addWidget(self.tower_widget)
        
        # 3D场可视化
        self.field_3d_viz = Field3DVisualization()
        left_layout.addWidget(self.field_3d_viz)
        
        splitter.addWidget(left_widget)
        
        # 右侧：控制和分析区域
        right_splitter = QSplitter(Qt.Vertical)
        
        # 控制面板
        self.control_panel = AdvancedControlPanel(
            self.simulation, self.tower_widget, self.field_3d_viz)
        right_splitter.addWidget(self.control_panel)
        
        # 数据分析
        self.data_analysis = DataAnalysisWidget(self.simulation)
        right_splitter.addWidget(self.data_analysis)
        
        splitter.addWidget(right_splitter)
        
        # 设置分割器比例
        splitter.setSizes([800, 400])
        right_splitter.setSizes([400, 300])
        
        main_layout.addWidget(splitter)
        
        # 创建停靠窗口
        self.create_dock_windows()
    
    def create_dock_windows(self):
        # 系统信息停靠窗口
        info_dock = QDockWidget("系统信息", self)
        info_widget = QTextEdit()
        info_widget.setReadOnly(True)
        info_widget.setHtml("""
            <h3>特斯拉线圈仿真系统</h3>
            <p>这是一个高级特斯拉线圈仿真系统，包含：</p>
            <ul>
                <li>多线圈系统仿真</li>
                <li>3D电磁场可视化</li>
                <li>实时数据分析</li>
                <li>高级物理模型</li>
                <li>效率优化工具</li>
            </ul>
            <p><b>系统状态:</b> 运行正常</p>
        """)
        info_dock.setWidget(info_widget)
        self.addDockWidget(Qt.RightDockWidgetArea, info_dock)
    
    def setup_menu(self):
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
        
        exit_action = QAction('退出', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 仿真菜单
        sim_menu = menubar.addMenu('仿真')
        
        start_action = QAction('开始仿真', self)
        start_action.setShortcut('F5')
        sim_menu.addAction(start_action)
        
        stop_action = QAction('停止仿真', self)
        stop_action.setShortcut('F6')
        sim_menu.addAction(stop_action)
        
        reset_action = QAction('重置仿真', self)
        reset_action.setShortcut('F7')
        sim_menu.addAction(reset_action)
        
        # 视图菜单
        view_menu = menubar.addMenu('视图')
        
        toggle_3d_action = QAction('切换3D视图', self)
        view_menu.addAction(toggle_3d_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu('帮助')
        
        about_action = QAction('关于', self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def setup_statusbar(self):
        statusbar = self.statusBar()
        
        self.status_label = QLabel("就绪")
        statusbar.addWidget(self.status_label)
        
        self.simulation_time_label = QLabel("仿真时间: 0.0s")
        statusbar.addPermanentWidget(self.simulation_time_label)
        
        self.efficiency_label = QLabel("效率: 0.0%")
        statusbar.addPermanentWidget(self.efficiency_label)
    
    def update_simulation(self):
        # 更新物理仿真
        self.simulation.update(0.05)
        
        # 更新可视化
        self.tower_widget.update_animation()
        self.field_3d_viz.update_visualization(self.simulation)
        
        # 更新数据分析
        self.data_analysis.update_plots()
        
        # 更新状态栏
        self.simulation_time_label.setText(f"仿真时间: {self.simulation.current_time:.1f}s")
        self.efficiency_label.setText(f"效率: {self.simulation.efficiency*100:.1f}%")
        
        # 更新控制面板状态
        self.control_panel.update_status()
    
    def show_about(self):
        QMessageBox.about(self, "关于特斯拉线圈仿真系统",
                         "高级特斯拉线圈仿真系统 v2.0\n\n"
                         "这是一个功能完整的特斯拉线圈仿真平台，"
                         "包含多线圈系统、3D场可视化、实时数据分析和优化工具。\n\n"
                         "基于PyQt5和科学计算库开发。")

def main():
    app = QApplication(sys.argv)
    
    # 设置应用程序样式
    app.setStyle('Fusion')
    
    # 创建调色板
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(43, 43, 43))
    palette.setColor(QPalette.WindowText, Qt.white)
    palette.setColor(QPalette.Base, QColor(25, 25, 25))
    palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
    palette.setColor(QPalette.ToolTipBase, Qt.white)
    palette.setColor(QPalette.ToolTipText, Qt.white)
    palette.setColor(QPalette.Text, Qt.white)
    palette.setColor(QPalette.Button, QColor(53, 53, 53))
    palette.setColor(QPalette.ButtonText, Qt.white)
    palette.setColor(QPalette.BrightText, Qt.red)
    palette.setColor(QPalette.Link, QColor(42, 130, 218))
    palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.HighlightedText, Qt.black)
    app.setPalette(palette)
    
    simulator = AdvancedTeslaSimulator()
    simulator.show()
    
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()