"""
《道德经》编程系统 - PyQt5图形界面完整实现
道法自然，无为而治 | Tao Programming System - Complete PyQt5 GUI
"""

import sys
import math
import random
import numpy as np
from typing import List, Dict, Any, Callable, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import time
from functools import wraps
import re

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QTabWidget, QTextEdit, QPushButton, QLabel, QLineEdit, 
                            QComboBox, QSlider, QSpinBox, QDoubleSpinBox, QCheckBox,
                            QGroupBox, QSplitter, QProgressBar, QTableWidget, 
                            QTableWidgetItem, QHeaderView, QMessageBox, QFileDialog,
                            QGraphicsView, QGraphicsScene, QGraphicsItem, QGraphicsEllipseItem,
                            QMenu, QAction, QStatusBar, QToolBar, QDockWidget)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QPointF, QRectF, QSize
from PyQt5.QtGui import QFont, QColor, QPen, QBrush, QPainter, QPalette, QKeySequence
from PyQt5.QtChart import QChart, QChartView, QLineSeries, QValueAxis

# ==================== 核心哲学定义 ====================

class YinYangState(Enum):
    """阴阳状态枚举"""
    YIN = -1    # 阴：收敛、静默、接受
    YANG = 1    # 阳：发散、活跃、创造
    BALANCE = 0 # 平衡态：中庸之道

@dataclass
class TaoVector:
    """道德经向量：描述系统阴阳状态"""
    yin: float    # 阴值 ∈ [0,1]
    yang: float   # 阳值 ∈ [0,1]
    
    def __post_init__(self):
        # 确保值在合理范围内
        self.yin = max(0.0, min(1.0, self.yin))
        self.yang = max(0.0, min(1.0, self.yang))
    
    @property
    def balance(self) -> float:
        """阴阳平衡度"""
        return 1 - abs(self.yin - self.yang)
    
    @property
    def dominance(self) -> YinYangState:
        """主导状态"""
        diff = self.yang - self.yin
        if diff < -0.3:
            return YinYangState.YIN
        elif diff > 0.3:
            return YinYangState.YANG
        return YinYangState.BALANCE
    
    def to_symbol(self) -> str:
        """转化为八卦符号"""
        symbols = {
            (0.8, 0.2): "☵",  # 坎水 - 险陷
            (0.2, 0.8): "☲",  # 离火 - 附丽
            (0.5, 0.5): "☯",  # 太极 - 平衡
            (0.7, 0.3): "☴",  # 巽风 - 顺从
            (0.3, 0.7): "☱",  # 兑泽 - 喜悦
            (0.9, 0.1): "☷",  # 坤地 - 柔顺
            (0.1, 0.9): "☰",  # 乾天 - 刚健
            (0.6, 0.4): "☳",  # 震雷 - 起动
            (0.4, 0.6): "☶",  # 艮山 - 静止
        }
        return symbols.get((round(self.yin, 1), round(self.yang, 1)), "⚋")
    
    def to_hexagram(self) -> str:
        """生成六十四卦名"""
        ratio = self.yang / (self.yin + self.yang) if (self.yin + self.yang) > 0 else 0.5
        
        hexagrams = [
            ("坤", "地地坤", 0.0), ("剥", "山地剥", 0.1), ("比", "水地比", 0.2),
            ("观", "风地观", 0.3), ("豫", "雷地豫", 0.4), ("谦", "地山谦", 0.5),
            ("泰", "地天泰", 0.6), ("大壮", "雷天大壮", 0.7), ("夬", "泽天夬", 0.8),
            ("乾", "天天乾", 0.9)
        ]
        
        return min(hexagrams, key=lambda x: abs(x[2] - ratio))[1]
    
    def to_color(self) -> QColor:
        """转换为颜色表示"""
        # 阴为蓝色调，阳为红色调，平衡为绿色调
        if self.dominance == YinYangState.YIN:
            return QColor(0, int(100 + 155 * self.yin), int(200 + 55 * self.yin))
        elif self.dominance == YinYangState.YANG:
            return QColor(int(200 + 55 * self.yang), int(100 + 155 * self.yang), 0)
        else:
            return QColor(int(100 + 155 * self.balance), 
                         int(200 + 55 * self.balance), 
                         int(100 + 155 * self.balance))

# ==================== 高级混沌系统 ====================

class QuantumTaoState:
    """量子道德状态：叠加态与坍缩"""
    
    def __init__(self, alpha: complex, beta: complex):
        self.alpha = alpha
        self.beta = beta
        
        norm = math.sqrt(abs(alpha)**2 + abs(beta)**2)
        if norm > 0:
            self.alpha /= norm
            self.beta /= norm
    
    def measure(self) -> YinYangState:
        prob_yang = abs(self.beta)**2
        return YinYangState.YANG if random.random() < prob_yang else YinYangState.YIN
    
    def evolve(self, time: float = 1.0):
        """简化量子演化"""
        angle = time * 0.1
        new_alpha = self.alpha * math.cos(angle) - self.beta * math.sin(angle)
        new_beta = self.alpha * math.sin(angle) + self.beta * math.cos(angle)
        
        norm = math.sqrt(abs(new_alpha)**2 + abs(new_beta)**2)
        if norm > 0:
            self.alpha, self.beta = new_alpha/norm, new_beta/norm
    
    def to_tao_vector(self) -> TaoVector:
        prob_yin = abs(self.alpha)**2
        prob_yang = abs(self.beta)**2
        return TaoVector(prob_yin, prob_yang)

class AdvancedTaoCell:
    """高级道元胞：集成多种混沌系统"""
    
    def __init__(self, cell_id: int, position: Tuple[float, float] = (0, 0)):
        self.cell_id = cell_id
        self.position = position
        self.velocity = (random.uniform(-0.1, 0.1), random.uniform(-0.1, 0.1))
        
        self.lorenz_state = np.array([random.uniform(0.1, 1.0) for _ in range(3)])
        self.rossler_state = np.array([random.uniform(0.1, 1.0) for _ in range(3)])
        self.quantum_state = QuantumTaoState(0.7+0j, 0.7+0j)
        
        self.energy = 1.0
        self.wisdom = 0.0
        self.neighbors: List['AdvancedTaoCell'] = []
        
        self.trajectory = [position]
        self.tao_history: List[TaoVector] = []
    
    @property
    def current_tao(self) -> TaoVector:
        lorenz_yang = np.mean(self.lorenz_state)
        rossler_yin = 1.0 - np.mean(self.rossler_state)
        quantum_vec = self.quantum_state.to_tao_vector()
        
        return TaoVector(
            yin=(rossler_yin + quantum_vec.yin) / 2,
            yang=(lorenz_yang + quantum_vec.yang) / 2
        )
    
    def multi_chaos_update(self, dt: float = 0.01):
        """多重混沌系统演化"""
        # 洛伦兹吸引子
        sigma, rho, beta = 10.0, 28.0, 8.0/3.0
        x, y, z = self.lorenz_state
        self.lorenz_state += dt * np.array([
            sigma * (y - x),
            x * (rho - z) - y,
            x * y - beta * z
        ])
        
        # 罗斯勒吸引子
        a, b, c = 0.2, 0.2, 5.7
        x_r, y_r, z_r = self.rossler_state
        self.rossler_state += dt * np.array([
            -y_r - z_r,
            x_r + a * y_r,
            b + z_r * (x_r - c)
        ])
        
        # 量子演化
        self.quantum_state.evolve(dt)
        
        # 位置更新
        self._update_position(dt)
        
        self.tao_history.append(self.current_tao)
        if len(self.tao_history) > 1000:
            self.tao_history.pop(0)
    
    def _update_position(self, dt: float):
        x, y = self.position
        vx, vy = self.velocity
        
        tao = self.current_tao
        vx += (tao.yang - 0.5) * 0.1
        vy += (tao.yin - 0.5) * 0.1
        
        x = (x + vx * dt) % 10.0
        y = (y + vy * dt) % 10.0
        
        self.position = (x, y)
        self.velocity = (vx * 0.99, vy * 0.99)
        self.trajectory.append(self.position)
    
    def compute_tao_entropy(self) -> float:
        if len(self.tao_history) < 2:
            return 0.0
        
        changes = []
        for i in range(1, len(self.tao_history)):
            prev = self.tao_history[i-1]
            curr = self.tao_history[i]
            change = abs(prev.yin - curr.yin) + abs(prev.yang - curr.yang)
            changes.append(change)
        
        return np.std(changes) if changes else 0.0

# ==================== 智能代码生成系统 ====================

class TaoAICodeGenerator:
    """AI驱动的道德经代码生成器"""
    
    def __init__(self):
        self.tao_knowledge_base = self._build_tao_knowledge()
        self.code_templates = self._build_templates()
        self.learned_patterns: Dict[str, float] = {}
    
    def _build_tao_knowledge(self) -> Dict[str, List[str]]:
        return {
            "无为": ["顺其自然，不强行干预", "让事物按其本性发展", "避免过度设计和控制"],
            "柔弱": ["柔软胜过刚强", "灵活性优于僵化", "适应变化的能力"],
            "平衡": ["阴阳调和，不偏不倚", "保持适度和中庸", "动态平衡而非静态"],
            "简约": ["大道至简", "去除不必要的复杂性", "本质优于表象"],
            "自然": ["道法自然", "符合事物本性", "自发秩序的形成"]
        }
    
    def _build_templates(self) -> Dict[str, str]:
        return {
            "algorithm": """
def {name}(data):
    \"\"\"{tao_principle}\"\"\"
    {initialization}
    
    # {tao_insight}
    {core_logic}
    
    return {result}
""",
            "class": """
class {name}:
    \"\"\"{tao_principle}\"\"\"
    
    def __init__(self{parameters}):
        {setup}
    
    def {main_method}(self, data):
        \"\"\"{method_insight}\"\"\"
        {implementation}
        return {result}
"""
        }
    
    def generate_tao_algorithm(self, tao_vector: TaoVector, complexity: int = 3) -> str:
        principle = self._select_principle(tao_vector)
        name = self._generate_tao_name(tao_vector)
        
        template = self.code_templates["algorithm"]
        components = self._generate_algorithm_components(tao_vector, complexity)
        
        code = template.format(
            name=name,
            tao_principle=principle,
            tao_insight=self._get_tao_insight(tao_vector),
            **components
        )
        
        return self._add_tao_comments(code, tao_vector)
    
    def _select_principle(self, tao_vector: TaoVector) -> str:
        if tao_vector.dominance == YinYangState.YIN:
            principles = ["无为", "柔弱", "简约"]
        elif tao_vector.dominance == YinYangState.YANG:
            principles = ["自然", "平衡"] 
        else:
            principles = ["平衡", "自然", "简约"]
        return random.choice(principles)
    
    def _generate_tao_name(self, tao_vector: TaoVector) -> str:
        base_names = {
            YinYangState.YIN: ["静", "柔", "虚", "纳", "容"],
            YinYangState.YANG: ["动", "刚", "实", "创", "发"],
            YinYangState.BALANCE: ["和", "中", "平", "调", "衡"]
        }
        prefixes = ["道", "德", "自", "天", "地"]
        name1 = random.choice(prefixes)
        name2 = random.choice(base_names[tao_vector.dominance])
        return f"{name1}{name2}_algorithm"
    
    def _generate_algorithm_components(self, tao_vector: TaoVector, complexity: int) -> Dict[str, str]:
        if tao_vector.dominance == YinYangState.YIN:
            initialization = "state = data"
            core_logic = self._generate_yin_logic(complexity)
            result = "state"
        elif tao_vector.dominance == YinYangState.YANG:
            initialization = "result = []\n    for item in data:"
            core_logic = self._generate_yang_logic(complexity)
            result = "result"
        else:
            initialization = "# 平衡初始化\n    working_data = data.copy()"
            core_logic = self._generate_balance_logic(complexity)
            result = "working_data"
        
        return {
            "initialization": initialization,
            "core_logic": core_logic,
            "result": result
        }
    
    def _generate_yin_logic(self, complexity: int) -> str:
        operations = [
            "# 阴之静：过滤与转化\n        state = list(filter(lambda x: x > 0, state))",
            "# 阴之柔：映射转换\n        state = list(map(lambda x: x * 0.5, state))",
            "# 阴之纳：累积吸收\n        state = [sum(state[:i+1]) for i in range(len(state))]",
            "# 阴之容：去重包容\n        state = list(set(state))"
        ]
        return '\n    '.join(random.sample(operations, min(complexity, len(operations))))
    
    def _generate_yang_logic(self, complexity: int) -> str:
        operations = [
            "# 阳之动：积极处理\n        result.append(item * 2)",
            "# 阳之创：创造新值\n        result.append(item ** 2)",
            "# 阳之发：扩展发散\n        result.extend([item, item + 1])",
            "# 阳之实：条件创造\n        if item % 2 == 0:\n            result.append(item)"
        ]
        return '\n        '.join(random.sample(operations, min(complexity, len(operations))))
    
    def _generate_balance_logic(self, complexity: int) -> str:
        operations = [
            "# 阴阳调和：过滤与映射\n        working_data = [x*2 for x in working_data if x > 0]",
            "# 动态平衡：条件处理\n        if len(working_data) > 1:\n            working_data = sorted(working_data)",
            "# 中庸之道：取中值\n        mid = len(working_data) // 2\n        working_data = working_data[max(0, mid-1):min(len(working_data), mid+2)]"
        ]
        return '\n    '.join(random.sample(operations, min(complexity, len(operations))))
    
    def _get_tao_insight(self, tao_vector: TaoVector) -> str:
        insights = {
            YinYangState.YIN: [
                "上善若水，水善利万物而不争",
                "柔弱胜刚强，无为而无所不为",
                "知其雄，守其雌，为天下溪"
            ],
            YinYangState.YANG: [
                "道生一，一生二，二生三，三生万物",
                "反者道之动，弱者道之用", 
                "大方无隅，大器晚成，大音希声"
            ],
            YinYangState.BALANCE: [
                "万物负阴而抱阳，冲气以为和",
                "知足不辱，知止不殆，可以长久",
                "治大国若烹小鲜"
            ]
        }
        return random.choice(insights[tao_vector.dominance])
    
    def _add_tao_comments(self, code: str, tao_vector: TaoVector) -> str:
        symbol = tao_vector.to_symbol()
        hexagram = tao_vector.to_hexagram()
        
        header = f'''"""
{symbol} 《道德经》编程系统
卦象: {hexagram}
阴阳状态: 阴({tao_vector.yin:.3f}) 阳({tao_vector.yang:.3f}) 平衡({tao_vector.balance:.3f})
生成时间: {time.strftime("%Y-%m-%d %H:%M:%S")}
原则: {self._select_principle(tao_vector)}
"""\n\n'''
        
        return header + code

# ==================== 道德经AI对话系统 ====================

class TaoAIChatbot:
    """道德经AI对话机器人"""
    
    def __init__(self):
        self.tao_wisdom = self._load_tao_wisdom()
        self.conversation_history: List[Dict[str, str]] = []
        self.understanding_level = 0.0
    
    def _load_tao_wisdom(self) -> Dict[str, List[str]]:
        return {
            "无为": ["无为而无所不为。", "道常无为而无不为。", "为无为，事无事，味无味。"],
            "自然": ["人法地，地法天，天法道，道法自然。", "道之尊，德之贵，夫莫之命而常自然。", "辅万物之自然而不敢为。"],
            "平衡": ["万物负阴而抱阳，冲气以为和。", "知足不辱，知止不殆，可以长久。", "持而盈之，不如其已。"],
            "简约": ["少则得，多则惑。", "大道至简。", "为学日益，为道日损。"]
        }
    
    def chat(self, user_input: str) -> str:
        intent = self._analyze_intent(user_input)
        tao_context = self._get_tao_context(intent)
        
        response = self._generate_response(user_input, intent, tao_context)
        
        self.conversation_history.append({
            "user": user_input,
            "ai": response,
            "intent": intent,
            "timestamp": time.time()
        })
        
        self.understanding_level = min(1.0, self.understanding_level + 0.01)
        
        return response
    
    def _analyze_intent(self, text: str) -> str:
        text = text.lower()
        if any(word in text for word in ["如何", "怎样", "怎么", "方法"]):
            return "method"
        elif any(word in text for word in ["为什么", "原因", "道理"]):
            return "why" 
        elif any(word in text for word in ["是什么", "定义", "意思"]):
            return "definition"
        elif any(word in text for word in ["例子", "示例", "实例"]):
            return "example"
        else:
            return "general"
    
    def _get_tao_context(self, intent: str) -> Dict[str, Any]:
        if self.conversation_history:
            available_principles = [p for p in self.tao_wisdom.keys() 
                                  if not any(p in msg["ai"] for msg in self.conversation_history[-3:])]
        else:
            available_principles = list(self.tao_wisdom.keys())
        
        principle = random.choice(available_principles) if available_principles else "无为"
        wisdom = random.choice(self.tao_wisdom[principle])
        
        return {
            "principle": principle,
            "wisdom": wisdom,
            "intent": intent,
            "understanding": self.understanding_level
        }
    
    def _generate_response(self, user_input: str, intent: str, context: Dict[str, Any]) -> str:
        principle = context["principle"]
        wisdom = context["wisdom"]
        
        if intent == "method":
            responses = [
                f"关于'{user_input}'，道德经教导我们：{wisdom}\n\n应用方法：{self._get_method_advice(principle)}",
                f"从《道德经》的角度，处理'{user_input}'应该：{self._get_tao_approach(principle)}\n\n经典智慧：{wisdom}"
            ]
        elif intent == "why":
            responses = [
                f"道德经对此的洞见是：{wisdom}\n\n这是因为{self._get_tao_reasoning(principle)}",
                f"《道德经》告诉我们：{wisdom}\n\n其中的道理在于：{self._get_deeper_meaning(principle)}"
            ]
        elif intent == "definition":
            responses = [
                f"根据《道德经》，这体现了'{principle}'的原则：{wisdom}\n\n{self._get_principle_definition(principle)}",
                f"道德经中的相关智慧：{wisdom}\n\n这反映了{principle}的思想：{self._get_tao_explanation(principle)}"
            ]
        else:
            responses = [
                f"{wisdom}\n\n这对'{user_input}'的启示是：{self._get_general_insight(principle)}",
                f"想起道德经的教导：{wisdom}\n\n或许这对您思考'{user_input}'有所启发"
            ]
        
        response = random.choice(responses)
        
        if self.understanding_level > 0.5:
            response += f"\n\n（基于您之前的对话，我注意到您对道德经的理解正在深化）"
        
        return response
    
    def _get_method_advice(self, principle: str) -> str:
        advice = {
            "无为": "顺应事物本性，不强求不控制，让解决方案自然显现",
            "自然": "找到最符合事物本质的方法，避免人为复杂化",
            "平衡": "在各种因素间找到中点，保持动态平衡",
            "简约": "从简单处着手，去除不必要的复杂性"
        }
        return advice.get(principle, "静心思考，答案自现")
    
    def get_conversation_summary(self) -> str:
        if not self.conversation_history:
            return "尚未开始对话"
        
        principles_mentioned = []
        for conv in self.conversation_history:
            for principle in self.tao_wisdom.keys():
                if principle in conv["ai"]:
                    principles_mentioned.append(principle)
        
        if principles_mentioned:
            most_common = max(set(principles_mentioned), key=principles_mentioned.count)
            return f"对话中主要探讨了'{most_common}'的原则，您的理解水平：{self.understanding_level:.1%}"
        else:
            return f"已进行{len(self.conversation_history)}轮对话，理解水平：{self.understanding_level:.1%}"

    def _get_tao_approach(self, principle: str) -> str:
        approaches = {
            "无为": "以不干预为干预，以无为实现有为",
            "自然": "效法自然规律，如水之就下",
            "平衡": "执两用中，不偏不倚",
            "简约": "返璞归真，抓住本质"
        }
        return approaches.get(principle, "顺应道的方式")
    
    def _get_tao_reasoning(self, principle: str) -> str:
        reasoning = {
            "无为": "过度干预反而破坏事物的自然秩序",
            "自然": "道法自然，违背自然规律必受其害", 
            "平衡": "物极必反，唯有平衡可以长久",
            "简约": "简单之中蕴含着深刻的真理"
        }
        return reasoning.get(principle, "这是道的运行规律")
    
    def _get_general_insight(self, principle: str) -> str:
        insights = {
            "无为": "不强求，不控制，顺应自然规律",
            "自然": "遵循事物本性，不人为干预",
            "平衡": "保持适度，避免极端",
            "简约": "回归简单，去除不必要的复杂"
        }
        return insights.get(principle, "道法自然，无为而治")
    
    def _get_deeper_meaning(self, principle: str) -> str:
        meanings = {
            "无为": "不是不作为，而是不违背自然规律的作为",
            "自然": "万物本来的样子，道的运行方式",
            "平衡": "阴阳调和，动态稳定的状态",
            "简约": "本质的体现，去除表象的干扰"
        }
        return meanings.get(principle, "道的深远智慧")
    
    def _get_principle_definition(self, principle: str) -> str:
        definitions = {
            "无为": "顺应自然，不强求不干预的智慧",
            "自然": "道的本质，万物运行的规律",
            "平衡": "阴阳调和，不偏不倚的状态",
            "简约": "去除复杂，回归本真的方法"
        }
        return definitions.get(principle, "道德经的核心原则")
    
    def _get_tao_explanation(self, principle: str) -> str:
        explanations = {
            "无为": "道常无为而无不为，侯王若能守之，万物将自化",
            "natural": "人法地，地法天，天法道，道法自然",
            "balance": "万物负阴而抱阳，冲气以为和",
            "simple": "为学日益，为道日损。损之又损，以至于无为"
        }
        return explanations.get(principle, "道德经的深邃智慧")

# ==================== PyQt5图形界面组件 ====================

class TaoCellGraphicsItem(QGraphicsEllipseItem):
    """道德经元胞图形项"""
    
    def __init__(self, cell: AdvancedTaoCell, size: float = 20.0):
        super().__init__(0, 0, size, size)
        self.cell = cell
        self.size = size
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.update_appearance()
    
    def update_appearance(self):
        """更新外观"""
        tao = self.cell.current_tao
        color = tao.to_color()
        
        # 设置颜色
        self.setBrush(QBrush(color))
        self.setPen(QPen(Qt.black, 1))
        
        # 设置位置
        x, y = self.cell.position
        self.setPos(x * 50, y * 50)  # 缩放位置
        
        # 设置透明度基于能量
        self.setOpacity(self.cell.energy)
    
    def mouseDoubleClickEvent(self, event):
        """双击显示详细信息"""
        tao = self.cell.current_tao
        info = f"元胞 {self.cell.cell_id}\n位置: {self.cell.position}\n阴: {tao.yin:.3f}\n阳: {tao.yang:.3f}\n熵: {self.cell.compute_tao_entropy():.3f}"
        QMessageBox.information(None, "元胞信息", info)
        super().mouseDoubleClickEvent(event)

class TaoGraphicsView(QGraphicsView):
    """道德经图形视图"""
    
    def __init__(self):
        super().__init__()
        self.scene = QGraphicsScene()
        self.setScene(self.scene)
        self.setRenderHint(QPainter.Antialiasing)
        self.cell_items: Dict[int, TaoCellGraphicsItem] = {}
        
        # 设置背景
        self.setBackgroundBrush(QBrush(QColor(240, 240, 235)))
    
    def update_cells(self, cells: List[AdvancedTaoCell]):
        """更新元胞显示"""
        # 移除不存在的元胞
        current_ids = {cell.cell_id for cell in cells}
        for cell_id in list(self.cell_items.keys()):
            if cell_id not in current_ids:
                item = self.cell_items.pop(cell_id)
                self.scene.removeItem(item)
        
        # 添加或更新元胞
        for cell in cells:
            if cell.cell_id in self.cell_items:
                # 更新现有元胞
                self.cell_items[cell.cell_id].update_appearance()
            else:
                # 添加新元胞
                item = TaoCellGraphicsItem(cell)
                self.cell_items[cell.cell_id] = item
                self.scene.addItem(item)
        
        # 更新场景矩形
        if self.cell_items:
            self.scene.setSceneRect(self.scene.itemsBoundingRect())

class CodeEditor(QTextEdit):
    """代码编辑器"""
    
    def __init__(self):
        super().__init__()
        self.setFont(QFont("Consolas", 10))
        self.setStyleSheet("QTextEdit { background-color: #f8f8f8; }")
    
    def set_python_code(self, code: str):
        """设置Python代码"""
        self.setPlainText(code)

class ChatWidget(QWidget):
    """聊天组件"""
    
    message_sent = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 聊天历史
        self.history = QTextEdit()
        self.history.setReadOnly(True)
        self.history.setFont(QFont("微软雅黑", 9))
        layout.addWidget(QLabel("道德经AI对话"))
        layout.addWidget(self.history)
        
        # 输入区域
        input_layout = QHBoxLayout()
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("输入您的问题...")
        self.input_field.returnPressed.connect(self.send_message)
        
        self.send_btn = QPushButton("发送")
        self.send_btn.clicked.connect(self.send_message)
        
        input_layout.addWidget(self.input_field)
        input_layout.addWidget(self.send_btn)
        layout.addLayout(input_layout)
        
        self.setLayout(layout)
    
    def send_message(self):
        message = self.input_field.text().strip()
        if message:
            self.message_sent.emit(message)
            self.input_field.clear()
    
    def add_message(self, sender: str, message: str):
        """添加消息到历史"""
        timestamp = time.strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {sender}: {message}\n"
        self.history.append(formatted_message)
        
        # 自动滚动到底部
        scrollbar = self.history.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

class TaoDashboard(QWidget):
    """系统仪表盘"""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 系统状态组
        status_group = QGroupBox("系统状态")
        status_layout = QVBoxLayout()
        
        self.health_bar = QProgressBar()
        self.health_bar.setRange(0, 100)
        self.health_bar.setFormat("系统健康度: %p%")
        
        self.yin_label = QLabel("阴: 0.000")
        self.yang_label = QLabel("阳: 0.000") 
        self.balance_label = QLabel("平衡: 0.000")
        self.entropy_label = QLabel("平均熵: 0.000")
        
        status_layout.addWidget(self.health_bar)
        status_layout.addWidget(self.yin_label)
        status_layout.addWidget(self.yang_label)
        status_layout.addWidget(self.balance_label)
        status_layout.addWidget(self.entropy_label)
        status_group.setLayout(status_layout)
        
        # 统计信息组
        stats_group = QGroupBox("统计信息")
        stats_layout = QVBoxLayout()
        
        self.cell_count_label = QLabel("元胞数量: 0")
        self.active_cells_label = QLabel("活跃元胞: 0")
        self.evolution_steps_label = QLabel("演化步数: 0")
        self.understanding_label = QLabel("AI理解度: 0%")
        
        stats_layout.addWidget(self.cell_count_label)
        stats_layout.addWidget(self.active_cells_label)
        stats_layout.addWidget(self.evolution_steps_label)
        stats_layout.addWidget(self.understanding_label)
        stats_group.setLayout(stats_layout)
        
        layout.addWidget(status_group)
        layout.addWidget(stats_group)
        layout.addStretch()
        
        self.setLayout(layout)
    
    def update_stats(self, system: 'CompleteTaoSystem'):
        """更新统计信息"""
        # 计算统计数据
        cells = system.cells
        total_cells = len(cells)
        active_cells = sum(1 for cell in cells if cell.compute_tao_entropy() > 0.1)
        
        yin_count = sum(1 for cell in cells if cell.current_tao.dominance == YinYangState.YIN)
        yang_count = sum(1 for cell in cells if cell.current_tao.dominance == YinYangState.YANG)
        balance_count = total_cells - yin_count - yang_count
        
        avg_yin = np.mean([cell.current_tao.yin for cell in cells])
        avg_yang = np.mean([cell.current_tao.yang for cell in cells])
        avg_balance = np.mean([cell.current_tao.balance for cell in cells])
        avg_entropy = np.mean([cell.compute_tao_entropy() for cell in cells])
        
        # 更新界面
        self.health_bar.setValue(int(system.system_health * 100))
        self.yin_label.setText(f"阴: {avg_yin:.3f}")
        self.yang_label.setText(f"阳: {avg_yang:.3f}")
        self.balance_label.setText(f"平衡: {avg_balance:.3f}")
        self.entropy_label.setText(f"平均熵: {avg_entropy:.3f}")
        
        self.cell_count_label.setText(f"元胞数量: {total_cells}")
        self.active_cells_label.setText(f"活跃元胞: {active_cells}")
        self.evolution_steps_label.setText(f"演化步数: {system.evolution_steps}")
        self.understanding_label.setText(f"AI理解度: {system.chatbot.understanding_level:.1%}")

class ControlPanel(QWidget):
    """控制面板"""
    
    evolution_started = pyqtSignal()
    evolution_stopped = pyqtSignal()
    evolution_reset = pyqtSignal()
    cell_count_changed = pyqtSignal(int)
    
    def __init__(self):
        super().__init__()
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 演化控制组
        control_group = QGroupBox("演化控制")
        control_layout = QVBoxLayout()
        
        self.start_btn = QPushButton("开始演化")
        self.stop_btn = QPushButton("停止演化")
        self.reset_btn = QPushButton("重置系统")
        
        self.stop_btn.setEnabled(False)
        
        control_layout.addWidget(self.start_btn)
        control_layout.addWidget(self.stop_btn)
        control_layout.addWidget(self.reset_btn)
        control_group.setLayout(control_layout)
        
        # 参数设置组
        params_group = QGroupBox("系统参数")
        params_layout = QVBoxLayout()
        
        # 元胞数量
        cell_layout = QHBoxLayout()
        cell_layout.addWidget(QLabel("元胞数量:"))
        self.cell_spin = QSpinBox()
        self.cell_spin.setRange(1, 100)
        self.cell_spin.setValue(16)
        cell_layout.addWidget(self.cell_spin)
        params_layout.addLayout(cell_layout)
        
        # 演化速度
        speed_layout = QHBoxLayout()
        speed_layout.addWidget(QLabel("演化速度:"))
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setRange(1, 100)
        self.speed_slider.setValue(50)
        speed_layout.addWidget(self.speed_slider)
        params_layout.addLayout(speed_layout)
        
        # 混沌强度
        chaos_layout = QHBoxLayout()
        chaos_layout.addWidget(QLabel("混沌强度:"))
        self.chaos_spin = QDoubleSpinBox()
        self.chaos_spin.setRange(0.1, 2.0)
        self.chaos_spin.setValue(1.0)
        self.chaos_spin.setSingleStep(0.1)
        chaos_layout.addWidget(self.chaos_spin)
        params_layout.addLayout(chaos_layout)
        
        params_group.setLayout(params_layout)
        
        # 代码生成组
        code_group = QGroupBox("代码生成")
        code_layout = QVBoxLayout()
        
        self.generate_code_btn = QPushButton("生成道德经代码")
        self.complexity_spin = QSpinBox()
        self.complexity_spin.setRange(1, 5)
        self.complexity_spin.setValue(3)
        self.complexity_spin.setPrefix("复杂度: ")
        
        code_layout.addWidget(self.generate_code_btn)
        code_layout.addWidget(self.complexity_spin)
        code_group.setLayout(code_layout)
        
        layout.addWidget(control_group)
        layout.addWidget(params_group)
        layout.addWidget(code_group)
        layout.addStretch()
        
        self.setLayout(layout)
        
        # 连接信号
        self.start_btn.clicked.connect(self.evolution_started)
        self.stop_btn.clicked.connect(self.evolution_stopped)
        self.reset_btn.clicked.connect(self.evolution_reset)
        self.cell_spin.valueChanged.connect(self.cell_count_changed)

class MainWindow(QMainWindow):
    """主窗口"""
    
    def __init__(self):
        super().__init__()
        self.tao_system = CompleteTaoSystem(num_cells=16)
        self.evolution_timer = QTimer()
        self.init_ui()
        self.connect_signals()
    
    def init_ui(self):
        self.setWindowTitle("《道德经》编程系统 - 道法自然")
        self.setGeometry(100, 100, 1400, 900)
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QHBoxLayout()
        central_widget.setLayout(main_layout)
        
        # 左侧控制面板
        self.control_panel = ControlPanel()
        self.control_panel.setMaximumWidth(300)
        main_layout.addWidget(self.control_panel)
        
        # 右侧选项卡
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        # 创建各个选项卡
        self.create_evolution_tab()
        self.create_code_tab()
        self.create_chat_tab()
        self.create_analysis_tab()
        
        # 创建状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("系统就绪 - 道法自然，无为而治")
        
        # 创建工具栏
        self.create_toolbar()
        
        # 创建停靠窗口
        self.create_dock_windows()
    
    def create_toolbar(self):
        toolbar = QToolBar("主工具栏")
        self.addToolBar(toolbar)
        
        # 添加工具栏动作
        start_action = QAction("开始演化", self)
        start_action.triggered.connect(self.control_panel.evolution_started)
        toolbar.addAction(start_action)
        
        stop_action = QAction("停止演化", self)
        stop_action.triggered.connect(self.control_panel.evolution_stopped)
        toolbar.addAction(stop_action)
        
        toolbar.addSeparator()
        
        export_action = QAction("导出状态", self)
        export_action.triggered.connect(self.export_system_state)
        toolbar.addAction(export_action)
    
    def create_dock_windows(self):
        # 仪表盘停靠窗口
        self.dashboard = TaoDashboard()
        dashboard_dock = QDockWidget("系统仪表盘", self)
        dashboard_dock.setWidget(self.dashboard)
        self.addDockWidget(Qt.RightDockWidgetArea, dashboard_dock)
    
    def create_evolution_tab(self):
        """创建演化选项卡"""
        tab = QWidget()
        layout = QVBoxLayout()
        
        # 图形视图
        self.graphics_view = TaoGraphicsView()
        layout.addWidget(self.graphics_view)
        
        # 信息显示
        info_layout = QHBoxLayout()
        self.current_tao_label = QLabel("当前状态: 初始化中...")
        self.hexagram_label = QLabel("卦象: --")
        info_layout.addWidget(self.current_tao_label)
        info_layout.addWidget(self.hexagram_label)
        info_layout.addStretch()
        
        layout.addLayout(info_layout)
        tab.setLayout(layout)
        self.tab_widget.addTab(tab, "🐉 道元演化")
    
    def create_code_tab(self):
        """创建代码选项卡"""
        tab = QWidget()
        layout = QVBoxLayout()
        
        # 代码编辑器
        self.code_editor = CodeEditor()
        layout.addWidget(QLabel("道德经代码生成器"))
        layout.addWidget(self.code_editor)
        
        # 代码操作按钮
        button_layout = QHBoxLayout()
        self.save_code_btn = QPushButton("保存代码")
        self.copy_code_btn = QPushButton("复制代码")
        self.execute_code_btn = QPushButton("执行代码")
        
        button_layout.addWidget(self.save_code_btn)
        button_layout.addWidget(self.copy_code_btn)
        button_layout.addWidget(self.execute_code_btn)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        tab.setLayout(layout)
        self.tab_widget.addTab(tab, "📜 道码生成")
    
    def create_chat_tab(self):
        """创建聊天选项卡"""
        tab = QWidget()
        layout = QVBoxLayout()
        
        # 聊天组件
        self.chat_widget = ChatWidget()
        layout.addWidget(self.chat_widget)
        
        tab.setLayout(layout)
        self.tab_widget.addTab(tab, "💭 道德对话")
    
    def create_analysis_tab(self):
        """创建分析选项卡"""
        tab = QWidget()
        layout = QVBoxLayout()
        
        # 创建表格显示元胞状态
        self.cell_table = QTableWidget()
        self.cell_table.setColumnCount(6)
        self.cell_table.setHorizontalHeaderLabels(["ID", "位置", "阴", "阳", "平衡", "熵"])
        self.cell_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        layout.addWidget(QLabel("元胞状态分析"))
        layout.addWidget(self.cell_table)
        
        tab.setLayout(layout)
        self.tab_widget.addTab(tab, "📊 道统分析")
    
    def connect_signals(self):
        """连接信号和槽"""
        # 控制面板信号
        self.control_panel.evolution_started.connect(self.start_evolution)
        self.control_panel.evolution_stopped.connect(self.stop_evolution)
        self.control_panel.evolution_reset.connect(self.reset_system)
        self.control_panel.cell_count_changed.connect(self.change_cell_count)
        self.control_panel.generate_code_btn.clicked.connect(self.generate_code)
        
        # 聊天信号
        self.chat_widget.message_sent.connect(self.handle_chat_message)
        
        # 代码操作信号
        self.save_code_btn.clicked.connect(self.save_code)
        self.copy_code_btn.clicked.connect(self.copy_code)
        self.execute_code_btn.clicked.connect(self.execute_code)
        
        # 定时器信号
        self.evolution_timer.timeout.connect(self.evolution_step)
    
    def start_evolution(self):
        """开始演化"""
        self.evolution_timer.start(100)  # 每100ms更新一次
        self.control_panel.start_btn.setEnabled(False)
        self.control_panel.stop_btn.setEnabled(True)
        self.status_bar.showMessage("系统演化中...")
    
    def stop_evolution(self):
        """停止演化"""
        self.evolution_timer.stop()
        self.control_panel.start_btn.setEnabled(True)
        self.control_panel.stop_btn.setEnabled(False)
        self.status_bar.showMessage("系统已暂停")
    
    def reset_system(self):
        """重置系统"""
        self.stop_evolution()
        cell_count = self.control_panel.cell_spin.value()
        self.tao_system = CompleteTaoSystem(num_cells=cell_count)
        self.update_display()
        self.status_bar.showMessage("系统已重置")
    
    def change_cell_count(self, count: int):
        """改变元胞数量"""
        if not self.evolution_timer.isActive():
            self.tao_system = CompleteTaoSystem(num_cells=count)
            self.update_display()
    
    def evolution_step(self):
        """演化步骤"""
        # 更新系统
        speed = self.control_panel.speed_slider.value() / 50.0
        for cell in self.tao_system.cells:
            cell.multi_chaos_update(0.01 * speed)
        
        self.tao_system.evolution_steps += 1
        self.tao_system._update_system_health()
        
        # 更新显示
        self.update_display()
    
    def update_display(self):
        """更新所有显示"""
        # 更新图形视图
        self.graphics_view.update_cells(self.tao_system.cells)
        
        # 更新状态标签
        if self.tao_system.cells:
            balanced_cell = min(self.tao_system.cells, 
                              key=lambda c: abs(c.current_tao.yin - c.current_tao.yang))
            tao = balanced_cell.current_tao
            self.current_tao_label.setText(
                f"当前状态: 阴({tao.yin:.3f}) 阳({tao.yang:.3f}) 平衡({tao.balance:.3f}) {tao.to_symbol()}")
            self.hexagram_label.setText(f"卦象: {tao.to_hexagram()}")
        
        # 更新仪表盘
        self.dashboard.update_stats(self.tao_system)
        
        # 更新分析表格
        self.update_analysis_table()
    
    def update_analysis_table(self):
        """更新分析表格"""
        self.cell_table.setRowCount(len(self.tao_system.cells))
        
        for i, cell in enumerate(self.tao_system.cells):
            tao = cell.current_tao
            self.cell_table.setItem(i, 0, QTableWidgetItem(str(cell.cell_id)))
            self.cell_table.setItem(i, 1, QTableWidgetItem(f"({cell.position[0]:.1f}, {cell.position[1]:.1f})"))
            self.cell_table.setItem(i, 2, QTableWidgetItem(f"{tao.yin:.3f}"))
            self.cell_table.setItem(i, 3, QTableWidgetItem(f"{tao.yang:.3f}"))
            self.cell_table.setItem(i, 4, QTableWidgetItem(f"{tao.balance:.3f}"))
            self.cell_table.setItem(i, 5, QTableWidgetItem(f"{cell.compute_tao_entropy():.3f}"))
    
    def generate_code(self):
        """生成代码"""
        if self.tao_system.cells:
            cell = random.choice(self.tao_system.cells)
            complexity = self.control_panel.complexity_spin.value()
            code = self.tao_system.code_generator.generate_tao_algorithm(cell.current_tao, complexity)
            self.code_editor.set_python_code(code)
            self.status_bar.showMessage("道德经代码已生成")
    
    def handle_chat_message(self, message: str):
        """处理聊天消息"""
        self.chat_widget.add_message("您", message)
        response = self.tao_system.chatbot.chat(message)
        self.chat_widget.add_message("道德经AI", response)
    
    def save_code(self):
        """保存代码"""
        file_path, _ = QFileDialog.getSaveFileName(self, "保存代码", "", "Python Files (*.py)")
        if file_path:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(self.code_editor.toPlainText())
            self.status_bar.showMessage(f"代码已保存到: {file_path}")
    
    def copy_code(self):
        """复制代码到剪贴板"""
        clipboard = QApplication.clipboard()
        clipboard.setText(self.code_editor.toPlainText())
        self.status_bar.showMessage("代码已复制到剪贴板")
    
    def execute_code(self):
        """执行代码（演示用）"""
        code = self.code_editor.toPlainText()
        try:
            # 这里应该在实际环境中更安全地执行代码
            # 这里只是演示
            QMessageBox.information(self, "代码执行", "代码执行功能在演示版本中受限")
        except Exception as e:
            QMessageBox.warning(self, "执行错误", f"代码执行出错: {e}")
    
    def export_system_state(self):
        """导出系统状态"""
        file_path, _ = QFileDialog.getSaveFileName(self, "导出系统状态", "", "JSON Files (*.json)")
        if file_path:
            state = self.tao_system.export_system_state()
            import json
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
            self.status_bar.showMessage(f"系统状态已导出到: {file_path}")

# ==================== 完整系统集成 ====================

class CompleteTaoSystem:
    """完整的道德经编程系统"""
    
    def __init__(self, num_cells: int = 16):
        self.cells = [AdvancedTaoCell(i, (random.uniform(0, 10), random.uniform(0, 10))) 
                     for i in range(num_cells)]
        
        self._connect_tao_network()
        
        self.code_generator = TaoAICodeGenerator()
        self.chatbot = TaoAIChatbot()
        
        self.evolution_steps = 0
        self.generated_codes = []
        self.system_health = 1.0
    
    def _connect_tao_network(self):
        """连接道德经网络"""
        for i, cell in enumerate(self.cells):
            num_neighbors = random.randint(3, 5)
            possible_neighbors = [c for j, c in enumerate(self.cells) if j != i]
            cell.neighbors = random.sample(possible_neighbors, 
                                         min(num_neighbors, len(possible_neighbors)))
    
    def _update_system_health(self):
        """更新系统健康度"""
        entropies = [cell.compute_tao_entropy() for cell in self.cells]
        avg_entropy = np.mean(entropies)
        
        if 0.05 < avg_entropy < 0.5:
            self.system_health = min(1.0, self.system_health + 0.01)
        else:
            self.system_health = max(0.0, self.system_health - 0.02)
    
    def export_system_state(self) -> Dict[str, Any]:
        """导出系统状态"""
        return {
            "evolution_steps": self.evolution_steps,
            "system_health": self.system_health,
            "cell_states": [
                {
                    "id": cell.cell_id,
                    "position": cell.position,
                    "tao_vector": {
                        "yin": cell.current_tao.yin,
                        "yang": cell.current_tao.yang,
                        "symbol": cell.current_tao.to_symbol()
                    },
                    "entropy": cell.compute_tao_entropy()
                }
                for cell in self.cells
            ],
            "conversation_summary": self.chatbot.get_conversation_summary(),
            "generated_codes_count": len(self.generated_codes)
        }

# ==================== 应用程序入口 ====================

def main():
    """主函数"""
    app = QApplication(sys.argv)
    
    # 设置应用程序样式
    app.setStyle('Fusion')
    
    # 创建并显示主窗口
    window = MainWindow()
    window.show()
    
    # 显示启动消息
    QMessageBox.information(window, "欢迎", 
        "欢迎使用《道德经》编程系统！\n\n"
        "这是一个融合东方哲学与计算机科学的创新平台。\n"
        "系统基于道德经原理，实现自组织代码生成和智能对话。\n\n"
        "道法自然，无为而治。")
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()