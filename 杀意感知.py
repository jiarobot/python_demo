import cv2
import numpy as np
import torch
from ultralytics import YOLO
import mediapipe as mp
from scipy import stats
import time
import pygame
import threading
from collections import deque
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import warnings
warnings.filterwarnings('ignore')

class AdvancedKillingIntentPerceptionSystem:
    def __init__(self):
        # 初始化YOLO模型 - 使用更精确的模型
        try:
            self.yolo_model = YOLO('yolov8n.pt')  # 使用更大的模型提高精度
        except:
            self.yolo_model = YOLO('yolov8n.pt')  # 备用模型
        
        # 初始化MediaPipe
        self.mp_face_detection = mp.solutions.face_detection
        self.mp_pose = mp.solutions.pose
        self.mp_hands = mp.solutions.hands
        self.mp_face_mesh = mp.solutions.face_mesh
        
        self.face_detection = self.mp_face_detection.FaceDetection(model_selection=1, min_detection_confidence=0.7)
        self.pose = self.mp_pose.Pose(static_image_mode=False, min_detection_confidence=0.7, min_tracking_confidence=0.7)
        self.hands = self.mp_hands.Hands(static_image_mode=False, max_num_hands=4, min_detection_confidence=0.6)
        self.face_mesh = self.mp_face_mesh.FaceMesh(static_image_mode=False, max_num_faces=3, min_detection_confidence=0.7)
        
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles
        
        # 系统参数
        self.threat_level = 0.0
        self.combined_threat = 0.0
        self.intensity_history = deque(maxlen=30)
        self.threat_history = deque(maxlen=100)
        self.facial_threat_history = deque(maxlen=20)
        self.behavior_threat_history = deque(maxlen=20)
        
        # 音频系统初始化
        try:
            pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
            self.warning_sound = self.generate_warning_sound()
        except:
            print("音频初始化失败，继续无音频模式")
            self.warning_sound = None
        
        # 视觉参数
        self.alpha = 0.4
        self.thermal_lut = self.create_advanced_thermal_lut()
        
        # 威胁检测参数
        self.eye_contact_threshold = 0.65
        self.movement_threshold = 12
        self.weapon_confidence = 0.5
        
        # 高级功能参数
        self.person_tracker = {}  # 人物跟踪器
        self.threat_persons = set()  # 威胁人物ID
        self.frame_count = 0
        
        # 机器学习增强
        self.threat_patterns = self.initialize_threat_patterns()
        
        print("燕双鹰高级杀意感知系统已启动...")
        print("系统特性: 多模态融合分析、实时威胁追踪、行为模式识别")
    
    def create_advanced_thermal_lut(self):
        """创建高级热力图颜色查找表"""
        lut = np.zeros((256, 1, 3), dtype=np.uint8)
        for i in range(256):
            # 更精细的热力颜色映射
            if i < 64:
                # 深蓝到浅蓝
                r = 0
                g = int(i * 2)
                b = 200 + int(i * 0.8)
            elif i < 128:
                # 蓝到青
                r = 0
                g = 128 + int((i-64) * 1.5)
                b = 255 - int((i-64) * 0.5)
            elif i < 192:
                # 青到黄
                r = int((i-128) * 2)
                g = 255
                b = 128 - int((i-128) * 1.5)
            else:
                # 黄到红
                r = 255
                g = 255 - int((i-192) * 2)
                b = 0
            lut[i, 0] = [b, g, r]
        return lut
    
    def generate_warning_sound(self):
        """生成高级警告音效"""
        try:
            # 创建更复杂的警告音
            sample_rate = 44100
            duration = 2.0
            t = np.linspace(0, duration, int(sample_rate * duration))
            
            # 多频率合成
            base_freq = 400
            harmonic1 = 0.3 * np.sin(2 * np.pi * base_freq * t)
            harmonic2 = 0.25 * np.sin(2 * np.pi * base_freq * 1.5 * t)
            harmonic3 = 0.2 * np.sin(2 * np.pi * base_freq * 2 * t)
            noise = 0.05 * np.random.normal(0, 1, len(t))
            
            signal = harmonic1 + harmonic2 + harmonic3 + noise
            
            # 动态包络
            attack = np.linspace(0, 1, int(0.1 * sample_rate))
            decay = np.linspace(1, 0.7, int(0.3 * sample_rate))
            release = np.linspace(0.7, 0, int(0.6 * sample_rate))
            sustain = np.ones(len(t) - len(attack) - len(decay) - len(release)) * 0.7
            
            envelope = np.concatenate([attack, decay, sustain, release])
            if len(envelope) > len(signal):
                envelope = envelope[:len(signal)]
            else:
                envelope = np.pad(envelope, (0, len(signal) - len(envelope)), 'constant')
            
            signal = signal * envelope
            
            # 转换为立体声
            signal_stereo = np.zeros((len(signal), 2))
            signal_stereo[:, 0] = signal  # 左声道
            signal_stereo[:, 1] = signal  # 右声道
            
            # 转换为16位整数
            signal_stereo = (signal_stereo * 32767).astype(np.int16)
            
            # 创建pygame声音对象
            return pygame.sndarray.make_sound(signal_stereo)
        except Exception as e:
            print(f"音频生成失败: {e}")
            return None
    
    def initialize_threat_patterns(self):
        """初始化威胁模式数据库"""
        patterns = {
            'aggressive_gestures': ['clenched_fist', 'pointing', 'rapid_movement'],
            'suspicious_objects': ['phone', 'briefcase', 'backpack', 'package'],
            'abnormal_behavior': ['loitering', 'rapid_approach', 'evasive_movement'],
            'facial_expressions': ['anger', 'fear', 'tension']
        }
        return patterns
    
    def detect_advanced_facial_analysis(self, face_region, face_landmarks):
        """高级面部情绪和微表情分析"""
        if face_region is None or face_region.size == 0:
            return 0.0, "neutral"
        
        threat_score = 0.0
        emotion = "neutral"
        
        try:
            # 使用多种特征进行情绪分析
            gray_face = cv2.cvtColor(face_region, cv2.COLOR_BGR2GRAY)
            
            # 1. LBP纹理分析
            lbp = self.advanced_local_binary_pattern(gray_face)
            hist = self.compute_lbp_histogram(lbp)
            texture_complexity = -np.sum([p * np.log2(p) for p in hist if p > 0])
            
            # 2. 边缘密度分析 (紧张面部通常有更多边缘)
            edges = cv2.Canny(gray_face, 50, 150)
            edge_density = np.sum(edges > 0) / (face_region.shape[0] * face_region.shape[1])
            
            # 3. 基于面部关键点的情绪估计
            if face_landmarks:
                emotion, landmark_score = self.analyze_facial_landmarks(face_landmarks)
                threat_score += landmark_score * 0.4
            
            # 综合评分
            texture_threat = min(texture_complexity / 4.0, 1.0) * 0.3
            edge_threat = min(edge_density * 10, 1.0) * 0.3
            
            threat_score += texture_threat + edge_threat
            
        except Exception as e:
            print(f"面部分析错误: {e}")
        
        return min(threat_score, 1.0), emotion
    
    def advanced_local_binary_pattern(self, image, P=16, R=2):
        """高级LBP实现"""
        height, width = image.shape
        lbp_image = np.zeros((height-2*R, width-2*R), dtype=np.uint8)
        
        for i in range(R, height-R):
            for j in range(R, width-R):
                center = image[i, j]
                binary_values = []
                
                # 圆形邻域采样
                for p in range(P):
                    theta = 2 * np.pi * p / P
                    x = i + R * np.cos(theta)
                    y = j + R * np.sin(theta)
                    
                    # 双线性插值
                    x1, y1 = int(np.floor(x)), int(np.floor(y))
                    x2, y2 = int(np.ceil(x)), int(np.ceil(y))
                    
                    if x1 == x2 and y1 == y2:
                        value = image[x1, y1]
                    else:
                        value = (image[x1, y1] * (x2-x) * (y2-y) +
                                image[x1, y2] * (x2-x) * (y-y1) +
                                image[x2, y1] * (x-x1) * (y2-y) +
                                image[x2, y2] * (x-x1) * (y-y1))
                    
                    binary_values.append(1 if value >= center else 0)
                
                # 转换为均匀模式
                transitions = 0
                for k in range(P):
                    if binary_values[k] != binary_values[(k+1) % P]:
                        transitions += 1
                
                if transitions <= 2:
                    # 计算LBP值
                    lbp_value = 0
                    for k, bit in enumerate(binary_values):
                        lbp_value += bit * (2 ** k)
                    lbp_image[i-R, j-R] = lbp_value % 256
                else:
                    lbp_image[i-R, j-R] = P + 1
        
        return lbp_image
    
    def compute_lbp_histogram(self, lbp_image):
        """计算LBP直方图"""
        n_bins = int(lbp_image.max() + 1)
        hist, _ = np.histogram(lbp_image.ravel(), bins=n_bins, range=(0, n_bins))
        hist = hist.astype("float")
        hist /= (hist.sum() + 1e-7)
        return hist
    
    def analyze_facial_landmarks(self, face_landmarks):
        """基于面部关键点分析情绪"""
        landmarks = face_landmarks.landmark
        
        # 提取关键点坐标
        left_eye = np.array([landmarks[33].x, landmarks[33].y])
        right_eye = np.array([landmarks[263].x, landmarks[263].y])
        mouth_left = np.array([landmarks[61].x, landmarks[61].y])
        mouth_right = np.array([landmarks[291].x, landmarks[291].y])
        mouth_center = np.array([landmarks[13].x, landmarks[13].y])
        
        # 计算特征
        eye_distance = np.linalg.norm(left_eye - right_eye)
        mouth_width = np.linalg.norm(mouth_left - mouth_right)
        mouth_openness = landmarks[13].y - landmarks[14].y
        
        # 情绪判断
        threat_score = 0.0
        emotion = "neutral"
        
        if mouth_width < eye_distance * 0.8:  # 嘴唇紧闭
            threat_score += 0.3
            emotion = "tense"
        if mouth_openness > 0.03:  # 嘴巴张开较大
            threat_score += 0.2
            emotion = "surprised"
        if abs(landmarks[159].y - landmarks[145].y) < 0.01:  # 眉毛紧张
            threat_score += 0.2
            emotion = "angry"
        
        return emotion, min(threat_score, 1.0)
    
    def analyze_advanced_body_language(self, pose_landmarks, hand_landmarks_list, frame_shape):
        """高级身体语言分析"""
        threat_score = 0.0
        behavior_analysis = []
        
        if pose_landmarks:
            landmarks = pose_landmarks.landmark
            
            # 姿态紧张度分析
            shoulder_tension = self.analyze_shoulder_tension(landmarks, frame_shape)
            threat_score += shoulder_tension * 0.3
            
            # 平衡和稳定性分析
            balance_score = self.analyze_balance(landmarks, frame_shape)
            threat_score += (1 - balance_score) * 0.2  # 不平衡可能表示攻击准备
            
            # 手部位置威胁分析
            hand_threat = self.analyze_hand_positions(landmarks, hand_landmarks_list, frame_shape)
            threat_score += hand_threat * 0.3
            
            # 运动准备分析
            movement_preparation = self.analyze_movement_preparation(landmarks, frame_shape)
            threat_score += movement_preparation * 0.2
            
            behavior_analysis.extend([
                f"肩部紧张度: {shoulder_tension:.2f}",
                f"平衡度: {balance_score:.2f}",
                f"手部威胁: {hand_threat:.2f}",
                f"运动准备: {movement_preparation:.2f}"
            ])
        
        return min(threat_score, 1.0), behavior_analysis
    
    def analyze_shoulder_tension(self, landmarks, frame_shape):
        """分析肩部紧张度"""
        left_shoulder = np.array([landmarks[self.mp_pose.PoseLandmark.LEFT_SHOULDER].x * frame_shape[1],
                                 landmarks[self.mp_pose.PoseLandmark.LEFT_SHOULDER].y * frame_shape[0]])
        right_shoulder = np.array([landmarks[self.mp_pose.PoseLandmark.RIGHT_SHOULDER].x * frame_shape[1],
                                  landmarks[self.mp_pose.PoseLandmark.RIGHT_SHOULDER].y * frame_shape[0]])
        
        shoulder_width = np.linalg.norm(left_shoulder - right_shoulder)
        shoulder_height_diff = abs(left_shoulder[1] - right_shoulder[1])
        
        # 紧张度计算
        width_tension = max(0, (shoulder_width - 150) / 100)  # 假设正常肩宽150像素
        height_tension = min(shoulder_height_diff / 20, 1.0)  # 高度差异
        
        return min((width_tension + height_tension) / 2, 1.0)
    
    def analyze_balance(self, landmarks, frame_shape):
        """分析身体平衡度"""
        left_hip = np.array([landmarks[self.mp_pose.PoseLandmark.LEFT_HIP].x * frame_shape[1],
                            landmarks[self.mp_pose.PoseLandmark.LEFT_HIP].y * frame_shape[0]])
        right_hip = np.array([landmarks[self.mp_pose.PoseLandmark.RIGHT_HIP].x * frame_shape[1],
                             landmarks[self.mp_pose.PoseLandmark.RIGHT_HIP].y * frame_shape[0]])
        left_ankle = np.array([landmarks[self.mp_pose.PoseLandmark.LEFT_ANKLE].x * frame_shape[1],
                              landmarks[self.mp_pose.PoseLandmark.LEFT_ANKLE].y * frame_shape[0]])
        right_ankle = np.array([landmarks[self.mp_pose.PoseLandmark.RIGHT_ANKLE].x * frame_shape[1],
                               landmarks[self.mp_pose.PoseLandmark.RIGHT_ANKLE].y * frame_shape[0]])
        
        # 计算重心
        center_of_mass = (left_hip + right_hip + left_ankle + right_ankle) / 4
        support_base_center = (left_ankle + right_ankle) / 2
        
        # 平衡度计算
        balance_offset = np.linalg.norm(center_of_mass - support_base_center)
        balance_score = max(0, 1 - balance_offset / 100)  # 假设100像素内为良好平衡
        
        return balance_score
    
    def analyze_hand_positions(self, pose_landmarks, hand_landmarks_list, frame_shape):
        """分析手部位置威胁"""
        threat_score = 0.0
        
        # 基于姿态的手部位置
        if pose_landmarks:
            left_wrist = np.array([pose_landmarks[self.mp_pose.PoseLandmark.LEFT_WRIST].x * frame_shape[1],
                                  pose_landmarks[self.mp_pose.PoseLandmark.LEFT_WRIST].y * frame_shape[0]])
            right_wrist = np.array([pose_landmarks[self.mp_pose.PoseLandmark.RIGHT_WRIST].x * frame_shape[1],
                                   pose_landmarks[self.mp_pose.PoseLandmark.RIGHT_WRIST].y * frame_shape[0]])
            
            body_center_x = frame_shape[1] / 2
            body_center_y = frame_shape[0] / 2
            
            # 手部靠近身体中心线
            for wrist in [left_wrist, right_wrist]:
                horizontal_threat = 1 - min(abs(wrist[0] - body_center_x) / (frame_shape[1] / 2), 1.0)
                vertical_threat = 1 - min(abs(wrist[1] - body_center_y) / (frame_shape[0] / 2), 1.0)
                threat_score += (horizontal_threat + vertical_threat) * 0.25
        
        # 基于手部关键点的姿态分析
        for hand_landmarks in hand_landmarks_list:
            if hand_landmarks:
                # 检测握拳手势
                fist_score = self.detect_fist_gesture(hand_landmarks)
                threat_score += fist_score * 0.3
                
                # 检测指向手势
                pointing_score = self.detect_pointing_gesture(hand_landmarks)
                threat_score += pointing_score * 0.2
        
        return min(threat_score, 1.0)
    
    def detect_fist_gesture(self, hand_landmarks):
        """检测握拳手势"""
        landmarks = hand_landmarks.landmark
        
        # 检查指尖是否靠近手掌
        fingertip_indices = [4, 8, 12, 16, 20]  # 指尖关键点
        palm_indices = [0, 5, 9, 13, 17]  # 手掌关键点
        
        closed_fingers = 0
        for tip_idx in fingertip_indices:
            tip = np.array([landmarks[tip_idx].x, landmarks[tip_idx].y])
            min_distance = float('inf')
            
            for palm_idx in palm_indices:
                palm = np.array([landmarks[palm_idx].x, landmarks[palm_idx].y])
                distance = np.linalg.norm(tip - palm)
                min_distance = min(min_distance, distance)
            
            if min_distance < 0.05:  # 阈值，可根据需要调整
                closed_fingers += 1
        
        return closed_fingers / 5  # 5根手指
    
    def detect_pointing_gesture(self, hand_landmarks):
        """检测指向手势"""
        landmarks = hand_landmarks.landmark
        
        # 食指伸直，其他手指弯曲
        index_tip = np.array([landmarks[8].x, landmarks[8].y])
        index_mcp = np.array([landmarks[5].x, landmarks[5].y])
        
        middle_tip = np.array([landmarks[12].x, landmarks[12].y])
        middle_mcp = np.array([landmarks[9].x, landmarks[9].y])
        
        # 食指伸直度
        index_extension = np.linalg.norm(index_tip - index_mcp)
        middle_extension = np.linalg.norm(middle_tip - middle_mcp)
        
        if index_extension > middle_extension * 1.2:  # 食指比中指更伸直
            return 0.8
        return 0.0
    
    def analyze_movement_preparation(self, landmarks, frame_shape):
        """分析运动准备状态"""
        left_knee = np.array([landmarks[self.mp_pose.PoseLandmark.LEFT_KNEE].x * frame_shape[1],
                             landmarks[self.mp_pose.PoseLandmark.LEFT_KNEE].y * frame_shape[0]])
        right_knee = np.array([landmarks[self.mp_pose.PoseLandmark.RIGHT_KNEE].x * frame_shape[1],
                              landmarks[self.mp_pose.PoseLandmark.RIGHT_KNEE].y * frame_shape[0]])
        
        left_ankle = np.array([landmarks[self.mp_pose.PoseLandmark.LEFT_ANKLE].x * frame_shape[1],
                              landmarks[self.mp_pose.PoseLandmark.LEFT_ANKLE].y * frame_shape[0]])
        right_ankle = np.array([landmarks[self.mp_pose.PoseLandmark.RIGHT_ANKLE].x * frame_shape[1],
                               landmarks[self.mp_pose.PoseLandmark.RIGHT_ANKLE].y * frame_shape[0]])
        
        # 膝盖弯曲度分析
        left_leg_bent = self.calculate_leg_bent_angle(left_knee, left_ankle)
        right_leg_bent = self.calculate_leg_bent_angle(right_knee, right_ankle)
        
        # 弯曲的腿可能表示准备移动
        bent_score = max(left_leg_bent, right_leg_bent)
        
        return bent_score
    
    def calculate_leg_bent_angle(self, knee, ankle):
        """计算腿部弯曲角度"""
        # 简化的弯曲度计算
        vertical_diff = abs(knee[1] - ankle[1])
        horizontal_diff = abs(knee[0] - ankle[0])
        
        # 水平差异越大，弯曲度越高
        bent_ratio = min(horizontal_diff / (vertical_diff + 1e-7), 2.0) / 2.0
        
        return bent_ratio
    
    def track_persons(self, yolo_results, pose_results, frame):
        """多人跟踪和威胁关联"""
        current_persons = {}
        
        # 从YOLO结果中提取人物
        for result in yolo_results:
            if result.boxes is not None:
                for i, box in enumerate(result.boxes):
                    cls = int(box.cls[0])
                    if self.yolo_model.names[cls] == 'person':
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        conf = float(box.conf[0])
                        
                        # 计算人物中心点
                        center_x = (x1 + x2) // 2
                        center_y = (y1 + y2) // 2
                        
                        person_id = self.assign_person_id(center_x, center_y)
                        current_persons[person_id] = {
                            'bbox': (x1, y1, x2, y2),
                            'center': (center_x, center_y),
                            'confidence': conf,
                            'threat_level': 0.0,
                            'tracking_count': self.person_tracker.get(person_id, {}).get('tracking_count', 0) + 1
                        }
        
        self.person_tracker = current_persons
        return current_persons
    
    def assign_person_id(self, center_x, center_y, max_distance=50):
        """为检测到的人物分配或匹配ID"""
        for person_id, info in self.person_tracker.items():
            prev_center = info['center']
            distance = np.linalg.norm(np.array(prev_center) - np.array([center_x, center_y]))
            if distance < max_distance:
                return person_id
        
        # 新人物，创建新ID
        return len(self.person_tracker)
    
    def calculate_comprehensive_threat(self, frame):
        """计算综合威胁等级"""
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # 多模型并行检测
        yolo_results = self.yolo_model(frame, verbose=False)
        face_results = self.face_detection.process(rgb_frame)
        pose_results = self.pose.process(rgb_frame)
        hand_results = self.hands.process(rgb_frame)
        face_mesh_results = self.face_mesh.process(rgb_frame)
        
        # 多人跟踪
        persons = self.track_persons(yolo_results, pose_results, frame)
        
        threat_components = {
            'weapon': 0.0,
            'behavior': 0.0,
            'facial': 0.0,
            'environment': 0.0
        }
        
        detailed_analysis = []
        
        # 武器检测 (最高权重)
        weapon_threat = self.detect_weapons(yolo_results)
        threat_components['weapon'] = weapon_threat * 0.4
        
        # 行为分析
        behavior_threat, behavior_details = self.analyze_advanced_body_language(
            pose_results.pose_landmarks, 
            hand_results.multi_hand_landmarks if hand_results.multi_hand_landmarks else [],
            frame.shape
        )
        threat_components['behavior'] = behavior_threat * 0.3
        detailed_analysis.extend(behavior_details)
        
        # 面部情绪分析
        facial_threat = 0.0
        if face_results.detections:
            for detection in face_results.detections:
                bbox = detection.location_data.relative_bounding_box
                x = int(bbox.xmin * frame.shape[1])
                y = int(bbox.ymin * frame.shape[0])
                w = int(bbox.width * frame.shape[1])
                h = int(bbox.height * frame.shape[0])
                
                face_region = frame[y:y+h, x:x+w]
                face_threat, emotion = self.detect_advanced_facial_analysis(
                    face_region, 
                    face_mesh_results.multi_face_landmarks[0] if face_mesh_results.multi_face_landmarks else None
                )
                facial_threat = max(facial_threat, face_threat)
                detailed_analysis.append(f"面部情绪: {emotion}, 威胁度: {face_threat:.2f}")
        
        threat_components['facial'] = facial_threat * 0.2
        
        # 环境上下文分析
        environmental_threat = self.analyze_environmental_context(persons, frame)
        threat_components['environment'] = environmental_threat * 0.1
        
        # 计算综合威胁
        total_threat = sum(threat_components.values())
        
        # 应用时间平滑和历史分析
        self.threat_level = 0.6 * self.threat_level + 0.4 * total_threat
        self.threat_history.append(self.threat_level)
        
        # 更新历史记录
        self.facial_threat_history.append(threat_components['facial'])
        self.behavior_threat_history.append(threat_components['behavior'])
        
        return self.threat_level, threat_components, detailed_analysis, yolo_results, persons
    
    def detect_weapons(self, yolo_results):
        """检测武器和可疑物品"""
        weapon_threat = 0.0
        weapon_categories = ['knife', 'gun', 'cell phone', 'backpack', 'suitcase', 'handbag']
        
        for result in yolo_results:
            if result.boxes is not None:
                for box in result.boxes:
                    cls = int(box.cls[0])
                    conf = float(box.conf[0])
                    label = self.yolo_model.names[cls]
                    
                    if label in weapon_categories:
                        threat_weight = 1.0 if label in ['knife', 'gun'] else 0.6
                        weapon_threat = max(weapon_threat, conf * threat_weight)
        
        return weapon_threat
    
    def analyze_environmental_context(self, persons, frame):
        """分析环境上下文威胁"""
        environmental_threat = 0.0
        
        # 多人场景分析
        if len(persons) > 2:
            environmental_threat += 0.3  # 人群环境增加基础威胁
        
        # 空间密度分析
        if len(persons) >= 2:
            centers = [info['center'] for info in persons.values()]
            min_distance = float('inf')
            
            for i in range(len(centers)):
                for j in range(i+1, len(centers)):
                    distance = np.linalg.norm(np.array(centers[i]) - np.array(centers[j]))
                    min_distance = min(min_distance, distance)
            
            # 人物间距离过近增加威胁
            if min_distance < 100:  # 100像素阈值
                environmental_threat += 0.4
        
        return min(environmental_threat, 1.0)
    
    def create_advanced_visualization(self, frame, threat_level, threat_components, detailed_analysis, persons):
        """创建高级可视化界面"""
        # 基础热力图叠加
        overlay = self.create_thermal_overlay(frame, threat_level)
        
        # 威胁组件雷达图
        radar_overlay = self.create_threat_radar(overlay, threat_components)
        
        # 绘制人物边界框和威胁信息
        for person_id, info in persons.items():
            x1, y1, x2, y2 = info['bbox']
            person_threat = info.get('threat_level', 0.0)
            
            # 根据个人威胁等级着色
            color = (0, 255, 0)  # 绿色 - 低威胁
            if person_threat > 0.5:
                color = (0, 255, 255)  # 黄色 - 中威胁
            if person_threat > 0.7:
                color = (0, 0, 255)  # 红色 - 高威胁
            
            cv2.rectangle(radar_overlay, (x1, y1), (x2, y2), color, 2)
            cv2.putText(radar_overlay, f"P{person_id}: {person_threat:.2f}", 
                       (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        
        # 添加威胁等级指示器
        final_frame = self.add_threat_indicators(radar_overlay, threat_level, threat_components, detailed_analysis)
        
        return final_frame
    
    def create_threat_radar(self, frame, threat_components):
        """创建威胁组件雷达图"""
        height, width = frame.shape[:2]
        radar_center = (width - 100, 100)
        radar_radius = 60
        
        # 绘制雷达图背景
        cv2.circle(frame, radar_center, radar_radius, (50, 50, 50), -1)
        cv2.circle(frame, radar_center, radar_radius, (200, 200, 200), 2)
        
        # 定义威胁组件位置
        components = list(threat_components.keys())
        angles = np.linspace(0, 2*np.pi, len(components), endpoint=False)
        
        for i, (component, angle) in enumerate(zip(components, angles)):
            # 计算雷达图顶点
            value = threat_components[component]
            x = int(radar_center[0] + radar_radius * value * np.cos(angle))
            y = int(radar_center[1] + radar_radius * value * np.sin(angle))
            
            # 绘制连接线
            cv2.line(frame, radar_center, (x, y), (255, 255, 255), 1)
            
            # 绘制数据点
            cv2.circle(frame, (x, y), 3, (0, 0, 255), -1)
            
            # 添加标签
            label_x = int(radar_center[0] + (radar_radius + 15) * np.cos(angle))
            label_y = int(radar_center[1] + (radar_radius + 15) * np.sin(angle))
            cv2.putText(frame, component[:3], (label_x-10, label_y+5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
        
        return frame
    
    def add_threat_indicators(self, frame, threat_level, threat_components, detailed_analysis):
        """添加威胁指示器和分析信息"""
        # 主威胁等级条
        threat_bar_width = 400
        threat_bar_height = 25
        threat_x = 50
        threat_y = frame.shape[0] - 80
        
        # 背景
        cv2.rectangle(frame, (threat_x, threat_y), 
                     (threat_x + threat_bar_width, threat_y + threat_bar_height), (50, 50, 50), -1)
        
        # 威胁等级填充
        fill_width = int(threat_level * threat_bar_width)
        color = (0, 255, 0) if threat_level < 0.4 else (0, 255, 255) if threat_level < 0.7 else (0, 0, 255)
        cv2.rectangle(frame, (threat_x, threat_y), 
                     (threat_x + fill_width, threat_y + threat_bar_height), color, -1)
        
        # 边框和文字
        cv2.rectangle(frame, (threat_x, threat_y), 
                     (threat_x + threat_bar_width, threat_y + threat_bar_height), (255, 255, 255), 2)
        
        threat_text = f"综合杀意感知等级: {threat_level:.3f}"
        cv2.putText(frame, threat_text, (threat_x, threat_y - 10), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # 威胁等级文字提示
        if threat_level > 0.7:
            warning_text = "⚠️ 高度威胁! 极度危险! ⚠️"
            text_size = cv2.getTextSize(warning_text, cv2.FONT_HERSHEY_SIMPLEX, 1.2, 3)[0]
            text_x = (frame.shape[1] - text_size[0]) // 2
            cv2.putText(frame, warning_text, (text_x, 50), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 3)
        elif threat_level > 0.5:
            warning_text = "⚠️ 中度威胁! 保持警惕! ⚠️"
            text_size = cv2.getTextSize(warning_text, cv2.FONT_HERSHEY_SIMPLEX, 1.0, 2)[0]
            text_x = (frame.shape[1] - text_size[0]) // 2
            cv2.putText(frame, warning_text, (text_x, 50), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)
        
        # 详细分析信息
        analysis_y = threat_y - 120
        for i, analysis in enumerate(detailed_analysis[:6]):  # 显示前6条分析
            cv2.putText(frame, analysis, (threat_x, analysis_y - i*20), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
        
        # 系统状态信息
        status_text = f"追踪人物: {len(self.person_tracker)} | 帧数: {self.frame_count}"
        cv2.putText(frame, status_text, (frame.shape[1] - 250, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        return frame
    
    def create_thermal_overlay(self, frame, threat_level):
        """创建热力图叠加层"""
        heat_map = np.zeros(frame.shape[:2], dtype=np.uint8)
        center_y, center_x = frame.shape[0] // 2, frame.shape[1] // 2
        
        # 生成径向渐变
        y, x = np.ogrid[:frame.shape[0], :frame.shape[1]]
        mask = np.sqrt((x - center_x)**2 + (y - center_y)**2)
        mask = 255 - np.clip(mask / max(center_x, center_y) * 255 * threat_level, 0, 255).astype(np.uint8)
        
        # 应用热力图颜色
        thermal = cv2.LUT(mask, self.thermal_lut)
        thermal = cv2.resize(thermal, (frame.shape[1], frame.shape[0]))
        
        # 混合原图和热力图
        overlay = cv2.addWeighted(frame, 1 - self.alpha, thermal, self.alpha, 0)
        return overlay
    
    def play_adaptive_warning(self, threat_level):
        """自适应警告音效"""
        if self.warning_sound and threat_level > 0.6:
            if not pygame.mixer.get_busy():
                self.warning_sound.play()
    
    def run(self, source=0):
        """运行高级杀意感知系统"""
        cap = cv2.VideoCapture(source)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        
        print("高级杀意感知系统运行中...")
        print("系统功能: 多人追踪、行为分析、情绪识别、环境感知")
        print("按 'q' 退出系统")
        
        # 性能监控
        fps_counter = 0
        start_time = time.time()
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            self.frame_count += 1
            fps_counter += 1
            
            # 计算FPS
            if fps_counter >= 30:
                end_time = time.time()
                fps = fps_counter / (end_time - start_time)
                print(f"系统FPS: {fps:.1f} | 威胁等级: {self.threat_level:.3f}")
                fps_counter = 0
                start_time = time.time()
            
            # 计算综合威胁等级
            threat_level, threat_components, detailed_analysis, yolo_results, persons = self.calculate_comprehensive_threat(frame)
            
            # 自适应警告
            self.play_adaptive_warning(threat_level)
            
            # 高级可视化
            result_frame = self.create_advanced_visualization(
                frame, threat_level, threat_components, detailed_analysis, persons
            )
            
            # 显示结果
            cv2.imshow('燕双鹰高级杀意感知系统 v2.0', result_frame)
            
            # 退出条件
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('r'):
                # 重置威胁等级
                self.threat_level = 0.0
                self.threat_history.clear()
                print("系统已重置")
        
        cap.release()
        cv2.destroyAllWindows()
        if self.warning_sound:
            pygame.mixer.quit()

# 增强型实时威胁监控面板
class AdvancedThreatMonitor:
    def __init__(self, perception_system):
        self.ps = perception_system
        self.fig, ((self.ax1, self.ax2), (self.ax3, self.ax4)) = plt.subplots(2, 2, figsize=(15, 10))
        plt.subplots_adjust(hspace=0.4)
        
        # 设置子图
        self.setup_threat_timeline(self.ax1)
        self.setup_component_radar(self.ax2)
        self.setup_person_tracker(self.ax3)
        self.setup_system_status(self.ax4)
        
    def setup_threat_timeline(self, ax):
        """设置威胁时间线图"""
        ax.set_ylim(0, 1)
        ax.set_xlim(0, 100)
        ax.set_title('实时威胁等级时间线', fontsize=12, fontweight='bold')
        ax.set_xlabel('时间帧')
        ax.set_ylabel('威胁等级')
        ax.grid(True, alpha=0.3)
        self.timeline_line, = ax.plot([], [], 'r-', linewidth=2, label='综合威胁')
        ax.legend()
    
    def setup_component_radar(self, ax):
        """设置威胁组件雷达图"""
        ax.set_xlim(-1.2, 1.2)
        ax.set_ylim(-1.2, 1.2)
        ax.set_title('威胁组件分析', fontsize=12, fontweight='bold')
        ax.set_aspect('equal')
        ax.grid(True, alpha=0.3)
        
        # 初始化雷达图
        components = ['weapon', 'behavior', 'facial', 'environment']
        angles = np.linspace(0, 2*np.pi, len(components), endpoint=False)
        angles = np.concatenate((angles, [angles[0]]))
        
        self.radar_lines = []
        for i in range(4):  # 保留4个历史帧
            line, = ax.plot([], [], 'o-', linewidth=1, alpha=0.7)
            self.radar_lines.append(line)
        
        # 添加组件标签
        for i, component in enumerate(components):
            angle = angles[i]
            x = 1.1 * np.cos(angle)
            y = 1.1 * np.sin(angle)
            ax.text(x, y, component, ha='center', va='center', fontsize=9)
    
    def setup_person_tracker(self, ax):
        """设置人物跟踪器"""
        ax.set_title('人物威胁分布', fontsize=12, fontweight='bold')
        ax.set_xlabel('人物ID')
        ax.set_ylabel('威胁等级')
        ax.set_ylim(0, 1)
        self.person_bars = ax.bar([], [], color='red', alpha=0.7)
    
    def setup_system_status(self, ax):
        """设置系统状态显示"""
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.set_title('系统状态', fontsize=12, fontweight='bold')
        ax.axis('off')
        self.status_text = ax.text(0.1, 0.8, '', fontsize=10, va='top')
    
    def update(self, frame):
        """更新所有图表"""
        # 更新时间线
        if len(self.ps.threat_history) > 0:
            x_data = list(range(len(self.ps.threat_history)))
            y_data = list(self.ps.threat_history)
            self.timeline_line.set_data(x_data, y_data)
            self.ax1.set_xlim(0, max(100, len(x_data)))
        
        # 更新人物跟踪
        if self.ps.person_tracker:
            person_ids = list(self.ps.person_tracker.keys())
            threat_levels = [info.get('threat_level', 0) for info in self.ps.person_tracker.values()]
            
            for bar, height in zip(self.ax3.patches, threat_levels):
                bar.set_height(height)
            
            # 调整x轴
            self.ax3.set_xlim(-0.5, len(person_ids) - 0.5)
            self.ax3.set_xticks(range(len(person_ids)))
            self.ax3.set_xticklabels([f'P{pid}' for pid in person_ids])
        
        # 更新系统状态
        status_info = f"""系统状态:
追踪人物: {len(self.ps.person_tracker)}
总帧数: {self.ps.frame_count}
当前威胁: {self.ps.threat_level:.3f}
面部威胁历史: {np.mean(list(self.ps.facial_threat_history)):.3f}
行为威胁历史: {np.mean(list(self.ps.behavior_threat_history)):.3f}"""
        self.status_text.set_text(status_info)
        
        return self.timeline_line, *self.radar_lines, *self.ax3.patches, self.status_text
    
    def start_monitor(self):
        """启动监控面板"""
        from matplotlib.animation import FuncAnimation
        ani = FuncAnimation(self.fig, self.update, interval=200, blit=False)
        plt.show()

if __name__ == "__main__":
    # 创建高级杀意感知系统
    system = AdvancedKillingIntentPerceptionSystem()
    
    # 在后台启动威胁监控面板
    try:
        monitor_thread = threading.Thread(target=AdvancedThreatMonitor(system).start_monitor)
        monitor_thread.daemon = True
        monitor_thread.start()
        print("威胁监控面板已启动")
    except Exception as e:
        print(f"监控面板启动失败: {e}")
    
    # 启动主系统
    try:
        system.run(source=0)  # 使用摄像头
        # system.run(source="test_video.mp4")  # 或使用视频文件
    except KeyboardInterrupt:
        print("\n系统被用户中断")
    except Exception as e:
        print(f"系统运行错误: {e}")
    
    print("燕双鹰杀意感知系统已关闭")