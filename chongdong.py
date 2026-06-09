import sys
import os
import numpy as np
import matplotlib
matplotlib.rc("font", family='Microsoft YaHei')
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QSplitter, QTabWidget, QGroupBox, QSlider, QLabel, QPushButton,
    QDoubleSpinBox, QComboBox, QStatusBar, QFileDialog, QCheckBox,
    QDockWidget, QTreeWidget, QTreeWidgetItem, QTextEdit, QProgressBar,
    QGridLayout, QSizePolicy, QAction, QMenu, QMessageBox, QToolBar
)
from PyQt5.QtCore import Qt, QTimer, QSize, QThread, pyqtSignal
from PyQt5.QtGui import QIcon, QFont, QPalette, QColor
from mpl_toolkits.mplot3d import Axes3D
import tensorflow as tf
from qiskit.quantum_info import Statevector
import time
import json
import scipy.integrate as integrate
import logging
from datetime import datetime

# 配置日志系统
logging.basicConfig(
    filename='vacuum_engine.log',
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('VacuumEmergenceEngine')

# ========================
# 增强物理引擎
# ========================

class QuantumGravityEngine:
    """量子引力引擎 - 处理时空度规和虫洞结构"""
    def __init__(self, size=256):
        self.size = size
        self.metric = np.zeros((size, size, 4, 4))
        self.curvature = np.zeros((size, size))
        self.planck_scale = 1.0
        self.wormhole_radius = 0.5
        self.spin_network = np.random.rand(size, size)
        self.update_metric()
        
    def update_metric(self):
        """更新时空度规"""
        center_x, center_y = self.size//2, self.size//2
        
        for i in range(self.size):
            for j in range(self.size):
                # 计算到中心的距离
                r = np.sqrt((i-center_x)**2 + (j-center_y)**2)
                
                # 创建4x4单位矩阵
                g = np.eye(4)
                
                # 量子引力修正
                curvature = self.spin_network[i,j] * self.planck_scale**2
                g[0,0] = -1.0 + 0.1 * curvature * np.sin(i/10)
                g[1,1] = 1.0 + 0.2 * curvature * np.cos(j/10)
                
                # 虫洞喉部区域
                if r < self.size//8 * self.wormhole_radius:
                    # 喉部度规修正
                    throat_factor = 1.0 - (r/(self.size//8 * self.wormhole_radius))**2
                    g[0,0] = -0.5 * throat_factor
                    if throat_factor > 0.01:
                        g[1,1] = 2.0 / throat_factor
                    else:
                        g[1,1] = 100.0
                
                self.metric[i,j] = g
                self.curvature[i,j] = curvature
                
        return self.metric
    
    def generate_spin_network(self):
        """生成新的自旋网络"""
        self.spin_network = np.random.rand(self.size, self.size)
        self.update_metric()
    
    def get_wormhole_throat(self):
        """获取虫洞喉部截面"""
        center = self.size//2
        return self.metric[center-5:center+5, center-5:center+5, :, :]
    
    def visualize_metric_component(self, component):
        """可视化特定度规分量"""
        if component == "g_tt":
            return self.metric[:, :, 0, 0]
        elif component == "g_rr":
            return self.metric[:, :, 1, 1]
        elif component == "g_θθ":
            return self.metric[:, :, 2, 2]
        elif component == "g_φφ":
            return self.metric[:, :, 3, 3]
        return self.curvature
    
    def calculate_geodesic(self, start_point, end_point):
        """计算测地线"""
        # 简化的测地线计算
        path = []
        x0, y0 = start_point
        x1, y1 = end_point
        
        steps = 100
        for i in range(steps + 1):
            t = i / steps
            x = x0 + (x1 - x0) * t
            y = y0 + (y1 - y0) * t
            path.append((x, y))
            
        return np.array(path)
    
    def calculate_geodesic_3d(self, start_point, end_point):
        """计算3D测地线"""
        path = self.calculate_geodesic(start_point, end_point)
        x = path[:, 0]
        y = path[:, 1]
        
        # 基于曲率的高度函数
        z = np.zeros_like(x)
        for i in range(len(x)):
            ix, iy = int(x[i]), int(y[i])
            if 0 <= ix < self.size and 0 <= iy < self.size:
                z[i] = self.curvature[ix, iy] * 10
            else:
                z[i] = 0
                
        return x, y, z

class StringTheoryEngine:
    """弦论引擎 - 处理弦的振动和量子涨落"""
    def __init__(self, N=100, tension=1.0):
        self.N = N  # 弦离散点数
        self.T = tension  # 弦张力
        self.X = np.zeros((3, N))  # 弦位置
        self.V = np.zeros((3, N))  # 弦速度
        self.quantum_fluctuation_scale = 0.01
        self.initialize_string()
        self.vibration_history = []
        self.energy_history = []
        
    def initialize_string(self):
        """初始化弦位置"""
        self.X[0] = np.linspace(-1, 1, self.N)
        self.X[1] = 0.1 * np.sin(np.pi * np.linspace(0, 1, self.N))
        self.V = np.zeros_like(self.X)
        
    def evolve(self, dt, steps=1):
        """演化弦的波动方程: ∂²X/∂t² = T ∂²X/∂σ²"""
        for _ in range(steps):
            # 中心差分法
            d2X_ds2 = np.zeros_like(self.X)
            d2X_ds2[:, 1:-1] = self.X[:, :-2] - 2*self.X[:, 1:-1] + self.X[:, 2:]
            
            # 边界条件 (固定端点)
            d2X_ds2[:, 0] = 0
            d2X_ds2[:, -1] = 0
            
            # 更新速度和位置
            self.V += self.T * d2X_ds2 * dt
            self.X += self.V * dt
            
            # 添加量子涨落
            self.quantum_fluctuations()
            
            # 记录振动历史和能量
            self.vibration_history.append(self.X.copy())
            self.energy_history.append(self.total_energy())
            
            if len(self.vibration_history) > 100:
                self.vibration_history.pop(0)
            if len(self.energy_history) > 100:
                self.energy_history.pop(0)
            
    def quantum_fluctuations(self):
        """添加量子涨落"""
        fluctuation = self.quantum_fluctuation_scale * np.random.randn(3, self.N)
        self.X += fluctuation
        self.V += 0.1 * self.quantum_fluctuation_scale * np.random.randn(3, self.N)
        
    def energy_spectrum(self):
        """计算振动模式能量谱"""
        modes = np.fft.rfft(self.X, axis=1)
        return np.sum(np.abs(modes)**2, axis=0)
    
    def total_energy(self):
        """计算弦的总能量"""
        kinetic = 0.5 * np.sum(self.V**2)
        potential = 0.5 * self.T * np.sum((self.X[:, 1:] - self.X[:, :-1])**2)
        return kinetic + potential
    
    def get_string_positions(self):
        """获取弦的当前位置"""
        return self.X.copy()
    
    def get_vibration_history(self):
        """获取振动历史"""
        return self.vibration_history.copy()
    
    def get_energy_history(self):
        """获取能量历史"""
        return self.energy_history.copy()

class HolographicRGEngine:
    """全息重整化群引擎 - 处理AdS/CFT对偶"""
    def __init__(self, size=64):
        self.size = size
        self.boundary_field = np.random.randn(size, size)
        self.bulk_field = np.zeros((size, size))
        self.rg_steps = 10
        self.learning_rate = 0.1
        self.init_model()
        self.history = []
        
    def init_model(self):
        """初始化深度学习模型"""
        self.model = tf.keras.Sequential([
            tf.keras.layers.InputLayer(input_shape=(self.size, self.size, 1)),
            tf.keras.layers.Conv2D(32, (3,3), activation='relu', padding='same'),
            tf.keras.layers.AveragePooling2D((2,2)),
            tf.keras.layers.Conv2D(64, (3,3), activation='relu', padding='same'),
            tf.keras.layers.AveragePooling2D((2,2)),
            tf.keras.layers.Conv2D(128, (3,3), activation='relu', padding='same'),
            tf.keras.layers.UpSampling2D((2,2)),
            tf.keras.layers.Conv2D(64, (3,3), activation='relu', padding='same'),
            tf.keras.layers.UpSampling2D((2,2)),
            tf.keras.layers.Conv2D(1, (3,3), activation='linear', padding='same')
        ])
        self.model.compile(optimizer='adam', loss='mse')
        
    def flow_to_bulk(self):
        """从边界CFT流向体引力理论"""
        input_field = self.boundary_field.reshape(1, self.size, self.size, 1)
        
        for _ in range(self.rg_steps):
            with tf.GradientTape() as tape:
                self.bulk_field = self.model(input_field)
                loss = tf.reduce_mean(self.bulk_field**2)  # 最小化作用量
                
            grads = tape.gradient(loss, self.model.trainable_variables)
            for var, grad in zip(self.model.trainable_variables, grads):
                var.assign_sub(self.learning_rate * grad)
                
        self.bulk_field = self.bulk_field.numpy()[0,:,:,0]
        self.history.append(self.bulk_field.copy())
        if len(self.history) > 20:
            self.history.pop(0)
        return self.bulk_field
    
    def get_history_frame(self, index):
        """获取历史帧"""
        if not self.history:
            return None
        return self.history[max(0, min(index, len(self.history)-1))]

class QuantumErrorCorrection:
    """量子纠错系统 - 确保传输稳定性"""
    def __init__(self, code_size=3):
        self.code_size = code_size
        self.n = code_size * code_size  # 物理量子比特数
        self.logical_state = Statevector.from_label('0'*self.n)
        self.error_probability = 0.05
        self.correction_history = []
        self.error_history = []
        self.stabilizer_history = []
        
    def apply_noise(self):
        """施加量子噪声"""
        errors = 0
        for i in range(self.n):
            if np.random.rand() < self.error_probability:
                # Pauli X错误
                self.logical_state = self.logical_state.evolve(self.pauli_error(['X'], [i]))
                errors += 1
        self.error_history.append(errors)
        return errors
        
    def correct_errors(self):
        """执行拓扑纠错"""
        errors = self.apply_noise()
        # 简化的纠错过程 - 实际应用中需要更复杂的逻辑
        # 这里我们使用随机旋转来模拟纠错效果
        correction = np.random.rand(self.n) < 0.3
        for i in range(self.n):
            if correction[i]:
                self.logical_state = self.logical_state.evolve(self.pauli_error(['X'], [i]))
        
        # 计算保真度 (简化版)
        target_state = Statevector.from_label('0'*self.n)
        fidelity = np.abs(self.logical_state.data.dot(target_state.data.conj()))**2
        self.correction_history.append(fidelity)
        
        # 计算稳定子测量 - 修复：使用.tolist()将NumPy数组转换为Python列表
        stabilizer = np.random.rand(3).tolist()  # 简化的稳定子值
        self.stabilizer_history.append(stabilizer)
        
        return fidelity, errors, stabilizer
        
    def pauli_error(self, pauli, qubits):
        """创建Pauli错误算子"""
        from qiskit.quantum_info import Operator, Pauli
        from functools import reduce
        import operator
        
        # 创建单位矩阵
        op = Operator(np.eye(2**self.n))
        
        # 应用Pauli门到指定量子比特
        for p, q in zip(pauli, qubits):
            pauli_op = Pauli(p).to_matrix()
            # 构造完整算子
            full_op = reduce(operator.xor, [Operator(np.eye(2**q)), 
                             Operator(pauli_op), 
                             Operator(np.eye(2**(self.n - q - 1)))], 
                            Operator(np.eye(1)))
            op = op.compose(full_op)
            
        return op

class ParticleTransport:
    """粒子传输引擎"""
    def __init__(self, grid_size=128):
        self.grid_size = grid_size
        self.particles = []
        self.transport_paths = {}
        self.transport_progress = {}
        self.particle_history = {}
        
    def add_particle(self, particle_id, start_pos, end_pos):
        """添加粒子"""
        self.particles.append(particle_id)
        self.transport_paths[particle_id] = (start_pos, end_pos)
        self.transport_progress[particle_id] = 0.0
        self.particle_history[particle_id] = []
        
    def update_transport(self, dt):
        """更新传输进度"""
        for particle_id in self.particles:
            self.transport_progress[particle_id] += dt * 0.1
            if self.transport_progress[particle_id] > 1.0:
                self.transport_progress[particle_id] = 1.0
                
            # 记录粒子位置历史
            pos = self.get_particle_position(particle_id)
            self.particle_history[particle_id].append(pos)
            if len(self.particle_history[particle_id]) > 100:
                self.particle_history[particle_id].pop(0)
                
    def get_particle_position(self, particle_id):
        """获取粒子当前位置"""
        if particle_id not in self.transport_paths:
            return None
            
        start_pos, end_pos = self.transport_paths[particle_id]
        progress = self.transport_progress[particle_id]
        
        # 线性插值
        x = start_pos[0] + (end_pos[0] - start_pos[0]) * progress
        y = start_pos[1] + (end_pos[1] - start_pos[1]) * progress
        return (x, y)
    
    def get_particle_history(self, particle_id):
        """获取粒子历史轨迹"""
        return self.particle_history.get(particle_id, [])

# ========================
# 集成真空演生引擎
# ========================

class VacuumEmergenceEngine:
    """集成所有物理引擎的主系统"""
    def __init__(self):
        # 物理引擎
        self.gravity_engine = QuantumGravityEngine(size=128)
        self.string_engine = StringTheoryEngine(N=100)
        self.rg_engine = HolographicRGEngine(size=64)
        self.qec = QuantumErrorCorrection(code_size=3)
        self.particle_transport = ParticleTransport()
        
        # 传输状态
        self.transport_progress = 0.0
        self.quantum_state = self.create_initial_state()
        self.rg_engine.boundary_field = np.abs(self.quantum_state)
        
        # 仿真参数
        self.time_step = 0.1
        self.simulation_running = False
        self.visualization_mode = "3D"
        
        # 添加示例粒子
        self.particle_transport.add_particle("particle1", (10, 10), (110, 110))
        self.particle_transport.add_particle("particle2", (110, 10), (10, 110))
        
    def create_initial_state(self, size=64):
        """创建初始量子态"""
        x = np.linspace(-5, 5, size)
        y = np.linspace(-5, 5, size)
        X, Y = np.meshgrid(x, y)
        return np.exp(-(X**2 + Y**2)/2) * np.exp(1j*X*2)
    
    def evolve_system(self):
        """演化整个系统一个时间步"""
        if not self.simulation_running:
            return 0.0, 0, [0,0,0], 0.0
            
        # 1. 弦论引擎演化
        self.string_engine.evolve(self.time_step)
        
        # 2. 量子纠错
        fidelity, errors, stabilizer = self.qec.correct_errors()
        
        # 3. 更新传输进度
        self.transport_progress += self.time_step * 0.1
        if self.transport_progress > 1.0:
            self.transport_progress = 1.0
            
        # 4. 全息RG流
        if self.transport_progress < 0.3:
            # 源端编码
            self.rg_engine.boundary_field = np.abs(self.quantum_state) * (1 - self.transport_progress/0.3)
        elif self.transport_progress < 0.7:
            # 虫洞传输
            self.rg_engine.flow_to_bulk()
        else:
            # 目标端重组
            target_field = np.roll(np.abs(self.quantum_state), shift=50, axis=1)
            self.rg_engine.boundary_field = target_field * ((self.transport_progress-0.7)/0.3)
        
        # 5. 更新粒子传输
        self.particle_transport.update_transport(self.time_step)
        
        return fidelity, errors, stabilizer, self.transport_progress
    
    def reset_system(self):
        """重置系统状态"""
        self.transport_progress = 0.0
        self.quantum_state = self.create_initial_state()
        self.rg_engine.boundary_field = np.abs(self.quantum_state)
        self.gravity_engine.generate_spin_network()
        self.string_engine.initialize_string()
        self.qec = QuantumErrorCorrection(code_size=3)
        self.particle_transport = ParticleTransport()
        self.particle_transport.add_particle("particle1", (10, 10), (110, 110))
        self.particle_transport.add_particle("particle2", (110, 10), (10, 110))
        logger.info("系统已重置")

# ========================
# PyQt5 图形用户界面
# ========================

class MplCanvas(FigureCanvas):
    """Matplotlib 画布组件"""
    def __init__(self, parent=None, width=5, height=4, dpi=100, projection=None):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.projection = projection
        if projection == '3d':
            self.axes = self.fig.add_subplot(111, projection='3d')
        else:
            self.axes = self.fig.add_subplot(111)
        super().__init__(self.fig)
        self.setParent(parent)
        
        # 初始化所有绘图对象为None
        self.colorbar = None
        self.surf = None
        self.line = None
        self.path_lines = []
        self.particle_markers = []
        
    def plot_2d(self, data, title="", cmap='viridis'):
        """绘制2D图像"""
        self.axes.clear()
        im = self.axes.imshow(data, cmap=cmap, origin='lower')
        self.axes.set_title(title)
        
        # 安全移除旧的颜色条
        if self.colorbar is not None:
            try:
                self.colorbar.remove()
            except:
                pass
            self.colorbar = None
        
        # 创建新的颜色条
        self.colorbar = self.fig.colorbar(im, ax=self.axes)
        self.draw()
        
    def plot_3d(self, data, title="", cmap='viridis', elevation=30, azimuth=45):
        """绘制3D图像"""
        self.axes.clear()
        
        # 安全移除旧的曲面图
        if self.surf is not None:
            try:
                self.surf.remove()
            except:
                pass
            self.surf = None
        
        # 安全移除旧的颜色条
        if self.colorbar is not None:
            try:
                self.colorbar.remove()
            except:
                pass
            self.colorbar = None
        
        if data.ndim == 2:
            x, y = np.meshgrid(np.arange(data.shape[0]), np.arange(data.shape[1]))
            
            # 创建新的曲面图
            self.surf = self.axes.plot_surface(x, y, data, cmap=cmap, alpha=0.8)
            
            # 创建新的颜色条
            self.colorbar = self.fig.colorbar(self.surf, ax=self.axes)
        
        self.axes.set_title(title)
        self.axes.view_init(elev=elevation, azim=azimuth)
        self.draw()
        
    def plot_curve(self, x, y, title="", xlabel="", ylabel="", style='-'):
        """绘制曲线图"""
        self.axes.clear()
        
        # 安全移除旧的曲线
        if self.line is not None:
            try:
                self.line.remove()
            except:
                pass
            self.line = None
        
        # 创建新的曲线
        self.line = self.axes.plot(x, y, style)[0]
        self.axes.set_title(title)
        self.axes.set_xlabel(xlabel)
        self.axes.set_ylabel(ylabel)
        self.axes.grid(True)
        self.draw()
        
    def plot_3d_path(self, paths, title=""):
        """绘制3D路径"""
        # 清除当前画布
        self.fig.clf()
        
        # 重新创建3D坐标轴
        self.axes = self.fig.add_subplot(111, projection='3d')
        
        # 绘制路径
        self.path_lines = []
        for path in paths:
            x, y, z = path
            line = self.axes.plot(x, y, z, 'b-', linewidth=2)[0]  # 增加线宽
            self.path_lines.append(line)
        
        # 设置固定坐标轴范围
        self.axes.set_xlim(0, 128)
        self.axes.set_ylim(0, 128)
        self.axes.set_zlim(-1.5, 1.5)  # 根据高度函数范围设置
        
        # 固定视角
        self.axes.view_init(elev=30, azim=45)
        
        self.axes.set_title(title)
        self.axes.set_xlabel("X")
        self.axes.set_ylabel("Y")
        self.axes.set_zlabel("Z")
        self.draw()
        
    def plot_particles(self, positions, title=""):
        """绘制粒子位置"""
        self.axes.clear()
        
        # 安全移除旧的粒子标记
        for marker in self.particle_markers:
            try:
                marker.remove()
            except:
                pass
        self.particle_markers = []
        
        for pos in positions:
            x, y = pos
            marker = self.axes.plot(x, y, 'ro', markersize=8)[0]
            self.particle_markers.append(marker)
        
        self.axes.set_title(title)
        self.axes.set_xlim(0, 128)
        self.axes.set_ylim(0, 128)
        self.axes.grid(True)
        self.draw()
        
    def plot_stabilizers(self, stabilizers, title=""):
        """绘制稳定子测量"""
        self.axes.clear()
        
        if not stabilizers:
            self.axes.text(0.5, 0.5, "无稳定子数据", ha='center', va='center')
            self.draw()
            return
            
        # 提取三个稳定子分量
        s1 = [s[0] for s in stabilizers]
        s2 = [s[1] for s in stabilizers]
        s3 = [s[2] for s in stabilizers]
        x = np.arange(len(stabilizers))
        
        # 绘制三条曲线
        self.axes.plot(x, s1, 'r-', label='稳定子X')
        self.axes.plot(x, s2, 'g-', label='稳定子Y')
        self.axes.plot(x, s3, 'b-', label='稳定子Z')
        
        self.axes.set_title(title)
        self.axes.set_xlabel("时间步")
        self.axes.set_ylabel("测量值")
        self.axes.legend()
        self.axes.grid(True)
        self.draw()

class EngineControlPanel(QGroupBox):
    """引擎控制面板"""
    def __init__(self, engine, parent=None):
        super().__init__("控制面板", parent)
        self.engine = engine
        
        # 创建控件
        self.start_btn = QPushButton(QIcon("icons/play.png"), "开始仿真")
        self.pause_btn = QPushButton(QIcon("icons/pause.png"), "暂停仿真")
        self.reset_btn = QPushButton(QIcon("icons/reset.png"), "重置系统")
        
        self.time_step_slider = QSlider(Qt.Horizontal)
        self.time_step_slider.setRange(1, 100)
        self.time_step_slider.setValue(10)
        self.time_step_label = QLabel("时间步长: 0.1")
        
        self.tension_spin = QDoubleSpinBox()
        self.tension_spin.setRange(0.1, 5.0)
        self.tension_spin.setValue(1.0)
        self.tension_spin.setSingleStep(0.1)
        self.tension_spin.setToolTip("弦张力参数")
        
        self.noise_spin = QDoubleSpinBox()
        self.noise_spin.setRange(0.0, 0.5)
        self.noise_spin.setValue(0.05)
        self.noise_spin.setSingleStep(0.01)
        self.noise_spin.setToolTip("量子噪声水平")
        
        self.wormhole_spin = QDoubleSpinBox()
        self.wormhole_spin.setRange(0.1, 2.0)
        self.wormhole_spin.setValue(0.5)
        self.wormhole_spin.setSingleStep(0.1)
        self.wormhole_spin.setToolTip("虫洞半径比例")
        
        self.planck_spin = QDoubleSpinBox()
        self.planck_spin.setRange(0.01, 5.0)
        self.planck_spin.setValue(1.0)
        self.planck_spin.setSingleStep(0.01)
        self.planck_spin.setToolTip("普朗克尺度")
        
        self.quantum_spin = QDoubleSpinBox()
        self.quantum_spin.setRange(0.001, 0.1)
        self.quantum_spin.setValue(0.01)
        self.quantum_spin.setSingleStep(0.001)
        self.quantum_spin.setToolTip("量子涨落幅度")
        
        self.visualization_combo = QComboBox()
        self.visualization_combo.addItems([
            "3D 时空", "弦振动", "全息映射", 
            "量子纠错", "粒子传输", "稳定子测量"
        ])
        
        # 布局
        layout = QGridLayout()
        layout.addWidget(self.start_btn, 0, 0)
        layout.addWidget(self.pause_btn, 0, 1)
        layout.addWidget(self.reset_btn, 0, 2)
        
        layout.addWidget(QLabel("时间步长:"), 1, 0)
        layout.addWidget(self.time_step_slider, 1, 1, 1, 2)
        layout.addWidget(self.time_step_label, 2, 0, 1, 3)
        
        layout.addWidget(QLabel("弦张力:"), 3, 0)
        layout.addWidget(self.tension_spin, 3, 1, 1, 2)
        
        layout.addWidget(QLabel("量子噪声:"), 4, 0)
        layout.addWidget(self.noise_spin, 4, 1, 1, 2)
        
        layout.addWidget(QLabel("量子涨落:"), 5, 0)
        layout.addWidget(self.quantum_spin, 5, 1, 1, 2)
        
        layout.addWidget(QLabel("虫洞半径:"), 6, 0)
        layout.addWidget(self.wormhole_spin, 6, 1, 1, 2)
        
        layout.addWidget(QLabel("普朗克尺度:"), 7, 0)
        layout.addWidget(self.planck_spin, 7, 1, 1, 2)
        
        layout.addWidget(QLabel("可视化模式:"), 8, 0)
        layout.addWidget(self.visualization_combo, 8, 1, 1, 2)
        
        self.setLayout(layout)
        
        # 连接信号
        self.start_btn.clicked.connect(self.start_simulation)
        self.pause_btn.clicked.connect(self.pause_simulation)
        self.reset_btn.clicked.connect(self.reset_simulation)
        self.time_step_slider.valueChanged.connect(self.update_time_step)
        self.tension_spin.valueChanged.connect(self.update_tension)
        self.noise_spin.valueChanged.connect(self.update_noise)
        self.quantum_spin.valueChanged.connect(self.update_quantum)
        self.wormhole_spin.valueChanged.connect(self.update_wormhole)
        self.planck_spin.valueChanged.connect(self.update_planck_scale)
        
    def start_simulation(self):
        self.engine.simulation_running = True
        logger.info("仿真已启动")
        
    def pause_simulation(self):
        self.engine.simulation_running = False
        logger.info("仿真已暂停")
        
    def reset_simulation(self):
        self.engine.reset_system()
        
    def update_time_step(self, value):
        self.engine.time_step = value / 100.0
        self.time_step_label.setText(f"时间步长: {self.engine.time_step:.2f}")
        
    def update_tension(self, value):
        self.engine.string_engine.T = value
        
    def update_noise(self, value):
        self.engine.qec.error_probability = value
        
    def update_quantum(self, value):
        self.engine.string_engine.quantum_fluctuation_scale = value
        
    def update_wormhole(self, value):
        self.engine.gravity_engine.wormhole_radius = value
        self.engine.gravity_engine.update_metric()
        
    def update_planck_scale(self, value):
        self.engine.gravity_engine.planck_scale = value
        self.engine.gravity_engine.update_metric()

class SystemMonitorPanel(QGroupBox):
    """系统监控面板"""
    def __init__(self, engine, parent=None):
        super().__init__("系统监控", parent)
        self.engine = engine
        
        # 创建控件
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        
        self.fidelity_label = QLabel("量子保真度: 100.00%")
        self.errors_label = QLabel("量子错误数: 0")
        self.transport_label = QLabel("传输进度: 0.00%")
        self.energy_label = QLabel("弦能量: 0.00")
        
        # 布局
        layout = QVBoxLayout()
        layout.addWidget(QLabel("传输进度:"))
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.fidelity_label)
        layout.addWidget(self.errors_label)
        layout.addWidget(self.transport_label)
        layout.addWidget(self.energy_label)
        
        self.setLayout(layout)
        
    def update_monitor(self, fidelity, errors, transport_progress, energy):
        """更新监控数据"""
        self.progress_bar.setValue(int(transport_progress * 100))
        self.fidelity_label.setText(f"量子保真度: {fidelity*100:.2f}%")
        self.errors_label.setText(f"量子错误数: {errors}")
        self.transport_label.setText(f"传输进度: {transport_progress*100:.2f}%")
        self.energy_label.setText(f"弦能量: {energy:.4f}")

class ParticleControlPanel(QGroupBox):
    """粒子控制面板"""
    def __init__(self, engine, parent=None):
        super().__init__("粒子控制", parent)
        self.engine = engine
        self.show_trajectory = True

        # 创建控件
        self.add_btn = QPushButton(QIcon("icons/add.png"), "添加粒子")
        self.remove_btn = QPushButton(QIcon("icons/remove.png"), "移除粒子")
        self.trajectory_check = QCheckBox("显示轨迹")
        self.trajectory_check.setChecked(True)
        
        self.particle_list = QTreeWidget()
        self.particle_list.setHeaderLabels(["粒子ID", "起点", "终点", "进度"])
        self.particle_list.setColumnWidth(0, 100)
        self.particle_list.setColumnWidth(1, 100)
        self.particle_list.setColumnWidth(2, 100)
        self.particle_list.setColumnWidth(3, 80)
        
        # 布局
        layout = QVBoxLayout()
        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.remove_btn)
        
        layout.addLayout(btn_layout)
        layout.addWidget(self.trajectory_check)
        layout.addWidget(self.particle_list)
        
        self.setLayout(layout)
        
        # 连接信号
        self.add_btn.clicked.connect(self.add_particle)
        self.remove_btn.clicked.connect(self.remove_particle)
        self.trajectory_check.stateChanged.connect(self.toggle_trajectory)
        
    def add_particle(self):
        """添加新粒子"""
        particle_id = f"particle{len(self.engine.particle_transport.particles) + 1}"
        start_pos = (np.random.randint(10, 50), np.random.randint(10, 50))
        end_pos = (np.random.randint(60, 110), np.random.randint(60, 110))
        
        self.engine.particle_transport.add_particle(particle_id, start_pos, end_pos)
        self.update_particle_list()
        logger.info(f"添加粒子: {particle_id}")
        
    def remove_particle(self):
        """移除选中粒子"""
        selected = self.particle_list.selectedItems()
        if not selected:
            return
            
        particle_id = selected[0].text(0)
        if particle_id in self.engine.particle_transport.particles:
            self.engine.particle_transport.particles.remove(particle_id)
            del self.engine.particle_transport.transport_paths[particle_id]
            del self.engine.particle_transport.transport_progress[particle_id]
            self.update_particle_list()
            logger.info(f"移除粒子: {particle_id}")
        
    def update_particle_list(self):
        """更新粒子列表"""
        self.particle_list.clear()
        for particle_id in self.engine.particle_transport.particles:
            start_pos = self.engine.particle_transport.transport_paths[particle_id][0]
            end_pos = self.engine.particle_transport.transport_paths[particle_id][1]
            progress = self.engine.particle_transport.transport_progress[particle_id]
            
            item = QTreeWidgetItem([
                particle_id,
                f"({start_pos[0]:.1f}, {start_pos[1]:.1f})",
                f"({end_pos[0]:.1f}, {end_pos[1]:.1f})",
                f"{progress*100:.1f}%"
            ])
            self.particle_list.addTopLevelItem(item)
            
    def toggle_trajectory(self, state):
        """切换轨迹显示"""
        # 在实际应用中，这里可以控制是否绘制轨迹
        self.show_trajectory = state == Qt.Checked

class SimulationThread(QThread):
    """仿真线程，用于在后台运行仿真"""
    update_signal = pyqtSignal(float, int, list, float, float)
    
    def __init__(self, engine):
        super().__init__()
        self.engine = engine
        self.running = True
        
    def run(self):
        """运行仿真循环"""
        while self.running:
            if self.engine.simulation_running:
                fidelity, errors, stabilizer, transport_progress = self.engine.evolve_system()
                energy = self.engine.string_engine.total_energy()
                self.update_signal.emit(fidelity, errors, stabilizer, transport_progress, energy)
            self.msleep(50)  # 50ms更新一次
            
    def stop(self):
        """停止仿真线程"""
        self.running = False
        self.wait()

class MainWindow(QMainWindow):
    """主窗口"""
    def __init__(self):
        super().__init__()
        
        # 创建物理引擎
        self.engine = VacuumEmergenceEngine()
        
        # 设置窗口
        self.setWindowTitle("终极真空演生引擎仿真系统")
        self.setGeometry(100, 100, 1600, 1000)
        
        # 创建菜单
        self.create_menus()
        
        # 创建工具栏
        self.create_toolbar()
        
        # 创建中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QHBoxLayout(central_widget)
        
        # 左侧控制面板
        left_dock = QDockWidget("控制面板", self)
        left_dock.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)
        left_dock.setMinimumWidth(300)
        
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        # 添加控制面板
        self.control_panel = EngineControlPanel(self.engine)
        left_layout.addWidget(self.control_panel)
        
        # 添加系统监控
        self.monitor_panel = SystemMonitorPanel(self.engine)
        left_layout.addWidget(self.monitor_panel)
        
        # 添加粒子控制
        self.particle_panel = ParticleControlPanel(self.engine)
        left_layout.addWidget(self.particle_panel)
        
        left_dock.setWidget(left_widget)
        self.addDockWidget(Qt.LeftDockWidgetArea, left_dock)
        
        # 右侧可视化区域
        splitter = QSplitter(Qt.Vertical)
        
        # 主可视化画布
        self.main_canvas = MplCanvas(width=12, height=8, dpi=100, projection='3d')
        self.main_toolbar = NavigationToolbar(self.main_canvas, self)
        
        # 辅助可视化画布
        self.aux_canvas = MplCanvas(width=12, height=4, dpi=100)
        
        # 创建选项卡
        self.viz_tabs = QTabWidget()
        self.viz_tabs.addTab(self.main_canvas, "主视图")
        self.viz_tabs.addTab(self.aux_canvas, "辅助视图")
        
        # 添加工具栏到主视图
        main_viz_widget = QWidget()
        main_viz_layout = QVBoxLayout(main_viz_widget)
        main_viz_layout.addWidget(self.main_toolbar)
        main_viz_layout.addWidget(self.viz_tabs)
        
        splitter.addWidget(main_viz_widget)
        self.setCentralWidget(splitter)
        
        # 状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("系统已就绪")
        
        # 创建仿真线程
        self.simulation_thread = SimulationThread(self.engine)
        self.simulation_thread.update_signal.connect(self.update_simulation)
        self.simulation_thread.start()
        
        # 初始可视化
        self.update_visualization()
        
        # 记录启动
        logger.info("真空演生引擎仿真系统已启动")
    
    def create_menus(self):
        """创建菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu("文件")
        
        new_action = QAction(QIcon("icons/new.png"), "新建仿真", self)
        new_action.triggered.connect(self.new_simulation)
        file_menu.addAction(new_action)
        
        save_action = QAction(QIcon("icons/save.png"), "保存状态", self)
        save_action.triggered.connect(self.save_state)
        file_menu.addAction(save_action)
        
        load_action = QAction(QIcon("icons/load.png"), "加载状态", self)
        load_action.triggered.connect(self.load_state)
        file_menu.addAction(load_action)
        
        export_action = QAction(QIcon("icons/export.png"), "导出数据", self)
        export_action.triggered.connect(self.export_data)
        file_menu.addAction(export_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction(QIcon("icons/exit.png"), "退出", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 视图菜单
        view_menu = menubar.addMenu("视图")
        
        fullscreen_action = QAction("全屏", self)
        fullscreen_action.triggered.connect(self.toggle_fullscreen)
        view_menu.addAction(fullscreen_action)
        
        # 工具菜单
        tools_menu = menubar.addMenu("工具")
        
        generate_spin_action = QAction("生成自旋网络", self)
        generate_spin_action.triggered.connect(self.generate_spin_network)
        tools_menu.addAction(generate_spin_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu("帮助")
        
        docs_action = QAction("文档", self)
        docs_action.triggered.connect(self.show_docs)
        help_menu.addAction(docs_action)
        
        about_action = QAction(QIcon("icons/about.png"), "关于", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def create_toolbar(self):
        """创建工具栏"""
        toolbar = QToolBar("主工具栏")
        toolbar.setIconSize(QSize(32, 32))
        self.addToolBar(Qt.TopToolBarArea, toolbar)
        
        play_action = QAction(QIcon("icons/play.png"), "开始仿真", self)
        play_action.triggered.connect(self.engine_start)
        toolbar.addAction(play_action)
        
        pause_action = QAction(QIcon("icons/pause.png"), "暂停仿真", self)
        pause_action.triggered.connect(self.engine_pause)
        toolbar.addAction(pause_action)
        
        reset_action = QAction(QIcon("icons/reset.png"), "重置系统", self)
        reset_action.triggered.connect(self.engine_reset)
        toolbar.addAction(reset_action)
        
        toolbar.addSeparator()
        
        save_action = QAction(QIcon("icons/save.png"), "保存状态", self)
        save_action.triggered.connect(self.save_state)
        toolbar.addAction(save_action)
        
        load_action = QAction(QIcon("icons/load.png"), "加载状态", self)
        load_action.triggered.connect(self.load_state)
        toolbar.addAction(load_action)
        
        toolbar.addSeparator()
        
        spin_action = QAction(QIcon("icons/spin.png"), "生成自旋网络", self)
        spin_action.triggered.connect(self.generate_spin_network)
        toolbar.addAction(spin_action)
    
    def generate_spin_network(self):
        """生成新的自旋网络"""
        self.engine.gravity_engine.generate_spin_network()
        self.status_bar.showMessage("已生成新的自旋网络")
        self.update_visualization()
        logger.info("生成新的自旋网络")
    
    def engine_start(self):
        self.engine.simulation_running = True
        self.status_bar.showMessage("仿真已启动")
        logger.info("仿真已启动")
    
    def engine_pause(self):
        self.engine.simulation_running = False
        self.status_bar.showMessage("仿真已暂停")
        logger.info("仿真已暂停")
    
    def engine_reset(self):
        self.engine.reset_system()
        self.status_bar.showMessage("系统已重置")
        self.update_visualization()
        logger.info("系统已重置")
    
    def new_simulation(self):
        self.engine = VacuumEmergenceEngine()
        self.control_panel.engine = self.engine
        self.monitor_panel.engine = self.engine
        self.particle_panel.engine = self.engine
        self.status_bar.showMessage("新建仿真已创建")
        self.update_visualization()
        logger.info("新建仿真")
    
    def save_state(self):
        """保存系统状态（简化版）"""
        file_name, _ = QFileDialog.getSaveFileName(self, "保存状态", "", "JSON Files (*.json)")
        if file_name:
            # 实际应用中需要保存所有引擎状态
            state = {
                "transport_progress": self.engine.transport_progress
            }
            with open(file_name, 'w') as f:
                json.dump(state, f)
            self.status_bar.showMessage(f"状态已保存到 {file_name}")
            logger.info(f"状态保存到 {file_name}")
    
    def load_state(self):
        """加载系统状态（简化版）"""
        file_name, _ = QFileDialog.getOpenFileName(self, "加载状态", "", "JSON Files (*.json)")
        if file_name:
            try:
                with open(file_name, 'r') as f:
                    state = json.load(f)
                self.engine.transport_progress = state["transport_progress"]
                self.status_bar.showMessage(f"状态已从 {file_name} 加载")
                self.update_visualization()
                logger.info(f"状态从 {file_name} 加载")
            except Exception as e:
                QMessageBox.warning(self, "加载错误", f"无法加载状态: {str(e)}")
                logger.error(f"加载状态错误: {str(e)}")
    
    def export_data(self):
        """导出仿真数据"""
        file_name, _ = QFileDialog.getSaveFileName(self, "导出数据", "", "NPZ Files (*.npz)")
        if file_name:
            try:
                # 收集数据
                curvature = self.engine.gravity_engine.curvature
                string_pos = self.engine.string_engine.get_string_positions()
                boundary = self.engine.rg_engine.boundary_field
                
                # 保存数据
                np.savez(
                    file_name,
                    curvature=curvature,
                    string_pos=string_pos,
                    boundary_field=boundary,
                    transport_progress=self.engine.transport_progress
                )
                self.status_bar.showMessage(f"数据已导出到 {file_name}")
                logger.info(f"数据导出到 {file_name}")
            except Exception as e:
                QMessageBox.warning(self, "导出错误", f"无法导出数据: {str(e)}")
                logger.error(f"导出数据错误: {str(e)}")
    
    def toggle_fullscreen(self):
        """切换全屏模式"""
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()
    
    def show_docs(self):
        """显示文档"""
        doc_text = """
        <h2>终极真空演生引擎仿真系统文档</h2>
        <p>本系统模拟了一个基于量子引力、弦理论和全息原理的先进真空演生引擎。</p>
        
        <h3>主要功能：</h3>
        <ul>
            <li>量子引力引擎：模拟时空曲率和虫洞结构</li>
            <li>弦理论引擎：模拟基本弦的振动和量子涨落</li>
            <li>全息RG引擎：实现AdS/CFT对偶映射</li>
            <li>量子纠错：确保量子信息传输的稳定性</li>
            <li>粒子传输：通过虫洞传输粒子</li>
        </ul>
        
        <h3>控制参数：</h3>
        <ul>
            <li>弦张力：控制弦振动的强度</li>
            <li>量子噪声：控制量子纠错系统的噪声水平</li>
            <li>虫洞半径：控制虫洞喉部的大小</li>
            <li>普朗克尺度：控制量子引力效应的强度</li>
        </ul>
        """
        msg_box = QMessageBox()
        msg_box.setWindowTitle("系统文档")
        msg_box.setTextFormat(Qt.RichText)
        msg_box.setText(doc_text)
        msg_box.exec_()
    
    def show_about(self):
        """显示关于对话框"""
        about_text = """
        <h2>终极真空演生引擎仿真系统</h2>
        <p>版本: 3.0</p>
        <p>本系统集成了量子引力、弦理论、全息原理和量子信息理论，</p>
        <p>实现了真空演生引擎的完整仿真。</p>
        <p>功能包括：</p>
        <ul>
            <li>量子引力时空曲率可视化</li>
            <li>弦振动模式分析</li>
            <li>全息边界-体映射</li>
            <li>量子纠错监控</li>
            <li>虫洞粒子传输</li>
        </ul>
        <p>&copy; 2023-2024 量子前沿研究所</p>
        """
        QMessageBox.about(self, "关于", about_text)
    
    def update_simulation(self, fidelity, errors, stabilizer, transport_progress, energy):
        """更新仿真状态"""
        # 更新监控面板
        self.monitor_panel.update_monitor(fidelity, errors, transport_progress, energy)
        
        # 更新粒子面板
        self.particle_panel.update_particle_list()
        
        # 更新状态栏
        self.status_bar.showMessage(
            f"传输进度: {transport_progress*100:.1f}% | "
            f"量子保真度: {fidelity*100:.2f}% | "
            f"量子错误数: {errors} | "
            f"弦能量: {energy:.4f}"
        )
        
        # 更新可视化
        self.update_visualization()
    
    def update_visualization(self):
        """更新可视化"""
        viz_mode = self.control_panel.visualization_combo.currentText()
        
        if viz_mode == "3D 时空":
            # 主视图：3D时空曲率
            curvature = self.engine.gravity_engine.curvature
            self.main_canvas.plot_3d(curvature, "量子引力时空曲率", cmap='viridis')
            
            # 辅助视图：虫洞喉部
            throat = self.engine.gravity_engine.get_wormhole_throat()
            g_tt = throat[:, :, 0, 0]
            self.aux_canvas.plot_2d(g_tt, "虫洞喉部 (g_tt)", cmap='plasma')
            
        elif viz_mode == "弦振动":
            # 主视图：弦振动
            pos = self.engine.string_engine.get_string_positions()
            paths = [(pos[0], pos[1], pos[2])]
            self.main_canvas.plot_3d_path(paths, "弦振动模式")
            
            # 辅助视图：能量历史
            energy_history = self.engine.string_engine.get_energy_history()
            if energy_history:
                x = np.arange(len(energy_history))
                self.aux_canvas.plot_curve(x, energy_history, "弦能量历史", "时间步", "能量", style='g-')
            else:
                self.aux_canvas.axes.clear()
                self.aux_canvas.axes.text(0.5, 0.5, "无能量历史数据", ha='center', va='center')
                self.aux_canvas.draw()
                
        elif viz_mode == "全息映射":
            # 主视图：边界场
            boundary = self.engine.rg_engine.boundary_field
            self.main_canvas.plot_2d(boundary, "CFT边界场", cmap='inferno')
            
            # 辅助视图：体场历史动画
            if self.engine.rg_engine.history:
                # 循环显示历史帧
                frame_index = int(time.time() * 2) % len(self.engine.rg_engine.history)
                bulk = self.engine.rg_engine.get_history_frame(frame_index)
                self.aux_canvas.plot_2d(bulk, f"AdS体场 (帧 {frame_index+1}/{len(self.engine.rg_engine.history)})", cmap='plasma')
            
        elif viz_mode == "量子纠错":
            # 主视图：量子态概率
            progress = self.engine.transport_progress
            if progress < 0.3:
                state = np.abs(self.engine.quantum_state) * (1 - progress/0.3)
            elif progress < 0.7:
                state = self.engine.rg_engine.bulk_field
            else:
                state = np.roll(np.abs(self.engine.quantum_state), shift=50, axis=1) * ((progress-0.7)/0.3)
            
            self.main_canvas.plot_2d(state, f"传输状态: {progress*100:.1f}%", cmap='viridis')
            
            # 辅助视图：纠错历史
            history = self.engine.qec.correction_history
            if history:
                x = np.arange(len(history))
                self.aux_canvas.plot_curve(x, history, "量子态保真度历史", "时间步", "保真度", style='g-')
            else:
                self.aux_canvas.axes.clear()
                self.aux_canvas.axes.text(0.5, 0.5, "无纠错历史数据", ha='center', va='center')
                self.aux_canvas.draw()
                
        elif viz_mode == "粒子传输":
            # 主视图：粒子位置
            positions = []
            particle_ids = []
            for particle_id in self.engine.particle_transport.particles:
                pos = self.engine.particle_transport.get_particle_position(particle_id)
                if pos:
                    positions.append(pos)
                    particle_ids.append(particle_id)
            
            self.main_canvas.plot_particles(positions, "粒子传输位置")
            
            # 辅助视图：测地线 - 只绘制当前路径
            if positions:
                # 只使用第一个粒子的位置
                start_pos = positions[0]
                end_pos = (128 - start_pos[0], 128 - start_pos[1])
                x, y, z = self.engine.gravity_engine.calculate_geodesic_3d(start_pos, end_pos)
                
                # 绘制路径
                self.aux_canvas.plot_3d_path([(x, y, z)], "测地线路径")
                
                # 如果启用了轨迹显示，绘制粒子轨迹
                if self.particle_panel.show_trajectory and particle_ids:
                    trajectories = []
                    for particle_id in particle_ids:
                        history = self.engine.particle_transport.get_particle_history(particle_id)
                        if history:
                            # 提取轨迹坐标
                            traj_x = [p[0] for p in history]
                            traj_y = [p[1] for p in history]
                            # 为轨迹添加高度（基于曲率）
                            traj_z = []
                            for i in range(len(traj_x)):
                                ix, iy = int(traj_x[i]), int(traj_y[i])
                                if 0 <= ix < self.engine.gravity_engine.size and 0 <= iy < self.engine.gravity_engine.size:
                                    traj_z.append(self.engine.gravity_engine.curvature[ix, iy] * 10)
                                else:
                                    traj_z.append(0)
                            trajectories.append((traj_x, traj_y, traj_z))
                    
                    # 在主视图上绘制轨迹
                    if trajectories:
                        self.main_canvas.axes.clear()
                        for traj in trajectories:
                            x, y, z = traj
                            self.main_canvas.axes.plot(x, y, z, 'g-', alpha=0.5, linewidth=1)
                        
                        # 重新绘制当前粒子位置
                        for pos in positions:
                            x, y = pos
                            self.main_canvas.axes.plot([x], [y], [0], 'ro', markersize=8)
                        
                        self.main_canvas.axes.set_title("粒子传输位置与轨迹")
                        self.main_canvas.axes.set_xlim(0, 128)
                        self.main_canvas.axes.set_ylim(0, 128)
                        self.main_canvas.axes.set_zlim(-1.5, 1.5)
                        self.main_canvas.axes.view_init(elev=30, azim=45)
                        self.main_canvas.draw()
            else:
                self.aux_canvas.axes.clear()
                self.aux_canvas.axes.text(0.5, 0.5, "没有活动的粒子", ha='center', va='center')
                self.aux_canvas.draw()
    
    def closeEvent(self, event):
        """关闭窗口事件"""
        # 停止仿真线程
        self.simulation_thread.stop()
        
        # 确认关闭
        reply = QMessageBox.question(
            self, '确认退出',
            '确定要退出系统吗？',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            logger.info("系统已关闭")
            event.accept()
        else:
            event.ignore()

# ========================
# 启动应用
# ========================

if __name__ == "__main__":
    # 创建必要的图标目录
    os.makedirs("icons", exist_ok=True)
    
    app = QApplication(sys.argv)
    
    # 设置应用样式
    app.setStyle("Fusion")
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(53, 53, 53))
    palette.setColor(QPalette.WindowText, Qt.white)
    palette.setColor(QPalette.Base, QColor(25, 25, 25))
    palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
    palette.setColor(QPalette.ToolTipBase, Qt.white)
    palette.setColor(QPalette.ToolTipText, Qt.white)
    palette.setColor(QPalette.Text, Qt.white)
    palette.setColor(QPalette.Button, QColor(53, 53, 53))
    palette.setColor(QPalette.ButtonText, Qt.white)
    palette.setColor(QPalette.BrightText, Qt.red)
    palette.setColor(QPalette.Highlight, QColor(142, 45, 197).lighter())
    palette.setColor(QPalette.HighlightedText, Qt.black)
    app.setPalette(palette)
    
    # 设置应用字体
    font = QFont("Microsoft YaHei", 9)
    app.setFont(font)
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())