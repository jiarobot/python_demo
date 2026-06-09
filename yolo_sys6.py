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
                             QHeaderView, QTreeWidget, QTreeWidgetItem, QListWidget)
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
from sklearn.manifold import TSNE
import matplotlib.pyplot as plt
from io import BytesIO

# ==================== 超神级推理引擎 ====================

class HyperInferenceEngine:
    def __init__(self):
        self.cognitive_modules = {
            "时空推理": SpatiotemporalReasoner(),
            "因果推断": CausalInferencer(),
            "语义网络": SemanticNetworkBuilder(),
            "多维聚类": MultidimensionalClusterer(),
            "异常检测": AnomalyDetector(),
            "行为预测": BehaviorPredictor(),
            "场景理解": SceneUnderstanding(),
            "元认知分析": MetaCognitiveAnalyzer()
        }
        
        self.memory_bank = MemoryBank()
        self.inference_history = deque(maxlen=1000)
        
    def hyper_analyze(self, detections, image, context=None):
        """超神级综合分析"""
        results = {}
        
        # 并行执行所有认知模块
        for name, module in self.cognitive_modules.items():
            try:
                results[name] = module.analyze(detections, image, context)
                # 记录推理历史
                self.inference_history.append({
                    'timestamp': time.time(),
                    'module': name,
                    'result': results[name]
                })
            except Exception as e:
                print(f"模块 {name} 执行失败: {e}")
                results[name] = {'error': str(e)}
        
        # 元认知整合
        results['整合洞察'] = self._integrate_insights(results)
        
        # 更新记忆库
        self.memory_bank.update(detections, results, image)
        
        return results
    
    def _integrate_insights(self, results):
        """整合各个模块的洞察"""
        integrated = {
            '置信度': 0.0,
            '关键发现': [],
            '行动建议': [],
            '风险等级': '低',
            '认知复杂度': 0
        }
        
        # 计算综合置信度
        confidences = []
        for name, result in results.items():
            if 'confidence' in result:
                confidences.append(result['confidence'])
            elif 'certainty' in result:
                confidences.append(result['certainty'])
        
        if confidences:
            integrated['置信度'] = np.mean(confidences)
        
        # 生成关键发现
        key_findings = set()
        for name, result in results.items():
            if 'key_findings' in result:
                key_findings.update(result['key_findings'])
            if 'insights' in result:
                key_findings.update(result['insights'])
        
        integrated['关键发现'] = list(key_findings)[:10]  # 限制数量
        
        # 生成行动建议
        if integrated['置信度'] > 0.8:
            integrated['行动建议'].append("高置信度结果，建议立即行动")
        if len(key_findings) > 5:
            integrated['行动建议'].append("检测到复杂场景，建议人工复核")
        
        # 评估风险等级
        risk_factors = sum(1 for finding in integrated['关键发现'] 
                          if any(word in finding.lower() for word in ['异常', '危险', '风险', '可疑']))
        if risk_factors > 3:
            integrated['风险等级'] = '高'
        elif risk_factors > 1:
            integrated['风险等级'] = '中'
        
        integrated['认知复杂度'] = len(key_findings) * integrated['置信度']
        
        return integrated

# ==================== 时空推理模块 ====================

class SpatiotemporalReasoner:
    def __init__(self):
        self.temporal_buffer = deque(maxlen=50)
        self.spatial_relations = ['left_of', 'right_of', 'above', 'below', 'inside', 'near']
        
    def analyze(self, detections, image, context):
        """时空推理分析"""
        current_frame = {
            'timestamp': time.time(),
            'detections': detections,
            'spatial_graph': self._build_spatial_graph(detections)
        }
        self.temporal_buffer.append(current_frame)
        
        results = {
            'temporal_trends': self._analyze_temporal_trends(),
            'spatial_relations': self._extract_spatial_relations(detections),
            'motion_patterns': self._detect_motion_patterns(),
            'trajectories': self._estimate_trajectories(),
            'certainty': self._calculate_temporal_certainty()
        }
        
        return results
    
    def _build_spatial_graph(self, detections):
        """构建空间关系图"""
        G = nx.Graph()
        for i, det1 in enumerate(detections):
            G.add_node(i, **det1)
            for j, det2 in enumerate(detections):
                if i != j:
                    relation = self._calculate_spatial_relation(det1, det2)
                    if relation['strength'] > 0.3:  # 关系强度阈值
                        G.add_edge(i, j, **relation)
        return G
    
    def _calculate_spatial_relation(self, det1, det2):
        """计算两个检测框的空间关系"""
        bbox1, bbox2 = det1['bbox'], det2['bbox']
        center1 = [(bbox1[0] + bbox1[2])/2, (bbox1[1] + bbox1[3])/2]
        center2 = [(bbox2[0] + bbox2[2])/2, (bbox2[1] + bbox2[3])/2]
        
        dx = center1[0] - center2[0]
        dy = center1[1] - center2[1]
        distance = math.sqrt(dx**2 + dy**2)
        
        relations = {}
        if abs(dx) > abs(dy):
            relations['relation'] = 'left_of' if dx < 0 else 'right_of'
        else:
            relations['relation'] = 'above' if dy < 0 else 'below'
        
        relations['strength'] = 1.0 / (1.0 + distance/100)  # 距离越近关系越强
        relations['distance'] = distance
        
        return relations
    
    def _analyze_temporal_trends(self):
        """分析时间趋势"""
        if len(self.temporal_buffer) < 2:
            return {'status': 'insufficient_data'}
        
        # 简单的趋势分析
        object_counts = [len(frame['detections']) for frame in self.temporal_buffer]
        trend = 'stable'
        if len(object_counts) >= 3:
            if object_counts[-1] > np.mean(object_counts[:-1]) + np.std(object_counts[:-1]):
                trend = 'increasing'
            elif object_counts[-1] < np.mean(object_counts[:-1]) - np.std(object_counts[:-1]):
                trend = 'decreasing'
        
        return {
            'object_count_trend': trend,
            'stability': np.std(object_counts) if object_counts else 0
        }
    
    def _extract_spatial_relations(self, detections):
        """提取空间关系"""
        relations = []
        for i, det1 in enumerate(detections):
            for j, det2 in enumerate(detections):
                if i < j:
                    relation = self._calculate_spatial_relation(det1, det2)
                    if relation['strength'] > 0.5:
                        relations.append({
                            'object1': det1['class'],
                            'object2': det2['class'],
                            'relation': relation['relation'],
                            'strength': relation['strength']
                        })
        return relations
    
    def _detect_motion_patterns(self):
        """检测运动模式"""
        if len(self.temporal_buffer) < 3:
            return {'status': 'insufficient_data'}
        
        # 简化的运动模式检测
        return {
            'motion_activity': 'moderate',  # 基于对象数量变化
            'pattern_consistency': 'high'
        }
    
    def _estimate_trajectories(self):
        """估计轨迹"""
        return {
            'estimated_trajectories': [],
            'prediction_confidence': 0.0
        }
    
    def _calculate_temporal_certainty(self):
        """计算时间维度置信度"""
        if len(self.temporal_buffer) < 5:
            return 0.3
        return min(0.9, 0.3 + len(self.temporal_buffer) * 0.1)

# ==================== 因果推断模块 ====================

class CausalInferencer:
    def __init__(self):
        self.causal_rules = self._load_causal_rules()
        
    def _load_causal_rules(self):
        """加载因果规则库"""
        rules = {
            'person': {
                'car': {'relation': 'driving', 'causal_strength': 0.8},
                'bicycle': {'relation': 'riding', 'causal_strength': 0.7},
                'cell phone': {'relation': 'using', 'causal_strength': 0.6}
            },
            'car': {
                'person': {'relation': 'transporting', 'causal_strength': 0.7},
                'traffic light': {'relation': 'responding_to', 'causal_strength': 0.5}
            }
        }
        return rules
    
    def analyze(self, detections, image, context):
        """因果推断分析"""
        causal_chains = self._find_causal_chains(detections)
        intervention_analysis = self._analyze_interventions(detections)
        counterfactuals = self._generate_counterfactuals(detections)
        
        return {
            'causal_networks': causal_chains,
            'intervention_effects': intervention_analysis,
            'counterfactual_scenarios': counterfactuals,
            'causal_confidence': self._calculate_causal_confidence(detections)
        }
    
    def _find_causal_chains(self, detections):
        """寻找因果链"""
        chains = []
        objects = [det['class'] for det in detections]
        
        for i, obj1 in enumerate(objects):
            for j, obj2 in enumerate(objects):
                if i != j:
                    # 直接因果关系
                    if obj1 in self.causal_rules and obj2 in self.causal_rules[obj1]:
                        rule = self.causal_rules[obj1][obj2]
                        chains.append({
                            'cause': obj1,
                            'effect': obj2,
                            'relation': rule['relation'],
                            'strength': rule['causal_strength'],
                            'type': 'direct'
                        })
                    
                    # 间接因果关系（通过共同对象）
                    for k, obj3 in enumerate(objects):
                        if k not in [i, j]:
                            if (obj1 in self.causal_rules and obj3 in self.causal_rules[obj1] and
                                obj3 in self.causal_rules and obj2 in self.causal_rules[obj3]):
                                chains.append({
                                    'cause': obj1,
                                    'effect': obj2,
                                    'through': obj3,
                                    'type': 'indirect',
                                    'strength': 0.5  # 间接关系强度衰减
                                })
        
        return chains
    
    def _analyze_interventions(self, detections):
        """分析干预效果"""
        interventions = []
        
        # 模拟干预分析
        for det in detections:
            if det['class'] == 'car':
                interventions.append({
                    'intervention': 'remove_car',
                    'expected_effect': 'reduce_traffic_congestion',
                    'confidence': 0.6
                })
            elif det['class'] == 'person':
                interventions.append({
                    'intervention': 'add_traffic_light',
                    'expected_effect': 'improve_pedestrian_safety',
                    'confidence': 0.7
                })
        
        return interventions
    
    def _generate_counterfactuals(self, detections):
        """生成反事实场景"""
        counterfactuals = []
        
        # 如果移除某个对象会发生什么
        for i, det in enumerate(detections):
            remaining = [d for j, d in enumerate(detections) if j != i]
            counterfactuals.append({
                'scenario': f'如果没有 {det["class"]}',
                'potential_outcomes': [
                    f'场景复杂度降低 {det["confidence"]*100:.1f}%',
                    f'可能影响 {len([d for d in remaining if self._could_interact(det, d)])} 个其他对象'
                ]
            })
        
        return counterfactuals
    
    def _could_interact(self, det1, det2):
        """判断两个对象是否可能交互"""
        interactions = [
            ('person', 'car'), ('person', 'bicycle'), 
            ('car', 'traffic light'), ('person', 'cell phone')
        ]
        return (det1['class'], det2['class']) in interactions or (det2['class'], det1['class']) in interactions
    
    def _calculate_causal_confidence(self, detections):
        """计算因果推断置信度"""
        objects = [det['class'] for det in detections]
        known_objects = sum(1 for obj in objects if obj in self.causal_rules or 
                           any(obj in rules for rules in self.causal_rules.values()))
        
        if not objects:
            return 0.0
        
        return known_objects / len(objects)

# ==================== 语义网络构建模块 ====================

class SemanticNetworkBuilder:
    def __init__(self):
        self.concept_net = self._build_concept_network()
        
    def _build_concept_network(self):
        """构建概念网络"""
        G = nx.Graph()
        
        # 添加概念节点和关系
        concepts = {
            'person': ['human', 'individual', 'pedestrian'],
            'car': ['vehicle', 'automobile', 'transportation'],
            'bicycle': ['vehicle', 'bike', 'transportation'],
            'traffic light': ['signal', 'light', 'regulation'],
            'cell phone': ['device', 'communication', 'electronic']
        }
        
        for concept, related in concepts.items():
            G.add_node(concept, type='object')
            for rel in related:
                G.add_node(rel, type='attribute')
                G.add_edge(concept, rel, relation='is_a')
        
        # 添加概念间关系
        relationships = [
            ('person', 'car', 'drives'),
            ('person', 'bicycle', 'rides'),
            ('person', 'cell phone', 'uses'),
            ('car', 'traffic light', 'obeys')
        ]
        
        for src, dst, rel in relationships:
            G.add_edge(src, dst, relation=rel)
        
        return G
    
    def analyze(self, detections, image, context):
        """语义网络分析"""
        detected_concepts = [det['class'] for det in detections]
        semantic_subnet = self._extract_semantic_subnet(detected_concepts)
        centrality_analysis = self._analyze_centrality(semantic_subnet)
        community_structure = self._detect_communities(semantic_subnet)
        
        return {
            'semantic_network': self._network_to_dict(semantic_subnet),
            'central_concepts': centrality_analysis,
            'semantic_communities': community_structure,
            'semantic_coherence': self._calculate_semantic_coherence(detected_concepts)
        }
    
    def _extract_semantic_subnet(self, concepts):
        """提取检测概念的语义子网"""
        subnet = nx.Graph()
        
        for concept in concepts:
            if concept in self.concept_net:
                # 添加概念及其直接邻居
                subnet.add_node(concept, **self.concept_net.nodes[concept])
                for neighbor in self.concept_net.neighbors(concept):
                    subnet.add_node(neighbor, **self.concept_net.nodes[neighbor])
                    subnet.add_edge(concept, neighbor, **self.concept_net.edges[concept, neighbor])
        
        return subnet
    
    def _analyze_centrality(self, network):
        """分析网络中心性"""
        if len(network.nodes) == 0:
            return {}
        
        try:
            degree_centrality = nx.degree_centrality(network)
            betweenness_centrality = nx.betweenness_centrality(network)
            
            central_concepts = []
            for node in network.nodes:
                if network.nodes[node].get('type') == 'object':
                    central_concepts.append({
                        'concept': node,
                        'degree_centrality': degree_centrality.get(node, 0),
                        'betweenness_centrality': betweenness_centrality.get(node, 0)
                    })
            
            # 按度中心性排序
            central_concepts.sort(key=lambda x: x['degree_centrality'], reverse=True)
            return central_concepts[:5]  # 返回前5个中心概念
            
        except Exception:
            return {}
    
    def _detect_communities(self, network):
        """检测语义社区"""
        if len(network.nodes) < 3:
            return []
        
        try:
            # 使用简单的连通组件作为社区
            communities = list(nx.connected_components(network))
            return [list(community) for community in communities]
        except Exception:
            return []
    
    def _network_to_dict(self, network):
        """将网络转换为字典格式"""
        return {
            'nodes': list(network.nodes(data=True)),
            'edges': list(network.edges(data=True))
        }
    
    def _calculate_semantic_coherence(self, concepts):
        """计算语义连贯性"""
        if len(concepts) < 2:
            return 1.0
        
        # 计算概念间的平均语义距离
        total_distance = 0
        count = 0
        
        for i, concept1 in enumerate(concepts):
            for j, concept2 in enumerate(concepts):
                if i < j:
                    try:
                        if concept1 in self.concept_net and concept2 in self.concept_net:
                            path_length = nx.shortest_path_length(self.concept_net, concept1, concept2)
                            total_distance += path_length
                            count += 1
                    except nx.NetworkXNoPath:
                        total_distance += 10  # 如果没有路径，赋予较大距离
        
        if count == 0:
            return 0.0
        
        avg_distance = total_distance / count
        # 距离越小，连贯性越高
        return max(0.0, 1.0 - avg_distance / 10.0)

# ==================== 多维聚类模块 ====================

class MultidimensionalClusterer:
    def __init__(self):
        self.feature_space = {}
        
    def analyze(self, detections, image, context):
        """多维聚类分析"""
        if not detections:
            return {'clusters': [], 'dimensional_reduction': {}}
        
        features = self._extract_multidimensional_features(detections, image)
        clusters = self._perform_clustering(features)
        dimensionality_reduction = self._reduce_dimensionality(features)
        
        return {
            'feature_clusters': clusters,
            'dimensional_reduction': dimensionality_reduction,
            'cluster_quality': self._evaluate_cluster_quality(clusters),
            'feature_importance': self._analyze_feature_importance(features)
        }
    
    def _extract_multidimensional_features(self, detections, image):
        """提取多维特征"""
        features = []
        
        for det in detections:
            bbox = det['bbox']
            feature_vector = [
                # 空间特征
                (bbox[0] + bbox[2]) / 2,  # 中心x
                (bbox[1] + bbox[3]) / 2,  # 中心y
                bbox[2] - bbox[0],        # 宽度
                bbox[3] - bbox[1],        # 高度
                (bbox[2] - bbox[0]) * (bbox[3] - bbox[1]),  # 面积
                
                # 语义特征（简化）
                hash(det['class']) % 100,  # 类别哈希
                det['confidence'],         # 置信度
                
                # 上下文特征
                len(detections),           # 场景中对象数量
            ]
            
            # 添加纹理特征（如果可能）
            try:
                x1, y1, x2, y2 = map(int, bbox)
                if (0 <= x1 < x2 <= image.shape[1] and 0 <= y1 < y2 <= image.shape[0]):
                    roi = image[y1:y2, x1:x2]
                    if roi.size > 0:
                        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
                        texture = np.std(gray)  # 纹理粗糙度
                        feature_vector.append(texture)
                    else:
                        feature_vector.append(0)
                else:
                    feature_vector.append(0)
            except:
                feature_vector.append(0)
            
            features.append({
                'object': det['class'],
                'feature_vector': feature_vector,
                'original_detection': det
            })
        
        return features
    
    def _perform_clustering(self, features):
        """执行聚类分析"""
        if len(features) < 2:
            return []
        
        try:
            vectors = np.array([f['feature_vector'] for f in features])
            
            # 使用DBSCAN聚类
            clustering = DBSCAN(eps=0.5, min_samples=2).fit(vectors)
            labels = clustering.labels_
            
            clusters = []
            for cluster_id in set(labels):
                if cluster_id != -1:  # 忽略噪声点
                    cluster_objects = [
                        features[i]['object'] 
                        for i in range(len(features)) 
                        if labels[i] == cluster_id
                    ]
                    clusters.append({
                        'cluster_id': cluster_id,
                        'objects': cluster_objects,
                        'size': len(cluster_objects),
                        'cohesion': self._calculate_cluster_cohesion(
                            vectors[labels == cluster_id]
                        )
                    })
            
            return clusters
        except Exception as e:
            print(f"聚类失败: {e}")
            return []
    
    def _reduce_dimensionality(self, features):
        """降维可视化"""
        if len(features) < 3:
            return {}
        
        try:
            vectors = np.array([f['feature_vector'] for f in features])
            
            # 使用t-SNE降维到2D
            tsne = TSNE(n_components=2, random_state=42)
            reduced_2d = tsne.fit_transform(vectors)
            
            # 使用PCA降维到3D
            from sklearn.decomposition import PCA
            pca = PCA(n_components=3)
            reduced_3d = pca.fit_transform(vectors)
            
            return {
                '2d_projection': reduced_2d.tolist(),
                '3d_projection': reduced_3d.tolist(),
                'explained_variance': pca.explained_variance_ratio_.tolist()
            }
        except Exception as e:
            print(f"降维失败: {e}")
            return {}
    
    def _calculate_cluster_cohesion(self, cluster_points):
        """计算聚类内聚度"""
        if len(cluster_points) < 2:
            return 1.0
        
        centroid = np.mean(cluster_points, axis=0)
        distances = np.linalg.norm(cluster_points - centroid, axis=1)
        return 1.0 / (1.0 + np.std(distances))
    
    def _evaluate_cluster_quality(self, clusters):
        """评估聚类质量"""
        if not clusters:
            return {'silhouette_score': 0, 'cluster_separation': 0}
        
        sizes = [cluster['size'] for cluster in clusters]
        cohesions = [cluster['cohesion'] for cluster in clusters]
        
        return {
            'avg_cluster_size': np.mean(sizes),
            'avg_cohesion': np.mean(cohesions),
            'cluster_balance': np.std(sizes) / (np.mean(sizes) + 1e-8)
        }
    
    def _analyze_feature_importance(self, features):
        """分析特征重要性"""
        if not features:
            return []
        
        # 简化的特征重要性分析
        feature_names = [
            'center_x', 'center_y', 'width', 'height', 'area',
            'class_hash', 'confidence', 'object_count', 'texture'
        ]
        
        vectors = np.array([f['feature_vector'] for f in features])
        # 使用方差作为重要性指标
        variances = np.var(vectors, axis=0)
        
        importance = []
        for i, var in enumerate(variances):
            if i < len(feature_names):
                importance.append({
                    'feature': feature_names[i],
                    'importance': var,
                    'normalized_importance': var / (np.sum(variances) + 1e-8)
                })
        
        return sorted(importance, key=lambda x: x['importance'], reverse=True)

# ==================== 其他高级模块（简化实现） ====================

class AnomalyDetector:
    def analyze(self, detections, image, context):
        """异常检测"""
        anomalies = []
        
        # 基于规则的异常检测
        for det in detections:
            # 异常1: 高置信度但位置异常
            if det['confidence'] > 0.8:
                bbox = det['bbox']
                center_x = (bbox[0] + bbox[2]) / 2
                center_y = (bbox[1] + bbox[3]) / 2
                
                # 如果在图像边缘
                if (center_x < 50 or center_x > image.shape[1] - 50 or
                    center_y < 50 or center_y > image.shape[0] - 50):
                    anomalies.append({
                        'type': 'edge_object',
                        'object': det['class'],
                        'confidence': det['confidence'],
                        'reason': '高置信度对象位于图像边缘'
                    })
            
            # 异常2: 尺寸异常
            width = bbox[2] - bbox[0]
            height = bbox[3] - bbox[1]
            area = width * height
            image_area = image.shape[0] * image.shape[1]
            
            if area > image_area * 0.5:  # 对象过大
                anomalies.append({
                    'type': 'oversized_object',
                    'object': det['class'],
                    'confidence': det['confidence'],
                    'reason': f'对象面积占比 {area/image_area:.1%}'
                })
        
        return {
            'detected_anomalies': anomalies,
            'anomaly_score': len(anomalies) / (len(detections) + 1e-8),
            'risk_assessment': 'high' if anomalies else 'low'
        }

class BehaviorPredictor:
    def analyze(self, detections, image, context):
        """行为预测"""
        predictions = []
        
        # 简化的行为预测
        objects = [det['class'] for det in detections]
        
        if 'person' in objects and 'car' in objects:
            predictions.append({
                'behavior': 'crossing_road',
                'actors': ['person', 'car'],
                'probability': 0.7,
                'time_horizon': 'immediate'
            })
        
        if 'car' in objects and len([o for o in objects if o == 'car']) > 3:
            predictions.append({
                'behavior': 'traffic_congestion',
                'actors': ['car'],
                'probability': 0.6,
                'time_horizon': 'near_future'
            })
        
        return {
            'behavior_predictions': predictions,
            'prediction_confidence': np.mean([p['probability'] for p in predictions]) if predictions else 0,
            'temporal_scope': [p['time_horizon'] for p in predictions]
        }

class SceneUnderstanding:
    def analyze(self, detections, image, context):
        """场景理解"""
        objects = [det['class'] for det in detections]
        scene_type = self._classify_scene(objects)
        
        return {
            'scene_type': scene_type,
            'scene_complexity': self._calculate_scene_complexity(detections),
            'dominant_objects': self._find_dominant_objects(objects),
            'scene_coherence': self._assess_scene_coherence(objects)
        }
    
    def _classify_scene(self, objects):
        """分类场景类型"""
        object_set = set(objects)
        
        if {'car', 'traffic light', 'person'} <= object_set:
            return 'urban_street'
        elif {'person', 'cell phone'} <= object_set:
            return 'social_scene'
        elif {'car', 'car'} and len([o for o in objects if o == 'car']) > 2:
            return 'traffic'
        else:
            return 'general'
    
    def _calculate_scene_complexity(self, detections):
        """计算场景复杂度"""
        if not detections:
            return 0
        
        num_objects = len(detections)
        num_classes = len(set(det['class'] for det in detections))
        avg_confidence = np.mean([det['confidence'] for det in detections])
        
        return (num_objects * 0.4 + num_classes * 0.4 + avg_confidence * 0.2) / 10
    
    def _find_dominant_objects(self, objects):
        """找到主导对象"""
        from collections import Counter
        counter = Counter(objects)
        return counter.most_common(3)
    
    def _assess_scene_coherence(self, objects):
        """评估场景连贯性"""
        coherent_scenes = [
            {'car', 'traffic light', 'person'},  # 街道场景
            {'person', 'cell phone'},            # 社交场景
        ]
        
        object_set = set(objects)
        for scene in coherent_scenes:
            if scene <= object_set:
                return 'high'
        
        return 'medium' if len(objects) > 0 else 'low'

class MetaCognitiveAnalyzer:
    def analyze(self, detections, image, context):
        """元认知分析"""
        return {
            'analysis_quality': self._assess_analysis_quality(detections),
            'confidence_calibration': self._calibrate_confidence(detections),
            'cognitive_biases': self._detect_biases(detections),
            'learning_suggestions': self._generate_learning_suggestions(detections)
        }
    
    def _assess_analysis_quality(self, detections):
        """评估分析质量"""
        if not detections:
            return {'score': 0, 'factors': ['no_objects']}
        
        factors = []
        score = 0.5  # 基础分
        
        # 对象数量
        if len(detections) > 5:
            factors.append('rich_scene')
            score += 0.2
        else:
            factors.append('sparse_scene')
        
        # 置信度质量
        avg_confidence = np.mean([det['confidence'] for det in detections])
        if avg_confidence > 0.7:
            factors.append('high_confidence')
            score += 0.2
        elif avg_confidence < 0.3:
            factors.append('low_confidence')
            score -= 0.1
        
        return {'score': min(1.0, score), 'factors': factors}
    
    def _calibrate_confidence(self, detections):
        """置信度校准"""
        if not detections:
            return {'calibration_factor': 1.0}
        
        confidences = [det['confidence'] for det in detections]
        avg_confidence = np.mean(confidences)
        
        # 简单的校准：如果平均置信度太高或太低，进行调整
        if avg_confidence > 0.8:
            return {'calibration_factor': 0.9, 'reason': 'overconfident'}
        elif avg_confidence < 0.3:
            return {'calibration_factor': 1.1, 'reason': 'underconfident'}
        else:
            return {'calibration_factor': 1.0, 'reason': 'well_calibrated'}
    
    def _detect_biases(self, detections):
        """检测认知偏差"""
        biases = []
        objects = [det['class'] for det in detections]
        
        # 检测类别不平衡
        from collections import Counter
        counter = Counter(objects)
        if len(counter) > 0:
            max_count = max(counter.values())
            for obj, count in counter.items():
                if count == max_count and count > len(objects) * 0.6:
                    biases.append({
                        'bias_type': 'category_dominance',
                        'dominant_category': obj,
                        'prevalence': count / len(objects)
                    })
        
        return biases
    
    def _generate_learning_suggestions(self, detections):
        """生成学习建议"""
        suggestions = []
        
        if len(detections) == 0:
            suggestions.append("考虑调整检测阈值或使用不同的模型")
        
        confidences = [det['confidence'] for det in detections]
        if len(confidences) > 0 and np.std(confidences) > 0.3:
            suggestions.append("检测结果置信度差异较大，建议分析不确定性来源")
        
        return suggestions

class MemoryBank:
    def __init__(self):
        self.long_term_memory = defaultdict(list)
        self.short_term_memory = deque(maxlen=100)
    
    def update(self, detections, analysis_results, image):
        """更新记忆库"""
        memory_entry = {
            'timestamp': time.time(),
            'detections': detections,
            'analysis': analysis_results,
            'image_features': self._extract_image_features(image) if image is not None else None
        }
        
        self.short_term_memory.append(memory_entry)
        
        # 定期转移到长期记忆
        if len(self.short_term_memory) % 10 == 0:
            self._consolidate_memory()
    
    def _extract_image_features(self, image):
        """提取图像特征（简化）"""
        return {
            'shape': image.shape,
            'brightness': np.mean(image),
            'contrast': np.std(image)
        }
    
    def _consolidate_memory(self):
        """巩固记忆"""
        # 简化的记忆巩固：将重要的分析结果转移到长期记忆
        for entry in self.short_term_memory:
            if entry['analysis'].get('整合洞察', {}).get('置信度', 0) > 0.8:
                key = tuple(sorted(set(det['class'] for det in entry['detections'])))
                self.long_term_memory[key].append(entry)

# ==================== PyQt界面 ====================

class HyperInferenceApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.hyper_engine = HyperInferenceEngine()
        self.model_loader = YOLOModelLoader()
        self.current_detections = []
        self.current_image = None
        self.current_results = {}
        self.current_image_path = None  # 添加这一行缺失的属性初始化
        
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("超神级YOLO二次推理系统")
        self.setGeometry(100, 100, 1600, 1000)
        
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
        
        # 模型加载组
        model_group = QGroupBox("神级推理引擎")
        model_layout = QVBoxLayout(model_group)
        
        self.model_status = QLabel("⚡ 超神引擎就绪")
        self.model_status.setStyleSheet("color: green; font-weight: bold;")
        model_layout.addWidget(self.model_status)
        
        load_model_btn = QPushButton("加载YOLO模型")
        load_model_btn.clicked.connect(self.load_model)
        model_layout.addWidget(load_model_btn)
        
        load_image_btn = QPushButton("加载图像")
        load_image_btn.clicked.connect(self.load_image)
        model_layout.addWidget(load_image_btn)
        
        # 推理按钮
        self.inference_btn = QPushButton("🚀 启动超神推理")
        self.inference_btn.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-weight: bold; }")
        self.inference_btn.clicked.connect(self.run_hyper_inference)
        self.inference_btn.setEnabled(False)
        model_layout.addWidget(self.inference_btn)
        
        layout.addWidget(model_group)
        
        # 结果显示区域
        result_group = QGroupBox("推理洞察")
        result_layout = QVBoxLayout(result_group)
        
        self.insight_display = QTextEdit()
        self.insight_display.setReadOnly(True)
        result_layout.addWidget(self.insight_display)
        
        layout.addWidget(result_group)
        
        # 认知模块状态
        module_group = QGroupBox("认知模块状态")
        module_layout = QVBoxLayout(module_group)
        
        self.module_status = QLabel()
        module_layout.addWidget(self.module_status)
        
        layout.addWidget(module_group)
        
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
        self.original_image_label.setStyleSheet("border: 1px solid gray; min-height: 400px;")
        original_layout.addWidget(self.original_image_label)
        tab_widget.addTab(original_tab, "原始图像")
        
        # 检测结果标签页
        detection_tab = QWidget()
        detection_layout = QVBoxLayout(detection_tab)
        self.detection_image_label = QLabel("检测结果")
        self.detection_image_label.setAlignment(Qt.AlignCenter)
        self.detection_image_label.setStyleSheet("border: 1px solid gray; min-height: 400px;")
        detection_layout.addWidget(self.detection_image_label)
        tab_widget.addTab(detection_tab, "目标检测")
        
        # 分析结果标签页
        analysis_tab = QWidget()
        analysis_layout = QVBoxLayout(analysis_tab)
        
        # 使用树形控件显示分析结果
        self.analysis_tree = QTreeWidget()
        self.analysis_tree.setHeaderLabels(["分析模块", "结果", "置信度"])
        analysis_layout.addWidget(self.analysis_tree)
        
        tab_widget.addTab(analysis_tab, "深度分析")
        
        # 网络可视化标签页
        network_tab = QWidget()
        network_layout = QVBoxLayout(network_tab)
        self.network_label = QLabel("语义网络可视化")
        self.network_label.setAlignment(Qt.AlignCenter)
        network_layout.addWidget(self.network_label)
        tab_widget.addTab(network_tab, "语义网络")
        
        return tab_widget
    
    def load_model(self):
        model_path, _ = QFileDialog.getOpenFileName(
            self, "选择YOLO模型文件", "", 
            "Model Files (*.pt *.pth);;All Files (*)"
        )
        
        if model_path:
            if self.model_loader.load_model(model_path):
                self.model_status.setText("✅ 模型加载成功 - 超神引擎激活")
                self.model_status.setStyleSheet("color: green; font-weight: bold;")
                self.check_ready_state()
            else:
                self.model_status.setText("❌ 模型加载失败")
                self.model_status.setStyleSheet("color: red; font-weight: bold;")
    
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
            self.current_image is not None):  # 这里应该是 current_image，不是 current_image_path
            self.inference_btn.setEnabled(True)
    
    def run_hyper_inference(self):
        if not hasattr(self.model_loader, 'model') or self.model_loader.model is None:
            QMessageBox.warning(self, "错误", "请先加载模型!")
            return
        
        if self.current_image is None:
            QMessageBox.warning(self, "错误", "请先加载图像!")
            return
        
        # 执行YOLO推理
        results = self.model_loader.predict(self.current_image)
        detections = self.parse_yolo_results(results)
        self.current_detections = detections
        
        # 显示检测结果
        self.display_detection_result()
        
        # 执行超神级推理
        self.current_results = self.hyper_engine.hyper_analyze(
            detections, self.current_image, None
        )
        
        # 显示分析结果
        self.display_hyper_analysis()
        
        # 更新模块状态
        self.update_module_status()
    
    def parse_yolo_results(self, results):
        """解析YOLO结果"""
        detections = []
        if results and len(results) > 0:
            result = results[0]
            if hasattr(result, 'boxes'):
                boxes = result.boxes
                for box in boxes:
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
    
    def display_hyper_analysis(self):
        """显示超神级分析结果"""
        # 清空树形控件
        self.analysis_tree.clear()
        
        # 添加整合洞察作为根节点
        integrated_item = QTreeWidgetItem(["整合洞察", "全局分析结果", ""])
        self.analysis_tree.addTopLevelItem(integrated_item)
        
        if '整合洞察' in self.current_results:
            insights = self.current_results['整合洞察']
            integrated_item.addChild(QTreeWidgetItem([
                "综合置信度", f"{insights.get('置信度', 0):.3f}", ""
            ]))
            integrated_item.addChild(QTreeWidgetItem([
                "风险等级", insights.get('风险等级', '未知'), ""
            ]))
            integrated_item.addChild(QTreeWidgetItem([
                "认知复杂度", f"{insights.get('认知复杂度', 0):.3f}", ""
            ]))
            
            # 关键发现
            findings_item = QTreeWidgetItem(["关键发现", "", ""])
            integrated_item.addChild(findings_item)
            for finding in insights.get('关键发现', [])[:5]:
                findings_item.addChild(QTreeWidgetItem(["", finding, ""]))
            
            # 行动建议
            actions_item = QTreeWidgetItem(["行动建议", "", ""])
            integrated_item.addChild(actions_item)
            for action in insights.get('行动建议', []):
                actions_item.addChild(QTreeWidgetItem(["", action, ""]))
        
        # 添加各个模块的分析结果
        for module_name, results in self.current_results.items():
            if module_name != '整合洞察':
                module_item = QTreeWidgetItem([module_name, "详细分析", ""])
                self.analysis_tree.addTopLevelItem(module_item)
                
                self._add_results_to_tree(module_item, results)
        
        # 展开所有节点
        self.analysis_tree.expandAll()
        
        # 更新洞察显示
        self.display_key_insights()
    
    def _add_results_to_tree(self, parent_item, results, prefix=""):
        """递归添加结果到树形控件"""
        if isinstance(results, dict):
            for key, value in results.items():
                if isinstance(value, (dict, list)):
                    child_item = QTreeWidgetItem([prefix + key, "", ""])
                    parent_item.addChild(child_item)
                    self._add_results_to_tree(child_item, value)
                else:
                    value_str = str(value)
                    if isinstance(value, float):
                        value_str = f"{value:.3f}"
                    parent_item.addChild(QTreeWidgetItem([prefix + key, value_str, ""]))
        elif isinstance(results, list):
            for i, item in enumerate(results):
                if isinstance(item, (dict, list)):
                    child_item = QTreeWidgetItem([f"{prefix}项目{i+1}", "", ""])
                    parent_item.addChild(child_item)
                    self._add_results_to_tree(child_item, item)
                else:
                    parent_item.addChild(QTreeWidgetItem([f"{prefix}项目{i+1}", str(item), ""]))
    
    def display_key_insights(self):
        """显示关键洞察"""
        insights_text = "🚀 超神级推理洞察报告\n\n"
        insights_text += "="*50 + "\n\n"
        
        if '整合洞察' in self.current_results:
            insights = self.current_results['整合洞察']
            
            insights_text += f"📊 综合评估:\n"
            insights_text += f"   • 置信度: {insights.get('置信度', 0):.1%}\n"
            insights_text += f"   • 风险等级: {insights.get('风险等级', '未知')}\n"
            insights_text += f"   • 认知复杂度: {insights.get('认知复杂度', 0):.3f}\n\n"
            
            insights_text += f"🔍 关键发现:\n"
            for finding in insights.get('关键发现', [])[:3]:
                insights_text += f"   • {finding}\n"
            
            insights_text += f"\n💡 行动建议:\n"
            for action in insights.get('行动建议', [])[:3]:
                insights_text += f"   • {action}\n"
        
        insights_text += f"\n🛠️ 分析模块: {len(self.current_results)} 个认知引擎激活\n"
        
        self.insight_display.setText(insights_text)
    
    def update_module_status(self):
        """更新模块状态显示"""
        status_text = "🧠 认知模块状态:\n\n"
        
        for module_name in self.hyper_engine.cognitive_modules.keys():
            if module_name in self.current_results:
                result = self.current_results[module_name]
                if 'confidence' in result:
                    confidence = result['confidence']
                    status_icon = "✅" if confidence > 0.7 else "⚠️" if confidence > 0.4 else "❌"
                elif 'certainty' in result:
                    certainty = result['certainty']
                    status_icon = "✅" if certainty > 0.7 else "⚠️" if certainty > 0.4 else "❌"
                else:
                    status_icon = "🔍"
                
                status_text += f"{status_icon} {module_name}\n"
            else:
                status_text += f"⏳ {module_name}\n"
        
        self.module_status.setText(status_text)

# YOLO模型加载器（与之前相同）
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
        results = self.model(image, conf=conf_threshold, iou=iou_threshold)
        return results

def main():
    app = QApplication(sys.argv)
    
    # 设置应用样式
    app.setStyle('Fusion')
    
    window = HyperInferenceApp()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()