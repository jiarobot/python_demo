import numpy as np
import matplotlib
matplotlib.rc("font", family='Microsoft YaHei')
import matplotlib.pyplot as plt
import networkx as nx
from typing import List, Tuple, Dict
import random
from collections import defaultdict
import time

class QuantumInspiredLogisticsOptimizer:
    """
    基于量子启发式的物流路径优化系统
    结合量子比特表示和遗传算法，解决多约束物流路径问题
    """
    
    def __init__(self, city_count: int, population_size: int = 100, 
                 max_generations: int = 500):
        self.city_count = city_count
        self.population_size = population_size
        self.max_generations = max_generations
        
        # 量子比特参数
        self.quantum_bits = None
        self.rotation_angle = 0.05 * np.pi
        
        # 物流约束参数
        self.time_windows = None
        self.capacity_constraints = None
        self.distance_matrix = None
        
        # 初始化系统
        self._initialize_system()
    
    def _initialize_system(self):
        """初始化量子比特和物流约束"""
        # 初始化量子比特种群 (每个个体有city_count个量子比特)
        self.quantum_bits = np.random.uniform(0, np.pi/2, 
                                            (self.population_size, self.city_count))
        
        # 生成随机距离矩阵
        self.distance_matrix = self._generate_distance_matrix()
        
        # 生成时间窗口约束
        self.time_windows = self._generate_time_windows()
        
        # 生成容量约束
        self.capacity_constraints = self._generate_capacity_constraints()
    
    def _generate_distance_matrix(self) -> np.ndarray:
        """生成城市间距离矩阵"""
        np.random.seed(42)
        matrix = np.random.randint(10, 100, (self.city_count, self.city_count))
        matrix = (matrix + matrix.T) // 2  # 确保对称
        np.fill_diagonal(matrix, 0)
        return matrix
    
    def _generate_time_windows(self) -> Dict:
        """生成时间窗口约束"""
        time_windows = {}
        for i in range(self.city_count):
            start = random.randint(0, 50)
            end = start + random.randint(10, 30)
            time_windows[i] = (start, end)
        return time_windows
    
    def _generate_capacity_constraints(self) -> Dict:
        """生成容量约束"""
        capacities = {}
        for i in range(self.city_count):
            capacities[i] = random.randint(5, 20)
        return capacities
    
    def quantum_measurement(self, quantum_bits: np.ndarray) -> np.ndarray:
        """量子测量：将量子比特转换为经典比特"""
        probabilities = np.sin(quantum_bits) ** 2
        measurements = (np.random.random(quantum_bits.shape) < probabilities).astype(int)
        return measurements
    
    def create_routes(self, measurements: np.ndarray) -> List[List[int]]:
        """根据测量结果创建路径"""
        routes = []
        for individual in measurements:
            route = list(np.where(individual == 1)[0])
            if len(route) == 0:
                route = [random.randint(0, self.city_count-1)]
            routes.append(route)
        return routes
    
    def calculate_fitness(self, routes: List[List[int]]) -> np.ndarray:
        """计算适应度：考虑距离、时间窗口、容量约束"""
        fitness_scores = np.zeros(len(routes))
        
        for idx, route in enumerate(routes):
            if len(route) < 2:
                fitness_scores[idx] = 0
                continue
            
            # 计算总距离
            total_distance = 0
            for i in range(len(route)-1):
                total_distance += self.distance_matrix[route[i], route[i+1]]
            
            # 计算时间窗口违反程度
            time_penalty = 0
            current_time = 0
            for city in route:
                start, end = self.time_windows[city]
                if current_time < start:
                    time_penalty += (start - current_time) * 2
                elif current_time > end:
                    time_penalty += (current_time - end) * 5
                current_time += 1  # 简化时间计算
            
            # 计算容量约束违反程度
            capacity_penalty = 0
            current_load = 0
            for city in route:
                city_capacity = self.capacity_constraints[city]
                if current_load + 1 > city_capacity:  # 假设每个城市需求为1
                    capacity_penalty += 10
                current_load += 1
            
            # 综合适应度 (距离越小越好，惩罚越小越好)
            fitness_scores[idx] = 1 / (total_distance + time_penalty + capacity_penalty + 1)
        
        return fitness_scores
    
    def quantum_rotation(self, quantum_bits: np.ndarray, best_solution: np.ndarray, 
                        current_solution: np.ndarray) -> np.ndarray:
        """量子旋转门：更新量子比特状态"""
        new_quantum_bits = quantum_bits.copy()
        
        for i in range(quantum_bits.shape[0]):
            for j in range(quantum_bits.shape[1]):
                # 修复：best_solution 是一维数组，使用 j 索引
                if current_solution[i, j] != best_solution[j]:
                    if current_solution[i, j] == 0 and best_solution[j] == 1:
                        # 向1状态旋转
                        new_quantum_bits[i, j] += self.rotation_angle
                    else:
                        # 向0状态旋转
                        new_quantum_bits[i, j] -= self.rotation_angle
                
                # 保持量子比特在有效范围内
                new_quantum_bits[i, j] = np.clip(new_quantum_bits[i, j], 0, np.pi/2)
        
        return new_quantum_bits
    
    def quantum_crossover(self, parent1: np.ndarray, parent2: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """量子交叉操作"""
        crossover_point = random.randint(1, self.city_count-1)
        
        child1 = np.concatenate([parent1[:crossover_point], parent2[crossover_point:]])
        child2 = np.concatenate([parent2[:crossover_point], parent1[crossover_point:]])
        
        return child1, child2
    
    def quantum_mutation(self, individual: np.ndarray, mutation_rate: float = 0.1) -> np.ndarray:
        """量子变异操作"""
        mutated = individual.copy()
        for i in range(len(individual)):
            if random.random() < mutation_rate:
                # 量子比特相位翻转
                mutated[i] = np.pi/2 - mutated[i]
        return mutated
    
    def optimize(self) -> Dict:
        """执行优化过程"""
        best_fitness_history = []
        avg_fitness_history = []
        best_solution = None
        best_fitness = 0
        
        print("开始量子启发式物流优化...")
        start_time = time.time()
        
        for generation in range(self.max_generations):
            # 量子测量
            measurements = self.quantum_measurement(self.quantum_bits)
            
            # 创建路径并计算适应度
            routes = self.create_routes(measurements)
            fitness_scores = self.calculate_fitness(routes)
            
            # 更新最佳解
            current_best_idx = np.argmax(fitness_scores)
            current_best_fitness = fitness_scores[current_best_idx]
            
            if current_best_fitness > best_fitness:
                best_fitness = current_best_fitness
                best_solution = measurements[current_best_idx].copy()
            
            # 记录历史数据
            best_fitness_history.append(best_fitness)
            avg_fitness_history.append(np.mean(fitness_scores))
            
            # 量子旋转更新（确保 best_solution 不为 None）
            if best_solution is not None:
                self.quantum_bits = self.quantum_rotation(
                    self.quantum_bits, best_solution, measurements
                )
            
            # 选择、交叉、变异
            self._evolutionary_operations(fitness_scores)
            
            if generation % 50 == 0:
                print(f"代 {generation}: 最佳适应度 = {best_fitness:.4f}")
        
        end_time = time.time()
        print(f"优化完成! 总耗时: {end_time - start_time:.2f} 秒")
        
        return {
            'best_solution': best_solution,
            'best_route': self.create_routes([best_solution])[0] if best_solution is not None else [],
            'best_fitness': best_fitness,
            'fitness_history': best_fitness_history,
            'avg_fitness_history': avg_fitness_history,
            'computation_time': end_time - start_time
        }
    
    def _evolutionary_operations(self, fitness_scores: np.ndarray):
        """执行进化操作"""
        # 选择 (锦标赛选择)
        selected_indices = self._tournament_selection(fitness_scores)
        new_population = []
        
        # 交叉和变异
        for i in range(0, len(selected_indices), 2):
            if i + 1 < len(selected_indices):
                parent1 = self.quantum_bits[selected_indices[i]]
                parent2 = self.quantum_bits[selected_indices[i+1]]
                
                child1, child2 = self.quantum_crossover(parent1, parent2)
                child1 = self.quantum_mutation(child1)
                child2 = self.quantum_mutation(child2)
                
                new_population.extend([child1, child2])
        
        # 更新种群
        if new_population:
            self.quantum_bits[:len(new_population)] = new_population
    
    def _tournament_selection(self, fitness_scores: np.ndarray, tournament_size: int = 3) -> List[int]:
        """锦标赛选择"""
        selected = []
        for _ in range(self.population_size):
            contestants = random.sample(range(len(fitness_scores)), tournament_size)
            winner = max(contestants, key=lambda x: fitness_scores[x])
            selected.append(winner)
        return selected

    def visualize_results(self, results: Dict):
        """可视化优化结果"""
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        
        # 适应度进化曲线
        axes[0, 0].plot(results['fitness_history'], label='最佳适应度', color='blue')
        axes[0, 0].plot(results['avg_fitness_history'], label='平均适应度', color='red')
        axes[0, 0].set_title('适应度进化曲线')
        axes[0, 0].set_xlabel('代数')
        axes[0, 0].set_ylabel('适应度')
        axes[0, 0].legend()
        axes[0, 0].grid(True)
        
        # 最佳路径可视化
        best_route = results['best_route']
        if len(best_route) > 1:
            # 创建城市坐标
            cities = np.random.rand(self.city_count, 2) * 100
            
            axes[0, 1].scatter(cities[:, 0], cities[:, 1], c='red', s=100)
            for i, (x, y) in enumerate(cities):
                axes[0, 1].annotate(str(i), (x, y), xytext=(5, 5), textcoords='offset points')
            
            # 绘制路径
            route_coords = cities[best_route]
            axes[0, 1].plot(route_coords[:, 0], route_coords[:, 1], 'b-', alpha=0.7)
            axes[0, 1].set_title('最佳物流路径')
            axes[0, 1].set_xlabel('X坐标')
            axes[0, 1].set_ylabel('Y坐标')
            axes[0, 1].grid(True)
        
        # 距离矩阵热力图
        im = axes[1, 0].imshow(self.distance_matrix, cmap='hot', interpolation='nearest')
        axes[1, 0].set_title('城市间距离矩阵')
        plt.colorbar(im, ax=axes[1, 0])
        
        # 约束条件展示
        cities = list(range(self.city_count))
        time_starts = [self.time_windows[i][0] for i in cities]
        time_ends = [self.time_windows[i][1] for i in cities]
        
        axes[1, 1].barh(cities, time_ends, left=time_starts, alpha=0.6, color='green')
        axes[1, 1].set_title('时间窗口约束')
        axes[1, 1].set_xlabel('时间')
        axes[1, 1].set_ylabel('城市')
        
        plt.tight_layout()
        plt.show()

# 高级功能：实时优化监控器
class RealTimeOptimizationMonitor:
    """实时优化监控器"""
    
    def __init__(self, optimizer: QuantumInspiredLogisticsOptimizer):
        self.optimizer = optimizer
        self.real_time_data = []
    
    def start_monitoring(self, interval: int = 10):
        """开始实时监控"""
        print("启动实时监控...")
        results = self.optimizer.optimize()
        
        # 生成实时数据报告
        self._generate_report(results)
        return results
    
    def _generate_report(self, results: Dict):
        """生成优化报告"""
        print("\n" + "="*50)
        print("量子物流优化系统 - 最终报告")
        print("="*50)
        print(f"优化城市数量: {self.optimizer.city_count}")
        print(f"种群大小: {self.optimizer.population_size}")
        print(f"总代数: {self.optimizer.max_generations}")
        print(f"计算时间: {results['computation_time']:.2f} 秒")
        print(f"最终最佳适应度: {results['best_fitness']:.4f}")
        print(f"最佳路径: {results['best_route']}")
        print(f"路径长度: {len(results['best_route'])} 个城市")
        
        # 计算路径总距离
        total_distance = 0
        route = results['best_route']
        if len(route) > 1:
            for i in range(len(route)-1):
                total_distance += self.optimizer.distance_matrix[route[i], route[i+1]]
            print(f"路径总距离: {total_distance}")

# 使用示例
if __name__ == "__main__":
    # 创建优化器实例
    optimizer = QuantumInspiredLogisticsOptimizer(
        city_count=20,        # 20个城市
        population_size=100,  # 种群大小100
        max_generations=200   # 最大200代
    )
    
    # 创建监控器
    monitor = RealTimeOptimizationMonitor(optimizer)
    
    # 执行优化并监控
    results = monitor.start_monitoring()
    
    # 可视化结果
    optimizer.visualize_results(results)