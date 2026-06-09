import sys
import numpy as np
import matplotlib
matplotlib.rc("font", family='Microsoft YaHei')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from matplotlib.colors import LinearSegmentedColormap
import scipy.ndimage as ndimage
from scipy import integrate
import seaborn as sns
from tqdm import tqdm
import warnings
warnings.filterwarnings('ignore')

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QGridLayout, QGroupBox, QLabel, 
                             QSlider, QComboBox, QPushButton, QCheckBox,
                             QDoubleSpinBox, QSpinBox, QTabWidget, QTextEdit,
                             QSplitter, QFrame, QProgressBar, QMessageBox)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QPalette, QColor

class QuantumConsciousnessField:
    """增强版量子意识场模拟器"""
    
    def __init__(self, grid_size=256, dt=0.1, hbar=1.0, mass=1.0):
        self.grid_size = grid_size
        self.dt = dt
        self.hbar = hbar
        self.mass = mass
        
        # 空间网格
        self.x = np.linspace(-10, 10, grid_size)
        self.y = np.linspace(-10, 10, grid_size)
        self.X, self.Y = np.meshgrid(self.x, self.y)
        
        # 初始化量子场
        self.psi_real = np.random.normal(0, 0.1, (grid_size, grid_size))
        self.psi_imag = np.random.normal(0, 0.1, (grid_size, grid_size))
        
        # 宇宙势场
        self.potential = self._create_cosmic_potential()
        
        # 意识源管理
        self.consciousness_sources = []
        self.source_id_counter = 0
        
        # 历史记录
        self.energy_history = []
        self.entropy_history = []
        self.coherence_history = []
        self.resonance_history = []
        self.balance_history = []
        
        # 动量空间
        self.kx = 2 * np.pi * np.fft.fftfreq(grid_size, self.x[1]-self.x[0])
        self.ky = 2 * np.pi * np.fft.fftfreq(grid_size, self.y[1]-self.y[0])
        self.KX, self.KY = np.meshgrid(self.kx, self.ky)
        
        # 模拟时间
        self.simulation_time = 0
        
        # 高级参数
        self.noise_level = 0.01
        self.diffusion_coeff = 0.1
        self.nonlinearity = 0.05
        
    def _create_cosmic_potential(self):
        """创建复杂的宇宙势场"""
        # 多尺度势场结构
        potential = np.zeros((self.grid_size, self.grid_size))
        
        # 1. 中心吸引势
        r_center = np.sqrt(self.X**2 + self.Y**2)
        potential += -8 * np.exp(-0.3 * r_center**2)
        
        # 2. 多极势场
        for i in range(4):
            angle = i * np.pi / 2
            x_rot = self.X * np.cos(angle) - self.Y * np.sin(angle)
            y_rot = self.X * np.sin(angle) + self.Y * np.cos(angle)
            potential += 3 * np.exp(-0.5 * (x_rot**2 + (y_rot-4)**2))
        
        # 3. 周期性结构
        potential += 1.5 * (np.sin(1.5*self.X) * np.sin(1.5*self.Y))
        
        # 4. 随机扰动
        potential += 0.5 * np.random.normal(0, 0.3, (self.grid_size, self.grid_size))
        
        return potential
    
    def add_consciousness_source(self, x=0, y=0, amplitude=1.0, frequency=0.5, 
                               focus=0.8, intention=1.0, source_type="普通"):
        """添加意识源"""
        source = {
            'id': self.source_id_counter,
            'x': x, 'y': y,
            'amplitude': amplitude,
            'frequency': frequency,
            'focus': focus,
            'intention': intention,
            'phase': 0.0,
            'type': source_type,
            'active': True
        }
        self.consciousness_sources.append(source)
        self.source_id_counter += 1
        return source['id']
    
    def remove_consciousness_source(self, source_id):
        """移除意识源"""
        self.consciousness_sources = [s for s in self.consciousness_sources if s['id'] != source_id]
    
    def update_consciousness_source(self, source_id, **kwargs):
        """更新意识源参数"""
        for source in self.consciousness_sources:
            if source['id'] == source_id:
                for key, value in kwargs.items():
                    if key in source:
                        source[key] = value
                break
    
    def get_consciousness_potential(self, t):
        """计算意识势场"""
        consciousness_potential = np.zeros((self.grid_size, self.grid_size))
        
        for source in self.consciousness_sources:
            if not source['active']:
                continue
                
            dx = self.X - source['x']
            dy = self.Y - source['y']
            r2 = dx**2 + dy**2
            
            # 根据专注度调整影响范围
            sigma = 1.5 / (source['focus'] + 0.1)
            
            # 不同类型的意识源有不同的影响模式
            if source['type'] == "专注":
                # 高度聚焦的影响
                influence_shape = np.exp(-r2 / (2 * (sigma/2)**2))
            elif source['type'] == "扩散":
                # 广泛影响
                influence_shape = np.exp(-r2 / (2 * (sigma*2)**2))
            elif source['type'] == "振荡":
                # 振荡模式
                radial_freq = np.sqrt(r2) * source['frequency']
                influence_shape = np.exp(-r2 / (2 * sigma**2)) * np.cos(radial_freq)
            else:  # 普通
                influence_shape = np.exp(-r2 / (2 * sigma**2))
            
            # 时间振荡
            oscillation = source['amplitude'] * source['intention'] * \
                         np.cos(source['frequency'] * t + source['phase'])
            
            consciousness_potential += oscillation * influence_shape
            
            # 更新相位
            source['phase'] += 0.1 * source['frequency']
        
        return consciousness_potential
    
    def compute_advanced_metrics(self):
        """计算高级物理指标"""
        psi = self.psi_real + 1j * self.psi_imag
        
        # 1. 能量计算
        psi_k = np.fft.fft2(psi)
        kinetic_energy = np.sum(np.abs(psi_k)**2 * (self.KX**2 + self.KY**2)) / (2 * self.mass)
        total_potential = self.potential + self.get_consciousness_potential(self.simulation_time)
        potential_energy = np.sum(total_potential * (self.psi_real**2 + self.psi_imag**2))
        total_energy = kinetic_energy + potential_energy
        
        # 2. 量子熵
        density_matrix = self.psi_real**2 + self.psi_imag**2
        density_matrix /= np.sum(density_matrix)
        eigenvalues = np.linalg.eigvalsh(density_matrix)
        eigenvalues = eigenvalues[eigenvalues > 1e-10]
        entropy = -np.sum(eigenvalues * np.log(eigenvalues)) if len(eigenvalues) > 0 else 0
        
        # 3. 相干性
        coherence = np.mean(np.abs(np.fft.fft2(psi))**2)
        
        # 4. 共振度
        field_frequencies = np.sqrt(self.KX**2 + self.KY**2 + 1)
        consciousness_freq = sum(s['frequency'] * s['amplitude'] 
                               for s in self.consciousness_sources if s['active'])
        resonance = np.exp(-np.abs(field_frequencies - consciousness_freq).mean())
        
        # 5. 三盗平衡度
        field_energy = np.sum(np.abs(self.cosmic_field))
        consciousness_energy = np.sum(np.abs(self.get_consciousness_potential(self.simulation_time)))
        balance = 1.0 - abs(field_energy - consciousness_energy) / (field_energy + consciousness_energy + 1e-10)
        
        return {
            'energy': total_energy,
            'entropy': entropy,
            'coherence': coherence,
            'resonance': resonance,
            'balance': balance
        }
    
    @property
    def cosmic_field(self):
        """获取当前宇宙场状态"""
        return self.psi_real**2 + self.psi_imag**2
    
    def schrodinger_step(self, t):
        """增强的薛定谔方程求解"""
        psi = self.psi_real + 1j * self.psi_imag
        
        # 添加非线性项 (Gross-Pitaevskii 方程风格)
        nonlinear_term = self.nonlinearity * np.abs(psi)**2
        
        # 第一步：势能项 (半时间步)
        total_potential = self.potential + self.get_consciousness_potential(t) + nonlinear_term
        psi = psi * np.exp(-1j * total_potential * self.dt / (2 * self.hbar))
        
        # 第二步：动能项
        psi_k = np.fft.fft2(psi)
        kinetic = (self.KX**2 + self.KY**2) / (2 * self.mass)
        psi_k = psi_k * np.exp(-1j * kinetic * self.dt / self.hbar)
        psi = np.fft.ifft2(psi_k)
        
        # 第三步：势能项 (半时间步)
        psi = psi * np.exp(-1j * total_potential * self.dt / (2 * self.hbar))
        
        # 添加量子噪声
        noise_real = np.random.normal(0, self.noise_level, psi.shape)
        noise_imag = np.random.normal(0, self.noise_level, psi.shape)
        psi += noise_real + 1j * noise_imag
        
        # 更新波函数
        self.psi_real = psi.real
        self.psi_imag = psi.imag
        
        # 周期性归一化
        if t % 50 == 0:
            norm = np.sqrt(np.sum(self.psi_real**2 + self.psi_imag**2))
            if norm > 0:
                self.psi_real /= norm
                self.psi_imag /= norm
    
    def step(self):
        """执行一个时间步"""
        self.schrodinger_step(self.simulation_time)
        
        # 计算指标
        metrics = self.compute_advanced_metrics()
        self.energy_history.append(metrics['energy'])
        self.entropy_history.append(metrics['entropy'])
        self.coherence_history.append(metrics['coherence'])
        self.resonance_history.append(metrics['resonance'])
        self.balance_history.append(metrics['balance'])
        
        self.simulation_time += self.dt
        
        # 限制历史记录长度
        max_history = 1000
        if len(self.energy_history) > max_history:
            self.energy_history.pop(0)
            self.entropy_history.pop(0)
            self.coherence_history.pop(0)
            self.resonance_history.pop(0)
            self.balance_history.pop(0)
    
    def reset(self):
        """重置模拟"""
        self.psi_real = np.random.normal(0, 0.1, (self.grid_size, self.grid_size))
        self.psi_imag = np.random.normal(0, 0.1, (self.grid_size, self.grid_size))
        self.energy_history = []
        self.entropy_history = []
        self.coherence_history = []
        self.resonance_history = []
        self.balance_history = []
        self.simulation_time = 0

class MplCanvas(FigureCanvas):
    """Matplotlib画布"""
    
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        super().__init__(self.fig)
        self.setParent(parent)

class ControlPanel(QWidget):
    """控制面板"""
    
    paramChanged = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.simulator = None
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 模拟控制组
        sim_group = QGroupBox("模拟控制")
        sim_layout = QGridLayout()
        
        self.start_btn = QPushButton("开始模拟")
        self.pause_btn = QPushButton("暂停")
        self.reset_btn = QPushButton("重置")
        self.step_btn = QPushButton("单步")
        
        sim_layout.addWidget(self.start_btn, 0, 0)
        sim_layout.addWidget(self.pause_btn, 0, 1)
        sim_layout.addWidget(self.reset_btn, 1, 0)
        sim_layout.addWidget(self.step_btn, 1, 1)
        
        sim_group.setLayout(sim_layout)
        layout.addWidget(sim_group)
        
        # 模拟参数组
        param_group = QGroupBox("模拟参数")
        param_layout = QGridLayout()
        
        param_layout.addWidget(QLabel("时间步长:"), 0, 0)
        self.dt_spin = QDoubleSpinBox()
        self.dt_spin.setRange(0.001, 0.5)
        self.dt_spin.setValue(0.05)
        self.dt_spin.setSingleStep(0.01)
        param_layout.addWidget(self.dt_spin, 0, 1)
        
        param_layout.addWidget(QLabel("网格大小:"), 1, 0)
        self.grid_spin = QSpinBox()
        self.grid_spin.setRange(64, 512)
        self.grid_spin.setValue(256)
        param_layout.addWidget(self.grid_spin, 1, 1)
        
        param_layout.addWidget(QLabel("噪声水平:"), 2, 0)
        self.noise_spin = QDoubleSpinBox()
        self.noise_spin.setRange(0.0, 0.1)
        self.noise_spin.setValue(0.01)
        self.noise_spin.setSingleStep(0.001)
        param_layout.addWidget(self.noise_spin, 2, 1)
        
        param_layout.addWidget(QLabel("非线性:"), 3, 0)
        self.nonlinear_spin = QDoubleSpinBox()
        self.nonlinear_spin.setRange(0.0, 0.2)
        self.nonlinear_spin.setValue(0.05)
        self.nonlinear_spin.setSingleStep(0.01)
        param_layout.addWidget(self.nonlinear_spin, 3, 1)
        
        param_group.setLayout(param_layout)
        layout.addWidget(param_group)
        
        # 意识源控制组
        source_group = QGroupBox("意识源管理")
        source_layout = QVBoxLayout()
        
        self.add_source_btn = QPushButton("添加意识源")
        source_layout.addWidget(self.add_source_btn)
        
        self.sources_list = QComboBox()
        source_layout.addWidget(QLabel("当前意识源:"))
        source_layout.addWidget(self.sources_list)
        
        source_control_layout = QGridLayout()
        
        source_control_layout.addWidget(QLabel("X位置:"), 0, 0)
        self.source_x_spin = QDoubleSpinBox()
        self.source_x_spin.setRange(-10, 10)
        self.source_x_spin.setValue(0)
        source_control_layout.addWidget(self.source_x_spin, 0, 1)
        
        source_control_layout.addWidget(QLabel("Y位置:"), 1, 0)
        self.source_y_spin = QDoubleSpinBox()
        self.source_y_spin.setRange(-10, 10)
        self.source_y_spin.setValue(0)
        source_control_layout.addWidget(self.source_y_spin, 1, 1)
        
        source_control_layout.addWidget(QLabel("强度:"), 2, 0)
        self.source_amp_spin = QDoubleSpinBox()
        self.source_amp_spin.setRange(0.1, 5.0)
        self.source_amp_spin.setValue(1.0)
        source_control_layout.addWidget(self.source_amp_spin, 2, 1)
        
        source_control_layout.addWidget(QLabel("频率:"), 3, 0)
        self.source_freq_spin = QDoubleSpinBox()
        self.source_freq_spin.setRange(0.1, 2.0)
        self.source_freq_spin.setValue(0.5)
        source_control_layout.addWidget(self.source_freq_spin, 3, 1)
        
        source_control_layout.addWidget(QLabel("专注度:"), 4, 0)
        self.source_focus_spin = QDoubleSpinBox()
        self.source_focus_spin.setRange(0.1, 1.0)
        self.source_focus_spin.setValue(0.8)
        source_control_layout.addWidget(self.source_focus_spin, 4, 1)
        
        source_control_layout.addWidget(QLabel("类型:"), 5, 0)
        self.source_type_combo = QComboBox()
        self.source_type_combo.addItems(["普通", "专注", "扩散", "振荡"])
        source_control_layout.addWidget(self.source_type_combo, 5, 1)
        
        source_control_layout.addWidget(QLabel("激活:"), 6, 0)
        self.source_active_check = QCheckBox()
        self.source_active_check.setChecked(True)
        source_control_layout.addWidget(self.source_active_check, 6, 1)
        
        source_layout.addLayout(source_control_layout)
        
        self.update_source_btn = QPushButton("更新意识源")
        self.remove_source_btn = QPushButton("移除意识源")
        
        source_layout.addWidget(self.update_source_btn)
        source_layout.addWidget(self.remove_source_btn)
        
        source_group.setLayout(source_layout)
        layout.addWidget(source_group)
        
        # 分析控制组
        analysis_group = QGroupBox("分析设置")
        analysis_layout = QVBoxLayout()
        
        self.auto_analysis_check = QCheckBox("自动分析")
        self.auto_analysis_check.setChecked(True)
        analysis_layout.addWidget(self.auto_analysis_check)
        
        self.analysis_btn = QPushButton("执行分析")
        analysis_layout.addWidget(self.analysis_btn)
        
        analysis_group.setLayout(analysis_layout)
        layout.addWidget(analysis_group)
        
        layout.addStretch()
        self.setLayout(layout)
        
        # 连接信号
        self.setup_connections()
    
    def setup_connections(self):
        """设置信号连接"""
        self.dt_spin.valueChanged.connect(self.on_param_changed)
        self.grid_spin.valueChanged.connect(self.on_param_changed)
        self.noise_spin.valueChanged.connect(self.on_param_changed)
        self.nonlinear_spin.valueChanged.connect(self.on_param_changed)
        
        self.sources_list.currentIndexChanged.connect(self.on_source_selected)
        self.add_source_btn.clicked.connect(self.on_add_source)
        self.update_source_btn.clicked.connect(self.on_update_source)
        self.remove_source_btn.clicked.connect(self.on_remove_source)
    
    def on_param_changed(self):
        """参数改变时发射信号"""
        self.paramChanged.emit()
    
    def on_add_source(self):
        """添加新的意识源"""
        if self.simulator:
            source_id = self.simulator.add_consciousness_source(
                x=self.source_x_spin.value(),
                y=self.source_y_spin.value(),
                amplitude=self.source_amp_spin.value(),
                frequency=self.source_freq_spin.value(),
                focus=self.source_focus_spin.value(),
                intention=1.0,
                source_type=self.source_type_combo.currentText()
            )
            self.update_sources_list()
            self.paramChanged.emit()
    
    def on_update_source(self):
        """更新当前选择的意识源"""
        current_id = self.get_current_source_id()
        if current_id is not None and self.simulator:
            self.simulator.update_consciousness_source(
                current_id,
                x=self.source_x_spin.value(),
                y=self.source_y_spin.value(),
                amplitude=self.source_amp_spin.value(),
                frequency=self.source_freq_spin.value(),
                focus=self.source_focus_spin.value(),
                type=self.source_type_combo.currentText(),
                active=self.source_active_check.isChecked()
            )
            self.paramChanged.emit()
    
    def on_remove_source(self):
        """移除当前选择的意识源"""
        current_id = self.get_current_source_id()
        if current_id is not None and self.simulator:
            self.simulator.remove_consciousness_source(current_id)
            self.update_sources_list()
            self.paramChanged.emit()
    
    def on_source_selected(self, index):
        """意识源选择改变"""
        if index >= 0 and self.simulator:
            source_id = int(self.sources_list.itemData(index))
            source = self.get_source_by_id(source_id)
            if source:
                self.source_x_spin.setValue(source['x'])
                self.source_y_spin.setValue(source['y'])
                self.source_amp_spin.setValue(source['amplitude'])
                self.source_freq_spin.setValue(source['frequency'])
                self.source_focus_spin.setValue(source['focus'])
                self.source_type_combo.setCurrentText(source['type'])
                self.source_active_check.setChecked(source['active'])
    
    def get_current_source_id(self):
        """获取当前选择的意识源ID"""
        index = self.sources_list.currentIndex()
        if index >= 0:
            return int(self.sources_list.itemData(index))
        return None
    
    def get_source_by_id(self, source_id):
        """根据ID获取意识源"""
        for source in self.simulator.consciousness_sources:
            if source['id'] == source_id:
                return source
        return None
    
    def update_sources_list(self):
        """更新意识源列表"""
        self.sources_list.clear()
        if self.simulator:
            for source in self.simulator.consciousness_sources:
                self.sources_list.addItem(
                    f"源{source['id']} ({source['type']})", 
                    source['id']
                )

class VisualizationPanel(QWidget):
    """可视化面板"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.simulator = None
        self.colors = ['#000066', '#0000FF', '#00FFFF', '#00FF00', '#FFFF00', '#FF0000', '#800000']
        self.cmap = LinearSegmentedColormap.from_list('quantum', self.colors)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 创建标签页
        self.tabs = QTabWidget()
        
        # 主视图标签页
        self.main_tab = QWidget()
        self.setup_main_tab()
        self.tabs.addTab(self.main_tab, "主视图")
        
        # 分析视图标签页
        self.analysis_tab = QWidget()
        self.setup_analysis_tab()
        self.tabs.addTab(self.analysis_tab, "分析视图")
        
        # 3D视图标签页
        self.three_d_tab = QWidget()
        self.setup_3d_tab()
        self.tabs.addTab(self.three_d_tab, "3D视图")
        
        layout.addWidget(self.tabs)
        self.setLayout(layout)
    
    def setup_main_tab(self):
        """设置主视图标签页"""
        layout = QGridLayout()
        
        # 量子场密度
        self.field_canvas = MplCanvas(self, width=6, height=5)
        layout.addWidget(self.field_canvas, 0, 0)
        
        # 势场分布
        self.potential_canvas = MplCanvas(self, width=6, height=5)
        layout.addWidget(self.potential_canvas, 0, 1)
        
        # 相位分布
        self.phase_canvas = MplCanvas(self, width=6, height=5)
        layout.addWidget(self.phase_canvas, 1, 0)
        
        # 动量空间
        self.momentum_canvas = MplCanvas(self, width=6, height=5)
        layout.addWidget(self.momentum_canvas, 1, 1)
        
        self.main_tab.setLayout(layout)
    
    def setup_analysis_tab(self):
        """设置分析视图标签页"""
        layout = QGridLayout()
        
        # 时间序列
        self.timeseries_canvas = MplCanvas(self, width=8, height=4)
        layout.addWidget(self.timeseries_canvas, 0, 0, 1, 2)
        
        # 相关性分析
        self.correlation_canvas = MplCanvas(self, width=4, height=4)
        layout.addWidget(self.correlation_canvas, 1, 0)
        
        # 功率谱
        self.powerspec_canvas = MplCanvas(self, width=4, height=4)
        layout.addWidget(self.powerspec_canvas, 1, 1)
        
        self.analysis_tab.setLayout(layout)
    
    def setup_3d_tab(self):
        """设置3D视图标签页"""
        layout = QVBoxLayout()
        
        self.three_d_canvas = MplCanvas(self, width=8, height=6)
        layout.addWidget(self.three_d_canvas)
        
        self.three_d_tab.setLayout(layout)
    
    def update_visualizations(self):
        """更新所有可视化"""
        if self.simulator is None:
            return
            
        self.update_main_views()
        self.update_analysis_views()
        self.update_3d_view()
        
        # 强制重绘
        for canvas in [self.field_canvas, self.potential_canvas, self.phase_canvas,
                      self.momentum_canvas, self.timeseries_canvas, self.correlation_canvas,
                      self.powerspec_canvas, self.three_d_canvas]:
            canvas.draw()
    
    def update_main_views(self):
        """更新主视图"""
        # 量子场密度
        self.field_canvas.fig.clear()
        ax = self.field_canvas.fig.add_subplot(111)
        density = self.simulator.cosmic_field
        im = ax.imshow(density, cmap=self.cmap, extent=[-10, 10, -10, 10], origin='lower')
        ax.set_title('量子场密度分布 | 宇宙基态显化')
        ax.set_xlabel('空间维度 X')
        ax.set_ylabel('空间维度 Y')
        self.field_canvas.fig.colorbar(im, ax=ax, label='概率密度')
        
        # 标记意识源
        for source in self.simulator.consciousness_sources:
            if source['active']:
                color = 'red' if source['type'] == '专注' else 'yellow'
                ax.plot(source['x'], source['y'], 'o', color=color, markersize=8)
        
        # 势场分布
        self.potential_canvas.fig.clear()
        ax = self.potential_canvas.fig.add_subplot(111)
        total_potential = self.simulator.potential + self.simulator.get_consciousness_potential(self.simulator.simulation_time)
        im = ax.imshow(total_potential, cmap='viridis', extent=[-10, 10, -10, 10], origin='lower')
        ax.set_title('总势场分布 | 天道约束+意识编程')
        self.potential_canvas.fig.colorbar(im, ax=ax, label='势能')
        
        # 相位分布
        self.phase_canvas.fig.clear()
        ax = self.phase_canvas.fig.add_subplot(111)
        phase = np.angle(self.simulator.psi_real + 1j * self.simulator.psi_imag)
        im = ax.imshow(phase, cmap='hsv', extent=[-10, 10, -10, 10], origin='lower')
        ax.set_title('量子相位分布 | 信息流动方向')
        self.phase_canvas.fig.colorbar(im, ax=ax, label='相位(弧度)')
        
        # 动量空间
        self.momentum_canvas.fig.clear()
        ax = self.momentum_canvas.fig.add_subplot(111)
        psi_k = np.fft.fftshift(np.fft.fft2(self.simulator.psi_real + 1j * self.simulator.psi_imag))
        k_power = np.log(np.abs(psi_k) + 1)
        im = ax.imshow(k_power, cmap='hot', extent=[-np.pi, np.pi, -np.pi, np.pi], origin='lower')
        ax.set_title('动量空间分布 | 频率谱分析')
        ax.set_xlabel('波数 kx')
        ax.set_ylabel('波数 ky')
        self.momentum_canvas.fig.colorbar(im, ax=ax, label='对数功率')
    
    def update_analysis_views(self):
        """更新分析视图"""
        if len(self.simulator.energy_history) < 10:
            return
            
        # 时间序列
        self.timeseries_canvas.fig.clear()
        ax = self.timeseries_canvas.fig.add_subplot(111)
        time_points = list(range(len(self.simulator.energy_history)))
        
        # 归一化显示
        metrics = {
            '能量': np.array(self.simulator.energy_history) / max(self.simulator.energy_history),
            '熵': np.array(self.simulator.entropy_history) / max(self.simulator.entropy_history),
            '相干性': np.array(self.simulator.coherence_history) / max(self.simulator.coherence_history),
            '共振度': self.simulator.resonance_history,
            '平衡度': self.simulator.balance_history
        }
        
        for label, values in metrics.items():
            ax.plot(time_points, values, label=label, linewidth=2)
        
        ax.set_xlabel('时间步')
        ax.set_ylabel('归一化指标')
        ax.set_title('系统动态演化指标')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        # 相关性分析
        self.correlation_canvas.fig.clear()
        ax = self.correlation_canvas.fig.add_subplot(111)
        
        data = np.array([
            self.simulator.energy_history[-100:],
            self.simulator.entropy_history[-100:],
            self.simulator.coherence_history[-100:],
            self.simulator.resonance_history[-100:],
            self.simulator.balance_history[-100:]
        ])
        
        # 归一化
        data = (data - data.mean(axis=1, keepdims=True)) / data.std(axis=1, keepdims=True)
        correlations = np.corrcoef(data)
        
        labels = ['能量', '熵', '相干性', '共振度', '平衡度']
        im = ax.imshow(correlations, cmap='coolwarm', vmin=-1, vmax=1)
        ax.set_xticks(range(len(labels)))
        ax.set_yticks(range(len(labels)))
        ax.set_xticklabels(labels, rotation=45)
        ax.set_yticklabels(labels)
        ax.set_title('物理量相关性矩阵')
        
        # 添加数值标注
        for i in range(len(labels)):
            for j in range(len(labels)):
                ax.text(j, i, f'{correlations[i,j]:.2f}', 
                       ha='center', va='center', color='white' if abs(correlations[i,j]) > 0.5 else 'black')
        
        self.correlation_canvas.fig.colorbar(im, ax=ax)
        
        # 功率谱分析
        self.powerspec_canvas.fig.clear()
        ax = self.powerspec_canvas.fig.add_subplot(111)
        
        signal = self.simulator.energy_history - np.mean(self.simulator.energy_history)
        n = len(signal)
        freq = np.fft.fftfreq(n)
        power = np.abs(np.fft.fft(signal))**2
        
        positive_freq = freq[:n//2]
        positive_power = power[:n//2]
        
        ax.semilogy(positive_freq, positive_power, 'b-', linewidth=1)
        ax.set_xlabel('频率')
        ax.set_ylabel('功率')
        ax.set_title('能量功率谱分析')
        ax.grid(True, alpha=0.3)
    
    def update_3d_view(self):
        """更新3D视图"""
        self.three_d_canvas.fig.clear()
        ax = self.three_d_canvas.fig.add_subplot(111, projection='3d')
        
        # 创建网格
        X, Y = np.meshgrid(self.simulator.x[::4], self.simulator.y[::4])  # 降采样以提高性能
        Z = self.simulator.cosmic_field[::4, ::4]
        
        # 绘制3D表面
        surf = ax.plot_surface(X, Y, Z, cmap=self.cmap, alpha=0.8, 
                              linewidth=0, antialiased=True)
        
        ax.set_xlabel('空间 X')
        ax.set_ylabel('空间 Y')
        ax.set_zlabel('场强度')
        ax.set_title('量子场3D结构')
        
        self.three_d_canvas.fig.colorbar(surf, ax=ax, shrink=0.5, aspect=5)

class StatusPanel(QWidget):
    """状态面板"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.simulator = None
        self.init_ui()
    
    def init_ui(self):
        layout = QGridLayout()
        
        # 实时指标显示
        self.metric_labels = {}
        metrics = ['能量', '熵', '相干性', '共振度', '平衡度', '模拟时间', '意识源数量']
        
        for i, metric in enumerate(metrics):
            layout.addWidget(QLabel(metric + ":"), i, 0)
            label = QLabel("0.000")
            label.setStyleSheet("background-color: #f0f0f0; padding: 2px; border: 1px solid #ccc;")
            self.metric_labels[metric] = label
            layout.addWidget(label, i, 1)
        
        # 进度条
        layout.addWidget(QLabel("模拟进度:"), len(metrics), 0)
        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar, len(metrics), 1)
        
        self.setLayout(layout)
    
    def update_status(self):
        """更新状态显示"""
        if self.simulator is None:
            return
            
        if len(self.simulator.energy_history) > 0:
            self.metric_labels['能量'].setText(f"{self.simulator.energy_history[-1]:.3f}")
            self.metric_labels['熵'].setText(f"{self.simulator.entropy_history[-1]:.3f}")
            self.metric_labels['相干性'].setText(f"{self.simulator.coherence_history[-1]:.3f}")
            self.metric_labels['共振度'].setText(f"{self.simulator.resonance_history[-1]:.3f}")
            self.metric_labels['平衡度'].setText(f"{self.simulator.balance_history[-1]:.3f}")
        
        self.metric_labels['模拟时间'].setText(f"{self.simulator.simulation_time:.1f}")
        self.metric_labels['意识源数量'].setText(f"{len(self.simulator.consciousness_sources)}")
        
        # 更新进度条（基于模拟时间）
        progress = min(100, int(self.simulator.simulation_time * 10))
        self.progress_bar.setValue(progress)

class MainWindow(QMainWindow):
    """主窗口"""
    
    def __init__(self):
        super().__init__()
        self.simulator = None
        self.timer = QTimer()
        self.is_running = False
        self.init_ui()
        self.init_simulation()
    
    def init_ui(self):
        self.setWindowTitle("《黄帝阴符经》量子意识场模拟系统")
        self.setGeometry(100, 100, 1600, 1000)
        
        # 设置深色主题
        self.set_dark_theme()
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        main_layout = QHBoxLayout()
        
        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        
        # 左侧控制面板
        self.control_panel = ControlPanel()
        splitter.addWidget(self.control_panel)
        
        # 右侧可视化区域
        right_widget = QWidget()
        right_layout = QVBoxLayout()
        
        # 可视化面板
        self.viz_panel = VisualizationPanel()
        right_layout.addWidget(self.viz_panel)
        
        # 状态面板
        self.status_panel = StatusPanel()
        right_layout.addWidget(self.status_panel)
        
        right_widget.setLayout(right_layout)
        splitter.addWidget(right_widget)
        
        # 设置分割器比例
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        
        main_layout.addWidget(splitter)
        central_widget.setLayout(main_layout)
        
        # 连接信号
        self.setup_connections()
        
        # 创建菜单栏
        self.create_menu_bar()
    
    def set_dark_theme(self):
        """设置深色主题"""
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
        palette.setColor(QPalette.Link, QColor(42, 130, 218))
        palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
        palette.setColor(QPalette.HighlightedText, Qt.black)
        
        self.setPalette(palette)
    
    def create_menu_bar(self):
        """创建菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu('文件')
        
        new_action = file_menu.addAction('新建模拟')
        new_action.triggered.connect(self.on_new_simulation)
        
        reset_action = file_menu.addAction('重置模拟')
        reset_action.triggered.connect(self.on_reset_simulation)
        
        file_menu.addSeparator()
        
        exit_action = file_menu.addAction('退出')
        exit_action.triggered.connect(self.close)
        
        # 模拟菜单
        sim_menu = menubar.addMenu('模拟')
        
        start_action = sim_menu.addAction('开始模拟')
        start_action.triggered.connect(self.on_start_simulation)
        
        pause_action = sim_menu.addAction('暂停模拟')
        pause_action.triggered.connect(self.on_pause_simulation)
        
        step_action = sim_menu.addAction('单步模拟')
        step_action.triggered.connect(self.on_step_simulation)
        
        # 帮助菜单
        help_menu = menubar.addMenu('帮助')
        
        about_action = help_menu.addAction('关于')
        about_action.triggered.connect(self.show_about)
    
    def setup_connections(self):
        """设置信号连接"""
        # 控制面板信号
        self.control_panel.start_btn.clicked.connect(self.on_start_simulation)
        self.control_panel.pause_btn.clicked.connect(self.on_pause_simulation)
        self.control_panel.reset_btn.clicked.connect(self.on_reset_simulation)
        self.control_panel.step_btn.clicked.connect(self.on_step_simulation)
        self.control_panel.paramChanged.connect(self.on_parameters_changed)
        
        # 定时器信号
        self.timer.timeout.connect(self.on_simulation_step)
        
        # 设置定时器间隔
        self.timer.setInterval(50)  # 20 FPS
    
    def init_simulation(self):
        """初始化模拟器"""
        self.simulator = QuantumConsciousnessField(
            grid_size=self.control_panel.grid_spin.value(),
            dt=self.control_panel.dt_spin.value()
        )
        
        # 添加默认意识源
        self.simulator.add_consciousness_source(0, 0, 1.0, 0.5, 0.8, 1.0, "普通")
        
        # 更新各个面板的模拟器引用
        self.control_panel.simulator = self.simulator
        self.viz_panel.simulator = self.simulator
        self.status_panel.simulator = self.simulator
        
        # 更新UI
        self.control_panel.update_sources_list()
        self.update_display()
    
    def on_parameters_changed(self):
        """处理参数改变"""
        if self.simulator:
            self.simulator.dt = self.control_panel.dt_spin.value()
            self.simulator.noise_level = self.control_panel.noise_spin.value()
            self.simulator.nonlinearity = self.control_panel.nonlinear_spin.value()
            
            # 如果网格大小改变，需要重新初始化
            new_grid_size = self.control_panel.grid_spin.value()
            if new_grid_size != self.simulator.grid_size:
                self.init_simulation()
    
    def on_start_simulation(self):
        """开始模拟"""
        if not self.is_running:
            self.timer.start()
            self.is_running = True
            self.control_panel.start_btn.setEnabled(False)
            self.control_panel.pause_btn.setEnabled(True)
    
    def on_pause_simulation(self):
        """暂停模拟"""
        if self.is_running:
            self.timer.stop()
            self.is_running = False
            self.control_panel.start_btn.setEnabled(True)
            self.control_panel.pause_btn.setEnabled(False)
    
    def on_reset_simulation(self):
        """重置模拟"""
        self.on_pause_simulation()
        self.init_simulation()
    
    def on_step_simulation(self):
        """单步模拟"""
        self.on_simulation_step()
    
    def on_new_simulation(self):
        """新建模拟"""
        reply = QMessageBox.question(self, '新建模拟', 
                                   '这将重置当前模拟，是否继续？',
                                   QMessageBox.Yes | QMessageBox.No,
                                   QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.on_reset_simulation()
    
    def on_simulation_step(self):
        """模拟步进"""
        if self.simulator:
            self.simulator.step()
            self.update_display()
    
    def update_display(self):
        """更新显示"""
        self.viz_panel.update_visualizations()
        self.status_panel.update_status()
    
    def show_about(self):
        """显示关于对话框"""
        about_text = """
        《黄帝阴符经》量子意识场模拟系统
        
        基于量子力学和信息论的现代科学框架，
        重新诠释《黄帝阴符经》中的古老智慧。
        
        功能特性：
        • 量子场演化模拟
        • 意识-宇宙相互作用
        • 多意识源管理
        • 实时可视化分析
        • 高级物理指标计算
        
        版本 1.0
        © 2024 量子意识研究实验室
        """
        
        QMessageBox.about(self, "关于系统", about_text)
    
    def closeEvent(self, event):
        """关闭事件处理"""
        self.on_pause_simulation()
        event.accept()

def main():
    app = QApplication(sys.argv)
    
    # 设置应用程序样式
    app.setStyle('Fusion')
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()