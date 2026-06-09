import sys
import os
import json
import time
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.distributions import Normal, Categorical
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QLabel, QPushButton, QComboBox, QSlider, QSpinBox, 
                            QTextEdit, QTabWidget, QGroupBox, QFileDialog, QProgressBar,
                            QSplitter, QCheckBox)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap, QPalette, QColor
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PIL import Image

# ==============================================
# 强化学习核心模块
# ==============================================

class HyperSensoryFusion(nn.Module):
    """增强型多模态感知融合"""
    def __init__(self, vision_dim=(3, 256, 256), proprio_dim=12, lidar_dim=720, latent_dim=512):
        super().__init__()
        # 视觉编码器 (ResNet-18简化版)
        self.vision_encoder = nn.Sequential(
            nn.Conv2d(3, 64, kernel_size=7, stride=2, padding=3),
            nn.BatchNorm2d(64),
            nn.ReLU(),
            nn.MaxPool2d(kernel_size=3, stride=2, padding=1),
            self._make_layer(64, 64, 2),
            self._make_layer(64, 128, 2, stride=2),
            nn.AdaptiveAvgPool2d((1, 1)),
            nn.Flatten()
        )
        
        # 物理信号编码器
        self.phys_encoder = nn.Sequential(
            nn.Linear(proprio_dim + lidar_dim, 256),
            nn.ReLU(),
            nn.Linear(256, 128)
        )
        
        # 跨模态注意力融合
        self.cross_attn = nn.MultiheadAttention(embed_dim=128, num_heads=4)
        
        # 状态预测器
        self.state_predictor = nn.LSTM(input_size=128, hidden_size=latent_dim, batch_first=True)
        
    def _make_layer(self, in_channels, out_channels, blocks, stride=1):
        layers = []
        layers.append(nn.Conv2d(in_channels, out_channels, kernel_size=3, stride=stride, padding=1))
        layers.append(nn.BatchNorm2d(out_channels))
        layers.append(nn.ReLU())
        
        for _ in range(1, blocks):
            layers.append(nn.Conv2d(out_channels, out_channels, kernel_size=3, padding=1))
            layers.append(nn.BatchNorm2d(out_channels))
            layers.append(nn.ReLU())
            
        return nn.Sequential(*layers)
    
    def forward(self, vision, joints, lidar):
        # 视觉特征提取
        vision = vision.permute(0, 3, 1, 2) 
        vis_feat = self.vision_encoder(vision)
        
        # 物理特征提取
        phys_feat = self.phys_encoder(torch.cat([joints, lidar], dim=-1))
        
        # 跨模态注意力
        attn_out, _ = self.cross_attn(
            query=vis_feat.unsqueeze(0),
            key=phys_feat.unsqueeze(0),
            value=phys_feat.unsqueeze(0)
        )
        
        # 状态预测
        state, _ = self.state_predictor(attn_out.permute(1, 0, 2))
        return state.squeeze(1)

class NeuroSymbolicCortex(nn.Module):
    """神经符号认知核心"""
    def __init__(self, state_dim, action_dim, symbol_dim=64):
        super().__init__()
        # 动态模型
        self.transition_net = nn.LSTM(
            input_size=state_dim + action_dim,
            hidden_size=256,
            num_layers=2,
            batch_first=True
        )
        
        # 符号生成器
        self.symbolizer = nn.Sequential(
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Linear(128, symbol_dim),
            nn.Tanh()
        )
        
        # 规则库 (可训练)
        self.rule_weights = nn.Parameter(torch.randn(5, symbol_dim))
        
        # 策略网络
        self.policy_net = nn.Sequential(
            nn.Linear(symbol_dim, 128),
            nn.ReLU(),
            nn.Linear(128, action_dim * 2)  # 均值和标准差
        )
        
        # 价值网络
        self.value_net = nn.Sequential(
            nn.Linear(symbol_dim, 128),
            nn.ReLU(),
            nn.Linear(128, 1)
        )
    
    def apply_rules(self, symbols):
        """应用可微分逻辑规则"""
        # 规则激活: σ(W·s)
        activations = torch.sigmoid(torch.matmul(symbols, self.rule_weights.t()))
        
        # 安全规则: ¬碰撞 ∧ 稳定
        safety = activations[:, 0] * (1 - activations[:, 1])
        
        # 效率规则: 节能 ∧ 快速
        efficiency = activations[:, 2] * activations[:, 3]
        
        return torch.stack([safety, efficiency], dim=-1)
    
    def forward(self, state, action):
        # 状态转移预测
        x = torch.cat([state, action], dim=-1)
        trans_out, _ = self.transition_net(x)
        next_state_pred = trans_out[..., :state.shape[-1]]
        
        # 符号表示
        symbols = self.symbolizer(trans_out)
        
        # 规则应用
        rule_output = self.apply_rules(symbols)
        
        # 策略生成
        policy_params = self.policy_net(symbols)
        mean, log_std = torch.chunk(policy_params, 2, dim=-1)
        log_std = torch.clamp(log_std, min=-20, max=2)
        
        # 价值预测
        value = self.value_net(symbols)
        
        return next_state_pred, symbols, rule_output, mean, log_std, value

class QuantumExplorer:
    """量子启发的探索策略"""
    def __init__(self, action_dim, min_eps=0.01, max_eps=1.0, tunneling_rate=0.2):
        self.action_dim = action_dim
        self.min_eps = min_eps
        self.max_eps = max_eps
        self.tunneling_rate = tunneling_rate
        self.energy_barrier = 1.0
        self.learning_progress = 0.0
        
    def update_progress(self, avg_reward):
        """根据学习进度更新能垒"""
        self.learning_progress = min(1.0, avg_reward)
        self.energy_barrier = max(0.1, 1.0 - self.learning_progress * 0.9)
        
    def explore(self, action_mean, action_std, step):
        """量子隧穿探索"""
        # 基础探索率
        epsilon = self.min_eps + (self.max_eps - self.min_eps) * np.exp(-step / 10000)
        
        # 量子隧穿事件
        if np.random.rand() < self.tunneling_rate:
            tunneling_prob = np.exp(-self.energy_barrier)
            if np.random.rand() < tunneling_prob:
                return np.random.uniform(-1, 1, size=self.action_dim)
        
        # 高斯探索
        return action_mean + np.random.randn(self.action_dim) * action_std * epsilon

class CogNexusAgent:
    """完整的认知强化学习智能体"""
    def __init__(self, state_dim, action_dim):
        self.state_dim = state_dim
        self.action_dim = action_dim
        
        # 核心组件
        self.fusion = HyperSensoryFusion(latent_dim=state_dim)
        self.cortex = NeuroSymbolicCortex(state_dim, action_dim)
        self.explorer = QuantumExplorer(action_dim)
        
        # 优化器
        self.optimizer = torch.optim.Adam(
            list(self.fusion.parameters()) + list(self.cortex.parameters()),
            lr=1e-4
        )
        
        # 训练状态
        self.step_count = 0
        self.episode_rewards = []
        self.avg_reward = 0.0
        
    def act(self, observation):
        """根据观察生成动作"""
        # 预处理观察
        vision = torch.tensor(observation['vision'], dtype=torch.float32).unsqueeze(0)
        joints = torch.tensor(observation['joints'], dtype=torch.float32).unsqueeze(0)
        lidar = torch.tensor(observation['lidar'], dtype=torch.float32).unsqueeze(0)
        
        # 融合感知
        with torch.no_grad():
            state = self.fusion(vision, joints, lidar)
            
            # 生成策略
            _, _, _, mean, log_std, _ = self.cortex(
                state, 
                torch.zeros(1, self.action_dim)
            )
            
            # 采样动作
            std = log_std.exp()
            dist = Normal(mean, std)
            action = dist.sample().numpy().squeeze(0)
            
            # 探索
            exploration_action = self.explorer.explore(
                action, 
                std.mean().item(),
                self.step_count
            )
            
        self.step_count += 1
        return exploration_action
    
    def train_step(self, batch):
        """执行训练步骤"""
        states, actions, rewards, next_states, dones = batch
        
        # 通过认知核心预测
        next_pred, symbols, rules, mean, log_std, values = self.cortex(states, actions)
        
        # 计算损失
        # 1. 状态重建损失
        recon_loss = F.mse_loss(next_pred, next_states)
        
        # 2. 策略损失 (PPO风格)
        dist = Normal(mean, log_std.exp())
        log_probs = dist.log_prob(actions).sum(-1, keepdim=True)
        
        with torch.no_grad():
            _, _, _, _, _, next_values = self.cortex(next_states, torch.zeros_like(actions))
            targets = rewards + 0.99 * next_values * (1 - dones.float())
            advantages = targets - values
            
        policy_loss = -(log_probs * advantages.detach()).mean()
        
        # 3. 价值损失
        value_loss = F.mse_loss(values, targets.detach())
        
        # 4. 规则一致性损失
        with torch.no_grad():
            _, true_symbols, true_rules, _, _, _ = self.cortex(
                next_states, torch.zeros_like(actions))
            
        symbol_loss = F.mse_loss(symbols, true_symbols)
        rule_loss = F.mse_loss(rules, true_rules)
        
        # 总损失
        total_loss = (
            recon_loss + 
            policy_loss + 
            0.5 * value_loss + 
            0.2 * symbol_loss + 
            0.1 * rule_loss
        )
        
        # 优化
        self.optimizer.zero_grad()
        total_loss.backward()
        self.optimizer.step()
        
        # 更新探索器
        if len(self.episode_rewards) > 10:
            self.avg_reward = np.mean(self.episode_rewards[-10:])
            self.explorer.update_progress(self.avg_reward)
        
        return {
            "total_loss": total_loss.item(),
            "recon_loss": recon_loss.item(),
            "policy_loss": policy_loss.item(),
            "value_loss": value_loss.item(),
            "symbol_loss": symbol_loss.item(),
            "rule_loss": rule_loss.item()
        }
    
    def save_checkpoint(self, path):
        """保存模型检查点"""
        torch.save({
            'fusion': self.fusion.state_dict(),
            'cortex': self.cortex.state_dict(),
            'optimizer': self.optimizer.state_dict(),
            'step_count': self.step_count,
            'rewards': self.episode_rewards
        }, path)
        
    def load_checkpoint(self, path):
        """加载模型检查点"""
        checkpoint = torch.load(path)
        self.fusion.load_state_dict(checkpoint['fusion'])
        self.cortex.load_state_dict(checkpoint['cortex'])
        self.optimizer.load_state_dict(checkpoint['optimizer'])
        self.step_count = checkpoint['step_count']
        self.episode_rewards = checkpoint['rewards']

# ==============================================
# PyQt 用户界面
# ==============================================

class TrainingThread(QThread):
    """训练线程"""
    update_signal = pyqtSignal(dict)  # 训练状态更新信号
    render_signal = pyqtSignal(np.ndarray)  # 环境渲染信号
    
    def __init__(self, agent, env):
        super().__init__()
        self.agent = agent
        self.env = env
        self.running = True
        self.paused = False
        self.episode_count = 0
        self.batch_size = 64
        self.replay_buffer = []
        self.max_buffer_size = 10000
        
    def run(self):
        """主训练循环"""
        while self.running:
            if not self.paused:
                # 重置环境
                obs = self.env.reset()
                episode_reward = 0
                state = None
                done = False
                
                # 执行一个episode
                while not done and self.running:
                    if self.paused:
                        break
                    
                    # 获取动作
                    action = self.agent.act(obs)
                    
                    # 执行动作
                    next_obs, reward, done, _ = self.env.step(action)
                    
                    # 渲染环境
                    if self.episode_count % 10 == 0:
                        self.render_signal.emit(self.env.render())
                    
                    # 存储经验
                    if state is not None:
                        self.replay_buffer.append((
                            state, 
                            torch.tensor(action, dtype=torch.float32), 
                            torch.tensor([reward], dtype=torch.float32),
                            self.agent.fusion(
                                torch.tensor(next_obs['vision'], dtype=torch.float32).unsqueeze(0),
                                torch.tensor(next_obs['joints'], dtype=torch.float32).unsqueeze(0),
                                torch.tensor(next_obs['lidar'], dtype=torch.float32).unsqueeze(0)
                            ).detach(),
                            torch.tensor([done], dtype=torch.float32)
                        ))
                        
                        # 保持缓冲区大小
                        if len(self.replay_buffer) > self.max_buffer_size:
                            self.replay_buffer.pop(0)
                    
                    state = self.agent.fusion(
                        torch.tensor(obs['vision'], dtype=torch.float32).unsqueeze(0),
                        torch.tensor(obs['joints'], dtype=torch.float32).unsqueeze(0),
                        torch.tensor(obs['lidar'], dtype=torch.float32).unsqueeze(0)
                    ).detach()
                    
                    obs = next_obs
                    episode_reward += reward
                
                # 记录奖励
                self.agent.episode_rewards.append(episode_reward)
                
                # 训练模型
                if len(self.replay_buffer) >= self.batch_size:
                    # 采样批次
                    indices = np.random.choice(len(self.replay_buffer), self.batch_size)
                    batch = [self.replay_buffer[i] for i in indices]
                    
                    # 解包批次
                    states = torch.cat([item[0] for item in batch])
                    actions = torch.stack([item[1] for item in batch])
                    rewards = torch.cat([item[2] for item in batch])
                    next_states = torch.cat([item[3] for item in batch])
                    dones = torch.cat([item[4] for item in batch])
                    
                    # 训练步骤
                    metrics = self.agent.train_step((states, actions, rewards, next_states, dones))
                    
                    # 发送更新信号
                    self.update_signal.emit({
                        "episode": self.episode_count,
                        "reward": episode_reward,
                        "avg_reward": np.mean(self.agent.episode_rewards[-10:]),
                        "steps": self.agent.step_count,
                        **metrics
                    })
                
                self.episode_count += 1
            else:
                time.sleep(0.1)  # 暂停时降低CPU使用率
    
    def stop(self):
        """停止训练"""
        self.running = False
        
    def toggle_pause(self):
        """切换暂停状态"""
        self.paused = not self.paused

class RewardPlot(FigureCanvas):
    """奖励曲线图"""
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        super().__init__(self.fig)
        self.setParent(parent)
        self.ax = self.fig.add_subplot(111)
        self.ax.set_title('Training Progress')
        self.ax.set_xlabel('Episode')
        self.ax.set_ylabel('Reward')
        self.ax.grid(True)
        self.reward_line, = self.ax.plot([], [], 'b-', label='Episode Reward')
        self.avg_line, = self.ax.plot([], [], 'r-', label='Avg Reward (10)')
        self.ax.legend(loc='upper left')
        self.x_data = []
        self.y_data = []
        self.avg_data = []
        
    def update_plot(self, episode, reward, avg_reward):
        """更新图表"""
        self.x_data.append(episode)
        self.y_data.append(reward)
        self.avg_data.append(avg_reward)
        
        self.reward_line.set_data(self.x_data, self.y_data)
        self.avg_line.set_data(self.x_data, self.avg_data)
        
        # 调整坐标轴范围
        self.ax.set_xlim(0, max(10, episode+1))
        self.ax.set_ylim(min(self.y_data)-10, max(self.y_data)+10)
        
        self.draw()

class CogNexusGUI(QMainWindow):
    """主应用程序窗口"""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CogNexus Pro - Advanced RL System")
        self.setGeometry(100, 100, 1400, 800)
        
        # 初始化智能体和环境
        self.agent = CogNexusAgent(state_dim=256, action_dim=7)
        self.env = SimulationEnvironment()
        
        # 创建训练线程
        self.train_thread = TrainingThread(self.agent, self.env)
        
        # 设置UI
        self.init_ui()
        
        # 连接信号
        self.train_thread.update_signal.connect(self.update_training_info)
        self.train_thread.render_signal.connect(self.update_rendering)
    
    def init_ui(self):
        """初始化用户界面"""
        # 主布局
        main_widget = QWidget()
        main_layout = QHBoxLayout()
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)
        
        # 左侧面板 (控制和信息)
        left_panel = QWidget()
        left_layout = QVBoxLayout()
        left_panel.setLayout(left_layout)
        left_panel.setMaximumWidth(400)
        
        # 右侧面板 (可视化和图表)
        right_panel = QWidget()
        right_layout = QVBoxLayout()
        right_panel.setLayout(right_layout)
        
        # 添加分割器
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([300, 1100])
        main_layout.addWidget(splitter)
        
        # ===== 左侧面板 =====
        
        # 控制组
        control_group = QGroupBox("Training Control")
        control_layout = QVBoxLayout()
        control_group.setLayout(control_layout)
        
        # 控制按钮
        self.start_btn = QPushButton("Start Training")
        self.pause_btn = QPushButton("Pause")
        self.stop_btn = QPushButton("Stop")
        self.save_btn = QPushButton("Save Model")
        self.load_btn = QPushButton("Load Model")
        
        self.start_btn.clicked.connect(self.start_training)
        self.pause_btn.clicked.connect(self.toggle_pause)
        self.stop_btn.clicked.connect(self.stop_training)
        self.save_btn.clicked.connect(self.save_model)
        self.load_btn.clicked.connect(self.load_model)
        
        # 探索控制
        exploration_group = QGroupBox("Exploration Settings")
        exploration_layout = QVBoxLayout()
        exploration_group.setLayout(exploration_layout)
        
        self.tunneling_cb = QCheckBox("Enable Quantum Tunneling")
        self.tunneling_cb.setChecked(True)
        
        min_eps_label = QLabel("Min Exploration Rate:")
        self.min_eps_slider = QSlider(Qt.Horizontal)
        self.min_eps_slider.setRange(0, 100)
        self.min_eps_slider.setValue(1)
        
        max_eps_label = QLabel("Max Exploration Rate:")
        self.max_eps_slider = QSlider(Qt.Horizontal)
        self.max_eps_slider.setRange(0, 100)
        self.max_eps_slider.setValue(100)
        
        exploration_layout.addWidget(self.tunneling_cb)
        exploration_layout.addWidget(min_eps_label)
        exploration_layout.addWidget(self.min_eps_slider)
        exploration_layout.addWidget(max_eps_label)
        exploration_layout.addWidget(self.max_eps_slider)
        
        # 按钮布局
        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.pause_btn)
        btn_layout.addWidget(self.stop_btn)
        
        btn_layout2 = QHBoxLayout()
        btn_layout2.addWidget(self.save_btn)
        btn_layout2.addWidget(self.load_btn)
        
        control_layout.addLayout(btn_layout)
        control_layout.addLayout(btn_layout2)
        control_layout.addWidget(exploration_group)
        
        # 训练信息
        info_group = QGroupBox("Training Information")
        info_layout = QVBoxLayout()
        info_group.setLayout(info_layout)
        
        self.episode_label = QLabel("Episode: 0")
        self.step_label = QLabel("Total Steps: 0")
        self.reward_label = QLabel("Episode Reward: 0.00")
        self.avg_reward_label = QLabel("Avg Reward (10): 0.00")
        
        # 损失信息
        self.loss_label = QLabel("Loss: N/A")
        self.recon_loss_label = QLabel("Recon Loss: N/A")
        self.policy_loss_label = QLabel("Policy Loss: N/A")
        self.value_loss_label = QLabel("Value Loss: N/A")
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        
        info_layout.addWidget(self.episode_label)
        info_layout.addWidget(self.step_label)
        info_layout.addWidget(self.reward_label)
        info_layout.addWidget(self.avg_reward_label)
        info_layout.addWidget(QLabel(""))
        info_layout.addWidget(self.loss_label)
        info_layout.addWidget(self.recon_loss_label)
        info_layout.addWidget(self.policy_loss_label)
        info_layout.addWidget(self.value_loss_label)
        info_layout.addWidget(QLabel(""))
        info_layout.addWidget(QLabel("Training Progress:"))
        info_layout.addWidget(self.progress_bar)
        
        # 添加到左侧面板
        left_layout.addWidget(control_group)
        left_layout.addWidget(info_group)
        
        # ===== 右侧面板 =====
        
        # 创建标签页
        self.tab_widget = QTabWidget()
        right_layout.addWidget(self.tab_widget)
        
        # 环境渲染标签页
        render_tab = QWidget()
        render_layout = QVBoxLayout()
        render_tab.setLayout(render_layout)
        
        self.render_label = QLabel()
        self.render_label.setAlignment(Qt.AlignCenter)
        self.render_label.setMinimumSize(640, 480)
        render_layout.addWidget(self.render_label)
        
        # 奖励图表标签页
        plot_tab = QWidget()
        plot_layout = QVBoxLayout()
        plot_tab.setLayout(plot_layout)
        
        self.reward_plot = RewardPlot()
        plot_layout.addWidget(self.reward_plot)
        
        # 符号可视化标签页
        symbol_tab = QWidget()
        symbol_layout = QVBoxLayout()
        symbol_tab.setLayout(symbol_layout)
        
        self.symbol_text = QTextEdit()
        self.symbol_text.setReadOnly(True)
        symbol_layout.addWidget(self.symbol_text)
        
        # 添加标签页
        self.tab_widget.addTab(render_tab, "Environment Rendering")
        self.tab_widget.addTab(plot_tab, "Training Metrics")
        self.tab_widget.addTab(symbol_tab, "Symbolic Reasoning")
    
    def start_training(self):
        """开始训练"""
        # 更新探索器设置
        min_eps = self.min_eps_slider.value() / 100.0
        max_eps = self.max_eps_slider.value() / 100.0
        tunneling = self.tunneling_cb.isChecked()
        
        self.agent.explorer.min_eps = min_eps
        self.agent.explorer.max_eps = max_eps
        self.agent.explorer.tunneling_rate = 0.2 if tunneling else 0.0
        
        # 启动训练线程
        if not self.train_thread.isRunning():
            self.train_thread.running = True
            self.train_thread.paused = False
            self.train_thread.start()
        
        self.start_btn.setEnabled(False)
        self.pause_btn.setEnabled(True)
        self.stop_btn.setEnabled(True)
    
    def toggle_pause(self):
        """切换暂停状态"""
        self.train_thread.toggle_pause()
        if self.train_thread.paused:
            self.pause_btn.setText("Resume")
        else:
            self.pause_btn.setText("Pause")
    
    def stop_training(self):
        """停止训练"""
        self.train_thread.stop()
        self.train_thread.wait()
        
        self.start_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)
        self.pause_btn.setText("Pause")
    
    def save_model(self):
        """保存模型"""
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Model", "", "Checkpoint Files (*.pt)"
        )
        if path:
            self.agent.save_checkpoint(path)
    
    def load_model(self):
        """加载模型"""
        path, _ = QFileDialog.getOpenFileName(
            self, "Load Model", "", "Checkpoint Files (*.pt)"
        )
        if path:
            self.agent.load_checkpoint(path)
    
    def update_training_info(self, data):
        """更新训练信息"""
        self.episode_label.setText(f"Episode: {data['episode']}")
        self.step_label.setText(f"Total Steps: {data['steps']}")
        self.reward_label.setText(f"Episode Reward: {data['reward']:.2f}")
        self.avg_reward_label.setText(f"Avg Reward (10): {data['avg_reward']:.2f}")
        
        self.loss_label.setText(f"Total Loss: {data['total_loss']:.4f}")
        self.recon_loss_label.setText(f"Recon Loss: {data['recon_loss']:.4f}")
        self.policy_loss_label.setText(f"Policy Loss: {data['policy_loss']:.4f}")
        self.value_loss_label.setText(f"Value Loss: {data['value_loss']:.4f}")
        
        # 更新进度条
        progress = min(100, int(data['episode'] / 1000 * 100))
        self.progress_bar.setValue(progress)
        
        # 更新图表
        self.reward_plot.update_plot(data['episode'], data['reward'], data['avg_reward'])
        
        # 更新符号信息
        symbol_info = f"""Symbolic Reasoning Report:
        - Episode: {data['episode']}
        - Total Steps: {data['steps']}
        - Symbol Loss: {data['symbol_loss']:.4f}
        - Rule Loss: {data['rule_loss']:.4f}
        - Quantum Tunneling: {'Enabled' if self.agent.explorer.tunneling_rate > 0 else 'Disabled'}
        - Energy Barrier: {self.agent.explorer.energy_barrier:.2f}
        - Learning Progress: {self.agent.explorer.learning_progress:.2%}
        """
        self.symbol_text.setText(symbol_info)
    
    def update_rendering(self, frame):
        """更新环境渲染"""
        # 将numpy数组转换为QImage
        height, width, channel = frame.shape
        bytes_per_line = 3 * width
        q_img = QImage(frame.data, width, height, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(q_img)
        
        # 缩放并显示
        scaled_pixmap = pixmap.scaled(
            self.render_label.width(), 
            self.render_label.height(),
            Qt.KeepAspectRatio
        )
        self.render_label.setPixmap(scaled_pixmap)
    
    def closeEvent(self, event):
        """关闭事件处理"""
        self.stop_training()
        event.accept()

# ==============================================
# 仿真环境
# ==============================================

class SimulationEnvironment:
    """机器人仿真环境"""
    def __init__(self, complexity=0.5):
        self.complexity = complexity
        self.task_types = [
            "Pick and Place", 
            "Obstacle Navigation", 
            "Assembly Task",
            "Mobile Manipulation"
        ]
        self.current_task = np.random.choice(self.task_types)
        self.step_count = 0
        self.max_steps = 200
        self.reset()
    
    def reset(self):
        """重置环境"""
        self.step_count = 0
        self.current_task = np.random.choice(self.task_types)
        
        # 生成随机观察
        return {
            'vision': np.random.rand(256, 256, 3).astype(np.float32),  # float32
            'joints': np.random.rand(12).astype(np.float32),  # float32
            'lidar': np.random.rand(720).astype(np.float32)   # float32
        }
    
    def step(self, action):
        """执行动作"""
        self.step_count += 1
        
        # 计算奖励
        task_reward = 0.0
        
        if self.current_task == "Pick and Place":
            # 成功概率与动作精确度相关
            precision = 1.0 - np.abs(action[:3]).mean()
            task_reward = 10.0 * precision * self.complexity
        
        elif self.current_task == "Obstacle Navigation":
            # 奖励前进速度，惩罚碰撞
            forward_speed = max(0, action[3])
            collision_penalty = -5.0 if np.random.rand() < 0.1 else 0.0
            task_reward = forward_speed * 5.0 + collision_penalty
        
        elif self.current_task == "Assembly Task":
            # 奖励精确对齐
            alignment = 1.0 - np.abs(action[4:6]).mean()
            task_reward = 15.0 * alignment * self.complexity
        
        else:  # Mobile Manipulation
            # 综合奖励
            movement = np.linalg.norm(action[3:5])
            manipulation = 1.0 - np.abs(action[:3]).mean()
            task_reward = (movement + manipulation * 2.0) * 3.0
        
        # 能量惩罚
        energy_penalty = -0.1 * np.linalg.norm(action)
        
        # 总奖励
        reward = task_reward + energy_penalty
        
        # 检查是否结束
        done = self.step_count >= self.max_steps or task_reward > 8.0
        
        # 生成新观察
        next_obs = self.reset() if done else self.reset()
        
        return next_obs, reward, done, {}
    
    def render(self):
        """渲染环境状态"""
        # 创建简单图像表示
        img_size = 480
        img = np.zeros((img_size, img_size, 3), dtype=np.uint8)
        
        # 绘制任务类型
        cv2.putText(img, f"Task: {self.current_task}", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # 绘制进度条
        progress = self.step_count / self.max_steps
        cv2.rectangle(img, (50, 50), (int(50 + 400 * progress), 70), (0, 200, 0), -1)
        cv2.rectangle(img, (50, 50), (450, 70), (255, 255, 255), 2)
        
        # 绘制机器人示意
        center_x, center_y = img_size // 2, img_size // 2
        cv2.circle(img, (center_x, center_y), 50, (0, 120, 255), -1)
        
        # 绘制激光雷达扫描线
        for i in range(0, 360, 10):
            angle = np.radians(i)
            length = 150 * (0.5 + 0.5 * np.random.rand())
            end_x = int(center_x + length * np.cos(angle))
            end_y = int(center_y + length * np.sin(angle))
            cv2.line(img, (center_x, center_y), (end_x, end_y), (0, 255, 0), 1)
        
        return img

# ==============================================
# 启动应用程序
# ==============================================

if __name__ == "__main__":
    # 修复OpenCV在PyQt中的问题
    import cv2
    cv2.namedWindow("dummy", cv2.WINDOW_NORMAL)
    cv2.destroyWindow("dummy")
    
    app = QApplication(sys.argv)
    
    # 设置应用样式
    app.setStyle("Fusion")
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(53, 53, 53))
    palette.setColor(QPalette.WindowText, Qt.white)
    palette.setColor(QPalette.Base, QColor(35, 35, 35))
    palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
    palette.setColor(QPalette.ToolTipBase, Qt.white)
    palette.setColor(QPalette.ToolTipText, Qt.white)
    palette.setColor(QPalette.Text, Qt.white)
    palette.setColor(QPalette.Button, QColor(53, 53, 53))
    palette.setColor(QPalette.ButtonText, Qt.white)
    palette.setColor(QPalette.BrightText, Qt.red)
    palette.setColor(QPalette.Highlight, QColor(142, 45, 197).lighter())
    palette.setColor(QPalette.HighlightedText, Qt.black)
    app.setPalette(palette)
    
    window = CogNexusGUI()
    window.show()
    sys.exit(app.exec_())