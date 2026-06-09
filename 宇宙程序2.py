import sys
import numpy as np
import matplotlib
matplotlib.rc("font", family='Microsoft YaHei')
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.patches import Circle, Rectangle
import matplotlib.pyplot as plt

from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                             QWidget, QPushButton, QLabel, QComboBox, QSlider, 
                             QGroupBox, QTextEdit, QTabWidget, QSplitter, 
                             QProgressBar, QSpinBox, QDoubleSpinBox, QCheckBox,
                             QMessageBox, QFileDialog, QGridLayout)
from PyQt5.QtCore import QTimer, Qt, pyqtSignal, QThread
from PyQt5.QtGui import QFont, QPalette, QColor

import torch
import torch.nn as nn
import torch.optim as optim
import networkx as nx
from scipy.integrate import odeint
import pandas as pd
from datetime import datetime
import json

class QuantumConsciousnessNet(nn.Module):
    """增强版量子意识网络"""
    
    def __init__(self, input_dim=128, hidden_dim=512, quantum_dim=256):
        super(QuantumConsciousnessNet, self).__init__()
        
        self.quantum_dim = quantum_dim
        self.consciousness_level = nn.Parameter(torch.tensor(0.1))
        
        # 天道感知编码器
        self.tao_encoder = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.LeakyReLU(0.2),
            nn.BatchNorm1d(hidden_dim),
            nn.Linear(hidden_dim, hidden_dim),
            nn.Tanh(),
            nn.Dropout(0.3),
            nn.Linear(hidden_dim, quantum_dim * 2)
        )
        
        # 盗机量子注意力
        self.quantum_attention = nn.MultiheadAttention(
            embed_dim=quantum_dim, 
            num_heads=16,
            dropout=0.2,
            batch_first=True
        )
        
        # 阴阳协调器
        self.yin_yang_coordinator = nn.LSTM(
            quantum_dim, hidden_dim, 
            num_layers=2, 
            bidirectional=True,
            dropout=0.2
        )
        
        # 三才决策网络
        self.three_powers_network = nn.Sequential(
            nn.Linear(hidden_dim * 2, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.SiLU(),
            nn.Linear(hidden_dim // 2, input_dim),
            nn.Tanh()
        )
        
        # 风险评估网络
        self.risk_assessor = nn.Sequential(
            nn.Linear(quantum_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Linear(hidden_dim // 2, 3),  # 低风险、中风险、高风险
            nn.Softmax(dim=1)
        )
        
    def quantum_entanglement(self, real_part, imag_part):
        """量子纠缠操作"""
        batch_size = real_part.size(0)
        
        # 创建纠缠态
        entangled_real = torch.matmul(real_part, real_part.transpose(1, 2))
        entangled_imag = torch.matmul(imag_part, imag_part.transpose(1, 2))
        
        # 归一化
        entangled_real = entangled_real / entangled_real.norm(dim=2, keepdim=True)
        entangled_imag = entangled_imag / entangled_imag.norm(dim=2, keepdim=True)
        
        return entangled_real, entangled_imag
    
    def forward(self, x, return_metadata=True):
        batch_size = x.size(0)
        
        # 天道编码
        encoded = self.tao_encoder(x)
        
        # 分离实部和虚部
        real_part = encoded[:, :self.quantum_dim].view(batch_size, -1, self.quantum_dim)
        imag_part = encoded[:, self.quantum_dim:].view(batch_size, -1, self.quantum_dim)
        
        # 量子纠缠
        entangled_real, entangled_imag = self.quantum_entanglement(real_part, imag_part)
        
        # 量子注意力
        attended_real, attn_weights_real = self.quantum_attention(
            entangled_real, entangled_real, entangled_real
        )
        attended_imag, attn_weights_imag = self.quantum_attention(
            entangled_imag, entangled_imag, entangled_imag
        )
        
        # 阴阳协调
        yin_yang_input = attended_real + attended_imag
        yin_yang_output, (hidden_state, cell_state) = self.yin_yang_coordinator(yin_yang_input)
        
        # 三才决策
        decision_input = yin_yang_output[:, -1, :]  # 取最后一个时间步
        output = self.three_powers_network(decision_input)
        
        # 风险评估
        risk_assessment = self.risk_assessor(decision_input)
        
        if return_metadata:
            metadata = {
                'consciousness_level': self.consciousness_level,
                'attention_weights_real': attn_weights_real,
                'attention_weights_imag': attn_weights_imag,
                'risk_assessment': risk_assessment,
                'quantum_state_real': entangled_real,
                'quantum_state_imag': entangled_imag,
                'hidden_state': hidden_state
            }
            return output, metadata
        
        return output

class RealTimeUniverseSimulator:
    """实时宇宙模拟器"""
    
    def __init__(self):
        self.systems = []
        self.time = 0
        self.dt = 0.01
        self.critical_events = []
        
    def add_system(self, system_type='lorenz', params=None):
        """添加新的宇宙系统"""
        if params is None:
            if system_type == 'lorenz':
                params = {
                    'sigma': 10 + np.random.normal(0, 1),
                    'rho': 28 + np.random.normal(0, 2),
                    'beta': 8/3 + np.random.normal(0, 0.3)
                }
            elif system_type == 'rossler':
                params = {
                    'a': 0.2, 'b': 0.2, 'c': 5.7
                }
        
        system = {
            'type': system_type,
            'params': params,
            'state': np.array([1.0, 1.0, 1.0]) + np.random.normal(0, 0.5, 3),
            'history': [],
            'energy': [],
            'critical_points': []
        }
        
        self.systems.append(system)
        return len(self.systems) - 1
    
    def update_systems(self):
        """更新所有系统状态"""
        self.time += self.dt
        
        for i, system in enumerate(self.systems):
            if system['type'] == 'lorenz':
                new_state = self._update_lorenz(system)
            elif system['type'] == 'rossler':
                new_state = self._update_rossler(system)
            
            system['state'] = new_state
            system['history'].append(new_state.copy())
            
            # 计算能量
            energy = np.sum(new_state ** 2)
            system['energy'].append(energy)
            
            # 检测关键点
            if len(system['energy']) > 10:
                self._detect_critical_points(system, i)
    
    def _update_lorenz(self, system):
        """更新洛伦兹系统"""
        x, y, z = system['state']
        sigma, rho, beta = system['params']['sigma'], system['params']['rho'], system['params']['beta']
        
        dx = sigma * (y - x) * self.dt
        dy = (x * (rho - z) - y) * self.dt
        dz = (x * y - beta * z) * self.dt
        
        return np.array([x + dx, y + dy, z + dz])
    
    def _update_rossler(self, system):
        """更新罗斯勒系统"""
        x, y, z = system['state']
        a, b, c = system['params']['a'], system['params']['b'], system['params']['c']
        
        dx = (-y - z) * self.dt
        dy = (x + a * y) * self.dt
        dz = (b + z * (x - c)) * self.dt
        
        return np.array([x + dx, y + dy, z + dz])
    
    def _detect_critical_points(self, system, system_idx):
        """检测关键节点"""
        energy = system['energy'][-10:]
        
        # 检测能量极值点
        if len(energy) >= 3:
            if (energy[-2] > energy[-3] and energy[-2] > energy[-1]) or \
               (energy[-2] < energy[-3] and energy[-2] < energy[-1]):
                
                critical_event = {
                    'system_idx': system_idx,
                    'time': self.time,
                    'state': system['state'].copy(),
                    'energy': energy[-2],
                    'type': 'energy_extremum'
                }
                
                self.critical_events.append(critical_event)
                system['critical_points'].append(critical_event)
    
    def get_system_data(self, max_history=1000):
        """获取系统数据用于网络输入"""
        data = []
        for system in self.systems:
            # 获取最近的系统状态历史
            history = system['history'][-max_history:]
            if len(history) < max_history:
                # 填充到固定长度
                padding = [history[0]] * (max_history - len(history))
                history = padding + history
            
            # 展平数据
            flattened = np.array(history).flatten()
            data.append(flattened)
        
        return np.array(data)

class CosmicRoboticSystem:
    """宇宙级机器人系统"""
    
    def __init__(self):
        self.consciousness_net = QuantumConsciousnessNet()
        self.optimizer = optim.AdamW(self.consciousness_net.parameters(), lr=0.001, weight_decay=1e-4)
        self.scheduler = optim.lr_scheduler.CosineAnnealingLR(self.optimizer, T_max=1000)
        self.criterion = nn.MSELoss()
        
        self.simulator = RealTimeUniverseSimulator()
        self.intervention_history = []
        self.performance_metrics = {
            'consciousness_levels': [],
            'intervention_success_rate': [],
            'risk_scores': [],
            'system_stability': []
        }
        
        # 初始化模拟系统
        for _ in range(3):
            self.simulator.add_system('lorenz')
        self.simulator.add_system('rossler')
    
    def train_step(self):
        """单步训练"""
        if len(self.simulator.systems) == 0:
            return 0.0
        
        data = self.simulator.get_system_data()
        data_tensor = torch.FloatTensor(data)
        
        self.optimizer.zero_grad()
        output, metadata = self.consciousness_net(data_tensor)
        
        # 复合损失函数
        reconstruction_loss = self.criterion(output, data_tensor)
        
        # 意识增长奖励
        consciousness_reward = -torch.log(1 + torch.exp(-metadata['consciousness_level']))
        
        # 风险评估正则化
        risk_penalty = torch.mean(metadata['risk_assessment'][:, 2])  # 惩罚高风险
        
        total_loss = reconstruction_loss + 0.1 * consciousness_reward + 0.05 * risk_penalty
        
        total_loss.backward()
        torch.nn.utils.clip_grad_norm_(self.consciousness_net.parameters(), 1.0)
        self.optimizer.step()
        self.scheduler.step()
        
        # 记录指标
        self.performance_metrics['consciousness_levels'].append(
            metadata['consciousness_level'].item()
        )
        
        return total_loss.item()
    
    def analyze_critical_points(self):
        """分析关键节点并生成干预策略"""
        if not self.simulator.critical_events:
            return None
        
        latest_event = self.simulator.critical_events[-1]
        system_idx = latest_event['system_idx']
        
        # 使用意识网络分析
        data = self.simulator.get_system_data()
        data_tensor = torch.FloatTensor(data)
        
        with torch.no_grad():
            _, metadata = self.consciousness_net(data_tensor)
            
            consciousness_level = metadata['consciousness_level'].item()
            risk_assessment = metadata['risk_assessment'][system_idx].numpy()
            
            # 生成干预策略
            if risk_assessment[2] > 0.7:  # 高风险
                intervention_type = 'stabilize'
                strength = 0.1
            elif risk_assessment[1] > 0.5:  # 中风险
                intervention_type = 'modulate'
                strength = 0.3
            else:  # 低风险
                intervention_type = 'enhance'
                strength = 0.5
            
            intervention = {
                'system_idx': system_idx,
                'time': self.simulator.time,
                'type': intervention_type,
                'strength': strength * consciousness_level,
                'risk_assessment': risk_assessment,
                'consciousness_level': consciousness_level
            }
            
            return intervention
        
        return None
    
    def execute_intervention(self, intervention):
        """执行干预"""
        if intervention is None:
            return False
        
        system_idx = intervention['system_idx']
        strength = intervention['strength']
        
        # 应用干预到系统状态
        current_state = self.simulator.systems[system_idx]['state']
        
        if intervention['type'] == 'stabilize':
            # 稳定化干预 - 减小状态变化
            noise = np.random.normal(0, 0.01, 3)
            new_state = current_state * (1 - strength) + noise
        elif intervention['type'] == 'modulate':
            # 调制干预 - 调整状态方向
            modulation = np.random.normal(0, strength, 3)
            new_state = current_state + modulation
        elif intervention['type'] == 'enhance':
            # 增强干预 - 强化当前趋势
            new_state = current_state * (1 + strength)
        
        self.simulator.systems[system_idx]['state'] = new_state
        
        # 记录干预
        intervention['original_state'] = current_state.copy()
        intervention['new_state'] = new_state.copy()
        self.intervention_history.append(intervention)
        
        return True

class UniverseCanvas(FigureCanvas):
    """宇宙系统画布"""
    
    def __init__(self, parent=None, width=8, height=6, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        super(UniverseCanvas, self).__init__(self.fig)
        self.setParent(parent)
        
        self.ax1 = self.fig.add_subplot(231, projection='3d')
        self.ax2 = self.fig.add_subplot(232)
        self.ax3 = self.fig.add_subplot(233)
        self.ax4 = self.fig.add_subplot(234)
        self.ax5 = self.fig.add_subplot(235)
        self.ax6 = self.fig.add_subplot(236)
        
        self.fig.tight_layout(pad=3.0)
        
    def update_plots(self, robotic_system):
        """更新所有图表"""
        self.fig.suptitle(f'宇宙机器人系统监控 - 时间: {robotic_system.simulator.time:.2f}', 
                         fontsize=14, fontweight='bold')
        
        self._plot_universe_systems(robotic_system)
        self._plot_consciousness_evolution(robotic_system)
        self._plot_intervention_analysis(robotic_system)
        self._plot_risk_assessment(robotic_system)
        self._plot_energy_dynamics(robotic_system)
        self._plot_quantum_states(robotic_system)
        
        self.draw()
    
    def _plot_universe_systems(self, robotic_system):
        """绘制宇宙系统状态"""
        self.ax1.clear()
        
        colors = ['red', 'blue', 'green', 'purple', 'orange', 'brown']
        
        for i, system in enumerate(robotic_system.simulator.systems):
            if len(system['history']) > 1:
                history = np.array(system['history'][-500:])  # 最近500个点
                color = colors[i % len(colors)]
                
                self.ax1.plot(history[:, 0], history[:, 1], history[:, 2], 
                             color=color, alpha=0.7, linewidth=1, 
                             label=f'系统 {i+1}')
                
                # 标记当前位置
                current_pos = system['state']
                self.ax1.scatter(current_pos[0], current_pos[1], current_pos[2], 
                                color=color, s=50, marker='o')
        
        self.ax1.set_title('多元宇宙系统轨迹')
        self.ax1.set_xlabel('X轴')
        self.ax1.set_ylabel('Y轴')
        self.ax1.set_zlabel('Z轴')
        self.ax1.legend()
    
    def _plot_consciousness_evolution(self, robotic_system):
        """绘制意识进化"""
        self.ax2.clear()
        
        if robotic_system.performance_metrics['consciousness_levels']:
            levels = robotic_system.performance_metrics['consciousness_levels'][-1000:]
            self.ax2.plot(levels, 'g-', linewidth=2)
            self.ax2.set_title('意识水平进化')
            self.ax2.set_xlabel('训练步数')
            self.ax2.set_ylabel('意识水平')
            self.ax2.grid(True, alpha=0.3)
    
    def _plot_intervention_analysis(self, robotic_system):
        """绘制干预分析"""
        self.ax3.clear()
        
        if robotic_system.intervention_history:
            times = [interv['time'] for interv in robotic_system.intervention_history]
            strengths = [interv['strength'] for interv in robotic_system.intervention_history]
            types = [interv['type'] for interv in robotic_system.intervention_history]
            
            colors = {'stabilize': 'red', 'modulate': 'blue', 'enhance': 'green'}
            color_list = [colors[t] for t in types]
            
            self.ax3.scatter(times, strengths, c=color_list, alpha=0.6, s=50)
            self.ax3.set_title('干预时间与强度分析')
            self.ax3.set_xlabel('时间')
            self.ax3.set_ylabel('干预强度')
            self.ax3.grid(True, alpha=0.3)
    
    def _plot_risk_assessment(self, robotic_system):
        """绘制风险评估"""
        self.ax4.clear()
        
        if robotic_system.intervention_history:
            risks = [interv['risk_assessment'] for interv in robotic_system.intervention_history]
            risks = np.array(risks)
            
            self.ax4.stackplot(range(len(risks)), 
                              risks[:, 0], risks[:, 1], risks[:, 2],
                              labels=['低风险', '中风险', '高风险'],
                              colors=['green', 'yellow', 'red'])
            
            self.ax4.set_title('风险评估趋势')
            self.ax4.set_xlabel('干预次数')
            self.ax4.set_ylabel('风险概率')
            self.ax4.legend()
            self.ax4.grid(True, alpha=0.3)
    
    def _plot_energy_dynamics(self, robotic_system):
        """绘制能量动态"""
        self.ax5.clear()
        
        for i, system in enumerate(robotic_system.simulator.systems):
            if system['energy']:
                energy = system['energy'][-500:]
                self.ax5.plot(energy, label=f'系统 {i+1}')
        
        self.ax5.set_title('系统能量动态')
        self.ax5.set_xlabel('时间步')
        self.ax5.set_ylabel('能量')
        self.ax5.legend()
        self.ax5.grid(True, alpha=0.3)
    
    def _plot_quantum_states(self, robotic_system):
        """绘制量子状态"""
        self.ax6.clear()
        
        # 模拟量子概率分布
        theta = np.linspace(0, 4*np.pi, 100)
        if robotic_system.performance_metrics['consciousness_levels']:
            current_level = robotic_system.performance_metrics['consciousness_levels'][-1]
            wave = np.sin(theta + current_level * 10) * np.exp(-0.1 * theta)
            probability = wave ** 2
            
            self.ax6.plot(theta, wave, 'b-', label='波函数')
            self.ax6.fill_between(theta, probability, alpha=0.3, label='概率密度')
            
            # 标记当前意识水平对应的相位
            phase = current_level * 4 * np.pi
            self.ax6.axvline(x=phase, color='red', linestyle='--', 
                            label=f'意识相位: {current_level:.3f}')
        
        self.ax6.set_title('量子意识波函数')
        self.ax6.set_xlabel('相位')
        self.ax6.set_ylabel('振幅')
        self.ax6.legend()
        self.ax6.grid(True, alpha=0.3)

class ControlPanel(QWidget):
    """控制面板"""
    
    intervention_signal = pyqtSignal(dict)
    
    def __init__(self, robotic_system):
        super().__init__()
        self.robotic_system = robotic_system
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 系统状态组
        status_group = QGroupBox("系统状态")
        status_layout = QGridLayout()
        
        self.consciousness_label = QLabel("意识水平: 0.000")
        self.risk_label = QLabel("总体风险: 低")
        self.systems_label = QLabel("活跃系统: 0")
        self.interventions_label = QLabel("干预次数: 0")
        
        status_layout.addWidget(self.consciousness_label, 0, 0)
        status_layout.addWidget(self.risk_label, 0, 1)
        status_layout.addWidget(self.systems_label, 1, 0)
        status_layout.addWidget(self.interventions_label, 1, 1)
        
        status_group.setLayout(status_layout)
        layout.addWidget(status_group)
        
        # 控制组
        control_group = QGroupBox("系统控制")
        control_layout = QVBoxLayout()
        
        # 添加系统按钮
        self.add_system_btn = QPushButton("添加宇宙系统")
        self.add_system_btn.clicked.connect(self.add_system)
        control_layout.addWidget(self.add_system_btn)
        
        # 系统类型选择
        system_type_layout = QHBoxLayout()
        system_type_layout.addWidget(QLabel("系统类型:"))
        self.system_type_combo = QComboBox()
        self.system_type_combo.addItems(["洛伦兹吸引子", "罗斯勒吸引子"])
        system_type_layout.addWidget(self.system_type_combo)
        control_layout.addLayout(system_type_layout)
        
        # 训练控制
        train_layout = QHBoxLayout()
        self.train_btn = QPushButton("开始训练")
        self.train_btn.clicked.connect(self.toggle_training)
        self.auto_intervene_check = QCheckBox("自动干预")
        self.auto_intervene_check.setChecked(True)
        
        train_layout.addWidget(self.train_btn)
        train_layout.addWidget(self.auto_intervene_check)
        control_layout.addLayout(train_layout)
        
        # 手动干预
        intervene_layout = QHBoxLayout()
        self.intervene_btn = QPushButton("手动干预")
        self.intervene_btn.clicked.connect(self.manual_intervention)
        self.intervene_type_combo = QComboBox()
        self.intervene_type_combo.addItems(["稳定化", "调制", "增强"])
        
        intervene_layout.addWidget(self.intervene_btn)
        intervene_layout.addWidget(self.intervene_type_combo)
        control_layout.addLayout(intervene_layout)
        
        # 干预强度
        strength_layout = QHBoxLayout()
        strength_layout.addWidget(QLabel("干预强度:"))
        self.strength_spin = QDoubleSpinBox()
        self.strength_spin.setRange(0.0, 1.0)
        self.strength_spin.setValue(0.3)
        self.strength_spin.setSingleStep(0.1)
        strength_layout.addWidget(self.strength_spin)
        control_layout.addLayout(strength_layout)
        
        control_group.setLayout(control_layout)
        layout.addWidget(control_group)
        
        # 性能监控组
        perf_group = QGroupBox("性能监控")
        perf_layout = QVBoxLayout()
        
        self.consciousness_progress = QProgressBar()
        self.consciousness_progress.setRange(0, 1000)
        self.consciousness_progress.setFormat("意识水平: %v")
        perf_layout.addWidget(QLabel("意识水平:"))
        perf_layout.addWidget(self.consciousness_progress)
        
        self.stability_progress = QProgressBar()
        self.stability_progress.setRange(0, 100)
        self.stability_progress.setFormat("系统稳定性: %v%")
        perf_layout.addWidget(QLabel("系统稳定性:"))
        perf_layout.addWidget(self.stability_progress)
        
        perf_group.setLayout(perf_layout)
        layout.addWidget(perf_group)
        
        # 日志组
        log_group = QGroupBox("系统日志")
        log_layout = QVBoxLayout()
        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(150)
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)
        
        self.setLayout(layout)
    
    def add_system(self):
        system_type = "lorenz" if self.system_type_combo.currentText() == "洛伦兹吸引子" else "rossler"
        self.robotic_system.simulator.add_system(system_type)
        self.log_message(f"添加了新的{system_type}系统")
        self.update_status()
    
    def toggle_training(self):
        if self.train_btn.text() == "开始训练":
            self.train_btn.setText("停止训练")
            self.log_message("开始意识网络训练")
        else:
            self.train_btn.setText("开始训练")
            self.log_message("停止意识网络训练")
    
    def manual_intervention(self):
        if not self.robotic_system.simulator.systems:
            QMessageBox.warning(self, "警告", "没有可干预的系统")
            return
        
        intervention_type_map = {"稳定化": "stabilize", "调制": "modulate", "增强": "enhance"}
        intervention_type = intervention_type_map[self.intervene_type_combo.currentText()]
        strength = self.strength_spin.value()
        
        # 选择最近的关键事件或随机系统
        if self.robotic_system.simulator.critical_events:
            system_idx = self.robotic_system.simulator.critical_events[-1]['system_idx']
        else:
            system_idx = np.random.randint(0, len(self.robotic_system.simulator.systems))
        
        intervention = {
            'system_idx': system_idx,
            'time': self.robotic_system.simulator.time,
            'type': intervention_type,
            'strength': strength,
            'risk_assessment': np.array([0.7, 0.2, 0.1]),  # 手动干预假设低风险
            'consciousness_level': self.robotic_system.performance_metrics['consciousness_levels'][-1] 
            if self.robotic_system.performance_metrics['consciousness_levels'] else 0.1
        }
        
        self.robotic_system.execute_intervention(intervention)
        self.log_message(f"执行手动{intervention_type}干预，强度: {strength:.2f}")
    
    def log_message(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
        # 保持日志长度
        if self.log_text.document().lineCount() > 100:
            cursor = self.log_text.textCursor()
            cursor.movePosition(cursor.Start)
            cursor.select(cursor.LineUnderCursor)
            cursor.removeSelectedText()
    
    def update_status(self):
        # 更新意识水平
        if self.robotic_system.performance_metrics['consciousness_levels']:
            level = self.robotic_system.performance_metrics['consciousness_levels'][-1]
            self.consciousness_label.setText(f"意识水平: {level:.3f}")
            self.consciousness_progress.setValue(int(level * 1000))
        
        # 更新风险状态
        if self.robotic_system.intervention_history:
            latest_risk = self.robotic_system.intervention_history[-1]['risk_assessment']
            if latest_risk[2] > 0.5:
                risk_text = "高"
            elif latest_risk[1] > 0.3:
                risk_text = "中"
            else:
                risk_text = "低"
            self.risk_label.setText(f"总体风险: {risk_text}")
        
        # 更新系统计数
        self.systems_label.setText(f"活跃系统: {len(self.robotic_system.simulator.systems)}")
        self.interventions_label.setText(f"干预次数: {len(self.robotic_system.intervention_history)}")
        
        # 更新稳定性（简化计算）
        stability = max(0, 100 - len(self.robotic_system.intervention_history))
        self.stability_progress.setValue(stability)

class CosmicRoboticApp(QMainWindow):
    """宇宙机器人主应用"""
    
    def __init__(self):
        super().__init__()
        self.robotic_system = CosmicRoboticSystem()
        self.is_training = False
        self.is_running = False
        
        self.init_ui()
        self.setup_timers()
    
    def init_ui(self):
        self.setWindowTitle("《阴符经》量子意识机器人系统")
        self.setGeometry(100, 100, 1600, 1000)
        
        # 中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QHBoxLayout()
        
        # 左侧控制面板
        self.control_panel = ControlPanel(self.robotic_system)
        main_layout.addWidget(self.control_panel, 1)
        
        # 右侧可视化区域
        right_layout = QVBoxLayout()
        
        # 宇宙画布
        self.universe_canvas = UniverseCanvas(self, width=10, height=8)
        right_layout.addWidget(self.universe_canvas)
        
        main_layout.addLayout(right_layout, 3)
        
        central_widget.setLayout(main_layout)
        
        # 状态栏
        self.statusBar().showMessage("系统就绪 - 等待启动命令")
    
    def setup_timers(self):
        # 模拟计时器
        self.simulation_timer = QTimer()
        self.simulation_timer.timeout.connect(self.update_simulation)
        self.simulation_timer.start(50)  # 20 Hz
        
        # 训练计时器
        self.training_timer = QTimer()
        self.training_timer.timeout.connect(self.update_training)
        
        # 状态更新计时器
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_status)
        self.status_timer.start(100)  # 10 Hz
    
    def update_simulation(self):
        """更新模拟"""
        self.robotic_system.simulator.update_systems()
        
        # 自动干预
        if self.control_panel.auto_intervene_check.isChecked() and self.is_training:
            intervention = self.robotic_system.analyze_critical_points()
            if intervention:
                self.robotic_system.execute_intervention(intervention)
                self.control_panel.log_message(
                    f"自动{intervention['type']}干预 - 系统{intervention['system_idx']+1}"
                )
    
    def update_training(self):
        """更新训练"""
        if self.is_training:
            loss = self.robotic_system.train_step()
            
            # 每100步记录一次损失
            if hasattr(self, 'train_step_count'):
                self.train_step_count += 1
            else:
                self.train_step_count = 0
            
            if self.train_step_count % 100 == 0:
                self.control_panel.log_message(f"训练损失: {loss:.4f}")
    
    def update_status(self):
        """更新状态"""
        self.control_panel.update_status()
        self.universe_canvas.update_plots(self.robotic_system)
        
        # 更新状态栏
        if self.is_training:
            status = f"训练中 - 意识水平: {self.robotic_system.performance_metrics['consciousness_levels'][-1]:.3f}" \
                    if self.robotic_system.performance_metrics['consciousness_levels'] else "训练中"
        else:
            status = "就绪"
        
        self.statusBar().showMessage(status)
    
    def closeEvent(self, event):
        """关闭事件"""
        reply = QMessageBox.question(self, '确认退出',
                                   '确定要退出宇宙机器人系统吗？',
                                   QMessageBox.Yes | QMessageBox.No,
                                   QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            # 停止所有计时器
            self.simulation_timer.stop()
            self.training_timer.stop()
            self.status_timer.stop()
            event.accept()
        else:
            event.ignore()

def main():
    app = QApplication(sys.argv)
    
    # 设置应用样式
    app.setStyle('Fusion')
    
    # 创建并显示主窗口
    main_window = CosmicRoboticApp()
    main_window.show()
    
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()