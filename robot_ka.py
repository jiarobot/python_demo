import numpy as np
import math
import time
import logging
from collections import defaultdict
import heapq
from scipy.spatial import Delaunay, ConvexHull
from scipy.spatial.distance import pdist, squareform
from sklearn.cluster import DBSCAN
import sys
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Rectangle, Circle
from matplotlib.collections import PatchCollection
from matplotlib.animation import FuncAnimation
from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits.mplot3d.art3d import Poly3DCollection, Line3DCollection
import matplotlib.cm as cm
from matplotlib.colors import Normalize
import matplotlib.gridspec as gridspec

class UnifiedMobileRobot:
    """统一移动机器人类，支持无人机和无人车模式"""
    
    def __init__(self, robot_type="drone", max_range=100.0, resolution=1.0):
        """
        初始化移动机器人
        
        参数:
            robot_type: 机器人类型 ("drone" 或 "ground")
            max_range: 传感器最大探测范围(米)
            resolution: 地形分辨率(米)
        """
        self.robot_type = robot_type
        self.max_range = max_range
        self.resolution = resolution
        
        # 机器人状态
        self.position = np.array([0.0, 0.0, 10.0])  # [x, y, z]
        self.orientation = np.array([0.0, 0.0, 0.0])  # [roll, pitch, yaw]
        self.velocity = np.array([0.0, 0.0, 0.0])  # [vx, vy, vz]
        self.battery_level = 100.0  # 电池百分比
        self.mode = "idle"  # 状态: idle, exploring, navigating, returning
        
        # 地形与环境
        self.terrain_points = np.empty((0, 3))  # 地形点云
        self.obstacles = []  # 障碍物列表
        self.water_bodies = []  # 水体区域
        self.vegetation_zones = []  # 植被区域
        self.terrain_features = {}  # 地形特征
        self.complexity_map = None  # 地形复杂度热力图
        self.thermal_map = None  # 热力图
        
        # 路径规划
        self.current_path = []  # 当前路径
        self.current_waypoint_idx = 0  # 当前航点索引
        self.path_cache = {}  # 路径缓存
        self.landing_zone = None  # 最佳着陆区
        
        # 动态障碍物追踪
        self.moving_obstacles = []
        self.obstacle_history = defaultdict(list)
        self.last_dynamic_update = time.time()
        
        # 配置参数
        self.clustering_model = DBSCAN(eps=2.0, min_samples=3)
        self.safety_margin = 3.0  # 安全裕度(米)
        self.max_speed = 5.0 if robot_type == "drone" else 2.0  # 最大速度(m/s)
        self.max_altitude = 50.0  # 最大飞行高度(米)
        self.min_altitude = 2.0  # 最小飞行高度(米)
        self.water_threshold = -1.0  # 水体检测高度阈值
        self.vegetation_threshold = 0.3  # 植被密度阈值
        
        # 初始化日志
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger("UnifiedMobileRobot")
        self.logger.info(f"初始化 {robot_type} 机器人")
    
    def update_sensors(self, point_cloud):
        """
        更新传感器数据并处理环境
        
        参数:
            point_cloud: 传感器获取的点云数据 (Nx3数组)
        """
        try:
            # 更新地形模型
            success = self._update_terrain_model(point_cloud)
            
            if success:
                # 提取地形特征
                self._extract_terrain_features()
                
                # 识别障碍物
                self._identify_obstacles()
                
                # 识别水体和植被
                self._identify_water_bodies()
                self._identify_vegetation_zones()
                
                # 计算地形复杂度热力图
                self._calculate_complexity_map()
                
                # 生成热力图
                self._generate_thermal_map()
                
                # 动态障碍物追踪
                current_time = time.time()
                if current_time - self.last_dynamic_update > 5.0:  # 每5秒更新一次
                    self._track_moving_obstacles()
                    self.last_dynamic_update = current_time
                    
                self.logger.info("传感器数据更新成功")
                return True
        except Exception as e:
            self.logger.error(f"传感器数据更新失败: {str(e)}")
            return False
    
    def _update_terrain_model(self, point_cloud):
        """更新地形模型"""
        # 点云预处理 - 转换为全局坐标系
        transformed_points = self._transform_to_global(point_cloud)
        
        # 过滤点云（范围和分辨率）
        self.terrain_points = self._filter_points(transformed_points)
        return True
    
    def _transform_to_global(self, point_cloud):
        """将点云数据转换为全局坐标系（考虑机器人姿态）"""
        # 简化实现 - 实际应使用旋转矩阵
        return point_cloud + self.position
    
    def _filter_points(self, points):
        """过滤点云数据（范围和分辨率）"""
        if points.size == 0:
            return points
        
        # 确保点云是二维数组
        if points.ndim == 1:
            points = points.reshape(-1, 3)
        
        # 计算到机器人的距离
        distances = np.linalg.norm(points[:, :3] - self.position[:3], axis=1)
        
        # 应用范围过滤
        filtered = points[distances <= self.max_range]
        
        # 应用分辨率过滤
        if self.resolution > 0 and len(filtered) > 0:
            # 使用网格化简化
            grid_size = self.resolution
            grid_points = {}
            for point in filtered:
                grid_key = tuple((point[:2] // grid_size).astype(int))
                if grid_key not in grid_points:
                    grid_points[grid_key] = []
                grid_points[grid_key].append(point)
            
            # 取每个网格的平均点
            filtered = np.array([np.mean(points, axis=0) for points in grid_points.values()])
        
        return filtered
    
    def _extract_terrain_features(self):
        """提取地形特征"""
        if len(self.terrain_points) < 3:
            self.terrain_features = {}
            return
            
        points = self.terrain_points
        
        # 1. 地形粗糙度（高度标准差）
        heights = points[:, 2]
        roughness = np.std(heights)
        
        # 2. 平均坡度
        slopes = []
        if len(points) > 10:
            try:
                # 使用Delaunay三角剖分计算坡度
                tri = Delaunay(points[:, :2])
                for simplex in tri.simplices:
                    a, b, c = points[simplex]
                    normal = np.cross(b - a, c - a)
                    slope = np.abs(np.arctan2(np.linalg.norm(normal[:2]), np.abs(normal[2])))
                    slopes.append(slope)
            except Exception as e:
                self.logger.warning(f"坡度计算失败: {str(e)}")
                slopes = []
        
        avg_slope = np.mean(slopes) if slopes else 0.0
        
        # 3. 地形起伏度（最大高度差）
        height_range = np.max(heights) - np.min(heights)
        
        # 4. 障碍物密度
        obstacle_density = len(self.obstacles) / len(points) if points.size > 0 else 0.0
        
        # 5. 可通行区域比例
        traversable_area = self._calculate_traversable_area()
        
        # 6. 地形复杂度
        complexity = self.analyze_terrain_complexity()
        
        # 存储特征
        self.terrain_features = {
            'roughness': roughness,
            'avg_slope': math.degrees(avg_slope) if avg_slope > 0 else 0.0,  # 转换为角度
            'height_range': height_range,
            'obstacle_density': obstacle_density,
            'traversable_area': traversable_area,
            'complexity': complexity
        }
    
    def _calculate_traversable_area(self):
        """计算可通行区域比例"""
        if len(self.terrain_points) == 0:
            return 0.0
            
        # 创建网格地图
        min_xy = np.min(self.terrain_points[:, :2], axis=0)
        max_xy = np.max(self.terrain_points[:, :2], axis=0)
        
        grid_size = self.resolution * 2
        width = int((max_xy[0] - min_xy[0]) / grid_size) + 1
        height = int((max_xy[1] - min_xy[1]) / grid_size) + 1
        
        if width <= 0 or height <= 0:
            return 0.0
        
        # 初始化网格
        grid = np.zeros((width, height), dtype=bool)
        
        # 标记障碍网格
        for obstacle in self.obstacles:
            min_obstacle = np.min(obstacle['vertices'], axis=0)
            max_obstacle = np.max(obstacle['vertices'], axis=0)
            
            min_x_idx = int((min_obstacle[0] - min_xy[0]) / grid_size)
            min_y_idx = int((min_obstacle[1] - min_xy[1]) / grid_size)
            max_x_idx = int((max_obstacle[0] - min_xy[0]) / grid_size)
            max_y_idx = int((max_obstacle[1] - min_xy[1]) / grid_size)
            
            # 确保索引在范围内
            min_x_idx = max(0, min(min_x_idx, width-1))
            min_y_idx = max(0, min(min_y_idx, height-1))
            max_x_idx = max(0, min(max_x_idx, width-1))
            max_y_idx = max(0, min(max_y_idx, height-1))
            
            grid[min_x_idx:max_x_idx+1, min_y_idx:max_y_idx+1] = True
        
        # 计算可通行区域比例
        traversable_cells = np.sum(~grid)
        total_cells = width * height
        return traversable_cells / total_cells if total_cells > 0 else 0.0
    
    def _identify_obstacles(self, height_threshold=0.5, slope_threshold=30):
        """识别障碍物"""
        self.obstacles = []
        if len(self.terrain_points) < 3:
            return
            
        # 1. 聚类分析识别障碍物
        try:
            clustering = self.clustering_model.fit(self.terrain_points)
            labels = clustering.labels_
            
            # 2. 识别障碍物群
            obstacle_clusters = {}
            for i, label in enumerate(labels):
                if label == -1:  # 噪声点
                    continue
                if label not in obstacle_clusters:
                    obstacle_clusters[label] = []
                obstacle_clusters[label].append(self.terrain_points[i])
            
            # 3. 计算每个簇的特征
            for cluster_id, points in obstacle_clusters.items():
                if len(points) < 3:
                    continue
                    
                # 确保点云是二维数组
                cluster_points = np.array(points).reshape(-1, 3)
                
                # 计算簇的高度和凸包
                min_z = np.min(cluster_points[:, 2])
                max_z = np.max(cluster_points[:, 2])
                height = max_z - min_z
                
                # 如果高度超过阈值，标记为障碍物
                if height > height_threshold:
                    # 计算凸包作为障碍物边界
                    try:
                        hull = ConvexHull(cluster_points[:, :2])
                        vertices = cluster_points[hull.vertices]
                        centroid = np.mean(vertices, axis=0)
                        
                        # 存储障碍物信息
                        self.obstacles.append({
                            'id': cluster_id,
                            'centroid': centroid,
                            'vertices': vertices,
                            'height': height,
                            'min_z': min_z,
                            'max_z': max_z,
                            'points': cluster_points
                        })
                    except Exception as e:
                        self.logger.warning(f"凸包计算失败: {str(e)}")
                        # 凸包计算失败时使用简单边界框
                        min_xy = np.min(cluster_points[:, :2], axis=0)
                        max_xy = np.max(cluster_points[:, :2], axis=0)
                        vertices = np.array([
                            [min_xy[0], min_xy[1]],
                            [max_xy[0], min_xy[1]],
                            [max_xy[0], max_xy[1]],
                            [min_xy[0], max_xy[1]]
                        ])
                        centroid = np.mean(vertices, axis=0)
                        self.obstacles.append({
                            'id': cluster_id,
                            'centroid': centroid,
                            'vertices': vertices,
                            'height': height,
                            'min_z': min_z,
                            'max_z': max_z,
                            'points': cluster_points
                        })
        except Exception as e:
            self.logger.error(f"障碍物识别失败: {str(e)}")
    
    def _identify_water_bodies(self):
        """识别水体区域"""
        self.water_bodies = []
        if len(self.terrain_points) < 3:
            return
            
        # 使用DBSCAN聚类低洼区域
        low_points = self.terrain_points[self.terrain_points[:, 2] < self.water_threshold]
        if len(low_points) < 3:
            return
            
        try:
            clustering = DBSCAN(eps=3.0, min_samples=5).fit(low_points)
            labels = clustering.labels_
            
            water_clusters = {}
            for i, label in enumerate(labels):
                if label == -1:
                    continue
                if label not in water_clusters:
                    water_clusters[label] = []
                water_clusters[label].append(low_points[i])
            
            for cluster_id, points in water_clusters.items():
                if len(points) < 10:
                    continue
                    
                cluster_points = np.array(points)
                hull = ConvexHull(cluster_points[:, :2])
                vertices = cluster_points[hull.vertices]
                
                self.water_bodies.append({
                    'id': cluster_id,
                    'points': cluster_points,
                    'vertices': vertices,
                    'centroid': np.mean(vertices, axis=0)
                })
        except Exception as e:
            self.logger.error(f"水体识别失败: {str(e)}")
    
    def _identify_vegetation_zones(self):
        """识别植被区域"""
        self.vegetation_zones = []
        if len(self.terrain_points) < 3:
            return
            
        # 创建网格分析点云密度
        grid_size = 5.0
        min_xy = np.min(self.terrain_points[:, :2], axis=0)
        max_xy = np.max(self.terrain_points[:, :2], axis=0)
        
        x_bins = int((max_xy[0] - min_xy[0]) / grid_size) + 1
        y_bins = int((max_xy[1] - min_xy[1]) / grid_size) + 1
        
        density_grid = np.zeros((x_bins, y_bins))
        
        for point in self.terrain_points:
            x_idx = int((point[0] - min_xy[0]) / grid_size)
            y_idx = int((point[1] - min_xy[1]) / grid_size)
            
            if 0 <= x_idx < x_bins and 0 <= y_idx < y_bins:
                density_grid[x_idx, y_idx] += 1
        
        # 识别高密度区域
        for i in range(x_bins):
            for j in range(y_bins):
                if density_grid[i, j] > self.vegetation_threshold * grid_size**2:
                    x = min_xy[0] + i * grid_size
                    y = min_xy[1] + j * grid_size
                    self.vegetation_zones.append({
                        'x': x,
                        'y': y,
                        'width': grid_size,
                        'height': grid_size,
                        'density': density_grid[i, j]
                    })
    
    def _calculate_complexity_map(self, grid_size=5.0):
        """计算地形复杂度热力图"""
        if len(self.terrain_points) < 10:
            self.complexity_map = None
            return
            
        # 创建网格
        min_xy = np.min(self.terrain_points[:, :2], axis=0)
        max_xy = np.max(self.terrain_points[:, :2], axis=0)
        
        x_bins = int((max_xy[0] - min_xy[0]) / grid_size) + 1
        y_bins = int((max_xy[1] - min_xy[1]) / grid_size) + 1
        
        # 初始化网格
        grid = np.zeros((x_bins, y_bins))
        counts = np.zeros((x_bins, y_bins))
        
        # 分配点云到网格
        for point in self.terrain_points:
            x_idx = int((point[0] - min_xy[0]) / grid_size)
            y_idx = int((point[1] - min_xy[1]) / grid_size)
            
            if 0 <= x_idx < x_bins and 0 <= y_idx < y_bins:
                grid[x_idx, y_idx] += point[2]
                counts[x_idx, y_idx] += 1
        
        # 计算平均高度
        avg_heights = np.divide(grid, counts, out=np.zeros_like(grid), where=counts!=0)
        
        # 计算局部粗糙度
        roughness_map = np.zeros((x_bins, y_bins))
        for i in range(1, x_bins-1):
            for j in range(1, y_bins-1):
                if counts[i, j] > 0:
                    # 取3x3邻域
                    neighborhood = avg_heights[i-1:i+2, j-1:j+2]
                    # 计算标准差作为粗糙度
                    roughness_map[i, j] = np.std(neighborhood) if neighborhood.size > 0 else 0
        
        # 计算局部障碍物密度
        obstacle_density_map = np.zeros((x_bins, y_bins))
        for obstacle in self.obstacles:
            centroid = obstacle['centroid']
            x_idx = int((centroid[0] - min_xy[0]) / grid_size)
            y_idx = int((centroid[1] - min_xy[1]) / grid_size)
            
            if 0 <= x_idx < x_bins and 0 <= y_idx < y_bins:
                obstacle_density_map[x_idx, y_idx] += 1
        
        # 归一化
        if np.max(obstacle_density_map) > 0:
            obstacle_density_map /= np.max(obstacle_density_map)
        
        # 综合复杂度
        complexity_map = (0.6 * roughness_map + 0.4 * obstacle_density_map) * 10
        
        # 存储结果
        self.complexity_map = {
            'data': complexity_map,
            'min_xy': min_xy,
            'max_xy': max_xy,
            'grid_size': grid_size
        }
    
    def _generate_thermal_map(self):
        """生成热力图表示地形能量分布"""
        if len(self.terrain_points) < 10:
            self.thermal_map = None
            return
            
        # 创建网格
        grid_size = 10.0
        min_xy = np.min(self.terrain_points[:, :2], axis=0)
        max_xy = np.max(self.terrain_points[:, :2], axis=0)
        
        x_bins = int((max_xy[0] - min_xy[0]) / grid_size) + 1
        y_bins = int((max_xy[1] - min_xy[1]) / grid_size) + 1
        
        # 初始化网格
        thermal_grid = np.zeros((x_bins, y_bins))
        
        # 计算每个网格的平均高度和光照
        for point in self.terrain_points:
            x_idx = int((point[0] - min_xy[0]) / grid_size)
            y_idx = int((point[1] - min_xy[1]) / grid_size)
            
            if 0 <= x_idx < x_bins and 0 <= y_idx < y_bins:
                # 简单模型：南坡更温暖
                slope_factor = 1.0
                if point[0] > 0:  # 假设正东方向
                    slope_factor += point[0] * 0.01
                thermal_grid[x_idx, y_idx] += point[2] * slope_factor
        
        # 归一化
        if np.max(thermal_grid) > 0:
            thermal_grid /= np.max(thermal_grid)
        
        self.thermal_map = {
            'data': thermal_grid,
            'min_xy': min_xy,
            'grid_size': grid_size
        }
    
    def _track_moving_obstacles(self):
        """追踪移动障碍物"""
        if not self.obstacles:
            return
            
        # 清空移动障碍物列表
        self.moving_obstacles = []
        
        # 对每个障碍物进行追踪
        for obstacle in self.obstacles:
            obstacle_id = obstacle['id']
            current_pos = obstacle['centroid']
            
            # 获取历史位置
            history = self.obstacle_history[obstacle_id]
            
            if history:
                # 计算平均速度
                last_pos = history[-1]['position']
                last_time = history[-1]['time']
                time_diff = time.time() - last_time
                
                if time_diff > 0:
                    # 计算速度向量
                    velocity = (current_pos - last_pos) / time_diff
                    
                    # 如果速度超过阈值，标记为移动障碍物
                    speed = np.linalg.norm(velocity[:2])
                    if speed > 0.5:  # 速度阈值0.5 m/s
                        obstacle['velocity'] = velocity
                        obstacle['speed'] = speed
                        self.moving_obstacles.append(obstacle)
            
            # 更新历史记录
            self.obstacle_history[obstacle_id].append({
                'position': current_pos.copy(),
                'time': time.time()
            })
            
            # 只保留最近5个记录
            if len(self.obstacle_history[obstacle_id]) > 5:
                self.obstacle_history[obstacle_id].pop(0)
    
    def analyze_terrain_complexity(self):
        """分析地形复杂度（综合多种特征）"""
        # 如果没有点云数据，返回最低复杂度
        if not self.terrain_features or not self.terrain_points.size > 0:
            return 0.0
        
        # 从地形特征计算
        roughness = self.terrain_features.get('roughness', 0)
        slope = self.terrain_features.get('avg_slope', 0)
        height_range = self.terrain_features.get('height_range', 0)
        obstacle_density = self.terrain_features.get('obstacle_density', 0)
        traversable = self.terrain_features.get('traversable_area', 1.0)
        
        # 综合复杂度公式（加权和）
        complexity = (
            0.15 * roughness * 5 +
            0.1 * slope / 10 +
            0.1 * height_range +
            0.15 * obstacle_density * 100
        )
        
        # 考虑可通行区域（可通行区域越少，复杂度越高）
        complexity *= (1.5 - traversable)
        
        # 增加移动障碍物的复杂度影响
        if self.moving_obstacles:
            max_speed = max(obs.get('speed', 0) for obs in self.moving_obstacles)
            complexity += max_speed * 0.5
            
        return complexity
    
    def recommend_altitude(self):
        """基于地形复杂度推荐飞行高度（仅对无人机有效）"""
        if self.robot_type != "drone":
            return self.position[2]
            
        complexity = self.analyze_terrain_complexity()
        
        # 获取地形最高点
        max_height = np.max(self.terrain_points[:, 2]) if self.terrain_points.size > 0 else 0
        
        # 基本安全高度（最高障碍物+安全裕度）
        min_safe_altitude = max_height + self.safety_margin if max_height > 0 else 5.0
        
        # 根据复杂度调整高度
        if complexity < 2.0:
            # 平坦地形：保持当前高度或略高于安全高度
            recommended = max(min_safe_altitude, self.position[2])
        elif complexity < 5.0:
            # 中等地形：在安全高度基础上增加复杂度补偿
            recommended = min_safe_altitude + complexity
        else:
            # 复杂地形：显著增加高度
            recommended = min_safe_altitude + complexity * 1.5
        
        # 限制高度范围
        recommended = min(self.max_altitude, max(self.min_altitude, recommended))
        
        return recommended
    
    def plan_path(self, target, altitude=None):
        """
        规划安全路径
        
        参数:
            target: 目标位置 [x, y, z]
            altitude: 指定飞行高度（仅对无人机有效）
        
        返回:
            路径点列表
        """
        if self.robot_type == "drone" and altitude is None:
            altitude = self.recommend_altitude()
        
        # 创建路径缓存键
        cache_key = (tuple(self.position), tuple(target), round(altitude if altitude else 0, 1))
        if cache_key in self.path_cache:
            return self.path_cache[cache_key]
        
        # 创建简化导航网格
        graph = self._create_navigation_graph(altitude)
        
        # 查找最近节点
        start_node = self._find_nearest_node(graph, self.position)
        end_node = self._find_nearest_node(graph, target)
        
        # 使用A*算法查找路径
        path = self._a_star_search(graph, start_node, end_node, altitude)
        
        # 缓存结果
        if path:
            self.path_cache[cache_key] = path
        
        return path
    
    def _create_navigation_graph(self, altitude):
        """创建简化导航网格图（用于路径规划）"""
        graph = {}
        
        # 1. 创建网格点
        grid_size = self.resolution * 5  # 更大的网格尺寸
        min_xy = np.min(self.terrain_points[:, :2], axis=0) if self.terrain_points.size > 0 else np.array([0, 0])
        max_xy = np.max(self.terrain_points[:, :2], axis=0) if self.terrain_points.size > 0 else np.array([10, 10])
        
        # 创建网格点
        x_points = np.arange(min_xy[0], max_xy[0] + grid_size, grid_size)
        y_points = np.arange(min_xy[1], max_xy[1] + grid_size, grid_size)
        
        nodes = []
        for x in x_points:
            for y in y_points:
                # 地面机器人使用地形高度
                if self.robot_type == "ground":
                    # 查找最近的地形点高度
                    distances = np.linalg.norm(self.terrain_points[:, :2] - [x, y], axis=1)
                    if len(distances) > 0:
                        min_idx = np.argmin(distances)
                        z = self.terrain_points[min_idx, 2] + 0.2  # 离地高度
                    else:
                        z = 0
                else:
                    z = altitude
                
                # 检查是否在障碍物内
                in_obstacle = False
                for obstacle in self.obstacles:
                    if self._point_in_polygon((x, y), obstacle['vertices'][:, :2]): 
                        in_obstacle = True
                        break
                
                if not in_obstacle:
                    nodes.append((x, y, z))
        
        # 2. 创建图结构
        for i, node in enumerate(nodes):
            neighbors = []
            for j, other in enumerate(nodes):
                if i == j:
                    continue
                # 计算距离
                dist = np.linalg.norm(np.array(node) - np.array(other))
                # 只连接一定距离内的节点
                if dist <= grid_size * 1.5:
                    # 检查视线是否被阻挡
                    if not self._line_of_sight_blocked(node, other):
                        neighbors.append((j, dist))
            graph[i] = {'pos': node, 'neighbors': neighbors}
        
        return graph
    
    def _point_in_polygon(self, point, polygon):
        """判断点是否在多边形内（射线法）"""
        if len(polygon) < 3:
            return False
            
        # 确保多边形顶点是二维的
        if polygon.shape[1] > 2:
            polygon = polygon[:, :2]
        
        x, y = point
        n = len(polygon)
        inside = False
        p1x, p1y = polygon[0]
        for i in range(n+1):
            p2x, p2y = polygon[i % n]
            if y > min(p1y, p2y):
                if y <= max(p1y, p2y):
                    if x <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (y-p1y)*(p2x-p1x)/(p2y-p1y)+p1x
                        if p1x == p2x or x <= xinters:
                            inside = not inside
            p1x, p1y = p2x, p2y
        return inside
    
    def _line_of_sight_blocked(self, p1, p2):
        """检查两点间视线是否被障碍物阻挡"""
        for obstacle in self.obstacles:
            # 简化：检查线段是否与障碍物凸包相交
            vertices = obstacle['vertices']
            n = len(vertices)
            for i in range(n):
                a = vertices[i]
                b = vertices[(i+1) % n]
                if self._line_segments_intersect(p1[:2], p2[:2], a, b):
                    return True
        return False
    
    def _line_segments_intersect(self, a, b, c, d):
        """检查两条线段是否相交"""
        def ccw(A, B, C):
            return (C[1]-A[1]) * (B[0]-A[0]) > (B[1]-A[1]) * (C[0]-A[0])
        return ccw(a, c, d) != ccw(b, c, d) and ccw(a, b, c) != ccw(a, b, d)
    
    def _find_nearest_node(self, graph, point):
        """在图中查找最近节点"""
        min_dist = float('inf')
        nearest_id = -1
        for node_id, node in graph.items():
            dist = np.linalg.norm(np.array(node['pos']) - np.array(point))
            if dist < min_dist:
                min_dist = dist
                nearest_id = node_id
        return nearest_id
    
    def _a_star_search(self, graph, start, goal, altitude):
        """A*路径搜索算法"""
        # 初始化数据结构
        open_set = []
        heapq.heappush(open_set, (0, start))
        came_from = {}
        g_score = {node: float('inf') for node in graph}
        g_score[start] = 0
        f_score = {node: float('inf') for node in graph}
        f_score[start] = np.linalg.norm(np.array(graph[start]['pos']) - np.array(graph[goal]['pos']))
        
        while open_set:
            current_f, current = heapq.heappop(open_set)
            
            if current == goal:
                # 重构路径
                path = []
                while current in came_from:
                    path.append(graph[current]['pos'])
                    current = came_from[current]
                path.reverse()
                path.insert(0, graph[start]['pos'])
                path.append(graph[goal]['pos'])
                return path
            
            for neighbor, dist in graph[current]['neighbors']:
                tentative_g = g_score[current] + dist
                
                if tentative_g < g_score[neighbor]:
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g
                    f_score[neighbor] = tentative_g + np.linalg.norm(
                        np.array(graph[neighbor]['pos']) - np.array(graph[goal]['pos']))
                    heapq.heappush(open_set, (f_score[neighbor], neighbor))
        
        return []  # 未找到路径
    
    def navigate_to(self, target):
        """
        导航到指定位置
        
        参数:
            target: 目标位置 [x, y, z]
        """
        self.mode = "navigating"
        self.logger.info(f"开始导航到目标位置: {target}")
        
        # 规划路径
        altitude = self.recommend_altitude() if self.robot_type == "drone" else None
        path = self.plan_path(target, altitude)
        
        if not path:
            self.logger.warning("无法找到安全路径")
            self.mode = "idle"
            return False
        
        self.current_path = path
        self.current_waypoint_idx = 0
        self.target_position = target
        return True
    
    def explore_area(self, area_size):
        """
        探索指定区域
        
        参数:
            area_size: 区域大小 [width, height]
        """
        self.mode = "exploring"
        self.logger.info(f"开始探索 {area_size[0]}x{area_size[1]} 区域")
        
        # 生成探索路径（简化实现）
        # 实际应用中应使用更复杂的探索算法
        start_x, start_y = self.position[0], self.position[1]
        width, height = area_size
        
        # 生成网格路径
        path = []
        grid_size = 5.0
        for i in range(int(width / grid_size)):
            x = start_x + i * grid_size
            for j in range(int(height / grid_size)):
                y = start_y + (j if i % 2 == 0 else height - j * grid_size)
                altitude = self.recommend_altitude() if self.robot_type == "drone" else None
                path.append([x, y, altitude if altitude else self.position[2]])
        
        self.current_path = path
        self.current_waypoint_idx = 0
        return True
    
    def return_to_base(self, base_position):
        """
        返回基地位置
        
        参数:
            base_position: 基地位置 [x, y, z]
        """
        self.mode = "returning"
        self.logger.info("返回基地")
        return self.navigate_to(base_position)
    
    def find_optimal_landing_zone(self, min_size=10.0):
        """寻找最佳着陆区域（仅对无人机有效）"""
        if self.robot_type != "drone" or not self.terrain_features:
            return None
            
        best_zone = None
        best_score = -float('inf')
        
        # 分析可通行区域
        min_xy = np.min(self.terrain_points[:, :2], axis=0)
        max_xy = np.max(self.terrain_points[:, :2], axis=0)
        
        grid_size = 5.0
        x_bins = int((max_xy[0] - min_xy[0]) / grid_size) + 1
        y_bins = int((max_xy[1] - min_xy[1]) / grid_size) + 1
        
        for i in range(x_bins):
            for j in range(y_bins):
                center_x = min_xy[0] + (i + 0.5) * grid_size
                center_y = min_xy[1] + (j + 0.5) * grid_size
                zone_points = []
                
                # 收集区域内的点
                for point in self.terrain_points:
                    if (abs(point[0] - center_x) <= min_size/2 and 
                        abs(point[1] - center_y) <= min_size/2):
                        zone_points.append(point)
                
                if len(zone_points) < 5:
                    continue
                    
                zone_points = np.array(zone_points)
                
                # 计算区域特征
                height_range = np.max(zone_points[:, 2]) - np.min(zone_points[:, 2])
                avg_height = np.mean(zone_points[:, 2])
                flatness = 1.0 / (height_range + 1e-5)
                
                # 计算障碍物距离
                obstacle_dist = float('inf')
                for obstacle in self.obstacles:
                    dist = np.linalg.norm(obstacle['centroid'][:2] - [center_x, center_y])
                    if dist < obstacle_dist:
                        obstacle_dist = dist
                
                # 计算得分
                score = (flatness * 0.6 + 
                         np.exp(-obstacle_dist/10) * 0.4)
                
                if score > best_score:
                    best_score = score
                    best_zone = {
                        'center': (center_x, center_y, avg_height),
                        'size': min_size,
                        'score': score,
                        'height_range': height_range,
                        'obstacle_distance': obstacle_dist
                    }
        
        self.landing_zone = best_zone
        return best_zone
    
    def update_position(self, dt):
        """
        更新机器人位置（基于当前路径和速度）
        
        参数:
            dt: 时间步长(秒)
        """
        if self.mode == "idle":
            return False
            
        if not self.current_path or self.current_waypoint_idx >= len(self.current_path):
            self.mode = "idle"
            self.logger.info("到达目的地")
            return False
        
        # 获取当前目标航点
        target_waypoint = np.array(self.current_path[self.current_waypoint_idx])
        
        # 计算到目标的方向向量
        direction = target_waypoint - self.position
        distance = np.linalg.norm(direction)
        
        if distance < 1.0:  # 到达航点阈值
            self.current_waypoint_idx += 1
            if self.current_waypoint_idx < len(self.current_path):
                target_waypoint = np.array(self.current_path[self.current_waypoint_idx])
                direction = target_waypoint - self.position
                distance = np.linalg.norm(direction)
            else:
                self.mode = "idle"
                self.logger.info("到达目的地")
                return False
        
        # 计算速度方向
        if distance > 0:
            direction /= distance
            
        # 计算加速度（简单模型）
        acceleration = np.zeros(3)
        if self.robot_type == "drone":
            # 无人机可以三维移动
            acceleration = direction * 2.0  # 加速度 2 m/s²
        else:
            # 地面机器人只能在XY平面移动
            direction[2] = 0
            acceleration = direction * 1.0  # 加速度 1 m/s²
        
        # 更新速度
        self.velocity += acceleration * dt
        
        # 限制最大速度
        speed = np.linalg.norm(self.velocity)
        if speed > self.max_speed:
            self.velocity = (self.velocity / speed) * self.max_speed
        
        # 更新位置
        self.position += self.velocity * dt
        
        # 地面机器人贴地
        if self.robot_type == "ground":
            # 查找最近的地形点高度
            distances = np.linalg.norm(self.terrain_points[:, :2] - self.position[:2], axis=1)
            if len(distances) > 0:
                min_idx = np.argmin(distances)
                self.position[2] = self.terrain_points[min_idx, 2] + 0.2  # 离地高度
        
        # 更新电池（简单模型）
        self.battery_level -= 0.01 * dt * (1 + speed/self.max_speed)
        
        # 检查低电量
        if self.battery_level < 20.0 and self.mode != "returning":
            self.logger.warning("电量低于20%，建议返回基地")
        
        return True
    
    def emergency_stop(self):
        """紧急停止"""
        self.velocity = np.zeros(3)
        self.mode = "idle"
        self.logger.warning("紧急停止")
    
    def get_status(self):
        """获取机器人状态"""
        return {
            "position": self.position.tolist(),
            "orientation": self.orientation.tolist(),
            "velocity": self.velocity.tolist(),
            "battery": self.battery_level,
            "mode": self.mode,
            "terrain_complexity": self.terrain_features.get("complexity", 0),
            "obstacle_count": len(self.obstacles),
            "path_progress": f"{self.current_waypoint_idx}/{len(self.current_path) if self.current_path else 0}"
        }

class RobotVisualizer:
    """移动机器人可视化类"""
    
    def __init__(self, robot):
        self.robot = robot
        self.fig = plt.figure(figsize=(16, 10))
        self.fig.suptitle(f'移动机器人仿真系统 - {"无人机" if robot.robot_type == "drone" else "无人车"}', fontsize=16)
        
        # 使用GridSpec创建复杂的布局
        gs = gridspec.GridSpec(2, 3, figure=self.fig)
        
        # 创建各个子图
        self.ax_3d = self.fig.add_subplot(gs[:, 0], projection='3d')
        self.ax_2d = self.fig.add_subplot(gs[0, 1:])
        self.ax_complexity = self.fig.add_subplot(gs[1, 1])
        self.ax_status = self.fig.add_subplot(gs[1, 2])
        
        # 设置子图标题
        self.ax_3d.set_title('3D环境视图')
        self.ax_2d.set_title('2D地图视图')
        self.ax_complexity.set_title('地形复杂度热力图')
        self.ax_status.set_title('机器人状态信息')
        
        # 初始化可视化元素
        self.init_visuals()
        
        # 添加图例
        self.add_legend()
    
    def init_visuals(self):
        """初始化可视化元素"""
        # 3D视图
        self.ax_3d.set_xlabel('X (m)')
        self.ax_3d.set_ylabel('Y (m)')
        self.ax_3d.set_zlabel('Z (m)')
        
        # 地形点云
        self.terrain_scatter_3d = self.ax_3d.scatter([], [], [], c='gray', s=1, alpha=0.5)
        
        # 路径
        self.path_line_3d, = self.ax_3d.plot([], [], [], 'r-', linewidth=2, label='规划路径')
        
        # 机器人位置
        self.robot_pos_3d, = self.ax_3d.plot([], [], [], 'bo', markersize=8, label='机器人')
        
        # 目标位置
        self.target_pos_3d, = self.ax_3d.plot([], [], [], 'g*', markersize=10, label='目标点')
        
        # 2D视图
        self.ax_2d.set_xlabel('X (m)')
        self.ax_2d.set_ylabel('Y (m)')
        self.ax_2d.grid(True)
        
        # 地形点云（2D）
        self.terrain_scatter_2d = self.ax_2d.scatter([], [], c='gray', s=1, alpha=0.3)
        
        # 路径（2D）
        self.path_line_2d, = self.ax_2d.plot([], [], 'r-', linewidth=2)
        
        # 机器人位置（2D）
        self.robot_pos_2d, = self.ax_2d.plot([], [], 'bo', markersize=8)
        
        # 目标位置（2D）
        self.target_pos_2d, = self.ax_2d.plot([], [], 'g*', markersize=10)
        
        # 障碍物集合
        self.obstacle_patches = []
        self.water_patches = []
        self.vegetation_patches = []
        
        # 移动障碍物
        self.moving_obstacles_arrows = []
        
        # 热力图
        self.complexity_im = self.ax_complexity.imshow(np.zeros((10, 10)), cmap='jet', 
                                                      origin='lower', aspect='auto')
        plt.colorbar(self.complexity_im, ax=self.ax_complexity, label='复杂度')
        
        # 状态信息
        self.status_text = self.ax_status.text(0.05, 0.95, '', transform=self.ax_status.transAxes, 
                                              fontsize=10, verticalalignment='top')
        self.ax_status.axis('off')
    
    def add_legend(self):
        """添加图例"""
        # 创建自定义图例元素
        from matplotlib.lines import Line2D
        legend_elements = [
            Line2D([0], [0], color='blue', marker='o', linestyle='None', markersize=8, label='机器人'),
            Line2D([0], [0], color='green', marker='*', linestyle='None', markersize=10, label='目标点'),
            Line2D([0], [0], color='red', linestyle='-', linewidth=2, label='规划路径'),
            Line2D([0], [0], color='red', marker='s', linestyle='None', markersize=8, label='障碍物'),
            Line2D([0], [0], color='blue', marker='s', linestyle='None', markersize=8, label='水体'),
            Line2D([0], [0], color='green', marker='s', linestyle='None', markersize=8, label='植被'),
            Line2D([0], [0], color='orange', marker='>', linestyle='None', markersize=8, label='移动障碍物')
        ]
        
        # 添加图例
        self.ax_2d.legend(handles=legend_elements, loc='upper right', fontsize=8)
    
    def update(self):
        """更新可视化"""
        # 清除之前的障碍物、水体等
        self.clear_patches()
        
        # 更新地形点云
        self.update_terrain()
        
        # 更新障碍物
        self.update_obstacles()
        
        # 更新水体
        self.update_water_bodies()
        
        # 更新植被区域
        self.update_vegetation_zones()
        
        # 更新移动障碍物
        self.update_moving_obstacles()
        
        # 更新路径
        self.update_path()
        
        # 更新机器人位置
        self.update_robot_position()
        
        # 更新热力图
        self.update_complexity_map()
        
        # 更新状态信息
        self.update_status()
        
        # 调整视图范围
        self.adjust_view()
        
        # 重绘
        plt.draw()
        plt.pause(0.01)
    
    def clear_patches(self):
        """清除之前的可视化元素"""
        # 清除障碍物
        for patch in self.obstacle_patches:
            patch.remove()
        self.obstacle_patches = []
        
        # 清除水体
        for patch in self.water_patches:
            patch.remove()
        self.water_patches = []
        
        # 清除植被
        for patch in self.vegetation_patches:
            patch.remove()
        self.vegetation_patches = []
        
        # 清除移动障碍物箭头
        for arrow in self.moving_obstacles_arrows:
            arrow.remove()
        self.moving_obstacles_arrows = []
    
    def update_terrain(self):
        """更新地形点云"""
        if self.robot.terrain_points.size > 0:
            # 3D视图
            self.terrain_scatter_3d._offsets3d = (self.robot.terrain_points[:, 0], 
                                                 self.robot.terrain_points[:, 1], 
                                                 self.robot.terrain_points[:, 2])
            
            # 2D视图
            self.terrain_scatter_2d.set_offsets(self.robot.terrain_points[:, :2])
    
    def update_obstacles(self):
        """更新障碍物可视化"""
        for obstacle in self.robot.obstacles:
            vertices = obstacle['vertices'][:, :2]
            height = obstacle['height']
            
            # 2D视图 - 多边形
            polygon = Polygon(vertices, closed=True, fill=True, color='red', alpha=0.3)
            self.ax_2d.add_patch(polygon)
            self.obstacle_patches.append(polygon)
            
            # 3D视图 - 多边形柱体
            for i in range(len(vertices)):
                a = vertices[i]
                b = vertices[(i+1) % len(vertices)]
                # 创建侧面
                x = [a[0], b[0], b[0], a[0]]
                y = [a[1], b[1], b[1], a[1]]
                z = [obstacle['min_z'], obstacle['min_z'], obstacle['max_z'], obstacle['max_z']]
                verts = [list(zip(x, y, z))]
                poly3d = Poly3DCollection(verts, alpha=0.3, color='red')
                self.ax_3d.add_collection3d(poly3d)
                self.obstacle_patches.append(poly3d)
    
    def update_water_bodies(self):
        """更新水体可视化"""
        for water in self.robot.water_bodies:
            vertices = water['vertices'][:, :2]
            
            # 2D视图 - 多边形
            polygon = Polygon(vertices, closed=True, fill=True, color='blue', alpha=0.3)
            self.ax_2d.add_patch(polygon)
            self.water_patches.append(polygon)
            
            # 3D视图 - 多边形
            x = vertices[:, 0]
            y = vertices[:, 1]
            z = np.ones(len(vertices)) * self.robot.water_threshold
            verts = [list(zip(x, y, z))]
            poly3d = Poly3DCollection(verts, alpha=0.3, color='blue')
            self.ax_3d.add_collection3d(poly3d)
            self.water_patches.append(poly3d)
    
    def update_vegetation_zones(self):
        """更新植被区域可视化"""
        for veg in self.robot.vegetation_zones:
            # 2D视图 - 矩形
            rect = Rectangle((veg['x'], veg['y']), veg['width'], veg['height'], 
                             color='green', alpha=0.3)
            self.ax_2d.add_patch(rect)
            self.vegetation_patches.append(rect)
            
            # 3D视图 - 矩形
            x = [veg['x'], veg['x'] + veg['width'], veg['x'] + veg['width'], veg['x']]
            y = [veg['y'], veg['y'], veg['y'] + veg['height'], veg['y'] + veg['height']]
            z = [0, 0, 0, 0]
            verts = [list(zip(x, y, z))]
            poly3d = Poly3DCollection(verts, alpha=0.3, color='green')
            self.ax_3d.add_collection3d(poly3d)
            self.vegetation_patches.append(poly3d)
    
    def update_moving_obstacles(self):
        """更新移动障碍物可视化"""
        for obstacle in self.robot.moving_obstacles:
            if 'velocity' in obstacle:
                pos = obstacle['centroid']
                vel = obstacle['velocity']
                speed = obstacle['speed']
                
                # 2D视图 - 箭头
                arrow = self.ax_2d.arrow(pos[0], pos[1], vel[0]*2, vel[1]*2, 
                                        head_width=1.0, head_length=1.5, 
                                        fc='orange', ec='orange')
                self.moving_obstacles_arrows.append(arrow)
                
                # 添加速度标签
                text = self.ax_2d.text(pos[0], pos[1], f'{speed:.1f}m/s', 
                                      fontsize=8, color='orange')
                self.moving_obstacles_arrows.append(text)
    
    def update_path(self):
        """更新路径可视化"""
        if self.robot.current_path:
            path_array = np.array(self.robot.current_path)
            
            # 3D路径
            self.path_line_3d.set_data(path_array[:, 0], path_array[:, 1])
            self.path_line_3d.set_3d_properties(path_array[:, 2])
            
            # 2D路径
            self.path_line_2d.set_data(path_array[:, 0], path_array[:, 1])
            
            # 更新目标位置
            target = path_array[-1]
            self.target_pos_3d.set_data([target[0]], [target[1]])
            self.target_pos_3d.set_3d_properties([target[2]])
            
            self.target_pos_2d.set_data([target[0]], [target[1]])
    
    def update_robot_position(self):
        """更新机器人位置"""
        # 3D位置
        self.robot_pos_3d.set_data([self.robot.position[0]], [self.robot.position[1]])
        self.robot_pos_3d.set_3d_properties([self.robot.position[2]])
        
        # 2D位置
        self.robot_pos_2d.set_data([self.robot.position[0]], [self.robot.position[1]])
        
        # 添加方向指示
        yaw = self.robot.orientation[2]
        dx = math.cos(yaw) * 2
        dy = math.sin(yaw) * 2
        
        # 清除旧的方向箭头
        for arrow in self.moving_obstacles_arrows:
            if hasattr(arrow, 'get_label') and arrow.get_label() == 'direction':
                arrow.remove()
        
        # 添加新的方向箭头
        arrow = self.ax_2d.arrow(self.robot.position[0], self.robot.position[1], 
                                dx, dy, head_width=0.5, head_length=0.8, 
                                fc='blue', ec='blue', label='direction')
        self.moving_obstacles_arrows.append(arrow)
    
    def update_complexity_map(self):
        """更新地形复杂度热力图"""
        if self.robot.complexity_map is not None:
            complexity_map = self.robot.complexity_map['data']
            min_xy = self.robot.complexity_map['min_xy']
            grid_size = self.robot.complexity_map['grid_size']
            
            # 计算范围
            extent = [min_xy[0], min_xy[0] + complexity_map.shape[0]*grid_size,
                     min_xy[1], min_xy[1] + complexity_map.shape[1]*grid_size]
            
            self.complexity_im.set_data(complexity_map)
            self.complexity_im.set_extent(extent)
            self.complexity_im.set_clim(vmin=np.min(complexity_map), vmax=np.max(complexity_map))
    
    def update_status(self):
        """更新状态信息"""
        status = self.robot.get_status()
        text = f"模式: {status['mode']}\n"
        text += f"位置: ({status['position'][0]:.1f}, {status['position'][1]:.1f}, {status['position'][2]:.1f})\n"
        text += f"速度: ({status['velocity'][0]:.1f}, {status['velocity'][1]:.1f}, {status['velocity'][2]:.1f}) m/s\n"
        text += f"电池: {status['battery']:.1f}%\n"
        text += f"地形复杂度: {status['terrain_complexity']:.2f}\n"
        text += f"障碍物数量: {status['obstacle_count']}\n"
        text += f"路径进度: {status['path_progress']}"
        
        self.status_text.set_text(text)
    
    def adjust_view(self):
        """调整视图范围"""
        if self.robot.terrain_points.size > 0:
            min_x, min_y = np.min(self.robot.terrain_points[:, :2], axis=0)
            max_x, max_y = np.max(self.robot.terrain_points[:, :2], axis=0)
            min_z, max_z = np.min(self.robot.terrain_points[:, 2]), np.max(self.robot.terrain_points[:, 2])
            
            margin = 10.0
            
            # 2D视图范围
            self.ax_2d.set_xlim(min_x - margin, max_x + margin)
            self.ax_2d.set_ylim(min_y - margin, max_y + margin)
            
            # 3D视图范围
            self.ax_3d.set_xlim(min_x - margin, max_x + margin)
            self.ax_3d.set_ylim(min_y - margin, max_y + margin)
            self.ax_3d.set_zlim(min_z - margin, max_z + margin)
            
            # 热力图范围
            if self.robot.complexity_map is not None:
                self.ax_complexity.set_xlim(min_x - margin, max_x + margin)
                self.ax_complexity.set_ylim(min_y - margin, max_y + margin)

def main():
    """主函数 - 运行机器人仿真和可视化"""
    # 创建无人机实例
    drone = UnifiedMobileRobot(robot_type="drone")
    
    # 创建可视化器
    visualizer = RobotVisualizer(drone)
    
    # 设置初始点云数据
    x = np.linspace(-50, 50, 100)
    y = np.linspace(-50, 50, 100)
    xx, yy = np.meshgrid(x, y)
    
    # 创建有地形特征的点云
    zz = np.sin(xx/10) * np.cos(yy/10) * 5 + 10
    
    # 添加一些障碍物
    zz[30:40, 30:40] += 8  # 方形障碍物
    zz[60:70, 20:30] += 6  # 另一个障碍物
    
    # 添加水体
    zz[10:20, 60:70] = -2  # 低洼区域
    
    # 创建点云
    points = np.vstack([xx.ravel(), yy.ravel(), zz.ravel()]).T
    
    # 添加随机噪声
    points += np.random.randn(*points.shape) * 0.5
    
    # 初始传感器更新
    drone.update_sensors(points)
    
    # 设置目标位置
    target = np.array([40.0, 40.0, 15.0])
    
    # 规划路径
    drone.navigate_to(target)
    
    # 设置动画参数
    dt = 0.1  # 时间步长
    total_time = 30.0  # 总仿真时间
    steps = int(total_time / dt)
    
    # 打开交互模式
    plt.ion()
    
    # 主循环
    for i in range(steps):
        # 更新机器人位置
        drone.update_position(dt)
        
        # 定期更新传感器数据（模拟新数据）
        if i % 10 == 0:
            # 轻微改变点云
            new_points = points.copy()
            new_points[:, 2] += np.random.randn(new_points.shape[0]) * 0.2
            drone.update_sensors(new_points)
        
        # 更新可视化
        visualizer.update()
        
        # 暂停
        time.sleep(dt)
        
        # 检查是否结束
        if drone.mode == "idle":
            break
    
    # 保持窗口打开
    plt.ioff()
    plt.show()

if __name__ == "__main__":
    main()