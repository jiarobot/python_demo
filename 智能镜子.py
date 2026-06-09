import sys
import os
import json
import time
import threading
from datetime import datetime, timedelta
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QLabel, QPushButton, QTextEdit, 
                            QListWidget, QListWidgetItem, QSplitter, 
                            QTabWidget, QProgressBar, QSlider, QSpinBox,
                            QCheckBox, QComboBox, QLineEdit, QMessageBox,
                            QFileDialog, QCalendarWidget, QTimeEdit)
from PyQt5.QtCore import Qt, QTimer, QDateTime, pyqtSignal, QThread, QSize
from PyQt5.QtGui import QFont, QPalette, QColor, QPixmap, QIcon, QMovie
import requests
import sqlite3
import logging
from logging.handlers import RotatingFileHandler
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import pyttsx3
import speech_recognition as sr
import platform
import psutil
import GPUtil

# 设置日志
def setup_logging():
    logger = logging.getLogger('SmartMirror')
    logger.setLevel(logging.DEBUG)
    
    # 创建文件处理器，限制文件大小为10MB，保留5个备份
    file_handler = RotatingFileHandler(
        'smart_mirror.log', 
        maxBytes=10*1024*1024, 
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    
    # 创建控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # 创建格式化器
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # 添加处理器到日志器
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

logger = setup_logging()

class VoiceAssistant(QThread):
    """语音助手线程"""
    speech_detected = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.is_listening = False
        self.engine = pyttsx3.init()
        
        # 设置语音属性
        voices = self.engine.getProperty('voices')
        if voices:
            self.engine.setProperty('voice', voices[0].id)
        self.engine.setProperty('rate', 150)
        
    def run(self):
        self.is_listening = True
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source)
            
        while self.is_listening:
            try:
                with self.microphone as source:
                    audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=10)
                
                text = self.recognizer.recognize_google(audio, language='zh-CN')
                self.speech_detected.emit(text)
            except sr.WaitTimeoutError:
                continue
            except sr.UnknownValueError:
                continue
            except Exception as e:
                logger.error(f"语音识别错误: {e}")
                
    def stop_listening(self):
        self.is_listening = False
        
    def speak(self, text):
        """文本转语音"""
        def _speak():
            self.engine.say(text)
            self.engine.runAndWait()
            
        thread = threading.Thread(target=_speak)
        thread.daemon = True
        thread.start()

class CameraManager(QThread):
    """摄像头管理器"""
    frame_ready = pyqtSignal(np.ndarray)
    face_detected = pyqtSignal(list)
    
    def __init__(self):
        super().__init__()
        self.camera = None
        self.is_running = False
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
        
    def start_camera(self, camera_id=0):
        self.camera = cv2.VideoCapture(camera_id)
        self.is_running = True
        self.start()
        
    def stop_camera(self):
        self.is_running = False
        if self.camera:
            self.camera.release()
            
    def run(self):
        while self.is_running:
            ret, frame = self.camera.read()
            if ret:
                # 发送帧数据
                self.frame_ready.emit(frame)
                
                # 人脸检测
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = self.face_cascade.detectMultiScale(gray, 1.3, 5)
                if len(faces) > 0:
                    self.face_detected.emit(faces.tolist())
                    
class WeatherService:
    """天气服务"""
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "http://api.openweathermap.org/data/2.5"
        
    def get_current_weather(self, city):
        """获取当前天气"""
        try:
            url = f"{self.base_url}/weather?q={city}&appid={self.api_key}&units=metric&lang=zh_cn"
            response = requests.get(url)
            data = response.json()
            
            if response.status_code == 200:
                return {
                    'temperature': data['main']['temp'],
                    'description': data['weather'][0]['description'],
                    'humidity': data['main']['humidity'],
                    'wind_speed': data['wind']['speed'],
                    'city': data['name']
                }
            else:
                logger.error(f"天气API错误: {data.get('message', 'Unknown error')}")
                return None
        except Exception as e:
            logger.error(f"获取天气信息错误: {e}")
            return None
            
    def get_forecast(self, city):
        """获取天气预报"""
        try:
            url = f"{self.base_url}/forecast?q={city}&appid={self.api_key}&units=metric&lang=zh_cn"
            response = requests.get(url)
            data = response.json()
            
            if response.status_code == 200:
                return data['list'][:5]  # 返回最近5个预报
            else:
                return None
        except Exception as e:
            logger.error(f"获取天气预报错误: {e}")
            return None

class DatabaseManager:
    """数据库管理器"""
    def __init__(self, db_path="smart_mirror.db"):
        self.db_path = db_path
        self.init_database()
        
    def init_database(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建用户设置表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        
        # 创建日程表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS schedules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                start_time DATETIME NOT NULL,
                end_time DATETIME,
                reminder_minutes INTEGER DEFAULT 0
            )
        ''')
        
        # 创建新闻偏好表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS news_preferences (
                category TEXT PRIMARY KEY,
                enabled BOOLEAN DEFAULT 1
            )
        ''')
        
        conn.commit()
        conn.close()
        
    def get_setting(self, key, default=None):
        """获取设置"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM user_settings WHERE key=?", (key,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else default
        
    def set_setting(self, key, value):
        """保存设置"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO user_settings (key, value) VALUES (?, ?)",
            (key, value)
        )
        conn.commit()
        conn.close()

class NewsService:
    """新闻服务"""
    def __init__(self, api_key):
        self.api_key = api_key
        
    def get_headlines(self, category='general', country='cn'):
        """获取新闻头条"""
        try:
            url = f"https://newsapi.org/v2/top-headlines"
            params = {
                'country': country,
                'category': category,
                'apiKey': self.api_key
            }
            response = requests.get(url, params=params)
            data = response.json()
            
            if data['status'] == 'ok':
                return data['articles'][:10]  # 返回前10条新闻
            else:
                return []
        except Exception as e:
            logger.error(f"获取新闻错误: {e}")
            return []

class SystemMonitor:
    """系统监控"""
    @staticmethod
    def get_cpu_usage():
        return psutil.cpu_percent(interval=1)
    
    @staticmethod
    def get_memory_usage():
        memory = psutil.virtual_memory()
        return {
            'percent': memory.percent,
            'used': memory.used // (1024**3),  # GB
            'total': memory.total // (1024**3)  # GB
        }
    
    @staticmethod
    def get_gpu_usage():
        try:
            gpus = GPUtil.getGPUs()
            if gpus:
                gpu = gpus[0]
                return {
                    'load': gpu.load * 100,
                    'memory_used': gpu.memoryUsed,
                    'memory_total': gpu.memoryTotal
                }
            return None
        except:
            return None
    
    @staticmethod
    def get_disk_usage():
        disk = psutil.disk_usage('/')
        return {
            'percent': disk.percent,
            'used': disk.used // (1024**3),  # GB
            'total': disk.total // (1024**3)  # GB
        }

class SmartMirrorWidget(QWidget):
    """智能镜主界面组件"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = DatabaseManager()
        self.voice_assistant = VoiceAssistant()
        self.camera_manager = CameraManager()
        self.system_monitor = SystemMonitor()
        
        # 初始化服务（需要设置API密钥）
        self.weather_service = WeatherService("your_weather_api_key")
        self.news_service = NewsService("your_news_api_key")
        
        self.init_ui()
        self.setup_connections()
        self.load_settings()
        
    def init_ui(self):
        """初始化用户界面"""
        main_layout = QHBoxLayout()
        
        # 左侧信息面板
        left_panel = QVBoxLayout()
        
        # 时间和日期
        self.time_label = QLabel()
        self.time_label.setAlignment(Qt.AlignCenter)
        self.time_label.setStyleSheet("font-size: 48px; color: white;")
        
        self.date_label = QLabel()
        self.date_label.setAlignment(Qt.AlignCenter)
        self.date_label.setStyleSheet("font-size: 24px; color: white;")
        
        # 天气信息
        self.weather_label = QLabel("天气信息加载中...")
        self.weather_label.setStyleSheet("font-size: 18px; color: white;")
        
        # 系统状态
        self.system_status_label = QLabel()
        self.system_status_label.setStyleSheet("font-size: 14px; color: white;")
        
        left_panel.addWidget(self.time_label)
        left_panel.addWidget(self.date_label)
        left_panel.addWidget(self.weather_label)
        left_panel.addWidget(self.system_status_label)
        left_panel.addStretch()
        
        # 右侧功能面板
        right_panel = QVBoxLayout()
        
        # 新闻显示
        self.news_list = QListWidget()
        self.news_list.setStyleSheet("""
            QListWidget {
                background: rgba(0, 0, 0, 0.5);
                color: white;
                border: none;
                font-size: 14px;
            }
            QListWidget::item {
                padding: 5px;
                border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            }
        """)
        
        # 语音状态
        self.voice_status_label = QLabel("语音助手: 离线")
        self.voice_status_label.setStyleSheet("font-size: 14px; color: white;")
        
        right_panel.addWidget(QLabel("最新新闻"))
        right_panel.addWidget(self.news_list)
        right_panel.addWidget(self.voice_status_label)
        
        # 组合布局
        main_layout.addLayout(left_panel)
        main_layout.addLayout(right_panel)
        main_layout.setStretchFactor(left_panel, 2)
        main_layout.setStretchFactor(right_panel, 1)
        
        self.setLayout(main_layout)
        
        # 设置背景为半透明黑色
        self.setStyleSheet("background: rgba(0, 0, 0, 0.7);")
        
        # 启动定时器
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_display)
        self.update_timer.start(1000)  # 每秒更新
        
        self.weather_timer = QTimer()
        self.weather_timer.timeout.connect(self.update_weather)
        self.weather_timer.start(300000)  # 每5分钟更新天气
        
        self.news_timer = QTimer()
        self.news_timer.timeout.connect(self.update_news)
        self.news_timer.start(600000)  # 每10分钟更新新闻
        
        self.system_timer = QTimer()
        self.system_timer.timeout.connect(self.update_system_status)
        self.system_timer.start(5000)  # 每5秒更新系统状态
        
    def setup_connections(self):
        """设置信号连接"""
        self.voice_assistant.speech_detected.connect(self.handle_speech)
        self.camera_manager.frame_ready.connect(self.handle_camera_frame)
        self.camera_manager.face_detected.connect(self.handle_face_detection)
        
    def load_settings(self):
        """加载用户设置"""
        self.city = self.db.get_setting('city', 'Beijing')
        self.news_categories = self.db.get_setting('news_categories', 'general,technology').split(',')
        
    def update_display(self):
        """更新显示内容"""
        # 更新时间
        current_time = QDateTime.currentDateTime()
        self.time_label.setText(current_time.toString("hh:mm:ss"))
        self.date_label.setText(current_time.toString("yyyy年MM月dd日 dddd"))
        
    def update_weather(self):
        """更新天气信息"""
        if self.weather_service:
            weather = self.weather_service.get_current_weather(self.city)
            if weather:
                text = f"{weather['city']} | {weather['temperature']}°C | {weather['description']}"
                self.weather_label.setText(text)
                
    def update_news(self):
        """更新新闻"""
        if self.news_service:
            self.news_list.clear()
            for category in self.news_categories:
                articles = self.news_service.get_headlines(category)
                for article in articles:
                    title = article['title']
                    if len(title) > 50:
                        title = title[:50] + "..."
                    item = QListWidgetItem(f"• {title}")
                    self.news_list.addItem(item)
                    
    def update_system_status(self):
        """更新系统状态"""
        cpu_usage = self.system_monitor.get_cpu_usage()
        memory = self.system_monitor.get_memory_usage()
        
        status_text = f"CPU: {cpu_usage}% | 内存: {memory['percent']}%"
        
        gpu_info = self.system_monitor.get_gpu_usage()
        if gpu_info:
            status_text += f" | GPU: {gpu_info['load']:.1f}%"
            
        self.system_status_label.setText(status_text)
        
    def handle_speech(self, text):
        """处理语音输入"""
        self.voice_status_label.setText(f"语音输入: {text}")
        
        # 简单的语音命令处理
        if "天气" in text:
            self.update_weather()
            self.voice_assistant.speak(f"已更新{self.city}的天气信息")
        elif "新闻" in text:
            self.update_news()
            self.voice_assistant.speak("已更新新闻")
        elif "时间" in text:
            current_time = QDateTime.currentDateTime().toString("hh点mm分")
            self.voice_assistant.speak(f"当前时间是{current_time}")
            
    def handle_camera_frame(self, frame):
        """处理摄像头帧"""
        # 这里可以添加图像处理逻辑
        pass
        
    def handle_face_detection(self, faces):
        """处理人脸检测"""
        if len(faces) > 0:
            # 检测到人脸，可以触发相应操作
            pass
            
    def start_voice_assistant(self):
        """启动语音助手"""
        self.voice_assistant.start()
        self.voice_status_label.setText("语音助手: 在线")
        
    def stop_voice_assistant(self):
        """停止语音助手"""
        self.voice_assistant.stop_listening()
        self.voice_status_label.setText("语音助手: 离线")
        
    def start_camera(self):
        """启动摄像头"""
        self.camera_manager.start_camera()
        
    def stop_camera(self):
        """停止摄像头"""
        self.camera_manager.stop_camera()

class SettingsDialog(QWidget):
    """设置对话框"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = DatabaseManager()
        self.init_ui()
        self.load_settings()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 城市设置
        city_layout = QHBoxLayout()
        city_layout.addWidget(QLabel("城市:"))
        self.city_input = QLineEdit()
        city_layout.addWidget(self.city_input)
        layout.addLayout(city_layout)
        
        # 新闻类别设置
        layout.addWidget(QLabel("新闻类别:"))
        self.news_checkboxes = {}
        categories = ['general', 'technology', 'sports', 'business', 'entertainment']
        for category in categories:
            checkbox = QCheckBox(category.capitalize())
            self.news_checkboxes[category] = checkbox
            layout.addWidget(checkbox)
            
        # 保存按钮
        save_btn = QPushButton("保存设置")
        save_btn.clicked.connect(self.save_settings)
        layout.addWidget(save_btn)
        
        self.setLayout(layout)
        
    def load_settings(self):
        """加载设置"""
        city = self.db.get_setting('city', 'Beijing')
        self.city_input.setText(city)
        
        enabled_categories = self.db.get_setting('news_categories', 'general,technology').split(',')
        for category, checkbox in self.news_checkboxes.items():
            checkbox.setChecked(category in enabled_categories)
            
    def save_settings(self):
        """保存设置"""
        city = self.city_input.text()
        self.db.set_setting('city', city)
        
        enabled_categories = []
        for category, checkbox in self.news_checkboxes.items():
            if checkbox.isChecked():
                enabled_categories.append(category)
                
        self.db.set_setting('news_categories', ','.join(enabled_categories))
        QMessageBox.information(self, "成功", "设置已保存")

class SmartMirrorMainWindow(QMainWindow):
    """智能镜主窗口"""
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        # 设置窗口属性
        self.setWindowTitle("智能镜系统")
        self.showFullScreen()  # 全屏显示
        
        # 创建中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        layout = QVBoxLayout(central_widget)
        
        # 创建标签页
        tab_widget = QTabWidget()
        
        # 主界面标签
        self.mirror_widget = SmartMirrorWidget()
        tab_widget.addTab(self.mirror_widget, "智能镜")
        
        # 设置标签
        self.settings_widget = SettingsDialog()
        tab_widget.addTab(self.settings_widget, "设置")
        
        layout.addWidget(tab_widget)
        
        # 创建状态栏
        self.statusBar().showMessage("智能镜系统已启动")
        
        # 添加工具栏
        self.create_toolbar()
        
    def create_toolbar(self):
        """创建工具栏"""
        toolbar = self.addToolBar("主工具栏")
        
        # 语音控制按钮
        voice_start_btn = QPushButton("启动语音")
        voice_start_btn.clicked.connect(self.mirror_widget.start_voice_assistant)
        toolbar.addWidget(voice_start_btn)
        
        voice_stop_btn = QPushButton("停止语音")
        voice_stop_btn.clicked.connect(self.mirror_widget.stop_voice_assistant)
        toolbar.addWidget(voice_stop_btn)
        
        # 摄像头控制按钮
        camera_start_btn = QPushButton("启动摄像头")
        camera_start_btn.clicked.connect(self.mirror_widget.start_camera)
        toolbar.addWidget(camera_start_btn)
        
        camera_stop_btn = QPushButton("停止摄像头")
        camera_stop_btn.clicked.connect(self.mirror_widget.stop_camera)
        toolbar.addWidget(camera_stop_btn)
        
        # 退出按钮
        exit_btn = QPushButton("退出")
        exit_btn.clicked.connect(self.close)
        toolbar.addWidget(exit_btn)
        
    def keyPressEvent(self, event):
        """键盘事件处理"""
        if event.key() == Qt.Key_Escape:
            self.close()
        elif event.key() == Qt.Key_F11:
            if self.isFullScreen():
                self.showNormal()
            else:
                self.showFullScreen()

def main():
    # 创建应用
    app = QApplication(sys.argv)
    
    # 设置应用样式
    app.setStyle('Fusion')
    
    # 创建并显示主窗口
    window = SmartMirrorMainWindow()
    window.show()
    
    # 运行应用
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()