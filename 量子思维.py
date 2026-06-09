import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.patches import Circle, Ellipse
import matplotlib.gridspec as gridspec
from scipy import signal
from scipy.integrate import odeint
import warnings
warnings.filterwarnings('ignore')

plt.rcParams['font.sans-serif'] = ['Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False

class QuantumConsciousnessVisualizer:
    def __init__(self):
        self.fig = plt.figure(figsize=(20, 12))
        self.setup_layout()
        
    def setup_layout(self):
        """设置可视化布局"""
        gs = gridspec.GridSpec(3, 3, figure=self.fig)
        
        # 定义各个子图位置
        self.ax_quantum_observer = self.fig.add_subplot(gs[0, 0])
        self.ax_five_thieves = self.fig.add_subplot(gs[0, 1])
        self.ax_fractal_breathing = self.fig.add_subplot(gs[0, 2])
        self.ax_entanglement = self.fig.add_subplot(gs[1, 0])
        self.ax_decoherence = self.fig.add_subplot(gs[1, 1])
        self.ax_meditation_waves = self.fig.add_subplot(gs[1, 2])
        self.ax_holographic = self.fig.add_subplot(gs[2, :])
        
        self.fig.suptitle('《黄帝阴符经》量子意识修行可视化系统\nQuantum Consciousness Visualization of Huangdi Yinfu Jing', 
                         fontsize=16, fontweight='bold', y=0.95)
    
    def quantum_observer_effect(self, frame):
        """量子观测者效应模拟"""
        self.ax_quantum_observer.clear()
        
        # 双缝实验模拟
        x = np.linspace(-10, 10, 1000)
        wavelength = 2.0
        
        # 未观测时的波函数（干涉图案）
        slit1 = np.exp(-(x - 2)**2 / 0.5) * np.sin(2 * np.pi * x / wavelength)
        slit2 = np.exp(-(x + 2)**2 / 0.5) * np.sin(2 * np.pi * x / wavelength + np.pi/4)
        wave_unobserved = slit1 + slit2
        
        # 观测时的粒子行为
        particle_positions = np.random.normal(0, 3, 50)
        
        if frame % 120 < 60:  # 未观测状态
            self.ax_quantum_observer.plot(x, wave_unobserved, 'b-', linewidth=2, label='未观测: 波函数叠加')
            self.ax_quantum_observer.fill_between(x, wave_unobserved, alpha=0.3, color='blue')
            title = "未观测状态: 波函数叠加 (量子潜能)"
        else:  # 观测状态
            self.ax_quantum_observer.hist(particle_positions, bins=20, density=True, 
                                        alpha=0.7, color='red', label='观测: 波函数坍缩')
            title = "观测状态: 波函数坍缩 (现实显现)"
        
        self.ax_quantum_observer.set_title(f'量子观测者效应\n"{title}"', fontsize=12)
        self.ax_quantum_observer.set_xlabel('位置')
        self.ax_quantum_observer.set_ylabel('概率幅')
        self.ax_quantum_observer.legend()
        self.ax_quantum_observer.grid(True, alpha=0.3)
    
    def five_thieves_simulation(self, frame):
        """五贼干扰模拟"""
        self.ax_five_thieves.clear()
        
        thieves = ['色', '声', '香', '味', '触']
        intensities = np.array([0.8, 0.6, 0.4, 0.7, 0.9]) + 0.2 * np.sin(frame * 0.1 + np.arange(5))
        
        # 量子意识状态
        consciousness_radius = 1.0 - 0.3 * np.mean(intensities)
        
        # 绘制五贼干扰
        angles = np.linspace(0, 2*np.pi, 6)[:-1]
        for i, (thief, intensity, angle) in enumerate(zip(thieves, intensities, angles)):
            x = 2.5 * np.cos(angle)
            y = 2.5 * np.sin(angle)
            
            # 干扰波
            interference_x = np.linspace(x, 0, 50)
            interference_y = np.linspace(y, 0, 50)
            self.ax_five_thieves.plot(interference_x, interference_y, 'r-', alpha=intensity*0.7)
            
            # 干扰源
            self.ax_five_thieves.text(x*1.2, y*1.2, thief, fontsize=20, 
                                    ha='center', va='center', color='red',
                                    bbox=dict(boxstyle="circle,pad=0.3", fc='red', alpha=0.3))
        
        # 中心意识
        consciousness = Circle((0, 0), consciousness_radius, fill=True, 
                             alpha=0.7, color='blue', label='清净意识')
        self.ax_five_thieves.add_patch(consciousness)
        
        protected_radius = 0.3
        protection = Circle((0, 0), protected_radius, fill=True, 
                          alpha=0.9, color='green', label='量子防护罩')
        self.ax_five_thieves.add_patch(protection)
        
        self.ax_five_thieves.set_xlim(-3, 3)
        self.ax_five_thieves.set_ylim(-3, 3)
        self.ax_five_thieves.set_aspect('equal')
        self.ax_five_thieves.set_title('五贼干扰与量子防护罩\n"天有五贼，见之者昌"', fontsize=12)
        self.ax_five_thieves.legend()
        self.ax_five_thieves.grid(True, alpha=0.3)
    
    def fractal_breathing_visualization(self, frame):
        """分形呼吸法可视化"""
        self.ax_fractal_breathing.clear()
        
        # 黄金分割比
        phi = (1 + np.sqrt(5)) / 2
        
        # 呼吸周期
        breath_phase = (frame % 100) / 100 * 2 * np.pi
        
        # 吸气（减熵）- 分形向内凝聚
        if np.sin(breath_phase) > 0:
            # 吸气阶段 - 分形向内
            scale = 0.5 + 0.3 * np.sin(breath_phase)
            color = 'blue'
            title_phase = "吸气: 能量凝聚 (减熵)"
        else:
            # 呼气阶段 - 分形展开
            scale = 0.8 + 0.2 * np.sin(breath_phase)
            color = 'red'
            title_phase = "呼气: 能量弥散 (可控增熵)"
        
        # 生成分形模式
        x = np.linspace(-2, 2, 300)
        y = np.linspace(-2, 2, 300)
        X, Y = np.meshgrid(x, y)
        
        # 曼德博集合风格的分形
        Z = self.mandelbrot_fractal(X, Y, scale, breath_phase)
        
        im = self.ax_fractal_breathing.imshow(Z, extent=[-2, 2, -2, 2], 
                                            cmap='viridis', alpha=0.8)
        
        # 添加呼吸节奏指示器
        theta = np.linspace(0, 2*np.pi, 100)
        breath_circle = 1.5 * np.array([np.cos(theta), np.sin(theta)])
        self.ax_fractal_breathing.plot(breath_circle[0], breath_circle[1], 'w-', alpha=0.5)
        
        # 当前呼吸位置
        current_angle = breath_phase
        marker_x = 1.5 * np.cos(current_angle)
        marker_y = 1.5 * np.sin(current_angle)
        self.ax_fractal_breathing.plot(marker_x, marker_y, 'ro', markersize=10)
        
        self.ax_fractal_breathing.set_title(f'分形呼吸能量调节\n"{title_phase}"', fontsize=12)
        self.ax_fractal_breathing.set_xlabel('沉水入火，自取灭亡 → 熵平衡术')
    
    def mandelbrot_fractal(self, X, Y, scale, phase):
        """生成曼德博分形"""
        Z = np.zeros(X.shape)
        for i in range(X.shape[0]):
            for j in range(X.shape[1]):
                x0 = X[i,j] * scale
                y0 = Y[i,j] * scale
                x = 0.0
                y = 0.0
                iteration = 0
                max_iteration = 50
                
                while (x*x + y*y <= 4 and iteration < max_iteration):
                    xtemp = x*x - y*y + x0
                    y = 2*x*y + y0 + 0.1*np.sin(phase)
                    x = xtemp
                    iteration += 1
                
                Z[i,j] = iteration
        return Z
    
    def quantum_entanglement_simulation(self, frame):
        """量子纠缠意象观模拟"""
        self.ax_entanglement.clear()
        
        # 两个纠缠的量子态
        t = np.linspace(0, 4*np.pi, 200)
        
        # 纠缠波函数
        psi1 = np.sin(t + frame*0.1)
        psi2 = np.sin(t + frame*0.1 + np.pi)  # 反相关
        
        # 意识观测点
        observation_point = 100 + int(50 * np.sin(frame*0.05))
        
        # 绘制纠缠态
        self.ax_entanglement.plot(t, psi1 + 2, 'b-', linewidth=2, label='意念A (手心)')
        self.ax_entanglement.plot(t, psi2 - 2, 'g-', linewidth=2, label='意念B (星空)')
        
        # 显示纠缠关联
        self.ax_entanglement.plot([t[observation_point], t[observation_point]], 
                                [psi1[observation_point] + 2, psi2[observation_point] - 2], 
                                'r--', alpha=0.7, label='量子纠缠关联')
        
        # 观测点标记
        self.ax_entanglement.plot(t[observation_point], psi1[observation_point] + 2, 'ro', markersize=8)
        self.ax_entanglement.plot(t[observation_point], psi2[observation_point] - 2, 'ro', markersize=8)
        
        self.ax_entanglement.set_ylim(-4, 4)
        self.ax_entanglement.set_title('量子纠缠意象观训练\n"不知不神之所以神"', fontsize=12)
        self.ax_entanglement.set_xlabel('时间')
        self.ax_entanglement.set_ylabel('量子态幅值')
        self.ax_entanglement.legend()
        self.ax_entanglement.grid(True, alpha=0.3)
    
    def decoherence_simulation(self, frame):
        """退相干过程模拟"""
        self.ax_decoherence.clear()
        
        time = np.linspace(0, 10, 200)
        
        # 初始量子叠加态
        quantum_state = np.exp(1j * 2 * np.pi * time) * np.exp(-time / 5)
        
        # 环境噪声（五贼干扰）
        noise_level = 0.5 + 0.3 * np.sin(frame * 0.1)
        environmental_noise = noise_level * np.random.normal(0, 1, len(time))
        
        # 退相干过程
        decoherence_time = 3.0
        coherence = np.exp(-time / decoherence_time)
        
        # 受干扰的量子态
        disturbed_state = quantum_state * coherence + environmental_noise
        
        # 绘制
        self.ax_decoherence.plot(time, np.real(quantum_state), 'b-', 
                               label='纯净量子态', linewidth=2)
        self.ax_decoherence.plot(time, np.real(disturbed_state), 'r-', 
                               label='退相干态', linewidth=2)
        self.ax_decoherence.plot(time, environmental_noise, 'g--', 
                               alpha=0.5, label='环境噪声(五贼)')
        
        self.ax_decoherence.fill_between(time, np.real(disturbed_state), 
                                       environmental_noise, alpha=0.2, color='red')
        
        self.ax_decoherence.set_title('意识退相干过程\n"五贼干扰导致量子潜能丧失"', fontsize=12)
        self.ax_decoherence.set_xlabel('时间')
        self.ax_decoherence.set_ylabel('量子相干性')
        self.ax_decoherence.legend()
        self.ax_decoherence.grid(True, alpha=0.3)
    
    def meditation_brainwaves(self, frame):
        """冥想脑波模拟"""
        self.ax_meditation_waves.clear()
        
        t = np.linspace(0, 4, 500)
        
        # 不同意识状态的脑波
        beta_wave = 0.3 * np.sin(20 * 2 * np.pi * t)  # 日常β波
        alpha_wave = 0.5 * np.sin(10 * 2 * np.pi * t)  # 放松α波
        theta_wave = 0.7 * np.sin(5 * 2 * np.pi * t)   # 冥想θ波
        gamma_wave = 0.9 * np.sin(40 * 2 * np.pi * t)  # 悟道γ波
        
        # 冥想效果增强
        meditation_effect = 0.5 + 0.5 * np.sin(frame * 0.05)
        
        # 综合脑波
        if frame < 50:
            composite_wave = beta_wave
            state = "日常状态 (β波)"
        elif frame < 100:
            composite_wave = 0.5*beta_wave + 0.5*alpha_wave
            state = "放松状态 (α波)"
        elif frame < 150:
            composite_wave = 0.2*beta_wave + 0.3*alpha_wave + 0.5*theta_wave
            state = "冥想状态 (θ波)"
        else:
            composite_wave = 0.1*beta_wave + 0.2*alpha_wave + 0.3*theta_wave + 0.4*gamma_wave*meditation_effect
            state = "深度悟道 (γ波增强)"
        
        self.ax_meditation_waves.plot(t, composite_wave, 'purple', linewidth=2)
        self.ax_meditation_waves.set_ylim(-2, 2)
        self.ax_meditation_waves.set_title(f'冥想脑波变化: {state}\n神经相干性增强', fontsize=12)
        self.ax_meditation_waves.set_xlabel('时间')
        self.ax_meditation_waves.set_ylabel('脑波幅值')
        self.ax_meditation_waves.grid(True, alpha=0.3)
    
    def holographic_universe(self, frame):
        """全息宇宙可视化"""
        self.ax_holographic.clear()
        
        # 生成全息模式
        x = np.linspace(-5, 5, 300)
        y = np.linspace(-5, 5, 300)
        X, Y = np.meshgrid(x, y)
        
        # 全息干涉图案
        R = np.sqrt(X**2 + Y**2)
        theta = np.arctan2(Y, X)
        
        # 动态全息图
        Z = np.cos(5 * theta + frame * 0.1) * np.sin(3 * R + frame * 0.05) * np.exp(-R/4)
        
        im = self.ax_holographic.imshow(Z, extent=[-5, 5, -5, 5], 
                                      cmap='plasma', alpha=0.9)
        
        # 添加局部与整体的关联线
        for i in range(0, 300, 50):
            self.ax_holographic.plot([x[i], 0], [y[i], 0], 'w-', alpha=0.2, linewidth=0.5)
        
        # 中心意识点
        self.ax_holographic.plot(0, 0, 'ro', markersize=10, label='个体意识')
        
        self.ax_holographic.set_title('全息宇宙原理: "宇宙在乎手，万化生乎身"\n局部蕴含整体信息', fontsize=14)
        self.ax_holographic.legend()
    
    def update(self, frame):
        """更新所有可视化"""
        self.quantum_observer_effect(frame)
        self.five_thieves_simulation(frame)
        self.fractal_breathing_visualization(frame)
        self.quantum_entanglement_simulation(frame)
        self.decoherence_simulation(frame)
        self.meditation_brainwaves(frame)
        self.holographic_universe(frame)
        
        # 添加整体进度指示
        progress = (frame % 200) / 200
        self.fig.text(0.02, 0.02, f'修行进度: {progress:.1%}', 
                     transform=self.fig.transFigure, fontsize=10,
                     bbox=dict(boxstyle="round,pad=0.3", fc="lightblue"))
    
    def animate(self, frames=200, interval=100):
        """运行动画"""
        anim = FuncAnimation(self.fig, self.update, frames=frames, 
                           interval=interval, repeat=True)
        plt.tight_layout()
        plt.show()
        return anim

# 创建并运行可视化系统
if __name__ == "__main__":
    print("启动《阴符经》量子意识修行可视化系统...")
    print("包含七大模块:")
    print("1. 量子观测者效应 - 展示意识对现实的塑造")
    print("2. 五贼干扰模拟 - 感官输入对量子态的干扰")  
    print("3. 分形呼吸法 - 能量调节的熵平衡术")
    print("4. 量子纠缠训练 - 非定域意识开发")
    print("5. 退相干过程 - 环境噪声对量子潜能的影响")
    print("6. 冥想脑波 - 不同意识状态的神经特征")
    print("7. 全息宇宙 - 局部与整体的量子关联")
    print("\n系统运行中...")
    
    visualizer = QuantumConsciousnessVisualizer()
    anim = visualizer.animate(frames=200, interval=100)