import cv2
import numpy as np
import pytesseract
from PIL import Image, ImageDraw, ImageFont
import sqlite3
import json
import datetime
import time
import threading
import queue
import logging
import os
import hashlib
from flask import Flask, render_template, request, jsonify, send_file
import matplotlib
matplotlib.rc("font", family='Microsoft YaHei')
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.ensemble import RandomForestClassifier, IsolationForest
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler
import pandas as pd
from werkzeug.utils import secure_filename
import zipfile
import io

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("container_system.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 系统配置
class Config:
    DATABASE_PATH = "container_system.db"
    UPLOAD_FOLDER = "uploads"
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'bmp'}
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    CAMERA_POSITIONS = ['front', 'back', 'left', 'right', 'top', 'bottom']
    DAMAGE_THRESHOLDS = {
        'dent': 0.7,
        'scratch': 0.5,
        'corrosion': 0.6,
        'crack': 0.8,
        'deformation': 0.75
    }
    
    def __init__(self):
        os.makedirs(self.UPLOAD_FOLDER, exist_ok=True)

config = Config()

class ContainerImageProcessor:
    """集装箱图像处理器"""
    
    def __init__(self):
        self.damage_detector = DamageDetector()
        self.ocr_engine = OCREngine()
        self.seal_detector = SealDetector()
        
    def process_single_image(self, image, position, container_number=None):
        """处理单张集装箱图像"""
        results = {
            'position': position,
            'container_number': container_number,
            'timestamp': datetime.datetime.now(),
            'damages': [],
            'seal_status': 'unknown',
            'iso_code': '',
            'confidence': 0.0
        }
        
        try:
            # 1. 识别集装箱号和ISO码
            if position in ['front', 'back']:
                ocr_results = self.ocr_engine.process_image(image)
                results['container_number'] = ocr_results.get('container_number', '')
                results['iso_code'] = ocr_results.get('iso_code', '')
                results['confidence'] = ocr_results.get('confidence', 0.0)
            
            # 2. 检查铅封状态
            if position == 'back':
                seal_status = self.seal_detector.detect_seal(image)
                results['seal_status'] = seal_status
            
            # 3. 检测损伤
            damages = self.damage_detector.detect_damages(image, position)
            results['damages'] = damages
            
            logger.info(f"处理{position}面图像完成 - 检测到{len(damages)}处损伤")
            
        except Exception as e:
            logger.error(f"处理{position}面图像时出错: {e}")
        
        return results
    
    def process_all_sides(self, images_dict, container_number=None):
        """处理所有面的图像"""
        all_results = {}
        container_number_found = container_number
        
        for position, image in images_dict.items():
            if position not in config.CAMERA_POSITIONS:
                logger.warning(f"未知的相机位置: {position}")
                continue
                
            result = self.process_single_image(image, position, container_number_found)
            all_results[position] = result
            
            # 如果在这个面上识别到了箱号，更新箱号
            if result['container_number'] and not container_number_found:
                container_number_found = result['container_number']
        
        # 汇总结果
        summary = self.summarize_results(all_results, container_number_found)
        return summary, all_results
    
    def summarize_results(self, all_results, container_number):
        """汇总所有面的处理结果"""
        total_damages = 0
        severe_damages = 0
        seal_status = "unknown"
        iso_code = ""
        
        for position, result in all_results.items():
            total_damages += len(result['damages'])
            severe_damages += len([d for d in result['damages'] if d['severity'] > 0.7])
            
            if result['seal_status'] != 'unknown':
                seal_status = result['seal_status']
            
            if result['iso_code']:
                iso_code = result['iso_code']
        
        summary = {
            'container_number': container_number,
            'iso_code': iso_code,
            'seal_status': seal_status,
            'total_damages': total_damages,
            'severe_damages': severe_damages,
            'overall_condition': self.assess_overall_condition(total_damages, severe_damages),
            'processing_time': datetime.datetime.now(),
            'recommendation': self.generate_recommendation(total_damages, severe_damages, seal_status)
        }
        
        return summary

    def assess_overall_condition(self, total_damages, severe_damages):
        """评估整体状况"""
        if severe_damages > 0:
            return "poor"
        elif total_damages > 3:
            return "fair"
        elif total_damages > 0:
            return "good"
        else:
            return "excellent"
    
    def generate_recommendation(self, total_damages, severe_damages, seal_status):
        """生成处理建议"""
        recommendations = []
        
        if seal_status == "broken":
            recommendations.append("需要安全检查 - 铅封破损")
        elif seal_status == "missing":
            recommendations.append("紧急处理 - 铅封缺失")
        
        if severe_damages > 0:
            recommendations.append("严重损伤 - 需要维修评估")
        elif total_damages > 3:
            recommendations.append("多处损伤 - 建议检查")
        
        if not recommendations:
            recommendations.append("状况良好 - 正常处理")
        
        return recommendations

class DamageDetector:
    """损伤检测器"""
    
    def __init__(self):
        self.detection_methods = {
            'dent': self.detect_dents,
            'scratch': self.detect_scratches,
            'corrosion': self.detect_corrosion,
            'crack': self.detect_cracks,
            'deformation': self.detect_deformation
        }
    
    def detect_damages(self, image, position):
        """检测所有类型的损伤"""
        damages = []
        
        for damage_type, detection_func in self.detection_methods.items():
            detected = detection_func(image, position)
            if detected['found']:
                damages.append({
                    'type': damage_type,
                    'location': position,
                    'severity': detected['severity'],
                    'coordinates': detected.get('coordinates', []),
                    'confidence': detected.get('confidence', 0.0)
                })
        
        return damages
    
    def detect_dents(self, image, position):
        """检测凹陷"""
        # 转换为灰度图
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # 使用边缘检测
        edges = cv2.Canny(gray, 50, 150)
        
        # 查找轮廓
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # 分析轮廓特征
        dent_contours = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if 500 < area < 50000:  # 合理范围的凹陷区域
                perimeter = cv2.arcLength(contour, True)
                circularity = 4 * np.pi * area / (perimeter * perimeter) if perimeter > 0 else 0
                
                # 凹陷通常具有较低的圆形度
                if circularity < 0.3:
                    dent_contours.append(contour)
        
        severity = min(len(dent_contours) * 0.1, 1.0)
        
        return {
            'found': len(dent_contours) > 0,
            'severity': severity,
            'coordinates': [cv2.boundingRect(c) for c in dent_contours],
            'confidence': 0.7
        }
    
    def detect_scratches(self, image, position):
        """检测划痕"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # 使用霍夫线变换检测直线
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=50, 
                               minLineLength=50, maxLineGap=10)
        
        scratch_count = 0
        line_coordinates = []
        
        if lines is not None:
            for line in lines:
                x1, y1, x2, y2 = line[0]
                length = np.sqrt((x2-x1)**2 + (y2-y1)**2)
                
                # 划痕通常是较长的细线
                if length > 100:
                    scratch_count += 1
                    line_coordinates.append((x1, y1, x2, y2))
        
        severity = min(scratch_count * 0.05, 1.0)
        
        return {
            'found': scratch_count > 0,
            'severity': severity,
            'coordinates': line_coordinates,
            'confidence': 0.8
        }
    
    def detect_corrosion(self, image, position):
        """检测腐蚀"""
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        # 定义腐蚀（锈色）的颜色范围
        lower_rust1 = np.array([0, 50, 50])
        upper_rust1 = np.array([10, 255, 255])
        lower_rust2 = np.array([170, 50, 50])
        upper_rust2 = np.array([180, 255, 255])
        
        mask1 = cv2.inRange(hsv, lower_rust1, upper_rust1)
        mask2 = cv2.inRange(hsv, lower_rust2, upper_rust2)
        mask = cv2.bitwise_or(mask1, mask2)
        
        # 计算腐蚀区域比例
        corrosion_ratio = np.sum(mask > 0) / (image.shape[0] * image.shape[1])
        
        found = corrosion_ratio > 0.01  # 超过1%的区域被腐蚀
        
        return {
            'found': found,
            'severity': min(corrosion_ratio * 10, 1.0),
            'confidence': 0.75
        }
    
    def detect_cracks(self, image, position):
        """检测裂缝"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # 使用边缘检测
        edges = cv2.Canny(gray, 100, 200)
        
        # 形态学操作连接断裂的边缘
        kernel = np.ones((3,3), np.uint8)
        edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)
        
        # 查找轮廓
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        crack_contours = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if 10 < area < 1000:  # 裂缝通常是小而细长的
                perimeter = cv2.arcLength(contour, True)
                if perimeter > 0:
                    # 计算细长度
                    elongation = area / (perimeter * perimeter)
                    if elongation < 0.1:  # 细长的轮廓
                        crack_contours.append(contour)
        
        severity = min(len(crack_contours) * 0.15, 1.0)
        
        return {
            'found': len(crack_contours) > 0,
            'severity': severity,
            'coordinates': [cv2.boundingRect(c) for c in crack_contours],
            'confidence': 0.65
        }
    
    def detect_deformation(self, image, position):
        """检测变形"""
        # 变形检测通常需要参考模板或历史图像
        # 这里使用简单的边缘直线度分析
        
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        
        # 检测直线
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=50, 
                               minLineLength=100, maxLineGap=10)
        
        if lines is None:
            return {'found': False, 'severity': 0.0, 'confidence': 0.6}
        
        # 分析直线的角度分布
        angles = []
        for line in lines:
            x1, y1, x2, y2 = line[0]
            angle = np.arctan2(y2-y1, x2-x1) * 180 / np.pi
            angles.append(angle)
        
        # 计算角度标准差，变形会导致直线不规则
        if len(angles) > 1:
            angle_std = np.std(angles)
            deformation_level = min(angle_std / 45, 1.0)  # 归一化
        else:
            deformation_level = 0.0
        
        found = deformation_level > 0.3
        
        return {
            'found': found,
            'severity': deformation_level,
            'confidence': 0.6
        }

class OCREngine:
    """OCR引擎"""
    
    def __init__(self):
        self.container_number_pattern = r'[A-Z]{4}\d{7}'
        self.iso_code_pattern = r'[0-9A-Z]{4}'
    
    def process_image(self, image):
        """处理图像识别箱号和ISO码"""
        # 预处理图像
        processed_image = self.preprocess_image(image)
        
        # 使用pytesseract进行OCR
        try:
            custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
            text = pytesseract.image_to_string(processed_image, config=custom_config)
            
            # 提取箱号和ISO码
            container_number = self.extract_container_number(text)
            iso_code = self.extract_iso_code(text)
            
            confidence = 0.8 if container_number else 0.3
            
            return {
                'container_number': container_number,
                'iso_code': iso_code,
                'confidence': confidence,
                'raw_text': text
            }
            
        except Exception as e:
            logger.error(f"OCR处理失败: {e}")
            return {'container_number': '', 'iso_code': '', 'confidence': 0.0, 'raw_text': ''}
    
    def preprocess_image(self, image):
        """预处理图像以提高OCR精度"""
        # 转换为灰度图
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # 降噪
        denoised = cv2.medianBlur(gray, 3)
        
        # 对比度增强
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        enhanced = clahe.apply(denoised)
        
        # 二值化
        _, binary = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        return binary
    
    def extract_container_number(self, text):
        """从文本中提取集装箱号"""
        import re
        matches = re.findall(self.container_number_pattern, text)
        return matches[0] if matches else ""
    
    def extract_iso_code(self, text):
        """从文本中提取ISO码"""
        import re
        matches = re.findall(self.iso_code_pattern, text)
        # 过滤出符合ISO码格式的（通常是4位数字字母组合）
        valid_codes = [code for code in matches if len(code) == 4 and any(c.isdigit() for c in code)]
        return valid_codes[0] if valid_codes else ""

class SealDetector:
    """铅封检测器"""
    
    def __init__(self):
        self.seal_template = self.create_seal_template()
    
    def create_seal_template(self):
        """创建铅封模板（简化版）"""
        # 在实际系统中，这里应该使用真实的铅封图像样本
        template = np.zeros((50, 50, 3), dtype=np.uint8)
        cv2.circle(template, (25, 25), 20, (255, 255, 255), -1)
        cv2.circle(template, (25, 25), 15, (0, 0, 0), -1)
        return template
    
    def detect_seal(self, image):
        """检测铅封状态"""
        try:
            # 转换为灰度图
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # 模板匹配
            result = cv2.matchTemplate(gray, cv2.cvtColor(self.seal_template, cv2.COLOR_BGR2GRAY), 
                                     cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
            
            # 根据匹配度判断铅封状态
            if max_val > 0.7:
                return "intact"
            elif max_val > 0.3:
                return "broken"
            else:
                return "missing"
                
        except Exception as e:
            logger.error(f"铅封检测失败: {e}")
            return "unknown"

class ContainerDatabase:
    """集装箱数据库管理"""
    
    def __init__(self, db_path):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 集装箱主表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS containers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                container_number TEXT UNIQUE,
                iso_code TEXT,
                created_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 操作记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS operations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                container_number TEXT,
                operation_type TEXT, -- 'in' or 'out'
                seal_status TEXT,
                overall_condition TEXT,
                total_damages INTEGER,
                severe_damages INTEGER,
                timestamp DATETIME,
                location TEXT,
                operator TEXT,
                processing_time REAL,
                FOREIGN KEY (container_number) REFERENCES containers (container_number)
            )
        ''')
        
        # 损伤记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS damages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                container_number TEXT,
                operation_id INTEGER,
                damage_type TEXT,
                damage_location TEXT,
                damage_severity REAL,
                coordinates TEXT, -- JSON格式存储坐标
                timestamp DATETIME,
                FOREIGN KEY (container_number) REFERENCES containers (container_number),
                FOREIGN KEY (operation_id) REFERENCES operations (id)
            )
        ''')
        
        # 图像记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS container_images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                container_number TEXT,
                operation_id INTEGER,
                image_position TEXT,
                image_path TEXT,
                processed_data TEXT, -- JSON格式存储处理结果
                timestamp DATETIME,
                FOREIGN KEY (container_number) REFERENCES containers (container_number),
                FOREIGN KEY (operation_id) REFERENCES operations (id)
            )
        ''')
        
        # 责任界定记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS responsibility (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                container_number TEXT,
                damage_type TEXT,
                damage_location TEXT,
                suspected_operation TEXT,
                confidence REAL,
                evidence TEXT, -- JSON格式存储证据
                resolved BOOLEAN DEFAULT FALSE,
                timestamp DATETIME,
                FOREIGN KEY (container_number) REFERENCES containers (container_number)
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("数据库初始化完成")
    
    def save_operation(self, container_data, operation_type, location="Gate_1", operator="system"):
        """保存操作记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 插入或更新集装箱信息
            cursor.execute('''
                INSERT OR REPLACE INTO containers (container_number, iso_code, last_updated)
                VALUES (?, ?, ?)
            ''', (container_data['container_number'], container_data.get('iso_code', ''), 
                  datetime.datetime.now()))
            
            # 插入操作记录
            cursor.execute('''
                INSERT INTO operations 
                (container_number, operation_type, seal_status, overall_condition, 
                 total_damages, severe_damages, timestamp, location, operator)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                container_data['container_number'],
                operation_type,
                container_data.get('seal_status', 'unknown'),
                container_data.get('overall_condition', 'unknown'),
                container_data.get('total_damages', 0),
                container_data.get('severe_damages', 0),
                container_data.get('processing_time', datetime.datetime.now()),
                location,
                operator
            ))
            
            operation_id = cursor.lastrowid
            
            # 保存损伤记录
            for position, result in container_data.get('detailed_results', {}).items():
                for damage in result.get('damages', []):
                    cursor.execute('''
                        INSERT INTO damages 
                        (container_number, operation_id, damage_type, damage_location, 
                         damage_severity, coordinates, timestamp)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        container_data['container_number'],
                        operation_id,
                        damage['type'],
                        damage['location'],
                        damage['severity'],
                        json.dumps(damage.get('coordinates', [])),
                        datetime.datetime.now()
                    ))
            
            conn.commit()
            logger.info(f"保存操作记录成功 - 集装箱: {container_data['container_number']}")
            return operation_id
            
        except Exception as e:
            logger.error(f"保存操作记录失败: {e}")
            conn.rollback()
            return None
        finally:
            conn.close()
    
    def get_container_history(self, container_number):
        """获取集装箱历史记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT o.operation_type, o.timestamp, o.seal_status, o.overall_condition,
                   o.total_damages, o.severe_damages, o.location, o.operator
            FROM operations o
            WHERE o.container_number = ?
            ORDER BY o.timestamp
        ''', (container_number,))
        
        operations = cursor.fetchall()
        
        # 获取损伤历史
        cursor.execute('''
            SELECT d.damage_type, d.damage_location, d.damage_severity, d.timestamp, o.operation_type
            FROM damages d
            JOIN operations o ON d.operation_id = o.id
            WHERE d.container_number = ?
            ORDER BY d.timestamp
        ''', (container_number,))
        
        damages = cursor.fetchall()
        
        conn.close()
        
        return {
            'operations': operations,
            'damages': damages
        }
    
    def get_damage_responsibility(self, container_number):
        """分析损伤责任"""
        history = self.get_container_history(container_number)
        
        if len(history['operations']) < 2:
            return "无法确定责任 - 需要更多操作记录"
        
        responsibility_analysis = self.analyze_damage_patterns(history)
        return responsibility_analysis
    
    def analyze_damage_patterns(self, history):
        """分析损伤模式"""
        operations = history['operations']
        damages = history['damages']
        
        # 按时间分组损伤
        damage_by_operation = {}
        for damage in damages:
            op_type = damage[4]  # operation_type
            if op_type not in damage_by_operation:
                damage_by_operation[op_type] = []
            damage_by_operation[op_type].append(damage)
        
        # 分析新损伤出现的时间点
        new_damages = []
        previous_damages = set()
        
        for op in operations:
            op_type = op[0]  # operation_type
            op_time = op[1]  # timestamp
            
            current_damages = set()
            if op_type in damage_by_operation:
                for damage in damage_by_operation[op_type]:
                    damage_key = (damage[0], damage[1])  # (type, location)
                    current_damages.add(damage_key)
                    
                    if damage_key not in previous_damages:
                        new_damages.append({
                            'type': damage[0],
                            'location': damage[1],
                            'operation': op_type,
                            'timestamp': op_time,
                            'severity': damage[2]
                        })
            
            previous_damages = current_damages
        
        if new_damages:
            analysis = f"发现{len(new_damages)}处新损伤:\n"
            for damage in new_damages:
                analysis += f"- {damage['type']}在{damage['location']}面 ({damage['operation']}操作时)\n"
            return analysis
        else:
            return "未检测到新损伤，责任无法明确界定"

class ContainerAnalytics:
    """集装箱数据分析"""
    
    def __init__(self, db_path):
        self.db = ContainerDatabase(db_path)
    
    def get_operation_stats(self, days=30):
        """获取操作统计"""
        conn = sqlite3.connect(self.db.db_path)
        
        end_date = datetime.datetime.now()
        start_date = end_date - datetime.timedelta(days=days)
        
        query = '''
            SELECT 
                operation_type,
                COUNT(*) as count,
                AVG(total_damages) as avg_damages,
                AVG(severe_damages) as avg_severe_damages,
                SUM(CASE WHEN seal_status = 'broken' THEN 1 ELSE 0 END) as broken_seals,
                SUM(CASE WHEN seal_status = 'missing' THEN 1 ELSE 0 END) as missing_seals
            FROM operations
            WHERE timestamp >= ? AND timestamp <= ?
            GROUP BY operation_type
        '''
        
        df = pd.read_sql_query(query, conn, params=[start_date, end_date])
        conn.close()
        
        return df.to_dict('records')
    
    def get_damage_heatmap(self):
        """获取损伤热力图数据"""
        conn = sqlite3.connect(self.db.db_path)
        
        query = '''
            SELECT 
                damage_location,
                damage_type,
                COUNT(*) as count,
                AVG(damage_severity) as avg_severity
            FROM damages
            GROUP BY damage_location, damage_type
        '''
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        # 转换为热力图格式
        heatmap_data = {}
        for _, row in df.iterrows():
            location = row['damage_location']
            if location not in heatmap_data:
                heatmap_data[location] = {}
            heatmap_data[location][row['damage_type']] = {
                'count': row['count'],
                'avg_severity': row['avg_severity']
            }
        
        return heatmap_data
    
    def generate_damage_report(self):
        """生成损伤报告"""
        stats = self.get_operation_stats()
        heatmap = self.get_damage_heatmap()
        
        report = {
            'period': '最近30天',
            'total_operations': sum([s['count'] for s in stats]),
            'operation_breakdown': stats,
            'damage_heatmap': heatmap,
            'generated_at': datetime.datetime.now()
        }
        
        return report

class RealTimeProcessor:
    """实时处理器"""
    
    def __init__(self, db_path, image_processor):
        self.db = ContainerDatabase(db_path)
        self.image_processor = image_processor
        self.processing_queue = queue.Queue()
        self.is_running = False
        self.processing_thread = None
    
    def start(self):
        """启动实时处理"""
        self.is_running = True
        self.processing_thread = threading.Thread(target=self._process_queue)
        self.processing_thread.daemon = True
        self.processing_thread.start()
        logger.info("实时处理器已启动")
    
    def stop(self):
        """停止实时处理"""
        self.is_running = False
        if self.processing_thread:
            self.processing_thread.join()
        logger.info("实时处理器已停止")
    
    def add_processing_job(self, images_dict, operation_type, location="Gate_1", operator="system"):
        """添加处理任务"""
        job_id = hashlib.md5(f"{datetime.datetime.now()}{operation_type}".encode()).hexdigest()[:8]
        job = {
            'job_id': job_id,
            'images': images_dict,
            'operation_type': operation_type,
            'location': location,
            'operator': operator,
            'submitted_at': datetime.datetime.now()
        }
        
        self.processing_queue.put(job)
        logger.info(f"添加处理任务 {job_id}")
        return job_id
    
    def _process_queue(self):
        """处理队列中的任务"""
        while self.is_running:
            try:
                job = self.processing_queue.get(timeout=1)
                self._process_job(job)
                self.processing_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"处理任务时出错: {e}")
    
    def _process_job(self, job):
        """处理单个任务"""
        logger.info(f"开始处理任务 {job['job_id']}")
        start_time = time.time()
        
        try:
            # 处理所有面的图像
            summary, detailed_results = self.image_processor.process_all_sides(
                job['images'])
            
            # 添加详细结果到摘要中
            summary['detailed_results'] = detailed_results
            
            # 保存到数据库
            operation_id = self.db.save_operation(
                summary, job['operation_type'], job['location'], job['operator'])
            
            processing_time = time.time() - start_time
            summary['processing_time_seconds'] = processing_time
            
            logger.info(f"任务 {job['job_id']} 处理完成，耗时: {processing_time:.2f}秒")
            
            # 发送处理完成通知
            self._notify_completion(job['job_id'], summary, operation_id)
            
        except Exception as e:
            logger.error(f"处理任务 {job['job_id']} 失败: {e}")
            self._notify_failure(job['job_id'], str(e))
    
    def _notify_completion(self, job_id, results, operation_id):
        """通知处理完成"""
        # 在实际系统中，这里可以发送WebSocket消息、调用回调函数等
        logger.info(f"任务 {job_id} 完成 - 集装箱: {results['container_number']}")
    
    def _notify_failure(self, job_id, error_message):
        """通知处理失败"""
        logger.error(f"任务 {job_id} 失败 - 错误: {error_message}")

# Web应用
app = Flask(__name__)
app.config.from_object(Config)

# 初始化系统组件
image_processor = ContainerImageProcessor()
db = ContainerDatabase(config.DATABASE_PATH)
real_time_processor = RealTimeProcessor(config.DATABASE_PATH, image_processor)
analytics = ContainerAnalytics(config.DATABASE_PATH)

# 启动实时处理器
real_time_processor.start()

@app.route('/')
def index():
    """主页"""
    return render_template('index.html')

@app.route('/api/process_container', methods=['POST'])
def api_process_container():
    """处理集装箱API"""
    try:
        operation_type = request.form.get('operation_type', 'in')
        location = request.form.get('location', 'Gate_1')
        operator = request.form.get('operator', 'system')
        
        # 获取上传的图像
        images_dict = {}
        for position in config.CAMERA_POSITIONS:
            file = request.files.get(f'image_{position}')
            if file and file.filename:
                # 读取图像
                image_data = file.read()
                nparr = np.frombuffer(image_data, np.uint8)
                image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                
                if image is not None:
                    images_dict[position] = image
                else:
                    return jsonify({'error': f'无法解码{position}面图像'}), 400
        
        if not images_dict:
            return jsonify({'error': '未提供有效图像'}), 400
        
        # 提交处理任务
        job_id = real_time_processor.add_processing_job(
            images_dict, operation_type, location, operator)
        
        return jsonify({
            'job_id': job_id,
            'status': 'processing',
            'message': '任务已提交处理'
        })
        
    except Exception as e:
        logger.error(f"API处理错误: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/container_info/<container_number>')
def api_container_info(container_number):
    """获取集装箱信息"""
    try:
        history = db.get_container_history(container_number)
        responsibility = db.get_damage_responsibility(container_number)
        
        return jsonify({
            'container_number': container_number,
            'history': history,
            'responsibility_analysis': responsibility
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/analytics/report')
def api_analytics_report():
    """获取分析报告"""
    try:
        report = analytics.generate_damage_report()
        return jsonify(report)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/system_status')
def api_system_status():
    """获取系统状态"""
    status = {
        'database': 'connected',
        'real_time_processor': 'running' if real_time_processor.is_running else 'stopped',
        'queue_size': real_time_processor.processing_queue.qsize(),
        'timestamp': datetime.datetime.now().isoformat()
    }
    return jsonify(status)

# 模拟数据生成函数（用于演示）
def generate_sample_images(container_number):
    """生成样本图像用于演示"""
    images = {}
    
    for position in config.CAMERA_POSITIONS:
        # 创建空白图像
        img = np.ones((400, 600, 3), dtype=np.uint8) * 200
        
        # 添加集装箱外观
        cv2.rectangle(img, (50, 50), (550, 350), (100, 100, 200), 2)
        
        # 添加位置标签
        cv2.putText(img, f"{position} - {container_number}", 
                   (100, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
        
        # 随机添加一些损伤效果
        if np.random.random() < 0.3:
            if position == 'front':
                cv2.circle(img, (200, 200), 30, (0, 0, 255), -1)  # 凹陷
            elif position == 'left':
                cv2.line(img, (100, 150), (300, 180), (255, 0, 0), 3)  # 划痕
        
        images[position] = img
    
    return images

def demo_system():
    """演示系统功能"""
    logger.info("=== 全向视觉集装箱编码系统演示 ===")
    
    # 生成并处理几个样本集装箱
    sample_containers = [
        "CSQU3054383",
        "MSKU9078493", 
        "TGHU4738291",
        "APHU4928374"
    ]
    
    for i, container_number in enumerate(sample_containers):
        operation_type = "in" if i % 2 == 0 else "out"
        
        logger.info(f"处理集装箱 {container_number} ({operation_type}操作)")
        
        # 生成样本图像
        sample_images = generate_sample_images(container_number)
        
        # 处理图像
        summary, detailed_results = image_processor.process_all_sides(
            sample_images, container_number)
        
        # 保存到数据库
        db.save_operation(summary, operation_type)
        
        logger.info(f"处理完成 - 箱号: {summary['container_number']}, "
                   f"损伤: {summary['total_damages']}, "
                   f"建议: {summary['recommendation']}")
        
        time.sleep(1)
    
    # 显示分析报告
    report = analytics.generate_damage_report()
    logger.info(f"分析报告: {report}")
    
    logger.info("=== 演示完成 ===")

if __name__ == "__main__":
    # 运行演示
    demo_system()
    
    # 启动Web服务（在实际部署中）
    # app.run(host='0.0.0.0', port=5000, debug=True)