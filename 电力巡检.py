import cv2
import numpy as np
import matplotlib.pyplot as plt
from scipy import ndimage
from skimage import feature, exposure, filters, morphology, measure
from sklearn.cluster import KMeans
import json
import os
from datetime import datetime

class PowerInspectionSystem:
    def __init__(self):
        self.config = {
            'insulator_params': {
                'min_area': 500,
                'max_area': 5000,
                'circularity_threshold': 0.6
            },
            'corona_discharge': {
                'blue_threshold': 150,
                'uv_intensity_threshold': 100
            },
            'cable_detection': {
                'hough_threshold': 100,
                'min_line_length': 50,
                'max_line_gap': 20
            }
        }
    
    def preprocess_image(self, image):
        """图像预处理增强"""
        # 自适应直方图均衡化
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        lab[:,:,0] = cv2.createCLAHE(clipLimit=2.0).apply(lab[:,:,0])
        enhanced = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
        
        # 噪声去除
        denoised = cv2.medianBlur(enhanced, 3)
        
        # 锐化增强
        kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
        sharpened = cv2.filter2D(denoised, -1, kernel)
        
        return sharpened
    
    def detect_insulators(self, image):
        """绝缘子检测与缺陷识别"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # 多尺度特征检测
        scales = [1.0, 0.75, 1.25]
        all_contours = []
        
        for scale in scales:
            scaled_img = cv2.resize(gray, None, fx=scale, fy=scale)
            
            # 边缘检测
            edges = cv2.Canny(scaled_img, 50, 150)
            
            # 形态学操作增强圆形特征
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5,5))
            closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)
            
            # 轮廓检测
            contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            for contour in contours:
                area = cv2.contourArea(contour)
                if self.config['insulator_params']['min_area'] < area < self.config['insulator_params']['max_area']:
                    # 计算圆形度
                    perimeter = cv2.arcLength(contour, True)
                    if perimeter > 0:
                        circularity = 4 * np.pi * area / (perimeter * perimeter)
                        if circularity > self.config['insulator_params']['circularity_threshold']:
                            # 逆缩放轮廓坐标
                            if scale != 1.0:
                                contour = (contour / scale).astype(np.int32)
                            all_contours.append(contour)
        
        return all_contours
    
    def analyze_insulator_condition(self, image, contours):
        """绝缘子状态分析"""
        results = []
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        for i, contour in enumerate(contours):
            # 创建掩码
            mask = np.zeros(gray.shape, np.uint8)
            cv2.drawContours(mask, [contour], 0, 255, -1)
            
            # 提取ROI
            x,y,w,h = cv2.boundingRect(contour)
            roi = gray[y:y+h, x:x+w]
            mask_roi = mask[y:y+h, x:x+w]
            
            # 纹理分析 - 裂纹检测
            # 修复：使用graycomatrix替代greycomatrix
            glcm = feature.graycomatrix(roi, [1], [0], symmetric=True, normed=True)
            contrast = feature.graycoprops(glcm, 'contrast')[0,0]
            homogeneity = feature.graycoprops(glcm, 'homogeneity')[0,0]
            
            # 表面污秽分析
            mean_intensity = np.mean(roi[mask_roi > 0])
            std_intensity = np.std(roi[mask_roi > 0])
            
            # 缺陷判断
            has_crack = contrast > 500  # 高对比度可能表示裂纹
            is_dirty = std_intensity > 40  # 高标准差可能表示污秽
            
            result = {
                'id': i,
                'position': (x, y, w, h),
                'has_crack': has_crack,
                'is_dirty': is_dirty,
                'contrast': contrast,
                'homogeneity': homogeneity,
                'intensity_std': std_intensity
            }
            results.append(result)
        
        return results
    
    def detect_corona_discharge(self, image):
        """电晕放电检测"""
        # 转换到HSV空间检测蓝色/紫色光晕
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        # 定义电晕放电颜色范围（蓝色/紫色）
        lower_blue = np.array([100, 50, 50])
        upper_blue = np.array([140, 255, 255])
        
        mask = cv2.inRange(hsv, lower_blue, upper_blue)
        
        # 形态学操作增强检测
        kernel = np.ones((5,5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        
        # 检测连通区域
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        discharge_regions = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if area > 50:  # 过滤小区域
                x,y,w,h = cv2.boundingRect(contour)
                intensity = np.mean(image[y:y+h, x:x+w])
                
                discharge_regions.append({
                    'position': (x, y, w, h),
                    'area': area,
                    'intensity': intensity,
                    'risk_level': 'high' if intensity > 200 else 'medium' if intensity > 150 else 'low'
                })
        
        return discharge_regions
    
    def detect_power_lines(self, image):
        """电力线检测"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # 边缘检测
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        
        # 霍夫线变换检测直线
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, 
                               threshold=self.config['cable_detection']['hough_threshold'],
                               minLineLength=self.config['cable_detection']['min_line_length'],
                               maxLineGap=self.config['cable_detection']['max_line_gap'])
        
        power_lines = []
        if lines is not None:
            for line in lines:
                x1, y1, x2, y2 = line[0]
                length = np.sqrt((x2-x1)**2 + (y2-y1)**2)
                angle = np.abs(np.arctan2(y2-y1, x2-x1) * 180 / np.pi)
                
                # 过滤接近水平的线（可能是电力线）
                if 10 < angle < 170 and length > 100:
                    power_lines.append({
                        'points': [(x1, y1), (x2, y2)],
                        'length': length,
                        'angle': angle
                    })
        
        return power_lines
    
    def detect_foreign_objects(self, image):
        """异物检测"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # 使用局部二值化检测异常区域
        binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                      cv2.THRESH_BINARY, 11, 2)
        
        # 查找轮廓
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        foreign_objects = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if 100 < area < 5000:  # 过滤太大或太小的区域
                # 计算形状特征
                perimeter = cv2.arcLength(contour, True)
                if perimeter > 0:
                    circularity = 4 * np.pi * area / (perimeter * perimeter)
                    
                    # 不规则形状可能是异物
                    if circularity < 0.7:
                        x,y,w,h = cv2.boundingRect(contour)
                        foreign_objects.append({
                            'position': (x, y, w, h),
                            'area': area,
                            'circularity': circularity,
                            'type': 'suspicious_object'
                        })
        
        return foreign_objects
    
    def comprehensive_inspection(self, image_path):
        """综合巡检分析"""
        # 读取图像
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"无法读取图像: {image_path}")
        
        # 预处理
        processed_image = self.preprocess_image(image)
        
        # 各项检测
        insulators = self.detect_insulators(processed_image)
        insulator_analysis = self.analyze_insulator_condition(processed_image, insulators)
        corona_discharge = self.detect_corona_discharge(processed_image)
        power_lines = self.detect_power_lines(processed_image)
        foreign_objects = self.detect_foreign_objects(processed_image)
        
        # 生成报告
        report = {
            'timestamp': datetime.now().isoformat(),
            'image_path': image_path,
            'insulators_found': len(insulators),
            'defective_insulators': len([i for i in insulator_analysis if i['has_crack'] or i['is_dirty']]),
            'corona_discharge_regions': len(corona_discharge),
            'power_lines_detected': len(power_lines),
            'foreign_objects': len(foreign_objects),
            'detailed_analysis': {
                'insulators': insulator_analysis,
                'corona_discharge': corona_discharge,
                'power_lines': power_lines,
                'foreign_objects': foreign_objects
            },
            'overall_risk_level': self.calculate_risk_level(
                insulator_analysis, corona_discharge, foreign_objects
            )
        }
        
        return report, processed_image
    
    def calculate_risk_level(self, insulators, corona, foreign_objects):
        """计算总体风险等级"""
        risk_score = 0
        
        # 绝缘子缺陷
        defective_insulators = len([i for i in insulators if i['has_crack'] or i['is_dirty']])
        risk_score += defective_insulators * 2
        
        # 电晕放电
        high_risk_corona = len([c for c in corona if c['risk_level'] == 'high'])
        risk_score += high_risk_corona * 3
        
        # 异物
        risk_score += len(foreign_objects)
        
        if risk_score >= 5:
            return "HIGH"
        elif risk_score >= 3:
            return "MEDIUM"
        else:
            return "LOW"
    
    def visualize_results(self, image, report, output_path=None):
        """可视化检测结果"""
        result_image = image.copy()
        
        # 绘制绝缘子
        for insulator in report['detailed_analysis']['insulators']:
            x, y, w, h = insulator['position']
            color = (0, 255, 0) if not (insulator['has_crack'] or insulator['is_dirty']) else (0, 0, 255)
            cv2.rectangle(result_image, (x, y), (x+w, y+h), color, 2)
            
            status = "DEFECTIVE" if (insulator['has_crack'] or insulator['is_dirty']) else "OK"
            cv2.putText(result_image, f"Insulator({status})", (x, y-10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        
        # 绘制电晕放电区域
        for discharge in report['detailed_analysis']['corona_discharge']:
            x, y, w, h = discharge['position']
            cv2.rectangle(result_image, (x, y), (x+w, y+h), (255, 0, 255), 2)
            cv2.putText(result_image, f"Corona({discharge['risk_level']})", 
                       (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 255), 1)
        
        # 绘制电力线
        for line in report['detailed_analysis']['power_lines']:
            (x1, y1), (x2, y2) = line['points']
            cv2.line(result_image, (x1, y1), (x2, y2), (255, 255, 0), 2)
            cv2.putText(result_image, "PowerLine", (x1, y1-10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)
        
        # 绘制异物
        for obj in report['detailed_analysis']['foreign_objects']:
            x, y, w, h = obj['position']
            cv2.rectangle(result_image, (x, y), (x+w, y+h), (0, 165, 255), 2)
            cv2.putText(result_image, "ForeignObject", (x, y-10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 165, 255), 1)
        
        # 添加总体信息
        cv2.putText(result_image, 
                   f"Risk Level: {report['overall_risk_level']} | "
                   f"Insulators: {report['insulators_found']}({report['defective_insulators']} defective) | "
                   f"Corona: {len(report['detailed_analysis']['corona_discharge'])}", 
                   (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
        
        if output_path:
            cv2.imwrite(output_path, result_image)
        
        return result_image

# 使用示例和测试代码
def main():
    # 初始化系统
    inspection_system = PowerInspectionSystem()
    
    # 创建测试图像（实际使用时替换为真实电力设备图像）
    def create_test_image():
        # 创建一个模拟电力设备场景
        img = np.ones((600, 800, 3), dtype=np.uint8) * 150  # 灰色背景
        
        # 添加模拟绝缘子（圆形）
        cv2.circle(img, (200, 300), 30, (100, 100, 100), -1)  # 正常绝缘子
        cv2.circle(img, (400, 300), 30, (50, 50, 50), -1)     # 污秽绝缘子
        cv2.ellipse(img, (600, 300), (30, 30), 0, 0, 360, (80, 80, 80), -1)  # 椭圆绝缘子
        
        # 添加模拟电力线
        cv2.line(img, (100, 100), (700, 100), (200, 200, 200), 3)
        cv2.line(img, (100, 150), (700, 150), (200, 200, 200), 3)
        
        # 添加模拟电晕放电（蓝色区域）
        cv2.circle(img, (500, 200), 15, (255, 100, 100), -1)
        
        # 添加模拟异物
        points = np.array([[300, 400], [320, 450], [280, 440]], np.int32)
        cv2.fillPoly(img, [points], (100, 150, 200))
        
        return img
    
    # 生成测试图像
    test_image = create_test_image()
    cv2.imwrite('test_power_equipment.jpg', test_image)
    
    # 执行综合巡检
    try:
        report, processed_img = inspection_system.comprehensive_inspection('test_power_equipment.jpg')
        
        # 保存处理结果
        result_img = inspection_system.visualize_results(
            processed_img, report, 'inspection_result.jpg'
        )
        
        # 打印报告
        print("=" * 50)
        print("电力巡检报告")
        print("=" * 50)
        print(f"检测时间: {report['timestamp']}")
        print(f"发现绝缘子数量: {report['insulators_found']}")
        print(f"缺陷绝缘子数量: {report['defective_insulators']}")
        print(f"电晕放电区域: {len(report['detailed_analysis']['corona_discharge'])}")
        print(f"电力线数量: {len(report['detailed_analysis']['power_lines'])}")
        print(f"异物数量: {len(report['detailed_analysis']['foreign_objects'])}")
        print(f"总体风险等级: {report['overall_risk_level']}")
        print("=" * 50)
        
        # 保存详细报告
        with open('inspection_report.json', 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print("检测完成！结果已保存至 inspection_result.jpg 和 inspection_report.json")
        
    except Exception as e:
        print(f"检测过程中出现错误: {e}")

if __name__ == "__main__":
    main()