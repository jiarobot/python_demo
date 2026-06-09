import sys
import numpy as np
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QToolBar, QAction, QStatusBar, QDockWidget, QListWidget, QLabel,
                             QMessageBox, QFileDialog, QSlider, QSpinBox, QDoubleSpinBox,
                             QTabWidget, QTextEdit, QComboBox, QPushButton, QGroupBox,
                             QCheckBox, QProgressBar, QSplitter, QTableWidget, QTableWidgetItem,
                             QTreeWidget, QTreeWidgetItem, QHeaderView, QDialog, QDialogButtonBox,
                             QFormLayout, QLineEdit, QMenu, QStyleFactory)
from PyQt5.QtCore import Qt, QSize, pyqtSignal, QPointF, QTimer, QThread, pyqtSlot, QDateTime
from PyQt5.QtGui import QIcon, QColor, QPixmap, QPainter, QPen, QFont, QPalette
import matplotlib
matplotlib.rc("font", family='Microsoft YaHei')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d import Axes3D
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point, LineString, Polygon
import cartopy.crs as ccrs
import cartopy.feature as cfeature
#from cartopy.io.img_tiles import OSM, StamenTerrain
from datetime import datetime, timedelta
import json
import math
import time
import requests
from io import StringIO
import csv
from scipy import interpolate
from pykrige.ok import OrdinaryKriging
import netCDF4 as nc
import folium
from folium import plugins
import webbrowser
import tempfile
import os


class MarineMapCanvas(FigureCanvas):
    """海域地图画布组件"""
    
    # 定义信号
    mapClicked = pyqtSignal(float, float)  # 经度, 纬度
    
    def __init__(self, parent=None, width=10, height=8, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        super().__init__(self.fig)
        self.setParent(parent)
        
        # 设置地图投影
        self.projection = ccrs.PlateCarree()
        self.ax = self.fig.add_subplot(111, projection=self.projection)
        
        # 底图选项
        self.tiles = None
        self.basemap_type = "default"  # 默认底图
        
        # 交互状态
        self.is_panning = False
        self.is_zooming = False
        
        # 初始化地图
        self.init_map()
        
        # 连接事件
        self.mpl_connect('button_press_event', self.on_click)
        self.mpl_connect('motion_notify_event', self.on_motion)
        self.mpl_connect('scroll_event', self.on_scroll)
        
    def init_map(self):
        """初始化地图显示"""
        # 清除现有内容
        self.ax.clear()
        
        # 根据底图类型设置不同的底图
        if self.basemap_type == "satellite":
            # 使用Stamen的卫星影像
            self.tiles = StamenTerrain()
            self.ax.add_image(self.tiles, 8)
        elif self.basemap_type == "terrain":
            # 使用Stamen的地形图
            self.tiles = StamenTerrain(style='terrain-background')
            self.ax.add_image(self.tiles, 8)
        else:
            # 默认底图 - 使用cartopy特征
            self.ax.add_feature(cfeature.LAND, color='lightgray')
            self.ax.add_feature(cfeature.OCEAN, color='lightblue')
            self.ax.add_feature(cfeature.COASTLINE, linewidth=0.5)
            self.ax.add_feature(cfeature.BORDERS, linestyle=':', linewidth=0.5)
            self.ax.add_feature(cfeature.LAKES, alpha=0.5, color='lightblue')
            self.ax.add_feature(cfeature.RIVERS, color='lightblue')
        
        # 设置网格线
        self.ax.gridlines(draw_labels=True, dms=True, x_inline=False, y_inline=False)
        
        # 设置默认视图
        self.ax.set_global()
        
        self.draw()
        
    def set_basemap(self, basemap_type):
        """设置底图类型"""
        self.basemap_type = basemap_type
        self.init_map()
        
    def set_view(self, lon_min, lon_max, lat_min, lat_max):
        """设置地图视图范围"""
        self.ax.set_extent([lon_min, lon_max, lat_min, lat_max], crs=self.projection)
        self.draw()
        
    def plot_points(self, lons, lats, **kwargs):
        """绘制点数据"""
        points = self.ax.scatter(lons, lats, transform=self.projection, **kwargs)
        self.draw()
        return points
        
    def plot_line(self, lons, lats, **kwargs):
        """绘制线数据"""
        line = self.ax.plot(lons, lats, transform=self.projection, **kwargs)
        self.draw()
        return line
        
    def plot_polygon(self, lons, lats, **kwargs):
        """绘制多边形数据"""
        polygon = self.ax.fill(lons, lats, transform=self.projection, **kwargs)
        self.draw()
        return polygon
        
    def plot_contour(self, lons, lats, values, **kwargs):
        """绘制等值线"""
        contour = self.ax.contour(lons, lats, values, transform=self.projection, **kwargs)
        self.ax.clabel(contour, inline=True, fontsize=8)
        self.draw()
        return contour
        
    def plot_quiver(self, lons, lats, u, v, **kwargs):
        """绘制矢量场（如流速、风向）"""
        quiver = self.ax.quiver(lons, lats, u, v, transform=self.projection, **kwargs)
        self.draw()
        return quiver
        
    def clear_plots(self):
        """清除所有绘制的内容"""
        for artist in self.ax.collections + self.ax.lines + self.ax.patches:
            artist.remove()
        self.draw()
        
    def on_click(self, event):
        """处理地图点击事件"""
        if event.inaxes == self.ax and event.button == 1:  # 左键点击
            lon, lat = event.xdata, event.ydata
            self.mapClicked.emit(lon, lat)
            
    def on_motion(self, event):
        """处理鼠标移动事件"""
        if event.inaxes == self.ax:
            # 更新状态栏显示鼠标位置的经纬度
            pass
            
    def on_scroll(self, event):
        """处理鼠标滚轮事件"""
        if event.inaxes == self.ax:
            # 实现缩放功能
            cur_xlim = self.ax.get_xlim()
            cur_ylim = self.ax.get_ylim()
            
            xdata = event.xdata
            ydata = event.ydata
            
            scale_factor = 1.5 if event.button == 'up' else 1/1.5
            
            new_width = (cur_xlim[1] - cur_xlim[0]) * scale_factor
            new_height = (cur_ylim[1] - cur_ylim[0]) * scale_factor
            
            relx = (cur_xlim[1] - xdata) / (cur_xlim[1] - cur_xlim[0])
            rely = (cur_ylim[1] - ydata) / (cur_ylim[1] - cur_ylim[0])
            
            self.ax.set_xlim([xdata - new_width * (1 - relx), xdata + new_width * relx])
            self.ax.set_ylim([ydata - new_height * (1 - rely), ydata + new_height * rely])
            
            self.draw()


class ThreeDMapCanvas(FigureCanvas):
    """3D海域地图画布组件"""
    
    def __init__(self, parent=None, width=10, height=8, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        super().__init__(self.fig)
        self.setParent(parent)
        
        # 创建3D轴
        self.ax = self.fig.add_subplot(111, projection='3d')
        
        # 初始化3D地图
        self.init_3d_map()
        
    def init_3d_map(self):
        """初始化3D地图"""
        self.ax.clear()
        
        # 设置标签
        self.ax.set_xlabel('经度')
        self.ax.set_ylabel('纬度')
        self.ax.set_zlabel('深度/高程')
        
        # 反转Z轴以便深度向下为正
        self.ax.invert_zaxis()
        
        self.draw()
        
    def plot_bathymetry(self, lons, lats, depths, **kwargs):
        """绘制海底地形"""
        surf = self.ax.plot_surface(lons, lats, depths, **kwargs)
        self.draw()
        return surf
        
    def plot_3d_route(self, lons, lats, depths, **kwargs):
        """绘制3D航线"""
        line = self.ax.plot(lons, lats, depths, **kwargs)
        self.draw()
        return line
        
    def set_view(self, elev=None, azim=None):
        """设置3D视图角度"""
        if elev is not None:
            self.ax.elev = elev
        if azim is not None:
            self.ax.azim = azim
        self.draw()


class MeasurementTool:
    """增强版测量工具类"""
    
    def __init__(self, map_canvas):
        self.map_canvas = map_canvas
        self.points = []
        self.line = None
        self.polygon = None
        self.distance = 0.0
        self.area = 0.0
        self.is_measuring = False
        self.is_area_mode = False
        
    def start_measurement(self, event, area_mode=False):
        """开始测量"""
        self.is_area_mode = area_mode
        
        if event.inaxes == self.map_canvas.ax:
            lon, lat = event.xdata, event.ydata
            self.points.append((lon, lat))
            
            # 绘制点
            self.map_canvas.ax.plot(lon, lat, 'ro', markersize=5, transform=self.map_canvas.projection)
            
            # 如果有多于一个点，绘制线
            if len(self.points) > 1:
                lons = [p[0] for p in self.points]
                lats = [p[1] for p in self.points]
                
                if self.line:
                    self.line.remove()
                    
                self.line, = self.map_canvas.ax.plot(lons, lats, 'r-', transform=self.map_canvas.projection)
                
                # 计算距离
                self.calculate_distance()
                
            # 如果是面积模式且有至少三个点，绘制多边形
            if self.is_area_mode and len(self.points) >= 3:
                if self.polygon:
                    self.polygon.remove()
                    
                lons = [p[0] for p in self.points]
                lats = [p[1] for p in self.points]
                self.polygon = self.map_canvas.ax.fill(lons, lats, alpha=0.3, color='red', 
                                                     transform=self.map_canvas.projection)[0]
                
                # 计算面积
                self.calculate_area()
                
            self.map_canvas.draw()
            
    def calculate_distance(self):
        """计算距离（使用大圆距离公式）"""
        self.distance = 0.0
        for i in range(1, len(self.points)):
            lon1, lat1 = self.points[i-1]
            lon2, lat2 = self.points[i]
            
            # 将角度转换为弧度
            lat1_rad = math.radians(lat1)
            lon1_rad = math.radians(lon1)
            lat2_rad = math.radians(lat2)
            lon2_rad = math.radians(lon2)
            
            # 大圆距离公式
            dlon = lon2_rad - lon1_rad
            dlat = lat2_rad - lat1_rad
            a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
            distance_km = 6371 * c  # 地球半径约6371km
            
            self.distance += distance_km
            
    def calculate_area(self):
        """计算多边形面积"""
        if len(self.points) < 3:
            return 0.0
            
        # 使用球面多边形面积计算公式
        lons = [p[0] for p in self.points]
        lats = [p[1] for p in self.points]
        
        # 创建一个多边形
        polygon = Polygon(zip(lons, lats))
        
        # 使用geopandas计算面积
        gdf = gpd.GeoDataFrame(geometry=[polygon], crs="EPSG:4326")
        gdf = gdf.to_crs(epsg=3857)  # 转换为投影坐标系以计算面积
        
        self.area = gdf.area.values[0] / 1e6  # 转换为平方公里
        
        return self.area
        
    def reset(self):
        """重置测量"""
        self.points = []
        if self.line:
            self.line.remove()
            self.line = None
        if self.polygon:
            self.polygon.remove()
            self.polygon = None
        self.distance = 0.0
        self.area = 0.0
        self.is_measuring = False
        self.is_area_mode = False
        self.map_canvas.draw()


class RoutePlanner:
    """增强版航线规划类"""
    
    def __init__(self, map_canvas):
        self.map_canvas = map_canvas
        self.waypoints = []
        self.route_line = None
        self.waypoint_markers = []
        self.waypoint_labels = []
        
    def add_waypoint(self, lon, lat, name=None):
        """添加航点"""
        if name is None:
            name = f"WP{len(self.waypoints)+1}"
            
        self.waypoints.append({"lon": lon, "lat": lat, "name": name})
        self.update_route()
        
    def remove_waypoint(self, index):
        """移除航点"""
        if 0 <= index < len(self.waypoints):
            self.waypoints.pop(index)
            self.update_route()
            
    def update_waypoint(self, index, lon, lat, name=None):
        """更新航点"""
        if 0 <= index < len(self.waypoints):
            self.waypoints[index]["lon"] = lon
            self.waypoints[index]["lat"] = lat
            if name:
                self.waypoints[index]["name"] = name
            self.update_route()
            
    def update_route(self):
        """更新航线显示"""
        # 清除现有航点和航线
        if self.route_line:
            self.route_line.remove()
            self.route_line = None
            
        for marker in self.waypoint_markers:
            marker.remove()
        self.waypoint_markers = []
        
        for label in self.waypoint_labels:
            label.remove()
        self.waypoint_labels = []
            
        # 如果有航点，绘制航线和航点
        if len(self.waypoints) >= 1:
            lons = [w["lon"] for w in self.waypoints]
            lats = [w["lat"] for w in self.waypoints]
            
            # 绘制航线
            if len(self.waypoints) >= 2:
                self.route_line, = self.map_canvas.ax.plot(lons, lats, 'b-', linewidth=2, 
                                                         transform=self.map_canvas.projection)
            
            # 绘制航点
            for i, waypoint in enumerate(self.waypoints):
                marker = self.map_canvas.ax.plot(waypoint["lon"], waypoint["lat"], 'bo', 
                                               markersize=8, transform=self.map_canvas.projection)[0]
                self.waypoint_markers.append(marker)
                
                # 添加航点标签
                label = self.map_canvas.ax.text(waypoint["lon"], waypoint["lat"], waypoint["name"], 
                                              color='white', fontsize=8, ha='center', va='center',
                                              bbox=dict(facecolor='blue', alpha=0.7, boxstyle='round'),
                                              transform=self.map_canvas.projection)
                self.waypoint_labels.append(label)
            
        self.map_canvas.draw()
        
    def clear_route(self):
        """清除航线"""
        self.waypoints = []
        self.update_route()
        
    def calculate_route_length(self):
        """计算航线长度"""
        length = 0.0
        for i in range(1, len(self.waypoints)):
            lon1, lat1 = self.waypoints[i-1]["lon"], self.waypoints[i-1]["lat"]
            lon2, lat2 = self.waypoints[i]["lon"], self.waypoints[i]["lat"]
            
            # 将角度转换为弧度
            lat1_rad = math.radians(lat1)
            lon1_rad = math.radians(lon1)
            lat2_rad = math.radians(lat2)
            lon2_rad = math.radians(lon2)
            
            # 大圆距离公式
            dlon = lon2_rad - lon1_rad
            dlat = lat2_rad - lat1_rad
            a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
            distance_km = 6371 * c  # 地球半径约6371km
            
            length += distance_km
            
        return length
        
    def optimize_route(self, avoid_areas=None):
        """优化航线，避开指定区域"""
        # 这里可以实现航线优化算法
        # 例如使用A*算法避开障碍区域
        pass
        
    def export_route(self, filename, format="json"):
        """导出航线到文件"""
        if format == "json":
            route_data = {
                "waypoints": self.waypoints,
                "length_km": self.calculate_route_length(),
                "export_date": datetime.now().isoformat()
            }
            
            with open(filename, 'w') as f:
                json.dump(route_data, f, indent=4)
                
        elif format == "kml":
            # 创建KML文件
            kml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
<Document>
<name>航线规划</name>
<description>导出时间: {datetime.now().isoformat()}</description>
<Style id="yellowLineGreenPoly">
    <LineStyle>
        <color>7f00ffff</color>
        <width>4</width>
    </LineStyle>
    <PolyStyle>
        <color>7f00ff00</color>
    </PolyStyle>
</Style>
<Placemark>
    <name>航线</name>
    <description>航线长度: {self.calculate_route_length():.2f} km</description>
    <styleUrl>#yellowLineGreenPoly</styleUrl>
    <LineString>
        <extrude>1</extrude>
        <tessellate>1</tessellate>
        <altitudeMode>absolute</altitudeMode>
        <coordinates>
"""
            for waypoint in self.waypoints:
                kml_content += f"            {waypoint['lon']},{waypoint['lat']},0\n"
                
            kml_content += """        </coordinates>
    </LineString>
</Placemark>
</Document>
</kml>"""
            
            with open(filename, 'w') as f:
                f.write(kml_content)
                
        elif format == "gpx":
            # 创建GPX文件
            gpx_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="MarineSystem" xmlns="http://www.topografix.com/GPX/1/1">
<trk>
<name>航线规划</name>
<desc>导出时间: {datetime.now().isoformat()}</desc>
<trkseg>
"""
            for waypoint in self.waypoints:
                gpx_content += f"<trkpt lat=\"{waypoint['lat']}\" lon=\"{waypoint['lon']}\"></trkpt>\n"
                
            gpx_content += """</trkseg>
</trk>
</gpx>"""
            
            with open(filename, 'w') as f:
                f.write(gpx_content)
            
    def import_route(self, filename):
        """从文件导入航线"""
        if filename.endswith('.json'):
            with open(filename, 'r') as f:
                route_data = json.load(f)
                
            self.waypoints = route_data["waypoints"]
            self.update_route()
            return route_data["length_km"]
            
        elif filename.endswith('.kml') or filename.endswith('.gpx'):
            # 解析KML/GPX文件
            # 这里简化处理，实际应用中需要完整解析
            pass


class MarineDataManager:
    """增强版海域数据管理类"""
    
    def __init__(self):
        self.datasets = {}
        self.current_dataset = None
        self.data_sources = {
            "本地文件": self.load_from_file,
            "在线数据": self.load_from_url,
            "实时传感器": self.load_from_sensor
        }
        
    def load_data(self, source_type, source, name=None, **kwargs):
        """加载数据"""
        if source_type in self.data_sources:
            data = self.data_sources[source_type](source, **kwargs)
            
            if name is None:
                name = f"dataset_{len(self.datasets) + 1}"
                
            self.datasets[name] = data
            self.current_dataset = name
            
            return data
        else:
            raise ValueError(f"不支持的數據源類型: {source_type}")
        
    def load_from_file(self, filename, **kwargs):
        """从文件加载数据"""
        if filename.endswith('.csv'):
            return pd.read_csv(filename, **kwargs)
        elif filename.endswith('.shp'):
            return gpd.read_file(filename, **kwargs)
        elif filename.endswith('.nc') or filename.endswith('.netcdf'):
            return nc.Dataset(filename, 'r')
        else:
            raise ValueError("不支援的檔案格式")
            
    def load_from_url(self, url, **kwargs):
        """从URL加载数据"""
        response = requests.get(url)
        if response.status_code == 200:
            if url.endswith('.csv'):
                return pd.read_csv(StringIO(response.text), **kwargs)
            else:
                raise ValueError("不支援的線上數據格式")
        else:
            raise ConnectionError(f"無法獲取數據: HTTP {response.status_code}")
            
    def load_from_sensor(self, sensor_id, **kwargs):
        """从传感器加载实时数据"""
        # 这里可以实现传感器数据获取逻辑
        # 模拟数据
        return pd.DataFrame({
            'timestamp': [datetime.now()],
            'sensor_id': [sensor_id],
            'value': [np.random.random()]
        })
        
    def get_data(self, name=None):
        """获取数据"""
        if name is None:
            name = self.current_dataset
            
        if name in self.datasets:
            return self.datasets[name]
        else:
            raise KeyError(f"數據集 '{name}' 不存在")
            
    def remove_data(self, name):
        """移除数据"""
        if name in self.datasets:
            del self.datasets[name]
            if self.current_dataset == name:
                self.current_dataset = None if not self.datasets else next(iter(self.datasets.keys()))
                
    def list_datasets(self):
        """列出所有数据集"""
        return list(self.datasets.keys())
        
    def get_dataset_info(self, name=None):
        """获取数据集信息"""
        if name is None:
            name = self.current_dataset
            
        if name in self.datasets:
            data = self.datasets[name]
            info = {
                "名称": name,
                "类型": type(data).__name__,
                "大小": str(getattr(data, 'shape', 'N/A')),
                "列名": list(data.columns) if hasattr(data, 'columns') else 'N/A'
            }
            return info
        else:
            raise KeyError(f"數據集 '{name}' 不存在")


class AnalysisTools:
    """分析工具类"""
    
    @staticmethod
    def interpolate_data(x, y, z, method='linear', resolution=100):
        """数据插值"""
        if method == 'linear':
            # 线性插值
            xi = np.linspace(min(x), max(x), resolution)
            yi = np.linspace(min(y), max(y), resolution)
            xi, yi = np.meshgrid(xi, yi)
            zi = interpolate.griddata((x, y), z, (xi, yi), method='linear')
            return xi, yi, zi
            
        elif method == 'cubic':
            # 三次样条插值
            xi = np.linspace(min(x), max(x), resolution)
            yi = np.linspace(min(y), max(y), resolution)
            xi, yi = np.meshgrid(xi, yi)
            zi = interpolate.griddata((x, y), z, (xi, yi), method='cubic')
            return xi, yi, zi
            
        elif method == 'kriging':
            # 克里金插值
            ok = OrdinaryKriging(x, y, z, variogram_model='linear')
            xi = np.linspace(min(x), max(x), resolution)
            yi = np.linspace(min(y), max(y), resolution)
            zi, ss = ok.execute('grid', xi, yi)
            return xi, yi, zi
            
    @staticmethod
    def calculate_gradient(x, y, z):
        """计算梯度"""
        dz_dx = np.gradient(z, axis=1)
        dz_dy = np.gradient(z, axis=0)
        return dz_dx, dz_dy
        
    @staticmethod
    def find_extrema(z):
        """寻找极值点"""
        max_val = np.max(z)
        min_val = np.min(z)
        max_pos = np.where(z == max_val)
        min_pos = np.where(z == min_val)
        return max_val, min_val, max_pos, min_pos
        
    @staticmethod
    def calculate_statistics(z):
        """计算统计量"""
        stats = {
            "mean": np.mean(z),
            "std": np.std(z),
            "min": np.min(z),
            "max": np.max(z),
            "median": np.median(z)
        }
        return stats


class RealTimeDataThread(QThread):
    """实时数据线程"""
    
    dataReceived = pyqtSignal(dict)
    
    def __init__(self, data_source, interval=1000):
        super().__init__()
        self.data_source = data_source
        self.interval = interval
        self.is_running = False
        
    def run(self):
        """线程运行"""
        self.is_running = True
        while self.is_running:
            # 获取数据
            data = self.fetch_data()
            self.dataReceived.emit(data)
            time.sleep(self.interval / 1000.0)
            
    def fetch_data(self):
        """获取数据"""
        # 这里可以实现实际的数据获取逻辑
        # 模拟数据
        return {
            "timestamp": datetime.now(),
            "value": np.random.random(),
            "quality": "good"
        }
        
    def stop(self):
        """停止线程"""
        self.is_running = False


class MarineToolbar(QToolBar):
    """增强版海域系统工具栏"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setIconSize(QSize(32, 32))
        self.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        
        # 创建动作
        self.zoom_in_action = QAction(QIcon("icons/zoom_in.png"), "放大", self)
        self.zoom_out_action = QAction(QIcon("icons/zoom_out.png"), "缩小", self)
        self.pan_action = QAction(QIcon("icons/pan.png"), "平移", self)
        self.measure_action = QAction(QIcon("icons/measure.png"), "测量", self)
        self.measure_area_action = QAction(QIcon("icons/measure_area.png"), "面积测量", self)
        self.route_action = QAction(QIcon("icons/route.png"), "航线规划", self)
        self.data_action = QAction(QIcon("icons/data.png"), "加载数据", self)
        self.export_action = QAction(QIcon("icons/export.png"), "导出", self)
        self.analysis_action = QAction(QIcon("icons/analysis.png"), "分析", self)
        self.realtime_action = QAction(QIcon("icons/realtime.png"), "实时数据", self)
        self.basemap_action = QAction(QIcon("icons/basemap.png"), "底图", self)
        self.view_3d_action = QAction(QIcon("icons/3d.png"), "3D视图", self)
        
        # 添加动作到工具栏
        self.addAction(self.zoom_in_action)
        self.addAction(self.zoom_out_action)
        self.addAction(self.pan_action)
        self.addSeparator()
        self.addAction(self.measure_action)
        self.addAction(self.measure_area_action)
        self.addAction(self.route_action)
        self.addSeparator()
        self.addAction(self.data_action)
        self.addAction(self.export_action)
        self.addAction(self.analysis_action)
        self.addSeparator()
        self.addAction(self.realtime_action)
        self.addAction(self.basemap_action)
        self.addAction(self.view_3d_action)


class MarineDockWidget(QDockWidget):
    """增强版海域系统停靠窗口"""
    
    def __init__(self, title, parent=None):
        super().__init__(title, parent)
        self.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)
        
        self.content_widget = QWidget()
        self.setWidget(self.content_widget)
        
    def set_content_layout(self, layout):
        """设置内容布局"""
        self.content_widget.setLayout(layout)


class DataImportDialog(QDialog):
    """数据导入对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("导入数据")
        self.setModal(True)
        
        layout = QFormLayout(self)
        
        self.source_type = QComboBox()
        self.source_type.addItems(["本地文件", "在线数据", "实时传感器"])
        layout.addRow("数据源类型:", self.source_type)
        
        self.source_input = QLineEdit()
        self.browse_button = QPushButton("浏览...")
        self.browse_button.clicked.connect(self.browse_file)
        source_layout = QHBoxLayout()
        source_layout.addWidget(self.source_input)
        source_layout.addWidget(self.browse_button)
        layout.addRow("数据源:", source_layout)
        
        self.dataset_name = QLineEdit()
        layout.addRow("数据集名称:", self.dataset_name)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)
        
    def browse_file(self):
        """浏览文件"""
        filename, _ = QFileDialog.getOpenFileName(
            self, "选择数据文件", "", 
            "所有支持格式 (*.csv *.shp *.nc *.netcdf);;CSV文件 (*.csv);;Shapefile (*.shp);;NetCDF (*.nc *.netcdf)"
        )
        if filename:
            self.source_input.setText(filename)
            
    def get_values(self):
        """获取对话框值"""
        return {
            "source_type": self.source_type.currentText(),
            "source": self.source_input.text(),
            "name": self.dataset_name.text() or None
        }


class MarineSystem(QMainWindow):
    """增强版海域系统主窗口"""
    
    def __init__(self):
        super().__init__()
        
        # 初始化UI
        self.init_ui()
        
        # 初始化工具
        self.measurement_tool = MeasurementTool(self.map_canvas)
        self.route_planner = RoutePlanner(self.map_canvas)
        self.data_manager = MarineDataManager()
        self.analysis_tools = AnalysisTools()
        
        # 实时数据
        self.realtime_thread = None
        
        # 连接信号和槽
        self.connect_signals()
        
        # 状态栏信息
        self.status_bar.showMessage("就绪")
        
    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("海域系统高级工具库")
        self.setGeometry(100, 100, 1400, 900)
        
        # 创建中心部件 - 地图画布
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # 创建标签页
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # 2D地图标签页
        self.map_tab = QWidget()
        self.map_layout = QVBoxLayout(self.map_tab)
        self.map_canvas = MarineMapCanvas(self.map_tab, width=10, height=8, dpi=100)
        self.map_layout.addWidget(self.map_canvas)
        self.tab_widget.addTab(self.map_tab, "2D地图")
        
        # 3D地图标签页
        self.map_3d_tab = QWidget()
        self.map_3d_layout = QVBoxLayout(self.map_3d_tab)
        self.map_3d_canvas = ThreeDMapCanvas(self.map_3d_tab, width=10, height=8, dpi=100)
        self.map_3d_layout.addWidget(self.map_3d_canvas)
        self.tab_widget.addTab(self.map_3d_tab, "3D视图")
        
        # 创建工具栏
        self.toolbar = MarineToolbar()
        self.addToolBar(Qt.TopToolBarArea, self.toolbar)
        
        # 创建状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # 创建左侧停靠窗口 - 图层管理
        self.layer_dock = MarineDockWidget("图层管理", self)
        layer_layout = QVBoxLayout()
        
        self.layer_tree = QTreeWidget()
        self.layer_tree.setHeaderLabels(["图层", "可见", "类型"])
        self.layer_tree.header().setSectionResizeMode(0, QHeaderView.Stretch)
        layer_layout.addWidget(self.layer_tree)
        
        layer_buttons_layout = QHBoxLayout()
        self.add_layer_button = QPushButton("添加图层")
        self.remove_layer_button = QPushButton("移除图层")
        self.layer_properties_button = QPushButton("属性")
        layer_buttons_layout.addWidget(self.add_layer_button)
        layer_buttons_layout.addWidget(self.remove_layer_button)
        layer_buttons_layout.addWidget(self.layer_properties_button)
        layer_layout.addLayout(layer_buttons_layout)
        
        self.layer_dock.set_content_layout(layer_layout)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.layer_dock)
        
        # 创建右侧停靠窗口 - 工具选项
        self.tools_dock = MarineDockWidget("工具选项", self)
        tools_layout = QVBoxLayout()
        
        # 创建工具选项标签页
        self.tools_tabs = QTabWidget()
        tools_layout.addWidget(self.tools_tabs)
        
        # 测量工具标签页
        measure_tab = QWidget()
        measure_layout = QVBoxLayout(measure_tab)
        measure_layout.addWidget(QLabel("测量工具:"))
        self.measure_result_label = QLabel("距离: 0.0 km")
        measure_layout.addWidget(self.measure_result_label)
        self.area_result_label = QLabel("面积: 0.0 km²")
        measure_layout.addWidget(self.area_result_label)
        self.reset_measure_button = QPushButton("重置测量")
        measure_layout.addWidget(self.reset_measure_button)
        measure_layout.addStretch()
        self.tools_tabs.addTab(measure_tab, "测量")
        
        # 航线规划标签页
        route_tab = QWidget()
        route_layout = QVBoxLayout(route_tab)
        route_layout.addWidget(QLabel("航线规划:"))
        self.route_length_label = QLabel("航线长度: 0.0 km")
        route_layout.addWidget(self.route_length_label)
        
        self.waypoints_table = QTableWidget()
        self.waypoints_table.setColumnCount(3)
        self.waypoints_table.setHorizontalHeaderLabels(["名称", "经度", "纬度"])
        route_layout.addWidget(self.waypoints_table)
        
        route_buttons_layout = QHBoxLayout()
        self.add_waypoint_button = QPushButton("添加航点")
        self.remove_waypoint_button = QPushButton("移除航点")
        self.clear_route_button = QPushButton("清除航线")
        route_buttons_layout.addWidget(self.add_waypoint_button)
        route_buttons_layout.addWidget(self.remove_waypoint_button)
        route_buttons_layout.addWidget(self.clear_route_button)
        route_layout.addLayout(route_buttons_layout)
        
        self.export_route_button = QPushButton("导出航线")
        route_layout.addWidget(self.export_route_button)
        route_layout.addStretch()
        self.tools_tabs.addTab(route_tab, "航线")
        
        # 分析工具标签页
        analysis_tab = QWidget()
        analysis_layout = QVBoxLayout(analysis_tab)
        analysis_layout.addWidget(QLabel("分析工具:"))
        
        self.analysis_type = QComboBox()
        self.analysis_type.addItems(["插值分析", "梯度分析", "统计分析"])
        analysis_layout.addWidget(self.analysis_type)
        
        self.run_analysis_button = QPushButton("运行分析")
        analysis_layout.addWidget(self.run_analysis_button)
        
        self.analysis_result = QTextEdit()
        self.analysis_result.setReadOnly(True)
        analysis_layout.addWidget(self.analysis_result)
        self.tools_tabs.addTab(analysis_tab, "分析")
        
        # 实时数据标签页
        realtime_tab = QWidget()
        realtime_layout = QVBoxLayout(realtime_tab)
        realtime_layout.addWidget(QLabel("实时数据:"))
        
        self.realtime_source = QComboBox()
        self.realtime_source.addItems(["传感器1", "传感器2", "传感器3"])
        realtime_layout.addWidget(self.realtime_source)
        
        self.realtime_interval = QSpinBox()
        self.realtime_interval.setRange(100, 10000)
        self.realtime_interval.setValue(1000)
        self.realtime_interval.setSuffix(" ms")
        realtime_layout.addWidget(QLabel("更新间隔:"))
        realtime_layout.addWidget(self.realtime_interval)
        
        self.start_realtime_button = QPushButton("开始")
        self.stop_realtime_button = QPushButton("停止")
        realtime_buttons_layout = QHBoxLayout()
        realtime_buttons_layout.addWidget(self.start_realtime_button)
        realtime_buttons_layout.addWidget(self.stop_realtime_button)
        realtime_layout.addLayout(realtime_buttons_layout)
        
        self.realtime_data_display = QTextEdit()
        self.realtime_data_display.setReadOnly(True)
        realtime_layout.addWidget(self.realtime_data_display)
        self.tools_tabs.addTab(realtime_tab, "实时数据")
        
        self.tools_dock.set_content_layout(tools_layout)
        self.addDockWidget(Qt.RightDockWidgetArea, self.tools_dock)
        
    def connect_signals(self):
        """连接信号和槽"""
        # 连接地图点击事件
        self.map_canvas.mapClicked.connect(self.on_map_click)
        
        # 连接工具栏动作
        self.toolbar.measure_action.triggered.connect(self.activate_measurement_tool)
        self.toolbar.measure_area_action.triggered.connect(self.activate_area_measurement_tool)
        self.toolbar.route_action.triggered.connect(self.activate_route_planning_tool)
        self.toolbar.data_action.triggered.connect(self.show_data_import_dialog)
        self.toolbar.export_action.triggered.connect(self.export_data)
        self.toolbar.analysis_action.triggered.connect(self.show_analysis_tools)
        self.toolbar.realtime_action.triggered.connect(self.show_realtime_tools)
        self.toolbar.basemap_action.triggered.connect(self.show_basemap_menu)
        self.toolbar.view_3d_action.triggered.connect(self.switch_to_3d_view)
        
        # 连接按钮信号
        self.reset_measure_button.clicked.connect(self.reset_measurement)
        self.add_waypoint_button.clicked.connect(self.add_waypoint_dialog)
        self.remove_waypoint_button.clicked.connect(self.remove_waypoint)
        self.clear_route_button.clicked.connect(self.clear_route)
        self.export_route_button.clicked.connect(self.export_route_dialog)
        self.run_analysis_button.clicked.connect(self.run_analysis)
        self.start_realtime_button.clicked.connect(self.start_realtime_data)
        self.stop_realtime_button.clicked.connect(self.stop_realtime_data)
        self.add_layer_button.clicked.connect(self.show_data_import_dialog)
        self.remove_layer_button.clicked.connect(self.remove_selected_layer)
        
    def on_map_click(self, lon, lat):
        """处理地图点击事件"""
        # 更新状态栏显示坐标
        self.status_bar.showMessage(f"经度: {lon:.6f}, 纬度: {lat:.6f}")
        
        if self.toolbar.measure_action.isChecked():
            # 模拟事件对象
            class MockEvent:
                def __init__(self, xdata, ydata):
                    self.xdata = xdata
                    self.ydata = ydata
                    self.inaxes = self.map_canvas.ax
                    self.button = 1
                    
            event = MockEvent(lon, lat)
            self.measurement_tool.start_measurement(event, area_mode=False)
            self.measure_result_label.setText(f"距离: {self.measurement_tool.distance:.2f} km")
            
        elif self.toolbar.measure_area_action.isChecked():
            # 模拟事件对象
            class MockEvent:
                def __init__(self, xdata, ydata):
                    self.xdata = xdata
                    self.ydata = ydata
                    self.inaxes = self.map_canvas.ax
                    self.button = 1
                    
            event = MockEvent(lon, lat)
            self.measurement_tool.start_measurement(event, area_mode=True)
            self.area_result_label.setText(f"面积: {self.measurement_tool.area:.2f} km²")
            
        elif self.toolbar.route_action.isChecked():
            self.route_planner.add_waypoint(lon, lat)
            self.update_waypoints_table()
            self.route_length_label.setText(f"航线长度: {self.route_planner.calculate_route_length():.2f} km")
            
    def activate_measurement_tool(self):
        """激活测量工具"""
        self.toolbar.measure_action.setChecked(True)
        self.toolbar.measure_area_action.setChecked(False)
        self.toolbar.route_action.setChecked(False)
        self.measurement_tool.reset()
        self.tools_tabs.setCurrentIndex(0)  # 切换到测量标签页
        
    def activate_area_measurement_tool(self):
        """激活面积测量工具"""
        self.toolbar.measure_area_action.setChecked(True)
        self.toolbar.measure_action.setChecked(False)
        self.toolbar.route_action.setChecked(False)
        self.measurement_tool.reset()
        self.tools_tabs.setCurrentIndex(0)  # 切换到测量标签页
        
    def activate_route_planning_tool(self):
        """激活航线规划工具"""
        self.toolbar.route_action.setChecked(True)
        self.toolbar.measure_action.setChecked(False)
        self.toolbar.measure_area_action.setChecked(False)
        self.tools_tabs.setCurrentIndex(1)  # 切换到航线标签页
        
    def reset_measurement(self):
        """重置测量"""
        self.measurement_tool.reset()
        self.measure_result_label.setText("距离: 0.0 km")
        self.area_result_label.setText("面积: 0.0 km²")
        
    def add_waypoint_dialog(self):
        """添加航点对话框"""
        dialog = QDialog(self)
        dialog.setWindowTitle("添加航点")
        layout = QFormLayout(dialog)
        
        name_edit = QLineEdit()
        layout.addRow("名称:", name_edit)
        
        lon_edit = QDoubleSpinBox()
        lon_edit.setRange(-180, 180)
        lon_edit.setDecimals(6)
        layout.addRow("经度:", lon_edit)
        
        lat_edit = QDoubleSpinBox()
        lat_edit.setRange(-90, 90)
        lat_edit.setDecimals(6)
        layout.addRow("纬度:", lat_edit)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)
        
        if dialog.exec_() == QDialog.Accepted:
            name = name_edit.text() or f"WP{len(self.route_planner.waypoints)+1}"
            self.route_planner.add_waypoint(lon_edit.value(), lat_edit.value(), name)
            self.update_waypoints_table()
            self.route_length_label.setText(f"航线长度: {self.route_planner.calculate_route_length():.2f} km")
            
    def remove_waypoint(self):
        """移除选中的航点"""
        current_row = self.waypoints_table.currentRow()
        if current_row >= 0:
            self.route_planner.remove_waypoint(current_row)
            self.update_waypoints_table()
            self.route_length_label.setText(f"航线长度: {self.route_planner.calculate_route_length():.2f} km")
            
    def clear_route(self):
        """清除航线"""
        self.route_planner.clear_route()
        self.waypoints_table.setRowCount(0)
        self.route_length_label.setText("航线长度: 0.0 km")
        
    def update_waypoints_table(self):
        """更新航点表格"""
        self.waypoints_table.setRowCount(len(self.route_planner.waypoints))
        for i, waypoint in enumerate(self.route_planner.waypoints):
            self.waypoints_table.setItem(i, 0, QTableWidgetItem(waypoint["name"]))
            self.waypoints_table.setItem(i, 1, QTableWidgetItem(f"{waypoint['lon']:.6f}"))
            self.waypoints_table.setItem(i, 2, QTableWidgetItem(f"{waypoint['lat']:.6f}"))
            
    def export_route_dialog(self):
        """导出航线对话框"""
        if not self.route_planner.waypoints:
            QMessageBox.warning(self, "警告", "没有可导出的航线")
            return
            
        formats = {
            "JSON": "json",
            "KML": "kml",
            "GPX": "gpx"
        }
        
        format_name, ok = QInputDialog.getItem(
            self, "导出格式", "选择导出格式:", list(formats.keys()), 0, False
        )
        
        if ok:
            filename, _ = QFileDialog.getSaveFileName(
                self, "导出航线", "", f"{format_name} Files (*.{formats[format_name]})"
            )
            
            if filename:
                try:
                    self.route_planner.export_route(filename, formats[format_name])
                    self.status_bar.showMessage(f"航线已导出到: {filename}")
                except Exception as e:
                    QMessageBox.critical(self, "错误", f"导出航线时出错: {str(e)}")
                    
    def show_data_import_dialog(self):
        """显示数据导入对话框"""
        dialog = DataImportDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            values = dialog.get_values()
            try:
                data = self.data_manager.load_data(values["source_type"], values["source"], values["name"])
                
                # 添加到图层树
                item = QTreeWidgetItem(self.layer_tree)
                item.setText(0, values["name"] or f"dataset_{len(self.data_manager.datasets)}")
                item.setText(2, type(data).__name__)
                
                # 添加复选框
                checkbox = QCheckBox()
                checkbox.setChecked(True)
                self.layer_tree.setItemWidget(item, 1, checkbox)
                
                # 如果是GeoDataFrame，绘制数据
                if isinstance(data, gpd.GeoDataFrame):
                    for geom in data.geometry:
                        if geom.geom_type == 'Point':
                            self.map_canvas.plot_points([geom.x], [geom.y], color='red', marker='o')
                        elif geom.geom_type == 'LineString':
                            lons, lats = geom.xy
                            self.map_canvas.plot_line(lons, lats, color='blue')
                        elif geom.geom_type == 'Polygon':
                            lons, lats = geom.exterior.xy
                            self.map_canvas.plot_polygon(lons, lats, color='green', alpha=0.5)
                
                self.status_bar.showMessage(f"成功加载数据: {values['source']}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"加载数据时出错: {str(e)}")
                
    def remove_selected_layer(self):
        """移除选中的图层"""
        current_item = self.layer_tree.currentItem()
        if current_item:
            dataset_name = current_item.text(0)
            try:
                self.data_manager.remove_data(dataset_name)
                self.layer_tree.takeTopLevelItem(self.layer_tree.indexOfTopLevelItem(current_item))
                self.status_bar.showMessage(f"已移除图层: {dataset_name}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"移除图层时出错: {str(e)}")
                
    def export_data(self):
        """导出数据"""
        # 这里可以实现多种数据导出功能
        pass
        
    def show_analysis_tools(self):
        """显示分析工具"""
        self.tools_tabs.setCurrentIndex(2)  # 切换到分析标签页
        
    def run_analysis(self):
        """运行分析"""
        analysis_type = self.analysis_type.currentText()
        
        if analysis_type == "统计分析":
            # 获取当前数据集
            try:
                data = self.data_manager.get_data()
                
                # 如果是DataFrame，进行统计分析
                if isinstance(data, pd.DataFrame):
                    # 选择数值列
                    numeric_cols = data.select_dtypes(include=[np.number]).columns.tolist()
                    if numeric_cols:
                        # 计算基本统计量
                        stats = data[numeric_cols].describe()
                        self.analysis_result.setText(stats.to_string())
                    else:
                        self.analysis_result.setText("没有数值列可分析")
                else:
                    self.analysis_result.setText("当前数据集不支持统计分析")
                    
            except Exception as e:
                self.analysis_result.setText(f"分析错误: {str(e)}")
                
    def show_realtime_tools(self):
        """显示实时数据工具"""
        self.tools_tabs.setCurrentIndex(3)  # 切换到实时数据标签页
        
    def start_realtime_data(self):
        """开始实时数据"""
        if self.realtime_thread is None:
            source = self.realtime_source.currentText()
            interval = self.realtime_interval.value()
            
            self.realtime_thread = RealTimeDataThread(source, interval)
            self.realtime_thread.dataReceived.connect(self.update_realtime_data)
            self.realtime_thread.start()
            
            self.status_bar.showMessage(f"开始接收实时数据: {source}")
            
    def stop_realtime_data(self):
        """停止实时数据"""
        if self.realtime_thread:
            self.realtime_thread.stop()
            self.realtime_thread.wait()
            self.realtime_thread = None
            self.status_bar.showMessage("已停止实时数据")
            
    def update_realtime_data(self, data):
        """更新实时数据显示"""
        timestamp = data["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
        text = f"[{timestamp}] {data['value']:.4f} ({data['quality']})\n"
        self.realtime_data_display.append(text)
        
        # 自动滚动到底部
        scrollbar = self.realtime_data_display.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        
    def show_basemap_menu(self):
        """显示底图菜单"""
        menu = QMenu(self)
        
        default_action = menu.addAction("默认底图")
        satellite_action = menu.addAction("卫星影像")
        terrain_action = menu.addAction("地形图")
        
        action = menu.exec_(self.toolbar.basemap_action.parentWidget().mapToGlobal(
            self.toolbar.basemap_action.parentWidget().rect().bottomLeft()
        ))
        
        if action == default_action:
            self.map_canvas.set_basemap("default")
        elif action == satellite_action:
            self.map_canvas.set_basemap("satellite")
        elif action == terrain_action:
            self.map_canvas.set_basemap("terrain")
            
    def switch_to_3d_view(self):
        """切换到3D视图"""
        self.tab_widget.setCurrentIndex(1)  # 切换到3D标签页
        
        # 如果有海底地形数据，在3D视图中显示
        # 这里需要根据实际数据实现


def main():
    """主函数"""
    app = QApplication(sys.argv)
    
    # 设置应用程序样式
    app.setStyle(QStyleFactory.create('Fusion'))
    
    # 创建主窗口
    marine_system = MarineSystem()
    marine_system.show()
    
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()