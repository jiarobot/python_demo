import sys
import numpy as np
import matplotlib
matplotlib.rc("font", family='Microsoft YaHei')
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QPushButton, QLabel, QSlider, QComboBox, QGroupBox, 
                            QTextEdit, QTabWidget, QFileDialog, QProgressBar, QSplitter,
                            QDoubleSpinBox, QSpinBox, QCheckBox, QGridLayout, QSizePolicy)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QPixmap, QImage, QFont
import imageio
import os
import time
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from qinggong import EnhancedLightfootEnv, SACAgent, train_sac, evaluate_agent, visualize_skills

# 重新定义visualize_skills函数，使其返回图像而不是显示
def visualize_skills_to_image(agent):
    """生成策略可视化并返回图像数组"""
    # 创建状态网格
    positions = np.linspace(0, 1, 20)
    energies = np.linspace(0, 1, 20)
    X, Y = np.meshgrid(positions, energies)
    
    # 固定其他状态 (更新为27个元素)
    base_state = np.zeros(27)
    base_state[3] = 0.5  # 高度
    base_state[6] = 1.0  # 技能1
    base_state[7] = 1.0  # 技能2
    base_state[8] = 1.0  # 技能3
    
    # 计算策略
    actions = np.zeros((20, 20, 3))
    for i in range(20):
        for j in range(20):
            state = base_state.copy()
            state[0] = X[i, j]  # 位置
            state[1] = Y[i, j]  # 内力
            action = agent.policy(state, deterministic=True)
            actions[i, j] = action
    
    # 创建图形
    fig = plt.figure(figsize=(15, 10), dpi=100)
    
    # 可视化内力输出
    ax1 = fig.add_subplot(131)
    cf1 = ax1.contourf(X, Y, actions[:, :, 0], 20, cmap='viridis')
    fig.colorbar(cf1, ax=ax1, label='内力输出')
    ax1.set_xlabel('位置')
    ax1.set_ylabel('内力')
    ax1.set_title('内力输出策略')
    
    # 可视化角度
    ax2 = fig.add_subplot(132)
    cf2 = ax2.contourf(X, Y, actions[:, :, 1] * 180, 20, cmap='plasma')
    fig.colorbar(cf2, ax=ax2, label='角度 (度)')
    ax2.set_xlabel('位置')
    ax2.set_ylabel('内力')
    ax2.set_title('角度策略')
    
    # 可视化内力控制
    ax3 = fig.add_subplot(133)
    cf3 = ax3.contourf(X, Y, actions[:, :, 2] * 2 - 1, 20, cmap='coolwarm')
    fig.colorbar(cf3, ax=ax3, label='内力控制')
    ax3.set_xlabel('位置')
    ax3.set_ylabel('内力')
    ax3.set_title('内力循环策略')
    
    fig.tight_layout()
    
    # 将图形转换为图像数组
    fig.canvas.draw()
    img = np.frombuffer(fig.canvas.tostring_rgb(), dtype=np.uint8)
    img = img.reshape(fig.canvas.get_width_height()[::-1] + (3,))
    
    plt.close(fig)
    return img

class TrainingThread(QThread):
    update_progress = pyqtSignal(int, list, list, list)
    training_finished = pyqtSignal()
    episode_completed = pyqtSignal(int, list, list)
    render_frame = pyqtSignal(np.ndarray)  # 新增信号用于传递渲染帧
    
    def __init__(self, env, num_episodes, render_every, parent=None):
        super().__init__(parent)
        self.env = env
        self.num_episodes = num_episodes
        self.render_every = render_every
        self.is_paused = False
        self.is_stopped = False
        self.agents = None
        self.episode_rewards = None
        self.current_frames = []
        
    def run(self):
        agents = [SACAgent(self.env.observation_space.shape[0], 
                          self.env.action_space.shape[0], i) 
                 for i in range(self.env.num_agents)]
        
        # 尝试加载已有模型
        for agent in agents:
            agent.load_models()
        
        self.agents = agents
        episode_rewards = [[] for _ in range(self.env.num_agents)]
        self.episode_rewards = episode_rewards
        
        for ep in range(self.num_episodes):
            while self.is_paused and not self.is_stopped:
                time.sleep(0.1)
                
            if self.is_stopped:
                break
                
            states = self.env.reset()
            episode_reward = [0] * self.env.num_agents
            done = [False] * self.env.num_agents
            self.current_frames = []
            
            # 每render_every集渲染一次
            render = (ep % self.render_every == 0)
            
            while not all(done):
                # 获取动作
                actions = []
                for i, agent in enumerate(agents):
                    if done[i]:
                        actions.append(np.zeros(self.env.action_space.shape[0]))
                    else:
                        action = agent.policy(states[i])
                        actions.append(action)
                
                # 执行动作
                next_states, rewards, done, _ = self.env.step(actions)
                
                # 存储经验
                for i, agent in enumerate(agents):
                    if not done[i]:
                        agent.store_experience(states[i], actions[i], rewards[i], next_states[i], done[i])
                
                # 更新状态
                states = next_states
                
                # 收集奖励
                for i in range(self.env.num_agents):
                    episode_reward[i] += rewards[i]
                
                # 渲染并发送帧
                if render:
                    frame = self.env.render(mode='rgb_array')
                    self.render_frame.emit(frame)
                    self.current_frames.append(frame)
            
            # 更新网络
            losses = []
            for agent in agents:
                critic_loss1, actor_loss, alpha_loss = agent.update()
                losses.append((critic_loss1, actor_loss, alpha_loss))
            
            # 保存奖励
            for i in range(self.env.num_agents):
                episode_rewards[i].append(episode_reward[i])
            
            # 发送信号更新UI
            self.episode_completed.emit(ep, episode_reward, losses)
            
            # 每10集保存一次模型
            if ep % 10 == 0:
                for agent in agents:
                    agent.save_models()
            
            # 保存渲染视频
            if render and self.current_frames:
                os.makedirs("videos", exist_ok=True)
                video_path = f"videos/episode_{ep}.mp4"
                imageio.mimsave(video_path, self.current_frames, fps=30)
        
        # 训练完成
        self.training_finished.emit()
    
    def pause(self):
        self.is_paused = True
    
    def resume(self):
        self.is_paused = False
    
    def stop(self):
        self.is_stopped = True

class LightfootApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("轻功水上漂训练系统 - 增强版")
        self.setGeometry(100, 100, 1600, 900)
        
        # 创建环境
        self.env = EnhancedLightfootEnv(water_length=100, num_agents=1, difficulty=1.0)
        
        # 初始化训练线程
        self.training_thread = None
        
        # 创建主界面
        self.init_ui()
        
        # 设置定时器用于实时渲染
        self.render_timer = QTimer(self)
        self.render_timer.timeout.connect(self.update_render)
        self.render_timer.start(50)  # 20 FPS
        
        # 当前渲染帧
        self.current_frame = None
    
    def init_ui(self):
        # 主布局
        main_widget = QWidget()
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # 左侧控制面板
        control_panel = QGroupBox("控制面板")
        control_panel.setMinimumWidth(400)
        control_layout = QVBoxLayout(control_panel)
        control_layout.setAlignment(Qt.AlignTop)
        
        # 右侧主显示区域
        display_panel = QWidget()
        display_layout = QVBoxLayout(display_panel)
        display_layout.setContentsMargins(5, 5, 5, 5)
        
        # 添加标签页
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabPosition(QTabWidget.North)
        display_layout.addWidget(self.tab_widget)
        
        # 实时渲染标签页
        self.render_tab = QWidget()
        self.render_layout = QVBoxLayout(self.render_tab)
        self.render_layout.setContentsMargins(5, 5, 5, 5)
        
        # 渲染显示区域
        self.render_label = QLabel()
        self.render_label.setAlignment(Qt.AlignCenter)
        self.render_label.setMinimumSize(800, 450)
        self.render_label.setStyleSheet("background-color: #2C3E50; border: 1px solid #34495E;")
        self.render_layout.addWidget(self.render_label)
        
        # 添加状态信息显示
        status_group = QGroupBox("实时状态")
        status_layout = QGridLayout(status_group)
        
        self.position_label = QLabel("位置: 0.0")
        self.energy_label = QLabel("内力: 100.0")
        self.velocity_label = QLabel("速度: 0.0")
        self.height_label = QLabel("高度: 1.0")
        self.wind_label = QLabel("风速: 0.0")
        self.water_current_label = QLabel("水流: 0.0")
        
        status_layout.addWidget(QLabel("智能体状态:"), 0, 0)
        status_layout.addWidget(self.position_label, 0, 1)
        status_layout.addWidget(self.energy_label, 1, 1)
        status_layout.addWidget(self.velocity_label, 2, 1)
        status_layout.addWidget(self.height_label, 3, 1)
        
        status_layout.addWidget(QLabel("环境状态:"), 4, 0)
        status_layout.addWidget(self.wind_label, 4, 1)
        status_layout.addWidget(self.water_current_label, 5, 1)
        
        self.render_layout.addWidget(status_group)
        
        # 奖励图表标签页
        self.reward_tab = QWidget()
        self.reward_layout = QVBoxLayout(self.reward_tab)
        
        # 奖励图表
        self.reward_fig = Figure(figsize=(8, 5), dpi=100)
        self.reward_canvas = FigureCanvas(self.reward_fig)
        self.reward_canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.reward_ax = self.reward_fig.add_subplot(111)
        self.reward_ax.set_title('奖励曲线')
        self.reward_ax.set_xlabel('训练轮次')
        self.reward_ax.set_ylabel('奖励')
        self.reward_line, = self.reward_ax.plot([], [], 'b-', linewidth=2)
        self.reward_ax.grid(True, linestyle='--', alpha=0.7)
        self.reward_ax.set_facecolor('#F8F9F9')
        self.reward_fig.tight_layout()
        
        self.reward_layout.addWidget(self.reward_canvas)
        
        # 策略可视化标签页
        self.strategy_tab = QWidget()
        self.strategy_layout = QVBoxLayout(self.strategy_tab)
        
        self.strategy_fig = Figure(figsize=(8, 5), dpi=100)
        self.strategy_canvas = FigureCanvas(self.strategy_fig)
        self.strategy_canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.strategy_ax = self.strategy_fig.add_subplot(111)
        self.strategy_ax.set_title('策略可视化')
        self.strategy_ax.axis('off')
        self.strategy_fig.tight_layout()
        
        self.strategy_layout.addWidget(self.strategy_canvas)
        
        # 添加标签页
        self.tab_widget.addTab(self.render_tab, "实时渲染")
        self.tab_widget.addTab(self.reward_tab, "奖励曲线")
        self.tab_widget.addTab(self.strategy_tab, "策略可视化")
        
        # 环境参数设置
        param_group = QGroupBox("环境参数")
        param_layout = QGridLayout(param_group)
        
        row = 0
        param_layout.addWidget(QLabel("水面长度:"), row, 0)
        self.water_length_spin = QSpinBox()
        self.water_length_spin.setRange(50, 500)
        self.water_length_spin.setValue(100)
        param_layout.addWidget(self.water_length_spin, row, 1)
        
        row += 1
        param_layout.addWidget(QLabel("智能体数量:"), row, 0)
        self.num_agents_spin = QSpinBox()
        self.num_agents_spin.setRange(1, 5)
        self.num_agents_spin.setValue(1)
        param_layout.addWidget(self.num_agents_spin, row, 1)
        
        row += 1
        param_layout.addWidget(QLabel("初始难度:"), row, 0)
        self.difficulty_spin = QDoubleSpinBox()
        self.difficulty_spin.setRange(0.5, 3.0)
        self.difficulty_spin.setSingleStep(0.1)
        self.difficulty_spin.setValue(1.0)
        param_layout.addWidget(self.difficulty_spin, row, 1)
        
        row += 1
        param_layout.addWidget(QLabel("最大步数:"), row, 0)
        self.max_steps_spin = QSpinBox()
        self.max_steps_spin.setRange(100, 2000)
        self.max_steps_spin.setValue(500)
        param_layout.addWidget(self.max_steps_spin, row, 1)
        
        row += 1
        param_layout.addWidget(QLabel("重力系数:"), row, 0)
        self.gravity_spin = QDoubleSpinBox()
        self.gravity_spin.setRange(0.1, 2.0)
        self.gravity_spin.setSingleStep(0.1)
        self.gravity_spin.setValue(0.5)
        param_layout.addWidget(self.gravity_spin, row, 1)
        
        control_layout.addWidget(param_group)
        
        # 训练参数设置
        train_group = QGroupBox("训练参数")
        train_layout = QGridLayout(train_group)
        
        row = 0
        train_layout.addWidget(QLabel("训练轮次:"), row, 0)
        self.num_episodes_spin = QSpinBox()
        self.num_episodes_spin.setRange(10, 10000)
        self.num_episodes_spin.setValue(1000)
        train_layout.addWidget(self.num_episodes_spin, row, 1)
        
        row += 1
        train_layout.addWidget(QLabel("渲染间隔:"), row, 0)
        self.render_every_spin = QSpinBox()
        self.render_every_spin.setRange(1, 100)
        self.render_every_spin.setValue(10)
        train_layout.addWidget(self.render_every_spin, row, 1)
        
        row += 1
        train_layout.addWidget(QLabel("批量大小:"), row, 0)
        self.batch_size_spin = QSpinBox()
        self.batch_size_spin.setRange(32, 2048)
        self.batch_size_spin.setValue(256)
        train_layout.addWidget(self.batch_size_spin, row, 1)
        
        row += 1
        train_layout.addWidget(QLabel("学习率:"), row, 0)
        self.lr_spin = QDoubleSpinBox()
        self.lr_spin.setRange(0.00001, 0.01)
        self.lr_spin.setSingleStep(0.00001)
        self.lr_spin.setValue(0.0003)
        self.lr_spin.setDecimals(5)
        train_layout.addWidget(self.lr_spin, row, 1)
        
        row += 1
        train_layout.addWidget(QLabel("折扣因子:"), row, 0)
        self.gamma_spin = QDoubleSpinBox()
        self.gamma_spin.setRange(0.9, 0.9999)
        self.gamma_spin.setSingleStep(0.001)
        self.gamma_spin.setValue(0.99)
        self.gamma_spin.setDecimals(4)
        train_layout.addWidget(self.gamma_spin, row, 1)
        
        control_layout.addWidget(train_group)
        
        # 训练控制按钮
        button_layout = QGridLayout()
        
        self.train_btn = QPushButton("开始训练")
        self.train_btn.setStyleSheet("background-color: #27AE60; color: white; font-weight: bold; padding: 8px;")
        self.train_btn.clicked.connect(self.start_training)
        button_layout.addWidget(self.train_btn, 0, 0)
        
        self.pause_btn = QPushButton("暂停训练")
        self.pause_btn.setStyleSheet("background-color: #F39C12; color: black; padding: 8px;")
        self.pause_btn.setEnabled(False)
        self.pause_btn.clicked.connect(self.pause_training)
        button_layout.addWidget(self.pause_btn, 0, 1)
        
        self.stop_btn = QPushButton("停止训练")
        self.stop_btn.setStyleSheet("background-color: #E74C3C; color: white; padding: 8px;")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_training)
        button_layout.addWidget(self.stop_btn, 1, 0)
        
        self.eval_btn = QPushButton("评估模型")
        self.eval_btn.setStyleSheet("background-color: #3498DB; color: white; padding: 8px;")
        self.eval_btn.clicked.connect(self.evaluate_model)
        button_layout.addWidget(self.eval_btn, 1, 1)
        
        self.visualize_btn = QPushButton("策略可视化")
        self.visualize_btn.setStyleSheet("background-color: #9B59B6; color: white; padding: 8px;")
        self.visualize_btn.clicked.connect(self.visualize_strategy)
        button_layout.addWidget(self.visualize_btn, 2, 0)
        
        self.save_model_btn = QPushButton("保存模型")
        self.save_model_btn.setStyleSheet("background-color: #2C3E50; color: white; padding: 8px;")
        self.save_model_btn.clicked.connect(self.save_model)
        button_layout.addWidget(self.save_model_btn, 2, 1)
        
        self.load_model_btn = QPushButton("加载模型")
        self.load_model_btn.setStyleSheet("background-color: #16A085; color: white; padding: 8px;")
        self.load_model_btn.clicked.connect(self.load_model)
        button_layout.addWidget(self.load_model_btn, 3, 0, 1, 2)
        
        control_layout.addLayout(button_layout)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #34495E;
                border-radius: 5px;
                text-align: center;
                background: #ECF0F1;
            }
            QProgressBar::chunk {
                background: #2ECC71;
                width: 10px;
            }
        """)
        control_layout.addWidget(self.progress_bar)
        
        # 日志显示
        log_group = QGroupBox("训练日志")
        log_layout = QVBoxLayout(log_group)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 9))
        self.log_text.setStyleSheet("background-color: #1C2833; color: #EAECEE;")
        log_layout.addWidget(self.log_text)
        
        control_layout.addWidget(log_group)
        
        # 添加左右面板
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(control_panel)
        splitter.addWidget(display_panel)
        splitter.setSizes([400, 1200])
        splitter.setHandleWidth(10)
        splitter.setStyleSheet("QSplitter::handle { background-color: #566573; }")
        
        main_layout.addWidget(splitter)
        self.setCentralWidget(main_widget)
        
        # 初始化奖励数据
        self.episode_rewards = []
        self.loss_data = []
        
        # 添加状态栏
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("就绪")
    
    def log_message(self, message):
        """添加日志消息"""
        timestamp = time.strftime("%H:%M:%S", time.localtime())
        self.log_text.append(f"[{timestamp}] {message}")
        self.log_text.ensureCursorVisible()
    
    def start_training(self):
        """开始训练"""
        # 更新环境参数
        water_length = self.water_length_spin.value()
        num_agents = self.num_agents_spin.value()
        difficulty = self.difficulty_spin.value()
        max_steps = self.max_steps_spin.value()
        gravity = self.gravity_spin.value()
        
        # 创建新环境
        self.env = EnhancedLightfootEnv(
            water_length=water_length,
            num_agents=num_agents,
            difficulty=difficulty
        )
        self.env.max_steps = max_steps
        self.env.gravity = gravity
        
        # 获取训练参数
        num_episodes = self.num_episodes_spin.value()
        render_every = self.render_every_spin.value()
        
        # 创建训练线程
        self.training_thread = TrainingThread(self.env, num_episodes, render_every)
        self.training_thread.episode_completed.connect(self.update_training_progress)
        self.training_thread.training_finished.connect(self.training_finished)
        self.training_thread.render_frame.connect(self.update_agent_frame)  # 连接新信号
        
        # 更新按钮状态
        self.train_btn.setEnabled(False)
        self.pause_btn.setEnabled(True)
        self.stop_btn.setEnabled(True)
        
        # 重置奖励数据
        self.episode_rewards = []
        self.loss_data = []
        self.reward_line.set_data([], [])
        self.reward_ax.relim()
        self.reward_ax.autoscale_view()
        self.reward_canvas.draw()
        
        # 启动训练线程
        self.training_thread.start()
        
        self.log_message("训练开始...")
        self.status_bar.showMessage("训练进行中...")
    
    def pause_training(self):
        """暂停训练"""
        if self.training_thread:
            if self.training_thread.is_paused:
                self.training_thread.resume()
                self.pause_btn.setText("暂停训练")
                self.log_message("训练继续")
                self.status_bar.showMessage("训练继续")
            else:
                self.training_thread.pause()
                self.pause_btn.setText("继续训练")
                self.log_message("训练暂停")
                self.status_bar.showMessage("训练已暂停")
    
    def stop_training(self):
        """停止训练"""
        if self.training_thread:
            self.training_thread.stop()
            self.training_thread.wait()
            self.training_finished()
            self.log_message("训练已停止")
            self.status_bar.showMessage("训练已停止")
    
    def training_finished(self):
        """训练完成处理"""
        self.train_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)
        self.pause_btn.setText("暂停训练")
        
        self.log_message("训练完成!")
        self.status_bar.showMessage("训练完成")
        
        # 保存最终模型
        if self.training_thread.agents:
            for agent in self.training_thread.agents:
                agent.save_models()
            self.log_message("最终模型已保存")
    
    def update_agent_frame(self, frame):
        """更新当前帧"""
        self.current_frame = frame
    
    def update_training_progress(self, episode, rewards, losses):
        """更新训练进度"""
        # 更新进度条
        progress = int((episode + 1) / self.num_episodes_spin.value() * 100)
        self.progress_bar.setValue(progress)
        
        # 记录奖励和损失
        self.episode_rewards.append(rewards)
        self.loss_data.append(losses)
        
        # 更新奖励曲线
        episodes = list(range(len(self.episode_rewards)))
        avg_rewards = [np.mean(r) for r in self.episode_rewards]
        
        self.reward_line.set_data(episodes, avg_rewards)
        self.reward_ax.relim()
        self.reward_ax.autoscale_view()
        self.reward_canvas.draw()
        
        # 记录日志
        loss_str = ", ".join([f"C:{c:.3f} A:{a:.3f} α:{al:.3f}" for c, a, al in losses])
        self.log_message(f"轮次 {episode+1}/{self.num_episodes_spin.value()}: 奖励={rewards}, 损失={loss_str}")
        
        # 更新状态栏
        self.status_bar.showMessage(f"训练中: 轮次 {episode+1}/{self.num_episodes_spin.value()} | 平均奖励: {np.mean(avg_rewards):.2f}")
    
    def evaluate_model(self):
        """评估当前模型"""
        if self.training_thread and self.training_thread.agents:
            agent = self.training_thread.agents[0]
            self.log_message("开始评估模型...")
            self.status_bar.showMessage("评估模型中...")
            
            # 创建评估环境
            eval_env = EnhancedLightfootEnv(
                water_length=self.water_length_spin.value(),
                num_agents=self.num_agents_spin.value(),
                difficulty=self.difficulty_spin.value()
            )
            eval_env.max_steps = self.max_steps_spin.value()
            eval_env.gravity = self.gravity_spin.value()
            
            avg_reward = evaluate_agent(eval_env, agent, num_episodes=5, render=False)
            self.log_message(f"评估完成! 平均奖励: {avg_reward:.2f}")
            self.status_bar.showMessage(f"评估完成! 平均奖励: {avg_reward:.2f}")
        else:
            self.log_message("错误: 没有可用的模型进行评估")
            self.status_bar.showMessage("错误: 没有可用的模型进行评估")
    
    def visualize_strategy(self):
        """可视化策略"""
        if self.training_thread and self.training_thread.agents:
            agent = self.training_thread.agents[0]
            self.log_message("生成策略可视化...")
            self.status_bar.showMessage("生成策略可视化...")
            
            try:
                # 生成策略可视化图像
                strategy_img = visualize_skills_to_image(agent)
                
                # 在策略画布上显示
                self.strategy_ax.clear()
                self.strategy_ax.imshow(strategy_img)
                self.strategy_ax.axis('off')
                self.strategy_ax.set_title('轻功策略可视化', fontsize=14)
                self.strategy_canvas.draw()
                
                # 切换到策略标签页
                self.tab_widget.setCurrentIndex(2)
                
                self.log_message("策略可视化已生成")
                self.status_bar.showMessage("策略可视化已生成")
            except Exception as e:
                self.log_message(f"生成策略可视化时出错: {str(e)}")
                self.status_bar.showMessage(f"错误: {str(e)}")
        else:
            self.log_message("错误: 没有可用的模型进行可视化")
            self.status_bar.showMessage("错误: 没有可用的模型进行可视化")
    
    def save_model(self):
        """保存模型"""
        if self.training_thread and self.training_thread.agents:
            path = QFileDialog.getExistingDirectory(self, "选择保存目录", "models")
            if path:
                for i, agent in enumerate(self.training_thread.agents):
                    agent.model_dir = os.path.join(path, f"agent_{i}")
                    os.makedirs(agent.model_dir, exist_ok=True)
                    agent.save_models()
                self.log_message(f"模型已保存到: {path}")
                self.status_bar.showMessage(f"模型已保存到: {path}")
        else:
            self.log_message("错误: 没有可用的模型保存")
            self.status_bar.showMessage("错误: 没有可用的模型保存")
    
    def load_model(self):
        """加载模型"""
        path = QFileDialog.getExistingDirectory(self, "选择模型目录", "models")
        if path:
            # 创建临时agent来加载模型
            agent = SACAgent(self.env.observation_space.shape[0], 
                           self.env.action_space.shape[0], 0)
            agent.model_dir = path
            if agent.load_models():
                self.log_message(f"模型已从 {path} 加载")
                self.status_bar.showMessage(f"模型已加载")
                
                # 如果训练线程存在，更新其agents
                if self.training_thread:
                    self.training_thread.agents = [agent]
            else:
                self.log_message("错误: 加载模型失败")
                self.status_bar.showMessage("错误: 加载模型失败")
    
    def update_render(self):
        """更新渲染显示"""
        if self.current_frame is not None:
            try:
                # 将numpy数组转换为QImage
                height, width, channel = self.current_frame.shape
                bytes_per_line = 3 * width
                q_img = QImage(self.current_frame.data, width, height, bytes_per_line, QImage.Format_RGB888)
                
                # 创建QPixmap并显示
                pixmap = QPixmap.fromImage(q_img)
                self.render_label.setPixmap(pixmap.scaled(
                    self.render_label.width(), 
                    self.render_label.height(),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                ))
                
                # 更新状态信息
                if self.training_thread and self.training_thread.agents:
                    agent = self.training_thread.agents[0]
                    self.position_label.setText(f"位置: {agent['position']:.1f}/{self.env.water_length}")
                    self.energy_label.setText(f"内力: {agent['energy']:.1f}/{self.env.max_energy}")
                    self.velocity_label.setText(f"速度: {agent['velocity']:.2f}")
                    self.height_label.setText(f"高度: {agent['height']:.2f}")
                    self.wind_label.setText(f"风速: {self.env.wind_speed:.2f}")
                    self.water_current_label.setText(f"水流: {self.env.water_current:.2f}")
                    
            except Exception as e:
                # 防止渲染错误中断程序
                pass

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 设置应用样式
    app.setStyle("Fusion")
    app.setStyleSheet("""
        QMainWindow {
            background-color: #34495E;
        }
        QGroupBox {
            font-weight: bold;
            border: 1px solid #2C3E50;
            border-radius: 5px;
            margin-top: 1ex;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top center;
            padding: 0 5px;
        }
        QLabel {
            color: #2C3E50;
        }
        QTextEdit {
            background-color: #ECF0F1;
            border: 1px solid #BDC3C7;
            border-radius: 3px;
        }
        QTabWidget::pane {
            border: 1px solid #BDC3C7;
            background: #ECF0F1;
        }
        QTabBar::tab {
            background: #BDC3C7;
            color: #2C3E50;
            padding: 8px;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
        }
        QTabBar::tab:selected {
            background: #3498DB;
            color: white;
        }
    """)
    
    window = LightfootApp()
    window.show()
    sys.exit(app.exec_())