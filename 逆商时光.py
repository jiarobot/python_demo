import sys
import json
import pickle
import datetime
import random
import math
import numpy as np
import ast
import threading
import time as time_module
from typing import Any, Dict, List, Optional, Set, Tuple, Callable
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QSlider, 
                             QListWidget, QListWidgetItem, QMessageBox,
                             QSplitter, QFrame, QTextEdit, QProgressBar,
                             QTabWidget, QGraphicsView, QGraphicsScene, 
                             QGraphicsItem, QGraphicsEllipseItem, QGraphicsLineItem,
                             QGraphicsTextItem, QDialog, QLineEdit, QDialogButtonBox,
                             QComboBox, QCheckBox, QGroupBox, QSpinBox, QDoubleSpinBox,
                             QTreeWidget, QTreeWidgetItem, QHeaderView, QTextBrowser,
                             QTableWidget, QTableWidgetItem, QToolBox, QFormLayout,
                             QScrollArea, QSizePolicy, QMenu, QAction, QToolBar,
                             QDockWidget, QStatusBar, QInputDialog, QFontDialog,
                             QColorDialog, QFileDialog, QMessageBox, QProgressDialog,
                             QGraphicsPathItem, QGraphicsPolygonItem, QGraphicsRectItem)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QDateTime, QSettings, QPointF, QRectF, QThread, pyqtSlot, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import (QFont, QColor, QPalette, QPen, QBrush, QLinearGradient, 
                         QPainter, QPainterPath, QFontMetrics, QKeySequence, QIcon,
                         QSyntaxHighlighter, QTextCharFormat, QTextCursor, QKeyEvent,
                         QPolygonF, QRadialGradient, QPainterPathStroker, QTransform)
import inspect
import hashlib
import base64
from collections import deque, defaultdict
import sqlite3
from contextlib import contextmanager
import scipy.integrate as integrate
from scipy.optimize import minimize
import networkx as nx


class NegativeEntropyException(Exception):
    """逆熵异常"""
    pass


class EntropyViolationWarning(Warning):
    """熵违警告"""
    pass


class ThermodynamicLaw:
    """热力学定律模拟"""
    
    @staticmethod
    def calculate_entropy(system_state: Dict) -> float:
        """计算系统熵值"""
        # 基于信息论的熵计算：H = -Σ p(x) log p(x)
        if not system_state:
            return 0.0
            
        # 提取概率分布（简化模型）
        probabilities = []
        
        # 状态多样性贡献熵
        state_diversity = len(system_state) / 100.0  # 状态数量标准化
        
        # 状态均匀性贡献熵
        if 'state_distribution' in system_state:
            dist = system_state['state_distribution']
            if isinstance(dist, dict) and dist:
                probs = np.array(list(dist.values()))
                probs = probs / probs.sum()  # 归一化
                entropy = -np.sum(probs * np.log2(probs + 1e-10))  # 避免log(0)
                return entropy * state_diversity
        
        # 默认基于随机性和复杂度的熵估计
        randomness = system_state.get('randomness_factor', 0.5)
        complexity = system_state.get('complexity', 0.3)
        
        return (randomness + complexity) * state_diversity
    
    @staticmethod
    def entropy_gradient(system_state: Dict, delta: float = 0.01) -> Dict[str, float]:
        """计算熵梯度（各参数对熵的影响）"""
        base_entropy = ThermodynamicLaw.calculate_entropy(system_state)
        gradients = {}
        
        # 对每个可调参数计算梯度
        for key in ['randomness_factor', 'complexity', 'order_parameter']:
            if key in system_state:
                perturbed_state = system_state.copy()
                perturbed_state[key] += delta
                new_entropy = ThermodynamicLaw.calculate_entropy(perturbed_state)
                gradients[key] = (new_entropy - base_entropy) / delta
        
        return gradients
    
    @staticmethod
    def maxwell_demon_operation(system_state: Dict, energy_cost: float) -> Dict:
        """麦克斯韦妖操作：消耗能量减少熵"""
        base_entropy = ThermodynamicLaw.calculate_entropy(system_state)
        
        if energy_cost <= 0:
            return system_state
            
        # 能量转换效率（逆熵效率）
        efficiency = min(0.9, energy_cost * 0.1)  # 最高90%效率
        
        # 计算可减少的熵
        entropy_reduction = base_entropy * efficiency
        
        # 创建新的低熵状态
        new_state = system_state.copy()
        new_state['randomness_factor'] = max(0.1, new_state.get('randomness_factor', 0.5) - efficiency * 0.3)
        new_state['complexity'] = max(0.1, new_state.get('complexity', 0.3) - efficiency * 0.2)
        new_state['order_parameter'] = new_state.get('order_parameter', 0.2) + efficiency * 0.4
        new_state['entropy'] = ThermodynamicLaw.calculate_entropy(new_state)
        new_state['energy_consumed'] = energy_cost
        new_state['entropy_reduction'] = entropy_reduction
        
        return new_state


class NegativeEntropyEngine:
    """逆熵引擎核心"""
    
    def __init__(self):
        self.entropy_level = 0.7  # 当前熵水平 (0-1)
        self.negative_entropy_buffer = 0.0  # 负熵储备
        self.max_negative_entropy = 1.0  # 最大负熵容量
        self.energy_efficiency = 0.3  # 能量转换效率
        self.time_reversal_capability = 0.0  # 时间逆流能力
        self.causal_restructuring_level = 0.0  # 因果重构水平
        
        # 逆熵操作记录
        self.entropy_reduction_log = deque(maxlen=1000)
        
    def generate_negative_entropy(self, energy_input: float) -> float:
        """生成负熵（消耗能量创建秩序）"""
        if energy_input <= 0:
            return 0.0
            
        # 能量到负熵的转换（受效率限制）
        negative_entropy_generated = energy_input * self.energy_efficiency
        
        # 热力学限制：不能超过最大容量
        actual_generation = min(negative_entropy_generated, 
                               self.max_negative_entropy - self.negative_entropy_buffer)
        
        if actual_generation > 0:
            self.negative_entropy_buffer += actual_generation
            self.entropy_level = max(0.0, self.entropy_level - actual_generation * 0.1)
            
            # 记录操作
            self.entropy_reduction_log.append({
                'timestamp': datetime.datetime.now(),
                'energy_input': energy_input,
                'negative_entropy_generated': actual_generation,
                'entropy_reduction': actual_generation * 0.1
            })
        
        return actual_generation
    
    def apply_negative_entropy(self, system_state: Dict, negative_entropy_amount: float) -> Dict:
        """应用负熵到系统状态"""
        if negative_entropy_amount <= 0 or self.negative_entropy_buffer <= 0:
            return system_state
            
        # 确定实际可用的负熵
        usable_entropy = min(negative_entropy_amount, self.negative_entropy_buffer)
        
        # 应用麦克斯韦妖操作
        new_state = ThermodynamicLaw.maxwell_demon_operation(system_state, usable_entropy)
        
        # 消耗负熵
        self.negative_entropy_buffer -= usable_entropy
        
        # 更新逆流能力（基于累计负熵应用）
        self.time_reversal_capability += usable_entropy * 0.01
        self.causal_restructuring_level += usable_entropy * 0.005
        
        return new_state
    
    def partial_time_reversal(self, timeline_data: Dict, reversal_strength: float) -> Dict:
        """部分时间逆流"""
        if reversal_strength <= 0 or self.time_reversal_capability < reversal_strength:
            raise NegativeEntropyException("时间逆流能力不足")
            
        # 消耗逆流能力
        self.time_reversal_capability -= reversal_strength
        
        # 创建时间逆流效果
        reversed_timeline = timeline_data.copy()
        
        # 逆序事件（部分逆序，基于强度）
        events = reversed_timeline.get('events', [])
        if events:
            # 计算要逆序的事件数量
            reversal_count = int(len(events) * reversal_strength)
            
            # 部分逆序
            if reversal_count > 0:
                # 选择要逆序的事件段
                start_idx = max(0, len(events) - reversal_count)
                segment = events[start_idx:]
                
                # 逆序并更新时间戳
                reversed_segment = list(reversed(segment))
                base_time = events[start_idx - 1]['timestamp'] if start_idx > 0 else 0
                
                for i, event in enumerate(reversed_segment):
                    event['timestamp'] = base_time + i * 10  # 重新分配时间戳
                    event['reversed'] = True  # 标记为逆序事件
                
                # 替换原事件段
                reversed_timeline['events'][start_idx:] = reversed_segment
        
        reversed_timeline['reversal_strength'] = reversal_strength
        reversed_timeline['reversal_timestamp'] = datetime.datetime.now()
        
        return reversed_timeline
    
    def causal_restructuring(self, causal_network: Dict, restructuring_strength: float) -> Dict:
        """因果重构"""
        if restructuring_strength <= 0 or self.causal_restructuring_level < restructuring_strength:
            raise NegativeEntropyException("因果重构能力不足")
            
        # 消耗重构能力
        self.causal_restructuring_level -= restructuring_strength
        
        # 创建新的因果网络
        new_causal_network = causal_network.copy()
        
        # 因果优化：减少因果环和矛盾
        if 'causal_links' in new_causal_network:
            links = new_causal_network['causal_links']
            
            # 检测并修复因果环
            causal_cycles = self.detect_causal_cycles(links)
            for cycle in causal_cycles:
                # 随机断开环中的一个连接（基于强度决定断开数量）
                if random.random() < restructuring_strength:
                    if cycle:
                        link_to_remove = random.choice(cycle)
                        if link_to_remove in links:
                            links.remove(link_to_network)
            
            # 优化因果密度（基于强度调整连接数量）
            target_density = 0.3 + restructuring_strength * 0.4  # 目标因果密度
            current_density = len(links) / max(1, len(set([l['source'] for l in links])))
            
            if current_density > target_density:
                # 减少连接数量
                excess_links = int(len(links) * (current_density - target_density))
                for _ in range(min(excess_links, len(links))):
                    if links:
                        links.pop(random.randint(0, len(links) - 1))
        
        new_causal_network['restructuring_strength'] = restructuring_strength
        new_causal_network['restructuring_timestamp'] = datetime.datetime.now()
        
        return new_causal_network
    
    def detect_causal_cycles(self, causal_links: List[Dict]) -> List[List[str]]:
        """检测因果环"""
        # 创建有向图
        graph = {}
        for link in causal_links:
            source = link.get('source')
            target = link.get('target')
            if source not in graph:
                graph[source] = []
            graph[source].append(target)
        
        # 简单环检测（简化实现）
        cycles = []
        visited = set()
        
        def dfs(node, path):
            if node in path:
                # 找到环
                cycle_start = path.index(node)
                cycles.append(path[cycle_start:] + [node])
                return
            if node in visited:
                return
                
            visited.add(node)
            path.append(node)
            
            for neighbor in graph.get(node, []):
                dfs(neighbor, path.copy())
        
        for node in graph:
            dfs(node, [])
            
        return cycles


class InformationReorganizer:
    """信息重组器（逆熵信息处理）"""
    
    def __init__(self):
        self.pattern_recognition_threshold = 0.7
        self.information_compression_ratio = 0.0
        self.meaning_extraction_efficiency = 0.5
        
    def reorganize_information(self, information_stream: List[Dict], negative_entropy: float) -> Dict:
        """重组信息流（应用负熵增加信息有序性）"""
        if not information_stream:
            return {"reorganized": [], "compression_ratio": 0.0, "order_increase": 0.0}
        
        # 计算原始信息熵
        original_entropy = self.calculate_information_entropy(information_stream)
        
        # 应用负熵进行重组
        reorganization_strength = min(1.0, negative_entropy * 2.0)
        
        # 模式识别和分类
        categorized_info = self.categorize_information(information_stream, reorganization_strength)
        
        # 信息压缩
        compressed_info = self.compress_information(categorized_info, reorganization_strength)
        
        # 意义提取
        meaningful_patterns = self.extract_meaningful_patterns(compressed_info, reorganization_strength)
        
        # 计算重组后的熵
        reorganized_entropy = self.calculate_information_entropy(meaningful_patterns)
        order_increase = max(0, original_entropy - reorganized_entropy)
        
        return {
            "reorganized": meaningful_patterns,
            "compression_ratio": len(meaningful_patterns) / max(1, len(information_stream)),
            "order_increase": order_increase,
            "original_entropy": original_entropy,
            "final_entropy": reorganized_entropy
        }
    
    def calculate_information_entropy(self, information: List[Dict]) -> float:
        """计算信息熵"""
        if not information:
            return 0.0
            
        # 基于信息多样性和重复度计算熵
        info_types = defaultdict(int)
        total_items = len(information)
        
        for item in information:
            item_type = item.get('type', 'unknown')
            info_types[item_type] += 1
        
        # 计算概率分布
        probabilities = [count / total_items for count in info_types.values()]
        
        # 香农熵
        entropy = -sum(p * math.log2(p) for p in probabilities if p > 0)
        
        return entropy
    
    def categorize_information(self, information: List[Dict], strength: float) -> Dict[str, List]:
        """信息分类"""
        categories = defaultdict(list)
        
        for item in information:
            # 基于相似性分类
            category = self.determine_category(item, strength)
            categories[category].append(item)
        
        return dict(categories)
    
    def determine_category(self, item: Dict, strength: float) -> str:
        """确定信息类别"""
        # 简化分类逻辑
        item_type = item.get('type', 'unknown')
        content = str(item.get('content', ''))
        
        # 基于强度进行更精细的分类
        if strength > 0.5:
            # 高强度下进行细粒度分类
            if len(content) > 50:
                return f"detailed_{item_type}"
            else:
                return f"brief_{item_type}"
        else:
            return item_type
    
    def compress_information(self, categorized_info: Dict, strength: float) -> List[Dict]:
        """信息压缩"""
        compressed = []
        
        for category, items in categorized_info.items():
            if strength > 0.3:
                # 应用压缩算法（简化）
                representative_item = self.select_representative(items, strength)
                compressed.append({
                    'category': category,
                    'representative': representative_item,
                    'item_count': len(items),
                    'compression_strength': strength
                })
            else:
                # 低强度下保持原样
                compressed.extend(items)
        
        return compressed
    
    def select_representative(self, items: List[Dict], strength: float) -> Dict:
        """选择代表性信息"""
        if not items:
            return {}
            
        # 基于强度选择策略
        if strength > 0.7:
            # 高强度：选择最独特的信息
            return max(items, key=lambda x: len(str(x.get('content', ''))))
        elif strength > 0.4:
            # 中强度：选择最新信息
            return items[-1] if items else {}
        else:
            # 低强度：随机选择
            return random.choice(items) if items else {}
    
    def extract_meaningful_patterns(self, information: List[Dict], strength: float) -> List[Dict]:
        """提取有意义模式"""
        patterns = []
        
        for item in information:
            if strength > 0.6:
                # 高强度模式提取
                pattern = self.analyze_pattern(item, strength)
                if pattern:
                    patterns.append(pattern)
            else:
                # 低强度下保持原信息
                patterns.append(item)
        
        return patterns
    
    def analyze_pattern(self, item: Dict, strength: float) -> Dict:
        """分析信息模式"""
        content = str(item.get('content', ''))
        
        # 简化模式分析
        pattern_info = {
            'type': 'extracted_pattern',
            'original_content': content[:100] + '...' if len(content) > 100 else content,
            'pattern_signature': hashlib.md5(content.encode()).hexdigest()[:8],
            'complexity': min(1.0, len(content) / 1000.0),
            'extraction_strength': strength
        }
        
        return pattern_info


class TemporalCrystal:
    """时间晶体（永动时间结构）"""
    
    def __init__(self, dimensionality: int = 4):
        self.dimensionality = dimensionality  # 时间晶体维度
        self.phase_coherence = 0.0  # 相位相干性
        self.temporal_periodicity = 1.0  # 时间周期性
        self.spontaneous_symmetry_breaking = False  # 自发对称性破缺
        self.energy_self_sustaining_level = 0.0  # 能量自持水平
        
    def initialize_crystal(self, initial_energy: float):
        """初始化时间晶体"""
        if initial_energy <= 0:
            raise NegativeEntropyException("初始化能量必须为正")
            
        self.phase_coherence = min(1.0, initial_energy * 0.1)
        self.temporal_periodicity = 1.0 + initial_energy * 0.05
        
        # 能量自持条件
        if initial_energy > 0.5:
            self.energy_self_sustaining_level = min(1.0, (initial_energy - 0.5) * 0.8)
            if initial_energy > 0.8:
                self.spontaneous_symmetry_breaking = True
    
    def evolve_crystal(self, time_steps: int, external_entropy: float = 0.0) -> Dict:
        """演化时间晶体"""
        results = {
            'phase_coherence_changes': [],
            'energy_fluctuations': [],
            'temporal_patterns': []
        }
        
        for step in range(time_steps):
            # 时间晶体动力学方程（简化）
            phase_change = self.calculate_phase_dynamics(step, external_entropy)
            energy_fluctuation = self.calculate_energy_fluctuation(step)
            temporal_pattern = self.generate_temporal_pattern(step)
            
            results['phase_coherence_changes'].append(phase_change)
            results['energy_fluctuations'].append(energy_fluctuation)
            results['temporal_patterns'].append(temporal_pattern)
            
            # 更新晶体状态
            self.update_crystal_state(phase_change, energy_fluctuation)
        
        return results
    
    def calculate_phase_dynamics(self, time_step: int, external_entropy: float) -> float:
        """计算相位动力学"""
        # 简化的时间晶体相位方程
        base_oscillation = math.sin(2 * math.pi * time_step / self.temporal_periodicity)
        entropy_effect = external_entropy * 0.1 * random.uniform(-1, 1)
        
        phase_change = base_oscillation * self.phase_coherence + entropy_effect
        return max(-1.0, min(1.0, phase_change))
    
    def calculate_energy_fluctuation(self, time_step: int) -> float:
        """计算能量涨落"""
        if self.energy_self_sustaining_level > 0:
            # 自持能量涨落
            base_energy = self.energy_self_sustaining_level
            fluctuation = math.sin(time_step * 0.5) * 0.1 * base_energy
            return base_energy + fluctuation
        else:
            # 衰减能量
            return max(0, 0.5 - time_step * 0.01)
    
    def generate_temporal_pattern(self, time_step: int) -> Dict:
        """生成时间模式"""
        pattern_complexity = min(1.0, self.phase_coherence * (1 + time_step * 0.01))
        
        return {
            'time_step': time_step,
            'pattern_type': 'temporal_crystal',
            'complexity': pattern_complexity,
            'symmetry_broken': self.spontaneous_symmetry_breaking,
            'dimensionality': self.dimensionality
        }
    
    def update_crystal_state(self, phase_change: float, energy_fluctuation: float):
        """更新晶体状态"""
        # 相位相干性更新
        self.phase_coherence = max(0.0, min(1.0, 
            self.phase_coherence + phase_change * 0.01))
        
        # 能量自持水平更新
        if self.energy_self_sustaining_level > 0:
            self.energy_self_sustaining_level = max(0.0, 
                self.energy_self_sustaining_level + energy_fluctuation * 0.001 - 0.0001)
        
        # 周期性调整
        self.temporal_periodicity = max(0.1, self.temporal_periodicity + random.uniform(-0.01, 0.01))


class EntropyVisualizationWidget(QGraphicsView):
    """熵可视化组件"""
    
    entropyLevelChanged = pyqtSignal(float)
    negativeEntropyGenerated = pyqtSignal(float)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.entropy_engine = NegativeEntropyEngine()
        self.current_entropy = 0.7
        self.target_entropy = 0.3
        self.visualization_mode = "thermodynamic"  # thermodynamic, information, temporal
        
        self.init_ui()
        
    def init_ui(self):
        """初始化UI"""
        self.scene = QGraphicsScene()
        self.setScene(self.scene)
        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.RubberBandDrag)
        
    def set_entropy_level(self, entropy: float):
        """设置熵水平"""
        self.current_entropy = max(0.0, min(1.0, entropy))
        self.render_entropy_visualization()
        self.entropyLevelChanged.emit(self.current_entropy)
        
    def generate_negative_entropy(self, energy: float):
        """生成负熵"""
        generated = self.entropy_engine.generate_negative_entropy(energy)
        self.negativeEntropyGenerated.emit(generated)
        self.render_entropy_visualization()
        
    def render_entropy_visualization(self):
        """渲染熵可视化"""
        self.scene.clear()
        
        if self.visualization_mode == "thermodynamic":
            self.render_thermodynamic_view()
        elif self.visualization_mode == "information":
            self.render_information_view()
        elif self.visualization_mode == "temporal":
            self.render_temporal_view()
            
    def render_thermodynamic_view(self):
        """渲染热力学视图"""
        # 绘制熵计
        self.draw_entropy_gauge()
        
        # 绘制负熵储备
        self.draw_negative_entropy_storage()
        
        # 绘制能量流
        self.draw_energy_flow()
        
    def draw_entropy_gauge(self):
        """绘制熵计量器"""
        # 熵计背景
        gauge_rect = QGraphicsRectItem(50, 50, 200, 30)
        gauge_rect.setBrush(QBrush(QColor(200, 200, 200)))
        gauge_rect.setPen(QPen(Qt.black, 2))
        self.scene.addItem(gauge_rect)
        
        # 当前熵水平
        entropy_width = 200 * self.current_entropy
        entropy_bar = QGraphicsRectItem(50, 50, entropy_width, 30)
        
        # 熵颜色渐变（低熵=蓝色，高熵=红色）
        entropy_color = QColor(
            int(255 * self.current_entropy),
            int(100 * (1 - self.current_entropy)),
            int(255 * (1 - self.current_entropy))
        )
        entropy_bar.setBrush(QBrush(entropy_color))
        entropy_bar.setPen(QPen(Qt.black, 1))
        self.scene.addItem(entropy_bar)
        
        # 熵标签
        entropy_label = QGraphicsTextItem(f"熵: {self.current_entropy:.3f}")
        entropy_label.setPos(260, 50)
        self.scene.addItem(entropy_label)
        
    def draw_negative_entropy_storage(self):
        """绘制负熵储备"""
        negative_entropy = self.entropy_engine.negative_entropy_buffer
        max_capacity = self.entropy_engine.max_negative_entropy
        
        # 储备罐
        tank_rect = QGraphicsRectItem(50, 100, 100, 150)
        tank_rect.setBrush(QBrush(QColor(240, 240, 240)))
        tank_rect.setPen(QPen(Qt.black, 2))
        self.scene.addItem(tank_rect)
        
        # 负熵液体
        liquid_height = 150 * (negative_entropy / max_capacity)
        liquid_rect = QGraphicsRectItem(50, 100 + (150 - liquid_height), 100, liquid_height)
        
        # 负熵颜色（秩序之色）
        negative_entropy_color = QColor(100, 200, 255, 180)
        liquid_rect.setBrush(QBrush(negative_entropy_color))
        liquid_rect.setPen(QPen(Qt.blue, 1))
        self.scene.addItem(liquid_rect)
        
        # 标签
        ne_label = QGraphicsTextItem(f"负熵: {negative_entropy:.3f}")
        ne_label.setPos(160, 100)
        self.scene.addItem(ne_label)
        
    def draw_energy_flow(self):
        """绘制能量流"""
        # 能量输入箭头
        energy_flow = QGraphicsLineItem(200, 200, 300, 150)
        energy_flow.setPen(QPen(QColor(255, 200, 0), 3))
        self.scene.addItem(energy_flow)
        
        # 能量标签
        energy_label = QGraphicsTextItem("能量输入")
        energy_label.setPos(310, 140)
        self.scene.addItem(energy_label)
        
    def render_information_view(self):
        """渲染信息视图"""
        # 绘制信息熵云图
        self.draw_information_cloud()
        
        # 绘制信息重组过程
        self.draw_information_reorganization()
        
    def draw_information_cloud(self):
        """绘制信息云"""
        # 基于熵值确定云的混乱程度
        chaos_level = self.current_entropy
        
        # 生成随机信息点
        num_points = int(50 + chaos_level * 100)
        for i in range(num_points):
            x = random.randint(50, 400)
            y = random.randint(50, 300)
            
            # 点的大小和颜色基于熵
            size = 3 + chaos_level * 5
            color_value = int(255 * chaos_level)
            
            point = QGraphicsEllipseItem(x, y, size, size)
            point.setBrush(QBrush(QColor(color_value, color_value, color_value)))
            point.setPen(QPen(Qt.NoPen))
            self.scene.addItem(point)
            
    def draw_information_reorganization(self):
        """绘制信息重组"""
        # 重组效率指示器
        efficiency = 1.0 - self.current_entropy
        
        # 绘制从混乱到有序的转变
        for i in range(5):
            x = 450 + i * 60
            y = 100
            
            # 秩序级别递增
            order_level = efficiency * (i / 4.0)
            
            # 绘制有序结构
            self.draw_ordered_structure(x, y, order_level)
            
    def draw_ordered_structure(self, x: float, y: float, order: float):
        """绘制有序结构"""
        size = 40 * (0.5 + order * 0.5)
        
        if order > 0.7:
            # 高秩序：晶体结构
            self.draw_crystal_structure(x, y, size, order)
        elif order > 0.3:
            # 中秩序：网格结构
            self.draw_grid_structure(x, y, size, order)
        else:
            # 低秩序：随机点
            self.draw_random_structure(x, y, size, order)
            
    def draw_crystal_structure(self, x: float, y: float, size: float, order: float):
        """绘制晶体结构"""
        # 六边形晶体
        hexagon = QGraphicsPolygonItem()
        points = []
        for i in range(6):
            angle = 2 * math.pi * i / 6
            px = x + size * math.cos(angle)
            py = y + size * math.sin(angle)
            points.append(QPointF(px, py))
        
        hexagon.setPolygon(QPolygonF(points))
        hexagon.setBrush(QBrush(QColor(100, 200, 255, int(200 * order))))
        hexagon.setPen(QPen(QColor(0, 100, 200), 2))
        self.scene.addItem(hexagon)
        
    def render_temporal_view(self):
        """渲染时间视图"""
        # 绘制时间流箭头
        self.draw_time_flow()
        
        # 绘制时间晶体结构
        self.draw_temporal_crystal()
        
    def draw_time_flow(self):
        """绘制时间流"""
        # 正常时间流
        normal_time = QGraphicsLineItem(50, 200, 250, 200)
        normal_time.setPen(QPen(QColor(0, 0, 255), 2))
        self.add_arrow_head(normal_time, QColor(0, 0, 255))
        self.scene.addItem(normal_time)
        
        # 逆熵时间流（如果熵足够低）
        if self.current_entropy < 0.5:
            reversed_time = QGraphicsLineItem(250, 250, 50, 250)
            reversed_time.setPen(QPen(QColor(255, 0, 0), 2))
            self.add_arrow_head(reversed_time, QColor(255, 0, 0), reversed=True)
            self.scene.addItem(reversed_time)
            
            # 逆流标签
            label = QGraphicsTextItem("逆熵时间流")
            label.setPos(30, 230)
            self.scene.addItem(label)
        
        # 正常时间流标签
        label = QGraphicsTextItem("正常时间流")
        label.setPos(260, 190)
        self.scene.addItem(label)
        
    def draw_temporal_crystal(self):
        """绘制时间晶体"""
        if self.current_entropy < 0.4:
            # 只在低熵下显示时间晶体
            crystal = TemporalCrystal()
            crystal.initialize_crystal(1.0 - self.current_entropy)
            
            # 绘制晶体结构
            x, y = 350, 150
            size = 80
            
            # 多维晶体表示
            for i in range(4):  # 4维表示
                angle = math.pi * i / 2
                radius = size * (0.3 + i * 0.2)
                
                circle = QGraphicsEllipseItem(x - radius, y - radius, radius * 2, radius * 2)
                circle.setPen(QPen(QColor(200, 100, 255, 100 + i * 30), 1))
                circle.setBrush(QBrush(Qt.NoBrush))
                self.scene.addItem(circle)
                
    def add_arrow_head(self, line_item: QGraphicsLineItem, color: QColor, reversed: bool = False):
        """添加箭头"""
        line = line_item.line()
        angle = math.atan2(line.dy(), line.dx())
        
        if reversed:
            angle += math.pi  # 反转方向
            
        arrow_size = 10
        arrow_p1 = line.p2() - QPointF(math.cos(angle - math.pi/6) * arrow_size, 
                                      math.sin(angle - math.pi/6) * arrow_size)
        arrow_p2 = line.p2() - QPointF(math.cos(angle + math.pi/6) * arrow_size, 
                                      math.sin(angle + math.pi/6) * arrow_size)
        
        arrow_head = QGraphicsPolygonItem()
        arrow_head.setPolygon(QPolygonF([line.p2(), arrow_p1, arrow_p2]))
        arrow_head.setBrush(QBrush(color))
        
        self.scene.addItem(arrow_head)

    def draw_ordered_structure(self, x: float, y: float, order: float):
        """绘制有序结构"""
        size = 40 * (0.5 + order * 0.5)
        
        if order > 0.7:
            # 高秩序：晶体结构
            self.draw_crystal_structure(x, y, size, order)
        elif order > 0.3:
            # 中秩序：网格结构
            self.draw_grid_structure(x, y, size, order)
        else:
            # 低秩序：随机点
            self.draw_random_structure(x, y, size, order)

    def draw_random_structure(self, x: float, y: float, size: float, order: float):
        """绘制随机结构（低秩序）"""
        # 创建一组随机分布的点
        num_points = int(10 + (1 - order) * 20)  # 秩序越低，点越多越随机
        
        for i in range(num_points):
            # 在指定区域内随机分布
            px = x + random.uniform(-size/2, size/2)
            py = y + random.uniform(-size/2, size/2)
            
            # 点的大小和颜色基于秩序程度
            point_size = 2 + (1 - order) * 3
            gray_value = int(150 + (1 - order) * 105)
            
            point = QGraphicsEllipseItem(px, py, point_size, point_size)
            point.setBrush(QBrush(QColor(gray_value, gray_value, gray_value)))
            point.setPen(QPen(Qt.NoPen))
            self.scene.addItem(point)

    def draw_grid_structure(self, x: float, y: float, size: float, order: float):
        """绘制网格结构（中秩序）"""
        # 计算网格参数
        grid_size = max(5, int(10 * (1 - order)))  # 秩序越高，网格越精细
        cell_size = size / grid_size
        
        # 绘制网格线
        for i in range(grid_size + 1):
            # 水平线
            h_line = QGraphicsLineItem(x - size/2, y - size/2 + i * cell_size, 
                                    x + size/2, y - size/2 + i * cell_size)
            # 垂直线
            v_line = QGraphicsLineItem(x - size/2 + i * cell_size, y - size/2,
                                    x - size/2 + i * cell_size, y + size/2)
            
            # 设置线条样式
            line_pen = QPen(QColor(100, 150, 200, int(150 + order * 105)))
            line_pen.setWidthF(0.5 + order * 1.5)
            
            h_line.setPen(line_pen)
            v_line.setPen(line_pen)
            
            self.scene.addItem(h_line)
            self.scene.addItem(v_line)
        
        # 在网格交点处添加点
        for i in range(grid_size + 1):
            for j in range(grid_size + 1):
                px = x - size/2 + i * cell_size
                py = y - size/2 + j * cell_size
                
                dot_size = 2 + order * 3
                dot = QGraphicsEllipseItem(px - dot_size/2, py - dot_size/2, 
                                        dot_size, dot_size)
                dot.setBrush(QBrush(QColor(50, 120, 200)))
                dot.setPen(QPen(Qt.NoPen))
                self.scene.addItem(dot)
                
class NegativeEntropyControlPanel(QWidget):
    """逆熵控制面板"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.entropy_engine = NegativeEntropyEngine()
        self.info_reorganizer = InformationReorganizer()
        self.temporal_crystal = TemporalCrystal()
        
        self.init_ui()
        
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout()
        
        # 标题
        title = QLabel("逆熵控制系统")
        title.setAlignment(Qt.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)
        
        # 熵状态显示
        entropy_group = QGroupBox("熵状态监控")
        entropy_layout = QVBoxLayout()
        
        self.entropy_bar = QProgressBar()
        self.entropy_bar.setFormat("系统熵值: %p%")
        entropy_layout.addWidget(self.entropy_bar)
        
        self.negative_entropy_label = QLabel("负熵储备: 0.000")
        entropy_layout.addWidget(self.negative_entropy_label)
        
        self.time_reversal_label = QLabel("时间逆流能力: 0.000")
        entropy_layout.addWidget(self.time_reversal_label)
        
        entropy_group.setLayout(entropy_layout)
        layout.addWidget(entropy_group)
        
        # 能量输入控制
        energy_group = QGroupBox("能量输入")
        energy_layout = QVBoxLayout()
        
        self.energy_slider = QSlider(Qt.Horizontal)
        self.energy_slider.setRange(1, 100)
        self.energy_slider.setValue(10)
        energy_layout.addWidget(QLabel("能量输入级别:"))
        energy_layout.addWidget(self.energy_slider)
        
        self.generate_btn = QPushButton("生成负熵")
        self.generate_btn.clicked.connect(self.generate_negative_entropy)
        energy_layout.addWidget(self.generate_btn)
        
        energy_group.setLayout(energy_layout)
        layout.addWidget(energy_group)
        
        # 逆熵应用控制
        application_group = QGroupBox("逆熵应用")
        application_layout = QVBoxLayout()
        
        self.application_mode = QComboBox()
        self.application_mode.addItems(["时间逆流", "因果重构", "信息重组", "秩序创造"])
        application_layout.addWidget(QLabel("应用模式:"))
        application_layout.addWidget(self.application_mode)
        
        self.strength_slider = QSlider(Qt.Horizontal)
        self.strength_slider.setRange(1, 100)
        self.strength_slider.setValue(20)
        application_layout.addWidget(QLabel("应用强度:"))
        application_layout.addWidget(self.strength_slider)
        
        self.apply_btn = QPushButton("应用逆熵")
        self.apply_btn.clicked.connect(self.apply_negative_entropy)
        application_layout.addWidget(self.apply_btn)
        
        application_group.setLayout(application_layout)
        layout.addWidget(application_group)
        
        # 时间晶体控制
        crystal_group = QGroupBox("时间晶体")
        crystal_layout = QVBoxLayout()
        
        self.crystal_energy = QDoubleSpinBox()
        self.crystal_energy.setRange(0.1, 10.0)
        self.crystal_energy.setValue(1.0)
        crystal_layout.addWidget(QLabel("初始化能量:"))
        crystal_layout.addWidget(self.crystal_energy)
        
        self.init_crystal_btn = QPushButton("初始化时间晶体")
        self.init_crystal_btn.clicked.connect(self.initialize_temporal_crystal)
        crystal_layout.addWidget(self.init_crystal_btn)
        
        self.evolve_steps = QSpinBox()
        self.evolve_steps.setRange(1, 1000)
        self.evolve_steps.setValue(100)
        crystal_layout.addWidget(QLabel("演化步数:"))
        crystal_layout.addWidget(self.evolve_steps)
        
        self.evolve_btn = QPushButton("演化时间晶体")
        self.evolve_btn.clicked.connect(self.evolve_temporal_crystal)
        crystal_layout.addWidget(self.evolve_btn)
        
        crystal_group.setLayout(crystal_layout)
        layout.addWidget(crystal_group)
        
        layout.addStretch(1)
        self.setLayout(layout)
        
        # 初始化状态
        self.update_display()
        
    def generate_negative_entropy(self):
        """生成负熵"""
        energy_level = self.energy_slider.value() / 100.0
        generated = self.entropy_engine.generate_negative_entropy(energy_level)
        
        QMessageBox.information(self, "负熵生成", 
                               f"已生成负熵: {generated:.4f}\n"
                               f"消耗能量: {energy_level:.2f}")
        
        self.update_display()
        
    def apply_negative_entropy(self):
        """应用负熵"""
        mode = self.application_mode.currentText()
        strength = self.strength_slider.value() / 100.0
        
        try:
            if mode == "时间逆流":
                # 模拟时间逆流应用
                result = self.entropy_engine.partial_time_reversal({}, strength)
                QMessageBox.information(self, "时间逆流", 
                                       f"时间逆流强度: {strength:.2f}\n"
                                       f"逆流事件数: {len(result.get('events', []))}")
                
            elif mode == "因果重构":
                # 模拟因果重构
                result = self.entropy_engine.causal_restructuring({}, strength)
                QMessageBox.information(self, "因果重构", 
                                       f"重构强度: {strength:.2f}\n"
                                       f"因果优化完成")
                
            elif mode == "信息重组":
                # 模拟信息重组
                sample_info = [{"type": "data", "content": f"信息块{i}"} for i in range(10)]
                result = self.info_reorganizer.reorganize_information(sample_info, strength)
                QMessageBox.information(self, "信息重组", 
                                       f"重组强度: {strength:.2f}\n"
                                       f"信息压缩比: {result.get('compression_ratio', 0):.2f}")
                
            elif mode == "秩序创造":
                # 模拟秩序创造
                QMessageBox.information(self, "秩序创造", 
                                       f"秩序创造强度: {strength:.2f}\n"
                                       f"系统有序度提升")
                                       
            self.update_display()
            
        except NegativeEntropyException as e:
            QMessageBox.warning(self, "逆熵应用失败", str(e))
            
    def initialize_temporal_crystal(self):
        """初始化时间晶体"""
        energy = self.crystal_energy.value()
        
        try:
            self.temporal_crystal.initialize_crystal(energy)
            QMessageBox.information(self, "时间晶体初始化", 
                                   f"初始化能量: {energy:.2f}\n"
                                   f"相位相干性: {self.temporal_crystal.phase_coherence:.3f}\n"
                                   f"能量自持: {self.temporal_crystal.energy_self_sustaining_level:.3f}")
        except NegativeEntropyException as e:
            QMessageBox.warning(self, "晶体初始化失败", str(e))
            
    def evolve_temporal_crystal(self):
        """演化时间晶体"""
        steps = self.evolve_steps.value()
        
        if self.temporal_crystal.phase_coherence == 0:
            QMessageBox.warning(self, "晶体未初始化", "请先初始化时间晶体")
            return
            
        results = self.temporal_crystal.evolve_crystal(steps)
        
        QMessageBox.information(self, "时间晶体演化", 
                               f"演化步数: {steps}\n"
                               f"生成模式数: {len(results.get('temporal_patterns', []))}\n"
                               f"最终相干性: {self.temporal_crystal.phase_coherence:.3f}")
                               
    def update_display(self):
        """更新显示"""
        # 更新熵值显示
        entropy_level = self.entropy_engine.entropy_level
        self.entropy_bar.setValue(int(entropy_level * 100))
        
        # 更新负熵储备
        negative_entropy = self.entropy_engine.negative_entropy_buffer
        self.negative_entropy_label.setText(f"负熵储备: {negative_entropy:.3f}")
        
        # 更新时间逆流能力
        time_reversal = self.entropy_engine.time_reversal_capability
        self.time_reversal_label.setText(f"时间逆流能力: {time_reversal:.3f}")


class NegativeEntropySystem(QMainWindow):
    """逆熵系统主界面"""
    
    def __init__(self):
        super().__init__()
        self.entropy_engine = NegativeEntropyEngine()
        self.info_reorganizer = InformationReorganizer()
        self.temporal_crystals = []  # 时间晶体列表
        
        self.init_ui()
        self.load_settings()
        
    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("逆熵时光系统 - 负熵时间流与因果重构")
        self.setGeometry(50, 50, 1400, 900)
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QHBoxLayout()
        central_widget.setLayout(main_layout)
        
        # 左侧控制面板
        left_panel = QFrame()
        left_layout = QVBoxLayout()
        
        self.control_panel = NegativeEntropyControlPanel()
        left_layout.addWidget(self.control_panel)
        
        left_panel.setLayout(left_layout)
        main_layout.addWidget(left_panel, 1)
        
        # 右侧可视化区域
        right_panel = QFrame()
        right_layout = QVBoxLayout()
        
        # 可视化模式选择
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("可视化模式:"))
        
        self.viz_mode = QComboBox()
        self.viz_mode.addItems(["热力学视图", "信息视图", "时间视图"])
        self.viz_mode.currentTextChanged.connect(self.change_visualization_mode)
        mode_layout.addWidget(self.viz_mode)
        
        mode_layout.addStretch(1)
        right_layout.addLayout(mode_layout)
        
        # 熵可视化组件
        self.entropy_viz = EntropyVisualizationWidget()
        right_layout.addWidget(self.entropy_viz, 1)
        
        # 连接信号
        self.entropy_viz.entropyLevelChanged.connect(self.on_entropy_changed)
        self.entropy_viz.negativeEntropyGenerated.connect(self.on_negative_entropy_generated)
        
        right_panel.setLayout(right_layout)
        main_layout.addWidget(right_panel, 2)
        
        # 创建菜单栏
        self.create_menus()
        
        # 创建状态栏
        self.statusBar().showMessage("逆熵系统已就绪 - 当前熵值: 0.700")
        
        # 初始可视化
        self.entropy_viz.set_entropy_level(self.entropy_engine.entropy_level)
        
    def create_menus(self):
        """创建菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu('文件')
        
        new_action = QAction('新逆熵项目', self)
        file_menu.addAction(new_action)
        
        save_action = QAction('保存系统状态', self)
        save_action.triggered.connect(self.save_system_state)
        file_menu.addAction(save_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction('退出', self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 操作菜单
        action_menu = menubar.addMenu('操作')
        
        maxwell_demon_action = QAction('麦克斯韦妖操作', self)
        maxwell_demon_action.triggered.connect(self.maxwell_demon_operation)
        action_menu.addAction(maxwell_demon_action)
        
        time_reversal_action = QAction('时间逆流', self)
        time_reversal_action.triggered.connect(self.time_reversal_operation)
        action_menu.addAction(time_reversal_action)
        
        causal_restructure_action = QAction('因果重构', self)
        causal_restructure_action.triggered.connect(self.causal_restructure_operation)
        action_menu.addAction(causal_restructure_action)
        
    def change_visualization_mode(self, mode_name: str):
        """更改可视化模式"""
        mode_map = {
            "热力学视图": "thermodynamic",
            "信息视图": "information", 
            "时间视图": "temporal"
        }
        
        if mode_name in mode_map:
            self.entropy_viz.visualization_mode = mode_map[mode_name]
            self.entropy_viz.render_entropy_visualization()
            
    def on_entropy_changed(self, entropy_level: float):
        """熵值变化处理"""
        self.entropy_engine.entropy_level = entropy_level
        self.statusBar().showMessage(f"逆熵系统运行中 - 当前熵值: {entropy_level:.3f}")
        
    def on_negative_entropy_generated(self, amount: float):
        """负熵生成处理"""
        self.statusBar().showMessage(f"生成负熵: {amount:.4f} - 系统秩序度提升")
        
    def maxwell_demon_operation(self):
        """麦克斯韦妖操作"""
        energy, ok = QInputDialog.getDouble(self, "麦克斯韦妖操作", 
                                          "输入操作能量:", 0.5, 0.1, 10.0, 2)
        if ok:
            # 应用麦克斯韦妖操作
            system_state = {"randomness_factor": 0.6, "complexity": 0.4}
            new_state = ThermodynamicLaw.maxwell_demon_operation(system_state, energy)
            
            entropy_reduction = new_state.get('entropy_reduction', 0)
            QMessageBox.information(self, "麦克斯韦妖操作完成",
                                  f"能量消耗: {energy:.2f}\n"
                                  f"熵减少: {entropy_reduction:.4f}\n"
                                  f"新秩序参数: {new_state.get('order_parameter', 0):.3f}")
                                  
    def time_reversal_operation(self):
        """时间逆流操作"""
        strength, ok = QInputDialog.getDouble(self, "时间逆流", 
                                            "逆流强度:", 0.3, 0.1, 1.0, 2)
        if ok:
            try:
                # 模拟时间线数据
                timeline_data = {
                    'events': [
                        {'id': f'event_{i}', 'timestamp': i * 100, 'description': f'事件{i}'}
                        for i in range(10)
                    ]
                }
                
                reversed_timeline = self.entropy_engine.partial_time_reversal(timeline_data, strength)
                
                QMessageBox.information(self, "时间逆流完成",
                                      f"逆流强度: {strength:.2f}\n"
                                      f"受影响事件: {len(reversed_timeline.get('events', []))}\n"
                                      f"逆流时间: {reversed_timeline.get('reversal_timestamp', '未知')}")
                                      
            except NegativeEntropyException as e:
                QMessageBox.warning(self, "时间逆流失败", str(e))
                
    def causal_restructure_operation(self):
        """因果重构操作"""
        strength, ok = QInputDialog.getDouble(self, "因果重构", 
                                            "重构强度:", 0.5, 0.1, 1.0, 2)
        if ok:
            try:
                # 模拟因果网络
                causal_network = {
                    'causal_links': [
                        {'source': 'cause_1', 'target': 'effect_1'},
                        {'source': 'cause_2', 'target': 'effect_2'},
                        {'source': 'effect_1', 'target': 'cause_2'}  # 形成环
                    ]
                }
                
                restructured = self.entropy_engine.causal_restructuring(causal_network, strength)
                
                QMessageBox.information(self, "因果重构完成",
                                      f"重构强度: {strength:.2f}\n"
                                      f"优化后连接数: {len(restructured.get('causal_links', []))}\n"
                                      f"重构时间: {restructured.get('restructuring_timestamp', '未知')}")
                                      
            except NegativeEntropyException as e:
                QMessageBox.warning(self, "因果重构失败", str(e))
                
    def save_system_state(self):
        """保存系统状态"""
        state = {
            'entropy_engine': {
                'entropy_level': self.entropy_engine.entropy_level,
                'negative_entropy_buffer': self.entropy_engine.negative_entropy_buffer,
                'time_reversal_capability': self.entropy_engine.time_reversal_capability
            },
            'timestamp': datetime.datetime.now().isoformat()
        }
        
        filename, _ = QFileDialog.getSaveFileName(self, "保存系统状态", "", "JSON文件 (*.json)")
        if filename:
            with open(filename, 'w') as f:
                json.dump(state, f, indent=2)
            QMessageBox.information(self, "保存成功", "系统状态已保存")
            
    def load_settings(self):
        """加载设置"""
        settings = QSettings("NegativeEntropySystem", "TimeReversal")
        geometry = settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
            
    def save_settings(self):
        """保存设置"""
        settings = QSettings("NegativeEntropySystem", "TimeReversal")
        settings.setValue("geometry", self.saveGeometry())
        
    def closeEvent(self, event):
        """关闭事件处理"""
        self.save_settings()
        
        # 检查系统状态
        if self.entropy_engine.entropy_level < 0.3:
            reply = QMessageBox.question(
                self, "低熵状态警告",
                "系统处于低熵状态，关闭可能导致秩序损失。确定要关闭吗？",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.No:
                event.ignore()
                return
                
        event.accept()


def main():
    """主函数"""
    app = QApplication(sys.argv)
    
    # 设置应用样式
    app.setStyle('Fusion')
    
    # 创建并显示主窗口
    window = NegativeEntropySystem()
    window.show()
    
    # 运行应用
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()