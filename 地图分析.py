import cv2
import numpy as np
import json
import time
import os
import sys
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass
from enum import Enum
from collections import deque
from scipy import ndimage
from sklearn.cluster import DBSCAN
import networkx as nx
from PIL import Image, ImageDraw, ImageFont
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
import joblib

class TerrainType(Enum):
    PLAIN = 0
    FOREST = 1
    MOUNTAIN = 2
    WATER = 3
    URBAN = 4
    DESERT = 5
    SWAMP = 6
    ROAD = 7
    BRIDGE = 8

@dataclass
class StrategicPoint:
    id: int
    position: Tuple[int, int]
    strategic_value: float
    terrain_type: TerrainType
    control_radius: int
    resource_value: float
    defensive_bonus: float
    mobility_penalty: float
    visibility: float
    elevation: float
    connectivity: float = 0.0
    threat_level: float = 0.0
    context_score: float = 0.0
    regional_importance: float = 0.0
    is_chokepoint: bool = False
    is_resource_rich: bool = False
    is_defensive_position: bool = False
    is_logistical_hub: bool = False
    is_ambush_site: bool = False
    is_artillery_position: bool = False
    
    def to_dict(self):
        return {
            'id': self.id,
            'position': self.position,
            'strategic_value': round(self.strategic_value, 3),
            'terrain_type': self.terrain_type.name,
            'control_radius': self.control_radius,
            'resource_value': round(self.resource_value, 3),
            'defensive_bonus': round(self.defensive_bonus, 3),
            'mobility_penalty': round(self.mobility_penalty, 3),
            'visibility': round(self.visibility, 3),
            'elevation': round(self.elevation, 3),
            'connectivity': round(self.connectivity, 3),
            'threat_level': round(self.threat_level, 3),
            'context_score': round(self.context_score, 3),
            'regional_importance': round(self.regional_importance, 3),
            'is_chokepoint': self.is_chokepoint,
            'is_resource_rich': self.is_resource_rich,
            'is_defensive_position': self.is_defensive_position,
            'is_logistical_hub': self.is_logistical_hub,
            'is_ambush_site': self.is_ambush_site,
            'is_artillery_position': self.is_artillery_position
        }

class AdvancedTextDetector:
    """高级文字检测器"""
    
    def __init__(self):
        self.text_classifier = self._load_text_classifier()
        
    def _load_text_classifier(self):
        """加载文字分类器"""
        try:
            # 尝试加载预训练模型
            return joblib.load('text_classifier.pkl')
        except:
            print("文字分类器未找到，使用传统方法")
            return None
    
    def detect_text_regions(self, image):
        """检测文字区域"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # 多方法文字检测
        mser_mask = self._mser_detection(gray)
        contour_mask = self._contour_based_detection(gray)
        texture_mask = self._texture_based_detection(gray)
        
        # 融合检测结果
        combined_mask = mser_mask | contour_mask | texture_mask
        
        # 形态学优化
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        combined_mask = cv2.morphologyEx(combined_mask.astype(np.uint8), 
                                       cv2.MORPH_CLOSE, kernel)
        combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_OPEN, kernel)
        
        return combined_mask.astype(bool)
    
    def _mser_detection(self, gray):
        """MSER文字检测"""
        mser = cv2.MSER_create(delta=5, min_area=50, max_area=2000)
        regions, _ = mser.detectRegions(gray)
        
        # 将掩码类型改为uint8而不是bool
        mask = np.zeros_like(gray, dtype=np.uint8)
        for region in regions:
            if len(region) > 10:
                hull = cv2.convexHull(region.reshape(-1, 1, 2))
                cv2.fillConvexPoly(mask, hull, 255)  # 使用255而不是True
                
        return mask
    
    def _contour_based_detection(self, gray):
        """基于轮廓的文字检测"""
        # 自适应阈值
        binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                    cv2.THRESH_BINARY, 11, 2)
        
        # 查找轮廓
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # 使用uint8而不是bool
        mask = np.zeros_like(gray, dtype=np.uint8)
        for contour in contours:
            area = cv2.contourArea(contour)
            x, y, w, h = cv2.boundingRect(contour)
            aspect_ratio = w / h
            
            # 文字特征：合适的长宽比和面积
            if (0.2 < aspect_ratio < 5.0 and 
                50 < area < 5000 and 
                w > 5 and h > 5):
                cv2.fillPoly(mask, [contour], 255)  # 使用255而不是True
                
        return mask
    
    def _texture_based_detection(self, gray):
        """基于纹理的文字检测"""
        # 计算局部二值模式
        lbp = self._calculate_lbp(gray)
        
        # 计算纹理统计量
        texture_std = ndimage.generic_filter(lbp, np.std, size=5)
        
        # 文字区域通常有较高的纹理变化
        text_mask = texture_std > np.percentile(texture_std, 70)
        
        return text_mask
    
    def _calculate_lbp(self, gray):
        """计算LBP纹理"""
        radius = 1
        n_points = 8 * radius
        
        lbp = np.zeros_like(gray, dtype=np.uint8)
        for i in range(radius, gray.shape[0]-radius):
            for j in range(radius, gray.shape[1]-radius):
                center = gray[i, j]
                binary_code = 0
                for k, (di, dj) in enumerate([(0,1), (1,1), (1,0), (1,-1), 
                                            (0,-1), (-1,-1), (-1,0), (-1,1)]):
                    if gray[i+di, j+dj] >= center:
                        binary_code |= (1 << k)
                lbp[i, j] = binary_code
                
        return lbp

class DeepTerrainClassifier:
    """深度地形分类器"""
    
    def __init__(self):
        self.feature_scaler = StandardScaler()
        self.terrain_model = self._initialize_model()
        
    def _initialize_model(self):
        """初始化地形分类模型"""
        try:
            return joblib.load('terrain_classifier.pkl')
        except:
            print("地形分类器未找到，使用基于规则的方法")
            return None
    
    def extract_advanced_features(self, image_roi):
        """提取高级特征"""
        features = []
        
        # 颜色特征
        color_features = self._extract_color_features(image_roi)
        features.extend(color_features)
        
        # 纹理特征
        texture_features = self._extract_texture_features(image_roi)
        features.extend(texture_features)
        
        # 形状特征
        shape_features = self._extract_shape_features(image_roi)
        features.extend(shape_features)
        
        # 频谱特征
        spectral_features = self._extract_spectral_features(image_roi)
        features.extend(spectral_features)
        
        return np.array(features)
    
    def _extract_color_features(self, roi):
        """提取颜色特征"""
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        lab = cv2.cvtColor(roi, cv2.COLOR_BGR2LAB)
        
        # 统计特征
        h_mean, h_std = np.mean(hsv[:,:,0]), np.std(hsv[:,:,0])
        s_mean, s_std = np.mean(hsv[:,:,1]), np.std(hsv[:,:,1])
        v_mean, v_std = np.mean(hsv[:,:,2]), np.std(hsv[:,:,2])
        l_mean, l_std = np.mean(lab[:,:,0]), np.std(lab[:,:,0])
        a_mean, a_std = np.mean(lab[:,:,1]), np.std(lab[:,:,1])
        b_mean, b_std = np.mean(lab[:,:,2]), np.std(lab[:,:,2])
        
        # 颜色直方图特征
        h_hist = cv2.calcHist([hsv], [0], None, [8], [0, 180]).flatten()
        s_hist = cv2.calcHist([hsv], [1], None, [4], [0, 256]).flatten()
        
        return [h_mean, h_std, s_mean, s_std, v_mean, v_std,
                l_mean, l_std, a_mean, a_std, b_mean, b_std] + list(h_hist) + list(s_hist)
    
    def _extract_texture_features(self, roi):
        """提取纹理特征"""
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        
        # GLCM纹理特征
        glcm = self._calculate_glcm(gray)
        contrast = greycoprops(glcm, 'contrast')[0, 0]
        homogeneity = greycoprops(glcm, 'homogeneity')[0, 0]
        energy = greycoprops(glcm, 'energy')[0, 0]
        correlation = greycoprops(glcm, 'correlation')[0, 0]
        
        # LBP纹理
        lbp = self._calculate_lbp_advanced(gray)
        lbp_hist, _ = np.histogram(lbp, bins=16, range=(0, 16))
        lbp_hist = lbp_hist / lbp_hist.sum()
        
        return [contrast, homogeneity, energy, correlation] + list(lbp_hist)
    
    def _calculate_glcm(self, gray):
        """计算GLCM"""
        # 简化版GLCM计算
        glcm = np.zeros((8, 8), dtype=np.uint32)
        for i in range(1, gray.shape[0]-1):
            for j in range(1, gray.shape[1]-1):
                center = gray[i, j] // 32
                right = gray[i, j+1] // 32
                glcm[center, right] += 1
                
        glcm = glcm.astype(np.float64)
        glcm += glcm.T  # 对称化
        glcm /= glcm.sum()  # 归一化
        
        return glcm.reshape(1, 8, 8)
    
    def _calculate_lbp_advanced(self, gray):
        """高级LBP计算"""
        radius = 2
        n_points = 8 * radius
        lbp = local_binary_pattern(gray, n_points, radius, method='uniform')
        return lbp
    
    def _extract_shape_features(self, roi):
        """提取形状特征"""
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        
        # 边缘密度
        edge_density = np.sum(edges) / (edges.size * 255)
        
        # 轮廓特征
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if contours:
            largest_contour = max(contours, key=cv2.contourArea)
            area = cv2.contourArea(largest_contour)
            perimeter = cv2.arcLength(largest_contour, True)
            circularity = (4 * np.pi * area) / (perimeter ** 2) if perimeter > 0 else 0
        else:
            area = perimeter = circularity = 0
            
        return [edge_density, area, perimeter, circularity]
    
    def _extract_spectral_features(self, roi):
        """提取频谱特征"""
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        
        # FFT分析
        fft = np.fft.fft2(gray)
        fft_shift = np.fft.fftshift(fft)
        magnitude = np.log(np.abs(fft_shift) + 1)
        
        # 频带能量
        h, w = magnitude.shape
        cy, cx = h//2, w//2
        
        # 低频能量 (中心区域)
        low_freq_mask = np.zeros((h, w), bool)
        cv2.circle(low_freq_mask, (cx, cy), min(cx, cy)//2, True, -1)
        low_freq_energy = np.mean(magnitude[low_freq_mask])
        
        # 高频能量 (外围区域)
        high_freq_energy = np.mean(magnitude[~low_freq_mask])
        
        return [low_freq_energy, high_freq_energy, high_freq_energy/(low_freq_energy+1e-6)]
    
    def classify_terrain(self, image, x, y, window_size=15):
        """分类地形"""
        h, w = image.shape[:2]
        x1, y1 = max(0, x-window_size), max(0, y-window_size)
        x2, y2 = min(w, x+window_size), min(h, y+window_size)
        
        roi = image[y1:y2, x1:x2]
        if roi.size == 0:
            return TerrainType.PLAIN
        
        # 使用机器学习模型分类
        if self.terrain_model is not None:
            try:
                features = self.extract_advanced_features(roi).reshape(1, -1)
                features = self.feature_scaler.transform(features)
                prediction = self.terrain_model.predict(features)[0]
                return TerrainType(prediction)
            except:
                pass
        
        # 回退到基于规则的方法
        return self._rule_based_classification(roi)
    
    def _rule_based_classification(self, roi):
        """基于规则的地形分类"""
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        lab = cv2.cvtColor(roi, cv2.COLOR_BGR2LAB)
        
        h_mean = np.mean(hsv[:,:,0])
        s_mean = np.mean(hsv[:,:,1])
        v_mean = np.mean(hsv[:,:,2])
        l_mean = np.mean(lab[:,:,0])
        
        # 道路检测 (线性特征)
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        line_density = np.sum(edges) / edges.size
        
        if line_density > 0.1 and v_mean > 150:
            return TerrainType.ROAD
        
        # 桥梁检测 (水域上的线性特征)
        if 100 <= h_mean <= 130 and line_density > 0.05:
            return TerrainType.BRIDGE
        
        # 其他地形分类
        if 35 <= h_mean <= 85 and s_mean > 40:
            return TerrainType.FOREST
        elif 100 <= h_mean <= 130 and s_mean > 40:
            return TerrainType.WATER
        elif s_mean < 30 and v_mean < 100:
            return TerrainType.MOUNTAIN
        elif s_mean < 40 and v_mean > 150:
            return TerrainType.URBAN
        elif (h_mean < 15 or h_mean > 165) and s_mean > 50:
            return TerrainType.DESERT
        elif 20 <= h_mean <= 35 and s_mean > 40:
            return TerrainType.SWAMP
        else:
            return TerrainType.PLAIN

class StrategicRegion:
    """战略区域"""
    
    def __init__(self, points, region_type, importance):
        self.points = points
        self.region_type = region_type
        self.importance = importance
        self.center = self._calculate_center()
        self.boundary = self._calculate_boundary()
        self.area = len(points)
        
    def _calculate_center(self):
        """计算区域中心"""
        if not self.points:
            return (0, 0)
        positions = np.array([p.position for p in self.points])
        return tuple(np.mean(positions, axis=0).astype(int))
    
    def _calculate_boundary(self):
        """计算区域边界"""
        if not self.points:
            return []
        positions = np.array([p.position for p in self.points])
        
        # 计算凸包
        if len(positions) >= 3:
            hull = cv2.convexHull(positions)
            return hull.reshape(-1, 2).tolist()
        else:
            return positions.tolist()
    
    def to_dict(self):
        return {
            'type': self.region_type,
            'importance': round(self.importance, 3),
            'center': self.center,
            'area': self.area,
            'boundary': self.boundary,
            'points_count': len(self.points)
        }

class AdvancedStrategicAnalyzer:
    """高级战略分析器"""
    
    def __init__(self):
        self.strategic_points = []
        self.strategic_regions = []
        self.text_detector = AdvancedTextDetector()
        self.terrain_classifier = DeepTerrainClassifier()
        self.text_mask = None
        self.terrain_map = None
        self.elevation_map = None
        self.resource_map = None
        self.mobility_map = None
        self.defense_map = None
        self.visibility_map = None
        self.threat_map = None
        self.strategic_network = nx.Graph()
        
        # 性能优化
        self.analysis_resolution = 0.7
        self.max_points = 2000
        self.enable_caching = True
        self.performance_cache = {}
        
    def load_and_preprocess(self, image_path):
        """加载并预处理地图"""
        print("加载地图...")
        self.original_map = cv2.imread(image_path)
        if self.original_map is None:
            raise ValueError("无法加载地图文件")
            
        # 调整分辨率
        if self.analysis_resolution < 1.0:
            new_w = int(self.original_map.shape[1] * self.analysis_resolution)
            new_h = int(self.original_map.shape[0] * self.analysis_resolution)
            self.original_map = cv2.resize(self.original_map, (new_w, new_h))
            
        self.map_height, self.map_width = self.original_map.shape[:2]
        self.processed_map = self.original_map.copy()
        
        print("检测文字区域...")
        self.text_mask = self.text_detector.detect_text_regions(self.original_map)
        
        print("生成地形分析图...")
        self._generate_terrain_maps()
        
        return True
    
    def _generate_terrain_maps(self):
        """生成地形分析图"""
        gray = cv2.cvtColor(self.processed_map, cv2.COLOR_BGR2GRAY)
        
        # 高程图
        sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=5)
        sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=5)
        self.elevation_map = np.sqrt(sobelx**2 + sobely**2)
        
        # 资源图
        hsv = cv2.cvtColor(self.processed_map, cv2.COLOR_BGR2HSV)
        forest_mask = cv2.inRange(hsv, (35, 40, 40), (85, 255, 255))
        water_mask = cv2.inRange(hsv, (100, 40, 40), (130, 255, 255))
        urban_mask = cv2.inRange(hsv, (0, 0, 100), (180, 50, 255))
        self.resource_map = (forest_mask * 0.6 + water_mask * 0.4 + urban_mask * 0.8) / 255.0
        
        # 机动性图
        edges = cv2.Canny(gray, 50, 150)
        self.mobility_map = 255 - edges
        
        # 防御图
        harris = cv2.cornerHarris(gray, 2, 3, 0.04)
        self.defense_map = cv2.normalize(harris, None, 0, 1, cv2.NORM_MINMAX)
        
        # 视野图
        self.visibility_map = self._calculate_advanced_visibility()
        
        # 威胁图
        self.threat_map = self._calculate_threat_map()
    
    def _calculate_advanced_visibility(self):
        """计算高级视野图"""
        visibility = np.ones((self.map_height, self.map_width))
        
        # 基于高程和地形的视野计算
        for y in range(0, self.map_height, 5):
            for x in range(0, self.map_width, 5):
                base_elevation = self.elevation_map[y, x]
                visible_count = 0
                total_count = 0
                
                # 检查多个方向
                for angle in np.linspace(0, 2*np.pi, 16):
                    for distance in range(10, 100, 10):
                        tx = int(x + distance * np.cos(angle))
                        ty = int(y + distance * np.sin(angle))
                        
                        if 0 <= tx < self.map_width and 0 <= ty < self.map_height:
                            target_elevation = self.elevation_map[ty, tx]
                            terrain_type = self.terrain_classifier.classify_terrain(
                                self.processed_map, tx, ty)
                            
                            # 视线遮挡判断
                            if (target_elevation <= base_elevation + 0.1 and 
                                terrain_type not in [TerrainType.FOREST, TerrainType.URBAN]):
                                visible_count += 1
                            total_count += 1
                
                visibility[y:y+5, x:x+5] = visible_count / (total_count + 1e-6)
        
        return visibility
    
    def _calculate_threat_map(self):
        """计算威胁图"""
        threat = np.zeros((self.map_height, self.map_width))
        
        # 基于地形和位置的威胁评估
        for y in range(0, self.map_height, 10):
            for x in range(0, self.map_width, 10):
                terrain_type = self.terrain_classifier.classify_terrain(
                    self.processed_map, x, y)
                
                base_threat = 0.0
                
                # 不同地形的威胁基础值
                if terrain_type == TerrainType.MOUNTAIN:
                    base_threat = 0.8  # 高地威胁
                elif terrain_type == TerrainType.URBAN:
                    base_threat = 0.6  # 城市威胁
                elif terrain_type == TerrainType.FOREST:
                    base_threat = 0.4  # 森林威胁（伏击）
                elif terrain_type in [TerrainType.ROAD, TerrainType.BRIDGE]:
                    base_threat = 0.7  # 交通要道威胁
                
                # 视野加成
                visibility = self.visibility_map[y, x]
                base_threat *= (0.5 + visibility * 0.5)
                
                threat[y:y+10, x:x+10] = base_threat
        
        return threat
    
    def detect_strategic_points(self):
        """检测战略点"""
        print("检测战略点...")
        points = []
        point_id = 0
        
        # 动态网格大小
        grid_size = max(8, min(25, int(np.sqrt(self.map_width * self.map_height / self.max_points))))
        
        for y in range(grid_size//2, self.map_height, grid_size):
            for x in range(grid_size//2, self.map_width, grid_size):
                
                # 跳过文字区域
                if self.text_mask is not None and self.text_mask[y, x]:
                    continue
                
                # 计算战略价值
                strategic_value = self._calculate_comprehensive_value(x, y)
                
                if strategic_value > 0.1:  # 较低阈值以捕捉更多点
                    terrain_type = self.terrain_classifier.classify_terrain(
                        self.processed_map, x, y)
                    
                    point = StrategicPoint(
                        id=point_id,
                        position=(x, y),
                        strategic_value=strategic_value,
                        terrain_type=terrain_type,
                        control_radius=int(15 + strategic_value * 25),
                        resource_value=self._get_local_value(self.resource_map, x, y),
                        defensive_bonus=self._get_local_value(self.defense_map, x, y),
                        mobility_penalty=1.0 - self._get_local_value(self.mobility_map, x, y),
                        visibility=self._get_local_value(self.visibility_map, x, y),
                        elevation=self._get_local_value(self.elevation_map, x, y),
                        is_chokepoint=self._is_chokepoint(x, y),
                        is_resource_rich=self._is_resource_rich(x, y),
                        is_defensive_position=self._is_defensive_position(x, y),
                        is_ambush_site=self._is_ambush_site(x, y, terrain_type),
                        is_artillery_position=self._is_artillery_position(x, y, terrain_type)
                    )
                    
                    points.append(point)
                    point_id += 1
                
                if len(points) >= self.max_points:
                    break
            
            if len(points) >= self.max_points:
                break
        
        # 高级后处理
        points = self._remove_redundant_points(points)
        points = self._calculate_advanced_metrics(points)
        points = self._identify_special_points(points)
        
        self.strategic_points = points
        print(f"检测到 {len(points)} 个战略点")
        return points
    
    def _calculate_comprehensive_value(self, x, y):
        """计算综合战略价值"""
        # 基础价值
        resource_val = self._get_local_value(self.resource_map, x, y)
        defense_val = self._get_local_value(self.defense_map, x, y)
        mobility_val = 1.0 - self._get_local_value(self.mobility_map, x, y)
        visibility_val = self._get_local_value(self.visibility_map, x, y)
        elevation_val = self._get_local_value(self.elevation_map, x, y)
        threat_val = self._get_local_value(self.threat_map, x, y)
        
        # 地形权重
        terrain_type = self.terrain_classifier.classify_terrain(self.processed_map, x, y)
        weights = self._get_terrain_weights(terrain_type)
        
        # 综合计算
        base_value = (resource_val * weights['resource'] +
                     defense_val * weights['defense'] +
                     mobility_val * weights['mobility'] +
                     visibility_val * weights['visibility'] +
                     elevation_val * weights['elevation'] +
                     threat_val * weights['threat'])
        
        # 上下文加成
        context_bonus = self._calculate_context_bonus(x, y, terrain_type)
        
        return min(1.0, base_value * 0.8 + context_bonus * 0.2)
    
    def _get_terrain_weights(self, terrain_type):
        """获取地形权重"""
        weights = {
            TerrainType.MOUNTAIN: {'resource': 0.1, 'defense': 0.6, 'mobility': 0.1, 
                                 'visibility': 0.8, 'elevation': 0.3, 'threat': 0.7},
            TerrainType.FOREST: {'resource': 0.5, 'defense': 0.4, 'mobility': 0.2,
                               'visibility': 0.2, 'elevation': 0.1, 'threat': 0.4},
            TerrainType.WATER: {'resource': 0.3, 'defense': 0.2, 'mobility': 0.0,
                              'visibility': 0.4, 'elevation': 0.2, 'threat': 0.2},
            TerrainType.URBAN: {'resource': 0.6, 'defense': 0.5, 'mobility': 0.3,
                              'visibility': 0.3, 'elevation': 0.1, 'threat': 0.6},
            TerrainType.ROAD: {'resource': 0.2, 'defense': 0.3, 'mobility': 0.8,
                             'visibility': 0.5, 'elevation': 0.1, 'threat': 0.7},
            TerrainType.BRIDGE: {'resource': 0.1, 'defense': 0.4, 'mobility': 0.9,
                               'visibility': 0.6, 'elevation': 0.1, 'threat': 0.8},
            TerrainType.PLAIN: {'resource': 0.2, 'defense': 0.2, 'mobility': 0.6,
                              'visibility': 0.5, 'elevation': 0.1, 'threat': 0.3}
        }
        return weights.get(terrain_type, weights[TerrainType.PLAIN])
    
    def _calculate_context_bonus(self, x, y, terrain_type):
        """计算上下文加成"""
        bonus = 0.0
        
        # 交通要道加成
        if self._controls_movement_corridor(x, y):
            bonus += 0.3
        
        # 资源集中区加成
        if self._in_resource_cluster(x, y):
            bonus += 0.2
        
        # 防御地形加成
        if self._has_defensive_terrain(x, y):
            bonus += 0.2
        
        # 高地控制加成
        if self._controls_high_ground(x, y):
            bonus += 0.3
        
        return bonus
    
    def _controls_movement_corridor(self, x, y):
        """控制交通要道"""
        # 检查是否在主要移动路径上
        mobility_local = self._get_local_value(self.mobility_map, x, y, 20)
        return mobility_local > 0.7
    
    def _in_resource_cluster(self, x, y):
        """在资源集中区"""
        resource_local = self._get_local_value(self.resource_map, x, y, 15)
        return resource_local > 0.6
    
    def _has_defensive_terrain(self, x, y):
        """有防御性地形"""
        defense_local = self._get_local_value(self.defense_map, x, y, 10)
        return defense_local > 0.5
    
    def _controls_high_ground(self, x, y):
        """控制高地"""
        elevation_local = self._get_local_value(self.elevation_map, x, y, 25)
        return elevation_local > 0.7
    
    def _get_local_value(self, map_data, x, y, radius=5):
        """获取局部值"""
        if map_data is None:
            return 0.5
        
        x1, y1 = max(0, x-radius), max(0, y-radius)
        x2, y2 = min(self.map_width, x+radius), min(self.map_height, y+radius)
        
        roi = map_data[y1:y2, x1:x2]
        if roi.size == 0:
            return 0.5
        
        value = np.mean(roi)
        
        # 归一化
        if map_data is self.elevation_map or map_data is self.defense_map:
            max_val = map_data.max() if map_data.max() > 0 else 1
            value = min(1.0, value / max_val)
        elif map_data is self.resource_map or map_data is self.mobility_map:
            value = value / 255.0
        
        return value
    
    def _is_chokepoint(self, x, y):
        """是否为咽喉要道"""
        if self.mobility_map is None:
            return False
        
        roi = self._get_roi(self.mobility_map, x, y, 20)
        if roi.size == 0:
            return False
        
        mobility_variance = np.var(roi)
        avg_mobility = np.mean(roi)
        
        # 狭窄通道特征：高方差，中等平均机动性
        return mobility_variance > 2000 and 50 < avg_mobility < 180
    
    def _is_resource_rich(self, x, y):
        """是否资源富集"""
        resource_val = self._get_local_value(self.resource_map, x, y, 10)
        return resource_val > 0.7
    
    def _is_defensive_position(self, x, y):
        """是否为防御位置"""
        defense_val = self._get_local_value(self.defense_map, x, y, 8)
        visibility_val = self._get_local_value(self.visibility_map, x, y, 15)
        return defense_val > 0.6 and visibility_val > 0.4
    
    def _is_ambush_site(self, x, y, terrain_type):
        """是否为伏击点"""
        if terrain_type not in [TerrainType.FOREST, TerrainType.URBAN]:
            return False
        
        visibility_val = self._get_local_value(self.visibility_map, x, y, 10)
        mobility_val = 1.0 - self._get_local_value(self.mobility_map, x, y, 15)
        
        return visibility_val < 0.3 and mobility_val < 0.4
    
    def _is_artillery_position(self, x, y, terrain_type):
        """是否为炮兵阵地"""
        if terrain_type != TerrainType.MOUNTAIN:
            return False
        
        elevation_val = self._get_local_value(self.elevation_map, x, y, 20)
        visibility_val = self._get_local_value(self.visibility_map, x, y, 30)
        mobility_val = 1.0 - self._get_local_value(self.mobility_map, x, y, 10)
        
        return elevation_val > 0.6 and visibility_val > 0.7 and mobility_val < 0.3
    
    def _get_roi(self, map_data, x, y, radius):
        """获取感兴趣区域"""
        x1, y1 = max(0, x-radius), max(0, y-radius)
        x2, y2 = min(self.map_width, x+radius), min(self.map_height, y+radius)
        return map_data[y1:y2, x1:x2]
    
    def _remove_redundant_points(self, points, min_distance=15):
        """移除冗余点"""
        if not points:
            return points
        
        sorted_points = sorted(points, key=lambda x: x.strategic_value, reverse=True)
        filtered_points = []
        
        for point in sorted_points:
            too_close = False
            for existing_point in filtered_points:
                dist = np.sqrt((point.position[0]-existing_point.position[0])**2 + 
                             (point.position[1]-existing_point.position[1])**2)
                if dist < min_distance:
                    too_close = True
                    break
            
            if not too_close:
                filtered_points.append(point)
        
        return filtered_points
    
    def _calculate_advanced_metrics(self, points):
        """计算高级指标"""
        if not points:
            return points
        
        # 构建网络计算连通性
        temp_graph = nx.Graph()
        for point in points:
            temp_graph.add_node(point.id, position=point.position)
        
        # 添加连接
        for i, p1 in enumerate(points):
            for p2 in points[i+1:]:
                dist = np.sqrt((p1.position[0]-p2.position[0])**2 + 
                             (p1.position[1]-p2.position[1])**2)
                if dist < 100:
                    weight = 1.0 / (dist + 1)
                    temp_graph.add_edge(p1.id, p2.id, weight=weight)
        
        # 计算网络指标
        if len(temp_graph.nodes) > 1:
            centrality = nx.betweenness_centrality(temp_graph, weight='weight')
            for point in points:
                point.connectivity = centrality.get(point.id, 0.0)
                point.threat_level = min(1.0, point.strategic_value * 0.6 + point.connectivity * 0.4)
                point.is_logistical_hub = (point.connectivity > 0.15 and 
                                         point.mobility_penalty < 0.3 and
                                         point.strategic_value > 0.5)
        
        return points
    
    def _identify_special_points(self, points):
        """识别特殊点"""
        for point in points:
            # 伏击点验证
            if point.is_ambush_site:
                point.context_score += 0.2
            
            # 炮兵阵地验证
            if point.is_artillery_position:
                point.context_score += 0.3
                point.regional_importance += 0.4
            
            # 咽喉要道重要性提升
            if point.is_chokepoint:
                point.regional_importance += 0.5
                point.threat_level = min(1.0, point.threat_level + 0.3)
        
        return points
    
    def identify_strategic_regions(self):
        """识别战略区域"""
        if not self.strategic_points:
            return []
        
        print("识别战略区域...")
        positions = np.array([p.position for p in self.strategic_points])
        values = np.array([p.strategic_value for p in self.strategic_points])
        
        # 基于DBSCAN聚类
        clustering = DBSCAN(eps=50, min_samples=3).fit(positions)
        
        regions = []
        unique_labels = set(clustering.labels_)
        
        for label in unique_labels:
            if label == -1:
                continue
                
            region_points = [self.strategic_points[i] for i in range(len(self.strategic_points)) 
                           if clustering.labels_[i] == label]
            
            if len(region_points) >= 3:
                region_type = self._classify_region_type(region_points)
                importance = self._calculate_region_importance(region_points)
                region = StrategicRegion(region_points, region_type, importance)
                regions.append(region)
        
        self.strategic_regions = regions
        print(f"识别到 {len(regions)} 个战略区域")
        return regions
    
    def _classify_region_type(self, points):
        """分类区域类型"""
        terrain_counts = {}
        special_counts = {
            'chokepoints': 0,
            'resources': 0,
            'defense': 0,
            'logistics': 0
        }
        
        for point in points:
            terrain = point.terrain_type
            terrain_counts[terrain] = terrain_counts.get(terrain, 0) + 1
            
            if point.is_chokepoint:
                special_counts['chokepoints'] += 1
            if point.is_resource_rich:
                special_counts['resources'] += 1
            if point.is_defensive_position:
                special_counts['defense'] += 1
            if point.is_logistical_hub:
                special_counts['logistics'] += 1
        
        # 基于特征分类
        if special_counts['chokepoints'] >= 2:
            return "CHOKEPOINT_CLUSTER"
        elif special_counts['resources'] >= 3:
            return "RESOURCE_BASIN"
        elif special_counts['defense'] >= 3:
            return "DEFENSIVE_PERIMETER"
        elif special_counts['logistics'] >= 2:
            return "LOGISTICS_HUB"
        
        # 基于地形分类
        dominant_terrain = max(terrain_counts.items(), key=lambda x: x[1])[0]
        if dominant_terrain == TerrainType.MOUNTAIN:
            return "HIGHLAND_CONTROL"
        elif dominant_terrain == TerrainType.URBAN:
            return "URBAN_COMPLEX"
        elif dominant_terrain == TerrainType.FOREST:
            return "FOREST_OPERATIONS"
        elif dominant_terrain == TerrainType.WATER:
            return "WATERWAY_ACCESS"
        else:
            return "STRATEGIC_ZONE"
    
    def _calculate_region_importance(self, points):
        """计算区域重要性"""
        if not points:
            return 0.0
        
        avg_value = np.mean([p.strategic_value for p in points])
        max_value = max([p.strategic_value for p in points])
        density = len(points) / 10.0  # 标准化密度
        
        # 特殊点加成
        special_bonus = sum(1 for p in points if any([
            p.is_chokepoint, p.is_logistical_hub, 
            p.is_artillery_position
        ])) * 0.1
        
        importance = (avg_value * 0.4 + max_value * 0.3 + 
                     min(1.0, density) * 0.2 + special_bonus)
        
        return min(1.0, importance)
    
    def generate_strategic_network(self):
        """生成战略网络"""
        if not self.strategic_points:
            return
        
        self.strategic_network.clear()
        
        # 添加节点
        for point in self.strategic_points:
            self.strategic_network.add_node(
                point.id,
                position=point.position,
                value=point.strategic_value,
                terrain=point.terrain_type.name
            )
        
        # 添加连接
        for i, p1 in enumerate(self.strategic_points):
            for p2 in self.strategic_points[i+1:]:
                dist = np.sqrt((p1.position[0]-p2.position[0])**2 + 
                             (p1.position[1]-p2.position[1])**2)
                
                max_dist = self._get_max_connection_distance(p1, p2)
                if dist < max_dist:
                    weight = self._calculate_connection_strength(p1, p2, dist)
                    self.strategic_network.add_edge(p1.id, p2.id, 
                                                   weight=weight, distance=dist)
    
    def _get_max_connection_distance(self, p1, p2):
        """获取最大连接距离"""
        base_distance = 120
        
        terrain_ranges = {
            TerrainType.MOUNTAIN: 0.6,
            TerrainType.WATER: 0.4,
            TerrainType.FOREST: 0.8,
            TerrainType.SWAMP: 0.5,
            TerrainType.URBAN: 1.2,
            TerrainType.ROAD: 1.5,  # 道路连接更远
            TerrainType.BRIDGE: 1.8, # 桥梁连接最远
            TerrainType.DESERT: 0.9,
            TerrainType.PLAIN: 1.0
        }
        
        range1 = terrain_ranges.get(p1.terrain_type, 1.0)
        range2 = terrain_ranges.get(p2.terrain_type, 1.0)
        
        return base_distance * (range1 + range2) / 2
    
    def _calculate_connection_strength(self, p1, p2, distance):
        """计算连接强度"""
        value_factor = (p1.strategic_value + p2.strategic_value) / 2
        terrain_compat = self._get_terrain_compatibility(p1.terrain_type, p2.terrain_type)
        
        return value_factor * terrain_compat / (distance + 1)
    
    def _get_terrain_compatibility(self, t1, t2):
        """获取地形兼容性"""
        # 简化兼容性矩阵
        if t1 == t2:
            return 1.0
        elif (t1 in [TerrainType.ROAD, TerrainType.BRIDGE] or 
              t2 in [TerrainType.ROAD, TerrainType.BRIDGE]):
            return 0.9  # 交通设施兼容性好
        elif (t1 in [TerrainType.MOUNTAIN, TerrainType.WATER] and 
              t2 in [TerrainType.MOUNTAIN, TerrainType.WATER]):
            return 0.3  # 困难地形兼容性差
        else:
            return 0.6  # 一般兼容性
    
    def generate_comprehensive_report(self):
        """生成综合分析报告"""
        if not self.strategic_points:
            return {}
        
        print("生成分析报告...")
        
        # 基础统计
        total_points = len(self.strategic_points)
        strategic_values = [p.strategic_value for p in self.strategic_points]
        avg_value = np.mean(strategic_values)
        max_value = max(strategic_values)
        
        # 地形分布
        terrain_dist = {}
        for terrain in TerrainType:
            count = len([p for p in self.strategic_points if p.terrain_type == terrain])
            if count > 0:
                terrain_dist[terrain.name] = count
        
        # 特殊点统计
        special_points = {
            'chokepoints': len([p for p in self.strategic_points if p.is_chokepoint]),
            'resource_rich': len([p for p in self.strategic_points if p.is_resource_rich]),
            'defensive': len([p for p in self.strategic_points if p.is_defensive_position]),
            'logistical': len([p for p in self.strategic_points if p.is_logistical_hub]),
            'ambush_sites': len([p for p in self.strategic_points if p.is_ambush_site]),
            'artillery_positions': len([p for p in self.strategic_points if p.is_artillery_position])
        }
        
        # 战略区域统计
        region_stats = {}
        if self.strategic_regions:
            region_types = [r.region_type for r in self.strategic_regions]
            for region_type in set(region_types):
                region_stats[region_type] = region_types.count(region_type)
        
        # 网络分析
        network_stats = {}
        if self.strategic_network:
            try:
                network_stats = {
                    'nodes': self.strategic_network.number_of_nodes(),
                    'edges': self.strategic_network.number_of_edges(),
                    'density': nx.density(self.strategic_network),
                    'components': nx.number_connected_components(self.strategic_network),
                    'avg_degree': np.mean([d for n, d in self.strategic_network.degree()])
                }
            except:
                network_stats = {'error': '网络分析失败'}
        
        # 威胁分析
        threat_levels = [p.threat_level for p in self.strategic_points]
        high_threat = len([t for t in threat_levels if t > 0.7])
        
        report = {
            'summary': {
                'total_strategic_points': total_points,
                'average_strategic_value': round(avg_value, 3),
                'max_strategic_value': round(max_value, 3),
                'high_threat_points': high_threat,
                'map_dimensions': (self.map_width, self.map_height),
                'analysis_timestamp': time.time()
            },
            'terrain_distribution': terrain_dist,
            'special_points': special_points,
            'strategic_regions': {
                'total_regions': len(self.strategic_regions),
                'region_types': region_stats,
                'regions': [r.to_dict() for r in self.strategic_regions]
            },
            'network_analysis': network_stats,
            'top_strategic_points': [p.to_dict() for p in 
                                   sorted(self.strategic_points, 
                                        key=lambda x: x.strategic_value, 
                                        reverse=True)[:20]],
            'critical_chokepoints': [p.to_dict() for p in 
                                   sorted([p for p in self.strategic_points if p.is_chokepoint],
                                        key=lambda x: x.strategic_value, 
                                        reverse=True)[:10]]
        }
        
        return report
    
    def visualize_analysis(self, show_details=True):
        """可视化分析结果"""
        if self.original_map is None:
            return None
        
        result_image = self.original_map.copy()
        
        if not self.strategic_points:
            return result_image
        
        # 绘制战略区域
        for region in self.strategic_regions:
            color = self._get_region_color(region.region_type)
            alpha = 0.3
            
            # 绘制区域边界
            if len(region.boundary) >= 3:
                points = np.array(region.boundary, dtype=np.int32)
                overlay = result_image.copy()
                cv2.fillPoly(overlay, [points], color)
                cv2.addWeighted(overlay, alpha, result_image, 1-alpha, 0, result_image)
                
                # 绘制边界线
                cv2.polylines(result_image, [points], True, color, 2)
        
        # 绘制战略点
        for point in self.strategic_points:
            x, y = point.position
            color, size = self._get_point_style(point)
            
            # 绘制控制范围
            if point.strategic_value > 0.4:
                cv2.circle(result_image, (x, y), point.control_radius, color, 1)
            
            # 绘制点
            cv2.circle(result_image, (x, y), size, color, -1)
            
            # 特殊标记
            if point.is_chokepoint:
                cv2.drawMarker(result_image, (x, y), (255, 0, 255), 
                             cv2.MARKER_STAR, 20, 3)
            elif point.is_logistical_hub:
                cv2.drawMarker(result_image, (x, y), (255, 255, 0), 
                             cv2.MARKER_DIAMOND, 16, 2)
            elif point.is_artillery_position:
                cv2.drawMarker(result_image, (x, y), (0, 0, 255), 
                             cv2.MARKER_TRIANGLE_DOWN, 18, 2)
            elif point.is_ambush_site:
                cv2.drawMarker(result_image, (x, y), (0, 255, 255), 
                             cv2.MARKER_SQUARE, 14, 2)
            
            # 显示标签
            if show_details and point.strategic_value > 0.3:
                label = f"{point.strategic_value:.2f}"
                cv2.putText(result_image, label, (x+10, y-10),
                          cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
        
        # 绘制战略网络
        if hasattr(self, 'strategic_network') and self.strategic_network:
            for edge in self.strategic_network.edges(data=True):
                node1, node2, data = edge
                p1 = next(p for p in self.strategic_points if p.id == node1)
                p2 = next(p for p in self.strategic_points if p.id == node2)
                
                weight = data.get('weight', 0.5)
                thickness = max(1, int(weight * 8))
                color = (200, 200, 100)  # 网络线颜色
                
                cv2.line(result_image, p1.position, p2.position, color, thickness)
        
        # 添加图例
        result_image = self._add_comprehensive_legend(result_image)
        
        return result_image
    
    def _get_region_color(self, region_type):
        """获取区域颜色"""
        colors = {
            "CHOKEPOINT_CLUSTER": (0, 0, 255),      # 红色
            "RESOURCE_BASIN": (0, 255, 0),          # 绿色
            "DEFENSIVE_PERIMETER": (255, 255, 0),   # 青色
            "LOGISTICS_HUB": (255, 0, 255),         # 紫色
            "HIGHLAND_CONTROL": (128, 128, 128),    # 灰色
            "URBAN_COMPLEX": (255, 165, 0),         # 橙色
            "FOREST_OPERATIONS": (0, 128, 0),       # 深绿
            "WATERWAY_ACCESS": (255, 0, 0),         # 蓝色
            "STRATEGIC_ZONE": (128, 0, 128)         # 紫色
        }
        return colors.get(region_type, (128, 128, 128))
    
    def _get_point_style(self, point):
        """获取点样式"""
        value = point.strategic_value
        
        if value > 0.8:
            color = (0, 0, 255)    # 红色 - 极高价值
            size = 12
        elif value > 0.6:
            color = (0, 165, 255)  # 橙色 - 高价值
            size = 10
        elif value > 0.4:
            color = (0, 255, 255)  # 黄色 - 中等价值
            size = 8
        else:
            color = (0, 255, 0)    # 绿色 - 低价值
            size = 6
        
        return color, size
    
    def _add_comprehensive_legend(self, image):
        """添加综合图例"""
        legend_items = [
            ("红色区域: 咽喉要道集群", (0, 0, 255)),
            ("绿色区域: 资源富集区", (0, 255, 0)),
            ("青色区域: 防御阵地", (255, 255, 0)),
            ("紫色区域: 后勤枢纽", (255, 0, 255)),
            ("红色点: 极高价值(>0.8)", (0, 0, 255)),
            ("橙色点: 高价值(0.6-0.8)", (0, 165, 255)),
            ("黄色点: 中等价值(0.4-0.6)", (0, 255, 255)),
            ("绿色点: 低价值(<0.4)", (0, 255, 0)),
            ("紫色星: 咽喉要道", (255, 0, 255)),
            ("青色菱形: 后勤枢纽", (255, 255, 0)),
            ("红色下三角: 炮兵阵地", (0, 0, 255)),
            ("黄色方块: 伏击点", (0, 255, 255))
        ]
        
        for i, (text, color) in enumerate(legend_items):
            y_position = 30 + i * 25
            cv2.putText(image, text, (10, y_position),
                      cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
            cv2.putText(image, text, (10, y_position),
                      cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        
        return image

# 使用示例
def analyze_map_advanced(image_path, output_dir="analysis_results"):
    """高级地图分析入口函数"""
    
    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)
    
    # 初始化分析器
    analyzer = AdvancedStrategicAnalyzer()
    
    try:
        # 加载和预处理
        analyzer.load_and_preprocess(image_path)
        
        # 检测战略点
        strategic_points = analyzer.detect_strategic_points()
        
        # 识别战略区域
        strategic_regions = analyzer.identify_strategic_regions()
        
        # 构建战略网络
        analyzer.generate_strategic_network()
        
        # 生成报告
        report = analyzer.generate_comprehensive_report()
        
        # 可视化结果
        visualization = analyzer.visualize_analysis(show_details=True)
        
        # 保存结果
        base_name = os.path.splitext(os.path.basename(image_path))[0]
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        
        # 保存可视化图像
        viz_path = os.path.join(output_dir, f"{base_name}_analysis_{timestamp}.jpg")
        cv2.imwrite(viz_path, visualization)
        
        # 保存报告
        report_path = os.path.join(output_dir, f"{base_name}_report_{timestamp}.json")
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        # 保存详细数据
        data_path = os.path.join(output_dir, f"{base_name}_data_{timestamp}.csv")
        with open(data_path, 'w', encoding='utf-8') as f:
            f.write("ID,X,Y,StrategicValue,Terrain,ControlRadius,Resource,Defense,Mobility,Visibility,Elevation,Connectivity,Threat,Context,RegionalImportance,IsChokepoint,IsResourceRich,IsDefensive,IsLogistical,IsAmbush,IsArtillery\n")
            for point in strategic_points:
                f.write(f"{point.id},{point.position[0]},{point.position[1]},{point.strategic_value:.3f},{point.terrain_type.name},{point.control_radius},{point.resource_value:.3f},{point.defensive_bonus:.3f},{point.mobility_penalty:.3f},{point.visibility:.3f},{point.elevation:.3f},{point.connectivity:.3f},{point.threat_level:.3f},{point.context_score:.3f},{point.regional_importance:.3f},{point.is_chokepoint},{point.is_resource_rich},{point.is_defensive_position},{point.is_logistical_hub},{point.is_ambush_site},{point.is_artillery_position}\n")
        
        print(f"分析完成！结果保存在: {output_dir}")
        print(f"- 可视化图像: {viz_path}")
        print(f"- 分析报告: {report_path}")
        print(f"- 详细数据: {data_path}")
        
        return report, visualization
        
    except Exception as e:
        print(f"分析过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        return None, None

if __name__ == "__main__":
    # 使用示例
    if len(sys.argv) > 1:
        image_path = sys.argv[1]
    else:
        image_path = "ty.jpg"  # 默认地图文件
        
    report, visualization = analyze_map_advanced(image_path)
    
    if visualization is not None:
        # 显示结果（如果可能）
        try:
            cv2.imshow("战略分析结果", visualization)
            cv2.waitKey(0)
            cv2.destroyAllWindows()
        except:
            print("无法显示图像，但分析已完成")