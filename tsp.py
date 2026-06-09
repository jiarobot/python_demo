import numpy as np
import matplotlib.pyplot as plt
import matplotlib
matplotlib.rc("font", family='Microsoft YaHei')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from scipy.spatial.distance import pdist, squareform
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import Matern, WhiteKernel, ConstantKernel
from scipy.optimize import minimize
from scipy.stats import norm
import optuna
from functools import partial
import time
import warnings
import logging
from typing import Dict, List, Tuple, Optional, Callable, Any
from enum import Enum
import json
import os
from dataclasses import dataclass
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
import sys

# PyQt5 imports
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QGroupBox, QPushButton, QLabel, QComboBox, QSpinBox, 
                             QDoubleSpinBox, QCheckBox, QTabWidget, QTextEdit, 
                             QFileDialog, QProgressBar, QSlider, QSplitter, QMessageBox,
                             QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QPalette, QColor

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('TSP_Solver')

# 忽略警告
warnings.filterwarnings('ignore')

# 设置随机种子以确保可重复性
np.random.seed(42)

class MutationOperator(Enum):
    SWAP = "swap"
    INVERSION = "inversion"
    INSERTION = "insertion"
    SCRAMBLE = "scramble"
    REVERSE = "reverse"
    
class CoolingSchedule(Enum):
    EXPONENTIAL = "exponential"
    LINEAR = "linear"
    LOGARITHMIC = "logarithmic"
    ADAPTIVE = "adaptive"
    QUADRATIC = "quadratic"
    
class AcceptanceCriterion(Enum):
    METROPOLIS = "metropolis"
    THRESHOLD = "threshold"
    TANH = "custom_tanh"
    BOLTZMANN = "boltzmann"

class AlgorithmType(Enum):
    SIMULATED_ANNEALING = "simulated_annealing"
    GENETIC_ALGORITHM = "genetic_algorithm"
    ANT_COLONY = "ant_colony"

@dataclass
class SAConfig:
    """模拟退火配置参数"""
    init_temp_method: str = "fixed"
    initial_temperature: float = 1000.0
    cooling_schedule: str = "exponential"
    cooling_rate: float = 0.99
    acceptance_criterion: str = "metropolis"
    mutation_operator: str = "swap"
    use_local_search: bool = False
    local_search_frequency: int = 100
    threshold: float = 0.1
    scale_factor: float = 100.0
    shift_factor: float = 50.0
    percentile: int = 90
    num_samples: int = 100
    mutation_weights: Optional[Dict[str, float]] = None
    
    def to_dict(self) -> Dict:
        return self.__dict__
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'SAConfig':
        return cls(**data)

@dataclass
class GAConfig:
    """遗传算法配置参数"""
    population_size: int = 100
    crossover_rate: float = 0.8
    mutation_rate: float = 0.2
    selection_method: str = "tournament"  # "roulette", "tournament", "rank"
    tournament_size: int = 5
    crossover_operator: str = "OX"  # "OX", "PMX", "CX"
    elitism_count: int = 2
    max_generations: int = 1000
    
    def to_dict(self) -> Dict:
        return self.__dict__
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'GAConfig':
        return cls(**data)

@dataclass
class ACOConfig:
    """蚁群算法配置参数"""
    num_ants: int = 50
    alpha: float = 1.0  # 信息素重要程度
    beta: float = 2.0   # 启发式信息重要程度
    evaporation_rate: float = 0.5
    q0: float = 0.9     # 直接选择概率
    initial_pheromone: float = 0.1
    max_iterations: int = 100
    
    def to_dict(self) -> Dict:
        return self.__dict__
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ACOConfig':
        return cls(**data)

class TSPInstance:
    """TSP问题实例类"""
    def __init__(self, name: str, coordinates: np.ndarray):
        self.name = name
        self.coordinates = coordinates
        self.n_cities = len(coordinates)
        self.distance_matrix = self._compute_distance_matrix()
        
    def _compute_distance_matrix(self) -> np.ndarray:
        """计算城市间的距离矩阵"""
        return squareform(pdist(self.coordinates, metric='euclidean'))
    
    def evaluate_tour(self, tour: np.ndarray) -> float:
        """评估路径的总长度"""
        return sum(self.distance_matrix[tour[i], tour[(i+1) % self.n_cities]] 
                  for i in range(self.n_cities))
    
    def save(self, filename: str):
        """保存TSP实例到文件"""
        data = {
            'name': self.name,
            'coordinates': self.coordinates.tolist(),
            'n_cities': self.n_cities
        }
        with open(filename, 'w') as f:
            json.dump(data, f)
    
    @classmethod
    def load(cls, filename: str) -> 'TSPInstance':
        """从文件加载TSP实例"""
        with open(filename, 'r') as f:
            data = json.load(f)
        return cls(data['name'], np.array(data['coordinates']))
    
    def visualize_tour(self, tour: np.ndarray, title: str = "", save_path: Optional[str] = None):
        """可视化路径"""
        plt.figure(figsize=(12, 10))
        tour_coords = self.coordinates[tour]
        tour_coords = np.vstack([tour_coords, tour_coords[0]])  # 闭合路径
        
        plt.plot(tour_coords[:, 0], tour_coords[:, 1], 'o-', linewidth=1, markersize=4)
        
        # 标记起点
        plt.plot(tour_coords[0, 0], tour_coords[0, 1], 'ro', markersize=8)
        
        plt.title(f"{title} (Length: {self.evaluate_tour(tour):.2f})")
        plt.xlabel("X Coordinate")
        plt.ylabel("Y Coordinate")
        plt.grid(True, alpha=0.3)
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.show()

class MplCanvas(FigureCanvas):
    """Matplotlib画布用于PyQt"""
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_subplot(111)
        super().__init__(self.fig)
        self.setParent(parent)

class BaseSolver:
    """基础求解器类"""
    def __init__(self, tsp_instance: TSPInstance):
        self.tsp = tsp_instance
        self.best_tour = None
        self.best_length = float('inf')
        self.history = []
        self.execution_time = 0
        
    def solve(self, max_iterations: int = 10000, max_time: float = 60, 
              callback: Optional[Callable] = None) -> Tuple[np.ndarray, float, List]:
        """求解TSP问题"""
        raise NotImplementedError("子类必须实现solve方法")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取求解统计信息"""
        return {
            'best_length': self.best_length,
            'execution_time': self.execution_time,
            'iterations': len(self.history),
            'improvement': self.history[0] - self.best_length if self.history else 0
        }

class ConfigurableSA(BaseSolver):
    """可配置的模拟退火算法类"""
    def __init__(self, tsp_instance: TSPInstance, config: SAConfig):
        super().__init__(tsp_instance)
        self.config = config
        self.temperature_history = []
        self.acceptance_history = []
        
        # 设置变异操作权重
        if self.config.mutation_weights is None:
            self.config.mutation_weights = {
                MutationOperator.SWAP.value: 0.4,
                MutationOperator.INVERSION.value: 0.3,
                MutationOperator.INSERTION.value: 0.2,
                MutationOperator.SCRAMBLE.value: 0.05,
                MutationOperator.REVERSE.value: 0.05
            }
        
    def _initialize_tour(self) -> Tuple[np.ndarray, float]:
        """初始化路径"""
        # 使用贪婪初始化获得更好的起点
        if np.random.rand() < 0.7:  # 70%概率使用贪婪初始化
            tour = self._greedy_initialization()
        else:
            tour = np.random.permutation(self.tsp.n_cities)
            
        return tour, self.tsp.evaluate_tour(tour)
    
    def _greedy_initialization(self) -> np.ndarray:
        """贪婪算法初始化路径"""
        tour = [np.random.randint(self.tsp.n_cities)]
        unvisited = set(range(self.tsp.n_cities)) - {tour[0]}
        
        while unvisited:
            current_city = tour[-1]
            # 找到最近的未访问城市
            next_city = min(unvisited, key=lambda city: self.tsp.distance_matrix[current_city, city])
            tour.append(next_city)
            unvisited.remove(next_city)
            
        return np.array(tour)
    
    def _get_neighbor(self, tour: np.ndarray) -> Tuple[np.ndarray, float]:
        """生成邻域解"""
        # 根据权重随机选择变异操作
        operators = list(self.config.mutation_weights.keys())
        weights = list(self.config.mutation_weights.values())
        operator = np.random.choice(operators, p=weights)
        
        new_tour = tour.copy()
        n = len(tour)
        
        if operator == MutationOperator.SWAP.value:
            # 交换两个城市
            i, j = np.random.choice(n, 2, replace=False)
            new_tour[i], new_tour[j] = new_tour[j], new_tour[i]
            
        elif operator == MutationOperator.INVERSION.value:
            # 逆序一段路径
            i, j = np.sort(np.random.choice(n, 2, replace=False))
            new_tour[i:j+1] = tour[i:j+1][::-1]
            
        elif operator == MutationOperator.INSERTION.value:
            # 插入一个城市到新位置
            i, j = np.random.choice(n, 2, replace=False)
            city = new_tour[i]
            new_tour = np.delete(new_tour, i)
            new_tour = np.insert(new_tour, j, city)
            
        elif operator == MutationOperator.SCRAMBLE.value:
            # 随机打乱一段路径
            i, j = np.sort(np.random.choice(n, 2, replace=False))
            segment = new_tour[i:j+1]
            np.random.shuffle(segment)
            new_tour[i:j+1] = segment
            
        elif operator == MutationOperator.REVERSE.value:
            # 反转整个路径
            new_tour = new_tour[::-1]
        
        return new_tour, self.tsp.evaluate_tour(new_tour)
    
    def _acceptance_probability(self, delta: float, temperature: float) -> float:
        """计算接受概率"""
        criterion = self.config.acceptance_criterion
        
        if criterion == AcceptanceCriterion.METROPOLIS.value:
            # 标准Metropolis准则
            return np.exp(-delta / temperature) if delta > 0 else 1.0
            
        elif criterion == AcceptanceCriterion.THRESHOLD.value:
            # 阈值接受准则
            return 1.0 if delta < self.config.threshold else 0.0
            
        elif criterion == AcceptanceCriterion.TANH.value:
            # 自定义tanh接受准则
            return 0.5 * (1 + np.tanh(-(delta - self.config.shift_factor) / self.config.scale_factor))
            
        elif criterion == AcceptanceCriterion.BOLTZMANN.value:
            # Boltzmann接受准则
            return 1.0 / (1.0 + np.exp(delta / temperature))
            
        else:
            return np.exp(-delta / temperature) if delta > 0 else 1.0
    
    def _temperature_schedule(self, iteration: int, initial_temp: float, 
                             current_temp: float, best_length: float, 
                             current_length: float) -> float:
        """温度调度函数"""
        schedule = self.config.cooling_schedule
        
        if schedule == CoolingSchedule.EXPONENTIAL.value:
            alpha = self.config.cooling_rate
            return initial_temp * (alpha ** iteration)
            
        elif schedule == CoolingSchedule.LINEAR.value:
            alpha = self.config.cooling_rate
            return initial_temp * (1 - alpha * iteration / self.max_iterations)
            
        elif schedule == CoolingSchedule.LOGARITHMIC.value:
            return initial_temp / np.log(iteration + 2)
            
        elif schedule == CoolingSchedule.ADAPTIVE.value:
            # 自适应降温 - 基于搜索进度
            if len(self.history) > 50:
                recent_improvement = max(self.history[-50:]) - min(self.history[-50:])
                if recent_improvement < 0.01 * best_length:
                    return current_temp * 0.7  # 快速降温
            return current_temp * 0.95
            
        elif schedule == CoolingSchedule.QUADRATIC.value:
            # 二次降温
            return initial_temp / (1 + self.config.cooling_rate * (iteration ** 2))
            
        else:  # 默认指数降温
            alpha = 0.99
            return initial_temp * (alpha ** iteration)
    
    def _initial_temperature(self, initial_tour: np.ndarray, initial_length: float) -> float:
        """初始温度计算"""
        method = self.config.init_temp_method
        
        if method == 'fixed':
            return self.config.initial_temperature
            
        elif method == 'percentile':
            # 基于初始解差异的百分位数
            num_samples = self.config.num_samples
            deltas = []
            
            for _ in range(num_samples):
                new_tour, new_length = self._get_neighbor(initial_tour)
                deltas.append(abs(new_length - initial_length))
            
            percentile = self.config.percentile
            return np.percentile(deltas, percentile)
            
        elif method == 'heuristic':
            # 基于问题规模的启发式
            return self.tsp.n_cities * 100
            
        elif method == 'auto':
            # 自动计算初始温度，使初始接受概率约为0.8
            num_samples = 100
            deltas = []
            
            for _ in range(num_samples):
                new_tour, new_length = self._get_neighbor(initial_tour)
                deltas.append(new_length - initial_length)
            
            positive_deltas = [d for d in deltas if d > 0]
            if positive_deltas:
                # 计算使平均接受概率为0.8的温度
                avg_delta = np.mean(positive_deltas)
                return -avg_delta / np.log(0.8)
            else:
                return 1000  # 默认值
        else:
            return 1000  # 默认值
    
    def solve(self, max_iterations: int = 10000, max_time: float = 60, 
              callback: Optional[Callable] = None) -> Tuple[np.ndarray, float, List]:
        """运行模拟退火算法"""
        start_time = time.time()
        self.max_iterations = max_iterations
        
        # 初始化
        current_tour, current_length = self._initialize_tour()
        initial_temp = self._initial_temperature(current_tour, current_length)
        temperature = initial_temp
        
        # 记录最佳解
        if current_length < self.best_length:
            self.best_tour = current_tour.copy()
            self.best_length = current_length
        
        self.history = [current_length]
        self.temperature_history = [temperature]
        self.acceptance_history = [1.0]  # 初始接受率为1
        
        # 主循环
        iteration = 0
        accept_count = 0
        
        while iteration < max_iterations and time.time() - start_time < max_time:
            # 生成邻域解
            new_tour, new_length = self._get_neighbor(current_tour)
            delta = new_length - current_length
            
            # 决定是否接受新解
            accept_prob = self._acceptance_probability(delta, temperature)
            accept = delta < 0 or np.random.rand() < accept_prob
            
            if accept:
                current_tour, current_length = new_tour, new_length
                accept_count += 1
                
                # 更新最佳解
                if current_length < self.best_length:
                    self.best_tour = current_tour.copy()
                    self.best_length = current_length
                    if callback:
                        callback(iteration, self.best_length, temperature, accept_prob, "New best solution found")
            
            # 记录历史
            self.history.append(current_length)
            self.temperature_history.append(temperature)
            self.acceptance_history.append(accept_prob if delta > 0 else 1.0)
            
            # 更新温度
            temperature = self._temperature_schedule(
                iteration, initial_temp, temperature, 
                self.best_length, current_length
            )
            
            # 应用局部搜索（如果配置）
            if (self.config.use_local_search and 
                iteration % self.config.local_search_frequency == 0 and 
                iteration > 0):
                current_tour, current_length = self._local_search(current_tour, current_length)
                
                # 更新最佳解
                if current_length < self.best_length:
                    self.best_tour = current_tour.copy()
                    self.best_length = current_length
                    if callback:
                        callback(iteration, self.best_length, temperature, accept_prob, "Improved by local search")
            
            # 回调函数
            if callback and iteration % 100 == 0:
                callback(iteration, self.best_length, temperature, accept_prob, "")
            
            iteration += 1
        
        self.execution_time = time.time() - start_time
        logger.info(f"SA completed. Iterations: {iteration}, Best length: {self.best_length:.2f}")
        return self.best_tour, self.best_length, self.history
    
    def _local_search(self, tour: np.ndarray, length: float) -> Tuple[np.ndarray, float]:
        """局部搜索：2-opt和3-opt的组合"""
        # 70%概率使用2-opt，30%概率使用3-opt
        if np.random.rand() < 0.7:
            return self._two_opt(tour, length)
        else:
            return self._three_opt(tour, length)
    
    def _two_opt(self, tour: np.ndarray, length: float) -> Tuple[np.ndarray, float]:
        """2-opt局部搜索"""
        best_tour = tour.copy()
        best_length = length
        n = len(tour)
        improved = True
        
        while improved:
            improved = False
            for i in range(1, n - 2):
                for j in range(i + 1, n):
                    if j - i == 1:
                        continue
                    
                    # 尝试2-opt交换
                    new_tour = best_tour.copy()
                    new_tour[i:j] = best_tour[i:j][::-1]
                    new_length = self.tsp.evaluate_tour(new_tour)
                    
                    if new_length < best_length:
                        best_tour, best_length = new_tour, new_length
                        improved = True
                        break  # 找到一个改进就重新开始搜索
                if improved:
                    break
        
        return best_tour, best_length
    
    def _three_opt(self, tour: np.ndarray, length: float) -> Tuple[np.ndarray, float]:
        """3-opt局部搜索"""
        best_tour = tour.copy()
        best_length = length
        n = len(tour)
        improved = True
        
        while improved:
            improved = False
            for i in range(1, n - 4):
                for j in range(i + 2, n - 2):
                    for k in range(j + 2, n):
                        if k - i <= 2:
                            continue
                            
                        # 尝试所有3-opt可能的交换
                        for option in range(1, 8):
                            new_tour = self._three_opt_swap(best_tour, i, j, k, option)
                            new_length = self.tsp.evaluate_tour(new_tour)
                            
                            if new_length < best_length:
                                best_tour, best_length = new_tour, new_length
                                improved = True
                                break  # 找到一个改进就重新开始搜索
                        if improved:
                            break
                    if improved:
                        break
                if improved:
                    break
        
        return best_tour, best_length
    
    def _three_opt_swap(self, tour: np.ndarray, i: int, j: int, k: int, option: int) -> np.ndarray:
        """执行3-opt交换的特定变体"""
        # 3-opt有7种可能的交换方式
        if option == 1:
            # 原始顺序
            return tour.copy()
        elif option == 2:
            # 交换段 [i, j) 和 [j, k)
            new_tour = np.concatenate([tour[:i], tour[j:k], tour[i:j], tour[k:]])
            return new_tour
        elif option == 3:
            # 交换段 [i, j) 和反转 [j, k)
            new_tour = np.concatenate([tour[:i], tour[j:k][::-1], tour[i:j], tour[k:]])
            return new_tour
        elif option == 4:
            # 交换段 [i, j) 反转和 [j, k)
            new_tour = np.concatenate([tour[:i], tour[j:k], tour[i:j][::-1], tour[k:]])
            return new_tour
        elif option == 5:
            # 交换段 [i, j) 和 [j, k) 都反转
            new_tour = np.concatenate([tour[:i], tour[j:k][::-1], tour[i:j][::-1], tour[k:]])
            return new_tour
        elif option == 6:
            # 交换段 [i, j) 和 [j, k) 并反转中间段
            new_tour = np.concatenate([tour[:i], tour[j:k], tour[i:j], tour[k:]])
            new_tour[i:k] = new_tour[i:k][::-1]
            return new_tour
        else:  # option == 7
            # 另一种交换方式
            new_tour = np.concatenate([tour[:i], tour[i:j][::-1], tour[j:k][::-1], tour[k:]])
            return new_tour

class GeneticAlgorithm(BaseSolver):
    """遗传算法求解TSP"""
    def __init__(self, tsp_instance: TSPInstance, config: GAConfig):
        super().__init__(tsp_instance)
        self.config = config
        self.population = []
        self.fitness = []
        
    def _initialize_population(self):
        """初始化种群"""
        self.population = []
        for _ in range(self.config.population_size):
            # 70%概率使用贪婪初始化，30%概率使用随机初始化
            if np.random.rand() < 0.7:
                tour = self._greedy_initialization()
            else:
                tour = np.random.permutation(self.tsp.n_cities)
            self.population.append(tour)
        
        # 计算适应度
        self.fitness = [1 / self.tsp.evaluate_tour(tour) for tour in self.population]
    
    def _greedy_initialization(self) -> np.ndarray:
        """贪婪算法初始化路径"""
        tour = [np.random.randint(self.tsp.n_cities)]
        unvisited = set(range(self.tsp.n_cities)) - {tour[0]}
        
        while unvisited:
            current_city = tour[-1]
            # 找到最近的未访问城市
            next_city = min(unvisited, key=lambda city: self.tsp.distance_matrix[current_city, city])
            tour.append(next_city)
            unvisited.remove(next_city)
            
        return np.array(tour)
    
    def _selection(self):
        """选择操作"""
        if self.config.selection_method == "roulette":
            # 轮盘赌选择
            total_fitness = sum(self.fitness)
            probabilities = [f / total_fitness for f in self.fitness]
            selected_indices = np.random.choice(
                range(len(self.population)), 
                size=len(self.population) - self.config.elitism_count, 
                p=probabilities,
                replace=True
            )
            return [self.population[i] for i in selected_indices]
            
        elif self.config.selection_method == "tournament":
            # 锦标赛选择
            selected = []
            for _ in range(len(self.population) - self.config.elitism_count):
                # 随机选择k个个体
                contestants = np.random.choice(range(len(self.population)), self.config.tournament_size, replace=False)
                # 选择适应度最高的
                winner = max(contestants, key=lambda i: self.fitness[i])
                selected.append(self.population[winner])
            return selected
            
        elif self.config.selection_method == "rank":
            # 排序选择
            sorted_indices = np.argsort(self.fitness)[::-1]  # 从高到低排序
            ranks = np.arange(1, len(self.population) + 1)
            probabilities = ranks / sum(ranks)
            selected_indices = np.random.choice(
                sorted_indices, 
                size=len(self.population) - self.config.elitism_count, 
                p=probabilities,
                replace=True
            )
            return [self.population[i] for i in selected_indices]
    
    def _crossover(self, parent1, parent2):
        """交叉操作"""
        if self.config.crossover_operator == "OX":
            return self._order_crossover(parent1, parent2)
        elif self.config.crossover_operator == "PMX":
            return self._partially_mapped_crossover(parent1, parent2)
        elif self.config.crossover_operator == "CX":
            return self._cycle_crossover(parent1, parent2)
        else:
            return self._order_crossover(parent1, parent2)
    
    def _order_crossover(self, parent1, parent2):
        """顺序交叉"""
        n = len(parent1)
        # 选择两个随机点
        i, j = np.sort(np.random.choice(n, 2, replace=False))
        
        # 创建子代
        child = np.full(n, -1, dtype=int)
        
        # 从parent1复制段
        child[i:j+1] = parent1[i:j+1]
        
        # 从parent2填充剩余位置
        pointer = (j + 1) % n
        for gene in np.roll(parent2, -j-1):
            if gene not in child:
                child[pointer] = gene
                pointer = (pointer + 1) % n
                
        return child
    
    def _partially_mapped_crossover(self, parent1, parent2):
        """部分映射交叉"""
        n = len(parent1)
        # 选择两个随机点
        i, j = np.sort(np.random.choice(n, 2, replace=False))
        
        # 创建子代
        child = np.full(n, -1, dtype=int)
        
        # 从parent1复制段
        child[i:j+1] = parent1[i:j+1]
        
        # 创建映射关系
        mapping = {}
        for idx in range(i, j+1):
            if parent2[idx] not in child:
                mapping[parent1[idx]] = parent2[idx]
        
        # 从parent2填充剩余位置
        for idx in range(n):
            if idx < i or idx > j:
                gene = parent2[idx]
                while gene in mapping:
                    gene = mapping[gene]
                child[idx] = gene
                
        return child
    
    def _cycle_crossover(self, parent1, parent2):
        """循环交叉"""
        n = len(parent1)
        child = np.full(n, -1, dtype=int)
        
        # 查找循环
        cycles = []
        visited = set()
        
        for i in range(n):
            if i not in visited:
                cycle = []
                current = i
                
                while current not in visited:
                    visited.add(current)
                    cycle.append(current)
                    current = np.where(parent1 == parent2[current])[0][0]
                
                cycles.append(cycle)
        
        # 交替从父母中选择循环
        for i, cycle in enumerate(cycles):
            if i % 2 == 0:  # 从parent1复制
                for idx in cycle:
                    child[idx] = parent1[idx]
            else:  # 从parent2复制
                for idx in cycle:
                    child[idx] = parent2[idx]
                    
        return child
    
    def _mutation(self, individual):
        """变异操作"""
        n = len(individual)
        
        # 随机选择变异操作
        mutation_type = np.random.choice(["swap", "inversion", "insertion"])
        
        if mutation_type == "swap":
            # 交换两个城市
            i, j = np.random.choice(n, 2, replace=False)
            individual[i], individual[j] = individual[j], individual[i]
            
        elif mutation_type == "inversion":
            # 逆序一段路径
            i, j = np.sort(np.random.choice(n, 2, replace=False))
            individual[i:j+1] = individual[i:j+1][::-1]
            
        elif mutation_type == "insertion":
            # 插入一个城市到新位置
            i, j = np.random.choice(n, 2, replace=False)
            city = individual[i]
            individual = np.delete(individual, i)
            individual = np.insert(individual, j, city)
            
        return individual
    
    def solve(self, max_iterations: int = 1000, max_time: float = 60, 
              callback: Optional[Callable] = None) -> Tuple[np.ndarray, float, List]:
        """运行遗传算法"""
        start_time = time.time()
        self.max_iterations = max_iterations
        
        # 初始化种群
        self._initialize_population()
        
        # 记录最佳解
        best_idx = np.argmax(self.fitness)
        self.best_tour = self.population[best_idx].copy()
        self.best_length = 1 / self.fitness[best_idx]
        self.history = [self.best_length]
        
        # 主循环
        iteration = 0
        
        while iteration < max_iterations and time.time() - start_time < max_time:
            # 选择精英
            elite_indices = np.argsort(self.fitness)[-self.config.elitism_count:]
            elite = [self.population[i] for i in elite_indices]
            
            # 选择
            selected = self._selection()
            
            # 交叉
            new_population = []
            for i in range(0, len(selected), 2):
                if i + 1 < len(selected):
                    parent1, parent2 = selected[i], selected[i+1]
                    if np.random.rand() < self.config.crossover_rate:
                        child1 = self._crossover(parent1, parent2)
                        child2 = self._crossover(parent2, parent1)
                        new_population.extend([child1, child2])
                    else:
                        new_population.extend([parent1, parent2])
            
            # 变异
            for i in range(len(new_population)):
                if np.random.rand() < self.config.mutation_rate:
                    new_population[i] = self._mutation(new_population[i])
            
            # 添加精英
            new_population.extend(elite)
            
            # 更新种群
            self.population = new_population
            
            # 计算适应度
            self.fitness = [1 / self.tsp.evaluate_tour(tour) for tour in self.population]
            
            # 更新最佳解
            best_idx = np.argmax(self.fitness)
            current_best_length = 1 / self.fitness[best_idx]
            
            if current_best_length < self.best_length:
                self.best_tour = self.population[best_idx].copy()
                self.best_length = current_best_length
                if callback:
                    callback(iteration, self.best_length, 0, 0, "New best solution found")
            
            # 记录历史
            self.history.append(self.best_length)
            
            # 回调函数
            if callback and iteration % 10 == 0:
                callback(iteration, self.best_length, 0, 0, "")
            
            iteration += 1
        
        self.execution_time = time.time() - start_time
        logger.info(f"GA completed. Generations: {iteration}, Best length: {self.best_length:.2f}")
        return self.best_tour, self.best_length, self.history

class AntColonyOptimization(BaseSolver):
    """蚁群算法求解TSP"""
    def __init__(self, tsp_instance: TSPInstance, config: ACOConfig):
        super().__init__(tsp_instance)
        self.config = config
        self.pheromone = np.full((tsp_instance.n_cities, tsp_instance.n_cities), 
                                self.config.initial_pheromone)
        np.fill_diagonal(self.pheromone, 0)  # 对角线设为0
        
    def _construct_solutions(self):
        """构建蚂蚁的解决方案"""
        solutions = []
        solution_lengths = []
        
        for _ in range(self.config.num_ants):
            # 每只蚂蚁从随机城市开始
            current_city = np.random.randint(self.tsp.n_cities)
            unvisited = set(range(self.tsp.n_cities))
            unvisited.remove(current_city)
            solution = [current_city]
            
            # 构建完整路径
            while unvisited:
                # 计算转移概率
                probabilities = self._calculate_probabilities(current_city, unvisited)
                
                # 选择下一个城市
                if np.random.rand() < self.config.q0:
                    # 贪婪选择
                    next_city = max(unvisited, key=lambda city: probabilities[city])
                else:
                    # 概率选择
                    cities = list(unvisited)
                    probs = [probabilities[city] for city in cities]
                    probs = probs / np.sum(probs)  # 归一化
                    next_city = np.random.choice(cities, p=probs)
                
                solution.append(next_city)
                unvisited.remove(next_city)
                current_city = next_city
            
            solutions.append(solution)
            solution_lengths.append(self.tsp.evaluate_tour(solution))
        
        return solutions, solution_lengths
    
    def _calculate_probabilities(self, current_city, unvisited):
        """计算转移到未访问城市的概率"""
        probabilities = {}
        total = 0
        
        for city in unvisited:
            # 信息素和启发式信息的组合
            pheromone = self.pheromone[current_city, city] ** self.config.alpha
            heuristic = (1 / self.tsp.distance_matrix[current_city, city]) ** self.config.beta
            probabilities[city] = pheromone * heuristic
            total += probabilities[city]
        
        # 归一化
        for city in unvisited:
            probabilities[city] /= total
            
        return probabilities
    
    def _update_pheromone(self, solutions, solution_lengths):
        """更新信息素"""
        # 信息素蒸发
        self.pheromone *= (1 - self.config.evaporation_rate)
        
        # 信息素沉积
        for solution, length in zip(solutions, solution_lengths):
            for i in range(len(solution) - 1):
                city_from, city_to = solution[i], solution[i+1]
                self.pheromone[city_from, city_to] += 1 / length
                self.pheromone[city_to, city_from] += 1 / length  # 对称矩阵
    
    def solve(self, max_iterations: int = 100, max_time: float = 60, 
              callback: Optional[Callable] = None) -> Tuple[np.ndarray, float, List]:
        """运行蚁群算法"""
        start_time = time.time()
        self.max_iterations = max_iterations
        
        # 初始化最佳解
        self.best_tour = np.random.permutation(self.tsp.n_cities)
        self.best_length = self.tsp.evaluate_tour(self.best_tour)
        self.history = [self.best_length]
        
        # 主循环
        iteration = 0
        
        while iteration < max_iterations and time.time() - start_time < max_time:
            # 构建解决方案
            solutions, solution_lengths = self._construct_solutions()
            
            # 更新信息素
            self._update_pheromone(solutions, solution_lengths)
            
            # 更新最佳解
            best_idx = np.argmin(solution_lengths)
            current_best_length = solution_lengths[best_idx]
            
            if current_best_length < self.best_length:
                self.best_tour = solutions[best_idx]
                self.best_length = current_best_length
                if callback:
                    callback(iteration, self.best_length, 0, 0, "New best solution found")
            
            # 记录历史
            self.history.append(self.best_length)
            
            # 回调函数
            if callback and iteration % 5 == 0:
                callback(iteration, self.best_length, 0, 0, "")
            
            iteration += 1
        
        self.execution_time = time.time() - start_time
        logger.info(f"ACO completed. Iterations: {iteration}, Best length: {self.best_length:.2f}")
        return self.best_tour, self.best_length, self.history

class BayesianOptimizer:
    """贝叶斯优化器类"""
    def __init__(self, tsp_instance: TSPInstance, n_init: int = 10, n_iter: int = 50, 
                 n_jobs: int = -1, output_dir: str = "bo_results"):
        self.tsp = tsp_instance
        self.n_init = n_init
        self.n_iter = n_iter
        self.n_jobs = n_jobs if n_jobs > 0 else os.cpu_count()
        self.output_dir = output_dir
        self.X = []  # 配置参数
        self.y = []  # 目标函数值
        self.configs = []  # 保存完整的配置对象
        self.gp = self._create_gp_model()
        self.study = None
        
        # 创建输出目录
        Path(output_dir).mkdir(exist_ok=True)
        
    def _create_gp_model(self) -> GaussianProcessRegressor:
        """创建高斯过程回归模型"""
        kernel = ConstantKernel(1.0) * Matern(length_scale=1.0, nu=2.5) + WhiteKernel(noise_level=1.0)
        return GaussianProcessRegressor(kernel=kernel, n_restarts_optimizer=10, alpha=1e-4)
    
    def _objective(self, trial) -> float:
        """Optuna目标函数"""
        # 定义超参数空间
        config = SAConfig()
        
        # 初始温度方法
        init_temp_method = trial.suggest_categorical('init_temp_method', ['fixed', 'percentile', 'heuristic', 'auto'])
        config.init_temp_method = init_temp_method
        
        if init_temp_method == 'fixed':
            config.initial_temperature = trial.suggest_float('initial_temperature', 100, 5000, log=True)
        
        # 降温策略
        cooling_schedule = trial.suggest_categorical('cooling_schedule', 
                                                    [s.value for s in CoolingSchedule])
        config.cooling_schedule = cooling_schedule
        config.cooling_rate = trial.suggest_float('cooling_rate', 0.9, 0.9999)
        
        # 接受准则
        acceptance_criterion = trial.suggest_categorical('acceptance_criterion', 
                                                        [c.value for c in AcceptanceCriterion])
        config.acceptance_criterion = acceptance_criterion
        
        if acceptance_criterion == AcceptanceCriterion.THRESHOLD.value:
            config.threshold = trial.suggest_float('threshold', 0.01, 0.5)
        elif acceptance_criterion == AcceptanceCriterion.TANH.value:
            config.scale_factor = trial.suggest_float('scale_factor', 10, 200)
            config.shift_factor = trial.suggest_float('shift_factor', 10, 100)
        
        # 变异算子权重
        config.mutation_weights = {
            MutationOperator.SWAP.value: trial.suggest_float('weight_swap', 0.1, 0.8),
            MutationOperator.INVERSION.value: trial.suggest_float('weight_inversion', 0.1, 0.8),
            MutationOperator.INSERTION.value: trial.suggest_float('weight_insertion', 0.1, 0.8),
            MutationOperator.SCRAMBLE.value: trial.suggest_float('weight_scramble', 0.01, 0.2),
            MutationOperator.REVERSE.value: trial.suggest_float('weight_reverse', 0.01, 0.2)
        }
        
        # 归一化权重
        total = sum(config.mutation_weights.values())
        for key in config.mutation_weights:
            config.mutation_weights[key] /= total
        
        # 局部搜索
        config.use_local_search = trial.suggest_categorical('use_local_search', [True, False])
        if config.use_local_search:
            config.local_search_frequency = trial.suggest_int('local_search_frequency', 50, 500)
        
        # 评估配置
        score = self._evaluate_config(config)
        
        # 保存配置和结果
        self.configs.append(config)
        self.X.append(self._config_to_vector(config))
        self.y.append(score)
        
        return score
    
    def _evaluate_config(self, config: SAConfig, n_runs: int = 3) -> float:
        """评估配置的性能"""
        scores = []
        
        # 使用进程池并行评估
        with ProcessPoolExecutor(max_workers=self.n_jobs) as executor:
            futures = []
            for _ in range(n_runs):
                sa = ConfigurableSA(self.tsp, config)
                futures.append(executor.submit(
                    sa.run, 
                    max_iterations=2000,  # 减少迭代次数以加快评估
                    max_time=30  # 限制评估时间
                ))
            
            for future in as_completed(futures):
                _, best_length, _ = future.result()
                scores.append(best_length)
        
        return np.mean(scores)
    
    def optimize(self) -> Tuple[SAConfig, float]:
        """执行贝叶斯优化"""
        logger.info("Starting Bayesian optimization...")
        
        # 创建Optuna研究
        self.study = optuna.create_study(direction='minimize')
        self.study.optimize(self._objective, n_trials=self.n_init + self.n_iter)
        
        # 获取最佳配置
        best_trial = self.study.best_trial
        best_config = self.configs[best_trial.number]
        best_score = best_trial.value
        
        # 保存优化结果
        self._save_results()
        
        logger.info(f"Bayesian optimization completed. Best score: {best_score:.2f}")
        return best_config, best_score
    
    def _config_to_vector(self, config: SAConfig) -> np.ndarray:
        """将配置转换为特征向量（用于可视化等目的）"""
        vector = []
        
        # 编码初始温度方法
        methods = ['fixed', 'percentile', 'heuristic', 'auto']
        vector.extend([1 if config.init_temp_method == m else 0 for m in methods])
        
        # 编码初始温度值（如果使用fixed）
        if config.init_temp_method == 'fixed':
            vector.append(config.initial_temperature / 5000)  # 归一化
        else:
            vector.append(0)
        
        # 编码降温策略
        strategies = [s.value for s in CoolingSchedule]
        vector.extend([1 if config.cooling_schedule == s else 0 for s in strategies])
        
        # 编码降温速率
        vector.append(config.cooling_rate)
        
        # 编码接受准则
        criteria = [c.value for c in AcceptanceCriterion]
        vector.extend([1 if config.acceptance_criterion == c else 0 for c in criteria])
        
        # 编码自定义接受准则参数
        if config.acceptance_criterion == AcceptanceCriterion.TANH.value:
            vector.append(config.scale_factor / 200)  # 归一化
            vector.append(config.shift_factor / 100)   # 归一化
        else:
            vector.extend([0, 0])
        
        if config.acceptance_criterion == AcceptanceCriterion.THRESHOLD.value:
            vector.append(config.threshold)
        else:
            vector.append(0)
        
        # 编码变异算子权重
        operators = [op.value for op in MutationOperator]
        for op in operators:
            vector.append(config.mutation_weights.get(op, 0))
        
        # 编码是否使用局部搜索
        vector.append(1 if config.use_local_search else 0)
        
        if config.use_local_search:
            vector.append(config.local_search_frequency / 500)  # 归一化
        else:
            vector.append(0)
        
        return np.array(vector)
    
    def _save_results(self):
        """保存优化结果"""
        # 保存所有试验结果
        results = []
        for i, (config, score) in enumerate(zip(self.configs, self.y)):
            results.append({
                'trial_id': i,
                'score': score,
                'config': config.to_dict()
            })
        
        with open(f"{self.output_dir}/bo_results.json", 'w') as f:
            json.dump(results, f, indent=2)
        
        # 保存最佳配置
        best_config, best_score = self.get_best_result()
        best_result = {
            'best_score': best_score,
            'best_config': best_config.to_dict()
        }
        
        with open(f"{self.output_dir}/best_config.json", 'w') as f:
            json.dump(best_result, f, indent=2)
        
        # 绘制优化过程
        self.plot_optimization_history()
    
    def get_best_result(self) -> Tuple[SAConfig, float]:
        """获取最佳结果"""
        if not self.study:
            return None, float('inf')
        
        best_trial = self.study.best_trial
        return self.configs[best_trial.number], best_trial.value
    
    def plot_optimization_history(self):
        """绘制优化历史"""
        if not self.study:
            return
        
        plt.figure(figsize=(10, 6))
        
        # 获取所有试验的值
        trials = self.study.trials
        values = [trial.value for trial in trials]
        best_values = [min(values[:i+1]) for i in range(len(values))]
        
        plt.plot(range(1, len(values)+1), values, 'o-', alpha=0.5, label='Trial')
        plt.plot(range(1, len(values)+1), best_values, 'r-', linewidth=2, label='Best')
        
        plt.xlabel('Trial')
        plt.ylabel('Tour Length')
        plt.title('Bayesian Optimization History')
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        plt.savefig(f"{self.output_dir}/optimization_history.png", dpi=300, bbox_inches='tight')
        plt.show()

class TSPWorker(QThread):
    """TSP求解工作线程"""
    update_signal = pyqtSignal(int, float, float, float, str)
    finished_signal = pyqtSignal(np.ndarray, float, list, dict)
    
    def __init__(self, tsp_instance, algorithm_type, config, max_iterations, max_time):
        super().__init__()
        self.tsp_instance = tsp_instance
        self.algorithm_type = algorithm_type
        self.config = config
        self.max_iterations = max_iterations
        self.max_time = max_time
        
    def run(self):
        """运行求解算法"""
        if self.algorithm_type == AlgorithmType.SIMULATED_ANNEALING.value:
            solver = ConfigurableSA(self.tsp_instance, self.config)
        elif self.algorithm_type == AlgorithmType.GENETIC_ALGORITHM.value:
            solver = GeneticAlgorithm(self.tsp_instance, self.config)
        elif self.algorithm_type == AlgorithmType.ANT_COLONY.value:
            solver = AntColonyOptimization(self.tsp_instance, self.config)
        else:
            solver = ConfigurableSA(self.tsp_instance, self.config)
        
        # 定义回调函数
        def callback(iteration, best_length, temperature, accept_prob, message):
            self.update_signal.emit(iteration, best_length, temperature, accept_prob, message)
        
        # 运行求解器
        best_tour, best_length, history = solver.solve(
            max_iterations=self.max_iterations,
            max_time=self.max_time,
            callback=callback
        )
        
        # 获取统计信息
        stats = solver.get_stats()
        
        # 发送完成信号
        self.finished_signal.emit(best_tour, best_length, history, stats)

class TSPGUI(QMainWindow):
    """TSP求解器图形用户界面"""
    def __init__(self):
        super().__init__()
        self.tsp_instance = None
        self.current_tour = None
        self.current_length = float('inf')
        self.history = []
        self.stats = {}
        self.results = {}  # 存储不同算法的结果
        
        self.init_ui()
        
    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle('TSP求解器')
        self.setGeometry(100, 100, 1200, 800)
        
        # 创建中心部件和主布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # 创建左侧控制面板
        control_panel = QWidget()
        control_layout = QVBoxLayout(control_panel)
        control_panel.setMaximumWidth(400)
        
        # 创建选项卡
        tabs = QTabWidget()
        control_layout.addWidget(tabs)
        
        # 问题设置选项卡
        problem_tab = QWidget()
        problem_layout = QVBoxLayout(problem_tab)
        
        # 问题实例选择
        problem_group = QGroupBox("问题实例")
        problem_group_layout = QVBoxLayout(problem_group)
        
        load_btn = QPushButton("加载TSP实例")
        load_btn.clicked.connect(self.load_tsp_instance)
        problem_group_layout.addWidget(load_btn)
        
        self.problem_info = QLabel("未加载问题实例")
        problem_group_layout.addWidget(self.problem_info)
        
        problem_layout.addWidget(problem_group)
        
        # 算法选择
        algorithm_group = QGroupBox("算法选择")
        algorithm_group_layout = QVBoxLayout(algorithm_group)
        
        self.algorithm_combo = QComboBox()
        self.algorithm_combo.addItems(["模拟退火", "遗传算法", "蚁群算法"])
        algorithm_group_layout.addWidget(QLabel("选择算法:"))
        algorithm_group_layout.addWidget(self.algorithm_combo)
        
        # 算法参数
        self.algorithm_params = QTabWidget()
        
        # 模拟退火参数
        sa_params = QWidget()
        sa_layout = QVBoxLayout(sa_params)
        
        # 初始温度
        sa_layout.addWidget(QLabel("初始温度:"))
        self.sa_init_temp = QDoubleSpinBox()
        self.sa_init_temp.setRange(100, 10000)
        self.sa_init_temp.setValue(1000)
        sa_layout.addWidget(self.sa_init_temp)
        
        # 降温策略
        sa_layout.addWidget(QLabel("降温策略:"))
        self.sa_cooling = QComboBox()
        self.sa_cooling.addItems(["指数降温", "线性降温", "对数降温", "自适应降温", "二次降温"])
        sa_layout.addWidget(self.sa_cooling)
        
        # 降温速率
        sa_layout.addWidget(QLabel("降温速率:"))
        self.sa_cooling_rate = QDoubleSpinBox()
        self.sa_cooling_rate.setRange(0.8, 0.9999)
        self.sa_cooling_rate.setValue(0.99)
        self.sa_cooling_rate.setSingleStep(0.001)
        sa_layout.addWidget(self.sa_cooling_rate)
        
        # 接受准则
        sa_layout.addWidget(QLabel("接受准则:"))
        self.sa_acceptance = QComboBox()
        self.sa_acceptance.addItems(["Metropolis", "阈值接受", "Tanh", "Boltzmann"])
        sa_layout.addWidget(self.sa_acceptance)
        
        sa_layout.addStretch()
        self.algorithm_params.addTab(sa_params, "模拟退火")
        
        # 遗传算法参数
        ga_params = QWidget()
        ga_layout = QVBoxLayout(ga_params)
        
        # 种群大小
        ga_layout.addWidget(QLabel("种群大小:"))
        self.ga_pop_size = QSpinBox()
        self.ga_pop_size.setRange(10, 500)
        self.ga_pop_size.setValue(100)
        ga_layout.addWidget(self.ga_pop_size)
        
        # 交叉率
        ga_layout.addWidget(QLabel("交叉率:"))
        self.ga_crossover_rate = QDoubleSpinBox()
        self.ga_crossover_rate.setRange(0.1, 1.0)
        self.ga_crossover_rate.setValue(0.8)
        ga_layout.addWidget(self.ga_crossover_rate)
        
        # 变异率
        ga_layout.addWidget(QLabel("变异率:"))
        self.ga_mutation_rate = QDoubleSpinBox()
        self.ga_mutation_rate.setRange(0.01, 0.5)
        self.ga_mutation_rate.setValue(0.2)
        ga_layout.addWidget(self.ga_mutation_rate)
        
        ga_layout.addStretch()
        self.algorithm_params.addTab(ga_params, "遗传算法")
        
        # 蚁群算法参数
        aco_params = QWidget()
        aco_layout = QVBoxLayout(aco_params)
        
        # 蚂蚁数量
        aco_layout.addWidget(QLabel("蚂蚁数量:"))
        self.aco_num_ants = QSpinBox()
        self.aco_num_ants.setRange(10, 200)
        self.aco_num_ants.setValue(50)
        aco_layout.addWidget(self.aco_num_ants)
        
        # 信息素重要程度
        aco_layout.addWidget(QLabel("信息素重要程度:"))
        self.aco_alpha = QDoubleSpinBox()
        self.aco_alpha.setRange(0.1, 5.0)
        self.aco_alpha.setValue(1.0)
        aco_layout.addWidget(self.aco_alpha)
        
        # 启发式信息重要程度
        aco_layout.addWidget(QLabel("启发式信息重要程度:"))
        self.aco_beta = QDoubleSpinBox()
        self.aco_beta.setRange(0.1, 5.0)
        self.aco_beta.setValue(2.0)
        aco_layout.addWidget(self.aco_beta)
        
        aco_layout.addStretch()
        self.algorithm_params.addTab(aco_params, "蚁群算法")
        
        algorithm_group_layout.addWidget(self.algorithm_params)
        problem_layout.addWidget(algorithm_group)
        
        # 运行参数
        run_group = QGroupBox("运行参数")
        run_layout = QVBoxLayout(run_group)
        
        run_layout.addWidget(QLabel("最大迭代次数:"))
        self.max_iterations = QSpinBox()
        self.max_iterations.setRange(100, 1000000)
        self.max_iterations.setValue(10000)
        run_layout.addWidget(self.max_iterations)
        
        run_layout.addWidget(QLabel("最大运行时间(秒):"))
        self.max_time = QSpinBox()
        self.max_time.setRange(10, 3600)
        self.max_time.setValue(60)
        run_layout.addWidget(self.max_time)
        
        run_layout.addStretch()
        problem_layout.addWidget(run_group)
        
        # 运行按钮
        self.run_btn = QPushButton("运行求解")
        self.run_btn.clicked.connect(self.run_solver)
        problem_layout.addWidget(self.run_btn)
        
        tabs.addTab(problem_tab, "问题设置")
        
        # 结果选项卡
        results_tab = QWidget()
        results_layout = QVBoxLayout(results_tab)
        
        # 结果信息
        self.results_info = QLabel("尚未运行求解")
        results_layout.addWidget(self.results_info)
        
        # 结果比较表
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(5)
        self.results_table.setHorizontalHeaderLabels(["算法", "路径长度", "运行时间", "迭代次数", "改进"])
        results_layout.addWidget(self.results_table)
        
        tabs.addTab(results_tab, "结果比较")
        
        # 添加到主布局
        main_layout.addWidget(control_panel)
        
        # 创建右侧可视化区域
        vis_widget = QWidget()
        vis_layout = QVBoxLayout(vis_widget)
        
        # 创建matplotlib画布
        self.canvas = MplCanvas(self, width=8, height=6, dpi=100)
        vis_layout.addWidget(self.canvas)
        
        # 进度条
        self.progress_bar = QProgressBar()
        vis_layout.addWidget(self.progress_bar)
        
        # 状态信息
        self.status_text = QTextEdit()
        self.status_text.setMaximumHeight(100)
        vis_layout.addWidget(self.status_text)
        
        main_layout.addWidget(vis_widget)
        
        # 连接算法选择变化事件
        self.algorithm_combo.currentIndexChanged.connect(self.on_algorithm_changed)
        self.on_algorithm_changed(0)  # 初始化显示
        
    def on_algorithm_changed(self, index):
        """算法选择变化时的处理"""
        self.algorithm_params.setCurrentIndex(index)
        
    def load_tsp_instance(self):
        """加载TSP实例"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "打开TSP实例", "", "TSP Files (*.tsp);;JSON Files (*.json);;All Files (*)"
        )
        
        if file_path:
            try:
                if file_path.endswith('.json'):
                    self.tsp_instance = TSPInstance.load(file_path)
                else:
                    self.tsp_instance = self.load_tsplib_instance(file_path)
                
                self.problem_info.setText(
                    f"已加载: {self.tsp_instance.name}\n"
                    f"城市数量: {self.tsp_instance.n_cities}\n"
                    f"最优解长度: 未知"
                )
                
                # 绘制城市分布
                self.plot_cities()
                
            except Exception as e:
                QMessageBox.critical(self, "错误", f"加载TSP实例时出错: {str(e)}")
    
    def load_tsplib_instance(self, filepath: str) -> TSPInstance:
        """从TSPLIB文件加载TSP实例"""
        coordinates = []
        name = Path(filepath).stem
        read_coords = False
        
        with open(filepath, 'r') as f:
            for line in f:
                line = line.strip()
                if line == "NODE_COORD_SECTION":
                    read_coords = True
                    continue
                elif line == "EOF":
                    break
                    
                if read_coords and line:
                    parts = line.split()
                    if len(parts) >= 3:
                        try:
                            # 忽略索引，只取坐标
                            x, y = float(parts[1]), float(parts[2])
                            coordinates.append([x, y])
                        except ValueError:
                            continue
        
        return TSPInstance(name, np.array(coordinates))
    
    def plot_cities(self):
        """绘制城市分布"""
        if self.tsp_instance is None:
            return
            
        self.canvas.axes.clear()
        coords = self.tsp_instance.coordinates
        self.canvas.axes.plot(coords[:, 0], coords[:, 1], 'o', markersize=4)
        self.canvas.axes.set_title(f"城市分布: {self.tsp_instance.name}")
        self.canvas.axes.set_xlabel("X坐标")
        self.canvas.axes.set_ylabel("Y坐标")
        self.canvas.axes.grid(True, alpha=0.3)
        self.canvas.draw()
    
    def plot_tour(self, tour):
        """绘制路径"""
        if self.tsp_instance is None or tour is None:
            return
            
        self.canvas.axes.clear()
        tour_coords = self.tsp_instance.coordinates[tour]
        tour_coords = np.vstack([tour_coords, tour_coords[0]])  # 闭合路径
        
        self.canvas.axes.plot(tour_coords[:, 0], tour_coords[:, 1], 'o-', linewidth=1, markersize=4)
        
        # 标记起点
        self.canvas.axes.plot(tour_coords[0, 0], tour_coords[0, 1], 'ro', markersize=8)
        
        self.canvas.axes.set_title(f"最佳路径 (长度: {self.current_length:.2f})")
        self.canvas.axes.set_xlabel("X坐标")
        self.canvas.axes.set_ylabel("Y坐标")
        self.canvas.axes.grid(True, alpha=0.3)
        self.canvas.draw()
    
    def plot_convergence(self):
        """绘制收敛曲线"""
        if not self.history:
            return
            
        self.canvas.axes.clear()
        self.canvas.axes.plot(self.history)
        self.canvas.axes.set_title("收敛曲线")
        self.canvas.axes.set_xlabel("迭代次数")
        self.canvas.axes.set_ylabel("路径长度")
        self.canvas.axes.grid(True, alpha=0.3)
        self.canvas.draw()
    
    def run_solver(self):
        """运行求解器"""
        if self.tsp_instance is None:
            QMessageBox.warning(self, "警告", "请先加载TSP实例")
            return
            
        # 获取算法类型
        algorithm_type = self.algorithm_combo.currentIndex()
        algorithm_map = {
            0: AlgorithmType.SIMULATED_ANNEALING.value,
            1: AlgorithmType.GENETIC_ALGORITHM.value,
            2: AlgorithmType.ANT_COLONY.value
        }
        algorithm = algorithm_map[algorithm_type]
        
        # 获取配置
        if algorithm == AlgorithmType.SIMULATED_ANNEALING.value:
            config = SAConfig()
            config.initial_temperature = self.sa_init_temp.value()
            
            cooling_map = {
                0: CoolingSchedule.EXPONENTIAL.value,
                1: CoolingSchedule.LINEAR.value,
                2: CoolingSchedule.LOGARITHMIC.value,
                3: CoolingSchedule.ADAPTIVE.value,
                4: CoolingSchedule.QUADRATIC.value
            }
            config.cooling_schedule = cooling_map[self.sa_cooling.currentIndex()]
            config.cooling_rate = self.sa_cooling_rate.value()
            
            acceptance_map = {
                0: AcceptanceCriterion.METROPOLIS.value,
                1: AcceptanceCriterion.THRESHOLD.value,
                2: AcceptanceCriterion.TANH.value,
                3: AcceptanceCriterion.BOLTZMANN.value
            }
            config.acceptance_criterion = acceptance_map[self.sa_acceptance.currentIndex()]
            
        elif algorithm == AlgorithmType.GENETIC_ALGORITHM.value:
            config = GAConfig()
            config.population_size = self.ga_pop_size.value()
            config.crossover_rate = self.ga_crossover_rate.value()
            config.mutation_rate = self.ga_mutation_rate.value()
            
        elif algorithm == AlgorithmType.ANT_COLONY.value:
            config = ACOConfig()
            config.num_ants = self.aco_num_ants.value()
            config.alpha = self.aco_alpha.value()
            config.beta = self.aco_beta.value()
        
        # 禁用运行按钮
        self.run_btn.setEnabled(False)
        
        # 重置进度条
        self.progress_bar.setValue(0)
        self.progress_bar.setMaximum(self.max_iterations.value())
        
        # 清空状态文本
        self.status_text.clear()
        
        # 创建并启动工作线程
        self.worker = TSPWorker(
            self.tsp_instance, algorithm, config, 
            self.max_iterations.value(), self.max_time.value()
        )
        self.worker.update_signal.connect(self.on_update)
        self.worker.finished_signal.connect(self.on_finished)
        self.worker.start()
    
    def on_update(self, iteration, best_length, temperature, accept_prob, message):
        """更新进度和状态"""
        self.progress_bar.setValue(iteration)
        
        if message:
            self.status_text.append(f"迭代 {iteration}: {message}")
        
        # 更新当前最佳解
        if best_length < self.current_length:
            self.current_length = best_length
            # 这里可以添加实时绘制路径的代码，但可能会影响性能
    
    def on_finished(self, best_tour, best_length, history, stats):
        """求解完成处理"""
        self.current_tour = best_tour
        self.current_length = best_length
        self.history = history
        self.stats = stats
        
        # 启用运行按钮
        self.run_btn.setEnabled(True)
        
        # 更新结果信息
        algorithm_name = self.algorithm_combo.currentText()
        self.results_info.setText(
            f"算法: {algorithm_name}\n"
            f"路径长度: {best_length:.2f}\n"
            f"运行时间: {stats['execution_time']:.2f}秒\n"
            f"迭代次数: {stats['iterations']}\n"
            f"改进: {stats['improvement']:.2f}"
        )
        
        # 保存结果用于比较
        self.results[algorithm_name] = {
            'length': best_length,
            'time': stats['execution_time'],
            'iterations': stats['iterations'],
            'improvement': stats['improvement']
        }
        
        # 更新结果比较表
        self.update_results_table()
        
        # 绘制最佳路径
        self.plot_tour(best_tour)
    
    def update_results_table(self):
        """更新结果比较表"""
        self.results_table.setRowCount(len(self.results))
        
        for row, (algo_name, result) in enumerate(self.results.items()):
            self.results_table.setItem(row, 0, QTableWidgetItem(algo_name))
            self.results_table.setItem(row, 1, QTableWidgetItem(f"{result['length']:.2f}"))
            self.results_table.setItem(row, 2, QTableWidgetItem(f"{result['time']:.2f}秒"))
            self.results_table.setItem(row, 3, QTableWidgetItem(str(result['iterations'])))
            self.results_table.setItem(row, 4, QTableWidgetItem(f"{result['improvement']:.2f}"))
        
        # 调整列宽
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

# 创建TSP实例（使用柏林52问题）
def create_berlin52_instance() -> TSPInstance:
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

def main():
    """主函数"""
    # 创建Qt应用
    app = QApplication(sys.argv)
    
    # 创建并显示主窗口
    window = TSPGUI()
    window.show()
    
    # 创建默认的TSP实例
    window.tsp_instance = create_berlin52_instance()
    window.problem_info.setText(
        f"已加载: {window.tsp_instance.name}\n"
        f"城市数量: {window.tsp_instance.n_cities}\n"
        f"最优解长度: 7542 (已知)"
    )
    window.plot_cities()
    
    # 运行应用
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()