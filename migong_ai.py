import sys
import numpy as np
import random
import math
import json
import os
from enum import Enum
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import torch
import torch.nn as nn
import torch.optim as optim
from collections import deque
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QSlider, QLabel, QGroupBox, QTabWidget, QListWidget,
    QFileDialog, QStatusBar, QSplitter, QFrame, QSizePolicy
)
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QPalette, QImage, QPixmap
from PyQt6.QtCore import Qt, QTimer, QSize, QPointF  # 添加 QPointF

# 颜色定义
BACKGROUND = QColor(10, 20, 30)
GRID_COLOR = QColor(35, 55, 75)
WALL_COLOR = QColor(60, 90, 130)
PLAYER_COLORS = [
    QColor(50, 180, 255),    # 蓝色
    QColor(255, 100, 100),   # 红色
    QColor(100, 255, 150),   # 绿色
    QColor(255, 200, 50),    # 黄色
    QColor(200, 100, 255),   # 紫色
]
TARGET_COLOR = QColor(255, 80, 80)
TEXT_COLOR = QColor(220, 220, 220)
BUTTON_COLOR = QColor(60, 100, 160)
BUTTON_HOVER = QColor(80, 130, 200)
PANEL_COLOR = QColor(25, 40, 55)
REWARD_COLOR = QColor(255, 215, 0)
TRAP_COLOR = QColor(220, 80, 60)
PORTAL_COLOR = QColor(180, 70, 200)
HEATMAP_LOW = QColor(30, 30, 150)
HEATMAP_HIGH = QColor(255, 50, 50)
PATH_COLORS = [
    QColor(100, 200, 255, 100),
    QColor(255, 150, 150, 100),
    QColor(150, 255, 180, 100),
    QColor(255, 230, 100, 100),
    QColor(230, 150, 255, 100),
]

# 算法类型枚举
class AlgorithmType(Enum):
    QLEARNING = "Q-learning"
    SARSA = "SARSA"
    DQN = "Deep Q-Network"

# 迷宫类 - 增强版
class AdvancedMaze:
    def __init__(self, width=15, height=15, difficulty=1):
        self.width = width
        self.height = height
        self.difficulty = difficulty
        self.grid = np.zeros((height, width))  # 0: 空, 1: 墙
        self.target_pos = (height-1, width-1)
        self.generate_maze()
        self.rewards = []
        self.traps = []
        self.portals = []
        self.add_special_cells()
        self.time_step = 0
        
    def generate_maze(self):
        # 生成一个随机迷宫（使用递归分割算法）
        self.grid.fill(0)  # 先全部设为空
        
        # 边界设为墙
        self.grid[0, :] = 1
        self.grid[-1, :] = 1
        self.grid[:, 0] = 1
        self.grid[:, -1] = 1
        
        # 递归分割算法
        self._divide(1, 1, self.height-2, self.width-2)
        
        # 确保起点和终点是空的
        self.grid[0][0] = 0
        self.grid[1][0] = 0
        self.grid[0][1] = 0
        self.grid[self.height-1][self.width-1] = 0
        self.grid[self.height-2][self.width-1] = 0
        self.grid[self.height-1][self.width-2] = 0
        
        # 根据难度增加墙壁复杂度
        for _ in range(int(self.difficulty * self.width * self.height / 10)):
            x, y = random.randint(1, self.height-2), random.randint(1, self.width-2)
            if self.grid[x][y] == 0 and (x, y) != (0, 0) and (x, y) != (self.height-1, self.width-1):
                # 添加随机墙
                if random.random() < 0.6:
                    self.grid[x][y] = 1
                # 或者添加一个2x2的墙块
                elif random.random() < 0.3:
                    for dx in range(2):
                        for dy in range(2):
                            if 0 <= x+dx < self.height and 0 <= y+dy < self.width:
                                self.grid[x+dx][y+dy] = 1
    
    def _divide(self, min_x, min_y, max_x, max_y):
        """递归分割迷宫"""
        if max_x - min_x < 2 or max_y - min_y < 2:
            return
        
        # 选择分割方向 (0=水平, 1=垂直)
        if max_x - min_x > max_y - min_y:
            direction = 0  # 水平分割
        elif max_x - min_x < max_y - min_y:
            direction = 1  # 垂直分割
        else:
            direction = random.randint(0, 1)
        
        if direction == 0:  # 水平分割
            wall_x = random.randint(min_x+1, max_x-1)
            # 创建墙
            for y in range(min_y, max_y+1):
                self.grid[wall_x][y] = 1
            
            # 在墙上开一个门
            door_y = random.randint(min_y, max_y)
            self.grid[wall_x][door_y] = 0
            
            # 递归分割两个区域
            self._divide(min_x, min_y, wall_x-1, max_y)
            self._divide(wall_x+1, min_y, max_x, max_y)
        else:  # 垂直分割
            wall_y = random.randint(min_y+1, max_y-1)
            # 创建墙
            for x in range(min_x, max_x+1):
                self.grid[x][wall_y] = 1
            
            # 在墙上开一个门
            door_x = random.randint(min_x, max_x)
            self.grid[door_x][wall_y] = 0
            
            # 递归分割两个区域
            self._divide(min_x, min_y, max_x, wall_y-1)
            self._divide(min_x, wall_y+1, max_x, max_y)
    
    def add_special_cells(self):
        # 添加奖励点
        num_rewards = min(5 + self.difficulty, 10)
        for _ in range(num_rewards):
            x, y = random.randint(0, self.height-1), random.randint(0, self.width-1)
            if (x, y) != (0, 0) and (x, y) != self.target_pos and self.grid[x][y] == 0:
                self.rewards.append((x, y, random.randint(5, 15)))  # 奖励值
        
        # 添加陷阱
        num_traps = min(3 + self.difficulty, 7)
        for _ in range(num_traps):
            x, y = random.randint(0, self.height-1), random.randint(0, self.width-1)
            if (x, y) != (0, 0) and (x, y) != self.target_pos and self.grid[x][y] == 0 and (x, y) not in [r[:2] for r in self.rewards]:
                self.traps.append((x, y, random.randint(-20, -5)))  # 惩罚值
        
        # 添加传送门
        num_portals = min(2 + self.difficulty // 2, 4)
        for _ in range(num_portals):
            x1, y1 = random.randint(0, self.height-1), random.randint(0, self.width-1)
            x2, y2 = random.randint(0, self.height-1), random.randint(0, self.width-1)
            if (x1, y1) != (0, 0) and (x2, y2) != (0, 0) and (x1, y1) != self.target_pos and (x2, y2) != self.target_pos and self.grid[x1][y1] == 0 and self.grid[x2][y2] == 0:
                self.portals.append(((x1, y1), (x2, y2), random.randint(0, 3)))  # 传送门类型
        
    def step(self, action, player_pos):
        """执行动作并返回新位置和奖励"""
        x, y = player_pos
        new_x, new_y = x, y
        
        # 0: 上, 1: 右, 2: 下, 3: 左
        if action == 0 and x > 0: new_x = x - 1
        elif action == 1 and y < self.width-1: new_y = y + 1
        elif action == 2 and x < self.height-1: new_x = x + 1
        elif action == 3 and y > 0: new_y = y - 1
        
        # 检查是否撞墙
        if self.grid[new_x][new_y] == 1:
            return (x, y), -1, False  # 撞墙，位置不变，小惩罚
        
        new_pos = (new_x, new_y)
        reward = 0
        done = False
        
        # 检查是否到达目标
        if new_pos == self.target_pos:
            reward = 100
            done = True
        
        # 检查是否获得奖励
        for i, (rx, ry, rval) in enumerate(self.rewards):
            if new_pos == (rx, ry):
                reward = rval
                self.rewards.pop(i)
                break
        
        # 检查是否触发陷阱
        for i, (tx, ty, tval) in enumerate(self.traps):
            if new_pos == (tx, ty):
                reward = tval
                break
        
        # 检查是否进入传送门
        for portal in self.portals:
            if new_pos == portal[0]:
                new_pos = portal[1]
                reward += 2  # 额外奖励
                break
            elif new_pos == portal[1]:
                new_pos = portal[0]
                reward += 2
                break
        
        # 每走一步有小惩罚，鼓励尽快到达目标
        if not done:
            reward -= 0.1
            
        return new_pos, reward, done

# 简单的DQN网络
class DQN(nn.Module):
    def __init__(self, input_size, output_size):
        super(DQN, self).__init__()
        self.fc1 = nn.Linear(input_size, 64)
        self.fc2 = nn.Linear(64, 64)
        self.fc3 = nn.Linear(64, output_size)
        
    def forward(self, x):
        x = torch.relu(self.fc1(x))
        x = torch.relu(self.fc2(x))
        return self.fc3(x)

# 强化学习智能体基类
class RLAgent:
    def __init__(self, maze, agent_id=0, algorithm=AlgorithmType.QLEARNING):
        self.maze = maze
        self.agent_id = agent_id
        self.algorithm = algorithm
        self.color = PLAYER_COLORS[agent_id % len(PLAYER_COLORS)]
        self.path_color = PATH_COLORS[agent_id % len(PATH_COLORS)]
        self.episode_rewards = []
        self.episode_steps = []
        self.total_reward = 0
        self.episode_count = 0
        self.best_reward = -float('inf')
        self.best_path = []
        self.model_initialized = False
        self.q_table = {}
        
    def initialize_model(self):
        """初始化模型"""
        self.model_initialized = True
        
    def choose_action(self, state):
        """根据当前状态选择动作"""
        return random.randint(0, 3)  # 随机动作
    
    def update_model(self, state, action, reward, next_state, done):
        """更新模型"""
        pass
    
    def decay_exploration(self):
        """降低探索率"""
        pass
    
    def train_episode(self):
        """训练一个回合"""
        state = (0, 0)  # 起点
        total_reward = 0
        steps = 0
        done = False
        path = [state]
        
        while not done and steps < 1000:  # 最多1000步
            action = self.choose_action(state)
            next_state, reward, done = self.maze.step(action, state)
            
            self.update_model(state, action, reward, next_state, done)
            
            state = next_state
            total_reward += reward
            steps += 1
            path.append(state)
            
            if done:
                break
        
        self.episode_rewards.append(total_reward)
        self.episode_steps.append(steps)
        self.total_reward += total_reward
        self.episode_count += 1
        self.decay_exploration()
        
        # 更新最佳路径
        if total_reward > self.best_reward:
            self.best_reward = total_reward
            self.best_path = path
        
        return path, total_reward, steps
    
    def transfer_learning(self, source_agent):
        """迁移学习：从另一个智能体学习"""
        pass
    
    def save_model(self, filename):
        """保存模型"""
        pass
    
    def load_model(self, filename):
        """加载模型"""
        pass

# Q-learning 智能体
class QLearningAgent(RLAgent):
    def __init__(self, maze, agent_id=0, learning_rate=0.1, discount_factor=0.95, 
                 exploration_rate=1.0, min_exploration=0.01, exploration_decay=0.995):
        super().__init__(maze, agent_id, AlgorithmType.QLEARNING)
        self.learning_rate = learning_rate
        self.discount_factor = discount_factor
        self.exploration_rate = exploration_rate
        self.min_exploration = min_exploration
        self.exploration_decay = exploration_decay
        self.actions = [0, 1, 2, 3]  # 上、右、下、左
        
    def get_state_key(self, pos):
        """将位置转换为状态键"""
        return pos
    
    def choose_action(self, state):
        """根据当前状态选择动作"""
        state_key = self.get_state_key(state)
        
        # 初始化Q值
        if state_key not in self.q_table:
            self.q_table[state_key] = np.zeros(len(self.actions))
        
        # ε-贪婪策略
        if np.random.uniform(0, 1) < self.exploration_rate:
            return np.random.choice(self.actions)  # 探索
        else:
            return np.argmax(self.q_table[state_key])  # 利用
    
    def update_model(self, state, action, reward, next_state, done):
        """更新Q表"""
        state_key = self.get_state_key(state)
        next_state_key = self.get_state_key(next_state)
        
        # 初始化Q值
        if next_state_key not in self.q_table:
            self.q_table[next_state_key] = np.zeros(len(self.actions))
        
        # Q-learning更新公式
        current_q = self.q_table[state_key][action]
        max_next_q = np.max(self.q_table[next_state_key]) if not done else 0
        new_q = current_q + self.learning_rate * (reward + self.discount_factor * max_next_q - current_q)
        
        self.q_table[state_key][action] = new_q
    
    def decay_exploration(self):
        """降低探索率"""
        self.exploration_rate = max(self.min_exploration, self.exploration_rate * self.exploration_decay)
    
    def save_model(self, filename):
        """保存模型"""
        if self.algorithm == AlgorithmType.QLEARNING:
            # 保存Q表
            q_table_serializable = {str(k): v.tolist() for k, v in self.q_table.items()}
            model_data = {
                'algorithm': self.algorithm.value,
                'q_table': q_table_serializable,
                'exploration_rate': self.exploration_rate,
                'episode_count': self.episode_count,
                'best_reward': self.best_reward
            }
            with open(filename, 'w') as f:
                json.dump(model_data, f)
    
    def load_model(self, filename):
        """加载模型"""
        if os.path.exists(filename):
            with open(filename, 'r') as f:
                model_data = json.load(f)
                if model_data['algorithm'] == self.algorithm.value:
                    self.q_table = {eval(k): np.array(v) for k, v in model_data['q_table'].items()}
                    self.exploration_rate = model_data['exploration_rate']
                    self.episode_count = model_data.get('episode_count', 0)
                    self.best_reward = model_data.get('best_reward', -float('inf'))
                    self.model_initialized = True
                    return True
        return False

# SARSA 智能体
class SarsaAgent(QLearningAgent):
    def __init__(self, maze, agent_id=0, learning_rate=0.1, discount_factor=0.95, 
                 exploration_rate=1.0, min_exploration=0.01, exploration_decay=0.995):
        super().__init__(maze, agent_id, learning_rate, discount_factor, exploration_rate, min_exploration, exploration_decay)
        self.algorithm = AlgorithmType.SARSA
        self.next_action = None
    
    def choose_action(self, state):
        """根据当前状态选择动作"""
        state_key = self.get_state_key(state)
        
        # 初始化Q值
        if state_key not in self.q_table:
            self.q_table[state_key] = np.zeros(len(self.actions))
        
        # ε-贪婪策略
        if np.random.uniform(0, 1) < self.exploration_rate:
            action = np.random.choice(self.actions)  # 探索
        else:
            action = np.argmax(self.q_table[state_key])  # 利用
        
        # 保存下一个动作用于SARSA更新
        self.next_action = action
        return action
    
    def update_model(self, state, action, reward, next_state, done):
        """更新Q表（SARSA更新）"""
        state_key = self.get_state_key(state)
        next_state_key = self.get_state_key(next_state)
        
        # 初始化Q值
        if next_state_key not in self.q_table:
            self.q_table[next_state_key] = np.zeros(len(self.actions))
        
        # 选择下一个动作
        next_action = self.choose_action(next_state) if not done else None
        
        # SARSA更新公式
        current_q = self.q_table[state_key][action]
        next_q = self.q_table[next_state_key][next_action] if next_action is not None else 0
        new_q = current_q + self.learning_rate * (reward + self.discount_factor * next_q - current_q)
        
        self.q_table[state_key][action] = new_q

# DQN 智能体
class DQNAgent(RLAgent):
    def __init__(self, maze, agent_id=0, learning_rate=0.001, discount_factor=0.95,
                 exploration_rate=1.0, min_exploration=0.01, exploration_decay=0.995, memory_size=10000, batch_size=64):
        super().__init__(maze, agent_id, AlgorithmType.DQN)
        self.learning_rate = learning_rate
        self.discount_factor = discount_factor
        self.exploration_rate = exploration_rate
        self.min_exploration = min_exploration
        self.exploration_decay = exploration_decay
        self.memory = deque(maxlen=memory_size)
        self.batch_size = batch_size
        self.model = DQN(2, 4)  # 输入为位置(x,y)，输出为4个动作
        self.optimizer = optim.Adam(self.model.parameters(), lr=learning_rate)
        self.loss_fn = nn.MSELoss()
        self.actions = [0, 1, 2, 3]
        self.initialize_model()
        
    def get_state_tensor(self, state):
        """将状态转换为张量"""
        return torch.tensor([state[0], state[1]], dtype=torch.float32).unsqueeze(0)
    
    def choose_action(self, state):
        """根据当前状态选择动作"""
        if np.random.uniform(0, 1) < self.exploration_rate:
            return np.random.choice(self.actions)  # 探索
        else:
            state_tensor = self.get_state_tensor(state)
            with torch.no_grad():
                q_values = self.model(state_tensor)
            return torch.argmax(q_values).item()  # 利用
    
    def update_model(self, state, action, reward, next_state, done):
        """存储经验并训练网络"""
        # 存储经验
        self.memory.append((state, action, reward, next_state, done))
        
        # 如果记忆库足够，则进行训练
        if len(self.memory) >= self.batch_size:
            self._train_network()
    
    def _train_network(self):
        """训练DQN网络"""
        # 随机采样一批经验
        batch = random.sample(self.memory, min(len(self.memory), self.batch_size))
        states, actions, rewards, next_states, dones = zip(*batch)
        
        # 转换为张量
        state_tensors = torch.tensor(states, dtype=torch.float32)
        action_tensors = torch.tensor(actions, dtype=torch.long).unsqueeze(1)
        reward_tensors = torch.tensor(rewards, dtype=torch.float32)
        next_state_tensors = torch.tensor(next_states, dtype=torch.float32)
        done_tensors = torch.tensor(dones, dtype=torch.float32)
        
        # 计算当前Q值
        current_q = self.model(state_tensors).gather(1, action_tensors)
        
        # 计算目标Q值
        with torch.no_grad():
            next_q = self.model(next_state_tensors).max(1)[0]
            target_q = reward_tensors + self.discount_factor * next_q * (1 - done_tensors)
        
        # 计算损失
        loss = self.loss_fn(current_q.squeeze(), target_q)
        
        # 反向传播
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()
    
    def decay_exploration(self):
        """降低探索率"""
        self.exploration_rate = max(self.min_exploration, self.exploration_rate * self.exploration_decay)
    
    def save_model(self, filename):
        """保存模型"""
        torch.save({
            'model_state_dict': self.model.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'exploration_rate': self.exploration_rate,
            'episode_count': self.episode_count,
            'best_reward': self.best_reward
        }, filename)
    
    def load_model(self, filename):
        """加载模型"""
        if os.path.exists(filename):
            checkpoint = torch.load(filename)
            self.model.load_state_dict(checkpoint['model_state_dict'])
            self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
            self.exploration_rate = checkpoint['exploration_rate']
            self.episode_count = checkpoint.get('episode_count', 0)
            self.best_reward = checkpoint.get('best_reward', -float('inf'))
            self.model_initialized = True
            return True
        return False

class MazeWidget(QWidget):
    def __init__(self, maze, agents, parent=None):
        super().__init__(parent)
        self.maze = maze
        self.agents = agents
        self.cell_size = 40
        self.offset_x = 50
        self.offset_y = 50
        self.show_heatmap = False
        self.show_best_path = False
        self.selected_agent = 0
        self.setMinimumSize(800, 600)
        
        # 设置背景色
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, BACKGROUND)
        self.setPalette(palette)
        
        # 初始化轨迹表面
        self.trail_surfaces = {}
        for agent in self.agents:
            trail_surface = QImage(self.width(), self.height(), QImage.Format.Format_ARGB32)
            trail_surface.fill(Qt.GlobalColor.transparent)
            self.trail_surfaces[agent.agent_id] = trail_surface
            
        self.episode_paths = {}
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 绘制迷宫
        self.draw_maze(painter)
        
        # 绘制轨迹
        for trail_surface in self.trail_surfaces.values():
            painter.drawImage(0, 0, trail_surface)
        
        # 绘制路径
        for agent in self.agents:
            if agent.agent_id in self.episode_paths:
                self.draw_path(painter, self.episode_paths[agent.agent_id], agent.color)
        
        # 绘制智能体
        for agent in self.agents:
            if agent.agent_id in self.episode_paths:
                self.draw_agent(painter, self.episode_paths[agent.agent_id][-1], agent.color)
        
        # 绘制最佳路径
        if self.show_best_path and self.agents and self.selected_agent < len(self.agents):
            self.draw_path(painter, self.agents[self.selected_agent].best_path, 
                          self.agents[self.selected_agent].color, width=5)
        
        # 绘制热力图
        if self.show_heatmap and self.agents and self.selected_agent < len(self.agents) and \
           self.agents[self.selected_agent].algorithm == AlgorithmType.QLEARNING:
            self.draw_heatmap(painter, self.agents[self.selected_agent])
        
    def draw_maze(self, painter):
        # 绘制网格
        for i in range(self.maze.height):
            for j in range(self.maze.width):
                rect_x = self.offset_x + j * self.cell_size
                rect_y = self.offset_y + i * self.cell_size
                
                # 绘制墙壁
                if self.maze.grid[i][j] == 1:
                    painter.setBrush(WALL_COLOR)
                    painter.setPen(WALL_COLOR.darker(150))
                    painter.drawRect(rect_x, rect_y, self.cell_size, self.cell_size)
                else:
                    painter.setBrush(GRID_COLOR)
                    painter.setPen(GRID_COLOR.darker(150))
                    painter.drawRect(rect_x, rect_y, self.cell_size, self.cell_size)
        
        # 绘制目标
        target_x = self.offset_x + self.maze.target_pos[1] * self.cell_size
        target_y = self.offset_y + self.maze.target_pos[0] * self.cell_size
        painter.setBrush(TARGET_COLOR)
        painter.setPen(TARGET_COLOR.darker(150))
        painter.drawRect(target_x, target_y, self.cell_size, self.cell_size)
        
        # 绘制奖励
        for x, y, val in self.maze.rewards:
            reward_x = self.offset_x + y * self.cell_size + self.cell_size // 4
            reward_y = self.offset_y + x * self.cell_size + self.cell_size // 4
            painter.setBrush(REWARD_COLOR)
            painter.setPen(REWARD_COLOR.darker(150))
            painter.drawEllipse(reward_x, reward_y, self.cell_size // 2, self.cell_size // 2)
            
            # 绘制奖励值
            painter.setPen(Qt.GlobalColor.black)
            font = painter.font()
            font.setPointSize(8)
            painter.setFont(font)
            painter.drawText(reward_x + self.cell_size // 4 - 5, 
                            reward_y + self.cell_size // 4 + 5, 
                            str(val))
        
        # 绘制陷阱
        for x, y, val in self.maze.traps:
            trap_x = self.offset_x + y * self.cell_size
            trap_y = self.offset_y + x * self.cell_size
            
            painter.setBrush(TRAP_COLOR)
            painter.setPen(TRAP_COLOR.darker(150))
            
            points = [
                QPointF(trap_x + self.cell_size // 2, trap_y),
                QPointF(trap_x + self.cell_size, trap_y + self.cell_size // 2),
                QPointF(trap_x + self.cell_size // 2, trap_y + self.cell_size),
                QPointF(trap_x, trap_y + self.cell_size // 2)
            ]
            painter.drawPolygon(points)
            
            # 绘制陷阱值
            painter.setPen(Qt.GlobalColor.black)
            painter.drawText(trap_x + self.cell_size // 2 - 5, 
                            trap_y + self.cell_size // 2 + 5, 
                            str(val))
        
        # 绘制传送门
        for (p1, p2, ptype) in self.maze.portals:
            # 第一个传送门
            p1_x = self.offset_x + p1[1] * self.cell_size + self.cell_size // 4
            p1_y = self.offset_y + p1[0] * self.cell_size + self.cell_size // 4
            color = PORTAL_COLOR if ptype < 2 else QColor(70, 200, 200)
            painter.setBrush(color)
            painter.setPen(color.darker(150))
            painter.drawEllipse(p1_x, p1_y, self.cell_size // 2, self.cell_size // 2)
            
            # 第二个传送门
            p2_x = self.offset_x + p2[1] * self.cell_size + self.cell_size // 4
            p2_y = self.offset_y + p2[0] * self.cell_size + self.cell_size // 4
            painter.drawEllipse(p2_x, p2_y, self.cell_size // 2, self.cell_size // 2)
            
            # 绘制连接线
            center1_x = self.offset_x + p1[1] * self.cell_size + self.cell_size // 2
            center1_y = self.offset_y + p1[0] * self.cell_size + self.cell_size // 2
            center2_x = self.offset_x + p2[1] * self.cell_size + self.cell_size // 2
            center2_y = self.offset_y + p2[0] * self.cell_size + self.cell_size // 2
            painter.drawLine(center1_x, center1_y, center2_x, center2_y)
    
    def draw_path(self, painter, path, color, width=3):
        if len(path) < 2:
            return
        
        points = []
        for pos in path:
            x, y = pos
            # 修复点创建方式
            points.append(QPointF(
                self.offset_x + y * self.cell_size + self.cell_size // 2,
                self.offset_y + x * self.cell_size + self.cell_size // 2
            ))
        
        pen = QPen(color, width)
        painter.setPen(pen)
        for i in range(1, len(points)):
            painter.drawLine(points[i-1], points[i])
        
        # 绘制起点和终点
        if points:
            painter.setBrush(color)
            painter.drawEllipse(points[0], 8, 8)
            painter.setBrush(TARGET_COLOR)
            painter.drawEllipse(points[-1], 8, 8)
    
    def draw_agent(self, painter, pos, color):
        x, y = pos
        center_x = self.offset_x + y * self.cell_size + self.cell_size // 2
        center_y = self.offset_y + x * self.cell_size + self.cell_size // 2
        radius = self.cell_size // 3
        
        # 绘制智能体
        painter.setBrush(color)
        painter.setPen(color.darker(150))
        painter.drawEllipse(center_x - radius, center_y - radius, radius * 2, radius * 2)
        
        # 绘制方向指示器
        painter.setBrush(Qt.GlobalColor.white)
        painter.drawEllipse(center_x - radius // 2, center_y - radius // 2, radius, radius)
    
    def draw_heatmap(self, painter, agent):
        if not hasattr(agent, 'q_table') or not agent.q_table:
            return
        
        # 计算最大Q值
        max_q = max(np.max(q_values) for q_values in agent.q_table.values()) if agent.q_table else 1
        
        # 绘制每个单元格的价值
        for i in range(self.maze.height):
            for j in range(self.maze.width):
                state = (i, j)
                if state in agent.q_table:
                    q_value = np.max(agent.q_table[state])
                    # 根据Q值计算颜色
                    ratio = min(1.0, q_value / max(1, max_q))
                    r = int(HEATMAP_LOW.red() + ratio * (HEATMAP_HIGH.red() - HEATMAP_LOW.red()))
                    g = int(HEATMAP_LOW.green() + ratio * (HEATMAP_HIGH.green() - HEATMAP_LOW.green()))
                    b = int(HEATMAP_LOW.blue() + ratio * (HEATMAP_HIGH.blue() - HEATMAP_LOW.blue()))
                    color = QColor(r, g, b, 150)
                    
                    rect_x = self.offset_x + j * self.cell_size
                    rect_y = self.offset_y + i * self.cell_size
                    
                    painter.setBrush(color)
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.drawRect(rect_x, rect_y, self.cell_size, self.cell_size)
                    
                    # 绘制Q值
                    if self.cell_size > 30:
                        painter.setPen(Qt.GlobalColor.white)
                        font = painter.font()
                        font.setPointSize(8)
                        painter.setFont(font)
                        painter.drawText(rect_x + self.cell_size // 2 - 10, 
                                        rect_y + self.cell_size // 2 + 5, 
                                        f"{q_value:.1f}")
    
    def update_trail(self, agent_id, path):
        if agent_id not in self.trail_surfaces:
            return
        
        if len(path) < 2:
            return
        
        # 创建临时绘图表面
        trail_surface = self.trail_surfaces[agent_id]
        painter = QPainter(trail_surface)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        color = self.agents[agent_id].path_color
        pen = QPen(color, 2)
        painter.setPen(pen)
        
        points = []
        for pos in path:
            x, y = pos
            # 修复点创建方式 - 使用 QPointF 而不是 Qt.QPointF
            points.append(QPointF(
                self.offset_x + y * self.cell_size + self.cell_size // 2,
                self.offset_y + x * self.cell_size + self.cell_size // 2
            ))
        
        for i in range(1, len(points)):
            painter.drawLine(points[i-1], points[i])
        
        painter.end()
        self.update()
    
    def update_path(self, agent_id, path):
        self.episode_paths[agent_id] = path
        self.update()
    
    def set_show_heatmap(self, show):
        self.show_heatmap = show
        self.update()
    
    def set_show_best_path(self, show):
        self.show_best_path = show
        self.update()
    
    def set_selected_agent(self, agent_id):
        self.selected_agent = agent_id
        self.update()
    
    def reset_trails(self):
        for agent_id in self.trail_surfaces:
            self.trail_surfaces[agent_id].fill(Qt.GlobalColor.transparent)
        self.episode_paths = {}
        self.update()

class TrainingChart(FigureCanvas):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        super().__init__(self.fig)
        self.setParent(parent)
        
        self.ax = self.fig.add_subplot(111)
        self.ax2 = self.ax.twinx()
        
        # 设置背景色
        self.fig.set_facecolor((0.1, 0.1, 0.15))
        self.ax.set_facecolor((0.1, 0.1, 0.15))
        
        # 设置标签颜色
        self.ax.tick_params(colors='white')
        self.ax.xaxis.label.set_color('white')
        self.ax.yaxis.label.set_color('white')
        self.ax.title.set_color('white')
        self.ax2.tick_params(colors='white')
        self.ax2.yaxis.label.set_color('white')
        
        # 设置网格
        self.ax.grid(color=(0.3, 0.3, 0.4))
        
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
    
    def update_chart(self, agents, steps=None):
        self.ax.clear()
        self.ax2.clear()
        
        self.ax.set_title('训练进度比较')
        self.ax.set_xlabel('训练回合')
        self.ax.set_ylabel('回合奖励')
        
        if steps:
            self.ax2.set_ylabel('步数', color='white')
            self.ax2.plot(steps, color='white', linestyle='--', label='步数')
        
        # 绘制每个智能体的奖励曲线
        for i, agent in enumerate(agents):
            if agent.episode_rewards:
                color = (
                    PLAYER_COLORS[i % len(PLAYER_COLORS)].red()/255,
                    PLAYER_COLORS[i % len(PLAYER_COLORS)].green()/255,
                    PLAYER_COLORS[i % len(PLAYER_COLORS)].blue()/255
                )
                self.ax.plot(agent.episode_rewards, label=f"智能体 {i} ({agent.algorithm.value})", color=color)
        
        if agents:
            self.ax.legend()
        
        self.draw()

class AgentInfoPanel(QWidget):
    def __init__(self, agents, parent=None):
        super().__init__(parent)
        self.agents = agents
        self.selected_agent = 0
        
        layout = QVBoxLayout()
        
        # 标题
        self.title_label = QLabel("智能体信息")
        self.title_label.setStyleSheet("font-size: 16pt; font-weight: bold; color: #DCDCDC;")
        layout.addWidget(self.title_label)
        
        # 信息显示
        self.info_label = QLabel()
        self.info_label.setStyleSheet("color: #DCDCDC; font-size: 12pt;")
        self.info_label.setWordWrap(True)
        layout.addWidget(self.info_label)
        
        self.setLayout(layout)
        self.update_info()
    
    def update_info(self):
        if self.selected_agent < len(self.agents):
            agent = self.agents[self.selected_agent]
            info_text = f"""
            <b>算法:</b> {agent.algorithm.value}<br>
            <b>训练回合:</b> {agent.episode_count}<br>
            <b>探索率:</b> {agent.exploration_rate:.4f}<br>
            <b>总奖励:</b> {agent.total_reward:.1f}<br>
            <b>最佳回合奖励:</b> {agent.best_reward:.1f}<br>
            <b>平均奖励:</b> {np.mean(agent.episode_rewards[-10:]) if agent.episode_rewards else 0:.2f}<br>
            <b>平均步数:</b> {np.mean(agent.episode_steps[-10:]) if agent.episode_steps else 0:.2f}
            """
            self.info_label.setText(info_text)
            
            # 设置标题颜色为智能体颜色
            color = agent.color.name()
            self.title_label.setStyleSheet(f"""
                font-size: 16pt; 
                font-weight: bold; 
                color: {color};
                background-color: #19232D;
                padding: 5px;
                border-radius: 5px;
            """)
        else:
            self.info_label.setText("没有选中智能体")
            self.title_label.setStyleSheet("font-size: 16pt; font-weight: bold; color: #DCDCDC;")
    
    def set_selected_agent(self, agent_id):
        self.selected_agent = agent_id
        self.update_info()

class RLControlPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(300)
        
        # 设置背景色
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, PANEL_COLOR)
        self.setPalette(palette)
        
        layout = QVBoxLayout()
        
        # 训练控制
        train_group = QGroupBox("训练控制")
        train_layout = QVBoxLayout()
        
        self.train_one_btn = QPushButton("训练1回合")
        self.train_ten_btn = QPushButton("训练10回合")
        self.train_hundred_btn = QPushButton("训练100回合")
        self.reset_btn = QPushButton("重置智能体")
        
        train_layout.addWidget(self.train_one_btn)
        train_layout.addWidget(self.train_ten_btn)
        train_layout.addWidget(self.train_hundred_btn)
        train_layout.addWidget(self.reset_btn)
        train_group.setLayout(train_layout)
        
        # 智能体管理
        agent_group = QGroupBox("智能体管理")
        agent_layout = QVBoxLayout()
        
        self.add_q_btn = QPushButton("添加Q-learning智能体")
        self.add_sarsa_btn = QPushButton("添加SARSA智能体")
        self.add_dqn_btn = QPushButton("添加DQN智能体")
        self.remove_agent_btn = QPushButton("移除智能体")
        
        agent_layout.addWidget(self.add_q_btn)
        agent_layout.addWidget(self.add_sarsa_btn)
        agent_layout.addWidget(self.add_dqn_btn)
        agent_layout.addWidget(self.remove_agent_btn)
        agent_group.setLayout(agent_layout)
        
        # 模型操作
        model_group = QGroupBox("模型操作")
        model_layout = QVBoxLayout()
        
        self.save_model_btn = QPushButton("保存模型")
        self.load_model_btn = QPushButton("加载模型")
        self.export_data_btn = QPushButton("导出数据")
        self.increase_difficulty_btn = QPushButton("迷宫难度+")
        
        model_layout.addWidget(self.save_model_btn)
        model_layout.addWidget(self.load_model_btn)
        model_layout.addWidget(self.export_data_btn)
        model_layout.addWidget(self.increase_difficulty_btn)
        model_group.setLayout(model_layout)
        
        # 参数控制
        param_group = QGroupBox("学习参数")
        param_layout = QVBoxLayout()
        
        self.lr_slider = self.create_slider("学习率", 0.01, 1.0, 0.1)
        self.df_slider = self.create_slider("折扣因子", 0.8, 0.999, 0.95)
        self.er_slider = self.create_slider("探索率", 0.001, 1.0, 0.1)
        self.ed_slider = self.create_slider("探索衰减", 0.95, 0.9999, 0.995)
        
        param_layout.addWidget(self.lr_slider)
        param_layout.addWidget(self.df_slider)
        param_layout.addWidget(self.er_slider)
        param_layout.addWidget(self.ed_slider)
        param_group.setLayout(param_layout)
        
        # 可视化控制
        vis_group = QGroupBox("可视化选项")
        vis_layout = QVBoxLayout()
        
        self.heatmap_btn = QPushButton("切换热力图 (H)")
        self.best_path_btn = QPushButton("切换最佳路径 (B)")
        
        vis_layout.addWidget(self.heatmap_btn)
        vis_layout.addWidget(self.best_path_btn)
        vis_group.setLayout(vis_layout)
        
        # 添加到主布局
        layout.addWidget(train_group)
        layout.addWidget(agent_group)
        layout.addWidget(model_group)
        layout.addWidget(param_group)
        layout.addWidget(vis_group)
        layout.addStretch()
        
        self.setLayout(layout)
        
        # 设置样式
        self.set_button_style()
    
    def set_button_style(self):
        buttons = [
            self.train_one_btn, self.train_ten_btn, self.train_hundred_btn, self.reset_btn,
            self.add_q_btn, self.add_sarsa_btn, self.add_dqn_btn, self.remove_agent_btn,
            self.save_model_btn, self.load_model_btn, self.export_data_btn, self.increase_difficulty_btn,
            self.heatmap_btn, self.best_path_btn
        ]
        
        style = """
            QPushButton {
                background-color: #3C64A0;
                color: white;
                border: 2px solid #6495ED;
                border-radius: 8px;
                padding: 8px;
                font-size: 12pt;
            }
            QPushButton:hover {
                background-color: #5080C8;
            }
            QPushButton:pressed {
                background-color: #2A4A80;
            }
        """
        
        for btn in buttons:
            btn.setStyleSheet(style)
    
    def create_slider(self, label, min_val, max_val, init_val):
        container = QWidget()
        layout = QVBoxLayout(container)
        
        # 标签
        lbl = QLabel(f"{label}: {init_val:.3f}")
        lbl.setStyleSheet("color: #DCDCDC; font-size: 11pt;")
        layout.addWidget(lbl)
        
        # 滑块
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setMinimum(int(min_val * 1000))
        slider.setMaximum(int(max_val * 1000))
        slider.setValue(int(init_val * 1000))
        slider.setStyleSheet("""
            QSlider::groove:horizontal {
                background: #3C5A80;
                height: 8px;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #6495ED;
                width: 20px;
                height: 20px;
                margin: -6px 0;
                border-radius: 10px;
            }
            QSlider::sub-page:horizontal {
                background: #5080C8;
                border-radius: 4px;
            }
        """)
        layout.addWidget(slider)
        
        # 连接信号
        slider.valueChanged.connect(lambda val, l=lbl, n=label: l.setText(f"{n}: {val/1000:.3f}"))
        
        return container

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("强化学习迷宫逃脱：多算法比较与可视化")
        self.setGeometry(100, 100, 1400, 900)
        
        # 创建迷宫和智能体
        self.maze = AdvancedMaze(difficulty=2)
        self.agents = [
            QLearningAgent(self.maze, agent_id=0, exploration_rate=0.5),
            SarsaAgent(self.maze, agent_id=1, exploration_rate=0.5),
            DQNAgent(self.maze, agent_id=2, exploration_rate=0.5)
        ]
        
        # 状态变量
        self.training = False
        self.training_episodes = 0
        self.training_progress = 0
        self.selected_agent = 0
        self.show_heatmap = False
        self.show_best_path = False
        self.model_filename = "rl_model.pth"
        self.export_filename = "rl_data.csv"
        
        # 创建主布局
        main_widget = QWidget()
        main_layout = QHBoxLayout(main_widget)
        
        # 左侧控制面板
        self.control_panel = RLControlPanel()
        main_layout.addWidget(self.control_panel, 1)
        
        # 右侧区域
        right_panel = QSplitter(Qt.Orientation.Vertical)
        right_panel.setHandleWidth(5)
        right_panel.setStyleSheet("QSplitter::handle { background: #3C5A80; }")
        
        # 迷宫显示区域
        self.maze_widget = MazeWidget(self.maze, self.agents)
        right_panel.addWidget(self.maze_widget)
        
        # 底部信息区域
        bottom_tabs = QTabWidget()
        
        # 图表标签页
        chart_tab = QWidget()
        chart_layout = QVBoxLayout(chart_tab)
        self.training_chart = TrainingChart()
        chart_layout.addWidget(self.training_chart)
        
        # 智能体信息标签页
        info_tab = QWidget()
        info_layout = QVBoxLayout(info_tab)
        self.agent_info = AgentInfoPanel(self.agents)
        info_layout.addWidget(self.agent_info)
        
        # 添加标签页
        bottom_tabs.addTab(chart_tab, "训练图表")
        bottom_tabs.addTab(info_tab, "智能体信息")
        
        right_panel.addWidget(bottom_tabs)
        right_panel.setSizes([600, 300])
        
        main_layout.addWidget(right_panel, 3)
        
        self.setCentralWidget(main_widget)
        
        # 状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.update_status()
        
        # 连接信号
        self.connect_signals()
        
        # 设置样式
        self.setStyleSheet("""
            QMainWindow {
                background-color: #0A141E;
            }
            QGroupBox {
                border: 2px solid #3C5A80;
                border-radius: 10px;
                margin-top: 1ex;
                font-size: 12pt;
                color: #DCDCDC;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                background-color: #19232D;
            }
            QTabWidget::pane {
                border: 1px solid #3C5A80;
                background: #19232D;
            }
            QTabBar::tab {
                background: #3C5A80;
                color: white;
                padding: 8px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background: #5080C8;
            }
        """)
    
    def connect_signals(self):
        # 训练按钮
        self.control_panel.train_one_btn.clicked.connect(lambda: self.start_training(1))
        self.control_panel.train_ten_btn.clicked.connect(lambda: self.start_training(10))
        self.control_panel.train_hundred_btn.clicked.connect(lambda: self.start_training(100))
        self.control_panel.reset_btn.clicked.connect(self.reset_agents)
        
        # 智能体管理
        self.control_panel.add_q_btn.clicked.connect(lambda: self.add_agent(AlgorithmType.QLEARNING))
        self.control_panel.add_sarsa_btn.clicked.connect(lambda: self.add_agent(AlgorithmType.SARSA))
        self.control_panel.add_dqn_btn.clicked.connect(lambda: self.add_agent(AlgorithmType.DQN))
        self.control_panel.remove_agent_btn.clicked.connect(self.remove_agent)
        
        # 模型操作
        self.control_panel.save_model_btn.clicked.connect(self.save_model)
        self.control_panel.load_model_btn.clicked.connect(self.load_model)
        self.control_panel.export_data_btn.clicked.connect(self.export_data)
        self.control_panel.increase_difficulty_btn.clicked.connect(self.increase_difficulty)
        
        # 可视化控制
        self.control_panel.heatmap_btn.clicked.connect(self.toggle_heatmap)
        self.control_panel.best_path_btn.clicked.connect(self.toggle_best_path)
        
        # 键盘快捷键
        self.heatmap_btn = self.control_panel.heatmap_btn
        self.best_path_btn = self.control_panel.best_path_btn
    
    def keyPressEvent(self, event):
        # 热力图切换
        if event.key() == Qt.Key.Key_H:
            self.toggle_heatmap()
        # 最佳路径切换
        elif event.key() == Qt.Key.Key_B:
            self.toggle_best_path()
        # 选择智能体
        elif event.key() == Qt.Key.Key_Up:
            if self.selected_agent < len(self.agents) - 1:
                self.selected_agent += 1
                self.update_selected_agent()
        elif event.key() == Qt.Key.Key_Down:
            if self.selected_agent > 0:
                self.selected_agent -= 1
                self.update_selected_agent()
        else:
            super().keyPressEvent(event)
    
    def start_training(self, episodes):
        self.training = True
        self.training_episodes = episodes
        self.training_progress = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.train_step)
        self.timer.start(10)  # 快速更新以加速训练
    
    def train_step(self):
        if not self.training:
            return
        
        for agent in self.agents:
            path, reward, steps = agent.train_episode()
            self.maze_widget.update_path(agent.agent_id, path)
            self.maze_widget.update_trail(agent.agent_id, path)
        
        self.training_progress += 1
        self.update_status()
        self.update_chart()
        self.agent_info.update_info()
        
        if self.training_progress >= self.training_episodes:
            self.training = False
            self.timer.stop()
    
    def reset_agents(self):
        self.agents = [
            QLearningAgent(self.maze, agent_id=0, exploration_rate=0.5),
            SarsaAgent(self.maze, agent_id=1, exploration_rate=0.5),
            DQNAgent(self.maze, agent_id=2, exploration_rate=0.5)
        ]
        self.maze_widget.reset_trails()
        self.selected_agent = 0
        self.update_selected_agent()
        self.update_chart()
        self.update_status()
    
    def add_agent(self, algorithm):
        agent_id = len(self.agents)
        if algorithm == AlgorithmType.QLEARNING:
            agent = QLearningAgent(self.maze, agent_id, exploration_rate=0.5)
        elif algorithm == AlgorithmType.SARSA:
            agent = SarsaAgent(self.maze, agent_id, exploration_rate=0.5)
        else:  # DQN
            agent = DQNAgent(self.maze, agent_id, exploration_rate=0.5)
        
        self.agents.append(agent)
        self.maze_widget.trail_surfaces[agent_id] = QImage(
            self.maze_widget.width(), self.maze_widget.height(), QImage.Format.Format_ARGB32
        )
        self.maze_widget.trail_surfaces[agent_id].fill(Qt.GlobalColor.transparent)
        self.update_status()
    
    def remove_agent(self):
        if len(self.agents) > 1:
            removed_agent = self.agents.pop()
            if removed_agent.agent_id in self.maze_widget.trail_surfaces:
                del self.maze_widget.trail_surfaces[removed_agent.agent_id]
            if self.selected_agent >= len(self.agents):
                self.selected_agent = len(self.agents) - 1
            self.update_selected_agent()
            self.update_status()
    
    def save_model(self):
        if not self.agents:
            return
        
        filename, _ = QFileDialog.getSaveFileName(
            self, "保存模型", "", "模型文件 (*.pth *.json)"
        )
        if filename:
            self.agents[self.selected_agent].save_model(filename)
            self.status_bar.showMessage(f"模型已保存到: {filename}", 5000)
    
    def load_model(self):
        if not self.agents:
            return
        
        filename, _ = QFileDialog.getOpenFileName(
            self, "加载模型", "", "模型文件 (*.pth *.json)"
        )
        if filename and self.agents[self.selected_agent].load_model(filename):
            self.status_bar.showMessage(f"模型已从 {filename} 加载", 5000)
            self.update_chart()
            self.agent_info.update_info()
    
    def export_data(self):
        filename, _ = QFileDialog.getSaveFileName(
            self, "导出训练数据", "", "CSV文件 (*.csv)"
        )
        if filename:
            with open(filename, 'w') as f:
                f.write("agent_id,episode,reward,steps\n")
                for agent in self.agents:
                    for i, (reward, steps) in enumerate(zip(agent.episode_rewards, agent.episode_steps)):
                        f.write(f"{agent.agent_id},{i},{reward},{steps}\n")
            self.status_bar.showMessage(f"数据已导出到: {filename}", 5000)
    
    def increase_difficulty(self):
        self.maze = AdvancedMaze(difficulty=self.maze.difficulty + 1)
        self.maze_widget.maze = self.maze
        self.maze_widget.reset_trails()
        self.update_status()
    
    def toggle_heatmap(self):
        self.show_heatmap = not self.show_heatmap
        self.maze_widget.set_show_heatmap(self.show_heatmap)
        self.update_status()
    
    def toggle_best_path(self):
        self.show_best_path = not self.show_best_path
        self.maze_widget.set_show_best_path(self.show_best_path)
        self.update_status()
    
    def update_selected_agent(self):
        self.maze_widget.set_selected_agent(self.selected_agent)
        self.agent_info.set_selected_agent(self.selected_agent)
        self.update_status()
    
    def update_chart(self):
        steps = self.agents[0].episode_steps if self.agents else None
        self.training_chart.update_chart(self.agents, steps)
    
    def update_status(self):
        status_text = (
            f"迷宫难度: {self.maze.difficulty} | "
            f"智能体数量: {len(self.agents)} | "
            f"当前智能体: {self.selected_agent} | "
            f"热力图: {'开' if self.show_heatmap else '关'} | "
            f"最佳路径: {'开' if self.show_best_path else '关'} | "
            f"训练状态: {'进行中' if self.training else '空闲'}"
        )
        self.status_bar.showMessage(status_text)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())