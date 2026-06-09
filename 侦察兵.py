import cv2
import numpy as np
import torch
import torch.nn as nn
from ultralytics import YOLO
import time
import json
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple
import threading
from queue import Queue, PriorityQueue
import socket
import struct
import pickle
from scipy.optimize import linear_sum_assignment
import math

# 配置日志系统
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("AdvancedScoutSystem")

class SensorType(Enum):
    VISIBLE_LIGHT = "visible"
    THERMAL = "thermal"
    NIGHT_VISION = "night_vision"
    DEPTH = "depth"
    LIDAR = "lidar"
    RADAR = "radar"

class ThreatLevel(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

@dataclass
class Detection:
    bbox: np.ndarray  # [x1, y1, x2, y2]
    confidence: float
    class_id: int
    track_id: Optional[int] = None
    sensor_type: SensorType = SensorType.VISIBLE_LIGHT
    position_3d: Optional[np.ndarray] = None
    velocity: Optional[np.ndarray] = None

@dataclass
class ThreatAssessment:
    threat_level: ThreatLevel
    confidence: float
    factors: List[str]
    recommended_actions: List[str]
    engagement_priority: int

class MultiSensorFusion:
    """多传感器数据融合引擎"""
    
    def __init__(self):
        self.sensors = {}
        self.fusion_weights = {
            SensorType.VISIBLE_LIGHT: 0.3,
            SensorType.THERMAL: 0.25,
            SensorType.NIGHT_VISION: 0.2,
            SensorType.DEPTH: 0.15,
            SensorType.LIDAR: 0.1
        }
        
    def register_sensor(self, sensor_type: SensorType, calibration_matrix: np.ndarray):
        """注册传感器并设置标定参数"""
        self.sensors[sensor_type] = {
            'calibration': calibration_matrix,
            'last_update': time.time(),
            'reliability': 1.0
        }
    
    def fuse_detections(self, detections_list: List[List[Detection]]) -> List[Detection]:
        """多传感器检测结果融合"""
        if not detections_list:
            return []
        
        # 时间同步和空间配准
        synchronized_dets = self._temporal_spatial_alignment(detections_list)
        
        # 数据关联
        associated_dets = self._data_association(synchronized_dets)
        
        # 决策级融合
        fused_detections = self._decision_fusion(associated_dets)
        
        return fused_detections
    
    def _temporal_spatial_alignment(self, detections_list):
        """时空配准"""
        aligned_detections = []
        current_time = time.time()
        
        for i, detections in enumerate(detections_list):
            sensor_types = list(self.sensors.keys())
            if i >= len(sensor_types):
                continue
                
            sensor_type = sensor_types[i]
            calibration = self.sensors[sensor_type]['calibration']
            
            aligned = []
            for det in detections:
                # 应用标定变换
                if det.position_3d is not None:
                    transformed_pos = calibration @ det.position_3d
                    det.position_3d = transformed_pos
                
                # 时间补偿
                time_delta = current_time - self.sensors[sensor_type]['last_update']
                if det.velocity is not None and det.position_3d is not None:
                    det.position_3d += det.velocity * time_delta
                
                aligned.append(det)
            
            aligned_detections.append(aligned)
        
        return aligned_detections
    
    def _data_association(self, detections_list):
        """多目标数据关联"""
        if not detections_list or all(len(dets) == 0 for dets in detections_list):
            return []
            
        # 使用匈牙利算法进行数据关联
        cost_matrix = self._build_cost_matrix(detections_list)
        row_ind, col_ind = linear_sum_assignment(cost_matrix)
        
        associated_detections = []
        for i, j in zip(row_ind, col_ind):
            if i < cost_matrix.shape[0] and j < cost_matrix.shape[1] and cost_matrix[i, j] < 0.5:
                detections_to_merge = []
                for k, dets in enumerate(detections_list):
                    if i < len(dets):
                        detections_to_merge.append(dets[i])
                
                if detections_to_merge:
                    merged_det = self._merge_detections(detections_to_merge)
                    associated_detections.append(merged_det)
        
        return associated_detections
    
    def _build_cost_matrix(self, detections_list):
        """构建关联代价矩阵"""
        max_detections = max(len(dets) for dets in detections_list)
        if max_detections == 0:
            return np.array([])
            
        cost_matrix = np.ones((max_detections, max_detections))
        
        for i in range(max_detections):
            for j in range(max_detections):
                costs = []
                for k, dets in enumerate(detections_list):
                    if i < len(dets) and j < len(dets):
                        sensor_types = list(self.sensors.keys())
                        if k < len(sensor_types):
                            sensor_type = sensor_types[k]
                            weight = self.fusion_weights[sensor_type]
                            
                            # 计算位置相似度
                            if (dets[i].position_3d is not None and 
                                dets[j].position_3d is not None):
                                pos_sim = self._position_similarity(
                                    dets[i].position_3d, dets[j].position_3d
                                )
                                costs.append(weight * pos_sim)
                
                if costs:
                    cost_matrix[i, j] = 1.0 - np.mean(costs)
        
        return cost_matrix
    
    def _position_similarity(self, pos1, pos2):
        """计算位置相似度"""
        distance = np.linalg.norm(pos1 - pos2)
        return np.exp(-distance / 10.0)
    
    def _merge_detections(self, detections):
        """合并多个检测结果"""
        if not detections:
            return None
            
        # 使用置信度最高的检测
        best_detection = max(detections, key=lambda x: x.confidence)
        return best_detection

class AdvancedTracker:
    """高级多目标跟踪器"""
    
    def __init__(self):
        self.tracks = {}
        self.next_track_id = 0
        self.track_history = {}
        self.max_age = 30
        
    def update(self, detections: List[Detection]) -> List[Detection]:
        """更新跟踪状态"""
        # 简单的基于IOU的跟踪
        current_track_ids = list(self.tracks.keys())
        
        for detection in detections:
            if detection.track_id is None:
                # 为新检测分配跟踪ID
                best_match_id = self._find_best_match(detection, current_track_ids)
                if best_match_id is not None:
                    detection.track_id = best_match_id
                    self.tracks[best_match_id] = detection
                    self.track_history[best_match_id].append(detection.bbox)
                else:
                    detection.track_id = self.next_track_id
                    self.tracks[self.next_track_id] = detection
                    self.track_history[self.next_track_id] = [detection.bbox]
                    self.next_track_id += 1
        
        # 清理丢失的轨迹
        self._delete_lost_tracks()
        
        return detections
    
    def _find_best_match(self, detection, current_track_ids):
        """找到最佳匹配的轨迹ID"""
        best_iou = 0.5  # IOU阈值
        best_id = None
        
        for track_id in current_track_ids:
            if track_id in self.tracks:
                last_bbox = self.tracks[track_id].bbox
                iou = self._calculate_iou(detection.bbox, last_bbox)
                if iou > best_iou:
                    best_iou = iou
                    best_id = track_id
        
        return best_id
    
    def _calculate_iou(self, bbox1, bbox2):
        """计算两个边界框的IOU"""
        x1 = max(bbox1[0], bbox2[0])
        y1 = max(bbox1[1], bbox2[1])
        x2 = min(bbox1[2], bbox2[2])
        y2 = min(bbox1[3], bbox2[3])
        
        if x2 <= x1 or y2 <= y1:
            return 0.0
        
        intersection = (x2 - x1) * (y2 - y1)
        area1 = (bbox1[2] - bbox1[0]) * (bbox1[3] - bbox1[1])
        area2 = (bbox2[2] - bbox2[0]) * (bbox2[3] - bbox2[1])
        union = area1 + area2 - intersection
        
        return intersection / union if union > 0 else 0.0
    
    def _delete_lost_tracks(self):
        """删除丢失的轨迹"""
        tracks_to_delete = []
        for track_id in self.tracks:
            # 简单实现：如果轨迹历史很长但没有更新，则删除
            if (track_id in self.track_history and 
                len(self.track_history[track_id]) > self.max_age):
                tracks_to_delete.append(track_id)
        
        for track_id in tracks_to_delete:
            del self.tracks[track_id]
            del self.track_history[track_id]

class BehavioralAnalyzer:
    """高级行为分析引擎"""
    
    def __init__(self):
        self.behavior_profiles = {}
        self.group_dynamics = GroupDynamicsAnalyzer()
        
    def analyze_behavior(self, tracks: Dict[int, Detection], frame_timestamp: float) -> Dict[int, Dict]:
        """分析目标行为模式"""
        behavioral_analysis = {}
        
        for track_id, detection in tracks.items():
            # 运动模式分析
            movement_pattern = self._analyze_movement_pattern(track_id, detection)
            
            # 威胁评估
            threat_assessment = self._assess_threat_level(track_id, detection, movement_pattern)
            
            behavioral_analysis[track_id] = {
                'movement_pattern': movement_pattern,
                'threat_assessment': threat_assessment,
                'timestamp': frame_timestamp
            }
        
        return behavioral_analysis
    
    def _analyze_movement_pattern(self, track_id, detection):
        """分析运动模式"""
        if track_id not in self.behavior_profiles:
            self.behavior_profiles[track_id] = {
                'path_history': [],
                'speed_history': [],
                'direction_history': [],
                'start_time': time.time()
            }
        
        profile = self.behavior_profiles[track_id]
        
        # 计算边界框中心作为位置
        bbox_center = np.array([
            (detection.bbox[0] + detection.bbox[2]) / 2,
            (detection.bbox[1] + detection.bbox[3]) / 2
        ])
        profile['path_history'].append(bbox_center)
        
        # 限制历史长度
        if len(profile['path_history']) > 100:
            profile['path_history'].pop(0)
        
        # 计算速度（基于边界框中心移动）
        if len(profile['path_history']) >= 2:
            last_pos = profile['path_history'][-2]
            current_pos = profile['path_history'][-1]
            distance = np.linalg.norm(current_pos - last_pos)
            profile['speed_history'].append(distance)
            if len(profile['speed_history']) > 50:
                profile['speed_history'].pop(0)
        
        # 分析运动特征
        movement_features = {
            'average_speed': np.mean(profile['speed_history']) if profile['speed_history'] else 0,
            'speed_variance': np.var(profile['speed_history']) if profile['speed_history'] else 0,
            'movement_consistency': self._calculate_movement_consistency(profile['path_history']),
        }
        
        return movement_features
    
    def _calculate_movement_consistency(self, path_history):
        """计算运动一致性"""
        if len(path_history) < 3:
            return 1.0
        
        directions = []
        for i in range(1, len(path_history)):
            dx = path_history[i][0] - path_history[i-1][0]
            dy = path_history[i][1] - path_history[i-1][1]
            if dx != 0 or dy != 0:
                direction = math.atan2(dy, dx)
                directions.append(direction)
        
        if len(directions) < 2:
            return 1.0
        
        # 计算方向变化的标准差
        direction_std = np.std(directions)
        consistency = 1.0 / (1.0 + direction_std)  # 方向变化越小，一致性越高
        
        return min(consistency, 1.0)
    
    def _assess_threat_level(self, track_id, detection, movement_pattern):
        """评估威胁等级"""
        threat_score = 0.0
        
        # 基于速度的威胁评估
        avg_speed = movement_pattern.get('average_speed', 0)
        if avg_speed > 10:
            threat_score += 0.3
        elif avg_speed > 5:
            threat_score += 0.15
        
        # 基于运动一致性的威胁评估
        consistency = movement_pattern.get('movement_consistency', 1.0)
        if consistency < 0.5:  # 运动不一致可能表示可疑行为
            threat_score += 0.2
        
        # 基于目标类别的威胁评估
        if detection.class_id in [0, 2, 3, 5, 7]:  # 人、车辆等
            threat_score += 0.3
        
        return {
            'threat_score': min(threat_score, 1.0),
            'factors': ['movement_analysis', 'object_type']
        }

class AdversarialDetection:
    """对抗性目标检测"""
    
    def __init__(self):
        self.camouflage_detector = AdvancedCamouflageDetector()
        
    def detect_adversarial_targets(self, frame: np.ndarray, detections: List[Detection]) -> List[Detection]:
        """检测对抗性目标"""
        adversarial_detections = []
        
        for detection in detections:
            roi = self._extract_roi(frame, detection.bbox)
            
            # 伪装检测
            camouflage_score = self.camouflage_detector.analyze(roi, frame, detection.bbox)
            
            if camouflage_score > 0.7:
                detection.confidence *= (1 - camouflage_score)
                detection.class_id = -1
                adversarial_detections.append(detection)
                
                logger.warning(f"检测到对抗性目标: track_id={detection.track_id}, score={camouflage_score:.3f}")
        
        return adversarial_detections
    
    def _extract_roi(self, frame, bbox):
        """提取感兴趣区域"""
        x1, y1, x2, y2 = map(int, bbox)
        x1 = max(0, x1)
        y1 = max(0, y1)
        x2 = min(frame.shape[1], x2)
        y2 = min(frame.shape[0], y2)
        
        return frame[y1:y2, x1:x2]

class RealTimeDecisionEngine:
    """实时决策引擎"""
    
    def __init__(self):
        self.decision_rules = self._load_decision_rules()
        self.mission_objectives = {}
        
    def _load_decision_rules(self):
        """加载决策规则"""
        return {
            'sensor_control_rules': {
                'high_threat': 'max_resolution',
                'medium_threat': 'balanced',
                'low_threat': 'energy_saving'
            },
            'alert_levels': {
                'critical': 'red',
                'high': 'orange', 
                'medium': 'yellow',
                'low': 'green'
            }
        }
    
    def make_decision(self, situational_awareness: Dict, mission_context: Dict) -> Dict:
        """基于当前态势做出决策"""
        decisions = {
            'sensor_control': self._optimize_sensor_usage(situational_awareness),
            'resource_allocation': self._allocate_resources(situational_awareness),
            'engagement_decisions': self._make_engagement_decisions(situational_awareness),
            'alert_level': self._determine_alert_level(situational_awareness),
            'recommended_actions': self._generate_actions(situational_awareness, mission_context)
        }
        
        return decisions
    
    def _optimize_sensor_usage(self, situational_awareness):
        """优化传感器使用"""
        threat_count = len(situational_awareness.get('threat_assessments', {}))
        
        if threat_count > 3:
            return "high_priority_mode"
        elif threat_count > 0:
            return "balanced_mode"
        else:
            return "surveillance_mode"
    
    def _allocate_resources(self, situational_awareness):
        """分配资源"""
        return {
            'processing_power': 'high' if len(situational_awareness.get('detections', [])) > 5 else 'normal',
            'bandwidth': 'high',
            'storage': 'continuous'
        }
    
    def _make_engagement_decisions(self, situational_awareness):
        """制定交战决策"""
        engagement_decisions = {}
        
        for track_id, assessment in situational_awareness.get('threat_assessments', {}).items():
            if assessment.threat_level in [ThreatLevel.HIGH, ThreatLevel.CRITICAL]:
                engagement_decisions[track_id] = {
                    'engagement_priority': assessment.engagement_priority,
                    'recommended_weapon': 'standard',
                    'engagement_conditions': {'range': 'medium', 'visibility': 'good'},
                }
        
        return engagement_decisions
    
    def _determine_alert_level(self, situational_awareness):
        """确定警报级别"""
        threat_assessments = situational_awareness.get('threat_assessments', {})
        
        if any(ta.threat_level == ThreatLevel.CRITICAL for ta in threat_assessments.values()):
            return 'red'
        elif any(ta.threat_level == ThreatLevel.HIGH for ta in threat_assessments.values()):
            return 'orange'
        elif any(ta.threat_level == ThreatLevel.MEDIUM for ta in threat_assessments.values()):
            return 'yellow'
        else:
            return 'green'
    
    def _generate_actions(self, situational_awareness, mission_context):
        """生成行动建议"""
        actions = []
        threat_count = len(situational_awareness.get('threat_assessments', {}))
        
        if threat_count > 0:
            actions.append(f"跟踪{threat_count}个潜在威胁目标")
        
        if any(ta.threat_level == ThreatLevel.CRITICAL for ta in situational_awareness.get('threat_assessments', {}).values()):
            actions.append("发出最高级别警报")
            actions.append("准备应对紧急情况")
        
        return actions

class NetworkCommunicator:
    """网络通信模块"""
    
    def __init__(self, host='localhost', port=9999):
        self.host = host
        self.port = port
        self.connected = False
        self.message_queue = Queue()
        
    def connect(self):
        """连接到指挥系统"""
        try:
            # 模拟连接，实际应用中这里会建立真实的socket连接
            self.connected = True
            logger.info(f"模拟连接到指挥系统 {self.host}:{self.port}")
            
        except Exception as e:
            logger.error(f"连接失败: {e}")
    
    def send_detection_data(self, detections: List[Detection], situational_awareness: Dict):
        """发送检测数据和态势感知信息"""
        if not self.connected:
            return
        
        # 模拟发送数据
        message = {
            'timestamp': time.time(),
            'detection_count': len(detections),
            'threat_levels': [ta.threat_level.name for ta in situational_awareness.get('threat_assessments', {}).values()]
        }
        
        logger.info(f"发送数据到指挥系统: {message}")

# 辅助类实现
class AdvancedCamouflageDetector:
    def analyze(self, roi, frame, bbox):
        # 简化的伪装检测 - 基于颜色和纹理分析
        if roi.size == 0:
            return 0.0
            
        # 计算ROI与周围区域的差异
        x1, y1, x2, y2 = map(int, bbox)
        margin = 20
        surrounding = frame[
            max(0, y1-margin):min(frame.shape[0], y2+margin),
            max(0, x1-margin):min(frame.shape[1], x2+margin)
        ]
        
        if surrounding.size == 0 or roi.size == 0:
            return 0.0
            
        # 计算颜色直方图差异
        roi_hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        surrounding_hsv = cv2.cvtColor(surrounding, cv2.COLOR_BGR2HSV)
        
        roi_hist = cv2.calcHist([roi_hsv], [0, 1], None, [50, 60], [0, 180, 0, 256])
        surrounding_hist = cv2.calcHist([surrounding_hsv], [0, 1], None, [50, 60], [0, 180, 0, 256])
        
        cv2.normalize(roi_hist, roi_hist, 0, 1, cv2.NORM_MINMAX)
        cv2.normalize(surrounding_hist, surrounding_hist, 0, 1, cv2.NORM_MINMAX)
        
        similarity = cv2.compareHist(roi_hist, surrounding_hist, cv2.HISTCMP_CORREL)
        camouflage_score = 1.0 - (similarity + 1) / 2  # 转换为0-1范围，越高表示越可能伪装
        
        return camouflage_score

class GroupDynamicsAnalyzer:
    def analyze_group_behavior(self, tracks, track_id):
        return "isolated"

class AdvancedScoutSystem:
    """高级侦察系统主类"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.running = False
        
        # 初始化核心组件
        self.yolo_model = YOLO(config.get('model_path', 'yolov8n.pt'))
        self.sensor_fusion = MultiSensorFusion()
        self.tracker = AdvancedTracker()
        self.behavior_analyzer = BehavioralAnalyzer()
        self.adversarial_detector = AdversarialDetection()
        self.decision_engine = RealTimeDecisionEngine()
        self.network_comm = NetworkCommunicator(
            config.get('command_host', 'localhost'),
            config.get('command_port', 9999)
        )
        
        # 初始化传感器
        self._initialize_sensors()
        
        # 性能监控
        self.performance_stats = {
            'frame_count': 0,
            'avg_processing_time': 0,
            'detection_counts': [],
            'threat_levels': []
        }
        
        # 系统状态
        self.system_status = {
            'operational': True,
            'sensor_status': {},
            'last_update': time.time(),
            'mission_mode': 'RECON'
        }
        
        logger.info("高级侦察系统初始化完成")
    
    def _initialize_sensors(self):
        """初始化传感器配置"""
        # 模拟传感器标定矩阵
        visible_calibration = np.eye(4)
        self.sensor_fusion.register_sensor(SensorType.VISIBLE_LIGHT, visible_calibration)
    
    def start_mission(self, video_source=0):
        """开始侦察任务"""
        try:
            self.network_comm.connect()
            
            cap = cv2.VideoCapture(video_source)
            if not cap.isOpened():
                raise ValueError("无法打开视频源")
            
            self.running = True
            logger.info("开始执行侦察任务")
            
            while self.running:
                start_time = time.time()
                
                # 读取帧
                ret, frame = cap.read()
                if not ret:
                    logger.warning("无法读取视频帧")
                    break
                
                # 处理当前帧
                results = self.process_frame(frame)
                
                # 更新性能统计
                self._update_performance_stats(start_time, results)
                
                # 显示结果
                if self.config.get('display_output', True):
                    self._display_results(frame, results)
                
                # 检查退出条件
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            
            # 清理资源
            cap.release()
            cv2.destroyAllWindows()
            
        except Exception as e:
            logger.error(f"任务执行错误: {e}")
        finally:
            self.running = False
            self._generate_mission_report()
    
    def process_frame(self, frame: np.ndarray) -> Dict:
        """处理单帧图像"""
        # YOLO目标检测
        yolo_results = self.yolo_model(frame, conf=0.4, iou=0.5)
        
        # 转换为标准检测格式
        detections = self._yolo_to_detections(yolo_results[0])
        
        # 多目标跟踪
        tracked_detections = self.tracker.update(detections)
        
        # 对抗性目标检测
        adversarial_targets = self.adversarial_detector.detect_adversarial_targets(frame, tracked_detections)
        
        # 行为分析
        behavioral_analysis = self.behavior_analyzer.analyze_behavior(
            {det.track_id: det for det in tracked_detections if det.track_id is not None}, 
            time.time()
        )
        
        # 威胁评估
        threat_assessments = self._assess_threats(tracked_detections, behavioral_analysis)
        
        # 态势感知
        situational_awareness = {
            'detections': tracked_detections,
            'behavioral_analysis': behavioral_analysis,
            'threat_assessments': threat_assessments,
            'adversarial_targets': adversarial_targets,
            'timestamp': time.time(),
            'frame_id': self.performance_stats['frame_count']
        }
        
        # 实时决策
        decisions = self.decision_engine.make_decision(
            situational_awareness, self.system_status
        )
        situational_awareness['decisions'] = decisions
        
        # 发送数据到指挥系统
        self.network_comm.send_detection_data(tracked_detections, situational_awareness)
        
        return situational_awareness
    
    def _yolo_to_detections(self, yolo_result) -> List[Detection]:
        """将YOLO结果转换为标准检测格式"""
        detections = []
        
        if yolo_result.boxes is not None:
            for box in yolo_result.boxes:
                bbox = box.xyxy[0].cpu().numpy()
                confidence = box.conf[0].cpu().numpy()
                class_id = int(box.cls[0].cpu().numpy())
                
                detection = Detection(
                    bbox=bbox,
                    confidence=float(confidence),
                    class_id=class_id,
                    sensor_type=SensorType.VISIBLE_LIGHT
                )
                
                detections.append(detection)
        
        return detections
    
    def _assess_threats(self, detections: List[Detection], behavioral_analysis: Dict) -> Dict[int, ThreatAssessment]:
        """综合威胁评估"""
        threat_assessments = {}
        
        for detection in detections:
            if detection.track_id is None:
                continue
                
            behavior = behavioral_analysis.get(detection.track_id, {})
            threat_factors = []
            threat_score = 0.0
            
            # 基于类别的威胁基础分
            class_threats = {
                0: 0.3,   # person
                1: 0.1,   # bicycle
                2: 0.5,   # car
                3: 0.6,   # motorcycle
                5: 0.8,   # bus
                7: 0.9    # truck
            }
            
            threat_score += class_threats.get(detection.class_id, 0.1)
            
            # 行为威胁因子
            movement = behavior.get('movement_pattern', {})
            if movement.get('average_speed', 0) > 5.0:
                threat_score += 0.2
                threat_factors.append('high_speed')
            
            if movement.get('speed_variance', 0) > 2.0:
                threat_score += 0.15
                threat_factors.append('erratic_movement')
            
            # 确定威胁等级
            if threat_score >= 0.8:
                threat_level = ThreatLevel.CRITICAL
            elif threat_score >= 0.6:
                threat_level = ThreatLevel.HIGH
            elif threat_score >= 0.4:
                threat_level = ThreatLevel.MEDIUM
            else:
                threat_level = ThreatLevel.LOW
            
            threat_assessments[detection.track_id] = ThreatAssessment(
                threat_level=threat_level,
                confidence=min(threat_score, 1.0),
                factors=threat_factors,
                recommended_actions=self._get_recommended_actions(threat_level, threat_factors),
                engagement_priority=int(threat_score * 100)
            )
        
        return threat_assessments
    
    def _get_recommended_actions(self, threat_level: ThreatLevel, factors: List[str]) -> List[str]:
        """根据威胁等级生成推荐行动"""
        actions = []
        
        if threat_level == ThreatLevel.CRITICAL:
            actions.extend(['立即警报', '准备交战', '请求支援'])
        elif threat_level == ThreatLevel.HIGH:
            actions.extend(['高度警戒', '持续跟踪', '准备应对措施'])
        elif threat_level == ThreatLevel.MEDIUM:
            actions.extend(['保持监视', '记录行为', '评估意图'])
        else:
            actions.append('常规监视')
        
        if 'high_speed' in factors:
            actions.append('速度监控')
        if 'erratic_movement' in factors:
            actions.append('行为分析')
        
        return actions
    
    def _display_results(self, frame: np.ndarray, results: Dict):
        """显示处理结果"""
        display_frame = frame.copy()
        
        # 绘制检测框
        for detection in results['detections']:
            bbox = detection.bbox.astype(int)
            track_id = detection.track_id or 0
            
            # 根据威胁等级选择颜色
            threat_assessment = results['threat_assessments'].get(track_id)
            if threat_assessment:
                if threat_assessment.threat_level == ThreatLevel.CRITICAL:
                    color = (0, 0, 255)  # 红色
                elif threat_assessment.threat_level == ThreatLevel.HIGH:
                    color = (0, 165, 255)  # 橙色
                elif threat_assessment.threat_level == ThreatLevel.MEDIUM:
                    color = (0, 255, 255)  # 黄色
                else:
                    color = (0, 255, 0)  # 绿色
            else:
                color = (255, 255, 255)  # 白色
            
            cv2.rectangle(display_frame, (bbox[0], bbox[1]), (bbox[2], bbox[3]), color, 2)
            
            # 显示跟踪ID和威胁等级
            label = f"ID:{track_id}"
            if threat_assessment:
                label += f" Thr:{threat_assessment.threat_level.name}"
            
            cv2.putText(display_frame, label, (bbox[0], bbox[1]-10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        
        # 显示系统状态
        self._draw_status_panel(display_frame, results)
        
        cv2.imshow('Advanced Scout System', display_frame)
    
    def _draw_status_panel(self, frame: np.ndarray, results: Dict):
        """绘制系统状态面板"""
        panel_height = 120
        panel = np.zeros((panel_height, frame.shape[1], 3), dtype=np.uint8)
        
        # 系统状态信息
        status_lines = [
            f"Frame: {self.performance_stats['frame_count']}",
            f"Targets: {len(results['detections'])}",
            f"High Threat: {sum(1 for ta in results['threat_assessments'].values() if ta.threat_level.value >= 3)}",
            f"FPS: {1/self.performance_stats['avg_processing_time'] if self.performance_stats['avg_processing_time'] > 0 else 0:.1f}",
            f"Mode: {self.system_status['mission_mode']}",
            f"Adversarial: {len(results.get('adversarial_targets', []))}"
        ]
        
        for i, line in enumerate(status_lines):
            cv2.putText(panel, line, (10, 20 + i * 20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
        
        # 将状态面板叠加到原图上
        frame[0:panel_height, 0:frame.shape[1]] = cv2.addWeighted(
            frame[0:panel_height, 0:frame.shape[1]], 0.7, panel, 0.3, 0
        )
    
    def _update_performance_stats(self, start_time: float, results: Dict):
        """更新性能统计"""
        processing_time = time.time() - start_time
        self.performance_stats['frame_count'] += 1
        self.performance_stats['avg_processing_time'] = (
            self.performance_stats['avg_processing_time'] * 0.9 + processing_time * 0.1
        )
        self.performance_stats['detection_counts'].append(len(results['detections']))
        
        # 每100帧记录一次统计
        if self.performance_stats['frame_count'] % 100 == 0:
            logger.info(f"处理统计: 帧数={self.performance_stats['frame_count']}, "
                       f"平均处理时间={self.performance_stats['avg_processing_time']:.3f}s")
    
    def _generate_mission_report(self):
        """生成任务报告"""
        report = {
            'mission_duration': time.time() - self.system_status['last_update'],
            'total_frames': self.performance_stats['frame_count'],
            'avg_targets_per_frame': np.mean(self.performance_stats['detection_counts']) if self.performance_stats['detection_counts'] else 0,
            'system_performance': {
                'avg_processing_time': self.performance_stats['avg_processing_time'],
                'total_processing_time': self.performance_stats['avg_processing_time'] * self.performance_stats['frame_count']
            }
        }
        
        logger.info(f"任务报告: {json.dumps(report, indent=2, default=str)}")
        
        # 保存报告到文件
        with open(f'mission_report_{int(time.time())}.json', 'w') as f:
            json.dump(report, f, indent=2, default=str)

# 配置和使用示例
if __name__ == "__main__":
    config = {
        'model_path': 'yolov8n.pt',
        'command_host': 'localhost',
        'command_port': 9999,
        'display_output': True,
        'log_level': 'INFO'
    }
    
    # 创建侦察系统实例
    scout_system = AdvancedScoutSystem(config)
    
    try:
        # 开始侦察任务（使用摄像头）
        scout_system.start_mission(0)  # 0 表示默认摄像头
        
    except KeyboardInterrupt:
        logger.info("任务被用户中断")
    except Exception as e:
        logger.error(f"系统错误: {e}")
    finally:
        scout_system.running = False