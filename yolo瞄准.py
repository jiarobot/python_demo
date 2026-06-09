import cv2
import numpy as np
import time
import math
from collections import deque, defaultdict
import threading
import random
from ultralytics import YOLO
import torch
import warnings
warnings.filterwarnings('ignore')

class YOLOCombatSight:
    def __init__(self, model_path='yolov8n.pt'):
        # 系统配置
        self.setup_configuration()
        
        # 加载YOLO模型
        self.model = self.load_yolo_model(model_path)
        
        # 算法引擎初始化
        self.setup_algorithms()
        
        # 数据管理系统
        self.setup_data_management()
        
        # 武器系统模拟
        self.setup_weapon_system()
        
        # 启动系统
        self.initialize_system()
        
        print("⚡ YOLO战斗瞄准系统初始化完成")
        print("🎯 系统状态: 就绪")
    
    def load_yolo_model(self, model_path):
        """加载YOLO模型"""
        print(f"🔧 加载YOLO模型: {model_path}")
        try:
            model = YOLO(model_path)
            # 测试模型
            if torch.cuda.is_available():
                model.to('cuda')
                print("✅ YOLO模型加载成功 (GPU加速)")
            else:
                print("✅ YOLO模型加载成功 (CPU模式)")
            return model
        except Exception as e:
            print(f"❌ YOLO模型加载失败: {e}")
            return None
    
    def setup_configuration(self):
        """系统核心配置"""
        # 战斗模式配置
        self.combat_modes = {
            'recon': {'detection_range': 200, 'tracking_intensity': 0.7},
            'assault': {'detection_range': 100, 'tracking_intensity': 0.9},
            'sniper': {'detection_range': 300, 'tracking_intensity': 0.8},
            'auto': {'detection_range': 150, 'tracking_intensity': 1.0}
        }
        self.current_mode = 'auto'
        
        # YOLO类别到战斗类别的映射
        self.class_mapping = {
            'person': 'infantry',
            'bicycle': 'vehicle',
            'car': 'vehicle',
            'motorcycle': 'vehicle',
            'airplane': 'aircraft',
            'bus': 'vehicle',
            'train': 'vehicle',
            'truck': 'vehicle',
            'boat': 'vehicle',
            'bird': 'unknown',
            'cat': 'unknown',
            'dog': 'unknown',
            'horse': 'unknown',
            'sheep': 'unknown',
            'cow': 'unknown',
            'elephant': 'unknown',
            'bear': 'unknown',
            'zebra': 'unknown',
            'giraffe': 'unknown'
        }
        
        # 目标威胁级别配置
        self.threat_config = {
            'infantry': 0.8,
            'vehicle': 0.6,
            'aircraft': 0.9,
            'unknown': 0.3
        }
        
        # 弹道参数
        self.ballistics = {
            'caliber': 7.62,           # mm
            'muzzle_velocity': 830,    # m/s
            'bullet_mass': 9.5,        # g
            'drag_coefficient': 0.295,
            'zero_range': 100,         # meters
            'sight_height': 0.05       # meters
        }
        
        # 环境参数
        self.environment = {
            'gravity': 9.81,
            'air_density': 1.225,
            'temperature': 15,
            'humidity': 50,
            'pressure': 1013.25,
            'wind_speed': 2,
            'wind_direction': 0
        }
    
    def setup_algorithms(self):
        """高级算法引擎"""
        # 预测引擎
        self.prediction_engine = TrajectoryPredictor()
        
        # 威胁分析器
        self.threat_analyzer = ThreatAssessmentEngine()
        
        # 弹道计算器
        self.ballistic_calculator = BallisticSolver()
    
    def setup_data_management(self):
        """数据管理系统"""
        # 目标数据库
        self.target_database = {}
        self.target_counter = 0
        
        # 轨迹存储器
        self.trajectory_archive = defaultdict(lambda: deque(maxlen=100))
        
        # 性能监控
        self.performance = {
            'frame_rate': deque(maxlen=60),
            'processing_time': deque(maxlen=60),
            'detection_accuracy': deque(maxlen=100),
            'tracking_stability': deque(maxlen=100)
        }
        
        # 系统状态
        self.system_state = {
            'operational': True,
            'calibrated': False,
            'target_locked': False,
            'firing_authorized': False,
            'threat_level': 0.0,
            'ammunition_count': 30,
            'system_health': 100.0,
            'camera_status': 'unknown',
            'yolo_status': 'unknown'
        }
        
        # 战斗记录
        self.combat_log = deque(maxlen=1000)
    
    def setup_weapon_system(self):
        """武器系统模拟"""
        self.weapon_state = {
            'safety_off': False,
            'firing_mode': 'semi',  # semi, burst, auto
            'barrel_temperature': 20,
            'recoil_compensation': 0.8,
            'vibration_damping': 0.9
        }
        
        # 弹药类型
        self.ammunition_types = {
            'standard': {'velocity': 830, 'mass': 9.5, 'bc': 0.295},
            'armor_piercing': {'velocity': 870, 'mass': 10.4, 'bc': 0.320},
            'tracer': {'velocity': 820, 'mass': 9.7, 'bc': 0.280}
        }
        self.current_ammo = 'standard'
    
    def initialize_system(self):
        """系统初始化"""
        # 启动处理线程
        self.running = True
        
        # 主处理管道
        self.processing_pipeline = YOLOProcessingPipeline(self)
        self.processing_thread = threading.Thread(target=self.processing_pipeline.run)
        self.processing_thread.daemon = True
        self.processing_thread.start()
        
        # 系统监控
        self.monitoring_thread = threading.Thread(target=self.system_monitor)
        self.monitoring_thread.daemon = True
        self.monitoring_thread.start()
        
        # 战术分析
        self.tactical_thread = threading.Thread(target=self.tactical_analysis)
        self.tactical_thread.daemon = True
        self.tactical_thread.start()
        
        # 执行系统校准
        self.perform_system_calibration()
    
    def perform_system_calibration(self):
        """系统校准程序"""
        print("🔧 执行系统校准...")
        
        # 模拟校准过程
        time.sleep(1)
        
        # 校准完成
        self.system_state['calibrated'] = True
        self.log_event("SYSTEM_CALIBRATION_COMPLETE", "系统校准完成")
        
        print("✅ 系统校准完成")
    
    def system_monitor(self):
        """系统健康监控"""
        while self.running:
            try:
                # 监控系统性能
                current_time = time.time()
                
                # 检查系统健康度
                if len(self.performance['processing_time']) > 10:
                    avg_process_time = np.mean(self.performance['processing_time'])
                    if avg_process_time > 0.1:  # 如果平均处理时间超过100ms
                        self.system_state['system_health'] *= 0.99
                
                # 武器系统监控
                if self.weapon_state['barrel_temperature'] > 100:
                    self.weapon_state['barrel_temperature'] *= 0.95  # 冷却
                
                # 环境更新
                self.update_environment()
                
                time.sleep(0.5)
                
            except Exception as e:
                self.log_event("SYSTEM_MONITOR_ERROR", f"监控错误: {str(e)}")
                time.sleep(1)
    
    def tactical_analysis(self):
        """战术分析引擎"""
        while self.running:
            try:
                # 分析目标行为模式
                self.analyze_tactical_patterns()
                
                # 更新威胁评估
                self.update_global_threat_assessment()
                
                # 优化系统参数
                self.optimize_system_parameters()
                
                time.sleep(1.0)  # 1Hz战术分析
                
            except Exception as e:
                self.log_event("TACTICAL_ANALYSIS_ERROR", f"战术分析错误: {str(e)}")
                time.sleep(2)
    
    def analyze_tactical_patterns(self):
        """分析战术模式"""
        if not self.target_database:
            return
        
        # 分析目标协同行为
        target_positions = [target['current_position'] for target in self.target_database.values()]
        
        if len(target_positions) >= 2:
            # 计算目标间距离矩阵
            positions_array = np.array(target_positions)
            distances = np.linalg.norm(positions_array[:, np.newaxis] - positions_array, axis=2)
            
            # 检测编队模式
            formation_score = self.detect_formation_patterns(distances)
            
            # 检测包围模式
            encirclement_score = self.detect_encirclement_pattern(positions_array)
            
            # 更新战术态势
            tactical_situation = {
                'formation_detected': formation_score > 0.7,
                'encirclement_risk': encirclement_score,
                'target_density': len(target_positions) / 10000.0,  # 每万平方米目标数
                'coordinated_movement': self.analyze_coordinated_movement()
            }
            
            self.system_state['tactical_situation'] = tactical_situation
    
    def detect_formation_patterns(self, distances):
        """检测编队模式"""
        try:
            # 分析距离分布
            flat_distances = distances[np.triu_indices_from(distances, k=1)]
            
            if len(flat_distances) < 2:
                return 0.0
            
            # 计算距离的一致性（编队通常有规律的距离）
            distance_std = np.std(flat_distances)
            distance_mean = np.mean(flat_distances)
            
            # 低标准差可能表示编队
            formation_score = max(0, 1 - distance_std / (distance_mean + 1e-5))
            
            return min(formation_score, 1.0)
            
        except:
            return 0.0
    
    def detect_encirclement_pattern(self, positions):
        """检测包围模式"""
        try:
            if len(positions) < 3:
                return 0.0
            
            # 计算位置的中心点
            center = np.mean(positions, axis=0)
            
            # 计算每个目标相对于中心的角度
            vectors = positions - center
            angles = np.arctan2(vectors[:, 1], vectors[:, 0])
            angles = np.sort(angles)
            
            # 计算角度间隔
            angle_diffs = np.diff(angles)
            angle_diffs = np.append(angle_diffs, 2*np.pi - angles[-1] + angles[0])
            
            # 最大间隔表示包围的缺口
            max_gap = np.max(angle_diffs)
            encirclement_score = 1 - (max_gap / (2*np.pi))
            
            return encirclement_score
            
        except:
            return 0.0
    
    def analyze_coordinated_movement(self):
        """分析协同运动"""
        if len(self.target_database) < 2:
            return 0.0
        
        try:
            velocity_correlations = []
            
            for target1 in self.target_database.values():
                for target2 in self.target_database.values():
                    if target1['id'] >= target2['id']:
                        continue
                    
                    vel1 = np.array(target1['velocity'])
                    vel2 = np.array(target2['velocity'])
                    
                    if np.linalg.norm(vel1) > 0.1 and np.linalg.norm(vel2) > 0.1:
                        # 计算速度方向相关性
                        dot_product = np.dot(vel1, vel2)
                        mag_product = np.linalg.norm(vel1) * np.linalg.norm(vel2)
                        correlation = dot_product / (mag_product + 1e-5)
                        velocity_correlations.append(correlation)
            
            if velocity_correlations:
                return np.mean(np.abs(velocity_correlations))
            else:
                return 0.0
                
        except:
            return 0.0
    
    def update_global_threat_assessment(self):
        """更新全局威胁评估"""
        if not self.target_database:
            self.system_state['threat_level'] = 0.0
            return
        
        # 计算综合威胁级别
        threat_scores = []
        
        for target in self.target_database.values():
            threat_score = self.calculate_comprehensive_threat(target)
            threat_scores.append(threat_score)
        
        # 全局威胁基于最高威胁目标和目标数量
        max_threat = max(threat_scores) if threat_scores else 0.0
        target_count_factor = min(len(threat_scores) / 10.0, 1.0)
        
        global_threat = max_threat * 0.7 + target_count_factor * 0.3
        
        # 战术态势影响
        tactical_bonus = 0.0
        if 'tactical_situation' in self.system_state:
            tactical = self.system_state['tactical_situation']
            if tactical.get('formation_detected', False):
                tactical_bonus += 0.2
            if tactical.get('encirclement_risk', 0) > 0.7:
                tactical_bonus += 0.3
            if tactical.get('coordinated_movement', 0) > 0.6:
                tactical_bonus += 0.2
        
        self.system_state['threat_level'] = min(global_threat + tactical_bonus, 1.0)
    
    def calculate_comprehensive_threat(self, target):
        """计算综合威胁评分"""
        # 基础威胁
        base_threat = target.get('threat_level', 0.5)
        
        # 距离威胁 (越近威胁越大)
        distance = target.get('estimated_distance', 100)
        distance_threat = max(0, 1 - distance / 300.0)
        
        # 速度威胁
        speed = np.linalg.norm(target.get('velocity', (0, 0)))
        speed_threat = min(speed / 10.0, 1.0)
        
        # 行为威胁
        behavior_threat = self.analyze_behavioral_threat(target)
        
        # 武器指向威胁 (模拟)
        weapon_threat = 0.0
        if random.random() < 0.3:  # 30%几率目标有武器指向
            weapon_threat = 0.8
        
        # 综合计算
        comprehensive_threat = (
            base_threat * 0.3 +
            distance_threat * 0.25 +
            speed_threat * 0.2 +
            behavior_threat * 0.15 +
            weapon_threat * 0.1
        )
        
        return min(comprehensive_threat, 1.0)
    
    def analyze_behavioral_threat(self, target):
        """分析行为威胁"""
        history = self.trajectory_archive.get(target['id'], [])
        
        if len(history) < 5:
            return 0.5
        
        positions = [pos for pos in history]
        
        # 分析运动模式
        movement_pattern = self.analyze_movement_pattern(positions)
        
        # 分析接近速度
        approach_speed = self.analyze_approach_speed(target)
        
        # 分析规避动作
        evasion_score = self.detect_evasion_maneuvers(positions)
        
        behavioral_threat = (
            movement_pattern * 0.4 +
            approach_speed * 0.4 +
            evasion_score * 0.2
        )
        
        return behavioral_threat
    
    def analyze_movement_pattern(self, positions):
        """分析运动模式"""
        if len(positions) < 3:
            return 0.5
        
        # 计算运动复杂性
        direction_changes = 0
        speeds = []
        
        for i in range(1, len(positions)):
            dx = positions[i][0] - positions[i-1][0]
            dy = positions[i][1] - positions[i-1][1]
            speed = math.sqrt(dx*dx + dy*dy)
            speeds.append(speed)
            
            if i >= 2:
                prev_dx = positions[i-1][0] - positions[i-2][0]
                prev_dy = positions[i-1][1] - positions[i-2][1]
                
                if abs(dx - prev_dx) > 5 or abs(dy - prev_dy) > 5:
                    direction_changes += 1
        
        # 复杂的运动模式可能表示战术移动
        complexity = min(direction_changes / len(positions) * 3, 1.0)
        
        return complexity
    
    def analyze_approach_speed(self, target):
        """分析接近速度"""
        center_x, center_y = 320, 240  # 假设画面中心
        
        if 'current_position' not in target:
            return 0.5
        
        current_pos = target['current_position']
        velocity = target.get('velocity', (0, 0))
        
        # 计算向中心的接近速度
        to_center_vector = (center_x - current_pos[0], center_y - current_pos[1])
        to_center_magnitude = math.sqrt(to_center_vector[0]**2 + to_center_vector[1]**2)
        
        if to_center_magnitude > 0:
            direction_to_center = (
                to_center_vector[0] / to_center_magnitude,
                to_center_vector[1] / to_center_magnitude
            )
            
            # 速度在向中心方向的分量
            approach_velocity = (
                velocity[0] * direction_to_center[0] +
                velocity[1] * direction_to_center[1]
            )
            
            return min(max(approach_velocity / 5.0, 0), 1.0)
        
        return 0.5
    
    def detect_evasion_maneuvers(self, positions):
        """检测规避动作"""
        if len(positions) < 10:
            return 0.0
        
        # 分析突然的方向变化
        sudden_turns = 0
        
        for i in range(2, len(positions)-2):
            # 计算前后段的方向
            prev_vector = (positions[i][0] - positions[i-2][0], 
                          positions[i][1] - positions[i-2][1])
            next_vector = (positions[i+2][0] - positions[i][0],
                          positions[i+2][1] - positions[i][1])
            
            prev_mag = math.sqrt(prev_vector[0]**2 + prev_vector[1]**2)
            next_mag = math.sqrt(next_vector[0]**2 + next_vector[1]**2)
            
            if prev_mag > 5 and next_mag > 5:
                dot_product = prev_vector[0]*next_vector[0] + prev_vector[1]*next_vector[1]
                cos_angle = dot_product / (prev_mag * next_mag)
                angle = math.acos(max(-1, min(1, cos_angle)))
                
                if angle > math.pi/3:  # 60度以上的急转
                    sudden_turns += 1
        
        evasion_score = min(sudden_turns / (len(positions) / 5), 1.0)
        return evasion_score
    
    def optimize_system_parameters(self):
        """根据态势优化系统参数"""
        threat_level = self.system_state['threat_level']
        
        # 根据威胁级别调整检测灵敏度
        if threat_level > 0.8:
            # 高威胁模式：提高检测频率，降低置信度阈值
            self.processing_pipeline.detection_interval = 2
            self.processing_pipeline.confidence_threshold = 0.4
        elif threat_level > 0.5:
            # 中等威胁：平衡模式
            self.processing_pipeline.detection_interval = 5
            self.processing_pipeline.confidence_threshold = 0.6
        else:
            # 低威胁：节能模式
            self.processing_pipeline.detection_interval = 10
            self.processing_pipeline.confidence_threshold = 0.7
    
    def update_environment(self):
        """更新环境参数"""
        # 模拟环境变化
        self.environment['wind_speed'] += random.uniform(-0.5, 0.5)
        self.environment['wind_speed'] = max(0, min(10, self.environment['wind_speed']))
        
        self.environment['temperature'] += random.uniform(-0.1, 0.1)
        self.environment['temperature'] = max(-10, min(40, self.environment['temperature']))
    
    def log_event(self, event_type, message):
        """记录系统事件"""
        timestamp = time.time()
        event = {
            'timestamp': timestamp,
            'type': event_type,
            'message': message,
            'target_count': len(self.target_database),
            'threat_level': self.system_state['threat_level']
        }
        self.combat_log.append(event)
        
        # 控制台输出重要事件
        if event_type in ['TARGET_LOCKED', 'FIRING_SOLUTION_READY', 'HIGH_THREAT_DETECTED']:
            print(f"📢 {message}")

class YOLOProcessingPipeline:
    def __init__(self, combat_sight):
        self.combat_sight = combat_sight
        self.detection_interval = 5
        self.confidence_threshold = 0.5
        
        # 初始化相机
        self.cap = None
        self.initialize_camera()
        
        # 帧处理状态
        self.previous_frame = None
        self.frame_count = 0
        self.test_mode = False
        
        # YOLO状态
        self.yolo_ready = self.combat_sight.model is not None
    
    def initialize_camera(self):
        """初始化摄像头"""
        print("📷 正在初始化摄像头...")
        try:
            # 尝试不同的后端
            backends = [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY]
            for backend in backends:
                try:
                    self.cap = cv2.VideoCapture(0, backend)
                    if self.cap.isOpened():
                        ret, test_frame = self.cap.read()
                        if ret and test_frame is not None:
                            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                            self.cap.set(cv2.CAP_PROP_FPS, 30)
                            self.combat_sight.system_state['camera_status'] = 'active'
                            print("✅ 摄像头初始化成功")
                            return
                        else:
                            self.cap.release()
                except:
                    continue
            
            # 如果所有后端都失败
            print("❌ 无法初始化摄像头，进入测试模式")
            self.test_mode = True
            self.combat_sight.system_state['camera_status'] = 'test_mode'
            
        except Exception as e:
            print(f"❌ 摄像头初始化错误: {e}")
            self.test_mode = True
            self.combat_sight.system_state['camera_status'] = 'test_mode'
    
    def run(self):
        """主处理循环"""
        print("🎬 启动YOLO视频处理管道...")
        
        if not self.yolo_ready:
            print("❌ YOLO模型未加载，无法启动处理管道")
            return
        
        consecutive_failures = 0
        max_consecutive_failures = 10
        
        while self.combat_sight.running:
            start_time = time.time()
            
            try:
                if self.test_mode:
                    # 测试模式：生成模拟帧
                    frame = self.generate_test_frame()
                    ret = True
                else:
                    ret, frame = self.cap.read()
                    if not ret:
                        consecutive_failures += 1
                        if consecutive_failures >= max_consecutive_failures:
                            print("❌ 摄像头持续失败，切换到测试模式")
                            self.test_mode = True
                            self.combat_sight.system_state['camera_status'] = 'test_mode'
                            frame = self.generate_test_frame()
                            ret = True
                        else:
                            time.sleep(0.1)
                            continue
                    else:
                        consecutive_failures = 0
                
                if ret:
                    # YOLO目标检测
                    if self.frame_count % self.detection_interval == 0:
                        detections = self.yolo_detection(frame)
                        self.update_target_tracking(detections)
                    
                    # 连续跟踪更新
                    self.continuous_tracking_update(frame)
                    
                    # 高级目标分析
                    self.advanced_target_analysis()
                    
                    # 性能记录
                    process_time = time.time() - start_time
                    self.combat_sight.performance['processing_time'].append(process_time)
                    self.combat_sight.performance['frame_rate'].append(1.0 / process_time if process_time > 0 else 0)
                    
                    self.frame_count += 1
                
            except Exception as e:
                self.combat_sight.log_event("PROCESSING_ERROR", f"处理错误: {str(e)}")
                time.sleep(0.1)
        
        if self.cap:
            self.cap.release()
    
    def generate_test_frame(self):
        """生成测试帧"""
        frame = np.random.randint(0, 50, (480, 640, 3), dtype=np.uint8)
        
        # 添加一些模拟目标
        for i in range(random.randint(0, 3)):
            x = random.randint(50, 590)
            y = random.randint(50, 430)
            w = random.randint(30, 100)
            h = random.randint(30, 100)
            color = (random.randint(100, 255), random.randint(100, 255), random.randint(100, 255))
            cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
        
        noise = np.random.randint(0, 30, (480, 640, 3), dtype=np.uint8)
        frame = cv2.add(frame, noise)
        
        return frame
    
    def yolo_detection(self, frame):
        """YOLO目标检测"""
        detections = []
        
        try:
            # 使用YOLO进行推理
            results = self.combat_sight.model(frame, conf=self.confidence_threshold, verbose=False)
            
            for result in results:
                boxes = result.boxes
                if boxes is not None:
                    for box in boxes:
                        # 获取边界框坐标
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                        confidence = box.conf[0].cpu().numpy()
                        class_id = int(box.cls[0].cpu().numpy())
                        class_name = self.combat_sight.model.names[class_id]
                        
                        # 转换为战斗类别
                        combat_class = self.combat_sight.class_mapping.get(class_name, 'unknown')
                        
                        # 计算中心点
                        centroid = ((x1 + x2) / 2, (y1 + y2) / 2)
                        
                        # 估计距离（基于目标大小）
                        width = x2 - x1
                        height = y2 - y1
                        area = width * height
                        estimated_distance = self.estimate_distance(combat_class, area)
                        
                        detection = {
                            'bbox': (int(x1), int(y1), int(x2), int(y2)),
                            'confidence': float(confidence),
                            'type': combat_class,
                            'centroid': (int(centroid[0]), int(centroid[1])),
                            'class_name': class_name,
                            'estimated_distance': estimated_distance
                        }
                        detections.append(detection)
            
            self.combat_sight.system_state['yolo_status'] = 'active'
            
        except Exception as e:
            print(f"YOLO检测错误: {e}")
            self.combat_sight.system_state['yolo_status'] = 'error'
        
        return detections
    
    def estimate_distance(self, target_type, area):
        """基于目标大小估计距离"""
        # 基础距离估计模型
        base_sizes = {
            'infantry': 10000,  # 人体在10米处的大概像素面积
            'vehicle': 50000,   # 车辆在10米处的大概像素面积
            'aircraft': 100000, # 飞机在10米处的大概像素面积
            'unknown': 20000    # 未知目标
        }
        
        base_area = base_sizes.get(target_type, 20000)
        distance = max(5, math.sqrt(base_area / (area + 1e-5)) * 10)
        
        return min(distance, 1000)  # 限制最大距离
    
    def update_target_tracking(self, detections):
        """更新目标跟踪"""
        current_time = time.time()
        
        # 数据关联
        matched_detections = set()
        
        # 更新现有目标
        for target_id, target in list(self.combat_sight.target_database.items()):
            # 检查目标超时
            if current_time - target['last_update'] > 5.0:
                del self.combat_sight.target_database[target_id]
                continue
            
            best_match = None
            best_score = 0
            
            for i, detection in enumerate(detections):
                if i in matched_detections:
                    continue
                
                match_score = self.calculate_tracking_score(target, detection)
                
                if match_score > best_score and match_score > 0.4:
                    best_score = match_score
                    best_match = (i, detection)
            
            if best_match:
                i, detection = best_match
                self.update_target_state(target_id, detection)
                matched_detections.add(i)
            else:
                # 预测目标状态
                self.predict_target_state(target_id)
        
        # 创建新目标
        for i, detection in enumerate(detections):
            if i not in matched_detections:
                self.create_new_target(detection)
    
    def calculate_tracking_score(self, target, detection):
        """计算跟踪匹配分数"""
        # 位置相似性
        target_pos = np.array(target['current_position'])
        detection_pos = np.array(detection['centroid'])
        pos_distance = np.linalg.norm(target_pos - detection_pos)
        pos_score = max(0, 1 - pos_distance / 200.0)
        
        # 类型相似性
        type_score = 1.0 if target['type'] == detection['type'] else 0.3
        
        # 大小相似性
        target_bbox = target['bbox']
        detection_bbox = detection['bbox']
        target_size = (target_bbox[2] - target_bbox[0]) * (target_bbox[3] - target_bbox[1])
        detection_size = (detection_bbox[2] - detection_bbox[0]) * (detection_bbox[3] - detection_bbox[1])
        size_ratio = min(target_size, detection_size) / max(target_size, detection_size)
        
        return pos_score * 0.6 + type_score * 0.2 + size_ratio * 0.2
    
    def create_new_target(self, detection):
        """创建新目标"""
        target_id = self.combat_sight.target_counter
        self.combat_sight.target_counter += 1
        
        centroid = detection['centroid']
        bbox = detection['bbox']
        
        # 基础威胁级别
        base_threat = self.combat_sight.threat_config.get(detection['type'], 0.5)
        
        target = {
            'id': target_id,
            'current_position': centroid,
            'bbox': bbox,
            'position_history': deque([centroid], maxlen=50),
            'velocity': (0, 0),
            'acceleration': (0, 0),
            'confidence': detection['confidence'],
            'threat_level': base_threat,
            'type': detection['type'],
            'class_name': detection.get('class_name', 'unknown'),
            'creation_time': time.time(),
            'last_update': time.time(),
            'tracking_quality': 1.0,
            'engagement_priority': 0.5
        }
        
        # 继承检测属性
        if 'estimated_distance' in detection:
            target['estimated_distance'] = detection['estimated_distance']
        
        self.combat_sight.target_database[target_id] = target
        self.combat_sight.trajectory_archive[target_id].append(centroid)
        
        self.combat_sight.log_event("TARGET_ACQUIRED", f"目标 {target_id} ({target['class_name']}) 已获取")
    
    def update_target_state(self, target_id, detection):
        """更新目标状态"""
        target = self.combat_sight.target_database[target_id]
        new_position = detection['centroid']
        old_position = target['current_position']
        
        # 更新位置历史
        target['position_history'].append(new_position)
        target['current_position'] = new_position
        target['bbox'] = detection['bbox']
        target['confidence'] = detection['confidence']
        target['last_update'] = time.time()
        
        # 更新类型（如果检测到更具体的类型）
        if detection['type'] != 'unknown':
            target['type'] = detection['type']
            target['class_name'] = detection.get('class_name', target['class_name'])
        
        # 更新速度和加速度
        if len(target['position_history']) >= 2:
            prev_pos = target['position_history'][-2]
            dt = 1/30.0
            
            new_velocity = (
                (new_position[0] - prev_pos[0]) / dt,
                (new_position[1] - prev_pos[1]) / dt
            )
            
            # 平滑速度更新
            target['velocity'] = (
                0.7 * target['velocity'][0] + 0.3 * new_velocity[0],
                0.7 * target['velocity'][1] + 0.3 * new_velocity[1]
            )
            
            # 更新加速度
            if len(target['position_history']) >= 3:
                prev_prev_pos = target['position_history'][-3]
                prev_velocity = (
                    (prev_pos[0] - prev_prev_pos[0]) / dt,
                    (prev_pos[1] - prev_prev_pos[1]) / dt
                )
                
                acceleration = (
                    (new_velocity[0] - prev_velocity[0]) / dt,
                    (new_velocity[1] - prev_velocity[1]) / dt
                )
                
                target['acceleration'] = acceleration
        
        # 更新跟踪质量
        target['tracking_quality'] = min(1.0, target['tracking_quality'] + 0.05)
        
        # 更新轨迹存档
        self.combat_sight.trajectory_archive[target_id].append(new_position)
    
    def predict_target_state(self, target_id):
        """预测目标状态"""
        target = self.combat_sight.target_database[target_id]
        
        # 简单线性预测
        current_pos = target['current_position']
        velocity = target['velocity']
        
        predicted_pos = (
            current_pos[0] + velocity[0] * 0.1,  # 预测0.1秒后
            current_pos[1] + velocity[1] * 0.1
        )
        
        target['predicted_position'] = predicted_pos
        target['tracking_quality'] *= 0.98  # 缓慢降低质量
    
    def continuous_tracking_update(self, frame):
        """连续跟踪更新"""
        # 使用光流进行连续跟踪
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        if self.previous_frame is not None:
            for target_id, target in self.combat_sight.target_database.items():
                if target['tracking_quality'] < 0.3:
                    continue
                
                try:
                    # 准备跟踪点
                    track_points = np.array([target['current_position']], dtype=np.float32).reshape(-1, 1, 2)
                    
                    # 计算光流
                    new_points, status, error = cv2.calcOpticalFlowPyrLK(
                        self.previous_frame, gray, track_points, None,
                        winSize=(15, 15), maxLevel=2,
                        criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 10, 0.03)
                    )
                    
                    if status[0][0]:
                        new_position = tuple(new_points[0][0])
                        target['current_position'] = new_position
                        target['position_history'].append(new_position)
                        self.combat_sight.trajectory_archive[target_id].append(new_position)
                except Exception as e:
                    print(f"光流跟踪错误: {e}")
        
        self.previous_frame = gray.copy()
    
    def advanced_target_analysis(self):
        """高级目标分析"""
        for target_id, target in self.combat_sight.target_database.items():
            # 更新威胁评估
            threat_level = self.combat_sight.calculate_comprehensive_threat(target)
            target['threat_level'] = threat_level
            
            # 更新交战优先级
            target['engagement_priority'] = self.calculate_engagement_priority(target)
            
            # 计算射击解决方案
            if threat_level > 0.7:
                firing_solution = self.calculate_firing_solution(target)
                target['firing_solution'] = firing_solution
    
    def calculate_engagement_priority(self, target):
        """计算交战优先级"""
        # 基于威胁级别、距离、跟踪质量
        threat = target['threat_level']
        distance = target.get('estimated_distance', 100)
        tracking_quality = target['tracking_quality']
        
        # 距离因子 (越近优先级越高)
        distance_factor = max(0, 1 - distance / 300.0)
        
        # 跟踪质量因子
        quality_factor = tracking_quality
        
        # 目标类型因子
        type_factors = {
            'infantry': 1.0,
            'vehicle': 0.8,
            'aircraft': 0.9,
            'unknown': 0.6
        }
        type_factor = type_factors.get(target['type'], 0.7)
        
        priority = (
            threat * 0.4 +
            distance_factor * 0.3 +
            quality_factor * 0.2 +
            type_factor * 0.1
        )
        
        return min(priority, 1.0)
    
    def calculate_firing_solution(self, target):
        """计算射击解决方案"""
        target_pos = target['current_position']
        velocity = target['velocity']
        distance = target.get('estimated_distance', 100)
        
        # 弹道下坠
        time_of_flight = distance / self.combat_sight.ballistics['muzzle_velocity']
        bullet_drop = 0.5 * self.combat_sight.environment['gravity'] * time_of_flight ** 2
        
        # 提前量
        lead_x = velocity[0] * time_of_flight
        lead_y = velocity[1] * time_of_flight
        
        # 风偏
        wind_deflection = self.calculate_wind_deflection(distance, time_of_flight)
        
        # 转换为像素偏移
        pixel_scale = 640 / (2 * distance * math.tan(math.radians(30)))  # 假设30度视场角
        
        adjusted_aimpoint = (
            int(target_pos[0] + lead_x * pixel_scale + wind_deflection * pixel_scale),
            int(target_pos[1] + lead_y * pixel_scale + bullet_drop * pixel_scale)
        )
        
        return {
            'aimpoint': adjusted_aimpoint,
            'estimated_range': distance,
            'time_of_flight': time_of_flight,
            'bullet_drop': bullet_drop,
            'wind_correction': wind_deflection,
            'lead_correction': (lead_x, lead_y)
        }
    
    def calculate_wind_deflection(self, distance, time_of_flight):
        """计算风偏"""
        wind_speed = self.combat_sight.environment['wind_speed']
        crosswind = wind_speed * math.sin(math.radians(self.combat_sight.environment['wind_direction']))
        
        # 简化风偏模型
        wind_deflection = crosswind * time_of_flight * 0.5
        
        return wind_deflection

# 辅助算法类
class TrajectoryPredictor:
    def predict(self, positions):
        # 轨迹预测
        pass

class ThreatAssessmentEngine:
    def assess(self, target):
        # 威胁评估
        pass

class BallisticSolver:
    def solve(self, target, environment):
        # 弹道解算
        pass

class CombatDisplay:
    def __init__(self, combat_sight):
        self.combat_sight = combat_sight
        self.display_mode = 'tactical'
        self.overlay_elements = {}
    
    def render(self, frame):
        """渲染战斗显示"""
        display_frame = frame.copy()
        
        # 绘制战术界面
        self.draw_tactical_overlay(display_frame)
        
        # 绘制目标信息
        self.draw_targets(display_frame)
        
        # 绘制系统状态
        self.draw_system_status(display_frame)
        
        # 绘制威胁警报
        if self.combat_sight.system_state['threat_level'] > 0.7:
            self.draw_threat_alert(display_frame)
        
        return display_frame
    
    def draw_tactical_overlay(self, frame):
        """绘制战术叠加层"""
        height, width = frame.shape[:2]
        center_x, center_y = width // 2, height // 2
        
        # 瞄准镜分划
        self.draw_reticule(frame, center_x, center_y)
        
        # 距离刻度
        self.draw_range_scale(frame, width, height)
        
        # 方位指示
        self.draw_compass(frame, width, height)
    
    def draw_reticule(self, frame, center_x, center_y):
        """绘制瞄准分划"""
        # 主十字线
        cv2.line(frame, (center_x - 50, center_y), (center_x + 50, center_y), (0, 255, 0), 2)
        cv2.line(frame, (center_x, center_y - 50), (center_x, center_y + 50), (0, 255, 0), 2)
        
        # 精细刻度
        for i in range(-40, 41, 10):
            if i == 0:
                continue
            length = 6 if abs(i) % 20 == 0 else 3
            cv2.line(frame, (center_x + i, center_y - length), 
                    (center_x + i, center_y + length), (0, 255, 0), 1)
            cv2.line(frame, (center_x - length, center_y + i), 
                    (center_x + length, center_y + i), (0, 255, 0), 1)
        
        # 外圈
        cv2.circle(frame, (center_x, center_y), 80, (0, 255, 0), 2)
        
        # 中心点
        cv2.circle(frame, (center_x, center_y), 3, (0, 255, 0), -1)
    
    def draw_range_scale(self, frame, width, height):
        """绘制距离刻度"""
        # 在右侧绘制垂直距离刻度
        scale_width = 20
        scale_x = width - 30
        
        cv2.line(frame, (scale_x, 50), (scale_x, height-50), (0, 255, 0), 2)
        
        # 距离标记 (假设每100米一个标记)
        for i in range(0, 6):
            y_pos = 50 + i * 80
            range_value = 500 - i * 100
            cv2.line(frame, (scale_x-10, y_pos), (scale_x+10, y_pos), (0, 255, 0), 1)
            cv2.putText(frame, f"{range_value}", (scale_x-40, y_pos+5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
    
    def draw_compass(self, frame, width, height):
        """绘制方位指示"""
        compass_radius = 30
        compass_x, compass_y = 40, 40
        
        # 罗盘圈
        cv2.circle(frame, (compass_x, compass_y), compass_radius, (0, 255, 0), 2)
        
        # 方向标记
        directions = ['N', 'E', 'S', 'W']
        for i, dir in enumerate(directions):
            angle = i * 90
            rad = math.radians(angle)
            x = int(compass_x + (compass_radius-5) * math.sin(rad))
            y = int(compass_y - (compass_radius-5) * math.cos(rad))
            cv2.putText(frame, dir, (x-5, y+5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
    
    def draw_targets(self, frame):
        """绘制目标信息"""
        for target_id, target in self.combat_sight.target_database.items():
            self.draw_single_target(frame, target)
    
    def draw_single_target(self, frame, target):
        """绘制单个目标"""
        pos = target['current_position']
        x, y = int(pos[0]), int(pos[1])
        bbox = target['bbox']
        
        # 确保边界框坐标是整数
        x1, y1, x2, y2 = map(int, bbox)
        
        # 根据威胁级别选择颜色
        color = self.get_threat_color(target['threat_level'])
        
        # 绘制边界框
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        
        # 绘制目标ID和信息
        info_text = f"T{target['id']} {target['class_name']}"
        cv2.putText(frame, info_text, (x1, y1-10), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        
        # 威胁级别条
        threat_width = int(target['threat_level'] * 40)
        cv2.rectangle(frame, (x-20, y-25), (x-20+threat_width, y-22), color, -1)
        
        # 绘制轨迹
        history = list(self.combat_sight.trajectory_archive[target['id']])
        if len(history) > 1:
            points = np.array(history, dtype=np.int32)
            cv2.polylines(frame, [points], False, color, 1)
        
        # 绘制预测轨迹
        if 'predicted_position' in target:
            pred_pos = target['predicted_position']
            pred_x, pred_y = int(pred_pos[0]), int(pred_pos[1])
            cv2.circle(frame, (pred_x, pred_y), 4, (0, 0, 255), -1)
            cv2.line(frame, (x, y), (pred_x, pred_y), (0, 0, 255), 1)
        
        # 如果是高优先级目标，绘制特殊标记
        if target['engagement_priority'] > 0.8:
            cv2.drawMarker(frame, (x, y), (0, 0, 255), cv2.MARKER_STAR, 20, 2)
        
        # 绘制射击解决方案
        if target.get('firing_solution'):
            aimpoint = target['firing_solution']['aimpoint']
            # 确保瞄准点是整数
            aimpoint = (int(aimpoint[0]), int(aimpoint[1]))
            cv2.circle(frame, aimpoint, 6, (0, 0, 255), 2)
            cv2.line(frame, (x, y), aimpoint, (0, 0, 255), 2)
            
            # 显示弹道信息
            solution = target['firing_solution']
            range_text = f"{solution['estimated_range']:.0f}m"
            cv2.putText(frame, range_text, (x+10, y+10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)
    
    def get_threat_color(self, threat_level):
        """根据威胁级别获取颜色"""
        if threat_level > 0.8:
            return (0, 0, 255)    # 红色 - 致命威胁
        elif threat_level > 0.6:
            return (0, 165, 255)  # 橙色 - 高威胁
        elif threat_level > 0.4:
            return (0, 255, 255)  # 黄色 - 中威胁
        else:
            return (0, 255, 0)    # 绿色 - 低威胁
    
    def draw_system_status(self, frame):
        """绘制系统状态"""
        height, width = frame.shape[:2]
        state = self.combat_sight.system_state
        
        # 系统状态栏
        status_bg = np.zeros((60, width, 3), dtype=np.uint8)
        frame[0:60, 0:width] = status_bg
        
        # 战斗模式
        mode_text = f"MODE: {self.combat_sight.current_mode.upper()}"
        cv2.putText(frame, mode_text, (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        # 目标数量
        targets_text = f"TARGETS: {len(self.combat_sight.target_database)}"
        cv2.putText(frame, targets_text, (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        # 威胁级别
        threat_color = self.get_threat_color(state['threat_level'])
        threat_text = f"THREAT: {state['threat_level']:.2f}"
        cv2.putText(frame, threat_text, (width-150, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, threat_color, 2)
        
        # 弹药状态
        ammo_text = f"AMMO: {state['ammunition_count']}"
        cv2.putText(frame, ammo_text, (width-150, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        # 系统健康度
        health_color = (0, 255, 0) if state['system_health'] > 70 else (0, 165, 255) if state['system_health'] > 30 else (0, 0, 255)
        health_text = f"HEALTH: {state['system_health']:.0f}%"
        cv2.putText(frame, health_text, (width-300, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, health_color, 2)
        
        # 摄像头状态
        camera_status = state.get('camera_status', 'unknown')
        camera_color = (0, 255, 0) if camera_status == 'active' else (0, 165, 255) if camera_status == 'test_mode' else (0, 0, 255)
        camera_text = f"CAMERA: {camera_status.upper()}"
        cv2.putText(frame, camera_text, (width-450, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, camera_color, 2)
        
        # YOLO状态
        yolo_status = state.get('yolo_status', 'unknown')
        yolo_color = (0, 255, 0) if yolo_status == 'active' else (0, 0, 255)
        yolo_text = f"YOLO: {yolo_status.upper()}"
        cv2.putText(frame, yolo_text, (width-450, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.6, yolo_color, 2)
        
        # 帧率
        if self.combat_sight.performance['frame_rate']:
            fps = np.mean(list(self.combat_sight.performance['frame_rate'])[-10:])
            fps_text = f"FPS: {fps:.1f}"
            cv2.putText(frame, fps_text, (width-600, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        # 战术态势显示
        if 'tactical_situation' in state:
            tactical = state['tactical_situation']
            if tactical.get('formation_detected'):
                cv2.putText(frame, "FORMATION DETECTED", (width//2-100, 20), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
            if tactical.get('encirclement_risk', 0) > 0.7:
                cv2.putText(frame, "ENCIRCLEMENT RISK", (width//2-100, 40), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
    
    def draw_threat_alert(self, frame):
        """绘制威胁警报"""
        height, width = frame.shape[:2]
        
        # 闪烁的红色边框
        alert_alpha = 0.3 + 0.2 * math.sin(time.time() * 8)  # 8Hz闪烁
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (width, height), (0, 0, 255), 20)
        cv2.addWeighted(overlay, alert_alpha, frame, 1 - alert_alpha, 0, frame)
        
        # 警报文本
        alert_text = "HIGH THREAT LEVEL!"
        text_size = cv2.getTextSize(alert_text, cv2.FONT_HERSHEY_SIMPLEX, 1, 2)[0]
        text_x = (width - text_size[0]) // 2
        cv2.putText(frame, alert_text, (text_x, 80), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

def main():
    """主函数"""
    print("🚀 启动YOLO战斗瞄准系统")
    print("=" * 50)
    
    # 创建战斗瞄准系统
    combat_system = YOLOCombatSight('yolov8n.pt')  # 可以使用 yolov8s.pt, yolov8m.pt 等
    
    # 创建显示系统
    display_system = CombatDisplay(combat_system)
    
    # 创建测试视频捕获
    try:
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if cap.isOpened():
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            print("🎥 摄像头初始化完成")
        else:
            print("⚠️ 摄像头无法打开，使用测试模式")
            cap = None
    except Exception as e:
        print(f"⚠️ 摄像头初始化失败: {e}")
        cap = None
    
    print("🎯 系统就绪，开始处理...")
    print("按 'q' 退出系统")
    print("按 'r' 重置目标跟踪")
    print("按 'm' 切换战斗模式")
    print("按 's' 切换安全开关")
    print("按 'c' 重新初始化摄像头")
    print("按 '1' 切换YOLO检测置信度阈值")
    
    confidence_levels = [0.3, 0.5, 0.7]
    current_confidence = 1  # 索引
    
    try:
        while combat_system.running:
            if cap:
                ret, frame = cap.read()
                if not ret:
                    print("⚠️ 摄像头读取失败，使用测试帧")
                    frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
            else:
                # 创建测试帧
                frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
            
            # 渲染显示
            display_frame = display_system.render(frame)
            
            # 显示帧
            cv2.imshow('YOLO Combat Sight System', display_frame)
            
            # 键盘控制
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('r'):
                combat_system.target_database.clear()
                combat_system.trajectory_archive.clear()
                print("🔄 目标跟踪已重置")
            elif key == ord('m'):
                # 切换战斗模式
                modes = list(combat_system.combat_modes.keys())
                current_index = modes.index(combat_system.current_mode)
                combat_system.current_mode = modes[(current_index + 1) % len(modes)]
                print(f"🎛️  战斗模式切换至: {combat_system.current_mode.upper()}")
            elif key == ord('s'):
                combat_system.weapon_state['safety_off'] = not combat_system.weapon_state['safety_off']
                status = "解除" if combat_system.weapon_state['safety_off'] else "启用"
                print(f"🔒 安全开关: {status}")
            elif key == ord('c'):
                # 重新初始化摄像头
                if cap:
                    cap.release()
                try:
                    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
                    if cap.isOpened():
                        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                        print("🔄 摄像头重新初始化成功")
                        combat_system.system_state['camera_status'] = 'active'
                    else:
                        print("❌ 摄像头重新初始化失败")
                        cap = None
                except Exception as e:
                    print(f"❌ 摄像头重新初始化错误: {e}")
                    cap = None
            elif key == ord('1'):
                # 切换YOLO置信度阈值
                current_confidence = (current_confidence + 1) % len(confidence_levels)
                combat_system.processing_pipeline.confidence_threshold = confidence_levels[current_confidence]
                print(f"🎚️  YOLO置信度阈值: {confidence_levels[current_confidence]}")
            
            # 添加小延迟以控制CPU使用率
            time.sleep(0.01)
            
    except KeyboardInterrupt:
        print("\n⚠️  用户中断系统")
    except Exception as e:
        print(f"❌ 系统错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 清理资源
        combat_system.running = False
        if cap:
            cap.release()
        cv2.destroyAllWindows()
        print("✅ 系统已安全关闭")

if __name__ == "__main__":
    main()