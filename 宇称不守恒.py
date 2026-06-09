import sys
import numpy as np
import matplotlib
matplotlib.rc("font", family='Microsoft YaHei')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                             QWidget, QPushButton, QLabel, QSlider, QGroupBox,
                             QComboBox, QSpinBox, QDoubleSpinBox, QTabWidget,
                             QTextEdit, QSplitter, QProgressBar)
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, pyqtProperty
from PyQt5.QtGui import QFont, QPalette, QColor
import random

class Particle:
    def __init__(self, particle_type, position, momentum, spin, lifetime=0):
        self.type = particle_type
        self.position = np.array(position, dtype=float)
        self.momentum = np.array(momentum, dtype=float)
        self.spin = np.array(spin, dtype=float)
        self.lifetime = lifetime
        self.age = 0
        self.decayed = False
        self.daughters = []
        
    def update(self, dt):
        self.age += dt
        if not self.decayed and self.lifetime > 0 and self.age > self.lifetime:
            self.decay()
            
    def decay(self):
        self.decayed = True
        # 根据粒子类型和宇称不守恒参数生成衰变产物
        if self.type == "Co-60":
            # 钴-60衰变为镍-60，发射电子和中微子
            # 宇称不守恒体现在电子发射方向的不对称性
            asymmetry = 0.4  # 不对称因子
            
            # 主要衰变方向与自旋方向相关
            direction = np.cross(self.spin, [0, 0, 1])
            if np.linalg.norm(direction) == 0:
                direction = np.array([1, 0, 0])
            direction = direction / np.linalg.norm(direction)
            
            # 应用不对称性
            if random.random() < asymmetry:
                # 优先发射到一个方向
                electron_dir = direction
            else:
                # 随机方向
                electron_dir = np.random.randn(3)
                electron_dir = electron_dir / np.linalg.norm(electron_dir)
            
            # 创建衰变产物
            electron = Particle("e-", self.position, electron_dir * 0.8, [0, 0, 0])
            antineutrino = Particle("v̄", self.position, -electron_dir * 0.2, [0, 0, 0])
            nickel = Particle("Ni-60", self.position, [0, 0, 0], [0, 0, 0])
            
            self.daughters = [electron, antineutrino, nickel]
            
        elif self.type == "π+":
            # π+介子衰变为μ+和中微子
            asymmetry = 0.3
            
            # 根据自旋方向产生不对称性
            direction = self.spin
            if np.linalg.norm(direction) == 0:
                direction = np.array([1, 0, 0])
            direction = direction / np.linalg.norm(direction)
            
            if random.random() < asymmetry:
                muon_dir = direction
            else:
                muon_dir = np.random.randn(3)
                muon_dir = muon_dir / np.linalg.norm(muon_dir)
                
            muon = Particle("μ+", self.position, muon_dir * 0.9, [0, 0, 0])
            neutrino = Particle("v_μ", self.position, -muon_dir * 0.1, [0, 0, 0])
            
            self.daughters = [muon, neutrino]
            
        elif self.type == "Λ":
            # Λ超子衰变为质子和π-介子
            asymmetry = 0.2
            
            direction = self.spin
            if np.linalg.norm(direction) == 0:
                direction = np.array([1, 0, 0])
            direction = direction / np.linalg.norm(direction)
            
            if random.random() < asymmetry:
                proton_dir = direction
            else:
                proton_dir = np.random.randn(3)
                proton_dir = proton_dir / np.linalg.norm(proton_dir)
                
            proton = Particle("p", self.position, proton_dir * 0.7, [0, 0, 0])
            pion = Particle("π-", self.position, -proton_dir * 0.3, [0, 0, 0])
            
            self.daughters = [proton, pion]

class ParityViolationSimulation(FigureCanvas):
    def __init__(self, parent=None, width=8, height=6, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        super().__init__(self.fig)
        self.setParent(parent)
        
        # 创建子图
        self.ax1 = self.fig.add_subplot(221)  # 宇称守恒情况
        self.ax2 = self.fig.add_subplot(222)  # 宇称不守恒情况
        self.ax3 = self.fig.add_subplot(223)  # 统计对比
        self.ax4 = self.fig.add_subplot(224)  # 时间演化
        
        self.particles = []
        self.history = []
        self.setup_plots()
        
    def setup_plots(self):
        # 初始化绘图
        self.ax1.clear()
        self.ax2.clear()
        self.ax3.clear()
        self.ax4.clear()
        
        # 设置标题
        self.ax1.set_title('宇称守恒情况')
        self.ax2.set_title('宇称不守恒情况')
        self.ax3.set_title('统计对比')
        self.ax4.set_title('时间演化')
        
        # 设置坐标轴
        for ax in [self.ax1, self.ax2]:
            ax.set_xlim(-1.5, 1.5)
            ax.set_ylim(-1.5, 1.5)
            ax.set_aspect('equal')
            ax.grid(True, linestyle='--', alpha=0.7)
            ax.axhline(y=0, color='k', linestyle='-', alpha=0.3)
            ax.axvline(x=0, color='k', linestyle='-', alpha=0.3)
        
        self.ax3.set_xlabel('方向')
        self.ax3.set_ylabel('粒子数量')
        
        self.ax4.set_xlabel('时间')
        self.ax4.set_ylabel('不对称度')
        
        self.fig.tight_layout()
        self.draw()
    
    def initialize_particles(self, num_particles, particle_type):
        self.particles = []
        for _ in range(num_particles):
            # 随机位置和动量
            position = [0, 0, 0]  # 所有粒子从原点开始
            momentum = np.random.randn(3)
            momentum = momentum / np.linalg.norm(momentum) * 0.1
            
            # 随机自旋方向
            spin = np.random.randn(3)
            spin = spin / np.linalg.norm(spin)
            
            # 设置寿命
            if particle_type == "Co-60":
                lifetime = random.expovariate(1/10.0)  # 平均寿命10个时间单位
            elif particle_type == "π+":
                lifetime = random.expovariate(1/5.0)   # 平均寿命5个时间单位
            elif particle_type == "Λ":
                lifetime = random.expovariate(1/8.0)   # 平均寿命8个时间单位
            else:
                lifetime = random.expovariate(1/10.0)
                
            self.particles.append(Particle(particle_type, position, momentum, spin, lifetime))
    
    def update_simulation(self, asymmetry_factor, num_particles, particle_type, time_step=0.1):
        # 如果粒子列表为空，初始化粒子
        if not self.particles:
            self.initialize_particles(num_particles, particle_type)
        
        # 更新粒子状态
        for particle in self.particles:
            particle.update(time_step)
        
        # 收集衰变产物
        new_particles = []
        for particle in self.particles:
            if particle.decayed:
                new_particles.extend(particle.daughters)
            else:
                new_particles.append(particle)
        
        self.particles = new_particles
        
        # 分析数据
        conserved_data = self.simulate_conserved(num_particles)
        violated_data = self.simulate_violated(num_particles, asymmetry_factor)
        
        # 更新绘图
        self.update_plots(conserved_data, violated_data, asymmetry_factor)
        
        # 记录历史数据
        if len(self.history) < 100:  # 只保留最近100个数据点
            self.history.append((conserved_data, violated_data, asymmetry_factor))
        else:
            self.history.pop(0)
            self.history.append((conserved_data, violated_data, asymmetry_factor))
    
    def simulate_conserved(self, num_particles):
        # 宇称守恒情况 - 对称分布
        theta = np.random.uniform(0, 2*np.pi, num_particles)
        x = np.cos(theta)
        y = np.sin(theta)
        
        # 统计上下半球的粒子数量
        upper = np.sum(y > 0)
        lower = np.sum(y < 0)
        
        return {'theta': theta, 'x': x, 'y': y, 'upper': upper, 'lower': lower}
    
    def simulate_violated(self, num_particles, asymmetry_factor):
        # 宇称不守恒情况 - 不对称分布
        theta = np.random.uniform(0, 2*np.pi, num_particles)
        
        # 应用不对称性 - 更多粒子向上半球发射
        mask = np.random.random(num_particles) < asymmetry_factor
        theta[mask] = np.random.uniform(0, np.pi, np.sum(mask))
        
        x = np.cos(theta)
        y = np.sin(theta)
        
        # 统计上下半球的粒子数量
        upper = np.sum(y > 0)
        lower = np.sum(y < 0)
        
        return {'theta': theta, 'x': x, 'y': y, 'upper': upper, 'lower': lower}
    
    def update_plots(self, conserved_data, violated_data, asymmetry_factor):
        # 清除之前的绘图
        self.ax1.clear()
        self.ax2.clear()
        self.ax3.clear()
        self.ax4.clear()
        
        # 绘制宇称守恒情况
        self.ax1.scatter(conserved_data['x'], conserved_data['y'], alpha=0.7, s=20, c='blue')
        self.ax1.set_title(f'宇称守恒情况\n(上: {conserved_data["upper"]}, 下: {conserved_data["lower"]})')
        
        # 绘制宇称不守恒情况
        self.ax2.scatter(violated_data['x'], violated_data['y'], alpha=0.7, s=20, c='red')
        self.ax2.set_title(f'宇称不守恒情况\n(上: {violated_data["upper"]}, 下: {violated_data["lower"]})')
        
        # 绘制统计对比
        categories = ['上半球', '下半球']
        conserved_counts = [conserved_data['upper'], conserved_data['lower']]
        violated_counts = [violated_data['upper'], violated_data['lower']]
        
        x = np.arange(len(categories))
        width = 0.35
        
        self.ax3.bar(x - width/2, conserved_counts, width, label='宇称守恒', color='blue', alpha=0.7)
        self.ax3.bar(x + width/2, violated_counts, width, label='宇称不守恒', color='red', alpha=0.7)
        
        self.ax3.set_xlabel('方向')
        self.ax3.set_ylabel('粒子数量')
        self.ax3.set_title('统计对比')
        self.ax3.set_xticks(x)
        self.ax3.set_xticklabels(categories)
        self.ax3.legend()
        
        # 绘制时间演化
        if len(self.history) > 1:
            times = range(len(self.history))
            asymmetry_degrees = []
            
            for conserved, violated, _ in self.history:
                # 计算不对称度
                conserved_asym = (conserved['upper'] - conserved['lower']) / (conserved['upper'] + conserved['lower'])
                violated_asym = (violated['upper'] - violated['lower']) / (violated['upper'] + violated['lower'])
                asymmetry_degrees.append((conserved_asym, violated_asym))
            
            conserved_degrees = [d[0] for d in asymmetry_degrees]
            violated_degrees = [d[1] for d in asymmetry_degrees]
            
            self.ax4.plot(times, conserved_degrees, label='宇称守恒', color='blue')
            self.ax4.plot(times, violated_degrees, label='宇称不守恒', color='red')
            self.ax4.set_xlabel('时间步')
            self.ax4.set_ylabel('不对称度')
            self.ax4.set_title('时间演化')
            self.ax4.legend()
            self.ax4.grid(True, linestyle='--', alpha=0.7)
        
        # 设置坐标轴
        for ax in [self.ax1, self.ax2]:
            ax.set_xlim(-1.5, 1.5)
            ax.set_ylim(-1.5, 1.5)
            ax.set_aspect('equal')
            ax.grid(True, linestyle='--', alpha=0.7)
            ax.axhline(y=0, color='k', linestyle='-', alpha=0.3)
            ax.axvline(x=0, color='k', linestyle='-', alpha=0.3)
            ax.set_xlabel('X方向')
            ax.set_ylabel('Y方向')
        
        self.fig.tight_layout()
        self.draw()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("宇称不守恒仿真 - 增强版")
        self.setGeometry(100, 100, 1400, 900)
        
        # 初始化参数
        self.asymmetry_factor = 0.3
        self.num_particles = 200
        self.particle_type = "Co-60"
        self.is_playing = False
        self.timer = QTimer()
        self.timer.timeout.connect(self.auto_update)
        
        # 创建中央部件和布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        # 左侧控制面板
        control_panel = self.create_control_panel()
        splitter.addWidget(control_panel)
        
        # 右侧绘图区域
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # 创建标签页
        self.tabs = QTabWidget()
        
        # 仿真标签页
        self.simulation = ParityViolationSimulation(self, width=10, height=8)
        self.tabs.addTab(self.simulation, "宇称不守恒仿真")
        
        # 信息标签页
        self.info_text = QTextEdit()
        self.info_text.setReadOnly(True)
        self.update_info_text()
        self.tabs.addTab(self.info_text, "物理背景")
        
        right_layout.addWidget(self.tabs)
        
        # 添加进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        right_layout.addWidget(self.progress_bar)
        
        splitter.addWidget(right_panel)
        
        # 设置分割器比例
        splitter.setSizes([300, 1100])
        
        # 初始仿真
        self.run_simulation()
    
    def create_control_panel(self):
        panel = QGroupBox("仿真控制")
        layout = QVBoxLayout()
        
        # 实验类型选择
        experiment_layout = QHBoxLayout()
        experiment_layout.addWidget(QLabel("实验类型:"))
        self.experiment_combo = QComboBox()
        self.experiment_combo.addItems(["钴-60衰变", "π+介子衰变", "Λ超子衰变"])
        self.experiment_combo.currentTextChanged.connect(self.on_experiment_changed)
        experiment_layout.addWidget(self.experiment_combo)
        layout.addLayout(experiment_layout)
        
        # 不对称因子控制
        asymmetry_layout = QVBoxLayout()
        asymmetry_layout.addWidget(QLabel("不对称因子:"))
        
        slider_layout = QHBoxLayout()
        self.asymmetry_slider = QSlider(Qt.Horizontal)
        self.asymmetry_slider.setMinimum(0)
        self.asymmetry_slider.setMaximum(100)
        self.asymmetry_slider.setValue(int(self.asymmetry_factor * 100))
        self.asymmetry_slider.valueChanged.connect(self.on_asymmetry_changed)
        slider_layout.addWidget(self.asymmetry_slider)
        
        self.asymmetry_spinbox = QDoubleSpinBox()
        self.asymmetry_spinbox.setMinimum(0.0)
        self.asymmetry_spinbox.setMaximum(1.0)
        self.asymmetry_spinbox.setSingleStep(0.01)
        self.asymmetry_spinbox.setValue(self.asymmetry_factor)
        self.asymmetry_spinbox.valueChanged.connect(self.on_asymmetry_spinbox_changed)
        slider_layout.addWidget(self.asymmetry_spinbox)
        
        asymmetry_layout.addLayout(slider_layout)
        layout.addLayout(asymmetry_layout)
        
        # 粒子数量控制
        particles_layout = QHBoxLayout()
        particles_layout.addWidget(QLabel("粒子数量:"))
        self.particles_spinbox = QSpinBox()
        self.particles_spinbox.setMinimum(10)
        self.particles_spinbox.setMaximum(1000)
        self.particles_spinbox.setValue(self.num_particles)
        self.particles_spinbox.valueChanged.connect(self.on_particles_changed)
        particles_layout.addWidget(self.particles_spinbox)
        layout.addLayout(particles_layout)
        
        # 时间控制
        time_layout = QHBoxLayout()
        time_layout.addWidget(QLabel("时间步长:"))
        self.time_spinbox = QDoubleSpinBox()
        self.time_spinbox.setMinimum(0.01)
        self.time_spinbox.setMaximum(1.0)
        self.time_spinbox.setSingleStep(0.05)
        self.time_spinbox.setValue(0.1)
        time_layout.addWidget(self.time_spinbox)
        layout.addLayout(time_layout)
        
        # 按钮控制
        button_layout = QHBoxLayout()
        
        self.run_button = QPushButton("单步运行")
        self.run_button.clicked.connect(self.run_simulation)
        button_layout.addWidget(self.run_button)
        
        self.play_button = QPushButton("开始播放")
        self.play_button.clicked.connect(self.toggle_play)
        button_layout.addWidget(self.play_button)
        
        self.reset_button = QPushButton("重置")
        self.reset_button.clicked.connect(self.reset_simulation)
        button_layout.addWidget(self.reset_button)
        
        layout.addLayout(button_layout)
        
        # 统计信息
        stats_group = QGroupBox("统计信息")
        stats_layout = QVBoxLayout()
        
        self.stats_label = QLabel("等待数据...")
        self.stats_label.setWordWrap(True)
        stats_layout.addWidget(self.stats_label)
        
        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)
        
        # 物理信息
        physics_group = QGroupBox("物理参数")
        physics_layout = QVBoxLayout()
        
        self.physics_label = QLabel("")
        self.physics_label.setWordWrap(True)
        physics_layout.addWidget(self.physics_label)
        
        physics_group.setLayout(physics_layout)
        layout.addWidget(physics_group)
        
        # 添加弹性空间
        layout.addStretch()
        
        panel.setLayout(layout)
        return panel
    
    def on_experiment_changed(self, text):
        if text == "钴-60衰变":
            self.particle_type = "Co-60"
        elif text == "π+介子衰变":
            self.particle_type = "π+"
        elif text == "Λ超子衰变":
            self.particle_type = "Λ"
        
        self.update_physics_info()
        self.simulation.particles = []  # 重置粒子
        self.run_simulation()
    
    def on_asymmetry_changed(self, value):
        self.asymmetry_factor = value / 100.0
        self.asymmetry_spinbox.setValue(self.asymmetry_factor)
    
    def on_asymmetry_spinbox_changed(self, value):
        self.asymmetry_factor = value
        self.asymmetry_slider.setValue(int(value * 100))
    
    def on_particles_changed(self, value):
        self.num_particles = value
    
    def run_simulation(self):
        time_step = self.time_spinbox.value()
        self.simulation.update_simulation(self.asymmetry_factor, self.num_particles, self.particle_type, time_step)
        self.update_stats()
        self.progress_bar.setValue((self.progress_bar.value() + 10) % 100)
    
    def auto_update(self):
        self.run_simulation()
    
    def toggle_play(self):
        if self.is_playing:
            self.timer.stop()
            self.play_button.setText("开始播放")
            self.is_playing = False
        else:
            self.timer.start(500)  # 每500毫秒更新一次
            self.play_button.setText("停止播放")
            self.is_playing = True
    
    def reset_simulation(self):
        self.asymmetry_factor = 0.3
        self.asymmetry_slider.setValue(30)
        self.asymmetry_spinbox.setValue(0.3)
        self.num_particles = 200
        self.particles_spinbox.setValue(200)
        self.simulation.particles = []
        self.simulation.history = []
        self.run_simulation()
    
    def update_stats(self):
        if not self.simulation.history:
            self.stats_label.setText("等待数据...")
            return
        
        conserved_data, violated_data, _ = self.simulation.history[-1]
        
        conserved_ratio = conserved_data["upper"] / (conserved_data["upper"] + conserved_data["lower"])
        violated_ratio = violated_data["upper"] / (violated_data["upper"] + violated_data["lower"])
        
        stats_text = f"""
        宇称守恒情况:
          上半球粒子: {conserved_data['upper']}
          下半球粒子: {conserved_data['lower']}
          比例: {conserved_ratio:.3f}
        
        宇称不守恒情况:
          上半球粒子: {violated_data['upper']}
          下半球粒子: {violated_data['lower']}
          比例: {violated_ratio:.3f}
        
        不对称度: {violated_ratio - conserved_ratio:.3f}
        """
        
        self.stats_label.setText(stats_text)
    
    def update_physics_info(self):
        if self.particle_type == "Co-60":
            info = """
            钴-60衰变实验 (吴健雄, 1957):
            - 衰变过程: Co-60 → Ni-60 + e- + ν̄e
            - 宇称不守恒表现: β衰变电子发射方向与核自旋方向相关
            - 实际不对称度: ~0.4
            - 历史意义: 首次实验验证宇称不守恒
            """
        elif self.particle_type == "π+":
            info = """
            π+介子衰变:
            - 衰变过程: π+ → μ+ + νμ
            - 宇称不守恒表现: μ+子极化与发射方向相关
            - 实际不对称度: ~0.3
            """
        elif self.particle_type == "Λ":
            info = """
            Λ超子衰变:
            - 衰变过程: Λ → p + π-
            - 宇称不守恒表现: 质子发射方向与超子自旋相关
            - 实际不对称度: ~0.2
            """
        
        self.physics_label.setText(info)
    
    def update_info_text(self):
        info = """
        <h2>宇称不守恒的物理背景</h2>
        
        <h3>历史背景</h3>
        <p>宇称不守恒是粒子物理学中的一个重大发现，由李政道和杨振宁于1956年提出，并在1957年由吴健雄通过钴-60衰变实验验证。这一发现推翻了长期以来认为物理定律在镜像变换下保持不变的基本假设，为此李政道和杨振宁获得了1957年诺贝尔物理学奖。</p>
        
        <h3>物理概念</h3>
        <p><b>宇称（Parity）</b>是描述物理系统在空间反演（镜像变换）下行为的性质。在弱相互作用中，物理过程在空间反演下不是对称的，这意味着物理系统与其镜像系统的行为不同。</p>
        
        <h3>实验验证</h3>
        <p>吴健雄的实验通过观察钴-60原子核β衰变中发射的电子的方向，发现了电子发射方向与原子核自旋方向的相关性，从而验证了宇称不守恒。</p>
        
        <h3>科学意义</h3>
        <p>宇称不守恒的发现是20世纪物理学最重要的突破之一，它不仅改变了我们对基本对称性的理解，也为后来的夸克模型和标准模型的发展奠定了基础。</p>
        
        <h3>本仿真说明</h3>
        <p>本程序通过模拟不同粒子衰变过程中的方向不对称性，直观展示了宇称不守恒现象。您可以通过调整参数观察不同条件下的不对称程度。</p>
        """
        
        self.info_text.setHtml(info)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 设置应用样式
    app.setStyle('Fusion')
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())