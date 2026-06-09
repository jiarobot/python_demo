# -*- coding: utf-8 -*-
"""
量子混沌系统与中国传统易学十二长生相结合 v2.0
- 增强的物理模型
- 完整的错误处理
- 丰富的可视化
- 数据导出功能
- 参数优化建议

Created on Sun Jun 15 09:05:48 2025
@author: DeepSeek Researcher
@version: 2.0
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from mpl_toolkits.mplot3d import Axes3D
from scipy.integrate import solve_ivp
from scipy.fft import fft, fftfreq
from scipy.stats import entropy as shannon_entropy
from tqdm import tqdm
import pandas as pd
from matplotlib.gridspec import GridSpec
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Any
import warnings
import json
import os
from datetime import datetime
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 忽略警告
warnings.filterwarnings('ignore')

# 设置中文字体
plt.rcParams['font.family'] = 'SimHei'
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['figure.dpi'] = 100
plt.rcParams['savefig.dpi'] = 300


@dataclass
class SystemConfig:
    """系统配置类"""
    dimension: int = 5
    hbar: float = 0.5
    G: float = 0.15
    alpha: float = 0.618
    decoherence_rate: float = 0.01
    elemental_phase: str = "木"
    dt: float = 0.02
    steps: int = 1000
    # Lorenz系统参数
    sigma: float = 10.0
    rho: float = 28.0
    beta: float = 8.0/3.0
    # 控制参数
    control_strength: float = 0.1
    use_control: bool = False
    # 保存路径
    save_dir: str = "./results"
    save_data: bool = True


class TwelveStages:
    """十二长生系统 - 增强版"""
    
    STAGES = ["长生", "沐浴", "冠带", "临官", "帝旺", 
              "衰", "病", "死", "墓", "绝", "胎", "养"]
    
    # 阶段描述
    STAGE_DESCRIPTIONS = {
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
    
    # 各阶段的影响系数
    STAGE_EFFECTS = {
        "长生": 1.2,    # 生长阶段 - 增强量子效应
        "沐浴": 0.9,    # 不稳定阶段 - 增加涨落
        "冠带": 1.1,    # 成长阶段 - 适度增强
        "临官": 1.3,    # 成熟阶段 - 强增强
        "帝旺": 1.5,    # 巅峰阶段 - 最强效果
        "衰": 0.95,     # 衰退阶段 - 轻微减弱
        "病": 0.8,      # 问题阶段 - 明显减弱
        "死": 0.5,      # 死亡阶段 - 大幅减弱
        "墓": 0.7,      # 隐藏阶段 - 部分恢复
        "绝": 0.6,      # 断绝阶段 - 微弱
        "胎": 1.0,      # 孕育阶段 - 恢复正常
        "养": 1.05      # 滋养阶段 - 轻微增强
    }
    
    # 涨落因子系数
    FLUCTUATION_FACTORS = {
        "长生": 1.0,
        "沐浴": 1.5,
        "冠带": 1.0,
        "临官": 1.1,
        "帝旺": 1.2,
        "衰": 0.9,
        "病": 0.7,
        "死": 0.5,
        "墓": 0.6,
        "绝": 0.4,
        "胎": 0.8,
        "养": 1.0
    }
    
    # 退相干因子系数
    DECOHERENCE_FACTORS = {
        "长生": 0.7,
        "沐浴": 1.2,
        "冠带": 1.0,
        "临官": 0.9,
        "帝旺": 0.8,
        "衰": 1.1,
        "病": 1.8,
        "死": 2.0,
        "墓": 1.3,
        "绝": 1.5,
        "胎": 0.6,
        "养": 0.8
    }
    
    # 五行对应的长生起始位置
    ELEMENTAL_PHASES = {
        "木": [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 0, 1],
        "火": [5, 6, 7, 8, 9, 10, 11, 0, 1, 2, 3, 4],
        "土": [8, 9, 10, 11, 0, 1, 2, 3, 4, 5, 6, 7],
        "金": [11, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        "水": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 0]
    }
    
    # 阶段颜色
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
    
    def __init__(self, elemental_phase: str = "木"):
        """
        初始化十二长生系统
        
        Args:
            elemental_phase: 五行属性（木、火、土、金、水）
        """
        if elemental_phase not in self.ELEMENTAL_PHASES:
            raise ValueError(f"无效的五行属性: {elemental_phase}，可选: {list(self.ELEMENTAL_PHASES.keys())}")
        
        self.elemental_phase = elemental_phase
        self.current_stage_idx = 0
        self.stage_history = []
        self.stage_timestamps = []
        self.transition_times = []
        
    def advance_stage(self, chaos_level: float, dt: float = 0.02) -> str:
        """
        根据混沌水平推进长生阶段
        
        Args:
            chaos_level: 当前混沌水平 (0-1)
            dt: 时间步长
            
        Returns:
            当前阶段名称
        """
        # 混沌水平越高，阶段变化越快
        base_rate = 0.05
        max_rate = 0.8
        transition_prob = min(max_rate, base_rate + chaos_level * 0.35)
        
        # 阶段持续时间影响转换概率
        if len(self.stage_timestamps) > 0:
            time_in_stage = self.stage_timestamps[-1] if self.stage_timestamps else 0
            if time_in_stage > 500:  # 长时间停留，增加转换概率
                transition_prob *= 1.5
        
        transition_prob *= dt / 0.02  # 归一化时间步长
        
        if np.random.rand() < transition_prob:
            self.current_stage_idx = (self.current_stage_idx + 1) % 12
            self.stage_history.append(self.current_stage_idx)
            self.transition_times.append(chaos_level)
        
        return self.current_stage()
    
    def current_stage(self) -> str:
        """获取当前阶段名称"""
        adjusted_idx = (self.current_stage_idx + 
                       self.ELEMENTAL_PHASES[self.elemental_phase][0]) % 12
        return self.STAGES[adjusted_idx]
    
    def stage_effect(self) -> float:
        """获取当前阶段对量子系统的影响系数"""
        stage = self.current_stage()
        return self.STAGE_EFFECTS[stage]
    
    def fluctuation_factor(self) -> float:
        """获取当前阶段的涨落因子"""
        stage = self.current_stage()
        return self.FLUCTUATION_FACTORS[stage]
    
    def decoherence_factor(self) -> float:
        """获取当前阶段的退相干因子"""
        stage = self.current_stage()
        return self.DECOHERENCE_FACTORS[stage]
    
    def stage_color(self, stage: str = None) -> str:
        """获取阶段对应的颜色"""
        stage = stage or self.current_stage()
        return self.STAGE_COLORS.get(stage, '#000000')
    
    def get_stage_sequence(self) -> List[str]:
        """获取五行对应的长生阶段序列"""
        return [self.STAGES[i] for i in self.ELEMENTAL_PHASES[self.elemental_phase]]
    
    def get_stage_description(self, stage: str = None) -> str:
        """获取阶段描述"""
        stage = stage or self.current_stage()
        return self.STAGE_DESCRIPTIONS.get(stage, "未知阶段")
    
    def get_stage_metrics(self) -> Dict[str, Any]:
        """获取当前阶段的综合指标"""
        stage = self.current_stage()
        return {
            'stage': stage,
            'effect': self.stage_effect(),
            'fluctuation': self.fluctuation_factor(),
            'decoherence': self.decoherence_factor(),
            'color': self.stage_color(),
            'description': self.get_stage_description(stage)
        }
    
    def reset(self):
        """重置系统状态"""
        self.current_stage_idx = 0
        self.stage_history = []
        self.stage_timestamps = []
        self.transition_times = []


class QuantumChaosSystem:
    """量子混沌系统 - 增强版"""
    
    def __init__(self, config: SystemConfig = None):
        """
        初始化量子混沌系统
        
        Args:
            config: 系统配置对象
        """
        self.config = config or SystemConfig()
        
        # 验证维度
        self.d = max(3, self.config.dimension)
        
        # 基本常数
        self.hbar = self.config.hbar
        self.G = self.config.G
        self.alpha = self.config.alpha
        self.decoherence_rate = self.config.decoherence_rate
        
        # 初始化十二长生系统
        self.twelve_stages = TwelveStages(self.config.elemental_phase)
        
        # 初始化量子态
        self._init_quantum_state()
        
        # 初始化拓扑联络场
        self.A = np.random.randn(self.d, self.d) * 0.01
        self.A = (self.A - self.A.T) / 2  # 反对称化
        
        # 混沌参数
        self.sigma = self.config.sigma
        self.rho = self.config.rho
        self.beta = self.config.beta
        
        # 历史状态存储
        self.history = []
        self.measurements = []
        
        # 李雅普诺夫指数计算
        self.lyapunov = np.zeros(self.d)
        self.trajectory = []
        self.reference = []
        
        # 拓扑荷历史
        self.topological_charge_history = []
        self.energy_history = []
        self.entropy_history = []
        
        # 混沌指标
        self.chaos_metrics = {
            'lyapunov_max': 0.0,
            'correlation_dimension': 0.0,
            'kolmogorov_entropy': 0.0
        }
        
        # 创建保存目录
        if self.config.save_data:
            os.makedirs(self.config.save_dir, exist_ok=True)
        
        logger.info(f"量子混沌系统初始化完成 - 维度:{self.d}, 五行属性:{self.config.elemental_phase}")
    
    def _init_quantum_state(self):
        """初始化量子态"""
        # 使用随机态但保证归一化
        self.psi = np.random.randn(self.d) + 1j * np.random.randn(self.d)
        self.psi /= np.linalg.norm(self.psi)
        
        # 保存初始态副本
        self.psi_initial = self.psi.copy()
    
    def lorenz_system(self, t: float, state: np.ndarray) -> np.ndarray:
        """Lorenz混沌系统方程"""
        x, y, z = state[:3]
        dxdt = self.sigma * (y - x)
        dydt = x * (self.rho - z) - y
        dzdt = x * y - self.beta * z
        
        dstate = np.zeros_like(state)
        dstate[0] = dxdt
        dstate[1] = dydt
        dstate[2] = dzdt
        
        # 更高维度的动力学（简谐振荡）
        for i in range(3, len(state)):
            freq = 0.1 * (i - 2)
            damping = 0.05
            dstate[i] = -damping * state[i] - freq**2 * state[i-3] if i-3 >= 0 else -damping * state[i]
        
        return dstate
    
    def compute_curvature(self) -> np.ndarray:
        """
        计算规范场曲率 F_{\mu\nu} = \partial_\mu A_\nu - \partial_\nu A_\mu + [A_\mu, A_\nu]
        
        Returns:
            曲率张量，形状为 (d, d, d, d)
        """
        d = self.d
        F = np.zeros((d, d, d, d), dtype=complex)
        
        # 有限差分步长
        dx = 0.1
        
        # 计算曲率
        for mu in range(d):
            for nu in range(d):
                if mu == nu:
                    continue
                
                # 偏导数项: ∂_μ A_ν
                dA_mu_nu = np.zeros((d, d), dtype=complex)
                dA_nu_mu = np.zeros((d, d), dtype=complex)
                
                # 对A的列方向求导（如果维度存在）
                if mu < 2:  # A的行索引
                    A_shifted = np.roll(self.A, -1, axis=mu)
                    dA_mu_nu = (A_shifted - self.A) / dx
                if nu < 2:  # A的行索引
                    A_shifted = np.roll(self.A, -1, axis=nu)
                    dA_nu_mu = (A_shifted - self.A) / dx
                
                # 对易子项 [A_μ, A_ν]
                commutator = np.zeros((d, d), dtype=complex)
                if mu < d and nu < d:
                    # 构造扩展的A矩阵（如果mu/nu超出2维，视为零）
                    A_mu = np.zeros((d, d), dtype=complex)
                    A_nu = np.zeros((d, d), dtype=complex)
                    
                    if mu < d:
                        A_mu[mu, :] = self.A[mu % 2, :] if mu < 2 else 0
                    if nu < d:
                        A_nu[nu, :] = self.A[nu % 2, :] if nu < 2 else 0
                    
                    commutator = A_mu @ A_nu - A_nu @ A_mu
                
                # 曲率张量
                F[mu, nu] = dA_mu_nu - dA_nu_mu + commutator
        
        # 归一化处理，避免数值过大
        max_val = np.max(np.abs(F))
        if max_val > 1e10:
            F = F / max_val * 1e10
        
        # 确保反对称性
        F = (F - F.transpose(1, 0, 2, 3)) / 2
        
        return F
    
    def quantum_fluctuation(self, dt: float):
        """量子涨落过程 - 受十二长生影响"""
        # 获取当前长生阶段的影响系数
        stage_metrics = self.twelve_stages.get_stage_metrics()
        stage_effect = stage_metrics['effect']
        fluctuation_factor = stage_metrics['fluctuation']
        
        # 涨落强度
        noise_amplitude = np.sqrt(dt * self.hbar * fluctuation_factor * stage_effect)
        
        # 加入量子噪声（保持厄米性）
        fluctuation = (np.random.randn(self.d) + 1j * np.random.randn(self.d)) * noise_amplitude
        
        # 更新波函数
        self.psi += fluctuation
        self.psi /= np.linalg.norm(self.psi)
        
        return np.linalg.norm(fluctuation)
    
    def gravitational_interaction(self, dt: float):
        """量子引力相互作用模型 - 受十二长生影响"""
        stage_metrics = self.twelve_stages.get_stage_metrics()
        stage_effect = stage_metrics['effect']
        
        # 计算质量分布（量子概率密度）
        mass_dist = np.abs(self.psi)**2
        
        # 计算引力势
        G_potential = np.zeros(self.d, dtype=complex)
        for i in range(self.d):
            for j in range(self.d):
                if i != j:
                    r = abs(i - j) + 1e-10
                    # 随距离衰减的引力势
                    G_potential[i] -= self.G * stage_effect * mass_dist[j] / r
        
        # 更新波函数（薛定谔-牛顿方程）
        self.psi = self.psi * np.exp(-1j * G_potential * dt / self.hbar)
        self.psi /= np.linalg.norm(self.psi)
    
    def decoherence_model(self, dt: float):
        """量子退相干与测量过程 - 受十二长生影响"""
        stage_metrics = self.twelve_stages.get_stage_metrics()
        stage_effect = stage_metrics['effect']
        decoherence_factor = stage_metrics['decoherence']
        
        # 退相干率
        gamma = self.decoherence_rate * stage_effect * decoherence_factor
        
        # 随机测量事件
        if np.random.rand() < gamma * dt:
            # 选择随机测量基
            basis = np.random.randn(self.d) + 1j * np.random.randn(self.d)
            basis /= np.linalg.norm(basis)
            
            # 投影测量
            proj = np.outer(basis, np.conj(basis))
            self.psi = proj @ self.psi
            self.psi /= np.linalg.norm(self.psi)
            
            # 记录测量
            self.measurements.append({
                'time': len(self.history) * dt if self.history else 0,
                'basis': basis,
                'stage': self.twelve_stages.current_stage()
            })
        
        # Lindblad主方程演化
        for i in range(self.d):
            # 投影算符作为Lindblad算符
            L = np.zeros((self.d, self.d), dtype=complex)
            L[i, i] = 1.0
            
            # Lindblad项
            L_dag = L.conj().T
            L_rho = L @ self.psi
            rho_L = self.psi @ L_dag if hasattr(self.psi, '__matmul__') else np.outer(self.psi, np.conj(self.psi)) @ L_dag
            
            # 简化演化
            dissipation = -0.5 * gamma * dt * (L_dag @ L @ self.psi)
            self.psi += dissipation
        
        self.psi /= np.linalg.norm(self.psi)
    
    def compute_topological_charge(self) -> float:
        """
        计算拓扑荷（第一陈数）
        
        Returns:
            拓扑荷数值
        """
        # 构建Berry曲率
        berry_curvature = np.zeros((self.d, self.d), dtype=complex)
        
        for i in range(self.d):
            for j in range(self.d):
                if i != j:
                    # 计算相位差
                    phase_diff = np.angle(self.psi[i] * np.conj(self.psi[j]))
                    berry_curvature[i, j] = 1j * self.A[i, j] * np.exp(1j * phase_diff)
        
        # 计算Chern数
        F = berry_curvature - berry_curvature.conj().T
        chern = np.trace(F @ F) / (2 * np.pi * 1j)
        
        return np.real(chern)
    
    def instanton_effect(self, dt: float):
        """瞬子效应模拟 - 量子隧穿"""
        stage_metrics = self.twelve_stages.get_stage_metrics()
        stage_effect = stage_metrics['effect']
        
        # 计算当前拓扑荷
        current_charge = self.compute_topological_charge()
        
        if self.topological_charge_history:
            prev_charge = self.topological_charge_history[-1]
            # 检测拓扑转变
            charge_jump = abs(current_charge - prev_charge)
            
            if charge_jump > 0.3:
                # 瞬子事件
                instanton_strength = 1.0
                
                # 胎养阶段增强瞬子效应
                current_stage = self.twelve_stages.current_stage()
                if current_stage in ["胎", "养"]:
                    instanton_strength = 2.5
                elif current_stage in ["死", "墓"]:
                    instanton_strength = 0.3
                
                # 量子隧穿
                tunneling_phase = 2 * np.pi * np.random.rand()
                tunneling = np.exp(1j * tunneling_phase * instanton_strength * stage_effect)
                self.psi *= tunneling
                self.psi /= np.linalg.norm(self.psi)
                
                logger.debug(f"瞬子事件发生 - 电荷跳跃: {charge_jump:.3f}, 阶段: {current_stage}")
        
        # 记录拓扑荷
        self.topological_charge_history.append(current_charge)
        
        return current_charge
    
    def compute_chaos_level(self, state: np.ndarray) -> float:
        """
        计算混沌水平
        
        Args:
            state: 系统状态向量
            
        Returns:
            混沌水平 (0-1)
        """
        # 基于状态范数
        norm_state = np.linalg.norm(state)
        chaos_from_norm = min(1.0, norm_state / 50.0)
        
        # 基于李雅普诺夫指数
        if len(self.lyapunov) > 0 and np.any(self.lyapunov > 0):
            lyap_chaos = min(1.0, np.max(self.lyapunov) / 2.0)
        else:
            lyap_chaos = 0.5
        
        # 基于能量的涨落
        if len(self.energy_history) > 10:
            energy_var = np.var(self.energy_history[-50:])
            energy_chaos = min(1.0, energy_var / 10.0)
        else:
            energy_chaos = 0.5
        
        # 综合混沌水平
        chaos_level = 0.4 * chaos_from_norm + 0.3 * lyap_chaos + 0.3 * energy_chaos
        
        return min(1.0, max(0.0, chaos_level))
    
    def compute_energy(self) -> float:
        """
        计算系统能量
        
        Returns:
            系统总能量
        """
        # 动能项
        kinetic = np.sum(np.abs(np.gradient(self.psi))**2) / 2
        
        # 势能项（简谐势）
        x = np.linspace(-5, 5, self.d)
        potential = 0.5 * np.sum(x**2 * np.abs(self.psi)**2)
        
        # 引力势能
        gravitational = 0
        for i in range(self.d):
            for j in range(self.d):
                if i != j:
                    r = abs(i - j) + 1e-10
                    gravitational -= self.G * np.abs(self.psi[i])**2 * np.abs(self.psi[j])**2 / r
        
        return kinetic + potential + gravitational
    
    def compute_entropy(self) -> float:
        """
        计算量子熵（冯·诺依曼熵）
        
        Returns:
            熵值
        """
        # 密度矩阵的对角元作为概率分布
        probabilities = np.abs(self.psi)**2
        probabilities = probabilities / np.sum(probabilities + 1e-10)
        
        # 香农熵
        return shannon_entropy(probabilities, base=2)
    
    def apply_pygame_control(self, state: np.ndarray, dt: float) -> np.ndarray:
        """
        应用混沌控制（反馈控制）
        
        Args:
            state: 当前状态
            dt: 时间步长
            
        Returns:
            控制后的状态
        """
        if not self.config.use_control:
            return state
        
        # 目标状态（稳定不动点）
        target = np.array([np.sqrt(self.beta * (self.rho - 1)),
                          np.sqrt(self.beta * (self.rho - 1)),
                          self.rho - 1] + [0] * (self.d - 3))
        
        # 控制力
        control_force = self.config.control_strength * (target[:self.d] - state)
        
        # 受十二长生影响的控制增益
        stage_effect = self.twelve_stages.stage_effect()
        control_force *= stage_effect
        
        # 只在前三个维度施加控制
        state[:3] += control_force[:3] * dt
        
        return state
    
    def compute_lyapunov_spectrum(self, n_steps: int = 100) -> np.ndarray:
        """
        计算李雅普诺夫谱
        
        Args:
            n_steps: 计算步数
            
        Returns:
            李雅普诺夫指数谱
        """
        # 正交化方法
        lyap = np.zeros(self.d)
        
        # 初始扰动向量
        perturbations = np.eye(self.d)
        
        state = self.trajectory[-1] if self.trajectory else np.zeros(self.d)
        
        for step in range(n_steps):
            # 演化状态和扰动
            for i in range(self.d):
                # 简化的雅可比矩阵
                J = np.eye(self.d) + 0.01 * np.random.randn(self.d, self.d)
                perturbations[:, i] = J @ perturbations[:, i]
            
            # Gram-Schmidt正交化
            for i in range(self.d):
                for j in range(i):
                    perturbations[:, i] -= np.dot(perturbations[:, i], perturbations[:, j]) * perturbations[:, j]
                
                norm = np.linalg.norm(perturbations[:, i])
                if norm > 1e-10:
                    lyap[i] += np.log(norm)
                    perturbations[:, i] /= norm
        
        return lyap / (n_steps * 0.02)
    
    def evolve(self, dt: float = None, steps: int = None) -> List[Dict]:
        """
        系统演化主函数
        
        Args:
            dt: 时间步长
            steps: 演化步数
            
        Returns:
            历史记录列表
        """
        dt = dt or self.config.dt
        steps = steps or self.config.steps
        
        # 重置历史
        self.history = []
        self.topological_charge_history = []
        self.energy_history = []
        self.entropy_history = []
        self.measurements = []
        
        # 初始状态
        state = np.real(self.psi[:self.d]).copy()
        ref_state = state.copy() + 1e-6 * np.random.randn(self.d)
        
        self.trajectory = [state.copy()]
        self.reference = [ref_state.copy()]
        
        # 李雅普诺夫指数计算变量
        lyap_exp = np.zeros((steps, self.d))
        
        # 重置十二长生
        self.twelve_stages.reset()
        
        logger.info(f"开始系统演化 - 步数:{steps}, 时间步长:{dt}")
        
        for i in tqdm(range(steps), desc="演化量子混沌系统"):
            t_span = [i*dt, (i+1)*dt]
            
            # 求解混沌动力学
            try:
                sol = solve_ivp(self.lorenz_system, t_span, state, method='RK45', rtol=1e-6)
                if sol.success:
                    state = sol.y[:, -1]
                else:
                    logger.warning(f"积分失败，使用前一步状态")
            except Exception as e:
                logger.error(f"积分错误: {e}")
                state = state  # 保持原状态
            
            # 参考轨迹演化
            try:
                sol_ref = solve_ivp(self.lorenz_system, t_span, ref_state, method='RK45', rtol=1e-6)
                if sol_ref.success:
                    ref_state = sol_ref.y[:, -1]
            except Exception:
                pass
            
            # 应用控制
            state = self.apply_pygame_control(state, dt)
            
            # 计算混沌水平
            chaos_level = self.compute_chaos_level(state)
            
            # 推进十二长生阶段
            self.twelve_stages.advance_stage(chaos_level, dt)
            current_stage = self.twelve_stages.current_stage()
            
            # 量子引力相互作用
            self.gravitational_interaction(dt)
            
            # 量子涨落
            fluctuation_magnitude = self.quantum_fluctuation(dt)
            
            # 退相干过程
            self.decoherence_model(dt)
            
            # 瞬子效应
            topological_charge = self.instanton_effect(dt)
            
            # 更新拓扑联络场（缓慢演化）
            self.A = (1 - 0.001 * dt) * self.A + 0.001 * np.random.randn(self.d, self.d) * dt
            self.A = (self.A - self.A.T) / 2  # 保持反对称
            
            # 计算能量和熵
            energy = self.compute_energy()
            entropy = self.compute_entropy()
            
            self.energy_history.append(energy)
            self.entropy_history.append(entropy)
            
            # 计算混沌指标
            if i > 0:
                delta = ref_state - state
                delta_norm = np.linalg.norm(delta)
                if delta_norm > 1e-10:
                    lyap_exp[i] = np.log(np.abs(delta) + 1e-10) / dt
                else:
                    lyap_exp[i] = lyap_exp[i-1] if i > 0 else np.zeros(self.d)
            
            # 存储历史状态
            self.history.append({
                'step': i,
                'time': (i+1)*dt,
                'state': state.copy(),
                'psi': self.psi.copy(),
                'A': self.A.copy(),
                'curvature': self.compute_curvature(),
                'topological_charge': topological_charge,
                'energy': energy,
                'entropy': entropy,
                'twelve_stages': current_stage,
                'stage_color': self.twelve_stages.stage_color(),
                'stage_effect': self.twelve_stages.stage_effect(),
                'fluctuation_magnitude': fluctuation_magnitude,
                'chaos_level': chaos_level
            })
            
            # 存储轨迹
            self.trajectory.append(state.copy())
            self.reference.append(ref_state.copy())
        
        # 计算平均李雅普诺夫指数
        if steps > 100:
            self.lyapunov = np.mean(lyap_exp[int(steps/2):], axis=0)
            self.chaos_metrics['lyapunov_max'] = float(np.max(self.lyapunov))
        
        # 计算相关维数
        self._compute_correlation_dimension()
        
        logger.info(f"演化完成 - 最终阶段:{self.twelve_stages.current_stage()}, "
                   f"最大李雅普诺夫指数:{self.chaos_metrics['lyapunov_max']:.4f}")
        
        return self.history
    
    def _compute_correlation_dimension(self):
        """计算相关维数（简化的Grassberger-Procaccia算法）"""
        if len(self.trajectory) < 100:
            return
        
        # 取后1000个点
        points = np.array(self.trajectory[-1000:])
        n_points = len(points)
        
        # 计算距离矩阵
        distances = []
        for i in range(0, n_points, 10):  # 降采样
            for j in range(i+1, n_points, 10):
                dist = np.linalg.norm(points[i] - points[j])
                distances.append(dist)
        
        distances = np.array(distances)
        
        if len(distances) > 0:
            # 相关积分
            r_values = np.logspace(-2, 1, 20)
            correlation_sum = []
            
            for r in r_values:
                c_sum = np.sum(distances < r) / (len(distances) + 1e-10)
                correlation_sum.append(c_sum)
            
            correlation_sum = np.array(correlation_sum)
            valid = correlation_sum > 0
            
            if np.sum(valid) > 5:
                # 线性拟合得到相关维数
                log_r = np.log(r_values[valid])
                log_c = np.log(correlation_sum[valid])
                
                # 简单线性回归
                slope = np.polyfit(log_r, log_c, 1)[0]
                self.chaos_metrics['correlation_dimension'] = float(slope)
        
        # Kolmogorov熵估算
        if len(self.entropy_history) > 100:
            entropy_rate = np.diff(self.entropy_history[-500:]) / 0.02
            self.chaos_metrics['kolmogorov_entropy'] = float(np.mean(np.abs(entropy_rate)))
    
    def save_data(self, filename: str = None):
        """保存演化数据到文件"""
        if not self.config.save_data:
            return
        
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"quantum_chaos_{self.config.elemental_phase}_{timestamp}"
        
        filepath = os.path.join(self.config.save_dir, filename)
        
        # 准备可序列化的数据（避免循环引用和复杂对象）
        serializable_history = []
        for h in self.history:
            # 只保存基本类型和可序列化的数据
            serializable_entry = {
                'step': int(h['step']),
                'time': float(h['time']),
                'twelve_stages': str(h['twelve_stages']),
                'stage_color': str(h['stage_color']),
                'stage_effect': float(h['stage_effect']),
                'energy': float(h['energy']),
                'entropy': float(h['entropy']),
                'topological_charge': float(h['topological_charge']),
                'chaos_level': float(h['chaos_level']),
                'fluctuation_magnitude': float(h['fluctuation_magnitude'])
            }
            
            # 处理state（numpy数组转为列表）
            if 'state' in h and h['state'] is not None:
                try:
                    if isinstance(h['state'], np.ndarray):
                        serializable_entry['state'] = h['state'].tolist()
                    else:
                        serializable_entry['state'] = list(h['state'])
                except:
                    serializable_entry['state'] = []
            
            # 处理psi（量子态，复数转为实部和虚部分开保存）
            if 'psi' in h and h['psi'] is not None:
                try:
                    if isinstance(h['psi'], np.ndarray):
                        serializable_entry['psi_real'] = np.real(h['psi']).tolist()
                        serializable_entry['psi_imag'] = np.imag(h['psi']).tolist()
                    else:
                        serializable_entry['psi_real'] = list(np.real(h['psi']))
                        serializable_entry['psi_imag'] = list(np.imag(h['psi']))
                except:
                    serializable_entry['psi_real'] = []
                    serializable_entry['psi_imag'] = []
            
            # 处理A（拓扑联络场）
            if 'A' in h and h['A'] is not None:
                try:
                    if isinstance(h['A'], np.ndarray):
                        serializable_entry['A'] = h['A'].tolist()
                    else:
                        serializable_entry['A'] = list(h['A'])
                except:
                    serializable_entry['A'] = []
            
            # curvature可能很大，跳过保存或只保存统计信息
            if 'curvature' in h:
                serializable_entry['curvature_stats'] = {
                    'mean': float(np.mean(np.abs(h['curvature']))),
                    'std': float(np.std(np.abs(h['curvature']))),
                    'max': float(np.max(np.abs(h['curvature']))),
                    'min': float(np.min(np.abs(h['curvature'])))
                }
            
            serializable_history.append(serializable_entry)
        
        # 处理measurements
        serializable_measurements = []
        for m in self.measurements:
            try:
                measurement_entry = {
                    'time': float(m.get('time', 0)),
                    'stage': str(m.get('stage', ''))
                }
                if 'basis' in m and m['basis'] is not None:
                    if isinstance(m['basis'], np.ndarray):
                        measurement_entry['basis_real'] = np.real(m['basis']).tolist()
                        measurement_entry['basis_imag'] = np.imag(m['basis']).tolist()
                serializable_measurements.append(measurement_entry)
            except:
                pass
        
        # 准备配置数据
        serializable_config = {
            'dimension': int(self.config.dimension),
            'hbar': float(self.config.hbar),
            'G': float(self.config.G),
            'alpha': float(self.config.alpha),
            'decoherence_rate': float(self.config.decoherence_rate),
            'elemental_phase': str(self.config.elemental_phase),
            'dt': float(self.config.dt),
            'steps': int(self.config.steps),
            'sigma': float(self.config.sigma),
            'rho': float(self.config.rho),
            'beta': float(self.config.beta),
            'use_control': bool(self.config.use_control),
            'control_strength': float(self.config.control_strength)
        }
        
        # 准备完整数据
        data = {
            'config': serializable_config,
            'chaos_metrics': {
                'lyapunov_max': float(self.chaos_metrics.get('lyapunov_max', 0)),
                'correlation_dimension': float(self.chaos_metrics.get('correlation_dimension', 0)),
                'kolmogorov_entropy': float(self.chaos_metrics.get('kolmogorov_entropy', 0))
            },
            'lyapunov_spectrum': self.lyapunov.tolist() if isinstance(self.lyapunov, np.ndarray) else list(self.lyapunov),
            'history': serializable_history,
            'measurements': serializable_measurements,
            'timestamp': datetime.now().isoformat(),
            'system_info': {
                'dimension': self.d,
                'total_steps': len(self.history),
                'final_stage': self.twelve_stages.current_stage(),
                'average_energy': float(np.mean([h['energy'] for h in self.history])),
                'average_entropy': float(np.mean([h['entropy'] for h in self.history])),
                'max_topological_charge': float(np.max([h['topological_charge'] for h in self.history]))
            }
        }
        
        # 保存为JSON
        json_path = f"{filepath}.json"
        try:
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.info(f"JSON数据已保存到: {json_path}")
        except Exception as e:
            logger.error(f"保存JSON失败: {e}")
            # 如果完整保存失败，保存简化版本
            try:
                simple_data = {
                    'config': serializable_config,
                    'chaos_metrics': data['chaos_metrics'],
                    'timestamp': data['timestamp'],
                    'system_info': data['system_info']
                }
                with open(f"{filepath}_simple.json", 'w', encoding='utf-8') as f:
                    json.dump(simple_data, f, indent=2, ensure_ascii=False)
                logger.info(f"简化版JSON数据已保存到: {filepath}_simple.json")
            except Exception as e2:
                logger.error(f"保存简化版JSON也失败: {e2}")
        
        # 保存为CSV（简化版，更可靠）
        try:
            df_data = []
            for h in self.history:
                df_data.append({
                    'step': h['step'],
                    'time': h['time'],
                    'stage': h['twelve_stages'],
                    'energy': h['energy'],
                    'entropy': h['entropy'],
                    'topological_charge': h['topological_charge'],
                    'chaos_level': h['chaos_level'],
                    'stage_effect': h['stage_effect']
                })
            
            df = pd.DataFrame(df_data)
            csv_path = f"{filepath}.csv"
            df.to_csv(csv_path, index=False, encoding='utf-8-sig')
            logger.info(f"CSV数据已保存到: {csv_path}")
        except Exception as e:
            logger.error(f"保存CSV失败: {e}")
        
        # 保存numpy格式（完整数据备份）
        try:
            npz_path = f"{filepath}.npz"
            
            # 提取数组数据
            states = np.array([h['state'] for h in self.history]) if self.history else np.array([])
            energies = np.array([h['energy'] for h in self.history])
            entropies = np.array([h['entropy'] for h in self.history])
            charges = np.array([h['topological_charge'] for h in self.history])
            chaos_levels = np.array([h['chaos_level'] for h in self.history])
            stages = np.array([h['twelve_stages'] for h in self.history])
            
            np.savez(npz_path,
                    states=states,
                    energies=energies,
                    entropies=entropies,
                    charges=charges,
                    chaos_levels=chaos_levels,
                    stages=stages,
                    lyapunov=self.lyapunov,
                    config_dimension=self.config.dimension,
                    config_elemental_phase=self.config.elemental_phase)
            
            logger.info(f"NPZ数据已保存到: {npz_path}")
        except Exception as e:
            logger.error(f"保存NPZ失败: {e}")
        
        return filepath
    
    def generate_full_report(self) -> pd.DataFrame:
        """生成完整分析报告"""
        if not self.history:
            logger.warning("请先运行演化!")
            return pd.DataFrame()
        
        # 按阶段分组分析
        stages = [h['twelve_stages'] for h in self.history]
        unique_stages = self.twelve_stages.get_stage_sequence()
        
        stage_stats = []
        for stage in unique_stages:
            indices = [i for i, s in enumerate(stages) if s == stage]
            if indices:
                stage_data = [self.history[i] for i in indices]
                
                stats = {
                    '阶段': stage,
                    '描述': self.twelve_stages.get_stage_description(stage),
                    '出现次数': len(indices),
                    '占比(%)': len(indices) / len(self.history) * 100,
                    '平均能量': np.mean([d['energy'] for d in stage_data]),
                    '能量标准差': np.std([d['energy'] for d in stage_data]),
                    '平均熵': np.mean([d['entropy'] for d in stage_data]),
                    '平均拓扑荷': np.mean([d['topological_charge'] for d in stage_data]),
                    '平均混沌水平': np.mean([d['chaos_level'] for d in stage_data]),
                    '平均阶段效应': np.mean([d['stage_effect'] for d in stage_data])
                }
                stage_stats.append(stats)
        
        df = pd.DataFrame(stage_stats)
        
        # 添加五行生克分析
        elemental_relations = self._analyze_elemental_relations()
        
        return df, elemental_relations
    
    def _analyze_elemental_relations(self) -> Dict:
        """分析五行生克关系"""
        elements = ["木", "火", "土", "金", "水"]
        current = self.config.elemental_phase
        
        # 生克关系矩阵
        generating = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}
        controlling = {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}
        
        return {
            'current_element': current,
            'generates': generating.get(current, ''),
            'controlled_by': controlling.get(current, ''),
            'controls': [k for k, v in controlling.items() if v == current][0] if current in controlling.values() else '',
            'description': self._get_elemental_description(current)
        }
    
    def _get_elemental_description(self, element: str) -> str:
        """获取五行描述"""
        descriptions = {
            "木": "木属性系统在长生阶段表现最佳，混沌能量强且持久，适合生长型系统",
            "火": "火属性系统在帝旺阶段能量最强，但波动大，适合爆发型系统",
            "土": "土属性系统整体稳定，各阶段过渡平稳，适合稳定型系统",
            "金": "金属性系统在临官阶段表现突出，混沌与量子平衡性好，适合精密控制",
            "水": "水属性系统恢复能力强，在绝胎阶段能快速重建，适合自适应系统"
        }
        return descriptions.get(element, "未知")


class QuantumChaosVisualizer:
    """量子混沌系统可视化器"""
    
    def __init__(self, system: QuantumChaosSystem):
        self.system = system
        self.config = system.config
    
    def create_advanced_visualization(self, save_path: str = None):
        """创建高级可视化仪表板"""
        if not self.system.history:
            logger.warning("请先运行演化!")
            return
        
        fig = plt.figure(figsize=(20, 12), facecolor='#f5f5f5')
        fig.suptitle(f'量子混沌系统与十二长生演化分析 v2.0\n'
                    f'五行属性: {self.system.config.elemental_phase} | '
                    f'维度: {self.system.d} | '
                    f'最大李雅普诺夫指数: {self.system.chaos_metrics["lyapunov_max"]:.4f}',
                    fontsize=16, color='darkblue', y=0.98)
        
        # 创建网格布局
        gs = GridSpec(3, 3, figure=fig, hspace=0.3, wspace=0.3)
        
        # 1. 阶段分布饼图
        ax1 = fig.add_subplot(gs[0, 0])
        self._plot_stage_distribution(ax1)
        
        # 2. 阶段时间序列
        ax2 = fig.add_subplot(gs[0, 1])
        self._plot_stage_timeline(ax2)
        
        # 3. 混沌轨迹3D
        ax3 = fig.add_subplot(gs[0, 2], projection='3d')
        self._plot_chaos_trajectory_3d(ax3)
        
        # 4. 能量演化
        ax4 = fig.add_subplot(gs[1, 0])
        self._plot_energy_evolution(ax4)
        
        # 5. 拓扑荷演化
        ax5 = fig.add_subplot(gs[1, 1])
        self._plot_topological_charge(ax5)
        
        # 6. 混沌指标
        ax6 = fig.add_subplot(gs[1, 2])
        self._plot_chaos_metrics(ax6)
        
        # 7. 阶段与系统指标关系
        ax7 = fig.add_subplot(gs[2, 0])
        self._plot_stage_metrics(ax7)
        
        # 8. 量子熵热图
        ax8 = fig.add_subplot(gs[2, 1])
        self._plot_entropy_heatmap(ax8)
        
        # 9. 五行生克图
        ax9 = fig.add_subplot(gs[2, 2])
        self._plot_elemental_relations(ax9)
        
        # 保存图像
        if save_path or self.system.config.save_data:
            if save_path is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                save_path = os.path.join(self.system.config.save_dir, 
                                        f"visualization_{timestamp}.png")
            plt.savefig(save_path, dpi=300, bbox_inches='tight', facecolor='white')
            logger.info(f"可视化已保存到: {save_path}")
        
        plt.show()
    
    def _plot_stage_distribution(self, ax):
        """绘制阶段分布"""
        stages = [h['twelve_stages'] for h in self.system.history]
        unique_stages = self.system.twelve_stages.get_stage_sequence()
        stage_counts = [stages.count(stage) for stage in unique_stages]
        colors = [self.system.twelve_stages.stage_color(stage) for stage in unique_stages]
        
        wedges, texts, autotexts = ax.pie(stage_counts, labels=unique_stages, 
                                          colors=colors, autopct='%1.1f%%',
                                          startangle=90)
        ax.set_title('十二长生阶段分布', fontsize=12, fontweight='bold')
        
        # 美化文字
        for text in texts:
            text.set_fontsize(8)
        for autotext in autotexts:
            autotext.set_fontsize(8)
            autotext.set_color('white')
            autotext.set_fontweight('bold')
    
    def _plot_stage_timeline(self, ax):
        """绘制阶段时间序列"""
        stages = [h['twelve_stages'] for h in self.system.history]
        times = [h['time'] for h in self.system.history]
        unique_stages = self.system.twelve_stages.get_stage_sequence()
        
        stage_to_idx = {stage: i for i, stage in enumerate(unique_stages)}
        stage_indices = [stage_to_idx[s] for s in stages]
        
        # 使用彩色散点
        colors = [self.system.twelve_stages.stage_color(s) for s in stages]
        ax.scatter(times, stage_indices, c=colors, s=10, alpha=0.6, edgecolors='none')
        
        ax.set_yticks(range(len(unique_stages)))
        ax.set_yticklabels(unique_stages, fontsize=9)
        ax.set_xlabel('时间', fontsize=10)
        ax.set_ylabel('长生阶段', fontsize=10)
        ax.set_title('长生阶段演化时间线', fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3, linestyle='--')
    
    def _plot_chaos_trajectory_3d(self, ax):
        """绘制3D混沌轨迹"""
        states = np.array([h['state'][:3] for h in self.system.history])
        colors = [h['stage_color'] for h in self.system.history]
        
        # 降采样以提高性能
        step = max(1, len(states) // 2000)
        states_sampled = states[::step]
        colors_sampled = colors[::step]
        
        # 分段着色绘制
        for i in range(1, len(states_sampled)):
            ax.plot(states_sampled[i-1:i+1, 0], 
                   states_sampled[i-1:i+1, 1], 
                   states_sampled[i-1:i+1, 2],
                   color=colors_sampled[i], alpha=0.7, linewidth=0.8)
        
        ax.set_xlabel('X', fontsize=9)
        ax.set_ylabel('Y', fontsize=9)
        ax.set_zlabel('Z', fontsize=9)
        ax.set_title('混沌轨迹（按阶段着色）', fontsize=12, fontweight='bold')
        
        # 添加颜色条
        import matplotlib.patches as mpatches
        unique_stages = self.system.twelve_stages.get_stage_sequence()
        patches = [mpatches.Patch(color=self.system.twelve_stages.stage_color(s), 
                                 label=s, alpha=0.7) for s in unique_stages[:5]]
        ax.legend(handles=patches, loc='upper right', fontsize=6, ncol=1)
    
    def _plot_energy_evolution(self, ax):
        """绘制能量演化"""
        times = [h['time'] for h in self.system.history]
        energies = [h['energy'] for h in self.system.history]
        stages = [h['twelve_stages'] for h in self.system.history]
        
        ax.plot(times, energies, 'b-', alpha=0.6, linewidth=0.8, label='系统能量')
        
        # 标注阶段变化点
        prev_stage = stages[0]
        change_times = []
        for i, stage in enumerate(stages):
            if stage != prev_stage:
                change_times.append(times[i])
                prev_stage = stage
        
        for ct in change_times:
            ax.axvline(x=ct, color='r', linestyle='--', alpha=0.3, linewidth=0.5)
        
        # 移动平均平滑
        window = min(50, len(energies))
        if window > 0:
            ma = np.convolve(energies, np.ones(window)/window, mode='valid')
            ma_times = times[window-1:]
            ax.plot(ma_times, ma, 'r-', linewidth=1.5, label=f'移动平均({window})')
        
        ax.set_xlabel('时间', fontsize=10)
        ax.set_ylabel('系统能量', fontsize=10)
        ax.set_title('能量演化', fontsize=12, fontweight='bold')
        ax.legend(loc='upper right', fontsize=8)
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.set_yscale('log')
    
    def _plot_topological_charge(self, ax):
        """绘制拓扑荷演化"""
        times = [h['time'] for h in self.system.history]
        charges = [h['topological_charge'] for h in self.system.history]
        
        ax.plot(times, charges, 'g-', linewidth=1, alpha=0.7, label='拓扑荷')
        ax.fill_between(times, charges, alpha=0.3, color='green')
        
        # 添加零线
        ax.axhline(y=0, color='k', linestyle='-', alpha=0.3, linewidth=0.5)
        
        ax.set_xlabel('时间', fontsize=10)
        ax.set_ylabel('拓扑荷', fontsize=10)
        ax.set_title('拓扑荷演化（陈数）', fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3, linestyle='--')
    
    def _plot_chaos_metrics(self, ax):
        """绘制混沌指标"""
        metrics = self.system.chaos_metrics
        
        names = ['最大李雅普诺夫指数', '相关维数', 'Kolmogorov熵']
        values = [metrics['lyapunov_max'], 
                 metrics.get('correlation_dimension', 0),
                 metrics.get('kolmogorov_entropy', 0)]
        
        colors = ['#d62728', '#2ca02c', '#9467bd']
        bars = ax.bar(names, values, color=colors, alpha=0.7, edgecolor='black')
        
        # 添加数值标签
        for bar, val in zip(bars, values):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01,
                   f'{val:.3f}', ha='center', va='bottom', fontsize=9)
        
        ax.set_ylabel('数值', fontsize=10)
        ax.set_title('混沌指标', fontsize=12, fontweight='bold')
        ax.set_xticklabels(names, rotation=15, ha='right', fontsize=8)
        ax.grid(True, alpha=0.3, axis='y', linestyle='--')
    
    def _plot_stage_metrics(self, ax):
        """绘制各阶段平均指标"""
        df, _ = self.system.generate_full_report()
        if df.empty:
            ax.text(0.5, 0.5, '无数据', ha='center', va='center', transform=ax.transAxes)
            return
        
        stages = df['阶段'].tolist()
        energies = df['平均能量'].tolist()
        entropies = df['平均熵'].tolist()
        
        x = np.arange(len(stages))
        width = 0.35
        
        bars1 = ax.bar(x - width/2, energies, width, label='平均能量', color='#ff7f0e', alpha=0.7)
        bars2 = ax.bar(x + width/2, entropies, width, label='平均熵', color='#1f77b4', alpha=0.7)
        
        ax.set_xlabel('长生阶段', fontsize=10)
        ax.set_ylabel('平均值', fontsize=10)
        ax.set_title('各阶段系统指标', fontsize=12, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(stages, rotation=45, ha='right', fontsize=8)
        ax.legend(loc='upper right', fontsize=8)
        ax.grid(True, alpha=0.3, axis='y', linestyle='--')
    
    def _plot_entropy_heatmap(self, ax):
        """绘制量子熵热图"""
        # 构建时间-阶段矩阵
        times = [h['time'] for h in self.system.history]
        stages = [h['twelve_stages'] for h in self.system.history]
        entropies = [h['entropy'] for h in self.system.history]
        
        unique_stages = self.system.twelve_stages.get_stage_sequence()
        stage_to_idx = {stage: i for i, stage in enumerate(unique_stages)}
        
        # 创建网格数据
        n_time_bins = min(100, len(times))
        time_bins = np.linspace(min(times), max(times), n_time_bins)
        
        heatmap_data = np.zeros((len(unique_stages), n_time_bins - 1))
        
        for i in range(len(time_bins) - 1):
            mask = (times >= time_bins[i]) & (times < time_bins[i+1])
            if np.any(mask):
                for stage in unique_stages:
                    stage_mask = mask & (np.array(stages) == stage)
                    if np.any(stage_mask):
                        idx = stage_to_idx[stage]
                        heatmap_data[idx, i] = np.mean(np.array(entropies)[stage_mask])
        
        # 绘制热图
        im = ax.imshow(heatmap_data, aspect='auto', cmap='viridis', 
                      extent=[time_bins[0], time_bins[-1], -0.5, len(unique_stages)-0.5],
                      origin='lower')
        
        ax.set_yticks(range(len(unique_stages)))
        ax.set_yticklabels(unique_stages, fontsize=8)
        ax.set_xlabel('时间', fontsize=10)
        ax.set_ylabel('长生阶段', fontsize=10)
        ax.set_title('量子熵演化热图', fontsize=12, fontweight='bold')
        
        # 添加颜色条
        plt.colorbar(im, ax=ax, label='量子熵', fraction=0.05)
    
    def _plot_elemental_relations(self, ax):
        """绘制五行生克关系图"""
        elements = ["木", "火", "土", "金", "水"]
        current = self.system.config.elemental_phase
        current_idx = elements.index(current)
        
        # 生克关系强度
        relations = np.array([
            [0, 1, -0.5, -0.5, 1],   # 木
            [1, 0, 1, -0.5, -0.5],    # 火
            [-0.5, 1, 0, 1, -0.5],    # 土
            [-0.5, -0.5, 1, 0, 1],    # 金
            [1, -0.5, -0.5, 1, 0]     # 水
        ])
        
        # 极坐标图
        angles = np.linspace(0, 2*np.pi, len(elements), endpoint=False)
        
        # 绘制径向图
        for i, elem in enumerate(elements):
            relation = relations[current_idx, i]
            color = 'red' if relation > 0 else 'blue' if relation < 0 else 'gray'
            radius = abs(relation) + 0.2
            ax.plot([angles[i], angles[i]], [0, radius], color=color, linewidth=2, alpha=0.7)
            ax.plot(angles[i], radius, 'o', color=color, markersize=10)
            
            # 添加标签
            ax.annotate(elem, (angles[i], radius + 0.15), ha='center', va='center', fontsize=10, fontweight='bold')
            
            # 添加生克符号
            if relation > 0:
                ax.annotate('生', (angles[i], radius/2), ha='center', va='center', fontsize=8, color='white', fontweight='bold')
            elif relation < 0:
                ax.annotate('克', (angles[i], radius/2), ha='center', va='center', fontsize=8, color='white', fontweight='bold')
        
        # 绘制参考圆
        theta = np.linspace(0, 2*np.pi, 100)
        ax.plot(np.cos(theta), np.sin(theta), 'k--', alpha=0.3, linewidth=0.5)
        ax.plot(1.5*np.cos(theta), 1.5*np.sin(theta), 'k--', alpha=0.3, linewidth=0.5)
        
        ax.set_xlim(-1.8, 1.8)
        ax.set_ylim(-1.8, 1.8)
        ax.set_aspect('equal')
        ax.set_title(f'五行生克关系图\n(中心: {current})', fontsize=12, fontweight='bold')
        ax.axis('off')
    
    def create_animation(self, filename: str = None, interval: int = 50, save: bool = True):
        """创建动态演化动画"""
        if not self.system.history:
            logger.warning("请先运行演化!")
            return
        
        fig = plt.figure(figsize=(14, 8), facecolor='black')
        fig.suptitle('量子混沌系统动态演化', fontsize=14, color='white')
        
        # 创建子图
        ax1 = fig.add_subplot(2, 2, 1, projection='3d')
        ax2 = fig.add_subplot(2, 2, 2)
        ax3 = fig.add_subplot(2, 2, 3)
        ax4 = fig.add_subplot(2, 2, 4)
        
        ax2.set_xlim(0, max([h['time'] for h in self.system.history]))
        ax2.set_ylim(0, max([h['energy'] for h in self.system.history]) * 1.1)
        ax3.set_ylim(-2, 2)
        ax4.set_ylim(0, 1.5)
        
        # 初始化绘图对象
        line1, = ax2.plot([], [], 'g-', linewidth=1, alpha=0.7)
        line2, = ax3.plot([], [], 'b-', linewidth=1)
        line3, = ax4.plot([], [], 'r-', linewidth=1)
        
        scatter = ax1.scatter([], [], [], c=[], cmap='rainbow', s=10)
        
        # 文本显示
        time_text = ax2.text(0.02, 0.95, '', transform=ax2.transAxes, color='white', fontsize=10)
        stage_text = ax2.text(0.02, 0.90, '', transform=ax2.transAxes, color='white', fontsize=10)
        
        def init():
            line1.set_data([], [])
            line2.set_data([], [])
            line3.set_data([], [])
            scatter._offsets3d = ([], [], [])
            time_text.set_text('')
            stage_text.set_text('')
            return line1, line2, line3, scatter, time_text, stage_text
        
        def update(frame):
            # 获取前frame个数据点
            data = self.system.history[:frame+1]
            times = [d['time'] for d in data]
            
            # 更新能量曲线
            energies = [d['energy'] for d in data]
            line1.set_data(times, energies)
            
            # 更新拓扑荷曲线
            charges = [d['topological_charge'] for d in data]
            line2.set_data(times, charges)
            
            # 更新混沌水平
            chaos_levels = [d['chaos_level'] for d in data]
            line3.set_data(times, chaos_levels)
            
            # 更新3D轨迹
            states = np.array([d['state'][:3] for d in data])
            if len(states) > 0:
                scatter._offsets3d = (states[:, 0], states[:, 1], states[:, 2])
                
                # 根据阶段设置颜色
                colors = [self.system.twelve_stages.stage_color(d['twelve_stages']) 
                         for d in data]
                scatter.set_color(colors)
            
            # 更新文本
            current_data = self.system.history[frame]
            time_text.set_text(f'时间: {current_data["time"]:.2f}')
            stage_text.set_text(f'阶段: {current_data["twelve_stages"]}')
            
            # 更新标题
            fig.suptitle(f'量子混沌系统动态演化 - 当前: {current_data["twelve_stages"]}', 
                        fontsize=14, color='white')
            
            # 自动调整坐标轴
            if frame > 10:
                ax2.set_xlim(0, times[-1])
                ax4.set_xlim(0, times[-1])
                ax3.set_xlim(0, times[-1])
            
            return line1, line2, line3, scatter, time_text, stage_text
        
        # 创建动画
        anim = FuncAnimation(fig, update, frames=len(self.system.history),
                            init_func=init, interval=interval, blit=False, repeat=False)
        
        if save and self.system.config.save_data:
            if filename is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = os.path.join(self.system.config.save_dir, 
                                       f"animation_{timestamp}.gif")
            
            anim.save(filename, writer='pillow', fps=20)
            logger.info(f"动画已保存到: {filename}")
        
        plt.close()
        return anim


def main():
    """主函数"""
    print("="*80)
    print("量子混沌系统与中国传统易学十二长生相结合 v2.0")
    print("="*80)
    print("\n功能特性:")
    print("  ✓ 十二长生阶段演化")
    print("  ✓ 量子引力相互作用")
    print("  ✓ 拓扑荷计算与瞬子效应")
    print("  ✓ 混沌指标分析（李雅普诺夫指数、相关维数等）")
    print("  ✓ 高级可视化仪表板")
    print("  ✓ 动态演化动画")
    print("  ✓ 数据导出（JSON/CSV）")
    print("="*80)
    
    # 选择五行属性
    elemental_phases = ["木", "火", "土", "金", "水"]
    print(f"\n可用五行属性: {elemental_phases}")
    
    while True:
        selected_phase = input("请选择五行属性 (默认:木): ").strip()
        if not selected_phase:
            selected_phase = "木"
            break
        if selected_phase in elemental_phases:
            break
        print(f"无效选择，请从 {elemental_phases} 中选择")
    
    # 配置系统
    print("\n配置系统参数...")
    config = SystemConfig(
        dimension=5,
        hbar=0.5,
        G=0.15,
        decoherence_rate=0.01,
        elemental_phase=selected_phase,
        dt=0.02,
        steps=1000,
        use_control=False,
        save_data=True,
        save_dir="./results"
    )
    
    # 初始化系统
    print(f"\n初始化{selected_phase}属性量子混沌系统...")
    chaos_system = QuantumChaosSystem(config)
    
    # 运行演化
    print("\n开始系统演化...")
    history = chaos_system.evolve()
    
    # 创建可视化器
    visualizer = QuantumChaosVisualizer(chaos_system)
    
    # 生成报告
    print("\n生成分析报告...")
    df_report, elemental_relations = chaos_system.generate_full_report()
    
    print("\n" + "="*80)
    print("十二长生阶段分析报告")
    print("="*80)
    print(df_report.to_string(index=False))
    
    print("\n" + "="*80)
    print("五行生克关系分析")
    print("="*80)
    print(f"当前五行属性: {elemental_relations['current_element']}")
    print(f"生: {elemental_relations['current_element']} → {elemental_relations['generates']}")
    print(f"克: {elemental_relations['current_element']} → {elemental_relations['controls']}")
    print(f"被克: {elemental_relations['controlled_by']} → {elemental_relations['current_element']}")
    print(f"说明: {elemental_relations['description']}")
    
    # 混沌指标
    print("\n" + "="*80)
    print("混沌指标分析")
    print("="*80)
    print(f"最大李雅普诺夫指数: {chaos_system.chaos_metrics['lyapunov_max']:.6f}")
    print(f"相关维数: {chaos_system.chaos_metrics.get('correlation_dimension', 0):.6f}")
    print(f"Kolmogorov熵: {chaos_system.chaos_metrics.get('kolmogorov_entropy', 0):.6f}")
    
    # 可视化
    print("\n生成高级可视化仪表板...")
    visualizer.create_advanced_visualization()
    
    # 询问是否生成动画
    create_anim = input("\n是否生成动态演化动画？(y/n，默认:n): ").strip().lower()
    if create_anim == 'y':
        print("生成动画中（可能需要一些时间）...")
        visualizer.create_animation(save=True)
    
    # 保存数据
    if config.save_data:
        print("\n保存数据...")
        chaos_system.save_data()
    
    # 系统优化建议
    print("\n" + "="*80)
    print("系统优化建议")
    print("="*80)
    
    suggestions = {
        "木": "建议增加初始维度至6，在冠带阶段施加控制以延长帝旺期",
        "火": "建议在沐浴阶段降低退相干率，在帝旺阶段增加引力耦合",
        "土": "建议保持当前参数，重点关注临官到帝旺的过渡优化",
        "金": "建议在胎养阶段增加量子涨落，促进系统新生",
        "水": "建议在死墓阶段引入外部扰动，加速进入胎养阶段"
    }
    
    print(suggestions.get(selected_phase, "保持当前参数，根据混沌指标调整"))
    
    # 根据混沌指标给出建议
    if chaos_system.chaos_metrics['lyapunov_max'] > 1.0:
        print("\n⚠ 混沌水平较高，建议增加控制强度或降低退相干率")
    elif chaos_system.chaos_metrics['lyapunov_max'] < 0.1:
        print("\n✓ 系统趋于稳定，可适当增加混沌激励")
    
    print("\n" + "="*80)
    print("模拟完成！")
    print(f"结果已保存到: {config.save_dir}")
    print("="*80)


if __name__ == "__main__":
    main()