import sys
import random
import numpy as np
import json
import time
import math
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QPushButton, QTabWidget, 
                             QGraphicsView, QGraphicsScene, QFrame, QGroupBox,
                             QSlider, QSpinBox, QDoubleSpinBox, QCheckBox,
                             QFileDialog, QMessageBox, QDockWidget, QFormLayout,
                             QComboBox, QSplitter, QProgressBar, QTextEdit,
                             QMenu, QAction, QStatusBar, QToolBar, QDialog,
                             QInputDialog, QListWidget, QListWidgetItem)
from PyQt5.QtCore import Qt, QTimer, QPointF, QRectF, QSize, QPropertyAnimation, QEasingCurve, pyqtSignal
from PyQt5.QtGui import (QPainter, QBrush, QPen, QColor, QFont, QPainterPath, 
                        QPalette, QLinearGradient, QRadialGradient, QIcon,
                        QKeySequence, QFontDatabase)
import pyqtgraph as pg
import pyqtgraph.opengl as gl
from pyqtgraph import PlotWidget, PlotItem, InfiniteLine, FillBetweenItem
import scipy.signal as signal
from scipy.fft import fft, fftfreq
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import pandas as pd

# 导入新模块
import os
import threading
from queue import Queue
import webbrowser

class AdvancedParticleBackground(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.particles = []
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_particles)
        self.timer.start(25)  # 更高帧率
        
        # 高级粒子参数
        self.particle_count = 300
        self.connection_distance = 180
        self.particle_speed_min = 0.3
        self.particle_speed_max = 3.0
        self.gravity_centers = []
        self.field_strength = 0.01
        self.particle_interaction = True
        self.color_scheme = "quantum"  # quantum, plasma, cosmic, neural
        
        # 音效可视化参数
        self.audio_input = False
        self.audio_data = np.zeros(100)
        self.audio_influence = 0.5
        
        self.init_particles()
        self.init_gravity_centers()
        
        # 性能优化
        self.last_update_time = time.time()
        self.frame_count = 0
        self.fps = 0
    
    def init_particles(self):
        self.particles = []
        for _ in range(self.particle_count):
            self.particles.append({
                'x': random.randint(0, self.width()),
                'y': random.randint(0, self.height()),
                'radius': random.uniform(1.5, 4),
                'speed': random.uniform(self.particle_speed_min, self.particle_speed_max),
                'angle': random.uniform(0, 2 * np.pi),
                'mass': random.uniform(0.5, 2.0),
                'charge': random.uniform(-1, 1),
                'color': self.generate_particle_color(),
                'osc_phase': random.uniform(0, 2 * np.pi),
                'osc_freq': random.uniform(0.02, 0.08),
                'lifetime': random.uniform(500, 2000),
                'age': 0
            })
    
    def init_gravity_centers(self):
        self.gravity_centers = [
            {'x': self.width()/3, 'y': self.height()/3, 'strength': 0.02},
            {'x': 2*self.width()/3, 'y': 2*self.height()/3, 'strength': 0.015},
            {'x': self.width()/2, 'y': self.height()/4, 'strength': -0.01}  # 排斥中心
        ]
    
    def generate_particle_color(self):
        if self.color_scheme == "quantum":
            return QColor(
                random.randint(100, 200),
                random.randint(150, 255),
                random.randint(200, 255),
                random.randint(80, 180)
            )
        elif self.color_scheme == "plasma":
            return QColor(
                random.randint(200, 255),
                random.randint(100, 200),
                random.randint(50, 150),
                random.randint(80, 180)
            )
        elif self.color_scheme == "cosmic":
            return QColor(
                random.randint(50, 150),
                random.randint(50, 150),
                random.randint(150, 255),
                random.randint(80, 180)
            )
        else:  # neural
            return QColor(
                random.randint(150, 255),
                random.randint(100, 200),
                random.randint(200, 255),
                random.randint(80, 180)
            )
    
    def set_color_scheme(self, scheme):
        self.color_scheme = scheme
        for p in self.particles:
            p['color'] = self.generate_particle_color()
    
    def set_audio_influence(self, influence):
        self.audio_influence = influence
    
    def update_audio_data(self, data):
        if len(data) > 0:
            self.audio_data = data
    
    def update_particles(self):
        current_time = time.time()
        self.frame_count += 1
        
        if current_time - self.last_update_time >= 1.0:
            self.fps = self.frame_count
            self.frame_count = 0
            self.last_update_time = current_time
        
        for p in self.particles:
            # 年龄和生命周期
            p['age'] += 1
            if p['age'] > p['lifetime']:
                # 重置粒子
                p.update({
                    'x': random.randint(0, self.width()),
                    'y': random.randint(0, self.height()),
                    'age': 0,
                    'lifetime': random.uniform(500, 2000)
                })
            
            # 重力场影响
            for center in self.gravity_centers:
                dx = center['x'] - p['x']
                dy = center['y'] - p['y']
                dist = max(np.sqrt(dx*dx + dy*dy), 1)
                force = center['strength'] * p['mass'] / (dist * dist)
                
                p['angle'] = np.arctan2(
                    np.sin(p['angle']) + dy/dist * force,
                    np.cos(p['angle']) + dx/dist * force
                )
            
            # 粒子间相互作用
            if self.particle_interaction:
                for p2 in self.particles:
                    if p2 is not p:
                        dx = p2['x'] - p['x']
                        dy = p2['y'] - p['y']
                        dist = max(np.sqrt(dx*dx + dy*dy), 5)
                        
                        if dist < 50:  # 近距离相互作用
                            force = 0.001 * p['charge'] * p2['charge'] / (dist * dist)
                            p['angle'] = np.arctan2(
                                np.sin(p['angle']) + dy/dist * force,
                                np.cos(p['angle']) + dx/dist * force
                            )
            
            # 音频影响
            if self.audio_input and len(self.audio_data) > 0:
                audio_index = min(int(p['x'] / self.width() * len(self.audio_data)), len(self.audio_data)-1)
                audio_effect = self.audio_data[audio_index] * self.audio_influence * 0.1
                p['angle'] += audio_effect
            
            # 振荡运动
            osc = np.sin(p['osc_phase']) * 0.8
            p['osc_phase'] += p['osc_freq']
            
            # 更新位置
            p['x'] += np.cos(p['angle']) * p['speed'] + osc
            p['y'] += np.sin(p['angle']) * p['speed'] + osc
            
            # 边界处理（弹性边界）
            if p['x'] < -50:
                p['x'] = self.width() + 50
            if p['x'] > self.width() + 50:
                p['x'] = -50
            if p['y'] < -50:
                p['y'] = self.height() + 50
            if p['y'] > self.height() + 50:
                p['y'] = -50
                
        self.update()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 绘制渐变背景
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0, QColor(10, 8, 31, 200))
        gradient.setColorAt(1, QColor(5, 3, 20, 200))
        painter.fillRect(self.rect(), gradient)
        
        # 绘制连接线（优化性能）
        connection_count = 0
        for i, p1 in enumerate(self.particles):
            for j, p2 in enumerate(self.particles[i+1:]):
                dx = p1['x'] - p2['x']
                dy = p1['y'] - p2['y']
                dist_sq = dx*dx + dy*dy
                
                if dist_sq < self.connection_distance**2:
                    dist = np.sqrt(dist_sq)
                    alpha = int(255 * (1 - dist/self.connection_distance))
                    
                    # 根据电荷设置连接线颜色
                    if p1['charge'] * p2['charge'] > 0:
                        color = QColor(255, 100, 100, alpha)  # 排斥 - 红色
                    else:
                        color = QColor(100, 100, 255, alpha)  # 吸引 - 蓝色
                    
                    painter.setPen(QPen(color, 1.5))
                    painter.drawLine(int(p1['x']), int(p1['y']), int(p2['x']), int(p2['y']))
                    connection_count += 1
        
        # 绘制粒子
        for p in self.particles:
            # 根据年龄调整透明度
            age_ratio = p['age'] / p['lifetime']
            alpha = int(255 * (1 - age_ratio * 0.5))
            color = p['color']
            color.setAlpha(alpha)
            
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(color))
            
            # 绘制光晕效果
            radius = p['radius'] * (1 + 0.3 * np.sin(p['osc_phase']))
            painter.drawEllipse(int(p['x'] - radius), int(p['y'] - radius), 
                              int(radius * 2), int(radius * 2))
        
        # 绘制FPS信息
        painter.setPen(QColor(200, 200, 255, 150))
        painter.drawText(10, 20, f"FPS: {self.fps} | Particles: {len(self.particles)} | Connections: {connection_count}")

    def resizeEvent(self, event):
        """当部件大小改变时重新初始化粒子和重力中心"""
        super().resizeEvent(event)
        self.init_particles()
        self.init_gravity_centers()

class QuantumFieldVisualization(gl.GLViewWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setBackgroundColor('k')
        
        # 量子场参数
        self.field_resolution = 50
        self.time = 0
        self.field_strength = 1.0
        self.wave_frequency = 1.0
        self.interference_enabled = True
        self.particle_count = 100
        
        # 创建量子场网格
        self.create_quantum_field()
        
        # 创建粒子系统
        self.quantum_particles = []
        self.create_quantum_particles()
        
        # 设置相机
        self.setCameraPosition(distance=8, elevation=30, azimuth=0)
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_field)
        self.timer.start(40)
    
    def create_quantum_field(self):
        # 创建场网格
        x = np.linspace(-5, 5, self.field_resolution)
        y = np.linspace(-5, 5, self.field_resolution)
        self.X, self.Y = np.meshgrid(x, y)
        self.Z = np.zeros_like(self.X)
        
        # 创建网格项
        self.field_mesh = gl.GLSurfacePlotItem(x=x, y=y, z=self.Z, 
                                             colors=self.calculate_field_colors(self.Z),
                                             shader='shaded')
        self.addItem(self.field_mesh)
    
    def create_quantum_particles(self):
        for _ in range(self.particle_count):
            particle = {
                'pos': np.array([random.uniform(-4, 4), 
                               random.uniform(-4, 4), 
                               random.uniform(-1, 1)]),
                'velocity': np.array([random.uniform(-0.1, 0.1),
                                    random.uniform(-0.1, 0.1),
                                    random.uniform(-0.05, 0.05)]),
                'phase': random.uniform(0, 2*np.pi),
                'size': random.uniform(0.1, 0.3),
                'color': (random.uniform(0.5, 1), 
                         random.uniform(0.5, 1), 
                         random.uniform(0.5, 1), 1)
            }
            self.quantum_particles.append(particle)
    
    def calculate_field_colors(self, Z):
        # 根据场强计算颜色
        colors = np.zeros((Z.shape[0], Z.shape[1], 4))
        
        for i in range(Z.shape[0]):
            for j in range(Z.shape[1]):
                z_val = Z[i, j]
                intensity = min(1.0, abs(z_val) * 2)
                
                if z_val > 0:
                    # 正场 - 蓝色调
                    colors[i, j] = (0.2, 0.4, 1.0, intensity)
                else:
                    # 负场 - 红色调
                    colors[i, j] = (1.0, 0.4, 0.2, intensity)
        
        return colors
    
    def update_field(self):
        self.time += 0.1
        
        # 更新量子场
        k = self.wave_frequency
        field_strength = self.field_strength
        
        # 基本波函数
        wave1 = field_strength * np.sin(k * self.X + self.time)
        wave2 = field_strength * np.cos(k * self.Y - self.time * 0.7)
        
        if self.interference_enabled:
            # 干涉模式
            wave3 = 0.5 * field_strength * np.sin(k * (self.X + self.Y) * 0.5 + self.time * 1.2)
            self.Z = wave1 + wave2 + wave3
        else:
            self.Z = wave1 + wave2
        
        # 添加量子涨落
        quantum_fluctuation = 0.1 * np.random.normal(0, 0.3, self.Z.shape)
        self.Z += quantum_fluctuation
        
        # 更新网格
        self.field_mesh.setData(z=self.Z, colors=self.calculate_field_colors(self.Z))
        
        # 更新粒子
        self.update_particles()
    
    def update_particles(self):
        # 简单的粒子运动（受场影响）
        for particle in self.quantum_particles:
            # 场对粒子的影响
            x_idx = int((particle['pos'][0] + 5) / 10 * (self.field_resolution - 1))
            y_idx = int((particle['pos'][1] + 5) / 10 * (self.field_resolution - 1))
            
            x_idx = max(0, min(self.field_resolution-1, x_idx))
            y_idx = max(0, min(self.field_resolution-1, y_idx))
            
            field_value = self.Z[y_idx, x_idx]
            
            # 场梯度影响速度
            particle['velocity'][2] += field_value * 0.01
            
            # 更新位置
            particle['pos'] += particle['velocity']
            
            # 边界处理
            for i in range(3):
                if abs(particle['pos'][i]) > 5:
                    particle['velocity'][i] *= -0.5
                    particle['pos'][i] = np.clip(particle['pos'][i], -4.5, 4.5)
    
    def update_parameters(self, field_strength, wave_freq, interference):
        self.field_strength = field_strength
        self.wave_frequency = wave_freq
        self.interference_enabled = interference

class NeuralNetworkVisualization(PlotWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setBackground('transparent')
        
        # 神经网络参数
        self.layer_sizes = [10, 8, 6, 4]  # 各层神经元数量
        self.activation_levels = [0.5] * len(self.layer_sizes)
        self.learning_rate = 0.1
        self.connection_strength = 0.7
        
        # 创建网络可视化
        self.create_network()
        
        # 动画参数
        self.animation_time = 0
        self.patterns = self.generate_patterns()
        self.current_pattern = 0
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_network)
        self.timer.start(100)
    
    def create_network(self):
        self.clear()
        
        # 创建神经元位置
        self.neuron_positions = []
        layer_spacing = 2.0 / (len(self.layer_sizes) - 1)
        
        for i, size in enumerate(self.layer_sizes):
            layer_x = -1 + i * layer_spacing
            neuron_spacing = 1.6 / max(size, 1)
            layer_neurons = []
            
            for j in range(size):
                neuron_y = -0.8 + j * neuron_spacing
                layer_neurons.append((layer_x, neuron_y))
            
            self.neuron_positions.append(layer_neurons)
    
    def generate_patterns(self):
        # 生成不同的激活模式
        patterns = []
        
        # 模式1: 波浪式激活
        for i in range(20):
            pattern = []
            for layer_idx in range(len(self.layer_sizes)):
                activation = 0.3 + 0.7 * abs(np.sin(i * 0.2 + layer_idx * 0.5))
                pattern.append(activation)
            patterns.append(pattern)
        
        # 模式2: 随机激活
        for i in range(10):
            pattern = [random.uniform(0.2, 0.9) for _ in range(len(self.layer_sizes))]
            patterns.append(pattern)
        
        return patterns
    
    def update_network(self):
        self.animation_time += 1
        
        # 切换模式
        if self.animation_time % 30 == 0:
            self.current_pattern = (self.current_pattern + 1) % len(self.patterns)
        
        # 更新激活水平
        target_pattern = self.patterns[self.current_pattern]
        for i in range(len(self.activation_levels)):
            # 平滑过渡到目标激活水平
            self.activation_levels[i] += (target_pattern[i] - self.activation_levels[i]) * self.learning_rate
        
        self.draw_network()
    
    def draw_network(self):
        self.clear()
        
        # 绘制连接
        for i in range(len(self.neuron_positions) - 1):
            for j, pos1 in enumerate(self.neuron_positions[i]):
                for k, pos2 in enumerate(self.neuron_positions[i + 1]):
                    # 连接强度基于激活水平
                    strength = min(self.activation_levels[i], self.activation_levels[i + 1]) * self.connection_strength
                    
                    if strength > 0.1:  # 只绘制显著连接
                        color = (255, 255, 255, int(255 * strength))
                        pen = pg.mkPen(color=color, width=strength * 3)
                        self.plot([pos1[0], pos2[0]], [pos1[1], pos2[1]], pen=pen)
        
        # 绘制神经元
        for i, layer in enumerate(self.neuron_positions):
            for j, pos in enumerate(layer):
                activation = self.activation_levels[i]
                size = 10 + activation * 15
                color = (int(255 * activation), 100, int(255 * (1 - activation)), 200)
                
                # 绘制神经元
                brush = pg.mkBrush(color=color)
                self.plot([pos[0]], [pos[1]], symbol='o', symbolSize=size, 
                         symbolBrush=brush, pen=None)
    
    def update_parameters(self, learning_rate, connection_strength):
        self.learning_rate = learning_rate
        self.connection_strength = connection_strength

class DataAnalysisDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("高级数据分析")
        self.setGeometry(200, 200, 800, 600)
        
        layout = QVBoxLayout()
        
        # 创建选项卡
        self.tabs = QTabWidget()
        
        # FFT分析选项卡
        self.fft_tab = QWidget()
        self.setup_fft_tab()
        self.tabs.addTab(self.fft_tab, "频谱分析")
        
        # 相关性分析选项卡
        self.correlation_tab = QWidget()
        self.setup_correlation_tab()
        self.tabs.addTab(self.correlation_tab, "相关性分析")
        
        layout.addWidget(self.tabs)
        self.setLayout(layout)
    
    def setup_fft_tab(self):
        layout = QVBoxLayout()
        
        # FFT图形显示
        self.fft_plot = pg.PlotWidget()
        self.fft_plot.setLabel('left', '幅度')
        self.fft_plot.setLabel('bottom', '频率', 'Hz')
        layout.addWidget(self.fft_plot)
        
        # 控制按钮
        button_layout = QHBoxLayout()
        self.analyze_btn = QPushButton("分析数据")
        self.export_fft_btn = QPushButton("导出频谱")
        button_layout.addWidget(self.analyze_btn)
        button_layout.addWidget(self.export_fft_btn)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        self.fft_tab.setLayout(layout)
    
    def setup_correlation_tab(self):
        layout = QVBoxLayout()
        
        # 相关性图形显示
        self.corr_plot = pg.PlotWidget()
        self.corr_plot.setLabel('left', '相关系数')
        self.corr_plot.setLabel('bottom', '时间延迟')
        layout.addWidget(self.corr_plot)
        
        self.corr_tab.setLayout(layout)
    
    def analyze_data(self, time_data, signal1, signal2):
        # 执行FFT分析
        n = len(time_data)
        if n > 0:
            dt = time_data[1] - time_data[0] if n > 1 else 1
            freqs = fftfreq(n, dt)
            fft1 = np.abs(fft(signal1))
            fft2 = np.abs(fft(signal2))
            
            # 绘制频谱
            self.fft_plot.clear()
            self.fft_plot.plot(freqs[:n//2], fft1[:n//2], pen='r', name='信号1')
            self.fft_plot.plot(freqs[:n//2], fft2[:n//2], pen='b', name='信号2')
            
            # 计算相关性
            correlation = np.correlate(signal1, signal2, mode='full')
            lags = np.arange(-n+1, n)
            
            self.corr_plot.clear()
            self.corr_plot.plot(lags, correlation, pen='g')

class SimulationEngine:
    def __init__(self):
        self.is_running = False
        self.simulation_speed = 1.0
        self.data_queue = Queue()
        self.thread = None
    
    def start_simulation(self):
        self.is_running = True
        self.thread = threading.Thread(target=self.run_simulation)
        self.thread.start()
    
    def stop_simulation(self):
        self.is_running = False
        if self.thread:
            self.thread.join()
    
    def run_simulation(self):
        while self.is_running:
            # 生成模拟数据
            timestamp = time.time()
            data = {
                'timestamp': timestamp,
                'quantum_state': np.random.normal(0, 1, 10),
                'neural_activity': np.random.random(20),
                'field_energy': random.uniform(0, 1)
            }
            
            self.data_queue.put(data)
            time.sleep(0.1 / self.simulation_speed)
    
    def get_data(self):
        if not self.data_queue.empty():
            return self.data_queue.get()
        return None

class EntanglementVisualization(PlotWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setBackground('transparent')
        self.getPlotItem().hideAxis('bottom')
        self.getPlotItem().hideAxis('left')
        
        # 创建绘图项
        self.gravity_wave = self.plot(pen=pg.mkPen(color='#00ff9f', width=3))
        self.brain_waves = self.plot(pen=pg.mkPen(color='#8a2be2', width=3))
        
        # 纠缠区域可视化
        self.entanglement_regions = []
        
        # 数据参数
        self.data_points = 200
        self.x = np.linspace(0, 10, self.data_points)
        self.gravity_data = np.zeros(self.data_points)
        self.brain_data = np.zeros(self.data_points)
        self.frame = 0
        
        # 动画参数
        self.gravity_amplitude = 0.5
        self.brain_amplitude = 0.5
        self.correlation_strength = 0.7
        self.noise_level = 0.05
        
        # 临界线
        self.critical_line = InfiniteLine(pos=0.7, angle=0, pen=pg.mkPen('#ff5555', width=2, style=Qt.DashLine))
        self.getPlotItem().addItem(self.critical_line)
        
        # 填充区域
        self.fill_region = FillBetweenItem(
            self.gravity_wave, self.brain_waves, 
            brush=pg.mkBrush((255, 100, 255, 50))
        )
        self.getPlotItem().addItem(self.fill_region)
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_plot)
        self.timer.start(50)
    
    def update_parameters(self, gravity_amp, brain_amp, correlation, noise):
        self.gravity_amplitude = gravity_amp
        self.brain_amplitude = brain_amp
        self.correlation_strength = correlation
        self.noise_level = noise
    
    def update_plot(self):
        self.frame += 1
        
        # 更新引力波数据
        phase_shift = self.frame / 20
        self.gravity_data = (
            np.sin(self.x + phase_shift) * 0.3 * self.gravity_amplitude + 
            np.sin(self.x*2.3 + phase_shift/1.5) * 0.2 * self.gravity_amplitude + 
            np.sin(self.x*4.7 + phase_shift/2) * 0.1 * self.gravity_amplitude + 
            np.random.normal(0, self.noise_level, self.data_points)
        )
        
        # 更新脑波数据（与引力波相关）
        brain_phase_shift = phase_shift * self.correlation_strength
        correlated_component = self.gravity_data * self.correlation_strength
        
        self.brain_data = (
            np.sin(self.x*1.5 + brain_phase_shift) * 0.4 * self.brain_amplitude + 
            np.sin(self.x*3.1 + brain_phase_shift/1.2) * 0.3 * np.sin(self.x/2) * self.brain_amplitude + 
            correlated_component * 0.5 +
            np.random.normal(0, self.noise_level, self.data_points)
        )
        
        self.gravity_wave.setData(self.x, self.gravity_data)
        self.brain_waves.setData(self.x, self.brain_data)
        
        # 更新填充区域
        self.fill_region.setCurves(self.gravity_wave, self.brain_waves)
    
    def export_data(self, filename):
        data = np.column_stack([self.x, self.gravity_data, self.brain_data])
        np.savetxt(filename, data, delimiter=',', header='Time,Gravity_Wave,Brain_Wave', comments='')

class RecursionVisualization(gl.GLViewWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setBackgroundColor('k')
        
        # 添加网格
        self.grid = gl.GLGridItem()
        self.grid.scale(2, 2, 2)
        self.addItem(self.grid)
        
        # 参数
        self.rotation_speed = 0.01
        self.universe_scale = 1.0
        self.recursion_depth = 4
        self.child_count_base = 3
        self.show_connections = True
        
        # 创建宇宙结构
        self.universes = []
        self.connections = []
        self.create_universe_structure()
        
        # 设置相机
        self.setCameraPosition(distance=15, elevation=30, azimuth=0)
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_rotation)
        self.timer.start(30)
        
        self.angle = 0
    
    def create_universe_structure(self):
        # 清除现有项目
        for item in self.universes + self.connections:
            self.removeItem(item)
        self.universes = []
        self.connections = []
        
        # 创建新的宇宙结构
        self.create_universe_level(0, self.recursion_depth, np.array([0, 0, 0]), self.universe_scale)
    
    def create_universe_level(self, depth, max_depth, position, scale):
        if depth > max_depth:
            return
            
        # 不同维度使用不同几何体
        if depth == 0:
            # 使用低细分的球体模拟二十面体
            mesh = gl.MeshData.sphere(rows=4, cols=4)
            color = (0.8, 0.2, 0.2, 0.9)  # 红色
            size = 0.8 * scale
        elif depth == 1:
            # 使用圆柱体模拟八面体
            mesh = gl.MeshData.cylinder(rows=4, cols=4, radius=[0.5, 0.5])
            color = (0.2, 0.8, 0.2, 0.8)  # 绿色
            size = 0.7 * scale
        elif depth == 2:
            # 使用更高细分的球体模拟十二面体
            mesh = gl.MeshData.sphere(rows=8, cols=8)
            color = (0.2, 0.2, 0.8, 0.7)  # 蓝色
            size = 0.6 * scale
        else:
            mesh = gl.MeshData.sphere(rows=6, cols=6)
            hue = depth / max_depth
            color = (hue, 1-hue, 0.5, 0.6)
            size = 0.5 * scale
        
        universe = gl.GLMeshItem(meshdata=mesh, smooth=True, color=color, 
                                shader='balloon', glOptions='opaque')
        universe.scale(size, size, size)
        universe.translate(position[0], position[1], position[2])
        self.addItem(universe)
        self.universes.append(universe)
        
        # 递归创建子宇宙
        child_count = self.child_count_base if depth == 0 else max(2, self.child_count_base - depth)
        for i in range(child_count):
            angle = (i / child_count) * 2 * np.pi
            distance = 2.0 * scale
            child_pos = position + np.array([
                np.cos(angle) * distance,
                np.sin(angle) * distance,
                np.sin(angle * 2) * distance * 0.5
            ])
            
            # 添加连接线
            if self.show_connections and depth < max_depth:
                line = gl.GLLinePlotItem(
                    pos=np.array([position, child_pos]),
                    color=(color[0], color[1], color[2], 0.6),
                    width=2
                )
                self.addItem(line)
                self.connections.append(line)
            
            self.create_universe_level(depth + 1, max_depth, child_pos, scale * 0.6)
    
    def update_parameters(self, rotation_speed, universe_scale, recursion_depth, child_count, show_connections):
        self.rotation_speed = rotation_speed
        self.universe_scale = universe_scale
        self.recursion_depth = recursion_depth
        self.child_count_base = child_count
        self.show_connections = show_connections
        
        # 重新创建宇宙结构
        self.create_universe_structure()
    
    def update_rotation(self):
        self.angle += self.rotation_speed
        for i, universe in enumerate(self.universes):
            universe.rotate(self.angle * (i % 3 + 1) * 0.1, 0, 1, 0)
            universe.rotate(self.angle * (i % 2 + 1) * 0.05, 1, 0, 0)
    
    def capture_image(self, filename):
        # 捕获当前视图为图像
        self.grabFrameBuffer().save(filename)

class CrystalVisualization(PlotWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setBackground('transparent')
        
        # 设置图表样式
        self.getPlotItem().setLabel('left', '活动强度')
        self.getPlotItem().setLabel('bottom', '时间 (秒)')
        
        # 创建绘图项
        self.brain_wave = self.plot(pen=pg.mkPen(color='#8a2be2', width=2), name='γ脑波活动 (40-100Hz)')
        self.crystal_param = self.plot(pen=pg.mkPen(color='#00ff9f', width=3), name='时间晶体序参量')
        
        # 参数 - 添加默认值
        self.data_points = 100
        self.x = np.linspace(0, 10, self.data_points)
        self.brain_data = np.zeros(self.data_points)
        self.crystal_data = np.zeros(self.data_points)
        self.critical_point = 0.7
        self.phase_transition_width = 0.1
        self.brain_freq = 1.0  # 添加默认值
        self.crystal_growth = 1.5  # 添加默认值
        
        # 添加临界线和区域
        self.critical_line = InfiniteLine(
            pos=self.critical_point, angle=0, 
            pen=pg.mkPen('#ff5555', width=2, style=Qt.DashLine)
        )
        self.getPlotItem().addItem(self.critical_line)
        
        # 创建相位区域
        self.phase_region = pg.LinearRegionItem(
            values=[self.critical_point - self.phase_transition_width/2, 
                    self.critical_point + self.phase_transition_width/2],
            brush=pg.mkBrush((0, 255, 159, 30)),
            movable=False
        )
        self.getPlotItem().addItem(self.phase_region)
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_plot)
        self.timer.start(100)
    
    def update_parameters(self, critical_point, transition_width, brain_freq, crystal_growth):
        self.critical_point = critical_point
        self.phase_transition_width = transition_width
        
        # 更新临界线和区域
        self.critical_line.setValue(critical_point)
        self.phase_region.setRegion([
            critical_point - transition_width/2, 
            critical_point + transition_width/2
        ])
        
        # 更新数据生成参数
        self.brain_freq = brain_freq
        self.crystal_growth = crystal_growth
    
    def update_plot(self):
        # 更新脑波数据
        self.brain_data = (
            np.sin(self.x * self.brain_freq) * 0.7 + 
            np.sin(self.x * self.brain_freq * 3) * 0.3 + 
            np.sin(self.x * self.brain_freq * 7) * 0.2 + 
            0.5 + np.random.normal(0, 0.1, self.data_points)
        )
        
        # 更新时间晶体序参量数据
        x_norm = self.x / 10
        self.crystal_data = (
            0.2 + 0.6 * (1 - np.exp(-x_norm * self.crystal_growth)) + 
            np.sin(self.x * 2) * 0.1 * (1 - np.exp(-x_norm * 2)) +
            np.random.normal(0, 0.05, self.data_points)
        )
        
        self.brain_wave.setData(self.x, self.brain_data)
        self.crystal_param.setData(self.x, self.crystal_data)
    
    def export_data(self, filename):
        data = np.column_stack([self.x, self.brain_data, self.crystal_data])
        np.savetxt(filename, data, delimiter=',', header='Time,Brain_Wave,Crystal_Parameter', comments='')

class ControlPanel(QDockWidget):
    def __init__(self, title, parent=None):
        super().__init__(title, parent)
        self.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        
        self.content = QWidget()
        self.setWidget(self.content)
        self.layout = QVBoxLayout(self.content)
        
        # 添加标题
        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #7cf; padding: 10px;")
        title_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(title_label)
        
        # 添加分隔线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet("color: rgba(100, 100, 255, 0.3);")
        self.layout.addWidget(line)
    
    def add_slider(self, label, min_val, max_val, default_val, callback):
        container = QWidget()
        layout = QHBoxLayout(container)
        
        label_widget = QLabel(label)
        label_widget.setStyleSheet("color: #e0e0ff;")
        layout.addWidget(label_widget)
        
        slider = QSlider(Qt.Horizontal)
        slider.setMinimum(int(min_val * 100))
        slider.setMaximum(int(max_val * 100))
        slider.setValue(int(default_val * 100))
        slider.valueChanged.connect(lambda val: callback(val / 100))
        layout.addWidget(slider)
        
        value_label = QLabel(f"{default_val:.2f}")
        value_label.setStyleSheet("color: #a0a0ff; min-width: 40px;")
        slider.valueChanged.connect(lambda val: value_label.setText(f"{val/100:.2f}"))
        layout.addWidget(value_label)
        
        self.layout.addWidget(container)
        return slider
    
    def add_spinbox(self, label, min_val, max_val, default_val, callback):
        container = QWidget()
        layout = QHBoxLayout(container)
        
        label_widget = QLabel(label)
        label_widget.setStyleSheet("color: #e0e0ff;")
        layout.addWidget(label_widget)
        
        spinbox = QSpinBox()
        spinbox.setMinimum(min_val)
        spinbox.setMaximum(max_val)
        spinbox.setValue(default_val)
        spinbox.valueChanged.connect(callback)
        layout.addWidget(spinbox)
        
        self.layout.addWidget(container)
        return spinbox
    
    def add_double_spinbox(self, label, min_val, max_val, default_val, callback):
        container = QWidget()
        layout = QHBoxLayout(container)
        
        label_widget = QLabel(label)
        label_widget.setStyleSheet("color: #e0e0ff;")
        layout.addWidget(label_widget)
        
        spinbox = QDoubleSpinBox()
        spinbox.setMinimum(min_val)
        spinbox.setMaximum(max_val)
        spinbox.setValue(default_val)
        spinbox.setSingleStep(0.1)
        spinbox.valueChanged.connect(callback)
        layout.addWidget(spinbox)
        
        self.layout.addWidget(container)
        return spinbox
    
    def add_checkbox(self, label, default_val, callback):
        container = QWidget()
        layout = QHBoxLayout(container)
        
        checkbox = QCheckBox(label)
        checkbox.setChecked(default_val)
        checkbox.stateChanged.connect(callback)
        checkbox.setStyleSheet("color: #e0e0ff;")
        layout.addWidget(checkbox)
        
        self.layout.addWidget(container)
        return checkbox
    
    def add_button(self, label, callback):
        button = QPushButton(label)
        button.clicked.connect(callback)
        button.setStyleSheet("""
            QPushButton {
                background-color: rgba(138, 43, 226, 0.3);
                color: #e0e0ff;
                border: 1px solid rgba(100, 100, 255, 0.5);
                border-radius: 5px;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: rgba(138, 43, 226, 0.5);
            }
            QPushButton:pressed {
                background-color: rgba(138, 43, 226, 0.7);
            }
        """)
        self.layout.addWidget(button)
        return button
    
    def add_combobox(self, label, items, default_index, callback):
        container = QWidget()
        layout = QHBoxLayout(container)
        
        label_widget = QLabel(label)
        label_widget.setStyleSheet("color: #e0e0ff;")
        layout.addWidget(label_widget)
        
        combobox = QComboBox()
        combobox.addItems(items)
        combobox.setCurrentIndex(default_index)
        combobox.currentIndexChanged.connect(callback)
        layout.addWidget(combobox)
        
        self.layout.addWidget(container)
        return combobox

class EnhancedMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("意识-时空统一理论可视化 - 增强版")
        self.setGeometry(50, 50, 1600, 1000)
        
        # 初始化模拟引擎
        self.simulation_engine = SimulationEngine()
        
        # 存储可视化对象
        self.visualizations = {}
        self.current_visualization = None
        
        # 数据记录
        self.data_log = []
        self.recording = False
        
        # 调整顺序：先设置状态栏，再设置UI
        self.setup_status_bar()  # 先调用
        self.setup_ui()
        self.setup_menus()
        
        # 启动模拟
        self.simulation_engine.start_simulation()
        
        # 数据更新定时器
        self.data_timer = QTimer(self)
        self.data_timer.timeout.connect(self.update_simulation_data)
        self.data_timer.start(100)
    
    def setup_ui(self):
        # 创建中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        main_layout = QVBoxLayout(central_widget)
        
        # 首先创建并添加背景
        self.background = AdvancedParticleBackground(central_widget)
        self.background.lower()
        
        # 创建内容布局（标题和选项卡）
        content_layout = QVBoxLayout()
        
        # 创建高级标题
        self.create_enhanced_header(content_layout)
        
        # 创建主选项卡
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet(self.get_tab_style())
        
        # 添加可视化选项卡
        self.create_enhanced_visualizations()
        
        content_layout.addWidget(self.tab_widget)
        
        # 将内容布局添加到主布局
        main_layout.addLayout(content_layout)
        
        # 创建高级控制面板
        self.create_enhanced_control_panels()
        
        # 设置样式
        self.apply_enhanced_styles()
        
        # 连接信号
        self.tab_widget.currentChanged.connect(self.on_tab_changed)
        
        # 延迟初始化选项卡
        QTimer.singleShot(100, lambda: self.on_tab_changed(0))
    
    def create_enhanced_header(self, layout):
        header_widget = QWidget()
        header_layout = QVBoxLayout(header_widget)
        
        # 主标题
        title_label = QLabel("意识-时空统一理论可视化平台")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("""
            QLabel {
                font-size: 42px;
                font-weight: bold;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #8a2be2, stop:0.3 #00bfff, stop:0.6 #00ff7f, stop:1 #ff00ff);
                -webkit-background-clip: text;
                color: transparent;
                padding: 15px;
            }
        """)
        
        # 副标题
        subtitle_label = QLabel("量子纠缠 · 递归创世 · 时间晶体 · 神经网络 · 量子场论")
        subtitle_label.setAlignment(Qt.AlignCenter)
        subtitle_label.setStyleSheet("font-size: 16px; color: #a0a0ff; margin-bottom: 10px;")
        
        # 状态指示器
        status_widget = QWidget()
        status_layout = QHBoxLayout(status_widget)
        
        self.quantum_indicator = self.create_status_indicator("量子态", "#ff5555")
        self.neural_indicator = self.create_status_indicator("神经活动", "#55ff55")
        self.field_indicator = self.create_status_indicator("场能量", "#5555ff")
        
        status_layout.addWidget(self.quantum_indicator)
        status_layout.addWidget(self.neural_indicator)
        status_layout.addWidget(self.field_indicator)
        status_layout.addStretch()
        
        header_layout.addWidget(title_label)
        header_layout.addWidget(subtitle_label)
        header_layout.addWidget(status_widget)
        layout.addWidget(header_widget)
    
    def create_status_indicator(self, text, color):
        container = QWidget()
        layout = QHBoxLayout(container)
        
        indicator = QLabel("●")
        indicator.setStyleSheet(f"color: {color}; font-size: 20px;")
        
        label = QLabel(text)
        label.setStyleSheet("color: #ccccff; font-size: 12px;")
        
        layout.addWidget(indicator)
        layout.addWidget(label)
        layout.setContentsMargins(5, 0, 5, 0)
        
        return container
    
    def create_enhanced_visualizations(self):
        # 量子纠缠可视化（增强版）
        entanglement_desc = """该理论揭示了意识活动与时空结构之间的量子纠缠关系。当大脑处于高γ波状态时，能够产生可测量的时空曲率扰动。"""
        entanglement_viz = EntanglementVisualization()
        entanglement_card = TheoryCard("意识-时空量子纠缠定理", entanglement_viz, entanglement_desc)
        self.tab_widget.addTab(entanglement_card, "🌌 量子纠缠")
        self.visualizations["entanglement"] = entanglement_viz
        
        # 递归创世可视化（增强版）
        recursion_desc = """每个宇宙都是上层宇宙的全息投影，创世过程遵循分形迭代公式。宇宙维度序列遵循精确的数学规律。"""
        recursion_viz = RecursionVisualization()
        recursion_card = TheoryCard("递归创世全息原理", recursion_viz, recursion_desc)
        self.tab_widget.addTab(recursion_card, "🌀 递归创世")
        self.visualizations["recursion"] = recursion_viz
        
        # 时间晶体可视化（增强版）
        crystal_desc = """意识本质是时间对称性破缺的宏观量子现象，大脑是生物时间晶体。当意识流强度超过临界值，系统进入时间晶体相。"""
        crystal_viz = CrystalVisualization()
        crystal_card = TheoryCard("时间晶体意识论", crystal_viz, crystal_desc)
        self.tab_widget.addTab(crystal_card, "⏳ 时间晶体")
        self.visualizations["crystal"] = crystal_viz
        
        # 新增：量子场可视化
        field_desc = """量子场论描述基本粒子如何通过场相互作用。意识可以被理解为量子场中的特殊激发模式。"""
        field_viz = QuantumFieldVisualization()
        field_card = TheoryCard("量子场意识理论", field_viz, field_desc)
        self.tab_widget.addTab(field_card, "⚛️ 量子场论")
        self.visualizations["field"] = field_viz
        
        # 新增：神经网络可视化
        neural_desc = """大脑神经网络与宇宙结构之间存在深刻的数学同构。神经网络活动模式反映了时空的基本几何。"""
        neural_viz = NeuralNetworkVisualization()
        neural_card = TheoryCard("神经网络宇宙学", neural_viz, neural_desc)
        self.tab_widget.addTab(neural_card, "🧠 神经网络")
        self.visualizations["neural"] = neural_viz
    
    def create_enhanced_control_panels(self):
        # 创建可停靠的控制面板
        self.create_entanglement_panel()
        self.create_recursion_panel()
        self.create_crystal_panel()
        self.create_field_panel()
        self.create_neural_panel()
        self.create_global_panel()
        
        # 默认显示全局控制面板
        self.addDockWidget(Qt.RightDockWidgetArea, self.global_panel)
    
    def create_field_panel(self):
        self.field_panel = ControlPanel("量子场控制", self)
        self.field_panel.add_slider("场强度", 0.1, 3.0, 1.0,
                                   lambda val: self.visualizations["field"].update_parameters(
                                       val, 
                                       self.visualizations["field"].wave_frequency,
                                       self.visualizations["field"].interference_enabled
                                   ))
        self.field_panel.add_slider("波频率", 0.5, 3.0, 1.0,
                                   lambda val: self.visualizations["field"].update_parameters(
                                       self.visualizations["field"].field_strength,
                                       val,
                                       self.visualizations["field"].interference_enabled
                                   ))
        self.field_panel.add_checkbox("干涉效应", True,
                                     lambda state: self.visualizations["field"].update_parameters(
                                         self.visualizations["field"].field_strength,
                                         self.visualizations["field"].wave_frequency,
                                         state == Qt.Checked
                                     ))
        self.field_panel.add_button("捕获场状态", self.capture_field_state)
    
    def create_neural_panel(self):
        self.neural_panel = ControlPanel("神经网络控制", self)
        self.neural_panel.add_slider("学习速率", 0.01, 0.5, 0.1,
                                    lambda val: self.visualizations["neural"].update_parameters(
                                        val,
                                        self.visualizations["neural"].connection_strength
                                    ))
        self.neural_panel.add_slider("连接强度", 0.1, 1.0, 0.7,
                                    lambda val: self.visualizations["neural"].update_parameters(
                                        self.visualizations["neural"].learning_rate,
                                        val
                                    ))
        self.neural_panel.add_button("重置网络", self.reset_neural_network)
    
    def create_entanglement_panel(self):
        self.entanglement_panel = ControlPanel("量子纠缠控制", self)
        self.entanglement_panel.add_slider("引力波幅度", 0.1, 2.0, 0.5,
                                        lambda val: self.visualizations["entanglement"].update_parameters(
                                            val,
                                            self.visualizations["entanglement"].brain_amplitude,
                                            self.visualizations["entanglement"].correlation_strength,
                                            self.visualizations["entanglement"].noise_level
                                        ))
        self.entanglement_panel.add_slider("脑波幅度", 0.1, 2.0, 0.5,
                                        lambda val: self.visualizations["entanglement"].update_parameters(
                                            self.visualizations["entanglement"].gravity_amplitude,
                                            val,
                                            self.visualizations["entanglement"].correlation_strength,
                                            self.visualizations["entanglement"].noise_level
                                        ))
        self.entanglement_panel.add_slider("关联强度", 0.0, 1.0, 0.7,
                                        lambda val: self.visualizations["entanglement"].update_parameters(
                                            self.visualizations["entanglement"].gravity_amplitude,
                                            self.visualizations["entanglement"].brain_amplitude,
                                            val,
                                            self.visualizations["entanglement"].noise_level
                                        ))
        self.entanglement_panel.add_slider("噪声水平", 0.0, 0.2, 0.05,
                                        lambda val: self.visualizations["entanglement"].update_parameters(
                                            self.visualizations["entanglement"].gravity_amplitude,
                                            self.visualizations["entanglement"].brain_amplitude,
                                            self.visualizations["entanglement"].correlation_strength,
                                            val
                                        ))
        self.entanglement_panel.add_button("导出数据", lambda: self.export_entanglement_data())

    def create_recursion_panel(self):
        self.recursion_panel = ControlPanel("递归创世控制", self)
        self.recursion_panel.add_slider("旋转速度", 0.0, 0.1, 0.01,
                                    lambda val: self.visualizations["recursion"].update_parameters(
                                        val,
                                        self.visualizations["recursion"].universe_scale,
                                        self.visualizations["recursion"].recursion_depth,
                                        self.visualizations["recursion"].child_count_base,
                                        self.visualizations["recursion"].show_connections
                                    ))
        self.recursion_panel.add_slider("宇宙尺度", 0.5, 3.0, 1.0,
                                    lambda val: self.visualizations["recursion"].update_parameters(
                                        self.visualizations["recursion"].rotation_speed,
                                        val,
                                        self.visualizations["recursion"].recursion_depth,
                                        self.visualizations["recursion"].child_count_base,
                                        self.visualizations["recursion"].show_connections
                                    ))
        self.recursion_panel.add_spinbox("递归深度", 1, 6, 4,
                                        lambda val: self.visualizations["recursion"].update_parameters(
                                            self.visualizations["recursion"].rotation_speed,
                                            self.visualizations["recursion"].universe_scale,
                                            val,
                                            self.visualizations["recursion"].child_count_base,
                                            self.visualizations["recursion"].show_connections
                                        ))
        self.recursion_panel.add_spinbox("子宇宙数量", 1, 8, 3,
                                        lambda val: self.visualizations["recursion"].update_parameters(
                                            self.visualizations["recursion"].rotation_speed,
                                            self.visualizations["recursion"].universe_scale,
                                            self.visualizations["recursion"].recursion_depth,
                                            val,
                                            self.visualizations["recursion"].show_connections
                                        ))
        self.recursion_panel.add_checkbox("显示连接", True,
                                        lambda state: self.visualizations["recursion"].update_parameters(
                                            self.visualizations["recursion"].rotation_speed,
                                            self.visualizations["recursion"].universe_scale,
                                            self.visualizations["recursion"].recursion_depth,
                                            self.visualizations["recursion"].child_count_base,
                                            state == Qt.Checked
                                        ))
        self.recursion_panel.add_button("捕获图像", lambda: self.capture_recursion_image())

    def create_crystal_panel(self):
        self.crystal_panel = ControlPanel("时间晶体控制", self)
        self.crystal_panel.add_slider("临界点", 0.1, 0.9, 0.7,
                                    lambda val: self.visualizations["crystal"].update_parameters(
                                        val,
                                        self.visualizations["crystal"].phase_transition_width,
                                        self.visualizations["crystal"].brain_freq,
                                        self.visualizations["crystal"].crystal_growth
                                    ))
        self.crystal_panel.add_slider("相变宽度", 0.01, 0.3, 0.1,
                                    lambda val: self.visualizations["crystal"].update_parameters(
                                        self.visualizations["crystal"].critical_point,
                                        val,
                                        self.visualizations["crystal"].brain_freq,
                                        self.visualizations["crystal"].crystal_growth
                                    ))
        self.crystal_panel.add_slider("脑波频率", 0.5, 3.0, 1.0,
                                    lambda val: self.visualizations["crystal"].update_parameters(
                                        self.visualizations["crystal"].critical_point,
                                        self.visualizations["crystal"].phase_transition_width,
                                        val,
                                        self.visualizations["crystal"].crystal_growth
                                    ))
        self.crystal_panel.add_slider("晶体生长", 0.5, 3.0, 1.5,
                                    lambda val: self.visualizations["crystal"].update_parameters(
                                        self.visualizations["crystal"].critical_point,
                                        self.visualizations["crystal"].phase_transition_width,
                                        self.visualizations["crystal"].brain_freq,
                                        val
                                    ))
        self.crystal_panel.add_button("导出数据", lambda: self.export_crystal_data())
    
    def create_global_panel(self):
        self.global_panel = ControlPanel("全局控制", self)
        
        # 添加新控件
        self.global_panel.add_combobox("颜色主题", 
                                      ["quantum", "plasma", "cosmic", "neural"], 
                                      0, self.change_color_theme)
        
        self.global_panel.add_slider("模拟速度", 0.1, 5.0, 1.0,
                                    self.change_simulation_speed)
        
        self.global_panel.add_checkbox("数据记录", False,
                                      self.toggle_data_recording)
        
        self.global_panel.add_button("数据分析", self.open_data_analysis)
        self.global_panel.add_button("保存会话", self.save_session)
        self.global_panel.add_button("加载会话", self.load_session)
        
        # 原版控件...
        self.global_panel.add_slider("粒子数量", 50, 800, 300,
                                    lambda val: self.background.set_particle_count(int(val)))
    
    def setup_menus(self):
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu("文件")
        
        new_action = QAction("新建会话", self)
        new_action.setShortcut(QKeySequence.New)
        file_menu.addAction(new_action)
        
        save_action = QAction("保存会话", self)
        save_action.setShortcut(QKeySequence.Save)
        file_menu.addAction(save_action)
        
        file_menu.addSeparator()
        
        export_data_action = QAction("导出数据", self)
        file_menu.addAction(export_data_action)
        
        # 视图菜单
        view_menu = menubar.addMenu("视图")
        
        fullscreen_action = QAction("全屏模式", self)
        fullscreen_action.setShortcut("F11")
        fullscreen_action.triggered.connect(self.toggle_fullscreen)
        view_menu.addAction(fullscreen_action)
        
        # 工具菜单
        tools_menu = menubar.addMenu("工具")
        
        data_analysis_action = QAction("数据分析工具", self)
        data_analysis_action.triggered.connect(self.open_data_analysis)
        tools_menu.addAction(data_analysis_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu("帮助")
        
        about_action = QAction("关于", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def setup_status_bar(self):
        status_bar = QStatusBar()
        self.setStatusBar(status_bar)
        
        self.status_label = QLabel("就绪")
        status_bar.addWidget(self.status_label)
        
        self.performance_label = QLabel("")
        status_bar.addPermanentWidget(self.performance_label)
        
        # 性能监控定时器
        self.performance_timer = QTimer(self)
        self.performance_timer.timeout.connect(self.update_performance)
        self.performance_timer.start(1000)
    
    def update_performance(self):
        memory_usage = "内存: {:.1f}MB".format(self.get_memory_usage())
        fps = "FPS: {}".format(getattr(self.background, 'fps', 0))
        self.performance_label.setText(f"{memory_usage} | {fps}")
    
    def get_memory_usage(self):
        import psutil
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024
    
    def update_simulation_data(self):
        data = self.simulation_engine.get_data()
        if data:
            # 更新状态指示器
            self.update_status_indicators(data)
            
            # 记录数据
            if self.recording:
                self.data_log.append(data)
    
    def update_status_indicators(self, data):
        # 更新量子态指示器
        quantum_level = np.mean(np.abs(data['quantum_state']))
        self.update_indicator_color(self.quantum_indicator, quantum_level)
        
        # 更新神经活动指示器
        neural_level = np.mean(data['neural_activity'])
        self.update_indicator_color(self.neural_indicator, neural_level)
        
        # 更新场能量指示器
        field_level = data['field_energy']
        self.update_indicator_color(self.field_indicator, field_level)
    
    def update_indicator_color(self, indicator, level):
        """根据水平更新指示器颜色强度"""
        # 查找指示器中的QLabel
        indicator_label = None
        for child in indicator.findChildren(QLabel):
            if child.text() == "●":  # 找到指示器圆点
                indicator_label = child
                break
        
        if indicator_label:
            intensity = int(255 * level)
            indicator_label.setStyleSheet(f"color: rgba({intensity}, {intensity}, {intensity}, 255); font-size: 20px;")
    
    def change_color_theme(self, index):
        themes = ["quantum", "plasma", "cosmic", "neural"]
        self.background.set_color_scheme(themes[index])
    
    def change_simulation_speed(self, speed):
        self.simulation_engine.simulation_speed = speed
    
    def toggle_data_recording(self, state):
        self.recording = state == Qt.Checked
        status = "开启" if self.recording else "停止"
        self.status_label.setText(f"数据记录已{status}")
    
    def open_data_analysis(self):
        dialog = DataAnalysisDialog(self)
        
        # 如果有数据，进行分析
        if hasattr(self, 'data_log') and len(self.data_log) > 0:
            # 提取示例数据进行演示
            time_data = np.arange(100)
            signal1 = np.sin(time_data * 0.1)
            signal2 = np.cos(time_data * 0.1)
            dialog.analyze_data(time_data, signal1, signal2)
        
        dialog.exec_()
    
    def save_session(self):
        filename, _ = QFileDialog.getSaveFileName(
            self, "保存会话", "", "会话文件 (*.session)"
        )
        if filename:
            session_data = {
                'timestamp': datetime.now().isoformat(),
                'visualization_states': {},
                'simulation_data': list(self.data_log)[-1000:],  # 保存最近1000个数据点
                'settings': {
                    'simulation_speed': self.simulation_engine.simulation_speed,
                    'color_theme': self.background.color_scheme
                }
            }
            
            try:
                with open(filename, 'w') as f:
                    json.dump(session_data, f, indent=2)
                self.status_label.setText("会话已保存")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"保存会话失败: {str(e)}")
    
    def load_session(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, "加载会话", "", "会话文件 (*.session)"
        )
        if filename:
            try:
                with open(filename, 'r') as f:
                    session_data = json.load(f)
                
                # 应用设置
                if 'settings' in session_data:
                    settings = session_data['settings']
                    self.simulation_engine.simulation_speed = settings.get('simulation_speed', 1.0)
                    # 应用其他设置...
                
                self.status_label.setText("会话已加载")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"加载会话失败: {str(e)}")
    
    def capture_field_state(self):
        filename, _ = QFileDialog.getSaveFileName(
            self, "保存场状态", "", "PNG图像 (*.png)"
        )
        if filename:
            # 实现场状态捕获逻辑
            pass
    
    def reset_neural_network(self):
        if "neural" in self.visualizations:
            self.visualizations["neural"].create_network()
    
    def export_entanglement_data(self):
        filename, _ = QFileDialog.getSaveFileName(
            self, "导出纠缠数据", "", "CSV文件 (*.csv)"
        )
        if filename:
            self.visualizations["entanglement"].export_data(filename)
            self.status_label.setText("纠缠数据已导出")

    def capture_recursion_image(self):
        filename, _ = QFileDialog.getSaveFileName(
            self, "保存递归图像", "", "PNG图像 (*.png)"
        )
        if filename:
            self.visualizations["recursion"].capture_image(filename)
            self.status_label.setText("递归图像已保存")

    def export_crystal_data(self):
        filename, _ = QFileDialog.getSaveFileName(
            self, "导出晶体数据", "", "CSV文件 (*.csv)"
        )
        if filename:
            self.visualizations["crystal"].export_data(filename)
            self.status_label.setText("晶体数据已导出")

    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def show_about(self):
        about_text = """
        <h2>意识-时空统一理论可视化平台</h2>
        <p>版本 2.0 - 增强版</p>
        <p>基于量子力学、广义相对论、神经科学的统一理论框架</p>
        <p>功能特性：</p>
        <ul>
            <li>多维度可视化系统</li>
            <li>实时数据模拟与分析</li>
            <li>高级交互控制</li>
            <li>会话保存与加载</li>
            <li>性能监控与优化</li>
        </ul>
        <p>© 2024 贾轩垚与DeepSeek联合研究项目</p>
        """
        QMessageBox.about(self, "关于", about_text)
    
    def get_tab_style(self):
        return """
            QTabWidget::pane {
                border: 3px solid rgba(100, 100, 255, 0.4);
                border-radius: 12px;
                background-color: rgba(25, 22, 56, 0.4);
            }
            QTabBar::tab {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(40, 37, 76, 0.8), stop:1 rgba(25, 22, 56, 0.8));
                border: 2px solid rgba(100, 100, 255, 0.4);
                border-bottom: none;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
                padding: 10px 20px;
                color: #b0b0ff;
                font-weight: bold;
                font-size: 14px;
            }
            QTabBar::tab:selected {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(138, 43, 226, 0.6), stop:1 rgba(100, 20, 200, 0.6));
                color: #ffffff;
            }
            QTabBar::tab:hover {
                background: rgba(138, 43, 226, 0.4);
            }
        """
    
    def apply_enhanced_styles(self):
        self.setStyleSheet("""
            QMainWindow {
                background: radial-gradient(circle at center, #0a081f, #000000);
            }
            QDockWidget {
                titlebar-close-icon: url(close.png);
                titlebar-normal-icon: url(float.png);
            }
            QDockWidget::title {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(138, 43, 226, 0.7), stop:1 rgba(0, 191, 255, 0.7));
                padding: 6px;
                border: 1px solid rgba(100, 100, 255, 0.3);
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
        """)
    
    def closeEvent(self, event):
        # 停止模拟引擎
        self.simulation_engine.stop_simulation()
        super().closeEvent(event)

    def on_tab_changed(self, index):
        """处理选项卡切换事件"""
        # 隐藏所有控制面板
        self.hide_all_control_panels()
        
        # 显示全局控制面板（始终显示）
        self.addDockWidget(Qt.RightDockWidgetArea, self.global_panel)
        
        # 根据当前选项卡显示对应的控制面板
        tab_text = self.tab_widget.tabText(index)
        if tab_text == "🌌 量子纠缠":
            self.addDockWidget(Qt.RightDockWidgetArea, self.entanglement_panel)
            self.current_visualization = "entanglement"
        elif tab_text == "🌀 递归创世":
            self.addDockWidget(Qt.RightDockWidgetArea, self.recursion_panel)
            self.current_visualization = "recursion"
        elif tab_text == "⏳ 时间晶体":
            self.addDockWidget(Qt.RightDockWidgetArea, self.crystal_panel)
            self.current_visualization = "crystal"
        elif tab_text == "⚛️ 量子场论":
            self.addDockWidget(Qt.RightDockWidgetArea, self.field_panel)
            self.current_visualization = "field"
        elif tab_text == "🧠 神经网络":
            self.addDockWidget(Qt.RightDockWidgetArea, self.neural_panel)
            self.current_visualization = "neural"
        
        # 更新状态栏
        self.status_label.setText(f"当前可视化: {tab_text}")

    def hide_all_control_panels(self):
        """隐藏所有专业控制面板"""
        panels = [self.entanglement_panel, self.recursion_panel, 
                self.crystal_panel, self.field_panel, self.neural_panel]
        for panel in panels:
            self.removeDockWidget(panel)


class TheoryCard(QGroupBox):
    def __init__(self, title, visualization, description, parent=None):
        super().__init__(title, parent)
        self.setStyleSheet("""
            QGroupBox {
                font-size: 18px;
                font-weight: bold;
                color: #7cf;
                border: 2px solid rgba(100, 100, 255, 0.3);
                border-radius: 15px;
                margin-top: 1ex;
                background-color: rgba(25, 22, 56, 0.6);
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #7cf;
            }
        """)
        
        layout = QVBoxLayout()
        
        # 描述标签
        desc_label = QLabel(description)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #e0e0ff; font-size: 14px; padding: 10px;")
        layout.addWidget(desc_label)
        
        # 可视化部件
        layout.addWidget(visualization)
        
        self.setLayout(layout)

# 增强的理论卡片类
class EnhancedTheoryCard(TheoryCard):
    def __init__(self, title, visualization, description, parent=None):
        super().__init__(title, visualization, description, parent)
        
        # 添加更多交互元素
        self.setup_enhanced_card()
    
    def setup_enhanced_card(self):
        layout = self.layout()
        
        # 添加控制按钮栏
        control_bar = QHBoxLayout()
        
        self.info_btn = QPushButton("ℹ️ 详细信息")
        self.export_btn = QPushButton("📊 导出")
        self.animate_btn = QPushButton("▶️ 动画")
        
        for btn in [self.info_btn, self.export_btn, self.animate_btn]:
            btn.setStyleSheet("""
                QPushButton {
                    background: rgba(138, 43, 226, 0.3);
                    border: 1px solid rgba(100, 100, 255, 0.5);
                    border-radius: 3px;
                    padding: 3px 8px;
                    color: #e0e0ff;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background: rgba(138, 43, 226, 0.5);
                }
            """)
            control_bar.addWidget(btn)
        
        control_bar.addStretch()
        layout.insertLayout(1, control_bar)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 设置高级样式
    app.setStyle('Fusion')
    
    # 加载字体
    font_id = QFontDatabase.addApplicationFontFromData(b"")  # 可以加载自定义字体
    if font_id >= 0:
        font_families = QFontDatabase.applicationFontFamilies(font_id)
        if font_families:
            app.setFont(QFont(font_families[0], 10))
    
    # 设置高级调色板
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(10, 8, 31))
    palette.setColor(QPalette.WindowText, QColor(224, 224, 255))
    palette.setColor(QPalette.Base, QColor(30, 27, 60))
    palette.setColor(QPalette.AlternateBase, QColor(40, 37, 80))
    palette.setColor(QPalette.ToolTipBase, QColor(224, 224, 255))
    palette.setColor(QPalette.ToolTipText, QColor(224, 224, 255))
    palette.setColor(QPalette.Text, QColor(224, 224, 255))
    palette.setColor(QPalette.Button, QColor(35, 32, 70))
    palette.setColor(QPalette.ButtonText, QColor(224, 224, 255))
    palette.setColor(QPalette.BrightText, QColor(255, 255, 255))
    palette.setColor(QPalette.Highlight, QColor(138, 43, 226))
    palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
    app.setPalette(palette)
    
    # 创建主窗口
    window = EnhancedMainWindow()
    window.show()
    
    # 启动应用程序
    sys.exit(app.exec_())