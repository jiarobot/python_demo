import sys
import os
import json
import time
import random
import math
import sqlite3
from datetime import datetime, timedelta
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QPushButton, QTabWidget, 
                             QTextEdit, QLineEdit, QListWidget, QListWidgetItem,
                             QMessageBox, QProgressBar, QFrame, QSplitter,
                             QFileDialog, QComboBox, QSpinBox, QCheckBox, QGroupBox,
                             QTableWidget, QTableWidgetItem, QHeaderView, QDialog,
                             QFormLayout, QDialogButtonBox, QCalendarWidget)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QDate
from PyQt5.QtGui import QFont, QPalette, QColor, QPixmap, QIcon, QPainter, QPen


class DatabaseManager:
    """数据库管理类"""
    def __init__(self):
        self.db_path = "kunlun_mirror.db"
        self.init_database()
    
    def init_database(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建占卜记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS divination_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question TEXT NOT NULL,
                result TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                divination_type TEXT NOT NULL
            )
        ''')
        
        # 创建运势记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS fortune_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                birth_date TEXT NOT NULL,
                zodiac TEXT NOT NULL,
                fortune_type TEXT NOT NULL,
                result TEXT NOT NULL,
                timestamp TEXT NOT NULL
            )
        ''')
        
        # 创建工具使用记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tool_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tool_name TEXT NOT NULL,
                input_data TEXT,
                output_data TEXT NOT NULL,
                timestamp TEXT NOT NULL
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def save_divination_record(self, question, result, divination_type):
        """保存占卜记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO divination_records (question, result, timestamp, divination_type)
            VALUES (?, ?, ?, ?)
        ''', (question, result, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), divination_type))
        
        conn.commit()
        conn.close()
    
    def get_divination_history(self, limit=50):
        """获取占卜历史记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT question, result, timestamp, divination_type 
            FROM divination_records 
            ORDER BY timestamp DESC 
            LIMIT ?
        ''', (limit,))
        
        records = cursor.fetchall()
        conn.close()
        return records
    
    def save_fortune_record(self, name, birth_date, zodiac, fortune_type, result):
        """保存运势记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO fortune_records (name, birth_date, zodiac, fortune_type, result, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (name, birth_date, zodiac, fortune_type, result, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        
        conn.commit()
        conn.close()
    
    def get_fortune_history(self, limit=50):
        """获取运势历史记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT name, birth_date, zodiac, fortune_type, result, timestamp 
            FROM fortune_records 
            ORDER BY timestamp DESC 
            LIMIT ?
        ''', (limit,))
        
        records = cursor.fetchall()
        conn.close()
        return records


class TimeThread(QThread):
    """时间线程，用于更新昆仑镜的时间显示"""
    time_signal = pyqtSignal(str)
    hour_changed = pyqtSignal(int)  # 小时变化信号
    
    def run(self):
        last_hour = -1
        while True:
            current_time = datetime.now()
            current_hour = current_time.hour
            
            # 发射时间信号
            self.time_signal.emit(current_time.strftime("%Y-%m-%d %H:%M:%S"))
            
            # 如果小时变化，发射小时变化信号
            if current_hour != last_hour:
                self.hour_changed.emit(current_hour)
                last_hour = current_hour
            
            time.sleep(1)


class DivinationThread(QThread):
    """占卜线程，模拟复杂的占卜计算"""
    result_signal = pyqtSignal(str, str)  # 结果和类型
    progress_signal = pyqtSignal(int)
    
    def __init__(self, question, divination_type):
        super().__init__()
        self.question = question
        self.divination_type = divination_type
    
    def run(self):
        # 模拟复杂的占卜计算过程
        steps = 50 if self.divination_type == "简易占卜" else 100 if self.divination_type == "详细占卜" else 150
        
        for i in range(steps + 1):
            self.progress_signal.emit(int(i * 100 / steps))
            time.sleep(0.03)
        
        # 根据占卜类型生成不同详细程度的结果
        if self.divination_type == "简易占卜":
            result = self.generate_simple_result()
        elif self.divination_type == "详细占卜":
            result = self.generate_detailed_result()
        else:  # 深度洞察
            result = self.generate_deep_insight()
        
        self.result_signal.emit(result, self.divination_type)
    
    def generate_simple_result(self):
        """生成简易占卜结果"""
        results = [
            "大吉：所求之事将顺利达成",
            "中吉：事情会有良好发展",
            "小吉：需稍加努力方可成功",
            "平：保持现状，静观其变",
            "凶：需谨慎行事，避免损失",
            "大凶：暂时不宜行动，等待时机"
        ]
        
        result = random.choice(results)
        return f"问题：{self.question}\n\n占卜结果：{result}"
    
    def generate_detailed_result(self):
        """生成详细占卜结果"""
        # 更详细的结果分类
        aspects = ["事业", "爱情", "健康", "财运", "人际关系"]
        levels = ["极佳", "良好", "一般", "需要注意", "挑战"]
        
        result = f"问题：{self.question}\n\n"
        result += "详细占卜分析：\n\n"
        
        for aspect in aspects:
            level = random.choice(levels)
            description = self.get_aspect_description(aspect, level)
            result += f"• {aspect}：{level}\n"
            result += f"  {description}\n\n"
        
        # 添加建议
        advice = self.get_advice()
        result += f"综合建议：{advice}"
        
        return result
    
    def generate_deep_insight(self):
        """生成深度洞察结果"""
        # 更深入的分析
        elements = ["金", "木", "水", "火", "土"]
        directions = ["东", "南", "西", "北", "中"]
        seasons = ["春", "夏", "秋", "冬"]
        
        result = f"问题：{self.question}\n\n"
        result += "深度洞察分析：\n\n"
        
        # 五行分析
        dominant_element = random.choice(elements)
        result += f"主导元素：{dominant_element}\n"
        result += f"元素解读：{self.get_element_meaning(dominant_element)}\n\n"
        
        # 方位分析
        favorable_direction = random.choice(directions)
        result += f"有利方位：{favorable_direction}\n"
        result += f"方位解读：{self.get_direction_meaning(favorable_direction)}\n\n"
        
        # 季节分析
        favorable_season = random.choice(seasons)
        result += f"有利季节：{favorable_season}\n"
        result += f"季节解读：{self.get_season_meaning(favorable_season)}\n\n"
        
        # 详细建议
        detailed_advice = self.get_detailed_advice()
        result += f"深度建议：{detailed_advice}"
        
        return result
    
    def get_aspect_description(self, aspect, level):
        """获取方面描述"""
        descriptions = {
            "事业": {
                "极佳": "工作顺利，有机会获得重要项目或晋升。",
                "良好": "工作稳定，与同事合作愉快。",
                "一般": "工作中规中矩，需要更多努力。",
                "需要注意": "工作中可能遇到挑战，需要谨慎应对。",
                "挑战": "工作压力较大，需要调整心态和策略。"
            },
            "爱情": {
                "极佳": "感情甜蜜，关系稳定发展。",
                "良好": "感情融洽，小惊喜不断。",
                "一般": "感情平稳，需要更多沟通。",
                "需要注意": "感情中可能存在小摩擦。",
                "挑战": "感情面临考验，需要双方共同努力。"
            },
            "健康": {
                "极佳": "身体状况良好，精力充沛。",
                "良好": "健康状态稳定，注意保持。",
                "一般": "偶有小不适，注意休息。",
                "需要注意": "健康需关注，避免过度劳累。",
                "挑战": "健康方面需要特别留意。"
            },
            "财运": {
                "极佳": "财运亨通，有意外收入可能。",
                "良好": "财务状况稳定，有小额进账。",
                "一般": "收支平衡，需要合理规划。",
                "需要注意": "财务方面需谨慎，避免冲动消费。",
                "挑战": "财务压力较大，需要精打细算。"
            },
            "人际关系": {
                "极佳": "人缘极佳，社交活动丰富。",
                "良好": "人际关系和谐，得到他人帮助。",
                "一般": "社交平稳，需要主动维护关系。",
                "需要注意": "可能遇到人际摩擦，需耐心处理。",
                "挑战": "人际关系复杂，需要谨慎应对。"
            }
        }
        
        return descriptions[aspect][level]
    
    def get_advice(self):
        """获取建议"""
        advice_list = [
            "保持积极心态，机遇自然来。",
            "注意与人沟通，避免误解。",
            "健康是最大的财富，注意休息。",
            "理财需谨慎，避免冲动消费。",
            "学习新技能，提升自我价值。",
            "耐心等待，时机即将成熟。",
            "勇敢尝试新事物，会有意外收获。",
            "关注家庭关系，营造和谐氛围。"
        ]
        
        return random.choice(advice_list)
    
    def get_element_meaning(self, element):
        """获取元素含义"""
        meanings = {
            "金": "象征财富与决断，宜坚定目标，果断行动。",
            "木": "象征成长与发展，宜学习进取，拓展人脉。",
            "水": "象征智慧与流动，宜灵活变通，顺势而为。",
            "火": "象征激情与活力，宜积极主动，展现自我。",
            "土": "象征稳定与积累，宜脚踏实地，稳步前进。"
        }
        
        return meanings[element]
    
    def get_direction_meaning(self, direction):
        """获取方位含义"""
        meanings = {
            "东": "象征新生与希望，宜开始新计划。",
            "南": "象征热情与名誉，宜社交展示。",
            "西": "象征收获与思考，宜反思总结。",
            "北": "象征智慧与内省，宜学习规划。",
            "中": "象征平衡与稳定，宜巩固基础。"
        }
        
        return meanings[direction]
    
    def get_season_meaning(self, season):
        """获取季节含义"""
        meanings = {
            "春": "象征开始与成长，宜播种新计划。",
            "夏": "象征繁荣与热情，宜积极行动。",
            "秋": "象征收获与反思，宜总结经验。",
            "冬": "象征积蓄与等待，宜养精蓄锐。"
        }
        
        return meanings[season]
    
    def get_detailed_advice(self):
        """获取详细建议"""
        advice_list = [
            "顺应天时，把握地利，创造人和。内在修为与外在行动同样重要。",
            "观照内心，明辨是非。外在的成就源于内在的平和与智慧。",
            "阴阳调和，刚柔并济。在进取与守成之间找到平衡点。",
            "以静制动，以柔克刚。在复杂局势中保持清醒头脑。",
            "积小流成江海，积跬步至千里。持之以恒方能成就大业。"
        ]
        
        return random.choice(advice_list)


class CalendarDialog(QDialog):
    """日历选择对话框"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("选择日期")
        self.setModal(True)
        self.resize(400, 300)
        
        layout = QVBoxLayout(self)
        
        self.calendar = QCalendarWidget()
        self.calendar.setGridVisible(True)
        layout.addWidget(self.calendar)
        
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def get_selected_date(self):
        """获取选择的日期"""
        return self.calendar.selectedDate()


class KunlunMirrorToolbox(QMainWindow):
    def __init__(self):
        super().__init__()
        self.db_manager = DatabaseManager()
        self.init_ui()
        self.init_data()
        
    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("昆仑镜工具箱 - 上古神器再现")
        self.setGeometry(100, 100, 1200, 800)
        
        # 设置主题颜色
        self.set_dark_theme()
        
        # 创建中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QVBoxLayout(central_widget)
        
        # 标题栏
        title_layout = QHBoxLayout()
        title_label = QLabel("昆仑镜工具箱")
        title_label.setFont(QFont("楷体", 20, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #E6B325; padding: 10px;")
        title_layout.addWidget(title_label)
        
        # 时间显示
        self.time_label = QLabel()
        self.time_label.setFont(QFont("宋体", 12))
        self.time_label.setAlignment(Qt.AlignRight)
        self.time_label.setStyleSheet("color: #AAAAAA; padding: 5px;")
        title_layout.addWidget(self.time_label)
        
        main_layout.addLayout(title_layout)
        
        # 创建标签页
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #555; background-color: #333; }
            QTabBar::tab { background-color: #444; color: #EEE; padding: 8px 15px; }
            QTabBar::tab:selected { background-color: #555; border-bottom: 2px solid #E6B325; }
        """)
        
        # 添加各个功能标签页
        self.create_mirror_tab()
        self.create_divination_tab()
        self.create_history_tab()
        self.create_fortune_tab()
        self.create_tools_tab()
        self.create_records_tab()
        self.create_settings_tab()
        
        main_layout.addWidget(self.tab_widget)
        
        # 状态栏
        self.statusBar().showMessage("昆仑镜已就绪 - 洞察过去，预知未来")
        
        # 启动时间线程
        self.time_thread = TimeThread()
        self.time_thread.time_signal.connect(self.update_time)
        self.time_thread.hour_changed.connect(self.on_hour_changed)
        self.time_thread.start()
    
    def set_dark_theme(self):
        """设置暗色主题"""
        dark_palette = QPalette()
        dark_palette.setColor(QPalette.Window, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.WindowText, Qt.white)
        dark_palette.setColor(QPalette.Base, QColor(35, 35, 35))
        dark_palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ToolTipBase, QColor(25, 25, 25))
        dark_palette.setColor(QPalette.ToolTipText, Qt.white)
        dark_palette.setColor(QPalette.Text, Qt.white)
        dark_palette.setColor(QPalette.Button, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ButtonText, Qt.white)
        dark_palette.setColor(QPalette.BrightText, Qt.red)
        dark_palette.setColor(QPalette.Highlight, QColor(230, 179, 37))
        dark_palette.setColor(QPalette.HighlightedText, QColor(35, 35, 35))
        self.setPalette(dark_palette)
    
    def create_mirror_tab(self):
        """创建昆仑镜主界面标签页"""
        mirror_tab = QWidget()
        layout = QVBoxLayout(mirror_tab)
        
        # 昆仑镜图像区域
        mirror_frame = QFrame()
        mirror_frame.setFrameStyle(QFrame.Box)
        mirror_frame.setStyleSheet("background-color: #222; border: 2px solid #E6B325;")
        mirror_layout = QVBoxLayout(mirror_frame)
        
        mirror_label = QLabel("昆仑镜")
        mirror_label.setFont(QFont("楷体", 24, QFont.Bold))
        mirror_label.setAlignment(Qt.AlignCenter)
        mirror_label.setStyleSheet("color: #E6B325; padding: 20px;")
        mirror_layout.addWidget(mirror_label)
        
        # 模拟镜面显示
        self.mirror_display = QTextEdit()
        self.mirror_display.setReadOnly(True)
        self.mirror_display.setFont(QFont("宋体", 12))
        self.mirror_display.setStyleSheet("""
            QTextEdit { 
                background-color: #111; 
                color: #E6B325; 
                border: 1px solid #444; 
                padding: 10px;
            }
        """)
        mirror_layout.addWidget(self.mirror_display)
        
        layout.addWidget(mirror_frame)
        
        # 功能按钮
        button_layout = QHBoxLayout()
        
        reflect_btn = QPushButton("照映过去")
        reflect_btn.setFont(QFont("宋体", 12))
        reflect_btn.setStyleSheet("QPushButton { background-color: #444; color: white; padding: 8px; }")
        reflect_btn.clicked.connect(self.reflect_past)
        button_layout.addWidget(reflect_btn)
        
        predict_btn = QPushButton("预知未来")
        predict_btn.setFont(QFont("宋体", 12))
        predict_btn.setStyleSheet("QPushButton { background-color: #444; color: white; padding: 8px; }")
        predict_btn.clicked.connect(self.predict_future)
        button_layout.addWidget(predict_btn)
        
        analyze_btn = QPushButton("洞察现在")
        analyze_btn.setFont(QFont("宋体", 12))
        analyze_btn.setStyleSheet("QPushButton { background-color: #444; color: white; padding: 8px; }")
        analyze_btn.clicked.connect(self.analyze_present)
        button_layout.addWidget(analyze_btn)
        
        clear_btn = QPushButton("清空镜面")
        clear_btn.setFont(QFont("宋体", 12))
        clear_btn.setStyleSheet("QPushButton { background-color: #555; color: white; padding: 8px; }")
        clear_btn.clicked.connect(self.clear_mirror)
        button_layout.addWidget(clear_btn)
        
        layout.addLayout(button_layout)
        
        self.tab_widget.addTab(mirror_tab, "昆仑镜")
    
    def create_divination_tab(self):
        """创建占卜功能标签页"""
        divination_tab = QWidget()
        layout = QVBoxLayout(divination_tab)
        
        # 标题
        title_label = QLabel("昆仑镜占卜")
        title_label.setFont(QFont("楷体", 18, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #E6B325; padding: 10px;")
        layout.addWidget(title_label)
        
        # 问题输入
        question_layout = QHBoxLayout()
        question_label = QLabel("请输入您的问题：")
        question_label.setFont(QFont("宋体", 12))
        question_layout.addWidget(question_label)
        
        self.question_input = QLineEdit()
        self.question_input.setFont(QFont("宋体", 12))
        self.question_input.setPlaceholderText("例如：我近期的事业运势如何？")
        self.question_input.setStyleSheet("QLineEdit { padding: 8px; background-color: #444; color: white; }")
        question_layout.addWidget(self.question_input)
        
        layout.addLayout(question_layout)
        
        # 占卜类型选择
        type_layout = QHBoxLayout()
        type_label = QLabel("选择占卜方式：")
        type_label.setFont(QFont("宋体", 12))
        type_layout.addWidget(type_label)
        
        self.divination_type = QComboBox()
        self.divination_type.setFont(QFont("宋体", 12))
        self.divination_type.addItems(["简易占卜", "详细占卜", "深度洞察"])
        self.divination_type.setStyleSheet("QComboBox { padding: 8px; background-color: #444; color: white; }")
        type_layout.addWidget(self.divination_type)
        
        layout.addLayout(type_layout)
        
        # 占卜按钮
        divination_btn = QPushButton("开始占卜")
        divination_btn.setFont(QFont("宋体", 14, QFont.Bold))
        divination_btn.setStyleSheet("QPushButton { background-color: #E6B325; color: #333; padding: 10px; }")
        divination_btn.clicked.connect(self.start_divination)
        layout.addWidget(divination_btn)
        
        # 进度条
        self.divination_progress = QProgressBar()
        self.divination_progress.setVisible(False)
        layout.addWidget(self.divination_progress)
        
        # 结果显示
        self.divination_result = QTextEdit()
        self.divination_result.setReadOnly(True)
        self.divination_result.setFont(QFont("宋体", 12))
        self.divination_result.setStyleSheet("""
            QTextEdit { 
                background-color: #222; 
                color: #E6B325; 
                border: 1px solid #444; 
                padding: 15px;
            }
        """)
        layout.addWidget(self.divination_result)
        
        self.tab_widget.addTab(divination_tab, "镜中占卜")
    
    def create_history_tab(self):
        """创建历史回顾标签页"""
        history_tab = QWidget()
        layout = QVBoxLayout(history_tab)
        
        # 标题
        title_label = QLabel("历史回顾")
        title_label.setFont(QFont("楷体", 18, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #E6B325; padding: 10px;")
        layout.addWidget(title_label)
        
        # 日期选择
        date_layout = QHBoxLayout()
        date_label = QLabel("选择日期：")
        date_label.setFont(QFont("宋体", 12))
        date_layout.addWidget(date_label)
        
        self.year_spin = QSpinBox()
        self.year_spin.setRange(1900, 2100)
        self.year_spin.setValue(datetime.now().year)
        self.year_spin.setStyleSheet("QSpinBox { padding: 5px; background-color: #444; color: white; }")
        date_layout.addWidget(QLabel("年"))
        date_layout.addWidget(self.year_spin)
        
        self.month_spin = QSpinBox()
        self.month_spin.setRange(1, 12)
        self.month_spin.setValue(datetime.now().month)
        self.month_spin.setStyleSheet("QSpinBox { padding: 5px; background-color: #444; color: white; }")
        date_layout.addWidget(QLabel("月"))
        date_layout.addWidget(self.month_spin)
        
        self.day_spin = QSpinBox()
        self.day_spin.setRange(1, 31)
        self.day_spin.setValue(datetime.now().day)
        self.day_spin.setStyleSheet("QSpinBox { padding: 5px; background-color: #444; color: white; }")
        date_layout.addWidget(QLabel("日"))
        date_layout.addWidget(self.day_spin)
        
        # 添加日历选择按钮
        calendar_btn = QPushButton("日历选择")
        calendar_btn.setFont(QFont("宋体", 10))
        calendar_btn.setStyleSheet("QPushButton { background-color: #555; color: white; padding: 5px; }")
        calendar_btn.clicked.connect(self.open_calendar_dialog)
        date_layout.addWidget(calendar_btn)
        
        layout.addLayout(date_layout)
        
        # 查询按钮
        query_btn = QPushButton("查询历史")
        query_btn.setFont(QFont("宋体", 12))
        query_btn.setStyleSheet("QPushButton { background-color: #444; color: white; padding: 8px; }")
        query_btn.clicked.connect(self.query_history)
        layout.addWidget(query_btn)
        
        # 历史事件显示
        self.history_display = QTextEdit()
        self.history_display.setReadOnly(True)
        self.history_display.setFont(QFont("宋体", 12))
        self.history_display.setStyleSheet("""
            QTextEdit { 
                background-color: #222; 
                color: #DDD; 
                border: 1px solid #444; 
                padding: 15px;
            }
        """)
        layout.addWidget(self.history_display)
        
        self.tab_widget.addTab(history_tab, "历史回顾")
    
    def create_fortune_tab(self):
        """创建运势分析标签页"""
        fortune_tab = QWidget()
        layout = QVBoxLayout(fortune_tab)
        
        # 标题
        title_label = QLabel("运势分析")
        title_label.setFont(QFont("楷体", 18, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #E6B325; padding: 10px;")
        layout.addWidget(title_label)
        
        # 个人信息输入
        info_group = QGroupBox("个人信息")
        info_group.setStyleSheet("QGroupBox { color: #E6B325; font-weight: bold; }")
        info_layout = QVBoxLayout(info_group)
        
        # 姓名
        name_layout = QHBoxLayout()
        name_label = QLabel("姓名：")
        name_label.setFont(QFont("宋体", 12))
        name_layout.addWidget(name_label)
        
        self.name_input = QLineEdit()
        self.name_input.setFont(QFont("宋体", 12))
        self.name_input.setStyleSheet("QLineEdit { padding: 8px; background-color: #444; color: white; }")
        name_layout.addWidget(self.name_input)
        info_layout.addLayout(name_layout)
        
        # 出生日期
        birth_layout = QHBoxLayout()
        birth_label = QLabel("出生日期：")
        birth_label.setFont(QFont("宋体", 12))
        birth_layout.addWidget(birth_label)
        
        self.birth_year = QSpinBox()
        self.birth_year.setRange(1900, 2023)
        self.birth_year.setValue(1990)
        self.birth_year.setStyleSheet("QSpinBox { padding: 5px; background-color: #444; color: white; }")
        birth_layout.addWidget(QLabel("年"))
        birth_layout.addWidget(self.birth_year)
        
        self.birth_month = QSpinBox()
        self.birth_month.setRange(1, 12)
        self.birth_month.setValue(1)
        self.birth_month.setStyleSheet("QSpinBox { padding: 5px; background-color: #444; color: white; }")
        birth_layout.addWidget(QLabel("月"))
        birth_layout.addWidget(self.birth_month)
        
        self.birth_day = QSpinBox()
        self.birth_day.setRange(1, 31)
        self.birth_day.setValue(1)
        self.birth_day.setStyleSheet("QSpinBox { padding: 5px; background-color: #444; color: white; }")
        birth_layout.addWidget(QLabel("日"))
        birth_layout.addWidget(self.birth_day)
        
        info_layout.addLayout(birth_layout)
        
        # 星座
        zodiac_layout = QHBoxLayout()
        zodiac_label = QLabel("星座：")
        zodiac_label.setFont(QFont("宋体", 12))
        zodiac_layout.addWidget(zodiac_label)
        
        self.zodiac_combo = QComboBox()
        self.zodiac_combo.setFont(QFont("宋体", 12))
        self.zodiac_combo.addItems([
            "白羊座", "金牛座", "双子座", "巨蟹座", 
            "狮子座", "处女座", "天秤座", "天蝎座", 
            "射手座", "摩羯座", "水瓶座", "双鱼座"
        ])
        self.zodiac_combo.setStyleSheet("QComboBox { padding: 8px; background-color: #444; color: white; }")
        zodiac_layout.addWidget(self.zodiac_combo)
        
        info_layout.addLayout(zodiac_layout)
        layout.addWidget(info_group)
        
        # 运势类型选择
        fortune_type_layout = QHBoxLayout()
        fortune_type_label = QLabel("运势类型：")
        fortune_type_label.setFont(QFont("宋体", 12))
        fortune_type_layout.addWidget(fortune_type_label)
        
        self.fortune_type = QComboBox()
        self.fortune_type.setFont(QFont("宋体", 12))
        self.fortune_type.addItems(["今日运势", "本周运势", "本月运势", "年度运势"])
        self.fortune_type.setStyleSheet("QComboBox { padding: 8px; background-color: #444; color: white; }")
        fortune_type_layout.addWidget(self.fortune_type)
        
        layout.addLayout(fortune_type_layout)
        
        # 分析按钮
        analyze_btn = QPushButton("分析运势")
        analyze_btn.setFont(QFont("宋体", 14, QFont.Bold))
        analyze_btn.setStyleSheet("QPushButton { background-color: #E6B325; color: #333; padding: 10px; }")
        analyze_btn.clicked.connect(self.analyze_fortune)
        layout.addWidget(analyze_btn)
        
        # 运势结果显示
        self.fortune_result = QTextEdit()
        self.fortune_result.setReadOnly(True)
        self.fortune_result.setFont(QFont("宋体", 12))
        self.fortune_result.setStyleSheet("""
            QTextEdit { 
                background-color: #222; 
                color: #DDD; 
                border: 1px solid #444; 
                padding: 15px;
            }
        """)
        layout.addWidget(self.fortune_result)
        
        self.tab_widget.addTab(fortune_tab, "运势分析")
    
    def create_tools_tab(self):
        """创建实用工具标签页"""
        tools_tab = QWidget()
        layout = QVBoxLayout(tools_tab)
        
        # 标题
        title_label = QLabel("实用工具")
        title_label.setFont(QFont("楷体", 18, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #E6B325; padding: 10px;")
        layout.addWidget(title_label)
        
        # 工具按钮网格
        tools_grid = QHBoxLayout()
        
        # 左侧工具列
        left_tools = QVBoxLayout()
        
        # 随机数生成器
        random_btn = QPushButton("随机数生成")
        random_btn.setFont(QFont("宋体", 12))
        random_btn.setStyleSheet("QPushButton { background-color: #444; color: white; padding: 10px; }")
        random_btn.clicked.connect(self.generate_random)
        left_tools.addWidget(random_btn)
        
        # 密码生成器
        password_btn = QPushButton("密码生成")
        password_btn.setFont(QFont("宋体", 12))
        password_btn.setStyleSheet("QPushButton { background-color: #444; color: white; padding: 10px; }")
        password_btn.clicked.connect(self.generate_password)
        left_tools.addWidget(password_btn)
        
        # 进制转换
        base_convert_btn = QPushButton("进制转换")
        base_convert_btn.setFont(QFont("宋体", 12))
        base_convert_btn.setStyleSheet("QPushButton { background-color: #444; color: white; padding: 10px; }")
        base_convert_btn.clicked.connect(self.base_conversion)
        left_tools.addWidget(base_convert_btn)
        
        # 右侧工具列
        right_tools = QVBoxLayout()
        
        # 日期计算
        date_calc_btn = QPushButton("日期计算")
        date_calc_btn.setFont(QFont("宋体", 12))
        date_calc_btn.setStyleSheet("QPushButton { background-color: #444; color: white; padding: 10px; }")
        date_calc_btn.clicked.connect(self.date_calculation)
        right_tools.addWidget(date_calc_btn)
        
        # 单位转换
        unit_convert_btn = QPushButton("单位转换")
        unit_convert_btn.setFont(QFont("宋体", 12))
        unit_convert_btn.setStyleSheet("QPushButton { background-color: #444; color: white; padding: 10px; }")
        unit_convert_btn.clicked.connect(self.unit_conversion)
        right_tools.addWidget(unit_convert_btn)
        
        # 颜色代码生成
        color_code_btn = QPushButton("颜色代码生成")
        color_code_btn.setFont(QFont("宋体", 12))
        color_code_btn.setStyleSheet("QPushButton { background-color: #444; color: white; padding: 10px; }")
        color_code_btn.clicked.connect(self.color_code_generator)
        right_tools.addWidget(color_code_btn)
        
        tools_grid.addLayout(left_tools)
        tools_grid.addLayout(right_tools)
        layout.addLayout(tools_grid)
        
        # 工具结果显示
        self.tools_result = QTextEdit()
        self.tools_result.setReadOnly(True)
        self.tools_result.setFont(QFont("宋体", 12))
        self.tools_result.setStyleSheet("""
            QTextEdit { 
                background-color: #222; 
                color: #DDD; 
                border: 1px solid #444; 
                padding: 15px;
            }
        """)
        layout.addWidget(self.tools_result)
        
        self.tab_widget.addTab(tools_tab, "实用工具")
    
    def create_records_tab(self):
        """创建记录查看标签页"""
        records_tab = QWidget()
        layout = QVBoxLayout(records_tab)
        
        # 标题
        title_label = QLabel("历史记录")
        title_label.setFont(QFont("楷体", 18, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #E6B325; padding: 10px;")
        layout.addWidget(title_label)
        
        # 记录类型选择
        type_layout = QHBoxLayout()
        type_label = QLabel("记录类型：")
        type_label.setFont(QFont("宋体", 12))
        type_layout.addWidget(type_label)
        
        self.record_type = QComboBox()
        self.record_type.setFont(QFont("宋体", 12))
        self.record_type.addItems(["占卜记录", "运势记录"])
        self.record_type.setStyleSheet("QComboBox { padding: 8px; background-color: #444; color: white; }")
        self.record_type.currentTextChanged.connect(self.load_records)
        type_layout.addWidget(self.record_type)
        
        # 刷新按钮
        refresh_btn = QPushButton("刷新记录")
        refresh_btn.setFont(QFont("宋体", 12))
        refresh_btn.setStyleSheet("QPushButton { background-color: #555; color: white; padding: 8px; }")
        refresh_btn.clicked.connect(self.load_records)
        type_layout.addWidget(refresh_btn)
        
        # 清空记录按钮
        clear_btn = QPushButton("清空记录")
        clear_btn.setFont(QFont("宋体", 12))
        clear_btn.setStyleSheet("QPushButton { background-color: #800000; color: white; padding: 8px; }")
        clear_btn.clicked.connect(self.clear_records)
        type_layout.addWidget(clear_btn)
        
        layout.addLayout(type_layout)
        
        # 记录表格
        self.records_table = QTableWidget()
        self.records_table.setStyleSheet("""
            QTableWidget { 
                background-color: #222; 
                color: #DDD; 
                border: 1px solid #444;
                gridline-color: #444;
            }
            QHeaderView::section {
                background-color: #444;
                color: #EEE;
                padding: 5px;
                border: 1px solid #555;
            }
        """)
        layout.addWidget(self.records_table)
        
        self.tab_widget.addTab(records_tab, "历史记录")
    
    def create_settings_tab(self):
        """创建设置标签页"""
        settings_tab = QWidget()
        layout = QVBoxLayout(settings_tab)
        
        # 标题
        title_label = QLabel("系统设置")
        title_label.setFont(QFont("楷体", 18, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #E6B325; padding: 10px;")
        layout.addWidget(title_label)
        
        # 主题设置
        theme_group = QGroupBox("主题设置")
        theme_group.setStyleSheet("QGroupBox { color: #E6B325; font-weight: bold; }")
        theme_layout = QVBoxLayout(theme_group)
        
        theme_selector_layout = QHBoxLayout()
        theme_label = QLabel("选择主题：")
        theme_label.setFont(QFont("宋体", 12))
        theme_selector_layout.addWidget(theme_label)
        
        self.theme_combo = QComboBox()
        self.theme_combo.setFont(QFont("宋体", 12))
        self.theme_combo.addItems(["暗色主题", "深蓝主题", "古典主题"])
        self.theme_combo.setStyleSheet("QComboBox { padding: 8px; background-color: #444; color: white; }")
        theme_selector_layout.addWidget(self.theme_combo)
        
        apply_theme_btn = QPushButton("应用主题")
        apply_theme_btn.setFont(QFont("宋体", 12))
        apply_theme_btn.setStyleSheet("QPushButton { background-color: #444; color: white; padding: 8px; }")
        apply_theme_btn.clicked.connect(self.apply_theme)
        theme_selector_layout.addWidget(apply_theme_btn)
        
        theme_layout.addLayout(theme_selector_layout)
        layout.addWidget(theme_group)
        
        # 数据管理
        data_group = QGroupBox("数据管理")
        data_group.setStyleSheet("QGroupBox { color: #E6B325; font-weight: bold; }")
        data_layout = QVBoxLayout(data_group)
        
        # 导出数据按钮
        export_btn = QPushButton("导出数据")
        export_btn.setFont(QFont("宋体", 12))
        export_btn.setStyleSheet("QPushButton { background-color: #444; color: white; padding: 8px; }")
        export_btn.clicked.connect(self.export_data)
        data_layout.addWidget(export_btn)
        
        # 导入数据按钮
        import_btn = QPushButton("导入数据")
        import_btn.setFont(QFont("宋体", 12))
        import_btn.setStyleSheet("QPushButton { background-color: #444; color: white; padding: 8px; }")
        import_btn.clicked.connect(self.import_data)
        data_layout.addWidget(import_btn)
        
        layout.addWidget(data_group)
        
        # 关于信息
        about_group = QGroupBox("关于昆仑镜")
        about_group.setStyleSheet("QGroupBox { color: #E6B325; font-weight: bold; }")
        about_layout = QVBoxLayout(about_group)
        
        about_text = QTextEdit()
        about_text.setReadOnly(True)
        about_text.setFont(QFont("宋体", 11))
        about_text.setHtml("""
            <h3>昆仑镜工具箱</h3>
            <p>版本: 2.0 完整增强版</p>
            <p>昆仑镜，上古十大神器之一，拥有洞察过去、预知未来的神奇力量。</p>
            <p>本工具箱集成了占卜、运势分析、历史回顾等多种功能，</p>
            <p>旨在为用户提供全方位的决策支持和生活指导。</p>
            <br>
            <p>开发理念：融合传统文化与现代技术，创造实用工具。</p>
            <p>© 2023 昆仑镜开发团队 保留所有权利</p>
        """)
        about_text.setStyleSheet("QTextEdit { background-color: #222; color: #DDD; border: none; }")
        about_layout.addWidget(about_text)
        
        layout.addWidget(about_group)
        
        self.tab_widget.addTab(settings_tab, "系统设置")
    
    def init_data(self):
        """初始化数据"""
        self.history_data = {
            "1-1": "元旦 - 新年的开始，万象更新",
            "2-14": "情人节 - 表达爱意的日子",
            "3-8": "国际妇女节 - 庆祝女性成就",
            "4-1": "愚人节 - 玩笑与欢乐的日子",
            "5-1": "劳动节 - 向劳动者致敬",
            "6-1": "儿童节 - 关爱儿童成长",
            "7-1": "建党节 - 纪念党的诞生",
            "8-1": "建军节 - 向军人致敬",
            "9-10": "教师节 - 感恩教师奉献",
            "10-1": "国庆节 - 庆祝国家成立",
            "12-25": "圣诞节 - 西方传统节日"
        }
        
        # 添加更多历史事件
        for month in range(1, 13):
            for day in range(1, 29):
                key = f"{month}-{day}"
                if key not in self.history_data:
                    events = [
                        f"{month}月{day}日 - 平凡而美好的一天",
                        f"{month}月{day}日 - 历史上的今天发生了许多小事",
                        f"{month}月{day}日 - 时光流逝，岁月如梭",
                        f"{month}月{day}日 - 每个平凡日子都值得珍惜"
                    ]
                    self.history_data[key] = random.choice(events)
    
    def update_time(self, current_time):
        """更新时间显示"""
        self.time_label.setText(f"当前时间: {current_time}")
    
    def on_hour_changed(self, hour):
        """小时变化时的处理"""
        # 根据小时更新状态栏提示
        if 5 <= hour < 10:
            self.statusBar().showMessage("清晨时光，昆仑镜能量充沛")
        elif 10 <= hour < 14:
            self.statusBar().showMessage("正午时分，昆仑镜洞察力最强")
        elif 14 <= hour < 18:
            self.statusBar().showMessage("下午时光，适合进行深度分析")
        elif 18 <= hour < 22:
            self.statusBar().showMessage("夜晚降临，昆仑镜映照星空")
        else:
            self.statusBar().showMessage("深夜时分，昆仑镜与宇宙共鸣")
    
    def reflect_past(self):
        """照映过去功能"""
        past_events = [
            "昆仑镜中显现：昨日种种，皆成今我。过去的经历塑造了现在的你。",
            "镜中回响：回顾过去，汲取经验与智慧。每个选择都有其意义。",
            "镜光闪烁：过去的成功与失败都是宝贵财富，值得珍视。",
            "镜面涟漪：时光如流水，过去已逝，但教训永存。",
            "镜中幻影：铭记过去，但不要被其束缚。前路漫漫，未来可期。",
            "镜影斑驳：过去的日子如同镜中花，虽已逝去，却留下芬芳。",
            "镜光回溯：每一个昨天的选择，都铸就了今天的你。"
        ]
        
        result = random.choice(past_events)
        self.mirror_display.setText(result)
        self.statusBar().showMessage("昆仑镜正在照映过去...")
    
    def predict_future(self):
        """预知未来功能"""
        future_predictions = [
            "镜中预言：明日将有新的机遇等待着你，请做好准备。",
            "镜光闪耀：未来充满无限可能，保持积极心态，勇往直前。",
            "镜面波动：近期需注意人际关系的变化，以柔克刚为上策。",
            "镜中启示：坚持目标，未来将不负所望。耐心是成功的关键。",
            "镜影朦胧：未来难以完全预测，但努力终有回报。相信自己。",
            "镜光流转：未来的道路上会有挑战，但也有惊喜等待发现。",
            "镜影交错：命运之轮正在转动，把握时机，创造属于自己的未来。"
        ]
        
        result = random.choice(future_predictions)
        self.mirror_display.setText(result)
        self.statusBar().showMessage("昆仑镜正在预知未来...")
    
    def analyze_present(self):
        """洞察现在功能"""
        present_insights = [
            "镜中显现：当下是最真实的时刻，珍惜此刻，活在当下。",
            "镜光聚焦：现在的选择将决定未来的方向，请慎重考虑。",
            "镜面清明：此刻的心境影响对事物的看法，保持平和心态。",
            "镜影如实：现状是过去的结果，也是未来的起点。",
            "镜光透彻：当下的困难是成长的阶梯，勇敢面对挑战。",
            "镜影真实：现在的你拥有改变一切的力量，善用此刻。",
            "镜面映照：此时此刻，你是完整的，无需外求。"
        ]
        
        result = random.choice(present_insights)
        self.mirror_display.setText(result)
        self.statusBar().showMessage("昆仑镜正在洞察现在...")
    
    def clear_mirror(self):
        """清空镜面"""
        self.mirror_display.clear()
        self.statusBar().showMessage("镜面已清空")
    
    def start_divination(self):
        """开始占卜"""
        question = self.question_input.text().strip()
        if not question:
            QMessageBox.warning(self, "警告", "请输入您的问题")
            return
        
        self.divination_progress.setVisible(True)
        self.divination_progress.setValue(0)
        self.divination_result.clear()
        
        divination_type = self.divination_type.currentText()
        self.divination_thread = DivinationThread(question, divination_type)
        self.divination_thread.progress_signal.connect(self.update_divination_progress)
        self.divination_thread.result_signal.connect(self.show_divination_result)
        self.divination_thread.start()
        
        self.statusBar().showMessage(f"昆仑镜正在进行{divination_type}...")
    
    def update_divination_progress(self, value):
        """更新占卜进度"""
        self.divination_progress.setValue(value)
    
    def show_divination_result(self, result, divination_type):
        """显示占卜结果"""
        self.divination_result.setText(result)
        self.divination_progress.setVisible(False)
        
        # 保存占卜记录
        question = self.question_input.text().strip()
        self.db_manager.save_divination_record(question, result, divination_type)
        
        self.statusBar().showMessage("占卜完成")
    
    def open_calendar_dialog(self):
        """打开日历选择对话框"""
        dialog = CalendarDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            selected_date = dialog.get_selected_date()
            self.year_spin.setValue(selected_date.year())
            self.month_spin.setValue(selected_date.month())
            self.day_spin.setValue(selected_date.day())
    
    def query_history(self):
        """查询历史"""
        year = self.year_spin.value()
        month = self.month_spin.value()
        day = self.day_spin.value()
        
        key = f"{month}-{day}"
        event = self.history_data.get(key, "未找到该日期的历史事件")
        
        # 添加随机历史细节
        details = [
            "这一天，风调雨顺，国泰民安。百姓安居乐业，社会和谐稳定。",
            "历史上，许多重要人物在这一天诞生或离世，留下了不朽的传奇。",
            "这一天发生了改变历史进程的重大事件，影响深远。",
            "文化上，这一天有着特殊的象征意义，传承着古老的智慧。",
            "许多传统习俗与这一天密切相关，体现了文化的多样性。",
            "这一天见证了人类文明的进步，是历史长河中的重要节点。",
            "无论是平凡还是非凡，这一天都是时间长河中不可或缺的一页。"
        ]
        
        # 添加星象信息
        constellations = ["白羊座", "金牛座", "双子座", "巨蟹座", "狮子座", "处女座", 
                         "天秤座", "天蝎座", "射手座", "摩羯座", "水瓶座", "双鱼座"]
        lucky_constellation = random.choice(constellations)
        
        full_event = f"{year}年{month}月{day}日\n{event}\n\n"
        full_event += f"历史细节：{random.choice(details)}\n\n"
        full_event += f"星象提示：今日{lucky_constellation}运势较佳，宜把握机会。"
        
        self.history_display.setText(full_event)
        self.statusBar().showMessage("历史查询完成")
    
    def analyze_fortune(self):
        """分析运势"""
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "警告", "请输入姓名")
            return
        
        birth_year = self.birth_year.value()
        birth_month = self.birth_month.value()
        birth_day = self.birth_day.value()
        zodiac = self.zodiac_combo.currentText()
        fortune_type = self.fortune_type.currentText()
        
        # 生成运势分析
        fortune_levels = ["极佳", "良好", "一般", "需要注意", "挑战"]
        aspects = ["事业", "爱情", "健康", "财运", "人际关系"]
        
        result = f"姓名: {name}\n"
        result += f"出生日期: {birth_year}年{birth_month}月{birth_day}日\n"
        result += f"星座: {zodiac}\n"
        result += f"运势类型: {fortune_type}\n\n"
        result += f"{fortune_type}运势分析:\n\n"
        
        overall_level = random.choice(fortune_levels)
        result += f"综合运势: {overall_level}\n"
        result += f"整体解读: {self.get_overall_fortune_description(overall_level)}\n\n"
        
        for aspect in aspects:
            level = random.choice(fortune_levels)
            description = self.generate_fortune_description(aspect, level)
            result += f"• {aspect}: {level}\n"
            result += f"  {description}\n\n"
        
        # 添加幸运数字和颜色
        lucky_number = random.randint(1, 9)
        lucky_colors = ["红色", "金色", "蓝色", "绿色", "紫色", "白色"]
        lucky_color = random.choice(lucky_colors)
        
        result += f"幸运数字: {lucky_number}\n"
        result += f"幸运颜色: {lucky_color}\n\n"
        
        # 添加建议
        advice = self.get_fortune_advice()
        result += f"运势建议: {advice}"
        
        self.fortune_result.setText(result)
        
        # 保存运势记录
        birth_date = f"{birth_year}-{birth_month}-{birth_day}"
        self.db_manager.save_fortune_record(name, birth_date, zodiac, fortune_type, result)
        
        self.statusBar().showMessage("运势分析完成")
    
    def get_overall_fortune_description(self, level):
        """获取整体运势描述"""
        descriptions = {
            "极佳": "天时地利人和，各方面运势都非常理想，是行动的好时机。",
            "良好": "运势平稳向上，有机会获得不错的进展，宜积极进取。",
            "一般": "运势平平，需要更多努力才能获得理想结果，保持耐心。",
            "需要注意": "运势有些波动，需谨慎行事，避免冲动决策。",
            "挑战": "面临较多挑战，需要调整心态和策略，以应对困难。"
        }
        
        return descriptions[level]
    
    def generate_fortune_description(self, aspect, level):
        """生成运势描述"""
        descriptions = {
            "事业": {
                "极佳": "工作顺利，有机会获得重要项目或晋升，职场人际关系和谐。",
                "良好": "工作稳定，与同事合作愉快，能够按时完成任务。",
                "一般": "工作中规中矩，需要更多努力才能获得认可，保持耐心。",
                "需要注意": "工作中可能遇到挑战，需要谨慎应对，避免冲突。",
                "挑战": "工作压力较大，需要调整心态和策略，寻求支持。"
            },
            "爱情": {
                "极佳": "感情甜蜜，关系稳定发展，有机会更进一步。",
                "良好": "感情融洽，小惊喜不断，彼此理解加深。",
                "一般": "感情平稳，需要更多沟通和关注，避免冷淡。",
                "需要注意": "感情中可能存在小摩擦，需要耐心沟通解决。",
                "挑战": "感情面临考验，需要双方共同努力，加强信任。"
            },
            "健康": {
                "极佳": "身体状况良好，精力充沛，适合进行体育锻炼。",
                "良好": "健康状态稳定，注意保持良好作息和饮食习惯。",
                "一般": "偶有小不适，注意休息，避免过度劳累。",
                "需要注意": "健康需关注，避免过度劳累，及时就医。",
                "挑战": "健康方面需要特别留意，可能有慢性问题需管理。"
            },
            "财运": {
                "极佳": "财运亨通，有意外收入可能，投资理财收益可观。",
                "良好": "财务状况稳定，有小额进账，收支平衡。",
                "一般": "收支平衡，需要合理规划，避免不必要的开支。",
                "需要注意": "财务方面需谨慎，避免冲动消费，注意储蓄。",
                "挑战": "财务压力较大，需要精打细算，寻找额外收入。"
            },
            "人际关系": {
                "极佳": "人缘极佳，社交活动丰富，能够得到他人帮助。",
                "良好": "人际关系和谐，得到他人帮助，社交圈扩展。",
                "一般": "社交平稳，需要主动维护关系，避免孤立。",
                "需要注意": "可能遇到人际摩擦，需耐心处理，避免冲突。",
                "挑战": "人际关系复杂，需要谨慎应对，保持距离。"
            }
        }
        
        return descriptions[aspect][level]
    
    def get_fortune_advice(self):
        """获取运势建议"""
        advice_list = [
            "保持积极心态，机遇自然来。相信自己，勇往直前。",
            "注意与人沟通，避免误解。倾听他人，表达清晰。",
            "健康是最大的财富，注意休息。适度运动，均衡饮食。",
            "理财需谨慎，避免冲动消费。规划预算，理性投资。",
            "学习新技能，提升自我价值。持续进步，不断成长。",
            "耐心等待，时机即将成熟。做好准备，把握机会。",
            "勇敢尝试新事物，会有意外收获。开拓视野，丰富体验。",
            "关注家庭关系，营造和谐氛围。珍惜亲情，维系感情。"
        ]
        
        return random.choice(advice_list)
    
    def generate_random(self):
        """生成随机数"""
        number = random.randint(1, 100)
        self.tools_result.setText(f"生成的随机数: {number}")
        self.statusBar().showMessage("随机数生成完成")
    
    def generate_password(self):
        """生成密码"""
        chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*"
        length = random.randint(12, 16)
        password = "".join(random.choice(chars) for _ in range(length))
        self.tools_result.setText(f"生成的密码: {password}\n密码长度: {length}")
        self.statusBar().showMessage("密码生成完成")
    
    def base_conversion(self):
        """进制转换"""
        number = random.randint(1, 255)
        binary = bin(number)[2:]
        octal = oct(number)[2:]
        hexadecimal = hex(number)[2:].upper()
        
        result = f"十进制: {number}\n"
        result += f"二进制: {binary}\n"
        result += f"八进制: {octal}\n"
        result += f"十六进制: {hexadecimal}"
        
        self.tools_result.setText(result)
        self.statusBar().showMessage("进制转换完成")
    
    def date_calculation(self):
        """日期计算"""
        today = datetime.now()
        future_date_30 = today + timedelta(days=30)
        future_date_90 = today + timedelta(days=90)
        past_date_30 = today - timedelta(days=30)
        
        result = f"今天: {today.strftime('%Y-%m-%d')}\n"
        result += f"30天后: {future_date_30.strftime('%Y-%m-%d')}\n"
        result += f"90天后: {future_date_90.strftime('%Y-%m-%d')}\n"
        result += f"30天前: {past_date_30.strftime('%Y-%m-%d')}"
        
        self.tools_result.setText(result)
        self.statusBar().showMessage("日期计算完成")
    
    def unit_conversion(self):
        """单位转换"""
        conversions = [
            "1公里 = 0.6214英里",
            "1千克 = 2.2046磅",
            "1升 = 0.2642加仑",
            "1米 = 3.2808英尺",
            "1摄氏度 = 33.8华氏度",
            "1公顷 = 2.4711英亩",
            "1千瓦时 = 3.6兆焦耳"
        ]
        result = "常用单位转换:\n\n" + "\n".join(conversions)
        self.tools_result.setText(result)
        self.statusBar().showMessage("单位转换完成")
    
    def color_code_generator(self):
        """颜色代码生成"""
        colors = [
            ("红色", "#FF0000", "RGB(255, 0, 0)"),
            ("绿色", "#00FF00", "RGB(0, 255, 0)"),
            ("蓝色", "#0000FF", "RGB(0, 0, 255)"),
            ("黄色", "#FFFF00", "RGB(255, 255, 0)"),
            ("紫色", "#800080", "RGB(128, 0, 128)"),
            ("橙色", "#FFA500", "RGB(255, 165, 0)"),
            ("金色", "#FFD700", "RGB(255, 215, 0)")
        ]
        
        result = "常用颜色代码:\n\n"
        for name, hex_code, rgb in colors:
            result += f"{name}: {hex_code}, {rgb}\n"
        
        self.tools_result.setText(result)
        self.statusBar().showMessage("颜色代码生成完成")
    
    def load_records(self):
        """加载记录"""
        record_type = self.record_type.currentText()
        
        if record_type == "占卜记录":
            records = self.db_manager.get_divination_history()
            self.records_table.setColumnCount(4)
            self.records_table.setHorizontalHeaderLabels(["问题", "结果", "时间", "占卜类型"])
            
            self.records_table.setRowCount(len(records))
            for row, record in enumerate(records):
                for col, value in enumerate(record):
                    item = QTableWidgetItem(str(value))
                    self.records_table.setItem(row, col, item)
        
        elif record_type == "运势记录":
            records = self.db_manager.get_fortune_history()
            self.records_table.setColumnCount(6)
            self.records_table.setHorizontalHeaderLabels(["姓名", "出生日期", "星座", "运势类型", "结果", "时间"])
            
            self.records_table.setRowCount(len(records))
            for row, record in enumerate(records):
                for col, value in enumerate(record):
                    item = QTableWidgetItem(str(value))
                    self.records_table.setItem(row, col, item)
        
        # 调整列宽
        self.records_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.statusBar().showMessage(f"已加载{len(records)}条{record_type}")
    
    def clear_records(self):
        """清空记录"""
        reply = QMessageBox.question(self, "确认清空", 
                                    "确定要清空所有记录吗？此操作不可撤销！",
                                    QMessageBox.Yes | QMessageBox.No,
                                    QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            # 这里应该实现清空数据库的逻辑
            QMessageBox.information(self, "提示", "清空记录功能正在开发中")
    
    def apply_theme(self):
        """应用主题"""
        theme = self.theme_combo.currentText()
        if theme == "暗色主题":
            self.set_dark_theme()
        elif theme == "深蓝主题":
            self.set_blue_theme()
        elif theme == "古典主题":
            self.set_classic_theme()
        
        self.statusBar().showMessage(f"已应用{theme}")
    
    def set_blue_theme(self):
        """设置深蓝主题"""
        blue_palette = QPalette()
        blue_palette.setColor(QPalette.Window, QColor(30, 30, 60))
        blue_palette.setColor(QPalette.WindowText, Qt.white)
        blue_palette.setColor(QPalette.Base, QColor(20, 20, 40))
        blue_palette.setColor(QPalette.AlternateBase, QColor(30, 30, 60))
        blue_palette.setColor(QPalette.ToolTipBase, QColor(10, 10, 30))
        blue_palette.setColor(QPalette.ToolTipText, Qt.white)
        blue_palette.setColor(QPalette.Text, Qt.white)
        blue_palette.setColor(QPalette.Button, QColor(40, 40, 80))
        blue_palette.setColor(QPalette.ButtonText, Qt.white)
        blue_palette.setColor(QPalette.BrightText, Qt.red)
        blue_palette.setColor(QPalette.Highlight, QColor(100, 149, 237))
        blue_palette.setColor(QPalette.HighlightedText, QColor(20, 20, 40))
        self.setPalette(blue_palette)
    
    def set_classic_theme(self):
        """设置古典主题"""
        classic_palette = QPalette()
        classic_palette.setColor(QPalette.Window, QColor(60, 40, 20))
        classic_palette.setColor(QPalette.WindowText, QColor(240, 220, 130))
        classic_palette.setColor(QPalette.Base, QColor(40, 25, 10))
        classic_palette.setColor(QPalette.AlternateBase, QColor(60, 40, 20))
        classic_palette.setColor(QPalette.ToolTipBase, QColor(30, 20, 5))
        classic_palette.setColor(QPalette.ToolTipText, QColor(240, 220, 130))
        classic_palette.setColor(QPalette.Text, QColor(240, 220, 130))
        classic_palette.setColor(QPalette.Button, QColor(80, 60, 30))
        classic_palette.setColor(QPalette.ButtonText, QColor(240, 220, 130))
        classic_palette.setColor(QPalette.BrightText, Qt.red)
        classic_palette.setColor(QPalette.Highlight, QColor(180, 160, 50))
        classic_palette.setColor(QPalette.HighlightedText, QColor(40, 25, 10))
        self.setPalette(classic_palette)
    
    def export_data(self):
        """导出数据"""
        file_path, _ = QFileDialog.getSaveFileName(self, "导出数据", "昆仑镜数据备份.json", "JSON文件 (*.json)")
        if file_path:
            # 这里应该实现导出数据的逻辑
            QMessageBox.information(self, "提示", "数据导出功能正在开发中")
    
    def import_data(self):
        """导入数据"""
        file_path, _ = QFileDialog.getOpenFileName(self, "导入数据", "", "JSON文件 (*.json)")
        if file_path:
            # 这里应该实现导入数据的逻辑
            QMessageBox.information(self, "提示", "数据导入功能正在开发中")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 设置应用程序字体
    font = QFont("微软雅黑", 10)
    app.setFont(font)
    
    window = KunlunMirrorToolbox()
    window.show()
    
    sys.exit(app.exec_())