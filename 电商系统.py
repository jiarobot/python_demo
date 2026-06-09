import sys
import json
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from logging.handlers import RotatingFileHandler
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
import threading
import time
from collections import deque
import warnings
warnings.filterwarnings('ignore')

# PyQt5 相关导入
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QLineEdit, QTextEdit, 
                             QTableWidget, QTableWidgetItem, QHeaderView, QComboBox, 
                             QDateEdit, QSpinBox, QDoubleSpinBox, QProgressBar, 
                             QMessageBox, QFileDialog, QSplitter, QGroupBox, QCheckBox,
                             QFrame, QScrollArea, QTreeWidget, QTreeWidgetItem, QListWidget,
                             QListWidgetItem, QDialog, QFormLayout, QDialogButtonBox,
                             QSystemTrayIcon, QMenu, QAction, QStyle, QToolBar, QStatusBar)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QDate, QTimer, QSize, QSettings
from PyQt5.QtGui import QFont, QColor, QPalette, QIcon, QPixmap, QPainter
from PyQt5.QtChart import QChart, QChartView, QLineSeries, QBarSeries, QBarSet, QPieSeries, QValueAxis

# 机器学习相关
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.cluster import KMeans, DBSCAN
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.metrics import mean_squared_error, r2_score, classification_report
from sklearn.model_selection import train_test_split, cross_val_score
import xgboost as xgb
import lightgbm as lgb

# 数据可视化
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import seaborn as sns
import plotly.graph_objects as go
import plotly.express as px

# 自然语言处理
from textblob import TextBlob
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer

# 网络相关
from bs4 import BeautifulSoup
import tweepy  # 需要安装: pip install tweepy
import facebook  # 需要安装: pip install facebook-sdk

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler('ecommerce_toolkit.log', maxBytes=1024*1024, backupCount=5),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 增强的数据库管理类
class AdvancedDatabaseManager:
    def __init__(self, db_path="ecommerce_advanced.db"):
        self.db_path = db_path
        self.init_database()
        self.setup_connection_pool()
    
    def init_database(self):
        """初始化数据库表结构"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 产品表（增强）
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT,
                subcategory TEXT,
                brand TEXT,
                price REAL,
                cost REAL,
                stock INTEGER,
                min_stock INTEGER DEFAULT 10,
                sales INTEGER DEFAULT 0,
                rating REAL DEFAULT 0,
                review_count INTEGER DEFAULT 0,
                created_date TEXT,
                updated_date TEXT,
                description TEXT,
                tags TEXT,
                image_url TEXT,
                status TEXT DEFAULT 'active',
                sku TEXT UNIQUE
            )
        ''')
        
        # 订单表（增强）
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_number TEXT UNIQUE,
                product_id INTEGER,
                customer_id INTEGER,
                quantity INTEGER,
                unit_price REAL,
                total_price REAL,
                order_date TEXT,
                status TEXT,
                payment_method TEXT,
                shipping_address TEXT,
                billing_address TEXT,
                notes TEXT,
                FOREIGN KEY (product_id) REFERENCES products (id),
                FOREIGN KEY (customer_id) REFERENCES customers (id)
            )
        ''')
        
        # 客户表（增强）
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id TEXT UNIQUE,
                name TEXT NOT NULL,
                email TEXT,
                phone TEXT,
                address TEXT,
                city TEXT,
                country TEXT,
                registration_date TEXT,
                segment TEXT,
                total_orders INTEGER DEFAULT 0,
                total_spent REAL DEFAULT 0,
                last_order_date TEXT,
                avg_order_value REAL DEFAULT 0,
                churn_probability REAL DEFAULT 0,
                lifetime_value REAL DEFAULT 0
            )
        ''')
        
        # 库存记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS inventory_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER,
                change_amount INTEGER,
                previous_stock INTEGER,
                new_stock INTEGER,
                reason TEXT,
                log_date TEXT,
                user_id INTEGER,
                FOREIGN KEY (product_id) REFERENCES products (id)
            )
        ''')
        
        # 价格历史表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS price_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER,
                old_price REAL,
                new_price REAL,
                change_date TEXT,
                reason TEXT,
                FOREIGN KEY (product_id) REFERENCES products (id)
            )
        ''')
        
        # 评论表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER,
                customer_id INTEGER,
                rating INTEGER,
                title TEXT,
                content TEXT,
                review_date TEXT,
                sentiment_score REAL,
                helpful_votes INTEGER DEFAULT 0,
                verified_purchase INTEGER DEFAULT 0,
                FOREIGN KEY (product_id) REFERENCES products (id),
                FOREIGN KEY (customer_id) REFERENCES customers (id)
            )
        ''')
        
        # 营销活动表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS campaigns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                type TEXT,
                start_date TEXT,
                end_date TEXT,
                budget REAL,
                spent REAL DEFAULT 0,
                target_audience TEXT,
                status TEXT,
                roi REAL DEFAULT 0,
                impressions INTEGER DEFAULT 0,
                clicks INTEGER DEFAULT 0,
                conversions INTEGER DEFAULT 0
            )
        ''')
        
        # 网站流量表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS web_traffic (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                visitors INTEGER,
                pageviews INTEGER,
                bounce_rate REAL,
                avg_session_duration REAL,
                conversion_rate REAL,
                source TEXT
            )
        ''')
        
        # 创建索引以提高查询性能
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_orders_date ON orders(order_date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_products_category ON products(category)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_customers_segment ON customers(segment)')
        
        conn.commit()
        conn.close()
        logger.info("数据库初始化完成")
    
    def setup_connection_pool(self):
        """设置数据库连接池（简化版）"""
        self.connections = deque(maxlen=5)
        for _ in range(5):
            self.connections.append(sqlite3.connect(self.db_path))
    
    def get_connection(self):
        """获取数据库连接"""
        if not self.connections:
            return sqlite3.connect(self.db_path)
        return self.connections.popleft()
    
    def return_connection(self, conn):
        """归还数据库连接"""
        if len(self.connections) < self.connections.maxlen:
            self.connections.append(conn)
        else:
            conn.close()
    
    def execute_query(self, query, params=None, return_id=False):
        """执行SQL查询"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            if return_id:
                result = cursor.lastrowid
            else:
                result = cursor.fetchall()
            
            conn.commit()
            return result
        except Exception as e:
            logger.error(f"数据库查询错误: {e}")
            conn.rollback()
            return None
        finally:
            self.return_connection(conn)
    
    def get_dataframe(self, query, params=None):
        """将查询结果转换为DataFrame"""
        conn = self.get_connection()
        try:
            df = pd.read_sql_query(query, conn, params=params)
            return df
        except Exception as e:
            logger.error(f"获取DataFrame错误: {e}")
            return pd.DataFrame()
        finally:
            self.return_connection(conn)
    
    def batch_insert(self, table, data):
        """批量插入数据"""
        if not data:
            return 0
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # 获取列名
        columns = ', '.join(data[0].keys())
        placeholders = ', '.join(['?' for _ in data[0]])
        query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
        
        try:
            # 转换为值列表
            values = [tuple(item.values()) for item in data]
            cursor.executemany(query, values)
            conn.commit()
            return cursor.rowcount
        except Exception as e:
            logger.error(f"批量插入错误: {e}")
            conn.rollback()
            return 0
        finally:
            self.return_connection(conn)


# 高级机器学习分析类
class AdvancedMLAnalyzer:
    def __init__(self, db_manager):
        self.db = db_manager
        self.models = {}
        self.scalers = {}
        logger.info("高级机器学习分析器初始化完成")
    
    def sales_forecasting(self, product_id=None, days=30, model_type='xgboost'):
        """高级销售预测"""
        # 获取历史销售数据
        if product_id:
            query = """
            SELECT date(order_date) as date, SUM(quantity) as daily_sales
            FROM orders 
            WHERE product_id = ? AND order_date >= date('now', '-365 days')
            GROUP BY date(order_date)
            ORDER BY date
            """
            df = self.db.get_dataframe(query, (product_id,))
        else:
            query = """
            SELECT date(order_date) as date, SUM(quantity) as daily_sales
            FROM orders 
            WHERE order_date >= date('now', '-365 days')
            GROUP BY date(order_date)
            ORDER BY date
            """
            df = self.db.get_dataframe(query)
        
        if len(df) < 30:
            logger.warning("数据不足，无法进行销售预测")
            return None
        
        # 创建时间序列特征
        df['date'] = pd.to_datetime(df['date'])
        df = df.set_index('date')
        df = df.asfreq('D').fillna(0)  # 填充缺失日期
        
        # 创建特征
        df['day_of_week'] = df.index.dayofweek
        df['day_of_month'] = df.index.day
        df['month'] = df.index.month
        df['year'] = df.index.year
        df['is_weekend'] = (df.index.dayofweek >= 5).astype(int)
        
        # 添加滞后特征
        for lag in [1, 7, 14, 30]:
            df[f'sales_lag_{lag}'] = df['daily_sales'].shift(lag)
        
        # 添加滚动统计特征
        df['sales_rolling_mean_7'] = df['daily_sales'].rolling(7).mean()
        df['sales_rolling_std_7'] = df['daily_sales'].rolling(7).std()
        
        # 删除缺失值
        df = df.dropna()
        
        if len(df) < 30:
            return None
        
        # 准备训练数据
        X = df.drop('daily_sales', axis=1)
        y = df['daily_sales']
        
        # 划分训练测试集
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, shuffle=False)
        
        # 选择模型
        if model_type == 'xgboost':
            model = xgb.XGBRegressor(n_estimators=100, max_depth=6, learning_rate=0.1)
        elif model_type == 'lightgbm':
            model = lgb.LGBMRegressor(n_estimators=100, max_depth=6, learning_rate=0.1)
        elif model_type == 'random_forest':
            model = RandomForestRegressor(n_estimators=100, max_depth=10, random_state=42)
        else:
            model = GradientBoostingRegressor(n_estimators=100, max_depth=6, learning_rate=0.1)
        
        # 训练模型
        model.fit(X_train, y_train)
        
        # 评估模型
        y_pred = model.predict(X_test)
        mse = mean_squared_error(y_test, y_pred)
        r2 = r2_score(y_test, y_pred)
        
        logger.info(f"销售预测模型评估 - MSE: {mse:.2f}, R²: {r2:.2f}")
        
        # 预测未来
        last_date = df.index[-1]
        future_dates = [last_date + timedelta(days=i) for i in range(1, days+1)]
        
        # 创建未来特征
        future_df = pd.DataFrame(index=future_dates)
        future_df['day_of_week'] = future_df.index.dayofweek
        future_df['day_of_month'] = future_df.index.day
        future_df['month'] = future_df.index.month
        future_df['year'] = future_df.index.year
        future_df['is_weekend'] = (future_df.index.dayofweek >= 5).astype(int)
        
        # 使用最后已知值填充滞后特征
        for lag in [1, 7, 14, 30]:
            future_df[f'sales_lag_{lag}'] = df['daily_sales'].iloc[-lag]
        
        # 使用最后已知值填充滚动特征
        future_df['sales_rolling_mean_7'] = df['daily_sales'].tail(7).mean()
        future_df['sales_rolling_std_7'] = df['daily_sales'].tail(7).std()
        
        # 预测
        future_predictions = model.predict(future_df)
        
        result = {
            'dates': future_dates,
            'predictions': future_predictions.tolist(),
            'model_performance': {'mse': mse, 'r2': r2},
            'feature_importance': dict(zip(X.columns, model.feature_importances_))
        }
        
        return result
    
    def customer_segmentation(self, method='kmeans', n_clusters=4):
        """高级客户细分"""
        query = """
        SELECT 
            total_orders, 
            total_spent, 
            avg_order_value,
            julianday('now') - julianday(last_order_date) as days_since_last_order,
            lifetime_value
        FROM customers 
        WHERE total_orders > 0 AND last_order_date IS NOT NULL
        """
        df = self.db.get_dataframe(query)
        
        if len(df) < 10:
            logger.warning("客户数据不足，无法进行细分")
            return None
        
        # 数据预处理
        scaler = StandardScaler()
        scaled_data = scaler.fit_transform(df)
        
        # 客户细分
        if method == 'kmeans':
            model = KMeans(n_clusters=n_clusters, random_state=42)
        elif method == 'dbscan':
            model = DBSCAN(eps=0.5, min_samples=5)
        else:
            model = KMeans(n_clusters=n_clusters, random_state=42)
        
        clusters = model.fit_predict(scaled_data)
        df['cluster'] = clusters
        
        # 分析每个集群的特征
        cluster_profiles = {}
        for cluster in set(clusters):
            cluster_data = df[df['cluster'] == cluster]
            profile = {
                'size': len(cluster_data),
                'avg_orders': cluster_data['total_orders'].mean(),
                'avg_spent': cluster_data['total_spent'].mean(),
                'avg_aov': cluster_data['avg_order_value'].mean(),
                'avg_recency': cluster_data['days_since_last_order'].mean(),
                'avg_lifetime_value': cluster_data['lifetime_value'].mean()
            }
            cluster_profiles[cluster] = profile
        
        result = {
            'clustered_data': df,
            'cluster_profiles': cluster_profiles,
            'model': model
        }
        
        return result
    
    def customer_churn_prediction(self):
        """客户流失预测"""
        # 获取客户数据
        query = """
        SELECT 
            c.*,
            CASE WHEN julianday('now') - julianday(c.last_order_date) > 90 THEN 1 ELSE 0 END as churned
        FROM customers c
        WHERE c.total_orders > 0 AND c.last_order_date IS NOT NULL
        """
        df = self.db.get_dataframe(query)
        
        if len(df) < 20:
            return None
        
        # 准备特征和目标变量
        feature_columns = ['total_orders', 'total_spent', 'avg_order_value', 
                          'julianday("now") - julianday(last_order_date) as recency']
        
        X = df[['total_orders', 'total_spent', 'avg_order_value']]
        X['recency'] = (pd.to_datetime('now') - pd.to_datetime(df['last_order_date'])).dt.days
        y = df['churned']
        
        # 划分训练测试集
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42)
        
        # 训练模型
        model = LogisticRegression(random_state=42)
        model.fit(X_train, y_train)
        
        # 预测
        y_pred = model.predict(X_test)
        y_pred_proba = model.predict_proba(X_test)[:, 1]
        
        # 评估模型
        accuracy = model.score(X_test, y_test)
        report = classification_report(y_test, y_pred, output_dict=True)
        
        # 预测所有客户的流失概率
        df['churn_probability'] = model.predict_proba(X)[:, 1]
        
        result = {
            'model': model,
            'accuracy': accuracy,
            'classification_report': report,
            'predictions': df[['id', 'name', 'churn_probability']].to_dict('records')
        }
        
        return result
    
    def sentiment_analysis(self, text):
        """情感分析"""
        try:
            # 使用TextBlob进行情感分析
            blob = TextBlob(text)
            sentiment = blob.sentiment
            
            # 使用NLTK的VADER进行情感分析（更适合社交媒体文本）
            sia = SentimentIntensityAnalyzer()
            vader_scores = sia.polarity_scores(text)
            
            result = {
                'textblob_polarity': sentiment.polarity,
                'textblob_subjectivity': sentiment.subjectivity,
                'vader_compound': vader_scores['compound'],
                'vader_positive': vader_scores['pos'],
                'vader_negative': vader_scores['neg'],
                'vader_neutral': vader_scores['neu'],
                'overall_sentiment': 'positive' if vader_scores['compound'] > 0.05 else 
                                    'negative' if vader_scores['compound'] < -0.05 else 'neutral'
            }
            
            return result
        except Exception as e:
            logger.error(f"情感分析错误: {e}")
            return None
    
    def analyze_reviews(self):
        """分析产品评论情感"""
        query = "SELECT id, product_id, content FROM reviews WHERE content IS NOT NULL"
        df = self.db.get_dataframe(query)
        
        if df.empty:
            return None
        
        # 对每条评论进行情感分析
        sentiments = []
        for _, row in df.iterrows():
            sentiment = self.sentiment_analysis(row['content'])
            if sentiment:
                sentiment['review_id'] = row['id']
                sentiment['product_id'] = row['product_id']
                sentiments.append(sentiment)
        
        # 更新数据库
        for sentiment in sentiments:
            self.db.execute_query(
                "UPDATE reviews SET sentiment_score = ? WHERE id = ?",
                (sentiment['vader_compound'], sentiment['review_id'])
            )
        
        # 按产品分组分析
        sentiment_df = pd.DataFrame(sentiments)
        product_sentiment = sentiment_df.groupby('product_id').agg({
            'vader_compound': 'mean',
            'textblob_polarity': 'mean',
            'review_id': 'count'
        }).rename(columns={'review_id': 'review_count'})
        
        return product_sentiment.to_dict('index')


# 实时监控系统
class RealTimeMonitor(QThread):
    data_updated = pyqtSignal(dict)
    alert_triggered = pyqtSignal(dict)
    
    def __init__(self, db_manager):
        super().__init__()
        self.db = db_manager
        self.running = False
        self.monitoring_interval = 60  # 秒
        self.alert_rules = self.load_alert_rules()
        
    def load_alert_rules(self):
        """加载警报规则"""
        return {
            'low_stock': {'enabled': True, 'threshold': 10},
            'sales_spike': {'enabled': True, 'threshold': 2.0},  # 2倍正常销量
            'negative_reviews': {'enabled': True, 'threshold': 0.3},  # 30%差评
            'website_downtime': {'enabled': True, 'timeout': 5}  # 5秒超时
        }
    
    def run(self):
        """运行监控循环"""
        self.running = True
        logger.info("实时监控系统启动")
        
        while self.running:
            try:
                # 检查库存
                if self.alert_rules['low_stock']['enabled']:
                    self.check_low_stock()
                
                # 检查销售异常
                if self.alert_rules['sales_spike']['enabled']:
                    self.check_sales_anomalies()
                
                # 检查负面评论
                if self.alert_rules['negative_reviews']['enabled']:
                    self.check_negative_reviews()
                
                # 检查网站状态
                if self.alert_rules['website_downtime']['enabled']:
                    self.check_website_status()
                
                # 发送监控数据
                monitor_data = self.collect_monitor_data()
                self.data_updated.emit(monitor_data)
                
                # 等待下一次检查
                time.sleep(self.monitoring_interval)
                
            except Exception as e:
                logger.error(f"监控系统错误: {e}")
                time.sleep(self.monitoring_interval)
    
    def check_low_stock(self):
        """检查低库存"""
        threshold = self.alert_rules['low_stock']['threshold']
        query = """
        SELECT p.id, p.name, p.stock, p.min_stock 
        FROM products p 
        WHERE p.stock <= ? AND p.status = 'active'
        """
        low_stock_products = self.db.execute_query(query, (threshold,))
        
        for product in low_stock_products:
            alert = {
                'type': 'low_stock',
                'level': 'warning' if product[2] > 0 else 'critical',
                'message': f"产品 {product[1]} 库存不足: {product[2]} (最低: {product[3]})",
                'product_id': product[0],
                'timestamp': datetime.now().isoformat()
            }
            self.alert_triggered.emit(alert)
    
    def check_sales_anomalies(self):
        """检查销售异常"""
        # 获取最近一小时的销售数据
        one_hour_ago = (datetime.now() - timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S')
        query = """
        SELECT COUNT(*) as recent_orders, 
               (SELECT COUNT(*) FROM orders WHERE order_date >= datetime('now', '-2 hours') 
                AND order_date < datetime('now', '-1 hour')) as previous_orders
        FROM orders 
        WHERE order_date >= ?
        """
        result = self.db.execute_query(query, (one_hour_ago,))
        
        if result and result[0][1] > 0:
            recent_orders, previous_orders = result[0]
            ratio = recent_orders / previous_orders if previous_orders > 0 else 0
            
            threshold = self.alert_rules['sales_spike']['threshold']
            if ratio >= threshold:
                alert = {
                    'type': 'sales_spike',
                    'level': 'info',
                    'message': f"销售异常: 最近一小时订单量是前一小时的 {ratio:.1f} 倍",
                    'ratio': ratio,
                    'timestamp': datetime.now().isoformat()
                }
                self.alert_triggered.emit(alert)
    
    def check_negative_reviews(self):
        """检查负面评论"""
        threshold = self.alert_rules['negative_reviews']['threshold']
        query = """
        SELECT p.id, p.name, 
               COUNT(*) as total_reviews,
               SUM(CASE WHEN r.sentiment_score < -0.1 THEN 1 ELSE 0 END) as negative_reviews
        FROM products p
        LEFT JOIN reviews r ON p.id = r.product_id
        WHERE r.review_date >= date('now', '-7 days')
        GROUP BY p.id
        HAVING total_reviews > 0
        """
        results = self.db.execute_query(query)
        
        for product in results:
            negative_ratio = product[3] / product[2]
            if negative_ratio >= threshold:
                alert = {
                    'type': 'negative_reviews',
                    'level': 'warning',
                    'message': f"产品 {product[1]} 近期负面评论比例过高: {negative_ratio:.1%}",
                    'product_id': product[0],
                    'negative_ratio': negative_ratio,
                    'timestamp': datetime.now().isoformat()
                }
                self.alert_triggered.emit(alert)
    
    def check_website_status(self):
        """检查网站状态"""
        # 这里应该检查实际的网站URL
        test_urls = ['https://www.example.com', 'https://api.example.com']
        
        for url in test_urls:
            try:
                response = requests.get(url, timeout=self.alert_rules['website_downtime']['timeout'])
                if response.status_code != 200:
                    alert = {
                        'type': 'website_downtime',
                        'level': 'critical',
                        'message': f"网站 {url} 响应异常: 状态码 {response.status_code}",
                        'url': url,
                        'status_code': response.status_code,
                        'timestamp': datetime.now().isoformat()
                    }
                    self.alert_triggered.emit(alert)
            except requests.exceptions.RequestException as e:
                alert = {
                    'type': 'website_downtime',
                    'level': 'critical',
                    'message': f"网站 {url} 无法访问: {str(e)}",
                    'url': url,
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                }
                self.alert_triggered.emit(alert)
    
    def collect_monitor_data(self):
        """收集监控数据"""
        # 获取基本指标
        total_products = self.db.execute_query("SELECT COUNT(*) FROM products")[0][0]
        total_customers = self.db.execute_query("SELECT COUNT(*) FROM customers")[0][0]
        
        # 今日订单
        today = datetime.now().strftime('%Y-%m-%d')
        today_orders = self.db.execute_query(
            "SELECT COUNT(*) FROM orders WHERE date(order_date) = ?", (today,))[0][0]
        
        # 今日销售额
        today_sales = self.db.execute_query(
            "SELECT SUM(total_price) FROM orders WHERE date(order_date) = ?", (today,))[0][0] or 0
        
        # 低库存产品数量
        low_stock_count = self.db.execute_query(
            "SELECT COUNT(*) FROM products WHERE stock <= min_stock AND status = 'active'")[0][0]
        
        return {
            'timestamp': datetime.now().isoformat(),
            'total_products': total_products,
            'total_customers': total_customers,
            'today_orders': today_orders,
            'today_sales': today_sales,
            'low_stock_count': low_stock_count,
            'system_status': 'normal'
        }
    
    def stop_monitor(self):
        """停止监控"""
        self.running = False
        logger.info("实时监控系统停止")


# 社交媒体集成类
class SocialMediaIntegrator:
    def __init__(self, db_manager):
        self.db = db_manager
        self.twitter_api = None
        self.facebook_api = None
        self.setup_apis()
    
    def setup_apis(self):
        """设置社交媒体API（需要实际的API密钥）"""
        # 这里需要实际的API密钥
        try:
            # Twitter API 设置
            consumer_key = "YOUR_TWITTER_CONSUMER_KEY"
            consumer_secret = "YOUR_TWITTER_CONSUMER_SECRET"
            access_token = "YOUR_TWITTER_ACCESS_TOKEN"
            access_token_secret = "YOUR_TWITTER_ACCESS_TOKEN_SECRET"
            
            if all([consumer_key, consumer_secret, access_token, access_token_secret]):
                auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
                auth.set_access_token(access_token, access_token_secret)
                self.twitter_api = tweepy.API(auth)
                logger.info("Twitter API 初始化成功")
        except Exception as e:
            logger.warning(f"Twitter API 初始化失败: {e}")
        
        try:
            # Facebook API 设置
            facebook_token = "YOUR_FACEBOOK_ACCESS_TOKEN"
            if facebook_token:
                self.facebook_api = facebook.GraphAPI(access_token=facebook_token)
                logger.info("Facebook API 初始化成功")
        except Exception as e:
            logger.warning(f"Facebook API 初始化失败: {e}")
    
    def monitor_mentions(self, keywords):
        """监控社交媒体提及"""
        if not self.twitter_api:
            return []
        
        mentions = []
        for keyword in keywords:
            try:
                tweets = self.twitter_api.search_tweets(q=keyword, count=10, lang='en')
                for tweet in tweets:
                    mention = {
                        'platform': 'twitter',
                        'user': tweet.user.screen_name,
                        'text': tweet.text,
                        'created_at': tweet.created_at.isoformat(),
                        'url': f"https://twitter.com/{tweet.user.screen_name}/status/{tweet.id}",
                        'keyword': keyword
                    }
                    mentions.append(mention)
            except Exception as e:
                logger.error(f"搜索Twitter提及错误: {e}")
        
        return mentions
    
    def analyze_social_sentiment(self, product_name):
        """分析社交媒体情感"""
        if not self.twitter_api:
            return None
        
        try:
            tweets = self.twitter_api.search_tweets(q=product_name, count=50, lang='en')
            texts = [tweet.text for tweet in tweets]
            
            if not texts:
                return None
            
            # 使用情感分析
            analyzer = AdvancedMLAnalyzer(self.db)
            sentiments = [analyzer.sentiment_analysis(text) for text in texts]
            
            # 计算平均情感
            avg_sentiment = np.mean([s['vader_compound'] for s in sentiments if s])
            
            result = {
                'product': product_name,
                'total_mentions': len(texts),
                'avg_sentiment': avg_sentiment,
                'positive_mentions': len([s for s in sentiments if s and s['vader_compound'] > 0.05]),
                'negative_mentions': len([s for s in sentiments if s and s['vader_compound'] < -0.05]),
                'sample_tweets': texts[:3]  # 返回前3条推文作为样本
            }
            
            return result
        except Exception as e:
            logger.error(f"社交媒体情感分析错误: {e}")
            return None
    
    def post_product_promotion(self, product_id, message):
        """发布产品推广（需要实际API权限）"""
        # 获取产品信息
        product = self.db.execute_query(
            "SELECT name, description, image_url FROM products WHERE id = ?", (product_id,))
        
        if not product:
            return False
        
        product_name, description, image_url = product[0]
        
        # 构建推广消息
        promotion_message = f"{message}\n\n产品: {product_name}\n描述: {description[:100]}..."
        
        # 发布到Twitter
        if self.twitter_api:
            try:
                self.twitter_api.update_status(promotion_message)
                logger.info(f"产品推广已发布到Twitter: {product_name}")
            except Exception as e:
                logger.error(f"Twitter发布错误: {e}")
        
        # 发布到Facebook
        if self.facebook_api:
            try:
                self.facebook_api.put_object("me", "feed", message=promotion_message)
                logger.info(f"产品推广已发布到Facebook: {product_name}")
            except Exception as e:
                logger.error(f"Facebook发布错误: {e}")
        
        return True


# 电子邮件营销类
class EmailMarketingManager:
    def __init__(self, db_manager):
        self.db = db_manager
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587
        self.email = "your_email@gmail.com"
        self.password = "your_app_password"
    
    def send_email(self, to_email, subject, body, is_html=False):
        """发送电子邮件"""
        try:
            # 创建邮件
            msg = MIMEMultipart()
            msg['From'] = self.email
            msg['To'] = to_email
            msg['Subject'] = subject
            
            # 添加邮件正文
            if is_html:
                msg.attach(MIMEText(body, 'html'))
            else:
                msg.attach(MIMEText(body, 'plain'))
            
            # 连接服务器并发送
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.email, self.password)
            text = msg.as_string()
            server.sendmail(self.email, to_email, text)
            server.quit()
            
            logger.info(f"邮件发送成功: {to_email}")
            return True
        except Exception as e:
            logger.error(f"邮件发送失败: {e}")
            return False
    
    def send_promotional_emails(self, campaign_id):
        """发送促销邮件"""
        # 获取活动信息
        campaign = self.db.execute_query(
            "SELECT name, target_audience FROM campaigns WHERE id = ?", (campaign_id,))
        
        if not campaign:
            return False
        
        campaign_name, target_audience = campaign[0]
        
        # 根据目标受众获取客户列表
        if target_audience == 'all':
            customers = self.db.execute_query("SELECT email, name FROM customers WHERE email IS NOT NULL")
        elif target_audience == 'high_value':
            customers = self.db.execute_query(
                "SELECT email, name FROM customers WHERE total_spent > 1000 AND email IS NOT NULL")
        elif target_audience == 'inactive':
            customers = self.db.execute_query(
                "SELECT email, name FROM customers WHERE last_order_date < date('now', '-90 days') AND email IS NOT NULL")
        else:
            customers = self.db.execute_query("SELECT email, name FROM customers WHERE email IS NOT NULL")
        
        # 发送邮件
        success_count = 0
        for customer in customers:
            email, name = customer
            subject = f"特别优惠 - {campaign_name}"
            body = f"""
亲爱的 {name},

我们为您准备了特别优惠！

{campaign_name}

不要错过这个难得的机会！

祝好,
您的电商团队
            """
            
            if self.send_email(email, subject, body):
                success_count += 1
        
        # 更新活动数据
        self.db.execute_query(
            "UPDATE campaigns SET conversions = ? WHERE id = ?",
            (success_count, campaign_id)
        )
        
        logger.info(f"促销邮件发送完成: {success_count}/{len(customers)} 成功")
        return True
    
    def send_abandoned_cart_emails(self):
        """发送购物车放弃提醒邮件"""
        # 获取放弃购物车的客户（有订单但未完成）
        query = """
        SELECT DISTINCT c.email, c.name, o.order_date
        FROM customers c
        JOIN orders o ON c.id = o.customer_id
        WHERE o.status = 'pending'
        AND o.order_date >= datetime('now', '-1 day')
        AND c.email IS NOT NULL
        """
        customers = self.db.execute_query(query)
        
        for customer in customers:
            email, name, order_date = customer
            subject = "您的购物车还在等您！"
            body = f"""
亲爱的 {name},

我们发现您有未完成的订单（{order_date}）。您的购物车商品还在等待您！

点击这里完成购买: [链接]

有任何问题，请随时联系我们。

祝好,
您的电商团队
            """
            
            self.send_email(email, subject, body)
        
        logger.info(f"购物车放弃提醒邮件发送完成: {len(customers)} 封")
        return True


# 由于代码长度限制，这里只展示了部分核心类
# 实际应用中还需要实现UI界面、报表生成器、API接口等组件

def main():
    """主函数"""
    app = QApplication(sys.argv)
    
    # 创建数据库管理器
    db_manager = AdvancedDatabaseManager()
    
    # 创建分析器
    analyzer = AdvancedMLAnalyzer(db_manager)
    
    # 测试功能
    print("测试销售预测...")
    forecast = analyzer.sales_forecasting(days=7, model_type='xgboost')
    if forecast:
        print("销售预测结果:")
        for i, (date, prediction) in enumerate(zip(forecast['dates'], forecast['predictions'])):
            print(f"{date.strftime('%Y-%m-%d')}: 预测销量 {prediction:.1f}")
    
    print("\n测试客户细分...")
    segmentation = analyzer.customer_segmentation()
    if segmentation:
        print("客户细分结果:")
        for cluster, profile in segmentation['cluster_profiles'].items():
            print(f"集群 {cluster}: {profile['size']} 位客户, 平均消费 ¥{profile['avg_spent']:.2f}")
    
    print("\n测试情感分析...")
    sentiment = analyzer.sentiment_analysis("这个产品太棒了！质量非常好，强烈推荐！")
    print(f"情感分析结果: {sentiment}")
    
    print("智能电商系统高级工具库测试完成！")
    
    # 在实际应用中，这里会启动GUI界面
    # window = AdvancedECommerceToolkit(db_manager, analyzer)
    # window.show()
    # sys.exit(app.exec_())

if __name__ == '__main__':
    main()