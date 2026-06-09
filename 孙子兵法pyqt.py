import sys
import cv2
import numpy as np
import time
from collections import deque, defaultdict
import math
from scipy.spatial import distance
from scipy.optimize import linear_sum_assignment
import warnings
from ultralytics import YOLO
import torch
import pandas as pd
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler
import json
import logging
from datetime import datetime
import os
from sunzibingfa import *
# PyQt界面
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                             QWidget, QLabel, QPushButton, QComboBox, QSlider, 
                             QGroupBox, QTextEdit, QTabWidget, QTableWidget, 
                             QTableWidgetItem, QProgressBar, QSplitter, QFrame,
                             QMessageBox, QFileDialog, QCheckBox, QSpinBox,
                             QDoubleSpinBox, QFormLayout, QGridLayout)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt5.QtGui import QImage, QPixmap, QFont, QPalette, QColor

warnings.filterwarnings('ignore')

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('TacticalVision')

class VideoThread(QThread):
    """视频处理线程"""
    change_pixmap_signal = pyqtSignal(np.ndarray)
    update_stats_signal = pyqtSignal(dict)
    update_tactical_signal = pyqtSignal(dict)
    
    def __init__(self, tactical_system, source=0):
        super().__init__()
        self.tactical_system = tactical_system
        self.source = source
        self._run_flag = True
        self.cap = None
        
    def run(self):
        """运行视频处理线程"""
        try:
            self.cap = cv2.VideoCapture(self.source)
            if not self.cap.isOpened():
                logger.error(f"无法打开视频源: {self.source}")
                return
                
            while self._run_flag:
                ret, frame = self.cap.read()
                if ret:
                    # 处理帧
                    processed_frame = self.tactical_system.process_frame(frame)
                    
                    # 发射信号
                    self.change_pixmap_signal.emit(processed_frame)
                    
                    # 更新统计信息
                    stats = {
                        'fps': 1.0 / self.tactical_system.performance_stats['avg_processing_time'] 
                        if self.tactical_system.performance_stats['avg_processing_time'] > 0 else 0,
                        'targets': self.tactical_system.performance_stats.get('current_targets', 0),
                        'total_frames': self.tactical_system.performance_stats['frames_processed'],
                        'max_targets': self.tactical_system.performance_stats['max_targets_tracked']
                    }
                    self.update_stats_signal.emit(stats)
                    
                    # 更新战术信息
                    tactical_info = {
                        'strategy': self.tactical_system.last_decisions.get('primary_strategy', 'Unknown'),
                        'risk': self.tactical_system.last_decisions.get('risk_level', 'medium'),
                        'threat_level': self.tactical_system.last_threats.get('overall_threat_level', 0)
                    }
                    self.update_tactical_signal.emit(tactical_info)
                    
                else:
                    break
                    
        except Exception as e:
            logger.error(f"视频处理错误: {e}")
            
    def stop(self):
        """停止线程"""
        self._run_flag = False
        if self.cap:
            self.cap.release()
        self.wait()

class EnhancedTacticalVision:
    """
    增强版智能战术视觉系统
    集成YOLO目标检测与深度战术分析
    """
    
    def __init__(self, yolo_model='yolov8n.pt'):
        # 初始化YOLO模型
        print("正在加载YOLO模型...")
        try:
            self.yolo_model = YOLO(yolo_model)
            self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
            print(f"使用设备: {self.device}")
        except Exception as e:
            print(f"模型加载失败: {e}")
            raise
        
        # 多目标跟踪系统
        self.tracker = AdvancedObjectTracker()
        self.track_history = defaultdict(lambda: deque(maxlen=50))
        
        # 战术决策系统
        self.tactical_engine = AdvancedTacticalEngine()
        self.strategy_log = deque(maxlen=200)
        
        # 环境感知系统
        self.environment_analyzer = AdvancedEnvironmentAnalyzer()
        
        # 威胁评估系统
        self.threat_assessor = ThreatAssessmentSystem()
        
        # 性能监控
        self.performance_stats = {
            'frames_processed': 0,
            'avg_processing_time': 0,
            'max_targets_tracked': 0,
            'current_targets': 0
        }
        
        # 数据记录
        self.analysis_data = []
        
        # 缓存最近的分析结果
        self.last_decisions = {}
        self.last_threats = {}
        self.last_environment = {}
        
        # 系统配置
        self.config = {
            'detection_confidence': 0.5,
            'tracking_enabled': True,
            'tactical_analysis_enabled': True,
            'threat_assessment_enabled': True,
            'environment_analysis_enabled': True
        }
        
        # 保存路径
        self.save_path = "tactical_data"
        os.makedirs(self.save_path, exist_ok=True)
        
    def process_frame(self, frame):
        """
        处理视频帧并进行深度战术分析
        """
        start_time = time.time()
        self.performance_stats['frames_processed'] += 1
        
        # 步骤1: YOLO目标检测
        yolo_results = self.yolo_model(frame, verbose=False, conf=self.config['detection_confidence'])
        detections = self._parse_yolo_detections(yolo_results, frame.shape)
        
        # 步骤2: 高级目标跟踪
        tracks = {}
        if self.config['tracking_enabled']:
            tracks = self.tracker.update(detections, frame)
            self.performance_stats['current_targets'] = len(tracks)
        
        # 步骤3: 环境与地形分析
        environment_data = {}
        if self.config['environment_analysis_enabled']:
            environment_data = self.environment_analyzer.comprehensive_analysis(frame)
            self.last_environment = environment_data
        
        # 步骤4: 威胁评估
        threat_assessment = {}
        if self.config['threat_assessment_enabled']:
            threat_assessment = self.threat_assessor.assess_threats(tracks, environment_data)
            self.last_threats = threat_assessment
        
        # 步骤5: 战术决策
        tactical_decisions = {}
        if self.config['tactical_analysis_enabled']:
            tactical_decisions = self.tactical_engine.generate_strategy(
                tracks, threat_assessment, environment_data
            )
            self.last_decisions = tactical_decisions
        
        # 步骤6: 可视化与数据记录
        result_frame = self._comprehensive_visualization(
            frame, tracks, environment_data, threat_assessment, tactical_decisions
        )
        
        # 性能统计
        processing_time = time.time() - start_time
        self._update_performance_stats(len(tracks), processing_time)
        
        # 数据记录
        self._record_analysis_data(tracks, threat_assessment, tactical_decisions)
        
        return result_frame
    
    def _parse_yolo_detections(self, yolo_results, frame_shape):
        """
        解析YOLO检测结果
        """
        detections = []
        
        for result in yolo_results:
            if result.boxes is not None:
                boxes = result.boxes.xyxy.cpu().numpy()
                confidences = result.boxes.conf.cpu().numpy()
                class_ids = result.boxes.cls.cpu().numpy()
                
                for i, (box, confidence, class_id) in enumerate(zip(boxes, confidences, class_ids)):
                    x1, y1, x2, y2 = box
                    width = x2 - x1
                    height = y2 - y1
                    
                    class_name = self.yolo_model.names[int(class_id)]
                    
                    # 计算目标中心点
                    centroid = (int((x1 + x2) / 2), int((y1 + y2) / 2))
                    
                    # 根据目标类型分配战术权重
                    tactical_weight = self._get_tactical_weight(class_name, confidence)
                    
                    detections.append({
                        'bbox': (int(x1), int(y1), int(width), int(height)),
                        'confidence': float(confidence),
                        'class_id': int(class_id),
                        'class_name': class_name,
                        'centroid': centroid,
                        'tactical_weight': tactical_weight,
                        'type': 'yolo'
                    })
        
        return detections
    
    def _get_tactical_weight(self, class_name, confidence):
        """
        根据目标类型分配战术权重
        """
        tactical_weights = {
            'person': 0.8,      # 人员 - 高威胁
            'car': 0.7,         # 车辆 - 高威胁  
            'truck': 0.75,      # 卡车 - 高威胁
            'bus': 0.7,         # 巴士 - 中高威胁
            'motorcycle': 0.6,  # 摩托车 - 中威胁
            'bicycle': 0.4,     # 自行车 - 低威胁
            'cat': 0.1,         # 动物 - 忽略
            'dog': 0.1,
            'bird': 0.05
        }
        
        base_weight = tactical_weights.get(class_name, 0.3)
        return base_weight * confidence
    
    def _comprehensive_visualization(self, frame, tracks, environment, threats, decisions):
        """
        综合可视化显示
        """
        result = frame.copy()
        height, width = frame.shape[:2]
        
        # 绘制环境分析
        result = self._draw_environment_analysis(result, environment)
        
        # 绘制目标跟踪
        result = self._draw_advanced_tracking(result, tracks)
        
        # 绘制威胁评估
        result = self._draw_threat_assessment(result, threats)
        
        # 绘制战术决策
        result = self._draw_tactical_decisions(result, decisions, width, height)
        
        # 绘制性能统计
        result = self._draw_performance_stats(result, width, height)
        
        # 绘制系统状态
        result = self._draw_system_status(result, width, height)
        
        return result
    
    def _draw_environment_analysis(self, frame, environment):
        """绘制环境分析结果"""
        # 绘制安全区域
        if 'safe_zones' in environment:
            for zone in environment['safe_zones']:
                points = np.array(zone['contour'], dtype=np.int32)
                cv2.fillPoly(frame, [points], (0, 255, 0, 50))
                cv2.putText(frame, f"Safe: {zone['safety_score']:.2f}", 
                           tuple(zone['center']), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
        
        # 绘制危险区域
        if 'danger_zones' in environment:
            for zone in environment['danger_zones']:
                points = np.array(zone['contour'], dtype=np.int32)
                cv2.fillPoly(frame, [points], (0, 0, 255, 50))
                cv2.putText(frame, f"Danger: {zone['risk_score']:.2f}", 
                           tuple(zone['center']), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)
        
        # 绘制战术要点
        if 'tactical_points' in environment:
            for point in environment['tactical_points']:
                pos = point['position']
                cv2.circle(frame, pos, 8, (255, 255, 0), -1)
                cv2.putText(frame, point['type'], (pos[0] + 10, pos[1]), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 0), 1)
        
        return frame
    
    def _draw_advanced_tracking(self, frame, tracks):
        """绘制高级跟踪信息"""
        for track_id, track in tracks.items():
            if len(track['positions']) > 1:
                # 绘制轨迹线
                points = np.array(track['positions'], dtype=np.int32)
                cv2.polylines(frame, [points], False, track['color'], 2)
                
                # 绘制速度向量
                if len(track['positions']) >= 2:
                    current_pos = track['positions'][-1]
                    prev_pos = track['positions'][-2]
                    cv2.arrowedLine(frame, prev_pos, current_pos, track['color'], 2, tipLength=0.3)
            
            # 绘制边界框和信息
            x, y, w, h = track['bbox']
            cv2.rectangle(frame, (x, y), (x + w, y + h), track['color'], 2)
            
            # 信息显示
            info_text = f"ID:{track_id} {track['class_name']} V:{track['velocity']:.1f}"
            cv2.putText(frame, info_text, (x, y-10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, track['color'], 1)
            
            # 显示置信度
            conf_text = f"Conf:{track['confidence']:.2f}"
            cv2.putText(frame, conf_text, (x, y+h+15), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, track['color'], 1)
            
            # 显示威胁等级
            if 'threat_level' in track:
                threat_text = f"Threat:{track['threat_level']:.2f}"
                cv2.putText(frame, threat_text, (x, y+h+30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, track['color'], 1)
        
        return frame
    
    def _draw_threat_assessment(self, frame, threats):
        """绘制威胁评估"""
        for threat in threats.get('individual_threats', []):
            pos = threat['position']
            threat_level = threat['threat_level']
            
            # 绘制威胁等级圆圈
            radius = int(15 + threat_level * 25)
            color = self._get_threat_color(threat_level)
            cv2.circle(frame, pos, radius, color, 2)
            
            # 绘制威胁等级
            cv2.putText(frame, f"Threat: {threat_level:.2f}", 
                       (pos[0] - 30, pos[1] - radius - 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
        
        return frame
    
    def _draw_tactical_decisions(self, frame, decisions, width, height):
        """绘制战术决策"""
        # 主策略显示
        strategy_text = f"STRATEGY: {decisions.get('primary_strategy', 'Unknown')}"
        cv2.putText(frame, strategy_text, (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # 风险等级
        risk_level = decisions.get('risk_level', 'medium')
        risk_color = self._get_risk_color(risk_level)
        cv2.putText(frame, f"RISK: {risk_level.upper()}", (width - 150, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, risk_color, 2)
        
        # 推荐行动
        actions = decisions.get('recommended_actions', [])
        for i, action in enumerate(actions[:4]):  # 显示前4个行动
            cv2.putText(frame, f"{i+1}. {action}", (10, 60 + i*25),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # 态势摘要
        summary = decisions.get('situation_summary', {})
        enemy_count = summary.get('enemy_count', 0)
        cv2.putText(frame, f"Enemies: {enemy_count}", (width - 150, 60),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
        
        return frame
    
    def _draw_performance_stats(self, frame, width, height):
        """绘制性能统计"""
        fps = 1.0 / self.performance_stats['avg_processing_time'] if self.performance_stats['avg_processing_time'] > 0 else 0
        
        stats_text = f"FPS: {fps:.1f} | Targets: {self.performance_stats.get('current_targets', 0)}"
        cv2.putText(frame, stats_text, (10, height - 10),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        return frame
    
    def _draw_system_status(self, frame, width, height):
        """绘制系统状态"""
        status_text = f"Detection: {'ON' if self.config['detection_confidence'] > 0 else 'OFF'} | "
        status_text += f"Tracking: {'ON' if self.config['tracking_enabled'] else 'OFF'} | "
        status_text += f"Tactical: {'ON' if self.config['tactical_analysis_enabled'] else 'OFF'}"
        
        cv2.putText(frame, status_text, (width - 400, height - 10),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
        
        return frame
    
    def _get_threat_color(self, threat_level):
        """根据威胁等级获取颜色"""
        if threat_level > 0.7:
            return (0, 0, 255)  # 红色 - 高威胁
        elif threat_level > 0.4:
            return (0, 165, 255)  # 橙色 - 中威胁
        else:
            return (0, 255, 0)  # 绿色 - 低威胁
    
    def _get_risk_color(self, risk_level):
        """根据风险等级获取颜色"""
        risk_colors = {
            'low': (0, 255, 0),      # 绿色
            'medium': (0, 255, 255),  # 黄色
            'high': (0, 0, 255)       # 红色
        }
        return risk_colors.get(risk_level, (255, 255, 255))
    
    def _update_performance_stats(self, num_targets, processing_time):
        """更新性能统计"""
        self.performance_stats['current_targets'] = num_targets
        self.performance_stats['max_targets_tracked'] = max(
            self.performance_stats['max_targets_tracked'], num_targets
        )
        
        # 更新平均处理时间（指数移动平均）
        alpha = 0.1
        if self.performance_stats['avg_processing_time'] == 0:
            self.performance_stats['avg_processing_time'] = processing_time
        else:
            self.performance_stats['avg_processing_time'] = (
                alpha * processing_time + 
                (1 - alpha) * self.performance_stats['avg_processing_time']
            )
    
    def _record_analysis_data(self, tracks, threats, decisions):
        """记录分析数据"""
        timestamp = time.time()
        
        frame_data = {
            'timestamp': timestamp,
            'target_count': len(tracks),
            'total_threat': threats.get('overall_threat_level', 0),
            'strategy': decisions.get('primary_strategy', 'Unknown'),
            'risk_level': decisions.get('risk_level', 'medium'),
            'tracks': {track_id: {
                'class_name': track['class_name'],
                'position': track['centroid'],
                'velocity': track['velocity'],
                'confidence': track['confidence']
            } for track_id, track in tracks.items()}
        }
        
        self.analysis_data.append(frame_data)
        
        # 保持数据量可控
        if len(self.analysis_data) > 1000:
            self.analysis_data = self.analysis_data[-1000:]
    
    def generate_report(self):
        """生成分析报告"""
        if not self.analysis_data:
            return "无分析数据"
        
        df = pd.DataFrame(self.analysis_data)
        
        report = {
            'total_frames_processed': self.performance_stats['frames_processed'],
            'average_targets_per_frame': df['target_count'].mean(),
            'most_common_strategy': df['strategy'].mode()[0] if not df['strategy'].mode().empty else 'Unknown',
            'average_threat_level': df['total_threat'].mean(),
            'max_targets_tracked': self.performance_stats['max_targets_tracked'],
            'average_processing_time': self.performance_stats['avg_processing_time'],
            'generation_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        return report
    
    def save_data(self, filename=None):
        """保存分析数据"""
        if filename is None:
            filename = f"tactical_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        filepath = os.path.join(self.save_path, filename)
        
        data_to_save = {
            'system_info': {
                'version': '2.0',
                'export_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'frames_processed': self.performance_stats['frames_processed']
            },
            'analysis_data': self.analysis_data,
            'performance_stats': self.performance_stats,
            'config': self.config
        }
        
        try:
            with open(filepath, 'w') as f:
                json.dump(data_to_save, f, indent=2)
            return True, f"数据已保存到: {filepath}"
        except Exception as e:
            return False, f"保存失败: {e}"
    
    def load_data(self, filepath):
        """加载分析数据"""
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            self.analysis_data = data.get('analysis_data', [])
            self.performance_stats.update(data.get('performance_stats', {}))
            self.config.update(data.get('config', {}))
            
            return True, f"数据已从 {filepath} 加载"
        except Exception as e:
            return False, f"加载失败: {e}"

# 其他类保持不变 (AdvancedObjectTracker, AdvancedTacticalEngine, 
# AdvancedEnvironmentAnalyzer, ThreatAssessmentSystem)
# 这里为了节省空间，省略了这些类的重复代码，它们与原始代码相同

class TacticalVisionGUI(QMainWindow):
    """战术视觉系统GUI"""
    
    def __init__(self):
        super().__init__()
        self.tactical_system = EnhancedTacticalVision()
        self.video_thread = None
        
        self.init_ui()
        self.init_connections()
        
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("增强版智能战术视觉系统 v2.0")
        self.setGeometry(100, 100, 1400, 900)
        
        # 设置深色主题
        self.set_dark_theme()
        
        # 创建中央窗口
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QHBoxLayout(central_widget)
        
        # 左侧视频面板
        left_panel = QVBoxLayout()
        
        # 视频显示
        self.video_label = QLabel()
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setMinimumSize(800, 600)
        self.video_label.setStyleSheet("background-color: black; border: 1px solid #555;")
        left_panel.addWidget(self.video_label)
        
        # 视频控制
        control_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("开始")
        self.start_btn.setStyleSheet("QPushButton { background-color: #2d5c2d; color: white; }")
        self.stop_btn = QPushButton("停止")
        self.stop_btn.setStyleSheet("QPushButton { background-color: #5c2d2d; color: white; }")
        self.stop_btn.setEnabled(False)
        
        self.source_combo = QComboBox()
        self.source_combo.addItems(["摄像头 0", "摄像头 1", "摄像头 2", "视频文件"])
        
        control_layout.addWidget(QLabel("视频源:"))
        control_layout.addWidget(self.source_combo)
        control_layout.addWidget(self.start_btn)
        control_layout.addWidget(self.stop_btn)
        control_layout.addStretch()
        
        left_panel.addLayout(control_layout)
        
        # 右侧信息面板
        right_panel = QVBoxLayout()
        
        # 创建标签页
        self.tab_widget = QTabWidget()
        
        # 状态标签页
        self.status_tab = self.create_status_tab()
        self.tab_widget.addTab(self.status_tab, "系统状态")
        
        # 战术标签页
        self.tactical_tab = self.create_tactical_tab()
        self.tab_widget.addTab(self.tactical_tab, "战术分析")
        
        # 目标标签页
        self.targets_tab = self.create_targets_tab()
        self.tab_widget.addTab(self.targets_tab, "目标跟踪")
        
        # 配置标签页
        self.config_tab = self.create_config_tab()
        self.tab_widget.addTab(self.config_tab, "系统配置")
        
        right_panel.addWidget(self.tab_widget)
        
        # 添加到主布局
        main_layout.addLayout(left_panel, 70)
        main_layout.addLayout(right_panel, 30)
        
    def create_status_tab(self):
        """创建状态标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 系统状态组
        status_group = QGroupBox("系统状态")
        status_layout = QFormLayout(status_group)
        
        self.fps_label = QLabel("0.0")
        self.targets_label = QLabel("0")
        self.frames_label = QLabel("0")
        self.max_targets_label = QLabel("0")
        
        status_layout.addRow("处理速度 (FPS):", self.fps_label)
        status_layout.addRow("当前目标:", self.targets_label)
        status_layout.addRow("处理帧数:", self.frames_label)
        status_layout.addRow("最大目标数:", self.max_targets_label)
        
        layout.addWidget(status_group)
        
        # 性能监控组
        perf_group = QGroupBox("性能监控")
        perf_layout = QVBoxLayout(perf_group)
        
        self.cpu_progress = QProgressBar()
        self.cpu_progress.setMaximum(100)
        self.memory_progress = QProgressBar()
        self.memory_progress.setMaximum(100)
        
        perf_layout.addWidget(QLabel("CPU使用率:"))
        perf_layout.addWidget(self.cpu_progress)
        perf_layout.addWidget(QLabel("内存使用率:"))
        perf_layout.addWidget(self.memory_progress)
        
        layout.addWidget(perf_group)
        
        # 系统控制组
        control_group = QGroupBox("系统控制")
        control_layout = QVBoxLayout(control_group)
        
        self.report_btn = QPushButton("生成报告")
        self.save_btn = QPushButton("保存数据")
        self.load_btn = QPushButton("加载数据")
        
        control_layout.addWidget(self.report_btn)
        control_layout.addWidget(self.save_btn)
        control_layout.addWidget(self.load_btn)
        
        layout.addWidget(control_group)
        layout.addStretch()
        
        return widget
    
    def create_tactical_tab(self):
        """创建战术分析标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 当前策略组
        strategy_group = QGroupBox("当前战术策略")
        strategy_layout = QVBoxLayout(strategy_group)
        
        self.strategy_label = QLabel("等待分析...")
        self.strategy_label.setStyleSheet("font-size: 16pt; font-weight: bold; color: #4CAF50;")
        self.strategy_label.setAlignment(Qt.AlignCenter)
        strategy_layout.addWidget(self.strategy_label)
        
        layout.addWidget(strategy_group)
        
        # 风险等级组
        risk_group = QGroupBox("风险等级")
        risk_layout = QVBoxLayout(risk_group)
        
        self.risk_label = QLabel("中等")
        self.risk_label.setStyleSheet("font-size: 14pt; font-weight: bold; color: #FF9800;")
        self.risk_label.setAlignment(Qt.AlignCenter)
        risk_layout.addWidget(self.risk_label)
        
        layout.addWidget(risk_group)
        
        # 威胁评估组
        threat_group = QGroupBox("威胁评估")
        threat_layout = QVBoxLayout(threat_group)
        
        self.threat_label = QLabel("0.0")
        self.threat_label.setStyleSheet("font-size: 14pt; font-weight: bold;")
        self.threat_label.setAlignment(Qt.AlignCenter)
        threat_layout.addWidget(self.threat_label)
        
        self.threat_progress = QProgressBar()
        self.threat_progress.setMaximum(100)
        threat_layout.addWidget(self.threat_progress)
        
        layout.addWidget(threat_group)
        
        # 推荐行动组
        actions_group = QGroupBox("推荐行动")
        actions_layout = QVBoxLayout(actions_group)
        
        self.actions_text = QTextEdit()
        self.actions_text.setReadOnly(True)
        self.actions_text.setMaximumHeight(150)
        actions_layout.addWidget(self.actions_text)
        
        layout.addWidget(actions_group)
        
        # 态势摘要组
        summary_group = QGroupBox("态势摘要")
        summary_layout = QVBoxLayout(summary_group)
        
        self.summary_text = QTextEdit()
        self.summary_text.setReadOnly(True)
        self.summary_text.setMaximumHeight(100)
        summary_layout.addWidget(self.summary_text)
        
        layout.addWidget(summary_group)
        
        layout.addStretch()
        
        return widget
    
    def create_targets_tab(self):
        """创建目标跟踪标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 目标表格
        self.targets_table = QTableWidget()
        self.targets_table.setColumnCount(6)
        self.targets_table.setHorizontalHeaderLabels(["ID", "类型", "位置", "速度", "置信度", "威胁等级"])
        layout.addWidget(self.targets_table)
        
        return widget
    
    def create_config_tab(self):
        """创建系统配置标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 检测配置组
        detect_group = QGroupBox("目标检测配置")
        detect_layout = QFormLayout(detect_group)
        
        self.confidence_slider = QSlider(Qt.Horizontal)
        self.confidence_slider.setRange(0, 100)
        self.confidence_slider.setValue(50)
        self.confidence_label = QLabel("0.5")
        
        detect_layout.addRow("检测置信度:", self.confidence_slider)
        detect_layout.addRow("", self.confidence_label)
        
        layout.addWidget(detect_group)
        
        # 功能开关组
        function_group = QGroupBox("功能开关")
        function_layout = QVBoxLayout(function_group)
        
        self.tracking_check = QCheckBox("启用目标跟踪")
        self.tracking_check.setChecked(True)
        self.tactical_check = QCheckBox("启用战术分析")
        self.tactical_check.setChecked(True)
        self.threat_check = QCheckBox("启用威胁评估")
        self.threat_check.setChecked(True)
        self.environment_check = QCheckBox("启用环境分析")
        self.environment_check.setChecked(True)
        
        function_layout.addWidget(self.tracking_check)
        function_layout.addWidget(self.tactical_check)
        function_layout.addWidget(self.threat_check)
        function_layout.addWidget(self.environment_check)
        
        layout.addWidget(function_group)
        
        # 高级配置组
        advanced_group = QGroupBox("高级配置")
        advanced_layout = QFormLayout(advanced_group)
        
        self.max_targets_spin = QSpinBox()
        self.max_targets_spin.setRange(1, 100)
        self.max_targets_spin.setValue(20)
        
        self.track_age_spin = QSpinBox()
        self.track_age_spin.setRange(1, 100)
        self.track_age_spin.setValue(30)
        
        self.cluster_eps_spin = QDoubleSpinBox()
        self.cluster_eps_spin.setRange(10, 500)
        self.cluster_eps_spin.setValue(100)
        self.cluster_eps_spin.setSingleStep(10)
        
        advanced_layout.addRow("最大目标数:", self.max_targets_spin)
        advanced_layout.addRow("轨迹保留帧数:", self.track_age_spin)
        advanced_layout.addRow("聚类距离阈值:", self.cluster_eps_spin)
        
        layout.addWidget(advanced_group)
        
        layout.addStretch()
        
        return widget
    
    def init_connections(self):
        """初始化信号连接"""
        self.start_btn.clicked.connect(self.start_video)
        self.stop_btn.clicked.connect(self.stop_video)
        self.report_btn.clicked.connect(self.generate_report)
        self.save_btn.clicked.connect(self.save_data)
        self.load_btn.clicked.connect(self.load_data)
        
        # 配置连接
        self.confidence_slider.valueChanged.connect(self.update_confidence)
        self.tracking_check.stateChanged.connect(self.update_tracking)
        self.tactical_check.stateChanged.connect(self.update_tactical)
        self.threat_check.stateChanged.connect(self.update_threat)
        self.environment_check.stateChanged.connect(self.update_environment)
        
        # 性能监控定时器
        self.perf_timer = QTimer()
        self.perf_timer.timeout.connect(self.update_performance)
        self.perf_timer.start(1000)  # 每秒更新一次
        
    def set_dark_theme(self):
        """设置深色主题"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QTabWidget::pane {
                border: 1px solid #555;
                background-color: #3c3c3c;
            }
            QTabBar::tab {
                background-color: #3c3c3c;
                color: #ffffff;
                padding: 8px 16px;
                border: 1px solid #555;
            }
            QTabBar::tab:selected {
                background-color: #505050;
            }
            QGroupBox {
                color: #ffffff;
                border: 1px solid #555;
                margin-top: 1ex;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QPushButton {
                background-color: #505050;
                color: #ffffff;
                border: 1px solid #555;
                padding: 5px 15px;
            }
            QPushButton:hover {
                background-color: #606060;
            }
            QLabel {
                color: #ffffff;
            }
            QProgressBar {
                border: 1px solid #555;
                background-color: #3c3c3c;
                text-align: center;
                color: white;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
            }
            QTextEdit, QTableWidget {
                background-color: #3c3c3c;
                color: #ffffff;
                border: 1px solid #555;
            }
            QComboBox {
                background-color: #3c3c3c;
                color: #ffffff;
                border: 1px solid #555;
                padding: 5px;
            }
            QSlider::groove:horizontal {
                border: 1px solid #555;
                height: 8px;
                background: #3c3c3c;
            }
            QSlider::handle:horizontal {
                background: #ffffff;
                border: 1px solid #555;
                width: 18px;
                margin: -5px 0;
                border-radius: 3px;
            }
            QCheckBox {
                color: #ffffff;
            }
            QCheckBox::indicator {
                width: 13px;
                height: 13px;
            }
            QCheckBox::indicator:unchecked {
                background-color: #3c3c3c;
                border: 1px solid #555;
            }
            QCheckBox::indicator:checked {
                background-color: #4CAF50;
                border: 1px solid #555;
            }
            QSpinBox, QDoubleSpinBox {
                background-color: #3c3c3c;
                color: #ffffff;
                border: 1px solid #555;
                padding: 5px;
            }
        """)
    
    def start_video(self):
        """开始视频处理"""
        source_index = self.source_combo.currentIndex()
        
        if source_index == 3:  # 视频文件
            file_path, _ = QFileDialog.getOpenFileName(
                self, "选择视频文件", "", "视频文件 (*.mp4 *.avi *.mov *.mkv)"
            )
            if not file_path:
                return
            source = file_path
        else:
            source = source_index
        
        self.video_thread = VideoThread(self.tactical_system, source)
        self.video_thread.change_pixmap_signal.connect(self.update_image)
        self.video_thread.update_stats_signal.connect(self.update_stats)
        self.video_thread.update_tactical_signal.connect(self.update_tactical_info)
        
        self.video_thread.start()
        
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
    
    def stop_video(self):
        """停止视频处理"""
        if self.video_thread:
            self.video_thread.stop()
            self.video_thread = None
        
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        
        # 清空视频显示
        self.video_label.clear()
        self.video_label.setText("视频已停止")
    
    def update_image(self, cv_img):
        """更新视频显示"""
        qt_img = self.convert_cv_qt(cv_img)
        self.video_label.setPixmap(qt_img)
    
    def convert_cv_qt(self, cv_img):
        """将OpenCV图像转换为Qt图像"""
        rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        convert_to_Qt_format = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        p = convert_to_Qt_format.scaled(self.video_label.width(), self.video_label.height(), Qt.KeepAspectRatio)
        return QPixmap.fromImage(p)
    
    def update_stats(self, stats):
        """更新统计信息"""
        self.fps_label.setText(f"{stats['fps']:.1f}")
        self.targets_label.setText(str(stats['targets']))
        self.frames_label.setText(str(stats['total_frames']))
        self.max_targets_label.setText(str(stats['max_targets']))
    
    def update_tactical_info(self, tactical_info):
        """更新战术信息"""
        self.strategy_label.setText(tactical_info['strategy'])
        
        # 更新风险等级
        risk_level = tactical_info['risk']
        self.risk_label.setText(risk_level.upper())
        if risk_level == 'low':
            self.risk_label.setStyleSheet("font-size: 14pt; font-weight: bold; color: #4CAF50;")
        elif risk_level == 'medium':
            self.risk_label.setStyleSheet("font-size: 14pt; font-weight: bold; color: #FF9800;")
        else:
            self.risk_label.setStyleSheet("font-size: 14pt; font-weight: bold; color: #F44336;")
        
        # 更新威胁等级
        threat_level = tactical_info['threat_level']
        self.threat_label.setText(f"{threat_level:.2f}")
        self.threat_progress.setValue(int(threat_level * 100))
        
        if threat_level > 0.7:
            self.threat_progress.setStyleSheet("QProgressBar::chunk { background-color: #F44336; }")
        elif threat_level > 0.4:
            self.threat_progress.setStyleSheet("QProgressBar::chunk { background-color: #FF9800; }")
        else:
            self.threat_progress.setStyleSheet("QProgressBar::chunk { background-color: #4CAF50; }")
        
        # 更新推荐行动
        if hasattr(self.tactical_system, 'last_decisions'):
            actions = self.tactical_system.last_decisions.get('recommended_actions', [])
            self.actions_text.clear()
            for i, action in enumerate(actions):
                self.actions_text.append(f"{i+1}. {action}")
        
        # 更新态势摘要
        if hasattr(self.tactical_system, 'last_decisions'):
            summary = self.tactical_system.last_decisions.get('situation_summary', {})
            self.summary_text.clear()
            self.summary_text.append(f"敌方数量: {summary.get('enemy_count', 0)}")
            self.summary_text.append(f"集群数量: {summary.get('cluster_count', 0)}")
            self.summary_text.append(f"地形优势: {summary.get('terrain_advantage', 0):.2f}")
        
        # 更新目标表格
        self.update_targets_table()
    
    def update_targets_table(self):
        """更新目标表格"""
        if hasattr(self.tactical_system, 'tracker'):
            tracks = self.tactical_system.tracker.tracks
            
            self.targets_table.setRowCount(len(tracks))
            
            for i, (track_id, track) in enumerate(tracks.items()):
                self.targets_table.setItem(i, 0, QTableWidgetItem(str(track_id)))
                self.targets_table.setItem(i, 1, QTableWidgetItem(track['class_name']))
                self.targets_table.setItem(i, 2, QTableWidgetItem(f"({track['centroid'][0]}, {track['centroid'][1]})"))
                self.targets_table.setItem(i, 3, QTableWidgetItem(f"{track['velocity']:.1f}"))
                self.targets_table.setItem(i, 4, QTableWidgetItem(f"{track['confidence']:.2f}"))
                
                threat_item = QTableWidgetItem(f"{track.get('threat_level', 0):.2f}")
                threat_level = track.get('threat_level', 0)
                if threat_level > 0.7:
                    threat_item.setBackground(QColor(244, 67, 54))  # 红色
                elif threat_level > 0.4:
                    threat_item.setBackground(QColor(255, 152, 0))  # 橙色
                else:
                    threat_item.setBackground(QColor(76, 175, 80))  # 绿色
                
                self.targets_table.setItem(i, 5, threat_item)
    
    def update_performance(self):
        """更新性能监控"""
        # 模拟CPU和内存使用率
        import psutil
        cpu_percent = psutil.cpu_percent()
        memory_percent = psutil.virtual_memory().percent
        
        self.cpu_progress.setValue(int(cpu_percent))
        self.memory_progress.setValue(int(memory_percent))
    
    def update_confidence(self, value):
        """更新检测置信度"""
        confidence = value / 100.0
        self.tactical_system.config['detection_confidence'] = confidence
        self.confidence_label.setText(f"{confidence:.2f}")
    
    def update_tracking(self, state):
        """更新跟踪设置"""
        self.tactical_system.config['tracking_enabled'] = (state == Qt.Checked)
    
    def update_tactical(self, state):
        """更新战术分析设置"""
        self.tactical_system.config['tactical_analysis_enabled'] = (state == Qt.Checked)
    
    def update_threat(self, state):
        """更新威胁评估设置"""
        self.tactical_system.config['threat_assessment_enabled'] = (state == Qt.Checked)
    
    def update_environment(self, state):
        """更新环境分析设置"""
        self.tactical_system.config['environment_analysis_enabled'] = (state == Qt.Checked)
    
    def generate_report(self):
        """生成分析报告"""
        report = self.tactical_system.generate_report()
        
        report_text = "=== 智能战术视觉系统分析报告 ===\n\n"
        for key, value in report.items():
            report_text += f"{key}: {value}\n"
        
        # 显示报告
        msg = QMessageBox()
        msg.setWindowTitle("系统分析报告")
        msg.setText(report_text)
        msg.exec_()
    
    def save_data(self):
        """保存数据"""
        success, message = self.tactical_system.save_data()
        
        msg = QMessageBox()
        msg.setWindowTitle("数据保存")
        if success:
            msg.setIcon(QMessageBox.Information)
        else:
            msg.setIcon(QMessageBox.Warning)
        msg.setText(message)
        msg.exec_()
    
    def load_data(self):
        """加载数据"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择数据文件", self.tactical_system.save_path, "JSON文件 (*.json)"
        )
        
        if file_path:
            success, message = self.tactical_system.load_data(file_path)
            
            msg = QMessageBox()
            msg.setWindowTitle("数据加载")
            if success:
                msg.setIcon(QMessageBox.Information)
            else:
                msg.setIcon(QMessageBox.Warning)
            msg.setText(message)
            msg.exec_()
    
    def closeEvent(self, event):
        """关闭事件"""
        self.stop_video()
        event.accept()

def main():
    """主函数"""
    app = QApplication(sys.argv)
    
    # 设置应用程序信息
    app.setApplicationName("增强版智能战术视觉系统")
    app.setApplicationVersion("2.0")
    
    # 创建并显示主窗口
    window = TacticalVisionGUI()
    window.show()
    
    # 显示启动消息
    QMessageBox.information(window, "系统启动", 
                           "增强版智能战术视觉系统已启动\n\n"
                           "系统特性:\n"
                           "- YOLO实时目标检测\n"
                           "- 高级多目标跟踪\n"
                           "- 深度态势分析\n"
                           "- 智能威胁评估\n"
                           "- 科学战术决策\n\n"
                           "点击'开始'按钮启动视频分析")
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()