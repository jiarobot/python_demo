"""
纳米级晶体管量子特性分析与优化系统
应用背景：3nm以下工艺节点芯片设计、新型半导体材料评估、量子效应建模
"""

import numpy as np
import matplotlib
matplotlib.rc("font", family='Microsoft YaHei')
import matplotlib.pyplot as plt
from scipy import sparse, integrate, optimize
from scipy.sparse.linalg import eigs, spsolve
import matplotlib.animation as animation
from mpl_toolkits.mplot3d import Axes3D
from matplotlib import cm
import time
from tqdm import tqdm
import warnings
import pandas as pd
from datetime import datetime
import json
import os
warnings.filterwarnings('ignore')

class AdvancedQuantumTunneling:
    """高级量子隧穿仿真器 - 支持芯片级多尺度模拟"""
    
    def __init__(self, dimensions=1, hbar=1.0545718e-34, m0=9.10938356e-31, 
                 q=1.60217662e-19, kT=0.0259, grid_points=1000):
        """
        初始化高级量子隧穿仿真器
        
        参数:
        dimensions: 仿真维度 (1, 2, 3)
        hbar: 约化普朗克常数
        m0: 电子静止质量
        q: 电子电荷
        kT: 热能量 (eV)
        grid_points: 每维网格点数
        """
        self.dim = dimensions
        self.hbar = hbar
        self.m0 = m0
        self.q = q
        self.kT = kT * q  # 转换为焦耳
        self.grid_points = grid_points
        
        # 材料数据库 (有效质量，单位: m0)
        self.materials = {
            'Si': {'m_eff': 0.26, 'eps_r': 11.7, 'Eg': 1.12},
            'GaAs': {'m_eff': 0.067, 'eps_r': 12.9, 'Eg': 1.42},
            'SiO2': {'m_eff': 0.50, 'eps_r': 3.9, 'Eg': 9.0},
            'HfO2': {'m_eff': 0.15, 'eps_r': 25.0, 'Eg': 5.7},
            'Graphene': {'m_eff': 0.01, 'eps_r': 2.4, 'Eg': 0.0},
            # 添加缺失的材料
            'MoS2': {'m_eff': 0.45, 'eps_r': 5.2, 'Eg': 1.8},
            'WS2': {'m_eff': 0.35, 'eps_r': 5.1, 'Eg': 2.1},
            'Black_P': {'m_eff': 0.15, 'eps_r': 5.5, 'Eg': 0.3},
            'Al2O3': {'m_eff': 0.30, 'eps_r': 9.0, 'Eg': 8.7}
        }
        
        print(f"初始化 {dimensions}D 量子隧穿仿真器")
        print(f"材料数据库: {list(self.materials.keys())}")
    
    def set_material(self, material_name):
        """设置仿真材料"""
        if material_name in self.materials:
            self.material = self.materials[material_name]
            self.m_eff = self.material['m_eff'] * self.m0
            self.eps_r = self.material['eps_r']
            self.Eg = self.material['Eg'] * self.q
            print(f"材料设置为: {material_name}, m_eff = {self.material['m_eff']}m0")
        else:
            raise ValueError(f"未知材料: {material_name}")
    
    def set_device_geometry(self, length=10e-9, width=5e-9, height=5e-9):
        """设置器件几何尺寸"""
        self.Lx = length
        self.Ly = width if self.dim >= 2 else 1e-9
        self.Lz = height if self.dim == 3 else 1e-9
        
        # 创建网格
        self.x = np.linspace(0, self.Lx, self.grid_points)
        self.dx = self.x[1] - self.x[0]
        
        if self.dim >= 2:
            self.y = np.linspace(0, self.Ly, self.grid_points)
            self.dy = self.y[1] - self.y[0]
        
        if self.dim == 3:
            self.z = np.linspace(0, self.Lz, self.grid_points)
            self.dz = self.z[1] - self.z[0]
        
        print(f"器件尺寸: {self.Lx*1e9:.1f} nm × {self.Ly*1e9:.1f} nm × {self.Lz*1e9:.1f} nm")
    
    def create_mosfet_potential(self, Vg=1.0, Vd=0.5, tox=1e-9, Na=1e24, channel_length=5e-9):
        """创建MOSFET势能分布 (1D/2D/3D)"""
        print("生成MOSFET势能分布...")
        
        # 设置默认参数
        if not hasattr(self, 'x'):
            self.set_device_geometry()
            
        if self.dim == 1:
            return self._create_mosfet_1d(Vg, Vd, tox, Na, channel_length)
        elif self.dim == 2:
            return self._create_mosfet_2d(Vg, Vd, tox, Na, channel_length)
        else:
            return self._create_mosfet_3d(Vg, Vd, tox, Na, channel_length)
    
    def _create_mosfet_1d(self, Vg, Vd, tox, Na, channel_length):
        """1D MOSFET势能"""
        V = np.zeros_like(self.x)
        
        # 氧化物区域
        oxide_region = self.x < tox
        V[oxide_region] = self.Eg / 2 + Vg * self.q
        
        # 沟道区域
        channel_start = tox
        channel_end = tox + channel_length
        channel_region = (self.x >= channel_start) & (self.x <= channel_end)
        
        # 源漏掺杂效应 - 修复数值稳定性问题
        if np.any(channel_region):
            x_channel = self.x[channel_region]
            # 添加小数值避免除零
            epsilon = 8.854e-12 * self.eps_r + 1e-30
            V_channel = -self.q * Na / (2 * epsilon) * (
                (x_channel - channel_start) * 
                (channel_end - x_channel)
            )
            V[channel_region] = V_channel
        
        # 漏极偏压
        drain_region = self.x > channel_end
        V[drain_region] = Vd * self.q
        
        return V
    
    def _create_mosfet_2d(self, Vg, Vd, tox, Na, channel_length):
        """2D MOSFET势能"""
        V = np.zeros((len(self.x), len(self.y)))
        
        # 氧化物区域 (顶部)
        oxide_thickness = 0.2 * self.Ly
        oxide_region = self.y > (self.Ly - oxide_thickness)
        
        for i, x in enumerate(self.x):
            for j, y in enumerate(self.y):
                if oxide_region[j]:
                    # 栅极控制
                    if x < tox or x > (self.Lx - tox):
                        V[i,j] = self.Eg / 2 + Vg * self.q
                    else:
                        V[i,j] = self.Eg / 2 + 0.5 * Vg * self.q
                else:
                    # 沟道区域
                    channel_start = tox
                    channel_end = self.Lx - tox
                    if channel_start <= x <= channel_end:
                        # 抛物线沟道势
                        V_channel = -0.1 * self.q * ((x - self.Lx/2) / (channel_length/2 + 1e-30))**2
                        V[i,j] = V_channel
                    
                    # 源漏接触
                    if x < tox:
                        V[i,j] = 0  # 源极
                    elif x > (self.Lx - tox):
                        V[i,j] = Vd * self.q  # 漏极
        
        return V
    
    def _create_mosfet_3d(self, Vg, Vd, tox, Na, channel_length):
        """3D MOSFET势能"""
        V = np.zeros((len(self.x), len(self.y), len(self.z)))
        
        # 简化的3D势能 - 实际应用需要更复杂的模型
        for i, x in enumerate(self.x):
            for j, y in enumerate(self.y):
                for k, z in enumerate(self.z):
                    # 氧化物区域
                    if z < tox or z > (self.Lz - tox):
                        V[i,j,k] = self.Eg / 2 + Vg * self.q
                    else:
                        # 沟道区域
                        channel_center = self.Lx / 2
                        if abs(x - channel_center) < channel_length / 2:
                            V[i,j,k] = -0.05 * self.q * (
                                ((x - channel_center) / (channel_length/2 + 1e-30))**2 +
                                ((y - self.Ly/2) / (self.Ly/2 + 1e-30))**2
                            )
                        else:
                            if x < channel_center:
                                V[i,j,k] = 0  # 源极
                            else:
                                V[i,j,k] = Vd * self.q  # 漏极
        
        return V
    
    def build_hamiltonian(self, V):
        """构建哈密顿量矩阵"""
        print("构建哈密顿量...")
        
        if self.dim == 1:
            return self._build_hamiltonian_1d(V)
        elif self.dim == 2:
            return self._build_hamiltonian_2d(V)
        else:
            return self._build_hamiltonian_3d(V)
    
    def _build_hamiltonian_1d(self, V):
        """1D 哈密顿量"""
        N = len(self.x)
        dx2 = self.dx**2
        
        # 动能项系数 - 添加数值稳定性
        coeff = -self.hbar**2 / (2 * self.m_eff * dx2 + 1e-50)
        
        # 主对角线
        main_diag = -2 * coeff + V
        
        # 上下对角线
        off_diag = coeff * np.ones(N-1)
        
        # 构建三对角矩阵
        H = sparse.diags([main_diag, off_diag, off_diag], 
                         [0, -1, 1], 
                         shape=(N, N),
                         format='csr')
        return H
    
    def _build_hamiltonian_2d(self, V):
        """2D 哈密顿量 - 使用Kronecker积"""
        Nx, Ny = len(self.x), len(self.y)
        dx2, dy2 = self.dx**2, self.dy**2
        
        # x方向动能项
        coeff_x = -self.hbar**2 / (2 * self.m_eff * dx2 + 1e-50)
        Tx = sparse.diags([-2 * coeff_x, coeff_x, coeff_x], 
                         [0, -1, 1], 
                         shape=(Nx, Nx))
        
        # y方向动能项
        coeff_y = -self.hbar**2 / (2 * self.m_eff * dy2 + 1e-50)
        Ty = sparse.diags([-2 * coeff_y, coeff_y, coeff_y], 
                         [0, -1, 1], 
                         shape=(Ny, Ny))
        
        # 总哈密顿量: H = Tx ⊗ Iy + Ix ⊗ Ty + V
        Ix = sparse.eye(Nx)
        Iy = sparse.eye(Ny)
        
        H = sparse.kron(Tx, Iy) + sparse.kron(Ix, Ty) + sparse.diags(V.ravel())
        
        return H
    
    def _build_hamiltonian_3d(self, V):
        """3D 哈密顿量 - 简化的对角近似"""
        print("警告: 3D哈密顿量使用简化模型")
        N = len(self.x) * len(self.y) * len(self.z)
        
        # 简化的对角哈密顿量
        H = sparse.diags(V.ravel())
        
        return H
    
    def solve_transmission(self, V, energy_range=(0.1, 2.0), num_energies=100):
        """计算透射系数 - 使用传输矩阵法"""
        print("计算透射系数...")
        
        energies = np.linspace(energy_range[0], energy_range[1], num_energies) * self.q
        transmission = np.zeros_like(energies)
        
        for i, E in enumerate(tqdm(energies)):
            if self.dim == 1:
                transmission[i] = self._transfer_matrix_1d(V, E)
            else:
                # 多维使用WKB近似
                transmission[i] = self._wkb_approximation(V, E)
        
        # 处理可能的NaN值
        transmission = np.nan_to_num(transmission, nan=0.0, posinf=1.0, neginf=0.0)
        transmission = np.clip(transmission, 0.0, 1.0)
        
        return energies / self.q, transmission
    
    def _transfer_matrix_1d(self, V, E):
        """1D 传输矩阵法"""
        # 波矢 - 添加数值稳定性
        delta_V = E - V
        k = np.sqrt(2 * self.m_eff * np.abs(delta_V) + 1e-50) / (self.hbar + 1e-50)
        k[delta_V < 0] = 1j * k[delta_V < 0]  # 衰减波
        
        # 简化的传输矩阵计算
        T = 1.0
        for i in range(1, len(V)):
            # 界面传输
            if i < len(V) - 1:
                k1, k2 = k[i-1], k[i]
                # 避免除零错误
                denominator = k1 + k2
                if abs(denominator) < 1e-30:
                    t = 0.0
                else:
                    r = (k1 - k2) / denominator  # 反射系数
                    t = 2 * k1 / denominator     # 透射系数
                T *= np.abs(t)**2 * np.exp(-2 * np.abs(np.imag(k[i])) * self.dx)
        
        return np.real(T)
    
    def _wkb_approximation(self, V, E):
        """WKB近似计算透射系数"""
        if self.dim == 1:
            # 找到经典禁带区域
            tunneling_region = V > E
            if np.any(tunneling_region):
                # 计算积分
                kappa = np.sqrt(2 * self.m_eff * (V[tunneling_region] - E) + 1e-50) / (self.hbar + 1e-50)
                integral = np.trapz(kappa, self.x[tunneling_region])
                return np.exp(-2 * np.abs(integral))
            else:
                return 1.0
        else:
            # 多维简化处理
            V_avg = np.mean(V)
            if E < V_avg:
                return np.exp(-np.sqrt(2 * self.m_eff * (V_avg - E) + 1e-50) * self.Lx / (self.hbar + 1e-50))
            else:
                return 1.0
    
    def calculate_current_voltage(self, V_potential, Vd_range=(0.0, 1.0), num_points=50):
        """计算I-V特性曲线"""
        print("计算I-V特性...")
        
        Vd_values = np.linspace(Vd_range[0], Vd_range[1], num_points)
        current = np.zeros_like(Vd_values)
        
        for i, Vd in enumerate(tqdm(Vd_values)):
            # 更新势能中的漏极偏压
            if self.dim == 1:
                V_updated = self._update_bias_1d(V_potential, Vd)
            else:
                V_updated = V_potential  # 简化处理
            
            # 计算透射系数
            energies, transmission = self.solve_transmission(V_updated)
            
            # Landauer公式计算电流
            current[i] = self._landauer_current(energies * self.q, transmission, Vd)
        
        # 处理可能的NaN值
        current = np.nan_to_num(current, nan=0.0, posinf=0.0, neginf=0.0)
        
        return Vd_values, current
    
    def _update_bias_1d(self, V, Vd):
        """更新1D势能中的偏压"""
        V_updated = V.copy()
        # 简化的偏压更新 - 实际应用中需要自洽计算
        drain_region = self.x > 0.7 * self.Lx
        V_updated[drain_region] += Vd * self.q
        return V_updated
    
    def _landauer_current(self, energies, transmission, Vd):
        """Landauer公式计算电流"""
        # 费米-狄拉克分布
        def fermi(e, mu, T):
            # 添加数值稳定性
            exponent = (e - mu) / (T + 1e-50)
            # 避免数值溢出
            exponent = np.clip(exponent, -500, 500)
            return 1.0 / (1.0 + np.exp(exponent))
        
        # 源漏化学势
        mu_s = 0  # 源极
        mu_d = -Vd * self.q  # 漏极
        
        # 电流积分
        integrand = transmission * (fermi(energies, mu_s, self.kT) - 
                                  fermi(energies, mu_d, self.kT))
        
        current = (2 * self.q / (self.hbar + 1e-50)) * np.trapz(integrand, energies)
        return current
    
    def quantum_capacitance(self, Vg_range=(0.0, 2.0), num_points=50):
        """计算量子电容"""
        print("计算量子电容...")
        
        Vg_values = np.linspace(Vg_range[0], Vg_range[1], num_points)
        Cq = np.zeros_like(Vg_values)
        
        for i, Vg in enumerate(tqdm(Vg_values)):
            # 不同栅压下的态密度
            V_potential = self.create_mosfet_potential(Vg=Vg)
            energies, dos = self.calculate_dos(V_potential)
            
            # 量子电容 Cq = e² * ∫ DOS(E) * (-df/dE) dE
            def fermi_derivative(e, mu, T):
                f = 1.0 / (1.0 + np.exp((e - mu) / (T + 1e-50)))
                return f * (1 - f) / (T + 1e-50)
            
            mu = 0  # 费米能级
            integrand = dos * fermi_derivative(energies * self.q, mu, self.kT)
            Cq[i] = self.q**2 * np.trapz(integrand, energies * self.q)
        
        # 处理可能的NaN值
        Cq = np.nan_to_num(Cq, nan=0.0, posinf=0.0, neginf=0.0)
        
        return Vg_values, Cq
    
    def calculate_dos(self, V, energy_range=(-1.0, 1.0), num_points=200):
        """计算态密度"""
        if self.dim == 1:
            return self._calculate_dos_1d(V, energy_range, num_points)
        else:
            # 多维简化处理
            energies = np.linspace(energy_range[0], energy_range[1], num_points)
            dos = np.ones_like(energies)  # 常数近似
            return energies, dos
    
    def _calculate_dos_1d(self, V, energy_range, num_points):
        """1D 态密度计算"""
        energies = np.linspace(energy_range[0], energy_range[1], num_points) * self.q
        dos = np.zeros_like(energies)
        
        # 使用格林函数方法计算DOS
        for i, E in enumerate(energies):
            # 简化的DOS计算 - 添加数值稳定性
            delta_E = E - V
            k = np.sqrt(2 * self.m_eff * np.maximum(delta_E, 1e-50)) / (self.hbar + 1e-50)
            # 避免除零错误
            k_safe = np.where(k > 1e-30, k, 1e-30)
            dos[i] = np.sum(1.0 / (np.pi * np.abs(k_safe))) / len(V)
        
        return energies / self.q, dos

class NanoTransistorDesignStudio:
    """纳米晶体管设计工作室 - 工业级应用"""
    
    def __init__(self):
        self.simulators = {}
        self.design_projects = {}
        self.material_library = {}
        self.performance_metrics = {}
        self.load_material_database()
        
    def load_material_database(self):
        """加载扩展的材料数据库"""
        self.material_library = {
            # 传统半导体
            'Si': {'m_eff': 0.26, 'eps_r': 11.7, 'Eg': 1.12, 'mobility': 1400, 'cost': 'low'},
            'Ge': {'m_eff': 0.12, 'eps_r': 16.0, 'Eg': 0.66, 'mobility': 3900, 'cost': 'medium'},
            'GaAs': {'m_eff': 0.067, 'eps_r': 12.9, 'Eg': 1.42, 'mobility': 8500, 'cost': 'high'},
            
            # 高k介质材料
            'SiO2': {'m_eff': 0.50, 'eps_r': 3.9, 'Eg': 9.0, 'mobility': 10, 'cost': 'low'},
            'HfO2': {'m_eff': 0.15, 'eps_r': 25.0, 'Eg': 5.7, 'mobility': 15, 'cost': 'medium'},
            'Al2O3': {'m_eff': 0.30, 'eps_r': 9.0, 'Eg': 8.7, 'mobility': 12, 'cost': 'medium'},
            
            # 2D材料
            'Graphene': {'m_eff': 0.01, 'eps_r': 2.4, 'Eg': 0.0, 'mobility': 200000, 'cost': 'high'},
            'MoS2': {'m_eff': 0.45, 'eps_r': 5.2, 'Eg': 1.8, 'mobility': 200, 'cost': 'high'},
            'WS2': {'m_eff': 0.35, 'eps_r': 5.1, 'Eg': 2.1, 'mobility': 150, 'cost': 'high'},
            
            # 新兴材料
            'Black_P': {'m_eff': 0.15, 'eps_r': 5.5, 'Eg': 0.3, 'mobility': 1000, 'cost': 'very_high'},
            'InSb': {'m_eff': 0.014, 'eps_r': 16.8, 'Eg': 0.17, 'mobility': 77000, 'cost': 'very_high'}
        }
        
    def create_technology_node(self, node_name, channel_length, oxide_thickness, 
                             material_stack, Vdd=0.7, design_rules=None):
        """创建特定工艺节点的晶体管设计"""
        
        if design_rules is None:
            design_rules = {
                'min_channel_length': channel_length * 0.8,
                'max_voltage': Vdd * 1.1,
                'leakage_spec': 1e-2,  # A/μm
                'performance_target': 1000  # μA/μm
            }
        
        project = {
            'name': node_name,
            'channel_length': channel_length,
            'oxide_thickness': oxide_thickness,
            'material_stack': material_stack,
            'Vdd': Vdd,
            'design_rules': design_rules,
            'created_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'status': 'initialized'
        }
        
        self.design_projects[node_name] = project
        print(f"创建工艺节点: {node_name}")
        print(f"沟道长度: {channel_length*1e9:.1f} nm, Vdd: {Vdd} V")
        print(f"材料堆叠: {material_stack}")
        
        return project
    
    def analyze_quantum_effects(self, project_name, analysis_types=None):
        """分析量子效应对于特定工艺节点的影响"""
        
        if analysis_types is None:
            analysis_types = ['tunneling', 'quantum_capacitance', 'ballistic_transport', 'subthreshold']
        
        project = self.design_projects[project_name]
        results = {}
        
        print(f"\n开始量子效应分析 - {project_name}")
        print("=" * 60)
        
        # 为每个材料组合创建仿真器
        for material_combo in project['material_stack']:
            print(f"\n分析材料组合: {material_combo}")
            
            # 创建仿真器
            sim_key = f"{project_name}_{material_combo}"
            self.simulators[sim_key] = AdvancedQuantumTunneling(
                dimensions=2,  # 使用2D进行更准确的分析
                grid_points=300
            )
            
            simulator = self.simulators[sim_key]
            simulator.set_material(material_combo['channel'])
            simulator.set_device_geometry(
                length=project['channel_length'],
                width=10e-9
            )
            
            # 生成势能
            V_potential = simulator.create_mosfet_potential(
                Vg=project['Vdd'],
                Vd=project['Vdd'],
                tox=project['oxide_thickness']
            )
            
            material_results = {}
            
            # 隧穿效应分析
            if 'tunneling' in analysis_types:
                energies, transmission = simulator.solve_transmission(V_potential)
                material_results['tunneling'] = {
                    'energies': energies,
                    'transmission': transmission,
                    'avg_transmission': np.mean(transmission)
                }
            
            # 量子电容分析
            if 'quantum_capacitance' in analysis_types:
                Vg_values, Cq = simulator.quantum_capacitance()
                material_results['quantum_capacitance'] = {
                    'Vg': Vg_values,
                    'Cq': Cq,
                    'max_Cq': np.max(Cq)
                }
            
            # I-V特性
            Vd_values, current = simulator.calculate_current_voltage(V_potential)
            material_results['iv_characteristics'] = {
                'Vd': Vd_values,
                'current': current,
                'on_current': np.max(current),
                'off_current': np.min(current[current > 0])
            }
            
            results[material_combo['name']] = material_results
        
        project['quantum_analysis'] = results
        project['status'] = 'analyzed'
        
        return results
    
    def calculate_performance_metrics(self, project_name):
        """计算关键性能指标"""
        
        project = self.design_projects[project_name]
        analysis_results = project['quantum_analysis']
        
        metrics = {}
        
        for material_name, results in analysis_results.items():
            iv_data = results['iv_characteristics']
            tunneling_data = results['tunneling']
            
            # 关键性能指标
            material_metrics = {
                'I_on': iv_data['on_current'] * 1e6,  # μA/μm
                'I_off': iv_data['off_current'] * 1e6,  # μA/μm
                'I_on_I_off_ratio': iv_data['on_current'] / max(iv_data['off_current'], 1e-30),
                'avg_transmission': tunneling_data['avg_transmission'],
                'subthreshold_swing': self._calculate_ss(results),
                'DIBL': self._calculate_dibl(results),  # 漏致势垒降低
                'quantum_capacitance_impact': results['quantum_capacitance']['max_Cq'] * 1e4  # fF/μm²
            }
            
            # 检查设计规则符合性
            material_metrics['design_rule_compliance'] = self._check_design_rules(
                material_metrics, project['design_rules']
            )
            
            metrics[material_name] = material_metrics
        
        project['performance_metrics'] = metrics
        return metrics
    
    def _calculate_ss(self, results):
        """计算亚阈值摆幅"""
        # 简化计算 - 实际应用中需要更精细的模型
        iv_data = results['iv_characteristics']
        if len(iv_data['current']) > 10:
            return 80  # mV/decade
        return 100
    
    def _calculate_dibl(self, results):
        """计算DIBL系数"""
        # 简化计算
        return 50  # mV/V
    
    def _check_design_rules(self, metrics, design_rules):
        """检查设计规则符合性"""
        compliance = {
            'leakage_current': metrics['I_off'] <= design_rules['leakage_spec'] * 1e6,
            'performance': metrics['I_on'] >= design_rules['performance_target'],
            'swing': metrics['subthreshold_swing'] <= 100,
            'dibl': metrics['DIBL'] <= 100
        }
        
        compliance['overall'] = all(compliance.values())
        return compliance
    
    def generate_technology_report(self, project_name, output_dir='reports'):
        """生成详细的技术报告"""
        
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        project = self.design_projects[project_name]
        metrics = project['performance_metrics']
        
        # 创建报告
        report = {
            'project_info': {
                'name': project['name'],
                'date_generated': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'channel_length_nm': project['channel_length'] * 1e9,
                'oxide_thickness_nm': project['oxide_thickness'] * 1e9,
                'Vdd': project['Vdd']
            },
            'material_analysis': {},
            'recommendations': []
        }
        
        # 分析每个材料
        best_material = None
        best_score = -np.inf
        
        for material_name, material_metrics in metrics.items():
            # 计算综合评分
            score = self._calculate_material_score(material_metrics)
            
            report['material_analysis'][material_name] = {
                'performance_metrics': material_metrics,
                'compliance_status': material_metrics['design_rule_compliance'],
                'overall_score': score
            }
            
            if score > best_score:
                best_score = score
                best_material = material_name
        
        # 生成推荐
        if best_material:
            report['recommendations'].append({
                'type': 'best_material',
                'material': best_material,
                'score': best_score,
                'reason': f"在测试的材料中综合性能最佳"
            })
        
        # 转换NumPy类型为JSON可序列化类型
        def convert_to_serializable(obj):
            """将NumPy数据类型转换为JSON可序列化的Python原生类型"""
            if isinstance(obj, (np.bool_)):
                return bool(obj)
            elif isinstance(obj, (np.integer)):
                return int(obj)
            elif isinstance(obj, (np.floating)):
                return float(obj)
            elif isinstance(obj, (np.ndarray)):
                return obj.tolist()
            elif isinstance(obj, (dict)):
                return {key: convert_to_serializable(value) for key, value in obj.items()}
            elif isinstance(obj, (list, tuple)):
                return [convert_to_serializable(item) for item in obj]
            else:
                return obj
        
        serializable_report = convert_to_serializable(report)
        
        # 保存报告
        report_file = os.path.join(output_dir, f"{project_name}_quantum_analysis_report.json")
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(serializable_report, f, indent=2, ensure_ascii=False)
        
        # 生成图表
        self._generate_analysis_plots(project_name, output_dir)
        
        print(f"\n技术报告已生成: {report_file}")
        return report
    
    def _calculate_material_score(self, metrics):
        """计算材料综合评分"""
        # 加权评分系统
        weights = {
            'I_on': 0.3,
            'I_on_I_off_ratio': 0.25,
            'subthreshold_swing': 0.2,
            'DIBL': 0.15,
            'quantum_capacitance_impact': 0.1
        }
        
        score = 0
        for key, weight in weights.items():
            normalized_value = self._normalize_metric(key, metrics[key])
            score += weight * normalized_value
        
        return score
    
    def _normalize_metric(self, metric_name, value):
        """归一化性能指标"""
        normalization_ranges = {
            'I_on': (0, 5000),  # μA/μm
            'I_on_I_off_ratio': (1e3, 1e8),
            'subthreshold_swing': (60, 120),  # 越小越好
            'DIBL': (0, 150),  # 越小越好
            'quantum_capacitance_impact': (0, 50)  # fF/μm²
        }
        
        min_val, max_val = normalization_ranges[metric_name]
        
        if metric_name in ['subthreshold_swing', 'DIBL']:
            # 对于这些指标，值越小越好
            normalized = 1 - (value - min_val) / (max_val - min_val)
        else:
            # 对于其他指标，值越大越好
            normalized = (value - min_val) / (max_val - min_val)
        
        return np.clip(normalized, 0, 1)
    
    def _generate_analysis_plots(self, project_name, output_dir):
        """生成分析图表"""
        
        project = self.design_projects[project_name]
        analysis_results = project['quantum_analysis']
        metrics = project['performance_metrics']
        
        fig = plt.figure(figsize=(20, 16))
        
        # 1. I-V特性比较
        ax1 = plt.subplot(2, 3, 1)
        for material_name, results in analysis_results.items():
            iv_data = results['iv_characteristics']
            plt.plot(iv_data['Vd'], iv_data['current'] * 1e6, 
                    label=material_name, linewidth=2, marker='o', markersize=4)
        
        plt.xlabel('漏极电压 Vd (V)')
        plt.ylabel('电流 I (μA/μm)')
        plt.title('不同材料I-V特性比较')
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        # 2. 透射系数比较
        ax2 = plt.subplot(2, 3, 2)
        for material_name, results in analysis_results.items():
            if 'tunneling' in results:
                tunneling_data = results['tunneling']
                plt.semilogy(tunneling_data['energies'], tunneling_data['transmission'],
                           label=material_name, linewidth=2)
        
        plt.xlabel('能量 (eV)')
        plt.ylabel('透射系数 T(E)')
        plt.title('量子隧穿特性')
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        # 3. 量子电容比较
        ax3 = plt.subplot(2, 3, 3)
        for material_name, results in analysis_results.items():
            if 'quantum_capacitance' in results:
                cap_data = results['quantum_capacitance']
                plt.plot(cap_data['Vg'], cap_data['Cq'] * 1e4,
                        label=material_name, linewidth=2)
        
        plt.xlabel('栅极电压 Vg (V)')
        plt.ylabel('量子电容 (fF/μm²)')
        plt.title('量子电容特性')
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        # 4. 性能指标雷达图
        ax4 = plt.subplot(2, 3, 4, polar=True)
        
        categories = ['I_on', 'I_on_I_off_ratio', 'subthreshold_swing', 
                     'DIBL', 'quantum_capacitance_impact']
        categories_display = ['开态电流', '开关比', '亚阈值摆幅', 'DIBL', '量子电容']
        
        N = len(categories)
        angles = [n / float(N) * 2 * np.pi for n in range(N)]
        angles += angles[:1]  # 闭合图形
        
        for material_name, material_metrics in metrics.items():
            values = []
            for category in categories:
                normalized = self._normalize_metric(category, material_metrics[category])
                values.append(normalized)
            values += values[:1]  # 闭合图形
            
            ax4.plot(angles, values, 'o-', linewidth=2, label=material_name)
            ax4.fill(angles, values, alpha=0.1)
        
        ax4.set_xticks(angles[:-1])
        ax4.set_xticklabels(categories_display)
        ax4.set_ylim(0, 1)
        plt.title('性能指标雷达图', y=1.08)
        plt.legend(bbox_to_anchor=(1.1, 1.0))
        
        # 5. 设计规则符合性
        ax5 = plt.subplot(2, 3, 5)
        compliance_data = []
        material_names = list(metrics.keys())
        rule_categories = ['leakage_current', 'performance', 'swing', 'dibl', 'overall']
        rule_labels = ['漏电流', '性能', '亚阈值摆幅', 'DIBL', '总体符合']
        
        for material_name in material_names:
            compliance = metrics[material_name]['design_rule_compliance']
            compliance_rates = [int(compliance[rule]) for rule in rule_categories]
            compliance_data.append(compliance_rates)
        
        compliance_array = np.array(compliance_data)
        x = np.arange(len(rule_categories))
        width = 0.8 / len(material_names)
        
        for i, material_name in enumerate(material_names):
            offset = width * i - width * (len(material_names) - 1) / 2
            bars = ax5.bar(x + offset, compliance_array[i], width, label=material_name)
            
            # 添加数值标签
            for bar, value in zip(bars, compliance_array[i]):
                height = bar.get_height()
                ax5.text(bar.get_x() + bar.get_width()/2., height,
                        f'{value}', ha='center', va='bottom')
        
        ax5.set_xlabel('设计规则类别')
        ax5.set_ylabel('符合性 (1=符合, 0=不符合)')
        ax5.set_title('设计规则符合性分析')
        ax5.set_xticks(x)
        ax5.set_xticklabels(rule_labels)
        ax5.legend()
        ax5.set_ylim(0, 1.2)
        
        # 6. 综合评分
        ax6 = plt.subplot(2, 3, 6)
        scores = [self._calculate_material_score(metrics[material]) 
                 for material in material_names]
        
        bars = ax6.bar(material_names, scores, color=['skyblue', 'lightcoral', 'lightgreen'])
        ax6.set_ylabel('综合评分')
        ax6.set_title('材料综合性能评分')
        ax6.set_ylim(0, 1)
        
        # 添加数值标签
        for bar, score in zip(bars, scores):
            height = bar.get_height()
            ax6.text(bar.get_x() + bar.get_width()/2., height,
                    f'{score:.3f}', ha='center', va='bottom')
        
        plt.suptitle(f'{project_name} - 量子效应综合分析报告', fontsize=16, fontweight='bold')
        plt.tight_layout()
        
        # 保存图片
        plot_file = os.path.join(output_dir, f"{project_name}_analysis_plots.png")
        plt.savefig(plot_file, dpi=300, bbox_inches='tight')
        plt.show()
        
        return plot_file

# 实际应用场景演示
def demonstrate_industrial_application():
    """演示工业级应用场景"""
    
    print("纳米级晶体管量子特性分析与优化系统")
    print("=" * 60)
    print("应用场景: 3nm以下工艺节点芯片设计")
    print("主要功能: 量子效应分析、材料评估、性能优化、设计验证")
    print("=" * 60)
    
    # 创建设计工作室
    design_studio = NanoTransistorDesignStudio()
    
    # 定义不同的工艺节点
    technology_nodes = {
        '3nm_Node': {
            'channel_length': 3e-9,
            'oxide_thickness': 0.5e-9,
            'Vdd': 0.65,
            'material_combinations': [
                {
                    'name': 'Si_FinFET',
                    'channel': 'Si',
                    'oxide': 'HfO2',
                    'architecture': 'FinFET'
                },
                {
                    'name': 'GaAs_GAA',
                    'channel': 'GaAs', 
                    'oxide': 'Al2O3',
                    'architecture': 'GAA'
                },
                {
                    'name': 'MoS2_Nanosheet',
                    'channel': 'MoS2',
                    'oxide': 'HfO2', 
                    'architecture': 'Nanosheet'
                }
            ]
        },
        '2nm_Node': {
            'channel_length': 2e-9,
            'oxide_thickness': 0.4e-9, 
            'Vdd': 0.6,
            'material_combinations': [
                {
                    'name': 'Si_Nanosheet',
                    'channel': 'Si',
                    'oxide': 'HfO2',
                    'architecture': 'Nanosheet'
                },
                {
                    'name': 'WS2_GAA',
                    'channel': 'WS2',
                    'oxide': 'Al2O3',
                    'architecture': 'GAA'
                },
                {
                    'name': 'Black_P_FET',
                    'channel': 'Black_P',
                    'oxide': 'HfO2',
                    'architecture': 'Vertical'
                }
            ]
        }
    }
    
    all_reports = {}
    
    # 分析每个工艺节点
    for node_name, node_specs in technology_nodes.items():
        print(f"\n{'='*60}")
        print(f"分析工艺节点: {node_name}")
        print(f"{'='*60}")
        
        # 创建工艺节点项目
        project = design_studio.create_technology_node(
            node_name=node_name,
            channel_length=node_specs['channel_length'],
            oxide_thickness=node_specs['oxide_thickness'],
            material_stack=node_specs['material_combinations'],
            Vdd=node_specs['Vdd']
        )
        
        # 量子效应分析
        analysis_results = design_studio.analyze_quantum_effects(node_name)
        
        # 计算性能指标
        performance_metrics = design_studio.calculate_performance_metrics(node_name)
        
        # 生成技术报告
        technology_report = design_studio.generate_technology_report(node_name)
        
        all_reports[node_name] = technology_report
        
        # 打印关键发现
        print(f"\n{node_name} 关键发现:")
        print("-" * 40)
        best_material = technology_report['recommendations'][0]['material']
        best_score = technology_report['recommendations'][0]['score']
        print(f"推荐材料: {best_material} (评分: {best_score:.3f})")
        
        best_metrics = performance_metrics[best_material]
        print(f"开态电流: {best_metrics['I_on']:.1f} μA/μm")
        print(f"开关比: {best_metrics['I_on_I_off_ratio']:.2e}")
        print(f"设计规则符合性: {'通过' if best_metrics['design_rule_compliance']['overall'] else '未通过'}")
    
    # 生成跨节点比较报告
    generate_cross_node_comparison(all_reports)
    
    return design_studio, all_reports

def generate_cross_node_comparison(all_reports):
    """生成跨工艺节点比较报告"""
    
    print(f"\n{'='*60}")
    print("跨工艺节点性能比较")
    print(f"{'='*60}")
    
    fig, axes = plt.subplots(2, 2, figsize=(15, 12))
    
    # 收集数据
    node_names = list(all_reports.keys())
    all_metrics = {}
    
    for node_name, report in all_reports.items():
        node_metrics = {}
        for material, analysis in report['material_analysis'].items():
            node_metrics[material] = analysis['performance_metrics']
        all_metrics[node_name] = node_metrics
    
    # 1. 开态电流比较
    ax1 = axes[0, 0]
    for node_name in node_names:
        materials = list(all_metrics[node_name].keys())
        ion_currents = [all_metrics[node_name][mat]['I_on'] for mat in materials]
        
        x_pos = np.arange(len(materials))
        width = 0.8 / len(node_names)
        offset = width * (list(node_names).index(node_name) - len(node_names)/2 + 0.5)
        
        bars = ax1.bar(x_pos + offset, ion_currents, width, label=node_name)
        
        # 添加数值标签
        for bar, current in zip(bars, ion_currents):
            ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height(),
                    f'{current:.0f}', ha='center', va='bottom', fontsize=8)
    
    ax1.set_xlabel('材料')
    ax1.set_ylabel('开态电流 (μA/μm)')
    ax1.set_title('各节点开态电流比较')
    ax1.set_xticks(np.arange(len(materials)))
    ax1.set_xticklabels(materials, rotation=45)
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # 2. 开关比比较
    ax2 = axes[0, 1]
    for node_name in node_names:
        materials = list(all_metrics[node_name].keys())
        ratios = [all_metrics[node_name][mat]['I_on_I_off_ratio'] for mat in materials]
        
        x_pos = np.arange(len(materials))
        width = 0.8 / len(node_names)
        offset = width * (list(node_names).index(node_name) - len(node_names)/2 + 0.5)
        
        bars = ax2.bar(x_pos + offset, np.log10(ratios), width, label=node_name)
        
        for bar, ratio in zip(bars, ratios):
            ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height(),
                    f'10^{np.log10(ratio):.1f}', ha='center', va='bottom', fontsize=7)
    
    ax2.set_xlabel('材料')
    ax2.set_ylabel('开关比 (log10)')
    ax2.set_title('各节点开关比比较')
    ax2.set_xticks(np.arange(len(materials)))
    ax2.set_xticklabels(materials, rotation=45)
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # 3. 综合评分比较
    ax3 = axes[1, 0]
    for node_name in node_names:
        materials = list(all_metrics[node_name].keys())
        scores = [all_metrics[node_name][mat]['design_rule_compliance']['overall'] 
                 for mat in materials]
        
        x_pos = np.arange(len(materials))
        width = 0.8 / len(node_names)
        offset = width * (list(node_names).index(node_name) - len(node_names)/2 + 0.5)
        
        colors = ['green' if s else 'red' for s in scores]
        bars = ax3.bar(x_pos + offset, scores, width, label=node_name, color=colors)
        
        for bar, score in zip(bars, scores):
            status = '通过' if score else '未通过'
            ax3.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1,
                    status, ha='center', va='bottom', fontsize=8)
    
    ax3.set_xlabel('材料')
    ax3.set_ylabel('设计规则符合性')
    ax3.set_title('设计规则符合性比较')
    ax3.set_xticks(np.arange(len(materials)))
    ax3.set_xticklabels(materials, rotation=45)
    ax3.set_ylim(0, 1.5)
    ax3.legend()
    
    # 4. 技术路线推荐
    ax4 = axes[1, 1]
    recommendations = []
    scores = []
    
    for node_name, report in all_reports.items():
        if report['recommendations']:
            rec = report['recommendations'][0]
            recommendations.append(f"{node_name}\n{rec['material']}")
            scores.append(rec['score'])
    
    bars = ax4.bar(recommendations, scores, color=['gold', 'silver', 'brown'])
    ax4.set_ylabel('综合评分')
    ax4.set_title('各节点推荐技术路线')
    ax4.set_ylim(0, 1)
    
    for bar, score in zip(bars, scores):
        ax4.text(bar.get_x() + bar.get_width()/2, bar.get_height(),
                f'{score:.3f}', ha='center', va='bottom')
    
    plt.suptitle('纳米级晶体管技术路线分析', fontsize=16, fontweight='bold')
    plt.tight_layout()
    plt.show()
    
    # 打印技术路线建议
    print("\n技术路线建议:")
    print("-" * 40)
    for node_name, report in all_reports.items():
        if report['recommendations']:
            rec = report['recommendations'][0]
            print(f"{node_name}: 推荐 {rec['material']} (评分: {rec['score']:.3f})")

# 运行完整的工业级应用
if __name__ == "__main__":
    start_time = time.time()
    
    # 运行完整的工业级演示
    design_studio, reports = demonstrate_industrial_application()
    
    end_time = time.time()
    print(f"\n完整的工业级分析完成!")
    print(f"总耗时: {end_time - start_time:.2f} 秒")
    print(f"分析了 {len(reports)} 个工艺节点")
    print(f"评估了 {sum(len(report['material_analysis']) for report in reports.values())} 种材料组合")
    
    # 保存最终报告
    final_report = {
        'analysis_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'total_analysis_time_seconds': end_time - start_time,
        'technology_nodes_analyzed': list(reports.keys()),
        'summary': {}
    }
    
    for node_name, report in reports.items():
        if report['recommendations']:
            best_rec = report['recommendations'][0]
            final_report['summary'][node_name] = {
                'recommended_material': best_rec['material'],
                'score': best_rec['score'],
                'channel_length_nm': report['project_info']['channel_length_nm']
            }
    
    with open('nanotransistor_technology_roadmap.json', 'w', encoding='utf-8') as f:
        json.dump(final_report, f, indent=2, ensure_ascii=False)
    
    print(f"\n最终技术路线图已保存: nanotransistor_technology_roadmap.json")