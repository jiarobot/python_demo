import pickle
import sys
import os
import json
import time
import random
import math
import threading
import sqlite3
from PyQt5.QtWidgets import QInputDialog
import numpy as np
import cv2
import torch
import torch.nn as nn
import torch.nn.functional as F
from datetime import datetime
from collections import deque, defaultdict
from scipy import stats, signal, ndimage
import hashlib
import networkx as nx
from sklearn.manifold import TSNE
from PIL import Image, ImageFilter, ImageEnhance

# PyQt5 imports
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QLabel, QPushButton, QSlider, QComboBox, QTextEdit, QTabWidget,
                            QSplitter, QFrame, QScrollArea, QSizePolicy, QGroupBox, QGridLayout,
                            QListWidget, QListWidgetItem, QCheckBox, QLineEdit, QMessageBox,
                            QFileDialog, QProgressBar, QSpinBox, QDoubleSpinBox)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QSize, QThread, QDateTime
from PyQt5.QtGui import QImage, QPixmap, QFont, QPalette, QColor, QIcon
import pyqtgraph as pg
import pyqtgraph.opengl as gl

# VR相关导入
try:
    import openvr
    VR_AVAILABLE = True
except ImportError:
    VR_AVAILABLE = False
    print("OpenVR not available. VR features disabled.")

# 设置matplotlib使用Qt5Agg后端
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

# 数据库模型
class UniverseDatabase:
    """宇宙数据库管理"""
    
    def __init__(self, db_path="universes.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建宇宙表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS universes (
                id TEXT PRIMARY KEY,
                quantum_state TEXT,
                seed INTEGER,
                creation_time TEXT,
                energy_level REAL,
                stability REAL,
                dimensionality INTEGER,
                luck_score REAL,
                consciousness_level REAL,
                entropy REAL,
                coherence REAL,
                resonance REAL,
                weights_blob BLOB,
                parent_id TEXT,
                FOREIGN KEY (parent_id) REFERENCES universes (id)
            )
        ''')
        
        # 创建量子态表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS quantum_states (
                id TEXT PRIMARY KEY,
                amplitudes_blob BLOB,
                entropy REAL,
                superposition_factor REAL,
                coherence REAL,
                collapse_history TEXT
            )
        ''')
        
        # 创建观察者表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS observers (
                id TEXT PRIMARY KEY,
                name TEXT,
                attention REAL,
                emotion REAL,
                intention REAL,
                intervention_strength REAL,
                creation_time TEXT
            )
        ''')
        
        # 创建干预记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS interventions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                universe_id TEXT,
                observer_id TEXT,
                intervention_type TEXT,
                parameters TEXT,
                timestamp TEXT,
                FOREIGN KEY (universe_id) REFERENCES universes (id),
                FOREIGN KEY (observer_id) REFERENCES observers (id)
            )
        ''')
        
        # 创建观察记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS observations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                universe_id TEXT,
                observer_id TEXT,
                observation_data TEXT,
                timestamp TEXT,
                FOREIGN KEY (universe_id) REFERENCES universes (id),
                FOREIGN KEY (observer_id) REFERENCES observers (id)
            )
        ''')
        
        # 创建纠缠关系表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS entanglements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                universe1_id TEXT,
                universe2_id TEXT,
                entanglement_strength REAL,
                creation_time TEXT,
                FOREIGN KEY (universe1_id) REFERENCES universes (id),
                FOREIGN KEY (universe2_id) REFERENCES universes (id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def save_universe(self, universe):
        """保存宇宙到数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 序列化权重
        weights_blob = sqlite3.Binary(pickle.dumps(universe['weights']))
        
        cursor.execute('''
            INSERT OR REPLACE INTO universes 
            (id, quantum_state, seed, creation_time, energy_level, stability, 
             dimensionality, luck_score, consciousness_level, entropy, coherence, 
             resonance, weights_blob, parent_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            universe['id'],
            universe.get('quantum_state'),
            universe.get('seed'),
            universe.get('creation_time'),
            universe.get('energy_level'),
            universe.get('stability'),
            universe.get('dimensionality'),
            universe.get('luck_score'),
            universe.get('consciousness_level'),
            universe.get('entropy'),
            universe.get('coherence'),
            universe.get('resonance'),
            weights_blob,
            universe.get('parent_id')
        ))
        
        conn.commit()
        conn.close()
    
    def load_universe(self, universe_id):
        """从数据库加载宇宙"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM universes WHERE id = ?', (universe_id,))
        row = cursor.fetchone()
        
        if row:
            # 反序列化权重
            weights = pickle.loads(row[12])
            
            universe = {
                'id': row[0],
                'quantum_state': row[1],
                'seed': row[2],
                'creation_time': row[3],
                'energy_level': row[4],
                'stability': row[5],
                'dimensionality': row[6],
                'luck_score': row[7],
                'consciousness_level': row[8],
                'entropy': row[9],
                'coherence': row[10],
                'resonance': row[11],
                'weights': weights,
                'parent_id': row[13]
            }
            
            conn.close()
            return universe
        
        conn.close()
        return None
    
    def get_all_universes(self):
        """获取所有宇宙"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT id FROM universes')
        universe_ids = [row[0] for row in cursor.fetchall()]
        
        universes = []
        for universe_id in universe_ids:
            universe = self.load_universe(universe_id)
            if universe:
                universes.append(universe)
        
        conn.close()
        return universes
    
    def save_quantum_state(self, state_id, state):
        """保存量子态到数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 序列化振幅和坍缩历史
        amplitudes_blob = sqlite3.Binary(pickle.dumps(state['amplitudes']))
        collapse_history = json.dumps(state['collapse_history'])
        
        cursor.execute('''
            INSERT OR REPLACE INTO quantum_states 
            (id, amplitudes_blob, entropy, superposition_factor, coherence, collapse_history)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            state_id,
            amplitudes_blob,
            state.get('entropy'),
            state.get('superposition_factor'),
            state.get('coherence'),
            collapse_history
        ))
        
        conn.commit()
        conn.close()
    
    def save_observer(self, observer):
        """保存观察者到数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO observers 
            (id, name, attention, emotion, intention, intervention_strength, creation_time)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            observer['id'],
            observer.get('name'),
            observer.get('attention'),
            observer.get('emotion'),
            observer.get('intention'),
            observer.get('intervention_strength'),
            observer.get('creation_time')
        ))
        
        conn.commit()
        conn.close()
    
    def record_intervention(self, universe_id, observer_id, intervention_type, parameters):
        """记录干预操作"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO interventions 
            (universe_id, observer_id, intervention_type, parameters, timestamp)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            universe_id,
            observer_id,
            intervention_type,
            json.dumps(parameters),
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    def record_observation(self, universe_id, observer_id, observation_data):
        """记录观察操作"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO observations 
            (universe_id, observer_id, observation_data, timestamp)
            VALUES (?, ?, ?, ?)
        ''', (
            universe_id,
            observer_id,
            json.dumps(observation_data),
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    def record_entanglement(self, universe1_id, universe2_id, strength):
        """记录纠缠关系"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO entanglements 
            (universe1_id, universe2_id, entanglement_strength, creation_time)
            VALUES (?, ?, ?, ?)
        ''', (
            universe1_id,
            universe2_id,
            strength,
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    def get_entangled_universes(self, universe_id):
        """获取与指定宇宙纠缠的其他宇宙"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT universe1_id, universe2_id, entanglement_strength 
            FROM entanglements 
            WHERE universe1_id = ? OR universe2_id = ?
        ''', (universe_id, universe_id))
        
        entanglements = []
        for row in cursor.fetchall():
            if row[0] == universe_id:
                other_id = row[1]
            else:
                other_id = row[0]
            
            entanglements.append({
                'universe_id': other_id,
                'strength': row[2]
            })
        
        conn.close()
        return entanglements

# 量子纠缠系统
class QuantumEntanglementSystem:
    """量子纠缠系统"""
    
    def __init__(self, database):
        self.database = database
        self.entanglement_graph = nx.Graph()
    
    def create_entanglement(self, universe1_id, universe2_id, strength=0.5):
        """创建量子纠缠"""
        # 记录到数据库
        self.database.record_entanglement(universe1_id, universe2_id, strength)
        
        # 更新图
        self.entanglement_graph.add_edge(
            universe1_id, universe2_id, 
            strength=strength,
            created=datetime.now().isoformat()
        )
        
        print(f"创建量子纠缠: {universe1_id} <-> {universe2_id} (强度: {strength})")
    
    def apply_entanglement_effects(self, universe_id):
        """应用纠缠效应"""
        entanglements = self.database.get_entangled_universes(universe_id)
        
        if not entanglements:
            return None
        
        # 获取当前宇宙
        universe = self.database.load_universe(universe_id)
        if not universe:
            return None
        
        # 对所有纠缠宇宙应用效应
        for entanglement in entanglements:
            other_universe = self.database.load_universe(entanglement['universe_id'])
            if not other_universe:
                continue
            
            # 根据纠缠强度应用效应
            strength = entanglement['strength']
            
            # 能量交换
            energy_diff = (other_universe['energy_level'] - universe['energy_level']) * strength * 0.1
            universe['energy_level'] += energy_diff
            other_universe['energy_level'] -= energy_diff
            
            # 稳定性同步
            stability_diff = (other_universe['stability'] - universe['stability']) * strength * 0.05
            universe['stability'] += stability_diff
            other_universe['stability'] -= stability_diff
            
            # 保存更新后的宇宙
            self.database.save_universe(universe)
            self.database.save_universe(other_universe)
        
        return universe

# 多观察者系统
class MultiObserverSystem:
    """多观察者系统"""
    
    def __init__(self, database):
        self.database = database
        self.observers = {}  # 当前活跃观察者
        self.active_observer_id = None
    
    def create_observer(self, name, attention=0.5, emotion=0.5, intention=0.5, intervention_strength=0.5):
        """创建新观察者"""
        observer_id = hashlib.md5(f"{name}_{datetime.now().timestamp()}".encode()).hexdigest()[:8]
        
        observer = {
            'id': observer_id,
            'name': name,
            'attention': attention,
            'emotion': emotion,
            'intention': intention,
            'intervention_strength': intervention_strength,
            'creation_time': datetime.now().isoformat()
        }
        
        self.observers[observer_id] = observer
        self.database.save_observer(observer)
        
        if self.active_observer_id is None:
            self.active_observer_id = observer_id
        
        print(f"创建观察者: {name} (ID: {observer_id})")
        return observer_id
    
    def switch_observer(self, observer_id):
        """切换当前观察者"""
        if observer_id in self.observers:
            self.active_observer_id = observer_id
            print(f"切换到观察者: {self.observers[observer_id]['name']}")
            return True
        return False
    
    def get_active_observer(self):
        """获取当前观察者"""
        if self.active_observer_id:
            return self.observers[self.active_observer_id]
        return None
    
    def update_observer_state(self, observer_id, **kwargs):
        """更新观察者状态"""
        if observer_id in self.observers:
            for key, value in kwargs.items():
                if key in self.observers[observer_id]:
                    self.observers[observer_id][key] = value
            
            # 保存到数据库
            self.database.save_observer(self.observers[observer_id])
            return True
        return False
    
    def get_observer_effect(self, observer_id, universe):
        """计算观察者对宇宙的影响"""
        if observer_id not in self.observers:
            return 0.0
        
        observer = self.observers[observer_id]
        
        # 计算共振
        resonance = (
            abs(universe['energy_level'] - observer['attention']) +
            abs(universe['stability'] - observer['emotion']) +
            abs(universe['dimensionality']/10 - observer['intention'])
        ) / 3
        
        # 转换为相似度 (1 - 差异)
        resonance = 1 - resonance
        
        # 计算总影响
        effect = resonance * observer['intervention_strength']
        
        return effect

# 高级预测模型
class AdvancedTemporalTransformer(nn.Module):
    """高级时空Transformer模型"""
    
    def __init__(self, num_frames=10, patch_size=16, dim=512, depth=12, heads=16, 
                 num_future_events=20, num_temporal_layers=4):
        super().__init__()
        
        self.num_frames = num_frames
        self.patch_size = patch_size
        self.dim = dim
        self.depth = depth
        self.heads = heads
        self.num_future_events = num_future_events
        self.num_temporal_layers = num_temporal_layers
        
        # Patch embedding
        self.patch_embed = nn.Conv2d(3, dim, kernel_size=patch_size, stride=patch_size)
        
        # 位置编码
        num_patches = (224 // patch_size) ** 2
        self.pos_embed = nn.Parameter(torch.randn(1, num_patches + 1, dim) * 0.02)
        
        # 时间编码
        self.time_embed = nn.Parameter(torch.randn(1, num_frames, dim) * 0.02)
        
        # Transformer layers
        self.transformer_layers = nn.ModuleList([
            nn.TransformerEncoderLayer(d_model=dim, nhead=heads, dim_feedforward=dim*4)
            for _ in range(depth)
        ])
        
        # 时间卷积层
        self.temporal_layers = nn.ModuleList([
            nn.Conv1d(dim, dim, kernel_size=3, padding=1)
            for _ in range(num_temporal_layers)
        ])
        
        # 未来事件预测头
        self.event_head = nn.Linear(dim, num_future_events)
        
        # 未来帧预测头
        self.frame_head = nn.Sequential(
            nn.Linear(dim, dim * 4),
            nn.ReLU(),
            nn.Linear(dim * 4, patch_size * patch_size * 3),
            nn.Sigmoid()
        )
        
        # 不确定性估计
        self.uncertainty_head = nn.Linear(dim, 1)
    
    def forward(self, x):
        """前向传播"""
        # x形状: (B, T, C, H, W)
        B, T, C, H, W = x.shape
        
        # 应用patch embedding到每一帧
        patches = []
        for t in range(T):
            frame = x[:, t, :, :, :]  # (B, C, H, W)
            patched = self.patch_embed(frame)  # (B, D, H/P, W/P)
            patched = patched.flatten(2).transpose(1, 2)  # (B, N, D)
            patches.append(patched)
        
        # 合并所有帧
        x = torch.stack(patches, dim=1)  # (B, T, N, D)
        
        # 添加位置编码
        x = x + self.pos_embed[:, :x.shape[2], :]
        
        # 添加时间编码
        x = x + self.time_embed[:, :T, :].unsqueeze(2)
        
        # 重塑为3D张量 (B*T, N, D) 以适应Transformer
        x = x.reshape(B * T, x.shape[2], x.shape[3])
        
        # 应用Transformer layers
        for layer in self.transformer_layers:
            x = layer(x)
        
        # 重塑回原始形状 (B, T, N, D)
        x = x.reshape(B, T, x.shape[1], x.shape[2])
        
        # 应用时间卷积 - 修复维度问题
        for layer in self.temporal_layers:
            # 将形状改为 (B, D, T, N)
            x = x.permute(0, 3, 1, 2)  # (B, D, T, N)
            
            # 合并批次和空间维度以适应Conv1d
            B, D, T_dim, N = x.shape
            x_reshaped = x.reshape(B * N, D, T_dim)  # (B*N, D, T)
            
            # 应用Conv1d
            x_reshaped = layer(x_reshaped)  # (B*N, D, T)
            
            # 恢复形状
            x = x_reshaped.reshape(B, N, D, T_dim).permute(0, 2, 3, 1)  # (B, D, T, N)
            x = x.permute(0, 2, 3, 1)  # (B, T, N, D)
        
        # 全局平均池化
        x = x.mean(dim=2)  # (B, T, D)
        
        # 时间维度上的平均
        x = x.mean(dim=1)  # (B, D)
        
        # 事件预测
        event_logits = self.event_head(x)  # (B, num_future_events)
        event_probs = F.softmax(event_logits, dim=1)
        
        # 不确定性估计
        uncertainty = torch.sigmoid(self.uncertainty_head(x))  # (B, 1)
        
        return event_probs, uncertainty
    
    def predict_future_frames(self, x, num_future_frames=5):
        """预测未来帧"""
        # 获取当前表示
        B, T, C, H, W = x.shape
        _, features = self.forward(x)  # (B, D)
        
        future_frames = []
        
        # 递归预测未来帧
        current_features = features
        for _ in range(num_future_frames):
            # 预测下一帧
            next_frame = self.frame_head(current_features)  # (B, P*P*3)
            next_frame = next_frame.view(B, 3, self.patch_size, self.patch_size)
            
            # 简单的上采样到原始大小
            next_frame = F.interpolate(next_frame, size=(H, W), mode='bilinear', align_corners=False)
            future_frames.append(next_frame)
            
            # 更新特征（简化处理）
            current_features = current_features * 0.9 + torch.randn_like(current_features) * 0.1
        
        return torch.stack(future_frames, dim=1)  # (B, F, C, H, W)

# VR接口系统
class VRInterfaceSystem:
    """VR接口系统"""
    
    def __init__(self):
        self.vr_system = None
        self.vr_available = VR_AVAILABLE
        
        if self.vr_available:
            self.init_vr()
    
    def init_vr(self):
        """初始化VR系统"""
        try:
            self.vr_system = openvr.init(openvr.VRApplication_Scene)
            print("VR系统初始化成功")
        except Exception as e:
            print(f"VR系统初始化失败: {e}")
            self.vr_available = False
    
    def render_universe_vr(self, universe, position=(0, 0, -2)):
        """在VR中渲染宇宙"""
        if not self.vr_available or not self.vr_system:
            return False
        
        try:
            # 这里简化处理，实际应该使用更复杂的渲染逻辑
            # 获取宇宙的视觉表示
            universe_texture = self.create_universe_texture(universe)
            
            # 在指定位置渲染纹理
            # (实际实现需要更复杂的OpenVR和OpenGL集成)
            
            return True
        except Exception as e:
            print(f"VR渲染失败: {e}")
            return False
    
    def create_universe_texture(self, universe):
        """创建宇宙的视觉纹理"""
        # 基于宇宙属性生成纹理
        energy = universe['energy_level']
        stability = universe['stability']
        dimensionality = universe['dimensionality']
        
        # 创建基础纹理
        size = 512
        texture = np.zeros((size, size, 3), dtype=np.uint8)
        
        # 基于能量添加红色分量
        texture[:, :, 0] = int(energy * 255)
        
        # 基于稳定性添加绿色分量
        texture[:, :, 1] = int(stability * 255)
        
        # 基于维度添加蓝色分量
        texture[:, :, 2] = int((dimensionality / 11) * 255)
        
        # 添加一些噪声和模式
        noise = np.random.randint(0, 50, (size, size, 3), dtype=np.uint8)
        texture = np.clip(texture + noise, 0, 255)
        
        return texture
    
    def get_vr_controller_input(self):
        """获取VR控制器输入"""
        if not self.vr_available or not self.vr_system:
            return None
        
        try:
            # 获取控制器状态
            controller_states = []
            for device_index in range(openvr.k_unMaxTrackedDeviceCount):
                if self.vr_system.getTrackedDeviceClass(device_index) == openvr.TrackedDeviceClass_Controller:
                    state = self.vr_system.getControllerState(device_index)
                    controller_states.append({
                        'device_index': device_index,
                        'buttons': state.rButton,
                        'triggers': state.rAxis
                    })
            
            return controller_states
        except Exception as e:
            print(f"获取VR控制器输入失败: {e}")
            return None
    
    def shutdown(self):
        """关闭VR系统"""
        if self.vr_available and self.vr_system:
            openvr.shutdown()
            self.vr_system = None

# 量子宇宙生成器（增强版）
class EnhancedQuantumUniverseGenerator:
    """增强版量子宇宙生成器"""
    
    def __init__(self, database, multi_observer_system):
        self.database = database
        self.multi_observer_system = multi_observer_system
        self.quantum_states = {}
        self.universe_counter = 0
        self.entanglement_system = QuantumEntanglementSystem(database)
        
        # 初始化量子态
        self.initialize_quantum_states()
        
        # 从数据库加载现有宇宙
        self.load_existing_universes()
    
    def initialize_quantum_states(self, num_states=5):
        """初始化量子态"""
        print("初始化量子态...")
        
        # 创建量子叠加态
        for i in range(num_states):
            state_id = f"quantum_state_{i}"
            
            # 每个量子态是一个概率分布
            amplitudes = torch.randn(100)  # 100维的振幅
            amplitudes = F.softmax(amplitudes, dim=0)
            
            self.quantum_states[state_id] = {
                'amplitudes': amplitudes,
                'entropy': stats.entropy(amplitudes.numpy()),
                'collapse_history': [],
                'superposition_factor': random.random(),
                'coherence': random.random()
            }
            
            # 保存到数据库
            self.database.save_quantum_state(state_id, self.quantum_states[state_id])
    
    def load_existing_universes(self):
        """从数据库加载现有宇宙"""
        universes = self.database.get_all_universes()
        if universes:
            print(f"从数据库加载 {len(universes)} 个宇宙")
            
            # 更新宇宙计数器
            max_id = 0
            for universe in universes:
                try:
                    universe_num = int(universe['id'].split('_')[1])
                    if universe_num > max_id:
                        max_id = universe_num
                except:
                    pass
            
            self.universe_counter = max_id + 1
    
    def generate_universe(self, parent_id=None, strategy='quantum', observer_id=None):
        """生成新宇宙"""
        # 选择量子态
        state_id = random.choice(list(self.quantum_states.keys()))
        state = self.quantum_states[state_id]
        
        # 生成种子
        seed = (int(time.time() * 1000) + random.randint(0, 1000)) % (2**32)
        
        # 生成宇宙ID
        universe_id = f"universe_{self.universe_counter:06d}"
        self.universe_counter += 1
        
        # 生成权重
        weights = self.generate_quantum_inspired_weights(seed, state['amplitudes'])
        
        # 创建宇宙
        universe = {
            'id': universe_id,
            'quantum_state': state_id,
            'seed': seed,
            'creation_time': datetime.now().isoformat(),
            'weights': weights,
            'energy_level': random.random(),
            'stability': random.random(),
            'dimensionality': random.randint(3, 11),
            'luck_score': 0.0,
            'consciousness_level': 0.0,
            'entropy': stats.entropy(weights['fc1'].flatten().numpy()) if 'fc1' in weights else 0,
            'coherence': state['coherence'] * random.random(),
            'resonance': 0.0,
            'parent_id': parent_id
        }
        
        # 应用观察者影响
        if observer_id:
            observer_effect = self.multi_observer_system.get_observer_effect(observer_id, universe)
            universe['energy_level'] = max(0, min(1, universe['energy_level'] + observer_effect * 0.1))
            universe['stability'] = max(0, min(1, universe['stability'] + observer_effect * 0.05))
            universe['resonance'] = observer_effect
        
        # 保存到数据库
        self.database.save_universe(universe)
        
        print(f"创建新宇宙: {universe_id}")
        return universe
    
    def generate_quantum_inspired_weights(self, seed, amplitudes):
        """生成量子启发的权重"""
        torch.manual_seed(seed)
        
        # 使用振幅分布来影响权重生成
        amplitude_factor = amplitudes[0].item() * 10
        
        weights = {}
        layers = [
            ('fc1', (1024, 224*224*3)),
            ('fc2', (1024, 1024)),
            ('fc3', (1024, 1024)),
            ('fc4', (512, 1024)),
            ('fc5', (20, 512))  # 20个输出类别
        ]
        
        for name, shape in layers:
            # 基础随机权重
            base_weights = torch.randn(shape) * 0.1
            
            # 应用量子振幅影响
            quantum_influence = torch.ones(shape) * amplitude_factor
            
            # 添加一些量子纠缠效应
            entanglement = torch.sin(torch.arange(shape[0] * shape[1]).reshape(shape) * 0.1)
            
            # 组合权重
            weights[name] = base_weights + quantum_influence + entanglement
        
        return weights
    
    def evolve_universe(self, universe_id, iterations=5, strategy=None, observer_id=None):
        """演化宇宙"""
        universe = self.database.load_universe(universe_id)
        if not universe:
            return False
        
        print(f"开始演化宇宙 {universe_id}...")
        
        if strategy is None:
            strategies = ['mutate', 'cross', 'quantum_fluctuation', 'dimensional_expansion', 'entropy_reduction']
            strategy = random.choice(strategies)
        
        for i in range(iterations):
            if strategy == 'mutate':
                self.mutate_universe(universe)
            elif strategy == 'cross':
                # 随机选择另一个宇宙进行交叉
                other_universes = self.database.get_all_universes()
                if other_universes:
                    other_universe = random.choice(other_universes)
                    if other_universe['id'] != universe_id:
                        self.crossover_universes(universe, other_universe)
            elif strategy == 'quantum_fluctuation':
                self.apply_quantum_fluctuation(universe)
            elif strategy == 'dimensional_expansion':
                self.expand_dimensions(universe)
            elif strategy == 'entropy_reduction':
                self.reduce_entropy(universe)
            
            # 应用纠缠效应
            self.entanglement_system.apply_entanglement_effects(universe_id)
            
            # 应用观察者影响
            if observer_id:
                observer_effect = self.multi_observer_system.get_observer_effect(observer_id, universe)
                universe['energy_level'] = max(0, min(1, universe['energy_level'] + observer_effect * 0.05))
                universe['stability'] = max(0, min(1, universe['stability'] + observer_effect * 0.02))
            
            # 更新宇宙属性
            if 'fc1' in universe['weights']:
                universe['entropy'] = stats.entropy(universe['weights']['fc1'].flatten().numpy())
            universe['energy_level'] = random.random()
            universe['stability'] = max(0, universe['stability'] - 0.1)
        
        # 保存更新后的宇宙
        self.database.save_universe(universe)
        
        # 记录干预
        if observer_id:
            self.database.record_intervention(
                universe_id, observer_id, 'evolve', 
                {'strategy': strategy, 'iterations': iterations}
            )
        
        print(f"宇宙 {universe_id} 演化完成，策略: {strategy}")
        return True
    
    def mutate_universe(self, universe, mutation_rate=0.1):
        """突变宇宙"""
        for key, weights in universe['weights'].items():
            mutation = torch.randn_like(weights) * mutation_rate
            universe['weights'][key] = weights + mutation
    
    def crossover_universes(self, universe1, universe2, crossover_rate=0.5):
        """宇宙交叉"""
        for key in universe1['weights']:
            if key in universe2['weights']:
                # 随机选择交叉点
                mask = torch.rand_like(universe1['weights'][key]) < crossover_rate
                universe1['weights'][key] = torch.where(
                    mask, 
                    universe2['weights'][key], 
                    universe1['weights'][key]
                )
    
    def apply_quantum_fluctuation(self, universe, fluctuation_strength=0.05):
        """应用量子涨落"""
        for key, weights in universe['weights'].items():
            fluctuation = torch.sin(torch.arange(weights.numel()).reshape(weights.shape) * fluctuation_strength)
            universe['weights'][key] = weights + fluctuation
    
    def expand_dimensions(self, universe, expansion_factor=1.2):
        """维度扩展"""
        for key, weights in universe['weights'].items():
            new_shape = [int(d * expansion_factor) for d in weights.shape]
            expanded_weights = torch.randn(new_shape) * 0.1
            
            min_shape = [min(d1, d2) for d1, d2 in zip(weights.shape, new_shape)]
            for i in range(min_shape[0]):
                for j in range(min_shape[1]):
                    expanded_weights[i, j] = weights[i, j]
            
            universe['weights'][key] = expanded_weights
        
        universe['dimensionality'] += 1
    
    def reduce_entropy(self, universe, reduction_factor=0.1):
        """减少熵"""
        for key, weights in universe['weights'].items():
            mean = torch.mean(weights)
            std = torch.std(weights)
            normalized = (weights - mean) / (std + 1e-8)
            universe['weights'][key] = normalized * reduction_factor
    
    def find_luckiest_universe(self, input_data, observer_id=None):
        """寻找最幸运的宇宙"""
        best_score = -1
        best_universe = None
        
        universes = self.database.get_all_universes()
        
        print(f"在 {len(universes)} 个宇宙中寻找最幸运的宇宙...")
        
        for universe in universes:
            # 评估宇宙
            luck_score = self.evaluate_universe_luck(universe, input_data, observer_id)
            universe['luck_score'] = luck_score
            
            # 保存更新后的幸运分数
            self.database.save_universe(universe)
            
            # 检查是否是最幸运的宇宙
            if luck_score > best_score:
                best_score = luck_score
                best_universe = universe
        
        return best_universe, best_score
    
    def evaluate_universe_luck(self, universe, input_data, observer_id=None):
        """评估宇宙的幸运程度"""
        # 前向传播获取预测
        probs = self.forward_pass(universe, input_data)
        
        # 基础幸运分数
        luck_score = torch.max(probs).item()
        
        # 添加宇宙属性影响
        energy_bonus = universe['energy_level'] * 0.2
        stability_bonus = universe['stability'] * 0.3
        dimensionality_bonus = min(1.0, universe['dimensionality'] / 11) * 0.2
        coherence_bonus = universe['coherence'] * 0.1
        
        # 添加观察者影响
        observer_bonus = 0
        if observer_id:
            observer_effect = self.multi_observer_system.get_observer_effect(observer_id, universe)
            observer_bonus = observer_effect * 0.3
        
        # 计算最终幸运分数
        final_score = luck_score + energy_bonus + stability_bonus + dimensionality_bonus + coherence_bonus + observer_bonus
        
        return min(1.0, final_score)
    
    def forward_pass(self, universe, input_data):
        """在宇宙中进行前向传播"""
        x = input_data.flatten().float()
        
        # 逐层传播
        for i in range(1, 6):
            key = f'fc{i}'
            if key in universe['weights']:
                weights = universe['weights'][key]
                
                # 确保输入维度匹配
                if x.shape[0] != weights.shape[1]:
                    if x.shape[0] < weights.shape[1]:
                        padding = torch.zeros(weights.shape[1] - x.shape[0])
                        x = torch.cat([x, padding])
                    else:
                        x = x[:weights.shape[1]]
                
                x = F.linear(x, weights)
                if i < 5:
                    x = F.relu(x)
        
        # 应用softmax
        probs = F.softmax(x, dim=0)
        
        return probs

class HyperDimensionalObserver:
    """超维观测器 - 可视化高维宇宙"""
    
    def __init__(self):
        # 创建OpenGL窗口
        self.gl_widget = gl.GLViewWidget()
        self.gl_widget.setWindowTitle('超维宇宙观测器')
        self.gl_widget.setCameraPosition(distance=30, elevation=20, azimuth=45)
        
        # 创建网格
        grid = gl.GLGridItem()
        grid.scale(2, 2, 2)
        self.gl_widget.addItem(grid)
        
        # 宇宙点云
        self.universe_scatter = gl.GLScatterPlotItem()
        self.gl_widget.addItem(self.universe_scatter)
        
        # 宇宙连接线
        self.universe_line_items = []
        
        # 当前焦点宇宙
        self.focused_universe = None
        
        # 颜色映射
        self.color_map = pg.ColorMap(
            [0.0, 0.5, 1.0],
            [
                (255, 0, 0, 255),    # 红色 - 低幸运
                (255, 255, 0, 255),  # 黄色 - 中等幸运
                (0, 255, 0, 255)     # 绿色 - 高幸运
            ]
        )
    
    def visualize_universes(self, universes, connections=None):
        """可视化宇宙"""
        if not universes:
            return
        
        # 提取宇宙特征进行降维
        features = []
        for universe in universes:
            # 使用权重矩阵的统计特征
            if 'weights' in universe and 'fc1' in universe['weights']:
                weights = universe['weights']['fc1'].flatten().numpy()
                feature = [
                    np.mean(weights),
                    np.std(weights),
                    np.min(weights),
                    np.max(weights),
                    stats.skew(weights),
                    stats.kurtosis(weights),
                    universe['energy_level'],
                    universe['stability'],
                    universe['dimensionality'],
                    universe['luck_score']
                ]
                features.append(feature)
        
        # 使用t-SNE降维到3D
        if len(features) > 10:
            tsne = TSNE(n_components=3, random_state=42, perplexity=min(30, len(features)-1))
            points_3d = tsne.fit_transform(features)
        else:
            # 如果宇宙太少，使用随机位置
            points_3d = np.random.rand(len(universes), 3) * 10 - 5
        
        # 更新点云
        colors = np.zeros((len(universes), 4))
        sizes = np.zeros(len(universes))
        
        for i, universe in enumerate(universes):
            # 根据幸运分数设置颜色
            luck = universe['luck_score']
            color = self.color_map.map(luck, 'qcolor')
            colors[i] = [color.red()/255, color.green()/255, color.blue()/255, 0.8]
            
            # 根据能量级别设置大小
            sizes[i] = 5 + universe['energy_level'] * 10
        
        self.universe_scatter.setData(
            pos=points_3d,
            color=colors,
            size=sizes,
            pxMode=False
        )
        
        # 绘制连接线
        self.clear_lines()
        if connections:
            for i, j in connections:
                if i < len(points_3d) and j < len(points_3d):
                    line = gl.GLLinePlotItem(
                        pos=np.array([points_3d[i], points_3d[j]]),
                        color=(1, 1, 1, 0.3),
                        width=1
                    )
                    self.gl_widget.addItem(line)
                    self.universe_line_items.append(line)
        
        # 标记焦点宇宙
        if self.focused_universe:
            for i, universe in enumerate(universes):
                if universe['id'] == self.focused_universe:
                    focus_point = points_3d[i]
                    focus_marker = gl.GLScatterPlotItem(
                        pos=[focus_point],
                        color=(1, 1, 1, 1),
                        size=20,
                        pxMode=False
                    )
                    self.gl_widget.addItem(focus_marker)
                    self.universe_line_items.append(focus_marker)
                    break
    
    def clear_lines(self):
        """清除所有连接线"""
        for line in self.universe_line_items:
            self.gl_widget.removeItem(line)
        self.universe_line_items = []
    
    def focus_on_universe(self, universe_id):
        """聚焦到特定宇宙"""
        self.focused_universe = universe_id
    
    def get_widget(self):
        """获取OpenGL窗口部件"""
        return self.gl_widget

class VideoCaptureThread(QThread):
    """视频捕获线程"""
    frame_ready = pyqtSignal(np.ndarray)
    
    def __init__(self, video_source=0):
        super().__init__()
        self.video_source = video_source
        self.running = True
    
    def run(self):
        cap = cv2.VideoCapture(self.video_source)
        while self.running:
            ret, frame = cap.read()
            if ret:
                self.frame_ready.emit(frame)
            time.sleep(0.033)  # 约30fps
        cap.release()
    
    def stop(self):
        self.running = False

class UniverseInfoWidget(QWidget):
    """宇宙信息显示部件"""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 宇宙ID
        self.id_label = QLabel("宇宙ID: ")
        layout.addWidget(self.id_label)
        
        # 量子态
        self.quantum_state_label = QLabel("量子态: ")
        layout.addWidget(self.quantum_state_label)
        
        # 属性网格
        properties_group = QGroupBox("宇宙属性")
        properties_layout = QVBoxLayout()
        
        self.energy_label = QLabel("能量级别: ")
        properties_layout.addWidget(self.energy_label)
        
        self.stability_label = QLabel("稳定性: ")
        properties_layout.addWidget(self.stability_label)
        
        self.dimensionality_label = QLabel("维度: ")
        properties_layout.addWidget(self.dimensionality_label)
        
        self.luck_label = QLabel("幸运分数: ")
        properties_layout.addWidget(self.luck_label)
        
        self.entropy_label = QLabel("熵: ")
        properties_layout.addWidget(self.entropy_label)
        
        self.coherence_label = QLabel("相干性: ")
        properties_layout.addWidget(self.coherence_label)
        
        self.resonance_label = QLabel("共振: ")
        properties_layout.addWidget(self.resonance_label)
        
        properties_group.setLayout(properties_layout)
        layout.addWidget(properties_group)
        
        # 操作按钮
        self.focus_button = QPushButton("聚焦此宇宙")
        layout.addWidget(self.focus_button)
        
        self.intervene_button = QPushButton("干预此宇宙")
        layout.addWidget(self.intervene_button)
        
        layout.addStretch()
        self.setLayout(layout)
    
    def update_info(self, universe):
        """更新宇宙信息"""
        self.id_label.setText(f"宇宙ID: {universe['id']}")
        self.quantum_state_label.setText(f"量子态: {universe.get('quantum_state', 'N/A')}")
        self.energy_label.setText(f"能量级别: {universe['energy_level']:.3f}")
        self.stability_label.setText(f"稳定性: {universe['stability']:.3f}")
        self.dimensionality_label.setText(f"维度: {universe['dimensionality']}")
        self.luck_label.setText(f"幸运分数: {universe['luck_score']:.3f}")
        
        # 修复熵的显示问题
        entropy = universe['entropy']
        if isinstance(entropy, bytes):
            # 如果是bytes类型，尝试转换为浮点数
            try:
                entropy = float(entropy.decode('utf-8'))
            except:
                entropy = 0.0
        self.entropy_label.setText(f"熵: {entropy:.3f}")
        
        self.coherence_label.setText(f"相干性: {universe.get('coherence', 0):.3f}")
        self.resonance_label.setText(f"共振: {universe.get('resonance', 0):.3f}")

# 主应用程序
class CosmicInterventionSystem(QMainWindow):
    """宇宙干预系统 - 终极增强版"""
    
    def __init__(self):
        super().__init__()
        
        # 初始化数据库
        self.database = UniverseDatabase()
        
        # 初始化多观察者系统
        self.multi_observer_system = MultiObserverSystem(self.database)
        
        # 初始化量子宇宙生成器
        self.quantum_generator = EnhancedQuantumUniverseGenerator(
            self.database, self.multi_observer_system
        )
        
        # 初始化高级预测模型
        self.predictor = AdvancedTemporalTransformer()
        
        # 初始化VR系统
        self.vr_system = VRInterfaceSystem()
        
        # 初始化超维观测器
        self.observer = HyperDimensionalObserver()
        
        # 视频捕获
        self.video_thread = VideoCaptureThread()
        self.video_thread.frame_ready.connect(self.process_frame)
        
        # 当前状态
        self.current_frame = None
        self.current_universes = []
        self.lucky_universe = None
        self.history = []
        self.observer_state = {}
        
        # 初始化UI
        self.init_ui()
        
        # 启动视频捕获
        self.video_thread.start()
        
        # 启动定时器用于更新可视化
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_visualization)
        self.timer.start(1000)  # 每秒更新一次
        
        # 创建默认观察者
        self.default_observer_id = self.multi_observer_system.create_observer("默认观察者")
    
    def init_ui(self):
        self.setWindowTitle("超维宇宙观测与干预系统 - 终极增强版")
        self.setGeometry(100, 100, 1920, 1080)
        
        # 中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QHBoxLayout()
        central_widget.setLayout(main_layout)
        
        # 左侧面板 - 控制和信息
        left_panel = QWidget()
        left_panel.setMaximumWidth(500)
        left_layout = QVBoxLayout()
        left_panel.setLayout(left_layout)
        
        # 观察者管理
        observer_group = QGroupBox("观察者管理")
        observer_layout = QVBoxLayout()
        
        self.observer_list = QListWidget()
        self.observer_list.itemSelectionChanged.connect(self.on_observer_selected)
        observer_layout.addWidget(self.observer_list)
        
        self.create_observer_btn = QPushButton("创建新观察者")
        self.create_observer_btn.clicked.connect(self.create_new_observer)
        observer_layout.addWidget(self.create_observer_btn)
        
        observer_group.setLayout(observer_layout)
        left_layout.addWidget(observer_group)
        
        # 观察者状态控制
        state_group = QGroupBox("观察者状态控制")
        state_layout = QGridLayout()
        
        state_layout.addWidget(QLabel("注意力:"), 0, 0)
        self.attention_slider = QSlider(Qt.Horizontal)
        self.attention_slider.setRange(0, 100)
        self.attention_slider.setValue(50)
        self.attention_slider.valueChanged.connect(self.update_observer_state)
        state_layout.addWidget(self.attention_slider, 0, 1)
        
        state_layout.addWidget(QLabel("情绪:"), 1, 0)
        self.emotion_slider = QSlider(Qt.Horizontal)
        self.emotion_slider.setRange(0, 100)
        self.emotion_slider.setValue(50)
        self.emotion_slider.valueChanged.connect(self.update_observer_state)
        state_layout.addWidget(self.emotion_slider, 1, 1)
        
        state_layout.addWidget(QLabel("意图:"), 2, 0)
        self.intention_slider = QSlider(Qt.Horizontal)
        self.intention_slider.setRange(0, 100)
        self.intention_slider.setValue(50)
        self.intention_slider.valueChanged.connect(self.update_observer_state)
        state_layout.addWidget(self.intention_slider, 2, 1)
        
        state_layout.addWidget(QLabel("干预强度:"), 3, 0)
        self.intervention_slider = QSlider(Qt.Horizontal)
        self.intervention_slider.setRange(0, 100)
        self.intervention_slider.setValue(50)
        self.intervention_slider.valueChanged.connect(self.update_observer_state)
        state_layout.addWidget(self.intervention_slider, 3, 1)
        
        state_group.setLayout(state_layout)
        left_layout.addWidget(state_group)
        
        # 宇宙信息
        self.universe_info = UniverseInfoWidget()
        left_layout.addWidget(self.universe_info)
        
        # 操作按钮
        operations_group = QGroupBox("宇宙操作")
        operations_layout = QVBoxLayout()
        
        self.create_universe_btn = QPushButton("创建新宇宙")
        self.create_universe_btn.clicked.connect(self.create_new_universe)
        operations_layout.addWidget(self.create_universe_btn)
        
        self.evolve_universe_btn = QPushButton("演化选中宇宙")
        self.evolve_universe_btn.clicked.connect(self.evolve_selected_universe)
        operations_layout.addWidget(self.evolve_universe_btn)
        
        self.entangle_universe_btn = QPushButton("创建量子纠缠")
        self.entangle_universe_btn.clicked.connect(self.create_entanglement)
        operations_layout.addWidget(self.entangle_universe_btn)
        
        self.collapse_quantum_btn = QPushButton("坍缩量子态")
        self.collapse_quantum_btn.clicked.connect(self.collapse_quantum_state)
        operations_layout.addWidget(self.collapse_quantum_btn)
        
        self.vr_mode_btn = QPushButton("VR模式")
        self.vr_mode_btn.clicked.connect(self.toggle_vr_mode)
        self.vr_mode_btn.setEnabled(self.vr_system.vr_available)
        operations_layout.addWidget(self.vr_mode_btn)
        
        operations_group.setLayout(operations_layout)
        left_layout.addWidget(operations_group)
        
        # 历史记录
        history_group = QGroupBox("历史记录")
        history_layout = QVBoxLayout()
        
        self.history_text = QTextEdit()
        self.history_text.setMaximumHeight(200)
        history_layout.addWidget(self.history_text)
        
        history_group.setLayout(history_layout)
        left_layout.addWidget(history_group)
        
        # 右侧面板 - 可视化
        right_panel = QWidget()
        right_layout = QVBoxLayout()
        right_panel.setLayout(right_layout)
        
        # 标签页
        self.tab_widget = QTabWidget()
        
        # 3D宇宙可视化标签页
        self.gl_container = QWidget()
        gl_layout = QVBoxLayout()
        gl_layout.addWidget(self.observer.get_widget())
        self.gl_container.setLayout(gl_layout)
        self.tab_widget.addTab(self.gl_container, "3D宇宙可视化")
        
        # 视频帧标签页
        self.video_container = QWidget()
        video_layout = QVBoxLayout()
        self.video_label = QLabel()
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setMinimumSize(640, 480)
        video_layout.addWidget(self.video_label)
        self.video_container.setLayout(video_layout)
        self.tab_widget.addTab(self.video_container, "实时视频")
        
        # 未来预测标签页
        self.prediction_container = QWidget()
        prediction_layout = QVBoxLayout()
        self.prediction_label = QLabel("未来预测将显示在这里")
        self.prediction_label.setAlignment(Qt.AlignCenter)
        prediction_layout.addWidget(self.prediction_label)
        self.prediction_container.setLayout(prediction_layout)
        self.tab_widget.addTab(self.prediction_container, "未来预测")
        
        # 宇宙数据库标签页
        self.database_container = QWidget()
        database_layout = QVBoxLayout()
        self.database_text = QTextEdit()
        self.database_text.setReadOnly(True)
        database_layout.addWidget(self.database_text)
        self.refresh_db_btn = QPushButton("刷新数据库")
        self.refresh_db_btn.clicked.connect(self.refresh_database_view)
        database_layout.addWidget(self.refresh_db_btn)
        self.database_container.setLayout(database_layout)
        self.tab_widget.addTab(self.database_container, "宇宙数据库")
        
        right_layout.addWidget(self.tab_widget)
        
        # 将左右面板添加到主布局
        main_layout.addWidget(left_panel)
        main_layout.addWidget(right_panel)
        
        # 初始化观察者列表
        self.update_observer_list()
    
    def update_observer_list(self):
        """更新观察者列表"""
        self.observer_list.clear()
        
        for observer_id, observer in self.multi_observer_system.observers.items():
            item = QListWidgetItem(observer['name'])
            item.setData(Qt.UserRole, observer_id)
            self.observer_list.addItem(item)
            
            # 标记当前活动观察者
            if observer_id == self.multi_observer_system.active_observer_id:
                item.setBackground(QColor(200, 200, 255))
    
    def on_observer_selected(self):
        """观察者选择变化"""
        selected_items = self.observer_list.selectedItems()
        if not selected_items:
            return
        
        observer_id = selected_items[0].data(Qt.UserRole)
        self.multi_observer_system.switch_observer(observer_id)
        
        # 更新UI状态
        observer = self.multi_observer_system.get_active_observer()
        if observer:
            self.attention_slider.setValue(int(observer['attention'] * 100))
            self.emotion_slider.setValue(int(observer['emotion'] * 100))
            self.intention_slider.setValue(int(observer['intention'] * 100))
            self.intervention_slider.setValue(int(observer['intervention_strength'] * 100))
    
    def create_new_observer(self):
        """创建新观察者"""
        name, ok = QInputDialog.getText(self, "创建观察者", "请输入观察者名称:")
        if ok and name:
            observer_id = self.multi_observer_system.create_observer(name)
            self.update_observer_list()
    
    def update_observer_state(self):
        """更新观察者状态"""
        observer = self.multi_observer_system.get_active_observer()
        if not observer:
            return
        
        self.multi_observer_system.update_observer_state(
            observer['id'],
            attention=self.attention_slider.value() / 100.0,
            emotion=self.emotion_slider.value() / 100.0,
            intention=self.intention_slider.value() / 100.0,
            intervention_strength=self.intervention_slider.value() / 100.0
        )
    
    def process_frame(self, frame):
        """处理视频帧"""
        self.current_frame = frame
        
        # 显示视频帧
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_frame.shape
        bytes_per_line = ch * w
        qt_image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
        self.video_label.setPixmap(QPixmap.fromImage(qt_image))
        
        # 每10帧进行一次宇宙探索
        if len(self.history) % 10 == 0:
            self.explore_universes()
    
    def explore_universes(self):
        """探索宇宙"""
        if self.current_frame is None:
            return
        
        # 获取当前观察者
        observer = self.multi_observer_system.get_active_observer()
        if not observer:
            return
        
        # 调整帧大小
        frame = cv2.resize(self.current_frame, (224, 224))
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame_tensor = torch.from_numpy(frame).float() / 255.0
        frame_tensor = frame_tensor.permute(2, 0, 1)  # (C, H, W)
        
        # 预测未来
        event_name, event_prob = self.predict_future(frame_tensor.unsqueeze(0))
        
        # 寻找幸运宇宙
        input_data = frame_tensor.flatten()
        lucky_universe, luck_score = self.quantum_generator.find_luckiest_universe(
            input_data, observer['id']
        )
        
        self.lucky_universe = lucky_universe
        
        # 更新宇宙信息显示
        if lucky_universe:
            self.universe_info.update_info(lucky_universe)
            self.observer_state['focus_universe'] = lucky_universe['id']
            self.observer.focus_on_universe(lucky_universe['id'])
        
        # 记录观察
        self.database.record_observation(
            lucky_universe['id'] if lucky_universe else None,
            observer['id'],
            {
                'event': event_name,
                'event_prob': event_prob,
                'luck_score': luck_score
            }
        )
        
        # 记录历史
        history_entry = {
            'time': datetime.now().isoformat(),
            'event': event_name,
            'event_prob': event_prob,
            'lucky_universe': lucky_universe['id'] if lucky_universe else None,
            'luck_score': luck_score,
            'observer': observer['name']
        }
        
        self.history.append(history_entry)
        
        # 更新历史显示
        self.update_history_display()
        
        # 更新预测显示
        self.prediction_label.setText(
            f"预测事件: {event_name}\n"
            f"概率: {event_prob:.3f}\n"
            f"幸运宇宙: {lucky_universe['id'] if lucky_universe else '无'}\n"
            f"幸运分数: {luck_score:.3f}\n"
            f"观察者: {observer['name']}"
        )
    
    # 在 CosmicInterventionSystem 类中修改 predict_future 方法
    def predict_future(self, frame):
        """预测未来"""
        # 确保输入有5个维度 (B, T, C, H, W)
        # 当前frame的形状是 (1, 3, 224, 224)，需要添加时间维度
        if len(frame.shape) == 4:
            # 添加时间维度
            frame = frame.unsqueeze(1)  # 现在形状是 (1, 1, 3, 224, 224)
        
        # 确保时间维度与模型期望的一致
        T = self.predictor.num_frames
        if frame.shape[1] < T:
            # 重复最后一帧以匹配期望的时间步数
            last_frame = frame[:, -1:, :, :, :]
            repeat_frames = last_frame.repeat(1, T - frame.shape[1], 1, 1, 1)
            frame = torch.cat([frame, repeat_frames], dim=1)
        elif frame.shape[1] > T:
            # 只取前T个帧
            frame = frame[:, :T, :, :, :]
        
        with torch.no_grad():
            prediction, uncertainty = self.predictor(frame)
        
        # 事件类别
        event_classes = [
            '时间线稳定', '时间线分支', '时间线收敛', '时间线断裂',
            '因果反转', '时空涟漪', '维度折叠', '维度扩展',
            '现实重构', '量子隧穿', '意识觉醒', '宇宙融合',
            '维度旅行', '时间循环', '平行交汇', '信息奇点',
            '熵减异常', '量子相干', '超维感知', '元现实显现'
        ]
        
        event_idx = torch.argmax(prediction).item()
        event_prob = prediction[0, event_idx].item()
        uncertainty = uncertainty.item()
        event_name = f"{event_classes[event_idx]} (不确定性: {uncertainty:.3f})"
        
        return event_name, event_prob
    
    def update_visualization(self):
        """更新可视化"""
        # 获取所有宇宙
        universes = self.database.get_all_universes()
        
        # 获取宇宙连接 (基于量子态和纠缠)
        connections = []
        universe_ids = [u['id'] for u in universes]
        
        for i, u1 in enumerate(universes):
            for j, u2 in enumerate(universes):
                if i != j:
                    # 量子态连接
                    if 'quantum_state' in u1 and 'quantum_state' in u2:
                        if u1['quantum_state'] == u2['quantum_state']:
                            connections.append((i, j))
                    
                    # 纠缠连接
                    entanglements = self.database.get_entangled_universes(u1['id'])
                    for entanglement in entanglements:
                        if entanglement['universe_id'] == u2['id']:
                            connections.append((i, j))
        
        # 更新观测器
        self.observer.visualize_universes(universes, connections)
    
    def update_history_display(self):
        """更新历史记录显示"""
        if not self.history:
            return
        
        # 只显示最近10条历史
        recent_history = self.history[-10:]
        text = ""
        
        for entry in recent_history:
            text += f"{entry['time']}: {entry['event']} ({entry['event_prob']:.3f})\n"
            text += f"  幸运宇宙: {entry['lucky_universe']} ({entry['luck_score']:.3f})\n"
            text += f"  观察者: {entry['observer']}\n\n"
        
        self.history_text.setText(text)
    
    def create_new_universe(self):
        """创建新宇宙"""
        observer = self.multi_observer_system.get_active_observer()
        if not observer:
            return
        
        parent_id = self.observer_state.get('focus_universe')
        strategy = 'quantum'  # 可以添加UI选择策略
        
        new_universe = self.quantum_generator.generate_universe(parent_id, strategy, observer['id'])
        
        # 记录干预
        self.database.record_intervention(
            new_universe['id'], observer['id'], 'create_universe',
            {'parent_id': parent_id, 'strategy': strategy}
        )
        
        # 更新显示
        self.universe_info.update_info(new_universe)
        self.observer_state['focus_universe'] = new_universe['id']
        self.observer.focus_on_universe(new_universe['id'])
    
    def evolve_selected_universe(self):
        """演化选中宇宙"""
        universe_id = self.observer_state.get('focus_universe')
        if not universe_id:
            return
        
        observer = self.multi_observer_system.get_active_observer()
        if not observer:
            return
        
        strategies = ['mutate', 'cross', 'quantum_fluctuation', 'dimensional_expansion', 'entropy_reduction']
        strategy = random.choice(strategies)
        
        success = self.quantum_generator.evolve_universe(universe_id, 5, strategy, observer['id'])
        
        if success:
            # 更新显示
            universe = self.database.load_universe(universe_id)
            if universe:
                self.universe_info.update_info(universe)
    
    def create_entanglement(self):
        """创建量子纠缠"""
        universe1_id = self.observer_state.get('focus_universe')
        if not universe1_id:
            return
        
        # 随机选择另一个宇宙
        universes = self.database.get_all_universes()
        if len(universes) < 2:
            return
        
        universe2 = random.choice(universes)
        while universe2['id'] == universe1_id and len(universes) > 1:
            universe2 = random.choice(universes)
        
        strength = random.uniform(0.3, 0.8)
        
        self.quantum_generator.entanglement_system.create_entanglement(
            universe1_id, universe2['id'], strength
        )
        
        # 记录干预
        observer = self.multi_observer_system.get_active_observer()
        if observer:
            self.database.record_intervention(
                universe1_id, observer['id'], 'create_entanglement',
                {'universe2_id': universe2['id'], 'strength': strength}
            )
    
    def collapse_quantum_state(self):
        """坍缩量子态"""
        universe_id = self.observer_state.get('focus_universe')
        if not universe_id:
            return
        
        universe = self.database.load_universe(universe_id)
        if not universe or 'quantum_state' not in universe:
            return
        
        state_id = universe['quantum_state']
        collapsed_index = self.quantum_generator.collapse_quantum_state(state_id)
        
        # 记录干预
        observer = self.multi_observer_system.get_active_observer()
        if observer:
            self.database.record_intervention(
                universe_id, observer['id'], 'collapse_quantum_state',
                {'quantum_state': state_id, 'collapsed_index': collapsed_index}
            )
    
    def toggle_vr_mode(self):
        """切换VR模式"""
        if not self.vr_system.vr_available:
            QMessageBox.warning(self, "VR不可用", "VR系统不可用，请检查安装。")
            return
        
        universe_id = self.observer_state.get('focus_universe')
        if not universe_id:
            QMessageBox.warning(self, "无焦点宇宙", "请先选择一个宇宙。")
            return
        
        universe = self.database.load_universe(universe_id)
        if not universe:
            return
        
        success = self.vr_system.render_universe_vr(universe)
        if success:
            QMessageBox.information(self, "VR模式", "已进入VR模式。")
        else:
            QMessageBox.warning(self, "VR错误", "无法进入VR模式。")
    
    def refresh_database_view(self):
        """刷新数据库视图"""
        universes = self.database.get_all_universes()
        observers = list(self.multi_observer_system.observers.values())
        
        text = f"宇宙数量: {len(universes)}\n"
        text += f"观察者数量: {len(observers)}\n\n"
        
        text += "最近创建的宇宙:\n"
        for universe in sorted(universes, key=lambda u: u.get('creation_time', ''), reverse=True)[:5]:
            text += f"  {universe['id']} (创建于: {universe.get('creation_time')})\n"
        
        text += "\n观察者列表:\n"
        for observer in observers:
            text += f"  {observer['name']} (ID: {observer['id']})\n"
        
        self.database_text.setText(text)
    
    def closeEvent(self, event):
        """关闭事件"""
        self.video_thread.stop()
        self.video_thread.wait()
        self.vr_system.shutdown()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 设置应用程序样式
    app.setStyle('Fusion')
    
    # 创建主窗口
    window = CosmicInterventionSystem()
    window.show()
    
    sys.exit(app.exec_())