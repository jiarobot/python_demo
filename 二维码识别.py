import numpy as np
import cv2
import math
import json
import time
from typing import List, Tuple, Dict, Optional, Any
from dataclasses import dataclass
from enum import Enum
import heapq
from collections import deque

class ProcessingMode(Enum):
    """处理模式枚举"""
    HIGH_SPEED = 1
    BALANCED = 2  
    HIGH_ACCURACY = 3

@dataclass
class DetectionResult:
    """检测结果数据结构"""
    success: bool
    qr_codes: List[Dict]
    processing_time: float
    image_metrics: Dict[str, float]
    debug_info: Dict[str, Any]
    timestamp: float

class RobustQRDetector:
    """鲁棒性二维码检测器 - 修复了凸包计算问题"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or self.default_config()
        self.performance_stats = {
            'total_frames': 0,
            'successful_detections': 0,
            'average_processing_time': 0.0
        }
        
    def default_config(self) -> Dict[str, Any]:
        """默认配置"""
        return {
            'min_contour_area': 50,
            'max_contour_area': 100000,
            'scale_levels': [0.5, 0.75, 1.0],
            'confidence_threshold': 0.4,
            'max_candidates': 50,
            'enable_multi_scale': True,
            'enable_perspective_correction': False  # 暂时禁用透视校正
        }
    
    def multi_scale_detection(self, image: np.ndarray) -> DetectionResult:
        """多尺度检测主函数"""
        start_time = time.time()
        all_detections = []
        debug_info = {}
        
        # 图像质量评估
        image_quality = self.assess_image_quality(image)
        debug_info['image_quality'] = image_quality
        
        # 多尺度处理
        if self.config['enable_multi_scale']:
            for scale in self.config['scale_levels']:
                scaled_image = self.scale_image(image, scale)
                detections = self.detect_at_scale(scaled_image, scale)
                all_detections.extend(detections)
        else:
            detections = self.detect_at_scale(image, 1.0)
            all_detections.extend(detections)
        
        # 候选区域融合与去重
        merged_detections = self.merge_detections(all_detections)
        
        # 置信度过滤
        final_detections = [
            det for det in merged_detections 
            if det['confidence'] >= self.config['confidence_threshold']
        ]
        
        processing_time = time.time() - start_time
        
        # 更新性能统计
        self.update_performance_stats(len(final_detections) > 0, processing_time)
        
        result = DetectionResult(
            success=len(final_detections) > 0,
            qr_codes=final_detections,
            processing_time=processing_time,
            image_metrics=image_quality,
            debug_info=debug_info,
            timestamp=time.time()
        )
        
        return result
    
    def scale_image(self, image: np.ndarray, scale: float) -> np.ndarray:
        """图像缩放"""
        if abs(scale - 1.0) < 0.01:
            return image
            
        new_width = int(image.shape[1] * scale)
        new_height = int(image.shape[0] * scale)
        
        return cv2.resize(image, (new_width, new_height), 
                         interpolation=cv2.INTER_AREA if scale < 1.0 else cv2.INTER_CUBIC)
    
    def detect_at_scale(self, image: np.ndarray, scale: float) -> List[Dict]:
        """在特定尺度下检测"""
        # 预处理
        preprocessed = self.robust_preprocessing(image)
        
        # 候选区域检测
        candidates = self.find_candidate_regions(preprocessed)
        
        # 特征验证
        validated_candidates = self.validate_candidates(image, candidates, scale)
        
        return validated_candidates
    
    def robust_preprocessing(self, image: np.ndarray) -> np.ndarray:
        """鲁棒性预处理管道"""
        # 转换为灰度图
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        # 对比度增强
        contrast_enhanced = self.contrast_enhancement(gray)
        
        # 自适应二值化
        binary = self.adaptive_binarization(contrast_enhanced)
        
        # 形态学操作
        morphological = self.safe_morphological_ops(binary)
        
        return morphological
    
    def contrast_enhancement(self, image: np.ndarray) -> np.ndarray:
        """对比度增强"""
        # CLAHE
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(image)
        return enhanced
    
    def adaptive_binarization(self, image: np.ndarray) -> np.ndarray:
        """自适应二值化"""
        binary = cv2.adaptiveThreshold(
            image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 11, 2
        )
        return binary
    
    def safe_morphological_ops(self, binary: np.ndarray) -> np.ndarray:
        """安全的形态学操作"""
        # 噪声去除
        kernel_open = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        denoised = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel_open)
        
        # 断点连接
        kernel_close = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        connected = cv2.morphologyEx(denoised, cv2.MORPH_CLOSE, kernel_close)
        
        return connected
    
    def find_candidate_regions(self, binary: np.ndarray) -> List[Dict]:
        """寻找候选区域"""
        contours, hierarchy = cv2.findContours(
            binary, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE
        )
        
        candidates = []
        
        for i, contour in enumerate(contours):
            # 基本几何特征
            area = cv2.contourArea(contour)
            if area < self.config['min_contour_area'] or area > self.config['max_contour_area']:
                continue
            
            perimeter = cv2.arcLength(contour, True)
            if perimeter == 0:
                continue
            
            # 多边形近似
            epsilon = 0.02 * perimeter
            approx = cv2.approxPolyDP(contour, epsilon, True)
            
            # 计算多种几何特征
            features = self.calculate_contour_features(contour, approx)
            
            if self.is_potential_qr_feature(features):
                candidate = {
                    'contour': contour,
                    'approx': approx,
                    'features': features,
                    'hierarchy': hierarchy[0][i] if hierarchy is not None else None,
                    'center': self.get_contour_center(contour)
                }
                candidates.append(candidate)
                
                if len(candidates) >= self.config['max_candidates']:
                    break
        
        return candidates
    
    def calculate_contour_features(self, contour: np.ndarray, approx: np.ndarray) -> Dict[str, float]:
        """计算轮廓特征"""
        area = cv2.contourArea(contour)
        perimeter = cv2.arcLength(contour, True)
        
        # 边界矩形特征
        rect = cv2.minAreaRect(contour)
        box = cv2.boxPoints(rect)
        box_area = cv2.contourArea(box.astype(np.float32))
        
        # 凸包特征
        hull = cv2.convexHull(contour)
        hull_area = cv2.contourArea(hull)
        
        # 计算各种特征指标
        rectangularity = area / box_area if box_area > 0 else 0
        circularity = 4 * math.pi * area / (perimeter * perimeter) if perimeter > 0 else 0
        solidity = area / hull_area if hull_area > 0 else 0
        aspect_ratio = self.calculate_aspect_ratio(rect)
        
        return {
            'area': area,
            'perimeter': perimeter,
            'rectangularity': rectangularity,
            'circularity': circularity,
            'solidity': solidity,
            'aspect_ratio': aspect_ratio,
            'vertex_count': len(approx)
        }
    
    def calculate_aspect_ratio(self, rect: Tuple) -> float:
        """计算宽高比"""
        width, height = rect[1]
        return max(width, height) / min(width, height) if min(width, height) > 0 else 0
    
    def get_contour_center(self, contour: np.ndarray) -> Tuple[float, float]:
        """获取轮廓中心 - 修复版本"""
        M = cv2.moments(contour)
        if M["m00"] != 0:
            cx = float(M["m10"] / M["m00"])
            cy = float(M["m01"] / M["m00"])
        else:
            # 如果矩为0，使用边界矩形的中心
            x, y, w, h = cv2.boundingRect(contour)
            cx = float(x + w / 2)
            cy = float(y + h / 2)
        return (cx, cy)
    
    def is_potential_qr_feature(self, features: Dict[str, float]) -> bool:
        """判断是否为潜在的QR码特征"""
        conditions = [
            0.6 <= features['rectangularity'] <= 1.4,
            features['circularity'] < 0.8,
            0.7 <= features['solidity'] <= 1.0,
            1.0 <= features['aspect_ratio'] <= 3.0,
            3 <= features['vertex_count'] <= 8
        ]
        
        return sum(conditions) >= 3
    
    def validate_candidates(self, image: np.ndarray, candidates: List[Dict], scale: float) -> List[Dict]:
        """验证候选区域"""
        validated = []
        
        # 寻找QR码模式组
        qr_groups = self.find_qr_pattern_groups(candidates)
        
        for group in qr_groups:
            if self.validate_qr_pattern(group):
                qr_code = self.safe_reconstruct_qr_code(group, scale)
                if qr_code:
                    # 计算综合置信度
                    confidence = self.calculate_comprehensive_confidence(group)
                    qr_code['confidence'] = confidence
                    qr_code['scale'] = scale
                    validated.append(qr_code)
        
        return validated
    
    def find_qr_pattern_groups(self, candidates: List[Dict]) -> List[List[Dict]]:
        """寻找QR码模式组"""
        groups = []
        
        # 基于空间距离和相似性分组
        for i in range(len(candidates)):
            for j in range(i + 1, len(candidates)):
                for k in range(j + 1, len(candidates)):
                    group = [candidates[i], candidates[j], candidates[k]]
                    
                    # 检查三个候选区域是否构成QR码模式
                    if self.is_valid_triplet(group):
                        groups.append(group)
        
        return groups
    
    def is_valid_triplet(self, group: List[Dict]) -> bool:
        """检查三个区域是否构成有效的三元组"""
        if len(group) != 3:
            return False
        
        # 面积相似性检查
        areas = [c['features']['area'] for c in group]
        area_ratio = max(areas) / min(areas)
        if area_ratio > 2.0:
            return False
        
        # 空间关系检查
        centers = [c['center'] for c in group]
        
        # 检查是否形成近似直角三角形
        return self.is_approximate_right_triangle(centers)
    
    def is_approximate_right_triangle(self, points: List[Tuple[float, float]]) -> bool:
        """检查是否近似直角三角形"""
        if len(points) != 3:
            return False
        
        # 计算所有边长
        distances = []
        for i in range(3):
            for j in range(i + 1, 3):
                dist = math.sqrt(
                    (points[i][0] - points[j][0])**2 + 
                    (points[i][1] - points[j][1])**2
                )
                distances.append(dist)
        
        distances.sort()
        
        # 检查勾股定理（宽松条件）
        a2, b2, c2 = distances[0]**2, distances[1]**2, distances[2]**2
        return abs(c2 - (a2 + b2)) < max(a2, b2) * 0.5
    
    def validate_qr_pattern(self, group: List[Dict]) -> bool:
        """验证QR码模式"""
        if len(group) != 3:
            return False
        
        # 综合验证：几何特征 + 空间关系
        geometric_valid = all(self.geometric_validation(c) for c in group)
        spatial_valid = self.is_approximate_right_triangle([c['center'] for c in group])
        
        return geometric_valid and spatial_valid
    
    def geometric_validation(self, candidate: Dict) -> bool:
        """几何验证"""
        features = candidate['features']
        
        conditions = [
            features['rectangularity'] > 0.7,
            features['solidity'] > 0.8,
            features['aspect_ratio'] < 2.5
        ]
        
        return all(conditions)
    
    def safe_reconstruct_qr_code(self, group: List[Dict], scale: float) -> Optional[Dict]:
        """安全的重建QR码 - 修复凸包问题"""
        try:
            # 获取三个位置探测图形的中心点
            centers = [c['center'] for c in group]
            
            # 确保点集有效
            if len(centers) != 3:
                return None
            
            # 创建numpy数组，确保数据类型正确
            points = np.array(centers, dtype=np.float32)
            
            # 检查点集是否有效
            if points.size == 0 or np.any(np.isnan(points)) or np.any(np.isinf(points)):
                return None
            
            # 安全地计算凸包
            if len(points) >= 3:
                try:
                    hull = cv2.convexHull(points)
                    if hull is None or len(hull) == 0:
                        # 如果凸包计算失败，使用最小边界矩形
                        rect = cv2.minAreaRect(points)
                        box = cv2.boxPoints(rect)
                    else:
                        # 使用凸包计算边界矩形
                        rect = cv2.minAreaRect(hull)
                        box = cv2.boxPoints(rect)
                except Exception as e:
                    print(f"凸包计算失败，使用备选方案: {e}")
                    # 备选方案：直接使用点集的边界矩形
                    rect = cv2.minAreaRect(points)
                    box = cv2.boxPoints(rect)
            else:
                # 点不足，无法计算凸包
                return None
            
            # 确保box是有效的
            if box is None or len(box) == 0:
                return None
            
            # 转换为整数列表
            box = np.int0(box).tolist()
            
            # 估算QR码版本
            estimated_version = self.estimate_qr_version(group, scale)
            
            qr_code = {
                'bounding_box': box,
                'center_points': centers,
                'contours': [c['contour'].tolist() for c in group],
                'features': [c['features'] for c in group],
                'estimated_version': estimated_version,
                'scale': scale
            }
            
            return qr_code
            
        except Exception as e:
            print(f"安全重建QR码失败: {e}")
            return None
    
    def estimate_qr_version(self, group: List[Dict], scale: float) -> int:
        """估算QR码版本"""
        avg_area = np.mean([c['features']['area'] for c in group])
        base_area = avg_area / (scale ** 2)
        
        if base_area < 500:
            return 1
        elif base_area < 1000:
            return 2
        elif base_area < 2000:
            return 3
        else:
            return 4
    
    def calculate_comprehensive_confidence(self, group: List[Dict]) -> float:
        """计算综合置信度"""
        confidences = []
        
        # 1. 几何特征置信度
        geometric_conf = np.mean([c['features']['rectangularity'] for c in group])
        confidences.append(geometric_conf)
        
        # 2. 空间关系置信度
        centers = [c['center'] for c in group]
        spatial_conf = self.calculate_spatial_confidence(centers)
        confidences.append(spatial_conf)
        
        # 3. 面积一致性置信度
        areas = [c['features']['area'] for c in group]
        area_conf = 1.0 - (np.std(areas) / np.mean(areas)) if np.mean(areas) > 0 else 0
        confidences.append(max(0, area_conf))
        
        # 4. 形状规则性置信度
        shape_conf = np.mean([c['features']['solidity'] for c in group])
        confidences.append(shape_conf)
        
        return float(np.mean(confidences))
    
    def calculate_spatial_confidence(self, centers: List[Tuple[float, float]]) -> float:
        """计算空间关系置信度"""
        distances = []
        for i in range(3):
            for j in range(i + 1, 3):
                dist = math.sqrt(
                    (centers[i][0] - centers[j][0])**2 + 
                    (centers[i][1] - centers[j][1])**2
                )
                distances.append(dist)
        
        # 检查直角关系
        distances.sort()
        a2, b2, c2 = distances[0]**2, distances[1]**2, distances[2]**2
        
        # 计算与直角三角形的相似度
        right_triangle_similarity = 1.0 - min(1.0, abs(c2 - (a2 + b2)) / max(a2, b2))
        
        return right_triangle_similarity
    
    def merge_detections(self, detections: List[Dict]) -> List[Dict]:
        """合并检测结果（去重）"""
        if not detections:
            return []
        
        # 简单的基于距离的合并
        merged = []
        used = set()
        
        for i in range(len(detections)):
            if i in used:
                continue
                
            current = detections[i]
            current_centers = current['center_points']
            
            # 查找相近的检测结果
            overlapping = [current]
            for j in range(i + 1, len(detections)):
                if j in used:
                    continue
                    
                other = detections[j]
                other_centers = other['center_points']
                
                if self.are_detections_similar(current_centers, other_centers):
                    overlapping.append(other)
                    used.add(j)
            
            # 合并重叠的检测结果
            if len(overlapping) > 1:
                merged_detection = self.merge_similar_detections(overlapping)
                merged.append(merged_detection)
            else:
                merged.append(current)
            
            used.add(i)
        
        return merged
    
    def are_detections_similar(self, centers1: List, centers2: List) -> bool:
        """检查两个检测结果是否相似"""
        if len(centers1) != 3 or len(centers2) != 3:
            return False
        
        # 计算中心点之间的平均距离
        total_distance = 0
        for c1, c2 in zip(centers1, centers2):
            distance = math.sqrt((c1[0]-c2[0])**2 + (c1[1]-c2[1])**2)
            total_distance += distance
        
        avg_distance = total_distance / 3
        return avg_distance < 50  # 阈值可根据图像尺寸调整
    
    def merge_similar_detections(self, detections: List[Dict]) -> Dict:
        """合并相似的检测结果"""
        # 选择置信度最高的检测结果
        best_detection = max(detections, key=lambda x: x['confidence'])
        
        # 更新合并信息
        best_detection['merged_count'] = len(detections)
        best_detection['original_detections'] = len(detections)
        
        return best_detection
    
    def assess_image_quality(self, image: np.ndarray) -> Dict[str, float]:
        """评估图像质量"""
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        
        # 计算图像质量指标
        blurriness = self.assess_blur(gray)
        contrast = self.assess_contrast(gray)
        brightness = self.assess_brightness(gray)
        
        return {
            'blurriness': blurriness,
            'contrast': contrast,
            'brightness': brightness,
            'quality_score': (contrast + (1 - blurriness)) / 2
        }
    
    def assess_blur(self, image: np.ndarray) -> float:
        """评估图像模糊度"""
        laplacian_var = cv2.Laplacian(image, cv2.CV_64F).var()
        blur_score = min(1.0, laplacian_var / 1000.0)
        return 1.0 - blur_score
    
    def assess_contrast(self, image: np.ndarray) -> float:
        """评估对比度"""
        std = np.std(image)
        return min(1.0, std / 128.0)
    
    def assess_brightness(self, image: np.ndarray) -> float:
        """评估亮度"""
        mean_brightness = np.mean(image)
        brightness_score = 1.0 - abs(mean_brightness - 128) / 128.0
        return max(0.0, brightness_score)
    
    def update_performance_stats(self, success: bool, processing_time: float):
        """更新性能统计"""
        self.performance_stats['total_frames'] += 1
        if success:
            self.performance_stats['successful_detections'] += 1
        
        # 更新平均处理时间
        alpha = 0.1
        current_avg = self.performance_stats['average_processing_time']
        new_avg = alpha * processing_time + (1 - alpha) * current_avg
        self.performance_stats['average_processing_time'] = new_avg

class RealTimeVisualization:
    """实时可视化类"""
    
    def __init__(self):
        self.color_palette = {
            'bounding_box': (0, 255, 0),
            'center_points': (255, 0, 0), 
            'contours': (0, 0, 255),
            'text': (255, 255, 255),
            'info_background': (0, 0, 0)
        }
    
    def draw_detection_result(self, image: np.ndarray, result: DetectionResult) -> np.ndarray:
        """绘制检测结果"""
        display_image = image.copy()
        
        # 绘制每个检测到的QR码
        for i, qr_code in enumerate(result.qr_codes):
            display_image = self.draw_single_qr_code(display_image, qr_code, i)
        
        # 绘制统计信息
        display_image = self.draw_statistics(display_image, result)
        
        return display_image
    
    def draw_single_qr_code(self, image: np.ndarray, qr_code: Dict, index: int) -> np.ndarray:
        """绘制单个QR码"""
        try:
            # 绘制边界框
            bbox = np.array(qr_code['bounding_box'], dtype=np.int32)
            cv2.polylines(image, [bbox], True, self.color_palette['bounding_box'], 2)
            
            # 绘制中心点
            for center in qr_code['center_points']:
                center_int = (int(center[0]), int(center[1]))
                cv2.circle(image, center_int, 5, self.color_palette['center_points'], -1)
            
            # 添加标签
            label = f"QR {index+1} (conf: {qr_code['confidence']:.2f})"
            center_x = int(np.mean(bbox[:, 0]))
            center_y = int(np.mean(bbox[:, 1]))
            
            # 标签背景
            text_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)[0]
            cv2.rectangle(image, 
                         (center_x - text_size[0]//2 - 5, center_y - text_size[1] - 5),
                         (center_x + text_size[0]//2 + 5, center_y + 5),
                         self.color_palette['info_background'], -1)
            
            # 标签文字
            cv2.putText(image, label, 
                       (center_x - text_size[0]//2, center_y), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, self.color_palette['text'], 2)
            
        except Exception as e:
            print(f"绘制QR码失败: {e}")
        
        return image
    
    def draw_statistics(self, image: np.ndarray, result: DetectionResult) -> np.ndarray:
        """绘制统计信息"""
        stats_text = [
            f"Processing: {result.processing_time*1000:.1f}ms",
            f"QR Codes: {len(result.qr_codes)}",
            f"Quality: {result.image_metrics['quality_score']:.2f}",
        ]
        
        y_offset = 30
        for text in stats_text:
            cv2.putText(image, text, (10, y_offset), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, self.color_palette['text'], 2)
            y_offset += 25
        
        return image

def create_realistic_test_image() -> np.ndarray:
    """创建更真实的测试图像"""
    # 创建背景
    image = np.ones((480, 640, 3), dtype=np.uint8) * 200
    
    # 创建模拟的QR码位置探测图形（三个实心方块）
    # QR码位置探测图形的典型比例是 1:1:3:1:1
    def draw_finder_pattern(img, x, y, size):
        # 外层黑框
        cv2.rectangle(img, (x, y), (x+size*7, y+size*7), (0, 0, 0), -1)
        # 中间白框
        cv2.rectangle(img, (x+size, y+size), (x+size*6, y+size*6), (255, 255, 255), -1)
        # 内层黑框
        cv2.rectangle(img, (x+size*2, y+size*2), (x+size*5, y+size*5), (0, 0, 0), -1)
    
    # 绘制三个位置探测图形（模拟QR码）
    draw_finder_pattern(image, 100, 100, 5)  # 左上
    draw_finder_pattern(image, 400, 100, 5)  # 右上
    draw_finder_pattern(image, 100, 300, 5)  # 左下
    
    # 添加一些噪声
    noise = np.random.randint(0, 30, (480, 640, 3), dtype=np.uint8)
    image = cv2.add(image, noise)
    
    # 轻微高斯模糊
    image = cv2.GaussianBlur(image, (3, 3), 0.5)
    
    return image

def robust_demo():
    """鲁棒性演示函数"""
    print("启动鲁棒性QR码检测系统...")
    
    # 创建检测器和可视化工具
    detector = RobustQRDetector()
    visualizer = RealTimeVisualization()
    
    # 生成测试图像
    test_image = create_realistic_test_image()
    
    # 执行检测
    print("执行多尺度检测...")
    result = detector.multi_scale_detection(test_image)
    
    # 显示结果
    print(f"检测结果: {result.success}")
    print(f"处理时间: {result.processing_time*1000:.2f}ms")
    print(f"检测到 {len(result.qr_codes)} 个QR码")
    print(f"图像质量评分: {result.image_metrics['quality_score']:.2f}")
    
    # 可视化
    display_image = visualizer.draw_detection_result(test_image, result)
    cv2.imshow('Robust QR Code Detection', display_image)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
    
    # 显示性能统计
    print("\n性能统计:")
    print(f"总帧数: {detector.performance_stats['total_frames']}")
    print(f"成功检测: {detector.performance_stats['successful_detections']}")
    print(f"平均处理时间: {detector.performance_stats['average_processing_time']*1000:.2f}ms")
    
    return result

# 嵌入式优化版本
class EmbeddedQRDetector:
    """嵌入式QR码检测器"""
    
    def __init__(self):
        self.detector = RobustQRDetector({
            'min_contour_area': 30,
            'max_contour_area': 50000,
            'scale_levels': [0.5, 0.75, 1.0],
            'confidence_threshold': 0.3,
            'max_candidates': 30,
            'enable_multi_scale': True,
            'enable_perspective_correction': False
        })
    
    def process_frame(self, frame: np.ndarray) -> Dict[str, Any]:
        """处理单帧图像"""
        # 预处理优化
        processed_frame = self.preprocess_for_embedded(frame)
        
        # 执行检测
        result = self.detector.multi_scale_detection(processed_frame)
        
        # 优化输出格式
        return self.format_embedded_output(result)
    
    def preprocess_for_embedded(self, frame: np.ndarray) -> np.ndarray:
        """嵌入式预处理"""
        # 降采样
        frame = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)
        
        # 转换为灰度
        if len(frame.shape) == 3:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        return frame
    
    def format_embedded_output(self, result: DetectionResult) -> Dict[str, Any]:
        """格式化嵌入式输出"""
        embedded_result = {
            'detected': result.success,
            'count': len(result.qr_codes),
            'processing_ms': int(result.processing_time * 1000),
            'positions': []
        }
        
        for qr in result.qr_codes:
            bbox_center = self.calculate_bounding_box_center(qr['bounding_box'])
            embedded_result['positions'].append({
                'center': bbox_center,
                'confidence': qr['confidence']
            })
            
        return embedded_result
    
    def calculate_bounding_box_center(self, bbox: List) -> Tuple[float, float]:
        """计算边界框中心"""
        points = np.array(bbox)
        center_x = np.mean(points[:, 0])
        center_y = np.mean(points[:, 1])
        return (float(center_x), float(center_y))

if __name__ == "__main__":
    # 运行鲁棒性演示
    result = robust_demo()
    
    # 测试嵌入式版本
    print("\n测试嵌入式版本:")
    embedded_detector = EmbeddedQRDetector()
    test_image = create_realistic_test_image()
    embedded_result = embedded_detector.process_frame(test_image)
    
    print(f"嵌入式结果: {json.dumps(embedded_result, indent=2)}")