import numpy as np
import matplotlib
matplotlib.rc("font", family='Microsoft YaHei')
import matplotlib.pyplot as plt
from scipy.fft import fft2, ifft2, fftshift, ifftshift
from scipy import ndimage
from mpl_toolkits.mplot3d import Axes3D
import cv2
from typing import Tuple, List
import warnings
warnings.filterwarnings('ignore')

class ComputationalHolography:
    def __init__(self, resolution: Tuple[int, int] = (1024, 1024), 
                 wavelength: float = 532e-9, pixel_size: float = 8e-6):
        """
        计算全息系统初始化
        
        参数:
            resolution: 全息图分辨率 (height, width)
            wavelength: 激光波长 (米)
            pixel_size: SLM像素尺寸 (米)
        """
        self.resolution = resolution
        self.wavelength = wavelength
        self.pixel_size = pixel_size
        self.k = 2 * np.pi / wavelength  # 波数
        
        # 创建坐标网格
        self.ny, self.nx = resolution
        self.x = np.linspace(-self.nx//2, self.nx//2, self.nx) * pixel_size
        self.y = np.linspace(-self.ny//2, self.ny//2, self.ny) * pixel_size
        self.X, self.Y = np.meshgrid(self.x, self.y)
        
        # 频率空间坐标
        self.fx = np.linspace(-0.5/pixel_size, 0.5/pixel_size, self.nx)
        self.fy = np.linspace(-0.5/pixel_size, 0.5/pixel_size, self.ny)
        self.FX, self.FY = np.meshgrid(self.fx, self.fy)
        
    def angular_spectrum_propagation(self, field: np.ndarray, distance: float) -> np.ndarray:
        """
        角谱方法进行波前传播
        
        参数:
            field: 输入光场
            distance: 传播距离
            
        返回:
            传播后的光场
        """
        # 傅里叶变换到频域
        field_f = fft2(field)
        field_f = fftshift(field_f)
        
        # 传递函数
        kz = np.sqrt(self.k**2 - (2*np.pi*self.FX)**2 - (2*np.pi*self.FY)**2)
        kz = np.real(kz)  # 取实部避免数值问题
        
        # 角谱传递函数
        H = np.exp(1j * kz * distance)
        
        # 应用传递函数
        field_f_prop = field_f * H
        
        # 逆傅里叶变换回空间域
        field_f_prop = ifftshift(field_f_prop)
        field_prop = ifft2(field_f_prop)
        
        return field_prop
    
    def create_point_source(self, position: Tuple[float, float, float]) -> np.ndarray:
        """
        创建点光源的波前
        
        参数:
            position: (x, y, z) 点光源位置
            
        返回:
            点光源在全息平面的复振幅
        """
        x0, y0, z0 = position
        
        # 计算距离
        r = np.sqrt((self.X - x0)**2 + (self.Y - y0)**2 + z0**2)
        
        # 球面波
        field = np.exp(1j * self.k * r) / r
        
        return field
    
    def create_object_wavefront(self, object_points: List[Tuple[float, float, float, complex]]) -> np.ndarray:
        """
        创建三维物体的波前
        
        参数:
            object_points: 物体点列表 [(x, y, z, amplitude), ...]
            
        返回:
            物体在全息平面的总复振幅
        """
        total_field = np.zeros(self.resolution, dtype=complex)
        
        for point in object_points:
            x, y, z, amp = point
            point_field = self.create_point_source((x, y, z))
            total_field += amp * point_field
        
        return total_field
    
    def create_reference_wave(self, angle_deg: float = 5.0) -> np.ndarray:
        """
        创建参考光波前
        
        参数:
            angle_deg: 参考光入射角度 (度)
            
        返回:
            参考光波前
        """
        angle_rad = np.deg2rad(angle_deg)
        kx_ref = self.k * np.sin(angle_rad)
        
        # 平面波
        reference_wave = np.exp(1j * kx_ref * self.X)
        
        return reference_wave
    
    def compute_hologram(self, object_field: np.ndarray, reference_field: np.ndarray) -> np.ndarray:
        """
        计算全息图
        
        参数:
            object_field: 物光波前
            reference_field: 参考光波前
            
        返回:
            全息图强度分布
        """
        # 干涉图样
        interference = object_field + reference_field
        hologram = np.abs(interference)**2
        
        # 归一化到0-255
        hologram_normalized = (hologram - hologram.min()) / (hologram.max() - hologram.min()) * 255
        
        return hologram_normalized.astype(np.uint8)
    
    def reconstruct_hologram(self, hologram: np.ndarray, reference_field: np.ndarray, 
                           reconstruction_distance: float) -> np.ndarray:
        """
        全息图重建
        
        参数:
            hologram: 全息图
            reference_field: 重建用的参考光
            reconstruction_distance: 重建距离
            
        返回:
            重建图像
        """
        # 全息图乘以参考光
        reconstruction_field = hologram.astype(complex) * reference_field
        
        # 传播到重建平面
        reconstructed_field = self.angular_spectrum_propagation(reconstruction_field, reconstruction_distance)
        
        # 计算强度
        reconstruction_intensity = np.abs(reconstructed_field)**2
        
        return reconstruction_intensity
    
    def gerchberg_saxton_algorithm(self, target_amplitude: np.ndarray, 
                                 iterations: int = 50, distance: float = 0.1) -> np.ndarray:
        """
        Gerchberg-Saxton算法计算相位全息图
        
        参数:
            target_amplitude: 目标振幅分布
            iterations: 迭代次数
            distance: 传播距离
            
        返回:
            相位全息图
        """
        # 初始化随机相位
        phase = 2 * np.pi * np.random.random(self.resolution)
        complex_field = target_amplitude * np.exp(1j * phase)
        
        for i in range(iterations):
            # 传播到全息图平面
            hologram_field = self.angular_spectrum_propagation(complex_field, distance)
            
            # 在全息图平面保持相位，振幅设为1
            hologram_phase = np.angle(hologram_field)
            hologram_field = np.exp(1j * hologram_phase)
            
            # 传播回目标平面
            reconstructed_field = self.angular_spectrum_propagation(hologram_field, -distance)
            
            # 在目标平面保持计算得到的振幅，替换为原始相位
            reconstructed_phase = np.angle(reconstructed_field)
            complex_field = target_amplitude * np.exp(1j * reconstructed_phase)
            
            if i % 10 == 0:
                error = np.mean(np.abs(np.abs(reconstructed_field) - target_amplitude))
                print(f"Iteration {i}, Error: {error:.4f}")
        
        # 返回相位全息图
        final_hologram_field = self.angular_spectrum_propagation(complex_field, distance)
        phase_hologram = np.angle(final_hologram_field)
        
        return phase_hologram

def create_3d_object() -> List[Tuple[float, float, float, complex]]:
    """
    创建示例三维物体
    """
    object_points = []
    
    # 创建字母'H'的点云
    # 竖线1
    for z in [-0.01, 0, 0.01]:
        for y in np.linspace(-0.005, 0.005, 20):
            object_points.append((-0.004, y, z, 1.0))
    
    # 竖线2
    for z in [-0.01, 0, 0.01]:
        for y in np.linspace(-0.005, 0.005, 20):
            object_points.append((0.004, y, z, 1.0))
    
    # 横线
    for z in [-0.01, 0, 0.01]:
        for x in np.linspace(-0.004, 0.004, 30):
            object_points.append((x, 0, z, 1.0))
    
    return object_points

def visualize_results(hologram: np.ndarray, reconstruction: np.ndarray, 
                     object_points: List[Tuple[float, float, float, complex]]):
    """
    可视化结果
    """
    fig = plt.figure(figsize=(20, 10))
    
    # 3D物体可视化
    ax1 = fig.add_subplot(231, projection='3d')
    points_array = np.array(object_points)
    ax1.scatter(points_array[:, 0], points_array[:, 1], points_array[:, 2], 
               c=points_array[:, 3].real, cmap='viridis')
    ax1.set_title('3D Object Points')
    ax1.set_xlabel('X')
    ax1.set_ylabel('Y')
    ax1.set_zlabel('Z')
    
    # 全息图
    ax2 = fig.add_subplot(232)
    ax2.imshow(hologram, cmap='gray')
    ax2.set_title('Computer Generated Hologram')
    ax2.axis('off')
    
    # 重建结果
    ax3 = fig.add_subplot(233)
    ax3.imshow(reconstruction, cmap='hot')
    ax3.set_title('Hologram Reconstruction')
    ax3.axis('off')
    
    # 全息图傅里叶频谱
    ax4 = fig.add_subplot(234)
    hologram_spectrum = np.log(np.abs(fftshift(fft2(hologram))) + 1)
    ax4.imshow(hologram_spectrum, cmap='viridis')
    ax4.set_title('Hologram Fourier Spectrum')
    ax4.axis('off')
    
    # 相位分布
    ax5 = fig.add_subplot(235)
    phase_hologram = np.angle(fft2(hologram))
    ax5.imshow(phase_hologram, cmap='hsv')
    ax5.set_title('Hologram Phase')
    ax5.axis('off')
    
    # 重建强度剖面
    ax6 = fig.add_subplot(236)
    center_line = reconstruction[reconstruction.shape[0]//2, :]
    ax6.plot(center_line)
    ax6.set_title('Reconstruction Intensity Profile')
    ax6.set_xlabel('Pixel')
    ax6.set_ylabel('Intensity')
    
    plt.tight_layout()
    plt.show()

def main():
    """
    主函数 - 演示完整计算全息流程
    """
    print("=== 计算全息系统启动 ===")
    
    # 初始化全息系统
    cgh = ComputationalHolography(resolution=(512, 512), wavelength=532e-9, pixel_size=8e-6)
    
    # 创建3D物体
    print("创建3D物体...")
    object_points = create_3d_object()
    
    # 计算物体波前
    print("计算物体波前...")
    object_field = cgh.create_object_wavefront(object_points)
    
    # 创建参考光
    print("创建参考光...")
    reference_wave = cgh.create_reference_wave(angle_deg=3.0)
    
    # 计算全息图
    print("计算全息图...")
    hologram = cgh.compute_hologram(object_field, reference_wave)
    
    # 全息图重建
    print("全息图重建...")
    reconstruction = cgh.reconstruct_hologram(hologram, reference_wave, reconstruction_distance=0.1)
    
    # Gerchberg-Saxton算法示例
    print("\n=== Gerchberg-Saxton算法相位恢复 ===")
    # 创建目标图像
    target_image = np.zeros(cgh.resolution)
    target_image[200:300, 200:300] = 1.0  # 方形目标
    
    # 运行GS算法
    phase_hologram = cgh.gerchberg_saxton_algorithm(target_image, iterations=30, distance=0.05)
    
    # 可视化GS算法结果
    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(15, 5))
    ax1.imshow(target_image, cmap='gray')
    ax1.set_title('Target Image')
    ax1.axis('off')
    
    ax2.imshow(phase_hologram, cmap='hsv')
    ax2.set_title('Phase Hologram (GS Algorithm)')
    ax2.axis('off')
    
    # 重建GS全息图
    gs_reconstruction = cgh.reconstruct_hologram(np.exp(1j * phase_hologram), 
                                               np.ones_like(phase_hologram), 0.05)
    ax3.imshow(gs_reconstruction, cmap='hot')
    ax3.set_title('GS Reconstruction')
    ax3.axis('off')
    
    plt.tight_layout()
    plt.show()
    
    # 可视化主要结果
    print("生成可视化结果...")
    visualize_results(hologram, reconstruction, object_points)
    
    # 保存结果
    cv2.imwrite('computer_generated_hologram.png', hologram)
    cv2.imwrite('hologram_reconstruction.png', (reconstruction / reconstruction.max() * 255).astype(np.uint8))
    
    print("=== 计算完成 ===")
    print("全息图已保存为 'computer_generated_hologram.png'")
    print("重建图像已保存为 'hologram_reconstruction.png'")

if __name__ == "__main__":
    main()