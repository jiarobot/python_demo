import cv2
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, IsolationForest
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from scipy import stats
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import warnings
import os
import json
from scipy.ndimage import gaussian_filter
warnings.filterwarnings('ignore')

class AdvancedWeatherMonitor:
    def __init__(self):
        self.weather_model = None
        self.scaler = StandardScaler()
        self.isolation_forest = IsolationForest(contamination=0.1, random_state=42)
        self.weather_history = []
        self.feature_names = []
        self.setup_parameters()
        
    def setup_parameters(self):
        """设置气象监测参数"""
        self.weather_classes = {
            'clear': 0,
            'cloudy': 1, 
            'rainy': 2,
            'snowy': 3,
            'foggy': 4,
            'stormy': 5
        }
        
        # 颜色特征范围 (HSV格式)
        self.color_ranges = {
            'clear_sky': [(100, 50, 150), (140, 255, 255)],  # 蓝天
            'cloud_white': [(0, 0, 180), (180, 30, 255)],    # 白云
            'cloud_gray': [(0, 0, 80), (180, 50, 180)],      # 灰云
            'rain_cloud': [(0, 50, 50), (180, 255, 150)],    # 雨云
        }
        
    def extract_advanced_features(self, image):
        """提取高级气象特征 - 修复版本"""
        features = {}
        
        # 转换为不同颜色空间
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # 1. 天空区域检测
        sky_mask = self.detect_sky_region(hsv)
        features['sky_ratio'] = float(np.mean(sky_mask) / 255.0)
        
        # 2. 颜色分布特征
        color_features = self.extract_color_features(hsv, lab, sky_mask)
        features.update(color_features)
        
        # 3. 纹理特征
        texture_features = self.extract_texture_features(gray, sky_mask)
        features.update(texture_features)
        
        # 4. 云层结构特征
        cloud_features = self.analyze_cloud_structure(sky_mask, gray)
        features.update(cloud_features)
        
        # 5. 动态特征（如果有多帧）
        if hasattr(self, 'previous_frame'):
            motion_features = self.analyze_motion_features(gray, self.previous_frame)
            features.update(motion_features)
        
        self.previous_frame = gray.copy()
        
        # 6. 光照和对比度特征
        illumination_features = self.analyze_illumination(image, gray)
        features.update(illumination_features)
        
        # 7. 边缘和轮廓特征
        edge_features = self.analyze_edges(gray)
        features.update(edge_features)
        
        return features
    
    def detect_sky_region(self, hsv_image):
        """检测天空区域 - 增强版"""
        # 蓝天范围
        blue_lower = np.array([100, 50, 150])
        blue_upper = np.array([140, 255, 255])
        
        # 灰白天空范围
        gray_lower = np.array([0, 0, 150])
        gray_upper = np.array([180, 50, 255])
        
        # 新增：清晨/傍晚的红色天空范围
        red_lower = np.array([0, 50, 150])
        red_upper = np.array([10, 255, 255])
        red_lower2 = np.array([170, 50, 150])
        red_upper2 = np.array([180, 255, 255])
        
        blue_mask = cv2.inRange(hsv_image, blue_lower, blue_upper)
        gray_mask = cv2.inRange(hsv_image, gray_lower, gray_upper)
        red_mask1 = cv2.inRange(hsv_image, red_lower, red_upper)
        red_mask2 = cv2.inRange(hsv_image, red_lower2, red_upper2)
        red_mask = cv2.bitwise_or(red_mask1, red_mask2)
        
        combined_mask = cv2.bitwise_or(blue_mask, gray_mask)
        combined_mask = cv2.bitwise_or(combined_mask, red_mask)
        
        # 形态学操作优化天空区域
        kernel = np.ones((5,5), np.uint8)
        combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_CLOSE, kernel)
        combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_OPEN, kernel)
        
        return combined_mask
    
    def extract_color_features(self, hsv_image, lab_image, sky_mask):
        """提取颜色特征 - 修复版本"""
        features = {}
        
        # 天空区域的颜色统计
        sky_pixels = hsv_image[sky_mask == 255]
        if len(sky_pixels) > 0:
            features['sky_hue_mean'] = float(np.mean(sky_pixels[:,0]))
            features['sky_sat_mean'] = float(np.mean(sky_pixels[:,1]))
            features['sky_val_mean'] = float(np.mean(sky_pixels[:,2]))
            features['sky_hue_std'] = float(np.std(sky_pixels[:,0]))
            features['sky_sat_std'] = float(np.std(sky_pixels[:,1]))
            features['sky_val_std'] = float(np.std(sky_pixels[:,2]))
            
            # 新增：天空颜色分布偏度
            features['sky_hue_skew'] = float(stats.skew(sky_pixels[:,0]) if len(sky_pixels) > 0 else 0)
            features['sky_sat_skew'] = float(stats.skew(sky_pixels[:,1]) if len(sky_pixels) > 0 else 0)
        else:
            features.update({f'sky_{k}': 0.0 for k in ['hue_mean', 'sat_mean', 'val_mean', 
                                                    'hue_std', 'sat_std', 'val_std',
                                                    'hue_skew', 'sat_skew']})
        
        # 整体图像颜色特征
        features['global_brightness'] = float(np.mean(hsv_image[:,:,2]))
        features['global_contrast'] = float(np.std(hsv_image[:,:,2]))
        features['color_richness'] = float(np.std(hsv_image[:,:,0]))
        
        # 新增：LAB颜色空间特征
        features['lab_l_mean'] = float(np.mean(lab_image[:,:,0]))
        features['lab_a_mean'] = float(np.mean(lab_image[:,:,1]))
        features['lab_b_mean'] = float(np.mean(lab_image[:,:,2]))
        features['lab_l_std'] = float(np.std(lab_image[:,:,0]))
        
        # 颜色直方图特征 - 确保固定长度
        hist_hue = cv2.calcHist([hsv_image], [0], None, [8], [0, 180])
        hist_hue = cv2.normalize(hist_hue, hist_hue).flatten()
        for i in range(8):  # 固定8个bin
            features[f'hue_hist_bin_{i}'] = float(hist_hue[i] if i < len(hist_hue) else 0.0)
        
        return features
    
    def extract_texture_features(self, gray_image, sky_mask):
        """提取纹理特征 - 修复版本"""
        features = {}
        
        # 天空区域的纹理分析
        sky_region = gray_image[sky_mask == 255]
        if len(sky_region) > 0:
            # GLCM-like 特征 (简化版)
            features['sky_smoothness'] = float(np.std(sky_region))
            features['sky_uniformity'] = float(len(np.unique(sky_region)) / 256.0)
            
            # 修复：避免reshape错误，使用有效的维度
            if len(sky_region) > 50:
                # 将天空区域重塑为合适的二维数组
                height = max(1, len(sky_region) // 50)
                reshaped_sky = sky_region[:height*50].reshape(height, 50)
                
                # 梯度特征
                grad_x = cv2.Sobel(reshaped_sky, cv2.CV_64F, 1, 0, ksize=3)
                grad_y = cv2.Sobel(reshaped_sky, cv2.CV_64F, 0, 1, ksize=3)
                gradient_mag = np.sqrt(grad_x**2 + grad_y**2)
                features['sky_gradient_magnitude'] = float(np.mean(gradient_mag))
                
                # 局部二值模式(LBP)纹理特征
                lbp_features = self.calculate_lbp_features(reshaped_sky)
                features.update(lbp_features)
            else:
                features['sky_gradient_magnitude'] = 0.0
                features.update({f'lbp_{k}': 0.0 for k in ['uniformity', 'contrast']})
        else:
            features.update({f'sky_{k}': 0.0 for k in ['smoothness', 'uniformity', 'gradient_magnitude']})
            features.update({f'lbp_{k}': 0.0 for k in ['uniformity', 'contrast']})
        
        return features
    
    def calculate_lbp_features(self, image):
        """计算LBP纹理特征 - 修复版本"""
        features = {}
        
        try:
            # 简化的LBP计算
            lbp_image = np.zeros_like(image)
            center = image[1:-1, 1:-1]
            
            # 与周围8个像素比较
            code = 0
            code |= (image[:-2, :-2] >= center) << 0
            code |= (image[:-2, 1:-1] >= center) << 1
            code |= (image[:-2, 2:] >= center) << 2
            code |= (image[1:-1, 2:] >= center) << 3
            code |= (image[2:, 2:] >= center) << 4
            code |= (image[2:, 1:-1] >= center) << 5
            code |= (image[2:, :-2] >= center) << 6
            code |= (image[1:-1, :-2] >= center) << 7
            
            lbp_image[1:-1, 1:-1] = code
            
            # LBP特征统计
            hist, _ = np.histogram(lbp_image.flatten(), bins=256, range=[0, 256])
            hist = hist.astype("float")
            hist /= (hist.sum() + 1e-7)  # 归一化
            
            # 使用均匀LBP模式的数量作为纹理度量
            features['lbp_uniformity'] = float(np.sum(hist[:59]))  # 均匀模式的数量
            features['lbp_contrast'] = float(np.std(lbp_image))
        except:
            features['lbp_uniformity'] = 0.0
            features['lbp_contrast'] = 0.0
        
        return features
    
    def analyze_cloud_structure(self, sky_mask, gray_image):
        """分析云层结构 - 修复版本"""
        features = {}
        
        # 在天空区域中检测云
        cloud_candidates = cv2.bitwise_and(gray_image, gray_image, mask=sky_mask)
        _, cloud_binary = cv2.threshold(cloud_candidates, 150, 255, cv2.THRESH_BINARY)
        
        # 云层轮廓分析
        contours, _ = cv2.findContours(cloud_binary.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if contours:
            areas = [cv2.contourArea(cnt) for cnt in contours]
            perimeters = [cv2.arcLength(cnt, True) for cnt in contours]
            
            features['cloud_count'] = float(len(contours))
            features['max_cloud_area'] = float(max(areas) if areas else 0)
            features['mean_cloud_area'] = float(np.mean(areas) if areas else 0)
            features['cloud_coverage'] = float(np.sum(areas) / np.sum(sky_mask == 255) if np.sum(sky_mask == 255) > 0 else 0)
            
            # 新增：云层形状特征
            if areas and perimeters:
                circularities = [4 * np.pi * area / (perim ** 2) if perim > 0 else 0 
                               for area, perim in zip(areas, perimeters)]
                features['mean_circularity'] = float(np.mean(circularities))
                features['cloud_density'] = float(len(contours) / (np.sum(sky_mask == 255) + 1e-7))
            else:
                features['mean_circularity'] = 0.0
                features['cloud_density'] = 0.0
        else:
            features.update({k: 0.0 for k in ['cloud_count', 'max_cloud_area', 'mean_cloud_area', 
                                          'cloud_coverage', 'mean_circularity', 'cloud_density']})
        
        return features
    
    def analyze_motion_features(self, current_gray, previous_gray):
        """分析运动特征（云层移动） - 修复版本"""
        features = {}
        
        try:
            # 计算光流
            flow = cv2.calcOpticalFlowFarneback(previous_gray, current_gray, None, 0.5, 3, 15, 3, 5, 1.2, 0)
            
            # 运动统计
            magnitude = np.sqrt(flow[...,0]**2 + flow[...,1]**2)
            angle = np.arctan2(flow[...,1], flow[...,0]) * 180 / np.pi
            
            features['motion_mean'] = float(np.mean(magnitude))
            features['motion_std'] = float(np.std(magnitude))
            features['motion_max'] = float(np.max(magnitude))
            features['motion_direction'] = float(np.mean(angle))  # 平均运动方向
        except:
            features.update({k: 0.0 for k in ['motion_mean', 'motion_std', 'motion_max', 'motion_direction']})
        
        return features
    
    def analyze_illumination(self, image, gray_image):
        """分析光照条件 - 修复版本"""
        features = {}
        
        # 光照均匀性
        features['illumination_uniformity'] = float(np.std(gray_image) / (np.mean(gray_image) + 1e-7))
        
        # 阴影检测
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        features['shadow_intensity'] = float(np.mean(lab[:,:,0]) / 255.0)
        
        # 对比度测量
        features['local_contrast'] = float(np.mean(cv2.Laplacian(gray_image, cv2.CV_64F) ** 2))
        
        return features
    
    def analyze_edges(self, gray_image):
        """分析边缘特征 - 修复版本"""
        features = {}
        
        # Canny边缘检测
        edges = cv2.Canny(gray_image, 50, 150)
        features['edge_density'] = float(np.sum(edges > 0) / edges.size)
        
        # 边缘方向分布
        sobelx = cv2.Sobel(gray_image, cv2.CV_64F, 1, 0, ksize=3)
        sobely = cv2.Sobel(gray_image, cv2.CV_64F, 0, 1, ksize=3)
        orientation = np.arctan2(sobely, sobelx)
        features['edge_orientation_variance'] = float(np.var(orientation))
        
        return features
    
    def train_weather_model(self, training_data):
        """训练气象分类模型 - 修复版本"""
        X = []
        y = []
        
        print("提取训练特征...")
        
        # 首先收集所有可能的特征名称
        all_feature_names = set()
        sample_features = []
        
        for i, data_point in enumerate(training_data):
            features = self.extract_advanced_features(data_point['image'])
            sample_features.append(features)
            all_feature_names.update(features.keys())
            
            if (i + 1) % 10 == 0:
                print(f"已处理 {i+1}/{len(training_data)} 个样本")
        
        # 排序特征名称以确保一致性
        self.feature_names = sorted(list(all_feature_names))
        print(f"总特征数量: {len(self.feature_names)}")
        
        # 构建特征矩阵，确保所有样本有相同的特征
        for i, features in enumerate(sample_features):
            feature_vector = []
            for feature_name in self.feature_names:
                value = features.get(feature_name, 0.0)
                # 确保所有特征值都是标量
                if hasattr(value, '__len__') and not isinstance(value, str):
                    if len(value) > 0:
                        feature_vector.append(float(np.mean(value)))
                    else:
                        feature_vector.append(0.0)
                else:
                    feature_vector.append(float(value))
            
            X.append(feature_vector)
            y.append(data_point['weather_type'])
        
        X = np.array(X)
        y = np.array(y)
        
        print(f"特征矩阵形状: {X.shape}")
        
        # 标准化特征
        X_scaled = self.scaler.fit_transform(X)
        
        # 训练随机森林分类器
        self.weather_model = RandomForestClassifier(
            n_estimators=100,  # 减少树的数量以加快训练
            max_depth=10,
            min_samples_split=5,
            min_samples_leaf=2,
            random_state=42
        )
        self.weather_model.fit(X_scaled, y)
        
        # 训练异常检测
        self.isolation_forest.fit(X_scaled)
        
        print("气象模型训练完成!")
        print(f"特征数量: {len(self.feature_names)}")
        print(f"训练样本数: {len(X)}")
        
        return self.weather_model
    
    def predict_weather(self, image):
        """预测天气状况 - 修复版本"""
        if self.weather_model is None:
            raise ValueError("请先训练模型!")
        
        # 提取特征
        features = self.extract_advanced_features(image)
        
        # 确保特征顺序与训练时一致
        feature_vector = []
        for feature_name in self.feature_names:
            value = features.get(feature_name, 0.0)
            if hasattr(value, '__len__') and not isinstance(value, str):
                if len(value) > 0:
                    feature_vector.append(float(np.mean(value)))
                else:
                    feature_vector.append(0.0)
            else:
                feature_vector.append(float(value))
        
        feature_vector = np.array(feature_vector).reshape(1, -1)
        
        # 标准化并预测
        feature_vector_scaled = self.scaler.transform(feature_vector)
        
        # 天气分类
        weather_pred = self.weather_model.predict(feature_vector_scaled)[0]
        weather_prob = self.weather_model.predict_proba(feature_vector_scaled)[0]
        
        # 异常检测
        is_anomaly = self.isolation_forest.predict(feature_vector_scaled)[0] == -1
        anomaly_score = self.isolation_forest.decision_function(feature_vector_scaled)[0]
        
        # 获取最重要的特征
        important_features = self.get_important_features(features)
        
        # 记录预测结果
        prediction_record = {
            'timestamp': datetime.now(),
            'weather': weather_pred,
            'confidence': float(max(weather_prob)),
            'is_anomaly': is_anomaly,
            'anomaly_score': float(anomaly_score),
            'features': features,
            'important_features': important_features,
            'all_probabilities': dict(zip(self.weather_model.classes_, weather_prob))
        }
        self.weather_history.append(prediction_record)
        
        return prediction_record
    
    def get_important_features(self, features):
        """获取最重要的特征及其贡献"""
        if self.weather_model is None or not hasattr(self, 'feature_names'):
            return {}
            
        importances = self.weather_model.feature_importances_
        feature_importance = dict(zip(self.feature_names, importances))
        
        # 返回最重要的5个特征
        sorted_features = sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)[:5]
        return dict(sorted_features)
    
    def analyze_weather_trends(self, window_size=10):
        """分析天气趋势"""
        if len(self.weather_history) < window_size:
            return None
        
        recent_data = self.weather_history[-window_size:]
        
        trends = {
            'weather_changes': len(set([r['weather'] for r in recent_data])),
            'avg_confidence': float(np.mean([r['confidence'] for r in recent_data])),
            'anomaly_count': sum([r['is_anomaly'] for r in recent_data]),
            'dominant_weather': stats.mode([r['weather'] for r in recent_data])[0][0],
            'stability_index': 1.0 - (len(set([r['weather'] for r in recent_data])) / window_size),
            'confidence_trend': self.calculate_confidence_trend(recent_data)
        }
        
        return trends
    
    def calculate_confidence_trend(self, recent_data):
        """计算置信度趋势"""
        if len(recent_data) < 2:
            return 0
        
        confidences = [r['confidence'] for r in recent_data]
        # 使用线性回归计算趋势
        x = np.arange(len(confidences))
        slope, _, _, _, _ = stats.linregress(x, confidences)
        return float(slope)
    
    def generate_weather_report(self, image):
        """生成详细气象报告"""
        prediction = self.predict_weather(image)
        trends = self.analyze_weather_trends()
        
        report = {
            'current_weather': prediction['weather'],
            'confidence': prediction['confidence'],
            'anomaly_detected': prediction['is_anomaly'],
            'anomaly_score': prediction['anomaly_score'],
            'sky_coverage': prediction['features']['sky_ratio'],
            'cloud_coverage': prediction['features'].get('cloud_coverage', 0),
            'brightness_level': prediction['features']['global_brightness'],
            'important_features': prediction['important_features'],
            'all_probabilities': prediction['all_probabilities'],
            'trend_analysis': trends
        }
        
        return report
    
    def save_model(self, filepath):
        """保存训练好的模型"""
        import joblib
        model_data = {
            'weather_model': self.weather_model,
            'scaler': self.scaler,
            'isolation_forest': self.isolation_forest,
            'feature_names': self.feature_names
        }
        joblib.dump(model_data, filepath)
        print(f"模型已保存到: {filepath}")
    
    def load_model(self, filepath):
        """加载训练好的模型"""
        import joblib
        model_data = joblib.load(filepath)
        self.weather_model = model_data['weather_model']
        self.scaler = model_data['scaler']
        self.isolation_forest = model_data['isolation_forest']
        self.feature_names = model_data['feature_names']
        print(f"模型已从 {filepath} 加载")

# 模拟数据生成和演示
def demo_weather_monitoring():
    """演示气象监测系统"""
    print("=== 高级视觉气象监测系统演示 ===")
    
    # 初始化监测器
    monitor = AdvancedWeatherMonitor()
    
    # 生成模拟训练数据
    print("生成模拟训练数据...")
    training_data = []
    
    # 模拟不同天气条件下的图像
    weather_types = ['clear', 'cloudy', 'rainy', 'snowy', 'foggy']
    
    for weather in weather_types:
        for i in range(30):  # 每种天气30个样本
            # 创建模拟图像
            if weather == 'clear':
                img = generate_clear_sky_image()
            elif weather == 'cloudy':
                img = generate_cloudy_image()
            elif weather == 'rainy':
                img = generate_rainy_image()
            elif weather == 'snowy':
                img = generate_snowy_image()
            else:  # foggy
                img = generate_foggy_image()
                
            training_data.append({
                'image': img,
                'weather_type': weather
            })
    
    # 训练模型
    print("训练气象分类模型...")
    monitor.train_weather_model(training_data)
    
    # 保存模型
    monitor.save_model('weather_model.pkl')
    
    # 测试预测
    print("\n进行天气预测测试...")
    test_images = [
        (generate_clear_sky_image(), "晴朗"),
        (generate_cloudy_image(), "多云"),
        (generate_rainy_image(), "雨天"),
        (generate_snowy_image(), "雪天"),
        (generate_foggy_image(), "雾天")
    ]
    
    for i, (test_img, true_weather) in enumerate(test_images):
        report = monitor.generate_weather_report(test_img)
        print(f"\n测试图像 {i+1} ({true_weather}) 结果:")
        print(f"  预测天气: {report['current_weather']}")
        print(f"  置信度: {report['confidence']:.3f}")
        print(f"  天空覆盖率: {report['sky_coverage']:.3f}")
        print(f"  云层覆盖率: {report['cloud_coverage']:.3f}")
        print(f"  异常检测: {'是' if report['anomaly_detected'] else '否'}")
        print(f"  最重要特征: {list(report['important_features'].keys())[:3]}")
        
        # 显示概率分布
        print("  概率分布:")
        for weather, prob in report['all_probabilities'].items():
            print(f"    {weather}: {prob:.3f}")

# 模拟图像生成函数
def generate_clear_sky_image():
    """生成晴朗天空模拟图像"""
    img = np.ones((400, 600, 3), dtype=np.uint8)
    # 模拟蓝天渐变
    for i in range(400):
        intensity = int(135 + (i / 400) * 50)  # 从上到下渐变
        img[i, :, 0] = max(100, min(200, intensity))  # 蓝色通道
        img[i, :, 1] = max(150, min(230, intensity + 30))  # 绿色通道  
        img[i, :, 2] = max(180, min(255, intensity + 80))  # 红色通道
    
    # 添加一些微小变化模拟真实天空
    noise = np.random.randint(-5, 5, (400, 600, 3), dtype=np.int16)
    img = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    
    return img

def generate_cloudy_image():
    """生成多云天空模拟图像"""
    img = generate_clear_sky_image()
    
    # 添加多种云层
    cloud_colors = [
        (240, 240, 240),  # 白色云
        (200, 200, 200),  # 浅灰云
        (150, 150, 150)   # 深灰云
    ]
    
    for _ in range(8):
        x, y = np.random.randint(0, 550), np.random.randint(0, 200)
        cloud_size = np.random.randint(30, 80)
        cloud_color = cloud_colors[np.random.randint(0, len(cloud_colors))]
        
        # 创建不规则云形状
        for _ in range(3):
            dx, dy = np.random.randint(-20, 20), np.random.randint(-10, 10)
            cv2.circle(img, (x+dx, y+dy), cloud_size//2, cloud_color, -1)
    
    return img

def generate_rainy_image():
    """生成雨天模拟图像"""
    img = np.ones((400, 600, 3), dtype=np.uint8) * 120  # 深灰色背景
    
    # 添加乌云
    for _ in range(5):
        x, y = np.random.randint(0, 550), np.random.randint(0, 150)
        cv2.circle(img, (x, y), 60, (80, 80, 80), -1)
        cv2.circle(img, (x+30, y), 50, (60, 60, 60), -1)
    
    # 添加雨滴效果 - 更真实的雨滴
    for _ in range(200):
        x, y = np.random.randint(0, 600), np.random.randint(0, 400)
        length = np.random.randint(5, 15)
        thickness = np.random.randint(1, 2)
        brightness = np.random.randint(150, 220)
        cv2.line(img, (x, y), (x, y+length), (brightness, brightness, brightness), thickness)
    
    return img

def generate_snowy_image():
    """生成雪天模拟图像"""
    img = np.ones((400, 600, 3), dtype=np.uint8) * 200  # 亮灰色背景
    
    # 添加雪花 - 不同大小和透明度
    for _ in range(100):
        x, y = np.random.randint(0, 600), np.random.randint(0, 400)
        size = np.random.randint(2, 6)
        brightness = np.random.randint(220, 255)
        
        # 创建更真实的雪花形状
        cv2.circle(img, (x, y), size, (brightness, brightness, brightness), -1)
        if size > 3:
            # 添加雪花的交叉线
            cv2.line(img, (x-size, y), (x+size, y), (brightness, brightness, brightness), 1)
            cv2.line(img, (x, y-size), (x, y+size), (brightness, brightness, brightness), 1)
    
    return img

def generate_foggy_image():
    """生成雾天模拟图像"""
    img = generate_clear_sky_image()
    
    # 添加多层雾效果
    for intensity in [0.2, 0.4, 0.6]:
        fog = np.ones((400, 600, 3), dtype=np.uint8) * np.random.randint(180, 220)
        alpha = intensity * 0.3
        img = cv2.addWeighted(img, 1-alpha, fog, alpha, 0)
    
    # 添加噪声模拟雾的颗粒感
    noise = np.random.randint(-10, 10, (400, 600, 3), dtype=np.int16)
    img = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    
    return img

class WeatherDataLogger:
    """气象数据记录和分析模块 - 增强版"""
    
    def __init__(self):
        self.weather_data = pd.DataFrame()
        self.alert_threshold = 0.7
        
    def log_prediction(self, prediction):
        """记录预测结果"""
        new_record = {
            'timestamp': prediction['timestamp'],
            'weather': prediction['weather'],
            'confidence': prediction['confidence'],
            'anomaly': prediction['is_anomaly'],
            'anomaly_score': prediction['anomaly_score']
        }
        new_record.update(prediction['features'])
        
        self.weather_data = pd.concat([
            self.weather_data, 
            pd.DataFrame([new_record])
        ], ignore_index=True)
        
        # 检查是否需要警报
        self.check_alerts(prediction)
    
    def check_alerts(self, prediction):
        """检查天气警报"""
        alerts = []
        
        # 低置信度警报
        if prediction['confidence'] < 0.6:
            alerts.append(f"低置信度预警: {prediction['confidence']:.3f}")
        
        # 异常检测警报
        if prediction['is_anomaly']:
            alerts.append("异常天气模式检测!")
        
        # 天气突变警报
        if len(self.weather_data) >= 3:
            recent_weather = self.weather_data['weather'].tail(3).values
            if len(set(recent_weather)) > 1:
                alerts.append("检测到天气快速变化")
        
        if alerts:
            print(f"\n⚠️ 天气警报 ({prediction['timestamp'].strftime('%H:%M:%S')}):")
            for alert in alerts:
                print(f"   - {alert}")
    
    def generate_daily_report(self):
        """生成日报 - 增强版"""
        if self.weather_data.empty:
            return None
            
        today = datetime.now().date()
        today_data = self.weather_data[
            self.weather_data['timestamp'].dt.date == today
        ]
        
        if today_data.empty:
            return None
            
        report = {
            'date': today,
            'total_observations': len(today_data),
            'dominant_weather': today_data['weather'].mode()[0] if not today_data.empty else 'unknown',
            'avg_confidence': today_data['confidence'].mean(),
            'anomaly_percentage': (today_data['anomaly'].sum() / len(today_data)) * 100,
            'weather_transitions': self.calculate_weather_transitions(today_data),
            'confidence_statistics': {
                'min': today_data['confidence'].min(),
                'max': today_data['confidence'].max(),
                'std': today_data['confidence'].std()
            },
            'feature_correlations': self.calculate_feature_correlations(today_data)
        }
        
        return report
    
    def calculate_weather_transitions(self, data):
        """计算天气转换模式"""
        transitions = []
        for i in range(1, len(data)):
            if data.iloc[i]['weather'] != data.iloc[i-1]['weather']:
                transitions.append({
                    'from': data.iloc[i-1]['weather'],
                    'to': data.iloc[i]['weather'],
                    'time': data.iloc[i]['timestamp'],
                    'duration_minutes': (data.iloc[i]['timestamp'] - data.iloc[i-1]['timestamp']).total_seconds() / 60
                })
        return transitions
    
    def calculate_feature_correlations(self, data):
        """计算特征与天气的相关性"""
        if len(data) < 5:
            return {}
        
        # 选择数值型特征
        numeric_cols = data.select_dtypes(include=[np.number]).columns
        correlations = {}
        
        for col in numeric_cols:
            if col not in ['confidence', 'anomaly_score']:
                try:
                    # 将天气类型转换为数值
                    weather_codes = pd.factorize(data['weather'])[0]
                    corr = np.corrcoef(data[col], weather_codes)[0, 1]
                    if not np.isnan(corr):
                        correlations[col] = corr
                except:
                    continue
        
        # 返回相关性最强的5个特征
        sorted_correlations = dict(sorted(correlations.items(), 
                                        key=lambda x: abs(x[1]), 
                                        reverse=True)[:5])
        return sorted_correlations
    
    def save_report(self, filename='weather_report.json'):
        """保存报告到文件"""
        report = self.generate_daily_report()
        if report:
            # 转换非JSON可序列化对象
            for key, value in report.items():
                if isinstance(value, (datetime, pd.Timestamp)):
                    report[key] = value.isoformat()
                elif isinstance(value, np.integer):
                    report[key] = int(value)
                elif isinstance(value, np.floating):
                    report[key] = float(value)
                elif isinstance(value, np.ndarray):
                    report[key] = value.tolist()
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            print(f"报告已保存到: {filename}")

# 实时监测循环示例
def real_time_monitoring(camera_source=0):
    """实时气象监测"""
    monitor = AdvancedWeatherMonitor()
    logger = WeatherDataLogger()
    
    # 尝试加载预训练模型
    try:
        monitor.load_model('weather_model.pkl')
        print("预训练模型加载成功!")
    except:
        print("未找到预训练模型，请先运行演示以训练模型")
        return
    
    cap = cv2.VideoCapture(camera_source)
    
    print("开始实时气象监测...")
    print("按 'q' 退出, 's' 保存报告")
    
    frame_count = 0
    
    while True:
        ret, frame = cap.read()
        if not ret:
            print("无法读取摄像头数据")
            break
        
        # 调整图像大小以提高处理速度
        frame = cv2.resize(frame, (640, 480))
        
        try:
            # 每5帧进行一次预测以减少计算量
            if frame_count % 5 == 0:
                # 气象预测
                prediction = monitor.predict_weather(frame)
                logger.log_prediction(prediction)
                
                # 在图像上显示结果
                weather_text = f"Weather: {prediction['weather']}"
                confidence_text = f"Confidence: {prediction['confidence']:.2f}"
                
                cv2.putText(frame, weather_text, (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                cv2.putText(frame, confidence_text, (10, 60),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                
                if prediction['is_anomaly']:
                    cv2.putText(frame, "ANOMALY DETECTED!", (10, 90),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
            
            frame_count += 1
            
        except Exception as e:
            print(f"预测错误: {e}")
        
        cv2.imshow('Weather Monitoring', frame)
        
        # 按键处理
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('s'):
            logger.save_report()
            print("报告已保存!")
    
    cap.release()
    cv2.destroyAllWindows()
    
    # 生成最终报告
    report = logger.generate_daily_report()
    if report:
        print("\n=== 每日气象报告 ===")
        print(f"观测次数: {report['total_observations']}")
        print(f"主要天气: {report['dominant_weather']}")
        print(f"平均置信度: {report['avg_confidence']:.3f}")
        print(f"异常比例: {report['anomaly_percentage']:.1f}%")
        print(f"天气转换次数: {len(report['weather_transitions'])}")
        
        # 保存报告
        logger.save_report()

# 新增：批量图像处理功能
def batch_process_images(image_folder, output_file='batch_weather_report.json'):
    """批量处理图像文件夹"""
    monitor = AdvancedWeatherMonitor()
    
    # 尝试加载模型
    try:
        monitor.load_model('weather_model.pkl')
    except:
        print("请先训练模型!")
        return
    
    results = []
    valid_extensions = ('.jpg', '.jpeg', '.png', '.bmp')
    
    print(f"处理文件夹: {image_folder}")
    
    for filename in os.listdir(image_folder):
        if filename.lower().endswith(valid_extensions):
            filepath = os.path.join(image_folder, filename)
            
            try:
                image = cv2.imread(filepath)
                if image is not None:
                    report = monitor.generate_weather_report(image)
                    report['filename'] = filename
                    results.append(report)
                    print(f"已处理: {filename}")
            except Exception as e:
                print(f"处理 {filename} 时出错: {e}")
    
    # 保存结果
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n批量处理完成! 结果保存在: {output_file}")
    print(f"总共处理了 {len(results)} 张图像")

if __name__ == "__main__":
    # 运行演示
    demo_weather_monitoring()
    
    print("\n" + "="*50)
    print("=== 系统特性总结 ===")
    print("✓ 多特征气象分析 (颜色、纹理、结构、运动)")
    print("✓ 实时异常检测和警报系统") 
    print("✓ 天气趋势预测和稳定性分析")
    print("✓ 非深度学习方案 - 完全可解释")
    print("✓ 资源高效运行")
    print("✓ 批量图像处理能力")
    print("✓ 详细的概率分布和特征重要性")
    print("✓ 模型保存和加载功能")
    print("✓ 实时警报和报告生成")
    
    # 询问是否启动实时监测
    response = input("\n是否启动实时监测? (y/n): ")
    if response.lower() == 'y':
        real_time_monitoring()
    
    # 询问是否进行批量处理
    response = input("\n是否进行批量图像处理? (输入文件夹路径或按回车跳过): ")
    if response.strip():
        batch_process_images(response.strip())