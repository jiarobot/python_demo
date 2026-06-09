import sys
import os
import json
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torch.utils.tensorboard import SummaryWriter
import torch_geometric
from torch_geometric.data import Data
from torch_geometric.nn import GATConv, global_add_pool
import random
from collections import deque, defaultdict
import networkx as nx
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas, NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from matplotlib import pyplot as plt
from sklearn.cluster import KMeans
from sklearn.manifold import TSNE
from scipy.spatial.distance import cdist
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QPushButton,
QLabel, QSlider, QComboBox, QGroupBox, QTextEdit, QTabWidget, QSplitter,
QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit, QCheckBox, QFileDialog,
QListWidget, QListWidgetItem, QProgressBar, QSpinBox, QDoubleSpinBox, QMessageBox,
QInputDialog)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QSettings
from PyQt5.QtGui import QFont, QColor, QIcon, QPixmap
import datetime
from dateutil.relativedelta import relativedelta
import pandas as pd
import seaborn as sns
from scipy.stats import linregress
import matplotlib
matplotlib.rc("font", family='Microsoft YaHei')
# ====================== 环境设置 ======================
TECH_FEATURE_SIZE = 16
MAX_TECH_LEVEL = 7
INIT_TECH_POOL = 8
MUTATION_RATE = 0.15
FUSION_RATE = 0.1
SYNERGY_BONUS = 1.8
DECAY_RATE = 0.06
INNOVATION_THRESHOLD = 0.85
REVOLUTION_PROB = 0.03
DIFFUSION_RATE = 0.1
TECH_NAME_PARTS = {
    'Physics': ['Quantum', 'Relativity', 'Particle', 'Field', 'String'],
    'Chemistry': ['Organic', 'Inorganic', 'Biochemistry', 'Catalysis', 'Polymer'],
    'Biology': ['Genomic', 'Proteomic', 'Cell', 'Molecular', 'Evolutionary'],
    'Mathematics': ['Topological', 'Algebraic', 'Analytic', 'Probabilistic', 'Computational'],
    'Computing': ['Quantum', 'Neural', 'Distributed', 'Secure', 'Bio-inspired']
}

# ====================== 强化学习模型 ======================
class TechNode:
    __slots__ = ['id', 'features', 'level', 'parents', 'children', 'age', 'last_updated', 'domain', 'name', 'created_at']
    
    def __init__(self, node_id, features, level=1, parents=None, domain=None, name=None):
        self.id = node_id
        self.features = features
        self.level = level
        self.parents = parents if parents is not None else []
        self.children = []
        self.age = 0
        self.last_updated = 0
        self.domain = domain if domain is not None else np.argmax(features[:5])
        self.name = name if name else self.generate_tech_name(domain)
        self.created_at = datetime.datetime.now()
        
    def generate_tech_name(self, domain):
        """生成有意义的科技名称"""
        if domain in TECH_NAME_PARTS:
            prefix = random.choice(TECH_NAME_PARTS[domain])
            suffix = random.choice(['Theory', 'System', 'Technology', 'Framework', 'Model'])
            return f"{prefix} {suffix}"
        return f"Tech-{self.id}"
    
    def __repr__(self):
        return f"{self.name} (Lv.{self.level}, {self.domain})"

class TechTreeEnv:
    def __init__(self):
        self.tech_pool = []  
        self.tech_graph = nx.DiGraph()
        self.current_step = 0
        self.max_steps = 500
        self.node_counter = 0
        self.domain_centers = {}
        self.domain_counter = defaultdict(int)
        self.innovation_pressure = 0.0
        self.domain_names = {}
        self.history = []
        self.reward_history = []
        self.reset()
        
    def reset(self):
        self.tech_pool = []
        self.tech_graph = nx.DiGraph()
        self.current_step = 0
        self.node_counter = 0
        self.domain_centers = {}
        self.domain_counter = defaultdict(int)
        self.innovation_pressure = 0.0
        self.domain_names = {}
        self.history = []
        self.reward_history = []
        
        # 创建初始科技 - 基础学科
        base_domains = ['Physics', 'Chemistry', 'Biology', 'Mathematics', 'Computing']
        for i, domain in enumerate(base_domains):
            self.domain_names[i] = domain
        
        for i in range(INIT_TECH_POOL):
            domain_idx = i % len(base_domains)
            domain = self.domain_names[domain_idx]
            features = np.zeros(TECH_FEATURE_SIZE)
            features[domain_idx] = 1.0
            features[5:] = np.random.uniform(-0.5, 0.5, TECH_FEATURE_SIZE-5)
            
            tech = TechNode(
                node_id=self.node_counter,
                features=features,
                domain=domain
            )
            self._add_tech(tech)
            self.domain_counter[domain] += 1
            self._update_domain_center(domain, tech.features)
        
        # 记录初始状态
        self._record_history()
        return self._get_state()
    
    def _calculate_synergy(self, tech_id):
        if len(self.tech_pool) < 2:
            return 0.0
            
        target_tech = next(t for t in self.tech_pool if t.id == tech_id)
        synergy = 0.0
        for tech in self.tech_pool:
            if tech.id == target_tech.id:
                continue
            feature_sim = np.dot(target_tech.features, tech.features) / (
                np.linalg.norm(target_tech.features) * np.linalg.norm(tech.features) + 1e-8)
            domain_sim = 1.0 if target_tech.domain == tech.domain else 0.3
            synergy += max(0, feature_sim) * domain_sim * tech.level
        return min(10.0, synergy / 10)
    
    def _apply_mutation(self):
        domain = random.choice(list(self.domain_centers.keys()))
        domain_techs = [t for t in self.tech_pool if t.domain == domain]
        if not domain_techs:
            return 0
        parent = random.choice(domain_techs)
        
        mutation = np.random.normal(0, MUTATION_RATE, TECH_FEATURE_SIZE)
        child_features = parent.features + 0.7 * mutation + 0.3 * (
            self.domain_centers[domain] - parent.features)
        child_features = np.clip(child_features, -1, 1)
        
        child = TechNode(
            node_id=self.node_counter,
            features=child_features,
            parents=[parent.id],
            domain=domain,
            name=f"{domain[:3]}-M{self.node_counter}"
        )
        
        self._add_tech(child)
        self.domain_counter[domain] += 1
        self._update_domain_center(domain, child.features)
        
        synergy = self._calculate_synergy(child.id)
        return synergy * 2
    
    def _apply_fusion(self):
        """应用技术融合 - 合并两个现有技术"""
        if len(self.tech_pool) < 2:
            return 0
            
        # 随机选择两个不同的技术
        tech1, tech2 = random.sample(self.tech_pool, 2)
        
        # 创建融合特征 - 加权平均
        features = (tech1.features + tech2.features) / 2
        # 添加随机扰动
        features += np.random.normal(0, FUSION_RATE, features.shape)
        features = np.clip(features, -1, 1)
        
        # 确定领域
        domain_idx = np.argmax(features[:5])
        domain = self.domain_names[domain_idx]
        
        # 创建新技术 - 等级基于两个技术的平均值
        avg_level = (tech1.level + tech2.level) / 2
        tech = TechNode(
            node_id=self.node_counter,
            features=features,
            level=int(avg_level),
            parents=[tech1.id, tech2.id],
            domain=domain
        )
        
        # 添加到技术树
        self._add_tech(tech)
        self.domain_counter[domain] += 1
        self._update_domain_center(domain, tech.features)
        
        # 更新父节点
        tech1.children.append(tech.id)
        tech2.children.append(tech.id)
        
        # 奖励基于新技术的等级和协同效应
        synergy = SYNERGY_BONUS if domain == tech1.domain == tech2.domain else 1.0
        return tech.level * synergy

    def _apply_development(self, tech_index):
        """应用技术开发 - 提升现有技术等级"""
        if tech_index < 0 or tech_index >= len(self.tech_pool):
            return 0
            
        tech = self.tech_pool[tech_index]
        
        # 检查是否可以升级
        if tech.level < MAX_TECH_LEVEL:
            tech.level += 1
            tech.last_updated = self.current_step
            # 奖励基于提升的等级
            return tech.level * 0.8
        return 0

    def _apply_domain_innovation(self):
        """应用领域创新 - 创建新领域的技术"""
        if not self.tech_pool:
            return 0
            
        # 随机选择一个技术
        base_tech = random.choice(self.tech_pool)
        
        # 创建新领域特征 - 显著改变特征向量
        features = base_tech.features.copy()
        # 在主要特征上添加大扰动
        features[:5] += np.random.uniform(-0.5, 0.5, 5)
        features[5:] += np.random.normal(0, 0.4, TECH_FEATURE_SIZE-5)
        features = np.clip(features, -1, 1)
        
        # 确定新领域
        domain_idx = np.argmax(features[:5])
        if domain_idx not in self.domain_names:
            # 创建新领域
            domain = f"NewDomain{len(self.domain_names)}"
            self.domain_names[domain_idx] = domain
            self.domain_counter[domain] = 0
        else:
            domain = self.domain_names[domain_idx]
        
        # 创建新技术
        tech = TechNode(
            node_id=self.node_counter,
            features=features,
            level=max(1, base_tech.level - 1),
            parents=[base_tech.id],
            domain=domain
        )
        
        # 添加到技术树
        self._add_tech(tech)
        self.domain_counter[domain] += 1
        self._update_domain_center(domain, tech.features)
        
        # 更新父节点
        base_tech.children.append(tech.id)
        
        # 高奖励用于领域创新
        return tech.level * 2.0

    def _apply_cross_domain_fusion(self):
        """应用跨领域融合 - 合并来自不同领域的技术"""
        # 按领域分组技术
        domain_techs = defaultdict(list)
        for tech in self.tech_pool:
            domain_techs[tech.domain].append(tech)
        
        # 确保至少有两个不同领域
        if len(domain_techs) < 2:
            return 0
            
        # 随机选择两个不同领域
        domain1, domain2 = random.sample(list(domain_techs.keys()), 2)
        
        # 从每个领域选择一个技术
        tech1 = random.choice(domain_techs[domain1])
        tech2 = random.choice(domain_techs[domain2])
        
        # 创建融合特征 - 加权平均
        features = (tech1.features + tech2.features) / 2
        # 添加随机扰动
        features += np.random.normal(0, FUSION_RATE * 2, features.shape)
        features = np.clip(features, -1, 1)
        
        # 确定新领域 - 可能是混合领域
        domain_idx = np.argmax(features[:5])
        if domain_idx not in self.domain_names:
            domain = f"Hybrid-{domain1[:3]}-{domain2[:3]}"
            self.domain_names[domain_idx] = domain
            self.domain_counter[domain] = 0
        else:
            domain = self.domain_names[domain_idx]
        
        # 创建新技术
        avg_level = (tech1.level + tech2.level) / 2
        tech = TechNode(
            node_id=self.node_counter,
            features=features,
            level=int(avg_level),
            parents=[tech1.id, tech2.id],
            domain=domain
        )
        
        # 添加到技术树
        self._add_tech(tech)
        self.domain_counter[domain] += 1
        self._update_domain_center(domain, tech.features)
        
        # 更新父节点
        tech1.children.append(tech.id)
        tech2.children.append(tech.id)
        
        # 高奖励用于跨领域创新
        return tech.level * 3.0

    def _add_tech(self, tech):
        # 确保节点在添加到tech_pool前已加入图中
        self.tech_graph.add_node(tech.id, 
                                features=tech.features, 
                                level=tech.level, 
                                domain=tech.domain,
                                name=tech.name)
        
        self.tech_pool.append(tech)
        
        # 添加边
        for parent_id in tech.parents:
            if parent_id < self.node_counter:
                # 确保父节点存在
                if parent_id not in self.tech_graph:
                    parent_tech = next((t for t in self.tech_pool if t.id == parent_id), None)
                    if parent_tech:
                        self.tech_graph.add_node(parent_id, 
                                            features=parent_tech.features, 
                                            level=parent_tech.level, 
                                            domain=parent_tech.domain,
                                            name=parent_tech.name)
                
                # 添加边
                if parent_id in self.tech_graph and tech.id in self.tech_graph:
                    self.tech_graph.add_edge(parent_id, tech.id)
                    parent_tech = next((t for t in self.tech_pool if t.id == parent_id), None)
                    if parent_tech and tech.id not in parent_tech.children:
                        parent_tech.children.append(tech.id)
        
        self.node_counter += 1
    
    def _update_domain_center(self, domain, features):
        if domain not in self.domain_centers:
            self.domain_centers[domain] = features.copy()
        else:
            self.domain_centers[domain] = 0.9 * self.domain_centers[domain] + 0.1 * features
    
    def _get_state(self):
        node_features = []
        for tech in self.tech_pool:
            feat = np.concatenate([
                tech.features,
                [tech.level / MAX_TECH_LEVEL],
                [min(1.0, tech.age / 100)],
                [self.innovation_pressure]
            ])
            node_features.append(feat)
        
        edge_index = []
        for tech in self.tech_pool:
            for child_id in tech.children:
                if child_id < self.node_counter:
                    edge_index.append([tech.id, child_id])
        
        if not edge_index:
            edge_index = [[0,0]]
        
        return Data(
            x=torch.tensor(np.array(node_features), 
            dtype=torch.float),
            edge_index=torch.tensor(edge_index, dtype=torch.long).t().contiguous()
        )
    
    def _apply_aging(self):
        """增加所有技术的年龄"""
        for tech in self.tech_pool:
            tech.age += 1
    
    def _apply_decay(self):
        """应用技术衰减 - 根据年龄和衰减率降低技术等级"""
        decayed_techs = []
        for tech in self.tech_pool[:]:  # 使用副本遍历，因为可能会删除元素
            # 衰减概率随年龄增加而增加
            decay_prob = min(0.5, tech.age * DECAY_RATE / 100)
            if random.random() < decay_prob and tech.level > 1:
                tech.level -= 1
                tech.last_updated = self.current_step
                # 如果技术等级降为0，则移除
                if tech.level <= 0:
                    decayed_techs.append(tech)
        
        # 移除衰减的技术
        for tech in decayed_techs:
            self._remove_tech(tech)
    
    def _remove_tech(self, tech):
        """从科技树中移除技术"""
        # 移除节点
        self.tech_graph.remove_node(tech.id)
        self.tech_pool.remove(tech)
        
        # 更新领域计数
        self.domain_counter[tech.domain] -= 1
        if self.domain_counter[tech.domain] == 0:
            del self.domain_counter[tech.domain]
            if tech.domain in self.domain_centers:
                del self.domain_centers[tech.domain]
    
    def _apply_knowledge_diffusion(self):
        """应用知识扩散 - 提升相关技术的等级"""
        if len(self.tech_pool) < 2:
            return
            
        # 随机选择一些技术进行扩散
        for _ in range(int(len(self.tech_pool) * DIFFUSION_RATE)):
            if len(self.tech_pool) < 2:
                break
                
            tech = random.choice(self.tech_pool)
            # 找到与当前技术相似的其他技术
            similarities = []
            for other in self.tech_pool:
                if other.id != tech.id:
                    sim = 1 - cdist([tech.features], [other.features], 'cosine')[0][0]
                    similarities.append((other, sim))
            
            if not similarities:
                continue
                
            # 选择最相似的技术
            other, sim = max(similarities, key=lambda x: x[1])
            if sim > 0.7:  # 相似度阈值
                # 提升等级（但不超过最大等级）
                other.level = min(MAX_TECH_LEVEL, other.level + 1)
                other.last_updated = self.current_step
    
    def _apply_tech_revolution(self):
        """应用技术革命 - 创建颠覆性新技术"""
        if random.random() < REVOLUTION_PROB and len(self.tech_pool) > 3:
            # 选择一个现有技术作为基础
            base_tech = random.choice(self.tech_pool)
            
            # 创建革命性技术
            features = base_tech.features.copy()
            # 添加随机扰动
            features += np.random.normal(0, 0.3, features.shape)
            features = np.clip(features, -1, 1)
            
            # 确定领域（可能创建新领域）
            domain_idx = np.argmax(features[:5])
            domain = self.domain_names.get(domain_idx, f"NewDomain{domain_idx}")
            if domain_idx not in self.domain_names:
                self.domain_names[domain_idx] = domain
                self.domain_counter[domain] = 0
            
            # 创建新技术（高等级）
            tech = TechNode(
                node_id=self.node_counter,
                features=features,
                level=min(MAX_TECH_LEVEL, base_tech.level + 2),
                domain=domain
            )
            
            # 添加技术
            self._add_tech(tech)
            self.domain_counter[domain] += 1
            self._update_domain_center(domain, tech.features)
    
    def _update_innovation_pressure(self):
        """更新创新压力"""
        # 创新压力基于技术平均年龄和领域多样性
        if not self.tech_pool:
            self.innovation_pressure = 0.0
            return
            
        avg_age = sum(t.age for t in self.tech_pool) / len(self.tech_pool)
        domain_diversity = len(self.domain_centers) / 10.0  # 归一化
        
        # 创新压力公式
        self.innovation_pressure = min(1.0, 0.5 * (avg_age / 50) + 0.5 * domain_diversity)
    def _calculate_final_reward(self):
        """计算模拟结束时的最终奖励"""
        # 奖励基于技术数量、领域多样性和技术等级
        tech_count = len(self.tech_pool)
        domain_count = len(self.domain_centers)
        avg_level = sum(t.level for t in self.tech_pool) / tech_count if tech_count > 0 else 0
        
        # 计算奖励公式
        reward = (
            0.5 * tech_count +
            2.0 * domain_count +
            1.5 * avg_level +
            0.8 * self.innovation_pressure * 100
        )
        return reward
    
    def step(self, actions):
        self.current_step += 1
        reward = 0
        done = False
        
        explorer_action = actions.get('explorer', 0)
        developer_action = actions.get('developer', None)
        innovator_action = actions.get('innovator', 0)
        
        # 探索者动作: 0-不操作, 1-突变, 2-融合
        if explorer_action == 1 and len(self.tech_pool) > 0:
            reward += self._apply_mutation()
        elif explorer_action == 2 and len(self.tech_pool) >= 2:
            reward += self._apply_fusion()
        
        # 开发者动作
        if developer_action is not None and developer_action < len(self.tech_pool):
            reward += self._apply_development(developer_action)
        
        # 创新者动作: 0-不操作, 1-领域创新, 2-跨领域融合
        if innovator_action == 1 and len(self.tech_pool) > 0:
            reward += self._apply_domain_innovation()
        elif innovator_action == 2 and len(self.tech_pool) >= 2:
            reward += self._apply_cross_domain_fusion()
        
        # 自然过程
        self._apply_aging()
        self._apply_decay()
        self._apply_knowledge_diffusion()
        self._apply_tech_revolution()
        
        # 更新创新压力
        self._update_innovation_pressure()
        
        # 终止条件
        if self.current_step >= self.max_steps:
            done = True
            reward += self._calculate_final_reward()  # 现在这个方法已实现
        
        # 记录历史
        self._record_history()
        self.reward_history.append(reward)
        
        return self._get_state(), reward, done, {}
    
    def _record_history(self):
        """记录当前状态到历史"""
        snapshot = {
            'step': self.current_step,
            'techs': [(t.id, t.name, t.domain, t.level, t.age) for t in self.tech_pool],
            'edges': list(self.tech_graph.edges),
            'innovation_pressure': self.innovation_pressure,
            'domain_count': len(self.domain_centers),
            'timestamp': datetime.datetime.now().isoformat()
        }
        self.history.append(snapshot)
    
    def restore_from_history(self, step):
        """从历史恢复到指定步骤"""
        if step < 0 or step >= len(self.history):
            return
        
        snapshot = self.history[step]
        
        # 重建环境
        self.tech_pool = []
        self.tech_graph = nx.DiGraph()
        self.current_step = snapshot['step']
        self.innovation_pressure = snapshot['innovation_pressure']
        self.node_counter = 0
        
        # 重建技术节点
        tech_id_map = {}
        for tech_data in snapshot['techs']:
            tech_id, name, domain, level, age = tech_data
            tech = TechNode(
                node_id=tech_id,
                features=np.zeros(TECH_FEATURE_SIZE),  # 特征不保存，简化实现
                level=level,
                domain=domain,
                name=name
            )
            tech.age = age
            self.tech_pool.append(tech)
            # 确保添加到图中
            self.tech_graph.add_node(tech.id, 
                                    features=tech.features, 
                                    level=tech.level, 
                                    domain=tech.domain,
                                    name=tech.name)
            tech_id_map[tech_id] = tech
            if tech_id >= self.node_counter:
                self.node_counter = tech_id + 1
        
        # 重建边关系
        for edge in snapshot['edges']:
            src, dst = edge
            # 确保两端节点都存在
            if src in tech_id_map and dst in tech_id_map:
                self.tech_graph.add_edge(src, dst)
                # 更新父节点和子节点引用
                parent = tech_id_map.get(src)
                child = tech_id_map.get(dst)
                if parent and child:
                    if child.id not in parent.children:
                        parent.children.append(child.id)
                    if parent.id not in child.parents:
                        child.parents.append(parent.id)
    
    # 其他方法保持不变（_apply_mutation, _apply_fusion等）...
    # 由于篇幅限制，这里省略了环境的具体实现细节，与之前版本类似
    
    def get_tech_data(self):
        """获取技术数据用于界面显示"""
        tech_data = []
        for tech in self.tech_pool:
            tech_data.append({
                'id': tech.id,
                'name': tech.name,
                'domain': tech.domain,
                'level': tech.level,
                'age': tech.age,
                'parents': [self.tech_pool[p].name for p in tech.parents if p < len(self.tech_pool)],
                'children': [self.tech_pool[c].name for c in tech.children if c < len(self.tech_pool)],
                'created_at': tech.created_at.strftime("%Y-%m-%d %H:%M")
            })
        return tech_data
    
    def get_domain_data(self):
        """获取领域数据用于界面显示"""
        domain_data = []
        for domain, count in self.domain_counter.items():
            domain_techs = [t for t in self.tech_pool if t.domain == domain]
            avg_level = sum(t.level for t in domain_techs) / len(domain_techs) if domain_techs else 0
            max_level = max(t.level for t in domain_techs) if domain_techs else 0
            domain_data.append({
                'name': domain,
                'tech_count': count,
                'avg_level': avg_level,
                'max_level': max_level,
                'innovation_potential': self._calculate_innovation_potential(domain)
            })
        return domain_data
    
    def _calculate_innovation_potential(self, domain):
        """计算领域创新潜力"""
        if domain not in self.domain_centers:
            return 0.0
        
        # 1. 技术多样性
        domain_techs = [t for t in self.tech_pool if t.domain == domain]
        if len(domain_techs) < 2:
            return 0.0
        
        features = np.array([t.features for t in domain_techs])
        avg_distance = np.mean(cdist(features, features, 'cosine'))
        
        # 2. 技术成熟度
        avg_level = sum(t.level for t in domain_techs) / len(domain_techs)
        
        # 3. 领域关联度
        other_domains = [d for d in self.domain_centers.keys() if d != domain]
        if not other_domains:
            return 0.0
        
        domain_sims = []
        for other_domain in other_domains:
            sim = 1 - cdist([self.domain_centers[domain]], [self.domain_centers[other_domain]], 'cosine')[0][0]
            domain_sims.append(sim)
        avg_domain_sim = np.mean(domain_sims) if domain_sims else 0.0
        
        # 创新潜力公式
        return (0.4 * avg_distance + 0.3 * (MAX_TECH_LEVEL - avg_level) + 0.3 * avg_domain_sim)
    
    def export_to_json(self, filename):
        """导出当前状态到JSON文件"""
        data = {
            'techs': [],
            'edges': list(self.tech_graph.edges),
            'current_step': self.current_step,
            'innovation_pressure': self.innovation_pressure,
            'domain_centers': {k: v.tolist() for k, v in self.domain_centers.items()},
            'domain_counter': dict(self.domain_counter),
            'timestamp': datetime.datetime.now().isoformat()
        }
        
        for tech in self.tech_pool:
            data['techs'].append({
                'id': tech.id,
                'name': tech.name,
                'features': tech.features.tolist(),
                'level': tech.level,
                'parents': tech.parents,
                'children': tech.children,
                'age': tech.age,
                'domain': tech.domain,
                'created_at': tech.created_at.isoformat()
            })
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
    
    def import_from_json(self, filename):
        """从JSON文件导入状态"""
        with open(filename, 'r') as f:
            data = json.load(f)
        
        # 重置环境
        self.tech_pool = []
        self.tech_graph = nx.DiGraph()
        self.current_step = data['current_step']
        self.innovation_pressure = data['innovation_pressure']
        self.domain_centers = {k: np.array(v) for k, v in data['domain_centers'].items()}
        self.domain_counter = defaultdict(int, data['domain_counter'])
        self.node_counter = 0
        
        # 重建技术节点
        tech_id_map = {}
        for tech_data in data['techs']:
            tech = TechNode(
                node_id=tech_data['id'],
                features=np.array(tech_data['features']),
                level=tech_data['level'],
                parents=tech_data['parents'],
                domain=tech_data['domain'],
                name=tech_data['name']
            )
            tech.children = tech_data['children']
            tech.age = tech_data['age']
            tech.created_at = datetime.datetime.fromisoformat(tech_data['created_at'])
            self.tech_pool.append(tech)
            self.tech_graph.add_node(tech.id, 
                                    features=tech.features, 
                                    level=tech.level, 
                                    domain=tech.domain,
                                    name=tech.name)
            tech_id_map[tech.id] = tech
            if tech.id >= self.node_counter:
                self.node_counter = tech.id + 1
        
        # 重建边关系
        for edge in data['edges']:
            self.tech_graph.add_edge(edge[0], edge[1])
        
        # 记录历史
        self._record_history()

class MultiAgentPPO:
    def __init__(self, node_feature_size, action_sizes):
        self.policy_net = TechGNN(node_feature_size, action_sizes)
        self.optimizer = optim.Adam(self.policy_net.parameters(), lr=0.001)
        self.action_sizes = action_sizes
        
    def select_action(self, state):
        # 简化版动作选择 - 实际实现需要完整的PPO算法
        with torch.no_grad():
            explorer_out, developer_out, innovator_out, _ = self.policy_net(state)
        
        return {
            'explorer': torch.argmax(explorer_out).item(),
            'developer': torch.argmax(developer_out).item(),
            'innovator': torch.argmax(innovator_out).item()
        }
    
# ====================== 强化学习智能体 ======================
class TechGNN(nn.Module):
    def __init__(self, node_feature_size, action_sizes):
        super(TechGNN, self).__init__()
        self.conv1 = GATConv(node_feature_size, 128, heads=4, dropout=0.2)
        self.conv2 = GATConv(128*4, 128, heads=2, dropout=0.2)
        self.conv3 = GATConv(128*2, 128, heads=1, dropout=0.2)
        
        self.explorer_head = nn.Sequential(
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, action_sizes['explorer'])
        )
        
        self.developer_head = nn.Sequential(
            nn.Linear(128, 128),
            nn.ReLU(),
            nn.Linear(128, action_sizes['developer'])
        )
        
        self.innovator_head = nn.Sequential(
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, action_sizes['innovator'])
        )
        
        self.value_head = nn.Sequential(
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, 1)
        )
        
        self.ln1 = nn.LayerNorm(128*4)
        self.ln2 = nn.LayerNorm(128*2)
        self.ln3 = nn.LayerNorm(128)
    
    def forward(self, data):
        x, edge_index = data.x, data.edge_index
        
        x = F.elu(self.conv1(x, edge_index))
        x = self.ln1(x)
        x = F.dropout(x, p=0.2, training=self.training)
        
        x = F.elu(self.conv2(x, edge_index))
        x = self.ln2(x)
        x = F.dropout(x, p=0.2, training=self.training)
        
        x = F.elu(self.conv3(x, edge_index))
        x = self.ln3(x)
        
        global_x = global_add_pool(x, data.batch) if hasattr(data, 'batch') else torch.mean(x, dim=0)
        
        explorer_out = self.explorer_head(global_x)
        developer_out = self.developer_head(global_x)
        innovator_out = self.innovator_head(global_x)
        value_out = self.value_head(global_x)
        
        return explorer_out, developer_out, innovator_out, value_out

# ====================== PyQt5 界面 ======================
class TechTreeCanvas(FigureCanvas):
    def __init__(self, parent=None, width=8, height=6, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        super().__init__(self.fig)
        self.setParent(parent)
        self.ax = self.fig.add_subplot(111)
        self.ax.set_facecolor('#1e1e2e')
        self.fig.set_facecolor('#252526')
        self.ax.tick_params(colors='white')
        self.ax.xaxis.label.set_color('white')
        self.ax.yaxis.label.set_color('white')
        self.ax.title.set_color('white')
        self.ax.spines['bottom'].set_color('white')
        self.ax.spines['top'].set_color('white')
        self.ax.spines['right'].set_color('white')
        self.ax.spines['left'].set_color('white')
        self.fig.tight_layout()
    
    def update_plot(self, env, highlight_tech=None):
        # 添加调试信息
        print(f"开始更新绘图 - 当前步数: {env.current_step}")
        print(f"技术池节点数: {len(env.tech_pool)}, 图中节点数: {len(env.tech_graph.nodes)}")
        
        self.ax.clear()
    
        if len(env.tech_pool) == 0:
            self.ax.text(0.5, 0.5, "No Technology Available", 
                        ha='center', va='center', fontsize=14, color='white')
            self.draw()
            print("绘图更新完成 (空图)")
            return
            
        # 确保图中的节点与tech_pool一致
        current_nodes = {t.id for t in env.tech_pool}
        nodes_to_remove = [node for node in env.tech_graph.nodes if node not in current_nodes]
        
        if nodes_to_remove:
            print(f"移除图中 {len(nodes_to_remove)} 个不在技术池的节点")
            env.tech_graph.remove_nodes_from(nodes_to_remove)
        
        # 确保所有tech_pool节点都在图中
        nodes_to_add = []
        for tech in env.tech_pool:
            if tech.id not in env.tech_graph:
                nodes_to_add.append(tech.id)
                print(f"添加缺失节点 {tech.id} 到图中")
                env.tech_graph.add_node(tech.id, 
                                    features=tech.features, 
                                    level=tech.level, 
                                    domain=tech.domain,
                                    name=tech.name)
        
        # 创建布局 - 增强健壮性
        try:
            if len(env.tech_graph.nodes) > 1:
                print("计算力导向布局...")
                pos = nx.spring_layout(env.tech_graph, seed=42, k=0.15, iterations=50)
            elif len(env.tech_graph.nodes) == 1:
                print("处理单个节点布局...")
                # 单个节点的特殊处理
                node = list(env.tech_graph.nodes)[0]
                pos = {node: [0.5, 0.5]}
            else:
                print("没有节点，使用空布局")
                pos = {}
        except Exception as e:
            print(f"布局计算失败: {e}")
            # 使用随机布局作为回退
            print("使用随机布局作为回退")
            pos = nx.random_layout(env.tech_graph)
        
        # 确保所有节点都有位置
        all_nodes = set(env.tech_graph.nodes)
        if not all_nodes:
            print("没有节点可绘制")
            self.ax.text(0.5, 0.5, "No Technology Available", 
                        ha='center', va='center', fontsize=14, color='white')
            self.draw()
            return
        
        missing_nodes = all_nodes - set(pos.keys())
        print(f"布局节点数: {len(pos)}, 图中节点数: {len(env.tech_graph.nodes)}")
        
        # 为缺失节点添加随机位置
        if missing_nodes:
            print(f"为{len(missing_nodes)}个缺失节点添加随机位置")
            for node in missing_nodes:
                pos[node] = np.random.rand(2) * 2 - 1  # 在[-1,1]范围内随机位置
        
        # 按领域分组
        domains = list(set(t.domain for t in env.tech_pool))
        domain_colors = plt.cm.get_cmap('tab20', len(domains))
        
        # 绘制节点
        node_colors = []
        node_sizes = []
        labels = {}
        highlight_nodes = []
        
        for tech in env.tech_pool:
            if tech.domain in domains:  # 确保领域在列表中
                domain_idx = domains.index(tech.domain)
                node_colors.append(domain_colors(domain_idx))
                node_sizes.append(tech.level * 400)
                if tech.level >= 4:
                    labels[tech.id] = tech.name
                if highlight_tech and tech.id == highlight_tech:
                    highlight_nodes.append(tech.id)
            else:
                print(f"警告: 技术 {tech.id} 的领域 '{tech.domain}' 不在领域列表中")
        
        try:
            # 绘制节点
            nx.draw_networkx_nodes(
                env.tech_graph,
                pos,
                node_size=node_sizes,
                node_color=node_colors,
                alpha=0.9,
                ax=self.ax
            )
            
            # 高亮选中的节点 - 修复后的代码
            if highlight_nodes:
                # 创建高亮节点的大小列表
                highlight_sizes = []
                for tech in env.tech_pool:
                    if tech.id in highlight_nodes:
                        # 找到该节点在原始列表中的索引
                        try:
                            idx = [t.id for t in env.tech_pool].index(tech.id)
                            highlight_sizes.append(node_sizes[idx] * 1.5)
                        except ValueError:
                            # 如果找不到索引，使用默认大小
                            highlight_sizes.append(800)  # 默认大小
                
                # 确保列表长度一致
                if len(highlight_sizes) != len(highlight_nodes):
                    highlight_sizes = [800] * len(highlight_nodes)
                
                nx.draw_networkx_nodes(
                    env.tech_graph,
                    pos,
                    nodelist=highlight_nodes,
                    node_size=highlight_sizes,
                    node_color='gold',
                    alpha=0.8,
                    ax=self.ax
                )
            
            # 绘制边
            if env.tech_graph.number_of_edges() > 0:
                nx.draw_networkx_edges(
                    env.tech_graph,
                    pos,
                    edge_color='gray',
                    alpha=0.5,
                    width=1.0,
                    ax=self.ax
                )
            
            # 绘制标签
            if labels:
                nx.draw_networkx_labels(
                    env.tech_graph,
                    pos,
                    labels,
                    font_size=8,
                    font_color='white',
                    ax=self.ax
                )
        except Exception as e:
            print(f"绘图错误: {e}")
            self.ax.text(0.5, 0.5, "绘图错误", 
                        ha='center', va='center', fontsize=14, color='red')
        
        # 添加图例
        if domains:
            legend_handles = []
            for i, domain in enumerate(domains):
                legend_handles.append(plt.Line2D([0], [0], marker='o', color='w', 
                                              markerfacecolor=domain_colors(i), markersize=10, label=domain))
            self.ax.legend(handles=legend_handles, loc='upper right', fontsize=8, facecolor='#2d2d30', edgecolor='none')
        
        self.ax.set_title(f"Tech Tree Evolution (Step {env.current_step}, Domains: {len(domains)}, Innovation Pressure: {env.innovation_pressure:.2f})",
                         color='white')
        self.ax.set_axis_off()
        self.draw()
        print("绘图更新完成")

class SimulationThread(QThread):
    update_signal = pyqtSignal(object)
    finished_signal = pyqtSignal()
    progress_signal = pyqtSignal(int)
    
    def __init__(self, env, agent=None, max_steps=500, auto_mode=True):
        super().__init__()
        self.env = env
        self.agent = agent
        self.max_steps = max_steps
        self.auto_mode = auto_mode
        self.running = True
    
    def run(self):
        state = self.env.reset()
        done = False
        
        while self.running and not done and self.env.current_step < self.max_steps:
            if self.auto_mode and self.agent:
                action_info = self.agent.select_action(state)
                actions = {
                    'explorer': action_info['explorer'],
                    'developer': action_info['developer'],
                    'innovator': action_info['innovator']
                }
            else:
                actions = {}
            
            next_state, reward, done, _ = self.env.step(actions)
            state = next_state
            
            # 更新进度
            self.progress_signal.emit(int((self.env.current_step / self.max_steps) * 100))
            
            # 每5步更新一次界面
            if self.env.current_step % 5 == 0:
                self.update_signal.emit(self.env)
        
        self.update_signal.emit(self.env)
        self.finished_signal.emit()
    
    def stop(self):
        self.running = False

class TrainingThread(QThread):
    update_signal = pyqtSignal(dict)
    finished_signal = pyqtSignal()
    progress_signal = pyqtSignal(int)
    
    def __init__(self, env, agent, episodes=100, save_interval=10):
        super().__init__()
        self.env = env
        self.agent = agent
        self.episodes = episodes
        self.save_interval = save_interval
        self.running = True
        self.writer = SummaryWriter(log_dir='runs/tech_tree_training')
    
    def run(self):
        total_rewards = []
        domain_evolution = []
        
        for ep in range(self.episodes):
            if not self.running:
                break
                
            state = self.env.reset()
            total_reward = 0
            done = False
            
            while not done:
                action_info = self.agent.select_action(state)
                actions = {
                    'explorer': action_info['explorer'],
                    'developer': action_info['developer'],
                    'innovator': action_info['innovator']
                }
                
                next_state, reward, done, _ = self.env.step(actions)
                total_reward += reward
                
                # 存储经验
                with torch.no_grad():
                    _, _, _, next_value = self.agent.policy_net(next_state)
                    next_value = next_value.item()
                
                # 更新智能体...
                # 这里省略了具体的训练逻辑
                
                state = next_state
            
            total_rewards.append(total_reward)
            domain_evolution.append(len(self.env.domain_centers))
            
            # 记录到TensorBoard
            self.writer.add_scalar('Reward/Total', total_reward, ep)
            self.writer.add_scalar('Stats/Domains', len(self.env.domain_centers), ep)
            self.writer.add_scalar('Stats/Techs', len(self.env.tech_pool), ep)
            
            # 发送更新信号
            self.update_signal.emit({
                'episode': ep + 1,
                'reward': total_reward,
                'domains': len(self.env.domain_centers),
                'techs': len(self.env.tech_pool)
            })
            
            # 更新进度
            progress = int(((ep + 1) / self.episodes) * 100)
            self.progress_signal.emit(progress)
            
            # 定期保存模型
            if (ep + 1) % self.save_interval == 0:
                torch.save(self.agent.policy_net.state_dict(), f'models/tech_tree_agent_ep{ep+1}.pth')
        
        self.finished_signal.emit()
        self.writer.close()
    
    def stop(self):
        self.running = False

class TechTreeApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("高级强化学习科技树生长模拟系统")
        self.setGeometry(100, 100, 1600, 1000)
        
        # 初始化环境
        self.env = TechTreeEnv()
        self.agent = None
        self.simulation_thread = None
        self.training_thread = None
        self.auto_mode = True
        self.highlight_tech = None
        
        # 创建主界面
        self.init_ui()
        self.load_settings()
        
        # 初始绘图
        self.canvas.update_plot(self.env)
    
    def init_ui(self):
        # 创建主布局
        main_widget = QWidget()
        main_layout = QHBoxLayout()
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)
        
        # 左侧控制面板
        control_panel = QWidget()
        control_layout = QVBoxLayout()
        control_panel.setLayout(control_layout)
        control_panel.setMaximumWidth(400)
        
        # 右侧可视化区域
        visual_panel = QWidget()
        visual_layout = QVBoxLayout()
        visual_panel.setLayout(visual_layout)
        
        # 添加分割器
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(control_panel)
        splitter.addWidget(visual_panel)
        splitter.setSizes([350, 1250])
        main_layout.addWidget(splitter)
        
        # ==== 控制面板内容 ====
        # 1. 系统控制组
        control_group = QGroupBox("系统控制")
        control_group_layout = QVBoxLayout()
        
        self.auto_mode_check = QCheckBox("自动模式 (强化学习)")
        self.auto_mode_check.setChecked(True)
        self.auto_mode_check.stateChanged.connect(self.toggle_auto_mode)
        
        self.start_btn = QPushButton(QIcon("icons/play.png"), "开始模拟")
        self.start_btn.clicked.connect(self.start_simulation)
        
        self.pause_btn = QPushButton(QIcon("icons/pause.png"), "暂停模拟")
        self.pause_btn.clicked.connect(self.pause_simulation)
        self.pause_btn.setEnabled(False)
        
        self.reset_btn = QPushButton(QIcon("icons/reset.png"), "重置环境")
        self.reset_btn.clicked.connect(self.reset_environment)
        
        self.step_back_btn = QPushButton(QIcon("icons/step_back.png"), "上一步")
        self.step_back_btn.clicked.connect(self.step_back)
        
        self.step_forward_btn = QPushButton(QIcon("icons/step_forward.png"), "下一步")
        self.step_forward_btn.clicked.connect(self.step_forward)
        
        control_btn_layout = QHBoxLayout()
        control_btn_layout.addWidget(self.step_back_btn)
        control_btn_layout.addWidget(self.step_forward_btn)
        
        control_group_layout.addWidget(self.auto_mode_check)
        control_group_layout.addWidget(self.start_btn)
        control_group_layout.addWidget(self.pause_btn)
        control_group_layout.addWidget(self.reset_btn)
        control_group_layout.addLayout(control_btn_layout)
        control_group.setLayout(control_group_layout)
        
        # 2. 参数控制组
        params_group = QGroupBox("环境参数")
        params_layout = QGridLayout()
        
        params_layout.addWidget(QLabel("创新压力阈值:"), 0, 0)
        self.pressure_threshold = QDoubleSpinBox()
        self.pressure_threshold.setRange(0.0, 1.0)
        self.pressure_threshold.setValue(INNOVATION_THRESHOLD)
        self.pressure_threshold.setSingleStep(0.05)
        params_layout.addWidget(self.pressure_threshold, 0, 1)
        
        params_layout.addWidget(QLabel("突变率:"), 1, 0)
        self.mutation_rate = QDoubleSpinBox()
        self.mutation_rate.setRange(0.01, 0.5)
        self.mutation_rate.setValue(MUTATION_RATE)
        self.mutation_rate.setSingleStep(0.01)
        params_layout.addWidget(self.mutation_rate, 1, 1)
        
        params_layout.addWidget(QLabel("融合率:"), 2, 0)
        self.fusion_rate = QDoubleSpinBox()
        self.fusion_rate.setRange(0.01, 0.5)
        self.fusion_rate.setValue(FUSION_RATE)
        self.fusion_rate.setSingleStep(0.01)
        params_layout.addWidget(self.fusion_rate, 2, 1)
        
        params_layout.addWidget(QLabel("知识衰减率:"), 3, 0)
        self.decay_rate = QDoubleSpinBox()
        self.decay_rate.setRange(0.01, 0.2)
        self.decay_rate.setValue(DECAY_RATE)
        self.decay_rate.setSingleStep(0.01)
        params_layout.addWidget(self.decay_rate, 3, 1)
        
        params_layout.addWidget(QLabel("革命概率:"), 4, 0)
        self.revolution_prob = QDoubleSpinBox()
        self.revolution_prob.setRange(0.0, 0.1)
        self.revolution_prob.setValue(REVOLUTION_PROB)
        self.revolution_prob.setSingleStep(0.005)
        params_layout.addWidget(self.revolution_prob, 4, 1)
        
        params_layout.addWidget(QLabel("扩散率:"), 5, 0)
        self.diffusion_rate = QDoubleSpinBox()
        self.diffusion_rate.setRange(0.01, 0.3)
        self.diffusion_rate.setValue(DIFFUSION_RATE)
        self.diffusion_rate.setSingleStep(0.01)
        params_layout.addWidget(self.diffusion_rate, 5, 1)
        
        params_group.setLayout(params_layout)
        
        # 3. 手动操作组
        manual_group = QGroupBox("手动操作")
        manual_layout = QVBoxLayout()
        
        # 探索者操作
        explorer_layout = QHBoxLayout()
        explorer_layout.addWidget(QLabel("探索者:"))
        self.explorer_combo = QComboBox()
        self.explorer_combo.addItems(["不操作", "技术突变", "技术融合"])
        explorer_layout.addWidget(self.explorer_combo)
        manual_layout.addLayout(explorer_layout)
        
        # 开发者操作
        developer_layout = QHBoxLayout()
        developer_layout.addWidget(QLabel("开发者:"))
        self.developer_combo = QComboBox()
        developer_layout.addWidget(self.developer_combo)
        manual_layout.addLayout(developer_layout)
        
        # 创新者操作
        innovator_layout = QHBoxLayout()
        innovator_layout.addWidget(QLabel("创新者:"))
        self.innovator_combo = QComboBox()
        self.innovator_combo.addItems(["不操作", "领域创新", "跨领域融合"])
        innovator_layout.addWidget(self.innovator_combo)
        manual_layout.addLayout(innovator_layout)
        
        self.apply_btn = QPushButton(QIcon("icons/apply.png"), "应用动作")
        self.apply_btn.clicked.connect(self.apply_manual_action)
        manual_layout.addWidget(self.apply_btn)
        
        manual_group.setLayout(manual_layout)
        
        # 4. 场景管理组
        scene_group = QGroupBox("场景管理")
        scene_layout = QVBoxLayout()
        
        self.scene_list = QListWidget()
        self.scene_list.itemClicked.connect(self.load_scene)
        
        scene_btn_layout = QHBoxLayout()
        self.save_scene_btn = QPushButton(QIcon("icons/save.png"), "保存")
        self.save_scene_btn.clicked.connect(self.save_scene)
        self.delete_scene_btn = QPushButton(QIcon("icons/delete.png"), "删除")
        self.delete_scene_btn.clicked.connect(self.delete_scene)
        
        scene_btn_layout.addWidget(self.save_scene_btn)
        scene_btn_layout.addWidget(self.delete_scene_btn)
        
        scene_layout.addWidget(self.scene_list)
        scene_layout.addLayout(scene_btn_layout)
        scene_group.setLayout(scene_layout)
        
        # 5. 状态信息组
        status_group = QGroupBox("状态信息")
        status_layout = QVBoxLayout()
        
        self.step_label = QLabel("当前步数: 0")
        self.tech_count_label = QLabel("技术数量: 0")
        self.domain_count_label = QLabel("领域数量: 0")
        self.pressure_label = QLabel("创新压力: 0.00")
        self.reward_label = QLabel("累计奖励: 0.00")
        
        status_layout.addWidget(self.step_label)
        status_layout.addWidget(self.tech_count_label)
        status_layout.addWidget(self.domain_count_label)
        status_layout.addWidget(self.pressure_label)
        status_layout.addWidget(self.reward_label)
        
        # 训练进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("未运行")
        status_layout.addWidget(self.progress_bar)
        
        status_group.setLayout(status_layout)
        
        # 添加到控制面板
        control_layout.addWidget(control_group)
        control_layout.addWidget(params_group)
        control_layout.addWidget(manual_group)
        control_layout.addWidget(scene_group)
        control_layout.addWidget(status_group)
        control_layout.addStretch()
        
        # ==== 可视化面板内容 ====
        # 1. 科技树可视化
        self.canvas = TechTreeCanvas(self)
        self.toolbar = NavigationToolbar(self.canvas, self)
        visual_layout.addWidget(self.toolbar)
        visual_layout.addWidget(self.canvas, 6)
        
        # 2. 数据表格和分析工具
        self.tabs = QTabWidget()
        
        # 技术表格
        self.tech_table = QTableWidget()
        self.tech_table.setColumnCount(7)
        self.tech_table.setHorizontalHeaderLabels(["ID", "名称", "领域", "等级", "年龄", "创建时间", "父技术"])
        self.tech_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.tech_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.tech_table.itemSelectionChanged.connect(self.tech_table_selection_changed)
        
        # 领域表格
        self.domain_table = QTableWidget()
        self.domain_table.setColumnCount(5)
        self.domain_table.setHorizontalHeaderLabels(["领域", "技术数量", "平均等级", "最高等级", "创新潜力"])
        self.domain_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        # 分析面板
        analysis_tab = QWidget()
        analysis_layout = QVBoxLayout()
        
        self.analysis_combo = QComboBox()
        self.analysis_combo.addItems([
            "技术演化趋势", 
            "领域创新潜力", 
            "技术关联网络", 
            "知识扩散分析",
            "技术成熟度曲线"
        ])
        self.analysis_combo.currentIndexChanged.connect(self.update_analysis)
        
        self.analysis_canvas = FigureCanvas(Figure(figsize=(10, 6)))
        self.analysis_canvas.setMinimumHeight(400)
        
        analysis_layout.addWidget(self.analysis_combo)
        analysis_layout.addWidget(self.analysis_canvas)
        analysis_tab.setLayout(analysis_layout)
        
        # 训练面板
        training_tab = QWidget()
        training_layout = QVBoxLayout()
        
        training_params_layout = QGridLayout()
        training_params_layout.addWidget(QLabel("训练轮数:"), 0, 0)
        self.episodes_spin = QSpinBox()
        self.episodes_spin.setRange(10, 1000)
        self.episodes_spin.setValue(100)
        training_params_layout.addWidget(self.episodes_spin, 0, 1)
        
        training_params_layout.addWidget(QLabel("学习率:"), 1, 0)
        self.lr_spin = QDoubleSpinBox()
        self.lr_spin.setRange(0.0001, 0.01)
        self.lr_spin.setValue(0.001)
        self.lr_spin.setSingleStep(0.0001)
        training_params_layout.addWidget(self.lr_spin, 1, 1)
        
        training_params_layout.addWidget(QLabel("折扣因子:"), 2, 0)
        self.gamma_spin = QDoubleSpinBox()
        self.gamma_spin.setRange(0.8, 0.99)
        self.gamma_spin.setValue(0.95)
        self.gamma_spin.setSingleStep(0.01)
        training_params_layout.addWidget(self.gamma_spin, 2, 1)
        
        training_btn_layout = QHBoxLayout()
        self.start_train_btn = QPushButton("开始训练")
        self.start_train_btn.clicked.connect(self.start_training)
        self.stop_train_btn = QPushButton("停止训练")
        self.stop_train_btn.clicked.connect(self.stop_training)
        self.stop_train_btn.setEnabled(False)
        
        training_btn_layout.addWidget(self.start_train_btn)
        training_btn_layout.addWidget(self.stop_train_btn)
        
        self.train_log = QTextEdit()
        self.train_log.setReadOnly(True)
        
        training_layout.addLayout(training_params_layout)
        training_layout.addLayout(training_btn_layout)
        training_layout.addWidget(QLabel("训练日志:"))
        training_layout.addWidget(self.train_log)
        training_tab.setLayout(training_layout)
        
        self.tabs.addTab(self.tech_table, "技术列表")
        self.tabs.addTab(self.domain_table, "领域统计")
        self.tabs.addTab(analysis_tab, "高级分析")
        self.tabs.addTab(training_tab, "模型训练")
        
        visual_layout.addWidget(self.tabs, 4)
    
    def tech_table_selection_changed(self):
        selected = self.tech_table.selectedItems()
        if selected:
            tech_id = int(self.tech_table.item(selected[0].row(), 0).text())
            self.highlight_tech = tech_id
            self.canvas.update_plot(self.env, tech_id)
    
    def update_analysis(self):
        analysis_type = self.analysis_combo.currentText()
        ax = self.analysis_canvas.figure.subplots()
        ax.clear()
        
        if analysis_type == "技术演化趋势":
            self.plot_tech_evolution(ax)
        elif analysis_type == "领域创新潜力":
            self.plot_domain_potential(ax)
        elif analysis_type == "技术关联网络":
            self.plot_tech_network(ax)
        elif analysis_type == "知识扩散分析":
            self.plot_knowledge_diffusion(ax)
        elif analysis_type == "技术成熟度曲线":
            self.plot_tech_maturity(ax)
        
        self.analysis_canvas.draw()
    
    def plot_tech_evolution(self, ax):
        """绘制技术演化趋势图"""
        steps = [s['step'] for s in self.env.history]
        tech_counts = [len(s['techs']) for s in self.env.history]
        domain_counts = [s['domain_count'] for s in self.env.history]
        pressures = [s['innovation_pressure'] for s in self.env.history]
        
        ax.plot(steps, tech_counts, label='技术数量', marker='o')
        ax.plot(steps, domain_counts, label='领域数量', marker='s')
        ax.plot(steps, pressures, label='创新压力', marker='^')
        
        ax.set_xlabel('模拟步数')
        ax.set_ylabel('数量/压力')
        ax.set_title('技术演化趋势')
        ax.legend()
        ax.grid(True, linestyle='--', alpha=0.6)
    
    def plot_domain_potential(self, ax):
        """绘制领域创新潜力图"""
        domain_data = self.env.get_domain_data()
        if not domain_data:
            return
            
        domains = [d['name'] for d in domain_data]
        potentials = [d['innovation_potential'] for d in domain_data]
        
        # 按潜力排序
        sorted_data = sorted(zip(domains, potentials), key=lambda x: x[1], reverse=True)
        domains = [d[0] for d in sorted_data]
        potentials = [d[1] for d in sorted_data]
        
        colors = plt.cm.viridis(np.linspace(0, 1, len(domains)))
        
        bars = ax.bar(domains, potentials, color=colors)
        ax.set_xlabel('领域')
        ax.set_ylabel('创新潜力')
        ax.set_title('领域创新潜力分析')
        
        # 添加数据标签
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.2f}', ha='center', va='bottom')
        
        plt.setp(ax.get_xticklabels(), rotation=45, ha='right')
    
    def plot_tech_network(self, ax):
        """绘制技术关联网络图"""
        if len(self.env.tech_pool) < 3:
            return
            
        # 创建技术相似度矩阵
        features = np.array([t.features for t in self.env.tech_pool])
        similarity = 1 - cdist(features, features, 'cosine')
        
        # 使用t-SNE降维
        tsne = TSNE(n_components=2, perplexity=min(30, len(features)-1), random_state=42)
        positions = tsne.fit_transform(features)
        
        # 绘制节点
        domains = list(set(t.domain for t in self.env.tech_pool))
        domain_colors = plt.cm.get_cmap('tab20', len(domains))
        
        for i, tech in enumerate(self.env.tech_pool):
            domain_idx = domains.index(tech.domain)
            ax.scatter(positions[i, 0], positions[i, 1], 
                      s=tech.level * 50, 
                      color=domain_colors(domain_idx),
                      alpha=0.7)
            if tech.level >= 4:
                ax.text(positions[i, 0], positions[i, 1], tech.name[:10], 
                       fontsize=8, ha='center', va='bottom')
        
        # 添加图例
        legend_handles = []
        for i, domain in enumerate(domains):
            legend_handles.append(plt.Line2D([0], [0], marker='o', color='w', 
                                          markerfacecolor=domain_colors(i), markersize=10, label=domain))
        ax.legend(handles=legend_handles, loc='best')
        
        ax.set_title('技术关联网络 (t-SNE降维)')
        ax.grid(True, linestyle='--', alpha=0.3)
    
    def plot_knowledge_diffusion(self, ax):
        """绘制知识扩散分析图"""
        if len(self.env.tech_pool) < 5:
            return
            
        # 获取技术年龄和等级
        ages = [t.age for t in self.env.tech_pool]
        levels = [t.level for t in self.env.tech_pool]
        
        # 计算线性回归
        slope, intercept, r_value, p_value, std_err = linregress(ages, levels)
        line_x = np.array([min(ages), max(ages)])
        line_y = intercept + slope * line_x
        
        # 绘制散点图和回归线
        ax.scatter(ages, levels, alpha=0.6, edgecolors='w')
        ax.plot(line_x, line_y, 'r-', label=f'线性拟合 (R²={r_value**2:.2f})')
        
        ax.set_xlabel('技术年龄')
        ax.set_ylabel('技术等级')
        ax.set_title('知识扩散分析')
        ax.legend()
        ax.grid(True, linestyle='--', alpha=0.3)
    
    def plot_tech_maturity(self, ax):
        """绘制技术成熟度曲线"""
        if len(self.env.tech_pool) < 10:
            return
            
        # 按领域分组计算平均等级
        domain_data = self.env.get_domain_data()
        domains = [d['name'] for d in domain_data]
        avg_levels = [d['avg_level'] for d in domain_data]
        tech_counts = [d['tech_count'] for d in domain_data]
        
        # 创建气泡图
        colors = plt.cm.plasma(np.linspace(0, 1, len(domains)))
        max_size = max(tech_counts) * 100
        
        for i, domain in enumerate(domains):
            ax.scatter(avg_levels[i], i, 
                      s=tech_counts[i] * 100, 
                      color=colors[i],
                      alpha=0.7,
                      edgecolors='w')
            ax.text(avg_levels[i], i, domain, 
                   fontsize=9, ha='left' if avg_levels[i] < MAX_TECH_LEVEL/2 else 'right', 
                   va='center', color='white')
        
        ax.axvline(x=MAX_TECH_LEVEL/2, color='gray', linestyle='--', alpha=0.5)
        ax.text(MAX_TECH_LEVEL/2, len(domains)-0.5, '成熟度阈值', 
               rotation=90, va='bottom', ha='right', color='gray')
        
        ax.set_xlabel('平均技术等级')
        ax.set_ylabel('')
        ax.set_yticks([])
        ax.set_title('领域技术成熟度曲线')
        ax.set_xlim(0, MAX_TECH_LEVEL)
        ax.grid(True, axis='x', linestyle='--', alpha=0.3)
    
    def update_ui(self, env):
        # 更新画布
        self.canvas.update_plot(env, self.highlight_tech)
        
        # 更新状态信息
        self.step_label.setText(f"当前步数: {env.current_step}")
        self.tech_count_label.setText(f"技术数量: {len(env.tech_pool)}")
        self.domain_count_label.setText(f"领域数量: {len(env.domain_centers)}")
        self.pressure_label.setText(f"创新压力: {env.innovation_pressure:.2f}")
        
        # 更新技术表格
        tech_data = env.get_tech_data()
        self.tech_table.setRowCount(len(tech_data))
        for i, tech in enumerate(tech_data):
            self.tech_table.setItem(i, 0, QTableWidgetItem(str(tech['id'])))
            self.tech_table.setItem(i, 1, QTableWidgetItem(tech['name']))
            self.tech_table.setItem(i, 2, QTableWidgetItem(tech['domain']))
            self.tech_table.setItem(i, 3, QTableWidgetItem(str(tech['level'])))
            self.tech_table.setItem(i, 4, QTableWidgetItem(str(tech['age'])))
            self.tech_table.setItem(i, 5, QTableWidgetItem(tech['created_at']))
            self.tech_table.setItem(i, 6, QTableWidgetItem(", ".join(tech['parents'])))
        
        # 更新领域表格
        domain_data = env.get_domain_data()
        self.domain_table.setRowCount(len(domain_data))
        for i, domain in enumerate(domain_data):
            self.domain_table.setItem(i, 0, QTableWidgetItem(domain['name']))
            self.domain_table.setItem(i, 1, QTableWidgetItem(str(domain['tech_count'])))
            self.domain_table.setItem(i, 2, QTableWidgetItem(f"{domain['avg_level']:.1f}"))
            self.domain_table.setItem(i, 3, QTableWidgetItem(str(domain['max_level'])))
            self.domain_table.setItem(i, 4, QTableWidgetItem(f"{domain['innovation_potential']:.2f}"))
        
        # 更新开发者下拉框
        self.developer_combo.clear()
        for tech in tech_data:
            self.developer_combo.addItem(f"{tech['name']} (Lv.{tech['level']})", tech['id'])
    
    def start_simulation(self):
        if self.simulation_thread and self.simulation_thread.isRunning():
            return
            
        # 更新环境参数
        global INNOVATION_THRESHOLD, MUTATION_RATE, FUSION_RATE, DECAY_RATE, REVOLUTION_PROB, DIFFUSION_RATE
        INNOVATION_THRESHOLD = self.pressure_threshold.value()
        MUTATION_RATE = self.mutation_rate.value()
        FUSION_RATE = self.fusion_rate.value()
        DECAY_RATE = self.decay_rate.value()
        REVOLUTION_PROB = self.revolution_prob.value()
        DIFFUSION_RATE = self.diffusion_rate.value()
        
        self.simulation_thread = SimulationThread(
            self.env,
            agent=self.agent,
            max_steps=500,
            auto_mode=self.auto_mode
        )
        self.simulation_thread.update_signal.connect(self.update_ui)
        self.simulation_thread.finished_signal.connect(self.simulation_finished)
        self.simulation_thread.progress_signal.connect(self.update_progress)
        self.simulation_thread.start()
        
        self.start_btn.setEnabled(False)
        self.pause_btn.setEnabled(True)
        self.reset_btn.setEnabled(False)
        self.progress_bar.setFormat("模拟中...")
    
    def update_progress(self, value):
        self.progress_bar.setValue(value)
    
    def pause_simulation(self):
        if self.simulation_thread:
            self.simulation_thread.stop()
            self.simulation_thread = None
            self.start_btn.setEnabled(True)
            self.pause_btn.setEnabled(False)
            self.reset_btn.setEnabled(True)
            self.progress_bar.setFormat("已暂停")
    
    def simulation_finished(self):
        self.start_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self.reset_btn.setEnabled(True)
        self.progress_bar.setFormat("模拟完成")
    
    def reset_environment(self):
        self.env.reset()
        self.highlight_tech = None
        self.update_ui(self.env)
        self.progress_bar.setFormat("已重置")
    
    def step_back(self):
        if len(self.env.history) > 1:
            step = max(0, self.env.current_step - 1)
            self.env.restore_from_history(step)
            self.update_ui(self.env)
    
    def step_forward(self):
        if self.env.current_step < len(self.env.history) - 1:
            step = min(len(self.env.history) - 1, self.env.current_step + 1)
            self.env.restore_from_history(step)
            self.update_ui(self.env)
    
    def toggle_auto_mode(self, state):
        self.auto_mode = (state == Qt.Checked)
    
    def apply_manual_action(self):
        if self.simulation_thread and self.simulation_thread.isRunning():
            return
            
        actions = {
            'explorer': self.explorer_combo.currentIndex(),
            'innovator': self.innovator_combo.currentIndex()
        }
        
        # 开发者动作
        if self.developer_combo.currentIndex() >= 0:
            actions['developer'] = self.developer_combo.currentIndex()
        
        # 执行一步
        _, _, done, _ = self.env.step(actions)
        self.update_ui(self.env)
        
        if done:
            self.reset_environment()
    
    def save_scene(self):
        """保存当前场景"""
        name, ok = QInputDialog.getText(self, "保存场景", "输入场景名称:")
        if ok and name:
            # 创建场景目录
            if not os.path.exists("scenes"):
                os.makedirs("scenes")
            
            # 保存场景
            filename = f"scenes/{name.replace(' ', '_')}.json"
            self.env.export_to_json(filename)
            
            # 更新场景列表
            self.update_scene_list()
    
    def delete_scene(self):
        """删除当前选中的场景"""
        selected = self.scene_list.currentItem()
        if selected:
            filename = selected.data(Qt.UserRole)
            os.remove(filename)
            self.update_scene_list()
    
    def load_scene(self, item):
        """加载选中的场景"""
        filename = item.data(Qt.UserRole)
        self.env.import_from_json(filename)
        self.update_ui(self.env)
        self.progress_bar.setFormat("场景已加载")
    
    def update_scene_list(self):
        """更新场景列表"""
        self.scene_list.clear()
        if os.path.exists("scenes"):
            for file in os.listdir("scenes"):
                if file.endswith(".json"):
                    item = QListWidgetItem(file[:-5].replace('_', ' '))
                    item.setData(Qt.UserRole, os.path.join("scenes", file))
                    self.scene_list.addItem(item)
    
    def start_training(self):
        """开始训练强化学习模型"""
        if self.training_thread and self.training_thread.isRunning():
            return
            
        # 初始化智能体
        node_feature_size = TECH_FEATURE_SIZE + 3
        action_sizes = {
            'explorer': 3,
            'developer': 50,
            'innovator': 3
        }
        self.agent = MultiAgentPPO(node_feature_size, action_sizes)
        
        # 创建训练线程
        self.training_thread = TrainingThread(
            self.env,
            self.agent,
            episodes=self.episodes_spin.value()
        )
        self.training_thread.update_signal.connect(self.update_train_log)
        self.training_thread.finished_signal.connect(self.training_finished)
        self.training_thread.progress_signal.connect(self.update_progress)
        self.training_thread.start()
        
        self.start_train_btn.setEnabled(False)
        self.stop_train_btn.setEnabled(True)
        self.progress_bar.setFormat("训练中...")
        self.train_log.append(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] 训练开始")
    
    def stop_training(self):
        """停止训练"""
        if self.training_thread:
            self.training_thread.stop()
            self.training_thread = None
            self.start_train_btn.setEnabled(True)
            self.stop_train_btn.setEnabled(False)
            self.progress_bar.setFormat("训练已停止")
            self.train_log.append(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] 训练停止")
    
    def training_finished(self):
        self.start_train_btn.setEnabled(True)
        self.stop_train_btn.setEnabled(False)
        self.progress_bar.setFormat("训练完成")
        self.train_log.append(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] 训练完成")
    
    def update_train_log(self, data):
        log = f"Episode {data['episode']}: Reward={data['reward']:.1f}, Domains={data['domains']}, Techs={data['techs']}"
        self.train_log.append(log)
    
    def load_settings(self):
        """加载用户设置"""
        settings = QSettings("TechInnovation", "TechTreeSimulator")
        self.restoreGeometry(settings.value("geometry", self.saveGeometry()))
        self.restoreState(settings.value("windowState", self.saveState()))
        
        # 更新场景列表
        self.update_scene_list()
    
    def save_settings(self):
        """保存用户设置"""
        settings = QSettings("TechInnovation", "TechTreeSimulator")
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("windowState", self.saveState())
    
    def closeEvent(self, event):
        """关闭窗口时保存设置"""
        self.save_settings()
        # 停止所有线程
        if self.simulation_thread and self.simulation_thread.isRunning():
            self.simulation_thread.stop()
        if self.training_thread and self.training_thread.isRunning():
            self.training_thread.stop()
        event.accept()

# ====================== 主程序入口 ======================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 设置应用样式
    app.setStyle("Fusion")
    app.setFont(QFont("Arial", 10))
    
    # 创建主窗口
    window = TechTreeApp()
    window.show()
    
    sys.exit(app.exec_())