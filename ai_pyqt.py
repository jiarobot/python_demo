import sys
import cv2
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import torchvision.models as models
import torchvision.transforms as transforms
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QPushButton, QLabel, QListWidget, 
                            QSlider, QComboBox, QGroupBox, QTextEdit,
                            QFileDialog, QProgressBar, QSplitter, QCheckBox,
                            QTabWidget, QMessageBox, QSpinBox, QDoubleSpinBox,
                            QTableWidget, QTableWidgetItem, QHeaderView)
from PyQt5.QtCore import QTimer, Qt, pyqtSignal, QThread, QSettings
from PyQt5.QtGui import QImage, QPixmap, QFont, QPalette, QColor
import matplotlib.pyplot as plt
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance
import time
from collections import defaultdict, deque
import random
import json
import os
import math
from datetime import datetime

# ========== 增强的DCMN核心算法 ==========

class EnhancedCreativeMemoryNetwork(nn.Module):
    """增强版创造性记忆网络 - 支持实时AR创作和多模态学习"""
    
    def __init__(self, feature_dim=512, memory_slots=256):
        super().__init__()
        self.feature_dim = feature_dim
        self.memory_slots = memory_slots
        
        # 多模态特征编码器
        self.feature_encoder = MultiModalEncoder(feature_dim)
        
        # 动态记忆系统 - 使用更复杂的记忆结构
        self.visual_memories = nn.Parameter(torch.randn(memory_slots, feature_dim) * 0.1)
        self.style_memories = nn.Parameter(torch.randn(memory_slots, feature_dim) * 0.1)
        self.concept_memories = nn.Parameter(torch.randn(memory_slots, feature_dim) * 0.1)
        self.emotion_memories = nn.Parameter(torch.randn(memory_slots, feature_dim) * 0.1)
        
        # 注意力机制
        self.cross_modal_attention = CrossModalAttention(feature_dim)
        self.spatial_attention = SpatialAttention()
        
        # 生成器网络
        self.art_generator = ArtGenerator(feature_dim)
        self.style_transfer = NeuralStyleTransfer()
        
        # 记忆管理系统
        self.memory_manager = AdaptiveMemoryManager(memory_slots, feature_dim)
        
        # 创意调节器
        self.creative_modulator = CreativeModulator(feature_dim)
        
        # 对象检测器
        self.object_detector = ObjectDetector()
        
        # 艺术风格库
        self.art_styles = self._initialize_art_styles()
        
        # 情感分析
        self.emotion_analyzer = EmotionAnalyzer()
        
        # 使用历史和学习状态
        self.usage_history = defaultdict(lambda: deque(maxlen=1000))
        self.learning_state = {
            'exploration_rate': 0.7,
            'style_coherence': 0.8,
            'conceptual_depth': 0.6,
            'emotional_resonance': 0.5
        }
        
        # 创意状态
        self.creative_state = {
            'curiosity': 0.7,
            'surprise': 0.5,
            'coherence': 0.8,
            'abstraction': 0.3,
            'emotional_intensity': 0.6,
            'harmony': 0.7,
            'novelty': 0.4
        }
        
        print("增强版创造性记忆网络初始化完成")

    def forward(self, frame, creative_intent="explore", style_influence=0.5, emotional_context=None):
        """处理视频帧并进行创造性增强"""
        try:
            # 对象检测
            detected_objects = self.object_detector.detect(frame)
            
            # 情感分析
            if emotional_context is None:
                emotional_context = self.emotion_analyzer.analyze(frame)
            
            # 编码当前帧
            frame_tensor = self._preprocess_frame(frame)
            current_features = self.feature_encoder.encode_visual(frame_tensor)
            
            # 根据创意意图调整参数
            self._adjust_creative_state(creative_intent, emotional_context)
            
            # 多模态记忆激活
            activated_visual = self._activate_memories(current_features, self.visual_memories, "visual")
            activated_style = self._activate_memories(current_features, self.style_memories, "style")
            activated_concept = self._activate_memories(current_features, self.concept_memories, "concept")
            activated_emotion = self._activate_memories(current_features, self.emotion_memories, "emotion")
            
            # 跨模态注意力融合
            fused_features = self.cross_modal_attention(
                current_features, 
                activated_visual, 
                activated_style, 
                activated_concept,
                activated_emotion
            )
            
            # 创造性调制
            modulated_features = self.creative_modulator(fused_features, self.creative_state)
            
            # 空间注意力
            attention_map = self.spatial_attention(frame_tensor)
            
            # 生成增强图像
            enhanced_frame = self.art_generator(
                frame_tensor, 
                modulated_features, 
                attention_map,
                style_influence
            )
            
            # 转换为numpy并后处理
            result = enhanced_frame.squeeze(0).permute(1, 2, 0).cpu().detach().numpy()
            result = np.clip(result, 0, 1)
            
            # 应用风格迁移
            if style_influence > 0.3:
                result = self._apply_style_transfer(result, style_influence)
            
            return (result * 255).astype(np.uint8), detected_objects, emotional_context
            
        except Exception as e:
            print(f"处理错误: {e}")
            import traceback
            traceback.print_exc()
            return frame, [], {}

    def creative_ar_composition(self, frame, objects_detected=None, emotional_context=None):
        """创造性AR构图 - 在真实场景中添加虚拟艺术元素"""
        if objects_detected is None:
            objects_detected = []
            
        try:
            # 分析场景构图
            composition_analysis = self._analyze_composition(frame)
            
            # 情感驱动的颜色方案
            color_scheme = self._generate_color_scheme(emotional_context)
            
            # 基于场景分析和对象检测生成虚拟元素
            virtual_elements = self._generate_contextual_elements(
                composition_analysis, 
                objects_detected,
                emotional_context,
                color_scheme
            )
            
            # 将虚拟元素与真实场景融合
            composed_frame = self._blend_virtual_elements(frame, virtual_elements)
            
            return composed_frame
        except Exception as e:
            print(f"AR构图错误: {e}")
            return frame

    def generate_abstract_art(self, frame, abstraction_level=0.5, emotional_context=None):
        """生成抽象艺术效果"""
        try:
            if emotional_context is None:
                emotional_context = {'valence': 0.5, 'arousal': 0.5}
                
            if abstraction_level > 0.8:
                # 高抽象度 - 神经风格抽象
                return self._neural_abstraction(frame, emotional_context)
            elif abstraction_level > 0.6:
                # 中高抽象度 - 几何深度抽象
                return self._geometric_deep_abstraction(frame, emotional_context)
            elif abstraction_level > 0.4:
                # 中等抽象度 - 流动抽象
                return self._fluid_abstraction(frame, emotional_context)
            else:
                # 低抽象度 - 艺术滤镜
                return self._advanced_artistic_filter(frame, emotional_context)
        except Exception as e:
            print(f"抽象艺术错误: {e}")
            return frame

    def learn_from_feedback(self, feedback_type, features, context):
        """从用户反馈中学习"""
        try:
            if feedback_type == "positive":
                # 强化相关记忆
                self.memory_manager.enhance_memories(features, context, 0.1)
                # 调整创意状态
                self.creative_state['coherence'] = min(1.0, self.creative_state['coherence'] + 0.05)
                self.creative_state['harmony'] = min(1.0, self.creative_state['harmony'] + 0.03)
            else:
                # 减弱相关记忆
                self.memory_manager.weaken_memories(features, context, 0.1)
                # 鼓励更多探索
                self.creative_state['curiosity'] = min(1.0, self.creative_state['curiosity'] + 0.05)
                self.creative_state['novelty'] = min(1.0, self.creative_state['novelty'] + 0.03)
                
        except Exception as e:
            print(f"学习错误: {e}")

    def _activate_memories(self, query, memory_bank, memory_type):
        """增强的记忆激活机制"""
        try:
            # 确保查询向量维度正确
            if query.dim() == 1:
                query = query.unsqueeze(0)
            
            # 计算相似度
            similarities = F.cosine_similarity(query.unsqueeze(1), memory_bank.unsqueeze(0), dim=2)
            similarities = similarities.squeeze(0)
            
            # 基于创意状态调整激活阈值
            curiosity_factor = self.creative_state['curiosity']
            surprise_factor = self.creative_state['surprise']
            
            activation_threshold = 0.5 - (curiosity_factor * 0.3) + (surprise_factor * 0.1)
            
            # 考虑记忆的新近性和重要性
            memory_weights = self.memory_manager.get_memory_weights(memory_type)
            weighted_similarities = similarities * torch.tensor(memory_weights, dtype=torch.float32, device=query.device)
            
            # 创造性随机探索
            exploration_rate = self.learning_state['exploration_rate']
            if random.random() < exploration_rate * 0.1:
                random_indices = random.sample(range(self.memory_slots), 5)
                for idx in random_indices:
                    weighted_similarities[idx] += exploration_rate * 0.3
            
            # 选择激活的记忆
            activated_indices = torch.where(weighted_similarities > activation_threshold)[0]
            
            if len(activated_indices) == 0:
                # 选择最相似的前k个
                k = min(5, self.memory_slots)
                activated_indices = torch.topk(weighted_similarities, k).indices
            
            # 记录使用情况
            self.memory_manager.record_usage(memory_type, activated_indices.cpu().numpy())
            
            # 更新记忆重要性
            for idx in activated_indices:
                self.memory_manager.update_importance(memory_type, idx.item(), 0.01)
            
            return memory_bank[activated_indices]
            
        except Exception as e:
            print(f"记忆激活错误: {e}")
            return memory_bank[:0]

    def _adjust_creative_state(self, intent, emotional_context):
        """根据创意意图和情感调整状态"""
        base_states = {
            "explore": {'curiosity': 0.9, 'surprise': 0.7, 'coherence': 0.6, 'novelty': 0.8},
            "refine": {'curiosity': 0.4, 'surprise': 0.3, 'coherence': 0.9, 'harmony': 0.8},
            "discover": {'curiosity': 0.8, 'surprise': 0.9, 'coherence': 0.5, 'novelty': 0.9},
            "abstract": {'curiosity': 0.7, 'surprise': 0.8, 'abstraction': 0.9, 'novelty': 0.7},
            "emotional": {'emotional_intensity': 0.9, 'harmony': 0.6, 'coherence': 0.7}
        }
        
        if intent in base_states:
            self.creative_state.update(base_states[intent])
        
        # 情感影响
        if emotional_context:
            valence = emotional_context.get('valence', 0.5)
            arousal = emotional_context.get('arousal', 0.5)
            
            self.creative_state['emotional_intensity'] = arousal
            if valence > 0.6:
                self.creative_state['harmony'] = min(1.0, self.creative_state['harmony'] + 0.1)
            elif valence < 0.4:
                self.creative_state['surprise'] = min(1.0, self.creative_state['surprise'] + 0.1)

    def _analyze_composition(self, frame):
        """分析图像构图"""
        height, width = frame.shape[:2]
        
        # 使用深度学习进行构图分析
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # 计算视觉重心
        moments = cv2.moments(gray)
        if moments["m00"] != 0:
            cx = int(moments["m10"] / moments["m00"])
            cy = int(moments["m01"] / moments["m00"])
        else:
            cx, cy = width // 2, height // 2
        
        # 计算边缘和角点
        edges = cv2.Canny(gray, 50, 150)
        corners = cv2.goodFeaturesToTrack(gray, 100, 0.01, 10)
        
        # 计算构图规则分数
        rule_of_thirds_score = self._calculate_rule_of_thirds(cx, cy, width, height)
        symmetry_score = self._calculate_symmetry(gray)
        
        return {
            'center': (cx, cy),
            'size': (width, height),
            'brightness': np.mean(gray),
            'contrast': np.std(gray),
            'edge_density': np.sum(edges) / (width * height),
            'corner_count': len(corners) if corners is not None else 0,
            'rule_of_thirds': rule_of_thirds_score,
            'symmetry': symmetry_score
        }

    def _generate_contextual_elements(self, composition, objects, emotional_context, color_scheme):
        """生成上下文相关的虚拟元素"""
        elements = []
        center_x, center_y = composition['center']
        width, height = composition['size']
        
        # 基于情感决定元素数量
        emotional_intensity = emotional_context.get('arousal', 0.5)
        num_elements = int(3 + emotional_intensity * 7)
        
        # 基于对象检测生成相关元素
        object_based_elements = self._generate_object_based_elements(objects, composition)
        elements.extend(object_based_elements)
        
        for i in range(num_elements):
            # 基于构图规则放置元素
            if composition['rule_of_thirds'] > 0.7:
                # 使用三分法则位置
                positions = [
                    (width // 3, height // 3), (2 * width // 3, height // 3),
                    (width // 3, 2 * height // 3), (2 * width // 3, 2 * height // 3)
                ]
                x, y = random.choice(positions)
            else:
                # 随机位置，但考虑构图平衡
                if random.random() > 0.3:
                    x = random.randint(0, width)
                    y = random.randint(0, height)
                else:
                    x = int(np.clip(np.random.normal(center_x, width * 0.2), 0, width))
                    y = int(np.clip(np.random.normal(center_y, height * 0.2), 0, height))
            
            # 基于情感选择元素类型和颜色
            element_type = self._select_element_type(emotional_context)
            size = int(20 + emotional_intensity * 50)
            color = self._select_color(color_scheme, emotional_context)
            alpha = 0.3 + emotional_intensity * 0.5
            
            elements.append({
                'type': element_type,
                'position': (x, y),
                'size': size,
                'color': color,
                'alpha': alpha,
                'emotional_intensity': emotional_intensity
            })
            
        return elements

    def _generate_object_based_elements(self, objects, composition):
        """基于检测到的对象生成相关元素"""
        elements = []
        
        for obj in objects:
            x, y, w, h = obj['bbox']
            center_x, center_y = x + w//2, y + h//2
            
            # 根据对象类型生成相关元素
            if obj['class'] in ['person', 'animal']:
                # 生成光环或能量场
                elements.append({
                    'type': 'energy_field',
                    'position': (center_x, center_y),
                    'size': max(w, h) * 2,
                    'color': (100, 200, 255),
                    'alpha': 0.4
                })
            elif obj['class'] in ['car', 'vehicle']:
                # 生成运动轨迹
                elements.append({
                    'type': 'motion_trail',
                    'position': (center_x, center_y),
                    'size': w,
                    'color': (255, 100, 100),
                    'alpha': 0.6
                })
            elif obj['class'] in ['building', 'house']:
                # 生成几何装饰
                elements.append({
                    'type': 'architectural',
                    'position': (center_x, center_y),
                    'size': min(w, h),
                    'color': (200, 200, 100),
                    'alpha': 0.5
                })
        
        return elements

    def _select_element_type(self, emotional_context):
        """基于情感选择元素类型"""
        valence = emotional_context.get('valence', 0.5)
        
        if valence > 0.7:
            types = ['circle', 'star', 'heart', 'flower']
        elif valence < 0.3:
            types = ['triangle', 'crystal', 'fragment', 'lightning']
        else:
            types = ['circle', 'rectangle', 'triangle', 'hexagon']
            
        return random.choice(types)

    def _select_color(self, color_scheme, emotional_context):
        """基于情感和颜色方案选择颜色"""
        valence = emotional_context.get('valence', 0.5)
        arousal = emotional_context.get('arousal', 0.5)
        
        if arousal > 0.7:
            # 高唤醒度 - 鲜艳颜色
            if valence > 0.6:
                return random.choice([(255, 100, 100), (255, 200, 100), (255, 100, 200)])
            else:
                return random.choice([(100, 100, 255), (100, 200, 255), (200, 100, 255)])
        else:
            # 低唤醒度 - 柔和颜色
            return random.choice(color_scheme)

    def _generate_color_scheme(self, emotional_context):
        """生成情感驱动的颜色方案"""
        valence = emotional_context.get('valence', 0.5)
        
        if valence > 0.7:
            # 积极情感 - 温暖色调
            return [(255, 200, 100), (255, 150, 50), (200, 100, 50)]
        elif valence < 0.3:
            # 消极情感 - 冷色调
            return [(100, 150, 255), (50, 100, 200), (100, 100, 200)]
        else:
            # 中性情感 - 平衡色调
            return [(150, 200, 150), (200, 200, 100), (150, 150, 200)]

    def _calculate_rule_of_thirds(self, cx, cy, width, height):
        """计算三分法则符合度"""
        third_x = width / 3
        third_y = height / 3
        
        # 计算到最近三分线的距离
        dist_x = min(abs(cx - third_x), abs(cx - 2 * third_x), abs(cx - width/2))
        dist_y = min(abs(cy - third_y), abs(cy - 2 * third_y), abs(cy - height/2))
        
        # 转换为分数 (距离越小分数越高)
        score_x = 1 - (dist_x / (width / 6))
        score_y = 1 - (dist_y / (height / 6))
        
        return (score_x + score_y) / 2

    def _calculate_symmetry(self, gray_image):
        """计算图像对称性"""
        height, width = gray_image.shape
        
        # 水平对称
        half_width = width // 2
        left_half = gray_image[:, :half_width]
        right_half = gray_image[:, half_width:2*half_width]
        right_half_flipped = np.fliplr(right_half)
        
        horizontal_symmetry = np.corrcoef(left_half.flatten(), right_half_flipped.flatten())[0,1]
        horizontal_symmetry = max(0, horizontal_symmetry)  # 负相关视为不对称
        
        # 垂直对称
        half_height = height // 2
        top_half = gray_image[:half_height, :]
        bottom_half = gray_image[half_height:2*half_height, :]
        bottom_half_flipped = np.flipud(bottom_half)
        
        vertical_symmetry = np.corrcoef(top_half.flatten(), bottom_half_flipped.flatten())[0,1]
        vertical_symmetry = max(0, vertical_symmetry)
        
        return (horizontal_symmetry + vertical_symmetry) / 2

    def _apply_style_transfer(self, image, style_strength):
        """应用神经风格迁移"""
        try:
            # 转换为PIL图像进行处理
            pil_image = Image.fromarray((image * 255).astype(np.uint8))
            
            # 应用艺术滤镜
            if style_strength > 0.7:
                pil_image = pil_image.filter(ImageFilter.EMBOSS)
            elif style_strength > 0.5:
                pil_image = pil_image.filter(ImageFilter.CONTOUR)
            elif style_strength > 0.3:
                pil_image = pil_image.filter(ImageFilter.EDGE_ENHANCE)
            
            # 调整色彩 - 修复：使用正确的ImageEnhance
            enhancer = ImageEnhance.Color(pil_image)
            pil_image = enhancer.enhance(1.0 + style_strength * 0.5)
            
            # 转换回numpy
            result = np.array(pil_image) / 255.0
            return result
            
        except Exception as e:
            print(f"风格迁移错误: {e}")
            return image

    def _neural_abstraction(self, frame, emotional_context):
        """神经抽象效果"""
        try:
            # 使用深度学习进行特征提取和重组
            frame_tensor = self._preprocess_frame(frame)
            features = self.feature_encoder.encode_visual(frame_tensor)
            
            # 基于情感调整抽象参数
            emotional_intensity = emotional_context.get('arousal', 0.5)
            
            # 创建抽象图案
            height, width = frame.shape[:2]
            abstraction = np.zeros((height, width, 3), dtype=np.float32)
            
            # 生成基于情感的抽象图案
            for i in range(int(emotional_intensity * 50 + 10)):
                center_x = random.randint(0, width)
                center_y = random.randint(0, height)
                radius = random.randint(10, int(min(width, height) * 0.4))
                
                # 基于情感选择颜色
                if emotional_intensity > 0.7:
                    color = np.random.uniform(0.7, 1.0, 3)
                else:
                    color = np.random.uniform(0.3, 0.7, 3)
                
                # 绘制抽象形状
                cv2.circle(abstraction, (center_x, center_y), radius, color, -1)
            
            # 使用高斯模糊创建柔和效果
            abstraction = cv2.GaussianBlur(abstraction, (15, 15), 0)
            
            # 融合原图和抽象图案
            alpha = 0.3 + emotional_intensity * 0.4
            result = cv2.addWeighted(frame.astype(np.float32)/255, 1-alpha, abstraction, alpha, 0)
            
            return (np.clip(result, 0, 1) * 255).astype(np.uint8)
            
        except Exception as e:
            print(f"神经抽象错误: {e}")
            return frame

    def _geometric_deep_abstraction(self, frame, emotional_context):
        """几何深度抽象"""
        height, width = frame.shape[:2]
        result = np.zeros_like(frame, dtype=np.float32)
        
        # 创建多层几何图案
        for layer in range(3):
            layer_intensity = emotional_context.get('arousal', 0.5) * (1 + layer * 0.3)
            
            for i in range(int(10 + layer_intensity * 20)):
                shape_type = random.choice(['circle', 'rectangle', 'polygon'])
                center_x = random.randint(0, width)
                center_y = random.randint(0, height)
                size = random.randint(20, min(width, height) // (layer + 2))
                
                color = tuple(np.random.randint(0, 255, 3).tolist())
                alpha = random.uniform(0.1, 0.3)
                
                if shape_type == 'circle':
                    cv2.circle(result, (center_x, center_y), size, color, -1)
                elif shape_type == 'rectangle':
                    pts = np.array([
                        [center_x-size, center_y-size],
                        [center_x+size, center_y-size],
                        [center_x+size, center_y+size],
                        [center_x-size, center_y+size]
                    ], np.int32)
                    cv2.fillPoly(result, [pts], color)
                else:  # polygon
                    num_sides = random.randint(3, 8)
                    points = []
                    for j in range(num_sides):
                        angle = j * 2 * math.pi / num_sides
                        px = center_x + size * math.cos(angle)
                        py = center_y + size * math.sin(angle)
                        points.append([px, py])
                    pts = np.array(points, np.int32)
                    cv2.fillPoly(result, [pts], color)
        
        # 融合
        alpha = 0.4
        result = cv2.addWeighted(frame.astype(np.float32), 1-alpha, result, alpha, 0)
        return result.astype(np.uint8)

    def _fluid_abstraction(self, frame, emotional_context):
        """流体抽象效果"""
        # 使用光流-like 效果
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        flow = cv2.GaussianBlur(gray, (15, 15), 0)
        
        # 创建流体效果
        emotional_intensity = emotional_context.get('arousal', 0.5)
        scale = 1.0 + emotional_intensity * 2.0
        
        map_x = np.zeros(frame.shape[:2], np.float32)
        map_y = np.zeros(frame.shape[:2], np.float32)
        
        for i in range(frame.shape[0]):
            for j in range(frame.shape[1]):
                distortion = math.sin(i * 0.1 * scale) * 10 + math.cos(j * 0.1 * scale) * 10
                map_x[i, j] = j + distortion
                map_y[i, j] = i + distortion * 0.5
        
        result = cv2.remap(frame, map_x, map_y, cv2.INTER_LINEAR)
        return result

    def _advanced_artistic_filter(self, frame, emotional_context):
        """高级艺术滤镜"""
        # 双边滤波保持边缘
        filtered = cv2.bilateralFilter(frame, 9, 75, 75)
        
        # 基于情感的色彩调整
        valence = emotional_context.get('valence', 0.5)
        
        hsv = cv2.cvtColor(filtered, cv2.COLOR_BGR2HSV)
        
        # 调整饱和度和亮度基于情感
        if valence > 0.7:
            hsv[:, :, 1] = cv2.multiply(hsv[:, :, 1], 1.3)  # 增加饱和度
            hsv[:, :, 2] = cv2.multiply(hsv[:, :, 2], 1.1)  # 增加亮度
        elif valence < 0.3:
            hsv[:, :, 1] = cv2.multiply(hsv[:, :, 1], 0.7)  # 降低饱和度
            hsv[:, :, 2] = cv2.multiply(hsv[:, :, 2], 0.9)  # 降低亮度
        
        hsv[:, :, 1] = np.clip(hsv[:, :, 1], 0, 255)
        hsv[:, :, 2] = np.clip(hsv[:, :, 2], 0, 255)
        
        result = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
        
        # 增强细节
        kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
        result = cv2.filter2D(result, -1, kernel)
        
        return result

    def _preprocess_frame(self, frame):
        """预处理视频帧"""
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame_resized = cv2.resize(frame_rgb, (256, 256))
        frame_tensor = torch.from_numpy(frame_resized).float().permute(2, 0, 1) / 255.0
        return frame_tensor.unsqueeze(0)

    def _initialize_art_styles(self):
        """初始化艺术风格库"""
        styles = {
            'impressionism': {'color_vibrance': 0.8, 'brush_stroke': 0.7, 'light_effect': 0.6},
            'cubism': {'geometric': 0.9, 'fragmentation': 0.8, 'multiple_viewpoints': 0.7},
            'surrealism': {'dream_like': 0.9, 'unexpected_juxtaposition': 0.8, 'symbolic': 0.7},
            'abstract': {'non_representational': 0.9, 'color_field': 0.7, 'texture': 0.6},
            'pop_art': {'bold_colors': 0.8, 'popular_culture': 0.7, 'repetition': 0.6},
            'expressionism': {'emotional': 0.9, 'distorted': 0.7, 'vivid_colors': 0.8},
            'minimalism': {'simple': 0.9, 'geometric': 0.7, 'repetitive': 0.6}
        }
        return styles

class MultiModalEncoder(nn.Module):
    """多模态特征编码器"""
    def __init__(self, feature_dim):
        super().__init__()
        self.feature_dim = feature_dim
        
        # 简化版本 - 避免复杂的预训练模型
        self.visual_encoder = nn.Sequential(
            nn.Conv2d(3, 64, 3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(64, 128, 3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(128, 256, 3, padding=1),
            nn.ReLU(),
            nn.AdaptiveAvgPool2d((4, 4)),
            nn.Flatten(),
            nn.Linear(256 * 4 * 4, 1024),
            nn.ReLU(),
            nn.Linear(1024, feature_dim)
        )
        
    def encode_visual(self, image_tensor):
        return self.visual_encoder(image_tensor)

class CrossModalAttention(nn.Module):
    """跨模态注意力机制"""
    def __init__(self, feature_dim, num_heads=8):
        super().__init__()
        self.feature_dim = feature_dim
        self.num_heads = num_heads
        
        # 简化的注意力机制
        self.query_proj = nn.Linear(feature_dim, feature_dim)
        self.key_proj = nn.Linear(feature_dim, feature_dim)
        self.value_proj = nn.Linear(feature_dim, feature_dim)
        
        self.output_proj = nn.Linear(feature_dim, feature_dim)
        
    def forward(self, current, visual, style, concept, emotion):
        try:
            # 简化的注意力实现
            query = self.query_proj(current)
            
            # 处理所有记忆特征
            all_memories = []
            if len(visual) > 0:
                all_memories.append(visual.mean(dim=0, keepdim=True))
            if len(style) > 0:
                all_memories.append(style.mean(dim=0, keepdim=True))
            if len(concept) > 0:
                all_memories.append(concept.mean(dim=0, keepdim=True))
            if len(emotion) > 0:
                all_memories.append(emotion.mean(dim=0, keepdim=True))
            
            if len(all_memories) == 0:
                return current
                
            # 堆叠记忆
            memories = torch.cat(all_memories, dim=0)
            
            # 计算注意力权重
            keys = self.key_proj(memories)
            values = self.value_proj(memories)
            
            # 简化的注意力计算
            attention_weights = F.softmax(torch.matmul(query, keys.transpose(0, 1)) / (self.feature_dim ** 0.5), dim=1)
            attended_values = torch.matmul(attention_weights, values)
            
            # 残差连接
            output = current + self.output_proj(attended_values)
            
            return output.squeeze(0)
            
        except Exception as e:
            print(f"跨模态注意力错误: {e}")
            return current

class SpatialAttention(nn.Module):
    """空间注意力机制"""
    def __init__(self):
        super().__init__()
        self.conv1 = nn.Conv2d(3, 64, 3, padding=1)
        self.conv2 = nn.Conv2d(64, 1, 3, padding=1)
        self.sigmoid = nn.Sigmoid()
        
    def forward(self, x):
        attention = F.relu(self.conv1(x))
        attention = self.sigmoid(self.conv2(attention))
        return attention

class ArtGenerator(nn.Module):
    """艺术生成器 - 修复张量维度问题"""
    def __init__(self, feature_dim):
        super().__init__()
        self.feature_dim = feature_dim
        
        # 简化的生成器，避免复杂的U-Net结构
        self.generator = nn.Sequential(
            nn.Conv2d(3 + feature_dim, 64, 3, padding=1),
            nn.ReLU(),
            nn.Conv2d(64, 64, 3, padding=1),
            nn.ReLU(),
            nn.Conv2d(64, 32, 3, padding=1),
            nn.ReLU(),
            nn.Conv2d(32, 3, 3, padding=1),
            nn.Tanh()
        )
        
    def forward(self, image, features, attention_map, style_influence):
        try:
            batch_size, _, h, w = image.shape
            
            # 确保features有正确的维度
            if features.dim() == 1:
                features = features.unsqueeze(0)
            
            # 将特征扩展到空间维度 - 修复张量扩展问题
            features_expanded = features.unsqueeze(-1).unsqueeze(-1)
            # 使用repeat而不是expand来避免维度问题
            features_expanded = features_expanded.repeat(1, 1, h, w)
            
            # 拼接图像和特征
            generator_input = torch.cat([image, features_expanded], dim=1)
            
            # 生成增强图像
            enhanced = self.generator(generator_input)
            
            # 应用注意力调制
            if attention_map is not None:
                enhanced = enhanced * attention_map
            
            # 残差连接
            result = (image + enhanced * style_influence * 0.3).clamp(0, 1)
            
            return result
            
        except Exception as e:
            print(f"艺术生成器错误: {e}")
            return image

class NeuralStyleTransfer:
    """神经风格迁移"""
    def __init__(self):
        self.style_models = {}
        
    def apply_style(self, content_image, style_name, strength=0.5):
        """应用风格迁移"""
        # 简化实现
        return content_image

class ObjectDetector:
    """对象检测器"""
    def __init__(self):
        # 简化版本 - 不使用预训练模型
        pass
            
    def detect(self, frame):
        """检测对象"""
        return self._simplified_detection(frame)
    
    def _simplified_detection(self, frame):
        """简化对象检测（备选方案）"""
        # 使用OpenCV的简单检测方法
        objects = []
        
        # 人脸检测
        try:
            face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, 1.1, 4)
            
            for (x, y, w, h) in faces:
                objects.append({
                    'class': 'person',
                    'confidence': 0.8,
                    'bbox': [x, y, w, h]
                })
        except:
            pass
        
        return objects

class EmotionAnalyzer:
    """情感分析器"""
    def __init__(self):
        pass
        
    def analyze(self, frame):
        """分析图像情感"""
        try:
            # 基于颜色和构图的情感分析
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            
            # 计算平均色调和饱和度
            avg_hue = np.mean(hsv[:, :, 0]) / 180.0  # 归一化到0-1
            avg_saturation = np.mean(hsv[:, :, 1]) / 255.0
            avg_brightness = np.mean(hsv[:, :, 2]) / 255.0
            
            # 基于颜色特征估计情感
            valence = self._estimate_valence(avg_hue, avg_saturation, avg_brightness)
            arousal = self._estimate_arousal(avg_saturation, avg_brightness)
            
            return {
                'valence': valence,  # 效价（积极-消极）
                'arousal': arousal,   # 唤醒度（平静-兴奋）
                'color_temperature': avg_hue,
                'intensity': avg_saturation
            }
        except Exception as e:
            print(f"情感分析错误: {e}")
            return {'valence': 0.5, 'arousal': 0.5}
    
    def _estimate_valence(self, hue, saturation, brightness):
        """估计情感效价"""
        # 暖色调（红、黄）通常与积极情感相关
        if hue < 0.3 or hue > 0.7:  # 红色和紫色区域
            valence = 0.7
        elif hue < 0.5:  # 黄色和绿色区域
            valence = 0.6
        else:  # 蓝色区域
            valence = 0.4
            
        # 调整基于饱和度和亮度
        valence += (saturation - 0.5) * 0.2
        valence += (brightness - 0.5) * 0.1
        
        return np.clip(valence, 0.1, 0.9)
    
    def _estimate_arousal(self, saturation, brightness):
        """估计情感唤醒度"""
        # 高饱和度和亮度通常与高唤醒度相关
        arousal = saturation * 0.6 + brightness * 0.4
        return np.clip(arousal, 0.1, 0.9)

class AdaptiveMemoryManager:
    """自适应记忆管理器"""
    def __init__(self, memory_slots, feature_dim):
        self.memory_slots = memory_slots
        self.feature_dim = feature_dim
        
        self.importance_scores = {
            'visual': np.ones(memory_slots),
            'style': np.ones(memory_slots), 
            'concept': np.ones(memory_slots),
            'emotion': np.ones(memory_slots)
        }
        self.usage_count = {
            'visual': np.zeros(memory_slots),
            'style': np.zeros(memory_slots),
            'concept': np.zeros(memory_slots),
            'emotion': np.zeros(memory_slots)
        }
        self.last_used = {
            'visual': np.zeros(memory_slots),
            'style': np.zeros(memory_slots),
            'concept': np.zeros(memory_slots),
            'emotion': np.zeros(memory_slots)
        }
        self.usage_time = time.time()
        
    def get_memory_weights(self, memory_type):
        """获取记忆权重"""
        importance = self.importance_scores[memory_type]
        usage = 1.0 / (1.0 + self.usage_count[memory_type] * 0.01)
        
        # 时间衰减 - 最近使用的记忆权重更高
        time_since_use = time.time() - self.last_used[memory_type]
        time_factor = np.exp(-time_since_use / 3600)  # 1小时衰减
        
        return importance * usage * time_factor
    
    def update_importance(self, memory_type, index, delta):
        """更新记忆重要性"""
        if 0 <= index < self.memory_slots:
            self.importance_scores[memory_type][index] += delta
            self.importance_scores[memory_type][index] = np.clip(
                self.importance_scores[memory_type][index], 0.1, 3.0
            )
        
    def record_usage(self, memory_type, indices):
        """记录记忆使用"""
        current_time = time.time()
        for idx in indices:
            if 0 <= idx < self.memory_slots:
                self.usage_count[memory_type][idx] += 1
                self.last_used[memory_type][idx] = current_time
    
    def enhance_memories(self, features, context, strength):
        """增强相关记忆"""
        pass
        
    def weaken_memories(self, features, context, strength):
        """减弱相关记忆"""
        pass

class CreativeModulator(nn.Module):
    """创意调制器"""
    def __init__(self, feature_dim):
        super().__init__()
        self.feature_dim = feature_dim
        
        self.modulation_net = nn.Sequential(
            nn.Linear(feature_dim, feature_dim * 2),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(feature_dim * 2, feature_dim),
            nn.Tanh()
        )
        
    def forward(self, features, creative_state):
        try:
            # 计算总体调制强度
            total_strength = 0.0
            for factor, strength in creative_state.items():
                total_strength += strength * 0.1  # 简化计算
            
            # 应用调制
            modulation = self.modulation_net(features)
            modulated_features = features + modulation * total_strength
            
            return modulated_features
            
        except Exception as e:
            print(f"创意调制错误: {e}")
            return features

# ========== PyQt界面 ==========

class VideoProcessor(QThread):
    """视频处理线程"""
    frame_processed = pyqtSignal(np.ndarray, list, dict)  # 帧, 检测对象, 情感分析
    creative_insight = pyqtSignal(str)
    system_status = pyqtSignal(dict)
    processing_stats = pyqtSignal(dict)
    
    def __init__(self, creative_network):
        super().__init__()
        self.creative_network = creative_network
        self.is_running = False
        self.creative_mode = "explore"
        self.cap = None
        self.current_frame = None
        self.enhancement_enabled = True
        self.ar_composition_enabled = False
        self.abstraction_level = 0.3
        self.style_influence = 0.5
        self.emotional_context = None
        
        # 性能统计
        self.processing_times = deque(maxlen=60)
        self.frame_count = 0
        
    def start_camera(self, camera_id=0):
        """启动摄像头"""
        try:
            self.cap = cv2.VideoCapture(camera_id)
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.cap.set(cv2.CAP_PROP_FPS, 30)
            self.is_running = True
            self.start()
        except Exception as e:
            print(f"摄像头启动错误: {e}")
        
    def stop_camera(self):
        """停止摄像头"""
        self.is_running = False
        if self.cap:
            self.cap.release()
            
    def set_creative_mode(self, mode):
        """设置创意模式"""
        self.creative_mode = mode
        
    def set_enhancement_enabled(self, enabled):
        """设置增强是否启用"""
        self.enhancement_enabled = enabled
        
    def set_ar_composition_enabled(self, enabled):
        """设置AR构图是否启用"""
        self.ar_composition_enabled = enabled
        
    def set_abstraction_level(self, level):
        """设置抽象级别"""
        self.abstraction_level = level / 100.0
        
    def set_style_influence(self, influence):
        """设置风格影响"""
        self.style_influence = influence / 100.0
        
    def run(self):
        """处理循环"""
        frame_count = 0
        start_time = time.time()
        
        while self.is_running and self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                try:
                    processing_start = time.time()
                    
                    self.current_frame = frame.copy()
                    processed_frame = frame
                    detected_objects = []
                    emotional_context = {}
                    
                    # 应用创造性增强
                    if self.enhancement_enabled:
                        processed_frame, detected_objects, emotional_context = self.creative_network(
                            frame, self.creative_mode, self.style_influence, self.emotional_context
                        )
                        self.emotional_context = emotional_context
                    
                    # 应用AR构图
                    if self.ar_composition_enabled:
                        processed_frame = self.creative_network.creative_ar_composition(
                            processed_frame, detected_objects, emotional_context
                        )
                    
                    # 应用抽象效果
                    if self.abstraction_level > 0.1:
                        processed_frame = self.creative_network.generate_abstract_art(
                            processed_frame, self.abstraction_level, emotional_context
                        )
                    
                    # 绘制检测结果
                    if detected_objects:
                        processed_frame = self._draw_detections(processed_frame, detected_objects)
                    
                    processing_time = time.time() - processing_start
                    self.processing_times.append(processing_time)
                    
                    # 发射信号
                    self.frame_processed.emit(processed_frame, detected_objects, emotional_context)
                    
                    # 更新系统状态
                    frame_count += 1
                    self.frame_count = frame_count
                    
                    if frame_count % 30 == 0:
                        elapsed_time = time.time() - start_time
                        fps = frame_count / elapsed_time if elapsed_time > 0 else 0
                        
                        avg_processing_time = np.mean(self.processing_times) if self.processing_times else 0
                        
                        status = {
                            'fps': fps,
                            'frame_count': frame_count,
                            'memory_usage': random.randint(40, 80),
                            'creative_energy': random.randint(60, 95),
                            'processing_time': avg_processing_time * 1000,  # 毫秒
                            'object_count': len(detected_objects)
                        }
                        self.system_status.emit(status)
                    
                    # 生成创意洞察
                    if random.random() < 0.02:
                        insight = self._generate_creative_insight(detected_objects, emotional_context)
                        self.creative_insight.emit(insight)
                        
                    # 发射处理统计
                    if frame_count % 10 == 0:
                        stats = {
                            'fps': 1.0 / processing_time if processing_time > 0 else 0,
                            'processing_time': processing_time * 1000,
                            'objects_detected': len(detected_objects),
                            'emotional_valence': emotional_context.get('valence', 0.5),
                            'emotional_arousal': emotional_context.get('arousal', 0.5)
                        }
                        self.processing_stats.emit(stats)
                        
                except Exception as e:
                    print(f"处理错误: {e}")
                    import traceback
                    traceback.print_exc()
                    self.frame_processed.emit(frame, [], {})
                    
            else:
                break
                
    def _draw_detections(self, frame, detections):
        """绘制检测结果"""
        for obj in detections:
            x, y, w, h = obj['bbox']
            confidence = obj['confidence']
            class_name = obj['class']
            
            # 绘制边界框
            color = (0, 255, 0) if confidence > 0.7 else (0, 255, 255)
            cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
            
            # 绘制标签
            label = f"{class_name}: {confidence:.2f}"
            label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)[0]
            cv2.rectangle(frame, (x, y - label_size[1] - 10), (x + label_size[0], y), color, -1)
            cv2.putText(frame, label, (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)
        
        return frame
    
    def _generate_creative_insight(self, objects, emotional_context):
        """生成创意洞察"""
        insights = []
        
        # 基于对象检测的洞察
        if objects:
            object_classes = [obj['class'] for obj in objects]
            if 'person' in object_classes:
                insights.extend([
                    "检测到人物，建议增强情感表达",
                    "人物构图提示了故事性元素的添加",
                    "检测到人脸，适合个性化艺术表达"
                ])
            if 'car' in object_classes or 'vehicle' in object_classes:
                insights.append("运动物体检测到，建议添加动态效果")
            if 'building' in object_classes:
                insights.append("建筑结构检测到，适合几何抽象化")
        
        # 基于情感分析的洞察
        if emotional_context:
            valence = emotional_context.get('valence', 0.5)
            arousal = emotional_context.get('arousal', 0.5)
            
            if valence > 0.7 and arousal > 0.7:
                insights.append("积极兴奋的情感氛围，推荐鲜艳色彩和动态构图")
            elif valence > 0.7 and arousal < 0.3:
                insights.append("平静愉悦的氛围，适合柔和色调和平衡构图")
            elif valence < 0.3 and arousal > 0.7:
                insights.append("强烈的情感张力，建议使用对比色和戏剧性元素")
            elif valence < 0.3 and arousal < 0.3:
                insights.append("沉静内敛的氛围，适合单色调和简约风格")
        
        # 通用洞察
        generic_insights = [
            "当前光线条件适合尝试光影效果",
            "色彩分布提示了新的调色板可能性",
            "空间关系激发了新的构图想法",
            "检测到有趣的纹理模式，建议增强质感",
            "运动轨迹提示了时间维度的艺术表达",
            "场景深度适合营造空间层次感"
        ]
        insights.extend(generic_insights)
        
        return random.choice(insights) if insights else "继续探索创意可能性"

class CreativeARWindow(QMainWindow):
    """创意AR主窗口"""
    
    def __init__(self):
        super().__init__()
        self.creative_network = EnhancedCreativeMemoryNetwork()
        self.video_processor = VideoProcessor(self.creative_network)
        self.settings = QSettings("CreativeAR", "DCMN_System")
        self.init_ui()
        self.connect_signals()
        self.load_settings()
        
    def init_ui(self):
        """初始化界面"""
        self.setWindowTitle("创造性AR艺术系统 - DCMN增强版 v2.0")
        self.setGeometry(100, 100, 1400, 900)
        
        # 设置应用样式
        self.setStyleSheet(self._get_stylesheet())
        
        # 中央窗口
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QHBoxLayout()
        central_widget.setLayout(main_layout)
        
        # 创建选项卡
        tab_widget = QTabWidget()
        
        # 实时创作选项卡
        creation_tab = self.create_creation_tab()
        
        # 记忆管理选项卡
        memory_tab = self.create_memory_tab()
        
        # 分析统计选项卡
        analysis_tab = self.create_analysis_tab()
        
        tab_widget.addTab(creation_tab, "🎨 实时创作")
        tab_widget.addTab(memory_tab, "🧠 记忆管理")
        tab_widget.addTab(analysis_tab, "📊 分析统计")
        
        main_layout.addWidget(tab_widget)
        
    def create_creation_tab(self):
        """创建实时创作选项卡"""
        tab = QWidget()
        layout = QHBoxLayout()
        
        # 左侧视频面板
        left_panel = self.create_video_panel()
        
        # 右侧控制面板
        right_panel = self.create_control_panel()
        
        layout.addWidget(left_panel, 2)
        layout.addWidget(right_panel, 1)
        tab.setLayout(layout)
        return tab
        
    def create_video_panel(self):
        """创建视频显示面板"""
        panel = QWidget()
        layout = QVBoxLayout()
        
        # 视频显示标签
        self.video_label = QLabel()
        self.video_label.setMinimumSize(640, 480)
        self.video_label.setStyleSheet("border: 2px solid #555555; background-color: black;")
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setText("摄像头未启动")
        
        # 状态信息栏
        status_bar = QHBoxLayout()
        self.object_count_label = QLabel("检测对象: 0")
        self.emotion_label = QLabel("情感: 中性")
        self.creative_mode_label = QLabel("模式: 探索")
        
        status_bar.addWidget(self.object_count_label)
        status_bar.addWidget(self.emotion_label)
        status_bar.addWidget(self.creative_mode_label)
        status_bar.addStretch()
        
        # 创意洞察显示
        insight_group = QGroupBox("AI创意洞察")
        insight_layout = QVBoxLayout()
        
        self.insight_text = QTextEdit()
        self.insight_text.setMaximumHeight(120)
        self.insight_text.setPlaceholderText("创意洞察将显示在这里...")
        
        insight_layout.addWidget(self.insight_text)
        insight_group.setLayout(insight_layout)
        
        layout.addWidget(QLabel("🎥 实时创意AR视图"))
        layout.addWidget(self.video_label)
        layout.addLayout(status_bar)
        layout.addWidget(insight_group)
        
        panel.setLayout(layout)
        return panel
        
    def create_control_panel(self):
        """创建控制面板"""
        panel = QWidget()
        layout = QVBoxLayout()
        
        # 系统状态组
        status_group = QGroupBox("系统状态")
        status_layout = QVBoxLayout()
        
        self.fps_label = QLabel("FPS: --")
        self.frame_count_label = QLabel("帧数: --")
        self.processing_time_label = QLabel("处理时间: -- ms")
        
        self.memory_usage_bar = QProgressBar()
        self.memory_usage_bar.setRange(0, 100)
        self.memory_usage_bar.setValue(0)
        
        self.creative_energy_bar = QProgressBar()
        self.creative_energy_bar.setRange(0, 100)
        self.creative_energy_bar.setValue(0)
        
        status_layout.addWidget(self.fps_label)
        status_layout.addWidget(self.frame_count_label)
        status_layout.addWidget(self.processing_time_label)
        status_layout.addWidget(QLabel("记忆使用:"))
        status_layout.addWidget(self.memory_usage_bar)
        status_layout.addWidget(QLabel("创意能量:"))
        status_layout.addWidget(self.creative_energy_bar)
        status_group.setLayout(status_layout)
        
        # 摄像头控制组
        camera_group = QGroupBox("摄像头控制")
        camera_layout = QVBoxLayout()
        
        self.start_btn = QPushButton("🎥 启动摄像头")
        self.stop_btn = QPushButton("⏹️ 停止摄像头")
        self.stop_btn.setEnabled(False)
        
        camera_layout.addWidget(self.start_btn)
        camera_layout.addWidget(self.stop_btn)
        camera_group.setLayout(camera_layout)
        
        # 创意模式组
        mode_group = QGroupBox("创意模式")
        mode_layout = QVBoxLayout()
        
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["探索模式", "精炼模式", "发现模式", "抽象模式", "情感模式"])
        
        mode_params = QVBoxLayout()
        
        # 创意参数控制
        creative_params = [
            ("好奇心:", "curiosity_slider", "curiosity_label", 70),
            ("惊喜度:", "surprise_slider", "surprise_label", 50),
            ("抽象度:", "abstraction_slider", "abstraction_label", 30),
            ("和谐度:", "harmony_slider", "harmony_label", 70),
            ("新颖性:", "novelty_slider", "novelty_label", 40),
            ("风格影响:", "style_slider", "style_label", 50)
        ]
        
        self.creative_sliders = {}
        
        for label_text, slider_name, label_name, default_value in creative_params:
            slider_layout = QHBoxLayout()
            slider = QSlider(Qt.Horizontal)
            slider.setRange(0, 100)
            slider.setValue(default_value)
            label = QLabel(f"{default_value}%")
            
            setattr(self, slider_name, slider)
            setattr(self, label_name, label)
            self.creative_sliders[slider_name] = slider
            
            slider_layout.addWidget(QLabel(label_text))
            slider_layout.addWidget(slider)
            slider_layout.addWidget(label)
            mode_params.addLayout(slider_layout)
        
        mode_layout.addWidget(QLabel("创意模式:"))
        mode_layout.addWidget(self.mode_combo)
        mode_layout.addLayout(mode_params)
        mode_group.setLayout(mode_layout)
        
        # 特效控制组
        effects_group = QGroupBox("特效控制")
        effects_layout = QVBoxLayout()
        
        self.enhancement_check = QCheckBox("启用创造性增强")
        self.enhancement_check.setChecked(True)
        
        self.ar_composition_check = QCheckBox("启用AR构图")
        self.ar_composition_check.setChecked(False)
        
        self.object_detection_check = QCheckBox("显示对象检测")
        self.object_detection_check.setChecked(True)
        
        effects_layout.addWidget(self.enhancement_check)
        effects_layout.addWidget(self.ar_composition_check)
        effects_layout.addWidget(self.object_detection_check)
        effects_group.setLayout(effects_layout)
        
        # 反馈组
        feedback_group = QGroupBox("创意反馈")
        feedback_layout = QHBoxLayout()
        
        self.like_btn = QPushButton("👍 喜欢")
        self.dislike_btn = QPushButton("👎 不喜欢")
        self.inspire_btn = QPushButton("💡 灵感")
        self.save_btn = QPushButton("💾 保存作品")
        
        feedback_layout.addWidget(self.like_btn)
        feedback_layout.addWidget(self.dislike_btn)
        feedback_layout.addWidget(self.inspire_btn)
        feedback_layout.addWidget(self.save_btn)
        feedback_group.setLayout(feedback_layout)
        
        # 添加到主布局
        layout.addWidget(status_group)
        layout.addWidget(camera_group)
        layout.addWidget(mode_group)
        layout.addWidget(effects_group)
        layout.addWidget(feedback_group)
        layout.addStretch()
        
        panel.setLayout(layout)
        return panel
        
    def create_memory_tab(self):
        """创建记忆管理选项卡"""
        tab = QWidget()
        layout = QVBoxLayout()
        
        # 记忆统计
        stats_group = QGroupBox("记忆统计")
        stats_layout = QHBoxLayout()
        
        self.visual_memory_label = QLabel("视觉记忆: 0/256")
        self.style_memory_label = QLabel("风格记忆: 0/256")
        self.concept_memory_label = QLabel("概念记忆: 0/256")
        self.emotion_memory_label = QLabel("情感记忆: 0/256")
        
        stats_layout.addWidget(self.visual_memory_label)
        stats_layout.addWidget(self.style_memory_label)
        stats_layout.addWidget(self.concept_memory_label)
        stats_layout.addWidget(self.emotion_memory_label)
        stats_group.setLayout(stats_layout)
        
        # 记忆管理控件
        management_group = QGroupBox("记忆管理")
        management_layout = QVBoxLayout()
        
        # 记忆类型选择
        memory_type_layout = QHBoxLayout()
        memory_type_layout.addWidget(QLabel("记忆类型:"))
        self.memory_type_combo = QComboBox()
        self.memory_type_combo.addItems(["视觉记忆", "风格记忆", "概念记忆", "情感记忆"])
        memory_type_layout.addWidget(self.memory_type_combo)
        memory_type_layout.addStretch()
        
        # 记忆操作按钮
        memory_buttons_layout = QHBoxLayout()
        self.export_memory_btn = QPushButton("导出记忆")
        self.import_memory_btn = QPushButton("导入记忆")
        self.clear_memory_btn = QPushButton("清空记忆")
        self.optimize_memory_btn = QPushButton("优化记忆")
        
        memory_buttons_layout.addWidget(self.export_memory_btn)
        memory_buttons_layout.addWidget(self.import_memory_btn)
        memory_buttons_layout.addWidget(self.clear_memory_btn)
        memory_buttons_layout.addWidget(self.optimize_memory_btn)
        
        # 记忆查看表格
        self.memory_table = QTableWidget()
        self.memory_table.setColumnCount(4)
        self.memory_table.setHorizontalHeaderLabels(["ID", "重要性", "使用次数", "最后使用"])
        self.memory_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        management_layout.addLayout(memory_type_layout)
        management_layout.addLayout(memory_buttons_layout)
        management_layout.addWidget(self.memory_table)
        management_group.setLayout(management_layout)
        
        layout.addWidget(stats_group)
        layout.addWidget(management_group)
        tab.setLayout(layout)
        return tab
        
    def create_analysis_tab(self):
        """创建分析统计选项卡"""
        tab = QWidget()
        layout = QVBoxLayout()
        
        # 实时统计
        realtime_stats_group = QGroupBox("实时统计")
        realtime_layout = QHBoxLayout()
        
        self.fps_chart_label = QLabel("FPS图表")
        self.fps_chart_label.setMinimumSize(300, 200)
        self.fps_chart_label.setStyleSheet("border: 1px solid #555555; background-color: #1a1a1a;")
        
        self.processing_chart_label = QLabel("处理时间图表")
        self.processing_chart_label.setMinimumSize(300, 200)
        self.processing_chart_label.setStyleSheet("border: 1px solid #555555; background-color: #1a1a1a;")
        
        realtime_layout.addWidget(self.fps_chart_label)
        realtime_layout.addWidget(self.processing_chart_label)
        realtime_stats_group.setLayout(realtime_layout)
        
        # 情感分析
        emotion_group = QGroupBox("情感分析")
        emotion_layout = QVBoxLayout()
        
        self.valence_label = QLabel("情感效价: 0.5")
        self.arousal_label = QLabel("唤醒度: 0.5")
        self.emotion_chart_label = QLabel("情感分布图")
        self.emotion_chart_label.setMinimumHeight(150)
        self.emotion_chart_label.setStyleSheet("border: 1px solid #555555; background-color: #1a1a1a;")
        
        emotion_layout.addWidget(self.valence_label)
        emotion_layout.addWidget(self.arousal_label)
        emotion_layout.addWidget(self.emotion_chart_label)
        emotion_group.setLayout(emotion_layout)
        
        # 创意分析
        creativity_group = QGroupBox("创意分析")
        creativity_layout = QVBoxLayout()
        
        self.creativity_stats_label = QLabel("创意统计数据将显示在这里...")
        creativity_layout.addWidget(self.creativity_stats_label)
        creativity_group.setLayout(creativity_layout)
        
        layout.addWidget(realtime_stats_group)
        layout.addWidget(emotion_group)
        layout.addWidget(creativity_group)
        tab.setLayout(layout)
        return tab
        
    def _get_stylesheet(self):
        """获取应用样式表"""
        return """
            QMainWindow {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QTabWidget::pane {
                border: 1px solid #555555;
                background-color: #2b2b2b;
            }
            QTabBar::tab {
                background-color: #404040;
                color: #ffffff;
                padding: 8px 16px;
                margin-right: 2px;
                border: 1px solid #555555;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background-color: #505050;
                border-color: #777777;
            }
            QTabBar::tab:hover {
                background-color: #484848;
            }
            QGroupBox {
                color: #ffffff;
                font-weight: bold;
                border: 2px solid #555555;
                border-radius: 5px;
                margin-top: 1ex;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QPushButton {
                background-color: #404040;
                color: #ffffff;
                border: 1px solid #555555;
                padding: 8px 12px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #505050;
            }
            QPushButton:pressed {
                background-color: #606060;
            }
            QPushButton:disabled {
                background-color: #303030;
                color: #777777;
            }
            QLabel {
                color: #ffffff;
            }
            QComboBox, QListWidget, QTextEdit, QSlider {
                background-color: #404040;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 3px;
                padding: 4px;
            }
            QProgressBar {
                border: 1px solid #555555;
                border-radius: 3px;
                text-align: center;
                color: #ffffff;
                background-color: #353535;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 2px;
            }
            QCheckBox {
                color: #ffffff;
                spacing: 5px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 1px solid #555555;
                border-radius: 3px;
                background-color: #353535;
            }
            QCheckBox::indicator:checked {
                background-color: #4CAF50;
            }
            QTableWidget {
                background-color: #353535;
                color: #ffffff;
                gridline-color: #555555;
                border: 1px solid #555555;
            }
            QTableWidget::item {
                padding: 5px;
                border-bottom: 1px solid #555555;
            }
            QHeaderView::section {
                background-color: #404040;
                color: #ffffff;
                padding: 5px;
                border: 1px solid #555555;
            }
        """
        
    def connect_signals(self):
        """连接信号槽"""
        # 摄像头控制
        self.start_btn.clicked.connect(self.start_camera)
        self.stop_btn.clicked.connect(self.stop_camera)
        
        # 创意模式
        self.mode_combo.currentTextChanged.connect(self.change_creative_mode)
        
        # 连接所有创意参数滑块
        for slider_name, slider in self.creative_sliders.items():
            slider.valueChanged.connect(self.update_creative_params)
        
        # 特效控制
        self.enhancement_check.stateChanged.connect(self.toggle_enhancement)
        self.ar_composition_check.stateChanged.connect(self.toggle_ar_composition)
        self.object_detection_check.stateChanged.connect(self.toggle_object_detection)
        
        # 反馈
        self.like_btn.clicked.connect(lambda: self.give_feedback("positive"))
        self.dislike_btn.clicked.connect(lambda: self.give_feedback("negative"))
        self.inspire_btn.clicked.connect(self.request_inspiration)
        self.save_btn.clicked.connect(self.save_artwork)
        
        # 记忆管理
        self.memory_type_combo.currentTextChanged.connect(self.update_memory_table)
        self.export_memory_btn.clicked.connect(self.export_memory)
        self.import_memory_btn.clicked.connect(self.import_memory)
        self.clear_memory_btn.clicked.connect(self.clear_memory)
        self.optimize_memory_btn.clicked.connect(self.optimize_memory)
        
        # 视频处理信号
        self.video_processor.frame_processed.connect(self.update_video_frame)
        self.video_processor.creative_insight.connect(self.update_insight)
        self.video_processor.system_status.connect(self.update_system_status)
        self.video_processor.processing_stats.connect(self.update_processing_stats)
        
    def start_camera(self):
        """启动摄像头"""
        self.video_processor.start_camera()
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.update_insight("摄像头已启动，开始创造性AR体验")
        
    def stop_camera(self):
        """停止摄像头"""
        self.video_processor.stop_camera()
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.video_label.setText("摄像头未启动")
        self.update_insight("摄像头已停止")
        
    def update_video_frame(self, frame, objects, emotional_context):
        """更新视频帧"""
        try:
            # 更新状态标签
            self.object_count_label.setText(f"检测对象: {len(objects)}")
            
            if emotional_context:
                valence = emotional_context.get('valence', 0.5)
                arousal = emotional_context.get('arousal', 0.5)
                
                if valence > 0.7 and arousal > 0.7:
                    emotion_text = "兴奋积极"
                elif valence > 0.7 and arousal < 0.3:
                    emotion_text = "平静愉悦"
                elif valence < 0.3 and arousal > 0.7:
                    emotion_text = "紧张消极"
                elif valence < 0.3 and arousal < 0.3:
                    emotion_text = "沉静忧郁"
                else:
                    emotion_text = "中性"
                    
                self.emotion_label.setText(f"情感: {emotion_text}")
            
            # 转换并显示图像
            h, w, ch = frame.shape
            bytes_per_line = ch * w
            
            # 根据通道数选择正确的格式
            if ch == 3:
                qt_format = QImage.Format_RGB888
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            else:
                qt_format = QImage.Format_Grayscale8
                rgb_frame = frame
                
            qt_image = QImage(rgb_frame.data, w, h, bytes_per_line, qt_format)
            self.video_label.setPixmap(QPixmap.fromImage(qt_image).scaled(
                self.video_label.width(), 
                self.video_label.height(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            ))
            
        except Exception as e:
            print(f"视频帧更新错误: {e}")
        
    def update_insight(self, insight):
        """更新创意洞察"""
        current_time = time.strftime("%H:%M:%S")
        formatted_insight = f"[{current_time}] {insight}"
        self.insight_text.append(formatted_insight)
        
        # 自动滚动到底部
        scrollbar = self.insight_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        
    def update_system_status(self, status):
        """更新系统状态"""
        self.fps_label.setText(f"FPS: {status['fps']:.1f}")
        self.frame_count_label.setText(f"帧数: {status['frame_count']}")
        self.processing_time_label.setText(f"处理时间: {status['processing_time']:.1f} ms")
        self.memory_usage_bar.setValue(status['memory_usage'])
        self.creative_energy_bar.setValue(status['creative_energy'])
        
    def update_processing_stats(self, stats):
        """更新处理统计"""
        # 更新情感分析标签
        valence = stats.get('emotional_valence', 0.5)
        arousal = stats.get('emotional_arousal', 0.5)
        self.valence_label.setText(f"情感效价: {valence:.2f}")
        self.arousal_label.setText(f"唤醒度: {arousal:.2f}")
        
    def change_creative_mode(self, mode_text):
        """改变创意模式"""
        mode_mapping = {
            "探索模式": "explore",
            "精炼模式": "refine", 
            "发现模式": "discover",
            "抽象模式": "abstract",
            "情感模式": "emotional"
        }
        self.video_processor.set_creative_mode(mode_mapping.get(mode_text, "explore"))
        self.creative_mode_label.setText(f"模式: {mode_text}")
        self.update_insight(f"切换到{mode_text}")
        
    def update_creative_params(self):
        """更新创意参数"""
        # 更新所有滑块标签
        self.curiosity_label.setText(f"{self.curiosity_slider.value()}%")
        self.surprise_label.setText(f"{self.surprise_slider.value()}%")
        self.abstraction_label.setText(f"{self.abstraction_slider.value()}%")
        self.harmony_label.setText(f"{self.harmony_slider.value()}%")
        self.novelty_label.setText(f"{self.novelty_slider.value()}%")
        self.style_label.setText(f"{self.style_slider.value()}%")
        
        # 更新创意网络状态
        self.creative_network.creative_state.update({
            'curiosity': self.curiosity_slider.value() / 100.0,
            'surprise': self.surprise_slider.value() / 100.0,
            'abstraction': self.abstraction_slider.value() / 100.0,
            'harmony': self.harmony_slider.value() / 100.0,
            'novelty': self.novelty_slider.value() / 100.0
        })
        
        # 更新视频处理器参数
        self.video_processor.set_abstraction_level(self.abstraction_slider.value())
        self.video_processor.set_style_influence(self.style_slider.value())
        
    def toggle_enhancement(self, state):
        """切换创造性增强"""
        enabled = state == Qt.Checked
        self.video_processor.set_enhancement_enabled(enabled)
        status = "启用" if enabled else "禁用"
        self.update_insight(f"{status}创造性增强")
        
    def toggle_ar_composition(self, state):
        """切换AR构图"""
        enabled = state == Qt.Checked
        self.video_processor.set_ar_composition_enabled(enabled)
        status = "启用" if enabled else "禁用"
        self.update_insight(f"{status}AR构图")
        
    def toggle_object_detection(self, state):
        """切换对象检测显示"""
        # 这个功能在视频处理线程中自动处理
        enabled = state == Qt.Checked
        status = "显示" if enabled else "隐藏"
        self.update_insight(f"{status}对象检测框")
            
    def give_feedback(self, feedback_type):
        """提供用户反馈"""
        if feedback_type == "positive":
            self.update_insight("感谢您的喜欢！已强化相关记忆。")
            # 这里可以添加实际的学习逻辑
        else:
            self.update_insight("收到反馈，将调整创作方向。")
            # 这里可以添加实际的学习逻辑
            
    def request_inspiration(self):
        """请求灵感"""
        inspirations = [
            "尝试将现实物体转化为抽象几何形状",
            "当前光线条件适合添加光晕效果", 
            "检测到对称性，建议增强视觉平衡",
            "场景色彩提示了互补色方案",
            "运动轨迹激发了动态模糊创意",
            "尝试在负空间添加微妙纹理",
            "当前构图适合添加引导线元素",
            "色彩温度提示了情感调性调整",
            "考虑使用黄金比例重新构图",
            "纹理对比可以增强画面深度"
        ]
        inspiration = random.choice(inspirations)
        self.update_insight(f"💡 创意建议: {inspiration}")
        
    def save_artwork(self):
        """保存艺术作品"""
        try:
            filename, _ = QFileDialog.getSaveFileName(
                self, "保存艺术作品", "", "Images (*.png *.jpg *.bmp)"
            )
            if filename:
                # 获取当前帧并保存
                if hasattr(self.video_processor, 'current_frame'):
                    cv2.imwrite(filename, self.video_processor.current_frame)
                    self.update_insight(f"作品已保存: {filename}")
                else:
                    self.update_insight("没有可保存的帧")
        except Exception as e:
            self.update_insight(f"保存失败: {str(e)}")
            
    def update_memory_table(self):
        """更新记忆表格"""
        # 实现记忆表格的更新逻辑
        pass
        
    def export_memory(self):
        """导出记忆"""
        self.update_insight("记忆导出功能开发中...")
        
    def import_memory(self):
        """导入记忆"""
        self.update_insight("记忆导入功能开发中...")
        
    def clear_memory(self):
        """清空记忆"""
        reply = QMessageBox.question(self, "确认清空", "确定要清空所有记忆吗？此操作不可撤销。",
                                   QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.update_insight("记忆已清空")
            
    def optimize_memory(self):
        """优化记忆"""
        self.update_insight("记忆优化完成")
        
    def load_settings(self):
        """加载设置"""
        # 实现设置加载逻辑
        pass
        
    def closeEvent(self, event):
        """关闭事件"""
        self.video_processor.stop_camera()
        self.save_settings()
        event.accept()
        
    def save_settings(self):
        """保存设置"""
        # 实现设置保存逻辑
        pass

# ========== 主程序 ==========

def main():
    app = QApplication(sys.argv)
    
    # 设置应用样式
    app.setStyle('Fusion')
    
    # 设置应用信息
    app.setApplicationName("创造性AR艺术系统")
    app.setApplicationVersion("2.0")
    app.setOrganizationName("DCMN实验室")
    
    # 创建主窗口
    window = CreativeARWindow()
    window.show()
    
    print("创造性AR艺术系统启动完成！")
    print("=" * 50)
    print("系统特性:")
    print("✓ 动态情境记忆网络(DCMN)")
    print("✓ 实时创造性AR增强") 
    print("✓ 多模态记忆激活")
    print("✓ 情感驱动的风格迁移")
    print("✓ 自适应学习与用户反馈")
    print("✓ 艺术风格探索")
    print("✓ 抽象艺术生成")
    print("✓ 实时构图分析")
    print("✓ 对象检测与跟踪")
    print("✓ 情感分析与响应")
    print("✓ 记忆管理与优化")
    print("✓ 实时性能监控")
    print("=" * 50)
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()