import cv2
import numpy as np
import matplotlib.pyplot as plt
from scipy import ndimage
from scipy.fftpack import dct, idct
import numba
from collections import deque, defaultdict
import time
from sklearn.ensemble import IsolationForest
from sklearn.cluster import DBSCAN
import warnings
warnings.filterwarnings('ignore')

class TrafficQuantumFieldSensor:
    """交通量子场感知与预测系统"""
    
    def __init__(self, camera_index=0):
        self.camera_index = camera_index
        self.cap = None
        self.is_running = False
        
        # 交通参数
        self.traffic_density = 0.0
        self.flow_velocity = 0.0
        self.congestion_level = 0.0
        self.accident_risk = 0.0
        
        # 量子场参数
        self.vehicle_charge = 1.0  # 车辆电荷等效
        self.road_potential = 0.5  # 道路势场
        self.traffic_pressure = 0.0  # 交通压力
        
        # 预测模型
        self.traffic_state_history = deque(maxlen=100)
        self.entropy_history = deque(maxlen=100)
        self.flow_prediction = deque(maxlen=50)
        
        # 实时分析窗口
        self.analysis_region = None
        self.lane_regions = []
        
        # 事故检测
        self.anomaly_detector = IsolationForest(contamination=0.1)
        self.anomaly_scores = deque(maxlen=50)
        
        # 性能优化
        self.process_every_n_frames = 2
        self.frame_count = 0
        
    def initialize_camera(self):
        """初始化交通摄像头"""
        try:
            self.cap = cv2.VideoCapture(self.camera_index)
            if not self.cap.isOpened():
                # 尝试使用视频文件
                self.cap = cv2.VideoCapture('traffic_video.mp4')
                if not self.cap.isOpened():
                    raise Exception("无法打开摄像头或视频文件")
            
            # 设置参数
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            
            print("交通摄像头初始化成功")
            return True
            
        except Exception as e:
            print(f"摄像头初始化失败: {e}")
            return False

    def setup_analysis_regions(self, frame):
        """设置交通分析区域"""
        height, width = frame.shape[:2]
        
        # 默认分析区域（整个画面）
        self.analysis_region = (0, 0, width, height)
        
        # 自动检测车道区域（简化版）
        self.lane_regions = self.detect_lane_regions(frame)
        
        # 如果没有检测到车道，使用默认区域
        if not self.lane_regions:
            lane_height = height // 3
            self.lane_regions = [
                (0, lane_height, width, lane_height + height//3)
            ]

    def detect_lane_regions(self, frame):
        """检测车道区域"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # 边缘检测
        edges = cv2.Canny(gray, 50, 150)
        
        # 霍夫线变换检测车道线
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=50, 
                               minLineLength=100, maxLineGap=50)
        
        regions = []
        if lines is not None:
            # 分析线分布来确定车道
            horizontal_lines = [line for line in lines if abs(line[0][1]-line[0][3]) < 20]
            
            if len(horizontal_lines) >= 2:
                # 基于水平线确定车道区域
                y_coords = sorted([line[0][1] for line in horizontal_lines])
                for i in range(len(y_coords)-1):
                    regions.append((0, y_coords[i], frame.shape[1], y_coords[i+1]))
        
        return regions

    def vehicle_detection_quantum(self, frame):
        """
        基于量子场理论的车辆检测
        将车辆视为场源，通过场强分布检测车辆
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # 背景减除（简化版）
        if not hasattr(self, 'background_model'):
            self.background_model = gray.copy().astype(np.float32)
        
        # 更新背景模型
        cv2.accumulateWeighted(gray, self.background_model, 0.01)
        background = self.background_model.astype(np.uint8)
        
        # 前景检测
        foreground = cv2.absdiff(gray, background)
        _, motion_mask = cv2.threshold(foreground, 30, 255, cv2.THRESH_BINARY)
        
        # 形态学操作
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        motion_mask = cv2.morphologyEx(motion_mask, cv2.MORPH_OPEN, kernel)
        motion_mask = cv2.morphologyEx(motion_mask, cv2.MORPH_CLOSE, kernel)
        
        # 查找轮廓
        contours, _ = cv2.findContours(motion_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        vehicles = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if area > 500:  # 过滤小区域
                x, y, w, h = cv2.boundingRect(contour)
                vehicles.append({
                    'position': (x + w//2, y + h//2),
                    'velocity': self.estimate_velocity(contour),
                    'size': (w, h),
                    'area': area
                })
        
        return vehicles, motion_mask

    def estimate_velocity(self, contour):
        """估计车辆速度（简化版）"""
        # 在实际应用中，这里应该使用多帧跟踪
        # 这里返回随机速度用于演示
        return np.random.normal(0.5, 0.2)

    def traffic_electromagnetic_field(self, vehicles):
        """
        计算交通电磁场
        将车辆视为移动电荷，计算场分布
        """
        if not vehicles:
            return np.zeros((480, 640)), np.zeros((480, 640))
        
        height, width = 480, 640
        Ex = np.zeros((height, width))
        Ey = np.zeros((height, width))
        Bz = np.zeros((height, width))
        
        for vehicle in vehicles:
            x, y = vehicle['position']
            vx, vy = vehicle['velocity'], 0  # 简化：假设水平运动
            
            # 车辆电荷（与车辆大小相关）
            q = vehicle['area'] / 1000 * self.vehicle_charge
            
            # 创建坐标网格
            Y, X = np.ogrid[:height, :width]
            
            # 距离计算
            R = np.sqrt((X - x)**2 + (Y - y)**2 + 1e-6)  # 避免除零
            
            # 电场计算 (库仑定律)
            Ex_vehicle = q * (X - x) / R**3
            Ey_vehicle = q * (Y - y) / R**3
            
            # 磁场计算 (毕奥-萨伐尔定律)
            Bz_vehicle = q * (vx * (Y - y) - vy * (X - x)) / R**3
            
            Ex += Ex_vehicle
            Ey += Ey_vehicle
            Bz += Bz_vehicle
        
        # 场强计算
        E_magnitude = np.sqrt(Ex**2 + Ey**2)
        B_magnitude = np.abs(Bz)
        
        return E_magnitude, B_magnitude

    def quantum_traffic_flow(self, frame, vehicles, E_field, B_field):
        """
        量子交通流模拟
        将交通流建模为量子流体
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0
        
        # 交通势场（基于道路结构和车辆分布）
        traffic_potential = self.calculate_traffic_potential(vehicles, gray.shape)
        
        # 电磁场贡献
        em_potential = E_field + B_field
        
        # 总势场
        total_potential = traffic_potential + 0.1 * em_potential
        
        # 量子波函数演化
        quantum_flow = self.evolve_quantum_wavefunction(gray, total_potential)
        
        return quantum_flow

    def calculate_traffic_potential(self, vehicles, shape):
        """计算交通势场"""
        height, width = shape
        potential = np.zeros((height, width))
        
        # 道路结构势场（假设水平道路）
        road_center = height // 2
        road_width = height // 4
        
        # 创建道路势场（抛物线势阱）
        for y in range(height):
            distance_from_center = abs(y - road_center)
            if distance_from_center < road_width:
                potential[y, :] = 0.1 * (distance_from_center / road_width)**2
            else:
                potential[y, :] = 1.0  # 高势垒
        
        # 车辆排斥势场
        for vehicle in vehicles:
            x, y = vehicle['position']
            vehicle_size = max(vehicle['size'])
            
            # 车辆周围的排斥势
            vehicle_potential = np.zeros((height, width))
            Y, X = np.ogrid[:height, :width]
            R = np.sqrt((X - x)**2 + (Y - y)**2 + 1e-6)
            
            # 高斯排斥势
            sigma = vehicle_size
            vehicle_potential = np.exp(-R**2 / (2 * sigma**2))
            
            potential += 0.5 * vehicle_potential
        
        return potential

    def evolve_quantum_wavefunction(self, density, potential):
        """演化量子波函数（简化版）"""
        # 初始波函数（基于交通密度）
        psi_real = np.sqrt(density)
        psi_imag = np.zeros_like(psi_real)
        
        # 简化量子演化（实际应用中使用分裂算符法）
        # 这里使用扩散过程模拟量子效应
        from scipy.ndimage import gaussian_filter
        
        # 概率密度演化
        probability_density = psi_real**2
        
        # 应用量子扩散
        quantum_diffused = gaussian_filter(probability_density, sigma=2)
        
        # 势场影响
        potential_effect = np.exp(-potential)
        final_density = quantum_diffused * potential_effect
        
        # 归一化
        final_density = final_density / (np.max(final_density) + 1e-8)
        
        return (final_density * 255).astype(np.uint8)

    def traffic_entropy_analysis(self, vehicles, quantum_flow, frame):
        """交通熵分析"""
        analysis = {}
        
        # 基本交通参数
        analysis['vehicle_count'] = len(vehicles)
        analysis['total_vehicle_area'] = sum(v['area'] for v in vehicles)
        
        # 交通密度计算
        if self.analysis_region:
            region_area = (self.analysis_region[2] - self.analysis_region[0]) * \
                         (self.analysis_region[3] - self.analysis_region[1])
            analysis['traffic_density'] = analysis['total_vehicle_area'] / region_area
        else:
            analysis['traffic_density'] = 0
        
        # 速度分析
        if vehicles:
            analysis['average_velocity'] = np.mean([v['velocity'] for v in vehicles])
            analysis['velocity_variance'] = np.var([v['velocity'] for v in vehicles])
        else:
            analysis['average_velocity'] = 0
            analysis['velocity_variance'] = 0
        
        # 香农熵（交通复杂度）
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        analysis['shannon_entropy'] = self.calculate_shannon_entropy(gray)
        
        # 量子熵（交通流相干性）
        analysis['quantum_entropy'] = self.calculate_quantum_entropy(quantum_flow)
        
        # 互信息（交通相关性）
        if hasattr(self, 'prev_quantum_flow'):
            analysis['mutual_information'] = self.calculate_mutual_information(
                quantum_flow, self.prev_quantum_flow)
        else:
            analysis['mutual_information'] = 0
        
        self.prev_quantum_flow = quantum_flow.copy()
        
        # 拥堵指数
        analysis['congestion_index'] = self.calculate_congestion_index(analysis)
        
        # 事故风险预测
        analysis['accident_risk'] = self.predict_accident_risk(analysis)
        
        return analysis

    def calculate_shannon_entropy(self, data):
        """计算香农熵"""
        histogram, _ = np.histogram(data, bins=256, range=(0, 255))
        prob = histogram / histogram.sum()
        prob = prob[prob > 0]
        return -np.sum(prob * np.log2(prob))

    def calculate_quantum_entropy(self, quantum_flow):
        """计算量子熵（简化版）"""
        # 使用概率分布的方差作为熵的度量
        normalized_flow = quantum_flow.astype(np.float32) / 255.0
        return np.var(normalized_flow)

    def calculate_mutual_information(self, data1, data2):
        """计算互信息"""
        hist_2d, _, _ = np.histogram2d(data1.flatten(), data2.flatten(), bins=32)
        prob_2d = hist_2d / hist_2d.sum()
        
        # 边缘分布
        prob1 = np.sum(prob_2d, axis=1)
        prob2 = np.sum(prob_2d, axis=0)
        
        # 互信息计算
        mi = 0
        for i in range(prob_2d.shape[0]):
            for j in range(prob_2d.shape[1]):
                if prob_2d[i, j] > 0 and prob1[i] > 0 and prob2[j] > 0:
                    mi += prob_2d[i, j] * np.log2(prob_2d[i, j] / (prob1[i] * prob2[j]))
        
        return mi

    def calculate_congestion_index(self, analysis):
        """计算交通拥堵指数"""
        density_weight = 0.4
        velocity_weight = 0.3
        entropy_weight = 0.3
        
        # 归一化参数（基于经验值）
        normalized_density = min(analysis['traffic_density'] * 1000, 1.0)
        normalized_velocity = max(0, 1 - analysis['average_velocity'])
        normalized_entropy = min(analysis['shannon_entropy'] / 8, 1.0)  # 假设最大熵为8
        
        congestion = (density_weight * normalized_density +
                     velocity_weight * normalized_velocity +
                     entropy_weight * normalized_entropy)
        
        return min(congestion, 1.0)

    def predict_accident_risk(self, analysis):
        """预测事故风险"""
        # 基于多个指标的简单风险评估
        risk_factors = []
        
        # 高密度风险
        if analysis['traffic_density'] > 0.3:
            risk_factors.append(0.4)
        
        # 速度差异风险
        if analysis['velocity_variance'] > 0.1:
            risk_factors.append(0.3)
        
        # 熵异常风险
        if analysis['shannon_entropy'] > 7.0:
            risk_factors.append(0.2)
        
        # 量子相干性风险
        if analysis['quantum_entropy'] < 0.01:
            risk_factors.append(0.1)
        
        if risk_factors:
            return min(sum(risk_factors), 1.0)
        else:
            return 0.05  # 基础风险

    def traffic_state_prediction(self, current_analysis):
        """交通状态预测"""
        # 保存当前状态
        state_vector = [
            current_analysis['traffic_density'],
            current_analysis['average_velocity'],
            current_analysis['congestion_index'],
            current_analysis['shannon_entropy']
        ]
        
        self.traffic_state_history.append(state_vector)
        self.entropy_history.append(current_analysis['shannon_entropy'])
        
        # 简单线性预测（实际应用中可以使用LSTM等模型）
        if len(self.traffic_state_history) >= 10:
            # 基于最近状态的趋势预测
            recent_states = list(self.traffic_state_history)[-10:]
            trends = []
            
            for i in range(len(state_vector)):
                values = [state[i] for state in recent_states]
                # 计算趋势（简单差分）
                if len(values) >= 2:
                    trend = values[-1] - values[0]
                    trends.append(trend)
                else:
                    trends.append(0)
            
            # 预测下一状态
            prediction = [
                current_analysis['traffic_density'] + trends[0] * 0.5,
                max(0, current_analysis['average_velocity'] + trends[1] * 0.3),
                min(1.0, max(0, current_analysis['congestion_index'] + trends[2] * 0.5)),
                current_analysis['shannon_entropy'] + trends[3] * 0.2
            ]
            
            self.flow_prediction.append(prediction)
            return prediction
        else:
            return state_vector  # 历史数据不足，返回当前状态

    def anomaly_detection(self, analysis):
        """异常交通模式检测"""
        features = [
            analysis['traffic_density'],
            analysis['average_velocity'],
            analysis['congestion_index'],
            analysis['shannon_entropy']
        ]
        
        self.anomaly_scores.append(features)
        
        if len(self.anomaly_scores) >= 20:
            # 使用隔离森林检测异常
            try:
                scores_array = np.array(self.anomaly_scores)
                anomaly_labels = self.anomaly_detector.fit_predict(scores_array)
                
                # 最新点是否为异常
                is_anomaly = anomaly_labels[-1] == -1
                anomaly_score = np.mean(self.anomaly_detector.decision_function(scores_array[-5:]))
                
                return is_anomaly, anomaly_score
            except:
                return False, 0.0
        else:
            return False, 0.0

    def create_traffic_visualization(self, frame, vehicles, E_field, B_field, 
                                   quantum_flow, analysis, prediction, anomaly_info):
        """创建交通可视化界面"""
        height, width = frame.shape[:2]
        
        # 创建综合显示面板
        display = np.zeros((height, width * 2, 3), dtype=np.uint8)
        
        # 左侧：原始视频和车辆检测
        left_panel = frame.copy()
        
        # 绘制检测到的车辆
        for vehicle in vehicles:
            x, y = vehicle['position']
            w, h = vehicle['size']
            cv2.rectangle(left_panel, (x-w//2, y-h//2), (x+w//2, y+h//2), (0, 255, 0), 2)
            cv2.putText(left_panel, f"v:{vehicle['velocity']:.2f}", 
                       (x-w//2, y-h//2-10), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
        
        # 叠加量子流场
        quantum_colored = cv2.applyColorMap(quantum_flow, cv2.COLORMAP_JET)
        alpha = 0.3
        left_panel = cv2.addWeighted(left_panel, 1-alpha, quantum_colored, alpha, 0)
        
        # 右侧：分析和预测信息
        right_panel = np.zeros((height, width, 3), dtype=np.uint8)
        
        # 显示交通分析结果
        self.display_traffic_analysis(right_panel, analysis, prediction, anomaly_info)
        
        # 绘制实时图表
        self.draw_traffic_charts(right_panel, height - 300)
        
        # 合并面板
        display[:, :width] = left_panel
        display[:, width:] = right_panel
        
        return display

    def display_traffic_analysis(self, panel, analysis, prediction, anomaly_info):
        """显示交通分析结果"""
        y_offset = 30
        cv2.putText(panel, "Quantum Traffic Analysis", (10, y_offset), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        y_offset += 40
        
        # 基本交通参数
        traffic_params = [
            f"Vehicles: {analysis['vehicle_count']}",
            f"Density: {analysis['traffic_density']:.3f}",
            f"Avg Velocity: {analysis['average_velocity']:.2f}",
            f"Velocity Var: {analysis['velocity_variance']:.3f}",
            f"Congestion: {analysis['congestion_index']:.2f}",
            f"Accident Risk: {analysis['accident_risk']:.2f}"
        ]
        
        for param in traffic_params:
            cv2.putText(panel, param, (10, y_offset), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
            y_offset += 20
        
        y_offset += 10
        
        # 熵分析参数
        entropy_params = [
            f"Shannon Entropy: {analysis['shannon_entropy']:.3f}",
            f"Quantum Entropy: {analysis['quantum_entropy']:.3f}",
            f"Mutual Info: {analysis['mutual_information']:.3f}"
        ]
        
        for param in entropy_params:
            cv2.putText(panel, param, (10, y_offset), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 100), 1)
            y_offset += 20
        
        y_offset += 10
        
        # 预测信息
        if prediction:
            prediction_params = [
                f"Pred Density: {prediction[0]:.3f}",
                f"Pred Velocity: {prediction[1]:.2f}",
                f"Pred Congestion: {prediction[2]:.2f}"
            ]
            
            for param in prediction_params:
                cv2.putText(panel, param, (10, y_offset), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, (100, 255, 100), 1)
                y_offset += 20
        
        # 异常检测
        is_anomaly, anomaly_score = anomaly_info
        anomaly_color = (0, 0, 255) if is_anomaly else (100, 100, 100)
        cv2.putText(panel, f"Anomaly: {is_anomaly} (score: {anomaly_score:.3f})", 
                   (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.4, anomaly_color, 1)

    def draw_traffic_charts(self, panel, start_y):
        """绘制交通数据图表"""
        if len(self.traffic_state_history) < 2:
            return
        
        plot_height = 250
        plot_width = panel.shape[1] - 20
        
        if start_y + plot_height > panel.shape[0]:
            return
        
        # 创建绘图区域
        plot_area = np.zeros((plot_height, plot_width, 3), dtype=np.uint8)
        
        # 提取历史数据
        densities = [state[0] for state in self.traffic_state_history]
        velocities = [state[1] for state in self.traffic_state_history]
        congestion = [state[2] for state in self.traffic_state_history]
        entropies = list(self.entropy_history)
        
        # 归一化数据到绘图范围
        def normalize_to_plot(data, height):
            if len(data) == 0:
                return []
            data_array = np.array(data)
            if np.max(data_array) - np.min(data_array) > 0:
                normalized = (data_array - np.min(data_array)) / (np.max(data_array) - np.min(data_array))
                return (height - normalized * height * 0.8).astype(int)
            return np.ones_like(data_array) * (height // 2)
        
        # 绘制密度曲线（红色）
        density_plot = normalize_to_plot(densities, plot_height)
        for i in range(1, len(density_plot)):
            x1 = int((i-1) * plot_width / max(1, len(density_plot)-1))  # 避免除以零
            y1 = int(density_plot[i-1])
            x2 = int(i * plot_width / max(1, len(density_plot)-1))      # 避免除以零
            y2 = int(density_plot[i])
            
            # 确保坐标在图像范围内
            x1 = max(0, min(x1, plot_width-1))
            y1 = max(0, min(y1, plot_height-1))
            x2 = max(0, min(x2, plot_width-1))
            y2 = max(0, min(y2, plot_height-1))
            
            cv2.line(plot_area, (x1, y1), (x2, y2), (0, 0, 255), 1)
        
        # 绘制速度曲线（绿色）
        velocity_plot = normalize_to_plot(velocities, plot_height)
        for i in range(1, len(velocity_plot)):
            x1 = int((i-1) * plot_width / max(1, len(velocity_plot)-1))
            y1 = int(velocity_plot[i-1])
            x2 = int(i * plot_width / max(1, len(velocity_plot)-1))
            y2 = int(velocity_plot[i])
            
            x1 = max(0, min(x1, plot_width-1))
            y1 = max(0, min(y1, plot_height-1))
            x2 = max(0, min(x2, plot_width-1))
            y2 = max(0, min(y2, plot_height-1))
            
            cv2.line(plot_area, (x1, y1), (x2, y2), (0, 255, 0), 1)
        
        # 绘制拥堵曲线（黄色）
        congestion_plot = normalize_to_plot(congestion, plot_height)
        for i in range(1, len(congestion_plot)):
            x1 = int((i-1) * plot_width / max(1, len(congestion_plot)-1))
            y1 = int(congestion_plot[i-1])
            x2 = int(i * plot_width / max(1, len(congestion_plot)-1))
            y2 = int(congestion_plot[i])
            
            x1 = max(0, min(x1, plot_width-1))
            y1 = max(0, min(y1, plot_height-1))
            x2 = max(0, min(x2, plot_width-1))
            y2 = max(0, min(y2, plot_height-1))
            
            cv2.line(plot_area, (x1, y1), (x2, y2), (0, 255, 255), 1)
        
        # 添加图例
        cv2.putText(plot_area, "Density", (5, 15), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.3, (0, 0, 255), 1)
        cv2.putText(plot_area, "Velocity", (5, 30), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.3, (0, 255, 0), 1)
        cv2.putText(plot_area, "Congestion", (5, 45), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.3, (0, 255, 255), 1)
        
        # 添加到面板
        panel[start_y:start_y+plot_height, 10:10+plot_width] = plot_area

    def run_traffic_analysis(self):
        """运行交通分析系统"""
        if not self.initialize_camera():
            return
        
        self.is_running = True
        
        print("量子交通场感知系统启动...")
        print("控制按键:")
        print("  'q': 退出系统")
        print("  'r': 重置分析区域")
        print("  's': 保存当前状态")
        
        while self.is_running:
            ret, frame = self.cap.read()
            if not ret:
                print("无法读取帧，尝试重新初始化...")
                break
            
            self.frame_count += 1
            
            # 设置分析区域（首次运行）
            if self.analysis_region is None:
                self.setup_analysis_regions(frame)
            
            # 降低处理频率以保证实时性
            if self.frame_count % self.process_every_n_frames != 0:
                # 显示当前帧（不处理）
                cv2.imshow('Quantum Traffic Analysis', frame)
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    break
                continue
            
            # 车辆检测
            vehicles, motion_mask = self.vehicle_detection_quantum(frame)
            
            # 交通电磁场计算
            E_field, B_field = self.traffic_electromagnetic_field(vehicles)
            
            # 量子交通流模拟
            quantum_flow = self.quantum_traffic_flow(frame, vehicles, E_field, B_field)
            
            # 交通熵分析
            traffic_analysis = self.traffic_entropy_analysis(vehicles, quantum_flow, frame)
            
            # 交通状态预测
            state_prediction = self.traffic_state_prediction(traffic_analysis)
            
            # 异常检测
            anomaly_info = self.anomaly_detection(traffic_analysis)
            
            # 创建可视化
            display_frame = self.create_traffic_visualization(
                frame, vehicles, E_field, B_field, quantum_flow, 
                traffic_analysis, state_prediction, anomaly_info
            )
            
            # 显示结果
            cv2.imshow('Quantum Traffic Analysis', display_frame)
            
            # 键盘控制
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('r'):
                self.setup_analysis_regions(frame)
                print("分析区域已重置")
            elif key == ord('s'):
                self.save_traffic_data(traffic_analysis)
        
        self.cleanup()

    def save_traffic_data(self, analysis):
        """保存交通数据"""
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        filename = f"traffic_data_{timestamp}.txt"
        
        with open(filename, 'w') as f:
            f.write("Traffic Analysis Data\n")
            f.write("=====================\n")
            for key, value in analysis.items():
                f.write(f"{key}: {value}\n")
        
        print(f"交通数据已保存到: {filename}")

    def cleanup(self):
        """清理资源"""
        if self.cap:
            self.cap.release()
        cv2.destroyAllWindows()
        self.is_running = False
        print("交通分析系统已停止")

# 使用示例和测试代码
def main():
    """主函数"""
    print("量子交通场感知系统")
    print("=================")
    
    # 创建交通分析器
    traffic_analyzer = TrafficQuantumFieldSensor(camera_index=0)
    
    try:
        # 运行分析系统
        traffic_analyzer.run_traffic_analysis()
    except KeyboardInterrupt:
        print("\n用户中断系统")
    except Exception as e:
        print(f"系统运行错误: {e}")
    finally:
        traffic_analyzer.cleanup()

if __name__ == "__main__":
    main()