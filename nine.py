import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.widgets import Slider, Button
import matplotlib.patches as patches
import time
import random

class Drone:
    def __init__(self, id, initial_pos):
        self.id = id
        self.position = np.array(initial_pos, dtype=float)
        self.velocity = np.array([0.0, 0.0])
        self.acceleration = np.array([0.0, 0.0])
        self.role = "Guardian"  # 初始角色：守卫者
        self.score = 0
        self.energy = 100
        self.stability = 0
        self.history = []
        self.color = self.assign_color()
    
    def assign_color(self):
        # 基于ID分配颜色
        colors = ['#FF5733', '#33FF57', '#3357FF', '#F333FF', 
                 '#FF33A1', '#33FFF0', '#F0FF33', '#8C33FF', '#FF8C33']
        return colors[self.id % len(colors)]
    
    def update_role(self, scores):
        """根据得分更新角色"""
        sorted_scores = sorted(scores, reverse=True)
        if self.score == sorted_scores[0]:
            self.role = "Heir"  # 继承者
        elif self.score in sorted_scores[1:3]:
            self.role = "Challenger"  # 挑战者
        else:
            self.role = "Guardian"  # 守卫者
    
    def calculate_forces(self, target, drones):
        """计算作用在无人机上的力"""
        # 目标吸引力 (与距离成正比)
        target_force = 0.1 * (target - self.position)
        
        # 无人机间斥力
        repulsion_force = np.array([0.0, 0.0])
        for drone in drones:
            if drone.id != self.id:
                dist = np.linalg.norm(self.position - drone.position)
                if dist < 5.0:  # 安全距离
                    direction = (self.position - drone.position) / (dist + 1e-5)
                    repulsion_force += 0.8 * direction / (dist**2 + 1e-5)
        
        # 边界力 (保持在一定范围内)
        boundary_force = np.array([0.0, 0.0])
        arena_size = 30
        boundary_margin = 5
        if abs(self.position[0]) > arena_size - boundary_margin:
            boundary_force[0] = -0.1 * self.position[0]
        if abs(self.position[1]) > arena_size - boundary_margin:
            boundary_force[1] = -0.1 * self.position[1]
        
        # 角色相关力
        role_force = np.array([0.0, 0.0])
        if self.role == "Heir":
            # 继承者尝试保持在中心
            role_force = 0.3 * (target - self.position)
        elif self.role == "Challenger":
            # 挑战者尝试接近中心
            role_force = 0.5 * (target - self.position)
        else:  # Guardian
            # 守卫者保持位置
            role_force = -0.2 * self.velocity
        
        # 合力
        total_force = target_force + repulsion_force + boundary_force + role_force
        
        # 添加随机扰动
        if random.random() < 0.2:
            total_force += 0.1 * np.random.randn(2)
        
        return total_force
    
    def update_score(self, target):
        """更新得分"""
        # 距离得分 (离目标越近得分越高)
        dist_score = max(0, 10 - 0.5 * np.linalg.norm(self.position - target))
        
        # 稳定性得分 (速度越小得分越高)
        speed = np.linalg.norm(self.velocity)
        stability_score = max(0, 5 - 0.2 * speed)
        self.stability = 0.9 * self.stability + 0.1 * stability_score
        
        # 能量消耗
        energy_cost = 0.05 * np.linalg.norm(self.acceleration) + 0.01
        self.energy = max(0, self.energy - energy_cost)
        
        # 角色加成
        role_bonus = 1.0
        if self.role == "Heir":
            role_bonus = 2.0
        elif self.role == "Challenger":
            role_bonus = 1.5
        
        # 更新总得分
        self.score += (dist_score + stability_score) * role_bonus * 0.1
    
    def update(self, target, drones, dt=0.1):
        """更新无人机状态"""
        self.acceleration = self.calculate_forces(target, drones)
        self.velocity = 0.9 * self.velocity + self.acceleration * dt
        self.position += self.velocity * dt
        self.update_score(target)
        self.history.append(self.position.copy())

class NineDronesSystem:
    def __init__(self):
        # 初始化9架无人机
        angles = np.linspace(0, 2*np.pi, 10)[:-1]
        radius = 15
        self.drones = [Drone(i, [radius*np.cos(a), radius*np.sin(a)]) 
                      for i, a in enumerate(angles)]
        
        # 目标位置 (皇位)
        self.target = np.array([0.0, 0.0])
        
        # 历史记录
        self.scores_history = []
        self.positions_history = []
        self.energy_history = []
        
        # 模拟参数
        self.time_step = 0
        self.max_steps = 1000
        self.is_running = False
    
    def update(self):
        """更新整个系统"""
        if not self.is_running or self.time_step >= self.max_steps:
            return
        
        # 收集所有得分
        scores = [drone.score for drone in self.drones]
        self.scores_history.append(scores.copy())
        
        # 更新角色
        for drone in self.drones:
            drone.update_role(scores)
        
        # 更新无人机状态
        positions = []
        energies = []
        for drone in self.drones:
            drone.update(self.target, self.drones)
            positions.append(drone.position.copy())
            energies.append(drone.energy)
        
        self.positions_history.append(positions)
        self.energy_history.append(energies)
        self.time_step += 1
    
    def reset(self):
        """重置系统"""
        angles = np.linspace(0, 2*np.pi, 10)[:-1]
        radius = 15
        for i, drone in enumerate(self.drones):
            drone.position = np.array([radius*np.cos(angles[i]), radius*np.sin(angles[i])])
            drone.velocity = np.array([0.0, 0.0])
            drone.acceleration = np.array([0.0, 0.0])
            drone.role = "Guardian"
            drone.score = 0
            drone.energy = 100
            drone.stability = 0
            drone.history = []
        
        self.scores_history = []
        self.positions_history = []
        self.energy_history = []
        self.time_step = 0

# 创建系统实例
system = NineDronesSystem()

# 创建图形界面
plt.figure(figsize=(15, 10))
plt.subplots_adjust(left=0.05, right=0.95, top=0.95, bottom=0.2)

# 主战场图
ax1 = plt.subplot2grid((3, 3), (0, 0), colspan=2, rowspan=2)
ax1.set_xlim(-35, 35)
ax1.set_ylim(-35, 35)
ax1.set_title('Nine Drones Battlefield')
ax1.grid(True)
ax1.set_aspect('equal')

# 绘制目标区域
target_circle = patches.Circle((0, 0), radius=1.5, color='gold', alpha=0.7)
ax1.add_patch(target_circle)
ax1.text(0, 0, 'Throne', ha='center', va='center', fontsize=12, fontweight='bold')

# 无人机点
drone_points = [ax1.plot([], [], 'o', markersize=10, color=drone.color)[0] 
                for drone in system.drones]

# 历史轨迹
trajectories = [ax1.plot([], [], '-', lw=1, alpha=0.5, color=drone.color)[0] 
                for drone in system.drones]

# 角色标签
role_labels = [ax1.text(0, 0, '', fontsize=9, ha='center', va='bottom') 
               for _ in system.drones]

# 得分图
ax2 = plt.subplot2grid((3, 3), (0, 2))
ax2.set_title('Scores Over Time')
ax2.set_xlim(0, system.max_steps)
ax2.set_ylim(0, 100)
ax2.set_xlabel('Time Step')
ax2.set_ylabel('Score')
score_lines = [ax2.plot([], [], '-', lw=2, color=drone.color)[0] 
               for drone in system.drones]

# 能量图
ax3 = plt.subplot2grid((3, 3), (1, 2))
ax3.set_title('Energy Levels')
ax3.set_xlim(0, system.max_steps)
ax3.set_ylim(0, 120)
ax3.set_xlabel('Time Step')
ax3.set_ylabel('Energy (%)')
energy_lines = [ax3.plot([], [], '-', lw=2, color=drone.color)[0] 
                for drone in system.drones]

# 得分榜
ax4 = plt.subplot2grid((3, 3), (2, 0), colspan=3)
ax4.axis('off')
ax4.set_title('Current Status', fontsize=12)
status_text = ax4.text(0.5, 0.5, '', ha='center', va='center', fontsize=10)

# 控制按钮区域
ax_control = plt.axes([0.3, 0.05, 0.4, 0.08])
ax_control.axis('off')

# 添加按钮
ax_start = plt.axes([0.1, 0.05, 0.1, 0.05])
ax_stop = plt.axes([0.21, 0.05, 0.1, 0.05])
ax_reset = plt.axes([0.6, 0.05, 0.1, 0.05])
ax_step = plt.axes([0.71, 0.05, 0.1, 0.05])

btn_start = Button(ax_start, 'Start')
btn_stop = Button(ax_stop, 'Stop')
btn_reset = Button(ax_reset, 'Reset')
btn_step = Button(ax_step, 'Step')

# 添加速度滑块
ax_speed = plt.axes([0.32, 0.15, 0.4, 0.03])
slider_speed = Slider(ax_speed, 'Speed', 1, 100, valinit=30)

def update_plot(frame):
    if not system.is_running:
        return
    
    # 更新系统状态
    for _ in range(int(slider_speed.val // 10)):
        system.update()
    
    # 更新无人机位置
    for i, drone in enumerate(system.drones):
        drone_points[i].set_data([drone.position[0]], [drone.position[1]])
        
        # 更新轨迹
        if len(drone.history) > 1:
            x_hist = [p[0] for p in drone.history]
            y_hist = [p[1] for p in drone.history]
            trajectories[i].set_data(x_hist, y_hist)
        
        # 更新角色标签
        role_labels[i].set_position((drone.position[0], drone.position[1] + 1.5))
        role_labels[i].set_text(f"{drone.role[:1]}")
    
    # 更新得分图
    if system.scores_history:
        time_steps = list(range(len(system.scores_history)))
        for i in range(len(system.drones)):
            scores = [s[i] for s in system.scores_history]
            score_lines[i].set_data(time_steps, scores)
    
    # 更新能量图
    if system.energy_history:
        for i in range(len(system.drones)):
            energies = [e[i] for e in system.energy_history]
            energy_lines[i].set_data(time_steps[:len(energies)], energies)
    
    # 更新得分榜
    status = "Current Rankings:\n"
    drones_sorted = sorted(system.drones, key=lambda d: d.score, reverse=True)
    for i, drone in enumerate(drones_sorted[:5]):
        status += f"{i+1}. Drone {drone.id}: {drone.role} (Score: {drone.score:.1f}, Energy: {drone.energy:.1f}%)\n"
    status_text.set_text(status)
    
    # 设置得分图Y轴范围
    max_score = max([max(s) for s in system.scores_history]) if system.scores_history else 100
    ax2.set_ylim(0, max_score * 1.1)
    
    plt.draw()

def start_simulation(event):
    system.is_running = True

def stop_simulation(event):
    system.is_running = False

def reset_simulation(event):
    system.reset()
    for line in score_lines:
        line.set_data([], [])
    for line in energy_lines:
        line.set_data([], [])
    for traj in trajectories:
        traj.set_data([], [])
    status_text.set_text('')
    plt.draw()

def step_simulation(event):
    system.is_running = False
    system.update()
    update_plot(0)

# 注册事件处理
btn_start.on_clicked(start_simulation)
btn_stop.on_clicked(stop_simulation)
btn_reset.on_clicked(reset_simulation)
btn_step.on_clicked(step_simulation)

# 创建动画
ani = FuncAnimation(plt.gcf(), update_plot, interval=50)

plt.show()