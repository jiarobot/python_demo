import sys
import math
import numpy as np
from datetime import datetime
import matplotlib
matplotlib.rc("font", family='Microsoft YaHei')
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.patches import Polygon, Circle, Rectangle, PathPatch
from matplotlib.path import Path
from matplotlib.collections import PatchCollection
import matplotlib.colors as mcolors
from matplotlib import cm

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QToolBar, QAction, 
                             QDockWidget, QListWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QSpinBox, QDoubleSpinBox, QComboBox, QColorDialog,
                             QMessageBox, QFileDialog, QSplitter, QToolBox, QGroupBox,
                             QRadioButton, QLineEdit, QTextEdit, QPushButton, QCheckBox,
                             QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView,
                             QProgressBar, QSlider, QDial, QTreeWidget, QTreeWidgetItem,
                             QMenu, QInputDialog, QDialog, QFormLayout, QDialogButtonBox,
                             QSizePolicy, QFileDialog, QScrollArea)
from PyQt5.QtGui import (QPixmap, QPainter, QPen, QColor, QFont, QIcon, QBrush, 
                         QPolygonF, QLinearGradient, QRadialGradient, QFontMetrics,
                         QKeySequence, QPalette, QImage, QPixmap, QTransform)
from PyQt5.QtCore import (Qt, QPoint, QRect, QSize, QPointF, pyqtSignal, QVariant, 
                          QTimer, QDateTime, QThread, pyqtSlot, QObject, QEvent,
                          QSettings, QUrl, QByteArray, QBuffer, QDataStream, QMimeData)

# 地理处理库
import geopandas as gpd
import pandas as pd
import shapely
from shapely.geometry import Point, LineString, Polygon, MultiPoint, MultiLineString, MultiPolygon
from shapely.ops import unary_union, transform
import pyproj
from pyproj import CRS, Transformer
import rasterio
from rasterio.plot import show
import folium
from folium import plugins
import contextily as ctx

# 科学计算库
from scipy import interpolate
from scipy.spatial import Delaunay, Voronoi, voronoi_plot_2d
from scipy.ndimage import gaussian_filter, sobel

# 3D可视化组件
try:
    from mpl_toolkits.mplot3d import Axes3D
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    HAS_3D = True
except ImportError:
    HAS_3D = False

# 网络请求
try:
    from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
    HAS_NETWORK = True
except ImportError:
    HAS_NETWORK = False


class GeoDataFrameModel:
    """地理数据框模型，用于存储和处理地理数据"""
    def __init__(self):
        self.gdf = gpd.GeoDataFrame()
        self.crs = "EPSG:4326"  # 默认坐标系
        self.fields = []
        
    def load_file(self, file_path):
        """加载地理数据文件"""
        try:
            self.gdf = gpd.read_file(file_path)
            if self.gdf.crs:
                self.crs = self.gdf.crs
            self.fields = list(self.gdf.columns)
            return True, "文件加载成功"
        except Exception as e:
            return False, f"文件加载失败: {str(e)}"
            
    def save_file(self, file_path, driver="ESRI Shapefile"):
        """保存地理数据文件"""
        try:
            self.gdf.to_file(file_path, driver=driver)
            return True, "文件保存成功"
        except Exception as e:
            return False, f"文件保存失败: {str(e)}"
            
    def reproject(self, target_crs):
        """重新投影到目标坐标系"""
        try:
            self.gdf = self.gdf.to_crs(target_crs)
            self.crs = target_crs
            return True, f"重新投影到 {target_crs} 成功"
        except Exception as e:
            return False, f"重新投影失败: {str(e)}"
            
    def get_bounds(self):
        """获取数据边界"""
        if self.gdf.empty:
            return (-180, -90, 180, 90)  # 默认全球范围
        return self.gdf.total_bounds


class MapCanvas(FigureCanvas):
    """地图画布控件，基于Matplotlib"""
    # 自定义信号
    mouse_moved = pyqtSignal(float, float)  # 经度, 纬度
    mouse_clicked = pyqtSignal(float, float)  # 经度, 纬度
    extent_changed = pyqtSignal(float, float, float, float)  # minx, miny, maxx, maxy
    
    def __init__(self, parent=None, width=10, height=8, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        super().__init__(self.fig)
        self.setParent(parent)
        
        self.ax = self.fig.add_subplot(111)
        self.fig.subplots_adjust(left=0.05, right=0.95, bottom=0.05, top=0.95)
        
        # 初始化地图范围
        self.extent = (-180, -90, 180, 90)  # 全球范围
        self.ax.set_xlim(self.extent[0], self.extent[2])
        self.ax.set_ylim(self.extent[1], self.extent[3])
        self.ax.set_aspect('equal')
        
        # 设置背景色
        self.ax.set_facecolor('#a0c8f0')  # 浅蓝色背景表示海洋
        
        # 绘制经纬网格
        self.draw_grid()
        
        # 连接事件
        self.mpl_connect('motion_notify_event', self.on_mouse_move)
        self.mpl_connect('button_press_event', self.on_mouse_click)
        self.mpl_connect('draw_event', self.on_draw)
        
        # 存储图层
        self.layers = {}
        self.current_layer = None
        
        # 绘图相关变量
        self.is_drawing = False
        self.drawing_type = None
        self.drawing_points = []
        self.drawing_artist = None
        
        self.draw()
        
    def draw_grid(self):
        """绘制经纬网格"""
        # 清除现有网格
        for line in self.ax.get_lines():
            line.remove()
            
        # 绘制经线
        for lon in range(-180, 181, 30):
            if lon != 0:  # 跳过本初子午线，避免重复
                self.ax.axvline(x=lon, color='gray', linestyle='--', alpha=0.5, linewidth=0.5)
        
        # 绘制纬线
        for lat in range(-90, 91, 30):
            if lat != 0:  # 跳过赤道，避免重复
                self.ax.axhline(y=lat, color='gray', linestyle='--', alpha=0.5, linewidth=0.5)
                
        # 绘制本初子午线和赤道
        self.ax.axvline(x=0, color='black', linestyle='-', alpha=0.7, linewidth=1)
        self.ax.axhline(y=0, color='black', linestyle='-', alpha=0.7, linewidth=1)
        
        # 添加坐标标签
        self.ax.set_xticks(range(-180, 181, 30))
        self.ax.set_yticks(range(-90, 91, 30))
        self.ax.tick_params(labelsize=8)
        
    def on_mouse_move(self, event):
        """处理鼠标移动事件"""
        if event.inaxes == self.ax:
            x, y = event.xdata, event.ydata
            self.mouse_moved.emit(x, y)
            
    def on_mouse_click(self, event):
        """处理鼠标点击事件"""
        if event.inaxes == self.ax and event.button == 1:  # 左键点击
            x, y = event.xdata, event.ydata
            self.mouse_clicked.emit(x, y)
            
            # 如果正在绘图，添加点
            if self.is_drawing:
                self.drawing_points.append((x, y))
                self.update_drawing_preview()
                
    def on_draw(self, event):
        """处理绘制事件"""
        self.extent = self.ax.get_xlim() + self.ax.get_ylim()
        self.extent_changed.emit(*self.extent)
        
    def add_layer(self, gdf, name, color='blue', alpha=0.5, edgecolor='black', linewidth=1):
        """添加地理数据层"""
        if gdf.empty:
            return
            
        # 清除同名的现有图层
        if name in self.layers:
            self.layers[name].remove()
            
        # 绘制几何图形
        patches = []
        for geom in gdf.geometry:
            if geom.geom_type == 'Point':
                x, y = geom.x, geom.y
                patch = Circle((x, y), radius=0.5, color=color, alpha=alpha)
                patches.append(patch)
            elif geom.geom_type == 'LineString':
                x, y = geom.xy
                patch = self.ax.plot(x, y, color=color, linewidth=linewidth, alpha=alpha)[0]
                self.layers[name] = patch
                continue
            elif geom.geom_type == 'Polygon':
                x, y = geom.exterior.xy
                patch = Polygon(list(zip(x, y)), closed=True, 
                               color=color, alpha=alpha, edgecolor=edgecolor, linewidth=linewidth)
                patches.append(patch)
            elif geom.geom_type in ['MultiPoint', 'MultiLineString', 'MultiPolygon']:
                # 简化处理复杂几何类型
                for g in geom.geoms:
                    if g.geom_type == 'Point':
                        x, y = g.x, g.y
                        patch = Circle((x, y), radius=0.5, color=color, alpha=alpha)
                        patches.append(patch)
                    elif g.geom_type == 'LineString':
                        x, y = g.xy
                        patch = self.ax.plot(x, y, color=color, linewidth=linewidth, alpha=alpha)[0]
                        self.layers[name] = patch
                        continue
                    elif g.geom_type == 'Polygon':
                        x, y = g.exterior.xy
                        patch = Polygon(list(zip(x, y)), closed=True, 
                                       color=color, alpha=alpha, edgecolor=edgecolor, linewidth=linewidth)
                        patches.append(patch)
        
        # 添加所有图形到图表
        if patches:
            collection = PatchCollection(patches, match_original=True)
            self.ax.add_collection(collection)
            self.layers[name] = collection
            
        self.draw()
        
    def remove_layer(self, name):
        """移除图层"""
        if name in self.layers:
            self.layers[name].remove()
            del self.layers[name]
            self.draw()
            
    def clear_layers(self):
        """清除所有图层"""
        for name in list(self.layers.keys()):
            self.remove_layer(name)
            
    def zoom_to_extent(self, extent):
        """缩放到指定范围"""
        self.ax.set_xlim(extent[0], extent[2])
        self.ax.set_ylim(extent[1], extent[3])
        self.draw()
        
    def zoom_in(self):
        """放大"""
        x_range = self.extent[2] - self.extent[0]
        y_range = self.extent[3] - self.extent[1]
        
        new_x_range = x_range * 0.7
        new_y_range = y_range * 0.7
        
        center_x = (self.extent[0] + self.extent[2]) / 2
        center_y = (self.extent[1] + self.extent[3]) / 2
        
        new_extent = (
            center_x - new_x_range / 2,
            center_y - new_y_range / 2,
            center_x + new_x_range / 2,
            center_y + new_y_range / 2
        )
        
        self.zoom_to_extent(new_extent)
        
    def zoom_out(self):
        """缩小"""
        x_range = self.extent[2] - self.extent[0]
        y_range = self.extent[3] - self.extent[1]
        
        new_x_range = x_range / 0.7
        new_y_range = y_range / 0.7
        
        center_x = (self.extent[0] + self.extent[2]) / 2
        center_y = (self.extent[1] + self.extent[3]) / 2
        
        # 限制最大范围
        new_x_range = min(new_x_range, 360)
        new_y_range = min(new_y_range, 180)
        
        new_extent = (
            center_x - new_x_range / 2,
            center_y - new_y_range / 2,
            center_x + new_x_range / 2,
            center_y + new_y_range / 2
        )
        
        self.zoom_to_extent(new_extent)
        
    def zoom_full(self):
        """缩放到全局范围"""
        self.zoom_to_extent((-180, -90, 180, 90))
        
    def pan(self, dx, dy):
        """平移地图"""
        x_range = self.extent[2] - self.extent[0]
        y_range = self.extent[3] - self.extent[1]
        
        new_extent = (
            self.extent[0] + dx * x_range,
            self.extent[1] + dy * y_range,
            self.extent[2] + dx * x_range,
            self.extent[3] + dy * y_range
        )
        
        self.zoom_to_extent(new_extent)
        
    def start_drawing(self, drawing_type):
        """开始绘制几何图形"""
        self.is_drawing = True
        self.drawing_type = drawing_type
        self.drawing_points = []
        
    def update_drawing_preview(self):
        """更新绘制预览"""
        # 清除旧的预览
        if self.drawing_artist:
            self.drawing_artist.remove()
            
        if not self.drawing_points:
            return
            
        # 根据绘制类型创建预览
        if self.drawing_type == 'point' and self.drawing_points:
            x, y = self.drawing_points[-1]
            self.drawing_artist = self.ax.plot(x, y, 'ro', markersize=8, alpha=0.7)[0]
        elif self.drawing_type == 'line' and len(self.drawing_points) > 1:
            x = [p[0] for p in self.drawing_points]
            y = [p[1] for p in self.drawing_points]
            self.drawing_artist = self.ax.plot(x, y, 'r-', linewidth=2, alpha=0.7)[0]
        elif self.drawing_type == 'polygon' and len(self.drawing_points) > 2:
            x = [p[0] for p in self.drawing_points]
            y = [p[1] for p in self.drawing_points]
            polygon = Polygon(list(zip(x, y)), closed=True, 
                             fill=False, edgecolor='red', linewidth=2, alpha=0.7)
            self.drawing_artist = self.ax.add_patch(polygon)
            
        self.draw()
        
    def finish_drawing(self):
        """完成绘制"""
        if not self.is_drawing or not self.drawing_points:
            return None
            
        # 创建几何图形
        geometry = None
        if self.drawing_type == 'point':
            geometry = Point(self.drawing_points[0])
        elif self.drawing_type == 'line':
            geometry = LineString(self.drawing_points)
        elif self.drawing_type == 'polygon':
            geometry = Polygon(self.drawing_points)
            
        # 清除预览
        if self.drawing_artist:
            self.drawing_artist.remove()
            self.drawing_artist = None
            
        self.is_drawing = False
        self.drawing_points = []
        self.draw()
        
        return geometry
        
    def cancel_drawing(self):
        """取消绘制"""
        if self.drawing_artist:
            self.drawing_artist.remove()
            self.drawing_artist = None
            
        self.is_drawing = False
        self.drawing_points = []
        self.draw()


class GPSTracker(QObject):
    """GPS跟踪器类，模拟或真实GPS数据接收"""
    gps_data_received = pyqtSignal(float, float, float, float, float)  # 经度, 纬度, 海拔, 速度, 方向
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_position)
        self.is_active = False
        self.current_position = (116.3974, 39.9093, 50.0, 0.0, 0.0)  # 北京天安门
        self.simulation_speed = 1.0  # 模拟速度倍数
        
    def start_tracking(self, simulation=True):
        """开始GPS跟踪"""
        self.is_active = True
        if simulation:
            self.timer.start(1000)  # 每秒更新一次
        else:
            # 这里可以连接真实GPS设备
            pass
            
    def stop_tracking(self):
        """停止GPS跟踪"""
        self.is_active = False
        self.timer.stop()
        
    def update_position(self):
        """更新位置（模拟）"""
        # 模拟GPS数据变化
        lon, lat, alt, speed, direction = self.current_position
        
        # 转换为弧度
        rad_direction = math.radians(direction)
        
        # 计算移动距离（假设速度单位为km/h，转换为度/秒）
        # 1km ≈ 0.009度（纬度），经度变化需要乘以cos(lat)
        km_per_degree = 111.0  # 大约值
        distance_km = speed * (1/3600)  # 每秒移动的公里数
        
        # 计算经纬度变化
        delta_lat = (distance_km / km_per_degree) * math.sin(rad_direction)
        delta_lon = (distance_km / km_per_degree) * math.cos(rad_direction) / math.cos(math.radians(lat))
        
        lon += delta_lon
        lat += delta_lat
        
        # 方向变化
        direction = (direction + 5) % 360
        
        # 随机速度变化
        speed = max(0, min(120, speed + np.random.uniform(-5, 5)))
        
        # 随机高度变化
        alt = max(0, alt + np.random.uniform(-1, 1))
        
        self.current_position = (lon, lat, alt, speed, direction)
        self.gps_data_received.emit(lon, lat, alt, speed, direction)


class SpatialAnalysisTools:
    """高级空间分析工具类"""
    def __init__(self, canvas):
        self.canvas = canvas
        
    def buffer_analysis(self, gdf, distance, unit='meters'):
        """缓冲区分析"""
        try:
            # 确保使用投影坐标系进行计算
            if gdf.crs.is_geographic:
                # 找到合适的投影坐标系
                centroid = gdf.unary_union.centroid
                utm_zone = int((centroid.x + 180) / 6) + 1
                hemisphere = 'north' if centroid.y >= 0 else 'south'
                proj_crs = f"EPSG:326{utm_zone:02d}" if hemisphere == 'north' else f"EPSG:327{utm_zone:02d}"
                
                # 转换为投影坐标系
                gdf_proj = gdf.to_crs(proj_crs)
                
                # 创建缓冲区
                buffered = gdf_proj.buffer(distance)
                
                # 转换回原始坐标系
                result_gdf = gpd.GeoDataFrame(geometry=buffered, crs=gdf_proj.crs)
                result_gdf = result_gdf.to_crs(gdf.crs)
            else:
                # 已经是投影坐标系，直接创建缓冲区
                buffered = gdf.buffer(distance)
                result_gdf = gpd.GeoDataFrame(geometry=buffered, crs=gdf.crs)
                
            return result_gdf, "缓冲区分析成功"
        except Exception as e:
            return gpd.GeoDataFrame(), f"缓冲区分析失败: {str(e)}"
            
    def intersect_analysis(self, gdf1, gdf2):
        """相交分析"""
        try:
            # 确保使用相同的坐标系
            if gdf1.crs != gdf2.crs:
                gdf2 = gdf2.to_crs(gdf1.crs)
                
            # 执行相交操作
            intersection = gpd.overlay(gdf1, gdf2, how='intersection')
            
            return intersection, "相交分析成功"
        except Exception as e:
            return gpd.GeoDataFrame(), f"相交分析失败: {str(e)}"
            
    def calculate_area(self, gdf):
        """计算面积"""
        try:
            # 确保使用投影坐标系进行计算
            if gdf.crs.is_geographic:
                centroid = gdf.unary_union.centroid
                utm_zone = int((centroid.x + 180) / 6) + 1
                hemisphere = 'north' if centroid.y >= 0 else 'south'
                proj_crs = f"EPSG:326{utm_zone:02d}" if hemisphere == 'north' else f"EPSG:327{utm_zone:02d}"
                
                # 转换为投影坐标系
                gdf_proj = gdf.to_crs(proj_crs)
                
                # 计算面积
                areas = gdf_proj.geometry.area
            else:
                # 已经是投影坐标系，直接计算面积
                areas = gdf.geometry.area
                
            return areas, "面积计算成功"
        except Exception as e:
            return pd.Series(), f"面积计算失败: {str(e)}"
            
    def voronoi_diagram(self, points_gdf):
        """创建Voronoi图"""
        try:
            # 获取点坐标
            points = np.array([(point.x, point.y) for point in points_gdf.geometry])
            
            # 创建Voronoi图
            vor = Voronoi(points)
            
            # 创建Voronoi多边形
            voronoi_polygons = []
            for region in vor.regions:
                if not region or -1 in region:  # 跳过无效区域
                    continue
                    
                polygon = Polygon([vor.vertices[i] for i in region])
                voronoi_polygons.append(polygon)
                
            # 创建GeoDataFrame
            result_gdf = gpd.GeoDataFrame(geometry=voronoi_polygons, crs=points_gdf.crs)
            
            return result_gdf, "Voronoi图生成成功"
        except Exception as e:
            return gpd.GeoDataFrame(), f"Voronoi图生成失败: {str(e)}"
            
    def delaunay_triangulation(self, points_gdf):
        """创建Delaunay三角网"""
        try:
            # 获取点坐标
            points = np.array([(point.x, point.y) for point in points_gdf.geometry])
            
            # 创建Delaunay三角网
            tri = Delaunay(points)
            
            # 创建三角形
            triangles = []
            for simplex in tri.simplices:
                triangle = Polygon(points[simplex])
                triangles.append(triangle)
                
            # 创建GeoDataFrame
            result_gdf = gpd.GeoDataFrame(geometry=triangles, crs=points_gdf.crs)
            
            return result_gdf, "Delaunay三角网生成成功"
        except Exception as e:
            return gpd.GeoDataFrame(), f"Delaunay三角网生成失败: {str(e)}"


class AdvancedMeasurementTool:
    """高级测量工具类，支持多种测量模式"""
    def __init__(self, canvas):
        self.canvas = canvas
        self.points = []
        self.is_measuring = False
        self.measurement_type = "distance"  # distance, area, height, angle
        
    def start_measurement(self, measurement_type="distance"):
        """开始测量"""
        self.points = []
        self.is_measuring = True
        self.measurement_type = measurement_type
        
    def add_point(self, point):
        """添加测量点"""
        if self.is_measuring:
            self.points.append(point)
            
    def end_measurement(self):
        """结束测量"""
        self.is_measuring = False
        return self.calculate_measurement()
        
    def calculate_measurement(self):
        """计算测量结果"""
        if len(self.points) < 2:
            return {"value": 0.0, "unit": "m", "type": self.measurement_type}
            
        if self.measurement_type == "distance":
            return self.calculate_distance()
        elif self.measurement_type == "area":
            return self.calculate_area()
        elif self.measurement_type == "angle":
            return self.calculate_angle()
            
    def calculate_distance(self):
        """计算距离（考虑地球曲率）"""
        if len(self.points) < 2:
            return {"value": 0.0, "unit": "m", "type": "distance"}
            
        # 使用大圆距离公式计算球面距离
        total_distance = 0.0
        for i in range(len(self.points) - 1):
            lon1, lat1 = self.points[i]
            lon2, lat2 = self.points[i+1]
            
            # 将经纬度转换为弧度
            lat1_rad = math.radians(lat1)
            lon1_rad = math.radians(lon1)
            lat2_rad = math.radians(lat2)
            lon2_rad = math.radians(lon2)
            
            # 计算大圆距离
            dlon = lon2_rad - lon1_rad
            dlat = lat2_rad - lat1_rad
            a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
            distance = 6371000 * c  # 地球半径6371km
            
            total_distance += distance
            
        return {
            "value": total_distance,
            "unit": "m",
            "type": "distance",
            "points": len(self.points)
        }
        
    def calculate_area(self):
        """计算面积（考虑地球曲率）"""
        if len(self.points) < 3:
            return {"value": 0.0, "unit": "m²", "type": "area"}
            
        # 使用球面多边形面积计算公式
        points_rad = [(math.radians(lon), math.radians(lat)) for lon, lat in self.points]
        
        # 确保多边形是闭合的
        if points_rad[0] != points_rad[-1]:
            points_rad.append(points_rad[0])
            
        # 计算球面多边形面积
        area = 0.0
        for i in range(len(points_rad) - 1):
            lon1, lat1 = points_rad[i]
            lon2, lat2 = points_rad[i+1]
            area += (lon2 - lon1) * (2 + math.sin(lat1) + math.sin(lat2))
            
        area = abs(area * 6371000**2 / 2.0)  # 地球半径6371km
        
        return {
            "value": area,
            "unit": "m²",
            "type": "area",
            "points": len(self.points)
        }
        
    def calculate_angle(self):
        """计算角度"""
        if len(self.points) < 3:
            return {"value": 0.0, "unit": "°", "type": "angle"}
            
        # 计算三个点之间的角度
        p1, p2, p3 = self.points[-3], self.points[-2], self.points[-1]
        
        # 计算向量
        v1 = (p1[0] - p2[0], p1[1] - p2[1])
        v2 = (p3[0] - p2[0], p3[1] - p2[1])
        
        # 计算向量长度
        v1_len = math.sqrt(v1[0]**2 + v1[1]**2)
        v2_len = math.sqrt(v2[0]**2 + v2[1]**2)
        
        # 计算点积
        dot = v1[0] * v2[0] + v1[1] * v2[1]
        
        # 计算角度
        angle = math.degrees(math.acos(dot / (v1_len * v2_len)))
        
        return {
            "value": angle,
            "unit": "°",
            "type": "angle",
            "points": len(self.points)
        }


class Terrain3DView(QWidget):
    """3D地形可视化组件"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("3D地形可视化")
        
        if not HAS_3D:
            layout = QVBoxLayout()
            layout.addWidget(QLabel("3D可视化功能不可用"))
            self.setLayout(layout)
            return
            
        self.setup_ui()
        
    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        
        # 创建3D图形画布
        self.fig = Figure(figsize=(10, 8))
        self.canvas = FigureCanvas(self.fig)
        self.ax = self.fig.add_subplot(111, projection='3d')
        
        # 控制面板
        control_group = QGroupBox("3D视图控制")
        control_layout = QHBoxLayout()
        
        # 旋转控制
        control_layout.addWidget(QLabel("旋转:"))
        self.rotation_dial = QDial()
        self.rotation_dial.setRange(0, 360)
        self.rotation_dial.setValue(45)
        self.rotation_dial.valueChanged.connect(self.update_3d_view)
        control_layout.addWidget(self.rotation_dial)
        
        # 倾斜控制
        control_layout.addWidget(QLabel("倾斜:"))
        self.tilt_dial = QDial()
        self.tilt_dial.setRange(0, 90)
        self.tilt_dial.setValue(30)
        self.tilt_dial.valueChanged.connect(self.update_3d_view)
        control_layout.addWidget(self.tilt_dial)
        
        # 缩放控制
        control_layout.addWidget(QLabel("缩放:"))
        self.zoom_slider = QSlider(Qt.Horizontal)
        self.zoom_slider.setRange(10, 200)
        self.zoom_slider.setValue(100)
        self.zoom_slider.valueChanged.connect(self.update_3d_view)
        control_layout.addWidget(self.zoom_slider)
        
        control_group.setLayout(control_layout)
        
        layout.addWidget(control_group)
        layout.addWidget(self.canvas)
        
        # 初始化3D数据
        self.init_3d_data()
        
    def init_3d_data(self):
        """初始化3D数据"""
        # 生成示例地形数据
        x = np.linspace(-5, 5, 100)
        y = np.linspace(-5, 5, 100)
        X, Y = np.meshgrid(x, y)
        
        # 创建地形高度
        Z = np.sin(np.sqrt(X**2 + Y**2))
        
        # 绘制3D表面
        self.surface = self.ax.plot_surface(X, Y, Z, cmap=cm.terrain, alpha=0.8)
        
        # 设置轴标签
        self.ax.set_xlabel('X')
        self.ax.set_ylabel('Y')
        self.ax.set_zlabel('Z')
        
        # 添加颜色条
        self.fig.colorbar(self.surface, ax=self.ax, shrink=0.5, aspect=5)
        
        self.canvas.draw()
        
    def update_3d_view(self):
        """更新3D视图"""
        # 设置视角
        elevation = self.tilt_dial.value()
        azimuth = self.rotation_dial.value()
        self.ax.view_init(elev=elevation, azim=azimuth)
        
        # 设置缩放
        scale = self.zoom_slider.value() / 100.0
        self.ax.set_box_aspect([scale, scale, scale*0.5])
        
        self.canvas.draw()
        
    def load_dem_data(self, dem_file):
        """从DEM文件加载数据"""
        try:
            with rasterio.open(dem_file) as src:
                dem_data = src.read(1)
                transform = src.transform
                
                # 创建坐标网格
                rows, cols = dem_data.shape
                x = np.linspace(transform[2], transform[2] + transform[0] * cols, cols)
                y = np.linspace(transform[5], transform[5] + transform[4] * rows, rows)
                X, Y = np.meshgrid(x, y)
                
                # 清除现有表面
                self.ax.clear()
                
                # 绘制新的表面
                self.surface = self.ax.plot_surface(X, Y, dem_data, cmap=cm.terrain, alpha=0.8)
                
                # 设置轴标签
                self.ax.set_xlabel('X')
                self.ax.set_ylabel('Y')
                self.ax.set_zlabel('Elevation')
                
                # 添加颜色条
                self.fig.colorbar(self.surface, ax=self.ax, shrink=0.5, aspect=5)
                
                self.canvas.draw()
                return True, "DEM数据加载成功"
        except Exception as e:
            return False, f"DEM数据加载失败: {str(e)}"


class AdvancedMainWindow(QMainWindow):
    """高级主窗口"""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("高级地理测绘系统")
        self.setGeometry(100, 100, 1400, 900)
        
        # 初始化设置
        self.settings = QSettings("MyCompany", "AdvancedGIS")
        
        # 初始化地图画布
        self.canvas = MapCanvas(self)
        self.setCentralWidget(self.canvas)
        
        # 初始化工具
        self.spatial_tools = SpatialAnalysisTools(self.canvas)
        self.measurement_tool = AdvancedMeasurementTool(self.canvas)
        self.gps_tracker = GPSTracker()
        self.gps_layer = None
        
        # 初始化3D视图
        self.terrain_3d_view = None
        
        # 存储加载的数据
        self.loaded_data = {}
        
        # 设置UI
        self.setup_ui()
        
        # 连接信号
        self.canvas.mouse_clicked.connect(self.on_map_click)
        self.canvas.mouse_moved.connect(self.on_mouse_moved)
        
    def setup_ui(self):
        """设置UI界面"""
        # 创建菜单栏
        self.create_menus()
        
        # 创建工具栏
        self.create_toolbars()
        
        # 创建面板
        self.create_dock_widgets()
        
        # 创建状态栏
        self.statusBar().showMessage("就绪")
        
    def create_menus(self):
        """创建菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu("文件")
        
        new_action = QAction("新建项目", self)
        new_action.triggered.connect(self.new_project)
        file_menu.addAction(new_action)
        
        open_action = QAction("打开数据", self)
        open_action.triggered.connect(self.open_data)
        file_menu.addAction(open_action)
        
        save_action = QAction("保存数据", self)
        save_action.triggered.connect(self.save_data)
        file_menu.addAction(save_action)
        
        file_menu.addSeparator()
        
        export_action = QAction("导出地图", self)
        export_action.triggered.connect(self.export_map)
        file_menu.addAction(export_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("退出", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 编辑菜单
        edit_menu = menubar.addMenu("编辑")
        
        undo_action = QAction("撤销", self)
        edit_menu.addAction(undo_action)
        
        redo_action = QAction("重做", self)
        edit_menu.addAction(redo_action)
        
        edit_menu.addSeparator()
        
        settings_action = QAction("设置", self)
        settings_action.triggered.connect(self.show_settings)
        edit_menu.addAction(settings_action)
        
        # 视图菜单
        view_menu = menubar.addMenu("视图")
        
        zoom_in_action = QAction("放大", self)
        zoom_in_action.triggered.connect(self.canvas.zoom_in)
        view_menu.addAction(zoom_in_action)
        
        zoom_out_action = QAction("缩小", self)
        zoom_out_action.triggered.connect(self.canvas.zoom_out)
        view_menu.addAction(zoom_out_action)
        
        zoom_full_action = QAction("全图", self)
        zoom_full_action.triggered.connect(self.canvas.zoom_full)
        view_menu.addAction(zoom_full_action)
        
        view_menu.addSeparator()
        
        # 3D视图
        if HAS_3D:
            view_3d_action = QAction("3D视图", self)
            view_3d_action.triggered.connect(self.show_3d_view)
            view_menu.addAction(view_3d_action)
            
        # 工具菜单
        tools_menu = menubar.addMenu("工具")
        
        measure_action = QAction("测量", self)
        measure_action.triggered.connect(self.start_measurement)
        tools_menu.addAction(measure_action)
        
        gps_action = QAction("GPS跟踪", self)
        gps_action.triggered.connect(self.toggle_gps_tracking)
        tools_menu.addAction(gps_action)
        
        tools_menu.addSeparator()
        
        buffer_action = QAction("缓冲区分析", self)
        buffer_action.triggered.connect(self.buffer_analysis)
        tools_menu.addAction(buffer_action)
        
        intersect_action = QAction("相交分析", self)
        intersect_action.triggered.connect(self.intersect_analysis)
        tools_menu.addAction(intersect_action)
        
        voronoi_action = QAction("Voronoi图", self)
        voronoi_action.triggered.connect(self.voronoi_analysis)
        tools_menu.addAction(voronoi_action)
        
        delaunay_action = QAction("Delaunay三角网", self)
        delaunay_action.triggered.connect(self.delaunay_analysis)
        tools_menu.addAction(delaunay_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu("帮助")
        
        about_action = QAction("关于", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
    def create_toolbars(self):
        """创建工具栏"""
        # 主工具栏
        main_toolbar = QToolBar("主工具栏")
        main_toolbar.setIconSize(QSize(32, 32))
        self.addToolBar(main_toolbar)
        
        # 添加工具按钮
        zoom_in_action = QAction("放大", self)
        zoom_in_action.triggered.connect(self.canvas.zoom_in)
        main_toolbar.addAction(zoom_in_action)
        
        zoom_out_action = QAction("缩小", self)
        zoom_out_action.triggered.connect(self.canvas.zoom_out)
        main_toolbar.addAction(zoom_out_action)
        
        zoom_full_action = QAction("全图", self)
        zoom_full_action.triggered.connect(self.canvas.zoom_full)
        main_toolbar.addAction(zoom_full_action)
        
        main_toolbar.addSeparator()
        
        measure_action = QAction("测量", self)
        measure_action.triggered.connect(self.start_measurement)
        main_toolbar.addAction(measure_action)
        
        gps_action = QAction("GPS跟踪", self)
        gps_action.triggered.connect(self.toggle_gps_tracking)
        main_toolbar.addAction(gps_action)
        
        main_toolbar.addSeparator()
        
        # 绘图工具栏
        draw_toolbar = QToolBar("绘图工具栏")
        draw_toolbar.setIconSize(QSize(32, 32))
        self.addToolBar(draw_toolbar)
        
        point_action = QAction("点", self)
        point_action.triggered.connect(lambda: self.start_drawing('point'))
        draw_toolbar.addAction(point_action)
        
        line_action = QAction("线", self)
        line_action.triggered.connect(lambda: self.start_drawing('line'))
        draw_toolbar.addAction(line_action)
        
        polygon_action = QAction("多边形", self)
        polygon_action.triggered.connect(lambda: self.start_drawing('polygon'))
        draw_toolbar.addAction(polygon_action)
        
    def create_dock_widgets(self):
        """创建停靠面板"""
        # 图层管理面板
        self.layer_manager = LayerManagerWidget(self)
        self.addDockWidget(Qt.RightDockWidgetArea, self.layer_manager)
        
        # 属性面板
        self.attribute_widget = AttributeWidget(self)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.attribute_widget)
        
    def new_project(self):
        """新建项目"""
        reply = QMessageBox.question(self, "新建项目", 
                                   "是否保存当前项目并创建新项目?",
                                   QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
        
        if reply == QMessageBox.Yes:
            self.save_data()
            self.clear_project()
        elif reply == QMessageBox.No:
            self.clear_project()
            
    def clear_project(self):
        """清除项目"""
        self.canvas.clear_layers()
        self.loaded_data.clear()
        self.layer_manager.update_layers()
        self.statusBar().showMessage("已创建新项目")
        
    def open_data(self):
        """打开地理数据文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "打开地理数据文件", "", 
            "地理数据文件 (*.shp *.geojson *.gpkg *.kml);;所有文件 (*)"
        )
        
        if file_path:
            # 创建数据模型
            model = GeoDataFrameModel()
            success, message = model.load_file(file_path)
            
            if success:
                # 生成唯一图层名
                base_name = file_path.split('/')[-1].split('.')[0]
                layer_name = base_name
                counter = 1
                while layer_name in self.loaded_data:
                    layer_name = f"{base_name}_{counter}"
                    counter += 1
                    
                # 存储数据
                self.loaded_data[layer_name] = model
                
                # 添加到图层管理器
                self.layer_manager.add_layer(layer_name)
                
                # 绘制到地图
                self.canvas.add_layer(model.gdf, layer_name)
                
                # 缩放到数据范围
                bounds = model.get_bounds()
                self.canvas.zoom_to_extent(bounds)
                
                self.statusBar().showMessage(f"已加载: {file_path}")
            else:
                QMessageBox.critical(self, "错误", message)
                
    def save_data(self):
        """保存地理数据"""
        if not self.loaded_data:
            QMessageBox.information(self, "信息", "没有数据可保存")
            return
            
        # 选择要保存的图层
        layer_names = list(self.loaded_data.keys())
        layer_name, ok = QInputDialog.getItem(self, "选择图层", "图层:", layer_names, 0, False)
        
        if ok and layer_name:
            file_path, _ = QFileDialog.getSaveFileName(
                self, "保存地理数据", f"{layer_name}.shp", 
                "Shapefile (*.shp);;GeoJSON (*.geojson);;GPKG (*.gpkg)"
            )
            
            if file_path:
                model = self.loaded_data[layer_name]
                success, message = model.save_file(file_path)
                
                if success:
                    self.statusBar().showMessage(f"已保存: {file_path}")
                else:
                    QMessageBox.critical(self, "错误", message)
                    
    def export_map(self):
        """导出地图为图像"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出地图", "", 
            "PNG图像 (*.png);;JPEG图像 (*.jpg);;PDF文档 (*.pdf);;SVG矢量图 (*.svg)"
        )
        
        if file_path:
            try:
                self.canvas.fig.savefig(file_path, dpi=300, bbox_inches='tight')
                self.statusBar().showMessage(f"地图已导出: {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导出失败: {str(e)}")
                
    def show_settings(self):
        """显示设置对话框"""
        dialog = QDialog(self)
        dialog.setWindowTitle("设置")
        dialog.setModal(True)
        dialog.resize(400, 300)
        
        layout = QVBoxLayout(dialog)
        
        # 地图设置
        map_group = QGroupBox("地图设置")
        map_layout = QFormLayout()
        
        # 背景颜色
        bg_color_btn = QPushButton("选择颜色")
        bg_color_btn.clicked.connect(lambda: self.choose_bg_color(bg_color_btn))
        map_layout.addRow("背景颜色:", bg_color_btn)
        
        # 网格显示
        grid_check = QCheckBox("显示网格")
        grid_check.setChecked(True)
        grid_check.toggled.connect(self.toggle_grid)
        map_layout.addRow("网格:", grid_check)
        
        map_group.setLayout(map_layout)
        layout.addWidget(map_group)
        
        # 按钮
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        
        dialog.exec_()
        
    def choose_bg_color(self, button):
        """选择背景颜色"""
        color = QColorDialog.getColor()
        if color.isValid():
            button.setStyleSheet(f"background-color: {color.name()}")
            self.canvas.ax.set_facecolor(color.name())
            self.canvas.draw()
            
    def toggle_grid(self, checked):
        """切换网格显示"""
        if checked:
            self.canvas.draw_grid()
        else:
            # 清除网格
            for line in self.canvas.ax.get_lines():
                line.remove()
            self.canvas.draw()
            
    def show_3d_view(self):
        """显示3D视图"""
        if not HAS_3D:
            QMessageBox.information(self, "信息", "3D可视化功能不可用")
            return
            
        if self.terrain_3d_view is None:
            self.terrain_3d_view = Terrain3DView(self)
            
        self.terrain_3d_view.show()
        
    def start_measurement(self):
        """开始测量"""
        types = ["距离", "面积", "角度"]
        type_str, ok = QInputDialog.getItem(self, "选择测量类型", "类型:", types, 0, False)
        
        if ok:
            measurement_type = type_str.lower()
            self.measurement_tool.start_measurement(measurement_type)
            self.statusBar().showMessage(f"开始{type_str}测量，请在地图上点击点")
            
    def toggle_gps_tracking(self):
        """切换GPS跟踪"""
        if self.gps_tracker.is_active:
            self.gps_tracker.stop_tracking()
            self.statusBar().showMessage("GPS跟踪已停止")
        else:
            self.gps_tracker.start_tracking()
            self.statusBar().showMessage("GPS跟踪已启动")
            
    def on_map_click(self, x, y):
        """处理地图点击事件"""
        # 如果正在测量，添加点
        if self.measurement_tool.is_measuring:
            self.measurement_tool.add_point((x, y))
            
            # 如果测量完成，显示结果
            if self.measurement_tool.measurement_type == 'angle' and len(self.measurement_tool.points) >= 3:
                result = self.measurement_tool.end_measurement()
                self.statusBar().showMessage(f"角度: {result['value']:.2f}°")
            elif self.measurement_tool.measurement_type == 'distance' and len(self.measurement_tool.points) >= 2:
                result = self.measurement_tool.end_measurement()
                self.statusBar().showMessage(f"距离: {result['value']:.2f}米")
            elif self.measurement_tool.measurement_type == 'area' and len(self.measurement_tool.points) >= 3:
                result = self.measurement_tool.end_measurement()
                self.statusBar().showMessage(f"面积: {result['value']:.2f}平方米")
                
    def on_mouse_moved(self, x, y):
        """处理鼠标移动事件"""
        # 更新状态栏坐标显示
        self.statusBar().showMessage(f"坐标: {x:.6f}, {y:.6f}")
        
    def buffer_analysis(self):
        """缓冲区分析"""
        if not self.loaded_data:
            QMessageBox.information(self, "信息", "没有可用的数据")
            return
            
        # 选择图层
        layer_names = list(self.loaded_data.keys())
        layer_name, ok = QInputDialog.getItem(self, "选择图层", "图层:", layer_names, 0, False)
        
        if ok and layer_name:
            # 输入缓冲区距离
            distance, ok = QInputDialog.getDouble(self, "缓冲区距离", "距离 (米):", 100, 0, 10000, 2)
            
            if ok:
                model = self.loaded_data[layer_name]
                result_gdf, message = self.spatial_tools.buffer_analysis(model.gdf, distance)
                
                if not result_gdf.empty:
                    # 创建结果图层
                    result_name = f"{layer_name}_buffer_{distance}m"
                    result_model = GeoDataFrameModel()
                    result_model.gdf = result_gdf
                    result_model.crs = model.crs
                    
                    # 存储结果
                    self.loaded_data[result_name] = result_model
                    
                    # 添加到图层管理器
                    self.layer_manager.add_layer(result_name)
                    
                    # 绘制到地图
                    self.canvas.add_layer(result_gdf, result_name, color='orange', alpha=0.3)
                    
                    self.statusBar().showMessage(message)
                else:
                    QMessageBox.critical(self, "错误", message)
                    
    def intersect_analysis(self):
        """相交分析"""
        if len(self.loaded_data) < 2:
            QMessageBox.information(self, "信息", "需要至少两个图层")
            return
            
        # 选择第一个图层
        layer_names = list(self.loaded_data.keys())
        layer1_name, ok = QInputDialog.getItem(self, "选择第一个图层", "图层:", layer_names, 0, False)
        
        if ok:
            # 选择第二个图层
            layer2_name, ok = QInputDialog.getItem(self, "选择第二个图层", "图层:", layer_names, 0, False)
            
            if ok:
                model1 = self.loaded_data[layer1_name]
                model2 = self.loaded_data[layer2_name]
                
                result_gdf, message = self.spatial_tools.intersect_analysis(model1.gdf, model2.gdf)
                
                if not result_gdf.empty:
                    # 创建结果图层
                    result_name = f"intersect_{layer1_name}_{layer2_name}"
                    result_model = GeoDataFrameModel()
                    result_model.gdf = result_gdf
                    result_model.crs = model1.crs
                    
                    # 存储结果
                    self.loaded_data[result_name] = result_model
                    
                    # 添加到图层管理器
                    self.layer_manager.add_layer(result_name)
                    
                    # 绘制到地图
                    self.canvas.add_layer(result_gdf, result_name, color='purple', alpha=0.5)
                    
                    self.statusBar().showMessage(message)
                else:
                    QMessageBox.critical(self, "错误", message)
                    
    def voronoi_analysis(self):
        """Voronoi图分析"""
        if not self.loaded_data:
            QMessageBox.information(self, "信息", "没有可用的数据")
            return
            
        # 选择点图层
        layer_names = list(self.loaded_data.keys())
        layer_name, ok = QInputDialog.getItem(self, "选择点图层", "图层:", layer_names, 0, False)
        
        if ok and layer_name:
            model = self.loaded_data[layer_name]
            
            # 检查是否为点数据
            if not all(model.gdf.geometry.type.isin(['Point', 'MultiPoint'])):
                QMessageBox.warning(self, "警告", "Voronoi图分析需要点数据")
                return
                
            result_gdf, message = self.spatial_tools.voronoi_diagram(model.gdf)
            
            if not result_gdf.empty:
                # 创建结果图层
                result_name = f"voronoi_{layer_name}"
                result_model = GeoDataFrameModel()
                result_model.gdf = result_gdf
                result_model.crs = model.crs
                
                # 存储结果
                self.loaded_data[result_name] = result_model
                
                # 添加到图层管理器
                self.layer_manager.add_layer(result_name)
                
                # 绘制到地图
                self.canvas.add_layer(result_gdf, result_name, color='green', alpha=0.3)
                
                self.statusBar().showMessage(message)
            else:
                QMessageBox.critical(self, "错误", message)
                
    def delaunay_analysis(self):
        """Delaunay三角网分析"""
        if not self.loaded_data:
            QMessageBox.information(self, "信息", "没有可用的数据")
            return
            
        # 选择点图层
        layer_names = list(self.loaded_data.keys())
        layer_name, ok = QInputDialog.getItem(self, "选择点图层", "图层:", layer_names, 0, False)
        
        if ok and layer_name:
            model = self.loaded_data[layer_name]
            
            # 检查是否为点数据
            if not all(model.gdf.geometry.type.isin(['Point', 'MultiPoint'])):
                QMessageBox.warning(self, "警告", "Delaunay三角网分析需要点数据")
                return
                
            result_gdf, message = self.spatial_tools.delaunay_triangulation(model.gdf)
            
            if not result_gdf.empty:
                # 创建结果图层
                result_name = f"delaunay_{layer_name}"
                result_model = GeoDataFrameModel()
                result_model.gdf = result_gdf
                result_model.crs = model.crs
                
                # 存储结果
                self.loaded_data[result_name] = result_model
                
                # 添加到图层管理器
                self.layer_manager.add_layer(result_name)
                
                # 绘制到地图
                self.canvas.add_layer(result_gdf, result_name, color='red', alpha=0.3)
                
                self.statusBar().showMessage(message)
            else:
                QMessageBox.critical(self, "错误", message)
                
    def start_drawing(self, drawing_type):
        """开始绘制"""
        self.canvas.start_drawing(drawing_type)
        self.statusBar().showMessage(f"开始绘制{drawing_type}，点击地图添加点，右键结束")
        
    def show_about(self):
        """显示关于对话框"""
        QMessageBox.about(self, "关于", 
            "高级地理测绘系统\n\n"
            "版本: 2.0\n"
            "基于PyQt5和GeoPandas开发\n"
            "提供强大的地理信息处理和分析功能"
        )


class LayerManagerWidget(QDockWidget):
    """图层管理面板"""
    def __init__(self, parent=None):
        super().__init__("图层管理", parent)
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        
        self.main_window = parent
        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderLabel("图层")
        self.tree_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree_widget.customContextMenuRequested.connect(self.show_context_menu)
        
        self.setWidget(self.tree_widget)
        
    def add_layer(self, layer_name):
        """添加图层到管理器"""
        item = QTreeWidgetItem(self.tree_widget)
        item.setText(0, layer_name)
        item.setCheckState(0, Qt.Checked)
        
    def update_layers(self):
        """更新图层列表"""
        self.tree_widget.clear()
        for layer_name in self.main_window.loaded_data.keys():
            self.add_layer(layer_name)
            
    def show_context_menu(self, position):
        """显示上下文菜单"""
        item = self.tree_widget.itemAt(position)
        if not item:
            return
            
        layer_name = item.text(0)
        
        menu = QMenu(self)
        
        # 图层操作
        zoom_action = QAction("缩放至图层", self)
        zoom_action.triggered.connect(lambda: self.zoom_to_layer(layer_name))
        menu.addAction(zoom_action)
        
        remove_action = QAction("移除图层", self)
        remove_action.triggered.connect(lambda: self.remove_layer(layer_name))
        menu.addAction(remove_action)
        
        menu.exec_(self.tree_widget.mapToGlobal(position))
        
    def zoom_to_layer(self, layer_name):
        """缩放至图层"""
        if layer_name in self.main_window.loaded_data:
            model = self.main_window.loaded_data[layer_name]
            bounds = model.get_bounds()
            self.main_window.canvas.zoom_to_extent(bounds)
            
    def remove_layer(self, layer_name):
        """移除图层"""
        if layer_name in self.main_window.loaded_data:
            # 从地图移除
            self.main_window.canvas.remove_layer(layer_name)
            
            # 从数据存储移除
            del self.main_window.loaded_data[layer_name]
            
            # 从树形控件移除
            for i in range(self.tree_widget.topLevelItemCount()):
                item = self.tree_widget.topLevelItem(i)
                if item.text(0) == layer_name:
                    self.tree_widget.takeTopLevelItem(i)
                    break


class AttributeWidget(QDockWidget):
    """属性面板"""
    def __init__(self, parent=None):
        super().__init__("属性", parent)
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["属性", "值"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        
        self.setWidget(self.table)
        
    def show_attributes(self, feature):
        """显示要素属性"""
        self.table.setRowCount(0)
        
        if not feature:
            return
            
        # 这里应该有显示要素属性的代码
        pass


def main():
    """主函数"""
    # 创建QApplication实例
    app = QApplication(sys.argv)
    
    # 设置应用程序信息
    app.setApplicationName("高级地理测绘系统")
    app.setApplicationVersion("2.0")
    app.setOrganizationName("MyCompany")
    
    # 创建主窗口
    window = AdvancedMainWindow()
    window.show()
    
    # 运行应用
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()