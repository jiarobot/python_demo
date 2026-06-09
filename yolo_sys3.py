import sys
import os
import cv2
import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image, ImageDraw, ImageFont
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QFileDialog, QComboBox, 
                             QSlider, QSpinBox, QCheckBox, QGroupBox,
                             QMessageBox, QWidget, QProgressBar, QSplitter,
                             QTabWidget, QTextEdit, QTableWidget, QTableWidgetItem,
                             QHeaderView, QTreeWidget, QTreeWidgetItem, QListWidget,
                             QDoubleSpinBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QPixmap, QImage, QPainter, QPen, QColor, QFont, QIcon
import json
import time
from collections import defaultdict, deque
import math
from scipy import ndimage
from scipy.spatial import distance
import networkx as nx
from sklearn.cluster import DBSCAN
import matplotlib
matplotlib.use('Agg')  # 使用非GUI后端
import matplotlib.pyplot as plt
from io import BytesIO
import gc
import psutil
import threading

# ==================== 轻量级超神推理引擎 ====================

class LightweightHyperEngine:
    def __init__(self):
        self.cognitive_modules = {
            "智能感知": IntelligentPerception(),
            "关系推理": RelationReasoner(),
            "场景理解": LightSceneUnderstanding(),
            "行为分析": BehaviorAnalyzer(),
            "异常检测": LightAnomalyDetector(),
            "记忆系统": LightMemorySystem()
        }
        
        self.computation_budget = 1000  # 计算预算（毫秒）
        self.performance_monitor = PerformanceMonitor()
        self.adaptive_controller = AdaptiveComputationController()
        
    def efficient_analyze(self, detections, image, context=None):
        """高效分析 - 在算力限制下最大化洞察力"""
        start_time = time.time()
        results = {}
        remaining_budget = self.computation_budget
        
        # 根据可用算力智能分配计算资源
        module_priority = self.adaptive_controller.get_module_priority(detections, context)
        
        for module_name in module_priority:
            if remaining_budget <= 0:
                break
                
            module = self.cognitive_modules[module_name]
            module_budget = self.adaptive_controller.allocate_budget(
                module_name, remaining_budget, len(detections)
            )
            
            try:
                module_start = time.time()
                results[module_name] = module.analyze(detections, image, context)
                module_time = (time.time() - module_start) * 1000
                
                # 更新剩余预算
                remaining_budget -= module_time
                
                # 记录性能
                self.performance_monitor.record_module_performance(
                    module_name, module_time, len(detections)
                )
                
            except Exception as e:
                print(f"模块 {module_name} 执行失败: {e}")
                results[module_name] = {'error': str(e)}
        
        # 智能整合结果
        if results:
            results['智能整合'] = self._lightweight_integration(results, detections)
        
        total_time = (time.time() - start_time) * 1000
        results['性能统计'] = {
            '总耗时': f"{total_time:.1f}ms",
            '剩余预算': f"{remaining_budget:.1f}ms",
            '计算效率': f"{(self.computation_budget - remaining_budget) / self.computation_budget * 100:.1f}%"
        }
        
        return results
    
    def _lightweight_integration(self, results, detections):
        """轻量级结果整合"""
        integrated = {
            '场景类型': '未知',
            '关键洞察': [],
            '置信度': 0.0,
            '计算效率': '高'
        }
        
        # 提取关键信息
        all_insights = []
        confidences = []
        
        for module_name, result in results.items():
            if 'insights' in result:
                all_insights.extend(result['insights'][:2])  # 每个模块最多取2个洞察
            if 'confidence' in result:
                confidences.append(result['confidence'])
            if 'scene_type' in result:
                integrated['场景类型'] = result['scene_type']
        
        # 计算综合置信度
        if confidences:
            integrated['置信度'] = np.mean(confidences)
        
        # 选择最重要的洞察
        integrated['关键洞察'] = all_insights[:5]  # 最多5个关键洞察
        
        # 根据对象数量调整计算效率评估
        if len(detections) > 10:
            integrated['计算效率'] = '中'
        elif len(detections) > 20:
            integrated['计算效率'] = '低'
        
        return integrated

# ==================== 智能感知模块 ====================

class IntelligentPerception:
    def __init__(self):
        self.feature_cache = {}
        self.cache_size = 50
        
    def analyze(self, detections, image, context):
        """智能感知分析"""
        start_time = time.time()
        
        # 提取轻量级特征
        features = self._extract_lightweight_features(detections, image)
        
        # 空间关系分析
        spatial_analysis = self._analyze_spatial_relations(detections)
        
        # 显著性检测
        saliency_map = self._fast_saliency_detection(image)
        
        # 对象重要性排序
        importance_ranking = self._rank_object_importance(detections, saliency_map)
        
        return {
            'object_count': len(detections),
            'spatial_relations': spatial_analysis,
            'importance_ranking': importance_ranking,
            'saliency_score': np.mean(saliency_map) if saliency_map is not None else 0,
            'confidence': self._calculate_perception_confidence(detections),
            'insights': self._generate_perception_insights(detections, importance_ranking),
            'computation_time': f"{(time.time() - start_time) * 1000:.1f}ms"
        }
    
    def _extract_lightweight_features(self, detections, image):
        """提取轻量级特征"""
        features = []
        for det in detections:
            bbox = det['bbox']
            feature = {
                'position': [(bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2],
                'size': (bbox[2] - bbox[0], bbox[3] - bbox[1]),
                'aspect_ratio': (bbox[2] - bbox[0]) / (bbox[3] - bbox[1] + 1e-8),
                'area': (bbox[2] - bbox[0]) * (bbox[3] - bbox[1]),
                'class': det['class'],
                'confidence': det['confidence']
            }
            features.append(feature)
        return features
    
    def _analyze_spatial_relations(self, detections):
        """分析空间关系"""
        if len(detections) < 2:
            return []
        
        relations = []
        for i, det1 in enumerate(detections):
            for j, det2 in enumerate(detections):
                if i < j:
                    relation = self._calculate_relation(det1, det2)
                    if relation['strength'] > 0.3:
                        relations.append(relation)
                        if len(relations) >= 10:  # 限制关系数量
                            return relations
        
        return relations
    
    def _calculate_relation(self, det1, det2):
        """计算两个对象间的关系"""
        bbox1, bbox2 = det1['bbox'], det2['bbox']
        center1 = [(bbox1[0] + bbox1[2])/2, (bbox1[1] + bbox1[3])/2]
        center2 = [(bbox2[0] + bbox2[2])/2, (bbox2[1] + bbox2[3])/2]
        
        dx = center2[0] - center1[0]
        dy = center2[1] - center1[1]
        distance = math.sqrt(dx**2 + dy**2)
        
        # 确定主要关系
        if abs(dx) > abs(dy) * 1.5:
            relation = 'left_of' if dx > 0 else 'right_of'
        elif abs(dy) > abs(dx) * 1.5:
            relation = 'below' if dy > 0 else 'above'
        else:
            relation = 'near'
        
        return {
            'object1': det1['class'],
            'object2': det2['class'],
            'relation': relation,
            'distance': distance,
            'strength': 1.0 / (1.0 + distance/100)
        }
    
    def _fast_saliency_detection(self, image):
        """快速显著性检测"""
        try:
            # 使用简单的基于颜色的显著性检测
            if image is None or image.size == 0:
                return None
                
            # 调整图像大小以加速处理
            small_img = cv2.resize(image, (64, 64))
            
            # 转换为Lab颜色空间
            lab = cv2.cvtColor(small_img, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            
            # 计算每个通道的均值
            mean_l = np.mean(l)
            mean_a = np.mean(a)
            mean_b = np.mean(b)
            
            # 计算显著性图
            saliency = np.sqrt(
                (l - mean_l)**2 + (a - mean_a)**2 + (b - mean_b)**2
            )
            
            # 归一化
            saliency = (saliency - np.min(saliency)) / (np.max(saliency) - np.min(saliency) + 1e-8)
            
            return cv2.resize(saliency, (image.shape[1], image.shape[0]))
            
        except Exception as e:
            print(f"显著性检测失败: {e}")
            return None
    
    def _rank_object_importance(self, detections, saliency_map):
        """对对象重要性进行排序"""
        if not detections:
            return []
        
        scores = []
        for det in detections:
            score = det['confidence']  # 基础分：检测置信度
            
            # 位置重要性（中心区域更重要）
            bbox = det['bbox']
            center_x = (bbox[0] + bbox[2]) / 2
            center_y = (bbox[1] + bbox[3]) / 2
            dist_from_center = math.sqrt(
                (center_x - 0.5)**2 + (center_y - 0.5)**2
            )
            center_score = 1.0 - min(1.0, dist_from_center * 2)
            score += center_score * 0.3
            
            # 尺寸重要性（大对象更重要）
            area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
            size_score = min(1.0, area * 10)  # 假设归一化坐标
            score += size_score * 0.2
            
            # 显著性重要性
            if saliency_map is not None:
                x1, y1, x2, y2 = map(int, bbox)
                if (0 <= x1 < x2 <= saliency_map.shape[1] and 
                    0 <= y1 < y2 <= saliency_map.shape[0]):
                    saliency_roi = saliency_map[y1:y2, x1:x2]
                    if saliency_roi.size > 0:
                        saliency_score = np.mean(saliency_roi)
                        score += saliency_score * 0.3
            
            scores.append({
                'object': det['class'],
                'score': score,
                'confidence': det['confidence'],
                'position': [center_x, center_y]
            })
        
        # 按分数排序
        scores.sort(key=lambda x: x['score'], reverse=True)
        return scores[:10]  # 返回前10个重要对象
    
    def _calculate_perception_confidence(self, detections):
        """计算感知置信度"""
        if not detections:
            return 0.0
        
        confidences = [det['confidence'] for det in detections]
        avg_confidence = np.mean(confidences)
        
        # 基于对象数量和置信度的综合评估
        count_factor = min(1.0, len(detections) / 20)  # 对象数量因子
        confidence_factor = avg_confidence
        
        return 0.3 + 0.7 * (count_factor * 0.4 + confidence_factor * 0.6)
    
    def _generate_perception_insights(self, detections, importance_ranking):
        """生成感知洞察"""
        insights = []
        
        if not detections:
            insights.append("场景中未检测到显著对象")
            return insights
        
        # 基于重要对象的洞察
        if importance_ranking:
            top_object = importance_ranking[0]
            insights.append(f"场景中最显著的对象是: {top_object['object']} (置信度: {top_object['confidence']:.2f})")
        
        # 基于对象数量的洞察
        if len(detections) > 10:
            insights.append("检测到复杂场景，包含多个对象")
        elif len(detections) <= 3:
            insights.append("场景相对简单，对象数量较少")
        
        # 基于空间分布的洞察
        if len(detections) >= 3:
            positions = [det['bbox'] for det in detections]
            centers = [[(x1+x2)/2, (y1+y2)/2] for x1, y1, x2, y2 in positions]
            centers = np.array(centers)
            
            # 计算空间分散度
            if len(centers) > 1:
                std_x, std_y = np.std(centers, axis=0)
                dispersion = math.sqrt(std_x**2 + std_y**2)
                
                if dispersion > 0.3:
                    insights.append("对象在场景中分布较分散")
                elif dispersion < 0.1:
                    insights.append("对象在场景中分布较集中")
        
        return insights

# ==================== 关系推理模块 ====================

class RelationReasoner:
    def __init__(self):
        self.relation_knowledge = self._load_relation_knowledge()
        
    def _load_relation_knowledge(self):
        """加载关系知识库"""
        return {
            'person': {
                'car': ['driving', 'approaching', 'entering', 'exiting'],
                'bicycle': ['riding', 'pushing'],
                'cell phone': ['using', 'holding'],
                'chair': ['sitting_on', 'standing_near']
            },
            'car': {
                'person': ['transporting', 'approaching'],
                'traffic light': ['stopping_at', 'passing'],
                'car': ['following', 'overtaking', 'parked_near']
            },
            'dog': {
                'person': ['accompanying', 'following'],
                'cat': ['chasing', 'ignoring']
            }
        }
    
    def analyze(self, detections, image, context):
        """关系推理分析"""
        start_time = time.time()
        
        # 提取对象关系
        object_relations = self._extract_object_relations(detections)
        
        # 构建关系图
        relation_graph = self._build_relation_graph(object_relations)
        
        # 推理高级关系
        advanced_relations = self._infer_advanced_relations(object_relations)
        
        # 场景关系模式识别
        relation_patterns = self._identify_relation_patterns(object_relations)
        
        return {
            'object_relations': object_relations,
            'relation_graph_summary': self._summarize_graph(relation_graph),
            'advanced_relations': advanced_relations,
            'relation_patterns': relation_patterns,
            'confidence': self._calculate_relation_confidence(object_relations),
            'insights': self._generate_relation_insights(object_relations, relation_patterns),
            'computation_time': f"{(time.time() - start_time) * 1000:.1f}ms"
        }
    
    def _extract_object_relations(self, detections):
        """提取对象间关系"""
        relations = []
        
        for i, det1 in enumerate(detections):
            for j, det2 in enumerate(detections):
                if i < j:
                    # 空间关系
                    spatial_rel = self._calculate_spatial_relation(det1, det2)
                    
                    # 语义关系
                    semantic_rels = self._get_semantic_relations(det1['class'], det2['class'])
                    
                    if spatial_rel or semantic_rels:
                        relations.append({
                            'object1': det1['class'],
                            'object2': det2['class'],
                            'spatial_relation': spatial_rel,
                            'semantic_relations': semantic_rels,
                            'combined_confidence': (det1['confidence'] + det2['confidence']) / 2
                        })
                    
                    # 限制关系数量以避免组合爆炸
                    if len(relations) >= 15:
                        return relations
        
        return relations
    
    def _calculate_spatial_relation(self, det1, det2):
        """计算空间关系"""
        bbox1, bbox2 = det1['bbox'], det2['bbox']
        
        # 计算边界框中心
        center1 = [(bbox1[0] + bbox1[2])/2, (bbox1[1] + bbox1[3])/2]
        center2 = [(bbox2[0] + bbox2[2])/2, (bbox2[1] + bbox2[3])/2]
        
        # 计算距离和方向
        dx = center2[0] - center1[0]
        dy = center2[1] - center1[1]
        distance_val = math.sqrt(dx**2 + dy**2)
        
        # 确定空间关系
        relations = []
        
        # 水平关系
        if dx > 0.1:  # object2在object1右边
            relations.append(('right_of', min(1.0, abs(dx))))
        elif dx < -0.1:  # object2在object1左边
            relations.append(('left_of', min(1.0, abs(dx))))
        
        # 垂直关系
        if dy > 0.1:  # object2在object1下面
            relations.append(('below', min(1.0, abs(dy))))
        elif dy < -0.1:  # object2在object1上面
            relations.append(('above', min(1.0, abs(dy))))
        
        # 接近关系
        if distance_val < 0.2:
            relations.append(('near', 1.0 - distance_val/0.2))
        
        return relations
    
    def _get_semantic_relations(self, class1, class2):
        """获取语义关系"""
        relations = []
        
        # 检查双向关系
        if class1 in self.relation_knowledge and class2 in self.relation_knowledge[class1]:
            for rel in self.relation_knowledge[class1][class2]:
                relations.append((rel, 0.7))  # 基础置信度
        
        if class2 in self.relation_knowledge and class1 in self.relation_knowledge[class2]:
            for rel in self.relation_knowledge[class2][class1]:
                # 避免重复
                if not any(r[0] == rel for r in relations):
                    relations.append((rel, 0.7))
        
        return relations
    
    def _build_relation_graph(self, relations):
        """构建关系图"""
        G = nx.Graph()
        
        for rel in relations:
            obj1, obj2 = rel['object1'], rel['object2']
            G.add_node(obj1)
            G.add_node(obj2)
            
            # 计算关系强度
            strength = 0.0
            if rel['spatial_relation']:
                strength += max(s[1] for s in rel['spatial_relation']) * 0.5
            if rel['semantic_relations']:
                strength += max(s[1] for s in rel['semantic_relations']) * 0.5
            
            if strength > 0.2:
                G.add_edge(obj1, obj2, weight=strength, 
                          spatial=rel['spatial_relation'],
                          semantic=rel['semantic_relations'])
        
        return G
    
    def _summarize_graph(self, graph):
        """总结图结构"""
        if len(graph.nodes) == 0:
            return {"node_count": 0, "edge_count": 0, "density": 0}
        
        return {
            "node_count": len(graph.nodes),
            "edge_count": len(graph.edges),
            "density": nx.density(graph),
            "connected_components": nx.number_connected_components(graph)
        }
    
    def _infer_advanced_relations(self, relations):
        """推理高级关系"""
        advanced = []
        
        for rel in relations:
            obj1, obj2 = rel['object1'], rel['object2']
            
            # 基于对象类型和关系的推理
            if obj1 == 'person' and obj2 == 'car':
                if any(r[0] == 'near' for r in rel['spatial_relation']):
                    advanced.append({
                        'type': 'potential_interaction',
                        'objects': [obj1, obj2],
                        'relation': 'person_approaching_car',
                        'confidence': 0.6
                    })
            
            elif obj1 == 'car' and obj2 == 'traffic light':
                advanced.append({
                    'type': 'regulatory',
                    'objects': [obj1, obj2],
                    'relation': 'vehicle_at_intersection',
                    'confidence': 0.7
                })
        
        return advanced
    
    def _identify_relation_patterns(self, relations):
        """识别关系模式"""
        patterns = []
        
        # 统计关系类型
        spatial_counts = defaultdict(int)
        semantic_counts = defaultdict(int)
        
        for rel in relations:
            for spatial_rel, strength in rel['spatial_relation']:
                if strength > 0.5:
                    spatial_counts[spatial_rel] += 1
            
            for semantic_rel, strength in rel['semantic_relations']:
                if strength > 0.5:
                    semantic_counts[semantic_rel] += 1
        
        # 识别主导模式
        if spatial_counts:
            dominant_spatial = max(spatial_counts.items(), key=lambda x: x[1])
            patterns.append(f"主导空间关系: {dominant_spatial[0]} ({dominant_spatial[1]}次)")
        
        if semantic_counts:
            dominant_semantic = max(semantic_counts.items(), key=lambda x: x[1])
            patterns.append(f"主导语义关系: {dominant_semantic[0]} ({dominant_semantic[1]}次)")
        
        # 基于对象组合的模式
        object_pairs = defaultdict(int)
        for rel in relations:
            pair = tuple(sorted([rel['object1'], rel['object2']]))
            object_pairs[pair] += 1
        
        if object_pairs:
            common_pair = max(object_pairs.items(), key=lambda x: x[1])
            patterns.append(f"常见对象对: {common_pair[0]} ({common_pair[1]}次)")
        
        return patterns
    
    def _calculate_relation_confidence(self, relations):
        """计算关系推理置信度"""
        if not relations:
            return 0.0
        
        # 基于关系数量和强度的置信度
        total_strength = 0
        for rel in relations:
            max_spatial = max([s[1] for s in rel['spatial_relation']]) if rel['spatial_relation'] else 0
            max_semantic = max([s[1] for s in rel['semantic_relations']]) if rel['semantic_relations'] else 0
            total_strength += (max_spatial + max_semantic) / 2
        
        avg_strength = total_strength / len(relations)
        relation_density = min(1.0, len(relations) / 10)  # 关系密度因子
        
        return 0.2 + 0.8 * (avg_strength * 0.6 + relation_density * 0.4)
    
    def _generate_relation_insights(self, relations, patterns):
        """生成关系洞察"""
        insights = []
        
        if not relations:
            insights.append("未检测到显著的对象间关系")
            return insights
        
        insights.append(f"检测到 {len(relations)} 个对象间关系")
        
        # 添加模式洞察
        insights.extend(patterns[:3])  # 最多3个模式
        
        # 基于关系类型的洞察
        spatial_relations = set()
        for rel in relations:
            for spatial_rel, _ in rel['spatial_relation']:
                spatial_relations.add(spatial_rel)
        
        if 'near' in spatial_relations:
            insights.append("多个对象在空间上接近，可能存在交互")
        
        # 基于对象类型的洞察
        object_types = set()
        for rel in relations:
            object_types.add(rel['object1'])
            object_types.add(rel['object2'])
        
        if 'person' in object_types and 'car' in object_types:
            insights.append("检测到人与车辆的潜在交互")
        
        return insights

# ==================== 轻量级场景理解模块 ====================

class LightSceneUnderstanding:
    def __init__(self):
        self.scene_templates = self._load_scene_templates()
        
    def _load_scene_templates(self):
        """加载场景模板"""
        return {
            'urban_street': ['car', 'person', 'traffic light', 'building'],
            'office': ['person', 'chair', 'computer', 'desk'],
            'park': ['person', 'tree', 'grass', 'bench'],
            'home': ['person', 'chair', 'tv', 'sofa'],
            'highway': ['car', 'truck', 'road'],
            'social': ['person', 'cell phone', 'person']  # 多人
        }
    
    def analyze(self, detections, image, context):
        """场景理解分析"""
        start_time = time.time()
        
        # 场景分类
        scene_classification = self._classify_scene(detections)
        
        # 场景复杂度评估
        complexity_analysis = self._analyze_complexity(detections)
        
        # 场景一致性评估
        consistency_analysis = self._assess_consistency(detections, scene_classification)
        
        return {
            'scene_type': scene_classification['primary_type'],
            'scene_alternatives': scene_classification['alternatives'],
            'complexity': complexity_analysis,
            'consistency': consistency_analysis,
            'confidence': scene_classification['confidence'],
            'insights': self._generate_scene_insights(scene_classification, complexity_analysis),
            'computation_time': f"{(time.time() - start_time) * 1000:.1f}ms"
        }
    
    def _classify_scene(self, detections):
        """场景分类"""
        object_types = [det['class'] for det in detections]
        object_set = set(object_types)
        
        best_match = None
        best_score = 0
        alternatives = []
        
        for scene_type, template_objects in self.scene_templates.items():
            template_set = set(template_objects)
            
            # 计算匹配度
            intersection = object_set.intersection(template_set)
            union = object_set.union(template_set)
            
            if len(union) > 0:
                similarity = len(intersection) / len(union)
                
                # 调整分数：考虑对象数量
                count_factor = min(1.0, len(intersection) / len(template_set))
                score = similarity * 0.7 + count_factor * 0.3
                
                if score > best_score:
                    best_score = score
                    best_match = scene_type
                
                if score > 0.3:
                    alternatives.append({
                        'scene_type': scene_type,
                        'score': score,
                        'matching_objects': list(intersection)
                    })
        
        # 按分数排序备选场景
        alternatives.sort(key=lambda x: x['score'], reverse=True)
        
        return {
            'primary_type': best_match if best_score > 0.3 else 'unknown',
            'confidence': best_score,
            'alternatives': alternatives[:3]  # 最多3个备选
        }
    
    def _analyze_complexity(self, detections):
        """分析场景复杂度"""
        if not detections:
            return {'level': 'very_low', 'score': 0}
        
        num_objects = len(detections)
        num_categories = len(set(det['class'] for det in detections))
        avg_confidence = np.mean([det['confidence'] for det in detections])
        
        # 复杂度分数
        complexity_score = (
            min(1.0, num_objects / 15) * 0.4 +
            min(1.0, num_categories / 8) * 0.4 +
            avg_confidence * 0.2
        )
        
        # 复杂度等级
        if complexity_score > 0.7:
            level = 'high'
        elif complexity_score > 0.4:
            level = 'medium'
        elif complexity_score > 0.1:
            level = 'low'
        else:
            level = 'very_low'
        
        return {
            'level': level,
            'score': complexity_score,
            'factors': {
                'object_count': num_objects,
                'category_count': num_categories,
                'confidence_avg': avg_confidence
            }
        }
    
    def _assess_consistency(self, detections, scene_classification):
        """评估场景一致性"""
        if scene_classification['primary_type'] == 'unknown':
            return {'consistent': False, 'reason': '未知场景类型'}
        
        scene_type = scene_classification['primary_type']
        expected_objects = set(self.scene_templates.get(scene_type, []))
        actual_objects = set(det['class'] for det in detections)
        
        # 计算一致性
        missing_objects = expected_objects - actual_objects
        unexpected_objects = actual_objects - expected_objects
        
        consistency_score = len(expected_objects.intersection(actual_objects)) / len(expected_objects.union(actual_objects))
        
        return {
            'consistent': consistency_score > 0.3,
            'score': consistency_score,
            'missing_objects': list(missing_objects),
            'unexpected_objects': list(unexpected_objects)
        }
    
    def _generate_scene_insights(self, scene_classification, complexity_analysis):
        """生成场景洞察"""
        insights = []
        
        scene_type = scene_classification['primary_type']
        confidence = scene_classification['confidence']
        
        if scene_type != 'unknown':
            insights.append(f"场景识别为: {scene_type} (置信度: {confidence:.2f})")
        else:
            insights.append("场景类型无法确定")
        
        # 复杂度洞察
        complexity_level = complexity_analysis['level']
        if complexity_level == 'high':
            insights.append("场景复杂度较高，包含多个不同类型的对象")
        elif complexity_level == 'low':
            insights.append("场景相对简单，对象数量和类型较少")
        
        # 一致性洞察
        if scene_type != 'unknown' and len(scene_classification['alternatives']) > 1:
            insights.append(f"备选场景: {', '.join(alt['scene_type'] for alt in scene_classification['alternatives'][:2])}")
        
        return insights

# ==================== 行为分析模块 ====================

class BehaviorAnalyzer:
    def __init__(self):
        self.behavior_patterns = self._load_behavior_patterns()
        
    def _load_behavior_patterns(self):
        """加载行为模式"""
        return {
            'crossing_road': {
                'objects': ['person', 'car'],
                'spatial': ['near', 'approaching'],
                'context': 'urban_street'
            },
            'social_interaction': {
                'objects': ['person', 'person'],
                'spatial': ['near'],
                'context': 'social'
            },
            'vehicle_interaction': {
                'objects': ['car', 'car'],
                'spatial': ['near', 'following'],
                'context': 'highway'
            },
            'using_device': {
                'objects': ['person', 'cell phone'],
                'spatial': ['near'],
                'context': ['office', 'home', 'social']
            }
        }
    
    def analyze(self, detections, image, context):
        """行为分析"""
        start_time = time.time()
        
        # 检测行为模式
        detected_behaviors = self._detect_behavior_patterns(detections, context)
        
        # 行为风险评估
        risk_assessment = self._assess_behavior_risk(detected_behaviors)
        
        # 行为趋势分析
        trend_analysis = self._analyze_behavior_trends(detected_behaviors)
        
        return {
            'detected_behaviors': detected_behaviors,
            'risk_assessment': risk_assessment,
            'trend_analysis': trend_analysis,
            'confidence': self._calculate_behavior_confidence(detected_behaviors),
            'insights': self._generate_behavior_insights(detected_behaviors, risk_assessment),
            'computation_time': f"{(time.time() - start_time) * 1000:.1f}ms"
        }
    
    def _detect_behavior_patterns(self, detections, context):
        """检测行为模式"""
        behaviors = []
        object_types = [det['class'] for det in detections]
        
        for behavior_name, pattern in self.behavior_patterns.items():
            # 检查对象类型匹配
            required_objects = set(pattern['objects'])
            if not required_objects.issubset(set(object_types)):
                continue
            
            # 检查上下文匹配
            if 'context' in pattern:
                expected_context = pattern['context']
                if isinstance(expected_context, str):
                    if context != expected_context:
                        continue
                elif isinstance(expected_context, list):
                    if context not in expected_context:
                        continue
            
            # 简化版空间关系检查（在实际应用中会更复杂）
            behavior_confidence = 0.5  # 基础置信度
            
            # 根据对象数量调整置信度
            object_count = sum(1 for obj in object_types if obj in required_objects)
            behavior_confidence += min(0.3, object_count * 0.1)
            
            if behavior_confidence > 0.6:
                behaviors.append({
                    'behavior': behavior_name,
                    'confidence': behavior_confidence,
                    'involved_objects': list(required_objects),
                    'description': self._get_behavior_description(behavior_name)
                })
        
        return behaviors
    
    def _get_behavior_description(self, behavior_name):
        """获取行为描述"""
        descriptions = {
            'crossing_road': '行人可能正在穿越马路',
            'social_interaction': '检测到人际交互',
            'vehicle_interaction': '车辆间存在交互',
            'using_device': '人员正在使用电子设备'
        }
        return descriptions.get(behavior_name, '未知行为')
    
    def _assess_behavior_risk(self, behaviors):
        """评估行为风险"""
        risk_scores = {
            'crossing_road': 0.7,
            'social_interaction': 0.2,
            'vehicle_interaction': 0.5,
            'using_device': 0.3
        }
        
        if not behaviors:
            return {'overall_risk': 'low', 'score': 0}
        
        # 计算总体风险
        max_risk = max(risk_scores.get(behavior['behavior'], 0) * behavior['confidence'] 
                      for behavior in behaviors)
        
        if max_risk > 0.6:
            risk_level = 'high'
        elif max_risk > 0.3:
            risk_level = 'medium'
        else:
            risk_level = 'low'
        
        return {
            'overall_risk': risk_level,
            'score': max_risk,
            'high_risk_behaviors': [
                behavior for behavior in behaviors 
                if risk_scores.get(behavior['behavior'], 0) > 0.5
            ]
        }
    
    def _analyze_behavior_trends(self, behaviors):
        """分析行为趋势"""
        if not behaviors:
            return {'trend': 'no_activity', 'active_behaviors': 0}
        
        behavior_types = [behavior['behavior'] for behavior in behaviors]
        
        # 简化的趋势分析
        if len(behaviors) >= 3:
            trend = 'high_activity'
        elif len(behaviors) >= 1:
            trend = 'moderate_activity'
        else:
            trend = 'low_activity'
        
        return {
            'trend': trend,
            'active_behaviors': len(behaviors),
            'behavior_diversity': len(set(behavior_types))
        }
    
    def _calculate_behavior_confidence(self, behaviors):
        """计算行为分析置信度"""
        if not behaviors:
            return 0.0
        
        # 基于检测到的行为数量和置信度
        avg_confidence = np.mean([behavior['confidence'] for behavior in behaviors])
        behavior_density = min(1.0, len(behaviors) / 5)  # 行为密度因子
        
        return 0.3 + 0.7 * (avg_confidence * 0.6 + behavior_density * 0.4)
    
    def _generate_behavior_insights(self, behaviors, risk_assessment):
        """生成行为洞察"""
        insights = []
        
        if not behaviors:
            insights.append("未检测到显著的行为模式")
            return insights
        
        insights.append(f"检测到 {len(behaviors)} 个行为模式")
        
        # 高风险行为洞察
        if risk_assessment['overall_risk'] == 'high':
            insights.append("⚠️ 检测到高风险行为，建议关注")
        
        # 主要行为洞察
        if behaviors:
            top_behavior = max(behaviors, key=lambda x: x['confidence'])
            insights.append(f"主要行为: {top_behavior['description']}")
        
        # 活动水平洞察
        trend = risk_assessment['trend_analysis']['trend']
        if trend == 'high_activity':
            insights.append("场景活动水平较高")
        elif trend == 'low_activity':
            insights.append("场景活动水平较低")
        
        return insights

# ==================== 轻量级异常检测模块 ====================

class LightAnomalyDetector:
    def __init__(self):
        self.normal_patterns = self._load_normal_patterns()
        
    def _load_normal_patterns(self):
        """加载正常模式"""
        return {
            'object_size_ranges': {
                'person': (0.05, 0.3),    # 相对图像大小的范围
                'car': (0.1, 0.5),
                'bicycle': (0.05, 0.2),
                'cell phone': (0.01, 0.05)
            },
            'typical_object_counts': {
                'urban_street': {'person': (1, 10), 'car': (1, 8)},
                'office': {'person': (1, 5), 'chair': (1, 10)},
                'park': {'person': (1, 15), 'tree': (1, 20)}
            }
        }
    
    def analyze(self, detections, image, context):
        """异常检测分析"""
        start_time = time.time()
        
        # 尺寸异常检测
        size_anomalies = self._detect_size_anomalies(detections, image)
        
        # 数量异常检测
        count_anomalies = self._detect_count_anomalies(detections, context)
        
        # 位置异常检测
        position_anomalies = self._detect_position_anomalies(detections, image)
        
        # 综合风险评估
        risk_assessment = self._assess_overall_risk(size_anomalies, count_anomalies, position_anomalies)
        
        return {
            'size_anomalies': size_anomalies,
            'count_anomalies': count_anomalies,
            'position_anomalies': position_anomalies,
            'risk_assessment': risk_assessment,
            'confidence': self._calculate_anomaly_confidence(size_anomalies + count_anomalies + position_anomalies),
            'insights': self._generate_anomaly_insights(size_anomalies, count_anomalies, position_anomalies, risk_assessment),
            'computation_time': f"{(time.time() - start_time) * 1000:.1f}ms"
        }
    
    def _detect_size_anomalies(self, detections, image):
        """检测尺寸异常"""
        anomalies = []
        
        if image is None:
            return anomalies
            
        image_area = image.shape[0] * image.shape[1]
        
        for det in detections:
            bbox = det['bbox']
            width = bbox[2] - bbox[0]
            height = bbox[3] - bbox[1]
            area = width * height
            
            # 计算相对面积
            relative_area = area / image_area
            
            # 检查是否在正常范围内
            obj_class = det['class']
            if obj_class in self.normal_patterns['object_size_ranges']:
                min_size, max_size = self.normal_patterns['object_size_ranges'][obj_class]
                
                if relative_area < min_size:
                    anomalies.append({
                        'type': 'undersized_object',
                        'object': obj_class,
                        'confidence': det['confidence'],
                        'relative_size': relative_area,
                        'expected_range': (min_size, max_size),
                        'severity': 'low' if relative_area > min_size * 0.5 else 'medium'
                    })
                elif relative_area > max_size:
                    anomalies.append({
                        'type': 'oversized_object',
                        'object': obj_class,
                        'confidence': det['confidence'],
                        'relative_size': relative_area,
                        'expected_range': (min_size, max_size),
                        'severity': 'high' if relative_area > max_size * 1.5 else 'medium'
                    })
        
        return anomalies
    
    def _detect_count_anomalies(self, detections, context):
        """检测数量异常"""
        anomalies = []
        
        if not context or context == 'unknown':
            return anomalies
        
        # 统计各类对象数量
        object_counts = defaultdict(int)
        for det in detections:
            object_counts[det['class']] += 1
        
        # 检查是否在典型范围内
        if context in self.normal_patterns['typical_object_counts']:
            typical_ranges = self.normal_patterns['typical_object_counts'][context]
            
            for obj_class, (min_count, max_count) in typical_ranges.items():
                actual_count = object_counts.get(obj_class, 0)
                
                if actual_count < min_count:
                    anomalies.append({
                        'type': 'insufficient_objects',
                        'object': obj_class,
                        'actual_count': actual_count,
                        'expected_range': (min_count, max_count),
                        'severity': 'low'
                    })
                elif actual_count > max_count:
                    anomalies.append({
                        'type': 'excessive_objects',
                        'object': obj_class,
                        'actual_count': actual_count,
                        'expected_range': (min_count, max_count),
                        'severity': 'medium' if actual_count > max_count * 1.5 else 'low'
                    })
        
        return anomalies
    
    def _detect_position_anomalies(self, detections, image):
        """检测位置异常"""
        anomalies = []
        
        if image is None:
            return anomalies
            
        image_height, image_width = image.shape[:2]
        
        for det in detections:
            bbox = det['bbox']
            center_x = (bbox[0] + bbox[2]) / 2
            center_y = (bbox[1] + bbox[3]) / 2
            
            # 检查是否在图像边缘
            edge_threshold = 0.05  # 5%的边缘区域
            if (center_x < edge_threshold or center_x > 1 - edge_threshold or
                center_y < edge_threshold or center_y > 1 - edge_threshold):
                
                anomalies.append({
                    'type': 'edge_object',
                    'object': det['class'],
                    'confidence': det['confidence'],
                    'position': (center_x, center_y),
                    'severity': 'low'
                })
            
            # 检查是否部分在图像外（对于非归一化坐标）
            if (bbox[0] < 0 or bbox[2] > image_width or 
                bbox[1] < 0 or bbox[3] > image_height):
                
                anomalies.append({
                    'type': 'partial_visibility',
                    'object': det['class'],
                    'confidence': det['confidence'],
                    'severity': 'medium'
                })
        
        return anomalies
    
    def _assess_overall_risk(self, size_anomalies, count_anomalies, position_anomalies):
        """评估总体风险"""
        all_anomalies = size_anomalies + count_anomalies + position_anomalies
        
        if not all_anomalies:
            return {'level': 'low', 'score': 0, 'anomaly_count': 0}
        
        # 计算风险分数
        risk_score = 0
        severity_weights = {'low': 0.3, 'medium': 0.6, 'high': 1.0}
        
        for anomaly in all_anomalies:
            risk_score += severity_weights.get(anomaly['severity'], 0.3)
        
        risk_score = min(1.0, risk_score / len(all_anomalies))
        
        # 确定风险等级
        if risk_score > 0.7:
            risk_level = 'high'
        elif risk_score > 0.4:
            risk_level = 'medium'
        else:
            risk_level = 'low'
        
        return {
            'level': risk_level,
            'score': risk_score,
            'anomaly_count': len(all_anomalies),
            'high_severity_count': sum(1 for a in all_anomalies if a['severity'] == 'high')
        }
    
    def _calculate_anomaly_confidence(self, anomalies):
        """计算异常检测置信度"""
        if not anomalies:
            return 0.8  # 没有异常时置信度较高
        
        # 基于异常数量和严重程度
        severity_scores = {'low': 0.3, 'medium': 0.6, 'high': 1.0}
        total_score = sum(severity_scores.get(anomaly['severity'], 0.3) for anomaly in anomalies)
        avg_severity = total_score / len(anomalies)
        
        return 0.3 + 0.7 * avg_severity
    
    def _generate_anomaly_insights(self, size_anomalies, count_anomalies, position_anomalies, risk_assessment):
        """生成异常洞察"""
        insights = []
        
        all_anomalies = size_anomalies + count_anomalies + position_anomalies
        
        if not all_anomalies:
            insights.append("未检测到显著异常")
            return insights
        
        insights.append(f"检测到 {len(all_anomalies)} 个异常")
        
        # 风险等级洞察
        risk_level = risk_assessment['level']
        if risk_level == 'high':
            insights.append("⚠️ 高风险异常检测，建议立即关注")
        elif risk_level == 'medium':
            insights.append("⚠️ 中等风险异常检测，建议关注")
        
        # 主要异常类型洞察
        anomaly_types = defaultdict(int)
        for anomaly in all_anomalies:
            anomaly_types[anomaly['type']] += 1
        
        if anomaly_types:
            main_anomaly = max(anomaly_types.items(), key=lambda x: x[1])
            insights.append(f"主要异常类型: {main_anomaly[0]} ({main_anomaly[1]}次)")
        
        # 高严重性异常洞察
        high_severity = [a for a in all_anomalies if a['severity'] == 'high']
        if high_severity:
            insights.append(f"发现 {len(high_severity)} 个高严重性异常")
        
        return insights

# ==================== 轻量级记忆系统 ====================

class LightMemorySystem:
    def __init__(self):
        self.short_term_memory = deque(maxlen=20)  # 短期记忆
        self.long_term_patterns = defaultdict(list)  # 长期模式
        self.memory_size = 100  # 记忆容量
        
    def analyze(self, detections, image, context):
        """记忆分析"""
        start_time = time.time()
        
        # 更新记忆
        self._update_memory(detections, context)
        
        # 模式识别
        pattern_analysis = self._analyze_patterns(detections)
        
        # 变化检测
        change_detection = self._detect_changes(detections)
        
        # 预测生成
        predictions = self._generate_predictions(detections, context)
        
        return {
            'memory_stats': self._get_memory_stats(),
            'pattern_analysis': pattern_analysis,
            'change_detection': change_detection,
            'predictions': predictions,
            'confidence': self._calculate_memory_confidence(),
            'insights': self._generate_memory_insights(pattern_analysis, change_detection, predictions),
            'computation_time': f"{(time.time() - start_time) * 1000:.1f}ms"
        }
    
    def _update_memory(self, detections, context):
        """更新记忆"""
        memory_entry = {
            'timestamp': time.time(),
            'detections': detections,
            'context': context,
            'object_count': len(detections),
            'object_types': [det['class'] for det in detections]
        }
        
        self.short_term_memory.append(memory_entry)
        
        # 定期转移到长期记忆
        if len(self.short_term_memory) >= 10:
            self._consolidate_memory()
    
    def _consolidate_memory(self):
        """巩固记忆"""
        if len(self.short_term_memory) < 5:
            return
        
        # 提取常见模式
        recent_entries = list(self.short_term_memory)[-5:]  # 最近5个条目
        
        # 分析对象类型模式
        object_patterns = defaultdict(int)
        for entry in recent_entries:
            for obj_type in entry['object_types']:
                object_patterns[obj_type] += 1
        
        # 保存频繁出现的模式
        for obj_type, count in object_patterns.items():
            if count >= 3:  # 在最近5次中出现至少3次
                pattern_key = f"frequent_object_{obj_type}"
                self.long_term_patterns[pattern_key].append({
                    'frequency': count / 5,
                    'last_seen': time.time()
                })
        
        # 限制长期记忆大小
        if len(self.long_term_patterns) > self.memory_size:
            # 移除最旧的模式
            oldest_key = min(self.long_term_patterns.keys(), 
                           key=lambda k: self.long_term_patterns[k][-1]['last_seen'])
            del self.long_term_patterns[oldest_key]
    
    def _analyze_patterns(self, detections):
        """分析模式"""
        current_objects = set(det['class'] for det in detections)
        
        # 检查与长期模式的匹配
        pattern_matches = []
        for pattern_key, pattern_history in self.long_term_patterns.items():
            if pattern_key.startswith('frequent_object_'):
                obj_type = pattern_key.replace('frequent_object_', '')
                if obj_type in current_objects:
                    avg_frequency = np.mean([p['frequency'] for p in pattern_history])
                    pattern_matches.append({
                        'pattern': f"频繁对象: {obj_type}",
                        'match_strength': avg_frequency,
                        'current_presence': True
                    })
        
        return {
            'pattern_matches': pattern_matches,
            'current_objects': list(current_objects),
            'pattern_diversity': len(pattern_matches)
        }
    
    def _detect_changes(self, detections):
        """检测变化"""
        if len(self.short_term_memory) < 2:
            return {'change_detected': False, 'change_magnitude': 0}
        
        current_objects = set(det['class'] for det in detections)
        previous_entry = self.short_term_memory[-2]  # 上一个条目
        previous_objects = set(previous_entry['object_types'])
        
        # 计算变化
        added_objects = current_objects - previous_objects
        removed_objects = previous_objects - current_objects
        
        change_magnitude = len(added_objects) + len(removed_objects)
        
        return {
            'change_detected': change_magnitude > 0,
            'change_magnitude': change_magnitude,
            'added_objects': list(added_objects),
            'removed_objects': list(removed_objects)
        }
    
    def _generate_predictions(self, detections, context):
        """生成预测"""
        predictions = []
        
        if len(self.short_term_memory) < 3:
            return predictions
        
        # 基于历史模式的简单预测
        current_objects = set(det['class'] for det in detections)
        
        # 检查对象出现模式
        for obj_type in current_objects:
            pattern_key = f"frequent_object_{obj_type}"
            if pattern_key in self.long_term_patterns:
                pattern_history = self.long_term_patterns[pattern_key]
                avg_frequency = np.mean([p['frequency'] for p in pattern_history])
                
                if avg_frequency > 0.7:
                    predictions.append({
                        'type': 'continuation',
                        'object': obj_type,
                        'prediction': f"{obj_type} 可能继续出现",
                        'confidence': avg_frequency
                    })
        
        # 基于场景上下文的预测
        if context == 'urban_street' and 'person' in current_objects and 'car' in current_objects:
            predictions.append({
                'type': 'interaction',
                'prediction': '可能发生人与车辆的交互',
                'confidence': 0.6
            })
        
        return predictions
    
    def _get_memory_stats(self):
        """获取记忆统计"""
        return {
            'short_term_memory_size': len(self.short_term_memory),
            'long_term_patterns_count': len(self.long_term_patterns),
            'memory_utilization': f"{(len(self.long_term_patterns) / self.memory_size) * 100:.1f}%"
        }
    
    def _calculate_memory_confidence(self):
        """计算记忆分析置信度"""
        # 基于记忆数据量的置信度
        memory_utilization = len(self.long_term_patterns) / self.memory_size
        history_length = min(1.0, len(self.short_term_memory) / 10)
        
        return 0.2 + 0.8 * (memory_utilization * 0.6 + history_length * 0.4)
    
    def _generate_memory_insights(self, pattern_analysis, change_detection, predictions):
        """生成记忆洞察"""
        insights = []
        
        # 模式洞察
        if pattern_analysis['pattern_matches']:
            insights.append(f"识别到 {len(pattern_analysis['pattern_matches'])} 个历史模式")
        
        # 变化洞察
        if change_detection['change_detected']:
            change_count = change_detection['change_magnitude']
            insights.append(f"检测到场景变化: {change_count} 个对象变化")
        
        # 预测洞察
        if predictions:
            insights.append(f"基于历史生成 {len(predictions)} 个预测")
        
        if not insights:
            insights.append("记忆系统需要更多数据以提供深入洞察")
        
        return insights

# ==================== 性能监控与自适应控制 ====================

class PerformanceMonitor:
    def __init__(self):
        self.module_performance = defaultdict(list)
        self.system_performance = deque(maxlen=100)
        
    def record_module_performance(self, module_name, execution_time, object_count):
        """记录模块性能"""
        self.module_performance[module_name].append({
            'timestamp': time.time(),
            'execution_time': execution_time,
            'object_count': object_count,
            'efficiency': object_count / (execution_time + 1e-8)  # 对象/毫秒
        })
        
        # 限制记录数量
        if len(self.module_performance[module_name]) > 50:
            self.module_performance[module_name].pop(0)
    
    def get_module_efficiency(self, module_name):
        """获取模块效率"""
        if module_name not in self.module_performance or not self.module_performance[module_name]:
            return 1.0
        
        efficiencies = [record['efficiency'] for record in self.module_performance[module_name]]
        return np.mean(efficiencies)
    
    def get_average_execution_time(self, module_name):
        """获取平均执行时间"""
        if module_name not in self.module_performance or not self.module_performance[module_name]:
            return 0
        
        times = [record['execution_time'] for record in self.module_performance[module_name]]
        return np.mean(times)

class AdaptiveComputationController:
    def __init__(self):
        self.performance_monitor = PerformanceMonitor()
        self.module_priorities = {
            '智能感知': 1.0,
            '关系推理': 0.8,
            '场景理解': 0.7,
            '行为分析': 0.6,
            '异常检测': 0.5,
            '记忆系统': 0.4
        }
    
    def get_module_priority(self, detections, context):
        """获取模块优先级"""
        # 基础优先级排序
        base_priority = sorted(self.module_priorities.keys(), 
                             key=lambda x: self.module_priorities[x], reverse=True)
        
        # 根据场景调整优先级
        if context == 'urban_street':
            # 在街道场景中，行为分析和异常检测更重要
            if '行为分析' in base_priority and '异常检测' in base_priority:
                base_priority.remove('行为分析')
                base_priority.remove('异常检测')
                base_priority.insert(1, '行为分析')
                base_priority.insert(2, '异常检测')
        
        return base_priority
    
    def allocate_budget(self, module_name, remaining_budget, object_count):
        """分配计算预算"""
        base_budget = remaining_budget * self.module_priorities.get(module_name, 0.5)
        
        # 根据对象数量调整预算
        if object_count > 10:
            # 对象多时增加预算
            adjusted_budget = base_budget * (1 + min(0.5, (object_count - 10) / 20))
        elif object_count < 3:
            # 对象少时减少预算
            adjusted_budget = base_budget * 0.7
        else:
            adjusted_budget = base_budget
        
        return min(adjusted_budget, remaining_budget)

# ==================== PyQt界面 ====================

class LightweightInferenceApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.hyper_engine = LightweightHyperEngine()
        self.model_loader = YOLOModelLoader()
        self.current_detections = []
        self.current_image = None
        self.current_results = {}
        self.current_image_path = None
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("轻量级超神YOLO推理系统")
        self.setGeometry(100, 100, 1400, 900)
        
        # 中央窗口
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QHBoxLayout(central_widget)
        
        # 左侧控制面板
        control_panel = self.create_control_panel()
        main_layout.addWidget(control_panel, 1)
        
        # 右侧显示区域
        display_panel = self.create_display_panel()
        main_layout.addWidget(display_panel, 2)
        
    def create_control_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # 系统状态组
        status_group = QGroupBox("系统状态")
        status_layout = QVBoxLayout(status_group)
        
        self.system_status = QLabel("🟢 系统就绪")
        self.system_status.setStyleSheet("color: green; font-weight: bold; font-size: 14px;")
        status_layout.addWidget(self.system_status)
        
        self.memory_status = QLabel("内存: 未知 | 计算预算: 1000ms")
        status_layout.addWidget(self.memory_status)
        
        layout.addWidget(status_group)
        
        # 模型控制组
        model_group = QGroupBox("模型控制")
        model_layout = QVBoxLayout(model_group)
        
        load_model_btn = QPushButton("加载YOLO模型")
        load_model_btn.clicked.connect(self.load_model)
        model_layout.addWidget(load_model_btn)
        
        load_image_btn = QPushButton("加载图像")
        load_image_btn.clicked.connect(self.load_image)
        model_layout.addWidget(load_image_btn)
        
        # 计算预算控制
        budget_layout = QHBoxLayout()
        budget_layout.addWidget(QLabel("计算预算:"))
        self.budget_spin = QDoubleSpinBox()
        self.budget_spin.setRange(100, 5000)
        self.budget_spin.setValue(1000)
        self.budget_spin.setSuffix("ms")
        self.budget_spin.valueChanged.connect(self.update_computation_budget)
        budget_layout.addWidget(self.budget_spin)
        model_layout.addLayout(budget_layout)
        
        layout.addWidget(model_group)
        
        # 推理控制组
        inference_group = QGroupBox("推理控制")
        inference_layout = QVBoxLayout(inference_group)
        
        self.inference_btn = QPushButton("🚀 启动智能推理")
        self.inference_btn.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-weight: bold; padding: 8px; }")
        self.inference_btn.clicked.connect(self.run_hyper_inference)
        self.inference_btn.setEnabled(False)
        inference_layout.addWidget(self.inference_btn)
        
        # 置信度阈值
        conf_layout = QHBoxLayout()
        conf_layout.addWidget(QLabel("置信度阈值:"))
        self.conf_threshold = QDoubleSpinBox()
        self.conf_threshold.setRange(0.1, 0.9)
        self.conf_threshold.setValue(0.25)
        self.conf_threshold.setSingleStep(0.05)
        conf_layout.addWidget(self.conf_threshold)
        inference_layout.addLayout(conf_layout)
        
        layout.addWidget(inference_group)
        
        # 结果展示组
        results_group = QGroupBox("智能洞察")
        results_layout = QVBoxLayout(results_group)
        
        self.insights_display = QTextEdit()
        self.insights_display.setReadOnly(True)
        self.insights_display.setMaximumHeight(300)
        results_layout.addWidget(self.insights_display)
        
        layout.addWidget(results_group)
        
        # 性能监控组
        perf_group = QGroupBox("性能监控")
        perf_layout = QVBoxLayout(perf_group)
        
        self.performance_display = QLabel("等待推理结果...")
        self.performance_display.setWordWrap(True)
        perf_layout.addWidget(self.performance_display)
        
        layout.addWidget(perf_group)
        
        layout.addStretch()
        
        return panel
    
    def create_display_panel(self):
        # 使用标签页组织显示
        tab_widget = QTabWidget()
        
        # 原始图像标签页
        original_tab = QWidget()
        original_layout = QVBoxLayout(original_tab)
        self.original_image_label = QLabel("原始图像")
        self.original_image_label.setAlignment(Qt.AlignCenter)
        self.original_image_label.setStyleSheet("border: 1px solid gray; min-height: 300px;")
        original_layout.addWidget(self.original_image_label)
        tab_widget.addTab(original_tab, "原始图像")
        
        # 检测结果标签页
        detection_tab = QWidget()
        detection_layout = QVBoxLayout(detection_tab)
        self.detection_image_label = QLabel("检测结果")
        self.detection_image_label.setAlignment(Qt.AlignCenter)
        self.detection_image_label.setStyleSheet("border: 1px solid gray; min-height: 300px;")
        detection_layout.addWidget(self.detection_image_label)
        tab_widget.addTab(detection_tab, "目标检测")
        
        # 分析结果标签页
        analysis_tab = QWidget()
        analysis_layout = QVBoxLayout(analysis_tab)
        
        # 使用树形控件显示分析结果
        self.analysis_tree = QTreeWidget()
        self.analysis_tree.setHeaderLabels(["分析模块", "关键结果", "置信度"])
        analysis_layout.addWidget(self.analysis_tree)
        
        tab_widget.addTab(analysis_tab, "智能分析")
        
        return tab_widget
    
    def update_computation_budget(self, value):
        """更新计算预算"""
        self.hyper_engine.computation_budget = value
        self.memory_status.setText(f"内存: 监控中 | 计算预算: {value}ms")
    
    def load_model(self):
        model_path, _ = QFileDialog.getOpenFileName(
            self, "选择YOLO模型文件", "", 
            "Model Files (*.pt *.pth);;All Files (*)"
        )
        
        if model_path:
            if self.model_loader.load_model(model_path):
                self.system_status.setText("🟢 模型加载成功 - 智能引擎就绪")
                self.system_status.setStyleSheet("color: green; font-weight: bold; font-size: 14px;")
                self.check_ready_state()
            else:
                self.system_status.setText("🔴 模型加载失败")
                self.system_status.setStyleSheet("color: red; font-weight: bold; font-size: 14px;")
    
    def load_image(self):
        image_path, _ = QFileDialog.getOpenFileName(
            self, "选择图像文件", "", 
            "Image Files (*.jpg *.jpeg *.png *.bmp);;All Files (*)"
        )
        
        if image_path:
            self.current_image_path = image_path
            
            # 显示原始图像
            pixmap = QPixmap(image_path)
            scaled_pixmap = pixmap.scaled(
                self.original_image_label.width(), 
                self.original_image_label.height(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.original_image_label.setPixmap(scaled_pixmap)
            
            # 加载图像用于推理
            self.current_image = cv2.imread(image_path)
            
            self.check_ready_state()
    
    def check_ready_state(self):
        if (self.model_loader.model is not None and 
            self.current_image is not None):  # 修正：使用 current_image 而不是 current_image_path
            self.inference_btn.setEnabled(True)
    
    def run_hyper_inference(self):
        if not hasattr(self.model_loader, 'model') or self.model_loader.model is None:
            QMessageBox.warning(self, "错误", "请先加载模型!")
            return
        
        if self.current_image is None:
            QMessageBox.warning(self, "错误", "请先加载图像!")
            return
        
        # 更新状态
        self.system_status.setText("🟡 推理进行中...")
        self.system_status.setStyleSheet("color: orange; font-weight: bold; font-size: 14px;")
        self.inference_btn.setEnabled(False)
        
        # 在后台线程中执行推理
        self.inference_thread = InferenceThread(
            self.model_loader, 
            self.hyper_engine,
            self.current_image,
            self.conf_threshold.value()
        )
        self.inference_thread.finished.connect(self.on_inference_finished)
        self.inference_thread.start()
    
    def on_inference_finished(self, result):
        # 恢复UI状态
        self.system_status.setText("🟢 推理完成")
        self.system_status.setStyleSheet("color: green; font-weight: bold; font-size: 14px;")
        self.inference_btn.setEnabled(True)
        
        if not result['success']:
            QMessageBox.warning(self, "推理错误", result['error'])
            return
        
        self.current_detections = result['detections']
        self.current_results = result['analysis_results']
        
        # 显示检测结果
        self.display_detection_result()
        
        # 显示分析结果
        self.display_analysis_results()
        
        # 更新性能显示
        self.update_performance_display()
    
    def display_detection_result(self):
        """显示检测结果"""
        if self.current_image is None:
            return
        
        result_image = self.current_image.copy()
        
        # 绘制检测框
        for detection in self.current_detections:
            bbox = detection['bbox']
            class_name = detection['class']
            confidence = detection['confidence']
            
            # 绘制边界框
            x1, y1, x2, y2 = map(int, bbox)
            cv2.rectangle(result_image, (x1, y1), (x2, y2), (0, 255, 0), 2)
            
            # 绘制标签
            label = f"{class_name}: {confidence:.2f}"
            label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)[0]
            cv2.rectangle(result_image, (x1, y1 - label_size[1] - 10), 
                         (x1 + label_size[0], y1), (0, 255, 0), -1)
            cv2.putText(result_image, label, (x1, y1 - 5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)
        
        # 转换为QPixmap并显示
        height, width, channel = result_image.shape
        bytes_per_line = 3 * width
        q_img = QImage(result_image.data, width, height, bytes_per_line, QImage.Format_RGB888).rgbSwapped()
        pixmap = QPixmap.fromImage(q_img)
        
        scaled_pixmap = pixmap.scaled(
            self.detection_image_label.width(), 
            self.detection_image_label.height(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        self.detection_image_label.setPixmap(scaled_pixmap)
    
    def display_analysis_results(self):
        """显示分析结果"""
        # 清空树形控件
        self.analysis_tree.clear()
        
        # 添加性能统计
        if '性能统计' in self.current_results:
            perf_item = QTreeWidgetItem(["性能统计", "系统性能指标", ""])
            self.analysis_tree.addTopLevelItem(perf_item)
            
            perf_stats = self.current_results['性能统计']
            for key, value in perf_stats.items():
                perf_item.addChild(QTreeWidgetItem([key, str(value), ""]))
        
        # 添加智能整合结果
        if '智能整合' in self.current_results:
            integrated_item = QTreeWidgetItem(["智能整合", "综合洞察", ""])
            self.analysis_tree.addTopLevelItem(integrated_item)
            
            insights = self.current_results['智能整合']
            integrated_item.addChild(QTreeWidgetItem([
                "场景类型", insights.get('场景类型', '未知'), ""
            ]))
            integrated_item.addChild(QTreeWidgetItem([
                "综合置信度", f"{insights.get('置信度', 0):.3f}", ""
            ]))
            integrated_item.addChild(QTreeWidgetItem([
                "计算效率", insights.get('计算效率', '未知'), ""
            ]))
            
            # 关键洞察
            insights_item = QTreeWidgetItem(["关键洞察", "", ""])
            integrated_item.addChild(insights_item)
            for insight in insights.get('关键洞察', [])[:5]:
                insights_item.addChild(QTreeWidgetItem(["", insight, ""]))
        
        # 添加各个模块的分析结果
        for module_name, results in self.current_results.items():
            if module_name not in ['性能统计', '智能整合']:
                module_item = QTreeWidgetItem([module_name, "模块分析结果", ""])
                self.analysis_tree.addTopLevelItem(module_item)
                
                # 添加置信度
                if 'confidence' in results:
                    module_item.addChild(QTreeWidgetItem([
                        "模块置信度", f"{results['confidence']:.3f}", ""
                    ]))
                
                # 添加计算时间
                if 'computation_time' in results:
                    module_item.addChild(QTreeWidgetItem([
                        "计算时间", results['computation_time'], ""
                    ]))
                
                # 添加关键洞察
                if 'insights' in results:
                    insights_item = QTreeWidgetItem(["模块洞察", "", ""])
                    module_item.addChild(insights_item)
                    for insight in results['insights'][:3]:
                        insights_item.addChild(QTreeWidgetItem(["", insight, ""]))
        
        # 展开所有节点
        self.analysis_tree.expandAll()
        
        # 更新洞察显示
        self.update_insights_display()
    
    def update_insights_display(self):
        """更新洞察显示"""
        insights_text = "🤖 智能推理洞察报告\n\n"
        insights_text += "=" * 40 + "\n\n"
        
        if '智能整合' in self.current_results:
            insights = self.current_results['智能整合']
            
            insights_text += "📊 综合评估:\n"
            insights_text += f"   场景类型: {insights.get('场景类型', '未知')}\n"
            insights_text += f"   置信度: {insights.get('置信度', 0):.1%}\n"
            insights_text += f"   计算效率: {insights.get('计算效率', '未知')}\n\n"
            
            insights_text += "🔍 关键洞察:\n"
            for insight in insights.get('关键洞察', [])[:5]:
                insights_text += f"   • {insight}\n"
        
        insights_text += f"\n🛠️ 分析模块: {len([k for k in self.current_results.keys() if k not in ['性能统计', '智能整合']])} 个智能引擎\n"
        
        self.insights_display.setText(insights_text)
    
    def update_performance_display(self):
        """更新性能显示"""
        if '性能统计' not in self.current_results:
            return
        
        perf_stats = self.current_results['性能统计']
        perf_text = "📈 性能统计:\n\n"
        
        for key, value in perf_stats.items():
            perf_text += f"{key}: {value}\n"
        
        # 添加内存使用信息
        try:
            memory_info = psutil.virtual_memory()
            perf_text += f"\n💾 系统内存: {memory_info.percent}% 使用"
        except:
            perf_text += f"\n💾 系统内存: 监控不可用"
        
        self.performance_display.setText(perf_text)

# ==================== 推理线程 ====================

class InferenceThread(QThread):
    finished = pyqtSignal(object)
    
    def __init__(self, model_loader, hyper_engine, image, conf_threshold):
        super().__init__()
        self.model_loader = model_loader
        self.hyper_engine = hyper_engine
        self.image = image
        self.conf_threshold = conf_threshold
    
    def run(self):
        try:
            # 执行YOLO推理
            results = self.model_loader.predict(self.image, conf_threshold=self.conf_threshold)
            detections = self.parse_yolo_results(results)
            
            # 执行超神级推理
            analysis_results = self.hyper_engine.efficient_analyze(detections, self.image)
            
            self.finished.emit({
                'success': True,
                'detections': detections,
                'analysis_results': analysis_results
            })
            
        except Exception as e:
            self.finished.emit({
                'success': False,
                'error': str(e)
            })
    
    def parse_yolo_results(self, results):
        """解析YOLO结果"""
        detections = []
        if results and len(results) > 0:
            result = results[0]
            if hasattr(result, 'boxes'):
                boxes = result.boxes
                for box in boxes:
                    if box.conf.item() >= self.conf_threshold:
                        x1, y1, x2, y2 = box.xyxy[0].tolist()
                        class_id = int(box.cls.item())
                        confidence = box.conf.item()
                        
                        detections.append({
                            'bbox': [x1, y1, x2, y2],
                            'class': self.model_loader.classes[class_id],
                            'confidence': confidence,
                            'class_id': class_id
                        })
        return detections

# YOLO模型加载器
class YOLOModelLoader:
    def __init__(self):
        self.model = None
        self.classes = None
        
    def load_model(self, model_path, device='cpu'):
        try:
            from ultralytics import YOLO
            self.model = YOLO(model_path)
            self.model.to(device)
            if hasattr(self.model, 'names'):
                self.classes = self.model.names
            return True
        except Exception as e:
            print(f"加载模型失败: {e}")
            return False
    
    def predict(self, image, conf_threshold=0.25, iou_threshold=0.45):
        if self.model is None:
            return None
        results = self.model(image, conf=conf_threshold, iou=iou_threshold, verbose=False)
        return results

def main():
    app = QApplication(sys.argv)
    
    # 设置应用样式
    app.setStyle('Fusion')
    
    window = LightweightInferenceApp()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()