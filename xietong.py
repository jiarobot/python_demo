import pygame
import numpy as np
import math
import random
import sys
from collections import deque
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg
import torch
import torch.nn as nn
import torch.optim as optim
from sklearn.cluster import KMeans
from scipy.spatial import Voronoi, voronoi_plot_2d

# 初始化pygame
pygame.init()
WIDTH, HEIGHT = 1200, 800
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("自适应无人机群协同作战模拟")
clock = pygame.time.Clock()

# 颜色定义
BACKGROUND = (10, 20, 30)
GRID_COLOR = (30, 40, 60)
DRONE_COLOR = (0, 200, 255)
ENEMY_COLOR = (255, 80, 80)
TARGET_COLOR = (50, 255, 150)
TEXT_COLOR = (220, 220, 220)
UI_BG = (20, 30, 50, 200)
RADAR_COLOR = (0, 150, 200, 50)
TRAIL_COLOR = (0, 200, 255, 100)
EXPLOSION_COLOR = (255, 200, 0)

# 战场参数
NUM_DRONES = 12
NUM_ENEMIES = 6
NUM_OBSTACLES = 15
SIMULATION_SPEED = 1.0
TACTICS = ["分散搜索", "集中突击", "分翼包抄", "防御阵型"]

# 强化学习参数
STATE_SIZE = 10
ACTION_SIZE = 4
HIDDEN_SIZE = 128
LEARNING_RATE = 0.001
GAMMA = 0.95
EPSILON_DECAY = 0.995
MIN_EPSILON = 0.01

class Drone:
    def __init__(self, x, y, drone_id):
        self.id = drone_id
        self.x = x
        self.y = y
        self.radius = 12
        self.speed = random.uniform(2.0, 3.5)
        self.direction = random.uniform(0, 2 * math.pi)
        self.color = DRONE_COLOR
        self.health = 100
        self.ammo = 100
        self.energy = 100
        self.target = None
        self.trail = deque(maxlen=20)
        self.last_shot = 0
        self.tactic = "分散搜索"
        self.state = [self.x, self.y, 0, 0, 0, 0, 0, 0, 0, 0]  # 状态向量
        
    def update(self, drones, enemies, obstacles, targets, tactic):
        self.tactic = tactic
        
        # 保存轨迹点
        self.trail.append((self.x, self.y))
        
        # 根据战术调整行为
        if self.tactic == "分散搜索":
            self.disperse_behavior(drones, enemies, obstacles)
        elif self.tactic == "集中突击":
            self.assault_behavior(drones, enemies, targets)
        elif self.tactic == "分翼包抄":
            self.flanking_behavior(drones, enemies)
        elif self.tactic == "防御阵型":
            self.defense_behavior(drones, enemies)
        
        # 移动无人机
        self.x += math.cos(self.direction) * self.speed * SIMULATION_SPEED
        self.y += math.sin(self.direction) * self.speed * SIMULATION_SPEED
        
        # 边界检查
        self.x = max(self.radius, min(WIDTH - self.radius, self.x))
        self.y = max(self.radius, min(HEIGHT - self.radius, self.y))
        
        # 能量消耗
        self.energy = max(0, self.energy - 0.05)
        
        # 更新状态向量
        self.state = [
            self.x / WIDTH, 
            self.y / HEIGHT,
            math.cos(self.direction),
            math.sin(self.direction),
            self.health / 100,
            self.ammo / 100,
            self.energy / 100,
            len(enemies) / 10,
            len(targets) / 5,
            TACTICS.index(self.tactic) / len(TACTICS)
        ]
    
    def disperse_behavior(self, drones, enemies, obstacles):
        # 分散搜索行为：避开其他无人机和障碍物，随机探索
        avoid_vector = self.calculate_avoidance(drones + obstacles, 100)
        
        if enemies:
            # 向最近的敌人移动
            closest_enemy = min(enemies, key=lambda e: self.distance_to(e.x, e.y))
            dx = closest_enemy.x - self.x
            dy = closest_enemy.y - self.y
            dist = max(0.1, math.sqrt(dx*dx + dy*dy))
            enemy_vector = (dx/dist, dy/dist)
        else:
            enemy_vector = (0, 0)
        
        # 组合向量
        dx = avoid_vector[0] * 1.5 + enemy_vector[0] * 0.5
        dy = avoid_vector[1] * 1.5 + enemy_vector[1] * 0.5
        
        # 随机探索成分
        dx += random.uniform(-0.5, 0.5)
        dy += random.uniform(-0.5, 0.5)
        
        # 更新方向
        if dx != 0 or dy != 0:
            self.direction = math.atan2(dy, dx)
    
    def assault_behavior(self, drones, enemies, targets):
        # 集中突击行为：向目标集中攻击
        if targets:
            # 优先攻击目标
            closest_target = min(targets, key=lambda t: self.distance_to(t.x, t.y))
            dx = closest_target.x - self.x
            dy = closest_target.y - self.y
        elif enemies:
            # 如果没有目标，攻击最近的敌人
            closest_enemy = min(enemies, key=lambda e: self.distance_to(e.x, e.y))
            dx = closest_enemy.x - self.x
            dy = closest_enemy.y - self.y
        else:
            dx, dy = 0, 0
            
        # 计算方向
        if dx != 0 or dy != 0:
            dist = max(0.1, math.sqrt(dx*dx + dy*dy))
            self.direction = math.atan2(dy, dx)
            
        # 尝试射击
        if enemies and self.ammo > 0 and pygame.time.get_ticks() - self.last_shot > 500:
            closest_enemy = min(enemies, key=lambda e: self.distance_to(e.x, e.y))
            if self.distance_to(closest_enemy.x, closest_enemy.y) < 200:
                self.shoot(closest_enemy)
    
    def flanking_behavior(self, drones, enemies):
        # 分翼包抄行为：绕到敌人侧面
        if not enemies:
            return
            
        # 找到敌人中心位置
        avg_x = sum(e.x for e in enemies) / len(enemies)
        avg_y = sum(e.y for e in enemies) / len(enemies)
        
        # 根据无人机ID决定包抄方向
        if self.id % 2 == 0:
            # 左侧包抄
            target_x = avg_x - 150
            target_y = avg_y
        else:
            # 右侧包抄
            target_x = avg_x + 150
            target_y = avg_y
            
        # 移动到包抄位置
        dx = target_x - self.x
        dy = target_y - self.y
        
        # 计算方向
        if dx != 0 or dy != 0:
            dist = max(0.1, math.sqrt(dx*dx + dy*dy))
            self.direction = math.atan2(dy, dx)
            
        # 尝试射击
        if enemies and self.ammo > 0 and pygame.time.get_ticks() - self.last_shot > 400:
            for enemy in enemies:
                if self.distance_to(enemy.x, enemy.y) < 180:
                    self.shoot(enemy)
                    break
    
    def defense_behavior(self, drones, enemies):
        # 防御阵型行为：保持队形，保护中心
        # 计算无人机群中心
        if drones:
            center_x = sum(d.x for d in drones) / len(drones)
            center_y = sum(d.y for d in drones) / len(drones)
        else:
            center_x, center_y = WIDTH/2, HEIGHT/2
            
        # 计算理想防御位置（圆形分布）
        angle = (self.id * 2 * math.pi) / len(drones)
        ideal_x = center_x + 120 * math.cos(angle)
        ideal_y = center_y + 120 * math.sin(angle)
        
        # 向理想位置移动
        dx = ideal_x - self.x
        dy = ideal_y - self.y
        
        # 避开其他无人机和敌人
        avoid_vector = self.calculate_avoidance(drones + enemies, 80)
        
        # 组合向量
        dx = dx * 0.8 + avoid_vector[0] * 1.2
        dy = dy * 0.8 + avoid_vector[1] * 1.2
        
        # 计算方向
        if dx != 0 or dy != 0:
            dist = max(0.1, math.sqrt(dx*dx + dy*dy))
            self.direction = math.atan2(dy, dx)
            
        # 尝试射击接近的敌人
        if enemies and self.ammo > 0 and pygame.time.get_ticks() - self.last_shot > 600:
            for enemy in enemies:
                if self.distance_to(enemy.x, enemy.y) < 220:
                    self.shoot(enemy)
                    break
    
    def calculate_avoidance(self, entities, threshold):
        # 计算避开其他实体所需的向量
        avoid_x, avoid_y = 0, 0
        for entity in entities:
            if entity is self:
                continue
                
            dist = self.distance_to(entity.x, entity.y)
            if dist < threshold:
                # 计算排斥力
                strength = (threshold - dist) / threshold
                avoid_x += (self.x - entity.x) * strength
                avoid_y += (self.y - entity.y) * strength
                
        # 归一化
        magnitude = max(0.1, math.sqrt(avoid_x*avoid_x + avoid_y*avoid_y))
        return (avoid_x/magnitude, avoid_y/magnitude)
    
    def distance_to(self, x, y):
        return math.sqrt((self.x - x)**2 + (self.y - y)**2)
    
    def shoot(self, enemy):
        if self.ammo <= 0:
            return
            
        self.ammo -= 1
        self.last_shot = pygame.time.get_ticks()
        
        # 计算命中概率 (距离越近命中率越高)
        dist = self.distance_to(enemy.x, enemy.y)
        hit_prob = max(0.1, 1.0 - dist / 300)
        
        if random.random() < hit_prob:
            # 命中敌人
            damage = random.randint(15, 30)
            enemy.health -= damage
            
            # 创建命中效果
            global effects
            effects.append({
                'type': 'hit',
                'x': enemy.x,
                'y': enemy.y,
                'color': (255, 100, 0),
                'size': 8,
                'life': 15
            })
            
            if enemy.health <= 0:
                # 敌人被摧毁
                effects.append({
                    'type': 'explosion',
                    'x': enemy.x,
                    'y': enemy.y,
                    'size': 40,
                    'life': 30
                })

class Enemy:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.radius = 14
        self.speed = random.uniform(1.0, 2.5)
        self.direction = random.uniform(0, 2 * math.pi)
        self.color = ENEMY_COLOR
        self.health = 100
        self.target = None
        self.last_shot = 0
        self.aggression = random.uniform(0.5, 1.0)
    
    def update(self, drones, targets):
        # 简单AI：追踪最近的无人机或目标
        if drones:
            closest_drone = min(drones, key=lambda d: self.distance_to(d.x, d.y))
            dx = closest_drone.x - self.x
            dy = closest_drone.y - self.y
            dist = max(0.1, math.sqrt(dx*dx + dy*dy))
            
            # 更新方向
            self.direction = math.atan2(dy, dx)
            
            # 移动
            self.x += math.cos(self.direction) * self.speed * SIMULATION_SPEED
            self.y += math.sin(self.direction) * self.speed * SIMULATION_SPEED
            
            # 边界检查
            self.x = max(self.radius, min(WIDTH - self.radius, self.x))
            self.y = max(self.radius, min(HEIGHT - self.radius, self.y))
            
            # 尝试射击
            if dist < 250 and pygame.time.get_ticks() - self.last_shot > 800:
                self.shoot(closest_drone)
    
    def distance_to(self, x, y):
        return math.sqrt((self.x - x)**2 + (self.y - y)**2)
    
    def shoot(self, drone):
        self.last_shot = pygame.time.get_ticks()
        
        # 计算命中概率
        dist = self.distance_to(drone.x, drone.y)
        hit_prob = max(0.1, 1.0 - dist / 300)
        
        if random.random() < hit_prob:
            # 命中无人机
            damage = random.randint(10, 25)
            drone.health -= damage
            
            # 创建命中效果
            global effects
            effects.append({
                'type': 'hit',
                'x': drone.x,
                'y': drone.y,
                'color': (255, 50, 50),
                'size': 8,
                'life': 15
            })

class Target:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.radius = 18
        self.color = TARGET_COLOR
        self.value = 100

class Obstacle:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.radius = random.randint(20, 50)
        self.color = (100, 100, 120)

# 强化学习神经网络
class QNetwork(nn.Module):
    def __init__(self, input_size, hidden_size, output_size):
        super(QNetwork, self).__init__()
        self.fc1 = nn.Linear(input_size, hidden_size)
        self.fc2 = nn.Linear(hidden_size, hidden_size)
        self.fc3 = nn.Linear(hidden_size, output_size)
        self.relu = nn.ReLU()
        
    def forward(self, x):
        x = self.relu(self.fc1(x))
        x = self.relu(self.fc2(x))
        x = self.fc3(x)
        return x

# 战术决策智能体
class TacticalAgent:
    def __init__(self):
        self.model = QNetwork(STATE_SIZE, HIDDEN_SIZE, ACTION_SIZE)
        self.optimizer = optim.Adam(self.model.parameters(), lr=LEARNING_RATE)
        self.criterion = nn.MSELoss()
        self.epsilon = 1.0
        self.memory = deque(maxlen=2000)
        self.last_tactic_change = pygame.time.get_ticks()
        
    def select_action(self, state):
        if random.random() < self.epsilon:
            # 随机探索
            return random.randint(0, ACTION_SIZE-1)
        else:
            # 使用模型选择最优动作
            state_tensor = torch.FloatTensor(state).unsqueeze(0)
            with torch.no_grad():
                q_values = self.model(state_tensor)
            return torch.argmax(q_values).item()
    
    def remember(self, state, action, reward, next_state, done):
        self.memory.append((state, action, reward, next_state, done))
    
    def replay(self, batch_size):
        if len(self.memory) < batch_size:
            return
            
        # 从记忆中采样
        batch = random.sample(self.memory, batch_size)
        states, actions, rewards, next_states, dones = zip(*batch)
        
        states = torch.FloatTensor(states)
        actions = torch.LongTensor(actions)
        rewards = torch.FloatTensor(rewards)
        next_states = torch.FloatTensor(next_states)
        dones = torch.FloatTensor(dones)
        
        # 计算当前Q值
        current_q = self.model(states).gather(1, actions.unsqueeze(1)).squeeze(1)
        
        # 计算目标Q值
        next_q = self.model(next_states).detach().max(1)[0]
        target_q = rewards + GAMMA * next_q * (1 - dones)
        
        # 计算损失
        loss = self.criterion(current_q, target_q)
        
        # 反向传播
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()
        
        # 衰减epsilon
        if self.epsilon > MIN_EPSILON:
            self.epsilon *= EPSILON_DECAY
            
        return loss.item()

# 创建战场实体
def create_battlefield():
    drones = []
    for i in range(NUM_DRONES):
        drones.append(Drone(WIDTH/4, HEIGHT/2 + random.uniform(-100, 100), i))
    
    enemies = []
    for i in range(NUM_ENEMIES):
        enemies.append(Enemy(WIDTH*3/4, HEIGHT/2 + random.uniform(-100, 100)))
    
    obstacles = []
    for i in range(NUM_OBSTACLES):
        obstacles.append(Obstacle(random.randint(100, WIDTH-100), random.randint(100, HEIGHT-100)))
    
    targets = []
    for i in range(3):
        targets.append(Target(random.randint(200, WIDTH-200), random.randint(150, HEIGHT-150)))
    
    return drones, enemies, obstacles, targets

# 绘制雷达图
def draw_radar(surface, drones, enemies):
    if not drones:
        return
        
    # 计算无人机群中心
    center_x = sum(d.x for d in drones) / len(drones)
    center_y = sum(d.y for d in drones) / len(drones)
    
    # 创建雷达表面
    radar = pygame.Surface((300, 300), pygame.SRCALPHA)
    pygame.draw.circle(radar, (*RADAR_COLOR[:3], 100), (150, 150), 150, 2)
    pygame.draw.circle(radar, (*RADAR_COLOR[:3], 80), (150, 150), 100, 1)
    pygame.draw.circle(radar, (*RADAR_COLOR[:3], 80), (150, 150), 50, 1)
    
    # 绘制坐标轴
    pygame.draw.line(radar, (*RADAR_COLOR[:3], 150), (150, 150), (150, 30), 1)
    pygame.draw.line(radar, (*RADAR_COLOR[:3], 150), (150, 150), (270, 150), 1)
    
    # 绘制无人机位置（相对于中心）
    for drone in drones:
        dx = drone.x - center_x
        dy = drone.y - center_y
        # 缩放以适应雷达范围
        scale = 150 / 400  # 400像素对应雷达半径150
        radar_x = 150 + dx * scale
        radar_y = 150 + dy * scale
        
        if 0 <= radar_x < 300 and 0 <= radar_y < 300:
            pygame.draw.circle(radar, DRONE_COLOR, (int(radar_x), int(radar_y)), 4)
    
    # 绘制敌人位置
    for enemy in enemies:
        dx = enemy.x - center_x
        dy = enemy.y - center_y
        scale = 150 / 400
        radar_x = 150 + dx * scale
        radar_y = 150 + dy * scale
        
        if 0 <= radar_x < 300 and 0 <= radar_y < 300:
            pygame.draw.circle(radar, ENEMY_COLOR, (int(radar_x), int(radar_y)), 5)
    
    # 将雷达绘制到主屏幕
    surface.blit(radar, (WIDTH - 320, 20))

# 绘制图表
def draw_charts(surface, performance_data):
    # 创建图表表面
    chart_surface = pygame.Surface((400, 300), pygame.SRCALPHA)
    
    # 绘制性能图表
    if len(performance_data) > 1:
        # 创建matplotlib图表
        fig, ax = plt.subplots(figsize=(4, 3), dpi=80)
        ax.plot(performance_data, color='cyan', linewidth=2)
        ax.set_title('战术性能评估', fontsize=10, color='white')
        ax.set_facecolor((0.1, 0.1, 0.2))
        fig.patch.set_facecolor((0.1, 0.1, 0.2, 0.7))
        ax.tick_params(colors='white')
        ax.spines['bottom'].set_color('white')
        ax.spines['top'].set_color('white') 
        ax.spines['right'].set_color('white')
        ax.spines['left'].set_color('white')
        
        # 将matplotlib图表转换为pygame表面
        canvas = FigureCanvasAgg(fig)
        canvas.draw()
        renderer = canvas.get_renderer()
        raw_data = renderer.tostring_rgb()
        size = canvas.get_width_height()
        
        # 创建pygame图像
        plt_surface = pygame.image.fromstring(raw_data, size, "RGB")
        plt_surface = pygame.transform.scale(plt_surface, (380, 280))
        chart_surface.blit(plt_surface, (10, 10))
        plt.close(fig)
    
    # 绘制到主屏幕
    surface.blit(chart_surface, (20, HEIGHT - 330))

# 绘制UI面板
def draw_ui(surface, drones, enemies, targets, tactic, agent, frame_count):
    # 绘制半透明背景
    ui_surface = pygame.Surface((400, 160), pygame.SRCALPHA)
    ui_surface.fill(UI_BG)
    
    # 绘制战术信息
    font = pygame.font.SysFont(None, 28)
    tactic_text = font.render(f"当前战术: {tactic}", True, TEXT_COLOR)
    ui_surface.blit(tactic_text, (20, 20))
    
    # 绘制状态信息
    font = pygame.font.SysFont(None, 24)
    drones_text = font.render(f"无人机: {len(drones)}/{NUM_DRONES}", True, TEXT_COLOR)
    enemies_text = font.render(f"敌人: {len(enemies)}/{NUM_ENEMIES}", True, TEXT_COLOR)
    targets_text = font.render(f"目标: {len(targets)}/3", True, TEXT_COLOR)
    
    ui_surface.blit(drones_text, (20, 60))
    ui_surface.blit(enemies_text, (20, 90))
    ui_surface.blit(targets_text, (20, 120))
    
    # 绘制智能体信息
    epsilon_text = font.render(f"探索率: {agent.epsilon:.3f}", True, TEXT_COLOR)
    memory_text = font.render(f"记忆: {len(agent.memory)}", True, TEXT_COLOR)
    
    ui_surface.blit(epsilon_text, (200, 60))
    ui_surface.blit(memory_text, (200, 90))
    
    # 绘制帧率
    fps_text = font.render(f"帧率: {frame_count}", True, TEXT_COLOR)
    ui_surface.blit(fps_text, (200, 120))
    
    # 绘制战术选项
    pygame.draw.rect(ui_surface, (60, 80, 120), (280, 20, 110, 30), border_radius=5)
    change_text = font.render("切换战术", True, TEXT_COLOR)
    ui_surface.blit(change_text, (290, 25))
    
    # 绘制到主屏幕
    surface.blit(ui_surface, (20, 20))

# 绘制Voronoi图
def draw_voronoi(surface, drones, enemies):
    if len(drones) < 3:
        return
        
    # 获取所有无人机位置
    points = np.array([(d.x, d.y) for d in drones])
    
    # 计算Voronoi图
    vor = Voronoi(points)
    
    # 绘制Voronoi边
    for edge in vor.ridge_vertices:
        if -1 not in edge:
            start = vor.vertices[edge[0]]
            end = vor.vertices[edge[1]]
            pygame.draw.line(surface, (0, 150, 200, 80), start, end, 2)
    
    # 绘制Voronoi点
    for point in points:
        pygame.draw.circle(surface, (0, 200, 255, 150), point, 5)

# 初始化
drones, enemies, obstacles, targets = create_battlefield()
tactical_agent = TacticalAgent()
current_tactic = "分散搜索"
effects = []
performance_history = []
running = True
paused = False
last_performance_update = pygame.time.get_ticks()

# 主循环
frame_count = 0
while running:
    frame_count = int(clock.get_fps())
    
    # 事件处理
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                paused = not paused
            elif event.key == pygame.K_r:
                drones, enemies, obstacles, targets = create_battlefield()
                effects = []
                performance_history = []
        elif event.type == pygame.MOUSEBUTTONDOWN:
            mouse_x, mouse_y = pygame.mouse.get_pos()
            # 检查是否点击了"切换战术"按钮
            if 300 <= mouse_x <= 410 and 40 <= mouse_y <= 70:
                # 切换到下一个战术
                current_index = TACTICS.index(current_tactic)
                current_tactic = TACTICS[(current_index + 1) % len(TACTICS)]
    
    if paused:
        continue
    
    # 更新实体
    for drone in drones:
        drone.update(drones, enemies, obstacles, targets, current_tactic)
    
    for enemy in enemies:
        enemy.update(drones, targets)
    
    # 移除被摧毁的实体
    drones = [d for d in drones if d.health > 0]
    enemies = [e for e in enemies if e.health > 0]
    
    # 战术决策（每2秒）
    current_time = pygame.time.get_ticks()
    if drones and current_time - tactical_agent.last_tactic_change > 2000:
        # 使用平均状态
        avg_state = np.mean([d.state for d in drones], axis=0)
        
        # 选择动作
        action = tactical_agent.select_action(avg_state)
        current_tactic = TACTICS[action]
        tactical_agent.last_tactic_change = current_time
        
        # 计算奖励（性能指标）
        if performance_history:
            prev_perf = performance_history[-1]
        else:
            prev_perf = 0.5
            
        performance = (len(drones)/NUM_DRONES * 0.4 + 
                      len(targets)/3 * 0.3 + 
                      (1 - len(enemies)/NUM_ENEMIES) * 0.3)
        reward = performance - prev_perf
        
        # 记忆经验
        tactical_agent.remember(avg_state, action, reward, avg_state, False)
        
        # 添加到历史
        performance_history.append(performance)
        
        # 经验回放
        if len(tactical_agent.memory) > 64:
            tactical_agent.replay(64)
    
    # 更新效果
    for effect in effects[:]:
        effect['life'] -= 1
        if effect['life'] <= 0:
            effects.remove(effect)
    
    # 绘制
    screen.fill(BACKGROUND)
    
    # 绘制网格
    for x in range(0, WIDTH, 40):
        pygame.draw.line(screen, GRID_COLOR, (x, 0), (x, HEIGHT), 1)
    for y in range(0, HEIGHT, 40):
        pygame.draw.line(screen, GRID_COLOR, (0, y), (WIDTH, y), 1)
    
    # 绘制轨迹
    for drone in drones:
        for i, (trail_x, trail_y) in enumerate(drone.trail):
            alpha = int(255 * i / len(drone.trail))
            pygame.draw.circle(screen, (*TRAIL_COLOR[:3], alpha//2), 
                             (int(trail_x), int(trail_y)), 2)
    
    # 绘制障碍物
    for obstacle in obstacles:
        pygame.draw.circle(screen, obstacle.color, (int(obstacle.x), int(obstacle.y)), obstacle.radius)
        pygame.draw.circle(screen, (70, 70, 90), (int(obstacle.x), int(obstacle.y)), obstacle.radius, 2)
    
    # 绘制目标
    for target in targets:
        pygame.draw.circle(screen, target.color, (int(target.x), int(target.y)), target.radius)
        pygame.draw.circle(screen, (30, 180, 100), (int(target.x), int(target.y)), target.radius, 3)
        # 绘制目标符号
        pygame.draw.line(screen, (30, 180, 100), 
                        (target.x - target.radius//2, target.y),
                        (target.x + target.radius//2, target.y), 3)
        pygame.draw.line(screen, (30, 180, 100), 
                        (target.x, target.y - target.radius//2),
                        (target.x, target.y + target.radius//2), 3)
    
    # 绘制敌人
    for enemy in enemies:
        pygame.draw.circle(screen, enemy.color, (int(enemy.x), int(enemy.y)), enemy.radius)
        pygame.draw.circle(screen, (180, 40, 40), (int(enemy.x), int(enemy.y)), enemy.radius, 2)
        
        # 绘制敌人符号
        pygame.draw.line(screen, (180, 40, 40), 
                        (enemy.x - enemy.radius*0.7, enemy.y - enemy.radius*0.7),
                        (enemy.x + enemy.radius*0.7, enemy.y + enemy.radius*0.7), 3)
        pygame.draw.line(screen, (180, 40, 40), 
                        (enemy.x + enemy.radius*0.7, enemy.y - enemy.radius*0.7),
                        (enemy.x - enemy.radius*0.7, enemy.y + enemy.radius*0.7), 3)
        
        # 绘制血条
        pygame.draw.rect(screen, (50, 50, 50), 
                        (enemy.x - 20, enemy.y - enemy.radius - 10, 40, 5))
        pygame.draw.rect(screen, (200, 30, 30), 
                        (enemy.x - 20, enemy.y - enemy.radius - 10, 40 * enemy.health/100, 5))
    
    # 绘制无人机
    for drone in drones:
        # 绘制主体
        pygame.draw.circle(screen, drone.color, (int(drone.x), int(drone.y)), drone.radius)
        pygame.draw.circle(screen, (0, 150, 180), (int(drone.x), int(drone.y)), drone.radius, 2)
        
        # 绘制方向指示器
        end_x = drone.x + math.cos(drone.direction) * drone.radius * 1.5
        end_y = drone.y + math.sin(drone.direction) * drone.radius * 1.5
        pygame.draw.line(screen, (0, 230, 255), 
                        (drone.x, drone.y), (end_x, end_y), 3)
        
        # 绘制状态条
        # 血条
        pygame.draw.rect(screen, (50, 50, 50), 
                        (drone.x - 20, drone.y - drone.radius - 20, 40, 5))
        pygame.draw.rect(screen, (0, 200, 100), 
                        (drone.x - 20, drone.y - drone.radius - 20, 40 * drone.health/100, 5))
        
        # 弹药条
        pygame.draw.rect(screen, (50, 50, 50), 
                        (drone.x - 20, drone.y - drone.radius - 15, 40, 3))
        pygame.draw.rect(screen, (0, 150, 255), 
                        (drone.x - 20, drone.y - drone.radius - 15, 40 * drone.ammo/100, 3))
        
        # 能量条
        pygame.draw.rect(screen, (50, 50, 50), 
                        (drone.x - 20, drone.y - drone.radius - 10, 40, 3))
        pygame.draw.rect(screen, (255, 200, 0), 
                        (drone.x - 20, drone.y - drone.radius - 10, 40 * drone.energy/100, 3))
    
    # 绘制效果
    for effect in effects:
        if effect['type'] == 'hit':
            pygame.draw.circle(screen, effect['color'], 
                             (int(effect['x']), int(effect['y'])), effect['size'])
        elif effect['type'] == 'explosion':
            radius = effect['size'] * (effect['life'] / 30)
            pygame.draw.circle(screen, EXPLOSION_COLOR, 
                             (int(effect['x']), int(effect['y'])), int(radius))
            pygame.draw.circle(screen, (255, 100, 0, 150), 
                             (int(effect['x']), int(effect['y'])), int(radius * 0.7))
    
    # 绘制Voronoi图
    draw_voronoi(screen, drones, enemies)
    
    # 绘制UI
    draw_ui(screen, drones, enemies, targets, current_tactic, tactical_agent, frame_count)
    
    # 绘制雷达
    draw_radar(screen, drones, enemies)
    
    # 绘制图表
    if performance_history:
        draw_charts(screen, performance_history)
    
    # 绘制战术说明
    font = pygame.font.SysFont(None, 24)
    if current_tactic == "分散搜索":
        desc = "战术: 分散搜索 - 无人机分散探索战场，避免聚集"
    elif current_tactic == "集中突击":
        desc = "战术: 集中突击 - 无人机集中火力攻击关键目标"
    elif current_tactic == "分翼包抄":
        desc = "战术: 分翼包抄 - 无人机分成两组从侧翼包围敌人"
    elif current_tactic == "防御阵型":
        desc = "战术: 防御阵型 - 无人机形成防御圈保护中心区域"
    
    desc_text = font.render(desc, True, TEXT_COLOR)
    screen.blit(desc_text, (WIDTH//2 - desc_text.get_width()//2, HEIGHT - 40))
    
    # 绘制控制说明
    controls = "空格键: 暂停/继续  |  R键: 重置战场  |  鼠标点击按钮: 切换战术"
    ctrl_text = font.render(controls, True, (150, 150, 150))
    screen.blit(ctrl_text, (WIDTH//2 - ctrl_text.get_width()//2, HEIGHT - 20))
    
    pygame.display.flip()
    clock.tick(60)

pygame.quit()
sys.exit()