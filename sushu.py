import sys
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
matplotlib.rc("font", family='Microsoft YaHei')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QTabWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTextEdit, QLabel, QComboBox, QLineEdit, QListWidget, 
    QListWidgetItem, QSplitter, QGroupBox, QFormLayout, QSlider
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QColor
import networkx as nx
from datetime import datetime
import json
from enum import Enum
import random

class StrategyDomain(Enum):
    GOVERNANCE = "治国"  # 治理策略
    MILITARY = "用兵"    # 军事策略
    PERSONNEL = "用人"   # 人才策略
    CRISIS = "危机"      # 危机处理
    SELF = "修身"       # 个人修养

class HistoricalCase:
    """历史案例数据库"""
    def __init__(self):
        self.cases = self._load_cases()
    
    def _load_cases(self):
        return {
            "汉初三杰": {
                "domain": StrategyDomain.PERSONNEL,
                "description": "刘邦善用张良、萧何、韩信三人之长",
                "strategy": "任疑则危",
                "factors": {"明察": 0.9, "度权": 0.95, "揣情": 0.85, "钓语": 0.7},
                "outcome": 0.95,
                "era": "秦汉"
            },
            "赤壁之战": {
                "domain": StrategyDomain.MILITARY,
                "description": "周瑜火烧赤壁以弱胜强",
                "strategy": "见微知著",
                "factors": {"见微": 0.8, "知著": 0.9, "决断": 0.95},
                "outcome": 0.9,
                "era": "三国"
            },
            "贞观之治": {
                "domain": StrategyDomain.GOVERNANCE,
                "description": "唐太宗纳谏如流，以德治国",
                "strategy": "德足以怀远",
                "factors": {"法": 0.7, "术": 0.6, "势": 0.8, "德": 0.95},
                "outcome": 0.98,
                "era": "唐"
            },
            "商鞅变法": {
                "domain": StrategyDomain.GOVERNANCE,
                "description": "商鞅在秦国推行变法",
                "strategy": "设变致权所以解结",
                "factors": {"法": 0.95, "术": 0.8, "势": 0.7, "德": 0.5},
                "outcome": 0.85,
                "era": "战国"
            },
            "韩信拜将": {
                "domain": StrategyDomain.PERSONNEL,
                "description": "刘邦拜韩信为大将",
                "strategy": "用人之智去其诈",
                "factors": {"明察": 0.85, "度权": 0.9, "揣情": 0.75, "钓语": 0.65},
                "outcome": 0.92,
                "era": "秦汉"
            },
            "空城计": {
                "domain": StrategyDomain.CRISIS,
                "description": "诸葛亮用空城计退司马懿",
                "strategy": "阴计外泄者败",
                "factors": {"见微": 0.95, "知著": 0.85, "决断": 0.9},
                "outcome": 0.88,
                "era": "三国"
            }
        }
    
    def find_similar_cases(self, current_factors, domain, threshold=0.7):
        """寻找相似历史案例"""
        similar = []
        for name, case in self.cases.items():
            if case['domain'] != domain:
                continue
                
            similarity = 0
            count = 0
            for factor, value in case['factors'].items():
                if factor in current_factors:
                    similarity += 1 - abs(value - current_factors[factor])
                    count += 1
            
            if count > 0:
                similarity /= count
                if similarity >= threshold:
                    case['similarity'] = similarity
                    similar.append(case)
        
        return sorted(similar, key=lambda x: x['similarity'], reverse=True)

class SuShuAgent:
    """基于素书原则的智能体"""
    def __init__(self, role, traits):
        """
        role: 角色类型 (君主/谋士/将领/平民)
        traits: 特质字典 {
            '道': 0-1, '德': 0-1, '仁': 0-1, '义': 0-1, '礼': 0-1,
            '明察': 0-1, '度权': 0-1, '揣情': 0-1, '钓语': 0-1
        }
        """
        self.role = role
        self.traits = traits
        self.knowledge = HistoricalCase()
        self.memory = []  # 决策记忆
        self.resources = {'财富': 50, '影响力': 50, '军事': 50}
        
    def make_decision(self, situation, domain):
        """基于当前情境做出决策"""
        # 评估当前状态
        status = self.assess_situation(situation)
        
        # 寻找相似历史案例
        similar_cases = self.knowledge.find_similar_cases(status, domain)
        
        # 选择最佳策略
        if similar_cases:
            strategy = similar_cases[0]['strategy']
            confidence = min(1.0, similar_cases[0]['outcome'] * 0.9 + random.uniform(0.05, 0.15))
        else:
            strategy = "潜居抱道以待其时"  # 默认策略
            confidence = 0.6 + self.traits.get('道', 0.3) * 0.4
        
        # 记录决策
        decision_record = {
            'timestamp': datetime.now().isoformat(),
            'situation': situation,
            'domain': domain.value,
            'strategy': strategy,
            'confidence': confidence,
            'factors': status,
            'similar_cases': similar_cases
        }
        self.memory.append(decision_record)
        
        return strategy, confidence, similar_cases[:3]
    
    def assess_situation(self, situation):
        """评估当前情境关键因素"""
        factors = {}
        
        # 宇宙观因素
        cosmology_factors = ['道', '德', '仁', '义', '礼']
        for factor in cosmology_factors:
            if factor in self.traits:
                # 个人特质与环境加权
                factors[factor] = (self.traits[factor] * 0.7 + situation.get(factor, 0.5) * 0.3)
        
        # 决策能力因素
        if 'urgency' in situation:
            factors['见微'] = self.traits.get('明察', 0.5) * (1 - situation['urgency'])
            factors['知著'] = self.traits.get('度权', 0.5) * situation['complexity']
            factors['决断'] = self.traits.get('揣情', 0.5) * situation['urgency']
        
        return factors
    
    def update_traits(self, outcome):
        """根据决策结果更新特质"""
        if outcome > 0.7:  # 成功
            for trait in ['德', '度权', '决断']:
                if trait in self.traits:
                    self.traits[trait] = min(1.0, self.traits[trait] + 0.03)
        else:  # 失败
            for trait in ['道', '明察', '揣情']:
                if trait in self.traits:
                    self.traits[trait] = max(0.1, self.traits[trait] - 0.02)
    
    def get_traits_radar_data(self):
        """获取特质雷达图数据"""
        labels = []
        values = []
        for trait, value in self.traits.items():
            labels.append(trait)
            values.append(value)
        return labels, values
    
    def get_resource_data(self):
        """获取资源数据"""
        return list(self.resources.keys()), list(self.resources.values())

class StrategyEvaluator:
    """策略效果评估系统"""
    def __init__(self):
        self.metrics = {
            '短期效果': ['执行速度', '资源消耗', '直接效果'],
            '中期效果': ['稳定性', '适应性', '可持续性'],
            '长期影响': ['历史影响', '系统变革', '文化传承']
        }
    
    def evaluate_strategy(self, strategy, context):
        """评估策略综合效果"""
        evaluation = {}
        
        # 基础评估
        base_score = self._base_evaluation(strategy, context)
        evaluation['基础评分'] = base_score
        
        # 时间维度评估
        for timeframe, metrics in self.metrics.items():
            evaluation[timeframe] = {}
            for metric in metrics:
                score = base_score * random.uniform(0.8, 1.2)
                evaluation[timeframe][metric] = min(10, max(0, score))
        
        # 风险评估
        evaluation['风险分析'] = {
            '实施风险': max(0, (1 - context.get('control', 0.5)) * 8),
            '道德风险': 3 if '阴' in strategy else 7,
            '系统风险': min(10, abs(5 - context.get('stability', 5)) * 2)
        }
        
        return evaluation
    
    def _base_evaluation(self, strategy, context):
        """基础评分算法"""
        # 策略类型加成
        strategy_bonus = {
            '德': 0.9, '仁': 0.85, '义': 0.8, '礼': 0.75, '法': 0.7,
            '术': 0.65, '势': 0.7, '阴': 0.6
        }
        
        # 匹配最高加成
        bonus = 0.7  # 默认
        for key, value in strategy_bonus.items():
            if key in strategy:
                bonus = max(bonus, value)
        
        # 环境适配度
        env_factor = 1.0
        if 'urgency' in context and context['urgency'] > 0.7:
            if '决断' in strategy:
                env_factor *= 1.2
            else:
                env_factor *= 0.8
                
        if 'complexity' in context and context['complexity'] > 0.6:
            if '知著' in strategy:
                env_factor *= 1.1
        
        return min(10, max(0, bonus * 8 * env_factor))

class SuShuSimulator:
    """素书策略模拟环境"""
    def __init__(self, era="战国"):
        self.era = era
        self.agents = []
        self.environment = self._init_environment(era)
        self.strategy_db = {
            StrategyDomain.GOVERNANCE: ["德足以怀远", "赏罚分明", "轻徭薄赋", "礼法并施"],
            StrategyDomain.MILITARY: ["不战而屈人之兵", "以正合以奇胜", "知己知彼", "避实击虚"],
            StrategyDomain.PERSONNEL: ["任疑则危", "用人之智去其诈", "使功不如使过", "亲仁友直"],
            StrategyDomain.CRISIS: ["安莫安于忍辱", "避嫌远疑", "括囊顺会", "长莫长于博谋"],
            StrategyDomain.SELF: ["守愚藏拙", "博学切问", "恭俭谦约", "潜居抱道"]
        }
        self.history = []
        self.evaluator = StrategyEvaluator()
        self.current_round = 0
        
    def _init_environment(self, era):
        """初始化时代环境"""
        env_params = {
            "战国": {"稳定度": 0.3, "资源": 0.6, "威胁": 0.8},
            "汉初": {"稳定度": 0.5, "资源": 0.4, "威胁": 0.6},
            "盛唐": {"稳定度": 0.8, "资源": 0.9, "威胁": 0.3},
            "宋末": {"稳定度": 0.4, "资源": 0.7, "威胁": 0.9}
        }
        return env_params.get(era, env_params["战国"])
    
    def add_agent(self, agent):
        """添加智能体到模拟环境"""
        self.agents.append(agent)
    
    def run_round(self):
        """运行一轮模拟"""
        round_result = {"round": self.current_round+1, "decisions": []}
        
        # 更新环境动态
        self._update_environment()
        
        for agent in self.agents:
            # 随机选择策略领域
            domain = random.choice(list(StrategyDomain))
            
            # 创建情境
            situation = {
                "urgency": random.uniform(0.1, 0.9),
                "complexity": random.uniform(0.3, 0.8),
                "control": self.environment['稳定度'] * agent.traits.get('德', 0.5)
            }
            
            # 智能体决策
            strategy, confidence, similar_cases = agent.make_decision(situation, domain)
            
            # 评估策略
            evaluation = self.evaluator.evaluate_strategy(strategy, situation)
            
            # 记录结果
            decision_record = {
                "agent": agent.role,
                "domain": domain.value,
                "strategy": strategy,
                "confidence": confidence,
                "evaluation": evaluation,
                "similar_cases": similar_cases
            }
            round_result["decisions"].append(decision_record)
            
            # 更新智能体特质
            outcome = evaluation['基础评分'] / 10
            agent.update_traits(outcome)
            
            # 更新资源
            if outcome > 0.7:
                for res in agent.resources:
                    agent.resources[res] = min(100, agent.resources[res] + random.randint(5, 15))
            else:
                for res in agent.resources:
                    agent.resources[res] = max(0, agent.resources[res] - random.randint(3, 10))
        
        self.history.append(round_result)
        self.current_round += 1
        
        return round_result
    
    def _update_environment(self):
        """更新环境状态"""
        # 随机环境变化
        self.environment['稳定度'] = max(0.1, min(0.99, 
            self.environment['稳定度'] + random.uniform(-0.15, 0.1))
        )
        self.environment['资源'] = max(0.1, min(0.99, 
            self.environment['资源'] + random.uniform(-0.1, 0.05))
        )
    
    def get_strategy_network(self):
        """获取策略关联网络数据"""
        G = nx.Graph()
        
        # 添加节点（策略）
        strategies = set()
        for domain, strats in self.strategy_db.items():
            for strat in strats:
                G.add_node(strat, domain=domain.value)
                strategies.add(strat)
        
        # 添加边（关联）
        for record in self.history:
            for decision in record['decisions']:
                strategy = decision['strategy']
                if strategy in strategies:
                    # 连接相似案例
                    for case in decision.get('similar_cases', []):
                        case_name = case['description']
                        G.add_node(case_name, domain="历史案例")
                        G.add_edge(strategy, case_name, weight=decision['confidence'])
        
        return G
    
    def get_environment_data(self):
        """获取环境数据"""
        return list(self.environment.keys()), list(self.environment.values())


class RadarChart(FigureCanvas):
    """特质雷达图"""
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)
        super().__init__(fig)
        self.setParent(parent)
        self.ax = fig.add_subplot(111, polar=True)
        
    def plot_radar(self, labels, values):
        """绘制雷达图"""
        self.ax.clear()
        
        # 数据闭合
        values += values[:1]
        num_vars = len(labels)
        angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
        angles += angles[:1]
        
        # 绘制雷达图
        self.ax.plot(angles, values, linewidth=2, linestyle='solid')
        self.ax.fill(angles, values, 'b', alpha=0.1)
        
        # 设置标签
        self.ax.set_xticks(angles[:-1])
        self.ax.set_xticklabels(labels)
        self.ax.set_ylim(0, 1)
        
        # 添加标题
        self.ax.set_title('角色特质雷达图', size=14, color='blue', y=1.1)
        
        self.draw()

class BarChart(FigureCanvas):
    """柱状图"""
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)
        super().__init__(fig)
        self.setParent(parent)
        self.ax = fig.add_subplot(111)
        
    def plot_bar(self, labels, values, title="资源分布", color='skyblue'):
        """绘制柱状图"""
        self.ax.clear()
        x = np.arange(len(labels))
        self.ax.bar(x, values, color=color)
        self.ax.set_xticks(x)
        self.ax.set_xticklabels(labels, rotation=45)
        self.ax.set_title(title)
        self.ax.grid(True, linestyle='--', alpha=0.7)
        self.draw()

class NetworkGraph(FigureCanvas):
    """策略网络图"""
    def __init__(self, parent=None, width=8, height=6, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)
        super().__init__(fig)
        self.setParent(parent)
        self.ax = fig.add_subplot(111)
        
    def plot_network(self, G):
        """绘制网络图"""
        self.ax.clear()
        
        if len(G.nodes) == 0:
            self.ax.text(0.5, 0.5, "暂无数据", ha='center', va='center', fontsize=16)
            self.draw()
            return
        
        # 按领域着色
        color_map = {
            '治国': 'red',
            '用兵': 'blue',
            '用人': 'green',
            '危机': 'orange',
            '修身': 'purple',
            '历史案例': 'gray'
        }
        
        node_colors = []
        for node in G.nodes:
            domain = G.nodes[node].get('domain', '修身')
            node_colors.append(color_map.get(domain, 'gray'))
        
        # 绘制网络
        pos = nx.spring_layout(G, seed=42)
        nx.draw_networkx_nodes(G, pos, node_size=800, node_color=node_colors, alpha=0.8, ax=self.ax)
        nx.draw_networkx_edges(G, pos, width=1.5, alpha=0.5, ax=self.ax)
        nx.draw_networkx_labels(G, pos, font_size=10, font_family='SimHei', ax=self.ax)
        
        self.ax.set_title("《素书》策略关联网络", fontsize=16)
        self.ax.axis('off')
        self.draw()


class MainWindow(QMainWindow):
    """主界面"""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("《素书》战略决策系统")
        self.setGeometry(100, 100, 1200, 800)
        
        # 创建模拟器
        self.simulator = SuShuSimulator(era="战国")
        
        # 创建初始智能体
        self.ruler = SuShuAgent("君主", {
            '道': 0.8, '德': 0.7, '仁': 0.6, '义': 0.75, '礼': 0.65,
            '明察': 0.7, '度权': 0.85, '揣情': 0.75, '钓语': 0.6
        })
        
        self.strategist = SuShuAgent("谋士", {
            '道': 0.9, '德': 0.8, '仁': 0.7, '义': 0.85, '礼': 0.6,
            '明察': 0.95, '度权': 0.9, '揣情': 0.85, '钓语': 0.75
        })
        
        self.general = SuShuAgent("将领", {
            '道': 0.6, '德': 0.7, '仁': 0.5, '义': 0.9, '礼': 0.5,
            '明察': 0.8, '度权': 0.75, '揣情': 0.7, '钓语': 0.4
        })
        
        # 添加到模拟器
        self.simulator.add_agent(self.ruler)
        self.simulator.add_agent(self.strategist)
        self.simulator.add_agent(self.general)
        
        # 创建主界面控件
        self.create_widgets()
        
        # 初始化数据
        self.update_agent_info()
        self.update_environment_info()
        
    def create_widgets(self):
        """创建界面控件"""
        # 主布局
        main_widget = QWidget()
        main_layout = QHBoxLayout()
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)
        
        # 左侧控制面板
        control_panel = QWidget()
        control_layout = QVBoxLayout()
        control_panel.setLayout(control_layout)
        control_panel.setMaximumWidth(300)
        
        # 时代选择
        era_group = QGroupBox("时代选择")
        era_layout = QVBoxLayout()
        self.era_combo = QComboBox()
        self.era_combo.addItems(["战国", "汉初", "盛唐", "宋末"])
        self.era_combo.setCurrentText("战国")
        self.era_combo.currentTextChanged.connect(self.change_era)
        era_layout.addWidget(QLabel("选择历史时期:"))
        era_layout.addWidget(self.era_combo)
        era_group.setLayout(era_layout)
        
        # 模拟控制
        sim_group = QGroupBox("模拟控制")
        sim_layout = QVBoxLayout()
        self.run_round_btn = QPushButton("运行一轮模拟")
        self.run_round_btn.clicked.connect(self.run_simulation_round)
        self.run_auto_btn = QPushButton("自动模拟(5轮)")
        self.run_auto_btn.clicked.connect(self.run_auto_simulation)
        self.reset_btn = QPushButton("重置模拟")
        self.reset_btn.clicked.connect(self.reset_simulation)
        sim_layout.addWidget(self.run_round_btn)
        sim_layout.addWidget(self.run_auto_btn)
        sim_layout.addWidget(self.reset_btn)
        sim_group.setLayout(sim_layout)
        
        # 智能体信息
        agent_group = QGroupBox("智能体信息")
        agent_layout = QVBoxLayout()
        self.agent_combo = QComboBox()
        self.agent_combo.addItems(["君主", "谋士", "将领"])
        self.agent_combo.currentIndexChanged.connect(self.update_agent_info)
        agent_layout.addWidget(QLabel("选择角色:"))
        agent_layout.addWidget(self.agent_combo)
        
        # 特质显示
        self.traits_text = QTextEdit()
        self.traits_text.setReadOnly(True)
        agent_layout.addWidget(QLabel("特质:"))
        agent_layout.addWidget(self.traits_text)
        
        # 资源显示
        self.resources_text = QTextEdit()
        self.resources_text.setReadOnly(True)
        agent_layout.addWidget(QLabel("资源:"))
        agent_layout.addWidget(self.resources_text)
        agent_group.setLayout(agent_layout)
        
        # 环境信息
        env_group = QGroupBox("环境信息")
        env_layout = QVBoxLayout()
        self.env_text = QTextEdit()
        self.env_text.setReadOnly(True)
        env_layout.addWidget(self.env_text)
        env_group.setLayout(env_layout)
        
        # 添加到控制面板
        control_layout.addWidget(era_group)
        control_layout.addWidget(sim_group)
        control_layout.addWidget(agent_group)
        control_layout.addWidget(env_group)
        control_layout.addStretch()
        
        # 右侧主区域 - 使用选项卡
        self.tab_widget = QTabWidget()
        
        # 第一页：策略模拟
        sim_tab = QWidget()
        sim_tab_layout = QVBoxLayout()
        
        # 结果输出
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setFont(QFont("SimSun", 10))
        sim_tab_layout.addWidget(QLabel("模拟结果:"))
        sim_tab_layout.addWidget(self.result_text)
        
        # 策略网络图
        self.network_graph = NetworkGraph(self, width=8, height=6)
        sim_tab_layout.addWidget(QLabel("策略关联网络:"))
        sim_tab_layout.addWidget(self.network_graph)
        
        sim_tab.setLayout(sim_tab_layout)
        
        # 第二页：角色分析
        analysis_tab = QWidget()
        analysis_layout = QVBoxLayout()
        
        # 特质雷达图
        self.radar_chart = RadarChart(self, width=5, height=4)
        
        # 资源柱状图
        self.resource_chart = BarChart(self, width=5, height=4)
        
        # 图表布局
        chart_layout = QHBoxLayout()
        chart_layout.addWidget(self.radar_chart)
        chart_layout.addWidget(self.resource_chart)
        
        # 决策历史
        self.history_list = QListWidget()
        self.history_list.itemClicked.connect(self.show_history_detail)
        self.detail_text = QTextEdit()
        self.detail_text.setReadOnly(True)
        
        # 历史布局
        history_layout = QHBoxLayout()
        history_layout.addWidget(self.history_list)
        history_layout.addWidget(self.detail_text)
        
        analysis_layout.addLayout(chart_layout)
        analysis_layout.addWidget(QLabel("决策历史:"))
        analysis_layout.addLayout(history_layout)
        analysis_tab.setLayout(analysis_layout)
        
        # 第三页：案例库
        case_tab = QWidget()
        case_layout = QVBoxLayout()
        
        self.case_list = QListWidget()
        self.case_list.itemClicked.connect(self.show_case_detail)
        self.case_detail = QTextEdit()
        self.case_detail.setReadOnly(True)
        
        # 案例筛选
        filter_layout = QHBoxLayout()
        self.case_filter = QComboBox()
        self.case_filter.addItems(["全部", "治国", "用兵", "用人", "危机", "修身"])
        self.case_filter.currentIndexChanged.connect(self.update_case_list)
        filter_layout.addWidget(QLabel("筛选领域:"))
        filter_layout.addWidget(self.case_filter)
        
        case_layout.addLayout(filter_layout)
        case_layout.addWidget(QLabel("历史案例:"))
        
        case_splitter = QSplitter(Qt.Horizontal)
        case_splitter.addWidget(self.case_list)
        case_splitter.addWidget(self.case_detail)
        case_layout.addWidget(case_splitter)
        
        case_tab.setLayout(case_layout)
        
        # 添加选项卡
        self.tab_widget.addTab(sim_tab, "策略模拟")
        self.tab_widget.addTab(analysis_tab, "角色分析")
        self.tab_widget.addTab(case_tab, "历史案例库")
        
        # 添加到主布局
        main_layout.addWidget(control_panel)
        main_layout.addWidget(self.tab_widget)
        
        # 初始化案例列表
        self.update_case_list()
        
    def change_era(self, era):
        """改变时代"""
        self.simulator = SuShuSimulator(era=era)
        self.simulator.add_agent(self.ruler)
        self.simulator.add_agent(self.strategist)
        self.simulator.add_agent(self.general)
        self.update_environment_info()
        self.result_text.clear()
        self.result_text.append(f"已切换到 {era} 时代")
        
    def update_agent_info(self):
        """更新智能体信息"""
        index = self.agent_combo.currentIndex()
        agent = [self.ruler, self.strategist, self.general][index]
        
        # 显示特质
        traits_text = ""
        for trait, value in agent.traits.items():
            traits_text += f"{trait}: {value:.2f}\n"
        self.traits_text.setText(traits_text)
        
        # 显示资源
        resources_text = ""
        for resource, value in agent.resources.items():
            resources_text += f"{resource}: {value}\n"
        self.resources_text.setText(resources_text)
        
        # 更新图表
        labels, values = agent.get_traits_radar_data()
        self.radar_chart.plot_radar(labels, values)
        
        r_labels, r_values = agent.get_resource_data()
        self.resource_chart.plot_bar(r_labels, r_values, title="资源分布", color='lightgreen')
        
        # 更新历史列表
        self.history_list.clear()
        for i, record in enumerate(agent.memory):
            item = QListWidgetItem(f"决策 #{i+1}: {record['strategy']}")
            item.setData(Qt.UserRole, record)
            self.history_list.addItem(item)
    
    def update_environment_info(self):
        """更新环境信息"""
        env_text = ""
        for key, value in self.simulator.environment.items():
            env_text += f"{key}: {value:.2f}\n"
        self.env_text.setText(env_text)
        
        # 更新环境图表
        labels, values = self.simulator.get_environment_data()
        self.env_bar = BarChart(self, width=3, height=3)
        self.env_bar.plot_bar(labels, values, title="环境状态", color='lightblue')
        
    def run_simulation_round(self):
        """运行一轮模拟"""
        round_result = self.simulator.run_round()
        
        # 显示结果
        self.result_text.append(f"\n=== 第 {round_result['round']} 轮模拟结果 ===")
        self.result_text.append(f"环境状态: 稳定度={self.simulator.environment['稳定度']:.2f}, 资源={self.simulator.environment['资源']:.2f}")
        
        for decision in round_result['decisions']:
            self.result_text.append(f"\n[{decision['agent']}] 在 {decision['domain']} 领域")
            self.result_text.append(f"策略: {decision['strategy']} (置信度: {decision['confidence']:.2f})")
            self.result_text.append(f"基础评分: {decision['evaluation']['基础评分']:.1f}/10")
            
            # 相似案例
            if decision['similar_cases']:
                self.result_text.append(f"历史参考: {decision['similar_cases'][0]['description']}")
            
            # 风险分析
            risks = decision['evaluation']['风险分析']
            self.result_text.append(f"风险: 实施={risks['实施风险']:.1f}, 道德={risks['道德风险']:.1f}, 系统={risks['系统风险']:.1f}")
        
        # 更新网络图
        G = self.simulator.get_strategy_network()
        self.network_graph.plot_network(G)
        
        # 更新智能体和环境信息
        self.update_agent_info()
        self.update_environment_info()
        
    def run_auto_simulation(self):
        """自动运行5轮模拟"""
        self.result_text.append("\n开始自动模拟...")
        for i in range(5):
            QApplication.processEvents()  # 更新UI
            QTimer.singleShot(1000 * (i+1), self.run_simulation_round)
    
    def reset_simulation(self):
        """重置模拟"""
        # 重置智能体特质
        self.ruler.traits = {
            '道': 0.8, '德': 0.7, '仁': 0.6, '义': 0.75, '礼': 0.65,
            '明察': 0.7, '度权': 0.85, '揣情': 0.75, '钓语': 0.6
        }
        self.strategist.traits = {
            '道': 0.9, '德': 0.8, '仁': 0.7, '义': 0.85, '礼': 0.6,
            '明察': 0.95, '度权': 0.9, '揣情': 0.85, '钓语': 0.75
        }
        self.general.traits = {
            '道': 0.6, '德': 0.7, '仁': 0.5, '义': 0.9, '礼': 0.5,
            '明察': 0.8, '度权': 0.75, '揣情': 0.7, '钓语': 0.4
        }
        
        # 重置资源
        for agent in [self.ruler, self.strategist, self.general]:
            agent.resources = {'财富': 50, '影响力': 50, '军事': 50}
            agent.memory = []
        
        # 重置模拟器
        self.simulator = SuShuSimulator(era=self.era_combo.currentText())
        self.simulator.add_agent(self.ruler)
        self.simulator.add_agent(self.strategist)
        self.simulator.add_agent(self.general)
        
        # 更新UI
        self.result_text.clear()
        self.result_text.append("模拟已重置")
        self.update_agent_info()
        self.update_environment_info()
        self.network_graph.plot_network(nx.Graph())
    
    def show_history_detail(self, item):
        """显示历史决策详情"""
        record = item.data(Qt.UserRole)
        detail = f"时间: {record['timestamp']}\n"
        detail += f"领域: {record['domain']}\n"
        detail += f"策略: {record['strategy']}\n"
        detail += f"置信度: {record['confidence']:.2f}\n\n"
        
        detail += "情境分析:\n"
        for factor, value in record['factors'].items():
            detail += f"  {factor}: {value:.2f}\n"
        
        detail += "\n相似历史案例:\n"
        for case in record['similar_cases']:
            detail += f"  {case['description']} ({case['era']}, 相似度: {case['similarity']:.2f})\n"
        
        self.detail_text.setText(detail)
    
    def update_case_list(self):
        """更新案例列表"""
        self.case_list.clear()
        domain_filter = self.case_filter.currentText()
        
        for name, case in HistoricalCase().cases.items():
            if domain_filter == "全部" or domain_filter == case['domain'].value:
                item = QListWidgetItem(f"{case['description']} ({case['era']})")
                item.setData(Qt.UserRole, case)
                self.case_list.addItem(item)
    
    def show_case_detail(self, item):
        """显示案例详情"""
        case = item.data(Qt.UserRole)
        detail = f"案例名称: {item.text()}\n"
        detail += f"历史时期: {case['era']}\n"
        detail += f"策略领域: {case['domain'].value}\n"
        detail += f"核心策略: {case['strategy']}\n"
        detail += f"效果评分: {case['outcome']:.2f}\n\n"
        
        detail += "关键因素:\n"
        for factor, value in case['factors'].items():
            detail += f"  {factor}: {value:.2f}\n"
        
        self.case_detail.setText(detail)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    # 设置中文字体
    font = QFont("Microsoft YaHei", 10)
    app.setFont(font)
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())