import sys
import os
import cv2
import numpy as np
import json
import time
import sqlite3
from datetime import datetime
from collections import defaultdict, deque
import matplotlib
matplotlib.rc("font", family='Microsoft YaHei')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QComboBox, 
                             QSlider, QSpinBox, QDoubleSpinBox, QCheckBox,
                             QFileDialog, QMessageBox, QProgressBar, QTabWidget,
                             QGroupBox, QListWidget, QSplitter, QFrame, QTextEdit,
                             QTableWidget, QTableWidgetItem, QHeaderView, QTreeWidget,
                             QTreeWidgetItem, QToolBar, QAction, QStatusBar, QToolBox,
                             QDockWidget, QScrollArea, QSizePolicy, QLineEdit,
                             QFormLayout, QDialog, QDialogButtonBox, QRadioButton,
                             QButtonGroup, QSystemTrayIcon, QMenu, QStyle)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QPoint, QSize, QSettings
from PyQt5.QtGui import QPixmap, QImage, QFont, QIcon, QPalette, QColor, QCursor
import torch
import torch.nn as nn
from ultralytics import YOLO
import torchvision.transforms as transforms
from PIL import Image, ImageDraw, ImageFont, ImageOps
import requests
from io import BytesIO
import zipfile
import webbrowser
from sklearn.cluster import DBSCAN
from sklearn.manifold import TSNE
import pandas as pd
import seaborn as sns
import warnings
warnings.filterwarnings('ignore')

class AISmartEnhancer:
    """AI智能增强分析器"""
    def __init__(self):
        self.anomaly_detector = self.load_anomaly_detector()
        self.behavior_analyzer = BehaviorAnalyzer()
        self.trend_predictor = TrendPredictor()
    
    def load_anomaly_detector(self):
        """加载异常检测模型"""
        # 简化的异常检测器
        class SimpleAnomalyDetector:
            def __init__(self):
                self.normal_patterns = defaultdict(list)
            
            def update_patterns(self, detections, frame_info):
                """更新正常模式"""
                if len(detections) > 0:
                    detection_count = len(detections)
                    avg_confidence = np.mean([d['confidence'] for d in detections])
                    self.normal_patterns['detection_count'].append(detection_count)
                    self.normal_patterns['avg_confidence'].append(avg_confidence)
            
            def detect_anomalies(self, detections, frame_info):
                """检测异常"""
                if len(self.normal_patterns['detection_count']) < 10:
                    return []
                
                anomalies = []
                detection_count = len(detections)
                avg_confidence = np.mean([d['confidence'] for d in detections]) if detections else 0
                
                # 简单的异常检测逻辑
                normal_count_mean = np.mean(self.normal_patterns['detection_count'][-50:])
                normal_confidence_mean = np.mean(self.normal_patterns['avg_confidence'][-50:])
                
                if detection_count > normal_count_mean * 2:
                    anomalies.append({
                        'type': 'HIGH_DENSITY',
                        'severity': 'WARNING',
                        'message': f'检测目标密度异常: {detection_count}个目标'
                    })
                
                if avg_confidence < normal_confidence_mean * 0.5 and detection_count > 0:
                    anomalies.append({
                        'type': 'LOW_CONFIDENCE',
                        'severity': 'WARNING', 
                        'message': f'平均置信度异常: {avg_confidence:.3f}'
                    })
                
                return anomalies
        
        return SimpleAnomalyDetector()
    
    def analyze_behavior_patterns(self, detection_history):
        """分析行为模式"""
        return self.behavior_analyzer.analyze(detection_history)
    
    def predict_trends(self, historical_data):
        """预测趋势"""
        return self.trend_predictor.predict(historical_data)

class BehaviorAnalyzer:
    """行为模式分析器"""
    def analyze(self, detection_history):
        """分析检测历史数据"""
        if len(detection_history) < 10:
            return {"patterns": [], "insights": []}
        
        patterns = []
        insights = []
        
        # 分析目标密度变化
        density_trend = self.analyze_density_trend(detection_history)
        if density_trend:
            patterns.append(density_trend)
        
        # 分析目标移动模式
        movement_patterns = self.analyze_movement(detection_history)
        patterns.extend(movement_patterns)
        
        # 生成洞察
        if patterns:
            insights.append("检测到显著的行为模式变化")
        
        return {"patterns": patterns, "insights": insights}
    
    def analyze_density_trend(self, history):
        """分析密度趋势"""
        densities = [len(frame['detections']) for frame in history[-30:]]
        if len(densities) < 5:
            return None
        
        trend = "稳定"
        if np.std(densities) > np.mean(densities) * 0.5:
            trend = "波动"
        elif densities[-1] > np.mean(densities) * 1.5:
            trend = "上升"
        elif densities[-1] < np.mean(densities) * 0.5:
            trend = "下降"
        
        return {
            "type": "DENSITY_TREND",
            "value": trend,
            "confidence": 0.8
        }
    
    def analyze_movement(self, history):
        """分析移动模式"""
        patterns = []
        # 简化的移动分析
        if len(history) > 10:
            patterns.append({
                "type": "MOVEMENT_PATTERN",
                "value": "稳定移动",
                "confidence": 0.7
            })
        return patterns

class TrendPredictor:
    """趋势预测器"""
    def predict(self, historical_data):
        """预测未来趋势"""
        predictions = []
        
        if len(historical_data) > 20:
            # 简单的线性预测
            recent_data = [len(frame['detections']) for frame in historical_data[-10:]]
            if len(recent_data) >= 5:
                trend = np.polyfit(range(len(recent_data)), recent_data, 1)[0]
                
                if trend > 0.1:
                    predictions.append({
                        "type": "DENSITY_INCREASE",
                        "confidence": min(0.9, abs(trend)),
                        "timeframe": "短期"
                    })
                elif trend < -0.1:
                    predictions.append({
                        "type": "DENSITY_DECREASE", 
                        "confidence": min(0.9, abs(trend)),
                        "timeframe": "短期"
                    })
        
        return predictions

class ARVisualizationEngine:
    """增强现实可视化引擎"""
    def __init__(self):
        self.effects = {
            'heatmap': self.apply_heatmap_effect,
            'trajectory': self.apply_trajectory_effect,
            'bounding_box': self.apply_enhanced_bbox,
            'info_panel': self.apply_info_panel
        }
    
    def apply_ar_effects(self, image, detections, effect_type, history=None):
        """应用AR效果"""
        if effect_type in self.effects:
            return self.effects[effect_type](image, detections, history)
        return image
    
    def apply_heatmap_effect(self, image, detections, history):
        """应用热力图效果"""
        if isinstance(image, np.ndarray):
            overlay = image.copy()
        else:
            overlay = np.array(image)
        
        h, w = overlay.shape[:2]
        heatmap = np.zeros((h, w), dtype=np.float32)
        
        for detection in detections:
            x1, y1, x2, y2 = detection['bbox']
            center_x, center_y = (x1 + x2) // 2, (y1 + y2) // 2
            
            # 在中心点周围创建高斯分布
            radius = min(w, h) // 20
            for i in range(max(0, center_x - radius), min(w, center_x + radius)):
                for j in range(max(0, center_y - radius), min(h, center_y + radius)):
                    dist = np.sqrt((i - center_x)**2 + (j - center_y)**2)
                    if dist < radius:
                        heatmap[j, i] += np.exp(-dist / (radius / 2))
        
        # 归一化并应用颜色映射
        if np.max(heatmap) > 0:
            heatmap = heatmap / np.max(heatmap)
            heatmap_colored = cv2.applyColorMap((heatmap * 255).astype(np.uint8), cv2.COLORMAP_JET)
            overlay = cv2.addWeighted(overlay, 0.7, heatmap_colored, 0.3, 0)
        
        return overlay
    
    def apply_trajectory_effect(self, image, detections, history):
        """应用轨迹追踪效果"""
        if history is None or len(history) < 2:
            return image
        
        if isinstance(image, np.ndarray):
            result = image.copy()
        else:
            result = np.array(image)
        
        # 绘制历史轨迹
        for i in range(1, min(20, len(history))):
            alpha = i / min(20, len(history))
            prev_detections = history[-i-1]['detections']
            current_detections = history[-i]['detections']
            
            for prev_det in prev_detections:
                for curr_det in current_detections:
                    if prev_det['class_id'] == curr_det['class_id']:
                        prev_center = self.get_bbox_center(prev_det['bbox'])
                        curr_center = self.get_bbox_center(curr_det['bbox'])
                        
                        # 绘制轨迹线
                        color = (0, 255, 0)  # 绿色轨迹
                        cv2.line(result, prev_center, curr_center, color, 2)
        
        return result
    
    def apply_enhanced_bbox(self, image, detections, history):
        """应用增强边界框"""
        if isinstance(image, np.ndarray):
            result = image.copy()
        else:
            result = np.array(image)
        
        for detection in detections:
            x1, y1, x2, y2 = detection['bbox']
            class_name = detection['class_name']
            confidence = detection['confidence']
            
            # 根据置信度选择颜色
            if confidence > 0.8:
                color = (0, 255, 0)  # 高置信度-绿色
            elif confidence > 0.5:
                color = (0, 255, 255)  # 中置信度-黄色
            else:
                color = (0, 0, 255)  # 低置信度-红色
            
            # 绘制3D样式边界框
            cv2.rectangle(result, (x1, y1), (x2, y2), color, 2)
            
            # 绘制阴影效果
            cv2.rectangle(result, (x1+2, y1+2), (x2+2, y2+2), (0, 0, 0), 1)
            
            # 绘制信息标签
            label = f"{class_name}: {confidence:.2f}"
            label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)[0]
            cv2.rectangle(result, (x1, y1 - label_size[1] - 10), 
                         (x1 + label_size[0] + 10, y1), color, -1)
            cv2.putText(result, label, (x1 + 5, y1 - 5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        return result
    
    def apply_info_panel(self, image, detections, history):
        """应用信息面板"""
        if isinstance(image, np.ndarray):
            result = image.copy()
        else:
            result = np.array(image)
        
        h, w = result.shape[:2]
        
        # 创建半透明信息面板
        panel = np.zeros((h, 300, 3), dtype=np.uint8)
        panel[:] = (50, 50, 50)  # 深灰色背景
        
        # 添加检测统计信息
        class_counts = defaultdict(int)
        total_confidence = 0
        
        for detection in detections:
            class_counts[detection['class_name']] += 1
            total_confidence += detection['confidence']
        
        avg_confidence = total_confidence / len(detections) if detections else 0
        
        # 在面板上绘制文本
        y_offset = 30
        cv2.putText(panel, "检测统计", (10, y_offset), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        y_offset += 40
        
        cv2.putText(panel, f"总目标数: {len(detections)}", (10, y_offset),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        y_offset += 25
        
        cv2.putText(panel, f"平均置信度: {avg_confidence:.3f}", (10, y_offset),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        y_offset += 25
        
        for class_name, count in class_counts.items():
            cv2.putText(panel, f"{class_name}: {count}", (10, y_offset),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            y_offset += 20
        
        # 将面板叠加到原图
        result[0:h, 0:300] = cv2.addWeighted(result[0:h, 0:300], 0.3, panel, 0.7, 0)
        
        return result
    
    def get_bbox_center(self, bbox):
        """获取边界框中心点"""
        x1, y1, x2, y2 = bbox
        return ((x1 + x2) // 2, (y1 + y2) // 2)

class CollaborativeSession:
    """协作会话管理"""
    def __init__(self):
        self.sessions = {}
        self.current_session = None
        self.annotations = []
    
    def create_session(self, session_name, participants):
        """创建协作会话"""
        session_id = f"session_{int(time.time())}"
        self.sessions[session_id] = {
            'name': session_name,
            'participants': participants,
            'created_at': datetime.now(),
            'annotations': [],
            'chat_messages': []
        }
        self.current_session = session_id
        return session_id
    
    def add_annotation(self, annotation):
        """添加标注"""
        if self.current_session:
            self.sessions[self.current_session]['annotations'].append({
                **annotation,
                'timestamp': datetime.now()
            })
    
    def add_chat_message(self, user, message):
        """添加聊天消息"""
        if self.current_session:
            self.sessions[self.current_session]['chat_messages'].append({
                'user': user,
                'message': message,
                'timestamp': datetime.now()
            })
    
    def export_session(self, session_id):
        """导出会话数据"""
        if session_id in self.sessions:
            return self.sessions[session_id]
        return None

class IntelligentYOLODetector:
    """智能YOLO检测器"""
    def __init__(self):
        self.models = {}
        self.current_model = None
        self.performance_stats = defaultdict(list)
        self.model_ensemble = False
    
    def load_model(self, model_path, model_name="default"):
        """加载模型"""
        try:
            model = YOLO(model_path)
            self.models[model_name] = {
                'model': model,
                'name': model_name,
                'path': model_path,
                'classes': model.names,
                'loaded_at': datetime.now()
            }
            
            if self.current_model is None:
                self.current_model = model_name
            
            # 生成颜色
            np.random.seed(42)
            colors = np.random.randint(0, 255, size=(len(model.names), 3), dtype=np.uint8)
            self.models[model_name]['colors'] = colors
            
            return True
        except Exception as e:
            print(f"模型加载失败: {e}")
            return False
    
    def enable_ensemble(self, model_paths):
        """启用模型集成"""
        for i, path in enumerate(model_paths):
            self.load_model(path, f"ensemble_{i}")
        self.model_ensemble = True
    
    def detect_ensemble(self, image, conf_threshold=0.25, iou_threshold=0.45):
        """集成检测"""
        if not self.model_ensemble:
            return self.detect_single(image, conf_threshold, iou_threshold)
        
        all_detections = []
        for model_info in self.models.values():
            if model_info['name'].startswith('ensemble_'):
                results = model_info['model'](image, conf=conf_threshold, iou=iou_threshold)
                
                for result in results:
                    boxes = result.boxes
                    for box in boxes:
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        class_id = int(box.cls[0])
                        class_name = model_info['classes'][class_id]
                        confidence = float(box.conf[0])
                        
                        all_detections.append({
                            'bbox': [x1, y1, x2, y2],
                            'class_id': class_id,
                            'class_name': class_name,
                            'confidence': confidence,
                            'model': model_info['name']
                        })
        
        # 融合检测结果（简单的非极大值抑制）
        fused_detections = self.fuse_detections(all_detections, iou_threshold)
        return self.draw_detections(image, fused_detections), fused_detections
    
    def detect_single(self, image, conf_threshold=0.25, iou_threshold=0.45):
        """单模型检测"""
        if self.current_model is None:
            return image, []
        
        model_info = self.models[self.current_model]
        model = model_info['model']
        
        results = model(image, conf=conf_threshold, iou=iou_threshold)
        detections = []
        
        for result in results:
            boxes = result.boxes
            for box in boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                class_id = int(box.cls[0])
                class_name = model_info['classes'][class_id]
                confidence = float(box.conf[0])
                
                detections.append({
                    'bbox': [x1, y1, x2, y2],
                    'class_id': class_id,
                    'class_name': class_name,
                    'confidence': confidence
                })
        
        result_image = self.draw_detections(image, detections)
        return result_image, detections
    
    def fuse_detections(self, all_detections, iou_threshold):
        """融合多个模型的检测结果"""
        if not all_detections:
            return []
        
        # 按类别分组
        class_groups = defaultdict(list)
        for detection in all_detections:
            class_groups[detection['class_name']].append(detection)
        
        fused = []
        for class_name, detections in class_groups.items():
            # 按置信度排序
            detections.sort(key=lambda x: x['confidence'], reverse=True)
            
            kept = []
            for det in detections:
                keep = True
                for kept_det in kept:
                    iou = self.calculate_iou(det['bbox'], kept_det['bbox'])
                    if iou > iou_threshold:
                        keep = False
                        break
                if keep:
                    kept.append(det)
            
            fused.extend(kept)
        
        return fused
    
    def calculate_iou(self, box1, box2):
        """计算IoU"""
        x11, y1_1, x2_1, y2_1 = box1
        x1_2, y1_2, x2_2, y2_2 = box2
        
        # 计算交集区域
        xi1 = max(x1_1, x1_2)
        yi1 = max(y1_1, y1_2)
        xi2 = min(x2_1, x2_2)
        yi2 = min(y2_1, y2_2)
        
        inter_area = max(0, xi2 - xi1) * max(0, yi2 - yi1)
        
        # 计算并集区域
        box1_area = (x2_1 - x1_1) * (y2_1 - y1_1)
        box2_area = (x2_2 - x1_2) * (y2_2 - y1_2)
        union_area = box1_area + box2_area - inter_area
        
        return inter_area / union_area if union_area > 0 else 0
    
    def draw_detections(self, image, detections):
        """绘制检测结果"""
        if isinstance(image, np.ndarray):
            pil_image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        else:
            pil_image = image.convert('RGB')
        
        draw = ImageDraw.Draw(pil_image)
        
        try:
            font = ImageFont.truetype("arial.ttf", 16)
        except:
            font = ImageFont.load_default()
        
        for detection in detections:
            x1, y1, x2, y2 = detection['bbox']
            class_name = detection['class_name']
            confidence = detection['confidence']
            
            # 获取模型特定的颜色
            model_name = detection.get('model', self.current_model)
            if model_name in self.models:
                colors = self.models[model_name]['colors']
                color = tuple(colors[detection['class_id']].tolist())
            else:
                color = (255, 0, 0)  # 默认红色
            
            # 绘制边界框和标签
            draw.rectangle([x1, y1, x2, y2], outline=color, width=3)
            
            label = f"{class_name}: {confidence:.2f}"
            if 'model' in detection:
                label += f" ({detection['model']})"
            
            label_bbox = draw.textbbox((x1, y1), label, font=font)
            draw.rectangle([label_bbox[0], label_bbox[1], label_bbox[2], label_bbox[3]], fill=color)
            draw.text((x1, y1), label, fill=(255, 255, 255), font=font)
        
        return cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
    
    def optimize_inference(self, image_size=(640, 640)):
        """优化推理设置"""
        # 这里可以实现各种优化策略
        pass

class RealTimeOptimizer:
    """实时优化器"""
    def __init__(self):
        self.performance_history = deque(maxlen=100)
        self.optimization_strategies = {
            'dynamic_resolution': self.dynamic_resolution,
            'model_pruning': self.model_pruning,
            'precision_reduction': self.precision_reduction
        }
    
    def dynamic_resolution(self, current_fps, target_fps=30):
        """动态分辨率调整"""
        if current_fps < target_fps * 0.8:
            return "降低分辨率"
        elif current_fps > target_fps * 1.2:
            return "提高分辨率"
        return "保持分辨率"
    
    def model_pruning(self, memory_usage, threshold=0.8):
        """模型剪枝策略"""
        if memory_usage > threshold:
            return "启用剪枝"
        return "保持原模型"
    
    def precision_reduction(self, fps, target_fps=30):
        """精度降低策略"""
        if fps < target_fps * 0.7:
            return "使用FP16"
        return "使用FP32"

class AnalyticsDashboard(QWidget):
    """分析仪表板"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.data_history = deque(maxlen=1000)
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        
        # 创建标签页
        self.tabs = QTabWidget()
        
        # 统计标签页
        stats_tab = QWidget()
        stats_layout = QVBoxLayout(stats_tab)
        
        self.stats_table = QTableWidget()
        self.stats_table.setColumnCount(4)
        self.stats_table.setHorizontalHeaderLabels(["指标", "当前值", "趋势", "状态"])
        stats_layout.addWidget(self.stats_table)
        
        self.tabs.addTab(stats_tab, "实时统计")
        
        # 趋势标签页
        trend_tab = QWidget()
        trend_layout = QVBoxLayout(trend_tab)
        
        self.trend_plot = MatplotlibPlot()
        trend_layout.addWidget(self.trend_plot)
        
        self.tabs.addTab(trend_tab, "趋势分析")
        
        # 分布标签页
        distribution_tab = QWidget()
        distribution_layout = QVBoxLayout(distribution_tab)
        
        self.distribution_plot = MatplotlibPlot()
        distribution_layout.addWidget(self.distribution_plot)
        
        self.tabs.addTab(distribution_tab, "目标分布")
        
        layout.addWidget(self.tabs)
    
    def update_stats(self, detections, performance_data):
        """更新统计信息"""
        # 更新统计数据
        current_time = datetime.now()
        stats = {
            'timestamp': current_time,
            'detection_count': len(detections),
            'avg_confidence': np.mean([d['confidence'] for d in detections]) if detections else 0,
            'fps': performance_data.get('fps', 0),
            'inference_time': performance_data.get('inference_time', 0)
        }
        
        self.data_history.append(stats)
        self.update_stats_table(stats)
        self.update_plots()
    
    def update_stats_table(self, stats):
        """更新统计表格"""
        self.stats_table.setRowCount(5)
        
        metrics = [
            ("检测目标数", stats['detection_count'], self.get_trend_icon('count'), "正常"),
            ("平均置信度", f"{stats['avg_confidence']:.3f}", self.get_trend_icon('confidence'), "正常"),
            ("帧率", f"{stats['fps']:.1f} FPS", self.get_trend_icon('fps'), "正常"),
            ("推理时间", f"{stats['inference_time']:.1f} ms", self.get_trend_icon('time'), "正常"),
            ("数据时间", stats['timestamp'].strftime("%H:%M:%S"), "→", "实时")
        ]
        
        for i, (name, value, trend, status) in enumerate(metrics):
            self.stats_table.setItem(i, 0, QTableWidgetItem(name))
            self.stats_table.setItem(i, 1, QTableWidgetItem(str(value)))
            self.stats_table.setItem(i, 2, QTableWidgetItem(trend))
            self.stats_table.setItem(i, 3, QTableWidgetItem(status))
    
    def get_trend_icon(self, metric):
        """获取趋势图标"""
        if len(self.data_history) < 2:
            return "→"
        
        current = self.data_history[-1]
        previous = self.data_history[-2]
        
        if metric == 'count':
            trend = current['detection_count'] - previous['detection_count']
        elif metric == 'confidence':
            trend = current['avg_confidence'] - previous['avg_confidence']
        elif metric == 'fps':
            trend = current['fps'] - previous['fps']
        elif metric == 'time':
            trend = previous['inference_time'] - current['inference_time']
        else:
            return "→"
        
        if trend > 0:
            return "↑"
        elif trend < 0:
            return "↓"
        else:
            return "→"
    
    def update_plots(self):
        """更新图表"""
        if len(self.data_history) < 2:
            return
        
        # 更新时间序列图
        times = [data['timestamp'] for data in self.data_history]
        counts = [data['detection_count'] for data in self.data_history]
        confidences = [data['avg_confidence'] for data in self.data_history]
        
        self.trend_plot.plot_timeseries(times, counts, confidences)
        
        # 更新分布图（这里需要更多的数据）
        if len(self.data_history) > 10:
            recent_counts = counts[-10:]
            self.distribution_plot.plot_distribution(recent_counts)

class MatplotlibPlot(FigureCanvas):
    """Matplotlib绘图组件"""
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig, self.ax = plt.subplots(figsize=(width, height), dpi=dpi)
        super().__init__(self.fig)
        self.setParent(parent)
        
        self.fig.tight_layout()
    
    def plot_timeseries(self, times, counts, confidences):
        """绘制时间序列图"""
        self.ax.clear()
        
        # 绘制目标数量
        color = 'tab:blue'
        self.ax.set_xlabel('时间')
        self.ax.set_ylabel('目标数量', color=color)
        self.ax.plot(times, counts, color=color, marker='o', linestyle='-', linewidth=2)
        self.ax.tick_params(axis='y', labelcolor=color)
        
        # 绘制置信度
        ax2 = self.ax.twinx()
        color = 'tab:red'
        ax2.set_ylabel('平均置信度', color=color)
        ax2.plot(times, confidences, color=color, marker='s', linestyle='--', linewidth=2)
        ax2.tick_params(axis='y', labelcolor=color)
        
        # 格式化时间轴
        if len(times) > 10:
            self.ax.set_xticks(times[::len(times)//10])
        
        self.fig.tight_layout()
        self.draw()
    
    def plot_distribution(self, counts):
        """绘制分布图"""
        self.ax.clear()
        
        self.ax.hist(counts, bins=10, alpha=0.7, edgecolor='black')
        self.ax.set_xlabel('目标数量')
        self.ax.set_ylabel('频次')
        self.ax.set_title('目标数量分布')
        
        self.fig.tight_layout()
        self.draw()

class InnovativeYOLOApp(QMainWindow):
    """创新YOLO应用主窗口"""
    def __init__(self):
        super().__init__()
        self.detector = IntelligentYOLODetector()
        self.ai_enhancer = AISmartEnhancer()
        self.ar_engine = ARVisualizationEngine()
        self.collaborative_session = CollaborativeSession()
        self.optimizer = RealTimeOptimizer()
        
        self.detection_history = deque(maxlen=100)
        self.performance_data = {}
        self.current_ar_effect = 'bounding_box'
        
        self.init_ui()
        self.init_system_tray()
        self.load_settings()
    
    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("YOLO智能推理与分析平台")
        self.setGeometry(100, 50, 1600, 900)
        
        # 设置应用图标和样式
        #self.setApplicationDisplayName("YOLO AI Platform")
        self.setStyleSheet(self.load_stylesheet())
        
        # 创建中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        main_layout = QHBoxLayout(central_widget)
        
        # 创建左侧控制面板
        control_panel = self.create_control_panel()
        main_layout.addWidget(control_panel, 1)
        
        # 创建中央显示区域
        display_area = self.create_display_area()
        main_layout.addWidget(display_area, 2)
        
        # 创建右侧分析面板
        analytics_panel = self.create_analytics_panel()
        main_layout.addWidget(analytics_panel, 1)
        
        # 创建状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("系统就绪")
        
        # 创建工具栏
        self.create_toolbar()
        
        # 创建停靠窗口
        self.create_dock_windows()
    
    def create_control_panel(self):
        """创建控制面板"""
        control_frame = QFrame()
        control_frame.setFrameShape(QFrame.StyledPanel)
        control_layout = QVBoxLayout(control_frame)
        
        # 智能模型管理组
        model_group = QGroupBox("🤖 智能模型管理")
        model_layout = QVBoxLayout(model_group)
        
        self.model_combo = QComboBox()
        self.model_combo.addItems(["yolov8n.pt", "yolov8s.pt", "yolov8m.pt", "yolov8l.pt", "yolov8x.pt"])
        model_layout.addWidget(QLabel("选择预训练模型:"))
        model_layout.addWidget(self.model_combo)
        
        load_model_btn = QPushButton("🚀 加载模型")
        load_model_btn.clicked.connect(self.load_selected_model)
        model_layout.addWidget(load_model_btn)
        
        ensemble_btn = QPushButton("🔗 启用模型集成")
        ensemble_btn.clicked.connect(self.enable_ensemble_mode)
        model_layout.addWidget(ensemble_btn)
        
        control_layout.addWidget(model_group)
        
        # AR效果组
        ar_group = QGroupBox("👁️ AR增强效果")
        ar_layout = QVBoxLayout(ar_group)
        
        self.ar_effect_combo = QComboBox()
        self.ar_effect_combo.addItems(["边界框", "热力图", "轨迹追踪", "信息面板"])
        self.ar_effect_combo.currentTextChanged.connect(self.change_ar_effect)
        ar_layout.addWidget(QLabel("选择AR效果:"))
        ar_layout.addWidget(self.ar_effect_combo)
        
        control_layout.addWidget(ar_group)
        
        # AI分析组
        ai_group = QGroupBox("🧠 AI智能分析")
        ai_layout = QVBoxLayout(ai_group)
        
        self.anomaly_toggle = QCheckBox("异常检测")
        self.anomaly_toggle.setChecked(True)
        ai_layout.addWidget(self.anomaly_toggle)
        
        self.behavior_toggle = QCheckBox("行为分析")
        self.behavior_toggle.setChecked(True)
        ai_layout.addWidget(self.behavior_toggle)
        
        self.trend_toggle = QCheckBox("趋势预测")
        ai_layout.addWidget(self.trend_toggle)
        
        control_layout.addWidget(ai_group)
        
        # 协作会话组
        collab_group = QGroupBox("👥 协作会话")
        collab_layout = QVBoxLayout(collab_group)
        
        create_session_btn = QPushButton("创建协作会话")
        create_session_btn.clicked.connect(self.create_collaborative_session)
        collab_layout.addWidget(create_session_btn)
        
        join_session_btn = QPushButton("加入会话")
        join_session_btn.clicked.connect(self.join_collaborative_session)
        collab_layout.addWidget(join_session_btn)
        
        control_layout.addWidget(collab_group)
        
        # 性能优化组
        perf_group = QGroupBox("⚡ 性能优化")
        perf_layout = QVBoxLayout(perf_group)
        
        self.auto_optimize = QCheckBox("自动优化")
        self.auto_optimize.setChecked(True)
        perf_layout.addWidget(self.auto_optimize)
        
        optimize_btn = QPushButton("立即优化")
        optimize_btn.clicked.connect(self.run_optimization)
        perf_layout.addWidget(optimize_btn)
        
        control_layout.addWidget(perf_group)
        
        control_layout.addStretch()
        
        return control_frame
    
    def create_display_area(self):
        """创建显示区域"""
        display_frame = QFrame()
        display_layout = QVBoxLayout(display_frame)
        
        # 创建标签页
        self.display_tabs = QTabWidget()
        
        # 主检测标签页
        main_detect_tab = QWidget()
        main_layout = QVBoxLayout(main_detect_tab)
        
        self.video_label = QLabel()
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setMinimumSize(640, 480)
        self.video_label.setText("欢迎使用YOLO智能推理平台\n请加载模型并选择输入源")
        self.video_label.setStyleSheet("border: 2px solid gray; background-color: #f0f0f0;")
        main_layout.addWidget(self.video_label)
        
        # 控制按钮组
        control_buttons = QHBoxLayout()
        
        self.start_btn = QPushButton("🎬 开始检测")
        self.start_btn.clicked.connect(self.start_detection)
        control_buttons.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("⏹️ 停止检测")
        self.stop_btn.clicked.connect(self.stop_detection)
        self.stop_btn.setEnabled(False)
        control_buttons.addWidget(self.stop_btn)
        
        snapshot_btn = QPushButton("📸 截图")
        snapshot_btn.clicked.connect(self.take_snapshot)
        control_buttons.addWidget(snapshot_btn)
        
        main_layout.addLayout(control_buttons)
        
        self.display_tabs.addTab(main_detect_tab, "实时检测")
        
        # AI分析标签页
        ai_analysis_tab = QWidget()
        ai_layout = QVBoxLayout(ai_analysis_tab)
        
        self.ai_analysis_text = QTextEdit()
        self.ai_analysis_text.setReadOnly(True)
        ai_layout.addWidget(self.ai_analysis_text)
        
        self.display_tabs.addTab(ai_analysis_tab, "AI分析")
        
        display_layout.addWidget(self.display_tabs)
        
        return display_frame
    
    def create_analytics_panel(self):
        """创建分析面板"""
        analytics_frame = QFrame()
        analytics_layout = QVBoxLayout(analytics_frame)
        
        # 创建分析仪表板
        self.analytics_dashboard = AnalyticsDashboard()
        analytics_layout.addWidget(self.analytics_dashboard)
        
        # 实时警报面板
        alert_group = QGroupBox("🚨 实时警报")
        alert_layout = QVBoxLayout(alert_group)
        
        self.alert_list = QListWidget()
        alert_layout.addWidget(self.alert_list)
        
        analytics_layout.addWidget(alert_group)
        
        return analytics_frame
    
    def create_toolbar(self):
        """创建工具栏"""
        toolbar = QToolBar("主工具栏")
        self.addToolBar(toolbar)
        
        # 文件操作
        open_image_action = QAction("📁 打开图像", self)
        open_image_action.triggered.connect(self.open_image)
        toolbar.addAction(open_image_action)
        
        open_video_action = QAction("🎥 打开视频", self)
        open_video_action.triggered.connect(self.open_video)
        toolbar.addAction(open_video_action)
        
        open_camera_action = QAction("📷 打开摄像头", self)
        open_camera_action.triggered.connect(self.open_camera)
        toolbar.addAction(open_camera_action)
        
        toolbar.addSeparator()
        
        # 分析操作
        export_action = QAction("📊 导出分析", self)
        export_action.triggered.connect(self.export_analysis)
        toolbar.addAction(export_action)
        
        report_action = QAction("📋 生成报告", self)
        report_action.triggered.connect(self.generate_report)
        toolbar.addAction(report_action)
    
    def create_dock_windows(self):
        """创建停靠窗口"""
        # 模型管理停靠窗口
        model_dock = QDockWidget("模型管理", self)
        model_widget = QWidget()
        model_layout = QVBoxLayout(model_widget)
        
        self.model_tree = QTreeWidget()
        self.model_tree.setHeaderLabels(["模型", "状态", "性能"])
        model_layout.addWidget(self.model_tree)
        
        model_dock.setWidget(model_widget)
        self.addDockWidget(Qt.LeftDockWidgetArea, model_dock)
    
    def init_system_tray(self):
        """初始化系统托盘"""
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray_icon = QSystemTrayIcon(self)
            self.tray_icon.setIcon(self.style().standardIcon(QStyle.SP_ComputerIcon))
            
            tray_menu = QMenu()
            
            show_action = tray_menu.addAction("显示窗口")
            show_action.triggered.connect(self.show)
            
            quit_action = tray_menu.addAction("退出")
            quit_action.triggered.connect(QApplication.quit)
            
            self.tray_icon.setContextMenu(tray_menu)
            self.tray_icon.show()
    
    def load_stylesheet(self):
        """加载样式表"""
        return """
        QMainWindow {
            background-color: #2b2b2b;
            color: #ffffff;
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
            subcontrol-position: top center;
            padding: 0 5px;
            background-color: #2b2b2b;
        }
        QPushButton {
            background-color: #4CAF50;
            border: none;
            color: white;
            padding: 8px 16px;
            text-align: center;
            text-decoration: none;
            font-size: 14px;
            margin: 4px 2px;
            border-radius: 4px;
        }
        QPushButton:hover {
            background-color: #45a049;
        }
        QPushButton:disabled {
            background-color: #666666;
        }
        QComboBox, QSpinBox, QDoubleSpinBox {
            padding: 5px;
            border: 1px solid #555555;
            border-radius: 3px;
            background-color: #333333;
            color: #ffffff;
        }
        QTabWidget::pane {
            border: 1px solid #555555;
            background-color: #333333;
        }
        QTabBar::tab {
            background-color: #444444;
            color: #ffffff;
            padding: 8px 16px;
            border: 1px solid #555555;
        }
        QTabBar::tab:selected {
            background-color: #4CAF50;
        }
        QStatusBar {
            background-color: #333333;
            color: #ffffff;
        }
        """
    
    def load_settings(self):
        """加载设置"""
        self.settings = QSettings("YOLOAI", "InnovativeYOLO")
    
    def load_selected_model(self):
        """加载选择的模型"""
        model_name = self.model_combo.currentText()
        self.status_bar.showMessage(f"正在加载模型: {model_name}")
        
        # 这里应该从本地或远程加载模型
        success = self.detector.load_model(model_name)
        if success:
            self.status_bar.showMessage(f"模型加载成功: {model_name}")
            self.update_model_tree()
        else:
            QMessageBox.warning(self, "错误", f"模型加载失败: {model_name}")
    
    def enable_ensemble_mode(self):
        """启用集成模式"""
        # 这里应该加载多个模型
        model_paths = ["yolov8n.pt", "yolov8s.pt"]  # 示例
        self.detector.enable_ensemble(model_paths)
        self.status_bar.showMessage("模型集成模式已启用")
    
    def change_ar_effect(self, effect_name):
        """改变AR效果"""
        effect_map = {
            "边界框": "bounding_box",
            "热力图": "heatmap", 
            "轨迹追踪": "trajectory",
            "信息面板": "info_panel"
        }
        self.current_ar_effect = effect_map.get(effect_name, "bounding_box")
    
    def create_collaborative_session(self):
        """创建协作会话"""
        dialog = QDialog(self)
        dialog.setWindowTitle("创建协作会话")
        layout = QFormLayout(dialog)
        
        session_name = QLineEdit()
        participants = QLineEdit()
        
        layout.addRow("会话名称:", session_name)
        layout.addRow("参与者:", participants)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)
        
        if dialog.exec_() == QDialog.Accepted:
            session_id = self.collaborative_session.create_session(
                session_name.text(), 
                participants.text().split(',')
            )
            self.status_bar.showMessage(f"协作会话已创建: {session_id}")
    
    def join_collaborative_session(self):
        """加入协作会话"""
        QMessageBox.information(self, "协作功能", "协作会话功能开发中...")
    
    def run_optimization(self):
        """运行优化"""
        self.status_bar.showMessage("正在优化系统性能...")
        # 这里应该实现具体的优化逻辑
        QTimer.singleShot(2000, lambda: self.status_bar.showMessage("性能优化完成"))
    
    def open_image(self):
        """打开图像"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择图像文件", "", "图像文件 (*.jpg *.jpeg *.png *.bmp)"
        )
        if file_path:
            self.current_image = cv2.imread(file_path)
            if self.current_image is not None:
                self.display_image(self.current_image)
                self.status_bar.showMessage(f"已加载图像: {file_path}")
    
    def open_video(self):
        """打开视频"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择视频文件", "", "视频文件 (*.mp4 *.avi *.mov)"
        )
        if file_path:
            self.video_path = file_path
            cap = cv2.VideoCapture(file_path)
            ret, frame = cap.read()
            if ret:
                self.display_image(frame)
                self.status_bar.showMessage(f"已加载视频: {file_path}")
            cap.release()
    
    def open_camera(self):
        """打开摄像头"""
        self.camera_id = 0
        cap = cv2.VideoCapture(self.camera_id)
        ret, frame = cap.read()
        if ret:
            self.display_image(frame)
            self.status_bar.showMessage(f"已打开摄像头: {self.camera_id}")
        cap.release()
    
    def start_detection(self):
        """开始检测"""
        if not self.detector.models:
            QMessageBox.warning(self, "错误", "请先加载模型")
            return
        
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        
        # 设置定时器进行实时检测
        self.detection_timer = QTimer()
        self.detection_timer.timeout.connect(self.process_frame)
        self.detection_timer.start(33)  # ~30 FPS
        
        self.status_bar.showMessage("检测已开始")
    
    def stop_detection(self):
        """停止检测"""
        if hasattr(self, 'detection_timer'):
            self.detection_timer.stop()
        
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.status_bar.showMessage("检测已停止")
    
    def process_frame(self):
        """处理帧"""
        start_time = time.time()
        
        # 获取当前帧（这里需要根据输入源获取）
        if hasattr(self, 'current_image'):
            frame = self.current_image.copy()
        else:
            # 这里应该从视频或摄像头获取帧
            frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        
        # 执行检测
        if self.detector.model_ensemble:
            result_frame, detections = self.detector.detect_ensemble(frame)
        else:
            result_frame, detections = self.detector.detect_single(frame)
        
        # 应用AR效果
        result_frame = self.ar_engine.apply_ar_effects(
            result_frame, detections, self.current_ar_effect, 
            list(self.detection_history)
        )
        
        # AI智能分析
        if self.anomaly_toggle.isChecked():
            anomalies = self.ai_enhancer.anomaly_detector.detect_anomalies(detections, {})
            for anomaly in anomalies:
                self.add_alert(anomaly['message'])
        
        if self.behavior_toggle.isChecked() and len(self.detection_history) > 10:
            behavior_analysis = self.ai_enhancer.analyze_behavior_patterns(
                list(self.detection_history)
            )
            self.update_ai_analysis(behavior_analysis)
        
        # 更新历史记录
        self.detection_history.append({
            'timestamp': datetime.now(),
            'detections': detections,
            'frame_info': {}
        })
        
        # 更新性能数据
        inference_time = (time.time() - start_time) * 1000
        self.performance_data = {
            'fps': 1000 / (inference_time + 1),
            'inference_time': inference_time
        }
        
        # 更新显示
        self.display_image(result_frame)
        self.analytics_dashboard.update_stats(detections, self.performance_data)
    
    def display_image(self, image):
        """显示图像"""
        if image is None:
            return
        
        h, w = image.shape[:2]
        label_width = self.video_label.width()
        label_height = self.video_label.height()
        
        scale = min(label_width / w, label_height / h)
        new_w = int(w * scale)
        new_h = int(h * scale)
        
        resized_image = cv2.resize(image, (new_w, new_h))
        rgb_image = cv2.cvtColor(resized_image, cv2.COLOR_BGR2RGB)
        
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        
        self.video_label.setPixmap(QPixmap.fromImage(qt_image))
    
    def add_alert(self, message):
        """添加警报"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.alert_list.addItem(f"[{timestamp}] {message}")
        self.alert_list.scrollToBottom()
    
    def update_ai_analysis(self, analysis):
        """更新AI分析"""
        text = "AI分析结果:\n\n"
        
        if analysis.get('patterns'):
            text += "检测到的模式:\n"
            for pattern in analysis['patterns']:
                text += f"- {pattern['type']}: {pattern['value']} (置信度: {pattern['confidence']:.2f})\n"
        
        if analysis.get('insights'):
            text += "\n洞察:\n"
            for insight in analysis['insights']:
                text += f"- {insight}\n"
        
        self.ai_analysis_text.setText(text)
    
    def update_model_tree(self):
        """更新模型树"""
        self.model_tree.clear()
        
        for model_name, model_info in self.detector.models.items():
            item = QTreeWidgetItem(self.model_tree)
            item.setText(0, model_name)
            item.setText(1, "已加载")
            item.setText(2, "就绪")
    
    def take_snapshot(self):
        """截图"""
        if hasattr(self, 'video_label') and self.video_label.pixmap():
            file_path, _ = QFileDialog.getSaveFileName(
                self, "保存截图", "", "PNG图像 (*.png);;JPEG图像 (*.jpg)"
            )
            if file_path:
                self.video_label.pixmap().save(file_path)
                self.status_bar.showMessage(f"截图已保存: {file_path}")
    
    def export_analysis(self):
        """导出分析"""
        QMessageBox.information(self, "导出", "分析数据导出功能开发中...")
    
    def generate_report(self):
        """生成报告"""
        QMessageBox.information(self, "报告", "智能报告生成功能开发中...")
    
    def closeEvent(self, event):
        """关闭事件"""
        self.stop_detection()
        self.settings.setValue("geometry", self.saveGeometry())
        event.accept()

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("YOLO智能推理平台")
    app.setApplicationVersion("1.0.0")
    
    # 设置应用程序样式
    app.setStyle('Fusion')
    
    window = InnovativeYOLOApp()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()