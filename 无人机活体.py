import cv2
import numpy as np
import dlib
from scipy import ndimage, fft
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.svm import SVC
from sklearn.preprocessing import StandardScaler, RobustScaler
from sklearn.decomposition import PCA
from sklearn.calibration import CalibratedClassifierCV
import pickle
import os
import json
from collections import deque, Counter
import time
from typing import Tuple, List, Dict, Any, Optional
import logging
from dataclasses import dataclass
from enum import Enum
import math
from scipy.signal import medfilt, savgol_filter
from scipy.ndimage import gaussian_filter, sobel
from skimage import feature, filters, measure, exposure, segmentation
import warnings
warnings.filterwarnings('ignore')

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('DroneLiveness')

class DroneFlightMode(Enum):
    SURVEILLANCE = "surveillance"  # 监控模式
    TRACKING = "tracking"         # 跟踪模式
    INSPECTION = "inspection"     # 巡检模式
    SECURITY = "security"         # 安防模式

@dataclass
class DroneDetectionResult:
    is_live: bool
    confidence: float
    target_id: int
    position: Tuple[float, float, float]  # (x, y, scale)
    distance_estimate: float
    quality_score: float
    features_used: List[str]
    processing_time: float
    flight_mode: DroneFlightMode
    timestamp: float

class DroneLivenessDetector:
    """
    无人机专用活体检测系统
    针对无人机场景优化：距离变化、角度变化、运动模糊、计算效率
    """
    
    def __init__(self, config_path: str = None):
        # 初始化配置
        self.config = self._load_drone_config(config_path)
        
        # 初始化检测器
        self.detector = dlib.get_frontal_face_detector()
        try:
            self.predictor = dlib.shape_predictor(self.config['landmark_model_path'])
        except:
            logger.warning("Landmark model not found, using basic detection")
            self.predictor = None
        
        # 无人机特定参数
        self.min_face_pixels = self.config['min_face_pixels']
        self.max_face_pixels = self.config['max_face_pixels']
        self.distance_estimation_model = self._init_distance_estimation()
        
        # 多目标跟踪
        self.target_tracker = {}
        self.next_target_id = 0
        self.track_history = deque(maxlen=self.config['max_track_history'])
        
        # 特征提取优化
        self.feature_cache = {}
        self.adaptive_feature_selection = self.config['adaptive_feature_selection']
        
        # 分类器系统
        self.classifier = None
        self.feature_scaler = None
        self.pca = None
        
        # 飞行状态
        self.current_flight_mode = DroneFlightMode.SURVEILLANCE
        self.altitude = None
        self.camera_angle = 0  # 相机角度（度）
        
        # 性能监控
        self.performance_stats = {
            'frames_processed': 0,
            'average_processing_time': 0,
            'detection_rate': 0,
            'targets_tracked': 0
        }
        
        logger.info("Drone Liveness Detector initialized")

    def _load_drone_config(self, config_path: str) -> Dict[str, Any]:
        """加载无人机专用配置"""
        default_config = {
            'landmark_model_path': 'shape_predictor_68_face_landmarks.dat',
            'min_face_pixels': 30,      # 最小人脸像素（适应远距离）
            'max_face_pixels': 400,     # 最大人脸像素
            'max_track_history': 100,
            'adaptive_feature_selection': True,
            'distance_estimation_constant': 1000,  # 距离估计常数
            'motion_blur_threshold': 0.7,
            'scale_pyramid_levels': 3,
            'real_time_optimization': True,
            'confidence_threshold_surveillance': 0.6,
            'confidence_threshold_tracking': 0.7,
            'confidence_threshold_inspection': 0.8,
            'max_targets': 10,
            'feature_cache_size': 100
        }
        
        if config_path and os.path.exists(config_path):
            with open(config_path, 'r') as f:
                user_config = json.load(f)
                default_config.update(user_config)
        
        return default_config

    def _init_distance_estimation(self):
        """初始化距离估计模型"""
        # 基于人脸大小和相机参数的简单距离估计
        # 实际应用中应该使用更精确的传感器数据
        return {
            'reference_face_width': 0.14,  # 平均人脸宽度（米）
            'focal_length': 1000,          # 焦距（像素）
            'sensor_width': 0.01           # 传感器宽度（米）
        }

    def set_flight_mode(self, mode: DroneFlightMode, altitude: float = None, 
                       camera_angle: float = 0):
        """设置飞行模式和参数"""
        self.current_flight_mode = mode
        self.altitude = altitude
        self.camera_angle = camera_angle
        logger.info(f"Flight mode set to {mode.value}, altitude: {altitude}, camera angle: {camera_angle}")

    def drone_optimized_face_detection(self, image: np.ndarray) -> List[Tuple]:
        """
        无人机优化的多尺度人脸检测
        考虑距离变化和角度变化
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        detected_faces = []
        
        # 多尺度检测适应不同距离
        scales = [1.0, 0.75, 0.5, 1.25, 1.5] if self.current_flight_mode == DroneFlightMode.SURVEILLANCE else [1.0, 0.8, 1.2]
        
        for scale in scales:
            if scale != 1.0:
                scaled_width = int(image.shape[1] * scale)
                scaled_height = int(image.shape[0] * scale)
                scaled_image = cv2.resize(gray, (scaled_width, scaled_height))
            else:
                scaled_image = gray
            
            # 检测人脸
            faces = self.detector(scaled_image, 1)  # 第二个参数是上采样次数
            
            for face in faces:
                # 转换回原始坐标
                x = int(face.left() / scale)
                y = int(face.top() / scale)
                w = int((face.right() - face.left()) / scale)
                h = int((face.bottom() - face.top()) / scale)
                
                # 过滤太小或太大的检测
                if (w * h >= self.min_face_pixels ** 2 and 
                    w * h <= self.max_face_pixels ** 2):
                    
                    # 计算检测置信度（基于人脸比例和位置）
                    aspect_ratio = w / h
                    center_x = x + w // 2
                    center_y = y + h // 2
                    
                    # 理想的人脸宽高比约为0.7-0.8
                    aspect_score = 1.0 - min(1.0, abs(aspect_ratio - 0.75) / 0.5)
                    
                    # 中心位置得分（假设目标在图像中心附近）
                    img_center_x = image.shape[1] // 2
                    img_center_y = image.shape[0] // 2
                    distance_to_center = math.sqrt((center_x - img_center_x)**2 + (center_y - img_center_y)**2)
                    max_distance = math.sqrt(img_center_x**2 + img_center_y**2)
                    center_score = 1.0 - (distance_to_center / max_distance)
                    
                    confidence = 0.6 * aspect_score + 0.4 * center_score
                    
                    detected_faces.append((x, y, w, h, confidence))
        
        # 非极大值抑制
        return self.non_max_suppression(detected_faces)

    def non_max_suppression(self, faces: List[Tuple], overlap_threshold: float = 0.3) -> List[Tuple]:
        """非极大值抑制去除重复检测"""
        if len(faces) == 0:
            return []
        
        # 按置信度排序
        faces = sorted(faces, key=lambda x: x[4], reverse=True)
        picked = []
        
        while len(faces) > 0:
            current = faces[0]
            picked.append(current)
            faces = faces[1:]
            
            # 计算与当前框的IoU
            to_remove = []
            for i, face in enumerate(faces):
                iou = self.calculate_iou(current, face)
                if iou > overlap_threshold:
                    to_remove.append(i)
            
            # 移除重叠框
            for i in sorted(to_remove, reverse=True):
                faces.pop(i)
        
        return picked

    def calculate_iou(self, box1: Tuple, box2: Tuple) -> float:
        """计算两个边界框的IoU"""
        x1, y1, w1, h1, _ = box1
        x2, y2, w2, h2, _ = box2
        
        # 计算交集
        x_left = max(x1, x2)
        y_top = max(y1, y2)
        x_right = min(x1 + w1, x2 + w2)
        y_bottom = min(y1 + h1, y2 + h2)
        
        if x_right < x_left or y_bottom < y_top:
            return 0.0
        
        intersection_area = (x_right - x_left) * (y_bottom - y_top)
        
        # 计算并集
        box1_area = w1 * h1
        box2_area = w2 * h2
        union_area = box1_area + box2_area - intersection_area
        
        return intersection_area / union_area

    def estimate_distance(self, face_width_pixels: int) -> float:
        """根据人脸大小估计距离"""
        if self.altitude is not None:
            # 如果有高度信息，使用高度作为基础
            base_distance = self.altitude / math.cos(math.radians(self.camera_angle))
            
            # 根据人脸大小调整
            expected_face_width = (self.distance_estimation_model['reference_face_width'] * 
                                 self.distance_estimation_model['focal_length']) / base_distance
            
            scale_factor = expected_face_width / face_width_pixels if face_width_pixels > 0 else 1.0
            return base_distance * scale_factor
        else:
            # 基于人脸大小的简单估计
            return (self.distance_estimation_model['reference_face_width'] * 
                   self.distance_estimation_model['focal_length']) / face_width_pixels

    def drone_optimized_feature_extraction(self, image: np.ndarray, 
                                         face_rect: Tuple) -> Dict[str, np.ndarray]:
        """
        无人机优化的特征提取
        考虑运动模糊、距离变化和计算效率
        """
        x, y, w, h, confidence = face_rect
        face_roi = image[y:y+h, x:x+w]
        
        if face_roi.size == 0:
            return {}
        
        features = {}
        
        # 1. 运动模糊鲁棒的LBP特征
        features['lbp'] = self.drone_lbp_features(face_roi)
        
        # 2. 距离不变纹理特征
        features['texture'] = self.distance_invariant_texture(face_roi)
        
        # 3. 运动模糊检测特征
        features['blur_analysis'] = self.motion_blur_analysis(face_roi)
        
        # 4. 角度不变特征
        features['angle_invariant'] = self.angle_invariant_features(face_roi)
        
        # 5. 频域稳定性分析
        features['frequency_stability'] = self.frequency_stability_analysis(face_roi)
        
        # 根据飞行模式选择特征
        if self.adaptive_feature_selection:
            features = self.adaptive_feature_selection(features)
        
        return features

    def drone_lbp_features(self, face_roi: np.ndarray) -> np.ndarray:
        """无人机优化的LBP特征，对运动模糊更鲁棒"""
        gray = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY)
        
        # 运动模糊补偿 - 使用导向滤波增强边缘
        guided = cv2.ximgproc.guidedFilter(gray, gray, 5, 0.1)
        
        # 多尺度LBP
        lbp_features = []
        radii = [1, 2, 3]  # 多半径适应不同距离
        
        for radius in radii:
            n_points = 8 * radius
            lbp = feature.local_binary_pattern(guided, n_points, radius, method='uniform')
            hist, _ = np.histogram(lbp.ravel(), bins=n_points+2, range=(0, n_points+2))
            hist = hist.astype(np.float32)
            hist /= (hist.sum() + 1e-8)
            lbp_features.extend(hist)
        
        return np.array(lbp_features)

    def distance_invariant_texture(self, face_roi: np.ndarray) -> np.ndarray:
        """距离不变的纹理特征"""
        gray = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY)
        
        # 多分辨率分析
        texture_features = []
        scales = [1.0, 0.5, 0.25]
        
        for scale in scales:
            if scale != 1.0:
                scaled = cv2.resize(gray, None, fx=scale, fy=scale)
            else:
                scaled = gray
            
            # Gabor滤波器组
            gabor_features = []
            for theta in np.arange(0, np.pi, np.pi/4):
                for freq in [0.1, 0.2, 0.3]:
                    gabor_kernel = cv2.getGaborKernel((15, 15), 5.0, theta, freq, 0.5, 0, ktype=cv2.CV_32F)
                    filtered = cv2.filter2D(scaled, cv2.CV_32F, gabor_kernel)
                    gabor_features.extend([filtered.mean(), filtered.std()])
            
            texture_features.extend(gabor_features)
        
        return np.array(texture_features[:30])  # 限制特征数量

    def motion_blur_analysis(self, face_roi: np.ndarray) -> np.ndarray:
        """运动模糊分析特征"""
        gray = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY)
        
        blur_features = []
        
        # 1. 拉普拉斯方差
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        blur_features.append(laplacian_var)
        
        # 2. 频域分析
        fft_transform = fft.fft2(gray)
        fft_shift = fft.fftshift(fft_transform)
        magnitude_spectrum = np.log(np.abs(fft_shift) + 1)
        
        # 检查频域中的运动模糊模式（沿特定方向的能量衰减）
        h, w = magnitude_spectrum.shape
        center_y, center_x = h // 2, w // 2
        
        # 分析不同方向的频率成分
        for angle in [0, 45, 90, 135]:
            # 创建角度掩码
            mask = np.zeros_like(magnitude_spectrum)
            line_length = min(h, w) // 2
            
            # 在频域中沿特定方向采样
            for r in range(1, line_length):
                x = int(center_x + r * math.cos(math.radians(angle)))
                y = int(center_y + r * math.sin(math.radians(angle)))
                
                if 0 <= x < w and 0 <= y < h:
                    mask[y, x] = 1
            
            directional_energy = (magnitude_spectrum * mask).sum()
            blur_features.append(directional_energy)
        
        # 3. 边缘锐度分析
        sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        gradient_magnitude = np.sqrt(sobelx**2 + sobely**2)
        edge_sharpness = gradient_magnitude.mean()
        blur_features.append(edge_sharpness)
        
        return np.array(blur_features)

    def angle_invariant_features(self, face_roi: np.ndarray) -> np.ndarray:
        """角度不变特征提取"""
        gray = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY)
        
        # 旋转不变的LBP
        lbp_rot = feature.local_binary_pattern(gray, 24, 3, method='uniform')
        hist_rot, _ = np.histogram(lbp_rot.ravel(), bins=26, range=(0, 26))
        hist_rot = hist_rot.astype(np.float32)
        hist_rot /= (hist_rot.sum() + 1e-8)
        
        # 傅里叶梅林变换（简化版）- 对旋转和缩放不变
        f = fft.fft2(gray)
        fshift = fft.fftshift(f)
        magnitude = np.log(np.abs(fshift) + 1)
        
        # 转换为极坐标（简化）
        h, w = magnitude.shape
        center_y, center_x = h // 2, w // 2
        max_radius = min(center_x, center_y)
        
        radial_features = []
        for r in range(5, max_radius, max_radius//10):
            circle_mask = np.zeros_like(magnitude)
            cv2.circle(circle_mask, (center_x, center_y), r, 1, -1)
            radial_energy = (magnitude * circle_mask).sum()
            radial_features.append(radial_energy)
        
        # 组合特征
        angle_features = list(hist_rot) + radial_features[:10]  # 限制数量
        
        return np.array(angle_features)

    def frequency_stability_analysis(self, face_roi: np.ndarray) -> np.ndarray:
        """频域稳定性分析"""
        gray = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY)
        
        # 多窗口频域分析
        h, w = gray.shape
        window_size = min(h, w) // 3
        
        stability_features = []
        
        if window_size > 10:
            # 在多个窗口上分析频域一致性
            windows = []
            for i in range(0, h - window_size, window_size//2):
                for j in range(0, w - window_size, window_size//2):
                    window = gray[i:i+window_size, j:j+window_size]
                    if window.size > 0:
                        windows.append(window)
            
            if len(windows) >= 2:
                # 计算各窗口的频域特征
                window_features = []
                for window in windows[:4]:  # 限制窗口数量
                    fft_window = fft.fft2(window)
                    fft_shift = fft.fftshift(fft_window)
                    magnitude = np.log(np.abs(fft_shift) + 1)
                    window_features.append(magnitude.flatten()[:20])  # 取前20个系数
                
                # 计算窗口间的一致性
                if len(window_features) >= 2:
                    consistency = 0
                    for i in range(len(window_features)):
                        for j in range(i+1, len(window_features)):
                            correlation = np.corrcoef(window_features[i], window_features[j])[0,1]
                            consistency += correlation if not np.isnan(correlation) else 0
                    
                    consistency /= (len(window_features) * (len(window_features)-1) / 2)
                    stability_features.append(consistency)
                else:
                    stability_features.append(0)
            else:
                stability_features.append(0)
        else:
            stability_features.append(0)
        
        return np.array(stability_features)

    def adaptive_feature_selection(self, features: Dict[str, np.ndarray]) -> Dict[str, np.ndarray]:
        """根据飞行模式自适应选择特征"""
        selected_features = {}
        
        if self.current_flight_mode == DroneFlightMode.SURVEILLANCE:
            # 监控模式：侧重计算效率和快速检测
            selected_features['lbp'] = features['lbp'][:50] if 'lbp' in features else np.array([])
            selected_features['blur_analysis'] = features['blur_analysis'] if 'blur_analysis' in features else np.array([])
            
        elif self.current_flight_mode == DroneFlightMode.TRACKING:
            # 跟踪模式：平衡精度和速度
            selected_features['lbp'] = features['lbp'] if 'lbp' in features else np.array([])
            selected_features['texture'] = features['texture'][:20] if 'texture' in features else np.array([])
            selected_features['blur_analysis'] = features['blur_analysis'] if 'blur_analysis' in features else np.array([])
            
        elif self.current_flight_mode == DroneFlightMode.INSPECTION:
            # 巡检模式：最高精度
            for key in features:
                selected_features[key] = features[key]
        
        elif self.current_flight_mode == DroneFlightMode.SECURITY:
            # 安防模式：侧重防欺骗
            selected_features['lbp'] = features['lbp'] if 'lbp' in features else np.array([])
            selected_features['angle_invariant'] = features['angle_invariant'] if 'angle_invariant' in features else np.array([])
            selected_features['frequency_stability'] = features['frequency_stability'] if 'frequency_stability' in features else np.array([])
        
        return selected_features

    def update_target_tracking(self, detection_results: List[DroneDetectionResult], 
                             frame_timestamp: float):
        """更新多目标跟踪"""
        current_targets = {}
        
        for result in detection_results:
            # 寻找最近的历史目标
            best_match_id = None
            min_distance = float('inf')
            
            for target_id, target_data in self.target_tracker.items():
                last_position = target_data['positions'][-1] if target_data['positions'] else (0, 0, 0)
                current_position = result.position
                
                # 计算位置距离
                pos_distance = math.sqrt(
                    (last_position[0] - current_position[0])**2 +
                    (last_position[1] - current_position[1])**2
                )
                
                # 计算尺度距离
                scale_distance = abs(last_position[2] - current_position[2])
                
                total_distance = pos_distance + scale_distance * 10  # 尺度变化权重更高
                
                if total_distance < min_distance and total_distance < 100:  # 距离阈值
                    min_distance = total_distance
                    best_match_id = target_id
            
            if best_match_id is not None:
                # 更新现有目标
                target_data = self.target_tracker[best_match_id]
                target_data['positions'].append(result.position)
                target_data['confidences'].append(result.confidence)
                target_data['last_seen'] = frame_timestamp
                target_data['live_count'] += 1 if result.is_live else 0
                target_data['total_count'] += 1
                
                # 更新目标ID
                result.target_id = best_match_id
                current_targets[best_match_id] = result
                
            else:
                # 创建新目标
                new_id = self.next_target_id
                self.next_target_id += 1
                
                self.target_tracker[new_id] = {
                    'positions': [result.position],
                    'confidences': [result.confidence],
                    'first_seen': frame_timestamp,
                    'last_seen': frame_timestamp,
                    'live_count': 1 if result.is_live else 0,
                    'total_count': 1
                }
                
                result.target_id = new_id
                current_targets[new_id] = result
        
        # 清理过期的目标
        current_time = time.time()
        expired_targets = []
        for target_id, target_data in self.target_tracker.items():
            if current_time - target_data['last_seen'] > 5.0:  # 5秒未更新
                expired_targets.append(target_id)
        
        for target_id in expired_targets:
            del self.target_tracker[target_id]
        
        # 更新跟踪历史
        self.track_history.append({
            'timestamp': frame_timestamp,
            'targets': current_targets
        })
        
        return current_targets

    def drone_liveness_detection(self, image: np.ndarray, 
                               previous_image: np.ndarray = None,
                               frame_timestamp: float = None) -> List[DroneDetectionResult]:
        """
        无人机场景下的活体检测主函数
        """
        if frame_timestamp is None:
            frame_timestamp = time.time()
        
        start_time = time.time()
        
        # 人脸检测
        detected_faces = self.drone_optimized_face_detection(image)
        
        if not detected_faces:
            return []
        
        results = []
        
        for i, face_rect in enumerate(detected_faces):
            if i >= self.config['max_targets']:
                break  # 限制处理的目标数量
            
            x, y, w, h, detection_confidence = face_rect
            
            # 特征提取
            features = self.drone_optimized_feature_extraction(image, face_rect)
            
            if not features:
                continue
            
            # 活体检测
            is_live, confidence = self.classify_liveness(features)
            
            # 距离估计
            distance = self.estimate_distance(w)
            
            # 位置信息（归一化坐标）
            img_height, img_width = image.shape[:2]
            pos_x = x / img_width
            pos_y = y / img_height
            scale = w / img_width  # 相对尺度
            
            # 质量评估
            quality_score = self.assess_drone_quality(features, w, h)
            
            # 构建结果
            result = DroneDetectionResult(
                is_live=is_live,
                confidence=confidence,
                target_id=-1,  # 将在跟踪中分配
                position=(pos_x, pos_y, scale),
                distance_estimate=distance,
                quality_score=quality_score,
                features_used=list(features.keys()),
                processing_time=time.time() - start_time,
                flight_mode=self.current_flight_mode,
                timestamp=frame_timestamp
            )
            
            results.append(result)
        
        # 目标跟踪
        if results:
            tracked_results = self.update_target_tracking(results, frame_timestamp)
            results = list(tracked_results.values())
        
        # 更新性能统计
        self.update_performance_stats(len(results), time.time() - start_time)
        
        return results

    def classify_liveness(self, features: Dict[str, np.ndarray]) -> Tuple[bool, float]:
        """活体分类"""
        if self.classifier is None or self.feature_scaler is None:
            # 如果没有训练好的分类器，使用基于特征的启发式方法
            return self.heuristic_liveness_detection(features)
        
        # 展平特征
        feature_vector = self._flatten_features(features)
        
        if len(feature_vector) == 0:
            return False, 0.0
        
        # 特征预处理
        feature_vector_scaled = self.feature_scaler.transform(feature_vector.reshape(1, -1))
        
        if self.pca:
            feature_vector_processed = self.pca.transform(feature_vector_scaled)
        else:
            feature_vector_processed = feature_vector_scaled
        
        # 预测
        confidence = self.classifier.predict_proba(feature_vector_processed)[0][1]
        
        # 根据飞行模式调整阈值
        threshold_map = {
            DroneFlightMode.SURVEILLANCE: self.config['confidence_threshold_surveillance'],
            DroneFlightMode.TRACKING: self.config['confidence_threshold_tracking'],
            DroneFlightMode.INSPECTION: self.config['confidence_threshold_inspection'],
            DroneFlightMode.SECURITY: self.config['confidence_threshold_inspection']
        }
        
        threshold = threshold_map.get(self.current_flight_mode, 0.7)
        is_live = confidence > threshold
        
        return is_live, confidence

    def heuristic_liveness_detection(self, features: Dict[str, np.ndarray]) -> Tuple[bool, float]:
        """启发式活体检测（用于无训练模型的情况）"""
        confidence = 0.5  # 基础置信度
        
        # 基于运动模糊分析
        if 'blur_analysis' in features:
            blur_features = features['blur_analysis']
            if len(blur_features) > 0:
                laplacian_var = blur_features[0]
                # 高拉普拉斯方差通常表示清晰图像（更可能是真实人脸）
                if laplacian_var > 100:
                    confidence += 0.2
                elif laplacian_var < 20:
                    confidence -= 0.2
        
        # 基于纹理丰富度
        if 'texture' in features:
            texture_features = features['texture']
            if len(texture_features) > 0:
                texture_std = np.std(texture_features)
                # 丰富的纹理通常表示真实人脸
                if texture_std > 0.1:
                    confidence += 0.15
        
        # 基于频域稳定性
        if 'frequency_stability' in features:
            stability_features = features['frequency_stability']
            if len(stability_features) > 0:
                stability = stability_features[0]
                # 高稳定性通常表示真实人脸
                if stability > 0.7:
                    confidence += 0.1
        
        confidence = max(0.0, min(1.0, confidence))
        is_live = confidence > 0.6
        
        return is_live, confidence

    def assess_drone_quality(self, features: Dict[str, np.ndarray], width: int, height: int) -> float:
        """评估检测质量（考虑无人机特定因素）"""
        quality_score = 1.0
        
        # 基于大小的质量
        face_area = width * height
        ideal_area = (self.min_face_pixels + self.max_face_pixels) / 2
        area_ratio = min(face_area / ideal_area, ideal_area / face_area)
        quality_score *= area_ratio
        
        # 基于运动模糊的质量
        if 'blur_analysis' in features:
            blur_features = features['blur_analysis']
            if len(blur_features) > 0:
                laplacian_var = blur_features[0]
                blur_quality = min(1.0, laplacian_var / 100)  # 假设100是良好阈值
                quality_score *= blur_quality
        
        # 基于纹理的质量
        if 'texture' in features:
            texture_features = features['texture']
            if len(texture_features) > 0:
                texture_energy = np.mean(np.abs(texture_features))
                texture_quality = min(1.0, texture_energy / 0.5)  # 经验阈值
                quality_score *= texture_quality
        
        return max(0.0, min(1.0, quality_score))

    def _flatten_features(self, features: Dict[str, np.ndarray]) -> np.ndarray:
        """展平特征字典"""
        flattened = []
        for key in ['lbp', 'texture', 'blur_analysis', 'angle_invariant', 'frequency_stability']:
            if key in features and len(features[key]) > 0:
                flattened.extend(features[key])
        return np.array(flattened)

    def update_performance_stats(self, targets_detected: int, processing_time: float):
        """更新性能统计"""
        self.performance_stats['frames_processed'] += 1
        self.performance_stats['targets_tracked'] += targets_detected
        
        # 更新平均处理时间（指数移动平均）
        alpha = 0.1
        current_avg = self.performance_stats['average_processing_time']
        if current_avg == 0:
            self.performance_stats['average_processing_time'] = processing_time
        else:
            self.performance_stats['average_processing_time'] = (
                alpha * processing_time + (1 - alpha) * current_avg
            )
        
        # 更新检测率
        detection_rate = targets_detected / max(1, self.performance_stats['frames_processed'])
        self.performance_stats['detection_rate'] = detection_rate

    def get_drone_performance_report(self) -> Dict[str, Any]:
        """获取无人机专用性能报告"""
        return {
            'flight_mode': self.current_flight_mode.value,
            'frames_processed': self.performance_stats['frames_processed'],
            'average_processing_time_ms': self.performance_stats['average_processing_time'] * 1000,
            'detection_rate': self.performance_stats['detection_rate'],
            'active_targets': len(self.target_tracker),
            'total_targets_tracked': self.performance_stats['targets_tracked'],
            'altitude': self.altitude,
            'camera_angle': self.camera_angle
        }

    def train_drone_classifier(self, real_samples: List[Dict], fake_samples: List[Dict]):
        """训练无人机专用分类器"""
        logger.info("Training drone-optimized classifier...")
        
        # 准备特征数据
        X_real = [self._flatten_features(sample) for sample in real_samples]
        X_fake = [self._flatten_features(sample) for sample in fake_samples]
        
        X = np.vstack([X_real, X_fake])
        y = np.hstack([np.ones(len(X_real)), np.zeros(len(X_fake))])
        
        # 特征预处理
        self.feature_scaler = RobustScaler()
        X_scaled = self.feature_scaler.fit_transform(X)
        
        # 使用随机森林（适合无人机场景）
        self.classifier = RandomForestClassifier(
            n_estimators=50,  # 减少树的数量以适应计算限制
            max_depth=10,
            min_samples_split=5,
            min_samples_leaf=2,
            random_state=42
        )
        
        self.classifier.fit(X_scaled, y)
        
        train_accuracy = self.classifier.score(X_scaled, y)
        logger.info(f"Drone classifier training completed with accuracy: {train_accuracy:.4f}")
        
        return train_accuracy

    def save_drone_model(self, model_path: str):
        """保存无人机专用模型"""
        model_data = {
            'classifier': self.classifier,
            'feature_scaler': self.feature_scaler,
            'pca': self.pca,
            'config': self.config,
            'performance_stats': self.performance_stats,
            'next_target_id': self.next_target_id
        }
        
        with open(model_path, 'wb') as f:
            pickle.dump(model_data, f)
        
        logger.info(f"Drone model saved to {model_path}")

    def load_drone_model(self, model_path: str):
        """加载无人机专用模型"""
        with open(model_path, 'rb') as f:
            model_data = pickle.load(f)
        
        self.classifier = model_data['classifier']
        self.feature_scaler = model_data['feature_scaler']
        self.pca = model_data['pca']
        self.config.update(model_data['config'])
        self.performance_stats.update(model_data['performance_stats'])
        self.next_target_id = model_data.get('next_target_id', 0)
        
        logger.info(f"Drone model loaded from {model_path}")

# 无人机控制集成类
class DroneIntegration:
    """无人机控制系统集成"""
    
    def __init__(self, liveness_detector: DroneLivenessDetector):
        self.detector = liveness_detector
        self.command_queue = deque()
        
    def process_drone_frame(self, frame: np.ndarray, telemetry: Dict[str, Any] = None) -> List[Dict]:
        """处理无人机传回的帧数据"""
        # 更新检测器状态
        if telemetry:
            altitude = telemetry.get('altitude')
            camera_angle = telemetry.get('camera_angle', 0)
            flight_mode_str = telemetry.get('flight_mode', 'surveillance')
            
            try:
                flight_mode = DroneFlightMode(flight_mode_str)
            except ValueError:
                flight_mode = DroneFlightMode.SURVEILLANCE
            
            self.detector.set_flight_mode(flight_mode, altitude, camera_angle)
        
        # 执行活体检测
        results = self.detector.drone_liveness_detection(frame)
        
        # 生成控制命令
        commands = self.generate_control_commands(results, telemetry)
        
        return commands
    
    def generate_control_commands(self, results: List[DroneDetectionResult], 
                                telemetry: Dict[str, Any]) -> List[Dict]:
        """根据检测结果生成无人机控制命令"""
        commands = []
        
        live_targets = [r for r in results if r.is_live]
        fake_targets = [r for r in results if not r.is_live]
        
        if live_targets:
            # 有活体目标时的策略
            if self.detector.current_flight_mode == DroneFlightMode.SURVEILLANCE:
                # 监控模式：跟踪最近的活体目标
                closest_target = min(live_targets, key=lambda x: x.distance_estimate)
                commands.append({
                    'type': 'track',
                    'target_id': closest_target.target_id,
                    'position': closest_target.position,
                    'distance': closest_target.distance_estimate
                })
            
            elif self.detector.current_flight_mode == DroneFlightMode.TRACKING:
                # 跟踪模式：保持对目标的跟踪
                for target in live_targets:
                    commands.append({
                        'type': 'maintain_track',
                        'target_id': target.target_id,
                        'position': target.position
                    })
            
            elif self.detector.current_flight_mode == DroneFlightMode.INSPECTION:
                # 巡检模式：靠近目标进行详细检查
                for target in live_targets:
                    if target.distance_estimate > 10:  # 如果距离大于10米
                        commands.append({
                            'type': 'approach',
                            'target_id': target.target_id,
                            'distance': target.distance_estimate
                        })
            
            elif self.detector.current_flight_mode == DroneFlightMode.SECURITY:
                # 安防模式：记录所有活体目标
                for target in live_targets:
                    commands.append({
                        'type': 'log_security_event',
                        'target_id': target.target_id,
                        'position': target.position,
                        'confidence': target.confidence,
                        'timestamp': target.timestamp
                    })
        
        elif fake_targets and self.detector.current_flight_mode == DroneFlightMode.SECURITY:
            # 安防模式下检测到伪造目标
            for target in fake_targets:
                commands.append({
                    'type': 'spoofing_alert',
                    'target_id': target.target_id,
                    'position': target.position,
                    'confidence': target.confidence
                })
        
        # 性能优化命令
        performance_report = self.detector.get_drone_performance_report()
        if performance_report['average_processing_time_ms'] > 100:  # 处理时间过长
            commands.append({
                'type': 'reduce_processing',
                'current_time_ms': performance_report['average_processing_time_ms']
            })
        
        return commands

# 实时无人机演示
def drone_live_demo():
    """无人机实时活体检测演示"""
    detector = DroneLivenessDetector()
    
    # 尝试加载预训练模型
    try:
        detector.load_drone_model('drone_liveness_model.pkl')
        logger.info("Loaded pre-trained drone model")
    except:
        logger.warning("No pre-trained model found, using heuristic detection")
    
    # 初始化无人机集成
    drone_control = DroneIntegration(detector)
    
    # 模拟无人机视频流（实际应用中替换为真实的无人机视频流）
    cap = cv2.VideoCapture(0)  # 使用摄像头模拟
    
    # 创建显示窗口
    cv2.namedWindow('Drone Liveness Detection', cv2.WINDOW_NORMAL)
    
    logger.info("Starting drone liveness detection demo. Press 'q' to quit")
    
    frame_count = 0
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        frame_count += 1
        
        # 模拟无人机遥测数据
        telemetry = {
            'altitude': 15 + 5 * math.sin(frame_count / 30),  # 模拟高度变化
            'camera_angle': 20 * math.sin(frame_count / 50),  # 模拟相机角度变化
            'flight_mode': 'surveillance'
        }
        
        # 每10帧切换一次飞行模式（演示用）
        if frame_count % 100 == 0:
            modes = list(DroneFlightMode)
            current_index = modes.index(detector.current_flight_mode)
            next_mode = modes[(current_index + 1) % len(modes)]
            detector.set_flight_mode(next_mode, telemetry['altitude'], telemetry['camera_angle'])
        
        # 处理帧并生成控制命令
        commands = drone_control.process_drone_frame(frame, telemetry)
        
        # 可视化结果
        display_frame = frame.copy()
        
        # 绘制检测结果
        results = detector.drone_liveness_detection(frame)
        
        for result in results:
            x = int(result.position[0] * frame.shape[1])
            y = int(result.position[1] * frame.shape[0])
            w = int(result.position[2] * frame.shape[1])
            h = int(w * 1.2)  # 假设人脸宽高比
            
            color = (0, 255, 0) if result.is_live else (0, 0, 255)
            status = "LIVE" if result.is_live else "FAKE"
            
            # 绘制边界框
            cv2.rectangle(display_frame, (x, y), (x + w, y + h), color, 2)
            
            # 绘制目标ID和状态
            cv2.putText(display_frame, f"ID:{result.target_id} {status}", (x, y-10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
            
            # 绘制置信度和距离
            info_text = f"Conf: {result.confidence:.2f} Dist: {result.distance_estimate:.1f}m"
            cv2.putText(display_frame, info_text, (x, y+h+20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        
        # 显示飞行模式和性能信息
        mode_text = f"Mode: {detector.current_flight_mode.value}"
        perf_report = detector.get_drone_performance_report()
        if perf_report['average_processing_time_ms'] > 0:
            fps = 1000 / perf_report['average_processing_time_ms']
        else:
            fps = 0

        perf_text = f"FPS: {fps:.1f} | Targets: {perf_report['active_targets']}"
        
        cv2.putText(display_frame, mode_text, (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(display_frame, perf_text, (10, 60),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
        
        # 显示控制命令
        if commands:
            cmd_text = f"Commands: {len(commands)}"
            cv2.putText(display_frame, cmd_text, (10, 90),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 1)
        
        cv2.imshow('Drone Liveness Detection', display_frame)
        
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('r'):
            # 重置统计
            detector.performance_stats = {
                'frames_processed': 0,
                'average_processing_time': 0,
                'detection_rate': 0,
                'targets_tracked': 0
            }
            detector.target_tracker = {}
            logger.info("Statistics reset")
    
    cap.release()
    cv2.destroyAllWindows()
    
    # 输出最终报告
    final_report = detector.get_drone_performance_report()
    logger.info("Final Drone Performance Report:")
    for key, value in final_report.items():
        logger.info(f"  {key}: {value}")

if __name__ == "__main__":
    drone_live_demo()