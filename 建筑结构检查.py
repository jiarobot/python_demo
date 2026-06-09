import cv2
import numpy as np
import matplotlib
matplotlib.rc("font", family='Microsoft YaHei')
import matplotlib.pyplot as plt
from scipy import ndimage
from skimage import feature, measure, filters, morphology
import json
import os
from datetime import datetime
import pandas as pd
from mpl_toolkits.mplot3d import Axes3D

class StructuralHealthMonitoring:
    def __init__(self, config_path=None):
        """
        初始化建筑结构健康监测系统
        
        参数:
            config_path: 配置文件路径
        """
        # 默认配置
        self.config = {
            'crack_detection': {
                'min_crack_width': 0.1,  # 最小裂缝宽度(mm)
                'max_crack_width': 10,   # 最大裂缝宽度(mm)
                'crack_length_threshold': 5,  # 最小裂缝长度(mm)
            },
            'deformation_detection': {
                'max_allowed_deformation': 0.01,  # 最大允许变形比例
            },
            'corrosion_detection': {
                'corrosion_threshold': 0.3,  # 腐蚀区域阈值
            },
            'calibration': {
                'pixel_to_mm_ratio': 0.1,  # 像素到毫米的转换比例
            }
        }
        
        # 如果提供了配置文件，则加载
        if config_path and os.path.exists(config_path):
            self.load_config(config_path)
            
        # 修复：初始化结果存储，定义正确的列结构
        self.results = {}
        self.defects_database = pd.DataFrame(columns=[
            'timestamp', 'overall_condition', 'crack_count', 
            'severe_crack_count', 'corrosion_area_count', 'defects_found'
        ])
        
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
    
    def multi_scale_crack_detection(self, image, scale_factors=[1.0, 0.5, 2.0]):
        """
        多尺度裂缝检测算法
        
        参数:
            image: 输入图像
            scale_factors: 多尺度因子列表
            
        返回:
            crack_map: 裂缝二值图
            crack_properties: 裂缝属性
        """
        # 转换为灰度图
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
            
        all_crack_maps = []
        
        for scale in scale_factors:
            # 尺度变换
            if scale != 1.0:
                scaled_img = cv2.resize(gray, None, fx=scale, fy=scale, 
                                      interpolation=cv2.INTER_AREA)
            else:
                scaled_img = gray.copy()
                
            # 增强对比度
            enhanced = self.contrast_enhancement(scaled_img)
            
            # 使用多方向Gabor滤波器检测线状特征
            gabor_cracks = self.gabor_crack_detection(enhanced)
            
            # 基于局部二值模式的裂缝检测
            lbp_cracks = self.lbp_crack_detection(enhanced)
            
            # 融合多尺度结果
            combined = cv2.bitwise_or(gabor_cracks, lbp_cracks)
            
            # 尺度还原
            if scale != 1.0:
                combined = cv2.resize(combined, (gray.shape[1], gray.shape[0]), 
                                    interpolation=cv2.INTER_NEAREST)
                
            all_crack_maps.append(combined)
        
        # 融合多尺度检测结果
        final_crack_map = np.zeros_like(gray, dtype=np.uint8)
        for crack_map in all_crack_maps:
            final_crack_map = cv2.bitwise_or(final_crack_map, crack_map)
            
        # 后处理
        final_crack_map = self.post_process_cracks(final_crack_map)
        
        # 提取裂缝属性
        crack_properties = self.analyze_crack_properties(final_crack_map)
        
        return final_crack_map, crack_properties
    
    def gabor_crack_detection(self, image):
        """使用Gabor滤波器检测裂缝"""
        kernels = []
        # 创建多个方向的Gabor滤波器
        for theta in np.arange(0, np.pi, np.pi / 8):
            kernel = cv2.getGaborKernel((21, 21), 5.0, theta, 10.0, 0.5, 0, ktype=cv2.CV_32F)
            kernels.append(kernel)
            
        # 应用滤波器
        responses = []
        for kernel in kernels:
            filtered = cv2.filter2D(image, cv2.CV_8UC3, kernel)
            responses.append(filtered)
            
        # 合并响应
        max_response = np.max(responses, axis=0)
        
        # 阈值处理
        _, crack_map = cv2.threshold(max_response, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        return crack_map.astype(np.uint8)
    
    def lbp_crack_detection(self, image):
        """基于局部二值模式的裂缝检测"""
        # 计算LBP特征
        radius = 3
        n_points = 8 * radius
        lbp = feature.local_binary_pattern(image, n_points, radius, method='uniform')
        
        # 计算LBP直方图
        hist, _ = np.histogram(lbp.ravel(), bins=np.arange(0, n_points + 3), range=(0, n_points + 2))
        
        # 找到最常见的模式（可能是裂缝）
        common_patterns = np.argsort(hist)[-3:]  # 取前3个最常见模式
        
        # 创建裂缝掩码
        crack_mask = np.zeros_like(image, dtype=np.uint8)
        for pattern in common_patterns:
            crack_mask[lbp == pattern] = 255
            
        return crack_mask
    
    def contrast_enhancement(self, image):
        """对比度增强"""
        # CLAHE (对比度受限的自适应直方图均衡化)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(image)
        
        # 非线性对比度拉伸
        enhanced = np.uint8(255 * (enhanced / 255) ** 0.8)
        
        return enhanced
    
    def post_process_cracks(self, crack_map):
        """裂缝后处理"""
        # 形态学操作去除噪声
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        cleaned = cv2.morphologyEx(crack_map, cv2.MORPH_OPEN, kernel)
        
        # 连接断裂的裂缝
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        connected = cv2.morphologyEx(cleaned, cv2.MORPH_CLOSE, kernel)
        
        # 去除小区域
        n_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(connected, connectivity=8)
        
        result = np.zeros_like(connected)
        for i in range(1, n_labels):
            if stats[i, cv2.CC_STAT_AREA] > 50:  # 面积阈值
                result[labels == i] = 255
                
        return result
    
    def analyze_crack_properties(self, crack_map):
        """分析裂缝属性"""
        # 找到轮廓
        contours, _ = cv2.findContours(crack_map, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        crack_properties = []
        pixel_to_mm = self.config['calibration']['pixel_to_mm_ratio']
        
        for contour in contours:
            if len(contour) < 5:
                continue
                
            # 计算裂缝长度
            length = cv2.arcLength(contour, False) * pixel_to_mm
            
            # 计算裂缝宽度（近似）
            rect = cv2.minAreaRect(contour)
            width = min(rect[1]) * pixel_to_mm
            
            # 计算方向
            vx, vy, x, y = cv2.fitLine(contour, cv2.DIST_L2, 0, 0.01, 0.01)
            orientation = np.arctan2(vy, vx)[0] * 180 / np.pi
            
            # 计算面积
            area = cv2.contourArea(contour) * (pixel_to_mm ** 2)
            
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
    
    def calculate_crack_severity(self, length, width):
        """计算裂缝严重程度"""
        if width < 0.1:
            return "轻微"
        elif width < 0.3:
            return "中等"
        else:
            return "严重"
    
    def structural_deformation_analysis(self, point_cloud_1, point_cloud_2):
        """
        结构变形分析
        
        参数:
            point_cloud_1: 基准点云
            point_cloud_2: 当前点云
            
        返回:
            deformation_map: 变形图
            deformation_metrics: 变形指标
        """
        # 点云配准（ICP算法）
        transformation = self.icp_registration(point_cloud_1, point_cloud_2)
        
        # 应用变换
        aligned_cloud = self.apply_transformation(point_cloud_2, transformation)
        
        # 计算变形量
        deformations = np.linalg.norm(point_cloud_1 - aligned_cloud, axis=1)
        
        # 创建变形图
        deformation_map = {
            'max_deformation': np.max(deformations),
            'mean_deformation': np.mean(deformations),
            'deformation_std': np.std(deformations),
            'exceed_threshold': np.sum(deformations > self.config['deformation_detection']['max_allowed_deformation']),
            'deformation_vectors': point_cloud_1 - aligned_cloud
        }
        
        return deformation_map
    
    def icp_registration(self, source, target, max_iterations=50):
        """迭代最近点算法"""
        # 简化的ICP实现
        # 在实际应用中应使用成熟的ICP库如Open3D
        transformation = np.eye(4)
        
        for i in range(max_iterations):
            # 找到最近邻点
            indices = self.find_nearest_neighbors(source, target)
            
            # 计算变换矩阵
            H = self.compute_transformation(source, target[indices])
            
            # 更新变换
            transformation = H @ transformation
            
            # 检查收敛
            if np.linalg.norm(H - np.eye(4)) < 1e-6:
                break
                
        return transformation
    
    def corrosion_detection(self, image):
        """
        腐蚀检测
        
        参数:
            image: 输入图像
            
        返回:
            corrosion_map: 腐蚀区域二值图
            corrosion_properties: 腐蚀属性
        """
        # 转换到HSV颜色空间
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        # 定义腐蚀颜色范围（锈色）
        lower_rust1 = np.array([0, 50, 50])
        upper_rust1 = np.array([10, 255, 255])
        lower_rust2 = np.array([160, 50, 50])
        upper_rust2 = np.array([180, 255, 255])
        
        # 创建掩码
        mask1 = cv2.inRange(hsv, lower_rust1, upper_rust1)
        mask2 = cv2.inRange(hsv, lower_rust2, upper_rust2)
        rust_mask = cv2.bitwise_or(mask1, mask2)
        
        # 纹理分析增强检测
        texture_analysis = self.texture_based_corrosion_detection(image)
        
        # 融合颜色和纹理检测结果
        combined_corrosion = cv2.bitwise_or(rust_mask, texture_analysis)
        
        # 后处理
        corrosion_map = self.post_process_corrosion(combined_corrosion)
        
        # 分析腐蚀属性
        corrosion_properties = self.analyze_corrosion_properties(corrosion_map)
        
        return corrosion_map, corrosion_properties
    
    def texture_based_corrosion_detection(self, image):
        """基于纹理的腐蚀检测"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # 计算局部熵
        entropy_map = ndimage.generic_filter(gray, self.calculate_entropy, size=5)
        
        # 阈值处理
        _, texture_mask = cv2.threshold(entropy_map.astype(np.uint8), 0, 255, 
                                      cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        return texture_mask
    
    def calculate_entropy(self, patch):
        """计算局部熵"""
        hist = np.histogram(patch, bins=256, range=(0, 255))[0]
        hist = hist[hist > 0] / len(patch)
        return -np.sum(hist * np.log2(hist))
    
    def post_process_corrosion(self, corrosion_map):
        """腐蚀后处理"""
        # 形态学操作
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        cleaned = cv2.morphologyEx(corrosion_map, cv2.MORPH_OPEN, kernel)
        
        # 去除小区域
        n_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(cleaned, connectivity=8)
        
        result = np.zeros_like(cleaned)
        for i in range(1, n_labels):
            if stats[i, cv2.CC_STAT_AREA] > 100:  # 面积阈值
                result[labels == i] = 255
                
        return result
    
    def analyze_corrosion_properties(self, corrosion_map):
        """分析腐蚀属性"""
        contours, _ = cv2.findContours(corrosion_map, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        corrosion_properties = []
        pixel_to_mm = self.config['calibration']['pixel_to_mm_ratio']
        
        for contour in contours:
            area = cv2.contourArea(contour) * (pixel_to_mm ** 2)
            perimeter = cv2.arcLength(contour, True) * pixel_to_mm
            
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
    
    def comprehensive_inspection(self, image, previous_image=None, point_cloud=None):
        """
        综合检测
        
        参数:
            image: 当前图像
            previous_image: 前次检测图像（用于变化检测）
            point_cloud: 3D点云数据（可选）
            
        返回:
            inspection_report: 检测报告
        """
        inspection_report = {
            'timestamp': datetime.now().isoformat(),
            'defects_found': False,
            'cracks': [],
            'corrosion': [],
            'deformation': None,
            'overall_condition': '良好',
            'recommendations': []
        }
        
        # 裂缝检测
        crack_map, crack_properties = self.multi_scale_crack_detection(image)
        inspection_report['cracks'] = crack_properties
        
        # 腐蚀检测
        corrosion_map, corrosion_properties = self.corrosion_detection(image)
        inspection_report['corrosion'] = corrosion_properties
        
        # 变化检测（如果有前次图像）
        if previous_image is not None:
            change_analysis = self.change_detection(image, previous_image)
            inspection_report['changes'] = change_analysis
            
        # 评估整体状况
        inspection_report = self.evaluate_overall_condition(inspection_report)
        
        # 存储结果
        self.store_inspection_results(inspection_report)
        
        return inspection_report
    
    def change_detection(self, current_image, previous_image):
        """变化检测"""
        # 转换为灰度
        current_gray = cv2.cvtColor(current_image, cv2.COLOR_BGR2GRAY)
        previous_gray = cv2.cvtColor(previous_image, cv2.COLOR_BGR2GRAY)
        
        # 计算差异
        diff = cv2.absdiff(current_gray, previous_gray)
        
        # 阈值处理
        _, change_map = cv2.threshold(diff, 30, 255, cv2.THRESH_BINARY)
        
        # 分析变化区域
        change_area = np.sum(change_map > 0) / (current_image.shape[0] * current_image.shape[1])
        
        return {
            'change_area_ratio': change_area,
            'change_map': change_map
        }
    
    def evaluate_overall_condition(self, inspection_report):
        """评估整体状况"""
        # 基于检测结果评估结构健康状况
        severe_cracks = sum(1 for crack in inspection_report['cracks'] 
                          if crack['severity'] == '严重')
        corrosion_areas = len(inspection_report['corrosion'])
        
        if severe_cracks > 3 or corrosion_areas > 5:
            inspection_report['overall_condition'] = '危险'
            inspection_report['recommendations'].append('立即进行专业评估和修复')
        elif severe_cracks > 0 or corrosion_areas > 2:
            inspection_report['overall_condition'] = '需关注'
            inspection_report['recommendations'].append('建议在6个月内进行专业检查')
        else:
            inspection_report['overall_condition'] = '良好'
            inspection_report['recommendations'].append('建议按常规周期进行检查')
            
        inspection_report['defects_found'] = (len(inspection_report['cracks']) > 0 or 
                                            len(inspection_report['corrosion']) > 0)
        
        return inspection_report
    
    def store_inspection_results(self, inspection_report):
        """存储检测结果"""
        # 添加到数据库
        new_entry = {
            'timestamp': inspection_report['timestamp'],
            'overall_condition': inspection_report['overall_condition'],
            'crack_count': len(inspection_report['cracks']),
            'severe_crack_count': sum(1 for c in inspection_report['cracks'] 
                                    if c['severity'] == '严重'),
            'corrosion_area_count': len(inspection_report['corrosion']),
            'defects_found': inspection_report['defects_found']
        }
        
        # 修复：使用 pd.concat() 替代已弃用的 append()
        new_entry_df = pd.DataFrame([new_entry])
        if self.defects_database.empty:
            self.defects_database = new_entry_df
        else:
            self.defects_database = pd.concat([self.defects_database, new_entry_df], ignore_index=True)
        
        # 保存详细报告
        report_filename = f"inspection_report_{inspection_report['timestamp'].replace(':', '-')}.json"
        with open(report_filename, 'w') as f:
            json.dump(inspection_report, f, indent=2, default=str)
    
    def generate_trend_analysis(self):
        """生成趋势分析报告"""
        if len(self.defects_database) < 2:
            return "需要更多数据来进行趋势分析"
            
        # 分析缺陷发展趋势
        trend_report = {
            'analysis_date': datetime.now().isoformat(),
            'data_points': len(self.defects_database),
            'crack_trend': '稳定',
            'corrosion_trend': '稳定',
            'overall_trend': '稳定',
            'predictions': {}
        }
        
        # 简单的趋势分析（实际应用中应使用更复杂的时序分析）
        if len(self.defects_database) > 1:
            crack_trend = np.polyfit(range(len(self.defects_database)), 
                                   self.defects_database['crack_count'], 1)[0]
            corrosion_trend = np.polyfit(range(len(self.defects_database)), 
                                       self.defects_database['corrosion_area_count'], 1)[0]
            
            if crack_trend > 0.1:
                trend_report['crack_trend'] = '恶化'
            elif crack_trend < -0.1:
                trend_report['crack_trend'] = '改善'
                
            if corrosion_trend > 0.05:
                trend_report['corrosion_trend'] = '恶化'
            elif corrosion_trend < -0.05:
                trend_report['corrosion_trend'] = '改善'
                
        return trend_report
    
    def visualize_results(self, image, inspection_report, output_path=None):
        """可视化检测结果"""
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        
        # 原始图像
        axes[0, 0].imshow(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        axes[0, 0].set_title('原始图像')
        axes[0, 0].axis('off')
        
        # 裂缝检测结果
        crack_vis = image.copy()
        for crack in inspection_report['cracks']:
            color = (255, 0, 0) if crack['severity'] == '轻微' else \
                   (255, 165, 0) if crack['severity'] == '中等' else (255, 0, 0)
            cv2.drawContours(crack_vis, [crack['contour']], -1, color, 2)
            
        axes[0, 1].imshow(cv2.cvtColor(crack_vis, cv2.COLOR_BGR2RGB))
        axes[0, 1].set_title(f'裂缝检测 (共{len(inspection_report["cracks"])}处)')
        axes[0, 1].axis('off')
        
        # 腐蚀检测结果
        corrosion_vis = image.copy()
        for corrosion in inspection_report['corrosion']:
            cv2.drawContours(corrosion_vis, [corrosion['contour']], -1, (0, 0, 255), 2)
            
        axes[1, 0].imshow(cv2.cvtColor(corrosion_vis, cv2.COLOR_BGR2RGB))
        axes[1, 0].set_title(f'腐蚀检测 (共{len(inspection_report["corrosion"])}处)')
        axes[1, 0].axis('off')
        
        # 状况总结
        axes[1, 1].text(0.1, 0.9, f"整体状况: {inspection_report['overall_condition']}", 
                       fontsize=12, transform=axes[1, 1].transAxes)
        axes[1, 1].text(0.1, 0.7, f"裂缝数量: {len(inspection_report['cracks'])}", 
                       fontsize=12, transform=axes[1, 1].transAxes)
        axes[1, 1].text(0.1, 0.5, f"腐蚀区域: {len(inspection_report['corrosion'])}", 
                       fontsize=12, transform=axes[1, 1].transAxes)
        axes[1, 1].text(0.1, 0.3, "建议:", fontsize=12, transform=axes[1, 1].transAxes)
        for i, rec in enumerate(inspection_report['recommendations']):
            axes[1, 1].text(0.1, 0.2 - i*0.1, f"- {rec}", 
                           fontsize=10, transform=axes[1, 1].transAxes)
        axes[1, 1].axis('off')
        
        plt.tight_layout()
        
        if output_path:
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            
        plt.show()

# 使用示例
def main():
    # 初始化系统
    shm = StructuralHealthMonitoring()
    
    # 加载测试图像
    # 在实际应用中，这里应该从相机或存储中加载真实的结构图像
    sample_image = np.ones((800, 600, 3), dtype=np.uint8) * 128  # 示例图像
    
    # 进行综合检测
    inspection_report = shm.comprehensive_inspection(sample_image)
    
    # 可视化结果
    shm.visualize_results(sample_image, inspection_report)
    
    # 生成趋势分析
    trend_report = shm.generate_trend_analysis()
    print("趋势分析报告:", trend_report)
    
    # 保存配置
    with open('shm_config.json', 'w') as f:
        json.dump(shm.config, f, indent=2)

if __name__ == "__main__":
    main()