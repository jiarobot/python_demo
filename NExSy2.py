import sys
import numpy as np
import matplotlib
matplotlib.use('Qt5Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.animation import FuncAnimation
from mpl_toolkits.mplot3d import Axes3D
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from scipy.ndimage import gaussian_filter
import torch
import torch.nn as nn
from collections import deque
import time

from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                             QWidget, QPushButton, QLabel, QSlider, QComboBox, 
                             QSpinBox, QDoubleSpinBox, QCheckBox, QGroupBox,
                             QTabWidget, QTextEdit, QProgressBar, QSplitter,
                             QFileDialog, QMessageBox, QGridLayout, QFrame)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QPalette, QColor

class EnhancedNeuralRadianceField(nn.Module):
    """
    增强版NeRF模型，支持多尺度特征提取和动态更新
    """
    def __init__(self, hidden_dim=128, num_layers=8):
        super().__init__()
        
        self.position_encoding = PositionalEncoding(L=10)
        self.direction_encoding = PositionalEncoding(L=4)
        
        # 主网络处理位置信息
        self.backbone_layers = nn.ModuleList()
        input_dim = 3 * 2 * 10  # 位置编码后的维度
        
        for i in range(num_layers):
            self.backbone_layers.append(nn.Linear(input_dim if i == 0 else hidden_dim, hidden_dim))
            self.backbone_layers.append(nn.ReLU())
        
        # 输出头
        self.density_head = nn.Linear(hidden_dim, 1)
        self.color_head = nn.Sequential(
            nn.Linear(hidden_dim + 3 * 2 * 4, hidden_dim // 2),
            nn.ReLU(),
            nn.Linear(hidden_dim // 2, 3)
        )
        self.semantic_head = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Linear(hidden_dim // 2, 5)  # 5个语义类别
        )
        
    def forward(self, positions, directions=None):
        # 位置编码
        encoded_pos = self.position_encoding(positions)
        
        # 通过主干网络
        x = encoded_pos
        for layer in self.backbone_layers:
            x = layer(x)
        
        # 密度输出
        density = torch.sigmoid(self.density_head(x))
        
        # 颜色输出（如果提供方向）
        if directions is not None:
            encoded_dir = self.direction_encoding(directions)
            color_input = torch.cat([x, encoded_dir], dim=-1)
            color = torch.sigmoid(self.color_head(color_input))
        else:
            color = torch.zeros(positions.shape[0], 3)
        
        # 语义输出
        semantics = torch.softmax(self.semantic_head(x), dim=-1)
        
        return density, color, semantics

class PositionalEncoding(nn.Module):
    """位置编码模块"""
    def __init__(self, L=10):
        super().__init__()
        self.L = L
        
    def forward(self, x):
        encoded = [x]
        for i in range(self.L):
            encoded.append(torch.sin(2 ** i * np.pi * x))
            encoded.append(torch.cos(2 ** i * np.pi * x))
        return torch.cat(encoded, dim=-1)

class EnhancedEnvironmentSimulator:
    """增强版环境模拟器"""
    
    def __init__(self, size=(200, 200, 50)):
        self.size = size
        self.obstacles = []
        self.dynamic_obstacles = []
        self.semantic_regions = {}
        self.weather_conditions = {'fog': 0.0, 'wind': (0, 0), 'rain': 0.0}
        self.time_of_day = 12.0  # 12:00 noon
        self.initialize_environment()
        
    def initialize_environment(self):
        """初始化复杂环境"""
        
        # 静态障碍物
        self.obstacles.extend([
            {'type': 'skyscraper', 'pos': (50, 50, 0), 'size': (20, 20, 40), 'material': 'concrete'},
            {'type': 'building', 'pos': (120, 80, 0), 'size': (25, 18, 25), 'material': 'brick'},
            {'type': 'building', 'pos': (30, 130, 0), 'size': (15, 15, 20), 'material': 'glass'},
            {'type': 'tree_cluster', 'pos': (80, 40, 0), 'size': (12, 12, 15), 'material': 'foliage'},
            {'type': 'tree_cluster', 'pos': (150, 30, 0), 'size': (10, 10, 12), 'material': 'foliage'},
            {'type': 'bridge', 'pos': (100, 100, 10), 'size': (40, 8, 5), 'material': 'steel'},
            {'type': 'power_line', 'pos': (60, 160, 15), 'size': (30, 2, 1), 'material': 'metal'},
        ])
        
        # 动态障碍物
        self.dynamic_obstacles.extend([
            {'type': 'car', 'pos': (70, 70, 0), 'size': (4, 2, 1.5), 'velocity': (3, 0, 0), 'route': 'horizontal'},
            {'type': 'truck', 'pos': (130, 120, 0), 'size': (6, 3, 2.5), 'velocity': (0, 2, 0), 'route': 'vertical'},
            {'type': 'drone', 'pos': (90, 90, 20), 'size': (2, 2, 1), 'velocity': (1, 1, 0.5), 'route': 'random'},
            {'type': 'bird_flock', 'pos': (40, 100, 25), 'size': (8, 8, 5), 'velocity': (2, -1, 0), 'route': 'flocking'},
        ])
        
        # 语义区域
        self.semantic_regions = {
            'construction_site': {'area': [(20, 20), (40, 40)], 'risk_level': 0.95, 'semantic_class': 4},
            'residential_area': {'area': [(140, 140), (180, 180)], 'risk_level': 0.3, 'semantic_class': 1},
            'commercial_zone': {'area': [(50, 120), (90, 160)], 'risk_level': 0.6, 'semantic_class': 2},
            'park': {'area': [(100, 30), (140, 70)], 'risk_level': 0.1, 'semantic_class': 3},
            'landing_zone': {'area': [(160, 160), (190, 190)], 'risk_level': 0.0, 'semantic_class': 0},
            'no_fly_zone': {'area': [(10, 80), (30, 100)], 'risk_level': 1.0, 'semantic_class': 4},
        }
        
    def update_dynamic_obstacles(self):
        """更新动态障碍物位置和状态"""
        for obstacle in self.dynamic_obstacles:
            vx, vy, vz = obstacle['velocity']
            x, y, z = obstacle['pos']
            route_type = obstacle['route']
            
            # 根据路线类型更新位置
            if route_type == 'horizontal':
                new_x, new_y = x + vx, y
                if new_x < 20 or new_x > self.size[0] - 20:
                    obstacle['velocity'] = (-vx, vy, vz)
            elif route_type == 'vertical':
                new_x, new_y = x, y + vy
                if new_y < 20 or new_y > self.size[1] - 20:
                    obstacle['velocity'] = (vx, -vy, vz)
            elif route_type == 'random':
                new_x, new_y = x + vx + np.random.uniform(-0.5, 0.5), y + vy + np.random.uniform(-0.5, 0.5)
                # 随机改变方向
                if np.random.random() < 0.05:
                    obstacle['velocity'] = (np.random.uniform(-3, 3), np.random.uniform(-3, 3), vz)
            elif route_type == 'flocking':
                new_x, new_y = x + vx, y + vy
                # 简单的群体行为
                if new_x < 10 or new_x > self.size[0] - 10:
                    obstacle['velocity'] = (-vx, vy, vz)
                if new_y < 10 or new_y > self.size[1] - 10:
                    obstacle['velocity'] = (vx, -vy, vz)
            
            obstacle['pos'] = (new_x, new_y, z)
    
    def set_weather_conditions(self, fog_density=0.0, wind_speed=0.0, wind_direction=0.0, rain_intensity=0.0):
        """设置天气条件"""
        self.weather_conditions = {
            'fog': fog_density,
            'wind': (wind_speed * np.cos(wind_direction), wind_speed * np.sin(wind_direction)),
            'rain': rain_intensity
        }
    
    def set_time_of_day(self, hour):
        """设置时间（影响光照条件）"""
        self.time_of_day = hour % 24
    
    def get_illumination_level(self, x, y, z):
        """根据位置和时间计算光照水平"""
        # 简化的光照模型
        base_light = 0.7 + 0.3 * np.sin(2 * np.pi * (self.time_of_day - 6) / 24)
        
        # 阴影效果（靠近建筑物时变暗）
        shadow_factor = 1.0
        for obstacle in self.obstacles:
            ox, oy, oz = obstacle['pos']
            sx, sy, sz = obstacle['size']
            if (abs(x - ox) < sx and abs(y - oy) < sy and z < oz + sz):
                shadow_factor *= 0.3
        
        # 天气影响
        weather_factor = 1.0 - 0.5 * self.weather_conditions['fog'] - 0.3 * self.weather_conditions['rain']
        
        return base_light * shadow_factor * weather_factor
    
    def get_semantic_cost(self, x, y, z):
        """获取位置的语义成本，考虑高度因素"""
        base_cost = 0.3  # 默认成本
        
        for region_name, region_data in self.semantic_regions.items():
            (x1, y1), (x2, y2) = region_data['area']
            if x1 <= x <= x2 and y1 <= y <= y2:
                base_cost = region_data['risk_level']
                break
        
        # 高度惩罚（太低或太高都有风险）
        height_penalty = 0.0
        if z < 5:  # 太低
            height_penalty = 0.4 * (5 - z) / 5
        elif z > 35:  # 太高（超出安全范围）
            height_penalty = 0.3 * (z - 35) / 15
        
        return min(1.0, base_cost + height_penalty)
    
    def is_collision(self, x, y, z, safety_margin=2):
        """检查是否与障碍物碰撞，考虑动态障碍物预测"""
        # 检查静态障碍物
        for obstacle in self.obstacles:
            ox, oy, oz = obstacle['pos']
            sx, sy, sz = obstacle['size']
            
            if (abs(x - ox) < sx/2 + safety_margin and 
                abs(y - oy) < sy/2 + safety_margin and 
                abs(z - oz) < sz/2 + safety_margin):
                return True
        
        # 检查动态障碍物，考虑速度和预测
        current_time = time.time()
        for obstacle in self.dynamic_obstacles:
            ox, oy, oz = obstacle['pos']
            sx, sy, sz = obstacle['size']
            vx, vy, vz = obstacle['velocity']
            
            # 预测位置（简单线性预测）
            pred_x, pred_y, pred_z = ox + vx, oy + vy, oz + vz
            
            if (abs(x - pred_x) < sx/2 + safety_margin + 2 and  # 额外2米的预测缓冲
                abs(y - pred_y) < sy/2 + safety_margin + 2 and 
                abs(z - pred_z) < sz/2 + safety_margin):
                return True
        
        return False

class EnhancedNeRFDroneNavigation:
    """增强版NeRF无人机导航系统"""
    
    def __init__(self, environment):
        self.env = environment
        self.nerf_model = EnhancedNeuralRadianceField()
        self.drone_pos = np.array([20.0, 20.0, 8.0])
        self.drone_goal = np.array([180.0, 180.0, 12.0])
        self.drone_velocity = np.array([0.0, 0.0, 0.0])
        self.trajectory = [self.drone_pos.copy()]
        
        # 导航参数
        self.sensor_range = 20
        self.replan_interval = 3
        self.step_count = 0
        self.max_speed = 5.0
        self.energy_consumption = 0.0
        self.collision_count = 0
        
        # 多尺度成本图
        self.cost_maps = {
            'static': self.build_static_cost_map(),
            'dynamic': np.zeros(self.env.size[:2]),
            'semantic': self.build_semantic_cost_map(),
            'combined': np.zeros(self.env.size[:2])
        }
        
        # 历史数据
        self.observation_history = []
        self.path_history = []
        
        # 构建初始路径
        self.planned_path = self.plan_path_astar()
        self.update_combined_cost_map()
        
    def build_static_cost_map(self):
        """构建静态障碍物成本图"""
        cost_map = np.zeros(self.env.size[:2])
        
        for i in range(self.env.size[0]):
            for j in range(self.env.size[1]):
                obstacle_cost = 0
                for obstacle in self.env.obstacles:
                    ox, oy, _ = obstacle['pos']
                    sx, sy, _ = obstacle['size']
                    dist = np.sqrt((i - ox)**2 + (j - oy)**2)
                    if dist < max(sx, sy) * 1.5:  # 扩大影响范围
                        cost = 0.9 * (1 - dist/(max(sx, sy) * 1.5))
                        obstacle_cost = max(obstacle_cost, cost)
                
                cost_map[i, j] = obstacle_cost
                
        return gaussian_filter(cost_map, sigma=3)
    
    def build_semantic_cost_map(self, height=10):
        """构建语义成本图"""
        cost_map = np.zeros(self.env.size[:2])
        
        for i in range(self.env.size[0]):
            for j in range(self.env.size[1]):
                cost_map[i, j] = self.env.get_semantic_cost(i, j, height)
                
        return cost_map
    
    def update_combined_cost_map(self):
        """更新组合成本图"""
        # 动态障碍物成本随时间衰减
        self.cost_maps['dynamic'] *= 0.95
        
        # 组合各种成本
        self.cost_maps['combined'] = (
            self.cost_maps['static'] * 0.4 +
            self.cost_maps['dynamic'] * 0.3 +
            self.cost_maps['semantic'] * 0.3
        )
    
    def simulate_enhanced_nerf_observation(self, position):
        """增强版NeRF观测模拟"""
        x, y, z = position
        
        # 基础密度和语义
        density = 0.0
        semantic_vector = np.zeros(5)  # 5个语义类别
        
        # 计算密度（基于障碍物距离和材质）
        for obstacle in self.env.obstacles + self.env.dynamic_obstacles:
            ox, oy, oz = obstacle['pos']
            dist = np.sqrt((x - ox)**2 + (y - oy)**2 + (z - oz)**2)
            
            # 不同材质的密度贡献不同
            material_density = {
                'concrete': 0.9, 'brick': 0.8, 'glass': 0.6, 
                'foliage': 0.5, 'steel': 0.7, 'metal': 0.7
            }
            
            material = obstacle.get('material', 'concrete')
            max_density = material_density.get(material, 0.7)
            
            if dist < 15:  # 观测范围
                density_contrib = max_density * (1 - dist/15)
                density = max(density, density_contrib)
        
        # 语义信息
        for region_name, region_data in self.env.semantic_regions.items():
            (x1, y1), (x2, y2) = region_data['area']
            if x1 <= x <= x2 and y1 <= y <= y2:
                semantic_class = region_data['semantic_class']
                semantic_vector[semantic_class] = 1.0
        
        # 天气和时间影响
        illumination = self.env.get_illumination_level(x, y, z)
        visibility = max(0.1, 1.0 - self.env.weather_conditions['fog'] * 0.8)
        
        return density, semantic_vector, illumination, visibility
    
    def update_cost_maps_with_observation(self, position):
        """用新的观测更新成本图"""
        x, y, z = position
        density, semantic_vector, illumination, visibility = self.simulate_enhanced_nerf_observation(position)
        
        # 更新动态成本图
        sensor_range = int(self.sensor_range * visibility)  # 能见度影响传感器范围
        x_min = max(0, int(x) - sensor_range)
        x_max = min(self.env.size[0], int(x) + sensor_range)
        y_min = max(0, int(y) - sensor_range)
        y_max = min(self.env.size[1], int(y) + sensor_range)
        
        for i in range(x_min, x_max):
            for j in range(y_min, y_max):
                dist = np.sqrt((i - x)**2 + (j - y)**2)
                if dist <= sensor_range:
                    weight = (1.0 - (dist / sensor_range)) * illumination
                    
                    # 动态障碍物成本
                    dynamic_cost = density * 0.6 + (1 - visibility) * 0.2
                    self.cost_maps['dynamic'][i, j] = max(
                        self.cost_maps['dynamic'][i, j],
                        dynamic_cost * weight
                    )
        
        self.update_combined_cost_map()
        self.observation_history.append({
            'position': position,
            'density': density,
            'semantic': semantic_vector,
            'timestamp': time.time()
        })
    
    def plan_path_astar(self):
        """使用A*算法规划路径，考虑多尺度成本图"""
        def heuristic(a, b):
            return np.sqrt((a[0]-b[0])**2 + (a[1]-b[1])**2)
        
        start = (int(self.drone_pos[0]), int(self.drone_pos[1]))
        goal = (int(self.drone_goal[0]), int(self.drone_goal[1]))
        
        open_set = {start}
        came_from = {}
        g_score = {start: 0}
        f_score = {start: heuristic(start, goal)}
        
        while open_set:
            current = min(open_set, key=lambda x: f_score.get(x, float('inf')))
            
            if current == goal:
                # 重建路径
                path = []
                while current in came_from:
                    path.append(current)
                    current = came_from[current]
                path.reverse()
                
                # 添加高度信息（根据地形和障碍物调整）
                full_path = []
                for i, (x, y) in enumerate(path):
                    # 寻找安全高度
                    z = 10  # 默认高度
                    for test_z in [8, 12, 15, 18]:
                        if not self.env.is_collision(x, y, test_z):
                            z = test_z
                            break
                    full_path.append((x, y, z))
                
                self.path_history.append(full_path)
                return full_path
            
            open_set.remove(current)
            
            # 探索8方向邻居
            for dx, dy in [(-1,0), (1,0), (0,-1), (0,1), 
                          (-1,-1), (-1,1), (1,-1), (1,1)]:
                neighbor = (current[0] + dx, current[1] + dy)
                
                if (0 <= neighbor[0] < self.env.size[0] and 
                    0 <= neighbor[1] < self.env.size[1]):
                    
                    # 检查碰撞
                    if self.env.is_collision(neighbor[0], neighbor[1], 10):  # 检查10米高度
                        continue
                    
                    # 成本计算
                    move_cost = np.sqrt(dx**2 + dy**2)
                    terrain_cost = self.cost_maps['combined'][neighbor] * 15
                    height_cost = 0  # 可以添加高度变化成本
                    
                    tentative_g_score = g_score[current] + move_cost + terrain_cost + height_cost
                    
                    if neighbor not in g_score or tentative_g_score < g_score[neighbor]:
                        came_from[neighbor] = current
                        g_score[neighbor] = tentative_g_score
                        f_score[neighbor] = tentative_g_score + heuristic(neighbor, goal)
                        open_set.add(neighbor)
        
        return []  # 无路径找到
    
    def navigate_step(self):
        """执行一步导航"""
        self.step_count += 1
        self.env.update_dynamic_obstacles()
        
        # 更新NeRF观测和成本图
        self.update_cost_maps_with_observation(self.drone_pos)
        
        # 能量消耗
        movement_cost = np.linalg.norm(self.drone_velocity) * 0.1
        hovering_cost = 0.05
        self.energy_consumption += movement_cost + hovering_cost
        
        # 定期重新规划路径或当路径为空时
        if (self.step_count % self.replan_interval == 0 or 
            not self.planned_path or
            self.env.is_collision(*self.drone_pos)):
            
            if self.env.is_collision(*self.drone_pos):
                self.collision_count += 1
            
            self.planned_path = self.plan_path_astar()
        
        # 沿着规划路径移动
        if self.planned_path:
            next_pos = np.array(self.planned_path[0])
            
            # 平滑移动（速度控制）
            direction = next_pos - self.drone_pos
            dist = np.linalg.norm(direction)
            
            if dist > 0:
                direction = direction / dist
                move_dist = min(dist, self.max_speed)
                new_pos = self.drone_pos + direction * move_dist
                
                # 检查移动是否安全
                if not self.env.is_collision(*new_pos):
                    self.drone_pos = new_pos
                    self.drone_velocity = direction * move_dist
                    self.planned_path = self.planned_path[1:]
                else:
                    # 如果移动不安全，重新规划
                    self.planned_path = self.plan_path_astar()
            else:
                self.planned_path = self.planned_path[1:]
            
            self.trajectory.append(self.drone_pos.copy())
        
        return self.drone_pos.copy()

class EnhancedVisualizationSystem:
    """增强版可视化系统"""
    
    def __init__(self, env, nav_system):
        self.env = env
        self.nav_system = nav_system
        
        # 创建图形和子图
        self.fig = plt.figure(figsize=(20, 15))
        
        # 更复杂的子图布局
        self.ax_3d_env = self.fig.add_subplot(331, projection='3d')
        self.ax_combined_cost = self.fig.add_subplot(332)
        self.ax_semantic_map = self.fig.add_subplot(333)
        self.ax_trajectory = self.fig.add_subplot(334)
        self.ax_nerf_density = self.fig.add_subplot(335)
        self.ax_energy_usage = self.fig.add_subplot(336)
        self.ax_path_analysis = self.fig.add_subplot(337)
        self.ax_sensor_data = self.fig.add_subplot(338)
        self.ax_performance = self.fig.add_subplot(339)
        
        plt.tight_layout()
        
        # 颜色映射
        self.cmap_cost = plt.cm.hot_r
        self.cmap_semantic = plt.cm.viridis
        self.cmap_density = plt.cm.plasma
        
    def plot_enhanced_3d_environment(self):
        """绘制增强的3D环境"""
        # 绘制静态障碍物
        for obstacle in self.env.obstacles:
            x, y, z = obstacle['pos']
            dx, dy, dz = obstacle['size']
            
            # 根据类型设置颜色
            colors = {
                'skyscraper': 'darkgray', 'building': 'gray', 
                'tree_cluster': 'green', 'bridge': 'lightblue',
                'power_line': 'yellow'
            }
            color = colors.get(obstacle['type'], 'gray')
            
            self.ax_3d_env.bar3d(x-dx/2, y-dy/2, 0, dx, dy, dz, 
                               color=color, alpha=0.7, shade=True)
        
        # 绘制动态障碍物
        for obstacle in self.env.dynamic_obstacles:
            x, y, z = obstacle['pos']
            dx, dy, dz = obstacle['size']
            
            colors = {'car': 'red', 'truck': 'darkred', 'drone': 'orange', 'bird_flock': 'brown'}
            color = colors.get(obstacle['type'], 'red')
            
            self.ax_3d_env.bar3d(x-dx/2, y-dy/2, 0, dx, dy, dz, 
                               color=color, alpha=0.6, shade=True)
            
            # 绘制速度向量
            vx, vy, vz = obstacle['velocity']
            self.ax_3d_env.quiver(x, y, z, vx, vy, vz, color=color, length=10, normalize=True)
        
        # 绘制无人机
        drone_x, drone_y, drone_z = self.nav_system.drone_pos
        self.ax_3d_env.scatter(drone_x, drone_y, drone_z, color='blue', s=100, label='Drone')
        
        # 绘制目标
        goal_x, goal_y, goal_z = self.nav_system.drone_goal
        self.ax_3d_env.scatter(goal_x, goal_y, goal_z, color='green', s=150, marker='*', label='Goal')
        
        # 绘制传感器范围
        u = np.linspace(0, 2 * np.pi, 30)
        v = np.linspace(0, np.pi, 15)
        x_sphere = drone_x + self.nav_system.sensor_range * np.outer(np.cos(u), np.sin(v))
        y_sphere = drone_y + self.nav_system.sensor_range * np.outer(np.sin(u), np.sin(v))
        z_sphere = drone_z + self.nav_system.sensor_range * np.outer(np.ones(np.size(u)), np.cos(v))
        
        self.ax_3d_env.plot_surface(x_sphere, y_sphere, z_sphere, color='blue', alpha=0.1)
        
        self.ax_3d_env.set_xlim(0, self.env.size[0])
        self.ax_3d_env.set_ylim(0, self.env.size[1])
        self.ax_3d_env.set_zlim(0, self.env.size[2])
        self.ax_3d_env.legend()
        
    def plot_combined_cost_map(self):
        """绘制组合成本图"""
        # 安全地清除可能存在的旧颜色条
        if hasattr(self, 'combined_cbar') and self.combined_cbar is not None:
            try:
                self.combined_cbar.remove()
            except (AttributeError, ValueError):
                pass  # 如果颜色条已经无效，忽略错误
            self.combined_cbar = None
        
        im = self.ax_combined_cost.imshow(self.nav_system.cost_maps['combined'].T, 
                                        origin='lower', 
                                        extent=[0, self.env.size[0], 0, self.env.size[1]], 
                                        cmap=self.cmap_cost, alpha=0.8)
        
        # 添加无人机位置和路径
        drone_x, drone_y, _ = self.nav_system.drone_pos
        self.ax_combined_cost.scatter(drone_x, drone_y, color='blue', s=80)
        
        if self.nav_system.planned_path:
            path_x = [pos[0] for pos in self.nav_system.planned_path]
            path_y = [pos[1] for pos in self.nav_system.planned_path]
            self.ax_combined_cost.plot(path_x, path_y, 'g-', linewidth=2, label='Planned Path')
        
        self.combined_cbar = self.fig.colorbar(im, ax=self.ax_combined_cost)
        self.combined_cbar.set_label('Combined Cost')
        self.ax_combined_cost.legend()

    def plot_nerf_density_field(self):
        """绘制NeRF密度场"""
        # 安全地清除可能存在的旧颜色条
        if hasattr(self, 'density_cbar') and self.density_cbar is not None:
            try:
                self.density_cbar.remove()
            except (AttributeError, ValueError):
                pass  # 如果颜色条已经无效，忽略错误
            self.density_cbar = None
        
        # 在网格上采样密度
        x_samples = np.linspace(0, self.env.size[0], 25)
        y_samples = np.linspace(0, self.env.size[1], 25)
        
        densities = np.zeros((len(x_samples), len(y_samples)))
        
        for i, x in enumerate(x_samples):
            for j, y in enumerate(y_samples):
                density, _, _, _ = self.nav_system.simulate_enhanced_nerf_observation([x, y, 10])
                densities[i, j] = density
        
        im = self.ax_nerf_density.imshow(densities.T, origin='lower', 
                                    extent=[0, self.env.size[0], 0, self.env.size[1]], 
                                    cmap=self.cmap_density, alpha=0.8)
        
        self.density_cbar = self.fig.colorbar(im, ax=self.ax_nerf_density)
        self.density_cbar.set_label('NeRF Density')

    def plot_trajectory_analysis(self):
        """绘制轨迹分析"""
        # 安全地清除可能存在的旧颜色条
        if hasattr(self, 'trajectory_cbar') and self.trajectory_cbar is not None:
            try:
                self.trajectory_cbar.remove()
            except (AttributeError, ValueError):
                pass  # 如果颜色条已经无效，忽略错误
            self.trajectory_cbar = None
        
        if len(self.nav_system.trajectory) > 1:
            traj = np.array(self.nav_system.trajectory)
            
            # 用颜色表示速度
            speeds = np.linalg.norm(np.diff(traj, axis=0), axis=1)
            speeds = np.concatenate([[0], speeds])  # 第一个点速度为0
            
            scatter = self.ax_trajectory.scatter(traj[:, 0], traj[:, 1], c=speeds, 
                                            cmap='coolwarm', s=30, alpha=0.7)
            self.trajectory_cbar = self.fig.colorbar(scatter, ax=self.ax_trajectory)
            self.trajectory_cbar.set_label('Speed')
            
            # 绘制传感器范围
            drone_x, drone_y, _ = self.nav_system.drone_pos
            sensor_circle = plt.Circle((drone_x, drone_y), self.nav_system.sensor_range, 
                                    color='blue', alpha=0.2)
            self.ax_trajectory.add_patch(sensor_circle)
        
        # 目标位置
        goal_x, goal_y, _ = self.nav_system.drone_goal
        self.ax_trajectory.scatter(goal_x, goal_y, color='green', s=100, marker='*')
        
        self.ax_trajectory.set_xlim(0, self.env.size[0])
        self.ax_trajectory.set_ylim(0, self.env.size[1])
        self.ax_trajectory.set_aspect('equal')

    def update_all_visualizations(self):
        """更新所有可视化"""
        # 在清除所有子图之前初始化颜色条属性
        if not hasattr(self, 'combined_cbar'):
            self.combined_cbar = None
        if not hasattr(self, 'density_cbar'):
            self.density_cbar = None
        if not hasattr(self, 'trajectory_cbar'):
            self.trajectory_cbar = None
        
        # 清除所有子图但不销毁颜色条引用
        for ax in [self.ax_3d_env, self.ax_combined_cost, self.ax_semantic_map,
                self.ax_trajectory, self.ax_nerf_density, self.ax_energy_usage,
                self.ax_path_analysis, self.ax_sensor_data, self.ax_performance]:
            ax.clear()
        
        # 更新可视化
        self.plot_enhanced_3d_environment()
        self.plot_combined_cost_map()
        self.plot_enhanced_semantic_map()
        self.plot_trajectory_analysis()
        self.plot_nerf_density_field()
        self.plot_energy_consumption()
        self.plot_path_analysis()
        self.plot_sensor_data()
        self.plot_performance_metrics()
        
        # 设置标题
        titles = [
            '3D Environment with Enhanced NeRF Navigation',
            'Combined Cost Map (Static + Dynamic + Semantic)',
            'Semantic Regions and Risk Assessment',
            'Trajectory Analysis and Sensor Coverage',
            'NeRF Density Field Estimation',
            'Energy Consumption Profile',
            'Path Planning Analysis',
            'Real-time Sensor Data',
            'Performance Metrics'
        ]
        
        axes = [self.ax_3d_env, self.ax_combined_cost, self.ax_semantic_map,
                self.ax_trajectory, self.ax_nerf_density, self.ax_energy_usage,
                self.ax_path_analysis, self.ax_sensor_data, self.ax_performance]
        
        for ax, title in zip(axes, titles):
            ax.set_title(title, fontsize=10)
        
        self.fig.tight_layout()
        
    def plot_enhanced_semantic_map(self):
        """绘制增强的语义地图"""
        # 绘制语义区域
        semantic_colors = ['green', 'lightblue', 'yellow', 'orange', 'red']
        semantic_labels = ['Safe', 'Residential', 'Commercial', 'Park', 'Danger']
        
        for region_name, region_data in self.env.semantic_regions.items():
            (x1, y1), (x2, y2) = region_data['area']
            semantic_class = region_data['semantic_class']
            color = semantic_colors[semantic_class]
            
            rect = patches.Rectangle((x1, y1), x2-x1, y2-y1, 
                                   linewidth=2, edgecolor=color, 
                                   facecolor=color, alpha=0.4)
            self.ax_semantic_map.add_patch(rect)
            self.ax_semantic_map.text((x1+x2)/2, (y1+y2)/2, region_name, 
                                    ha='center', va='center', fontsize=8, fontweight='bold')
        
        # 添加图例
        for i, (color, label) in enumerate(zip(semantic_colors, semantic_labels)):
            self.ax_semantic_map.plot([], [], color=color, label=label, linewidth=10)
        
        self.ax_semantic_map.set_xlim(0, self.env.size[0])
        self.ax_semantic_map.set_ylim(0, self.env.size[1])
        self.ax_semantic_map.legend()
        
    def plot_energy_consumption(self):
        """绘制能量消耗图"""
        steps = list(range(self.nav_system.step_count + 1))
        energy_per_step = [0.0]
        
        # 计算每步的能量消耗（简化模型）
        for i in range(1, len(self.nav_system.trajectory)):
            if i < len(self.nav_system.trajectory):
                dist = np.linalg.norm(self.nav_system.trajectory[i] - self.nav_system.trajectory[i-1])
                energy = dist * 0.1 + 0.05  # 移动能耗 + 悬停能耗
                energy_per_step.append(energy_per_step[-1] + energy)
        
        self.ax_energy_usage.plot(steps[:len(energy_per_step)], energy_per_step, 'r-', linewidth=2)
        self.ax_energy_usage.set_xlabel('Time Steps')
        self.ax_energy_usage.set_ylabel('Total Energy Consumption')
        self.ax_energy_usage.grid(True, alpha=0.3)
        
    def plot_path_analysis(self):
        """绘制路径分析"""
        if len(self.nav_system.path_history) > 0:
            # 绘制所有历史路径
            for i, path in enumerate(self.nav_system.path_history[-5:]):  # 只显示最近5条路径
                if len(path) > 1:
                    path_arr = np.array(path)
                    alpha = 0.2 + 0.8 * (i / min(5, len(self.nav_system.path_history)))
                    self.ax_path_analysis.plot(path_arr[:, 0], path_arr[:, 1], 
                                             color='purple', alpha=alpha, linewidth=1)
            
            # 当前路径
            if self.nav_system.planned_path and len(self.nav_system.planned_path) > 1:
                current_path = np.array(self.nav_system.planned_path)
                self.ax_path_analysis.plot(current_path[:, 0], current_path[:, 1], 
                                         'g-', linewidth=3, label='Current Path')
        
        # 起点和终点
        start_x, start_y, _ = self.nav_system.trajectory[0]
        goal_x, goal_y, _ = self.nav_system.drone_goal
        self.ax_path_analysis.scatter(start_x, start_y, color='blue', s=100, label='Start')
        self.ax_path_analysis.scatter(goal_x, goal_y, color='green', s=100, marker='*', label='Goal')
        
        self.ax_path_analysis.set_xlim(0, self.env.size[0])
        self.ax_path_analysis.set_ylim(0, self.env.size[1])
        self.ax_path_analysis.legend()
        self.ax_path_analysis.set_aspect('equal')
        
    def plot_sensor_data(self):
        """绘制传感器数据"""
        if len(self.nav_system.observation_history) > 0:
            # 提取最近的观测数据
            recent_obs = self.nav_system.observation_history[-10:]  # 最近10个观测
            
            densities = [obs['density'] for obs in recent_obs]
            timestamps = [obs['timestamp'] - recent_obs[0]['timestamp'] for obs in recent_obs]
            
            self.ax_sensor_data.plot(timestamps, densities, 'bo-', linewidth=2, label='Density')
            self.ax_sensor_data.set_xlabel('Time (s)')
            self.ax_sensor_data.set_ylabel('Observed Density')
            self.ax_sensor_data.legend()
            self.ax_sensor_data.grid(True, alpha=0.3)
        
    def plot_performance_metrics(self):
        """绘制性能指标"""
        metrics = [
            f"Steps: {self.nav_system.step_count}",
            f"Energy: {self.nav_system.energy_consumption:.1f}",
            f"Collisions: {self.nav_system.collision_count}",
            f"Distance to Goal: {np.linalg.norm(self.nav_system.drone_pos - self.nav_system.drone_goal):.1f}m",
            f"Path Efficiency: {self.calculate_path_efficiency():.3f}",
            f"Avg Cost: {self.calculate_average_path_cost():.3f}"
        ]
        
        self.ax_performance.axis('off')
        for i, metric in enumerate(metrics):
            self.ax_performance.text(0.1, 0.9 - i*0.15, metric, fontsize=12, 
                                   transform=self.ax_performance.transAxes,
                                   bbox=dict(boxstyle="round,pad=0.3", facecolor="lightblue"))
    
    def calculate_path_efficiency(self):
        """计算路径效率"""
        if len(self.nav_system.trajectory) < 2:
            return 0.0
        
        straight_dist = np.linalg.norm(self.nav_system.trajectory[0] - self.nav_system.drone_goal)
        actual_dist = 0.0
        for i in range(1, len(self.nav_system.trajectory)):
            actual_dist += np.linalg.norm(self.nav_system.trajectory[i] - self.nav_system.trajectory[i-1])
        
        return straight_dist / actual_dist if actual_dist > 0 else 0.0
    
    def calculate_average_path_cost(self):
        """计算路径平均成本"""
        if len(self.nav_system.trajectory) == 0:
            return 0.0
        
        total_cost = 0.0
        for pos in self.nav_system.trajectory:
            x, y = int(pos[0]), int(pos[1])
            if 0 <= x < self.nav_system.cost_maps['combined'].shape[0] and 0 <= y < self.nav_system.cost_maps['combined'].shape[1]:
                total_cost += self.nav_system.cost_maps['combined'][x, y]
        
        return total_cost / len(self.nav_system.trajectory)

class NeRFNavigationApp(QMainWindow):
    """PyQt主应用程序窗口"""
    
    def __init__(self):
        super().__init__()
        self.env = EnhancedEnvironmentSimulator()
        self.nav_system = EnhancedNeRFDroneNavigation(self.env)
        self.viz_system = EnhancedVisualizationSystem(self.env, self.nav_system)
        
        self.simulation_timer = QTimer()
        self.simulation_timer.timeout.connect(self.simulation_step)
        
        self.is_playing = False
        self.current_speed = 1
        
        self.init_ui()
        
    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("Enhanced NeRF-based Drone Navigation System")
        self.setGeometry(100, 50, 1800, 1000)
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QHBoxLayout(central_widget)
        
        # 左侧控制面板
        control_panel = self.create_control_panel()
        main_layout.addWidget(control_panel, 1)
        
        # 右侧可视化区域
        viz_frame = self.create_visualization_frame()
        main_layout.addWidget(viz_frame, 4)
        
        # 状态栏
        self.statusBar().showMessage("Ready to start simulation")
        
    def create_control_panel(self):
        """创建控制面板"""
        control_frame = QFrame()
        control_frame.setFrameStyle(QFrame.Box)
        control_frame.setLineWidth(2)
        
        layout = QVBoxLayout(control_frame)
        
        # 模拟控制组
        sim_group = QGroupBox("Simulation Control")
        sim_layout = QVBoxLayout(sim_group)
        
        # 控制按钮
        btn_layout = QHBoxLayout()
        self.start_btn = QPushButton("Start")
        self.pause_btn = QPushButton("Pause")
        self.reset_btn = QPushButton("Reset")
        self.step_btn = QPushButton("Step")
        
        self.start_btn.clicked.connect(self.start_simulation)
        self.pause_btn.clicked.connect(self.pause_simulation)
        self.reset_btn.clicked.connect(self.reset_simulation)
        self.step_btn.clicked.connect(self.single_step)
        
        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.pause_btn)
        btn_layout.addWidget(self.reset_btn)
        btn_layout.addWidget(self.step_btn)
        sim_layout.addLayout(btn_layout)
        
        # 速度控制
        speed_layout = QHBoxLayout()
        speed_layout.addWidget(QLabel("Speed:"))
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setRange(1, 10)
        self.speed_slider.setValue(5)
        self.speed_slider.valueChanged.connect(self.change_speed)
        speed_layout.addWidget(self.speed_slider)
        sim_layout.addLayout(speed_layout)
        
        # 进度条
        self.progress_bar = QProgressBar()
        sim_layout.addWidget(self.progress_bar)
        
        layout.addWidget(sim_group)
        
        # 环境参数组
        env_group = QGroupBox("Environment Parameters")
        env_layout = QGridLayout(env_group)
        
        # 天气控制
        env_layout.addWidget(QLabel("Fog Density:"), 0, 0)
        self.fog_spin = QDoubleSpinBox()
        self.fog_spin.setRange(0.0, 1.0)
        self.fog_spin.setSingleStep(0.1)
        self.fog_spin.setValue(0.0)
        self.fog_spin.valueChanged.connect(self.update_weather)
        env_layout.addWidget(self.fog_spin, 0, 1)
        
        env_layout.addWidget(QLabel("Wind Speed:"), 1, 0)
        self.wind_spin = QDoubleSpinBox()
        self.wind_spin.setRange(0.0, 10.0)
        self.wind_spin.setValue(0.0)
        self.wind_spin.valueChanged.connect(self.update_weather)
        env_layout.addWidget(self.wind_spin, 1, 1)
        
        env_layout.addWidget(QLabel("Rain Intensity:"), 2, 0)
        self.rain_spin = QDoubleSpinBox()
        self.rain_spin.setRange(0.0, 1.0)
        self.rain_spin.setValue(0.0)
        self.rain_spin.valueChanged.connect(self.update_weather)
        env_layout.addWidget(self.rain_spin, 2, 1)
        
        env_layout.addWidget(QLabel("Time of Day:"), 3, 0)
        self.time_spin = QDoubleSpinBox()
        self.time_spin.setRange(0.0, 24.0)
        self.time_spin.setValue(12.0)
        self.time_spin.valueChanged.connect(self.update_time)
        env_layout.addWidget(self.time_spin, 3, 1)
        
        layout.addWidget(env_group)
        
        # 无人机参数组
        drone_group = QGroupBox("Drone Parameters")
        drone_layout = QGridLayout(drone_group)
        
        drone_layout.addWidget(QLabel("Sensor Range:"), 0, 0)
        self.sensor_spin = QDoubleSpinBox()
        self.sensor_spin.setRange(5.0, 50.0)
        self.sensor_spin.setValue(20.0)
        self.sensor_spin.valueChanged.connect(self.update_drone_params)
        drone_layout.addWidget(self.sensor_spin, 0, 1)
        
        drone_layout.addWidget(QLabel("Max Speed:"), 1, 0)
        self.speed_spin = QDoubleSpinBox()
        self.speed_spin.setRange(1.0, 10.0)
        self.speed_spin.setValue(5.0)
        self.speed_spin.valueChanged.connect(self.update_drone_params)
        drone_layout.addWidget(self.speed_spin, 1, 1)
        
        drone_layout.addWidget(QLabel("Replan Interval:"), 2, 0)
        self.replan_spin = QSpinBox()
        self.replan_spin.setRange(1, 20)
        self.replan_spin.setValue(3)
        self.replan_spin.valueChanged.connect(self.update_drone_params)
        drone_layout.addWidget(self.replan_spin, 2, 1)
        
        layout.addWidget(drone_group)
        
        # 导航算法组
        algo_group = QGroupBox("Navigation Algorithm")
        algo_layout = QVBoxLayout(algo_group)
        
        self.algo_combo = QComboBox()
        self.algo_combo.addItems(["A* with NeRF Cost", "RRT* with NeRF", "D* Lite with NeRF"])
        algo_layout.addWidget(self.algo_combo)
        
        cost_layout = QHBoxLayout()
        cost_layout.addWidget(QLabel("Static Weight:"))
        self.static_weight = QDoubleSpinBox()
        self.static_weight.setRange(0.0, 1.0)
        self.static_weight.setValue(0.4)
        self.static_weight.valueChanged.connect(self.update_cost_weights)
        cost_layout.addWidget(self.static_weight)
        algo_layout.addLayout(cost_layout)
        
        cost_layout2 = QHBoxLayout()
        cost_layout2.addWidget(QLabel("Dynamic Weight:"))
        self.dynamic_weight = QDoubleSpinBox()
        self.dynamic_weight.setRange(0.0, 1.0)
        self.dynamic_weight.setValue(0.3)
        self.dynamic_weight.valueChanged.connect(self.update_cost_weights)
        cost_layout2.addWidget(self.dynamic_weight)
        algo_layout.addLayout(cost_layout2)
        
        cost_layout3 = QHBoxLayout()
        cost_layout3.addWidget(QLabel("Semantic Weight:"))
        self.semantic_weight = QDoubleSpinBox()
        self.semantic_weight.setRange(0.0, 1.0)
        self.semantic_weight.setValue(0.3)
        self.semantic_weight.valueChanged.connect(self.update_cost_weights)
        cost_layout3.addWidget(self.semantic_weight)
        algo_layout.addLayout(cost_layout3)
        
        layout.addWidget(algo_group)
        
        # 数据显示组
        data_group = QGroupBox("Performance Data")
        data_layout = QVBoxLayout(data_group)
        
        self.data_display = QTextEdit()
        self.data_display.setReadOnly(True)
        self.data_display.setMaximumHeight(200)
        data_layout.addWidget(self.data_display)
        
        layout.addWidget(data_group)
        
        # 分析按钮
        self.analyze_btn = QPushButton("Run Performance Analysis")
        self.analyze_btn.clicked.connect(self.run_performance_analysis)
        layout.addWidget(self.analyze_btn)
        
        layout.addStretch()
        
        return control_frame
        
    def create_visualization_frame(self):
        """创建可视化框架"""
        viz_frame = QFrame()
        layout = QVBoxLayout(viz_frame)
        
        # 创建matplotlib画布
        self.canvas = FigureCanvas(self.viz_system.fig)
        self.toolbar = NavigationToolbar(self.canvas, self)
        
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)
        
        return viz_frame
        
    def start_simulation(self):
        """开始模拟"""
        self.is_playing = True
        interval = 1000 // (self.current_speed * 2)  # 根据速度调整间隔
        self.simulation_timer.start(interval)
        self.statusBar().showMessage("Simulation running...")
        
    def pause_simulation(self):
        """暂停模拟"""
        self.is_playing = False
        self.simulation_timer.stop()
        self.statusBar().showMessage("Simulation paused")
        
    def reset_simulation(self):
        """重置模拟"""
        self.pause_simulation()
        self.env = EnhancedEnvironmentSimulator()
        self.nav_system = EnhancedNeRFDroneNavigation(self.env)
        self.viz_system = EnhancedVisualizationSystem(self.env, self.nav_system)
        self.canvas.figure = self.viz_system.fig
        self.update_display()
        self.statusBar().showMessage("Simulation reset")
        
    def single_step(self):
        """单步执行"""
        self.pause_simulation()
        self.simulation_step()
        
    def simulation_step(self):
        """模拟步骤"""
        if self.is_playing:
            self.nav_system.navigate_step()
            self.update_display()
            
            # 检查是否到达目标
            dist_to_goal = np.linalg.norm(self.nav_system.drone_pos - self.nav_system.drone_goal)
            if dist_to_goal < 5.0:
                self.pause_simulation()
                self.statusBar().showMessage("Goal reached!")
                
            # 更新进度条
            progress = min(100, int((self.nav_system.step_count / 200) * 100))
            self.progress_bar.setValue(progress)
            
    def change_speed(self, value):
        """改变模拟速度"""
        self.current_speed = value
        if self.is_playing:
            self.pause_simulation()
            self.start_simulation()
            
    def update_weather(self):
        """更新天气条件"""
        fog = self.fog_spin.value()
        wind_speed = self.wind_spin.value()
        rain = self.rain_spin.value()
        self.env.set_weather_conditions(fog, wind_speed, 0, rain)
        
    def update_time(self):
        """更新时间"""
        self.env.set_time_of_day(self.time_spin.value())
        
    def update_drone_params(self):
        """更新无人机参数"""
        self.nav_system.sensor_range = self.sensor_spin.value()
        self.nav_system.max_speed = self.speed_spin.value()
        self.nav_system.replan_interval = self.replan_spin.value()
        
    def update_cost_weights(self):
        """更新成本权重"""
        static_w = self.static_weight.value()
        dynamic_w = self.dynamic_weight.value()
        semantic_w = self.semantic_weight.value()
        
        # 归一化权重
        total = static_w + dynamic_w + semantic_w
        if total > 0:
            self.nav_system.cost_maps['combined'] = (
                self.nav_system.cost_maps['static'] * (static_w / total) +
                self.nav_system.cost_maps['dynamic'] * (dynamic_w / total) +
                self.nav_system.cost_maps['semantic'] * (semantic_w / total)
            )
        
    def update_display(self):
        """更新显示"""
        self.viz_system.update_all_visualizations()
        self.canvas.draw()
        self.update_data_display()
        
    def update_data_display(self):
        """更新数据显示"""
        data_text = f"""
=== Real-time Performance Data ===
Step Count: {self.nav_system.step_count}
Drone Position: ({self.nav_system.drone_pos[0]:.1f}, {self.nav_system.drone_pos[1]:.1f}, {self.nav_system.drone_pos[2]:.1f})
Distance to Goal: {np.linalg.norm(self.nav_system.drone_pos - self.nav_system.drone_goal):.1f}m
Energy Consumption: {self.nav_system.energy_consumption:.1f}
Collision Count: {self.nav_system.collision_count}
Current Speed: {np.linalg.norm(self.nav_system.drone_velocity):.1f} m/s
Path Efficiency: {self.viz_system.calculate_path_efficiency():.3f}
Average Path Cost: {self.viz_system.calculate_average_path_cost():.3f}
Observations Collected: {len(self.nav_system.observation_history)}
Paths Planned: {len(self.nav_system.path_history)}
        """
        self.data_display.setText(data_text.strip())
        
    def run_performance_analysis(self):
        """运行性能分析"""
        analysis_text = """
=== Detailed Performance Analysis ===

PATH EFFICIENCY ANALYSIS:
- Straight-line distance: {straight_dist:.1f}m
- Actual path length: {actual_dist:.1f}m
- Efficiency ratio: {efficiency:.3f}

COST ANALYSIS:
- Average cost along path: {avg_cost:.3f}
- Minimum possible cost in environment: {min_cost:.3f}
- Cost efficiency: {cost_efficiency:.3f}

ENERGY ANALYSIS:
- Total energy consumed: {energy:.1f}
- Energy per meter: {energy_per_meter:.3f}

OBSTACLE AVOIDANCE:
- Dynamic obstacles avoided: {obstacles_avoided}/{total_obstacles}
- Collision incidents: {collisions}

NAVIGATION INTELLIGENCE:
- Path replanning events: {replanning_events}
- Average observations per step: {obs_per_step:.1f}
- Semantic understanding utilization: {semantic_utilization:.1f}%
        """.format(
            straight_dist=np.linalg.norm(self.nav_system.trajectory[0] - self.nav_system.drone_goal),
            actual_dist=sum(np.linalg.norm(self.nav_system.trajectory[i] - self.nav_system.trajectory[i-1]) 
                          for i in range(1, len(self.nav_system.trajectory))),
            efficiency=self.viz_system.calculate_path_efficiency(),
            avg_cost=self.viz_system.calculate_average_path_cost(),
            min_cost=np.min(self.nav_system.cost_maps['combined']),
            cost_efficiency=1.0 - self.viz_system.calculate_average_path_cost(),
            energy=self.nav_system.energy_consumption,
            energy_per_meter=self.nav_system.energy_consumption / max(1, len(self.nav_system.trajectory)),
            obstacles_avoided=len(self.env.dynamic_obstacles) - self.nav_system.collision_count,
            total_obstacles=len(self.env.dynamic_obstacles),
            collisions=self.nav_system.collision_count,
            replanning_events=len(self.nav_system.path_history),
            obs_per_step=len(self.nav_system.observation_history) / max(1, self.nav_system.step_count),
            semantic_utilization=100 * np.mean([np.max(obs['semantic']) for obs in self.nav_system.observation_history])
        )
        
        QMessageBox.information(self, "Performance Analysis", analysis_text.strip())

def main():
    app = QApplication(sys.argv)
    
    # 设置应用程序样式
    app.setStyle('Fusion')
    
    # 创建并显示主窗口
    main_window = NeRFNavigationApp()
    main_window.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()