import sys
import numpy as np
import random
import math
from collections import deque
import matplotlib
matplotlib.rc("font", family='Microsoft YaHei')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QSlider, QSpinBox, QDoubleSpinBox, 
                             QComboBox, QCheckBox, QGroupBox, QTextEdit, QTabWidget,
                             QProgressBar, QFileDialog, QMessageBox, QSplitter, QFrame,
                             QGridLayout, QTableWidget, QTableWidgetItem, QHeaderView)
from PyQt5.QtCore import QTimer, Qt, QThread, pyqtSignal, QSize
from PyQt5.QtGui import QFont, QPalette, QColor, QIcon
from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *
import torch.nn as nn

# 检查OpenGL是否可用
try:
    from PyQt5.QtOpenGL import QGLWidget
    OPENGL_AVAILABLE = True
except ImportError:
    OPENGL_AVAILABLE = False
    print("OpenGL not available, 3D visualization disabled")

# 强化学习神经网络模型
class DQN(nn.Module):
    def __init__(self, input_size, hidden_size, output_size):
        super(DQN, self).__init__()
        self.fc1 = nn.Linear(input_size, hidden_size)
        self.fc2 = nn.Linear(hidden_size, hidden_size)
        self.fc3 = nn.Linear(hidden_size, output_size)
        self.relu = nn.ReLU()
        
    def forward(self, x):
        x = self.relu(self.fc1(x))
        x = self.relu(self.fc2(x))
        return self.fc3(x)

class ReplayBuffer:
    def __init__(self, capacity):
        self.buffer = deque(maxlen=capacity)
    
    def push(self, state, action, reward, next_state, done):
        self.buffer.append((state, action, reward, next_state, done))
    
    def sample(self, batch_size):
        return random.sample(self.buffer, batch_size)
    
    def __len__(self):
        return len(self.buffer)

class MazeEnvironment3D:
    """三维迷宫环境"""
    def __init__(self, size=8, complexity=0.3):
        self.size = size
        self.complexity = complexity
        self.grid = np.zeros((size, size, size))
        self.start_pos = (1, 1, 1)
        self.end_pos = (size-2, size-2, size-2)
        self.dynamic_obstacles = []
        self.teleporters = []  # 传送门
        self.reward_locations = {}  # 特殊奖励位置
        self._generate_maze()
        
    def _generate_maze(self):
        # 创建边界
        self.grid[0, :, :] = 1
        self.grid[-1, :, :] = 1
        self.grid[:, 0, :] = 1
        self.grid[:, -1, :] = 1
        self.grid[:, :, 0] = 1
        self.grid[:, :, -1] = 1
        
        # 使用递归分割算法生成更复杂的迷宫
        self._recursive_division(1, self.size-2, 1, self.size-2, 1, self.size-2)
        
        # 确保起点和终点是开放的
        self.grid[self.start_pos] = 0
        self.grid[self.end_pos] = 0
        
        # 添加动态障碍物
        for _ in range(int(self.size * self.complexity)):
            x, y, z = random.randint(1, self.size-2), random.randint(1, self.size-2), random.randint(1, self.size-2)
            if (x, y, z) != self.start_pos and (x, y, z) != self.end_pos and self.grid[x, y, z] == 0:
                self.dynamic_obstacles.append((x, y, z))
                self.grid[x, y, z] = 2  # 2表示动态障碍物
        
        # 添加传送门
        for _ in range(2):
            x1, y1, z1 = random.randint(1, self.size-2), random.randint(1, self.size-2), random.randint(1, self.size-2)
            x2, y2, z2 = random.randint(1, self.size-2), random.randint(1, self.size-2), random.randint(1, self.size-2)
            if (x1, y1, z1) != self.start_pos and (x1, y1, z1) != self.end_pos and self.grid[x1, y1, z1] == 0:
                if (x2, y2, z2) != self.start_pos and (x2, y2, z2) != self.end_pos and self.grid[x2, y2, z2] == 0:
                    self.teleporters.append(((x1, y1, z1), (x2, y2, z2)))
                    self.grid[x1, y1, z1] = 3  # 3表示传送门
                    self.grid[x2, y2, z2] = 3
        
        # 添加奖励位置
        for _ in range(3):
            x, y, z = random.randint(1, self.size-2), random.randint(1, self.size-2), random.randint(1, self.size-2)
            if (x, y, z) != self.start_pos and (x, y, z) != self.end_pos and self.grid[x, y, z] == 0:
                self.reward_locations[(x, y, z)] = random.choice([5, 10, 15])  # 不同大小的奖励
    
    def _recursive_division(self, x1, x2, y1, y2, z1, z2):
        """递归分割算法生成三维迷宫"""
        if x2 - x1 < 2 or y2 - y1 < 2 or z2 - z1 < 2:
            return
            
        # 随机选择分割平面 (0=x, 1=y, 2=z)
        plane = random.randint(0, 2)
        
        if plane == 0:  # 在x方向分割
            split_x = random.randint(x1 + 1, x2 - 1)
            hole_y = random.randint(y1, y2)
            hole_z = random.randint(z1, z2)
            for y in range(y1, y2 + 1):
                for z in range(z1, z2 + 1):
                    if not (y == hole_y and z == hole_z):
                        self.grid[split_x, y, z] = 1
            self._recursive_division(x1, split_x-1, y1, y2, z1, z2)
            self._recursive_division(split_x+1, x2, y1, y2, z1, z2)
            
        elif plane == 1:  # 在y方向分割
            split_y = random.randint(y1 + 1, y2 - 1)
            hole_x = random.randint(x1, x2)
            hole_z = random.randint(z1, z2)
            for x in range(x1, x2 + 1):
                for z in range(z1, z2 + 1):
                    if not (x == hole_x and z == hole_z):
                        self.grid[x, split_y, z] = 1
            self._recursive_division(x1, x2, y1, split_y-1, z1, z2)
            self._recursive_division(x1, x2, split_y+1, y2, z1, z2)
            
        else:  # 在z方向分割
            split_z = random.randint(z1 + 1, z2 - 1)
            hole_x = random.randint(x1, x2)
            hole_y = random.randint(y1, y2)
            for x in range(x1, x2 + 1):
                for y in range(y1, y2 + 1):
                    if not (x == hole_x and y == hole_y):
                        self.grid[x, y, split_z] = 1
            self._recursive_division(x1, x2, y1, y2, z1, split_z-1)
            self._recursive_division(x1, x2, y1, y2, split_z+1, z2)
    
    def reset(self):
        # 重置动态障碍物
        for x, y, z in self.dynamic_obstacles:
            self.grid[x, y, z] = 2
        return self.start_pos
    
    def step(self, state, action):
        x, y, z = state
        
        # 动作: 0=上, 1=右, 2=下, 3=左, 4=前, 5=后
        if action == 0: y += 1
        elif action == 1: x += 1
        elif action == 2: y -= 1
        elif action == 3: x -= 1
        elif action == 4: z += 1
        elif action == 5: z -= 1
        
        # 边界检查
        if x < 0 or x >= self.size or y < 0 or y >= self.size or z < 0 or z >= self.size:
            return state, -10, False  # 碰到边界，惩罚
        
        # 障碍物检查
        if self.grid[x, y, z] == 1:
            return state, -10, False  # 碰到静态障碍物，惩罚
        
        # 动态障碍物检查
        if self.grid[x, y, z] == 2:
            return state, -10, False  # 碰到动态障碍物，惩罚
        
        # 传送门检查
        if self.grid[x, y, z] == 3:
            for (enter, exit) in self.teleporters:
                if (x, y, z) == enter:
                    x, y, z = exit
                    break
                elif (x, y, z) == exit:
                    x, y, z = enter
                    break
        
        # 奖励位置检查
        reward = -0.1  # 普通移动的奖励
        if (x, y, z) in self.reward_locations:
            reward = self.reward_locations[(x, y, z)]
            # 移除奖励，避免重复获取
            self.reward_locations.pop((x, y, z))
        
        # 到达终点
        if (x, y, z) == self.end_pos:
            return (x, y, z), 100, True
        
        return (x, y, z), reward, False
    
    def update_dynamic_obstacles(self):
        # 随机移动动态障碍物
        for i, (x, y, z) in enumerate(self.dynamic_obstacles):
            # 清除当前位置
            self.grid[x, y, z] = 0
            
            # 随机选择新位置
            dx, dy, dz = random.choice([(1,0,0), (-1,0,0), (0,1,0), (0,-1,0), (0,0,1), (0,0,-1)])
            new_x, new_y, new_z = x + dx, y + dy, z + dz
            
            # 确保新位置在边界内且不是起点或终点
            if (0 < new_x < self.size-1 and 0 < new_y < self.size-1 and 0 < new_z < self.size-1 and
                (new_x, new_y, new_z) != self.start_pos and (new_x, new_y, new_z) != self.end_pos and
                self.grid[new_x, new_y, new_z] == 0):
                x, y, z = new_x, new_y, new_z
            
            # 更新障碍物位置
            self.dynamic_obstacles[i] = (x, y, z)
            self.grid[x, y, z] = 2

class RLAgent:
    """强化学习智能体基类"""
    def __init__(self, env, learning_rate=0.001, discount_factor=0.95, 
                 exploration_rate=1.0, exploration_decay=0.995, min_exploration=0.01):
        self.env = env
        self.lr = learning_rate
        self.gamma = discount_factor
        self.epsilon = exploration_rate
        self.epsilon_decay = exploration_decay
        self.min_epsilon = min_exploration
        
        # 训练统计
        self.episode_rewards = []
        self.episode_steps = []
        self.success_rate = []
        self.success_count = 0
        self.training_history = []
    
    def get_state_features(self, state):
        x, y, z = state
        ex, ey, ez = self.env.end_pos
        # 状态特征：当前位置 + 终点方向 + 周围障碍物信息
        features = [
            x/self.env.size, y/self.env.size, z/self.env.size,
            (ex-x)/self.env.size, (ey-y)/self.env.size, (ez-z)/self.env.size
        ]
        
        # 添加周围环境信息
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                for dz in [-1, 0, 1]:
                    if dx == 0 and dy == 0 and dz == 0:
                        continue
                    nx, ny, nz = x + dx, y + dy, z + dz
                    if 0 <= nx < self.env.size and 0 <= ny < self.env.size and 0 <= nz < self.env.size:
                        features.append(self.env.grid[nx, ny, nz])
                    else:
                        features.append(1)  # 边界
        
        return np.array(features, dtype=np.float32)
    
    def choose_action(self, state):
        raise NotImplementedError
    
    def update(self, state, action, reward, next_state, done):
        raise NotImplementedError
    
    def train(self, episodes=500):
        raise NotImplementedError
    
    def get_optimal_path(self):
        path = []
        state = self.env.reset()
        done = False
        
        while not done and len(path) < 1000:  # 防止无限循环
            path.append(state)
            action = self.choose_action(state)
            state, _, done = self.env.step(state, action)
        
        path.append(state)  # 添加终点
        return path

class QLearningAgent(RLAgent):
    """Q-learning智能体"""
    def __init__(self, env, **kwargs):
        super().__init__(env, **kwargs)
        # 初始化Q表
        self.q_table = np.zeros((env.size, env.size, env.size, 6))
    
    def choose_action(self, state):
        x, y, z = state
        if random.random() < self.epsilon:
            return random.randint(0, 5)  # 随机探索
        else:
            return np.argmax(self.q_table[x, y, z])  # 选择最优动作
    
    def update(self, state, action, reward, next_state, done):
        x, y, z = state
        nx, ny, nz = next_state
        
        current_q = self.q_table[x, y, z, action]
        max_next_q = np.max(self.q_table[nx, ny, nz]) if not done else 0
        
        # Q-learning更新公式
        new_q = current_q + self.lr * (reward + self.gamma * max_next_q - current_q)
        self.q_table[x, y, z, action] = new_q
    
    def train(self, episodes=500):
        self.episode_rewards = []
        self.episode_steps = []
        self.success_rate = []
        self.success_count = 0
        self.training_history = []
        
        for episode in range(episodes):
            state = self.env.reset()
            total_reward = 0
            steps = 0
            done = False
            
            while not done and steps < 1000:  # 防止无限循环
                action = self.choose_action(state)
                next_state, reward, done = self.env.step(state, action)
                
                self.update(state, action, reward, next_state, done)
                
                state = next_state
                total_reward += reward
                steps += 1
                
                if done:
                    self.success_count += 1
                
                # 定期更新动态障碍物
                if steps % 20 == 0:
                    self.env.update_dynamic_obstacles()
            
            # 更新探索率
            self.epsilon = max(self.min_epsilon, self.epsilon * self.epsilon_decay)
            
            # 记录统计数据
            self.episode_rewards.append(total_reward)
            self.episode_steps.append(steps)
            self.success_rate.append(self.success_count / (episode + 1))
            self.training_history.append({
                'episode': episode,
                'reward': total_reward,
                'steps': steps,
                'success': done,
                'epsilon': self.epsilon
            })
        
        return self.training_history

class DQNAgent(RLAgent):
    """深度Q网络智能体"""
    def __init__(self, env, **kwargs):
        super().__init__(env, **kwargs)
        self.state_size = 33  # 6个基本特征 + 27个周围环境特征
        self.action_size = 6
        
        # 神经网络
        self.model = DQN(self.state_size, 128, self.action_size)
        self.target_model = DQN(self.state_size, 128, self.action_size)
        self.optimizer = optim.Adam(self.model.parameters(), lr=self.lr)
        self.memory = ReplayBuffer(10000)
        self.batch_size = 32
        self.update_target_frequency = 100
        self.steps_done = 0
        
        # 同步目标网络
        self.update_target_network()
    
    def update_target_network(self):
        self.target_model.load_state_dict(self.model.state_dict())
    
    def choose_action(self, state):
        if random.random() < self.epsilon:
            return random.randint(0, self.action_size - 1)
        else:
            state_features = self.get_state_features(state)
            state_tensor = torch.FloatTensor(state_features).unsqueeze(0)
            with torch.no_grad():
                q_values = self.model(state_tensor)
            return q_values.max(1)[1].item()
    
    def update(self, state, action, reward, next_state, done):
        state_features = self.get_state_features(state)
        next_state_features = self.get_state_features(next_state)
        
        self.memory.push(state_features, action, reward, next_state_features, done)
        
        if len(self.memory) < self.batch_size:
            return
        
        # 从记忆库中采样
        batch = self.memory.sample(self.batch_size)
        state_batch = torch.FloatTensor([e[0] for e in batch])
        action_batch = torch.LongTensor([e[1] for e in batch])
        reward_batch = torch.FloatTensor([e[2] for e in batch])
        next_state_batch = torch.FloatTensor([e[3] for e in batch])
        done_batch = torch.BoolTensor([e[4] for e in batch])
        
        # 计算当前Q值
        current_q_values = self.model(state_batch).gather(1, action_batch.unsqueeze(1))
        
        # 计算目标Q值
        next_q_values = self.target_model(next_state_batch).max(1)[0].detach()
        target_q_values = reward_batch + (self.gamma * next_q_values * ~done_batch)
        
        # 计算损失
        loss = nn.MSELoss()(current_q_values.squeeze(), target_q_values)
        
        # 反向传播
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()
        
        # 定期更新目标网络
        self.steps_done += 1
        if self.steps_done % self.update_target_frequency == 0:
            self.update_target_network()
    
    def train(self, episodes=500):
        self.episode_rewards = []
        self.episode_steps = []
        self.success_rate = []
        self.success_count = 0
        self.training_history = []
        
        for episode in range(episodes):
            state = self.env.reset()
            total_reward = 0
            steps = 0
            done = False
            
            while not done and steps < 1000:
                action = self.choose_action(state)
                next_state, reward, done = self.env.step(state, action)
                
                self.update(state, action, reward, next_state, done)
                
                state = next_state
                total_reward += reward
                steps += 1
                
                if done:
                    self.success_count += 1
                
                # 定期更新动态障碍物
                if steps % 20 == 0:
                    self.env.update_dynamic_obstacles()
            
            # 更新探索率
            self.epsilon = max(self.min_epsilon, self.epsilon * self.epsilon_decay)
            
            # 记录统计数据
            self.episode_rewards.append(total_reward)
            self.episode_steps.append(steps)
            self.success_rate.append(self.success_count / (episode + 1))
            self.training_history.append({
                'episode': episode,
                'reward': total_reward,
                'steps': steps,
                'success': done,
                'epsilon': self.epsilon
            })
        
        return self.training_history

# 3D可视化组件
if OPENGL_AVAILABLE:
    class GLWidget(QGLWidget):
        def __init__(self, parent=None):
            super(GLWidget, self).__init__(parent)
            self.maze_env = None
            self.agent_pos = (0, 0, 0)
            self.path = []
            self.camera_rotation_x = -30
            self.camera_rotation_y = 45
            self.camera_distance = 20
            self.mode = "third_person"
            self.cell_size = 2.0
            self.agent_size = 0.5
        
        def initializeGL(self):
            glEnable(GL_DEPTH_TEST)
            glEnable(GL_LIGHTING)
            glEnable(GL_LIGHT0)
            glEnable(GL_COLOR_MATERIAL)
            glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
            glClearColor(0.05, 0.05, 0.1, 1.0)
        
        def resizeGL(self, w, h):
            glViewport(0, 0, w, h)
            glMatrixMode(GL_PROJECTION)
            glLoadIdentity()
            gluPerspective(45, w/h, 0.1, 100.0)
            glMatrixMode(GL_MODELVIEW)
        
        def paintGL(self):
            glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
            glLoadIdentity()
            
            if self.mode == "third_person":
                glTranslatef(0, 0, -self.camera_distance)
                glRotatef(self.camera_rotation_x, 1, 0, 0)
                glRotatef(self.camera_rotation_y, 0, 1, 0)
                if self.maze_env:
                    glTranslatef(-self.maze_env.size*self.cell_size/2, 
                                 -self.maze_env.size*self.cell_size/2, 
                                 -self.maze_env.size*self.cell_size/2)
            else:
                x, y, z = self.agent_pos
                gluLookAt(
                    x*self.cell_size, y*self.cell_size, z*self.cell_size + 1,
                    x*self.cell_size, y*self.cell_size, z*self.cell_size,
                    0, 1, 0
                )
            
            self.draw_maze()
        
        def draw_cube(self, x, y, z, size, color):
            vertices = [
                [x, y, z],
                [x+size, y, z],
                [x+size, y+size, z],
                [x, y+size, z],
                [x, y, z+size],
                [x+size, y, z+size],
                [x+size, y+size, z+size],
                [x, y+size, z+size]
            ]
            
            faces = [
                [0, 1, 2, 3],  # 前
                [4, 5, 6, 7],  # 后
                [0, 1, 5, 4],  # 下
                [2, 3, 7, 6],  # 上
                [0, 3, 7, 4],  # 左
                [1, 2, 6, 5]   # 右
            ]
            
            glColor4f(*color)
            glBegin(GL_QUADS)
            for face in faces:
                for vertex in face:
                    glVertex3fv(vertices[vertex])
            glEnd()
            
            glColor4f(color[0]*0.7, color[1]*0.7, color[2]*0.7, color[3])
            glBegin(GL_LINES)
            for face in faces:
                for i in range(4):
                    glVertex3fv(vertices[face[i]])
                    glVertex3fv(vertices[face[(i+1)%4]])
            glEnd()
        
        def draw_sphere(self, x, y, z, radius, color):
            glColor4f(*color)
            glPushMatrix()
            glTranslatef(x, y, z)
            quad = gluNewQuadric()
            gluSphere(quad, radius, 16, 16)
            gluDeleteQuadric(quad)
            glPopMatrix()
        
        def draw_maze(self):
            if self.maze_env is None:
                return
            
            # 绘制迷宫单元格
            for x in range(self.maze_env.size):
                for y in range(self.maze_env.size):
                    for z in range(self.maze_env.size):
                        cell_type = self.maze_env.grid[x, y, z]
                        if cell_type == 1:  # 静态障碍物
                            self.draw_cube(x*self.cell_size, y*self.cell_size, z*self.cell_size, 
                                         self.cell_size, (0.5, 0.2, 0.7, 1.0))
                        elif cell_type == 2:  # 动态障碍物
                            self.draw_cube(x*self.cell_size, y*self.cell_size, z*self.cell_size, 
                                         self.cell_size, (0.8, 0.4, 0.1, 1.0))
                        elif cell_type == 3:  # 传送门
                            self.draw_cube(x*self.cell_size, y*self.cell_size, z*self.cell_size, 
                                         self.cell_size, (0.2, 0.8, 0.8, 1.0))
            
            # 绘制奖励位置
            for (x, y, z), reward in self.maze_env.reward_locations.items():
                color = (1.0, 1.0, 0.0, 1.0) if reward > 0 else (0.5, 0.5, 0.0, 1.0)
                self.draw_sphere(x*self.cell_size + self.cell_size/2, 
                               y*self.cell_size + self.cell_size/2, 
                               z*self.cell_size + self.cell_size/2, 
                               self.cell_size/4, color)
            
            # 绘制起点和终点
            sx, sy, sz = self.maze_env.start_pos
            self.draw_sphere(sx*self.cell_size + self.cell_size/2, 
                           sy*self.cell_size + self.cell_size/2, 
                           sz*self.cell_size + self.cell_size/2, 
                           self.cell_size/3, (0.0, 0.8, 0.0, 1.0))
            
            ex, ey, ez = self.maze_env.end_pos
            self.draw_sphere(ex*self.cell_size + self.cell_size/2, 
                           ey*self.cell_size + self.cell_size/2, 
                           ez*self.cell_size + self.cell_size/2, 
                           self.cell_size/3, (0.9, 0.1, 0.1, 1.0))
            
            # 绘制智能体
            ax, ay, az = self.agent_pos
            self.draw_sphere(ax*self.cell_size + self.cell_size/2, 
                           ay*self.cell_size + self.cell_size/2, 
                           az*self.cell_size + self.cell_size/2, 
                           self.agent_size, (0.2, 0.7, 1.0, 1.0))
            
            # 绘制路径
            if self.path:
                glColor4f(1.0, 1.0, 0.3, 0.8)
                glBegin(GL_LINE_STRIP)
                for x, y, z in self.path:
                    glVertex3f(x*self.cell_size + self.cell_size/2, 
                              y*self.cell_size + self.cell_size/2, 
                              z*self.cell_size + self.cell_size/2)
                glEnd()
        
        def set_maze_env(self, maze_env):
            self.maze_env = maze_env
            self.update()
        
        def set_agent_pos(self, pos):
            self.agent_pos = pos
            self.update()
        
        def set_path(self, path):
            self.path = path
            self.update()
        
        def set_camera_mode(self, mode):
            self.mode = mode
            self.update()
        
        def set_camera_rotation(self, x, y):
            self.camera_rotation_x = x
            self.camera_rotation_y = y
            self.update()
        
        def set_camera_distance(self, distance):
            self.camera_distance = distance
            self.update()

# 训练线程
class TrainingThread(QThread):
    update_signal = pyqtSignal(dict)
    finished_signal = pyqtSignal()
    
    def __init__(self, agent, episodes):
        super().__init__()
        self.agent = agent
        self.episodes = episodes
        self.is_running = True
    
    def run(self):
        history = self.agent.train(self.episodes)
        for record in history:
            if not self.is_running:
                break
            self.update_signal.emit(record)
            self.msleep(10)  # 稍微延迟以便UI更新
        self.finished_signal.emit()
    
    def stop(self):
        self.is_running = False

# 图表组件
class MplCanvas(FigureCanvas):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_subplot(111)
        super(MplCanvas, self).__init__(self.fig)

# 主窗口
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("三维迷宫强化学习系统")
        self.setGeometry(100, 50, 1600, 900)
        
        # 初始化环境和智能体
        self.maze_env = MazeEnvironment3D(8)
        self.agent = QLearningAgent(self.maze_env)
        self.training_thread = None
        
        # 训练状态
        self.training = False
        self.optimal_path = []
        self.show_path = False
        self.agent_position = self.maze_env.start_pos
        
        # 创建UI
        self.create_ui()
        
        # 更新定时器
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_display)
        self.update_timer.start(100)  # 每100ms更新一次
    
    def create_ui(self):
        # 创建中央部件和主布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        
        # 左侧面板 - 3D视图和控制
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # 3D视图
        if OPENGL_AVAILABLE:
            self.gl_widget = GLWidget()
            self.gl_widget.set_maze_env(self.maze_env)
            self.gl_widget.set_agent_pos(self.agent_position)
            left_layout.addWidget(self.gl_widget)
        else:
            self.gl_widget = QLabel("OpenGL not available")
            self.gl_widget.setAlignment(Qt.AlignCenter)
            left_layout.addWidget(self.gl_widget)
        
        # 控制按钮
        control_layout = QHBoxLayout()
        
        self.train_btn = QPushButton("开始训练")
        self.train_btn.clicked.connect(self.start_training)
        control_layout.addWidget(self.train_btn)
        
        self.stop_btn = QPushButton("停止训练")
        self.stop_btn.clicked.connect(self.stop_training)
        self.stop_btn.setEnabled(False)
        control_layout.addWidget(self.stop_btn)
        
        self.show_path_btn = QPushButton("显示最优路径")
        self.show_path_btn.clicked.connect(self.show_optimal_path)
        control_layout.addWidget(self.show_path_btn)
        
        self.reset_btn = QPushButton("重置环境")
        self.reset_btn.clicked.connect(self.reset_environment)
        control_layout.addWidget(self.reset_btn)
        
        left_layout.addLayout(control_layout)
        
        # 右侧面板 - 信息和图表
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # 标签页
        tab_widget = QTabWidget()
        
        # 训练参数标签页
        params_tab = QWidget()
        params_layout = QVBoxLayout(params_tab)
        
        # 算法选择
        algo_group = QGroupBox("算法选择")
        algo_layout = QVBoxLayout(algo_group)
        
        self.algo_combo = QComboBox()
        self.algo_combo.addItems(["Q-learning", "深度Q网络 (DQN)"])
        self.algo_combo.currentTextChanged.connect(self.change_algorithm)
        algo_layout.addWidget(self.algo_combo)
        
        params_layout.addWidget(algo_group)
        
        # 环境参数
        env_group = QGroupBox("环境参数")
        env_layout = QGridLayout(env_group)
        
        env_layout.addWidget(QLabel("迷宫大小:"), 0, 0)
        self.size_spin = QSpinBox()
        self.size_spin.setRange(5, 20)
        self.size_spin.setValue(8)
        self.size_spin.valueChanged.connect(self.change_env_size)
        env_layout.addWidget(self.size_spin, 0, 1)
        
        env_layout.addWidget(QLabel("复杂度:"), 1, 0)
        self.complexity_spin = QDoubleSpinBox()
        self.complexity_spin.setRange(0.1, 0.8)
        self.complexity_spin.setValue(0.3)
        self.complexity_spin.setSingleStep(0.1)
        env_layout.addWidget(self.complexity_spin, 1, 1)
        
        self.dynamic_obstacles_check = QCheckBox("动态障碍物")
        self.dynamic_obstacles_check.setChecked(True)
        env_layout.addWidget(self.dynamic_obstacles_check, 2, 0, 1, 2)
        
        self.teleporters_check = QCheckBox("传送门")
        self.teleporters_check.setChecked(True)
        env_layout.addWidget(self.teleporters_check, 3, 0, 1, 2)
        
        params_layout.addWidget(env_group)
        
        # 训练参数
        train_group = QGroupBox("训练参数")
        train_layout = QGridLayout(train_group)
        
        train_layout.addWidget(QLabel("训练轮数:"), 0, 0)
        self.episodes_spin = QSpinBox()
        self.episodes_spin.setRange(100, 10000)
        self.episodes_spin.setValue(500)
        train_layout.addWidget(self.episodes_spin, 0, 1)
        
        train_layout.addWidget(QLabel("学习率:"), 1, 0)
        self.lr_spin = QDoubleSpinBox()
        self.lr_spin.setRange(0.001, 1.0)
        self.lr_spin.setValue(0.1)
        self.lr_spin.setSingleStep(0.01)
        train_layout.addWidget(self.lr_spin, 1, 1)
        
        train_layout.addWidget(QLabel("折扣因子:"), 2, 0)
        self.gamma_spin = QDoubleSpinBox()
        self.gamma_spin.setRange(0.1, 0.99)
        self.gamma_spin.setValue(0.95)
        self.gamma_spin.setSingleStep(0.01)
        train_layout.addWidget(self.gamma_spin, 2, 1)
        
        train_layout.addWidget(QLabel("探索率:"), 3, 0)
        self.epsilon_spin = QDoubleSpinBox()
        self.epsilon_spin.setRange(0.01, 1.0)
        self.epsilon_spin.setValue(1.0)
        self.epsilon_spin.setSingleStep(0.05)
        train_layout.addWidget(self.epsilon_spin, 3, 1)
        
        train_layout.addWidget(QLabel("探索衰减:"), 4, 0)
        self.epsilon_decay_spin = QDoubleSpinBox()
        self.epsilon_decay_spin.setRange(0.9, 0.999)
        self.epsilon_decay_spin.setValue(0.995)
        self.epsilon_decay_spin.setSingleStep(0.001)
        train_layout.addWidget(self.epsilon_decay_spin, 4, 1)
        
        params_layout.addWidget(train_group)
        
        # 视角控制
        camera_group = QGroupBox("视角控制")
        camera_layout = QVBoxLayout(camera_group)
        
        camera_mode_layout = QHBoxLayout()
        self.third_person_btn = QPushButton("第三人称")
        self.third_person_btn.clicked.connect(lambda: self.set_camera_mode("third_person"))
        camera_mode_layout.addWidget(self.third_person_btn)
        
        self.first_person_btn = QPushButton("第一人称")
        self.first_person_btn.clicked.connect(lambda: self.set_camera_mode("first_person"))
        camera_mode_layout.addWidget(self.first_person_btn)
        
        camera_layout.addLayout(camera_mode_layout)
        
        camera_layout.addWidget(QLabel("相机距离:"))
        self.distance_slider = QSlider(Qt.Horizontal)
        self.distance_slider.setRange(5, 50)
        self.distance_slider.setValue(20)
        self.distance_slider.valueChanged.connect(self.change_camera_distance)
        camera_layout.addWidget(self.distance_slider)
        
        params_layout.addWidget(camera_group)
        
        tab_widget.addTab(params_tab, "参数设置")
        
        # 训练信息标签页
        info_tab = QWidget()
        info_layout = QVBoxLayout(info_tab)
        
        # 训练统计
        stats_group = QGroupBox("训练统计")
        stats_layout = QGridLayout(stats_group)
        
        self.episode_label = QLabel("当前轮数: 0")
        stats_layout.addWidget(self.episode_label, 0, 0)
        
        self.reward_label = QLabel("当前奖励: 0.0")
        stats_layout.addWidget(self.reward_label, 0, 1)
        
        self.steps_label = QLabel("当前步数: 0")
        stats_layout.addWidget(self.steps_label, 1, 0)
        
        self.epsilon_label = QLabel("探索率: 1.0")
        stats_layout.addWidget(self.epsilon_label, 1, 1)
        
        self.success_label = QLabel("成功率: 0.0%")
        stats_layout.addWidget(self.success_label, 2, 0)
        
        info_layout.addWidget(stats_group)
        
        # 训练进度
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        info_layout.addWidget(self.progress_bar)
        
        # 训练日志
        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(150)
        info_layout.addWidget(QLabel("训练日志:"))
        info_layout.addWidget(self.log_text)
        
        tab_widget.addTab(info_tab, "训练信息")
        
        # 图表标签页
        chart_tab = QWidget()
        chart_layout = QVBoxLayout(chart_tab)
        
        self.reward_canvas = MplCanvas(self, width=5, height=4, dpi=100)
        chart_layout.addWidget(QLabel("奖励曲线:"))
        chart_layout.addWidget(self.reward_canvas)
        
        self.steps_canvas = MplCanvas(self, width=5, height=4, dpi=100)
        chart_layout.addWidget(QLabel("步数曲线:"))
        chart_layout.addWidget(self.steps_canvas)
        
        self.success_canvas = MplCanvas(self, width=5, height=4, dpi=100)
        chart_layout.addWidget(QLabel("成功率曲线:"))
        chart_layout.addWidget(self.success_canvas)
        
        tab_widget.addTab(chart_tab, "训练图表")
        
        right_layout.addWidget(tab_widget)
        
        # 添加到主布局
        main_layout.addWidget(left_panel, 2)
        main_layout.addWidget(right_panel, 1)
    
    def change_algorithm(self, algorithm):
        if algorithm == "Q-learning":
            self.agent = QLearningAgent(self.maze_env)
        else:  # DQN
            self.agent = DQNAgent(self.maze_env)
        
        # 更新参数
        self.update_agent_parameters()
        self.log_text.append(f"切换算法: {algorithm}")
    
    def change_env_size(self, size):
        self.maze_env = MazeEnvironment3D(size, self.complexity_spin.value())
        self.change_algorithm(self.algo_combo.currentText())
        if OPENGL_AVAILABLE:
            self.gl_widget.set_maze_env(self.maze_env)
        self.log_text.append(f"迷宫大小更新: {size}")
    
    def update_agent_parameters(self):
        self.agent.lr = self.lr_spin.value()
        self.agent.gamma = self.gamma_spin.value()
        self.agent.epsilon = self.epsilon_spin.value()
        self.agent.epsilon_decay = self.epsilon_decay_spin.value()
        self.agent.min_epsilon = 0.01
    
    def start_training(self):
        if self.training:
            return
        
        self.training = True
        self.train_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        
        # 更新参数
        self.update_agent_parameters()
        
        # 重置训练统计
        self.agent.episode_rewards = []
        self.agent.episode_steps = []
        self.agent.success_rate = []
        self.agent.success_count = 0
        
        # 创建训练线程
        self.training_thread = TrainingThread(self.agent, self.episodes_spin.value())
        self.training_thread.update_signal.connect(self.update_training_info)
        self.training_thread.finished_signal.connect(self.training_finished)
        self.training_thread.start()
        
        self.log_text.append("开始训练...")
    
    def stop_training(self):
        if self.training_thread and self.training_thread.isRunning():
            self.training_thread.stop()
            self.training_thread.wait()
            self.training_finished()
            self.log_text.append("训练已停止")
    
    def training_finished(self):
        self.training = False
        self.train_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.log_text.append("训练完成!")
        
        # 更新图表
        self.update_charts()
    
    def update_training_info(self, record):
        episode = record['episode']
        reward = record['reward']
        steps = record['steps']
        epsilon = record['epsilon']
        
        # 更新统计信息
        self.episode_label.setText(f"当前轮数: {episode+1}")
        self.reward_label.setText(f"当前奖励: {reward:.2f}")
        self.steps_label.setText(f"当前步数: {steps}")
        self.epsilon_label.setText(f"探索率: {epsilon:.3f}")
        
        # 更新进度条
        progress = int((episode + 1) / self.episodes_spin.value() * 100)
        self.progress_bar.setValue(progress)
        
        # 更新成功率
        if self.agent.success_rate:
            success_rate = self.agent.success_rate[-1] * 100
            self.success_label.setText(f"成功率: {success_rate:.1f}%")
    
    def update_charts(self):
        # 更新奖励图表
        self.reward_canvas.axes.clear()
        if self.agent.episode_rewards:
            self.reward_canvas.axes.plot(self.agent.episode_rewards, 'b-')
            self.reward_canvas.axes.set_title('每轮奖励')
            self.reward_canvas.axes.set_xlabel('训练轮数')
            self.reward_canvas.axes.set_ylabel('奖励')
        self.reward_canvas.draw()
        
        # 更新步数图表
        self.steps_canvas.axes.clear()
        if self.agent.episode_steps:
            self.steps_canvas.axes.plot(self.agent.episode_steps, 'r-')
            self.steps_canvas.axes.set_title('每轮步数')
            self.steps_canvas.axes.set_xlabel('训练轮数')
            self.steps_canvas.axes.set_ylabel('步数')
        self.steps_canvas.draw()
        
        # 更新成功率图表
        self.success_canvas.axes.clear()
        if self.agent.success_rate:
            self.success_canvas.axes.plot(self.agent.success_rate, 'g-')
            self.success_canvas.axes.set_title('成功率')
            self.success_canvas.axes.set_xlabel('训练轮数')
            self.success_canvas.axes.set_ylabel('成功率')
        self.success_canvas.draw()
    
    def show_optimal_path(self):
        self.optimal_path = self.agent.get_optimal_path()
        self.show_path = True
        if OPENGL_AVAILABLE:
            self.gl_widget.set_path(self.optimal_path)
        self.log_text.append("显示最优路径")
    
    def reset_environment(self):
        size = self.size_spin.value()
        complexity = self.complexity_spin.value()
        self.maze_env = MazeEnvironment3D(size, complexity)
        
        # 重新创建智能体
        self.change_algorithm(self.algo_combo.currentText())
        
        # 重置显示
        self.agent_position = self.maze_env.start_pos
        self.optimal_path = []
        self.show_path = False
        
        if OPENGL_AVAILABLE:
            self.gl_widget.set_maze_env(self.maze_env)
            self.gl_widget.set_agent_pos(self.agent_position)
            self.gl_widget.set_path([])
        
        # 重置统计信息
        self.episode_label.setText("当前轮数: 0")
        self.reward_label.setText("当前奖励: 0.0")
        self.steps_label.setText("当前步数: 0")
        self.epsilon_label.setText("探索率: 1.0")
        self.success_label.setText("成功率: 0.0%")
        self.progress_bar.setValue(0)
        
        self.log_text.append("环境已重置")
    
    def set_camera_mode(self, mode):
        if OPENGL_AVAILABLE:
            self.gl_widget.set_camera_mode(mode)
    
    def change_camera_distance(self, distance):
        if OPENGL_AVAILABLE:
            self.gl_widget.set_camera_distance(distance)
    
    def update_display(self):
        # 更新智能体位置显示
        if OPENGL_AVAILABLE and not self.training:
            self.gl_widget.set_agent_pos(self.agent_position)
            self.gl_widget.update()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 设置应用程序样式
    app.setStyle('Fusion')
    
    # 创建并显示主窗口
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec_())