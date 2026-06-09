import cv2
import numpy as np
import torch
from ultralytics import YOLO
from collections import deque, defaultdict
import time
from scipy import ndimage
from scipy.fftpack import dct, idct
import numba
from sklearn.ensemble import IsolationForest
import warnings
warnings.filterwarnings('ignore')

class MDPQuantumTrafficSystem:
    """基于MDP的实时量子交通决策系统"""
    
    def __init__(self, camera_index=0, model_path='yolov8n.pt'):
        self.camera_index = camera_index
        self.cap = None
        self.is_running = False
        
        # 加载YOLO模型
        print("加载YOLO模型...")
        self.model = YOLO(model_path)
        self.vehicle_classes = [2, 3, 5, 7]  # car, motorcycle, bus, truck
        
        # MDP参数
        self.states = ['free_flow', 'light_congestion', 'heavy_congestion', 'gridlock']
        self.actions = ['maintain', 'increase_flow', 'decrease_flow', 'emergency_clear']
        self.policy = None
        self.value_function = None
        self.state_transition_history = deque(maxlen=100)
        
        # 实时性保障参数
        self.frame_processing_time = deque(maxlen=30)  # 记录处理时间
        self.target_fps = 15  # 目标帧率
        self.max_processing_time = 1.0 / self.target_fps  # 最大处理时间(秒)
        
        # 交通参数
        self.traffic_density = 0.0
        self.flow_velocity = 0.0
        self.congestion_level = 0.0
        self.accident_risk = 0.0
        
        # 量子场参数
        self.vehicle_charge = 1.0
        self.road_potential = 0.5
        
        # 跟踪和历史数据
        self.track_history = defaultdict(lambda: deque(maxlen=30))
        self.traffic_state_history = deque(maxlen=100)
        self.entropy_history = deque(maxlen=100)
        
        # 性能优化
        self.process_every_n_frames = 2
        self.frame_count = 0
        self.last_detection_time = time.time()
        
        # 初始化MDP
        self.initialize_mdp()
        
        # 可视化参数
        self.colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), 
                      (255, 255, 0), (255, 0, 255), (0, 255, 255)]

    def initialize_mdp(self):
        """初始化马尔科夫决策过程"""
        # 状态空间
        self.state_space_size = len(self.states)
        
        # 动作空间
        self.action_space_size = len(self.actions)
        
        # 初始化转移概率矩阵 (简化版本)
        self.transition_probs = self.initialize_transition_probabilities()
        
        # 奖励函数
        self.reward_function = self.initialize_reward_function()
        
        # 折扣因子
        self.gamma = 0.95
        
        # 初始化值函数和策略
        self.value_function = np.zeros(self.state_space_size)
        self.policy = np.zeros(self.state_space_size, dtype=int)
        
        # 使用值迭代求解MDP
        self.value_iteration()

    def initialize_transition_probabilities(self):
        """初始化状态转移概率矩阵"""
        # 简化版本：基于经验设定转移概率
        # 实际应用中应该从数据中学习
        
        transition_probs = np.zeros((self.state_space_size, self.action_space_size, self.state_space_size))
        
        # free_flow 状态
        transition_probs[0, :, 0] = 0.7  # 保持在自由流
        transition_probs[0, :, 1] = 0.3  # 转移到轻度拥堵
        
        # light_congestion 状态
        transition_probs[1, 0, 1] = 0.6  # 保持动作：保持在轻度拥堵
        transition_probs[1, 0, 0] = 0.2  # 恢复到自由流
        transition_probs[1, 0, 2] = 0.2  # 恶化为重度拥堵
        
        transition_probs[1, 1, 0] = 0.5  # 增加流量：改善到自由流
        transition_probs[1, 1, 1] = 0.5  # 保持在轻度拥堵
        
        # heavy_congestion 状态
        transition_probs[2, 0, 2] = 0.6  # 保持动作：保持在重度拥堵
        transition_probs[2, 0, 1] = 0.3  # 改善到轻度拥堵
        transition_probs[2, 0, 3] = 0.1  # 恶化为死锁
        
        transition_probs[2, 2, 1] = 0.7  # 减少流量：改善到轻度拥堵
        transition_probs[2, 2, 2] = 0.3  # 保持在重度拥堵
        
        # gridlock 状态
        transition_probs[3, 3, 1] = 0.8  # 紧急清空：改善到轻度拥堵
        transition_probs[3, 3, 2] = 0.2  # 改善到重度拥堵
        
        return transition_probs

    def initialize_reward_function(self):
        """初始化奖励函数"""
        # 基于状态的奖励
        state_rewards = {
            'free_flow': 10,
            'light_congestion': 0,
            'heavy_congestion': -5,
            'gridlock': -20
        }
        
        # 基于动作的成本
        action_costs = {
            'maintain': 0,
            'increase_flow': -1,
            'decrease_flow': -2,
            'emergency_clear': -5
        }
        
        # 构建奖励矩阵
        reward_matrix = np.zeros((self.state_space_size, self.action_space_size))
        
        for i, state in enumerate(self.states):
            for j, action in enumerate(self.actions):
                reward_matrix[i, j] = state_rewards[state] + action_costs[action]
        
        return reward_matrix

    def value_iteration(self, theta=1e-6):
        """值迭代算法求解MDP"""
        max_iterations = 1000
        
        for i in range(max_iterations):
            delta = 0
            new_value_function = np.copy(self.value_function)
            
            for s in range(self.state_space_size):
                # 计算每个动作的Q值
                q_values = np.zeros(self.action_space_size)
                
                for a in range(self.action_space_size):
                    # 计算期望回报
                    expected_return = 0
                    for next_s in range(self.state_space_size):
                        expected_return += self.transition_probs[s, a, next_s] * (
                            self.reward_function[s, a] + self.gamma * self.value_function[next_s]
                        )
                    q_values[a] = expected_return
                
                # 更新值函数
                new_value_function[s] = np.max(q_values)
                delta = max(delta, abs(new_value_function[s] - self.value_function[s]))
            
            self.value_function = new_value_function
            
            # 检查收敛
            if delta < theta:
                print(f"MDP值迭代在 {i+1} 次迭代后收敛")
                break
        
        # 提取最优策略
        self.extract_optimal_policy()

    def extract_optimal_policy(self):
        """从值函数中提取最优策略"""
        for s in range(self.state_space_size):
            q_values = np.zeros(self.action_space_size)
            
            for a in range(self.action_space_size):
                expected_return = 0
                for next_s in range(self.state_space_size):
                    expected_return += self.transition_probs[s, a, next_s] * (
                        self.reward_function[s, a] + self.gamma * self.value_function[next_s]
                    )
                q_values[a] = expected_return
            
            self.policy[s] = np.argmax(q_values)

    def get_current_state(self, traffic_analysis):
        """根据交通分析确定当前状态"""
        congestion = traffic_analysis['congestion_index']
        vehicle_count = traffic_analysis['vehicle_count']
        avg_velocity = traffic_analysis['average_velocity']
        
        # 基于多个指标确定状态
        if congestion < 0.3 and vehicle_count < 10 and avg_velocity > 5:
            return 0  # free_flow
        elif congestion < 0.6 and vehicle_count < 20 and avg_velocity > 2:
            return 1  # light_congestion
        elif congestion < 0.8 and vehicle_count < 30 and avg_velocity > 1:
            return 2  # heavy_congestion
        else:
            return 3  # gridlock

    def mdp_decision(self, current_state, traffic_analysis):
        """基于MDP做出决策"""
        # 获取最优动作
        optimal_action = self.policy[current_state]
        action_name = self.actions[optimal_action]
        
        # 计算动作的价值
        action_value = self.calculate_action_value(current_state, optimal_action)
        
        # 生成决策建议
        decision_advice = self.generate_decision_advice(action_name, traffic_analysis)
        
        return {
            'current_state': self.states[current_state],
            'optimal_action': action_name,
            'action_value': action_value,
            'advice': decision_advice,
            'state_confidence': self.calculate_state_confidence(current_state, traffic_analysis)
        }

    def calculate_action_value(self, state, action):
        """计算动作的价值"""
        value = 0
        for next_state in range(self.state_space_size):
            value += self.transition_probs[state, action, next_state] * (
                self.reward_function[state, action] + self.gamma * self.value_function[next_state]
            )
        return value

    def calculate_state_confidence(self, state, traffic_analysis):
        """计算状态识别的置信度"""
        # 基于多个指标的一致性计算置信度
        congestion = traffic_analysis['congestion_index']
        vehicle_count = traffic_analysis['vehicle_count']
        
        # 状态特定的置信度计算
        if state == 0:  # free_flow
            confidence = 1.0 - congestion
        elif state == 1:  # light_congestion
            confidence = 1.0 - abs(congestion - 0.45)
        elif state == 2:  # heavy_congestion
            confidence = 1.0 - abs(congestion - 0.7)
        else:  # gridlock
            confidence = congestion
        
        return max(0.0, min(1.0, confidence))

    def generate_decision_advice(self, action, traffic_analysis):
        """生成决策建议"""
        advice_map = {
            'maintain': "保持当前交通控制策略，系统运行良好",
            'increase_flow': "建议增加绿灯时间或开放更多车道",
            'decrease_flow': "建议限制入口流量或调整信号配时",
            'emergency_clear': "需要紧急干预，考虑启用应急通道"
        }
        
        base_advice = advice_map.get(action, "无特定建议")
        
        # 基于具体交通状况细化建议
        if traffic_analysis['accident_risk'] > 0.7:
            base_advice += " | 高风险状态，建议加强监控"
        
        if traffic_analysis['average_velocity'] < 1.0:
            base_advice += " | 流速过低，考虑交通疏导"
        
        return base_advice

    def update_mdp_from_experience(self, state, action, next_state, reward):
        """基于经验更新MDP模型（简化版）"""
        # 在实际应用中，这里应该使用强化学习算法如Q-learning
        # 这里使用简单的经验回放更新
        
        # 记录经验
        experience = {
            'state': state,
            'action': action,
            'next_state': next_state,
            'reward': reward,
            'timestamp': time.time()
        }
        
        self.state_transition_history.append(experience)
        
        # 定期更新MDP模型（简化版）
        if len(self.state_transition_history) % 50 == 0:
            self.adaptive_mdp_update()

    def adaptive_mdp_update(self):
        """自适应MDP模型更新"""
        # 基于历史经验调整转移概率（简化版）
        # 实际应用中应该使用更复杂的强化学习算法
        
        print("执行自适应MDP更新...")
        
        # 这里可以添加基于经验的学习算法
        # 例如：Q-learning, SARSA, 等
        
        # 重新运行值迭代
        self.value_iteration(theta=1e-4)

    def initialize_camera(self):
        """初始化交通摄像头"""
        try:
            self.cap = cv2.VideoCapture(self.camera_index)
            if not self.cap.isOpened():
                self.cap = cv2.VideoCapture('traffic_video.mp4')
                if not self.cap.isOpened():
                    raise Exception("无法打开摄像头或视频文件")
            
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            
            print("交通摄像头初始化成功")
            return True
            
        except Exception as e:
            print(f"摄像头初始化失败: {e}")
            return False

    @numba.jit(nopython=True)
    def realtime_vehicle_detection(self, frame, model_output):
        """实时车辆检测（优化版本）"""
        # 这里使用简化的处理，实际应该集成YOLO
        vehicles = []
        
        # 模拟车辆检测结果
        # 实际应用中这里应该解析YOLO输出
        if len(model_output) > 0:
            for detection in model_output:
                x, y, w, h, conf, cls = detection
                if conf > 0.5:  # 置信度阈值
                    vehicles.append({
                        'position': (x + w/2, y + h/2),
                        'velocity': 0.0,  # 需要通过跟踪计算
                        'size': (w, h),
                        'area': w * h,
                        'confidence': conf
                    })
        
        return vehicles

    def optimized_traffic_analysis(self, vehicles, frame):
        """优化的交通分析（保证实时性）"""
        start_time = time.time()
        
        # 基本统计（快速计算）
        vehicle_count = len(vehicles)
        total_area = sum(v['area'] for v in vehicles) if vehicles else 0
        frame_area = frame.shape[0] * frame.shape[1]
        
        # 简化版的交通密度
        density = total_area / frame_area if frame_area > 0 else 0
        
        # 速度估计（简化）
        avg_velocity = self.estimate_average_velocity(vehicles)
        
        # 快速熵计算
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        shannon_entropy = self.fast_entropy_calculation(gray)
        
        # 拥堵指数（简化计算）
        congestion_index = min(1.0, density * 2 + max(0, 1 - avg_velocity/10))
        
        # 事故风险评估（简化）
        accident_risk = self.fast_risk_assessment(vehicles, density, avg_velocity)
        
        processing_time = time.time() - start_time
        self.frame_processing_time.append(processing_time)
        
        return {
            'vehicle_count': vehicle_count,
            'traffic_density': density,
            'average_velocity': avg_velocity,
            'congestion_index': congestion_index,
            'shannon_entropy': shannon_entropy,
            'accident_risk': accident_risk,
            'processing_time': processing_time
        }

    def estimate_average_velocity(self, vehicles):
        """快速速度估计"""
        if not vehicles:
            return 0.0
        
        # 基于跟踪历史的简单速度估计
        velocities = []
        for vehicle in vehicles:
            if 'id' in vehicle and vehicle['id'] in self.track_history:
                history = list(self.track_history[vehicle['id']])
                if len(history) >= 2:
                    # 计算最近两帧的位移
                    pos1 = history[-2]['position']
                    pos2 = history[-1]['position']
                    displacement = np.sqrt((pos2[0]-pos1[0])**2 + (pos2[1]-pos1[1])**2)
                    velocity = displacement / 0.033  # 假设30fps
                    velocities.append(min(velocity, 50.0))  # 限制最大速度
        
        return np.mean(velocities) if velocities else 5.0  # 默认速度

    def fast_entropy_calculation(self, image):
        """快速熵计算"""
        # 使用下采样和简化直方图加速计算
        small_img = cv2.resize(image, (64, 48))
        hist = cv2.calcHist([small_img], [0], None, [32], [0, 256])
        hist = hist / hist.sum()
        hist = hist[hist > 0]
        return -np.sum(hist * np.log2(hist))

    def fast_risk_assessment(self, vehicles, density, velocity):
        """快速风险评估"""
        risk = 0.0
        
        # 密度风险
        if density > 0.3:
            risk += 0.3
        
        # 速度差异风险（简化）
        if velocity < 2.0 and density > 0.2:
            risk += 0.4
        
        # 车辆数量风险
        if len(vehicles) > 15:
            risk += 0.3
        
        return min(risk, 1.0)

    def realtime_quantum_field(self, vehicles, frame_shape):
        """实时量子场计算（优化版本）"""
        height, width = frame_shape[:2]
        
        if not vehicles:
            return np.zeros((height, width)), np.zeros((height, width))
        
        # 简化版的场计算
        field = np.zeros((height, width))
        
        for vehicle in vehicles:
            x, y = map(int, vehicle['position'])
            if 0 <= x < width and 0 <= y < height:
                # 使用高斯核快速计算场影响
                size = int(max(vehicle['size']) / 2)
                influence = self.fast_gaussian_influence(x, y, size, height, width)
                field += influence * vehicle.get('area', 1000) / 1000
        
        # 归一化
        if np.max(field) > 0:
            field = field / np.max(field)
        
        return field, field  # 简化版本返回相同的场

    def fast_gaussian_influence(self, center_x, center_y, sigma, height, width):
        """快速高斯影响计算"""
        # 创建小范围的影响区域
        size = min(50, 2 * sigma + 1)  # 限制计算范围
        half_size = size // 2
        
        # 计算局部区域
        x_min = max(0, center_x - half_size)
        x_max = min(width, center_x + half_size + 1)
        y_min = max(0, center_y - half_size)
        y_max = min(height, center_y + half_size + 1)
        
        if x_min >= x_max or y_min >= y_max:
            return np.zeros((height, width))
        
        # 创建局部坐标网格
        x_local = np.arange(x_min, x_max)
        y_local = np.arange(y_min, y_max)
        X, Y = np.meshgrid(x_local, y_local)
        
        # 计算高斯权重
        dx = X - center_x
        dy = Y - center_y
        weights = np.exp(-(dx**2 + dy**2) / (2 * sigma**2))
        
        # 创建全图影响矩阵
        influence = np.zeros((height, width))
        influence[y_min:y_max, x_min:x_max] = weights
        
        return influence

    def adaptive_processing_control(self):
        """自适应处理控制（确保实时性）"""
        if len(self.frame_processing_time) < 5:
            return
        
        avg_processing_time = np.mean(self.frame_processing_time)
        
        # 动态调整处理频率
        if avg_processing_time > self.max_processing_time * 1.2:
            # 处理时间过长，降低处理频率
            self.process_every_n_frames = min(5, self.process_every_n_frames + 1)
            print(f"降低处理频率至每 {self.process_every_n_frames} 帧处理一次")
        
        elif avg_processing_time < self.max_processing_time * 0.8 and self.process_every_n_frames > 1:
            # 处理时间充足，提高处理频率
            self.process_every_n_frames = max(1, self.process_every_n_frames - 1)
            print(f"提高处理频率至每 {self.process_every_n_frames} 帧处理一次")

    def realtime_visualization(self, frame, vehicles, analysis, mdp_decision, field):
        """实时可视化（优化版本）"""
        height, width = frame.shape[:2]
        
        # 创建显示面板
        display = np.zeros((height, width * 2, 3), dtype=np.uint8)
        
        # 左侧：原始帧和检测结果
        left_panel = frame.copy()
        
        # 绘制检测框（简化）
        for vehicle in vehicles:
            x, y = map(int, vehicle['position'])
            w, h = map(int, vehicle['size'])
            cv2.rectangle(left_panel, (x-w//2, y-h//2), (x+w//2, y+h//2), (0, 255, 0), 2)
        
        # 右侧：分析和决策信息
        right_panel = self.create_realtime_info_panel(width, height, analysis, mdp_decision, field)
        
        display[:, :width] = left_panel
        display[:, width:] = right_panel
        
        return display

    def create_realtime_info_panel(self, width, height, analysis, mdp_decision, field):
        """创建实时信息面板"""
        panel = np.zeros((height, width, 3), dtype=np.uint8)
        
        y_offset = 30
        
        # 系统状态
        cv2.putText(panel, "Real-time MDP Traffic System", (10, y_offset), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        y_offset += 40
        
        # 交通状态
        state_info = [
            f"State: {mdp_decision['current_state']}",
            f"Confidence: {mdp_decision['state_confidence']:.2f}",
            f"Action: {mdp_decision['optimal_action']}",
            f"Value: {mdp_decision['action_value']:.2f}"
        ]
        
        for info in state_info:
            cv2.putText(panel, info, (10, y_offset), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
            y_offset += 20
        
        y_offset += 10
        
        # 交通参数
        traffic_info = [
            f"Vehicles: {analysis['vehicle_count']}",
            f"Density: {analysis['traffic_density']:.3f}",
            f"Velocity: {analysis['average_velocity']:.1f}",
            f"Congestion: {analysis['congestion_index']:.2f}",
            f"Risk: {analysis['accident_risk']:.2f}"
        ]
        
        for info in traffic_info:
            cv2.putText(panel, info, (10, y_offset), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 100), 1)
            y_offset += 20
        
        y_offset += 10
        
        # 性能信息
        perf_info = [
            f"Processing: {analysis['processing_time']*1000:.1f}ms",
            f"Frame Skip: {self.process_every_n_frames}",
            f"Target FPS: {self.target_fps}"
        ]
        
        for info in perf_info:
            cv2.putText(panel, info, (10, y_offset), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (100, 200, 200), 1)
            y_offset += 20
        
        y_offset += 10
        
        # 决策建议
        advice = mdp_decision['advice']
        # 分割长建议为多行
        words = advice.split()
        lines = []
        current_line = ""
        
        for word in words:
            if len(current_line + word) < 35:
                current_line += word + " "
            else:
                lines.append(current_line)
                current_line = word + " "
        if current_line:
            lines.append(current_line)
        
        for line in lines:
            cv2.putText(panel, line, (10, y_offset), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.3, (100, 255, 100), 1)
            y_offset += 15
        
        # 绘制简化图表
        self.draw_realtime_charts(panel, height - 150)
        
        return panel

    def draw_realtime_charts(self, panel, start_y):
        """绘制实时图表（优化版本）"""
        if len(self.traffic_state_history) < 2:
            return
        
        plot_height = 120
        plot_width = panel.shape[1] - 20
        
        if start_y + plot_height > panel.shape[0]:
            return
        
        # 创建绘图区域
        plot_area = np.zeros((plot_height, plot_width, 3), dtype=np.uint8)
        
        # 提取最近的数据（限制数量以保证性能）
        recent_data = list(self.traffic_state_history)[-min(20, len(self.traffic_state_history)):]
        
        if len(recent_data) < 2:
            return
        
        # 提取密度和拥堵数据
        densities = [data.get('traffic_density', 0) for data in recent_data]
        congestion = [data.get('congestion_index', 0) for data in recent_data]
        
        # 简化归一化
        def simple_normalize(data, height):
            if not data or max(data) == min(data):
                return [height // 2] * len(data)
            return [int(height - (val - min(data)) / (max(data) - min(data)) * height * 0.8) 
                   for val in data]
        
        # 绘制曲线
        density_plot = simple_normalize(densities, plot_height)
        congestion_plot = simple_normalize(congestion, plot_height)
        
        for i in range(1, len(density_plot)):
            x1 = int((i-1) * plot_width / len(density_plot))
            y1 = density_plot[i-1]
            x2 = int(i * plot_width / len(density_plot))
            y2 = density_plot[i]
            cv2.line(plot_area, (x1, y1), (x2, y2), (255, 0, 0), 1)
            
            y1_c = congestion_plot[i-1]
            y2_c = congestion_plot[i]
            cv2.line(plot_area, (x1, y1_c), (x2, y2_c), (0, 255, 255), 1)
        
        # 简单图例
        cv2.putText(plot_area, "Density", (5, 15), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.3, (255, 0, 0), 1)
        cv2.putText(plot_area, "Congestion", (5, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.3, (0, 255, 255), 1)
        
        panel[start_y:start_y+plot_height, 10:10+plot_width] = plot_area

    def run_realtime_system(self):
        """运行实时系统"""
        if not self.initialize_camera():
            return
        
        self.is_running = True
        
        print("实时MDP量子交通系统启动...")
        print("控制按键:")
        print("  'q': 退出系统")
        print("  'r': 重置MDP")
        print("  'p': 性能报告")
        
        last_state = None
        last_action = None
        
        while self.is_running:
            frame_start_time = time.time()
            
            ret, frame = self.cap.read()
            if not ret:
                print("无法读取帧")
                break
            
            self.frame_count += 1
            
            # 自适应处理控制
            self.adaptive_processing_control()
            
            # 跳过部分帧以保证实时性
            if self.frame_count % self.process_every_n_frames != 0:
                # 显示当前帧（不处理）
                cv2.imshow('MDP Quantum Traffic System', frame)
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    break
                elif key == ord('p'):
                    self.show_performance_report()
                continue
            
            # 实时车辆检测（简化版）
            # 实际应用中这里应该调用YOLO
            vehicles = self.simulate_vehicle_detection(frame)
            
            # 优化的交通分析
            traffic_analysis = self.optimized_traffic_analysis(vehicles, frame)
            
            # 实时量子场计算
            quantum_field, _ = self.realtime_quantum_field(vehicles, frame.shape)
            
            # MDP决策
            current_state = self.get_current_state(traffic_analysis)
            mdp_decision = self.mdp_decision(current_state, traffic_analysis)
            
            # 学习更新
            if last_state is not None and last_action is not None:
                # 计算奖励（基于状态改善）
                reward = self.calculate_reward(last_state, current_state, traffic_analysis)
                self.update_mdp_from_experience(last_state, last_action, current_state, reward)
            
            last_state = current_state
            last_action = self.actions.index(mdp_decision['optimal_action'])
            
            # 保存历史数据
            self.traffic_state_history.append(traffic_analysis)
            
            # 实时可视化
            display_frame = self.realtime_visualization(frame, vehicles, traffic_analysis, mdp_decision, quantum_field)
            
            # 显示结果
            cv2.imshow('MDP Quantum Traffic System', display_frame)
            
            # 计算并显示帧率
            frame_time = time.time() - frame_start_time
            current_fps = 1.0 / frame_time if frame_time > 0 else 0
            if self.frame_count % 30 == 0:
                print(f"当前帧率: {current_fps:.1f} FPS, 处理时间: {frame_time*1000:.1f}ms")
            
            # 键盘控制
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('r'):
                self.initialize_mdp()
                print("MDP已重置")
            elif key == ord('p'):
                self.show_performance_report()
        
        self.cleanup()

    def simulate_vehicle_detection(self, frame):
        """模拟车辆检测（用于演示）"""
        # 在实际应用中，这里应该使用YOLO
        vehicles = []
        
        # 创建一些模拟车辆
        height, width = frame.shape[:2]
        num_vehicles = np.random.randint(5, 20)
        
        for i in range(num_vehicles):
            x = np.random.randint(50, width-50)
            y = np.random.randint(50, height-50)
            w = np.random.randint(30, 80)
            h = np.random.randint(20, 50)
            
            vehicles.append({
                'id': i,
                'position': (x, y),
                'size': (w, h),
                'area': w * h,
                'velocity': np.random.uniform(0.5, 5.0)
            })
        
        return vehicles

    def calculate_reward(self, prev_state, current_state, analysis):
        """计算奖励（基于状态改善）"""
        base_rewards = [10, 0, -5, -20]  # 对应四个状态的基准奖励
        
        # 状态改善奖励
        state_improvement = prev_state - current_state  # 正数表示改善
        
        # 交通效率奖励
        efficiency_bonus = analysis['average_velocity'] * 0.1
        
        # 安全奖励
        safety_bonus = (1 - analysis['accident_risk']) * 5
        
        total_reward = base_rewards[current_state] + state_improvement * 2 + efficiency_bonus + safety_bonus
        
        return total_reward

    def show_performance_report(self):
        """显示性能报告"""
        if not self.frame_processing_time:
            print("尚无性能数据")
            return
        
        avg_processing = np.mean(self.frame_processing_time)
        max_processing = np.max(self.frame_processing_time)
        min_processing = np.min(self.frame_processing_time)
        
        print("\n=== 系统性能报告 ===")
        print(f"平均处理时间: {avg_processing*1000:.1f}ms")
        print(f"最大处理时间: {max_processing*1000:.1f}ms")
        print(f"最小处理时间: {min_processing*1000:.1f}ms")
        print(f"当前帧跳过: {self.process_every_n_frames}")
        print(f"目标帧率: {self.target_fps} FPS")
        print(f"历史状态数: {len(self.traffic_state_history)}")
        print(f"跟踪车辆数: {len(self.track_history)}")
        print("==================\n")

    def cleanup(self):
        """清理资源"""
        if self.cap:
            self.cap.release()
        cv2.destroyAllWindows()
        self.is_running = False
        print("系统已停止")

# 高级版本：带深度强化学习
class AdvancedMDPTrafficSystem(MDPQuantumTrafficSystem):
    """高级MDP交通系统（集成深度强化学习）"""
    
    def __init__(self, camera_index=0, model_path='yolov8n.pt'):
        super().__init__(camera_index, model_path)
        
        # DQN参数
        self.learning_rate = 0.001
        self.epsilon = 1.0
        self.epsilon_min = 0.01
        self.epsilon_decay = 0.995
        self.memory = deque(maxlen=2000)
        self.batch_size = 32
        
        # 状态特征维度
        self.state_dim = 6  # 车辆数、密度、速度、拥堵、熵、风险
        self.action_dim = len(self.actions)
        
        # 初始化DQN
        self.dqn_model = self.build_dqn_model()
        self.target_model = self.build_dqn_model()
        self.update_target_model()
    
    def build_dqn_model(self):
        """构建DQN模型（简化版）"""
        # 在实际应用中，这里应该使用PyTorch或TensorFlow
        # 这里返回一个模拟的模型
        class SimpleDQN:
            def predict(self, state):
                # 模拟预测
                return np.random.uniform(-1, 1, 4)  # 4个动作的Q值
            
            def fit(self, states, targets, verbose=0):
                # 模拟训练
                pass
        
        return SimpleDQN()
    
    def update_target_model(self):
        """更新目标网络"""
        # 在实际应用中，这里应该复制权重
        self.target_model = self.dqn_model
    
    def dqn_decision(self, state_features):
        """DQN决策"""
        if np.random.random() <= self.epsilon:
            # 探索：随机选择动作
            return np.random.randint(self.action_dim)
        else:
            # 利用：选择最优动作
            q_values = self.dqn_model.predict(state_features.reshape(1, -1))[0]
            return np.argmax(q_values)
    
    def remember(self, state, action, reward, next_state, done):
        """存储经验"""
        self.memory.append((state, action, reward, next_state, done))
    
    def replay(self):
        """经验回放"""
        if len(self.memory) < self.batch_size:
            return
        
        # 在实际应用中，这里应该实现完整的DQN训练
        # 简化版本：只更新epsilon
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay

def main():
    """主函数"""
    print("实时MDP量子交通决策系统")
    print("======================")
    
    # 选择运行模式
    print("选择运行模式:")
    print("1. 基础MDP系统")
    print("2. 高级DQN系统")
    
    choice = input("请输入选择 (1-2): ").strip()
    
    if choice == "1":
        system = MDPQuantumTrafficSystem(camera_index=0)
    elif choice == "2":
        system = AdvancedMDPTrafficSystem(camera_index=0)
    else:
        print("无效选择，使用基础模式")
        system = MDPQuantumTrafficSystem(camera_index=0)
    
    try:
        system.run_realtime_system()
    except KeyboardInterrupt:
        print("\n用户中断系统")
    except Exception as e:
        print(f"系统运行错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        system.cleanup()

if __name__ == "__main__":
    main()