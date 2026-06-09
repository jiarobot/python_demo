import numpy as np
import matplotlib
matplotlib.rc("font", family='Microsoft YaHei')
import matplotlib.pyplot as plt
from scipy.optimize import minimize
from scipy import linalg
import cv2
import time
from collections import deque

class QuantumOpticalFieldImaging:
    def __init__(self, resolution=64, compression_ratio=0.3):
        """
        量子光学场成像系统
        
        参数:
            resolution: 成像分辨率
            compression_ratio: 压缩感知采样率
        """
        self.resolution = resolution
        self.compression_ratio = compression_ratio
        self.num_measurements = int(resolution * resolution * compression_ratio)
        
        # 生成测量矩阵 (模拟DMD模式)
        self.measurement_matrix = self._generate_measurement_matrix()
        
        # 量子态参数
        self.alpha = 0.5  # 相干态参数
        self.phase = 0.0  # 相位
        
        # 实时显示缓冲区
        self.image_buffer = deque(maxlen=10)
        
    def _generate_measurement_matrix(self):
        """生成哈达玛测量矩阵"""
        n = self.resolution * self.resolution
        m = self.num_measurements
        
        # 使用部分哈达玛矩阵
        hadamard = self._partial_hadamard(m, n)
        return hadamard
    
    def _partial_hadamard(self, m, n):
        """生成部分哈达玛矩阵"""
        # 简化的哈达玛矩阵生成
        H = np.random.choice([-1, 1], size=(m, n))
        H = H / np.sqrt(m)
        return H
    
    def _quantum_coherent_state(self, x, y):
        """
        生成量子相干态的光学场分布
        基于量子谐振子波函数
        """
        x_norm = (x - self.resolution/2) / (self.resolution/4)
        y_norm = (y - self.resolution/2) / (self.resolution/4)
        
        r2 = x_norm**2 + y_norm**2
        
        # 相干态波函数
        psi = np.exp(-r2/2 + self.alpha * (x_norm + 1j*y_norm) - 
                    np.abs(self.alpha)**2/2)
        
        return np.abs(psi)**2  # 概率密度
    
    def simulate_optical_field(self):
        """模拟量子光学场"""
        field = np.zeros((self.resolution, self.resolution))
        
        for i in range(self.resolution):
            for j in range(self.resolution):
                field[i, j] = self._quantum_coherent_state(i, j)
        
        # 添加量子噪声
        field += 0.01 * np.random.poisson(lam=1, size=field.shape)
        
        return field / np.max(field)
    
    def compress_sensing_measurement(self, optical_field):
        """压缩感知测量过程"""
        field_vector = optical_field.flatten()
        measurements = self.measurement_matrix @ field_vector
        
        # 添加测量噪声
        measurements += 0.01 * np.random.randn(len(measurements))
        
        return measurements
    
    def total_variation_minimization(self, measurements):
        """全变分最小化重构算法"""
        def tv_norm(x):
            """计算全变分范数"""
            img = x.reshape(self.resolution, self.resolution)
            dx = np.diff(img, axis=0)
            dy = np.diff(img, axis=1)
            return np.sum(np.abs(dx)) + np.sum(np.abs(dy))
        
        def objective(x):
            """优化目标函数"""
            data_fidelity = 0.5 * np.sum((self.measurement_matrix @ x - measurements)**2)
            tv_penalty = 0.1 * tv_norm(x)
            return data_fidelity + tv_penalty
        
        # 初始化
        x0 = self.measurement_matrix.T @ measurements
        
        # 使用L-BFGS优化
        result = minimize(objective, x0, method='L-BFGS-B', 
                         bounds=[(0, 1)] * len(x0),
                         options={'maxiter': 50, 'disp': False})
        
        return result.x.reshape(self.resolution, self.resolution)
    
    def wigner_function_reconstruction(self, optical_field):
        """
        Wigner函数重构 - 量子相空间表示
        这是量子光学中的核心概念
        """
        # 傅里叶变换到动量空间
        momentum_field = np.fft.fftshift(np.fft.fft2(np.fft.ifftshift(optical_field)))
        
        # 计算Wigner函数 (简化版本)
        wigner = np.zeros((self.resolution, self.resolution), dtype=complex)
        
        for i in range(self.resolution):
            for j in range(self.resolution):
                # Wigner函数的简化计算
                shift_x = i - self.resolution // 2
                shift_y = j - self.resolution // 2
                
                # 位移后的场
                shifted_field = np.roll(optical_field, (shift_x, shift_y), axis=(0, 1))
                
                # Wigner函数值
                wigner[i, j] = np.sum(optical_field * np.conj(shifted_field))
        
        return np.abs(wigner)
    
    def real_time_processing(self, duration=30):
        """实时处理循环"""
        print("开始量子光学场实时成像...")
        print("按 'q' 退出，按 'r' 重置相位")
        
        start_time = time.time()
        frame_count = 0
        
        plt.ion()
        fig, axes = plt.subplots(2, 2, figsize=(12, 10))
        
        while time.time() - start_time < duration:
            # 更新量子态参数 (模拟交互)
            self.phase += 0.1
            self.alpha = 0.5 + 0.2 * np.sin(time.time() * 0.5)
            
            # 生成光学场
            optical_field = self.simulate_optical_field()
            
            # 压缩测量
            measurements = self.compress_sensing_measurement(optical_field)
            
            # 重构图像
            reconstructed = self.total_variation_minimization(measurements)
            
            # 计算Wigner函数
            wigner = self.wigner_function_reconstruction(optical_field)
            
            # 更新显示
            self._update_display(axes, optical_field, reconstructed, 
                               wigner, measurements, frame_count)
            
            frame_count += 1
            
            # 处理键盘输入
            if plt.waitforbuttonpress(0.001):
                key = plt.gcf().canvas.get_tlw().key
                if key == 'q':
                    break
                elif key == 'r':
                    self.phase = 0.0
            
            time.sleep(0.05)  # 控制帧率
        
        plt.ioff()
        plt.show()
        
        fps = frame_count / duration
        print(f"平均帧率: {fps:.2f} FPS")
    
    def _update_display(self, axes, optical_field, reconstructed, wigner, measurements, frame_count):
        """更新实时显示"""
        for ax in axes.flat:
            ax.clear()
        
        # 原始光学场
        axes[0, 0].imshow(optical_field, cmap='hot', interpolation='nearest')
        axes[0, 0].set_title('量子光学场')
        axes[0, 0].axis('off')
        
        # 重构图像
        axes[0, 1].imshow(reconstructed, cmap='hot', interpolation='nearest')
        axes[0, 1].set_title('压缩感知重构')
        axes[0, 1].axis('off')
        
        # Wigner函数
        axes[1, 0].imshow(wigner, cmap='seismic', interpolation='nearest')
        axes[1, 0].set_title('Wigner函数 (量子相空间)')
        axes[1, 0].axis('off')
        
        # 测量值
        axes[1, 1].plot(measurements)
        axes[1, 1].set_title(f'压缩测量值 (采样率: {self.compression_ratio*100:.1f}%)')
        axes[1, 1].set_xlabel('测量索引')
        axes[1, 1].set_ylabel('测量值')
        
        plt.suptitle(f'量子光学场实时成像 - 帧: {frame_count}')
        plt.tight_layout()
        plt.draw()

class InteractiveQuantumField:
    """交互式量子场控制类"""
    
    def __init__(self, imaging_system):
        self.imaging_system = imaging_system
        self.setup_interaction()
    
    def setup_interaction(self):
        """设置交互参数"""
        self.interaction_strength = 0.1
        self.perturbation_center = [0.5, 0.5]  # 归一化坐标
    
    def apply_quantum_perturbation(self, position, strength):
        """
        应用量子扰动
        模拟用户与量子场的交互
        """
        x_norm, y_norm = position
        
        # 更新相干态参数
        self.imaging_system.alpha += strength * 0.1
        self.imaging_system.phase += strength * 0.05
        
        # 创建局部扰动
        perturbation = self._create_gaussian_perturbation(x_norm, y_norm, strength)
        return perturbation
    
    def _create_gaussian_perturbation(self, x_center, y_center, strength):
        """创建高斯型扰动"""
        perturbation = np.zeros((self.imaging_system.resolution, 
                               self.imaging_system.resolution))
        
        for i in range(self.imaging_system.resolution):
            for j in range(self.imaging_system.resolution):
                x = i / self.imaging_system.resolution
                y = j / self.imaging_system.resolution
                
                distance = np.sqrt((x - x_center)**2 + (y - y_center)**2)
                perturbation[i, j] = strength * np.exp(-distance**2 / 0.1)
        
        return perturbation

def main():
    """主函数"""
    print("=" * 60)
    print("量子光学场实时成像与交互系统")
    print("基于压缩感知和量子光学原理的全新视觉应用")
    print("=" * 60)
    
    # 创建成像系统
    qof_imaging = QuantumOpticalFieldImaging(resolution=64, compression_ratio=0.3)
    
    # 创建交互系统
    interactive_system = InteractiveQuantumField(qof_imaging)
    
    # 开始实时处理
    try:
        qof_imaging.real_time_processing(duration=30)
    except KeyboardInterrupt:
        print("\n程序被用户中断")
    except Exception as e:
        print(f"运行时错误: {e}")
    
    print("量子光学场成像系统结束运行")

if __name__ == "__main__":
    main()