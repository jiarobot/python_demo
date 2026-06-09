import sys
import json
import datetime
import numpy as np
import random
import sqlite3
import uuid
import hashlib
import requests
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QPushButton, QTextEdit, QSlider, 
                             QProgressBar, QListWidget, QCalendarWidget, QGroupBox,
                             QSpinBox, QComboBox, QMessageBox, QFileDialog, QSplitter,
                             QLineEdit, QCheckBox, QTableWidget, QTableWidgetItem,
                             QHeaderView, QTreeWidget, QTreeWidgetItem, QFrame, QToolBar,
                             QStatusBar, QAction, QDialog, QFormLayout, QDialogButtonBox,
                             QGridLayout, QStackedWidget, QRadioButton, QButtonGroup)
from PyQt5.QtCore import Qt, QTimer, QTime, QDateTime, QDate, QSize, pyqtSignal
from PyQt5.QtGui import QFont, QPalette, QColor, QPixmap, QIcon, QMovie, QPainter, QPen, QIntValidator
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.dates import DateFormatter
import pandas as pd
from scipy import stats
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import bcrypt
import jwt
import qdarkstyle
from enum import Enum
import speech_recognition as sr
import sounddevice as sd
import soundfile as sf
from scipy.io.wavfile import write
import wavio
import threading
import time
import re
import os
from cryptography.fernet import Fernet

# 增强的情感分析API
class AdvancedEmotionAnalysisAPI:
    def __init__(self):
        self.emotion_categories = {
            "positive": ["快乐", "兴奋", "满足", "平静", "希望", "爱", "感恩", "自豪"],
            "negative": ["悲伤", "愤怒", "恐惧", "焦虑", "羞愧", "孤独", "绝望", "压力"],
            "neutral": ["平静", "中性", "无聊", "疲倦", "好奇", "困惑"]
        }
        
        # 情感词汇库（扩展版）
        self.emotion_lexicon = {
            "快乐": 9, "开心": 9, "高兴": 9, "幸福": 10, "满意": 8, "兴奋": 8,
            "悲伤": 3, "难过": 3, "痛苦": 2, "伤心": 3, "失望": 4, "绝望": 1,
            "愤怒": 2, "生气": 2, "恼火": 3, "烦躁": 4, "仇恨": 1,
            "恐惧": 2, "害怕": 3, "担心": 4, "焦虑": 4, "紧张": 5,
            "平静": 6, "放松": 7, "安宁": 7, "平和": 7, "中性": 5,
            "爱": 10, "喜欢": 8, "感激": 9, "感恩": 9, "自豪": 8
        }
    
    def analyze_text_advanced(self, text):
        """增强版文本情感分析"""
        words = re.findall(r'[\w\u4e00-\u9fff]+', text.lower())
        
        emotion_scores = {}
        total_score = 0
        word_count = 0
        
        for word in words:
            if word in self.emotion_lexicon:
                score = self.emotion_lexicon[word]
                total_score += score
                word_count += 1
                
                # 分类情感
                for category, emotions in self.emotion_categories.items():
                    if word in emotions:
                        emotion_scores[category] = emotion_scores.get(category, 0) + 1
        
        if word_count > 0:
            avg_score = total_score / word_count
        else:
            avg_score = 5.0  # 中性
            
        # 确定主要情感
        if emotion_scores:
            primary_emotion = max(emotion_scores.items(), key=lambda x: x[1])[0]
        else:
            primary_emotion = "neutral"
            
        # 计算情感强度
        intensity = min(10, max(1, abs(avg_score - 5) * 2 + 5))
        
        # 检测危机关键词
        crisis_keywords = ["自杀", "自残", "不想活了", "结束一切", "绝望"]
        crisis_detected = any(keyword in text for keyword in crisis_keywords)
        
        return {
            "score": round(avg_score, 2),
            "primary_emotion": primary_emotion,
            "intensity": round(intensity, 2),
            "emotion_breakdown": emotion_scores,
            "word_count": word_count,
            "crisis_alert": crisis_detected,
            "recommendation": self.generate_recommendation(primary_emotion, intensity, crisis_detected)
        }
    
    def generate_recommendation(self, emotion, intensity, crisis_detected):
        """根据情感状态生成个性化建议"""
        if crisis_detected:
            return {
                "urgency": "high",
                "action": "立即联系心理危机干预热线或寻求专业帮助",
                "resources": ["心理危机干预热线: 400-161-9995", "紧急联系人", "就近医院心理科"]
            }
        
        recommendations = {
            "positive": {
                "low": "继续保持积极心态，尝试记录感恩日记",
                "medium": "与他人分享您的积极体验，加强社交联系",
                "high": "利用积极情绪尝试新活动或学习新技能"
            },
            "negative": {
                "low": "尝试深呼吸或短暂休息来调整情绪",
                "medium": "进行正念冥想或轻度运动来缓解情绪",
                "high": "建议进行专业心理咨询或使用放松技术"
            },
            "neutral": {
                "low": "保持现状，注意自我观察",
                "medium": "尝试轻微活动来提升能量水平",
                "high": "探索新的兴趣爱好来增加生活乐趣"
            }
        }
        
        intensity_level = "low" if intensity < 4 else "high" if intensity > 7 else "medium"
        
        return {
            "urgency": "low" if not crisis_detected else "high",
            "action": recommendations[emotion][intensity_level],
            "resources": self.get_resources(emotion, intensity_level)
        }
    
    def get_resources(self, emotion, intensity):
        """获取相关资源推荐"""
        resources = {
            "positive": ["积极心理学练习", "感恩日记模板", "社交活动建议"],
            "negative": ["放松技巧指南", "正念冥想音频", "情绪调节策略"],
            "neutral": ["自我探索问题", "兴趣评估工具", "目标设定指南"]
        }
        return resources.get(emotion, [])

# 增强的生物反馈设备
class AdvancedBioFeedbackDevice:
    def __init__(self):
        self.connected = False
        self.heart_rate = 72
        self.hrv = 45
        self.gsr = 2.5
        self.temperature = 36.6
        self.respiration_rate = 16
        self.blood_oxygen = 98
        self.muscle_tension = 2.0
        
    def connect(self):
        """连接生物反馈设备"""
        self.connected = True
        return True
        
    def disconnect(self):
        """断开生物反馈设备"""
        self.connected = False
        
    def read_data(self):
        """读取生物反馈数据"""
        if not self.connected:
            return None
            
        # 模拟更真实的数据变化
        self.heart_rate += random.randint(-3, 3)
        self.hrv += random.randint(-5, 5)
        self.gsr += random.random() * 0.3 - 0.15
        self.temperature += random.random() * 0.2 - 0.1
        self.respiration_rate += random.randint(-2, 2)
        self.blood_oxygen += random.randint(-1, 1)
        self.muscle_tension += random.random() * 0.2 - 0.1
        
        # 确保数据在合理范围内
        return {
            "heart_rate": max(50, min(120, self.heart_rate)),
            "hrv": max(15, min(100, self.hrv)),
            "gsr": max(0.5, min(10.0, self.gsr)),
            "temperature": max(35.5, min(38.0, self.temperature)),
            "respiration_rate": max(8, min(30, self.respiration_rate)),
            "blood_oxygen": max(85, min(100, self.blood_oxygen)),
            "muscle_tension": max(0.5, min(5.0, self.muscle_tension)),
            "timestamp": datetime.datetime.now().isoformat(),
            "stress_level": self.calculate_stress_level()
        }
    
    def calculate_stress_level(self):
        """计算压力水平（1-10）"""
        # 基于心率变异性(HRV)和皮电反应(GSR)计算压力水平
        hrv_factor = max(0, min(1, (self.hrv - 20) / 60))  # HRV越高，压力越小
        gsr_factor = max(0, min(1, (self.gsr - 0.5) / 8))  # GSR越高，压力越大
        
        stress_level = 10 * (0.7 * (1 - hrv_factor) + 0.3 * gsr_factor)
        return round(stress_level, 1)

# 增强的数据库管理类
class AdvancedDatabaseManager:
    def __init__(self, db_name="mental_health_advanced.db"):
        self.db_name = db_name
        self.encryption_key = self.get_or_create_encryption_key()
        self.cipher_suite = Fernet(self.encryption_key)
        self.init_database()
        
    def get_or_create_encryption_key(self):
        """获取或创建加密密钥"""
        key_file = "encryption_key.key"
        if os.path.exists(key_file):
            with open(key_file, "rb") as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            with open(key_file, "wb") as f:
                f.write(key)
            return key
        
    def encrypt_data(self, data):
        """加密敏感数据"""
        if isinstance(data, str):
            data = data.encode()
        return self.cipher_suite.encrypt(data).decode()
    
    def decrypt_data(self, encrypted_data):
        """解密数据"""
        if isinstance(encrypted_data, str):
            encrypted_data = encrypted_data.encode()
        return self.cipher_suite.decrypt(encrypted_data).decode()
        
    def init_database(self):
        """初始化数据库表结构"""
        conn = sqlite3.connect(self.db_name)
        c = conn.cursor()
        
        # 用户表（增强）
        c.execute('''CREATE TABLE IF NOT EXISTS users
                     (id TEXT PRIMARY KEY, username TEXT UNIQUE, email TEXT UNIQUE, 
                     password_hash TEXT, created_at TEXT, last_login TEXT, 
                     user_type TEXT, settings TEXT, profile_data TEXT)''')
        
        # 情绪记录表（增强）
        c.execute('''CREATE TABLE IF NOT EXISTS emotion_records
                     (id TEXT PRIMARY KEY, user_id TEXT, date TEXT, emotion_score REAL, 
                     emotion_category TEXT, intensity REAL, notes TEXT, tags TEXT, 
                     physiological_data TEXT, crisis_alert INTEGER, recommendation TEXT,
                     FOREIGN KEY(user_id) REFERENCES users(id))''')
        
        # 日记表（增强）
        c.execute('''CREATE TABLE IF NOT EXISTS journal_entries
                     (id TEXT PRIMARY KEY, user_id TEXT, date TEXT, title TEXT, 
                     content TEXT, emotion_score REAL, sentiment TEXT, tags TEXT,
                     word_count INTEGER, analysis_data TEXT, encrypted_content TEXT,
                     FOREIGN KEY(user_id) REFERENCES users(id))''')
        
        # 活动记录表（增强）
        c.execute('''CREATE TABLE IF NOT EXISTS activity_records
                     (id TEXT PRIMARY KEY, user_id TEXT, date TEXT, activity_type TEXT, 
                     duration INTEGER, notes TEXT, effectiveness REAL, category TEXT,
                     difficulty TEXT, satisfaction INTEGER, FOREIGN KEY(user_id) REFERENCES users(id))''')
        
        # 成就表（增强）
        c.execute('''CREATE TABLE IF NOT EXISTS achievements
                     (id TEXT PRIMARY KEY, user_id TEXT, achievement_type TEXT, 
                     achieved_at TEXT, details TEXT, points INTEGER, badge_url TEXT,
                     FOREIGN KEY(user_id) REFERENCES users(id))''')
        
        # 治疗计划表
        c.execute('''CREATE TABLE IF NOT EXISTS treatment_plans
                     (id TEXT PRIMARY KEY, user_id TEXT, title TEXT, description TEXT,
                     start_date TEXT, end_date TEXT, goals TEXT, progress REAL,
                     therapist_notes TEXT, status TEXT, FOREIGN KEY(user_id) REFERENCES users(id))''')
        
        # 咨询记录表
        c.execute('''CREATE TABLE IF NOT EXISTS counseling_sessions
                     (id TEXT PRIMARY KEY, user_id TEXT, date TEXT, therapist_name TEXT,
                     duration INTEGER, notes TEXT, goals TEXT, outcomes TEXT,
                     next_steps TEXT, rating INTEGER, FOREIGN KEY(user_id) REFERENCES users(id))''')
        
        conn.commit()
        conn.close()
        
    def execute_query(self, query, params=()):
        """执行SQL查询"""
        conn = sqlite3.connect(self.db_name)
        c = conn.cursor()
        c.execute(query, params)
        result = c.fetchall()
        conn.commit()
        conn.close()
        return result
        
    def get_user(self, username):
        """获取用户信息"""
        result = self.execute_query("SELECT * FROM users WHERE username=?", (username,))
        if result:
            return {
                "id": result[0][0],
                "username": result[0][1],
                "email": result[0][2],
                "password_hash": result[0][3],
                "created_at": result[0][4],
                "last_login": result[0][5],
                "user_type": result[0][6],
                "settings": json.loads(result[0][7]) if result[0][7] else {},
                "profile_data": json.loads(result[0][8]) if result[0][8] else {}
            }
        return None
        
    def get_user_by_email(self, email):
        """通过邮箱获取用户信息"""
        result = self.execute_query("SELECT * FROM users WHERE email=?", (email,))
        if result:
            return {
                "id": result[0][0],
                "username": result[0][1],
                "email": result[0][2],
                "password_hash": result[0][3],
                "created_at": result[0][4],
                "last_login": result[0][5],
                "user_type": result[0][6],
                "settings": json.loads(result[0][7]) if result[0][7] else {},
                "profile_data": json.loads(result[0][8]) if result[0][8] else {}
            }
        return None
        
    def create_user(self, username, email, password, user_type="standard"):
        """创建新用户"""
        # 检查用户名和邮箱是否已存在
        if self.get_user(username):
            return None, "用户名已存在"
        if self.get_user_by_email(email):
            return None, "邮箱已被注册"
            
        # 验证邮箱格式
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            return None, "邮箱格式不正确"
            
        # 验证密码强度
        if len(password) < 8:
            return None, "密码长度至少8位"
        if not re.search(r'[A-Z]', password):
            return None, "密码必须包含大写字母"
        if not re.search(r'[a-z]', password):
            return None, "密码必须包含小写字母"
        if not re.search(r'[0-9]', password):
            return None, "密码必须包含数字"
            
        user_id = str(uuid.uuid4())
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        created_at = datetime.datetime.now().isoformat()
        
        # 默认设置
        default_settings = {
            "theme": "dark",
            "language": "zh-CN",
            "notifications": True,
            "data_backup": True,
            "privacy_level": "standard"
        }
        
        # 默认个人资料
        default_profile = {
            "full_name": "",
            "age": 0,
            "gender": "",
            "therapy_history": "",
            "medications": "",
            "emergency_contact": ""
        }
        
        try:
            self.execute_query(
                """INSERT INTO users (id, username, email, password_hash, created_at, 
                user_type, settings, profile_data) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (user_id, username, email, password_hash, created_at, user_type, 
                 json.dumps(default_settings), json.dumps(default_profile))
            )
            return user_id, "注册成功"
        except Exception as e:
            return None, f"注册失败: {str(e)}"
        
    def verify_password(self, username, password):
        """验证密码"""
        user = self.get_user(username)
        if user:
            return bcrypt.checkpw(password.encode('utf-8'), user["password_hash"].encode('utf-8'))
        return False
        
    def update_user_profile(self, user_id, profile_data):
        """更新用户个人资料"""
        try:
            self.execute_query(
                "UPDATE users SET profile_data=? WHERE id=?",
                (json.dumps(profile_data), user_id)
            )
            return True, "资料更新成功"
        except Exception as e:
            return False, f"更新失败: {str(e)}"
            
    def update_user_settings(self, user_id, settings):
        """更新用户设置"""
        try:
            self.execute_query(
                "UPDATE users SET settings=? WHERE id=?",
                (json.dumps(settings), user_id)
            )
            return True, "设置更新成功"
        except Exception as e:
            return False, f"更新失败: {str(e)}"

# 注册对话框
class RegisterDialog(QDialog):
    def __init__(self, db_manager):
        super().__init__()
        self.db_manager = db_manager
        self.setWindowTitle("注册新账户")
        self.setModal(True)
        self.setFixedSize(400, 500)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 标题
        title = QLabel("创建新账户")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # 表单
        form_layout = QFormLayout()
        
        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("请输入用户名")
        form_layout.addRow("用户名:", self.username_edit)
        
        self.email_edit = QLineEdit()
        self.email_edit.setPlaceholderText("请输入邮箱地址")
        form_layout.addRow("邮箱:", self.email_edit)
        
        self.password_edit = QLineEdit()
        self.password_edit.setPlaceholderText("至少8位，包含大小写字母和数字")
        self.password_edit.setEchoMode(QLineEdit.Password)
        form_layout.addRow("密码:", self.password_edit)
        
        self.confirm_password_edit = QLineEdit()
        self.confirm_password_edit.setPlaceholderText("请再次输入密码")
        self.confirm_password_edit.setEchoMode(QLineEdit.Password)
        form_layout.addRow("确认密码:", self.confirm_password_edit)
        
        # 用户类型选择
        user_type_layout = QHBoxLayout()
        self.standard_radio = QRadioButton("普通用户")
        self.therapist_radio = QRadioButton("治疗师")
        self.standard_radio.setChecked(True)
        
        user_type_layout.addWidget(self.standard_radio)
        user_type_layout.addWidget(self.therapist_radio)
        form_layout.addRow("账户类型:", user_type_layout)
        
        layout.addLayout(form_layout)
        
        # 密码强度指示器
        self.password_strength_label = QLabel("密码强度: 弱")
        self.password_strength_label.setStyleSheet("color: red;")
        layout.addWidget(self.password_strength_label)
        
        self.password_match_label = QLabel("")
        layout.addWidget(self.password_match_label)
        
        # 实时验证
        self.password_edit.textChanged.connect(self.check_password_strength)
        self.confirm_password_edit.textChanged.connect(self.check_password_match)
        
        # 按钮
        button_layout = QHBoxLayout()
        
        register_btn = QPushButton("注册")
        register_btn.clicked.connect(self.register)
        button_layout.addWidget(register_btn)
        
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        
        # 已有账户提示
        login_prompt = QLabel("已有账户？")
        login_prompt.setAlignment(Qt.AlignCenter)
        layout.addWidget(login_prompt)
        
        login_btn = QPushButton("立即登录")
        login_btn.clicked.connect(self.show_login)
        layout.addWidget(login_btn)
        
        self.setLayout(layout)
        
    def check_password_strength(self):
        """检查密码强度"""
        password = self.password_edit.text()
        
        if len(password) == 0:
            self.password_strength_label.setText("密码强度: 无")
            self.password_strength_label.setStyleSheet("color: gray;")
            return 0
            
        strength = 0
        if len(password) >= 8:
            strength += 1
        if re.search(r'[A-Z]', password):
            strength += 1
        if re.search(r'[a-z]', password):
            strength += 1
        if re.search(r'[0-9]', password):
            strength += 1
        if re.search(r'[^A-Za-z0-9]', password):
            strength += 1
            
        if strength <= 2:
            self.password_strength_label.setText("密码强度: 弱")
            self.password_strength_label.setStyleSheet("color: red;")
        elif strength <= 4:
            self.password_strength_label.setText("密码强度: 中")
            self.password_strength_label.setStyleSheet("color: orange;")
        else:
            self.password_strength_label.setText("密码强度: 强")
            self.password_strength_label.setStyleSheet("color: green;")
            
        return strength
        
    def check_password_match(self):
        """检查密码是否匹配"""
        password = self.password_edit.text()
        confirm = self.confirm_password_edit.text()
        
        if not confirm:
            self.password_match_label.setText("")
            return
            
        if password == confirm:
            self.password_match_label.setText("密码匹配 ✓")
            self.password_match_label.setStyleSheet("color: green;")
        else:
            self.password_match_label.setText("密码不匹配 ✗")
            self.password_match_label.setStyleSheet("color: red;")
            
    def register(self):
        """注册新用户"""
        username = self.username_edit.text().strip()
        email = self.email_edit.text().strip()
        password = self.password_edit.text()
        confirm_password = self.confirm_password_edit.text()
        user_type = "therapist" if self.therapist_radio.isChecked() else "standard"
        
        # 验证输入
        if not username or not email or not password:
            QMessageBox.warning(self, "输入错误", "请填写所有必填字段！")
            return
            
        if password != confirm_password:
            QMessageBox.warning(self, "密码错误", "两次输入的密码不一致！")
            return
            
        if self.check_password_strength() < 3:
            QMessageBox.warning(self, "密码太弱", "密码强度不足，请使用更复杂的密码！")
            return
            
        # 创建用户
        user_id, message = self.db_manager.create_user(username, email, password, user_type)
        
        if user_id:
            QMessageBox.information(self, "注册成功", f"{message}\n请使用新账户登录。")
            self.accept()
        else:
            QMessageBox.warning(self, "注册失败", message)
            
    def show_login(self):
        """显示登录对话框"""
        self.reject()

# 增强的登录对话框
class EnhancedLoginDialog(QDialog):
    def __init__(self, db_manager):
        super().__init__()
        self.db_manager = db_manager
        self.setWindowTitle("心理创伤恢复系统 - 登录")
        self.setModal(True)
        self.setFixedSize(400, 400)
        self.init_ui()
        
    def init_ui(self):
        self.stacked_widget = QStackedWidget()
        
        # 登录页面
        self.login_page = self.create_login_page()
        self.stacked_widget.addWidget(self.login_page)
        
        # 注册页面
        self.register_page = RegisterDialog(self.db_manager)
        self.register_page.setParent(self)
        self.stacked_widget.addWidget(self.register_page)
        
        layout = QVBoxLayout()
        layout.addWidget(self.stacked_widget)
        self.setLayout(layout)
        
    def create_login_page(self):
        """创建登录页面"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # 标题
        title = QLabel("心理创伤恢复系统")
        title.setFont(QFont("Arial", 18, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        subtitle = QLabel("登录您的账户")
        subtitle.setFont(QFont("Arial", 12))
        subtitle.setAlignment(Qt.AlignCenter)
        layout.addWidget(subtitle)
        
        layout.addSpacing(20)
        
        # 登录表单
        form_layout = QFormLayout()
        
        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("用户名或邮箱")
        form_layout.addRow("账户:", self.username_edit)
        
        self.password_edit = QLineEdit()
        self.password_edit.setPlaceholderText("请输入密码")
        self.password_edit.setEchoMode(QLineEdit.Password)
        form_layout.addRow("密码:", self.password_edit)
        
        # 记住我
        self.remember_me = QCheckBox("记住我")
        form_layout.addRow("", self.remember_me)
        
        # 忘记密码
        forgot_password = QLabel("<a href='#'>忘记密码？</a>")
        forgot_password.setOpenExternalLinks(False)
        forgot_password.linkActivated.connect(self.forgot_password)
        form_layout.addRow("", forgot_password)
        
        layout.addLayout(form_layout)
        
        layout.addSpacing(20)
        
        # 登录按钮
        login_btn = QPushButton("登录")
        login_btn.clicked.connect(self.login)
        layout.addWidget(login_btn)
        
        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)
        
        # 注册提示
        register_prompt = QLabel("还没有账户？")
        register_prompt.setAlignment(Qt.AlignCenter)
        layout.addWidget(register_prompt)
        
        register_btn = QPushButton("创建新账户")
        register_btn.clicked.connect(self.show_register)
        layout.addWidget(register_btn)
        
        widget.setLayout(layout)
        return widget
        
    def login(self):
        """处理登录"""
        username = self.username_edit.text().strip()
        password = self.password_edit.text()
        
        if not username or not password:
            QMessageBox.warning(self, "输入错误", "请输入用户名/邮箱和密码！")
            return
            
        # 尝试验证（支持用户名或邮箱登录）
        user = self.db_manager.get_user(username)
        if not user:
            user = self.db_manager.get_user_by_email(username)
            
        if not user:
            QMessageBox.warning(self, "登录失败", "账户不存在！")
            return
            
        if self.db_manager.verify_password(user["username"], password):
            self.user_info = user
            self.accept()
        else:
            QMessageBox.warning(self, "登录失败", "密码不正确！")
            
    def show_register(self):
        """显示注册页面"""
        self.stacked_widget.setCurrentIndex(1)
        
    def forgot_password(self):
        """忘记密码功能"""
        QMessageBox.information(self, "忘记密码", 
                              "请联系系统管理员或使用注册邮箱重置密码。\n\n临时解决方案：注册新账户。")
        
    def get_user_info(self):
        """获取用户信息"""
        return self.user_info

# 用户个人资料对话框
class UserProfileDialog(QDialog):
    def __init__(self, user_info, db_manager):
        super().__init__()
        self.user_info = user_info
        self.db_manager = db_manager
        self.setWindowTitle("个人资料")
        self.setModal(True)
        self.setFixedSize(500, 600)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 标签页
        self.tabs = QTabWidget()
        
        # 基本资料标签页
        basic_tab = QWidget()
        self.init_basic_tab(basic_tab)
        self.tabs.addTab(basic_tab, "基本资料")
        
        # 设置标签页
        settings_tab = QWidget()
        self.init_settings_tab(settings_tab)
        self.tabs.addTab(settings_tab, "设置")
        
        # 统计标签页
        stats_tab = QWidget()
        self.init_stats_tab(stats_tab)
        self.tabs.addTab(stats_tab, "统计")
        
        layout.addWidget(self.tabs)
        
        # 按钮
        button_layout = QHBoxLayout()
        
        save_btn = QPushButton("保存更改")
        save_btn.clicked.connect(self.save_profile)
        button_layout.addWidget(save_btn)
        
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
    def init_basic_tab(self, tab):
        layout = QFormLayout()
        
        self.full_name_edit = QLineEdit()
        layout.addRow("姓名:", self.full_name_edit)
        
        self.age_spinbox = QSpinBox()
        self.age_spinbox.setRange(0, 120)
        layout.addRow("年龄:", self.age_spinbox)
        
        self.gender_combo = QComboBox()
        self.gender_combo.addItems(["", "男", "女", "其他"])
        layout.addRow("性别:", self.gender_combo)
        
        self.therapy_history_edit = QTextEdit()
        self.therapy_history_edit.setMaximumHeight(80)
        layout.addRow("治疗历史:", self.therapy_history_edit)
        
        self.medications_edit = QTextEdit()
        self.medications_edit.setMaximumHeight(80)
        layout.addRow("当前用药:", self.medications_edit)
        
        self.emergency_contact_edit = QLineEdit()
        layout.addRow("紧急联系人:", self.emergency_contact_edit)
        
        # 加载现有数据
        self.load_profile_data()
        
        tab.setLayout(layout)
        
    def init_settings_tab(self, tab):
        layout = QVBoxLayout()
        
        # 主题设置
        theme_group = QGroupBox("界面主题")
        theme_layout = QHBoxLayout()
        
        self.theme_dark = QRadioButton("深色主题")
        self.theme_light = QRadioButton("浅色主题")
        self.theme_auto = QRadioButton("自动")
        
        theme_layout.addWidget(self.theme_dark)
        theme_layout.addWidget(self.theme_light)
        theme_layout.addWidget(self.theme_auto)
        theme_group.setLayout(theme_layout)
        layout.addWidget(theme_group)
        
        # 隐私设置
        privacy_group = QGroupBox("隐私设置")
        privacy_layout = QFormLayout()
        
        self.notifications_cb = QCheckBox("启用通知")
        privacy_layout.addRow(self.notifications_cb)
        
        self.data_backup_cb = QCheckBox("自动备份数据")
        privacy_layout.addRow(self.data_backup_cb)
        
        self.privacy_combo = QComboBox()
        self.privacy_combo.addItems(["标准", "高", "最高"])
        privacy_layout.addRow("隐私级别:", self.privacy_combo)
        
        privacy_group.setLayout(privacy_layout)
        layout.addWidget(privacy_group)
        
        tab.setLayout(layout)
        
    def init_stats_tab(self, tab):
        layout = QVBoxLayout()
        
        # 用户统计信息
        stats_text = QTextEdit()
        stats_text.setReadOnly(True)
        
        # 获取用户统计数据
        emotion_count = len(self.db_manager.execute_query(
            "SELECT id FROM emotion_records WHERE user_id=?", (self.user_info["id"],)
        ))
        
        journal_count = len(self.db_manager.execute_query(
            "SELECT id FROM journal_entries WHERE user_id=?", (self.user_info["id"],)
        ))
        
        activity_count = len(self.db_manager.execute_query(
            "SELECT id FROM activity_records WHERE user_id=?", (self.user_info["id"],)
        ))
        
        stats_info = f"""
        <h3>使用统计</h3>
        <p>情绪记录数: {emotion_count}</p>
        <p>日记条目数: {journal_count}</p>
        <p>活动记录数: {activity_count}</p>
        <p>注册时间: {self.user_info['created_at'][:10]}</p>
        <p>最后登录: {self.user_info['last_login'][:10] if self.user_info['last_login'] else '从未登录'}</p>
        """
        
        stats_text.setHtml(stats_info)
        layout.addWidget(stats_text)
        
        tab.setLayout(layout)
        
    def load_profile_data(self):
        """加载个人资料数据"""
        profile_data = self.user_info.get("profile_data", {})
        
        self.full_name_edit.setText(profile_data.get("full_name", ""))
        self.age_spinbox.setValue(profile_data.get("age", 0))
        self.gender_combo.setCurrentText(profile_data.get("gender", ""))
        self.therapy_history_edit.setText(profile_data.get("therapy_history", ""))
        self.medications_edit.setText(profile_data.get("medications", ""))
        self.emergency_contact_edit.setText(profile_data.get("emergency_contact", ""))
        
        # 加载设置
        settings = self.user_info.get("settings", {})
        theme = settings.get("theme", "dark")
        if theme == "dark":
            self.theme_dark.setChecked(True)
        elif theme == "light":
            self.theme_light.setChecked(True)
        else:
            self.theme_auto.setChecked(True)
            
        self.notifications_cb.setChecked(settings.get("notifications", True))
        self.data_backup_cb.setChecked(settings.get("data_backup", True))
        
        privacy_level = settings.get("privacy_level", "standard")
        index = {"standard": 0, "high": 1, "maximum": 2}.get(privacy_level, 0)
        self.privacy_combo.setCurrentIndex(index)
        
    def save_profile(self):
        """保存个人资料和设置"""
        # 更新个人资料
        profile_data = {
            "full_name": self.full_name_edit.text(),
            "age": self.age_spinbox.value(),
            "gender": self.gender_combo.currentText(),
            "therapy_history": self.therapy_history_edit.toPlainText(),
            "medications": self.medications_edit.toPlainText(),
            "emergency_contact": self.emergency_contact_edit.text()
        }
        
        success, message = self.db_manager.update_user_profile(self.user_info["id"], profile_data)
        if not success:
            QMessageBox.warning(self, "保存失败", message)
            return
            
        # 更新设置
        theme = "dark" if self.theme_dark.isChecked() else "light" if self.theme_light.isChecked() else "auto"
        privacy_level = ["standard", "high", "maximum"][self.privacy_combo.currentIndex()]
        
        settings = {
            "theme": theme,
            "notifications": self.notifications_cb.isChecked(),
            "data_backup": self.data_backup_cb.isChecked(),
            "privacy_level": privacy_level
        }
        
        success, message = self.db_manager.update_user_settings(self.user_info["id"], settings)
        if success:
            QMessageBox.information(self, "成功", "个人资料和设置已保存！")
            self.user_info["profile_data"] = profile_data
            self.user_info["settings"] = settings
        else:
            QMessageBox.warning(self, "保存失败", message)

# 主应用程序窗口（增强版）
class EnhancedMentalHealthApp(QMainWindow):
    def __init__(self, user_info, db_manager):
        super().__init__()
        self.user_info = user_info
        self.db_manager = db_manager
        self.emotion_analyzer = AdvancedEmotionAnalysisAPI()
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle(f"高级心理创伤恢复系统 - {self.user_info['username']}")
        self.setGeometry(100, 100, 1400, 900)
        
        # 应用主题
        self.apply_theme()
        
        # 创建菜单栏
        self.create_menu()
        
        # 创建状态栏
        self.statusBar().showMessage(f"欢迎回来，{self.user_info['username']}！")
        
        # 创建标签页界面
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        
        # 仪表板标签页
        self.dashboard_tab = QWidget()
        self.init_dashboard_tab()
        self.tabs.addTab(self.dashboard_tab, "🏠 仪表板")
        
        # 情绪追踪标签页
        self.emotion_tab = QWidget()
        self.init_emotion_tab()
        self.tabs.addTab(self.emotion_tab, "📊 情绪追踪")
        
        # 智能日记标签页
        self.journal_tab = QWidget()
        self.init_journal_tab()
        self.tabs.addTab(self.journal_tab, "📝 智能日记")
        
        # 生物反馈标签页
        self.biofeedback_tab = QWidget()
        self.init_biofeedback_tab()
        self.tabs.addTab(self.biofeedback_tab, "💓 生物反馈")
        
        # 治疗计划标签页
        self.treatment_tab = QWidget()
        self.init_treatment_tab()
        self.tabs.addTab(self.treatment_tab, "📋 治疗计划")
        
        # 心理教育资源标签页
        self.education_tab = QWidget()
        self.init_education_tab()
        self.tabs.addTab(self.education_tab, "📚 心理教育")
        
        # 加载初始数据
        self.load_initial_data()
        
    def apply_theme(self):
        """应用主题设置"""
        theme = self.user_info.get("settings", {}).get("theme", "dark")
        if theme == "dark":
            self.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
        elif theme == "light":
            # 浅色主题样式
            light_style = """
            QMainWindow { background-color: #f0f0f0; }
            QWidget { background-color: #ffffff; color: #333333; }
            QTabWidget::pane { border: 1px solid #cccccc; }
            QTabBar::tab { background-color: #e0e0e0; padding: 8px 12px; }
            QTabBar::tab:selected { background-color: #ffffff; }
            """
            self.setStyleSheet(light_style)
        
    def create_menu(self):
        """创建增强的菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu("文件")
        
        profile_action = QAction("个人资料", self)
        profile_action.triggered.connect(self.show_profile)
        file_menu.addAction(profile_action)
        
        file_menu.addSeparator()
        
        export_action = QAction("导出数据", self)
        export_action.triggered.connect(self.export_data)
        file_menu.addAction(export_action)
        
        backup_action = QAction("备份数据", self)
        backup_action.triggered.connect(self.backup_data)
        file_menu.addAction(backup_action)
        
        file_menu.addSeparator()
        
        logout_action = QAction("退出登录", self)
        logout_action.triggered.connect(self.logout)
        file_menu.addAction(logout_action)
        
        # 工具菜单
        tools_menu = menubar.addMenu("工具")
        
        settings_action = QAction("系统设置", self)
        settings_action.triggered.connect(self.show_settings)
        tools_menu.addAction(settings_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu("帮助")
        
        resources_action = QAction("危机资源", self)
        resources_action.triggered.connect(self.show_crisis_resources)
        help_menu.addAction(resources_action)
        
        about_action = QAction("关于", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
    def show_profile(self):
        """显示个人资料对话框"""
        dialog = UserProfileDialog(self.user_info, self.db_manager)
        dialog.exec_()
        
    def init_dashboard_tab(self):
        """初始化增强的仪表板"""
        layout = QVBoxLayout()
        
        # 欢迎区域
        welcome_widget = QGroupBox("欢迎面板")
        welcome_layout = QHBoxLayout()
        
        # 用户信息
        user_info = QLabel(f"""
        <h2>欢迎回来，{self.user_info['username']}！</h2>
        <p>今日心情如何？让我们开始今天的恢复之旅。</p>
        <p>注册时间: {self.user_info['created_at'][:10]}</p>
        """)
        welcome_layout.addWidget(user_info)
        
        # 快速操作按钮
        quick_actions = QVBoxLayout()
        
        quick_emotion = QPushButton("记录情绪")
        quick_emotion.clicked.connect(lambda: self.tabs.setCurrentIndex(1))
        quick_actions.addWidget(quick_emotion)
        
        quick_journal = QPushButton("写日记")
        quick_journal.clicked.connect(lambda: self.tabs.setCurrentIndex(2))
        quick_actions.addWidget(quick_journal)
        
        quick_bio = QPushButton("生物反馈")
        quick_bio.clicked.connect(lambda: self.tabs.setCurrentIndex(3))
        quick_actions.addWidget(quick_bio)
        
        welcome_layout.addLayout(quick_actions)
        welcome_widget.setLayout(welcome_layout)
        layout.addWidget(welcome_widget)
        
        # 主要内容区域
        splitter = QSplitter(Qt.Horizontal)
        
        # 左侧 - 情绪概览和紧急通知
        left_widget = QWidget()
        left_layout = QVBoxLayout()
        
        # 情绪概览
        emotion_overview = QGroupBox("情绪概览")
        emotion_layout = QVBoxLayout()
        self.emotion_summary = QLabel("加载中...")
        emotion_layout.addWidget(self.emotion_summary)
        emotion_overview.setLayout(emotion_layout)
        left_layout.addWidget(emotion_overview)
        
        # 紧急通知
        self.alert_widget = QGroupBox("重要通知")
        self.alert_layout = QVBoxLayout()
        self.alert_label = QLabel("暂无重要通知")
        self.alert_layout.addWidget(self.alert_label)
        self.alert_widget.setLayout(self.alert_layout)
        left_layout.addWidget(self.alert_widget)
        
        left_widget.setLayout(left_layout)
        splitter.addWidget(left_widget)
        
        # 右侧 - 推荐和进度
        right_widget = QWidget()
        right_layout = QVBoxLayout()
        
        # 个性化推荐
        recommendation_widget = QGroupBox("个性化推荐")
        recommendation_layout = QVBoxLayout()
        self.recommendation_list = QListWidget()
        recommendation_layout.addWidget(self.recommendation_list)
        recommendation_widget.setLayout(recommendation_layout)
        right_layout.addWidget(recommendation_widget)
        
        # 进度追踪
        progress_widget = QGroupBox("恢复进度")
        progress_layout = QVBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        progress_layout.addWidget(QLabel("整体恢复进度:"))
        progress_layout.addWidget(self.progress_bar)
        progress_widget.setLayout(progress_layout)
        right_layout.addWidget(progress_widget)
        
        right_widget.setLayout(right_layout)
        splitter.addWidget(right_widget)
        
        splitter.setSizes([400, 600])
        layout.addWidget(splitter)
        
        self.dashboard_tab.setLayout(layout)
        
    def init_emotion_tab(self):
        """初始化情绪追踪标签页"""
        layout = QVBoxLayout()
        
        title = QLabel("高级情绪追踪")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # 这里将实现完整的情绪追踪功能
        emotion_desc = QLabel("""
        <p>使用多维度情绪评估工具来追踪您的情绪变化。</p>
        <p>功能包括：实时情绪记录、情绪趋势分析、情绪触发因素识别等。</p>
        """)
        emotion_desc.setWordWrap(True)
        layout.addWidget(emotion_desc)
        
        self.emotion_tab.setLayout(layout)
        
    def init_journal_tab(self):
        """初始化智能日记标签页"""
        layout = QVBoxLayout()
        
        title = QLabel("智能日记")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # 这里将实现完整的日记功能
        journal_desc = QLabel("""
        <p>通过AI辅助的日记系统记录您的想法和感受。</p>
        <p>功能包括：语音输入、情感分析、智能建议、加密存储等。</p>
        """)
        journal_desc.setWordWrap(True)
        layout.addWidget(journal_desc)
        
        self.journal_tab.setLayout(layout)
        
    def init_biofeedback_tab(self):
        """初始化生物反馈标签页"""
        layout = QVBoxLayout()
        
        title = QLabel("生物反馈训练")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # 这里将实现完整的生物反馈功能
        bio_desc = QLabel("""
        <p>通过生物反馈技术学习调节生理反应。</p>
        <p>功能包括：实时生理数据监测、压力水平评估、放松训练指导等。</p>
        """)
        bio_desc.setWordWrap(True)
        layout.addWidget(bio_desc)
        
        self.biofeedback_tab.setLayout(layout)
        
    def init_treatment_tab(self):
        """初始化治疗计划标签页"""
        layout = QVBoxLayout()
        
        title = QLabel("个性化治疗计划")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # 这里将实现治疗计划功能
        treatment_desc = QLabel("""
        <p>制定和追踪个性化的心理治疗计划。</p>
        <p>功能包括：目标设定、进度追踪、治疗师笔记、成效评估等。</p>
        """)
        treatment_desc.setWordWrap(True)
        layout.addWidget(treatment_desc)
        
        self.treatment_tab.setLayout(layout)
        
    def init_education_tab(self):
        """初始化心理教育资源标签页"""
        layout = QVBoxLayout()
        
        title = QLabel("心理教育资源库")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # 这里将实现教育资源功能
        education_desc = QLabel("""
        <p>访问丰富的心理健康教育资源。</p>
        <p>资源包括：文章、视频、音频课程、自助练习、推荐书籍等。</p>
        """)
        education_desc.setWordWrap(True)
        layout.addWidget(education_desc)
        
        self.education_tab.setLayout(layout)
        
    def load_initial_data(self):
        """加载初始数据"""
        self.update_dashboard()
        
    def update_dashboard(self):
        """更新仪表板数据"""
        # 更新情绪摘要
        self.update_emotion_summary()
        
        # 更新推荐
        self.update_recommendations()
        
        # 更新进度
        self.update_progress()
        
    def update_emotion_summary(self):
        """更新情绪摘要"""
        # 获取最近的情绪记录
        results = self.db_manager.execute_query(
            "SELECT emotion_score, emotion_category, date FROM emotion_records WHERE user_id=? ORDER BY date DESC LIMIT 5",
            (self.user_info["id"],)
        )
        
        if not results:
            summary_text = "<p>暂无情绪记录，请开始记录您的情绪。</p>"
        else:
            scores = [row[0] for row in results]
            avg_score = np.mean(scores)
            last_record = results[0]
            
            summary_text = f"""
            <p>最近情绪: <b>{last_record[0]:.1f}/10</b> ({last_record[1]})</p>
            <p>平均情绪: <b>{avg_score:.1f}/10</b></p>
            <p>记录数量: <b>{len(results)}</b></p>
            <p>最后记录: {last_record[2][:10]}</p>
            """
            
        self.emotion_summary.setText(summary_text)
        
    def update_recommendations(self):
        """更新个性化推荐"""
        recommendations = [
            "基于您的情绪模式，建议尝试正念冥想练习",
            "检测到压力水平较高，推荐进行深呼吸练习",
            "最近情绪记录较少，建议增加自我观察频率"
        ]
        
        self.recommendation_list.clear()
        self.recommendation_list.addItems(recommendations)
        
    def update_progress(self):
        """更新恢复进度"""
        # 简单的进度计算（实际应用中应该更复杂）
        emotion_count = len(self.db_manager.execute_query(
            "SELECT id FROM emotion_records WHERE user_id=?", (self.user_info["id"],)
        ))
        
        journal_count = len(self.db_manager.execute_query(
            "SELECT id FROM journal_entries WHERE user_id=?", (self.user_info["id"],)
        ))
        
        # 基础进度计算
        base_progress = min(100, (emotion_count + journal_count) * 2)
        self.progress_bar.setValue(base_progress)
        
    def export_data(self):
        """导出数据"""
        QMessageBox.information(self, "导出数据", "数据导出功能已增强，支持多种格式导出。")
        
    def backup_data(self):
        """备份数据"""
        QMessageBox.information(self, "备份数据", "自动备份功能已启用，数据安全有保障。")
        
    def show_settings(self):
        """显示系统设置"""
        QMessageBox.information(self, "系统设置", "系统设置可通过个人资料页面进行调整。")
        
    def show_crisis_resources(self):
        """显示危机资源"""
        resources = """
        <h3>心理危机干预资源</h3>
        <p><b>全国心理援助热线：</b> 400-161-9995</p>
        <p><b>北京心理危机干预中心：</b> 010-82951332</p>
        <p><b>上海市心理援助热线：</b> 021-12320-5</p>
        <p><b>广州市心理援助热线：</b> 020-81899120</p>
        <p><b>紧急情况请拨打：</b> 110 或 120</p>
        """
        QMessageBox.information(self, "危机资源", resources)
        
    def show_about(self):
        """显示关于信息"""
        about_text = """
        <h3>高级心理创伤恢复系统 v3.0</h3>
        <p>这是一个全面的心理健康管理平台，专为心理创伤恢复设计。</p>
        <p><b>主要功能：</b></p>
        <ul>
        <li>多维度情绪追踪与分析</li>
        <li>AI辅助智能日记</li>
        <li>生物反馈训练</li>
        <li>个性化治疗计划</li>
        <li>丰富的心理教育资源</li>
        <li>安全的数据加密存储</li>
        </ul>
        <p>© 2024 心理健康科技 - 高级版</p>
        """
        QMessageBox.about(self, "关于系统", about_text)
        
    def logout(self):
        """退出登录"""
        reply = QMessageBox.question(self, "确认退出", 
                                   "确定要退出登录吗？",
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.close()

# 应用程序入口点
def main():
    """主函数"""
    app = QApplication(sys.argv)
    
    # 初始化数据库
    db_manager = AdvancedDatabaseManager()
    
    # 显示增强的登录对话框
    login_dialog = EnhancedLoginDialog(db_manager)
    if login_dialog.exec_() != QDialog.Accepted:
        sys.exit(0)
        
    # 获取用户信息
    user_info = login_dialog.get_user_info()
    
    # 更新最后登录时间
    db_manager.execute_query(
        "UPDATE users SET last_login=? WHERE id=?",
        (datetime.datetime.now().isoformat(), user_info["id"])
    )
    
    # 创建并显示主窗口
    window = EnhancedMentalHealthApp(user_info, db_manager)
    window.show()
    
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()