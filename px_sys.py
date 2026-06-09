import sys
import numpy as np
import math
import time
import logging
from collections import defaultdict
import heapq
from scipy.spatial import Delaunay, ConvexHull
from scipy.spatial.distance import pdist, squareform
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QSplitter, QGroupBox, QLabel, QPushButton, QSlider, QTextEdit,
                             QListWidget, QFileDialog, QTabWidget, QDoubleSpinBox, QCheckBox,
                             QProgressBar, QComboBox, QMessageBox)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt5.QtGui import QColor, QFont, QPalette
import pyqtgraph as pg
import pyqtgraph.opengl as gl
from pyqtgraph import GradientEditorItem

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("TerrainAnalyzer")

class EnhancedTopologyAnalyzer:
    """增强版地形拓扑分析器"""
    
    def __init__(self, max_range=100.0, resolution=1.0):
        self.max_range = max_range
        self.resolution = resolution
        self.terrain_points = np.empty((0, 3))
        self.obstacles = []
        self.drone_position = np.array([0, 0, 10])
        self.terrain_features = {}
        self.path_cache = {}
        self.last_update_time = time.time()
        self.clustering_model = DBSCAN(eps=2.0, min_samples=3)
        self.color_map = {}
        self.complexity_map = None
        self.safety_margin = 3.0  # 安全裕度
        self.obstacle_threshold = 0.5  # 障碍物高度阈值
        self.dynamic_obstacle_map = None  # 动态障碍物地图
        
    def update_from_lidar(self, point_cloud, drone_position, drone_orientation):
        """从激光雷达数据更新地形模型"""
        try:
            self.drone_position = np.array(drone_position)
            
            # 点云预处理 - 转换为全局坐标系
            transformed_points = self._transform_to_global(point_cloud, drone_orientation)
            
            # 过滤点云（范围限制）
            self.terrain_points = self._filter_points(transformed_points)
            
            # 提取地形特征
            self._extract_terrain_features()
            
            # 识别障碍物
            self._identify_obstacles()
            
            # 计算地形复杂度热力图
            self._calculate_complexity_map()
            
            self.last_update_time = time.time()
            return True
        except Exception as e:
            logger.error(f"更新地形模型失败: {str(e)}")
            return False
        
    def _transform_to_global(self, point_cloud, orientation):
        """将点云数据转换为全局坐标系（考虑无人机姿态）"""
        # 简化实现 - 实际应使用旋转矩阵
        return point_cloud + self.drone_position
        
    def _filter_points(self, points):
        """过滤点云数据（范围和分辨率）"""
        if points.size == 0:
            return points
        
        # 确保点云是二维数组
        if points.ndim == 1:
            points = points.reshape(-1, 3)
        
        # 计算到无人机的距离
        distances = np.linalg.norm(points[:, :3] - self.drone_position[:3], axis=1)
        
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
                logger.warning(f"坡度计算失败: {str(e)}")
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
                        logger.warning(f"凸包计算失败: {str(e)}")
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
            logger.error(f"障碍物识别失败: {str(e)}")
    
    def _calculate_traversable_area(self):
        """计算可通行区域比例（简化实现）"""
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
    
    def compute_persistence(self):
        """计算地形持续同调特征（增强版）"""
        if len(self.terrain_points) < 10:
            return None
            
        try:
            # 1. 构建距离矩阵
            dist_matrix = squareform(pdist(self.terrain_points))
            
            # 2. 构建Vietoris-Rips复形（使用更高效的方法）
            simplices = self._build_vietoris_rips_optimized(dist_matrix)
            
            # 3. 计算持续同调
            barcodes = self._compute_barcodes_optimized(simplices)
            
            return barcodes
        except Exception as e:
            logger.error(f"持续同调计算失败: {str(e)}")
            return None
    
    def _build_vietoris_rips_optimized(self, dist_matrix, max_dim=2):
        """优化版Vietoris-Rips复形构建"""
        n = dist_matrix.shape[0]
        simplices = defaultdict(list)
        
        # 添加0-单形
        simplices[0] = [(i,) for i in range(n)]
        
        # 添加1-单形（边）
        edges = []
        for i in range(n):
            for j in range(i+1, n):
                if dist_matrix[i, j] <= self.resolution * 2:  # 使用分辨率作为距离阈值
                    edges.append((i, j))
        simplices[1] = edges
        
        # 添加2-单形（面）
        if max_dim >= 2:
            triangles = []
            # 创建邻接列表
            adj_list = [[] for _ in range(n)]
            for (i, j) in edges:
                adj_list[i].append(j)
                adj_list[j].append(i)
            
            # 查找三角形
            for i in range(n):
                neighbors = adj_list[i]
                for j_idx, j in enumerate(neighbors):
                    for k in neighbors[j_idx+1:]:
                        if dist_matrix[j, k] <= self.resolution * 2:
                            triangles.append((i, j, k))
            simplices[2] = triangles
        
        return simplices
    
    def _compute_barcodes_optimized(self, simplices):
        """优化版持续同调计算"""
        barcodes = {0: [], 1: []}
        n = len(simplices[0])
        
        # 使用并查集计算H0
        parent = list(range(n))
        rank = [0] * n
        
        def find(x):
            if parent[x] != x:
                parent[x] = find(parent[x])
            return parent[x]
        
        def union(x, y):
            rx, ry = find(x), find(y)
            if rx == ry:
                return False
            if rank[rx] < rank[ry]:
                parent[rx] = ry
            elif rank[rx] > rank[ry]:
                parent[ry] = rx
            else:
                parent[ry] = rx
                rank[rx] += 1
            return True
        
        # 处理所有边
        for edge in simplices.get(1, []):
            i, j = edge
            if 0 <= i < n and 0 <= j < n:
                union(i, j)
        
        # 计算连通分量
        components = {}
        for i in range(n):
            root = find(i)
            if root not in components:
                components[root] = []
            components[root].append(i)
        
        # 添加H0条形码
        for comp in components.values():
            barcodes[0].append((0, float('inf')))  # 无限持续
        
        # 计算H1（使用欧拉公式近似）
        if 2 in simplices:
            num_vertices = n
            num_edges = len(simplices[1])
            num_faces = len(simplices[2])
            
            # 欧拉示性数
            chi = num_vertices - num_edges + num_faces
            # 连通分量数
            num_components = len(components)
            # H1 = |edges| - |vertices| + |components| + |faces| - |cavities|
            # 简化计算：H1 ≈ edges - vertices + components
            h1_count = max(0, num_edges - num_vertices + num_components)
            barcodes[1] = [(0, 1.0)] * h1_count
        
        return barcodes
    
    def analyze_terrain_complexity(self):
        """分析地形复杂度（综合多种特征）"""
        barcodes = self.compute_persistence()
        
        # 如果没有点云数据，返回最低复杂度
        if not self.terrain_features or not barcodes:
            return 0.0
        
        # 从拓扑特征计算
        h0_count = len([b for b in barcodes[0] if b[1] == float('inf')])
        h1_count = len(barcodes.get(1, []))
        
        # 从地形特征计算
        roughness = self.terrain_features.get('roughness', 0)
        slope = self.terrain_features.get('avg_slope', 0)
        height_range = self.terrain_features.get('height_range', 0)
        obstacle_density = self.terrain_features.get('obstacle_density', 0)
        traversable = self.terrain_features.get('traversable_area', 1.0)
        
        # 综合复杂度公式（加权和）
        complexity = (
            0.2 * h0_count + 
            0.3 * h1_count +
            0.15 * roughness * 5 +
            0.1 * slope / 10 +
            0.1 * height_range +
            0.15 * obstacle_density * 100
        )
        
        # 考虑可通行区域（可通行区域越少，复杂度越高）
        complexity *= (1.5 - traversable)
        
        return complexity
    
    def recommend_flight_altitude(self, current_altitude):
        """基于地形复杂度推荐飞行高度（智能策略）"""
        complexity = self.analyze_terrain_complexity()
        
        # 获取地形最高点
        max_height = np.max(self.terrain_points[:, 2]) if self.terrain_points.size > 0 else 0
        
        # 基本安全高度（最高障碍物+安全裕度）
        safety_margin = 3.0  # 米
        min_safe_altitude = max_height + safety_margin if max_height > 0 else 5.0
        
        # 根据复杂度调整高度
        if complexity < 2.0:
            # 平坦地形：保持当前高度或略高于安全高度
            recommended = max(min_safe_altitude, current_altitude)
        elif complexity < 5.0:
            # 中等地形：在安全高度基础上增加复杂度补偿
            recommended = min_safe_altitude + complexity
        else:
            # 复杂地形：显著增加高度
            recommended = min_safe_altitude + complexity * 1.5
        
        # 限制高度范围
        min_alt = max(5.0, min_safe_altitude)
        max_alt = min(50.0, min_safe_altitude + 20.0)  # 不超过50米
        recommended = min(max_alt, max(min_alt, recommended))
        
        return recommended
    
    def find_safe_path(self, start, end, altitude=None):
        """查找安全飞行路径（A*算法实现）"""
        if not altitude:
            altitude = self.recommend_flight_altitude(start[2])
        
        # 创建路径缓存键
        cache_key = (tuple(start), tuple(end), round(altitude, 1))
        if cache_key in self.path_cache:
            return self.path_cache[cache_key]
        
        # 创建简化导航网格
        graph = self._create_navigation_graph(altitude)
        
        # 查找最近节点
        start_node = self._find_nearest_node(graph, start)
        end_node = self._find_nearest_node(graph, end)
        
        # 使用A*算法查找路径
        path = self._a_star_search(graph, start_node, end_node, altitude)
        
        # 缓存结果
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
                # 检查是否在障碍物内
                in_obstacle = False
                for obstacle in self.obstacles:
                    if self._point_in_polygon((x, y), obstacle['vertices']):
                        in_obstacle = True
                        break
                
                if not in_obstacle:
                    nodes.append((x, y, altitude))
        
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


class TerrainVisualizer(gl.GLViewWidget):
    """3D地形可视化器"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.analyzer = None
        self.drone_position = np.array([0, 0, 10])
        self.path_points = []
        self.obstacle_meshes = []
        self.setCameraPosition(distance=50, elevation=30, azimuth=-45)
        self.setBackgroundColor('k')
        self.complexity_mesh = None
        self.complexity_legend = None
        
    def set_analyzer(self, analyzer):
        self.analyzer = analyzer
        
    def update_visualization(self):
        """更新3D可视化"""
        self.clear()
        
        if self.analyzer is None or self.analyzer.terrain_points.size == 0:
            return
            
        # 添加地形点云
        points = self.analyzer.terrain_points
        
        # 确保点云是二维数组
        if points.ndim == 1:
            points = points.reshape(-1, 3)
        
        # 创建点云对象
        scatter = gl.GLScatterPlotItem(
            pos=points,
            color=(0.5, 1.0, 0.5, 0.8),
            size=0.5,
            pxMode=False
        )
        self.addItem(scatter)
        
        # 添加无人机位置
        drone_scatter = gl.GLScatterPlotItem(
            pos=np.array([self.drone_position]),
            color=(1.0, 0.0, 0.0, 1.0),
            size=1.0,
            pxMode=False
        )
        self.addItem(drone_scatter)
        
        # 添加障碍物
        for obstacle in self.analyzer.obstacles:
            points = obstacle['points']
            if len(points) < 3:
                continue
                
            # 确保点云是二维数组 (N, 3)
            if points.ndim == 1:
                points = points.reshape(-1, 3)
            
            # 确保数据类型正确
            points = points.astype(np.float32)
            
            # 创建障碍物网格
            try:
                mesh_data = gl.MeshData(vertexes=points)
                mesh = gl.GLMeshItem(
                    meshdata=mesh_data,
                    color=(1.0, 0.0, 0.0, 0.5),
                    shader='shaded',
                    glOptions='opaque'
                )
                self.addItem(mesh)
                self.obstacle_meshes.append(mesh)
            except Exception as e:
                # 网格创建失败时使用点云替代
                scatter = gl.GLScatterPlotItem(
                    pos=points,
                    color=(1.0, 0.0, 0.0, 0.5),
                    size=0.5,
                    pxMode=False
                )
                self.addItem(scatter)
                continue
                
            # 添加边界框
            vertices = obstacle['vertices']
            min_z = obstacle['min_z']
            max_z = obstacle['max_z']
            edges = []
            for i in range(len(vertices)):
                edges.append([vertices[i][0], vertices[i][1], min_z])
                edges.append([vertices[(i+1)%len(vertices)][0], vertices[(i+1)%len(vertices)][1], min_z])
                edges.append([vertices[i][0], vertices[i][1], max_z])
                edges.append([vertices[(i+1)%len(vertices)][0], vertices[(i+1)%len(vertices)][1], max_z])
                edges.append([vertices[i][0], vertices[i][1], min_z])
                edges.append([vertices[i][0], vertices[i][1], max_z])
            
            edge_item = gl.GLLinePlotItem(
                pos=np.array(edges),
                color=(1.0, 0.5, 0.5, 1.0),
                width=1.0,
                antialias=True
            )
            self.addItem(edge_item)
        
        # 添加路径
        if self.path_points:
            path_item = gl.GLLinePlotItem(
                pos=np.array(self.path_points),
                color=(0.0, 1.0, 1.0, 1.0),
                width=2.0,
                antialias=True
            )
            self.addItem(path_item)
        
        # 添加地形复杂度热力图
        if self.analyzer.complexity_map:
            try:
                data = self.analyzer.complexity_map['data']
                min_xy = self.analyzer.complexity_map['min_xy']
                grid_size = self.analyzer.complexity_map['grid_size']
                
                # 创建网格顶点
                x = np.arange(min_xy[0], min_xy[0] + grid_size * data.shape[0], grid_size)
                y = np.arange(min_xy[1], min_xy[1] + grid_size * data.shape[1], grid_size)
                xx, yy = np.meshgrid(x, y, indexing='ij')
                
                # 创建网格高度（使用复杂度值）
                zz = np.zeros_like(xx)
                
                # 创建颜色映射
                colors = np.zeros((data.shape[0], data.shape[1], 4))
                max_complexity = np.max(data)
                if max_complexity > 0:
                    normalized = data / max_complexity
                else:
                    normalized = data
                
                # 绿-黄-红渐变
                for i in range(data.shape[0]):
                    for j in range(data.shape[1]):
                        val = normalized[i, j]
                        if val < 0.5:
                            # 绿到黄
                            r = val * 2
                            g = 1.0
                            b = 0.0
                        else:
                            # 黄到红
                            r = 1.0
                            g = 2 - val * 2
                            b = 0.0
                        colors[i, j] = (r, g, b, 0.7)  # RGBA
                
                # 创建网格对象
                grid = gl.GLSurfacePlotItem(
                    x=x, y=y, z=zz,
                    colors=colors.reshape(-1, 4),
                    shader='shaded',
                    smooth=True
                )
                self.addItem(grid)
                self.complexity_mesh = grid
                
                # 添加图例
            except Exception as e:
                logger.error(f"创建复杂度热力图失败: {str(e)}")
        
        # 添加坐标轴
        axis = gl.GLAxisItem()
        axis.setSize(10, 10, 10)
        self.addItem(axis)
        
    def set_drone_position(self, position):
        self.drone_position = position
        
    def set_path(self, path):
        self.path_points = path


class AnalysisWorker(QThread):
    """后台分析线程"""
    analysis_complete = pyqtSignal(dict)
    progress_updated = pyqtSignal(int)
    
    def __init__(self, analyzer, point_cloud, drone_position, orientation):
        super().__init__()
        self.analyzer = analyzer
        self.point_cloud = point_cloud
        self.drone_position = drone_position
        self.orientation = orientation
        self.cancel_requested = False
    
    def run(self):
        """执行分析任务"""
        try:
            # 更新点云数据
            self.analyzer.update_from_lidar(self.point_cloud, self.drone_position, self.orientation)
            self.progress_updated.emit(30)
            
            if self.cancel_requested:
                return
                
            # 提取地形特征
            self.analyzer._extract_terrain_features()
            self.progress_updated.emit(60)
            
            if self.cancel_requested:
                return
                
            # 识别障碍物
            self.analyzer._identify_obstacles()
            self.progress_updated.emit(80)
            
            if self.cancel_requested:
                return
                
            # 计算复杂度热力图
            self.analyzer._calculate_complexity_map()
            self.progress_updated.emit(100)
            
            # 发送完成信号
            self.analysis_complete.emit(self.analyzer.terrain_features)
        except Exception as e:
            logger.error(f"分析过程中出错: {str(e)}")
    
    def cancel(self):
        """取消分析任务"""
        self.cancel_requested = True


class TerrainAnalysisApp(QMainWindow):
    """地形分析应用主窗口"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("高级地形拓扑分析系统 v2.0")
        self.setGeometry(100, 100, 1600, 1000)
        
        # 创建地形分析器
        self.analyzer = EnhancedTopologyAnalyzer(max_range=100.0, resolution=1.0)
        
        # 初始化UI
        self.init_ui()
        
        # 初始化模拟数据
        self.simulated_lidar = self.generate_simulated_terrain()
        
        # 设置初始位置
        self.drone_position = np.array([25.0, 25.0, 15.0])
        
        # 更新可视化
        self.update_visualization()
        
        # 设置定时器用于模拟数据更新
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.simulate_flight)
        self.timer.setInterval(1000)  # 1秒更新一次
        
        # 分析工作线程
        self.analysis_worker = None
        
        # 飞行路径
        self.flight_path = []
        self.current_path_index = 0
        
    def init_ui(self):
        """初始化用户界面"""
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        # 主布局
        main_layout = QHBoxLayout(main_widget)
        
        # 左侧控制面板
        control_panel = QGroupBox("控制面板")
        control_layout = QVBoxLayout()
        control_layout.setSpacing(10)
        
        # 添加控制按钮
        btn_layout = QHBoxLayout()
        self.load_btn = QPushButton("加载点云")
        self.load_btn.setIcon(self.style().standardIcon(getattr(self.style(), 'SP_DialogOpenButton')))
        self.load_btn.clicked.connect(self.load_point_cloud)
        btn_layout.addWidget(self.load_btn)
        
        self.analyze_btn = QPushButton("分析地形")
        self.analyze_btn.setIcon(self.style().standardIcon(getattr(self.style(), 'SP_FileDialogContentsView')))
        self.analyze_btn.clicked.connect(self.analyze_terrain)
        btn_layout.addWidget(self.analyze_btn)
        
        self.plan_path_btn = QPushButton("规划路径")
        self.plan_path_btn.setIcon(self.style().standardIcon(getattr(self.style(), 'SP_ArrowRight')))
        self.plan_path_btn.clicked.connect(self.plan_path)
        btn_layout.addWidget(self.plan_path_btn)
        
        control_layout.addLayout(btn_layout)
        
        # 模拟控制
        sim_layout = QHBoxLayout()
        self.start_sim_btn = QPushButton("开始模拟")
        self.start_sim_btn.setIcon(self.style().standardIcon(getattr(self.style(), 'SP_MediaPlay')))
        self.start_sim_btn.clicked.connect(self.toggle_simulation)
        sim_layout.addWidget(self.start_sim_btn)
        
        self.follow_path_btn = QPushButton("沿路径飞行")
        self.follow_path_btn.setIcon(self.style().standardIcon(getattr(self.style(), 'SP_MediaSeekForward')))
        self.follow_path_btn.clicked.connect(self.toggle_path_following)
        self.follow_path_btn.setEnabled(False)
        sim_layout.addWidget(self.follow_path_btn)
        
        control_layout.addLayout(sim_layout)
        
        # 参数设置
        param_group = QGroupBox("参数设置")
        param_layout = QVBoxLayout()
        param_layout.setSpacing(5)
        
        self.max_range_spin = QDoubleSpinBox()
        self.max_range_spin.setRange(10.0, 200.0)
        self.max_range_spin.setValue(100.0)
        self.max_range_spin.setPrefix("最大范围: ")
        self.max_range_spin.setSuffix(" m")
        self.max_range_spin.valueChanged.connect(self.update_analyzer_params)
        param_layout.addWidget(self.max_range_spin)
        
        self.resolution_spin = QDoubleSpinBox()
        self.resolution_spin.setRange(0.1, 5.0)
        self.resolution_spin.setValue(1.0)
        self.resolution_spin.setPrefix("分辨率: ")
        self.resolution_spin.setSuffix(" m")
        self.resolution_spin.valueChanged.connect(self.update_analyzer_params)
        param_layout.addWidget(self.resolution_spin)
        
        self.altitude_spin = QDoubleSpinBox()
        self.altitude_spin.setRange(5.0, 100.0)
        self.altitude_spin.setValue(15.0)
        self.altitude_spin.setPrefix("飞行高度: ")
        self.altitude_spin.setSuffix(" m")
        param_layout.addWidget(self.altitude_spin)
        
        # 障碍物检测阈值
        self.obstacle_threshold_spin = QDoubleSpinBox()
        self.obstacle_threshold_spin.setRange(0.1, 10.0)
        self.obstacle_threshold_spin.setValue(0.5)
        self.obstacle_threshold_spin.setPrefix("障碍物阈值: ")
        self.obstacle_threshold_spin.setSuffix(" m")
        param_layout.addWidget(self.obstacle_threshold_spin)
        
        # 复杂度计算选项
        self.complexity_mode = QComboBox()
        self.complexity_mode.addItems(["标准模式", "增强模式", "快速模式"])
        self.complexity_mode.setCurrentIndex(0)
        param_layout.addWidget(QLabel("复杂度计算模式:"))
        param_layout.addWidget(self.complexity_mode)
        
        param_group.setLayout(param_layout)
        control_layout.addWidget(param_group)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("就绪")
        control_layout.addWidget(self.progress_bar)
        
        # 地形特征显示
        self.feature_list = QListWidget()
        self.feature_list.setFont(QFont("Arial", 10))
        self.feature_list.setAlternatingRowColors(True)
        control_layout.addWidget(QLabel("地形特征:"))
        control_layout.addWidget(self.feature_list)
        
        # 日志显示
        log_group = QGroupBox("系统日志")
        log_layout = QVBoxLayout()
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 9))
        log_layout.addWidget(self.log_text)
        log_group.setLayout(log_layout)
        control_layout.addWidget(log_group)
        
        control_panel.setLayout(control_layout)
        
        # 右侧可视化区域 - 创建一个QWidget来容纳右侧布局
        right_widget = QWidget()
        vis_layout = QVBoxLayout(right_widget)
        
        # 标签页
        self.tabs = QTabWidget()
        vis_layout.addWidget(self.tabs)
        
        # 3D可视化标签页
        tab_3d = QWidget()
        tab_3d_layout = QVBoxLayout(tab_3d)
        self.vis_3d = TerrainVisualizer()
        self.vis_3d.set_analyzer(self.analyzer)
        tab_3d_layout.addWidget(self.vis_3d)
        self.tabs.addTab(tab_3d, "3D视图")
        
        # 2D可视化标签页
        tab_2d = QWidget()
        tab_2d_layout = QVBoxLayout(tab_2d)
        self.plot_2d = pg.PlotWidget()
        self.plot_2d.setLabel('left', 'Y', units='m')
        self.plot_2d.setLabel('bottom', 'X', units='m')
        self.plot_2d.setTitle("地形俯视图")
        self.plot_2d.setAspectLocked()
        self.plot_2d_plot = self.plot_2d.plot([], [], pen=None, symbol='o', symbolSize=3, symbolBrush=(0, 255, 0, 100))
        self.plot_2d_drone = self.plot_2d.plot([], [], pen=None, symbol='o', symbolSize=8, symbolBrush=(255, 0, 0))
        self.plot_2d_path = self.plot_2d.plot([], [], pen=pg.mkPen(color=(0, 255, 255), width=2))
        self.plot_2d_obstacles = []
        
        # 添加复杂度热力图
        self.complexity_img = pg.ImageItem()
        self.plot_2d.addItem(self.complexity_img)
        
        # 添加颜色条
        self.color_bar = pg.ColorBarItem(values=(0, 10), colorMap=pg.colormap.get('CET-L3'))
        self.color_bar.setImageItem(self.complexity_img)
        self.color_bar.setLevels((0, 10))
        
        tab_2d_layout.addWidget(self.plot_2d)
        self.tabs.addTab(tab_2d, "2D视图")
        
        # 主分割器
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(control_panel)
        splitter.addWidget(right_widget)  # 添加右侧的QWidget而不是布局
        splitter.setSizes([400, 1200])
        
        main_layout.addWidget(splitter)
        
        # 状态栏
        self.statusBar().showMessage("就绪")
        
        # 日志重定向
        self.log_handler = LogHandler(self.log_text)
        logger.addHandler(self.log_handler)
        
    def update_analyzer_params(self):
        """更新分析器参数"""
        self.analyzer.max_range = self.max_range_spin.value()
        self.analyzer.resolution = self.resolution_spin.value()
        logger.info(f"更新参数: 最大范围={self.analyzer.max_range}m, 分辨率={self.analyzer.resolution}m")
        
    def load_point_cloud(self):
        """加载点云数据（模拟）"""
        # 在实际应用中，这里应该从文件加载点云数据
        # 这里我们使用模拟数据
        self.simulated_lidar = self.generate_simulated_terrain()
        logger.info("已加载模拟点云数据")
        self.update_visualization()
        
    def analyze_terrain(self):
        """分析地形"""
        if self.analysis_worker and self.analysis_worker.isRunning():
            QMessageBox.information(self, "分析进行中", "当前已有分析任务在进行中，请等待完成。")
            return
            
        orientation = (0, 0, 0)  # 假设无人机姿态
        
        # 创建后台工作线程
        self.analysis_worker = AnalysisWorker(
            self.analyzer,
            self.simulated_lidar,
            self.drone_position,
            orientation
        )
        self.analysis_worker.analysis_complete.connect(self.on_analysis_complete)
        self.analysis_worker.progress_updated.connect(self.update_progress)
        
        # 禁用分析按钮
        self.analyze_btn.setEnabled(False)
        self.progress_bar.setFormat("分析中...")
        
        # 启动线程
        self.analysis_worker.start()
        
    def on_analysis_complete(self, features):
        """分析完成处理"""
        # 启用分析按钮
        self.analyze_btn.setEnabled(True)
        self.progress_bar.setFormat("分析完成")
        
        # 显示地形特征
        self.feature_list.clear()
        if features:
            self.feature_list.addItem(f"粗糙度: {features['roughness']:.2f} m")
            self.feature_list.addItem(f"平均坡度: {features['avg_slope']:.1f} °")
            self.feature_list.addItem(f"高度范围: {features['height_range']:.2f} m")
            self.feature_list.addItem(f"障碍物密度: {features['obstacle_density'] * 100:.1f}%")
            self.feature_list.addItem(f"可通行区域: {features['traversable_area'] * 100:.1f}%")
            self.feature_list.addItem(f"地形复杂度: {features['complexity']:.2f}")
            
            # 推荐高度
            rec_alt = self.analyzer.recommend_flight_altitude(self.drone_position[2])
            self.feature_list.addItem(f"推荐高度: {rec_alt:.1f} m")
            self.altitude_spin.setValue(rec_alt)
            
        self.update_visualization()
        
    def update_progress(self, value):
        """更新进度条"""
        self.progress_bar.setValue(value)
        
    def plan_path(self):
        """规划路径"""
        if self.analyzer.terrain_points.size == 0:
            logger.warning("没有地形数据，无法规划路径")
            return
            
        # 设置目标点（模拟）
        target = np.array([75.0, 75.0, self.altitude_spin.value()])
        
        # 规划路径
        path = self.analyzer.find_safe_path(self.drone_position, target, self.altitude_spin.value())
        
        if path:
            logger.info(f"已规划路径，包含 {len(path)} 个航点")
            self.vis_3d.set_path(path)
            self.flight_path = path
            self.current_path_index = 0
            self.follow_path_btn.setEnabled(True)
            self.update_visualization()
        else:
            logger.warning("无法找到安全路径")
            self.flight_path = []
            self.follow_path_btn.setEnabled(False)
        
    def toggle_simulation(self):
        """切换模拟状态"""
        if self.timer.isActive():
            self.timer.stop()
            self.start_sim_btn.setText("开始模拟")
            self.start_sim_btn.setIcon(self.style().standardIcon(getattr(self.style(), 'SP_MediaPlay')))
            logger.info("模拟已停止")
        else:
            self.timer.start()
            self.start_sim_btn.setText("停止模拟")
            self.start_sim_btn.setIcon(self.style().standardIcon(getattr(self.style(), 'SP_MediaStop')))
            logger.info("模拟已开始")
        
    def toggle_path_following(self):
        """切换路径跟随状态"""
        if self.timer.isActive():
            self.timer.stop()
            self.follow_path_btn.setText("沿路径飞行")
            self.follow_path_btn.setIcon(self.style().standardIcon(getattr(self.style(), 'SP_MediaSeekForward')))
            logger.info("路径跟随已停止")
        else:
            if not self.flight_path:
                logger.warning("没有飞行路径，无法开始跟随")
                return
                
            self.timer.start(500)  # 更快更新
            self.follow_path_btn.setText("停止跟随")
            self.follow_path_btn.setIcon(self.style().standardIcon(getattr(self.style(), 'SP_MediaStop')))
            logger.info("路径跟随已开始")
        
    def simulate_flight(self):
        """模拟无人机飞行"""
        if self.flight_path and self.follow_path_btn.text() == "停止跟随":
            # 路径跟随模式
            if self.current_path_index < len(self.flight_path):
                self.drone_position = np.array(self.flight_path[self.current_path_index])
                self.current_path_index += 1
            else:
                # 到达终点
                self.timer.stop()
                self.follow_path_btn.setText("沿路径飞行")
                self.follow_path_btn.setIcon(self.style().standardIcon(getattr(self.style(), 'SP_MediaSeekForward')))
                logger.info("已到达路径终点")
        else:
            # 自由飞行模式
            # 更新无人机位置
            self.drone_position[0] += 2.0
            self.drone_position[1] += 1.0
            
            # 边界检查
            if self.drone_position[0] > 100:
                self.drone_position[0] = 0
            if self.drone_position[1] > 100:
                self.drone_position[1] = 0
                
        # 更新点云数据
        self.simulated_lidar = self.generate_simulated_terrain()
        
        # 更新分析器
        orientation = (0, 0, 0)
        self.analyzer.update_from_lidar(self.simulated_lidar, self.drone_position, orientation)
        
        # 更新可视化
        self.update_visualization()
        
        logger.info(f"无人机位置更新: {self.drone_position}")
        
    def generate_simulated_terrain(self):
        """生成模拟地形数据"""
        # 生成基础网格
        x = np.linspace(0, 100, 50)
        y = np.linspace(0, 100, 50)
        xx, yy = np.meshgrid(x, y)
        
        # 创建地形高度
        zz = 10 + np.sin(xx/10) * np.cos(yy/10) * 5
        zz += np.sin(xx/5) * 2
        zz += np.cos(yy/7) * 3
        
        # 添加随机噪声
        zz += np.random.rand(*zz.shape) * 2
        
        # 添加障碍物
        zz[10:15, 20:25] += 8 + np.random.rand(5, 5) * 3
        zz[20:25, 15:20] += 12 + np.random.rand(5, 5) * 4
        zz[5:10, 10:15] += 15 + np.random.rand(5, 5) * 5
        zz[30:40, 30:40] += 7 + np.random.rand(10, 10) * 3
        zz[35:45, 5:15] += 10 + np.random.rand(10, 10) * 4
        
        # 添加一个深谷
        zz[40:60, 40:60] -= 8 + np.random.rand(10, 10) * 4
        
        # 转换为点云
        points = np.vstack([xx.ravel(), yy.ravel(), zz.ravel()]).T
        
        # 添加一些随机点
        random_points = np.random.rand(1000, 3) * 100
        random_points[:, 2] = random_points[:, 2] * 0.5 + 5
        
        # 合并点云
        all_points = np.vstack([points, random_points])
        
        return all_points
    
    def update_visualization(self):
        """更新所有可视化组件"""
        # 更新3D可视化
        self.vis_3d.set_drone_position(self.drone_position)
        self.vis_3d.update_visualization()
        
        # 更新2D可视化
        if self.analyzer.terrain_points.size > 0:
            # 地形点
            self.plot_2d_plot.setData(
                self.analyzer.terrain_points[:, 0],
                self.analyzer.terrain_points[:, 1]
            )
            
            # 无人机位置
            self.plot_2d_drone.setData(
                [self.drone_position[0]],
                [self.drone_position[1]]
            )
            
            # 路径
            if self.vis_3d.path_points:
                path = np.array(self.vis_3d.path_points)
                self.plot_2d_path.setData(
                    path[:, 0],
                    path[:, 1]
                )
            
            # 障碍物
            for item in self.plot_2d_obstacles:
                self.plot_2d.removeItem(item)
            self.plot_2d_obstacles = []
            
            for obstacle in self.analyzer.obstacles:
                vertices = obstacle['vertices']
                x = np.append(vertices[:, 0], vertices[0, 0])
                y = np.append(vertices[:, 1], vertices[0, 1])
                obstacle_item = self.plot_2d.plot(x, y, pen=pg.mkPen(color=(255, 100, 100), width=2))
                self.plot_2d_obstacles.append(obstacle_item)
            
            # 更新复杂度热力图
            if self.analyzer.complexity_map:
                data = self.analyzer.complexity_map['data']
                min_xy = self.analyzer.complexity_map['min_xy']
                grid_size = self.analyzer.complexity_map['grid_size']
                
                # 创建图像数据
                img_data = np.rot90(data)
                
                # 设置图像位置和缩放
                self.complexity_img.setImage(
                    img_data, 
                    pos=(min_xy[0], min_xy[1]), 
                    scale=(grid_size, grid_size)
                )
                
                # 更新颜色条范围
                max_val = np.max(data)
                if max_val > 0:
                    self.color_bar.setLevels((0, max_val))
        
        # 更新状态栏
        if self.analyzer.terrain_features:
            complexity = self.analyzer.terrain_features.get('complexity', 0)
            status = f"无人机位置: ({self.drone_position[0]:.1f}, {self.drone_position[1]:.1f}, {self.drone_position[2]:.1f}) | "
            status += f"地形复杂度: {complexity:.2f} | "
            status += f"障碍物: {len(self.analyzer.obstacles)}"
            self.statusBar().showMessage(status)


class LogHandler(logging.Handler):
    """自定义日志处理器，用于在文本框中显示日志"""
    
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget
        self.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        
    def emit(self, record):
        msg = self.format(record)
        self.text_widget.append(msg)
        self.text_widget.verticalScrollBar().setValue(
            self.text_widget.verticalScrollBar().maximum()
        )


def set_dark_theme(app):
    """设置应用为深色主题"""
    # 设置调色板
    palette = app.palette()
    palette.setColor(palette.Window, QColor(53, 53, 53))
    palette.setColor(palette.WindowText, Qt.white)
    palette.setColor(palette.Base, QColor(35, 35, 35))
    palette.setColor(palette.AlternateBase, QColor(53, 53, 53))
    palette.setColor(palette.ToolTipBase, Qt.white)
    palette.setColor(palette.ToolTipText, Qt.white)
    palette.setColor(palette.Text, Qt.white)
    palette.setColor(palette.Button, QColor(53, 53, 53))
    palette.setColor(palette.ButtonText, Qt.white)
    palette.setColor(palette.BrightText, Qt.red)
    palette.setColor(palette.Highlight, QColor(142, 45, 197).lighter())
    palette.setColor(palette.HighlightedText, Qt.black)
    app.setPalette(palette)
    
    # 设置样式
    app.setStyle("Fusion")
    
    # 设置全局样式表
    style_sheet = """
        QWidget {
            background-color: #353535;
            color: #FFFFFF;
            font-family: Arial;
            font-size: 10pt;
        }
        
        QGroupBox {
            border: 1px solid #5A5A5A;
            border-radius: 5px;
            margin-top: 1ex;
            padding-top: 10px;
        }
        
        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top center;
            padding: 0 5px;
            background-color: #353535;
        }
        
        QPushButton {
            background-color: #5A5A5A;
            border: 1px solid #5A5A5A;
            border-radius: 4px;
            padding: 5px;
            min-width: 80px;
        }
        
        QPushButton:hover {
            background-color: #6A6A6A;
        }
        
        QPushButton:pressed {
            background-color: #4A4A4A;
        }
        
        QListWidget {
            background-color: #252525;
            border: 1px solid #5A5A5A;
            border-radius: 4px;
        }
        
        QTextEdit {
            background-color: #252525;
            border: 1px solid #5A5A5A;
            border-radius: 4px;
        }
        
        QProgressBar {
            border: 1px solid #5A5A5A;
            border-radius: 4px;
            text-align: center;
            background-color: #252525;
        }
        
        QProgressBar::chunk {
            background-color: #4CAF50;
        }
        
        QTabWidget::pane {
            border: 1px solid #5A5A5A;
            background: #353535;
        }
        
        QTabBar::tab {
            background: #454545;
            color: white;
            padding: 8px;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
        }
        
        QTabBar::tab:selected {
            background: #5A5A5A;
            border-bottom-color: #5A5A5A;
        }
    """
    app.setStyleSheet(style_sheet)

class AdvancedTopologyAnalyzer(EnhancedTopologyAnalyzer):
    """增强版地形分析器，添加水体识别和植被分析功能"""
    
    def __init__(self, max_range=100.0, resolution=1.0):
        super().__init__(max_range, resolution)
        self.water_bodies = []
        self.vegetation_zones = []
        self.thermal_map = None
        self.water_threshold = -1.0  # 低于此高度视为水体
        self.vegetation_threshold = 0.3  # 点云密度高于此值视为植被区
        
    def update_from_lidar(self, point_cloud, drone_position, drone_orientation):
        """扩展点云处理功能，添加水体和植被识别"""
        success = super().update_from_lidar(point_cloud, drone_position, drone_orientation)
        if success:
            self._identify_water_bodies()
            self._identify_vegetation_zones()
            self._generate_thermal_map()
        return success
        
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
            logger.error(f"水体识别失败: {str(e)}")
    
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
    
    def find_optimal_landing_zone(self, min_size=10.0):
        """寻找最佳着陆区域"""
        if not self.terrain_features:
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
        
        return best_zone


# 修改 AdvancedVisualizer 类中的水体可视化部分
class AdvancedVisualizer(gl.GLViewWidget):
    """增强版3D地形可视化器，修复水体渲染问题"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.analyzer = None
        self.drone_position = np.array([0, 0, 10])
        self.path_points = []
        self.setCameraPosition(distance=50, elevation=30, azimuth=-45)
        self.setBackgroundColor('k')
        self.complexity_mesh = None
        self.thermal_mesh = None
        self.landing_zone = None
        
    def set_analyzer(self, analyzer):
        self.analyzer = analyzer
        
    def update_visualization(self):
        """更新3D可视化 - 重写修复水体渲染问题"""
        self.clear()
        
        if self.analyzer is None:
            return
            
        # 添加地形点云
        if self.analyzer.terrain_points.size > 0:
            points = self.analyzer.terrain_points
            if points.ndim == 1:
                points = points.reshape(-1, 3)
                
            scatter = gl.GLScatterPlotItem(
                pos=points,
                color=(0.5, 1.0, 0.5, 0.8),
                size=0.5,
                pxMode=False
            )
            self.addItem(scatter)
        
        # 添加无人机位置
        drone_scatter = gl.GLScatterPlotItem(
            pos=np.array([self.drone_position]),
            color=(1.0, 0.0, 0.0, 1.0),
            size=1.0,
            pxMode=False
        )
        self.addItem(drone_scatter)
        
        # 添加障碍物 - 更可靠的方法
        for obstacle in self.analyzer.obstacles:
            if 'points' not in obstacle or len(obstacle['points']) < 3:
                continue
                
            points = obstacle['points']
            if points.ndim == 1:
                points = points.reshape(-1, 3)
                
            # 使用边界框代替凸包，更可靠
            min_pt = np.min(points, axis=0)
            max_pt = np.max(points, axis=0)
            
            # 创建立方体网格
            verts = np.array([
                [min_pt[0], min_pt[1], min_pt[2]],
                [max_pt[0], min_pt[1], min_pt[2]],
                [max_pt[0], max_pt[1], min_pt[2]],
                [min_pt[0], max_pt[1], min_pt[2]],
                [min_pt[0], min_pt[1], max_pt[2]],
                [max_pt[0], min_pt[1], max_pt[2]],
                [max_pt[0], max_pt[1], max_pt[2]],
                [min_pt[0], max_pt[1], max_pt[2]]
            ])
            
            faces = np.array([
                [0, 1, 2], [0, 2, 3],  # 底面
                [4, 5, 6], [4, 6, 7],  # 顶面
                [0, 1, 5], [0, 5, 4],  # 侧面
                [1, 2, 6], [1, 6, 5],  # 侧面
                [2, 3, 7], [2, 7, 6],  # 侧面
                [3, 0, 4], [3, 4, 7]   # 侧面
            ])
            
            mesh_data = gl.MeshData(vertexes=verts, faces=faces)
            mesh = gl.GLMeshItem(
                meshdata=mesh_data,
                color=(1.0, 0.3, 0.3, 0.5),
                shader='shaded',
                glOptions='opaque'
            )
            self.addItem(mesh)
        
        # 添加水体 - 使用平面网格代替凸包
        for water_body in self.analyzer.water_bodies:
            if 'points' not in water_body or len(water_body['points']) < 3:
                continue
                
            points = water_body['points']
            if points.ndim == 1:
                points = points.reshape(-1, 3)
                
            # 计算水体平均高度
            water_level = np.mean(points[:, 2])
            
            # 创建水体平面
            min_xy = np.min(points[:, :2], axis=0)
            max_xy = np.max(points[:, :2], axis=0)
            
            verts = np.array([
                [min_xy[0], min_xy[1], water_level],
                [max_xy[0], min_xy[1], water_level],
                [max_xy[0], max_xy[1], water_level],
                [min_xy[0], max_xy[1], water_level]
            ])
            
            faces = np.array([[0, 1, 2], [0, 2, 3]])
            
            mesh_data = gl.MeshData(vertexes=verts, faces=faces)
            water_mesh = gl.GLMeshItem(
                meshdata=mesh_data,
                color=(0.2, 0.4, 0.8, 0.5),
                shader='shaded',
                glOptions='translucent'
            )
            self.addItem(water_mesh)
        
        # 添加植被区域 - 使用平面网格
        for vegetation in self.analyzer.vegetation_zones:
            verts = np.array([
                [vegetation['x'], vegetation['y'], 0],
                [vegetation['x'] + vegetation['width'], vegetation['y'], 0],
                [vegetation['x'] + vegetation['width'], vegetation['y'] + vegetation['height'], 0],
                [vegetation['x'], vegetation['y'] + vegetation['height'], 0]
            ])
            
            faces = np.array([[0, 1, 2], [0, 2, 3]])
            
            mesh_data = gl.MeshData(vertexes=verts, faces=faces)
            veg_mesh = gl.GLMeshItem(
                meshdata=mesh_data,
                color=(0.2, 0.8, 0.3, 0.3),
                shader='shaded',
                glOptions='translucent'
            )
            self.addItem(veg_mesh)
        
        # 添加路径
        if self.path_points:
            path_item = gl.GLLinePlotItem(
                pos=np.array(self.path_points),
                color=(0.0, 1.0, 1.0, 1.0),
                width=2.0,
                antialias=True
            )
            self.addItem(path_item)
        
        # 添加着陆区
        if self.landing_zone:
            center = self.landing_zone['center']
            size = self.landing_zone['size']
            
            verts = np.array([
                [center[0]-size/2, center[1]-size/2, center[2]],
                [center[0]+size/2, center[1]-size/2, center[2]],
                [center[0]+size/2, center[1]+size/2, center[2]],
                [center[0]-size/2, center[1]+size/2, center[2]]
            ])
            
            faces = np.array([[0, 1, 2], [0, 2, 3]])
            
            mesh_data = gl.MeshData(vertexes=verts, faces=faces)
            landing_mesh = gl.GLMeshItem(
                meshdata=mesh_data,
                color=(0.9, 0.7, 0.1, 0.5),
                shader='shaded',
                glOptions='translucent'
            )
            self.addItem(landing_mesh)
            
            # 添加文字标签
            text = gl.GLTextItem(
                pos=center,
                text=f"Landing Zone\nScore: {self.landing_zone['score']:.2f}",
                color=(1, 1, 0, 1)
            )
            self.addItem(text)
        
        # 添加坐标轴
        axis = gl.GLAxisItem()
        axis.setSize(10, 10, 10)
        self.addItem(axis)
        
    def set_drone_position(self, position):
        self.drone_position = position
        
    def set_path(self, path):
        self.path_points = path
        
    def set_landing_zone(self, zone):
        self.landing_zone = zone

class AdvancedTerrainApp(TerrainAnalysisApp):
    """增强版地形分析应用，添加新功能"""
    
    def __init__(self):
        # 使用增强版分析器和可视化器
        super().__init__()
        # 替换分析器为增强版
        self.analyzer = AdvancedTopologyAnalyzer()  # 使用增强版分析器
        # 在初始化UI前更新可视化器使用的分析器
        self.vis_3d.set_analyzer(self.analyzer)
        self.setWindowTitle("高级地形拓扑分析系统 Pro")
        self.vis_3d = AdvancedVisualizer()
        self.vis_3d.set_analyzer(self.analyzer)
        
        # 更新UI中的可视化组件
        tab_3d = self.tabs.widget(0)
        tab_3d_layout = tab_3d.layout()
        if tab_3d_layout:
            # 移除旧的可视化器
            old_widget = tab_3d_layout.itemAt(0).widget()
            if old_widget:
                old_widget.deleteLater()
            
            # 添加新的可视化器
            tab_3d_layout.addWidget(self.vis_3d)
        
    def init_ui(self):
        """扩展用户界面"""
        super().init_ui()
        
        # 添加新的控制元素
        control_panel = self.findChild(QGroupBox, "控制面板")
        if control_panel:
            control_layout = control_panel.layout()
            
            # 添加水体阈值设置
            water_threshold_spin = QDoubleSpinBox()
            water_threshold_spin.setRange(-10.0, 10.0)
            water_threshold_spin.setValue(-1.0)
            water_threshold_spin.setPrefix("水体阈值: ")
            water_threshold_spin.setSuffix(" m")
            water_threshold_spin.valueChanged.connect(self.update_water_threshold)
            control_layout.insertWidget(5, water_threshold_spin)
            
            # 添加植被阈值设置
            veg_threshold_spin = QDoubleSpinBox()
            veg_threshold_spin.setRange(0.1, 2.0)
            veg_threshold_spin.setValue(0.3)
            veg_threshold_spin.setPrefix("植被密度: ")
            veg_threshold_spin.valueChanged.connect(self.update_vegetation_threshold)
            control_layout.insertWidget(6, veg_threshold_spin)
            
            # 添加寻找着陆区按钮
            landing_btn = QPushButton("寻找着陆区")
            landing_btn.clicked.connect(self.find_landing_zone)
            control_layout.insertWidget(7, landing_btn)
    
    def update_water_threshold(self, value):
        """更新水体检测阈值"""
        self.analyzer.water_threshold = value
        if self.analyzer.terrain_points.size > 0:
            self.analyzer._identify_water_bodies()
            self.update_visualization()
    
    def update_vegetation_threshold(self, value):
        """更新植被检测阈值"""
        self.analyzer.vegetation_threshold = value
        if self.analyzer.terrain_points.size > 0:
            self.analyzer._identify_vegetation_zones()
            self.update_visualization()
    
    def find_landing_zone(self):
        """寻找并标记最佳着陆区"""
        landing_zone = self.analyzer.find_optimal_landing_zone()
        if landing_zone:
            center = landing_zone['center']
            size = landing_zone['size']
            
            # 创建着陆区标记
            vertices = np.array([
                [center[0]-size/2, center[1]-size/2, center[2]],
                [center[0]+size/2, center[1]-size/2, center[2]],
                [center[0]+size/2, center[1]+size/2, center[2]],
                [center[0]-size/2, center[1]+size/2, center[2]]
            ])
            
            # 创建网格
            landing_mesh = gl.GLMeshItem(
                vertexes=vertices,
                color=(0.9, 0.7, 0.1, 0.5),
                shader='shaded',
                glOptions='translucent'
            )
            self.vis_3d.addItem(landing_mesh)
            
            # 添加文字标签
            text = gl.GLTextItem(
                pos=center,
                text=f"着陆区\n评分: {landing_zone['score']:.2f}",
                color=(1, 1, 0, 1)
            )
            self.vis_3d.addItem(text)
            
            logger.info(f"找到最佳着陆区: 位置={center}, 评分={landing_zone['score']:.2f}")
        else:
            logger.warning("未找到合适的着陆区")
    
    def generate_simulated_terrain(self):
        """扩展模拟地形生成，添加水体和植被"""
        terrain = super().generate_simulated_terrain()
        
        # 添加水体
        water_points = []
        for i in range(3):
            x, y = np.random.rand(2) * 80 + 10
            width, height = np.random.rand(2) * 15 + 5
            depth = np.random.rand() * 3 + 1
            
            x_vals = np.linspace(x, x+width, 20)
            y_vals = np.linspace(y, y+height, 20)
            xx, yy = np.meshgrid(x_vals, y_vals)
            zz = np.full_like(xx, -depth)
            
            water_points.append(np.vstack([xx.ravel(), yy.ravel(), zz.ravel()]).T)
        
        # 添加植被
        veg_points = []
        for i in range(5):
            x, y = np.random.rand(2) * 80 + 10
            size = np.random.rand() * 10 + 5
            height = np.random.rand() * 3 + 1
            
            # 生成随机植被点
            for j in range(50):
                px = x + np.random.randn() * size/2
                py = y + np.random.randn() * size/2
                pz = height * np.random.rand()
                veg_points.append([px, py, pz])
        
        # 合并所有点
        all_points = np.vstack([
            terrain, 
            *water_points,
            np.array(veg_points)
        ])
        
        return all_points
    
if __name__ == "__main__":
    app = QApplication(sys.argv)
    set_dark_theme(app)  # 假设有深色主题设置函数
    window = AdvancedTerrainApp()
    window.show()
    sys.exit(app.exec_())