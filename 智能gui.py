import sys
import json
import time
import threading
import random
import numpy as np
from datetime import datetime
from pathlib import Path
from collections import deque

import pyautogui
import keyboard
import cv2
import pytesseract
from PIL import Image
from skimage import metrics
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QTextEdit, QLabel, 
                             QListWidget, QGroupBox, QSpinBox, QComboBox,
                             QFileDialog, QMessageBox, QCheckBox, QTabWidget,
                             QLineEdit, QSlider, QProgressBar, QSplitter)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QIcon, QPixmap, QImage


class QLearningAgent:
    """Q学习强化学习智能体"""
    def __init__(self, state_size, action_size, learning_rate=0.1, discount_factor=0.95, exploration_rate=1.0, exploration_decay=0.995):
        self.state_size = state_size
        self.action_size = action_size
        self.learning_rate = learning_rate
        self.discount_factor = discount_factor
        self.exploration_rate = exploration_rate
        self.exploration_decay = exploration_decay
        self.min_exploration = 0.01
        self.q_table = {}
        
    def get_state_key(self, state):
        """将状态转换为可哈希的键"""
        return tuple(state.flatten()) if hasattr(state, 'flatten') else tuple(state)
        
    def choose_action(self, state):
        """根据当前状态选择动作"""
        state_key = self.get_state_key(state)
        
        # 初始化未知状态的Q值
        if state_key not in self.q_table:
            self.q_table[state_key] = np.zeros(self.action_size)
            
        # 探索-利用权衡
        if np.random.rand() < self.exploration_rate:
            return random.randrange(self.action_size)
        else:
            return np.argmax(self.q_table[state_key])
            
    def learn(self, state, action, reward, next_state, done):
        """更新Q值"""
        state_key = self.get_state_key(state)
        next_state_key = self.get_state_key(next_state)
        
        # 初始化未知状态的Q值
        if next_state_key not in self.q_table:
            self.q_table[next_state_key] = np.zeros(self.action_size)
            
        # Q学习更新规则
        if done:
            target = reward
        else:
            target = reward + self.discount_factor * np.max(self.q_table[next_state_key])
            
        self.q_table[state_key][action] += self.learning_rate * (target - self.q_table[state_key][action])
        
        # 衰减探索率
        if done:
            self.exploration_rate = max(self.min_exploration, self.exploration_rate * self.exploration_decay)
            
    def save(self, filepath):
        """保存Q表"""
        # 将numpy数组转换为列表以便序列化
        save_data = {str(k): v.tolist() for k, v in self.q_table.items()}
        with open(filepath, 'w') as f:
            json.dump(save_data, f)
            
    def load(self, filepath):
        """加载Q表"""
        with open(filepath, 'r') as f:
            loaded_data = json.load(f)
            
        # 将键转换回元组，值转换回numpy数组
        self.q_table = {}
        for k, v in loaded_data.items():
            # 将字符串键转换回元组
            key_tuple = tuple(map(float, k.strip('()').split(', ')))
            self.q_table[key_tuple] = np.array(v)


class DQNAgent:
    """深度Q网络智能体（简化版）"""
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
        
    def _build_model(self):
        """构建神经网络模型（简化版）"""
        # 在实际应用中，这里应该使用深度学习框架如TensorFlow或PyTorch
        # 这里我们使用一个简化的模拟版本
        class SimpleModel:
            def __init__(self, state_size, action_size, learning_rate):
                self.weights = np.random.randn(state_size, action_size) * 0.01
                self.bias = np.zeros((1, action_size))
                self.learning_rate = learning_rate
                
            def predict(self, state):
                return np.dot(state, self.weights) + self.bias
                
            def fit(self, states, targets):
                # 简化的梯度下降更新
                for i in range(len(states)):
                    state = states[i]
                    target = targets[i]
                    
                    # 前向传播
                    prediction = np.dot(state, self.weights) + self.bias
                    
                    # 计算梯度
                    error = prediction - target
                    dW = np.outer(state, error)
                    db = error
                    
                    # 更新权重
                    self.weights -= self.learning_rate * dW
                    self.bias -= self.learning_rate * db
                    
        return SimpleModel(self.state_size, self.action_size, self.learning_rate)
        
    def remember(self, state, action, reward, next_state, done):
        """存储经验到记忆库"""
        self.memory.append((state, action, reward, next_state, done))
        
    def choose_action(self, state):
        """根据当前状态选择动作"""
        if np.random.rand() <= self.epsilon:
            return random.randrange(self.action_size)
        act_values = self.model.predict(state)
        return np.argmax(act_values[0])
        
    def replay(self, batch_size):
        """从记忆库中回放经验进行学习"""
        if len(self.memory) < batch_size:
            return
            
        minibatch = random.sample(self.memory, batch_size)
        states = []
        targets = []
        
        for state, action, reward, next_state, done in minibatch:
            target = self.model.predict(state)
            if done:
                target[0][action] = reward
            else:
                next_prediction = self.model.predict(next_state)
                target[0][action] = reward + self.gamma * np.amax(next_prediction[0])
                
            states.append(state)
            targets.append(target[0])
            
        # 批量训练模型
        self.model.fit(np.array(states), np.array(targets))
        
        # 衰减探索率
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay
            
    def save(self, filepath):
        """保存模型权重"""
        data = {
            'weights': self.model.weights.tolist(),
            'bias': self.model.bias.tolist(),
            'epsilon': self.epsilon
        }
        with open(filepath, 'w') as f:
            json.dump(data, f)
            
    def load(self, filepath):
        """加载模型权重"""
        with open(filepath, 'r') as f:
            data = json.load(f)
            
        self.model.weights = np.array(data['weights'])
        self.model.bias = np.array(data['bias'])
        self.epsilon = data['epsilon']


class ScreenProcessor:
    """屏幕处理工具类"""
    @staticmethod
    def capture_screen(region=None):
        """捕获屏幕区域"""
        screenshot = pyautogui.screenshot(region=region)
        return cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
    
    @staticmethod
    def extract_features(image, size=(64, 64)):
        """从图像中提取特征"""
        # 调整大小
        resized = cv2.resize(image, size)
        # 转换为灰度图
        gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
        # 归一化
        normalized = gray / 255.0
        return normalized.flatten()
    
    @staticmethod
    def find_template(template_path, screen_region=None, threshold=0.8):
        """在屏幕上查找模板图像"""
        # 读取模板图像
        template = cv2.imread(template_path)
        if template is None:
            return None
            
        # 捕获屏幕
        screen = ScreenProcessor.capture_screen(screen_region)
        
        # 模板匹配
        result = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
        
        if max_val >= threshold:
            # 返回匹配位置（中心点）
            h, w = template.shape[:2]
            center_x = max_loc[0] + w // 2
            center_y = max_loc[1] + h // 2
            return (center_x, center_y), max_val
        return None, max_val
    
    @staticmethod
    def extract_text(image, lang='eng'):
        """从图像中提取文本"""
        # 使用OCR提取文本
        pil_image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        text = pytesseract.image_to_string(pil_image, lang=lang)
        return text.strip()


class AutomationEnvironment:
    """自动化环境，用于强化学习"""
    def __init__(self, target_regions, actions):
        self.target_regions = target_regions  # 目标区域列表
        self.actions = actions  # 可用动作列表
        self.current_state = None
        self.current_region_idx = 0
        self.steps = 0
        self.max_steps = 100
        
    def reset(self):
        """重置环境"""
        self.current_region_idx = 0
        self.steps = 0
        # 捕获当前屏幕状态
        self.current_state = self.get_state()
        return self.current_state
        
    def get_state(self):
        """获取当前状态"""
        if self.current_region_idx >= len(self.target_regions):
            region = None  # 全屏
        else:
            region = self.target_regions[self.current_region_idx]
            
        screen = ScreenProcessor.capture_screen(region)
        return ScreenProcessor.extract_features(screen)
        
    def step(self, action_idx):
        """执行动作并返回新状态、奖励和完成标志"""
        self.steps += 1
        
        # 执行动作
        action = self.actions[action_idx]
        reward = self.execute_action(action)
        
        # 获取新状态
        new_state = self.get_state()
        self.current_state = new_state
        
        # 检查是否完成
        done = self.is_done() or self.steps >= self.max_steps
        
        return new_state, reward, done
        
    def execute_action(self, action):
        """执行具体动作并返回奖励"""
        action_type = action.get('type', 'click')
        
        if action_type == 'click':
            x, y = action.get('x', 0), action.get('y', 0)
            button = action.get('button', 'left')
            pyautogui.click(x, y, button=button)
            return self.calculate_reward()
            
        elif action_type == 'type':
            text = action.get('text', '')
            pyautogui.write(text)
            return 0.1  # 小型奖励
            
        elif action_type == 'hotkey':
            keys = action.get('keys', [])
            pyautogui.hotkey(*keys)
            return 0.2  # 中型奖励
            
        elif action_type == 'wait':
            duration = action.get('duration', 1)
            time.sleep(duration)
            return -0.1  # 小型惩罚
            
        return 0  # 默认无奖励
        
    def calculate_reward(self):
        """计算奖励值"""
        # 这里可以根据具体任务设计奖励函数
        # 例如，检测是否成功点击了目标，或者是否完成了特定任务
        
        # 简单示例：如果成功进入下一个区域，给予奖励
        if self.check_region_completion():
            self.current_region_idx += 1
            return 1.0  # 大型奖励
            
        return -0.01  # 小型惩罚，鼓励高效完成任务
        
    def check_region_completion(self):
        """检查当前区域是否完成"""
        # 这里可以实现具体的完成检测逻辑
        # 例如，检测特定图像或文本是否出现
        
        # 简单示例：随机决定是否完成
        return random.random() < 0.3
        
    def is_done(self):
        """检查是否完成所有任务"""
        return self.current_region_idx >= len(self.target_regions)


class IntelligentAutomationSystem(QMainWindow):
    """智能自动化系统主窗口"""
    update_log_signal = pyqtSignal(str)
    update_status_signal = pyqtSignal(str)
    update_progress_signal = pyqtSignal(int)
    
    def __init__(self):
        super().__init__()
        self.recorder = AutomationRecorder()
        self.player = AutomationPlayer()
        self.screen_processor = ScreenProcessor()
        self.current_script = []
        self.script_file = None
        self.rl_agent = None
        self.env = None
        self.is_training = False
        self.training_thread = None
        
        self.update_log_signal.connect(self.update_log)
        self.update_status_signal.connect(self.update_status)
        self.update_progress_signal.connect(self.update_progress)
        
        self.setup_ui()
        self.setup_mouse_listener()
        
    def setup_ui(self):
        """设置用户界面"""
        self.setWindowTitle("智能自动化系统 - 基于强化学习")
        self.setGeometry(100, 100, 1200, 800)
        
        # 创建中心部件和主布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # 创建左右分割器
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        # 左侧面板 - 控制和状态
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        splitter.addWidget(left_panel)
        
        # 右侧面板 - 日志和可视化
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        splitter.addWidget(right_panel)
        
        # 设置分割器比例
        splitter.setSizes([400, 800])
        
        # 左侧面板内容
        # 控制按钮区域
        control_group = QGroupBox("控制")
        control_layout = QVBoxLayout(control_group)
        
        record_play_layout = QHBoxLayout()
        self.record_btn = QPushButton("开始录制")
        self.record_btn.clicked.connect(self.toggle_recording)
        record_play_layout.addWidget(self.record_btn)
        
        self.play_btn = QPushButton("开始回放")
        self.play_btn.clicked.connect(self.toggle_playback)
        record_play_layout.addWidget(self.play_btn)
        
        self.stop_btn = QPushButton("停止")
        self.stop_btn.clicked.connect(self.stop)
        self.stop_btn.setEnabled(False)
        record_play_layout.addWidget(self.stop_btn)
        
        control_layout.addLayout(record_play_layout)
        
        # 回放设置
        play_settings_layout = QHBoxLayout()
        play_settings_layout.addWidget(QLabel("速度:"))
        self.speed_spin = QSpinBox()
        self.speed_spin.setRange(1, 10)
        self.speed_spin.setValue(1)
        play_settings_layout.addWidget(self.speed_spin)
        
        play_settings_layout.addWidget(QLabel("循环次数:"))
        self.loop_combo = QComboBox()
        self.loop_combo.addItems(["1", "3", "5", "10", "无限"])
        play_settings_layout.addWidget(self.loop_combo)
        
        control_layout.addLayout(play_settings_layout)
        left_layout.addWidget(control_group)
        
        # 强化学习设置
        rl_group = QGroupBox("强化学习设置")
        rl_layout = QVBoxLayout(rl_group)
        
        # 算法选择
        algorithm_layout = QHBoxLayout()
        algorithm_layout.addWidget(QLabel("算法:"))
        self.algorithm_combo = QComboBox()
        self.algorithm_combo.addItems(["Q学习", "深度Q网络"])
        algorithm_layout.addWidget(self.algorithm_combo)
        rl_layout.addLayout(algorithm_layout)
        
        # 学习参数
        params_layout = QHBoxLayout()
        params_layout.addWidget(QLabel("学习率:"))
        self.learning_rate_input = QLineEdit("0.1")
        params_layout.addWidget(self.learning_rate_input)
        
        params_layout.addWidget(QLabel("折扣因子:"))
        self.discount_factor_input = QLineEdit("0.95")
        params_layout.addWidget(self.discount_factor_input)
        rl_layout.addLayout(params_layout)
        
        # 训练控制
        train_control_layout = QHBoxLayout()
        self.train_btn = QPushButton("开始训练")
        self.train_btn.clicked.connect(self.toggle_training)
        train_control_layout.addWidget(self.train_btn)
        
        self.save_model_btn = QPushButton("保存模型")
        self.save_model_btn.clicked.connect(self.save_model)
        train_control_layout.addWidget(self.save_model_btn)
        
        self.load_model_btn = QPushButton("加载模型")
        self.load_model_btn.clicked.connect(self.load_model)
        train_control_layout.addWidget(self.load_model_btn)
        
        rl_layout.addLayout(train_control_layout)
        
        # 训练进度
        self.training_progress = QProgressBar()
        self.training_progress.setValue(0)
        rl_layout.addWidget(self.training_progress)
        
        left_layout.addWidget(rl_group)
        
        # 动作列表
        actions_group = QGroupBox("动作列表")
        actions_layout = QVBoxLayout(actions_group)
        
        self.actions_list = QListWidget()
        actions_layout.addWidget(self.actions_list)
        
        # 动作列表按钮
        action_buttons_layout = QHBoxLayout()
        self.clear_btn = QPushButton("清空列表")
        self.clear_btn.clicked.connect(self.clear_actions)
        action_buttons_layout.addWidget(self.clear_btn)
        
        self.save_btn = QPushButton("保存脚本")
        self.save_btn.clicked.connect(self.save_script)
        action_buttons_layout.addWidget(self.save_btn)
        
        self.load_btn = QPushButton("加载脚本")
        self.load_btn.clicked.connect(self.load_script)
        action_buttons_layout.addWidget(self.load_btn)
        
        actions_layout.addLayout(action_buttons_layout)
        left_layout.addWidget(actions_group)
        
        # 右侧面板内容
        # 日志区域
        log_group = QGroupBox("系统日志")
        log_layout = QVBoxLayout(log_group)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)
        
        right_layout.addWidget(log_group)
        
        # 屏幕可视化区域
        screen_group = QGroupBox("屏幕可视化")
        screen_layout = QVBoxLayout(screen_group)
        
        self.screen_label = QLabel()
        self.screen_label.setAlignment(Qt.AlignCenter)
        self.screen_label.setMinimumSize(640, 360)
        self.screen_label.setText("屏幕捕获将显示在这里")
        screen_layout.addWidget(self.screen_label)
        
        screen_control_layout = QHBoxLayout()
        self.capture_btn = QPushButton("捕获屏幕")
        self.capture_btn.clicked.connect(self.capture_and_display_screen)
        screen_control_layout.addWidget(self.capture_btn)
        
        self.analyze_btn = QPushButton("分析屏幕")
        self.analyze_btn.clicked.connect(self.analyze_screen)
        screen_control_layout.addWidget(self.analyze_btn)
        
        screen_layout.addLayout(screen_control_layout)
        right_layout.addWidget(screen_group)
        
        # 状态栏
        self.statusBar().showMessage("就绪")
        
    def setup_mouse_listener(self):
        """设置鼠标监听器"""
        self.mouse_timer = QTimer()
        self.mouse_timer.timeout.connect(self.check_mouse)
        self.mouse_timer.start(100)  # 每100毫秒检查一次
        
        # 屏幕捕获定时器
        self.screen_timer = QTimer()
        self.screen_timer.timeout.connect(self.update_screen_display)
        self.screen_timer.start(1000)  # 每1秒更新一次屏幕显示
        
    def check_mouse(self):
        """检查鼠标状态"""
        if self.recorder.recording:
            x, y = pyautogui.position()
            self.recorder.record_mouse_move(x, y)
            
    def update_screen_display(self):
        """更新屏幕显示"""
        if not self.isVisible():
            return
            
        # 捕获屏幕
        screen = self.screen_processor.capture_screen()
        # 调整大小以适应显示
        screen = cv2.resize(screen, (640, 360))
        
        # 转换为QImage
        height, width, channel = screen.shape
        bytes_per_line = 3 * width
        q_img = QImage(screen.data, width, height, bytes_per_line, QImage.Format_RGB888).rgbSwapped()
        
        # 显示图像
        self.screen_label.setPixmap(QPixmap.fromImage(q_img))
        
    def capture_and_display_screen(self):
        """捕获并显示屏幕"""
        self.update_screen_display()
        self.log("屏幕已捕获")
        
    def analyze_screen(self):
        """分析屏幕内容"""
        screen = self.screen_processor.capture_screen()
        
        # 提取文本
        text = self.screen_processor.extract_text(screen)
        if text:
            self.log(f"提取的文本: {text}")
            
        # 这里可以添加更多的屏幕分析功能
        self.log("屏幕分析完成")
        
    def toggle_training(self):
        """切换训练状态"""
        if not self.is_training:
            self.start_training()
        else:
            self.stop_training()
            
    def start_training(self):
        """开始强化学习训练"""
        if not self.actions_list.count():
            QMessageBox.warning(self, "警告", "请先定义一些动作")
            return
            
        # 收集动作
        actions = []
        for i in range(self.actions_list.count()):
            item = self.actions_list.item(i)
            # 从项目文本中解析动作（这里需要根据实际格式实现）
            action = self.parse_action_from_text(item.text())
            if action:
                actions.append(action)
                
        if not actions:
            QMessageBox.warning(self, "警告", "无法解析动作")
            return
            
        # 创建环境
        # 这里需要定义目标区域，可以根据实际需求调整
        target_regions = [(0, 0, 1920, 1080)]  # 示例：全屏
        
        self.env = AutomationEnvironment(target_regions, actions)
        
        # 创建智能体
        algorithm = self.algorithm_combo.currentText()
        state_size = 64 * 64  # 特征向量大小
        action_size = len(actions)
        
        if algorithm == "Q学习":
            learning_rate = float(self.learning_rate_input.text())
            discount_factor = float(self.discount_factor_input.text())
            self.rl_agent = QLearningAgent(state_size, action_size, learning_rate, discount_factor)
        else:  # 深度Q网络
            self.rl_agent = DQNAgent(state_size, action_size)
            
        # 开始训练线程
        self.is_training = True
        self.train_btn.setText("停止训练")
        self.training_thread = threading.Thread(target=self.training_loop)
        self.training_thread.daemon = True
        self.training_thread.start()
        
        self.log("开始强化学习训练")
        
    def stop_training(self):
        """停止训练"""
        self.is_training = False
        self.train_btn.setText("开始训练")
        self.log("训练已停止")
        
    def training_loop(self):
        """训练循环"""
        batch_size = 32
        episodes = 100
        max_steps_per_episode = 100
        
        for episode in range(episodes):
            if not self.is_training:
                break
                
            state = self.env.reset()
            total_reward = 0
            
            for step in range(max_steps_per_episode):
                if not self.is_training:
                    break
                    
                # 选择动作
                action = self.rl_agent.choose_action(state)
                
                # 执行动作
                next_state, reward, done = self.env.step(action)
                total_reward += reward
                
                # 学习
                if isinstance(self.rl_agent, QLearningAgent):
                    self.rl_agent.learn(state, action, reward, next_state, done)
                else:  # DQNAgent
                    self.rl_agent.remember(state, action, reward, next_state, done)
                    self.rl_agent.replay(batch_size)
                    
                state = next_state
                
                if done:
                    break
                    
            # 更新进度
            progress = int((episode + 1) / episodes * 100)
            self.update_progress_signal.emit(progress)
            
            # 记录日志
            self.update_log_signal.emit(f"回合 {episode + 1}/{episodes}, 总奖励: {total_reward:.2f}")
            
        self.update_log_signal.emit("训练完成")
        self.update_progress_signal.emit(0)
        self.is_training = False
        self.train_btn.setText("开始训练")
        
    def save_model(self):
        """保存模型"""
        if self.rl_agent is None:
            QMessageBox.warning(self, "警告", "没有可保存的模型")
            return
            
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存模型", "", "JSON Files (*.json)"
        )
        
        if file_path:
            try:
                self.rl_agent.save(file_path)
                self.log(f"模型已保存到: {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"保存模型时出错: {str(e)}")
                
    def load_model(self):
        """加载模型"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "加载模型", "", "JSON Files (*.json)"
        )
        
        if file_path:
            try:
                # 需要先创建智能体，然后加载
                algorithm = self.algorithm_combo.currentText()
                state_size = 64 * 64  # 特征向量大小
                action_size = self.actions_list.count()
                
                if algorithm == "Q学习":
                    self.rl_agent = QLearningAgent(state_size, action_size)
                else:  # 深度Q网络
                    self.rl_agent = DQNAgent(state_size, action_size)
                    
                self.rl_agent.load(file_path)
                self.log(f"已加载模型: {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"加载模型时出错: {str(e)}")
                
    def parse_action_from_text(self, text):
        """从文本解析动作（简化版）"""
        # 在实际应用中，这里需要根据动作列表的显示格式实现解析逻辑
        # 这里返回一个示例动作
        return {
            'type': 'click',
            'x': 100,
            'y': 100,
            'button': 'left'
        }
        
    def update_log(self, message):
        """更新日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
        
    def update_status(self, message):
        """更新状态栏"""
        self.statusBar().showMessage(message)
        
    def update_progress(self, value):
        """更新进度条"""
        self.training_progress.setValue(value)
        
    # 以下方法与前一个示例相同，为保持完整性保留
    def toggle_recording(self):
        """切换录制状态"""
        if not self.recorder.recording:
            self.start_recording()
        else:
            self.stop_recording()
            
    def start_recording(self):
        """开始录制"""
        self.recorder.start_recording()
        self.record_btn.setText("停止录制")
        self.stop_btn.setEnabled(True)
        self.play_btn.setEnabled(False)
        self.update_status("录制中...")
        self.update_log("开始录制")
        
    def stop_recording(self):
        """停止录制"""
        self.recorder.stop_recording()
        self.record_btn.setText("开始录制")
        self.stop_btn.setEnabled(False)
        self.play_btn.setEnabled(True)
        self.update_status("录制完成")
        self.update_log("停止录制")
        
        # 更新动作列表
        self.update_actions_list()
        
    def toggle_playback(self):
        """切换回放状态"""
        if not self.player.playing:
            self.start_playback()
        else:
            self.stop_playback()
            
    def start_playback(self):
        """开始回放"""
        # 获取回放设置
        speed = self.speed_spin.value()
        loop_count = self.loop_combo.currentText()
        loop = loop_count == "无限"
        
        # 加载动作并开始回放
        self.player.load_actions(self.recorder.get_actions())
        if self.player.start_playback(speed, loop):
            self.play_btn.setText("停止回放")
            self.record_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            self.update_status("回放中...")
            self.update_log("开始回放")
            
    def stop_playback(self):
        """停止回放"""
        self.player.stop_playback()
        self.play_btn.setText("开始回放")
        self.record_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.update_status("回放停止")
        self.update_log("停止回放")
        
    def stop(self):
        """停止所有操作"""
        if self.recorder.recording:
            self.stop_recording()
        if self.player.playing:
            self.stop_playback()
        if self.is_training:
            self.stop_training()
            
    def clear_actions(self):
        """清空动作列表"""
        self.recorder.actions = []
        self.actions_list.clear()
        self.update_log("已清空动作列表")
        
    def update_actions_list(self):
        """更新动作列表显示"""
        self.actions_list.clear()
        for i, action in enumerate(self.recorder.actions):
            if action['type'] == 'mouse':
                if action['action'] == 'move':
                    text = f"{i+1}. 移动到 ({action['x']}, {action['y']})"
                else:
                    text = f"{i+1}. 点击 ({action['x']}, {action['y']}) [{action['button']}]"
            else:
                text = f"{i+1}. 按键 [{action['key']}]"
                
            self.actions_list.addItem(text)
            
    def save_script(self):
        """保存脚本到文件"""
        if not self.recorder.actions:
            QMessageBox.warning(self, "警告", "没有可保存的动作")
            return
            
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存脚本", "", "JSON Files (*.json)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w') as f:
                    json.dump(self.recorder.actions, f, indent=4)
                self.update_log(f"脚本已保存到: {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"保存脚本时出错: {str(e)}")
                
    def load_script(self):
        """从文件加载脚本"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "加载脚本", "", "JSON Files (*.json)"
        )
        
        if file_path:
            try:
                with open(file_path, 'r') as f:
                    actions = json.load(f)
                self.recorder.actions = actions
                self.update_actions_list()
                self.update_log(f"已加载脚本: {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"加载脚本时出错: {str(e)}")
                
    def closeEvent(self, event):
        """应用程序关闭事件"""
        # 确保停止所有操作
        self.stop()
        # 移除所有键盘监听
        keyboard.unhook_all()
        event.accept()


# 以下是前面示例中的AutomationRecorder和AutomationPlayer类
# 为保持完整性，这里再次包含它们

class AutomationRecorder:
    """录制鼠标和键盘操作的类"""
    def __init__(self):
        self.actions = []
        self.recording = False
        self.start_time = None
        
    def start_recording(self):
        """开始录制"""
        self.actions = []
        self.recording = True
        self.start_time = time.time()
        # 设置热键监听
        keyboard.hook(self._record_keyboard)
        
    def stop_recording(self):
        """停止录制"""
        self.recording = False
        keyboard.unhook_all()
        
    def _record_keyboard(self, event):
        """记录键盘事件"""
        if self.recording and event.event_type == 'down':
            action = {
                'type': 'keyboard',
                'action': 'key_press',
                'key': event.name,
                'time': time.time() - self.start_time
            }
            self.actions.append(action)
            
    def record_mouse_click(self, x, y, button, pressed):
        """记录鼠标点击事件"""
        if self.recording and pressed:
            action = {
                'type': 'mouse',
                'action': 'click',
                'button': button.name,
                'x': x,
                'y': y,
                'time': time.time() - self.start_time
            }
            self.actions.append(action)
            
    def record_mouse_move(self, x, y):
        """记录鼠标移动事件"""
        if self.recording:
            action = {
                'type': 'mouse',
                'action': 'move',
                'x': x,
                'y': y,
                'time': time.time() - self.start_time
            }
            self.actions.append(action)
            
    def get_actions(self):
        """获取录制的动作列表"""
        return self.actions


class AutomationPlayer:
    """回放自动化操作的类"""
    def __init__(self):
        self.playing = False
        self.actions = []
        self.current_action_index = 0
        self.play_thread = None
        
    def load_actions(self, actions):
        """加载动作列表"""
        self.actions = actions
        
    def start_playback(self, speed=1.0, loop=False):
        """开始回放"""
        if not self.actions:
            return False
            
        self.playing = True
        self.current_action_index = 0
        self.play_thread = threading.Thread(
            target=self._playback_thread, 
            args=(speed, loop)
        )
        self.play_thread.daemon = True
        self.play_thread.start()
        return True
        
    def stop_playback(self):
        """停止回放"""
        self.playing = False
        if self.play_thread and self.play_thread.is_alive():
            self.play_thread.join(timeout=1.0)
            
    def _playback_thread(self, speed, loop):
        """回放线程"""
        while self.playing and self.current_action_index < len(self.actions):
            action = self.actions[self.current_action_index]
            
            # 等待适当的时间
            if self.current_action_index > 0:
                prev_time = self.actions[self.current_action_index - 1]['time']
                current_time = action['time']
                delay = (current_time - prev_time) / speed
                time.sleep(delay)
            else:
                time.sleep(action['time'] / speed)
                
            # 执行动作
            if self.playing:
                self._execute_action(action)
                self.current_action_index += 1
                
        # 如果需要循环播放
        if loop and self.playing:
            self.current_action_index = 0
            self._playback_thread(speed, loop)
            
    def _execute_action(self, action):
        """执行单个动作"""
        try:
            if action['type'] == 'mouse':
                if action['action'] == 'move':
                    pyautogui.moveTo(action['x'], action['y'])
                elif action['action'] == 'click':
                    pyautogui.click(action['x'], action['y'], button=action['button'])
            elif action['type'] == 'keyboard':
                if action['action'] == 'key_press':
                    pyautogui.press(action['key'])
        except Exception as e:
            print(f"执行动作时出错: {e}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = IntelligentAutomationSystem()
    window.show()
    sys.exit(app.exec_())