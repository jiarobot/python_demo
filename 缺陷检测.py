import cv2
import numpy as np
from scipy import ndimage
from sklearn.cluster import DBSCAN
import matplotlib
matplotlib.rc("font", family='Microsoft YaHei')
import matplotlib.pyplot as plt
from collections import deque
import time
import json
from dataclasses import dataclass
from typing import List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')

@dataclass
class Defect:
    """缺陷数据类"""
    contour: np.ndarray
    area: float
    centroid: Tuple[float, float]
    defect_type: str
    confidence: float
    bbox: Tuple[int, int, int, int]

class AdvancedDefectDetector:
    """高级缺陷检测器"""
    
    def __init__(self, config_path: str = None):
        self.config = self._load_config(config_path)
        self.fps_queue = deque(maxlen=30)  # FPS计算队列
        self.adaptive_threshold = 128  # 自适应阈值
        self.reference_image = None  # 参考图像（模板）
        
        # 形态学操作核
        self.kernel_small = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        self.kernel_medium = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        self.kernel_large = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        
    def _load_config(self, config_path: str) -> dict:
        """加载配置文件"""
        default_config = {
            "min_defect_area": 50,
            "max_defect_area": 10000,
            "blur_kernel_size": 5,
            "canny_low": 50,
            "canny_high": 150,
            "morph_operations": 2,
            "similarity_threshold": 0.8,
            "adaptive_learning_rate": 0.01,
            "cluster_eps": 10.0,
            "cluster_min_samples": 3
        }
        
        if config_path and os.path.exists(config_path):
            with open(config_path, 'r') as f:
                user_config = json.load(f)
                default_config.update(user_config)
                
        return default_config
    
    def preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """图像预处理管道"""
        # 转换为灰度图
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
            
        # 高斯模糊去噪
        blurred = cv2.GaussianBlur(gray, 
                                 (self.config["blur_kernel_size"], 
                                  self.config["blur_kernel_size"]), 0)
        
        # 对比度增强 - CLAHE
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(blurred)
        
        # 非局部均值去噪
        denoised = cv2.fastNlMeansDenoising(enhanced, None, 10, 7, 21)
        
        return denoised
    
    def multi_scale_feature_extraction(self, image: np.ndarray) -> dict:
        """多尺度特征提取"""
        features = {}
        
        # 1. 小尺度特征 - 边缘检测
        edges = cv2.Canny(image, self.config["canny_low"], self.config["canny_high"])
        features['edges'] = edges
        
        # 2. 中尺度特征 - 纹理分析
        sobelx = cv2.Sobel(image, cv2.CV_64F, 1, 0, ksize=3)
        sobely = cv2.Sobel(image, cv2.CV_64F, 0, 1, ksize=3)
        gradient_magnitude = np.sqrt(sobelx**2 + sobely**2)
        features['texture'] = gradient_magnitude.astype(np.uint8)
        
        # 3. 大尺度特征 - 区域分析
        _, binary = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        features['regions'] = binary
        
        # 4. 频率域分析 - FFT
        fft = np.fft.fft2(image)
        fft_shift = np.fft.fftshift(fft)
        magnitude_spectrum = 20 * np.log(np.abs(fft_shift) + 1)
        features['frequency'] = magnitude_spectrum.astype(np.uint8)
        
        return features
    
    def advanced_segmentation(self, image: np.ndarray) -> np.ndarray:
        """高级图像分割"""
        # 多阈值分割
        thresholds = []
        for i in range(3):
            threshold = cv2.adaptiveThreshold(
                image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                cv2.THRESH_BINARY, 11, 2*i
            )
            thresholds.append(threshold)
        
        # 结合多个阈值结果
        combined = np.zeros_like(image)
        for thresh in thresholds:
            combined = cv2.bitwise_or(combined, thresh)
            
        # 形态学操作清理
        cleaned = self._morphological_cleanup(combined)
        
        return cleaned
    
    def _morphological_cleanup(self, image: np.ndarray) -> np.ndarray:
        """形态学清理"""
        # 开运算去除小噪声
        opened = cv2.morphologyEx(image, cv2.MORPH_OPEN, self.kernel_medium)
        
        # 闭运算填充小孔洞
        closed = cv2.morphologyEx(opened, cv2.MORPH_CLOSE, self.kernel_small)
        
        # 距离变换 + 分水岭（可选，用于复杂场景）
        dist_transform = cv2.distanceTransform(closed, cv2.DIST_L2, 5)
        _, sure_fg = cv2.threshold(dist_transform, 0.7 * dist_transform.max(), 255, 0)
        sure_fg = np.uint8(sure_fg)
        
        return sure_fg
    
    def defect_clustering_analysis(self, contours: List[np.ndarray]) -> List[List[np.ndarray]]:
        """缺陷聚类分析"""
        if not contours:
            return []
            
        # 提取轮廓特征
        features = []
        for contour in contours:
            if len(contour) >= 5:  # 需要足够点来计算椭圆
                (x, y), (w, h), angle = cv2.minAreaRect(contour)
                area = cv2.contourArea(contour)
                perimeter = cv2.arcLength(contour, True)
                circularity = 4 * np.pi * area / (perimeter ** 2) if perimeter > 0 else 0
                
                features.append([x, y, w, h, area, circularity])
        
        if len(features) < 2:
            return [contours]
            
        features = np.array(features)
        
        # DBSCAN聚类
        clustering = DBSCAN(
            eps=self.config["cluster_eps"], 
            min_samples=self.config["cluster_min_samples"]
        ).fit(features)
        
        # 按聚类分组轮廓
        clusters = []
        for label in set(clustering.labels_):
            if label != -1:  # 忽略噪声点
                cluster_contours = [contours[i] for i in range(len(contours)) 
                                  if clustering.labels_[i] == label]
                clusters.append(cluster_contours)
                
        return clusters if clusters else [contours]
    
    def classify_defect(self, contour: np.ndarray, image: np.ndarray) -> Tuple[str, float]:
        """缺陷分类"""
        area = cv2.contourArea(contour)
        
        # 计算形状特征
        perimeter = cv2.arcLength(contour, True)
        circularity = 4 * np.pi * area / (perimeter ** 2) if perimeter > 0 else 0
        
        # 计算矩形度
        x, y, w, h = cv2.boundingRect(contour)
        rect_area = w * h
        rectangularity = area / rect_area if rect_area > 0 else 0
        
        # 计算伸长度
        elongation = max(w, h) / min(w, h) if min(w, h) > 0 else 1
        
        # 基于规则分类
        if circularity > 0.8:
            defect_type = "孔洞"
            confidence = min(circularity, 0.95)
        elif elongation > 3:
            defect_type = "划痕"
            confidence = min((elongation - 1) / 5, 0.9)
        elif rectangularity < 0.3:
            defect_type = "凹陷"
            confidence = 0.85
        else:
            defect_type = "异物"
            confidence = 0.7
            
        return defect_type, confidence
    
    def template_matching_analysis(self, current_image: np.ndarray, 
                                 template_image: np.ndarray) -> np.ndarray:
        """模板匹配分析"""
        # 多尺度模板匹配
        scales = [0.8, 0.9, 1.0, 1.1, 1.2]
        best_match = None
        best_score = -1
        
        for scale in scales:
            # 调整模板尺寸
            width = int(template_image.shape[1] * scale)
            height = int(template_image.shape[0] * scale)
            resized_template = cv2.resize(template_image, (width, height))
            
            # 模板匹配
            result = cv2.matchTemplate(current_image, resized_template, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, _ = cv2.minMaxLoc(result)
            
            if max_val > best_score:
                best_score = max_val
                best_match = resized_template
                
        return best_match if best_score > self.config["similarity_threshold"] else None
    
    def detect_defects(self, image: np.ndarray, 
                      reference_image: Optional[np.ndarray] = None) -> List[Defect]:
        """主检测函数"""
        start_time = time.time()
        
        # 预处理
        processed = self.preprocess_image(image)
        
        # 多尺度特征提取
        features = self.multi_scale_feature_extraction(processed)
        
        # 分割
        segmented = self.advanced_segmentation(processed)
        
        # 轮廓检测
        contours, _ = cv2.findContours(segmented, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        defects = []
        valid_contours = []
        
        # 初步筛选轮廓
        for contour in contours:
            area = cv2.contourArea(contour)
            if (self.config["min_defect_area"] <= area <= self.config["max_defect_area"]):
                valid_contours.append(contour)
        
        # 聚类分析
        clusters = self.defect_clustering_analysis(valid_contours)
        
        # 分析每个聚类
        for cluster in clusters:
            for contour in cluster:
                area = cv2.contourArea(contour)
                
                # 计算质心
                M = cv2.moments(contour)
                if M["m00"] != 0:
                    cx = int(M["m10"] / M["m00"])
                    cy = int(M["m01"] / M["m00"])
                else:
                    cx, cy = 0, 0
                
                # 边界框
                x, y, w, h = cv2.boundingRect(contour)
                
                # 分类缺陷
                defect_type, confidence = self.classify_defect(contour, processed)
                
                # 创建缺陷对象
                defect = Defect(
                    contour=contour,
                    area=area,
                    centroid=(cx, cy),
                    defect_type=defect_type,
                    confidence=confidence,
                    bbox=(x, y, w, h)
                )
                defects.append(defect)
        
        # 计算FPS
        end_time = time.time()
        processing_time = end_time - start_time
        self.fps_queue.append(1.0 / processing_time if processing_time > 0 else 0)
        
        return defects
    
    def visualize_results(self, image: np.ndarray, defects: List[Defect], 
                         show_features: bool = False) -> np.ndarray:
        """可视化结果"""
        result = image.copy()
        
        # 颜色映射
        color_map = {
            "孔洞": (0, 0, 255),    # 红色
            "划痕": (0, 255, 255),  # 黄色
            "凹陷": (255, 0, 0),    # 蓝色
            "异物": (0, 255, 0)     # 绿色
        }
        
        # 绘制缺陷
        for defect in defects:
            color = color_map.get(defect.defect_type, (255, 255, 255))
            
            # 绘制轮廓
            cv2.drawContours(result, [defect.contour], -1, color, 2)
            
            # 绘制边界框
            x, y, w, h = defect.bbox
            cv2.rectangle(result, (x, y), (x + w, y + h), color, 2)
            
            # 绘制质心
            cv2.circle(result, defect.centroid, 5, color, -1)
            
            # 添加标签
            label = f"{defect.defect_type}({defect.confidence:.2f})"
            cv2.putText(result, label, (x, y - 10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        
        # 添加统计信息
        fps = np.mean(self.fps_queue) if self.fps_queue else 0
        stats = f"Defects: {len(defects)} | FPS: {fps:.1f}"
        cv2.putText(result, stats, (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        return result

def main():
    """主函数 - 演示使用"""
    # 初始化检测器
    detector = AdvancedDefectDetector()
    
    # 创建模拟图像或从摄像头读取
    print("选择输入源:")
    print("1. 使用摄像头")
    print("2. 使用测试图像")
    choice = input("请输入选择 (1/2): ")
    
    if choice == "1":
        # 摄像头模式
        cap = cv2.VideoCapture(0)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        print("摄像头已启动，按 'q' 退出，按 's' 保存当前帧")
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
                
            # 检测缺陷
            defects = detector.detect_defects(frame)
            
            # 可视化结果
            result = detector.visualize_results(frame, defects)
            
            cv2.imshow('Industrial Defect Detection', result)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('s'):
                # 保存当前帧
                timestamp = int(time.time())
                cv2.imwrite(f'defect_frame_{timestamp}.jpg', result)
                print(f"帧已保存: defect_frame_{timestamp}.jpg")
        
        cap.release()
        
    else:
        # 测试图像模式
        # 创建模拟工业图像
        test_image = create_test_image()
        
        # 检测缺陷
        defects = detector.detect_defects(test_image)
        
        # 可视化结果
        result = detector.visualize_results(test_image, defects, show_features=True)
        
        # 显示结果
        plt.figure(figsize=(15, 10))
        plt.subplot(121), plt.imshow(cv2.cvtColor(test_image, cv2.COLOR_BGR2RGB))
        plt.title('原始图像'), plt.axis('off')
        plt.subplot(122), plt.imshow(cv2.cvtColor(result, cv2.COLOR_BGR2RGB))
        plt.title('缺陷检测结果'), plt.axis('off')
        plt.show()
        
        print(f"检测到 {len(defects)} 个缺陷:")
        for i, defect in enumerate(defects):
            print(f"缺陷 {i+1}: {defect.defect_type}, 置信度: {defect.confidence:.2f}, "
                  f"面积: {defect.area:.1f}")

def create_test_image() -> np.ndarray:
    """创建测试图像"""
    image = np.ones((480, 640, 3), dtype=np.uint8) * 128  # 灰色背景
    
    # 添加一些模拟缺陷
    cv2.circle(image, (100, 100), 15, (200, 200, 200), -1)  # 孔洞
    cv2.ellipse(image, (300, 200), (50, 10), 30, 0, 360, (180, 180, 180), -1)  # 划痕
    cv2.rectangle(image, (450, 150), (500, 200), (160, 160, 160), -1)  # 凹陷
    cv2.circle(image, (200, 350), 20, (220, 220, 220), -1)  # 异物
    
    # 添加一些噪声
    noise = np.random.normal(0, 10, image.shape).astype(np.uint8)
    image = cv2.add(image, noise)
    
    return image

if __name__ == "__main__":
    import os
    main()