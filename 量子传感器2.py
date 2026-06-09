import cv2
import numpy as np
import matplotlib.pyplot as plt
from scipy import ndimage
from scipy.sparse import diags
from scipy.sparse.linalg import spsolve
import numba
from collections import deque
import time

class PDEQuantumSensor:
    """基于偏微分方程的量子传感器模拟器"""
    
    def __init__(self, camera_index=0):
        self.camera_index = camera_index
        self.cap = None
        self.is_running = False
        
        # PDE参数
        self.dt = 0.1  # 时间步长
        self.dx = 1.0  # 空间步长
        self.diffusion_coeff = 0.1  # 扩散系数
        self.potential_strength = 0.5  # 势场强度
        self.wave_energy = 1.0  # 波能量
        
        # 量子PDE参数
        self.hbar = 1.0  # 约化普朗克常数
        self.mass = 1.0  # 粒子质量
        self.schrodinger_dt = 0.01
        
        # 分析参数
        self.frame_buffer = deque(maxlen=5)  # 帧缓冲区用于时间导数计算
        self.quantum_state = None
        
    def initialize_camera(self):
        """初始化摄像头"""
        try:
            self.cap = cv2.VideoCapture(self.camera_index)
            if not self.cap.isOpened():
                raise Exception("无法打开摄像头")
            
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.cap.set(cv2.CAP_PROP_FPS, 30)
            
            print("摄像头初始化成功")
            return True
            
        except Exception as e:
            print(f"摄像头初始化失败: {e}")
            return False

    def heat_equation_solver(self, frame, iterations=3):
        """
        热传导方程求解器
        ∂u/∂t = α ∇²u
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0
        u = gray.copy()
        
        # 有限差分法求解热传导方程
        for _ in range(iterations):
            # 拉普拉斯算子 (∇²u)
            laplacian = (np.roll(u, 1, axis=0) + np.roll(u, -1, axis=0) +
                        np.roll(u, 1, axis=1) + np.roll(u, -1, axis=1) - 4 * u)
            
            # 时间演化 u_{n+1} = u_n + α * dt * ∇²u
            u = u + self.diffusion_coeff * self.dt * laplacian
        
        return (u * 255).astype(np.uint8)

    def wave_equation_evolution(self, frame):
        """
        波动方程模拟
        ∂²u/∂t² = c² ∇²u
        """
        if len(self.frame_buffer) < 3:
            # 确保返回三通道图像
            if len(frame.shape) == 2:  # 如果是单通道
                return cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
            return frame
        
        # 确保使用三通道图像进行处理
        if len(self.frame_buffer[-2].shape) == 2:
            u_prev = self.frame_buffer[-2].astype(np.float32)
        else:
            u_prev = cv2.cvtColor(self.frame_buffer[-2], cv2.COLOR_BGR2GRAY).astype(np.float32)
        
        if len(self.frame_buffer[-1].shape) == 2:
            u_current = self.frame_buffer[-1].astype(np.float32)
        else:
            u_current = cv2.cvtColor(self.frame_buffer[-1], cv2.COLOR_BGR2GRAY).astype(np.float32)
        
        # 拉普拉斯算子
        laplacian = ndimage.laplace(u_current)
        
        # 波动方程演化 (简化版本)
        u_next = 2 * u_current - u_prev + (self.wave_energy ** 2) * laplacian
        
        # 转换为BGR格式
        u_next = np.clip(u_next, 0, 255).astype(np.uint8)
        
        # 确保输出是三通道
        if len(u_next.shape) == 2:
            wave_frame = cv2.cvtColor(u_next, cv2.COLOR_GRAY2BGR)
        else:
            wave_frame = u_next
        
        return wave_frame

    def schrodinger_equation_step(self, psi_real, psi_imag, potential, dt, dx, hbar, mass):
        """
        薛定谔方程数值求解 (使用分裂算符法)
        iℏ ∂ψ/∂t = [-ℏ²/2m ∇² + V] ψ
        """
        n = psi_real.shape[0]
        k = 2 * np.pi * np.fft.fftfreq(n, dx)
        
        # 动能算符 (傅里叶空间)
        kinetic = (hbar ** 2) * (k ** 2) / (2 * mass)
        
        # 第一步: 在实空间演化势能项的一半
        psi_real_new = psi_real * np.cos(-0.5 * potential * dt / hbar) - \
                      psi_imag * np.sin(-0.5 * potential * dt / hbar)
        psi_imag_new = psi_real * np.sin(-0.5 * potential * dt / hbar) + \
                      psi_imag * np.cos(-0.5 * potential * dt / hbar)
        
        # 第二步: 在动量空间演化动能项
        psi_real_fft = np.fft.fft(psi_real_new)
        psi_imag_fft = np.fft.fft(psi_imag_new)
        
        psi_real_fft_new = psi_real_fft * np.cos(-kinetic * dt / hbar) - \
                          psi_imag_fft * np.sin(-kinetic * dt / hbar)
        psi_imag_fft_new = psi_real_fft * np.sin(-kinetic * dt / hbar) + \
                          psi_imag_fft * np.cos(-kinetic * dt / hbar)
        
        psi_real_new = np.fft.ifft(psi_real_fft_new).real
        psi_imag_new = np.fft.ifft(psi_imag_fft_new).real
        
        # 第三步: 在实空间演化势能项的另一半
        psi_real_final = psi_real_new * np.cos(-0.5 * potential * dt / hbar) - \
                        psi_imag_new * np.sin(-0.5 * potential * dt / hbar)
        psi_imag_final = psi_real_new * np.sin(-0.5 * potential * dt / hbar) + \
                        psi_imag_new * np.cos(-0.5 * potential * dt / hbar)
        
        return psi_real_final, psi_imag_final

    def quantum_wave_packet_evolution(self, frame):
        """
        量子波包演化模拟
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0
        
        # 初始化波函数
        height, width = gray.shape
        
        if self.quantum_state is None:
            # 初始波函数 (高斯波包)
            x, y = np.meshgrid(np.linspace(-1, 1, width), np.linspace(-1, 1, height))
            x0, y0 = 0, 0  # 波包中心
            sigma = 0.3    # 波包宽度
            
            # 初始波函数
            psi_real = np.exp(-((x - x0)**2 + (y - y0)**2) / (2 * sigma**2))
            psi_imag = np.zeros_like(psi_real)
            
            self.quantum_state = (psi_real, psi_imag)
        
        psi_real, psi_imag = self.quantum_state
        
        # 势场 (基于图像强度)
        potential = self.potential_strength * (1 - gray)
        
        # 对每一行进行薛定谔方程演化
        for i in range(height):
            psi_real[i], psi_imag[i] = self.schrodinger_equation_step(
                psi_real[i], psi_imag[i], potential[i], 
                self.schrodinger_dt, self.dx, self.hbar, self.mass
            )
        
        # 计算概率密度
        probability_density = psi_real**2 + psi_imag**2
        
        # 归一化
        probability_density = probability_density / (np.sum(probability_density) + 1e-8)
        
        # 更新量子态
        self.quantum_state = (psi_real, psi_imag)
        
        # 转换为可视化格式
        quantum_frame = (probability_density * 255).astype(np.uint8)
        quantum_frame = cv2.applyColorMap(quantum_frame, cv2.COLORMAP_JET)
        
        return quantum_frame

    def navier_stokes_approximation(self, frame):
        """
        纳维-斯托克斯方程近似 (用于量子流体动力学)
        ρ(∂v/∂t + v·∇v) = -∇p + μ∇²v + f
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0
        
        # 速度场初始化 (从图像梯度获得)
        grad_y, grad_x = np.gradient(gray)
        
        # 简化版本: 只考虑扩散项和压力项
        velocity_x = grad_x
        velocity_y = grad_y
        
        # 压力项 (泊松方程)
        pressure = -ndimage.laplace(gray)
        
        # 扩散项
        diffusion_x = ndimage.laplace(velocity_x)
        diffusion_y = ndimage.laplace(velocity_y)
        
        # 简化演化
        new_velocity_x = velocity_x + self.dt * (-pressure + self.diffusion_coeff * diffusion_x)
        new_velocity_y = velocity_y + self.dt * (-pressure + self.diffusion_coeff * diffusion_y)
        
        # 计算涡量
        vorticity = np.gradient(new_velocity_y, axis=1) - np.gradient(new_velocity_x, axis=0)
        
        # 可视化涡量场
        vorticity_vis = np.abs(vorticity) * 255
        vorticity_vis = np.clip(vorticity_vis, 0, 255).astype(np.uint8)
        vorticity_frame = cv2.applyColorMap(vorticity_vis, cv2.COLORMAP_JET)
        
        return vorticity_frame

    def maxwell_equations_simulation(self, frame):
        """
        麦克斯韦方程组模拟 (电磁场演化)
        ∇·E = ρ/ε₀, ∇·B = 0, ∇×E = -∂B/∂t, ∇×B = μ₀J + μ₀ε₀∂E/∂t
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0
        
        height, width = gray.shape
        
        # 电场和磁场初始化
        Ex = np.gradient(gray, axis=1)  # x方向电场
        Ey = np.gradient(gray, axis=0)  # y方向电场
        Bz = np.zeros_like(gray)        # z方向磁场
        
        # 电荷密度 (从图像强度推导)
        charge_density = gray - 0.5
        
        # 简化麦克斯韦方程演化
        for _ in range(2):  # 少量迭代
            # 法拉第定律: ∂B/∂t = -∇×E
            curl_E = np.gradient(Ey, axis=1) - np.gradient(Ex, axis=0)
            Bz = Bz - self.dt * curl_E
            
            # 安培-麦克斯韦定律: ∂E/∂t = c²∇×B - J/ε₀
            curl_B_y = np.gradient(Bz, axis=1)
            curl_B_x = -np.gradient(Bz, axis=0)
            
            # 电流密度 (简化)
            current_density = charge_density * 0.1
            
            Ex = Ex + self.dt * (self.wave_energy**2 * curl_B_x - current_density)
            Ey = Ey + self.dt * (self.wave_energy**2 * curl_B_y - current_density)
        
        # 计算电磁场能量密度
        em_energy = 0.5 * (Ex**2 + Ey**2 + Bz**2)
        em_energy_vis = (em_energy / (np.max(em_energy) + 1e-8) * 255).astype(np.uint8)
        
        em_frame = cv2.applyColorMap(em_energy_vis, cv2.COLORMAP_HOT)
        
        return em_frame

    def pde_based_quantum_analysis(self, frame):
        """
        基于PDE的量子特性分析
        """
        analysis_results = {}
        
        # 确保输入是三通道
        if len(frame.shape) == 2:
            frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
        
        # 1. 量子相干性分析 (通过波动方程)
        wave_frame = self.wave_equation_evolution(frame)
        # 确保wave_frame是三通道
        if len(wave_frame.shape) == 2:
            wave_gray = wave_frame
        else:
            wave_gray = cv2.cvtColor(wave_frame, cv2.COLOR_BGR2GRAY)
        analysis_results['coherence'] = np.std(wave_gray) / (np.mean(wave_gray) + 1e-8)
        
        # 2. 量子纠缠分析 (通过热扩散方程)
        heat_frame = self.heat_equation_solver(frame)
        # 确保heat_frame是三通道
        if len(heat_frame.shape) == 2:
            heat_gray = heat_frame
        else:
            heat_gray = cv2.cvtColor(heat_frame, cv2.COLOR_BGR2GRAY)
        
        # 计算信息扩散速率作为纠缠度量
        if len(frame.shape) == 2:
            original_gray = frame
        else:
            original_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        info_diffusion = np.mean(np.abs(heat_gray.astype(float) - original_gray.astype(float)))
        analysis_results['entanglement'] = info_diffusion
        
        # 3. 量子隧穿概率 (通过薛定谔方程)
        quantum_frame = self.quantum_wave_packet_evolution(frame)
        # 确保quantum_frame是三通道
        if len(quantum_frame.shape) == 2:
            quantum_gray = quantum_frame
        else:
            quantum_gray = cv2.cvtColor(quantum_frame, cv2.COLOR_BGR2GRAY)
        
        # 波函数穿透势垒的概率
        tunnel_prob = np.mean(quantum_gray > 128)  # 高概率区域的比例
        analysis_results['tunneling_probability'] = tunnel_prob
        
        # 4. 量子涡旋分析 (通过纳维-斯托克斯方程)
        vortex_frame = self.navier_stokes_approximation(frame)
        # 确保vortex_frame是三通道
        if len(vortex_frame.shape) == 2:
            vortex_gray = vortex_frame
        else:
            vortex_gray = cv2.cvtColor(vortex_frame, cv2.COLOR_BGR2GRAY)
        
        # 涡旋强度
        vortex_strength = np.mean(vortex_gray) / 255.0
        analysis_results['vortex_strength'] = vortex_strength
        
        # 5. 量子场能量 (通过麦克斯韦方程)
        em_frame = self.maxwell_equations_simulation(frame)
        # 确保em_frame是三通道
        if len(em_frame.shape) == 2:
            em_gray = em_frame
        else:
            em_gray = cv2.cvtColor(em_frame, cv2.COLOR_BGR2GRAY)
        analysis_results['field_energy'] = np.mean(em_gray) / 255.0
        
        return analysis_results

    def visualize_pde_analysis(self, frame, analysis_results):
        """
        可视化PDE分析结果
        """
        # 确保输入是三通道
        if len(frame.shape) == 2:
            frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
        
        height, width = frame.shape[:2]
        
        # 创建综合显示界面
        display_frame = np.zeros((height, width * 2, 3), dtype=np.uint8)
        
        # 左侧: 原始帧和PDE模拟
        left_panel = frame.copy()
        
        # 在左侧面板叠加量子波函数
        quantum_frame = self.quantum_wave_packet_evolution(frame)
        # 确保quantum_frame是三通道
        if len(quantum_frame.shape) == 2:
            quantum_frame = cv2.cvtColor(quantum_frame, cv2.COLOR_GRAY2BGR)
        
        alpha = 0.3
        left_panel = cv2.addWeighted(left_panel, 1 - alpha, quantum_frame, alpha, 0)
        
        # 右侧: 分析结果和图表
        right_panel = np.zeros((height, width, 3), dtype=np.uint8)
        
        # 显示分析参数
        y_offset = 30
        cv2.putText(right_panel, "PDE Quantum Analysis", (10, y_offset), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        y_offset += 40
        
        params = [
            f"Coherence: {analysis_results['coherence']:.4f}",
            f"Entanglement: {analysis_results['entanglement']:.2f}",
            f"Tunneling Prob: {analysis_results['tunneling_probability']:.3f}",
            f"Vortex Strength: {analysis_results['vortex_strength']:.3f}",
            f"Field Energy: {analysis_results['field_energy']:.3f}",
            f"Diffusion Coeff: {self.diffusion_coeff:.2f}",
            f"Potential Strength: {self.potential_strength:.2f}"
        ]
        
        for param in params:
            cv2.putText(right_panel, param, (10, y_offset), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
            y_offset += 20
        
        # 绘制实时场分布
        self.draw_field_distributions(right_panel, frame, y_offset)
        
        # 合并面板
        display_frame[:, :width] = left_panel
        display_frame[:, width:] = right_panel
        
        return display_frame

    def draw_field_distributions(self, panel, frame, start_y):
        """绘制场分布图"""
        # 确保输入是三通道
        if len(frame.shape) == 2:
            frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
        
        plot_height = 200
        plot_width = panel.shape[1] - 20
        
        if plot_height + start_y > panel.shape[0]:
            return
        
        # 创建绘图区域
        plot_area = np.zeros((plot_height, plot_width, 3), dtype=np.uint8)
        
        # 获取各种场的分布
        if len(frame.shape) == 2:
            gray = frame
        else:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # 1. 概率密度分布
        if self.quantum_state is not None:
            psi_real, psi_imag = self.quantum_state
            prob_density = psi_real**2 + psi_imag**2
            center_row = prob_density[prob_density.shape[0] // 2, :]
            center_row = center_row / (np.max(center_row) + 1e-8)
            
            # 绘制概率密度
            for i in range(1, len(center_row)):
                x1 = int((i-1) * plot_width / len(center_row))
                y1 = int(plot_height - center_row[i-1] * plot_height * 0.8)
                x2 = int(i * plot_width / len(center_row))
                y2 = int(plot_height - center_row[i] * plot_height * 0.8)
                cv2.line(plot_area, (x1, y1), (x2, y2), (0, 255, 0), 1)
        
        # 2. 势场分布
        potential = 1 - (gray.astype(float) / 255.0)
        center_potential = potential[potential.shape[0] // 2, :]
        
        for i in range(1, len(center_potential)):
            x1 = int((i-1) * plot_width / len(center_potential))
            y1 = int(plot_height - center_potential[i-1] * plot_height * 0.8)
            x2 = int(i * plot_width / len(center_potential))
            y2 = int(plot_height - center_potential[i] * plot_height * 0.8)
            cv2.line(plot_area, (x1, y1), (x2, y2), (255, 0, 0), 1)
        
        # 添加图例
        cv2.putText(plot_area, "Probability", (5, 15), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.3, (0, 255, 0), 1)
        cv2.putText(plot_area, "Potential", (5, 30), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.3, (255, 0, 0), 1)
        
        # 将绘图区域添加到面板
        panel[start_y:start_y+plot_height, 10:10+plot_width] = plot_area

    def run_pde_simulation(self):
        """运行PDE量子传感器模拟"""
        if not self.initialize_camera():
            return
        
        self.is_running = True
        
        print("基于PDE的量子传感器模拟启动...")
        print("控制按键:")
        print("  'q': 退出")
        print("  'd': 增加扩散系数")
        print("  'D': 减少扩散系数") 
        print("  'p': 增加势场强度")
        print("  'P': 减少势场强度")
        print("  'w': 增加波能量")
        print("  'W': 减少波能量")
        
        while self.is_running:
            ret, frame = self.cap.read()
            if not ret:
                print("无法读取帧")
                break
            
            # 添加到帧缓冲区用于时间导数计算
            self.frame_buffer.append(frame.copy())
            
            # 执行PDE分析
            analysis_results = self.pde_based_quantum_analysis(frame)
            
            # 可视化结果
            display_frame = self.visualize_pde_analysis(frame, analysis_results)
            
            # 显示结果
            cv2.imshow('PDE Quantum Sensor Analysis', display_frame)
            
            # 键盘控制
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('d'):
                self.diffusion_coeff = min(1.0, self.diffusion_coeff + 0.05)
            elif key == ord('D'):
                self.diffusion_coeff = max(0.01, self.diffusion_coeff - 0.05)
            elif key == ord('p'):
                self.potential_strength = min(2.0, self.potential_strength + 0.1)
            elif key == ord('P'):
                self.potential_strength = max(0.1, self.potential_strength - 0.1)
            elif key == ord('w'):
                self.wave_energy = min(3.0, self.wave_energy + 0.1)
            elif key == ord('W'):
                self.wave_energy = max(0.1, self.wave_energy - 0.1)
        
        self.cleanup()

    def cleanup(self):
        """清理资源"""
        if self.cap:
            self.cap.release()
        cv2.destroyAllWindows()
        self.is_running = False
        print("PDE量子传感器模拟已停止")

class AdvancedPDEQuantumSensor(PDEQuantumSensor):
    """高级PDE量子传感器，包含更多物理模型"""
    
    def __init__(self, camera_index=0):
        super().__init__(camera_index)
        
        # 高级PDE参数
        self.nonlinear_coeff = 0.1  # 非线性系数
        self.damping_coeff = 0.05   # 阻尼系数
        self.reaction_coeff = 0.2   # 反应系数
        
    def nonlinear_schrodinger_equation(self, frame):
        """
        非线性薛定谔方程 (Gross-Pitaevskii方程)
        iℏ ∂ψ/∂t = [-ℏ²/2m ∇² + V + g|ψ|²] ψ
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0
        
        if self.quantum_state is None:
            # 初始化波函数
            height, width = gray.shape
            x, y = np.meshgrid(np.linspace(-1, 1, width), np.linspace(-1, 1, height))
            psi_real = np.exp(-(x**2 + y**2) / 0.3)
            psi_imag = np.zeros_like(psi_real)
            self.quantum_state = (psi_real, psi_imag)
        
        psi_real, psi_imag = self.quantum_state
        potential = self.potential_strength * (1 - gray)
        
        # 非线性项: g|ψ|²
        density = psi_real**2 + psi_imag**2
        nonlinear_potential = self.nonlinear_coeff * density
        
        # 结合势场
        total_potential = potential + nonlinear_potential
        
        # 使用分裂算符法演化
        for i in range(psi_real.shape[0]):
            psi_real[i], psi_imag[i] = self.schrodinger_equation_step(
                psi_real[i], psi_imag[i], total_potential[i],
                self.schrodinger_dt, self.dx, self.hbar, self.mass
            )
        
        # 更新量子态
        self.quantum_state = (psi_real, psi_imag)
        
        # 可视化
        density_vis = (density / (np.max(density) + 1e-8) * 255).astype(np.uint8)
        return cv2.applyColorMap(density_vis, cv2.COLORMAP_VIRIDIS)
    
    def reaction_diffusion_system(self, frame):
        """
        反应-扩散系统 (Turing模式)
        ∂u/∂t = D_u ∇²u + f(u,v)
        ∂v/∂t = D_v ∇²v + g(u,v)
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0
        
        # 初始化化学浓度
        u = gray.copy()  # 激活剂
        v = 1 - gray     # 抑制剂
        
        # 反应项参数 (FitzHugh-Nagumo模型)
        a, b = 0.1, 0.2
        
        for _ in range(2):  # 少量迭代
            # 拉普拉斯项
            laplacian_u = ndimage.laplace(u)
            laplacian_v = ndimage.laplace(v)
            
            # 反应项
            f_uv = u - u**3 - v + a
            g_uv = (u - b * v) * self.reaction_coeff
            
            # 演化方程
            u_new = u + self.dt * (self.diffusion_coeff * laplacian_u + f_uv)
            v_new = v + self.dt * (0.5 * self.diffusion_coeff * laplacian_v + g_uv)
            
            u, v = u_new, v_new
        
        # 可视化图灵模式
        pattern = (u * 255).astype(np.uint8)
        return cv2.applyColorMap(pattern, cv2.COLORMAP_PLASMA)

def main():
    """主函数"""
    print("选择模拟模式:")
    print("1. 基础PDE量子传感器")
    print("2. 高级PDE量子传感器")
    
    choice = input("请输入选择 (1 或 2): ").strip()
    
    if choice == "1":
        sensor = PDEQuantumSensor(camera_index=0)
    elif choice == "2":
        sensor = AdvancedPDEQuantumSensor(camera_index=0)
    else:
        print("无效选择，使用基础模式")
        sensor = PDEQuantumSensor(camera_index=0)
    
    try:
        sensor.run_pde_simulation()
    except KeyboardInterrupt:
        print("\n用户中断模拟")
    except Exception as e:
        print(f"模拟过程中出现错误: {e}")
    finally:
        sensor.cleanup()

if __name__ == "__main__":
    main()