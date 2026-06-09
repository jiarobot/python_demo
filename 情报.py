import sys
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import networkx as nx
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QSplitter, QTabWidget, QToolBar, QAction, QStatusBar, QLabel,
                             QComboBox, QSlider, QSpinBox, QCheckBox, QPushButton, QFileDialog,
                             QMessageBox, QGraphicsView, QGraphicsScene, QGraphicsEllipseItem,
                             QGraphicsTextItem, QGraphicsLineItem, QMenu, QDockWidget, QTextEdit,
                             QListWidget, QTreeWidget, QTreeWidgetItem, QGroupBox, QFormLayout,
                             QProgressBar, QTableWidget, QTableWidgetItem, QHeaderView, QDialog,
                             QDialogButtonBox, QLineEdit, QDateTimeEdit, QDoubleSpinBox)
from PyQt5.QtCore import Qt, QTimer, QPointF, QRectF, pyqtSignal, QThread, pyqtSlot, QDateTime
from PyQt5.QtGui import QColor, QPen, QBrush, QFont, QPainter, QLinearGradient, QIcon, QPixmap, QPalette
import matplotlib.pyplot as plt
import matplotlib
matplotlib.rc("font", family='Microsoft YaHei')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from matplotlib.dates import DateFormatter
import pyqtgraph as pg
from wordcloud import WordCloud
import folium
from io import BytesIO
from PIL import Image
import requests
from sklearn.cluster import DBSCAN, KMeans
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import joblib
import json
import csv
import webbrowser
import socket
import threading
import time
from bs4 import BeautifulSoup
import tweepy
import warnings
warnings.filterwarnings('ignore')

# 设置pyqtgraph使用抗锯齿
pg.setConfigOptions(antialias=True)


class DataLoaderThread(QThread):
    """数据加载线程"""
    progress = pyqtSignal(int)
    finished = pyqtSignal(object)
    error = pyqtSignal(str)
    
    def __init__(self, data_source, params=None):
        super().__init__()
        self.data_source = data_source
        self.params = params or {}
        
    def run(self):
        try:
            if self.data_source == "synthetic":
                data = self.generate_synthetic_data()
            elif self.data_source == "csv":
                data = self.load_csv_data()
            elif self.data_source == "api":
                data = self.fetch_api_data()
            elif self.data_source == "twitter":
                data = self.fetch_twitter_data()
            elif self.data_source == "web_scrape":
                data = self.scrape_web_data()
            else:
                raise ValueError(f"未知数据源: {self.data_source}")
                
            self.finished.emit(data)
        except Exception as e:
            self.error.emit(str(e))
    
    def generate_synthetic_data(self):
        """生成合成数据"""
        # 模拟加载进度
        for i in range(101):
            self.progress.emit(i)
            time.sleep(0.02)
            
        # 生成时间序列数据
        dates = [datetime.now() - timedelta(days=i) for i in range(100)]
        values = np.random.randn(100).cumsum() + 50
        
        # 生成网络数据
        graph = nx.gnp_random_graph(20, 0.3, directed=True)
        for i, j in graph.edges():
            graph[i][j]['weight'] = np.random.rand()
            
        # 生成地理数据
        geo_data = []
        for _ in range(15):
            lat = 39.5 + np.random.rand() * 1.0
            lon = 115.5 + np.random.rand() * 1.0
            geo_data.append({"lat": lat, "lon": lon, "value": np.random.randint(1, 100)})
            
        # 生成文本数据
        sample_text = """
        人工智能 机器学习 深度学习 神经网络 自然语言处理 计算机视觉 
        数据分析 大数据 云计算 物联网 区块链 网络安全 情报分析 
        可视化 模式识别 预测分析 时间序列 网络分析 地理空间分析
        人工智能 机器学习 深度学习 神经网络 自然语言处理 计算机视觉
        数据分析 大数据 云计算 物联网 区块链 网络安全 情报分析
        """
        
        return {
            "time_series": (dates, values),
            "network": graph,
            "geo": geo_data,
            "text": sample_text
        }
    
    def load_csv_data(self):
        """加载CSV数据"""
        file_path = self.params.get("file_path")
        if not file_path:
            raise ValueError("未提供文件路径")
            
        data = pd.read_csv(file_path)
        
        # 模拟加载进度
        for i in range(101):
            self.progress.emit(i)
            time.sleep(0.01)
            
        return {"table": data}
    
    def fetch_api_data(self):
        """从API获取数据"""
        # 这里只是示例，实际应用中需要替换为真实的API调用
        url = self.params.get("url", "")
        
        # 模拟API调用
        for i in range(101):
            self.progress.emit(i)
            time.sleep(0.03)
            
        # 返回模拟数据
        dates = [datetime.now() - timedelta(hours=i) for i in range(24)]
        values = np.random.randn(24).cumsum() + 100
        
        return {"time_series": (dates, values)}
    
    def fetch_twitter_data(self):
        """获取Twitter数据"""
        # 这里需要Twitter API密钥
        # 简化实现，仅返回模拟数据
        
        for i in range(101):
            self.progress.emit(i)
            time.sleep(0.02)
            
        tweets = [
            {"text": "人工智能正在改变世界 #AI", "likes": 45, "retweets": 12},
            {"text": "网络安全是当今最大的挑战之一 #CyberSecurity", "likes": 78, "retweets": 23},
            {"text": "大数据分析提供了前所未有的洞察力 #BigData", "likes": 32, "retweets": 8},
            {"text": "机器学习算法可以预测市场趋势 #MachineLearning", "likes": 67, "retweets": 19},
            {"text": "物联网连接了物理世界和数字世界 #IoT", "likes": 54, "retweets": 15},
        ]
        
        return {"tweets": tweets}
    
    def scrape_web_data(self):
        """爬取网页数据"""
        url = self.params.get("url", "")
        
        # 模拟网页爬取
        for i in range(101):
            self.progress.emit(i)
            time.sleep(0.02)
            
        # 返回模拟数据
        return {"text": "网页内容提取的文本数据示例"}


class RealTimeDataThread(QThread):
    """实时数据线程"""
    new_data = pyqtSignal(object)
    
    def __init__(self, data_type, interval=1.0):
        super().__init__()
        self.data_type = data_type
        self.interval = interval
        self.running = False
        
    def run(self):
        self.running = True
        while self.running:
            data = self.generate_data()
            self.new_data.emit(data)
            time.sleep(self.interval)
    
    def stop(self):
        self.running = False
        
    def generate_data(self):
        """生成实时数据"""
        if self.data_type == "time_series":
            timestamp = datetime.now()
            value = np.random.randn()
            return {"timestamp": timestamp, "value": value}
        elif self.data_type == "network":
            # 随机添加或移除节点和边
            return {"action": "update", "nodes": [], "edges": []}
        else:
            return {"data": np.random.rand()}


class AdvancedTimeSeriesChart(FigureCanvas):
    """高级时间序列图表组件"""
    def __init__(self, parent=None, width=10, height=6, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        super().__init__(self.fig)
        self.setParent(parent)
        self.axes = self.fig.add_subplot(111)
        self.fig.tight_layout()
        self.setStyleSheet("background-color: white;")
        
        # 添加导航工具栏
        self.toolbar = NavigationToolbar(self, parent)
        
        # 数据存储
        self.data = {}
        self.anomalies = {}
        
    def plot_data(self, dates, values, title="时间序列分析", xlabel="时间", ylabel="数值", label="数据"):
        """绘制时间序列数据"""
        self.axes.clear()
        line, = self.axes.plot(dates, values, '-o', linewidth=2, markersize=4, label=label)
        self.axes.set_title(title, fontsize=14, fontweight='bold')
        self.axes.set_xlabel(xlabel)
        self.axes.set_ylabel(ylabel)
        self.axes.grid(True, linestyle='--', alpha=0.7)
        self.axes.xaxis.set_major_formatter(DateFormatter('%Y-%m-%d'))
        self.fig.autofmt_xdate()
        
        # 存储数据
        self.data[label] = (dates, values, line)
        
        # 如果有异常点，也绘制出来
        if label in self.anomalies:
            anomaly_dates, anomaly_values = self.anomalies[label]
            self.axes.plot(anomaly_dates, anomaly_values, 'ro', markersize=8, label=f"{label}异常点")
        
        self.axes.legend()
        self.draw()
        
    def add_anomalies(self, dates, values, label="数据"):
        """添加异常点标记"""
        self.anomalies[label] = (dates, values)
        
        # 如果数据已经存在，重新绘制
        if label in self.data:
            self.plot_data(self.data[label][0], self.data[label][1], label=label)
            
    def clear_anomalies(self, label=None):
        """清除异常点标记"""
        if label is None:
            self.anomalies.clear()
        elif label in self.anomalies:
            del self.anomalies[label]
            
        # 重新绘制所有数据
        for label, (dates, values, _) in self.data.items():
            self.plot_data(dates, values, label=label)
            
    def apply_moving_average(self, window_size=5, label="数据"):
        """应用移动平均平滑"""
        if label not in self.data:
            return
            
        dates, values, _ = self.data[label]
        values_series = pd.Series(values)
        moving_avg = values_series.rolling(window=window_size).mean()
        
        # 绘制移动平均线
        self.axes.plot(dates, moving_avg, '--', linewidth=2, label=f"{label}移动平均")
        self.axes.legend()
        self.draw()


class InteractiveNetworkGraphView(QGraphicsView):
    """交互式网络关系图组件"""
    node_clicked = pyqtSignal(str, dict)
    edge_clicked = pyqtSignal(tuple, dict)
    background_clicked = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene()
        self.setScene(self.scene)
        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.scale_factor = 1.0
        self.nodes = {}
        self.edges = {}
        self.graph = None
        self.layout = 'spring'
        
        # 社区检测颜色
        self.community_colors = [
            QColor(255, 0, 0), QColor(0, 255, 0), QColor(0, 0, 255),
            QColor(255, 255, 0), QColor(255, 0, 255), QColor(0, 255, 255),
            QColor(128, 0, 0), QColor(0, 128, 0), QColor(0, 0, 128),
            QColor(128, 128, 0), QColor(128, 0, 128), QColor(0, 128, 128)
        ]
        
    def wheelEvent(self, event):
        """鼠标滚轮缩放"""
        factor = 1.2
        if event.angleDelta().y() < 0:
            factor = 1.0 / factor
        self.scale(factor, factor)
        self.scale_factor *= factor
        
    def draw_network(self, graph, layout='spring', detect_communities=False):
        """绘制网络图"""
        self.scene.clear()
        self.nodes.clear()
        self.edges.clear()
        self.graph = graph
        self.layout = layout
        
        # 计算布局
        if layout == 'spring':
            pos = nx.spring_layout(graph, k=3/np.sqrt(graph.order()), iterations=50)
        elif layout == 'circular':
            pos = nx.circular_layout(graph)
        elif layout == 'kamada_kawai':
            pos = nx.kamada_kawai_layout(graph)
        elif layout == 'spectral':
            pos = nx.spectral_layout(graph)
        else:
            pos = nx.spring_layout(graph)
        
        # 检测社区
        communities = {}
        if detect_communities and graph.number_of_nodes() > 0:
            try:
                # 使用Louvain方法检测社区
                import community as community_louvain
                partition = community_louvain.best_partition(graph)
                communities = partition
            except:
                # 如果社区检测失败，使用简单的连通组件
                communities = {}
                for i, comp in enumerate(nx.connected_components(graph)):
                    for node in comp:
                        communities[node] = i
        
        # 绘制边
        for edge in graph.edges(data=True):
            n1, n2, attr = edge
            x1, y1 = pos[n1]
            x2, y2 = pos[n2]
            
            # 调整坐标到视图中心
            x1 = (x1 + 1) * 300
            y1 = (y1 + 1) * 300
            x2 = (x2 + 1) * 300
            y2 = (y2 + 1) * 300
            
            # 根据权重设置边的粗细
            weight = attr.get('weight', 1.0)
            pen_width = max(1, min(5, int(weight * 3)))
            
            line = QGraphicsLineItem(x1, y1, x2, y2)
            line.setPen(QPen(QColor(100, 100, 100), pen_width))
            line.setData(0, (n1, n2))  # 存储边标识
            line.setZValue(0)  # 边在底层
            
            self.scene.addItem(line)
            self.edges[(n1, n2)] = line
            
            # 使边可点击
            line.setFlag(QGraphicsLineItem.ItemIsSelectable)
        
        # 绘制节点
        for node, (x, y) in pos.items():
            x = (x + 1) * 300
            y = (y + 1) * 300
            
            # 根据节点度决定大小
            degree = graph.degree(node)
            size = 20 + degree * 3
            
            # 选择节点颜色
            if node in communities:
                color_idx = communities[node] % len(self.community_colors)
                color = self.community_colors[color_idx]
            else:
                color = QColor(65, 105, 225)  # 默认蓝色
            
            # 创建节点
            ellipse = QGraphicsEllipseItem(QRectF(-size/2, -size/2, size, size))
            ellipse.setPos(x, y)
            ellipse.setBrush(QBrush(color))
            ellipse.setPen(QPen(Qt.black, 1))
            ellipse.setData(0, node)  # 存储节点标识
            ellipse.setZValue(1)  # 节点在顶层
            
            # 添加节点标签
            text = QGraphicsTextItem(str(node))
            text.setPos(x - text.boundingRect().width()/2, y + size/2 + 5)
            text.setFont(QFont("Arial", 8))
            text.setZValue(2)  # 文本在最顶层
            
            self.scene.addItem(ellipse)
            self.scene.addItem(text)
            self.nodes[node] = (ellipse, text)
            
            # 使节点可点击
            ellipse.setFlag(QGraphicsEllipseItem.ItemIsSelectable)
            
    def mousePressEvent(self, event):
        """处理鼠标点击事件"""
        if event.button() == Qt.RightButton:
            self._right_click_menu(event.pos())
        else:
            # 获取点击的项目
            item = self.itemAt(event.pos())
            if item is None:
                self.background_clicked.emit()
            elif hasattr(item, 'data') and item.data(0) is not None:
                if isinstance(item, QGraphicsEllipseItem):
                    # 点击了节点
                    node = item.data(0)
                    node_data = {"degree": self.graph.degree(node)}
                    if node in self.graph.nodes:
                        node_data.update(self.graph.nodes[node])
                    self.node_clicked.emit(node, node_data)
                elif isinstance(item, QGraphicsLineItem):
                    # 点击了边
                    edge = item.data(0)
                    edge_data = self.graph.get_edge_data(edge[0], edge[1])
                    self.edge_clicked.emit(edge, edge_data)
            super().mousePressEvent(event)
            
    def _right_click_menu(self, pos):
        """右键菜单"""
        menu = QMenu()
        reset_action = menu.addAction("重置视图")
        center_action = menu.addAction("居中视图")
        community_action = menu.addAction("检测社区")
        layout_menu = menu.addMenu("布局算法")
        
        spring_action = layout_menu.addAction("Spring")
        circular_action = layout_menu.addAction("Circular")
        kamada_action = layout_menu.addAction("Kamada-Kawai")
        spectral_action = layout_menu.addAction("Spectral")
        
        action = menu.exec_(self.mapToGlobal(pos))
        
        if action == reset_action:
            self.reset_view()
        elif action == center_action:
            self.centerOn(self.scene.itemsBoundingRect().center())
        elif action == community_action:
            self.detect_communities()
        elif action == spring_action:
            self.apply_layout('spring')
        elif action == circular_action:
            self.apply_layout('circular')
        elif action == kamada_action:
            self.apply_layout('kamada_kawai')
        elif action == spectral_action:
            self.apply_layout('spectral')
            
    def reset_view(self):
        """重置视图"""
        self.resetTransform()
        self.scale_factor = 1.0
        self.centerOn(self.scene.itemsBoundingRect().center())
        
    def detect_communities(self):
        """检测并显示社区"""
        if self.graph:
            self.draw_network(self.graph, self.layout, detect_communities=True)
            
    def apply_layout(self, layout):
        """应用新的布局算法"""
        if self.graph:
            self.draw_network(self.graph, layout, detect_communities=False)


class AdvancedGeoMapView(QWidget):
    """高级地理地图视图组件"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.browser = None
        self.map = None
        self.markers = []
        self.circles = []
        self.init_ui()
        
    def init_ui(self):
        """初始化UI"""
        # 创建工具栏
        toolbar = QToolBar()
        self.zoom_in_btn = QPushButton("放大")
        self.zoom_out_btn = QPushButton("缩小")
        self.reset_btn = QPushButton("重置")
        self.heatmap_btn = QPushButton("热力图")
        self.cluster_btn = QPushButton("聚类分析")
        
        toolbar.addWidget(self.zoom_in_btn)
        toolbar.addWidget(self.zoom_out_btn)
        toolbar.addWidget(self.reset_btn)
        toolbar.addWidget(self.heatmap_btn)
        toolbar.addWidget(self.cluster_btn)
        
        self.layout.addWidget(toolbar)
        
        # 连接信号
        self.zoom_in_btn.clicked.connect(self.zoom_in)
        self.zoom_out_btn.clicked.connect(self.zoom_out)
        self.reset_btn.clicked.connect(self.reset_view)
        self.heatmap_btn.clicked.connect(self.toggle_heatmap)
        self.cluster_btn.clicked.connect(self.cluster_analysis)
        
    def create_map(self, center=[39.9042, 116.4074], zoom_start=10):
        """创建地图"""
        self.map = folium.Map(location=center, zoom_start=zoom_start, tiles='OpenStreetMap')
        
    def add_marker(self, location, popup_text, tooltip_text="", icon_color='blue'):
        """添加标记"""
        if self.map:
            folium.Marker(
                location=location,
                popup=popup_text,
                tooltip=tooltip_text,
                icon=folium.Icon(color=icon_color)
            ).add_to(self.map)
            self.markers.append({
                "location": location,
                "popup": popup_text,
                "tooltip": tooltip_text,
                "color": icon_color
            })
            
    def add_circle(self, location, radius, color='red', fill=True, fill_color=None, popup_text=""):
        """添加圆形区域"""
        if self.map:
            if fill_color is None:
                fill_color = color
                
            folium.Circle(
                location=location,
                radius=radius,
                color=color,
                fill=fill,
                fill_color=fill_color,
                popup=popup_text
            ).add_to(self.map)
            self.circles.append({
                "location": location,
                "radius": radius,
                "color": color,
                "fill": fill,
                "fill_color": fill_color,
                "popup": popup_text
            })
            
    def add_heatmap(self, data, radius=15, blur=10, max_zoom=1):
        """添加热力图"""
        if self.map:
            from folium.plugins import HeatMap
            
            heat_data = [[point['lat'], point['lon'], point.get('value', 1)] for point in data]
            HeatMap(heat_data, radius=radius, blur=blur, max_zoom=max_zoom).add_to(self.map)
            
    def show_map(self):
        """显示地图"""
        if self.map:
            # 将地图保存为HTML
            self.map.save('temp_map.html')
            
            # 创建浏览器视图显示地图
            if self.browser:
                self.layout.removeWidget(self.browser)
                self.browser.deleteLater()
                
            self.browser = QLabel()
            self.browser.setText('<iframe src="temp_map.html" width="100%" height="500"></iframe>')
            self.browser.setOpenExternalLinks(True)
            self.layout.addWidget(self.browser)
            
    def zoom_in(self):
        """放大地图"""
        if self.map:
            current_zoom = self.map.options['zoom']
            self.map.options['zoom'] = current_zoom + 1
            self.show_map()
            
    def zoom_out(self):
        """缩小地图"""
        if self.map:
            current_zoom = self.map.options['zoom']
            self.map.options['zoom'] = max(1, current_zoom - 1)
            self.show_map()
            
    def reset_view(self):
        """重置视图"""
        if self.map:
            self.map.options['zoom'] = 10
            self.map.options['center'] = [39.9042, 116.4074]
            self.show_map()
            
    def toggle_heatmap(self):
        """切换热力图显示"""
        # 这里需要实现热力图的切换逻辑
        QMessageBox.information(self, "信息", "热力图功能待实现")
        
    def cluster_analysis(self):
        """地理聚类分析"""
        if not self.markers:
            QMessageBox.warning(self, "警告", "没有地理数据进行聚类分析")
            return
            
        # 提取坐标数据
        coords = np.array([m["location"] for m in self.markers])
        
        # 使用DBSCAN进行聚类
        dbscan = DBSCAN(eps=0.1, min_samples=2)
        clusters = dbscan.fit_predict(coords)
        
        # 为每个聚类添加圆形区域
        unique_clusters = set(clusters)
        for cluster_id in unique_clusters:
            if cluster_id == -1:  # 噪声点
                continue
                
            cluster_points = coords[clusters == cluster_id]
            center = cluster_points.mean(axis=0)
            radius = np.max(np.linalg.norm(cluster_points - center, axis=1)) * 100000  # 转换为米
            
            self.add_circle(
                location=center.tolist(),
                radius=radius,
                color='blue',
                fill=True,
                fill_color='blue',
                popup_text=f"聚类 {cluster_id}: {len(cluster_points)}个点"
            )
            
        self.show_map()


class AdvancedWordCloudView(FigureCanvas):
    """高级词云可视化组件"""
    def __init__(self, parent=None, width=10, height=6, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        super().__init__(self.fig)
        self.setParent(parent)
        self.axes = self.fig.add_subplot(111)
        self.fig.tight_layout()
        self.setStyleSheet("background-color: white;")
        
        # 添加导航工具栏
        self.toolbar = NavigationToolbar(self, parent)
        
    def generate_wordcloud(self, text, max_words=100, background_color='white', 
                          colormap='viridis', width=800, height=400):
        """生成词云"""
        self.axes.clear()
        
        # 生成词云
        wordcloud = WordCloud(
            width=width, 
            height=height,
            background_color=background_color,
            max_words=max_words,
            colormap=colormap
        ).generate(text)
        
        # 显示词云
        self.axes.imshow(wordcloud, interpolation='bilinear')
        self.axes.axis('off')
        self.axes.set_title('关键词词云', fontsize=14, fontweight='bold')
        self.draw()


class DataTableWidget(QTableWidget):
    """数据表格组件"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setEditTriggers(QTableWidget.NoEditTriggers)
        self.setSelectionBehavior(QTableWidget.SelectRows)
        self.setAlternatingRowColors(True)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
    def load_data(self, data):
        """加载数据到表格"""
        if isinstance(data, pd.DataFrame):
            self.setRowCount(data.shape[0])
            self.setColumnCount(data.shape[1])
            self.setHorizontalHeaderLabels(data.columns)
            
            for i in range(data.shape[0]):
                for j in range(data.shape[1]):
                    item = QTableWidgetItem(str(data.iloc[i, j]))
                    self.setItem(i, j, item)
        elif isinstance(data, list):
            if len(data) == 0:
                return
                
            # 获取所有键作为列名
            columns = list(data[0].keys())
            self.setColumnCount(len(columns))
            self.setHorizontalHeaderLabels(columns)
            self.setRowCount(len(data))
            
            for i, row in enumerate(data):
                for j, col in enumerate(columns):
                    item = QTableWidgetItem(str(row.get(col, "")))
                    self.setItem(i, j, item)


class AnalyticsEngine:
    """分析引擎"""
    def __init__(self):
        self.models = {}
        
    def detect_anomalies(self, data, method='isolation_forest', **kwargs):
        """异常检测"""
        if method == 'isolation_forest':
            return self._isolation_forest(data, **kwargs)
        elif method == 'z_score':
            return self._z_score(data, **kwargs)
        else:
            raise ValueError(f"未知异常检测方法: {method}")
            
    def _isolation_forest(self, data, contamination=0.1):
        """使用孤立森林进行异常检测"""
        if isinstance(data, pd.Series):
            data = data.values.reshape(-1, 1)
        elif isinstance(data, list):
            data = np.array(data).reshape(-1, 1)
            
        clf = IsolationForest(contamination=contamination, random_state=42)
        predictions = clf.fit_predict(data)
        
        # -1表示异常，1表示正常
        anomalies = np.where(predictions == -1)[0]
        return anomalies
    
    def _z_score(self, data, threshold=3.0):
        """使用Z分数进行异常检测"""
        if isinstance(data, pd.Series):
            data = data.values
        elif isinstance(data, list):
            data = np.array(data)
            
        mean = np.mean(data)
        std = np.std(data)
        z_scores = np.abs((data - mean) / std)
        
        anomalies = np.where(z_scores > threshold)[0]
        return anomalies
        
    def cluster_data(self, data, method='kmeans', **kwargs):
        """聚类分析"""
        if method == 'kmeans':
            return self._kmeans_clustering(data, **kwargs)
        elif method == 'dbscan':
            return self._dbscan_clustering(data, **kwargs)
        else:
            raise ValueError(f"未知聚类方法: {method}")
            
    def _kmeans_clustering(self, data, n_clusters=3):
        """K均值聚类"""
        if isinstance(data, pd.DataFrame):
            data = data.values
        elif isinstance(data, list):
            data = np.array(data)
            
        # 标准化数据
        scaler = StandardScaler()
        data_scaled = scaler.fit_transform(data)
        
        kmeans = KMeans(n_clusters=n_clusters, random_state=42)
        clusters = kmeans.fit_predict(data_scaled)
        
        return clusters, kmeans.cluster_centers_
    
    def _dbscan_clustering(self, data, eps=0.5, min_samples=5):
        """DBSCAN聚类"""
        if isinstance(data, pd.DataFrame):
            data = data.values
        elif isinstance(data, list):
            data = np.array(data)
            
        # 标准化数据
        scaler = StandardScaler()
        data_scaled = scaler.fit_transform(data)
        
        dbscan = DBSCAN(eps=eps, min_samples=min_samples)
        clusters = dbscan.fit_predict(data_scaled)
        
        return clusters
    
    def train_model(self, X, y, model_type='random_forest', **kwargs):
        """训练机器学习模型"""
        if model_type == 'random_forest':
            from sklearn.ensemble import RandomForestClassifier
            model = RandomForestClassifier(**kwargs)
        elif model_type == 'logistic_regression':
            from sklearn.linear_model import LogisticRegression
            model = LogisticRegression(**kwargs)
        else:
            raise ValueError(f"未知模型类型: {model_type}")
            
        model.fit(X, y)
        return model
    
    def predict(self, model, X):
        """使用模型进行预测"""
        return model.predict(X)


class SettingsDialog(QDialog):
    """设置对话框"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置")
        self.setModal(True)
        self.init_ui()
        
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        
        # API设置
        api_group = QGroupBox("API设置")
        api_layout = QFormLayout(api_group)
        
        self.twitter_key_edit = QLineEdit()
        self.twitter_secret_edit = QLineEdit()
        self.mapbox_key_edit = QLineEdit()
        
        api_layout.addRow("Twitter API密钥:", self.twitter_key_edit)
        api_layout.addRow("Twitter API密钥密钥:", self.twitter_secret_edit)
        api_layout.addRow("Mapbox访问令牌:", self.mapbox_key_edit)
        
        # 可视化设置
        viz_group = QGroupBox("可视化设置")
        viz_layout = QFormLayout(viz_group)
        
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["浅色", "深色", "系统"])
        
        self.animation_check = QCheckBox("启用动画")
        self.animation_check.setChecked(True)
        
        viz_layout.addRow("主题:", self.theme_combo)
        viz_layout.addRow(self.animation_check)
        
        # 数据分析设置
        data_group = QGroupBox("数据分析设置")
        data_layout = QFormLayout(data_group)
        
        self.auto_analyze_check = QCheckBox("自动分析新数据")
        self.auto_analyze_check.setChecked(True)
        
        self.anomaly_threshold = QDoubleSpinBox()
        self.anomaly_threshold.setRange(1.0, 5.0)
        self.anomaly_threshold.setValue(3.0)
        self.anomaly_threshold.setSingleStep(0.1)
        
        data_layout.addRow(self.auto_analyze_check)
        data_layout.addRow("异常检测阈值(Z分数):", self.anomaly_threshold)
        
        # 按钮
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        
        layout.addWidget(api_group)
        layout.addWidget(viz_group)
        layout.addWidget(data_group)
        layout.addWidget(button_box)
        
    def get_settings(self):
        """获取设置"""
        return {
            "twitter_api_key": self.twitter_key_edit.text(),
            "twitter_api_secret": self.twitter_secret_edit.text(),
            "mapbox_token": self.mapbox_key_edit.text(),
            "theme": self.theme_combo.currentText(),
            "animation": self.animation_check.isChecked(),
            "auto_analyze": self.auto_analyze_check.isChecked(),
            "anomaly_threshold": self.anomaly_threshold.value()
        }
        
    def set_settings(self, settings):
        """设置对话框值"""
        self.twitter_key_edit.setText(settings.get("twitter_api_key", ""))
        self.twitter_secret_edit.setText(settings.get("twitter_api_secret", ""))
        self.mapbox_key_edit.setText(settings.get("mapbox_token", ""))
        
        theme_index = self.theme_combo.findText(settings.get("theme", "浅色"))
        if theme_index >= 0:
            self.theme_combo.setCurrentIndex(theme_index)
            
        self.animation_check.setChecked(settings.get("animation", True))
        self.auto_analyze_check.setChecked(settings.get("auto_analyze", True))
        self.anomaly_threshold.setValue(settings.get("anomaly_threshold", 3.0))


class AdvancedIntelligenceDashboard(QMainWindow):
    """高级情报可视化主仪表板"""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("高级情报可视化分析工具")
        self.setGeometry(100, 100, 1800, 1000)
        
        # 初始化数据
        self.data = {}
        self.settings = {
            "twitter_api_key": "",
            "twitter_api_secret": "",
            "mapbox_token": "",
            "theme": "浅色",
            "animation": True,
            "auto_analyze": True,
            "anomaly_threshold": 3.0
        }
        
        # 初始化分析引擎
        self.analytics = AnalyticsEngine()
        
        # 初始化UI
        self.init_ui()
        
        # 加载示例数据
        self.load_sample_data()
        
    def init_ui(self):
        """初始化用户界面"""
        # 创建中央部件和主布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        
        # 创建左侧控制面板
        control_panel = self.create_control_panel()
        splitter.addWidget(control_panel)
        
        # 创建右侧可视化区域
        visualization_area = self.create_visualization_area()
        splitter.addWidget(visualization_area)
        
        # 设置分割器比例
        splitter.setSizes([400, 1400])
        
        main_layout.addWidget(splitter)
        
        # 创建状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪")
        
        # 创建进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(200)
        self.progress_bar.setVisible(False)
        self.status_bar.addPermanentWidget(self.progress_bar)
        
        # 创建菜单栏
        self.create_menus()
        
        # 创建停靠窗口
        self.create_dock_windows()
        
        # 应用主题
        self.apply_theme(self.settings["theme"])
        
    def create_control_panel(self):
        """创建控制面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # 数据源选择
        source_group = QGroupBox("数据源")
        source_layout = QVBoxLayout(source_group)
        
        self.source_combo = QComboBox()
        self.source_combo.addItems(["合成数据", "CSV文件", "API数据", "Twitter数据", "网页爬取"])
        source_layout.addWidget(self.source_combo)
        
        self.source_params = QWidget()
        self.source_params_layout = QVBoxLayout(self.source_params)
        source_layout.addWidget(self.source_params)
        
        self.update_source_params()
        
        self.source_combo.currentTextChanged.connect(self.update_source_params)
        
        load_btn = QPushButton("加载数据")
        load_btn.clicked.connect(self.load_data)
        source_layout.addWidget(load_btn)
        
        layout.addWidget(source_group)
        
        # 实时数据控制
        realtime_group = QGroupBox("实时数据")
        realtime_layout = QVBoxLayout(realtime_group)
        
        self.realtime_check = QCheckBox("启用实时数据流")
        self.realtime_check.stateChanged.connect(self.toggle_realtime_data)
        
        self.realtime_interval = QSpinBox()
        self.realtime_interval.setRange(1, 60)
        self.realtime_interval.setValue(5)
        self.realtime_interval.setSuffix(" 秒")
        
        realtime_layout.addWidget(self.realtime_check)
        realtime_layout.addWidget(QLabel("更新间隔:"))
        realtime_layout.addWidget(self.realtime_interval)
        
        layout.addWidget(realtime_group)
        
        # 分析工具
        analysis_group = QGroupBox("分析工具")
        analysis_layout = QVBoxLayout(analysis_group)
        
        anomaly_btn = QPushButton("异常检测")
        anomaly_btn.clicked.connect(self.detect_anomalies)
        analysis_layout.addWidget(anomaly_btn)
        
        cluster_btn = QPushButton("聚类分析")
        cluster_btn.clicked.connect(self.cluster_analysis)
        analysis_layout.addWidget(cluster_btn)
        
        pattern_btn = QPushButton("模式识别")
        pattern_btn.clicked.connect(self.pattern_recognition)
        analysis_layout.addWidget(pattern_btn)
        
        forecast_btn = QPushButton("预测分析")
        forecast_btn.clicked.connect(self.forecast_analysis)
        analysis_layout.addWidget(forecast_btn)
        
        layout.addWidget(analysis_group)
        
        # 可视化选项
        viz_group = QGroupBox("可视化选项")
        viz_layout = QVBoxLayout(viz_group)
        
        # 时间序列选项
        ts_options = QGroupBox("时间序列")
        ts_layout = QVBoxLayout(ts_options)
        
        self.ts_smoothing = QCheckBox("启用平滑")
        self.ts_smoothing.stateChanged.connect(self.update_time_series)
        
        self.ts_trendline = QCheckBox("显示趋势线")
        self.ts_trendline.stateChanged.connect(self.update_time_series)
        
        ts_layout.addWidget(self.ts_smoothing)
        ts_layout.addWidget(self.ts_trendline)
        
        viz_layout.addWidget(ts_options)
        
        # 网络图选项
        net_options = QGroupBox("网络图")
        net_layout = QVBoxLayout(net_options)
        
        self.net_layout_combo = QComboBox()
        self.net_layout_combo.addItems(["Spring", "Circular", "Kamada-Kawai", "Spectral"])
        self.net_layout_combo.currentTextChanged.connect(self.update_network_layout)
        
        self.community_detection = QCheckBox("社区检测")
        self.community_detection.stateChanged.connect(self.update_network_communities)
        
        net_layout.addWidget(QLabel("布局算法:"))
        net_layout.addWidget(self.net_layout_combo)
        net_layout.addWidget(self.community_detection)
        
        viz_layout.addWidget(net_options)
        
        layout.addWidget(viz_group)
        
        # 添加弹性空间
        layout.addStretch()
        
        return panel
    
    def update_source_params(self):
        """更新数据源参数界面"""
        # 清空现有参数控件
        for i in reversed(range(self.source_params_layout.count())): 
            self.source_params_layout.itemAt(i).widget().setParent(None)
        
        source_type = self.source_combo.currentText()
        
        if source_type == "CSV文件":
            file_btn = QPushButton("选择文件")
            file_btn.clicked.connect(self.select_file)
            self.source_params_layout.addWidget(file_btn)
            
            self.file_label = QLabel("未选择文件")
            self.source_params_layout.addWidget(self.file_label)
            
        elif source_type == "API数据":
            url_edit = QLineEdit()
            url_edit.setPlaceholderText("输入API URL")
            self.source_params_layout.addWidget(QLabel("API URL:"))
            self.source_params_layout.addWidget(url_edit)
            
        elif source_type == "Twitter数据":
            query_edit = QLineEdit()
            query_edit.setPlaceholderText("输入搜索查询")
            self.source_params_layout.addWidget(QLabel("搜索查询:"))
            self.source_params_layout.addWidget(query_edit)
            
            count_spin = QSpinBox()
            count_spin.setRange(1, 100)
            count_spin.setValue(10)
            self.source_params_layout.addWidget(QLabel("推文数量:"))
            self.source_params_layout.addWidget(count_spin)
            
        elif source_type == "网页爬取":
            url_edit = QLineEdit()
            url_edit.setPlaceholderText("输入网页URL")
            self.source_params_layout.addWidget(QLabel("网页URL:"))
            self.source_params_layout.addWidget(url_edit)
    
    def select_file(self):
        """选择文件"""
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(
            self, "选择数据文件", "", 
            "CSV文件 (*.csv);;文本文件 (*.txt);;所有文件 (*)", 
            options=options
        )
        
        if file_name:
            self.file_label.setText(file_name)
    
    def create_visualization_area(self):
        """创建可视化区域"""
        area = QTabWidget()
        
        # 时间序列标签页
        self.time_series_tab = QWidget()
        ts_layout = QVBoxLayout(self.time_series_tab)
        self.time_series_chart = AdvancedTimeSeriesChart(self.time_series_tab, width=12, height=8)
        ts_layout.addWidget(self.time_series_chart.toolbar)
        ts_layout.addWidget(self.time_series_chart)
        area.addTab(self.time_series_tab, "时间序列分析")
        
        # 网络分析标签页
        self.network_tab = QWidget()
        net_layout = QVBoxLayout(self.network_tab)
        self.network_view = InteractiveNetworkGraphView(self.network_tab)
        net_layout.addWidget(self.network_view)
        area.addTab(self.network_tab, "网络关系分析")
        
        # 地理空间标签页
        self.geo_tab = QWidget()
        geo_layout = QVBoxLayout(self.geo_tab)
        self.geo_map = AdvancedGeoMapView(self.geo_tab)
        geo_layout.addWidget(self.geo_map)
        area.addTab(self.geo_tab, "地理空间分析")
        
        # 文本分析标签页
        self.text_analysis_tab = QWidget()
        text_layout = QVBoxLayout(self.text_analysis_tab)
        self.word_cloud = AdvancedWordCloudView(self.text_analysis_tab, width=12, height=8)
        text_layout.addWidget(self.word_cloud.toolbar)
        text_layout.addWidget(self.word_cloud)
        area.addTab(self.text_analysis_tab, "文本分析")
        
        # 数据表格标签页
        self.data_table_tab = QWidget()
        table_layout = QVBoxLayout(self.data_table_tab)
        self.data_table = DataTableWidget()
        table_layout.addWidget(self.data_table)
        area.addTab(self.data_table_tab, "数据表格")
        
        # 高级分析标签页
        self.advanced_tab = QWidget()
        advanced_layout = QVBoxLayout(self.advanced_tab)
        advanced_layout.addWidget(QLabel("高级分析功能"))
        area.addTab(self.advanced_tab, "高级分析")
        
        return area
        
    def create_menus(self):
        """创建菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu("文件")
        
        load_action = QAction("加载数据", self)
        load_action.triggered.connect(self.load_data)
        file_menu.addAction(load_action)
        
        export_action = QAction("导出结果", self)
        export_action.triggered.connect(self.export_visualization)
        file_menu.addAction(export_action)
        
        settings_action = QAction("设置", self)
        settings_action.triggered.connect(self.show_settings)
        file_menu.addAction(settings_action)
        
        exit_action = QAction("退出", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 视图菜单
        view_menu = menubar.addMenu("视图")
        
        ts_action = QAction("时间序列", self)
        ts_action.triggered.connect(lambda: self.centralWidget().findChild(QTabWidget).setCurrentIndex(0))
        view_menu.addAction(ts_action)
        
        net_action = QAction("网络分析", self)
        net_action.triggered.connect(lambda: self.centralWidget().findChild(QTabWidget).setCurrentIndex(1))
        view_menu.addAction(net_action)
        
        geo_action = QAction("地理空间", self)
        geo_action.triggered.connect(lambda: self.centralWidget().findChild(QTabWidget).setCurrentIndex(2))
        view_menu.addAction(geo_action)
        
        text_action = QAction("文本分析", self)
        text_action.triggered.connect(lambda: self.centralWidget().findChild(QTabWidget).setCurrentIndex(3))
        view_menu.addAction(text_action)
        
        table_action = QAction("数据表格", self)
        table_action.triggered.connect(lambda: self.centralWidget().findChild(QTabWidget).setCurrentIndex(4))
        view_menu.addAction(table_action)
        
        # 工具菜单
        tools_menu = menubar.addMenu("工具")
        
        anomaly_action = QAction("异常检测", self)
        anomaly_action.triggered.connect(self.detect_anomalies)
        tools_menu.addAction(anomaly_action)
        
        cluster_action = QAction("聚类分析", self)
        cluster_action.triggered.connect(self.cluster_analysis)
        tools_menu.addAction(cluster_action)
        
        pattern_action = QAction("模式识别", self)
        pattern_action.triggered.connect(self.pattern_recognition)
        tools_menu.addAction(pattern_action)
        
        forecast_action = QAction("预测分析", self)
        forecast_action.triggered.connect(self.forecast_analysis)
        tools_menu.addAction(forecast_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu("帮助")
        
        docs_action = QAction("文档", self)
        docs_action.triggered.connect(self.show_documentation)
        help_menu.addAction(docs_action)
        
        about_action = QAction("关于", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
    def create_dock_windows(self):
        """创建停靠窗口"""
        # 数据详情停靠窗口
        self.details_dock = QDockWidget("数据详情", self)
        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_dock.setWidget(self.details_text)
        self.addDockWidget(Qt.RightDockWidgetArea, self.details_dock)
        
        # 分析结果停靠窗口
        self.results_dock = QDockWidget("分析结果", self)
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_dock.setWidget(self.results_text)
        self.addDockWidget(Qt.RightDockWidgetArea, self.results_dock)
        
        # 日志停靠窗口
        self.log_dock = QDockWidget("日志", self)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_dock.setWidget(self.log_text)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.log_dock)
        
    def load_sample_data(self):
        """加载示例数据"""
        self.log_message("正在加载示例数据...")
        
        # 使用线程加载数据
        self.loader_thread = DataLoaderThread("synthetic")
        self.loader_thread.progress.connect(self.progress_bar.setValue)
        self.loader_thread.finished.connect(self.on_data_loaded)
        self.loader_thread.error.connect(self.on_data_error)
        self.loader_thread.start()
        
        self.progress_bar.setVisible(True)
        
    def load_data(self):
        """加载数据"""
        source_type = self.source_combo.currentText()
        
        if source_type == "合成数据":
            data_source = "synthetic"
            params = {}
        elif source_type == "CSV文件":
            if not hasattr(self, 'file_label') or self.file_label.text() == "未选择文件":
                QMessageBox.warning(self, "警告", "请先选择CSV文件")
                return
            data_source = "csv"
            params = {"file_path": self.file_label.text()}
        elif source_type == "API数据":
            data_source = "api"
            params = {"url": ""}  # 实际应用中应该从UI获取URL
        elif source_type == "Twitter数据":
            data_source = "twitter"
            params = {}  # 实际应用中应该从UI获取查询参数
        elif source_type == "网页爬取":
            data_source = "web_scrape"
            params = {"url": ""}  # 实际应用中应该从UI获取URL
        else:
            QMessageBox.warning(self, "警告", "未知数据源类型")
            return
            
        self.log_message(f"正在从{source_type}加载数据...")
        
        # 使用线程加载数据
        self.loader_thread = DataLoaderThread(data_source, params)
        self.loader_thread.progress.connect(self.progress_bar.setValue)
        self.loader_thread.finished.connect(self.on_data_loaded)
        self.loader_thread.error.connect(self.on_data_error)
        self.loader_thread.start()
        
        self.progress_bar.setVisible(True)
        
    @pyqtSlot(object)
    def on_data_loaded(self, data):
        """数据加载完成"""
        self.data.update(data)
        self.progress_bar.setVisible(False)
        self.status_bar.showMessage("数据加载完成")
        self.log_message("数据加载完成")
        
        # 更新可视化
        self.update_visualizations()
        
        # 自动分析数据（如果设置启用）
        if self.settings["auto_analyze"]:
            self.detect_anomalies()
        
    @pyqtSlot(str)
    def on_data_error(self, error_msg):
        """数据加载错误"""
        self.progress_bar.setVisible(False)
        self.status_bar.showMessage(f"数据加载错误: {error_msg}")
        self.log_message(f"错误: {error_msg}")
        QMessageBox.critical(self, "错误", f"数据加载失败: {error_msg}")
        
    def update_visualizations(self):
        """更新所有可视化"""
        # 更新时间序列图表
        if "time_series" in self.data:
            dates, values = self.data["time_series"]
            self.time_series_chart.plot_data(dates, values, "时间序列数据")
        
        # 更新网络图
        if "network" in self.data:
            layout = self.net_layout_combo.currentText().lower().replace('-', '_')
            detect_communities = self.community_detection.isChecked()
            self.network_view.draw_network(self.data["network"], layout, detect_communities)
            
        # 更新地理地图
        if "geo" in self.data:
            self.geo_map.create_map()
            for point in self.data["geo"]:
                self.geo_map.add_marker(
                    [point["lat"], point["lon"]], 
                    f"值: {point.get('value', 'N/A')}",
                    icon_color='red'
                )
            self.geo_map.show_map()
            
        # 更新词云
        if "text" in self.data:
            self.word_cloud.generate_wordcloud(self.data["text"])
            
        # 更新数据表格
        if "table" in self.data:
            self.data_table.load_data(self.data["table"])
        elif "tweets" in self.data:
            self.data_table.load_data(self.data["tweets"])
            
    def update_time_series(self):
        """更新时间序列图表"""
        if "time_series" in self.data:
            dates, values = self.data["time_series"]
            self.time_series_chart.plot_data(dates, values, "时间序列数据")
            
            if self.ts_smoothing.isChecked():
                self.time_series_chart.apply_moving_average(5)
                
    def update_network_layout(self):
        """更新网络图布局"""
        if "network" in self.data:
            layout = self.net_layout_combo.currentText().lower().replace('-', '_')
            detect_communities = self.community_detection.isChecked()
            self.network_view.draw_network(self.data["network"], layout, detect_communities)
            
    def update_network_communities(self):
        """更新网络图社区检测"""
        if "network" in self.data:
            layout = self.net_layout_combo.currentText().lower().replace('-', '_')
            detect_communities = self.community_detection.isChecked()
            self.network_view.draw_network(self.data["network"], layout, detect_communities)
            
    def toggle_realtime_data(self, state):
        """切换实时数据流"""
        if state == Qt.Checked:
            self.start_realtime_data()
        else:
            self.stop_realtime_data()
            
    def start_realtime_data(self):
        """启动实时数据流"""
        interval = self.realtime_interval.value()
        self.realtime_thread = RealTimeDataThread("time_series", interval)
        self.realtime_thread.new_data.connect(self.on_new_realtime_data)
        self.realtime_thread.start()
        self.log_message("实时数据流已启动")
        
    def stop_realtime_data(self):
        """停止实时数据流"""
        if hasattr(self, 'realtime_thread'):
            self.realtime_thread.stop()
            self.realtime_thread.wait()
            self.log_message("实时数据流已停止")
            
    @pyqtSlot(object)
    def on_new_realtime_data(self, data):
        """处理新的实时数据"""
        # 这里可以实现实时数据的处理和可视化更新
        self.log_message(f"收到实时数据: {data}")
        
    def detect_anomalies(self):
        """异常检测"""
        if "time_series" not in self.data:
            QMessageBox.warning(self, "警告", "没有时间序列数据进行异常检测")
            return
            
        self.log_message("正在执行异常检测...")
        
        dates, values = self.data["time_series"]
        
        # 使用分析引擎检测异常
        anomalies = self.analytics.detect_anomalies(
            values, 
            method='isolation_forest',
            contamination=0.1
        )
        
        # 提取异常点的日期和值
        anomaly_dates = [dates[i] for i in anomalies]
        anomaly_values = [values[i] for i in anomalies]
        
        # 在图表上标记异常点
        self.time_series_chart.add_anomalies(anomaly_dates, anomaly_values)
        
        # 显示分析结果
        result_text = f"检测到 {len(anomalies)} 个异常点\n\n"
        result_text += "异常点详情:\n"
        for i, idx in enumerate(anomalies):
            result_text += f"{i+1}. 时间: {dates[idx].strftime('%Y-%m-%d')}, 值: {values[idx]:.2f}\n"
            
        self.results_text.setText(result_text)
        self.log_message(f"异常检测完成，找到 {len(anomalies)} 个异常点")
        
    def cluster_analysis(self):
        """聚类分析"""
        if "geo" not in self.data:
            QMessageBox.warning(self, "警告", "没有地理数据进行聚类分析")
            return
            
        self.log_message("正在执行地理聚类分析...")
        
        # 提取坐标数据
        coords = np.array([[point["lat"], point["lon"]] for point in self.data["geo"]])
        
        # 使用分析引擎进行聚类
        clusters = self.analytics.cluster_data(coords, method='dbscan', eps=0.1, min_samples=2)
        
        # 显示分析结果
        unique_clusters = set(clusters)
        result_text = f"发现 {len(unique_clusters)} 个聚类\n\n"
        result_text += "聚类详情:\n"
        
        for cluster_id in unique_clusters:
            cluster_points = coords[clusters == cluster_id]
            result_text += f"聚类 {cluster_id}: {len(cluster_points)} 个点\n"
            
        self.results_text.setText(result_text)
        self.log_message(f"聚类分析完成，发现 {len(unique_clusters)} 个聚类")
        
        # 在地图上显示聚类结果
        self.geo_map.cluster_analysis()
        
    def pattern_recognition(self):
        """模式识别"""
        self.log_message("正在执行模式识别...")
        # 这里可以实现模式识别算法
        QMessageBox.information(self, "信息", "模式识别功能待实现")
        
    def forecast_analysis(self):
        """预测分析"""
        self.log_message("正在执行预测分析...")
        # 这里可以实现预测分析算法
        QMessageBox.information(self, "信息", "预测分析功能待实现")
        
    def export_visualization(self):
        """导出可视化结果"""
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getSaveFileName(
            self, "导出可视化结果", "", 
            "PNG图像 (*.png);;JPEG图像 (*.jpg);;PDF文件 (*.pdf);;CSV文件 (*.csv)", 
            options=options
        )
        
        if file_name:
            # 根据文件类型执行不同的导出操作
            if file_name.endswith('.png') or file_name.endswith('.jpg'):
                # 导出当前标签页的图像
                current_tab = self.centralWidget().findChild(QTabWidget).currentIndex()
                if current_tab == 0:  # 时间序列
                    self.time_series_chart.fig.savefig(file_name, dpi=300, bbox_inches='tight')
                elif current_tab == 3:  # 文本分析
                    self.word_cloud.fig.savefig(file_name, dpi=300, bbox_inches='tight')
            elif file_name.endswith('.csv'):
                # 导出数据表格
                if "table" in self.data:
                    self.data["table"].to_csv(file_name, index=False)
                else:
                    QMessageBox.warning(self, "警告", "没有表格数据可导出")
                    return
                    
            self.status_bar.showMessage(f"已导出到: {file_name}")
            self.log_message(f"已导出可视化结果到 {file_name}")
            
    def show_settings(self):
        """显示设置对话框"""
        dialog = SettingsDialog(self)
        dialog.set_settings(self.settings)
        
        if dialog.exec_() == QDialog.Accepted:
            new_settings = dialog.get_settings()
            self.settings.update(new_settings)
            self.apply_theme(self.settings["theme"])
            self.log_message("设置已更新")
            
    def apply_theme(self, theme):
        """应用主题"""
        if theme == "深色":
            self.apply_dark_theme()
        elif theme == "浅色":
            self.apply_light_theme()
        else:
            # 使用系统默认主题
            pass
            
    def apply_dark_theme(self):
        """应用深色主题"""
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
        
    def apply_light_theme(self):
        """应用浅色主题"""
        self.setPalette(self.style().standardPalette())
        
    def show_documentation(self):
        """显示文档"""
        webbrowser.open("https://github.com/yourusername/intelligence-visualization-tool")
        
    def show_about(self):
        """显示关于信息"""
        about_text = """
        <h2>高级情报可视化分析工具</h2>
        <p>版本: 2.0</p>
        <p>版权所有 © 2023 高级情报分析团队</p>
        <p>这是一个功能强大的情报可视化工具，支持多种数据源和高级分析方法。</p>
        <p>功能包括:</p>
        <ul>
            <li>多数据源支持（合成数据、CSV、API、Twitter、网页爬取）</li>
            <li>实时数据流处理</li>
            <li>高级时间序列分析</li>
            <li>交互式网络关系分析</li>
            <li>地理空间可视化</li>
            <li>文本分析和词云生成</li>
            <li>异常检测和聚类分析</li>
            <li>可定制的主题和设置</li>
        </ul>
        """
        
        QMessageBox.about(self, "关于", about_text)
        
    def log_message(self, message):
        """记录日志消息"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
        
    def closeEvent(self, event):
        """处理关闭事件"""
        # 停止所有后台线程
        if hasattr(self, 'realtime_thread'):
            self.realtime_thread.stop()
            self.realtime_thread.wait()
            
        if hasattr(self, 'loader_thread') and self.loader_thread.isRunning():
            self.loader_thread.quit()
            self.loader_thread.wait()
            
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # 使用融合样式，使界面看起来更现代
    
    # 设置应用程序字体
    font = QFont("Arial", 10)
    app.setFont(font)
    
    dashboard = AdvancedIntelligenceDashboard()
    dashboard.show()
    
    sys.exit(app.exec_())