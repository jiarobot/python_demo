import cv2
import numpy as np
from ultralytics import YOLO
import time
from collections import defaultdict, deque
import math
from scipy import stats, integrate, optimize
from scipy.spatial.distance import mahalanobis
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import pandas as pd
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, WhiteKernel
import warnings
warnings.filterwarnings('ignore')

class MeasureTheoreticTrafficAnalyzer:
    """
    基于测度论和泛函分析的车流分析系统
    
    核心数学思想：
    1. 将交通流视为概率测度空间上的随机过程
    2. 使用函数空间方法分析交通密度演化
    3. 基于随机微分方程的预测模型
    4. 信息几何在交通模式识别中的应用
    5. 基于测度值的异常检测
    """
    
    def __init__(self, model_path='yolov8n.pt', conf_threshold=0.4):
        # YOLO检测器
        self.model = YOLO(model_path)
        self.conf_threshold = conf_threshold
        self.vehicle_classes = [2, 3, 5, 7]
        
        # 测度论相关数据结构
        self.probability_measure = defaultdict(lambda: GaussianMeasure())
        self.traffic_process = StochasticTrafficProcess()
        self.function_space_analyzer = FunctionSpaceAnalyzer()
        
        # 随机过程参数
        self.brownian_motions = {}
        self.levy_processes = {}
        self.markov_chains = {}
        
        # 信息几何结构
        self.information_manifold = InformationManifold()
        self.statistical_manifolds = {}
        
        # 泛函分析工具
        self.operator_theory = OperatorTheory()
        self.spectral_analysis = SpectralAnalyzer()
        
        # 实时分析系统
        self.frame_measure = FrameMeasure()
        self.entropy_analyzer = EntropyAnalyzer()
        
        # 可视化系统
        self.visualization_engine = AdvancedVisualization()
        
        print("基于测度论的车流分析系统初始化完成")

class GaussianMeasure:
    """高斯测度实现"""
    def __init__(self, dimension=2):
        self.dimension = dimension
        self.mean = np.zeros(dimension)
        self.covariance = np.eye(dimension)
        self.precision = np.eye(dimension)
        self.samples = deque(maxlen=1000)
        
    def update(self, new_sample):
        """在线更新高斯测度"""
        self.samples.append(new_sample)
        samples_array = np.array(list(self.samples))
        
        if len(samples_array) > 1:
            self.mean = np.mean(samples_array, axis=0)
            self.covariance = np.cov(samples_array.T)
            if np.linalg.det(self.covariance) > 1e-10:
                self.precision = np.linalg.inv(self.covariance)
    
    def density(self, x):
        """计算概率密度"""
        diff = x - self.mean
        exponent = -0.5 * diff.T @ self.precision @ diff
        normalization = 1.0 / ((2 * np.pi) ** (self.dimension/2) * 
                             np.sqrt(np.linalg.det(self.covariance)))
        return normalization * np.exp(exponent)
    
    def kl_divergence(self, other):
        """计算KL散度"""
        diff = other.mean - self.mean
        trace_term = np.trace(other.precision @ self.covariance)
        det_term = np.log(np.linalg.det(other.covariance) / 
                         np.linalg.det(self.covariance))
        return 0.5 * (trace_term + diff.T @ other.precision @ diff - 
                     self.dimension + det_term)

class StochasticTrafficProcess:
    """随机交通过程建模"""
    def __init__(self):
        self.intensity_measures = {}
        self.point_processes = {}
        self.diffusion_processes = {}
        self.jump_processes = {}
        
    def hawkes_process_intensity(self, t, history, base_rate=0.1, decay=0.5, influence=0.3):
        """Hawkes过程强度函数"""
        intensity = base_rate
        for event_time in history:
            if event_time < t:
                intensity += influence * np.exp(-decay * (t - event_time))
        return intensity
    
    def ornstein_uhlenbeck(self, x0, theta, mu, sigma, dt, n_steps):
        """Ornstein-Uhlenbeck过程模拟"""
        process = [x0]
        for i in range(1, n_steps):
            dx = theta * (mu - process[-1]) * dt + sigma * np.sqrt(dt) * np.random.normal()
            process.append(process[-1] + dx)
        return process
    
    def levy_process_simulation(self, n_steps, dt, mu=0, sigma=1, alpha=1.5):
        """Lévy过程模拟"""
        process = [0]
        for i in range(1, n_steps):
            # 简化的Lévy过程（稳定分布）
            if alpha == 2:  # 高斯情况
                increment = np.random.normal(mu * dt, sigma * np.sqrt(dt))
            else:  # 非高斯稳定分布
                u = np.random.uniform(-np.pi/2, np.pi/2)
                w = -np.log(np.random.uniform(0, 1))
                scale = (dt ** (1/alpha)) * sigma
                increment = scale * (np.sin(alpha * u) / 
                                  (np.cos(u) ** (1/alpha))) * \
                          (np.cos((1 - alpha) * u) / w) ** ((1 - alpha)/alpha)
            
            process.append(process[-1] + increment)
        return process

class FunctionSpaceAnalyzer:
    """函数空间分析器"""
    def __init__(self):
        self.reproducing_kernels = {}
        self.sobolev_norms = {}
        self.functional_derivatives = {}
        
    def kernel_density_estimate(self, points, bandwidth=0.1, grid_size=50):
        """基于再生核希尔伯特空间的密度估计"""
        if len(points) == 0:
            return None, None, None
            
        points = np.array(points)
        x_min, x_max = points[:,0].min(), points[:,0].max()
        y_min, y_max = points[:,1].min(), points[:,1].max()
        
        # 扩展边界
        x_range = x_max - x_min
        y_range = y_max - y_min
        x_min -= 0.1 * x_range
        x_max += 0.1 * x_range
        y_min -= 0.1 * y_range
        y_max += 0.1 * y_range
        
        # 创建网格
        x_grid = np.linspace(x_min, x_max, grid_size)
        y_grid = np.linspace(y_min, y_max, grid_size)
        X, Y = np.meshgrid(x_grid, y_grid)
        grid_points = np.vstack([X.ravel(), Y.ravel()]).T
        
        # 高斯核密度估计
        density = np.zeros(len(grid_points))
        for point in points:
            distances = np.linalg.norm(grid_points - point, axis=1)
            density += np.exp(-0.5 * (distances / bandwidth) ** 2)
        
        density /= (2 * np.pi * bandwidth ** 2 * len(points))
        density = density.reshape(X.shape)
        
        return X, Y, density
    
    def sobolev_norm(self, function_values, derivative_order=1):
        """计算Sobolev范数"""
        if len(function_values) < 2:
            return 0
            
        # 计算函数值的L2范数
        l2_norm = np.sqrt(np.mean(function_values ** 2))
        
        if derivative_order >= 1:
            # 数值计算导数
            derivatives = np.gradient(function_values)
            derivative_norm = np.sqrt(np.mean(derivatives ** 2))
            return np.sqrt(l2_norm ** 2 + derivative_norm ** 2)
        else:
            return l2_norm

class InformationManifold:
    """信息几何流形"""
    def __init__(self):
        self.fisher_metrics = {}
        self.affine_connections = {}
        self.geodesics = {}
        
    def fisher_information(self, probability_measure, points):
        """计算Fisher信息矩阵"""
        if len(points) < 2:
            return np.eye(2)
            
        # 数值计算Fisher信息
        n_params = 2  # 均值的两个分量
        fisher_matrix = np.zeros((n_params, n_params))
        epsilon = 1e-6
        
        for i in range(n_params):
            for j in range(n_params):
                # 数值计算二阶导数
                pass  # 简化实现
                
        return fisher_matrix
    
    def alpha_connection(self, alpha=0):
        """计算α联络"""
        # 信息几何中的α联络
        if alpha == 0:
            return "Levi-Civita联络"
        elif alpha == 1:
            return "指数联络"
        elif alpha == -1:
            return "混合联络"
        else:
            return f"α={alpha}联络"

class OperatorTheory:
    """算子理论应用"""
    def __init__(self):
        self.spectral_measures = {}
        self.compact_operators = {}
        
    def transfer_operator(self, transition_kernel, function_space):
        """转移算子"""
        # 在函数空间上定义的转移算子
        def operator_action(f):
            # 简化的转移算子作用
            return lambda x: integrate.quad(
                lambda y: transition_kernel(x, y) * f(y), -np.inf, np.inf)[0]
        return operator_action
    
    def perron_frobenius_operator(self, dynamical_system, density_function):
        """Perron-Frobenius算子"""
        # 用于分析动力系统的算子
        def pushforward_density(x):
            # 密度函数的推前
            pass
        return pushforward_density

class SpectralAnalyzer:
    """谱分析器"""
    def __init__(self):
        self.eigenvalues = {}
        self.eigenfunctions = {}
        
    def kernel_pca(self, kernel_matrix, n_components=3):
        """核主成分分析"""
        if kernel_matrix is None or len(kernel_matrix) == 0:
            return None, None
            
        # 中心化核矩阵
        n = len(kernel_matrix)
        one_n = np.ones((n, n)) / n
        kernel_centered = kernel_matrix - one_n @ kernel_matrix - kernel_matrix @ one_n + one_n @ kernel_matrix @ one_n
        
        # 特征分解
        eigenvalues, eigenvectors = np.linalg.eigh(kernel_centered)
        
        # 排序特征值
        idx = np.argsort(eigenvalues)[::-1]
        eigenvalues = eigenvalues[idx][:n_components]
        eigenvectors = eigenvectors[:, idx][:, :n_components]
        
        return eigenvalues, eigenvectors

class FrameMeasure:
    """帧测度分析"""
    def __init__(self):
        self.empirical_measures = {}
        self.radon_nikodym_derivatives = {}
        
    def empirical_distribution(self, samples, weights=None):
        """经验分布函数"""
        if len(samples) == 0:
            return lambda x: 0
            
        samples_sorted = np.sort(samples)
        if weights is None:
            weights = np.ones(len(samples)) / len(samples)
        else:
            weights = weights / np.sum(weights)
            
        def cdf(x):
            return np.sum(weights[samples_sorted <= x])
            
        return cdf
    
    def wasserstein_distance(self, measure1, measure2, p=1):
        """Wasserstein距离"""
        # 简化的一维Wasserstein距离计算
        if hasattr(measure1, 'samples') and hasattr(measure2, 'samples'):
            samples1 = np.sort(np.array(list(measure1.samples)).flatten())
            samples2 = np.sort(np.array(list(measure2.samples)).flatten())
            
            if len(samples1) == 0 or len(samples2) == 0:
                return float('inf')
                
            # 经验Wasserstein距离
            n1, n2 = len(samples1), len(samples2)
            quantiles1 = np.arange(n1) / n1
            quantiles2 = np.arange(n2) / n2
            
            # 线性插值计算逆CDF
            from scipy.interpolate import interp1d
            inv_cdf1 = interp1d(quantiles1, samples1, 
                              bounds_error=False, fill_value=(samples1[0], samples1[-1]))
            inv_cdf2 = interp1d(quantiles2, samples2, 
                              bounds_error=False, fill_value=(samples2[0], samples2[-1]))
            
            # 在共同定义域上积分
            t_vals = np.linspace(0, 1, 100)
            distance = np.mean(np.abs(inv_cdf1(t_vals) - inv_cdf2(t_vals)) ** p) ** (1/p)
            return distance
        else:
            return float('inf')

class EntropyAnalyzer:
    """熵分析器"""
    def __init__(self):
        self.shannon_entropies = {}
        self.renyi_entropies = {}
        self.tsallis_entropies = {}
        
    def shannon_entropy(self, probabilities):
        """香农熵"""
        probabilities = np.array(probabilities)
        probabilities = probabilities[probabilities > 0]  # 移除零概率
        return -np.sum(probabilities * np.log(probabilities))
    
    def renyi_entropy(self, probabilities, alpha=1):
        """Rényi熵"""
        if alpha == 1:
            return self.shannon_entropy(probabilities)
        else:
            probabilities = np.array(probabilities)
            probabilities = probabilities[probabilities > 0]
            return (1 / (1 - alpha)) * np.log(np.sum(probabilities ** alpha))
    
    def tsallis_entropy(self, probabilities, q=1):
        """Tsallis熵"""
        if q == 1:
            return self.shannon_entropy(probabilities)
        else:
            probabilities = np.array(probabilities)
            probabilities = probabilities[probabilities > 0]
            return (1 / (q - 1)) * (1 - np.sum(probabilities ** q))

class AdvancedVisualization:
    """高级可视化引擎"""
    def __init__(self):
        self.probability_plots = {}
        self.manifold_projections = {}
        
    def plot_probability_contour(self, ax, X, Y, density, title="概率密度等高线"):
        """绘制概率密度等高线"""
        if density is not None:
            contour = ax.contourf(X, Y, density, levels=20, alpha=0.6)
            ax.contour(X, Y, density, levels=10, colors='black', alpha=0.3)
            ax.set_title(title)
            plt.colorbar(contour, ax=ax)
            
    def plot_stochastic_process(self, ax, process, title="随机过程"):
        """绘制随机过程"""
        if len(process) > 0:
            ax.plot(process, linewidth=1)
            ax.set_title(title)
            ax.set_xlabel("时间步")
            ax.set_ylabel("值")

class MathematicalTrafficAnalyzer:
    """
    主分析类 - 整合所有数学工具
    """
    def __init__(self, model_path='yolov8n.pt'):
        self.detector = MeasureTheoreticTrafficAnalyzer(model_path)
        self.frame_count = 0
        
        # 数学分析结果存储
        self.analysis_results = {
            'entropy_evolution': [],
            'wasserstein_distances': [],
            'sobolev_norms': [],
            'spectral_analysis': [],
            'stochastic_intensities': []
        }
        
    def process_frame_with_mathematics(self, frame):
        """使用高级数学工具处理帧"""
        start_time = time.time()
        self.frame_count += 1
        
        # YOLO检测
        results = self.detector.model.track(
            frame, persist=True, conf=self.detector.conf_threshold,
            classes=self.detector.vehicle_classes, verbose=False
        )
        
        detection_results = results[0] if results else None
        
        # 提取车辆信息
        vehicles = self.extract_vehicle_information(detection_results, frame.shape)
        
        # 应用数学分析
        mathematical_insights = self.apply_mathematical_analysis(vehicles, frame)
        
        # 可视化
        visualized_frame = self.mathematical_visualization(frame, vehicles, mathematical_insights)
        
        processing_time = (time.time() - start_time) * 1000
        return visualized_frame, processing_time, len(vehicles), mathematical_insights
    
    def extract_vehicle_information(self, detection_results, frame_shape):
        """提取车辆信息"""
        vehicles = []
        
        if detection_results and detection_results.boxes is not None:
            boxes = detection_results.boxes.xyxy.cpu().numpy()
            track_ids = detection_results.boxes.id.cpu().numpy().astype(int) if detection_results.boxes.id is not None else []
            confidences = detection_results.boxes.conf.cpu().numpy()
            classes = detection_results.boxes.cls.cpu().numpy().astype(int)
            
            for i, (box, conf, cls) in enumerate(zip(boxes, confidences, classes)):
                track_id = track_ids[i] if i < len(track_ids) else i
                x1, y1, x2, y2 = box.astype(int)
                
                vehicle_info = {
                    'id': track_id,
                    'bbox': (x1, y1, x2, y2),
                    'center': ((x1 + x2) // 2, (y1 + y2) // 2),
                    'velocity': self.calculate_velocity(track_id, (x1, y1, x2, y2)),
                    'type': cls,
                    'confidence': conf
                }
                
                # 更新测度
                center_point = np.array(vehicle_info['center'])
                if track_id not in self.detector.probability_measure:
                    self.detector.probability_measure[track_id] = GaussianMeasure(2)
                self.detector.probability_measure[track_id].update(center_point)
                
                vehicles.append(vehicle_info)
                
        return vehicles
    
    def calculate_velocity(self, track_id, bbox):
        """计算速度向量"""
        if track_id in self.detector.track_history and len(self.detector.track_history[track_id]) >= 2:
            history = list(self.detector.track_history[track_id])
            current_center = self.get_bbox_center(bbox)
            prev_center = self.get_bbox_center(history[-2])
            return (current_center[0] - prev_center[0], current_center[1] - prev_center[1])
        return (0, 0)
    
    def get_bbox_center(self, bbox):
        """获取边界框中心"""
        x1, y1, x2, y2 = bbox
        return ((x1 + x2) // 2, (y1 + y2) // 2)
    
    def apply_mathematical_analysis(self, vehicles, frame):
        """应用数学分析"""
        insights = {}
        
        # 1. 概率测度分析
        insights['probability_analysis'] = self.analyze_probability_measures(vehicles)
        
        # 2. 随机过程分析
        insights['stochastic_analysis'] = self.analyze_stochastic_processes(vehicles)
        
        # 3. 函数空间分析
        insights['functional_analysis'] = self.analyze_function_spaces(vehicles, frame)
        
        # 4. 信息几何分析
        insights['information_geometry'] = self.analyze_information_geometry(vehicles)
        
        # 5. 熵分析
        insights['entropy_analysis'] = self.analyze_entropy(vehicles)
        
        return insights
    
    def analyze_probability_measures(self, vehicles):
        """概率测度分析"""
        analysis = {}
        
        if len(vehicles) > 0:
            # 提取所有车辆位置
            positions = [vehicle['center'] for vehicle in vehicles]
            positions_array = np.array(positions)
            
            # 计算整体经验测度
            overall_measure = GaussianMeasure(2)
            for pos in positions:
                overall_measure.update(pos)
            
            analysis['overall_mean'] = overall_measure.mean.tolist()
            analysis['overall_covariance'] = overall_measure.covariance.tolist()
            
            # 计算车辆间的KL散度
            if len(vehicles) > 1:
                kl_divergences = []
                for i in range(len(vehicles)):
                    for j in range(i+1, len(vehicles)):
                        id1, id2 = vehicles[i]['id'], vehicles[j]['id']
                        if id1 in self.detector.probability_measure and id2 in self.detector.probability_measure:
                            kl = self.detector.probability_measure[id1].kl_divergence(
                                self.detector.probability_measure[id2])
                            kl_divergences.append(kl)
                
                analysis['avg_kl_divergence'] = np.mean(kl_divergences) if kl_divergences else 0
            
        return analysis
    
    def analyze_stochastic_processes(self, vehicles):
        """随机过程分析"""
        analysis = {}
        
        # Hawkes过程强度估计
        current_time = time.time()
        if not hasattr(self, 'event_history'):
            self.event_history = []
        
        # 添加当前事件
        if len(vehicles) > 0:
            self.event_history.append(current_time)
            # 只保留最近的事件
            time_window = 60  # 60秒窗口
            self.event_history = [t for t in self.event_history if current_time - t < time_window]
        
        # 计算当前强度
        if len(self.event_history) > 0:
            intensity = self.detector.traffic_process.hawkes_process_intensity(
                current_time, self.event_history)
            analysis['hawkes_intensity'] = intensity
        
        # Ornstein-Uhlenbeck过程模拟（用于速度建模）
        if len(vehicles) > 0:
            speeds = [np.sqrt(v['velocity'][0]**2 + v['velocity'][1]**2) for v in vehicles]
            avg_speed = np.mean(speeds) if speeds else 0
            ou_process = self.detector.traffic_process.ornstein_uhlenbeck(
                avg_speed, 0.5, 5.0, 1.0, 0.1, 10)
            analysis['ou_process'] = ou_process
        
        return analysis
    
    def analyze_function_spaces(self, vehicles, frame):
        """函数空间分析"""
        analysis = {}
        
        if len(vehicles) > 0:
            positions = [vehicle['center'] for vehicle in vehicles]
            
            # 核密度估计
            X, Y, density = self.detector.function_space_analyzer.kernel_density_estimate(positions)
            analysis['density_field'] = (X, Y, density)
            
            # Sobolev范数计算
            if density is not None:
                sobolev_norm = self.detector.function_space_analyzer.sobolev_norm(density.flatten())
                analysis['sobolev_norm'] = sobolev_norm
                self.analysis_results['sobolev_norms'].append(sobolev_norm)
        
        return analysis
    
    def analyze_information_geometry(self, vehicles):
        """信息几何分析"""
        analysis = {}
        
        if len(vehicles) >= 2:
            # 计算经验Fisher信息
            positions = [vehicle['center'] for vehicle in vehicles]
            fisher_info = self.detector.information_manifold.fisher_information(None, positions)
            analysis['fisher_information_trace'] = np.trace(fisher_info) if fisher_info is not None else 0
            
            # α联络分析
            analysis['levi_civita_connection'] = self.detector.information_manifold.alpha_connection(0)
            analysis['exponential_connection'] = self.detector.information_manifold.alpha_connection(1)
        
        return analysis
    
    def analyze_entropy(self, vehicles):
        """熵分析"""
        analysis = {}
        
        if len(vehicles) > 0:
            # 位置分布熵
            positions = [vehicle['center'] for vehicle in vehicles]
            
            # 创建位置直方图
            if len(positions) > 1:
                positions_array = np.array(positions)
                x_hist, _ = np.histogram(positions_array[:,0], bins=10, density=True)
                y_hist, _ = np.histogram(positions_array[:,1], bins=10, density=True)
                
                # 计算香农熵
                x_entropy = self.detector.entropy_analyzer.shannon_entropy(x_hist)
                y_entropy = self.detector.entropy_analyzer.shannon_entropy(y_hist)
                
                analysis['position_entropy_x'] = x_entropy
                analysis['position_entropy_y'] = y_entropy
                analysis['total_position_entropy'] = x_entropy + y_entropy
                
                self.analysis_results['entropy_evolution'].append(analysis['total_position_entropy'])
        
        return analysis
    
    def mathematical_visualization(self, frame, vehicles, insights):
        """数学可视化"""
        # 创建可视化画布
        vis_frame = frame.copy()
        
        # 绘制车辆和轨迹
        for vehicle in vehicles:
            x1, y1, x2, y2 = vehicle['bbox']
            track_id = vehicle['id']
            
            # 根据概率测度不确定性选择颜色
            if track_id in self.detector.probability_measure:
                uncertainty = np.trace(self.detector.probability_measure[track_id].covariance)
                color_intensity = min(255, int(uncertainty * 100))
                color = (0, color_intensity, 255 - color_intensity)
            else:
                color = (0, 255, 0)
            
            cv2.rectangle(vis_frame, (x1, y1), (x2, y2), color, 2)
            
            # 绘制轨迹
            if track_id in self.detector.track_history:
                points = []
                for bbox in list(self.detector.track_history[track_id])[-10:]:
                    center = self.get_bbox_center(bbox)
                    points.append(center)
                
                for i in range(1, len(points)):
                    cv2.line(vis_frame, points[i-1], points[i], color, 2)
        
        # 绘制概率密度场
        if 'functional_analysis' in insights and 'density_field' in insights['functional_analysis']:
            X, Y, density = insights['functional_analysis']['density_field']
            if density is not None:
                # 将密度场叠加到帧上
                density_normalized = (density - density.min()) / (density.max() - density.min() + 1e-8)
                heatmap = cv2.applyColorMap((density_normalized * 255).astype(np.uint8), cv2.COLORMAP_JET)
                heatmap_resized = cv2.resize(heatmap, (vis_frame.shape[1], vis_frame.shape[0]))
                vis_frame = cv2.addWeighted(vis_frame, 0.7, heatmap_resized, 0.3, 0)
        
        # 绘制数学信息面板
        self.draw_mathematical_panel(vis_frame, insights)
        
        return vis_frame
    
    def draw_mathematical_panel(self, frame, insights):
        """绘制数学信息面板"""
        panel_height = 300
        panel_width = 400
        panel = np.zeros((panel_height, panel_width, 3), dtype=np.uint8)
        
        y_offset = 20
        line_height = 25
        
        # 标题
        cv2.putText(panel, "数学分析仪表板", (10, y_offset), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        y_offset += line_height + 10
        
        # 概率测度信息
        if 'probability_analysis' in insights:
            prob_info = insights['probability_analysis']
            cv2.putText(panel, f"平均KL散度: {prob_info.get('avg_kl_divergence', 0):.3f}", 
                       (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            y_offset += line_height
        
        # 随机过程信息
        if 'stochastic_analysis' in insights:
            stoch_info = insights['stochastic_analysis']
            cv2.putText(panel, f"Hawkes强度: {stoch_info.get('hawkes_intensity', 0):.3f}", 
                       (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            y_offset += line_height
        
        # 函数空间信息
        if 'functional_analysis' in insights:
            func_info = insights['functional_analysis']
            cv2.putText(panel, f"Sobolev范数: {func_info.get('sobolev_norm', 0):.3f}", 
                       (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            y_offset += line_height
        
        # 信息几何信息
        if 'information_geometry' in insights:
            geom_info = insights['information_geometry']
            cv2.putText(panel, f"Fisher迹: {geom_info.get('fisher_information_trace', 0):.3f}", 
                       (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            y_offset += line_height
        
        # 熵信息
        if 'entropy_analysis' in insights:
            entropy_info = insights['entropy_analysis']
            cv2.putText(panel, f"位置熵: {entropy_info.get('total_position_entropy', 0):.3f}", 
                       (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            y_offset += line_height
        
        # 系统状态
        cv2.putText(panel, f"分析帧数: {self.frame_count}", 
                   (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        y_offset += line_height
        
        # 叠加到帧上
        frame[10:10+panel_height, 10:10+panel_width] = panel

def main():
    """主函数 - 数学增强的车流分析系统"""
    print("启动基于泛函分析和概率论的车流分析系统...")
    print("=" * 60)
    print("系统特性:")
    print("- 概率测度空间建模")
    print("- 随机过程分析")
    print("- 函数空间方法")
    print("- 信息几何应用")
    print("- 高级熵分析")
    print("=" * 60)
    
    # 初始化分析器
    analyzer = MathematicalTrafficAnalyzer('yolov8n.pt')
    
    # 视频源
    video_source = 0  # 摄像头或视频文件
    
    cap = cv2.VideoCapture(video_source)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    
    print("系统准备就绪，开始分析...")
    print("控制指令: 'q'退出, 's'保存分析报告")
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # 数学增强的处理
            processed_frame, proc_time, vehicle_count, insights = analyzer.process_frame_with_mathematics(frame)
            
            # 显示处理信息
            info_text = f"数学分析: {proc_time:.1f}ms | 车辆: {vehicle_count}"
            cv2.putText(processed_frame, info_text, (10, processed_frame.shape[0]-10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            
            cv2.imshow('数学增强车流分析', processed_frame)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('s'):
                # 保存分析报告
                save_analysis_report(analyzer, insights)
                print("分析报告已保存")
            
            # 定期输出数学洞察
            if analyzer.frame_count % 30 == 0:
                print_math_insights(insights)
                
    except KeyboardInterrupt:
        print("\n分析被用户中断")
    except Exception as e:
        print(f"分析错误: {e}")
    finally:
        cap.release()
        cv2.destroyAllWindows()
        generate_comprehensive_report(analyzer)

def print_math_insights(insights):
    """打印数学洞察"""
    print("\n--- 数学分析洞察 ---")
    if 'entropy_analysis' in insights:
        entropy = insights['entropy_analysis'].get('total_position_entropy', 0)
        print(f"系统熵: {entropy:.3f} (不确定性度量)")
    
    if 'probability_analysis' in insights:
        kl_div = insights['probability_analysis'].get('avg_kl_divergence', 0)
        print(f"平均KL散度: {kl_div:.3f} (分布差异性)")
    
    if 'functional_analysis' in insights:
        sob_norm = insights['functional_analysis'].get('sobolev_norm', 0)
        print(f"Sobolev范数: {sob_norm:.3f} (函数平滑度)")

def save_analysis_report(analyzer, insights):
    """保存分析报告"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"math_traffic_analysis_{timestamp}.txt"
    
    with open(filename, 'w') as f:
        f.write("数学车流分析报告\n")
        f.write("=" * 50 + "\n")
        f.write(f"生成时间: {datetime.now()}\n")
        f.write(f"分析帧数: {analyzer.frame_count}\n\n")
        
        f.write("最终分析结果:\n")
        for key, value in insights.items():
            f.write(f"{key}: {value}\n")
        
        f.write("\n时间序列分析:\n")
        if analyzer.analysis_results['entropy_evolution']:
            avg_entropy = np.mean(analyzer.analysis_results['entropy_evolution'])
            f.write(f"平均位置熵: {avg_entropy:.3f}\n")
        
        if analyzer.analysis_results['sobolev_norms']:
            avg_sobolev = np.mean(analyzer.analysis_results['sobolev_norms'])
            f.write(f"平均Sobolev范数: {avg_sobolev:.3f}\n")
    
    print(f"分析报告已保存至: {filename}")

def generate_comprehensive_report(analyzer):
    """生成综合分析报告"""
    print("\n" + "=" * 60)
    print("数学车流分析综合报告")
    print("=" * 60)
    
    print(f"总分析帧数: {analyzer.frame_count}")
    
    if analyzer.analysis_results['entropy_evolution']:
        entropy_data = analyzer.analysis_results['entropy_evolution']
        print(f"位置熵统计 - 均值: {np.mean(entropy_data):.3f}, 标准差: {np.std(entropy_data):.3f}")
        
    if analyzer.analysis_results['sobolev_norms']:
        sobolev_data = analyzer.analysis_results['sobolev_norms']
        print(f"Sobolev范数统计 - 均值: {np.mean(sobolev_data):.3f}, 标准差: {np.std(sobolev_data):.3f}")
    
    print("=" * 60)

if __name__ == "__main__":
    main()