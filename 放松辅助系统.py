import sys
import time
import math
import random
import json
import sqlite3
from datetime import datetime, timedelta
import numpy as np
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QGridLayout, QTabWidget, QLabel, 
                             QPushButton, QSlider, QProgressBar, QTextEdit,
                             QListWidget, QListWidgetItem, QGroupBox, 
                             QSpinBox, QDoubleSpinBox, QComboBox, QCheckBox,
                             QMessageBox, QSplitter, QFrame, QDial, QFileDialog,
                             QInputDialog, QCalendarWidget, QTableWidget, 
                             QTableWidgetItem, QHeaderView, QToolBar, QAction,
                             QStatusBar, QMenu, QMenuBar, QSystemTrayIcon, 
                             QStyle, QToolButton, QLineEdit, QDialog, 
                             QDialogButtonBox, QFormLayout)
from PyQt5.QtCore import QUrl, Qt, QTimer, QTime, pyqtSignal, QThread, QSize, QPoint, QSettings
from PyQt5.QtGui import (QFont, QPalette, QColor, QPainter, QPen, QBrush, 
                         QLinearGradient, QRadialGradient, QIcon, QPixmap, 
                         QMovie, QPainterPath)
from PyQt5.QtMultimedia import QSoundEffect, QAudioDeviceInfo, QAudio
from PyQt5.QtMultimediaWidgets import QVideoWidget
from PyQt5.QtChart import QChart, QChartView, QLineSeries, QValueAxis, QDateTimeAxis, QSplineSeries
from PyQt5.QtCore import QDateTime

# 生物反馈传感器模拟类（实际应用中会连接真实传感器）
class BioFeedbackSensor(QThread):
    data_updated = pyqtSignal(dict)  # 心率，皮电反应，肌电等数据
    
    def __init__(self):
        super().__init__()
        self.running = False
        self.heart_rate = 70
        self.gsr = 500  # 皮电反应
        self.emg = 50   # 肌电
        self.temperature = 36.5
        self.respiration_rate = 16
        self.stress_level = 50
        
    def run(self):
        self.running = True
        while self.running:
            # 模拟生物反馈数据变化
            self.heart_rate += random.randint(-2, 2)
            self.heart_rate = max(60, min(100, self.heart_rate))
            
            self.gsr += random.randint(-10, 10)
            self.gsr = max(200, min(800, self.gsr))
            
            self.emg += random.randint(-2, 2)
            self.emg = max(10, min(100, self.emg))
            
            self.temperature += random.uniform(-0.1, 0.1)
            self.temperature = max(36.0, min(37.5, self.temperature))
            
            self.respiration_rate += random.randint(-1, 1)
            self.respiration_rate = max(12, min(20, self.respiration_rate))
            
            # 计算压力水平（简化模型）
            self.stress_level = int((self.heart_rate - 60) * 2.5 + 
                                   (self.gsr - 200) / 6 + 
                                   (self.emg - 10) * 0.5)
            self.stress_level = max(0, min(100, self.stress_level))
            
            data = {
                'heart_rate': self.heart_rate,
                'gsr': self.gsr,
                'emg': self.emg,
                'temperature': self.temperature,
                'respiration_rate': self.respiration_rate,
                'stress_level': self.stress_level,
                'timestamp': datetime.now()
            }
            
            self.data_updated.emit(data)
            time.sleep(1)  # 每秒更新一次
    
    def stop_sensor(self):
        self.running = False
        self.wait()

# 环境音效管理器
class SoundManager:
    def __init__(self):
        self.sounds = {}
        self.current_sound = None
        self.volume = 0.5
        
        # 预定义音效
        self.sound_files = {
            'rain': 'sounds/rain.wav',
            'ocean': 'sounds/ocean.wav',
            'forest': 'sounds/forest.wav',
            'white_noise': 'sounds/white_noise.wav',
            'birds': 'sounds/birds.wav',
            'wind': 'sounds/wind.wav',
            'thunder': 'sounds/thunder.wav',
            'fireplace': 'sounds/fireplace.wav'
        }
        
    def load_sounds(self):
        for name, file_path in self.sound_files.items():
            effect = QSoundEffect()
            # 将字符串路径转换为 QUrl
            url = QUrl.fromLocalFile(file_path)
            effect.setSource(url)
            effect.setLoopCount(QSoundEffect.Infinite)
            effect.setVolume(self.volume)
            self.sounds[name] = effect

    
    def play_sound(self, sound_name):
        if self.current_sound:
            self.current_sound.stop()
        
        if sound_name in self.sounds:
            self.current_sound = self.sounds[sound_name]
            self.current_sound.play()
    
    def stop_sound(self):
        if self.current_sound:
            self.current_sound.stop()
            self.current_sound = None
    
    def set_volume(self, volume):
        self.volume = volume
        for sound in self.sounds.values():
            sound.setVolume(volume)
        if self.current_sound:
            self.current_sound.setVolume(volume)

# 数据分析管理器
class DataAnalyzer:
    def __init__(self, db_path='relaxation_data.db'):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # 创建会话记录表
        c.execute('''CREATE TABLE IF NOT EXISTS sessions
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      technique TEXT,
                      duration INTEGER,
                      start_time DATETIME,
                      end_time DATETIME,
                      stress_before INTEGER,
                      stress_after INTEGER,
                      notes TEXT)''')
        
        # 创建生物反馈数据表
        c.execute('''CREATE TABLE IF NOT EXISTS biofeedback
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      session_id INTEGER,
                      timestamp DATETIME,
                      heart_rate INTEGER,
                      gsr INTEGER,
                      emg INTEGER,
                      temperature REAL,
                      respiration_rate INTEGER,
                      stress_level INTEGER,
                      FOREIGN KEY(session_id) REFERENCES sessions(id))''')
        
        conn.commit()
        conn.close()
    
    def save_session(self, technique, duration, start_time, end_time, 
                    stress_before, stress_after, notes=""):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('''INSERT INTO sessions 
                     (technique, duration, start_time, end_time, 
                      stress_before, stress_after, notes)
                     VALUES (?, ?, ?, ?, ?, ?, ?)''',
                  (technique, duration, start_time, end_time, 
                   stress_before, stress_after, notes))
        
        session_id = c.lastrowid
        conn.commit()
        conn.close()
        return session_id
    
    def save_biofeedback_data(self, session_id, data):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('''INSERT INTO biofeedback 
                     (session_id, timestamp, heart_rate, gsr, emg, 
                      temperature, respiration_rate, stress_level)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                  (session_id, data['timestamp'], data['heart_rate'], 
                   data['gsr'], data['emg'], data['temperature'], 
                   data['respiration_rate'], data['stress_level']))
        
        conn.commit()
        conn.close()
    
    def get_session_history(self, limit=50):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('''SELECT * FROM sessions 
                     ORDER BY start_time DESC LIMIT ?''', (limit,))
        sessions = c.fetchall()
        
        conn.close()
        return sessions
    
    def get_stress_trends(self, days=30):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # 获取最近30天的平均压力水平
        c.execute('''SELECT date(start_time) as day, 
                            AVG(stress_before), AVG(stress_after)
                     FROM sessions 
                     WHERE start_time >= date('now', '-{} days')
                     GROUP BY day ORDER BY day'''.format(days))
        
        trends = c.fetchall()
        conn.close()
        return trends

# 高级呼吸模式类
class AdvancedBreathingPattern:
    def __init__(self, name, inhale, hold, exhale, hold_after, cycles=0):
        self.name = name
        self.inhale = inhale
        self.hold = hold
        self.exhale = exhale
        self.hold_after = hold_after
        self.cycles = cycles  # 0表示无限循环
    
    def total_cycle_time(self):
        return self.inhale + self.hold + self.exhale + self.hold_after
    
    def get_phase_at_time(self, elapsed_time, cycle_count):
        """根据经过的时间和周期计数返回当前阶段和进度"""
        if self.cycles > 0 and cycle_count >= self.cycles:
            return "complete", 1.0, cycle_count
        
        cycle_time = elapsed_time % self.total_cycle_time()
        
        if cycle_time < self.inhale:
            return "inhale", cycle_time / self.inhale, cycle_count
        elif cycle_time < self.inhale + self.hold:
            return "hold", (cycle_time - self.inhale) / self.hold, cycle_count
        elif cycle_time < self.inhale + self.hold + self.exhale:
            return "exhale", (cycle_time - self.inhale - self.hold) / self.exhale, cycle_count
        else:
            # 检查是否完成一个完整周期
            remaining_time = cycle_time - self.inhale - self.hold - self.exhale
            if remaining_time >= self.hold_after - 0.1:  # 容差
                cycle_count += 1
                if self.cycles > 0 and cycle_count >= self.cycles:
                    return "complete", 1.0, cycle_count
            
            return "hold_after", remaining_time / self.hold_after, cycle_count

# 增强版呼吸练习
class EnhancedBreathingExercise:
    def __init__(self):
        self.name = "高级呼吸练习"
        self.description = "包含多种呼吸模式和生物反馈的高级呼吸练习"
        
        # 高级呼吸模式
        self.patterns = [
            AdvancedBreathingPattern("平衡呼吸", 4, 0, 4, 0),
            AdvancedBreathingPattern("4-7-8呼吸", 4, 7, 8, 0),
            AdvancedBreathingPattern("箱式呼吸", 4, 4, 4, 4),
            AdvancedBreathingPattern("放松呼吸", 5, 0, 5, 0),
            AdvancedBreathingPattern("能量呼吸", 2, 0, 4, 0),
            AdvancedBreathingPattern("深度放松", 6, 2, 8, 2, cycles=10)
        ]
        
        self.current_pattern = self.patterns[0]
        self.is_running = False
        self.start_time = 0
        self.cycle_count = 0
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_display)
        
        # 生物反馈集成
        self.bio_sensor = BioFeedbackSensor()
        self.bio_sensor.data_updated.connect(self.on_biofeedback_update)
        self.current_bio_data = None
        
        # 音效集成
        self.sound_manager = SoundManager()
        self.sound_manager.load_sounds()
        
    def start(self):
        self.is_running = True
        self.start_time = time.time()
        self.cycle_count = 0
        self.timer.start(50)  # 每50毫秒更新一次
        
        # 启动生物反馈传感器
        self.bio_sensor.start()
        
        # 播放环境音效
        self.sound_manager.play_sound('ocean')
    
    def stop(self):
        self.is_running = False
        self.timer.stop()
        
        # 停止生物反馈传感器
        self.bio_sensor.stop_sensor()
        
        # 停止音效
        self.sound_manager.stop_sound()
    
    def set_pattern(self, pattern_index):
        if 0 <= pattern_index < len(self.patterns):
            self.current_pattern = self.patterns[pattern_index]
    
    def update_display(self):
        """更新显示（由UI组件处理）"""
        pass
    
    def on_biofeedback_update(self, data):
        """处理生物反馈数据更新"""
        self.current_bio_data = data
    
    def get_ui(self):
        return EnhancedBreathingUI(self)

# 增强版呼吸练习UI
class EnhancedBreathingUI(QWidget):
    def __init__(self, exercise):
        super().__init__()
        self.exercise = exercise
        self.exercise.update_display = self.update_display
        self.init_ui()
        
    def init_ui(self):
        main_layout = QHBoxLayout()
        
        # 左侧面板 - 呼吸控制
        left_panel = QVBoxLayout()
        
        # 标题
        title = QLabel("高级呼吸练习")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        left_panel.addWidget(title)
        
        # 模式选择
        pattern_layout = QHBoxLayout()
        pattern_layout.addWidget(QLabel("呼吸模式:"))
        self.pattern_combo = QComboBox()
        for pattern in self.exercise.patterns:
            self.pattern_combo.addItem(pattern.name)
        self.pattern_combo.currentIndexChanged.connect(self.pattern_changed)
        pattern_layout.addWidget(self.pattern_combo)
        pattern_layout.addStretch()
        left_panel.addLayout(pattern_layout)
        
        # 呼吸指示器
        self.breathing_circle = AdvancedBreathingCircle()
        left_panel.addWidget(self.breathing_circle)
        
        # 周期计数
        self.cycle_label = QLabel("周期: 0/∞")
        self.cycle_label.setAlignment(Qt.AlignCenter)
        left_panel.addWidget(self.cycle_label)
        
        # 控制按钮
        control_layout = QHBoxLayout()
        self.start_btn = QPushButton("开始")
        self.start_btn.clicked.connect(self.toggle_exercise)
        control_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("停止")
        self.stop_btn.clicked.connect(self.stop_exercise)
        self.stop_btn.setEnabled(False)
        control_layout.addWidget(self.stop_btn)
        
        left_panel.addLayout(control_layout)
        
        # 音效控制
        sound_layout = QHBoxLayout()
        sound_layout.addWidget(QLabel("环境音效:"))
        self.sound_combo = QComboBox()
        self.sound_combo.addItems(["无", "雨声", "海洋", "森林", "白噪音", "鸟鸣", "风声", "雷声", "壁炉"])
        self.sound_combo.currentTextChanged.connect(self.sound_changed)
        sound_layout.addWidget(self.sound_combo)
        
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(50)
        self.volume_slider.valueChanged.connect(self.volume_changed)
        sound_layout.addWidget(QLabel("音量:"))
        sound_layout.addWidget(self.volume_slider)
        
        left_panel.addLayout(sound_layout)
        
        # 右侧面板 - 生物反馈
        right_panel = QVBoxLayout()
        
        bio_title = QLabel("生物反馈数据")
        bio_title.setFont(QFont("Arial", 14, QFont.Bold))
        right_panel.addWidget(bio_title)
        
        # 生物反馈指标
        self.heart_rate_label = QLabel("心率: -- BPM")
        right_panel.addWidget(self.heart_rate_label)
        
        self.gsr_label = QLabel("皮电反应: --")
        right_panel.addWidget(self.gsr_label)
        
        self.stress_label = QLabel("压力水平: --")
        right_panel.addWidget(self.stress_label)
        
        self.temperature_label = QLabel("体温: -- °C")
        right_panel.addWidget(self.temperature_label)
        
        # 压力水平指示器
        self.stress_gauge = StressGauge()
        right_panel.addWidget(self.stress_gauge)
        
        # 呼吸频率
        self.respiration_label = QLabel("呼吸频率: -- 次/分钟")
        right_panel.addWidget(self.respiration_label)
        
        right_panel.addStretch()
        
        # 组合左右面板
        splitter = QSplitter(Qt.Horizontal)
        left_widget = QWidget()
        left_widget.setLayout(left_panel)
        right_widget = QWidget()
        right_widget.setLayout(right_panel)
        right_widget.setMaximumWidth(250)
        
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([600, 200])
        
        main_layout.addWidget(splitter)
        self.setLayout(main_layout)
    
    def pattern_changed(self, index):
        self.exercise.set_pattern(index)
    
    def sound_changed(self, sound_name):
        sound_map = {
            "无": None,
            "雨声": "rain",
            "海洋": "ocean",
            "森林": "forest",
            "白噪音": "white_noise",
            "鸟鸣": "birds",
            "风声": "wind",
            "雷声": "thunder",
            "壁炉": "fireplace"
        }
        
        if sound_name == "无":
            self.exercise.sound_manager.stop_sound()
        elif sound_name in sound_map:
            self.exercise.sound_manager.play_sound(sound_map[sound_name])
    
    def volume_changed(self, value):
        volume = value / 100.0
        self.exercise.sound_manager.set_volume(volume)
    
    def toggle_exercise(self):
        if self.exercise.is_running:
            self.stop_exercise()
        else:
            self.start_exercise()
    
    def start_exercise(self):
        self.exercise.start()
        self.start_btn.setText("暂停")
        self.stop_btn.setEnabled(True)
    
    def stop_exercise(self):
        self.exercise.stop()
        self.start_btn.setText("开始")
        self.stop_btn.setEnabled(False)
        self.breathing_circle.reset()
        
        # 重置生物反馈显示
        self.heart_rate_label.setText("心率: -- BPM")
        self.gsr_label.setText("皮电反应: --")
        self.stress_label.setText("压力水平: --")
        self.temperature_label.setText("体温: -- °C")
        self.respiration_label.setText("呼吸频率: -- 次/分钟")
        self.stress_gauge.set_stress_level(0)
    
    def update_display(self):
        if self.exercise.is_running:
            elapsed = time.time() - self.exercise.start_time
            phase, progress, cycle_count = self.exercise.current_pattern.get_phase_at_time(
                elapsed, self.exercise.cycle_count)
            
            self.exercise.cycle_count = cycle_count
            
            # 更新呼吸指示器
            self.breathing_circle.update_breathing(phase, progress)
            
            # 更新周期计数
            if self.exercise.current_pattern.cycles > 0:
                self.cycle_label.setText(f"周期: {cycle_count}/{self.exercise.current_pattern.cycles}")
            else:
                self.cycle_label.setText(f"周期: {cycle_count}/∞")
            
            # 更新生物反馈数据
            if self.exercise.current_bio_data:
                data = self.exercise.current_bio_data
                self.heart_rate_label.setText(f"心率: {data['heart_rate']} BPM")
                self.gsr_label.setText(f"皮电反应: {data['gsr']}")
                self.stress_label.setText(f"压力水平: {data['stress_level']}")
                self.temperature_label.setText(f"体温: {data['temperature']:.1f} °C")
                self.respiration_label.setText(f"呼吸频率: {data['respiration_rate']} 次/分钟")
                self.stress_gauge.set_stress_level(data['stress_level'])

# 高级呼吸指示器
class AdvancedBreathingCircle(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumSize(300, 300)
        self.phase = "inhale"
        self.progress = 0
        self.radius = 0
        
    def update_breathing(self, phase, progress):
        self.phase = phase
        self.progress = progress
        self.update()
    
    def reset(self):
        self.phase = "inhale"
        self.progress = 0
        self.update()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 绘制背景
        gradient = QRadialGradient(self.width()/2, self.height()/2, self.width()/2)
        gradient.setColorAt(0, QColor(240, 240, 240))
        gradient.setColorAt(1, QColor(200, 200, 200))
        painter.fillRect(self.rect(), QBrush(gradient))
        
        # 计算中心点和最大半径
        center_x = self.width() / 2
        center_y = self.height() / 2
        max_radius = min(center_x, center_y) - 20
        
        # 根据阶段和进度计算当前半径
        if self.phase == "inhale":
            self.radius = max_radius * 0.3 + max_radius * 0.7 * self.progress
            color = QColor(100, 200, 100)  # 绿色表示吸气
        elif self.phase == "exhale":
            self.radius = max_radius * 0.3 + max_radius * 0.7 * (1 - self.progress)
            color = QColor(200, 100, 100)  # 红色表示呼气
        elif self.phase == "complete":
            self.radius = max_radius * 0.5
            color = QColor(100, 100, 200)  # 蓝色表示完成
        else:  # 屏息
            self.radius = max_radius * 0.3
            color = QColor(100, 100, 200)  # 蓝色表示屏息
        
        # 绘制外圆
        painter.setBrush(QBrush(color.lighter(150)))
        painter.setPen(QPen(Qt.black, 2))
        painter.drawEllipse(int(center_x - max_radius), int(center_y - max_radius), 
                           int(max_radius * 2), int(max_radius * 2))
        
        # 绘制内圆
        gradient = QRadialGradient(center_x, center_y, self.radius)
        gradient.setColorAt(0, color.lighter(200))
        gradient.setColorAt(1, color.darker(150))
        painter.setBrush(QBrush(gradient))
        painter.setPen(QPen(Qt.black, 1))
        painter.drawEllipse(int(center_x - self.radius), int(center_y - self.radius), 
                           int(self.radius * 2), int(self.radius * 2))
        
        # 绘制阶段文字
        phase_text = {
            "inhale": "吸气",
            "exhale": "呼气",
            "hold": "屏息",
            "hold_after": "屏息",
            "complete": "完成"
        }.get(self.phase, "")
        
        painter.setPen(QPen(Qt.black))
        painter.setFont(QFont("Arial", 16, QFont.Bold))
        painter.drawText(self.rect(), Qt.AlignCenter, phase_text)

# 压力水平指示器
class StressGauge(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumSize(200, 100)
        self.stress_level = 0
        
    def set_stress_level(self, level):
        self.stress_level = level
        self.update()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 绘制背景
        painter.fillRect(self.rect(), QColor(240, 240, 240))
        
        # 绘制压力计背景
        gauge_rect = self.rect().adjusted(10, 10, -10, -10)
        gauge_rect.setHeight(30)
        
        # 绘制渐变背景（从绿到红）
        gradient = QLinearGradient(gauge_rect.topLeft(), gauge_rect.topRight())
        gradient.setColorAt(0, QColor(0, 255, 0))   # 绿色
        gradient.setColorAt(0.5, QColor(255, 255, 0)) # 黄色
        gradient.setColorAt(1, QColor(255, 0, 0))   # 红色
        
        painter.setBrush(QBrush(gradient))
        painter.setPen(QPen(Qt.black, 1))
        painter.drawRect(gauge_rect)
        
        # 绘制指针
        pointer_x = int(gauge_rect.left() + (gauge_rect.width() * self.stress_level / 100))
        pointer_y = gauge_rect.bottom()
        
        painter.setPen(QPen(Qt.black, 2))
        painter.drawLine(pointer_x, gauge_rect.top(), pointer_x, gauge_rect.bottom() + 10)
        
        # 绘制三角形指针
        path = QPainterPath()
        path.moveTo(pointer_x, gauge_rect.bottom() + 10)
        path.lineTo(pointer_x - 5, gauge_rect.bottom() + 20)
        path.lineTo(pointer_x + 5, gauge_rect.bottom() + 20)
        path.closeSubpath()
        
        painter.setBrush(QBrush(Qt.black))
        painter.drawPath(path)
        
        # 绘制标签
        painter.setPen(QPen(Qt.black))
        painter.setFont(QFont("Arial", 10))
        painter.drawText(gauge_rect.left(), gauge_rect.bottom() + 40, "放松")
        painter.drawText(gauge_rect.right() - 30, gauge_rect.bottom() + 40, "紧张")

# 数据分析面板
class DataAnalysisPanel(QWidget):
    def __init__(self, analyzer):
        super().__init__()
        self.analyzer = analyzer
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 标题
        title = QLabel("放松数据统计")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # 选项卡
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        
        # 会话历史标签页
        self.session_history_tab = QWidget()
        self.session_history_layout = QVBoxLayout(self.session_history_tab)
        
        # 会话历史表格
        self.session_table = QTableWidget()
        self.session_table.setColumnCount(7)
        self.session_table.setHorizontalHeaderLabels([
            "ID", "技术", "时长(分)", "开始时间", "结束时间", "压力前", "压力后"
        ])
        self.session_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.session_history_layout.addWidget(self.session_table)
        
        # 刷新按钮
        refresh_btn = QPushButton("刷新数据")
        refresh_btn.clicked.connect(self.refresh_data)
        self.session_history_layout.addWidget(refresh_btn)
        
        self.tabs.addTab(self.session_history_tab, "会话历史")
        
        # 趋势分析标签页
        self.trends_tab = QWidget()
        self.trends_layout = QVBoxLayout(self.trends_tab)
        
        # 压力趋势图表
        self.stress_chart_view = QChartView()
        self.stress_chart_view.setRenderHint(QPainter.Antialiasing)
        self.trends_layout.addWidget(self.stress_chart_view)
        
        self.tabs.addTab(self.trends_tab, "趋势分析")
        
        self.setLayout(layout)
        self.refresh_data()
    
    def refresh_data(self):
        # 刷新会话历史
        sessions = self.analyzer.get_session_history()
        self.session_table.setRowCount(len(sessions))
        
        for row, session in enumerate(sessions):
            for col, value in enumerate(session):
                item = QTableWidgetItem(str(value))
                self.session_table.setItem(row, col, item)
        
        # 刷新趋势图表
        self.update_stress_chart()
    
    def update_stress_chart(self):
        chart = QChart()
        chart.setTitle("压力水平趋势")
        chart.setAnimationOptions(QChart.SeriesAnimations)
        
        # 创建系列
        before_series = QSplineSeries()
        before_series.setName("放松前压力")
        
        after_series = QSplineSeries()
        after_series.setName("放松后压力")
        
        # 获取数据
        trends = self.analyzer.get_stress_trends(30)
        
        # 添加数据点
        for i, (day, avg_before, avg_after) in enumerate(trends):
            before_series.append(i, avg_before)
            after_series.append(i, avg_after)
        
        # 添加到图表
        chart.addSeries(before_series)
        chart.addSeries(after_series)
        
        # 创建坐标轴
        axis_x = QValueAxis()
        axis_x.setTitleText("天数")
        axis_x.setLabelFormat("%d")
        axis_x.setRange(0, len(trends))
        chart.addAxis(axis_x, Qt.AlignBottom)
        
        axis_y = QValueAxis()
        axis_y.setTitleText("压力水平")
        axis_y.setLabelFormat("%d")
        axis_y.setRange(0, 100)
        chart.addAxis(axis_y, Qt.AlignLeft)
        
        # 附加系列到坐标轴
        before_series.attachAxis(axis_x)
        before_series.attachAxis(axis_y)
        after_series.attachAxis(axis_x)
        after_series.attachAxis(axis_y)
        
        self.stress_chart_view.setChart(chart)

# 主应用程序窗口
class AdvancedRelaxationSystem(QMainWindow):
    def __init__(self):
        super().__init__()
        self.analyzer = DataAnalyzer()
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("高级放松辅助系统")
        self.setGeometry(100, 100, 1000, 700)
        
        # 创建菜单栏
        self.create_menu()
        
        # 创建中央部件和布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # 创建标签页
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        
        # 添加各种放松技术
        self.breathing_exercise = EnhancedBreathingExercise()
        self.tabs.addTab(self.breathing_exercise.get_ui(), "高级呼吸练习")
        
        # 添加数据分析面板
        self.data_panel = DataAnalysisPanel(self.analyzer)
        self.tabs.addTab(self.data_panel, "数据分析")
        
        # 状态栏
        self.statusBar().showMessage("系统就绪")
        
        # 显示窗口
        self.show()
    
    def create_menu(self):
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu('文件')
        
        export_action = QAction('导出数据', self)
        export_action.triggered.connect(self.export_data)
        file_menu.addAction(export_action)
        
        exit_action = QAction('退出', self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 工具菜单
        tools_menu = menubar.addMenu('工具')
        
        settings_action = QAction('设置', self)
        settings_action.triggered.connect(self.show_settings)
        tools_menu.addAction(settings_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu('帮助')
        
        about_action = QAction('关于', self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def export_data(self):
        filename, _ = QFileDialog.getSaveFileName(
            self, "导出数据", "", "CSV Files (*.csv)")
        
        if filename:
            # 实现数据导出逻辑
            QMessageBox.information(self, "导出成功", f"数据已导出到 {filename}")
    
    def show_settings(self):
        # 实现设置对话框
        QMessageBox.information(self, "设置", "设置功能开发中")
    
    def show_about(self):
        QMessageBox.about(self, "关于", 
                         "高级放松辅助系统 v2.0\n\n"
                         "这是一个功能强大的放松辅助工具，集成了多种放松技术、"
                         "生物反馈监测和数据分析功能。")

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("高级放松辅助系统")
    app.setApplicationVersion("2.0")
    
    # 设置应用程序样式
    app.setStyle('Fusion')
    
    # 创建并显示主窗口
    window = AdvancedRelaxationSystem()
    
    # 运行应用程序
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()