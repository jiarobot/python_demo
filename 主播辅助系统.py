import sys
import os
import json
import time
import threading
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QTextEdit, 
                             QListWidget, QListWidgetItem, QSlider, QSpinBox,
                             QCheckBox, QGroupBox, QTabWidget, QProgressBar,
                             QMessageBox, QFileDialog, QComboBox, QLineEdit,
                             QSplitter, QFrame, QSystemTrayIcon, QMenu, QAction)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread, QSettings
from PyQt5.QtGui import QIcon, QFont, QPalette, QColor, QPixmap
from PyQt5.QtMultimedia import QSound
import pyautogui
import pyperclip
import keyboard
from PIL import Image, ImageDraw, ImageFont
import requests
from bs4 import BeautifulSoup
import qrcode
import speech_recognition as sr
from gtts import gTTS
import pygame
import random

# 语音识别线程
class SpeechRecognitionThread(QThread):
    recognized = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.is_listening = False
        
    def run(self):
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source)
            
        while self.is_listening:
            try:
                with self.microphone as source:
                    audio = self.recognizer.listen(source, timeout=1, phrase_time_limit=5)
                text = self.recognizer.recognize_google(audio, language='zh-CN')
                self.recognized.emit(text)
            except sr.WaitTimeoutError:
                pass
            except sr.UnknownValueError:
                pass
            except Exception as e:
                print(f"语音识别错误: {e}")
    
    def start_listening(self):
        self.is_listening = True
        self.start()
    
    def stop_listening(self):
        self.is_listening = False
        self.wait()

# 文本转语音线程
class TextToSpeechThread(QThread):
    finished_speaking = pyqtSignal()
    
    def __init__(self, text, lang='zh'):
        super().__init__()
        self.text = text
        self.lang = lang
        
    def run(self):
        try:
            tts = gTTS(text=self.text, lang=self.lang)
            tts.save('temp_speech.mp3')
            
            pygame.mixer.init()
            pygame.mixer.music.load('temp_speech.mp3')
            pygame.mixer.music.play()
            
            while pygame.mixer.music.get_busy():
                time.sleep(0.1)
                
            pygame.mixer.quit()
            if os.path.exists('temp_speech.mp3'):
                os.remove('temp_speech.mp3')
                
            self.finished_speaking.emit()
        except Exception as e:
            print(f"文本转语音错误: {e}")

# 计时器类
class TimerThread(QThread):
    timer_updated = pyqtSignal(str)
    timer_finished = pyqtSignal()
    
    def __init__(self, duration):
        super().__init__()
        self.duration = duration  # 秒
        self.is_running = False
        self.remaining = duration
        
    def run(self):
        self.is_running = True
        while self.remaining > 0 and self.is_running:
            mins, secs = divmod(self.remaining, 60)
            time_str = f"{mins:02d}:{secs:02d}"
            self.timer_updated.emit(time_str)
            time.sleep(1)
            self.remaining -= 1
            
        if self.remaining <= 0:
            self.timer_finished.emit()
            
    def stop(self):
        self.is_running = False

# 弹幕模拟器
class DanmuSimulator(QThread):
    danmu_received = pyqtSignal(str, str)  # 用户名, 消息
    
    def __init__(self):
        super().__init__()
        self.is_running = False
        self.messages = [
            "主播好厉害！", "666", "这个操作太秀了", "关注了", "礼物走一波",
            "今天播到几点？", "技术太强了", "学到了", "哈哈哈", "太搞笑了",
            "支持主播", "加油", "这是什么游戏？", "主播多大了？", "求带"
        ]
        self.users = ["游客123", "小粉丝", "老观众", "新来的", "铁粉", 
                     "路人甲", "吃瓜群众", "榜一大哥", "神秘人", "小可爱"]
        
    def run(self):
        self.is_running = True
        while self.is_running:
            time.sleep(random.uniform(1, 5))  # 随机间隔
            if self.is_running:
                user = random.choice(self.users)
                message = random.choice(self.messages)
                self.danmu_received.emit(user, message)
                
    def stop(self):
        self.is_running = False

# 主窗口类
class StreamerAssistant(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = QSettings("StreamerTools", "Assistant")
        self.init_ui()
        self.init_timers()
        self.init_speech()
        self.init_danmu()
        self.load_settings()
        
    def init_ui(self):
        self.setWindowTitle("主播辅助系统 - 高级工具库")
        self.setGeometry(100, 100, 1200, 800)
        self.setWindowIcon(QIcon(self.create_icon()))
        
        # 创建中央部件和主布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # 创建左右分割
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        # 左侧功能区
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        splitter.addWidget(left_widget)
        
        # 右侧信息区
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        splitter.addWidget(right_widget)
        
        # 设置分割比例
        splitter.setSizes([700, 500])
        
        # 左侧功能区 - 选项卡
        self.tab_widget = QTabWidget()
        left_layout.addWidget(self.tab_widget)
        
        # 计时器选项卡
        self.init_timer_tab()
        
        # 语音控制选项卡
        self.init_speech_tab()
        
        # 弹幕管理选项卡
        self.init_danmu_tab()
        
        # 快捷键选项卡
        self.init_hotkey_tab()
        
        # 工具选项卡
        self.init_tools_tab()
        
        # 右侧信息区 - 状态显示
        self.init_status_area(right_layout)
        
        # 系统托盘
        self.init_system_tray()
        
        # 应用样式
        self.apply_dark_theme()
        
    def init_timer_tab(self):
        timer_tab = QWidget()
        layout = QVBoxLayout(timer_tab)
        
        # 计时器设置
        timer_group = QGroupBox("计时器设置")
        timer_layout = QVBoxLayout(timer_group)
        
        time_setting_layout = QHBoxLayout()
        time_setting_layout.addWidget(QLabel("时长(分钟):"))
        self.timer_minutes = QSpinBox()
        self.timer_minutes.setRange(1, 120)
        self.timer_minutes.setValue(10)
        time_setting_layout.addWidget(self.timer_minutes)
        time_setting_layout.addStretch()
        
        timer_layout.addLayout(time_setting_layout)
        
        # 计时器控制按钮
        timer_buttons_layout = QHBoxLayout()
        self.start_timer_btn = QPushButton("开始计时")
        self.start_timer_btn.clicked.connect(self.start_timer)
        timer_buttons_layout.addWidget(self.start_timer_btn)
        
        self.stop_timer_btn = QPushButton("停止计时")
        self.stop_timer_btn.clicked.connect(self.stop_timer)
        self.stop_timer_btn.setEnabled(False)
        timer_buttons_layout.addWidget(self.stop_timer_btn)
        
        timer_layout.addLayout(timer_buttons_layout)
        
        # 计时器显示
        self.timer_display = QLabel("10:00")
        self.timer_display.setAlignment(Qt.AlignCenter)
        self.timer_display.setFont(QFont("Arial", 48, QFont.Bold))
        timer_layout.addWidget(self.timer_display)
        
        layout.addWidget(timer_group)
        
        # 倒计时列表
        countdown_group = QGroupBox("倒计时列表")
        countdown_layout = QVBoxLayout(countdown_group)
        
        self.countdown_list = QListWidget()
        countdown_layout.addWidget(self.countdown_list)
        
        add_countdown_layout = QHBoxLayout()
        self.countdown_name = QLineEdit()
        self.countdown_name.setPlaceholderText("事件名称")
        add_countdown_layout.addWidget(self.countdown_name)
        
        self.countdown_date = QLineEdit()
        self.countdown_date.setPlaceholderText("YYYY-MM-DD")
        add_countdown_layout.addWidget(self.countdown_date)
        
        add_countdown_btn = QPushButton("添加")
        add_countdown_btn.clicked.connect(self.add_countdown)
        add_countdown_layout.addWidget(add_countdown_btn)
        
        countdown_layout.addLayout(add_countdown_layout)
        
        layout.addWidget(countdown_group)
        layout.addStretch()
        
        self.tab_widget.addTab(timer_tab, "计时器")
        
    def init_speech_tab(self):
        speech_tab = QWidget()
        layout = QVBoxLayout(speech_tab)
        
        # 语音识别
        speech_recognition_group = QGroupBox("语音识别")
        speech_recognition_layout = QVBoxLayout(speech_recognition_group)
        
        self.speech_status = QLabel("语音识别未启动")
        speech_recognition_layout.addWidget(self.speech_status)
        
        speech_buttons_layout = QHBoxLayout()
        self.start_speech_btn = QPushButton("开始语音识别")
        self.start_speech_btn.clicked.connect(self.start_speech_recognition)
        speech_buttons_layout.addWidget(self.start_speech_btn)
        
        self.stop_speech_btn = QPushButton("停止语音识别")
        self.stop_speech_btn.clicked.connect(self.stop_speech_recognition)
        self.stop_speech_btn.setEnabled(False)
        speech_buttons_layout.addWidget(self.stop_speech_btn)
        
        speech_recognition_layout.addLayout(speech_buttons_layout)
        
        self.recognized_text = QTextEdit()
        self.recognized_text.setPlaceholderText("识别结果将显示在这里...")
        speech_recognition_layout.addWidget(self.recognized_text)
        
        layout.addWidget(speech_recognition_group)
        
        # 文本转语音
        tts_group = QGroupBox("文本转语音")
        tts_layout = QVBoxLayout(tts_group)
        
        self.tts_text = QTextEdit()
        self.tts_text.setPlaceholderText("输入要转换为语音的文本...")
        tts_layout.addWidget(self.tts_text)
        
        tts_buttons_layout = QHBoxLayout()
        self.speak_btn = QPushButton("朗读")
        self.speak_btn.clicked.connect(self.text_to_speech)
        tts_buttons_layout.addWidget(self.speak_btn)
        
        self.stop_speak_btn = QPushButton("停止")
        self.stop_speak_btn.clicked.connect(self.stop_text_to_speech)
        tts_buttons_layout.addWidget(self.stop_speak_btn)
        
        tts_layout.addLayout(tts_buttons_layout)
        
        layout.addWidget(tts_group)
        layout.addStretch()
        
        self.tab_widget.addTab(speech_tab, "语音控制")
        
    def init_danmu_tab(self):
        danmu_tab = QWidget()
        layout = QVBoxLayout(danmu_tab)
        
        # 弹幕显示
        danmu_display_group = QGroupBox("弹幕显示")
        danmu_display_layout = QVBoxLayout(danmu_display_group)
        
        self.danmu_list = QListWidget()
        danmu_display_layout.addWidget(self.danmu_list)
        
        # 弹幕控制
        danmu_control_layout = QHBoxLayout()
        self.start_danmu_btn = QPushButton("开始模拟弹幕")
        self.start_danmu_btn.clicked.connect(self.start_danmu_simulation)
        danmu_control_layout.addWidget(self.start_danmu_btn)
        
        self.stop_danmu_btn = QPushButton("停止模拟")
        self.stop_danmu_btn.clicked.connect(self.stop_danmu_simulation)
        self.stop_danmu_btn.setEnabled(False)
        danmu_control_layout.addWidget(self.stop_danmu_btn)
        
        self.clear_danmu_btn = QPushButton("清空弹幕")
        self.clear_danmu_btn.clicked.connect(self.clear_danmu)
        danmu_control_layout.addWidget(self.clear_danmu_btn)
        
        danmu_display_layout.addLayout(danmu_control_layout)
        
        layout.addWidget(danmu_display_group)
        
        # 自动回复设置
        auto_reply_group = QGroupBox("自动回复设置")
        auto_reply_layout = QVBoxLayout(auto_reply_group)
        
        self.auto_reply_enabled = QCheckBox("启用自动回复")
        auto_reply_layout.addWidget(self.auto_reply_enabled)
        
        self.reply_keywords = QTextEdit()
        self.reply_keywords.setPlaceholderText("每行一个关键词和回复，格式: 关键词->回复内容")
        auto_reply_layout.addWidget(self.reply_keywords)
        
        layout.addWidget(auto_reply_group)
        layout.addStretch()
        
        self.tab_widget.addTab(danmu_tab, "弹幕管理")
        
    def init_hotkey_tab(self):
        hotkey_tab = QWidget()
        layout = QVBoxLayout(hotkey_tab)
        
        # 快捷键设置
        hotkey_group = QGroupBox("快捷键设置")
        hotkey_layout = QVBoxLayout(hotkey_group)
        
        hotkey_list = [
            ("开始/停止计时", "F1"),
            ("开始/停止语音识别", "F2"),
            ("朗读剪贴板", "F3"),
            ("截图", "F4"),
            ("显示/隐藏窗口", "Ctrl+H")
        ]
        
        for action, key in hotkey_list:
            hotkey_item_layout = QHBoxLayout()
            hotkey_item_layout.addWidget(QLabel(action))
            hotkey_item_layout.addStretch()
            hotkey_item_layout.addWidget(QLabel(key))
            hotkey_layout.addLayout(hotkey_item_layout)
        
        # 自定义快捷键
        custom_hotkey_layout = QHBoxLayout()
        custom_hotkey_layout.addWidget(QLabel("自定义:"))
        self.custom_action = QLineEdit()
        self.custom_action.setPlaceholderText("动作描述")
        custom_hotkey_layout.addWidget(self.custom_action)
        
        self.custom_key = QLineEdit()
        self.custom_key.setPlaceholderText("快捷键")
        custom_hotkey_layout.addWidget(self.custom_key)
        
        add_hotkey_btn = QPushButton("添加")
        add_hotkey_btn.clicked.connect(self.add_custom_hotkey)
        custom_hotkey_layout.addWidget(add_hotkey_btn)
        
        hotkey_layout.addLayout(custom_hotkey_layout)
        
        layout.addWidget(hotkey_group)
        
        # 宏命令
        macro_group = QGroupBox("宏命令")
        macro_layout = QVBoxLayout(macro_group)
        
        self.macro_list = QListWidget()
        macro_layout.addWidget(self.macro_list)
        
        macro_buttons_layout = QHBoxLayout()
        record_macro_btn = QPushButton("录制宏")
        record_macro_btn.clicked.connect(self.record_macro)
        macro_buttons_layout.addWidget(record_macro_btn)
        
        play_macro_btn = QPushButton("执行宏")
        play_macro_btn.clicked.connect(self.play_macro)
        macro_buttons_layout.addWidget(play_macro_btn)
        
        save_macro_btn = QPushButton("保存宏")
        save_macro_btn.clicked.connect(self.save_macro)
        macro_buttons_layout.addWidget(save_macro_btn)
        
        macro_layout.addLayout(macro_buttons_layout)
        
        layout.addWidget(macro_group)
        layout.addStretch()
        
        self.tab_widget.addTab(hotkey_tab, "快捷键")
        
    def init_tools_tab(self):
        tools_tab = QWidget()
        layout = QVBoxLayout(tools_tab)
        
        # 截图工具
        screenshot_group = QGroupBox("截图工具")
        screenshot_layout = QVBoxLayout(screenshot_group)
        
        screenshot_buttons_layout = QHBoxLayout()
        fullscreen_screenshot_btn = QPushButton("全屏截图")
        fullscreen_screenshot_btn.clicked.connect(self.take_fullscreen_screenshot)
        screenshot_buttons_layout.addWidget(fullscreen_screenshot_btn)
        
        region_screenshot_btn = QPushButton("区域截图")
        region_screenshot_btn.clicked.connect(self.take_region_screenshot)
        screenshot_buttons_layout.addWidget(region_screenshot_btn)
        
        screenshot_layout.addLayout(screenshot_buttons_layout)
        
        layout.addWidget(screenshot_group)
        
        # 二维码生成
        qr_group = QGroupBox("二维码生成")
        qr_layout = QVBoxLayout(qr_group)
        
        self.qr_text = QTextEdit()
        self.qr_text.setPlaceholderText("输入要生成二维码的文本或URL...")
        qr_layout.addWidget(self.qr_text)
        
        generate_qr_btn = QPushButton("生成二维码")
        generate_qr_btn.clicked.connect(self.generate_qr_code)
        qr_layout.addWidget(generate_qr_btn)
        
        layout.addWidget(qr_group)
        
        # 随机抽奖
        lottery_group = QGroupBox("随机抽奖")
        lottery_layout = QVBoxLayout(lottery_group)
        
        self.lottery_candidates = QTextEdit()
        self.lottery_candidates.setPlaceholderText("每行一个候选人...")
        lottery_layout.addWidget(self.lottery_candidates)
        
        lottery_buttons_layout = QHBoxLayout()
        draw_lottery_btn = QPushButton("抽取一名幸运观众")
        draw_lottery_btn.clicked.connect(self.draw_lottery)
        lottery_buttons_layout.addWidget(draw_lottery_btn)
        
        self.lottery_result = QLabel("等待抽奖...")
        lottery_buttons_layout.addWidget(self.lottery_result)
        
        lottery_layout.addLayout(lottery_buttons_layout)
        
        layout.addWidget(lottery_group)
        layout.addStretch()
        
        self.tab_widget.addTab(tools_tab, "工具")
        
    def init_status_area(self, layout):
        # 系统状态
        status_group = QGroupBox("系统状态")
        status_layout = QVBoxLayout(status_group)
        
        self.cpu_usage = QProgressBar()
        self.cpu_usage.setFormat("CPU使用率: %p%")
        status_layout.addWidget(self.cpu_usage)
        
        self.memory_usage = QProgressBar()
        self.memory_usage.setFormat("内存使用率: %p%")
        status_layout.addWidget(self.memory_usage)
        
        self.network_status = QLabel("网络: 正常")
        status_layout.addWidget(self.network_status)
        
        layout.addWidget(status_group)
        
        # 直播统计
        stats_group = QGroupBox("直播统计")
        stats_layout = QVBoxLayout(stats_group)
        
        self.stream_duration = QLabel("直播时长: 00:00:00")
        stats_layout.addWidget(self.stream_duration)
        
        self.viewer_count = QLabel("观众人数: 0")
        stats_layout.addWidget(self.viewer_count)
        
        self.danmu_count = QLabel("弹幕数量: 0")
        stats_layout.addWidget(self.danmu_count)
        
        layout.addWidget(stats_group)
        
        # 快速操作
        quick_actions_group = QGroupBox("快速操作")
        quick_actions_layout = QVBoxLayout(quick_actions_group)
        
        quick_buttons = [
            ("播放音效", self.play_sound_effect),
            ("复制感谢语", self.copy_thanks_message),
            ("显示时间", self.show_current_time),
            ("清空剪贴板", self.clear_clipboard)
        ]
        
        for text, slot in quick_buttons:
            btn = QPushButton(text)
            btn.clicked.connect(slot)
            quick_actions_layout.addWidget(btn)
        
        layout.addWidget(quick_actions_group)
        
        # 日志显示
        log_group = QGroupBox("系统日志")
        log_layout = QVBoxLayout(log_group)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)
        
        layout.addWidget(log_group)
        
        layout.addStretch()
        
    def init_system_tray(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
            
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon(self.create_icon()))
        
        tray_menu = QMenu()
        
        show_action = QAction("显示", self)
        show_action.triggered.connect(self.show)
        tray_menu.addAction(show_action)
        
        hide_action = QAction("隐藏", self)
        hide_action.triggered.connect(self.hide)
        tray_menu.addAction(hide_action)
        
        tray_menu.addSeparator()
        
        quit_action = QAction("退出", self)
        quit_action.triggered.connect(self.quit_application)
        tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.tray_icon_activated)
        self.tray_icon.show()
        
    def init_timers(self):
        # 系统状态更新定时器
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_system_status)
        self.status_timer.start(2000)  # 每2秒更新一次
        
        # 直播时长计时器
        self.stream_timer = QTimer()
        self.stream_timer.timeout.connect(self.update_stream_duration)
        self.stream_start_time = None
        
        # 计时器线程
        self.timer_thread = None
        
    def init_speech(self):
        self.speech_thread = SpeechRecognitionThread()
        self.speech_thread.recognized.connect(self.on_speech_recognized)
        
        self.tts_thread = None
        
    def init_danmu(self):
        self.danmu_simulator = DanmuSimulator()
        self.danmu_simulator.danmu_received.connect(self.on_danmu_received)
        self.danmu_count_value = 0
        
    def load_settings(self):
        # 加载保存的设置
        geometry = self.settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
            
        window_state = self.settings.value("windowState")
        if window_state:
            self.restoreState(window_state)
            
    def save_settings(self):
        # 保存设置
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("windowState", self.saveState())
        
    def apply_dark_theme(self):
        # 应用暗色主题
        dark_palette = QPalette()
        dark_palette.setColor(QPalette.Window, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.WindowText, Qt.white)
        dark_palette.setColor(QPalette.Base, QColor(25, 25, 25))
        dark_palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ToolTipBase, Qt.white)
        dark_palette.setColor(QPalette.ToolTipText, Qt.white)
        dark_palette.setColor(QPalette.Text, Qt.white)
        dark_palette.setColor(QPalette.Button, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ButtonText, Qt.white)
        dark_palette.setColor(QPalette.BrightText, Qt.red)
        dark_palette.setColor(QPalette.Link, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.HighlightedText, Qt.black)
        
        self.setPalette(dark_palette)
        self.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #555;
                border-radius: 5px;
                margin-top: 1ex;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #FFF;
            }
            QTabWidget::pane {
                border: 1px solid #555;
                top: -1px;
            }
            QTabBar::tab {
                background: #444;
                color: #FFF;
                padding: 8px 20px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background: #555;
            }
        """)
        
    def create_icon(self):
        # 创建一个简单的程序图标
        img = Image.new('RGB', (64, 64), color='red')
        d = ImageDraw.Draw(img)
        d.text((10, 10), "SA", fill='white')
        img.save('temp_icon.png')
        return 'temp_icon.png'
        
    # 计时器功能
    def start_timer(self):
        minutes = self.timer_minutes.value()
        self.timer_thread = TimerThread(minutes * 60)
        self.timer_thread.timer_updated.connect(self.update_timer_display)
        self.timer_thread.timer_finished.connect(self.timer_finished)
        self.timer_thread.start()
        
        self.start_timer_btn.setEnabled(False)
        self.stop_timer_btn.setEnabled(True)
        
        self.log_message(f"计时器启动: {minutes}分钟")
        
    def stop_timer(self):
        if self.timer_thread:
            self.timer_thread.stop()
            self.timer_thread.wait()
            self.timer_thread = None
            
        self.start_timer_btn.setEnabled(True)
        self.stop_timer_btn.setEnabled(False)
        self.timer_display.setText(f"{self.timer_minutes.value():02d}:00")
        
        self.log_message("计时器已停止")
        
    def update_timer_display(self, time_str):
        self.timer_display.setText(time_str)
        
    def timer_finished(self):
        self.timer_display.setText("时间到!")
        self.start_timer_btn.setEnabled(True)
        self.stop_timer_btn.setEnabled(False)
        
        # 播放提示音
        QSound.play("system.wav")  # 需要准备一个提示音文件
        
        self.log_message("计时器时间到")
        
    def add_countdown(self):
        name = self.countdown_name.text()
        date_str = self.countdown_date.text()
        
        if not name or not date_str:
            QMessageBox.warning(self, "输入错误", "请填写事件名称和日期")
            return
            
        try:
            target_date = datetime.strptime(date_str, "%Y-%m-%d")
            today = datetime.now()
            days_left = (target_date - today).days
            
            if days_left < 0:
                QMessageBox.warning(self, "日期错误", "目标日期不能是过去的时间")
                return
                
            item_text = f"{name}: 还有{days_left}天 ({date_str})"
            self.countdown_list.addItem(item_text)
            
            self.countdown_name.clear()
            self.countdown_date.clear()
            
            self.log_message(f"添加倒计时: {item_text}")
        except ValueError:
            QMessageBox.warning(self, "格式错误", "日期格式应为 YYYY-MM-DD")
            
    # 语音识别功能
    def start_speech_recognition(self):
        self.speech_thread.start_listening()
        self.speech_status.setText("语音识别中...")
        self.start_speech_btn.setEnabled(False)
        self.stop_speech_btn.setEnabled(True)
        
        self.log_message("语音识别已启动")
        
    def stop_speech_recognition(self):
        self.speech_thread.stop_listening()
        self.speech_status.setText("语音识别未启动")
        self.start_speech_btn.setEnabled(True)
        self.stop_speech_btn.setEnabled(False)
        
        self.log_message("语音识别已停止")
        
    def on_speech_recognized(self, text):
        self.recognized_text.append(f"[{datetime.now().strftime('%H:%M:%S')}] {text}")
        
        # 自动回复功能
        if self.auto_reply_enabled.isChecked():
            self.process_auto_reply(text)
            
    def text_to_speech(self):
        text = self.tts_text.toPlainText()
        if not text:
            QMessageBox.warning(self, "输入错误", "请输入要朗读的文本")
            return
            
        self.tts_thread = TextToSpeechThread(text)
        self.tts_thread.finished_speaking.connect(self.tts_finished)
        self.tts_thread.start()
        
        self.speak_btn.setEnabled(False)
        self.stop_speak_btn.setEnabled(True)
        
        self.log_message("开始文本转语音")
        
    def stop_text_to_speech(self):
        if self.tts_thread and self.tts_thread.isRunning():
            # 停止播放
            if pygame.mixer.get_init():
                pygame.mixer.music.stop()
                pygame.mixer.quit()
                
        self.speak_btn.setEnabled(True)
        self.stop_speak_btn.setEnabled(False)
        
        self.log_message("文本转语音已停止")
        
    def tts_finished(self):
        self.speak_btn.setEnabled(True)
        self.stop_speak_btn.setEnabled(False)
        
    def process_auto_reply(self, message):
        # 处理自动回复
        keywords_text = self.reply_keywords.toPlainText()
        if not keywords_text:
            return
            
        for line in keywords_text.split('\n'):
            if '->' in line:
                keyword, reply = line.split('->', 1)
                if keyword.strip() in message:
                    # 自动回复
                    self.tts_text.setText(reply.strip())
                    self.text_to_speech()
                    self.log_message(f"自动回复: {reply.strip()}")
                    break
                    
    # 弹幕功能
    def start_danmu_simulation(self):
        self.danmu_simulator.start()
        self.start_danmu_btn.setEnabled(False)
        self.stop_danmu_btn.setEnabled(True)
        
        self.log_message("弹幕模拟已启动")
        
    def stop_danmu_simulation(self):
        self.danmu_simulator.stop()
        self.start_danmu_btn.setEnabled(True)
        self.stop_danmu_btn.setEnabled(False)
        
        self.log_message("弹幕模拟已停止")
        
    def on_danmu_received(self, user, message):
        item_text = f"[{datetime.now().strftime('%H:%M:%S')}] {user}: {message}"
        self.danmu_list.addItem(item_text)
        
        # 滚动到最后一条
        self.danmu_list.scrollToBottom()
        
        # 更新弹幕计数
        self.danmu_count_value += 1
        self.danmu_count.setText(f"弹幕数量: {self.danmu_count_value}")
        
    def clear_danmu(self):
        self.danmu_list.clear()
        self.danmu_count_value = 0
        self.danmu_count.setText("弹幕数量: 0")
        
        self.log_message("弹幕已清空")
        
    # 快捷键功能
    def add_custom_hotkey(self):
        action = self.custom_action.text()
        key = self.custom_key.text()
        
        if not action or not key:
            QMessageBox.warning(self, "输入错误", "请填写动作和快捷键")
            return
            
        # 这里可以添加实际的快捷键注册逻辑
        self.log_message(f"添加快捷键: {action} -> {key}")
        
        self.custom_action.clear()
        self.custom_key.clear()
        
    def record_macro(self):
        self.log_message("开始录制宏命令")
        # 这里可以添加宏录制逻辑
        
    def play_macro(self):
        self.log_message("执行宏命令")
        # 这里可以添加宏执行逻辑
        
    def save_macro(self):
        self.log_message("保存宏命令")
        # 这里可以添加宏保存逻辑
        
    # 工具功能
    def take_fullscreen_screenshot(self):
        try:
            screenshot = pyautogui.screenshot()
            filename = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            screenshot.save(filename)
            self.log_message(f"全屏截图已保存: {filename}")
        except Exception as e:
            self.log_message(f"截图失败: {str(e)}")
            
    def take_region_screenshot(self):
        self.log_message("区域截图功能暂未实现")
        # 这里可以添加区域截图逻辑
        
    def generate_qr_code(self):
        text = self.qr_text.toPlainText()
        if not text:
            QMessageBox.warning(self, "输入错误", "请输入要生成二维码的文本")
            return
            
        try:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(text)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            filename = f"qrcode_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            img.save(filename)
            
            self.log_message(f"二维码已生成: {filename}")
        except Exception as e:
            self.log_message(f"二维码生成失败: {str(e)}")
            
    def draw_lottery(self):
        candidates_text = self.lottery_candidates.toPlainText()
        if not candidates_text:
            QMessageBox.warning(self, "输入错误", "请输入候选人列表")
            return
            
        candidates = [c.strip() for c in candidates_text.split('\n') if c.strip()]
        if not candidates:
            QMessageBox.warning(self, "输入错误", "没有有效的候选人")
            return
            
        winner = random.choice(candidates)
        self.lottery_result.setText(f"中奖者: {winner}")
        
        self.log_message(f"抽奖结果: {winner}")
        
    # 快速操作功能
    def play_sound_effect(self):
        self.log_message("播放音效")
        # 这里可以添加音效播放逻辑
        
    def copy_thanks_message(self):
        thanks_messages = [
            "感谢大家的支持!",
            "谢谢礼物!",
            "感谢关注!",
            "谢谢大家的弹幕!"
        ]
        message = random.choice(thanks_messages)
        pyperclip.copy(message)
        self.log_message(f"已复制感谢语: {message}")
        
    def show_current_time(self):
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.log_message(f"当前时间: {current_time}")
        
    def clear_clipboard(self):
        pyperclip.copy("")
        self.log_message("剪贴板已清空")
        
    # 系统状态更新
    def update_system_status(self):
        # 模拟系统状态更新
        self.cpu_usage.setValue(random.randint(10, 80))
        self.memory_usage.setValue(random.randint(20, 90))
        
        # 模拟观众人数变化
        if self.stream_start_time:
            viewer_change = random.randint(-5, 10)
            current_viewers = int(self.viewer_count.text().split(": ")[1])
            new_viewers = max(0, current_viewers + viewer_change)
            self.viewer_count.setText(f"观众人数: {new_viewers}")
            
    def update_stream_duration(self):
        if self.stream_start_time:
            duration = datetime.now() - self.stream_start_time
            hours, remainder = divmod(duration.total_seconds(), 3600)
            minutes, seconds = divmod(remainder, 60)
            self.stream_duration.setText(f"直播时长: {int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}")
            
    def start_stream(self):
        self.stream_start_time = datetime.now()
        self.stream_timer.start(1000)  # 每秒更新一次
        self.log_message("直播开始")
        
    def stop_stream(self):
        self.stream_timer.stop()
        self.stream_start_time = None
        self.stream_duration.setText("直播时长: 00:00:00")
        self.log_message("直播结束")
        
    # 系统托盘功能
    def tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            if self.isVisible():
                self.hide()
            else:
                self.show()
                self.activateWindow()
                
    def closeEvent(self, event):
        # 最小化到系统托盘而不是退出
        if self.tray_icon.isVisible():
            self.hide()
            event.ignore()
        else:
            self.quit_application()
            
    def quit_application(self):
        # 停止所有线程
        if self.timer_thread and self.timer_thread.isRunning():
            self.timer_thread.stop()
            self.timer_thread.wait()
            
        if self.speech_thread.is_listening:
            self.speech_thread.stop_listening()
            
        if self.danmu_simulator.is_running:
            self.danmu_simulator.stop()
            self.danmu_simulator.wait()
            
        # 保存设置
        self.save_settings()
        
        # 退出程序
        QApplication.quit()
        
    def log_message(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )

# 主函数
def main():
    app = QApplication(sys.argv)
    app.setApplicationName("主播辅助系统")
    app.setApplicationVersion("1.0")
    
    # 设置高DPI支持
    app.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    app.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    window = StreamerAssistant()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()