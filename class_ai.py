import sys
import json
import random
import math
import uuid
import threading
import time
import hashlib
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from collections import OrderedDict, defaultdict
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Type, Any, Union, Optional, Tuple, Callable
from enum import Enum
from datetime import datetime, timedelta
from scipy.spatial import Voronoi
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
from scipy.signal import convolve2d
plt.rc("font", family='Microsoft YaHei')
from PyQt5.QtWidgets import (
    QApplication, QGraphicsEllipseItem, QMainWindow, QTextEdit, QLineEdit, QPushButton, 
    QVBoxLayout, QHBoxLayout, QWidget, QListWidget, QLabel, QSplitter,
    QTabWidget, QListWidgetItem, QMessageBox, QStatusBar, QComboBox,
    QInputDialog, QFileDialog, QStackedWidget, QGroupBox, QGridLayout,
    QProgressBar, QDialog, QTreeWidget, QTreeWidgetItem, QHeaderView,
    QDockWidget, QFormLayout, QSpinBox, QDoubleSpinBox, QCheckBox,
    QSizePolicy, QScrollArea, QFrame, QToolBar, QAction, QGraphicsView,
    QGraphicsScene, QGraphicsItem, QGraphicsPixmapItem, QSlider
)
from PyQt5.QtCore import Qt, QTimer, QDateTime, QSize, QPointF, QRectF, QUrl, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QPen, QPixmap, QPalette, QIcon, QPainter,QPen, QBrush, QLinearGradient, QRadialGradient, QConicalGradient,QImage, QPolygonF, QKeySequence, QFontDatabase, QTransform, QDesktopServices
from PyQt5.QtMultimedia import QSoundEffect, QMediaPlayer, QMediaContent
from PyQt5.QtMultimediaWidgets import QVideoWidget

# ======================
# 游戏状态与核心类 - 终极版
# ======================

class ElementType(Enum):
    FIRE = "火"
    WATER = "水"
    EARTH = "土"
    AIR = "气"
    LIGHT = "光"
    DARK = "暗"
    ELECTRIC = "电"
    ICE = "冰"
    METAL = "金属"
    WOOD = "木"
    QUANTUM = "量子"
    VOID = "虚空"

class Rarity(Enum):
    COMMON = 1
    UNCOMMON = 2
    RARE = 3
    EPIC = 4
    LEGENDARY = 5
    MYTHIC = 6
    EXOTIC = 7
    PRIMORDIAL = 8

class ResearchField(Enum):
    ELEMENTAL = "元素研究"
    MECHANICAL = "机械研究"
    BIOLOGICAL = "生物研究"
    ENERGY = "能源研究"
    SPATIAL = "空间研究"
    TEMPORAL = "时间研究"
    QUANTUM = "量子研究"
    COSMIC = "宇宙研究"

class GameObject:
    def __init__(self, name, description, level=1, durability=100, max_durability=100):
        self.name = name
        self.description = description
        self.game_state = GameState()
        self.level = level
        self.attributes = []
        self.abilities = []
        self.energy = 0
        self.max_energy = 10
        self.cooldowns = {}
        self.durability = durability
        self.max_durability = max_durability
        self.elemental_affinity = {}
        self.rarity = Rarity.COMMON
        self.owner = None
    
    def __str__(self):
        return f"{self.name} [等级 {self.level}]"
    
    def inspect(self):
        info = f"{self.name} (等级: {self.level})\n{self.description}"
        if self.attributes:
            info += f"\n属性: {', '.join(self.attributes)}"
        if self.abilities:
            info += f"\n能力: {', '.join(a.name for a in self.abilities)}"
        if self.energy > 0:
            info += f"\n能量: {self.energy}/{self.max_energy}"
        if self.durability < self.max_durability:
            info += f"\n耐久: {self.durability}/{self.max_durability}"
        return info
    
    def use(self, target=None):
        # 消耗耐久度
        self.durability = max(0, self.durability - 1)
        return f"你不知道如何使用{self.name}。"
    
    def activate_ability(self, ability_name, target=None):
        ability = next((a for a in self.abilities if a.name.lower() == ability_name.lower()), None)
        if not ability:
            return f"{self.name}没有名为'{ability_name}'的能力"
        
        # 检查冷却时间
        if ability.name in self.cooldowns and self.cooldowns[ability.name] > 0:
            return f"{ability.name}仍在冷却中 ({self.cooldowns[ability.name]}回合)"
        
        # 检查能量
        if self.energy < ability.cost:
            return f"能量不足! 需要 {ability.cost} 能量, 当前 {self.energy}"
        
        # 检查要求
        if ability.requirements:
            if not target or not all(req in getattr(target, "attributes", []) for req in ability.requirements):
                return f"无法使用{ability.name}: 目标不符合要求"
        
        # 消耗能量
        self.energy -= ability.cost
        
        # 设置冷却时间
        if ability.cooldown > 0:
            self.cooldowns[ability.name] = ability.cooldown
        
        # 执行能力效果
        result = self.apply_ability_effect(ability, target)
        
        # 获得经验值
        self.game_state.gain_xp(ability.power * 2, self.__class__.__name__)
        
        # 消耗耐久度
        self.durability = max(0, self.durability - ability.power // 10)
        
        return result
    
    def apply_ability_effect(self, ability, target):
        """由子类实现具体的能力效果"""
        if ability.effect:
            return ability.effect.replace("{self}", self.name).replace("{target}", target.name if target else "")
        return f"{self.name}使用了{ability.name}!"
    
    def recharge(self, amount=5):
        self.energy = min(self.energy + amount, self.max_energy)
        return f"{self.name}恢复了{amount}点能量"
    
    def repair(self, amount=10):
        self.durability = min(self.durability + amount, self.max_durability)
        return f"{self.name}修复了{amount}点耐久度"
    
    def to_dict(self):
        return {
            "class": self.__class__.__name__,
            "name": self.name,
            "description": self.description,
            "level": self.level,
            "attributes": self.attributes,
            "abilities": [asdict(a) for a in self.abilities],
            "energy": self.energy,
            "max_energy": self.max_energy,
            "durability": self.durability,
            "max_durability": self.max_durability
        }
    
    @classmethod
    def from_dict(cls, data):
        obj = cls(data["name"], data["description"], data["level"])
        obj.attributes = data["attributes"]
        obj.abilities = [Ability(**a) for a in data["abilities"]]
        obj.energy = data["energy"]
        obj.max_energy = data["max_energy"]
        obj.durability = data["durability"]
        obj.max_durability = data["max_durability"]
        return obj

@dataclass
class Ability:
    name: str
    description: str
    power: int = 1
    cost: int = 0
    cooldown: int = 0
    requirements: List[str] = field(default_factory=list)
    effect: Optional[str] = None
    element: Optional[ElementType] = None
    rarity: Rarity = Rarity.COMMON
    
    def __str__(self):
        return f"{self.name} (强度: {self.power}, 消耗: {self.cost})"
    
class SpaceTimeArchitect(GameObject):
    """时空建筑师 - 创建空间结构和时间流"""
    def __init__(self, name, description, stability=5):
        super().__init__(name, description)
        self.stability = stability
        self.abilities = [
            Ability("空间折叠", "创建连接两点的空间折叠", stability, 20),
            Ability("时间加速", "加速局部时间流", stability*2, 40),
            Ability("时间停滞", "冻结局部时间", stability*3, 60)
        ]
        self.category = "时空/构造"
        self.rarity = "Rare"

class NeuralLaceMaster(GameObject):
    """神经蕾丝大师 - 控制神经接口技术"""
    def __init__(self, name, description, bandwidth=100):
        super().__init__(name, description)
        self.bandwidth = bandwidth
        self.abilities = [
            Ability("神经扫描", "扫描目标神经活动", bandwidth//10, 15),
            Ability("认知增强", "提升目标认知能力", bandwidth//5, 30),
            Ability("思维窃取", "读取目标思维模式", bandwidth//2, 50)
        ]
        self.category = "神经/接口"
        self.rarity = "Epic"

class MultiverseNavigator(GameObject):
    """多元宇宙导航者 - 在平行宇宙间穿梭"""
    def __init__(self, name, description, navigation=7):
        super().__init__(name, description)
        self.navigation = navigation
        self.abilities = [
            Ability("宇宙感知", "感知附近平行宇宙", navigation, 25),
            Ability("量子隧道", "创建宇宙间隧道", navigation*2, 45),
            Ability("维度跳跃", "瞬间穿越到其他宇宙", navigation*3, 70)
        ]
        self.category = "多元/导航"
        self.rarity = "Legendary"

class QuantumEconomist(GameObject):
    """量子经济师 - 操控量子经济系统"""
    def __init__(self, name, description, market_influence=4):
        super().__init__(name, description)
        self.market_influence = market_influence
        self.abilities = [
            Ability("量子套利", "利用量子波动获利", market_influence, 20),
            Ability("市场操纵", "影响量子市场", market_influence*2, 40),
            Ability("时空投资", "投资时间晶体", market_influence*3, 60)
        ]
        self.category = "经济/量子"
        self.rarity = "Exotic"



class GameEvent:
    def __init__(self, name: str, description: str, effect: Callable, probability: float = 0.1):
        self.name = name
        self.description = description
        self.effect = effect
        self.probability = probability

class Skill:
    def __init__(self, name: str, description: str, level: int = 1, max_level: int = 10, xp: int = 0):
        self.name = name
        self.description = description
        self.level = level
        self.max_level = max_level
        self.xp = xp
        self.unlocked = level > 0

    def gain_xp(self, amount: int):
        if not self.unlocked:
            return
            
        self.xp += amount
        xp_needed = self.level * 100
        if self.xp >= xp_needed and self.level < self.max_level:
            self.level += 1
            self.xp = 0
            return f"{self.name} 升级到 {self.level} 级!"
        return ""
    
# ======================
# 超维宇宙核心系统
# ======================

class QuantumConsciousness:
    """量子意识系统 - 模拟玩家意识的量子态"""
    def __init__(self, player_id):
        self.player_id = player_id
        self.state = np.zeros(16, dtype=complex)  # 16维量子态
        self.state[0] = 1.0  # 初始状态
        self.entangled_players = []  # 纠缠的玩家
        self.superposition_level = 1.0  # 叠加态级别
        self.decoherence_rate = 0.01  # 退相干率
    
    def apply_quantum_gate(self, gate, qubits):
        """应用量子门操作"""
        # 简化的量子门操作
        if gate == "H":
            # Hadamard门
            for q in qubits:
                self.state = self.hadamard_transform(q)
        elif gate == "X":
            # Pauli-X门
            for q in qubits:
                self.state = self.pauli_x(q)
        elif gate == "CNOT":
            # CNOT门
            if len(qubits) >= 2:
                self.state = self.cnot_gate(qubits[0], qubits[1])
    
    def hadamard_transform(self, qubit):
        """Hadamard变换"""
        # 简化的Hadamard变换
        new_state = self.state.copy()
        new_state[0] = (self.state[0] + self.state[1]) / np.sqrt(2)
        new_state[1] = (self.state[0] - self.state[1]) / np.sqrt(2)
        return new_state
    
    def pauli_x(self, qubit):
        """Pauli-X门"""
        new_state = self.state.copy()
        new_state[0], new_state[1] = self.state[1], self.state[0]
        return new_state
    
    def cnot_gate(self, control, target):
        """CNOT门"""
        new_state = self.state.copy()
        # 简化实现 - 实际应为张量运算
        if control == 0 and target == 1:
            new_state[3] = self.state[2]  # |10> -> |11>
            new_state[2] = self.state[3]  # |11> -> |10>
        return new_state
    
    def entangle_with(self, other_player):
        """与另一个玩家意识纠缠"""
        if other_player not in self.entangled_players:
            self.entangled_players.append(other_player)
            # 创建量子纠缠
            self.apply_quantum_gate("H", [0])
            self.apply_quantum_gate("CNOT", [0, 1])
    
    def measure(self, qubit):
        """测量量子态"""
        probabilities = np.abs(self.state)**2
        outcome = np.random.choice(len(probabilities), p=probabilities)
        return bin(outcome)[2:].zfill(int(np.log2(len(self.state))))
    
    def update_decoherence(self):
        """更新退相干状态"""
        self.superposition_level = max(0, self.superposition_level - self.decoherence_rate)
        if self.superposition_level < 0.5:
            # 触发退相干事件
            return "意识退相干警告! 量子态正在坍缩"
        return ""

class RealityDistortionEngine:
    """现实扭曲引擎 - 允许玩家修改游戏规则"""
    def __init__(self):
        self.reality_level = 100  # 现实稳定度 (0-100)
        self.distortion_fields = []  # 活动扭曲场
        self.player_distortion_power = defaultdict(int)  # 玩家扭曲能力
    
    def create_distortion_field(self, player_id, center, radius, effect):
        """创建现实扭曲场"""
        field_id = str(uuid.uuid4())
        self.distortion_fields.append({
            "id": field_id,
            "player": player_id,
            "center": center,
            "radius": radius,
            "effect": effect,
            "strength": 10,
            "lifetime": 100
        })
        self.reality_level = max(0, self.reality_level - 5)
        return field_id
    
    def apply_distortion(self, game_state, position):
        """应用现实扭曲效果"""
        for field in self.distortion_fields[:]:
            distance = np.linalg.norm(np.array(position) - np.array(field["center"]))
            if distance <= field["radius"]:
                # 应用扭曲效果
                effect = field["effect"]
                
                if effect == "time_dilation":
                    # 时间膨胀
                    game_state.time_scale = max(0.1, game_state.time_scale * 0.8)
                elif effect == "gravity_shift":
                    # 重力变化
                    game_state.gravity = max(0.1, game_state.gravity * 1.2)
                elif effect == "quantum_fluctuation":
                    # 量子涨落
                    if random.random() < 0.3:
                        # 随机创建或销毁对象
                        if random.random() < 0.5:
                            item_id = f"quantum_object_{uuid.uuid4().hex[:6]}"
                            game_state.inventory[item_id] = QuantumObject(item_id, "量子涨落产生的物体")
                        else:
                            if game_state.inventory:
                                item_id = random.choice(list(game_state.inventory.keys()))
                                del game_state.inventory[item_id]
                
                # 更新扭曲场
                field["lifetime"] -= 1
                if field["lifetime"] <= 0:
                    self.distortion_fields.remove(field)
                    self.reality_level = min(100, self.reality_level + 3)
    
    def stabilize_reality(self, amount=5):
        """稳定现实"""
        self.reality_level = min(100, self.reality_level + amount)
        return f"现实稳定度增加至 {self.reality_level}%"

class MultiverseSimulator:
    """多元宇宙模拟器 - 管理平行宇宙"""
    def __init__(self):
        self.parallel_universes = {}  # 宇宙ID -> 游戏状态
        self.current_universe = "prime"  # 当前宇宙
        self.universe_connections = defaultdict(list)  # 宇宙连接关系
        self.quantum_tunnels = []  # 量子隧道
    
    def create_universe(self, universe_id, base_state=None):
        """创建新宇宙"""
        if universe_id in self.parallel_universes:
            return False
        
        if base_state:
            # 复制基础宇宙状态
            new_state = json.loads(json.dumps(base_state))
        else:
            # 创建新宇宙
            new_state = {
                "inventory": {},
                "player_state": {
                    "health": 100,
                    "energy": 100,
                    "position": [0, 0, 0]
                },
                "world_state": {}
            }
        
        self.parallel_universes[universe_id] = new_state
        return True
    
    def switch_universe(self, universe_id):
        """切换到指定宇宙"""
        if universe_id in self.parallel_universes:
            self.current_universe = universe_id
            return True
        return False
    
    def create_quantum_tunnel(self, from_universe, to_universe, position, stability=100):
        """创建量子隧道"""
        tunnel_id = str(uuid.uuid4())
        self.quantum_tunnels.append({
            "id": tunnel_id,
            "from": from_universe,
            "to": to_universe,
            "position": position,
            "stability": stability
        })
        # 更新宇宙连接关系
        self.universe_connections[from_universe].append(to_universe)
        self.universe_connections[to_universe].append(from_universe)
        return tunnel_id
    
    def traverse_tunnel(self, player_id, tunnel_id):
        """穿越量子隧道"""
        tunnel = next((t for t in self.quantum_tunnels if t["id"] == tunnel_id), None)
        if not tunnel:
            return False
        
        # 更新玩家位置到目标宇宙
        from_state = self.parallel_universes[tunnel["from"]]
        to_state = self.parallel_universes[tunnel["to"]]
        
        if player_id in from_state["player_state"]:
            player_state = from_state["player_state"][player_id]
            to_state["player_state"][player_id] = player_state
            del from_state["player_state"][player_id]
            
            # 更新当前宇宙
            self.current_universe = tunnel["to"]
            return True
        
        return False
    
    def quantum_entangle_universes(self, universe1, universe2):
        """量子纠缠两个宇宙"""
        if universe1 not in self.universe_connections[universe2]:
            self.universe_connections[universe1].append(universe2)
            self.universe_connections[universe2].append(universe1)
            
            # 创建双向隧道
            self.create_quantum_tunnel(universe1, universe2, [0, 0, 0])
            self.create_quantum_tunnel(universe2, universe1, [0, 0, 0])
            return True
        return False

class NeuralLaceInterface:
    """神经蕾丝接口 - 连接玩家大脑与游戏系统"""
    def __init__(self):
        self.connected_players = {}  # 玩家ID -> 连接状态
        self.brain_computer_interfaces = defaultdict(dict)  # BCI设备状态
        self.cognitive_enhancement_level = defaultdict(int)  # 认知增强级别
        self.thought_patterns = defaultdict(list)  # 玩家思维模式
    
    def connect_player(self, player_id, bci_device="cortex_stream"):
        """连接玩家神经蕾丝接口"""
        if player_id not in self.connected_players:
            self.connected_players[player_id] = {
                "status": "connecting",
                "device": bci_device,
                "bandwidth": 100,  # Mbit/s
                "latency": 50  # ms
            }
            return f"正在连接 {bci_device}..."
        
        return "玩家已连接"
    
    def enhance_cognition(self, player_id, enhancement_type="neuro_boost"):
        """增强玩家认知能力"""
        if player_id not in self.connected_players:
            return "玩家未连接"
        
        if enhancement_type == "neuro_boost":
            self.cognitive_enhancement_level[player_id] = min(5, self.cognitive_enhancement_level[player_id] + 1)
            return f"神经增强级别提升至 {self.cognitive_enhancement_level[player_id]}"
        elif enhancement_type == "memory_enhance":
            # 提升记忆能力
            return "记忆增强激活"
        elif enhancement_type == "processing_accel":
            # 提升处理速度
            self.connected_players[player_id]["latency"] = max(10, self.connected_players[player_id]["latency"] - 10)
            return f"处理延迟降低至 {self.connected_players[player_id]['latency']}ms"
        
        return "未知增强类型"
    
    def record_thought_pattern(self, player_id, thought):
        """记录玩家思维模式"""
        self.thought_patterns[player_id].append(thought)
        # 限制存储的思维数量
        if len(self.thought_patterns[player_id]) > 100:
            self.thought_patterns[player_id].pop(0)
        return "思维模式已记录"
    
    def predict_action(self, player_id):
        """预测玩家下一步行动"""
        if player_id not in self.thought_patterns or not self.thought_patterns[player_id]:
            return "未知"
        
        # 简化的预测算法 - 实际应使用深度学习模型
        last_thought = self.thought_patterns[player_id][-1]
        if "攻击" in last_thought:
            return "攻击动作"
        elif "建造" in last_thought:
            return "建造动作"
        elif "探索" in last_thought:
            return "探索动作"
        return "待机"

class QuantumNeuralNetwork(nn.Module):
    """量子神经网络 - 融合量子计算与深度学习"""
    def __init__(self, input_size, hidden_size, output_size, quantum_layer_size=8):
        super(QuantumNeuralNetwork, self).__init__()
        self.classical_fc1 = nn.Linear(input_size, hidden_size)
        self.quantum_layer = nn.Linear(hidden_size, quantum_layer_size)
        self.quantum_to_classical = nn.Linear(quantum_layer_size, hidden_size)
        self.classical_fc2 = nn.Linear(hidden_size, output_size)
        self.activation = nn.ReLU()
        self.quantum_activation = self.quantum_activation_function
    
    def quantum_activation_function(self, x):
        """量子激活函数 - 模拟量子叠加态"""
        # 实际实现应使用量子门操作
        return torch.sin(x) * torch.exp(-x**2)
    
    def forward(self, x):
        # 经典神经网络层
        x = self.activation(self.classical_fc1(x))
        
        # 量子层
        quantum_state = self.quantum_activation(self.quantum_layer(x))
        
        # 量子到经典转换
        x = self.activation(self.quantum_to_classical(quantum_state))
        
        # 输出层
        x = self.classical_fc2(x)
        return x

class SpaceTimeManipulator:
    """时空操纵器 - 控制游戏内时间与空间"""
    def __init__(self):
        self.time_scale = 1.0  # 时间流逝速度
        self.time_direction = 1.0  # 时间方向 (1.0=正向, -1.0=反向)
        self.local_time_bubbles = {}  # 局部时间场
        self.space_folds = []  # 空间折叠
        self.gravity = 9.8  # 重力加速度
    
    def create_time_bubble(self, position, radius, time_scale):
        """创建局部时间场"""
        bubble_id = str(uuid.uuid4())
        self.local_time_bubbles[bubble_id] = {
            "position": position,
            "radius": radius,
            "time_scale": time_scale,
            "lifetime": 100
        }
        return bubble_id
    
    def create_space_fold(self, point_a, point_b):
        """创建空间折叠 - 连接两个空间点"""
        fold_id = str(uuid.uuid4())
        self.space_folds.append({
            "id": fold_id,
            "point_a": point_a,
            "point_b": point_b,
            "stability": 100
        })
        return fold_id
    
    def teleport_via_fold(self, entity_id, fold_id):
        """通过空间折叠传送实体"""
        fold = next((f for f in self.space_folds if f["id"] == fold_id), None)
        if not fold:
            return False
        
        # 在实际游戏中，这里会更新实体的位置
        return True
    
    def reverse_time(self, duration=10):
        """局部时间倒流"""
        self.time_direction = -1.0
        # 设置恢复正向时间的计时器
        threading.Timer(duration, self.restore_time_direction).start()
        return f"时间倒流激活，持续 {duration} 秒"
    
    def restore_time_direction(self):
        """恢复正向时间"""
        self.time_direction = 1.0
        return "时间流恢复正常"

# ======================
# 游戏状态与核心类
# ======================

class GameState:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.reset()
        return cls._instance
    
    def reset(self):
        # 基础状态
        self.current_universe = "prime"
        self.player_id = str(uuid.uuid4())
        self.inventory = OrderedDict()
        self.unlocked_realities = {"prime": True}
        self.completed_challenges = set()
        self.created_objects = {}
        self.available_classes = self.get_base_classes()
        self.discovered_abilities = {}
        self.player_energy = 1000
        self.player_max_energy = 1000
        self.player_level = 1
        self.player_xp = 0
        self.class_xp = {}
        self.game_time = 0
        self.learned_recipes = []
        self.quests = {
            "main": "稳定多元宇宙结构",
            "side": ["收集奇异物质", "关闭量子异常", "建立宇宙连接"]
        }
        self.history = []
        self.current_abilities = []
        self.selected_object = None
        
        # 超维系统
        self.quantum_consciousness = QuantumConsciousness(self.player_id)
        self.reality_distortion_engine = RealityDistortionEngine()
        self.multiverse_simulator = MultiverseSimulator()
        self.neural_lace_interface = NeuralLaceInterface()
        self.space_time_manipulator = SpaceTimeManipulator()
        self.quantum_neural_network = QuantumNeuralNetwork(
            input_size=20, 
            hidden_size=64, 
            output_size=10,
            quantum_layer_size=8
        )
        
        # 创建初始宇宙
        self.multiverse_simulator.create_universe("prime")
        self.multiverse_simulator.create_universe("quantum_flux")
        self.multiverse_simulator.create_universe("neural_paradise")
        self.multiverse_simulator.create_quantum_tunnel("prime", "quantum_flux", [0, 0, 0])
        self.multiverse_simulator.create_quantum_tunnel("prime", "neural_paradise", [10, 5, 0])
        
        # 高级经济
        self.quantum_currency = 10000
        self.time_crystals = 5
        self.reality_shards = 3
        
        # 世界状态
        self.time_of_day = "量子黎明"
        self.weather = "量子风暴"
        self.dimensional_stability = 85.0
        self.quantum_fluctuation_level = 15.0
        
        # 公司状态
        self.corporations = {
            "量子动力": {"reputation": 75, "stock": 1500},
            "神经蕾丝科技": {"reputation": 60, "stock": 2200},
            "时空工程集团": {"reputation": 85, "stock": 1800}
        }
    
    def get_base_classes(self):
        # 返回基础类定义
        return {
            "量子意识操控者": QuantumMindController,
            "现实扭曲者": RealityWarper,
            "时空建筑师": SpaceTimeArchitect,
            "神经蕾丝大师": NeuralLaceMaster,
            "多元宇宙导航者": MultiverseNavigator,
            "量子经济师": QuantumEconomist
        }

class QuantumObject:
    """量子对象 - 具有量子态的游戏对象"""
    def __init__(self, name, description, quantum_state=None):
        self.name = name
        self.description = description
        self.quantum_state = quantum_state or np.zeros(8, dtype=complex)
        self.quantum_state[0] = 1.0
        self.superposition = True
        self.entangled_objects = []
    
    def observe(self):
        """观察对象，使量子态坍缩"""
        if self.superposition:
            probabilities = np.abs(self.quantum_state)**2
            outcome = np.random.choice(len(probabilities), p=probabilities)
            self.superposition = False
            return f"{self.name}坍缩为状态: {outcome}"
        return f"{self.name}已在确定状态"
    
    def entangle_with(self, other):
        """与另一个量子对象纠缠"""
        if not isinstance(other, QuantumObject):
            return "只能与量子对象纠缠"
        
        # 创建纠缠
        self.quantum_state[0] = 1/np.sqrt(2)
        self.quantum_state[3] = 1/np.sqrt(2)  # 简化的贝尔态
        other.quantum_state = self.quantum_state
        self.entangled_objects.append(other)
        other.entangled_objects.append(self)
        return f"{self.name} 和 {other.name} 已量子纠缠"

class QuantumMindController(GameObject):
    """量子意识操控者 - 影响其他玩家意识"""
    def __init__(self, name, description, influence=5):
        super().__init__(name, description)
        self.influence = influence
        self.abilities = [
            Ability("意识扫描", "扫描目标意识状态", influence, 10),
            Ability("量子暗示", "植入量子级心理暗示", influence*2, 25),
            Ability("意识融合", "与目标意识短暂融合", influence*3, 50)
        ]
        self.category = "量子/心理"
        self.rarity = "Exotic"

class RealityWarper(GameObject):
    """现实扭曲者 - 修改局部现实规则"""
    def __init__(self, name, description, warp_strength=3):
        super().__init__(name, description)
        self.warp_strength = warp_strength
        self.abilities = [
            Ability("现实扭曲", "扭曲局部现实规则", warp_strength, 30),
            Ability("法则修改", "修改物理法则", warp_strength*2, 60),
            Ability("存在抹除", "将目标从现实中移除", warp_strength*3, 100)
        ]
        self.category = "现实/操控"
        self.rarity = "Legendary"

# ======================
# PyQt5 游戏界面 - 超维宇宙
# ======================

class QuantumConsciousnessWidget(QWidget):
    """量子意识可视化组件"""
    consciousness_updated = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        
        # 量子态显示
        self.quantum_state_label = QLabel("量子态: |0⟩")
        self.layout.addWidget(self.quantum_state_label)
        
        # 量子位可视化
        self.qubit_view = QGraphicsView()
        self.qubit_scene = QGraphicsScene()
        self.qubit_view.setScene(self.qubit_scene)
        self.layout.addWidget(self.qubit_view)
        
        # 控制按钮
        control_layout = QHBoxLayout()
        self.entangle_button = QPushButton("创建纠缠")
        self.measure_button = QPushButton("测量")
        self.superposition_button = QPushButton("叠加态")
        
        control_layout.addWidget(self.entangle_button)
        control_layout.addWidget(self.measure_button)
        control_layout.addWidget(self.superposition_button)
        
        self.layout.addLayout(control_layout)
        
        # 连接信号
        self.entangle_button.clicked.connect(self.create_entanglement)
        self.measure_button.clicked.connect(self.measure_quantum_state)
        self.superposition_button.clicked.connect(self.create_superposition)
        
        # 初始可视化
        self.update_visualization()
    
    def create_entanglement(self):
        self.consciousness_updated.emit()
        self.update_visualization()
    
    def measure_quantum_state(self):
        self.consciousness_updated.emit()
        self.update_visualization()
    
    def create_superposition(self):
        self.consciousness_updated.emit()
        self.update_visualization()
    
    def update_visualization(self):
        """更新量子态可视化"""
        self.qubit_scene.clear()
        
        # 创建量子位表示
        for i in range(8):
            # 随机量子态
            state = random.choice([0, 1, 2])  # 0=|0>, 1=|1>, 2=叠加态
            
            # 创建量子位图形
            qubit = QGraphicsEllipseItem(0, 0, 50, 50)
            qubit.setPos(i * 60, 0)
            
            # 设置颜色
            if state == 0:
                qubit.setBrush(QColor(0, 150, 255))  # 蓝色
            elif state == 1:
                qubit.setBrush(QColor(255, 50, 50))  # 红色
            else:  # 叠加态
                gradient = QLinearGradient(0, 0, 50, 50)
                gradient.setColorAt(0, QColor(0, 150, 255))
                gradient.setColorAt(1, QColor(255, 50, 50))
                qubit.setBrush(QBrush(gradient))
            
            self.qubit_scene.addItem(qubit)
            
            # 添加标签
            label = self.qubit_scene.addText(f"Q{i}")
            label.setPos(i * 60 + 15, 55)
        
        # 添加纠缠连接
        for i in range(0, 8, 2):
            line = self.qubit_scene.addLine(i*60+25, 25, (i+1)*60+25, 25)
            line.setPen(QPen(QColor(0, 200, 0), 2, Qt.DashLine))

class MultiverseMapWidget(QGraphicsView):
    """多元宇宙地图可视化"""
    universe_selected = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene()
        self.setScene(self.scene)
        self.setRenderHint(QPainter.Antialiasing)
        self.universes = {}
        self.tunnels = []
        
        # 初始布局
        self.layout_universes()
    
    def layout_universes(self):
        """布局多元宇宙"""
        self.scene.clear()
        self.universes.clear()
        self.tunnels = []
        
        # 定义宇宙位置
        universe_positions = {
            "prime": (0, 0),
            "quantum_flux": (200, 0),
            "neural_paradise": (0, 200),
            "time_vortex": (200, 200),
            "void_realm": (100, 300)
        }
        
        # 创建宇宙节点
        for universe_id, pos in universe_positions.items():
            universe = QGraphicsEllipseItem(0, 0, 80, 80)
            universe.setPos(pos[0], pos[1])
            universe.setBrush(QColor(70, 70, 150, 200))
            universe.setPen(QPen(Qt.white, 2))
            universe.setData(0, universe_id)  # 存储宇宙ID
            
            # 添加标签
            label = self.scene.addText(universe_id)
            label.setPos(pos[0] + 10, pos[1] + 30)
            label.setDefaultTextColor(Qt.white)
            
            self.scene.addItem(universe)
            self.universes[universe_id] = universe
        
        # 创建量子隧道
        tunnel_connections = [
            ("prime", "quantum_flux"),
            ("prime", "neural_paradise"),
            ("quantum_flux", "time_vortex"),
            ("neural_paradise", "void_realm")
        ]
        
        for from_id, to_id in tunnel_connections:
            if from_id in universe_positions and to_id in universe_positions:
                from_pos = universe_positions[from_id]
                to_pos = universe_positions[to_id]
                
                # 调整位置到宇宙中心
                from_center = (from_pos[0] + 40, from_pos[1] + 40)
                to_center = (to_pos[0] + 40, to_pos[1] + 40)
                
                # 创建隧道
                tunnel = self.scene.addLine(
                    from_center[0], from_center[1],
                    to_center[0], to_center[1],
                    QPen(QColor(0, 200, 200), 3, Qt.DashLine)
                )
                self.tunnels.append(tunnel)
    
    def mousePressEvent(self, event):
        """处理宇宙选择"""
        item = self.itemAt(event.pos())
        if item and item in self.universes.values():
            universe_id = item.data(0)
            self.universe_selected.emit(universe_id)
            self.highlight_universe(universe_id)
        super().mousePressEvent(event)
    
    def highlight_universe(self, universe_id):
        """高亮显示选中的宇宙"""
        for uid, universe in self.universes.items():
            if uid == universe_id:
                universe.setPen(QPen(Qt.yellow, 4))
            else:
                universe.setPen(QPen(Qt.white, 2))

class RealityDistortionControl(QWidget):
    """现实扭曲控制面板"""
    distortion_created = pyqtSignal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QFormLayout(self)
        
        # 扭曲类型选择
        self.distortion_type = QComboBox()
        self.distortion_type.addItems([
            "时间膨胀", "重力偏移", "量子涨落", 
            "空间压缩", "现实重构", "法则覆写"
        ])
        self.layout.addRow("扭曲类型:", self.distortion_type)
        
        # 强度控制
        self.strength_slider = QSlider(Qt.Horizontal)
        self.strength_slider.setRange(1, 10)
        self.strength_slider.setValue(5)
        self.layout.addRow("强度:", self.strength_slider)
        
        # 范围控制
        self.radius_slider = QSlider(Qt.Horizontal)
        self.radius_slider.setRange(10, 100)
        self.radius_slider.setValue(50)
        self.layout.addRow("范围:", self.radius_slider)
        
        # 位置控制
        self.x_spin = QSpinBox()
        self.x_spin.setRange(-100, 100)
        self.y_spin = QSpinBox()
        self.y_spin.setRange(-100, 100)
        self.z_spin = QSpinBox()
        self.z_spin.setRange(-100, 100)
        
        pos_layout = QHBoxLayout()
        pos_layout.addWidget(QLabel("X:"))
        pos_layout.addWidget(self.x_spin)
        pos_layout.addWidget(QLabel("Y:"))
        pos_layout.addWidget(self.y_spin)
        pos_layout.addWidget(QLabel("Z:"))
        pos_layout.addWidget(self.z_spin)
        self.layout.addRow("位置:", pos_layout)
        
        # 创建按钮
        self.create_button = QPushButton("创建扭曲场")
        self.create_button.clicked.connect(self.create_distortion)
        self.layout.addWidget(self.create_button)
    
    def create_distortion(self):
        """创建扭曲场"""
        distortion_data = {
            "type": self.distortion_type.currentText(),
            "strength": self.strength_slider.value(),
            "radius": self.radius_slider.value(),
            "position": [
                self.x_spin.value(),
                self.y_spin.value(),
                self.z_spin.value()
            ]
        }
        self.distortion_created.emit(distortion_data)

class NeuralLaceInterfaceWidget(QWidget):
    """神经蕾丝接口控制面板"""
    thought_recorded = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        
        # 连接状态
        self.connection_status = QLabel("神经蕾丝接口: 未连接")
        self.layout.addWidget(self.connection_status)
        
        # 连接按钮
        self.connect_button = QPushButton("连接接口")
        self.connect_button.clicked.connect(self.connect_interface)
        self.layout.addWidget(self.connect_button)
        
        # 认知增强控制
        enhance_group = QGroupBox("认知增强")
        enhance_layout = QHBoxLayout()
        
        self.neuro_boost_button = QPushButton("神经增强")
        self.memory_enhance_button = QPushButton("记忆增强")
        self.processing_button = QPushButton("处理加速")
        
        enhance_layout.addWidget(self.neuro_boost_button)
        enhance_layout.addWidget(self.memory_enhance_button)
        enhance_layout.addWidget(self.processing_button)
        enhance_group.setLayout(enhance_layout)
        self.layout.addWidget(enhance_group)
        
        # 思维记录
        self.thought_input = QLineEdit()
        self.thought_input.setPlaceholderText("输入你的思维...")
        self.record_button = QPushButton("记录思维")
        
        thought_layout = QHBoxLayout()
        thought_layout.addWidget(self.thought_input)
        thought_layout.addWidget(self.record_button)
        self.layout.addLayout(thought_layout)
        
        # 思维模式显示
        self.thought_patterns = QListWidget()
        self.layout.addWidget(self.thought_patterns)
        
        # 连接信号
        self.record_button.clicked.connect(self.record_thought)
    
    def connect_interface(self):
        self.connection_status.setText("神经蕾丝接口: 已连接 (带宽: 100Gbit/s)")
    
    def record_thought(self):
        thought = self.thought_input.text()
        if thought:
            self.thought_patterns.addItem(thought)
            self.thought_recorded.emit(thought)
            self.thought_input.clear()

class SpaceTimeControl(QWidget):
    """时空控制面板"""
    time_reversed = pyqtSignal(float)
    space_fold_created = pyqtSignal(list, list)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        
        # 时间控制
        time_group = QGroupBox("时间操纵")
        time_layout = QFormLayout()
        
        self.time_scale_slider = QSlider(Qt.Horizontal)
        self.time_scale_slider.setRange(1, 100)
        self.time_scale_slider.setValue(50)
        time_layout.addRow("时间流速:", self.time_scale_slider)
        
        self.reverse_time_button = QPushButton("时间倒流")
        self.reverse_time_button.clicked.connect(self.reverse_time)
        time_layout.addWidget(self.reverse_time_button)
        
        time_group.setLayout(time_layout)
        self.layout.addWidget(time_group)
        
        # 空间控制
        space_group = QGroupBox("空间操纵")
        space_layout = QFormLayout()
        
        # 点A位置
        self.point_a_x = QSpinBox()
        self.point_a_x.setRange(-100, 100)
        self.point_a_y = QSpinBox()
        self.point_a_y.setRange(-100, 100)
        self.point_a_z = QSpinBox()
        self.point_a_z.setRange(-100, 100)
        
        point_a_layout = QHBoxLayout()
        point_a_layout.addWidget(QLabel("X:"))
        point_a_layout.addWidget(self.point_a_x)
        point_a_layout.addWidget(QLabel("Y:"))
        point_a_layout.addWidget(self.point_a_y)
        point_a_layout.addWidget(QLabel("Z:"))
        point_a_layout.addWidget(self.point_a_z)
        space_layout.addRow("点 A:", point_a_layout)
        
        # 点B位置
        self.point_b_x = QSpinBox()
        self.point_b_x.setRange(-100, 100)
        self.point_b_y = QSpinBox()
        self.point_b_y.setRange(-100, 100)
        self.point_b_z = QSpinBox()
        self.point_b_z.setRange(-100, 100)
        
        point_b_layout = QHBoxLayout()
        point_b_layout.addWidget(QLabel("X:"))
        point_b_layout.addWidget(self.point_b_x)
        point_b_layout.addWidget(QLabel("Y:"))
        point_b_layout.addWidget(self.point_b_y)
        point_b_layout.addWidget(QLabel("Z:"))
        point_b_layout.addWidget(self.point_b_z)
        space_layout.addRow("点 B:", point_b_layout)
        
        # 创建空间折叠
        self.create_fold_button = QPushButton("创建空间折叠")
        self.create_fold_button.clicked.connect(self.create_space_fold)
        space_layout.addWidget(self.create_fold_button)
        
        space_group.setLayout(space_layout)
        self.layout.addWidget(space_group)
    
    def reverse_time(self):
        duration = self.time_scale_slider.value() / 10.0
        self.time_reversed.emit(duration)
    
    def create_space_fold(self):
        point_a = [
            self.point_a_x.value(),
            self.point_a_y.value(),
            self.point_a_z.value()
        ]
        point_b = [
            self.point_b_x.value(),
            self.point_b_y.value(),
            self.point_b_z.value()
        ]
        self.space_fold_created.emit(point_a, point_b)

class HyperVerseGameWindow(QMainWindow):
    """超维宇宙游戏主窗口"""
    def __init__(self):
        super().__init__()
        self.game_state = GameState()
        self.init_ui()
        
        # 设置定时器
        self.setup_timers()
        
        # 初始更新
        self.update_status()
    
    def init_ui(self):
        self.setWindowTitle('超维宇宙：类组合冒险')
        self.setGeometry(100, 100, 1600, 900)
        
        # 创建中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # 左侧面板 - 量子意识
        left_dock = QDockWidget("量子意识", self)
        left_dock.setWidget(QuantumConsciousnessWidget())
        self.addDockWidget(Qt.LeftDockWidgetArea, left_dock)
        
        # 右侧面板 - 多元宇宙地图
        right_dock = QDockWidget("多元宇宙", self)
        self.multiverse_map = MultiverseMapWidget()
        self.multiverse_map.universe_selected.connect(self.switch_universe)
        right_dock.setWidget(self.multiverse_map)
        self.addDockWidget(Qt.RightDockWidgetArea, right_dock)
        
        # 底部面板 - 现实扭曲控制
        bottom_dock = QDockWidget("现实扭曲引擎", self)
        self.reality_control = RealityDistortionControl()
        self.reality_control.distortion_created.connect(self.create_distortion_field)
        bottom_dock.setWidget(self.reality_control)
        self.addDockWidget(Qt.BottomDockWidgetArea, bottom_dock)
        
        # 中央区域 - 游戏主视图
        central_tabs = QTabWidget()
        
        # 神经蕾丝接口标签
        neural_tab = QWidget()
        neural_layout = QVBoxLayout(neural_tab)
        self.neural_lace_interface = NeuralLaceInterfaceWidget()
        self.neural_lace_interface.thought_recorded.connect(self.record_thought)
        neural_layout.addWidget(self.neural_lace_interface)
        central_tabs.addTab(neural_tab, "神经蕾丝接口")
        
        # 时空操纵标签
        spacetime_tab = QWidget()
        spacetime_layout = QVBoxLayout(spacetime_tab)
        self.space_time_control = SpaceTimeControl()
        self.space_time_control.time_reversed.connect(self.reverse_time)
        self.space_time_control.space_fold_created.connect(self.create_space_fold)
        spacetime_layout.addWidget(self.space_time_control)
        central_tabs.addTab(spacetime_tab, "时空操纵")
        
        # 量子神经网络标签
        qnn_tab = QWidget()
        qnn_layout = QVBoxLayout(qnn_tab)
        qnn_layout.addWidget(QLabel("量子神经网络可视化"))
        self.qnn_canvas = FigureCanvas(Figure(figsize=(10, 8)))
        qnn_layout.addWidget(self.qnn_canvas)
        self.visualize_qnn()
        central_tabs.addTab(qnn_tab, "量子神经网络")
        
        main_layout.addWidget(central_tabs)
        
        # 状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # 创建工具栏
        self.create_toolbar()
        
        # 创建菜单
        self.create_menu()
    
    def create_toolbar(self):
        toolbar = QToolBar("主工具栏")
        toolbar.setIconSize(QSize(48, 48))
        self.addToolBar(toolbar)
        
        # 量子操作
        quantum_action = QAction(QIcon("quantum.png"), "量子实验室", self)
        toolbar.addAction(quantum_action)
        
        # 现实扭曲
        reality_action = QAction(QIcon("reality.png"), "现实扭曲", self)
        toolbar.addAction(reality_action)
        
        # 时空操纵
        spacetime_action = QAction(QIcon("spacetime.png"), "时空操纵", self)
        toolbar.addAction(spacetime_action)
        
        toolbar.addSeparator()
        
        # 神经蕾丝
        neural_action = QAction(QIcon("neural.png"), "神经蕾丝", self)
        toolbar.addAction(neural_action)
        
        # 多元宇宙
        multiverse_action = QAction(QIcon("multiverse.png"), "多元宇宙", self)
        toolbar.addAction(multiverse_action)
        
        toolbar.addSeparator()
        
        # 保存/加载
        save_action = QAction(QIcon("save.png"), "保存宇宙", self)
        toolbar.addAction(save_action)
        
        load_action = QAction(QIcon("load.png"), "加载宇宙", self)
        toolbar.addAction(load_action)
    
    def create_menu(self):
        menubar = self.menuBar()
        
        # 宇宙菜单
        universe_menu = menubar.addMenu('宇宙操作')
        new_universe_action = QAction('创建新宇宙', self)
        universe_menu.addAction(new_universe_action)
        
        switch_universe_action = QAction('切换宇宙', self)
        universe_menu.addAction(switch_universe_action)
        
        # 量子菜单
        quantum_menu = menubar.addMenu('量子操作')
        entangle_action = QAction('创建量子纠缠', self)
        quantum_menu.addAction(entangle_action)
        
        measure_action = QAction('测量量子态', self)
        quantum_menu.addAction(measure_action)
        
        # 现实菜单
        reality_menu = menubar.addMenu('现实操作')
        distort_action = QAction('扭曲现实', self)
        reality_menu.addAction(distort_action)
        
        stabilize_action = QAction('稳定现实', self)
        reality_menu.addAction(stabilize_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu('超维帮助')
        manual_action = QAction('超维手册', self)
        help_menu.addAction(manual_action)
        
        about_action = QAction('关于超维宇宙', self)
        help_menu.addAction(about_action)
    
    def setup_timers(self):
        # 状态更新定时器
        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self.update_status)
        self.status_timer.start(1000)  # 每秒更新
        
        # 现实稳定度定时器
        self.reality_timer = QTimer(self)
        self.reality_timer.timeout.connect(self.update_reality)
        self.reality_timer.start(5000)  # 每5秒更新
    
    def update_status(self):
        """更新状态信息"""
        status = f"当前宇宙: {self.game_state.current_universe} | "
        status += f"现实稳定度: {self.game_state.reality_distortion_engine.reality_level}% | "
        status += f"量子货币: {self.game_state.quantum_currency} | "
        status += f"时间晶体: {self.game_state.time_crystals}"
        self.status_bar.showMessage(status)
    
    def update_reality(self):
        """更新现实稳定度"""
        # 随机事件影响现实
        if random.random() < 0.2:
            change = random.randint(-5, 3)
            self.game_state.reality_distortion_engine.reality_level = max(0, 
                min(100, self.game_state.reality_distortion_engine.reality_level + change)
            )
    
    def switch_universe(self, universe_id):
        """切换宇宙"""
        if self.game_state.multiverse_simulator.switch_universe(universe_id):
            self.status_bar.showMessage(f"已切换到宇宙: {universe_id}")
    
    def create_distortion_field(self, distortion_data):
        """创建现实扭曲场"""
        field_id = self.game_state.reality_distortion_engine.create_distortion_field(
            self.game_state.player_id,
            distortion_data["position"],
            distortion_data["radius"],
            self.map_distortion_type(distortion_data["type"])
        )
        self.status_bar.showMessage(f"现实扭曲场已创建: {field_id}")
    
    def map_distortion_type(self, type_name):
        """映射扭曲类型名称"""
        mapping = {
            "时间膨胀": "time_dilation",
            "重力偏移": "gravity_shift",
            "量子涨落": "quantum_fluctuation",
            "空间压缩": "space_compression",
            "现实重构": "reality_reconstruction",
            "法则覆写": "law_override"
        }
        return mapping.get(type_name, "quantum_fluctuation")
    
    def record_thought(self, thought):
        """记录玩家思维"""
        self.game_state.neural_lace_interface.record_thought_pattern(
            self.game_state.player_id, thought)
    
    def reverse_time(self, duration):
        """时间倒流"""
        result = self.game_state.space_time_manipulator.reverse_time(duration)
        self.status_bar.showMessage(result)
    
    def create_space_fold(self, point_a, point_b):
        """创建空间折叠"""
        fold_id = self.game_state.space_time_manipulator.create_space_fold(point_a, point_b)
        self.status_bar.showMessage(f"空间折叠已创建: {fold_id}")
    
    def visualize_qnn(self):
        """可视化量子神经网络"""
        fig = self.qnn_canvas.figure
        fig.clf()
        ax = fig.add_subplot(111, projection='3d')
        
        # 创建神经网络结构数据
        layers = [4, 8, 6, 3]  # 输入层、隐藏层、量子层、输出层
        
        # 绘制神经网络
        for layer_idx, neurons in enumerate(layers):
            x = np.full(neurons, layer_idx)
            y = np.linspace(0, 1, neurons)
            z = np.zeros(neurons)
            
            # 绘制神经元
            ax.scatter(x, y, z, s=100, c='b', alpha=0.6)
            
            # 绘制连接
            if layer_idx > 0:
                prev_x = np.full(layers[layer_idx-1], layer_idx-1)
                prev_y = np.linspace(0, 1, layers[layer_idx-1])
                prev_z = np.zeros(layers[layer_idx-1])
                
                for i in range(layers[layer_idx-1]):
                    for j in range(neurons):
                        ax.plot(
                            [prev_x[i], x[j]], 
                            [prev_y[i], y[j]], 
                            [prev_z[i], z[j]], 
                            'gray', alpha=0.3
                        )
        
        # 标记量子层
        ax.text(2, 0.5, -0.1, "量子层", fontsize=12, color='r')
        
        ax.set_title("量子神经网络结构")
        ax.set_xlabel("层")
        ax.set_ylabel("神经元")
        ax.set_zlabel("激活")
        self.qnn_canvas.draw()

# ======================
# 启动游戏
# ======================

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 设置超维宇宙主题
    app.setStyle("Fusion")
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(10, 5, 30))
    palette.setColor(QPalette.WindowText, QColor(200, 220, 255))
    palette.setColor(QPalette.Base, QColor(15, 10, 40))
    palette.setColor(QPalette.AlternateBase, QColor(25, 20, 50))
    palette.setColor(QPalette.ToolTipBase, QColor(200, 220, 255))
    palette.setColor(QPalette.ToolTipText, QColor(10, 5, 30))
    palette.setColor(QPalette.Text, QColor(180, 200, 255))
    palette.setColor(QPalette.Button, QColor(30, 25, 60))
    palette.setColor(QPalette.ButtonText, QColor(200, 220, 255))
    palette.setColor(QPalette.BrightText, QColor(255, 100, 100))
    palette.setColor(QPalette.Highlight, QColor(100, 150, 255))
    palette.setColor(QPalette.HighlightedText, QColor(0, 0, 0))
    app.setPalette(palette)
    
    # 加载样式表
    style = """
        QDockWidget {
            titlebar-close-icon: url(close.png);
            titlebar-normal-icon: url(undock.png);
            font-size: 14px;
            font-weight: bold;
            background-color: #1a1a3a;
        }
        QDockWidget::title {
            background-color: #2a2a5a;
            padding: 4px;
        }
        QTabWidget::pane {
            border: 1px solid #444477;
            background: #1a1a3a;
        }
        QTabBar::tab {
            background: #2a2a5a;
            color: #aaccff;
            padding: 8px;
            border: 1px solid #444477;
            border-bottom: none;
        }
        QTabBar::tab:selected {
            background: #3a3a7a;
            color: #ffffff;
        }
        QGroupBox {
            border: 2px solid #444477;
            border-radius: 5px;
            margin-top: 1ex;
            font-weight: bold;
            color: #aaccff;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top center;
            padding: 0 5px;
        }
    """
    app.setStyleSheet(style)
    
    window = HyperVerseGameWindow()
    window.show()
    sys.exit(app.exec_())