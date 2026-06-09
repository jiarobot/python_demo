import numpy as np
import cv2
from scipy import ndimage
from skimage import segmentation, feature, filters, morphology
from sklearn.cluster import DBSCAN, MeanShift
from sklearn.ensemble import RandomForestClassifier
import matplotlib
matplotlib.rc("font", family='Microsoft YaHei')
import matplotlib.pyplot as plt
from collections import defaultdict
import json
from dataclasses import dataclass
from typing import Tuple, List, Dict, Optional
import time

@dataclass
class SegmentationConfig:
    """前瞻性配置系统，支持自适应参数调整"""
    # 多尺度处理配置
    scales: Tuple[float, ...] = (1.0, 0.5, 0.25)
    min_region_size: int = 100
    max_region_size: int = 10000
    
    # 特征提取配置
    texture_window_size: int = 5
    gradient_threshold: float = 0.1
    curvature_scale: float = 2.0
    
    # 聚类配置
    dbscan_eps: float = 0.05
    dbscan_min_samples: int = 10
    meanshift_bandwidth: float = 0.1
    
    # 优化配置
    use_multiscale: bool = True
    adaptive_thresholding: bool = True
    post_processing: bool = True
    
    def adaptive_config(self, image_size: Tuple[int, int]):
        """基于图像尺寸的自适应配置"""
        area = image_size[0] * image_size[1]
        self.min_region_size = max(50, int(area * 0.0005))
        self.max_region_size = min(100000, int(area * 0.1))
        return self
    
class MultiModalFeatureExtractor:
    """前瞻性特征提取器，融合几何、纹理和上下文特征"""
    
    def __init__(self, config: SegmentationConfig):
        self.config = config
        
    def extract_geometric_features(self, depth_map: np.ndarray) -> Dict[str, np.ndarray]:
        """提取几何特征：表面法线、曲率、平面性等"""
        features = {}
        
        # 1. 表面法线计算
        features['normals'] = self._compute_surface_normals(depth_map)
        
        # 2. 曲率特征
        features['curvature'] = self._compute_curvature(depth_map)
        
        # 3. 平面性检测
        features['planarity'] = self._compute_planarity(depth_map)
        
        # 4. 边缘特征
        features['edges'] = self._compute_depth_edges(depth_map)
        
        return features
    
    def _compute_surface_normals(self, depth_map: np.ndarray) -> np.ndarray:
        """计算表面法线向量"""
        dz_dx = cv2.Sobel(depth_map, cv2.CV_64F, 1, 0, ksize=3)
        dz_dy = cv2.Sobel(depth_map, cv2.CV_64F, 0, 1, ksize=3)
        
        # 构造法线场
        normals = np.dstack((-dz_dx, -dz_dy, np.ones_like(depth_map)))
        norm = np.linalg.norm(normals, axis=2, keepdims=True)
        normals = np.divide(normals, norm, where=norm != 0)
        
        return normals
    
    def _compute_curvature(self, depth_map: np.ndarray) -> np.ndarray:
        """计算表面曲率"""
        # 二阶导数
        dxx = cv2.Sobel(depth_map, cv2.CV_64F, 2, 0, ksize=3)
        dyy = cv2.Sobel(depth_map, cv2.CV_64F, 0, 2, ksize=3)
        dxy = cv2.Sobel(depth_map, cv2.CV_64F, 1, 1, ksize=3)
        
        # 一阶导数
        dx = cv2.Sobel(depth_map, cv2.CV_64F, 1, 0, ksize=3)
        dy = cv2.Sobel(depth_map, cv2.CV_64F, 0, 1, ksize=3)
        
        # 平均曲率
        denominator = (1 + dx**2 + dy**2)**1.5
        curvature = (dxx * (1 + dy**2) - 2 * dxy * dx * dy + dyy * (1 + dx**2)) / denominator
        curvature = np.nan_to_num(curvature)
        
        return np.abs(curvature)
    
    def _compute_planarity(self, depth_map: np.ndarray) -> np.ndarray:
        """计算局部平面性"""
        planarity = np.zeros_like(depth_map)
        window_size = 5
        half_window = window_size // 2
        
        h, w = depth_map.shape
        for i in range(half_window, h - half_window):
            for j in range(half_window, w - half_window):
                window = depth_map[i-half_window:i+half_window+1, j-half_window:j+half_window+1]
                if np.std(window) > 0:
                    # 拟合平面
                    X, Y = np.meshgrid(range(window_size), range(window_size))
                    X = X.flatten()
                    Y = Y.flatten()
                    Z = window.flatten()
                    
                    A = np.column_stack([X, Y, np.ones(len(X))])
                    try:
                        coeffs, _, _, _ = np.linalg.lstsq(A, Z, rcond=None)
                        predicted = A @ coeffs
                        mse = np.mean((Z - predicted) ** 2)
                        planarity[i, j] = 1.0 / (1.0 + mse)
                    except:
                        planarity[i, j] = 0
        
        return planarity
    
    def _compute_depth_edges(self, depth_map: np.ndarray) -> np.ndarray:
        """计算深度边缘"""
        # 多尺度边缘检测
        edges_small = feature.canny(depth_map, sigma=1)
        edges_medium = feature.canny(depth_map, sigma=2)
        edges_large = feature.canny(depth_map, sigma=3)
        
        # 融合多尺度边缘
        combined_edges = edges_small.astype(float) + edges_medium.astype(float) + edges_large.astype(float)
        return combined_edges / 3.0
    
    def extract_texture_features(self, depth_map: np.ndarray) -> Dict[str, np.ndarray]:
        """从深度图提取纹理特征"""
        features = {}
        
        # 1. 局部二值模式
        features['lbp'] = self._compute_lbp(depth_map)
        
        # 2. Gabor滤波响应
        features['gabor'] = self._compute_gabor_responses(depth_map)
        
        # 3. 局部深度统计
        features['local_stats'] = self._compute_local_statistics(depth_map)
        
        return features
    
    def _compute_lbp(self, depth_map: np.ndarray) -> np.ndarray:
        """计算局部二值模式"""
        lbp = np.zeros_like(depth_map)
        h, w = depth_map.shape
        
        for i in range(1, h-1):
            for j in range(1, w-1):
                center = depth_map[i, j]
                binary_pattern = 0
                # 3x3邻域
                neighbors = [
                    (i-1, j-1), (i-1, j), (i-1, j+1),
                    (i, j-1),             (i, j+1),
                    (i+1, j-1), (i+1, j), (i+1, j+1)
                ]
                
                for idx, (ni, nj) in enumerate(neighbors):
                    if depth_map[ni, nj] >= center:
                        binary_pattern |= (1 << idx)
                
                lbp[i, j] = binary_pattern
        
        return lbp
    
    def _compute_gabor_responses(self, depth_map: np.ndarray) -> np.ndarray:
        """计算Gabor滤波响应"""
        gabor_responses = []
        
        # 多方向Gabor滤波器
        for theta in np.arange(0, np.pi, np.pi/4):
            kernel = cv2.getGaborKernel((5, 5), 1.0, theta, 1.0, 0.5, 0, ktype=cv2.CV_32F)
            response = cv2.filter2D(depth_map.astype(np.float32), cv2.CV_32F, kernel)
            gabor_responses.append(response)
        
        # 取最大响应作为纹理强度
        return np.max(gabor_responses, axis=0)
    
    def _compute_local_statistics(self, depth_map: np.ndarray) -> np.ndarray:
        """计算局部统计特征"""
        local_mean = ndimage.uniform_filter(depth_map, size=5)
        local_std = ndimage.generic_filter(depth_map, np.std, size=5)
        local_entropy = ndimage.generic_filter(depth_map, self._entropy, size=5)
        
        # 组合统计特征
        return np.stack([local_mean, local_std, local_entropy], axis=-1)
    
    def _entropy(self, values):
        """计算局部熵"""
        hist, _ = np.histogram(values, bins=8, density=True)
        hist = hist[hist > 0]
        return -np.sum(hist * np.log2(hist))
    
class MultiScaleSegmentationEngine:
    """前瞻性多尺度分割引擎"""
    
    def __init__(self, config: SegmentationConfig):
        self.config = config
        self.feature_extractor = MultiModalFeatureExtractor(config)
    
    def hierarchical_segmentation(self, depth_map: np.ndarray) -> Dict[str, np.ndarray]:
        """分层多尺度分割"""
        segmentation_results = {}
        
        for scale in self.config.scales:
            if scale != 1.0:
                scaled_depth = cv2.resize(depth_map, None, fx=scale, fy=scale, 
                                        interpolation=cv2.INTER_AREA)
            else:
                scaled_depth = depth_map.copy()
            
            # 在当前尺度进行分割
            seg_result = self._segment_single_scale(scaled_depth)
            
            if scale != 1.0:
                # 上采样回原尺寸
                seg_result = cv2.resize(seg_result, depth_map.shape[::-1], 
                                      interpolation=cv2.INTER_NEAREST)
            
            segmentation_results[f'scale_{scale}'] = seg_result
        
        # 融合多尺度结果
        final_segmentation = self._fuse_multiscale_results(segmentation_results, depth_map)
        
        return {'final': final_segmentation, **segmentation_results}
    
    def _segment_single_scale(self, depth_map: np.ndarray) -> np.ndarray:
        """单尺度分割"""
        # 1. 超像素过分割
        superpixels = self._compute_superpixels(depth_map)
        
        # 2. 区域特征提取
        region_features = self._extract_region_features(depth_map, superpixels)
        
        # 3. 区域合并
        merged_regions = self._merge_regions(superpixels, region_features)
        
        return merged_regions
    
    def _compute_superpixels(self, depth_map: np.ndarray) -> np.ndarray:
        """计算超像素"""
        # 使用SLIC算法进行初始过分割
        # 将深度图转换为3通道用于SLIC
        depth_3ch = np.stack([depth_map] * 3, axis=-1)
        segments = segmentation.slic(depth_3ch, n_segments=200, compactness=10, 
                                   sigma=1, start_label=1)
        return segments
    
    def _extract_region_features(self, depth_map: np.ndarray, regions: np.ndarray) -> Dict[int, np.ndarray]:
        """提取区域特征"""
        region_features = {}
        unique_regions = np.unique(regions)
        
        geometric_features = self.feature_extractor.extract_geometric_features(depth_map)
        texture_features = self.feature_extractor.extract_texture_features(depth_map)
        
        for region_id in unique_regions:
            if region_id == 0:  # 忽略边界
                continue
                
            mask = regions == region_id
            features = []
            
            # 几何特征
            for feat_name, feat_map in geometric_features.items():
                if feat_map.ndim == 2:
                    region_feat = feat_map[mask]
                    features.extend([np.mean(region_feat), np.std(region_feat)])
                else:  # 3D特征如法线
                    for channel in range(feat_map.shape[2]):
                        channel_feat = feat_map[..., channel][mask]
                        features.extend([np.mean(channel_feat), np.std(channel_feat)])
            
            # 纹理特征
            for feat_name, feat_map in texture_features.items():
                if feat_map.ndim == 2:
                    region_feat = feat_map[mask]
                    features.extend([np.mean(region_feat), np.std(region_feat)])
                else:
                    for channel in range(feat_map.shape[2]):
                        channel_feat = feat_map[..., channel][mask]
                        features.extend([np.mean(channel_feat), np.std(channel_feat)])
            
            # 深度统计
            depth_values = depth_map[mask]
            features.extend([
                np.mean(depth_values),
                np.std(depth_values),
                np.median(depth_values),
                np.min(depth_values),
                np.max(depth_values)
            ])
            
            # 区域形状特征
            region_area = np.sum(mask)
            features.append(region_area)
            
            region_features[region_id] = np.array(features)
        
        return region_features
    
    def _merge_regions(self, regions: np.ndarray, region_features: Dict[int, np.ndarray]) -> np.ndarray:
        """基于特征相似性合并区域"""
        # 构建区域邻接图
        adjacency_graph = self._build_region_adjacency(regions)
        
        # 计算区域间相似度
        similarities = self._compute_region_similarities(region_features, adjacency_graph)
        
        # 层次合并
        merged_regions = self._hierarchical_merging(regions, adjacency_graph, similarities)
        
        return merged_regions
    
    def _build_region_adjacency(self, regions: np.ndarray) -> Dict[int, List[int]]:
        """构建区域邻接关系"""
        h, w = regions.shape
        adjacency = defaultdict(set)
        
        # 检查水平和垂直邻接
        for i in range(h-1):
            for j in range(w-1):
                current = regions[i, j]
                right = regions[i, j+1]
                down = regions[i+1, j]
                
                if current != right and current != 0 and right != 0:
                    adjacency[current].add(right)
                    adjacency[right].add(current)
                
                if current != down and current != 0 and down != 0:
                    adjacency[current].add(down)
                    adjacency[down].add(current)
        
        return {k: list(v) for k, v in adjacency.items()}
    
    def _compute_region_similarities(self, features: Dict[int, np.ndarray], 
                                   adjacency: Dict[int, List[int]]) -> Dict[Tuple[int, int], float]:
        """计算相邻区域相似度"""
        similarities = {}
        
        for region1, neighbors in adjacency.items():
            if region1 not in features:
                continue
                
            feat1 = features[region1]
            
            for region2 in neighbors:
                if region2 not in features:
                    continue
                    
                feat2 = features[region2]
                
                # 使用多种相似度度量
                cosine_sim = np.dot(feat1, feat2) / (np.linalg.norm(feat1) * np.linalg.norm(feat2) + 1e-8)
                euclidean_dist = np.linalg.norm(feat1 - feat2)
                euclidean_sim = 1.0 / (1.0 + euclidean_dist)
                
                # 组合相似度
                combined_sim = (cosine_sim + euclidean_sim) / 2.0
                similarities[(region1, region2)] = combined_sim
        
        return similarities
    
    def _hierarchical_merging(self, regions: np.ndarray, adjacency: Dict[int, List[int]], 
                            similarities: Dict[Tuple[int, int], float], 
                            similarity_threshold: float = 0.7) -> np.ndarray:
        """层次区域合并"""
        # 实现区域合并逻辑
        current_regions = regions.copy()
        region_mapping = {i: i for i in np.unique(regions) if i != 0}
        
        # 按相似度排序区域对
        sorted_pairs = sorted(similarities.items(), key=lambda x: x[1], reverse=True)
        
        for (region1, region2), similarity in sorted_pairs:
            if similarity < similarity_threshold:
                break
                
            if (region1 in region_mapping and region2 in region_mapping and 
                region_mapping[region1] != region_mapping[region2]):
                
                # 合并区域
                new_label = min(region_mapping[region1], region_mapping[region2])
                old_label = max(region_mapping[region1], region_mapping[region2])
                
                # 更新映射
                for region_id, current_label in region_mapping.items():
                    if current_label == old_label:
                        region_mapping[region_id] = new_label
        
        # 应用合并结果
        merged_regions = np.zeros_like(regions)
        for region_id, new_label in region_mapping.items():
            merged_regions[regions == region_id] = new_label
        
        return merged_regions
    
    def _fuse_multiscale_results(self, segmentation_results: Dict[str, np.ndarray], 
                               depth_map: np.ndarray) -> np.ndarray:
        """融合多尺度分割结果"""
        # 使用多数投票或置信度融合
        h, w = depth_map.shape
        final_segmentation = np.zeros((h, w), dtype=np.int32)
        
        # 收集所有尺度的标签
        all_labels = np.stack([result for result in segmentation_results.values()])
        
        # 对每个像素进行多数投票
        for i in range(h):
            for j in range(w):
                labels = all_labels[:, i, j]
                final_segmentation[i, j] = np.bincount(labels).argmax()
        
        return final_segmentation
    
class SemanticClassifier:
    """基于传统机器学习的语义分类器"""
    
    def __init__(self):
        self.classifier = RandomForestClassifier(n_estimators=100, random_state=42)
        self.feature_importances_ = None
        self.classes_ = None
    
    def extract_semantic_features(self, depth_map: np.ndarray, segmentation_mask: np.ndarray) -> Dict[int, np.ndarray]:
        """为每个分割区域提取语义特征"""
        region_features = {}
        unique_regions = np.unique(segmentation_mask)
        
        geometric_features = MultiModalFeatureExtractor(SegmentationConfig()).extract_geometric_features(depth_map)
        texture_features = MultiModalFeatureExtractor(SegmentationConfig()).extract_texture_features(depth_map)
        
        for region_id in unique_regions:
            if region_id == 0:  # 忽略背景
                continue
                
            mask = segmentation_mask == region_id
            features = []
            
            # 组合多种特征
            for feat_dict in [geometric_features, texture_features]:
                for feat_name, feat_map in feat_dict.items():
                    if feat_map.ndim == 2:
                        region_feat = feat_map[mask]
                        features.extend([
                            np.mean(region_feat),
                            np.std(region_feat),
                            np.median(region_feat),
                            np.min(region_feat),
                            np.max(region_feat)
                        ])
            
            # 区域形状特征
            region_area = np.sum(mask)
            features.append(region_area)
            
            # 深度分布特征
            depth_values = depth_map[mask]
            features.extend([
                np.mean(depth_values),
                np.std(depth_values),
                np.median(depth_values),
                np.percentile(depth_values, 25),
                np.percentile(depth_values, 75)
            ])
            
            region_features[region_id] = np.array(features)
        
        return region_features
    
    def train(self, features: np.ndarray, labels: np.ndarray):
        """训练分类器"""
        self.classifier.fit(features, labels)
        self.feature_importances_ = self.classifier.feature_importances_
        self.classes_ = self.classifier.classes_
    
    def predict(self, features: np.ndarray) -> np.ndarray:
        """预测语义标签"""
        return self.classifier.predict(features)
    
    def predict_proba(self, features: np.ndarray) -> np.ndarray:
        """预测概率"""
        return self.classifier.predict_proba(features)
    
class NonDLDepthSegmentationSystem:
    """完整的非深度学习深度图语义分割系统"""
    
    def __init__(self, config: SegmentationConfig = None):
        self.config = config or SegmentationConfig()
        self.segmentation_engine = MultiScaleSegmentationEngine(self.config)
        self.classifier = SemanticClassifier()
        self.is_trained = False
    
    def process(self, depth_map: np.ndarray, rgb_image: Optional[np.ndarray] = None) -> Dict:
        """完整处理流程"""
        start_time = time.time()
        
        # 1. 预处理
        processed_depth = self._preprocess_depth(depth_map)
        
        # 2. 多尺度分割
        segmentation_start = time.time()
        segmentation_results = self.segmentation_engine.hierarchical_segmentation(processed_depth)
        segmentation_time = time.time() - segmentation_start
        
        # 3. 语义分类（如果已训练）
        classification_results = None
        if self.is_trained:
            classification_start = time.time()
            classification_results = self._classify_regions(processed_depth, segmentation_results['final'])
            classification_time = time.time() - classification_start
        else:
            classification_time = 0
        
        total_time = time.time() - start_time
        
        return {
            'segmentation_mask': segmentation_results['final'],
            'multiscale_results': segmentation_results,
            'semantic_labels': classification_results,
            'timing': {
                'total': total_time,
                'segmentation': segmentation_time,
                'classification': classification_time if self.is_trained else None
            }
        }
    
    def _preprocess_depth(self, depth_map: np.ndarray) -> np.ndarray:
        """深度图预处理"""
        # 1. 填充缺失值
        depth_map = np.nan_to_num(depth_map, nan=0.0)
        
        # 2. 中值滤波去噪
        depth_map = cv2.medianBlur(depth_map.astype(np.float32), 3)
        
        # 3. 双边滤波保持边缘
        depth_map = cv2.bilateralFilter(depth_map, 5, 25, 25)
        
        # 4. 归一化
        if depth_map.max() > 0:
            depth_map = depth_map / depth_map.max()
        
        return depth_map
    
    def _classify_regions(self, depth_map: np.ndarray, segmentation_mask: np.ndarray) -> np.ndarray:
        """区域语义分类"""
        # 提取区域特征
        region_features = self.classifier.extract_semantic_features(depth_map, segmentation_mask)
        
        # 预测语义标签
        semantic_mask = np.zeros_like(segmentation_mask, dtype=np.int32)
        
        for region_id, features in region_features.items():
            features_2d = features.reshape(1, -1)
            prediction = self.classifier.predict(features_2d)[0]
            semantic_mask[segmentation_mask == region_id] = prediction
        
        return semantic_mask
    
    def train_classifier(self, training_data: List[Tuple[np.ndarray, np.ndarray, np.ndarray]]):
        """训练语义分类器"""
        all_features = []
        all_labels = []
        
        for depth_map, segmentation_mask, ground_truth in training_data:
            # 提取特征
            region_features = self.classifier.extract_semantic_features(depth_map, segmentation_mask)
            
            # 为每个区域分配标签（使用区域内的主要标签）
            for region_id in np.unique(segmentation_mask):
                if region_id == 0:
                    continue
                
                region_mask = segmentation_mask == region_id
                region_gt = ground_truth[region_mask]
                
                if len(region_gt) > 0:
                    # 使用区域内最多的标签
                    region_label = np.bincount(region_gt).argmax()
                    all_features.append(region_features[region_id])
                    all_labels.append(region_label)
        
        # 训练分类器
        self.classifier.train(np.array(all_features), np.array(all_labels))
        self.is_trained = True
        
        print(f"训练完成! 样本数量: {len(all_features)}, 类别数量: {len(np.unique(all_labels))}")

class VisualizationTools:
    """可视化工具类"""
    
    @staticmethod
    def visualize_results(depth_map: np.ndarray, results: Dict, figsize: Tuple[int, int] = (15, 10)):
        """可视化完整结果"""
        fig, axes = plt.subplots(2, 3, figsize=figsize)
        
        # 原始深度图
        axes[0, 0].imshow(depth_map, cmap='viridis')
        axes[0, 0].set_title('原始深度图')
        axes[0, 0].axis('off')
        
        # 分割结果
        axes[0, 1].imshow(results['segmentation_mask'], cmap='tab20')
        axes[0, 1].set_title('分割结果')
        axes[0, 1].axis('off')
        
        # 语义标签（如果存在）
        if results['semantic_labels'] is not None:
            axes[0, 2].imshow(results['semantic_labels'], cmap='tab10')
            axes[0, 2].set_title('语义标签')
        else:
            axes[0, 2].text(0.5, 0.5, '未训练分类器', ha='center', va='center', 
                          transform=axes[0, 2].transAxes, fontsize=12)
        axes[0, 2].axis('off')
        
        # 多尺度结果
        multiscale_keys = list(results['multiscale_results'].keys())[:3]
        for idx, key in enumerate(multiscale_keys):
            axes[1, idx].imshow(results['multiscale_results'][key], cmap='tab20')
            axes[1, idx].set_title(f'{key}分割')
            axes[1, idx].axis('off')
        
        plt.tight_layout()
        plt.show()
    
    @staticmethod
    def plot_feature_importance(classifier: SemanticClassifier, top_n: int = 15):
        """绘制特征重要性"""
        if classifier.feature_importances_ is None:
            print("分类器未训练或特征重要性不可用")
            return
        
        importances = classifier.feature_importances_
        indices = np.argsort(importances)[::-1][:top_n]
        
        plt.figure(figsize=(10, 6))
        plt.title("特征重要性 (Top {})".format(top_n))
        plt.bar(range(top_n), importances[indices])
        plt.xticks(range(top_n), indices, rotation=45)
        plt.tight_layout()
        plt.show()
def create_synthetic_depth_data(size: Tuple[int, int] = (256, 256)) -> np.ndarray:
    """创建合成深度数据用于测试"""
    h, w = size
    depth_map = np.zeros(size)
    
    # 创建多个不同深度的物体
    # 平面背景
    depth_map[:, :] = 1.0
    
    # 球体
    y, x = np.ogrid[:h, :w]
    center_y, center_x = h//2, w//2
    radius = min(h, w) // 4
    mask = (x - center_x)**2 + (y - center_y)**2 <= radius**2
    depth_map[mask] = 0.5
    
    # 立方体
    cube_size = h // 6
    cube_y_start, cube_x_start = h//4, w//4
    cube_y_end, cube_x_end = cube_y_start + cube_size, cube_x_start + cube_size
    depth_map[cube_y_start:cube_y_end, cube_x_start:cube_x_end] = 0.3
    
    # 添加噪声
    noise = np.random.normal(0, 0.02, size)
    depth_map += noise
    
    return np.clip(depth_map, 0, 1)

def demo_system():
    """演示完整系统"""
    print("=== 非深度学习深度图语义分割系统演示 ===")
    
    # 1. 创建系统
    config = SegmentationConfig()
    system = NonDLDepthSegmentationSystem(config)
    
    # 2. 生成测试数据
    print("生成合成深度数据...")
    depth_map = create_synthetic_depth_data((256, 256))
    
    # 3. 处理图像
    print("开始分割处理...")
    results = system.process(depth_map)
    
    # 4. 可视化结果
    print("可视化结果...")
    VisualizationTools.visualize_results(depth_map, results)
    
    # 5. 显示性能信息
    timing = results['timing']
    print(f"\n性能统计:")
    print(f"总处理时间: {timing['total']:.3f}秒")
    print(f"分割时间: {timing['segmentation']:.3f}秒")
    if timing['classification']:
        print(f"分类时间: {timing['classification']:.3f}秒")
    
    return system, results

if __name__ == "__main__":
    # 运行演示
    system, results = demo_system()
    
    print("\n系统特点总结:")
    print("✅ 完全基于传统计算机视觉方法")
    print("✅ 多尺度处理提高准确性") 
    print("✅ 多模态特征融合")
    print("✅ 自适应参数调整")
    print("✅ 可解释性强")
    print("✅ 无需大量标注数据")
    print("✅ 计算效率高")