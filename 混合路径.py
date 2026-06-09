import numpy as np
import matplotlib.pyplot as plt
from typing import List, Tuple, Dict, Optional
import random
from dataclasses import dataclass
from scipy.spatial import KDTree
import time

@dataclass
class VehicleState:
    x: float
    y: float
    velocity: float
    heading: float
    acceleration: float

@dataclass
class Obstacle:
    x: float
    y: float
    radius: float
    velocity_x: float = 0
    velocity_y: float = 0

class QuantumInspiredOptimizer:
    """
    量子启发式优化器 - 结合量子比特概念和遗传算法
    """
    def __init__(self, population_size: int, chromosome_length: int):
        self.population_size = population_size
        self.chromosome_length = chromosome_length
        self.quantum_population = self.initialize_quantum_population()
        
    def initialize_quantum_population(self) -> np.ndarray:
        """初始化量子种群，每个基因是量子态的叠加"""
        return np.random.uniform(0, np.pi/2, 
                               (self.population_size, self.chromosome_length))
    
    def observe_quantum_state(self, quantum_chromosomes: np.ndarray) -> np.ndarray:
        """量子观测：将量子态坍缩到经典状态"""
        probabilities = np.sin(quantum_chromosomes) ** 2
        return (np.random.random(quantum_chromosomes.shape) < probabilities).astype(float)
    
    def quantum_rotation_gate(self, quantum_chromosomes: np.ndarray, 
                            best_solution: np.ndarray, rotation_angle: float) -> np.ndarray:
        """量子旋转门操作 - 引导搜索方向"""
        direction = np.sign(best_solution - 0.5)
        new_chromosomes = quantum_chromosomes + direction * rotation_angle
        return np.clip(new_chromosomes, 0, np.pi/2)
    
    def quantum_crossover(self, parent1: np.ndarray, parent2: np.ndarray) -> np.ndarray:
        """量子交叉操作 - 保持多样性"""
        alpha = np.random.random()
        child = alpha * parent1 + (1 - alpha) * parent2
        # 添加量子扰动
        quantum_perturbation = np.random.normal(0, 0.1, parent1.shape)
        return child + quantum_perturbation

class PathPlanner:
    """
    基于量子遗传算法的路径规划器
    """
    def __init__(self, map_width: float, map_height: float):
        self.map_width = map_width
        self.map_height = map_height
        self.obstacles: List[Obstacle] = []
        self.optimizer: Optional[QuantumInspiredOptimizer] = None
        
    def add_obstacle(self, obstacle: Obstacle):
        self.obstacles.append(obstacle)
    
    def generate_random_obstacles(self, num_obstacles: int):
        """生成随机障碍物"""
        for _ in range(num_obstacles):
            x = random.uniform(0, self.map_width)
            y = random.uniform(0, self.map_height)
            radius = random.uniform(5, 15)
            self.obstacles.append(Obstacle(x, y, radius))
    
    def fitness_function(self, path: np.ndarray, start: Tuple[float, float], 
                        goal: Tuple[float, float]) -> float:
        """
        适应度函数：评估路径质量
        考虑：路径长度、安全性、平滑度、可行性
        """
        # 路径长度代价
        total_length = 0
        for i in range(len(path) - 1):
            dx = path[i+1, 0] - path[i, 0]
            dy = path[i+1, 1] - path[i, 1]
            total_length += np.sqrt(dx**2 + dy**2)
        
        # 障碍物碰撞代价
        collision_penalty = 0
        for point in path:
            for obstacle in self.obstacles:
                distance = np.sqrt((point[0] - obstacle.x)**2 + (point[1] - obstacle.y)**2)
                if distance < obstacle.radius + 2:  # 安全距离
                    collision_penalty += 1000 * (obstacle.radius + 2 - distance)
        
        # 路径平滑度代价
        smoothness_penalty = 0
        for i in range(1, len(path) - 1):
            v1 = path[i] - path[i-1]
            v2 = path[i+1] - path[i]
            if np.linalg.norm(v1) > 0 and np.linalg.norm(v2) > 0:
                v1 = v1 / np.linalg.norm(v1)
                v2 = v2 / np.linalg.norm(v2)
                angle = np.arccos(np.clip(np.dot(v1, v2), -1, 1))
                smoothness_penalty += angle * 10
        
        # 目标接近度奖励
        distance_to_goal = np.linalg.norm(path[-1] - np.array(goal))
        goal_reward = -distance_to_goal * 50
        
        fitness = goal_reward - total_length - collision_penalty - smoothness_penalty
        return fitness
    
    def decode_chromosome(self, chromosome: np.ndarray, start: Tuple[float, float], 
                         goal: Tuple[float, float], num_waypoints: int) -> np.ndarray:
        """将染色体解码为实际路径"""
        path = np.zeros((num_waypoints + 2, 2))
        path[0] = start
        path[-1] = goal
        
        # 解码中间路径点
        for i in range(num_waypoints):
            x_ratio = chromosome[i * 2]
            y_ratio = chromosome[i * 2 + 1]
            path[i + 1, 0] = start[0] + (goal[0] - start[0]) * x_ratio
            path[i + 1, 1] = start[1] + (goal[1] - start[1]) * y_ratio
        
        return path
    
    def plan_path(self, start: Tuple[float, float], goal: Tuple[float, float], 
                 num_waypoints: int = 5, generations: int = 100) -> Dict:
        """
        主路径规划函数
        """
        chromosome_length = num_waypoints * 2  # 每个路径点有x,y坐标
        
        if self.optimizer is None:
            self.optimizer = QuantumInspiredOptimizer(
                population_size=50, 
                chromosome_length=chromosome_length
            )
        
        best_fitness = -float('inf')
        best_path = None
        fitness_history = []
        
        for generation in range(generations):
            # 观测量子态获得经典种群
            classical_population = self.optimizer.observe_quantum_state(
                self.optimizer.quantum_population
            )
            
            # 评估适应度
            fitness_scores = []
            paths = []
            
            for chromosome in classical_population:
                path = self.decode_chromosome(chromosome, start, goal, num_waypoints)
                fitness = self.fitness_function(path, start, goal)
                fitness_scores.append(fitness)
                paths.append(path)
                
                if fitness > best_fitness:
                    best_fitness = fitness
                    best_path = path
            
            fitness_history.append(best_fitness)
            
            # 选择最佳个体
            elite_indices = np.argsort(fitness_scores)[-10:]  # 选择前10个最佳
            
            # 更新量子种群
            new_quantum_population = []
            
            # 保留精英
            for idx in elite_indices:
                new_quantum_population.append(self.optimizer.quantum_population[idx])
            
            # 量子交叉和变异
            while len(new_quantum_population) < self.optimizer.population_size:
                parent1_idx, parent2_idx = random.sample(list(elite_indices), 2)
                parent1 = self.optimizer.quantum_population[parent1_idx]
                parent2 = self.optimizer.quantum_population[parent2_idx]
                
                child = self.optimizer.quantum_crossover(parent1, parent2)
                new_quantum_population.append(child)
            
            self.optimizer.quantum_population = np.array(new_quantum_population)
            
            # 应用量子旋转门向最佳解进化
            if best_path is not None:
                best_chromosome = classical_population[np.argmax(fitness_scores)]
                rotation_angle = 0.1 * (1 - generation / generations)  # 自适应旋转角度
                self.optimizer.quantum_population = self.optimizer.quantum_rotation_gate(
                    self.optimizer.quantum_population, best_chromosome, rotation_angle
                )
            
            if generation % 20 == 0:
                print(f"Generation {generation}, Best Fitness: {best_fitness:.2f}")
        
        return {
            'path': best_path,
            'fitness_history': fitness_history,
            'obstacles': self.obstacles
        }

class RealTimeTrajectoryPredictor:
    """
    实时轨迹预测器 - 用于预测动态障碍物轨迹
    """
    def __init__(self, prediction_horizon: int = 10):
        self.prediction_horizon = prediction_horizon
        self.obstacle_history: Dict[int, List[Tuple[float, float]]] = {}
        
    def update_obstacle_history(self, obstacle_id: int, position: Tuple[float, float]):
        if obstacle_id not in self.obstacle_history:
            self.obstacle_history[obstacle_id] = []
        
        self.obstacle_history[obstacle_id].append(position)
        # 保持最近20个位置
        if len(self.obstacle_history[obstacle_id]) > 20:
            self.obstacle_history[obstacle_id].pop(0)
    
    def predict_obstacle_trajectory(self, obstacle_id: int, 
                                  current_position: Tuple[float, float]) -> List[Tuple[float, float]]:
        """预测障碍物未来轨迹"""
        if obstacle_id not in self.obstacle_history or len(self.obstacle_history[obstacle_id]) < 3:
            # 没有足够历史数据，假设静止
            return [current_position] * self.prediction_horizon
        
        history = self.obstacle_history[obstacle_id]
        
        # 简单线性预测
        positions = []
        if len(history) >= 2:
            # 计算平均速度
            recent_positions = history[-5:] if len(history) >= 5 else history
            velocities = []
            for i in range(1, len(recent_positions)):
                dx = recent_positions[i][0] - recent_positions[i-1][0]
                dy = recent_positions[i][1] - recent_positions[i-1][1]
                velocities.append((dx, dy))
            
            avg_vx = np.mean([v[0] for v in velocities])
            avg_vy = np.mean([v[1] for v in velocities])
            
            # 预测未来位置
            x, y = current_position
            for t in range(1, self.prediction_horizon + 1):
                pred_x = x + avg_vx * t
                pred_y = y + avg_vy * t
                positions.append((pred_x, pred_y))
        
        return positions

def visualize_results(planning_result: Dict, start: Tuple[float, float], 
                     goal: Tuple[float, float], map_width: float, map_height: float):
    """可视化规划结果"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
    
    # 路径可视化
    ax1.set_xlim(0, map_width)
    ax1.set_ylim(0, map_height)
    ax1.set_title('Optimized Path with Quantum-inspired Algorithm')
    ax1.set_xlabel('X Coordinate')
    ax1.set_ylabel('Y Coordinate')
    
    # 绘制障碍物
    for obstacle in planning_result['obstacles']:
        circle = plt.Circle((obstacle.x, obstacle.y), obstacle.radius, 
                           color='red', alpha=0.7)
        ax1.add_patch(circle)
    
    # 绘制路径
    if planning_result['path'] is not None:
        path = planning_result['path']
        ax1.plot(path[:, 0], path[:, 1], 'b-', linewidth=2, label='Planned Path')
        ax1.scatter(path[:, 0], path[:, 1], c='blue', s=30, zorder=5)
    
    # 绘制起点和终点
    ax1.scatter(start[0], start[1], c='green', s=100, marker='s', label='Start')
    ax1.scatter(goal[0], goal[1], c='orange', s=100, marker='s', label='Goal')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # 适应度进化曲线
    ax2.plot(planning_result['fitness_history'])
    ax2.set_title('Fitness Evolution Over Generations')
    ax2.set_xlabel('Generation')
    ax2.set_ylabel('Fitness Score')
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.show()

# 示例使用和演示
def demo_quantum_path_planning():
    """演示量子启发式路径规划"""
    print("=== 量子启发式自动驾驶路径规划演示 ===")
    
    # 创建规划器
    planner = PathPlanner(map_width=100, map_height=100)
    
    # 添加障碍物
    planner.generate_random_obstacles(8)
    
    # 手动添加一些特定障碍物
    planner.add_obstacle(Obstacle(30, 40, 8))
    planner.add_obstacle(Obstacle(60, 30, 10))
    planner.add_obstacle(Obstacle(70, 70, 6))
    
    # 设置起点和终点
    start = (10, 10)
    goal = (90, 90)
    
    print("开始路径规划...")
    start_time = time.time()
    
    # 执行路径规划
    result = planner.plan_path(
        start=start,
        goal=goal,
        num_waypoints=6,
        generations=80
    )
    
    end_time = time.time()
    print(f"规划完成! 耗时: {end_time - start_time:.2f}秒")
    print(f"最终适应度: {result['fitness_history'][-1]:.2f}")
    
    # 可视化结果
    visualize_results(result, start, goal, 100, 100)
    
    return result

def performance_comparison():
    """性能对比：量子遗传算法 vs 传统遗传算法"""
    # 这里可以实现与传统方法的对比
    pass

if __name__ == "__main__":
    # 运行演示
    result = demo_quantum_path_planning()