import sys
import numpy as np
import random
import cv2
import time
import json
import os
from collections import deque, namedtuple
from datetime import datetime
from enum import Enum
import matplotlib
matplotlib.rc("font", family='Microsoft YaHei')
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
from torch.utils.tensorboard import SummaryWriter

from PyQt5.QtWidgets import (QApplication, QMainWindow, QPushButton, QLineEdit,
                            QLabel, QVBoxLayout, QWidget, QTextEdit, QHBoxLayout, 
                            QProgressBar, QComboBox, QCheckBox, QSlider, QTabWidget,
                            QGroupBox, QSpinBox, QDoubleSpinBox, QRadioButton, QTableWidget,
                            QTableWidgetItem, QTreeWidget, QTreeWidgetItem, QListView, QSplitter,
                            QFileDialog, QMessageBox, QToolBar, QStatusBar, QAction, QMenu, QDockWidget)
from PyQt5.QtCore import QTimer, Qt, QRect, QPoint, QSize, QThread, QStringListModel, pyqtSignal
from PyQt5.QtGui import QPainter, QColor, QFont, QImage, QPixmap, QIcon, QPalette

# 定义动作类型枚举
class ActionType(Enum):
    CLICK = 0
    INPUT_TEXT = 1
    SELECT_ITEM = 2
    DRAG_SLIDER = 3
    CHECK_TOGGLE = 4
    TAB_SWITCH = 5
    MENU_SELECT = 6
    SCROLL = 7
    DOUBLE_CLICK = 8
    RIGHT_CLICK = 9
    DRAG_DROP = 10

# 定义高级经验回放缓冲区
class PrioritizedReplayBuffer:
    def __init__(self, capacity, alpha=0.6, beta=0.4, beta_increment=0.001):
        self.capacity = capacity
        self.alpha = alpha
        self.beta = beta
        self.beta_increment = beta_increment
        self.buffer = []
        self.pos = 0
        self.priorities = np.zeros((capacity,), dtype=np.float32)
        
    def push(self, state, action, reward, next_state, done):
        max_prio = self.priorities.max() if self.buffer else 1.0
        
        if len(self.buffer) < self.capacity:
            self.buffer.append((state, action, reward, next_state, done))
        else:
            self.buffer[self.pos] = (state, action, reward, next_state, done)
        
        self.priorities[self.pos] = max_prio
        self.pos = (self.pos + 1) % self.capacity
    
    def sample(self, batch_size):
        if len(self.buffer) == self.capacity:
            prios = self.priorities
        else:
            prios = self.priorities[:self.pos]
        
        probs = prios ** self.alpha
        probs /= probs.sum()
        
        indices = np.random.choice(len(self.buffer), batch_size, p=probs)
        samples = [self.buffer[idx] for idx in indices]
        
        self.beta = min(1.0, self.beta + self.beta_increment)
        
        total = len(self.buffer)
        weights = (total * probs[indices]) ** (-self.beta)
        weights /= weights.max()
        weights = np.array(weights, dtype=np.float32)
        
        batch = list(zip(*samples))
        states = np.array(batch[0])
        actions = np.array(batch[1])
        rewards = np.array(batch[2])
        next_states = np.array(batch[3])
        dones = np.array(batch[4])
        
        return states, actions, rewards, next_states, dones, indices, weights
    
    def update_priorities(self, indices, priorities):
        for idx, prio in zip(indices, priorities):
            self.priorities[idx] = prio
    
    def __len__(self):
        return len(self.buffer)

# 定义Noisy线性层
class NoisyLinear(nn.Module):
    def __init__(self, in_features, out_features, std_init=0.4):
        super(NoisyLinear, self).__init__()
        
        self.in_features = in_features
        self.out_features = out_features
        self.std_init = std_init
        
        self.weight_mu = nn.Parameter(torch.FloatTensor(out_features, in_features))
        self.weight_sigma = nn.Parameter(torch.FloatTensor(out_features, in_features))
        self.register_buffer('weight_epsilon', torch.FloatTensor(out_features, in_features))
        
        self.bias_mu = nn.Parameter(torch.FloatTensor(out_features))
        self.bias_sigma = nn.Parameter(torch.FloatTensor(out_features))
        self.register_buffer('bias_epsilon', torch.FloatTensor(out_features))
        
        self.reset_parameters()
        self.reset_noise()
    
    def reset_parameters(self):
        mu_range = 1 / np.sqrt(self.in_features)
        
        self.weight_mu.data.uniform_(-mu_range, mu_range)
        self.weight_sigma.data.fill_(self.std_init / np.sqrt(self.in_features))
        
        self.bias_mu.data.uniform_(-mu_range, mu_range)
        self.bias_sigma.data.fill_(self.std_init / np.sqrt(self.out_features))
    
    def reset_noise(self):
        epsilon_in = self.scale_noise(self.in_features)
        epsilon_out = self.scale_noise(self.out_features)
        
        self.weight_epsilon.copy_(epsilon_out.ger(epsilon_in))
        self.bias_epsilon.copy_(epsilon_out)
    
    def forward(self, x):
        if self.training:
            weight = self.weight_mu + self.weight_sigma * self.weight_epsilon
            bias = self.bias_mu + self.bias_sigma * self.bias_epsilon
        else:
            weight = self.weight_mu
            bias = self.bias_mu
        
        return F.linear(x, weight, bias)
    
    @staticmethod
    def scale_noise(size):
        x = torch.randn(size)
        return x.sign().mul(x.abs().sqrt())

# 定义Dueling DQN网络
class DuelingDQN(nn.Module):
    def __init__(self, state_dim, action_dim, hidden_dim=512, noisy=False):
        super(DuelingDQN, self).__init__()
        
        self.noisy = noisy
        
        if noisy:
            self.feature = nn.Sequential(
                NoisyLinear(state_dim, hidden_dim),
                nn.ReLU(),
                NoisyLinear(hidden_dim, hidden_dim),
                nn.ReLU()
            )
            
            self.advantage = nn.Sequential(
                NoisyLinear(hidden_dim, hidden_dim),
                nn.ReLU(),
                NoisyLinear(hidden_dim, action_dim)
            )
            
            self.value = nn.Sequential(
                NoisyLinear(hidden_dim, hidden_dim),
                nn.ReLU(),
                NoisyLinear(hidden_dim, 1)
            )
        else:
            self.feature = nn.Sequential(
                nn.Linear(state_dim, hidden_dim),
                nn.ReLU(),
                nn.Linear(hidden_dim, hidden_dim),
                nn.ReLU()
            )
            
            self.advantage = nn.Sequential(
                nn.Linear(hidden_dim, hidden_dim),
                nn.ReLU(),
                nn.Linear(hidden_dim, action_dim)
            )
            
            self.value = nn.Sequential(
                nn.Linear(hidden_dim, hidden_dim),
                nn.ReLU(),
                nn.Linear(hidden_dim, 1)
            )
    
    def forward(self, x):
        x = self.feature(x)
        advantage = self.advantage(x)
        value = self.value(x)
        return value + advantage - advantage.mean()
    
    def reset_noise(self):
        if self.noisy:
            for module in self.modules():
                if isinstance(module, NoisyLinear):
                    module.reset_noise()

# Rainbow DQN算法
class RainbowDQNAgent:
    def __init__(self, state_dim, action_dim, lr=1e-4, gamma=0.99, 
                 buffer_size=100000, batch_size=64, tau=0.005, 
                 noisy=True, prioritized=True, n_step=3):
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.gamma = gamma
        self.batch_size = batch_size
        self.tau = tau
        self.n_step = n_step
        
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        # 创建策略网络和目标网络
        self.policy_net = DuelingDQN(state_dim, action_dim, noisy=noisy).to(self.device)
        self.target_net = DuelingDQN(state_dim, action_dim, noisy=noisy).to(self.device)
        self.target_net.load_state_dict(self.policy_net.state_dict())
        
        self.optimizer = optim.Adam(self.policy_net.parameters(), lr=lr)
        self.prioritized = prioritized
        
        if prioritized:
            self.memory = PrioritizedReplayBuffer(buffer_size)
        else:
            self.memory = ReplayBuffer(buffer_size)
        
        self.n_step_buffer = deque(maxlen=n_step)
        self.steps_done = 0
        
    def get_action(self, state, eval=False):
        state = torch.FloatTensor(state).unsqueeze(0).to(self.device)
        q_values = self.policy_net(state)
        action = q_values.max(1)[1].item()
            
        self.steps_done += 1
        return action
    
    def push_memory(self, state, action, reward, next_state, done):
        if self.prioritized:
            self.memory.push(state, action, reward, next_state, done)
        else:
            self.memory.push(state, action, reward, next_state, done)
    
    def learn(self):
        if len(self.memory) < self.batch_size:
            return None, None
        
        if self.prioritized:
            states, actions, rewards, next_states, dones, indices, weights = self.memory.sample(self.batch_size)
            weights = torch.FloatTensor(weights).to(self.device)
        else:
            states, actions, rewards, next_states, dones = self.memory.sample(self.batch_size)
            indices, weights = None, None
        
        states = torch.FloatTensor(states).to(self.device)
        actions = torch.LongTensor(actions).unsqueeze(1).to(self.device)
        rewards = torch.FloatTensor(rewards).to(self.device)
        next_states = torch.FloatTensor(next_states).to(self.device)
        dones = torch.FloatTensor(dones).to(self.device)
        
        # 计算当前Q值
        current_q = self.policy_net(states).gather(1, actions).squeeze(1)
        
        # 计算下一个状态的最大Q值（使用目标网络）
        next_actions = self.policy_net(next_states).max(1)[1].unsqueeze(1)
        next_q = self.target_net(next_states).gather(1, next_actions).squeeze(1)
        
        # 计算目标Q值
        target_q = rewards + (1 - dones) * self.gamma * next_q
        
        # 计算损失
        loss = F.mse_loss(current_q, target_q.detach(), reduction='none')
        
        if self.prioritized:
            # 更新优先级
            priorities = loss + 1e-5
            loss = (loss * weights).mean()
            self.memory.update_priorities(indices, priorities.cpu().detach().numpy())
        else:
            loss = loss.mean()
        
        # 优化模型
        self.optimizer.zero_grad()
        loss.backward()
        # 梯度裁剪
        torch.nn.utils.clip_grad_value_(self.policy_net.parameters(), 10)
        self.optimizer.step()
        
        # 更新目标网络
        for target_param, policy_param in zip(self.target_net.parameters(), self.policy_net.parameters()):
            target_param.data.copy_(self.tau * policy_param.data + (1.0 - self.tau) * target_param.data)
        
        # 重置噪声
        self.policy_net.reset_noise()
        self.target_net.reset_noise()
        
        return loss.item(), current_q.mean().item()
    
    def save(self, path):
        torch.save({
            'policy_state_dict': self.policy_net.state_dict(),
            'target_state_dict': self.target_net.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
        }, path)
    
    def load(self, path):
        checkpoint = torch.load(path)
        self.policy_net.load_state_dict(checkpoint['policy_state_dict'])
        self.target_net.load_state_dict(checkpoint['target_state_dict'])
        self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])

# 高级PyQt环境模拟
class AdvancedPyQtEnvironment:
    def __init__(self):
        self.state = None
        self.max_steps = 200
        self.current_step = 0
        self.complexity_level = 1
        self.reset()
        
    def set_complexity(self, level):
        """设置环境复杂度级别 (1-5)"""
        self.complexity_level = max(1, min(5, level))
        self.reset()
        
    def reset(self):
        """重置环境到初始状态"""
        self.current_step = 0
        
        # 根据复杂度级别设置不同的初始状态
        if self.complexity_level == 1:
            self.state = self._get_simple_state()
        elif self.complexity_level == 2:
            self.state = self._get_medium_state()
        elif self.complexity_level == 3:
            self.state = self._get_complex_state()
        elif self.complexity_level == 4:
            self.state = self._get_very_complex_state()
        else:
            self.state = self._get_extreme_state()
            
        return self._get_state_vector()
    
    def _get_simple_state(self):
        """简单任务状态"""
        return {
            'button1_enabled': True,
            'button2_enabled': True,
            'input_field': '',
            'progress_value': 0,
            'status': '初始状态',
            'subtask_completed': [False, False]
        }
    
    def _get_medium_state(self):
        """中等任务状态"""
        return {
            'button1_enabled': True,
            'button2_enabled': True,
            'button3_enabled': True,
            'input_field': '',
            'progress_value': 0,
            'slider_value': 0,
            'checkbox_checked': False,
            'combobox_index': 0,
            'status': '初始状态',
            'subtask_completed': [False, False, False, False]
        }
    
    def _get_complex_state(self):
        """复杂任务状态"""
        return {
            'button1_enabled': True,
            'button2_enabled': True,
            'button3_enabled': True,
            'input_field': '',
            'progress_value': 0,
            'slider_value': 0,
            'checkbox_checked': False,
            'combobox_index': 0,
            'spinbox_value': 0,
            'radiobutton_selected': 0,
            'tab_index': 0,
            'status': '初始状态',
            'subtask_completed': [False, False, False, False, False]
        }
    
    def _get_very_complex_state(self):
        """非常复杂任务状态"""
        return {
            'button1_enabled': True,
            'button2_enabled': True,
            'button3_enabled': True,
            'button4_enabled': True,
            'input_field': '',
            'input_field2': '',
            'progress_value': 0,
            'slider_value': 0,
            'slider_value2': 0,
            'checkbox_checked': False,
            'checkbox2_checked': False,
            'combobox_index': 0,
            'combobox2_index': 0,
            'spinbox_value': 0,
            'spinbox2_value': 0,
            'radiobutton_selected': 0,
            'tab_index': 0,
            'list_selection': 0,
            'tree_selection': '',
            'status': '初始状态',
            'subtask_completed': [False] * 8
        }
    
    def _get_extreme_state(self):
        """极端复杂任务状态"""
        return {
            'button1_enabled': True,
            'button2_enabled': True,
            'button3_enabled': True,
            'button4_enabled': True,
            'button5_enabled': True,
            'input_field': '',
            'input_field2': '',
            'input_field3': '',
            'progress_value': 0,
            'progress_value2': 0,
            'slider_value': 0,
            'slider_value2': 0,
            'slider_value3': 0,
            'checkbox_checked': False,
            'checkbox2_checked': False,
            'checkbox3_checked': False,
            'combobox_index': 0,
            'combobox2_index': 0,
            'combobox3_index': 0,
            'spinbox_value': 0,
            'spinbox2_value': 0,
            'spinbox3_value': 0,
            'radiobutton_selected': 0,
            'radiobutton2_selected': 0,
            'tab_index': 0,
            'tab2_index': 0,
            'list_selection': 0,
            'list2_selection': 0,
            'tree_selection': '',
            'table_selection_row': -1,
            'table_selection_col': -1,
            'menu_selection': '',
            'toolbar_action': '',
            'status': '初始状态',
            'subtask_completed': [False] * 15
        }
    
    def _get_state_vector(self):
        """将状态转换为向量表示"""
        state_values = []
        
        # 根据复杂度级别添加不同的状态特征
        if self.complexity_level >= 1:
            state_values.extend([
                int(self.state['button1_enabled']),
                int(self.state['button2_enabled']),
                len(self.state['input_field']) / 10.0,
                self.state['progress_value'] / 100.0,
                int(self.state['status'] == '成功')
            ])
            
            if self.complexity_level >= 2:
                state_values.extend([
                    int(self.state['button3_enabled']),
                    self.state['slider_value'] / 100.0,
                    int(self.state['checkbox_checked']),
                    self.state['combobox_index'] / 3.0
                ])
                
                if self.complexity_level >= 3:
                    state_values.extend([
                        self.state['spinbox_value'] / 100.0,
                        self.state['radiobutton_selected'] / 2.0,
                        self.state['tab_index'] / 2.0
                    ])
                    
                    if self.complexity_level >= 4:
                        state_values.extend([
                            int(self.state['button4_enabled']),
                            len(self.state['input_field2']) / 10.0,
                            self.state['slider_value2'] / 100.0,
                            int(self.state['checkbox2_checked']),
                            self.state['combobox2_index'] / 3.0,
                            self.state['spinbox2_value'] / 100.0,
                            self.state['list_selection'] / 5.0
                        ])
                        
                        if self.complexity_level >= 5:
                            state_values.extend([
                                int(self.state['button5_enabled']),
                                len(self.state['input_field3']) / 10.0,
                                self.state['progress_value2'] / 100.0,
                                self.state['slider_value3'] / 100.0,
                                int(self.state['checkbox3_checked']),
                                self.state['combobox3_index'] / 3.0,
                                self.state['spinbox3_value'] / 100.0,
                                self.state['radiobutton2_selected'] / 2.0,
                                self.state['tab2_index'] / 2.0,
                                self.state['list2_selection'] / 5.0,
                                (self.state['table_selection_row'] + 1) / 6.0,
                                (self.state['table_selection_col'] + 1) / 4.0
                            ])
        
        # 添加子任务完成状态
        for i in range(len(self.state['subtask_completed'])):
            if i < len(self.state['subtask_completed']):
                state_values.append(int(self.state['subtask_completed'][i]))
            else:
                state_values.append(0)
        
        return np.array(state_values, dtype=np.float32)
    
    def step(self, action):
        """执行一个动作并返回新状态、奖励和是否完成"""
        reward = 0
        done = False
        info = {}
        
        self.current_step += 1
        
        # 动作执行逻辑 - 根据复杂度级别执行不同的动作
        if self.complexity_level == 1:
            reward, done = self._execute_simple_action(action)
        elif self.complexity_level == 2:
            reward, done = self._execute_medium_action(action)
        elif self.complexity_level == 3:
            reward, done = self._execute_complex_action(action)
        elif self.complexity_level == 4:
            reward, done = self._execute_very_complex_action(action)
        else:
            reward, done = self._execute_extreme_action(action)
        
        # 检查是否超过最大步数
        if self.current_step >= self.max_steps:
            done = True
            # 根据完成度给予部分奖励
            completion = sum(self.state['subtask_completed']) / len(self.state['subtask_completed'])
            reward = completion * 10.0
        
        return self._get_state_vector(), reward, done, info
    
    def _execute_simple_action(self, action):
        """执行简单任务动作"""
        reward = 0
        done = False
        
        if action == 0:  # 点击按钮1
            if self.state['button1_enabled']:
                self.state['button1_enabled'] = False
                self.state['status'] = '按钮1已点击'
                self.state['subtask_completed'][0] = True
                reward = 2.0
            else:
                reward = -0.5
                
        elif action == 1:  # 点击按钮2
            if self.state['button2_enabled']:
                self.state['button2_enabled'] = False
                self.state['status'] = '按钮2已点击'
                self.state['subtask_completed'][1] = True
                reward = 2.0
            else:
                reward = -0.5
                
        elif action == 2:  # 在输入框中输入文本
            if len(self.state['input_field']) < 10:
                self.state['input_field'] += 'a'
                self.state['status'] = f'已输入{len(self.state["input_field"])}个字符'
                reward = 0.3
            else:
                reward = -0.3
                
        elif action == 3:  # 增加进度条
            if self.state['progress_value'] < 100:
                self.state['progress_value'] += 10
                self.state['status'] = f'进度: {self.state["progress_value"]}%'
                reward = 0.5
                
                # 检查是否完成任务
                if (not self.state['button1_enabled'] and 
                    not self.state['button2_enabled'] and 
                    len(self.state['input_field']) >= 5 and 
                    self.state['progress_value'] >= 100):
                    self.state['status'] = '任务完成!'
                    reward = 10.0
                    done = True
            else:
                reward = -0.3
        
        return reward, done
    
    def _execute_medium_action(self, action):
        """执行中等任务动作"""
        reward = 0
        done = False
        
        # 这里简化实现，实际应根据动作类型执行相应操作
        # 根据动作索引执行不同的界面操作
        
        # 检查是否完成任务
        if all(self.state['subtask_completed']):
            self.state['status'] = '任务完成!'
            reward = 20.0
            done = True
            
        return reward, done
    
    # 类似地实现其他复杂度级别的动作执行方法
    def _execute_complex_action(self, action):
        return 0, False
    
    def _execute_very_complex_action(self, action):
        return 0, False
    
    def _execute_extreme_action(self, action):
        return 0, False

# 计算机视觉线程
class CVThread(QThread):
    update_signal = pyqtSignal(np.ndarray)
    element_detected = pyqtSignal(str, QRect)
    
    def __init__(self, window):
        super().__init__()
        self.window = window
        self.running = False
        
    def run(self):
        self.running = True
        while self.running:
            # 捕获屏幕图像
            screen = self.capture_screen()
            if screen is not None:
                self.update_signal.emit(screen)
                
                # 检测界面元素
                self.detect_elements(screen)
                
            time.sleep(0.1)  # 降低CPU使用率
    
    def capture_screen(self):
        """捕获当前窗口的截图"""
        try:
            # 在实际应用中，这里会使用更复杂的屏幕捕获技术
            # 这里简化实现，返回一个模拟的图像
            screen = np.zeros((400, 600, 3), dtype=np.uint8)
            cv2.putText(screen, "Screen Capture Simulation", (50, 200), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            # 添加一些模拟的界面元素
            cv2.rectangle(screen, (100, 100), (200, 130), (0, 255, 0), 2)  # 按钮
            cv2.rectangle(screen, (100, 150), (300, 180), (255, 0, 0), 2)  # 输入框
            cv2.rectangle(screen, (100, 200), (400, 230), (0, 0, 255), 2)  # 进度条
            
            return screen
        except Exception as e:
            print(f"Screen capture error: {e}")
            return None
    
    def detect_elements(self, screen):
        """检测屏幕上的界面元素"""
        # 在实际应用中，这里会使用计算机视觉技术检测界面元素
        # 这里简化实现，模拟检测到一些元素
        
        elements = [
            ("button", QRect(100, 100, 100, 30)),
            ("input_field", QRect(100, 150, 200, 30)),
            ("progress_bar", QRect(100, 200, 300, 30))
        ]
        
        for element_type, rect in elements:
            self.element_detected.emit(element_type, rect)
    
    def stop(self):
        self.running = False

# 高级主界面类
class UltraAdvancedMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.env = AdvancedPyQtEnvironment()
        state_dim = len(self.env._get_state_vector())
        action_dim = 50  # 更多的动作数量
        
        self.agent = RainbowDQNAgent(state_dim, action_dim, noisy=True, prioritized=True)
        self.cv_thread = CVThread(self)
        
        self.episodes = 0
        self.total_reward = 0
        self.cumulative_rewards = []
        self.losses = []
        self.q_values = []
        
        self.training = False
        self.evaluation_mode = False
        self.recording = False
        
        # TensorBoard记录器
        self.log_dir = f"runs/{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.writer = SummaryWriter(self.log_dir)
        
        self.init_ui()
        
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle('超强PyQt界面强化学习系统')
        self.setGeometry(100, 100, 1200, 800)
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主分割器
        main_splitter = QSplitter(Qt.Horizontal)
        
        # 左侧面板 - 控制界面
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(5, 5, 5, 5)
        
        # 训练控制组
        control_group = QGroupBox("训练控制")
        control_layout = QVBoxLayout(control_group)
        
        self.train_button = QPushButton('开始训练')
        self.eval_button = QPushButton('开始评估')
        self.reset_button = QPushButton('重置环境')
        self.save_button = QPushButton('保存模型')
        self.load_button = QPushButton('加载模型')
        self.record_button = QPushButton('开始录制')
        
        control_layout.addWidget(self.train_button)
        control_layout.addWidget(self.eval_button)
        control_layout.addWidget(self.reset_button)
        control_layout.addWidget(self.save_button)
        control_layout.addWidget(self.load_button)
        control_layout.addWidget(self.record_button)
        
        # 参数设置组
        params_group = QGroupBox("训练参数")
        params_layout = QVBoxLayout(params_group)
        
        params_layout.addWidget(QLabel("复杂度级别:"))
        self.complexity_combo = QComboBox()
        self.complexity_combo.addItems(["简单", "中等", "复杂", "非常复杂", "极端复杂"])
        self.complexity_combo.setCurrentIndex(2)
        params_layout.addWidget(self.complexity_combo)
        
        params_layout.addWidget(QLabel("学习率:"))
        self.lr_spinbox = QDoubleSpinBox()
        self.lr_spinbox.setRange(0.00001, 0.1)
        self.lr_spinbox.setValue(0.0001)
        self.lr_spinbox.setSingleStep(0.0001)
        params_layout.addWidget(self.lr_spinbox)
        
        params_layout.addWidget(QLabel("折扣因子:"))
        self.gamma_spinbox = QDoubleSpinBox()
        self.gamma_spinbox.setRange(0.1, 0.999)
        self.gamma_spinbox.setValue(0.99)
        self.gamma_spinbox.setSingleStep(0.01)
        params_layout.addWidget(self.gamma_spinbox)
        
        params_layout.addWidget(QLabel("批次大小:"))
        self.batch_spinbox = QSpinBox()
        self.batch_spinbox.setRange(16, 256)
        self.batch_spinbox.setValue(64)
        params_layout.addWidget(self.batch_spinbox)
        
        # 状态信息组
        status_group = QGroupBox("状态信息")
        status_layout = QVBoxLayout(status_group)
        
        self.episode_label = QLabel("回合: 0")
        self.reward_label = QLabel("总奖励: 0.00")
        self.epsilon_label = QLabel("探索率: -")
        self.loss_label = QLabel("损失: -")
        self.q_value_label = QLabel("Q值: -")
        self.step_label = QLabel("步数: 0")
        
        status_layout.addWidget(self.episode_label)
        status_layout.addWidget(self.reward_label)
        status_layout.addWidget(self.epsilon_label)
        status_layout.addWidget(self.loss_label)
        status_layout.addWidget(self.q_value_label)
        status_layout.addWidget(self.step_label)
        
        # 添加到左侧布局
        left_layout.addWidget(control_group)
        left_layout.addWidget(params_group)
        left_layout.addWidget(status_group)
        left_layout.addStretch()
        
        # 右侧面板 - 模拟界面和日志
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # 创建标签页容器
        self.tab_widget = QTabWidget()
        
        # 第一个标签页 - 模拟界面
        tab1 = QWidget()
        tab1_layout = QVBoxLayout(tab1)
        
        # 添加复杂的界面元素
        self._create_complex_ui(tab1_layout)
        
        # 第二个标签页 - 训练图表
        tab2 = QWidget()
        tab2_layout = QVBoxLayout(tab2)
        
        # 创建Matplotlib图表
        self.figure = Figure(figsize=(10, 8), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        tab2_layout.addWidget(self.canvas)
        
        # 初始化图表
        self._init_charts()
        
        # 第三个标签页 - 计算机视觉
        tab3 = QWidget()
        tab3_layout = QVBoxLayout(tab3)
        
        self.cv_label = QLabel()
        self.cv_label.setAlignment(Qt.AlignCenter)
        self.cv_label.setMinimumSize(600, 400)
        self.cv_label.setStyleSheet("border: 1px solid gray;")
        tab3_layout.addWidget(self.cv_label)
        
        # 添加到标签页
        self.tab_widget.addTab(tab1, "模拟界面")
        self.tab_widget.addTab(tab2, "训练图表")
        self.tab_widget.addTab(tab3, "计算机视觉")
        
        # 日志区域
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        
        # 添加到右侧布局
        right_layout.addWidget(self.tab_widget)
        right_layout.addWidget(self.log_text)
        
        # 添加到主分割器
        main_splitter.addWidget(left_panel)
        main_splitter.addWidget(right_panel)
        main_splitter.setSizes([300, 900])
        
        # 设置主布局
        main_layout = QHBoxLayout(central_widget)
        main_layout.addWidget(main_splitter)
        
        # 创建菜单栏
        self._create_menu_bar()
        
        # 创建状态栏
        self.statusBar().showMessage("就绪")
        
        # 连接信号和槽
        self.train_button.clicked.connect(self.toggle_training)
        self.eval_button.clicked.connect(self.toggle_evaluation)
        self.reset_button.clicked.connect(self.reset_environment)
        self.save_button.clicked.connect(self.save_model)
        self.load_button.clicked.connect(self.load_model)
        self.record_button.clicked.connect(self.toggle_recording)
        self.complexity_combo.currentIndexChanged.connect(self.change_complexity)
        
        # 连接CV线程信号
        self.cv_thread.update_signal.connect(self.update_cv_display)
        self.cv_thread.element_detected.connect(self.handle_element_detected)
        
        # 训练定时器
        self.timer = QTimer()
        self.timer.timeout.connect(self.train_step)
        
        # 更新界面状态
        self.update_ui()
        
        # 启动CV线程
        self.cv_thread.start()
        
        self.log_text.append(f"{datetime.now().strftime('%H:%M:%S')} - 系统初始化完成")
    
    def _create_complex_ui(self, layout):
        """创建复杂的界面元素"""
        # 按钮区域
        button_layout = QHBoxLayout()
        self.button1 = QPushButton('按钮1')
        self.button2 = QPushButton('按钮2')
        self.button3 = QPushButton('按钮3')
        self.button4 = QPushButton('按钮4')
        self.button5 = QPushButton('按钮5')
        button_layout.addWidget(self.button1)
        button_layout.addWidget(self.button2)
        button_layout.addWidget(self.button3)
        button_layout.addWidget(self.button4)
        button_layout.addWidget(self.button5)
        layout.addLayout(button_layout)
        
        # 输入区域
        input_layout = QHBoxLayout()
        self.input_label = QLabel('输入框:')
        self.input_field = QLineEdit()
        self.input_label2 = QLabel('输入框2:')
        self.input_field2 = QLineEdit()
        self.input_label3 = QLabel('输入框3:')
        self.input_field3 = QLineEdit()
        input_layout.addWidget(self.input_label)
        input_layout.addWidget(self.input_field)
        input_layout.addWidget(self.input_label2)
        input_layout.addWidget(self.input_field2)
        input_layout.addWidget(self.input_label3)
        input_layout.addWidget(self.input_field3)
        layout.addLayout(input_layout)
        
        # 进度条和滑块
        progress_layout = QHBoxLayout()
        self.progress_label = QLabel('进度:')
        self.progress_bar = QProgressBar()
        self.progress_label2 = QLabel('进度2:')
        self.progress_bar2 = QProgressBar()
        self.slider_label = QLabel('滑块:')
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 100)
        progress_layout.addWidget(self.progress_label)
        progress_layout.addWidget(self.progress_bar)
        progress_layout.addWidget(self.progress_label2)
        progress_layout.addWidget(self.progress_bar2)
        progress_layout.addWidget(self.slider_label)
        progress_layout.addWidget(self.slider)
        layout.addLayout(progress_layout)
        
        # 复选框和单选按钮
        check_radio_layout = QHBoxLayout()
        self.checkbox = QCheckBox('复选框')
        self.checkbox2 = QCheckBox('复选框2')
        self.checkbox3 = QCheckBox('复选框3')
        self.radio1 = QRadioButton('选项1')
        self.radio2 = QRadioButton('选项2')
        self.radio3 = QRadioButton('选项3')
        check_radio_layout.addWidget(self.checkbox)
        check_radio_layout.addWidget(self.checkbox2)
        check_radio_layout.addWidget(self.checkbox3)
        check_radio_layout.addWidget(self.radio1)
        check_radio_layout.addWidget(self.radio2)
        check_radio_layout.addWidget(self.radio3)
        layout.addLayout(check_radio_layout)
        
        # 组合框和微调框
        combo_spin_layout = QHBoxLayout()
        self.combobox_label = QLabel('组合框:')
        self.combobox = QComboBox()
        self.combobox.addItems(['选项1', '选项2', '选项3', '选项4'])
        self.combobox_label2 = QLabel('组合框2:')
        self.combobox2 = QComboBox()
        self.combobox2.addItems(['选项A', '选项B', '选项C', '选项D'])
        self.combobox_label3 = QLabel('组合框3:')
        self.combobox3 = QComboBox()
        self.combobox3.addItems(['项目1', '项目2', '项目3', '项目4'])
        self.spinbox_label = QLabel('微调框:')
        self.spinbox = QSpinBox()
        self.spinbox.setRange(0, 100)
        combo_spin_layout.addWidget(self.combobox_label)
        combo_spin_layout.addWidget(self.combobox)
        combo_spin_layout.addWidget(self.combobox_label2)
        combo_spin_layout.addWidget(self.combobox2)
        combo_spin_layout.addWidget(self.combobox_label3)
        combo_spin_layout.addWidget(self.combobox3)
        combo_spin_layout.addWidget(self.spinbox_label)
        combo_spin_layout.addWidget(self.spinbox)
        layout.addLayout(combo_spin_layout)
        
        # 标签页
        self.tab_widget_inner = QTabWidget()
        tab1_inner = QWidget()
        tab2_inner = QWidget()
        tab3_inner = QWidget()
        
        # 添加一些内容到内部标签页
        tab1_inner_layout = QVBoxLayout(tab1_inner)
        tab1_inner_layout.addWidget(QLabel("标签页1内容"))
        
        tab2_inner_layout = QVBoxLayout(tab2_inner)
        tab2_inner_layout.addWidget(QLabel("标签页2内容"))
        
        tab3_inner_layout = QVBoxLayout(tab3_inner)
        tab3_inner_layout.addWidget(QLabel("标签页3内容"))
        
        self.tab_widget_inner.addTab(tab1_inner, "标签1")
        self.tab_widget_inner.addTab(tab2_inner, "标签2")
        self.tab_widget_inner.addTab(tab3_inner, "标签3")
        layout.addWidget(self.tab_widget_inner)
        
        # 列表和树形视图
        list_tree_layout = QHBoxLayout()
        
        self.list_widget = QListView()
        self.list_model = QStringListModel(["项目1", "项目2", "项目3", "项目4", "项目5"])
        self.list_widget.setModel(self.list_model)
        
        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderLabel("树形结构")
        root_item = QTreeWidgetItem(self.tree_widget, ["根节点"])
        child1 = QTreeWidgetItem(root_item, ["子节点1"])
        child2 = QTreeWidgetItem(root_item, ["子节点2"])
        child3 = QTreeWidgetItem(root_item, ["子节点3"])
        
        list_tree_layout.addWidget(self.list_widget)
        list_tree_layout.addWidget(self.tree_widget)
        layout.addLayout(list_tree_layout)
        
        # 状态显示
        self.status_label = QLabel('状态: 初始状态')
        layout.addWidget(self.status_label)
    
    def _init_charts(self):
        """初始化训练图表"""
        self.figure.clear()
        
        # 创建多个子图
        self.ax1 = self.figure.add_subplot(221)  # 奖励曲线
        self.ax2 = self.figure.add_subplot(222)  # 损失曲线
        self.ax3 = self.figure.add_subplot(223)  # Q值曲线
        self.ax4 = self.figure.add_subplot(224)  # 探索率曲线
        
        # 设置图表标题和标签
        self.ax1.set_title('累计奖励')
        self.ax1.set_xlabel('回合')
        self.ax1.set_ylabel('奖励')
        
        self.ax2.set_title('训练损失')
        self.ax2.set_xlabel('更新步骤')
        self.ax2.set_ylabel('损失')
        
        self.ax3.set_title('Q值')
        self.ax3.set_xlabel('更新步骤')
        self.ax3.set_ylabel('Q值')
        
        self.ax4.set_title('探索率')
        self.ax4.set_xlabel('步骤')
        self.ax4.set_ylabel('探索率')
        
        self.canvas.draw()
    
    def _create_menu_bar(self):
        """创建菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu('文件')
        
        new_action = QAction('新建', self)
        new_action.setShortcut('Ctrl+N')
        file_menu.addAction(new_action)
        
        open_action = QAction('打开', self)
        open_action.setShortcut('Ctrl+O')
        file_menu.addAction(open_action)
        
        save_action = QAction('保存', self)
        save_action.setShortcut('Ctrl+S')
        file_menu.addAction(save_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction('退出', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 编辑菜单
        edit_menu = menubar.addMenu('编辑')
        
        undo_action = QAction('撤销', self)
        undo_action.setShortcut('Ctrl+Z')
        edit_menu.addAction(undo_action)
        
        redo_action = QAction('重做', self)
        redo_action.setShortcut('Ctrl+Y')
        edit_menu.addAction(redo_action)
        
        edit_menu.addSeparator()
        
        cut_action = QAction('剪切', self)
        cut_action.setShortcut('Ctrl+X')
        edit_menu.addAction(cut_action)
        
        copy_action = QAction('复制', self)
        copy_action.setShortcut('Ctrl+C')
        edit_menu.addAction(copy_action)
        
        paste_action = QAction('粘贴', self)
        paste_action.setShortcut('Ctrl+V')
        edit_menu.addAction(paste_action)
        
        # 视图菜单
        view_menu = menubar.addMenu('视图')
        
        toolbar_action = QAction('工具栏', self, checkable=True)
        toolbar_action.setChecked(True)
        view_menu.addAction(toolbar_action)
        
        statusbar_action = QAction('状态栏', self, checkable=True)
        statusbar_action.setChecked(True)
        view_menu.addAction(statusbar_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu('帮助')
        
        about_action = QAction('关于', self)
        help_menu.addAction(about_action)
    
    def update_ui(self):
        """更新界面显示"""
        state = self.env.state
        
        # 根据复杂度级别更新不同的控件状态
        if self.env.complexity_level >= 1:
            self.button1.setEnabled(state['button1_enabled'])
            self.button2.setEnabled(state['button2_enabled'])
            self.input_field.setText(state['input_field'])
            self.progress_bar.setValue(state['progress_value'])
            
            if self.env.complexity_level >= 2:
                self.button3.setEnabled(state['button3_enabled'])
                self.slider.setValue(state['slider_value'])
                self.checkbox.setChecked(state['checkbox_checked'])
                self.combobox.setCurrentIndex(state['combobox_index'])
                
                if self.env.complexity_level >= 3:
                    self.spinbox.setValue(state['spinbox_value'])
                    
                    # 更新单选按钮
                    if state['radiobutton_selected'] == 0:
                        self.radio1.setChecked(True)
                    elif state['radiobutton_selected'] == 1:
                        self.radio2.setChecked(True)
                    else:
                        self.radio3.setChecked(True)
                    
                    # 更新标签页
                    self.tab_widget_inner.setCurrentIndex(state['tab_index'])
                    
                    if self.env.complexity_level >= 4:
                        self.button4.setEnabled(state['button4_enabled'])
                        self.input_field2.setText(state['input_field2'])
                        self.slider.setValue(state['slider_value2'])  # 注意：这里使用了同一个滑块
                        self.checkbox2.setChecked(state['checkbox2_checked'])
                        self.combobox2.setCurrentIndex(state['combobox2_index'])
                        self.spinbox.setValue(state['spinbox2_value'])  # 注意：这里使用了同一个微调框
                        
                        if self.env.complexity_level >= 5:
                            self.button5.setEnabled(state['button5_enabled'])
                            self.input_field3.setText(state['input_field3'])
                            self.progress_bar2.setValue(state['progress_value2'])
                            self.slider.setValue(state['slider_value3'])  # 注意：这里使用了同一个滑块
                            self.checkbox3.setChecked(state['checkbox3_checked'])
                            self.combobox3.setCurrentIndex(state['combobox3_index'])
                            self.spinbox.setValue(state['spinbox3_value'])  # 注意：这里使用了同一个微调框
        
        # 更新状态标签
        self.status_label.setText(f"状态: {state['status']}")
        
        # 更新训练信息
        self.episode_label.setText(f"回合: {self.episodes}")
        self.reward_label.setText(f"总奖励: {self.total_reward:.2f}")
        self.step_label.setText(f"步数: {self.env.current_step}")
        
        if self.losses:
            self.loss_label.setText(f"损失: {self.losses[-1]:.4f}")
        
        if self.q_values:
            self.q_value_label.setText(f"Q值: {self.q_values[-1]:.4f}")
    
    def update_cv_display(self, image):
        """更新计算机视觉显示"""
        # 将OpenCV图像转换为Qt图像
        height, width, channel = image.shape
        bytes_per_line = 3 * width
        qt_image = QImage(image.data, width, height, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qt_image)
        
        # 缩放图像以适应标签
        scaled_pixmap = pixmap.scaled(self.cv_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.cv_label.setPixmap(scaled_pixmap)
    
    def handle_element_detected(self, element_type, rect):
        """处理检测到的界面元素"""
        # 在实际应用中，这里会更新界面元素的状态
        pass
    
    def reset_environment(self):
        """重置环境"""
        state = self.env.reset()
        self.episodes = 0
        self.total_reward = 0
        self.cumulative_rewards = []
        self.losses = []
        self.q_values = []
        self.update_ui()
        self.log_text.append(f"{datetime.now().strftime('%H:%M:%S')} - 环境已重置")
    
    def change_complexity(self, index):
        """改变环境复杂度"""
        self.env.set_complexity(index + 1)
        self.reset_environment()
        self.log_text.append(f"{datetime.now().strftime('%H:%M:%S')} - 复杂度设置为: {['简单', '中等', '复杂', '非常复杂', '极端复杂'][index]}")
    
    def toggle_training(self):
        """切换训练状态"""
        if self.training:
            self.training = False
            self.timer.stop()
            self.train_button.setText('开始训练')
            self.log_text.append(f"{datetime.now().strftime('%H:%M:%S')} - 训练停止")
        else:
            self.training = True
            self.evaluation_mode = False
            self.timer.start(50)  # 每50毫秒执行一步
            self.train_button.setText('停止训练')
            self.log_text.append(f"{datetime.now().strftime('%H:%M:%S')} - 开始训练...")
    
    def toggle_evaluation(self):
        """切换评估状态"""
        if self.training:
            self.training = False
            self.timer.stop()
            self.eval_button.setText('开始评估')
            self.log_text.append(f"{datetime.now().strftime('%H:%M:%S')} - 评估停止")
        else:
            self.training = True
            self.evaluation_mode = True
            self.timer.start(100)  # 每100毫秒执行一步
            self.eval_button.setText('停止评估')
            self.log_text.append(f"{datetime.now().strftime('%H:%M:%S')} - 开始评估...")
    
    def toggle_recording(self):
        """切换录制状态"""
        if self.recording:
            self.recording = False
            self.record_button.setText('开始录制')
            self.log_text.append(f"{datetime.now().strftime('%H:%M:%S')} - 录制停止")
        else:
            self.recording = True
            self.record_button.setText('停止录制')
            self.log_text.append(f"{datetime.now().strftime('%H:%M:%S')} - 开始录制...")
    
    def save_model(self):
        """保存模型"""
        path, _ = QFileDialog.getSaveFileName(self, "保存模型", "", "模型文件 (*.pth)")
        if path:
            self.agent.save(path)
            self.log_text.append(f"{datetime.now().strftime('%H:%M:%S')} - 模型已保存: {path}")
    
    def load_model(self):
        """加载模型"""
        path, _ = QFileDialog.getOpenFileName(self, "加载模型", "", "模型文件 (*.pth)")
        if path:
            self.agent.load(path)
            self.log_text.append(f"{datetime.now().strftime('%H:%M:%S')} - 模型已加载: {path}")
    
    def train_step(self):
        """执行一步训练"""
        current_state = self.env._get_state_vector()
        
        if self.evaluation_mode:
            action = self.agent.get_action(current_state, eval=True)
        else:
            action = self.agent.get_action(current_state)
        
        next_state, reward, done, info = self.env.step(action)
        self.total_reward += reward
        
        if not self.evaluation_mode:
            # 存储经验到回放缓冲区
            self.agent.push_memory(current_state, action, reward, next_state, done)
            
            # 学习
            loss, q_value = self.agent.learn()
            if loss is not None:
                self.losses.append(loss)
                self.q_values.append(q_value)
                
                # 记录到TensorBoard
                self.writer.add_scalar('Training/Loss', loss, self.agent.steps_done)
                self.writer.add_scalar('Training/QValue', q_value, self.agent.steps_done)
        
        # 更新界面
        self.update_ui()
        
        # 如果回合结束，重置环境
        if done:
            self.episodes += 1
            self.cumulative_rewards.append(self.total_reward)
            
            # 记录到TensorBoard
            self.writer.add_scalar('Training/Episode Reward', self.total_reward, self.episodes)
            self.writer.add_scalar('Training/Episode Length', self.env.current_step, self.episodes)
            
            if self.evaluation_mode:
                self.log_text.append(f"{datetime.now().strftime('%H:%M:%S')} - 评估回合 {self.episodes} 完成! 总奖励: {self.total_reward:.2f}")
            else:
                self.log_text.append(f"{datetime.now().strftime('%H:%M:%S')} - 训练回合 {self.episodes} 完成! 总奖励: {self.total_reward:.2f}")
            
            state = self.env.reset()
            self.total_reward = 0
            
            # 定期保存模型
            if self.episodes % 10 == 0 and not self.evaluation_mode:
                model_path = f"dqn_model_episode_{self.episodes}.pth"
                self.agent.save(model_path)
                self.log_text.append(f"{datetime.now().strftime('%H:%M:%S')} - 模型已自动保存: {model_path}")
            
            # 更新图表
            self._update_charts()
    
    def _update_charts(self):
        """更新训练图表"""
        if not self.losses or not self.q_values or not self.cumulative_rewards:
            return
        
        # 清空图表
        self.ax1.clear()
        self.ax2.clear()
        self.ax3.clear()
        self.ax4.clear()
        
        # 绘制奖励曲线
        self.ax1.plot(self.cumulative_rewards, 'b-')
        self.ax1.set_title('累计奖励')
        self.ax1.set_xlabel('回合')
        self.ax1.set_ylabel('奖励')
        
        # 绘制损失曲线
        self.ax2.plot(self.losses, 'r-')
        self.ax2.set_title('训练损失')
        self.ax2.set_xlabel('更新步骤')
        self.ax2.set_ylabel('损失')
        
        # 绘制Q值曲线
        self.ax3.plot(self.q_values, 'g-')
        self.ax3.set_title('Q值')
        self.ax3.set_xlabel('更新步骤')
        self.ax3.set_ylabel('Q值')
        
        # 探索率曲线（简化实现）
        steps = range(len(self.losses))
        exploration_rates = [0.1 + 0.9 * np.exp(-0.001 * step) for step in steps]
        self.ax4.plot(steps, exploration_rates, 'm-')
        self.ax4.set_title('探索率')
        self.ax4.set_xlabel('步骤')
        self.ax4.set_ylabel('探索率')
        
        # 刷新画布
        self.canvas.draw()
    
    def closeEvent(self, event):
        """处理窗口关闭事件"""
        # 停止CV线程
        self.cv_thread.stop()
        self.cv_thread.wait()
        
        # 关闭TensorBoard记录器
        self.writer.close()
        
        event.accept()

def main():
    app = QApplication(sys.argv)
    window = UltraAdvancedMainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()