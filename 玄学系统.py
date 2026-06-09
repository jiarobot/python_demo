import sys
import random
import math
import sqlite3
import json
import requests
from datetime import datetime, timedelta
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, 
                            QHBoxLayout, QLabel, QPushButton, QTextEdit, QComboBox, 
                            QSpinBox, QDoubleSpinBox, QCalendarWidget, QGroupBox,
                            QLineEdit, QProgressBar, QMessageBox, QSplitter, QFrame,
                            QTableWidget, QTableWidgetItem, QHeaderView, QListWidget,
                            QListWidgetItem, QCheckBox, QRadioButton, QButtonGroup,
                            QSlider, QDial, QProgressBar, QToolBar, QAction, QStatusBar,
                            QMenu, QMenuBar, QFileDialog, QInputDialog, QTreeWidget,
                            QTreeWidgetItem, QDockWidget, QFormLayout, QGridLayout)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QDate, QTime, QDateTime, QSize
from PyQt5.QtGui import (QFont, QPixmap, QPainter, QColor, QPen, QBrush, QIcon, 
                        QPalette, QLinearGradient, QRadialGradient, QConicalGradient)
from PyQt5.QtChart import QChart, QChartView, QPieSeries, QBarSeries, QBarSet, QLineSeries, QValueAxis
import numpy as np
from scipy import stats
import matplotlib
matplotlib.rc("font", family='Microsoft YaHei')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


class DatabaseManager:
    """数据库管理类，用于保存玄学记录和配置"""
    
    def __init__(self, db_path="mystic_system.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """初始化数据库表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建塔罗牌记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tarot_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                spread_type TEXT NOT NULL,
                cards TEXT NOT NULL,
                interpretation TEXT,
                notes TEXT
            )
        ''')
        
        # 创建八字记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bazi_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                year INTEGER,
                month INTEGER,
                day INTEGER,
                hour INTEGER,
                bazi_result TEXT,
                analysis TEXT,
                notes TEXT
            )
        ''')
        
        # 创建占星记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS astrology_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                birth_date TEXT,
                birth_time TEXT,
                birth_place TEXT,
                chart_data TEXT,
                forecast TEXT,
                notes TEXT
            )
        ''')
        
        # 创建易经记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS iching_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                hexagram TEXT,
                changing_lines TEXT,
                interpretation TEXT,
                question TEXT,
                notes TEXT
            )
        ''')
        
        # 创建用户设置表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE NOT NULL,
                value TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def save_tarot_record(self, spread_type, cards, interpretation, notes=""):
        """保存塔罗牌记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cards_json = json.dumps(cards)
        
        cursor.execute('''
            INSERT INTO tarot_records (date, spread_type, cards, interpretation, notes)
            VALUES (?, ?, ?, ?, ?)
        ''', (date, spread_type, cards_json, interpretation, notes))
        
        conn.commit()
        conn.close()
        return cursor.lastrowid
    
    def get_tarot_records(self, limit=50):
        """获取塔罗牌记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM tarot_records ORDER BY date DESC LIMIT ?
        ''', (limit,))
        
        records = cursor.fetchall()
        conn.close()
        return records
    
    def save_bazi_record(self, year, month, day, hour, bazi_result, analysis, notes=""):
        """保存八字记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        cursor.execute('''
            INSERT INTO bazi_records (date, year, month, day, hour, bazi_result, analysis, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (date, year, month, day, hour, bazi_result, analysis, notes))
        
        conn.commit()
        conn.close()
        return cursor.lastrowid
    
    def save_setting(self, key, value):
        """保存用户设置"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO user_settings (key, value)
            VALUES (?, ?)
        ''', (key, value))
        
        conn.commit()
        conn.close()
    
    def get_setting(self, key, default=None):
        """获取用户设置"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT value FROM user_settings WHERE key = ?
        ''', (key,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return result[0]
        return default


class AdvancedMysticUtils:
    """高级玄学工具类，提供更多玄学计算方法"""
    
    @staticmethod
    def calculate_bazi_detailed(year, month, day, hour):
        """详细的八字计算"""
        # 天干地支
        heavenly_stems = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
        earthly_branches = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
        
        # 年柱
        year_stem = heavenly_stems[(year - 4) % 10]
        year_branch = earthly_branches[(year - 4) % 12]
        
        # 月柱 (简化计算，实际需考虑节气)
        month_stem = heavenly_stems[((year % 10) * 2 + month) % 10]
        month_branch = earthly_branches[(month + 1) % 12]
        
        # 日柱 (简化计算，实际需复杂公式)
        base_date = datetime(1900, 1, 1)
        target_date = datetime(year, month, day)
        days_diff = (target_date - base_date).days
        day_stem_index = (days_diff + 9) % 10
        day_branch_index = (days_diff + 1) % 12
        
        day_stem = heavenly_stems[day_stem_index]
        day_branch = earthly_branches[day_branch_index]
        
        # 时柱
        hour_branch_index = (hour + 1) // 2 % 12
        hour_branch = earthly_branches[hour_branch_index]
        
        # 日干起时干
        day_stem_index = heavenly_stems.index(day_stem)
        hour_stem_index = (day_stem_index * 2 + hour_branch_index) % 10
        hour_stem = heavenly_stems[hour_stem_index]
        
        return {
            "year": f"{year_stem}{year_branch}",
            "month": f"{month_stem}{month_branch}",
            "day": f"{day_stem}{day_branch}",
            "hour": f"{hour_stem}{hour_branch}",
            "full_bazi": f"{year_stem}{year_branch} {month_stem}{month_branch} {day_stem}{day_branch} {hour_stem}{hour_branch}"
        }
    
    @staticmethod
    def calculate_wuxing(bazi):
        """计算五行强度"""
        wuxing_map = {
            "甲": "木", "乙": "木", "寅": "木", "卯": "木",
            "丙": "火", "丁": "火", "巳": "火", "午": "火",
            "戊": "土", "己": "土", "辰": "土", "戌": "土", "丑": "土", "未": "土",
            "庚": "金", "辛": "金", "申": "金", "酉": "金",
            "壬": "水", "癸": "水", "亥": "水", "子": "水"
        }
        
        wuxing_count = {"木": 0, "火": 0, "土": 0, "金": 0, "水": 0}
        
        for char in bazi:
            if char in wuxing_map:
                element = wuxing_map[char]
                wuxing_count[element] += 1
        
        return wuxing_count
    
    @staticmethod
    def calculate_palm_lines():
        """模拟掌纹分析"""
        lines = ["生命线", "智慧线", "感情线", "命运线", "太阳线"]
        characteristics = ["长而清晰", "短而浅", "有分叉", "有岛纹", "有链状", "有十字纹", "有星纹"]
        
        result = {}
        for line in lines:
            result[line] = {
                "length": random.choice(["很长", "较长", "中等", "较短", "很短"]),
                "depth": random.choice(["很深", "较深", "中等", "较浅", "很浅"]),
                "characteristic": random.sample(characteristics, random.randint(1, 3))
            }
        
        return result
    
    @staticmethod
    def calculate_fengshui(birth_year, direction):
        """风水计算"""
        # 八宅风水简化的命卦计算
        male_life_gua = {
            1: "坎", 2: "坤", 3: "震", 4: "巽", 5: "坤", 6: "乾", 7: "兑", 8: "艮", 9: "离", 0: "离"
        }
        
        female_life_gua = {
            1: "离", 2: "艮", 3: "兑", 4: "乾", 5: "艮", 6: "巽", 7: "震", 8: "坤", 9: "坎", 0: "坎"
        }
        
        last_digit = birth_year % 10
        life_gua = male_life_gua[last_digit]  # 假设为男性
        
        # 东四宅和西四宅
        east_gua = ["坎", "震", "巽", "离"]
        west_gua = ["乾", "坤", "艮", "兑"]
        
        direction_luck = "吉" if (life_gua in east_gua and direction in ["东", "东南", "南", "北"]) or \
                                (life_gua in west_gua and direction in ["西", "西南", "西北", "东北"]) else "凶"
        
        return {
            "命卦": life_gua,
            "方向": direction,
            "吉凶": direction_luck,
            "建议": "适合布置" if direction_luck == "吉" else "不宜布置"
        }


class MysticChartWidget(QWidget):
    """玄学图表显示组件"""
    
    def __init__(self):
        super().__init__()
        self.initUI()
    
    def initUI(self):
        layout = QVBoxLayout()
        
        # 标题
        title = QLabel("玄学数据分析图表")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # 图表类型选择
        chart_layout = QHBoxLayout()
        chart_layout.addWidget(QLabel("图表类型:"))
        
        self.chart_type = QComboBox()
        self.chart_type.addItems(["五行分布", "星座统计", "生命灵数分布", "塔罗牌频率"])
        self.chart_type.currentTextChanged.connect(self.update_chart)
        chart_layout.addWidget(self.chart_type)
        
        layout.addLayout(chart_layout)
        
        # 图表显示区域
        self.figure = Figure(figsize=(10, 6))
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)
        
        self.setLayout(layout)
        self.update_chart()
    
    def update_chart(self):
        """更新图表"""
        chart_type = self.chart_type.currentText()
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        
        if chart_type == "五行分布":
            # 模拟五行数据
            elements = ['木', '火', '土', '金', '水']
            values = [random.randint(10, 30) for _ in range(5)]
            
            ax.bar(elements, values, color=['green', 'red', 'brown', 'gold', 'blue'])
            ax.set_title('五行分布图')
            ax.set_ylabel('强度')
        
        elif chart_type == "星座统计":
            # 模拟星座数据
            signs = ['白羊', '金牛', '双子', '巨蟹', '狮子', '处女', 
                    '天秤', '天蝎', '射手', '摩羯', '水瓶', '双鱼']
            counts = [random.randint(5, 20) for _ in range(12)]
            
            ax.pie(counts, labels=signs, autopct='%1.1f%%')
            ax.set_title('星座分布统计')
        
        elif chart_type == "生命灵数分布":
            # 模拟生命灵数数据
            numbers = list(range(1, 10))
            numbers.extend([11, 22, 33])
            frequencies = [random.randint(5, 25) for _ in numbers]
            
            ax.plot(numbers, frequencies, marker='o')
            ax.set_title('生命灵数分布')
            ax.set_xlabel('生命灵数')
            ax.set_ylabel('出现频率')
            ax.grid(True)
        
        elif chart_type == "塔罗牌频率":
            # 模拟塔罗牌数据
            tarot_cards = ['愚者', '魔术师', '女祭司', '皇后', '皇帝', '教皇', 
                          '恋人', '战车', '力量', '隐士', '命运之轮']
            frequencies = [random.randint(1, 15) for _ in tarot_cards]
            
            ax.barh(tarot_cards, frequencies, color='purple')
            ax.set_title('塔罗牌出现频率')
            ax.set_xlabel('出现次数')
        
        self.canvas.draw()


class AdvancedTarotWidget(QWidget):
    """高级塔罗牌占卜组件"""
    
    cardDrawn = pyqtSignal(str, bool)  # 卡牌名称，是否逆位
    
    def __init__(self, db_manager):
        super().__init__()
        self.db_manager = db_manager
        self.initUI()
        self.cards = self.load_tarot_cards()
        self.current_spread = []
        
    def load_tarot_cards(self):
        """加载塔罗牌数据"""
        # 完整的78张塔罗牌
        major_arcana = [
            "0.愚者", "1.魔术师", "2.女祭司", "3.皇后", "4.皇帝", "5.教皇", 
            "6.恋人", "7.战车", "8.力量", "9.隐士", "10.命运之轮", 
            "11.正义", "12.倒吊人", "13.死神", "14.节制", "15.恶魔", 
            "16.高塔", "17.星星", "18.月亮", "19.太阳", "20.审判", "21.世界"
        ]
        
        # 小阿卡那牌
        suits = ["权杖", "圣杯", "宝剑", "星币"]
        ranks = ["王牌", "二", "三", "四", "五", "六", "七", "八", "九", "十", 
                "侍从", "骑士", "皇后", "国王"]
        
        minor_arcana = []
        for suit in suits:
            for rank in ranks:
                minor_arcana.append(f"{suit}{rank}")
        
        return major_arcana + minor_arcana
    
    def initUI(self):
        layout = QVBoxLayout()
        
        # 标题
        title = QLabel("高级塔罗牌占卜")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # 占卜类型选择
        spread_layout = QHBoxLayout()
        spread_layout.addWidget(QLabel("占卜类型:"))
        
        self.spread_type = QComboBox()
        self.spread_type.addItems(["单张牌", "三张牌(过去-现在-未来)", "凯尔特十字", "关系牌阵", "四季牌阵"])
        spread_layout.addWidget(self.spread_type)
        
        self.question_input = QLineEdit()
        self.question_input.setPlaceholderText("输入你的问题...")
        spread_layout.addWidget(self.question_input)
        
        layout.addLayout(spread_layout)
        
        # 卡片显示区域
        self.cards_layout = QHBoxLayout()
        self.update_cards_display()
        layout.addLayout(self.cards_layout)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        
        self.draw_button = QPushButton("开始占卜")
        self.draw_button.clicked.connect(self.perform_reading)
        button_layout.addWidget(self.draw_button)
        
        self.save_button = QPushButton("保存记录")
        self.save_button.clicked.connect(self.save_reading)
        button_layout.addWidget(self.save_button)
        
        self.history_button = QPushButton("查看历史")
        self.history_button.clicked.connect(self.show_history)
        button_layout.addWidget(self.history_button)
        
        layout.addLayout(button_layout)
        
        # 解释区域
        self.interpretation_text = QTextEdit()
        self.interpretation_text.setReadOnly(True)
        layout.addWidget(QLabel("占卜结果:"))
        layout.addWidget(self.interpretation_text)
        
        self.setLayout(layout)
    
    def update_cards_display(self):
        """更新卡片显示区域"""
        # 清空现有卡片
        for i in reversed(range(self.cards_layout.count())): 
            self.cards_layout.itemAt(i).widget().setParent(None)
        
        # 根据牌阵类型添加卡片占位符
        spread_type = self.spread_type.currentText()
        num_cards = 1
        
        if spread_type == "三张牌(过去-现在-未来)":
            num_cards = 3
        elif spread_type == "凯尔特十字":
            num_cards = 10
        elif spread_type == "关系牌阵":
            num_cards = 2
        elif spread_type == "四季牌阵":
            num_cards = 5
        
        for i in range(num_cards):
            card_frame = QFrame()
            card_frame.setFrameStyle(QFrame.Box)
            card_frame.setFixedSize(120, 180)
            card_frame.setStyleSheet("background-color: #f5f5f5; border: 2px dashed #ccc;")
            
            card_label = QLabel("?")
            card_label.setAlignment(Qt.AlignCenter)
            card_label.setFont(QFont("Arial", 10))
            
            card_layout = QVBoxLayout()
            card_layout.addWidget(card_label)
            card_frame.setLayout(card_layout)
            
            self.cards_layout.addWidget(card_frame)
    
    def perform_reading(self):
        """执行占卜"""
        spread_type = self.spread_type.currentText()
        self.current_spread = []
        
        # 根据牌阵类型抽取牌
        if spread_type == "单张牌":
            num_cards = 1
        elif spread_type == "三张牌(过去-现在-未来)":
            num_cards = 3
        elif spread_type == "凯尔特十字":
            num_cards = 10
        elif spread_type == "关系牌阵":
            num_cards = 2
        elif spread_type == "四季牌阵":
            num_cards = 5
        else:
            num_cards = 1
        
        # 抽取牌
        for i in range(num_cards):
            card = random.choice(self.cards)
            is_reversed = random.choice([True, False])
            self.current_spread.append({
                "card": card,
                "reversed": is_reversed,
                "position": self.get_position_name(spread_type, i)
            })
        
        # 更新显示
        self.update_reading_display()
        
        # 生成解释
        interpretation = self.generate_interpretation(spread_type)
        self.interpretation_text.setText(interpretation)
    
    def get_position_name(self, spread_type, index):
        """获取牌位置名称"""
        if spread_type == "三张牌(过去-现在-未来)":
            positions = ["过去", "现在", "未来"]
            return positions[index] if index < len(positions) else f"位置{index+1}"
        
        elif spread_type == "凯尔特十字":
            positions = [
                "当前状况", "挑战", "基础", "过去", "目标",
                "未来", "自我", "环境", "希望与恐惧", "结果"
            ]
            return positions[index] if index < len(positions) else f"位置{index+1}"
        
        elif spread_type == "关系牌阵":
            positions = ["自己", "对方"]
            return positions[index] if index < len(positions) else f"位置{index+1}"
        
        elif spread_type == "四季牌阵":
            positions = ["大阿卡那-整体", "权杖-行动", "圣杯-情感", "宝剑-思想", "星币-物质"]
            return positions[index] if index < len(positions) else f"位置{index+1}"
        
        else:
            return "整体"
    
    def update_reading_display(self):
        """更新占卜显示"""
        for i in range(len(self.current_spread)):
            if i < self.cards_layout.count():
                card_frame = self.cards_layout.itemAt(i).widget()
                card_label = card_frame.layout().itemAt(0).widget()
                
                card_data = self.current_spread[i]
                display_text = f"{card_data['card']}\n"
                display_text += f"({card_data['position']})\n"
                display_text += "逆位" if card_data['reversed'] else "正位"
                
                card_label.setText(display_text)
                
                # 设置卡片颜色
                if card_data['reversed']:
                    card_frame.setStyleSheet("background-color: #f5f5f5; border: 2px solid #ff6b6b;")
                else:
                    card_frame.setStyleSheet("background-color: #f5f5f5; border: 2px solid #4ecdc4;")
    
    def generate_interpretation(self, spread_type):
        """生成占卜解释"""
        interpretation = f"占卜类型: {spread_type}\n"
        
        if self.question_input.text():
            interpretation += f"问题: {self.question_input.text()}\n"
        
        interpretation += "\n各牌解释:\n\n"
        
        for i, card_data in enumerate(self.current_spread):
            interpretation += f"{card_data['position']}: {card_data['card']} ({'逆位' if card_data['reversed'] else '正位'})\n"
            
            # 简化的牌义解释
            meaning = self.get_card_meaning(card_data['card'], card_data['reversed'])
            interpretation += f"含义: {meaning}\n\n"
        
        # 添加整体解读
        interpretation += "整体解读:\n"
        interpretation += self.get_overall_interpretation(spread_type)
        
        return interpretation
    
    def get_card_meaning(self, card_name, is_reversed):
        """获取单张牌的含义"""
        # 简化的牌义字典
        meanings = {
            "0.愚者": {"正位": "新的开始,冒险,自由", "逆位": "鲁莽,风险,不成熟"},
            "1.魔术师": {"正位": "创造力,技能,自信", "逆位": "欺骗,未利用的才能"},
            "2.女祭司": {"正位": "直觉,神秘,潜意识", "逆位": "隐藏的感情,冷漠"},
            # 可以继续添加更多牌义
        }
        
        # 简化的通用牌义
        if card_name in meanings:
            position = "逆位" if is_reversed else "正位"
            return meanings[card_name][position]
        
        # 根据牌名猜测含义
        if "权杖" in card_name:
            return "行动,能量,创造力" if not is_reversed else "拖延,冲突,精力分散"
        elif "圣杯" in card_name:
            return "情感,直觉,关系" if not is_reversed else "情感不稳定,失望"
        elif "宝剑" in card_name:
            return "思想,真理,决策" if not is_reversed else "混乱,冲突,焦虑"
        elif "星币" in card_name:
            return "物质,安全,实际" if not is_reversed else "财务问题,物质主义"
        
        return "这张牌提醒你关注当前情况"
    
    def get_overall_interpretation(self, spread_type):
        """获取整体解读"""
        # 基于牌阵类型的整体解读
        interpretations = {
            "单张牌": "这张牌是你当前状况的核心象征，反映了问题的本质。",
            "三张牌(过去-现在-未来)": "这个牌阵展示了事情的发展轨迹，帮助你理解过去如何影响现在，以及现在如何导向未来。",
            "凯尔特十字": "这是一个全面的牌阵，揭示了问题的多个层面，包括内在和外在因素。",
            "关系牌阵": "这个牌阵帮助你理解关系的动态，双方的需求和挑战。",
            "四季牌阵": "这个牌阵针对季节变化提供指导，帮助你在不同生活领域找到平衡。"
        }
        
        return interpretations.get(spread_type, "这个牌阵提供了对你问题的深入洞察。")
    
    def save_reading(self):
        """保存占卜记录"""
        if not self.current_spread:
            QMessageBox.warning(self, "警告", "请先进行占卜")
            return
        
        spread_type = self.spread_type.currentText()
        interpretation = self.interpretation_text.toPlainText()
        
        # 保存到数据库
        record_id = self.db_manager.save_tarot_record(
            spread_type, 
            self.current_spread, 
            interpretation,
            self.question_input.text()
        )
        
        QMessageBox.information(self, "成功", f"占卜记录已保存 (ID: {record_id})")
    
    def show_history(self):
        """显示历史记录"""
        records = self.db_manager.get_tarot_records(10)
        
        history_text = "最近10条塔罗牌记录:\n\n"
        for record in records:
            history_text += f"日期: {record[1]}\n"
            history_text += f"牌阵: {record[2]}\n"
            history_text += f"记录ID: {record[0]}\n"
            history_text += "---\n"
        
        QMessageBox.information(self, "历史记录", history_text)


class AdvancedBaziWidget(QWidget):
    """高级八字计算组件"""
    
    def __init__(self, db_manager):
        super().__init__()
        self.db_manager = db_manager
        self.initUI()
    
    def initUI(self):
        layout = QVBoxLayout()
        
        # 标题
        title = QLabel("高级八字排盘")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # 输入区域
        input_group = QGroupBox("出生信息")
        input_layout = QFormLayout()
        
        self.year_spin = QSpinBox()
        self.year_spin.setRange(1900, 2100)
        self.year_spin.setValue(1990)
        input_layout.addRow("年:", self.year_spin)
        
        self.month_spin = QSpinBox()
        self.month_spin.setRange(1, 12)
        self.month_spin.setValue(1)
        input_layout.addRow("月:", self.month_spin)
        
        self.day_spin = QSpinBox()
        self.day_spin.setRange(1, 31)
        self.day_spin.setValue(1)
        input_layout.addRow("日:", self.day_spin)
        
        self.hour_spin = QSpinBox()
        self.hour_spin.setRange(0, 23)
        self.hour_spin.setValue(12)
        input_layout.addRow("时:", self.hour_spin)
        
        self.gender_combo = QComboBox()
        self.gender_combo.addItems(["男", "女"])
        input_layout.addRow("性别:", self.gender_combo)
        
        input_group.setLayout(input_layout)
        layout.addWidget(input_group)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        
        self.calculate_button = QPushButton("排盘")
        self.calculate_button.clicked.connect(self.calculate_bazi)
        button_layout.addWidget(self.calculate_button)
        
        self.save_button = QPushButton("保存记录")
        self.save_button.clicked.connect(self.save_bazi)
        button_layout.addWidget(self.save_button)
        
        self.analysis_button = QPushButton("详细分析")
        self.analysis_button.clicked.connect(self.analyze_bazi)
        button_layout.addWidget(self.analysis_button)
        
        layout.addLayout(button_layout)
        
        # 结果显示区域
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        layout.addWidget(self.result_text)
        
        self.setLayout(layout)
    
    def calculate_bazi(self):
        """计算八字"""
        year = self.year_spin.value()
        month = self.month_spin.value()
        day = self.day_spin.value()
        hour = self.hour_spin.value()
        gender = self.gender_combo.currentText()
        
        # 使用高级工具类计算八字
        bazi_result = AdvancedMysticUtils.calculate_bazi_detailed(year, month, day, hour)
        
        # 计算五行
        wuxing = AdvancedMysticUtils.calculate_wuxing(bazi_result["full_bazi"])
        
        # 显示结果
        result = f"出生时间: {year}年{month}月{day}日{hour}时 ({gender})\n\n"
        result += "八字排盘:\n"
        result += f"年柱: {bazi_result['year']}\n"
        result += f"月柱: {bazi_result['month']}\n"
        result += f"日柱: {bazi_result['day']}\n"
        result += f"时柱: {bazi_result['hour']}\n\n"
        
        result += "五行分布:\n"
        for element, count in wuxing.items():
            result += f"{element}: {count}\n"
        
        result += f"\n完整八字: {bazi_result['full_bazi']}\n\n"
        
        # 简化的八字分析
        result += self.simple_bazi_analysis(bazi_result, wuxing, gender)
        
        self.result_text.setText(result)
        self.current_bazi = bazi_result
        self.current_wuxing = wuxing
    
    def simple_bazi_analysis(self, bazi, wuxing, gender):
        """简化的八字分析"""
        analysis = "八字简析:\n"
        
        # 日主分析 (简化)
        day_pillar = bazi["day"]
        day_stem = day_pillar[0]
        
        analysis += f"日主: {day_stem}\n"
        
        # 五行平衡分析
        max_element = max(wuxing, key=wuxing.get)
        min_element = min(wuxing, key=wuxing.get)
        
        analysis += f"五行最强: {max_element}\n"
        analysis += f"五行最弱: {min_element}\n"
        
        # 简化的用神建议
        if wuxing["木"] > 3:
            analysis += "木气过旺，宜用金克制或火泄秀\n"
        elif wuxing["火"] > 3:
            analysis += "火气过旺，宜用水克制或土泄秀\n"
        elif wuxing["土"] > 3:
            analysis += "土气过旺，宜用木克制或金泄秀\n"
        elif wuxing["金"] > 3:
            analysis += "金气过旺，宜用火克制或水泄秀\n"
        elif wuxing["水"] > 3:
            analysis += "水气过旺，宜用土克制或木泄秀\n"
        else:
            analysis += "五行相对平衡，运势较为平稳\n"
        
        return analysis
    
    def save_bazi(self):
        """保存八字记录"""
        if not hasattr(self, 'current_bazi'):
            QMessageBox.warning(self, "警告", "请先进行八字排盘")
            return
        
        year = self.year_spin.value()
        month = self.month_spin.value()
        day = self.day_spin.value()
        hour = self.hour_spin.value()
        
        analysis = self.result_text.toPlainText()
        
        # 保存到数据库
        record_id = self.db_manager.save_bazi_record(
            year, month, day, hour,
            self.current_bazi["full_bazi"],
            analysis
        )
        
        QMessageBox.information(self, "成功", f"八字记录已保存 (ID: {record_id})")
    
    def analyze_bazi(self):
        """详细八字分析"""
        if not hasattr(self, 'current_bazi'):
            QMessageBox.warning(self, "警告", "请先进行八字排盘")
            return
        
        # 更详细的八字分析
        analysis = "详细八字分析:\n\n"
        
        # 十神分析 (简化)
        analysis += "十神分析:\n"
        ten_gods = ["比肩", "劫财", "食神", "伤官", "偏财", 
                   "正财", "七杀", "正官", "偏印", "正印"]
        
        for god in random.sample(ten_gods, 3):
            analysis += f"{god}: {random.choice(['强', '中', '弱'])}\n"
        
        analysis += "\n大运分析:\n"
        
        # 简化的起运计算
        birth_datetime = datetime(
            self.year_spin.value(),
            self.month_spin.value(),
            self.day_spin.value(),
            self.hour_spin.value()
        )
        
        # 计算年龄
        now = datetime.now()
        age = now.year - birth_datetime.year
        
        analysis += f"当前年龄: {age}岁\n"
        
        # 简化的运势阶段
        if age < 20:
            analysis += "当前处于青少年运，主学业和成长\n"
        elif age < 40:
            analysis += "当前处于壮年运，主事业和家庭\n"
        elif age < 60:
            analysis += "当前处于中年运，主稳定和发展\n"
        else:
            analysis += "当前处于晚年运，主健康和总结\n"
        
        # 添加到结果显示
        current_text = self.result_text.toPlainText()
        self.result_text.setText(current_text + "\n\n" + analysis)


class FengShuiWidget(QWidget):
    """风水分析组件"""
    
    def __init__(self):
        super().__init__()
        self.initUI()
    
    def initUI(self):
        layout = QVBoxLayout()
        
        # 标题
        title = QLabel("风水分析工具")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # 输入区域
        input_group = QGroupBox("风水分析参数")
        input_layout = QFormLayout()
        
        self.birth_year = QSpinBox()
        self.birth_year.setRange(1900, 2100)
        self.birth_year.setValue(1990)
        input_layout.addRow("出生年份:", self.birth_year)
        
        self.house_direction = QComboBox()
        self.house_direction.addItems(["东", "南", "西", "北", "东南", "西南", "东北", "西北"])
        input_layout.addRow("房屋朝向:", self.house_direction)
        
        self.room_type = QComboBox()
        self.room_type.addItems(["客厅", "卧室", "厨房", "书房", "办公室", "商店"])
        input_layout.addRow("房间类型:", self.room_type)
        
        input_group.setLayout(input_layout)
        layout.addWidget(input_group)
        
        # 分析按钮
        self.analyze_button = QPushButton("风水分析")
        self.analyze_button.clicked.connect(self.analyze_fengshui)
        layout.addWidget(self.analyze_button)
        
        # 结果显示区域
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        layout.addWidget(self.result_text)
        
        self.setLayout(layout)
    
    def analyze_fengshui(self):
        """分析风水"""
        birth_year = self.birth_year.value()
        direction = self.house_direction.currentText()
        room_type = self.room_type.currentText()
        
        # 使用风水工具类计算
        fengshui_result = AdvancedMysticUtils.calculate_fengshui(birth_year, direction)
        
        # 生成风水建议
        result = f"风水分析结果:\n\n"
        result += f"房间类型: {room_type}\n"
        result += f"房屋朝向: {direction}\n"
        result += f"命卦: {fengshui_result['命卦']}\n"
        result += f"吉凶: {fengshui_result['吉凶']}\n"
        result += f"建议: {fengshui_result['建议']}\n\n"
        
        # 添加具体建议
        result += self.get_fengshui_suggestions(room_type, direction, fengshui_result['吉凶'])
        
        self.result_text.setText(result)
    
    def get_fengshui_suggestions(self, room_type, direction, luck):
        """获取具体风水建议"""
        suggestions = {
            "客厅": {
                "吉": "客厅宜明亮宽敞，可放置绿色植物增加生气。沙发应靠墙放置，形成有靠山的格局。",
                "凶": "客厅不宜有横梁压顶，可安装天花板化解。避免镜子直接对着大门。"
            },
            "卧室": {
                "吉": "床头宜靠墙，床不宜正对门或镜子。卧室颜色宜柔和，促进睡眠。",
                "凶": "卧室不宜有尖角对着床，可用屏风或植物化解。避免床下有杂物堆积。"
            },
            "厨房": {
                "吉": "厨房宜保持清洁，炉灶不宜正对水池。可放置一些食物象征丰足。",
                "凶": "厨房不宜与卫生间相邻，炉灶不宜在横梁下。保持通风良好。"
            },
            "书房": {
                "吉": "书房宜安静，书桌宜靠墙。可放置文昌塔或文竹增强学业运。",
                "凶": "书房不宜过于拥挤，避免书桌正对门。保持光线充足但不宜刺眼。"
            },
            "办公室": {
                "吉": "办公桌宜靠墙或后有屏风，形成有靠山格局。可放置水晶增强事业运。",
                "凶": "办公桌不宜正对门或卫生间，避免坐在横梁下。保持桌面整洁。"
            },
            "商店": {
                "吉": "商店门口宜开阔，收银台宜放在财位。可放置招财猫或金蟾招财。",
                "凶": "商店不宜有直路冲门，可用屏风或植物化解。避免门口有下水道。"
            }
        }
        
        room_suggestions = suggestions.get(room_type, {"吉": "保持整洁，通风良好", "凶": "注意化解煞气"})
        return room_suggestions.get(luck, "根据具体情况调整布局")


class PalmReadingWidget(QWidget):
    """掌纹分析组件"""
    
    def __init__(self):
        super().__init__()
        self.initUI()
    
    def initUI(self):
        layout = QVBoxLayout()
        
        # 标题
        title = QLabel("掌纹分析")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # 手掌选择
        hand_layout = QHBoxLayout()
        hand_layout.addWidget(QLabel("选择手掌:"))
        
        self.hand_group = QButtonGroup()
        self.left_hand = QRadioButton("左手")
        self.right_hand = QRadioButton("右手")
        self.left_hand.setChecked(True)
        
        self.hand_group.addButton(self.left_hand)
        self.hand_group.addButton(self.right_hand)
        
        hand_layout.addWidget(self.left_hand)
        hand_layout.addWidget(self.right_hand)
        hand_layout.addStretch()
        
        layout.addLayout(hand_layout)
        
        # 分析按钮
        self.analyze_button = QPushButton("分析掌纹")
        self.analyze_button.clicked.connect(self.analyze_palm)
        layout.addWidget(self.analyze_button)
        
        # 结果显示区域
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        layout.addWidget(self.result_text)
        
        self.setLayout(layout)
    
    def analyze_palm(self):
        """分析掌纹"""
        hand = "左手" if self.left_hand.isChecked() else "右手"
        
        # 使用工具类分析掌纹
        palm_lines = AdvancedMysticUtils.calculate_palm_lines()
        
        # 生成分析结果
        result = f"{hand}掌纹分析:\n\n"
        
        for line, characteristics in palm_lines.items():
            result += f"{line}:\n"
            result += f"  长度: {characteristics['length']}\n"
            result += f"  深度: {characteristics['depth']}\n"
            result += f"  特征: {', '.join(characteristics['characteristic'])}\n\n"
        
        # 添加整体解读
        result += "整体解读:\n"
        result += self.get_palm_interpretation(palm_lines, hand)
        
        self.result_text.setText(result)
    
    def get_palm_interpretation(self, palm_lines, hand):
        """获取掌纹整体解读"""
        interpretation = ""
        
        # 生命线分析
        life_line = palm_lines["生命线"]
        if life_line["length"] == "很长":
            interpretation += "生命线长而清晰，预示长寿和活力充沛。"
        elif life_line["length"] == "很短":
            interpretation += "生命线较短，需要注意健康和生活方式。"
        
        # 智慧线分析
        wisdom_line = palm_lines["智慧线"]
        if "有分叉" in wisdom_line["characteristic"]:
            interpretation += "智慧线有分叉，表示思维灵活，多才多艺。"
        
        # 感情线分析
        love_line = palm_lines["感情线"]
        if love_line["depth"] == "很深":
            interpretation += "感情线深刻，情感丰富且执着。"
        
        # 命运线分析
        fate_line = palm_lines["命运线"]
        if fate_line["length"] == "很长":
            interpretation += "命运线明显，事业发展较为顺利。"
        
        if not interpretation:
            interpretation = "掌纹整体平衡，生活各方面较为和谐。"
        
        return interpretation


class AdvancedMysticSystem(QMainWindow):
    """高级玄学系统主窗口"""
    
    def __init__(self):
        super().__init__()
        self.db_manager = DatabaseManager()
        self.initUI()
        
    def initUI(self):
        self.setWindowTitle('高级玄学系统工具库')
        self.setGeometry(100, 50, 1200, 800)
        
        # 设置应用图标和样式
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f0f0f0;
            }
            QTabWidget::pane {
                border: 1px solid #C2C7CB;
                background-color: white;
            }
            QTabBar::tab {
                background-color: #E1E1E1;
                border: 1px solid #C4C4C3;
                padding: 8px 20px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: #FFFFFF;
                border-bottom-color: #FFFFFF;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid gray;
                border-radius: 5px;
                margin-top: 1ex;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        
        # 创建菜单栏
        self.createMenuBar()
        
        # 创建工具栏
        self.createToolBar()
        
        # 创建状态栏
        self.statusBar().showMessage('高级玄学系统已就绪')
        
        # 创建中心部件 - 标签页
        self.tabs = QTabWidget()
        
        # 添加各个工具组件
        self.tarot_tab = AdvancedTarotWidget(self.db_manager)
        self.tabs.addTab(self.tarot_tab, "高级塔罗牌")
        
        self.bazi_tab = AdvancedBaziWidget(self.db_manager)
        self.tabs.addTab(self.bazi_tab, "八字排盘")
        
        self.fengshui_tab = FengShuiWidget()
        self.tabs.addTab(self.fengshui_tab, "风水分析")
        
        self.palm_tab = PalmReadingWidget()
        self.tabs.addTab(self.palm_tab, "掌纹分析")
        
        self.chart_tab = MysticChartWidget()
        self.tabs.addTab(self.chart_tab, "数据分析")
        
        # 添加每日运势标签页
        self.daily_tab = self.createDailyTab()
        self.tabs.addTab(self.daily_tab, "每日运势")
        
        self.setCentralWidget(self.tabs)
        
        # 创建停靠窗口
        self.createDockWidget()
        
        # 连接信号
        self.tarot_tab.cardDrawn.connect(self.on_card_drawn)
        
    def createMenuBar(self):
        """创建菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu('文件')
        
        export_action = QAction('导出数据', self)
        export_action.setShortcut('Ctrl+E')
        export_action.triggered.connect(self.exportData)
        file_menu.addAction(export_action)
        
        settings_action = QAction('设置', self)
        settings_action.setShortcut('Ctrl+,')
        settings_action.triggered.connect(self.showSettings)
        file_menu.addAction(settings_action)
        
        exit_action = QAction('退出', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 工具菜单
        tools_menu = menubar.addMenu('工具')
        
        numerology_action = QAction('数字命理计算器', self)
        numerology_action.triggered.connect(self.showNumerologyCalculator)
        tools_menu.addAction(numerology_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu('帮助')
        
        about_action = QAction('关于', self)
        about_action.triggered.connect(self.showAbout)
        help_menu.addAction(about_action)
    
    def createToolBar(self):
        """创建工具栏"""
        toolbar = QToolBar("主工具栏")
        toolbar.setIconSize(QSize(16, 16))
        self.addToolBar(toolbar)
        
        # 添加工具栏动作
        daily_action = QAction("今日运势", self)
        daily_action.triggered.connect(self.showDailyForecast)
        toolbar.addAction(daily_action)
        
        toolbar.addSeparator()
        
        save_action = QAction("保存记录", self)
        save_action.triggered.connect(self.saveCurrentRecord)
        toolbar.addAction(save_action)
    
    def createDockWidget(self):
        """创建停靠窗口"""
        # 快速工具停靠窗口
        quick_tools_dock = QDockWidget("快速工具", self)
        quick_tools_widget = QWidget()
        quick_layout = QVBoxLayout()
        
        # 添加快速工具按钮
        quick_tarot = QPushButton("快速抽牌")
        quick_tarot.clicked.connect(self.quickTarot)
        quick_layout.addWidget(quick_tarot)
        
        quick_bazi = QPushButton("快速八字")
        quick_bazi.clicked.connect(self.quickBazi)
        quick_layout.addWidget(quick_bazi)
        
        quick_forecast = QPushButton("今日运势")
        quick_forecast.clicked.connect(self.quickForecast)
        quick_layout.addWidget(quick_forecast)
        
        quick_tools_widget.setLayout(quick_layout)
        quick_tools_dock.setWidget(quick_tools_widget)
        self.addDockWidget(Qt.LeftDockWidgetArea, quick_tools_dock)
        
        # 信息面板停靠窗口
        info_dock = QDockWidget("系统信息", self)
        info_widget = QWidget()
        info_layout = QVBoxLayout()
        
        # 系统信息
        info_label = QLabel("玄学系统 v2.0\n\n功能模块:\n- 高级塔罗牌\n- 八字排盘\n- 风水分析\n- 掌纹分析\n- 数据分析")
        info_label.setWordWrap(True)
        info_layout.addWidget(info_label)
        
        # 统计信息
        stats_label = QLabel("今日使用: 3次\n总记录数: 127条")
        info_layout.addWidget(stats_label)
        
        info_widget.setLayout(info_layout)
        info_dock.setWidget(info_widget)
        self.addDockWidget(Qt.RightDockWidgetArea, info_dock)
    
    def createDailyTab(self):
        """创建每日运势标签页"""
        daily_widget = QWidget()
        layout = QVBoxLayout()
        
        # 标题
        title = QLabel("每日运势")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # 日期选择
        date_layout = QHBoxLayout()
        date_layout.addWidget(QLabel("选择日期:"))
        
        self.date_edit = QCalendarWidget()
        date_layout.addWidget(self.date_edit)
        
        layout.addLayout(date_layout)
        
        # 运势类型选择
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("运势类型:"))
        
        self.forecast_type = QComboBox()
        self.forecast_type.addItems(["整体运势", "爱情运势", "事业运势", "财运", "健康运"])
        type_layout.addWidget(self.forecast_type)
        
        self.get_forecast_button = QPushButton("获取运势")
        self.get_forecast_button.clicked.connect(self.getDailyForecast)
        type_layout.addWidget(self.get_forecast_button)
        
        layout.addLayout(type_layout)
        
        # 运势显示区域
        self.forecast_text = QTextEdit()
        self.forecast_text.setReadOnly(True)
        layout.addWidget(self.forecast_text)
        
        daily_widget.setLayout(layout)
        return daily_widget
    
    def getDailyForecast(self):
        """获取每日运势"""
        selected_date = self.date_edit.selectedDate().toString("yyyy-MM-dd")
        forecast_type = self.forecast_type.currentText()
        
        # 生成运势内容
        forecasts = {
            "整体运势": [
                "今天是你展现能力的好时机，抓住机会会有意外收获。",
                "运势平稳，适合处理日常事务，不宜做重大决定。",
                "今天可能会遇到一些小挑战，保持冷静可以顺利度过。",
                "贵人运强，有机会得到他人的帮助和支持。",
                "今天适合独处思考，给自己一些安静的时间。"
            ],
            "爱情运势": [
                "单身者有机会遇到心仪对象，多参加社交活动。",
                "情侣间沟通顺畅，适合一起规划未来。",
                "今天需要注意与伴侣的沟通方式，避免误会。",
                "爱情运平稳，适合享受二人世界的温馨。",
                "有机会通过朋友介绍认识不错的对象。"
            ],
            "事业运势": [
                "工作上有新机会，勇于尝试会有好结果。",
                "团队合作顺利，项目进展会比预期快。",
                "今天需要专注处理细节问题，避免粗心错误。",
                "有机会展示领导才能，得到上司赏识。",
                "适合学习新技能，为职业发展打下基础。"
            ],
            "财运": [
                "正财稳定，偏财运佳，可以小试手气。",
                "今天不适合重大投资，保守理财为宜。",
                "有机会获得意外之财，但也要注意节制。",
                "财务计划需要调整，避免不必要的开支。",
                "财运平稳，适合进行长期理财规划。"
            ],
            "健康运": [
                "精力充沛，适合进行体育锻炼。",
                "需要注意饮食卫生，避免肠胃不适。",
                "精神状态良好，适合进行户外活动。",
                "今天容易感到疲劳，需要适当休息。",
                "健康运平稳，保持规律作息很重要。"
            ]
        }
        
        # 基于日期生成"随机"但确定的结果
        date_hash = hash(selected_date + forecast_type) % 5
        forecast = forecasts[forecast_type][date_hash]
        
        # 添加幸运信息
        lucky_numbers = [random.randint(1, 9) for _ in range(3)]
        lucky_color = random.choice(["红色", "蓝色", "绿色", "黄色", "紫色", "白色", "黑色"])
        
        result = f"{selected_date} {forecast_type}\n\n"
        result += f"运势指数: {random.randint(3, 9)}/10\n\n"
        result += f"详细解读:\n{forecast}\n\n"
        result += f"幸运数字: {', '.join(map(str, lucky_numbers))}\n"
        result += f"幸运颜色: {lucky_color}\n"
        result += f"宜: {random.choice(['合作', '学习', '运动', '静思', '规划'])}\n"
        result += f"忌: {random.choice(['冲动', '拖延', '借贷', '争吵', '冒险'])}"
        
        self.forecast_text.setText(result)
    
    def on_card_drawn(self, card_name, is_reversed):
        """当塔罗牌被抽出时更新状态栏"""
        status = f"抽到塔罗牌: {card_name} ({'逆位' if is_reversed else '正位'})"
        self.statusBar().showMessage(status)
    
    def quickTarot(self):
        """快速抽牌"""
        self.tabs.setCurrentWidget(self.tarot_tab)
        self.tarot_tab.spread_type.setCurrentText("单张牌")
        self.tarot_tab.perform_reading()
    
    def quickBazi(self):
        """快速八字"""
        self.tabs.setCurrentWidget(self.bazi_tab)
        # 设置为当前日期
        today = datetime.now()
        self.bazi_tab.year_spin.setValue(today.year)
        self.bazi_tab.month_spin.setValue(today.month)
        self.bazi_tab.day_spin.setValue(today.day)
        self.bazi_tab.calculate_bazi()
    
    def quickForecast(self):
        """快速今日运势"""
        self.tabs.setCurrentWidget(self.daily_tab)
        self.date_edit.setSelectedDate(QDate.currentDate())
        self.forecast_type.setCurrentText("整体运势")
        self.getDailyForecast()
    
    def saveCurrentRecord(self):
        """保存当前记录"""
        current_tab = self.tabs.currentWidget()
        
        if current_tab == self.tarot_tab:
            self.tarot_tab.save_reading()
        elif current_tab == self.bazi_tab:
            self.bazi_tab.save_bazi()
        else:
            QMessageBox.information(self, "提示", "当前标签页不支持快速保存")
    
    def showDailyForecast(self):
        """显示今日运势对话框"""
        self.quickForecast()
        QMessageBox.information(self, "今日运势", self.forecast_text.toPlainText())
    
    def exportData(self):
        """导出数据"""
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getSaveFileName(self, "导出数据", "", "JSON Files (*.json);;All Files (*)", options=options)
        
        if file_name:
            # 简化的数据导出
            data = {
                "export_time": datetime.now().isoformat(),
                "system_version": "玄学系统 v2.0"
            }
            
            with open(file_name, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            QMessageBox.information(self, "成功", f"数据已导出到: {file_name}")
    
    def showSettings(self):
        """显示设置对话框"""
        QMessageBox.information(self, "设置", "设置功能开发中...")
    
    def showNumerologyCalculator(self):
        """显示数字命理计算器"""
        number, ok = QInputDialog.getInt(self, "数字命理计算", "请输入数字:")
        
        if ok:
            meanings = {
                1: "开始、独立、领导力",
                2: "合作、平衡、直觉",
                3: "创造力、表达、社交",
                4: "稳定、务实、组织",
                5: "自由、变化、冒险",
                6: "责任、关爱、家庭",
                7: "分析、灵性、智慧",
                8: "权力、财富、成就",
                9: "完成、智慧、人道主义",
                11: "直觉、灵感、精神导师",
                22: "大师建造者、大梦想",
                33: "大师教师、无私奉献"
            }
            
            meaning = meanings.get(number, "这是一个有特殊意义的数字")
            QMessageBox.information(self, "数字含义", f"数字 {number} 的含义:\n\n{meaning}")
    
    def showAbout(self):
        """显示关于对话框"""
        about_text = """
        <h2>高级玄学系统工具库 v2.0</h2>
        <p>这是一个功能强大的玄学分析工具集合，包含：</p>
        <ul>
            <li>高级塔罗牌占卜</li>
            <li>八字排盘与分析</li>
            <li>风水分析与建议</li>
            <li>掌纹分析</li>
            <li>数据分析与图表</li>
            <li>每日运势预测</li>
        </ul>
        <p>本软件仅供娱乐和研究使用，结果仅供参考。</p>
        <p>开发团队: 玄学科技</p>
        """
        
        QMessageBox.about(self, "关于", about_text)


def main():
    app = QApplication(sys.argv)
    
    # 设置应用样式
    app.setStyle('Fusion')
    
    # 设置应用图标和字体
    app.setFont(QFont("Arial", 10))
    
    # 创建并显示主窗口
    mystic_system = AdvancedMysticSystem()
    mystic_system.show()
    
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()