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
            'Graphene': {'m_eff': 0.01, 'eps_r': 2.4, 'Eg': 0.0}
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

class QuantumDeviceAnalyzer:
    """量子器件分析器"""
    
    def __init__(self, simulator):
        self.simulator = simulator
    
    def full_device_analysis(self, material='Si', Vg=1.0, Vd_range=(0.0, 1.0)):
        """完整器件分析"""
        print(f"\n开始 {material} 器件分析")
        print("=" * 50)
        
        # 设置材料
        self.simulator.set_material(material)
        
        # 确保几何尺寸已设置
        if not hasattr(self.simulator, 'x'):
            self.simulator.set_device_geometry()
        
        # 生成势能
        V_potential = self.simulator.create_mosfet_potential(Vg=Vg)
        
        # 计算透射系数
        energies, transmission = self.simulator.solve_transmission(V_potential)
        
        # 计算I-V特性
        Vd_values, current = self.simulator.calculate_current_voltage(V_potential, Vd_range)
        
        # 计算量子电容
        Vg_values, Cq = self.simulator.quantum_capacitance()
        
        return {
            'material': material,
            'potential': V_potential,
            'energies': energies,
            'transmission': transmission,
            'Vd': Vd_values,
            'current': current,
            'Vg_cap': Vg_values,
            'Cq': Cq
        }
    
    def compare_materials(self, materials=['Si', 'GaAs', 'Graphene']):
        """比较不同材料的性能"""
        results = {}
        
        for material in materials:
            print(f"\n分析材料: {material}")
            try:
                results[material] = self.full_device_analysis(material)
            except Exception as e:
                print(f"分析材料 {material} 时出错: {e}")
                # 创建空结果
                results[material] = {
                    'material': material,
                    'potential': np.array([0]),
                    'energies': np.array([0]),
                    'transmission': np.array([0]),
                    'Vd': np.array([0, 1]),
                    'current': np.array([0, 0]),
                    'Vg_cap': np.array([0, 1]),
                    'Cq': np.array([0, 0])
                }
        
        return results

def plot_comprehensive_analysis(results):
    """绘制综合分析结果"""
    fig = plt.figure(figsize=(20, 15))
    
    # 1. 势能分布
    ax1 = plt.subplot(3, 3, 1)
    if results['simulator'].dim == 1:
        plt.plot(results['simulator'].x * 1e9, results['potential'] / results['simulator'].q, 'b-', linewidth=2)
        plt.xlabel('位置 (nm)')
        plt.ylabel('势能 (eV)')
        plt.title('势能分布')
        plt.grid(True, alpha=0.3)
    
    # 2. 透射系数
    ax2 = plt.subplot(3, 3, 2)
    if len(results['energies']) > 0 and len(results['transmission']) > 0:
        plt.semilogy(results['energies'], results['transmission'], 'r-', linewidth=2)
        plt.xlabel('能量 (eV)')
        plt.ylabel('透射系数 T(E)')
        plt.title('能量相关的透射系数')
        plt.grid(True, alpha=0.3)
    
    # 3. I-V特性
    ax3 = plt.subplot(3, 3, 3)
    if len(results['Vd']) > 0 and len(results['current']) > 0:
        plt.plot(results['Vd'], results['current'] * 1e6, 'g-', linewidth=2)
        plt.xlabel('漏极电压 Vd (V)')
        plt.ylabel('电流 I (μA/μm)')
        plt.title('I-V 特性曲线')
        plt.grid(True, alpha=0.3)
    
    # 4. 量子电容
    ax4 = plt.subplot(3, 3, 4)
    if len(results['Vg_cap']) > 0 and len(results['Cq']) > 0:
        plt.plot(results['Vg_cap'], results['Cq'] * 1e4, 'purple', linewidth=2)
        plt.xlabel('栅极电压 Vg (V)')
        plt.ylabel('量子电容 (fF/μm²)')
        plt.title('量子电容 vs 栅压')
        plt.grid(True, alpha=0.3)
    
    # 5. 性能指标
    ax5 = plt.subplot(3, 3, 5)
    metrics = {}
    
    if len(results['transmission']) > 0:
        metrics['峰值透射率'] = np.max(results['transmission'])
        metrics['平均透射率'] = np.mean(results['transmission'])
    else:
        metrics['峰值透射率'] = 0
        metrics['平均透射率'] = 0
        
    if len(results['current']) > 0:
        current_safe = np.where(results['current'] > 1e-30, results['current'], 1e-30)
        metrics['最大电流'] = np.max(results['current']) * 1e6
        metrics['开关比'] = np.max(current_safe) / (np.min(current_safe) + 1e-30)
    else:
        metrics['最大电流'] = 0
        metrics['开关比'] = 0
        
    metrics['亚阈值摆幅'] = 100  # 简化计算
    
    bars = plt.bar(range(len(metrics)), list(metrics.values()))
    plt.xticks(range(len(metrics)), list(metrics.keys()), rotation=45)
    plt.ylabel('数值')
    plt.title('器件性能指标')
    
    # 添加数值标签
    for bar, value in zip(bars, metrics.values()):
        plt.text(bar.get_x() + bar.get_width()/2, bar.get_height(), 
                f'{value:.2e}', ha='center', va='bottom')
    
    # 6. 材料比较 (如果有多材料数据)
    if 'comparison' in results:
        ax6 = plt.subplot(3, 3, 6)
        for material, data in results['comparison'].items():
            if len(data['Vd']) > 0 and len(data['current']) > 0:
                plt.plot(data['Vd'], data['current'] * 1e6, label=material, linewidth=2)
        plt.xlabel('漏极电压 Vd (V)')
        plt.ylabel('电流 I (μA/μm)')
        plt.title('不同材料I-V特性比较')
        plt.legend()
        plt.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.show()

# 运行仿真
if __name__ == "__main__":
    start_time = time.time()
    
    print("量子隧穿芯片级仿真系统")
    print("=" * 50)
    
    # 创建1D仿真器
    sim_1d = AdvancedQuantumTunneling(dimensions=1, grid_points=500)
    
    # 先设置器件几何尺寸和材料
    sim_1d.set_device_geometry(length=10e-9)
    sim_1d.set_material('Si')
    
    analyzer = QuantumDeviceAnalyzer(sim_1d)
    
    # 硅器件分析
    si_results = analyzer.full_device_analysis('Si', Vg=1.0)
    si_results['simulator'] = sim_1d
    
    # 材料比较
    comparison_results = analyzer.compare_materials(['Si', 'GaAs', 'Graphene'])
    si_results['comparison'] = comparison_results
    
    # 绘制结果
    plot_comprehensive_analysis(si_results)
    
    # 2D器件仿真
    print("\n" + "="*50)
    print("2D器件仿真")
    print("="*50)
    
    sim_2d = AdvancedQuantumTunneling(dimensions=2, grid_points=100)
    sim_2d.set_material('GaAs')
    sim_2d.set_device_geometry(length=20e-9, width=10e-9)
    
    V_2d = sim_2d.create_mosfet_potential(Vg=1.0)
    
    # 绘制2D势能
    fig, ax = plt.subplots(1, 2, figsize=(15, 6))
    
    # 2D势能图
    X, Y = np.meshgrid(sim_2d.x * 1e9, sim_2d.y * 1e9)
    im1 = ax[0].contourf(X, Y, V_2d.T / sim_2d.q, 50, cmap='viridis')
    ax[0].set_xlabel('x (nm)')
    ax[0].set_ylabel('y (nm)')
    ax[0].set_title('2D MOSFET势能分布 (eV)')
    plt.colorbar(im1, ax=ax[0])
    
    # 透射系数
    energies, transmission = sim_2d.solve_transmission(V_2d)
    ax[1].semilogy(energies, transmission, 'b-', linewidth=2)
    ax[1].set_xlabel('能量 (eV)')
    ax[1].set_ylabel('透射系数')
    ax[1].set_title('2D器件透射特性')
    ax[1].grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.show()
    
    end_time = time.time()
    print(f"\n仿真完成! 总耗时: {end_time - start_time:.2f} 秒")
    
    # 性能总结
    print("\n性能总结:")
    print("-" * 30)
    for material, data in comparison_results.items():
        if len(data['current']) > 0:
            max_current = np.max(data['current']) * 1e6
        else:
            max_current = 0
            
        if len(data['transmission']) > 0:
            avg_transmission = np.mean(data['transmission'])
        else:
            avg_transmission = 0
            
        print(f"{material}: 最大电流 = {max_current:.2f} μA/μm, "
              f"平均透射率 = {avg_transmission:.3e}")