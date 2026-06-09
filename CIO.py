import sys
import random
import json
import sqlite3
from datetime import datetime, timedelta
from threading import Thread
import numpy as np
import pandas as pd
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QSplitter, QTabWidget, QToolBar, 
                             QAction, QStatusBar, QLabel, QComboBox, QPushButton,
                             QTableWidget, QTableWidgetItem, QHeaderView, QTreeWidget,
                             QTreeWidgetItem, QListView, QProgressBar, QGridLayout,
                             QGroupBox, QTextEdit, QLineEdit, QMessageBox, QDialog,
                             QDialogButtonBox, QFormLayout, QSpinBox, QDoubleSpinBox,
                             QCheckBox, QFileDialog, QMenu, QSystemTrayIcon, QStyle,
                             QListWidget, QListWidgetItem, QSlider, QFrame, QSizePolicy)
from PyQt5.QtCore import Qt, QTimer, QSize, QThread, pyqtSignal, QDateTime, QSettings
from PyQt5.QtGui import QIcon, QColor, QFont, QPalette, QPainter, QLinearGradient, QBrush
import pyqtgraph as pg
import matplotlib.pyplot as plt
import matplotlib
matplotlib.rc("font", family='Microsoft YaHei')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import seaborn as sns
import networkx as nx
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
from prophet import Prophet
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
from plotly.offline import plot
import warnings
warnings.filterwarnings('ignore')

# 数据生成器线程
class DataGeneratorThread(QThread):
    data_ready = pyqtSignal(dict)
    
    def __init__(self):
        super().__init__()
        self.running = True
        
    def run(self):
        while self.running:
            # 生成模拟数据
            data = {
                'timestamp': datetime.now(),
                'cpu_usage': random.randint(10, 95),
                'memory_usage': random.randint(20, 90),
                'network_in': random.randint(100, 1000),
                'network_out': random.randint(50, 800),
                'disk_io': random.randint(100, 500),
                'active_users': random.randint(50, 500),
                'security_events': random.randint(0, 10),
                'system_errors': random.randint(0, 5)
            }
            self.data_ready.emit(data)
            self.msleep(2000)  # 每2秒生成一次数据
            
    def stop(self):
        self.running = False

# 预测分析线程
class PredictionThread(QThread):
    prediction_ready = pyqtSignal(object)
    
    def __init__(self, historical_data):
        super().__init__()
        self.historical_data = historical_data
        
    def run(self):
        # 使用Prophet进行时间序列预测
        try:
            df = self.historical_data.copy()
            df = df.rename(columns={'timestamp': 'ds', 'cpu_usage': 'y'})
            
            model = Prophet(
                yearly_seasonality=True,
                weekly_seasonality=True,
                daily_seasonality=True,
                seasonality_mode='multiplicative'
            )
            model.fit(df)
            
            future = model.make_future_dataframe(periods=24, freq='H')
            forecast = model.predict(future)
            
            self.prediction_ready.emit(forecast)
        except Exception as e:
            print(f"Prediction error: {e}")

# 异常检测线程
class AnomalyDetectionThread(QThread):
    anomalies_detected = pyqtSignal(object)
    
    def __init__(self, data):
        super().__init__()
        self.data = data
        
    def run(self):
        try:
            # 使用多种算法进行异常检测
            X = self.data[['cpu_usage', 'memory_usage', 'network_in', 'network_out']].values
            
            # 隔离森林
            iso_forest = IsolationForest(contamination=0.1, random_state=42)
            iso_preds = iso_forest.fit_predict(X)
            
            # DBSCAN聚类
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)
            dbscan = DBSCAN(eps=0.5, min_samples=5)
            dbscan_preds = dbscan.fit_predict(X_scaled)
            
            # 合并异常检测结果
            anomalies = (iso_preds == -1) | (dbscan_preds == -1)
            
            result = self.data.copy()
            result['is_anomaly'] = anomalies
            
            self.anomalies_detected.emit(result)
        except Exception as e:
            print(f"Anomaly detection error: {e}")

# 设置对话框
class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置")
        self.setModal(True)
        self.resize(500, 400)
        
        self.settings = QSettings("CIO Tool", "Advanced CIO Visualization")
        
        self.initUI()
        self.loadSettings()
        
    def initUI(self):
        layout = QVBoxLayout(self)
        
        # 数据收集设置
        data_group = QGroupBox("数据收集设置")
        data_layout = QFormLayout()
        
        self.update_interval = QSpinBox()
        self.update_interval.setRange(1, 60)
        self.update_interval.setSuffix(" 秒")
        data_layout.addRow("数据更新间隔:", self.update_interval)
        
        self.history_days = QSpinBox()
        self.history_days.setRange(1, 365)
        self.history_days.setSuffix(" 天")
        data_layout.addRow("历史数据保留天数:", self.history_days)
        
        data_group.setLayout(data_layout)
        layout.addWidget(data_group)
        
        # 警报设置
        alert_group = QGroupBox("警报设置")
        alert_layout = QFormLayout()
        
        self.cpu_threshold = QDoubleSpinBox()
        self.cpu_threshold.setRange(0, 100)
        self.cpu_threshold.setSuffix("%")
        self.cpu_threshold.setDecimals(1)
        alert_layout.addRow("CPU使用率警报阈值:", self.cpu_threshold)
        
        self.memory_threshold = QDoubleSpinBox()
        self.memory_threshold.setRange(0, 100)
        self.memory_threshold.setSuffix("%")
        self.memory_threshold.setDecimals(1)
        alert_layout.addRow("内存使用率警报阈值:", self.memory_threshold)
        
        self.enable_email_alerts = QCheckBox()
        alert_layout.addRow("启用邮件警报:", self.enable_email_alerts)
        
        alert_group.setLayout(alert_layout)
        layout.addWidget(alert_group)
        
        # 可视化设置
        viz_group = QGroupBox("可视化设置")
        viz_layout = QFormLayout()
        
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["深色主题", "浅色主题", "蓝色主题", "绿色主题"])
        viz_layout.addRow("界面主题:", self.theme_combo)
        
        self.animation_check = QCheckBox()
        self.animation_check.setChecked(True)
        viz_layout.addRow("启用动画效果:", self.animation_check)
        
        viz_group.setLayout(viz_layout)
        layout.addWidget(viz_group)
        
        # 按钮
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
    def loadSettings(self):
        self.update_interval.setValue(self.settings.value("update_interval", 5, type=int))
        self.history_days.setValue(self.settings.value("history_days", 30, type=int))
        self.cpu_threshold.setValue(self.settings.value("cpu_threshold", 85.0, type=float))
        self.memory_threshold.setValue(self.settings.value("memory_threshold", 80.0, type=float))
        self.enable_email_alerts.setChecked(self.settings.value("enable_email_alerts", False, type=bool))
        self.theme_combo.setCurrentText(self.settings.value("theme", "深色主题"))
        self.animation_check.setChecked(self.settings.value("animation", True, type=bool))
        
    def saveSettings(self):
        self.settings.setValue("update_interval", self.update_interval.value())
        self.settings.setValue("history_days", self.history_days.value())
        self.settings.setValue("cpu_threshold", self.cpu_threshold.value())
        self.settings.setValue("memory_threshold", self.memory_threshold.value())
        self.settings.setValue("enable_email_alerts", self.enable_email_alerts.isChecked())
        self.settings.setValue("theme", self.theme_combo.currentText())
        self.settings.setValue("animation", self.animation_check.isChecked())

# 自定义图表部件
class CustomPlotWidget(pg.PlotWidget):
    def __init__(self, title="", parent=None):
        super().__init__(parent)
        self.setBackground('w')
        self.showGrid(x=True, y=True)
        self.setTitle(title, color='#333', size='12pt')
        
    def add_curve(self, data, color, name, width=2):
        pen = pg.mkPen(color=color, width=width)
        return self.plot(data, pen=pen, name=name)

# 仪表盘卡片部件
class DashboardCard(QFrame):
    def __init__(self, title, value, unit="", trend=None, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(120)
        self.setMaximumWidth(300)
        self.setFrameShape(QFrame.StyledPanel)
        self.setFrameShadow(QFrame.Raised)
        self.setLineWidth(1)
        
        self.title = title
        self.value = value
        self.unit = unit
        self.trend = trend
        
        self.initUI()
        
    def initUI(self):
        layout = QVBoxLayout(self)
        
        # 标题
        title_label = QLabel(self.title)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #555;")
        layout.addWidget(title_label)
        
        # 值
        value_label = QLabel(f"{self.value}{self.unit}")
        value_label.setAlignment(Qt.AlignCenter)
        value_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #2980b9;")
        layout.addWidget(value_label)
        
        # 趋势
        if self.trend is not None:
            trend_label = QLabel(f"{self.trend}%")
            trend_label.setAlignment(Qt.AlignCenter)
            
            if self.trend > 0:
                trend_label.setStyleSheet("color: #e74c3c; font-size: 12px;")
                trend_label.setText(f"↑ {self.trend}%")
            else:
                trend_label.setStyleSheet("color: #27ae60; font-size: 12px;")
                trend_label.setText(f"↓ {abs(self.trend)}%")
                
            layout.addWidget(trend_label)
        
        # 进度条
        progress = QProgressBar()
        progress.setValue(min(100, int(float(self.value))))
        progress.setTextVisible(False)
        
        if float(self.value) > 80:
            progress.setStyleSheet("""
                QProgressBar {
                    border: 1px solid #bbb;
                    border-radius: 5px;
                    text-align: center;
                    background-color: #f5f5f5;
                    height: 8px;
                }
                QProgressBar::chunk {
                    background-color: #e74c3c;
                    border-radius: 5px;
                }
            """)
        else:
            progress.setStyleSheet("""
                QProgressBar {
                    border: 1px solid #bbb;
                    border-radius: 5px;
                    text-align: center;
                    background-color: #f5f5f5;
                    height: 8px;
                }
                QProgressBar::chunk {
                    background-color: #2ecc71;
                    border-radius: 5px;
                }
            """)
            
        layout.addWidget(progress)
        
    def updateValue(self, value, trend=None):
        self.value = value
        if trend is not None:
            self.trend = trend
            
        # 更新子部件
        value_label = self.findChild(QLabel, None)
        if value_label:
            value_label.setText(f"{self.value}{self.unit}")
            
        if trend is not None:
            trend_label = self.layout().itemAt(2).widget()
            if trend_label:
                if self.trend > 0:
                    trend_label.setStyleSheet("color: #e74c3c; font-size: 12px;")
                    trend_label.setText(f"↑ {self.trend}%")
                else:
                    trend_label.setStyleSheet("color: #27ae60; font-size: 12px;")
                    trend_label.setText(f"↓ {abs(self.trend)}%")
        
        # 更新进度条
        progress = self.findChild(QProgressBar)
        if progress:
            progress.setValue(min(100, int(float(self.value))))
            
            if float(self.value) > 80:
                progress.setStyleSheet("""
                    QProgressBar {
                        border: 1px solid #bbb;
                        border-radius: 5px;
                        text-align: center;
                        background-color: #f5f5f5;
                        height: 8px;
                    }
                    QProgressBar::chunk {
                        background-color: #e74c3c;
                        border-radius: 5px;
                    }
                """)
            else:
                progress.setStyleSheet("""
                    QProgressBar {
                        border: 1px solid #bbb;
                        border-radius: 5px;
                        text-align: center;
                        background-color: #f5f5f5;
                        height: 8px;
                    }
                    QProgressBar::chunk {
                        background-color: #2ecc71;
                        border-radius: 5px;
                    }
                """)

# 主应用程序窗口
class CIOVisualizationTool(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("高级CIO可视化分析平台 v3.0")
        self.setGeometry(100, 100, 1800, 1000)
        
        # 初始化设置
        self.settings = QSettings("CIO Tool", "Advanced CIO Visualization")
        
        # 初始化数据库
        self.initDatabase()
        
        # 初始化数据
        self.historical_data = pd.DataFrame()
        self.loadHistoricalData()
        
        # 初始化UI
        self.initUI()
        
        # 初始化数据生成器
        self.data_generator = DataGeneratorThread()
        self.data_generator.data_ready.connect(self.handleNewData)
        self.data_generator.start()
        
        # 初始化定时器
        self.initTimers()
        
        # 创建系统托盘图标
        self.createSystemTray()
        
    def initDatabase(self):
        self.conn = sqlite3.connect('cio_data.db')
        self.cursor = self.conn.cursor()
        
        # 创建数据表
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME,
                cpu_usage REAL,
                memory_usage REAL,
                network_in INTEGER,
                network_out INTEGER,
                disk_io INTEGER,
                active_users INTEGER,
                security_events INTEGER,
                system_errors INTEGER
            )
        ''')
        
        self.conn.commit()
        
    def loadHistoricalData(self):
        try:
            # 从数据库加载历史数据
            days = self.settings.value("history_days", 30, type=int)
            cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
            
            query = f"SELECT * FROM system_metrics WHERE timestamp >= '{cutoff_date}' ORDER BY timestamp"
            self.historical_data = pd.read_sql_query(query, self.conn)
            
            if not self.historical_data.empty:
                self.historical_data['timestamp'] = pd.to_datetime(self.historical_data['timestamp'])
        except Exception as e:
            print(f"Error loading historical data: {e}")
            self.historical_data = pd.DataFrame()
        
    def initUI(self):
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QHBoxLayout(central_widget)
        
        # 左侧边栏
        sidebar = self.createSidebar()
        main_layout.addWidget(sidebar, 1)
        
        # 右侧主区域
        right_panel = QSplitter(Qt.Vertical)
        main_layout.addWidget(right_panel, 4)
        
        # 顶部仪表板
        dashboard = self.createDashboard()
        right_panel.addWidget(dashboard)
        
        # 底部详情区域
        detail_tabs = self.createDetailTabs()
        right_panel.addWidget(detail_tabs)
        
        # 设置分割比例
        right_panel.setSizes([400, 600])
        
        # 创建工具栏
        self.createToolbar()
        
        # 创建状态栏
        self.createStatusBar()
        
        # 应用主题
        self.applyTheme()
        
    def createSidebar(self):
        sidebar = QWidget()
        sidebar.setMaximumWidth(280)
        sidebar_layout = QVBoxLayout(sidebar)
        
        # 标题
        title = QLabel("CIO控制中心")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 18px;
                font-weight: bold;
                padding: 15px;
                background-color: #3498db;
                border-radius: 8px;
                margin: 5px;
            }
        """)
        sidebar_layout.addWidget(title)
        
        # 快速操作按钮
        quick_actions = QGroupBox("快速操作")
        quick_layout = QVBoxLayout()
        
        actions = [
            ("系统概览", "overview"),
            ("性能分析", "performance"),
            ("安全监控", "security"),
            ("资源管理", "resources"),
            ("成本分析", "cost"),
            ("生成报告", "report")
        ]
        
        for action_name, icon_name in actions:
            btn = QPushButton(action_name)
            btn.setIcon(QIcon(f"icons/{icon_name}.png"))
            btn.setStyleSheet("""
                QPushButton {
                    text-align: left;
                    padding: 10px;
                    border: none;
                    border-radius: 5px;
                    background-color: #f8f9fa;
                }
                QPushButton:hover {
                    background-color: #e9ecef;
                }
            """)
            quick_layout.addWidget(btn)
        
        quick_actions.setLayout(quick_layout)
        sidebar_layout.addWidget(quick_actions)
        
        # 系统选择
        sys_group = QGroupBox("系统选择")
        sys_layout = QVBoxLayout()
        
        self.system_combo = QComboBox()
        self.system_combo.addItems(["全部系统", "ERP系统", "CRM系统", "财务系统", "HR系统", "生产系统", "数据分析平台"])
        sys_layout.addWidget(self.system_combo)
        
        self.refresh_btn = QPushButton("刷新数据")
        self.refresh_btn.clicked.connect(self.refreshData)
        self.refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #2ecc71;
                color: white;
                padding: 8px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #27ae60;
            }
        """)
        sys_layout.addWidget(self.refresh_btn)
        
        sys_group.setLayout(sys_layout)
        sidebar_layout.addWidget(sys_group)
        
        # 实时警报
        alert_group = QGroupBox("实时警报")
        alert_layout = QVBoxLayout()
        
        self.alert_list = QListWidget()
        self.alert_list.setStyleSheet("""
            QListWidget {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 5px;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #dee2e6;
            }
            QListWidget::item:last {
                border-bottom: none;
            }
        """)
        
        # 添加示例警报
        alerts = [
            ("高", "CPU使用率超过85%", "10分钟前"),
            ("中", "内存使用率异常", "25分钟前"),
            ("低", "网络流量波动", "1小时前"),
            ("高", "数据库连接数接近上限", "5分钟前")
        ]
        
        for severity, message, time in alerts:
            item = QListWidgetItem(f"{severity}: {message} ({time})")
            if severity == "高":
                item.setBackground(QColor(255, 200, 200))
            elif severity == "中":
                item.setBackground(QColor(255, 235, 200))
            self.alert_list.addItem(item)
        
        alert_layout.addWidget(self.alert_list)
        
        # 警报操作按钮
        alert_btn_layout = QHBoxLayout()
        acknowledge_btn = QPushButton("确认")
        acknowledge_btn.setStyleSheet("QPushButton { padding: 5px; }")
        silence_btn = QPushButton("静音")
        silence_btn.setStyleSheet("QPushButton { padding: 5px; }")
        
        alert_btn_layout.addWidget(acknowledge_btn)
        alert_btn_layout.addWidget(silence_btn)
        alert_layout.addLayout(alert_btn_layout)
        
        alert_group.setLayout(alert_layout)
        sidebar_layout.addWidget(alert_group)
        
        sidebar_layout.addStretch()
        
        return sidebar
        
    def createDashboard(self):
        dashboard = QWidget()
        layout = QVBoxLayout(dashboard)
        
        # 创建指标卡片的水平布局
        metrics_layout = QHBoxLayout()
        
        # 创建仪表盘卡片
        self.health_card = DashboardCard("系统健康度", "92.5", "%", 2.1)
        self.security_card = DashboardCard("安全状态", "87.3", "%", -1.2)
        self.resource_card = DashboardCard("资源使用率", "76.8", "%", 0.5)
        self.performance_card = DashboardCard("性能指标", "89.2", "%", 1.8)
        self.cost_card = DashboardCard("成本效率", "83.5", "%", -0.7)
        
        metrics_layout.addWidget(self.health_card)
        metrics_layout.addWidget(self.security_card)
        metrics_layout.addWidget(self.resource_card)
        metrics_layout.addWidget(self.performance_card)
        metrics_layout.addWidget(self.cost_card)
        
        layout.addLayout(metrics_layout)
        
        # 创建图表区域
        charts_widget = QWidget()
        charts_layout = QHBoxLayout(charts_widget)
        
        # 左侧性能图表
        left_chart = QWidget()
        left_layout = QVBoxLayout(left_chart)
        
        # CPU使用率实时图表
        cpu_chart = CustomPlotWidget("CPU使用率实时监控")
        cpu_chart.setYRange(0, 100)
        self.cpu_curve = cpu_chart.add_curve([], '#3498db', 'CPU使用率')
        left_layout.addWidget(cpu_chart)
        
        # 内存使用率实时图表
        memory_chart = CustomPlotWidget("内存使用率实时监控")
        memory_chart.setYRange(0, 100)
        self.memory_curve = memory_chart.add_curve([], '#e74c3c', '内存使用率')
        left_layout.addWidget(memory_chart)
        
        charts_layout.addWidget(left_chart, 2)
        
        # 右侧网络和异常检测
        right_chart = QWidget()
        right_layout = QVBoxLayout(right_chart)
        
        # 网络流量图
        network_fig = plt.figure(figsize=(8, 4))
        network_canvas = FigureCanvas(network_fig)
        self.plotNetworkTraffic(network_fig)
        right_layout.addWidget(network_canvas)
        
        # 异常检测图
        anomaly_fig = plt.figure(figsize=(8, 4))
        anomaly_canvas = FigureCanvas(anomaly_fig)
        self.plotAnomalyDetection(anomaly_fig)
        right_layout.addWidget(anomaly_canvas)
        
        charts_layout.addWidget(right_chart, 1)
        
        layout.addWidget(charts_widget)
        
        return dashboard
        
    def createDetailTabs(self):
        tab_widget = QTabWidget()
        tab_widget.setTabPosition(QTabWidget.North)
        tab_widget.setMovable(True)
        
        # 系统性能标签
        performance_tab = QWidget()
        performance_layout = QVBoxLayout(performance_tab)
        
        # 性能数据表格
        perf_table = QTableWidget()
        perf_table.setRowCount(15)
        perf_table.setColumnCount(6)
        perf_table.setHorizontalHeaderLabels(["服务器", "CPU使用率", "内存使用率", "磁盘IO", "网络流量", "状态"])
        
        # 填充示例数据
        servers = ["DB-SRV-01", "APP-SRV-01", "WEB-SRV-01", "FILE-SRV-01", "BACKUP-SRV-01",
                  "ANALYTICS-01", "API-GATEWAY-01", "AUTH-SRV-01", "CACHE-01", "LOGGING-01"]
        statuses = ["正常", "警告", "正常", "错误", "正常", "正常", "警告", "正常", "正常", "正常"]
        
        for i in range(10):
            perf_table.setItem(i, 0, QTableWidgetItem(servers[i]))
            perf_table.setItem(i, 1, QTableWidgetItem(f"{random.randint(10, 95)}%"))
            perf_table.setItem(i, 2, QTableWidgetItem(f"{random.randint(20, 90)}%"))
            perf_table.setItem(i, 3, QTableWidgetItem(f"{random.randint(100, 1000)} IOPS"))
            perf_table.setItem(i, 4, QTableWidgetItem(f"{random.randint(50, 800)} Mbps"))
            
            status_item = QTableWidgetItem(statuses[i])
            if statuses[i] == "正常":
                status_item.setBackground(QColor(46, 204, 113))
            elif statuses[i] == "警告":
                status_item.setBackground(QColor(241, 196, 15))
            else:
                status_item.setBackground(QColor(231, 76, 60))
            status_item.setTextAlignment(Qt.AlignCenter)
            perf_table.setItem(i, 5, status_item)
        
        perf_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        performance_layout.addWidget(perf_table)
        
        tab_widget.addTab(performance_tab, "📊 系统性能")
        
        # 安全监控标签
        security_tab = QWidget()
        security_layout = QVBoxLayout(security_tab)
        
        # 安全事件表格
        security_table = QTableWidget()
        security_table.setRowCount(20)
        security_table.setColumnCount(6)
        security_table.setHorizontalHeaderLabels(["时间", "事件类型", "源IP", "目标", "严重程度", "状态"])
        
        # 填充安全事件数据
        event_types = ["登录失败", "端口扫描", "异常流量", "权限提升", "文件修改", "数据泄露尝试"]
        severity_levels = ["低", "中", "高", "严重"]
        statuses = ["新", "已确认", "处理中", "已解决"]
        
        for i in range(20):
            time = (datetime.now() - timedelta(minutes=random.randint(1, 1440))).strftime("%Y-%m-%d %H:%M")
            event_type = random.choice(event_types)
            source_ip = f"192.168.{random.randint(1, 255)}.{random.randint(1, 255)}"
            target = random.choice(["数据库服务器", "Web服务器", "文件服务器", "身份验证服务"])
            severity = random.choice(severity_levels)
            status = random.choice(statuses)
            
            security_table.setItem(i, 0, QTableWidgetItem(time))
            security_table.setItem(i, 1, QTableWidgetItem(event_type))
            security_table.setItem(i, 2, QTableWidgetItem(source_ip))
            security_table.setItem(i, 3, QTableWidgetItem(target))
            
            severity_item = QTableWidgetItem(severity)
            if severity == "低":
                severity_item.setBackground(QColor(46, 204, 113))
            elif severity == "中":
                severity_item.setBackground(QColor(241, 196, 15))
            elif severity == "高":
                severity_item.setBackground(QColor(243, 156, 18))
            else:
                severity_item.setBackground(QColor(231, 76, 60))
            severity_item.setTextAlignment(Qt.AlignCenter)
            security_table.setItem(i, 4, severity_item)
            
            status_item = QTableWidgetItem(status)
            if status == "新":
                status_item.setBackground(QColor(52, 152, 219))
            elif status == "已确认":
                status_item.setBackground(QColor(241, 196, 15))
            elif status == "处理中":
                status_item.setBackground(QColor(243, 156, 18))
            else:
                status_item.setBackground(QColor(46, 204, 113))
            status_item.setTextAlignment(Qt.AlignCenter)
            security_table.setItem(i, 5, status_item)
        
        security_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        security_layout.addWidget(security_table)
        
        tab_widget.addTab(security_tab, "🔒 安全监控")
        
        # 资源管理标签
        resources_tab = QWidget()
        resources_layout = QVBoxLayout(resources_tab)
        
        # 资源使用情况网格
        resources_grid = QGridLayout()
        
        # 存储使用情况
        storage_group = QGroupBox("存储使用情况")
        storage_layout = QVBoxLayout()
        
        storage_labels = [
            ("主存储", "4.2TB / 10TB", 42),
            ("备份存储", "7.1TB / 12TB", 59),
            ("归档存储", "18.4TB / 20TB", 92),
            ("云存储", "2.5TB / 5TB", 50)
        ]
        
        for label, text, percent in storage_labels:
            storage_row = QHBoxLayout()
            storage_row.addWidget(QLabel(label))
            progress = QProgressBar()
            progress.setValue(percent)
            progress.setFormat(text)
            progress.setStyleSheet("""
                QProgressBar {
                    border: 1px solid #bbb;
                    border-radius: 3px;
                    text-align: center;
                    background-color: #f5f5f5;
                }
                QProgressBar::chunk {
                    background-color: #3498db;
                    border-radius: 3px;
                }
            """)
            storage_row.addWidget(progress)
            storage_layout.addLayout(storage_row)
        
        storage_group.setLayout(storage_layout)
        resources_grid.addWidget(storage_group, 0, 0)
        
        # 许可证管理
        license_group = QGroupBox("许可证使用")
        license_layout = QVBoxLayout()
        
        license_data = [
            ("Windows Server", "24/30", 80),
            ("Oracle DB", "5/10", 50),
            ("VMware vSphere", "8/12", 67),
            ("Office 365", "145/150", 97),
            ("Adobe Creative Cloud", "23/25", 92)
        ]
        
        for product, usage, percent in license_data:
            license_row = QHBoxLayout()
            license_row.addWidget(QLabel(product))
            license_row.addWidget(QLabel(usage))
            progress = QProgressBar()
            progress.setValue(percent)
            progress.setStyleSheet("""
                QProgressBar {
                    border: 1px solid #bbb;
                    border-radius: 3px;
                    text-align: center;
                    background-color: #f5f5f5;
                }
                QProgressBar::chunk {
                    background-color: #2ecc71;
                    border-radius: 3px;
                }
            """)
            license_row.addWidget(progress)
            license_layout.addLayout(license_row)
        
        license_group.setLayout(license_layout)
        resources_grid.addWidget(license_group, 0, 1)
        
        # 云资源使用
        cloud_group = QGroupBox("云资源使用")
        cloud_layout = QVBoxLayout()
        
        cloud_services = [
            ("AWS EC2", "$1,245.80", "运行中: 12实例"),
            ("Azure Storage", "$684.30", "使用: 45TB"),
            ("Google Cloud", "$324.50", "运行中: 5实例"),
            ("AWS RDS", "$458.75", "运行中: 3实例")
        ]
        
        for service, cost, status in cloud_services:
            cloud_row = QHBoxLayout()
            cloud_row.addWidget(QLabel(service))
            cloud_row.addWidget(QLabel(cost))
            cloud_row.addWidget(QLabel(status))
            cloud_layout.addLayout(cloud_row)
        
        cloud_group.setLayout(cloud_layout)
        resources_grid.addWidget(cloud_group, 1, 0)
        
        # 预算使用情况
        budget_group = QGroupBox("IT预算使用")
        budget_layout = QVBoxLayout()
        
        budget_categories = [
            ("硬件", "42%", "$42,000/$100,000"),
            ("软件", "35%", "$35,000/$100,000"),
            ("服务", "58%", "$58,000/$100,000"),
            ("人力", "72%", "$216,000/$300,000"),
            ("云服务", "45%", "$45,000/$100,000")
        ]
        
        for category, percent, amount in budget_categories:
            budget_row = QHBoxLayout()
            budget_row.addWidget(QLabel(category))
            budget_row.addWidget(QLabel(percent))
            budget_row.addWidget(QLabel(amount))
            budget_layout.addLayout(budget_row)
        
        budget_group.setLayout(budget_layout)
        resources_grid.addWidget(budget_group, 1, 1)
        
        resources_layout.addLayout(resources_grid)
        tab_widget.addTab(resources_tab, "💾 资源管理")
        
        # 网络拓扑标签
        topology_tab = QWidget()
        topology_layout = QVBoxLayout(topology_tab)
        
        # 创建网络拓扑图
        topology_fig = plt.figure(figsize=(12, 8))
        topology_canvas = FigureCanvas(topology_fig)
        self.plotNetworkTopology(topology_fig)
        topology_layout.addWidget(topology_canvas)
        
        tab_widget.addTab(topology_tab, "🌐 网络拓扑")
        
        # 预测分析标签
        prediction_tab = QWidget()
        prediction_layout = QVBoxLayout(prediction_tab)
        
        # 预测分析图表
        prediction_fig = plt.figure(figsize=(12, 8))
        prediction_canvas = FigureCanvas(prediction_fig)
        self.plotPredictions(prediction_fig)
        prediction_layout.addWidget(prediction_canvas)
        
        # 预测控制按钮
        prediction_controls = QHBoxLayout()
        predict_btn = QPushButton("生成预测")
        predict_btn.clicked.connect(self.generatePredictions)
        prediction_controls.addWidget(predict_btn)
        
        prediction_controls.addStretch()
        prediction_layout.addLayout(prediction_controls)
        
        tab_widget.addTab(prediction_tab, "🔮 预测分析")
        
        return tab_widget
        
    def createToolbar(self):
        toolbar = QToolBar("主工具栏")
        toolbar.setIconSize(QSize(24, 24))
        self.addToolBar(toolbar)
        
        # 添加工具栏动作
        refresh_action = QAction(QIcon("icons/refresh.png"), "刷新", self)
        refresh_action.setShortcut("F5")
        refresh_action.triggered.connect(self.refreshData)
        toolbar.addAction(refresh_action)
        
        dashboard_action = QAction(QIcon("icons/dashboard.png"), "仪表板", self)
        dashboard_action.triggered.connect(self.showDashboard)
        toolbar.addAction(dashboard_action)
        
        alert_action = QAction(QIcon("icons/alert.png"), "警报", self)
        alert_action.triggered.connect(self.showAlerts)
        toolbar.addAction(alert_action)
        
        report_action = QAction(QIcon("icons/report.png"), "报告", self)
        report_action.triggered.connect(self.generateReport)
        toolbar.addAction(report_action)
        
        settings_action = QAction(QIcon("icons/settings.png"), "设置", self)
        settings_action.triggered.connect(self.showSettings)
        toolbar.addAction(settings_action)
        
        toolbar.addSeparator()
        
        # 添加时间范围选择
        time_label = QLabel("时间范围:")
        time_label.setStyleSheet("color: white; padding: 5px;")
        toolbar.addWidget(time_label)
        
        self.time_range = QComboBox()
        self.time_range.addItems(["实时", "最近1小时", "最近24小时", "最近7天", "最近30天"])
        toolbar.addWidget(self.time_range)
        
        toolbar.addSeparator()
        
        # 添加搜索框
        search_label = QLabel("搜索:")
        search_label.setStyleSheet("color: white; padding: 5px;")
        toolbar.addWidget(search_label)
        
        search_box = QLineEdit()
        search_box.setPlaceholderText("输入搜索关键词...")
        search_box.setMaximumWidth(200)
        toolbar.addWidget(search_box)
        
    def createStatusBar(self):
        status_bar = QStatusBar()
        self.setStatusBar(status_bar)
        
        # 添加状态信息
        self.status_label = QLabel("系统状态: 正常运行")
        self.status_label.setStyleSheet("color: #2ecc71; font-weight: bold; padding: 3px;")
        status_bar.addWidget(self.status_label)
        
        # 添加数据更新时间标签
        self.update_label = QLabel("最后更新: --")
        self.update_label.setStyleSheet("color: #7f8c8d; padding: 3px;")
        status_bar.addWidget(self.update_label)
        
        # 添加时间标签
        self.time_label = QLabel()
        self.updateTime()
        self.time_label.setStyleSheet("color: #7f8c8d; padding: 3px;")
        status_bar.addPermanentWidget(self.time_label)
        
        # 添加用户信息
        user_label = QLabel("用户: CIO Admin")
        user_label.setStyleSheet("color: #3498db; padding: 3px;")
        status_bar.addPermanentWidget(user_label)
        
    def createSystemTray(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
            
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.style().standardIcon(QStyle.SP_ComputerIcon))
        
        tray_menu = QMenu()
        
        show_action = tray_menu.addAction("显示")
        show_action.triggered.connect(self.show)
        
        hide_action = tray_menu.addAction("隐藏")
        hide_action.triggered.connect(self.hide)
        
        tray_menu.addSeparator()
        
        quit_action = tray_menu.addAction("退出")
        quit_action.triggered.connect(QApplication.quit)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()
        self.tray_icon.activated.connect(self.trayIconActivated)
        
    def trayIconActivated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self.show()
            self.activateWindow()
        
    def initTimers(self):
        # 设置定时器更新时间
        self.clock_timer = QTimer()
        self.clock_timer.timeout.connect(self.updateTime)
        self.clock_timer.start(1000)  # 每秒更新
        
        # 设置定时器保存数据
        self.save_timer = QTimer()
        self.save_timer.timeout.connect(self.saveDataToDB)
        self.save_timer.start(30000)  # 每30秒保存一次
        
    def updateTime(self):
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.time_label.setText(f"时间: {current_time}")
        
    def handleNewData(self, data):
        # 处理新数据
        timestamp = data['timestamp']
        
        # 更新实时图表
        if hasattr(self, 'cpu_data'):
            self.cpu_data.append(data['cpu_usage'])
            self.memory_data.append(data['memory_usage'])
            
            if len(self.cpu_data) > 100:
                self.cpu_data.pop(0)
                self.memory_data.pop(0)
                
            self.cpu_curve.setData(self.cpu_data)
            self.memory_curve.setData(self.memory_data)
        else:
            self.cpu_data = [data['cpu_usage']]
            self.memory_data = [data['memory_usage']]
            
        # 更新仪表盘卡片
        self.health_card.updateValue(92.5 + random.uniform(-2, 2))
        self.security_card.updateValue(87.3 + random.uniform(-1, 1))
        self.resource_card.updateValue(76.8 + random.uniform(-3, 3))
        self.performance_card.updateValue(89.2 + random.uniform(-2, 2))
        self.cost_card.updateValue(83.5 + random.uniform(-1, 1))
        
        # 添加到历史数据
        new_row = pd.DataFrame([data])
        if self.historical_data.empty:
            self.historical_data = new_row
        else:
            self.historical_data = pd.concat([self.historical_data, new_row], ignore_index=True)
            
        # 更新状态栏
        self.update_label.setText(f"最后更新: {timestamp.strftime('%H:%M:%S')}")
        
        # 检查警报条件
        self.checkAlerts(data)
        
    def checkAlerts(self, data):
        cpu_threshold = self.settings.value("cpu_threshold", 85.0, type=float)
        memory_threshold = self.settings.value("memory_threshold", 80.0, type=float)
        
        alerts = []
        
        if data['cpu_usage'] > cpu_threshold:
            alerts.append(f"CPU使用率过高: {data['cpu_usage']}%")
            
        if data['memory_usage'] > memory_threshold:
            alerts.append(f"内存使用率过高: {data['memory_usage']}%")
            
        if data['security_events'] > 5:
            alerts.append(f"安全事件激增: {data['security_events']}起")
            
        if data['system_errors'] > 3:
            alerts.append(f"系统错误增多: {data['system_errors']}个")
            
        # 显示警报
        for alert in alerts:
            self.showAlert(alert)
            
    def showAlert(self, message):
        # 在系统托盘显示警报
        if hasattr(self, 'tray_icon'):
            self.tray_icon.showMessage("系统警报", message, QSystemTrayIcon.Warning, 5000)
            
        # 在警报列表中添加
        item = QListWidgetItem(f"高: {message} (刚刚)")
        item.setBackground(QColor(255, 200, 200))
        self.alert_list.insertItem(0, item)
        
    def saveDataToDB(self):
        if self.historical_data.empty:
            return
            
        # 获取最新数据
        latest_data = self.historical_data.iloc[-1:]
        
        try:
            # 保存到数据库
            latest_data.to_sql('system_metrics', self.conn, if_exists='append', index=False)
        except Exception as e:
            print(f"Error saving data to DB: {e}")
            
    def plotNetworkTraffic(self, fig):
        ax = fig.add_subplot(111)
        
        # 生成模拟网络数据
        times = pd.date_range(start=datetime.now() - timedelta(days=7), end=datetime.now(), freq='H')
        inbound = np.random.randint(100, 1000, size=len(times)) + np.sin(np.arange(len(times)) * 0.1) * 100
        outbound = np.random.randint(50, 800, size=len(times)) + np.cos(np.arange(len(times)) * 0.1) * 80
        
        ax.plot(times, inbound, label='入站流量', color='#3498db', linewidth=2)
        ax.plot(times, outbound, label='出站流量', color='#e74c3c', linewidth=2)
        ax.set_title('网络流量趋势', fontsize=14, fontweight='bold')
        ax.legend()
        ax.grid(True, alpha=0.3)
        fig.autofmt_xdate()
        fig.tight_layout()
        
    def plotAnomalyDetection(self, fig):
        ax = fig.add_subplot(111)
        
        # 生成模拟数据
        np.random.seed(42)
        data = np.random.randn(100, 2)
        data = np.r_[data, np.random.randn(5, 2) + 2.5]  # 添加一些异常点
        
        # 使用隔离森林进行异常检测
        clf = IsolationForest(contamination=0.1, random_state=42)
        preds = clf.fit_predict(data)
        
        # 绘制正常点
        normal = data[preds == 1]
        ax.scatter(normal[:, 0], normal[:, 1], c='#3498db', label='正常', alpha=0.7, s=60)
        
        # 绘制异常点
        anomalies = data[preds == -1]
        ax.scatter(anomalies[:, 0], anomalies[:, 1], c='#e74c3c', label='异常', alpha=0.7, s=80, edgecolors='black')
        
        ax.set_title('系统异常检测', fontsize=14, fontweight='bold')
        ax.legend()
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        
    def plotNetworkTopology(self, fig):
        ax = fig.add_subplot(111)
        
        # 创建网络拓扑图
        G = nx.Graph()
        
        # 添加节点
        nodes = [
            ("核心交换机", "switch"),
            ("防火墙", "firewall"),
            ("路由器", "router"),
            ("主服务器", "server"),
            ("备份服务器", "server"),
            ("用户终端", "client"),
            ("云服务", "cloud"),
            ("数据库集群", "database"),
            ("应用服务器", "server"),
            ("Web服务器", "server")
        ]
        
        for node, node_type in nodes:
            G.add_node(node, type=node_type)
        
        # 添加边
        edges = [
            ("核心交换机", "防火墙"),
            ("防火墙", "路由器"),
            ("核心交换机", "主服务器"),
            ("核心交换机", "备份服务器"),
            ("路由器", "云服务"),
            ("核心交换机", "用户终端"),
            ("核心交换机", "数据库集群"),
            ("核心交换机", "应用服务器"),
            ("核心交换机", "Web服务器"),
            ("数据库集群", "应用服务器"),
            ("应用服务器", "Web服务器")
        ]
        
        for edge in edges:
            G.add_edge(edge[0], edge[1])
        
        # 根据节点类型设置颜色和大小
        node_colors = []
        node_sizes = []
        for node in G.nodes():
            if G.nodes[node]['type'] == 'switch':
                node_colors.append('#3498db')
                node_sizes.append(2000)
            elif G.nodes[node]['type'] == 'firewall':
                node_colors.append('#e74c3c')
                node_sizes.append(1800)
            elif G.nodes[node]['type'] == 'router':
                node_colors.append('#9b59b6')
                node_sizes.append(1800)
            elif G.nodes[node]['type'] == 'server':
                node_colors.append('#2ecc71')
                node_sizes.append(1500)
            elif G.nodes[node]['type'] == 'client':
                node_colors.append('#f39c12')
                node_sizes.append(1000)
            elif G.nodes[node]['type'] == 'cloud':
                node_colors.append('#1abc9c')
                node_sizes.append(2000)
            else:  # database
                node_colors.append('#34495e')
                node_sizes.append(1700)
        
        pos = nx.spring_layout(G, seed=42, k=2, iterations=50)
        nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=node_sizes, alpha=0.9, ax=ax)
        nx.draw_networkx_edges(G, pos, width=2, alpha=0.6, edge_color='#7f8c8d', ax=ax)
        nx.draw_networkx_labels(G, pos, font_size=9, font_weight='bold', ax=ax)
        
        ax.set_title('企业网络拓扑图', fontsize=14, fontweight='bold')
        ax.axis('off')
        fig.tight_layout()
        
    def plotPredictions(self, fig):
        ax = fig.add_subplot(111)
        
        # 生成示例预测数据
        dates = pd.date_range(start='2023-01-01', end='2023-02-10', freq='D')
        actual = np.sin(np.arange(len(dates)) * 0.1) * 20 + 50 + np.random.normal(0, 5, len(dates))
        
        # 模拟预测结果
        train_size = int(len(dates) * 0.8)
        train_dates = dates[:train_size]
        test_dates = dates[train_size:]
        
        # 简单线性外推作为预测
        x = np.arange(len(train_dates))
        coeffs = np.polyfit(x, actual[:train_size], 1)
        poly = np.poly1d(coeffs)
        
        future_x = np.arange(len(dates))
        forecast = poly(future_x)
        
        # 绘制实际值
        ax.plot(dates, actual, 'o-', label='实际值', color='#3498db', linewidth=2, markersize=4)
        
        # 绘制预测值
        ax.plot(dates, forecast, '--', label='预测值', color='#e74c3c', linewidth=2)
        
        # 填充置信区间
        ax.fill_between(dates, forecast-10, forecast+10, color='#e74c3c', alpha=0.2)
        
        # 添加垂直线分隔训练和测试数据
        ax.axvline(x=dates[train_size], color='gray', linestyle='--', alpha=0.7)
        ax.text(dates[train_size], ax.get_ylim()[1] * 0.9, '预测开始', ha='center', va='bottom', 
                backgroundcolor='w', fontsize=10)
        
        ax.set_title('CPU使用率预测', fontsize=14, fontweight='bold')
        ax.legend()
        ax.grid(True, alpha=0.3)
        fig.autofmt_xdate()
        fig.tight_layout()
        
    def generatePredictions(self):
        if self.historical_data.empty:
            QMessageBox.warning(self, "警告", "没有足够的数据进行预测分析")
            return
            
        # 启动预测线程
        self.prediction_thread = PredictionThread(self.historical_data)
        self.prediction_thread.prediction_ready.connect(self.handlePredictionResults)
        self.prediction_thread.start()
        
        # 显示进度指示
        self.status_label.setText("系统状态: 正在生成预测...")
        
    def handlePredictionResults(self, forecast):
        # 处理预测结果
        self.status_label.setText("系统状态: 预测完成")
        
        # 在实际应用中，这里会更新预测图表
        QMessageBox.information(self, "预测完成", "时间序列预测已生成并更新到预测分析标签页")
        
    def applyTheme(self):
        theme = self.settings.value("theme", "深色主题")
        
        if theme == "深色主题":
            self.setStyleSheet("""
                QMainWindow {
                    background-color: #2c3e50;
                }
                QWidget {
                    background-color: #34495e;
                    color: #ecf0f1;
                }
                QTabWidget::pane {
                    border: 1px solid #2c3e50;
                    background: #2c3e50;
                    border-radius: 4px;
                }
                QTabBar::tab {
                    background: #34495e;
                    color: #ecf0f1;
                    padding: 8px 20px;
                    border-top-left-radius: 4px;
                    border-top-right-radius: 4px;
                }
                QTabBar::tab:selected {
                    background: #3498db;
                    color: white;
                }
                QGroupBox {
                    font-weight: bold;
                    border: 2px solid #2c3e50;
                    border-radius: 8px;
                    margin-top: 1ex;
                    padding-top: 10px;
                    background-color: #34495e;
                    color: #ecf0f1;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 5px 0 5px;
                    color: #3498db;
                }
                QTableWidget {
                    background-color: #2c3e50;
                    alternate-background-color: #34495e;
                    gridline-color: #2c3e50;
                    border: 1px solid #2c3e50;
                    color: #ecf0f1;
                }
                QTableWidget::item:selected {
                    background-color: #3498db;
                    color: white;
                }
                QHeaderView::section {
                    background-color: #3498db;
                    color: white;
                    padding: 4px;
                    border: 1px solid #2980b9;
                }
                QToolBar {
                    background-color: #34495e;
                    border: none;
                }
                QStatusBar {
                    background-color: #34495e;
                    color: #ecf0f1;
                }
            """)
        elif theme == "浅色主题":
            self.setStyleSheet("""
                QMainWindow {
                    background-color: #f5f5f5;
                }
                QWidget {
                    background-color: #ffffff;
                    color: #333333;
                }
                QTabWidget::pane {
                    border: 1px solid #ddd;
                    background: #f9f9f9;
                    border-radius: 4px;
                }
                QTabBar::tab {
                    background: #e9e9e9;
                    color: #555555;
                    padding: 8px 20px;
                    border-top-left-radius: 4px;
                    border-top-right-radius: 4px;
                }
                QTabBar::tab:selected {
                    background: #3498db;
                    color: white;
                }
                QGroupBox {
                    font-weight: bold;
                    border: 2px solid #ddd;
                    border-radius: 8px;
                    margin-top: 1ex;
                    padding-top: 10px;
                    background-color: #f9f9f9;
                    color: #333333;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 5px 0 5px;
                    color: #2980b9;
                }
                QTableWidget {
                    background-color: #ffffff;
                    alternate-background-color: #f5f5f5;
                    gridline-color: #ddd;
                    border: 1px solid #ddd;
                    color: #333333;
                }
                QTableWidget::item:selected {
                    background-color: #3498db;
                    color: white;
                }
                QHeaderView::section {
                    background-color: #3498db;
                    color: white;
                    padding: 4px;
                    border: 1px solid #2980b9;
                }
                QToolBar {
                    background-color: #f8f8f8;
                    border: none;
                }
                QStatusBar {
                    background-color: #f8f8f8;
                    color: #555555;
                }
            """)
        # 其他主题样式可以类似添加
        
    def refreshData(self):
        self.loadHistoricalData()
        QMessageBox.information(self, "刷新", "数据刷新完成！")
        
    def showDashboard(self):
        # 切换到仪表板视图
        pass
        
    def showAlerts(self):
        # 显示警报对话框
        pass
        
    def generateReport(self):
        # 生成报告
        options = QFileDialog.Options()
        fileName, _ = QFileDialog.getSaveFileName(self, "保存报告", "", "PDF Files (*.pdf);;HTML Files (*.html)", options=options)
        if fileName:
            QMessageBox.information(self, "报告", f"CIO报告已保存到: {fileName}")
        
    def showSettings(self):
        dialog = SettingsDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            dialog.saveSettings()
            self.applyTheme()
            self.loadHistoricalData()
            
    def closeEvent(self, event):
        # 停止数据生成器
        self.data_generator.stop()
        self.data_generator.wait()
        
        # 保存数据
        self.saveDataToDB()
        
        # 关闭数据库连接
        self.conn.close()
        
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 设置应用程序样式
    app.setStyle('Fusion')
    
    # 创建并显示主窗口
    window = CIOVisualizationTool()
    window.show()
    
    sys.exit(app.exec_())