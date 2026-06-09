import numpy as np
import matplotlib
matplotlib.rc("font", family='Microsoft YaHei')
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
from sklearn.metrics.pairwise import euclidean_distances
import time
from collections import defaultdict
import warnings
warnings.filterwarnings('ignore')

class ProjectedStreamingCoreset:
    """
    基于随机投影的在线流数据核心集构建算法
    专门针对k-means聚类问题
    """
    
    def __init__(self, target_coreset_size, target_k, epsilon_jl=0.1, delta_jl=0.01, 
                 max_stream_size=100000, projection_type='gaussian', random_state=42):
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
            投影类型: 'gaussian' 或 'sparse'
        random_state : int
            随机种子
        """
        self.target_coreset_size = target_coreset_size
        self.target_k = target_k
        self.epsilon_jl = epsilon_jl
        self.delta_jl = delta_jl
        self.max_stream_size = max_stream_size
        self.projection_type = projection_type
        self.random_state = random_state
        np.random.seed(random_state)
        
        # 将在第一次数据到达时初始化的参数
        self.original_dim = None
        self.projection_dim = None
        self.projection_matrix = None
        self.coreset_points = None
        self.coreset_weights = None
        self.points_processed = 0
        self.cluster_centers = None
        
    def _compute_projection_dimension(self):
        """计算JL投影的目标维度"""
        # 根据JL引理计算所需维度
        # k = O(ε^(-2) * log(n/δ))
        constant = 4.0 / (self.epsilon_jl**2 - self.epsilon_jl**3/3)
        k_jl = int(np.ceil(constant * self.epsilon_jl**(-2) * 
                          np.log(self.max_stream_size / self.delta_jl)))
        return max(2, k_jl)  # 至少2维
    
    def _generate_projection_matrix(self, original_dim):
        """生成随机投影矩阵"""
        if self.projection_type == 'gaussian':
            # 高斯随机矩阵，元素来自 N(0, 1/sqrt(k))
            matrix = np.random.randn(self.projection_dim, original_dim) / np.sqrt(self.projection_dim)
        elif self.projection_type == 'sparse':
            # 稀疏Achlioptas矩阵，约1/3元素非零
            s = 3  # 稀疏参数
            matrix = np.zeros((self.projection_dim, original_dim))
            
            # 以概率1/(2s)取+sqrt(s)，1/(2s)取-sqrt(s)，1-1/s取0
            for i in range(self.projection_dim):
                for j in range(original_dim):
                    r = np.random.random()
                    if r < 1/(2*s):
                        matrix[i, j] = np.sqrt(s)
                    elif r < 1/s:
                        matrix[i, j] = -np.sqrt(s)
                    else:
                        matrix[i, j] = 0
            matrix /= np.sqrt(self.projection_dim)
        else:
            raise ValueError("projection_type必须是'gaussian'或'sparse'")
            
        return matrix
    
    def _initialize_online_coreset_algorithm(self):
        """初始化在线核心集构造算法"""
        # 使用简化的流式k-means++变体作为在线核心集构造器
        # 这里实现一个基于权重分配的简单版本
        self.coreset_points = []  # 存储投影后的核心集点
        self.coreset_weights = []  # 存储每个核心集点的权重
        self.cluster_centers = None  # 当前聚类中心
        
    def _project_point(self, point):
        """将数据点投影到低维空间"""
        return self.projection_matrix @ point
    
    def _online_coreset_update(self, projected_point):
        """在线更新核心集 - 简化的流式k-means++变体"""
        
        if len(self.coreset_points) < self.target_coreset_size:
            # 如果核心集还没满，直接添加
            self.coreset_points.append(projected_point)
            self.coreset_weights.append(1)
        else:
            # 核心集已满，需要决定是否替换
            if self.cluster_centers is None:
                # 如果还没有聚类中心，随机替换
                replace_idx = np.random.randint(0, self.target_coreset_size)
                self.coreset_points[replace_idx] = projected_point
                self.coreset_weights[replace_idx] = 1
            else:
                # 计算当前点到聚类中心的最近距离
                coreset_array = np.array(self.coreset_points)
                distances = euclidean_distances([projected_point], self.cluster_centers)
                min_distance = np.min(distances)
                
                # 计算核心集中所有点的最小距离
                coreset_distances = euclidean_distances(coreset_array, self.cluster_centers)
                coreset_min_distances = np.min(coreset_distances, axis=1)
                
                # 找到最小距离最小的点（最容易被代表）
                min_core_idx = np.argmin(coreset_min_distances)
                min_core_distance = coreset_min_distances[min_core_idx]
                
                # 如果新点比核心集中某个点更难被代表，则替换
                if min_distance > min_core_distance:
                    self.coreset_points[min_core_idx] = projected_point
                    self.coreset_weights[min_core_idx] = 1
    
    def _update_cluster_centers(self):
        """在核心集上更新聚类中心"""
        if len(self.coreset_points) >= self.target_k:
            coreset_array = np.array(self.coreset_points)
            weights_array = np.array(self.coreset_weights)
            
            # 使用加权k-means
            kmeans = KMeans(n_clusters=self.target_k, random_state=self.random_state)
            kmeans.fit(coreset_array, sample_weight=weights_array)
            self.cluster_centers = kmeans.cluster_centers_
    
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
            self.projection_matrix = self._generate_projection_matrix(self.original_dim)
            self._initialize_online_coreset_algorithm()
            print(f"初始化: 原始维度={self.original_dim}, 投影维度={self.projection_dim}")
        
        # 1. 随机投影
        projected_point = self._project_point(point)
        
        # 2. 在线核心集更新
        self._online_coreset_update(projected_point)
        
        # 3. 定期更新聚类中心（每100个点更新一次）
        self.points_processed += 1
        if self.points_processed % 100 == 0:
            self._update_cluster_centers()
    
    def process_stream(self, data_stream):
        """
        处理数据流
        
        Parameters:
        -----------
        data_stream : iterable
            数据流迭代器
        """
        for i, point in enumerate(data_stream):
            self.process_point(point)
            
            # 每1000个点打印进度
            if (i + 1) % 1000 == 0:
                print(f"已处理 {i + 1} 个数据点，当前核心集大小: {len(self.coreset_points)}")
    
    def get_coreset(self):
        """获取当前核心集（投影空间）"""
        return np.array(self.coreset_points), np.array(self.coreset_weights)
    
    def get_cluster_centers_lowdim(self):
        """获取低维空间的聚类中心"""
        return self.cluster_centers
    
    def inverse_project_centers(self):
        """
        将聚类中心逆投影回原始空间（近似解）
        使用最小二乘方法
        """
        if self.cluster_centers is None:
            return None
            
        # 使用伪逆进行逆投影: x ≈ A⁺ y
        A_pinv = np.linalg.pinv(self.projection_matrix)
        original_centers = A_pinv @ self.cluster_centers.T
        return original_centers.T
    
    def evaluate_approximation(self, test_data, true_centers=None):
        """
        评估核心集近似的质量
        
        Parameters:
        -----------
        test_data : array-like
            测试数据集
        true_centers : array-like, optional
            真实聚类中心（如果有的话）
        """
        test_data = np.array(test_data)
        
        if self.cluster_centers is None:
            print("尚未计算聚类中心")
            return
        
        # 将测试数据投影到低维空间
        projected_test = test_data @ self.projection_matrix.T
        
        # 在低维空间计算测试数据到核心集聚类中心的距离
        lowdim_distances = euclidean_distances(projected_test, self.cluster_centers)
        lowdim_cost = np.sum(np.min(lowdim_distances, axis=1)**2)
        
        # 如果有真实中心，计算真实代价
        if true_centers is not None:
            true_distances = euclidean_distances(test_data, true_centers)
            true_cost = np.sum(np.min(true_distances, axis=1)**2)
            approximation_ratio = lowdim_cost / true_cost
            print(f"真实k-means代价: {true_cost:.4f}")
            print(f"核心集近似代价: {lowdim_cost:.4f}")
            print(f"近似比率: {approximation_ratio:.4f}")
            return approximation_ratio
        else:
            print(f"核心集近似k-means代价: {lowdim_cost:.4f}")
            return lowdim_cost

# 演示和测试代码
def demo_projected_streaming_coreset():
    """演示投影流式核心集算法"""
    print("=" * 60)
    print("基于随机投影的在线流数据核心集构建算法演示")
    print("=" * 60)
    
    # 生成模拟高维数据流
    np.random.seed(42)
    
    # 参数设置
    n_samples = 5000  # 总样本数
    original_dim = 100  # 原始维度
    target_k = 3  # 聚类数
    target_coreset_size = 50  # 目标核心集大小
    
    print(f"生成 {n_samples} 个 {original_dim} 维数据点...")
    
    # 生成3个高维高斯簇
    centers = np.array([
        [1.0] * original_dim,
        [-1.0] * original_dim,
        [0.0] * original_dim
    ])
    
    # 添加一些噪声使中心不完全在直线上
    centers += np.random.normal(0, 0.5, centers.shape)
    
    # 生成数据
    cluster_sizes = [2000, 1500, 1500]
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
    print(f"数据形状: {len(data_stream)} 个样本, {original_dim} 维")
    
    # 计算真实k-means结果作为基准
    print("\n计算真实k-means结果作为基准...")
    start_time = time.time()
    true_kmeans = KMeans(n_clusters=target_k, random_state=42)
    true_kmeans.fit(data_stream)
    true_centers = true_kmeans.cluster_centers_
    true_cost = true_kmeans.inertia_
    true_time = time.time() - start_time
    print(f"真实k-means计算时间: {true_time:.4f}秒")
    print(f"真实k-means代价: {true_cost:.4f}")
    
    # 初始化投影流式核心集算法
    print(f"\n初始化投影流式核心集算法...")
    print(f"目标核心集大小: {target_coreset_size}")
    print(f"目标聚类数: {target_k}")
    
    psc = ProjectedStreamingCoreset(
        target_coreset_size=target_coreset_size,
        target_k=target_k,
        epsilon_jl=0.2,
        delta_jl=0.01,
        max_stream_size=n_samples,
        projection_type='gaussian',
        random_state=42
    )
    
    # 处理数据流
    print("\n开始处理数据流...")
    start_time = time.time()
    psc.process_stream(data_stream)
    stream_time = time.time() - start_time
    
    # 最终更新聚类中心
    psc._update_cluster_centers()
    
    print(f"\n流式处理完成!")
    print(f"流式处理时间: {stream_time:.4f}秒")
    print(f"加速比: {true_time/stream_time:.2f}x")
    
    # 获取结果
    coreset_points, coreset_weights = psc.get_coreset()
    lowdim_centers = psc.get_cluster_centers_lowdim()
    original_centers_approx = psc.inverse_project_centers()
    
    print(f"\n最终核心集大小: {len(coreset_points)}")
    print(f"核心集点维度: {coreset_points.shape[1]}")
    
    # 评估近似质量
    print("\n评估近似质量...")
    approximation_ratio = psc.evaluate_approximation(data_stream, true_centers)
    
    # 可视化结果（如果维度允许）
    if coreset_points.shape[1] >= 2:
        # 传递 psc 对象以便在可视化中使用投影矩阵
        visualize_results_with_fix(data_stream, true_labels, coreset_points, 
                                coreset_weights, lowdim_centers, original_centers_approx, psc)
    
    return psc, true_kmeans, approximation_ratio

def visualize_results_with_fix(data_stream, true_labels, coreset_points, coreset_weights, 
                              lowdim_centers, original_centers_approx, psc_obj):
    """修复后的可视化函数"""
    try:
        from sklearn.decomposition import PCA
        
        data_array = np.array(data_stream)
        
        # 将原始数据降到2D
        pca = PCA(n_components=2)
        data_2d = pca.fit_transform(data_array)
        
        # 将核心集数据逆投影到原始空间再降到2D
        if psc_obj.projection_matrix is not None:
            A_pinv = np.linalg.pinv(psc_obj.projection_matrix)
            coreset_original_approx = coreset_points @ A_pinv.T
            coreset_2d = pca.transform(coreset_original_approx)
        else:
            # 备用方案：直接对低维核心集进行PCA
            pca_core = PCA(n_components=2)
            coreset_2d = pca_core.fit_transform(coreset_points)
        
        # 处理聚类中心
        if lowdim_centers is not None and original_centers_approx is not None:
            lowdim_centers_2d = pca.transform(original_centers_approx)
        elif lowdim_centers is not None:
            pca_center = PCA(n_components=2)
            lowdim_centers_2d = pca_center.fit_transform(lowdim_centers)
        else:
            lowdim_centers_2d = None
        
        plt.figure(figsize=(15, 5))
        
        # 子图1: 原始数据
        plt.subplot(1, 3, 1)
        scatter = plt.scatter(data_2d[:, 0], data_2d[:, 1], c=true_labels, 
                             alpha=0.6, cmap='viridis', s=10)
        plt.title('原始数据 (PCA降维)')
        plt.colorbar(scatter)
        
        # 子图2: 核心集
        plt.subplot(1, 3, 2)
        sizes = np.array(coreset_weights) * 100 + 10
        plt.scatter(coreset_2d[:, 0], coreset_2d[:, 1], c='red', 
                   s=sizes, alpha=0.7, edgecolors='black', label='核心集点')
        if lowdim_centers_2d is not None:
            plt.scatter(lowdim_centers_2d[:, 0], lowdim_centers_2d[:, 1], 
                       c='blue', marker='X', s=200, label='聚类中心')
        plt.title('核心集表示')
        plt.legend()
        
        # 子图3: 比较
        plt.subplot(1, 3, 3)
        plt.scatter(data_2d[:, 0], data_2d[:, 1], c=true_labels, 
                   alpha=0.2, cmap='viridis', s=5)
        plt.scatter(coreset_2d[:, 0], coreset_2d[:, 1], c='red', 
                   s=sizes, alpha=0.7, edgecolors='black', label='核心集')
        if lowdim_centers_2d is not None:
            plt.scatter(lowdim_centers_2d[:, 0], lowdim_centers_2d[:, 1], 
                       c='blue', marker='X', s=200, label='聚类中心')
        plt.title('数据 vs 核心集')
        plt.legend()
        
        plt.tight_layout()
        plt.show()
        
    except Exception as e:
        print(f"可视化失败: {e}")
        import traceback
        traceback.print_exc()
        
def visualize_results(data_stream, true_labels, coreset_points, coreset_weights, 
                     lowdim_centers, original_centers_approx):
    """可视化结果（如果数据是2D或3D）"""
    try:
        # 使用PCA将高维数据降到2D进行可视化
        from sklearn.decomposition import PCA
        
        data_array = np.array(data_stream)
        
        # 将原始数据降到2D
        pca = PCA(n_components=2)
        data_2d = pca.fit_transform(data_array)
        
        # 修复：将核心集数据降到2D（使用相同的PCA变换）
        # 注意：coreset_points 已经是投影后的低维数据，需要先逆投影到原始空间
        if original_centers_approx is not None:
            # 使用伪逆进行逆投影
            A_pinv = np.linalg.pinv(psc.projection_matrix)
            coreset_original_approx = coreset_points @ A_pinv.T
            coreset_2d = pca.transform(coreset_original_approx)
        else:
            # 如果无法逆投影，直接对低维核心集进行PCA
            pca_core = PCA(n_components=2)
            coreset_2d = pca_core.fit_transform(coreset_points)
        
        # 修复：将低维聚类中心逆变换到原始空间再降到2D
        if lowdim_centers is not None and original_centers_approx is not None:
            lowdim_centers_2d = pca.transform(original_centers_approx)
        elif lowdim_centers is not None:
            pca_center = PCA(n_components=2)
            lowdim_centers_2d = pca_center.fit_transform(lowdim_centers)
        
        plt.figure(figsize=(15, 5))
        
        # 子图1: 原始数据
        plt.subplot(1, 3, 1)
        scatter = plt.scatter(data_2d[:, 0], data_2d[:, 1], c=true_labels, 
                             alpha=0.6, cmap='viridis', s=10)
        plt.title('原始数据 (PCA降维)')
        plt.colorbar(scatter)
        
        # 子图2: 核心集
        plt.subplot(1, 3, 2)
        # 根据权重调整点的大小
        sizes = np.array(coreset_weights) * 100 + 10
        plt.scatter(coreset_2d[:, 0], coreset_2d[:, 1], c='red', 
                   s=sizes, alpha=0.7, edgecolors='black', label='核心集点')
        if lowdim_centers is not None:
            plt.scatter(lowdim_centers_2d[:, 0], lowdim_centers_2d[:, 1], 
                       c='blue', marker='X', s=200, label='聚类中心')
        plt.title('核心集表示')
        plt.legend()
        
        # 子图3: 比较
        plt.subplot(1, 3, 3)
        plt.scatter(data_2d[:, 0], data_2d[:, 1], c=true_labels, 
                   alpha=0.2, cmap='viridis', s=5)
        plt.scatter(coreset_2d[:, 0], coreset_2d[:, 1], c='red', 
                   s=sizes, alpha=0.7, edgecolors='black', label='核心集')
        if lowdim_centers is not None:
            plt.scatter(lowdim_centers_2d[:, 0], lowdim_centers_2d[:, 1], 
                       c='blue', marker='X', s=200, label='聚类中心')
        plt.title('数据 vs 核心集')
        plt.legend()
        
        plt.tight_layout()
        plt.show()
        
    except Exception as e:
        print(f"可视化失败: {e}")
        import traceback
        traceback.print_exc()

# 性能对比实验
def performance_comparison():
    """比较不同方法在不同数据规模下的性能"""
    print("\n" + "="*60)
    print("性能对比实验")
    print("="*60)
    
    np.random.seed(42)
    
    # 测试不同数据规模
    data_sizes = [1000, 5000, 10000]
    dimensions = [50, 100, 200]
    
    results = defaultdict(list)
    
    for n_samples in data_sizes:
        for original_dim in dimensions:
            print(f"\n测试: {n_samples}样本, {original_dim}维")
            
            # 生成数据
            centers = np.random.randn(3, original_dim) * 2
            data_stream = []
            for center in centers:
                cluster_data = np.random.normal(0, 1, (n_samples//3, original_dim)) + center
                data_stream.extend(cluster_data)
            
            # 基准: 标准k-means
            start_time = time.time()
            kmeans = KMeans(n_clusters=3, random_state=42)
            kmeans.fit(data_stream)
            kmeans_time = time.time() - start_time
            kmeans_cost = kmeans.inertia_
            
            # 投影流式核心集
            psc = ProjectedStreamingCoreset(
                target_coreset_size=50,
                target_k=3,
                epsilon_jl=0.2,
                max_stream_size=n_samples
            )
            
            start_time = time.time()
            psc.process_stream(data_stream)
            psc._update_cluster_centers()
            psc_time = time.time() - start_time
            
            # 评估近似质量
            approx_ratio = psc.evaluate_approximation(data_stream, kmeans.cluster_centers_)
            
            results['n_samples'].append(n_samples)
            results['dimension'].append(original_dim)
            results['kmeans_time'].append(kmeans_time)
            results['psc_time'].append(psc_time)
            results['speedup'].append(kmeans_time / psc_time)
            results['approx_ratio'].append(approx_ratio)
            
            print(f"k-means时间: {kmeans_time:.4f}s")
            print(f"PSA时间: {psc_time:.4f}s")
            print(f"加速比: {kmeans_time/psc_time:.2f}x")
            print(f"近似比率: {approx_ratio:.4f}")
    
    # 绘制结果
    plt.figure(figsize=(12, 8))
    
    # 子图1: 时间对比
    plt.subplot(2, 2, 1)
    for i, dim in enumerate(dimensions):
        mask = np.array(results['dimension']) == dim
        plt.plot(np.array(results['n_samples'])[mask], 
                np.array(results['kmeans_time'])[mask], 
                'o-', label=f'k-means ({dim}D)')
        plt.plot(np.array(results['n_samples'])[mask], 
                np.array(results['psc_time'])[mask], 
                's--', label=f'PSA ({dim}D)')
    plt.xlabel('数据规模')
    plt.ylabel('时间 (秒)')
    plt.title('计算时间对比')
    plt.legend()
    plt.yscale('log')
    
    # 子图2: 加速比
    plt.subplot(2, 2, 2)
    for dim in dimensions:
        mask = np.array(results['dimension']) == dim
        plt.plot(np.array(results['n_samples'])[mask], 
                np.array(results['speedup'])[mask], 'o-', label=f'{dim}D')
    plt.xlabel('数据规模')
    plt.ylabel('加速比')
    plt.title('PSA相对于k-means的加速比')
    plt.legend()
    
    # 子图3: 近似质量
    plt.subplot(2, 2, 3)
    for dim in dimensions:
        mask = np.array(results['dimension']) == dim
        plt.plot(np.array(results['n_samples'])[mask], 
                np.array(results['approx_ratio'])[mask], 'o-', label=f'{dim}D')
    plt.axhline(y=1.0, color='r', linestyle='--', alpha=0.7, label='完美近似')
    plt.xlabel('数据规模')
    plt.ylabel('近似比率')
    plt.title('近似质量 (比率越接近1越好)')
    plt.legend()
    
    plt.tight_layout()
    plt.show()
    
    return results

if __name__ == "__main__":
    # 运行演示
    psc, true_kmeans, approx_ratio = demo_projected_streaming_coreset()
    
    # 运行性能对比
    results = performance_comparison()