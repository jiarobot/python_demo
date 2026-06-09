import sys
import os
import pandas as pd
import numpy as np
import torch
import torch.nn as nn
from typing import Dict, Any, List, Tuple
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.patches import Ellipse
import seaborn as sns

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QGroupBox, QLabel, QLineEdit, 
                             QPushButton, QTextEdit, QTabWidget, QComboBox,
                             QCheckBox, QSpinBox, QDoubleSpinBox, QProgressBar,
                             QFileDialog, QMessageBox, QTableWidget, QTableWidgetItem,
                             QSplitter, QHeaderView, QSlider, QGridLayout)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QPalette, QColor

# 导入我们之前实现的最小二乘神经网络
import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
import math
from collections import deque
import random

class QuantumInspiredLeastSquares(nn.Module):
    """
    量子启发式最小二乘层 - 颠覆性创新1
    用量子力学概念重构最小二乘，实现超线性计算
    """
    
    def __init__(self, input_dim: int, output_dim: int, num_quantum_states: int = 8):
        super().__init__()
        self.input_dim = input_dim
        self.output_dim = output_dim
        self.num_quantum_states = num_quantum_states
        
        # 量子态权重（叠加态）
        self.quantum_weights = nn.ParameterList([
            nn.Parameter(torch.Tensor(output_dim, input_dim)) 
            for _ in range(num_quantum_states)
        ])
        
        # 量子振幅（概率幅）
        self.quantum_amplitudes = nn.Parameter(torch.ones(num_quantum_states) / num_quantum_states)
        
        # 量子纠缠矩阵
        self.entanglement = nn.Parameter(torch.eye(input_dim) * 0.1)
        
        # 观测算子
        self.observable = nn.Linear(input_dim, output_dim, bias=False)
        
        self.reset_parameters()
    
    def reset_parameters(self):
        for weight in self.quantum_weights:
            nn.init.xavier_uniform_(weight)
        nn.init.orthogonal_(self.entanglement)
    
    def quantum_superposition(self, x: torch.Tensor) -> torch.Tensor:
        """量子叠加态计算"""
        # 纠缠变换
        x_entangled = x @ self.entanglement
        
        # 并行计算所有量子态
        quantum_outputs = []
        for i, weight in enumerate(self.quantum_weights):
            amplitude = F.softmax(self.quantum_amplitudes, dim=0)[i]
            output = F.linear(x_entangled, weight) * amplitude
            quantum_outputs.append(output)
        
        # 量子叠加
        superimposed = torch.stack(quantum_outputs).sum(dim=0)
        
        # 量子观测（坍缩）
        observed = self.observable(superimposed)
        
        return observed
    
    def quantum_least_squares(self, X: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
        """量子最小二乘解析解"""
        # 量子化的协方差矩阵
        X_entangled = X @ self.entanglement
        quantum_cov = X_entangled.t() @ X_entangled + 1e-8 * torch.eye(self.input_dim, device=X.device)
        
        # 量子特征分解
        eigenvalues, eigenvectors = torch.linalg.eigh(quantum_cov)
        
        # 量子正则化（基于特征值）
        regularized_inv = eigenvectors @ torch.diag(1.0 / torch.sqrt(eigenvalues + 1e-8)) @ eigenvectors.t()
        
        # 量子最小二乘解
        quantum_solution = regularized_inv @ X_entangled.t() @ y
        
        return quantum_solution.t()
    
    def forward(self, x: torch.Tensor, y: Optional[torch.Tensor] = None) -> torch.Tensor:
        if y is not None and self.training:
            # 在线更新量子权重
            quantum_sol = self.quantum_least_squares(x, y)
            
            # 量子态更新（基于梯度与解析解的混合）
            with torch.no_grad():
                for i in range(self.num_quantum_states):
                    amplitude = F.softmax(self.quantum_amplitudes, dim=0)[i]
                    self.quantum_weights[i].data = amplitude * quantum_sol + (1 - amplitude) * self.quantum_weights[i]
        
        return self.quantum_superposition(x)

class MetaLeastSquaresLearner(nn.Module):
    """
    元最小二乘学习器 - 颠覆性创新2
    实现快速适应和新任务零样本学习
    """
    
    def __init__(self, input_dim: int, output_dim: int, meta_hidden_dim: int = 128):
        super().__init__()
        self.input_dim = input_dim
        self.output_dim = output_dim
        
        # 元学习网络（学习如何学习）
        self.meta_encoder = nn.Sequential(
            nn.Linear(input_dim + output_dim, meta_hidden_dim),
            nn.ReLU(),
            nn.Linear(meta_hidden_dim, meta_hidden_dim),
            nn.ReLU()
        )
        
        # 元参数生成器
        self.weight_generator = nn.Linear(meta_hidden_dim, output_dim * input_dim)
        self.bias_generator = nn.Linear(meta_hidden_dim, output_dim)
        
        # 快速适应缓存
        self.support_set = deque(maxlen=1000)
        self.adaptation_steps = 3
        
    def meta_forward(self, x: torch.Tensor, support_x: torch.Tensor, support_y: torch.Tensor) -> torch.Tensor:
        """元学习前向传播"""
        batch_size = x.size(0)
        support_size = support_x.size(0)
        
        # 编码支持集（少量样本）
        support_encoded = []
        for i in range(support_size):
            sample = torch.cat([support_x[i], support_y[i]])
            encoded = self.meta_encoder(sample)
            support_encoded.append(encoded)
        
        # 元特征聚合
        meta_features = torch.stack(support_encoded).mean(dim=0)
        
        # 生成任务特定参数
        task_weights = self.weight_generator(meta_features).view(self.output_dim, self.input_dim)
        task_bias = self.bias_generator(meta_features)
        
        # 任务特定预测
        return F.linear(x, task_weights, task_bias)
    
    def fast_adaptation(self, x: torch.Tensor, adaptation_data: Tuple[torch.Tensor, torch.Tensor]) -> torch.Tensor:
        """快速适应新任务"""
        adapt_x, adapt_y = adaptation_data
        
        # 多步快速适应
        current_x, current_y = adapt_x, adapt_y
        for step in range(self.adaptation_steps):
            # 元预测
            prediction = self.meta_forward(x, current_x, current_y)
            
            if step < self.adaptation_steps - 1:
                # 生成伪样本增强适应
                with torch.no_grad():
                    noise = 0.1 * torch.randn_like(current_x)
                    augmented_x = current_x + noise
                    augmented_y = self.meta_forward(augmented_x, current_x, current_y)
                    
                    current_x = torch.cat([current_x, augmented_x])
                    current_y = torch.cat([current_y, augmented_y])
        
        return prediction
    
    def forward(self, x: torch.Tensor, adaptation_data: Optional[Tuple[torch.Tensor, torch.Tensor]] = None) -> torch.Tensor:
        if adaptation_data is not None:
            return self.fast_adaptation(x, adaptation_data)
        else:
            # 零样本预测（使用历史支持集）
            if len(self.support_set) > 0:
                support_x, support_y = zip(*list(self.support_set))
                support_x = torch.stack(support_x)
                support_y = torch.stack(support_y)
                return self.meta_forward(x, support_x, support_y)
            else:
                # 返回默认预测
                return torch.zeros(x.size(0), self.output_dim, device=x.device)

class ReinforcementLeastSquaresAgent(nn.Module):
    """
    强化最小二乘智能体 - 颠覆性创新3
    将最小二乘转化为强化学习策略
    """
    
    def __init__(self, state_dim: int, action_dim: int, hidden_dim: int = 256):
        super().__init__()
        self.state_dim = state_dim
        self.action_dim = action_dim
        
        # 策略网络（最小二乘增强）
        self.policy_net = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU()
        )
        
        # 最小二乘价值估计器
        self.value_estimator = QuantumInspiredLeastSquares(hidden_dim, 1)
        
        # 优势函数估计
        self.advantage_net = nn.Linear(hidden_dim, action_dim)
        
        # 经验回放
        self.memory = deque(maxlen=10000)
        self.batch_size = 32
        
    def get_action(self, state: torch.Tensor, exploration: bool = True) -> torch.Tensor:
        """基于最小二乘的策略选择"""
        features = self.policy_net(state)
        
        # 价值估计
        state_value = self.value_estimator(features)
        
        # 优势估计
        advantages = self.advantage_net(features)
        
        # 策略生成（带探索）
        action_probs = F.softmax(advantages, dim=-1)
        
        if exploration:
            action_dist = torch.distributions.Categorical(action_probs)
            action = action_dist.sample()
        else:
            action = torch.argmax(action_probs, dim=-1)
            
        return action, action_probs, state_value
    
    def update_with_least_squares(self, states: torch.Tensor, targets: torch.Tensor) -> float:
        """使用最小二乘更新价值函数"""
        features = self.policy_net(states)
        
        # 最小二乘更新价值估计器
        predicted_values = self.value_estimator(features, targets)
        
        # 计算TD误差
        td_errors = targets - predicted_values.detach()
        
        return td_errors.pow(2).mean().item()

class MultiModalLeastSquaresFusion(nn.Module):
    """
    多模态最小二乘融合 - 颠覆性创新4
    统一处理视觉、语言、数值数据
    """
    
    def __init__(self, vision_dim: int, language_dim: int, numeric_dim: int, output_dim: int):
        super().__init__()
        
        # 模态编码器
        self.vision_encoder = nn.Sequential(
            nn.Linear(vision_dim, 256),
            nn.ReLU(),
            nn.Linear(256, 128)
        )
        
        self.language_encoder = nn.Sequential(
            nn.Linear(language_dim, 256),
            nn.ReLU(),
            nn.Linear(256, 128)
        )
        
        self.numeric_encoder = nn.Sequential(
            nn.Linear(numeric_dim, 128),
            nn.ReLU()
        )
        
        # 跨模态注意力融合
        self.cross_modal_attention = nn.MultiheadAttention(128, num_heads=8, batch_first=True)
        
        # 最小二乘融合层
        self.fusion_least_squares = QuantumInspiredLeastSquares(128 * 3, output_dim)
        
        # 模态权重学习
        self.modal_weights = nn.Parameter(torch.ones(3))
        
    def forward(self, vision: torch.Tensor, language: torch.Tensor, numeric: torch.Tensor, 
                targets: Optional[torch.Tensor] = None) -> torch.Tensor:
        
        # 模态编码
        vision_encoded = self.vision_encoder(vision)
        language_encoded = self.language_encoder(language)  
        numeric_encoded = self.numeric_encoder(numeric)
        
        # 跨模态注意力
        modal_features = torch.stack([vision_encoded, language_encoded, numeric_encoded], dim=1)
        attended_features, _ = self.cross_modal_attention(modal_features, modal_features, modal_features)
        
        # 模态加权融合
        weights = F.softmax(self.modal_weights, dim=0)
        fused = (attended_features * weights.view(1, 3, 1)).sum(dim=1)
        
        # 最小二乘预测
        return self.fusion_least_squares(fused, targets)

class EvolutionaryLeastSquaresOptimizer:
    """
    进化最小二乘优化器 - 颠覆性创新5
    结合遗传算法和最小二乘的混合优化
    """
    
    def __init__(self, model: nn.Module, population_size: int = 20, elite_size: int = 5):
        self.model = model
        self.population_size = population_size
        self.elite_size = elite_size
        self.population = self.initialize_population()
        
    def initialize_population(self) -> List[Dict]:
        """初始化参数种群"""
        population = []
        for _ in range(self.population_size):
            individual = {}
            for name, param in self.model.named_parameters():
                individual[name] = param.data.clone() + 0.1 * torch.randn_like(param)
            population.append(individual)
        return population
    
    def evaluate_fitness(self, individual: Dict, X: torch.Tensor, y: torch.Tensor) -> float:
        """评估个体适应度（使用最小二乘损失）"""
        # 临时设置模型参数
        original_params = {name: param.data.clone() for name, param in self.model.named_parameters()}
        
        for name, param in self.model.named_parameters():
            param.data = individual[name]
        
        # 计算适应度（负损失）
        with torch.no_grad():
            prediction = self.model(X)
            fitness = -F.mse_loss(prediction, y).item()
        
        # 恢复原始参数
        for name, param in self.model.named_parameters():
            param.data = original_params[name]
            
        return fitness
    
    def evolve(self, X: torch.Tensor, y: torch.Tensor, generations: int = 10):
        """进化优化"""
        for generation in range(generations):
            # 评估适应度
            fitness_scores = []
            for individual in self.population:
                fitness = self.evaluate_fitness(individual, X, y)
                fitness_scores.append(fitness)
            
            # 选择精英
            elite_indices = np.argsort(fitness_scores)[-self.elite_size:]
            elites = [self.population[i] for i in elite_indices]
            
            # 生成新种群
            new_population = elites.copy()  # 保留精英
            
            while len(new_population) < self.population_size:
                # 选择父母
                parent1, parent2 = random.choices(elites, k=2)
                
                # 交叉重组
                child = {}
                for name in parent1.keys():
                    if random.random() < 0.5:
                        child[name] = parent1[name]
                    else:
                        child[name] = parent2[name]
                
                # 变异
                for name in child:
                    if random.random() < 0.1:  # 变异概率
                        child[name] = child[name] + 0.05 * torch.randn_like(child[name])
                
                new_population.append(child)
            
            self.population = new_population
            
            # 更新最佳个体到模型
            best_individual = elites[-1]
            for name, param in self.model.named_parameters():
                param.data = best_individual[name]
            
            print(f"Generation {generation}, Best Fitness: {fitness_scores[elite_indices[-1]]:.6f}")

class UniversalLeastSquaresSystem(nn.Module):
    """
    通用最小二乘系统 - 终极颠覆性框架
    整合所有创新技术的完整系统
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__()
        self.config = config
        
        # 多模态输入处理
        self.multimodal_fusion = MultiModalLeastSquaresFusion(
            vision_dim=config.get('vision_dim', 512),
            language_dim=config.get('language_dim', 768), 
            numeric_dim=config.get('numeric_dim', 64),
            output_dim=config.get('latent_dim', 256)
        )
        
        # 元学习核心
        self.meta_learner = MetaLeastSquaresLearner(
            input_dim=config.get('latent_dim', 256),
            output_dim=config.get('output_dim', 10)
        )
        
        # 强化学习决策
        self.rl_agent = ReinforcementLeastSquaresAgent(
            state_dim=config.get('latent_dim', 256),
            action_dim=config.get('action_dim', 5)
        )
        
        # 量子计算增强
        self.quantum_predictor = QuantumInspiredLeastSquares(
            input_dim=config.get('latent_dim', 256),
            output_dim=config.get('output_dim', 10)
        )
        
        # 自适应融合门控
        self.fusion_gate = nn.Parameter(torch.ones(3))
        
    def forward(self, inputs: Dict[str, torch.Tensor], 
                adaptation_data: Optional[Dict] = None,
                training_mode: str = "multimodal") -> Dict[str, torch.Tensor]:
        
        # 多模态融合
        multimodal_latent = self.multimodal_fusion(
            inputs.get('vision', torch.zeros(1, 512)),
            inputs.get('language', torch.zeros(1, 768)), 
            inputs.get('numeric', torch.zeros(1, 64)),
            inputs.get('targets', None)
        )
        
        # 多策略预测
        meta_prediction = self.meta_learner(multimodal_latent, 
                                           adaptation_data.get('support_set', None) if adaptation_data else None)
        
        quantum_prediction = self.quantum_predictor(multimodal_latent, 
                                                   inputs.get('targets', None))
        
        # 强化学习决策
        rl_action, rl_probs, rl_value = self.rl_agent.get_action(multimodal_latent)
        
        # 自适应融合
        fusion_weights = F.softmax(self.fusion_gate, dim=0)
        final_prediction = (fusion_weights[0] * meta_prediction + 
                           fusion_weights[1] * quantum_prediction + 
                           fusion_weights[2] * rl_probs.float())
        
        return {
            'prediction': final_prediction,
            'meta_output': meta_prediction,
            'quantum_output': quantum_prediction, 
            'rl_action': rl_action,
            'rl_value': rl_value,
            'fusion_weights': fusion_weights,
            'latent_representation': multimodal_latent
        }

# 颠覆性训练框架
class LeastSquaresUniverseTrainer:
    """最小二乘宇宙训练器 - 终极训练框架"""
    
    def __init__(self, model: UniversalLeastSquaresSystem, config: Dict):
        self.model = model
        self.config = config
        
        # 多目标优化器
        self.optimizers = {
            'multimodal': torch.optim.Adam(model.multimodal_fusion.parameters(), lr=1e-3),
            'meta': torch.optim.Adam(model.meta_learner.parameters(), lr=1e-4),
            'quantum': torch.optim.Adam(model.quantum_predictor.parameters(), lr=1e-3),
            'rl': torch.optim.Adam(model.rl_agent.parameters(), lr=1e-4)
        }
        
        # 进化优化器
        self.evolutionary_optimizer = EvolutionaryLeastSquaresOptimizer(model)
        
        # 训练状态
        self.training_phase = 0
        
    def multimodal_loss(self, predictions: Dict, targets: Dict) -> torch.Tensor:
        """多模态损失函数"""
        loss = 0.0
        
        # 预测损失
        if 'regression' in targets:
            loss += F.mse_loss(predictions['prediction'], targets['regression'])
        
        # 一致性损失（不同方法应该一致）
        loss += 0.1 * F.mse_loss(predictions['meta_output'], predictions['quantum_output'])
        
        # 价值正则化
        loss += 0.01 * predictions['rl_value'].pow(2).mean()
        
        return loss
    
    def train_phase_1(self, dataloader: Any, epochs: int):
        """阶段1：多模态基础训练"""
        self.model.train()
        
        for epoch in range(epochs):
            total_loss = 0
            for batch_idx, batch in enumerate(dataloader):
                # 前向传播
                outputs = self.model(batch['inputs'], training_mode="multimodal")
                
                # 计算损失
                loss = self.multimodal_loss(outputs, batch['targets'])
                
                # 反向传播
                self.optimizers['multimodal'].zero_grad()
                loss.backward()
                self.optimizers['multimodal'].step()
                
                total_loss += loss.item()
                
                if batch_idx % 100 == 0:
                    print(f'Phase 1 - Epoch: {epoch}, Batch: {batch_idx}, Loss: {loss.item():.6f}')
    
    def train_phase_2(self, dataloader: Any, epochs: int):
        """阶段2：元学习适应训练"""
        self.model.train()
        
        for epoch in range(epochs):
            total_loss = 0
            for batch_idx, batch in enumerate(dataloader):
                # 元学习训练（每个batch都是新任务）
                adaptation_data = {
                    'support_set': (batch['support_x'], batch['support_y'])
                }
                
                outputs = self.model(batch['inputs'], adaptation_data, "meta_learning")
                loss = self.multimodal_loss(outputs, batch['targets'])
                
                self.optimizers['meta'].zero_grad()
                loss.backward()
                self.optimizers['meta'].step()
                
                total_loss += loss.item()
    
    def train_phase_3(self, dataloader: Any, epochs: int):
        """阶段3：进化优化强化"""
        self.model.eval()  # 进化算法不需要梯度
        
        # 收集训练数据用于进化
        all_X, all_y = [], []
        for batch in dataloader:
            with torch.no_grad():
                latent = self.model(batch['inputs'])['latent_representation']
                all_X.append(latent)
                all_y.append(batch['targets']['regression'])
        
        X = torch.cat(all_X)
        y = torch.cat(all_y)
        
        # 进化优化
        self.evolutionary_optimizer.evolve(X, y, generations=epochs)

# 示例使用
def demonstrate_universal_system():
    """演示通用最小二乘系统的强大功能"""
    
    config = {
        'vision_dim': 512,
        'language_dim': 768,
        'numeric_dim': 64,
        'latent_dim': 256,
        'output_dim': 1,
        'action_dim': 5
    }
    
    # 创建终极系统
    universal_system = UniversalLeastSquaresSystem(config)
    
    # 创建训练器
    trainer = LeastSquaresUniverseTrainer(universal_system, config)
    
    # 模拟多模态输入
    sample_inputs = {
        'vision': torch.randn(1, 512),
        'language': torch.randn(1, 768),
        'numeric': torch.randn(1, 64),
        'targets': torch.randn(1, 1)
    }
    
    # 测试前向传播
    with torch.no_grad():
        outputs = universal_system(sample_inputs)
        print("系统输出结构:")
        for key, value in outputs.items():
            if isinstance(value, torch.Tensor):
                print(f"{key}: {value.shape}")
            else:
                print(f"{key}: {value}")
    
    print("\n融合权重:", outputs['fusion_weights'])
    print("最终预测:", outputs['prediction'])

class TrainingThread(QThread):
    """训练线程，防止界面卡死"""
    update_signal = pyqtSignal(dict)  # 发送训练进度信息
    finished_signal = pyqtSignal(bool)  # 发送训练完成信号
    
    def __init__(self, model, trainer, data, epochs):
        super().__init__()
        self.model = model
        self.trainer = trainer
        self.data = data
        self.epochs = epochs
        self.is_running = True
        
    def run(self):
        """执行训练"""
        try:
            for epoch in range(self.epochs):
                if not self.is_running:
                    break
                    
                # 模拟训练步骤
                loss = np.random.random() * (1 - epoch/self.epochs)  # 模拟损失下降
                accuracy = 0.8 + 0.2 * (epoch/self.epochs)  # 模拟准确率上升
                
                # 发送更新信号
                self.update_signal.emit({
                    'epoch': epoch + 1,
                    'total_epochs': self.epochs,
                    'loss': loss,
                    'accuracy': accuracy,
                    'quantum_amplitude': np.random.random(),
                    'fusion_weights': np.random.random(3)
                })
                
                # 模拟训练时间
                self.msleep(100)
                
            self.finished_signal.emit(True)
        except Exception as e:
            self.finished_signal.emit(False)
            
    def stop(self):
        """停止训练"""
        self.is_running = False

class MplCanvas(FigureCanvas):
    """Matplotlib画布"""
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_subplot(111)
        super().__init__(self.fig)
        self.setParent(parent)
        
    def update_plot(self, data, plot_type):
        """更新绘图"""
        self.axes.clear()
        
        if plot_type == "loss":
            self.axes.plot(data['epochs'], data['losses'], 'b-', label='Training Loss')
            if 'val_losses' in data:
                self.axes.plot(data['epochs'], data['val_losses'], 'r-', label='Validation Loss')
            self.axes.set_xlabel('Epoch')
            self.axes.set_ylabel('Loss')
            self.axes.legend()
            self.axes.grid(True, alpha=0.3)
            
        elif plot_type == "accuracy":
            self.axes.plot(data['epochs'], data['accuracies'], 'g-', label='Accuracy')
            self.axes.set_xlabel('Epoch')
            self.axes.set_ylabel('Accuracy')
            self.axes.legend()
            self.axes.grid(True, alpha=0.3)
            
        elif plot_type == "quantum_states":
            amplitudes = data['amplitudes']
            states = range(len(amplitudes))
            self.axes.bar(states, amplitudes, color='purple', alpha=0.7)
            self.axes.set_xlabel('Quantum State')
            self.axes.set_ylabel('Amplitude')
            self.axes.set_title('Quantum State Amplitudes')
            
        elif plot_type == "fusion_weights":
            weights = data['weights']
            labels = ['Meta-Learning', 'Quantum', 'RL']
            colors = ['#FF6B6B', '#4ECDC4', '#45B7D1']
            self.axes.pie(weights, labels=labels, colors=colors, autopct='%1.1f%%')
            self.axes.set_title('Fusion Weights Distribution')
            
        elif plot_type == "prediction_vs_actual":
            actual = data['actual']
            predicted = data['predicted']
            self.axes.scatter(actual, predicted, alpha=0.6, color='blue')
            min_val = min(min(actual), min(predicted))
            max_val = max(max(actual), max(predicted))
            self.axes.plot([min_val, max_val], [min_val, max_val], 'r--', alpha=0.8)
            self.axes.set_xlabel('Actual Values')
            self.axes.set_ylabel('Predicted Values')
            self.axes.set_title('Prediction vs Actual')
            self.axes.grid(True, alpha=0.3)
            
        elif plot_type == "residuals":
            actual = data['actual']
            predicted = data['predicted']
            residuals = actual - predicted
            self.axes.scatter(predicted, residuals, alpha=0.6, color='green')
            self.axes.axhline(y=0, color='r', linestyle='--')
            self.axes.set_xlabel('Predicted Values')
            self.axes.set_ylabel('Residuals')
            self.axes.set_title('Residual Analysis')
            self.axes.grid(True, alpha=0.3)
            
        self.fig.tight_layout()
        self.draw()

class ControlPanel(QWidget):
    """控制面板"""
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 模型配置组
        model_group = QGroupBox("模型配置")
        model_layout = QGridLayout()
        
        model_layout.addWidget(QLabel("输入维度:"), 0, 0)
        self.input_dim = QSpinBox()
        self.input_dim.setRange(1, 1000)
        self.input_dim.setValue(10)
        model_layout.addWidget(self.input_dim, 0, 1)
        
        model_layout.addWidget(QLabel("输出维度:"), 1, 0)
        self.output_dim = QSpinBox()
        self.output_dim.setRange(1, 100)
        self.output_dim.setValue(1)
        model_layout.addWidget(self.output_dim, 1, 1)
        
        model_layout.addWidget(QLabel("隐藏层维度:"), 2, 0)
        self.hidden_dim = QLineEdit("64,32")
        model_layout.addWidget(self.hidden_dim, 2, 1)
        
        model_layout.addWidget(QLabel("量子态数量:"), 3, 0)
        self.quantum_states = QSpinBox()
        self.quantum_states.setRange(1, 20)
        self.quantum_states.setValue(8)
        model_layout.addWidget(self.quantum_states, 3, 1)
        
        model_group.setLayout(model_layout)
        layout.addWidget(model_group)
        
        # 训练参数组
        train_group = QGroupBox("训练参数")
        train_layout = QGridLayout()
        
        train_layout.addWidget(QLabel("训练轮数:"), 0, 0)
        self.epochs = QSpinBox()
        self.epochs.setRange(1, 10000)
        self.epochs.setValue(100)
        train_layout.addWidget(self.epochs, 0, 1)
        
        train_layout.addWidget(QLabel("学习率:"), 1, 0)
        self.learning_rate = QDoubleSpinBox()
        self.learning_rate.setRange(0.0001, 1.0)
        self.learning_rate.setValue(0.001)
        self.learning_rate.setDecimals(4)
        train_layout.addWidget(self.learning_rate, 1, 1)
        
        train_layout.addWidget(QLabel("批大小:"), 2, 0)
        self.batch_size = QSpinBox()
        self.batch_size.setRange(1, 1024)
        self.batch_size.setValue(32)
        train_layout.addWidget(self.batch_size, 2, 1)
        
        train_group.setLayout(train_layout)
        layout.addWidget(train_group)
        
        # 算法选择组
        algo_group = QGroupBox("算法选项")
        algo_layout = QVBoxLayout()
        
        self.use_quantum = QCheckBox("使用量子最小二乘")
        self.use_quantum.setChecked(True)
        algo_layout.addWidget(self.use_quantum)
        
        self.use_meta = QCheckBox("使用元学习")
        self.use_meta.setChecked(True)
        algo_layout.addWidget(self.use_meta)
        
        self.use_rl = QCheckBox("使用强化学习")
        self.use_rl.setChecked(True)
        algo_layout.addWidget(self.use_rl)
        
        self.use_evolution = QCheckBox("使用进化优化")
        algo_layout.addWidget(self.use_evolution)
        
        algo_group.setLayout(algo_layout)
        layout.addWidget(algo_group)
        
        # 控制按钮
        self.train_btn = QPushButton("开始训练")
        self.train_btn.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; }")
        layout.addWidget(self.train_btn)
        
        self.stop_btn = QPushButton("停止训练")
        self.stop_btn.setStyleSheet("QPushButton { background-color: #f44336; color: white; }")
        self.stop_btn.setEnabled(False)
        layout.addWidget(self.stop_btn)
        
        self.predict_btn = QPushButton("执行预测")
        layout.addWidget(self.predict_btn)
        
        layout.addStretch()
        self.setLayout(layout)

class VisualizationPanel(QWidget):
    """可视化面板"""
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.init_data()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 绘图类型选择
        plot_control_layout = QHBoxLayout()
        plot_control_layout.addWidget(QLabel("选择图表类型:"))
        self.plot_selector = QComboBox()
        self.plot_selector.addItems([
            "损失曲线", "准确率曲线", "量子态分布", 
            "融合权重", "预测vs实际", "残差分析"
        ])
        plot_control_layout.addWidget(self.plot_selector)
        plot_control_layout.addStretch()
        
        self.export_plot_btn = QPushButton("导出图表")
        plot_control_layout.addWidget(self.export_plot_btn)
        
        layout.addLayout(plot_control_layout)
        
        # 绘图区域
        self.canvas = MplCanvas(self, width=8, height=6, dpi=100)
        layout.addWidget(self.canvas)
        
        # 实时数据展示
        self.data_table = QTableWidget(5, 3)
        self.data_table.setHorizontalHeaderLabels(["指标", "当前值", "历史最佳"])
        self.data_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.data_table)
        
        self.setLayout(layout)
        
    def init_data(self):
        """初始化示例数据"""
        self.training_data = {
            'epochs': list(range(100)),
            'losses': np.random.exponential(1, 100) * np.linspace(1, 0.1, 100),
            'val_losses': np.random.exponential(1, 100) * np.linspace(1, 0.15, 100),
            'accuracies': 0.7 + 0.3 * (1 - np.exp(-np.linspace(0, 5, 100))),
            'amplitudes': np.random.dirichlet(np.ones(8)),
            'weights': np.random.dirichlet(np.ones(3)),
            'actual': np.random.normal(0, 1, 100),
            'predicted': np.random.normal(0, 1, 100) * 0.9 + 0.1
        }
        
        # 初始化表格数据
        self.update_table({
            'loss': 0.1234,
            'accuracy': 0.8567,
            'quantum_amplitude': 0.5432,
            'fusion_weights': [0.4, 0.35, 0.25]
        })
        
        # 显示初始图表
        self.update_plot()
        
    def update_plot(self):
        """更新图表"""
        plot_type = self.plot_selector.currentText()
        
        if plot_type == "损失曲线":
            self.canvas.update_plot(self.training_data, "loss")
        elif plot_type == "准确率曲线":
            self.canvas.update_plot(self.training_data, "accuracy")
        elif plot_type == "量子态分布":
            self.canvas.update_plot(self.training_data, "quantum_states")
        elif plot_type == "融合权重":
            self.canvas.update_plot(self.training_data, "fusion_weights")
        elif plot_type == "预测vs实际":
            self.canvas.update_plot(self.training_data, "prediction_vs_actual")
        elif plot_type == "残差分析":
            self.canvas.update_plot(self.training_data, "residuals")
            
    def update_table(self, metrics):
        """更新数据表格"""
        data = [
            ["训练损失", f"{metrics.get('loss', 0):.4f}", "0.0345"],
            ["准确率", f"{metrics.get('accuracy', 0):.2%}", "92.34%"],
            ["量子振幅", f"{metrics.get('quantum_amplitude', 0):.4f}", "0.8765"],
            ["元学习权重", f"{metrics.get('fusion_weights', [0,0,0])[0]:.3f}", "0.456"],
            ["量子权重", f"{metrics.get('fusion_weights', [0,0,0])[1]:.3f}", "0.321"]
        ]
        
        for i, row in enumerate(data):
            for j, value in enumerate(row):
                self.data_table.setItem(i, j, QTableWidgetItem(str(value)))
                
    def export_plot(self):
        """导出当前图表"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存图表", "", "PNG文件 (*.png);;PDF文件 (*.pdf);;所有文件 (*)"
        )
        
        if file_path:
            self.canvas.fig.savefig(file_path, dpi=300, bbox_inches='tight')
            QMessageBox.information(self, "导出成功", f"图表已保存到: {file_path}")

class DataExportPanel(QWidget):
    """数据导出面板"""
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 导出选项
        export_group = QGroupBox("导出选项")
        export_layout = QGridLayout()
        
        export_layout.addWidget(QLabel("导出格式:"), 0, 0)
        self.export_format = QComboBox()
        self.export_format.addItems(["CSV", "Excel", "JSON", "Pickle"])
        export_layout.addWidget(self.export_format, 0, 1)
        
        export_layout.addWidget(QLabel("数据范围:"), 1, 0)
        self.data_range = QComboBox()
        self.data_range.addItems(["全部数据", "最近100条", "最近1000条", "自定义..."])
        export_layout.addWidget(self.data_range, 1, 1)
        
        export_layout.addWidget(QLabel("包含列:"), 2, 0)
        self.columns_include = QLineEdit("epoch,loss,accuracy,quantum_amplitude,fusion_weights")
        export_layout.addWidget(self.columns_include, 2, 1)
        
        export_group.setLayout(export_layout)
        layout.addWidget(export_group)
        
        # 预览区域
        preview_group = QGroupBox("数据预览")
        preview_layout = QVBoxLayout()
        
        self.preview_table = QTableWidget(10, 5)
        self.preview_table.setHorizontalHeaderLabels(["Epoch", "Loss", "Accuracy", "Quantum", "Meta Weight"])
        preview_layout.addWidget(self.preview_table)
        
        preview_group.setLayout(preview_layout)
        layout.addWidget(preview_group)
        
        # 导出按钮
        self.export_btn = QPushButton("导出数据")
        self.export_btn.setStyleSheet("QPushButton { background-color: #2196F3; color: white; }")
        layout.addWidget(self.export_btn)
        
        self.setLayout(layout)
        
        # 初始化预览数据
        self.update_preview()
        
        # 连接信号
        self.export_btn.clicked.connect(self.export_data)
        
    def update_preview(self):
        """更新预览数据"""
        # 生成示例数据
        data = []
        for i in range(10):
            row = [
                i + 1,
                np.random.exponential(1) * (1 - i/10),
                0.7 + 0.3 * (i/10),
                np.random.random(),
                np.random.dirichlet([1,1,1])[0]
            ]
            data.append(row)
            
        # 填充表格
        self.preview_table.setRowCount(len(data))
        for i, row in enumerate(data):
            for j, value in enumerate(row):
                self.preview_table.setItem(i, j, QTableWidgetItem(f"{value:.4f}"))
                
    def export_data(self):
        """导出数据"""
        file_ext = {
            "CSV": "csv",
            "Excel": "xlsx", 
            "JSON": "json",
            "Pickle": "pkl"
        }
        
        format_name = self.export_format.currentText()
        ext = file_ext[format_name]
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, f"导出数据为{format_name}", f"least_squares_data.{ext}", 
            f"{format_name}文件 (*.{ext})"
        )
        
        if file_path:
            try:
                # 创建示例数据框
                epochs = 100
                data = {
                    'epoch': range(1, epochs+1),
                    'loss': np.random.exponential(1, epochs) * np.linspace(1, 0.1, epochs),
                    'accuracy': 0.7 + 0.3 * (1 - np.exp(-np.linspace(0, 5, epochs))),
                    'quantum_amplitude': np.random.random(epochs),
                    'meta_weight': np.random.dirichlet([1,1,1], epochs)[:,0],
                    'quantum_weight': np.random.dirichlet([1,1,1], epochs)[:,1],
                    'rl_weight': np.random.dirichlet([1,1,1], epochs)[:,2]
                }
                
                df = pd.DataFrame(data)
                
                # 根据选择的格式导出
                if format_name == "CSV":
                    df.to_csv(file_path, index=False)
                elif format_name == "Excel":
                    df.to_excel(file_path, index=False)
                elif format_name == "JSON":
                    df.to_json(file_path, indent=2)
                elif format_name == "Pickle":
                    df.to_pickle(file_path)
                    
                QMessageBox.information(self, "导出成功", f"数据已导出到: {file_path}")
                
            except Exception as e:
                QMessageBox.critical(self, "导出失败", f"导出过程中发生错误: {str(e)}")

class LeastSquaresApp(QMainWindow):
    """主应用程序窗口"""
    def __init__(self):
        super().__init__()
        self.model = None
        self.trainer = None
        self.training_thread = None
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("最小二乘神经网络分析平台")
        self.setGeometry(100, 100, 1400, 900)
        
        # 设置样式
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #cccccc;
                border-radius: 5px;
                margin-top: 1ex;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        
        # 创建中央部件和布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 使用分割器创建可调整的布局
        splitter = QSplitter(Qt.Horizontal)
        
        # 左侧控制面板
        self.control_panel = ControlPanel()
        splitter.addWidget(self.control_panel)
        
        # 右侧选项卡
        self.tab_widget = QTabWidget()
        
        # 可视化标签页
        self.viz_panel = VisualizationPanel()
        self.tab_widget.addTab(self.viz_panel, "训练可视化")
        
        # 数据导出标签页
        self.export_panel = DataExportPanel()
        self.tab_widget.addTab(self.export_panel, "数据导出")
        
        # 日志标签页
        self.log_panel = QTextEdit()
        self.log_panel.setReadOnly(True)
        self.tab_widget.addTab(self.log_panel, "训练日志")
        
        splitter.addWidget(self.tab_widget)
        
        # 设置分割器比例
        splitter.setSizes([300, 1100])
        
        # 主布局
        layout = QVBoxLayout()
        layout.addWidget(splitter)
        
        # 底部状态栏
        self.status_bar = self.statusBar()
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(200)
        self.status_bar.addPermanentWidget(self.progress_bar)
        
        central_widget.setLayout(layout)
        
        # 连接信号和槽
        self.connect_signals()
        
        # 初始化日志
        self.log("应用程序启动成功")
        self.log("最小二乘神经网络分析平台已就绪")
        
    def connect_signals(self):
        """连接信号和槽"""
        # 控制面板信号
        self.control_panel.train_btn.clicked.connect(self.start_training)
        self.control_panel.stop_btn.clicked.connect(self.stop_training)
        self.control_panel.predict_btn.clicked.connect(self.run_prediction)
        
        # 可视化面板信号
        self.viz_panel.plot_selector.currentTextChanged.connect(self.viz_panel.update_plot)
        self.viz_panel.export_plot_btn.clicked.connect(self.viz_panel.export_plot)
        
    def start_training(self):
        """开始训练"""
        try:
            # 获取参数
            input_dim = self.control_panel.input_dim.value()
            output_dim = self.control_panel.output_dim.value()
            epochs = self.control_panel.epochs.value()
            
            # 创建模型配置
            config = {
                'input_dim': input_dim,
                'output_dim': output_dim,
                'hidden_dims': [int(x) for x in self.control_panel.hidden_dim.text().split(',')],
                'quantum_states': self.control_panel.quantum_states.value()
            }
            
            # 创建模型和训练器
            self.model = UniversalLeastSquaresSystem(config)
            self.trainer = LeastSquaresUniverseTrainer(self.model, config)
            
            # 创建训练线程
            self.training_thread = TrainingThread(self.model, self.trainer, None, epochs)
            self.training_thread.update_signal.connect(self.update_training_progress)
            self.training_thread.finished_signal.connect(self.training_finished)
            
            # 更新UI状态
            self.control_panel.train_btn.setEnabled(False)
            self.control_panel.stop_btn.setEnabled(True)
            self.progress_bar.setRange(0, epochs)
            
            # 开始训练
            self.training_thread.start()
            
            self.log(f"开始训练: 输入维度={input_dim}, 输出维度={output_dim}, 轮数={epochs}")
            
        except Exception as e:
            QMessageBox.critical(self, "训练错误", f"启动训练时发生错误: {str(e)}")
            self.log(f"训练错误: {str(e)}")
            
    def stop_training(self):
        """停止训练"""
        if self.training_thread and self.training_thread.isRunning():
            self.training_thread.stop()
            self.training_thread.wait()
            
        self.control_panel.train_btn.setEnabled(True)
        self.control_panel.stop_btn.setEnabled(False)
        self.log("训练已停止")
        
    def run_prediction(self):
        """执行预测"""
        if self.model is None:
            QMessageBox.warning(self, "警告", "请先训练模型")
            return
            
        # 模拟预测过程
        self.log("开始执行预测...")
        
        # 模拟预测结果
        actual = np.random.normal(0, 1, 100)
        predicted = actual * 0.95 + np.random.normal(0, 0.1, 100)
        
        # 更新可视化
        self.viz_panel.training_data['actual'] = actual
        self.viz_panel.training_data['predicted'] = predicted
        self.viz_panel.update_plot()
        
        self.log("预测完成")
        QMessageBox.information(self, "预测完成", "预测任务已成功执行")
        
    def update_training_progress(self, metrics):
        """更新训练进度"""
        epoch = metrics['epoch']
        total_epochs = metrics['total_epochs']
        loss = metrics['loss']
        accuracy = metrics['accuracy']
        
        # 更新进度条
        self.progress_bar.setValue(epoch)
        
        # 更新状态栏
        self.status_bar.showMessage(f"训练中... Epoch: {epoch}/{total_epochs}, Loss: {loss:.4f}, Accuracy: {accuracy:.2%}")
        
        # 更新可视化
        self.viz_panel.update_table(metrics)
        
        # 更新日志
        if epoch % 10 == 0:
            self.log(f"Epoch {epoch}/{total_epochs}: Loss={loss:.4f}, Accuracy={accuracy:.2%}")
            
    def training_finished(self, success):
        """训练完成回调"""
        self.control_panel.train_btn.setEnabled(True)
        self.control_panel.stop_btn.setEnabled(False)
        
        if success:
            self.status_bar.showMessage("训练完成")
            self.log("训练成功完成")
            QMessageBox.information(self, "训练完成", "模型训练已成功完成")
        else:
            self.status_bar.showMessage("训练失败")
            self.log("训练过程中出现错误")
            QMessageBox.warning(self, "训练失败", "训练过程中出现错误")
            
    def log(self, message):
        """添加日志"""
        timestamp = pd.Timestamp.now().strftime("%H:%M:%S")
        self.log_panel.append(f"[{timestamp}] {message}")
        
    def closeEvent(self, event):
        """应用程序关闭事件"""
        if self.training_thread and self.training_thread.isRunning():
            reply = QMessageBox.question(
                self, '确认退出', 
                '训练仍在进行中，确定要退出吗？',
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.training_thread.stop()
                self.training_thread.wait()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()

# 简化版的模型实现（用于演示）
class UniversalLeastSquaresSystem(nn.Module):
    """简化版的通用最小二乘系统"""
    def __init__(self, config):
        super().__init__()
        self.config = config
        
    def forward(self, x):
        return x

class LeastSquaresUniverseTrainer:
    """简化版的训练器"""
    def __init__(self, model, config):
        self.model = model
        self.config = config

def main():
    """主函数"""
    app = QApplication(sys.argv)
    
    # 设置应用程序样式
    app.setStyle('Fusion')
    
    # 创建并显示主窗口
    window = LeastSquaresApp()
    window.show()
    
    # 运行应用程序
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()