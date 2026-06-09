import sys
import os
import json
import math
import numpy as np
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QSplitter, QTabWidget, QToolBar, QAction, QToolButton, QMenu,
                             QStatusBar, QLabel, QMessageBox, QFileDialog, QDockWidget,
                             QTableWidget, QTableWidgetItem, QTreeWidget, QTreeWidgetItem,
                             QHeaderView, QGraphicsView, QGraphicsScene, QGraphicsItem, QGraphicsItemGroup,
                             QGraphicsEllipseItem, QGraphicsPolygonItem, QGraphicsLineItem,
                             QDialog, QPushButton, QComboBox, QSpinBox, QDoubleSpinBox,
                             QSlider, QCheckBox, QGroupBox, QFormLayout, QProgressBar)
from PyQt5.QtCore import Qt, QPointF, QRectF, QSize, QTimer, pyqtSignal, QThread, QVariant
from PyQt5.QtGui import (QIcon, QPixmap, QColor, QPen, QBrush, QFont, QPainterPath, 
                         QKeySequence, QPainter, QPolygonF)
from PyQt5.QtSvg import QSvgRenderer
import sqlite3
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import geopandas as gpd
from shapely.geometry import Point, Polygon, LineString
import folium
from folium.plugins import HeatMap
import tempfile
from io import BytesIO
from PIL import Image
import requests
import pandas as pd
from sklearn.cluster import DBSCAN
from scipy import stats
import networkx as nx


class MapTools:
    """地图工具类，提供各种地图操作功能"""
    
    @staticmethod
    def calculate_distance(point1, point2):
        """计算两点之间的距离（米）"""
        # 简化的距离计算，实际应用中应使用更精确的公式
        lat1, lon1 = point1.y(), point1.x()
        lat2, lon2 = point2.y(), point2.x()
        
        # 使用Haversine公式计算大圆距离
        R = 6371000  # 地球半径，单位米
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)
        
        a = math.sin(delta_phi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(delta_lambda/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c
    
    @staticmethod
    def calculate_area(points):
        """计算多边形面积（平方米）"""
        if len(points) < 3:
            return 0.0
            
        # 将QPointF转换为经纬度元组
        coords = [(p.x(), p.y()) for p in points]
        
        # 使用shapely计算面积（近似值）
        polygon = Polygon(coords)
        return polygon.area * 111319.488 * 111319.488  # 粗略转换
    
    @staticmethod
    def create_buffer(geometry, distance):
        """创建缓冲区"""
        try:
            buffered = geometry.buffer(distance / 111319.488)  # 粗略转换
            return buffered
        except:
            return None
    
    @staticmethod
    def wgs84_to_web_mercator(lon, lat):
        """WGS84坐标转换为Web墨卡托投影"""
        x = lon * 20037508.34 / 180
        y = math.log(math.tan((90 + lat) * math.pi / 360)) / (math.pi / 180)
        y = y * 20037508.34 / 180
        return (x, y)
    
    @staticmethod
    def web_mercator_to_wgs84(x, y):
        """Web墨卡托投影转换为WGS84坐标"""
        lon = (x / 20037508.34) * 180
        lat = (y / 20037508.34) * 180
        lat = 180 / math.pi * (2 * math.atan(math.exp(lat * math.pi / 180)) - math.pi / 2)
        return (lon, lat)


class SpatialAnalysis:
    """空间分析工具类"""
    
    @staticmethod
    def find_clusters(points, eps=0.01, min_samples=5):
        """使用DBSCAN算法进行聚类分析"""
        if not points:
            return []
            
        coords = np.array([[p.x(), p.y()] for p in points])
        db = DBSCAN(eps=eps, min_samples=min_samples).fit(coords)
        labels = db.labels_
        
        # 组织聚类结果
        clusters = {}
        for i, label in enumerate(labels):
            if label not in clusters:
                clusters[label] = []
            clusters[label].append(points[i])
            
        return clusters
    
    @staticmethod
    def calculate_density(points, area):
        """计算点密度"""
        if area <= 0:
            return 0
        return len(points) / area
    
    @staticmethod
    def interpolate_surface(points, values, method='idw', resolution=100):
        """表面插值（反距离权重法）"""
        if not points or not values:
            return None, None, None
            
        # 获取边界
        x_coords = [p.x() for p in points]
        y_coords = [p.y() for p in points]
        x_min, x_max = min(x_coords), max(x_coords)
        y_min, y_max = min(y_coords), max(y_coords)
        
        # 创建网格
        xi = np.linspace(x_min, x_max, resolution)
        yi = np.linspace(y_min, y_max, resolution)
        xi, yi = np.meshgrid(xi, yi)
        zi = np.zeros(xi.shape)
        
        if method == 'idw':
            # 反距离权重插值
            for i in range(resolution):
                for j in range(resolution):
                    weights = []
                    value_sum = 0
                    weight_sum = 0
                    
                    for k, point in enumerate(points):
                        dist = MapTools.calculate_distance(
                            QPointF(xi[i, j], yi[i, j]), 
                            QPointF(point.x(), point.y())
                        )
                        if dist < 1e-6:  # 避免除以零
                            weight = 1e10
                        else:
                            weight = 1.0 / (dist ** 2)
                            
                        weights.append(weight)
                        value_sum += values[k] * weight
                        weight_sum += weight
                    
                    if weight_sum > 0:
                        zi[i, j] = value_sum / weight_sum
                    else:
                        zi[i, j] = np.nan
        
        return xi, yi, zi
    
    @staticmethod
    def calculate_visibility(observer_point, terrain_points, max_distance=1000):
        """计算可视域分析"""
        visible_points = []
        
        for point in terrain_points:
            distance = MapTools.calculate_distance(observer_point, point)
            if distance <= max_distance:
                # 简化版可视域分析 - 实际应用需要地形数据
                visible_points.append(point)
                
        return visible_points


class DatabaseManager:
    """数据库管理类"""
    
    def __init__(self, db_path="forest_management.db"):
        self.db_path = db_path
        self.connection = None
        self.connect()
        self.init_database()
    
    def connect(self):
        """连接到数据库"""
        try:
            self.connection = sqlite3.connect(self.db_path)
            self.connection.enable_load_extension(True)
            # 尝试加载SpatiaLite扩展（如果可用）
            try:
                self.connection.execute("SELECT load_extension('mod_spatialite')")
            except:
                pass
        except Exception as e:
            print(f"数据库连接错误: {e}")
    
    def init_database(self):
        """初始化数据库表"""
        try:
            cursor = self.connection.cursor()
            
            # 创建空间元数据表（如果使用SpatiaLite）
            try:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS geometry_columns (
                        f_table_name VARCHAR,
                        f_geometry_column VARCHAR,
                        geometry_type INTEGER,
                        coord_dimension INTEGER,
                        srid INTEGER,
                        spatial_index_enabled INTEGER
                    )
                """)
            except:
                pass
            
            # 创建森林区域表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS forest_areas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    type TEXT,
                    area REAL,
                    geometry_type TEXT,
                    geometry_data TEXT,
                    created_date TEXT,
                    updated_date TEXT
                )
            """)
            
            # 创建树木表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trees (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    species TEXT,
                    age INTEGER,
                    height REAL,
                    diameter REAL,
                    health_status TEXT,
                    latitude REAL,
                    longitude REAL,
                    area_id INTEGER,
                    planted_date TEXT,
                    notes TEXT,
                    FOREIGN KEY (area_id) REFERENCES forest_areas (id)
                )
            """)
            
            # 创建监测数据表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS monitoring_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tree_id INTEGER,
                    record_date TEXT,
                    health_score INTEGER,
                    growth_rate REAL,
                    pest_infestation BOOLEAN,
                    weather_conditions TEXT,
                    notes TEXT,
                    FOREIGN KEY (tree_id) REFERENCES trees (id)
                )
            """)
            
            # 创建用户表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    full_name TEXT,
                    role TEXT,
                    permissions TEXT
                )
            """)
            
            self.connection.commit()
            
        except Exception as e:
            print(f"数据库初始化错误: {e}")
    
    def execute_query(self, query, parameters=None):
        """执行SQL查询"""
        try:
            cursor = self.connection.cursor()
            if parameters:
                cursor.execute(query, parameters)
            else:
                cursor.execute(query)
            self.connection.commit()
            return cursor
        except Exception as e:
            print(f"查询执行错误: {e}")
            return None
    
    def get_forest_areas(self):
        """获取所有森林区域"""
        try:
            cursor = self.execute_query("SELECT * FROM forest_areas")
            return cursor.fetchall()
        except:
            return []
    
    def add_tree(self, tree_data):
        """添加树木记录"""
        query = """
            INSERT INTO trees (species, age, height, diameter, health_status, 
                              latitude, longitude, area_id, planted_date, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        parameters = (
            tree_data.get('species'), tree_data.get('age'), tree_data.get('height'),
            tree_data.get('diameter'), tree_data.get('health_status'),
            tree_data.get('latitude'), tree_data.get('longitude'),
            tree_data.get('area_id'), tree_data.get('planted_date'),
            tree_data.get('notes')
        )
        return self.execute_query(query, parameters)
    
    def get_trees_by_area(self, area_id):
        """获取指定区域的树木"""
        try:
            cursor = self.execute_query(
                "SELECT * FROM trees WHERE area_id = ?", 
                (area_id,)
            )
            return cursor.fetchall()
        except:
            return []
    
    def add_monitoring_data(self, monitoring_data):
        """添加监测数据"""
        query = """
            INSERT INTO monitoring_data 
            (tree_id, record_date, health_score, growth_rate, pest_infestation, weather_conditions, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        parameters = (
            monitoring_data.get('tree_id'), monitoring_data.get('record_date'),
            monitoring_data.get('health_score'), monitoring_data.get('growth_rate'),
            monitoring_data.get('pest_infestation'), monitoring_data.get('weather_conditions'),
            monitoring_data.get('notes')
        )
        return self.execute_query(query, parameters)
    
    def get_monitoring_data(self, tree_id, limit=100):
        """获取树木的监测数据"""
        try:
            cursor = self.execute_query(
                "SELECT * FROM monitoring_data WHERE tree_id = ? ORDER BY record_date DESC LIMIT ?",
                (tree_id, limit)
            )
            return cursor.fetchall()
        except:
            return []


class MapCanvas(QGraphicsView):
    """地图画布控件"""
    
    # 定义信号
    pointAdded = pyqtSignal(QPointF, dict)
    areaAdded = pyqtSignal(list, dict)
    selectionChanged = pyqtSignal(list)
    mapMoved = pyqtSignal(float, float, float)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        
        # 地图状态变量
        self.zoom_level = 10
        self.center_lat = 39.9042  # 默认中心点（北京）
        self.center_lon = 116.4074
        self.scale_factor = 1.0
        
        # 绘图工具状态
        self.current_tool = "select"  # 默认工具
        self.drawing = False
        self.current_shape = None
        self.temp_points = []
        
        # 图层管理
        self.layers = {}
        self.selected_items = []
        
        # 地图配置
        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        
        # 初始化地图
        self.init_map()
    
    def init_map(self):
        """初始化地图"""
        self.scene.clear()
        self.layers.clear()
        
        # 创建基础图层
        base_layer = QGraphicsItemGroup()
        self.scene.addItem(base_layer)
        self.layers['base'] = base_layer
        
        # 创建要素图层
        feature_layer = QGraphicsItemGroup()
        self.scene.addItem(feature_layer)
        self.layers['features'] = feature_layer
        
        # 创建临时图层
        temp_layer = QGraphicsItemGroup()
        self.scene.addItem(temp_layer)
        self.layers['temp'] = temp_layer
        
        # 设置场景范围
        self.scene.setSceneRect(-1000, -1000, 2000, 2000)
        self.centerOn(0, 0)
        
        # 绘制网格背景
        self.draw_grid()
    
    def draw_grid(self):
        """绘制网格"""
        grid_size = 100
        rect = self.scene.sceneRect()
        left = int(rect.left()) - (int(rect.left()) % grid_size)
        top = int(rect.top()) - (int(rect.top()) % grid_size)
        right = int(rect.right())
        bottom = int(rect.bottom())
        
        # 绘制网格线
        pen = QPen(QColor(200, 200, 200, 100))
        for x in range(left, right, grid_size):
            self.scene.addLine(x, top, x, bottom, pen)
        for y in range(top, bottom, grid_size):
            self.scene.addLine(left, y, right, y, pen)
    
    def wheelEvent(self, event):
        """鼠标滚轮事件 - 缩放地图"""
        zoom_in_factor = 1.25
        zoom_out_factor = 1 / zoom_in_factor
        
        # 保存当前鼠标位置的场景坐标
        old_pos = self.mapToScene(event.pos())
        
        # 缩放
        if event.angleDelta().y() > 0:
            self.scale(zoom_in_factor, zoom_in_factor)
            self.zoom_level += 1
        else:
            self.scale(zoom_out_factor, zoom_out_factor)
            self.zoom_level -= 1
        
        # 获取缩放后的鼠标位置
        new_pos = self.mapToScene(event.pos())
        
        # 移动场景以保持鼠标位置不变
        delta = new_pos - old_pos
        self.translate(delta.x(), delta.y())
        
        # 发射地图移动信号
        self.mapMoved.emit(self.center_lat, self.center_lon, self.zoom_level)
        
        event.accept()
    
    def mousePressEvent(self, event):
        """鼠标按下事件"""
        if self.current_tool == "add_point":
            scene_pos = self.mapToScene(event.pos())
            self.add_point(scene_pos)
            event.accept()
        elif self.current_tool == "add_polygon":
            if event.button() == Qt.LeftButton:
                scene_pos = self.mapToScene(event.pos())
                if not self.drawing:
                    self.start_drawing_polygon(scene_pos)
                else:
                    self.continue_drawing_polygon(scene_pos)
                event.accept()
            elif event.button() == Qt.RightButton and self.drawing:
                self.finish_drawing_polygon()
                event.accept()
        else:
            super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        """鼠标移动事件"""
        if self.drawing and self.current_tool == "add_polygon" and self.current_shape:
            scene_pos = self.mapToScene(event.pos())
            self.update_temp_shape(scene_pos)
        
        # 更新状态栏坐标显示
        scene_pos = self.mapToScene(event.pos())
        
        # 使用更安全的方式获取主窗口
        main_window = self.get_main_window()
        if main_window and hasattr(main_window, 'statusBar'):
            main_window.statusBar().showMessage(f"坐标: {scene_pos.x():.6f}, {scene_pos.y():.6f}")
        
        super().mouseMoveEvent(event)

    def get_main_window(self):
        """获取主窗口实例"""
        parent = self.parent()
        while parent is not None:
            if isinstance(parent, ForestManagementSystem):
                return parent
            parent = parent.parent()
        return None
    
    def keyPressEvent(self, event):
        """键盘事件"""
        if event.key() == Qt.Key_Escape and self.drawing:
            self.cancel_drawing()
            event.accept()
        else:
            super().keyPressEvent(event)
    
    def set_tool(self, tool):
        """设置当前工具"""
        self.current_tool = tool
        self.setDragMode(QGraphicsView.RubberBandDrag if tool == "select" else QGraphicsView.NoDrag)
        
        # 取消当前绘图操作
        if tool != "add_polygon":
            self.cancel_drawing()
    
    def start_drawing_polygon(self, point):
        """开始绘制多边形"""
        self.drawing = True
        self.temp_points = [point]
        
        # 创建临时图形
        self.current_shape = QGraphicsPolygonItem()
        self.current_shape.setPen(QPen(Qt.blue, 2))
        self.current_shape.setBrush(QBrush(QColor(0, 0, 255, 50)))
        self.layers['temp'].addToGroup(self.current_shape)
        
        self.update_temp_shape(point)
    
    def continue_drawing_polygon(self, point):
        """继续绘制多边形"""
        self.temp_points.append(point)
        self.update_temp_shape(point)
    
    def finish_drawing_polygon(self):
        """完成多边形绘制"""
        if len(self.temp_points) >= 3:
            polygon = QPolygonF(self.temp_points)
            
            # 创建永久图形
            poly_item = QGraphicsPolygonItem(polygon)
            poly_item.setPen(QPen(Qt.darkGreen, 2))
            poly_item.setBrush(QBrush(QColor(0, 255, 0, 100)))
            poly_item.setData(0, "forest_area")
            self.layers['features'].addToGroup(poly_item)
            
            # 发射信号
            properties = {
                "name": f"区域_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "type": "forest",
                "area": MapTools.calculate_area(self.temp_points)
            }
            self.areaAdded.emit(self.temp_points, properties)
        
        self.cancel_drawing()
    
    def cancel_drawing(self):
        """取消绘图"""
        self.drawing = False
        self.temp_points = []
        if self.current_shape:
            self.layers['temp'].removeFromGroup(self.current_shape)
            self.scene.removeItem(self.current_shape)
            self.current_shape = None
    
    def update_temp_shape(self, current_point):
        """更新临时图形"""
        if not self.temp_points or not self.current_shape:
            return
        
        points = self.temp_points + [current_point]
        polygon = QPolygonF(points)
        self.current_shape.setPolygon(polygon)
    
    def add_point(self, point):
        """添加点要素"""
        # 创建点图形
        ellipse = QGraphicsEllipseItem(-5, -5, 10, 10)
        ellipse.setPos(point)
        ellipse.setPen(QPen(Qt.red))
        ellipse.setBrush(QBrush(Qt.red))
        ellipse.setData(0, "tree")
        self.layers['features'].addToGroup(ellipse)
        
        # 发射信号
        properties = {
            "type": "tree",
            "latitude": point.y(),
            "longitude": point.x()
        }
        self.pointAdded.emit(point, properties)
    
    def clear_selection(self):
        """清除选择"""
        for item in self.selected_items:
            item.setPen(QPen(Qt.black))
        self.selected_items.clear()
    
    def get_selected_items(self):
        """获取选中的项目"""
        return self.selected_items


class AnalysisWorker(QThread):
    """分析工作线程"""
    
    finished = pyqtSignal(object)
    progress = pyqtSignal(int)
    
    def __init__(self, analysis_type, data, parameters):
        super().__init__()
        self.analysis_type = analysis_type
        self.data = data
        self.parameters = parameters
    
    def run(self):
        """执行分析"""
        try:
            if self.analysis_type == "cluster":
                result = self.perform_cluster_analysis()
            elif self.analysis_type == "density":
                result = self.perform_density_analysis()
            elif self.analysis_type == "interpolation":
                result = self.perform_interpolation()
            else:
                result = None
            
            self.finished.emit(result)
        except Exception as e:
            self.finished.emit({"error": str(e)})
    
    def perform_cluster_analysis(self):
        """执行聚类分析"""
        points = self.data.get('points', [])
        eps = self.parameters.get('eps', 0.01)
        min_samples = self.parameters.get('min_samples', 5)
        
        clusters = SpatialAnalysis.find_clusters(points, eps, min_samples)
        
        result = {
            'type': 'cluster',
            'clusters': clusters,
            'parameters': self.parameters
        }
        
        return result
    
    def perform_density_analysis(self):
        """执行密度分析"""
        points = self.data.get('points', [])
        area = self.parameters.get('area', 1.0)
        
        density = SpatialAnalysis.calculate_density(points, area)
        
        result = {
            'type': 'density',
            'density': density,
            'parameters': self.parameters
        }
        
        return result
    
    def perform_interpolation(self):
        """执行插值分析"""
        points = self.data.get('points', [])
        values = self.data.get('values', [])
        method = self.parameters.get('method', 'idw')
        resolution = self.parameters.get('resolution', 100)
        
        xi, yi, zi = SpatialAnalysis.interpolate_surface(
            points, values, method, resolution
        )
        
        result = {
            'type': 'interpolation',
            'xi': xi,
            'yi': yi,
            'zi': zi,
            'parameters': self.parameters
        }
        
        return result


class ForestManagementSystem(QMainWindow):
    """山林管理系统主窗口"""
    
    def __init__(self):
        super().__init__()
        
        # 初始化系统
        self.db_manager = DatabaseManager()
        self.current_file = None
        self.analysis_workers = []
        
        # 设置UI
        self.init_ui()
        
        # 加载初始数据
        self.load_initial_data()
    
    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("山林管理系统")
        self.setGeometry(100, 100, 1200, 800)
        
        # 创建中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QHBoxLayout(central_widget)
        
        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        
        # 左侧面板
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # 图层管理
        layer_group = QGroupBox("图层管理")
        layer_layout = QVBoxLayout(layer_group)
        
        self.layer_tree = QTreeWidget()
        self.layer_tree.setHeaderLabels(["图层", "可见性"])
        layer_layout.addWidget(self.layer_tree)
        
        left_layout.addWidget(layer_group)
        
        # 属性表格
        attr_group = QGroupBox("属性数据")
        attr_layout = QVBoxLayout(attr_group)
        
        self.attr_table = QTableWidget()
        self.attr_table.setColumnCount(3)
        self.attr_table.setHorizontalHeaderLabels(["ID", "名称", "值"])
        attr_layout.addWidget(self.attr_table)
        
        left_layout.addWidget(attr_group)
        
        # 右侧地图区域
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # 创建地图画布
        self.map_canvas = MapCanvas()
        right_layout.addWidget(self.map_canvas)
        
        # 添加面板到分割器
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([300, 900])
        
        main_layout.addWidget(splitter)
        
        # 创建工具栏
        self.create_toolbars()
        
        # 创建状态栏
        status_bar = QStatusBar()
        self.setStatusBar(status_bar)
        status_bar.showMessage("就绪")
        
        # 连接信号和槽
        self.map_canvas.pointAdded.connect(self.on_point_added)
        self.map_canvas.areaAdded.connect(self.on_area_added)
        self.map_canvas.selectionChanged.connect(self.on_selection_changed)
        self.map_canvas.mapMoved.connect(self.on_map_moved)
    
    def create_toolbars(self):
        """创建工具栏"""
        # 主工具栏
        main_toolbar = QToolBar("主工具栏")
        main_toolbar.setIconSize(QSize(32, 32))
        self.addToolBar(main_toolbar)
        
        # 文件操作
        new_action = QAction(QIcon("icons/new.png"), "新建", self)
        new_action.setShortcut(QKeySequence.New)
        new_action.triggered.connect(self.new_file)
        main_toolbar.addAction(new_action)
        
        open_action = QAction(QIcon("icons/open.png"), "打开", self)
        open_action.setShortcut(QKeySequence.Open)
        open_action.triggered.connect(self.open_file)
        main_toolbar.addAction(open_action)
        
        save_action = QAction(QIcon("icons/save.png"), "保存", self)
        save_action.setShortcut(QKeySequence.Save)
        save_action.triggered.connect(self.save_file)
        main_toolbar.addAction(save_action)
        
        main_toolbar.addSeparator()
        
        # 地图工具
        select_action = QAction(QIcon("icons/select.png"), "选择", self)
        select_action.triggered.connect(lambda: self.map_canvas.set_tool("select"))
        main_toolbar.addAction(select_action)
        
        add_point_action = QAction(QIcon("icons/point.png"), "添加点", self)
        add_point_action.triggered.connect(lambda: self.map_canvas.set_tool("add_point"))
        main_toolbar.addAction(add_point_action)
        
        add_polygon_action = QAction(QIcon("icons/polygon.png"), "添加多边形", self)
        add_polygon_action.triggered.connect(lambda: self.map_canvas.set_tool("add_polygon"))
        main_toolbar.addAction(add_polygon_action)
        
        main_toolbar.addSeparator()
        
        # 分析工具
        analysis_menu = QMenu(self)
        analysis_menu.addAction("聚类分析", self.run_cluster_analysis)
        analysis_menu.addAction("密度分析", self.run_density_analysis)
        analysis_menu.addAction("表面插值", self.run_interpolation_analysis)
        analysis_menu.addAction("可视域分析", self.run_visibility_analysis)
        
        analysis_button = QToolButton()
        analysis_button.setPopupMode(QToolButton.InstantPopup)
        analysis_button.setIcon(QIcon("icons/analysis.png"))
        analysis_button.setText("空间分析")
        analysis_button.setMenu(analysis_menu)
        main_toolbar.addWidget(analysis_button)
        
        # 可视化工具
        visualize_action = QAction(QIcon("icons/visualize.png"), "可视化", self)
        visualize_action.triggered.connect(self.show_visualization_dialog)
        main_toolbar.addAction(visualize_action)
        
        # 地图操作工具栏
        map_toolbar = QToolBar("地图操作")
        self.addToolBar(map_toolbar)
        
        zoom_in_action = QAction(QIcon("icons/zoom_in.png"), "放大", self)
        zoom_in_action.triggered.connect(self.zoom_in)
        map_toolbar.addAction(zoom_in_action)
        
        zoom_out_action = QAction(QIcon("icons/zoom_out.png"), "缩小", self)
        zoom_out_action.triggered.connect(self.zoom_out)
        map_toolbar.addAction(zoom_out_action)
        
        pan_action = QAction(QIcon("icons/pan.png"), "平移", self)
        pan_action.triggered.connect(self.enable_pan)
        map_toolbar.addAction(pan_action)
        
        full_extent_action = QAction(QIcon("icons/full_extent.png"), "全图", self)
        full_extent_action.triggered.connect(self.zoom_to_full_extent)
        map_toolbar.addAction(full_extent_action)
    
    def load_initial_data(self):
        """加载初始数据"""
        # 加载森林区域
        areas = self.db_manager.get_forest_areas()
        for area in areas:
            self.add_area_to_map(area)
        
        # 更新图层树
        self.update_layer_tree()
    
    def add_area_to_map(self, area_data):
        """添加区域到地图"""
        # 从数据库数据创建图形
        # 这里需要根据实际的数据结构解析几何数据
        pass
    
    def update_layer_tree(self):
        """更新图层树"""
        self.layer_tree.clear()
        
        # 添加基础图层
        base_item = QTreeWidgetItem(self.layer_tree, ["基础图层"])
        base_item.setCheckState(1, Qt.Checked)
        base_item.setData(0, Qt.UserRole, "base")
        
        # 添加要素图层
        feature_item = QTreeWidgetItem(self.layer_tree, ["要素图层"])
        feature_item.setCheckState(1, Qt.Checked)
        feature_item.setData(0, Qt.UserRole, "features")
        
        self.layer_tree.expandAll()
    
    def on_point_added(self, point, properties):
        """处理点添加事件"""
        # 保存到数据库
        tree_data = {
            'species': properties.get('species', '未知'),
            'age': properties.get('age', 0),
            'height': properties.get('height', 0.0),
            'diameter': properties.get('diameter', 0.0),
            'health_status': properties.get('health_status', '良好'),
            'latitude': point.y(),
            'longitude': point.x(),
            'area_id': properties.get('area_id'),
            'planted_date': properties.get('planted_date', datetime.now().strftime('%Y-%m-%d')),
            'notes': properties.get('notes', '')
        }
        
        self.db_manager.add_tree(tree_data)
        
        self.statusBar().showMessage(f"添加了树木在位置: {point.x():.6f}, {point.y():.6f}")
    
    def on_area_added(self, points, properties):
        """处理区域添加事件"""
        # 保存到数据库
        # 这里需要将几何数据转换为可存储的格式
        self.statusBar().showMessage(f"添加了区域: {properties.get('name')}, 面积: {properties.get('area'):.2f} 平方米")
    
    def on_selection_changed(self, selected_items):
        """处理选择变化事件"""
        # 更新属性表格
        self.update_attribute_table(selected_items)
    
    def on_map_moved(self, lat, lon, zoom):
        """处理地图移动事件"""
        self.statusBar().showMessage(f"中心点: {lat:.6f}, {lon:.6f} | 缩放级别: {zoom}")
    
    def update_attribute_table(self, items):
        """更新属性表格"""
        self.attr_table.setRowCount(0)
        
        if not items:
            return
        
        # 显示第一个选中项目的属性
        item = items[0]
        item_type = item.data(0)
        
        if item_type == "tree":
            self.attr_table.setRowCount(5)
            self.attr_table.setItem(0, 0, QTableWidgetItem("类型"))
            self.attr_table.setItem(0, 1, QTableWidgetItem("树木"))
            # 这里应该从数据库加载实际数据
        elif item_type == "forest_area":
            self.attr_table.setRowCount(5)
            self.attr_table.setItem(0, 0, QTableWidgetItem("类型"))
            self.attr_table.setItem(0, 1, QTableWidgetItem("森林区域"))
    
    def new_file(self):
        """新建文件"""
        # 确认是否保存当前更改
        reply = QMessageBox.question(self, "确认", "是否保存当前更改?",
                                   QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
        
        if reply == QMessageBox.Cancel:
            return
        elif reply == QMessageBox.Yes:
            self.save_file()
        
        # 重置系统
        self.current_file = None
        self.map_canvas.init_map()
        self.statusBar().showMessage("已创建新文件")
    
    def open_file(self):
        """打开文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "打开文件", "", "山林管理文件 (*.fmf);;所有文件 (*)"
        )
        
        if file_path:
            try:
                # 这里应该实现文件加载逻辑
                self.current_file = file_path
                self.statusBar().showMessage(f"已打开文件: {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"无法打开文件: {str(e)}")
    
    def save_file(self):
        """保存文件"""
        if not self.current_file:
            self.save_file_as()
            return
        
        try:
            # 这里应该实现文件保存逻辑
            self.statusBar().showMessage(f"已保存文件: {self.current_file}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法保存文件: {str(e)}")
    
    def save_file_as(self):
        """另存为文件"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存文件", "", "山林管理文件 (*.fmf);;所有文件 (*)"
        )
        
        if file_path:
            self.current_file = file_path
            self.save_file()
    
    def zoom_in(self):
        """放大地图"""
        self.map_canvas.scale(1.25, 1.25)
    
    def zoom_out(self):
        """缩小地图"""
        self.map_canvas.scale(0.8, 0.8)
    
    def enable_pan(self):
        """启用平移模式"""
        self.map_canvas.setDragMode(QGraphicsView.ScrollHandDrag)
    
    def zoom_to_full_extent(self):
        """缩放至全图"""
        self.map_canvas.fitInView(self.map_canvas.scene.sceneRect(), Qt.KeepAspectRatio)
    
    def run_cluster_analysis(self):
        """运行聚类分析"""
        # 获取当前点数据
        points = self.get_current_points()
        
        if not points:
            QMessageBox.warning(self, "警告", "没有可分析的点数据")
            return
        
        # 显示分析对话框
        dialog = ClusterAnalysisDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            parameters = dialog.get_parameters()
            
            # 创建工作线程
            worker = AnalysisWorker("cluster", {"points": points}, parameters)
            worker.finished.connect(self.on_analysis_finished)
            worker.start()
            
            self.analysis_workers.append(worker)
            
            # 显示进度条
            self.show_progress_dialog("正在执行聚类分析...")
    
    def run_density_analysis(self):
        """运行密度分析"""
        # 获取当前点数据和区域数据
        points = self.get_current_points()
        area = self.get_current_area()
        
        if not points or area <= 0:
            QMessageBox.warning(self, "警告", "没有可分析的数据")
            return
        
        # 显示分析对话框
        dialog = DensityAnalysisDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            parameters = dialog.get_parameters()
            parameters['area'] = area
            
            # 创建工作线程
            worker = AnalysisWorker("density", {"points": points}, parameters)
            worker.finished.connect(self.on_analysis_finished)
            worker.start()
            
            self.analysis_workers.append(worker)
            
            # 显示进度条
            self.show_progress_dialog("正在执行密度分析...")
    
    def run_interpolation_analysis(self):
        """运行插值分析"""
        # 获取当前点数据和值
        points = self.get_current_points()
        values = self.get_current_values()
        
        if not points or not values:
            QMessageBox.warning(self, "警告", "没有可分析的数据")
            return
        
        # 显示分析对话框
        dialog = InterpolationDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            parameters = dialog.get_parameters()
            
            # 创建工作线程
            worker = AnalysisWorker("interpolation", {"points": points, "values": values}, parameters)
            worker.finished.connect(self.on_analysis_finished)
            worker.start()
            
            self.analysis_workers.append(worker)
            
            # 显示进度条
            self.show_progress_dialog("正在执行插值分析...")
    
    def run_visibility_analysis(self):
        """运行可视域分析"""
        # 这里应该实现可视域分析逻辑
        QMessageBox.information(self, "信息", "可视域分析功能尚未实现")
    
    def on_analysis_finished(self, result):
        """分析完成处理"""
        if 'error' in result:
            QMessageBox.critical(self, "错误", f"分析失败: {result['error']}")
            return
        
        # 根据分析类型处理结果
        if result['type'] == 'cluster':
            self.handle_cluster_result(result)
        elif result['type'] == 'density':
            self.handle_density_result(result)
        elif result['type'] == 'interpolation':
            self.handle_interpolation_result(result)
        
        # 关闭进度对话框
        self.close_progress_dialog()
        
        # 显示结果
        self.show_analysis_result(result)
    
    def handle_cluster_result(self, result):
        """处理聚类分析结果"""
        clusters = result['clusters']
        
        # 在地图上显示聚类结果
        colors = [QColor(255, 0, 0), QColor(0, 255, 0), QColor(0, 0, 255), 
                 QColor(255, 255, 0), QColor(255, 0, 255), QColor(0, 255, 255)]
        
        for i, (cluster_id, points) in enumerate(clusters.items()):
            if cluster_id == -1:  # 噪声点
                color = QColor(128, 128, 128)
            else:
                color = colors[cluster_id % len(colors)]
            
            for point in points:
                ellipse = QGraphicsEllipseItem(-3, -3, 6, 6)
                ellipse.setPos(point)
                ellipse.setPen(QPen(color))
                ellipse.setBrush(QBrush(color))
                ellipse.setData(0, f"cluster_{cluster_id}")
                self.map_canvas.layers['features'].addToGroup(ellipse)
    
    def handle_density_result(self, result):
        """处理密度分析结果"""
        density = result['density']
        
        # 显示密度值
        self.statusBar().showMessage(f"密度: {density:.4f} 点/平方米")
    
    def handle_interpolation_result(self, result):
        """处理插值分析结果"""
        xi, yi, zi = result['xi'], result['yi'], result['zi']
        
        # 创建等高线图
        contour_figure = Figure()
        contour_canvas = FigureCanvas(contour_figure)
        ax = contour_figure.add_subplot(111)
        
        # 绘制等高线
        contour = ax.contourf(xi, yi, zi, levels=20, cmap='viridis')
        contour_figure.colorbar(contour, ax=ax)
        ax.set_title('表面插值结果')
        
        # 显示图表
        contour_dialog = QDialog(self)
        contour_dialog.setWindowTitle("插值结果")
        contour_dialog.setLayout(QVBoxLayout())
        contour_dialog.layout().addWidget(contour_canvas)
        contour_dialog.resize(800, 600)
        contour_dialog.exec_()
    
    def show_analysis_result(self, result):
        """显示分析结果"""
        # 创建结果对话框
        result_dialog = QDialog(self)
        result_dialog.setWindowTitle("分析结果")
        result_dialog.setLayout(QVBoxLayout())
        
        # 创建文本浏览器显示结果
        from PyQt5.QtWidgets import QTextBrowser
        text_browser = QTextBrowser()
        
        # 根据结果类型格式化文本
        if result['type'] == 'cluster':
            text = "聚类分析结果:\n\n"
            clusters = result['clusters']
            for cluster_id, points in clusters.items():
                if cluster_id == -1:
                    text += f"噪声点: {len(points)} 个\n"
                else:
                    text += f"聚类 {cluster_id}: {len(points)} 个点\n"
            
            text += f"\n参数: EPS={result['parameters']['eps']}, MinSamples={result['parameters']['min_samples']}"
            
        elif result['type'] == 'density':
            text = f"密度分析结果:\n\n密度: {result['density']:.6f} 点/平方米"
            
        elif result['type'] == 'interpolation':
            text = "插值分析完成\n\n"
            text += f"方法: {result['parameters']['method']}\n"
            text += f"分辨率: {result['parameters']['resolution']}x{result['parameters']['resolution']}"
        
        text_browser.setPlainText(text)
        result_dialog.layout().addWidget(text_browser)
        
        # 添加关闭按钮
        from PyQt5.QtWidgets import QDialogButtonBox
        button_box = QDialogButtonBox(QDialogButtonBox.Ok)
        button_box.accepted.connect(result_dialog.accept)
        result_dialog.layout().addWidget(button_box)
        
        result_dialog.exec_()
    
    def get_current_points(self):
        """获取当前点数据"""
        # 这里应该实现从地图或数据库获取点数据的逻辑
        # 返回示例数据
        return [QPointF(116.0 + i * 0.01, 39.0 + i * 0.01) for i in range(100)]
    
    def get_current_values(self):
        """获取当前值数据"""
        # 这里应该实现从数据库获取值数据的逻辑
        # 返回示例数据
        return [i * 0.5 for i in range(100)]
    
    def get_current_area(self):
        """获取当前区域面积"""
        # 这里应该实现从地图或数据库获取区域面积的逻辑
        # 返回示例数据
        return 1000000.0  # 1平方公里
    
    def show_progress_dialog(self, message):
        """显示进度对话框"""
        self.progress_dialog = QDialog(self)
        self.progress_dialog.setWindowTitle("请稍候")
        self.progress_dialog.setLayout(QVBoxLayout())
        
        progress_label = QLabel(message)
        self.progress_dialog.layout().addWidget(progress_label)
        
        progress_bar = QProgressBar()
        progress_bar.setRange(0, 0)  # 无限进度条
        self.progress_dialog.layout().addWidget(progress_bar)
        
        self.progress_dialog.setModal(True)
        self.progress_dialog.show()
    
    def close_progress_dialog(self):
        """关闭进度对话框"""
        if hasattr(self, 'progress_dialog'):
            self.progress_dialog.accept()
    
    def show_visualization_dialog(self):
        """显示可视化对话框"""
        dialog = VisualizationDialog(self)
        dialog.exec_()


class ClusterAnalysisDialog(QDialog):
    """聚类分析对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("聚类分析参数")
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        layout = QFormLayout(self)
        
        self.eps_spinbox = QDoubleSpinBox()
        self.eps_spinbox.setRange(0.001, 1.0)
        self.eps_spinbox.setValue(0.01)
        self.eps_spinbox.setSingleStep(0.001)
        self.eps_spinbox.setDecimals(3)
        layout.addRow("EPS (距离阈值):", self.eps_spinbox)
        
        self.min_samples_spinbox = QSpinBox()
        self.min_samples_spinbox.setRange(1, 100)
        self.min_samples_spinbox.setValue(5)
        layout.addRow("最小样本数:", self.min_samples_spinbox)
        
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addRow(button_box)
    
    def get_parameters(self):
        """获取参数"""
        return {
            'eps': self.eps_spinbox.value(),
            'min_samples': self.min_samples_spinbox.value()
        }


class DensityAnalysisDialog(QDialog):
    """密度分析对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("密度分析参数")
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        layout = QFormLayout(self)
        
        self.area_spinbox = QDoubleSpinBox()
        self.area_spinbox.setRange(1.0, 1000000.0)
        self.area_spinbox.setValue(10000.0)
        self.area_spinbox.setSuffix(" 平方米")
        layout.addRow("区域面积:", self.area_spinbox)
        
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addRow(button_box)
    
    def get_parameters(self):
        """获取参数"""
        return {
            'area': self.area_spinbox.value()
        }


class InterpolationDialog(QDialog):
    """插值分析对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("插值分析参数")
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        layout = QFormLayout(self)
        
        self.method_combo = QComboBox()
        self.method_combo.addItems(["反距离权重 (IDW)", "克里金法", "样条函数"])
        layout.addRow("插值方法:", self.method_combo)
        
        self.resolution_spinbox = QSpinBox()
        self.resolution_spinbox.setRange(10, 1000)
        self.resolution_spinbox.setValue(100)
        layout.addRow("分辨率:", self.resolution_spinbox)
        
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addRow(button_box)
    
    def get_parameters(self):
        """获取参数"""
        method_map = {
            "反距离权重 (IDW)": "idw",
            "克里金法": "kriging",
            "样条函数": "spline"
        }
        
        return {
            'method': method_map[self.method_combo.currentText()],
            'resolution': self.resolution_spinbox.value()
        }


class VisualizationDialog(QDialog):
    """可视化对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("数据可视化")
        self.setGeometry(100, 100, 800, 600)
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        
        # 图表类型选择
        chart_group = QGroupBox("图表类型")
        chart_layout = QHBoxLayout(chart_group)
        
        self.chart_combo = QComboBox()
        self.chart_combo.addItems(["柱状图", "折线图", "散点图", "饼图", "等高线图"])
        chart_layout.addWidget(QLabel("选择图表类型:"))
        chart_layout.addWidget(self.chart_combo)
        chart_layout.addStretch()
        
        layout.addWidget(chart_group)
        
        # 图表显示区域
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)
        
        # 按钮
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.generate_chart)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        # 初始生成图表
        self.generate_chart()
    
    def generate_chart(self):
        """生成图表"""
        chart_type = self.chart_combo.currentText()
        self.figure.clear()
        
        ax = self.figure.add_subplot(111)
        
        # 示例数据
        if chart_type == "柱状图":
            categories = ['松树', '橡树', '枫树', '杉木', '柏树']
            values = [25, 32, 18, 27, 15]
            ax.bar(categories, values)
            ax.set_title('树木种类分布')
            ax.set_ylabel('数量')
            
        elif chart_type == "折线图":
            months = ['1月', '2月', '3月', '4月', '5月', '6月']
            growth = [10, 15, 25, 40, 60, 85]
            ax.plot(months, growth, marker='o')
            ax.set_title('树木生长趋势')
            ax.set_ylabel('生长指数')
            
        elif chart_type == "散点图":
            x = np.random.rand(50) * 100
            y = np.random.rand(50) * 100
            sizes = np.random.rand(50) * 100
            ax.scatter(x, y, s=sizes, alpha=0.6)
            ax.set_title('树木分布散点图')
            ax.set_xlabel('经度')
            ax.set_ylabel('纬度')
            
        elif chart_type == "饼图":
            labels = ['健康', '一般', '较差', '病害']
            sizes = [65, 20, 10, 5]
            ax.pie(sizes, labels=labels, autopct='%1.1f%%')
            ax.set_title('树木健康状况')
            
        elif chart_type == "等高线图":
            x = np.linspace(-3, 3, 100)
            y = np.linspace(-3, 3, 100)
            X, Y = np.meshgrid(x, y)
            Z = np.sin(X) * np.cos(Y)
            contour = ax.contourf(X, Y, Z, levels=20, cmap='viridis')
            self.figure.colorbar(contour, ax=ax)
            ax.set_title('地形等高线')
        
        self.canvas.draw()


def main():
    """主函数"""
    app = QApplication(sys.argv)
    
    # 设置应用程序样式
    app.setStyle('Fusion')
    
    # 创建并显示主窗口
    window = ForestManagementSystem()
    window.show()
    
    # 运行应用程序
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()