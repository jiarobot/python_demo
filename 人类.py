import numpy as np
import matplotlib.pyplot as plt
from scipy.integrate import odeint
from matplotlib import rcParams

rcParams['font.sans-serif'] = ['SimHei']
rcParams['axes.unicode_minus'] = False

class HumanEcosystemModel:
    def __init__(self):
        self.params = {
            'r': 0.1,      # 自然资源增长率
            'K': 100,      # 环境承载力
            'alpha': 0.02, # 人类消耗系数
            'beta': 0.01,  # 技术改善系数
            'delta': 0.05, # 资源再生率
            'gamma': 0.03  # 环境恢复率
        }
    
    def system_dynamics(self, state, t):
        """
        定义系统动力学方程
        state = [人类发展水平, 环境质量, 资源存量]
        """
        H, E, R = state
        r, K, alpha, beta, delta, gamma = self.params.values()
        
        # 人类发展方程
        dHdt = beta * H * (1 - H/K) * E - alpha * H * R
        
        # 环境质量方程
        dEdt = gamma * (K - E) - 0.01 * H * E + 0.005 * R
        
        # 资源存量方程
        dRdt = delta * R * (1 - R/K) - 0.02 * H * R + 0.001 * E
        
        return [dHdt, dEdt, dRdt]
    
    def simulate(self, time_span=200, initial_conditions=None):
        """运行模拟"""
        if initial_conditions is None:
            initial_conditions = [10, 80, 60]  # 初始状态
        
        t = np.linspace(0, time_span, 1000)
        solution = odeint(self.system_dynamics, initial_conditions, t)
        
        return t, solution
    
    def plot_results(self, t, solution, scenario_name="默认情景"):
        """绘制结果"""
        H, E, R = solution.T
        
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
        
        # 主要变量趋势
        ax1.plot(t, H, 'b-', label='人类发展水平', linewidth=2)
        ax1.plot(t, E, 'g-', label='环境质量', linewidth=2)
        ax1.plot(t, R, 'r-', label='资源存量', linewidth=2)
        ax1.set_title(f'{scenario_name} - 系统动态')
        ax1.set_xlabel('时间')
        ax1.set_ylabel('水平')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # 相空间图
        ax2.plot(H, E, 'purple', linewidth=1.5)
        ax2.set_xlabel('人类发展水平')
        ax2.set_ylabel('环境质量')
        ax2.set_title('人类-环境相空间')
        ax2.grid(True, alpha=0.3)
        
        # 人类发展与环境关系
        ax3.plot(t, H/E, 'orange', linewidth=2)
        ax3.set_xlabel('时间')
        ax3.set_ylabel('人类发展/环境质量 比率')
        ax3.set_title('发展-环境平衡')
        ax3.grid(True, alpha=0.3)
        
        # 资源使用效率
        efficiency = np.where(H > 0, E/H, 0)
        ax4.plot(t, efficiency, 'brown', linewidth=2)
        ax4.set_xlabel('时间')
        ax4.set_ylabel('环境效率')
        ax4.set_title('单位发展的环境影响')
        ax4.grid(True, alpha=0.3)
        
        plt.tight_layout()
        return fig

# 运行不同情景的模拟
model = HumanEcosystemModel()

print("开始生态系统模拟...")

# 情景1：平衡发展
print("情景1: 平衡发展")
t1, sol1 = model.simulate(initial_conditions=[10, 80, 60])
fig1 = model.plot_results(t1, sol1, "平衡发展")

# 情景2：快速发展（高初始人类发展）
print("情景2: 快速发展")
t2, sol2 = model.simulate(initial_conditions=[30, 70, 50])
fig2 = model.plot_results(t2, sol2, "快速发展")

# 情景3：环境保护优先
print("情景3: 环境保护优先")
model.params['alpha'] = 0.01  # 降低消耗系数
model.params['beta'] = 0.015  # 调整技术改善
t3, sol3 = model.simulate(initial_conditions=[10, 90, 70])
fig3 = model.plot_results(t3, sol3, "环境保护优先")

# 创建比较图
plt.figure(figsize=(14, 10))

# 重置参数
model.params = {
    'r': 0.1, 'K': 100, 'alpha': 0.02, 
    'beta': 0.01, 'delta': 0.05, 'gamma': 0.03
}

scenarios = {
    '平衡发展': [10, 80, 60],
    '快速发展': [30, 70, 50], 
    '环保优先': [10, 90, 70]
}

colors = ['blue', 'red', 'green']
linestyles = ['-', '--', '-.']

for i, (name, init_cond) in enumerate(scenarios.items()):
    if name == '环保优先':
        model.params['alpha'] = 0.01
    else:
        model.params['alpha'] = 0.02
        
    t, sol = model.simulate(initial_conditions=init_cond)
    H, E, R = sol.T
    
    plt.subplot(2, 2, 1)
    plt.plot(t, H, color=colors[i], linestyle=linestyles[i], 
             label=name, linewidth=2)
    
    plt.subplot(2, 2, 2)  
    plt.plot(t, E, color=colors[i], linestyle=linestyles[i],
             label=name, linewidth=2)
    
    plt.subplot(2, 2, 3)
    plt.plot(t, R, color=colors[i], linestyle=linestyles[i],
             label=name, linewidth=2)
    
    plt.subplot(2, 2, 4)
    sustainability = E / (H + 1e-6)  # 避免除零
    plt.plot(t, sustainability, color=colors[i], linestyle=linestyles[i],
             label=name, linewidth=2)

plt.subplot(2, 2, 1)
plt.title('人类发展水平比较')
plt.xlabel('时间')
plt.ylabel('发展水平')
plt.legend()
plt.grid(True, alpha=0.3)

plt.subplot(2, 2, 2)
plt.title('环境质量比较')
plt.xlabel('时间')
plt.ylabel('环境质量')
plt.legend()
plt.grid(True, alpha=0.3)

plt.subplot(2, 2, 3)
plt.title('资源存量比较')
plt.xlabel('时间')
plt.ylabel('资源存量')
plt.legend()
plt.grid(True, alpha=0.3)

plt.subplot(2, 2, 4)
plt.title('可持续发展指数比较')
plt.xlabel('时间')
plt.ylabel('环境/发展比率')
plt.legend()
plt.grid(True, alpha=0.3)

plt.tight_layout()
plt.show()

print("模拟完成。图表展示了不同发展策略下的长期动态。")
print("注：这是一个高度简化的理论模型，现实情况要复杂得多。")