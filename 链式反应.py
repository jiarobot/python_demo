import cv2
import numpy as np
import matplotlib
matplotlib.rc("font", family='Microsoft YaHei')
import matplotlib.pyplot as plt
from scipy import ndimage
import time

class VisualChainReaction:
    def __init__(self):
        self.chain_levels = []
        self.fusion_weights = []
        
    def load_image(self, image_path):
        """加载图像并进行基础预处理"""
        self.original = cv2.imread(image_path)
        if self.original is None:
            raise ValueError(f"无法加载图像: {image_path}")
        
        # 转换为RGB和灰度图
        self.rgb = cv2.cvtColor(self.original, cv2.COLOR_BGR2RGB)
        self.gray = cv2.cvtColor(self.original, cv2.COLOR_BGR2GRAY)
        
        print(f"图像加载成功: {self.original.shape}")
        return self.rgb
    
    def create_quantum_kernel(self, size=5, intensity=1.0):
        """创建量子化卷积核，模拟视觉冲击效应"""
        kernel = np.zeros((size, size))
        center = size // 2
        
        for i in range(size):
            for j in range(size):
                distance = np.sqrt((i - center)**2 + (j - center)**2)
                # 量子化效应：距离中心越近，权重呈指数增长
                kernel[i, j] = np.exp(-distance**2 / (2 * (intensity**2)))
        
        return kernel / np.sum(kernel)
    
    def level_1_edge_amplification(self, image, threshold1=50, threshold2=150):
        """第一级：边缘增强与量子化"""
        # Canny边缘检测
        edges = cv2.Canny(image, threshold1, threshold2)
        
        # 量子化卷积增强
        quantum_kernel = self.create_quantum_kernel(7, 1.5)
        enhanced_edges = cv2.filter2D(edges.astype(np.float32), -1, quantum_kernel)
        
        # 边缘膨胀强化
        kernel = np.ones((3, 3), np.uint8)
        dilated_edges = cv2.dilate(enhanced_edges.astype(np.uint8), kernel, iterations=1)
        
        # 与原图融合
        result = cv2.addWeighted(image, 0.7, 
                               cv2.cvtColor(dilated_edges, cv2.COLOR_GRAY2RGB), 0.3, 0)
        
        self.chain_levels.append(('边缘量子化增强', result))
        return result
    
    def level_2_frequency_breakthrough(self, image, alpha=1.5, beta=0.5):
        """第二级：频率域突破"""
        # 傅里叶变换
        f = np.fft.fft2(image, axes=(0, 1))
        f_shift = np.fft.fftshift(f)
        
        # 创建频率增强掩码
        rows, cols, ch = image.shape
        crow, ccol = rows // 2, cols // 2
        
        # 高频增强，低频保持
        mask = np.ones((rows, cols, ch))
        for c in range(ch):
            # 创建带通滤波器
            for i in range(rows):
                for j in range(cols):
                    distance = np.sqrt((i - crow)**2 + (j - ccol)**2)
                    if 30 < distance < min(rows, cols) // 3:
                        mask[i, j, c] = alpha  # 增强中高频
                    elif distance < 10:
                        mask[i, j, c] = beta   # 减弱极低频
        
        # 应用频率增强
        f_shift_enhanced = f_shift * mask
        
        # 逆傅里叶变换
        f_ishift = np.fft.ifftshift(f_shift_enhanced)
        img_back = np.fft.ifft2(f_ishift, axes=(0, 1))
        img_back = np.abs(img_back).astype(np.uint8)
        
        self.chain_levels.append(('频率域突破', img_back))
        return img_back
    
    def level_3_neural_activation(self, image, intensity=0.8):
        """第三级：神经激活模拟"""
        # 分离通道进行独立处理
        b, g, r = cv2.split(image)
        
        # 模拟视觉神经的激活函数
        def neural_activation(channel, intensity):
            # S型激活函数增强对比度
            channel_norm = channel.astype(np.float32) / 255.0
            activated = 1 / (1 + np.exp(-intensity * (channel_norm - 0.5)))
            return (activated * 255).astype(np.uint8)
        
        b_activated = neural_activation(b, intensity)
        g_activated = neural_activation(g, intensity + 0.1)  # 绿色通道稍微不同
        r_activated = neural_activation(r, intensity - 0.1)  # 红色通道稍微不同
        
        # 合并通道
        result = cv2.merge([b_activated, g_activated, r_activated])
        
        # 添加微光晕效果
        glow = cv2.GaussianBlur(result, (15, 15), 0)
        result = cv2.addWeighted(result, 0.85, glow, 0.15, 0)
        
        self.chain_levels.append(('神经激活增强', result))
        return result
    
    def level_4_quantum_resonance(self, image, resonance_factor=1.2):
        """第四级：量子共振效应"""
        # Lab颜色空间转换
        lab = cv2.cvtColor(image, cv2.COLOR_RGB2LAB)
        l, a, b = cv2.split(lab)
        
        # 量子共振：增强颜色对比和细节
        l_enhanced = cv2.equalizeHist(l)
        
        # 幅度共振增强
        a_resonance = a.astype(np.float32)
        b_resonance = b.astype(np.float32)
        
        # 应用共振函数
        a_resonance = 128 + (a_resonance - 128) * resonance_factor
        b_resonance = 128 + (b_resonance - 128) * resonance_factor
        
        a_resonance = np.clip(a_resonance, 0, 255).astype(np.uint8)
        b_resonance = np.clip(b_resonance, 0, 255).astype(np.uint8)
        
        # 合并LAB通道
        lab_resonance = cv2.merge([l_enhanced, a_resonance, b_resonance])
        result = cv2.cvtColor(lab_resonance, cv2.COLOR_LAB2RGB)
        
        self.chain_levels.append(('量子共振', result))
        return result
    
    def level_5_temporal_fusion(self, image, memory_decay=0.7):
        """第五级：时序融合与记忆效应"""
        if len(self.chain_levels) < 4:
            return image
        
        # 获取前几级的结果进行时序融合
        previous_results = [level[1] for level in self.chain_levels[-4:]]
        
        # 应用记忆衰减权重
        weights = [memory_decay ** i for i in range(len(previous_results)-1, -1, -1)]
        total_weight = sum(weights)
        
        # 加权融合
        result = np.zeros_like(image, dtype=np.float32)
        for img, weight in zip(previous_results, weights):
            result += img.astype(np.float32) * weight
        
        result = (result / total_weight).astype(np.uint8)
        
        self.chain_levels.append(('时序融合', result))
        return result
    
    def execute_chain_reaction(self, image_path, show_process=True):
        """执行完整的链式反应视觉处理"""
        print("开始链式反应视觉处理...")
        
        # 加载图像
        self.load_image(image_path)
        current_image = self.rgb.copy()
        
        # 执行各级处理
        levels = [
            self.level_1_edge_amplification,
            self.level_2_frequency_breakthrough,
            self.level_3_neural_activation,
            self.level_4_quantum_resonance,
            self.level_5_temporal_fusion
        ]
        
        for i, level_func in enumerate(levels, 1):
            print(f"执行第 {i} 级处理...")
            start_time = time.time()
            
            current_image = level_func(current_image)
            
            elapsed = time.time() - start_time
            print(f"第 {i} 级完成，耗时: {elapsed:.2f}秒")
        
        # 最终融合优化
        final_result = self.final_optimization(current_image)
        self.chain_levels.append(('最终优化', final_result))
        
        if show_process:
            self.visualize_process()
        
        return final_result
    
    def final_optimization(self, image):
        """最终优化处理"""
        # 自适应对比度增强
        lab = cv2.cvtColor(image, cv2.COLOR_RGB2LAB)
        l, a, b = cv2.split(lab)
        
        # CLAHE对比度限制自适应直方图均衡化
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        l_enhanced = clahe.apply(l)
        
        lab_enhanced = cv2.merge([l_enhanced, a, b])
        result = cv2.cvtColor(lab_enhanced, cv2.COLOR_LAB2RGB)
        
        # 最终锐化
        kernel = np.array([[-1, -1, -1],
                          [-1,  9, -1],
                          [-1, -1, -1]])
        result = cv2.filter2D(result, -1, kernel)
        
        return result
    
    def visualize_process(self):
        """可视化处理过程"""
        n_levels = len(self.chain_levels)
        fig, axes = plt.subplots(2, (n_levels + 1) // 2, figsize=(20, 10))
        axes = axes.flatten()
        
        # 显示原图
        axes[0].imshow(self.rgb)
        axes[0].set_title('原始图像')
        axes[0].axis('off')
        
        # 显示各级处理结果
        for i, (name, img) in enumerate(self.chain_levels, 1):
            if i < len(axes):
                axes[i].imshow(img)
                axes[i].set_title(f'Level {i}: {name}')
                axes[i].axis('off')
        
        # 隐藏多余的子图
        for i in range(n_levels + 1, len(axes)):
            axes[i].axis('off')
        
        plt.tight_layout()
        plt.show()
    
    def save_results(self, output_dir="output/"):
        """保存处理结果"""
        import os
        os.makedirs(output_dir, exist_ok=True)
        
        # 保存原图
        cv2.imwrite(f"{output_dir}original.jpg", 
                   cv2.cvtColor(self.rgb, cv2.COLOR_RGB2BGR))
        
        # 保存各级处理结果
        for i, (name, img) in enumerate(self.chain_levels, 1):
            cv2.imwrite(f"{output_dir}level_{i}_{name}.jpg", 
                       cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
        
        print(f"所有结果已保存到: {output_dir}")

def main():
    """主函数：演示链式反应视觉处理"""
    # 创建处理器实例
    processor = VisualChainReaction()
    
    try:
        # 执行链式反应处理
        # 请将 'your_image.jpg' 替换为您的图像路径
        final_result = processor.execute_chain_reaction('mudan.png')
        
        # 保存结果
        processor.save_results()
        
        print("链式反应视觉处理完成！")
        
        # 显示最终对比
        plt.figure(figsize=(12, 6))
        plt.subplot(1, 2, 1)
        plt.imshow(processor.rgb)
        plt.title('原始图像')
        plt.axis('off')
        
        plt.subplot(1, 2, 2)
        plt.imshow(final_result)
        plt.title('链式反应增强结果')
        plt.axis('off')
        
        plt.tight_layout()
        plt.show()
        
    except Exception as e:
        print(f"处理过程中出现错误: {e}")
        print("请确保图像路径正确，且已安装所有依赖库")

if __name__ == "__main__":
    main()