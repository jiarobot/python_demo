import cv2
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from ultralytics import YOLO
from scipy import ndimage
from scipy.spatial import Delaunay
import matplotlib
matplotlib.rc("font", family='Microsoft YaHei')
import matplotlib.pyplot as plt
from sklearn.cluster import DBSCAN
from sklearn.mixture import GaussianMixture
import pywt
from numba import jit
import warnings
import json
import pickle
import hashlib
from datetime import datetime
import os
warnings.filterwarnings('ignore')

class MetaLearner:
    """元学习器 - 实现系统自进化能力"""
    
    def __init__(self):
        self.meta_knowledge = {}
        self.evolution_history = []
        self.performance_metrics = {}
        self.adaptation_strategies = self._initialize_adaptation_strategies()
        
    def _initialize_adaptation_strategies(self):
        """初始化自适应策略"""
        return {
            'parameter_evolution': {
                'mutation_rate': 0.1,
                'crossover_rate': 0.7,
                'selection_pressure': 0.8
            },
            'architecture_evolution': {
                'complexity_penalty': 0.01,
                'innovation_reward': 0.1,
                'stability_weight': 0.3
            },
            'knowledge_evolution': {
                'forgetting_factor': 0.05,
                'consolidation_rate': 0.2,
                'transfer_learning': 0.5
            }
        }
    
    def evolve_parameters(self, current_params, performance_feedback):
        """参数进化"""
        evolved_params = current_params.copy()
        
        for key, value in current_params.items():
            if isinstance(value, (int, float)):
                # 基于性能反馈的定向突变
                mutation_strength = self.adaptation_strategies['parameter_evolution']['mutation_rate']
                
                if performance_feedback.get('improvement_needed', False):
                    mutation_strength *= 1.5  # 增加突变强度
                
                # 高斯突变
                mutation = np.random.normal(0, mutation_strength * abs(value))
                evolved_params[key] = value + mutation
                
                # 保持参数在合理范围内
                if 'threshold' in key.lower():
                    evolved_params[key] = np.clip(evolved_params[key], 0, 1)
                elif 'rate' in key.lower():
                    evolved_params[key] = np.clip(evolved_params[key], 0, 1)
        
        return evolved_params
    
    def evolve_architecture(self, current_arch, complexity_feedback):
        """架构进化"""
        # 基于复杂性和性能的架构优化
        new_arch = current_arch.copy()
        
        complexity_score = complexity_feedback.get('complexity', 0.5)
        performance_score = complexity_feedback.get('performance', 0.5)
        
        # 计算最优复杂度
        target_complexity = performance_score * (1 - complexity_score)
        
        # 调整架构复杂度
        if target_complexity > 0.7 and len(new_arch.get('layers', [])) < 10:
            # 增加复杂度
            new_layer = {
                'type': 'adaptive',
                'complexity': target_complexity,
                'parameters': self._generate_new_layer_params()
            }
            new_arch.setdefault('layers', []).append(new_layer)
        elif target_complexity < 0.3 and len(new_arch.get('layers', [])) > 2:
            # 减少复杂度
            if new_arch.get('layers'):
                new_arch['layers'].pop()
        
        return new_arch
    
    def _generate_new_layer_params(self):
        """生成新层参数"""
        layer_types = ['quantum_conv', 'topological_pool', 'causal_attention', 'adaptive_fusion']
        return {
            'type': np.random.choice(layer_types),
            'size': np.random.randint(8, 64),
            'activation': np.random.choice(['relu', 'sigmoid', 'tanh', 'gelu'])
        }
    
    def consolidate_knowledge(self, new_experience, confidence_threshold=0.8):
        """知识巩固"""
        experience_hash = hashlib.md5(str(new_experience).encode()).hexdigest()
        
        if new_experience.get('confidence', 0) > confidence_threshold:
            # 强化现有知识
            if experience_hash in self.meta_knowledge:
                self.meta_knowledge[experience_hash]['strength'] += 1
                self.meta_knowledge[experience_hash]['last_used'] = datetime.now()
            else:
                # 创建新知识
                self.meta_knowledge[experience_hash] = {
                    'experience': new_experience,
                    'strength': 1,
                    'created': datetime.now(),
                    'last_used': datetime.now(),
                    'applicability_score': self._calculate_applicability(new_experience)
                }
        
        # 知识遗忘机制
        self._forget_weak_knowledge()
        
        return len(self.meta_knowledge)
    
    def _calculate_applicability(self, experience):
        """计算知识适用性"""
        factors = [
            experience.get('generalizability', 0.5),
            experience.get('robustness', 0.5),
            experience.get('novelty', 0.3)
        ]
        return np.mean(factors)
    
    def _forget_weak_knowledge(self):
        """弱知识遗忘"""
        current_time = datetime.now()
        forgotten_keys = []
        
        for key, knowledge in self.meta_knowledge.items():
            time_diff = (current_time - knowledge['last_used']).days
            forgetting_probability = (1 - knowledge['strength'] / 100) * time_diff / 30
            
            if np.random.random() < forgetting_probability:
                forgotten_keys.append(key)
        
        for key in forgotten_keys:
            del self.meta_knowledge[key]
    
    def transfer_learning(self, source_domain, target_domain):
        """迁移学习"""
        transferable_knowledge = []
        
        for knowledge in self.meta_knowledge.values():
            if self._is_transferable(knowledge, source_domain, target_domain):
                transferable_knowledge.append(knowledge)
        
        # 按适用性排序
        transferable_knowledge.sort(key=lambda x: x['applicability_score'], reverse=True)
        
        return transferable_knowledge[:5]  # 返回前5个最适用的知识
    
    def _is_transferable(self, knowledge, source_domain, target_domain):
        """判断知识是否可迁移"""
        experience = knowledge['experience']
        
        # 领域相似度计算
        domain_similarity = self._calculate_domain_similarity(source_domain, target_domain)
        
        # 知识通用性
        generalizability = experience.get('generalizability', 0.5)
        
        return domain_similarity * generalizability > 0.6

class NeuralEvolutionaryOptimizer:
    """神经进化优化器"""
    
    def __init__(self, population_size=20):
        self.population_size = population_size
        self.population = []
        self.fitness_scores = {}
        self.generation = 0
        self.best_individual = None
        
        self._initialize_population()
    
    def _initialize_population(self):
        """初始化种群"""
        for i in range(self.population_size):
            individual = {
                'id': i,
                'genes': self._generate_random_genes(),
                'age': 0,
                'fitness': 0,
                'specialization': np.random.choice(['quantum', 'topological', 'causal', 'fusion'])
            }
            self.population.append(individual)
    
    def _generate_random_genes(self):
        """生成随机基因"""
        genes = {
            'quantum_sensitivity': np.random.uniform(0.1, 1.0),
            'topological_complexity': np.random.uniform(0.1, 1.0),
            'causal_depth': np.random.uniform(0.1, 1.0),
            'fusion_strategy': np.random.choice(['weighted', 'geometric', 'harmonic', 'adaptive']),
            'adaptation_rate': np.random.uniform(0.01, 0.1),
            'innovation_bias': np.random.uniform(0.1, 0.9)
        }
        return genes
    
    def evaluate_fitness(self, individual, performance_data):
        """评估适应度"""
        fitness = 0
        
        # 检测性能
        detection_accuracy = performance_data.get('accuracy', 0.5)
        fitness += detection_accuracy * 0.4
        
        # 计算效率
        efficiency = performance_data.get('efficiency', 0.5)
        fitness += efficiency * 0.2
        
        # 鲁棒性
        robustness = performance_data.get('robustness', 0.5)
        fitness += robustness * 0.2
        
        # 创新性
        innovation = performance_data.get('innovation', 0.5)
        fitness += innovation * 0.2
        
        individual['fitness'] = fitness
        self.fitness_scores[individual['id']] = fitness
        
        return fitness
    
    def evolve_population(self):
        """种群进化"""
        self.generation += 1
        
        # 选择
        selected_parents = self._selection()
        
        # 交叉和变异
        new_population = self._crossover_and_mutation(selected_parents)
        
        # 替换
        self.population = new_population
        
        # 更新最佳个体
        self._update_best_individual()
        
        return self.best_individual
    
    def _selection(self):
        """选择操作"""
        # 按适应度排序
        sorted_population = sorted(self.population, key=lambda x: x['fitness'], reverse=True)
        
        # 精英选择：保留前20%
        elite_count = max(1, int(0.2 * self.population_size))
        selected = sorted_population[:elite_count]
        
        # 轮盘赌选择剩余个体
        remaining_count = self.population_size - elite_count
        fitness_sum = sum(ind['fitness'] for ind in self.population)
        
        for _ in range(remaining_count):
            pick = np.random.uniform(0, fitness_sum)
            current = 0
            for individual in self.population:
                current += individual['fitness']
                if current > pick:
                    selected.append(individual.copy())
                    break
        
        return selected
    
    def _crossover_and_mutation(self, parents):
        """交叉和变异"""
        new_population = []
        
        while len(new_population) < self.population_size:
            # 选择父母
            parent1, parent2 = np.random.choice(parents, 2, replace=False)
            
            # 交叉
            child_genes = self._crossover(parent1['genes'], parent2['genes'])
            
            # 变异
            child_genes = self._mutate(child_genes)
            
            child = {
                'id': len(new_population),
                'genes': child_genes,
                'age': 0,
                'fitness': 0,
                'specialization': self._inherit_specialization(parent1, parent2)
            }
            
            new_population.append(child)
        
        return new_population
    
    def _crossover(self, genes1, genes2):
        """基因交叉"""
        child_genes = {}
        
        for key in genes1.keys():
            if np.random.random() < 0.5:
                child_genes[key] = genes1[key]
            else:
                child_genes[key] = genes2[key]
        
        return child_genes
    
    def _mutate(self, genes, mutation_rate=0.1):
        """基因变异"""
        mutated_genes = genes.copy()
        
        for key in mutated_genes.keys():
            if np.random.random() < mutation_rate:
                if isinstance(mutated_genes[key], float):
                    # 高斯变异
                    mutation = np.random.normal(0, 0.1)
                    mutated_genes[key] = np.clip(mutated_genes[key] + mutation, 0.1, 1.0)
                elif isinstance(mutated_genes[key], str):
                    # 策略变异
                    strategies = ['weighted', 'geometric', 'harmonic', 'adaptive']
                    current_index = strategies.index(mutated_genes[key])
                    new_index = (current_index + np.random.randint(1, len(strategies))) % len(strategies)
                    mutated_genes[key] = strategies[new_index]
        
        return mutated_genes
    
    def _inherit_specialization(self, parent1, parent2):
        """继承专业化特征"""
        if parent1['specialization'] == parent2['specialization']:
            return parent1['specialization']
        else:
            # 50%概率选择父母之一的专业化
            return parent1['specialization'] if np.random.random() < 0.5 else parent2['specialization']
    
    def _update_best_individual(self):
        """更新最佳个体"""
        best_individual = max(self.population, key=lambda x: x['fitness'])
        
        if self.best_individual is None or best_individual['fitness'] > self.best_individual['fitness']:
            self.best_individual = best_individual.copy()

class SelfEvolvingTunnelDetector:
    """自进化隧道检测器"""
    
    def __init__(self, yolo_model='yolov8n.pt'):
        # 核心组件
        self.yolo = YOLO(yolo_model)
        self.meta_learner = MetaLearner()
        self.evolutionary_optimizer = NeuralEvolutionaryOptimizer()
        
        # 进化状态
        self.evolution_state = {
            'generation': 0,
            'best_fitness': 0,
            'adaptation_level': 0,
            'knowledge_base_size': 0,
            'last_improvement': datetime.now()
        }
        
        # 当前最佳配置
        self.current_best_genes = None
        self.performance_history = []
        
        # 初始化自适应参数
        self._initialize_adaptive_parameters()
    
    def _initialize_adaptive_parameters(self):
        """初始化自适应参数"""
        self.adaptive_params = {
            'structural_analysis': {
                'crack_sensitivity': 0.7,
                'deformation_threshold': 0.6,
                'corrosion_sensitivity': 0.8,
                'leakage_detection_level': 0.75
            },
            'topological_analysis': {
                'persistence_threshold': 0.1,
                'homology_depth': 3,
                'complexity_weight': 0.5
            },
            'causal_inference': {
                'causal_depth': 2,
                'confidence_threshold': 0.6,
                'temporal_window': 5
            },
            'fusion_strategy': {
                'method': 'adaptive',
                'confidence_weighting': True,
                'dynamic_threshold': 0.5
            }
        }
    
    def detect_with_evolution(self, image_path, feedback_data=None):
        """带进化的检测"""
        # 加载图像
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"无法读取图像: {image_path}")
        
        print(f"🚀 第{self.evolution_state['generation']}代自进化检测开始...")
        
        # 获取当前最佳基因配置
        if self.current_best_genes:
            self._apply_gene_configuration(self.current_best_genes)
        
        # 执行多模态检测
        detection_results = self._multimodal_evolutionary_detection(image)
        
        # 性能评估
        performance_metrics = self._evaluate_performance(detection_results, feedback_data)
        
        # 进化优化
        if feedback_data is not None:
            self._evolutionary_optimization(performance_metrics)
        
        # 知识巩固
        self._consolidate_knowledge(detection_results, performance_metrics)
        
        # 更新进化状态
        self._update_evolution_state(performance_metrics)
        
        return {
            'detection_results': detection_results,
            'performance_metrics': performance_metrics,
            'evolution_state': self.evolution_state.copy(),
            'adaptive_params': self.adaptive_params.copy()
        }
    
    def _multimodal_evolutionary_detection(self, image):
        """多模态进化检测"""
        results = {}
        
        # 保存原始图像用于可视化
        results['original_image'] = image.copy()
        
        # 1. 结构损伤检测
        results['structural_analysis'] = self._evolutionary_structural_detection(image)
        
        # 2. 拓扑进化分析
        results['topological_analysis'] = self._evolutionary_topological_analysis(image)
        
        # 3. 因果进化推理
        results['causal_analysis'] = self._evolutionary_causal_inference(image, results)
        
        # 4. YOLO进化辅助
        results['yolo_analysis'] = self._evolutionary_yolo_analysis(image)
        
        # 5. 自适应融合
        results['final_detection'] = self._adaptive_fusion(results)
        
        return results
    
    def _evolutionary_structural_detection(self, image):
        """进化结构损伤检测"""
        structural_params = self.adaptive_params['structural_analysis']
        
        # 裂缝检测
        crack_analysis = self._detect_cracks(image, structural_params['crack_sensitivity'])
        
        # 变形检测
        deformation_analysis = self._detect_deformation(image, structural_params['deformation_threshold'])
        
        # 腐蚀检测
        corrosion_analysis = self._detect_corrosion(image, structural_params['corrosion_sensitivity'])
        
        # 渗漏检测
        leakage_analysis = self._detect_leakage(image, structural_params['leakage_detection_level'])
        
        return {
            'cracks': crack_analysis,
            'deformation': deformation_analysis,
            'corrosion': corrosion_analysis,
            'leakage': leakage_analysis,
            'overall_damage': self._calculate_overall_damage(
                crack_analysis, deformation_analysis, corrosion_analysis, leakage_analysis
            )
        }
    
    def _detect_cracks(self, image, sensitivity):
        """检测裂缝"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # 使用Canny边缘检测
        edges = cv2.Canny(gray, 50, 150)
        
        # 使用Hough变换检测直线（裂缝）
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=30, 
                               minLineLength=20, maxLineGap=10)
        
        crack_density = 0
        if lines is not None:
            # 计算裂缝密度
            total_length = sum(np.sqrt((x2-x1)**2 + (y2-y1)**2) for line in lines for x1,y1,x2,y2 in [line[0]])
            image_area = gray.shape[0] * gray.shape[1]
            crack_density = min(1.0, total_length / image_area * 1000)
        
        # 使用形态学操作增强裂缝检测
        kernel = np.ones((3,3), np.uint8)
        dilated_edges = cv2.dilate(edges, kernel, iterations=1)
        
        # 计算裂缝区域比例
        crack_ratio = np.sum(dilated_edges > 0) / (image.shape[0] * image.shape[1])
        
        # 综合裂缝指标
        crack_score = min(1.0, (crack_density + crack_ratio * 5) * sensitivity)
        
        return {
            'score': crack_score,
            'density': crack_density,
            'ratio': crack_ratio,
            'lines': lines if lines is not None else []
        }
    
    def _detect_deformation(self, image, threshold):
        """检测结构变形"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # 使用SIFT特征点检测结构变化
        sift = cv2.SIFT_create()
        keypoints, descriptors = sift.detectAndCompute(gray, None)
        
        # 计算结构不规则性
        if len(keypoints) > 10:
            # 计算关键点分布的均匀性
            points = np.array([kp.pt for kp in keypoints])
            std_dev = np.std(points, axis=0)
            irregularity = min(1.0, (std_dev[0] + std_dev[1]) / (gray.shape[0] + gray.shape[1]) * 10)
        else:
            irregularity = 0.1
        
        # 使用轮廓分析检测形状异常
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        shape_anomaly = 0
        if contours:
            # 计算轮廓的凸性缺陷
            for contour in contours:
                if len(contour) > 5:
                    hull = cv2.convexHull(contour, returnPoints=False)
                    if len(hull) > 3:
                        defects = cv2.convexityDefects(contour, hull)
                        if defects is not None:
                            shape_anomaly += len(defects)
            
            shape_anomaly = min(1.0, shape_anomaly / len(contours) * 0.1)
        
        deformation_score = min(1.0, (irregularity + shape_anomaly) * threshold)
        
        return {
            'score': deformation_score,
            'irregularity': irregularity,
            'shape_anomaly': shape_anomaly,
            'keypoints_count': len(keypoints) if keypoints else 0
        }
    
    def _detect_corrosion(self, image, sensitivity):
        """检测腐蚀"""
        # 转换到HSV颜色空间检测锈蚀颜色
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        # 定义锈蚀颜色范围（红褐色）
        lower_rust1 = np.array([0, 50, 50])
        upper_rust1 = np.array([10, 255, 255])
        lower_rust2 = np.array([160, 50, 50])
        upper_rust2 = np.array([180, 255, 255])
        
        mask1 = cv2.inRange(hsv, lower_rust1, upper_rust1)
        mask2 = cv2.inRange(hsv, lower_rust2, upper_rust2)
        rust_mask = cv2.bitwise_or(mask1, mask2)
        
        # 计算锈蚀区域比例
        rust_ratio = np.sum(rust_mask > 0) / (image.shape[0] * image.shape[1])
        
        # 使用纹理分析检测表面劣化
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        texture_roughness = np.std(cv2.Laplacian(gray, cv2.CV_64F))
        texture_score = min(1.0, texture_roughness / 100)
        
        corrosion_score = min(1.0, (rust_ratio * 5 + texture_score) * sensitivity)
        
        return {
            'score': corrosion_score,
            'rust_ratio': rust_ratio,
            'texture_roughness': texture_roughness,
            'rust_mask': rust_mask
        }
    
    def _detect_leakage(self, image, detection_level):
        """检测渗漏"""
        # 检测水渍和潮湿区域
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        # 水渍通常显示为暗色区域
        lower_dark = np.array([0, 0, 0])
        upper_dark = np.array([180, 255, 100])
        dark_mask = cv2.inRange(hsv, lower_dark, upper_dark)
        
        # 潮湿区域可能有反光
        lower_bright = np.array([0, 0, 150])
        upper_bright = np.array([180, 50, 255])
        bright_mask = cv2.inRange(hsv, lower_bright, upper_bright)
        
        # 结合两种特征
        leakage_mask = cv2.bitwise_or(dark_mask, bright_mask)
        
        # 计算渗漏区域比例
        leakage_ratio = np.sum(leakage_mask > 0) / (image.shape[0] * image.shape[1])
        
        # 检测渗漏的纹理特征（模糊、扩散）
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blurriness = cv2.Laplacian(gray, cv2.CV_64F).var()
        blur_score = max(0, 1 - blurriness / 1000)  # 模糊度越高，渗漏可能性越大
        
        leakage_score = min(1.0, (leakage_ratio * 10 + blur_score) * detection_level)
        
        return {
            'score': leakage_score,
            'leakage_ratio': leakage_ratio,
            'blurriness': blurriness,
            'leakage_mask': leakage_mask
        }
    
    def _calculate_overall_damage(self, cracks, deformation, corrosion, leakage):
        """计算总体损伤程度"""
        weights = [0.3, 0.25, 0.25, 0.2]  # 裂缝、变形、腐蚀、渗漏的权重
        scores = [cracks['score'], deformation['score'], corrosion['score'], leakage['score']]
        
        overall_score = np.average(scores, weights=weights)
        
        # 根据损伤程度分类
        if overall_score < 0.2:
            level = "完好"
        elif overall_score < 0.4:
            level = "轻微损伤"
        elif overall_score < 0.6:
            level = "中度损伤"
        elif overall_score < 0.8:
            level = "严重损伤"
        else:
            level = "危险状态"
        
        return {
            'score': overall_score,
            'level': level,
            'components': {
                'cracks': cracks['score'],
                'deformation': deformation['score'],
                'corrosion': corrosion['score'],
                'leakage': leakage['score']
            }
        }
    
    def _evolutionary_topological_analysis(self, image):
        """进化拓扑分析"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # 自适应拓扑参数
        topological_params = self.adaptive_params['topological_analysis']
        
        # 多尺度拓扑分析
        topological_features = {}
        
        for scale in [1, 2, 4]:
            scaled_image = cv2.resize(gray, 
                                    (gray.shape[1]//scale, gray.shape[0]//scale))
            
            # 进化持续同调
            persistence_features = self._evolutionary_persistent_homology(
                scaled_image, topological_params
            )
            topological_features[f'scale_{scale}'] = persistence_features
        
        # 多尺度融合
        fused_topology = self._fuse_multiscale_topology(topological_features)
        
        return fused_topology
    
    def _evolutionary_persistent_homology(self, image, params):
        """进化持续同调"""
        # 距离变换
        _, binary = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        distance_transform = cv2.distanceTransform(binary, cv2.DIST_L2, 5)
        
        # 自适应阈值
        max_distance = np.max(distance_transform)
        n_thresholds = int(params['homology_depth'] * 10)
        thresholds = np.linspace(0, max_distance, n_thresholds)
        
        topological_evolution = []
        
        for threshold in thresholds:
            level_set = distance_transform > threshold
            
            # 连通分量（0维同调）
            components = ndimage.label(level_set)[1]
            
            # 孔洞检测（1维同调）
            holes = self._count_evolutionary_holes(level_set)
            
            topological_evolution.append({
                'threshold': threshold,
                'components': components,
                'holes': holes,
                'complexity': components + holes
            })
        
        # 计算进化拓扑熵
        topological_entropy = self._calculate_evolutionary_topological_entropy(topological_evolution)
        
        return {
            'evolution': topological_evolution,
            'entropy': topological_entropy,
            'max_complexity': max([t['complexity'] for t in topological_evolution])
        }
    
    def _count_evolutionary_holes(self, binary_image):
        """计算进化孔洞数量"""
        try:
            # 尝试使用scipy的欧拉数计算
            euler_characteristic = ndimage.binary_euler_number(binary_image)
        except AttributeError:
            # 如果scipy版本不支持，使用替代方法计算欧拉数
            euler_characteristic = self._calculate_euler_number_alternative(binary_image)
        
        components = ndimage.label(binary_image)[1]
        
        # 进化孔洞计算：欧拉数 = 连通分量数 - 孔洞数
        # 所以：孔洞数 = 连通分量数 - 欧拉数
        holes = components - euler_characteristic
        complexity_adjustment = self.adaptive_params['topological_analysis']['complexity_weight']
        
        return max(0, holes * complexity_adjustment)

    def _calculate_euler_number_alternative(self, binary_image):
        """替代方法计算欧拉数"""
        # 方法1: 使用连通分量和孔洞的关系
        labeled_image, num_components = ndimage.label(binary_image)
        
        # 计算孔洞数量 - 使用填充方法
        filled_image = ndimage.binary_fill_holes(binary_image)
        holes = np.sum(filled_image & ~binary_image)
        
        # 欧拉数 = 连通分量数 - 孔洞数
        euler = num_components - holes
        return euler
    
    def _calculate_evolutionary_topological_entropy(self, topological_evolution):
        """计算进化拓扑熵"""
        complexities = [t['complexity'] for t in topological_evolution]
        
        if not complexities or max(complexities) == 0:
            return 0.0
        
        # 归一化复杂度
        normalized_complexities = np.array(complexities) / max(complexities)
        
        # 计算概率分布
        probabilities = normalized_complexities / np.sum(normalized_complexities)
        
        # 进化熵计算
        entropy = -np.sum(probabilities * np.log(probabilities + 1e-8))
        normalized_entropy = entropy / np.log(len(probabilities) + 1e-8)
        
        return normalized_entropy
    
    def _fuse_multiscale_topology(self, topological_features):
        """融合多尺度拓扑"""
        # 自适应尺度权重
        scale_weights = {'scale_1': 0.5, 'scale_2': 0.3, 'scale_4': 0.2}
        
        fused_entropy = 0
        fused_complexity = 0
        
        for scale, features in topological_features.items():
            weight = scale_weights[scale]
            fused_entropy += features['entropy'] * weight
            fused_complexity += features['max_complexity'] * weight
        
        return {
            'fused_entropy': fused_entropy,
            'fused_complexity': fused_complexity,
            'scale_features': topological_features
        }
    
    def _evolutionary_causal_inference(self, image, previous_results):
        """进化因果推理"""
        # 构建进化因果图
        causal_graph = self._build_evolutionary_causal_graph(image, previous_results)
        
        # 因果效应计算
        causal_effects = self._calculate_evolutionary_causal_effects(causal_graph)
        
        # 干预分析
        intervention_analysis = self._evolutionary_intervention_analysis(causal_graph)
        
        return {
            'causal_graph': causal_graph,
            'causal_effects': causal_effects,
            'intervention_analysis': intervention_analysis
        }
    
    def _build_evolutionary_causal_graph(self, image, previous_results):
        """构建进化因果图"""
        nodes = {}
        
        # 结构损伤节点
        structural_analysis = previous_results['structural_analysis']
        nodes['crack_severity'] = structural_analysis['cracks']['score']
        nodes['deformation_level'] = structural_analysis['deformation']['score']
        nodes['corrosion_extent'] = structural_analysis['corrosion']['score']
        nodes['leakage_presence'] = structural_analysis['leakage']['score']
        
        # 拓扑节点
        topo_analysis = previous_results['topological_analysis']
        nodes['topological_complexity'] = topo_analysis['fused_complexity'] / 100  # 归一化
        nodes['structural_entropy'] = topo_analysis['fused_entropy']
        
        # 图像特征节点
        nodes['texture_anomaly'] = self._calculate_texture_anomaly(image)
        nodes['color_consistency'] = self._calculate_color_consistency(image)
        
        # 时间演化节点（如果可用）
        if hasattr(self, 'previous_detection'):
            nodes['temporal_evolution'] = self._calculate_temporal_evolution()
        else:
            nodes['temporal_evolution'] = 0.5
        
        return nodes
    
    def _calculate_evolutionary_causal_effects(self, causal_graph):
        """计算进化因果效应"""
        nodes = list(causal_graph.values())
        
        if len(nodes) < 2:
            return {'total_effect': 0.5, 'confidence': 0.5}
        
        # 进化相关性分析
        correlation_matrix = np.corrcoef([nodes, [1 - n for n in nodes]])[0, 1]
        
        # 因果强度计算
        causal_strength = abs(correlation_matrix)
        
        # 自适应置信度
        confidence_params = self.adaptive_params['causal_inference']
        confidence_threshold = confidence_params['confidence_threshold']
        
        if causal_strength > confidence_threshold:
            confidence = min(1.0, causal_strength * 1.5)
        else:
            confidence = causal_strength
        
        return {
            'total_effect': causal_strength,
            'confidence': confidence,
            'normalized_effect': causal_strength * confidence
        }
    
    def _evolutionary_intervention_analysis(self, causal_graph):
        """进化干预分析"""
        # 模拟干预效果
        intervention_results = {}
        
        for node_name, node_value in causal_graph.items():
            # 模拟将该节点设置为正常值的效果
            normal_value = 0.1  # 假设的正常值
            
            # 计算干预效应
            intervention_effect = abs(node_value - normal_value)
            
            # 进化权重调整
            evolutionary_weight = self._get_evolutionary_node_weight(node_name)
            
            intervention_results[node_name] = {
                'intervention_effect': intervention_effect,
                'evolutionary_weight': evolutionary_weight,
                'weighted_effect': intervention_effect * evolutionary_weight
            }
        
        # 总干预效应
        total_intervention = sum([ir['weighted_effect'] for ir in intervention_results.values()])
        
        return {
            'intervention_results': intervention_results,
            'total_intervention_effect': total_intervention / len(intervention_results)
        }
    
    def _get_evolutionary_node_weight(self, node_name):
        """获取进化节点权重"""
        # 基于历史性能的权重分配
        weight_mapping = {
            'crack_severity': 0.25,
            'deformation_level': 0.2,
            'corrosion_extent': 0.2,
            'leakage_presence': 0.15,
            'topological_complexity': 0.1,
            'structural_entropy': 0.05,
            'texture_anomaly': 0.03,
            'color_consistency': 0.02
        }
        
        return weight_mapping.get(node_name, 0.1)
    
    def _evolutionary_yolo_analysis(self, image):
        """进化YOLO分析"""
        results = self.yolo(image)
        
        yolo_insights = {
            'object_count': 0,
            'spatial_distribution': 0.5,
            'context_anomaly': 0.5,
            'evolutionary_confidence': 0.5
        }
        
        if len(results[0].boxes) == 0:
            return yolo_insights
        
        boxes = results[0].boxes.xyxy.cpu().numpy()
        confidences = results[0].boxes.conf.cpu().numpy()
        
        # 进化对象计数
        yolo_insights['object_count'] = len(boxes)
        
        # 空间分布分析
        if len(boxes) > 1:
            centers = np.array([[(x1+x2)/2, (y1+y2)/2] for x1, y1, x2, y2 in boxes])
            from scipy.spatial.distance import pdist
            distances = pdist(centers)
            yolo_insights['spatial_distribution'] = np.std(distances) / (np.mean(distances) + 1e-8)
        
        # 上下文异常检测
        avg_confidence = np.mean(confidences)
        yolo_insights['context_anomaly'] = 1.0 - avg_confidence
        
        # 进化置信度调整
        evolutionary_factor = self.adaptive_params['fusion_strategy'].get('dynamic_threshold', 0.5)
        yolo_insights['evolutionary_confidence'] = avg_confidence * evolutionary_factor
        
        return yolo_insights
    
    def _adaptive_fusion(self, all_results):
        """自适应融合"""
        fusion_params = self.adaptive_params['fusion_strategy']
        fusion_method = fusion_params['method']
        
        # 提取各模态证据
        structural_evidence = all_results['structural_analysis']['overall_damage']['score']
        topological_evidence = all_results['topological_analysis']['fused_entropy']
        causal_evidence = all_results['causal_analysis']['causal_effects']['normalized_effect']
        yolo_evidence = 1.0 - all_results['yolo_analysis']['context_anomaly']
        
        evidences = [structural_evidence, topological_evidence, causal_evidence, yolo_evidence]
        
        # 基于进化策略的融合
        if fusion_method == 'weighted':
            # 自适应权重
            weights = self._calculate_evolutionary_weights(evidences)
            final_confidence = np.average(evidences, weights=weights)
        
        elif fusion_method == 'geometric':
            final_confidence = np.exp(np.mean(np.log(np.array(evidences) + 1e-8)))
        
        elif fusion_method == 'harmonic':
            final_confidence = len(evidences) / np.sum(1.0 / (np.array(evidences) + 1e-8))
        
        else:  # adaptive
            # 基于证据质量的动态融合
            evidence_quality = self._assess_evidence_quality(evidences)
            weights = evidence_quality / np.sum(evidence_quality)
            final_confidence = np.average(evidences, weights=weights)
        
        # 动态阈值调整
        dynamic_threshold = fusion_params.get('dynamic_threshold', 0.5)
        normalized_confidence = min(1.0, final_confidence / dynamic_threshold)
        
        return {
            'final_confidence': normalized_confidence,
            'structural_contribution': structural_evidence,
            'topological_contribution': topological_evidence,
            'causal_contribution': causal_evidence,
            'contextual_contribution': yolo_evidence,
            'fusion_method': fusion_method,
            'anomaly_level': self._classify_anomaly_level(normalized_confidence)
        }
    
    def _calculate_evolutionary_weights(self, evidences):
        """计算进化权重"""
        # 基于历史性能的权重分配
        base_weights = [0.4, 0.25, 0.2, 0.15]  # structural, topological, causal, contextual
        
        # 根据证据强度调整权重
        evidence_strength = np.array(evidences)
        strength_weights = evidence_strength / np.sum(evidence_strength)
        
        # 进化混合
        evolutionary_mix = 0.7  # 倾向于历史性能
        final_weights = evolutionary_mix * np.array(base_weights) + (1 - evolutionary_mix) * strength_weights
        
        return final_weights / np.sum(final_weights)
    
    def _assess_evidence_quality(self, evidences):
        """评估证据质量"""
        # 基于一致性和强度的质量评估
        mean_evidence = np.mean(evidences)
        std_evidence = np.std(evidences)
        
        # 一致性分数（标准差越小越好）
        consistency_scores = 1.0 / (1.0 + std_evidence)
        
        # 强度分数
        strength_scores = np.array(evidences)
        
        # 质量综合
        quality_scores = consistency_scores * strength_scores
        
        return quality_scores
    
    def _classify_anomaly_level(self, confidence):
        """分类异常级别"""
        if confidence < 0.2:
            return "结构完好"
        elif confidence < 0.4:
            return "轻微损伤"
        elif confidence < 0.6:
            return "中度损伤"
        elif confidence < 0.8:
            return "严重损伤"
        else:
            return "危险状态"
    
    def _evaluate_performance(self, detection_results, feedback_data):
        """评估性能"""
        performance = {}
        
        final_detection = detection_results['final_detection']
        
        # 检测置信度
        performance['detection_confidence'] = final_detection['final_confidence']
        
        # 证据一致性
        contributions = [
            final_detection['structural_contribution'],
            final_detection['topological_contribution'],
            final_detection['causal_contribution'],
            final_detection['contextual_contribution']
        ]
        performance['evidence_consistency'] = 1.0 - np.std(contributions)
        
        # 计算效率（简化）
        performance['computational_efficiency'] = 0.8  # 假设值
        
        # 如果有反馈数据，计算准确性
        if feedback_data is not None:
            ground_truth = feedback_data.get('ground_truth', 0.5)
            detection_score = final_detection['final_confidence']
            performance['accuracy'] = 1.0 - abs(ground_truth - detection_score)
        else:
            performance['accuracy'] = performance['detection_confidence']
        
        # 创新性评估
        performance['innovation'] = self._assess_innovation(detection_results)
        
        # 总体性能
        performance['overall_performance'] = (
            performance['accuracy'] * 0.4 +
            performance['evidence_consistency'] * 0.3 +
            performance['computational_efficiency'] * 0.2 +
            performance['innovation'] * 0.1
        )
        
        return performance
    
    def _assess_innovation(self, detection_results):
        """评估创新性"""
        # 基于方法多样性和新颖性的创新评估
        innovation_score = 0
        
        # 结构分析创新
        structural_damage = detection_results['structural_analysis']['overall_damage']['score']
        innovation_score += min(1.0, structural_damage * 2) * 0.4
        
        # 拓扑分析创新
        topological_entropy = detection_results['topological_analysis']['fused_entropy']
        innovation_score += topological_entropy * 0.3
        
        # 因果推理创新
        causal_effect = detection_results['causal_analysis']['causal_effects']['normalized_effect']
        innovation_score += causal_effect * 0.2
        
        # 融合策略创新
        fusion_method = detection_results['final_detection']['fusion_method']
        if fusion_method == 'adaptive':
            innovation_score += 0.1
        
        return innovation_score
    
    def _evolutionary_optimization(self, performance_metrics):
        """进化优化"""
        print("🔬 执行进化优化...")
        
        # 评估当前种群
        for individual in self.evolutionary_optimizer.population:
            self.evolutionary_optimizer.evaluate_fitness(individual, performance_metrics)
        
        # 执行进化
        best_individual = self.evolutionary_optimizer.evolve_population()
        
        # 更新当前最佳基因
        if (self.current_best_genes is None or 
            best_individual['fitness'] > self.evolution_state['best_fitness']):
            self.current_best_genes = best_individual['genes']
            self.evolution_state['best_fitness'] = best_individual['fitness']
            self.evolution_state['last_improvement'] = datetime.now()
        
        # 元学习知识巩固
        learning_experience = {
            'performance': performance_metrics,
            'genes': best_individual['genes'],
            'timestamp': datetime.now(),
            'confidence': performance_metrics.get('overall_performance', 0.5)
        }
        self.meta_learner.consolidate_knowledge(learning_experience)
    
    def _apply_gene_configuration(self, genes):
        """应用基因配置"""
        # 更新结构分析参数
        self.adaptive_params['structural_analysis']['crack_sensitivity'] = genes['quantum_sensitivity']
        self.adaptive_params['structural_analysis']['deformation_threshold'] = genes['topological_complexity']
        self.adaptive_params['structural_analysis']['corrosion_sensitivity'] = genes['causal_depth']
        
        # 更新拓扑参数
        self.adaptive_params['topological_analysis']['complexity_weight'] = genes['topological_complexity']
        
        # 更新因果参数
        self.adaptive_params['causal_inference']['causal_depth'] = int(genes['causal_depth'] * 5)
        
        # 更新融合策略
        self.adaptive_params['fusion_strategy']['method'] = genes['fusion_strategy']
        self.adaptive_params['fusion_strategy']['dynamic_threshold'] = genes['adaptation_rate']
    
    def _consolidate_knowledge(self, detection_results, performance_metrics):
        """知识巩固"""
        # 创建知识经验
        knowledge_experience = {
            'detection_pattern': {
                'structural_damage': detection_results['structural_analysis']['overall_damage']['score'],
                'topological_entropy': detection_results['topological_analysis']['fused_entropy'],
                'causal_effect': detection_results['causal_analysis']['causal_effects']['normalized_effect'],
                'final_confidence': detection_results['final_detection']['final_confidence']
            },
            'performance': performance_metrics,
            'adaptive_params': self.adaptive_params.copy(),
            'timestamp': datetime.now(),
            'generalizability': performance_metrics['evidence_consistency'],
            'robustness': performance_metrics['computational_efficiency'],
            'novelty': performance_metrics['innovation']
        }
        
        # 巩固知识
        knowledge_size = self.meta_learner.consolidate_knowledge(knowledge_experience)
        self.evolution_state['knowledge_base_size'] = knowledge_size
    
    def _update_evolution_state(self, performance_metrics):
        """更新进化状态"""
        self.evolution_state['generation'] += 1
        self.evolution_state['adaptation_level'] = performance_metrics['overall_performance']
        
        # 记录性能历史
        self.performance_history.append({
            'generation': self.evolution_state['generation'],
            'performance': performance_metrics['overall_performance'],
            'timestamp': datetime.now()
        })
        
        # 限制历史记录长度
        if len(self.performance_history) > 100:
            self.performance_history = self.performance_history[-100:]
    
    def get_evolution_report(self):
        """获取进化报告"""
        report = {
            'current_generation': self.evolution_state['generation'],
            'best_fitness': self.evolution_state['best_fitness'],
            'adaptation_level': self.evolution_state['adaptation_level'],
            'knowledge_base_size': self.evolution_state['knowledge_base_size'],
            'performance_trend': self._calculate_performance_trend(),
            'evolutionary_maturity': self._calculate_evolutionary_maturity(),
            'recommendations': self._generate_evolution_recommendations()
        }
        
        return report
    
    def _calculate_performance_trend(self):
        """计算性能趋势"""
        if len(self.performance_history) < 2:
            return "稳定"
        
        recent_performance = [p['performance'] for p in self.performance_history[-5:]]
        if len(recent_performance) < 2:
            return "稳定"
        
        # 计算斜率
        x = np.arange(len(recent_performance))
        slope = np.polyfit(x, recent_performance, 1)[0]
        
        if slope > 0.01:
            return "上升"
        elif slope < -0.01:
            return "下降"
        else:
            return "稳定"
    
    def _calculate_evolutionary_maturity(self):
        """计算进化成熟度"""
        maturity_score = min(1.0, self.evolution_state['generation'] / 50.0)
        maturity_score += self.evolution_state['knowledge_base_size'] / 1000.0
        maturity_score += self.evolution_state['best_fitness'] * 0.3
        
        return min(1.0, maturity_score)
    
    def _generate_evolution_recommendations(self):
        """生成进化建议"""
        recommendations = []
        
        # 基于当前状态的建议
        if self.evolution_state['generation'] < 10:
            recommendations.append("系统处于早期进化阶段，建议增加探索性突变")
        
        if self.evolution_state['best_fitness'] < 0.7:
            recommendations.append("检测性能有待提升，建议调整融合策略权重")
        
        if self.evolution_state['knowledge_base_size'] < 50:
            recommendations.append("知识库规模较小，建议在更多场景中运行以积累经验")
        
        if len(recommendations) == 0:
            recommendations.append("系统运行良好，继续保持当前进化策略")
        
        return recommendations

    def _calculate_texture_anomaly(self, image):
        """计算纹理异常"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # 使用局部二值模式(LBP)计算纹理特征
        lbp = self._compute_lbp(gray)
        
        # 计算纹理均匀性（异常区域通常纹理不均匀）
        texture_uniformity = np.std(lbp) / (np.mean(lbp) + 1e-8)
        
        # 使用Gabor滤波器检测纹理异常
        gabor_response = self._compute_gabor_features(gray)
        gabor_anomaly = np.std(gabor_response) / (np.mean(gabor_response) + 1e-8)
        
        # 结合多种纹理特征
        texture_anomaly = (texture_uniformity + gabor_anomaly) / 2
        
        return min(1.0, texture_anomaly)

    def _compute_lbp(self, image, radius=3, points=24):
        """计算局部二值模式"""
        height, width = image.shape
        lbp_image = np.zeros_like(image, dtype=np.float32)
        
        for i in range(radius, height - radius):
            for j in range(radius, width - radius):
                center = image[i, j]
                binary_pattern = 0
                for p in range(points):
                    # 计算圆形邻域坐标
                    theta = 2 * np.pi * p / points
                    x = i + radius * np.cos(theta)
                    y = j + radius * np.sin(theta)
                    
                    # 双线性插值
                    x1, y1 = int(np.floor(x)), int(np.floor(y))
                    x2, y2 = int(np.ceil(x)), int(np.ceil(y))
                    
                    if x1 < 0 or x2 >= height or y1 < 0 or y2 >= width:
                        continue
                    
                    # 插值计算邻域像素值
                    dx, dy = x - x1, y - y1
                    neighbor_value = (1 - dx) * (1 - dy) * image[x1, y1] + \
                                dx * (1 - dy) * image[x2, y1] + \
                                (1 - dx) * dy * image[x1, y2] + \
                                dx * dy * image[x2, y2]
                    
                    # 构建LBP模式
                    if neighbor_value > center:
                        binary_pattern |= (1 << p)
                
                lbp_image[i, j] = binary_pattern
        
        return lbp_image

    def _compute_gabor_features(self, image):
        """计算Gabor滤波器特征"""
        gabor_kernels = []
        
        # 创建多个Gabor滤波器
        for theta in np.arange(0, np.pi, np.pi / 4):
            for sigma in [1, 3]:
                for frequency in [0.1, 0.3, 0.5]:
                    kernel = cv2.getGaborKernel((21, 21), sigma, theta, frequency, 0.5, 0, ktype=cv2.CV_32F)
                    gabor_kernels.append(kernel)
        
        # 应用Gabor滤波器
        gabor_responses = []
        for kernel in gabor_kernels:
            filtered = cv2.filter2D(image, cv2.CV_32F, kernel)
            gabor_responses.append(np.mean(np.abs(filtered)))
        
        return np.array(gabor_responses)

    def _calculate_color_consistency(self, image):
        """计算颜色一致性"""
        # 转换到HSV颜色空间
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        # 计算颜色通道的统计特征
        h_mean, h_std = np.mean(hsv[:, :, 0]), np.std(hsv[:, :, 0])
        s_mean, s_std = np.mean(hsv[:, :, 1]), np.std(hsv[:, :, 1])
        v_mean, v_std = np.mean(hsv[:, :, 2]), np.std(hsv[:, :, 2])
        
        # 颜色一致性得分（标准差越小，一致性越高）
        color_consistency = 1.0 / (1.0 + (h_std + s_std + v_std) / 3.0)
        
        # 检测颜色异常区域
        color_anomalies = self._detect_color_anomalies(hsv)
        
        # 结合一致性得分和异常检测
        final_score = color_consistency * (1.0 - color_anomalies)
        
        return max(0.0, min(1.0, final_score))

    def _detect_color_anomalies(self, hsv_image):
        """检测颜色异常"""
        # 定义正常颜色范围（可根据具体场景调整）
        normal_h_ranges = [(0, 30), (150, 180)]  # 红色和部分蓝色
        normal_s_range = (50, 255)  # 饱和度适中到高
        normal_v_range = (50, 255)  # 亮度适中到高
        
        anomaly_mask = np.ones(hsv_image.shape[:2], dtype=np.float32)
        
        h, s, v = hsv_image[:, :, 0], hsv_image[:, :, 1], hsv_image[:, :, 2]
        
        # 创建正常颜色掩码
        normal_mask = np.zeros_like(h, dtype=bool)
        for h_range in normal_h_ranges:
            normal_mask |= ((h >= h_range[0]) & (h <= h_range[1]))
        
        normal_mask &= ((s >= normal_s_range[0]) & (s <= normal_s_range[1]))
        normal_mask &= ((v >= normal_v_range[0]) & (v <= normal_v_range[1]))
        
        # 异常区域为不正常颜色的区域
        anomaly_mask[normal_mask] = 0
        
        # 计算异常比例
        anomaly_ratio = np.sum(anomaly_mask) / (anomaly_mask.size + 1e-8)
        
        return anomaly_ratio

    def _calculate_temporal_evolution(self):
        """计算时间演化"""
        # 如果有历史检测数据，计算时间变化
        if hasattr(self, 'previous_detection') and self.previous_detection is not None:
            current_confidence = getattr(self, 'current_confidence', 0.5)
            previous_confidence = self.previous_detection.get('final_confidence', 0.5)
            
            # 计算置信度变化
            confidence_change = abs(current_confidence - previous_confidence)
            
            # 时间演化得分（变化越大，演化越明显）
            temporal_evolution = min(1.0, confidence_change * 2)
            
            return temporal_evolution
        else:
            return 0.5  # 默认值

    # 新增的真实桥梁分析接口
    def analyze_real_bridge(self, image_path, bridge_type="concrete", feedback_data=None):
        """分析真实桥梁图像
        
        Args:
            image_path: 桥梁图像路径
            bridge_type: 桥梁类型 ("concrete", "steel", "composite")
            feedback_data: 反馈数据用于进化学习
        """
        print(f"🏗️ 开始分析{bridge_type}桥梁: {image_path}")
        
        # 根据桥梁类型调整参数
        self._adjust_parameters_for_bridge_type(bridge_type)
        
        # 执行检测
        results = self.detect_with_evolution(image_path, feedback_data)
        
        # 生成桥梁专用报告
        bridge_report = self._generate_bridge_report(results, bridge_type)
        
        return {
            'detection_results': results['detection_results'],
            'performance_metrics': results['performance_metrics'],
            'bridge_report': bridge_report,
            'evolution_state': results['evolution_state']
        }
    
    def _adjust_parameters_for_bridge_type(self, bridge_type):
        """根据桥梁类型调整参数"""
        if bridge_type == "concrete":
            # 混凝土桥梁：关注裂缝和渗漏
            self.adaptive_params['structural_analysis']['crack_sensitivity'] = 0.8
            self.adaptive_params['structural_analysis']['leakage_detection_level'] = 0.9
        elif bridge_type == "steel":
            # 钢桥：关注腐蚀和变形
            self.adaptive_params['structural_analysis']['corrosion_sensitivity'] = 0.9
            self.adaptive_params['structural_analysis']['deformation_threshold'] = 0.8
        elif bridge_type == "composite":
            # 复合桥梁：平衡关注所有类型
            self.adaptive_params['structural_analysis']['crack_sensitivity'] = 0.7
            self.adaptive_params['structural_analysis']['corrosion_sensitivity'] = 0.7
            self.adaptive_params['structural_analysis']['deformation_threshold'] = 0.7
    
    def _generate_bridge_report(self, results, bridge_type):
        """生成桥梁专用报告"""
        structural = results['detection_results']['structural_analysis']
        final_detection = results['detection_results']['final_detection']
        
        report = {
            'bridge_type': bridge_type,
            'overall_condition': final_detection['anomaly_level'],
            'confidence_score': final_detection['final_confidence'],
            'damage_breakdown': {
                'cracks': {
                    'score': structural['cracks']['score'],
                    'level': self._classify_damage_level(structural['cracks']['score']),
                    'density': structural['cracks']['density']
                },
                'deformation': {
                    'score': structural['deformation']['score'],
                    'level': self._classify_damage_level(structural['deformation']['score']),
                    'irregularity': structural['deformation']['irregularity']
                },
                'corrosion': {
                    'score': structural['corrosion']['score'],
                    'level': self._classify_damage_level(structural['corrosion']['score']),
                    'rust_ratio': structural['corrosion']['rust_ratio']
                },
                'leakage': {
                    'score': structural['leakage']['score'],
                    'level': self._classify_damage_level(structural['leakage']['score']),
                    'leakage_ratio': structural['leakage']['leakage_ratio']
                }
            },
            'maintenance_recommendations': self._generate_maintenance_recommendations(structural),
            'inspection_frequency': self._recommend_inspection_frequency(final_detection['final_confidence']),
            'risk_assessment': self._assess_risk_level(final_detection['final_confidence'])
        }
        
        return report
    
    def _classify_damage_level(self, score):
        """分类损伤级别"""
        if score < 0.2:
            return "无"
        elif score < 0.4:
            return "轻微"
        elif score < 0.6:
            return "中度"
        elif score < 0.8:
            return "严重"
        else:
            return "危险"
    
    def _generate_maintenance_recommendations(self, structural_analysis):
        """生成维护建议"""
        recommendations = []
        
        if structural_analysis['cracks']['score'] > 0.6:
            recommendations.append("建议进行裂缝修补和结构加固")
        
        if structural_analysis['deformation']['score'] > 0.5:
            recommendations.append("建议进行结构变形监测和校正")
        
        if structural_analysis['corrosion']['score'] > 0.4:
            recommendations.append("建议进行防腐处理和表面修复")
        
        if structural_analysis['leakage']['score'] > 0.3:
            recommendations.append("建议进行防水处理和排水系统检查")
        
        if structural_analysis['overall_damage']['score'] < 0.3:
            recommendations.append("结构状况良好，建议常规维护")
        
        return recommendations if recommendations else ["结构状况良好，保持常规检查"]
    
    def _recommend_inspection_frequency(self, confidence):
        """推荐检查频率"""
        if confidence < 0.3:
            return "12个月"
        elif confidence < 0.5:
            return "6个月"
        elif confidence < 0.7:
            return "3个月"
        else:
            return "立即检查"
    
    def _assess_risk_level(self, confidence):
        """评估风险等级"""
        if confidence < 0.3:
            return {"level": "低风险", "color": "green"}
        elif confidence < 0.5:
            return {"level": "中风险", "color": "yellow"}
        elif confidence < 0.7:
            return {"level": "高风险", "color": "orange"}
        else:
            return {"level": "极高风险", "color": "red"}
    
    def batch_analyze_bridges(self, image_folder, output_report_path="bridge_analysis_report.json"):
        """批量分析桥梁图像"""
        print(f"📁 开始批量分析桥梁图像文件夹: {image_folder}")
        
        bridge_reports = {}
        
        # 支持常见图像格式
        image_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff']
        
        for filename in os.listdir(image_folder):
            if any(filename.lower().endswith(ext) for ext in image_extensions):
                image_path = os.path.join(image_folder, filename)
                
                try:
                    # 尝试自动识别桥梁类型
                    bridge_type = self._auto_detect_bridge_type(image_path)
                    
                    # 分析桥梁
                    result = self.analyze_real_bridge(image_path, bridge_type)
                    
                    bridge_reports[filename] = {
                        'bridge_type': bridge_type,
                        'analysis_result': result['bridge_report'],
                        'timestamp': datetime.now().isoformat()
                    }
                    
                    print(f"✅ 已完成分析: {filename}")
                    
                except Exception as e:
                    print(f"❌ 分析失败 {filename}: {str(e)}")
                    bridge_reports[filename] = {
                        'error': str(e),
                        'timestamp': datetime.now().isoformat()
                    }
        
        # 保存报告
        with open(output_report_path, 'w', encoding='utf-8') as f:
            json.dump(bridge_reports, f, ensure_ascii=False, indent=2)
        
        print(f"📊 批量分析完成，报告已保存至: {output_report_path}")
        return bridge_reports
    
    def _auto_detect_bridge_type(self, image_path):
        """自动检测桥梁类型"""
        image = cv2.imread(image_path)
        if image is None:
            return "unknown"
        
        # 基于颜色和纹理特征进行简单分类
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        # 检测混凝土特征（灰色调）
        gray_mask = cv2.inRange(hsv, np.array([0, 0, 50]), np.array([180, 50, 200]))
        gray_ratio = np.sum(gray_mask > 0) / (image.shape[0] * image.shape[1])
        
        # 检测钢铁特征（金属色、锈色）
        metal_mask1 = cv2.inRange(hsv, np.array([0, 0, 150]), np.array([180, 50, 255]))
        metal_mask2 = cv2.inRange(hsv, np.array([0, 50, 50]), np.array([30, 255, 255]))
        metal_ratio = np.sum(cv2.bitwise_or(metal_mask1, metal_mask2) > 0) / (image.shape[0] * image.shape[1])
        
        if gray_ratio > 0.4:
            return "concrete"
        elif metal_ratio > 0.3:
            return "steel"
        else:
            return "composite"

# 高级可视化类
class EvolutionaryVisualization:
    """进化可视化"""
    
    @staticmethod
    def create_evolution_dashboard(detector, results, output_path='evolution_dashboard.png'):
        """创建进化仪表盘"""
        fig, axes = plt.subplots(2, 3, figsize=(18, 12))
        
        # 1. 检测结果可视化
        original_image = results['detection_results'].get('original_image', 
                                                         np.zeros((300, 400, 3), dtype=np.uint8))
        axes[0, 0].imshow(cv2.cvtColor(original_image, cv2.COLOR_BGR2RGB))
        axes[0, 0].set_title('检测图像')
        axes[0, 0].axis('off')
        
        # 2. 结构损伤可视化
        structural = results['detection_results']['structural_analysis']
        damage_types = ['裂缝', '变形', '腐蚀', '渗漏']
        damage_scores = [
            structural['cracks']['score'],
            structural['deformation']['score'],
            structural['corrosion']['score'],
            structural['leakage']['score']
        ]
        
        bars = axes[0, 1].bar(damage_types, damage_scores, color=['red', 'orange', 'brown', 'blue'])
        axes[0, 1].set_title('结构损伤分析')
        axes[0, 1].set_ylabel('损伤程度')
        axes[0, 1].set_ylim(0, 1)
        
        # 添加数值标签
        for bar, score in zip(bars, damage_scores):
            axes[0, 1].text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.02, 
                           f'{score:.2f}', ha='center', va='bottom')
        
        # 3. 性能指标雷达图
        performance_metrics = results['performance_metrics']
        metrics = ['准确性', '一致性', '效率', '创新性']
        values = [
            performance_metrics.get('accuracy', 0.5),
            performance_metrics.get('evidence_consistency', 0.5),
            performance_metrics.get('computational_efficiency', 0.5),
            performance_metrics.get('innovation', 0.5)
        ]
        
        # 完成雷达图
        angles = np.linspace(0, 2*np.pi, len(metrics), endpoint=False).tolist()
        values += values[:1]  # 完成循环
        angles += angles[:1]
        
        axes[0, 2].plot(angles, values, 'o-', linewidth=2)
        axes[0, 2].fill(angles, values, alpha=0.25)
        axes[0, 2].set_xticks(angles[:-1])
        axes[0, 2].set_xticklabels(metrics)
        axes[0, 2].set_ylim(0, 1)
        axes[0, 2].set_title('性能指标雷达图')
        
        # 4. 进化历史
        if detector.performance_history:
            generations = [p['generation'] for p in detector.performance_history]
            performances = [p['performance'] for p in detector.performance_history]
            
            axes[1, 0].plot(generations, performances, 'b-', alpha=0.7)
            axes[1, 0].set_xlabel('进化代数')
            axes[1, 0].set_ylabel('性能分数')
            axes[1, 0].set_title('进化性能历史')
            axes[1, 0].grid(True, alpha=0.3)
        
        # 5. 证据贡献度
        final_detection = results['detection_results']['final_detection']
        contributions = [
            final_detection['structural_contribution'],
            final_detection['topological_contribution'], 
            final_detection['causal_contribution'],
            final_detection['contextual_contribution']
        ]
        labels = ['结构', '拓扑', '因果', '上下文']
        
        bars2 = axes[1, 1].bar(labels, contributions, color=['red', 'blue', 'green', 'orange'])
        axes[1, 1].set_title('证据贡献度')
        axes[1, 1].set_ylabel('贡献度')
        
        # 添加数值标签
        for bar, contrib in zip(bars2, contributions):
            axes[1, 1].text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.02, 
                           f'{contrib:.2f}', ha='center', va='bottom')
        
        # 6. 进化状态
        evolution_state = results['evolution_state']
        state_metrics = ['进化代数', '最佳适应度', '适应水平', '知识库大小']
        state_values = [
            evolution_state['generation'] / 100.0,
            evolution_state['best_fitness'],
            evolution_state['adaptation_level'],
            min(1.0, evolution_state['knowledge_base_size'] / 100.0)
        ]
        
        bars3 = axes[1, 2].bar(state_metrics, state_values, color=['purple', 'cyan', 'yellow', 'pink'])
        axes[1, 2].set_title('进化状态')
        axes[1, 2].tick_params(axis='x', rotation=45)
        
        # 添加数值标签
        for bar, value in zip(bars3, state_values):
            axes[1, 2].text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.02, 
                           f'{value:.2f}', ha='center', va='bottom')
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.show()

    @staticmethod
    def create_bridge_report_visualization(bridge_report, output_path='bridge_report.png'):
        """创建桥梁报告可视化"""
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        
        # 1. 总体状况
        overall_condition = bridge_report['overall_condition']
        confidence = bridge_report['confidence_score']
        
        # 使用颜色编码的风险等级
        risk_colors = {
            "结构完好": "green",
            "轻微损伤": "lightgreen", 
            "中度损伤": "yellow",
            "严重损伤": "orange",
            "危险状态": "red"
        }
        
        color = risk_colors.get(overall_condition, "gray")
        
        axes[0, 0].pie([confidence, 1-confidence], labels=[f'置信度: {confidence:.2f}', ''], 
                      colors=[color, 'lightgray'], autopct='%1.1f%%')
        axes[0, 0].set_title(f'总体状况: {overall_condition}')
        
        # 2. 损伤分解
        damage_breakdown = bridge_report['damage_breakdown']
        damage_types = list(damage_breakdown.keys())
        damage_scores = [damage_breakdown[dt]['score'] for dt in damage_types]
        damage_levels = [damage_breakdown[dt]['level'] for dt in damage_types]
        
        bars = axes[0, 1].bar(damage_types, damage_scores, 
                             color=['red', 'orange', 'brown', 'blue'])
        axes[0, 1].set_title('损伤类型分解')
        axes[0, 1].set_ylabel('损伤程度')
        axes[0, 1].set_ylim(0, 1)
        axes[0, 1].tick_params(axis='x', rotation=45)
        
        # 添加数值和级别标签
        for bar, score, level in zip(bars, damage_scores, damage_levels):
            axes[0, 1].text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.02, 
                           f'{score:.2f}\n({level})', ha='center', va='bottom', fontsize=9)
        
        # 3. 维护建议
        recommendations = bridge_report['maintenance_recommendations']
        axes[1, 0].axis('off')
        axes[1, 0].set_title('维护建议')
        
        recommendation_text = "\n".join([f"• {rec}" for rec in recommendations])
        axes[1, 0].text(0.05, 0.95, recommendation_text, transform=axes[1, 0].transAxes,
                       fontsize=11, verticalalignment='top', linespacing=1.5)
        
        # 4. 检查计划
        inspection_freq = bridge_report['inspection_frequency']
        risk_assessment = bridge_report['risk_assessment']
        
        risk_info = f"风险等级: {risk_assessment['level']}\n建议检查频率: {inspection_freq}"
        axes[1, 1].text(0.5, 0.5, risk_info, transform=axes[1, 1].transAxes,
                       fontsize=14, ha='center', va='center', 
                       bbox=dict(boxstyle="round,pad=0.3", facecolor=risk_assessment['color'], alpha=0.3))
        axes[1, 1].set_title('风险评估与检查计划')
        axes[1, 1].axis('off')
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.show()

# 演示函数
def demonstrate_real_bridge_analysis():
    """演示真实桥梁分析"""
    print("🏗️ 启动真实桥梁分析系统...")
    
    # 初始化自进化检测器
    detector = SelfEvolvingTunnelDetector()
    
    # 创建模拟真实桥梁图像
    test_bridge_images = []
    for i in range(2):  # 创建2个测试桥梁图像
        bridge_image = create_realistic_bridge_image(i)
        filename = f'real_bridge_test_{i}.jpg'
        cv2.imwrite(filename, bridge_image)
        test_bridge_images.append(filename)
    
    # 分析每个桥梁
    for i, image_path in enumerate(test_bridge_images):
        print(f"\n=== 分析第{i+1}座桥梁 ===")
        
        # 自动检测桥梁类型并分析
        bridge_type = detector._auto_detect_bridge_type(image_path)
        print(f"检测到的桥梁类型: {bridge_type}")
        
        # 模拟反馈数据
        feedback_data = {
            'ground_truth': 0.6 + i * 0.1,
            'user_feedback': 'accurate' if i > 0 else 'moderate'
        }
        
        # 执行桥梁分析
        results = detector.analyze_real_bridge(image_path, bridge_type, feedback_data)
        
        # 显示结果
        bridge_report = results['bridge_report']
        print(f"桥梁总体状况: {bridge_report['overall_condition']}")
        print(f"检测置信度: {bridge_report['confidence_score']:.4f}")
        print(f"建议检查频率: {bridge_report['inspection_frequency']}")
        print(f"风险等级: {bridge_report['risk_assessment']['level']}")
        
        # 显示损伤详情
        print("损伤详情:")
        for damage_type, info in bridge_report['damage_breakdown'].items():
            print(f"  {damage_type}: {info['level']} (分数: {info['score']:.3f})")
        
        # 显示维护建议
        print("维护建议:")
        for rec in bridge_report['maintenance_recommendations']:
            print(f"  • {rec}")
        
        # 创建可视化报告
        EvolutionaryVisualization.create_bridge_report_visualization(bridge_report, 
                                                                   f'bridge_report_{i}.png')
    
    # 生成进化报告
    evolution_report = detector.get_evolution_report()
    print(f"\n📊 系统进化报告:")
    print(f"  当前代数: {evolution_report['current_generation']}")
    print(f"  最佳适应度: {evolution_report['best_fitness']:.4f}")
    print(f"  性能趋势: {evolution_report['performance_trend']}")
    print(f"  进化成熟度: {evolution_report['evolutionary_maturity']:.4f}")
    
    return detector, results

def create_realistic_bridge_image(iteration):
    """创建真实桥梁测试图像"""
    width, height = 800, 600
    image = np.ones((height, width, 3), dtype=np.uint8) * 180  # 灰色背景
    
    # 桥梁主体结构
    cv2.rectangle(image, (100, 200), (700, 400), (120, 120, 120), -1)  # 桥面
    
    # 根据迭代次数增加损伤
    damage_level = 0.3 + iteration * 0.3
    
    # 添加裂缝
    if damage_level > 0.3:
        for i in range(int(3 * damage_level)):
            start_x = np.random.randint(150, 650)
            start_y = np.random.randint(220, 380)
            length = np.random.randint(20, 80)
            angle = np.random.uniform(0, np.pi)
            end_x = int(start_x + length * np.cos(angle))
            end_y = int(start_y + length * np.sin(angle))
            cv2.line(image, (start_x, start_y), (end_x, end_y), (0, 0, 0), 2)
    
    # 添加腐蚀区域
    if damage_level > 0.4:
        for i in range(int(5 * damage_level)):
            center_x = np.random.randint(120, 680)
            center_y = np.random.randint(210, 390)
            radius = np.random.randint(5, 15)
            # 锈蚀颜色
            color = (np.random.randint(100, 150), np.random.randint(50, 100), np.random.randint(0, 50))
            cv2.circle(image, (center_x, center_y), radius, color, -1)
    
    # 添加变形区域
    if damage_level > 0.5:
        deformation_center = (400, 300)
        axes = (int(80 * damage_level), int(40 * damage_level))
        cv2.ellipse(image, deformation_center, axes, 45, 0, 360, (100, 100, 150), 2)
    
    # 添加渗漏痕迹
    if damage_level > 0.6:
        for i in range(int(3 * damage_level)):
            start_x = np.random.randint(150, 650)
            start_y = np.random.randint(350, 400)
            length = np.random.randint(30, 100)
            # 水渍颜色
            color = (200 - i*10, 200 - i*10, 255)
            cv2.line(image, (start_x, start_y), (start_x, start_y + length), color, 3)
    
    # 添加噪声模拟真实环境
    noise = np.random.normal(0, 10, image.shape).astype(np.uint8)
    image = cv2.add(image, noise)
    
    return image

# 使用示例
if __name__ == "__main__":
    # 演示真实桥梁分析
    detector, results = demonstrate_real_bridge_analysis()
    
    print("\n🎯 真实桥梁分析系统特性总结:")
    print("  • 多损伤类型检测 - 裂缝、变形、腐蚀、渗漏")
    print("  • 桥梁类型自适应 - 混凝土、钢桥、复合桥梁")  
    print("  • 智能维护建议 - 基于损伤程度的个性化建议")
    print("  • 风险评估系统 - 多维度安全评估")
    print("  • 批量处理能力 - 支持多图像自动分析")
    print("  • 进化学习 - 持续优化检测精度")
    
    # 演示批量分析（如果有图像文件夹）
    # detector.batch_analyze_bridges("bridge_images/", "batch_analysis_report.json")