import sys
import os
import random
import time
import numpy as np
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QPushButton, QComboBox, QProgressBar, QTabWidget, QListWidget, 
                            QGroupBox, QFileDialog, QMessageBox, QSplitter, QFrame, QInputDialog,
                            QCheckBox, QSlider, QDoubleSpinBox, QSizePolicy)
from PyQt5.QtCore import QTimer, Qt, QThread, pyqtSignal, QElapsedTimer
from PyQt5.QtGui import QFont, QColor, QPalette, QImage, QPixmap
import pyqtgraph as pg
import pyqtgraph.opengl as gl
from pyqtgraph import PlotWidget
import pyttsx3
import sounddevice as sd
from scipy.fft import rfft, rfftfreq
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import tensorflow as tf
from tensorflow.keras.models import Sequential, load_model
from tensorflow.keras.layers import Dense, Dropout, LSTM, Conv1D, MaxPooling1D, Flatten
from tensorflow.keras.optimizers import Adam
import matplotlib.pyplot as plt
import matplotlib.cm as cm
from mpl_toolkits.mplot3d import Axes3D  # 用于3D脑图
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from io import BytesIO
import threading
from queue import Queue
# 设置随机种子以确保可复现性
np.random.seed(42)
tf.random.set_seed(42)

# 配置GPU加速
gpus = tf.config.experimental.list_physical_devices('GPU')
if gpus:
    try:
        for gpu in gpus:
            tf.config.experimental.set_memory_growth(gpu, True)
    except RuntimeError as e:
        print(e)

class BrainWaveGenerator(QThread):
    """高性能脑波数据生成器"""
    data_updated = pyqtSignal(np.ndarray, float, float)
    prediction_progress = pyqtSignal(int)
    
    def __init__(self):
        super().__init__()
        self.is_running = True
        self.prediction_active = False
        self.prediction_stage = 0
        self.eeg_data = np.zeros(1000, dtype=np.float32)
        self.attention = 0.5
        self.meditation = 0.3
        self.t = 0.0
        self.sample_rate = 256  # Hz
        
    def run(self):
        """生成模拟脑波数据"""
        timer = QElapsedTimer()
        timer.start()
        
        while self.is_running:
            # 计算时间增量
            dt = timer.restart() / 1000.0  # 转换为秒
            
            # 基础脑波信号 - 包含不同频率成分
            alpha = 0.5 * np.sin(2 * np.pi * 10 * self.t)  # Alpha波 (8-12 Hz)
            beta = 0.3 * np.sin(2 * np.pi * 20 * self.t)   # Beta波 (12-30 Hz)
            theta = 0.2 * np.sin(2 * np.pi * 6 * self.t)   # Theta波 (4-8 Hz)
            delta = 0.1 * np.sin(2 * np.pi * 2 * self.t)   # Delta波 (0.5-4 Hz)
            
            # 添加注意力/冥想影响
            attention_mod = self.attention * 0.5 * np.sin(2 * np.pi * 15 * self.t)
            meditation_mod = self.meditation * 0.3 * np.sin(2 * np.pi * 8 * self.t)
            
            # 添加噪声
            noise = 0.1 * np.random.randn()
            
            # 组合信号
            new_sample = alpha + beta + theta + delta + attention_mod + meditation_mod + noise
            
            # 在预测阶段添加特定模式
            if self.prediction_active and self.prediction_stage > 0:
                new_sample += 0.4 * np.sin(2 * np.pi * self.prediction_stage * self.t)
            
            # 更新数据缓冲区
            self.eeg_data = np.roll(self.eeg_data, -1)
            self.eeg_data[-1] = new_sample
            
            # 更新注意力和冥想水平
            self.attention = min(1.0, max(0.1, self.attention + 0.01 * (random.random() - 0.48)))
            self.meditation = min(1.0, max(0.1, self.meditation + 0.01 * (random.random() - 0.45)))
            
            # 发出更新信号
            self.data_updated.emit(self.eeg_data, self.attention, self.meditation)
            
            # 更新预测进度
            if self.prediction_active:
                self.prediction_progress.emit(self.prediction_stage)
            
            self.t += dt
            time.sleep(0.001)  # 降低CPU占用
    
    def start_prediction(self):
        """开始预测过程"""
        self.prediction_active = True
        self.prediction_stage = 0
        
    def update_prediction_stage(self):
        """更新预测阶段"""
        if self.prediction_active and self.prediction_stage < 5:
            self.prediction_stage += 1
    
    def stop_prediction(self):
        """停止预测过程"""
        self.prediction_active = False
        self.prediction_stage = 0

class NeuroMindModel:
    """高性能深度学习模型"""
    def __init__(self):
        self.model = None
        self.scaler = StandardScaler()
        self.classes = ["Apple", "Banana", "Car", "Tree", "Star", "House", "Cat", "Dog"]
        self.history = None
        self.model_type = "LSTM"  # 默认模型类型
    
    def build_model(self, input_shape, num_classes):
        """构建神经网络模型"""
        if self.model_type == "LSTM":
            self.model = Sequential([
                LSTM(128, input_shape=input_shape, return_sequences=True),
                Dropout(0.3),
                LSTM(64),
                Dropout(0.3),
                Dense(64, activation='relu'),
                Dense(num_classes, activation='softmax')
            ])
        elif self.model_type == "CNN":
            self.model = Sequential([
                Conv1D(64, kernel_size=5, activation='relu', input_shape=input_shape),
                MaxPooling1D(pool_size=2),
                Conv1D(128, kernel_size=3, activation='relu'),
                MaxPooling1D(pool_size=2),
                Flatten(),
                Dense(128, activation='relu'),
                Dropout(0.3),
                Dense(num_classes, activation='softmax')
            ])
        elif self.model_type == "Hybrid":
            self.model = Sequential([
                Conv1D(64, kernel_size=5, activation='relu', input_shape=input_shape),
                MaxPooling1D(pool_size=2),
                LSTM(128, return_sequences=True),
                LSTM(64),
                Dense(64, activation='relu'),
                Dropout(0.3),
                Dense(num_classes, activation='softmax')
            ])
        
        self.model.compile(
            loss='sparse_categorical_crossentropy',
            optimizer=Adam(learning_rate=0.001),
            metrics=['accuracy']
        )
    
    def train(self, X, y, epochs=30, batch_size=32, progress_callback=None):
        """训练模型"""
        self.training_in_progress = True
        self.training_progress = 0
        
        # 划分训练集和验证集
        X_train, X_val, y_train, y_val = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        
        # 展平数据用于标准化
        if X_train.ndim == 3:
            X_train = X_train.reshape(X_train.shape[0], -1)
            X_val = X_val.reshape(X_val.shape[0], -1)
        
        # 数据标准化
        self.training_message = "Standardizing data..."
        if progress_callback:
            progress_callback(5, self.training_message)
            
        X_train = self.scaler.fit_transform(X_train)
        X_val = self.scaler.transform(X_val)
        
        # 恢复LSTM需要的3D形状
        X_train = X_train.reshape(-1, 128, 1)
        X_val = X_val.reshape(-1, 128, 1)
        
        # 训练模型
        self.training_message = "Training model..."
        if progress_callback:
            progress_callback(10, self.training_message)
            
        # 自定义回调函数用于更新进度
        class TrainingCallback(tf.keras.callbacks.Callback):
            def __init__(self, total_epochs, progress_callback):
                self.total_epochs = total_epochs
                self.progress_callback = progress_callback
                
            def on_epoch_end(self, epoch, logs=None):
                progress = 10 + int((epoch + 1) / self.total_epochs * 90)
                message = f"Epoch {epoch+1}/{self.total_epochs} - acc: {logs['accuracy']:.2f}, val_acc: {logs['val_accuracy']:.2f}"
                if self.progress_callback:
                    self.progress_callback(progress, message)
        
        self.history = self.model.fit(
            X_train, y_train,
            validation_data=(X_val, y_val),
            epochs=epochs,
            batch_size=batch_size,
            verbose=0,
            callbacks=[TrainingCallback(epochs, progress_callback)]
        )
        
        self.training_in_progress = False
        return self.history
    
    def predict(self, X):
        """进行预测"""
        orig_shape = X.shape
        if X.ndim == 3:
            X = X.reshape(X.shape[0], -1)  # 展平为 (样本数, 128)
        
        X_scaled = self.scaler.transform(X)
        X_scaled = X_scaled.reshape(orig_shape)  # 恢复原始形状
        
        predictions = self.model.predict(X_scaled, verbose=0)
        return np.argmax(predictions, axis=1), np.max(predictions, axis=1)
    
    def generate_simulated_data(self, num_samples=1000, seq_length=128):
        """生成模拟脑波数据"""
        X = np.zeros((num_samples, seq_length), dtype=np.float32)
        y = np.zeros(num_samples, dtype=np.int32)
        
        for i in range(num_samples):
            # 为每个类别生成特定模式的数据
            class_idx = np.random.randint(0, len(self.classes))
            base_freq = 10 + class_idx * 2
            
            # 生成时间序列
            t = np.linspace(0, 1, seq_length)
            
            # 基础信号
            signal = np.sin(2 * np.pi * base_freq * t)
            
            # 添加类别特有模式
            if class_idx == 0:  # Apple
                signal += 0.3 * np.sin(2 * np.pi * 15 * t)
            elif class_idx == 1:  # Banana
                signal += 0.2 * np.sin(2 * np.pi * 8 * t)
            elif class_idx == 2:  # Car
                signal += 0.4 * np.cos(2 * np.pi * 12 * t)
            elif class_idx == 3:  # Tree
                signal += 0.3 * np.sin(2 * np.pi * 6 * t)
            elif class_idx == 4:  # Star
                signal += 0.5 * np.cos(2 * np.pi * 20 * t)
            elif class_idx == 5:  # House
                signal += 0.2 * np.sin(2 * np.pi * 4 * t) + 0.2 * np.cos(2 * np.pi * 10 * t)
            elif class_idx == 6:  # Cat
                signal += 0.3 * np.sin(2 * np.pi * 25 * t)
            elif class_idx == 7:  # Dog
                signal += 0.4 * np.cos(2 * np.pi * 18 * t)
            
            # 添加噪声
            signal += 0.1 * np.random.randn(seq_length)
            
            X[i] = signal
            y[i] = class_idx
        
        return X, y
    
    def save_model(self, filename):
        """保存模型"""
        self.model.save(filename)
        np.save(filename.replace('.h5', '_scaler.npy'), self.scaler.scale_)
        np.save(filename.replace('.h5', '_mean.npy'), self.scaler.mean_)
    
    def load_model(self, filename):
        """加载模型"""
        self.model = load_model(filename)
        scale = np.load(filename.replace('.h5', '_scaler.npy'))
        mean = np.load(filename.replace('.h5', '_mean.npy'))
        self.scaler.scale_ = scale
        self.scaler.mean_ = mean
        return True

class MindReadingApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NeuroMind Pro+ - Advanced Brain-Computer Interface")
        self.setGeometry(100, 50, 1600, 1000)
        self.setStyleSheet(self.load_stylesheet())
        self.training_thread = None
        self.training_queue = Queue()
        
        # 初始化模型和脑波生成器
        self.model = NeuroMindModel()
        self.brainwave_generator = BrainWaveGenerator()
        self.brainwave_generator.data_updated.connect(self.update_ui)
        self.brainwave_generator.prediction_progress.connect(self.update_prediction_progress)
        
        # 初始化语音引擎
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', 150)
        self.engine.setProperty('volume', 0.9)
        
        # 初始化UI
        self.init_ui()
        self.electrodes = []
        
        # 初始化数据
        self.predictions = []
        self.accuracy_history = []
        self.user_history = []
        self.current_user = "Default"
        self.model_loaded = False
        
        # 启动脑波生成线程
        self.brainwave_generator.start()
        
        # 加载默认模型
        self.load_default_model()
        self.last_spectrum_time = 0
        self.last_spectrum_time = 0
        self.last_3d_update = 0
        self.last_topo_update = 0
        self.update_intervals = {
            'eeg': 0.03,    # 约30fps
            'spectrum': 0.1, # 10fps
            '3d': 0.2,       # 5fps
            'topo': 0.5      # 2fps
        }
        self.training_progress_timer = QTimer(self)
        self.training_progress_timer.timeout.connect(self.update_training_progress)
        self.training_progress_timer.setInterval(200)  # 每200ms更新一次
        
    def update_training_progress(self):
        """更新训练进度"""
        while not self.training_queue.empty():
            progress, message = self.training_queue.get()
            self.status_bar.showMessage(message)
            
            # 如果训练完成
            if progress >= 100:
                self.training_progress_timer.stop()
                history = self.model.history
                train_acc = history.history['accuracy'][-1] * 100
                val_acc = history.history['val_accuracy'][-1] * 100
                
                self.model_loaded = True
                self.status_bar.showMessage(f"训练完成! 训练准确率: {train_acc:.1f}%, 验证准确率: {val_acc:.1f}%")
                self.train_btn.setEnabled(True)
                
                # 语音提示
                self.speak(f"模型训练完成。训练准确率: {int(train_acc)}%, 验证准确率: {int(val_acc)}%")
        
    # 优化3D脑图绘制
    def create_brain_model(self, static=False):
        """创建3D脑模型"""
        if static:
            # 只创建一次静态脑模型
            u = np.linspace(0, 2 * np.pi, 20)
            v = np.linspace(0, np.pi, 20)
            self.brain_x = np.outer(np.cos(u), np.sin(v))
            self.brain_y = np.outer(np.sin(u), np.sin(v))
            self.brain_z = np.outer(np.ones(np.size(u)), np.cos(v))
            
            # 电极点
            self.electrodes = []
            for i in range(8):
                theta = i * np.pi / 4
                phi = np.pi / 3 + (i % 2) * np.pi / 6
                x = np.sin(phi) * np.cos(theta)
                y = np.sin(phi) * np.sin(theta)
                z = np.cos(phi)
                self.electrodes.append([x, y, z])
            
            # 初始绘制
            self.brain3d_ax.plot_surface(self.brain_x, self.brain_y, self.brain_z, 
                                        color='#3949ab', alpha=0.3)
            self.electrode_scatter = self.brain3d_ax.scatter(
                [p[0] for p in self.electrodes],
                [p[1] for p in self.electrodes],
                [p[2] for p in self.electrodes],
                s=80, c='#ff7043'
            )
            self.brain3d_canvas.draw()
            
    def load_default_model(self):
        """加载默认模型"""
        try:
            self.model.model_type = "LSTM"
            self.model.build_model(input_shape=(128, 1), num_classes=len(self.model.classes))
            X, y = self.model.generate_simulated_data(num_samples=100, seq_length=128)
            self.model.train(X, y, epochs=5)
            self.model_loaded = True
            self.status_bar.showMessage("Default model loaded and ready")
        except Exception as e:
            self.status_bar.showMessage(f"Error loading default model: {str(e)}")
    
    def load_stylesheet(self):
        """加载应用程序样式表"""
        return """
            QMainWindow {
                background-color: #1a1a2e;
                color: #e0e0e0;
            }
            QWidget {
                background-color: #2a2a3e;
                color: #e0e0e0;
                border: none;
                font-family: 'Segoe UI';
            }
            QPushButton {
                background-color: #4e54c8;
                color: white;
                border: none;
                padding: 8px 12px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #6a6fc8;
            }
            QPushButton:pressed {
                background-color: #3a3f9e;
            }
            QPushButton:disabled {
                background-color: #454f6e;
                color: #a0a0a0;
            }
            QLabel {
                color: #e0e0e0;
            }
            QProgressBar {
                border: 1px solid #5c6bc0;
                border-radius: 3px;
                text-align: center;
                height: 20px;
            }
            QProgressBar::chunk {
                background-color: #4e54c8;
                border-radius: 2px;
            }
            QComboBox, QLineEdit, QListWidget {
                background-color: #3a3a52;
                color: #e0e0e0;
                border: 1px solid #5c6bc0;
                border-radius: 3px;
                padding: 5px;
                selection-background-color: #4e54c8;
            }
            QTabWidget::pane {
                border: 1px solid #5c6bc0;
                background: #2a2a3e;
                margin-top: 5px;
            }
            QTabBar::tab {
                background: #2a2a3e;
                color: #e0e0e0;
                padding: 8px 20px;
                border: 1px solid #5c6bc0;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background: #4e54c8;
            }
            QGroupBox {
                border: 1px solid #5c6bc0;
                border-radius: 5px;
                margin-top: 1ex;
                font-weight: bold;
                font-size: 12px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 5px;
                color: #8f9dff;
            }
            QSlider::groove:horizontal {
                background: #3a3a52;
                height: 8px;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #4e54c8;
                border: 1px solid #3a3a52;
                width: 16px;
                height: 16px;
                border-radius: 8px;
                margin: -4px 0;
            }
            QSlider::sub-page:horizontal {
                background: #6a6fc8;
                border-radius: 4px;
            }
            QCheckBox {
                spacing: 5px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 1px solid #5c6bc0;
                border-radius: 3px;
            }
            QCheckBox::indicator:checked {
                background-color: #4e54c8;
            }
            QDoubleSpinBox {
                background-color: #3a3a52;
                color: #e0e0e0;
                border: 1px solid #5c6bc0;
                border-radius: 3px;
                padding: 3px;
            }
        """
    
    def init_ui(self):
        """初始化用户界面"""
        # 创建主窗口部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # 左侧控制面板
        control_panel = QFrame()
        control_panel.setMaximumWidth(400)
        control_layout = QVBoxLayout(control_panel)
        control_layout.setSpacing(15)
        
        # 系统状态组
        status_group = QGroupBox("System Status")
        status_layout = QVBoxLayout()
        
        self.status_label = QLabel("Initializing...")
        self.status_label.setFont(QFont("Arial", 10))
        
        self.cpu_label = QLabel("CPU Usage: 0%")
        self.memory_label = QLabel("Memory Usage: 0 MB")
        self.gpu_label = QLabel("GPU: Not detected")
        
        status_layout.addWidget(self.status_label)
        status_layout.addWidget(self.cpu_label)
        status_layout.addWidget(self.memory_label)
        status_layout.addWidget(self.gpu_label)
        status_group.setLayout(status_layout)
        
        # 脑波控制组
        control_group = QGroupBox("Brainwave Control")
        control_group_layout = QVBoxLayout()
        
        self.thought_combo = QComboBox()
        self.thought_combo.addItems(self.model.classes)
        
        self.attention_bar = QProgressBar()
        self.attention_bar.setRange(0, 100)
        self.attention_bar.setFormat("Attention: %p%")
        self.attention_bar.setStyleSheet("QProgressBar::chunk { background-color: #ff7043; }")
        
        self.meditation_bar = QProgressBar()
        self.meditation_bar.setRange(0, 100)
        self.meditation_bar.setFormat("Meditation: %p%")
        self.meditation_bar.setStyleSheet("QProgressBar::chunk { background-color: #4fc3f7; }")
        
        self.stress_level_bar = QProgressBar()
        self.stress_level_bar.setRange(0, 100)
        self.stress_level_bar.setFormat("Stress Level: %p%")
        self.stress_level_bar.setStyleSheet("QProgressBar::chunk { background-color: #f44336; }")
        
        # 预测进度条
        self.prediction_progress = QProgressBar()
        self.prediction_progress.setRange(0, 5)
        self.prediction_progress.setFormat("Prediction Progress: %v/5")
        self.prediction_progress.setStyleSheet("QProgressBar::chunk { background-color: #66bb6a; }")
        
        self.start_btn = QPushButton("Start Mind Reading")
        self.start_btn.clicked.connect(self.start_prediction)
        
        self.confirm_btn = QPushButton("Confirm Prediction")
        self.confirm_btn.setEnabled(False)
        self.confirm_btn.clicked.connect(self.confirm_prediction)
        
        self.audio_btn = QPushButton("Play Relaxation Audio")
        self.audio_btn.clicked.connect(self.play_relaxation_audio)
        
        control_group_layout.addWidget(QLabel("Select Thought:"))
        control_group_layout.addWidget(self.thought_combo)
        control_group_layout.addWidget(self.attention_bar)
        control_group_layout.addWidget(self.meditation_bar)
        control_group_layout.addWidget(self.stress_level_bar)
        control_group_layout.addWidget(self.prediction_progress)
        control_group_layout.addWidget(self.start_btn)
        control_group_layout.addWidget(self.confirm_btn)
        control_group_layout.addWidget(self.audio_btn)
        control_group.setLayout(control_group_layout)
        
        # 模型管理组
        model_group = QGroupBox("Model Management")
        model_layout = QVBoxLayout()
        
        self.model_type_combo = QComboBox()
        self.model_type_combo.addItems(["LSTM", "CNN", "Hybrid"])
        self.model_type_combo.setCurrentText("LSTM")
        self.model_type_combo.currentTextChanged.connect(self.change_model_type)
        
        self.train_btn = QPushButton("Train New Model")
        self.train_btn.clicked.connect(self.train_model)
        
        self.save_btn = QPushButton("Save Current Model")
        self.save_btn.clicked.connect(self.save_model)
        
        self.load_btn = QPushButton("Load Model")
        self.load_btn.clicked.connect(self.load_model)
        
        self.realtime_check = QCheckBox("Real-time Training")
        self.realtime_check.setChecked(False)
        
        model_layout.addWidget(QLabel("Model Type:"))
        model_layout.addWidget(self.model_type_combo)
        model_layout.addWidget(self.train_btn)
        model_layout.addWidget(self.save_btn)
        model_layout.addWidget(self.load_btn)
        model_layout.addWidget(self.realtime_check)
        model_group.setLayout(model_layout)
        
        # 添加到控制面板
        control_layout.addWidget(status_group)
        control_layout.addWidget(control_group)
        control_layout.addWidget(model_group)
        control_layout.addStretch()
        
        # 右侧可视化区域
        vis_frame = QFrame()
        vis_layout = QVBoxLayout(vis_frame)
        vis_layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建标签页
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        
        # 实时数据标签页
        realtime_tab = QWidget()
        realtime_layout = QVBoxLayout(realtime_tab)
        
        # 使用PyQtGraph创建实时图表
        self.eeg_plot = pg.PlotWidget(title="Real-time EEG Signal")
        self.eeg_plot.setBackground('#2a2a3e')
        self.eeg_plot.setLabel('left', 'Amplitude')
        self.eeg_plot.setLabel('bottom', 'Time (s)')
        self.eeg_plot.addLegend()
        self.eeg_curve = self.eeg_plot.plot(pen=pg.mkPen('#4fc3f7', width=2), name="EEG")
        
        # 频谱图
        self.spectrum_plot = pg.PlotWidget(title="Frequency Spectrum")
        self.spectrum_plot.setBackground('#2a2a3e')
        self.spectrum_plot.setLabel('left', 'Power')
        self.spectrum_plot.setLabel('bottom', 'Frequency (Hz)')
        self.spectrum_plot.setXRange(0, 40)
        self.spectrum_curve = self.spectrum_plot.plot(pen=pg.mkPen('#ff7043', width=2), name="Spectrum")
        
        # 脑地形图占位符
        topo_frame = QFrame()
        topo_layout = QVBoxLayout(topo_frame)
        topo_layout.setContentsMargins(0, 0, 0, 0)
        self.topo_label = QLabel("Topographic Map")
        self.topo_label.setAlignment(Qt.AlignCenter)
        self.topo_label.setMinimumHeight(200)
        topo_layout.addWidget(self.topo_label)
        
        # 添加到实时标签页
        splitter1 = QSplitter(Qt.Vertical)
        splitter1.addWidget(self.eeg_plot)
        splitter1.addWidget(self.spectrum_plot)
        splitter1.addWidget(topo_frame)
        splitter1.setSizes([400, 300, 300])
        
        realtime_layout.addWidget(splitter1)
        
        # 分析标签页
        analysis_tab = QWidget()
        analysis_layout = QVBoxLayout(analysis_tab)
        
        # 准确率图表
        self.acc_plot = pg.PlotWidget(title="Prediction Accuracy History")
        self.acc_plot.setBackground('#2a2a3e')
        self.acc_plot.setLabel('left', 'Accuracy (%)')
        self.acc_plot.setLabel('bottom', 'Attempts')
        self.acc_plot.setYRange(0, 100)
        self.acc_curve = self.acc_plot.plot(pen=pg.mkPen('#66bb6a', width=2))
        
        # 特征图
        self.feature_plot = pg.PlotWidget(title="Feature Importance")
        self.feature_plot.setBackground('#2a2a3e')
        self.feature_plot.setLabel('left', 'Importance')
        self.feature_plot.setLabel('bottom', 'Features')
        
        # 添加到分析标签页
        analysis_layout.addWidget(self.acc_plot)
        analysis_layout.addWidget(self.feature_plot)
        
        # 3D脑图标签页 - 使用Matplotlib代替PyQtGraph的3D
        brain3d_tab = QWidget()
        brain3d_layout = QVBoxLayout(brain3d_tab)
        
        # 创建Matplotlib图形
        self.brain3d_fig = plt.figure(figsize=(8, 6), facecolor='#2a2a3e')
        self.brain3d_ax = self.brain3d_fig.add_subplot(111, projection='3d')
        self.brain3d_ax.set_facecolor('#2a2a3e')
        
        # 设置3D坐标轴颜色
        self.brain3d_ax.xaxis.pane.set_edgecolor('#e0e0e0')
        self.brain3d_ax.yaxis.pane.set_edgecolor('#e0e0e0')
        self.brain3d_ax.zaxis.pane.set_edgecolor('#e0e0e0')
        self.brain3d_ax.xaxis.pane.fill = False
        self.brain3d_ax.yaxis.pane.fill = False
        self.brain3d_ax.zaxis.pane.fill = False
        self.brain3d_ax.tick_params(axis='x', colors='#e0e0e0')
        self.brain3d_ax.tick_params(axis='y', colors='#e0e0e0')
        self.brain3d_ax.tick_params(axis='z', colors='#e0e0e0')
        self.brain3d_ax.set_title('3D Brain Activity', color='#e0e0e0')
        
        # 将图形嵌入到Qt
        self.brain3d_canvas = FigureCanvas(self.brain3d_fig)
        brain3d_layout.addWidget(self.brain3d_canvas)
        
        # 创建脑模型
        self.create_brain_model()  # 现在可以安全调用，因为brain3d_canvas已经创建
        
        # 添加标签页
        self.tabs.addTab(realtime_tab, "Real-time Data")
        self.tabs.addTab(analysis_tab, "Analysis")
        self.tabs.addTab(brain3d_tab, "3D Brain")
        
        vis_layout.addWidget(self.tabs)
        
        # 添加分割器
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(control_panel)
        splitter.addWidget(vis_frame)
        splitter.setSizes([350, 1250])
        
        main_layout.addWidget(splitter)
        
        # 状态栏
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("System ready. Model loaded.")
        
        # 创建系统监控计时器
        self.sys_monitor_timer = QTimer(self)
        self.sys_monitor_timer.timeout.connect(self.update_system_status)
        self.sys_monitor_timer.start(2000)
        
        # 创建预测计时器
        self.prediction_timer = QTimer(self)
        self.prediction_timer.timeout.connect(self.update_prediction_stage)
        
        # 初始化系统状态
        self.update_system_status()
    
    def update_electrodes(self, attention, meditation):
        """更新电极点颜色和大小"""
        # 清除现有图形
        self.brain3d_ax.clear()
        
        # 重新绘制脑模型
        u = np.linspace(0, 2 * np.pi, 20)
        v = np.linspace(0, np.pi, 20)
        x = np.outer(np.cos(u), np.sin(v))
        y = np.outer(np.sin(u), np.sin(v))
        z = np.outer(np.ones(np.size(u)), np.cos(v))
        self.brain3d_ax.plot_surface(x, y, z, color='#3949ab', alpha=0.3)
        
        # 更新电极点
        for i, pos in enumerate(self.electrodes):
            # 根据注意力和冥想水平改变电极颜色和大小
            intensity = attention if i % 2 == 0 else meditation
            size = 80 + intensity * 120
            color = plt.cm.viridis(intensity)
            self.brain3d_ax.scatter([pos[0]], [pos[1]], [pos[2]], s=size, c=[color])
        
        self.brain3d_canvas.draw()
    
    def update_ui(self, eeg_data, attention, meditation):
        current_time = time.time()
        
        # 更新进度条
        self.attention_bar.setValue(int(attention * 100))
        self.meditation_bar.setValue(int(meditation * 100))
        
        # 计算压力水平 (简单计算)
        stress = min(100, max(0, int((1 - meditation) * 80 + (1 - attention) * 20)))
        self.stress_level_bar.setValue(stress)
        
        # 更新EEG图 (高频更新)
        x = np.linspace(0, len(eeg_data)/256, len(eeg_data))
        self.eeg_curve.setData(x, eeg_data)
        
        # 更新频谱图 (低频更新)
        if current_time - self.last_spectrum_time > self.update_intervals['spectrum']:
            self.last_spectrum_time = current_time
            if len(eeg_data) > 100:
                # 使用快速FFT计算
                segment = eeg_data[-512:]  # 减少计算点数
                fft_data = np.abs(rfft(segment))
                freqs = rfftfreq(len(segment), 1/256)
                self.spectrum_curve.setData(freqs, fft_data)
        
        # 更新3D脑图 (低频更新)
        if current_time - self.last_3d_update > self.update_intervals['3d']:
            self.last_3d_update = current_time
            self.update_electrodes(attention, meditation)
        
        # 更新脑地形图 (最低频更新)
        if current_time - self.last_topo_update > self.update_intervals['topo']:
            self.last_topo_update = current_time
            self.update_topomap(eeg_data)

    # 优化脑地形图生成
    def update_topomap(self, eeg_data):
        """更新脑地形图"""
        try:
            if not hasattr(self, 'topo_fig'):
                # 预创建图形元素
                self.topo_fig, self.topo_ax = plt.subplots(figsize=(4, 3), facecolor='#2a2a3e')
                self.topo_ax.set_facecolor('#2a2a3e')
                self.topo_ax.set_xticks([])
                self.topo_ax.set_yticks([])
                self.topo_ax.set_title('Brain Topography', color='white')
                
                # 电极位置 (固定不变)
                self.topo_pos = np.array([
                    [0, 0.5],   # Fp1
                    [0, -0.5],  # Fp2
                    [-0.5, 0],  # T3
                    [0.5, 0],   # T4
                    [-0.3, 0.3], # C3
                    [0.3, 0.3],  # C4
                    [-0.3, -0.3], # P3
                    [0.3, -0.3]  # P4
                ])
                
                # 添加电极标签 (固定不变)
                for i, (x, y) in enumerate(self.topo_pos):
                    self.topo_ax.text(x, y, f'E{i+1}', ha='center', va='center', 
                                     color='white', fontsize=8)
                
                # 创建颜色条 (固定不变)
                self.topo_cbar = self.topo_fig.colorbar(
                    plt.cm.ScalarMappable(cmap='viridis'), 
                    ax=self.topo_ax
                )
                self.topo_cbar.ax.yaxis.set_tick_params(color='white')
                plt.setp(plt.getp(self.topo_cbar.ax.axes, 'yticklabels'), color='white')
                
                # 创建散点图对象
                self.topo_scatter = self.topo_ax.scatter(
                    self.topo_pos[:, 0], self.topo_pos[:, 1], 
                    s=300, cmap='viridis', edgecolors='w', linewidths=1.5
                )
            
            # 随机生成8个通道的数据
            data = np.random.rand(8) * 10
            
            # 只更新数据
            self.topo_scatter.set_array(data)
            self.topo_scatter.set_clim(vmin=min(data), vmax=max(data))
            
            # 保存到内存缓冲区
            buffer = BytesIO()
            self.topo_fig.savefig(buffer, format='png', bbox_inches='tight', pad_inches=0, transparent=True)
            buffer.seek(0)
            
            # 直接从内存加载图像
            pixmap = QPixmap()
            pixmap.loadFromData(buffer.getvalue())
            self.topo_label.setPixmap(pixmap.scaled(
                self.topo_label.width(), 
                self.topo_label.height(), 
                Qt.KeepAspectRatio
            ))
        except Exception as e:
            print(f"Topomap error: {e}")
    
    def update_system_status(self):
        """更新系统状态信息"""
        # 模拟系统状态
        cpu_usage = random.randint(5, 30)
        memory_usage = random.randint(200, 500)
        
        self.cpu_label.setText(f"CPU Usage: {cpu_usage}%")
        self.memory_label.setText(f"Memory Usage: {memory_usage} MB")
        
        if gpus:
            self.gpu_label.setText(f"GPU: {gpus[0].name.split('/')[-1]}")
        else:
            self.gpu_label.setText("GPU: Not available")
    
    
    def start_prediction(self):
        """开始预测过程"""
        if not self.model_loaded:
            QMessageBox.warning(self, "Model Not Loaded", "Please load or train a model first.")
            return
        
        self.target_thought = self.thought_combo.currentText()
        self.brainwave_generator.start_prediction()
        self.start_btn.setEnabled(False)
        self.confirm_btn.setEnabled(True)
        self.status_bar.showMessage("Reading brainwaves... Please focus on your thought.")
        
        # 开始预测阶段计时器
        self.prediction_stage = 0
        self.prediction_timer.start(1500)
        
        # 语音提示
        self.speak(f"Starting mind reading for {self.target_thought}")
    
    def update_prediction_progress(self, stage):
        """更新预测进度条"""
        self.prediction_progress.setValue(stage)
    
    def update_prediction_stage(self):
        """更新预测阶段"""
        self.prediction_stage += 1
        self.brainwave_generator.update_prediction_stage()
        
        if self.prediction_stage <= 5:
            self.status_bar.showMessage(f"Analyzing brainwaves... Stage {self.prediction_stage}/5")
        else:
            self.prediction_timer.stop()
            self.complete_prediction()
    
    def complete_prediction(self):
        """完成预测并显示结果"""
        # 获取最近的脑波数据
        eeg_data = self.brainwave_generator.eeg_data[-128:]
        if len(eeg_data) < 128:
            eeg_data = np.pad(eeg_data, (0, 128 - len(eeg_data)), 'constant')
        
        # 转换为模型输入格式
        X = np.array(eeg_data).reshape(1, 128, 1)
        
        # 进行预测
        prediction_idx, confidence = self.model.predict(X)
        predicted_class = self.model.classes[prediction_idx[0]]
        confidence_percent = int(confidence[0] * 100)
        
        # 为了演示目的，80%的时间预测正确
        if random.random() < 0.8:
            predicted = self.target_thought
            is_correct = True
        else:
            # 从其他类别中选择一个
            other_classes = [c for c in self.model.classes if c != self.target_thought]
            predicted = random.choice(other_classes)
            is_correct = False
        
        # 更新结果
        self.status_bar.showMessage(f"Predicted: {predicted} (Confidence: {confidence_percent}%)")
        
        # 更新准确率历史
        self.predictions.append(1 if is_correct else 0)
        if self.predictions:
            accuracy = sum(self.predictions) / len(self.predictions) * 100
            self.accuracy_history.append(accuracy)
            self.update_accuracy_plot()
        
        # 重置按钮状态
        self.start_btn.setEnabled(True)
        self.brainwave_generator.stop_prediction()
        
        # 语音反馈
        feedback = "Correct" if is_correct else "Incorrect"
        self.speak(f"Prediction complete. Result: {predicted}. Confidence: {confidence_percent} percent. {feedback}")
    
    def confirm_prediction(self):
        """确认预测结果"""
        self.confirm_btn.setEnabled(False)
        self.start_btn.setEnabled(True)
        self.brainwave_generator.stop_prediction()
        self.prediction_timer.stop()
        
        # 在实际应用中，这里会保存用户的反馈用于重新训练
        self.status_bar.showMessage("Prediction confirmed. Thank you for your feedback.")
        self.speak("Prediction confirmed. Feedback recorded.")
        
        # 实时训练选项
        if self.realtime_check.isChecked():
            self.status_bar.showMessage("Updating model with new data...")
            self.speak("Updating model with new data.")
            # 在实际应用中，这里会使用新数据更新模型

    def train_model(self):
        """训练模型"""
        if self.model.training_in_progress:
            QMessageBox.information(self, "训练中", "模型正在训练中，请稍候...")
            return
            
        try:
            self.train_btn.setEnabled(False)
            self.status_bar.showMessage("准备训练数据...")
            
            # 生成模拟数据（在后台线程中）
            def generate_data():
                try:
                    self.status_bar.showMessage("生成训练数据中...")
                    X, y = self.model.generate_simulated_data(num_samples=2000)
                    self.training_queue.put((5, "数据生成完成，开始训练..."))
                    
                    # 构建模型
                    self.model.build_model(input_shape=(128, 1), num_classes=len(self.model.classes))
                    
                    # 启动训练
                    self.model.train(X, y, epochs=50, progress_callback=lambda p, m: self.training_queue.put((p, m)))
                except Exception as e:
                    self.training_queue.put((0, f"训练错误: {str(e)}"))
                    self.train_btn.setEnabled(True)
            
            # 启动训练线程
            self.training_thread = threading.Thread(target=generate_data, daemon=True)
            self.training_thread.start()
            
            # 启动进度更新计时器
            self.training_progress_timer.start()
            
        except Exception as e:
            QMessageBox.critical(self, "训练错误", f"训练准备过程中出错:\n{str(e)}")
            self.train_btn.setEnabled(True)
    def save_model(self):
        """保存模型"""
        if not self.model_loaded:
            QMessageBox.warning(self, "No Model", "No model to save. Please train a model first.")
            return
            
        filename, _ = QFileDialog.getSaveFileName(self, "Save Model", "", "HDF5 Files (*.h5)")
        if filename:
            try:
                self.model.save_model(filename)
                self.status_bar.showMessage(f"Model saved to {filename}")
                self.speak("Model saved successfully.")
            except Exception as e:
                QMessageBox.critical(self, "Save Error", f"Failed to save model:\n{str(e)}")
    
    def load_model(self):
        """加载模型"""
        filename, _ = QFileDialog.getOpenFileName(self, "Load Model", "", "HDF5 Files (*.h5)")
        if filename:
            try:
                self.model.load_model(filename)
                self.model_loaded = True
                self.status_bar.showMessage(f"Model loaded from {filename}")
                self.speak("Model loaded successfully.")
            except Exception as e:
                QMessageBox.critical(self, "Load Error", f"Failed to load model:\n{str(e)}")
    
    def change_model_type(self, model_type):
        """更改模型类型"""
        self.model.model_type = model_type
        self.status_bar.showMessage(f"Model type changed to {model_type}")
    
    def update_accuracy_plot(self):
        """更新准确率图表"""
        if not self.accuracy_history:
            return
            
        x = np.arange(len(self.accuracy_history))
        self.acc_curve.setData(x, self.accuracy_history)
        
        # 添加趋势线
        if len(x) > 1:
            # 使用移动平均平滑曲线
            window_size = min(5, len(x))
            weights = np.repeat(1.0, window_size) / window_size
            smoothed = np.convolve(self.accuracy_history, weights, 'valid')
            self.acc_plot.plot(x[window_size-1:], smoothed, pen=pg.mkPen('#ff7043', width=2, style=Qt.DashLine))
    
    def play_relaxation_audio(self):
        """播放放松音频"""
        try:
            # 生成白噪声作为放松音频
            duration = 10  # seconds
            fs = 44100  # sample rate
            samples = np.random.randn(duration * fs)
            
            # 添加alpha波频率
            t = np.linspace(0, duration, duration * fs, endpoint=False)
            alpha_wave = 0.3 * np.sin(2 * np.pi * 10 * t)
            samples = 0.7 * samples + 0.3 * alpha_wave
            
            # 标准化
            samples *= 0.1 / np.max(np.abs(samples))
            
            # 播放音频
            sd.play(samples, fs)
            self.status_bar.showMessage("Playing relaxation audio...")
            self.speak("Playing relaxation audio.")
        except Exception as e:
            self.status_bar.showMessage(f"Audio error: {str(e)}")
    
    def speak(self, text):
        """使用语音引擎朗读文本"""
        self.engine.say(text)
        self.engine.runAndWait()
    
    def closeEvent(self, event):
        """关闭应用时停止线程"""
        self.brainwave_generator.is_running = False
        self.brainwave_generator.wait(2000)
        
        # 停止任何正在播放的音频
        sd.stop()
        if self.training_progress_timer.isActive():
            self.training_progress_timer.stop()
        
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    # 启用高DPI缩放
    if hasattr(Qt, 'AA_EnableHighDpiScaling'):
        app.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
        app.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    window = MindReadingApp()
    window.show()
    sys.exit(app.exec_())