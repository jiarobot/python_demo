import sys
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QGroupBox, QLabel, QComboBox, 
                             QDoubleSpinBox, QPushButton, QSlider, QTextEdit,
                             QTabWidget, QSplitter)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont

class AtomSimulation:
    """原子物理仿真核心类"""
    
    def __init__(self):
        # 物理常数
        self.h = 6.626e-34  # 普朗克常数 (J·s)
        self.hbar = self.h / (2 * np.pi)  # 约化普朗克常数
        self.e = 1.602e-19  # 电子电荷 (C)
        self.m_e = 9.109e-31  # 电子质量 (kg)
        self.epsilon_0 = 8.854e-12  # 真空介电常数 (F/m)
        self.c = 3.0e8  # 光速 (m/s)
        self.k = 8.99e9  # 库伦常数 (N·m²/C²)
        
        # 原子参数
        self.atomic_number = 1  # 原子序数 (氢原子)
        self.energy_levels = 8  # 能级数量
        self.current_level = 1  # 当前能级
        
        # 轨道参数
        self.orbital_radius = []  # 轨道半径
        self.orbital_energy = []  # 轨道能量
        self.orbital_velocity = []  # 轨道速度
        
        # 计算初始轨道参数
        self.calculate_orbitals()
    
    def calculate_orbitals(self):
        """计算轨道参数"""
        self.orbital_radius = []
        self.orbital_energy = []
        self.orbital_velocity = []
        
        for n in range(1, self.energy_levels + 1):
            # 波尔半径公式: r_n = (4πϵ_0 ħ² n²) / (m_e e² Z)
            r_n = (4 * np.pi * self.epsilon_0 * self.hbar**2 * n**2) / \
                  (self.m_e * self.e**2 * self.atomic_number)
            self.orbital_radius.append(r_n * 1e12)  # 转换为皮米
            
            # 波尔能量公式: E_n = - (m_e e⁴ Z²) / (2 (4πϵ_0)² ħ² n²)
            E_n = - (self.m_e * self.e**4 * self.atomic_number**2) / \
                   (2 * (4 * np.pi * self.epsilon_0)**2 * self.hbar**2 * n**2)
            self.orbital_energy.append(E_n / self.e)  # 转换为电子伏特
            
            # 轨道速度: v_n = e² Z / (2 (4πϵ_0) ħ n)
            v_n = (self.e**2 * self.atomic_number) / \
                  (2 * (4 * np.pi * self.epsilon_0) * self.hbar * n)
            self.orbital_velocity.append(v_n / 1e6)  # 转换为千米/秒
    
    def set_atomic_number(self, Z):
        """设置原子序数"""
        self.atomic_number = Z
        self.calculate_orbitals()
    
    def get_transition_energy(self, n_i, n_f):
        """计算跃迁能量"""
        if n_i == n_f:
            return 0
        E_i = self.orbital_energy[n_i-1]
        E_f = self.orbital_energy[n_f-1]
        return E_f - E_i  # 电子伏特
    
    def get_transition_wavelength(self, n_i, n_f):
        """计算跃迁波长"""
        if n_i == n_f:
            return float('inf')
        delta_E = abs(self.get_transition_energy(n_i, n_f)) * self.e  # 转换为焦耳
        wavelength = (self.h * self.c) / delta_E  # 波长公式: λ = hc/ΔE
        return wavelength * 1e9  # 转换为纳米
    
    def get_photon_frequency(self, n_i, n_f):
        """计算光子频率"""
        if n_i == n_f:
            return 0
        wavelength = self.get_transition_wavelength(n_i, n_f)
        if wavelength == 0:
            return float('inf')
        return self.c / (wavelength * 1e-9)  # 频率


class AtomVisualization(FigureCanvas):
    """原子可视化组件"""
    
    def __init__(self, parent=None, width=5, height=5, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        super().__init__(self.fig)
        self.setParent(parent)
        
        self.atom_sim = None
        self.electron_angle = 0
        
        # 设置动画定时器
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_animation)
        self.animation_speed = 10
        
        self.init_plot()
    
    def set_simulation(self, atom_sim):
        """设置仿真对象"""
        self.atom_sim = atom_sim
        self.update_plot()
    
    def init_plot(self):
        """初始化绘图区域"""
        self.ax = self.fig.add_subplot(111)
        self.ax.set_aspect('equal')
        self.ax.set_xlim(-600, 600)
        self.ax.set_ylim(-600, 600)
        self.ax.set_xlabel('X (pm)')
        self.ax.set_ylabel('Y (pm)')
        self.ax.set_title('Bohr Atomic Model')
        self.ax.grid(True, alpha=0.3)
        
        # 初始化绘图元素
        self.nucleus = self.ax.plot([0], [0], 'ro', markersize=10, label='Nucleus')[0]
        self.electron = self.ax.plot([0], [0], 'bo', markersize=6, label='Electron')[0]
        self.orbit_lines = []
        self.energy_labels = []
        
        self.fig.tight_layout()
    
    def update_plot(self):
        """更新绘图"""
        if not self.atom_sim:
            return
            
        self.ax.clear()
        self.init_plot()
        
        # 绘制原子核
        self.ax.plot([0], [0], 'ro', markersize=10 + self.atom_sim.atomic_number, 
                    label=f'Nucleus (Z={self.atom_sim.atomic_number})')
        
        # 绘制轨道
        colors = plt.cm.viridis(np.linspace(0, 1, self.atom_sim.energy_levels))
        for i, radius in enumerate(self.atom_sim.orbital_radius):
            n = i + 1
            color = colors[i]
            
            # 绘制圆形轨道
            theta = np.linspace(0, 2*np.pi, 100)
            x = radius * np.cos(theta)
            y = radius * np.sin(theta)
            orbit_line, = self.ax.plot(x, y, '--', color=color, alpha=0.7, 
                                      label=f'n={n}')
            self.orbit_lines.append(orbit_line)
            
            # 添加能级标签
            energy_text = f'n={n}\nE={self.atom_sim.orbital_energy[i]:.2f} eV\nr={radius:.0f} pm'
            self.ax.text(radius, 0, energy_text, fontsize=8, 
                        ha='left', va='center', color=color)
        
        # 绘制电子
        current_radius = self.atom_sim.orbital_radius[self.atom_sim.current_level-1]
        x_e = current_radius * np.cos(self.electron_angle)
        y_e = current_radius * np.sin(self.electron_angle)
        self.electron = self.ax.plot(x_e, y_e, 'bo', markersize=8, 
                                   label=f'Electron (n={self.atom_sim.current_level})')[0]
        
        # 添加图例
        self.ax.legend(loc='upper right')
        
        self.draw()
    
    def update_animation(self):
        """更新动画"""
        if not self.atom_sim:
            return
            
        # 更新电子角度
        n = self.atom_sim.current_level
        velocity_factor = 1 / (n ** 3)  # 速度与n^3成反比
        self.electron_angle += 0.05 * velocity_factor * self.animation_speed / 10
        
        # 更新电子位置
        current_radius = self.atom_sim.orbital_radius[n-1]
        x_e = current_radius * np.cos(self.electron_angle)
        y_e = current_radius * np.sin(self.electron_angle)
        
        self.electron.set_data([x_e], [y_e])
        self.draw()
    
    def set_animation_speed(self, speed):
        """设置动画速度"""
        self.animation_speed = speed
    
    def start_animation(self):
        """开始动画"""
        self.timer.start(50)  # 20 FPS
    
    def stop_animation(self):
        """停止动画"""
        self.timer.stop()


class SpectrumVisualization(FigureCanvas):
    """光谱可视化组件"""
    
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        super().__init__(self.fig)
        self.setParent(parent)
        
        self.atom_sim = None
        self.init_plot()
    
    def set_simulation(self, atom_sim):
        """设置仿真对象"""
        self.atom_sim = atom_sim
        self.update_plot()
    
    def init_plot(self):
        """初始化绘图区域"""
        self.ax = self.fig.add_subplot(111)
        self.ax.set_xlabel('Wavelength (nm)')
        self.ax.set_ylabel('Intensity')
        self.ax.set_title('Atomic Emission Spectrum')
        self.ax.grid(True, alpha=0.3)
        
        self.fig.tight_layout()
    
    def update_plot(self):
        """更新光谱图"""
        if not self.atom_sim:
            return
            
        self.ax.clear()
        self.init_plot()
        
        # 计算所有可能的跃迁
        wavelengths = []
        intensities = []
        labels = []
        
        for n_i in range(1, self.atom_sim.energy_levels + 1):
            for n_f in range(1, n_i):
                wavelength = self.atom_sim.get_transition_wavelength(n_i, n_f)
                if wavelength < 10 or wavelength > 1000:  # 限制显示范围
                    continue
                    
                # 计算强度 (简化模型)
                intensity = 1.0 / (abs(n_i - n_f) ** 2)
                
                wavelengths.append(wavelength)
                intensities.append(intensity)
                labels.append(f'{n_i}→{n_f}')
        
        if wavelengths:
            # 绘制光谱线
            self.ax.vlines(wavelengths, 0, intensities, colors='blue', linewidth=2)
            
            # 添加标签
            for i, (w, inten, label) in enumerate(zip(wavelengths, intensities, labels)):
                self.ax.text(w, inten + 0.05, label, fontsize=8, 
                           ha='center', va='bottom', rotation=90)
            
            self.ax.set_xlim(0, max(wavelengths) * 1.1)
            self.ax.set_ylim(0, max(intensities) * 1.2)
        
        self.draw()


class EnergyLevelVisualization(FigureCanvas):
    """能级图可视化组件"""
    
    def __init__(self, parent=None, width=5, height=5, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        super().__init__(self.fig)
        self.setParent(parent)
        
        self.atom_sim = None
        self.init_plot()
    
    def set_simulation(self, atom_sim):
        """设置仿真对象"""
        self.atom_sim = atom_sim
        self.update_plot()
    
    def init_plot(self):
        """初始化绘图区域"""
        self.ax = self.fig.add_subplot(111)
        self.ax.set_xlabel('Energy Level')
        self.ax.set_ylabel('Energy (eV)')
        self.ax.set_title('Energy Level Diagram')
        self.ax.grid(True, alpha=0.3)
        
        self.fig.tight_layout()
    
    def update_plot(self):
        """更新能级图"""
        if not self.atom_sim:
            return
            
        self.ax.clear()
        self.init_plot()
        
        # 绘制能级
        levels = range(1, self.atom_sim.energy_levels + 1)
        energies = self.atom_sim.orbital_energy
        
        self.ax.hlines(energies, 0, 1, colors='red', linewidth=2)
        
        # 添加能级标签
        for i, (n, energy) in enumerate(zip(levels, energies)):
            self.ax.text(0.5, energy, f'n={n}\nE={energy:.2f} eV', 
                        fontsize=9, ha='center', va='bottom' if i == 0 else 'top')
        
        # 标记当前能级
        current_energy = energies[self.atom_sim.current_level - 1]
        self.ax.plot(0.5, current_energy, 'bo', markersize=10, label='Current Level')
        
        self.ax.set_xlim(0, 1)
        self.ax.set_ylim(min(energies) - 1, 0)
        self.ax.legend()
        
        self.draw()


class BohrAtomicSimulator(QMainWindow):
    """波尔原子模型仿真主窗口"""
    
    def __init__(self):
        super().__init__()
        self.atom_sim = AtomSimulation()
        self.init_ui()
        
    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle('Bohr Atomic Model Simulator')
        self.setGeometry(100, 100, 1400, 900)
        
        # 创建中央部件和主布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # 创建左侧控制面板
        control_panel = self.create_control_panel()
        main_layout.addWidget(control_panel, 1)
        
        # 创建右侧可视化区域
        viz_splitter = QSplitter(Qt.Vertical)
        main_layout.addWidget(viz_splitter, 3)
        
        # 创建原子模型可视化
        self.atom_viz = AtomVisualization(self, width=6, height=6)
        viz_splitter.addWidget(self.atom_viz)
        self.atom_viz.set_simulation(self.atom_sim)
        
        # 创建底部标签页
        bottom_tabs = QTabWidget()
        viz_splitter.addWidget(bottom_tabs)
        
        # 光谱标签页
        self.spectrum_viz = SpectrumVisualization(self, width=6, height=4)
        bottom_tabs.addTab(self.spectrum_viz, "Emission Spectrum")
        self.spectrum_viz.set_simulation(self.atom_sim)
        
        # 能级图标签页
        self.energy_viz = EnergyLevelVisualization(self, width=6, height=4)
        bottom_tabs.addTab(self.energy_viz, "Energy Levels")
        self.energy_viz.set_simulation(self.atom_sim)
        
        # 信息显示标签页
        self.info_display = QTextEdit()
        self.info_display.setReadOnly(True)
        bottom_tabs.addTab(self.info_display, "Information")
        
        # 设置分割比例
        viz_splitter.setSizes([500, 400])
        
        # 启动动画
        self.atom_viz.start_animation()
        
        # 更新初始信息
        self.update_info_display()
    
    def create_control_panel(self):
        """创建控制面板"""
        control_panel = QWidget()
        layout = QVBoxLayout(control_panel)
        
        # 原子选择组
        atom_group = QGroupBox("Atom Selection")
        atom_layout = QVBoxLayout(atom_group)
        
        atom_layout.addWidget(QLabel("Atomic Number (Z):"))
        self.atom_combo = QComboBox()
        for i in range(1, 11):  # 1到10号元素
            self.atom_combo.addItem(f"{i} - {self.get_element_name(i)}", i)
        self.atom_combo.currentIndexChanged.connect(self.on_atom_changed)
        atom_layout.addWidget(self.atom_combo)
        
        layout.addWidget(atom_group)
        
        # 能级控制组
        level_group = QGroupBox("Energy Level Control")
        level_layout = QVBoxLayout(level_group)
        
        level_layout.addWidget(QLabel("Current Energy Level:"))
        self.level_slider = QSlider(Qt.Horizontal)
        self.level_slider.setMinimum(1)
        self.level_slider.setMaximum(self.atom_sim.energy_levels)
        self.level_slider.setValue(self.atom_sim.current_level)
        self.level_slider.valueChanged.connect(self.on_level_changed)
        level_layout.addWidget(self.level_slider)
        
        self.level_label = QLabel(f"n = {self.atom_sim.current_level}")
        level_layout.addWidget(self.level_label)
        
        # 跃迁控制
        level_layout.addWidget(QLabel("Transition:"))
        transition_layout = QHBoxLayout()
        
        self.transition_from = QComboBox()
        self.transition_to = QComboBox()
        self.update_transition_combos()
        
        transition_layout.addWidget(QLabel("From:"))
        transition_layout.addWidget(self.transition_from)
        transition_layout.addWidget(QLabel("To:"))
        transition_layout.addWidget(self.transition_to)
        
        level_layout.addLayout(transition_layout)
        
        self.transition_button = QPushButton("Apply Transition")
        self.transition_button.clicked.connect(self.on_transition)
        level_layout.addWidget(self.transition_button)
        
        layout.addWidget(level_group)
        
        # 动画控制组
        anim_group = QGroupBox("Animation Control")
        anim_layout = QVBoxLayout(anim_group)
        
        anim_layout.addWidget(QLabel("Animation Speed:"))
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setMinimum(1)
        self.speed_slider.setMaximum(20)
        self.speed_slider.setValue(10)
        self.speed_slider.valueChanged.connect(self.on_speed_changed)
        anim_layout.addWidget(self.speed_slider)
        
        self.anim_toggle = QPushButton("Pause Animation")
        self.anim_toggle.clicked.connect(self.toggle_animation)
        anim_layout.addWidget(self.anim_toggle)
        
        layout.addWidget(anim_group)
        
        # 信息显示组
        info_group = QGroupBox("Transition Information")
        info_layout = QVBoxLayout(info_group)
        
        self.transition_info = QLabel("Select a transition to see details")
        self.transition_info.setWordWrap(True)
        info_layout.addWidget(self.transition_info)
        
        layout.addWidget(info_group)
        
        # 添加弹性空间
        layout.addStretch(1)
        
        return control_panel
    
    def get_element_name(self, atomic_number):
        """获取元素名称"""
        elements = {
            1: "Hydrogen", 2: "Helium", 3: "Lithium", 4: "Beryllium", 
            5: "Boron", 6: "Carbon", 7: "Nitrogen", 8: "Oxygen", 
            9: "Fluorine", 10: "Neon"
        }
        return elements.get(atomic_number, f"Element {atomic_number}")
    
    def update_transition_combos(self):
        """更新跃迁组合框"""
        self.transition_from.clear()
        self.transition_to.clear()
        
        for n in range(1, self.atom_sim.energy_levels + 1):
            self.transition_from.addItem(f"n={n}", n)
            self.transition_to.addItem(f"n={n}", n)
        
        # 设置默认值
        self.transition_from.setCurrentIndex(1)  # n=2
        self.transition_to.setCurrentIndex(0)   # n=1
    
    def on_atom_changed(self):
        """原子选择改变事件"""
        Z = self.atom_combo.currentData()
        self.atom_sim.set_atomic_number(Z)
        
        # 更新能级滑块最大值
        self.level_slider.setMaximum(self.atom_sim.energy_levels)
        
        # 更新可视化
        self.atom_viz.update_plot()
        self.spectrum_viz.update_plot()
        self.energy_viz.update_plot()
        
        # 更新跃迁组合框
        self.update_transition_combos()
        
        # 更新信息显示
        self.update_info_display()
    
    def on_level_changed(self, value):
        """能级改变事件"""
        self.atom_sim.current_level = value
        self.level_label.setText(f"n = {value}")
        
        # 更新可视化
        self.atom_viz.update_plot()
        self.energy_viz.update_plot()
        
        # 更新信息显示
        self.update_info_display()
    
    def on_transition(self):
        """跃迁事件"""
        n_from = self.transition_from.currentData()
        n_to = self.transition_to.currentData()
        
        if n_from == n_to:
            self.transition_info.setText("No transition: initial and final levels are the same")
            return
        
        # 计算跃迁参数
        energy = self.atom_sim.get_transition_energy(n_from, n_to)
        wavelength = self.atom_sim.get_transition_wavelength(n_from, n_to)
        frequency = self.atom_sim.get_photon_frequency(n_from, n_to)
        
        # 显示跃迁信息
        if n_from > n_to:
            transition_type = "Emission"
            photon_energy = abs(energy)
        else:
            transition_type = "Absorption"
            photon_energy = abs(energy)
        
        info_text = f"""
        <b>{transition_type} Transition:</b> n={n_from} → n={n_to}
        <br>Energy Change: {energy:.4f} eV
        <br>Photon Energy: {photon_energy:.4f} eV
        <br>Wavelength: {wavelength:.2f} nm
        <br>Frequency: {frequency:.2e} Hz
        """
        
        self.transition_info.setText(info_text)
        
        # 如果是从高能级到低能级，更新当前能级
        if n_from > n_to:
            self.level_slider.setValue(n_to)
            self.atom_sim.current_level = n_to
            self.level_label.setText(f"n = {n_to}")
            
            # 更新可视化
            self.atom_viz.update_plot()
            self.energy_viz.update_plot()
    
    def on_speed_changed(self, value):
        """动画速度改变事件"""
        self.atom_viz.set_animation_speed(value)
    
    def toggle_animation(self):
        """切换动画状态"""
        if self.atom_viz.timer.isActive():
            self.atom_viz.stop_animation()
            self.anim_toggle.setText("Resume Animation")
        else:
            self.atom_viz.start_animation()
            self.anim_toggle.setText("Pause Animation")
    
    def update_info_display(self):
        """更新信息显示"""
        Z = self.atom_sim.atomic_number
        n = self.atom_sim.current_level
        
        info_text = f"""
        <h2>Bohr Atomic Model Simulation</h2>
        
        <h3>Atom Information:</h3>
        <b>Element:</b> {self.get_element_name(Z)} (Z={Z})<br>
        <b>Current Energy Level:</b> n={n}<br>
        <b>Orbital Radius:</b> {self.atom_sim.orbital_radius[n-1]:.2f} pm<br>
        <b>Orbital Energy:</b> {self.atom_sim.orbital_energy[n-1]:.4f} eV<br>
        <b>Orbital Velocity:</b> {self.atom_sim.orbital_velocity[n-1]:.2f} km/s<br>
        
        <h3>Physical Constants:</h3>
        Planck's Constant (h): {self.atom_sim.h:.3e} J·s<br>
        Electron Charge (e): {self.atom_sim.e:.3e} C<br>
        Electron Mass (m_e): {self.atom_sim.m_e:.3e} kg<br>
        Speed of Light (c): {self.atom_sim.c:.3e} m/s<br>
        
        <h3>Bohr Model Equations:</h3>
        <b>Orbital Radius:</b> r_n = (4πϵ₀ ħ² n²) / (m_e e² Z)<br>
        <b>Orbital Energy:</b> E_n = - (m_e e⁴ Z²) / (2 (4πϵ₀)² ħ² n²)<br>
        <b>Photon Wavelength:</b> λ = hc / |ΔE|<br>
        """
        
        self.info_display.setHtml(info_text)


def main():
    """主函数"""
    app = QApplication(sys.argv)
    
    # 设置应用样式
    app.setStyle('Fusion')
    
    # 创建并显示主窗口
    window = BohrAtomicSimulator()
    window.show()
    
    # 运行应用
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()