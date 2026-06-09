import numpy as np
import matplotlib
matplotlib.rc("font", family='Microsoft YaHei')
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
from sklearn.metrics.pairwise import euclidean_distances
from sklearn.decomposition import PCA
import time
from collections import defaultdict, deque
import warnings
import itertools
from scipy.spatial.distance import cdist
from scipy.stats import entropy
import seaborn as sns
from sklearn.metrics import silhouette_score, calinski_harabasz_score

warnings.filterwarnings('ignore')

class AdvancedProjectedStreamingCoreset:
    """
    增强版的基于随机投影的在线流数据核心集构建算法
    支持多种核心集构建策略和自适应参数调整
    """
    
    def __init__(self, target_coreset_size, target_k, epsilon_jl=0.1, delta_jl=0.01, 
                 max_stream_size=100000, projection_type='gaussian', 
                 coreset_strategy='weighted', adaptive=True, 
                 memory_size=1000, random_state=42):
        """
        初始化参数
        
        Parameters:
        -----------
        target_coreset_size : int
            目标核心集大小
        target_k : int
            目标聚类数(k-means中的k)
        epsilon_jl : float
            JL投影的失真度参数
        delta_jl : float
            JL投影失败概率上限
        max_stream_size : int
            预估的最大流数据量
        projection_type : str
            投影类型: 'gaussian', 'sparse', 或 'rff' (随机傅里叶特征)
        coreset_strategy : str
            核心集构建策略: 'uniform', 'weighted', 'sensitivity', 'merge'
        adaptive : bool
            是否启用自适应参数调整
        memory_size : int
            用于统计分析的滑动窗口大小
        random_state : int
            随机种子
        """
        self.target_coreset_size = target_coreset_size
        self.target_k = target_k
        self.epsilon_jl = epsilon_jl
        self.delta_jl = delta_jl
        self.max_stream_size = max_stream_size
        self.projection_type = projection_type
        self.coreset_strategy = coreset_strategy
        self.adaptive = adaptive
        self.memory_size = memory_size
        self.random_state = random_state
        np.random.seed(random_state)
        
        # 将在第一次数据到达时初始化的参数
        self.original_dim = None
        self.projection_dim = None
        self.projection_matrix = None
        self.coreset_points = None
        self.coreset_weights = None
        self.coreset_sensitivities = None
        self.points_processed = 0
        self.cluster_centers = None
        self.cluster_labels = None
        
        # 自适应参数
        self.recent_points = deque(maxlen=memory_size)
        self.dimensionality_estimate = None
        self.data_variance = None
        self.learning_rate = 0.01
        
        # 统计信息
        self.history = {
            'costs': [],
            'approx_ratios': [],
            'coreset_sizes': [],
            'dimensionality_estimates': [],
            'timestamps': []
        }
        
    def _compute_projection_dimension(self):
        """计算JL投影的目标维度"""
        # 使用更精确的维度估计公式
        constant = 4.0 / (self.epsilon_jl**2 - self.epsilon_jl**3/3)
        k_jl = int(np.ceil(constant * np.log(self.max_stream_size / self.delta_jl)))
        
        # 如果启用了自适应，根据数据特性调整维度
        if self.adaptive and self.dimensionality_estimate is not None:
            # 考虑数据的内在维度
            adjusted_dim = int(k_jl * (self.dimensionality_estimate / self.original_dim))
            return max(2, min(k_jl, adjusted_dim))
        
        return max(2, k_jl)
    
    def _estimate_dimensionality(self, points):
        """估计数据的固有维度"""
        if len(points) < 10:
            return len(points[0]) if points else self.original_dim
            
        # 使用最近邻方法估计固有维度
        try:
            distances = []
            for i in range(min(100, len(points))):
                point = points[i]
                other_points = [p for j, p in enumerate(points) if j != i]
                if other_points:
                    dist = np.min([np.linalg.norm(point - p) for p in other_points])
                    distances.append(dist)
            
            if len(distances) > 1:
                # 简单的固有维度估计
                mean_dist = np.mean(distances)
                std_dist = np.std(distances)
                if mean_dist > 0:
                    dim_estimate = (mean_dist ** 2) / (2 * std_dist ** 2)
                    return max(1, min(self.original_dim, dim_estimate))
        except:
            pass
            
        return self.original_dim
    
    def _generate_projection_matrix(self, original_dim):
        """生成随机投影矩阵"""
        if self.projection_type == 'gaussian':
            # 高斯随机矩阵
            matrix = np.random.randn(self.projection_dim, original_dim) / np.sqrt(self.projection_dim)
        elif self.projection_type == 'sparse':
            # 稀疏Achlioptas矩阵
            s = 3
            matrix = np.zeros((self.projection_dim, original_dim))
            
            for i in range(self.projection_dim):
                for j in range(original_dim):
                    r = np.random.random()
                    if r < 1/(2*s):
                        matrix[i, j] = np.sqrt(s)
                    elif r < 1/s:
                        matrix[i, j] = -np.sqrt(s)
            matrix /= np.sqrt(self.projection_dim)
        elif self.projection_type == 'rff':
            # 随机傅里叶特征（用于核方法近似）
            # 这里简化为另一种随机投影
            scale = 1.0 / np.sqrt(self.projection_dim)
            matrix = np.random.randn(self.projection_dim, original_dim) * scale
        else:
            raise ValueError("projection_type必须是'gaussian', 'sparse'或'rff'")
            
        return matrix
    
    def _initialize_coreset_algorithm(self):
        """初始化核心集构造算法"""
        self.coreset_points = []
        self.coreset_weights = []
        self.coreset_sensitivities = []
    
    def _ensure_projection_dimension(self, point):
        """确保投影维度合理，避免维度爆炸"""
        max_reasonable_dim = min(1000, self.original_dim * 2)  # 设置合理上限
        if self.projection_dim > max_reasonable_dim:
            print(f"警告: 投影维度 {self.projection_dim} 过大，调整为 {max_reasonable_dim}")
            self.projection_dim = max_reasonable_dim
            self.projection_matrix = self._generate_projection_matrix(self.original_dim)
    
    def _project_point(self, point):
        """将数据点投影到低维空间"""
        projected = self.projection_matrix @ point
        return np.asarray(projected).flatten()  # 确保返回一维数组
    
    def _compute_sensitivity(self, point, centers):
        """计算点的敏感性（对聚类成本的影响）"""
        if centers is None or len(centers) == 0:
            return 1.0
            
        try:
            distances = euclidean_distances([point], centers)[0]
            min_distance = np.min(distances)
            
            # 简化的敏感性计算
            if len(self.coreset_points) > 0:
                coreset_array = np.array(self.coreset_points)
                coreset_distances = euclidean_distances(coreset_array, centers)
                coreset_min_distances = np.min(coreset_distances, axis=1)
                avg_core_distance = np.mean(coreset_min_distances)
                
                if avg_core_distance > 0:
                    sensitivity = min_distance / avg_core_distance
                    return min(10.0, max(0.1, sensitivity))
            
            return 1.0
        except Exception as e:
            print(f"计算敏感性时出错: {e}")
            return 1.0
    
    def _uniform_coreset_update(self, projected_point):
        """均匀采样核心集更新策略"""
        if len(self.coreset_points) < self.target_coreset_size:
            self.coreset_points.append(projected_point)
            self.coreset_weights.append(1)
            self.coreset_sensitivities.append(1.0)
        else:
            # 随机替换
            replace_idx = np.random.randint(0, self.target_coreset_size)
            self.coreset_points[replace_idx] = projected_point
            self.coreset_weights[replace_idx] = 1
            self.coreset_sensitivities[replace_idx] = 1.0
    
    def _weighted_coreset_update(self, projected_point):
        """基于权重的核心集更新策略"""
        sensitivity = self._compute_sensitivity(projected_point, self.cluster_centers)
        
        if len(self.coreset_points) < self.target_coreset_size:
            self.coreset_points.append(projected_point)
            self.coreset_weights.append(sensitivity)
            self.coreset_sensitivities.append(sensitivity)
        else:
            # 基于敏感性权重的替换策略
            if len(self.coreset_weights) > 0:
                weights = np.array(self.coreset_weights)
                if np.sum(weights) > 0:
                    replace_prob = 1 - (weights / np.sum(weights))
                    replace_idx = np.random.choice(len(self.coreset_points), p=replace_prob)
                    
                    self.coreset_points[replace_idx] = projected_point
                    self.coreset_weights[replace_idx] = sensitivity
                    self.coreset_sensitivities[replace_idx] = sensitivity
    
    def _sensitivity_coreset_update(self, projected_point):
        """基于敏感性的核心集更新策略"""
        sensitivity = self._compute_sensitivity(projected_point, self.cluster_centers)
        
        if len(self.coreset_points) < self.target_coreset_size:
            self.coreset_points.append(projected_point)
            self.coreset_weights.append(1)
            self.coreset_sensitivities.append(sensitivity)
        else:
            # 替换敏感性最低的点
            min_sens_idx = np.argmin(self.coreset_sensitivities)
            min_sensitivity = self.coreset_sensitivities[min_sens_idx]
            
            if sensitivity > min_sensitivity:
                self.coreset_points[min_sens_idx] = projected_point
                self.coreset_weights[min_sens_idx] = 1
                self.coreset_sensitivities[min_sens_idx] = sensitivity
    
    def _merge_coreset_update(self, projected_point):
        """基于合并的核心集更新策略"""
        if len(self.coreset_points) < self.target_coreset_size:
            self.coreset_points.append(projected_point)
            self.coreset_weights.append(1)
            self.coreset_sensitivities.append(1.0)
        else:
            # 找到最近的核心集点进行合并
            coreset_array = np.array(self.coreset_points)
            distances = euclidean_distances([projected_point], coreset_array)[0]
            nearest_idx = np.argmin(distances)
            
            # 合并点（加权平均）
            weight_old = self.coreset_weights[nearest_idx]
            weight_new = 1
            
            merged_point = (weight_old * self.coreset_points[nearest_idx] + 
                          weight_new * projected_point) / (weight_old + weight_new)
            
            self.coreset_points[nearest_idx] = merged_point
            self.coreset_weights[nearest_idx] = weight_old + weight_new
    
    def _online_coreset_update(self, projected_point):
        """在线更新核心集 - 根据策略选择更新方法"""
        if self.coreset_strategy == 'uniform':
            self._uniform_coreset_update(projected_point)
        elif self.coreset_strategy == 'weighted':
            self._weighted_coreset_update(projected_point)
        elif self.coreset_strategy == 'sensitivity':
            self._sensitivity_coreset_update(projected_point)
        elif self.coreset_strategy == 'merge':
            self._merge_coreset_update(projected_point)
        else:
            raise ValueError(f"未知的核心集策略: {self.coreset_strategy}")
    
    def _update_cluster_centers(self):
        """在核心集上更新聚类中心"""
        if (len(self.coreset_points) >= self.target_k and 
            len(self.coreset_points) > 0):
            try:
                # 确保所有核心集点具有相同的维度
                coreset_array = np.array(self.coreset_points)
                
                # 检查维度一致性
                if coreset_array.ndim != 2:
                    print(f"警告: 核心集数组维度异常: {coreset_array.shape}")
                    return
                
                weights_array = np.array(self.coreset_weights)
                
                # 使用加权k-means
                kmeans = KMeans(n_clusters=self.target_k, random_state=self.random_state)
                kmeans.fit(coreset_array, sample_weight=weights_array)
                self.cluster_centers = kmeans.cluster_centers_
                self.cluster_labels = kmeans.labels_
            except Exception as e:
                print(f"更新聚类中心时出错: {e}")
    
    def _adaptive_parameter_update(self):
        """自适应参数更新"""
        if len(self.recent_points) < 10:
            return
            
        recent_array = np.array(list(self.recent_points))
        
        # 更新维度估计
        self.dimensionality_estimate = self._estimate_dimensionality(recent_array)
        
        # 更新数据方差估计
        self.data_variance = np.mean(np.var(recent_array, axis=0))
        
        # 根据数据特性调整投影维度
        if self.adaptive:
            new_projection_dim = self._compute_projection_dimension()
            if new_projection_dim != self.projection_dim:
                # 重新生成投影矩阵（在实际应用中需要更复杂的处理）
                self.projection_dim = new_projection_dim
                self.projection_matrix = self._generate_projection_matrix(self.original_dim)
    
    def process_point(self, point):
        """
        处理单个数据点
        
        Parameters:
        -----------
        point : array-like
            输入数据点
        """
        point = np.array(point).flatten()
        
        # 如果是第一个点，初始化参数
        if self.original_dim is None:
            self.original_dim = len(point)
            self.projection_dim = self._compute_projection_dimension()
            self._ensure_projection_dimension(point)  # 确保维度合理
            self.projection_matrix = self._generate_projection_matrix(self.original_dim)
            self._initialize_coreset_algorithm()
            print(f"初始化: 原始维度={self.original_dim}, 投影维度={self.projection_dim}")
        
        # 1. 随机投影
        projected_point = self._project_point(point)
        
        # 2. 在线核心集更新
        self._online_coreset_update(projected_point)
        
        # 3. 更新最近点缓存
        self.recent_points.append(point)
        
        # 4. 定期更新聚类中心和自适应参数
        self.points_processed += 1
        if self.points_processed % 100 == 0:
            self._update_cluster_centers()
            if self.adaptive:
                self._adaptive_parameter_update()
            
            # 记录统计信息
            self._record_statistics()
    
    def process_stream(self, data_stream, batch_size=1000):
        """
        处理数据流
        
        Parameters:
        -----------
        data_stream : iterable
            数据流迭代器
        batch_size : int
            批处理大小
        """
        batch = []
        for i, point in enumerate(data_stream):
            batch.append(point)
            
            if len(batch) >= batch_size:
                for p in batch:
                    self.process_point(p)
                batch = []
                
                # 每批处理完打印进度
                print(f"已处理 {i + 1} 个数据点，当前核心集大小: {len(self.coreset_points)}")
        
        # 处理剩余的点
        for p in batch:
            self.process_point(p)
    
    def _record_statistics(self):
        """记录算法运行统计信息"""
        current_time = time.time()
        
        # 计算当前代价 - 添加安全检查
        if (self.cluster_centers is not None and 
            len(self.recent_points) > 0 and 
            len(self.cluster_centers) > 0):
            try:
                recent_array = np.array(list(self.recent_points))
                projected_recent = recent_array @ self.projection_matrix.T
                
                # 确保维度匹配
                if projected_recent.shape[1] == self.cluster_centers.shape[1]:
                    distances = euclidean_distances(projected_recent, self.cluster_centers)
                    current_cost = np.sum(np.min(distances, axis=1)**2)
                    self.history['costs'].append(current_cost)
                else:
                    self.history['costs'].append(0)
                    print(f"维度不匹配: 投影数据 {projected_recent.shape}, 聚类中心 {self.cluster_centers.shape}")
            except Exception as e:
                print(f"计算代价时出错: {e}")
                self.history['costs'].append(0)
        else:
            self.history['costs'].append(0)
        
        # 记录其他统计信息
        self.history['coreset_sizes'].append(len(self.coreset_points))
        self.history['dimensionality_estimates'].append(self.dimensionality_estimate or self.original_dim)
        self.history['timestamps'].append(current_time)
    
    def get_coreset(self):
        """获取当前核心集（投影空间）"""
        if len(self.coreset_points) == 0:
            return np.array([]), np.array([])
        return np.array(self.coreset_points), np.array(self.coreset_weights)
    
    def get_cluster_centers_lowdim(self):
        """获取低维空间的聚类中心"""
        return self.cluster_centers
    
    def inverse_project_centers(self):
        """
        将聚类中心逆投影回原始空间（近似解）
        """
        if self.cluster_centers is None:
            return None
            
        A_pinv = np.linalg.pinv(self.projection_matrix)
        original_centers = A_pinv @ self.cluster_centers.T
        return original_centers.T
    
    def evaluate_approximation_quality(self, test_data, true_centers=None, true_labels=None):
        """
        全面评估核心集近似的质量
        
        Parameters:
        -----------
        test_data : array-like
            测试数据集
        true_centers : array-like, optional
            真实聚类中心
        true_labels : array-like, optional
            真实聚类标签
        """
        test_data = np.array(test_data)
        
        if self.cluster_centers is None:
            print("尚未计算聚类中心")
            return {}
        
        # 将测试数据投影到低维空间
        projected_test = test_data @ self.projection_matrix.T
        
        # 确保维度匹配
        if projected_test.shape[1] != self.cluster_centers.shape[1]:
            print(f"维度不匹配: 测试数据投影后 {projected_test.shape}, 聚类中心 {self.cluster_centers.shape}")
            return {}
        
        # 在低维空间计算测试数据到核心集聚类中心的距离
        lowdim_distances = euclidean_distances(projected_test, self.cluster_centers)
        lowdim_labels = np.argmin(lowdim_distances, axis=1)
        lowdim_cost = np.sum(np.min(lowdim_distances, axis=1)**2)
        
        metrics = {
            'lowdim_cost': lowdim_cost,
            'coreset_size': len(self.coreset_points),
            'projection_dim': self.projection_dim
        }
        
        # 如果有真实中心，计算真实代价和近似比率
        if true_centers is not None:
            true_distances = euclidean_distances(test_data, true_centers)
            true_cost = np.sum(np.min(true_distances, axis=1)**2)
            approximation_ratio = lowdim_cost / true_cost if true_cost > 0 else float('inf')
            
            metrics.update({
                'true_cost': true_cost,
                'approximation_ratio': approximation_ratio,
                'cost_difference': abs(lowdim_cost - true_cost)
            })
            
            print(f"真实k-means代价: {true_cost:.4f}")
            print(f"核心集近似代价: {lowdim_cost:.4f}")
            print(f"近似比率: {approximation_ratio:.4f}")
            print(f"代价差异: {abs(lowdim_cost - true_cost):.4f}")
        
        # 计算聚类质量指标
        if true_labels is not None:
            from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score
            
            ari = adjusted_rand_score(true_labels, lowdim_labels)
            nmi = normalized_mutual_info_score(true_labels, lowdim_labels)
            
            metrics.update({
                'ari': ari,
                'nmi': nmi
            })
            
            print(f"调整兰德指数 (ARI): {ari:.4f}")
            print(f"标准化互信息 (NMI): {nmi:.4f}")
        
        # 计算轮廓系数和Calinski-Harabasz指数
        if len(set(lowdim_labels)) > 1:
            try:
                silhouette_avg = silhouette_score(projected_test, lowdim_labels)
                calinski_harabasz = calinski_harabasz_score(projected_test, lowdim_labels)
                
                metrics.update({
                    'silhouette_score': silhouette_avg,
                    'calinski_harabasz_score': calinski_harabasz
                })
                
                print(f"轮廓系数: {silhouette_avg:.4f}")
                print(f"Calinski-Harabasz指数: {calinski_harabasz:.4f}")
            except Exception as e:
                print(f"计算聚类质量指标时出错: {e}")
        
        return metrics
    
    def plot_statistics(self):
        """绘制算法运行统计信息"""
        if len(self.history['timestamps']) < 2:
            print("统计信息不足，无法绘图")
            return
        
        # 计算相对时间
        start_time = self.history['timestamps'][0]
        relative_times = [t - start_time for t in self.history['timestamps']]
        
        fig, axes = plt.subplots(2, 3, figsize=(18, 10))
        
        # 子图1: 代价变化
        if self.history['costs']:
            axes[0, 0].plot(relative_times, self.history['costs'], 'b-', alpha=0.7)
            axes[0, 0].set_xlabel('时间 (秒)')
            axes[0, 0].set_ylabel('聚类代价')
            axes[0, 0].set_title('聚类代价变化')
            axes[0, 0].grid(True, alpha=0.3)
        
        # 子图2: 核心集大小
        axes[0, 1].plot(relative_times, self.history['coreset_sizes'], 'g-', alpha=0.7)
        axes[0, 1].axhline(y=self.target_coreset_size, color='r', linestyle='--', label='目标大小')
        axes[0, 1].set_xlabel('时间 (秒)')
        axes[0, 1].set_ylabel('核心集大小')
        axes[0, 1].set_title('核心集大小变化')
        axes[0, 1].legend()
        axes[0, 1].grid(True, alpha=0.3)
        
        # 子图3: 维度估计
        axes[0, 2].plot(relative_times, self.history['dimensionality_estimates'], 'purple', alpha=0.7)
        axes[0, 2].axhline(y=self.original_dim, color='r', linestyle='--', label='原始维度')
        axes[0, 2].set_xlabel('时间 (秒)')
        axes[0, 2].set_ylabel('估计维度')
        axes[0, 2].set_title('数据固有维度估计')
        axes[0, 2].legend()
        axes[0, 2].grid(True, alpha=0.3)
        
        # 子图4: 处理速度
        if len(relative_times) > 1:
            processing_speeds = []
            for i in range(1, len(relative_times)):
                time_diff = relative_times[i] - relative_times[i-1]
                points_processed = 100  # 假设每100个点记录一次
                speed = points_processed / time_diff if time_diff > 0 else 0
                processing_speeds.append(speed)
            
            axes[1, 0].plot(relative_times[1:], processing_speeds, 'orange', alpha=0.7)
            axes[1, 0].set_xlabel('时间 (秒)')
            axes[1, 0].set_ylabel('处理速度 (点/秒)')
            axes[1, 0].set_title('数据流处理速度')
            axes[1, 0].grid(True, alpha=0.3)
        
        # 子图5: 内存使用估计
        memory_usage = [size * self.projection_dim * 8 / 1024 for size in self.history['coreset_sizes']]  # 估计内存使用 (KB)
        axes[1, 1].plot(relative_times, memory_usage, 'brown', alpha=0.7)
        axes[1, 1].set_xlabel('时间 (秒)')
        axes[1, 1].set_ylabel('内存使用 (KB)')
        axes[1, 1].set_title('核心集内存使用')
        axes[1, 1].grid(True, alpha=0.3)
        
        # 子图6: 投影误差估计
        if len(self.recent_points) > 10:
            projection_errors = []
            for t_idx in range(len(relative_times)):
                if t_idx < len(self.history['dimensionality_estimates']):
                    dim_est = self.history['dimensionality_estimates'][t_idx]
                    if dim_est > 0:
                        error_est = 1 - (min(self.projection_dim, dim_est) / max(self.projection_dim, dim_est))
                        projection_errors.append(error_est)
            
            if projection_errors:
                axes[1, 2].plot(relative_times[:len(projection_errors)], projection_errors, 'red', alpha=0.7)
                axes[1, 2].set_xlabel('时间 (秒)')
                axes[1, 2].set_ylabel('投影误差估计')
                axes[1, 2].set_title('投影误差变化')
                axes[1, 2].grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.show()

# 简化演示函数
def simple_demo():
    """简化演示增强版投影流式核心集算法"""
    print("=" * 70)
    print("增强版投影流式核心集算法演示")
    print("=" * 70)
    
    # 生成更简单的模拟数据
    np.random.seed(42)
    
    # 参数设置 - 使用更小的数据测试
    n_samples = 500
    original_dim = 20   # 进一步减少维度
    target_k = 3
    target_coreset_size = 30
    
    print(f"生成 {n_samples} 个 {original_dim} 维数据点...")
    
    # 生成3个簇
    centers = np.array([
        [2.0] * 5 + [0.0] * 15,
        [-2.0] * 10 + [1.0] * 10, 
        [0.0] * 15 + [-1.0] * 5
    ])
    
    # 调整中心点维度
    centers = centers[:, :original_dim]
    
    cluster_sizes = [200, 150, 150]
    
    data_stream = []
    true_labels = []
    
    for i, (center, size) in enumerate(zip(centers, cluster_sizes)):
        cluster_data = np.random.normal(0, 1, (size, original_dim)) + center
        data_stream.extend(cluster_data)
        true_labels.extend([i] * size)
    
    # 打乱数据
    indices = np.random.permutation(n_samples)
    data_stream = [data_stream[i] for i in indices]
    true_labels = [true_labels[i] for i in indices]
    
    print("数据生成完成!")
    
    # 计算真实k-means结果作为基准
    print("\n计算真实k-means结果作为基准...")
    start_time = time.time()
    true_kmeans = KMeans(n_clusters=target_k, random_state=42)
    true_kmeans.fit(data_stream)
    true_centers = true_kmeans.cluster_centers_
    true_time = time.time() - start_time
    print(f"真实k-means计算时间: {true_time:.4f}秒")
    
    # 测试uniform策略
    strategy = 'uniform'
    print(f"\n{'='*50}")
    print(f"测试策略: {strategy}")
    print(f"{'='*50}")
    
    # 初始化算法 - 使用更保守的参数
    apsc = AdvancedProjectedStreamingCoreset(
        target_coreset_size=target_coreset_size,
        target_k=target_k,
        epsilon_jl=0.3,  # 增大epsilon以减少投影维度
        delta_jl=0.05,   # 增大delta以减少投影维度
        max_stream_size=n_samples,
        projection_type='gaussian',
        coreset_strategy=strategy,
        adaptive=False,   # 先禁用自适应
        memory_size=200,
        random_state=42
    )
    
    # 处理数据流
    start_time = time.time()
    apsc.process_stream(data_stream, batch_size=50)
    stream_time = time.time() - start_time
    
    # 最终更新
    apsc._update_cluster_centers()
    
    print(f"\n策略 '{strategy}' 完成!")
    print(f"处理时间: {stream_time:.4f}秒")
    if true_time > 0:
        print(f"加速比: {true_time/stream_time:.2f}x")
    
    # 评估质量
    metrics = apsc.evaluate_approximation_quality(
        data_stream, true_centers, true_labels
    )
    
    # 显示统计图表
    apsc.plot_statistics()
    
    return apsc, metrics

if __name__ == "__main__":
    # 运行简化演示
    results, metrics = simple_demo()
    
    print("\n演示完成!")