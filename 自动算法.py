import numpy as np
import matplotlib.pyplot as plt
from scipy.spatial.distance import pdist, squareform
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import Matern, WhiteKernel, ConstantKernel
from scipy.optimize import minimize
from scipy.stats import norm
import optuna
from functools import partial
import time
import warnings
warnings.filterwarnings('ignore')

# 设置随机种子以确保可重复性
np.random.seed(42)

class TSPInstance:
    """TSP问题实例类"""
    def __init__(self, name, coordinates):
        self.name = name
        self.coordinates = coordinates
        self.n_cities = len(coordinates)
        self.distance_matrix = self._compute_distance_matrix()
        
    def _compute_distance_matrix(self):
        """计算城市间的距离矩阵"""
        return squareform(pdist(self.coordinates, metric='euclidean'))
    
    def evaluate_tour(self, tour):
        """评估路径的总长度"""
        return sum(self.distance_matrix[tour[i], tour[(i+1) % self.n_cities]] 
                  for i in range(self.n_cities))

class ConfigurableSA:
    """可配置的模拟退火算法类"""
    def __init__(self, tsp_instance, config):
        self.tsp = tsp_instance
        self.config = config
        self.best_tour = None
        self.best_length = float('inf')
        self.history = []
        
    def _initialize_tour(self):
        """初始化路径"""
        tour = np.random.permutation(self.tsp.n_cities)
        return tour, self.tsp.evaluate_tour(tour)
    
    def _get_neighbor(self, tour):
        """生成邻域解"""
        # 根据配置选择不同的邻域操作
        if self.config.get('mutation_operator', 'swap') == 'swap':
            # 交换两个城市
            i, j = np.random.choice(len(tour), 2, replace=False)
            new_tour = tour.copy()
            new_tour[i], new_tour[j] = new_tour[j], new_tour[i]
        elif self.config.get('mutation_operator') == 'inversion':
            # 逆序一段路径
            i, j = np.sort(np.random.choice(len(tour), 2, replace=False))
            new_tour = tour.copy()
            new_tour[i:j+1] = tour[i:j+1][::-1]
        else:  # insertion
            # 插入一个城市到新位置
            i, j = np.random.choice(len(tour), 2, replace=False)
            new_tour = np.delete(tour, i)
            new_tour = np.insert(new_tour, j, tour[i])
        
        return new_tour, self.tsp.evaluate_tour(new_tour)
    
    def _acceptance_probability(self, delta, temperature):
        """计算接受概率"""
        criterion = self.config.get('acceptance_criterion', 'metropolis')
        
        if criterion == 'metropolis':
            # 标准Metropolis准则
            return np.exp(-delta / temperature) if delta > 0 else 1.0
        elif criterion == 'threshold':
            # 阈值接受准则
            threshold = self.config.get('threshold', 0.1)
            return 1.0 if delta < threshold else 0.0
        elif criterion == 'custom_tanh':
            # 自定义tanh接受准则
            scale = self.config.get('scale_factor', 100)
            shift = self.config.get('shift_factor', 50)
            return 0.5 * (1 + np.tanh(-(delta - shift) / scale))
        else:
            return np.exp(-delta / temperature) if delta > 0 else 1.0
    
    def _temperature_schedule(self, iteration, initial_temp, current_temp):
        """温度调度函数"""
        schedule = self.config.get('cooling_schedule', 'exponential')
        
        if schedule == 'exponential':
            alpha = self.config.get('cooling_rate', 0.99)
            return initial_temp * (alpha ** iteration)
        elif schedule == 'linear':
            alpha = self.config.get('cooling_rate', 0.99)
            return initial_temp * (1 - alpha * iteration / self.max_iterations)
        elif schedule == 'logarithmic':
            return initial_temp / np.log(iteration + 2)
        else:  # adaptive
            # 简化的自适应降温
            if len(self.history) > 10 and np.std(self.history[-10:]) < 0.01:
                return current_temp * 0.8  # 快速降温
            return current_temp * 0.99
    
    def _initial_temperature(self):
        """初始温度计算"""
        method = self.config.get('init_temp_method', 'fixed')
        
        if method == 'fixed':
            return self.config.get('initial_temperature', 1000)
        elif method == 'percentile':
            # 基于初始解差异的百分位数
            num_samples = self.config.get('num_samples', 100)
            deltas = []
            current_tour, current_length = self._initialize_tour()
            
            for _ in range(num_samples):
                new_tour, new_length = self._get_neighbor(current_tour)
                deltas.append(abs(new_length - current_length))
            
            percentile = self.config.get('percentile', 90)
            return np.percentile(deltas, percentile)
        else:  # heuristic
            # 基于问题规模的启发式
            return self.tsp.n_cities * 100
    
    def run(self, max_iterations=10000, max_time=60):
        """运行模拟退火算法"""
        self.max_iterations = max_iterations
        start_time = time.time()
        
        # 初始化
        current_tour, current_length = self._initialize_tour()
        initial_temp = self._initial_temperature()
        temperature = initial_temp
        
        # 记录最佳解
        if current_length < self.best_length:
            self.best_tour = current_tour
            self.best_length = current_length
        
        self.history = [current_length]
        
        # 主循环
        for iteration in range(max_iterations):
            # 检查时间限制
            if time.time() - start_time > max_time:
                break
                
            # 生成邻域解
            new_tour, new_length = self._get_neighbor(current_tour)
            delta = new_length - current_length
            
            # 决定是否接受新解
            if delta < 0 or np.random.rand() < self._acceptance_probability(delta, temperature):
                current_tour, current_length = new_tour, new_length
                
                # 更新最佳解
                if current_length < self.best_length:
                    self.best_tour = current_tour
                    self.best_length = current_length
            
            # 记录历史
            self.history.append(current_length)
            
            # 更新温度
            temperature = self._temperature_schedule(iteration, initial_temp, temperature)
            
            # 应用局部搜索（如果配置）
            if self.config.get('use_local_search', False) and iteration % 100 == 0:
                current_tour, current_length = self._local_search(current_tour, current_length)
        
        return self.best_tour, self.best_length, self.history
    
    def _local_search(self, tour, length):
        """简单的局部搜索：2-opt"""
        improved = True
        best_tour = tour.copy()
        best_length = length
        
        while improved:
            improved = False
            for i in range(1, len(tour) - 2):
                for j in range(i + 1, len(tour)):
                    if j - i == 1:
                        continue
                    
                    # 尝试2-opt交换
                    new_tour = best_tour.copy()
                    new_tour[i:j] = best_tour[i:j][::-1]
                    new_length = self.tsp.evaluate_tour(new_tour)
                    
                    if new_length < best_length:
                        best_tour, best_length = new_tour, new_length
                        improved = True
            
            tour, length = best_tour, best_length
        
        return best_tour, best_length

class BayesianOptimizer:
    """贝叶斯优化器类"""
    def __init__(self, tsp_instance, n_init=10, n_iter=50):
        self.tsp = tsp_instance
        self.n_init = n_init
        self.n_iter = n_iter
        self.X = []  # 配置参数
        self.y = []  # 目标函数值
        self.gp = self._create_gp_model()
        
    def _create_gp_model(self):
        """创建高斯过程回归模型"""
        kernel = ConstantKernel(1.0) * Matern(length_scale=1.0, nu=2.5) + WhiteKernel(noise_level=1.0)
        return GaussianProcessRegressor(kernel=kernel, n_restarts_optimizer=10, alpha=1e-4)
    
    def _config_to_vector(self, config):
        """将配置字典转换为特征向量"""
        # 这是一个简化的实现，实际应用中需要更复杂的编码
        vector = []
        
        # 编码初始温度方法
        if config.get('init_temp_method', 'fixed') == 'fixed':
            vector.extend([1, 0, 0])
        elif config.get('init_temp_method') == 'percentile':
            vector.extend([0, 1, 0])
        else:  # heuristic
            vector.extend([0, 0, 1])
        
        # 编码初始温度值（如果使用fixed）
        if config.get('init_temp_method', 'fixed') == 'fixed':
            vector.append(config.get('initial_temperature', 1000) / 5000)  # 归一化
        else:
            vector.append(0)
        
        # 编码降温策略
        if config.get('cooling_schedule', 'exponential') == 'exponential':
            vector.extend([1, 0, 0, 0])
        elif config.get('cooling_schedule') == 'linear':
            vector.extend([0, 1, 0, 0])
        elif config.get('cooling_schedule') == 'logarithmic':
            vector.extend([0, 0, 1, 0])
        else:  # adaptive
            vector.extend([0, 0, 0, 1])
        
        # 编码降温速率
        vector.append(config.get('cooling_rate', 0.99))
        
        # 编码接受准则
        if config.get('acceptance_criterion', 'metropolis') == 'metropolis':
            vector.extend([1, 0, 0])
        elif config.get('acceptance_criterion') == 'threshold':
            vector.extend([0, 1, 0])
        else:  # custom_tanh
            vector.extend([0, 0, 1])
        
        # 编码自定义接受准则参数
        if config.get('acceptance_criterion', 'metropolis') == 'custom_tanh':
            vector.append(config.get('scale_factor', 100) / 200)  # 归一化
            vector.append(config.get('shift_factor', 50) / 100)   # 归一化
        else:
            vector.extend([0, 0])
        
        # 编码变异算子
        if config.get('mutation_operator', 'swap') == 'swap':
            vector.extend([1, 0, 0])
        elif config.get('mutation_operator') == 'inversion':
            vector.extend([0, 1, 0])
        else:  # insertion
            vector.extend([0, 0, 1])
        
        # 编码是否使用局部搜索
        vector.append(1 if config.get('use_local_search', False) else 0)
        
        return np.array(vector)
    
    def _vector_to_config(self, vector):
        """将特征向量转换为配置字典"""
        config = {}
        idx = 0
        
        # 解码初始温度方法
        temp_method = np.argmax(vector[idx:idx+3])
        if temp_method == 0:
            config['init_temp_method'] = 'fixed'
        elif temp_method == 1:
            config['init_temp_method'] = 'percentile'
        else:
            config['init_temp_method'] = 'heuristic'
        idx += 3
        
        # 解码初始温度值
        if config['init_temp_method'] == 'fixed':
            config['initial_temperature'] = vector[idx] * 5000  # 反归一化
        idx += 1
        
        # 解码降温策略
        cooling_method = np.argmax(vector[idx:idx+4])
        if cooling_method == 0:
            config['cooling_schedule'] = 'exponential'
        elif cooling_method == 1:
            config['cooling_schedule'] = 'linear'
        elif cooling_method == 2:
            config['cooling_schedule'] = 'logarithmic'
        else:
            config['cooling_schedule'] = 'adaptive'
        idx += 4
        
        # 解码降温速率
        config['cooling_rate'] = vector[idx]
        idx += 1
        
        # 解码接受准则
        acceptance_method = np.argmax(vector[idx:idx+3])
        if acceptance_method == 0:
            config['acceptance_criterion'] = 'metropolis'
        elif acceptance_method == 1:
            config['acceptance_criterion'] = 'threshold'
        else:
            config['acceptance_criterion'] = 'custom_tanh'
        idx += 3
        
        # 解码自定义接受准则参数
        if config['acceptance_criterion'] == 'custom_tanh':
            config['scale_factor'] = vector[idx] * 200  # 反归一化
            config['shift_factor'] = vector[idx+1] * 100  # 反归一化
            idx += 2
        else:
            idx += 2
        
        # 解码变异算子
        mutation_method = np.argmax(vector[idx:idx+3])
        if mutation_method == 0:
            config['mutation_operator'] = 'swap'
        elif mutation_method == 1:
            config['mutation_operator'] = 'inversion'
        else:
            config['mutation_operator'] = 'insertion'
        idx += 3
        
        # 解码是否使用局部搜索
        config['use_local_search'] = bool(round(vector[idx]))
        
        return config
    
    def _random_config(self):
        """生成随机配置"""
        config = {}
        
        # 初始温度方法
        methods = ['fixed', 'percentile', 'heuristic']
        config['init_temp_method'] = np.random.choice(methods)
        
        if config['init_temp_method'] == 'fixed':
            config['initial_temperature'] = np.random.uniform(100, 5000)
        
        # 降温策略
        strategies = ['exponential', 'linear', 'logarithmic', 'adaptive']
        config['cooling_schedule'] = np.random.choice(strategies)
        config['cooling_rate'] = np.random.uniform(0.9, 0.999)
        
        # 接受准则
        criteria = ['metropolis', 'threshold', 'custom_tanh']
        config['acceptance_criterion'] = np.random.choice(criteria)
        
        if config['acceptance_criterion'] == 'threshold':
            config['threshold'] = np.random.uniform(0.01, 0.5)
        elif config['acceptance_criterion'] == 'custom_tanh':
            config['scale_factor'] = np.random.uniform(10, 200)
            config['shift_factor'] = np.random.uniform(10, 100)
        
        # 变异算子
        operators = ['swap', 'inversion', 'insertion']
        config['mutation_operator'] = np.random.choice(operators)
        
        # 局部搜索
        config['use_local_search'] = np.random.choice([True, False])
        
        return config
    
    def _evaluate_config(self, config):
        """评估配置的性能"""
        sa = ConfigurableSA(self.tsp, config)
        _, best_length, _ = sa.run(max_iterations=5000, max_time=30)  # 限制评估时间
        
        # 多次运行取平均以获得更稳定的评估
        total_length = best_length
        n_runs = 1  # 为了速度，只运行一次
        
        for _ in range(n_runs - 1):
            sa = ConfigurableSA(self.tsp, config)
            _, length, _ = sa.run(max_iterations=5000, max_time=30)
            total_length += length
        
        return total_length / n_runs
    
    def _acquisition_function(self, x, gp, best_y):
        """采集函数（期望改进）"""
        x = x.reshape(1, -1)
        mu, sigma = gp.predict(x, return_std=True)
        
        # 避免除零错误
        sigma = max(1e-9, sigma)
        
        # 计算期望改进
        improvement = best_y - mu
        z = improvement / sigma
        ei = improvement * norm.cdf(z) + sigma * norm.pdf(z)
        
        return -ei[0]  # 最小化负的EI
    
    def optimize(self):
        """执行贝叶斯优化"""
        # 初始随机采样
        print("Performing initial random sampling...")
        for _ in range(self.n_init):
            config = self._random_config()
            y = self._evaluate_config(config)
            
            self.X.append(self._config_to_vector(config))
            self.y.append(y)
            
            print(f"Config {len(self.X)}: {y:.2f}")
        
        # 贝叶斯优化循环
        print("Starting Bayesian optimization...")
        for i in range(self.n_iter):
            # 训练GP模型
            X_array = np.array(self.X)
            y_array = np.array(self.y)
            self.gp.fit(X_array, y_array)
            
            # 找到当前最佳值
            best_idx = np.argmin(y_array)
            best_y = y_array[best_idx]
            
            # 优化采集函数以找到下一个点
            bounds = [(0, 1) for _ in range(len(self.X[0]))]
            result = minimize(
                fun=self._acquisition_function,
                x0=self._config_to_vector(self._random_config()),
                args=(self.gp, best_y),
                bounds=bounds,
                method='L-BFGS-B'
            )
            
            # 获取新配置
            new_config = self._vector_to_config(result.x)
            new_y = self._evaluate_config(new_config)
            
            # 添加到数据集
            self.X.append(result.x)
            self.y.append(new_y)
            
            print(f"Iteration {i+1}/{self.n_iter}: {new_y:.2f} (Best: {min(self.y):.2f})")
        
        # 返回最佳配置
        best_idx = np.argmin(self.y)
        best_config = self._vector_to_config(self.X[best_idx])
        return best_config, min(self.y)

# 创建TSP实例（使用柏林52问题）
def create_berlin52_instance():
    """创建柏林52TSP实例"""
    # 柏林52城市的坐标
    coordinates = np.array([
        [565, 575], [25, 185], [345, 750], [945, 685], [845, 655],
        [880, 660], [25, 230], [525, 1000], [580, 1175], [650, 1130],
        [1605, 620], [1220, 580], [1465, 200], [1530, 5], [845, 680],
        [725, 370], [145, 665], [415, 635], [510, 875], [560, 365],
        [300, 465], [520, 585], [480, 415], [835, 625], [975, 580],
        [1215, 245], [1320, 315], [1250, 400], [660, 180], [410, 250],
        [420, 555], [575, 665], [1150, 1160], [700, 580], [685, 595],
        [685, 610], [770, 610], [795, 645], [720, 635], [760, 650],
        [475, 960], [95, 260], [875, 920], [700, 500], [555, 815],
        [830, 485], [1170, 65], [830, 610], [605, 625], [595, 360],
        [1340, 725], [1740, 245]
    ])
    
    return TSPInstance("Berlin52", coordinates)

# 主函数
def main():
    # 创建TSP实例
    tsp = create_berlin52_instance()
    print(f"Created TSP instance: {tsp.name} with {tsp.n_cities} cities")
    
    # 运行贝叶斯优化
    optimizer = BayesianOptimizer(tsp, n_init=5, n_iter=10)  # 为了演示，使用较小的值
    best_config, best_score = optimizer.optimize()
    
    print("\nBest configuration found:")
    for key, value in best_config.items():
        print(f"  {key}: {value}")
    print(f"Best score: {best_score:.2f}")
    
    # 使用最佳配置运行完整的SA
    print("\nRunning SA with best configuration...")
    sa = ConfigurableSA(tsp, best_config)
    best_tour, best_length, history = sa.run(max_iterations=20000, max_time=120)
    
    print(f"Final tour length: {best_length:.2f}")
    
    # 绘制收敛曲线
    plt.figure(figsize=(10, 6))
    plt.plot(history)
    plt.title("SA Convergence with Optimized Configuration")
    plt.xlabel("Iteration")
    plt.ylabel("Tour Length")
    plt.grid(True)
    plt.savefig("convergence.png")
    plt.show()
    
    # 绘制最佳路径
    plt.figure(figsize=(10, 8))
    tour_coords = tsp.coordinates[best_tour]
    tour_coords = np.vstack([tour_coords, tour_coords[0]])  # 闭合路径
    
    plt.plot(tour_coords[:, 0], tour_coords[:, 1], 'o-')
    plt.title(f"Best Tour (Length: {best_length:.2f})")
    plt.xlabel("X Coordinate")
    plt.ylabel("Y Coordinate")
    plt.grid(True)
    plt.savefig("best_tour.png")
    plt.show()

if __name__ == "__main__":
    main()