import sys
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
import torch_geometric
from torch_geometric.data import Data
from torch_geometric.nn import GATConv, global_add_pool
import random
from collections import deque, defaultdict
import networkx as nx
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib import pyplot as plt
from sklearn.cluster import KMeans
from scipy.spatial.distance import cdist
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QSlider, QComboBox, QGroupBox, QTextEdit, QTabWidget, QSplitter,
    QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit, QCheckBox
)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QColor

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

# ====================== 强化学习模型 ======================
class TechNode:
    __slots__ = ['id', 'features', 'level', 'parents', 'children', 'age', 'last_updated', 'domain', 'name']
    
    def __init__(self, node_id, features, level=1, parents=None, domain=None, name=None):
        self.id = node_id
        self.features = features
        self.level = level
        self.parents = parents if parents is not None else []
        self.children = []
        self.age = 0
        self.last_updated = 0
        self.domain = domain if domain is not None else np.argmax(features[:5])
        self.name = name if name else f"Tech-{node_id}"
        
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
                domain=domain,
                name=f"{domain[:3]}-{i}"
            )
            self._add_tech(tech)
            self.domain_counter[domain] += 1
            self._update_domain_center(domain, tech.features)
        
        return self._get_state()
    
    def _add_tech(self, tech):
        self.tech_pool.append(tech)
        self.tech_graph.add_node(tech.id, 
                                features=tech.features, 
                                level=tech.level, 
                                domain=tech.domain,
                                name=tech.name)
        
        for parent_id in tech.parents:
            if parent_id < self.node_counter:
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
            reward += self._calculate_final_reward()
        
        return self._get_state(), reward, done, {}
    
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
        domain = max(self.domain_counter, key=self.domain_counter.get)
        domain_techs = [t for t in self.tech_pool if t.domain == domain]
        if len(domain_techs) < 2:
            return 0
            
        tech1, tech2 = random.sample(domain_techs, 2)
        
        if random.random() < FUSION_RATE:
            fusion_vector = (tech1.features + tech2.features) / 2
            fusion_vector[:5] += 0.2 * (self.domain_centers[domain][:5] - fusion_vector[:5])
            innovation = np.random.normal(0, 0.15, TECH_FEATURE_SIZE)
            child_features = np.clip(fusion_vector + innovation, -1, 1)
            
            child = TechNode(
                node_id=self.node_counter,
                features=child_features,
                parents=[tech1.id, tech2.id],
                domain=domain,
                name=f"{domain[:3]}-F{self.node_counter}"
            )
            
            self._add_tech(child)
            self.domain_counter[domain] += 1
            self._update_domain_center(domain, child.features)
            
            synergy = self._calculate_synergy(child.id)
            return 8 + synergy * 3
        else:
            return -1
    
    def _apply_development(self, tech_idx):
        tech = self.tech_pool[tech_idx]
        if tech.level >= MAX_TECH_LEVEL:
            return -0.5
        
        tech.level += 1
        tech.last_updated = self.current_step
        self.tech_graph.nodes[tech.id]['level'] = tech.level
        
        base_reward = tech.level * 1.5
        pressure_bonus = self.innovation_pressure * 3
        return base_reward + pressure_bonus
    
    def _apply_domain_innovation(self):
        if len(self.domain_centers) >= 10:
            return -1
        
        domain1, domain2 = random.sample(list(self.domain_centers.keys()), 2)
        
        new_features = 0.6 * self.domain_centers[domain1] + 0.4 * self.domain_centers[domain2]
        innovation = np.random.normal(0, 0.25, TECH_FEATURE_SIZE)
        new_features = np.clip(new_features + innovation, -1, 1)
        
        domain_id = max(self.domain_names.keys()) + 1 if self.domain_names else 0
        new_domain = f"{domain1[:3]}-{domain2[:3]}"
        self.domain_names[domain_id] = new_domain
        
        tech = TechNode(
            node_id=self.node_counter,
            features=new_features,
            domain=new_domain,
            name=f"{new_domain}-I{self.node_counter}"
        )
        
        self._add_tech(tech)
        self.domain_counter[new_domain] = 1
        self.domain_centers[new_domain] = new_features.copy()
        return 15.0
    
    def _apply_cross_domain_fusion(self):
        domain1, domain2 = random.sample(list(self.domain_centers.keys()), 2)
        domain1_techs = [t for t in self.tech_pool if t.domain == domain1]
        domain2_techs = [t for t in self.tech_pool if t.domain == domain2]
        
        if not domain1_techs or not domain2_techs:
            return 0
            
        tech1 = random.choice(domain1_techs)
        tech2 = random.choice(domain2_techs)
        
        if random.random() < FUSION_RATE * 0.7:
            fusion_vector = (tech1.features + tech2.features) / 2
            fusion_vector[:5] = 0.5 * (self.domain_centers[domain1][:5] + self.domain_centers[domain2][:5])
            innovation = np.random.normal(0, 0.3, TECH_FEATURE_SIZE)
            child_features = np.clip(fusion_vector + innovation, -1, 1)
            
            new_domain = random.choice([domain1, domain2, f"{domain1[:2]}{domain2[:2]}"])
            
            child = TechNode(
                node_id=self.node_counter,
                features=child_features,
                parents=[tech1.id, tech2.id],
                domain=new_domain,
                name=f"{domain1[:2]}{domain2[:2]}-C{self.node_counter}"
            )
            
            self._add_tech(child)
            self.domain_counter[new_domain] = self.domain_counter.get(new_domain, 0) + 1
            self._update_domain_center(new_domain, child.features)
            
            synergy = self._calculate_synergy(child.id)
            return 12 + synergy * 4
        else:
            return -1.5
    
    def _apply_aging(self):
        for tech in self.tech_pool:
            tech.age += 1
    
    def _apply_decay(self):
        for tech in self.tech_pool:
            decay_prob = DECAY_RATE + (tech.age / 200) + (0.1 if self.current_step - tech.last_updated > 50 else 0)
            if random.random() < decay_prob and tech.level > 1:
                levels_lost = 1 if tech.level < 3 else 2
                tech.level = max(1, tech.level - levels_lost)
                self.tech_graph.nodes[tech.id]['level'] = tech.level
    
    def _apply_knowledge_diffusion(self):
        if len(self.tech_pool) < 5:
            return
            
        features = np.array([t.features for t in self.tech_pool])
        levels = np.array([t.level for t in self.tech_pool])
        
        similarity = 1 / (1 + cdist(features, features, 'cosine'))
        np.fill_diagonal(similarity, 0)
        
        for i, tech in enumerate(self.tech_pool):
            similar_indices = np.argsort(similarity[i])[-3:]
            similar_levels = levels[similar_indices]
            if max(similar_levels) > tech.level:
                if random.random() < DIFFUSION_RATE:
                    tech.level = min(MAX_TECH_LEVEL, tech.level + 1)
                    self.tech_graph.nodes[tech.id]['level'] = tech.level
    
    def _apply_tech_revolution(self):
        if random.random() < REVOLUTION_PROB and len(self.tech_pool) > 10:
            domain = max(self.domain_counter, key=self.domain_counter.get)
            domain_techs = [t for t in self.tech_pool if t.domain == domain]
            
            if len(domain_techs) < 5:
                return
                
            for tech in random.sample(domain_techs, max(2, len(domain_techs)//3)):
                if tech.level > 2:
                    tech.level = max(1, tech.level - 2)
                    self.tech_graph.nodes[tech.id]['level'] = tech.level
            
            revolution_features = self.domain_centers[domain] + np.random.normal(0, 0.4, TECH_FEATURE_SIZE)
            revolution_features = np.clip(revolution_features, -1, 1)
            
            tech = TechNode(
                node_id=self.node_counter,
                features=revolution_features,
                domain=domain,
                name=f"{domain[:3]}-R{self.node_counter}"
            )
            
            self._add_tech(tech)
            self.domain_counter[domain] += 1
            self._update_domain_center(domain, tech.features)
            self.innovation_pressure = 0.0
    
    def _update_innovation_pressure(self):
        avg_age = sum(t.age for t in self.tech_pool) / len(self.tech_pool)
        recent_innovations = sum(1 for t in self.tech_pool if t.age < 20)
        stagnation = min(1.0, avg_age / 100)
        innovation_deficit = 1 - (recent_innovations / max(1, len(self.tech_pool) / 10))
        self.innovation_pressure = min(1.0, 0.7 * stagnation + 0.3 * innovation_deficit)
        
        if self.innovation_pressure > INNOVATION_THRESHOLD and random.random() < 0.3:
            self._apply_domain_innovation()
    
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
    
    def _calculate_final_reward(self):
        if len(self.tech_graph) > 0:
            pr = nx.pagerank(self.tech_graph, weight='level')
            influence = sum(pr.values()) / len(pr)
        else:
            influence = 0
        
        domain_diversity = len(self.domain_centers) / 20
        max_level = max(t.level for t in self.tech_pool) / MAX_TECH_LEVEL
        levels = [t.level for t in self.tech_pool]
        level_std = np.std(levels)
        balance = 1 / (1 + level_std)
        return 50 * influence + 30 * domain_diversity + 20 * max_level + 10 * balance
    
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
                'children': [self.tech_pool[c].name for c in tech.children if c < len(self.tech_pool)]
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
                'max_level': max_level
            })
        return domain_data

# ====================== 强化学习智能体 ======================
class TechGNN(nn.Module):
    def __init__(self, node_feature_size, action_sizes):
        super(TechGNN, self).__init__()
        self.conv1 = GATConv(node_feature_size, 64, heads=4, dropout=0.2)
        self.conv2 = GATConv(64*4, 64, heads=2, dropout=0.2)
        self.conv3 = GATConv(64*2, 64, heads=1, dropout=0.2)
        
        self.explorer_head = nn.Sequential(
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, action_sizes['explorer'])
        )
        
        self.developer_head = nn.Sequential(
            nn.Linear(64, 64),
            nn.ReLU(),
            nn.Linear(64, action_sizes['developer'])
        )
        
        self.innovator_head = nn.Sequential(
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, action_sizes['innovator'])
        )
        
        self.value_head = nn.Sequential(
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, 1)
        )
        
        self.ln1 = nn.LayerNorm(64*4)
        self.ln2 = nn.LayerNorm(64*2)
        self.ln3 = nn.LayerNorm(64)
    
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
    
    def update_plot(self, env):
        self.ax.clear()
        
        if len(env.tech_pool) == 0:
            self.ax.text(0.5, 0.5, "No Technology Available", 
                        ha='center', va='center', fontsize=14, color='white')
            self.draw()
            return
            
        # 创建布局
        pos = {}
        domain_positions = {}
        domains = list(set(t.domain for t in env.tech_pool))
        domain_colors = plt.cm.get_cmap('tab20', len(domains))
        
        # 按领域分组技术
        for i, domain in enumerate(domains):
            domain_techs = [t.id for t in env.tech_pool if t.domain == domain]
            domain_positions[domain] = (i * 2, 0)
            
            # 在领域内垂直排列技术
            for j, tech_id in enumerate(domain_techs):
                tech = next(t for t in env.tech_pool if t.id == tech_id)
                pos[tech_id] = (i * 2, j + 1)
        
        # 绘制节点
        node_colors = []
        node_sizes = []
        labels = {}
        for tech in env.tech_pool:
            domain_idx = domains.index(tech.domain)
            node_colors.append(domain_colors(domain_idx))
            node_sizes.append(tech.level * 400)
            if tech.level >= 4:
                labels[tech.id] = tech.name
        
        nx.draw_networkx_nodes(
            env.tech_graph,
            pos,
            node_size=node_sizes,
            node_color=node_colors,
            alpha=0.9,
            ax=self.ax
        )
        
        # 绘制边
        nx.draw_networkx_edges(
            env.tech_graph,
            pos,
            edge_color='gray',
            alpha=0.5,
            width=1.0,
            ax=self.ax
        )
        
        # 绘制标签
        nx.draw_networkx_labels(
            env.tech_graph,
            pos,
            labels,
            font_size=8,
            font_color='white',
            ax=self.ax
        )
        
        # 添加领域标签
        for domain, (x, y) in domain_positions.items():
            self.ax.text(x, y, domain, 
                        ha='center', va='center', 
                        fontsize=10, color='white',
                        bbox=dict(facecolor='#3c3c3c', alpha=0.7, boxstyle='round,pad=0.5'))
        
        self.ax.set_title(f"Tech Tree Evolution (Step {env.current_step}, Domains: {len(domains)}, Innovation Pressure: {env.innovation_pressure:.2f})",
                         color='white')
        self.ax.set_axis_off()
        self.draw()

class SimulationThread(QThread):
    update_signal = pyqtSignal(object)
    finished_signal = pyqtSignal()
    
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
                # 手动模式使用默认动作
                actions = {}
            
            next_state, reward, done, _ = self.env.step(actions)
            state = next_state
            
            # 每5步更新一次界面
            if self.env.current_step % 5 == 0:
                self.update_signal.emit(self.env)
        
        self.update_signal.emit(self.env)
        self.finished_signal.emit()
    
    def stop(self):
        self.running = False

class TechTreeApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("强化学习科技树生长模拟系统")
        self.setGeometry(100, 100, 1400, 900)
        
        # 初始化环境
        self.env = TechTreeEnv()
        self.agent = None
        self.simulation_thread = None
        self.auto_mode = True
        
        # 创建主界面
        self.init_ui()
        
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
        control_panel.setMaximumWidth(350)
        
        # 右侧可视化区域
        visual_panel = QWidget()
        visual_layout = QVBoxLayout()
        visual_panel.setLayout(visual_layout)
        
        # 添加分割器
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(control_panel)
        splitter.addWidget(visual_panel)
        splitter.setSizes([300, 1100])
        main_layout.addWidget(splitter)
        
        # ==== 控制面板内容 ====
        # 1. 系统控制组
        control_group = QGroupBox("系统控制")
        control_group_layout = QVBoxLayout()
        
        self.auto_mode_check = QCheckBox("自动模式 (强化学习)")
        self.auto_mode_check.setChecked(True)
        self.auto_mode_check.stateChanged.connect(self.toggle_auto_mode)
        
        self.start_btn = QPushButton("开始模拟")
        self.start_btn.clicked.connect(self.start_simulation)
        
        self.pause_btn = QPushButton("暂停模拟")
        self.pause_btn.clicked.connect(self.pause_simulation)
        self.pause_btn.setEnabled(False)
        
        self.reset_btn = QPushButton("重置环境")
        self.reset_btn.clicked.connect(self.reset_environment)
        
        control_group_layout.addWidget(self.auto_mode_check)
        control_group_layout.addWidget(self.start_btn)
        control_group_layout.addWidget(self.pause_btn)
        control_group_layout.addWidget(self.reset_btn)
        control_group.setLayout(control_group_layout)
        
        # 2. 参数控制组
        params_group = QGroupBox("环境参数")
        params_layout = QVBoxLayout()
        
        # 创新压力阈值
        pressure_layout = QHBoxLayout()
        pressure_layout.addWidget(QLabel("创新压力阈值:"))
        self.pressure_threshold = QLineEdit(str(INNOVATION_THRESHOLD))
        pressure_layout.addWidget(self.pressure_threshold)
        params_layout.addLayout(pressure_layout)
        
        # 突变率
        mutation_layout = QHBoxLayout()
        mutation_layout.addWidget(QLabel("突变率:"))
        self.mutation_rate = QSlider(Qt.Horizontal)
        self.mutation_rate.setRange(1, 30)
        self.mutation_rate.setValue(int(MUTATION_RATE * 100))
        mutation_layout.addWidget(self.mutation_rate)
        params_layout.addLayout(mutation_layout)
        
        # 融合率
        fusion_layout = QHBoxLayout()
        fusion_layout.addWidget(QLabel("融合率:"))
        self.fusion_rate = QSlider(Qt.Horizontal)
        self.fusion_rate.setRange(1, 30)
        self.fusion_rate.setValue(int(FUSION_RATE * 100))
        fusion_layout.addWidget(self.fusion_rate)
        params_layout.addLayout(fusion_layout)
        
        # 知识衰减率
        decay_layout = QHBoxLayout()
        decay_layout.addWidget(QLabel("知识衰减率:"))
        self.decay_rate = QSlider(Qt.Horizontal)
        self.decay_rate.setRange(1, 20)
        self.decay_rate.setValue(int(DECAY_RATE * 100))
        decay_layout.addWidget(self.decay_rate)
        params_layout.addLayout(decay_layout)
        
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
        
        self.apply_btn = QPushButton("应用动作")
        self.apply_btn.clicked.connect(self.apply_manual_action)
        manual_layout.addWidget(self.apply_btn)
        
        manual_group.setLayout(manual_layout)
        
        # 4. 状态信息组
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
        
        status_group.setLayout(status_layout)
        
        # 添加到控制面板
        control_layout.addWidget(control_group)
        control_layout.addWidget(params_group)
        control_layout.addWidget(manual_group)
        control_layout.addWidget(status_group)
        control_layout.addStretch()
        
        # ==== 可视化面板内容 ====
        # 1. 科技树可视化
        self.canvas = TechTreeCanvas(self)
        visual_layout.addWidget(self.canvas, 7)
        
        # 2. 数据表格
        self.tabs = QTabWidget()
        
        # 技术表格
        self.tech_table = QTableWidget()
        self.tech_table.setColumnCount(6)
        self.tech_table.setHorizontalHeaderLabels(["ID", "名称", "领域", "等级", "年龄", "父技术"])
        self.tech_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        # 领域表格
        self.domain_table = QTableWidget()
        self.domain_table.setColumnCount(4)
        self.domain_table.setHorizontalHeaderLabels(["领域", "技术数量", "平均等级", "最高等级"])
        self.domain_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        self.tabs.addTab(self.tech_table, "技术列表")
        self.tabs.addTab(self.domain_table, "领域统计")
        
        visual_layout.addWidget(self.tabs, 3)
    
    def update_ui(self, env):
        # 更新画布
        self.canvas.update_plot(env)
        
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
            self.tech_table.setItem(i, 5, QTableWidgetItem(", ".join(tech['parents'])))
        
        # 更新领域表格
        domain_data = env.get_domain_data()
        self.domain_table.setRowCount(len(domain_data))
        for i, domain in enumerate(domain_data):
            self.domain_table.setItem(i, 0, QTableWidgetItem(domain['name']))
            self.domain_table.setItem(i, 1, QTableWidgetItem(str(domain['tech_count'])))
            self.domain_table.setItem(i, 2, QTableWidgetItem(f"{domain['avg_level']:.1f}"))
            self.domain_table.setItem(i, 3, QTableWidgetItem(str(domain['max_level'])))
        
        # 更新开发者下拉框
        self.developer_combo.clear()
        for tech in tech_data:
            self.developer_combo.addItem(f"{tech['name']} (Lv.{tech['level']})", tech['id'])
    
    def start_simulation(self):
        if self.simulation_thread and self.simulation_thread.isRunning():
            return
            
        # 更新环境参数
        global INNOVATION_THRESHOLD, MUTATION_RATE, FUSION_RATE, DECAY_RATE
        try:
            INNOVATION_THRESHOLD = float(self.pressure_threshold.text())
        except:
            pass
        MUTATION_RATE = self.mutation_rate.value() / 100
        FUSION_RATE = self.fusion_rate.value() / 100
        DECAY_RATE = self.decay_rate.value() / 100
        
        self.simulation_thread = SimulationThread(
            self.env,
            agent=self.agent,
            max_steps=500,
            auto_mode=self.auto_mode
        )
        self.simulation_thread.update_signal.connect(self.update_ui)
        self.simulation_thread.finished_signal.connect(self.simulation_finished)
        self.simulation_thread.start()
        
        self.start_btn.setEnabled(False)
        self.pause_btn.setEnabled(True)
        self.reset_btn.setEnabled(False)
    
    def pause_simulation(self):
        if self.simulation_thread:
            self.simulation_thread.stop()
            self.simulation_thread = None
            self.start_btn.setEnabled(True)
            self.pause_btn.setEnabled(False)
            self.reset_btn.setEnabled(True)
    
    def simulation_finished(self):
        self.start_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self.reset_btn.setEnabled(True)
    
    def reset_environment(self):
        self.env.reset()
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