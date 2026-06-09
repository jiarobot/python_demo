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
                    if self._point_in_polygon((x, y), obstacle['vertices']):
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
            
        x, y = point
        n = len(polygon)
        inside = False
        # 只取前两个值 (x, y)
        p1x, p1y = polygon[0][:2]
        for i in range(n+1):
            # 只取前两个值 (x, y)
            p2x, p2y = polygon[i % n][:2]
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

# 示例用法
if __name__ == "__main__":
    # 创建无人机实例
    drone = UnifiedMobileRobot(robot_type="drone")
    
    # 模拟传感器数据
    point_cloud = np.random.rand(1000, 3) * 100
    point_cloud[:, 2] = np.sin(point_cloud[:, 0]/10) * np.cos(point_cloud[:, 1]/10) * 5 + 10
    
    # 更新传感器
    drone.update_sensors(point_cloud)
    
    # 规划路径
    target = np.array([80.0, 80.0, 15.0])
    drone.navigate_to(target)
    
    # 模拟运行
    dt = 0.1  # 时间步长
    for i in range(100):
        drone.update_position(dt)
        print(f"位置: {drone.position}, 模式: {drone.mode}")
        time.sleep(dt)
        
        # 每10步更新一次传感器
        if i % 10 == 0:
            # 移动点云模拟新数据
            point_cloud += np.random.randn(1000, 3) * 0.5
            drone.update_sensors(point_cloud)
    
    # 获取状态
    print("\n最终状态:")
    print(drone.get_status())