import sys
import json
import datetime
import random
import numpy as np
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QTextEdit, QListWidget, 
                             QLabel, QLineEdit, QTabWidget, QGroupBox, 
                             QSpinBox, QDoubleSpinBox, QSlider, QCheckBox,
                             QProgressBar, QMessageBox, QFileDialog, QSplitter)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QPalette, QColor, QPixmap, QPainter
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from pyqtgraph import ComboBox
from wordcloud import WordCloud
import sqlite3
from collections import Counter
import re


class DreamDatabase:
    """梦境数据库管理类"""
    
    def __init__(self, db_path="dreams.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS dreams (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                mood TEXT,
                clarity INTEGER,
                lucidity INTEGER,
                tags TEXT,
                category TEXT
            )
        ''')
        conn.commit()
        conn.close()
    
    def add_dream(self, title, content, mood="neutral", clarity=5, lucidity=0, tags="", category="general"):
        """添加梦境记录"""
        date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO dreams (date, title, content, mood, clarity, lucidity, tags, category)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (date, title, content, mood, clarity, lucidity, tags, category))
        conn.commit()
        dream_id = cursor.lastrowid
        conn.close()
        return dream_id
    
    def get_dreams(self, limit=None, category=None):
        """获取梦境记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = "SELECT * FROM dreams"
        params = []
        
        if category:
            query += " WHERE category = ?"
            params.append(category)
            
        query += " ORDER BY date DESC"
        
        if limit:
            query += " LIMIT ?"
            params.append(limit)
            
        cursor.execute(query, params)
        dreams = cursor.fetchall()
        conn.close()
        
        return dreams
    
    def get_dream_statistics(self):
        """获取梦境统计信息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 梦境总数
        cursor.execute("SELECT COUNT(*) FROM dreams")
        total_dreams = cursor.fetchone()[0]
        
        # 不同情绪的梦境数量
        cursor.execute("SELECT mood, COUNT(*) FROM dreams GROUP BY mood")
        mood_stats = dict(cursor.fetchall())
        
        # 平均清晰度
        cursor.execute("SELECT AVG(clarity) FROM dreams")
        avg_clarity = cursor.fetchone()[0] or 0
        
        # 平均清醒度
        cursor.execute("SELECT AVG(lucidity) FROM dreams")
        avg_lucidity = cursor.fetchone()[0] or 0
        
        # 最常见的标签
        cursor.execute("SELECT tags FROM dreams WHERE tags != ''")
        all_tags = []
        for row in cursor.fetchall():
            all_tags.extend([tag.strip() for tag in row[0].split(',')])
        
        tag_counts = Counter(all_tags)
        common_tags = tag_counts.most_common(10)
        
        conn.close()
        
        return {
            'total_dreams': total_dreams,
            'mood_stats': mood_stats,
            'avg_clarity': round(avg_clarity, 2),
            'avg_lucidity': round(avg_lucidity, 2),
            'common_tags': common_tags
        }


class DreamAnalyzer:
    """梦境分析器"""
    
    def __init__(self):
        self.emotion_words = {
            'happy': ['快乐', '开心', '兴奋', '喜悦', '幸福', '愉快'],
            'sad': ['悲伤', '难过', '伤心', '痛苦', '失落', '绝望'],
            'fear': ['恐惧', '害怕', '惊恐', '恐怖', '惊吓', '恐慌'],
            'angry': ['愤怒', '生气', '恼火', '暴躁', '气愤', '发怒'],
            'neutral': ['平常', '普通', '一般', '正常', '平淡']
        }
    
    def analyze_emotion(self, text):
        """分析梦境情绪"""
        emotion_scores = {emotion: 0 for emotion in self.emotion_words.keys()}
        
        for emotion, words in self.emotion_words.items():
            for word in words:
                emotion_scores[emotion] += text.count(word)
        
        # 如果没有检测到情绪词，返回中性
        if sum(emotion_scores.values()) == 0:
            return 'neutral'
        
        return max(emotion_scores.items(), key=lambda x: x[1])[0]
    
    def extract_keywords(self, text, top_n=10):
        """提取关键词"""
        # 简单的关键词提取：按词频排序
        words = re.findall(r'[\u4e00-\u9fa5]+', text)
        word_counts = Counter(words)
        
        # 过滤常见词
        common_words = {'的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好', '自己', '这个', '那', '他', '她', '它'}
        filtered_words = {word: count for word, count in word_counts.items() 
                         if word not in common_words and len(word) > 1}
        
        return Counter(filtered_words).most_common(top_n)
    
    def calculate_dream_coherence(self, text):
        """计算梦境连贯性评分（简单版）"""
        sentences = re.split(r'[。！？!?]', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if len(sentences) <= 1:
            return 5  # 单句梦境默认中等连贯性
        
        # 简单评估：句子数量和长度分布
        avg_length = sum(len(s) for s in sentences) / len(sentences)
        length_variance = sum((len(s) - avg_length) ** 2 for s in sentences) / len(sentences)
        
        # 归一化到1-10分
        coherence = max(1, min(10, 10 - (length_variance / 100)))
        return round(coherence, 1)


class DreamVisualizationWidget(FigureCanvas):
    """梦境可视化组件"""
    
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        super().__init__(self.fig)
        self.setParent(parent)
        
        self.db = DreamDatabase()
        self.analyzer = DreamAnalyzer()
    
    def plot_mood_distribution(self):
        """绘制情绪分布图"""
        self.fig.clear()
        stats = self.db.get_dream_statistics()
        mood_stats = stats['mood_stats']
        
        ax = self.fig.add_subplot(111)
        moods = list(mood_stats.keys())
        counts = list(mood_stats.values())
        
        colors = ['gold', 'lightcoral', 'lightblue', 'lightgreen', 'plum']
        ax.bar(moods, counts, color=colors[:len(moods)])
        ax.set_title('梦境情绪分布')
        ax.set_ylabel('数量')
        
        self.fig.tight_layout()
        self.draw()
    
    def plot_clarity_trend(self):
        """绘制清晰度趋势图"""
        dreams = self.db.get_dreams(limit=30)  # 最近30个梦境
        
        if not dreams:
            self.fig.clear()
            ax = self.fig.add_subplot(111)
            ax.text(0.5, 0.5, '暂无数据', ha='center', va='center', transform=ax.transAxes)
            ax.set_title('梦境清晰度趋势')
            self.fig.tight_layout()
            self.draw()
            return
        
        # 提取日期和清晰度
        dates = [dream[1] for dream in dreams][::-1]  # 反转以时间顺序显示
        clarities = [dream[5] for dream in dreams][::-1]
        
        self.fig.clear()
        ax = self.fig.add_subplot(111)
        ax.plot(range(len(dates)), clarities, marker='o', linewidth=2, markersize=4)
        ax.set_title('梦境清晰度趋势')
        ax.set_ylabel('清晰度 (1-10)')
        ax.set_xlabel('梦境序号')
        ax.set_ylim(0, 10)
        ax.grid(True, linestyle='--', alpha=0.7)
        
        # 设置x轴标签为日期（简化显示）
        if len(dates) > 10:
            step = len(dates) // 5
            ax.set_xticks(range(0, len(dates), step))
            ax.set_xticklabels([dates[i][5:10] for i in range(0, len(dates), step)])
        else:
            ax.set_xticks(range(len(dates)))
            ax.set_xticklabels([date[5:10] for date in dates])
        
        self.fig.tight_layout()
        self.draw()
    
    def generate_word_cloud(self, dream_texts):
        """生成词云图"""
        if not dream_texts:
            self.fig.clear()
            ax = self.fig.add_subplot(111)
            ax.text(0.5, 0.5, '暂无数据', ha='center', va='center', transform=ax.transAxes)
            ax.set_title('梦境词云')
            self.fig.tight_layout()
            self.draw()
            return
        
        # 合并所有梦境文本
        all_text = ' '.join(dream_texts)
        
        # 生成词云
        wordcloud = WordCloud(
            font_path='simhei.ttf',  # 中文字体
            width=800, 
            height=400, 
            background_color='white',
            max_words=100
        ).generate(all_text)
        
        self.fig.clear()
        ax = self.fig.add_subplot(111)
        ax.imshow(wordcloud, interpolation='bilinear')
        ax.axis('off')
        ax.set_title('梦境词云')
        
        self.fig.tight_layout()
        self.draw()


class DreamSimulator:
    """梦境模拟器"""
    
    def __init__(self):
        self.themes = [
            "飞行", "追逐", "坠落", "考试", "迷路", 
            "遇见名人", "回到过去", "预见未来", "超能力", "奇幻冒险"
        ]
        
        self.locations = [
            "童年家园", "学校", "森林", "海滩", "城市", 
            "外太空", "古代宫殿", "未来世界", "神秘岛屿", "梦境迷宫"
        ]
        
        self.characters = [
            "家人", "朋友", "陌生人", "已故亲人", "名人", 
            "神话生物", "动物", "自己", "虚构角色", "神秘导师"
        ]
    
    def generate_dream(self, theme=None, length=5):
        """生成模拟梦境"""
        if not theme:
            theme = random.choice(self.themes)
        
        location = random.choice(self.locations)
        character = random.choice(self.characters)
        
        # 根据主题生成梦境内容
        dream_templates = {
            "飞行": f"我梦见自己在{location}上空飞翔，感觉非常自由。{character}也在附近飞翔，我们一起探索了这个神奇的地方。",
            "追逐": f"在{location}，我被一个神秘的存在追逐。我拼命奔跑，但似乎永远无法摆脱它。最后，我遇到了{character}，他/她帮助我逃脱。",
            "坠落": f"我梦见自己从{location}的高处坠落，心跳加速。在坠落过程中，我看到了{character}，他/她试图抓住我。",
            "考试": f"我回到了学生时代，在{location}参加一场重要的考试。但试卷上的题目我一道都不会，非常焦虑。{character}坐在我旁边，试图帮助我。",
            "迷路": f"我在{location}迷路了，四处寻找出口。这个地方似乎没有尽头，我遇到了{character}，他/她给我指了一条路。"
        }
        
        # 如果主题不在模板中，使用通用模板
        if theme not in dream_templates:
            dream_content = f"我梦见自己在{location}，主题是关于{theme}的。在梦中，我遇到了{character}，我们一起经历了一段奇妙的冒险。"
        else:
            dream_content = dream_templates[theme]
        
        # 根据长度扩展内容
        if length > 5:
            extensions = [
                "梦境中的色彩非常鲜艳，一切都显得那么真实。",
                "我能感受到梦中的情绪波动，从紧张到放松，再到兴奋。",
                "梦中的时间感很奇怪，有时过得很快，有时又很慢。",
                "我意识到自己在做梦，尝试控制梦境的发展。",
                "梦境最后出现了一个转折，让我感到非常意外。"
            ]
            
            for _ in range(length - 5):
                dream_content += " " + random.choice(extensions)
        
        return {
            "title": f"{theme}之梦",
            "content": dream_content,
            "theme": theme,
            "length": length
        }


class DreamRecorderWidget(QWidget):
    """梦境记录组件"""
    
    dream_saved = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.db = DreamDatabase()
        self.analyzer = DreamAnalyzer()
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 标题输入
        title_layout = QHBoxLayout()
        title_layout.addWidget(QLabel("梦境标题:"))
        self.title_input = QLineEdit()
        title_layout.addWidget(self.title_input)
        layout.addLayout(title_layout)
        
        # 内容输入
        content_layout = QVBoxLayout()
        content_layout.addWidget(QLabel("梦境内容:"))
        self.content_input = QTextEdit()
        self.content_input.setMinimumHeight(200)
        content_layout.addWidget(self.content_input)
        layout.addLayout(content_layout)
        
        # 情绪和评分
        metrics_layout = QHBoxLayout()
        
        # 情绪选择
        mood_layout = QVBoxLayout()
        mood_layout.addWidget(QLabel("情绪:"))
        self.mood_combo = QComboBox()
        self.mood_combo.addItems(["快乐", "悲伤", "恐惧", "愤怒", "中性"])
        mood_layout.addWidget(self.mood_combo)
        metrics_layout.addLayout(mood_layout)
        
        # 清晰度
        clarity_layout = QVBoxLayout()
        clarity_layout.addWidget(QLabel("清晰度 (1-10):"))
        self.clarity_slider = QSlider(Qt.Horizontal)
        self.clarity_slider.setRange(1, 10)
        self.clarity_slider.setValue(5)
        self.clarity_label = QLabel("5")
        clarity_layout.addWidget(self.clarity_slider)
        clarity_layout.addWidget(self.clarity_label)
        metrics_layout.addLayout(clarity_layout)
        
        # 清醒度
        lucidity_layout = QVBoxLayout()
        lucidity_layout.addWidget(QLabel("清醒度 (1-10):"))
        self.lucidity_slider = QSlider(Qt.Horizontal)
        self.lucidity_slider.setRange(0, 10)
        self.lucidity_slider.setValue(0)
        self.lucidity_label = QLabel("0")
        lucidity_layout.addWidget(self.lucidity_slider)
        lucidity_layout.addWidget(self.lucidity_label)
        metrics_layout.addLayout(lucidity_layout)
        
        layout.addLayout(metrics_layout)
        
        # 标签和分类
        tags_layout = QHBoxLayout()
        tags_layout.addWidget(QLabel("标签 (用逗号分隔):"))
        self.tags_input = QLineEdit()
        tags_layout.addWidget(self.tags_input)
        
        tags_layout.addWidget(QLabel("分类:"))
        self.category_combo = QComboBox()
        self.category_combo.addItems(["日常", "奇幻", "噩梦", "预知", "回忆", "其他"])
        tags_layout.addWidget(self.category_combo)
        
        layout.addLayout(tags_layout)
        
        # 按钮
        button_layout = QHBoxLayout()
        
        self.save_btn = QPushButton("保存梦境")
        self.save_btn.clicked.connect(self.save_dream)
        button_layout.addWidget(self.save_btn)
        
        self.analyze_btn = QPushButton("自动分析")
        self.analyze_btn.clicked.connect(self.auto_analyze)
        button_layout.addWidget(self.analyze_btn)
        
        self.clear_btn = QPushButton("清空")
        self.clear_btn.clicked.connect(self.clear_form)
        button_layout.addWidget(self.clear_btn)
        
        layout.addLayout(button_layout)
        
        # 连接滑块信号
        self.clarity_slider.valueChanged.connect(lambda v: self.clarity_label.setText(str(v)))
        self.lucidity_slider.valueChanged.connect(lambda v: self.lucidity_label.setText(str(v)))
        
        self.setLayout(layout)
    
    def save_dream(self):
        """保存梦境记录"""
        title = self.title_input.text().strip()
        content = self.content_input.toPlainText().strip()
        
        if not title or not content:
            QMessageBox.warning(self, "输入错误", "请填写梦境标题和内容")
            return
        
        mood_map = {"快乐": "happy", "悲伤": "sad", "恐惧": "fear", "愤怒": "angry", "中性": "neutral"}
        mood = mood_map.get(self.mood_combo.currentText(), "neutral")
        
        clarity = self.clarity_slider.value()
        lucidity = self.lucidity_slider.value()
        tags = self.tags_input.text().strip()
        category = self.category_combo.currentText()
        
        self.db.add_dream(title, content, mood, clarity, lucidity, tags, category)
        
        QMessageBox.information(self, "成功", "梦境记录已保存")
        self.dream_saved.emit()
        self.clear_form()
    
    def auto_analyze(self):
        """自动分析梦境内容"""
        content = self.content_input.toPlainText().strip()
        if not content:
            QMessageBox.warning(self, "输入错误", "请先输入梦境内容")
            return
        
        # 分析情绪
        emotion = self.analyzer.analyze_emotion(content)
        emotion_map = {"happy": "快乐", "sad": "悲伤", "fear": "恐惧", "angry": "愤怒", "neutral": "中性"}
        self.mood_combo.setCurrentText(emotion_map.get(emotion, "中性"))
        
        # 分析连贯性作为清晰度参考
        coherence = self.analyzer.calculate_dream_coherence(content)
        self.clarity_slider.setValue(int(coherence))
        
        # 提取关键词作为标签建议
        keywords = self.analyzer.extract_keywords(content, top_n=5)
        if keywords:
            tag_suggestion = ", ".join([word for word, count in keywords])
            self.tags_input.setText(tag_suggestion)
        
        QMessageBox.information(self, "分析完成", f"已自动分析梦境内容\n检测到情绪: {emotion_map.get(emotion, '中性')}\n连贯性评分: {coherence}/10")
    
    def clear_form(self):
        """清空表单"""
        self.title_input.clear()
        self.content_input.clear()
        self.mood_combo.setCurrentIndex(4)  # 中性
        self.clarity_slider.setValue(5)
        self.lucidity_slider.setValue(0)
        self.tags_input.clear()
        self.category_combo.setCurrentIndex(0)


class DreamLibraryWidget(QWidget):
    """梦境库组件"""
    
    def __init__(self):
        super().__init__()
        self.db = DreamDatabase()
        self.init_ui()
        self.load_dreams()
    
    def init_ui(self):
        layout = QHBoxLayout()
        
        # 左侧梦境列表
        left_panel = QVBoxLayout()
        left_panel.addWidget(QLabel("梦境记录:"))
        
        self.dream_list = QListWidget()
        self.dream_list.currentRowChanged.connect(self.display_dream)
        left_panel.addWidget(self.dream_list)
        
        # 筛选选项
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("分类筛选:"))
        self.category_filter = QComboBox()
        self.category_filter.addItems(["全部", "日常", "奇幻", "噩梦", "预知", "回忆", "其他"])
        self.category_filter.currentTextChanged.connect(self.load_dreams)
        filter_layout.addWidget(self.category_filter)
        
        filter_layout.addWidget(QLabel("显示数量:"))
        self.limit_spin = QSpinBox()
        self.limit_spin.setRange(1, 100)
        self.limit_spin.setValue(20)
        self.limit_spin.valueChanged.connect(self.load_dreams)
        filter_layout.addWidget(self.limit_spin)
        
        left_panel.addLayout(filter_layout)
        
        # 右侧梦境详情
        right_panel = QVBoxLayout()
        right_panel.addWidget(QLabel("梦境详情:"))
        
        self.dream_title = QLabel("")
        self.dream_title.setFont(QFont("Arial", 12, QFont.Bold))
        right_panel.addWidget(self.dream_title)
        
        self.dream_date = QLabel("")
        right_panel.addWidget(self.dream_date)
        
        self.dream_content = QTextEdit()
        self.dream_content.setReadOnly(True)
        right_panel.addWidget(self.dream_content)
        
        # 梦境元数据
        meta_layout = QHBoxLayout()
        
        self.dream_mood = QLabel("情绪: -")
        meta_layout.addWidget(self.dream_mood)
        
        self.dream_clarity = QLabel("清晰度: -")
        meta_layout.addWidget(self.dream_clarity)
        
        self.dream_lucidity = QLabel("清醒度: -")
        meta_layout.addWidget(self.dream_lucidity)
        
        self.dream_tags = QLabel("标签: -")
        meta_layout.addWidget(self.dream_tags)
        
        self.dream_category = QLabel("分类: -")
        meta_layout.addWidget(self.dream_category)
        
        right_panel.addLayout(meta_layout)
        
        # 操作按钮
        button_layout = QHBoxLayout()
        
        self.export_btn = QPushButton("导出梦境")
        self.export_btn.clicked.connect(self.export_dream)
        button_layout.addWidget(self.export_btn)
        
        self.delete_btn = QPushButton("删除梦境")
        self.delete_btn.clicked.connect(self.delete_dream)
        button_layout.addWidget(self.delete_btn)
        
        right_panel.addLayout(button_layout)
        
        # 将左右面板添加到主布局
        splitter = QSplitter(Qt.Horizontal)
        
        left_widget = QWidget()
        left_widget.setLayout(left_panel)
        splitter.addWidget(left_widget)
        
        right_widget = QWidget()
        right_widget.setLayout(right_panel)
        splitter.addWidget(right_widget)
        
        splitter.setSizes([300, 500])
        layout.addWidget(splitter)
        
        self.setLayout(layout)
    
    def load_dreams(self):
        """加载梦境列表"""
        self.dream_list.clear()
        category = self.category_filter.currentText()
        limit = self.limit_spin.value()
        
        if category == "全部":
            dreams = self.db.get_dreams(limit=limit)
        else:
            dreams = self.db.get_dreams(limit=limit, category=category)
        
        for dream in dreams:
            self.dream_list.addItem(f"{dream[1]} - {dream[2]}")
        
        self.dreams_data = dreams
    
    def display_dream(self, index):
        """显示选中的梦境详情"""
        if index < 0 or index >= len(self.dreams_data):
            return
        
        dream = self.dreams_data[index]
        
        self.dream_title.setText(dream[2])  # 标题
        self.dream_date.setText(f"记录时间: {dream[1]}")  # 日期
        
        self.dream_content.setText(dream[3])  # 内容
        
        # 元数据
        mood_map = {"happy": "快乐", "sad": "悲伤", "fear": "恐惧", "angry": "愤怒", "neutral": "中性"}
        self.dream_mood.setText(f"情绪: {mood_map.get(dream[4], '中性')}")
        self.dream_clarity.setText(f"清晰度: {dream[5]}/10")
        self.dream_lucidity.setText(f"清醒度: {dream[6]}/10")
        self.dream_tags.setText(f"标签: {dream[7] if dream[7] else '无'}")
        self.dream_category.setText(f"分类: {dream[8]}")
        
        self.current_dream_index = index
    
    def export_dream(self):
        """导出当前梦境"""
        if not hasattr(self, 'current_dream_index'):
            QMessageBox.warning(self, "错误", "请先选择一个梦境")
            return
        
        dream = self.dreams_data[self.current_dream_index]
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出梦境", f"{dream[2]}.json", "JSON文件 (*.json)"
        )
        
        if file_path:
            dream_dict = {
                "id": dream[0],
                "date": dream[1],
                "title": dream[2],
                "content": dream[3],
                "mood": dream[4],
                "clarity": dream[5],
                "lucidity": dream[6],
                "tags": dream[7],
                "category": dream[8]
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(dream_dict, f, ensure_ascii=False, indent=2)
            
            QMessageBox.information(self, "成功", "梦境已导出")
    
    def delete_dream(self):
        """删除当前梦境"""
        if not hasattr(self, 'current_dream_index'):
            QMessageBox.warning(self, "错误", "请先选择一个梦境")
            return
        
        reply = QMessageBox.question(
            self, "确认删除", 
            "确定要删除这个梦境记录吗？此操作不可恢复。",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            dream = self.dreams_data[self.current_dream_index]
            dream_id = dream[0]
            
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM dreams WHERE id = ?", (dream_id,))
            conn.commit()
            conn.close()
            
            self.load_dreams()
            QMessageBox.information(self, "成功", "梦境已删除")


class DreamAnalysisWidget(QWidget):
    """梦境分析组件"""
    
    def __init__(self):
        super().__init__()
        self.db = DreamDatabase()
        self.init_ui()
        self.update_stats()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 统计信息
        stats_group = QGroupBox("梦境统计")
        stats_layout = QHBoxLayout()
        
        self.total_dreams = QLabel("总梦境数: 0")
        stats_layout.addWidget(self.total_dreams)
        
        self.avg_clarity = QLabel("平均清晰度: 0")
        stats_layout.addWidget(self.avg_clarity)
        
        self.avg_lucidity = QLabel("平均清醒度: 0")
        stats_layout.addWidget(self.avg_lucidity)
        
        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)
        
        # 可视化区域
        viz_layout = QHBoxLayout()
        
        self.viz_widget = DreamVisualizationWidget(self, width=8, height=6)
        viz_layout.addWidget(self.viz_widget)
        
        # 可视化控制
        viz_controls = QVBoxLayout()
        
        self.mood_dist_btn = QPushButton("情绪分布")
        self.mood_dist_btn.clicked.connect(self.viz_widget.plot_mood_distribution)
        viz_controls.addWidget(self.mood_dist_btn)
        
        self.clarity_trend_btn = QPushButton("清晰度趋势")
        self.clarity_trend_btn.clicked.connect(self.viz_widget.plot_clarity_trend)
        viz_controls.addWidget(self.clarity_trend_btn)
        
        self.wordcloud_btn = QPushButton("生成词云")
        self.wordcloud_btn.clicked.connect(self.generate_wordcloud)
        viz_controls.addWidget(self.wordcloud_btn)
        
        viz_controls.addStretch()
        viz_layout.addLayout(viz_controls)
        
        layout.addLayout(viz_layout)
        
        # 常见标签
        tags_group = QGroupBox("最常见标签")
        self.tags_layout = QHBoxLayout()
        
        tags_group.setLayout(self.tags_layout)
        layout.addWidget(tags_group)
        
        self.setLayout(layout)
    
    def update_stats(self):
        """更新统计信息"""
        stats = self.db.get_dream_statistics()
        
        self.total_dreams.setText(f"总梦境数: {stats['total_dreams']}")
        self.avg_clarity.setText(f"平均清晰度: {stats['avg_clarity']}")
        self.avg_lucidity.setText(f"平均清醒度: {stats['avg_lucidity']}")
        
        # 更新标签显示
        # 清除现有标签
        for i in reversed(range(self.tags_layout.count())): 
            self.tags_layout.itemAt(i).widget().setParent(None)
        
        # 添加新标签
        for tag, count in stats['common_tags']:
            tag_label = QLabel(f"{tag}({count})")
            self.tags_layout.addWidget(tag_label)
        
        self.tags_layout.addStretch()
    
    def generate_wordcloud(self):
        """生成词云"""
        dreams = self.db.get_dreams()
        dream_texts = [dream[3] for dream in dreams]
        self.viz_widget.generate_word_cloud(dream_texts)


class DreamSimulatorWidget(QWidget):
    """梦境模拟器组件"""
    
    def __init__(self):
        super().__init__()
        self.simulator = DreamSimulator()
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 模拟控制
        control_layout = QHBoxLayout()
        
        control_layout.addWidget(QLabel("梦境主题:"))
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["随机"] + self.simulator.themes)
        control_layout.addWidget(self.theme_combo)
        
        control_layout.addWidget(QLabel("梦境长度:"))
        self.length_slider = QSlider(Qt.Horizontal)
        self.length_slider.setRange(1, 10)
        self.length_slider.setValue(5)
        self.length_label = QLabel("5")
        control_layout.addWidget(self.length_slider)
        control_layout.addWidget(self.length_label)
        
        self.generate_btn = QPushButton("生成梦境")
        self.generate_btn.clicked.connect(self.generate_dream)
        control_layout.addWidget(self.generate_btn)
        
        layout.addLayout(control_layout)
        
        # 生成的梦境
        self.dream_title = QLabel("")
        self.dream_title.setFont(QFont("Arial", 12, QFont.Bold))
        layout.addWidget(self.dream_title)
        
        self.dream_content = QTextEdit()
        self.dream_content.setReadOnly(True)
        layout.addWidget(self.dream_content)
        
        # 保存按钮
        button_layout = QHBoxLayout()
        
        self.save_btn = QPushButton("保存到梦境库")
        self.save_btn.clicked.connect(self.save_dream)
        self.save_btn.setEnabled(False)
        button_layout.addWidget(self.save_btn)
        
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        # 连接信号
        self.length_slider.valueChanged.connect(lambda v: self.length_label.setText(str(v)))
        
        self.setLayout(layout)
    
    def generate_dream(self):
        """生成模拟梦境"""
        theme = self.theme_combo.currentText()
        if theme == "随机":
            theme = None
        
        length = self.length_slider.value()
        
        dream = self.simulator.generate_dream(theme, length)
        
        self.dream_title.setText(dream["title"])
        self.dream_content.setText(dream["content"])
        self.current_dream = dream
        self.save_btn.setEnabled(True)
    
    def save_dream(self):
        """保存模拟的梦境"""
        if not hasattr(self, 'current_dream'):
            return
        
        db = DreamDatabase()
        db.add_dream(
            self.current_dream["title"],
            self.current_dream["content"],
            category="模拟"
        )
        
        QMessageBox.information(self, "成功", "模拟梦境已保存到梦境库")
        self.save_btn.setEnabled(False)


class QComboBox(ComboBox):
    """为了代码完整性而添加的简单QComboBox类"""
    pass


class DreamSystem(QMainWindow):
    """梦境系统主窗口"""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("梦境系统 - 高级工具库")
        self.setGeometry(100, 100, 1200, 800)
        
        # 创建标签页
        self.tabs = QTabWidget()
        
        # 梦境记录页
        self.recorder_tab = DreamRecorderWidget()
        self.recorder_tab.dream_saved.connect(self.on_dream_saved)
        self.tabs.addTab(self.recorder_tab, "记录梦境")
        
        # 梦境库页
        self.library_tab = DreamLibraryWidget()
        self.tabs.addTab(self.library_tab, "梦境库")
        
        # 梦境分析页
        self.analysis_tab = DreamAnalysisWidget()
        self.tabs.addTab(self.analysis_tab, "梦境分析")
        
        # 梦境模拟页
        self.simulator_tab = DreamSimulatorWidget()
        self.tabs.addTab(self.simulator_tab, "梦境模拟")
        
        self.setCentralWidget(self.tabs)
        
        # 状态栏
        self.statusBar().showMessage("梦境系统已就绪")
    
    def on_dream_saved(self):
        """当梦境保存时更新其他标签页"""
        self.library_tab.load_dreams()
        self.analysis_tab.update_stats()
        self.statusBar().showMessage("梦境已保存")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 设置应用样式
    app.setStyle("Fusion")
    
    # 创建并显示主窗口
    window = DreamSystem()
    window.show()
    
    sys.exit(app.exec_())