import cv2
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from scipy import ndimage
import time
from collections import deque

class QuantumSensorSimulator:
    def __init__(self, camera_index=0):
        """
        量子传感器模拟器初始化
        
        参数:
            camera_index: 摄像头索引 (默认0)
        """
        self.camera_index = camera_index
        self.cap = None
        self.is_running = False
        
        # 量子传感器参数
        self.quantum_noise_level = 0.1
        self.entanglement_factor = 0.5
        self.superposition_states = 3
        self.decoherence_rate = 0.05
        
        # 数据分析参数
        self.wave_function_amplitude = None
        self.quantum_coherence = None
        self.entanglement_correlation = None
        
        # 历史数据存储
        self.energy_history = deque(maxlen=100)
        self.coherence_history = deque(maxlen=100)
        self.correlation_history = deque(maxlen=100)
        
    def initialize_camera(self):
        """初始化摄像头"""
        try:
            self.cap = cv2.VideoCapture(self.camera_index)
            if not self.cap.isOpened():
                raise Exception("无法打开摄像头")
            
            # 设置摄像头参数
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.cap.set(cv2.CAP_PROP_FPS, 30)
            
            print("摄像头初始化成功")
            return True
            
        except Exception as e:
            print(f"摄像头初始化失败: {e}")
            return False
    
    def quantum_wave_function(self, frame):
        """
        模拟量子波函数
        将图像转换为波函数表示
        """
        # 转换为灰度图
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # 归一化
        normalized = gray.astype(np.float32) / 255.0
        
        # 应用傅里叶变换模拟波函数
        f_transform = np.fft.fft2(normalized)
        f_shift = np.fft.fftshift(f_transform)
        
        # 计算波函数振幅
        magnitude_spectrum = np.abs(f_shift)
        phase_spectrum = np.angle(f_shift)
        
        return magnitude_spectrum, phase_spectrum, f_shift
    
    def apply_quantum_noise(self, frame):
        """
        应用量子噪声
        模拟量子测量过程中的不确定性
        """
        # 生成量子噪声
        noise = np.random.normal(0, self.quantum_noise_level, frame.shape[:2])
        noise = np.stack([noise] * 3, axis=-1)
        
        # 应用噪声
        noisy_frame = frame.astype(np.float32) / 255.0
        noisy_frame = np.clip(noisy_frame + noise * 0.1, 0, 1)
        
        return (noisy_frame * 255).astype(np.uint8)
    
    def simulate_entanglement(self, frame1, frame2=None):
        """
        模拟量子纠缠效应
        如果提供两个帧，模拟它们之间的纠缠关系
        """
        if frame2 is None:
            # 单帧纠缠 - 模拟内部量子态纠缠
            lab = cv2.cvtColor(frame1, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            
            # 纠缠通道之间的相关性
            entangled = (a.astype(np.float32) * self.entanglement_factor + 
                        b.astype(np.float32) * (1 - self.entanglement_factor))
            
            return entangled.astype(np.uint8)
        else:
            # 双帧纠缠 - 模拟两个量子系统之间的纠缠
            gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
            gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)
            
            # 计算相关性作为纠缠度量
            correlation = np.corrcoef(gray1.flatten(), gray2.flatten())[0, 1]
            self.entanglement_correlation = correlation
            
            return correlation
    
    def quantum_measurement(self, frame):
        """
        模拟量子测量过程
        包括波函数坍缩和测量不确定性
        """
        # 波函数坍缩模拟
        collapsed = self.apply_wavefunction_collapse(frame)
        
        # 测量不确定性
        measured = self.apply_measurement_uncertainty(collapsed)
        
        return measured
    
    def apply_wavefunction_collapse(self, frame):
        """
        应用波函数坍缩
        模拟量子态在测量时的坍缩过程
        """
        # 多尺度分析模拟不同测量基
        scales = []
        current = frame.astype(np.float32)
        
        for i in range(self.superposition_states):
            # 高斯金字塔下采样
            current = cv2.pyrDown(current)
            scales.append(current)
        
        # 重建过程模拟坍缩
        collapsed = scales[-1]
        for i in range(len(scales)-2, -1, -1):
            collapsed = cv2.pyrUp(collapsed)
            h, w = scales[i].shape[:2]
            collapsed = cv2.resize(collapsed, (w, h))
        
        return collapsed.astype(np.uint8)
    
    def apply_measurement_uncertainty(self, frame):
        """
        应用测量不确定性
        模拟海森堡不确定性原理
        """
        # 位置-动量不确定性关系模拟
        uncertainty = np.random.random(frame.shape[:2]) * self.decoherence_rate
        
        # 应用不确定性到图像
        uncertain_frame = frame.astype(np.float32)
        uncertain_frame += uncertain_frame * uncertainty[..., np.newaxis]
        
        return np.clip(uncertain_frame, 0, 255).astype(np.uint8)
    
    def analyze_quantum_properties(self, frame):
        """
        分析量子特性
        计算各种量子力学参数
        """
        # 计算能量谱（强度分布）
        energy = np.mean(frame.astype(np.float32) ** 2)
        self.energy_history.append(energy)
        
        # 计算量子相干性
        magnitude, phase, f_shift = self.quantum_wave_function(frame)
        coherence = np.std(magnitude) / (np.mean(magnitude) + 1e-8)
        self.coherence_history.append(coherence)
        
        # 更新相关性历史
        if self.entanglement_correlation is not None:
            self.correlation_history.append(self.entanglement_correlation)
        
        return {
            'energy': energy,
            'coherence': coherence,
            'entanglement': self.entanglement_correlation
        }
    
    def visualize_quantum_data(self, frame, quantum_data):
        """
        可视化量子数据和分析结果
        """
        # 创建显示图像
        display_frame = frame.copy()
        
        # 添加量子数据叠加
        height, width = display_frame.shape[:2]
        
        # 创建信息面板
        info_panel = np.zeros((height, 300, 3), dtype=np.uint8)
        
        # 显示量子参数
        y_offset = 30
        cv2.putText(info_panel, "Quantum Sensor Data", (10, y_offset), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
        y_offset += 30
        
        params = [
            f"Energy: {quantum_data['energy']:.2f}",
            f"Coherence: {quantum_data['coherence']:.4f}",
            f"Entanglement: {quantum_data['entanglement']:.4f}" if quantum_data['entanglement'] else "Entanglement: N/A",
            f"Noise Level: {self.quantum_noise_level:.2f}",
            f"Decoherence: {self.decoherence_rate:.2f}"
        ]
        
        for param in params:
            cv2.putText(info_panel, param, (10, y_offset), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
            y_offset += 20
        
        # 绘制实时图表
        self.draw_realtime_plots(info_panel, height - 150)
        
        # 合并显示
        combined = np.hstack([display_frame, info_panel])
        
        return combined
    
    def draw_realtime_plots(self, panel, start_y):
        """在信息面板上绘制实时数据图表"""
        if len(self.energy_history) < 2:
            return
        
        plot_height = 120
        plot_width = 280
        
        # 创建绘图区域
        plot_area = np.zeros((plot_height, plot_width, 3), dtype=np.uint8)
        
        # 归一化数据
        def normalize_data(data):
            if len(data) == 0:
                return []
            data_array = np.array(data)
            if np.max(data_array) - np.min(data_array) > 0:
                return (data_array - np.min(data_array)) / (np.max(data_array) - np.min(data_array))
            return np.zeros_like(data_array)
        
        # 绘制能量曲线 (红色)
        energy_norm = normalize_data(self.energy_history)
        for i in range(1, len(energy_norm)):
            x1 = int((i-1) * plot_width / len(energy_norm))
            y1 = int(plot_height - energy_norm[i-1] * plot_height * 0.8)
            x2 = int(i * plot_width / len(energy_norm))
            y2 = int(plot_height - energy_norm[i] * plot_height * 0.8)
            cv2.line(plot_area, (x1, y1), (x2, y2), (0, 0, 255), 1)
        
        # 绘制相干性曲线 (绿色)
        coherence_norm = normalize_data(self.coherence_history)
        for i in range(1, len(coherence_norm)):
            x1 = int((i-1) * plot_width / len(coherence_norm))
            y1 = int(plot_height - coherence_norm[i-1] * plot_height * 0.8)
            x2 = int(i * plot_width / len(coherence_norm))
            y2 = int(plot_height - coherence_norm[i] * plot_height * 0.8)
            cv2.line(plot_area, (x1, y1), (x2, y2), (0, 255, 0), 1)
        
        # 将绘图区域添加到面板
        panel[start_y:start_y+plot_height, 10:10+plot_width] = plot_area
        
        # 添加图例
        cv2.putText(panel, "Energy", (15, start_y + 15), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.3, (0, 0, 255), 1)
        cv2.putText(panel, "Coherence", (15, start_y + 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.3, (0, 255, 0), 1)
    
    def run_simulation(self):
        """运行量子传感器模拟"""
        if not self.initialize_camera():
            return
        
        self.is_running = True
        prev_frame = None
        
        print("开始量子传感器模拟...")
        print("按 'q' 退出, 'n' 调整噪声水平, 'd' 调整退相干率")
        
        while self.is_running:
            ret, frame = self.cap.read()
            if not ret:
                print("无法读取帧")
                break
            
            # 量子传感器处理流程
            # 1. 应用量子噪声
            quantum_frame = self.apply_quantum_noise(frame)
            
            # 2. 模拟量子测量
            measured_frame = self.quantum_measurement(quantum_frame)
            
            # 3. 模拟量子纠缠
            if prev_frame is not None:
                entanglement = self.simulate_entanglement(frame, prev_frame)
            else:
                entanglement = self.simulate_entanglement(frame)
            
            # 4. 分析量子特性
            quantum_data = self.analyze_quantum_properties(frame)
            
            # 5. 可视化结果
            display_frame = self.visualize_quantum_data(measured_frame, quantum_data)
            
            # 显示结果
            cv2.imshow('Quantum Sensor Simulation', display_frame)
            
            # 键盘控制
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('n'):
                self.quantum_noise_level = min(1.0, self.quantum_noise_level + 0.05)
            elif key == ord('m'):
                self.quantum_noise_level = max(0.0, self.quantum_noise_level - 0.05)
            elif key == ord('d'):
                self.decoherence_rate = min(0.5, self.decoherence_rate + 0.02)
            elif key == ord('c'):
                self.decoherence_rate = max(0.0, self.decoherence_rate - 0.02)
            
            prev_frame = frame.copy()
        
        self.cleanup()
    
    def cleanup(self):
        """清理资源"""
        if self.cap:
            self.cap.release()
        cv2.destroyAllWindows()
        self.is_running = False
        print("量子传感器模拟已停止")

def main():
    """主函数"""
    # 创建量子传感器模拟器
    quantum_simulator = QuantumSensorSimulator(camera_index=0)
    
    try:
        # 运行模拟
        quantum_simulator.run_simulation()
    except KeyboardInterrupt:
        print("\n用户中断模拟")
    except Exception as e:
        print(f"模拟过程中出现错误: {e}")
    finally:
        quantum_simulator.cleanup()

if __name__ == "__main__":
    main()