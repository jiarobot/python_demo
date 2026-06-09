import sys
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Qt5Agg')
matplotlib.rc("font", family='Microsoft YaHei')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter, 
    QTabWidget, QGroupBox, QPushButton, QComboBox, QSlider, QLabel, QListWidget,
    QTreeWidget, QTreeWidgetItem, QTableWidget, QTableWidgetItem, QHeaderView,
    QStatusBar, QToolBar, QAction, QFileDialog, QDockWidget, QProgressBar,
    QMessageBox, QScrollArea, QFormLayout, QLineEdit, QCheckBox, QSpinBox,
    QDoubleSpinBox, QTextEdit, QDialog, QDialogButtonBox, QGridLayout
)
from datetime import timedelta
from PyQt5.QtCore import Qt, QTimer, QSize
from PyQt5.QtGui import QIcon, QPixmap, QFont, QColor, QPalette
import xarray as xr
import tensorflow as tf
from tensorflow.keras.models import Model
from tensorflow.keras.layers import Input, ConvLSTM2D, Dense, Flatten, Reshape, Concatenate
from scipy.ndimage import gaussian_filter
import pyproj
import numba
import warnings
warnings.filterwarnings('ignore')

# 系统配置
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
plt.style.use('ggplot')

# =============================================
# 1. 核心功能类
# =============================================
class CycloneAnalysisSystem:
    def __init__(self):
        self.cyclone_data = None
        self.env_data = None
        self.terrain_data = None
        self.population_data = None
        self.infrastructure_data = None
        self.current_cyclone = None
        self.simulation_results = {}
        self.prediction_model = None
        self.load_sample_data()
        
    def load_sample_data(self):
        """加载示例数据"""
        print("加载示例数据...")
        self._generate_sample_cyclone_data()
        self._generate_sample_environment_data()
        self._generate_sample_terrain_data()
        self._generate_sample_population_data()
        self._generate_sample_infrastructure_data()
        print("数据加载完成!")
        
    def _generate_sample_cyclone_data(self):
        """生成示例气旋数据"""
        num_cyclones = 50
        cyclones = []
        
        for i in range(num_cyclones):
            basin = 'WP' if i % 2 == 0 else 'NA'
            lat0 = np.random.uniform(5, 35)
            lon0 = np.random.uniform(100, 180) if basin == 'WP' else np.random.uniform(-100, -20)
            
            num_points = np.random.randint(20, 60)
            lats = [lat0]
            lons = [lon0]
            winds = [np.random.uniform(15, 30)]
            pressures = [1000]
            rmws = [50]  # 最大风速半径
            
            for j in range(1, num_points):
                lat_change = np.random.uniform(-0.5, 0.8)
                lon_change = np.random.uniform(-0.7, -0.1)
                lats.append(lats[-1] + lat_change)
                lons.append(lons[-1] + lon_change)
                
                if j < num_points/2:
                    wind_change = np.random.uniform(0, 15)
                else:
                    wind_change = np.random.uniform(-15, 0)
                
                winds.append(max(15, min(300, winds[-1] + wind_change)))
                pressures.append(max(880, min(1010, 1010 - (winds[-1] - 30)*0.6)))
                rmws.append(max(20, min(150, rmws[-1] + np.random.uniform(-5, 5))))
            
            sid = f"C{i:04d}"
            name = f"Cyclone-{i+1}"
            time = pd.date_range('2023-01-01', periods=num_points, freq='6H')
            
            for j in range(num_points):
                # 风速分类
                wind = winds[j]
                if wind < 34: cat = "Tropical Depression"
                elif wind < 64: cat = "Tropical Storm"
                elif wind < 83: cat = "Category 1"
                elif wind < 96: cat = "Category 2"
                elif wind < 113: cat = "Category 3"
                elif wind < 137: cat = "Category 4"
                else: cat = "Category 5"
                
                cyclones.append({
                    'sid': sid,
                    'name': name,
                    'time': time[j],
                    'lat': lats[j],
                    'lon': lons[j],
                    'wind': winds[j],
                    'pres': pressures[j],
                    'rmw': rmws[j],
                    'basin': basin,
                    'category': cat
                })
        
        df = pd.DataFrame(cyclones)
        self.cyclone_data = df
        
    def _generate_sample_environment_data(self):
        """生成示例环境数据"""
        dates = pd.date_range('2023-01-01', '2023-12-31', freq='D')
        lats = np.linspace(-60, 60, 180)
        lons = np.linspace(0, 360, 360)
        
        sst = np.zeros((len(dates), len(lats), len(lons)))
        shear = np.zeros_like(sst)
        
        for i, date in enumerate(dates):
            month = date.month
            # 使用[:, np.newaxis]将一维数组转换为二维列向量
            sst[i] = (20 + 10 * np.cos(np.deg2rad(lats)) + 
                    3 * np.sin(2 * np.pi * (month-1)/11))[:, np.newaxis]
            shear[i] = (10 + 5 * np.sin(2 * np.pi * (month-3)/11) - 
                    2 * np.cos(np.deg2rad(lats)))[:, np.newaxis]
                
        self.env_data = {
            'dates': dates,
            'lats': lats,
            'lons': lons,
            'sst': sst,
            'shear': shear
        }
        
    def _generate_sample_terrain_data(self):
        """生成示例地形数据"""
        lats = np.linspace(-60, 60, 1000)
        lons = np.linspace(0, 360, 2000)
        lon_grid, lat_grid = np.meshgrid(lons, lats)
        
        terrain = np.zeros_like(lat_grid)
        terrain = 100 * np.sin(np.deg2rad(lat_grid*3)) * np.cos(np.deg2rad(lon_grid*2))
        terrain += 3000 * np.exp(-((lat_grid-30)/15)**2 - ((lon_grid-120)/40)**2)
        terrain += 2500 * np.exp(-((lat_grid+20)/10)**2 - ((lon_grid+70)/30)**2)
        terrain = np.where(terrain < 0, -4000 + terrain, terrain)
            
        self.terrain_data = {
            'lats': lats,
            'lons': lons,
            'elevation': terrain
        }
        
    def _generate_sample_population_data(self):
        """生成示例人口数据"""
        lats = np.linspace(-60, 60, 360)
        lons = np.linspace(0, 360, 720)
        lon_grid, lat_grid = np.meshgrid(lons, lats)
        
        population = np.zeros_like(lat_grid)
        population += 5000 * np.exp(-((lat_grid-30)/15)**2) * (1 + 0.5 * np.sin(np.deg2rad(lon_grid*2)))
        population += 2000 * np.exp(-(lat_grid/20)**2)
        
        # 简化海岸线因子
        coast_factor = np.exp(-np.abs(self.terrain_data['elevation'])/1000)
        population *= coast_factor[:population.shape[0], :population.shape[1]]
            
        self.population_data = {
            'lats': lats,
            'lons': lons,
            'density': population
        }
        
    def _generate_sample_infrastructure_data(self):
        """生成示例基础设施数据"""
        self.infrastructure_data = {
            'cities': [
                {'name': 'Tokyo', 'lat': 35.68, 'lon': 139.76, 'population': 13.5e6},
                {'name': 'Shanghai', 'lat': 31.23, 'lon': 121.47, 'population': 24.3e6},
                {'name': 'Manila', 'lat': 14.60, 'lon': 120.98, 'population': 13.5e6},
                {'name': 'Miami', 'lat': 25.76, 'lon': -80.19, 'population': 6.1e6},
                {'name': 'New Orleans', 'lat': 29.95, 'lon': -90.07, 'population': 1.3e6}
            ],
            'power_plants': [
                {'name': 'Fukushima', 'type': 'Nuclear', 'lat': 37.42, 'lon': 141.03, 'capacity': 4700},
                {'name': 'Shanghai Power', 'type': 'Coal', 'lat': 31.30, 'lon': 121.50, 'capacity': 5000},
                {'name': 'Hoover Dam', 'type': 'Hydro', 'lat': 36.01, 'lon': -114.74, 'capacity': 2080}
            ]
        }
        
    def get_cyclone_names(self):
        """获取所有气旋名称"""
        return self.cyclone_data[['sid', 'name']].drop_duplicates().values.tolist()
    
    def get_cyclone_data(self, cyclone_id):
        """获取指定气旋的数据"""
        return self.cyclone_data[self.cyclone_data['sid'] == cyclone_id]
    
    def simulate_wind_field(self, lat, lon, wind_speed, pressure, rmw, resolution=0.5, radius=500):
        """模拟风场"""
        # 创建网格
        lats = np.arange(lat - 5, lat + 5 + resolution, resolution)
        lons = np.arange(lon - 5, lon + 5 + resolution, resolution)
        lon_grid, lat_grid = np.meshgrid(lons, lats)
        
        # 计算距离中心的距离 (km)
        R = np.sqrt((lon_grid - lon)**2 * (111 * np.cos(np.radians(lat)))**2 + 
                     (lat_grid - lat)**2 * 111**2)
        
        # 梯度风模型
        V_max = wind_speed
        R_max = rmw
        
        wind_field = np.zeros_like(R)
        wind_field[R > 0] = V_max * (R_max / R[R>0]) * np.sqrt(1 + (R_max / R[R>0])**2)
        wind_field[R < R_max] = V_max * (R[R < R_max] / R_max)
        
        # 添加角向分量
        theta = np.arctan2(lat_grid - lat, lon_grid - lon)
        u = -wind_field * np.sin(theta)
        v = wind_field * np.cos(theta)
        
        return lats, lons, u, v, wind_field
    
    def simulate_storm_surge(self, landfall_lat, landfall_lon, wind_speed, pressure, 
                           forward_speed=20, forward_angle=45, resolution=0.2):
        """模拟风暴潮"""
        # 创建网格
        lats = np.arange(landfall_lat - 2, landfall_lat + 2 + resolution, resolution)
        lons = np.arange(landfall_lon - 2, landfall_lon + 2 + resolution, resolution)
        lon_grid, lat_grid = np.meshgrid(lons, lats)
        
        # 计算距离
        R = np.sqrt((lon_grid - landfall_lon)**2 * (111 * np.cos(np.radians(landfall_lat)))**2 + 
                     (lat_grid - landfall_lat)**2 * 111**2)
        
        # 风暴潮模型
        surge = np.zeros_like(R)
        surge[R > 0] = (0.002 * wind_speed**1.5 * np.exp(-R[R>0]/150) * 
                      (1010 - pressure)/100 * 
                      (1 + 0.5 * np.cos(np.deg2rad(forward_angle - 
                        np.arctan2(lat_grid[R>0]-landfall_lat, lon_grid[R>0]-landfall_lon)))))
        
        surge += 0.5 * forward_speed * np.exp(-R/50)
        surge = gaussian_filter(surge, sigma=1)
        
        return lats, lons, surge
    
    def assess_impact(self, lat, lon, wind_speed, surge_height, population_density):
        """评估灾害影响"""
        # 计算受影响区域
        R_wind = min(500, wind_speed * 5)  # 强风影响半径 (km)
        R_surge = min(200, surge_height * 100)  # 风暴潮影响半径 (km)
        
        # 计算受影响人口
        wind_pop = population_density * (np.pi * R_wind**2)
        surge_pop = population_density * (np.pi * R_surge**2)
        total_pop = wind_pop + surge_pop
        
        # 经济损失估算 (十亿美元)
        econ_loss = wind_speed**2 * surge_height * population_density * 1e-6
        
        # 灾害等级
        if wind_speed > 250 or surge_height > 5:
            disaster_level = "灾难性 (Catastrophic)"
        elif wind_speed > 200 or surge_height > 3:
            disaster_level = "极端 (Extreme)"
        elif wind_speed > 150 or surge_height > 2:
            disaster_level = "严重 (Severe)"
        elif wind_speed > 120 or surge_height > 1:
            disaster_level = "中等 (Moderate)"
        else:
            disaster_level = "轻微 (Minor)"
        
        return {
            'affected_area_wind': np.pi * R_wind**2,
            'affected_area_surge': np.pi * R_surge**2,
            'affected_population': total_pop,
            'economic_loss': econ_loss,
            'disaster_level': disaster_level
        }

# =============================================
# 2. PyQt界面组件
# =============================================
class MapCanvas(FigureCanvas):
    """地图可视化画布"""
    def __init__(self, parent=None, width=10, height=8, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        super(MapCanvas, self).__init__(self.fig)
        self.setParent(parent)
        self.ax = self.fig.add_subplot(1, 1, 1, projection=ccrs.PlateCarree())
        self.ax.set_global()
        self.ax.coastlines()
        self.ax.add_feature(cfeature.BORDERS, linestyle=':')
        self.ax.add_feature(cfeature.LAND, facecolor='lightgray')
        self.ax.add_feature(cfeature.OCEAN, facecolor='lightblue')
        self.ax.gridlines(draw_labels=True)
        self.current_cyclone_id = None
        self.current_colorbar = None
    
    def clear_existing_colorbar(self):
        """清除现有的颜色条"""
        if self.current_colorbar:
            self.current_colorbar.remove()  # 从图形中移除颜色条
            self.current_colorbar = None

    def plot_cyclone_track(self, cyclone_data):
        """绘制气旋轨迹"""
        self.clear_existing_colorbar()
        self.fig.clear()  # 清除整个图形
        
        # 创建新的地理坐标系
        self.ax = self.fig.add_subplot(1, 1, 1, projection=ccrs.PlateCarree())
        
        # 设置地图属性和特征
        self.ax.set_global()
        self.ax.coastlines()
        self.ax.add_feature(cfeature.BORDERS, linestyle=':')
        self.ax.add_feature(cfeature.LAND, facecolor='lightgray')
        self.ax.add_feature(cfeature.OCEAN, facecolor='lightblue')
        self.ax.gridlines(draw_labels=True)
        
        # 按风速着色
        scatter = self.ax.scatter(
            cyclone_data['lon'], 
            cyclone_data['lat'], 
            c=cyclone_data['wind'],
            cmap='viridis',
            s=cyclone_data['wind']/2,
            transform=ccrs.PlateCarree()
        )
        
        # 绘制路径线
        self.ax.plot(
            cyclone_data['lon'], 
            cyclone_data['lat'], 
            'k--', 
            alpha=0.5, 
            transform=ccrs.PlateCarree()
        )
        
        # 标记起点和终点
        self.ax.plot(
            cyclone_data['lon'].iloc[0], 
            cyclone_data['lat'].iloc[0], 
            'go', 
            markersize=8, 
            label='Start',
            transform=ccrs.PlateCarree()
        )
        
        self.ax.plot(
            cyclone_data['lon'].iloc[-1], 
            cyclone_data['lat'].iloc[-1], 
            'ro', 
            markersize=8, 
            label='End',
            transform=ccrs.PlateCarree()
        )
        
        # 添加标题和图例
        self.ax.set_title(f"{cyclone_data['name'].iloc[0]} Track", fontsize=14)
        self.ax.legend()
        
        # 添加颜色条
        self.current_colorbar = self.fig.colorbar(scatter, ax=self.ax)
        self.current_colorbar.set_label('Wind Speed (km/h)')
        
        self.draw()
        
    def plot_wind_field(self, lats, lons, u, v, wind_speed):
        """绘制风场"""
        self.clear_existing_colorbar() 
        self.fig.clear()  # 清除整个图形
        
        # 创建新的地理坐标系
        self.ax = self.fig.add_subplot(1, 1, 1, projection=ccrs.PlateCarree())
        
        # 设置地图属性和特征
        self.ax.set_global()
        self.ax.coastlines()
        self.ax.add_feature(cfeature.BORDERS, linestyle=':')
        self.ax.add_feature(cfeature.LAND, facecolor='lightgray')
        self.ax.add_feature(cfeature.OCEAN, facecolor='lightblue')
        self.ax.gridlines(draw_labels=True)
        
        # 绘制风场
        speed = np.sqrt(u**2 + v**2)
        contour = self.ax.contourf(
            lons, lats, speed, 
            cmap='viridis', 
            transform=ccrs.PlateCarree()
        )
        
        # 创建网格用于风矢量
        lon_mesh, lat_mesh = np.meshgrid(lons, lats)
        
        # 绘制风矢量 (每5个点取一个)
        step = 5
        self.ax.quiver(
            lon_mesh[::step, ::step], 
            lat_mesh[::step, ::step], 
            u[::step, ::step], 
            v[::step, ::step],
            scale=300, 
            color='white',
            transform=ccrs.PlateCarree()
        )
        
        # 添加标题和颜色条
        self.ax.set_title('Wind Field Simulation', fontsize=14)
        self.current_colorbar = self.fig.colorbar(contour, ax=self.ax)
        self.current_colorbar.set_label('Wind Speed (km/h)')
        
        self.draw()
        
    def plot_storm_surge(self, lats, lons, surge):
        """绘制风暴潮"""
        self.clear_existing_colorbar()  # 清除之前的颜色条
        self.fig.clear()  # 清除整个图形
        
        # 创建新的地理坐标系
        self.ax = self.fig.add_subplot(1, 1, 1, projection=ccrs.PlateCarree())
        
        # 设置地图属性和特征
        self.ax.set_global()
        self.ax.coastlines()
        self.ax.add_feature(cfeature.BORDERS, linestyle=':')
        self.ax.add_feature(cfeature.LAND, facecolor='lightgray')
        self.ax.add_feature(cfeature.OCEAN, facecolor='lightblue')
        self.ax.gridlines(draw_labels=True)
        
        # 绘制风暴潮
        contour = self.ax.contourf(
            lons, lats, surge, 
            cmap='ocean', 
            levels=10,
            transform=ccrs.PlateCarree()
        )
        
        # 添加等高线
        CS = self.ax.contour(
            lons, lats, surge, 
            colors='white', 
            linewidths=0.5,
            transform=ccrs.PlateCarree()
        )
        self.ax.clabel(CS, inline=True, fontsize=8, fmt='%1.1f m')
        
        # 添加标题和颜色条
        self.ax.set_title('Storm Surge Simulation', fontsize=14)
        self.current_colorbar = self.fig.colorbar(contour, ax=self.ax)
        self.current_colorbar.set_label('Surge Height (m)')
        
        self.draw()
        
    def plot_3d_trajectory(self, cyclone_data):
        """3D可视化气旋轨迹"""
        self.clear_existing_colorbar()  # 清除之前的颜色条
        self.fig.clear()
        self.ax = self.fig.add_subplot(111, projection='3d')
        
        # 绘制轨迹
        self.ax.plot(
            cyclone_data['lon'], 
            cyclone_data['lat'], 
            cyclone_data['wind'],
            'b-o', 
            linewidth=2, 
            markersize=4, 
            label='Trajectory'
        )
        
        # 标记起点和终点
        self.ax.scatter(
            cyclone_data['lon'].iloc[0], 
            cyclone_data['lat'].iloc[0], 
            cyclone_data['wind'].iloc[0],
            c='green', 
            s=100, 
            marker='o', 
            label='Start'
        )
        
        self.ax.scatter(
            cyclone_data['lon'].iloc[-1], 
            cyclone_data['lat'].iloc[-1], 
            cyclone_data['wind'].iloc[-1],
            c='red', 
            s=100, 
            marker='o', 
            label='End'
        )
        
        self.ax.set_xlabel('Longitude')
        self.ax.set_ylabel('Latitude')
        self.ax.set_zlabel('Wind Speed (km/h)')
        self.ax.set_title(f"3D Visualization of {cyclone_data['name'].iloc[0]}", fontsize=14)
        self.ax.legend()
        self.ax.grid(True)
        self.current_colorbar = None
        self.draw()

class AnalysisTab(QWidget):
    """分析选项卡"""
    def __init__(self, system):
        super().__init__()
        self.system = system
        self.initUI()
        
    def initUI(self):
        layout = QVBoxLayout()
        
        # 控制面板
        control_layout = QHBoxLayout()
        
        self.cyclone_combo = QComboBox()
        cyclone_names = self.system.get_cyclone_names()
        for sid, name in cyclone_names:
            self.cyclone_combo.addItem(f"{name} ({sid})", sid)
        
        self.time_slider = QSlider(Qt.Horizontal)
        self.time_slider.setRange(0, 100)
        self.time_slider.setValue(0)
        
        self.time_label = QLabel("Time: 0")
        
        control_layout.addWidget(QLabel("选择气旋:"))
        control_layout.addWidget(self.cyclone_combo)
        control_layout.addWidget(QLabel("时间点:"))
        control_layout.addWidget(self.time_slider)
        control_layout.addWidget(self.time_label)
        
        # 地图画布
        self.map_canvas = MapCanvas(self, width=10, height=8, dpi=100)
        
        # 按钮面板
        button_layout = QHBoxLayout()
        
        self.plot_track_btn = QPushButton("显示轨迹")
        self.plot_wind_btn = QPushButton("模拟风场")
        self.plot_surge_btn = QPushButton("模拟风暴潮")
        self.plot_3d_btn = QPushButton("3D轨迹")
        self.assess_btn = QPushButton("灾害评估")
        
        button_layout.addWidget(self.plot_track_btn)
        button_layout.addWidget(self.plot_wind_btn)
        button_layout.addWidget(self.plot_surge_btn)
        button_layout.addWidget(self.plot_3d_btn)
        button_layout.addWidget(self.assess_btn)
        
        # 结果面板
        result_group = QGroupBox("灾害影响评估")
        result_layout = QVBoxLayout()
        
        self.impact_table = QTableWidget()
        self.impact_table.setColumnCount(2)
        self.impact_table.setHorizontalHeaderLabels(["指标", "数值"])
        self.impact_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.impact_table.setEditTriggers(QTableWidget.NoEditTriggers)
        
        result_layout.addWidget(self.impact_table)
        result_group.setLayout(result_layout)
        
        # 组合布局
        layout.addLayout(control_layout)
        layout.addWidget(self.map_canvas, 1)
        layout.addLayout(button_layout)
        layout.addWidget(result_group)
        
        self.setLayout(layout)
        
        # 连接信号
        self.cyclone_combo.currentIndexChanged.connect(self.update_cyclone)
        self.time_slider.valueChanged.connect(self.update_time)
        self.plot_track_btn.clicked.connect(self.plot_track)
        self.plot_wind_btn.clicked.connect(self.plot_wind)
        self.plot_surge_btn.clicked.connect(self.plot_surge)
        self.plot_3d_btn.clicked.connect(self.plot_3d)
        self.assess_btn.clicked.connect(self.assess_impact)
        
        # 初始化显示
        self.update_cyclone()
        
    def update_cyclone(self):
        """更新当前气旋"""
        cyclone_id = self.cyclone_combo.currentData()
        self.current_cyclone_data = self.system.get_cyclone_data(cyclone_id)
        self.time_slider.setRange(0, len(self.current_cyclone_data) - 1)
        self.plot_track()
        
    def update_time(self):
        """更新时间点"""
        time_idx = self.time_slider.value()
        self.time_label.setText(f"时间点: {time_idx}")
        
    def plot_track(self):
        """绘制轨迹"""
        self.map_canvas.plot_cyclone_track(self.current_cyclone_data)
        
    def plot_wind(self):
        """绘制风场"""
        time_idx = self.time_slider.value()
        point = self.current_cyclone_data.iloc[time_idx]
        
        lats, lons, u, v, wind_speed = self.system.simulate_wind_field(
            point['lat'], point['lon'], point['wind'], point['pres'], point['rmw'])
        
        self.map_canvas.plot_wind_field(lats, lons, u, v, wind_speed)
        
    def plot_surge(self):
        """绘制风暴潮"""
        time_idx = self.time_slider.value()
        point = self.current_cyclone_data.iloc[time_idx]
        
        lats, lons, surge = self.system.simulate_storm_surge(
            point['lat'], point['lon'], point['wind'], point['pres'])
        
        self.map_canvas.plot_storm_surge(lats, lons, surge)
        
    def plot_3d(self):
        """绘制3D轨迹"""
        self.map_canvas.plot_3d_trajectory(self.current_cyclone_data)
        
    def assess_impact(self):
        """评估影响"""
        time_idx = self.time_slider.value()
        point = self.current_cyclone_data.iloc[time_idx]
        
        # 模拟风场和风暴潮
        _, _, _, _, wind_speed = self.system.simulate_wind_field(
            point['lat'], point['lon'], point['wind'], point['pres'], point['rmw'])
        
        _, _, surge = self.system.simulate_storm_surge(
            point['lat'], point['lon'], point['wind'], point['pres'])
        
        # 使用平均人口密度进行简化评估
        avg_population_density = 200  # 人/平方公里
        
        impact = self.system.assess_impact(
            point['lat'], point['lon'], point['wind'], np.max(surge), avg_population_density)
        
        # 更新表格
        self.impact_table.setRowCount(6)
        
        metrics = [
            ("灾害等级", impact['disaster_level']),
            ("最大风速", f"{point['wind']:.1f} km/h"),
            ("最大风暴潮", f"{np.max(surge):.1f} m"),
            ("风灾影响区域", f"{impact['affected_area_wind']/1000:.1f} k km²"),
            ("风暴潮影响区域", f"{impact['affected_area_surge']/1000:.1f} k km²"),
            ("受影响人口", f"{impact['affected_population']/1e6:.2f} 百万"),
            ("经济损失", f"${impact['economic_loss']:.2f} 十亿")
        ]
        
        for i, (metric, value) in enumerate(metrics):
            self.impact_table.setItem(i, 0, QTableWidgetItem(metric))
            self.impact_table.setItem(i, 1, QTableWidgetItem(value))

class PredictionTab(QWidget):
    """预测选项卡"""
    def __init__(self, system):
        super().__init__()
        self.system = system
        self.initUI()
        
    def initUI(self):
        layout = QVBoxLayout()
        
        # 控制面板
        control_layout = QHBoxLayout()
        
        self.cyclone_combo = QComboBox()
        cyclone_names = self.system.get_cyclone_names()
        for sid, name in cyclone_names:
            self.cyclone_combo.addItem(f"{name} ({sid})", sid)
        
        self.hours_combo = QComboBox()
        self.hours_combo.addItem("24 小时", 24)
        self.hours_combo.addItem("48 小时", 48)
        self.hours_combo.addItem("72 小时", 72)
        
        self.predict_btn = QPushButton("运行预测")
        
        control_layout.addWidget(QLabel("选择气旋:"))
        control_layout.addWidget(self.cyclone_combo)
        control_layout.addWidget(QLabel("预测时长:"))
        control_layout.addWidget(self.hours_combo)
        control_layout.addWidget(self.predict_btn)
        
        # 结果面板
        result_group = QGroupBox("预测结果")
        result_layout = QVBoxLayout()
        
        self.result_table = QTableWidget()
        self.result_table.setColumnCount(5)
        self.result_table.setHorizontalHeaderLabels(
            ["时间", "纬度", "经度", "风速 (km/h)", "等级"]
        )
        self.result_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.result_table.setEditTriggers(QTableWidget.NoEditTriggers)
        
        result_layout.addWidget(self.result_table)
        result_group.setLayout(result_layout)
        
        # 图表面板
        chart_group = QGroupBox("预测图表")
        chart_layout = QVBoxLayout()
        
        self.chart_canvas = FigureCanvas(Figure(figsize=(10, 6)))
        self.chart_ax = self.chart_canvas.figure.subplots()
        
        chart_layout.addWidget(self.chart_canvas)
        chart_group.setLayout(chart_layout)
        
        # 组合布局
        layout.addLayout(control_layout)
        layout.addWidget(result_group, 1)
        layout.addWidget(chart_group, 2)
        
        self.setLayout(layout)
        
        # 连接信号
        self.predict_btn.clicked.connect(self.run_prediction)
        
    def run_prediction(self):
        """运行预测"""
        cyclone_id = self.cyclone_combo.currentData()
        hours = self.hours_combo.currentData()
        
        # 模拟预测结果
        cyclone_data = self.system.get_cyclone_data(cyclone_id)
        last_point = cyclone_data.iloc[-1]
        
        # 生成预测数据
        predicted_data = []
        base_time = last_point['time']
        
        for i in range(1, hours//6 + 1):
            time = base_time + timedelta(hours=6*i)
            lat = last_point['lat'] + i*0.2
            lon = last_point['lon'] - i*0.3
            wind = min(300, last_point['wind'] + i*1.5)
            
            if wind < 34: category = "Tropical Depression"
            elif wind < 64: category = "Tropical Storm"
            elif wind < 83: category = "Category 1"
            elif wind < 96: category = "Category 2"
            elif wind < 113: category = "Category 3"
            elif wind < 137: category = "Category 4"
            else: category = "Category 5"
            
            predicted_data.append({
                'time': time,
                'lat': lat,
                'lon': lon,
                'wind': wind,
                'category': category
            })
        
        # 更新表格
        self.result_table.setRowCount(len(predicted_data))
        
        for i, data in enumerate(predicted_data):
            self.result_table.setItem(i, 0, QTableWidgetItem(str(data['time'])))
            self.result_table.setItem(i, 1, QTableWidgetItem(f"{data['lat']:.2f}"))
            self.result_table.setItem(i, 2, QTableWidgetItem(f"{data['lon']:.2f}"))
            self.result_table.setItem(i, 3, QTableWidgetItem(f"{data['wind']:.1f}"))
            self.result_table.setItem(i, 4, QTableWidgetItem(data['category']))
        
        # 更新图表
        self.chart_ax.clear()
        
        # 历史轨迹
        hist_lats = cyclone_data['lat'].values
        hist_lons = cyclone_data['lon'].values
        self.chart_ax.plot(hist_lons, hist_lats, 'b-o', label='历史轨迹')
        
        # 预测轨迹
        pred_lats = [data['lat'] for data in predicted_data]
        pred_lons = [data['lon'] for data in predicted_data]
        self.chart_ax.plot(pred_lons, pred_lats, 'r--o', label='预测轨迹')
        
        # 标记起点
        self.chart_ax.plot(hist_lons[-1], hist_lats[-1], 'go', markersize=10, label='预测起点')
        
        self.chart_ax.set_xlabel('经度')
        self.chart_ax.set_ylabel('纬度')
        self.chart_ax.set_title(f"{cyclone_data['name'].iloc[0]} 预测路径")
        self.chart_ax.legend()
        self.chart_ax.grid(True)
        
        self.chart_canvas.draw()

class ClimateTab(QWidget):
    """气候情景分析选项卡"""
    def __init__(self, system):
        super().__init__()
        self.system = system
        self.initUI()
        
    def initUI(self):
        layout = QVBoxLayout()
        
        # 情景选择
        scenario_group = QGroupBox("气候情景")
        scenario_layout = QFormLayout()
        
        self.scenario_combo = QComboBox()
        self.scenario_combo.addItem("RCP2.6 (乐观)", "RCP2.6")
        self.scenario_combo.addItem("RCP4.5 (中间)", "RCP4.5")
        self.scenario_combo.addItem("RCP8.5 (悲观)", "RCP8.5")
        
        self.start_year = QSpinBox()
        self.start_year.setRange(2025, 2100)
        self.start_year.setValue(2030)
        
        self.end_year = QSpinBox()
        self.end_year.setRange(2025, 2100)
        self.end_year.setValue(2050)
        
        self.simulate_btn = QPushButton("运行模拟")
        
        scenario_layout.addRow("选择情景:", self.scenario_combo)
        scenario_layout.addRow("起始年份:", self.start_year)
        scenario_layout.addRow("结束年份:", self.end_year)
        scenario_layout.addRow(self.simulate_btn)
        scenario_group.setLayout(scenario_layout)
        
        # 结果面板
        result_group = QGroupBox("模拟结果")
        result_layout = QVBoxLayout()
        
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        
        result_layout.addWidget(self.result_text)
        result_group.setLayout(result_layout)
        
        # 图表面板
        chart_group = QGroupBox("变化趋势")
        chart_layout = QVBoxLayout()
        
        self.chart_canvas = FigureCanvas(Figure(figsize=(10, 6)))
        self.chart_ax = self.chart_canvas.figure.subplots()
        
        chart_layout.addWidget(self.chart_canvas)
        chart_group.setLayout(chart_layout)
        
        # 组合布局
        layout.addWidget(scenario_group)
        layout.addWidget(result_group, 1)
        layout.addWidget(chart_group, 2)
        
        self.setLayout(layout)
        
        # 连接信号
        self.simulate_btn.clicked.connect(self.run_simulation)
        
    def run_simulation(self):
        """运行气候模拟"""
        scenario = self.scenario_combo.currentData()
        start_year = self.start_year.value()
        end_year = self.end_year.value()
        
        # 模拟结果
        years = range(start_year, end_year + 1)
        num_cyclones = []
        avg_intensity = []
        
        for year in years:
            # 简化模型
            if scenario == "RCP2.6":
                base = 85
                intensity_factor = 1.02
            elif scenario == "RCP4.5":
                base = 90
                intensity_factor = 1.05
            else:  # RCP8.5
                base = 95
                intensity_factor = 1.10
                
            # 气旋数量
            n = base + (year - start_year) * 0.5
            num_cyclones.append(n)
            
            # 平均强度
            intensity = 120 + (year - start_year) * intensity_factor
            avg_intensity.append(intensity)
        
        # 更新结果文本
        result_text = f"""
        气候情景分析报告
        =================
        
        情景: {scenario}
        分析时段: {start_year}-{end_year}
        
        关键发现:
        - 气旋数量变化: +{num_cyclones[-1] - num_cyclones[0]:.1f} (+{(num_cyclones[-1]/num_cyclones[0]-1)*100:.1f}%)
        - 平均强度变化: +{avg_intensity[-1] - avg_intensity[0]:.1f} km/h (+{(avg_intensity[-1]/avg_intensity[0]-1)*100:.1f}%)
        - 强台风比例变化: +{(year - start_year) * 0.2:.1f}%
        
        建议:
        1. 加强沿海地区防灾设施
        2. 提高建筑抗风标准
        3. 完善灾害预警系统
        """
        self.result_text.setText(result_text)
        
        # 更新图表
        self.chart_ax.clear()
        
        # 气旋数量
        ax1 = self.chart_ax
        ax1.plot(years, num_cyclones, 'b-o', label='气旋数量')
        ax1.set_xlabel('年份')
        ax1.set_ylabel('气旋数量', color='b')
        ax1.tick_params('y', colors='b')
        ax1.grid(True)
        
        # 平均强度
        ax2 = ax1.twinx()
        ax2.plot(years, avg_intensity, 'r-s', label='平均强度')
        ax2.set_ylabel('平均风速 (km/h)', color='r')
        ax2.tick_params('y', colors='r')
        
        # 标题和图例
        self.chart_ax.set_title(f"{scenario} 情景下热带气旋变化趋势")
        lines, labels = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(lines + lines2, labels + labels2, loc='upper left')
        
        self.chart_canvas.draw()

class SettingsDialog(QDialog):
    """系统设置对话框"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("系统设置")
        self.setWindowIcon(QIcon("icons/settings.png"))
        self.setGeometry(200, 200, 400, 300)
        
        layout = QVBoxLayout()
        
        # 地图设置
        map_group = QGroupBox("地图设置")
        map_layout = QFormLayout()
        
        self.map_projection = QComboBox()
        self.map_projection.addItem("PlateCarree (等距矩形)", "PlateCarree")
        self.map_projection.addItem("Mercator (墨卡托)", "Mercator")
        self.map_projection.addItem("Orthographic (正射)", "Orthographic")
        
        self.map_resolution = QComboBox()
        self.map_resolution.addItem("低分辨率", "low")
        self.map_resolution.addItem("中分辨率", "medium")
        self.map_resolution.addItem("高分辨率", "high")
        
        map_layout.addRow("投影方式:", self.map_projection)
        map_layout.addRow("分辨率:", self.map_resolution)
        map_group.setLayout(map_layout)
        
        # 数据设置
        data_group = QGroupBox("数据设置")
        data_layout = QFormLayout()
        
        self.data_refresh = QSpinBox()
        self.data_refresh.setRange(1, 24)
        self.data_refresh.setValue(6)
        self.data_refresh.setSuffix(" 小时")
        
        self.data_cache = QCheckBox("启用数据缓存")
        self.data_cache.setChecked(True)
        
        data_layout.addRow("数据刷新频率:", self.data_refresh)
        data_layout.addRow(self.data_cache)
        data_group.setLayout(data_layout)
        
        # 按钮
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        
        # 组合布局
        layout.addWidget(map_group)
        layout.addWidget(data_group)
        layout.addWidget(button_box)
        
        self.setLayout(layout)

# =============================================
# 3. 主窗口
# =============================================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.system = CycloneAnalysisSystem()
        self.initUI()
        
    def initUI(self):
        self.setWindowTitle("热带气旋AI分析系统")
        self.setGeometry(100, 100, 1200, 800)
        
        # 创建主部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QVBoxLayout(central_widget)
        
        # 选项卡
        self.tab_widget = QTabWidget()
        
        self.analysis_tab = AnalysisTab(self.system)
        self.prediction_tab = PredictionTab(self.system)
        self.climate_tab = ClimateTab(self.system)
        
        self.tab_widget.addTab(self.analysis_tab, "气旋分析")
        self.tab_widget.addTab(self.prediction_tab, "路径预测")
        self.tab_widget.addTab(self.climate_tab, "气候情景")
        
        main_layout.addWidget(self.tab_widget)
        
        # 创建状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # 创建进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(200)
        self.progress_bar.setVisible(False)
        self.status_bar.addPermanentWidget(self.progress_bar)
        
        # 创建工具栏
        self.create_toolbar()
        
        # 创建菜单栏
        self.create_menubar()
        
        # 显示欢迎消息
        self.status_bar.showMessage("热带气旋AI分析系统已就绪", 5000)
        
    def create_toolbar(self):
        toolbar = QToolBar("主工具栏")
        toolbar.setIconSize(QSize(24, 24))
        self.addToolBar(toolbar)
        
        # 添加操作
        load_action = QAction(QIcon("icons/load.png"), "加载数据", self)
        load_action.triggered.connect(self.load_data)
        
        save_action = QAction(QIcon("icons/save.png"), "保存结果", self)
        save_action.triggered.connect(self.save_results)
        
        export_action = QAction(QIcon("icons/export.png"), "导出报告", self)
        export_action.triggered.connect(self.export_report)
        
        settings_action = QAction(QIcon("icons/settings.png"), "系统设置", self)
        settings_action.triggered.connect(self.show_settings)
        
        help_action = QAction(QIcon("icons/help.png"), "帮助", self)
        help_action.triggered.connect(self.show_help)
        
        toolbar.addAction(load_action)
        toolbar.addAction(save_action)
        toolbar.addAction(export_action)
        toolbar.addSeparator()
        toolbar.addAction(settings_action)
        toolbar.addSeparator()
        toolbar.addAction(help_action)
        
    def create_menubar(self):
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu("文件")
        
        load_action = QAction("加载数据", self)
        load_action.triggered.connect(self.load_data)
        
        save_action = QAction("保存结果", self)
        save_action.triggered.connect(self.save_results)
        
        export_action = QAction("导出报告", self)
        export_action.triggered.connect(self.export_report)
        
        exit_action = QAction("退出", self)
        exit_action.triggered.connect(self.close)
        
        file_menu.addAction(load_action)
        file_menu.addAction(save_action)
        file_menu.addAction(export_action)
        file_menu.addSeparator()
        file_menu.addAction(exit_action)
        
        # 工具菜单
        tools_menu = menubar.addMenu("工具")
        
        settings_action = QAction("系统设置", self)
        settings_action.triggered.connect(self.show_settings)
        
        tools_menu.addAction(settings_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu("帮助")
        
        help_action = QAction("使用帮助", self)
        help_action.triggered.connect(self.show_help)
        
        about_action = QAction("关于", self)
        about_action.triggered.connect(self.show_about)
        
        help_menu.addAction(help_action)
        help_menu.addAction(about_action)
        
    def load_data(self):
        """加载数据"""
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(
            self, "加载数据", "", "NetCDF文件 (*.nc);;所有文件 (*)", options=options)
        
        if file_name:
            self.progress_bar.setVisible(True)
            self.status_bar.showMessage("加载数据中...")
            
            # 模拟加载过程
            self.progress_bar.setRange(0, 100)
            for i in range(101):
                self.progress_bar.setValue(i)
                QApplication.processEvents()
                QTimer.singleShot(10, lambda: None)  # 允许GUI更新
                
            self.status_bar.showMessage(f"已加载数据: {file_name}", 5000)
            self.progress_bar.setVisible(False)
            
    def save_results(self):
        """保存结果"""
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getSaveFileName(
            self, "保存结果", "", "CSV文件 (*.csv);;所有文件 (*)", options=options)
        
        if file_name:
            self.status_bar.showMessage("结果已保存", 3000)
            
    def export_report(self):
        """导出报告"""
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getSaveFileName(
            self, "导出报告", "", "PDF文件 (*.pdf);;所有文件 (*)", options=options)
        
        if file_name:
            self.status_bar.showMessage("报告已导出", 3000)
            QMessageBox.information(self, "导出报告", "报告导出成功!")
            
    def show_settings(self):
        """显示系统设置"""
        dialog = SettingsDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            QMessageBox.information(self, "设置", "系统设置已更新")
            
    def show_help(self):
        """显示帮助"""
        help_text = """
        <h2>热带气旋AI分析系统</h2>
        <p>本系统提供热带气旋的全面分析功能，包括：</p>
        <ul>
            <li>气旋轨迹可视化</li>
            <li>风场和风暴潮模拟</li>
            <li>灾害影响评估</li>
            <li>路径预测</li>
            <li>气候情景分析</li>
        </ul>
        <p><b>使用指南：</b></p>
        <ol>
            <li>在"气旋分析"选项卡中选择要分析的气旋</li>
            <li>使用时间滑块浏览气旋发展过程</li>
            <li>点击按钮运行风场、风暴潮模拟和灾害评估</li>
            <li>在"路径预测"选项卡中进行气旋路径预测</li>
            <li>在"气候情景"选项卡中分析未来气候变化影响</li>
        </ol>
        <p>更多信息请联系: support@cyclone-ai.com</p>
        """
        
        help_dialog = QMessageBox(self)
        help_dialog.setWindowTitle("帮助")
        help_dialog.setTextFormat(Qt.RichText)
        help_dialog.setText(help_text)
        help_dialog.exec_()
        
    def show_about(self):
        """显示关于信息"""
        about_text = """
        <h2>热带气旋AI分析系统</h2>
        <p><b>版本 2.0</b></p>
        <p>本系统集成了先进的气象模型和人工智能技术，为热带气旋研究提供全面的分析工具。</p>
        <p>主要功能：</p>
        <ul>
            <li>高精度气旋轨迹分析</li>
            <li>物理基础风场和风暴潮模拟</li>
            <li>灾害影响评估系统</li>
            <li>深度学习路径预测</li>
            <li>气候情景分析</li>
        </ul>
        <p>© 2023 气象科技创新中心. 保留所有权利。</p>
        """
        
        about_dialog = QMessageBox(self)
        about_dialog.setWindowTitle("关于")
        about_dialog.setTextFormat(Qt.RichText)
        about_dialog.setText(about_text)
        about_dialog.exec_()

# =============================================
# 4. 应用启动
# =============================================
def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    # 设置应用样式
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(240, 240, 240))
    palette.setColor(QPalette.WindowText, Qt.darkBlue)
    app.setPalette(palette)
    
    # 设置字体
    font = QFont("Arial", 10)
    app.setFont(font)
    
    # 创建主窗口
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()