import pygame
import numpy as np
import matplotlib
matplotlib.rc("font", family='Microsoft YaHei')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg
import random
import math
import sys
from collections import deque
import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F

# 初始化pygame
pygame.init()
WIDTH, HEIGHT = 1200, 800
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("军事对抗智能模拟系统 - 红蓝军团多战区博弈")

# 颜色定义
BACKGROUND = (10, 20, 30)
RED = (220, 60, 60)
BLUE = (60, 120, 220)
GREEN = (50, 180, 80)
YELLOW = (220, 200, 60)
PURPLE = (150, 60, 220)
CYAN = (60, 200, 220)
WHITE = (240, 240, 240)
GRAY = (100, 100, 120)
TERRAIN_COLORS = [(30, 80, 40), (120, 150, 80), (100, 100, 100), (70, 70, 150)]

# 字体
font_large = pygame.font.SysFont('simhei', 32)
font_medium = pygame.font.SysFont('simhei', 24)
font_small = pygame.font.SysFont('simhei', 18)

class MilitaryUnit:
    def __init__(self, x, y, unit_type, side, unit_id):
        self.x = x
        self.y = y
        self.unit_type = unit_type  # 0:步兵, 1:坦克, 2:炮兵, 3:无人机, 4:后勤
        self.side = side  # 0:红方, 1:蓝方
        self.id = unit_id
        self.health = 100
        self.ammo = 100 if unit_type != 4 else 200
        self.fuel = 100 if unit_type in [1, 3] else 0
        self.attack_power = [20, 50, 70, 30, 5][unit_type]
        self.defense = [30, 60, 20, 10, 10][unit_type]
        self.speed = [2, 3, 1, 5, 2][unit_type]
        self.range = [40, 60, 150, 200, 20][unit_type]
        self.target = None
        self.path = []
        self.cooldown = 0
        self.last_action = "待命"
        self.status = "active"
        
    def draw(self, screen, offset_x, offset_y, scale):
        color = RED if self.side == 0 else BLUE
        unit_size = 12 if self.unit_type != 1 else 15
        unit_size = 10 if self.unit_type == 4 else unit_size
        
        # 绘制单位
        pygame.draw.circle(screen, color, 
                          (int(offset_x + self.x * scale), 
                           int(offset_y + self.y * scale)), 
                          unit_size)
        
        # 绘制单位类型标识
        symbols = ["I", "T", "A", "U", "S"]
        symbol_color = WHITE
        text = font_small.render(symbols[self.unit_type], True, symbol_color)
        screen.blit(text, (int(offset_x + self.x * scale) - 5, 
                          int(offset_y + self.y * scale) - 8))
        
        # 绘制血条
        bar_width = 20
        bar_height = 4
        pygame.draw.rect(screen, (100, 100, 100), 
                        (int(offset_x + self.x * scale) - bar_width//2, 
                         int(offset_y + self.y * scale) + unit_size + 2, 
                         bar_width, bar_height))
        pygame.draw.rect(screen, GREEN, 
                        (int(offset_x + self.x * scale) - bar_width//2, 
                         int(offset_y + self.y * scale) + unit_size + 2, 
                         bar_width * self.health / 100, bar_height))
    
    def move_toward(self, target_x, target_y):
        dx = target_x - self.x
        dy = target_y - self.y
        distance = max(0.1, math.sqrt(dx*dx + dy*dy))
        move_dist = min(self.speed, distance)
        
        self.x += (dx / distance) * move_dist
        self.y += (dy / distance) * move_dist
        
        self.last_action = f"移动至({int(target_x)},{int(target_y)})"
    
    def attack(self, target):
        if self.cooldown <= 0 and self.ammo > 0:
            distance = math.sqrt((self.x - target.x)**2 + (self.y - target.y)**2)
            if distance <= self.range:
                damage = max(1, self.attack_power - target.defense // 2)
                target.health -= damage
                self.ammo -= 1
                self.cooldown = 10
                self.last_action = f"攻击{target.unit_type_name()}"
                return True
        return False
    
    def unit_type_name(self):
        names = ["步兵", "坦克", "炮兵", "无人机", "后勤"]
        return names[self.unit_type]
    
    def update(self):
        if self.cooldown > 0:
            self.cooldown -= 1
        if self.health <= 0:
            self.status = "destroyed"

class StrategicPoint:
    def __init__(self, x, y, point_id, point_type):
        self.x = x
        self.y = y
        self.id = point_id
        self.point_type = point_type  # 0:指挥所, 1:资源点, 2:雷达站, 3:机场
        self.controlled_by = -1  # -1:中立, 0:红方, 1:蓝方
        self.resources = 100 if point_type == 1 else 0
        self.value = [100, 50, 80, 70][point_type]
        self.health = 200
        self.unit_production = [0, 0, 0, 0]  # 步兵,坦克,炮兵,无人机
        self.last_capture_progress = 0
        
    def draw(self, screen, offset_x, offset_y, scale):
        colors = [YELLOW, GREEN, CYAN, PURPLE]
        pygame.draw.circle(screen, colors[self.point_type], 
                          (int(offset_x + self.x * scale), 
                           int(offset_y + self.y * scale)), 15)
        
        # 绘制控制状态
        if self.controlled_by == 0:
            pygame.draw.circle(screen, RED, 
                              (int(offset_x + self.x * scale), 
                               int(offset_y + self.y * scale)), 8, 2)
        elif self.controlled_by == 1:
            pygame.draw.circle(screen, BLUE, 
                              (int(offset_x + self.x * scale), 
                               int(offset_y + self.y * scale)), 8, 2)
        
        # 绘制点类型标识
        symbols = ["HQ", "RS", "RD", "AP"]
        text = font_small.render(symbols[self.point_type], True, WHITE)
        screen.blit(text, (int(offset_x + self.x * scale) - 10, 
                          int(offset_y + self.y * scale) - 8))

class Battlefield:
    def __init__(self, width=1000, height=800):
        self.width = width
        self.height = height
        self.red_units = []
        self.blue_units = []
        self.strategic_points = []
        self.terrain = np.zeros((width//20, height//20))
        self.generate_terrain()
        self.generate_strategic_points()
        self.generate_initial_units()
        self.red_score = 0
        self.blue_score = 0
        self.resource_history = []
        self.battle_history = []
        self.time_step = 0
        
    def generate_terrain(self):
        # 生成地形 (0:平原, 1:森林, 2:山地, 3:水域)
        for x in range(self.terrain.shape[0]):
            for y in range(self.terrain.shape[1]):
                # 使用柏林噪声生成地形
                nx = x / self.terrain.shape[0] - 0.5
                ny = y / self.terrain.shape[1] - 0.5
                d = 2 * max(abs(nx), abs(ny))
                elevation = (1 + math.sin(3 * x + 2 * y)) / 2
                moisture = (1 + math.sin(2 * x + 5 * y)) / 2
                
                if d > 0.8:
                    self.terrain[x, y] = 2  # 山地
                elif elevation < 0.3:
                    self.terrain[x, y] = 3  # 水域
                elif moisture > 0.7:
                    self.terrain[x, y] = 1  # 森林
                else:
                    self.terrain[x, y] = 0  # 平原
    
    def generate_strategic_points(self):
        # 创建战略点
        points = [
            (200, 200, 0),  # 指挥所
            (800, 200, 1),  # 资源点
            (200, 600, 2),  # 雷达站
            (800, 600, 3),  # 机场
            (500, 400, 1),  # 中心资源点
        ]
        
        for i, (x, y, ptype) in enumerate(points):
            self.strategic_points.append(StrategicPoint(x, y, i, ptype))
    
    def generate_initial_units(self):
        # 红方初始单位
        for i in range(5):
            self.red_units.append(MilitaryUnit(100 + i*30, 100, 0, 0, i))
        for i in range(3):
            self.red_units.append(MilitaryUnit(100 + i*40, 150, 1, 0, 5+i))
        self.red_units.append(MilitaryUnit(200, 200, 4, 0, 8))
        
        # 蓝方初始单位
        for i in range(5):
            self.blue_units.append(MilitaryUnit(900 - i*30, 700, 0, 1, i))
        for i in range(3):
            self.blue_units.append(MilitaryUnit(900 - i*40, 650, 1, 1, 5+i))
        self.blue_units.append(MilitaryUnit(800, 600, 4, 1, 8))
    
    def draw_terrain(self, screen, offset_x, offset_y, scale):
        cell_size = 20
        for x in range(0, self.width, cell_size):
            for y in range(0, self.height, cell_size):
                tx = x // cell_size
                ty = y // cell_size
                if tx < self.terrain.shape[0] and ty < self.terrain.shape[1]:
                    terrain_type = self.terrain[tx, ty]
                    color = TERRAIN_COLORS[int(terrain_type)]
                    pygame.draw.rect(screen, color, 
                                   (offset_x + x*scale/cell_size, 
                                    offset_y + y*scale/cell_size, 
                                    scale, scale))
    
    def draw(self, screen, offset_x, offset_y, scale):
        # 绘制地形
        self.draw_terrain(screen, offset_x, offset_y, scale)
        
        # 绘制战略点
        for point in self.strategic_points:
            point.draw(screen, offset_x, offset_y, scale)
        
        # 绘制红方单位
        for unit in self.red_units:
            if unit.status == "active":
                unit.draw(screen, offset_x, offset_y, scale)
        
        # 绘制蓝方单位
        for unit in self.blue_units:
            if unit.status == "active":
                unit.draw(screen, offset_x, offset_y, scale)
    
    def update(self):
        self.time_step += 1
        
        # 更新单位
        for unit in self.red_units + self.blue_units:
            if unit.status == "active":
                unit.update()
        
        # 简单的AI行为
        self.simple_ai_actions()
        
        # 控制点检测
        self.check_point_control()
        
        # 计分
        self.update_scores()
        
        # 记录资源历史
        if self.time_step % 10 == 0:
            red_res = sum(1 for p in self.strategic_points if p.controlled_by == 0)
            blue_res = sum(1 for p in self.strategic_points if p.controlled_by == 1)
            self.resource_history.append((red_res, blue_res))
        
        # 清理被摧毁的单位
        self.red_units = [u for u in self.red_units if u.status != "destroyed"]
        self.blue_units = [u for u in self.blue_units if u.status != "destroyed"]
    
    def simple_ai_actions(self):
        # 红方AI行为
        for unit in self.red_units:
            if unit.target is None or random.random() < 0.02:
                # 寻找最近的战略点或敌方单位
                closest_target = None
                min_dist = float('inf')
                
                # 检查战略点
                for point in self.strategic_points:
                    if point.controlled_by != 0:  # 未被红方控制
                        dist = math.sqrt((unit.x - point.x)**2 + (unit.y - point.y)**2)
                        if dist < min_dist:
                            min_dist = dist
                            closest_target = ("point", point)
                
                # 检查敌方单位
                for enemy in self.blue_units:
                    if enemy.status == "active":
                        dist = math.sqrt((unit.x - enemy.x)**2 + (unit.y - enemy.y)**2)
                        if dist < unit.range * 1.2 and dist < min_dist:
                            min_dist = dist
                            closest_target = ("unit", enemy)
                
                if closest_target:
                    if closest_target[0] == "point":
                        unit.target = closest_target[1]
                        unit.path = []
                    else:
                        unit.target = closest_target[1]
            
            if unit.target:
                if isinstance(unit.target, StrategicPoint):
                    # 移动到战略点
                    if math.sqrt((unit.x - unit.target.x)**2 + (unit.y - unit.target.y)**2) > 20:
                        unit.move_toward(unit.target.x, unit.target.y)
                elif isinstance(unit.target, MilitaryUnit):
                    # 攻击敌方单位
                    if math.sqrt((unit.x - unit.target.x)**2 + (unit.y - unit.target.y)**2) <= unit.range:
                        unit.attack(unit.target)
                    else:
                        unit.move_toward(unit.target.x, unit.target.y)
        
        # 蓝方AI行为（类似红方）
        for unit in self.blue_units:
            if unit.target is None or random.random() < 0.02:
                closest_target = None
                min_dist = float('inf')
                
                for point in self.strategic_points:
                    if point.controlled_by != 1:
                        dist = math.sqrt((unit.x - point.x)**2 + (unit.y - point.y)**2)
                        if dist < min_dist:
                            min_dist = dist
                            closest_target = ("point", point)
                
                for enemy in self.red_units:
                    if enemy.status == "active":
                        dist = math.sqrt((unit.x - enemy.x)**2 + (unit.y - enemy.y)**2)
                        if dist < unit.range * 1.2 and dist < min_dist:
                            min_dist = dist
                            closest_target = ("unit", enemy)
                
                if closest_target:
                    if closest_target[0] == "point":
                        unit.target = closest_target[1]
                        unit.path = []
                    else:
                        unit.target = closest_target[1]
            
            if unit.target:
                if isinstance(unit.target, StrategicPoint):
                    if math.sqrt((unit.x - unit.target.x)**2 + (unit.y - unit.target.y)**2) > 20:
                        unit.move_toward(unit.target.x, unit.target.y)
                elif isinstance(unit.target, MilitaryUnit):
                    if math.sqrt((unit.x - unit.target.x)**2 + (unit.y - unit.target.y)**2) <= unit.range:
                        unit.attack(unit.target)
                    else:
                        unit.move_toward(unit.target.x, unit.target.y)
    
    def check_point_control(self):
        for point in self.strategic_points:
            red_units_near = 0
            blue_units_near = 0
            
            for unit in self.red_units:
                if unit.status == "active" and math.sqrt((unit.x - point.x)**2 + (unit.y - point.y)**2) < 50:
                    red_units_near += 1
            
            for unit in self.blue_units:
                if unit.status == "active" and math.sqrt((unit.x - point.x)**2 + (unit.y - point.y)**2) < 50:
                    blue_units_near += 1
            
            if red_units_near > blue_units_near:
                point.last_capture_progress += 0.01 * red_units_near
            elif blue_units_near > red_units_near:
                point.last_capture_progress -= 0.01 * blue_units_near
            
            if point.last_capture_progress >= 1.0 and point.controlled_by != 0:
                point.controlled_by = 0
                point.last_capture_progress = 0
            elif point.last_capture_progress <= -1.0 and point.controlled_by != 1:
                point.controlled_by = 1
                point.last_capture_progress = 0
    
    def update_scores(self):
        self.red_score = 0
        self.blue_score = 0
        
        # 战略点得分
        for point in self.strategic_points:
            if point.controlled_by == 0:
                self.red_score += point.value
            elif point.controlled_by == 1:
                self.blue_score += point.value
        
        # 单位得分
        self.red_score += len(self.red_units) * 10
        self.blue_score += len(self.blue_units) * 10

class DQNAgent:
    """简化的DQN智能体，用于高级决策"""
    def __init__(self, state_size, action_size):
        self.state_size = state_size
        self.action_size = action_size
        self.memory = deque(maxlen=2000)
        self.gamma = 0.95    # 折扣因子
        self.epsilon = 1.0   # 探索率
        self.epsilon_min = 0.01
        self.epsilon_decay = 0.995
        self.learning_rate = 0.001
        self.model = self._build_model()
        self.target_model = self._build_model()
        self.update_target_model()
    
    def _build_model(self):
        model = nn.Sequential(
            nn.Linear(self.state_size, 64),
            nn.ReLU(),
            nn.Linear(64, 64),
            nn.ReLU(),
            nn.Linear(64, self.action_size)
        )
        return model
    
    def update_target_model(self):
        self.target_model.load_state_dict(self.model.state_dict())
    
    def remember(self, state, action, reward, next_state, done):
        self.memory.append((state, action, reward, next_state, done))
    
    def act(self, state):
        if np.random.rand() <= self.epsilon:
            return random.randrange(self.action_size)
        state = torch.tensor(state, dtype=torch.float32).unsqueeze(0)
        act_values = self.model(state)
        return torch.argmax(act_values[0]).item()
    
    def replay(self, batch_size):
        if len(self.memory) < batch_size:
            return
        minibatch = random.sample(self.memory, batch_size)
        
        states, actions, rewards, next_states, dones = zip(*minibatch)
        states = torch.tensor(states, dtype=torch.float32)
        actions = torch.tensor(actions, dtype=torch.long)
        rewards = torch.tensor(rewards, dtype=torch.float32)
        next_states = torch.tensor(next_states, dtype=torch.float32)
        dones = torch.tensor(dones, dtype=torch.float32)
        
        # 计算当前Q值和目标Q值
        current_q = self.model(states).gather(1, actions.unsqueeze(1)).squeeze(1)
        next_q = self.target_model(next_states).max(1)[0]
        target_q = rewards + (1 - dones) * self.gamma * next_q
        
        # 计算损失
        loss = F.mse_loss(current_q, target_q.detach())
        
        # 优化模型
        optimizer = optim.Adam(self.model.parameters(), lr=self.learning_rate)
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        
        # 衰减探索率
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay
    
    def load(self, name):
        self.model.load_state_dict(torch.load(name))
    
    def save(self, name):
        torch.save(self.model.state_dict(), name)

class Simulation:
    def __init__(self):
        self.battlefield = Battlefield()
        self.running = True
        self.paused = False
        self.speed = 1.0
        self.selected_unit = None
        self.view_offset_x = 0
        self.view_offset_y = 0
        self.view_scale = 0.8
        self.dragging = False
        self.last_mouse_pos = (0, 0)
        self.stats_surface = pygame.Surface((300, HEIGHT))
        self.resource_graph_surface = pygame.Surface((300, 200))
        self.update_stats_surface()
        self.update_resource_graph()
        
        # 创建高级决策智能体
        self.red_commander = DQNAgent(20, 5)  # 简化的状态和动作空间
        self.blue_commander = DQNAgent(20, 5)
    
    def update_resource_graph(self):
        if not self.battlefield.resource_history:
            return
            
        fig, ax = plt.subplots(figsize=(3, 2), dpi=100)
        steps = list(range(len(self.battlefield.resource_history)))
        red_res = [r[0] for r in self.battlefield.resource_history]
        blue_res = [r[1] for r in self.battlefield.resource_history]
        
        ax.plot(steps, red_res, 'r-', label='红方')
        ax.plot(steps, blue_res, 'b-', label='蓝方')
        ax.fill_between(steps, red_res, 0, color='red', alpha=0.2)
        ax.fill_between(steps, blue_res, 0, color='blue', alpha=0.2)
        ax.set_title('资源控制历史')
        ax.set_xlabel('时间步')
        ax.set_ylabel('控制点数量')
        ax.legend(loc='upper right')
        ax.grid(True, linestyle='--', alpha=0.6)
        
        canvas = FigureCanvasAgg(fig)
        canvas.draw()
        renderer = canvas.get_renderer()
        raw_data = renderer.tostring_rgb()
        
        self.resource_graph_surface = pygame.image.fromstring(raw_data, 
                                                           canvas.get_width_height(), 
                                                           "RGB")
        plt.close(fig)
    
    def update_stats_surface(self):
        self.stats_surface.fill((20, 30, 40))
        
        # 标题
        title = font_large.render("战场情报面板", True, YELLOW)
        self.stats_surface.blit(title, (20, 20))
        
        # 分数
        score_text = font_medium.render(f"红方得分: {self.battlefield.red_score}", True, RED)
        self.stats_surface.blit(score_text, (20, 70))
        score_text = font_medium.render(f"蓝方得分: {self.battlefield.blue_score}", True, BLUE)
        self.stats_surface.blit(score_text, (20, 100))
        
        # 单位数量
        red_units = len([u for u in self.battlefield.red_units if u.status == "active"])
        blue_units = len([u for u in self.battlefield.blue_units if u.status == "active"])
        unit_text = font_medium.render(f"红方单位: {red_units}", True, RED)
        self.stats_surface.blit(unit_text, (20, 140))
        unit_text = font_medium.render(f"蓝方单位: {blue_units}", True, BLUE)
        self.stats_surface.blit(unit_text, (20, 170))
        
        # 战略点控制
        control_text = font_medium.render("战略点控制:", True, WHITE)
        self.stats_surface.blit(control_text, (20, 210))
        
        y_offset = 240
        for i, point in enumerate(self.battlefield.strategic_points):
            types = ["指挥所", "资源点", "雷达站", "机场"]
            if point.controlled_by == 0:
                ctrl_text = "红方控制"
                color = RED
            elif point.controlled_by == 1:
                ctrl_text = "蓝方控制"
                color = BLUE
            else:
                ctrl_text = "中立"
                color = WHITE
                
            point_text = font_small.render(f"{types[point.point_type]}: {ctrl_text}", True, color)
            self.stats_surface.blit(point_text, (30, y_offset))
            y_offset += 30
        
        # 资源图
        self.stats_surface.blit(self.resource_graph_surface, (0, 450))
        
        # 时间步
        time_text = font_medium.render(f"时间步: {self.battlefield.time_step}", True, CYAN)
        self.stats_surface.blit(time_text, (20, 660))
        
        # 指令
        controls = [
            "控制指令:",
            "空格键: 暂停/继续",
            "鼠标拖动: 移动视角",
            "滚轮: 缩放",
            "鼠标点击: 选择单位",
            "右键: 移动/攻击"
        ]
        
        y_offset = 700
        for text in controls:
            ctrl_text = font_small.render(text, True, GREEN)
            self.stats_surface.blit(ctrl_text, (20, y_offset))
            y_offset += 25
    
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    self.paused = not self.paused
                elif event.key == pygame.K_ESCAPE:
                    self.running = False
                elif event.key == pygame.K_r:
                    self.battlefield = Battlefield()
                    self.update_stats_surface()
                elif event.key == pygame.K_EQUALS:
                    self.speed = min(5.0, self.speed + 0.5)
                elif event.key == pygame.K_MINUS:
                    self.speed = max(0.1, self.speed - 0.5)
            
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # 左键
                    mouse_x, mouse_y = event.pos
                    
                    # 检查是否点击了单位
                    self.selected_unit = None
                    for unit in self.battlefield.red_units + self.battlefield.blue_units:
                        if unit.status == "active":
                            screen_x = self.view_offset_x + unit.x * self.view_scale
                            screen_y = self.view_offset_y + unit.y * self.view_scale
                            distance = math.sqrt((screen_x - mouse_x)**2 + (screen_y - mouse_y)**2)
                            if distance < 15:
                                self.selected_unit = unit
                                break
                
                elif event.button == 3:  # 右键
                    if self.selected_unit:
                        mouse_x, mouse_y = event.pos
                        world_x = (mouse_x - self.view_offset_x) / self.view_scale
                        world_y = (mouse_y - self.view_offset_y) / self.view_scale
                        
                        # 检查是否右键点击了敌方单位
                        target_unit = None
                        for unit in (self.battlefield.blue_units if self.selected_unit.side == 0 else self.battlefield.red_units):
                            if unit.status == "active":
                                distance = math.sqrt((world_x - unit.x)**2 + (world_y - unit.y)**2)
                                if distance < 15:
                                    target_unit = unit
                                    break
                        
                        if target_unit:
                            self.selected_unit.target = target_unit
                        else:
                            self.selected_unit.target = None
                            self.selected_unit.path = []
                            self.selected_unit.move_toward(world_x, world_y)
                
                elif event.button == 4:  # 滚轮上
                    self.view_scale = min(1.5, self.view_scale * 1.1)
                elif event.button == 5:  # 滚轮下
                    self.view_scale = max(0.3, self.view_scale * 0.9)
                
                elif event.button == 2:  # 中键
                    self.dragging = True
                    self.last_mouse_pos = event.pos
            
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 2:
                    self.dragging = False
            
            elif event.type == pygame.MOUSEMOTION:
                if self.dragging:
                    dx = event.pos[0] - self.last_mouse_pos[0]
                    dy = event.pos[1] - self.last_mouse_pos[1]
                    self.view_offset_x += dx
                    self.view_offset_y += dy
                    self.last_mouse_pos = event.pos
    
    def run(self):
        clock = pygame.time.Clock()
        frame_count = 0
        
        while self.running:
            self.handle_events()
            
            if not self.paused:
                for _ in range(int(self.speed)):
                    self.battlefield.update()
                    frame_count += 1
                    
                    # 定期更新统计面板
                    if frame_count % 10 == 0:
                        self.update_stats_surface()
                        if frame_count % 50 == 0:
                            self.update_resource_graph()
            
            # 绘制
            screen.fill(BACKGROUND)
            self.battlefield.draw(screen, self.view_offset_x, self.view_offset_y, self.view_scale)
            
            # 绘制选中单位的信息
            if self.selected_unit:
                pygame.draw.circle(screen, YELLOW, 
                                 (int(self.view_offset_x + self.selected_unit.x * self.view_scale),
                                  int(self.view_offset_y + self.selected_unit.y * self.view_scale)), 
                                 18, 2)
                
                # 绘制状态信息
                info_surface = pygame.Surface((250, 100))
                info_surface.fill((30, 40, 50))
                pygame.draw.rect(info_surface, (60, 70, 90), info_surface.get_rect(), 2)
                
                side = "红方" if self.selected_unit.side == 0 else "蓝方"
                title = font_medium.render(f"{side} {self.selected_unit.unit_type_name()}", True, YELLOW)
                info_surface.blit(title, (10, 5))
                
                status_text = [
                    f"生命值: {self.selected_unit.health}/100",
                    f"弹药: {self.selected_unit.ammo}",
                    f"燃料: {self.selected_unit.fuel}" if self.selected_unit.fuel > 0 else "",
                    f"状态: {self.selected_unit.last_action}"
                ]
                
                y_offset = 35
                for text in status_text:
                    if text:
                        txt = font_small.render(text, True, WHITE)
                        info_surface.blit(txt, (15, y_offset))
                        y_offset += 20
                
                screen.blit(info_surface, (10, 10))
            
            # 绘制统计面板
            screen.blit(self.stats_surface, (WIDTH - 300, 0))
            
            # 绘制速度指示器
            speed_text = font_small.render(f"速度: {self.speed:.1f}x", True, GREEN)
            screen.blit(speed_text, (WIDTH - 150, HEIGHT - 30))
            
            if self.paused:
                paused_text = font_large.render("已暂停", True, YELLOW)
                screen.blit(paused_text, (WIDTH // 2 - 60, 20))
            
            pygame.display.flip()
            clock.tick(60)

# 启动模拟
if __name__ == "__main__":
    sim = Simulation()
    sim.run()
    pygame.quit()
    sys.exit()