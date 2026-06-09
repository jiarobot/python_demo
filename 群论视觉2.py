import numpy as np
import cv2
import matplotlib
matplotlib.rc("font", family='Microsoft YaHei')
import matplotlib.pyplot as plt
from scipy import ndimage, spatial
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler
import math
from typing import List, Tuple, Dict, Any, Optional
import json
from dataclasses import dataclass
from pathlib import Path
import time
from enum import Enum

class PartType(Enum):
    GEAR = "gear"
    BEARING = "bearing" 
    BOLT = "bolt"
    WASHER = "washer"
    UNKNOWN = "unknown"

@dataclass
class DetectionResult:
    part_type: PartType
    confidence: float
    bounding_box: Tuple[int, int, int, int]
    center: Tuple[int, int]
    orientation: float
    symmetry_score: float
    defects: List[Dict[str, Any]]
    transform_type: str

class IndustrialGroupTheoryDetector:
    """
    工业级基于群论的零件检测系统
    模拟真实生产线环境
    """
    
    def __init__(self, config_path: Optional[str] = None):
        # 加载配置或使用默认值
        self.config = self._load_config(config_path)
        
        # 初始化检测参数
        self.min_contour_area = self.config.get('min_contour_area', 1000)
        self.similarity_threshold = self.config.get('similarity_threshold', 0.65)
        self.max_orientation_variance = self.config.get('max_orientation_variance', 15.0)
        
        # 零件模板数据库
        self.template_database = {}
        self.feature_database = {}
        
        # 质量检测参数
        self.defect_thresholds = {
            'symmetry_deviation': 0.15,
            'circularity_threshold': 0.85,
            'area_variance_threshold': 0.2,
            'edge_continuity_threshold': 0.9
        }
        
        # 初始化图像处理参数
        self.morph_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        
        print("工业级群论检测器初始化完成")
    
    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """加载配置文件"""
        default_config = {
            'min_contour_area': 1000,
            'similarity_threshold': 0.65,
            'max_orientation_variance': 15.0,
            'feature_weights': {
                'zernike': 0.3,
                'fourier': 0.25,
                'topological': 0.2,
                'symmetry': 0.25
            },
            'quality_thresholds': {
                'excellent': 0.9,
                'good': 0.8,
                'acceptable': 0.7
            }
        }
        
        if config_path and Path(config_path).exists():
            try:
                with open(config_path, 'r') as f:
                    user_config = json.load(f)
                    default_config.update(user_config)
            except Exception as e:
                print(f"配置文件加载失败，使用默认配置: {e}")
        
        return default_config
    
    def load_template_database(self, database_path: str):
        """加载零件模板数据库"""
        template_dir = Path(database_path)
        if not template_dir.exists():
            print(f"模板数据库路径不存在: {database_path}")
            return
        
        # 支持多种图像格式
        image_extensions = ['*.jpg', '*.jpeg', '*.png', '*.bmp', '*.tiff']
        
        for part_type in PartType:
            if part_type == PartType.UNKNOWN:
                continue
                
            part_dir = template_dir / part_type.value
            if not part_dir.exists():
                continue
                
            self.template_database[part_type] = []
            self.feature_database[part_type] = []
            
            for ext in image_extensions:
                for template_path in part_dir.glob(ext):
                    try:
                        # 读取模板图像
                        template = cv2.imread(str(template_path), cv2.IMREAD_GRAYSCALE)
                        if template is None:
                            continue
                            
                        # 预处理模板
                        processed_template = self._preprocess_image(template)
                        
                        # 提取群论特征
                        features = self._extract_group_theory_features(processed_template)
                        
                        self.template_database[part_type].append(processed_template)
                        self.feature_database[part_type].append({
                            'features': features,
                            'original_size': template.shape,
                            'template_path': str(template_path)
                        })
                        
                        print(f"加载模板: {template_path} -> {part_type.value}")
                        
                    except Exception as e:
                        print(f"加载模板失败 {template_path}: {e}")
        
        print(f"模板数据库加载完成: {len(self.template_database)} 种零件类型")
    
    def _preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """工业图像预处理"""
        # 1. 高斯去噪
        denoised = cv2.GaussianBlur(image, (5, 5), 0)
        
        # 2. 自适应阈值二值化
        binary = cv2.adaptiveThreshold(
            denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 11, 2
        )
        
        # 3. 形态学操作
        cleaned = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, self.morph_kernel)
        cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_OPEN, self.morph_kernel)
        
        # 4. 边缘保留滤波
        filtered = cv2.bilateralFilter(cleaned, 9, 75, 75)
        
        return filtered
    
    def _extract_group_theory_features(self, image: np.ndarray) -> Dict[str, Any]:
        """提取群论特征"""
        features = {}
        
        # 1. 多尺度Zernike矩 (旋转不变)
        features['zernike_moments'] = self._compute_multi_scale_zernike(image)
        
        # 2. 傅里叶描述子 (形状描述)
        features['fourier_descriptors'] = self._compute_robust_fourier_descriptors(image)
        
        # 3. 对称性分析
        features['symmetry_analysis'] = self._analyze_symmetries(image)
        
        # 4. 拓扑特征
        features['topological_features'] = self._compute_topological_descriptors(image)
        
        # 5. 纹理特征 (基于灰度共生矩阵)
        features['texture_features'] = self._compute_texture_features(image)
        
        return features
    
    def _compute_multi_scale_zernike(self, image: np.ndarray, scales: List[float] = None) -> np.ndarray:
        """多尺度Zernike矩计算"""
        if scales is None:
            scales = [0.8, 1.0, 1.2]
            
        all_moments = []
        
        for scale in scales:
            # 尺度变换
            if scale != 1.0:
                scaled_img = cv2.resize(image, None, fx=scale, fy=scale)
                # 调整回原尺寸
                if scaled_img.shape != image.shape:
                    scaled_img = cv2.resize(scaled_img, (image.shape[1], image.shape[0]))
            else:
                scaled_img = image.copy()
            
            # 计算Zernike矩 (使用OpenCV的矩)
            moments = cv2.moments(scaled_img)
            hu_moments = cv2.HuMoments(moments).flatten()
            
            # 对数变换增强小值
            hu_moments = -np.sign(hu_moments) * np.log10(np.abs(hu_moments) + 1e-8)
            
            all_moments.extend(hu_moments)
        
        return np.array(all_moments)
    
    def _compute_robust_fourier_descriptors(self, image: np.ndarray, num_descriptors: int = 20) -> np.ndarray:
        """鲁棒傅里叶描述子"""
        try:
            # 提取轮廓
            contours, _ = cv2.findContours(image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_TC89_KCOS)
            if not contours:
                return np.zeros(num_descriptors)
            
            # 选择最大轮廓
            main_contour = max(contours, key=cv2.contourArea)
            
            # 轮廓重采样到固定点数
            contour_length = cv2.arcLength(main_contour, True)
            if contour_length == 0:
                return np.zeros(num_descriptors)
                
            # 等间距采样
            num_points = 128
            sampled_contour = np.zeros((num_points, 2), dtype=np.float32)
            
            for i in range(num_points):
                distance = (contour_length * i) / num_points
                point = self._get_contour_point_at_distance(main_contour, distance)
                sampled_contour[i] = point
            
            # 转换为复数序列
            complex_contour = sampled_contour[:, 0] + 1j * sampled_contour[:, 1]
            
            # 傅里叶变换
            fd = np.fft.fft(complex_contour)
            
            # 归一化并提取描述子
            if np.abs(fd[1]) > 0:
                fd_normalized = fd / np.abs(fd[1])
            else:
                fd_normalized = fd
            
            # 取前n个描述子 (排除DC分量)
            descriptors = np.abs(fd_normalized[1:num_descriptors+1])
            
            return descriptors
            
        except Exception as e:
            print(f"傅里叶描述子计算失败: {e}")
            return np.zeros(num_descriptors)
    
    def _get_contour_point_at_distance(self, contour: np.ndarray, target_distance: float) -> np.ndarray:
        """在轮廓上按距离获取点"""
        current_distance = 0
        
        for i in range(len(contour)):
            p1 = contour[i][0]
            p2 = contour[(i + 1) % len(contour)][0]
            
            segment_length = np.linalg.norm(p2 - p1)
            
            if current_distance + segment_length >= target_distance:
                # 线性插值
                t = (target_distance - current_distance) / segment_length
                point = p1 + t * (p2 - p1)
                return point
                
            current_distance += segment_length
        
        return contour[0][0]  # 默认返回第一个点
    
    def _analyze_symmetries(self, image: np.ndarray) -> Dict[str, float]:
        """全面对称性分析"""
        symmetries = {}
        
        # 1. 旋转对称性
        symmetries['rotational'] = self._compute_rotational_symmetry(image)
        
        # 2. 反射对称性
        symmetries['reflection_horizontal'] = self._compute_reflection_symmetry(image, 'horizontal')
        symmetries['reflection_vertical'] = self._compute_reflection_symmetry(image, 'vertical')
        
        # 3. 径向对称性
        symmetries['radial'] = self._compute_radial_symmetry(image)
        
        return symmetries
    
    def _compute_rotational_symmetry(self, image: np.ndarray, max_angle: int = 180) -> float:
        """计算旋转对称性"""
        scores = []
        center_x, center_y = image.shape[1] // 2, image.shape[0] // 2
        
        for angle in range(10, max_angle + 1, 10):
            if 360 % angle != 0:
                continue
                
            rotation_scores = []
            for k in range(1, 360 // angle):
                rotated = ndimage.rotate(image, angle * k, reshape=False)
                # 计算相关性
                correlation = np.corrcoef(image.flatten(), rotated.flatten())[0, 1]
                if not np.isnan(correlation):
                    rotation_scores.append(correlation)
            
            if rotation_scores:
                scores.append(np.mean(rotation_scores))
        
        return np.mean(scores) if scores else 0.0
    
    def _compute_reflection_symmetry(self, image: np.ndarray, axis: str) -> float:
        """计算反射对称性"""
        if axis == 'horizontal':
            flipped = cv2.flip(image, 1)
        elif axis == 'vertical':
            flipped = cv2.flip(image, 0)
        else:
            return 0.0
        
        # 计算结构相似性
        correlation = np.corrcoef(image.flatten(), flipped.flatten())[0, 1]
        return correlation if not np.isnan(correlation) else 0.0
    
    def _compute_radial_symmetry(self, image: np.ndarray) -> float:
        """计算径向对称性"""
        try:
            # 计算距离变换
            dist_transform = cv2.distanceTransform(image, cv2.DIST_L2, 5)
            
            # 创建极坐标网格
            center_x, center_y = image.shape[1] // 2, image.shape[0] // 2
            y, x = np.ogrid[:image.shape[0], :image.shape[1]]
            
            # 转换为极坐标
            r = np.sqrt((x - center_x)**2 + (y - center_y)**2)
            theta = np.arctan2(y - center_y, x - center_x)
            
            # 采样径向剖面
            max_radius = min(center_x, center_y)
            radial_profiles = []
            
            for angle in np.linspace(0, 2*np.pi, 36, endpoint=False):
                # 提取径向剖面
                profile = []
                for radius in np.linspace(0, max_radius, 50):
                    xi = int(center_x + radius * np.cos(angle))
                    yi = int(center_y + radius * np.sin(angle))
                    
                    if 0 <= xi < image.shape[1] and 0 <= yi < image.shape[0]:
                        profile.append(dist_transform[yi, xi])
                    else:
                        profile.append(0)
                
                radial_profiles.append(profile)
            
            # 计算剖面间的相关性
            if len(radial_profiles) > 1:
                correlations = []
                for i in range(len(radial_profiles)):
                    for j in range(i+1, len(radial_profiles)):
                        corr = np.corrcoef(radial_profiles[i], radial_profiles[j])[0, 1]
                        if not np.isnan(corr):
                            correlations.append(corr)
                
                return np.mean(correlations) if correlations else 0.0
            else:
                return 0.0
                
        except Exception as e:
            print(f"径向对称性计算失败: {e}")
            return 0.0
    
    def _compute_topological_descriptors(self, image: np.ndarray) -> Dict[str, float]:
        """计算拓扑描述子"""
        topological = {}
        
        # 计算轮廓
        contours, hierarchy = cv2.findContours(image, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            return topological
        
        # 1. 欧拉数
        topological['euler_number'] = self._compute_euler_number(contours, hierarchy)
        
        # 2. 孔洞数量
        topological['hole_count'] = max(0, len(contours) - 1)
        
        # 3. 凸性缺陷
        topological['convexity'] = self._compute_convexity(contours[0])
        
        # 4. 紧密度
        area = cv2.contourArea(contours[0])
        perimeter = cv2.arcLength(contours[0], True)
        topological['compactness'] = (4 * np.pi * area) / (perimeter ** 2) if perimeter > 0 else 0
        
        # 5. 伸长度
        if len(contours[0]) >= 5:
            ellipse = cv2.fitEllipse(contours[0])
            major_axis, minor_axis = max(ellipse[1]), min(ellipse[1])
            topological['elongation'] = minor_axis / major_axis if major_axis > 0 else 0
        else:
            topological['elongation'] = 0
        
        return topological
    
    def _compute_euler_number(self, contours: List, hierarchy: List) -> int:
        """计算欧拉数"""
        if hierarchy is None:
            return 1
        
        # 简单实现：对象数 - 孔洞数
        object_count = 0
        hole_count = 0
        
        for i, h in enumerate(hierarchy[0]):
            if h[3] == -1:  # 外部轮廓
                object_count += 1
            else:  # 孔洞
                hole_count += 1
        
        return object_count - hole_count
    
    def _compute_convexity(self, contour: np.ndarray) -> float:
        """计算凸性"""
        hull = cv2.convexHull(contour)
        contour_area = cv2.contourArea(contour)
        hull_area = cv2.contourArea(hull)
        
        return contour_area / hull_area if hull_area > 0 else 0
    
    def _compute_texture_features(self, image: np.ndarray) -> np.ndarray:
        """计算纹理特征"""
        # 使用LBP (局部二值模式)
        lbp = self._compute_lbp(image)
        
        # 计算LBP直方图
        hist, _ = np.histogram(lbp.ravel(), bins=256, range=(0, 256))
        hist = hist.astype(np.float32)
        hist /= (hist.sum() + 1e-8)  # 归一化
        
        # 返回主要特征 (前16个bin)
        return hist[:16]
    
    def _compute_lbp(self, image: np.ndarray, radius: int = 1, points: int = 8) -> np.ndarray:
        """计算局部二值模式"""
        height, width = image.shape
        lbp_image = np.zeros_like(image)
        
        for i in range(radius, height - radius):
            for j in range(radius, width - radius):
                center = image[i, j]
                binary = 0
                
                for p in range(points):
                    angle = 2 * np.pi * p / points
                    x = j + radius * np.cos(angle)
                    y = i - radius * np.sin(angle)
                    
                    # 双线性插值
                    x1, y1 = int(np.floor(x)), int(np.floor(y))
                    x2, y2 = int(np.ceil(x)), int(np.ceil(y))
                    
                    if (0 <= x1 < width and 0 <= x2 < width and 
                        0 <= y1 < height and 0 <= y2 < height):
                        
                        # 插值权重
                        wx = x - x1
                        wy = y - y1
                        
                        # 双线性插值
                        value = (image[y1, x1] * (1 - wx) * (1 - wy) +
                                image[y1, x2] * wx * (1 - wy) +
                                image[y2, x1] * (1 - wx) * wy +
                                image[y2, x2] * wx * wy)
                        
                        binary |= (1 if value >= center else 0) << p
                
                lbp_image[i, j] = binary
        
        return lbp_image
    
    def detect_parts(self, image: np.ndarray, visualize: bool = False) -> List[DetectionResult]:
        """检测图像中的零件"""
        start_time = time.time()
        
        # 预处理图像
        processed_image = self._preprocess_image(image)
        
        # 检测候选区域
        candidate_regions = self._detect_candidate_regions(processed_image)
        
        # 识别每个候选区域
        detections = []
        for i, region in enumerate(candidate_regions):
            try:
                detection = self._recognize_part(region, processed_image)
                if detection:
                    detections.append(detection)
            except Exception as e:
                print(f"区域 {i} 识别失败: {e}")
        
        # 后处理：非极大值抑制
        detections = self._non_maximum_suppression(detections)
        
        # 质量分析
        for detection in detections:
            detection.defects = self._analyze_quality(detection, processed_image)
        
        processing_time = time.time() - start_time
        print(f"检测完成: 找到 {len(detections)} 个零件, 耗时 {processing_time:.2f}秒")
        
        if visualize:
            self._visualize_results(image, detections, processed_image)
        
        return detections
    
    def _detect_candidate_regions(self, image: np.ndarray) -> List[Dict[str, Any]]:
        """检测候选区域"""
        regions = []
        
        # 查找轮廓
        contours, _ = cv2.findContours(image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < self.min_contour_area:
                continue
            
            # 计算边界框和最小外接矩形
            x, y, w, h = cv2.boundingRect(contour)
            rect = cv2.minAreaRect(contour)
            box = cv2.boxPoints(rect)
            box = np.int0(box)
            
            # 计算方向
            orientation = rect[2]
            
            # 提取区域
            mask = np.zeros_like(image)
            cv2.drawContours(mask, [contour], 0, 255, -1)
            region_image = cv2.bitwise_and(image, image, mask=mask)
            region_cropped = region_image[y:y+h, x:x+w]
            
            regions.append({
                'contour': contour,
                'bbox': (x, y, w, h),
                'min_area_rect': rect,
                'orientation': orientation,
                'area': area,
                'mask': mask,
                'region_image': region_cropped,
                'center': (x + w//2, y + h//2)
            })
        
        return regions
    
    def _recognize_part(self, region: Dict[str, Any], full_image: np.ndarray) -> Optional[DetectionResult]:
        """识别单个零件"""
        best_match = None
        best_similarity = 0
        best_part_type = PartType.UNKNOWN
        
        # 提取区域特征
        region_features = self._extract_group_theory_features(region['region_image'])
        
        # 与模板数据库比较
        for part_type, template_features_list in self.feature_database.items():
            for template_data in template_features_list:
                similarity = self._compute_feature_similarity(region_features, template_data['features'])
                
                if similarity > best_similarity and similarity > self.similarity_threshold:
                    best_similarity = similarity
                    best_part_type = part_type
                    best_match = template_data
        
        if best_match is None:
            return None
        
        # 计算对称性分数
        symmetry_score = np.mean(list(region_features['symmetry_analysis'].values()))
        
        # 创建检测结果
        detection = DetectionResult(
            part_type=best_part_type,
            confidence=best_similarity,
            bounding_box=region['bbox'],
            center=region['center'],
            orientation=region['orientation'],
            symmetry_score=symmetry_score,
            defects=[],
            transform_type="similarity"  # 可以扩展为具体的变换类型
        )
        
        return detection
    
    def _compute_feature_similarity(self, features1: Dict, features2: Dict) -> float:
        """计算特征相似度"""
        weights = self.config['feature_weights']
        total_similarity = 0
        total_weight = 0
        
        # Zernike矩相似度
        if 'zernike_moments' in features1 and 'zernike_moments' in features2:
            z1, z2 = features1['zernike_moments'], features2['zernike_moments']
            if len(z1) == len(z2):
                z_sim = 1 - spatial.distance.cosine(z1, z2)
                total_similarity += weights['zernike'] * z_sim
                total_weight += weights['zernike']
        
        # 傅里叶描述子相似度
        if 'fourier_descriptors' in features1 and 'fourier_descriptors' in features2:
            f1, f2 = features1['fourier_descriptors'], features2['fourier_descriptors']
            if len(f1) == len(f2):
                f_sim = 1 - spatial.distance.cosine(f1, f2)
                total_similarity += weights['fourier'] * f_sim
                total_weight += weights['fourier']
        
        # 对称性相似度
        if 'symmetry_analysis' in features1 and 'symmetry_analysis' in features2:
            s1, s2 = features1['symmetry_analysis'], features2['symmetry_analysis']
            sym_keys = set(s1.keys()) & set(s2.keys())
            if sym_keys:
                sym_sims = [1 - abs(s1[k] - s2[k]) for k in sym_keys]
                sym_sim = np.mean(sym_sims)
                total_similarity += weights['symmetry'] * sym_sim
                total_weight += weights['symmetry']
        
        # 拓扑特征相似度
        if 'topological_features' in features1 and 'topological_features' in features2:
            t1, t2 = features1['topological_features'], features2['topological_features']
            topo_keys = set(t1.keys()) & set(t2.keys())
            if topo_keys:
                topo_sims = [1 - abs(t1[k] - t2[k]) for k in topo_keys]
                topo_sim = np.mean(topo_sims)
                total_similarity += weights['topological'] * topo_sim
                total_weight += weights['topological']
        
        return total_similarity / total_weight if total_weight > 0 else 0
    
    def _analyze_quality(self, detection: DetectionResult, image: np.ndarray) -> List[Dict[str, Any]]:
        """分析零件质量"""
        defects = []
        
        # 1. 对称性缺陷
        if detection.symmetry_score < self.defect_thresholds['symmetry_deviation']:
            defects.append({
                'type': 'symmetry_defect',
                'severity': 1 - detection.symmetry_score,
                'description': f'对称性不足: {detection.symmetry_score:.3f}'
            })
        
        # 2. 提取检测区域进行详细分析
        x, y, w, h = detection.bounding_box
        region = image[y:y+h, x:x+w]
        
        if region.size > 0:
            # 3. 圆度检查
            circularity = self._compute_circularity(region)
            if circularity < self.defect_thresholds['circularity_threshold']:
                defects.append({
                    'type': 'shape_defect',
                    'severity': 1 - circularity,
                    'description': f'形状不规则: 圆度 {circularity:.3f}'
                })
            
            # 4. 边缘连续性检查
            edge_continuity = self._compute_edge_continuity(region)
            if edge_continuity < self.defect_thresholds['edge_continuity_threshold']:
                defects.append({
                    'type': 'edge_defect',
                    'severity': 1 - edge_continuity,
                    'description': f'边缘不连续: {edge_continuity:.3f}'
                })
        
        return defects
    
    def _compute_circularity(self, region: np.ndarray) -> float:
        """计算圆度"""
        contours, _ = cv2.findContours(region, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return 0
        
        contour = max(contours, key=cv2.contourArea)
        area = cv2.contourArea(contour)
        perimeter = cv2.arcLength(contour, True)
        
        if perimeter == 0:
            return 0
        
        circularity = (4 * np.pi * area) / (perimeter ** 2)
        return min(circularity, 1.0)  # 最大为1
    
    def _compute_edge_continuity(self, region: np.ndarray) -> float:
        """计算边缘连续性"""
        edges = cv2.Canny(region, 50, 150)
        
        if np.sum(edges) == 0:
            return 0
        
        # 计算边缘点的连通性
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return 0
        
        # 最长轮廓占总边缘的比例
        main_contour_length = max(cv2.arcLength(c, True) for c in contours)
        total_edge_length = np.sum(edges > 0)
        
        if total_edge_length == 0:
            return 0
        
        continuity = main_contour_length / total_edge_length
        return min(continuity, 1.0)
    
    def _non_maximum_suppression(self, detections: List[DetectionResult], iou_threshold: float = 0.5) -> List[DetectionResult]:
        """非极大值抑制"""
        if not detections:
            return []
        
        # 按置信度排序
        detections.sort(key=lambda x: x.confidence, reverse=True)
        
        keep = []
        while detections:
            # 取最高置信度的检测
            best = detections.pop(0)
            keep.append(best)
            
            # 移除与当前检测重叠度高的检测
            detections = [det for det in detections 
                         if self._compute_iou(best.bounding_box, det.bounding_box) < iou_threshold]
        
        return keep
    
    def _compute_iou(self, box1: Tuple[int, int, int, int], box2: Tuple[int, int, int, int]) -> float:
        """计算IoU"""
        x1, y1, w1, h1 = box1
        x2, y2, w2, h2 = box2
        
        # 计算交集
        xi1 = max(x1, x2)
        yi1 = max(y1, y2)
        xi2 = min(x1 + w1, x2 + w2)
        yi2 = min(y1 + h1, y2 + h2)
        
        inter_area = max(0, xi2 - xi1) * max(0, yi2 - yi1)
        
        # 计算并集
        box1_area = w1 * h1
        box2_area = w2 * h2
        union_area = box1_area + box2_area - inter_area
        
        return inter_area / union_area if union_area > 0 else 0
    
    def _visualize_results(self, original_image: np.ndarray, detections: List[DetectionResult], processed_image: np.ndarray):
        """可视化结果"""
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        
        # 原始图像
        axes[0, 0].imshow(original_image, cmap='gray')
        axes[0, 0].set_title('原始图像')
        axes[0, 0].axis('off')
        
        # 处理后的图像
        axes[0, 1].imshow(processed_image, cmap='gray')
        axes[0, 1].set_title('预处理后图像')
        axes[0, 1].axis('off')
        
        # 检测结果
        result_image = cv2.cvtColor(original_image, cv2.COLOR_GRAY2BGR) if len(original_image.shape) == 2 else original_image.copy()
        
        for detection in detections:
            x, y, w, h = detection.bounding_box
            cx, cy = detection.center
            
            # 绘制边界框
            color = (0, 255, 0) if not detection.defects else (255, 0, 0)
            cv2.rectangle(result_image, (x, y), (x + w, y + h), color, 2)
            
            # 绘制中心点和方向
            cv2.circle(result_image, (cx, cy), 5, color, -1)
            
            # 绘制方向线
            angle_rad = np.deg2rad(detection.orientation)
            line_length = min(w, h) // 2
            end_x = int(cx + line_length * np.cos(angle_rad))
            end_y = int(cy - line_length * np.sin(angle_rad))
            cv2.arrowedLine(result_image, (cx, cy), (end_x, end_y), color, 2)
            
            # 添加标签
            label = f"{detection.part_type.value}: {detection.confidence:.2f}"
            cv2.putText(result_image, label, (x, y - 10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
            
            # 添加对称性分数
            sym_label = f"Sym: {detection.symmetry_score:.2f}"
            cv2.putText(result_image, sym_label, (x, y + h + 20), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
        
        axes[1, 0].imshow(cv2.cvtColor(result_image, cv2.COLOR_BGR2RGB))
        axes[1, 0].set_title('检测结果')
        axes[1, 0].axis('off')
        
        # 质量分析
        if detections:
            part_types = [det.part_type.value for det in detections]
            confidences = [det.confidence for det in detections]
            symmetry_scores = [det.symmetry_score for det in detections]
            defect_counts = [len(det.defects) for det in detections]
            
            x = range(len(detections))
            width = 0.25
            
            axes[1, 1].bar([i - width for i in x], confidences, width, label='置信度', alpha=0.7)
            axes[1, 1].bar(x, symmetry_scores, width, label='对称性', alpha=0.7)
            axes[1, 1].bar([i + width for i in x], [c/10 for c in defect_counts], width, label='缺陷数/10', alpha=0.7)
            
            axes[1, 1].set_xlabel('检测序号')
            axes[1, 1].set_ylabel('分数')
            axes[1, 1].set_title('质量分析')
            axes[1, 1].set_xticks(x)
            axes[1, 1].set_xticklabels([f"#{i}" for i in range(len(detections))])
            axes[1, 1].legend()
            axes[1, 1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.show()
        
        # 打印详细结果
        print("\n" + "="*50)
        print("检测结果详情:")
        print("="*50)
        for i, detection in enumerate(detections):
            print(f"\n零件 #{i}:")
            print(f"  类型: {detection.part_type.value}")
            print(f"  置信度: {detection.confidence:.3f}")
            print(f"  对称性分数: {detection.symmetry_score:.3f}")
            print(f"  位置: {detection.center}")
            print(f"  方向: {detection.orientation:.1f}°")
            print(f"  缺陷数量: {len(detection.defects)}")
            
            for defect in detection.defects:
                print(f"    - {defect['description']} (严重度: {defect['severity']:.3f})")

def generate_simulated_templates():
    """生成模拟零件模板"""
    import os
    os.makedirs("simulated_templates", exist_ok=True)
    
    for part_type in [PartType.GEAR, PartType.BEARING, PartType.BOLT, PartType.WASHER]:
        os.makedirs(f"simulated_templates/{part_type.value}", exist_ok=True)
        
        # 为每种零件生成多个模板
        for i in range(3):
            template = create_part_template(part_type, variation=i)
            cv2.imwrite(f"simulated_templates/{part_type.value}/template_{i}.png", template)

def create_part_template(part_type: PartType, variation: int = 0) -> np.ndarray:
    """创建零件模板"""
    size = 200
    template = np.zeros((size, size), dtype=np.uint8)
    center = (size // 2, size // 2)
    
    if part_type == PartType.GEAR:
        # 齿轮模板
        cv2.circle(template, center, 60, 255, -1)
        cv2.circle(template, center, 30, 0, -1)
        
        # 齿轮齿
        for angle in range(0, 360, 30):
            angle_rad = np.deg2rad(angle)
            x1 = int(center[0] + 60 * np.cos(angle_rad))
            y1 = int(center[1] + 60 * np.sin(angle_rad))
            x2 = int(center[0] + 80 * np.cos(angle_rad))
            y2 = int(center[1] + 80 * np.sin(angle_rad))
            cv2.line(template, (x1, y1), (x2, y2), 255, 8)
    
    elif part_type == PartType.BEARING:
        # 轴承模板
        cv2.circle(template, center, 70, 255, 15)
        cv2.circle(template, center, 40, 255, 10)
        
        # 滚珠
        for angle in range(0, 360, 45):
            angle_rad = np.deg2rad(angle)
            x = int(center[0] + 55 * np.cos(angle_rad))
            y = int(center[1] + 55 * np.sin(angle_rad))
            cv2.circle(template, (x, y), 8, 255, -1)
    
    elif part_type == PartType.BOLT:
        # 螺栓模板
        cv2.circle(template, center, 25, 255, -1)
        cv2.rectangle(template, (center[0] - 15, center[1] - 50), 
                     (center[0] + 15, center[1] + 50), 255, -1)
        
        # 螺纹
        for y in range(center[1] - 40, center[1] + 40, 10):
            cv2.line(template, (center[0] - 20, y), (center[0] + 20, y), 255, 2)
    
    elif part_type == PartType.WASHER:
        # 垫圈模板
        cv2.circle(template, center, 50, 255, -1)
        cv2.circle(template, center, 25, 0, -1)
    
    # 添加一些变化
    if variation == 1:
        # 旋转变化
        angle = 15
        M = cv2.getRotationMatrix2D(center, angle, 1)
        template = cv2.warpAffine(template, M, (size, size))
    elif variation == 2:
        # 轻微形变
        pts1 = np.float32([[0,0], [size,0], [0,size], [size,size]])
        pts2 = np.float32([[5,5], [size-5,5], [5,size-5], [size-5,size-5]])
        M = cv2.getPerspectiveTransform(pts1, pts2)
        template = cv2.warpPerspective(template, M, (size, size))
    
    return template

def generate_test_image() -> np.ndarray:
    """生成更好的测试图像 - 修复零件放置问题"""
    width, height = 800, 600
    # 创建更清晰的背景
    image = np.random.randint(80, 120, (height, width), dtype=np.uint8)
    
    # 添加轻微的纹理
    noise = np.random.normal(0, 5, (height, width)).astype(np.uint8)
    image = cv2.add(image, noise)
    
    # 添加多个零件实例 (不同位置、旋转、尺度)
    parts = [
        (PartType.GEAR, (200, 150), 0.9, 30),
        (PartType.BEARING, (400, 200), 1.0, -15),
        (PartType.BOLT, (600, 300), 0.8, 45),
        (PartType.WASHER, (300, 400), 1.0, 0),
        (PartType.GEAR, (500, 450), 0.7, 60),  # 有缺陷的齿轮
    ]
    
    for part_type, position, scale, angle in parts:
        template = create_part_template(part_type)
        
        # 应用变换
        if scale != 1.0:
            new_size = int(200 * scale)
            template = cv2.resize(template, (new_size, new_size))
        
        if angle != 0:
            center = (template.shape[1] // 2, template.shape[0] // 2)
            M = cv2.getRotationMatrix2D(center, angle, 1)
            template = cv2.warpAffine(template, M, template.shape[:2])
        
        # 随机添加一些缺陷
        if position == (500, 450):  # 有缺陷的齿轮
            # 添加缺失的齿
            cv2.rectangle(template, (120, 90), (140, 110), 0, -1)
            # 添加划痕
            cv2.line(template, (50, 50), (80, 80), 0, 3)
        
        # 将模板放置到图像中 - 修复放置逻辑
        x, y = position
        h, w = template.shape
        
        # 确保零件完全在图像内
        x_start = max(0, x - w // 2)
        y_start = max(0, y - h // 2)
        x_end = min(width, x_start + w)
        y_end = min(height, y_start + h)
        
        # 调整模板大小以匹配ROI
        template_cropped = template[0:y_end-y_start, 0:x_end-x_start]
        
        # 使用更清晰的混合方式
        roi = image[y_start:y_end, x_start:x_end]
        mask = template_cropped > 127
        
        # 直接替换区域，避免模糊
        roi[mask] = 255  # 设置为白色前景
        roi[~mask] = roi[~mask]  # 保持背景不变
    
    # 添加轻微的噪声
    salt_pepper = np.random.random(image.shape) > 0.98
    image[salt_pepper] = 255
    
    return image

def generate_quality_report(results: List[DetectionResult]):
    """生成质量报告 - 修复除以零错误"""
    print("\n" + "="*60)
    print("工业零件质量检测报告")
    print("="*60)
    
    total_parts = len(results)
    
    if total_parts == 0:
        print("未检测到任何零件！")
        print("可能的原因：")
        print("1. 图像质量问题")
        print("2. 模板匹配阈值过高")
        print("3. 预处理参数需要调整")
        return
    
    defective_parts = sum(1 for r in results if r.defects)
    quality_scores = [r.confidence * r.symmetry_score for r in results]
    
    print(f"检测零件总数: {total_parts}")
    print(f"有缺陷零件数: {defective_parts}")
    print(f"合格率: {(total_parts - defective_parts) / total_parts * 100:.1f}%")
    print(f"平均质量分数: {np.mean(quality_scores):.3f}")
    
    # 按零件类型统计
    type_stats = {}
    for result in results:
        part_type = result.part_type.value
        if part_type not in type_stats:
            type_stats[part_type] = {'count': 0, 'defects': 0, 'avg_confidence': 0}
        
        type_stats[part_type]['count'] += 1
        if result.defects:
            type_stats[part_type]['defects'] += 1
        type_stats[part_type]['avg_confidence'] += result.confidence
    
    print("\n按零件类型统计:")
    for part_type, stats in type_stats.items():
        avg_conf = stats['avg_confidence'] / stats['count']
        defect_rate = stats['defects'] / stats['count'] * 100
        print(f"  {part_type}: {stats['count']}个, 缺陷率: {defect_rate:.1f}%, 平均置信度: {avg_conf:.3f}")
    
    # 缺陷类型分析
    defect_types = {}
    for result in results:
        for defect in result.defects:
            defect_type = defect['type']
            if defect_type not in defect_types:
                defect_types[defect_type] = 0
            defect_types[defect_type] += 1
    
    if defect_types:
        print("\n缺陷类型分析:")
        for defect_type, count in defect_types.items():
            print(f"  {defect_type}: {count}次")

def debug_detection_process(detector: IndustrialGroupTheoryDetector, image: np.ndarray):
    """调试检测过程"""
    print("\n=== 调试信息 ===")
    
    # 预处理图像
    processed = detector._preprocess_image(image)
    
    # 检测候选区域
    regions = detector._detect_candidate_regions(processed)
    print(f"找到候选区域: {len(regions)} 个")
    
    # 显示每个区域
    for i, region in enumerate(regions):
        area = region['area']
        bbox = region['bbox']
        print(f"区域 {i}: 面积={area}, 边界框={bbox}")
        
        # 检查区域特征
        try:
            features = detector._extract_group_theory_features(region['region_image'])
            print(f"  特征提取成功: Zernike矩长度={len(features['zernike_moments'])}")
        except Exception as e:
            print(f"  特征提取失败: {e}")

def simulate_industrial_scenario():
    """模拟真实工业检测场景 - 改进版本"""
    print("初始化工业视觉检测系统...")
    
    # 创建检测器
    detector = IndustrialGroupTheoryDetector()
    
    # 降低相似度阈值以提高检测率
    detector.similarity_threshold = 0.1
    detector.min_contour_area = 500  # 降低最小面积要求
    
    # 生成模拟的零件模板数据库
    print("\n生成模拟零件模板...")
    generate_simulated_templates()
    
    # 加载模板数据库
    detector.load_template_database("simulated_templates")
    
    # 生成测试图像 (模拟真实工业场景)
    print("\n生成测试图像...")
    test_image = generate_test_image()
    
    # 调试检测过程
    debug_detection_process(detector, test_image)
    
    # 执行检测
    print("\n开始零件检测...")
    results = detector.detect_parts(test_image, visualize=True)
    
    # 生成质量报告
    generate_quality_report(results)
    
    return results

# 在文件末尾的if __name__ == "__main__":部分添加错误处理
if __name__ == "__main__":
    try:
        # 运行完整的工业检测演示
        results = simulate_industrial_scenario()
        
        if not results:
            print("\n警告：没有检测到任何零件！")
            print("建议调整以下参数：")
            print("1. 降低 similarity_threshold")
            print("2. 降低 min_contour_area") 
            print("3. 检查模板图像质量")
            print("4. 调整预处理参数")
            
    except Exception as e:
        print(f"程序执行出错: {e}")
        import traceback
        traceback.print_exc()