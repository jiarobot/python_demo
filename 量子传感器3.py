import cv2
import numpy as np
import matplotlib.pyplot as plt
from scipy import ndimage
from scipy.fftpack import dct, idct
from scipy.special import erf
import numba
from collections import deque
import time
from sklearn.cluster import KMeans

class EntropicQuantumFieldSensor:
    """基于信息熵和麦克斯韦方程组的量子场传感器"""
    
    def __init__(self, camera_index=0):
        self.camera_index = camera_index
        self.cap = None
        self.is_running = False
        
        # 麦克斯韦方程组参数
        self.epsilon_0 = 8.854e-12  # 真空介电常数
        self.mu_0 = 1.256e-6       # 真空磁导率
        self.c = 1 / np.sqrt(self.epsilon_0 * self.mu_0)  # 光速
        
        # 量子场参数
        self.hbar = 1.0545718e-34  # 约化普朗克常数
        self.electron_charge = 1.602e-19
        
        # 信息熵参数
        self.entropy_window = 5
        self.mutual_info_history = deque(maxlen=100)
        self.quantum_entropy_history = deque(maxlen=100)
        
        # 实时优化参数
        self.downsample_factor = 2
        self.field_update_frequency = 2  # 每2帧更新一次场计算
        
        # 状态变量
        self.frame_count = 0
        self.E_field = None  # 电场 (Ex, Ey, Ez)
        self.B_field = None  # 磁场 (Bx, By, Bz)
        self.quantum_state = None
        self.charge_density = None
        
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

    @numba.jit(nopython=True, parallel=True)
    def maxwell_fdtd_2d(self, Ex, Ey, Bz, Jx, Jy, rho, dt, dx, epsilon_0, mu_0):
        """
        2D FDTD麦克斯韦方程组求解器 (TE模式)
        使用Yee网格进行离散化
        """
        nx, ny = Ex.shape
        
        # 更新磁场 Bz (法拉第定律)
        for i in numba.prange(1, nx-1):
            for j in numba.prange(1, ny-1):
                dBz_dt = -( (Ey[i+1, j] - Ey[i-1, j]) / (2*dx) - 
                           (Ex[i, j+1] - Ex[i, j-1]) / (2*dx) )
                Bz[i, j] = Bz[i, j] + dt * dBz_dt
        
        # 更新电场 Ex, Ey (安培-麦克斯韦定律)
        for i in numba.prange(1, nx-1):
            for j in numba.prange(1, ny-1):
                # Ex 分量
                dEy_dx = (Ey[i+1, j] - Ey[i-1, j]) / (2*dx)
                dEx_dt = ( (Bz[i, j] - Bz[i, j-1]) / dx - 
                          mu_0 * Jx[i, j] ) / epsilon_0
                Ex[i, j] = Ex[i, j] + dt * dEx_dt
                
                # Ey 分量
                dEx_dy = (Ex[i, j+1] - Ex[i, j-1]) / (2*dx)
                dEy_dt = ( -(Bz[i, j] - Bz[i-1, j]) / dx - 
                          mu_0 * Jy[i, j] ) / epsilon_0
                Ey[i, j] = Ey[i, j] + dt * dEy_dt
        
        return Ex, Ey, Bz

    def initialize_electromagnetic_fields(self, frame_shape):
        """初始化电磁场"""
        h, w = frame_shape[:2]
        
        if self.E_field is None:
            # 初始化电场和磁场
            self.E_field = (
                np.random.normal(0, 1e-3, (h, w)),  # Ex
                np.random.normal(0, 1e-3, (h, w)),  # Ey  
                np.zeros((h, w))                     # Ez
            )
            
            self.B_field = (
                np.zeros((h, w)),  # Bx
                np.zeros((h, w)),  # By
                np.random.normal(0, 1e-6, (h, w))  # Bz
            )
            
            # 电荷密度和电流密度
            self.charge_density = np.zeros((h, w))
            self.J_field = (
                np.zeros((h, w)),  # Jx
                np.zeros((h, w)),  # Jy
                np.zeros((h, w))   # Jz
            )

    def update_electromagnetic_fields(self, frame):
        """更新电磁场分布"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0
        
        # 从图像推导电荷和电流分布
        self.charge_density = gray - 0.5  # 归一化电荷密度
        
        # 电流密度从图像梯度推导
        grad_y, grad_x = np.gradient(gray)
        self.J_field = (
            grad_x * 0.1,  # Jx
            grad_y * 0.1,  # Jy
            np.zeros_like(gray)  # Jz
        )
        
        # FDTD参数
        dx = 1.0  # 空间步长 (像素)
        dt = 0.1 * dx / self.c  # 时间步长 (满足CFL条件)
        
        # 更新电磁场
        Ex, Ey, Bz = self.maxwell_fdtd_2d(
            self.E_field[0].copy(), self.E_field[1].copy(), self.B_field[2].copy(),
            self.J_field[0], self.J_field[1], self.charge_density,
            dt, dx, self.epsilon_0, self.mu_0
        )
        
        # 更新场状态
        self.E_field = (Ex, Ey, self.E_field[2])
        self.B_field = (self.B_field[0], self.B_field[1], Bz)
        
        return self.calculate_field_energy()

    def calculate_field_energy(self):
        """计算电磁场能量密度"""
        Ex, Ey, Ez = self.E_field
        Bx, By, Bz = self.B_field
        
        # 电磁场能量密度: u = 0.5 * (ε₀E² + B²/μ₀)
        electric_energy = 0.5 * self.epsilon_0 * (Ex**2 + Ey**2 + Ez**2)
        magnetic_energy = 0.5 * (Bx**2 + By**2 + Bz**2) / self.mu_0
        total_energy = electric_energy + magnetic_energy
        
        return {
            'electric_energy': np.mean(electric_energy),
            'magnetic_energy': np.mean(magnetic_energy), 
            'total_energy': np.mean(total_energy),
            'poynting_vector': self.calculate_poynting_vector()
        }

    def calculate_poynting_vector(self):
        """计算坡印廷矢量 (能流密度)"""
        Ex, Ey, Ez = self.E_field
        Bx, By, Bz = self.B_field
        
        # S = (E × B) / μ₀
        Sx = (Ey * Bz - Ez * By) / self.mu_0
        Sy = (Ez * Bx - Ex * Bz) / self.mu_0
        Sz = (Ex * By - Ey * Bx) / self.mu_0
        
        return np.sqrt(Sx**2 + Sy**2 + Sz**2)

    def quantum_electrodynamics_simulation(self, frame):
        """
        量子电动力学模拟
        结合电磁场和量子波函数演化
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0
        
        # 从电磁场推导量子势
        electric_potential = -np.sqrt(self.E_field[0]**2 + self.E_field[1]**2)
        magnetic_potential = np.sqrt(self.B_field[0]**2 + self.B_field[1]**2)
        
        # 总势场
        total_potential = electric_potential + magnetic_potential
        
        # 量子波函数演化 (使用QED修正的薛定谔方程)
        qed_frame = self.evolve_qed_wavefunction(gray, total_potential)
        
        return qed_frame

    def evolve_qed_wavefunction(self, image, potential):
        """
        QED波函数演化
        考虑电磁场相互作用的量子演化
        """
        h, w = image.shape
        
        # 初始化波函数
        if self.quantum_state is None:
            psi_real = np.exp(-((np.arange(w) - w/2)**2 / (2*(w/8)**2))[np.newaxis, :] * 
                            np.exp(-((np.arange(h) - h/2)**2 / (2*(h/8)**2))[:, np.newaxis]))
            psi_imag = np.zeros_like(psi_real)
            self.quantum_state = (psi_real, psi_imag)
        
        psi_real, psi_imag = self.quantum_state
        
        # QED演化参数
        dt = 0.01
        dx = 1.0
        
        # 分裂算符法演化
        for i in range(h):
            # 动能项 (傅里叶空间)
            k = 2 * np.pi * np.fft.fftfreq(w, dx)
            kinetic = (self.hbar**2) * (k**2) / (2 * self.electron_charge)
            
            # 势能项 (包含电磁相互作用)
            V = potential[i] * self.electron_charge
            
            # 演化步骤
            # 1. 半势能步
            psi_real_half = psi_real[i] * np.cos(-0.5 * V * dt / self.hbar) - \
                           psi_imag[i] * np.sin(-0.5 * V * dt / self.hbar)
            psi_imag_half = psi_real[i] * np.sin(-0.5 * V * dt / self.hbar) + \
                           psi_imag[i] * np.cos(-0.5 * V * dt / self.hbar)
            
            # 2. 动能步 (傅里叶空间)
            psi_real_fft = np.fft.fft(psi_real_half)
            psi_imag_fft = np.fft.fft(psi_imag_half)
            
            psi_real_fft_new = psi_real_fft * np.cos(-kinetic * dt / self.hbar) - \
                              psi_imag_fft * np.sin(-kinetic * dt / self.hbar)
            psi_imag_fft_new = psi_real_fft * np.sin(-kinetic * dt / self.hbar) + \
                              psi_imag_fft * np.cos(-kinetic * dt / self.hbar)
            
            psi_real_new = np.fft.ifft(psi_real_fft_new).real
            psi_imag_new = np.fft.ifft(psi_imag_fft_new).real
            
            # 3. 半势能步
            psi_real[i] = psi_real_new * np.cos(-0.5 * V * dt / self.hbar) - \
                         psi_imag_new * np.sin(-0.5 * V * dt / self.hbar)
            psi_imag[i] = psi_real_new * np.sin(-0.5 * V * dt / self.hbar) + \
                         psi_imag_new * np.cos(-0.5 * V * dt / self.hbar)
        
        # 更新量子态
        self.quantum_state = (psi_real, psi_imag)
        
        # 计算概率密度
        probability_density = psi_real**2 + psi_imag**2
        probability_density = probability_density / (np.sum(probability_density) + 1e-8)
        
        return (probability_density * 255).astype(np.uint8)

    # ==================== 信息熵分析模块 ====================

    def calculate_shannon_entropy(self, data):
        """计算香农熵"""
        histogram, _ = np.histogram(data, bins=256, range=(0, 255))
        prob = histogram / histogram.sum()
        prob = prob[prob > 0]  # 移除零概率
        entropy = -np.sum(prob * np.log2(prob))
        return entropy

    def calculate_quantum_entropy(self, wavefunction):
        """计算量子熵 (冯·诺依曼熵)"""
        if self.quantum_state is None:
            return 0.0
        
        psi_real, psi_imag = self.quantum_state
        density_matrix = np.outer(psi_real.flatten(), psi_real.flatten()) + \
                        np.outer(psi_imag.flatten(), psi_imag.flatten())
        
        # 计算特征值
        eigenvalues = np.linalg.eigvalsh(density_matrix)
        eigenvalues = eigenvalues[eigenvalues > 0]  # 移除零特征值
        
        # 冯·诺依曼熵: S = -Σ λ_i log λ_i
        entropy = -np.sum(eigenvalues * np.log2(eigenvalues))
        return entropy

    def calculate_mutual_information(self, frame1, frame2):
        """计算互信息"""
        gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY).flatten()
        gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY).flatten()
        
        # 联合直方图
        joint_hist, _, _ = np.histogram2d(gray1, gray2, bins=32)
        joint_prob = joint_hist / joint_hist.sum()
        
        # 边缘概率
        prob1 = np.sum(joint_prob, axis=1)
        prob2 = np.sum(joint_prob, axis=0)
        
        # 互信息: I(X;Y) = ΣΣ p(x,y) log(p(x,y)/(p(x)p(y)))
        mutual_info = 0
        for i in range(joint_prob.shape[0]):
            for j in range(joint_prob.shape[1]):
                if joint_prob[i, j] > 0 and prob1[i] > 0 and prob2[j] > 0:
                    mutual_info += joint_prob[i, j] * np.log2(joint_prob[i, j] / (prob1[i] * prob2[j]))
        
        return mutual_info

    def calculate_renyi_entropy(self, data, alpha=2):
        """计算Renyi熵 (广义熵)"""
        histogram, _ = np.histogram(data, bins=256, range=(0, 255))
        prob = histogram / histogram.sum()
        prob = prob[prob > 0]
        
        if alpha == 1:
            # Renyi熵在α=1时退化为香农熵
            return -np.sum(prob * np.log2(prob))
        else:
            return (1 / (1 - alpha)) * np.log2(np.sum(prob ** alpha))

    def entropy_based_quantum_analysis(self, frame, prev_frame=None):
        """基于信息熵的量子分析"""
        analysis = {}
        
        # 基本熵分析
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        analysis['shannon_entropy'] = self.calculate_shannon_entropy(gray)
        analysis['renyi_entropy_2'] = self.calculate_renyi_entropy(gray, alpha=2)
        
        # 量子熵
        if self.quantum_state is not None:
            quantum_entropy = self.calculate_quantum_entropy(self.quantum_state)
            analysis['quantum_entropy'] = quantum_entropy
            self.quantum_entropy_history.append(quantum_entropy)
        
        # 互信息分析
        if prev_frame is not None:
            mutual_info = self.calculate_mutual_information(frame, prev_frame)
            analysis['mutual_information'] = mutual_info
            self.mutual_info_history.append(mutual_info)
        
        # 电磁场熵分析
        if self.E_field is not None:
            Ex, Ey, Ez = self.E_field
            e_field_magnitude = np.sqrt(Ex**2 + Ey**2 + Ez**2)
            analysis['field_entropy'] = self.calculate_shannon_entropy(
                (e_field_magnitude * 1e6).astype(np.uint8)  # 缩放以便可视化
            )
        
        # 信息流分析
        analysis['information_flow'] = self.analyze_information_flow(frame)
        
        return analysis

    def analyze_information_flow(self, frame):
        """分析信息流特性"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # 使用光流法分析信息传播
        if hasattr(self, 'prev_gray'):
            # 计算光流
            flow = cv2.calcOpticalFlowFarneback(
                self.prev_gray, gray, None, 0.5, 3, 15, 3, 5, 1.2, 0
            )
            
            # 计算光流幅值作为信息流强度
            flow_magnitude = np.sqrt(flow[..., 0]**2 + flow[..., 1]**2)
            information_flow = np.mean(flow_magnitude)
        else:
            information_flow = 0.0
        
        self.prev_gray = gray.copy()
        return information_flow

    # ==================== 实时可视化模块 ====================

    def create_entropy_visualization(self, frame, analysis_results, field_energy):
        """创建信息熵和场可视化"""
        h, w = frame.shape[:2]
        
        # 创建综合显示面板
        display = np.zeros((h, w * 2, 3), dtype=np.uint8)
        
        # 左侧: 量子场叠加显示
        left_panel = frame.copy()
        
        # 叠加电磁场可视化
        field_viz = self.visualize_electromagnetic_field()
        alpha = 0.4
        left_panel = cv2.addWeighted(left_panel, 1-alpha, field_viz, alpha, 0)
        
        # 右侧: 信息熵分析显示
        right_panel = np.zeros((h, w, 3), dtype=np.uint8)
        
        # 显示分析结果
        self.display_entropy_analysis(right_panel, analysis_results, field_energy)
        
        # 绘制实时熵图表
        self.draw_entropy_charts(right_panel, h - 250)
        
        # 合并面板
        display[:, :w] = left_panel
        display[:, w:] = right_panel
        
        return display

    def visualize_electromagnetic_field(self):
        """可视化电磁场"""
        if self.E_field is None:
            return np.zeros((480, 640, 3), dtype=np.uint8)
        
        Ex, Ey, Ez = self.E_field
        Bx, By, Bz = self.B_field
        
        # 电场强度可视化
        e_magnitude = np.sqrt(Ex**2 + Ey**2 + Ez**2)
        e_normalized = (e_magnitude / (np.max(e_magnitude) + 1e-8) * 255).astype(np.uint8)
        e_viz = cv2.applyColorMap(e_normalized, cv2.COLORMAP_HOT)
        
        # 磁场可视化
        b_magnitude = np.sqrt(Bx**2 + By**2 + Bz**2)
        b_normalized = (b_magnitude / (np.max(b_magnitude) + 1e-8) * 255).astype(np.uint8)
        b_viz = cv2.applyColorMap(b_normalized, cv2.COLORMAP_COOL)
        
        # 叠加显示
        combined = cv2.addWeighted(e_viz, 0.6, b_viz, 0.4, 0)
        
        return combined

    def display_entropy_analysis(self, panel, analysis, field_energy):
        """显示熵分析结果"""
        y_offset = 30
        cv2.putText(panel, "Quantum Entropy Field Analysis", (10, y_offset), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        y_offset += 40
        
        # 熵分析参数
        entropy_params = [
            f"Shannon Entropy: {analysis.get('shannon_entropy', 0):.3f}",
            f"Renyi Entropy: {analysis.get('renyi_entropy_2', 0):.3f}",
            f"Quantum Entropy: {analysis.get('quantum_entropy', 0):.3f}",
            f"Mutual Info: {analysis.get('mutual_information', 0):.3f}",
            f"Field Entropy: {analysis.get('field_entropy', 0):.3f}",
            f"Info Flow: {analysis.get('information_flow', 0):.3f}"
        ]
        
        for param in entropy_params:
            cv2.putText(panel, param, (10, y_offset), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
            y_offset += 20
        
        y_offset += 10
        
        # 场能量参数
        field_params = [
            f"Electric Energy: {field_energy['electric_energy']:.2e}",
            f"Magnetic Energy: {field_energy['magnetic_energy']:.2e}",
            f"Total Energy: {field_energy['total_energy']:.2e}",
            f"Poynting Flux: {np.mean(field_energy['poynting_vector']):.2e}"
        ]
        
        for param in field_params:
            cv2.putText(panel, param, (10, y_offset), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 100), 1)
            y_offset += 20

    def draw_entropy_charts(self, panel, start_y):
        """绘制熵实时图表"""
        if len(self.quantum_entropy_history) < 2:
            return
        
        plot_height = 200
        plot_width = panel.shape[1] - 20
        
        if start_y + plot_height > panel.shape[0]:
            return
        
        # 创建绘图区域
        plot_area = np.zeros((plot_height, plot_width, 3), dtype=np.uint8)
        
        # 归一化数据
        def normalize_to_plot(data, height):
            if len(data) == 0:
                return []
            data_array = np.array(data)
            if np.max(data_array) - np.min(data_array) > 0:
                normalized = (data_array - np.min(data_array)) / (np.max(data_array) - np.min(data_array))
                return (height - normalized * height * 0.8).astype(int)
            return np.ones_like(data_array) * (height // 2)
        
        # 绘制量子熵曲线
        if len(self.quantum_entropy_history) > 1:
            q_entropy_plot = normalize_to_plot(self.quantum_entropy_history, plot_height)
            for i in range(1, len(q_entropy_plot)):
                x1 = int((i-1) * plot_width / len(q_entropy_plot))
                y1 = q_entropy_plot[i-1]
                x2 = int(i * plot_width / len(q_entropy_plot))
                y2 = q_entropy_plot[i]
                cv2.line(plot_area, (x1, y1), (x2, y2), (0, 255, 0), 2)
        
        # 绘制互信息曲线
        if len(self.mutual_info_history) > 1:
            mi_plot = normalize_to_plot(self.mutual_info_history, plot_height)
            for i in range(1, len(mi_plot)):
                x1 = int((i-1) * plot_width / len(mi_plot))
                y1 = mi_plot[i-1]
                x2 = int(i * plot_width / len(mi_plot))
                y2 = mi_plot[i]
                cv2.line(plot_area, (x1, y1), (x2, y2), (255, 0, 0), 2)
        
        # 添加图例
        cv2.putText(plot_area, "Quantum Entropy", (5, 15), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
        cv2.putText(plot_area, "Mutual Info", (5, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 0, 0), 1)
        
        # 添加到面板
        panel[start_y:start_y+plot_height, 10:10+plot_width] = plot_area

    # ==================== 主运行循环 ====================

    def run_entropic_sensor(self):
        """运行熵量子传感器"""
        if not self.initialize_camera():
            return
        
        self.is_running = True
        prev_frame = None
        
        print("熵量子场传感器启动...")
        print("控制按键:")
        print("  'q': 退出")
        print("  'r': 重置量子态")
        print("  'e': 导出场数据")
        
        while self.is_running:
            ret, frame = self.cap.read()
            if not ret:
                print("无法读取帧")
                break
            
            self.frame_count += 1
            
            # 初始化电磁场
            self.initialize_electromagnetic_fields(frame.shape)
            
            # 更新电磁场 (降低频率以保证实时性)
            if self.frame_count % self.field_update_frequency == 0:
                field_energy = self.update_electromagnetic_fields(frame)
            
            # QED量子演化
            qed_frame = self.quantum_electrodynamics_simulation(frame)
            
            # 信息熵分析
            entropy_analysis = self.entropy_based_quantum_analysis(frame, prev_frame)
            
            # 创建可视化
            display_frame = self.create_entropy_visualization(frame, entropy_analysis, field_energy)
            
            # 显示结果
            cv2.imshow('Entropic Quantum Field Sensor', display_frame)
            
            # 键盘控制
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('r'):
                self.quantum_state = None
                print("量子态已重置")
            elif key == ord('e'):
                self.export_field_data()
            
            prev_frame = frame.copy()
        
        self.cleanup()

    def export_field_data(self):
        """导出场数据用于进一步分析"""
        if self.E_field is not None:
            timestamp = int(time.time())
            filename = f"quantum_field_data_{timestamp}.npz"
            
            np.savez(filename,
                    E_field=self.E_field,
                    B_field=self.B_field,
                    quantum_state=self.quantum_state,
                    entropy_history=list(self.quantum_entropy_history))
            
            print(f"场数据已导出到: {filename}")

    def cleanup(self):
        """清理资源"""
        if self.cap:
            self.cap.release()
        cv2.destroyAllWindows()
        self.is_running = False
        print("熵量子场传感器已停止")

class AdvancedEntropicSensor(EntropicQuantumFieldSensor):
    """高级熵传感器，包含更多信息论和量子场论特性"""
    
    def __init__(self, camera_index=0):
        super().__init__(camera_index)
        
        # 高级参数
        self.fractal_dimension = None
        self.complexity_measure = deque(maxlen=100)
        self.quantum_discord = deque(maxlen=100)
        
    def calculate_fractal_dimension(self, image):
        """计算分形维数 (信息复杂度度量)"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # 使用盒计数法计算分形维数
        sizes = 2**np.arange(3, 8)
        counts = []
        
        for size in sizes:
            # 下采样图像
            h, w = gray.shape
            h_new, w_new = h // size, w // size
            if h_new == 0 or w_new == 0:
                continue
            
            resized = cv2.resize(gray, (w_new, h_new))
            
            # 计算非零像素数
            non_zero = np.count_nonzero(resized > 0)
            counts.append(non_zero)
        
        if len(counts) < 2:
            return 1.0
        
        # 线性拟合计算分形维数
        coeffs = np.polyfit(np.log(sizes[:len(counts)]), np.log(counts), 1)
        return -coeffs[0]  # 分形维数是斜率的负数

    def calculate_quantum_discord(self, frame1, frame2):
        """计算量子不和谐度 (量子关联度量)"""
        gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY).flatten()
        gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY).flatten()
        
        # 简化版本: 使用互信息和条件熵计算
        mutual_info = self.calculate_mutual_information(frame1, frame2)
        
        # 条件熵近似
        entropy1 = self.calculate_shannon_entropy(gray1)
        entropy2 = self.calculate_shannon_entropy(gray2)
        
        # 量子不和谐度近似
        discord = mutual_info - min(entropy1, entropy2)
        return max(0, discord)

    def advanced_entropy_analysis(self, frame, prev_frame):
        """高级熵分析"""
        analysis = super().entropy_based_quantum_analysis(frame, prev_frame)
        
        # 分形分析
        fractal_dim = self.calculate_fractal_dimension(frame)
        analysis['fractal_dimension'] = fractal_dim
        self.fractal_dimension = fractal_dim
        
        # 量子不和谐度
        if prev_frame is not None:
            discord = self.calculate_quantum_discord(frame, prev_frame)
            analysis['quantum_discord'] = discord
            self.quantum_discord.append(discord)
        
        # 复杂度测量
        complexity = analysis['shannon_entropy'] * fractal_dim
        analysis['complexity_measure'] = complexity
        self.complexity_measure.append(complexity)
        
        return analysis

def main():
    """主函数"""
    print("选择传感器模式:")
    print("1. 基础熵量子场传感器")
    print("2. 高级熵量子场传感器")
    
    choice = input("请输入选择 (1 或 2): ").strip()
    
    if choice == "1":
        sensor = EntropicQuantumFieldSensor(camera_index=0)
    elif choice == "2":
        sensor = AdvancedEntropicSensor(camera_index=0)
    else:
        print("无效选择，使用基础模式")
        sensor = EntropicQuantumFieldSensor(camera_index=0)
    
    try:
        sensor.run_entropic_sensor()
    except KeyboardInterrupt:
        print("\n用户中断模拟")
    except Exception as e:
        print(f"模拟过程中出现错误: {e}")
    finally:
        sensor.cleanup()

if __name__ == "__main__":
    main()