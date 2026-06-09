import numpy as np
import cv2
import random
from typing import List, Dict, Tuple, Callable
from dataclasses import dataclass
from functools import partial
import matplotlib.pyplot as plt
from skimage import filters, feature, segmentation, morphology
from scipy import ndimage

@dataclass
class VisionGene:
    """视觉处理操作的基因编码"""
    operation: str
    parameters: Dict
    weight: float = 1.0

class EvolutionaryVisionPipeline:
    """
    进化式视觉处理管道
    通过随机生成和选择发现有效的视觉算法
    """
    
    def __init__(self, population_size: int = 50, max_generations: int = 100):
        self.population_size = population_size
        self.max_generations = max_generations
        self.operation_library = self._build_operation_library()
        self.population = []
        self.fitness_history = []
        
    def _build_operation_library(self) -> Dict[str, Callable]:
        """构建基础视觉操作库"""
        return {
            # 滤波操作
            'gaussian_blur': lambda img, sigma: cv2.GaussianBlur(img, (0, 0), sigma),
            'median_blur': lambda img, ksize: cv2.medianBlur(img, ksize),
            'bilateral_filter': lambda img, d, sigma_color, sigma_space: 
                cv2.bilateralFilter(img, d, sigma_color, sigma_space),
            
            # 边缘检测
            'canny': lambda img, threshold1, threshold2: 
                cv2.Canny(img, threshold1, threshold2),
            'sobel': lambda img, dx, dy, ksize: 
                cv2.Sobel(img, cv2.CV_64F, dx, dy, ksize),
            'laplacian': lambda img, ksize: 
                cv2.Laplacian(img, cv2.CV_64F, ksize),
            
            # 形态学操作
            'erode': lambda img, ksize, iterations: 
                cv2.erode(img, np.ones((ksize, ksize)), iterations=iterations),
            'dilate': lambda img, ksize, iterations: 
                cv2.dilate(img, np.ones((ksize, ksize)), iterations=iterations),
            'morph_open': lambda img, ksize: 
                cv2.morphologyEx(img, cv2.MORPH_OPEN, np.ones((ksize, ksize))),
            'morph_close': lambda img, ksize: 
                cv2.morphologyEx(img, cv2.MORPH_CLOSE, np.ones((ksize, ksize))),
            
            # 颜色空间转换
            'rgb_to_hsv': lambda img: cv2.cvtColor(img, cv2.COLOR_RGB2HSV),
            'rgb_to_lab': lambda img: cv2.cvtColor(img, cv2.COLOR_RGB2LAB),
            'rgb_to_gray': lambda img: cv2.cvtColor(img, cv2.COLOR_RGB2GRAY),
            
            # 阈值处理
            'adaptive_threshold': lambda img, block_size, C: 
                cv2.adaptiveThreshold(img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                    cv2.THRESH_BINARY, block_size, C),
            'otsu_threshold': lambda img: 
                (cv2.threshold(img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1] 
                 if len(img.shape) == 2 else img),
            
            # 特征检测
            'harris_corners': lambda img, block_size, ksize, k: 
                cv2.cornerHarris(img, block_size, ksize, k),
            'blob_detection': lambda img, min_threshold, max_threshold: 
                feature.blob_dog(img, min_threshold, max_threshold),
            
            # 图像增强
            'histogram_equalization': lambda img: 
                cv2.equalizeHist(img) if len(img.shape) == 2 else img,
            'clahe': lambda img, clip_limit, tile_size: 
                cv2.createCLAHE(clipLimit=clip_limit, 
                              tileGridSize=(tile_size, tile_size)).apply(img)
        }
    
    def random_gene(self) -> VisionGene:
        """随机生成视觉基因"""
        operation = random.choice(list(self.operation_library.keys()))
        
        # 为不同操作生成随机参数
        param_ranges = {
            'gaussian_blur': {'sigma': (0.1, 5.0)},
            'median_blur': {'ksize': (3, 11)},
            'bilateral_filter': {'d': (1, 15), 'sigma_color': (10, 150), 'sigma_space': (10, 150)},
            'canny': {'threshold1': (50, 200), 'threshold2': (100, 300)},
            'sobel': {'dx': (0, 2), 'dy': (0, 2), 'ksize': (1, 7)},
            'laplacian': {'ksize': (1, 7)},
            'erode': {'ksize': (1, 7), 'iterations': (1, 5)},
            'dilate': {'ksize': (1, 7), 'iterations': (1, 5)},
            'morph_open': {'ksize': (1, 7)},
            'morph_close': {'ksize': (1, 7)},
            'adaptive_threshold': {'block_size': (3, 51), 'C': (1, 20)},
            'harris_corners': {'block_size': (2, 10), 'ksize': (3, 7), 'k': (0.01, 0.1)},
            'clahe': {'clip_limit': (1.0, 5.0), 'tile_size': (2, 16)}
        }
        
        parameters = {}
        if operation in param_ranges:
            for param, (min_val, max_val) in param_ranges[operation].items():
                if isinstance(min_val, int):
                    parameters[param] = random.randint(min_val, max_val)
                else:
                    parameters[param] = random.uniform(min_val, max_val)
        
        return VisionGene(operation, parameters, weight=random.uniform(0.5, 2.0))
    
    def random_pipeline(self, length: int = 5) -> List[VisionGene]:
        """随机生成处理管道"""
        return [self.random_gene() for _ in range(length)]
    
    def execute_pipeline(self, image: np.ndarray, pipeline: List[VisionGene]) -> np.ndarray:
        """执行视觉处理管道"""
        result = image.copy()
        
        for gene in pipeline:
            try:
                operation_func = self.operation_library[gene.operation]
                
                # 检查操作是否适用于当前图像
                if gene.operation in ['rgb_to_gray', 'adaptive_threshold', 'otsu_threshold']:
                    if len(result.shape) == 3:
                        if gene.operation in ['adaptive_threshold', 'otsu_threshold']:
                            result = cv2.cvtColor(result, cv2.COLOR_RGB2GRAY)
                
                # 执行操作
                if gene.parameters:
                    result = operation_func(result, **gene.parameters)
                else:
                    result = operation_func(result)
                    
            except Exception as e:
                # 如果操作失败，跳过该步骤
                continue
                
        return result
    
    def fitness_function(self, original: np.ndarray, processed: np.ndarray, 
                        target_metric: str = "edge_density") -> float:
        """评估管道性能的适应度函数"""
        
        try:
            if target_metric == "edge_density":
                # 边缘密度 - 适用于边缘检测任务
                if len(processed.shape) == 3:
                    gray = cv2.cvtColor(processed, cv2.COLOR_RGB2GRAY)
                else:
                    gray = processed
                
                edges = cv2.Canny(gray, 50, 150)
                edge_density = np.sum(edges > 0) / (edges.shape[0] * edges.shape[1])
                return edge_density
                
            elif target_metric == "contrast":
                # 对比度增强
                if len(processed.shape) == 3:
                    gray = cv2.cvtColor(processed, cv2.COLOR_RGB2GRAY)
                else:
                    gray = processed
                
                contrast = gray.std()
                return contrast / 100.0  # 归一化
                
            elif target_metric == "corner_density":
                # 角点密度
                if len(processed.shape) == 3:
                    gray = cv2.cvtColor(processed, cv2.COLOR_RGB2GRAY)
                else:
                    gray = processed
                
                corners = cv2.cornerHarris(gray, 2, 3, 0.04)
                corner_density = np.sum(corners > 0.01 * corners.max()) / (gray.shape[0] * gray.shape[1])
                return corner_density
                
            elif target_metric == "segmentation_quality":
                # 分割质量 (基于纹理变化)
                if len(processed.shape) == 3:
                    gray = cv2.cvtColor(processed, cv2.COLOR_RGB2GRAY)
                else:
                    gray = processed
                
                # 计算局部方差
                local_var = ndimage.generic_filter(gray, np.var, size=5)
                texture_variation = local_var.std()
                return texture_variation / 1000.0
                
        except Exception as e:
            return 0.0
            
        return 0.0
    
    def initialize_population(self):
        """初始化种群 - 随机生成无意义的管道"""
        self.population = [self.random_pipeline(random.randint(3, 8)) 
                          for _ in range(self.population_size)]
    
    def evaluate_population(self, image: np.ndarray, target_metric: str) -> List[float]:
        """评估整个种群的适应度"""
        fitness_scores = []
        
        for pipeline in self.population:
            try:
                processed = self.execute_pipeline(image, pipeline)
                fitness = self.fitness_function(image, processed, target_metric)
                fitness_scores.append(fitness)
            except:
                fitness_scores.append(0.0)
                
        return fitness_scores
    
    def selection(self, fitness_scores: List[float], selection_rate: float = 0.3) -> List[List[VisionGene]]:
        """选择优秀的个体"""
        selected_indices = np.argsort(fitness_scores)[-int(len(fitness_scores) * selection_rate):]
        return [self.population[i] for i in selected_indices]
    
    def crossover(self, parent1: List[VisionGene], parent2: List[VisionGene]) -> List[VisionGene]:
        """交叉操作 - 组合两个管道"""
        crossover_point = random.randint(1, min(len(parent1), len(parent2)) - 1)
        child = parent1[:crossover_point] + parent2[crossover_point:]
        return child
    
    def mutation(self, pipeline: List[VisionGene], mutation_rate: float = 0.1) -> List[VisionGene]:
        """变异操作"""
        mutated = pipeline.copy()
        
        for i in range(len(mutated)):
            if random.random() < mutation_rate:
                # 替换基因
                mutated[i] = self.random_gene()
            elif random.random() < mutation_rate:
                # 调整参数
                if mutated[i].parameters:
                    param_name = random.choice(list(mutated[i].parameters.keys()))
                    current_val = mutated[i].parameters[param_name]
                    if isinstance(current_val, int):
                        mutated[i].parameters[param_name] = max(1, current_val + random.randint(-2, 2))
                    else:
                        mutated[i].parameters[param_name] = max(0.1, current_val * random.uniform(0.5, 1.5))
        
        # 添加或删除基因
        if random.random() < mutation_rate and len(mutated) < 15:
            mutated.append(self.random_gene())
        elif random.random() < mutation_rate and len(mutated) > 2:
            mutated.pop(random.randint(0, len(mutated) - 1))
            
        return mutated
    
    def evolve(self, image: np.ndarray, target_metric: str = "edge_density"):
        """执行进化过程"""
        self.initialize_population()
        
        for generation in range(self.max_generations):
            # 评估适应度
            fitness_scores = self.evaluate_population(image, target_metric)
            best_fitness = max(fitness_scores)
            self.fitness_history.append(best_fitness)
            
            if generation % 10 == 0:
                print(f"Generation {generation}, Best Fitness: {best_fitness:.4f}")
            
            # 选择
            selected = self.selection(fitness_scores)
            
            # 生成新种群
            new_population = selected.copy()
            
            while len(new_population) < self.population_size:
                if random.random() < 0.7 and len(selected) >= 2:
                    # 交叉
                    parent1, parent2 = random.sample(selected, 2)
                    child = self.crossover(parent1, parent2)
                    child = self.mutation(child)
                    new_population.append(child)
                else:
                    # 变异或新个体
                    if selected and random.random() < 0.5:
                        individual = random.choice(selected)
                        new_population.append(self.mutation(individual))
                    else:
                        new_population.append(self.random_pipeline(random.randint(3, 8)))
            
            self.population = new_population
        
        # 返回最佳管道
        final_fitness = self.evaluate_population(image, target_metric)
        best_index = np.argmax(final_fitness)
        return self.population[best_index], final_fitness[best_index]
    
    def visualize_pipeline(self, image: np.ndarray, pipeline: List[VisionGene], 
                          save_path: str = None):
        """可视化管道处理过程"""
        fig, axes = plt.subplots(2, len(pipeline) + 1, figsize=(4 * (len(pipeline) + 1), 8))
        
        # 显示原始图像
        if len(image.shape) == 3:
            axes[0, 0].imshow(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        else:
            axes[0, 0].imshow(image, cmap='gray')
        axes[0, 0].set_title("Original")
        axes[0, 0].axis('off')
        
        current = image.copy()
        intermediate_results = [current]
        
        # 逐步执行管道并显示结果
        for i, gene in enumerate(pipeline):
            try:
                operation_func = self.operation_library[gene.operation]
                
                if gene.parameters:
                    current = operation_func(current, **gene.parameters)
                else:
                    current = operation_func(current)
                    
                intermediate_results.append(current)
                
                # 显示处理结果
                if len(current.shape) == 3:
                    axes[0, i+1].imshow(cv2.cvtColor(current, cv2.COLOR_BGR2RGB))
                else:
                    axes[0, i+1].imshow(current, cmap='gray')
                
                axes[0, i+1].set_title(f"{gene.operation}")
                axes[0, i+1].axis('off')
                
            except Exception as e:
                print(f"Error visualizing step {i}: {e}")
                break
        
        # 显示操作描述
        for i, gene in enumerate(pipeline):
            param_text = ", ".join([f"{k}:{v}" for k, v in gene.parameters.items()])
            axes[1, i+1].text(0.5, 0.5, f"{gene.operation}\n{param_text}", 
                             ha='center', va='center', fontsize=10)
            axes[1, i+1].axis('off')
        
        axes[1, 0].text(0.5, 0.5, "Operation\nDetails", ha='center', va='center', fontsize=12)
        axes[1, 0].axis('off')
        
        plt.tight_layout()
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.show()

# 应用示例
def demo_evolutionary_vision():
    """演示进化视觉算法的应用"""
    
    # 加载测试图像
    image = cv2.imread('test_image.jpg')  # 替换为你的图像路径
    if image is None:
        # 创建示例图像
        image = np.random.randint(0, 255, (300, 400, 3), dtype=np.uint8)
        cv2.putText(image, "Test Image", (100, 150), cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 3)
    
    # 创建进化视觉管道
    evp = EvolutionaryVisionPipeline(population_size=30, max_generations=50)
    
    # 针对不同任务进化管道
    tasks = [
        ("edge_density", "边缘检测"),
        ("contrast", "对比度增强"), 
        ("corner_density", "角点检测"),
        ("segmentation_quality", "分割质量")
    ]
    
    best_pipelines = {}
    
    for metric, task_name in tasks:
        print(f"\n=== 进化 {task_name} 管道 ===")
        best_pipeline, fitness = evp.evolve(image, target_metric=metric)
        best_pipelines[task_name] = (best_pipeline, fitness)
        
        print(f"最佳适应度: {fitness:.4f}")
        print("最佳管道:")
        for i, gene in enumerate(best_pipeline):
            print(f"  {i+1}. {gene.operation} {gene.parameters}")
        
        # 可视化最佳管道
        evp.visualize_pipeline(image, best_pipeline, 
                              save_path=f"pipeline_{task_name}.png")
    
    # 绘制进化过程
    plt.figure(figsize=(10, 6))
    plt.plot(evp.fitness_history)
    plt.xlabel('Generation')
    plt.ylabel('Best Fitness')
    plt.title('Evolution Progress')
    plt.grid(True)
    plt.savefig('evolution_progress.png', dpi=300, bbox_inches='tight')
    plt.show()
    
    return best_pipelines

# 实时进化应用
class RealTimeEvolvedVision:
    """实时进化视觉处理应用"""
    
    def __init__(self):
        self.evp = EvolutionaryVisionPipeline(population_size=20, max_generations=30)
        self.current_pipeline = []
        
    def process_video(self, video_source: int = 0, target_metric: str = "edge_density"):
        """实时处理视频流并持续进化"""
        cap = cv2.VideoCapture(video_source)
        
        frame_count = 0
        evolution_interval = 30  # 每30帧进化一次
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
                
            frame_count += 1
            
            # 定期进化管道
            if frame_count % evolution_interval == 0 or not self.current_pipeline:
                print("Evolving pipeline...")
                self.current_pipeline, fitness = self.evp.evolve(frame, target_metric)
                print(f"New pipeline fitness: {fitness:.4f}")
            
            # 应用当前最佳管道
            processed = self.evp.execute_pipeline(frame, self.current_pipeline)
            
            # 显示结果
            cv2.imshow('Original', frame)
            cv2.imshow('Evolved Processing', processed)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        
        cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    # 运行演示
    pipelines = demo_evolutionary_vision()
    
    # 运行实时处理 (取消注释以运行)
    # real_time_processor = RealTimeEvolvedVision()
    # real_time_processor.process_video(0, "edge_density")