import numpy as np
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from matplotlib.animation import FuncAnimation
from matplotlib.widgets import Slider, Button
from sklearn.decomposition import PCA
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import ipywidgets as widgets
from IPython.display import display

# ======================
# 算法核心组件模拟
# ======================

class ASE2Simulator:
    def __init__(self):
        # 多尺度系统参数
        self.scales = np.linspace(0.1, 2.0, 20)  # 控制尺度
        self.time = np.linspace(0, 10, 1000)
        
        # 初始系统状态 (Lorenz吸引子模拟复杂系统)
        self.x = np.zeros(len(self.time))
        self.y = np.zeros(len(self.time))
        self.z = np.zeros(len(self.time))
        
        # 控制参数
        self.current_scale = 1.0
        self.chaos_level = 0.5
        self.structure_coherence = 0.3
        self.controllability_potential = np.zeros(len(self.scales))
        
        # 目标状态
        self.target_manifold = None
        
        # 历史记录
        self.history = {
            'scale': [],
            'entropy': [],
            'cep': [],
            'control_actions': [],
            'structure_coherence': []
        }
    
    def update_system(self, sigma=10.0, rho=28.0, beta=8/3):
        """更新Lorenz系统状态"""
        dt = self.time[1] - self.time[0]
        for i in range(1, len(self.time)):
            dx = sigma * (self.y[i-1] - self.x[i-1])
            dy = self.x[i-1] * (rho - self.z[i-1]) - self.y[i-1]
            dz = self.x[i-1] * self.y[i-1] - beta * self.z[i-1]
            
            # 添加控制影响
            control_strength = 0.5 * np.exp(-0.5*(self.scales - self.current_scale)**2/(0.2**2))
            control_effect = np.sum(control_strength) * self.structure_coherence
            
            self.x[i] = self.x[i-1] + dx * dt + control_effect * np.random.normal(0, 0.1)
            self.y[i] = self.y[i-1] + dy * dt + control_effect * np.random.normal(0, 0.1)
            self.z[i] = self.z[i-1] + dz * dt
    
    def calculate_multiscale_entropy(self):
        """计算多尺度熵 (简化版本)"""
        entropies = []
        for scale in self.scales:
            # 简化计算 - 实际中会使用小波变换
            scaled_data = self.z[::int(scale*10)]
            if len(scaled_data) < 10:
                entropy = 0
            else:
                hist, _ = np.histogram(scaled_data, bins=20)
                prob = hist / hist.sum()
                entropy = -np.sum(prob * np.log(prob + 1e-10))
            entropies.append(entropy)
        return np.array(entropies)
    
    def calculate_cep(self, entropies):
        """计算可控性涌现潜力"""
        # 与当前尺度的距离
        scale_dist = np.exp(-0.5*(self.scales - self.current_scale)**2/(0.5**2))
        
        # 可预测性 - 熵越低通常越可预测
        predictability = 1 / (entropies + 0.1)
        
        # 目标相关性 - 假设目标是稳定在z=30附近
        target_error = np.abs(np.mean(self.z) - 30)
        relevance = np.exp(-0.1 * target_error)
        
        # 综合CEP
        cep = scale_dist * predictability * relevance
        return cep
    
    def apply_weak_constraints(self, cep):
        """应用弱约束引导系统"""
        # 选择最优尺度
        optimal_scale = self.scales[np.argmax(cep)]
        
        # 计算到混沌边缘的距离
        mean_entropy = np.mean(self.calculate_multiscale_entropy())
        chaos_distance = np.abs(mean_entropy - self.chaos_level)
        
        # 根据距离调整控制
        if chaos_distance > 0.3:
            # 远离混沌边缘 - 施加更强的引导
            self.current_scale = optimal_scale
            self.structure_coherence = min(1.0, self.structure_coherence + 0.05)
        else:
            # 接近混沌边缘 - 允许更多探索
            self.current_scale = optimal_scale + np.random.normal(0, 0.1)
            self.structure_coherence = max(0.1, self.structure_coherence - 0.02)
        
        # 记录历史
        self.history['scale'].append(self.current_scale)
        self.history['entropy'].append(mean_entropy)
        self.history['cep'].append(np.max(cep))
        self.history['control_actions'].append(chaos_distance)
        self.history['structure_coherence'].append(self.structure_coherence)
        
        return optimal_scale, chaos_distance
    
    def evolve_system(self):
        """执行一个完整的ASE²循环"""
        # 更新系统状态
        self.update_system()
        
        # 多尺度熵计算
        entropies = self.calculate_multiscale_entropy()
        
        # 计算CEP
        cep = self.calculate_cep(entropies)
        self.controllability_potential = cep
        
        # 应用弱约束
        optimal_scale, chaos_distance = self.apply_weak_constraints(cep)
        
        return entropies, cep, optimal_scale, chaos_distance

# ======================
# 可视化系统
# ======================

class ASE2Visualizer:
    def __init__(self):
        self.sim = ASE2Simulator()
        self.fig = plt.figure(figsize=(16, 12), facecolor='#1e1e1e')
        self.gs = GridSpec(3, 2, figure=self.fig, 
                          width_ratios=[1.2, 1], height_ratios=[1, 1, 1])
        
        # 创建子图
        self.ax1 = self.fig.add_subplot(self.gs[0, 0], projection='3d')  # 3D系统状态
        self.ax2 = self.fig.add_subplot(self.gs[1, 0])  # 熵-尺度地形图
        self.ax3 = self.fig.add_subplot(self.gs[2, 0])  # CEP可视化
        self.ax4 = self.fig.add_subplot(self.gs[:, 1])  # 控制面板/结构演化
        
        # 美化设置
        for ax in [self.ax1, self.ax2, self.ax3, self.ax4]:
            ax.set_facecolor('#2d2d2d')
            ax.tick_params(colors='white')
            for spine in ax.spines.values():
                spine.set_color('gray')
        
        # 初始绘图
        self.initialize_plots()
        
        # 添加控制滑块
        self.add_controls()
        
    def initialize_plots(self):
        """初始化所有绘图元素"""
        # 3D系统状态图
        self.ax1.clear()
        self.ax1.set_title('Complex System State (Lorenz Attractor)', color='white', pad=10)
        self.system_plot = self.ax1.plot([], [], [], 'cyan', alpha=0.8)[0]
        self.current_point = self.ax1.plot([], [], [], 'ro', markersize=8)[0]
        self.ax1.grid(True, alpha=0.2)
        self.ax1.set_xlabel('X', color='white')
        self.ax1.set_ylabel('Y', color='white')
        self.ax1.set_zlabel('Z', color='white')
        
        # 熵-尺度地形图
        self.ax2.clear()
        self.ax2.set_title('Multiscale Entropy Topography', color='white', pad=10)
        self.entropy_plot = self.ax2.plot([], [], 'mo-', linewidth=2)[0]
        self.optimal_scale_line = self.ax2.axvline(0, color='yellow', linestyle='--', alpha=0)
        self.ax2.set_xlabel('Control Scale', color='white')
        self.ax2.set_ylabel('Entropy', color='white')
        self.ax2.grid(True, alpha=0.2)
        
        # CEP可视化
        self.ax3.clear()
        self.ax3.set_title('Controllability Emergence Potential (CEP)', color='white', pad=10)
        self.cep_plot = self.ax3.plot([], [], 'go-', linewidth=2)[0]
        self.optimal_scale_marker = self.ax3.plot([], [], 'yo', markersize=10)[0]
        self.ax3.set_xlabel('Control Scale', color='white')
        self.ax3.set_ylabel('CEP', color='white')
        self.ax3.grid(True, alpha=0.2)
        
        # 控制面板/结构演化
        self.ax4.clear()
        self.ax4.set_title('System Structure Evolution & Control Metrics', color='white', pad=10)
        self.ax4.axis('off')
        
        # 创建内部网格用于控制面板
        inner_grid = self.ax4.inset_axes([0.05, 0.05, 0.9, 0.9])
        inner_grid.set_facecolor('#3d3d3d')
        inner_grid.axis('off')
        
        # 添加文本指标
        self.metrics_text = inner_grid.text(0.05, 0.85, "", color='cyan', fontsize=10)
        
        # 添加结构相干性图
        self.structure_ax = inner_grid.inset_axes([0.05, 0.4, 0.4, 0.4])
        self.structure_ax.set_title('Structure Coherence', color='white', fontsize=10)
        self.structure_plot, = self.structure_ax.plot([], [], 'c-')
        self.structure_ax.set_ylim(0, 1)
        self.structure_ax.grid(True, alpha=0.2)
        self.structure_ax.tick_params(colors='white')
        
        # 添加混沌边缘距离图
        self.chaos_ax = inner_grid.inset_axes([0.55, 0.4, 0.4, 0.4])
        self.chaos_ax.set_title('Distance to Chaos Edge', color='white', fontsize=10)
        self.chaos_plot, = self.chaos_ax.plot([], [], 'm-')
        self.chaos_ax.set_ylim(0, 1)
        self.chaos_ax.grid(True, alpha=0.2)
        self.chaos_ax.tick_params(colors='white')
        
        # 添加网络结构图
        self.network_ax = inner_grid.inset_axes([0.2, 0.05, 0.6, 0.25])
        self.network_ax.set_title('Emergent Control Structure', color='white', fontsize=10)
        self.network_ax.axis('off')
        self.network_img = self.network_ax.imshow(np.random.rand(10, 10), cmap='viridis', 
                                                interpolation='gaussian', alpha=0.8)
        
    def add_controls(self):
        """添加交互控制元素"""
        # 创建滑块轴
        ax_chaos = self.fig.add_axes([0.25, 0.92, 0.5, 0.03], facecolor='#2d2d2d')
        ax_sigma = self.fig.add_axes([0.25, 0.88, 0.5, 0.03], facecolor='#2d2d2d')
        
        # 创建滑块
        self.chaos_slider = Slider(
            ax=ax_chaos,
            label='Chaos Level',
            valmin=0.1,
            valmax=2.0,
            valinit=0.5,
            color='#ff6b6b',
            track_color='#4d4d4d'
        )
        self.sigma_slider = Slider(
            ax=ax_sigma,
            label='System Complexity (σ)',
            valmin=5,
            valmax=20,
            valinit=10,
            color='#4d9de0',
            track_color='#4d4d4d'
        )
        
        # 添加重置按钮
        reset_ax = self.fig.add_axes([0.8, 0.92, 0.1, 0.04])
        self.reset_button = Button(reset_ax, 'Reset', color='#2d2d2d', hovercolor='#3d3d3d')
        
        # 事件处理
        self.chaos_slider.on_changed(self.update_chaos)
        self.sigma_slider.on_changed(self.update_sigma)
        self.reset_button.on_clicked(self.reset_simulation)
    
    def update_chaos(self, val):
        """更新混沌水平"""
        self.sim.chaos_level = val
    
    def update_sigma(self, val):
        """更新系统复杂度"""
        self.sim.sigma = val
    
    def reset_simulation(self, event):
        """重置模拟"""
        self.sim = ASE2Simulator()
        self.update_plots(0)
    
    def update_plots(self, frame):
        """更新所有绘图"""
        # 执行算法步骤
        entropies, cep, optimal_scale, chaos_distance = self.sim.evolve_system()
        
        # 更新3D系统图
        self.system_plot.set_data(self.sim.x, self.sim.y)
        self.system_plot.set_3d_properties(self.sim.z)
        self.current_point.set_data([self.sim.x[-1]], [self.sim.y[-1]])
        self.current_point.set_3d_properties([self.sim.z[-1]])
        
        # 更新熵地形图
        self.entropy_plot.set_data(self.sim.scales, entropies)
        self.ax2.set_ylim(0, max(entropies)*1.1)
        self.optimal_scale_line.set_xdata([optimal_scale]*2)
        self.optimal_scale_line.set_ydata([0, max(entropies)])
        self.optimal_scale_line.set_alpha(1.0)
        
        # 更新CEP图
        self.cep_plot.set_data(self.sim.scales, cep)
        self.ax3.set_ylim(0, max(cep)*1.1)
        self.optimal_scale_marker.set_data([optimal_scale], [max(cep)])
        
        # 更新控制面板
        metrics_text = f"""
        ASE² Algorithm Status:
        Current Scale: {optimal_scale:.3f}
        Entropy Level: {np.mean(entropies):.3f}
        CEP Max: {max(cep):.3f}
        Structure Coherence: {self.sim.structure_coherence:.3f}
        Chaos Distance: {chaos_distance:.3f}
        Control Mode: {'EXPLOITATION' if chaos_distance > 0.3 else 'EXPLORATION'}
        """
        self.metrics_text.set_text(metrics_text)
        
        # 更新结构相干性历史
        self.structure_plot.set_data(range(len(self.sim.history['structure_coherence'])), 
                                     self.sim.history['structure_coherence'])
        self.structure_ax.set_xlim(0, len(self.sim.history['structure_coherence'])+1)
        
        # 更新混沌距离历史
        self.chaos_plot.set_data(range(len(self.sim.history['control_actions'])), 
                                 self.sim.history['control_actions'])
        self.chaos_ax.set_xlim(0, len(self.sim.history['control_actions'])+1)
        
        # 更新网络结构图
        size = int(10 + 10 * self.sim.structure_coherence)
        network = np.random.rand(size, size) * self.sim.structure_coherence
        self.network_img.set_data(network)
        self.network_img.set_extent([0, size, 0, size])
        
        return [self.system_plot, self.current_point, self.entropy_plot, 
                self.optimal_scale_line, self.cep_plot, self.optimal_scale_marker,
                self.metrics_text, self.structure_plot, self.chaos_plot, self.network_img]
    
    def animate(self):
        """创建动画"""
        self.ani = FuncAnimation(self.fig, self.update_plots, frames=100, 
                                interval=200, blit=True, repeat=True)
        plt.tight_layout()
        plt.subplots_adjust(top=0.85)
        plt.show()

# ======================
# 交互式控制面板 (Plotly)
# ======================

def create_control_dashboard():
    """创建交互式控制面板"""
    # 创建控件
    chaos_slider = widgets.FloatSlider(
        value=0.5,
        min=0.1,
        max=2.0,
        step=0.1,
        description='Chaos Level:',
        continuous_update=False,
        style={'description_width': '100px'},
        layout=widgets.Layout(width='400px')
    )
    
    complexity_slider = widgets.FloatSlider(
        value=10.0,
        min=5.0,
        max=20.0,
        step=0.5,
        description='Complexity:',
        continuous_update=False,
        style={'description_width': '100px'},
        layout=widgets.Layout(width='400px')
    )
    
    scale_dropdown = widgets.Dropdown(
        options=[('Micro', 0.1), ('Meso', 1.0), ('Macro', 2.0)],
        value=1.0,
        description='Init Scale:',
        style={'description_width': '100px'},
        layout=widgets.Layout(width='200px')
    )
    
    reset_button = widgets.Button(
        description='Reset Simulation',
        button_style='danger',
        layout=widgets.Layout(width='150px')
    )
    
    # 创建3D状态图
    fig = make_subplots(
        rows=2, cols=2,
        specs=[[{'type': 'scatter3d'}, {'type': 'xy'}],
               [{'type': 'xy'}, {'type': 'heatmap'}]],
        subplot_titles=(
            'Complex System State', 
            'Multiscale Entropy Topography',
            'Controllability Emergence Potential',
            'Emergent Control Structure'
        ),
        vertical_spacing=0.1,
        horizontal_spacing=0.1
    )
    
    # 添加初始轨迹
    fig.add_trace(go.Scatter3d(
        x=[0], y=[0], z=[0],
        mode='lines',
        line=dict(width=4, color='cyan'),
        row=1, col=1
    ))
    
    # 添加熵地形图
    fig.add_trace(go.Scatter(
        x=[], y=[],
        mode='lines+markers',
        line=dict(width=2, color='magenta'),
        name='Entropy'),
        row=1, col=2
    )
    
    # 添加CEP图
    fig.add_trace(go.Scatter(
        x=[], y=[],
        mode='lines+markers',
        line=dict(width=2, color='green'),
        name='CEP'),
        row=2, col=1
    )
    
    # 添加网络结构
    fig.add_trace(go.Heatmap(
        z=np.zeros((10,10)),
        colorscale='Viridis',
        showscale=False),
        row=2, col=2
    )
    
    # 布局设置
    fig.update_layout(
        title='ASE² Algorithm Interactive Dashboard',
        height=800,
        template='plotly_dark',
        margin=dict(t=80, b=60, l=60, r=60),
        scene=dict(
            xaxis_title='X',
            yaxis_title='Y',
            zaxis_title='Z'
        ),
        showlegend=False
    )
    
    # 控件容器
    controls = widgets.VBox([
        widgets.HBox([chaos_slider, complexity_slider]),
        widgets.HBox([scale_dropdown, reset_button])
    ])
    
    # 输出部件
    output = widgets.Output()
    
    # 显示所有部件
    display(widgets.VBox([controls, output]))
    display(fig)
    
    # 添加交互逻辑
    def on_value_change(change):
        with output:
            print(f"参数更新: Chaos={chaos_slider.value}, Complexity={complexity_slider.value}")
    
    chaos_slider.observe(on_value_change, names='value')
    complexity_slider.observe(on_value_change, names='value')
    scale_dropdown.observe(on_value_change, names='value')
    
    reset_button.on_click(lambda b: print("模拟已重置"))

# ======================
# 运行可视化
# ======================

if __name__ == "__main__":
    # 创建并运行动画
    visualizer = ASE2Visualizer()
    visualizer.animate()
    
    # 创建交互式控制面板 (在Jupyter中运行)
    # create_control_dashboard()