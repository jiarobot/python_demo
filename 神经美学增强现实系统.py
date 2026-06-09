import cv2
import numpy as np
import torch
import torch.nn as nn
import mediapipe as mp
from scipy import ndimage
from PIL import Image, ImageFilter
import matplotlib
matplotlib.rc("font", family='Microsoft YaHei')
import matplotlib.pyplot as plt
from transformers import CLIPProcessor, CLIPModel
import warnings
warnings.filterwarnings('ignore')

class NeuroAestheticAR:
    def __init__(self):
        # 初始化所有组件
        self.setup_neural_aesthetics()
        self.setup_composition_analyzer()
        self.setup_color_harmony()
        self.setup_ar_renderer()
        
        # 美学参数
        self.aesthetic_params = {
            'golden_ratio': 1.618,
            'rule_of_thirds': True,
            'color_harmony_weight': 0.8,
            'composition_weight': 0.9,
            'dynamic_balance': True
        }
        
    def setup_neural_aesthetics(self):
        """设置神经美学分析模型"""
        print("初始化神经美学分析引擎...")
        
        # 使用CLIP模型进行美学理解
        try:
            self.clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
            self.clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
        except:
            print("CLIP模型加载失败，将继续使用基础功能")
            self.clip_model = None
            self.clip_processor = None
        
        # 美学概念嵌入
        self.aesthetic_concepts = [
            "beautiful composition", "harmonious colors", "balanced layout",
            "professional photography", "artistic painting", "pleasing aesthetics",
            "perfect lighting", "elegant design", "visual harmony"
        ]
        
    def setup_composition_analyzer(self):
        """设置构图分析系统"""
        print("初始化智能构图分析...")
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(static_image_mode=False, min_detection_confidence=0.7)
        
        self.mp_face = mp.solutions.face_detection
        self.face_detector = self.mp_face.FaceDetection(model_selection=0, min_detection_confidence=0.7)
        
    def setup_color_harmony(self):
        """设置色彩和谐系统"""
        print("初始化色彩和谐引擎...")
        # 定义专业色彩和谐方案
        self.color_harmonies = {
            'analogous': self.analogous_harmony,
            'complementary': self.complementary_harmony, 
            'triadic': self.triadic_harmony,
            'monochromatic': self.monochromatic_harmony,
            'golden_ratio': self.golden_ratio_harmony
        }
        
    def setup_ar_renderer(self):
        """设置AR渲染系统"""
        print("初始化AR实时渲染...")
        self.focal_points = []
        self.dynamic_weights = []
        
    def triadic_harmony(self, hsv, composition_data):
        """三分色和谐"""
        h, s, v = hsv[:,:,0], hsv[:,:,1], hsv[:,:,2]
        
        dominant_hues = composition_data['color_distribution']['dominant_hues']
        if dominant_hues:
            base_hue = dominant_hues[0]
            # 三分色：基础色 + 120度 + 240度
            triad_hues = [base_hue, (base_hue + 60) % 180, (base_hue + 120) % 180]
            
            # 强化三分色关系
            for target_hue in triad_hues:
                mask = np.abs(h - target_hue) < 15
                s[mask] = np.clip(s[mask] * 1.2, 0, 255)
                v[mask] = np.clip(v[mask] * 1.1, 0, 255)
        
        return cv2.merge([h, s, v])
    
    def monochromatic_harmony(self, hsv, composition_data):
        """单色和谐"""
        h, s, v = hsv[:,:,0], hsv[:,:,1], hsv[:,:,2]
        
        dominant_hues = composition_data['color_distribution']['dominant_hues']
        if dominant_hues:
            base_hue = dominant_hues[0]
            
            # 在基础色调上创建单色变化
            mask = np.abs(h - base_hue) < 30  # 扩大色调范围以包含类似色调
            
            # 增强饱和度变化以创造层次感
            s_variation = np.sin(np.arange(h.shape[0]).reshape(-1, 1) * 0.1) * 0.3 + 1
            s[mask] = np.clip(s[mask] * s_variation[mask], 0, 255)
            
            # 增强亮度变化
            v_variation = np.cos(np.arange(h.shape[1]).reshape(1, -1) * 0.05) * 0.2 + 1
            v[mask] = np.clip(v[mask] * v_variation[mask], 0, 255)
        
        return cv2.merge([h, s, v])

    def analyze_composition(self, image):
        """深度构图分析"""
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # 分析关键视觉元素
        composition_data = {
            'salient_regions': self.find_salient_regions(image),
            'face_positions': self.detect_faces(rgb_image),
            'body_positions': self.detect_poses(rgb_image),
            'edge_density': self.analyze_edge_distribution(image),
            'color_distribution': self.analyze_color_distribution(image)
        }
        
        return composition_data
    
    def find_salient_regions(self, image):
        """使用频域分析和颜色对比找到显著区域"""
        # 方法1: 使用颜色对比度检测显著区域
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        
        # 计算LAB通道的均值
        mean_l = np.mean(l)
        mean_a = np.mean(a)
        mean_b = np.mean(b)
        
        # 计算每个像素与均值的差异
        diff_l = np.abs(l - mean_l)
        diff_a = np.abs(a - mean_a)
        diff_b = np.abs(b - mean_b)
        
        # 合并差异作为显著性图
        saliency_map = (diff_l + diff_a + diff_b) / 3
        
        # 二值化显著性图
        _, binary_saliency = cv2.threshold(saliency_map.astype(np.uint8), 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # 形态学操作去除噪声
        kernel = np.ones((5,5), np.uint8)
        binary_saliency = cv2.morphologyEx(binary_saliency, cv2.MORPH_OPEN, kernel)
        binary_saliency = cv2.morphologyEx(binary_saliency, cv2.MORPH_CLOSE, kernel)
        
        # 找到显著区域
        contours, _ = cv2.findContours(binary_saliency, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        salient_regions = []
        for contour in contours:
            if cv2.contourArea(contour) > 100:  # 过滤小区域
                x, y, w, h = cv2.boundingRect(contour)
                salient_regions.append({
                    'bbox': (x, y, w, h),
                    'center': (x + w//2, y + h//2),
                    'area': w * h
                })
        
        return salient_regions
    
    def detect_faces(self, rgb_image):
        """检测人脸位置"""
        results = self.face_detector.process(rgb_image)
        faces = []
        
        if results.detections:
            for detection in results.detections:
                bbox = detection.location_data.relative_bounding_box
                h, w, _ = rgb_image.shape
                
                x = int(bbox.xmin * w)
                y = int(bbox.ymin * h)
                width = int(bbox.width * w)
                height = int(bbox.height * h)
                
                faces.append({
                    'bbox': (x, y, width, height),
                    'center': (x + width//2, y + height//2),
                    'confidence': detection.score[0]
                })
        
        return faces
    
    def detect_poses(self, rgb_image):
        """检测人体姿态"""
        results = self.pose.process(rgb_image)
        poses = []
        
        if results.pose_landmarks:
            landmarks = results.pose_landmarks.landmark
            h, w, _ = rgb_image.shape
            
            # 提取关键关节点
            key_points = {
                'nose': landmarks[self.mp_pose.PoseLandmark.NOSE],
                'left_shoulder': landmarks[self.mp_pose.PoseLandmark.LEFT_SHOULDER],
                'right_shoulder': landmarks[self.mp_pose.PoseLandmark.RIGHT_SHOULDER]
            }
            
            for name, landmark in key_points.items():
                poses.append({
                    'point': (int(landmark.x * w), int(landmark.y * h)),
                    'type': name
                })
        
        return poses
    
    def analyze_edge_distribution(self, image):
        """分析边缘分布用于构图评估"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        
        # 计算边缘密度分布
        h, w = edges.shape
        quadrants = [
            edges[0:h//2, 0:w//2],      # 左上
            edges[0:h//2, w//2:w],      # 右上  
            edges[h//2:h, 0:w//2],      # 左下
            edges[h//2:h, w//2:w]       # 右下
        ]
        
        densities = [np.sum(quad) / (quad.size + 1e-6) for quad in quadrants]
        return densities
    
    def analyze_color_distribution(self, image):
        """分析色彩分布"""
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        # 分析色调分布
        hue_hist = cv2.calcHist([hsv], [0], None, [180], [0, 180])
        hue_hist = hue_hist / (np.sum(hue_hist) + 1e-6)
        
        return {
            'hue_distribution': hue_hist,
            'dominant_hues': self.find_dominant_hues(hsv),
            'color_variance': np.var(hsv[:,:,0])
        }
    
    def find_dominant_hues(self, hsv_image, n_clusters=5):
        """找到主导色调"""
        try:
            from sklearn.cluster import KMeans
            
            # 采样像素点
            pixels = hsv_image.reshape(-1, 3)
            sample_indices = np.random.choice(pixels.shape[0], min(1000, pixels.shape[0]), replace=False)
            sample_pixels = pixels[sample_indices]
            
            # K-means聚类找到主要颜色
            kmeans = KMeans(n_clusters=n_clusters, random_state=42)
            kmeans.fit(sample_pixels[:, 0].reshape(-1, 1))  # 只在色调通道上聚类
            
            dominant_hues = kmeans.cluster_centers_.flatten()
            return sorted(dominant_hues)
        except:
            # 如果KMeans不可用，使用简化的方法
            hue_channel = hsv_image[:,:,0].flatten()
            hist, bins = np.histogram(hue_channel, bins=180, range=(0, 180))
            peak_indices = np.argsort(hist)[-n_clusters:]
            dominant_hues = bins[peak_indices]
            return sorted(dominant_hues)
    
    def calculate_aesthetic_score(self, composition_data):
        """计算综合美学评分"""
        score = 0.0
        weights = {
            'rule_of_thirds': 0.3,
            'golden_ratio': 0.25, 
            'balance': 0.2,
            'color_harmony': 0.25
        }
        
        # 三分法则评分
        thirds_score = self.evaluate_rule_of_thirds(composition_data)
        score += thirds_score * weights['rule_of_thirds']
        
        # 黄金比例评分
        golden_score = self.evaluate_golden_ratio(composition_data)
        score += golden_score * weights['golden_ratio']
        
        # 视觉平衡评分
        balance_score = self.evaluate_visual_balance(composition_data)
        score += balance_score * weights['balance']
        
        # 色彩和谐评分
        color_score = self.evaluate_color_harmony(composition_data)
        score += color_score * weights['color_harmony']
        
        return min(score * 10, 10.0)  # 转换为10分制
    
    def evaluate_rule_of_thirds(self, composition_data):
        """评估三分法则符合度"""
        if not composition_data['salient_regions']:
            return 0.5  # 默认中等分数
        
        h, w = 480, 640  # 假设图像尺寸
        third_x = [w/3, 2*w/3]
        third_y = [h/3, 2*h/3]
        
        score = 0
        total_weight = 0
        
        for region in composition_data['salient_regions']:
            center_x, center_y = region['center']
            weight = region['area'] / (w * h)  # 区域面积权重
            
            # 计算到最近三分线的距离
            dist_x = min(abs(center_x - x) for x in third_x)
            dist_y = min(abs(center_y - y) for y in third_y)
            
            # 距离越近分数越高
            region_score = max(0, 1 - (dist_x + dist_y) / (w + h))
            score += region_score * weight
            total_weight += weight
        
        return score / (total_weight + 1e-6)
    
    def evaluate_golden_ratio(self, composition_data):
        """评估黄金比例符合度"""
        # 简化的黄金比例评估
        if not composition_data['salient_regions']:
            return 0.5
            
        # 分析主要区域的比例关系
        areas = [r['area'] for r in composition_data['salient_regions']]
        if len(areas) >= 2:
            ratio = max(areas) / min(areas)
            golden_diff = abs(ratio - self.aesthetic_params['golden_ratio'])
            return max(0, 1 - golden_diff / self.aesthetic_params['golden_ratio'])
        
        return 0.5
    
    def evaluate_visual_balance(self, composition_data):
        """评估视觉平衡"""
        edge_densities = composition_data['edge_density']
        if len(edge_densities) == 4:
            # 计算对角线平衡
            diag1_balance = abs(edge_densities[0] - edge_densities[3])
            diag2_balance = abs(edge_densities[1] - edge_densities[2])
            total_balance = 1 - (diag1_balance + diag2_balance) / 2
            return max(0, total_balance)
        
        return 0.5
    
    def evaluate_color_harmony(self, composition_data):
        """评估色彩和谐度"""
        color_data = composition_data['color_distribution']
        dominant_hues = color_data['dominant_hues']
        
        if len(dominant_hues) < 2:
            return 0.5
            
        # 计算色调之间的和谐关系
        hue_differences = []
        for i in range(len(dominant_hues)):
            for j in range(i+1, len(dominant_hues)):
                diff = abs(dominant_hues[i] - dominant_hues[j])
                hue_differences.append(min(diff, 180 - diff))
        
        # 理想和谐角度：类似色30°，互补色180°，分裂互补色150°等
        ideal_differences = [30, 60, 120, 150, 180]
        harmony_scores = []
        
        for diff in hue_differences:
            closest_ideal = min(ideal_differences, key=lambda x: abs(x - diff))
            score = max(0, 1 - abs(diff - closest_ideal) / 90)
            harmony_scores.append(score)
        
        return np.mean(harmony_scores) if harmony_scores else 0.5
    
    def apply_aesthetic_enhancement(self, image, composition_data):
        """应用美学增强"""
        enhanced = image.copy()
        
        # 1. 色彩和谐增强
        enhanced = self.enhance_color_harmony(enhanced, composition_data)
        
        # 2. 构图优化
        enhanced = self.optimize_composition(enhanced, composition_data)
        
        # 3. 动态平衡调整
        enhanced = self.apply_dynamic_balance(enhanced, composition_data)
        
        # 4. 专业级后期处理
        enhanced = self.professional_toning(enhanced)
        
        return enhanced
    
    def enhance_color_harmony(self, image, composition_data):
        """增强色彩和谐"""
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV).astype(np.float32)
        
        # 分析当前色彩和谐度并选择最佳和谐方案
        best_harmony = self.select_best_harmony(composition_data)
        
        # 应用选择的色彩和谐方案
        if best_harmony in self.color_harmonies:
            enhanced_hsv = self.color_harmonies[best_harmony](hsv, composition_data)
        else:
            enhanced_hsv = self.golden_ratio_harmony(hsv, composition_data)
        
        enhanced_hsv = np.clip(enhanced_hsv, 0, 255).astype(np.uint8)
        return cv2.cvtColor(enhanced_hsv, cv2.COLOR_HSV2BGR)
    
    def golden_ratio_harmony(self, hsv, composition_data):
        """黄金比例色彩和谐"""
        h, s, v = hsv[:,:,0], hsv[:,:,1], hsv[:,:,2]
        
        # 基于黄金比例调整色调分布
        dominant_hues = composition_data['color_distribution']['dominant_hues']
        if len(dominant_hues) >= 2:
            base_hue = dominant_hues[0]
            target_hues = [base_hue, (base_hue + 137) % 180]  # 近似黄金比例角度
            
            # 创建色调映射
            hue_mask = np.zeros_like(h)
            for target_hue in target_hues:
                mask = np.abs(h - target_hue) < 30
                hue_mask = np.logical_or(hue_mask, mask)
            
            # 增强目标色调区域
            h[hue_mask] = np.clip(h[hue_mask] * 1.1, 0, 179)
            s[hue_mask] = np.clip(s[hue_mask] * 1.2, 0, 255)
        
        return cv2.merge([h, s, v])
    
    def complementary_harmony(self, hsv, composition_data):
        """互补色和谐"""
        h, s, v = hsv[:,:,0], hsv[:,:,1], hsv[:,:,2]
        
        dominant_hues = composition_data['color_distribution']['dominant_hues']
        if dominant_hues:
            base_hue = dominant_hues[0]
            comp_hue = (base_hue + 90) % 180  # 近似互补
            
            # 强化互补色关系
            for target_hue in [base_hue, comp_hue]:
                mask = np.abs(h - target_hue) < 15
                s[mask] = np.clip(s[mask] * 1.3, 0, 255)
        
        return cv2.merge([h, s, v])
    
    def analogous_harmony(self, hsv, composition_data):
        """类似色和谐"""
        h, s, v = hsv[:,:,0], hsv[:,:,1], hsv[:,:,2]
        
        dominant_hues = composition_data['color_distribution']['dominant_hues']
        if dominant_hues:
            base_hue = dominant_hues[0]
            
            # 在基础色调附近创建和谐
            for offset in [-20, 0, 20]:
                target_hue = (base_hue + offset) % 180
                mask = np.abs(h - target_hue) < 10
                v[mask] = np.clip(v[mask] * 1.1, 0, 255)
        
        return cv2.merge([h, s, v])
    
    def select_best_harmony(self, composition_data):
        """选择最佳色彩和谐方案"""
        color_data = composition_data['color_distribution']
        dominant_hues = color_data['dominant_hues']
        
        if len(dominant_hues) < 2:
            return 'monochromatic'
        
        # 基于当前色彩分布选择最佳和谐方案
        hue_range = max(dominant_hues) - min(dominant_hues)
        
        if hue_range < 30:
            return 'analogous'
        elif 80 < hue_range < 100:
            return 'complementary'
        else:
            return 'golden_ratio'
    
    def optimize_composition(self, image, composition_data):
        """优化图像构图"""
        enhanced = image.copy()
        
        # 应用虚拟构图引导线
        if self.aesthetic_params['rule_of_thirds']:
            enhanced = self.apply_composition_guides(enhanced)
        
        # 动态裁剪建议（视觉上显示，不实际裁剪）
        enhanced = self.suggest_optimal_crop(enhanced, composition_data)
        
        return enhanced
    
    def apply_composition_guides(self, image):
        """应用构图引导线"""
        guide_overlay = image.copy()
        h, w = image.shape[:2]
        
        # 三分线
        for i in range(1, 3):
            x = w * i // 3
            y = h * i // 3
            cv2.line(guide_overlay, (x, 0), (x, h), (0, 255, 255), 1)
            cv2.line(guide_overlay, (0, y), (w, y), (0, 255, 255), 1)
        
        # 黄金比例线
        phi = 0.618
        golden_x = int(w * phi)
        golden_y = int(h * phi)
        cv2.line(guide_overlay, (golden_x, 0), (golden_x, h), (255, 215, 0), 1)
        cv2.line(guide_overlay, (0, golden_y), (w, golden_y), (255, 215, 0), 1)
        
        # 半透明叠加
        alpha = 0.3
        return cv2.addWeighted(image, 1 - alpha, guide_overlay, alpha, 0)
    
    def suggest_optimal_crop(self, image, composition_data):
        """建议最优裁剪区域"""
        h, w = image.shape[:2]
        
        # 基于显著区域计算最佳裁剪
        salient_regions = composition_data['salient_regions']
        if not salient_regions:
            return image
        
        # 计算理想的主体位置
        ideal_centers = []
        for region in salient_regions:
            center_x, center_y = region['center']
            
            # 移动到最近的三分点或黄金比例点
            third_x = [w/3, 2*w/3]
            third_y = [h/3, 2*h/3]
            
            best_x = min(third_x, key=lambda x: abs(x - center_x))
            best_y = min(third_y, key=lambda y: abs(y - center_y))
            
            ideal_centers.append((best_x, best_y))
        
        # 绘制裁剪建议
        crop_overlay = image.copy()
        for ideal_x, ideal_y in ideal_centers:
            cv2.circle(crop_overlay, (int(ideal_x), int(ideal_y)), 10, (0, 255, 0), -1)
            cv2.circle(crop_overlay, (int(ideal_x), int(ideal_y)), 15, (0, 255, 0), 2)
        
        alpha = 0.2
        return cv2.addWeighted(image, 1 - alpha, crop_overlay, alpha, 0)
    
    def apply_dynamic_balance(self, image, composition_data):
        """应用动态视觉平衡"""
        balanced = image.copy()
        
        # 分析视觉重量分布
        weight_map = self.calculate_visual_weight(image, composition_data)
        
        # 应用平衡调整（通过局部对比度和色彩微调）
        hsv = cv2.cvtColor(balanced, cv2.COLOR_BGR2HSV).astype(np.float32)
        
        # 根据视觉重量调整亮度和饱和度
        for i in range(0, image.shape[0], 10):
            for j in range(0, image.shape[1], 10):
                weight = weight_map[i, j]
                
                # 调整局部区域
                if i+10 < image.shape[0] and j+10 < image.shape[1]:
                    if weight > 0.7:  # 重区域
                        hsv[i:i+10, j:j+10, 1] *= 1.1  # 增加饱和度
                    elif weight < 0.3:  # 轻区域  
                        hsv[i:i+10, j:j+10, 2] *= 1.05  # 增加亮度
        
        hsv = np.clip(hsv, 0, 255).astype(np.uint8)
        balanced = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
        
        return balanced
    
    def calculate_visual_weight(self, image, composition_data):
        """计算视觉重量分布图"""
        h, w = image.shape[:2]
        weight_map = np.zeros((h, w))
        
        # 基于显著区域、人脸、边缘密度计算视觉重量
        for region in composition_data['salient_regions']:
            x, y, rw, rh = region['bbox']
            center_x, center_y = region['center']
            area = region['area']
            
            # 创建高斯权重分布
            y_coords, x_coords = np.ogrid[y:y+rh, x:x+rw]
            dist_from_center = np.sqrt((x_coords - center_x)**2 + (y_coords - center_y)**2)
            
            gaussian_weight = np.exp(-dist_from_center**2 / (2 * (min(rw, rh)/4)**2))
            weight_map[y:y+rh, x:x+rw] += gaussian_weight * (area / (h * w))
        
        # 归一化
        if np.max(weight_map) > 0:
            weight_map /= np.max(weight_map)
        
        return weight_map
    
    def professional_toning(self, image):
        """专业级色调处理"""
        # 应用电影级色调曲线
        toned = self.apply_filmic_curve(image)
        
        # 智能锐化
        toned = self.smart_sharpen(toned)
        
        # 微对比度增强
        toned = self.micro_contrast(toned)
        
        return toned
    
    def apply_filmic_curve(self, image):
        """应用电影级S曲线"""
        # 转换为浮点进行计算
        img_float = image.astype(np.float32) / 255.0
        
        # S曲线调整
        shadows = 0.1
        highlights = 0.9
        midtones = 0.5
        
        # 创建S曲线
        curve = np.zeros_like(img_float)
        for c in range(3):
            channel = img_float[:,:,c]
            
            # 阴影调整
            shadow_mask = channel < midtones
            curve[shadow_mask, c] = shadows + (midtones - shadows) * (channel[shadow_mask] / midtones) ** 2
            
            # 高光调整  
            highlight_mask = channel >= midtones
            curve[highlight_mask, c] = midtones + (highlights - midtones) * ((channel[highlight_mask] - midtones) / (1 - midtones)) ** 0.8
        
        return (curve * 255).astype(np.uint8)
    
    def smart_sharpen(self, image):
        """智能锐化 - 只锐化边缘区域"""
        # 创建边缘掩码
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        
        # 膨胀边缘掩码
        kernel = np.ones((3,3), np.uint8)
        edge_mask = cv2.dilate(edges, kernel, iterations=1)
        
        # 只对边缘区域应用锐化
        sharpened = cv2.detailEnhance(image, sigma_s=10, sigma_r=0.15)
        
        # 混合原图和锐化图
        mask = edge_mask.astype(np.float32) / 255.0
        mask = cv2.GaussianBlur(mask, (0,0), sigmaX=2)
        mask = np.stack([mask]*3, axis=2)
        
        result = image * (1 - mask) + sharpened * mask
        return result.astype(np.uint8)
    
    def micro_contrast(self, image):
        """微对比度增强"""
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        
        # 对亮度通道应用局部对比度增强
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        l_enhanced = clahe.apply(l)
        
        enhanced_lab = cv2.merge([l_enhanced, a, b])
        return cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2BGR)
    
    def realtime_ar_pipeline(self):
        """实时AR处理管线"""
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("无法打开摄像头")
            return
            
        cv2.namedWindow('NeuroAesthetic AR', cv2.WINDOW_NORMAL)
        
        print("启动实时神经美学AR系统...")
        print("按 'q' 退出, 's' 保存当前帧")
        
        frame_count = 0
        composition_data = None
        aesthetic_score = 5.0  # 默认分数
        
        while True:
            ret, frame = cap.read()
            if not ret:
                print("无法读取视频帧")
                break
            
            # 降低分辨率以提高性能
            frame = cv2.resize(frame, (640, 480))
            
            # 每隔几帧进行一次完整分析（性能优化）
            if frame_count % 5 == 0:
                try:
                    composition_data = self.analyze_composition(frame)
                    aesthetic_score = self.calculate_aesthetic_score(composition_data)
                except Exception as e:
                    print(f"分析失败: {e}")
                    # 使用默认值继续运行
            
            # 实时增强
            if composition_data is not None:
                try:
                    enhanced_frame = self.apply_aesthetic_enhancement(frame, composition_data)
                except Exception as e:
                    print(f"增强失败: {e}")
                    enhanced_frame = frame
            else:
                enhanced_frame = frame
            
            # 显示美学评分
            cv2.putText(enhanced_frame, f'Aesthetic Score: {aesthetic_score:.1f}/10', 
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            # 显示原图和增强图的对比
            comparison = np.hstack([frame, enhanced_frame])
            cv2.imshow('NeuroAesthetic AR', comparison)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('s'):
                # 保存对比图像
                timestamp = cv2.getTickCount()
                filename = f'neuro_aesthetic_{timestamp}.jpg'
                cv2.imwrite(filename, comparison)
                print(f"图像已保存: {filename}")
            
            frame_count += 1
        
        cap.release()
        cv2.destroyAllWindows()

# 主执行程序
if __name__ == "__main__":
    # 初始化神经美学AR系统
    neuro_ar = NeuroAestheticAR()
    
    # 启动实时AR管线
    neuro_ar.realtime_ar_pipeline()