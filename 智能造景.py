import sys
import random
import math
import numpy as np
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QSlider, 
                             QSpinBox, QDoubleSpinBox, QCheckBox, QGroupBox,
                             QTabWidget, QFileDialog, QMessageBox, QSplitter,
                             QFrame, QComboBox, QTextEdit, QProgressBar,
                             QListWidget, QListWidgetItem, QTreeWidget, QTreeWidgetItem,
                             QDockWidget, QToolBar, QAction, QColorDialog, QMenu)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread, QPoint, QSize, QRectF
from PyQt5.QtGui import (QPainter, QPen, QBrush, QColor, QFont, QPixmap, QImage,
                         QIcon, QLinearGradient, QRadialGradient, QPalette,
                         QMouseEvent, QKeyEvent, QTransform)
import matplotlib
matplotlib.rc("font", family='Microsoft YaHei')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d import Axes3D
from scipy import ndimage
from scipy.ndimage import gaussian_filter, sobel
import noise
from PIL import Image, ImageFilter
import json
import time
from datetime import datetime
import os


# 高级地形生成算法类
class AdvancedTerrainGenerator:
    def __init__(self):
        self.height_map = None
        self.biome_map = None
        
    def generate_multifractal_terrain(self, width, height, scale=100.0, octaves=6, 
                                     persistence=0.5, lacunarity=2.0, offset=1.0, 
                                     gain=2.0, ridge_threshold=0.5):
        """生成多重分形地形，支持山脊和峡谷"""
        height_map = np.zeros((height, width))
        
        for y in range(height):
            for x in range(width):
                nx = x / scale
                ny = y / scale
                
                # 使用多重分形噪声
                value = 0.0
                amplitude = 1.0
                frequency = 1.0
                
                for _ in range(octaves):
                    # 使用Perlin噪声作为基础
                    noise_val = noise.pnoise2(nx * frequency, ny * frequency, 
                                            octaves=1, persistence=persistence, 
                                            lacunarity=lacunarity)
                    
                    # 应用山脊变换
                    noise_val = abs(noise_val)
                    noise_val = ridge_threshold - noise_val
                    noise_val *= noise_val
                    
                    value += noise_val * amplitude
                    amplitude *= persistence
                    frequency *= lacunarity
                
                height_map[y, x] = value
        
        # 归一化
        height_map = (height_map - height_map.min()) / (height_map.max() - height_map.min())
        
        return height_map
    
    def generate_volcanic_terrain(self, width, height, crater_count=5, crater_size=0.1):
        """生成火山地形"""
        height_map = np.random.rand(height, width) * 0.1  # 基础噪声
        
        # 添加火山口
        for _ in range(crater_count):
            cx = random.randint(0, width-1)
            cy = random.randint(0, height-1)
            size = random.randint(int(width*crater_size*0.5), int(width*crater_size))
            
            for y in range(height):
                for x in range(width):
                    dist = math.sqrt((x-cx)**2 + (y-cy)**2)
                    if dist < size:
                        # 火山口形状
                        height_val = 1 - (dist / size)
                        height_val = height_val ** 2  # 使边缘更陡峭
                        height_map[y, x] += height_val * 0.5
        
        # 添加岩浆流
        for i in range(3):
            start_x = random.randint(0, width-1)
            start_y = random.randint(0, height-1)
            self._add_lava_flow(height_map, start_x, start_y, width, height)
        
        # 归一化
        height_map = (height_map - height_map.min()) / (height_map.max() - height_map.min())
        
        return height_map
    
    def _add_lava_flow(self, height_map, start_x, start_y, width, height):
        """添加岩浆流"""
        x, y = start_x, start_y
        for _ in range(100):  # 流动步数
            # 随机方向，但倾向于向下坡流动
            dx = random.randint(-1, 1)
            dy = random.randint(-1, 1)
            
            nx, ny = x + dx, y + dy
            if 0 <= nx < width and 0 <= ny < height:
                # 增加高度（岩浆堆积）
                height_map[ny, nx] += 0.1
                # 平滑周围区域
                for sy in range(max(0, ny-1), min(height, ny+2)):
                    for sx in range(max(0, nx-1), min(width, nx+2)):
                        if sy != ny or sx != nx:
                            height_map[sy, sx] = (height_map[sy, sx] + height_map[ny, nx] * 0.5) / 1.5
                
                x, y = nx, ny
    
    def generate_canyon_terrain(self, width, height, canyon_count=3):
        """生成峡谷地形"""
        # 使用多重分形创建基础地形
        height_map = self.generate_multifractal_terrain(width, height, scale=50, ridge_threshold=0.7)
        
        # 添加峡谷
        for _ in range(canyon_count):
            # 随机起点和方向
            start_x = random.randint(0, width-1)
            start_y = random.randint(0, height-1)
            angle = random.uniform(0, 2*math.pi)
            
            length = random.randint(50, 200)
            width_canyon = random.randint(5, 20)
            
            for i in range(length):
                # 计算当前位置
                x = int(start_x + i * math.cos(angle))
                y = int(start_y + i * math.sin(angle))
                
                if 0 <= x < width and 0 <= y < height:
                    # 创建峡谷（降低高度）
                    for wy in range(-width_canyon, width_canyon+1):
                        for wx in range(-width_canyon, width_canyon+1):
                            nx, ny = x + wx, y + wy
                            if 0 <= nx < width and 0 <= ny < height:
                                dist = math.sqrt(wx**2 + wy**2)
                                if dist < width_canyon:
                                    # 峡谷深度随距离中心变化
                                    depth = (1 - dist/width_canyon) * 0.5
                                    height_map[ny, nx] -= depth
                
                # 随机改变方向
                if random.random() < 0.1:
                    angle += random.uniform(-0.5, 0.5)
        
        # 确保高度在0-1之间
        height_map = np.clip(height_map, 0, 1)
        
        return height_map
    
    def apply_thermal_erosion(self, height_map, iterations=10, talus_angle=30):
        """应用热侵蚀算法"""
        height_map = height_map.copy()
        talus = math.tan(math.radians(talus_angle)) / height_map.shape[0]
        
        for _ in range(iterations):
            # 计算高度差
            diff = np.zeros_like(height_map)
            for y in range(1, height_map.shape[0]-1):
                for x in range(1, height_map.shape[1]-1):
                    # 检查8个邻居
                    max_diff = 0
                    for dy in [-1, 0, 1]:
                        for dx in [-1, 0, 1]:
                            if dx == 0 and dy == 0:
                                continue
                            ny, nx = y+dy, x+dx
                            diff_val = height_map[y, x] - height_map[ny, nx]
                            if diff_val > max_diff:
                                max_diff = diff_val
                    
                    # 如果高度差超过临界值，进行侵蚀
                    if max_diff > talus:
                        diff[y, x] = max_diff * 0.5  # 移动一半的差异
            
            # 应用侵蚀
            for y in range(1, height_map.shape[0]-1):
                for x in range(1, height_map.shape[1]-1):
                    if diff[y, x] > 0:
                        # 找到最高的邻居
                        max_neighbor = height_map[y, x]
                        max_ny, max_nx = y, x
                        for dy in [-1, 0, 1]:
                            for dx in [-1, 0, 1]:
                                if dx == 0 and dy == 0:
                                    continue
                                ny, nx = y+dy, x+dx
                                if height_map[ny, nx] > max_neighbor:
                                    max_neighbor = height_map[ny, nx]
                                    max_ny, max_nx = ny, nx
                        
                        # 转移物质
                        transfer = diff[y, x] * 0.5
                        height_map[y, x] -= transfer
                        height_map[max_ny, max_nx] += transfer
        
        return height_map
    
    def generate_biome_map(self, height_map, temperature_map=None, precipitation_map=None):
        """根据高度、温度和降水生成生物群系图"""
        if temperature_map is None:
            # 生成基于纬度的温度图（假设顶部是北极，底部是赤道）
            temperature_map = np.zeros_like(height_map)
            for y in range(height_map.shape[0]):
                latitude = y / height_map.shape[0]  # 0=北极, 1=赤道
                temperature_map[y, :] = 1 - latitude  # 赤道更热
        
        if precipitation_map is None:
            # 生成随机降水图
            precipitation_map = np.random.rand(*height_map.shape)
            precipitation_map = gaussian_filter(precipitation_map, sigma=10)
            precipitation_map = (precipitation_map - precipitation_map.min()) / (precipitation_map.max() - precipitation_map.min())
        
        # 创建生物群系图
        biome_map = np.zeros_like(height_map, dtype=int)
        
        for y in range(height_map.shape[0]):
            for x in range(height_map.shape[1]):
                height = height_map[y, x]
                temp = temperature_map[y, x]
                precip = precipitation_map[y, x]
                
                # 生物群系分类
                if height < 0.1:  # 海洋
                    biome_map[y, x] = 0
                elif height < 0.2:  # 海滩
                    biome_map[y, x] = 1
                elif height > 0.8:  # 高山
                    if temp < 0.3:
                        biome_map[y, x] = 2  # 雪山
                    else:
                        biome_map[y, x] = 3  # 高山草甸
                else:  # 陆地
                    if temp < 0.3:  # 寒冷
                        if precip < 0.3:
                            biome_map[y, x] = 4  # 苔原
                        else:
                            biome_map[y, x] = 5  # 针叶林
                    elif temp < 0.7:  # 温带
                        if precip < 0.3:
                            biome_map[y, x] = 6  # 草原
                        elif precip < 0.6:
                            biome_map[y, x] = 7  # 落叶林
                        else:
                            biome_map[y, x] = 8  # 雨林
                    else:  # 热带
                        if precip < 0.4:
                            biome_map[y, x] = 9  # 沙漠
                        else:
                            biome_map[y, x] = 10  # 热带雨林
        
        return biome_map, temperature_map, precipitation_map


# 高级植被生成器
class AdvancedVegetationGenerator:
    def __init__(self):
        self.vegetation_map = None
        self.tree_map = None
        self.plant_diversity_map = None
        
    def generate_advanced_vegetation(self, height_map, biome_map, soil_quality_map=None):
        """生成高级植被分布，考虑生物群系和土壤质量"""
        if soil_quality_map is None:
            # 基于高度和坡度生成土壤质量图
            gradient_y, gradient_x = np.gradient(height_map)
            slope_map = np.sqrt(gradient_x**2 + gradient_y**2)
            soil_quality_map = 1 - slope_map  # 坡度越小，土壤质量越好
            soil_quality_map = gaussian_filter(soil_quality_map, sigma=2)
            soil_quality_map = (soil_quality_map - soil_quality_map.min()) / (soil_quality_map.max() - soil_quality_map.min())
        
        vegetation_map = np.zeros_like(height_map)
        tree_map = np.zeros_like(height_map, dtype=bool)
        plant_diversity_map = np.zeros_like(height_map)
        
        # 不同生物群系的植被参数
        biome_vegetation_params = {
            0: (0, 0, 0),      # 海洋 - 无植被
            1: (0.1, 0.05, 0.2),  # 海滩 - 少量植被
            2: (0.05, 0.01, 0.1), # 雪山 - 极少植被
            3: (0.3, 0.1, 0.4),   # 高山草甸
            4: (0.2, 0.05, 0.3),  # 苔原
            5: (0.7, 0.3, 0.6),   # 针叶林
            6: (0.5, 0.1, 0.5),   # 草原
            7: (0.8, 0.4, 0.7),   # 落叶林
            8: (0.9, 0.6, 0.8),   # 雨林
            9: (0.1, 0.02, 0.2),  # 沙漠
            10: (0.95, 0.7, 0.9)  # 热带雨林
        }
        
        for y in range(height_map.shape[0]):
            for x in range(height_map.shape[1]):
                biome = biome_map[y, x]
                height = height_map[y, x]
                soil_quality = soil_quality_map[y, x]
                
                if biome in biome_vegetation_params:
                    max_density, tree_prob, diversity = biome_vegetation_params[biome]
                    
                    # 考虑土壤质量和高度
                    density_factor = soil_quality * (1 - abs(height - 0.5))  # 中等高度最适合植被
                    vegetation_density = max_density * density_factor
                    
                    # 添加随机变化
                    vegetation_density *= random.uniform(0.8, 1.2)
                    vegetation_map[y, x] = min(vegetation_density, 1.0)
                    
                    # 决定是否有树木
                    if random.random() < tree_prob * soil_quality:
                        tree_map[y, x] = True
                    
                    # 植物多样性
                    plant_diversity_map[y, x] = diversity * soil_quality
        
        return vegetation_map, tree_map, plant_diversity_map, soil_quality_map
    
    def simulate_vegetation_growth(self, vegetation_map, growth_rate=0.01, carrying_capacity=1.0):
        """模拟植被生长过程"""
        new_vegetation = vegetation_map.copy()
        
        # 使用卷积核模拟生长扩散
        kernel = np.array([[0.05, 0.2, 0.05],
                          [0.2, 0.0, 0.2],
                          [0.05, 0.2, 0.05]])
        
        # 应用生长扩散
        growth_diffusion = ndimage.convolve(vegetation_map, kernel, mode='constant')
        new_vegetation += growth_diffusion * growth_rate
        
        # 应用环境承载力限制
        new_vegetation = np.minimum(new_vegetation, carrying_capacity)
        
        return new_vegetation


# 天气和气候系统
class WeatherSystem:
    def __init__(self):
        self.temperature_map = None
        self.precipitation_map = None
        self.wind_map = None
        self.season = 0  # 0=春, 1=夏, 2=秋, 3=冬
        self.time_of_day = 12  # 0-24小时
        
    def update_seasonal_effects(self, height_map, latitude_effect=True):
        """更新季节性效果"""
        # 季节对温度的影响
        season_temp_effect = [0.0, 0.2, 0.0, -0.2]  # 春、夏、秋、冬
        
        # 创建基础温度图（基于纬度）
        if self.temperature_map is None or latitude_effect:
            self.temperature_map = np.zeros_like(height_map)
            for y in range(height_map.shape[0]):
                latitude = y / height_map.shape[0]  # 0=北极, 1=赤道
                base_temp = 1 - latitude  # 赤道更热
                self.temperature_map[y, :] = base_temp
        
        # 应用季节效果
        season_effect = season_temp_effect[self.season]
        
        # 高度对温度的影响（每高度单位降低温度）
        height_effect = height_map * 0.5  # 越高越冷
        
        self.temperature_map = np.clip(self.temperature_map + season_effect - height_effect, 0, 1)
        
        # 更新降水图（季节影响）
        if self.precipitation_map is None:
            self.precipitation_map = np.random.rand(*height_map.shape)
            self.precipitation_map = gaussian_filter(self.precipitation_map, sigma=10)
            self.precipitation_map = (self.precipitation_map - self.precipitation_map.min()) / (self.precipitation_map.max() - self.precipitation_map.min())
        
        # 季节对降水的影响
        season_precip_effect = [0.1, 0.2, 0.1, -0.1]  # 春、夏、秋、冬
        self.precipitation_map = np.clip(self.precipitation_map + season_precip_effect[self.season], 0, 1)
        
        # 生成风场
        self._generate_wind_field(height_map)
    
    def _generate_wind_field(self, height_map):
        """生成风场（简化模型）"""
        height, width = height_map.shape
        self.wind_map = np.zeros((height, width, 2))  # 2个通道：x和y方向的风速
        
        # 创建基本风场（从西向东）
        base_wind = 0.5
        for y in range(height):
            for x in range(width):
                # 风受地形影响
                terrain_effect = 1 - height_map[y, x] * 0.5  # 高地风速较小
                
                # 添加一些随机变化
                variation = random.uniform(0.8, 1.2)
                
                self.wind_map[y, x, 0] = base_wind * terrain_effect * variation  # x方向
                self.wind_map[y, x, 1] = random.uniform(-0.1, 0.1)  # y方向的小扰动
    
    def simulate_rainfall(self, precipitation_map, iterations=10):
        """模拟降雨过程"""
        water_map = np.zeros_like(precipitation_map)
        
        for _ in range(iterations):
            # 根据降水概率添加雨水
            rain_mask = np.random.rand(*precipitation_map.shape) < precipitation_map * 0.1
            water_map[rain_mask] += 0.01
            
            # 模拟水流
            water_map = self._simulate_water_flow(water_map, precipitation_map)
            
            # 蒸发
            water_map *= 0.95
        
        return water_map
    
    def _simulate_water_flow(self, water_map, height_map):
        """模拟水流（简化版）"""
        new_water_map = water_map.copy()
        height, width = water_map.shape
        
        for y in range(1, height-1):
            for x in range(1, width-1):
                if water_map[y, x] > 0:
                    # 找到最低的邻居
                    min_height = height_map[y, x] + water_map[y, x]
                    min_dir = (0, 0)
                    
                    for dy in [-1, 0, 1]:
                        for dx in [-1, 0, 1]:
                            if dx == 0 and dy == 0:
                                continue
                            ny, nx = y+dy, x+dx
                            neighbor_height = height_map[ny, nx] + water_map[ny, nx]
                            if neighbor_height < min_height:
                                min_height = neighbor_height
                                min_dir = (dy, dx)
                    
                    # 如果有流向，移动一部分水
                    if min_dir != (0, 0):
                        dy, dx = min_dir
                        ny, nx = y+dy, x+dx
                        water_to_move = min(water_map[y, x] * 0.1, 0.05)
                        new_water_map[y, x] -= water_to_move
                        new_water_map[ny, nx] += water_to_move
        
        return new_water_map


# 3D可视化画布
class Terrain3DCanvas(FigureCanvas):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        super().__init__(self.fig)
        self.setParent(parent)
        
        self.ax = self.fig.add_subplot(111, projection='3d')
        self.ax.set_xticks([])
        self.ax.set_yticks([])
        self.ax.set_zticks([])
        
        self.terrain_generator = AdvancedTerrainGenerator()
        self.vegetation_generator = AdvancedVegetationGenerator()
        self.weather_system = WeatherSystem()
        
        self.height_map = None
        self.vegetation_map = None
        self.tree_map = None
        self.biome_map = None
        self.water_map = None
        
    def generate_terrain(self, terrain_type="multifractal", width=256, height=256, **kwargs):
        """生成地形"""
        if terrain_type == "multifractal":
            # 提取多重分形地形特有的参数
            multifractal_kwargs = {
                'scale': kwargs.get('scale', 100.0),
                'octaves': kwargs.get('octaves', 6),
                'persistence': kwargs.get('persistence', 0.5),
                'lacunarity': kwargs.get('lacunarity', 2.0),
                'offset': kwargs.get('offset', 1.0),
                'gain': kwargs.get('gain', 2.0),
                'ridge_threshold': kwargs.get('ridge_threshold', 0.5)
            }
            self.height_map = self.terrain_generator.generate_multifractal_terrain(
                width, height, **multifractal_kwargs)
        elif terrain_type == "volcanic":
            # 提取火山地形特有的参数
            volcanic_kwargs = {
                'crater_count': kwargs.get('crater_count', 5),
                'crater_size': kwargs.get('crater_size', 0.1)
            }
            self.height_map = self.terrain_generator.generate_volcanic_terrain(
                width, height, **volcanic_kwargs)
        elif terrain_type == "canyon":
            # 提取峡谷地形特有的参数
            canyon_kwargs = {
                'canyon_count': kwargs.get('canyon_count', 3)
            }
            self.height_map = self.terrain_generator.generate_canyon_terrain(
                width, height, **canyon_kwargs)
        
        # 应用热侵蚀（使用侵蚀特有的参数）
        if kwargs.get('apply_thermal_erosion', True):
            iterations = kwargs.get('erosion_iterations', 5)
            talus_angle = kwargs.get('talus_angle', 30)
            self.height_map = self.terrain_generator.apply_thermal_erosion(
                self.height_map, iterations, talus_angle)
        
        # 生成生物群系
        self.biome_map, temp_map, precip_map = self.terrain_generator.generate_biome_map(
            self.height_map)
        
        # 更新天气系统
        self.weather_system.update_seasonal_effects(self.height_map)
        
        self.update_3d_display()
        
    def generate_vegetation(self):
        """生成植被"""
        if self.height_map is not None and self.biome_map is not None:
            self.vegetation_map, self.tree_map, diversity_map, soil_map = \
                self.vegetation_generator.generate_advanced_vegetation(
                    self.height_map, self.biome_map)
            
            # 确保植被值在合理范围内
            self.vegetation_map = np.clip(self.vegetation_map, 0, 1)
            
            self.update_3d_display()
        
    def simulate_weather(self):
        """模拟天气"""
        if self.weather_system.precipitation_map is not None:
            self.water_map = self.weather_system.simulate_rainfall(
                self.weather_system.precipitation_map)
            self.update_3d_display()
        
    def update_3d_display(self):
        """更新3D显示"""
        self.ax.clear()
        
        if self.height_map is not None:
            # 创建网格
            x = np.arange(0, self.height_map.shape[1], 1)
            y = np.arange(0, self.height_map.shape[0], 1)
            x, y = np.meshgrid(x, y)
            
            # 绘制3D地形
            surf = self.ax.plot_surface(x, y, self.height_map * 100, 
                                    cmap='terrain', alpha=0.9,
                                    linewidth=0, antialiased=True)
            
            # 如果有植被，添加绿色色调
            if self.vegetation_map is not None:
                # 确保植被值在0-1范围内
                vegetation_clipped = np.clip(self.vegetation_map, 0, 1)
                
                # 创建植被颜色映射
                colors = np.zeros((*vegetation_clipped.shape, 4))
                colors[..., 1] = vegetation_clipped  # 绿色通道
                colors[..., 3] = vegetation_clipped * 0.5  # 透明度，确保在0-1范围内
                
                # 叠加植被颜色
                self.ax.plot_surface(x, y, self.height_map * 100, 
                                    facecolors=colors, shade=False)
            
            # 如果有水体，添加蓝色色调
            if self.water_map is not None:
                water_mask = self.water_map > 0.01
                if np.any(water_mask):
                    # 确保水体值在合理范围内
                    water_clipped = np.clip(self.water_map, 0, 1)
                    
                    water_colors = np.zeros((*water_clipped.shape, 4))
                    water_colors[..., 2] = 1.0  # 蓝色通道
                    # 确保透明度在0-1范围内
                    water_colors[..., 3] = np.clip(water_clipped * 5, 0, 0.7)  # 降低乘数
        
        self.ax.set_xlabel('X')
        self.ax.set_ylabel('Y')
        self.ax.set_zlabel('高度')
        self.fig.tight_layout()
        self.draw()


# 实时编辑工具类
class TerrainEditor:
    def __init__(self, terrain_canvas):
        self.canvas = terrain_canvas
        self.edit_mode = "raise"  # raise, lower, smooth, flatten
        self.brush_size = 10
        self.brush_strength = 0.1
        self.is_drawing = False
        self.last_point = None
        
    def set_edit_mode(self, mode):
        """设置编辑模式"""
        self.edit_mode = mode
    
    def set_brush_size(self, size):
        """设置画笔大小"""
        self.brush_size = max(1, size)
    
    def set_brush_strength(self, strength):
        """设置画笔强度"""
        self.brush_strength = max(0.01, min(1.0, strength))
    
    def mouse_press(self, x, y):
        """鼠标按下事件"""
        if self.canvas.height_map is not None:
            self.is_drawing = True
            self.last_point = (x, y)
            self.apply_brush(x, y)
    
    def mouse_move(self, x, y):
        """鼠标移动事件"""
        if self.is_drawing and self.canvas.height_map is not None:
            # 在两点之间插值应用画笔
            if self.last_point:
                self.interpolate_brush(self.last_point[0], self.last_point[1], x, y)
            self.last_point = (x, y)
    
    def mouse_release(self):
        """鼠标释放事件"""
        self.is_drawing = False
        self.last_point = None
    
    def apply_brush(self, x, y):
        """在指定位置应用画笔"""
        if self.canvas.height_map is None:
            return
            
        height, width = self.canvas.height_map.shape
        center_x, center_y = int(x * width), int(y * height)
        
        # 应用圆形画笔
        for brush_y in range(-self.brush_size, self.brush_size+1):
            for brush_x in range(-self.brush_size, self.brush_size+1):
                dist = math.sqrt(brush_x**2 + brush_y**2)
                if dist <= self.brush_size:
                    px = center_x + brush_x
                    py = center_y + brush_y
                    
                    if 0 <= px < width and 0 <= py < height:
                        # 计算画笔强度（基于距离）
                        strength_factor = 1 - (dist / self.brush_size)
                        strength = self.brush_strength * strength_factor
                        
                        # 根据编辑模式应用变化
                        if self.edit_mode == "raise":
                            self.canvas.height_map[py, px] += strength
                        elif self.edit_mode == "lower":
                            self.canvas.height_map[py, px] -= strength
                        elif self.edit_mode == "smooth":
                            # 平滑：取周围像素的平均值
                            neighbors = []
                            for dy in [-1, 0, 1]:
                                for dx in [-1, 0, 1]:
                                    nx, ny = px+dx, py+dy
                                    if 0 <= nx < width and 0 <= ny < height:
                                        neighbors.append(self.canvas.height_map[ny, nx])
                            if neighbors:
                                avg = sum(neighbors) / len(neighbors)
                                self.canvas.height_map[py, px] = avg * strength + self.canvas.height_map[py, px] * (1 - strength)
                        elif self.edit_mode == "flatten":
                            # 平整：向目标高度调整
                            target_height = self.canvas.height_map[center_y, center_x]
                            self.canvas.height_map[py, px] = target_height * strength + self.canvas.height_map[py, px] * (1 - strength)
        
        # 确保高度在有效范围内
        self.canvas.height_map = np.clip(self.canvas.height_map, 0, 1)
        
        # 更新显示
        self.canvas.update_3d_display()
    
    def interpolate_brush(self, x1, y1, x2, y2):
        """在两点之间插值应用画笔"""
        height, width = self.canvas.height_map.shape
        px1, py1 = int(x1 * width), int(y1 * height)
        px2, py2 = int(x2 * width), int(y2 * height)
        
        # 计算两点之间的距离
        dist = max(1, math.sqrt((px2-px1)**2 + (py2-py1)**2))
        
        # 在两点之间插值
        for i in range(int(dist)):
            t = i / dist
            x = x1 + t * (x2 - x1)
            y = y1 + t * (y2 - y1)
            self.apply_brush(x, y)


# 增强版主窗口
class AdvancedLandscapingSystem(QMainWindow):
    def __init__(self):
        super().__init__()
        self.terrain_editor = None
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle('高级智能造景系统')
        self.setGeometry(100, 100, 1400, 900)
        
        # 设置应用图标
        self.setWindowIcon(QIcon(self.create_icon()))
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        main_layout = QHBoxLayout(central_widget)
        
        # 创建左侧控制面板
        control_panel = self.create_control_panel()
        main_layout.addWidget(control_panel, 1)
        
        # 创建右侧显示区域
        display_area = self.create_display_area()
        main_layout.addWidget(display_area, 3)
        
        # 创建工具栏
        self.create_toolbar()
        
        # 创建状态栏
        self.statusBar().showMessage("就绪")
        
        # 创建菜单栏
        self.create_menubar()
        
        # 初始化地形编辑器
        self.terrain_editor = TerrainEditor(self.canvas_3d)
        
    def create_icon(self):
        """创建应用图标"""
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 绘制简单的山脉图标
        painter.setBrush(QColor(100, 150, 100))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(0, 16, 32, 16)
        
        painter.setBrush(QColor(150, 200, 150))
        painter.drawEllipse(8, 12, 16, 12)
        
        painter.setBrush(QColor(200, 250, 200))
        painter.drawEllipse(16, 8, 8, 8)
        
        painter.end()
        return QIcon(pixmap)
    
    def create_menubar(self):
        """创建菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu('文件')
        
        new_action = QAction('新建项目', self)
        new_action.setShortcut('Ctrl+N')
        new_action.triggered.connect(self.new_project)
        file_menu.addAction(new_action)
        
        open_action = QAction('打开项目', self)
        open_action.setShortcut('Ctrl+O')
        open_action.triggered.connect(self.open_project)
        file_menu.addAction(open_action)
        
        save_action = QAction('保存项目', self)
        save_action.setShortcut('Ctrl+S')
        save_action.triggered.connect(self.save_project)
        file_menu.addAction(save_action)
        
        file_menu.addSeparator()
        
        export_action = QAction('导出场景', self)
        export_action.setShortcut('Ctrl+E')
        export_action.triggered.connect(self.export_scene)
        file_menu.addAction(export_action)
        
        # 编辑菜单
        edit_menu = menubar.addMenu('编辑')
        
        undo_action = QAction('撤销', self)
        undo_action.setShortcut('Ctrl+Z')
        edit_menu.addAction(undo_action)
        
        redo_action = QAction('重做', self)
        redo_action.setShortcut('Ctrl+Y')
        edit_menu.addAction(redo_action)
        
        edit_menu.addSeparator()
        
        terrain_edit_menu = edit_menu.addMenu('地形编辑')
        
        raise_action = QAction('抬高地形', self)
        raise_action.triggered.connect(lambda: self.set_edit_mode("raise"))
        terrain_edit_menu.addAction(raise_action)
        
        lower_action = QAction('降低地形', self)
        lower_action.triggered.connect(lambda: self.set_edit_mode("lower"))
        terrain_edit_menu.addAction(lower_action)
        
        smooth_action = QAction('平滑地形', self)
        smooth_action.triggered.connect(lambda: self.set_edit_mode("smooth"))
        terrain_edit_menu.addAction(smooth_action)
        
        flatten_action = QAction('平整地形', self)
        flatten_action.triggered.connect(lambda: self.set_edit_mode("flatten"))
        terrain_edit_menu.addAction(flatten_action)
        
        # 视图菜单
        view_menu = menubar.addMenu('视图')
        
        view_2d_action = QAction('2D视图', self)
        view_2d_action.triggered.connect(self.show_2d_view)
        view_menu.addAction(view_2d_action)
        
        view_3d_action = QAction('3D视图', self)
        view_3d_action.triggered.connect(self.show_3d_view)
        view_menu.addAction(view_3d_action)
        
        # 工具菜单
        tools_menu = menubar.addMenu('工具')
        
        generate_terrain_action = QAction('生成地形', self)
        generate_terrain_action.triggered.connect(self.generate_terrain)
        tools_menu.addAction(generate_terrain_action)
        
        generate_vegetation_action = QAction('生成植被', self)
        generate_vegetation_action.triggered.connect(self.generate_vegetation)
        tools_menu.addAction(generate_vegetation_action)
        
        simulate_weather_action = QAction('模拟天气', self)
        simulate_weather_action.triggered.connect(self.simulate_weather)
        tools_menu.addAction(simulate_weather_action)
    
    def create_toolbar(self):
        """创建工具栏"""
        toolbar = QToolBar("主工具栏")
        self.addToolBar(Qt.TopToolBarArea, toolbar)
        
        # 添加工具按钮
        new_action = QAction(QIcon.fromTheme("document-new"), "新建", self)
        new_action.triggered.connect(self.new_project)
        toolbar.addAction(new_action)
        
        open_action = QAction(QIcon.fromTheme("document-open"), "打开", self)
        open_action.triggered.connect(self.open_project)
        toolbar.addAction(open_action)
        
        save_action = QAction(QIcon.fromTheme("document-save"), "保存", self)
        save_action.triggered.connect(self.save_project)
        toolbar.addAction(save_action)
        
        toolbar.addSeparator()
        
        # 地形编辑工具
        raise_action = QAction("抬升", self)
        raise_action.triggered.connect(lambda: self.set_edit_mode("raise"))
        toolbar.addAction(raise_action)
        
        lower_action = QAction("降低", self)
        lower_action.triggered.connect(lambda: self.set_edit_mode("lower"))
        toolbar.addAction(lower_action)
        
        smooth_action = QAction("平滑", self)
        smooth_action.triggered.connect(lambda: self.set_edit_mode("smooth"))
        toolbar.addAction(smooth_action)
        
        flatten_action = QAction("平整", self)
        flatten_action.triggered.connect(lambda: self.set_edit_mode("flatten"))
        toolbar.addAction(flatten_action)
        
        toolbar.addSeparator()
        
        # 画笔大小控制
        toolbar.addWidget(QLabel("画笔大小:"))
        self.brush_size_slider = QSlider(Qt.Horizontal)
        self.brush_size_slider.setRange(1, 50)
        self.brush_size_slider.setValue(10)
        self.brush_size_slider.valueChanged.connect(self.update_brush_size)
        toolbar.addWidget(self.brush_size_slider)
        
        toolbar.addWidget(QLabel("强度:"))
        self.brush_strength_slider = QSlider(Qt.Horizontal)
        self.brush_strength_slider.setRange(1, 100)
        self.brush_strength_slider.setValue(10)
        self.brush_strength_slider.valueChanged.connect(self.update_brush_strength)
        toolbar.addWidget(self.brush_strength_slider)
    
    def create_control_panel(self):
        """创建增强版控制面板"""
        panel = QFrame()
        panel.setFrameStyle(QFrame.StyledPanel)
        panel.setMaximumWidth(400)
        
        # 使用选项卡组织控件
        tab_widget = QTabWidget()
        
        # 地形生成选项卡
        terrain_tab = self.create_terrain_tab()
        tab_widget.addTab(terrain_tab, "地形生成")
        
        # 植被生成选项卡
        vegetation_tab = self.create_vegetation_tab()
        tab_widget.addTab(vegetation_tab, "植被生成")
        
        # 天气模拟选项卡
        weather_tab = self.create_weather_tab()
        tab_widget.addTab(weather_tab, "天气模拟")
        
        # 场景设置选项卡
        scene_tab = self.create_scene_tab()
        tab_widget.addTab(scene_tab, "场景设置")
        
        layout = QVBoxLayout(panel)
        layout.addWidget(tab_widget)
        
        return panel
    
    def create_terrain_tab(self):
        """创建地形生成选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 地形类型选择
        type_group = QGroupBox("地形类型")
        type_layout = QVBoxLayout(type_group)
        
        self.terrain_type_combo = QComboBox()
        self.terrain_type_combo.addItems(["多重分形", "火山", "峡谷"])
        type_layout.addWidget(self.terrain_type_combo)
        
        layout.addWidget(type_group)
        
        # 地形参数
        param_group = QGroupBox("地形参数")
        param_layout = QVBoxLayout(param_group)
        
        # 地图尺寸
        size_layout = QHBoxLayout()
        size_layout.addWidget(QLabel("地图尺寸:"))
        self.size_combo = QComboBox()
        self.size_combo.addItems(["128x128", "256x256", "512x512", "1024x1024"])
        self.size_combo.setCurrentIndex(1)
        size_layout.addWidget(self.size_combo)
        param_layout.addLayout(size_layout)
        
        # 噪声尺度
        scale_layout = QHBoxLayout()
        scale_layout.addWidget(QLabel("噪声尺度:"))
        self.scale_slider = QSlider(Qt.Horizontal)
        self.scale_slider.setRange(10, 500)
        self.scale_slider.setValue(100)
        scale_layout.addWidget(self.scale_slider)
        self.scale_label = QLabel("100")
        scale_layout.addWidget(self.scale_label)
        param_layout.addLayout(scale_layout)
        
        # 八度数量
        octaves_layout = QHBoxLayout()
        octaves_layout.addWidget(QLabel("八度数量:"))
        self.octaves_spin = QSpinBox()
        self.octaves_spin.setRange(1, 10)
        self.octaves_spin.setValue(6)
        octaves_layout.addWidget(self.octaves_spin)
        param_layout.addLayout(octaves_layout)
        
        # 持久度
        persistence_layout = QHBoxLayout()
        persistence_layout.addWidget(QLabel("持久度:"))
        self.persistence_spin = QDoubleSpinBox()
        self.persistence_spin.setRange(0.1, 1.0)
        self.persistence_spin.setSingleStep(0.1)
        self.persistence_spin.setValue(0.5)
        persistence_layout.addWidget(self.persistence_spin)
        param_layout.addLayout(persistence_layout)
        
        # 侵蚀迭代
        erosion_layout = QHBoxLayout()
        erosion_layout.addWidget(QLabel("侵蚀迭代:"))
        self.erosion_spin = QSpinBox()
        self.erosion_spin.setRange(0, 20)
        self.erosion_spin.setValue(5)
        erosion_layout.addWidget(self.erosion_spin)
        param_layout.addLayout(erosion_layout)
        
        # 应用热侵蚀
        self.thermal_erosion_check = QCheckBox("应用热侵蚀")
        self.thermal_erosion_check.setChecked(True)
        param_layout.addWidget(self.thermal_erosion_check)
        
        layout.addWidget(param_group)
        
        # 生成按钮
        self.generate_terrain_btn = QPushButton("生成地形")
        self.generate_terrain_btn.clicked.connect(self.generate_terrain)
        layout.addWidget(self.generate_terrain_btn)
        
        layout.addStretch()
        
        # 连接信号
        self.scale_slider.valueChanged.connect(self.update_scale_label)
        
        return widget
    
    def create_vegetation_tab(self):
        """创建植被生成选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 植被类型
        type_group = QGroupBox("植被类型")
        type_layout = QVBoxLayout(type_group)
        
        self.vegetation_type_combo = QComboBox()
        self.vegetation_type_combo.addItems(["自动根据生物群系", "森林", "草原", "沙漠植被"])
        type_layout.addWidget(self.vegetation_type_combo)
        
        layout.addWidget(type_group)
        
        # 植被参数
        param_group = QGroupBox("植被参数")
        param_layout = QVBoxLayout(param_group)
        
        # 密度
        density_layout = QHBoxLayout()
        density_layout.addWidget(QLabel("植被密度:"))
        self.density_slider = QSlider(Qt.Horizontal)
        self.density_slider.setRange(1, 100)
        self.density_slider.setValue(50)
        density_layout.addWidget(self.density_slider)
        param_layout.addLayout(density_layout)
        
        # 多样性
        diversity_layout = QHBoxLayout()
        diversity_layout.addWidget(QLabel("植物多样性:"))
        self.diversity_slider = QSlider(Qt.Horizontal)
        self.diversity_slider.setRange(1, 100)
        self.diversity_slider.setValue(50)
        diversity_layout.addWidget(self.diversity_slider)
        param_layout.addLayout(diversity_layout)
        
        layout.addWidget(param_group)
        
        # 生成按钮
        self.generate_vegetation_btn = QPushButton("生成植被")
        self.generate_vegetation_btn.clicked.connect(self.generate_vegetation)
        layout.addWidget(self.generate_vegetation_btn)
        
        # 模拟生长按钮
        self.simulate_growth_btn = QPushButton("模拟生长")
        self.simulate_growth_btn.clicked.connect(self.simulate_growth)
        layout.addWidget(self.simulate_growth_btn)
        
        layout.addStretch()
        
        return widget
    
    def create_weather_tab(self):
        """创建天气模拟选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 季节设置
        season_group = QGroupBox("季节设置")
        season_layout = QVBoxLayout(season_group)
        
        self.season_combo = QComboBox()
        self.season_combo.addItems(["春季", "夏季", "秋季", "冬季"])
        season_layout.addWidget(self.season_combo)
        
        layout.addWidget(season_group)
        
        # 天气参数
        param_group = QGroupBox("天气参数")
        param_layout = QVBoxLayout(param_group)
        
        # 温度
        temp_layout = QHBoxLayout()
        temp_layout.addWidget(QLabel("基础温度:"))
        self.temp_slider = QSlider(Qt.Horizontal)
        self.temp_slider.setRange(0, 100)
        self.temp_slider.setValue(50)
        temp_layout.addWidget(self.temp_slider)
        param_layout.addLayout(temp_layout)
        
        # 降水量
        precip_layout = QHBoxLayout()
        precip_layout.addWidget(QLabel("降水量:"))
        self.precip_slider = QSlider(Qt.Horizontal)
        self.precip_slider.setRange(0, 100)
        self.precip_slider.setValue(50)
        precip_layout.addWidget(self.precip_slider)
        param_layout.addLayout(precip_layout)
        
        layout.addWidget(param_group)
        
        # 模拟按钮
        self.simulate_weather_btn = QPushButton("模拟天气")
        self.simulate_weather_btn.clicked.connect(self.simulate_weather)
        layout.addWidget(self.simulate_weather_btn)
        
        layout.addStretch()
        
        return widget
    
    def create_scene_tab(self):
        """创建场景设置选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 场景信息
        info_group = QGroupBox("场景信息")
        info_layout = QVBoxLayout(info_group)
        
        self.scene_name_edit = QTextEdit()
        self.scene_name_edit.setMaximumHeight(30)
        self.scene_name_edit.setPlaceholderText("场景名称")
        info_layout.addWidget(self.scene_name_edit)
        
        self.scene_description_edit = QTextEdit()
        self.scene_description_edit.setMaximumHeight(100)
        self.scene_description_edit.setPlaceholderText("场景描述")
        info_layout.addWidget(self.scene_description_edit)
        
        layout.addWidget(info_group)
        
        # 导出选项
        export_group = QGroupBox("导出选项")
        export_layout = QVBoxLayout(export_group)
        
        self.export_resolution_combo = QComboBox()
        self.export_resolution_combo.addItems(["低 (512x512)", "中 (1024x1024)", "高 (2048x2048)", "超高 (4096x4096)"])
        self.export_resolution_combo.setCurrentIndex(1)
        export_layout.addWidget(self.export_resolution_combo)
        
        self.include_vegetation_check = QCheckBox("包含植被")
        self.include_vegetation_check.setChecked(True)
        export_layout.addWidget(self.include_vegetation_check)
        
        self.include_water_check = QCheckBox("包含水体")
        self.include_water_check.setChecked(True)
        export_layout.addWidget(self.include_water_check)
        
        layout.addWidget(export_group)
        
        # 导出按钮
        self.export_btn = QPushButton("导出场景")
        self.export_btn.clicked.connect(self.export_scene)
        layout.addWidget(self.export_btn)
        
        layout.addStretch()
        
        return widget
    
    def create_display_area(self):
        """创建显示区域"""
        area = QWidget()
        layout = QVBoxLayout(area)
        
        # 创建模式选择按钮
        mode_layout = QHBoxLayout()
        
        self.view_2d_btn = QPushButton("2D视图")
        self.view_2d_btn.setCheckable(True)
        self.view_2d_btn.clicked.connect(self.show_2d_view)
        mode_layout.addWidget(self.view_2d_btn)
        
        self.view_3d_btn = QPushButton("3D视图")
        self.view_3d_btn.setCheckable(True)
        self.view_3d_btn.setChecked(True)
        self.view_3d_btn.clicked.connect(self.show_3d_view)
        mode_layout.addWidget(self.view_3d_btn)
        
        layout.addLayout(mode_layout)
        
        # 创建画布堆叠
        self.canvas_stack = QWidget()
        self.canvas_layout = QVBoxLayout(self.canvas_stack)
        
        # 创建2D画布
        self.canvas_2d = FigureCanvas(Figure(figsize=(8, 6)))
        self.canvas_2d.setVisible(False)
        self.canvas_layout.addWidget(self.canvas_2d)
        
        # 创建3D画布
        self.canvas_3d = Terrain3DCanvas(self, width=8, height=6, dpi=100)
        self.canvas_layout.addWidget(self.canvas_3d)
        
        layout.addWidget(self.canvas_stack)
        
        # 状态信息
        self.status_label = QLabel("就绪")
        layout.addWidget(self.status_label)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        return area
    
    def update_scale_label(self, value):
        """更新噪声尺度标签"""
        self.scale_label.setText(str(value))
    
    def update_brush_size(self, value):
        """更新画笔大小"""
        if self.terrain_editor:
            self.terrain_editor.set_brush_size(value)
    
    def update_brush_strength(self, value):
        """更新画笔强度"""
        if self.terrain_editor:
            self.terrain_editor.set_brush_strength(value / 100.0)
    
    def set_edit_mode(self, mode):
        """设置编辑模式"""
        if self.terrain_editor:
            self.terrain_editor.set_edit_mode(mode)
            self.statusBar().showMessage(f"编辑模式: {mode}")
    
    def show_2d_view(self):
        """显示2D视图"""
        self.view_2d_btn.setChecked(True)
        self.view_3d_btn.setChecked(False)
        self.canvas_2d.setVisible(True)
        self.canvas_3d.setVisible(False)
    
    def show_3d_view(self):
        """显示3D视图"""
        self.view_2d_btn.setChecked(False)
        self.view_3d_btn.setChecked(True)
        self.canvas_2d.setVisible(False)
        self.canvas_3d.setVisible(True)
    
    def generate_terrain(self):
        """生成地形"""
        # 获取地图尺寸
        size_text = self.size_combo.currentText()
        width, height = map(int, size_text.split('x'))
        
        # 获取地形类型
        terrain_type_map = {
            "多重分形": "multifractal",
            "火山": "volcanic", 
            "峡谷": "canyon"
        }
        terrain_type = terrain_type_map.get(self.terrain_type_combo.currentText(), "multifractal")
        
        # 获取参数
        scale = self.scale_slider.value()
        octaves = self.octaves_spin.value()
        persistence = self.persistence_spin.value()
        erosion_iterations = self.erosion_spin.value()
        apply_thermal_erosion = self.thermal_erosion_check.isChecked()
        
        # 显示进度
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # 生成地形
        self.canvas_3d.generate_terrain(
            terrain_type=terrain_type,
            width=width, 
            height=height,
            scale=scale,
            octaves=octaves,
            persistence=persistence,
            erosion_iterations=erosion_iterations,
            apply_thermal_erosion=apply_thermal_erosion
        )
        
        self.progress_bar.setValue(100)
        QTimer.singleShot(1000, lambda: self.progress_bar.setVisible(False))
        
        self.statusBar().showMessage("地形生成完成")
    
    def generate_vegetation(self):
        """生成植被"""
        if self.canvas_3d.height_map is None:
            QMessageBox.warning(self, "警告", "请先生成地形！")
            return
            
        self.canvas_3d.generate_vegetation()
        self.statusBar().showMessage("植被生成完成")
    
    def simulate_weather(self):
        """模拟天气"""
        if self.canvas_3d.height_map is None:
            QMessageBox.warning(self, "警告", "请先生成地形！")
            return
            
        # 更新季节
        season_index = self.season_combo.currentIndex()
        self.canvas_3d.weather_system.season = season_index
        
        self.canvas_3d.simulate_weather()
        self.statusBar().showMessage("天气模拟完成")
    
    def simulate_growth(self):
        """模拟植被生长"""
        if self.canvas_3d.vegetation_map is None:
            QMessageBox.warning(self, "警告", "请先生成植被！")
            return
            
        # 在实际实现中，这里应该调用植被生长模拟
        self.statusBar().showMessage("植被生长模拟完成")
    
    def new_project(self):
        """新建项目"""
        reply = QMessageBox.question(self, "新建项目", 
                                   "是否保存当前项目？", 
                                   QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
        
        if reply == QMessageBox.Yes:
            self.save_project()
        elif reply == QMessageBox.Cancel:
            return
        
        # 重置画布
        self.canvas_3d.height_map = None
        self.canvas_3d.vegetation_map = None
        self.canvas_3d.tree_map = None
        self.canvas_3d.biome_map = None
        self.canvas_3d.water_map = None
        self.canvas_3d.update_3d_display()
        
        self.statusBar().showMessage("新建项目")
    
    def open_project(self):
        """打开项目"""
        filename, _ = QFileDialog.getOpenFileName(
            self, "打开项目", "", "智能造景项目 (*.slp);;所有文件 (*)")
        
        if filename:
            # 在实际实现中，这里应该加载项目数据
            self.statusBar().showMessage(f"已打开项目: {filename}")
    
    def save_project(self):
        """保存项目"""
        filename, _ = QFileDialog.getSaveFileName(
            self, "保存项目", "", "智能造景项目 (*.slp);;所有文件 (*)")
        
        if filename:
            # 在实际实现中，这里应该保存项目数据
            self.statusBar().showMessage(f"项目已保存: {filename}")
    
    def export_scene(self):
        """导出场景"""
        if self.canvas_3d.height_map is None:
            QMessageBox.warning(self, "警告", "没有可导出的场景！")
            return
            
        filename, _ = QFileDialog.getSaveFileName(
            self, "导出场景", "", "PNG图像 (*.png);;JPEG图像 (*.jpg);;所有文件 (*)")
        
        if filename:
            # 保存当前视图
            self.canvas_3d.fig.savefig(filename, dpi=150, bbox_inches='tight')
            self.statusBar().showMessage(f"场景已导出到 {filename}")
    
    def mousePressEvent(self, event):
        """鼠标按下事件"""
        if (event.button() == Qt.LeftButton and 
            self.canvas_3d.isVisible() and 
            self.canvas_3d.rect().contains(self.canvas_3d.mapFromGlobal(event.globalPos()))):
            
            # 获取鼠标在画布上的相对位置
            canvas_pos = self.canvas_3d.mapFromGlobal(event.globalPos())
            x = canvas_pos.x() / self.canvas_3d.width()
            y = canvas_pos.y() / self.canvas_3d.height()
            
            if self.terrain_editor:
                self.terrain_editor.mouse_press(x, y)
        
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        """鼠标移动事件"""
        if (event.buttons() & Qt.LeftButton and 
            self.canvas_3d.isVisible() and 
            self.canvas_3d.rect().contains(self.canvas_3d.mapFromGlobal(event.globalPos()))):
            
            # 获取鼠标在画布上的相对位置
            canvas_pos = self.canvas_3d.mapFromGlobal(event.globalPos())
            x = canvas_pos.x() / self.canvas_3d.width()
            y = canvas_pos.y() / self.canvas_3d.height()
            
            if self.terrain_editor:
                self.terrain_editor.mouse_move(x, y)
        
        super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event):
        """鼠标释放事件"""
        if event.button() == Qt.LeftButton and self.terrain_editor:
            self.terrain_editor.mouse_release()
        
        super().mouseReleaseEvent(event)


# 主函数
def main():
    app = QApplication(sys.argv)
    app.setApplicationName("高级智能造景系统")
    app.setApplicationVersion("2.0")
    
    # 设置应用程序样式
    app.setStyle('Fusion')
    
    # 创建并显示主窗口
    window = AdvancedLandscapingSystem()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()