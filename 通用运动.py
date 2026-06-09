import sys
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                             QWidget, QPushButton, QSlider, QLabel, QComboBox, 
                             QTabWidget, QGroupBox, QSpinBox, QDoubleSpinBox, 
                             QCheckBox, QTextEdit, QSplitter, QFileDialog, 
                             QMessageBox, QProgressBar, QListWidget, QTreeWidget, 
                             QTreeWidgetItem, QDockWidget, QGraphicsView, QGraphicsScene,
                             QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread, QObject, QPointF, QRectF
from PyQt5.QtGui import QFont, QPalette, QColor, QLinearGradient, QPainter, QPen, QBrush, QPixmap
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from mpl_toolkits.mplot3d import Axes3D
import json
import time
import random

from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
import hashlib
import math
from scipy import signal
from scipy.spatial import distance
import networkx as nx
from sklearn.manifold import TSNE
from sklearn.cluster import DBSCAN
import pickle
import zipfile
import os
from datetime import datetime
import numpy as np
from matplotlib.figure import Figure

class TwoLinkArm:
    def __init__(self, l1=1.0, l2=0.8):
        self.name = "Two-Link Arm"
        self.dof = 2
        self.joint_limits = [(-np.pi, np.pi), (-np.pi, np.pi)]
        self.parameters = {"l1": l1, "l2": l2}
        
    def forward_kinematics(self, joint_angles):
        theta1, theta2 = joint_angles
        l1, l2 = self.parameters["l1"], self.parameters["l2"]
        
        x = l1 * np.cos(theta1) + l2 * np.cos(theta1 + theta2)
        y = l1 * np.sin(theta1) + l2 * np.sin(theta1 + theta2)
        
        return np.array([x, y])
    
    def inverse_kinematics(self, target_position):
        x, y = target_position
        l1, l2 = self.parameters["l1"], self.parameters["l2"]
        
        # 计算第二个关节角度
        D = (x**2 + y**2 - l1**2 - l2**2) / (2 * l1 * l2)
        D = np.clip(D, -1, 1)  # 避免数值误差
        
        theta2 = np.arccos(D)  # 肘部向上解
        
        # 计算第一个关节角度
        theta1 = np.arctan2(y, x) - np.arctan2(l2 * np.sin(theta2), l1 + l2 * np.cos(theta2))
        
        return np.array([theta1, theta2])
    
    def jacobian(self, joint_angles):
        theta1, theta2 = joint_angles
        l1, l2 = self.parameters["l1"], self.parameters["l2"]
        
        J11 = -l1 * np.sin(theta1) - l2 * np.sin(theta1 + theta2)
        J12 = -l2 * np.sin(theta1 + theta2)
        J21 = l1 * np.cos(theta1) + l2 * np.cos(theta1 + theta2)
        J22 = l2 * np.cos(theta1 + theta2)
        
        return np.array([[J11, J12], [J21, J22]])
# 神经形态计算引擎
class NeuromorphicEngine:
    def __init__(self, num_neurons=1000, connectivity=0.1):
        self.num_neurons = num_neurons
        self.connectivity = connectivity
        self.neurons = np.zeros(num_neurons)
        self.weights = self.initialize_weights()
        self.thresholds = np.random.normal(0.5, 0.1, num_neurons)
        self.plasticity_rules = self.setup_plasticity_rules()
        self.memory_traces = np.zeros(num_neurons)
        self.temporal_dynamics = np.zeros(num_neurons)
        
    def initialize_weights(self):
        """初始化脉冲神经网络权重"""
        weights = np.random.normal(0, 0.1, (self.num_neurons, self.num_neurons))
        # 应用稀疏连接
        mask = np.random.random((self.num_neurons, self.num_neurons)) < self.connectivity
        weights = weights * mask
        return weights
    
    def setup_plasticity_rules(self):
        """设置神经可塑性规则"""
        rules = {
            'stdp': self.stdp_rule,  # 脉冲时序依赖可塑性
            'homeostatic': self.homeostatic_plasticity,
            'heterosynaptic': self.heterosynaptic_plasticity
        }
        return rules
    
    def stdp_rule(self, pre_spikes, post_spikes, dt=1.0):
        """脉冲时序依赖可塑性"""
        A_plus, A_minus = 0.1, 0.12  # 学习率参数
        tau_plus, tau_minus = 20.0, 20.0  # 时间常数
        
        for i in range(self.num_neurons):
            for j in range(self.num_neurons):
                if pre_spikes[i] and not post_spikes[j]:
                    # 前脉冲后无脉冲 - 抑制
                    self.weights[i, j] -= A_minus * np.exp(-dt / tau_minus)
                elif not pre_spikes[i] and post_spikes[j]:
                    # 前无脉冲后脉冲 - 增强
                    self.weights[i, j] += A_plus * np.exp(-dt / tau_plus)
        
        # 限制权重范围
        self.weights = np.clip(self.weights, -1.0, 1.0)
    
    def homeostatic_plasticity(self, activity_level):
        """稳态可塑性 - 维持网络整体活动水平"""
        target_activity = 0.1  # 目标活动水平
        scaling_factor = 1.0 + (target_activity - activity_level) * 0.1
        self.thresholds *= scaling_factor
        self.thresholds = np.clip(self.thresholds, 0.1, 0.9)
    
    def heterosynaptic_plasticity(self):
        """异突触可塑性 - 平衡兴奋和抑制"""
        excitatory = np.sum(self.weights[self.weights > 0])
        inhibitory = np.sum(np.abs(self.weights[self.weights < 0]))
        
        if excitatory > inhibitory * 1.5:  # 兴奋性过强
            # 增加抑制性权重
            inhibitory_mask = self.weights < 0
            self.weights[inhibitory_mask] *= 1.05
        elif inhibitory > excitatory * 1.5:  # 抑制性过强
            # 增加兴奋性权重
            excitatory_mask = self.weights > 0
            self.weights[excitatory_mask] *= 1.05
    
    def update(self, inputs, dt=1.0):
        """更新神经形态网络"""
        # 应用输入到输入神经元
        input_size = min(len(inputs), self.num_neurons // 10)
        self.neurons[:input_size] += inputs[:input_size]
        
        # 计算膜电位
        membrane_potentials = self.neurons + np.dot(self.weights, self.neurons)
        
        # 应用时间动力学
        self.temporal_dynamics = 0.9 * self.temporal_dynamics + 0.1 * membrane_potentials
        
        # 生成脉冲
        spikes = membrane_potentials > self.thresholds
        self.neurons[spikes] = 1.0  # 发放脉冲
        self.neurons[~spikes] *= 0.9  # 衰减
        
        # 更新可塑性
        self.plasticity_rules['stdp'](spikes, spikes, dt)
        
        # 计算活动水平并应用稳态可塑性
        activity_level = np.mean(spikes)
        self.plasticity_rules['homeostatic'](activity_level)
        self.plasticity_rules['heterosynaptic']()
        
        # 更新记忆痕迹
        self.memory_traces = 0.95 * self.memory_traces + 0.05 * spikes
        
        return spikes, membrane_potentials

# 群体智能控制系统
class SwarmIntelligenceController:
    def __init__(self, num_agents=50, search_space=(-2, 2)):
        self.num_agents = num_agents
        self.search_space = search_space
        self.agents = self.initialize_agents()
        self.global_best_position = None
        self.global_best_fitness = -float('inf')
        self.interaction_network = self.create_interaction_network()
        self.emergence_threshold = 0.7
        self.collective_intelligence = 0.0
        
    def initialize_agents(self):
        """初始化智能体群"""
        agents = []
        for i in range(self.num_agents):
            position = np.random.uniform(self.search_space[0], self.search_space[1], 2)
            velocity = np.random.uniform(-0.1, 0.1, 2)
            agent = {
                'id': i,
                'position': position,
                'velocity': velocity,
                'best_position': position.copy(),
                'best_fitness': -float('inf'),
                'type': np.random.choice(['explorer', 'exploiter', 'sentinel']),
                'influence_radius': np.random.uniform(0.1, 0.5),
                'communication_range': np.random.uniform(0.3, 1.0)
            }
            agents.append(agent)
        return agents
    
    def create_interaction_network(self):
        """创建智能体交互网络"""
        G = nx.Graph()
        for i in range(self.num_agents):
            G.add_node(i)
            
        # 基于距离的概率连接
        for i in range(self.num_agents):
            for j in range(i+1, self.num_agents):
                dist = np.linalg.norm(self.agents[i]['position'] - self.agents[j]['position'])
                if dist < 1.0 and np.random.random() < 0.3:
                    G.add_edge(i, j, weight=1.0/dist)
                    
        return G
    
    def evaluate_fitness(self, position, target):
        """评估位置适应度"""
        # 基于距离目标的接近程度
        distance_to_target = np.linalg.norm(position - target)
        fitness = 1.0 / (1.0 + distance_to_target)
        return fitness
    
    def update_swarm(self, target_position, obstacles=[]):
        """更新群体状态"""
        # 更新每个智能体
        for agent in self.agents:
            # 评估当前位置适应度
            current_fitness = self.evaluate_fitness(agent['position'], target_position)
            
            # 更新个体最佳
            if current_fitness > agent['best_fitness']:
                agent['best_fitness'] = current_fitness
                agent['best_position'] = agent['position'].copy()
            
            # 更新全局最佳
            if current_fitness > self.global_best_fitness:
                self.global_best_fitness = current_fitness
                self.global_best_position = agent['position'].copy()
            
            # 根据智能体类型更新行为
            if agent['type'] == 'explorer':
                self.update_explorer(agent, target_position)
            elif agent['type'] == 'exploiter':
                self.update_exploiter(agent, target_position)
            elif agent['type'] == 'sentinel':
                self.update_sentinel(agent, target_position)
            
            # 应用边界条件
            agent['position'] = np.clip(agent['position'], 
                                      self.search_space[0], self.search_space[1])
        
        # 更新交互网络
        self.update_interaction_network()
        
        # 检测涌现行为
        self.detect_emergence(target_position)
        
        return self.global_best_position, self.global_best_fitness
    
    def update_explorer(self, agent, target):
        """探索者行为 - 广泛搜索"""
        # 随机探索与目标导向的平衡
        exploration_bias = 0.7  # 偏向探索
        
        if np.random.random() < exploration_bias:
            # 随机探索
            agent['velocity'] += np.random.uniform(-0.05, 0.05, 2)
        else:
            # 向目标移动
            direction = target - agent['position']
            direction = direction / (np.linalg.norm(direction) + 1e-8)
            agent['velocity'] += direction * 0.02
        
        # 速度限制
        agent['velocity'] = np.clip(agent['velocity'], -0.2, 0.2)
        agent['position'] += agent['velocity']
    
    def update_exploiter(self, agent, target):
        """利用者行为 - 精细搜索"""
        # 主要关注已知的好位置
        exploitation_bias = 0.8
        
        if np.random.random() < exploitation_bias and self.global_best_position is not None:
            # 向全局最佳移动
            direction = self.global_best_position - agent['position']
            direction = direction / (np.linalg.norm(direction) + 1e-8)
            agent['velocity'] += direction * 0.03
        else:
            # 向目标移动
            direction = target - agent['position']
            direction = direction / (np.linalg.norm(direction) + 1e-8)
            agent['velocity'] += direction * 0.02
        
        # 局部精细搜索
        agent['velocity'] += np.random.uniform(-0.01, 0.01, 2)
        agent['velocity'] = np.clip(agent['velocity'], -0.1, 0.1)
        agent['position'] += agent['velocity']
    
    def update_sentinel(self, agent, target):
        """哨兵行为 - 监视和通信"""
        # 在重要位置附近巡逻
        if self.global_best_position is not None:
            # 在全局最佳位置周围巡逻
            patrol_radius = 0.3
            angle = time.time() * 0.5 + agent['id']  # 基于时间的相位
            patrol_offset = np.array([np.cos(angle), np.sin(angle)]) * patrol_radius
            target_position = self.global_best_position + patrol_offset
        else:
            target_position = target
        
        # 向目标位置移动
        direction = target_position - agent['position']
        direction = direction / (np.linalg.norm(direction) + 1e-8)
        agent['velocity'] += direction * 0.02
        
        # 与其他智能体通信
        self.communicate_with_neighbors(agent)
        
        agent['velocity'] = np.clip(agent['velocity'], -0.15, 0.15)
        agent['position'] += agent['velocity']
    
    def communicate_with_neighbors(self, agent):
        """与邻近智能体通信"""
        neighbors = []
        for other_agent in self.agents:
            if other_agent['id'] != agent['id']:
                dist = np.linalg.norm(agent['position'] - other_agent['position'])
                if dist < agent['communication_range']:
                    neighbors.append(other_agent)
        
        if neighbors:
            # 平均邻居的速度（简单的共识算法）
            neighbor_velocities = [n['velocity'] for n in neighbors]
            average_velocity = np.mean(neighbor_velocities, axis=0)
            agent['velocity'] = 0.7 * agent['velocity'] + 0.3 * average_velocity
    
    def update_interaction_network(self):
        """更新交互网络"""
        self.interaction_network.clear_edges()
        
        # 基于当前距离重新连接
        for i in range(self.num_agents):
            for j in range(i+1, self.num_agents):
                dist = np.linalg.norm(self.agents[i]['position'] - self.agents[j]['position'])
                if dist < self.agents[i]['communication_range'] and dist < self.agents[j]['communication_range']:
                    # 距离越近，连接权重越大
                    weight = 1.0 / (1.0 + dist)
                    self.interaction_network.add_edge(i, j, weight=weight)
    
    def detect_emergence(self, target):
        """检测涌现行为"""
        # 计算群体一致性
        positions = np.array([agent['position'] for agent in self.agents])
        centroid = np.mean(positions, axis=0)
        dispersion = np.mean(np.linalg.norm(positions - centroid, axis=1))
        
        # 计算目标接近度
        target_distances = np.linalg.norm(positions - target, axis=1)
        avg_target_distance = np.mean(target_distances)
        
        # 计算网络连通性
        connectivity = nx.density(self.interaction_network)
        
        # 综合评估集体智能
        self.collective_intelligence = (
            (1.0 / (1.0 + dispersion)) * 0.4 +  # 一致性
            (1.0 / (1.0 + avg_target_distance)) * 0.4 +  # 目标导向性
            connectivity * 0.2  # 连通性
        )
        
        # 检测是否出现涌现行为
        if self.collective_intelligence > self.emergence_threshold:
            self.handle_emergence()
    
    def handle_emergence(self):
        """处理涌现行为"""
        # 当集体智能超过阈值时，增强群体能力
        for agent in self.agents:
            # 增加通信范围
            agent['communication_range'] *= 1.1
            # 增加影响力半径
            agent['influence_radius'] *= 1.05
        
        # 随机将一些探索者转变为利用者
        for agent in self.agents:
            if agent['type'] == 'explorer' and np.random.random() < 0.2:
                agent['type'] = 'exploiter'

# 超材料形态控制
class MetamaterialController:
    def __init__(self, grid_size=20, material_properties=None):
        self.grid_size = grid_size
        self.material_properties = material_properties or self.default_properties()
        self.stiffness_grid = np.ones((grid_size, grid_size))
        self.deformation_grid = np.zeros((grid_size, grid_size, 2))
        self.activation_pattern = np.zeros((grid_size, grid_size))
        self.topology = self.initialize_topology()
        self.phase_transitions = []
        
    def default_properties(self):
        """默认超材料属性"""
        return {
            'youngs_modulus_range': (0.1, 10.0),  # 杨氏模量范围
            'poissons_ratio_range': (0.1, 0.4),   # 泊松比范围
            'density_range': (0.5, 2.0),          # 密度范围
            'phase_transition_temp': 0.7,         # 相变温度
            'shape_memory_effect': True           # 形状记忆效应
        }
    
    def initialize_topology(self):
        """初始化超材料拓扑结构"""
        # 创建初始网格拓扑
        topology = np.ones((self.grid_size, self.grid_size))
        
        # 随机引入一些孔洞或薄弱点
        for i in range(self.grid_size):
            for j in range(self.grid_size):
                if np.random.random() < 0.1:  # 10%的概率创建孔洞
                    topology[i, j] = 0
                    
        return topology
    
    def apply_mechanical_stress(self, stress_field):
        """应用机械应力并计算变形"""
        # 简化线性弹性模型
        for i in range(1, self.grid_size-1):
            for j in range(1, self.grid_size-1):
                if self.topology[i, j] > 0:  # 只有实体材料点响应
                    # 计算局部应力
                    local_stress = stress_field[i, j]
                    
                    # 基于材料属性计算应变
                    youngs_modulus = self.get_material_property(i, j, 'youngs_modulus')
                    strain = local_stress / youngs_modulus
                    
                    # 更新变形
                    self.deformation_grid[i, j] = strain * 0.1
                    
                    # 传播变形到邻居
                    for di in [-1, 0, 1]:
                        for dj in [-1, 0, 1]:
                            if di == 0 and dj == 0:
                                continue
                            ni, nj = i+di, j+dj
                            if 0 <= ni < self.grid_size and 0 <= nj < self.grid_size:
                                # 衰减传播
                                propagation_factor = 0.3 / (abs(di) + abs(dj))
                                self.deformation_grid[ni, nj] += (
                                    self.deformation_grid[i, j] * propagation_factor
                                )
    
    def get_material_property(self, i, j, property_name):
        """获取材料点属性"""
        prop_range = self.material_properties.get(property_name + '_range', (0.1, 1.0))
        
        # 基于激活模式和拓扑调整属性
        base_value = np.random.uniform(prop_range[0], prop_range[1])
        activation_factor = 1.0 + self.activation_pattern[i, j] * 0.5
        topology_factor = self.topology[i, j]
        
        return base_value * activation_factor * topology_factor
    
    def adaptive_redistribution(self, performance_feedback):
        """基于性能反馈自适应重新分布材料"""
        # 根据性能反馈调整刚度分布
        for i in range(self.grid_size):
            for j in range(self.grid_size):
                # 高应力区域增加刚度
                stress_magnitude = np.linalg.norm(self.deformation_grid[i, j])
                if stress_magnitude > 0.1:  # 高应力阈值
                    self.stiffness_grid[i, j] *= 1.1
                else:
                    self.stiffness_grid[i, j] *= 0.99  # 轻微衰减
                
                # 限制刚度范围
                self.stiffness_grid[i, j] = np.clip(self.stiffness_grid[i, j], 0.1, 10.0)
                
                # 基于性能反馈调整拓扑
                if performance_feedback < 0.5 and np.random.random() < 0.05:
                    # 性能不佳时随机改变拓扑
                    self.topology[i, j] = 1 - self.topology[i, j]  # 翻转
    
    def phase_transition(self, external_stimulus):
        """相变响应外部刺激"""
        # 检查是否达到相变条件
        stimulus_intensity = np.mean(np.abs(external_stimulus))
        transition_temp = self.material_properties['phase_transition_temp']
        
        if stimulus_intensity > transition_temp:
            # 记录相变
            transition = {
                'time': time.time(),
                'location': np.unravel_index(np.argmax(external_stimulus), external_stimulus.shape),
                'intensity': stimulus_intensity
            }
            self.phase_transitions.append(transition)
            
            # 应用相变效果
            max_i, max_j = transition['location']
            radius = 3  # 相变影响半径
            
            for i in range(max(0, max_i-radius), min(self.grid_size, max_i+radius+1)):
                for j in range(max(0, max_j-radius), min(self.grid_size, max_j+radius+1)):
                    dist = np.sqrt((i-max_i)**2 + (j-max_j)**2)
                    if dist <= radius:
                        # 距离越近，相变效果越强
                        effect = 1.0 - dist/radius
                        self.activation_pattern[i, j] = effect
                        
                        # 如果是形状记忆材料，可以恢复原始形状
                        if self.material_properties['shape_memory_effect']:
                            self.deformation_grid[i, j] *= (1.0 - effect*0.5)

# 意识-机器接口模拟
class BrainMachineInterface:
    def __init__(self, signal_dim=32, sampling_rate=256):
        self.signal_dim = signal_dim
        self.sampling_rate = sampling_rate
        self.brain_signals = np.zeros(signal_dim)
        self.attention_level = 0.5
        self.cognitive_load = 0.0
        self.mental_commands = {}
        self.intent_recognition = IntentRecognizer()
        self.neural_adaptation = NeuralAdaptationModel()
        self.setup_mental_commands()
        
    def setup_mental_commands(self):
        """设置可识别的心理命令"""
        self.mental_commands = {
            'move_forward': self.decode_move_forward,
            'move_backward': self.decode_move_backward,
            'turn_left': self.decode_turn_left,
            'turn_right': self.decode_turn_right,
            'stop': self.decode_stop,
            'increase_speed': self.decode_increase_speed,
            'decrease_speed': self.decode_decrease_speed
        }
    
    def simulate_brain_activity(self, visual_input, task_difficulty):
        """模拟大脑活动基于视觉输入和任务难度"""
        # 生成模拟脑电信号
        time_point = time.time() * 10  # 快速时间变化
        
        # 基础脑电节律
        alpha_rhythm = np.sin(2 * np.pi * 10 * time_point / self.sampling_rate)  # 10Hz alpha
        beta_rhythm = np.sin(2 * np.pi * 20 * time_point / self.sampling_rate)   # 20Hz beta
        
        # 视觉刺激响应
        visual_response = np.sum(np.abs(visual_input)) * 0.01 if visual_input is not None else 0
        
        # 任务难度影响
        task_effect = task_difficulty * 0.5
        
        # 组合信号
        base_signal = alpha_rhythm * 0.3 + beta_rhythm * 0.5 + visual_response + task_effect
        
        # 添加噪声和个体差异
        noise = np.random.normal(0, 0.1, self.signal_dim)
        individual_variation = np.sin(np.arange(self.signal_dim) * 0.1)
        
        self.brain_signals = base_signal + noise + individual_variation
        
        # 更新认知状态
        self.update_cognitive_state(visual_input, task_difficulty)
        
        return self.brain_signals
    
    def update_cognitive_state(self, visual_input, task_difficulty):
        """更新认知状态"""
        # 注意力水平基于视觉复杂度和任务难度
        visual_complexity = np.std(visual_input) if visual_input is not None else 0
        self.attention_level = 0.7 - visual_complexity * 0.1 + task_difficulty * 0.2
        self.attention_level = np.clip(self.attention_level, 0.1, 0.9)
        
        # 认知负载
        self.cognitive_load = task_difficulty * 0.8 + visual_complexity * 0.2
    
    def decode_mental_command(self, intended_action):
        """解码心理命令"""
        if intended_action in self.mental_commands:
            return self.mental_commands[intended_action]()
        else:
            return np.zeros(2)  # 默认无动作
    
    def decode_move_forward(self):
        """解码'前进'心理命令"""
        return np.array([0.1, 0.0])  # 轻微前进
    
    def decode_move_backward(self):
        """解码'后退'心理命令"""
        return np.array([-0.05, 0.0])  # 轻微后退
    
    def decode_turn_left(self):
        """解码'左转'心理命令"""
        return np.array([0.0, 0.1])  # 左转
    
    def decode_turn_right(self):
        """解码'右转'心理命令"""
        return np.array([0.0, -0.1])  # 右转
    
    def decode_stop(self):
        """解码'停止'心理命令"""
        return np.array([0.0, 0.0])  # 停止
    
    def decode_increase_speed(self):
        """解码'加速'心理命令"""
        return np.array([0.2, 0.0])  # 加速
    
    def decode_decrease_speed(self):
        """解码'减速'心理命令"""
        return np.array([-0.1, 0.0])  # 减速
    
    def adapt_interface(self, performance_feedback):
        """基于性能反馈自适应调整接口"""
        self.neural_adaptation.adapt(performance_feedback, self.brain_signals)
        
        # 调整心理命令解码灵敏度
        adaptation_factor = 1.0 + performance_feedback * 0.2
        for command in self.mental_commands.values():
            # 这里简化处理，实际需要更复杂的调整
            pass

# 辅助类
class IntentRecognizer:
    def __init__(self):
        self.pattern_library = {}
        self.recognition_threshold = 0.7
        
    def recognize_intent(self, brain_signals, context):
        """识别用户意图"""
        # 简化实现 - 实际需要机器学习模型
        if np.max(brain_signals) > 0.5:
            return "move_forward"
        elif np.min(brain_signals) < -0.5:
            return "move_backward"
        else:
            return "stop"

class NeuralAdaptationModel:
    def __init__(self):
        self.adaptation_rate = 0.1
        self.baseline_signals = None
        
    def adapt(self, performance, current_signals):
        """神经网络适应性调整"""
        if self.baseline_signals is None:
            self.baseline_signals = current_signals.copy()
        
        # 基于性能调整基线
        adjustment = performance * self.adaptation_rate
        self.baseline_signals += (current_signals - self.baseline_signals) * adjustment

# 高级可视化系统
class AdvancedVisualizationSystem(FigureCanvas):
    def __init__(self, parent=None, width=12, height=10, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        super().__init__(self.fig)
        self.setParent(parent)
        
        # 创建复杂的多子图布局
        self.ax_main = self.fig.add_subplot(2, 3, 1)  # 主模拟视图
        self.ax_swarm = self.fig.add_subplot(2, 3, 2)  # 群体智能可视化
        self.ax_neuro = self.fig.add_subplot(2, 3, 3)  # 神经形态活动
        self.ax_material = self.fig.add_subplot(2, 3, 4)  # 超材料变形
        self.ax_bmi = self.fig.add_subplot(2, 3, 5)  # 脑机接口信号
        self.ax_performance = self.fig.add_subplot(2, 3, 6)  # 性能指标
        
        self.setup_visualizations()
        
    def setup_visualizations(self):
        """设置各个可视化组件"""
        # 主模拟视图
        self.ax_main.set_aspect('equal')
        self.ax_main.grid(True)
        self.ax_main.set_xlabel('X')
        self.ax_main.set_ylabel('Y')
        self.ax_main.set_title('Main Simulation View')
        
        # 群体智能可视化
        self.ax_swarm.set_title('Swarm Intelligence')
        self.ax_swarm.set_xlabel('X')
        self.ax_swarm.set_ylabel('Y')
        
        # 神经形态活动
        self.ax_neuro.set_title('Neuromorphic Activity')
        self.ax_neuro.set_xlabel('Neuron Index')
        self.ax_neuro.set_ylabel('Activation')
        
        # 超材料变形
        self.ax_material.set_title('Metamaterial Deformation')
        self.ax_material.set_xlabel('Grid X')
        self.ax_material.set_ylabel('Grid Y')
        
        # 脑机接口信号
        self.ax_bmi.set_title('Brain-Machine Interface')
        self.ax_bmi.set_xlabel('Time')
        self.ax_bmi.set_ylabel('Signal Amplitude')
        
        # 性能指标
        self.ax_performance.set_title('Performance Metrics')
        self.ax_performance.set_xlabel('Time Step')
        self.ax_performance.set_ylabel('Metric Value')
        
        self.fig.tight_layout()
        
    def update_all_visualizations(self, simulation_data):
        """更新所有可视化"""
        self.ax_main.clear()
        self.ax_swarm.clear()
        self.ax_neuro.clear()
        self.ax_material.clear()
        self.ax_bmi.clear()
        self.ax_performance.clear()
        
        # 更新主模拟视图
        self.update_main_view(simulation_data['main_simulation'])
        
        # 更新群体智能可视化
        self.update_swarm_view(simulation_data['swarm_intelligence'])
        
        # 更新神经形态活动
        self.update_neuromorphic_view(simulation_data['neuromorphic_engine'])
        
        # 更新超材料变形
        self.update_material_view(simulation_data['metamaterial_controller'])
        
        # 更新脑机接口信号
        self.update_bmi_view(simulation_data['brain_machine_interface'])
        
        # 更新性能指标
        self.update_performance_view(simulation_data['performance_metrics'])
        
        self.fig.tight_layout()
        self.draw()
    
    def update_main_view(self, simulation_data):
        """更新主模拟视图"""
        # 绘制机械臂
        model = simulation_data['model']
        angles = simulation_data['joint_angles']
        
        l1, l2 = model.parameters["l1"], model.parameters["l2"]
        theta1, theta2 = angles
        
        x0, y0 = 0, 0
        x1 = l1 * np.cos(theta1)
        y1 = l1 * np.sin(theta1)
        x2 = x1 + l2 * np.cos(theta1 + theta2)
        y2 = y1 + l2 * np.sin(theta1 + theta2)
        
        self.ax_main.plot([x0, x1, x2], [y0, y1, y2], 'o-', lw=3, markersize=10)
        self.ax_main.plot(simulation_data['target_position'][0], 
                         simulation_data['target_position'][1], 
                         'rx', markersize=15, markeredgewidth=3)
        
        self.ax_main.set_xlim(-2, 2)
        self.ax_main.set_ylim(-2, 2)
        self.ax_main.grid(True)
        self.ax_main.set_title('Advanced Machine Simulation')
    
    def update_swarm_view(self, swarm_data):
        """更新群体智能可视化"""
        agents = swarm_data['agents']
        colors = {'explorer': 'blue', 'exploiter': 'green', 'sentinel': 'red'}
        
        for agent in agents:
            color = colors.get(agent['type'], 'black')
            x, y = agent['position']
            self.ax_swarm.scatter(x, y, c=color, alpha=0.7)
            
            # 绘制通信范围
            circle = plt.Circle((x, y), agent['communication_range'], 
                              color=color, alpha=0.1)
            self.ax_swarm.add_patch(circle)
        
        # 绘制全局最佳位置
        if swarm_data['global_best_position'] is not None:
            gx, gy = swarm_data['global_best_position']
            self.ax_swarm.scatter(gx, gy, c='gold', s=200, marker='*', 
                                edgecolors='black')
        
        self.ax_swarm.set_xlim(-2, 2)
        self.ax_swarm.set_ylim(-2, 2)
        self.ax_swarm.grid(True)
        self.ax_swarm.set_title(f'Swarm Intelligence (CI: {swarm_data["collective_intelligence"]:.3f})')
    
    def update_neuromorphic_view(self, neuro_data):
        """更新神经形态活动可视化"""
        spikes = neuro_data['spikes']
        potentials = neuro_data['potentials']
        
        # 显示神经元活动
        neuron_indices = np.arange(len(spikes))
        self.ax_neuro.bar(neuron_indices[spikes], potentials[spikes], 
                         color='red', alpha=0.7, label='Spiking')
        self.ax_neuro.bar(neuron_indices[~spikes], potentials[~spikes], 
                         color='blue', alpha=0.5, label='Silent')
        
        self.ax_neuro.set_xlabel('Neuron Index')
        self.ax_neuro.set_ylabel('Membrane Potential')
        self.ax_neuro.legend()
        self.ax_neuro.set_title('Neuromorphic Network Activity')
    
    def update_material_view(self, material_data):
        """更新超材料变形可视化"""
        # 清除之前的颜色条（如果存在）
        if hasattr(self, 'material_colorbar') and self.material_colorbar is not None:
            try:
                # 检查颜色条是否仍然有效
                if self.material_colorbar.ax is not None:
                    self.material_colorbar.remove()
            except (AttributeError, ValueError):
                # 如果移除过程中出现错误，忽略并继续
                pass
            finally:
                self.material_colorbar = None
        
        self.ax_material.clear()
        
        deformation = material_data['deformation_grid']
        
        # 计算变形幅度
        deformation_magnitude = np.linalg.norm(deformation, axis=2)
        
        # 设置固定的颜色映射范围，避免显示范围自动收缩
        vmin = 0  # 最小值固定为0
        vmax = max(0.1, np.max(deformation_magnitude))  # 最大值至少为0.1，确保可见性
        
        # 显示热图，固定颜色范围
        im = self.ax_material.imshow(deformation_magnitude, cmap='hot', 
                                interpolation='nearest', vmin=vmin, vmax=vmax)
        self.ax_material.set_xlabel('Grid X')
        self.ax_material.set_ylabel('Grid Y')
        
        # 创建颜色条并保存引用
        self.material_colorbar = self.fig.colorbar(im, ax=self.ax_material)
        self.ax_material.set_title('Metamaterial Deformation Field')
        
    def update_bmi_view(self, bmi_data):
        """更新脑机接口信号可视化"""
        signals = bmi_data['brain_signals']
        time_points = np.arange(len(signals))
        
        self.ax_bmi.plot(time_points, signals, 'b-', alpha=0.7)
        self.ax_bmi.set_xlabel('Time Sample')
        self.ax_bmi.set_ylabel('Signal Amplitude')
        self.ax_bmi.grid(True)
        self.ax_bmi.set_title(f'BMI Signals (Attention: {bmi_data["attention_level"]:.2f})')
    
    def update_performance_view(self, performance_data):
        """更新性能指标可视化"""
        metrics = performance_data['history']
        if len(metrics) > 0:
            time_steps = np.arange(len(metrics))
            
            for metric_name in metrics[0].keys():
                values = [m[metric_name] for m in metrics]
                self.ax_performance.plot(time_steps, values, label=metric_name)
            
            self.ax_performance.set_xlabel('Time Step')
            self.ax_performance.set_ylabel('Metric Value')
            self.ax_performance.legend()
            self.ax_performance.grid(True)
            self.ax_performance.set_title('Performance Metrics Over Time')

# 主应用程序
class RevolutionaryMachineSimulationApp(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # 初始化颠覆性技术组件
        self.neuromorphic_engine = NeuromorphicEngine(num_neurons=500)
        self.swarm_controller = SwarmIntelligenceController(num_agents=30)
        self.metamaterial_controller = MetamaterialController(grid_size=15)
        self.brain_machine_interface = BrainMachineInterface()
        
        self.init_ui()
        self.init_simulation()
        self.init_performance_tracking()
        
    def init_ui(self):
        self.setWindowTitle("Revolutionary Machine Motion Simulation System")
        self.setGeometry(100, 100, 2000, 1400)
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QHBoxLayout()
        
        # 左侧控制面板
        control_panel = self.create_control_panel()
        main_layout.addWidget(control_panel, 1)
        
        # 右侧可视化区域
        viz_splitter = QSplitter(Qt.Vertical)
        
        # 高级可视化系统
        self.advanced_viz = AdvancedVisualizationSystem()
        viz_splitter.addWidget(self.advanced_viz)
        
        # 数据监控面板
        self.monitor_panel = self.create_monitor_panel()
        viz_splitter.addWidget(self.monitor_panel)
        
        viz_splitter.setSizes([1000, 400])
        main_layout.addWidget(viz_splitter, 3)
        
        central_widget.setLayout(main_layout)
        
        # 状态栏
        self.statusBar().showMessage("Revolutionary Simulation System Ready")
        
        # 仿真定时器
        self.sim_timer = QTimer()
        self.sim_timer.timeout.connect(self.update_simulation)
        self.sim_dt = 0.05
        self.sim_time = 0
        
    def create_control_panel(self):
        """创建革命性控制面板"""
        panel = QWidget()
        layout = QVBoxLayout()
        
        # 神经形态计算控制组
        neuro_group = QGroupBox("Neuromorphic Computing")
        neuro_layout = QVBoxLayout()
        
        self.neuro_enable = QCheckBox("Enable Neuromorphic Engine")
        self.neuro_enable.setChecked(True)
        neuro_layout.addWidget(self.neuro_enable)
        
        neuron_layout = QHBoxLayout()
        neuron_layout.addWidget(QLabel("Number of Neurons:"))
        self.neuron_spin = QSpinBox()
        self.neuron_spin.setRange(100, 5000)
        self.neuron_spin.setValue(500)
        neuron_layout.addWidget(self.neuron_spin)
        neuro_layout.addLayout(neuron_layout)
        
        neuro_group.setLayout(neuro_layout)
        layout.addWidget(neuro_group)
        
        # 群体智能控制组
        swarm_group = QGroupBox("Swarm Intelligence")
        swarm_layout = QVBoxLayout()
        
        self.swarm_enable = QCheckBox("Enable Swarm Intelligence")
        self.swarm_enable.setChecked(True)
        swarm_layout.addWidget(self.swarm_enable)
        
        agent_layout = QHBoxLayout()
        agent_layout.addWidget(QLabel("Number of Agents:"))
        self.agent_spin = QSpinBox()
        self.agent_spin.setRange(5, 100)
        self.agent_spin.setValue(30)
        agent_layout.addWidget(self.agent_spin)
        swarm_layout.addLayout(agent_layout)
        
        swarm_group.setLayout(swarm_layout)
        layout.addWidget(swarm_group)
        
        # 超材料控制组
        material_group = QGroupBox("Metamaterial Control")
        material_layout = QVBoxLayout()
        
        self.material_enable = QCheckBox("Enable Metamaterial Adaptation")
        self.material_enable.setChecked(True)
        material_layout.addWidget(self.material_enable)
        
        grid_layout = QHBoxLayout()
        grid_layout.addWidget(QLabel("Grid Size:"))
        self.grid_spin = QSpinBox()
        self.grid_spin.setRange(5, 50)
        self.grid_spin.setValue(15)
        grid_layout.addWidget(self.grid_spin)
        material_layout.addLayout(grid_layout)
        
        material_group.setLayout(material_layout)
        layout.addWidget(material_group)
        
        # 脑机接口控制组
        bmi_group = QGroupBox("Brain-Machine Interface")
        bmi_layout = QVBoxLayout()
        
        self.bmi_enable = QCheckBox("Enable BMI Control")
        self.bmi_enable.setChecked(True)
        bmi_layout.addWidget(self.bmi_enable)
        
        # 心理命令按钮
        command_group = QGroupBox("Mental Commands")
        command_layout = QHBoxLayout()
        
        self.forward_btn = QPushButton("Move Forward")
        self.forward_btn.clicked.connect(lambda: self.set_mental_command('move_forward'))
        command_layout.addWidget(self.forward_btn)
        
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.clicked.connect(lambda: self.set_mental_command('stop'))
        command_layout.addWidget(self.stop_btn)
        
        command_group.setLayout(command_layout)
        bmi_layout.addWidget(command_group)
        
        bmi_group.setLayout(bmi_layout)
        layout.addWidget(bmi_group)
        
        # 仿真控制组
        sim_group = QGroupBox("Simulation Control")
        sim_layout = QVBoxLayout()
        
        self.start_btn = QPushButton("Start Simulation")
        self.start_btn.clicked.connect(self.start_simulation)
        sim_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("Stop Simulation")
        self.stop_btn.clicked.connect(self.stop_simulation)
        sim_layout.addWidget(self.stop_btn)
        
        self.reset_btn = QPushButton("Reset Simulation")
        self.reset_btn.clicked.connect(self.reset_simulation)
        sim_layout.addWidget(self.reset_btn)
        
        # 目标控制
        target_layout = QHBoxLayout()
        target_layout.addWidget(QLabel("Target X:"))
        self.target_x_spin = QDoubleSpinBox()
        self.target_x_spin.setRange(-2.0, 2.0)
        self.target_x_spin.setValue(1.2)
        self.target_x_spin.setSingleStep(0.1)
        target_layout.addWidget(self.target_x_spin)
        
        target_layout.addWidget(QLabel("Y:"))
        self.target_y_spin = QDoubleSpinBox()
        self.target_y_spin.setRange(-2.0, 2.0)
        self.target_y_spin.setValue(0.5)
        self.target_y_spin.setSingleStep(0.1)
        target_layout.addWidget(self.target_y_spin)
        
        self.set_target_btn = QPushButton("Set Target")
        self.set_target_btn.clicked.connect(self.set_target_position)
        target_layout.addWidget(self.set_target_btn)
        
        sim_layout.addLayout(target_layout)
        sim_group.setLayout(sim_layout)
        layout.addWidget(sim_group)
        
        # 高级实验组
        experiment_group = QGroupBox("Advanced Experiments")
        experiment_layout = QVBoxLayout()
        
        self.emergence_test_btn = QPushButton("Test Emergent Behavior")
        self.emergence_test_btn.clicked.connect(self.test_emergent_behavior)
        experiment_layout.addWidget(self.emergence_test_btn)
        
        self.phase_transition_btn = QPushButton("Induce Phase Transition")
        self.phase_transition_btn.clicked.connect(self.induce_phase_transition)
        experiment_layout.addWidget(self.phase_transition_btn)
        
        self.adaptive_learning_btn = QPushButton("Start Adaptive Learning")
        self.adaptive_learning_btn.clicked.connect(self.start_adaptive_learning)
        experiment_layout.addWidget(self.adaptive_learning_btn)
        
        experiment_group.setLayout(experiment_layout)
        layout.addWidget(experiment_group)
        
        layout.addStretch()
        panel.setLayout(layout)
        
        return panel
        
    def create_monitor_panel(self):
        """创建监控面板"""
        panel = QWidget()
        layout = QVBoxLayout()
        
        # 选项卡 widget
        self.monitor_tabs = QTabWidget()
        
        # 性能指标标签页
        self.metrics_tab = QWidget()
        metrics_layout = QVBoxLayout()
        self.metrics_table = QTableWidget()
        self.metrics_table.setColumnCount(3)
        self.metrics_table.setHorizontalHeaderLabels(["Metric", "Value", "Trend"])
        metrics_layout.addWidget(self.metrics_table)
        self.metrics_tab.setLayout(metrics_layout)
        self.monitor_tabs.addTab(self.metrics_tab, "Performance Metrics")
        
        # 系统状态标签页
        self.status_tab = QWidget()
        status_layout = QVBoxLayout()
        self.status_tree = QTreeWidget()
        self.status_tree.setHeaderLabels(["Component", "Status", "Details"])
        status_layout.addWidget(self.status_tree)
        self.status_tab.setLayout(status_layout)
        self.monitor_tabs.addTab(self.status_tab, "System Status")
        
        # 数据记录标签页
        self.data_tab = QWidget()
        data_layout = QVBoxLayout()
        self.data_log = QTextEdit()
        self.data_log.setReadOnly(True)
        data_layout.addWidget(self.data_log)
        
        data_control_layout = QHBoxLayout()
        self.save_data_btn = QPushButton("Save Data")
        self.save_data_btn.clicked.connect(self.save_simulation_data)
        data_control_layout.addWidget(self.save_data_btn)
        
        self.load_data_btn = QPushButton("Load Data")
        self.load_data_btn.clicked.connect(self.load_simulation_data)
        data_control_layout.addWidget(self.load_data_btn)
        
        data_layout.addLayout(data_control_layout)
        self.data_tab.setLayout(data_layout)
        self.monitor_tabs.addTab(self.data_tab, "Data Logging")
        
        layout.addWidget(self.monitor_tabs)
        panel.setLayout(layout)
        
        return panel
        
    def init_simulation(self):
        """初始化仿真系统"""
        # 创建二连杆机械臂模型
        
        self.model = TwoLinkArm()
        self.simulator = {
            'model': self.model,
            'joint_angles': np.zeros(2),
            'target_position': np.array([1.2, 0.5]),
            'trajectory': None,
            'trajectory_index': 0
        }
        
        # 初始化心理命令
        self.current_mental_command = "stop"
        
    def init_performance_tracking(self):
        """初始化性能跟踪"""
        self.performance_history = []
        self.performance_metrics = {
            'position_error': 0.0,
            'swarm_intelligence': 0.0,
            'neuromorphic_activity': 0.0,
            'material_adaptation': 0.0,
            'bmi_efficiency': 0.0,
            'overall_performance': 0.0
        }
        
    def set_mental_command(self, command):
        """设置心理命令"""
        self.current_mental_command = command
        self.statusBar().showMessage(f"Mental command set: {command}")
        
    def set_target_position(self):
        """设置目标位置"""
        x = self.target_x_spin.value()
        y = self.target_y_spin.value()
        self.simulator['target_position'] = np.array([x, y])
        
    def start_simulation(self):
        """开始仿真"""
        self.sim_timer.start(int(self.sim_dt * 1000))
        self.statusBar().showMessage("Simulation Running")
        
    def stop_simulation(self):
        """停止仿真"""
        self.sim_timer.stop()
        self.statusBar().showMessage("Simulation Stopped")
        
    def reset_simulation(self):
        """重置仿真"""
        self.simulator['joint_angles'] = np.zeros(2)
        self.simulator['target_position'] = np.random.uniform(-1.5, 1.5, 2)
        self.sim_time = 0
        self.performance_history = []
        
        # 重置技术组件
        self.neuromorphic_engine = NeuromorphicEngine(num_neurons=self.neuron_spin.value())
        self.swarm_controller = SwarmIntelligenceController(num_agents=self.agent_spin.value())
        self.metamaterial_controller = MetamaterialController(grid_size=self.grid_spin.value())
        
        self.statusBar().showMessage("Simulation Reset")
        
    def test_emergent_behavior(self):
        """测试涌现行为"""
        # 提高涌现阈值以促进行为出现
        self.swarm_controller.emergence_threshold = 0.5
        self.statusBar().showMessage("Testing emergent behavior - threshold lowered")
        
    def induce_phase_transition(self):
        """诱导超材料相变"""
        # 施加外部刺激
        stimulus = np.random.uniform(0, 1, (15, 15)) * 1.5  # 高强度刺激
        self.metamaterial_controller.phase_transition(stimulus)
        self.statusBar().showMessage("Phase transition induced in metamaterial")
        
    def start_adaptive_learning(self):
        """开始自适应学习"""
        # 提高神经形态引擎的学习率
        self.neuromorphic_engine.plasticity_rules['stdp'] = lambda pre, post, dt: self.neuromorphic_engine.stdp_rule(pre, post, dt*2)
        self.statusBar().showMessage("Adaptive learning activated")
        
    def update_simulation(self):
        """更新仿真"""
        self.sim_time += self.sim_dt
        
        # 1. 处理脑机接口输入
        if self.bmi_enable.isChecked():
            # 模拟视觉输入（当前位置与目标的差异）
            visual_input = self.simulator['target_position'] - self.model.forward_kinematics(
                self.simulator['joint_angles'])
            
            # 模拟大脑活动
            task_difficulty = 0.5  # 中等难度
            brain_signals = self.brain_machine_interface.simulate_brain_activity(
                visual_input, task_difficulty)
            
            # 解码心理命令
            control_signal = self.brain_machine_interface.decode_mental_command(
                self.current_mental_command)
            
            # 应用控制信号
            self.simulator['joint_angles'] += control_signal * 0.1
        
        # 2. 更新神经形态引擎
        if self.neuro_enable.isChecked():
            # 准备输入（位置误差和目标信息）
            current_pos = self.model.forward_kinematics(self.simulator['joint_angles'])
            error = self.simulator['target_position'] - current_pos
            neuromorphic_input = np.concatenate([error, self.simulator['target_position']])
            
            # 更新神经形态网络
            spikes, potentials = self.neuromorphic_engine.update(neuromorphic_input, self.sim_dt)
            
            # 使用神经形态输出调整控制（简化）
            if np.any(spikes):
                neural_control = np.mean(potentials[spikes]) * 0.01
                self.simulator['joint_angles'] += neural_control
        
        # 3. 更新群体智能
        if self.swarm_enable.isChecked():
            best_position, best_fitness = self.swarm_controller.update_swarm(
                self.simulator['target_position'])
            
            # 使用群体智能结果（简化）
            if best_fitness > 0.5:  # 群体找到好位置
                direction = best_position - current_pos
                direction = direction / (np.linalg.norm(direction) + 1e-8)
                self.simulator['joint_angles'] += direction * 0.05
        
        # 4. 更新超材料控制
        if self.material_enable.isChecked():
            # 模拟应力场（基于位置误差）
            stress_field = np.zeros((15, 15, 2))
            error_magnitude = np.linalg.norm(
                self.simulator['target_position'] - current_pos)
            
            # 创建与误差相关的应力模式
            for i in range(15):
                for j in range(15):
                    stress_field[i, j] = [error_magnitude * 0.01 * (i-7), 
                                         error_magnitude * 0.01 * (j-7)]
            
            self.metamaterial_controller.apply_mechanical_stress(stress_field)
            
            # 基于性能反馈自适应调整
            performance_feedback = 1.0 / (1.0 + error_magnitude)  # 误差越小性能越好
            self.metamaterial_controller.adaptive_redistribution(performance_feedback)
        
        # 5. 限制关节角度
        self.simulator['joint_angles'] = np.clip(
            self.simulator['joint_angles'], -np.pi, np.pi)
        
        # 6. 更新性能指标
        self.update_performance_metrics()
        
        # 7. 准备可视化数据
        viz_data = {
            'main_simulation': {
                'model': self.model,
                'joint_angles': self.simulator['joint_angles'],
                'target_position': self.simulator['target_position']
            },
            'swarm_intelligence': {
                'agents': self.swarm_controller.agents,
                'global_best_position': self.swarm_controller.global_best_position,
                'collective_intelligence': self.swarm_controller.collective_intelligence
            },
            'neuromorphic_engine': {
                'spikes': spikes if self.neuro_enable.isChecked() else np.zeros(500, dtype=bool),
                'potentials': potentials if self.neuro_enable.isChecked() else np.zeros(500)
            },
            'metamaterial_controller': {
                'deformation_grid': self.metamaterial_controller.deformation_grid
            },
            'brain_machine_interface': {
                'brain_signals': self.brain_machine_interface.brain_signals,
                'attention_level': self.brain_machine_interface.attention_level
            },
            'performance_metrics': {
                'history': self.performance_history
            }
        }
        
        # 8. 更新可视化
        self.advanced_viz.update_all_visualizations(viz_data)
        
        # 9. 更新监控面板
        self.update_monitor_panel()
        
    def update_performance_metrics(self):
        """更新性能指标"""
        current_pos = self.model.forward_kinematics(self.simulator['joint_angles'])
        error = np.linalg.norm(self.simulator['target_position'] - current_pos)
        
        self.performance_metrics['position_error'] = error
        self.performance_metrics['swarm_intelligence'] = self.swarm_controller.collective_intelligence
        self.performance_metrics['neuromorphic_activity'] = np.mean(
            self.neuromorphic_engine.neurons) if self.neuro_enable.isChecked() else 0
        self.performance_metrics['material_adaptation'] = np.mean(
            np.linalg.norm(self.metamaterial_controller.deformation_grid, axis=2))
        self.performance_metrics['bmi_efficiency'] = self.brain_machine_interface.attention_level
        
        # 综合性能指标
        self.performance_metrics['overall_performance'] = (
            0.3 * (1.0 / (1.0 + error)) +  # 位置精度
            0.2 * self.performance_metrics['swarm_intelligence'] +  # 群体智能
            0.2 * self.performance_metrics['neuromorphic_activity'] +  # 神经形态活动
            0.15 * (1.0 / (1.0 + self.performance_metrics['material_adaptation'])) +  # 材料适应性
            0.15 * self.performance_metrics['bmi_efficiency'] ) # BMI效率
        
        # 记录历史
        self.performance_history.append(self.performance_metrics.copy())
        
        # 保持历史长度
        if len(self.performance_history) > 1000:
            self.performance_history.pop(0)
    
    def update_monitor_panel(self):
        """更新监控面板"""
        # 更新性能指标表
        self.metrics_table.setRowCount(len(self.performance_metrics))
        
        for i, (metric, value) in enumerate(self.performance_metrics.items()):
            self.metrics_table.setItem(i, 0, QTableWidgetItem(metric.replace('_', ' ').title()))
            self.metrics_table.setItem(i, 1, QTableWidgetItem(f"{value:.4f}"))
            
            # 趋势指示（简化）
            if len(self.performance_history) > 1:
                prev_value = self.performance_history[-2].get(metric, value)
                trend = "↑" if value > prev_value else "↓" if value < prev_value else "→"
                self.metrics_table.setItem(i, 2, QTableWidgetItem(trend))
        
        # 更新系统状态树
        self.update_status_tree()
        
        # 更新数据日志
        self.update_data_log()
    
    def update_status_tree(self):
        """更新系统状态树"""
        self.status_tree.clear()
        
        # 神经形态计算状态
        neuro_item = QTreeWidgetItem(["Neuromorphic Computing", 
                                    "Active" if self.neuro_enable.isChecked() else "Inactive",
                                    f"Neurons: {self.neuromorphic_engine.num_neurons}"])
        self.status_tree.addTopLevelItem(neuro_item)
        
        # 群体智能状态
        swarm_item = QTreeWidgetItem(["Swarm Intelligence", 
                                    "Active" if self.swarm_enable.isChecked() else "Inactive",
                                    f"Agents: {self.swarm_controller.num_agents}, CI: {self.swarm_controller.collective_intelligence:.3f}"])
        self.status_tree.addTopLevelItem(swarm_item)
        
        # 超材料控制状态
        material_item = QTreeWidgetItem(["Metamaterial Control", 
                                       "Active" if self.material_enable.isChecked() else "Inactive",
                                       f"Grid: {self.metamaterial_controller.grid_size}x{self.metamaterial_controller.grid_size}"])
        self.status_tree.addTopLevelItem(material_item)
        
        # 脑机接口状态
        bmi_item = QTreeWidgetItem(["Brain-Machine Interface", 
                                  "Active" if self.bmi_enable.isChecked() else "Inactive",
                                  f"Attention: {self.brain_machine_interface.attention_level:.2f}"])
        self.status_tree.addTopLevelItem(bmi_item)
        
        # 性能状态
        performance_item = QTreeWidgetItem(["Overall Performance", 
                                          "Good" if self.performance_metrics['overall_performance'] > 0.7 else "Fair" if self.performance_metrics['overall_performance'] > 0.4 else "Poor",
                                          f"Score: {self.performance_metrics['overall_performance']:.3f}"])
        self.status_tree.addTopLevelItem(performance_item)
    
    def update_data_log(self):
        """更新数据日志"""
        if len(self.performance_history) % 10 == 0:  # 每10步更新一次
            current_time = datetime.now().strftime("%H:%M:%S")
            log_entry = f"[{current_time}] Step {len(self.performance_history)}: "
            log_entry += f"Perf: {self.performance_metrics['overall_performance']:.3f}, "
            log_entry += f"Error: {self.performance_metrics['position_error']:.3f}, "
            log_entry += f"Swarm CI: {self.performance_metrics['swarm_intelligence']:.3f}\n"
            
            self.data_log.append(log_entry)
            
            # 限制日志长度
            if self.data_log.document().lineCount() > 100:
                cursor = self.data_log.textCursor()
                cursor.movePosition(cursor.Start)
                cursor.select(cursor.LineUnderCursor)
                cursor.removeSelectedText()
    
    def save_simulation_data(self):
        """保存仿真数据"""
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Simulation Data", "", "ZIP Files (*.zip)")
        
        if filename:
            # 创建临时目录保存数据
            temp_dir = "temp_sim_data"
            os.makedirs(temp_dir, exist_ok=True)
            
            # 保存性能历史
            with open(f"{temp_dir}/performance.json", 'w') as f:
                json.dump(self.performance_history, f, indent=2)
            
            # 保存系统状态
            system_state = {
                'simulation_time': self.sim_time,
                'joint_angles': self.simulator['joint_angles'].tolist(),
                'target_position': self.simulator['target_position'].tolist(),
                'performance_metrics': self.performance_metrics
            }
            
            with open(f"{temp_dir}/system_state.json", 'w') as f:
                json.dump(system_state, f, indent=2)
            
            # 创建ZIP文件
            with zipfile.ZipFile(filename, 'w') as zipf:
                for root, dirs, files in os.walk(temp_dir):
                    for file in files:
                        zipf.write(os.path.join(root, file), 
                                 os.path.relpath(os.path.join(root, file), temp_dir))
            
            # 清理临时文件
            for file in os.listdir(temp_dir):
                os.remove(os.path.join(temp_dir, file))
            os.rmdir(temp_dir)
            
            self.statusBar().showMessage(f"Simulation data saved to {filename}")
    
    def load_simulation_data(self):
        """加载仿真数据"""
        filename, _ = QFileDialog.getOpenFileName(
            self, "Load Simulation Data", "", "ZIP Files (*.zip)")
        
        if filename:
            # 创建临时目录解压数据
            temp_dir = "temp_sim_data"
            os.makedirs(temp_dir, exist_ok=True)
            
            # 解压ZIP文件
            with zipfile.ZipFile(filename, 'r') as zipf:
                zipf.extractall(temp_dir)
            
            # 加载性能历史
            try:
                with open(f"{temp_dir}/performance.json", 'r') as f:
                    self.performance_history = json.load(f)
            except FileNotFoundError:
                self.performance_history = []
            
            # 加载系统状态
            try:
                with open(f"{temp_dir}/system_state.json", 'r') as f:
                    system_state = json.load(f)
                    self.sim_time = system_state.get('simulation_time', 0)
                    self.simulator['joint_angles'] = np.array(system_state.get('joint_angles', [0, 0]))
                    self.simulator['target_position'] = np.array(system_state.get('target_position', [1.2, 0.5]))
                    self.performance_metrics = system_state.get('performance_metrics', {})
            except FileNotFoundError:
                pass
            
            # 清理临时文件
            for file in os.listdir(temp_dir):
                os.remove(os.path.join(temp_dir, file))
            os.rmdir(temp_dir)
            
            self.statusBar().showMessage(f"Simulation data loaded from {filename}")

# 运行应用程序
if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # 设置现代UI样式
    app.setStyle('Fusion')
    
    # 创建暗色主题调色板
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(40, 40, 40))
    palette.setColor(QPalette.WindowText, Qt.white)
    palette.setColor(QPalette.Base, QColor(25, 25, 25))
    palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
    palette.setColor(QPalette.ToolTipBase, Qt.white)
    palette.setColor(QPalette.ToolTipText, Qt.white)
    palette.setColor(QPalette.Text, Qt.white)
    palette.setColor(QPalette.Button, QColor(53, 53, 53))
    palette.setColor(QPalette.ButtonText, Qt.white)
    palette.setColor(QPalette.BrightText, Qt.red)
    palette.setColor(QPalette.Link, QColor(42, 130, 218))
    palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.HighlightedText, Qt.black)
    app.setPalette(palette)
    
    window = RevolutionaryMachineSimulationApp()
    window.show()
    
    sys.exit(app.exec_())