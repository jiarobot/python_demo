import cv2
import numpy as np
import argparse
import time
from collections import deque, defaultdict
import json
import os
from datetime import datetime
from scipy import ndimage
import math

class AdvancedMotionDetector:
    def __init__(self, min_area=800, show_mask=True, enable_tracking=True,
                 use_advanced_math=True, temporal_stability=True):
        """
        高级运动检测器 - 结合数学方法和智能过滤
        """
        self.min_area = min_area
        self.show_mask = show_mask
        self.enable_tracking = enable_tracking
        self.use_advanced_math = use_advanced_math
        self.temporal_stability = temporal_stability
        
        # 多背景减除器融合
        self.backSub_knn = cv2.createBackgroundSubtractorKNN(
            history=500, dist2Threshold=400, detectShadows=True)
        self.backSub_mog2 = cv2.createBackgroundSubtractorMOG2(
            history=500, varThreshold=16, detectShadows=True)
        
        # 数学形态学内核
        self.kernel_small = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        self.kernel_medium = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        self.kernel_large = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11))
        
        # 跟踪和记忆
        self.track_history = defaultdict(lambda: deque(maxlen=30))
        self.object_memory = defaultdict(dict)
        self.next_id = 0
        self.track_colors = {}
        
        # 高级数学分析
        self.entropy_history = deque(maxlen=20)
        self.fourier_analysis = deque(maxlen=10)
        
        # 时间稳定性分析
        self.frame_buffer = deque(maxlen=5)
        self.stability_scores = deque(maxlen=50)
        
        # 性能优化
        self.processing_times = deque(maxlen=30)
        self.frame_count = 0
        
        # 统计
        self.stats = {
            'total_frames': 0,
            'stable_motion_frames': 0,
            'detected_objects': 0,
            'filtered_noise': 0
        }

    def calculate_entropy(self, image):
        """计算图像熵 - 信息论应用"""
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
            
        # 计算直方图
        hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
        hist = hist.ravel() / hist.sum()
        
        # 计算熵
        entropy = -np.sum(hist * np.log2(hist + 1e-10))
        return float(entropy)  # 确保返回Python float

    def temporal_consistency_filter(self, current_mask, consistency_frames=3):
        """时间一致性过滤 - 减少瞬态噪声"""
        self.frame_buffer.append(current_mask)
        
        if len(self.frame_buffer) < consistency_frames:
            return current_mask
            
        # 计算多帧一致性
        consistent_mask = np.zeros_like(current_mask)
        for mask in self.frame_buffer:
            consistent_mask = cv2.bitwise_or(consistent_mask, mask)
        
        # 只保留在多数帧中出现的区域
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        consistent_mask = cv2.morphologyEx(consistent_mask, cv2.MORPH_OPEN, kernel)
        
        return consistent_mask

    def mathematical_morphology_advanced(self, fg_mask):
        """高级数学形态学处理"""
        # 1. 初始二值化
        _, binary = cv2.threshold(fg_mask, 200, 255, cv2.THRESH_BINARY)
        
        # 2. 基于拓扑分析的形态学操作
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(binary, connectivity=8)
        
        if num_labels <= 1:
            return binary
            
        # 3. 基于组件大小的自适应形态学
        refined_mask = np.zeros_like(binary)
        
        for i in range(1, num_labels):  # 跳过背景
            area = stats[i, cv2.CC_STAT_AREA]
            
            if area < self.min_area:
                continue
                
            # 提取单个组件
            component_mask = (labels == i).astype(np.uint8) * 255
            
            # 根据组件特性选择形态学操作
            if area < self.min_area * 3:
                # 小区域 - 强过滤
                processed = cv2.morphologyEx(component_mask, cv2.MORPH_OPEN, self.kernel_medium)
                processed = cv2.morphologyEx(processed, cv2.MORPH_CLOSE, self.kernel_small)
            else:
                # 大区域 - 保持细节
                processed = cv2.morphologyEx(component_mask, cv2.MORPH_OPEN, self.kernel_small)
                processed = cv2.morphologyEx(processed, cv2.MORPH_CLOSE, self.kernel_medium)
            
            # 应用区域生长细化
            if np.sum(processed) > 0:
                refined_component = self.region_growing_refinement(processed)
                refined_mask = cv2.bitwise_or(refined_mask, refined_component)
        
        return refined_mask

    def region_growing_refinement(self, mask):
        """区域生长细化 - 改进边界准确性"""
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            return mask
            
        # 找到最大轮廓
        main_contour = max(contours, key=cv2.contourArea)
        
        # 创建精确掩模
        refined = np.zeros_like(mask)
        cv2.drawContours(refined, [main_contour], -1, 255, -1)
        
        return refined

    def multi_background_fusion(self, frame):
        """多背景模型融合"""
        # KNN背景减除
        fg_mask_knn = self.backSub_knn.apply(frame)
        
        # MOG2背景减除
        fg_mask_mog2 = self.backSub_mog2.apply(frame)
        
        # 融合两个掩模
        _, binary_knn = cv2.threshold(fg_mask_knn, 200, 255, cv2.THRESH_BINARY)
        _, binary_mog2 = cv2.threshold(fg_mask_mog2, 200, 255, cv2.THRESH_BINARY)
        
        # 逻辑与操作 - 只有两个模型都检测到的区域才保留
        fused_mask = cv2.bitwise_and(binary_knn, binary_mog2)
        
        # 补充检测：如果一个模型检测到大区域而另一个没有
        contours_knn, _ = cv2.findContours(binary_knn, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        contours_mog2, _ = cv2.findContours(binary_mog2, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        large_areas_knn = [c for c in contours_knn if cv2.contourArea(c) > self.min_area * 2]
        large_areas_mog2 = [c for c in contours_mog2 if cv2.contourArea(c) > self.min_area * 2]
        
        # 如果有一个模型检测到大区域，添加到融合掩模
        for contour in large_areas_knn + large_areas_mog2:
            if cv2.contourArea(contour) > self.min_area * 2:
                temp_mask = np.zeros_like(fused_mask)
                cv2.drawContours(temp_mask, [contour], -1, 255, -1)
                fused_mask = cv2.bitwise_or(fused_mask, temp_mask)
        
        return fused_mask

    def intelligent_contour_analysis(self, binary_mask):
        """智能轮廓分析 - 减少小杂框"""
        contours, _ = cv2.findContours(binary_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            return [], []
        
        # 第一阶段：基本过滤
        filtered_contours = []
        bounding_boxes = []
        
        for contour in contours:
            area = cv2.contourArea(contour)
            
            # 面积过滤
            if area < self.min_area:
                self.stats['filtered_noise'] += 1
                continue
                
            # 形状分析过滤
            x, y, w, h = cv2.boundingRect(contour)
            aspect_ratio = w / h if h > 0 else 0
            
            # 过滤极端长宽比
            if aspect_ratio < 0.1 or aspect_ratio > 10:
                continue
                
            # 紧凑性分析
            perimeter = cv2.arcLength(contour, True)
            if perimeter > 0:
                circularity = 4 * np.pi * area / (perimeter * perimeter)
                # 过滤过于不规则的形状
                if circularity < 0.1:
                    continue
            
            filtered_contours.append(contour)
            
            # 计算改进的边界框
            rect = cv2.minAreaRect(contour)
            box = cv2.boxPoints(rect)
            box = np.int0(box)
            
            moments = cv2.moments(contour)
            if moments["m00"] != 0:
                cx = int(moments["m10"] / moments["m00"])
                cy = int(moments["m01"] / moments["m00"])
            else:
                cx, cy = x + w // 2, y + h // 2
                
            bounding_boxes.append({
                'contour': contour,
                'bbox_rect': (x, y, w, h),  # 传统矩形
                'bbox_rotated': box,        # 旋转矩形
                'center': (cx, cy),
                'area': area,
                'aspect_ratio': aspect_ratio
            })
        
        # 第二阶段：轮廓合并（减少小杂框）
        merged_boxes = self.contour_merging(bounding_boxes)
        
        return filtered_contours, merged_boxes

    def contour_merging(self, boxes):
        """轮廓合并算法 - 减少过度分割"""
        if len(boxes) <= 1:
            return boxes
            
        merged = []
        used = set()
        
        for i, box1 in enumerate(boxes):
            if i in used:
                continue
                
            current_group = [box1]
            used.add(i)
            
            for j, box2 in enumerate(boxes):
                if j in used or i == j:
                    continue
                    
                # 判断是否应该合并
                if self.should_merge_boxes(box1, box2):
                    current_group.append(box2)
                    used.add(j)
            
            # 合并组内框
            if len(current_group) > 1:
                merged_box = self.merge_box_group(current_group)
                merged.append(merged_box)
            else:
                merged.append(box1)
        
        # 添加未合并的框
        for i, box in enumerate(boxes):
            if i not in used:
                merged.append(box)
                
        return merged

    def should_merge_boxes(self, box1, box2):
        """判断两个框是否应该合并"""
        x1, y1, w1, h1 = box1['bbox_rect']
        x2, y2, w2, h2 = box2['bbox_rect']
        
        # 计算中心距离
        center1 = box1['center']
        center2 = box2['center']
        distance = np.sqrt((center1[0]-center2[0])**2 + (center1[1]-center2[1])**2)
        
        # 计算重叠度
        overlap_x = max(0, min(x1+w1, x2+w2) - max(x1, x2))
        overlap_y = max(0, min(y1+h1, y2+h2) - max(y1, y2))
        overlap_area = overlap_x * overlap_y
        
        min_area = min(box1['area'], box2['area'])
        
        # 合并条件：距离近或重叠，且面积相似
        distance_threshold = min(w1, h1, w2, h2) * 2
        area_similarity = abs(box1['area'] - box2['area']) / min_area < 3.0
        
        return (distance < distance_threshold or overlap_area > 0) and area_similarity

    def advanced_tracking(self, current_boxes):
        """高级跟踪算法"""
        if not self.enable_tracking or not current_boxes:
            return {}
            
        object_matches = {}
        used_indices = set()
        
        # 卡尔曼滤波预测（简化版）
        for obj_id, history in list(self.track_history.items()):
            if len(history) > 0:
                last_center = history[-1]
                
                # 预测当前位置（简单线性预测）
                if len(history) > 1:
                    prev_center = history[-2]
                    velocity = (last_center[0]-prev_center[0], last_center[1]-prev_center[1])
                    predicted_center = (last_center[0]+velocity[0], last_center[1]+velocity[1])
                else:
                    predicted_center = last_center
                
                best_match = None
                min_distance = float('inf')
                
                for i, box in enumerate(current_boxes):
                    if i in used_indices:
                        continue
                        
                    current_center = box['center']
                    distance = np.sqrt((current_center[0]-predicted_center[0])**2 + 
                                     (current_center[1]-predicted_center[1])**2)
                    
                    # 动态阈值
                    threshold = 100 + 50 * (1.0 - self.get_stability_score())
                    if distance < min_distance and distance < threshold:
                        min_distance = distance
                        best_match = i
                
                if best_match is not None:
                    object_matches[obj_id] = best_match
                    used_indices.add(best_match)
                    self.track_history[obj_id].append(current_boxes[best_match]['center'])
        
        # 新对象检测
        for i, box in enumerate(current_boxes):
            if i not in used_indices:
                # 稳定性检查
                if self.is_stable_detection(box):
                    new_id = self.next_id
                    self.next_id += 1
                    object_matches[new_id] = i
                    self.track_history[new_id].append(box['center'])
                    self.track_colors[new_id] = (
                        np.random.randint(50, 200),
                        np.random.randint(50, 200),
                        np.random.randint(50, 200)
                    )
        
        self.cleanup_tracks()
        return object_matches

    def get_stability_score(self):
        """获取稳定性评分"""
        if len(self.stability_scores) == 0:
            return 1.0
        return float(np.mean(list(self.stability_scores)))  # 转换为Python float

    def is_stable_detection(self, box):
        """判断检测是否稳定"""
        area = box['area']
        x, y, w, h = box['bbox_rect']
        
        # 面积检查
        if area < self.min_area * 1.5:
            return False
            
        # 边界检查
        if x < 5 or y < 5:
            return False
            
        return True

    def cleanup_tracks(self):
        """清理丢失的轨迹"""
        current_time = time.time()
        lost_tracks = []
        
        for obj_id in list(self.track_history.keys()):
            if len(self.track_history[obj_id]) == 0:
                lost_tracks.append(obj_id)
        
        for obj_id in lost_tracks:
            del self.track_history[obj_id]
            if obj_id in self.track_colors:
                del self.track_colors[obj_id]

    def process_frame_advanced(self, frame):
        """高级帧处理"""
        start_time = time.time()
        self.frame_count += 1
        
        # 1. 高级数学分析（如果启用）
        if self.use_advanced_math:
            entropy = self.calculate_entropy(frame)
            self.entropy_history.append(entropy)
        
        # 2. 多背景模型融合
        fused_mask = self.multi_background_fusion(frame)
        
        # 3. 高级数学形态学处理
        processed_mask = self.mathematical_morphology_advanced(fused_mask)
        
        # 4. 时间一致性过滤（如果启用）
        if self.temporal_stability:
            processed_mask = self.temporal_consistency_filter(processed_mask)
        
        # 5. 智能轮廓分析
        contours, boxes = self.intelligent_contour_analysis(processed_mask)
        
        # 6. 高级跟踪
        object_matches = self.advanced_tracking(boxes)
        
        # 7. 绘制结果
        result_frame = frame.copy()
        motion_detected = self.draw_advanced_detections(result_frame, boxes, object_matches)
        
        # 8. 显示掩模
        if self.show_mask:
            mask_display = cv2.cvtColor(processed_mask, cv2.COLOR_GRAY2BGR)
            
            # 在掩模上绘制检测结果
            for box in boxes:
                x, y, w, h = box['bbox_rect']
                cv2.rectangle(mask_display, (x, y), (x + w, y + h), (0, 255, 0), 1)
            
            # 调整大小匹配
            if mask_display.shape != result_frame.shape:
                mask_display = cv2.resize(mask_display, 
                                        (result_frame.shape[1], result_frame.shape[0]))
            result_frame = np.hstack((result_frame, mask_display))
        
        # 9. 更新统计
        processing_time = time.time() - start_time
        self.processing_times.append(processing_time)
        
        self.stats['total_frames'] += 1
        if motion_detected and len(boxes) > 0:
            self.stats['stable_motion_frames'] += 1
        self.stats['detected_objects'] = len(boxes)
        
        # 更新稳定性评分
        stability = 1.0 - (len(boxes) / 20.0)  # 简化稳定性计算
        self.stability_scores.append(min(1.0, max(0.0, stability)))
        
        return result_frame, motion_detected, len(boxes)

    def draw_advanced_detections(self, frame, boxes, object_matches):
        """绘制高级检测结果"""
        motion_detected = False
        
        for obj_id, box_idx in object_matches.items():
            if box_idx < len(boxes):
                box_data = boxes[box_idx]
                
                # 获取跟踪颜色
                color = self.track_colors.get(obj_id, (0, 255, 0))
                
                # 确保x和y变量被定义 - 从bbox_rect获取
                x, y, w, h = box_data['bbox_rect']
                
                # 绘制旋转边界框 - 添加安全检查
                if 'bbox_rotated' in box_data:
                    rotated_box = box_data['bbox_rotated']
                    # 检查旋转边界框是否有效
                    if rotated_box is not None and len(rotated_box) > 0:
                        try:
                            cv2.drawContours(frame, [rotated_box], 0, color, 2)
                        except cv2.error as e:
                            print(f"绘制旋转边界框错误: {e}")
                            # 回退到绘制矩形边界框
                            cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
                    else:
                        # 如果旋转边界框无效，使用矩形边界框
                        cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
                else:
                    # 如果没有旋转边界框，使用矩形边界框
                    cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
                
                # 绘制中心点和ID
                center = box_data['center']
                cv2.circle(frame, center, 4, color, -1)
                cv2.putText(frame, f'ID:{obj_id}', (x, y-10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                
                # 绘制轨迹
                if obj_id in self.track_history:
                    points = list(self.track_history[obj_id])
                    for i in range(1, len(points)):
                        alpha = i / len(points)
                        thickness = max(1, int(3 * alpha))
                        cv2.line(frame, points[i-1], points[i], color, thickness)
                
                # 显示高级信息
                info_text = [
                    f'Area: {box_data["area"]:.0f}',
                    f'Stability: {self.get_stability_score():.2f}'
                ]
                
                for i, text in enumerate(info_text):
                    y_offset = y + h + 15 + i * 15
                    cv2.putText(frame, text, (x, min(y_offset, frame.shape[0]-10)), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
                
                motion_detected = True
        
        return motion_detected

    def merge_box_group(self, box_group):
        """合并框组 - 修复旋转边界框生成"""
        all_contours = [box['contour'] for box in box_group]
        all_points = np.vstack(all_contours)
        
        # 创建合并后的轮廓
        if len(all_points) >= 3:  # 至少需要3个点来计算凸包
            merged_contour = cv2.convexHull(all_points)
        else:
            # 如果点太少，使用第一个框的轮廓
            merged_contour = box_group[0]['contour']
        
        # 计算新特征
        area = sum(box['area'] for box in box_group)
        x, y, w, h = cv2.boundingRect(merged_contour)
        
        moments = cv2.moments(merged_contour)
        if moments["m00"] != 0:
            cx = int(moments["m10"] / moments["m00"])
            cy = int(moments["m01"] / moments["m00"])
        else:
            cx, cy = x + w // 2, y + h // 2
        
        # 安全地生成旋转边界框
        try:
            rotated_rect = cv2.minAreaRect(merged_contour)
            rotated_box = cv2.boxPoints(rotated_rect)
            rotated_box = np.int0(rotated_box)
        except:
            # 如果生成旋转边界框失败，使用矩形边界框
            rotated_box = np.array([[x, y], [x+w, y], [x+w, y+h], [x, y+h]], dtype=np.int32)
        
        return {
            'contour': merged_contour,
            'bbox_rect': (x, y, w, h),
            'bbox_rotated': rotated_box,
            'center': (cx, cy),
            'area': area,
            'aspect_ratio': w / h if h > 0 else 0,
            'merged': True
        }

    def get_advanced_stats(self):
        """获取高级统计 - 修复JSON序列化问题"""
        if len(self.processing_times) > 0:
            avg_time = np.mean(self.processing_times)
            fps = 1.0 / avg_time if avg_time > 0 else 0
        else:
            avg_time = 0
            fps = 0
            
        # 确保所有值都是Python原生类型
        entropy_value = 0.0
        if self.entropy_history:
            entropy_value = float(np.mean(list(self.entropy_history)))
            
        stability_score = float(self.get_stability_score())
        
        return {
            'fps': float(fps),
            'avg_processing_time_ms': float(avg_time * 1000),
            'total_frames': int(self.stats['total_frames']),
            'stable_motion_frames': int(self.stats['stable_motion_frames']),
            'motion_ratio': float((self.stats['stable_motion_frames'] / self.stats['total_frames'] * 100) 
                            if self.stats['total_frames'] > 0 else 0),
            'current_objects': int(self.stats['detected_objects']),
            'filtered_noise': int(self.stats['filtered_noise']),
            'stability_score': stability_score,
            'active_tracks': int(len(self.track_history)),
            'entropy': entropy_value
        }

def convert_to_serializable(obj):
    """将对象转换为JSON可序列化的格式"""
    if isinstance(obj, (np.float32, np.float64)):
        return float(obj)
    elif isinstance(obj, (np.int32, np.int64)):
        return int(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {key: convert_to_serializable(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_to_serializable(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(convert_to_serializable(item) for item in obj)
    else:
        return obj

def main():
    parser = argparse.ArgumentParser(description='高级实时运动检测系统')
    parser.add_argument('--input', type=str, default='0', 
                       help='输入源: 摄像头ID (如0,1) 或视频文件路径')
    parser.add_argument('--min_area', type=int, default=800,
                       help='最小检测区域面积 (默认: 800)')
    parser.add_argument('--no_mask', action='store_true',
                       help='不显示前景掩模')
    parser.add_argument('--no_tracking', action='store_true',
                       help='禁用物体跟踪')
    parser.add_argument('--no_advanced_math', action='store_true',
                       help='禁用高级数学方法')
    parser.add_argument('--no_temporal_stability', action='store_true',
                       help='禁用时间稳定性分析')
    parser.add_argument('--output_dir', type=str, default='advanced_output',
                       help='输出目录')
    
    args = parser.parse_args()
    
    # 初始化视频源
    try:
        input_source = int(args.input)
    except ValueError:
        input_source = args.input
    
    cap = cv2.VideoCapture(input_source)
    
    if not cap.isOpened():
        print(f"错误: 无法打开视频源 {args.input}")
        return
    
    # 设置分辨率
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    
    # 获取实际分辨率
    actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    
    print(f"视频源: {args.input}")
    print(f"分辨率: {actual_width}x{actual_height}")
    print(f"FPS: {fps}")
    
    # 初始化高级检测器
    detector = AdvancedMotionDetector(
        min_area=args.min_area,
        show_mask=not args.no_mask,
        enable_tracking=not args.no_tracking,
        use_advanced_math=not args.no_advanced_math,
        temporal_stability=not args.no_temporal_stability
    )
    
    # 性能监控
    start_time = time.time()
    
    print("\n=== 高级实时运动检测系统 ===")
    print("结合高级数学方法和智能过滤")
    print("快捷键:")
    print("  'q' - 退出")
    print("  'p' - 暂停/继续")
    print("  'r' - 重置检测器")
    print("  'c' - 清除跟踪")
    print("  's' - 保存当前帧")
    print("  'm' - 切换数学方法显示")
    
    paused = False
    show_math_info = True
    
    # 创建输出目录
    os.makedirs(args.output_dir, exist_ok=True)
    
    try:
        while True:
            if not paused:
                ret, frame = cap.read()
                if not ret:
                    print("无法读取帧，退出...")
                    break
                
                # 处理帧
                processed_frame, motion_detected, num_objects = detector.process_frame_advanced(frame)
                
                # 获取统计信息
                stats = detector.get_advanced_stats()
                
                # 显示统计信息
                if show_math_info:
                    stats_text = [
                        f'FPS: {stats["fps"]:.1f}',
                        f'Process: {stats["avg_processing_time_ms"]:.1f}ms',
                        f'Frames: {stats["total_frames"]}',
                        f'Stable Motion: {stats["stable_motion_frames"]} ({stats["motion_ratio"]:.1f}%)',
                        f'Objects: {stats["current_objects"]}',
                        f'Filtered Noise: {stats["filtered_noise"]}',
                        f'Stability: {stats["stability_score"]:.2f}',
                        f'Entropy: {stats["entropy"]:.2f}',
                        f'Active Tracks: {stats["active_tracks"]}'
                    ]
                    
                    for i, text in enumerate(stats_text):
                        # 背景阴影
                        cv2.putText(processed_frame, text, (12, 35 + i * 25), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 3)
                        # 前景文字
                        cv2.putText(processed_frame, text, (10, 33 + i * 25), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                
                # 显示状态
                status = "ADVANCED MOTION" if motion_detected else "STABLE SCENE"
                color = (0, 255, 0) if motion_detected else (255, 255, 0)
                cv2.putText(processed_frame, status, (actual_width-300, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
                
                # 显示分辨率信息
                res_text = f'Resolution: {actual_width}x{actual_height} | Min Area: {args.min_area}'
                cv2.putText(processed_frame, res_text, (10, actual_height-10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                
                # 显示结果
                cv2.imshow('Advanced Motion Detection', processed_frame)
            
            # 键盘输入处理
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('p'):
                paused = not paused
                print("暂停" if paused else "继续")
            elif key == ord('r'):
                detector.backSub_knn = cv2.createBackgroundSubtractorKNN(
                    history=500, dist2Threshold=400, detectShadows=True)
                detector.backSub_mog2 = cv2.createBackgroundSubtractorMOG2(
                    history=500, varThreshold=16, detectShadows=True)
                print("检测器已重置")
            elif key == ord('c'):
                detector.track_history.clear()
                detector.next_id = 0
                print("跟踪已清除")
            elif key == ord('s'):
                # 保存当前帧
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                filename = os.path.join(args.output_dir, f"advanced_frame_{timestamp}.jpg")
                cv2.imwrite(filename, processed_frame)
                print(f"帧已保存: {filename}")
            elif key == ord('m'):
                show_math_info = not show_math_info
                print("数学信息显示:" + ("开启" if show_math_info else "关闭"))
    
    except KeyboardInterrupt:
        print("\n程序被用户中断")
    
    finally:
        # 释放资源
        cap.release()
        cv2.destroyAllWindows()
        
        # 打印最终统计
        total_time = time.time() - start_time
        final_stats = detector.get_advanced_stats()
        
        print(f"\n=== 高级检测最终统计 ===")
        print(f"总运行时间: {total_time:.2f}秒")
        print(f"处理帧数: {final_stats['total_frames']}")
        print(f"平均FPS: {final_stats['fps']:.2f}")
        print(f"稳定运动帧数: {final_stats['stable_motion_frames']}")
        print(f"稳定运动比例: {final_stats['motion_ratio']:.2f}%")
        print(f"过滤噪声数: {final_stats['filtered_noise']}")
        print(f"平均稳定性: {final_stats['stability_score']:.2f}")
        print(f"平均熵: {final_stats['entropy']:.2f}")
        
        # 保存统计信息 - 使用转换函数确保可序列化
        stats_filename = os.path.join(args.output_dir, f"advanced_stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        
        # 准备统计数据
        stats_data = {
            'total_time': float(total_time),
            'total_frames': int(final_stats['total_frames']),
            'stable_motion_frames': int(final_stats['stable_motion_frames']),
            'motion_ratio': float(final_stats['motion_ratio']),
            'avg_fps': float(final_stats['fps']),
            'filtered_noise': int(final_stats['filtered_noise']),
            'avg_stability': float(final_stats['stability_score']),
            'avg_entropy': float(final_stats['entropy']),
            'min_area': int(args.min_area),
            'resolution': f"{actual_width}x{actual_height}"
        }
        
        # 转换为可序列化格式
        serializable_stats = convert_to_serializable(stats_data)
        
        with open(stats_filename, 'w') as f:
            json.dump(serializable_stats, f, indent=2)
        
        print(f"高级统计已保存: {stats_filename}")

if __name__ == "__main__":
    main()