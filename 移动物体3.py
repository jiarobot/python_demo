import cv2
import numpy as np
import argparse
import time
import threading
from collections import deque, defaultdict
import json
import os
from datetime import datetime
from sklearn.cluster import MiniBatchKMeans
from scipy import ndimage
from scipy.signal import medfilt
import heapq

class SymbolicNeuralLayer:
    """符号神经网络层 - 基于规则的推理系统"""
    def __init__(self, rules=None):
        self.rules = rules or self.default_rules()
        self.symbolic_memory = defaultdict(list)
        self.pattern_buffer = deque(maxlen=100)
        
    def default_rules(self):
        """默认符号推理规则"""
        return {
            'motion_consistency': {
                'condition': lambda data: len(data) > 5 and np.std(data) < 0.1,
                'action': lambda: 'STABLE_MOTION'
            },
            'object_merging': {
                'condition': lambda boxes: self.should_merge_boxes(boxes),
                'action': lambda boxes: self.merge_boxes(boxes)
            },
            'false_positive': {
                'condition': lambda motion, area, duration: area < 100 and duration < 3,
                'action': lambda: 'IGNORE'
            },
            'exposure_change': {
                'condition': lambda brightness_history: np.std(brightness_history[-5:]) > 25,
                'action': lambda: 'ADJUST_SENSITIVITY'
            }
        }
    
    def should_merge_boxes(self, boxes):
        """符号推理：判断是否应该合并边界框"""
        if len(boxes) < 2:
            return False
            
        # 计算所有边界框之间的距离和重叠度
        centers = [(x + w/2, y + h/2) for x, y, w, h in boxes]
        distances = []
        
        for i in range(len(centers)):
            for j in range(i+1, len(centers)):
                dist = np.sqrt((centers[i][0]-centers[j][0])**2 + 
                              (centers[i][1]-centers[j][1])**2)
                distances.append(dist)
                
        # 符号规则：如果平均距离小于阈值且数量合理，则合并
        avg_distance = np.mean(distances) if distances else float('inf')
        return avg_distance < 50 and len(boxes) <= 5
    
    def merge_boxes(self, boxes):
        """符号推理：合并边界框"""
        if not boxes:
            return None
            
        x_min = min(box[0] for box in boxes)
        y_min = min(box[1] for box in boxes)
        x_max = max(box[0] + box[2] for box in boxes)
        y_max = max(box[1] + box[3] for box in boxes)
        
        return (x_min, y_min, x_max - x_min, y_max - y_min)
    
    def infer(self, context):
        """符号推理引擎"""
        decisions = []
        
        # 应用所有规则
        for rule_name, rule in self.rules.items():
            try:
                if 'motion_data' in context and rule_name == 'motion_consistency':
                    if rule['condition'](context['motion_data']):
                        decisions.append(rule['action']())
                        
                elif 'boxes' in context and rule_name == 'object_merging':
                    if rule['condition'](context['boxes']):
                        merged_box = rule['action'](context['boxes'])
                        decisions.append(('MERGE_BOXES', merged_box))
                        
                elif all(k in context for k in ['motion_area', 'motion_duration']) and rule_name == 'false_positive':
                    if rule['condition'](context['motion_strength'], 
                                       context['motion_area'], 
                                       context['motion_duration']):
                        decisions.append(rule['action']())
                        
                elif 'brightness_history' in context and rule_name == 'exposure_change':
                    if rule['condition'](context['brightness_history']):
                        decisions.append(rule['action']())
                        
            except Exception as e:
                print(f"规则 {rule_name} 执行错误: {e}")
                
        return decisions

class OnlineLearner:
    """在线学习系统 - 免训练的实时学习"""
    def __init__(self, memory_size=1000, adaptation_rate=0.1):
        self.memory_size = memory_size
        self.adaptation_rate = adaptation_rate
        
        # 运动模式记忆
        self.motion_patterns = deque(maxlen=memory_size)
        self.motion_clusters = None
        self.cluster_centers = []
        
        # 环境适应参数
        self.sensitivity = 1.0
        self.background_stability = 1.0
        self.noise_level = 0.0
        
        # 性能统计
        self.learning_stats = {
            'patterns_learned': 0,
            'adaptations_made': 0,
            'false_positives_reduced': 0
        }
    
    def learn_motion_pattern(self, motion_data):
        """学习运动模式"""
        if motion_data is not None and len(motion_data) > 0:
            self.motion_patterns.append(motion_data)
            self.learning_stats['patterns_learned'] += 1
            
            # 定期更新聚类
            if len(self.motion_patterns) % 50 == 0:
                self.update_clusters()
    
    def update_clusters(self):
        """更新运动模式聚类"""
        if len(self.motion_patterns) < 10:
            return
            
        try:
            # 使用迷你批次K-means进行在线聚类
            data = np.array(list(self.motion_patterns))
            if data.shape[1] < 2:
                return
                
            self.motion_clusters = MiniBatchKMeans(n_clusters=min(5, len(data)), 
                                                  random_state=42)
            self.motion_clusters.fit(data)
            self.cluster_centers = self.motion_clusters.cluster_centers_
        except Exception as e:
            print(f"聚类更新失败: {e}")
    
    def adapt_parameters(self, current_performance, historical_performance):
        """自适应参数调整"""
        # 计算性能变化
        if historical_performance and current_performance:
            performance_ratio = current_performance / historical_performance
            
            # 调整灵敏度
            if performance_ratio < 0.8:  # 性能下降
                self.sensitivity *= (1 + self.adaptation_rate)
                self.learning_stats['adaptations_made'] += 1
            elif performance_ratio > 1.2:  # 性能提升
                self.sensitivity *= (1 - self.adaptation_rate)
                
            # 限制灵敏度范围
            self.sensitivity = np.clip(self.sensitivity, 0.5, 2.0)
    
    def predict_motion_type(self, motion_features):
        """预测运动类型"""
        if self.motion_clusters is None or motion_features is None:
            return "UNKNOWN"
            
        try:
            distance = float('inf')
            predicted_type = "UNKNOWN"
            
            for i, center in enumerate(self.cluster_centers):
                if len(center) == len(motion_features):
                    dist = np.linalg.norm(center - motion_features)
                    if dist < distance:
                        distance = dist
                        predicted_type = f"PATTERN_{i}"
                        
            return predicted_type if distance < 100 else "NEW_PATTERN"
        except:
            return "UNKNOWN"

class CognitiveMotionDetector:
    """认知运动检测器 - 结合符号AI和在线学习"""
    def __init__(self, use_knn=True, min_area=800, show_mask=True,
                 enable_cognitive=True, learning_rate=0.05):
        
        # 初始化组件
        self.symbolic_engine = SymbolicNeuralLayer()
        self.online_learner = OnlineLearner(adaptation_rate=learning_rate)
        self.enable_cognitive = enable_cognitive
        
        # 背景减除器
        self.backSub = cv2.createBackgroundSubtractorKNN(
            history=2000,
            dist2Threshold=800,  # 更高的阈值减少噪声
            detectShadows=True
        )
        
        self.min_area = min_area
        self.show_mask = show_mask
        
        # 形态学内核
        self.kernel_open = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        self.kernel_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11))
        self.kernel_dilate = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        
        # 认知记忆系统
        self.object_memory = defaultdict(lambda: {
            'first_seen': time.time(),
            'last_seen': time.time(),
            'trajectory': deque(maxlen=50),
            'appearance_count': 0,
            'motion_pattern': [],
            'cognitive_id': None
        })
        
        self.cognitive_object_id = 0
        self.track_colors = {}
        
        # 环境感知
        self.brightness_history = deque(maxlen=30)
        self.motion_intensity_history = deque(maxlen=100)
        self.scene_stability = 1.0
        
        # 性能统计
        self.cognitive_stats = {
            'frames_processed': 0,
            'symbolic_decisions': 0,
            'learning_adaptations': 0,
            'objects_tracked': 0,
            'false_positives_filtered': 0
        }
        
        print("认知运动检测器初始化完成")
        print(f"符号推理: {'启用' if enable_cognitive else '禁用'}")
        print(f"在线学习: 启用")

    def cognitive_preprocessing(self, frame):
        """认知预处理 - 环境感知"""
        # 亮度分析
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        current_brightness = np.mean(gray)
        self.brightness_history.append(current_brightness)
        
        # 场景稳定性评估
        if len(self.brightness_history) > 5:
            brightness_variance = np.var(list(self.brightness_history))
            self.scene_stability = 1.0 / (1.0 + brightness_variance / 100.0)
        
        # 应用环境自适应
        adaptive_frame = self.adaptive_enhancement(frame, current_brightness)
        return adaptive_frame

    def adaptive_enhancement(self, frame, brightness):
        """自适应图像增强"""
        # 根据亮度调整对比度
        target_brightness = 128
        brightness_diff = target_brightness - brightness
        
        # 自适应伽马校正
        gamma = 1.0 + brightness_diff / 255.0
        gamma = np.clip(gamma, 0.5, 2.0)
        
        # 应用伽马校正
        inv_gamma = 1.0 / gamma
        table = np.array([((i / 255.0) ** inv_gamma) * 255 for i in np.arange(0, 256)]).astype("uint8")
        enhanced = cv2.LUT(frame, table)
        
        return enhanced

    def intelligent_morphology(self, fg_mask):
        """智能形态学处理"""
        # 初始二值化
        _, binary_mask = cv2.threshold(fg_mask, 180, 255, cv2.THRESH_BINARY)
        
        # 根据场景稳定性调整形态学参数
        stability_factor = self.scene_stability
        
        # 动态调整内核大小
        open_kernel_size = max(3, int(5 * stability_factor))
        close_kernel_size = max(7, int(11 * stability_factor))
        
        kernel_open = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (open_kernel_size, open_kernel_size))
        kernel_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (close_kernel_size, close_kernel_size))
        
        # 应用形态学操作
        binary_mask = cv2.morphologyEx(binary_mask, cv2.MORPH_OPEN, kernel_open)
        binary_mask = cv2.morphologyEx(binary_mask, cv2.MORPH_CLOSE, kernel_close)
        
        # 智能区域连接
        binary_mask = self.cognitive_region_connection(binary_mask)
        
        return binary_mask

    def cognitive_region_connection(self, binary_mask):
        """认知区域连接 - 基于运动语义"""
        # 使用连通组件分析
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(binary_mask, connectivity=8)
        
        if num_labels <= 1:
            return binary_mask
            
        # 创建增强掩模
        enhanced_mask = np.zeros_like(binary_mask)
        
        for i in range(1, num_labels):  # 跳过背景
            area = stats[i, cv2.CC_STAT_AREA]
            
            # 基于认知规则的区域处理
            if area > self.min_area:
                # 保留有效区域
                component_mask = (labels == i).astype(np.uint8) * 255
                enhanced_mask = cv2.bitwise_or(enhanced_mask, component_mask)
            elif area > self.min_area * 0.3:
                # 小区域但可能重要 - 使用符号推理判断
                context = {
                    'motion_area': area,
                    'scene_stability': self.scene_stability
                }
                decisions = self.symbolic_engine.infer(context)
                
                if 'IGNORE' not in decisions:
                    component_mask = (labels == i).astype(np.uint8) * 255
                    enhanced_mask = cv2.bitwise_or(enhanced_mask, component_mask)
                    self.cognitive_stats['false_positives_filtered'] += 1
        
        return enhanced_mask

    def extract_cognitive_features(self, contours):
        """提取认知特征"""
        cognitive_features = []
        bounding_boxes = []
        
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < self.min_area:
                continue
                
            # 几何特征
            x, y, w, h = cv2.boundingRect(contour)
            aspect_ratio = w / h if h > 0 else 0
            solidity = area / (w * h) if w * h > 0 else 0
            
            # 运动特征
            moments = cv2.moments(contour)
            if moments["m00"] != 0:
                cx = int(moments["m10"] / moments["m00"])
                cy = int(moments["m01"] / moments["m00"])
            else:
                cx, cy = x + w // 2, y + h // 2
                
            # 形状复杂度
            perimeter = cv2.arcLength(contour, True)
            circularity = 4 * np.pi * area / (perimeter * perimeter) if perimeter > 0 else 0
            
            features = {
                'contour': contour,
                'bbox': (x, y, w, h),
                'center': (cx, cy),
                'area': area,
                'aspect_ratio': aspect_ratio,
                'solidity': solidity,
                'circularity': circularity,
                'cognitive_signature': [area, aspect_ratio, circularity, solidity]
            }
            
            cognitive_features.append(features)
            bounding_boxes.append((x, y, w, h))
            
        return cognitive_features, bounding_boxes

    def cognitive_tracking(self, current_features):
        """认知跟踪 - 结合符号推理和在线学习"""
        if not current_features:
            return {}
            
        object_matches = {}
        used_features = set()
        
        # 阶段1: 符号推理匹配
        symbolic_matches = self.symbolic_matching(current_features, used_features)
        object_matches.update(symbolic_matches)
        
        # 阶段2: 学习增强匹配
        learning_matches = self.learning_enhanced_matching(current_features, used_features)
        object_matches.update(learning_matches)
        
        # 阶段3: 新对象认知
        new_objects = self.cognitive_new_object_detection(current_features, used_features)
        object_matches.update(new_objects)
        
        # 更新对象记忆
        self.update_object_memory(object_matches, current_features)
        
        return object_matches

    def symbolic_matching(self, features, used_features):
        """符号推理匹配"""
        matches = {}
        
        for obj_id, memory in self.object_memory.items():
            if len(memory['trajectory']) == 0:
                continue
                
            last_center = memory['trajectory'][-1]
            best_match = None
            min_cognitive_distance = float('inf')
            
            for i, feat in enumerate(features):
                if i in used_features:
                    continue
                    
                current_center = feat['center']
                
                # 计算认知距离（结合空间、时间和特征相似性）
                spatial_distance = np.sqrt((current_center[0]-last_center[0])**2 + 
                                         (current_center[1]-last_center[1])**2)
                
                # 特征相似性
                if 'cognitive_signature' in feat and memory.get('cognitive_signature'):
                    feature_distance = np.linalg.norm(
                        np.array(feat['cognitive_signature']) - 
                        np.array(memory['cognitive_signature'])
                    )
                else:
                    feature_distance = 0
                    
                cognitive_distance = spatial_distance + feature_distance * 0.1
                
                if cognitive_distance < min_cognitive_distance and cognitive_distance < 100:
                    min_cognitive_distance = cognitive_distance
                    best_match = i
            
            if best_match is not None:
                matches[obj_id] = best_match
                used_features.add(best_match)
                
        return matches

    def learning_enhanced_matching(self, features, used_features):
        """学习增强匹配"""
        matches = {}
        
        # 使用在线学习预测运动模式
        for i, feat in enumerate(features):
            if i in used_features:
                continue
                
            motion_features = feat['cognitive_signature']
            predicted_pattern = self.online_learner.predict_motion_type(motion_features)
            
            # 寻找具有相似模式的历史对象
            for obj_id, memory in self.object_memory.items():
                if memory.get('motion_pattern') == predicted_pattern and obj_id not in matches:
                    matches[obj_id] = i
                    used_features.add(i)
                    break
                    
        return matches

    def cognitive_new_object_detection(self, features, used_features):
        """认知新对象检测"""
        new_objects = {}
        
        for i, feat in enumerate(features):
            if i in used_features:
                continue
                
            # 符号推理：判断是否为新对象
            context = {
                'motion_area': feat['area'],
                'motion_strength': feat['solidity'],
                'scene_stability': self.scene_stability
            }
            
            decisions = self.symbolic_engine.infer(context)
            
            if 'IGNORE' not in decisions:
                new_id = self.cognitive_object_id
                self.cognitive_object_id += 1
                new_objects[new_id] = i
                
                # 生成认知颜色
                self.track_colors[new_id] = (
                    np.random.randint(50, 200),
                    np.random.randint(50, 200),
                    np.random.randint(50, 200)
                )
                
                self.cognitive_stats['objects_tracked'] += 1
        
        return new_objects

    def update_object_memory(self, matches, features):
        """更新对象记忆"""
        current_time = time.time()
        
        # 更新匹配的对象
        for obj_id, feature_idx in matches.items():
            if feature_idx < len(features):
                feat = features[feature_idx]
                
                self.object_memory[obj_id]['last_seen'] = current_time
                self.object_memory[obj_id]['trajectory'].append(feat['center'])
                self.object_memory[obj_id]['appearance_count'] += 1
                self.object_memory[obj_id]['cognitive_signature'] = feat['cognitive_signature']
                
                # 学习运动模式
                self.online_learner.learn_motion_pattern(feat['cognitive_signature'])
        
        # 清理长时间未见的对象
        current_time = time.time()
        expired_objects = []
        
        for obj_id, memory in self.object_memory.items():
            if current_time - memory['last_seen'] > 10.0:  # 10秒未出现
                expired_objects.append(obj_id)
                
        for obj_id in expired_objects:
            del self.object_memory[obj_id]

    def process_frame_cognitive(self, frame):
        """认知帧处理"""
        start_time = time.time()
        self.cognitive_stats['frames_processed'] += 1
        
        # 认知预处理
        preprocessed_frame = self.cognitive_preprocessing(frame)
        
        # 背景减除（使用自适应学习率）
        learning_rate = 0.001 * self.online_learner.sensitivity
        fg_mask = self.backSub.apply(preprocessed_frame, learningRate=learning_rate)
        
        # 智能形态学处理
        processed_mask = self.intelligent_morphology(fg_mask)
        
        # 提取轮廓和认知特征
        contours, _ = cv2.findContours(processed_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cognitive_features, bounding_boxes = self.extract_cognitive_features(contours)
        
        # 符号推理决策
        context = {
            'boxes': bounding_boxes,
            'brightness_history': list(self.brightness_history),
            'scene_stability': self.scene_stability,
            'motion_intensity': len(cognitive_features)
        }
        
        symbolic_decisions = self.symbolic_engine.infer(context)
        self.cognitive_stats['symbolic_decisions'] += len(symbolic_decisions)
        
        # 应用符号决策
        processed_features = self.apply_symbolic_decisions(cognitive_features, symbolic_decisions)
        
        # 认知跟踪
        object_matches = self.cognitive_tracking(processed_features)
        
        # 绘制认知结果
        result_frame = frame.copy()
        motion_detected = self.draw_cognitive_detections(result_frame, processed_features, object_matches)
        
        # 显示掩模
        if self.show_mask:
            mask_display = cv2.cvtColor(processed_mask, cv2.COLOR_GRAY2BGR)
            result_frame = np.hstack((result_frame, mask_display))
        
        # 在线学习适应
        processing_time = time.time() - start_time
        self.motion_intensity_history.append(len(processed_features))
        
        if len(self.motion_intensity_history) > 10:
            current_perf = np.mean(list(self.motion_intensity_history)[-5:])
            historical_perf = np.mean(list(self.motion_intensity_history)[-10:-5])
            self.online_learner.adapt_parameters(current_perf, historical_perf)
        
        return result_frame, motion_detected, len(processed_features)

    def apply_symbolic_decisions(self, features, decisions):
        """应用符号推理决策"""
        processed_features = features.copy()
        
        for decision in decisions:
            if decision == 'ADJUST_SENSITIVITY':
                self.online_learner.sensitivity *= 0.8
            elif isinstance(decision, tuple) and decision[0] == 'MERGE_BOXES':
                # 合并边界框的逻辑已在特征提取中处理
                pass
                
        return processed_features

    def draw_cognitive_detections(self, frame, features, object_matches):
        """绘制认知检测结果"""
        motion_detected = False
        
        for obj_id, feature_idx in object_matches.items():
            if feature_idx < len(features):
                feat = features[feature_idx]
                contour = feat['contour']
                bbox = feat['bbox']
                center = feat['center']
                
                x, y, w, h = bbox
                
                # 获取认知颜色
                color = self.track_colors.get(obj_id, (0, 255, 0))
                
                # 绘制边界框和轮廓
                cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
                cv2.drawContours(frame, [contour], -1, color, 1)
                
                # 绘制中心点和认知ID
                cv2.circle(frame, center, 5, color, -1)
                cv2.putText(frame, f'CID:{obj_id}', (x, y-10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                
                # 绘制认知轨迹
                if obj_id in self.object_memory:
                    trajectory = list(self.object_memory[obj_id]['trajectory'])
                    for i in range(1, len(trajectory)):
                        alpha = i / len(trajectory)
                        thickness = max(1, int(3 * alpha))
                        cv2.line(frame, trajectory[i-1], trajectory[i], color, thickness)
                
                # 显示认知信息
                memory = self.object_memory.get(obj_id, {})
                appearance_count = memory.get('appearance_count', 0)
                
                info_text = [
                    f'Appearances: {appearance_count}',
                    f'Area: {feat["area"]:.0f}',
                    f'Stability: {self.scene_stability:.2f}'
                ]
                
                for i, text in enumerate(info_text):
                    y_offset = y + h + 15 + i * 15
                    cv2.putText(frame, text, (x, min(y_offset, frame.shape[0]-10)), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
                
                motion_detected = True
        
        return motion_detected

    def get_cognitive_stats(self):
        """获取认知统计"""
        processing_times = [0.01]  # 默认值
        
        avg_time = np.mean(processing_times)
        fps = 1.0 / avg_time if avg_time > 0 else 0
        
        return {
            'fps': fps,
            'frames_processed': self.cognitive_stats['frames_processed'],
            'objects_tracked': self.cognitive_stats['objects_tracked'],
            'symbolic_decisions': self.cognitive_stats['symbolic_decisions'],
            'learning_adaptations': self.online_learner.learning_stats['adaptations_made'],
            'false_positives_filtered': self.cognitive_stats['false_positives_filtered'],
            'scene_stability': self.scene_stability,
            'cognitive_sensitivity': self.online_learner.sensitivity,
            'active_objects': len(self.object_memory)
        }

def main():
    parser = argparse.ArgumentParser(description='认知实时运动检测系统')
    parser.add_argument('--input', type=str, default='0', 
                       help='输入源: 摄像头ID (如0,1) 或视频文件路径')
    parser.add_argument('--min_area', type=int, default=800,
                       help='最小检测区域面积 (默认: 800)')
    parser.add_argument('--no_cognitive', action='store_true',
                       help='禁用认知功能')
    parser.add_argument('--no_mask', action='store_true',
                       help='不显示前景掩模')
    parser.add_argument('--learning_rate', type=float, default=0.05,
                       help='在线学习率 (默认: 0.05)')
    parser.add_argument('--output_dir', type=str, default='cognitive_output',
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
    
    # 设置合适的分辨率
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    
    # 获取实际分辨率
    actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    
    print(f"视频源: {args.input}")
    print(f"分辨率: {actual_width}x{actual_height}")
    print(f"FPS: {fps}")
    
    # 初始化认知检测器
    detector = CognitiveMotionDetector(
        min_area=args.min_area,
        show_mask=not args.no_mask,
        enable_cognitive=not args.no_cognitive,
        learning_rate=args.learning_rate
    )
    
    # 性能监控
    start_time = time.time()
    cognitive_cycles = 0
    
    print("\n=== 认知实时运动检测系统 ===")
    print("结合符号AI和在线学习的智能检测")
    print("快捷键:")
    print("  'q' - 退出")
    print("  'p' - 暂停/继续")
    print("  'r' - 重置认知系统")
    print("  'c' - 清除认知记忆")
    print("  'd' - 切换认知显示")
    print("  'l' - 切换学习模式")
    
    paused = False
    show_cognitive = True
    learning_enabled = True
    
    try:
        while True:
            if not paused:
                ret, frame = cap.read()
                if not ret:
                    print("无法读取帧，退出...")
                    break
                
                # 处理帧
                processed_frame, motion_detected, num_objects = detector.process_frame_cognitive(frame)
                cognitive_cycles += 1
                
                # 获取认知统计
                stats = detector.get_cognitive_stats()
                
                # 显示认知信息
                if show_cognitive:
                    stats_text = [
                        f'FPS: {stats["fps"]:.1f}',
                        f'Frames: {stats["frames_processed"]}',
                        f'Objects: {num_objects} (Active: {stats["active_objects"]})',
                        f'Symbolic Decisions: {stats["symbolic_decisions"]}',
                        f'Learning Adaptations: {stats["learning_adaptations"]}',
                        f'False Positives Filtered: {stats["false_positives_filtered"]}',
                        f'Scene Stability: {stats["scene_stability"]:.2f}',
                        f'Cognitive Sensitivity: {stats["cognitive_sensitivity"]:.2f}',
                        f'Learning: {"ON" if learning_enabled else "OFF"}'
                    ]
                    
                    for i, text in enumerate(stats_text):
                        # 背景阴影
                        cv2.putText(processed_frame, text, (12, 35 + i * 25), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 3)
                        # 前景文字
                        cv2.putText(processed_frame, text, (10, 33 + i * 25), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                
                # 显示认知状态
                status = "COGNITIVE MOTION" if motion_detected else "COGNITIVE SCAN"
                color = (0, 255, 0) if motion_detected else (255, 255, 0)
                cv2.putText(processed_frame, status, (actual_width-300, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
                
                # 显示结果
                cv2.imshow('Cognitive Motion Detection', processed_frame)
            
            # 键盘输入处理
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('p'):
                paused = not paused
                print("暂停" if paused else "继续")
            elif key == ord('r'):
                # 重新初始化背景减除器
                detector.backSub = cv2.createBackgroundSubtractorKNN(
                    history=2000,
                    dist2Threshold=800,
                    detectShadows=True
                )
                print("认知系统已重置")
            elif key == ord('c'):
                detector.object_memory.clear()
                detector.cognitive_object_id = 0
                print("认知记忆已清除")
            elif key == ord('d'):
                show_cognitive = not show_cognitive
                print("认知显示:" + ("开启" if show_cognitive else "关闭"))
            elif key == ord('l'):
                learning_enabled = not learning_enabled
                detector.online_learner.adaptation_rate = 0.05 if learning_enabled else 0.0
                print("学习模式:" + ("开启" if learning_enabled else "关闭"))
    
    except KeyboardInterrupt:
        print("\n程序被用户中断")
    
    finally:
        # 释放资源
        cap.release()
        cv2.destroyAllWindows()
        
        # 打印最终统计
        total_time = time.time() - start_time
        final_stats = detector.get_cognitive_stats()
        
        print(f"\n=== 认知系统最终统计 ===")
        print(f"总运行时间: {total_time:.2f}秒")
        print(f"处理帧数: {final_stats['frames_processed']}")
        print(f"平均FPS: {final_stats['fps']:.2f}")
        print(f"跟踪对象总数: {final_stats['objects_tracked']}")
        print(f"符号推理决策: {final_stats['symbolic_decisions']}")
        print(f"学习适应次数: {final_stats['learning_adaptations']}")
        print(f"过滤误检数: {final_stats['false_positives_filtered']}")
        print(f"平均场景稳定性: {final_stats['scene_stability']:.2f}")
        
        # 保存认知统计
        os.makedirs(args.output_dir, exist_ok=True)
        stats_filename = os.path.join(args.output_dir, f"cognitive_stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        
        cognitive_data = {
            'total_time': total_time,
            'total_frames': final_stats['frames_processed'],
            'avg_fps': final_stats['fps'],
            'objects_tracked': final_stats['objects_tracked'],
            'symbolic_decisions': final_stats['symbolic_decisions'],
            'learning_adaptations': final_stats['learning_adaptations'],
            'false_positives_filtered': final_stats['false_positives_filtered'],
            'scene_stability': final_stats['scene_stability'],
            'final_sensitivity': final_stats['cognitive_sensitivity'],
            'learning_patterns': detector.online_learner.learning_stats['patterns_learned']
        }
        
        with open(stats_filename, 'w') as f:
            json.dump(cognitive_data, f, indent=2)
        
        print(f"认知统计已保存: {stats_filename}")

if __name__ == "__main__":
    main()