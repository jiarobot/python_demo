import cv2
import numpy as np
import torch
from ultralytics import YOLO
import matplotlib.pyplot as plt
from scipy import ndimage
from sklearn.cluster import DBSCAN
import pywt
from numba import jit
import warnings
warnings.filterwarnings('ignore')

class PhysicsGuidedYOLO:
    """物理引导的零样本YOLO检测器"""
    
    def __init__(self, model_name='yolov8n.pt'):
        # 加载预训练YOLO模型（不进行微调）
        self.model = YOLO(model_name)
        
        # 物理约束参数
        self.physical_constraints = {
            'tunnel_geometry': self._define_tunnel_geometry(),
            'material_properties': self._define_material_properties(),
            'fluid_dynamics': self._define_fluid_dynamics()
        }
        
        # 零样本检测映射
        self.zero_shot_mapping = self._create_zero_shot_mapping()
    
    def _define_tunnel_geometry(self):
        """定义隧道几何约束"""
        return {
            'expected_aspect_ratios': [2.5, 3.0, 4.0],  # 隧道典型宽高比
            'curvature_limits': [0.1, 0.5],  # 曲率限制
            'perspective_angles': [15, 30, 45]  # 视角角度
        }
    
    def _define_material_properties(self):
        """定义材料物理属性"""
        return {
            'concrete_reflectance': [0.3, 0.6],
            'water_absorption': [0.7, 0.9],
            'metal_specularity': [0.8, 1.0]
        }
    
    def _define_fluid_dynamics(self):
        """定义流体动力学参数"""
        return {
            'flow_velocity_range': [0.01, 1.0],  # m/s
            'viscosity_coefficient': 0.001,
            'surface_tension': 0.072
        }
    
    def _create_zero_shot_mapping(self):
        """创建零样本类别映射"""
        # 将通用YOLO类别映射到隧道特定概念
        mapping = {
            # 结构相关
            'person': 'maintenance_access',
            'backpack': 'equipment_cluster', 
            'handbag': 'small_equipment',
            'suitcase': 'maintenance_gear',
            
            # 液体相关
            'bottle': 'potential_container',
            'cup': 'liquid_holder',
            'bowl': 'containment_vessel',
            
            # 表面异常
            'tv': 'flat_surface_anomaly',
            'laptop': 'planar_defect',
            'cell phone': 'small_surface_issue',
            
            # 线状特征
            'kite': 'suspension_element',
            'fork': 'crack_like_pattern',
            'spoon': 'curved_anomaly'
        }
        return mapping
    
    def physical_feature_extraction(self, image):
        """基于物理原理的特征提取"""
        features = {}
        
        # 1. 结构光模拟分析
        features['structural_analysis'] = self._simulate_structured_light(image)
        
        # 2. 材料反射特性分析
        features['material_reflectance'] = self._analyze_material_reflectance(image)
        
        # 3. 流体痕迹检测
        features['fluid_traces'] = self._detect_fluid_traces(image)
        
        # 4. 应力分布模拟
        features['stress_distribution'] = self._simulate_stress_distribution(image)
        
        return features
    
    def _simulate_structured_light(self, image):
        """模拟结构光投影分析表面形貌"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # 生成模拟结构光模式
        height, width = gray.shape
        x, y = np.meshgrid(np.linspace(0, 2*np.pi, width), 
                          np.linspace(0, 2*np.pi, height))
        
        structured_light = np.sin(5*x) * np.sin(5*y)
        
        # 分析形变模式
        deformation = cv2.filter2D(gray, -1, structured_light)
        
        return {
            'surface_roughness': np.std(deformation),
            'depth_variation': np.ptp(deformation),
            'pattern_distortion': np.mean(np.abs(deformation - gray))
        }
    
    def _analyze_material_reflectance(self, image):
        """分析材料反射特性"""
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l_channel, a_channel, b_channel = cv2.split(lab)
        
        # 计算反射率特征
        reflectance_features = {
            'specular_intensity': np.percentile(l_channel, 95),
            'diffuse_reflectance': np.median(l_channel),
            'color_consistency': np.std(a_channel) + np.std(b_channel),
            'absorption_coefficient': 1.0 - (np.mean(l_channel) / 255.0)
        }
        
        return reflectance_features
    
    def _detect_fluid_traces(self, image):
        """基于流体动力学的痕迹检测"""
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        # 湿度相关特征
        saturation = hsv[:, :, 1].astype(np.float32)
        value = hsv[:, :, 2].astype(np.float32)
        
        # 计算流体流动模式
        flow_pattern = self._calculate_flow_pattern(saturation, value)
        
        return {
            'moisture_likelihood': np.mean(flow_pattern),
            'flow_direction_consistency': np.std(flow_pattern),
            'capillary_effect': self._detect_capillary_effects(image)
        }
    @staticmethod
    @jit(nopython=True)
    def _calculate_flow_pattern(saturation, value):
        """计算流体流动模式"""
        height, width = saturation.shape
        flow_pattern = np.zeros((height, width))
        
        for i in range(1, height-1):
            for j in range(1, width-1):
                # 基于梯度的流动方向估计
                grad_s = np.sqrt(
                    (saturation[i+1, j] - saturation[i-1, j])**2 +
                    (saturation[i, j+1] - saturation[i, j-1])**2
                )
                grad_v = np.sqrt(
                    (value[i+1, j] - value[i-1, j])**2 +
                    (value[i, j+1] - value[i, j-1])**2
                )
                flow_pattern[i, j] = (grad_s + grad_v) / 2.0
        
        return flow_pattern / np.max(flow_pattern)
    
    def _detect_capillary_effects(self, image):
        """检测毛细管效应特征"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # 使用小波变换分析多尺度特征
        coeffs = pywt.wavedec2(gray, 'db4', level=3)
        
        # 分析高频分量中的毛细特征
        capillary_features = []
        for i, (cH, cV, cD) in enumerate(coeffs[1:]):
            # 垂直和水平方向的细节
            vertical_detail = np.mean(np.abs(cV))
            horizontal_detail = np.mean(np.abs(cH))
            diagonal_detail = np.mean(np.abs(cD))
            
            capillary_features.append(
                (vertical_detail + horizontal_detail) / (diagonal_detail + 1e-6)
            )
        
        return np.mean(capillary_features)
    
    def _simulate_stress_distribution(self, image):
        """模拟应力分布"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # 计算Hessian矩阵特征值分析应力集中
        sobel_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=5)
        sobel_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=5)
        
        sobel_xx = cv2.Sobel(sobel_x, cv2.CV_64F, 1, 0, ksize=5)
        sobel_yy = cv2.Sobel(sobel_y, cv2.CV_64F, 0, 1, ksize=5)
        sobel_xy = cv2.Sobel(sobel_x, cv2.CV_64F, 0, 1, ksize=5)
        
        # 计算主应力
        stress_tensor = np.stack([sobel_xx, sobel_xy, sobel_xy, sobel_yy], axis=-1)
        stress_tensor = stress_tensor.reshape(stress_tensor.shape[0], stress_tensor.shape[1], 2, 2)
        
        eigenvalues = np.linalg.eigvals(stress_tensor)
        principal_stress = np.max(np.abs(eigenvalues), axis=2)
        
        return {
            'max_stress': np.max(principal_stress),
            'stress_concentration': np.mean(principal_stress > np.percentile(principal_stress, 90)),
            'stress_gradient': np.std(principal_stress)
        }

class ZeroShotTunnelDetector:
    """零样本隧道检测器"""
    
    def __init__(self):
        self.physics_yolo = PhysicsGuidedYOLO()
        self.quantum_clustering = QuantumInspiredClustering()
        self.bio_mimetic_analysis = BioMimeticAnalyzer()
    
    def detect_tunnel_anomalies(self, image_path):
        """检测隧道异常"""
        # 读取图像
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"无法读取图像: {image_path}")
        
        print("步骤1: 物理特征提取...")
        physical_features = self.physics_yolo.physical_feature_extraction(image)
        
        print("步骤2: YOLO零样本检测...")
        yolo_results = self.physics_yolo.model(image)
        
        print("步骤3: 量子聚类分析...")
        cluster_analysis = self.quantum_clustering.analyze_image_regions(
            image, yolo_results
        )
        
        print("步骤4: 仿生模式识别...")
        bio_analysis = self.bio_mimetic_analysis.analyze_biological_patterns(
            image, physical_features
        )
        
        print("步骤5: 多模态融合检测...")
        final_detection = self._multimodal_fusion(
            physical_features, yolo_results, cluster_analysis, bio_analysis
        )
        
        return {
            'original_image': image,
            'physical_features': physical_features,
            'yolo_detections': yolo_results,
            'cluster_analysis': cluster_analysis,
            'bio_analysis': bio_analysis,
            'final_detection': final_detection
        }
    
    def _multimodal_fusion(self, physical_features, yolo_results, 
                          cluster_analysis, bio_analysis):
        """多模态信息融合"""
        # 1. 物理约束验证
        physical_constraints = self._apply_physical_constraints(
            physical_features, yolo_results
        )
        
        # 2. 时空一致性分析
        temporal_consistency = self._analyze_temporal_consistency(
            yolo_results, cluster_analysis
        )
        
        # 3. 生物启发验证
        biological_verification = self._biological_verification(
            bio_analysis, physical_features
        )
        
        # 4. 生成最终检测结果
        fusion_result = {
            'leakage_probability': self._calculate_leakage_probability(
                physical_constraints, temporal_consistency, biological_verification
            ),
            'structural_risk': self._assess_structural_risk(
                physical_features, cluster_analysis
            ),
            'maintenance_urgency': self._calculate_maintenance_urgency(
                physical_constraints, biological_verification
            ),
            'anomaly_locations': self._locate_anomalies(
                yolo_results, cluster_analysis, bio_analysis
            )
        }
        
        return fusion_result
    
    def _apply_physical_constraints(self, physical_features, yolo_results):
        """应用物理约束验证"""
        constraints_met = {}
        
        # 验证材料反射率
        reflectance = physical_features['material_reflectance']
        constraints_met['material_consistency'] = (
            reflectance['specular_intensity'] > 50 and
            reflectance['absorption_coefficient'] < 0.8
        )
        
        # 验证流体痕迹
        fluid_traces = physical_features['fluid_traces']
        constraints_met['fluid_evidence'] = (
            fluid_traces['moisture_likelihood'] > 0.3 or
            fluid_traces['capillary_effect'] > 1.5
        )
        
        # 验证应力分布
        stress = physical_features['stress_distribution']
        constraints_met['stress_anomaly'] = (
            stress['stress_concentration'] > 0.1 or
            stress['max_stress'] > np.percentile(stress['max_stress'], 75)
        )
        
        return constraints_met
    
    def _analyze_temporal_consistency(self, yolo_results, cluster_analysis):
        """分析时空一致性"""
        # 基于YOLO检测的物体运动一致性
        detections = yolo_results[0].boxes if len(yolo_results[0].boxes) > 0 else None
        
        if detections is None:
            return {'temporal_stability': 0.5, 'spatial_coherence': 0.5}
        
        # 计算检测框的空间分布一致性
        boxes = detections.xyxy.cpu().numpy()
        confidences = detections.conf.cpu().numpy()
        
        spatial_coherence = self._calculate_spatial_coherence(boxes)
        temporal_stability = np.mean(confidences)  # 使用置信度作为稳定性代理
        
        return {
            'temporal_stability': temporal_stability,
            'spatial_coherence': spatial_coherence
        }
    
    def _calculate_spatial_coherence(self, boxes):
        """计算空间一致性"""
        if len(boxes) < 2:
            return 0.5
        
        # 计算检测框之间的空间关系
        centers = np.array([[(x1+x2)/2, (y1+y2)/2] for x1, y1, x2, y2 in boxes])
        
        # 使用DBSCAN聚类分析空间分布
        clustering = DBSCAN(eps=50, min_samples=2).fit(centers)
        
        # 计算聚类质量
        labels = clustering.labels_
        n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
        
        if n_clusters == 0:
            return 0.5
        
        coherence_score = n_clusters / len(boxes)
        return min(coherence_score, 1.0)
    
    def _biological_verification(self, bio_analysis, physical_features):
        """生物启发验证"""
        # 模拟生物视觉系统的验证机制
        verification_scores = {}
        
        # 边缘一致性验证
        edge_consistency = bio_analysis.get('edge_consistency', 0.5)
        verification_scores['edge_verification'] = edge_consistency
        
        # 纹理模式验证
        texture_pattern = bio_analysis.get('texture_anomaly', 0.5)
        verification_scores['texture_verification'] = texture_pattern
        
        # 运动模式验证（基于流体特征）
        fluid_evidence = physical_features['fluid_traces']['moisture_likelihood']
        verification_scores['motion_verification'] = min(fluid_evidence * 2, 1.0)
        
        return verification_scores
    
    def _calculate_leakage_probability(self, physical_constraints, 
                                     temporal_consistency, biological_verification):
        """计算泄露概率"""
        # 物理证据权重
        physical_weight = 0.4
        temporal_weight = 0.3
        biological_weight = 0.3
        
        # 物理约束得分
        physical_score = np.mean([
            float(physical_constraints['material_consistency']),
            float(physical_constraints['fluid_evidence']),
            float(physical_constraints['stress_anomaly'])
        ])
        
        # 时空一致性得分
        temporal_score = (
            temporal_consistency['temporal_stability'] +
            temporal_consistency['spatial_coherence']
        ) / 2
        
        # 生物验证得分
        biological_score = np.mean(list(biological_verification.values()))
        
        # 加权融合
        leakage_prob = (
            physical_weight * physical_score +
            temporal_weight * temporal_score +
            biological_weight * biological_score
        )
        
        return min(leakage_prob, 1.0)
    
    def _assess_structural_risk(self, physical_features, cluster_analysis):
        """评估结构风险"""
        stress_features = physical_features['stress_distribution']
        
        risk_factors = [
            stress_features['max_stress'] / 255.0,
            stress_features['stress_concentration'],
            cluster_analysis.get('anomaly_density', 0.5)
        ]
        
        return np.mean(risk_factors)
    
    def _calculate_maintenance_urgency(self, physical_constraints, biological_verification):
        """计算维护紧急度"""
        urgency_factors = []
        
        # 物理约束违反
        if not physical_constraints['material_consistency']:
            urgency_factors.append(0.8)
        
        if physical_constraints['fluid_evidence']:
            urgency_factors.append(0.7)
            
        if physical_constraints['stress_anomaly']:
            urgency_factors.append(0.9)
        
        # 生物验证异常
        bio_scores = list(biological_verification.values())
        if np.mean(bio_scores) > 0.7:
            urgency_factors.append(0.6)
        
        return np.mean(urgency_factors) if urgency_factors else 0.3
    
    def _locate_anomalies(self, yolo_results, cluster_analysis, bio_analysis):
        """定位异常区域"""
        anomalies = []
        
        # 从YOLO检测中提取潜在异常
        if len(yolo_results[0].boxes) > 0:
            boxes = yolo_results[0].boxes.xyxy.cpu().numpy()
            confidences = yolo_results[0].boxes.conf.cpu().numpy()
            
            for i, (box, conf) in enumerate(zip(boxes, confidences)):
                if conf > 0.5:  # 高置信度检测
                    anomalies.append({
                        'type': 'object_based',
                        'bbox': box.tolist(),
                        'confidence': float(conf),
                        'source': 'yolo_zero_shot'
                    })
        
        # 从聚类分析中添加异常
        cluster_anomalies = cluster_analysis.get('anomaly_regions', [])
        anomalies.extend(cluster_anomalies)
        
        # 从生物分析中添加异常
        bio_anomalies = bio_analysis.get('suspicious_regions', [])
        anomalies.extend(bio_anomalies)
        
        return anomalies

class QuantumInspiredClustering:
    """量子启发聚类分析"""
    
    def __init__(self):
        self.quantum_states = 4  # 量子态数量
    
    def analyze_image_regions(self, image, yolo_results):
        """分析图像区域"""
        # 量子叠加态特征提取
        quantum_features = self._extract_quantum_features(image)
        
        # 叠加态聚类
        clusters = self._quantum_clustering(quantum_features)
        
        # 异常区域检测
        anomalies = self._detect_quantum_anomalies(clusters, quantum_features)
        
        return {
            'quantum_features': quantum_features,
            'clusters': clusters,
            'anomaly_regions': anomalies,
            'anomaly_density': len(anomalies) / (image.shape[0] * image.shape[1])
        }
    
    def _extract_quantum_features(self, image):
        """提取量子特征"""
        features = []
        
        # 多尺度量子特征
        for scale in [1, 2, 4]:
            resized = cv2.resize(image, 
                               (image.shape[1]//scale, image.shape[0]//scale))
            
            # 量子幅度特征
            magnitude_features = self._quantum_magnitude_analysis(resized)
            features.extend(magnitude_features)
            
            # 量子相位特征
            phase_features = self._quantum_phase_analysis(resized)
            features.extend(phase_features)
        
        return np.array(features)
    
    def _quantum_magnitude_analysis(self, image):
        """量子幅度分析"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # 小波变换模拟量子测量
        coeffs = pywt.wavedec2(gray, 'db4', level=2)
        
        magnitude_features = []
        for coeff in coeffs:
            if isinstance(coeff, tuple):
                for c in coeff:
                    magnitude_features.extend([
                        np.mean(np.abs(c)),
                        np.std(c),
                        np.percentile(np.abs(c), 90)
                    ])
            else:
                magnitude_features.extend([
                    np.mean(np.abs(coeff)),
                    np.std(coeff),
                    np.percentile(np.abs(coeff), 90)
                ])
        
        return magnitude_features
    
    def _quantum_phase_analysis(self, image):
        """量子相位分析"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY).astype(np.float32)
        
        # 傅里叶变换相位分析
        f_transform = np.fft.fft2(gray)
        phase = np.angle(f_transform)
        
        # 相位一致性特征
        phase_features = [
            np.mean(phase),
            np.std(phase),
            np.percentile(phase, 75) - np.percentile(phase, 25)
        ]
        
        return phase_features
    
    def _quantum_clustering(self, features):
        """量子聚类"""
        # 简化版量子聚类（实际应用可使用量子计算库）
        from sklearn.cluster import KMeans
        
        # 量子态数量的聚类
        kmeans = KMeans(n_clusters=self.quantum_states)
        labels = kmeans.fit_predict(features.reshape(-1, 1))
        
        return {
            'cluster_labels': labels,
            'cluster_centers': kmeans.cluster_centers_,
            'quantum_entropy': self._calculate_quantum_entropy(labels)
        }
    
    def _calculate_quantum_entropy(self, labels):
        """计算量子熵"""
        unique, counts = np.unique(labels, return_counts=True)
        probabilities = counts / len(labels)
        entropy = -np.sum(probabilities * np.log2(probabilities + 1e-8))
        return entropy
    
    def _detect_quantum_anomalies(self, clusters, features):
        """检测量子异常"""
        anomalies = []
        
        # 基于量子态概率的异常检测
        labels = clusters['cluster_labels']
        centers = clusters['cluster_centers']
        
        for i, (label, feature) in enumerate(zip(labels, features)):
            distance = np.abs(feature - centers[label])
            
            # 距离中心较远的点视为异常
            if distance > 2 * np.std(features):
                anomalies.append({
                    'index': i,
                    'quantum_state': int(label),
                    'anomaly_score': float(distance)
                })
        
        return anomalies

class BioMimeticAnalyzer:
    """仿生分析器"""
    
    def __init__(self):
        self.retina_model = self._create_retina_model()
        self.visual_cortex = self._create_visual_cortex()
    
    def _create_retina_model(self):
        """创建视网膜模型"""
        return {
            'photoreceptor_layer': cv2.getGaussianKernel(5, 1.0),
            'bipolar_cells': cv2.getGaussianKernel(3, 0.5),
            'ganglion_cells': np.array([[-1, -1, -1], [-1, 8, -1], [-1, -1, -1]])
        }
    
    def _create_visual_cortex(self):
        """创建视觉皮层模型"""
        # 简化版Gabor滤波器模拟V1皮层
        filters = []
        for theta in np.arange(0, np.pi, np.pi/4):
            kernel = cv2.getGaborKernel((21, 21), 5.0, theta, 10.0, 0.5, 0, ktype=cv2.CV_32F)
            filters.append(kernel)
        return filters
    
    def analyze_biological_patterns(self, image, physical_features):
        """分析生物模式"""
        # 视网膜处理
        retinal_output = self._retinal_processing(image)
        
        # 视觉皮层特征提取
        cortical_features = self._cortical_processing(retinal_output)
        
        # 模式识别
        pattern_analysis = self._pattern_recognition(cortical_features, physical_features)
        
        return pattern_analysis
    
    def _retinal_processing(self, image):
        """视网膜处理"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # 光感受器层
        photoreceptor = cv2.filter2D(gray, -1, self.retina_model['photoreceptor_layer'])
        
        # 双极细胞层（中心-周边拮抗）
        bipolar = cv2.filter2D(photoreceptor, -1, self.retina_model['bipolar_cells'])
        
        # 神经节细胞层（边缘检测）
        ganglion = cv2.filter2D(bipolar, -1, self.retina_model['ganglion_cells'])
        
        return {
            'photoreceptor': photoreceptor,
            'bipolar': bipolar,
            'ganglion': ganglion
        }
    
    def _cortical_processing(self, retinal_output):
        """视觉皮层处理"""
        ganglion_output = retinal_output['ganglion']
        
        cortical_responses = []
        for gabor_filter in self.visual_cortex:
            response = cv2.filter2D(ganglion_output, -1, gabor_filter)
            cortical_responses.append(response)
        
        # 特征整合
        integrated_features = {
            'orientation_selectivity': np.std(cortical_responses),
            'spatial_frequency': np.mean([np.mean(np.abs(r)) for r in cortical_responses]),
            'texture_consistency': self._analyze_texture_consistency(cortical_responses)
        }
        
        return integrated_features
    
    def _analyze_texture_consistency(self, cortical_responses):
        """分析纹理一致性"""
        response_variance = np.var(cortical_responses, axis=0)
        consistency_score = 1.0 / (1.0 + np.mean(response_variance))
        return consistency_score
    
    def _pattern_recognition(self, cortical_features, physical_features):
        """模式识别"""
        # 结合物理特征的生物模式识别
        pattern_scores = {}
        
        # 边缘一致性分析
        edge_consistency = cortical_features['orientation_selectivity']
        pattern_scores['edge_consistency'] = min(edge_consistency * 10, 1.0)
        
        # 纹理异常检测
        texture_consistency = cortical_features['texture_consistency']
        pattern_scores['texture_anomaly'] = 1.0 - texture_consistency
        
        # 结合流体特征的生物验证
        fluid_traces = physical_features['fluid_traces']
        pattern_scores['biological_fluid_evidence'] = (
            fluid_traces['moisture_likelihood'] * 
            cortical_features['spatial_frequency']
        )
        
        # 可疑区域识别
        suspicious_regions = self._identify_suspicious_regions(
            cortical_features, pattern_scores
        )
        
        return {
            'pattern_scores': pattern_scores,
            'suspicious_regions': suspicious_regions
        }
    
    def _identify_suspicious_regions(self, cortical_features, pattern_scores):
        """识别可疑区域"""
        suspicious_regions = []
        
        # 基于模式得分识别异常区域
        for pattern_name, score in pattern_scores.items():
            if score > 0.7:  # 高异常得分
                suspicious_regions.append({
                    'pattern_type': pattern_name,
                    'anomaly_score': score,
                    'biological_basis': 'cortical_response_anomaly'
                })
        
        return suspicious_regions

# 使用示例
def demo_zero_shot_tunnel_detection():
    """演示零样本隧道检测"""
    print("=== 零样本物理引导隧道检测系统 ===")
    
    # 初始化检测器
    detector = ZeroShotTunnelDetector()
    
    # 创建测试图像（实际应用中替换为真实隧道图像）
    test_image = create_test_tunnel_image()
    cv2.imwrite('test_tunnel.jpg', test_image)
    
    print("开始零样本检测分析...")
    results = detector.detect_tunnel_anomalies('test_tunnel.jpg')
    
    # 显示结果
    display_detection_results(results)
    
    return results

def create_test_tunnel_image():
    """创建测试隧道图像"""
    width, height = 800, 600
    image = np.zeros((height, width, 3), dtype=np.uint8)
    
    # 创建隧道结构
    cv2.rectangle(image, (100, 100), (700, 500), (100, 100, 100), -1)  # 隧道内部
    
    # 添加模拟泄露
    cv2.circle(image, (400, 300), 40, (0, 0, 200), -1)  # 红色泄露区域
    cv2.line(image, (200, 150), (300, 180), (0, 200, 200), 3)  # 裂缝
    
    # 添加一些纹理
    noise = np.random.randint(0, 50, (height, width, 3), dtype=np.uint8)
    image = cv2.add(image, noise)
    
    return image

def display_detection_results(results):
    """显示检测结果"""
    print("\n=== 检测结果 ===")
    
    final_detection = results['final_detection']
    
    print(f"泄露概率: {final_detection['leakage_probability']:.3f}")
    print(f"结构风险: {final_detection['structural_risk']:.3f}")
    print(f"维护紧急度: {final_detection['maintenance_urgency']:.3f}")
    
    print(f"\n检测到的异常数量: {len(final_detection['anomaly_locations'])}")
    
    # 显示物理特征
    physical = results['physical_features']
    print(f"\n物理特征分析:")
    print(f"  表面粗糙度: {physical['structural_analysis']['surface_roughness']:.3f}")
    print(f"  湿度可能性: {physical['fluid_traces']['moisture_likelihood']:.3f}")
    print(f"  最大应力: {physical['stress_distribution']['max_stress']:.3f}")

if __name__ == "__main__":
    results = demo_zero_shot_tunnel_detection()