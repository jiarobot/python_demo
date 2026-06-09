import sys
import json
import sqlite3
import numpy as np
import matplotlib
matplotlib.rc("font", family='Microsoft YaHei')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from datetime import datetime, timedelta
import random
import os

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QLabel, QPushButton, QTabWidget, 
                            QListWidget, QTextEdit, QSlider, QSpinBox, 
                            QDoubleSpinBox, QGroupBox, QFormLayout, 
                            QProgressBar, QMessageBox, QFileDialog, 
                            QSplitter, QFrame, QGraphicsView, QGraphicsScene,
                            QGraphicsPixmapItem, QGraphicsEllipseItem, QComboBox,
                            QDialog, QTableWidget, QTableWidgetItem, QDialogButtonBox,
                            QLineEdit, QTextBrowser, QCheckBox, QRadioButton,
                            QButtonGroup, QStackedWidget, QSizePolicy, QGridLayout,
                            QToolBar, QStatusBar, QAction, QToolButton, QMenu,
                            QInputDialog, QCalendarWidget, QDateEdit, QTimeEdit)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QPointF, QRectF, QDateTime, QSize
from PyQt5.QtGui import QPixmap, QImage, QPainter, QPen, QColor, QFont, QIcon, QPalette
from PyQt5.QtMultimedia import QSound, QMediaPlayer, QMediaContent
from PyQt5.QtMultimediaWidgets import QVideoWidget

class AcupointDatabase:
    """增强版穴位数据库管理类"""
    
    def __init__(self, db_path="acupoints.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建穴位表 - 修复表结构
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS acupoints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                location TEXT,
                function TEXT,
                massage_technique TEXT,
                duration_range TEXT,
                intensity_range TEXT,
                image_path TEXT,
                category TEXT,
                meridian TEXT,
                contraindications TEXT,
                video_path TEXT,
                audio_path TEXT
            )
        ''')
        
        # 创建按摩记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS massage_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_name TEXT,
                acupoint_name TEXT,
                technique TEXT,
                duration INTEGER,
                intensity INTEGER,
                pressure INTEGER,
                feedback_rating INTEGER,
                feedback_text TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 创建用户偏好表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_preferences (
                user_name TEXT PRIMARY KEY,
                preferred_techniques TEXT,
                sensitivity_level INTEGER,
                preferred_duration INTEGER,
                health_conditions TEXT,
                goals TEXT,
                created_date DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 插入更丰富的示例数据
        sample_data = [
            ("涌泉穴", "足底前1/3凹陷处", "补肾壮阳、强筋健骨、安神助眠", "按压、揉捏、振动", "3-5分钟", "中等强度", 
             "images/yongquan.png", "肾经", "足少阴肾经", "孕妇慎用", "videos/yongquan.mp4", "audio/yongquan.wav"),
            
            ("太冲穴", "足背第一、二跖骨结合部前方凹陷处", "疏肝理气、缓解压力、降压明目", "按压、点按", "2-3分钟", "轻到中等强度", 
             "images/taichong.png", "肝经", "足厥阴肝经", "无特殊禁忌", "videos/taichong.mp4", "audio/taichong.wav"),
            
            ("足三里", "小腿前外侧，犊鼻下3寸", "调理脾胃、补中益气、增强免疫力", "按压、揉捏、推拿", "3-5分钟", "中等强度", 
             "images/zusanli.png", "胃经", "足阳明胃经", "饭后一小时不宜按摩", "videos/zusanli.mp4", "audio/zusanli.wav"),
            
            ("三阴交", "小腿内侧，足内踝尖上3寸", "调理肝脾肾、妇科疾病、美容养颜", "按压、揉捏", "2-4分钟", "轻到中等强度", 
             "images/sanyinjiao.png", "脾经", "足太阴脾经", "孕妇禁用", "videos/sanyinjiao.mp4", "audio/sanyinjiao.wav"),
            
            ("太溪穴", "足内侧，内踝后方与脚跟骨筋腱之间的凹陷处", "补肾气、壮腰膝、调节内分泌", "按压、点按", "2-3分钟", "轻到中等强度", 
             "images/taixi.png", "肾经", "足少阴肾经", "无特殊禁忌", "videos/taixi.mp4", "audio/taixi.wav"),
            
            ("昆仑穴", "足外踝后方，外踝尖与跟腱之间的凹陷处", "舒筋活络、清头明目、缓解头痛", "按压、揉捏", "2-3分钟", "中等强度", 
             "images/kunlun.png", "膀胱经", "足太阳膀胱经", "孕妇慎用", "videos/kunlun.mp4", "audio/kunlun.wav")
        ]
        
        # 检查表结构并动态调整插入语句
        cursor.execute("PRAGMA table_info(acupoints)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if len(columns) >= 13:  # 包含所有列
            insert_sql = '''
                INSERT OR IGNORE INTO acupoints 
                (name, location, function, massage_technique, duration_range, intensity_range, 
                 image_path, category, meridian, contraindications, video_path, audio_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            '''
            cursor.executemany(insert_sql, sample_data)
        else:
            # 如果表结构不完整，使用简化插入
            simplified_data = [(d[0], d[1], d[2], d[3], d[4], d[5], d[6]) for d in sample_data]
            insert_sql = '''
                INSERT OR IGNORE INTO acupoints 
                (name, location, function, massage_technique, duration_range, intensity_range, image_path)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            '''
            cursor.executemany(insert_sql, simplified_data)
            
            # 尝试添加缺失的列
            missing_columns = ['category', 'meridian', 'contraindications', 'video_path', 'audio_path']
            for column in missing_columns:
                try:
                    cursor.execute(f"ALTER TABLE acupoints ADD COLUMN {column} TEXT")
                    print(f"已添加列: {column}")
                except sqlite3.OperationalError as e:
                    print(f"列 {column} 可能已存在: {e}")
        
        conn.commit()
        conn.close()
    
    def get_all_acupoints(self):
        """获取所有穴位信息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM acupoints ORDER BY name")
        acupoints = cursor.fetchall()
        conn.close()
        return acupoints
    
    def get_acupoint_by_name(self, name):
        """根据名称获取穴位信息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM acupoints WHERE name=?", (name,))
        acupoint = cursor.fetchone()
        conn.close()
        return acupoint
    
    def get_acupoints_by_category(self, category):
        """根据类别获取穴位"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM acupoints WHERE category=?", (category,))
        acupoints = cursor.fetchall()
        conn.close()
        return acupoints
    
    def add_acupoint(self, name, location, function, technique, duration, intensity, 
                    image_path, category="", meridian="", contraindications="", video_path="", audio_path=""):
        """添加新穴位"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 检查表结构
        cursor.execute("PRAGMA table_info(acupoints)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if len(columns) >= 13:
            cursor.execute('''
                INSERT INTO acupoints 
                (name, location, function, massage_technique, duration_range, intensity_range, 
                 image_path, category, meridian, contraindications, video_path, audio_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (name, location, function, technique, duration, intensity, 
                  image_path, category, meridian, contraindications, video_path, audio_path))
        else:
            cursor.execute('''
                INSERT INTO acupoints 
                (name, location, function, massage_technique, duration_range, intensity_range, image_path)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (name, location, function, technique, duration, intensity, image_path))
        
        conn.commit()
        conn.close()
    
    def update_acupoint(self, name, **kwargs):
        """更新穴位信息"""
        if not kwargs:
            return
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 检查哪些列实际存在
        cursor.execute("PRAGMA table_info(acupoints)")
        existing_columns = [column[1] for column in cursor.fetchall()]
        
        valid_kwargs = {k: v for k, v in kwargs.items() if k in existing_columns}
        
        if not valid_kwargs:
            conn.close()
            return
        
        set_clause = ", ".join([f"{key}=?" for key in valid_kwargs.keys()])
        values = list(valid_kwargs.values())
        values.append(name)
        
        cursor.execute(f"UPDATE acupoints SET {set_clause} WHERE name=?", values)
        conn.commit()
        conn.close()
    
    def delete_acupoint(self, name):
        """删除穴位"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM acupoints WHERE name=?", (name,))
        conn.commit()
        conn.close()
    
    def add_massage_record(self, user_name, acupoint_name, technique, duration, 
                          intensity, pressure, feedback_rating=0, feedback_text=""):
        """添加按摩记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO massage_records 
            (user_name, acupoint_name, technique, duration, intensity, pressure, feedback_rating, feedback_text)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_name, acupoint_name, technique, duration, intensity, pressure, feedback_rating, feedback_text))
        conn.commit()
        conn.close()
    
    def get_user_records(self, user_name, limit=50):
        """获取用户按摩记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM massage_records 
            WHERE user_name=? 
            ORDER BY timestamp DESC 
            LIMIT ?
        ''', (user_name, limit))
        records = cursor.fetchall()
        conn.close()
        return records
    
    def get_popular_acupoints(self, limit=5):
        """获取最受欢迎的穴位"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT acupoint_name, COUNT(*) as usage_count 
            FROM massage_records 
            GROUP BY acupoint_name 
            ORDER BY usage_count DESC 
            LIMIT ?
        ''', (limit,))
        popular = cursor.fetchall()
        conn.close()
        return popular

class AdvancedMassageSimulator:
    """高级按摩模拟器"""
    
    def __init__(self):
        self.techniques = {
            "按压": self.press_technique,
            "揉捏": self.knead_technique,
            "点按": self.point_press_technique,
            "推拿": self.push_pull_technique,
            "振动": self.vibration_technique,
            "叩击": self.tapping_technique,
            "摩擦": self.rubbing_technique,
            "拿捏": self.grasping_technique
        }
        
        # 按摩效果参数
        self.pressure_level = 5  # 压力级别 1-10
        self.speed_level = 5     # 速度级别 1-10
        self.duration = 3        # 持续时间(分钟)
        self.rhythm_pattern = "均匀"  # 节奏模式
        
        # 生理效应模拟
        self.physiological_effects = {
            "血液循环": 0,
            "肌肉放松": 0,
            "神经调节": 0,
            "内分泌平衡": 0,
            "免疫力提升": 0
        }
        
    def set_rhythm_pattern(self, pattern):
        """设置节奏模式"""
        self.rhythm_pattern = pattern
    
    def press_technique(self, acupoint):
        """按压手法模拟"""
        intensity = self.pressure_level * 10
        effect = f"对{acupoint}进行按压按摩，压力级别: {self.pressure_level}/10"
        
        # 生理效应计算
        self.physiological_effects["血液循环"] = self.pressure_level * 8
        self.physiological_effects["肌肉放松"] = self.pressure_level * 6
        
        return effect, intensity, self.physiological_effects.copy()
    
    def knead_technique(self, acupoint):
        """揉捏手法模拟"""
        intensity = self.pressure_level * 8 + self.speed_level * 2
        effect = f"对{acupoint}进行揉捏按摩，压力: {self.pressure_level}/10，速度: {self.speed_level}/10"
        
        self.physiological_effects["血液循环"] = self.pressure_level * 7 + self.speed_level * 3
        self.physiological_effects["肌肉放松"] = self.pressure_level * 9
        
        return effect, intensity, self.physiological_effects.copy()
    
    def point_press_technique(self, acupoint):
        """点按手法模拟"""
        intensity = self.pressure_level * 12
        effect = f"对{acupoint}进行点按按摩，精准刺激穴位"
        
        self.physiological_effects["神经调节"] = self.pressure_level * 10
        self.physiological_effects["内分泌平衡"] = self.pressure_level * 6
        
        return effect, intensity, self.physiological_effects.copy()
    
    def push_pull_technique(self, acupoint):
        """推拿手法模拟"""
        intensity = self.pressure_level * 6 + self.speed_level * 4
        effect = f"对{acupoint}进行推拿按摩，线性运动，节奏: {self.rhythm_pattern}"
        
        self.physiological_effects["血液循环"] = self.speed_level * 8
        self.physiological_effects["肌肉放松"] = self.pressure_level * 7
        
        return effect, intensity, self.physiological_effects.copy()
    
    def vibration_technique(self, acupoint):
        """振动手法模拟"""
        intensity = self.speed_level * 10
        effect = f"对{acupoint}进行振动按摩，频率: {self.speed_level}/10"
        
        self.physiological_effects["神经调节"] = self.speed_level * 9
        self.physiological_effects["肌肉放松"] = self.speed_level * 7
        
        return effect, intensity, self.physiological_effects.copy()
    
    def tapping_technique(self, acupoint):
        """叩击手法模拟"""
        intensity = self.pressure_level * 5 + self.speed_level * 5
        effect = f"对{acupoint}进行叩击按摩，节奏轻快"
        
        self.physiological_effects["血液循环"] = self.speed_level * 9
        self.physiological_effects["免疫力提升"] = self.pressure_level * 4
        
        return effect, intensity, self.physiological_effects.copy()
    
    def rubbing_technique(self, acupoint):
        """摩擦手法模拟"""
        intensity = self.speed_level * 8
        effect = f"对{acupoint}进行摩擦按摩，产生温热感"
        
        self.physiological_effects["血液循环"] = self.speed_level * 10
        self.physiological_effects["内分泌平衡"] = self.speed_level * 5
        
        return effect, intensity, self.physiological_effects.copy()
    
    def grasping_technique(self, acupoint):
        """拿捏手法模拟"""
        intensity = self.pressure_level * 9
        effect = f"对{acupoint}进行拿捏按摩，深度放松"
        
        self.physiological_effects["肌肉放松"] = self.pressure_level * 10
        self.physiological_effects["神经调节"] = self.pressure_level * 7
        
        return effect, intensity, self.physiological_effects.copy()
    
    def simulate_massage(self, acupoint, technique):
        """执行按摩模拟"""
        if technique in self.techniques:
            return self.techniques[technique](acupoint)
        else:
            return f"未知按摩手法: {technique}", 0, self.physiological_effects.copy()
    
    def get_technique_description(self, technique):
        """获取手法描述"""
        descriptions = {
            "按压": "用拇指或手掌按压穴位，力度由轻到重",
            "揉捏": "用拇指和食指揉捏肌肉，促进血液循环",
            "点按": "用指尖点按穴位，精准刺激",
            "推拿": "线性推动手法，舒缓经络",
            "振动": "快速振动手法，放松神经",
            "叩击": "轻快叩击，刺激表层组织",
            "摩擦": "快速摩擦产生热量，促进循环",
            "拿捏": "深度拿捏肌肉，缓解紧张"
        }
        return descriptions.get(technique, "未知手法")

class EnhancedFootGraphicsView(QGraphicsView):
    """增强版足部穴位图显示组件"""
    
    acupoint_clicked = pyqtSignal(str)  # 穴位点击信号
    acupoint_hovered = pyqtSignal(str)  # 穴位悬停信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene()
        self.setScene(self.scene)
        
        # 足部图像和穴位数据
        self.foot_image = None
        self.acupoints = {}
        self.labels = {}
        
        # 缩放控制
        self.zoom_factor = 1.0
        self.max_zoom = 3.0
        self.min_zoom = 0.5
        
        # 设置视图属性
        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        
    def load_foot_image(self, image_path):
        """加载足部图像"""
        pixmap = QPixmap(image_path)
        if not pixmap.isNull():
            self.foot_image = QGraphicsPixmapItem(pixmap)
            self.scene.addItem(self.foot_image)
            self.setSceneRect(self.foot_image.boundingRect())
            self.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)
    
    def add_acupoint(self, name, x, y, radius=15):
        """添加穴位点"""
        # 创建穴位点
        ellipse = QGraphicsEllipseItem(QRectF(x-radius, y-radius, radius*2, radius*2))
        ellipse.setBrush(QColor(255, 0, 0, 180))  # 半透明红色
        ellipse.setPen(QPen(Qt.red, 2))
        ellipse.setToolTip(name)
        ellipse.setData(0, name)  # 存储穴位名称
        ellipse.setAcceptHoverEvents(True)
        
        # 添加穴位标签
        label = self.scene.addSimpleText(name)
        label.setPos(x + radius + 5, y - radius)
        label.setBrush(Qt.darkRed)
        font = QFont("Arial", 8, QFont.Bold)
        label.setFont(font)
        
        self.scene.addItem(ellipse)
        self.acupoints[name] = ellipse
        self.labels[name] = label
    
    def wheelEvent(self, event):
        """鼠标滚轮缩放"""
        if event.angleDelta().y() > 0:
            self.zoom_in()
        else:
            self.zoom_out()
    
    def zoom_in(self):
        """放大"""
        if self.zoom_factor < self.max_zoom:
            self.zoom_factor *= 1.1
            self.set_transform()
    
    def zoom_out(self):
        """缩小"""
        if self.zoom_factor > self.min_zoom:
            self.zoom_factor /= 1.1
            self.set_transform()
    
    def set_transform(self):
        """设置变换"""
        self.resetTransform()
        self.scale(self.zoom_factor, self.zoom_factor)
    
    def mousePressEvent(self, event):
        """鼠标点击事件处理"""
        if event.button() == Qt.LeftButton:
            # 获取点击位置的场景坐标
            scene_pos = self.mapToScene(event.pos())
            items = self.scene.items(scene_pos)
            
            # 检查是否点击了穴位点
            for item in items:
                if isinstance(item, QGraphicsEllipseItem) and item.data(0):
                    acupoint_name = item.data(0)
                    self.acupoint_clicked.emit(acupoint_name)
                    # 高亮显示被点击的穴位
                    self.highlight_acupoint(acupoint_name)
                    return
        
        super().mousePressEvent(event)
    
    def highlight_acupoint(self, acupoint_name):
        """高亮显示穴位"""
        for name, ellipse in self.acupoints.items():
            if name == acupoint_name:
                ellipse.setBrush(QColor(255, 255, 0, 200))  # 黄色高亮
                ellipse.setPen(QPen(Qt.yellow, 3))
                self.labels[name].setBrush(Qt.darkBlue)
            else:
                ellipse.setBrush(QColor(255, 0, 0, 180))  # 恢复原色
                ellipse.setPen(QPen(Qt.red, 2))
                self.labels[name].setBrush(Qt.darkRed)

class UserProfileManager:
    """用户档案管理器"""
    
    def __init__(self, db_path="acupoints.db"):
        self.db_path = db_path
        self.current_user = None
        self.init_database()
    
    def init_database(self):
        """初始化用户数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 用户偏好表已在AcupointDatabase中创建
        conn.commit()
        conn.close()
    
    def create_user(self, name, preferred_techniques, sensitivity_level, 
                   preferred_duration, health_conditions, goals):
        """创建新用户"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO user_preferences 
                (user_name, preferred_techniques, sensitivity_level, preferred_duration, health_conditions, goals)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (name, ",".join(preferred_techniques), sensitivity_level, 
                  preferred_duration, ",".join(health_conditions), ",".join(goals)))
            conn.commit()
            self.current_user = name
            return True
        except sqlite3.IntegrityError:
            return False  # 用户名已存在
        finally:
            conn.close()
    
    def get_user(self, name):
        """获取用户信息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM user_preferences WHERE user_name=?", (name,))
        user = cursor.fetchone()
        conn.close()
        return user
    
    def update_user(self, name, **kwargs):
        """更新用户信息"""
        if not kwargs:
            return
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        set_clause = ", ".join([f"{key}=?" for key in kwargs.keys()])
        values = list(kwargs.values())
        values.append(name)
        
        cursor.execute(f"UPDATE user_preferences SET {set_clause} WHERE user_name=?", values)
        conn.commit()
        conn.close()
    
    def get_all_users(self):
        """获取所有用户"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT user_name FROM user_preferences ORDER BY created_date DESC")
        users = [row[0] for row in cursor.fetchall()]
        conn.close()
        return users
    
    def set_current_user(self, name):
        """设置当前用户"""
        if self.get_user(name):
            self.current_user = name
            return True
        return False

class AcupointInfoWidget(QWidget):
    """增强版穴位信息显示组件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 穴位名称
        self.name_label = QLabel("穴位信息")
        self.name_label.setFont(QFont("微软雅黑", 18, QFont.Bold))
        self.name_label.setAlignment(Qt.AlignCenter)
        self.name_label.setStyleSheet("color: #2E86AB; padding: 10px;")
        layout.addWidget(self.name_label)
        
        # 详细信息
        info_group = QGroupBox("详细信息")
        info_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        info_layout = QFormLayout()
        
        self.location_label = QLabel("")
        self.function_label = QTextBrowser()
        self.function_label.setMaximumHeight(80)
        self.technique_label = QLabel("")
        self.duration_label = QLabel("")
        self.intensity_label = QLabel("")
        self.category_label = QLabel("")
        self.meridian_label = QLabel("")
        self.contraindications_label = QLabel("")
        
        info_layout.addRow("位置:", self.location_label)
        info_layout.addRow("功能:", self.function_label)
        info_layout.addRow("按摩手法:", self.technique_label)
        info_layout.addRow("推荐时长:", self.duration_label)
        info_layout.addRow("推荐强度:", self.intensity_label)
        info_layout.addRow("类别:", self.category_label)
        info_layout.addRow("经络:", self.meridian_label)
        info_layout.addRow("禁忌:", self.contraindications_label)
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # 操作按钮
        button_layout = QHBoxLayout()
        
        self.video_button = QPushButton("观看视频演示")
        self.video_button.setIcon(QIcon("icons/video.png"))
        self.video_button.clicked.connect(self.show_video)
        
        self.audio_button = QPushButton("收听音频指导")
        self.audio_button.setIcon(QIcon("icons/audio.png"))
        self.audio_button.clicked.connect(self.play_audio)
        
        button_layout.addWidget(self.video_button)
        button_layout.addWidget(self.audio_button)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def update_info(self, acupoint_data):
        """更新穴位信息"""
        if acupoint_data:
            self.name_label.setText(acupoint_data[1])  # 名称
            self.location_label.setText(acupoint_data[2])  # 位置
            self.function_label.setText(acupoint_data[3])  # 功能
            self.technique_label.setText(acupoint_data[4])  # 手法
            self.duration_label.setText(acupoint_data[5])  # 时长
            self.intensity_label.setText(acupoint_data[6])  # 强度
            self.category_label.setText(acupoint_data[8])  # 类别
            self.meridian_label.setText(acupoint_data[9])  # 经络
            self.contraindications_label.setText(acupoint_data[10])  # 禁忌
            
            # 存储多媒体路径
            self.video_path = acupoint_data[11] if len(acupoint_data) > 11 else ""
            self.audio_path = acupoint_data[12] if len(acupoint_data) > 12 else ""
        else:
            self.clear_info()
    
    def clear_info(self):
        """清空信息"""
        self.name_label.setText("穴位信息")
        self.location_label.setText("")
        self.function_label.setText("")
        self.technique_label.setText("")
        self.duration_label.setText("")
        self.intensity_label.setText("")
        self.category_label.setText("")
        self.meridian_label.setText("")
        self.contraindications_label.setText("")
        self.video_path = ""
        self.audio_path = ""
    
    def show_video(self):
        """显示视频演示"""
        if hasattr(self, 'video_path') and self.video_path:
            # 在实际应用中，这里应该打开视频播放器
            QMessageBox.information(self, "视频演示", f"播放视频: {self.video_path}")
        else:
            QMessageBox.warning(self, "视频演示", "该穴位暂无视频演示")
    
    def play_audio(self):
        """播放音频指导"""
        if hasattr(self, 'audio_path') and self.audio_path:
            # 在实际应用中，这里应该播放音频
            QMessageBox.information(self, "音频指导", f"播放音频: {self.audio_path}")
        else:
            QMessageBox.warning(self, "音频指导", "该穴位暂无音频指导")

class MassageControlWidget(QWidget):
    """增强版按摩控制组件"""
    
    massage_started = pyqtSignal(str, str, int, int, int)  # 穴位, 手法, 时长, 强度, 压力
    massage_stopped = pyqtSignal()
    technique_changed = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self.is_massaging = False
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_progress)
        self.remaining_time = 0
        self.current_technique = "按压"
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 穴位和手法选择
        technique_group = QGroupBox("按摩设置")
        technique_layout = QFormLayout()
        
        self.acupoint_combo = QComboBox()
        self.technique_combo = QComboBox()
        self.technique_combo.addItems(["按压", "揉捏", "点按", "推拿", "振动", "叩击", "摩擦", "拿捏"])
        self.technique_combo.currentTextChanged.connect(self.on_technique_changed)
        
        technique_layout.addRow("穴位:", self.acupoint_combo)
        technique_layout.addRow("手法:", self.technique_combo)
        
        technique_group.setLayout(technique_layout)
        layout.addWidget(technique_group)
        
        # 手法描述
        self.technique_desc = QLabel("")
        self.technique_desc.setWordWrap(True)
        self.technique_desc.setStyleSheet("background-color: #F0F8FF; padding: 5px; border-radius: 5px;")
        layout.addWidget(self.technique_desc)
        
        # 参数控制
        param_group = QGroupBox("按摩参数")
        param_layout = QGridLayout()
        
        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(1, 60)  # 1-60分钟
        self.duration_spin.setValue(5)
        self.duration_spin.setSuffix(" 分钟")
        
        self.intensity_slider = QSlider(Qt.Horizontal)
        self.intensity_slider.setRange(1, 10)
        self.intensity_slider.setValue(5)
        self.intensity_label = QLabel("5")
        
        self.pressure_slider = QSlider(Qt.Horizontal)
        self.pressure_slider.setRange(1, 10)
        self.pressure_slider.setValue(5)
        self.pressure_label = QLabel("5")
        
        # 节奏选择
        self.rhythm_combo = QComboBox()
        self.rhythm_combo.addItems(["均匀", "轻快", "缓慢", "强弱交替"])
        
        param_layout.addWidget(QLabel("时长:"), 0, 0)
        param_layout.addWidget(self.duration_spin, 0, 1)
        param_layout.addWidget(QLabel("强度:"), 1, 0)
        param_layout.addWidget(self.intensity_slider, 1, 1)
        param_layout.addWidget(self.intensity_label, 1, 2)
        param_layout.addWidget(QLabel("压力:"), 2, 0)
        param_layout.addWidget(self.pressure_slider, 2, 1)
        param_layout.addWidget(self.pressure_label, 2, 2)
        param_layout.addWidget(QLabel("节奏:"), 3, 0)
        param_layout.addWidget(self.rhythm_combo, 3, 1)
        
        param_group.setLayout(param_layout)
        layout.addWidget(param_group)
        
        # 连接滑块和标签
        self.intensity_slider.valueChanged.connect(lambda v: self.intensity_label.setText(str(v)))
        self.pressure_slider.valueChanged.connect(lambda v: self.pressure_label.setText(str(v)))
        
        # 进度显示
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("QProgressBar::chunk { background-color: #4CAF50; }")
        layout.addWidget(self.progress_bar)
        
        # 时间显示
        self.time_label = QLabel("")
        self.time_label.setAlignment(Qt.AlignCenter)
        self.time_label.setVisible(False)
        layout.addWidget(self.time_label)
        
        # 控制按钮
        button_layout = QHBoxLayout()
        
        self.start_button = QPushButton("开始按摩")
        self.start_button.setIcon(QIcon("icons/start.png"))
        self.start_button.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-weight: bold; }")
        self.start_button.clicked.connect(self.start_massage)
        
        self.pause_button = QPushButton("暂停")
        self.pause_button.setIcon(QIcon("icons/pause.png"))
        self.pause_button.setEnabled(False)
        self.pause_button.clicked.connect(self.pause_massage)
        
        self.stop_button = QPushButton("停止按摩")
        self.stop_button.setIcon(QIcon("icons/stop.png"))
        self.stop_button.setStyleSheet("QPushButton { background-color: #F44336; color: white; font-weight: bold; }")
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.stop_massage)
        
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.pause_button)
        button_layout.addWidget(self.stop_button)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def set_acupoints(self, acupoints):
        """设置穴位列表"""
        self.acupoint_combo.clear()
        for acupoint in acupoints:
            self.acupoint_combo.addItem(acupoint[1])  # 穴位名称
    
    def on_technique_changed(self, technique):
        """手法改变事件"""
        self.current_technique = technique
        self.technique_changed.emit(technique)
        
        # 更新手法描述
        simulator = AdvancedMassageSimulator()
        desc = simulator.get_technique_description(technique)
        self.technique_desc.setText(f"当前手法: {technique}\n{desc}")
    
    def start_massage(self):
        """开始按摩"""
        acupoint = self.acupoint_combo.currentText()
        technique = self.technique_combo.currentText()
        duration = self.duration_spin.value()
        intensity = self.intensity_slider.value()
        pressure = self.pressure_slider.value()
        
        if not acupoint:
            QMessageBox.warning(self, "警告", "请选择穴位")
            return
        
        self.is_massaging = True
        self.remaining_time = duration * 60  # 转换为秒
        
        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(self.remaining_time)
        self.progress_bar.setValue(0)
        
        self.time_label.setVisible(True)
        self.update_time_display()
        
        self.start_button.setEnabled(False)
        self.pause_button.setEnabled(True)
        self.stop_button.setEnabled(True)
        
        self.timer.start(1000)  # 每秒更新一次
        
        self.massage_started.emit(acupoint, technique, duration, intensity, pressure)
    
    def pause_massage(self):
        """暂停/继续按摩"""
        if self.timer.isActive():
            self.timer.stop()
            self.pause_button.setText("继续")
        else:
            self.timer.start(1000)
            self.pause_button.setText("暂停")
    
    def stop_massage(self):
        """停止按摩"""
        self.is_massaging = False
        self.timer.stop()
        
        self.progress_bar.setVisible(False)
        self.time_label.setVisible(False)
        self.start_button.setEnabled(True)
        self.pause_button.setEnabled(False)
        self.pause_button.setText("暂停")
        self.stop_button.setEnabled(False)
        
        self.massage_stopped.emit()
    
    def update_progress(self):
        """更新进度"""
        if self.remaining_time > 0:
            self.remaining_time -= 1
            self.progress_bar.setValue(self.progress_bar.maximum() - self.remaining_time)
            self.update_time_display()
        else:
            self.stop_massage()
            QMessageBox.information(self, "按摩完成", "按摩疗程已完成！")
    
    def update_time_display(self):
        """更新时间显示"""
        minutes = self.remaining_time // 60
        seconds = self.remaining_time % 60
        self.time_label.setText(f"剩余时间: {minutes:02d}:{seconds:02d}")

class StatisticsWidget(QWidget):
    """统计信息显示组件"""
    
    def __init__(self, db_path="acupoints.db", parent=None):
        super().__init__(parent)
        self.db_path = db_path
        self.init_ui()
        self.load_statistics()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 标题
        title = QLabel("按摩统计")
        title.setFont(QFont("微软雅黑", 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # 统计标签页
        self.tabs = QTabWidget()
        
        # 总体统计标签
        overall_tab = QWidget()
        overall_layout = QVBoxLayout()
        
        self.stats_text = QTextBrowser()
        overall_layout.addWidget(self.stats_text)
        
        overall_tab.setLayout(overall_layout)
        self.tabs.addTab(overall_tab, "总体统计")
        
        # 图表标签
        chart_tab = QWidget()
        chart_layout = QVBoxLayout()
        
        # 使用matplotlib显示图表
        self.figure = Figure(figsize=(10, 8), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        chart_layout.addWidget(self.canvas)
        
        chart_tab.setLayout(chart_layout)
        self.tabs.addTab(chart_tab, "图表分析")
        
        layout.addWidget(self.tabs)
        self.setLayout(layout)
    
    def load_statistics(self):
        """加载统计信息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 获取总体统计
        cursor.execute("SELECT COUNT(*) FROM massage_records")
        total_sessions = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT user_name) FROM massage_records")
        total_users = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT acupoint_name) FROM massage_records")
        total_acupoints = cursor.fetchone()[0]
        
        cursor.execute("SELECT AVG(duration) FROM massage_records")
        avg_duration = cursor.fetchone()[0] or 0
        
        # 获取最受欢迎的穴位
        popular_acupoints = cursor.execute('''
            SELECT acupoint_name, COUNT(*) as count 
            FROM massage_records 
            GROUP BY acupoint_name 
            ORDER BY count DESC 
            LIMIT 5
        ''').fetchall()
        
        # 获取最常用的手法
        popular_techniques = cursor.execute('''
            SELECT technique, COUNT(*) as count 
            FROM massage_records 
            GROUP BY technique 
            ORDER BY count DESC 
            LIMIT 5
        ''').fetchall()
        
        conn.close()
        
        # 更新统计文本
        stats_text = f"""
        <h3>总体统计</h3>
        <p><b>总按摩次数:</b> {total_sessions}</p>
        <p><b>用户数量:</b> {total_users}</p>
        <p><b>使用穴位数量:</b> {total_acupoints}</p>
        <p><b>平均按摩时长:</b> {avg_duration:.1f} 分钟</p>
        
        <h3>最受欢迎穴位</h3>
        <ol>
        """
        
        for acupoint, count in popular_acupoints:
            stats_text += f"<li>{acupoint}: {count} 次</li>"
        
        stats_text += "</ol><h3>最常用手法</h3><ol>"
        
        for technique, count in popular_techniques:
            stats_text += f"<li>{technique}: {count} 次</li>"
        
        stats_text += "</ol>"
        
        self.stats_text.setHtml(stats_text)
        
        # 更新图表
        self.update_charts(popular_acupoints, popular_techniques)
    
    def update_charts(self, popular_acupoints, popular_techniques):
        """更新图表"""
        self.figure.clear()
        
        # 穴位使用频率图表
        ax1 = self.figure.add_subplot(211)
        acupoint_names = [item[0] for item in popular_acupoints]
        acupoint_counts = [item[1] for item in popular_acupoints]
        
        bars = ax1.bar(acupoint_names, acupoint_counts, color='skyblue')
        ax1.set_title('最受欢迎穴位')
        ax1.set_ylabel('使用次数')
        
        # 在柱状图上添加数值标签
        for bar, count in zip(bars, acupoint_counts):
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height,
                    f'{count}', ha='center', va='bottom')
        
        # 手法使用频率图表
        ax2 = self.figure.add_subplot(212)
        technique_names = [item[0] for item in popular_techniques]
        technique_counts = [item[1] for item in popular_techniques]
        
        bars = ax2.bar(technique_names, technique_counts, color='lightgreen')
        ax2.set_title('最常用手法')
        ax2.set_ylabel('使用次数')
        
        # 在柱状图上添加数值标签
        for bar, count in zip(bars, technique_counts):
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height,
                    f'{count}', ha='center', va='bottom')
        
        self.figure.tight_layout()
        self.canvas.draw()

class UserRegistrationDialog(QDialog):
    """用户注册对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("用户注册")
        self.resize(500, 400)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 基本信息
        info_group = QGroupBox("基本信息")
        info_layout = QFormLayout()
        
        self.name_edit = QLineEdit()
        self.age_spin = QSpinBox()
        self.age_spin.setRange(1, 120)
        
        self.gender_group = QButtonGroup()
        self.gender_male = QRadioButton("男")
        self.gender_female = QRadioButton("女")
        self.gender_group.addButton(self.gender_male)
        self.gender_group.addButton(self.gender_female)
        
        gender_layout = QHBoxLayout()
        gender_layout.addWidget(self.gender_male)
        gender_layout.addWidget(self.gender_female)
        gender_widget = QWidget()
        gender_widget.setLayout(gender_layout)
        
        info_layout.addRow("姓名:", self.name_edit)
        info_layout.addRow("年龄:", self.age_spin)
        info_layout.addRow("性别:", gender_widget)
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # 健康状况
        health_group = QGroupBox("健康状况")
        health_layout = QVBoxLayout()
        
        self.health_conditions = []
        conditions = ["高血压", "糖尿病", "心脏病", "关节炎", "失眠", "消化问题", "其他"]
        
        for condition in conditions:
            checkbox = QCheckBox(condition)
            self.health_conditions.append(checkbox)
            health_layout.addWidget(checkbox)
        
        health_group.setLayout(health_layout)
        layout.addWidget(health_group)
        
        # 按摩偏好
        pref_group = QGroupBox("按摩偏好")
        pref_layout = QFormLayout()  # 修复这里的变量名
        
        self.sensitivity_slider = QSlider(Qt.Horizontal)
        self.sensitivity_slider.setRange(1, 10)
        self.sensitivity_slider.setValue(5)
        self.sensitivity_label = QLabel("5")
        
        self.preferred_duration = QSpinBox()
        self.preferred_duration.setRange(5, 60)
        self.preferred_duration.setValue(15)
        self.preferred_duration.setSuffix(" 分钟")
        
        self.sensitivity_slider.valueChanged.connect(lambda v: self.sensitivity_label.setText(str(v)))
        
        pref_layout.addRow("敏感度:", self.sensitivity_slider)
        pref_layout.addRow("", self.sensitivity_label)
        pref_layout.addRow("偏好时长:", self.preferred_duration)
        
        pref_group.setLayout(pref_layout)  # 修复这里的变量名
        layout.addWidget(pref_group)
        
        # 按钮
        button_layout = QHBoxLayout()
        
        self.ok_button = QPushButton("确定")
        self.ok_button.clicked.connect(self.accept)
        
        self.cancel_button = QPushButton("取消")
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def get_user_data(self):
        """获取用户数据"""
        name = self.name_edit.text().strip()
        age = self.age_spin.value()
        gender = "男" if self.gender_male.isChecked() else "女"
        
        health_conditions = []
        for checkbox in self.health_conditions:
            if checkbox.isChecked():
                health_conditions.append(checkbox.text())
        
        sensitivity = self.sensitivity_slider.value()
        preferred_duration = self.preferred_duration.value()
        
        return {
            "name": name,
            "age": age,
            "gender": gender,
            "health_conditions": health_conditions,
            "sensitivity": sensitivity,
            "preferred_duration": preferred_duration
        }

class FeedbackDialog(QDialog):
    """按摩反馈对话框"""
    
    def __init__(self, acupoint, technique, duration, parent=None):
        super().__init__(parent)
        self.acupoint = acupoint
        self.technique = technique
        self.duration = duration
        self.setWindowTitle("按摩反馈")
        self.resize(400, 300)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 按摩信息
        info_label = QLabel(f"穴位: {self.acupoint}\n手法: {self.technique}\n时长: {self.duration}分钟")
        info_label.setStyleSheet("background-color: #E3F2FD; padding: 10px; border-radius: 5px;")
        layout.addWidget(info_label)
        
        # 评分
        rating_group = QGroupBox("请评价本次按摩效果")
        rating_layout = QVBoxLayout()
        
        self.rating_slider = QSlider(Qt.Horizontal)
        self.rating_slider.setRange(1, 10)
        self.rating_slider.setValue(8)
        self.rating_label = QLabel("8/10")
        
        rating_layout.addWidget(QLabel("满意度评分:"))
        rating_layout.addWidget(self.rating_slider)
        rating_layout.addWidget(self.rating_label)
        
        self.rating_slider.valueChanged.connect(lambda v: self.rating_label.setText(f"{v}/10"))
        
        rating_group.setLayout(rating_layout)
        layout.addWidget(rating_group)
        
        # 反馈文本
        feedback_group = QGroupBox("详细反馈（可选）")
        feedback_layout = QVBoxLayout()
        
        self.feedback_text = QTextEdit()
        self.feedback_text.setPlaceholderText("请描述按摩后的感受、效果或任何建议...")
        
        feedback_layout.addWidget(self.feedback_text)
        feedback_group.setLayout(feedback_layout)
        layout.addWidget(feedback_group)
        
        # 按钮 - 修复这里的拼写错误
        button_layout = QHBoxLayout()
        
        self.submit_button = QPushButton("提交反馈")
        self.submit_button.clicked.connect(self.accept)
        
        self.skip_button = QPushButton("跳过")
        self.skip_button.clicked.connect(self.reject)
        
        button_layout.addWidget(self.submit_button)
        button_layout.addWidget(self.skip_button)  # 修复拼写错误
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def get_feedback(self):
        """获取反馈数据"""
        return {
            "rating": self.rating_slider.value(),
            "text": self.feedback_text.toPlainText()
        }

class EnhancedFootCareSystem(QMainWindow):
    """增强版智能足疗呵护系统主窗口"""
    
    def __init__(self):
        super().__init__()
        self.init_components()
        self.init_ui()
        self.load_data()
        self.apply_stylesheet()
    
    def init_components(self):
        """初始化组件"""
        self.acupoint_db = AcupointDatabase()
        self.massage_simulator = AdvancedMassageSimulator()
        self.user_manager = UserProfileManager()
        
        # 创建界面组件
        self.acupoint_info = AcupointInfoWidget()
        self.foot_view = EnhancedFootGraphicsView()
        self.massage_control = MassageControlWidget()
        self.statistics_widget = StatisticsWidget()
        
        # 多媒体播放器
        self.media_player = QMediaPlayer()
        self.video_widget = QVideoWidget()
        
        # 连接信号
        self.foot_view.acupoint_clicked.connect(self.on_acupoint_clicked)
        self.massage_control.massage_started.connect(self.on_massage_started)
        self.massage_control.massage_stopped.connect(self.on_massage_stopped)
        self.massage_control.technique_changed.connect(self.on_technique_changed)
    
    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("智能足疗呵护系统 - 专业版")
        self.setGeometry(100, 100, 1400, 900)
        
        # 创建中央部件和主标签页
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_tabs = QTabWidget()
        main_layout = QVBoxLayout()
        main_layout.addWidget(main_tabs)
        central_widget.setLayout(main_layout)
        
        # 标签页1：按摩主界面
        massage_tab = QWidget()
        massage_layout = QHBoxLayout()
        
        # 左侧：穴位图和信息
        left_splitter = QSplitter(Qt.Vertical)
        left_splitter.addWidget(self.foot_view)
        left_splitter.addWidget(self.acupoint_info)
        left_splitter.setSizes([600, 300])
        
        # 右侧：按摩控制
        right_widget = QWidget()
        right_layout = QVBoxLayout()
        right_widget.setLayout(right_layout)
        
        right_layout.addWidget(self.massage_control)
        
        # 添加到按摩标签页
        massage_layout.addWidget(left_splitter, 2)
        massage_layout.addWidget(right_widget, 1)
        massage_tab.setLayout(massage_layout)
        
        main_tabs.addTab(massage_tab, "穴位按摩")
        
        # 标签页2：统计信息
        main_tabs.addTab(self.statistics_widget, "统计信息")
        
        # 标签页3：视频学习
        video_tab = self.create_video_tab()
        main_tabs.addTab(video_tab, "视频学习")
        
        # 创建菜单栏
        self.create_menubar()
        
        # 创建工具栏
        self.create_toolbar()
        
        # 创建状态栏
        self.create_statusbar()
    
    def create_video_tab(self):
        """创建视频学习标签页"""
        tab = QWidget()
        layout = QVBoxLayout()
        
        # 视频标题
        title = QLabel("足部按摩教学视频")
        title.setFont(QFont("微软雅黑", 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # 视频播放区域
        video_group = QGroupBox("视频播放器")
        video_layout = QVBoxLayout()
        
        video_layout.addWidget(self.video_widget)
        self.media_player.setVideoOutput(self.video_widget)
        
        # 视频控制
        control_layout = QHBoxLayout()
        
        self.play_button = QPushButton("播放")
        self.play_button.clicked.connect(self.play_video)
        
        self.pause_button = QPushButton("暂停")
        self.pause_button.clicked.connect(self.pause_video)
        
        self.stop_button = QPushButton("停止")
        self.stop_button.clicked.connect(self.stop_video)
        
        control_layout.addWidget(self.play_button)
        control_layout.addWidget(self.pause_button)
        control_layout.addWidget(self.stop_button)
        control_layout.addStretch()
        
        video_layout.addLayout(control_layout)
        video_group.setLayout(video_layout)
        layout.addWidget(video_group)
        
        # 视频列表
        video_list_group = QGroupBox("可用视频")
        video_list_layout = QVBoxLayout()
        
        self.video_list = QListWidget()
        # 添加示例视频（实际应用中应从数据库加载）
        self.video_list.addItems(["足底按摩基础技巧", "涌泉穴按摩方法", "太冲穴降压按摩", "全套足部保健按摩"])
        
        self.video_list.itemClicked.connect(self.on_video_selected)
        video_list_layout.addWidget(self.video_list)
        
        video_list_group.setLayout(video_list_layout)
        layout.addWidget(video_list_group)
        
        tab.setLayout(layout)
        return tab
    
    def create_menubar(self):
        """创建菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu("文件")
        
        new_user_action = QAction("新建用户", self)
        new_user_action.triggered.connect(self.new_user)
        file_menu.addAction(new_user_action)
        
        switch_user_action = QAction("切换用户", self)
        switch_user_action.triggered.connect(self.switch_user)
        file_menu.addAction(switch_user_action)
        
        file_menu.addSeparator()
        
        import_action = QAction("导入数据", self)
        import_action.triggered.connect(self.import_data)
        file_menu.addAction(import_action)
        
        export_action = QAction("导出数据", self)
        export_action.triggered.connect(self.export_data)
        file_menu.addAction(export_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("退出", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 工具菜单
        tools_menu = menubar.addMenu("工具")
        
        user_manager_action = QAction("用户管理", self)
        user_manager_action.triggered.connect(self.show_user_manager)
        tools_menu.addAction(user_manager_action)
        
        acupoint_manager_action = QAction("穴位管理", self)
        acupoint_manager_action.triggered.connect(self.show_acupoint_manager)
        tools_menu.addAction(acupoint_manager_action)
        
        tools_menu.addSeparator()
        
        settings_action = QAction("系统设置", self)
        settings_action.triggered.connect(self.show_settings)
        tools_menu.addAction(settings_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu("帮助")
        
        about_action = QAction("关于", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def create_toolbar(self):
        """创建工具栏"""
        toolbar = QToolBar("主工具栏")
        self.addToolBar(toolbar)
        
        # 用户相关工具
        user_action = QAction(QIcon("icons/user.png"), "当前用户", self)
        user_action.triggered.connect(self.show_current_user)
        toolbar.addAction(user_action)
        
        toolbar.addSeparator()
        
        # 按摩工具
        start_action = QAction(QIcon("icons/start.png"), "快速开始", self)
        start_action.triggered.connect(self.quick_start)
        toolbar.addAction(start_action)
        
        history_action = QAction(QIcon("icons/history.png"), "按摩历史", self)
        history_action.triggered.connect(self.show_massage_history)
        toolbar.addAction(history_action)
        
        toolbar.addSeparator()
        
        # 学习工具
        learn_action = QAction(QIcon("icons/learn.png"), "学习模式", self)
        learn_action.triggered.connect(self.enter_learning_mode)
        toolbar.addAction(learn_action)
    
    def create_statusbar(self):
        """创建状态栏"""
        statusbar = self.statusBar()
        
        # 当前用户显示
        self.user_label = QLabel("未选择用户")
        statusbar.addWidget(self.user_label)
        
        # 系统时间
        self.time_label = QLabel()
        statusbar.addPermanentWidget(self.time_label)
        
        # 更新时间显示
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_time)
        self.timer.start(1000)
        self.update_time()
    
    def apply_stylesheet(self):
        """应用样式表"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #F5F5F5;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #CCCCCC;
                border-radius: 5px;
                margin-top: 1ex;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 5px 10px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #0D47A1;
            }
            QTabWidget::pane {
                border: 1px solid #C2C7CB;
            }
            QTabBar::tab {
                background-color: #E1E1E1;
                color: #333333;
                padding: 8px 20px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background-color: #2196F3;
                color: white;
            }
        """)
    
    def load_data(self):
        """加载数据"""
        # 加载穴位数据
        acupoints = self.acupoint_db.get_all_acupoints()
        self.massage_control.set_acupoints(acupoints)
        
        # 加载足部图像和穴位点
        self.foot_view.load_foot_image("images/foot.png")  # 需要准备足部图像
        
        # 添加穴位点（这里需要根据实际图像坐标调整）
        for acupoint in acupoints:
            x, y = self.get_acupoint_coordinates(acupoint[1])
            if x and y:
                self.foot_view.add_acupoint(acupoint[1], x, y)
    
    def get_acupoint_coordinates(self, acupoint_name):
        """获取穴位在图像上的坐标（简化实现）"""
        coordinates = {
            "涌泉穴": (200, 400),
            "太冲穴": (300, 200),
            "足三里": (400, 300),
            "三阴交": (350, 350),
            "太溪穴": (250, 300),
            "昆仑穴": (320, 250)
        }
        return coordinates.get(acupoint_name, (None, None))
    
    def update_time(self):
        """更新时间显示"""
        current_time = QDateTime.currentDateTime().toString("yyyy-MM-dd hh:mm:ss")
        self.time_label.setText(current_time)
    
    def on_acupoint_clicked(self, acupoint_name):
        """穴位点击事件处理"""
        acupoint_data = self.acupoint_db.get_acupoint_by_name(acupoint_name)
        if acupoint_data:
            self.acupoint_info.update_info(acupoint_data)
    
    def on_technique_changed(self, technique):
        """手法改变事件处理"""
        # 可以在这里更新模拟器的节奏模式等
        rhythm = self.massage_control.rhythm_combo.currentText()
        self.massage_simulator.set_rhythm_pattern(rhythm)
    
    def on_massage_started(self, acupoint, technique, duration, intensity, pressure):
        """按摩开始事件处理"""
        # 更新按摩模拟器参数
        self.massage_simulator.pressure_level = pressure
        self.massage_simulator.speed_level = intensity
        self.massage_simulator.duration = duration
        
        # 执行按摩模拟
        effect, intensity_value, physiological_effects = self.massage_simulator.simulate_massage(acupoint, technique)
        
        # 显示按摩效果
        effect_text = f"开始对{acupoint}进行{technique}按摩\n\n预计效果: {effect}\n强度值: {intensity_value}\n\n生理效应:\n"
        
        for effect_name, effect_value in physiological_effects.items():
            effect_text += f"{effect_name}: {effect_value}/100\n"
        
        QMessageBox.information(self, "按摩开始", effect_text)
    
    def on_massage_stopped(self):
        """按摩停止事件处理"""
        # 显示反馈对话框
        feedback_dialog = FeedbackDialog(
            self.massage_control.acupoint_combo.currentText(),
            self.massage_control.technique_combo.currentText(),
            self.massage_control.duration_spin.value(),
            self
        )
        
        if feedback_dialog.exec_() == QDialog.Accepted:
            feedback_data = feedback_dialog.get_feedback()
            
            # 保存按摩记录
            if self.user_manager.current_user:
                self.acupoint_db.add_massage_record(
                    self.user_manager.current_user,
                    self.massage_control.acupoint_combo.currentText(),
                    self.massage_control.technique_combo.currentText(),
                    self.massage_control.duration_spin.value(),
                    self.massage_control.intensity_slider.value(),
                    self.massage_control.pressure_slider.value(),
                    feedback_data["rating"],
                    feedback_data["text"]
                )
                
                # 更新统计信息
                self.statistics_widget.load_statistics()
        
        QMessageBox.information(self, "按摩停止", "按摩已停止")
    
    def new_user(self):
        """新建用户"""
        dialog = UserRegistrationDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            user_data = dialog.get_user_data()
            
            if not user_data["name"]:
                QMessageBox.warning(self, "错误", "请输入用户名")
                return
            
            # 创建用户
            success = self.user_manager.create_user(
                user_data["name"],
                ["按压", "揉捏"],  # 默认偏好手法
                user_data["sensitivity"],
                user_data["preferred_duration"],
                user_data["health_conditions"],
                ["放松", "保健"]  # 默认目标
            )
            
            if success:
                self.user_manager.set_current_user(user_data["name"])
                self.user_label.setText(f"当前用户: {user_data['name']}")
                QMessageBox.information(self, "成功", f"用户 {user_data['name']} 创建成功！")
            else:
                QMessageBox.warning(self, "错误", "用户名已存在")
    
    def switch_user(self):
        """切换用户"""
        users = self.user_manager.get_all_users()
        
        if not users:
            QMessageBox.information(self, "提示", "暂无用户，请先创建用户")
            return
        
        user, ok = QInputDialog.getItem(self, "切换用户", "选择用户:", users, 0, False)
        
        if ok and user:
            self.user_manager.set_current_user(user)
            self.user_label.setText(f"当前用户: {user}")
    
    def show_current_user(self):
        """显示当前用户信息"""
        if self.user_manager.current_user:
            user_data = self.user_manager.get_user(self.user_manager.current_user)
            if user_data:
                info = f"""
                用户名: {user_data[0]}
                偏好手法: {user_data[1]}
                敏感度: {user_data[2]}/10
                偏好时长: {user_data[3]}分钟
                健康状况: {user_data[4]}
                目标: {user_data[5]}
                创建时间: {user_data[6]}
                """
                QMessageBox.information(self, "用户信息", info)
        else:
            QMessageBox.information(self, "用户信息", "当前未选择用户")
    
    def show_user_manager(self):
        """显示用户管理对话框"""
        from PyQt5.QtWidgets import QDialog, QTableWidget, QTableWidgetItem, QDialogButtonBox
        
        dialog = QDialog(self)
        dialog.setWindowTitle("用户管理")
        dialog.resize(700, 400)
        
        layout = QVBoxLayout()
        
        # 用户表格
        table = QTableWidget()
        table.setColumnCount(7)
        table.setHorizontalHeaderLabels(["姓名", "偏好手法", "敏感度", "偏好时长", "健康状况", "目标", "创建时间"])
        
        # 填充数据
        users = self.user_manager.get_all_users()
        table.setRowCount(len(users))
        
        for row, user_name in enumerate(users):
            user_data = self.user_manager.get_user(user_name)
            if user_data:
                table.setItem(row, 0, QTableWidgetItem(user_data[0]))
                table.setItem(row, 1, QTableWidgetItem(user_data[1]))
                table.setItem(row, 2, QTableWidgetItem(str(user_data[2])))
                table.setItem(row, 3, QTableWidgetItem(str(user_data[3])))
                table.setItem(row, 4, QTableWidgetItem(user_data[4]))
                table.setItem(row, 5, QTableWidgetItem(user_data[5]))
                table.setItem(row, 6, QTableWidgetItem(user_data[6]))
        
        layout.addWidget(table)
        
        # 按钮
        button_layout = QHBoxLayout()
        
        delete_button = QPushButton("删除用户")
        delete_button.clicked.connect(lambda: self.delete_user(table, dialog))
        
        button_box = QDialogButtonBox(QDialogButtonBox.Ok)
        button_box.accepted.connect(dialog.accept)
        
        button_layout.addWidget(delete_button)
        button_layout.addStretch()
        button_layout.addWidget(button_box)
        
        layout.addLayout(button_layout)
        
        dialog.setLayout(layout)
        dialog.exec_()
    
    def delete_user(self, table, dialog):
        """删除用户"""
        current_row = table.currentRow()
        if current_row >= 0:
            user_name = table.item(current_row, 0).text()
            reply = QMessageBox.question(self, "确认删除", f"确定要删除用户 {user_name} 吗？")
            
            if reply == QMessageBox.Yes:
                # 在实际应用中，这里应该从数据库删除用户
                QMessageBox.information(self, "提示", "用户删除功能需连接数据库实现")
                # 刷新表格
                dialog.accept()
                self.show_user_manager()
        else:
            QMessageBox.warning(self, "错误", "请先选择要删除的用户")
    
    def show_acupoint_manager(self):
        """显示穴位管理对话框"""
        QMessageBox.information(self, "穴位管理", "穴位管理功能开发中...")
    
    def show_massage_history(self):
        """显示按摩历史"""
        if not self.user_manager.current_user:
            QMessageBox.warning(self, "错误", "请先选择用户")
            return
        
        records = self.acupoint_db.get_user_records(self.user_manager.current_user)
        
        dialog = QDialog(self)
        dialog.setWindowTitle("按摩历史")
        dialog.resize(800, 400)
        
        layout = QVBoxLayout()
        
        # 历史记录表格
        table = QTableWidget()
        table.setColumnCount(8)
        table.setHorizontalHeaderLabels(["穴位", "手法", "时长", "强度", "压力", "评分", "反馈", "时间"])
        
        table.setRowCount(len(records))
        
        for row, record in enumerate(records):
            table.setItem(row, 0, QTableWidgetItem(record[2]))  # 穴位
            table.setItem(row, 1, QTableWidgetItem(record[3]))  # 手法
            table.setItem(row, 2, QTableWidgetItem(str(record[4])))  # 时长
            table.setItem(row, 3, QTableWidgetItem(str(record[5])))  # 强度
            table.setItem(row, 4, QTableWidgetItem(str(record[6])))  # 压力
            table.setItem(row, 5, QTableWidgetItem(str(record[7])))  # 评分
            table.setItem(row, 6, QTableWidgetItem(record[8] or ""))  # 反馈
            table.setItem(row, 7, QTableWidgetItem(record[9]))  # 时间
        
        layout.addWidget(table)
        
        # 按钮
        button_box = QDialogButtonBox(QDialogButtonBox.Ok)
        button_box.accepted.connect(dialog.accept)
        layout.addWidget(button_box)
        
        dialog.setLayout(layout)
        dialog.exec_()
    
    def quick_start(self):
        """快速开始按摩"""
        if not self.user_manager.current_user:
            QMessageBox.warning(self, "错误", "请先选择用户")
            return
        
        # 使用用户偏好设置
        user_data = self.user_manager.get_user(self.user_manager.current_user)
        if user_data:
            # 设置默认参数
            self.massage_control.duration_spin.setValue(int(user_data[3]))
            self.massage_control.intensity_slider.setValue(int(user_data[2]))
            
            # 选择最常用的穴位
            popular = self.acupoint_db.get_popular_acupoints(1)
            if popular:
                self.massage_control.acupoint_combo.setCurrentText(popular[0][0])
        
        # 切换到按摩标签页
        self.centralWidget().findChild(QTabWidget).setCurrentIndex(0)
        QMessageBox.information(self, "快速开始", "已根据您的偏好设置参数，点击开始按摩即可")
    
    def enter_learning_mode(self):
        """进入学习模式"""
        QMessageBox.information(self, "学习模式", "学习模式功能开发中...")
    
    def play_video(self):
        """播放视频"""
        QMessageBox.information(self, "视频播放", "视频播放功能需连接实际视频文件")
    
    def pause_video(self):
        """暂停视频"""
        self.media_player.pause()
    
    def stop_video(self):
        """停止视频"""
        self.media_player.stop()
    
    def on_video_selected(self, item):
        """视频选择事件"""
        QMessageBox.information(self, "视频选择", f"已选择: {item.text()}")
    
    def import_data(self):
        """导入数据"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "导入数据", "", "JSON文件 (*.json);;CSV文件 (*.csv);;所有文件 (*)"
        )
        if file_path:
            try:
                if file_path.endswith('.json'):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    # 处理导入的数据
                    QMessageBox.information(self, "导入成功", "数据导入成功！")
                elif file_path.endswith('.csv'):
                    # 处理CSV导入
                    QMessageBox.information(self, "导入成功", "CSV数据导入成功！")
            except Exception as e:
                QMessageBox.critical(self, "导入失败", f"数据导入失败: {str(e)}")
    
    def export_data(self):
        """导出数据"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出数据", "", "JSON文件 (*.json);;CSV文件 (*.csv);;所有文件 (*)"
        )
        if file_path:
            try:
                # 准备导出数据
                export_data = {
                    "acupoints": self.acupoint_db.get_all_acupoints(),
                    "user_profiles": self.user_manager.get_all_users(),
                    "massage_records": self.acupoint_db.get_user_records(self.user_manager.current_user) if self.user_manager.current_user else []
                }
                
                if file_path.endswith('.json'):
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump(export_data, f, ensure_ascii=False, indent=2)
                elif file_path.endswith('.csv'):
                    # 导出为CSV格式
                    pass
                
                QMessageBox.information(self, "导出成功", "数据导出成功！")
            except Exception as e:
                QMessageBox.critical(self, "导出失败", f"数据导出失败: {str(e)}")
    
    def show_settings(self):
        """显示系统设置对话框"""
        QMessageBox.information(self, "系统设置", "系统设置功能开发中...")
    
    def show_about(self):
        """显示关于信息"""
        about_text = """
        <h2>智能足疗呵护系统 专业版</h2>
        <p>版本: 2.0</p>
        <p>开发团队: 健康科技团队</p>
        <p>版权所有 © 2023</p>
        <p>本系统提供专业的足部穴位按摩指导，帮助用户改善健康状况。</p>
        <p>功能包括：穴位识别、按摩模拟、用户管理、数据统计等。</p>
        """
        QMessageBox.about(self, "关于", about_text)

def main():
    """主函数"""
    app = QApplication(sys.argv)
    
    # 设置应用程序样式
    app.setStyle("Fusion")
    
    # 设置应用程序字体
    app.setFont(QFont("微软雅黑", 10))
    
    # 创建并显示主窗口
    window = EnhancedFootCareSystem()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    # 创建必要的目录
    for directory in ["images", "videos", "audio", "icons"]:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"创建目录: {directory}")
    
    # 如果数据库文件存在，先备份然后删除，确保使用新的表结构
    db_path = "acupoints.db"
    if os.path.exists(db_path):
        backup_path = f"acupoints_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        os.rename(db_path, backup_path)
        print(f"已备份旧数据库: {backup_path}")
    
    main()