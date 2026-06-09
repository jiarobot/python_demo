import cv2
import numpy as np
import matplotlib.pyplot as plt
from scipy import ndimage, spatial
from skimage import feature, measure, filters, morphology, segmentation
import json
import os
from datetime import datetime
import pandas as pd
from mpl_toolkits.mplot3d import Axes3D
import glob
from geopy.distance import geodesic
from pyproj import Transformer
import rasterio
from rasterio.transform import from_bounds
import warnings
warnings.filterwarnings('ignore')

class DroneStructuralMonitoring:
    def __init__(self, config_path=None):
        """
        初始化无人机建筑结构监测系统
        
        参数:
            config_path: 配置文件路径
        """
        # 默认配置 - 针对无人机视角优化
        self.config = {
            'drone_params': {
                'camera_resolution': (4000, 3000),  # 相机分辨率
                'focal_length_mm': 24,  # 焦距(mm)
                'sensor_width_mm': 13.2,  # 传感器宽度(mm)
                'flight_altitude': 50,  # 飞行高度(m)
                'overlap_ratio': 0.7,  # 图像重叠率
            },
            'crack_detection': {
                'min_crack_width': 0.05,  # 最小裂缝宽度(mm)
                'max_crack_width': 20,    # 最大裂缝宽度(mm)
                'crack_length_threshold': 10,  # 最小裂缝长度(mm)
            },
            'deformation_detection': {
                'max_allowed_deformation': 0.005,  # 最大允许变形比例
            },
            'corrosion_detection': {
                'corrosion_threshold': 0.2,  # 腐蚀区域阈值
            },
            'spalling_detection': {
                'spalling_area_threshold': 100,  # 剥落最小面积(mm²)
            },
            'calibration': {
                'gps_accuracy': 0.1,  # GPS精度(m)
            },
            'advanced_analysis': {
                'thermal_analysis': True,
                'multispectral_analysis': False,
                '3d_reconstruction': True,
            }
        }
        
        # 如果提供了配置文件，则加载
        if config_path and os.path.exists(config_path):
            self.load_config(config_path)
            
        # 初始化结果存储
        self.results = {}
        self.defects_database = pd.DataFrame()
        self.flight_path_data = None
        self.orthomosaic = None
        self.digital_surface_model = None
        
        # 坐标系转换器 (WGS84 to UTM)
        self.transformer = Transformer.from_crs("EPSG:4326", "EPSG:32633", always_xy=True)
        
    def load_config(self, config_path):
        """加载配置文件"""
        with open(config_path, 'r') as f:
            user_config = json.load(f)
            # 深度更新配置
            for key, value in user_config.items():
                if key in self.config and isinstance(value, dict):
                    self.config[key].update(value)
                else:
                    self.config[key] = value
    
    def calculate_ground_sample_distance(self):
        """计算地面采样距离(GSD) - 每个像素代表的实际尺寸"""
        drone_config = self.config['drone_params']
        gsd = (drone_config['flight_altitude'] * drone_config['sensor_width_mm'] * 1000) / \
              (drone_config['focal_length_mm'] * drone_config['camera_resolution'][0])
        return gsd  # mm/pixel
    
    def process_drone_imagery(self, image_folder, flight_log_path=None):
        """
        处理无人机采集的图像序列
        
        参数:
            image_folder: 图像文件夹路径
            flight_log_path: 飞行日志路径
        """
        print("开始处理无人机图像数据...")
        
        # 计算GSD
        self.gsd = self.calculate_ground_sample_distance()
        print(f"地面采样距离(GSD): {self.gsd:.2f} mm/像素")
        
        # 加载飞行日志数据
        if flight_log_path:
            self.flight_path_data = self.load_flight_log(flight_log_path)
        
        # 获取所有图像文件
        image_files = sorted(glob.glob(os.path.join(image_folder, "*.jpg")) + 
                           glob.glob(os.path.join(image_folder, "*.png")))
        
        if not image_files:
            raise ValueError("在指定文件夹中未找到图像文件")
        
        print(f"找到 {len(image_files)} 张图像")
        
        all_results = []
        ortho_images = []
        
        for i, img_path in enumerate(image_files):
            print(f"处理图像 {i+1}/{len(image_files)}: {os.path.basename(img_path)}")
            
            # 读取图像
            image = cv2.imread(img_path)
            if image is None:
                print(f"无法读取图像: {img_path}")
                continue
            
            # 图像预处理 - 针对无人机视角优化
            processed_image = self.preprocess_drone_image(image)
            
            # 综合缺陷检测
            inspection_result = self.comprehensive_drone_inspection(processed_image, img_path)
            
            # 地理参考信息
            if self.flight_path_data.any() and i < len(self.flight_path_data):
                inspection_result['gps_coords'] = self.flight_path_data[i]
                inspection_result['gsd'] = self.gsd
            
            all_results.append(inspection_result)
            
            # 为正射影像准备图像
            ortho_images.append(processed_image)
        
        # 生成正射影像（简化版）
        if len(ortho_images) > 1:
            self.orthomosaic = self.create_simple_orthomosaic(ortho_images)
        
        # 综合分析所有结果
        comprehensive_report = self.analyze_comprehensive_results(all_results)
        
        return comprehensive_report
    
    def preprocess_drone_image(self, image):
        """
        无人机图像预处理
        - 镜头畸变校正
        - 辐射校正
        - 对比度增强
        """
        # 1. 镜头畸变校正（简化版）
        corrected = self.lens_distortion_correction(image)
        
        # 2. 辐射校正
        radiometric_corrected = self.radiometric_correction(corrected)
        
        # 3. 对比度增强 - 针对高空拍摄优化
        enhanced = self.enhance_drone_contrast(radiometric_corrected)
        
        # 4. 图像锐化 - 增强细节
        sharpened = self.sharpen_image(enhanced)
        
        return sharpened
    
    def lens_distortion_correction(self, image):
        """镜头畸变校正（简化实现）"""
        # 在实际应用中应使用相机标定参数
        h, w = image.shape[:2]
        
        # 创建校正映射（使用假设的相机参数）
        camera_matrix = np.array([
            [w, 0, w/2],
            [0, w, h/2],
            [0, 0, 1]
        ], dtype=np.float32)
        
        dist_coeffs = np.array([-0.3, 0.1, 0, 0], dtype=np.float32)  # 假设的畸变系数
        
        # 应用畸变校正
        corrected = cv2.undistort(image, camera_matrix, dist_coeffs)
        
        return corrected
    
    def radiometric_correction(self, image):
        """辐射校正 - 补偿光照变化"""
        # 转换为LAB颜色空间
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        
        # 对亮度通道进行直方图均衡化
        lab[:,:,0] = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8)).apply(lab[:,:,0])
        
        # 转换回BGR
        corrected = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
        
        return corrected
    
    def enhance_drone_contrast(self, image):
        """针对无人机图像的对比度增强"""
        # 自适应对比度增强
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        
        # 使用双边滤波替代引导滤波（避免使用cv2.ximgproc）
        bilateral_l = cv2.bilateralFilter(l, d=9, sigmaColor=75, sigmaSpace=75)
        
        # 合并通道
        enhanced_lab = cv2.merge([bilateral_l, a, b])
        enhanced = cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2BGR)
        
        return enhanced
    
    def sharpen_image(self, image):
        """图像锐化 - 增强结构细节"""
        kernel = np.array([[-1,-1,-1],
                          [-1, 9,-1],
                          [-1,-1,-1]])
        sharpened = cv2.filter2D(image, -1, kernel)
        return sharpened
    
    def comprehensive_drone_inspection(self, image, image_path):
        """
        无人机视角下的综合结构检测
        """
        inspection_result = {
            'image_path': image_path,
            'timestamp': datetime.now().isoformat(),
            'defects_found': False,
            'cracks': [],
            'corrosion': [],
            'spalling': [],  # 混凝土剥落
            'deformation': None,
            'vegetation_encroachment': None,  # 植被侵蚀
            'drainage_issues': None,  # 排水问题
            'overall_condition': '良好'
        }
        
        # 1. 多尺度裂缝检测（针对高空视角优化）
        crack_map, crack_properties = self.advanced_crack_detection(image)
        inspection_result['cracks'] = crack_properties
        
        # 2. 腐蚀检测
        corrosion_map, corrosion_properties = self.enhanced_corrosion_detection(image)
        inspection_result['corrosion'] = corrosion_properties
        
        # 3. 混凝土剥落检测
        spalling_map, spalling_properties = self.spalling_detection(image)
        inspection_result['spalling'] = spalling_properties
        
        # 4. 植被侵蚀检测
        vegetation_analysis = self.detect_vegetation_encroachment(image)
        inspection_result['vegetation_encroachment'] = vegetation_analysis
        
        # 5. 排水问题检测
        drainage_analysis = self.analyze_drainage_issues(image)
        inspection_result['drainage_issues'] = drainage_analysis
        
        # 6. 结构变形初步分析
        deformation_analysis = self.preliminary_deformation_analysis(image)
        inspection_result['deformation'] = deformation_analysis
        
        # 评估整体状况
        inspection_result = self.evaluate_drone_inspection_condition(inspection_result)
        
        return inspection_result
    
    def advanced_crack_detection(self, image):
        """
        高级裂缝检测算法 - 针对无人机视角优化
        结合多尺度分析和深度学习思想
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        
        # 1. 多尺度线状特征检测
        multi_scale_cracks = self.multi_scale_line_detection(gray)
        
        # 2. 基于纹理分析的裂缝检测
        texture_based_cracks = self.texture_based_crack_detection(gray)
        
        # 3. 基于边缘连接的裂缝检测
        edge_based_cracks = self.edge_based_crack_detection(gray)
        
        # 4. 融合多种检测结果
        combined_cracks = self.fuse_crack_detections([
            multi_scale_cracks, 
            texture_based_cracks, 
            edge_based_cracks
        ])
        
        # 5. 后处理
        final_crack_map = self.post_process_cracks(combined_cracks)
        
        # 6. 分析裂缝属性
        crack_properties = self.analyze_crack_properties(final_crack_map)
        
        return final_crack_map, crack_properties
    
    def multi_scale_line_detection(self, image):
        """多尺度线状特征检测"""
        scales = [0.5, 1.0, 2.0]  # 多尺度分析
        all_maps = []
        
        for scale in scales:
            if scale != 1.0:
                scaled_img = cv2.resize(image, None, fx=scale, fy=scale)
            else:
                scaled_img = image.copy()
            
            # Frangi滤波器 - 专门用于血管/裂缝检测
            frangi_ridges = self.frangi_filter(scaled_img)
            
            # 尺度还原
            if scale != 1.0:
                frangi_ridges = cv2.resize(frangi_ridges, (image.shape[1], image.shape[0]))
            
            all_maps.append(frangi_ridges)
        
        # 融合多尺度结果
        combined = np.mean(all_maps, axis=0)
        _, binary_map = cv2.threshold(combined, 0.1, 255, cv2.THRESH_BINARY)
        
        return binary_map.astype(np.uint8)
    
    def frangi_filter(self, image, scale_range=(1, 10), scale_ratio=2):
        """
        Frangi滤波器 - 用于线状结构增强
        专门针对裂缝等线状特征优化
        """
        # 计算Hessian矩阵
        def hessian_matrix(img, sigma):
            # 高斯二阶导数
            size = int(6 * sigma + 1)
            if size % 2 == 0:
                size += 1
                
            # 计算二阶导数
            dxx = cv2.GaussianBlur(img, (size, size), sigma, sigma, borderType=cv2.BORDER_REFLECT)
            dxx = cv2.Sobel(dxx, cv2.CV_64F, 2, 0, ksize=3)
            
            dyy = cv2.GaussianBlur(img, (size, size), sigma, sigma, borderType=cv2.BORDER_REFLECT)
            dyy = cv2.Sobel(dyy, cv2.CV_64F, 0, 2, ksize=3)
            
            dxy = cv2.GaussianBlur(img, (size, size), sigma, sigma, borderType=cv2.BORDER_REFLECT)
            dxy = cv2.Sobel(dxy, cv2.CV_64F, 1, 1, ksize=3)
            
            return dxx, dyy, dxy
        
        # 多尺度Frangi响应
        frangi_response = np.zeros_like(image, dtype=np.float64)
        
        for sigma in np.linspace(scale_range[0], scale_range[1], 5):
            dxx, dyy, dxy = hessian_matrix(image, sigma)
            
            # 计算特征值
            lambda1 = 0.5 * (dxx + dyy + np.sqrt((dxx - dyy)**2 + 4 * dxy**2))
            lambda2 = 0.5 * (dxx + dyy - np.sqrt((dxx - dyy)**2 + 4 * dxy**2))
            
            # Frangi血管度量
            Rb = (lambda2 / (lambda1 + 1e-8))**2  # 斑点状度量
            S = np.sqrt(lambda1**2 + lambda2**2)   # 二阶范数
            
            # 组合响应
            response = np.exp(-Rb / 0.5) * (1 - np.exp(-S / 0.5))
            
            frangi_response = np.maximum(frangi_response, response)
        
        # 归一化
        frangi_response = (frangi_response - frangi_response.min()) / (frangi_response.max() - frangi_response.min())
        
        return frangi_response
    
    def texture_based_crack_detection(self, image):
        """基于纹理分析的裂缝检测"""
        # 计算局部二值模式
        radius = 2
        n_points = 8 * radius
        lbp = feature.local_binary_pattern(image, n_points, radius, method='uniform')
        
        # 计算LBP方差 - 裂缝区域通常有较高的纹理变化
        lbp_var = ndimage.generic_filter(lbp, np.std, size=5)
        
        # 阈值处理
        _, texture_map = cv2.threshold(lbp_var.astype(np.uint8), 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        return texture_map
    
    def edge_based_crack_detection(self, image):
        """基于边缘连接的裂缝检测"""
        # 多尺度Canny边缘检测
        edges1 = cv2.Canny(image, 50, 150)
        edges2 = cv2.Canny(image, 100, 200)
        edges_combined = cv2.bitwise_or(edges1, edges2)
        
        # 边缘连接
        kernel = np.ones((3, 3), np.uint8)
        connected_edges = cv2.morphologyEx(edges_combined, cv2.MORPH_CLOSE, kernel)
        
        # 去除短边缘
        contours, _ = cv2.findContours(connected_edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        result = np.zeros_like(connected_edges)
        
        for contour in contours:
            if cv2.arcLength(contour, False) > 20:  # 长度阈值
                cv2.drawContours(result, [contour], -1, 255, 1)
        
        return result
    
    def fuse_crack_detections(self, crack_maps):
        """融合多种裂缝检测结果"""
        # 加权融合
        weights = [0.4, 0.3, 0.3]  # 根据可靠性分配权重
        fused = np.zeros_like(crack_maps[0], dtype=np.float32)
        
        for crack_map, weight in zip(crack_maps, weights):
            fused += crack_map.astype(np.float32) * weight
        
        # 二值化
        _, binary_fused = cv2.threshold(fused.astype(np.uint8), 128, 255, cv2.THRESH_BINARY)
        
        return binary_fused
    
    def enhanced_corrosion_detection(self, image):
        """增强的腐蚀检测 - 结合颜色和纹理特征"""
        # 1. 基于颜色的腐蚀检测
        color_corrosion = self.color_based_corrosion_detection(image)
        
        # 2. 基于纹理的腐蚀检测
        texture_corrosion = self.advanced_texture_corrosion_detection(image)
        
        # 3. 基于形状的腐蚀检测
        shape_corrosion = self.shape_based_corrosion_detection(image)
        
        # 融合结果
        combined = cv2.bitwise_or(color_corrosion, texture_corrosion)
        combined = cv2.bitwise_or(combined, shape_corrosion)
        
        # 后处理
        final_corrosion = self.post_process_corrosion(combined)
        
        # 分析属性
        corrosion_properties = self.analyze_corrosion_properties(final_corrosion)
        
        return final_corrosion, corrosion_properties
    
    def color_based_corrosion_detection(self, image):
        """基于颜色的腐蚀检测"""
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        # 定义腐蚀颜色范围（锈色、变色区域）
        lower_rust1 = np.array([0, 50, 50])
        upper_rust1 = np.array([15, 255, 255])
        lower_rust2 = np.array([160, 50, 50])
        upper_rust2 = np.array([180, 255, 255])
        
        # 定义变色区域（褪色、污渍）
        lower_discoloration = np.array([0, 0, 50])
        upper_discoloration = np.array([180, 50, 200])
        
        # 创建掩码
        mask_rust1 = cv2.inRange(hsv, lower_rust1, upper_rust1)
        mask_rust2 = cv2.inRange(hsv, lower_rust2, upper_rust2)
        mask_discoloration = cv2.inRange(hsv, lower_discoloration, upper_discoloration)
        
        combined_mask = cv2.bitwise_or(mask_rust1, mask_rust2)
        combined_mask = cv2.bitwise_or(combined_mask, mask_discoloration)
        
        return combined_mask
    
    def advanced_texture_corrosion_detection(self, image):
        """基于高级纹理特征的腐蚀检测"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # 计算多尺度局部熵
        entropy_maps = []
        for window_size in [5, 9, 13]:
            entropy = ndimage.generic_filter(gray, self.calculate_entropy, size=window_size)
            entropy_maps.append(entropy)
        
        # 融合多尺度熵
        combined_entropy = np.mean(entropy_maps, axis=0)
        
        # 阈值处理
        _, texture_mask = cv2.threshold(combined_entropy.astype(np.uint8), 0, 255, 
                                      cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        return texture_mask
    
    def shape_based_corrosion_detection(self, image):
        """基于形状特征的腐蚀检测"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # 计算梯度幅值
        grad_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        grad_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        gradient_magnitude = np.sqrt(grad_x**2 + grad_y**2)
        
        # 腐蚀区域通常有复杂的边界形状
        # 使用梯度变化检测不规则区域
        _, shape_mask = cv2.threshold(gradient_magnitude.astype(np.uint8), 0, 255, 
                                    cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        return shape_mask
    
    def spalling_detection(self, image):
        """混凝土剥落检测"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # 1. 基于纹理的剥落检测
        texture_spalling = self.texture_based_spalling_detection(gray)
        
        # 2. 基于颜色的剥落检测
        color_spalling = self.color_based_spalling_detection(image)
        
        # 3. 基于形状的剥落检测
        shape_spalling = self.shape_based_spalling_detection(gray)
        
        # 融合结果
        combined = cv2.bitwise_or(texture_spalling, color_spalling)
        combined = cv2.bitwise_or(combined, shape_spalling)
        
        # 后处理
        final_spalling = self.post_process_spalling(combined)
        
        # 分析属性
        spalling_properties = self.analyze_spalling_properties(final_spalling)
        
        return final_spalling, spalling_properties
    
    def texture_based_spalling_detection(self, image):
        """基于纹理的剥落检测"""
        # 剥落区域通常有粗糙的纹理
        lbp = feature.local_binary_pattern(image, 24, 3, method='uniform')
        lbp_hist, _ = np.histogram(lbp.ravel(), bins=256, range=(0, 256))
        
        # 找到高纹理变化的区域
        texture_variance = ndimage.generic_filter(image, np.std, size=7)
        _, texture_mask = cv2.threshold(texture_variance.astype(np.uint8), 0, 255, 
                                      cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        return texture_mask
    
    def color_based_spalling_detection(self, image):
        """基于颜色的剥落检测"""
        # 剥落区域通常颜色较浅（暴露的混凝土）
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l_channel = lab[:,:,0]
        
        # 高亮度区域可能是剥落
        _, color_mask = cv2.threshold(l_channel, 200, 255, cv2.THRESH_BINARY)
        
        return color_mask
    
    def shape_based_spalling_detection(self, image):
        """基于形状的剥落检测"""
        # 剥落区域通常有不规则的形状
        edges = cv2.Canny(image, 50, 150)
        
        # 填充闭合区域
        kernel = np.ones((5, 5), np.uint8)
        closed_edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)
        
        # 找到轮廓
        contours, _ = cv2.findContours(closed_edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        shape_mask = np.zeros_like(image)
        for contour in contours:
            area = cv2.contourArea(contour)
            if area > 100:  # 面积阈值
                cv2.drawContours(shape_mask, [contour], -1, 255, -1)
        
        return shape_mask
    
    def detect_vegetation_encroachment(self, image):
        """检测植被侵蚀"""
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        # 定义植被颜色范围（绿色）
        lower_green = np.array([35, 50, 50])
        upper_green = np.array([85, 255, 255])
        
        # 创建植被掩码
        vegetation_mask = cv2.inRange(hsv, lower_green, upper_green)
        
        # 计算植被覆盖比例
        vegetation_ratio = np.sum(vegetation_mask > 0) / (image.shape[0] * image.shape[1])
        
        return {
            'vegetation_mask': vegetation_mask,
            'coverage_ratio': vegetation_ratio,
            'risk_level': '高' if vegetation_ratio > 0.1 else '中' if vegetation_ratio > 0.05 else '低'
        }
    
    def analyze_drainage_issues(self, image):
        """分析排水问题"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # 检测积水区域（暗色区域）
        _, dark_regions = cv2.threshold(gray, 50, 255, cv2.THRESH_BINARY_INV)
        
        # 检测水渍痕迹
        edges = cv2.Canny(gray, 50, 150)
        
        # 分析水渍模式
        drainage_analysis = {
            'water_accumulation_areas': dark_regions,
            'stain_patterns': edges,
            'water_accumulation_ratio': np.sum(dark_regions > 0) / (image.shape[0] * image.shape[1]),
            'drainage_risk': '需要检查' if np.sum(dark_regions > 0) > 1000 else '正常'
        }
        
        return drainage_analysis
    
    def preliminary_deformation_analysis(self, image):
        """初步变形分析"""
        # 基于图像特征的简单变形分析
        # 在实际应用中应结合3D点云数据
        
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # 检测直线特征（结构边缘）
        edges = cv2.Canny(gray, 50, 150)
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=50, minLineLength=50, maxLineGap=10)
        
        line_analysis = {
            'detected_lines': lines if lines is not None else [],
            'line_count': len(lines) if lines is not None else 0,
            'deformation_indication': '需要进一步检查' if lines is not None and len(lines) > 20 else '正常'
        }
        
        return line_analysis
    
    def post_process_cracks(self, crack_map):
        """裂缝后处理"""
        # 形态学操作
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        cleaned = cv2.morphologyEx(crack_map, cv2.MORPH_OPEN, kernel)
        
        # 连接断裂的裂缝
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        connected = cv2.morphologyEx(cleaned, cv2.MORPH_CLOSE, kernel)
        
        # 去除小区域
        n_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(connected, connectivity=8)
        
        result = np.zeros_like(connected)
        for i in range(1, n_labels):
            if stats[i, cv2.CC_STAT_AREA] > 30:  # 面积阈值
                result[labels == i] = 255
                
        return result
    
    def post_process_corrosion(self, corrosion_map):
        """腐蚀后处理"""
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        cleaned = cv2.morphologyEx(corrosion_map, cv2.MORPH_OPEN, kernel)
        
        n_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(cleaned, connectivity=8)
        
        result = np.zeros_like(cleaned)
        for i in range(1, n_labels):
            if stats[i, cv2.CC_STAT_AREA] > 100:  # 面积阈值
                result[labels == i] = 255
                
        return result
    
    def post_process_spalling(self, spalling_map):
        """剥落后处理"""
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        cleaned = cv2.morphologyEx(spalling_map, cv2.MORPH_OPEN, kernel)
        
        n_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(cleaned, connectivity=8)
        
        result = np.zeros_like(cleaned)
        for i in range(1, n_labels):
            if stats[i, cv2.CC_STAT_AREA] > 150:  # 面积阈值
                result[labels == i] = 255
                
        return result
    
    def analyze_crack_properties(self, crack_map):
        """分析裂缝属性"""
        contours, _ = cv2.findContours(crack_map, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        crack_properties = []
        
        for contour in contours:
            if len(contour) < 5:
                continue
                
            # 计算裂缝长度
            length = cv2.arcLength(contour, False) * self.gsd
            
            # 计算裂缝宽度（近似）
            rect = cv2.minAreaRect(contour)
            width = min(rect[1]) * self.gsd
            
            # 计算方向
            vx, vy, x, y = cv2.fitLine(contour, cv2.DIST_L2, 0, 0.01, 0.01)
            orientation = np.arctan2(vy, vx)[0] * 180 / np.pi
            
            # 计算面积
            area = cv2.contourArea(contour) * (self.gsd ** 2)
            
            # 计算严重程度
            severity = self.calculate_crack_severity(length, width)
            
            crack_properties.append({
                'length_mm': length,
                'width_mm': width,
                'area_mm2': area,
                'orientation_deg': orientation,
                'severity': severity,
                'contour': contour
            })
            
        return crack_properties
    
    def analyze_corrosion_properties(self, corrosion_map):
        """分析腐蚀属性"""
        contours, _ = cv2.findContours(corrosion_map, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        corrosion_properties = []
        
        for contour in contours:
            area = cv2.contourArea(contour) * (self.gsd ** 2)
            perimeter = cv2.arcLength(contour, True) * self.gsd
            
            # 计算圆形度
            circularity = 4 * np.pi * area / (perimeter ** 2) if perimeter > 0 else 0
            
            # 计算边界框
            x, y, w, h = cv2.boundingRect(contour)
            
            corrosion_properties.append({
                'area_mm2': area,
                'perimeter_mm': perimeter,
                'circularity': circularity,
                'bounding_box': (x, y, w, h),
                'contour': contour
            })
            
        return corrosion_properties
    
    def analyze_spalling_properties(self, spalling_map):
        """分析剥落属性"""
        contours, _ = cv2.findContours(spalling_map, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        spalling_properties = []
        
        for contour in contours:
            area = cv2.contourArea(contour) * (self.gsd ** 2)
            
            if area < self.config['spalling_detection']['spalling_area_threshold']:
                continue
                
            perimeter = cv2.arcLength(contour, True) * self.gsd
            
            # 计算紧凑度
            compactness = (perimeter ** 2) / (4 * np.pi * area) if area > 0 else 0
            
            spalling_properties.append({
                'area_mm2': area,
                'perimeter_mm': perimeter,
                'compactness': compactness,
                'contour': contour,
                'severity': '严重' if area > 1000 else '中等' if area > 500 else '轻微'
            })
            
        return spalling_properties
    
    def calculate_crack_severity(self, length, width):
        """计算裂缝严重程度"""
        if width < 0.1:
            return "轻微"
        elif width < 0.5:
            return "中等"
        else:
            return "严重"
    
    def evaluate_drone_inspection_condition(self, inspection_result):
        """评估无人机检测的整体状况"""
        severe_cracks = sum(1 for crack in inspection_result['cracks'] 
                          if crack['severity'] == '严重')
        corrosion_areas = len(inspection_result['corrosion'])
        severe_spalling = sum(1 for spall in inspection_result['spalling'] 
                            if spall['severity'] == '严重')
        
        total_severe_defects = severe_cracks + severe_spalling
        
        if total_severe_defects > 5:
            inspection_result['overall_condition'] = '危险'
            inspection_result['recommendations'] = ['立即进行专业评估和修复', '考虑限制使用']
        elif total_severe_defects > 2 or corrosion_areas > 5:
            inspection_result['overall_condition'] = '需紧急关注'
            inspection_result['recommendations'] = ['建议在3个月内进行专业检查', '加强监测频率']
        elif total_severe_defects > 0 or corrosion_areas > 2:
            inspection_result['overall_condition'] = '需关注'
            inspection_result['recommendations'] = ['建议在6个月内进行专业检查', '定期监测']
        else:
            inspection_result['overall_condition'] = '良好'
            inspection_result['recommendations'] = ['建议按常规周期进行检查']
            
        inspection_result['defects_found'] = (len(inspection_result['cracks']) > 0 or 
                                            len(inspection_result['corrosion']) > 0 or
                                            len(inspection_result['spalling']) > 0)
        
        return inspection_result
    
    def load_flight_log(self, flight_log_path):
        """加载飞行日志数据"""
        # 简化实现 - 实际应用中应解析具体的飞行日志格式
        try:
            if flight_log_path.endswith('.csv'):
                flight_data = pd.read_csv(flight_log_path)
                # 假设CSV包含latitude, longitude, altitude列
                return flight_data[['latitude', 'longitude', 'altitude']].values
            else:
                print("不支持的飞行日志格式")
                return None
        except Exception as e:
            print(f"加载飞行日志失败: {e}")
            return None
    
    def create_simple_orthomosaic(self, images):
        """创建简化的正射影像"""
        # 在实际应用中应使用专业的摄影测量软件
        # 这里提供简化实现
        
        if len(images) == 0:
            return None
            
        # 简单的图像拼接（实际应用应使用特征匹配和 bundle adjustment）
        try:
            # 使用OpenCV的拼接器
            stitcher = cv2.Stitcher.create(cv2.Stitcher_PANORAMA)
            status, panorama = stitcher.stitch(images)
            
            if status == cv2.Stitcher_OK:
                return panorama
            else:
                print("图像拼接失败，使用第一张图像作为替代")
                return images[0]
        except:
            print("拼接过程出错，使用第一张图像作为替代")
            return images[0]
    
    def analyze_comprehensive_results(self, all_results):
        """综合分析所有检测结果"""
        comprehensive_report = {
            'analysis_timestamp': datetime.now().isoformat(),
            'total_images_processed': len(all_results),
            'overall_structure_condition': '良好',
            'defect_statistics': {},
            'risk_assessment': {},
            'maintenance_recommendations': [],
            'detailed_findings': all_results
        }
        
        # 统计缺陷
        total_cracks = sum(len(result['cracks']) for result in all_results)
        severe_cracks = sum(sum(1 for crack in result['cracks'] if crack['severity'] == '严重') 
                          for result in all_results)
        total_corrosion = sum(len(result['corrosion']) for result in all_results)
        total_spalling = sum(len(result['spalling']) for result in all_results)
        
        comprehensive_report['defect_statistics'] = {
            'total_cracks': total_cracks,
            'severe_cracks': severe_cracks,
            'total_corrosion_areas': total_corrosion,
            'total_spalling_areas': total_spalling
        }
        
        # 风险评估
        risk_score = (severe_cracks * 3 + total_corrosion * 1 + total_spalling * 2) / len(all_results)
        
        if risk_score > 5:
            risk_level = '高风险'
        elif risk_score > 2:
            risk_level = '中等风险'
        else:
            risk_level = '低风险'
            
        comprehensive_report['risk_assessment'] = {
            'risk_score': risk_score,
            'risk_level': risk_level,
            'primary_concerns': []
        }
        
        if severe_cracks > 0:
            comprehensive_report['risk_assessment']['primary_concerns'].append('严重裂缝')
        if total_corrosion > 10:
            comprehensive_report['risk_assessment']['primary_concerns'].append('广泛腐蚀')
        if total_spalling > 5:
            comprehensive_report['risk_assessment']['primary_concerns'].append('多处剥落')
        
        # 维护建议
        if risk_level == '高风险':
            comprehensive_report['maintenance_recommendations'] = [
                '立即进行专业结构评估',
                '制定紧急修复计划',
                '增加监测频率至每月一次',
                '考虑临时加固措施'
            ]
            comprehensive_report['overall_structure_condition'] = '危险'
        elif risk_level == '中等风险':
            comprehensive_report['maintenance_recommendations'] = [
                '6个月内进行详细结构评估',
                '制定预防性维护计划',
                '每季度进行一次无人机监测',
                '重点关注严重缺陷区域'
            ]
            comprehensive_report['overall_structure_condition'] = '需关注'
        else:
            comprehensive_report['maintenance_recommendations'] = [
                '按年度计划进行常规检查',
                '继续定期无人机监测',
                '建立长期结构健康档案'
            ]
            comprehensive_report['overall_structure_condition'] = '良好'
        
        return comprehensive_report
    
    def generate_detailed_report(self, comprehensive_report, output_path):
        """生成详细检测报告"""
        report_content = f"""
无人机建筑结构检测报告
生成时间: {comprehensive_report['analysis_timestamp']}
==================================================

总体概况:
---------
处理图像数量: {comprehensive_report['total_images_processed']}
结构整体状况: {comprehensive_report['overall_structure_condition']}
风险评估等级: {comprehensive_report['risk_assessment']['risk_level']}

缺陷统计:
---------
裂缝总数: {comprehensive_report['defect_statistics']['total_cracks']}
严重裂缝: {comprehensive_report['defect_statistics']['severe_cracks']}
腐蚀区域: {comprehensive_report['defect_statistics']['total_corrosion_areas']}
剥落区域: {comprehensive_report['defect_statistics']['total_spalling_areas']}

主要关注点:
-----------
{chr(10).join(['• ' + concern for concern in comprehensive_report['risk_assessment']['primary_concerns']])}

维护建议:
---------
{chr(10).join(['• ' + recommendation for recommendation in comprehensive_report['maintenance_recommendations']])}

详细发现:
---------
"""
        
        for i, finding in enumerate(comprehensive_report['detailed_findings']):
            report_content += f"\n图像 {i+1}:\n"
            report_content += f"  裂缝: {len(finding['cracks'])} 处\n"
            report_content += f"  腐蚀: {len(finding['corrosion'])} 处\n"
            report_content += f"  剥落: {len(finding['spalling'])} 处\n"
            report_content += f"  状况: {finding['overall_condition']}\n"
        
        # 保存报告
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        print(f"详细报告已保存至: {output_path}")
        return report_content
    
    def visualize_drone_results(self, image, inspection_result, output_path=None):
        """可视化无人机检测结果"""
        fig, axes = plt.subplots(2, 3, figsize=(18, 12))
        fig.suptitle('无人机建筑结构检测分析结果', fontsize=16, fontweight='bold')
        
        # 原始图像
        axes[0, 0].imshow(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        axes[0, 0].set_title('原始无人机图像')
        axes[0, 0].axis('off')
        
        # 裂缝检测结果
        crack_vis = image.copy()
        for crack in inspection_result['cracks']:
            color = (0, 255, 0) if crack['severity'] == '轻微' else \
                   (255, 165, 0) if crack['severity'] == '中等' else (255, 0, 0)
            cv2.drawContours(crack_vis, [crack['contour']], -1, color, 2)
            # 标记严重裂缝
            if crack['severity'] == '严重':
                M = cv2.moments(crack['contour'])
                if M["m00"] != 0:
                    cx = int(M["m10"] / M["m00"])
                    cy = int(M["m01"] / M["m00"])
                    cv2.putText(crack_vis, '!', (cx, cy), cv2.FONT_HERSHEY_SIMPLEX, 
                               1, (0, 0, 255), 2)
            
        axes[0, 1].imshow(cv2.cvtColor(crack_vis, cv2.COLOR_BGR2RGB))
        axes[0, 1].set_title(f'裂缝检测 ({len(inspection_result["cracks"])}处)')
        axes[0, 1].axis('off')
        
        # 腐蚀检测结果
        corrosion_vis = image.copy()
        for corrosion in inspection_result['corrosion']:
            cv2.drawContours(corrosion_vis, [corrosion['contour']], -1, (0, 0, 255), 2)
            
        axes[0, 2].imshow(cv2.cvtColor(corrosion_vis, cv2.COLOR_BGR2RGB))
        axes[0, 2].set_title(f'腐蚀检测 ({len(inspection_result["corrosion"])}处)')
        axes[0, 2].axis('off')
        
        # 剥落检测结果
        spalling_vis = image.copy()
        for spalling in inspection_result['spalling']:
            color = (255, 255, 0) if spalling['severity'] == '轻微' else \
                   (255, 165, 0) if spalling['severity'] == '中等' else (255, 0, 0)
            cv2.drawContours(spalling_vis, [spalling['contour']], -1, color, -1)  # 填充
            
        axes[1, 0].imshow(cv2.cvtColor(spalling_vis, cv2.COLOR_BGR2RGB))
        axes[1, 0].set_title(f'剥落检测 ({len(inspection_result["spalling"])}处)')
        axes[1, 0].axis('off')
        
        # 植被侵蚀
        if inspection_result['vegetation_encroachment']:
            veg_vis = image.copy()
            veg_mask = inspection_result['vegetation_encroachment']['vegetation_mask']
            veg_vis[veg_mask > 0] = [0, 255, 0]  # 绿色高亮植被
            
            axes[1, 1].imshow(cv2.cvtColor(veg_vis, cv2.COLOR_BGR2RGB))
            axes[1, 1].set_title(f'植被侵蚀 ({inspection_result["vegetation_encroachment"]["coverage_ratio"]:.1%})')
            axes[1, 1].axis('off')
        
        # 状况总结
        axes[1, 2].text(0.05, 0.95, "检测结果总结", fontsize=14, fontweight='bold', 
                       transform=axes[1, 2].transAxes)
        axes[1, 2].text(0.05, 0.85, f"整体状况: {inspection_result['overall_condition']}", 
                       fontsize=12, transform=axes[1, 2].transAxes, 
                       color='red' if inspection_result['overall_condition'] != '良好' else 'green')
        axes[1, 2].text(0.05, 0.75, f"裂缝数量: {len(inspection_result['cracks'])}", 
                       fontsize=11, transform=axes[1, 2].transAxes)
        axes[1, 2].text(0.05, 0.65, f"腐蚀区域: {len(inspection_result['corrosion'])}", 
                       fontsize=11, transform=axes[1, 2].transAxes)
        axes[1, 2].text(0.05, 0.55, f"剥落区域: {len(inspection_result['spalling'])}", 
                       fontsize=11, transform=axes[1, 2].transAxes)
        axes[1, 2].text(0.05, 0.45, "主要建议:", fontsize=12, transform=axes[1, 2].transAxes)
        
        for i, rec in enumerate(inspection_result['recommendations']):
            axes[1, 2].text(0.05, 0.35 - i*0.08, f"• {rec}", 
                           fontsize=10, transform=axes[1, 2].transAxes)
        
        axes[1, 2].axis('off')
        
        plt.tight_layout()
        
        if output_path:
            plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
            print(f"结果可视化已保存至: {output_path}")
            
        plt.show()

    def calculate_entropy(self, patch):
        """计算图像块的熵值"""
        if len(patch) == 0:
            return 0
        
        # 计算直方图
        hist, _ = np.histogram(patch, bins=256, range=(0, 256))
        
        # 计算概率
        prob = hist / hist.sum()
        
        # 计算熵（避免log(0)）
        entropy = -np.sum(prob * np.log2(prob + 1e-10))
        
        return entropy
    
    def calculate_entropy(self, patch):
        """计算图像块的熵值"""
        if len(patch) == 0:
            return 0
        
        # 计算直方图
        hist, _ = np.histogram(patch, bins=256, range=(0, 256))
        
        # 计算概率
        prob = hist / hist.sum()
        
        # 计算熵（避免log(0)）
        entropy = -np.sum(prob * np.log2(prob + 1e-10))
        
        return entropy

    def fuse_crack_detections(self, crack_maps):
        """融合多种裂缝检测结果"""
        # 确保所有图像尺寸相同
        target_shape = crack_maps[0].shape
        resized_maps = []
        
        for crack_map in crack_maps:
            if crack_map.shape != target_shape:
                resized_map = cv2.resize(crack_map, (target_shape[1], target_shape[0]))
                resized_maps.append(resized_map)
            else:
                resized_maps.append(crack_map)
        
        # 加权融合
        weights = [0.4, 0.3, 0.3]  # 根据可靠性分配权重
        fused = np.zeros_like(resized_maps[0], dtype=np.float32)
        
        for crack_map, weight in zip(resized_maps, weights):
            fused += crack_map.astype(np.float32) * weight
        
        # 二值化
        _, binary_fused = cv2.threshold(fused.astype(np.uint8), 128, 255, cv2.THRESH_BINARY)
        
        return binary_fused

    def post_process_cracks(self, crack_map):
        """裂缝后处理"""
        # 形态学操作
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        cleaned = cv2.morphologyEx(crack_map, cv2.MORPH_OPEN, kernel)
        
        # 连接断裂的裂缝
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        connected = cv2.morphologyEx(cleaned, cv2.MORPH_CLOSE, kernel)
        
        # 去除小区域
        n_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(connected, connectivity=8)
        
        result = np.zeros_like(connected)
        for i in range(1, n_labels):
            if stats[i, cv2.CC_STAT_AREA] > 30:  # 面积阈值
                result[labels == i] = 255
                
        return result

    def post_process_corrosion(self, corrosion_map):
        """腐蚀后处理"""
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        cleaned = cv2.morphologyEx(corrosion_map, cv2.MORPH_OPEN, kernel)
        
        n_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(cleaned, connectivity=8)
        
        result = np.zeros_like(cleaned)
        for i in range(1, n_labels):
            if stats[i, cv2.CC_STAT_AREA] > 100:  # 面积阈值
                result[labels == i] = 255
                
        return result

    def post_process_spalling(self, spalling_map):
        """剥落后处理"""
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        cleaned = cv2.morphologyEx(spalling_map, cv2.MORPH_OPEN, kernel)
        
        n_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(cleaned, connectivity=8)
        
        result = np.zeros_like(cleaned)
        for i in range(1, n_labels):
            if stats[i, cv2.CC_STAT_AREA] > 150:  # 面积阈值
                result[labels == i] = 255
                
        return result

def create_sample_flight_log(file_path):
    """创建示例飞行日志"""
    import pandas as pd
    
    # 创建示例飞行数据
    flight_data = {
        'latitude': [31.2304, 31.2305, 31.2306, 31.2307, 31.2308],
        'longitude': [121.4737, 121.4738, 121.4739, 121.4740, 121.4741],
        'altitude': [50.0, 50.5, 51.0, 50.8, 50.2]
    }
    
    df = pd.DataFrame(flight_data)
    df.to_csv(file_path, index=False)
    print(f"示例飞行日志已创建: {file_path}")

# 使用示例
def main():
    # 初始化无人机监测系统
    drone_monitor = DroneStructuralMonitoring()
    
    print("=== 无人机建筑结构智能检测系统 ===")
    print("系统初始化完成，准备处理无人机数据...")
    
    # 创建示例图像文件夹（如果不存在）
    image_folder = "drone_images"
    if not os.path.exists(image_folder):
        os.makedirs(image_folder)
        print(f"创建了示例图像文件夹: {image_folder}")
        
        # 生成一个示例图像用于演示
        sample_image = generate_sample_structure_image()
        cv2.imwrite(os.path.join(image_folder, "sample_image.jpg"), sample_image)
        print("已生成示例图像用于演示")
    
    # 创建示例飞行日志（如果不存在）
    flight_log = "flight_log.csv"
    if not os.path.exists(flight_log):
        create_sample_flight_log(flight_log)
        print(f"已创建示例飞行日志: {flight_log}")
    
    try:
        # 处理无人机图像数据
        comprehensive_report = drone_monitor.process_drone_imagery(image_folder, flight_log)
        
        # 生成详细报告
        report_path = f"drone_inspection_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        detailed_report = drone_monitor.generate_detailed_report(comprehensive_report, report_path)
        
        # 打印摘要
        print("\n" + "="*50)
        print("检测完成摘要:")
        print(f"处理图像: {comprehensive_report['total_images_processed']} 张")
        print(f"整体状况: {comprehensive_report['overall_structure_condition']}")
        print(f"风险评估: {comprehensive_report['risk_assessment']['risk_level']}")
        print(f"严重裂缝: {comprehensive_report['defect_statistics']['severe_cracks']} 处")
        print(f"详细报告: {report_path}")
        print("="*50)
        
        # 可视化示例结果（使用第一张图像）
        if comprehensive_report['detailed_findings']:
            sample_image = cv2.imread(comprehensive_report['detailed_findings'][0]['image_path'])
            if sample_image is not None:
                visualization_path = f"visualization_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                drone_monitor.visualize_drone_results(
                    sample_image, 
                    comprehensive_report['detailed_findings'][0],
                    visualization_path
                )
        
    except Exception as e:
        print(f"处理过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        print("切换到演示模式...")
        demo_mode(drone_monitor)

def demo_mode(drone_monitor):
    """演示模式 - 使用生成的示例图像"""
    print("运行演示模式...")
    
    # 创建示例图像
    sample_image = generate_sample_structure_image()
    
    # 保存示例图像到临时文件
    temp_image_path = "temp_demo_image.jpg"
    cv2.imwrite(temp_image_path, sample_image)
    
    try:
        # 模拟处理
        inspection_result = drone_monitor.comprehensive_drone_inspection(sample_image, temp_image_path)
        
        # 可视化结果
        visualization_path = "demo_results.png"
        drone_monitor.visualize_drone_results(sample_image, inspection_result, visualization_path)
        
        print(f"演示模式完成，结果已保存至 {visualization_path}")
        
        # 清理临时文件
        if os.path.exists(temp_image_path):
            os.remove(temp_image_path)
            
    except Exception as e:
        print(f"演示模式出错: {e}")
        import traceback
        traceback.print_exc()

def generate_sample_structure_image():
    """生成示例结构图像用于演示"""
    # 创建混凝土纹理背景
    height, width = 800, 1200
    image = np.ones((height, width, 3), dtype=np.uint8) * 180  # 灰色背景
    
    # 添加混凝土纹理
    noise = np.random.normal(0, 15, (height, width, 3)).astype(np.uint8)
    image = cv2.add(image, noise)
    
    # 添加模拟裂缝
    cv2.line(image, (100, 200), (300, 250), (50, 50, 50), 3)
    cv2.line(image, (400, 150), (500, 400), (50, 50, 50), 2)
    
    # 添加模拟腐蚀区域
    cv2.circle(image, (700, 300), 40, (30, 60, 100), -1)
    
    # 添加模拟剥落区域
    pts = np.array([[800, 500], [900, 480], [950, 550], [850, 570]], np.int32)
    cv2.fillPoly(image, [pts], (200, 200, 200))
    
    return image

if __name__ == "__main__":
    main()