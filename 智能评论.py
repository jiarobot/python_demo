import sys
import json
import sqlite3
from datetime import datetime
from typing import List, Dict, Any, Optional
import pandas as pd
from textblob import TextBlob
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
import numpy as np

from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                             QWidget, QTextEdit, QLineEdit, QPushButton, QListWidget, 
                             QListWidgetItem, QLabel, QTabWidget, QTableWidget, 
                             QTableWidgetItem, QHeaderView, QSplitter, QComboBox,
                             QSpinBox, QCheckBox, QMessageBox, QProgressBar,
                             QGroupBox, QFormLayout, QFileDialog)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QColor, QPalette, QIcon


class SentimentAnalyzer:
    """情感分析器"""
    
    @staticmethod
    def analyze_sentiment(text: str) -> Dict[str, Any]:
        """分析文本情感"""
        blob = TextBlob(text)
        polarity = blob.sentiment.polarity  # 情感极性 (-1到1)
        subjectivity = blob.sentiment.subjectivity  # 主观性 (0到1)
        
        # 情感分类
        if polarity > 0.1:
            sentiment = "positive"
        elif polarity < -0.1:
            sentiment = "negative"
        else:
            sentiment = "neutral"
            
        return {
            "sentiment": sentiment,
            "polarity": polarity,
            "subjectivity": subjectivity,
            "confidence": abs(polarity)  # 置信度
        }


class CommentClusterer:
    """评论聚类分析器"""
    
    def __init__(self):
        self.vectorizer = TfidfVectorizer(max_features=1000, stop_words='english')
        self.kmeans = KMeans(n_clusters=5, random_state=42)
        self.is_fitted = False
        
    def fit_predict(self, comments: List[str]) -> List[int]:
        """对评论进行聚类"""
        if not comments:
            return []
            
        # 向量化文本
        X = self.vectorizer.fit_transform(comments)
        
        # 聚类
        labels = self.kmeans.fit_predict(X)
        self.is_fitted = True
        
        return labels.tolist()
    
    def get_cluster_keywords(self, comments: List[str], n_keywords: int = 5) -> Dict[int, List[str]]:
        """获取每个聚类的关键词"""
        if not self.is_fitted or not comments:
            return {}
            
        X = self.vectorizer.transform(comments)
        feature_names = self.vectorizer.get_feature_names_out()
        
        cluster_keywords = {}
        for cluster_id in range(self.kmeans.n_clusters):
            # 获取聚类中心
            center = self.kmeans.cluster_centers_[cluster_id]
            
            # 获取最重要的特征
            top_indices = center.argsort()[-n_keywords:][::-1]
            keywords = [feature_names[i] for i in top_indices]
            
            cluster_keywords[cluster_id] = keywords
            
        return cluster_keywords


class DatabaseManager:
    """数据库管理类"""
    
    def __init__(self, db_path: str = "comments.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                sentiment TEXT,
                polarity REAL,
                subjectivity REAL,
                cluster_id INTEGER,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                source TEXT,
                rating INTEGER
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS replies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                comment_id INTEGER,
                content TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (comment_id) REFERENCES comments (id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def add_comment(self, content: str, source: str = "manual", rating: int = None) -> int:
        """添加评论到数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 分析情感
        sentiment_data = SentimentAnalyzer.analyze_sentiment(content)
        
        cursor.execute('''
            INSERT INTO comments (content, sentiment, polarity, subjectivity, source, rating)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (content, sentiment_data["sentiment"], sentiment_data["polarity"], 
              sentiment_data["subjectivity"], source, rating))
        
        comment_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return comment_id
    
    def get_comments(self, limit: int = 100, sentiment_filter: str = None) -> List[Dict]:
        """获取评论列表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = "SELECT * FROM comments ORDER BY timestamp DESC LIMIT ?"
        params = [limit]
        
        if sentiment_filter:
            query = "SELECT * FROM comments WHERE sentiment = ? ORDER BY timestamp DESC LIMIT ?"
            params = [sentiment_filter, limit]
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        comments = []
        for row in rows:
            comments.append({
                "id": row[0],
                "content": row[1],
                "sentiment": row[2],
                "polarity": row[3],
                "subjectivity": row[4],
                "cluster_id": row[5],
                "timestamp": row[6],
                "source": row[7],
                "rating": row[8]
            })
        
        conn.close()
        return comments
    
    def add_reply(self, comment_id: int, content: str):
        """添加回复"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO replies (comment_id, content)
            VALUES (?, ?)
        ''', (comment_id, content))
        
        conn.commit()
        conn.close()
    
    def get_replies(self, comment_id: int) -> List[Dict]:
        """获取评论的回复"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM replies WHERE comment_id = ? ORDER BY timestamp
        ''', (comment_id,))
        
        rows = cursor.fetchall()
        replies = [{"id": row[0], "content": row[2], "timestamp": row[3]} for row in rows]
        
        conn.close()
        return replies
    
    def update_cluster_ids(self, comment_ids: List[int], cluster_ids: List[int]):
        """更新评论的聚类ID"""
        if len(comment_ids) != len(cluster_ids):
            return
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for comment_id, cluster_id in zip(comment_ids, cluster_ids):
            cursor.execute('''
                UPDATE comments SET cluster_id = ? WHERE id = ?
            ''', (cluster_id, comment_id))
        
        conn.commit()
        conn.close()


class AnalysisWorker(QThread):
    """后台分析工作线程"""
    
    progress_updated = pyqtSignal(int)
    analysis_completed = pyqtSignal(dict)
    
    def __init__(self, comments: List[str], comment_ids: List[int]):
        super().__init__()
        self.comments = comments
        self.comment_ids = comment_ids
        self.clusterer = CommentClusterer()
    
    def run(self):
        """执行分析任务"""
        # 情感分析
        sentiments = []
        polarities = []
        subjectivities = []
        
        for i, comment in enumerate(self.comments):
            sentiment_data = SentimentAnalyzer.analyze_sentiment(comment)
            sentiments.append(sentiment_data["sentiment"])
            polarities.append(sentiment_data["polarity"])
            subjectivities.append(sentiment_data["subjectivity"])
            
            # 更新进度
            progress = int((i + 1) / len(self.comments) * 50)
            self.progress_updated.emit(progress)
        
        # 聚类分析
        if len(self.comments) > 1:
            cluster_labels = self.clusterer.fit_predict(self.comments)
            cluster_keywords = self.clusterer.get_cluster_keywords(self.comments)
        else:
            cluster_labels = [0] * len(self.comments)
            cluster_keywords = {0: ["insufficient", "data"]}
        
        # 发送结果
        result = {
            "comment_ids": self.comment_ids,
            "sentiments": sentiments,
            "polarities": polarities,
            "subjectivities": subjectivities,
            "cluster_labels": cluster_labels,
            "cluster_keywords": cluster_keywords
        }
        
        self.progress_updated.emit(100)
        self.analysis_completed.emit(result)


class CommentWidget(QWidget):
    """单个评论显示组件"""
    
    def __init__(self, comment_data: Dict, parent=None):
        super().__init__(parent)
        self.comment_data = comment_data
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout()
        
        # 评论内容
        content_label = QLabel(self.comment_data["content"])
        content_label.setWordWrap(True)
        content_label.setStyleSheet("font-size: 12pt; margin-bottom: 5px;")
        layout.addWidget(content_label)
        
        # 元信息行
        meta_layout = QHBoxLayout()
        
        # 情感标签
        sentiment = self.comment_data.get("sentiment", "unknown")
        sentiment_color = {
            "positive": "#4CAF50",
            "negative": "#F44336",
            "neutral": "#2196F3",
            "unknown": "#9E9E9E"
        }.get(sentiment, "#9E9E9E")
        
        sentiment_label = QLabel(sentiment.upper())
        sentiment_label.setStyleSheet(f"""
            background-color: {sentiment_color};
            color: white;
            padding: 2px 8px;
            border-radius: 10px;
            font-size: 9pt;
            font-weight: bold;
        """)
        meta_layout.addWidget(sentiment_label)
        
        # 时间戳
        timestamp = self.comment_data.get("timestamp", "")
        if timestamp:
            time_label = QLabel(timestamp)
            time_label.setStyleSheet("color: #666; font-size: 9pt;")
            meta_layout.addWidget(time_label)
        
        # 来源
        source = self.comment_data.get("source", "")
        if source:
            source_label = QLabel(f"From: {source}")
            source_label.setStyleSheet("color: #666; font-size: 9pt;")
            meta_layout.addWidget(source_label)
        
        meta_layout.addStretch()
        layout.addLayout(meta_layout)
        
        self.setLayout(layout)
        self.setStyleSheet("""
            QWidget {
                background-color: #F5F5F5;
                border: 1px solid #E0E0E0;
                border-radius: 5px;
                padding: 10px;
                margin: 5px 0;
            }
        """)


class CommentInputWidget(QWidget):
    """评论输入组件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout()
        
        # 输入框
        self.input_field = QTextEdit()
        self.input_field.setPlaceholderText("输入评论内容...")
        self.input_field.setMaximumHeight(100)
        layout.addWidget(self.input_field)
        
        # 控制行
        control_layout = QHBoxLayout()
        
        # 评分选择
        control_layout.addWidget(QLabel("评分:"))
        self.rating_combo = QComboBox()
        self.rating_combo.addItem("无评分", None)
        for i in range(1, 6):
            self.rating_combo.addItem("★" * i, i)
        control_layout.addWidget(self.rating_combo)
        
        # 来源输入
        control_layout.addWidget(QLabel("来源:"))
        self.source_input = QLineEdit()
        self.source_input.setPlaceholderText("评论来源")
        self.source_input.setMaximumWidth(150)
        control_layout.addWidget(self.source_input)
        
        control_layout.addStretch()
        
        # 添加按钮
        self.add_button = QPushButton("添加评论")
        self.add_button.clicked.connect(self.add_comment)
        control_layout.addWidget(self.add_button)
        
        layout.addLayout(control_layout)
        self.setLayout(layout)
    
    def add_comment(self):
        """添加评论"""
        content = self.input_field.toPlainText().strip()
        if not content:
            QMessageBox.warning(self, "输入错误", "评论内容不能为空")
            return
        
        rating = self.rating_combo.currentData()
        source = self.source_input.text().strip() or "manual"
        
        # 发送信号
        self.parent().add_comment_signal.emit(content, source, rating)
        
        # 清空输入
        self.input_field.clear()
        self.source_input.clear()


class AnalysisDashboard(QWidget):
    """分析仪表板"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout()
        
        # 统计信息组
        stats_group = QGroupBox("评论统计")
        stats_layout = QHBoxLayout()
        
        self.total_comments_label = QLabel("总评论数: 0")
        self.positive_comments_label = QLabel("正面评论: 0")
        self.negative_comments_label = QLabel("负面评论: 0")
        self.neutral_comments_label = QLabel("中性评论: 0")
        
        for label in [self.total_comments_label, self.positive_comments_label, 
                     self.negative_comments_label, self.neutral_comments_label]:
            label.setStyleSheet("font-size: 11pt; font-weight: bold;")
            stats_layout.addWidget(label)
        
        stats_layout.addStretch()
        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)
        
        # 情感分布组
        sentiment_group = QGroupBox("情感分析")
        sentiment_layout = QVBoxLayout()
        
        self.sentiment_table = QTableWidget()
        self.sentiment_table.setColumnCount(3)
        self.sentiment_table.setHorizontalHeaderLabels(["情感类型", "数量", "百分比"])
        self.sentiment_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        sentiment_layout.addWidget(self.sentiment_table)
        
        sentiment_group.setLayout(sentiment_layout)
        layout.addWidget(sentiment_group)
        
        # 聚类分析组
        cluster_group = QGroupBox("主题聚类")
        cluster_layout = QVBoxLayout()
        
        self.cluster_table = QTableWidget()
        self.cluster_table.setColumnCount(3)
        self.cluster_table.setHorizontalHeaderLabels(["聚类ID", "评论数量", "关键词"])
        self.cluster_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        cluster_layout.addWidget(self.cluster_table)
        
        cluster_group.setLayout(cluster_layout)
        layout.addWidget(cluster_group)
        
        self.setLayout(layout)
    
    def update_stats(self, comments: List[Dict]):
        """更新统计信息"""
        if not comments:
            return
            
        total = len(comments)
        positive = len([c for c in comments if c.get("sentiment") == "positive"])
        negative = len([c for c in comments if c.get("sentiment") == "negative"])
        neutral = len([c for c in comments if c.get("sentiment") == "neutral"])
        
        self.total_comments_label.setText(f"总评论数: {total}")
        self.positive_comments_label.setText(f"正面评论: {positive}")
        self.negative_comments_label.setText(f"负面评论: {negative}")
        self.neutral_comments_label.setText(f"中性评论: {neutral}")
        
        # 更新情感分布表
        self.sentiment_table.setRowCount(3)
        sentiments = [
            ("正面", positive, positive/total*100 if total > 0 else 0),
            ("负面", negative, negative/total*100 if total > 0 else 0),
            ("中性", neutral, neutral/total*100 if total > 0 else 0)
        ]
        
        for i, (sentiment, count, percentage) in enumerate(sentiments):
            self.sentiment_table.setItem(i, 0, QTableWidgetItem(sentiment))
            self.sentiment_table.setItem(i, 1, QTableWidgetItem(str(count)))
            self.sentiment_table.setItem(i, 2, QTableWidgetItem(f"{percentage:.1f}%"))
    
    def update_clusters(self, cluster_data: Dict):
        """更新聚类信息"""
        if not cluster_data:
            return
            
        cluster_keywords = cluster_data.get("cluster_keywords", {})
        cluster_counts = {}
        
        for cluster_id in cluster_keywords.keys():
            cluster_counts[cluster_id] = 0
        
        # 统计每个聚类的评论数
        comments = self.parent().db_manager.get_comments(limit=1000)
        for comment in comments:
            cluster_id = comment.get("cluster_id")
            if cluster_id is not None and cluster_id in cluster_counts:
                cluster_counts[cluster_id] += 1
        
        # 更新聚类表
        self.cluster_table.setRowCount(len(cluster_keywords))
        
        for i, (cluster_id, keywords) in enumerate(cluster_keywords.items()):
            self.cluster_table.setItem(i, 0, QTableWidgetItem(str(cluster_id)))
            self.cluster_table.setItem(i, 1, QTableWidgetItem(str(cluster_counts.get(cluster_id, 0))))
            self.cluster_table.setItem(i, 2, QTableWidgetItem(", ".join(keywords)))


class SmartCommentSystem(QMainWindow):
    """智能评论系统主窗口"""
    
    def __init__(self):
        super().__init__()
        self.db_manager = DatabaseManager()
        self.comments = []
        self.init_ui()
        self.load_comments()
    
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("智能评论分析系统")
        self.setGeometry(100, 100, 1200, 800)
        
        # 创建中央部件和主布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # 创建标签页
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)
        
        # 评论管理标签页
        self.comments_tab = self.create_comments_tab()
        self.tabs.addTab(self.comments_tab, "评论管理")
        
        # 分析仪表板标签页
        self.analysis_tab = self.create_analysis_tab()
        self.tabs.addTab(self.analysis_tab, "分析仪表板")
        
        # 设置标签页
        self.settings_tab = self.create_settings_tab()
        self.tabs.addTab(self.settings_tab, "设置")
    
    def create_comments_tab(self) -> QWidget:
        """创建评论管理标签页"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        
        # 左侧：评论列表
        left_panel = QVBoxLayout()
        
        # 筛选控件
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("筛选:"))
        
        self.sentiment_filter = QComboBox()
        self.sentiment_filter.addItem("全部情感", None)
        self.sentiment_filter.addItem("正面", "positive")
        self.sentiment_filter.addItem("负面", "negative")
        self.sentiment_filter.addItem("中性", "neutral")
        self.sentiment_filter.currentIndexChanged.connect(self.load_comments)
        filter_layout.addWidget(self.sentiment_filter)
        
        self.limit_spin = QSpinBox()
        self.limit_spin.setRange(10, 1000)
        self.limit_spin.setValue(100)
        self.limit_spin.valueChanged.connect(self.load_comments)
        filter_layout.addWidget(QLabel("显示数量:"))
        filter_layout.addWidget(self.limit_spin)
        
        filter_layout.addStretch()
        
        # 操作按钮
        self.analyze_btn = QPushButton("分析评论")
        self.analyze_btn.clicked.connect(self.analyze_comments)
        filter_layout.addWidget(self.analyze_btn)
        
        self.export_btn = QPushButton("导出数据")
        self.export_btn.clicked.connect(self.export_data)
        filter_layout.addWidget(self.export_btn)
        
        left_panel.addLayout(filter_layout)
        
        # 评论列表
        self.comments_list = QListWidget()
        self.comments_list.itemClicked.connect(self.show_comment_details)
        left_panel.addWidget(self.comments_list)
        
        # 右侧：评论详情和输入
        right_panel = QVBoxLayout()
        
        # 评论详情
        detail_group = QGroupBox("评论详情")
        detail_layout = QVBoxLayout()
        
        self.comment_detail = QTextEdit()
        self.comment_detail.setReadOnly(True)
        detail_layout.addWidget(self.comment_detail)
        
        # 回复区域
        reply_layout = QHBoxLayout()
        self.reply_input = QLineEdit()
        self.reply_input.setPlaceholderText("输入回复...")
        reply_layout.addWidget(self.reply_input)
        
        self.reply_btn = QPushButton("回复")
        self.reply_btn.clicked.connect(self.add_reply)
        reply_layout.addWidget(self.reply_btn)
        
        detail_layout.addLayout(reply_layout)
        detail_group.setLayout(detail_layout)
        right_panel.addWidget(detail_group)
        
        # 添加评论区域
        self.comment_input = CommentInputWidget()
        right_panel.addWidget(self.comment_input)
        
        # 设置左右面板比例
        splitter = QSplitter(Qt.Horizontal)
        
        left_widget = QWidget()
        left_widget.setLayout(left_panel)
        splitter.addWidget(left_widget)
        
        right_widget = QWidget()
        right_widget.setLayout(right_panel)
        splitter.addWidget(right_widget)
        
        splitter.setSizes([600, 400])
        
        layout.addWidget(splitter)
        
        return widget
    
    def create_analysis_tab(self) -> QWidget:
        """创建分析仪表板标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        self.dashboard = AnalysisDashboard(self)
        layout.addWidget(self.dashboard)
        
        return widget
    
    def create_settings_tab(self) -> QWidget:
        """创建设置标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 数据库设置组
        db_group = QGroupBox("数据库设置")
        db_layout = QFormLayout()
        
        self.db_path_label = QLabel("comments.db")
        db_layout.addRow("数据库路径:", self.db_path_label)
        
        self.change_db_btn = QPushButton("更改数据库")
        self.change_db_btn.clicked.connect(self.change_database)
        db_layout.addRow(self.change_db_btn)
        
        db_group.setLayout(db_layout)
        layout.addWidget(db_group)
        
        # 分析设置组
        analysis_group = QGroupBox("分析设置")
        analysis_layout = QFormLayout()
        
        self.auto_analyze_check = QCheckBox("添加评论后自动分析")
        self.auto_analyze_check.setChecked(True)
        analysis_layout.addRow(self.auto_analyze_check)
        
        self.cluster_count_spin = QSpinBox()
        self.cluster_count_spin.setRange(2, 10)
        self.cluster_count_spin.setValue(5)
        analysis_layout.addRow("聚类数量:", self.cluster_count_spin)
        
        analysis_group.setLayout(analysis_layout)
        layout.addWidget(analysis_group)
        
        layout.addStretch()
        
        return widget
    
    def load_comments(self):
        """加载评论列表"""
        sentiment_filter = self.sentiment_filter.currentData()
        limit = self.limit_spin.value()
        
        self.comments = self.db_manager.get_comments(limit, sentiment_filter)
        self.comments_list.clear()
        
        for comment in self.comments:
            item = QListWidgetItem()
            widget = CommentWidget(comment)
            item.setSizeHint(widget.sizeHint())
            self.comments_list.addItem(item)
            self.comments_list.setItemWidget(item, widget)
        
        # 更新仪表板
        self.dashboard.update_stats(self.comments)
    
    def show_comment_details(self, item):
        """显示评论详情"""
        index = self.comments_list.row(item)
        if index < 0 or index >= len(self.comments):
            return
        
        comment = self.comments[index]
        
        # 构建详情文本
        detail_text = f"""
评论内容:
{comment['content']}

情感分析:
- 情感: {comment.get('sentiment', '未知')}
- 极性: {comment.get('polarity', 0):.3f}
- 主观性: {comment.get('subjectivity', 0):.3f}

元数据:
- 时间: {comment.get('timestamp', '未知')}
- 来源: {comment.get('source', '未知')}
- 评分: {comment.get('rating', '无')}
- 聚类ID: {comment.get('cluster_id', '未聚类')}

回复:
"""
        
        # 添加回复
        replies = self.db_manager.get_replies(comment['id'])
        for i, reply in enumerate(replies, 1):
            detail_text += f"\n{i}. {reply['content']} ({reply['timestamp']})"
        
        if not replies:
            detail_text += "\n暂无回复"
        
        self.comment_detail.setPlainText(detail_text)
        self.current_comment_id = comment['id']
    
    def add_comment_signal(self, content: str, source: str, rating: int):
        """添加评论信号处理"""
        comment_id = self.db_manager.add_comment(content, source, rating)
        
        # 重新加载评论
        self.load_comments()
        
        # 自动分析
        if self.auto_analyze_check.isChecked():
            QTimer.singleShot(100, self.analyze_comments)
    
    def add_reply(self):
        """添加回复"""
        if not hasattr(self, 'current_comment_id'):
            QMessageBox.warning(self, "错误", "请先选择一条评论")
            return
        
        reply_content = self.reply_input.text().strip()
        if not reply_content:
            QMessageBox.warning(self, "错误", "回复内容不能为空")
            return
        
        self.db_manager.add_reply(self.current_comment_id, reply_content)
        self.reply_input.clear()
        
        # 刷新详情显示
        current_item = self.comments_list.currentItem()
        if current_item:
            self.show_comment_details(current_item)
    
    def analyze_comments(self):
        """分析评论"""
        if not self.comments:
            QMessageBox.information(self, "提示", "没有可分析的评论")
            return
        
        # 创建进度对话框
        self.progress_dialog = QMessageBox(self)
        self.progress_dialog.setWindowTitle("分析中")
        self.progress_dialog.setText("正在分析评论，请稍候...")
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_dialog.layout().addWidget(self.progress_bar, 1, 1)
        self.progress_dialog.show()
        
        # 准备分析数据
        comment_texts = [c['content'] for c in self.comments]
        comment_ids = [c['id'] for c in self.comments]
        
        # 启动分析线程
        self.analysis_worker = AnalysisWorker(comment_texts, comment_ids)
        self.analysis_worker.progress_updated.connect(self.update_progress)
        self.analysis_worker.analysis_completed.connect(self.analysis_finished)
        self.analysis_worker.start()
    
    def update_progress(self, value):
        """更新进度条"""
        self.progress_bar.setValue(value)
    
    def analysis_finished(self, result):
        """分析完成"""
        self.progress_dialog.accept()
        
        # 更新数据库中的聚类信息
        self.db_manager.update_cluster_ids(result['comment_ids'], result['cluster_labels'])
        
        # 重新加载评论
        self.load_comments()
        
        # 更新仪表板的聚类信息
        self.dashboard.update_clusters(result)
        
        QMessageBox.information(self, "完成", "评论分析完成！")
    
    def export_data(self):
        """导出数据"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出数据", "comments_export.csv", "CSV Files (*.csv)"
        )
        
        if file_path:
            comments = self.db_manager.get_comments(limit=10000)  # 获取所有评论
            df = pd.DataFrame(comments)
            df.to_csv(file_path, index=False, encoding='utf-8-sig')
            
            QMessageBox.information(self, "成功", f"数据已导出到: {file_path}")
    
    def change_database(self):
        """更改数据库"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择数据库文件", "", "SQLite Database (*.db)"
        )
        
        if file_path:
            self.db_manager = DatabaseManager(file_path)
            self.db_path_label.setText(file_path)
            self.load_comments()
            
            QMessageBox.information(self, "成功", f"已切换到数据库: {file_path}")


def main():
    """主函数"""
    app = QApplication(sys.argv)
    
    # 设置应用样式
    app.setStyle('Fusion')
    
    # 创建并显示主窗口
    window = SmartCommentSystem()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()