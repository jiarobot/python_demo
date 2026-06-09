import sys
import os
import numpy as np
import librosa
import soundfile as sf
import pygame
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QSlider, 
                             QFileDialog, QMessageBox, QTabWidget, QTextEdit,
                             QGroupBox, QComboBox, QSpinBox, QDoubleSpinBox,
                             QCheckBox, QProgressBar, QSplitter, QListWidget,
                             QListWidgetItem, QTreeWidget, QTreeWidgetItem,
                             QDial, QFrame, QScrollArea, QSizePolicy,
                             QInputDialog, QLineEdit, QToolBar, QAction,
                             QStatusBar, QMenuBar, QMenu, QToolButton,
                             QGridLayout, QFormLayout, QProgressDialog)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QPropertyAnimation, QEasingCurve, pyqtProperty
from PyQt5.QtGui import QPixmap, QFont, QPalette, QColor, QIcon, QPainter, QLinearGradient, QPen, QBrush
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib
matplotlib.rc("font", family='Microsoft YaHei')
from matplotlib.figure import Figure
import matplotlib.gridspec as gridspec
from scipy import signal
from scipy.io import wavfile
import random
import math
from datetime import datetime
import json
import pickle
from collections import deque, defaultdict
import hashlib


# ==================== 量子音乐生成器 ====================

class QuantumMusicGenerator:
    """量子启发的音乐生成系统 - 实现真正的无中生有"""
    
    def __init__(self):
        self.wave_function = None
        self.quantum_state = None
        self.entanglement_map = {}
        self.superposition_states = []
        self.observer_effect = 0.1  # 观察者效应强度
        
    def initialize_quantum_field(self, dimensions=128):
        """初始化量子音乐场"""
        # 创建量子叠加态
        self.wave_function = np.random.randn(dimensions) + 1j * np.random.randn(dimensions)
        self.wave_function = self.wave_function / np.linalg.norm(self.wave_function)
        
        # 初始化纠缠网络
        self._create_entanglement_network(dimensions)
        
        return True
    
    def _create_entanglement_network(self, dimensions):
        """创建量子纠缠网络"""
        # 基于小世界网络创建纠缠关系
        for i in range(dimensions):
            connections = []
            # 连接邻近节点
            for j in range(max(0, i-3), min(dimensions, i+4)):
                if i != j:
                    connections.append(j)
            # 添加随机长程连接（小世界特性）
            for _ in range(2):
                random_node = random.randint(0, dimensions-1)
                if random_node not in connections:
                    connections.append(random_node)
            
            self.entanglement_map[i] = connections
    
    def quantum_collapse_to_melody(self, observation_point=None):
        """通过量子塌缩生成旋律"""
        if self.wave_function is None:
            self.initialize_quantum_field()
        
        # 如果没有观察点，随机选择
        if observation_point is None:
            observation_point = random.randint(0, len(self.wave_function)-1)
        
        # 应用观察者效应 - 导致波函数塌缩
        collapsed_wave = self._apply_observer_effect(observation_point)
        
        # 将塌缩后的量子态转换为旋律
        melody = self._quantum_state_to_melody(collapsed_wave)
        
        # 更新量子场（根据塌缩结果）
        self._update_quantum_field(collapsed_wave, observation_point)
        
        return melody
    
    def _apply_observer_effect(self, observation_point):
        """应用观察者效应导致波函数塌缩"""
        # 计算概率幅度
        probabilities = np.abs(self.wave_function) ** 2
        
        # 增强观察点附近的概率
        probabilities[observation_point] += self.observer_effect
        probabilities = probabilities / np.sum(probabilities)
        
        # 根据概率分布进行塌缩
        collapsed_index = np.random.choice(len(probabilities), p=probabilities)
        
        # 创建塌缩后的状态向量
        collapsed_state = np.zeros_like(self.wave_function, dtype=complex)
        collapsed_state[collapsed_index] = 1.0  # 确定态
        
        # 考虑纠缠效应 - 纠缠节点也会受到影响
        for entangled_node in self.entanglement_map.get(collapsed_index, []):
            # 纠缠节点的状态也会部分塌缩
            entanglement_strength = 0.3  # 纠缠强度
            collapsed_state[entangled_node] = entanglement_strength
        
        return collapsed_state
    
    def _quantum_state_to_melody(self, quantum_state):
        """将量子态转换为旋律"""
        # 提取实部和虚部作为音乐参数
        real_part = np.real(quantum_state)
        imag_part = np.imag(quantum_state)
        
        # 归一化
        real_part = real_part / (np.max(np.abs(real_part)) + 1e-8)
        imag_part = imag_part / (np.max(np.abs(imag_part)) + 1e-8)
        
        # 生成旋律序列（2秒的旋律）
        duration = 2.0  # 秒
        sample_rate = 22050
        t = np.linspace(0, duration, int(sample_rate * duration))
        
        melody_wave = np.zeros_like(t)
        
        # 使用量子态的实部和虚部生成复合波形
        for i in range(min(20, len(real_part))):  # 使用前20个分量
            if abs(real_part[i]) > 0.01:  # 只使用显著的分量
                # 基频在音乐范围内 (100-1000 Hz)
                base_freq = 100 + 900 * (abs(real_part[i]) ** 0.5)
                
                # 添加谐波
                for harmonic in range(1, 6):
                    freq = base_freq * harmonic
                    amplitude = abs(real_part[i]) / (harmonic ** 1.2)
                    phase = imag_part[i] * 2 * np.pi
                    
                    melody_wave += amplitude * np.sin(2 * np.pi * freq * t + phase)
        
        # 应用包络
        envelope = np.ones_like(t)
        attack = int(0.1 * len(t))
        decay = int(0.3 * len(t))
        release = int(0.2 * len(t))
        
        envelope[:attack] = np.linspace(0, 1, attack)
        envelope[attack:decay] = np.linspace(1, 0.7, decay-attack)
        envelope[-release:] = np.linspace(0.7, 0, release)
        
        melody_wave *= envelope
        
        # 归一化
        if np.max(np.abs(melody_wave)) > 0:
            melody_wave = melody_wave / np.max(np.abs(melody_wave))
        
        return melody_wave, sample_rate
    
    def _update_quantum_field(self, collapsed_state, observation_point):
        """根据塌缩结果更新量子场"""
        # 波函数根据塌缩结果进行演化
        learning_rate = 0.1
        
        # 向塌缩方向演化
        self.wave_function = (1 - learning_rate) * self.wave_function + learning_rate * collapsed_state
        
        # 归一化
        self.wave_function = self.wave_function / np.linalg.norm(self.wave_function)
        
        # 记录叠加态历史
        self.superposition_states.append(collapsed_state.copy())
        if len(self.superposition_states) > 100:  # 保持最近100个状态
            self.superposition_states.pop(0)
    
    def create_quantum_superposition(self, num_states=5):
        """创建量子叠加态 - 同时探索多个可能性"""
        superposed_melodies = []
        
        for _ in range(num_states):
            # 在叠加态中随机采样
            if len(self.superposition_states) >= 2:
                # 从历史状态中随机选择并混合
                state1, state2 = random.sample(self.superposition_states, 2)
                mix_ratio = random.random()
                mixed_state = mix_ratio * state1 + (1 - mix_ratio) * state2
            else:
                # 如果历史状态不足，使用当前波函数或者生成随机状态
                if self.wave_function is not None:
                    mixed_state = self.wave_function.copy()
                else:
                    # 如果连波函数都没有，就生成一个随机状态
                    dimensions = 128  # 默认维度
                    mixed_state = np.random.randn(dimensions) + 1j * np.random.randn(dimensions)
                    mixed_state = mixed_state / np.linalg.norm(mixed_state)
            
            # 转换为旋律
            melody, sr = self._quantum_state_to_melody(mixed_state)
            superposed_melodies.append(melody)
        
        return superposed_melodies


# ==================== 神经美学评估器 ====================

class NeuralAestheticEvaluator:
    """基于神经科学的审美评估系统"""
    
    def __init__(self):
        self.aesthetic_model = self._build_aesthetic_model()
        self.emotional_response_map = {}
        self.cognitive_patterns = {}
        
    def _build_aesthetic_model(self):
        """构建审美评估神经网络"""
        class AestheticNet(nn.Module):
            def __init__(self):
                super(AestheticNet, self).__init__()
                self.conv1 = nn.Conv1d(1, 16, kernel_size=5, stride=2)
                self.conv2 = nn.Conv1d(16, 32, kernel_size=5, stride=2)
                self.conv3 = nn.Conv1d(32, 64, kernel_size=5, stride=2)
                self.pool = nn.AdaptiveAvgPool1d(1)
                self.fc1 = nn.Linear(64, 32)
                self.fc2 = nn.Linear(32, 8)  # 8个审美维度
                self.fc3 = nn.Linear(8, 1)   # 总体审美评分
                
            def forward(self, x):
                x = torch.relu(self.conv1(x))
                x = torch.relu(self.conv2(x))
                x = torch.relu(self.conv3(x))
                x = self.pool(x).squeeze(-1)
                x = torch.relu(self.fc1(x))
                aesthetic_dims = torch.sigmoid(self.fc2(x))
                overall_score = torch.sigmoid(self.fc3(aesthetic_dims))
                return overall_score, aesthetic_dims
        
        return AestheticNet()
    
    def evaluate_melody(self, melody_wave, sample_rate):
        """评估旋律的审美价值"""
        # 提取音乐特征
        features = self._extract_aesthetic_features(melody_wave, sample_rate)
        
        # 转换为模型输入
        input_tensor = torch.FloatTensor(features).unsqueeze(0).unsqueeze(0)
        
        # 评估（这里简化实现，实际需要训练好的模型）
        with torch.no_grad():
            # 模拟评估过程
            overall_score = random.uniform(0.3, 0.9)  # 模拟评分
            
            # 审美维度评分（新颖性、复杂性、和谐性、情感强度等）
            aesthetic_dimensions = {
                'novelty': random.uniform(0, 1),
                'complexity': random.uniform(0, 1),
                'harmony': random.uniform(0, 1),
                'emotional_intensity': random.uniform(0, 1),
                'rhythmic_interest': random.uniform(0, 1),
                'memorability': random.uniform(0, 1),
                'surprise': random.uniform(0, 1),
                'coherence': random.uniform(0, 1)
            }
        
        return {
            'overall_score': overall_score,
            'dimensions': aesthetic_dimensions,
            'emotional_response': self._predict_emotional_response(aesthetic_dimensions)
        }
    
    def _extract_aesthetic_features(self, melody_wave, sample_rate):
        """提取审美相关特征"""
        # 简化实现 - 实际需要更复杂的特征工程
        features = []
        
        # 频谱特征
        spectral_centroids = librosa.feature.spectral_centroid(y=melody_wave, sr=sample_rate)[0]
        features.extend([np.mean(spectral_centroids), np.std(spectral_centroids)])
        
        # 节奏特征
        tempo, _ = librosa.beat.beat_track(y=melody_wave, sr=sample_rate)
        features.append(tempo)
        
        # 音高特征
        pitches, magnitudes = librosa.piptrack(y=melody_wave, sr=sample_rate)
        pitch_mean = np.mean(pitches[pitches > 0]) if np.any(pitches > 0) else 0
        features.append(pitch_mean)
        
        # 零交叉率
        zcr = librosa.feature.zero_crossing_rate(melody_wave)[0]
        features.extend([np.mean(zcr), np.std(zcr)])
        
        # 确保特征数量固定（填充或截断）
        target_length = 1000  # 模型期望的输入长度
        if len(features) < target_length:
            features.extend([0] * (target_length - len(features)))
        else:
            features = features[:target_length]
            
        return features
    
    def _predict_emotional_response(self, aesthetic_dimensions):
        """预测情感响应"""
        # 基于审美维度预测可能的情感反应
        emotions = {}
        
        # 新颖性和惊喜度与兴奋相关
        excitement = (aesthetic_dimensions['novelty'] + aesthetic_dimensions['surprise']) / 2
        emotions['excitement'] = excitement
        
        # 和谐性与愉悦相关
        emotions['pleasure'] = aesthetic_dimensions['harmony'] * 0.7 + aesthetic_dimensions['coherence'] * 0.3
        
        # 复杂性与智力兴趣相关
        emotions['intellectual_interest'] = aesthetic_dimensions['complexity'] * 0.6 + aesthetic_dimensions['novelty'] * 0.4
        
        # 情感强度与情感深度相关
        emotions['emotional_depth'] = aesthetic_dimensions['emotional_intensity']
        
        return emotions


# ==================== 元学习创作系统 ====================

class MetaLearningComposer:
    """元学习创作系统 - 学习如何创作"""
    
    def __init__(self):
        self.creation_strategies = []
        self.aesthetic_memory = deque(maxlen=1000)
        self.creative_patterns = {}
        self.innovation_level = 0.5  # 创新程度 (0-1)
        
    def learn_from_creation(self, melody, aesthetic_evaluation, creation_context):
        """从创作过程中学习"""
        # 记录创作经验
        experience = {
            'melody_features': self._extract_creation_features(melody),
            'aesthetic_score': aesthetic_evaluation['overall_score'],
            'aesthetic_dimensions': aesthetic_evaluation['dimensions'],
            'context': creation_context,
            'timestamp': datetime.now()
        }
        
        self.aesthetic_memory.append(experience)
        
        # 更新创作策略
        self._update_creation_strategies(experience)
        
        # 发现创作模式
        self._discover_creative_patterns()
    
    def _extract_creation_features(self, melody):
        """提取创作特征"""
        # 简化实现
        return {
            'length': len(melody),
            'mean_amplitude': np.mean(np.abs(melody)),
            'dynamic_range': np.max(melody) - np.min(melody)
        }
    
    def _update_creation_strategies(self, experience):
        """更新创作策略"""
        # 根据成功的创作经验调整策略
        if experience['aesthetic_score'] > 0.7:  # 高评分创作
            # 强化相关策略
            strategy = {
                'features': experience['melody_features'],
                'dimensions': experience['aesthetic_dimensions'],
                'success_rate': 1.0,
                'usage_count': 1
            }
            
            self.creation_strategies.append(strategy)
            
            # 提高创新程度
            self.innovation_level = min(1.0, self.innovation_level + 0.05)
        
        elif experience['aesthetic_score'] < 0.3:  # 低评分创作
            # 降低创新程度
            self.innovation_level = max(0.1, self.innovation_level - 0.02)
    
    def _discover_creative_patterns(self):
        """发现创作模式"""
        if len(self.aesthetic_memory) < 10:
            return
        
        # 分析成功创作的共同模式
        successful_creations = [exp for exp in self.aesthetic_memory 
                               if exp['aesthetic_score'] > 0.7]
        
        if len(successful_creations) >= 3:
            # 发现模式（简化实现）
            pattern_key = f"pattern_{len(self.creative_patterns)}"
            self.creative_patterns[pattern_key] = {
                'avg_novelty': np.mean([exp['aesthetic_dimensions']['novelty'] 
                                      for exp in successful_creations]),
                'avg_harmony': np.mean([exp['aesthetic_dimensions']['harmony'] 
                                      for exp in successful_creations]),
                'sample_size': len(successful_creations)
            }
    
    def get_creative_guidance(self, current_context):
        """获取创作指导"""
        if not self.creation_strategies:
            return {"advice": "自由探索", "innovation_level": self.innovation_level}
        
        # 基于历史成功经验提供指导
        best_strategy = max(self.creation_strategies, 
                           key=lambda x: x['success_rate'])
        
        guidance = {
            "advice": f"尝试类似成功的模式 (评分: {best_strategy['success_rate']:.2f})",
            "target_novelty": best_strategy['dimensions']['novelty'],
            "target_harmony": best_strategy['dimensions']['harmony'],
            "innovation_level": self.innovation_level
        }
        
        return guidance


# ==================== 意识流界面组件 ====================

class ConsciousnessStreamWidget(QWidget):
    """意识流可视化组件 - 显示AI的创作思维过程"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.thoughts = []
        self.current_thought = ""
        self.thought_intensity = 0
        self.thought_timer = QTimer()
        self.thought_timer.timeout.connect(self.update_thought_stream)
        self.thought_timer.start(100)  # 每100ms更新一次
        
        # 设置样式
        self.setMinimumSize(400, 200)
        self.setStyleSheet("""
            ConsciousnessStreamWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #1a1a2e, stop:0.5 #16213e, stop:1 #0f3460);
                border-radius: 15px;
                border: 2px solid #4cc9f0;
            }
        """)
    
    def add_thought(self, thought, intensity=0.5):
        """添加思维片段"""
        self.thoughts.append((thought, intensity))
        if len(self.thoughts) > 10:  # 保持最近的10个思维
            self.thoughts.pop(0)
    
    def update_thought_stream(self):
        """更新意识流显示"""
        if self.thoughts:
            # 随机选择一个思维片段进行显示
            thought, intensity = random.choice(self.thoughts)
            self.current_thought = thought
            self.thought_intensity = intensity
            self.update()
    
    def paintEvent(self, event):
        """绘制意识流界面"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 绘制背景
        rect = self.rect()
        gradient = QLinearGradient(rect.topLeft(), rect.bottomRight())
        gradient.setColorAt(0, QColor(26, 26, 46))    # #1a1a2e
        gradient.setColorAt(0.5, QColor(22, 33, 62))  # #16213e
        gradient.setColorAt(1, QColor(15, 52, 96))    # #0f3460
        
        painter.fillRect(rect, QBrush(gradient))
        
        # 绘制思维流
        self.draw_thought_stream(painter)
        
        # 绘制当前思维
        self.draw_current_thought(painter)
        
        painter.end()
    
    def draw_thought_stream(self, painter):
        """绘制思维流背景"""
        width, height = self.width(), self.height()
        
        # 绘制流动的粒子（代表潜意识活动）
        painter.setPen(QPen(QColor(76, 201, 240, 100), 1))
        
        for i in range(50):
            x = (width * i / 50 + datetime.now().timestamp() * 20) % width
            y = height * 0.3 + math.sin(datetime.now().timestamp() + i) * height * 0.2
            
            size = 2 + math.sin(datetime.now().timestamp() * 2 + i) * 2
            painter.drawEllipse(int(x), int(y), int(size), int(size))
    
    def draw_current_thought(self, painter):
        """绘制当前思维文本"""
        if not self.current_thought:
            return
        
        # 根据思维强度设置透明度
        alpha = int(100 + 155 * self.thought_intensity)
        text_color = QColor(255, 255, 255, alpha)
        
        painter.setPen(QPen(text_color))
        painter.setFont(QFont("Arial", 10, QFont.Bold))
        
        # 绘制思维文本
        text_rect = self.rect().adjusted(10, 10, -10, -10)
        painter.drawText(text_rect, Qt.AlignCenter | Qt.TextWordWrap, self.current_thought)


# ==================== 量子音乐画布 ====================

class QuantumMusicCanvas(FigureCanvas):
    """量子音乐可视化画布"""
    
    def __init__(self, parent=None, width=8, height=6, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        super().__init__(self.fig)
        self.setParent(parent)
        
        # 设置暗色主题
        plt.style.use('dark_background')
        self.fig.patch.set_facecolor('#0f3460')
        
        self.quantum_state = None
        self.melody_wave = None
        
    def plot_quantum_state(self, quantum_state):
        """绘制量子态可视化"""
        self.fig.clear()
        
        # 创建3D子图
        ax = self.fig.add_subplot(111, projection='3d')
        
        # 提取实部和虚部
        real_part = np.real(quantum_state)
        imag_part = np.imag(quantum_state)
        
        # 创建网格
        x = np.arange(len(quantum_state))
        y = real_part
        z = imag_part
        
        # 绘制量子态轨迹
        ax.plot(x, y, z, 'o-', color='#4cc9f0', linewidth=2, markersize=4)
        
        # 设置标签
        ax.set_xlabel('量子维度', color='white')
        ax.set_ylabel('实部', color='white')
        ax.set_zlabel('虚部', color='white')
        
        # 设置颜色
        ax.xaxis.pane.fill = False
        ax.yaxis.pane.fill = False
        ax.zaxis.pane.fill = False
        ax.xaxis.pane.set_edgecolor('white')
        ax.yaxis.pane.set_edgecolor('white')
        ax.zaxis.pane.set_edgecolor('white')
        
        ax.set_title('量子音乐态可视化', color='white', fontsize=14)
        
        self.fig.tight_layout()
        self.draw()
    
    def plot_melody_evolution(self, melody_wave, sample_rate):
        """绘制旋律演化图"""
        self.fig.clear()
        
        # 创建子图网格
        gs = gridspec.GridSpec(2, 2, width_ratios=[3, 1], height_ratios=[1, 1])
        
        # 波形图
        ax1 = self.fig.add_subplot(gs[0, 0])
        times = np.linspace(0, len(melody_wave)/sample_rate, len(melody_wave))
        ax1.plot(times, melody_wave, color='#4cc9f0', linewidth=1)
        ax1.set_title('旋律波形', color='white')
        ax1.set_ylabel('振幅', color='white')
        ax1.grid(True, alpha=0.3)
        
        # 频谱图
        ax2 = self.fig.add_subplot(gs[1, 0])
        D = librosa.amplitude_to_db(np.abs(librosa.stft(melody_wave)), ref=np.max)
        img = librosa.display.specshow(D, y_axis='log', x_axis='time', 
                                      sr=sample_rate, ax=ax2, cmap='magma')
        ax2.set_title('频谱图', color='white')
        ax2.set_ylabel('频率 (Hz)', color='white')
        ax2.set_xlabel('时间 (s)', color='white')
        self.fig.colorbar(img, ax=ax2)
        
        # 特征雷达图
        ax3 = self.fig.add_subplot(gs[:, 1], polar=True)
        
        # 提取特征值（简化）
        features = ['新颖性', '复杂性', '和谐性', '情感强度', '节奏兴趣']
        values = [0.7, 0.5, 0.8, 0.6, 0.4]  # 示例值
        
        # 完成雷达图
        angles = np.linspace(0, 2*np.pi, len(features), endpoint=False).tolist()
        values += values[:1]  # 闭合图形
        angles += angles[:1]
        
        ax3.plot(angles, values, 'o-', linewidth=2, color='#f72585')
        ax3.fill(angles, values, alpha=0.25, color='#f72585')
        ax3.set_xticks(angles[:-1])
        ax3.set_xticklabels(features, color='white')
        ax3.set_title('音乐特征雷达图', color='white', pad=20)
        
        self.fig.tight_layout()
        self.draw()


# ==================== 主应用程序 ====================

class QuantumMusicExplorer(QMainWindow):
    """量子音乐探索系统主界面"""
    
    def __init__(self):
        super().__init__()
        
        # 初始化核心组件
        self.quantum_generator = QuantumMusicGenerator()
        self.aesthetic_evaluator = NeuralAestheticEvaluator()
        self.meta_composer = MetaLearningComposer()
        
        # 音频播放
        pygame.mixer.init()
        self.current_melody = None
        self.current_sample_rate = 22050
        
        # 创作状态
        self.creation_history = []
        self.current_creation_context = {}
        
        self.init_ui()
        self.setup_connections()
        
        # 初始化量子场
        self.quantum_generator.initialize_quantum_field()
        
    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("量子音乐自探索系统 - 无中生有的旋律创造")
        self.setGeometry(100, 50, 1600, 1000)
        
        # 设置应用程序样式
        self.setStyleSheet("""
            QMainWindow {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #0f3460, stop:0.5 #16213e, stop:1 #1a1a2e);
                color: white;
            }
            QTabWidget::pane {
                border: 2px solid #4cc9f0;
                border-radius: 10px;
                background: rgba(26, 26, 46, 200);
            }
            QTabBar::tab {
                background: #16213e;
                color: white;
                padding: 8px 15px;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
            }
            QTabBar::tab:selected {
                background: #4cc9f0;
                color: #1a1a2e;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #4cc9f0;
                border-radius: 8px;
                margin-top: 1ex;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 10px;
                background: #4cc9f0;
                color: #1a1a2e;
                border-radius: 4px;
            }
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #4cc9f0, stop:1 #3a8fb7);
                border: 1px solid #2a6f97;
                border-radius: 5px;
                color: white;
                padding: 8px 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #5cd9ff, stop:1 #4a9fc7);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #3ab9e0, stop:1 #2a7fa7);
            }
        """)
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        main_layout = QVBoxLayout(central_widget)
        
        # 创建意识流显示
        self.consciousness_stream = ConsciousnessStreamWidget()
        main_layout.addWidget(self.consciousness_stream)
        
        # 创建标签页
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        # 创建各个标签页
        self.create_quantum_exploration_tab()
        self.create_aesthetic_evaluation_tab()
        self.create_meta_learning_tab()
        self.create_composition_lab_tab()
        
        # 创建状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("量子音乐场已初始化 - 准备进行无中生有的创造")
        
        # 添加思维片段
        self.consciousness_stream.add_thought("量子场初始化完成...", 0.3)
        self.consciousness_stream.add_thought("寻找创造性的初始状态...", 0.5)
        self.consciousness_stream.add_thought("准备进行波函数塌缩...", 0.7)
        
    def create_quantum_exploration_tab(self):
        """创建量子探索标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 量子控制区域
        quantum_control_group = QGroupBox("量子场控制")
        quantum_layout = QHBoxLayout(quantum_control_group)
        
        self.collapse_btn = QPushButton("量子塌缩创造")
        self.collapse_btn.setStyleSheet("font-size: 14px; padding: 10px;")
        
        self.superposition_btn = QPushButton("叠加态探索")
        self.entanglement_btn = QPushButton("纠缠网络可视化")
        
        quantum_layout.addWidget(self.collapse_btn)
        quantum_layout.addWidget(self.superposition_btn)
        quantum_layout.addWidget(self.entanglement_btn)
        
        # 观察者控制
        observer_group = QGroupBox("观察者效应控制")
        observer_layout = QFormLayout(observer_group)
        
        self.observer_effect_slider = QSlider(Qt.Horizontal)
        self.observer_effect_slider.setRange(1, 100)
        self.observer_effect_slider.setValue(10)
        
        self.quantum_dimension_spin = QSpinBox()
        self.quantum_dimension_spin.setRange(64, 512)
        self.quantum_dimension_spin.setValue(128)
        
        observer_layout.addRow("观察者效应强度:", self.observer_effect_slider)
        observer_layout.addRow("量子维度:", self.quantum_dimension_spin)
        
        # 量子可视化
        self.quantum_canvas = QuantumMusicCanvas(self, width=10, height=8)
        
        # 添加到布局
        layout.addWidget(quantum_control_group)
        layout.addWidget(observer_group)
        layout.addWidget(self.quantum_canvas)
        
        self.tab_widget.addTab(tab, "量子探索")
        
    def create_aesthetic_evaluation_tab(self):
        """创建审美评估标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 评估控制
        eval_control_group = QGroupBox("审美评估")
        eval_layout = QHBoxLayout(eval_control_group)
        
        self.evaluate_btn = QPushButton("评估当前旋律")
        self.emotional_analysis_btn = QPushButton("情感分析")
        self.comparative_analysis_btn = QPushButton("对比分析")
        
        eval_layout.addWidget(self.evaluate_btn)
        eval_layout.addWidget(self.emotional_analysis_btn)
        eval_layout.addWidget(self.comparative_analysis_btn)
        
        # 评估结果显示
        eval_result_group = QGroupBox("评估结果")
        eval_result_layout = QVBoxLayout(eval_result_group)
        
        self.evaluation_text = QTextEdit()
        self.evaluation_text.setReadOnly(True)
        
        eval_result_layout.addWidget(self.evaluation_text)
        
        layout.addWidget(eval_control_group)
        layout.addWidget(eval_result_group)
        
        self.tab_widget.addTab(tab, "审美评估")
        
    def create_meta_learning_tab(self):
        """创建元学习标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 学习控制
        learning_control_group = QGroupBox("元学习控制")
        learning_layout = QHBoxLayout(learning_control_group)
        
        self.learn_btn = QPushButton("从当前创作学习")
        self.pattern_analysis_btn = QPushButton("分析创作模式")
        self.strategy_optimize_btn = QPushButton("优化创作策略")
        
        learning_layout.addWidget(self.learn_btn)
        learning_layout.addWidget(self.pattern_analysis_btn)
        learning_layout.addWidget(self.strategy_optimize_btn)
        
        # 学习结果显示
        learning_result_group = QGroupBox("学习成果")
        learning_result_layout = QVBoxLayout(learning_result_group)
        
        self.learning_text = QTextEdit()
        self.learning_text.setReadOnly(True)
        
        learning_result_layout.addWidget(self.learning_text)
        
        layout.addWidget(learning_control_group)
        layout.addWidget(learning_result_group)
        
        self.tab_widget.addTab(tab, "元学习")
        
    def create_composition_lab_tab(self):
        """创作实验室标签页"""
        tab = QWidget()
        layout = QHBoxLayout(tab)
        
        # 左侧：创作控制
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        # 音频控制
        audio_control_group = QGroupBox("音频控制")
        audio_layout = QVBoxLayout(audio_control_group)
        
        self.play_btn = QPushButton("播放旋律")
        self.stop_btn = QPushButton("停止播放")
        self.save_btn = QPushButton("保存旋律")
        
        audio_layout.addWidget(self.play_btn)
        audio_layout.addWidget(self.stop_btn)
        audio_layout.addWidget(self.save_btn)
        
        # 创作参数
        composition_group = QGroupBox("创作参数")
        composition_layout = QFormLayout(composition_group)
        
        self.innovation_slider = QSlider(Qt.Horizontal)
        self.innovation_slider.setRange(0, 100)
        self.innovation_slider.setValue(50)
        
        self.complexity_slider = QSlider(Qt.Horizontal)
        self.complexity_slider.setRange(0, 100)
        self.complexity_slider.setValue(50)
        
        composition_layout.addRow("创新程度:", self.innovation_slider)
        composition_layout.addRow("复杂度:", self.complexity_slider)
        
        left_layout.addWidget(audio_control_group)
        left_layout.addWidget(composition_group)
        left_layout.addStretch()
        
        # 右侧：旋律可视化
        self.melody_canvas = QuantumMusicCanvas(self, width=10, height=8)
        
        layout.addWidget(left_widget)
        layout.addWidget(self.melody_canvas)
        
        self.tab_widget.addTab(tab, "创作实验室")
        
    def setup_connections(self):
        """设置信号连接"""
        # 量子探索
        self.collapse_btn.clicked.connect(self.quantum_collapse_creation)
        self.superposition_btn.clicked.connect(self.explore_superposition)
        
        # 审美评估
        self.evaluate_btn.clicked.connect(self.evaluate_current_melody)
        
        # 元学习
        self.learn_btn.clicked.connect(self.learn_from_creation)
        
        # 音频控制
        self.play_btn.clicked.connect(self.play_melody)
        self.stop_btn.clicked.connect(self.stop_playback)
        self.save_btn.clicked.connect(self.save_melody)
        
        # 参数变化
        self.observer_effect_slider.valueChanged.connect(self.update_observer_effect)
        
    def quantum_collapse_creation(self):
        """量子塌缩创造旋律"""
        self.status_bar.showMessage("正在进行量子塌缩...")
        
        # 更新观察者效应
        self.update_observer_effect()
        
        # 添加思维片段
        self.consciousness_stream.add_thought("应用观察者效应...", 0.6)
        self.consciousness_stream.add_thought("波函数开始塌缩...", 0.8)
        
        # 执行量子塌缩
        melody_wave, sample_rate = self.quantum_generator.quantum_collapse_to_melody()
        
        if melody_wave is not None:
            self.current_melody = melody_wave
            self.current_sample_rate = sample_rate
            
            # 更新可视化
            self.melody_canvas.plot_melody_evolution(melody_wave, sample_rate)
            
            # 添加思维片段
            self.consciousness_stream.add_thought("旋律创造成功!", 0.9)
            self.consciousness_stream.add_thought("准备进行审美评估...", 0.5)
            
            self.status_bar.showMessage("量子塌缩完成 - 新旋律已生成")
            
            # 记录创作上下文
            self.current_creation_context = {
                'method': 'quantum_collapse',
                'timestamp': datetime.now(),
                'observer_effect': self.quantum_generator.observer_effect
            }
        else:
            self.status_bar.showMessage("量子塌缩失败")
    
    def explore_superposition(self):
        """探索量子叠加态"""
        self.status_bar.showMessage("探索量子叠加态...")
        
        # 添加思维片段
        self.consciousness_stream.add_thought("进入叠加态探索...", 0.7)
        
        # 生成多个叠加态旋律
        superposed_melodies = self.quantum_generator.create_quantum_superposition(3)
        
        if superposed_melodies:
            # 选择第一个旋律作为当前旋律
            self.current_melody = superposed_melodies[0]
            
            # 更新可视化
            self.melody_canvas.plot_melody_evolution(self.current_melody, 
                                                   self.current_sample_rate)
            
            self.status_bar.showMessage(f"叠加态探索完成 - 生成{len(superposed_melodies)}个变体")
            
            # 记录创作上下文
            self.current_creation_context = {
                'method': 'superposition_exploration',
                'timestamp': datetime.now(),
                'variants_generated': len(superposed_melodies)
            }
    
    def evaluate_current_melody(self):
        """评估当前旋律"""
        if self.current_melody is None:
            QMessageBox.warning(self, "警告", "请先生成旋律")
            return
            
        self.status_bar.showMessage("正在进行审美评估...")
        
        # 添加思维片段
        self.consciousness_stream.add_thought("启动神经网络审美评估...", 0.6)
        
        # 执行评估
        evaluation = self.aesthetic_evaluator.evaluate_melody(
            self.current_melody, self.current_sample_rate)
        
        # 显示评估结果
        result_text = "=== 审美评估结果 ===\n\n"
        result_text += f"总体评分: {evaluation['overall_score']:.3f}\n\n"
        
        result_text += "维度分析:\n"
        for dim, score in evaluation['dimensions'].items():
            result_text += f"  {dim}: {score:.3f}\n"
        
        result_text += "\n情感响应预测:\n"
        for emotion, intensity in evaluation['emotional_response'].items():
            result_text += f"  {emotion}: {intensity:.3f}\n"
        
        self.evaluation_text.setText(result_text)
        
        # 添加思维片段
        self.consciousness_stream.add_thought(f"评估完成 - 评分: {evaluation['overall_score']:.3f}", 
                                            evaluation['overall_score'])
        
        self.status_bar.showMessage("审美评估完成")
        
        # 保存评估结果到创作上下文
        self.current_creation_context['aesthetic_evaluation'] = evaluation
    
    def learn_from_creation(self):
        """从当前创作学习"""
        if self.current_melody is None or 'aesthetic_evaluation' not in self.current_creation_context:
            QMessageBox.warning(self, "警告", "请先生成并评估旋律")
            return
            
        self.status_bar.showMessage("正在进行元学习...")
        
        # 添加思维片段
        self.consciousness_stream.add_thought("开始元学习过程...", 0.7)
        
        # 执行学习
        self.meta_composer.learn_from_creation(
            self.current_melody,
            self.current_creation_context['aesthetic_evaluation'],
            self.current_creation_context
        )
        
        # 显示学习成果
        learning_text = "=== 元学习成果 ===\n\n"
        learning_text += f"创作策略数量: {len(self.meta_composer.creation_strategies)}\n"
        learning_text += f"发现的模式数量: {len(self.meta_composer.creative_patterns)}\n"
        learning_text += f"当前创新程度: {self.meta_composer.innovation_level:.3f}\n\n"
        
        # 获取创作指导
        guidance = self.meta_composer.get_creative_guidance(self.current_creation_context)
        learning_text += "创作指导:\n"
        for key, value in guidance.items():
            learning_text += f"  {key}: {value}\n"
        
        self.learning_text.setText(learning_text)
        
        # 添加思维片段
        self.consciousness_stream.add_thought("元学习完成 - 创作策略已更新", 0.8)
        
        self.status_bar.showMessage("元学习完成")
        
        # 记录到创作历史
        self.creation_history.append({
            'melody': self.current_melody.copy() if hasattr(self.current_melody, 'copy') else self.current_melody,
            'context': self.current_creation_context.copy(),
            'timestamp': datetime.now()
        })
    
    def play_melody(self):
        """播放当前旋律"""
        if self.current_melody is None:
            QMessageBox.warning(self, "警告", "请先生成旋律")
            return
            
        try:
            # 临时保存为WAV文件并播放
            temp_file = "temp_melody.wav"
            sf.write(temp_file, self.current_melody, self.current_sample_rate)
            
            pygame.mixer.music.load(temp_file)
            pygame.mixer.music.play()
            
            self.status_bar.showMessage("正在播放旋律...")
            
            # 添加思维片段
            self.consciousness_stream.add_thought("播放生成的旋律...", 0.4)
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"播放失败: {str(e)}")
    
    def stop_playback(self):
        """停止播放"""
        pygame.mixer.music.stop()
        self.status_bar.showMessage("播放已停止")
        
        # 添加思维片段
        self.consciousness_stream.add_thought("播放停止", 0.2)
    
    def save_melody(self):
        """保存旋律"""
        if self.current_melody is None:
            QMessageBox.warning(self, "警告", "请先生成旋律")
            return
            
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存旋律", "", "WAV文件 (*.wav)"
        )
        
        if file_path:
            try:
                sf.write(file_path, self.current_melody, self.current_sample_rate)
                QMessageBox.information(self, "成功", "旋律保存成功")
                
                # 添加思维片段
                self.consciousness_stream.add_thought("旋律已保存", 0.3)
                
            except Exception as e:
                QMessageBox.critical(self, "错误", f"保存失败: {str(e)}")
    
    def update_observer_effect(self):
        """更新观察者效应强度"""
        effect_value = self.observer_effect_slider.value() / 100.0
        self.quantum_generator.observer_effect = effect_value
        
        # 添加思维片段
        self.consciousness_stream.add_thought(f"观察者效应调整为: {effect_value:.2f}", 0.4)


def main():
    """主函数"""
    app = QApplication(sys.argv)
    
    # 设置应用程序属性
    app.setApplicationName("量子音乐自探索系统")
    app.setApplicationVersion("1.0.0")
    
    # 创建并显示主窗口
    window = QuantumMusicExplorer()
    window.show()
    
    # 运行应用程序
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()