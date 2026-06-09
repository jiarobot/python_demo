import sys
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.gridspec import GridSpec
from scipy.integrate import solve_ivp
from tqdm import tqdm
import pandas as pd
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QGroupBox, QLabel, QLineEdit, QPushButton, QComboBox, 
                            QTabWidget, QTextEdit, QScrollArea, QSplitter, QFormLayout)
from PyQt5.QtCore import Qt

plt.rcParams['font.family'] = 'SimHei'
plt.rcParams['axes.unicode_minus'] = False

class TwelveStages:
    """十二长生系统"""
    STAGES = ["长生", "沐浴", "冠带", "临官", "帝旺", 
              "衰", "病", "死", "墓", "绝", "胎", "养"]
    
    ELEMENTAL_PHASES = {
        "木": [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 0, 1],
        "火": [5, 6, 7, 8, 9, 10, 11, 0, 1, 2, 3, 4],
        "土": [8, 9, 10, 11, 0, 1, 2, 3, 4, 5, 6, 7],
        "金": [11, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        "水": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 0]
    }
    
    STAGE_COLORS = {
        "长生": '#1f77b4',    # 深蓝
        "沐浴": '#aec7e8',    # 浅蓝
        "冠带": '#2ca02c',    # 绿色
        "临官": '#98df8a',    # 浅绿
        "帝旺": '#d62728',    # 红色
        "衰": '#ff9896',      # 浅红
        "病": '#8c564b',      # 棕色
        "死": '#7f7f7f',      # 灰色
        "墓": '#9467bd',      # 紫色
        "绝": '#c5b0d5',      # 浅紫
        "胎": '#e377c2',      # 粉色
        "养": '#f7b6d2'       # 浅粉
    }
    
    def __init__(self, elemental_phase="木"):
        self.elemental_phase = elemental_phase
        self.current_stage_idx = 0
        self.stage_history = []
        
    def advance_stage(self, chaos_level):
        transition_prob = min(0.8, 0.05 + chaos_level * 0.3)
        if np.random.rand() < transition_prob:
            self.current_stage_idx = (self.current_stage_idx + 1) % 12
            self.stage_history.append(self.current_stage_idx)
        return self.current_stage()
    
    def current_stage(self):
        adjusted_idx = (self.current_stage_idx + 
                       self.ELEMENTAL_PHASES[self.elemental_phase][0]) % 12
        return self.STAGES[adjusted_idx]
    
    def stage_effect(self):
        stage = self.current_stage()
        effects = {
            "长生": 1.2, "沐浴": 0.9, "冠带": 1.1, "临官": 1.3, 
            "帝旺": 1.5, "衰": 0.95, "病": 0.8, "死": 0.5, 
            "墓": 0.7, "绝": 0.6, "胎": 1.0, "养": 1.05
        }
        return effects[stage]
    
    def stage_color(self, stage=None):
        stage = stage or self.current_stage()
        return self.STAGE_COLORS[stage]
    
    def get_stage_sequence(self):
        return [self.STAGES[i] for i in self.ELEMENTAL_PHASES[self.elemental_phase]]


class QuantumChaosSystem:
    def __init__(self, dimension=3, hbar=1.0, G=0.1, alpha=0.618, 
                 decoherence_rate=0.01, elemental_phase="木", 
                 sigma=10.0, rho=28.0, beta=8.0/3.0):
        self.d = max(3, dimension)
        self.hbar = hbar
        self.G = G
        self.alpha = alpha
        self.decoherence_rate = decoherence_rate
        self.elemental_phase = elemental_phase
        self.sigma = sigma
        self.rho = rho
        self.beta = beta
        
        self.twelve_stages = TwelveStages(elemental_phase)
        self.initialize_system()
        
    def initialize_system(self):
        self.psi = np.random.randn(self.d) + 1j * np.random.randn(self.d)
        self.psi /= np.linalg.norm(self.psi)
        self.A = np.zeros((self.d, self.d))
        self.history = []
        self.lyapunov = np.zeros(self.d)
        self.trajectory = []
        self.reference = []
        self.topological_charge_history = []
        self.control_system = None
    
    def chaos_dynamics(self, t, state):
        x, y, z = state[:3]
        dxdt = self.sigma * (y - x)
        dydt = x * (self.rho - z) - y
        dzdt = x * y - self.beta * z
        
        dstate = np.zeros_like(state)
        dstate[0] = dxdt
        dstate[1] = dydt
        dstate[2] = dzdt
        
        for i in range(3, len(state)):
            dstate[i] = -0.1 * state[i]
        
        return dstate
    
    def quantum_fluctuation(self, dt):
        stage_effect = self.twelve_stages.stage_effect()
        fluctuation_factor = 1.0
        current_stage = self.twelve_stages.current_stage()
        
        if current_stage == "沐浴":
            fluctuation_factor = 1.5
        elif current_stage == "死" or current_stage == "墓":
            fluctuation_factor = 0.5
        
        fluctuation = (np.random.randn(self.d) + 1j * np.random.randn(self.d)) * np.sqrt(dt * self.hbar * fluctuation_factor * stage_effect)
        self.psi += fluctuation
        self.psi /= np.linalg.norm(self.psi)
    
    def gravitational_interaction(self, dt):
        stage_effect = self.twelve_stages.stage_effect()
        mass_dist = np.abs(self.psi)**2
        G_potential = np.zeros_like(self.psi)
        
        for i in range(self.d):
            for j in range(self.d):
                if i != j:
                    r = abs(i - j)
                    if self.twelve_stages.current_stage() == "帝旺":
                        G_potential[i] += -self.G * 1.8 * mass_dist[j] / (r + 1e-10)
                    elif self.twelve_stages.current_stage() == "绝":
                        G_potential[i] += -self.G * 0.5 * mass_dist[j] / (r + 1e-10)
                    else:
                        G_potential[i] += -self.G * stage_effect * mass_dist[j] / (r + 1e-10)
        
        self.psi = self.psi * np.exp(-1j * G_potential * dt / self.hbar)
        self.psi /= np.linalg.norm(self.psi)
    
    def decoherence_model(self, dt):
        stage_effect = self.twelve_stages.stage_effect()
        current_stage = self.twelve_stages.current_stage()
        decoherence_factor = 1.0
        
        if current_stage == "病" or current_stage == "死":
            decoherence_factor = 1.8
        elif current_stage == "长生" or current_stage == "帝旺":
            decoherence_factor = 0.7
        
        if np.random.rand() < self.decoherence_rate * dt * decoherence_factor:
            basis = np.random.randn(self.d) + 1j * np.random.randn(self.d)
            basis /= np.linalg.norm(basis)
            proj = np.outer(basis, np.conj(basis))
            self.psi = proj @ self.psi
            self.psi /= np.linalg.norm(self.psi)
        
        gamma = self.decoherence_rate * stage_effect * decoherence_factor
        for i in range(self.d):
            op = np.zeros((self.d, self.d))
            op[i, i] = 1
            L_term = op @ self.psi - 0.5 * (op @ op.conj().T @ self.psi + op.conj().T @ op @ self.psi)
            self.psi -= gamma * L_term * dt
        
        self.psi /= np.linalg.norm(self.psi)
    
    def topological_charge(self):
        U = np.zeros((self.d, self.d), dtype=complex)
        for i in range(self.d):
            for j in range(self.d):
                if i != j:
                    phase_diff = np.angle(self.psi[i] * np.conj(self.psi[j]))
                    U[i, j] = 1j * self.A[i, j] * np.exp(1j * phase_diff)
        
        F = U - np.conj(U).T
        charge = np.trace(F @ F) / (2 * np.pi * 1j)
        return np.real(charge)
    
    def instanton_effect(self, dt):
        stage_effect = self.twelve_stages.stage_effect()
        current_charge = self.topological_charge()
        
        if self.topological_charge_history:
            prev_charge = self.topological_charge_history[-1]
            if abs(current_charge - prev_charge) > 0.5:
                tunneling_strength = 1.0
                if self.twelve_stages.current_stage() == "胎" or self.twelve_stages.current_stage() == "养":
                    tunneling_strength = 2.0
                elif self.twelve_stages.current_stage() == "死" or self.twelve_stages.current_stage() == "墓":
                    tunneling_strength = 0.5
                
                tunneling = np.exp(1j * np.random.uniform(0, 2*np.pi, self.d) * tunneling_strength * stage_effect)
                self.psi *= tunneling
                self.psi /= np.linalg.norm(self.psi)
        
        self.topological_charge_history.append(float(current_charge))
    
    def evolve(self, dt, steps):
        self.initialize_system()
        self.history = []
        self.topological_charge_history = []
        
        state = np.real(self.psi[:self.d]).copy()
        ref_state = state.copy() + 1e-8 * np.random.randn(self.d)
        
        self.trajectory = [state.copy()]
        self.reference = [ref_state.copy()]
        lyap_exp = np.zeros((steps, self.d))
        
        for i in tqdm(range(steps), desc="演化量子混沌系统"):
            t_span = [i*dt, (i+1)*dt]
            sol = solve_ivp(self.chaos_dynamics, t_span, state, method='RK45')
            state = sol.y[:, -1]
            
            if self.control_system:
                state = self.apply_control(state, dt)
            
            sol_ref = solve_ivp(self.chaos_dynamics, t_span, ref_state, method='RK45')
            ref_state = sol_ref.y[:, -1]
            
            chaos_level = min(1.0, np.linalg.norm(state) / 50.0)
            current_stage = self.twelve_stages.advance_stage(chaos_level)
            
            self.gravitational_interaction(dt)
            self.quantum_fluctuation(dt)
            self.decoherence_model(dt)
            self.instanton_effect(dt)
            
            self.A = np.roll(self.A, 1, axis=0)
            self.A += 0.01 * np.random.randn(*self.A.shape)
            
            self.history.append({
                'time': (i+1)*dt,
                'state': state.copy(),
                'psi': self.psi.copy(),
                'A': self.A.copy(),
                'topological_charge': self.topological_charge_history[-1] if self.topological_charge_history else 0,
                'twelve_stages': current_stage,
                'stage_color': self.twelve_stages.stage_color()
            })
            
            self.trajectory.append(state.copy())
            self.reference.append(ref_state.copy())
            
            delta = ref_state - state
            if np.linalg.norm(delta) > 1e-10:
                lyap_exp[i] = np.log(np.abs(delta) + 1e-10) / dt
            else:
                lyap_exp[i] = lyap_exp[i-1] if i > 0 else np.zeros(self.d)
        
        self.lyapunov = np.mean(lyap_exp[int(steps/2):], axis=0)
        return self.history
    
    def generate_stage_report(self):
        if not self.history:
            return pd.DataFrame()
        
        stages = [h['twelve_stages'] for h in self.history]
        chaos_energy = np.linalg.norm([h['state'] for h in self.history], axis=1)
        entropy = [np.abs(h['psi'][0]) for h in self.history]
        lyapunov = [np.max(np.abs(h['state'])) for h in self.history]
        
        df = pd.DataFrame({
            '时间': [h['time'] for h in self.history],
            '长生阶段': stages,
            '混沌能量': chaos_energy,
            '量子熵': entropy,
            '李雅普诺夫指数': lyapunov
        })
        
        grouped = df.groupby('长生阶段').agg({
            '混沌能量': ['mean', 'std', 'max'],
            '量子熵': ['mean', 'std'],
            '李雅普诺夫指数': ['mean', 'std']
        })
        
        grouped.columns = ['_'.join(col).strip() for col in grouped.columns.values]
        grouped = grouped.rename(columns={
            '混沌能量_mean': '平均混沌能量',
            '混沌能量_std': '混沌能量标准差',
            '混沌能量_max': '最大混沌能量',
            '量子熵_mean': '平均量子熵',
            '量子熵_std': '量子熵标准差',
            '李雅普诺夫指数_mean': '平均李雅普诺夫指数',
            '李雅普诺夫指数_std': '李雅普诺夫指数标准差'
        })
        
        stage_descriptions = {
            "长生": "新生阶段，系统开始生长，量子效应逐渐增强",
            "沐浴": "不稳定阶段，系统波动增大，量子涨落明显",
            "冠带": "成长阶段，系统结构形成，混沌开始显现",
            "临官": "成熟阶段，系统达到稳定状态，混沌有序",
            "帝旺": "巅峰阶段，系统能量最强，混沌效应显著",
            "衰": "衰退阶段，系统能量减弱，混沌效应下降",
            "病": "问题阶段，系统出现异常，量子退相干增强",
            "死": "死亡阶段，系统能量最低，混沌效应消失",
            "墓": "隐藏阶段，系统能量储存，为新生准备",
            "绝": "断绝阶段，系统连接中断，量子隧穿减少",
            "胎": "孕育阶段，新系统开始形成，量子效应恢复",
            "养": "滋养阶段，系统能量积累，混沌效应再生"
        }
        
        grouped['阶段描述'] = grouped.index.map(stage_descriptions)
        grouped = grouped[['阶段描述', '平均混沌能量', '混沌能量标准差', '最大混沌能量',
                          '平均量子熵', '量子熵标准差', 
                          '平均李雅普诺夫指数', '李雅普诺夫指数标准差']]
        
        return grouped


class ParameterControl(QGroupBox):
    """参数控制面板"""
    def __init__(self, parent=None):
        super().__init__("系统参数设置", parent)
        self.input_fields = {}
        self.init_ui()
        
    def init_ui(self):
        layout = QFormLayout()
        
        # 五行属性选择
        self.element_combo = QComboBox()
        self.element_combo.addItems(["木", "火", "土", "金", "水"])
        layout.addRow("五行属性:", self.element_combo)
        
        # 系统参数
        self.input_fields["dimension"] = QLineEdit("5")
        layout.addRow("系统维度:", self.input_fields["dimension"])
        
        self.input_fields["hbar"] = QLineEdit("0.5")
        layout.addRow("普朗克常数:", self.input_fields["hbar"])
        
        self.input_fields["G"] = QLineEdit("0.15")
        layout.addRow("引力耦合:", self.input_fields["G"])
        
        self.input_fields["decoherence_rate"] = QLineEdit("0.01")
        layout.addRow("退相干率:", self.input_fields["decoherence_rate"])
        
        # 混沌参数
        self.input_fields["sigma"] = QLineEdit("10.0")
        layout.addRow("σ (对流强度):", self.input_fields["sigma"])
        
        self.input_fields["rho"] = QLineEdit("28.0")
        layout.addRow("ρ (稳定性阈值):", self.input_fields["rho"])
        
        self.input_fields["beta"] = QLineEdit("2.67")
        layout.addRow("β (耗散系数):", self.input_fields["beta"])
        
        # 演化参数
        self.input_fields["dt"] = QLineEdit("0.02")
        layout.addRow("时间步长:", self.input_fields["dt"])
        
        self.input_fields["steps"] = QLineEdit("1000")
        layout.addRow("演化步数:", self.input_fields["steps"])
        
        self.setLayout(layout)
    
    def get_parameters(self):
        return {
            "elemental_phase": self.element_combo.currentText(),
            "dimension": int(self.input_fields["dimension"].text()),
            "hbar": float(self.input_fields["hbar"].text()),
            "G": float(self.input_fields["G"].text()),
            "decoherence_rate": float(self.input_fields["decoherence_rate"].text()),
            "sigma": float(self.input_fields["sigma"].text()),
            "rho": float(self.input_fields["rho"].text()),
            "beta": float(self.input_fields["beta"].text()),
            "dt": float(self.input_fields["dt"].text()),
            "steps": int(self.input_fields["steps"].text())
        }


class VisualizationCanvas(FigureCanvas):
    """可视化画布"""
    def __init__(self, parent=None, width=10, height=8, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        super().__init__(self.fig)
        self.setParent(parent)
        self.ax3d = None
        self.ax_stages = None
        self.ax_energy = None
        self.ax_relations = None
        self.ax_lyapunov = None
    
    def visualize(self, chaos_system):
        if not chaos_system.history:
            return
        
        self.fig.clear()
        gs = GridSpec(3, 2, figure=self.fig)
        
        # 1. 混沌轨迹
        self.ax3d = self.fig.add_subplot(gs[0, :], projection='3d')
        states = np.array([h['state'] for h in chaos_system.history])
        stage_colors = [h['stage_color'] for h in chaos_system.history]
        
        for i in range(1, len(states)):
            self.ax3d.plot(states[i-1:i+1, 0], states[i-1:i+1, 1], states[i-1:i+1, 2],
                          color=stage_colors[i], alpha=0.7, linewidth=1.2)
        
        self.ax3d.set_title(f'五行:{chaos_system.elemental_phase} - 混沌轨迹', fontsize=12)
        self.ax3d.set_xlabel('X')
        self.ax3d.set_ylabel('Y')
        self.ax3d.set_zlabel('Z')
        
        # 2. 阶段分布
        self.ax_stages = self.fig.add_subplot(gs[1, 0])
        stages = [h['twelve_stages'] for h in chaos_system.history]
        unique_stages = chaos_system.twelve_stages.get_stage_sequence()
        stage_counts = [stages.count(stage) for stage in unique_stages]
        colors = [chaos_system.twelve_stages.stage_color(stage) for stage in unique_stages]
        
        self.ax_stages.bar(unique_stages, stage_counts, color=colors)
        self.ax_stages.set_title('长生阶段分布', fontsize=10)
        self.ax_stages.set_ylabel('出现次数')
        self.ax_stages.tick_params(axis='x', rotation=45)
        
        # 3. 能量变化
        self.ax_energy = self.fig.add_subplot(gs[1, 1])
        times = [h['time'] for h in chaos_system.history]
        chaos_energy = np.linalg.norm([h['state'] for h in chaos_system.history], axis=1)
        entropy = [np.abs(h['psi'][0]) for h in chaos_system.history]
        
        self.ax_energy.plot(times, chaos_energy, 'b-', label='混沌能量')
        self.ax_energy.plot(times, entropy, 'r-', label='量子熵')
        self.ax_energy.set_title('能量与熵变化', fontsize=10)
        self.ax_energy.set_xlabel('时间')
        self.ax_energy.legend()
        self.ax_energy.grid(True, linestyle='--', alpha=0.7)
        
        # 4. 五行关系
        self.ax_relations = self.fig.add_subplot(gs[2, 0])
        elements = ["木", "火", "土", "金", "水"]
        relations = np.array([
            [0, 1, 0.5, -1, 0.5],
            [0.5, 0, 1, 0.5, -1],
            [-1, 0.5, 0, 1, 0.5],
            [0.5, -1, 0.5, 0, 1],
            [1, 0.5, -1, 0.5, 0]
        ])
        
        current_idx = elements.index(chaos_system.elemental_phase)
        angles = np.linspace(0, 2*np.pi, len(elements), endpoint=False)
        
        self.ax_relations.plot(np.append(angles, angles[0]), 
                              np.append(relations[current_idx], relations[current_idx][0]), 
                              'o-', linewidth=2, color='darkgreen')
        self.ax_relations.fill(np.append(angles, angles[0]), 
                              np.append(relations[current_idx], relations[current_idx][0]), 
                              alpha=0.25, color='lightgreen')
        
        self.ax_relations.set_xticks(angles)
        self.ax_relations.set_xticklabels(elements)
        self.ax_relations.set_ylim(-1.5, 1.5)
        self.ax_relations.set_title(f'五行生克关系: {chaos_system.elemental_phase}为中心', fontsize=10)
        self.ax_relations.grid(True)
        
        for i, elem in enumerate(elements):
            relation = relations[current_idx][i]
            if relation > 0:
                self.ax_relations.annotate('生', (angles[i], relation + 0.1), ha='center', color='red')
            elif relation < 0:
                self.ax_relations.annotate('克', (angles[i], relation - 0.1), ha='center', color='blue')
            else:
                self.ax_relations.annotate('平', (angles[i], relation), ha='center', color='gray')
        
        # 5. 李雅普诺夫指数
        self.ax_lyapunov = self.fig.add_subplot(gs[2, 1])
        lyap_exp = np.array([np.max(np.abs(h['state'])) for h in chaos_system.history])
        
        self.ax_lyapunov.plot(times, lyap_exp, 'g-', label='最大李雅普诺夫指数')
        self.ax_lyapunov.set_title('混沌指数变化', fontsize=10)
        self.ax_lyapunov.set_xlabel('时间')
        self.ax_lyapunov.grid(True, linestyle='--', alpha=0.7)
        
        self.fig.tight_layout()
        self.draw()


class AnalysisReport(QTextEdit):
    """分析报告显示"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setStyleSheet("font-family: 'Microsoft YaHei'; font-size: 10pt;")
    
    def show_report(self, chaos_system):
        if not chaos_system.history:
            self.setText("请先运行模拟生成数据")
            return
        
        report = chaos_system.generate_stage_report()
        if report.empty:
            self.setText("无法生成报告")
            return
        
        # 基本系统信息
        text = f"<h2>量子混沌系统分析报告</h2>"
        text += f"<p><b>五行属性:</b> {chaos_system.elemental_phase}</p>"
        text += f"<p><b>系统维度:</b> {chaos_system.d}</p>"
        text += f"<p><b>引力耦合:</b> {chaos_system.G}</p>"
        text += f"<p><b>退相干率:</b> {chaos_system.decoherence_rate}</p>"
        text += f"<p><b>混沌参数:</b> σ={chaos_system.sigma}, ρ={chaos_system.rho}, β={chaos_system.beta:.2f}</p>"
        
        # 阶段统计信息
        text += "<h3>长生阶段统计</h3>"
        text += report.to_html(classes='table table-striped', border=0)
        
        # 五行生克分析
        elemental_effects = {
            "木": "木属性系统在长生阶段表现最佳，混沌能量强且持久，但在死墓阶段恢复较慢",
            "火": "火属性系统在帝旺阶段能量最强，但波动大，需要控制避免过早进入衰退",
            "土": "土属性系统整体稳定，各阶段过渡平稳，适合长期演化研究",
            "金": "金属性系统在临官阶段表现突出，混沌与量子平衡性好，适合精密控制",
            "水": "水属性系统恢复能力强，在绝胎阶段能快速重建，适合动态环境"
        }
        
        text += "<h3>五行生克分析</h3>"
        text += f"<p>{elemental_effects.get(chaos_system.elemental_phase, '')}</p>"
        
        # 系统优化建议
        suggestions = {
            "木": "建议增加初始维度至6，在冠带阶段施加控制以延长帝旺期",
            "火": "建议在沐浴阶段降低退相干率，在帝旺阶段增加引力耦合",
            "土": "建议保持当前参数，重点关注临官到帝旺的过渡优化",
            "金": "建议在胎养阶段增加量子涨落，促进系统新生",
            "水": "建议在死墓阶段引入外部扰动，加速进入胎养阶段"
        }
        
        text += "<h3>系统优化建议</h3>"
        text += f"<p>{suggestions.get(chaos_system.elemental_phase, '')}</p>"
        
        self.setHtml(text)


class MainWindow(QMainWindow):
    """主界面"""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("量子混沌与十二长生系统模拟")
        self.setGeometry(100, 100, 1200, 800)
        
        self.chaos_system = None
        self.init_ui()
        
    def init_ui(self):
        # 创建主分割器
        main_splitter = QSplitter(Qt.Horizontal)
        
        # 左侧面板 - 参数控制
        left_panel = QWidget()
        left_layout = QVBoxLayout()
        
        self.param_control = ParameterControl()
        left_layout.addWidget(self.param_control)
        
        self.run_button = QPushButton("运行模拟")
        self.run_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50; 
                color: white; 
                font-weight: bold; 
                padding: 10px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        self.run_button.clicked.connect(self.run_simulation)
        left_layout.addWidget(self.run_button)
        
        # 状态信息
        self.status_label = QLabel("准备就绪")
        self.status_label.setStyleSheet("""
            QLabel {
                border: 1px solid #ccc; 
                padding: 10px;
                background-color: #f9f9f9;
                min-height: 40px;
            }
        """)
        left_layout.addWidget(self.status_label)
        
        left_panel.setLayout(left_layout)
        
        # 右侧面板 - 结果展示
        self.tabs = QTabWidget()
        
        # 可视化标签页
        vis_tab = QWidget()
        vis_layout = QVBoxLayout()
        self.vis_canvas = VisualizationCanvas(self)
        vis_layout.addWidget(self.vis_canvas)
        vis_tab.setLayout(vis_layout)
        
        # 报告标签页
        report_tab = QWidget()
        report_layout = QVBoxLayout()
        self.report_view = AnalysisReport()
        report_layout.addWidget(self.report_view)
        report_tab.setLayout(report_layout)
        
        self.tabs.addTab(vis_tab, "可视化结果")
        self.tabs.addTab(report_tab, "分析报告")
        
        main_splitter.addWidget(left_panel)
        main_splitter.addWidget(self.tabs)
        main_splitter.setSizes([300, 900])
        
        self.setCentralWidget(main_splitter)
    
    def run_simulation(self):
        self.status_label.setText("正在初始化系统...")
        QApplication.processEvents()
        
        try:
            params = self.param_control.get_parameters()
            
            self.chaos_system = QuantumChaosSystem(
                dimension=params["dimension"],
                hbar=params["hbar"],
                G=params["G"],
                decoherence_rate=params["decoherence_rate"],
                elemental_phase=params["elemental_phase"],
                sigma=params["sigma"],
                rho=params["rho"],
                beta=params["beta"]
            )
            
            self.status_label.setText("正在模拟演化...")
            QApplication.processEvents()
            
            self.chaos_system.evolve(
                dt=params["dt"],
                steps=params["steps"]
            )
            
            self.status_label.setText("正在生成可视化...")
            QApplication.processEvents()
            
            self.vis_canvas.visualize(self.chaos_system)
            
            self.status_label.setText("正在生成分析报告...")
            QApplication.processEvents()
            
            self.report_view.show_report(self.chaos_system)
            
            self.status_label.setText("模拟完成!")
        
        except Exception as e:
            self.status_label.setText(f"错误: {str(e)}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())