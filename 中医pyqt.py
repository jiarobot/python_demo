import sys
import cv2
import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from collections import defaultdict
import math
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QComboBox, 
                             QSlider, QTextEdit, QTabWidget, QGroupBox,
                             QFileDialog, QMessageBox, QProgressBar, QSplitter,
                             QCheckBox, QSpinBox, QDoubleSpinBox, QTableWidget,
                             QTableWidgetItem, QHeaderView)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QPixmap, QImage, QFont
import json
from datetime import datetime

class TCMAnalysisThread(QThread):
    """中医分析线程"""
    progress_updated = pyqtSignal(int)
    analysis_completed = pyqtSignal(dict)
    image_processed = pyqtSignal(str, object)

    def __init__(self, image_path, analysis_types):
        super().__init__()
        self.image_path = image_path
        self.analysis_types = analysis_types
        self.tcm_cv = TraditionalChineseMedicineCV()

    def run(self):
        try:
            image = cv2.imread(self.image_path)
            if image is None:
                raise ValueError("无法读取图像文件")

            results = {}
            total_steps = len(self.analysis_types)
            
            for i, analysis_type in enumerate(self.analysis_types):
                try:
                    progress = int((i / total_steps) * 100)
                    self.progress_updated.emit(progress)
                    
                    if analysis_type == "yin_yang":
                        result = self.tcm_cv.calculate_yin_yang_balance(image)
                        results['yin_yang'] = result
                        
                    elif analysis_type == "five_elements":
                        result = self.tcm_cv.detect_five_elements(image)
                        results['five_elements'] = result
                        
                    elif analysis_type == "meridians":
                        result = self.tcm_cv.meridian_energy_analysis(image)
                        results['meridians'] = result
                        
                    elif analysis_type == "acupuncture":
                        result_img, points_data = self.tcm_cv.acupuncture_point_detection(image)
                        results['acupuncture'] = points_data
                        self.image_processed.emit("acupuncture", result_img)
                        
                    elif analysis_type == "qi_flow":
                        result_img, flow_data = self.tcm_cv.qi_flow_analysis(image)
                        results['qi_flow'] = flow_data
                        self.image_processed.emit("qi_flow", result_img)
                        
                    elif analysis_type == "pulse_diagnosis":
                        result = self.tcm_cv.pulse_diagnosis_simulation(image)
                        results['pulse'] = result
                        
                    elif analysis_type == "tongue_diagnosis":
                        result_img, tongue_data = self.tcm_cv.tongue_diagnosis(image)
                        results['tongue'] = tongue_data
                        self.image_processed.emit("tongue", result_img)
                        
                    elif analysis_type == "facial_diagnosis":
                        result_img, facial_data = self.tcm_cv.facial_diagnosis(image)
                        results['facial'] = facial_data
                        self.image_processed.emit("facial", result_img)
                        
                except Exception as e:
                    print(f"分析 {analysis_type} 时出错: {str(e)}")
                    continue

            # 综合诊断
            if len(self.analysis_types) > 1:
                try:
                    results['comprehensive'] = self.tcm_cv.comprehensive_diagnosis(results)
                except Exception as e:
                    print(f"综合诊断时出错: {str(e)}")

            self.progress_updated.emit(100)
            self.analysis_completed.emit(results)

        except Exception as e:
            print(f"分析错误: {str(e)}")
            import traceback
            traceback.print_exc()
            self.progress_updated.emit(0)

class TraditionalChineseMedicineCV:
    def __init__(self):
        # 五行颜色对应关系
        self.five_elements_colors = {
            'wood': {'color': [0, 255, 0], 'range': [30, 80, 30, 80, 30, 80]},
            'fire': {'color': [255, 0, 0], 'range': [80, 255, 30, 80, 30, 80]},
            'earth': {'color': [255, 255, 0], 'range': [80, 255, 80, 255, 30, 80]},
            'metal': {'color': [255, 255, 255], 'range': [200, 255, 200, 255, 200, 255]},
            'water': {'color': [0, 0, 255], 'range': [30, 80, 30, 80, 80, 255]}
        }
        
        # 五行相生相克关系
        self.generating_cycle = {'wood': 'fire', 'fire': 'earth', 'earth': 'metal', 
                               'metal': 'water', 'water': 'wood'}
        self.restraining_cycle = {'wood': 'earth', 'earth': 'water', 'water': 'fire',
                                'fire': 'metal', 'metal': 'wood'}
        
        # 十二经络对应关系
        self.meridians = {
            'lung': {'element': 'metal', 'yin_yang': 'yin'},
            'large_intestine': {'element': 'metal', 'yin_yang': 'yang'},
            'stomach': {'element': 'earth', 'yin_yang': 'yang'},
            'spleen': {'element': 'earth', 'yin_yang': 'yin'},
            'heart': {'element': 'fire', 'yin_yang': 'yin'},
            'small_intestine': {'element': 'fire', 'yin_yang': 'yang'},
            'bladder': {'element': 'water', 'yin_yang': 'yang'},
            'kidney': {'element': 'water', 'yin_yang': 'yin'},
            'pericardium': {'element': 'fire', 'yin_yang': 'yin'},
            'triple_warmer': {'element': 'fire', 'yin_yang': 'yang'},
            'gallbladder': {'element': 'wood', 'yin_yang': 'yang'},
            'liver': {'element': 'wood', 'yin_yang': 'yin'}
        }
        
        # 中医体质类型
        self.constitution_types = {
            '平和质': {'description': '阴阳平衡，气血调和'},
            '气虚质': {'description': '元气不足，易感疲劳'},
            '阳虚质': {'description': '阳气不足，畏寒怕冷'},
            '阴虚质': {'description': '阴液不足，虚火内生'},
            '痰湿质': {'description': '痰湿凝聚，形体肥胖'},
            '湿热质': {'description': '湿热内蕴，面垢油光'},
            '血瘀质': {'description': '血行不畅，肤色晦暗'},
            '气郁质': {'description': '气机郁滞，情绪低落'},
            '特禀质': {'description': '先天失常，过敏体质'}
        }

    def calculate_yin_yang_balance(self, image):
        """计算阴阳平衡"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # 使用OTSU自动阈值
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        yin_energy = np.sum(binary == 0)
        yang_energy = np.sum(binary == 255)
        total_pixels = image.shape[0] * image.shape[1]
        
        yin_ratio = yin_energy / total_pixels
        yang_ratio = yang_energy / total_pixels
        balance = yang_ratio - yin_ratio
        
        # 计算阴阳能量分布图
        yin_map = (gray < 100).astype(np.uint8) * 255
        yang_map = (gray > 150).astype(np.uint8) * 255
        
        return {
            'yin_energy': int(yin_energy),
            'yang_energy': int(yang_energy),
            'yin_ratio': float(yin_ratio),
            'yang_ratio': float(yang_ratio),
            'balance': float(balance),
            'status': '阴阳平衡' if abs(balance) < 0.1 else 
                     ('阳盛阴虚' if balance > 0.1 else '阴盛阳虚'),
            'yin_map': yin_map,
            'yang_map': yang_map
        }

    def detect_five_elements(self, image):
        """五行元素检测"""
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        element_distribution = {}
        element_maps = {}
        
        for element, info in self.five_elements_colors.items():
            try:
                if element == 'wood':  # 绿色
                    lower = np.array([35, 50, 50])
                    upper = np.array([85, 255, 255])
                    mask = cv2.inRange(hsv, lower, upper)
                elif element == 'fire':  # 红色
                    lower1 = np.array([0, 50, 50])
                    upper1 = np.array([10, 255, 255])
                    lower2 = np.array([170, 50, 50])
                    upper2 = np.array([180, 255, 255])
                    mask1 = cv2.inRange(hsv, lower1, upper1)
                    mask2 = cv2.inRange(hsv, lower2, upper2)
                    mask = mask1 + mask2
                elif element == 'earth':  # 黄色
                    lower = np.array([20, 50, 50])
                    upper = np.array([35, 255, 255])
                    mask = cv2.inRange(hsv, lower, upper)
                elif element == 'metal':  # 白色/灰色
                    lower = np.array([0, 0, 100])
                    upper = np.array([180, 50, 255])
                    mask = cv2.inRange(hsv, lower, upper)
                elif element == 'water':  # 蓝色
                    lower = np.array([100, 50, 50])
                    upper = np.array([130, 255, 255])
                    mask = cv2.inRange(hsv, lower, upper)
                
                element_ratio = np.sum(mask > 0) / (image.shape[0] * image.shape[1])
                element_distribution[element] = element_ratio
                element_maps[element] = mask
                
            except Exception as e:
                print(f"检测元素 {element} 时出错: {str(e)}")
                element_distribution[element] = 0.0
                element_maps[element] = np.zeros(image.shape[:2], dtype=np.uint8)
        
        # 分析五行关系
        relationships = self.analyze_element_relationships(element_distribution)
        
        return {
            'distribution': element_distribution,
            'maps': element_maps,
            'relationships': relationships
        }

    def analyze_element_relationships(self, element_distribution):
        """分析五行关系"""
        relationships = {
            'generating': {},
            'restraining': {},
            'imbalances': [],
            'recommendations': []
        }
        
        # 相生关系
        for source, target in self.generating_cycle.items():
            strength = element_distribution[source] * element_distribution[target]
            relationships['generating'][f"{source}生{target}"] = strength
            
        # 相克关系
        for restrainer, restrained in self.restraining_cycle.items():
            strength = element_distribution[restrainer] * element_distribution[restrained]
            relationships['restraining'][f"{restrainer}克{restrained}"] = strength
            
        # 检测不平衡和建议
        avg_element = sum(element_distribution.values()) / len(element_distribution)
        for element, ratio in element_distribution.items():
            if ratio > avg_element * 1.5:
                relationships['imbalances'].append(f"{element}过盛")
                # 根据五行理论给出建议
                if element == 'fire':
                    relationships['recommendations'].append("建议：多食用寒凉食物，如西瓜、黄瓜")
                elif element == 'wood':
                    relationships['recommendations'].append("建议：进行放松运动，避免过度紧张")
            elif ratio < avg_element * 0.5:
                relationships['imbalances'].append(f"{element}不足")
                
        return relationships

    def meridian_energy_analysis(self, image):
        """经络能量分析"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # 使用Gabor滤波器模拟经络能量
        meridians_energy = {}
        for meridian, info in self.meridians.items():
            try:
                # 创建不同方向的Gabor滤波器
                ksize = 31
                sigma = 4.0
                theta = np.pi / 4
                lambd = 10.0
                gamma = 0.5
                psi = 0
                
                kernel = cv2.getGaborKernel((ksize, ksize), sigma, theta, lambd, gamma, psi, ktype=cv2.CV_32F)
                filtered = cv2.filter2D(gray, cv2.CV_32F, kernel)
                
                # 计算能量
                energy = np.mean(np.abs(filtered))
                meridians_energy[meridian] = {
                    'energy': float(energy),
                    'element': info['element'],
                    'yin_yang': info['yin_yang']
                }
            except Exception as e:
                print(f"分析经络 {meridian} 时出错: {str(e)}")
                meridians_energy[meridian] = {
                    'energy': 0.0,
                    'element': info['element'],
                    'yin_yang': info['yin_yang']
                }
            
        return meridians_energy

    def acupuncture_point_detection(self, image):
        """穴位检测"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        result = image.copy()
        points_data = {
            'harris_points': 0,
            'sift_points': 0,
            'orb_points': 0,
            'total_points': 0
        }
        
        try:
            # 1. Harris角点检测
            dst = cv2.cornerHarris(gray, 2, 3, 0.04)
            dst = cv2.dilate(dst, None)
            harris_points = dst > 0.01 * dst.max()
            
            # 2. SIFT特征点
            sift = cv2.SIFT_create()
            kp_sift, des_sift = sift.detectAndCompute(gray, None)
            
            # 3. ORB特征点
            orb = cv2.ORB_create()
            kp_orb, des_orb = orb.detectAndCompute(gray, None)
            
            # 绘制Harris穴位点
            y, x = np.where(harris_points)
            points_data['harris_points'] = len(x)
            for i in range(min(len(x), 50)):  # 限制数量
                cv2.circle(result, (x[i], y[i]), 3, (0, 0, 255), -1)
                cv2.circle(result, (x[i], y[i]), 8, (0, 255, 255), 1)
                
            # 绘制SIFT穴位点
            points_data['sift_points'] = len(kp_sift) if kp_sift else 0
            if kp_sift:
                for kp in kp_sift[:20]:  # 限制数量
                    x, y = int(kp.pt[0]), int(kp.pt[1])
                    cv2.circle(result, (x, y), 2, (255, 0, 0), -1)
                    cv2.circle(result, (x, y), 6, (255, 255, 0), 1)
            
            points_data['orb_points'] = len(kp_orb) if kp_orb else 0
            points_data['total_points'] = points_data['harris_points'] + points_data['sift_points'] + points_data['orb_points']
            
        except Exception as e:
            print(f"穴位检测时出错: {str(e)}")
            
        return result, points_data

    def qi_flow_analysis(self, image):
        """气机运行分析"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        result = image.copy()
        flow_data = {
            'total_flow_points': 0,
            'pyramid_levels': 3,
            'flow_intensity': 0.0
        }
        
        try:
            # 创建图像金字塔
            pyramid_levels = 3
            current_frame = gray.copy()
            
            pyramid = [current_frame]
            for i in range(pyramid_levels-1):
                current_frame = cv2.pyrDown(current_frame)
                pyramid.append(current_frame)
                
            # 在金字塔的每一层计算光流
            flow_points = 0
            total_flow = []
            
            for level, frame in enumerate(pyramid):
                h, w = frame.shape
                
                # 模拟能量流动方向
                for i in range(0, h, 10):
                    for j in range(0, w, 10):
                        # 基于图像梯度计算流动方向
                        if i < h-1 and j < w-1:
                            dx = float(frame[i, j+1] - frame[i, j])
                            dy = float(frame[i+1, j] - frame[i, j])
                            
                            # 归一化
                            magnitude = np.sqrt(dx*dx + dy*dy)
                            if magnitude > 1:
                                dx /= magnitude
                                dy /= magnitude
                                
                            total_flow.append(magnitude)
                            
                            # 在原始图像上绘制箭头
                            scale = 2 ** level  # 金字塔缩放因子
                            start_x = int(j * scale)
                            start_y = int(i * scale)
                            end_x = int(start_x + dx * 20)
                            end_y = int(start_y + dy * 20)
                            
                            if (0 <= start_x < image.shape[1] and 0 <= start_y < image.shape[0] and
                                0 <= end_x < image.shape[1] and 0 <= end_y < image.shape[0]):
                                cv2.arrowedLine(result, (start_x, start_y), (end_x, end_y), 
                                              (0, 255, 0), 1, tipLength=0.3)
                                flow_points += 1
            
            flow_data['total_flow_points'] = flow_points
            flow_data['flow_intensity'] = float(np.mean(total_flow)) if total_flow else 0.0
            
        except Exception as e:
            print(f"气机分析时出错: {str(e)}")
            
        return result, flow_data

    def pulse_diagnosis_simulation(self, image):
        """脉诊模拟"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        try:
            # 1. 计算图像纹理特征
            sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=5)
            sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=5)
            
            gradient_magnitude = np.sqrt(sobelx**2 + sobely**2)
            texture_energy = np.mean(gradient_magnitude)
            
            # 2. 频率分析（模拟脉搏）
            rows, cols = gray.shape
            crow, ccol = rows//2, cols//2
            
            # 创建掩模
            mask = np.zeros((rows, cols, 2), np.uint8)
            r = 30
            center = [crow, ccol]
            x, y = np.ogrid[:rows, :cols]
            mask_area = (x - center[0])**2 + (y - center[1])**2 <= r*r
            mask[mask_area] = 1
            
            dft = cv2.dft(np.float32(gray), flags=cv2.DFT_COMPLEX_OUTPUT)
            dft_shift = np.fft.fftshift(dft)
            
            # 应用掩模
            fshift = dft_shift * mask
            f_ishift = np.fft.ifftshift(fshift)
            img_back = cv2.idft(f_ishift)
            img_back = cv2.magnitude(img_back[:,:,0], img_back[:,:,1])
            
            low_freq_energy = np.mean(img_back)
            high_freq_energy = texture_energy - low_freq_energy
            
            # 3. 脉象判断
            pulse_types = []
            if texture_energy < 50:
                pulse_types.append("沉脉")
            elif texture_energy > 150:
                pulse_types.append("浮脉")
                
            if low_freq_energy > high_freq_energy:
                pulse_types.append("缓脉")
            else:
                pulse_types.append("数脉")
                
            return {
                'texture_energy': float(texture_energy),
                'low_freq_energy': float(low_freq_energy),
                'high_freq_energy': float(high_freq_energy),
                'pulse_types': pulse_types,
                'pulse_description': "、".join(pulse_types)
            }
            
        except Exception as e:
            print(f"脉诊模拟时出错: {str(e)}")
            return {
                'texture_energy': 0.0,
                'low_freq_energy': 0.0,
                'high_freq_energy': 0.0,
                'pulse_types': ["分析失败"],
                'pulse_description': "分析失败"
            }

    def tongue_diagnosis(self, image):
        """舌诊分析"""
        # 转换为HSV颜色空间
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        result = image.copy()
        tongue_data = {
            'tongue_color': "未知",
            'coating_color': "未知",
            'pale_ratio': 0.0,
            'red_ratio': 0.0,
            'purple_ratio': 0.0,
            'white_coating_ratio': 0.0,
            'yellow_coating_ratio': 0.0
        }
        
        try:
            # 舌色分析
            # 1. 淡白舌
            pale_tongue_mask = cv2.inRange(hsv, np.array([0, 0, 100]), np.array([180, 50, 200]))
            pale_ratio = np.sum(pale_tongue_mask > 0) / (image.shape[0] * image.shape[1])
            
            # 2. 红舌
            red_tongue_mask = cv2.inRange(hsv, np.array([0, 50, 50]), np.array([10, 255, 255])) + \
                             cv2.inRange(hsv, np.array([170, 50, 50]), np.array([180, 255, 255]))
            red_ratio = np.sum(red_tongue_mask > 0) / (image.shape[0] * image.shape[1])
            
            # 3. 紫舌
            purple_tongue_mask = cv2.inRange(hsv, np.array([120, 50, 50]), np.array([150, 255, 255]))
            purple_ratio = np.sum(purple_tongue_mask > 0) / (image.shape[0] * image.shape[1])
            
            # 舌苔分析
            # 白苔
            white_coating_mask = cv2.inRange(hsv, np.array([0, 0, 150]), np.array([180, 50, 255]))
            white_coating_ratio = np.sum(white_coating_mask > 0) / (image.shape[0] * image.shape[1])
            
            # 黄苔
            yellow_coating_mask = cv2.inRange(hsv, np.array([20, 50, 50]), np.array([35, 255, 255]))
            yellow_coating_ratio = np.sum(yellow_coating_mask > 0) / (image.shape[0] * image.shape[1])
            
            # 诊断结果
            ratios = [pale_ratio, red_ratio, purple_ratio]
            colors = ["淡白舌", "红舌", "紫舌"]
            tongue_color = colors[np.argmax(ratios)]
            
            coating_color = "白苔" if white_coating_ratio > yellow_coating_ratio else "黄苔"
            
            cv2.putText(result, f"舌色: {tongue_color}", (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.putText(result, f"苔色: {coating_color}", (10, 70), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            
            tongue_data.update({
                'tongue_color': tongue_color,
                'coating_color': coating_color,
                'pale_ratio': float(pale_ratio),
                'red_ratio': float(red_ratio),
                'purple_ratio': float(purple_ratio),
                'white_coating_ratio': float(white_coating_ratio),
                'yellow_coating_ratio': float(yellow_coating_ratio)
            })
            
        except Exception as e:
            print(f"舌诊分析时出错: {str(e)}")
            cv2.putText(result, "舌诊分析失败", (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            
        return result, tongue_data

    def facial_diagnosis(self, image):
        """面诊分析"""
        result = image.copy()
        facial_data = {'face_detected': False, 'face_regions': {}}
        
        try:
            # 使用Haar级联检测器检测面部
            face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, 1.1, 4)
            
            facial_data['face_detected'] = len(faces) > 0
            
            if len(faces) > 0:
                for (x, y, w, h) in faces:
                    # 绘制面部区域
                    cv2.rectangle(result, (x, y), (x+w, y+h), (255, 0, 0), 2)
                    
                    # 分析面部不同区域
                    face_roi = image[y:y+h, x:x+w]
                    
                    if face_roi.size > 0:
                        # 额头区域 (上部1/4)
                        forehead = face_roi[0:h//4, 0:w]
                        if forehead.size > 0:
                            forehead_hsv = cv2.cvtColor(forehead, cv2.COLOR_BGR2HSV)
                            forehead_brightness = np.mean(forehead_hsv[:,:,2])
                        else:
                            forehead_brightness = 0
                        
                        # 面颊区域
                        cheeks = face_roi[h//4:3*h//4, w//4:3*w//4]
                        if cheeks.size > 0:
                            cheeks_hsv = cv2.cvtColor(cheeks, cv2.COLOR_BGR2HSV)
                            cheeks_redness = np.mean(cheeks_hsv[:,:,0])
                        else:
                            cheeks_redness = 0
                        
                        facial_data['face_regions'] = {
                            'forehead_brightness': float(forehead_brightness),
                            'cheeks_redness': float(cheeks_redness)
                        }
                        
                        # 添加诊断文本
                        diagnosis = []
                        if forehead_brightness < 100:
                            diagnosis.append("额头晦暗")
                        if cheeks_redness > 150:
                            diagnosis.append("面颊潮红")
                            
                        if diagnosis:
                            cv2.putText(result, "面部诊断: " + "，".join(diagnosis), 
                                       (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        
        except Exception as e:
            print(f"面诊分析时出错: {str(e)}")
            
        return result, facial_data

    def comprehensive_diagnosis(self, analysis_results):
        """综合诊断"""
        diagnosis = {
            'constitution_type': '未知',
            'syndrome_differentiation': [],
            'recommendations': [],
            'health_score': 0
        }
        
        try:
            # 体质类型判断
            scores = {
                '平和质': 0,
                '气虚质': 0,
                '阳虚质': 0,
                '阴虚质': 0,
                '痰湿质': 0,
                '湿热质': 0,
                '血瘀质': 0,
                '气郁质': 0
            }
            
            # 基于分析结果评分
            if 'yin_yang' in analysis_results:
                yin_yang = analysis_results['yin_yang']
                if yin_yang['status'] == '阳盛阴虚':
                    scores['阴虚质'] += 3
                    scores['湿热质'] += 1
                elif yin_yang['status'] == '阴盛阳虚':
                    scores['阳虚质'] += 3
                    scores['痰湿质'] += 1
                else:
                    scores['平和质'] += 2
                    
            if 'five_elements' in analysis_results:
                elements = analysis_results['five_elements']
                for element, ratio in elements['distribution'].items():
                    if ratio > 0.3:  # 某元素过盛
                        if element == 'fire':
                            scores['湿热质'] += 2
                        elif element == 'earth':
                            scores['痰湿质'] += 2
                        elif element == 'water':
                            scores['阳虚质'] += 1
                            
            # 确定主要体质
            diagnosis['constitution_type'] = max(scores, key=scores.get)
            
            # 证候辨证
            if scores['阴虚质'] >= 2:
                diagnosis['syndrome_differentiation'].append("阴虚火旺")
            if scores['阳虚质'] >= 2:
                diagnosis['syndrome_differentiation'].append("阳气不足")
            if scores['痰湿质'] >= 2:
                diagnosis['syndrome_differentiation'].append("痰湿内阻")
                
            # 健康评分 (0-100)
            base_score = 70
            if diagnosis['constitution_type'] == '平和质':
                base_score += 20
            if len(diagnosis['syndrome_differentiation']) == 0:
                base_score += 10
                
            diagnosis['health_score'] = min(100, base_score)
            
            # 建议
            constitution_desc = self.constitution_types.get(diagnosis['constitution_type'], {})
            diagnosis['recommendations'].append(f"体质类型: {diagnosis['constitution_type']}")
            diagnosis['recommendations'].append(f"特征: {constitution_desc.get('description', '')}")
            
            if diagnosis['health_score'] < 60:
                diagnosis['recommendations'].append("建议：及时就医，进行专业中医调理")
            elif diagnosis['health_score'] < 80:
                diagnosis['recommendations'].append("建议：注意生活习惯，适当进行中医保健")
            else:
                diagnosis['recommendations'].append("建议：保持良好生活习惯，定期检查")
                
        except Exception as e:
            print(f"综合诊断时出错: {str(e)}")
            diagnosis['recommendations'].append("诊断过程中出现错误，请重试")
            
        return diagnosis

class TCMAnalysisApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.image_path = None
        self.current_image = None
        self.analysis_results = {}
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("中医计算机视觉诊断系统")
        self.setGeometry(100, 100, 1400, 900)
        
        # 中央窗口
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QHBoxLayout(central_widget)
        
        # 左侧面板
        left_panel = QWidget()
        left_panel.setMaximumWidth(400)
        left_layout = QVBoxLayout(left_panel)
        
        # 图像加载区域
        load_group = QGroupBox("图像管理")
        load_layout = QVBoxLayout(load_group)
        
        self.load_btn = QPushButton("加载图像")
        self.load_btn.clicked.connect(self.load_image)
        load_layout.addWidget(self.load_btn)
        
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setMinimumHeight(200)
        self.image_label.setStyleSheet("border: 1px solid gray;")
        load_layout.addWidget(self.image_label)
        
        left_layout.addWidget(load_group)
        
        # 分析选项
        analysis_group = QGroupBox("分析选项")
        analysis_layout = QVBoxLayout(analysis_group)
        
        self.analysis_checkboxes = {}
        analyses = [
            ("yin_yang", "阴阳平衡分析"),
            ("five_elements", "五行元素分析"), 
            ("meridians", "经络能量分析"),
            ("acupuncture", "穴位检测"),
            ("qi_flow", "气机运行分析"),
            ("pulse_diagnosis", "脉诊模拟"),
            ("tongue_diagnosis", "舌诊分析"),
            ("facial_diagnosis", "面诊分析")
        ]
        
        for key, text in analyses:
            checkbox = QCheckBox(text)
            self.analysis_checkboxes[key] = checkbox
            analysis_layout.addWidget(checkbox)
            
        self.analyze_btn = QPushButton("开始分析")
        self.analyze_btn.clicked.connect(self.start_analysis)
        analysis_layout.addWidget(self.analyze_btn)
        
        self.progress_bar = QProgressBar()
        analysis_layout.addWidget(self.progress_bar)
        
        left_layout.addWidget(analysis_group)
        
        # 参数设置
        params_group = QGroupBox("分析参数")
        params_layout = QVBoxLayout(params_group)
        
        # 阴阳平衡阈值
        yin_layout = QHBoxLayout()
        yin_layout.addWidget(QLabel("阴阈值:"))
        self.yin_threshold = QSpinBox()
        self.yin_threshold.setRange(0, 255)
        self.yin_threshold.setValue(100)
        yin_layout.addWidget(self.yin_threshold)
        params_layout.addLayout(yin_layout)
        
        yang_layout = QHBoxLayout()
        yang_layout.addWidget(QLabel("阳阈值:"))
        self.yang_threshold = QSpinBox()
        self.yang_threshold.setRange(0, 255)
        self.yang_threshold.setValue(150)
        yang_layout.addWidget(self.yang_threshold)
        params_layout.addLayout(yang_layout)
        
        left_layout.addWidget(params_group)
        
        # 右侧结果显示区域
        right_panel = QTabWidget()
        
        # 综合结果标签页
        self.comprehensive_tab = QWidget()
        comprehensive_layout = QVBoxLayout(self.comprehensive_tab)
        
        self.result_text = QTextEdit()
        self.result_text.setFont(QFont("宋体", 10))
        comprehensive_layout.addWidget(self.result_text)
        
        right_panel.addTab(self.comprehensive_tab, "综合诊断")
        
        # 可视化结果标签页
        self.visualization_tab = QWidget()
        visualization_layout = QVBoxLayout(self.visualization_tab)
        
        self.vis_label = QLabel()
        self.vis_label.setAlignment(Qt.AlignCenter)
        self.vis_label.setMinimumSize(600, 400)
        self.vis_label.setStyleSheet("border: 1px solid gray;")
        visualization_layout.addWidget(self.vis_label)
        
        right_panel.addTab(self.visualization_tab, "可视化结果")
        
        # 详细数据标签页
        self.details_tab = QWidget()
        details_layout = QVBoxLayout(self.details_tab)
        
        self.details_table = QTableWidget()
        details_layout.addWidget(self.details_table)
        
        right_panel.addTab(self.details_tab, "详细数据")
        
        # 添加到主布局
        main_layout.addWidget(left_panel)
        main_layout.addWidget(right_panel)
        
    def load_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择图像文件", "", 
            "图像文件 (*.png *.jpg *.jpeg *.bmp *.tiff)"
        )
        
        if file_path:
            self.image_path = file_path
            pixmap = QPixmap(file_path)
            scaled_pixmap = pixmap.scaled(300, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.image_label.setPixmap(scaled_pixmap)
            
    def start_analysis(self):
        if not self.image_path:
            QMessageBox.warning(self, "警告", "请先加载图像文件")
            return
            
        # 获取选中的分析类型
        selected_analyses = []
        for key, checkbox in self.analysis_checkboxes.items():
            if checkbox.isChecked():
                selected_analyses.append(key)
                
        if not selected_analyses:
            QMessageBox.warning(self, "警告", "请选择至少一种分析方法")
            return
            
        self.analyze_btn.setEnabled(False)
        self.progress_bar.setValue(0)
        
        # 创建分析线程
        self.analysis_thread = TCMAnalysisThread(self.image_path, selected_analyses)
        self.analysis_thread.progress_updated.connect(self.update_progress)
        self.analysis_thread.analysis_completed.connect(self.analysis_finished)
        self.analysis_thread.image_processed.connect(self.update_visualization)
        self.analysis_thread.start()
        
    def update_progress(self, value):
        self.progress_bar.setValue(value)
        
    def update_visualization(self, analysis_type, image):
        """更新可视化结果"""
        if image is not None:
            try:
                # 转换OpenCV图像为QPixmap
                if len(image.shape) == 3:  # 彩色图像
                    rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                else:  # 灰度图像
                    rgb_image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
                    
                h, w, ch = rgb_image.shape
                bytes_per_line = ch * w
                qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
                pixmap = QPixmap.fromImage(qt_image)
                scaled_pixmap = pixmap.scaled(600, 400, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.vis_label.setPixmap(scaled_pixmap)
            except Exception as e:
                print(f"更新可视化时出错: {str(e)}")
            
    def analysis_finished(self, results):
        self.analysis_results = results
        self.analyze_btn.setEnabled(True)
        self.display_results()
        
    def display_results(self):
        """显示分析结果"""
        report = "=== 中医计算机视觉诊断报告 ===\n\n"
        report += f"分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        report += "=" * 50 + "\n\n"
        
        # 阴阳平衡结果
        if 'yin_yang' in self.analysis_results:
            yy = self.analysis_results['yin_yang']
            report += "【阴阳平衡分析】\n"
            report += f"阴能量: {yy['yin_energy']:,} ({yy['yin_ratio']:.1%})\n"
            report += f"阳能量: {yy['yang_energy']:,} ({yy['yang_ratio']:.1%})\n"
            report += f"平衡状态: {yy['status']}\n"
            report += f"平衡度: {yy['balance']:.3f}\n\n"
            
        # 五行分析结果
        if 'five_elements' in self.analysis_results:
            fe = self.analysis_results['five_elements']
            report += "【五行元素分析】\n"
            for element, ratio in fe['distribution'].items():
                report += f"{element}: {ratio:.3f}\n"
                
            if fe['relationships']['imbalances']:
                report += "\n五行不平衡:\n"
                for imbalance in fe['relationships']['imbalances']:
                    report += f"  - {imbalance}\n"
                    
            if fe['relationships']['recommendations']:
                report += "\n调理建议:\n"
                for rec in fe['relationships']['recommendations']:
                    report += f"  - {rec}\n"
            report += "\n"
            
        # 经络分析
        if 'meridians' in self.analysis_results:
            report += "【经络能量分析】\n"
            for meridian, data in self.analysis_results['meridians'].items():
                report += f"{meridian}: {data['energy']:.3f} ({data['yin_yang']}-{data['element']})\n"
            report += "\n"
            
        # 穴位检测
        if 'acupuncture' in self.analysis_results:
            acu = self.analysis_results['acupuncture']
            report += "【穴位检测】\n"
            report += f"Harris角点: {acu['harris_points']} 个\n"
            report += f"SIFT特征点: {acu['sift_points']} 个\n"
            report += f"ORB特征点: {acu['orb_points']} 个\n"
            report += f"总检测点: {acu['total_points']} 个\n\n"
            
        # 气机分析
        if 'qi_flow' in self.analysis_results:
            qi = self.analysis_results['qi_flow']
            report += "【气机运行分析】\n"
            report += f"流动点数: {qi['total_flow_points']} 个\n"
            report += f"流动强度: {qi['flow_intensity']:.3f}\n\n"
            
        # 脉诊结果
        if 'pulse' in self.analysis_results:
            pulse = self.analysis_results['pulse']
            report += "【脉诊模拟】\n"
            report += f"纹理能量: {pulse['texture_energy']:.3f}\n"
            report += f"低频能量: {pulse['low_freq_energy']:.3f}\n"
            report += f"高频能量: {pulse['high_freq_energy']:.3f}\n"
            report += f"脉象类型: {pulse['pulse_description']}\n\n"
            
        # 舌诊结果
        if 'tongue' in self.analysis_results:
            tongue = self.analysis_results['tongue']
            report += "【舌诊分析】\n"
            report += f"舌色: {tongue['tongue_color']}\n"
            report += f"苔色: {tongue['coating_color']}\n\n"
            
        # 面诊结果
        if 'facial' in self.analysis_results:
            facial = self.analysis_results['facial']
            report += "【面诊分析】\n"
            report += f"检测到面部: {'是' if facial['face_detected'] else '否'}\n"
            if facial['face_detected']:
                report += f"额头亮度: {facial['face_regions'].get('forehead_brightness', 0):.1f}\n"
                report += f"面颊红润度: {facial['face_regions'].get('cheeks_redness', 0):.1f}\n"
            report += "\n"
            
        # 综合诊断
        if 'comprehensive' in self.analysis_results:
            comp = self.analysis_results['comprehensive']
            report += "【综合诊断结果】\n"
            report += f"体质类型: {comp['constitution_type']}\n"
            report += f"健康评分: {comp['health_score']}/100\n"
            
            if comp['syndrome_differentiation']:
                report += f"证候辨证: {', '.join(comp['syndrome_differentiation'])}\n"
                
            report += "\n健康建议:\n"
            for rec in comp['recommendations']:
                report += f"  - {rec}\n"
                
        self.result_text.setText(report)
        self.update_details_table()
        
    def update_details_table(self):
        """更新详细数据表格"""
        self.details_table.clear()
        
        # 收集所有数据
        rows = []
        for analysis_type, data in self.analysis_results.items():
            if analysis_type == 'comprehensive':
                continue
                
            self.flatten_dict(data, f"{analysis_type}", rows)
            
        # 设置表格
        if rows:
            self.details_table.setRowCount(len(rows))
            self.details_table.setColumnCount(2)
            self.details_table.setHorizontalHeaderLabels(["分析项目", "数值"])
            
            for i, (key, value) in enumerate(rows):
                self.details_table.setItem(i, 0, QTableWidgetItem(str(key)))
                self.details_table.setItem(i, 1, QTableWidgetItem(str(value)))
                
            self.details_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            
    def flatten_dict(self, data, prefix, rows):
        """将嵌套字典展平为表格行"""
        if isinstance(data, dict):
            for key, value in data.items():
                new_prefix = f"{prefix}.{key}" if prefix else key
                self.flatten_dict(value, new_prefix, rows)
        elif isinstance(data, list):
            for i, item in enumerate(data):
                new_prefix = f"{prefix}[{i}]"
                self.flatten_dict(item, new_prefix, rows)
        else:
            rows.append((prefix, data))

def main():
    app = QApplication(sys.argv)
    window = TCMAnalysisApp()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()