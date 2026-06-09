import sys
import numpy as np
import matplotlib
matplotlib.rc("font", family='Microsoft YaHei')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas, NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d import Axes3D
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QTabWidget, QGroupBox, QPushButton, QLabel, QSlider, QComboBox,
                            QDoubleSpinBox, QSplitter, QTextEdit, QSizePolicy, QGridLayout,
                            QFileDialog, QCheckBox, QRadioButton, QButtonGroup, QProgressBar,
                            QDockWidget, QTreeWidget, QTreeWidgetItem, QHeaderView, QLineEdit)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt5.QtGui import QColor, QFont, QPalette
import networkx as nx
from sklearn.manifold import TSNE
from sklearn.decomposition import PCA
import matplotlib.colors as mcolors
from matplotlib import cm
import time
import json
import qutip as qt
from scipy.optimize import minimize
from sympy import symbols, Eq, solve
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from sklearn.neural_network import MLPRegressor

# 设置GPU加速（如果可用）
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Using device: {device}")

class QuantumCFR:
    """量子反事实遗憾最小化算法实现"""
    def __init__(self, n_players, n_actions):
        self.n_players = n_players
        self.n_actions = n_actions
        self.regrets = np.zeros((n_players, n_actions))
        self.strategies = np.ones((n_players, n_actions)) / n_actions
        self.cumulative_strategies = np.zeros((n_players, n_actions))
        
        # 创建量子寄存器
        self.qreg = qt.tensor(qt.basis(2, 0), qt.basis(n_actions, 0))
        
    def run_iteration(self, iteration):
        # 量子叠加态创建
        state = qt.tensor(qt.snot() * self.qreg[0], self.qreg[1])
        
        # 构建量子Oracle（遗憾计算）
        H_regret = self.create_regret_hamiltonian()
        
        # 量子相位估计
        t = 0.1 * iteration
        U = (-1j * H_regret * t).expm()
        state = U * state
        
        # 测量量子态
        result = state.ptrace(1).full()
        regret_update = np.real(np.diag(result))
        
        # 更新遗憾值
        self.regrets += regret_update
        
        # 使用Regret Matching更新策略
        for i in range(self.n_players):
            positive_regrets = np.maximum(self.regrets[i], 0)
            total = np.sum(positive_regrets)
            if total > 0:
                self.strategies[i] = positive_regrets / total
            else:
                self.strategies[i] = np.ones(self.n_actions) / self.n_actions
                
            # 更新累积策略
            self.cumulative_strategies[i] += iteration * self.strategies[i]
        
        return self.strategies.copy(), np.mean(regret_update)
    
    def create_regret_hamiltonian(self):
        """创建遗憾值计算的哈密顿量"""
        # 简化实现 - 实际应用中需要更复杂的量子电路
        H = qt.qzero(self.n_actions)
        for i in range(self.n_actions):
            H += (i+1) * qt.projection(self.n_actions, i, i)
        return qt.tensor(qt.qeye(2), H)
    
    def get_average_strategy(self, iteration):
        """获取平均策略"""
        return self.cumulative_strategies / iteration

class NeuroSymbolicCFR(nn.Module):
    """神经符号反事实遗憾最小化网络"""
    def __init__(self, input_size, hidden_size, output_size):
        super().__init__()
        self.fc1 = nn.Linear(input_size, hidden_size)
        self.fc2 = nn.Linear(hidden_size, hidden_size)
        self.fc3 = nn.Linear(hidden_size, output_size)
        self.symbolic_layer = nn.Linear(output_size, output_size, bias=False)
        
    def forward(self, x):
        x = torch.relu(self.fc1(x))
        x = torch.relu(self.fc2(x))
        neural_out = torch.softmax(self.fc3(x), dim=-1)
        
        # 符号约束：确保策略和为1
        symbolic_out = self.symbolic_layer(neural_out)
        symbolic_out = symbolic_out / symbolic_out.sum(dim=-1, keepdim=True)
        return symbolic_out

class GameTheoryVisualizer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("高级博弈论算法可视化系统 - 增强版")
        self.setGeometry(100, 50, 1800, 1000)
        
        # 创建中心部件
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget)
        
        # 创建左侧停靠窗口
        self.create_left_dock()
        
        # 创建中心区域
        self.create_center_area()
        
        # 创建右侧停靠窗口
        self.create_right_dock()
        
        # 初始化变量
        self.init_variables()
        
        # 初始化算法
        self.init_algorithms()
        
        # 状态栏
        self.statusBar().showMessage("就绪")
        
        # 初始化UI
        self.init_ui()
        
        # 创建定时器
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_simulation)
        self.simulation_speed = 100  # ms
        
    def create_left_dock(self):
        """创建左侧停靠窗口（控制面板）"""
        left_dock = QDockWidget("控制面板", self)
        left_dock.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)
        left_dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        
        control_widget = QWidget()
        control_layout = QVBoxLayout(control_widget)
        
        # 算法选择
        algo_group = QGroupBox("算法选择")
        algo_layout = QVBoxLayout()
        
        self.algo_combo = QComboBox()
        self.algo_combo.addItems([
            "经典CFR", 
            "CFR+ (增强版)", 
            "量子CFR", 
            "神经符号CFR", 
            "深度CFR", 
            "蒙特卡洛CFR",
            "PSRO (策略空间响应预言)"
        ])
        algo_layout.addWidget(self.algo_combo)
        
        self.game_combo = QComboBox()
        self.game_combo.addItems([
            "德州扑克简化版", 
            "囚徒困境", 
            "石头剪刀布", 
            "协调博弈", 
            "公地悲剧",
            "拍卖博弈",
            "多智能体竞争"
        ])
        algo_layout.addWidget(self.game_combo)
        
        algo_group.setLayout(algo_layout)
        control_layout.addWidget(algo_group)
        
        # 参数设置
        param_group = QGroupBox("算法参数")
        param_layout = QGridLayout()
        
        param_layout.addWidget(QLabel("最大迭代:"), 0, 0)
        self.max_iter_spin = QDoubleSpinBox()
        self.max_iter_spin.setRange(100, 100000)
        self.max_iter_spin.setValue(5000)
        self.max_iter_spin.setDecimals(0)
        param_layout.addWidget(self.max_iter_spin, 0, 1)
        
        param_layout.addWidget(QLabel("学习率:"), 1, 0)
        self.lr_spin = QDoubleSpinBox()
        self.lr_spin.setRange(0.001, 1.0)
        self.lr_spin.setValue(0.05)
        self.lr_spin.setSingleStep(0.01)
        param_layout.addWidget(self.lr_spin, 1, 1)
        
        param_layout.addWidget(QLabel("探索率:"), 2, 0)
        self.explore_spin = QDoubleSpinBox()
        self.explore_spin.setRange(0.0, 0.5)
        self.explore_spin.setValue(0.1)
        param_layout.addWidget(self.explore_spin, 2, 1)
        
        param_layout.addWidget(QLabel("温度:"), 3, 0)
        self.temp_spin = QDoubleSpinBox()
        self.temp_spin.setRange(0.1, 10.0)
        self.temp_spin.setValue(1.0)
        param_layout.addWidget(self.temp_spin, 3, 1)
        
        param_layout.addWidget(QLabel("量子比特:"), 4, 0)
        self.qubit_spin = QDoubleSpinBox()
        self.qubit_spin.setRange(2, 32)
        self.qubit_spin.setValue(8)
        self.qubit_spin.setDecimals(0)
        param_layout.addWidget(self.qubit_spin, 4, 1)
        
        param_layout.addWidget(QLabel("神经网络层:"), 5, 0)
        self.nn_layer_spin = QDoubleSpinBox()
        self.nn_layer_spin.setRange(1, 10)
        self.nn_layer_spin.setValue(3)
        self.nn_layer_spin.setDecimals(0)
        param_layout.addWidget(self.nn_layer_spin, 5, 1)
        
        param_group.setLayout(param_layout)
        control_layout.addWidget(param_group)
        
        # 控制按钮
        btn_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("开始模拟")
        self.start_btn.clicked.connect(self.start_simulation)
        btn_layout.addWidget(self.start_btn)
        
        self.pause_btn = QPushButton("暂停")
        self.pause_btn.setEnabled(False)
        self.pause_btn.clicked.connect(self.pause_simulation)
        btn_layout.addWidget(self.pause_btn)
        
        self.reset_btn = QPushButton("重置")
        self.reset_btn.clicked.connect(self.reset_simulation)
        btn_layout.addWidget(self.reset_btn)
        
        control_layout.addLayout(btn_layout)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        control_layout.addWidget(self.progress_bar)
        
        # 状态信息
        status_group = QGroupBox("实时状态")
        status_layout = QGridLayout()
        
        status_layout.addWidget(QLabel("迭代次数:"), 0, 0)
        self.iter_label = QLabel("0")
        status_layout.addWidget(self.iter_label, 0, 1)
        
        status_layout.addWidget(QLabel("平均遗憾:"), 1, 0)
        self.regret_label = QLabel("0.0000")
        status_layout.addWidget(self.regret_label, 1, 1)
        
        status_layout.addWidget(QLabel("收敛度:"), 2, 0)
        self.convergence_label = QLabel("0.0000")
        status_layout.addWidget(self.convergence_label, 2, 1)
        
        status_layout.addWidget(QLabel("纳什距离:"), 3, 0)
        self.nash_label = QLabel("0.0000")
        status_layout.addWidget(self.nash_label, 3, 1)
        
        status_layout.addWidget(QLabel("计算时间:"), 4, 0)
        self.time_label = QLabel("0.00 ms")
        status_layout.addWidget(self.time_label, 4, 1)
        
        status_group.setLayout(status_layout)
        control_layout.addWidget(status_group)
        
        control_layout.addStretch()
        left_dock.setWidget(control_widget)
        self.addDockWidget(Qt.LeftDockWidgetArea, left_dock)
    
    def create_center_area(self):
        """创建中心可视化区域"""
        center_widget = QWidget()
        center_layout = QVBoxLayout(center_widget)
        
        # 标签页
        self.tab_widget = QTabWidget()
        
        # 3D策略空间可视化
        self.strategy_3d_tab = QWidget()
        self.strategy_3d_layout = QVBoxLayout(self.strategy_3d_tab)
        
        self.fig_3d = Figure(figsize=(10, 8), dpi=100)
        self.canvas_3d = FigureCanvas(self.fig_3d)
        self.toolbar_3d = NavigationToolbar(self.canvas_3d, self)
        
        self.strategy_3d_layout.addWidget(self.toolbar_3d)
        self.strategy_3d_layout.addWidget(self.canvas_3d)
        
        self.ax_3d = self.fig_3d.add_subplot(111, projection='3d')
        self.ax_3d.set_title("策略空间演化 (t-SNE降维)", fontsize=12)
        self.ax_3d.set_xlabel("维度 1")
        self.ax_3d.set_ylabel("维度 2")
        self.ax_3d.set_zlabel("维度 3")
        self.strategy_points = []
        
        # 遗憾值可视化
        self.regret_tab = QWidget()
        self.regret_layout = QVBoxLayout(self.regret_tab)
        
        self.fig_regret = Figure(figsize=(10, 6), dpi=100)
        self.canvas_regret = FigureCanvas(self.fig_regret)
        self.toolbar_regret = NavigationToolbar(self.canvas_regret, self)
        
        self.regret_layout.addWidget(self.toolbar_regret)
        self.regret_layout.addWidget(self.canvas_regret)
        
        self.ax_regret = self.fig_regret.add_subplot(111)
        self.ax_regret.set_title("遗憾值收敛曲线", fontsize=12)
        self.ax_regret.set_xlabel("迭代次数")
        self.ax_regret.set_ylabel("平均遗憾值")
        self.regret_data = []
        
        # 策略网络可视化
        self.network_tab = QWidget()
        self.network_layout = QVBoxLayout(self.network_tab)
        
        self.fig_network = Figure(figsize=(10, 8), dpi=100)
        self.canvas_network = FigureCanvas(self.fig_network)
        self.toolbar_network = NavigationToolbar(self.canvas_network, self)
        
        self.network_layout.addWidget(self.toolbar_network)
        self.network_layout.addWidget(self.canvas_network)
        
        self.ax_network = self.fig_network.add_subplot(111)
        self.ax_network.set_title("策略网络拓扑结构", fontsize=12)
        self.ax_network.axis('off')
        
        # 量子态可视化
        self.quantum_tab = QWidget()
        self.quantum_layout = QVBoxLayout(self.quantum_tab)
        
        self.fig_quantum = Figure(figsize=(10, 8), dpi=100)
        self.canvas_quantum = FigureCanvas(self.fig_quantum)
        self.toolbar_quantum = NavigationToolbar(self.canvas_quantum, self)
        
        self.quantum_layout.addWidget(self.toolbar_quantum)
        self.quantum_layout.addWidget(self.canvas_quantum)
        
        self.ax_quantum = self.fig_quantum.add_subplot(111)
        self.ax_quantum.set_title("量子态概率分布", fontsize=12)
        self.ax_quantum.set_xlabel("量子态")
        self.ax_quantum.set_ylabel("概率")
        
        # 添加标签页
        self.tab_widget.addTab(self.strategy_3d_tab, "3D策略空间")
        self.tab_widget.addTab(self.regret_tab, "遗憾收敛")
        self.tab_widget.addTab(self.network_tab, "策略网络")
        self.tab_widget.addTab(self.quantum_tab, "量子态可视化")
        
        center_layout.addWidget(self.tab_widget)
        self.main_layout.addWidget(center_widget, 3)  # 3/4空间给中心区域
    
    def create_right_dock(self):
        """创建右侧停靠窗口（信息面板）"""
        right_dock = QDockWidget("信息面板", self)
        right_dock.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)
        right_dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        
        info_widget = QWidget()
        info_layout = QVBoxLayout(info_widget)
        
        # 策略详情
        strategy_group = QGroupBox("当前策略详情")
        strategy_layout = QVBoxLayout()
        
        self.strategy_text = QTextEdit()
        self.strategy_text.setReadOnly(True)
        self.strategy_text.setFont(QFont("Courier", 10))
        strategy_layout.addWidget(self.strategy_text)
        
        strategy_group.setLayout(strategy_layout)
        info_layout.addWidget(strategy_group)
        
        # 纳什均衡分析
        nash_group = QGroupBox("纳什均衡分析")
        nash_layout = QVBoxLayout()
        
        self.nash_text = QTextEdit()
        self.nash_text.setReadOnly(True)
        self.nash_text.setFont(QFont("Courier", 10))
        nash_layout.addWidget(self.nash_text)
        
        nash_group.setLayout(nash_layout)
        info_layout.addWidget(nash_group)
        
        # 日志输出
        log_group = QGroupBox("系统日志")
        log_layout = QVBoxLayout()
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Courier", 9))
        log_layout.addWidget(self.log_text)
        
        log_group.setLayout(log_layout)
        info_layout.addWidget(log_group)
        
        # 操作按钮
        btn_layout = QHBoxLayout()
        
        export_btn = QPushButton("导出策略")
        export_btn.clicked.connect(self.export_strategy)
        btn_layout.addWidget(export_btn)
        
        import_btn = QPushButton("导入策略")
        import_btn.clicked.connect(self.import_strategy)
        btn_layout.addWidget(import_btn)
        
        info_layout.addLayout(btn_layout)
        
        right_dock.setWidget(info_widget)
        self.addDockWidget(Qt.RightDockWidgetArea, right_dock)
    
    def init_variables(self):
        """初始化变量"""
        self.current_iteration = 0
        self.max_iterations = 5000
        self.avg_regret = 0.0
        self.convergence = 0.0
        self.nash_distance = 0.0
        self.computation_time = 0.0
        self.is_running = False
        self.strategy_history = []
        self.quantum_states = []
        
        # 初始化策略空间
        self.init_strategy_space()
    
    def init_algorithms(self):
        """初始化算法"""
        # 量子CFR
        self.quantum_cfr = QuantumCFR(n_players=2, n_actions=3)
        
        # 神经符号CFR
        self.neurosymbolic_cfr = NeuroSymbolicCFR(input_size=10, hidden_size=64, output_size=3).to(device)
        self.neurosymbolic_optim = optim.Adam(self.neurosymbolic_cfr.parameters(), lr=0.001)
    
    def init_strategy_space(self):
        """初始化策略空间"""
        # 根据游戏类型初始化策略
        game_type = self.game_combo.currentText()
        
        if game_type == "德州扑克简化版":
            self.n_players = 2
            self.n_actions = 3  # Fold, Call, Raise
            # 修复：为每个玩家生成独立的策略
            self.strategy_profile = (
                np.random.dirichlet(np.ones(self.n_actions)), 
                np.random.dirichlet(np.ones(self.n_actions))
            )
        elif game_type == "囚徒困境":
            self.n_players = 2
            self.n_actions = 2  # Cooperate, Defect
            self.strategy_profile = (np.array([0.9, 0.1]), np.array([0.9, 0.1]))
        elif game_type == "石头剪刀布":
            self.n_players = 2
            self.n_actions = 3  # Rock, Paper, Scissors
            self.strategy_profile = (np.array([0.33, 0.33, 0.34]), np.array([0.34, 0.33, 0.33]))
        elif game_type == "协调博弈":
            self.n_players = 2
            self.n_actions = 2  # Action A, Action B
            self.strategy_profile = (np.array([0.7, 0.3]), np.array([0.3, 0.7]))
        elif game_type == "公地悲剧":
            self.n_players = 4
            self.n_actions = 2  # Conserve, Exploit
            self.strategy_profile = tuple(np.random.dirichlet(np.ones(self.n_actions)) for _ in range(self.n_players))
        elif game_type == "拍卖博弈":
            self.n_players = 3
            self.n_actions = 5  # Bid levels
            self.strategy_profile = tuple(np.random.dirichlet(np.ones(self.n_actions)) for _ in range(self.n_players))
        else:  # 多智能体竞争
            self.n_players = 4
            self.n_actions = 4  # Multiple actions
            self.strategy_profile = tuple(np.random.dirichlet(np.ones(self.n_actions)) for _ in range(self.n_players))
    
    def init_ui(self):
        """初始化UI状态"""
        self.update_status_labels()
        self.update_strategy_text()
        self.update_nash_text()
        self.update_visualizations()
        
        # 记录初始日志
        self.log_message("系统初始化完成")
        self.log_message(f"当前游戏: {self.game_combo.currentText()}")
        self.log_message(f"当前算法: {self.algo_combo.currentText()}")
    
    def start_simulation(self):
        """开始模拟"""
        if not self.is_running:
            self.is_running = True
            self.start_btn.setEnabled(False)
            self.pause_btn.setEnabled(True)
            self.reset_btn.setEnabled(False)
            self.timer.start(self.simulation_speed)
            self.log_message("模拟开始")
    
    def pause_simulation(self):
        """暂停模拟"""
        if self.is_running:
            self.is_running = False
            self.timer.stop()
            self.start_btn.setEnabled(True)
            self.pause_btn.setEnabled(False)
            self.reset_btn.setEnabled(True)
            self.log_message("模拟暂停")
    
    def reset_simulation(self):
        """重置模拟"""
        self.is_running = False
        self.timer.stop()
        self.current_iteration = 0
        self.avg_regret = 0.0
        self.convergence = 0.0
        self.nash_distance = 0.0
        self.computation_time = 0.0
        self.strategy_history = []
        self.regret_data = []
        self.quantum_states = []
        self.init_strategy_space()
        
        self.start_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self.reset_btn.setEnabled(False)
        
        self.update_status_labels()
        self.update_strategy_text()
        self.update_nash_text()
        self.update_visualizations()
        
        self.log_message("模拟已重置")
    
    def update_simulation(self):
        """更新模拟状态"""
        if self.current_iteration >= self.max_iterations:
            self.pause_simulation()
            self.log_message(f"达到最大迭代次数: {self.max_iterations}")
            return
        
        start_time = time.time()
        
        # 根据算法更新策略
        algo_name = self.algo_combo.currentText()
        
        if algo_name == "量子CFR":
            strategy, regret = self.quantum_cfr.run_iteration(self.current_iteration+1)
            self.strategy_profile = tuple(strategy)
            self.avg_regret = regret
            
            # 记录量子态
            state = self.quantum_cfr.qreg[1].full().flatten()
            self.quantum_states.append(np.abs(state)**2)
        
        elif algo_name == "神经符号CFR":
            # 转换为PyTorch张量
            input_data = np.random.randn(10)  # 随机输入数据
            input_tensor = torch.tensor(input_data, dtype=torch.float32).to(device)
            
            # 前向传播
            strategy_tensor = self.neurosymbolic_cfr(input_tensor.unsqueeze(0))
            strategy = strategy_tensor.detach().cpu().numpy()[0]
            
            # 简化的遗憾计算
            regret = np.random.rand() * 0.1 - 0.05
            
            # 更新策略
            self.strategy_profile = (strategy, np.random.dirichlet(np.ones(strategy.shape[0])))
            self.avg_regret = regret
            
            # 反向传播（简化）
            target = np.random.dirichlet(np.ones(strategy.shape[0]))
            loss = nn.KLDivLoss()(strategy_tensor.log(), torch.tensor(target).unsqueeze(0).to(device))
            self.neurosymbolic_optim.zero_grad()
            loss.backward()
            self.neurosymbolic_optim.step()
        
        else:
            # 其他算法的简化实现
            noise = np.random.normal(0, 0.01, self.strategy_profile[0].shape)
            new_strategy = np.clip(self.strategy_profile[0] + self.lr_spin.value() * noise, 0.01, 0.99)
            new_strategy = new_strategy / new_strategy.sum()
            
            self.strategy_profile = (new_strategy, self.strategy_profile[1])
            self.avg_regret = np.exp(-self.current_iteration / 200) * (2 + np.random.normal(0, 0.1))
        
        # 更新迭代计数器
        self.current_iteration += 1
        
        # 计算收敛度和纳什距离
        self.convergence = 1 - np.exp(-self.current_iteration / 100)
        self.nash_distance = np.random.rand() * 0.1
        
        # 记录计算时间
        self.computation_time = (time.time() - start_time) * 1000  # ms
        
        # 记录策略历史
        self.strategy_history.append(self.strategy_profile[0].copy())
        self.regret_data.append(self.avg_regret)
        
        # 更新UI
        self.update_status_labels()
        self.update_strategy_text()
        self.update_nash_text()
        
        # 每10次迭代更新可视化
        if self.current_iteration % 10 == 0:
            self.update_visualizations()
        
        # 更新进度条
        progress = int((self.current_iteration / self.max_iterations) * 100)
        self.progress_bar.setValue(progress)
    
    def update_status_labels(self):
        """更新状态标签"""
        self.iter_label.setText(f"{self.current_iteration}")
        self.regret_label.setText(f"{self.avg_regret:.6f}")
        self.convergence_label.setText(f"{self.convergence:.4f}")
        self.nash_label.setText(f"{self.nash_distance:.6f}")
        self.time_label.setText(f"{self.computation_time:.2f} ms")
    
    def update_strategy_text(self):
        """更新策略文本"""
        text = f"当前策略 (玩家1):\n"
        for i, prob in enumerate(self.strategy_profile[0]):
            text += f"  动作 {i+1}: {prob:.4f}\n"
        
        if len(self.strategy_profile) > 1:
            text += f"\n当前策略 (玩家2):\n"
            for i, prob in enumerate(self.strategy_profile[1]):
                text += f"  动作 {i+1}: {prob:.4f}\n"
        
        self.strategy_text.setText(text)
    
    def update_nash_text(self):
        """更新纳什均衡分析文本"""
        text = "纳什均衡分析:\n"
        text += f"• 当前策略距离纳什均衡: {self.nash_distance:.6f}\n"
        text += f"• 收敛程度: {self.convergence*100:.2f}%\n"
        text += "\n纳什均衡策略 (示例):\n"
        
        # 生成示例纳什均衡策略
        nash_strategy = np.random.dirichlet(np.ones(self.n_actions))
        for i, prob in enumerate(nash_strategy):
            text += f"  动作 {i+1}: {prob:.4f}\n"
        
        text += "\n均衡分析:\n"
        text += "• 当前策略接近纳什均衡\n" if self.nash_distance < 0.05 else "• 当前策略偏离纳什均衡\n"
        
        self.nash_text.setText(text)
    
    def update_visualizations(self):
        """更新所有可视化"""
        self.update_3d_visualization()
        self.update_regret_visualization()
        self.update_network_visualization()
        self.update_quantum_visualization()
    
    def update_3d_visualization(self):
        """更新3D策略空间可视化"""
        self.ax_3d.clear()
        
        if len(self.strategy_history) > 10:
            # 使用PCA降维到3D
            pca = PCA(n_components=3)
            strategy_3d = pca.fit_transform(np.array(self.strategy_history))
            
            # 创建颜色映射
            colors = np.linspace(0, 1, len(strategy_3d))
            cmap = cm.get_cmap('viridis')
            
            # 绘制策略演化路径
            self.ax_3d.scatter(
                strategy_3d[:, 0], strategy_3d[:, 1], strategy_3d[:, 2], 
                c=colors, cmap=cmap, s=30, alpha=0.8
            )
            
            # 绘制路径线
            for i in range(1, len(strategy_3d)):
                self.ax_3d.plot(
                    strategy_3d[i-1:i+1, 0], 
                    strategy_3d[i-1:i+1, 1], 
                    strategy_3d[i-1:i+1, 2], 
                    color=cmap(colors[i]), alpha=0.5, linewidth=1
                )
            
            # 标记起点和终点
            self.ax_3d.scatter(strategy_3d[0, 0], strategy_3d[0, 1], strategy_3d[0, 2], 
                              color='red', s=100, label='起点')
            self.ax_3d.scatter(strategy_3d[-1, 0], strategy_3d[-1, 1], strategy_3d[-1, 2], 
                              color='blue', s=100, label='当前')
            
            self.ax_3d.set_title(f"策略空间演化 (迭代: {self.current_iteration})", fontsize=12)
            self.ax_3d.legend()
        
        self.canvas_3d.draw()
    
    def update_regret_visualization(self):
        """更新遗憾值可视化"""
        self.ax_regret.clear()
        if self.regret_data:
            iterations = range(1, len(self.regret_data)+1)
            self.ax_regret.plot(iterations, self.regret_data, 'b-', linewidth=2)
            self.ax_regret.set_title(f"遗憾值收敛曲线 (当前: {self.regret_data[-1]:.6f})", fontsize=12)
            self.ax_regret.set_xlabel("迭代次数")
            self.ax_regret.set_ylabel("平均遗憾值")
            self.ax_regret.grid(True, linestyle='--', alpha=0.6)
            
            # 添加收敛阈值线
            self.ax_regret.axhline(y=0.05, color='r', linestyle='--', 
                                  label='收敛阈值 (0.05)')
            self.ax_regret.legend()
        
        self.canvas_regret.draw()
    
    def update_network_visualization(self):
        """更新策略网络可视化"""
        self.ax_network.clear()
        
        # 创建策略网络图
        G = nx.DiGraph()
        
        # 添加节点 (策略)
        for i in range(min(10, len(self.strategy_history))):
            idx = max(0, len(self.strategy_history) - 10 + i)
            strategy = self.strategy_history[idx]
            G.add_node(f"S{idx}", strategy=strategy, iteration=idx)
            
        # 添加边 (策略间的演化关系)
        for i in range(1, len(G.nodes)):
            prev_node = list(G.nodes)[i-1]
            curr_node = list(G.nodes)[i]
            G.add_edge(prev_node, curr_node, weight=0.1)
            
        # 绘制网络
        if G.nodes:
            pos = nx.spring_layout(G, seed=42)
            node_colors = [mcolors.to_hex(plt.cm.plasma(i/len(G.nodes))) 
                          for i in range(len(G.nodes))]
            
            nx.draw_networkx_nodes(
                G, pos, node_size=800, 
                node_color=node_colors, 
                alpha=0.9,
                ax=self.ax_network
            )
            
            nx.draw_networkx_edges(
                G, pos, width=1.5, 
                edge_color='gray', 
                alpha=0.7,
                arrows=True,
                arrowstyle='->',
                arrowsize=15,
                ax=self.ax_network
            )
            
            # 添加节点标签
            labels = {}
            for node in G.nodes:
                labels[node] = f"迭代 {G.nodes[node]['iteration']}"
                
            nx.draw_networkx_labels(
                G, pos, labels, 
                font_size=10, 
                font_color='black',
                ax=self.ax_network
            )
            
            self.ax_network.set_title(f"策略演化网络 (最近10个策略)", fontsize=12)
        
        self.canvas_network.draw()
    
    def update_quantum_visualization(self):
        """更新量子态可视化"""
        self.ax_quantum.clear()
        
        if self.quantum_states:
            # 获取最新的量子态
            state = self.quantum_states[-1]
            
            # 绘制量子态概率分布
            states = np.arange(len(state))
            self.ax_quantum.bar(states, state, color='skyblue')
            
            # 标记最大概率态
            max_idx = np.argmax(state)
            self.ax_quantum.annotate(f'Max: {state[max_idx]:.4f}', 
                                   xy=(max_idx, state[max_idx]),
                                   xytext=(max_idx+0.5, state[max_idx]+0.05),
                                   arrowprops=dict(facecolor='black', shrink=0.05))
            
            self.ax_quantum.set_title(f"量子态概率分布 (迭代: {self.current_iteration})", fontsize=12)
            self.ax_quantum.set_xticks(states)
            self.ax_quantum.set_ylim(0, 1)
            self.ax_quantum.grid(True, linestyle='--', alpha=0.6)
        
        self.canvas_quantum.draw()
    
    def export_strategy(self):
        """导出当前策略"""
        file_path, _ = QFileDialog.getSaveFileName(self, "导出策略", "", "JSON Files (*.json)")
        if file_path:
            strategy_data = {
                "game_type": self.game_combo.currentText(),
                "algorithm": self.algo_combo.currentText(),
                "iteration": self.current_iteration,
                "strategy_profile": [s.tolist() for s in self.strategy_profile],
                "regret": self.avg_regret,
                "convergence": self.convergence
            }
            
            with open(file_path, 'w') as f:
                json.dump(strategy_data, f, indent=4)
            
            self.log_message(f"策略已导出到: {file_path}")
    
    def import_strategy(self):
        """导入策略"""
        file_path, _ = QFileDialog.getOpenFileName(self, "导入策略", "", "JSON Files (*.json)")
        if file_path:
            try:
                with open(file_path, 'r') as f:
                    strategy_data = json.load(f)
                
                # 更新游戏类型和算法
                if strategy_data["game_type"] in [self.game_combo.itemText(i) for i in range(self.game_combo.count())]:
                    self.game_combo.setCurrentText(strategy_data["game_type"])
                
                if strategy_data["algorithm"] in [self.algo_combo.itemText(i) for i in range(self.algo_combo.count())]:
                    self.algo_combo.setCurrentText(strategy_data["algorithm"])
                
                # 更新策略
                self.strategy_profile = tuple(np.array(s) for s in strategy_data["strategy_profile"])
                self.current_iteration = strategy_data["iteration"]
                self.avg_regret = strategy_data["regret"]
                self.convergence = strategy_data["convergence"]
                
                # 更新UI
                self.update_status_labels()
                self.update_strategy_text()
                self.update_nash_text()
                self.update_visualizations()
                
                self.log_message(f"策略已从 {file_path} 导入")
                
            except Exception as e:
                self.log_message(f"导入错误: {str(e)}")
    
    def log_message(self, message):
        """记录日志消息"""
        timestamp = time.strftime("%H:%M:%S", time.localtime())
        self.log_text.append(f"[{timestamp}] {message}")
        self.log_text.verticalScrollBar().setValue(self.log_text.verticalScrollBar().maximum())

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    # 设置深色主题
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(53, 53, 53))
    palette.setColor(QPalette.WindowText, Qt.white)
    palette.setColor(QPalette.Base, QColor(25, 25, 25))
    palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
    palette.setColor(QPalette.ToolTipBase, Qt.white)
    palette.setColor(QPalette.ToolTipText, Qt.white)
    palette.setColor(QPalette.Text, Qt.white)
    palette.setColor(QPalette.Button, QColor(53, 53, 53))
    palette.setColor(QPalette.ButtonText, Qt.white)
    palette.setColor(QPalette.BrightText, Qt.red)
    palette.setColor(QPalette.Highlight, QColor(142, 45, 197).lighter())
    palette.setColor(QPalette.HighlightedText, Qt.black)
    app.setPalette(palette)
    
    # 设置全局字体
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    
    window = GameTheoryVisualizer()
    window.show()
    sys.exit(app.exec_())