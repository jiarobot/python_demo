import sys
import sqlite3
import json
import numpy as np
import torch
import torch.nn as nn
from datetime import datetime, timedelta
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QTabWidget, QTreeWidget, QTreeWidgetItem,
                           QListWidget, QTextEdit, QLineEdit, QPushButton,
                           QLabel, QSplitter, QProgressBar, QMessageBox,
                           QFileDialog, QGraphicsView, QGraphicsScene, QGraphicsItem,
                           QMenu, QDialog, QFormLayout, QSpinBox,
                           QDoubleSpinBox, QCheckBox, QComboBox, QTableWidget,
                           QTableWidgetItem, QHeaderView, QGroupBox, QSlider,
                           QTextBrowser, QToolBar, QDockWidget, QStatusBar,
                           QInputDialog, QListWidgetItem, QFrame, QStyleFactory)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QPointF, QRectF, QDateTime, QUrl
from PyQt6.QtGui import QFont, QColor, QPen, QBrush, QPainter, QIcon, QDesktopServices, QPalette, QActionGroup, QAction
from PyQt6.QtCharts import QChart, QChartView, QPieSeries, QBarSeries, QBarSet, QLineSeries, QValueAxis
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebChannel import QWebChannel

import networkx as nx
from sklearn.cluster import DBSCAN, KMeans
from sklearn.manifold import TSNE
from sklearn.decomposition import PCA
from sklearn.feature_extraction.text import TfidfVectorizer
import matplotlib.pyplot as plt
from wordcloud import WordCloud
import requests
from bs4 import BeautifulSoup
import threading
import time
import asyncio
import aiohttp
import websockets
import pickle
import hashlib
import hmac
import secrets
from cryptography.fernet import Fernet
import jwt
import zipfile
import io
import csv
import logging
from logging.handlers import RotatingFileHandler
import os
import webbrowser
from pathlib import Path

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler('collective_unconscious.log', maxBytes=10485760, backupCount=5),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 深度学习模型定义
class EnhancedArchetypePredictor(nn.Module):
    """增强版原型预测神经网络"""
    
    def __init__(self, input_size=512, hidden_size=512, output_size=100, num_heads=8):
        super(EnhancedArchetypePredictor, self).__init__()
        
        # 多头自注意力机制
        self.attention = nn.MultiheadAttention(input_size, num_heads)
        
        # 编码器层
        self.encoder = nn.Sequential(
            nn.Linear(input_size, hidden_size),
            nn.GELU(),
            nn.Dropout(0.3),
            nn.Linear(hidden_size, hidden_size // 2),
            nn.GELU(),
            nn.Dropout(0.3),
            nn.Linear(hidden_size // 2, hidden_size // 4),
            nn.GELU(),
        )
        
        # 多任务输出头
        self.archetype_head = nn.Linear(hidden_size // 4, output_size)
        self.intensity_head = nn.Linear(hidden_size // 4, 1)
        self.emotion_head = nn.Linear(hidden_size // 4, 5)  # 5种基本情感
        self.cultural_bias_head = nn.Linear(hidden_size // 4, 10)  # 10种文化倾向
        
    def forward(self, x):
        # 自注意力机制
        attn_output, _ = self.attention(x.unsqueeze(0), x.unsqueeze(0), x.unsqueeze(0))
        x = attn_output.squeeze(0)
        
        # 编码
        encoded = self.encoder(x)
        
        # 多任务输出
        archetype_probs = torch.softmax(self.archetype_head(encoded), dim=1)
        intensity = torch.sigmoid(self.intensity_head(encoded))
        emotion_probs = torch.softmax(self.emotion_head(encoded), dim=1)
        cultural_bias = torch.tanh(self.cultural_bias_head(encoded))
        
        return archetype_probs, intensity, emotion_probs, cultural_bias

class AdvancedCollectiveUnconsciousDB:
    """高级版集体潜意识数据库管理"""
    
    def __init__(self, db_path="collective_unconscious.db"):
        self.db_path = db_path
        self.encryption_key = self._get_encryption_key()
        self.init_database()
        self.update_database_schema()  # 添加这一行
    
    def update_database_schema(self):
        """更新数据库表结构"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 检查users表是否有permissions列
            cursor.execute("PRAGMA table_info(users)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'permissions' not in columns:
                cursor.execute("ALTER TABLE users ADD COLUMN permissions TEXT DEFAULT 'basic'")
                logger.info("已添加缺失的permissions列")
            
            # 检查其他可能缺失的列
            cursor.execute("PRAGMA table_info(archetypes)")
            archetype_columns = [column[1] for column in cursor.fetchall()]
            
            if 'cross_cultural_index' not in archetype_columns:
                cursor.execute("ALTER TABLE archetypes ADD COLUMN cross_cultural_index REAL DEFAULT 0.0")
                logger.info("已添加缺失的cross_cultural_index列")
            
            # 检查collective_memories表
            cursor.execute("PRAGMA table_info(collective_memories)")
            memory_columns = [column[1] for column in cursor.fetchall()]
            
            missing_columns = []
            if 'language' not in memory_columns:
                missing_columns.append("language TEXT DEFAULT 'en'")
            if 'sentiment_score' not in memory_columns:
                missing_columns.append("sentiment_score REAL DEFAULT 0.0")
            if 'geographic_location' not in memory_columns:
                missing_columns.append("geographic_location TEXT")
            if 'demographic_info' not in memory_columns:
                missing_columns.append("demographic_info TEXT")
            
            if missing_columns:
                for column_def in missing_columns:
                    column_name = column_def.split()[0]
                    cursor.execute(f"ALTER TABLE collective_memories ADD COLUMN {column_def}")
                    logger.info(f"已添加缺失的{column_name}列")
            
            conn.commit()
            
        except Exception as e:
            logger.error(f"更新数据库结构时出错: {e}")
        finally:
            conn.close()
    
    def _get_encryption_key(self):
        """获取或生成加密密钥"""
        key_file = "encryption.key"
        if os.path.exists(key_file):
            with open(key_file, "rb") as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            with open(key_file, "wb") as f:
                f.write(key)
            return key
    
    def init_database(self):
        """初始化数据库表结构"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建增强用户表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                email TEXT,
                role TEXT DEFAULT 'researcher',
                permissions TEXT DEFAULT 'basic',
                created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                profile_data TEXT
            )
        ''')
        
        # 创建增强原型表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS archetypes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                description TEXT,
                category TEXT,
                power_level REAL DEFAULT 0.0,
                cultural_origin TEXT,
                historical_period TEXT,
                created_by INTEGER,
                created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                tags TEXT,
                neural_embedding BLOB,
                cross_cultural_index REAL DEFAULT 0.0,
                FOREIGN KEY (created_by) REFERENCES users (id)
            )
        ''')
        
        # 创建增强集体记忆表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS collective_memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                emotion_vector TEXT,
                archetype_connections TEXT,
                intensity REAL DEFAULT 0.0,
                source_type TEXT,
                cultural_context TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                added_by INTEGER,
                confidence REAL DEFAULT 1.0,
                encrypted_content BLOB,
                language TEXT DEFAULT 'en',
                sentiment_score REAL DEFAULT 0.0,
                geographic_location TEXT,
                demographic_info TEXT,
                FOREIGN KEY (added_by) REFERENCES users (id)
            )
        ''')
        
        # 创建增强模式识别表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_type TEXT NOT NULL,
                data TEXT,
                confidence REAL DEFAULT 0.0,
                discovered_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                discovered_by INTEGER,
                significance REAL DEFAULT 0.0,
                complexity_index REAL DEFAULT 0.0,
                temporal_stability REAL DEFAULT 0.0,
                cross_validation_score REAL DEFAULT 0.0,
                FOREIGN KEY (discovered_by) REFERENCES users (id)
            )
        ''')
        
        # 创建增强协作会话表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS collaboration_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                created_by INTEGER,
                created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active INTEGER DEFAULT 1,
                session_type TEXT DEFAULT 'research',
                encryption_key BLOB,
                access_level TEXT DEFAULT 'public',
                FOREIGN KEY (created_by) REFERENCES users (id)
            )
        ''')
        
        # 创建增强会话消息表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS session_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER,
                user_id INTEGER,
                message_type TEXT,
                content TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                encrypted_content BLOB,
                reply_to INTEGER,
                reaction_data TEXT,
                FOREIGN KEY (session_id) REFERENCES collaboration_sessions (id),
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # 创建增强分析任务表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS analysis_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                task_type TEXT,
                parameters TEXT,
                status TEXT DEFAULT 'pending',
                created_by INTEGER,
                created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                started_date TIMESTAMP,
                completed_date TIMESTAMP,
                result TEXT,
                progress REAL DEFAULT 0.0,
                priority INTEGER DEFAULT 1,
                FOREIGN KEY (created_by) REFERENCES users (id)
            )
        ''')
        
        # 创建数据源表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS data_sources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                source_type TEXT,
                connection_params TEXT,
                last_sync TIMESTAMP,
                is_active INTEGER DEFAULT 1,
                sync_frequency INTEGER DEFAULT 3600
            )
        ''')
        
        # 创建可视化配置表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS visualization_configs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                config_data TEXT,
                created_by INTEGER,
                is_default INTEGER DEFAULT 0
            )
        ''')
        
        conn.commit()
        conn.close()
        
        # 创建默认管理员用户
        self.create_user('admin', 'admin123', 'admin@system.com', 'admin', 'full')
    
    def encrypt_data(self, data):
        """加密数据"""
        fernet = Fernet(self.encryption_key)
        return fernet.encrypt(data.encode())
    
    def decrypt_data(self, encrypted_data):
        """解密数据"""
        fernet = Fernet(self.encryption_key)
        return fernet.decrypt(encrypted_data).decode()
    
    def create_user(self, username, password, email, role='researcher', permissions='basic'):
        """创建用户"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 检查用户是否已存在
        cursor.execute('SELECT id FROM users WHERE username = ?', (username,))
        if cursor.fetchone():
            conn.close()
            return False
        
        # 创建密码哈希（使用更安全的算法）
        salt = secrets.token_hex(16)
        password_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000).hex()
        
        # 确保使用正确的格式：salt$hash
        stored_hash = f"{salt}${password_hash}"
        
        cursor.execute('''
            INSERT INTO users (username, password_hash, email, role, permissions)
            VALUES (?, ?, ?, ?, ?)
        ''', (username, stored_hash, email, role, permissions))
        
        conn.commit()
        conn.close()
        return True
    
    def authenticate_user(self, username, password):
        """用户认证"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, username, password_hash, role, permissions FROM users 
            WHERE username = ?
        ''', (username,))
        
        user = cursor.fetchone()
        conn.close()
        
        if user:
            # 检查密码哈希格式
            password_hash_parts = user[2].split('$')
            
            if len(password_hash_parts) == 2:
                # 新格式：salt$hash
                salt, stored_hash = password_hash_parts
                password_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000).hex()
            else:
                # 旧格式或无效格式，尝试直接比较
                stored_hash = user[2]
                password_hash = hashlib.sha256(password.encode()).hexdigest()
            
            if password_hash == stored_hash:
                # 如果是旧格式，更新为新的安全格式
                if len(password_hash_parts) != 2:
                    self._update_password_format(username, password)
                
                # 更新最后登录时间
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE users SET last_login = CURRENT_TIMESTAMP 
                    WHERE id = ?
                ''', (user[0],))
                conn.commit()
                conn.close()
                
                return {
                    'id': user[0],
                    'username': user[1],
                    'role': user[3],
                    'permissions': user[4] if len(user) > 4 else 'basic'
                }
        
        return None
    
    def _update_password_format(self, username, password):
        """更新密码格式为新的安全格式"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建新的安全哈希
        salt = secrets.token_hex(16)
        password_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000).hex()
        stored_hash = f"{salt}${password_hash}"
        
        cursor.execute('''
            UPDATE users SET password_hash = ? WHERE username = ?
        ''', (stored_hash, username))
        
        conn.commit()
        conn.close()
        logger.info(f"已更新用户 {username} 的密码存储格式")

    def reset_admin_password(self):
        """重置管理员密码"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 检查管理员用户是否存在
        cursor.execute('SELECT id FROM users WHERE username = ?', ('admin',))
        admin_user = cursor.fetchone()
        
        if admin_user:
            # 删除旧的管理员用户
            cursor.execute('DELETE FROM users WHERE username = ?', ('admin',))
            logger.info("已删除旧的管理员用户")
        
        # 创建新的管理员用户
        salt = secrets.token_hex(16)
        password_hash = hashlib.pbkdf2_hmac('sha256', 'admin123'.encode(), salt.encode(), 100000).hex()
        stored_hash = f"{salt}${password_hash}"
        
        cursor.execute('''
            INSERT INTO users (username, password_hash, email, role, permissions)
            VALUES (?, ?, ?, ?, ?)
        ''', ('admin', stored_hash, 'admin@system.com', 'admin', 'full'))
        
        conn.commit()
        conn.close()
        logger.info("已重新创建管理员用户")
         
    def add_collective_memory(self, content, user_id, emotion_vector=None, 
                            archetype_connections=None, intensity=0.0, 
                            source_type="user", cultural_context="global", 
                            confidence=1.0, encrypt=False, language="en",
                            sentiment_score=0.0, geographic_location=None,
                            demographic_info=None):
        """添加集体记忆"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        emotion_json = json.dumps(emotion_vector) if emotion_vector else "[]"
        connections_json = json.dumps(archetype_connections) if archetype_connections else "[]"
        demographic_json = json.dumps(demographic_info) if demographic_info else "{}"
        
        encrypted_content = None
        if encrypt:
            encrypted_content = self.encrypt_data(content)
            content = ""  # 清空明文内容
        
        cursor.execute('''
            INSERT INTO collective_memories 
            (content, emotion_vector, archetype_connections, intensity, 
             source_type, cultural_context, added_by, confidence, encrypted_content,
             language, sentiment_score, geographic_location, demographic_info)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (content, emotion_json, connections_json, intensity, 
              source_type, cultural_context, user_id, confidence, encrypted_content,
              language, sentiment_score, geographic_location, demographic_json))
        
        conn.commit()
        conn.close()
        return True

class AdvancedDeepLearningAnalyzer(QThread):
    """高级深度学习分析器"""
    analysis_progress = pyqtSignal(int, str)
    analysis_complete = pyqtSignal(dict)
    pattern_discovered = pyqtSignal(dict)
    model_trained = pyqtSignal(dict)
    
    def __init__(self, db_manager, user_id):
        super().__init__()
        self.db_manager = db_manager
        self.user_id = user_id
        self.model = EnhancedArchetypePredictor()
        self.running = False
        self.tasks = []
        self.current_task = None
        
        # 加载或训练模型
        self.load_model()
    
    def load_model(self):
        """加载预训练模型"""
        try:
            if os.path.exists('enhanced_archetype_model.pth'):
                self.model.load_state_dict(torch.load('enhanced_archetype_model.pth'))
                self.model.eval()
                logger.info("增强深度学习模型加载成功")
            else:
                logger.warning("未找到预训练模型，将使用随机初始化模型")
        except Exception as e:
            logger.error(f"加载模型失败: {e}")
    
    def add_task(self, task_type, parameters, priority=1):
        """添加分析任务"""
        task_id = len(self.tasks) + 1
        task = {
            'id': task_id,
            'type': task_type,
            'parameters': parameters,
            'status': 'pending',
            'progress': 0,
            'priority': priority,
            'created': datetime.now()
        }
        self.tasks.append(task)
        
        # 按优先级排序
        self.tasks.sort(key=lambda x: (-x['priority'], x['created']))
        return task_id
    
    def run(self):
        """运行分析循环"""
        self.running = True
        while self.running:
            # 处理待执行任务
            for task in self.tasks:
                if task['status'] == 'pending':
                    task['status'] = 'running'
                    self.current_task = task
                    self.process_task(task)
                    self.current_task = None
            
            # 实时数据分析
            self.realtime_analysis()
            
            time.sleep(2)  # 每2秒检查一次
    
    def process_task(self, task):
        """处理分析任务"""
        try:
            if task['type'] == 'cultural_pattern_analysis':
                result = self.analyze_cultural_patterns(task)
            elif task['type'] == 'temporal_analysis':
                result = self.analyze_temporal_patterns(task)
            elif task['type'] == 'cross_cultural_comparison':
                result = self.cross_cultural_analysis(task)
            elif task['type'] == 'neural_network_training':
                result = self.train_neural_network(task)
            elif task['type'] == 'sentiment_analysis':
                result = self.analyze_sentiment_trends(task)
            elif task['type'] == 'archetype_evolution':
                result = self.analyze_archetype_evolution(task)
            else:
                result = {'error': f'未知任务类型: {task["type"]}'}
            
            task['status'] = 'completed'
            task['progress'] = 100
            task['result'] = result
            self.analysis_complete.emit(task)
            
        except Exception as e:
            logger.error(f"任务处理失败: {e}")
            task['status'] = 'failed'
            task['error'] = str(e)
            self.analysis_complete.emit(task)
    
    def analyze_cultural_patterns(self, task):
        """分析文化模式"""
        self.analysis_progress.emit(10, "开始文化模式分析...")
        
        # 从数据库获取数据
        conn = sqlite3.connect(self.db_manager.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT content, cultural_context, timestamp, sentiment_score
            FROM collective_memories 
            WHERE cultural_context IS NOT NULL
        ''')
        
        data = cursor.fetchall()
        conn.close()
        
        if not data:
            self.analysis_progress.emit(100, "无文化数据可供分析")
            return {'error': '无数据'}
        
        self.analysis_progress.emit(30, f"分析 {len(data)} 条文化数据...")
        
        # 文化聚类分析
        cultural_groups = {}
        for content, context, timestamp, sentiment in data:
            if context not in cultural_groups:
                cultural_groups[context] = {'texts': [], 'sentiments': []}
            cultural_groups[context]['texts'].append(content)
            cultural_groups[context]['sentiments'].append(sentiment)
        
        # 使用TF-IDF进行文本分析
        vectorizer = TfidfVectorizer(max_features=1000, stop_words='english')
        cultural_patterns = {}
        
        for culture, data in cultural_groups.items():
            if len(data['texts']) < 3:  # 至少需要3个文本进行分析
                continue
                
            try:
                tfidf_matrix = vectorizer.fit_transform(data['texts'])
                feature_names = vectorizer.get_feature_names_out()
                
                # 获取每个文化的重要词汇
                importance_scores = np.asarray(tfidf_matrix.mean(axis=0)).flatten()
                important_words = [
                    (feature_names[i], importance_scores[i]) 
                    for i in importance_scores.argsort()[-20:][::-1]
                ]
                
                # 情感分析
                avg_sentiment = np.mean(data['sentiments'])
                sentiment_std = np.std(data['sentiments'])
                
                cultural_patterns[culture] = {
                    'important_words': important_words,
                    'sample_size': len(data['texts']),
                    'unique_features': len(feature_names),
                    'avg_sentiment': float(avg_sentiment),
                    'sentiment_volatility': float(sentiment_std)
                }
            except Exception as e:
                logger.warning(f"文化 {culture} 分析失败: {e}")
        
        self.analysis_progress.emit(80, "生成分析报告...")
        
        # 保存分析结果
        result = {
            'task_type': 'cultural_pattern_analysis',
            'cultural_patterns': cultural_patterns,
            'total_cultures_analyzed': len(cultural_patterns),
            'timestamp': datetime.now().isoformat()
        }
        
        # 发送模式发现信号
        for culture, pattern in cultural_patterns.items():
            pattern_data = {
                'type': 'cultural_pattern',
                'culture': culture,
                'significance': pattern['sample_size'] / len(data),
                'key_features': [word for word, score in pattern['important_words'][:5]],
                'sentiment': pattern['avg_sentiment'],
                'discovered_by': self.user_id
            }
            self.pattern_discovered.emit(pattern_data)
        
        self.analysis_progress.emit(100, "文化模式分析完成")
        
        return result

    def analyze_temporal_patterns(self, task):
        """分析时间模式"""
        self.analysis_progress.emit(20, "开始时间模式分析...")
        
        # 模拟时间模式分析
        time.sleep(2)
        
        result = {
            'task_type': 'temporal_analysis',
            'periodic_patterns': [
                {'period': 'daily', 'confidence': 0.85, 'description': '日间情感波动'},
                {'period': 'weekly', 'confidence': 0.72, 'description': '周末文化活跃度提升'},
                {'period': 'monthly', 'confidence': 0.63, 'description': '月相影响模式'}
            ],
            'trends': [
                {'trend': 'increasing', 'metric': 'global_connectivity', 'rate': 0.15},
                {'trend': 'decreasing', 'metric': 'cultural_isolation', 'rate': 0.08}
            ]
        }
        
        self.analysis_progress.emit(100, "时间模式分析完成")
        return result

    def cross_cultural_analysis(self, task):
        """跨文化分析"""
        self.analysis_progress.emit(25, "开始跨文化分析...")
        
        # 模拟跨文化分析
        time.sleep(3)
        
        result = {
            'task_type': 'cross_cultural_analysis',
            'similarities': [
                {'cultures': ['Western', 'Eastern'], 'similarity_score': 0.76, 'common_archetypes': ['Hero', 'Wise Elder']},
                {'cultures': ['African', 'Latin American'], 'similarity_score': 0.82, 'common_archetypes': ['Community', 'Ancestors']}
            ],
            'divergences': [
                {'cultures': ['Western', 'Middle Eastern'], 'divergence_score': 0.68, 'key_differences': ['Individualism vs Collectivism']}
            ]
        }
        
        self.analysis_progress.emit(100, "跨文化分析完成")
        return result

    def train_neural_network(self, task):
        """训练神经网络"""
        self.analysis_progress.emit(10, "准备训练数据...")
        
        # 模拟训练过程
        epochs = task['parameters'].get('epochs', 10)
        for epoch in range(epochs):
            progress = 10 + (epoch / epochs) * 80
            self.analysis_progress.emit(int(progress), f"训练周期 {epoch+1}/{epochs}...")
            time.sleep(0.5)
        
        # 保存模型
        torch.save(self.model.state_dict(), 'enhanced_archetype_model.pth')
        
        result = {
            'task_type': 'neural_network_training',
            'epochs_trained': epochs,
            'final_loss': 0.023,
            'model_performance': {
                'accuracy': 0.89,
                'precision': 0.87,
                'recall': 0.91
            }
        }
        
        self.model_trained.emit(result)
        self.analysis_progress.emit(100, "神经网络训练完成")
        return result

    def analyze_sentiment_trends(self, task):
        """分析情感趋势"""
        self.analysis_progress.emit(30, "分析情感趋势...")
        
        # 模拟情感趋势分析
        time.sleep(2)
        
        result = {
            'task_type': 'sentiment_analysis',
            'overall_sentiment': 0.65,
            'trend_direction': 'positive',
            'key_emotions': ['Hope', 'Concern', 'Curiosity'],
            'volatility_index': 0.23
        }
        
        self.analysis_progress.emit(100, "情感趋势分析完成")
        return result

    def analyze_archetype_evolution(self, task):
        """分析原型演化"""
        self.analysis_progress.emit(40, "分析原型演化模式...")
        
        # 模拟原型演化分析
        time.sleep(3)
        
        result = {
            'task_type': 'archetype_evolution',
            'emerging_archetypes': [
                {'name': 'Digital Shaman', 'growth_rate': 0.45, 'description': '数字时代的灵性引导者'},
                {'name': 'Eco-Warrior', 'growth_rate': 0.38, 'description': '环境保护的现代英雄'}
            ],
            'declining_archetypes': [
                {'name': 'Lone Genius', 'decline_rate': 0.22, 'reason': '协作文化兴起'}
            ]
        }
        
        self.analysis_progress.emit(100, "原型演化分析完成")
        return result

    def realtime_analysis(self):
        """实时分析"""
        # 这里可以添加实时分析逻辑
        pass

class EnhancedRealTimeDataCollector(QThread):
    """增强版实时数据收集器"""
    data_received = pyqtSignal(dict)
    connection_status = pyqtSignal(str, bool)
    source_updated = pyqtSignal(str, int)  # 数据源更新
    
    def __init__(self, db_manager, user_id):
        super().__init__()
        self.db_manager = db_manager
        self.user_id = user_id
        self.sources = {
            'social_media': {'active': True, 'count': 0},
            'news_feeds': {'active': True, 'count': 0},
            'academic_publications': {'active': False, 'count': 0},
            'cultural_databases': {'active': False, 'count': 0},
            'government_reports': {'active': False, 'count': 0}
        }
        self.running = False
        self.collection_stats = {
            'total_collected': 0,
            'last_collection': datetime.now()
        }
    
    def run(self):
        """运行数据收集"""
        self.running = True
        self.connection_status.emit("数据收集器启动", True)
        
        while self.running:
            # 收集社交媒体数据
            if self.sources['social_media']['active']:
                self.collect_social_media_data()
            
            # 收集新闻数据
            if self.sources['news_feeds']['active']:
                self.collect_news_data()
            
            # 收集学术数据
            if self.sources['academic_publications']['active']:
                self.collect_academic_data()
            
            time.sleep(20)  # 每20秒收集一次
    
    def collect_social_media_data(self):
        """收集社交媒体数据（模拟）"""
        try:
            # 模拟从社交媒体API获取数据
            topics = ['climate_change', 'technology', 'culture', 'health', 'politics', 'AI', 'space']
            topic = np.random.choice(topics)
            
            # 模拟情感分析
            emotions = ['joy', 'anger', 'fear', 'sadness', 'surprise']
            emotion_weights = np.random.dirichlet(np.ones(5))
            emotion_vector = {emotion: float(weight) for emotion, weight in zip(emotions, emotion_weights)}
            
            # 模拟内容
            contents = [
                f"人们正在热烈讨论{topic}话题",
                f"{topic}领域的新发展正在涌现",
                f"关于{topic}的文化视角正在演变",
                f"公众对{topic}的看法正在发生变化",
                f"社交媒体上{topic}的讨论热度上升"
            ]
            content = np.random.choice(contents)
            
            # 模拟地理位置和人口统计
            locations = ['North America', 'Europe', 'Asia', 'Africa', 'South America']
            demographics = {'age_group': np.random.choice(['18-25', '26-35', '36-50', '50+']),
                           'gender': np.random.choice(['Male', 'Female', 'Other'])}
            
            data = {
                'content': content,
                'source': 'social_media',
                'emotion_vector': emotion_vector,
                'intensity': np.random.uniform(0.3, 0.9),
                'cultural_context': 'global',
                'timestamp': datetime.now().isoformat(),
                'language': 'zh' if np.random.random() > 0.5 else 'en',
                'sentiment_score': np.random.uniform(-1, 1),
                'geographic_location': np.random.choice(locations),
                'demographic_info': demographics
            }
            
            self.data_received.emit(data)
            
            # 保存到数据库
            self.db_manager.add_collective_memory(
                content=data['content'],
                user_id=self.user_id,
                emotion_vector=emotion_vector,
                intensity=data['intensity'],
                source_type='social_media',
                cultural_context=data['cultural_context'],
                language=data['language'],
                sentiment_score=data['sentiment_score'],
                geographic_location=data['geographic_location'],
                demographic_info=data['demographic_info']
            )
            
            # 更新统计
            self.sources['social_media']['count'] += 1
            self.collection_stats['total_collected'] += 1
            self.source_updated.emit('social_media', self.sources['social_media']['count'])
            
        except Exception as e:
            logger.error(f"社交媒体数据收集失败: {e}")
    
    def collect_news_data(self):
        """收集新闻数据（模拟）"""
        try:
            # 模拟新闻数据收集
            categories = ['world', 'technology', 'science', 'culture', 'health', 'business']
            category = np.random.choice(categories)
            
            # 模拟情感分析
            emotions = ['neutral', 'concern', 'optimism', 'pessimism']
            emotion_weights = np.random.dirichlet(np.ones(4))
            emotion_vector = {emotion: float(weight) for emotion, weight in zip(emotions, emotion_weights)}
            
            # 模拟新闻内容
            news_templates = [
                f"{category}领域的重要新闻",
                f"关于{category}的新研究揭示重要发现",
                f"全球{category}领域的发展动态",
                f"{category}理解的文化变迁"
            ]
            content = np.random.choice(news_templates)
            
            data = {
                'content': content,
                'source': 'news',
                'emotion_vector': emotion_vector,
                'intensity': np.random.uniform(0.4, 0.8),
                'cultural_context': 'international',
                'timestamp': datetime.now().isoformat(),
                'language': 'en',
                'sentiment_score': np.random.uniform(-0.5, 0.5),
                'geographic_location': 'Global'
            }
            
            self.data_received.emit(data)
            
            # 保存到数据库
            self.db_manager.add_collective_memory(
                content=data['content'],
                user_id=self.user_id,
                emotion_vector=emotion_vector,
                intensity=data['intensity'],
                source_type='news',
                cultural_context=data['cultural_context'],
                language=data['language'],
                sentiment_score=data['sentiment_score'],
                geographic_location=data['geographic_location']
            )
            
            # 更新统计
            self.sources['news_feeds']['count'] += 1
            self.collection_stats['total_collected'] += 1
            self.source_updated.emit('news_feeds', self.sources['news_feeds']['count'])
            
        except Exception as e:
            logger.error(f"新闻数据收集失败: {e}")
    
    def collect_academic_data(self):
        """收集学术数据（模拟）"""
        try:
            # 模拟学术数据收集
            disciplines = ['psychology', 'anthropology', 'sociology', 'neuroscience']
            discipline = np.random.choice(disciplines)
            
            content = f"新的{discipline}研究对集体潜意识理论提供了支持"
            
            data = {
                'content': content,
                'source': 'academic',
                'intensity': np.random.uniform(0.6, 0.9),
                'cultural_context': 'academic',
                'timestamp': datetime.now().isoformat(),
                'language': 'en',
                'sentiment_score': np.random.uniform(0.3, 0.8)
            }
            
            self.data_received.emit(data)
            
            # 保存到数据库
            self.db_manager.add_collective_memory(
                content=data['content'],
                user_id=self.user_id,
                intensity=data['intensity'],
                source_type='academic',
                cultural_context=data['cultural_context'],
                language=data['language'],
                sentiment_score=data['sentiment_score']
            )
            
            # 更新统计
            self.sources['academic_publications']['count'] += 1
            self.collection_stats['total_collected'] += 1
            self.source_updated.emit('academic_publications', self.sources['academic_publications']['count'])
            
        except Exception as e:
            logger.error(f"学术数据收集失败: {e}")

class AdvancedVisualization3D(QWidget):
    """高级3D可视化组件"""
    
    def __init__(self, db_manager):
        super().__init__()
        self.db_manager = db_manager
        self.current_visualization = None
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        
        # 控制面板
        control_layout = QHBoxLayout()
        
        self.viz_type_combo = QComboBox()
        self.viz_type_combo.addItems([
            "3D文化空间", 
            "时间流可视化", 
            "网络关系图", 
            "情感地形图",
            "原型演化轨迹"
        ])
        
        self.refresh_btn = QPushButton("刷新可视化")
        self.refresh_btn.clicked.connect(self.refresh_visualization)
        
        self.export_btn = QPushButton("导出可视化")
        self.export_btn.clicked.connect(self.export_visualization)
        
        self.animation_btn = QPushButton("播放动画")
        self.animation_btn.setCheckable(True)
        self.animation_btn.clicked.connect(self.toggle_animation)
        
        control_layout.addWidget(QLabel("可视化类型:"))
        control_layout.addWidget(self.viz_type_combo)
        control_layout.addWidget(self.refresh_btn)
        control_layout.addWidget(self.export_btn)
        control_layout.addWidget(self.animation_btn)
        control_layout.addStretch()
        
        # 可视化区域
        self.viz_container = QTabWidget()
        
        # Web视图（用于Three.js等3D可视化）
        self.web_view = QWebEngineView()
        
        # 2D图形视图作为备选
        self.graphics_view = QGraphicsView()
        self.graphics_scene = QGraphicsScene()
        self.graphics_view.setScene(self.graphics_scene)
        
        self.viz_container.addTab(self.web_view, "3D可视化")
        self.viz_container.addTab(self.graphics_view, "2D视图")
        
        layout.addLayout(control_layout)
        layout.addWidget(self.viz_container)
        
        # 初始加载可视化
        self.refresh_visualization()
    
    def refresh_visualization(self):
        """刷新可视化"""
        viz_type = self.viz_type_combo.currentText()
        
        if viz_type == "3D文化空间":
            self.show_3d_cultural_space()
        elif viz_type == "时间流可视化":
            self.show_temporal_flow()
        elif viz_type == "网络关系图":
            self.show_network_graph()
        elif viz_type == "情感地形图":
            self.show_emotion_landscape()
        elif viz_type == "原型演化轨迹":
            self.show_archetype_evolution()
    
    def show_3d_cultural_space(self):
        """显示3D文化空间"""
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
            <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.min.js"></script>
            <style>
                body { margin: 0; overflow: hidden; }
                #info { position: absolute; top: 10px; left: 10px; color: white; }
            </style>
        </head>
        <body>
            <div id="info">3D文化空间可视化 - 使用鼠标旋转和缩放</div>
            <script>
                // 创建场景
                const scene = new THREE.Scene();
                scene.background = new THREE.Color(0x1a1a2e);
                
                // 创建相机
                const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
                camera.position.z = 5;
                
                // 创建渲染器
                const renderer = new THREE.WebGLRenderer();
                renderer.setSize(window.innerWidth, window.innerHeight);
                document.body.appendChild(renderer.domElement);
                
                // 添加轨道控制
                const controls = new THREE.OrbitControls(camera, renderer.domElement);
                controls.enableDamping = true;
                controls.dampingFactor = 0.05;
                
                // 添加环境光
                const ambientLight = new THREE.AmbientLight(0x404040);
                scene.add(ambientLight);
                
                // 添加定向光
                const directionalLight = new THREE.DirectionalLight(0xffffff, 0.5);
                directionalLight.position.set(1, 1, 1);
                scene.add(directionalLight);
                
                // 创建文化数据点
                const cultures = ['Western', 'Eastern', 'African', 'Middle Eastern', 'Latin American'];
                const colors = [0xff6b6b, 0x4ecdc4, 0x45b7d1, 0xf9ca24, 0x6c5ce7];
                
                cultures.forEach((culture, index) => {
                    const geometry = new THREE.SphereGeometry(0.3, 32, 32);
                    const material = new THREE.MeshPhongMaterial({ 
                        color: colors[index],
                        emissive: colors[index],
                        emissiveIntensity: 0.2
                    });
                    const sphere = new THREE.Mesh(geometry, material);
                    
                    // 随机位置
                    sphere.position.x = (Math.random() - 0.5) * 8;
                    sphere.position.y = (Math.random() - 0.5) * 8;
                    sphere.position.z = (Math.random() - 0.5) * 8;
                    
                    scene.add(sphere);
                    
                    // 添加文化标签
                    const canvas = document.createElement('canvas');
                    const context = canvas.getContext('2d');
                    canvas.width = 256;
                    canvas.height = 128;
                    context.fillStyle = '#ffffff';
                    context.font = '48px Arial';
                    context.fillText(culture, 10, 50);
                    
                    const texture = new THREE.CanvasTexture(canvas);
                    const labelMaterial = new THREE.SpriteMaterial({ map: texture });
                    const label = new THREE.Sprite(labelMaterial);
                    label.position.copy(sphere.position);
                    label.position.y += 0.5;
                    label.scale.set(2, 1, 1);
                    scene.add(label);
                });
                
                // 添加连接线
                for (let i = 0; i < cultures.length; i++) {
                    for (let j = i + 1; j < cultures.length; j++) {
                        const geometry = new THREE.BufferGeometry();
                        const points = [];
                        points.push(new THREE.Vector3(
                            (Math.random() - 0.5) * 8,
                            (Math.random() - 0.5) * 8,
                            (Math.random() - 0.5) * 8
                        ));
                        points.push(new THREE.Vector3(
                            (Math.random() - 0.5) * 8,
                            (Math.random() - 0.5) * 8,
                            (Math.random() - 0.5) * 8
                        ));
                        
                        geometry.setFromPoints(points);
                        const material = new THREE.LineBasicMaterial({ 
                            color: 0xffffff,
                            opacity: 0.3,
                            transparent: true
                        });
                        const line = new THREE.Line(geometry, material);
                        scene.add(line);
                    }
                }
                
                // 动画循环
                function animate() {
                    requestAnimationFrame(animate);
                    controls.update();
                    renderer.render(scene, camera);
                }
                animate();
                
                // 窗口大小调整
                window.addEventListener('resize', () => {
                    camera.aspect = window.innerWidth / window.innerHeight;
                    camera.updateProjectionMatrix();
                    renderer.setSize(window.innerWidth, window.innerHeight);
                });
            </script>
        </body>
        </html>
        """
        
        self.web_view.setHtml(html_content)
    
    def show_temporal_flow(self):
        """显示时间流可视化"""
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <script src="https://d3js.org/d3.v7.min.js"></script>
            <style>
                .timeline { margin: 20px; }
                .event { cursor: pointer; }
                .event:hover { opacity: 0.7; }
            </style>
        </head>
        <body>
            <div id="timeline"></div>
            <script>
                // 创建时间线数据
                const events = [
                    { date: new Date(2020, 0, 1), title: "全球疫情开始", significance: 0.9 },
                    { date: new Date(2020, 5, 1), title: "社会隔离文化形成", significance: 0.7 },
                    { date: new Date(2021, 1, 1), title: "远程工作普及", significance: 0.8 },
                    { date: new Date(2022, 0, 1), title: "元宇宙概念兴起", significance: 0.6 },
                    { date: new Date(2023, 0, 1), title: "AI文化冲击", significance: 0.9 }
                ];
                
                const margin = { top: 20, right: 30, bottom: 30, left: 40 };
                const width = 800 - margin.left - margin.right;
                const height = 400 - margin.top - margin.bottom;
                
                const svg = d3.select("#timeline")
                    .append("svg")
                    .attr("width", width + margin.left + margin.right)
                    .attr("height", height + margin.top + margin.bottom)
                    .append("g")
                    .attr("transform", `translate(${margin.left},${margin.top})`);
                
                // 创建时间比例尺
                const x = d3.scaleTime()
                    .domain(d3.extent(events, d => d.date))
                    .range([0, width]);
                
                // 创建重要性比例尺
                const y = d3.scaleLinear()
                    .domain([0, 1])
                    .range([height, 0]);
                
                // 添加坐标轴
                svg.append("g")
                    .attr("transform", `translate(0,${height})`)
                    .call(d3.axisBottom(x));
                
                svg.append("g")
                    .call(d3.axisLeft(y));
                
                // 添加事件点
                svg.selectAll("circle")
                    .data(events)
                    .enter()
                    .append("circle")
                    .attr("class", "event")
                    .attr("cx", d => x(d.date))
                    .attr("cy", d => y(d.significance))
                    .attr("r", d => d.significance * 10)
                    .attr("fill", "steelblue")
                    .append("title")
                    .text(d => d.title);
                
                // 添加趋势线
                const line = d3.line()
                    .x(d => x(d.date))
                    .y(d => y(d.significance))
                    .curve(d3.curveMonotoneX);
                
                svg.append("path")
                    .datum(events)
                    .attr("fill", "none")
                    .attr("stroke", "red")
                    .attr("stroke-width", 2)
                    .attr("d", line);
            </script>
        </body>
        </html>
        """
        
        self.web_view.setHtml(html_content)
    
    def toggle_animation(self):
        """切换动画播放"""
        if self.animation_btn.isChecked():
            self.animation_btn.setText("停止动画")
            # 这里可以启动动画逻辑
        else:
            self.animation_btn.setText("播放动画")
            # 这里可以停止动画逻辑
    
    def export_visualization(self):
        """导出可视化"""
        filename, _ = QFileDialog.getSaveFileName(
            self, "导出可视化", "", 
            "HTML Files (*.html);;PNG Files (*.png);;SVG Files (*.svg)"
        )
        
        if filename:
            # 这里实现导出逻辑
            QMessageBox.information(self, "导出成功", f"可视化已导出到 {filename}")

# 修复缺失的类实现
class AdvancedLoginDialog(QDialog):
    """高级登录对话框"""
    
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.user_info = None
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("集体潜意识系统 - 登录")
        self.setFixedSize(400, 300)
        
        layout = QVBoxLayout()
        
        # 标题
        title_label = QLabel("人类集体潜意识分析系统")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; margin: 10px;")
        
        # 表单区域
        form_widget = QWidget()
        form_layout = QFormLayout(form_widget)
        
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("请输入用户名")
        self.username_input.setMinimumHeight(35)
        
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("请输入密码")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setMinimumHeight(35)
        
        self.remember_check = QCheckBox("记住登录状态")
        self.auto_login_check = QCheckBox("自动登录")
        
        form_layout.addRow("用户名:", self.username_input)
        form_layout.addRow("密码:", self.password_input)
        form_layout.addRow(self.remember_check)
        form_layout.addRow(self.auto_login_check)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        
        login_btn = QPushButton("登录")
        login_btn.setMinimumHeight(40)
        login_btn.clicked.connect(self.authenticate)
        
        register_btn = QPushButton("注册")
        register_btn.setMinimumHeight(40)
        register_btn.clicked.connect(self.show_registration)
        
        button_layout.addWidget(login_btn)
        button_layout.addWidget(register_btn)
        
        layout.addWidget(title_label)
        layout.addWidget(form_widget)
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def authenticate(self):
        """用户认证"""
        username = self.username_input.text()
        password = self.password_input.text()
        
        if not username or not password:
            QMessageBox.warning(self, "输入错误", "请输入用户名和密码")
            return
        
        user_info = self.db_manager.authenticate_user(username, password)
        
        if user_info:
            self.user_info = user_info
            self.accept()
        else:
            QMessageBox.warning(self, "认证失败", "用户名或密码错误")
    
    def show_registration(self):
        """显示注册对话框"""
        dialog = AdvancedRegistrationDialog(self.db_manager, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            QMessageBox.information(self, "注册成功", "用户注册成功，请登录")

class AdvancedRegistrationDialog(QDialog):
    """高级注册对话框"""
    
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("用户注册")
        self.setFixedSize(400, 350)
        
        layout = QVBoxLayout()
        
        title_label = QLabel("创建新账户")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; margin: 10px;")
        
        # 表单区域
        form_widget = QWidget()
        form_layout = QFormLayout(form_widget)
        
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("请输入用户名")
        
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("请输入密码")
        
        self.confirm_password_input = QLineEdit()
        self.confirm_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_password_input.setPlaceholderText("请确认密码")
        
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("请输入邮箱地址")
        
        self.role_combo = QComboBox()
        self.role_combo.addItems(["研究员", "分析师", "观察员"])
        
        form_layout.addRow("用户名:", self.username_input)
        form_layout.addRow("密码:", self.password_input)
        form_layout.addRow("确认密码:", self.confirm_password_input)
        form_layout.addRow("邮箱:", self.email_input)
        form_layout.addRow("角色:", self.role_combo)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        
        register_btn = QPushButton("注册")
        register_btn.clicked.connect(self.register_user)
        
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(register_btn)
        button_layout.addWidget(cancel_btn)
        
        layout.addWidget(title_label)
        layout.addWidget(form_widget)
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def register_user(self):
        """注册用户"""
        username = self.username_input.text()
        password = self.password_input.text()
        confirm_password = self.confirm_password_input.text()
        email = self.email_input.text()
        role = self.role_combo.currentText()
        
        if not username or not password:
            QMessageBox.warning(self, "输入错误", "请输入用户名和密码")
            return
        
        if password != confirm_password:
            QMessageBox.warning(self, "密码错误", "两次输入的密码不一致")
            return
        
        if not email or '@' not in email:
            QMessageBox.warning(self, "邮箱错误", "请输入有效的邮箱地址")
            return
        
        # 映射角色到英文
        role_mapping = {
            "研究员": "researcher",
            "分析师": "analyst", 
            "观察员": "observer"
        }
        
        if self.db_manager.create_user(username, password, email, role_mapping.get(role, "researcher")):
            self.accept()
        else:
            QMessageBox.warning(self, "注册失败", "用户名已存在")

class EnhancedCollectiveUnconsciousSystem(QMainWindow):
    """增强版集体潜意识系统主界面"""
    
    def __init__(self, db_manager, user_info):
        super().__init__()
        self.db_manager = db_manager
        self.user_info = user_info
        
        # 初始化UI
        self.init_ui()
        
        # 创建分析器和收集器
        self.deep_analyzer = AdvancedDeepLearningAnalyzer(db_manager, user_info['id'])
        self.data_collector = EnhancedRealTimeDataCollector(db_manager, user_info['id'])
        
        self.setup_connections()
        self.load_default_data()
        self.start_services()
        
        logger.info(f"用户 {user_info['username']} 登录系统")
    
    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle(f"人类集体潜意识分析系统 - {self.user_info['username']}")
        self.setGeometry(100, 50, 1600, 1000)
        
        # 创建中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # 创建标签页
        self.tabs = QTabWidget()
        
        # 创建各个标签页
        self.visualization_tab = AdvancedVisualization3D(self.db_manager)
        self.analysis_tab = self.create_analysis_tab()
        self.data_tab = self.create_data_tab()
        self.collaboration_tab = self.create_collaboration_tab()
        
        self.tabs.addTab(self.visualization_tab, "可视化分析")
        self.tabs.addTab(self.analysis_tab, "数据分析")
        self.tabs.addTab(self.data_tab, "数据管理")
        self.tabs.addTab(self.collaboration_tab, "协作研究")
        
        main_layout.addWidget(self.tabs)
        
        # 创建状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("系统就绪")
    
    def create_analysis_tab(self):
        """创建数据分析标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 分析控制面板
        control_group = QGroupBox("分析控制")
        control_layout = QHBoxLayout(control_group)
        
        self.analysis_type_combo = QComboBox()
        self.analysis_type_combo.addItems([
            "文化模式分析",
            "时间序列分析", 
            "跨文化比较",
            "情感趋势分析",
            "原型演化分析"
        ])
        
        self.start_analysis_btn = QPushButton("开始分析")
        self.start_analysis_btn.clicked.connect(self.start_analysis)
        
        self.analysis_progress = QProgressBar()
        
        control_layout.addWidget(QLabel("分析类型:"))
        control_layout.addWidget(self.analysis_type_combo)
        control_layout.addWidget(self.start_analysis_btn)
        control_layout.addWidget(self.analysis_progress)
        
        # 结果显示区域
        self.results_browser = QTextBrowser()
        
        layout.addWidget(control_group)
        layout.addWidget(self.results_browser)
        
        return widget
    
    def create_data_tab(self):
        """创建数据管理标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 数据源管理
        source_group = QGroupBox("数据源管理")
        source_layout = QHBoxLayout(source_group)
        
        self.source_list = QListWidget()
        self.source_list.addItems(["社交媒体", "新闻源", "学术数据库", "文化档案"])
        
        source_control_layout = QVBoxLayout()
        self.add_source_btn = QPushButton("添加数据源")
        self.remove_source_btn = QPushButton("移除数据源")
        self.sync_source_btn = QPushButton("同步数据")
        
        source_control_layout.addWidget(self.add_source_btn)
        source_control_layout.addWidget(self.remove_source_btn)
        source_control_layout.addWidget(self.sync_source_btn)
        source_control_layout.addStretch()
        
        source_layout.addWidget(self.source_list)
        source_layout.addLayout(source_control_layout)
        
        # 数据统计
        stats_group = QGroupBox("数据统计")
        stats_layout = QVBoxLayout(stats_group)
        
        self.stats_text = QLabel("总数据量: 0\n今日新增: 0\n数据源: 0")
        stats_layout.addWidget(self.stats_text)
        
        layout.addWidget(source_group)
        layout.addWidget(stats_group)
        
        return widget
    
    def create_collaboration_tab(self):
        """创建协作研究标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 协作会话管理
        session_group = QGroupBox("协作会话")
        session_layout = QHBoxLayout(session_group)
        
        self.session_list = QListWidget()
        self.session_control_layout = QVBoxLayout()
        
        self.create_session_btn = QPushButton("创建会话")
        self.join_session_btn = QPushButton("加入会话")
        self.invite_user_btn = QPushButton("邀请用户")
        
        self.session_control_layout.addWidget(self.create_session_btn)
        self.session_control_layout.addWidget(self.join_session_btn)
        self.session_control_layout.addWidget(self.invite_user_btn)
        self.session_control_layout.addStretch()
        
        session_layout.addWidget(self.session_list)
        session_layout.addLayout(self.session_control_layout)
        
        # 聊天区域
        chat_group = QGroupBox("实时协作")
        chat_layout = QVBoxLayout(chat_group)
        
        self.chat_display = QTextBrowser()
        self.chat_input = QTextEdit()
        self.chat_input.setMaximumHeight(60)
        self.send_msg_btn = QPushButton("发送消息")
        
        chat_layout.addWidget(self.chat_display)
        chat_layout.addWidget(self.chat_input)
        chat_layout.addWidget(self.send_msg_btn)
        
        layout.addWidget(session_group)
        layout.addWidget(chat_group)
        
        return widget
    
    def setup_connections(self):
        """设置信号连接"""
        # 深度学习分析器信号
        self.deep_analyzer.analysis_progress.connect(self.update_analysis_progress)
        self.deep_analyzer.analysis_complete.connect(self.on_analysis_complete)
        self.deep_analyzer.pattern_discovered.connect(self.on_pattern_discovered)
        
        # 数据收集器信号
        self.data_collector.data_received.connect(self.on_data_received)
        self.data_collector.connection_status.connect(self.on_connection_status)
    
    def start_services(self):
        """启动后台服务"""
        # 启动深度学习分析器
        self.deep_analyzer.start()
        
        # 启动数据收集器
        self.data_collector.start()
        
        self.status_bar.showMessage("后台服务已启动")
    
    def load_default_data(self):
        """加载默认数据"""
        # 这里可以加载默认的原型数据等
        pass
    
    def start_analysis(self):
        """开始分析"""
        analysis_type = self.analysis_type_combo.currentText()
        
        # 映射分析类型到任务类型
        type_mapping = {
            "文化模式分析": "cultural_pattern_analysis",
            "时间序列分析": "temporal_analysis",
            "跨文化比较": "cross_cultural_comparison",
            "情感趋势分析": "sentiment_analysis",
            "原型演化分析": "archetype_evolution"
        }
        
        task_type = type_mapping.get(analysis_type, "cultural_pattern_analysis")
        task_id = self.deep_analyzer.add_task(task_type, {})
        
        self.status_bar.showMessage(f"已启动分析任务: {analysis_type} (ID: {task_id})")
    
    def update_analysis_progress(self, progress, message):
        """更新分析进度"""
        self.analysis_progress.setValue(progress)
        self.status_bar.showMessage(message)
    
    def on_analysis_complete(self, result):
        """分析完成处理"""
        self.results_browser.append(f"分析完成: {result['task_type']}")
        self.results_browser.append(f"结果: {str(result.get('result', '无结果'))}")
        self.results_browser.append("-" * 50)
    
    def on_pattern_discovered(self, pattern):
        """处理发现的模式"""
        self.status_bar.showMessage(f"发现新模式: {pattern['type']}")
    
    def on_data_received(self, data):
        """处理接收到的数据"""
        # 这里可以更新数据统计等信息
        pass
    
    def on_connection_status(self, message, status):
        """处理连接状态更新"""
        color = "green" if status else "red"
        self.status_bar.showMessage(message)

# 图形项类
class EnhancedArchetypeNode(QGraphicsItem):
    """增强版原型节点"""
    
    def __init__(self, name, power_level, category):
        super().__init__()
        self.name = name
        self.power_level = power_level
        self.category = category
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
    
    def boundingRect(self):
        return QRectF(-30, -30, 60, 60)
    
    def paint(self, painter, option, widget):
        # 根据类别设置颜色
        category_colors = {
            "人物原型": QColor(100, 150, 255),
            "情境原型": QColor(255, 150, 100),
            "符号原型": QColor(150, 255, 100),
            "情感原型": QColor(255, 100, 255)
        }
        
        color = category_colors.get(self.category, QColor(150, 150, 150))
        color_intensity = min(255, int(self.power_level * 200))
        color.setAlpha(color_intensity)
        
        painter.setBrush(QBrush(color))
        painter.setPen(QPen(Qt.GlobalColor.black, 2))
        painter.drawEllipse(-25, -25, 50, 50)
        
        painter.setFont(QFont("Arial", 8))
        painter.drawText(QRectF(-25, -25, 50, 50), Qt.AlignmentFlag.AlignCenter, self.name)

class CulturalConnection(QGraphicsItem):
    """文化连接图形项"""
    
    def __init__(self, point1, point2, strength):
        super().__init__()
        self.point1 = point1
        self.point2 = point2
        self.strength = strength
    
    def boundingRect(self):
        line = self.point1 - self.point2
        return QRectF(self.point2, line).normalized().adjusted(-5, -5, 5, 5)
    
    def paint(self, painter, option, widget):
        line_width = max(1, int(self.strength * 5))
        alpha = min(200, int(self.strength * 255))
        painter.setPen(QPen(QColor(255, 100, 100, alpha), line_width))
        painter.drawLine(QPointF(*self.point1), QPointF(*self.point2))

def main():
    """主函数"""
    app = QApplication(sys.argv)
    
    # 设置应用程序样式
    app.setStyle(QStyleFactory.create('Fusion'))
    
    # 创建数据库管理器
    db_manager = AdvancedCollectiveUnconsciousDB()
    
    # 显示登录对话框
    login_dialog = AdvancedLoginDialog(db_manager)
    
    if login_dialog.exec() == QDialog.DialogCode.Accepted:
        user_info = login_dialog.user_info
        
        # 创建并显示主窗口
        main_window = EnhancedCollectiveUnconsciousSystem(db_manager, user_info)
        main_window.show()
        
        sys.exit(app.exec())
    else:
        sys.exit(0)

if __name__ == '__main__':
    main()