import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import matplotlib
matplotlib.rc("font", family='Microsoft YaHei')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                             QWidget, QPushButton, QSlider, QLabel, QComboBox, 
                             QTextEdit, QGroupBox, QTabWidget, QSpinBox, QDoubleSpinBox,
                             QCheckBox, QProgressBar, QSplitter)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt5.QtGui import QFont, QPalette, QColor
import sys
import time
from scipy import ndimage
import qutip as qt
from sklearn.manifold import TSNE
import seaborn as sns

class QuantumFractalState(nn.Module):
    """量子分形状态表示"""
    def __init__(self, num_qubits, fractal_dim=256):
        super(QuantumFractalState, self).__init__()
        self.num_qubits = num_qubits
        self.fractal_dim = fractal_dim
        self.state_dim = 2 ** num_qubits
        
        # 量子态参数化
        self.quantum_amplitudes = nn.Parameter(torch.randn(self.state_dim, dtype=torch.cfloat))
        self.quantum_amplitudes.data = F.normalize(self.quantum_amplitudes.data, p=2, dim=0)
        
        # 分形变换矩阵
        self.fractal_transform = nn.Parameter(
            torch.randn(fractal_dim, self.state_dim, dtype=torch.cfloat) * 0.1
        )
        
        # 量子门参数
        self.rotation_gates = nn.Parameter(torch.randn(num_qubits, 3) * 0.1)  # RX, RY, RZ
        
    def apply_quantum_gates(self, state):
        """应用参数化量子门"""
        for qubit in range(self.num_qubits):
            # 旋转门
            rx = torch.cos(self.rotation_gates[qubit, 0]/2) * torch.eye(2) - 1j * torch.sin(self.rotation_gates[qubit, 0]/2) * torch.tensor([[0, 1], [1, 0]], dtype=torch.cfloat)
            ry = torch.cos(self.rotation_gates[qubit, 1]/2) * torch.eye(2) - 1j * torch.sin(self.rotation_gates[qubit, 1]/2) * torch.tensor([[0, -1j], [1j, 0]], dtype=torch.cfloat)
            rz = torch.cos(self.rotation_gates[qubit, 2]/2) * torch.eye(2) - 1j * torch.sin(self.rotation_gates[qubit, 2]/2) * torch.tensor([[1, 0], [0, -1]], dtype=torch.cfloat)
            
            # 应用到对应量子位
            gate = rz @ ry @ rx
            state = self.apply_single_qubit_gate(state, gate, qubit)
        
        return state
    
    def apply_single_qubit_gate(self, state, gate, qubit):
        """应用单量子比特门"""
        # 将状态重塑为张量网络形式
        state_tensor = state.reshape([2] * self.num_qubits)
        
        # 应用门到指定量子位
        # 执行张量收缩 - 修正维度处理
        result = torch.tensordot(state_tensor, gate, dims=([qubit], [1]))
        
        # 修正维度排列逻辑
        # 计算正确的维度顺序
        dim_order = list(range(qubit)) + [self.num_qubits] + list(range(qubit, self.num_qubits))
        
        # 确保维度索引不超出范围
        dim_order = [d for d in dim_order if d < result.dim()]
        
        # 应用排列
        result = result.permute(*dim_order)
        
        return result.reshape(-1)
    
    def fractal_quantum_embedding(self, x):
        """将经典数据嵌入到量子-分形混合空间"""
        batch_size = x.shape[0]
        
        # 经典到量子编码
        x_flat = x.view(batch_size, -1)
        encoding = torch.atan(x_flat)  # 角度编码
        
        # 创建初始量子态
        initial_state = torch.ones(self.state_dim, dtype=torch.cfloat) / np.sqrt(self.state_dim)
        
        # 应用参数化量子电路
        quantum_state = self.apply_quantum_gates(initial_state)
        
        # 分形变换
        fractal_state = torch.matmul(self.fractal_transform, quantum_state)
        
        # 与输入数据交互 - 修正维度匹配
        # 将 fractal_state 扩展到与 encoding 匹配的维度
        fractal_state_expanded = fractal_state.unsqueeze(0).expand(batch_size, -1)
        
        # 将 encoding 投影到 fractal_dim 维度
        if encoding.size(1) != self.fractal_dim:
            # 使用线性变换将编码维度匹配到分形维度
            encoding_projected = F.linear(encoding, 
                                        torch.eye(self.fractal_dim, encoding.size(1), 
                                                dtype=encoding.dtype, device=encoding.device))
        else:
            encoding_projected = encoding
        
        encoded_state = fractal_state_expanded * encoding_projected
        
        return encoded_state

class MandelbrotQuantumLayer(nn.Module):
    """曼德博罗-量子混合层"""
    def __init__(self, in_features, out_features, max_iter=100, escape_radius=2.0):
        super(MandelbrotQuantumLayer, self).__init__()
        self.in_features = in_features
        self.out_features = out_features
        self.max_iter = max_iter
        self.escape_radius = escape_radius
        
        # 量子-分形权重
        self.quantum_weights = nn.Parameter(torch.randn(out_features, in_features, dtype=torch.cfloat) * 0.1)
        self.fractal_bias = nn.Parameter(torch.randn(out_features, dtype=torch.cfloat) * 0.1)
        
        # 混沌动力学参数
        self.chaos_param = nn.Parameter(torch.tensor(3.57))  # Feigenbaum常数附近
        
    def mandelbrot_iteration(self, z, c):
        """曼德博罗迭代的量子版本"""
        return z**2 + c
    
    def forward(self, x):
        batch_size = x.size(0)
        
        # 将输入转换为复数
        x_complex = x.to(torch.cfloat)
        
        # 如果输入是多维的，展平它
        if x_complex.dim() > 2:
            x_complex = x_complex.view(batch_size, -1)
        
        # 确保输入特征数与权重匹配
        if x_complex.size(1) != self.in_features:
            # 使用线性投影将输入特征数匹配到期望的输入特征数
            projection = torch.eye(self.in_features, x_complex.size(1), 
                                 dtype=x_complex.dtype, device=x_complex.device)
            x_complex = torch.matmul(x_complex, projection.t())
        
        # 量子-分形变换
        z = torch.zeros(batch_size, self.out_features, dtype=torch.cfloat)
        c = torch.matmul(x_complex, self.quantum_weights.t()) + self.fractal_bias
        
        # 曼德博罗迭代（量子版本）
        escape_time = torch.zeros(batch_size, self.out_features)
        for i in range(self.max_iter):
            mask = torch.abs(z) < self.escape_radius
            if not mask.any():
                break
            
            # 量子叠加的迭代
            z_new = self.mandelbrot_iteration(z, c)
            z = torch.where(mask, z_new, z)
            escape_time += mask.float()
        
        # 混沌动力学激活
        stability = escape_time / self.max_iter
        chaos_factor = torch.sin(self.chaos_param * stability * np.pi)
        
        # 输出实部和虚部作为特征
        output_real = torch.abs(z) * chaos_factor
        output_imag = torch.angle(z) * chaos_factor
        
        # 合并实部和虚部
        output = torch.cat([output_real, output_imag], dim=1)
        
        return output


class QuantumFractalCNN(nn.Module):
    """量子-分形卷积神经网络"""
    def __init__(self, num_classes=10, num_qubits=4, fractal_depth=3):
        super(QuantumFractalCNN, self).__init__()
        
        # 量子-分形嵌入层
        self.quantum_fractal_embed = QuantumFractalState(num_qubits=num_qubits)
        
        # 获取分形维度
        fractal_dim = self.quantum_fractal_embed.fractal_dim
        
        # 曼德博罗-量子卷积层
        self.mandelbrot_conv1 = MandelbrotQuantumLayer(fractal_dim, 32)
        self.mandelbrot_conv2 = MandelbrotQuantumLayer(64, 32)  # 减少输出通道数
        
        # 分形池化层
        self.fractal_pool = FractalPooling(kernel_size=2, fractal_dim=2)
        
        # 量子注意力机制 - 使用更合理的通道数
        self.quantum_attention = QuantumFractalAttention(channels=64)  # 32*2=64
        
        # 动态分形全连接层
        self.dynamic_fractal_fc = DynamicFractalFC(64, num_classes, fractal_levels=3)
        
    def forward(self, x):
        # 量子-分形嵌入
        x_embedded = self.quantum_fractal_embed.fractal_quantum_embedding(x)
        
        # 调整维度以匹配卷积层的期望输入
        batch_size = x_embedded.size(0)
        fractal_dim = x_embedded.size(1)
        
        # 将分形嵌入重塑为类似图像的形式
        side_dim = int(np.sqrt(fractal_dim))
        if side_dim * side_dim != fractal_dim:
            side_dim = int(np.ceil(np.sqrt(fractal_dim)))
            padding_size = side_dim * side_dim - fractal_dim
            x_embedded = F.pad(x_embedded, (0, padding_size))
            fractal_dim = side_dim * side_dim
        
        x = x_embedded.view(batch_size, 1, side_dim, side_dim)
        
        # 曼德博罗-量子卷积
        x = self.mandelbrot_conv1(x)
        x = F.relu(x)
        
        # 分形池化
        x = self.fractal_pool(x)
        
        # 第二层卷积
        x = self.mandelbrot_conv2(x)
        x = F.relu(x)
        
        # 在传递给量子注意力之前，确保数据是4D格式且通道数正确
        if x.dim() == 2:
            batch_size, features = x.shape
            # 将特征重塑为合理的空间维度
            spatial_dim = int(np.sqrt(features))
            if spatial_dim * spatial_dim != features:
                spatial_dim = int(np.ceil(np.sqrt(features)))
                padding_size = spatial_dim * spatial_dim - features
                x = F.pad(x, (0, padding_size))
                features = spatial_dim * spatial_dim
            
            # 使用1x1卷积调整通道数
            if not hasattr(self, 'channel_adjust'):
                self.channel_adjust = nn.Conv2d(1, 64, 1)  # 调整到期望的通道数
            
            x = x.view(batch_size, 1, spatial_dim, spatial_dim)
            x = self.channel_adjust(x)
        
        # 量子注意力
        x = self.quantum_attention(x)
        
        # 全局分形池化
        x = F.adaptive_avg_pool2d(x, (1, 1))
        x = x.view(x.size(0), -1)
        
        # 动态分形分类
        x = self.dynamic_fractal_fc(x)
        
        return x


class FractalPooling(nn.Module):
    """分形池化层 - 基于分形维度的自适应池化"""
    def __init__(self, kernel_size=2, fractal_dim=1.5):
        super(FractalPooling, self).__init__()
        self.kernel_size = kernel_size
        self.fractal_dim = fractal_dim
        
    def forward(self, x):
        # 检查输入维度，如果不是4维，则reshape为4维
        if x.dim() == 2:
            # 将2D特征转换为4D特征图
            batch_size, features = x.shape
            # 计算合适的空间维度
            side_dim = int(np.sqrt(features))
            if side_dim * side_dim != features:
                # 如果不能完美平方，使用填充
                side_dim = int(np.ceil(np.sqrt(features)))
                padding_size = side_dim * side_dim - features
                x = F.pad(x, (0, padding_size))
            
            x = x.view(batch_size, 1, side_dim, side_dim)
        
        batch_size, channels, height, width = x.shape
        
        # 计算分形权重
        fractal_weights = self.calculate_fractal_weights(x)
        
        # 应用分形池化
        x_pooled = F.avg_pool2d(x * fractal_weights, self.kernel_size)
        
        return x_pooled
    
    def calculate_fractal_weights(self, x):
        """计算基于分形维度的权重"""
        # 使用差分盒计数方法估计分形维度
        batch_size, channels, height, width = x.shape
        
        weights = torch.ones_like(x)
        for b in range(batch_size):
            for c in range(channels):
                # 提取特征图
                feature_map = x[b, c].detach().cpu().numpy()
                
                # 估算分形维度（简化版）
                fractal_dim = self.estimate_fractal_dimension(feature_map)
                
                # 根据分形维度调整权重
                weight_factor = 1.0 + (fractal_dim - self.fractal_dim) * 0.5
                weights[b, c] = weight_factor
        
        return weights
    
    def estimate_fractal_dimension(self, image, threshold=0.5):
        """使用盒计数法估算分形维度（简化版）"""
        # 二值化图像
        binary_image = (image > threshold).astype(int)
        
        # 简化版分形维度计算
        if np.sum(binary_image) == 0:
            return 1.0
        
        # 使用不同大小的盒子覆盖图像
        sizes = [2, 4, 8, 16]
        counts = []
        
        for size in sizes:
            if size > min(image.shape):
                break
            
            # 计算需要的盒子数量
            box_count = 0
            for i in range(0, image.shape[0], size):
                for j in range(0, image.shape[1], size):
                    if np.any(binary_image[i:min(i+size, image.shape[0]), 
                              j:min(j+size, image.shape[1])]):
                        box_count += 1
            
            counts.append(box_count)
        
        if len(counts) < 2:
            return 1.0
        
        # 计算分形维度（对数斜率）
        log_sizes = np.log(sizes[:len(counts)])
        log_counts = np.log(counts)
        
        # 防止除零
        if np.std(log_sizes) < 1e-10:
            return 1.0
        
        fractal_dim = -np.polyfit(log_sizes, log_counts, 1)[0]
        
        return max(1.0, min(2.0, fractal_dim))

class QuantumFractalAttention(nn.Module):
    """量子-分形注意力机制"""
    def __init__(self, channels, reduction=16, num_qubits=3):
        super(QuantumFractalAttention, self).__init__()
        self.channels = channels
        self.num_qubits = num_qubits
        
        # 量子注意力权重
        self.quantum_gate = nn.Parameter(torch.randn(num_qubits, 3) * 0.1)
        
        # 分形缩放
        self.fractal_scale = nn.Parameter(torch.ones(1, channels, 1, 1))
        self.fractal_shift = nn.Parameter(torch.zeros(1, channels, 1, 1))
        
        # 经典注意力组件
        self.avg_pool = nn.AdaptiveAvgPool2d(1)
        self.fc = nn.Sequential(
            nn.Linear(channels, channels // reduction),
            nn.ReLU(inplace=True),
            nn.Linear(channels // reduction, channels),
            nn.Sigmoid()
        )
        
    def forward(self, x):
        batch_size, channels, height, width = x.shape
        
        # 确保通道数匹配
        if channels != self.channels:
            # 如果通道数不匹配，使用1x1卷积进行投影
            if hasattr(self, 'channel_adjust'):
                x = self.channel_adjust(x)
            else:
                # 动态创建通道调整层
                self.channel_adjust = nn.Conv2d(channels, self.channels, 1).to(x.device)
                x = self.channel_adjust(x)
            channels = self.channels
        
        # 量子态准备
        quantum_weights = self.prepare_quantum_attention_weights(batch_size)
        
        # 分形变换
        fractal_x = x * self.fractal_scale + self.fractal_shift
        
        # 量子-分形融合
        quantum_fractal_x = fractal_x * quantum_weights
        
        # 经典注意力 - 修复形状不匹配问题
        y = self.avg_pool(quantum_fractal_x)
        y = y.view(batch_size, channels)  # 确保形状正确
        y = self.fc(y).view(batch_size, channels, 1, 1)
        
        return x * y
    
    def prepare_quantum_attention_weights(self, batch_size):
        """准备量子注意力权重"""
        # 创建初始量子态
        state_dim = 2 ** self.num_qubits
        initial_state = torch.ones(state_dim, dtype=torch.cfloat) / np.sqrt(state_dim)
        
        # 应用量子门
        quantum_state = initial_state
        for qubit in range(self.num_qubits):
            # 简化版量子门应用
            angle = self.quantum_gate[qubit].mean()
            quantum_state = quantum_state * torch.exp(1j * angle)
        
        # 转换为注意力权重
        attention_weights = torch.abs(quantum_state) ** 2
        
        # 确保权重长度与通道数匹配
        if len(attention_weights) < self.channels:
            # 如果权重太少，重复填充
            repeat_times = (self.channels + len(attention_weights) - 1) // len(attention_weights)
            attention_weights = attention_weights.repeat(repeat_times)
        
        attention_weights = attention_weights[:self.channels]
        
        # 如果仍然不够，用1填充
        if len(attention_weights) < self.channels:
            padding = torch.ones(self.channels - len(attention_weights))
            attention_weights = torch.cat([attention_weights, padding])
        
        attention_weights = attention_weights.view(1, self.channels, 1, 1)
        attention_weights = attention_weights.repeat(batch_size, 1, 1, 1)
        
        return attention_weights
    
class DynamicFractalFC(nn.Module):
    """动态分形全连接层"""
    def __init__(self, in_features, out_features, fractal_levels=3):
        super(DynamicFractalFC, self).__init__()
        self.in_features = in_features
        self.out_features = out_features
        self.fractal_levels = fractal_levels
        
        # 基础全连接层
        self.base_fc = nn.Linear(in_features, out_features)
        
        # 分形分支
        self.fractal_branches = nn.ModuleList()
        for level in range(fractal_levels):
            branch_in = max(in_features // (2 ** level), 1)
            branch_out = max(out_features // (2 ** level), 1)
            self.fractal_branches.append(nn.Linear(branch_in, branch_out))
        
        # 动态权重
        self.dynamic_weights = nn.Parameter(torch.ones(fractal_levels + 1))
        
    def forward(self, x):
        # 基础路径
        base_output = self.base_fc(x)
        
        # 分形分支
        branch_outputs = []
        for level, branch in enumerate(self.fractal_branches):
            # 下采样输入
            if level > 0:
                x_down = F.adaptive_avg_pool1d(x.unsqueeze(1), 
                                             max(x.size(1) // (2 ** level), 1)).squeeze(1)
            else:
                x_down = x
            
            # 分支处理
            branch_out = branch(x_down)
            
            # 上采样回原始尺寸
            if level > 0:
                branch_out = F.interpolate(branch_out.unsqueeze(1), 
                                         size=self.out_features).squeeze(1)
            
            branch_outputs.append(branch_out)
        
        # 动态融合
        weighted_base = self.dynamic_weights[0] * base_output
        weighted_branches = sum(w * branch for w, branch in 
                               zip(self.dynamic_weights[1:], branch_outputs))
        
        return weighted_base + weighted_branches
    
class QuantumFractalVisualizer(FigureCanvas):
    """量子-分形可视化画布"""
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        super(QuantumFractalVisualizer, self).__init__(self.fig)
        self.setParent(parent)
        
        # 创建2x2的子图布局
        self.axes = self.fig.subplots(2, 2)
        self.fig.subplots_adjust(hspace=0.5, wspace=0.3)
        
        # 设置所有子图的背景色
        for ax_row in self.axes:
            for ax in ax_row:
                ax.set_facecolor('black')
        self.fig.patch.set_facecolor('black')
        
        # 初始可视化
        self.visualize_initial_fractal()
    
    def visualize_initial_fractal(self):
        """初始分形可视化"""
        # 只在第一个子图显示初始分形
        ax = self.axes[0, 0]
        x = np.linspace(-2, 1, 800)
        y = np.linspace(-1.5, 1.5, 800)
        X, Y = np.meshgrid(x, y)
        Z = X + 1j * Y
        
        # 曼德博罗集计算
        mandelbrot = self.calculate_mandelbrot(Z)
        
        ax.clear()
        ax.imshow(mandelbrot, extent=[-2, 1, -1.5, 1.5], cmap='hot')
        ax.set_title('Quantum-Fractal Neural Network', color='white')
        ax.set_xlabel('Real Axis', color='white')
        ax.set_ylabel('Imaginary Axis', color='white')
        ax.tick_params(colors='white')
        
        # 清除其他子图
        for i in range(2):
            for j in range(2):
                if i == 0 and j == 0:
                    continue  # 跳过第一个子图
                self.axes[i, j].clear()
                self.axes[i, j].set_facecolor('black')
                self.axes[i, j].set_xticks([])
                self.axes[i, j].set_yticks([])
        
        self.draw()
    
    def calculate_mandelbrot(self, Z, max_iter=100):
        """计算曼德博罗集"""
        output = np.zeros(Z.shape)
        z = np.zeros(Z.shape, dtype=complex)
        
        for i in range(max_iter):
            mask = np.abs(z) < 10
            z[mask] = z[mask]**2 + Z[mask]
            output += mask
        
        return output
    
    def update_visualization(self, quantum_state, fractal_pattern, iteration):
        """更新可视化"""
        # 不需要清除整个画布，直接更新每个子图
        # 1. 量子态可视化
        if quantum_state is not None:
            q_state = quantum_state.detach().numpy() if torch.is_tensor(quantum_state) else quantum_state
            self.axes[0, 0].clear()
            self.axes[0, 0].bar(range(len(q_state)), np.abs(q_state)**2, color='cyan', alpha=0.7)
            self.axes[0, 0].set_title('Quantum State Probabilities', color='white', fontsize=10)
            self.axes[0, 0].set_facecolor('black')
            self.axes[0, 0].tick_params(colors='white')
        
        # 2. 分形模式可视化
        if fractal_pattern is not None:
            fractal_img = fractal_pattern.detach().numpy() if torch.is_tensor(fractal_pattern) else fractal_pattern
            if fractal_img.ndim > 2:
                fractal_img = fractal_img[0, 0]  # 取第一个通道
            self.axes[0, 1].clear()
            self.axes[0, 1].imshow(fractal_img, cmap='viridis')
            self.axes[0, 1].set_title('Fractal Pattern', color='white', fontsize=10)
            self.axes[0, 1].set_facecolor('black')
            self.axes[0, 1].tick_params(colors='white')
        
        # 3. 量子-分形融合可视化
        self.axes[1, 0].clear()
        self.visualize_quantum_fractal_fusion(self.axes[1, 0])
        
        # 4. 训练进度
        self.axes[1, 1].clear()
        self.axes[1, 1].text(0.5, 0.5, f'Iteration: {iteration}\nQuantum-Fractal Fusion Active', 
                           ha='center', va='center', color='white', fontsize=12,
                           transform=self.axes[1, 1].transAxes)
        self.axes[1, 1].set_facecolor('black')
        self.axes[1, 1].set_xticks([])
        self.axes[1, 1].set_yticks([])
        
        self.draw()
    
    def visualize_quantum_fractal_fusion(self, ax):
        """可视化量子-分形融合"""
        # 创建量子-分形混合模式
        x = np.linspace(-2, 2, 300)
        y = np.linspace(-2, 2, 300)
        X, Y = np.meshgrid(x, y)
        
        # 量子振荡 + 分形模式
        quantum_oscillation = np.sin(5 * X) * np.cos(5 * Y)
        fractal_component = np.exp(-(X**2 + Y**2)) * np.sin(10 * np.sqrt(X**2 + Y**2))
        
        fusion = quantum_oscillation * fractal_component
        
        im = ax.imshow(fusion, cmap='plasma', extent=[-2, 2, -2, 2])
        ax.set_title('Quantum-Fractal Fusion', color='white', fontsize=10)
        ax.set_facecolor('black')
        ax.tick_params(colors='white')

class TrainingThread(QThread):
    """训练线程"""
    update_signal = pyqtSignal(object, object, int)
    finished_signal = pyqtSignal()
    
    def __init__(self, model, dataloader, num_epochs):
        super(TrainingThread, self).__init__()
        self.model = model
        self.dataloader = dataloader
        self.num_epochs = num_epochs
        self.is_running = True
    
    def run(self):
        """训练过程"""
        optimizer = torch.optim.Adam(self.model.parameters(), lr=0.001)
        criterion = nn.CrossEntropyLoss()
        
        for epoch in range(self.num_epochs):
            if not self.is_running:
                break
                
            for i, (data, target) in enumerate(self.dataloader):
                if not self.is_running:
                    break
                    
                optimizer.zero_grad()
                output = self.model(data)
                loss = criterion(output, target)
                loss.backward()
                optimizer.step()
                
                # 每10个batch发送更新信号
                if i % 10 == 0:
                    # 获取量子态和分形模式用于可视化
                    quantum_state = torch.randn(8)  # 模拟量子态
                    fractal_pattern = torch.randn(1, 1, 32, 32)  # 模拟分形模式
                    
                    self.update_signal.emit(quantum_state, fractal_pattern, epoch * len(self.dataloader) + i)
                
                time.sleep(0.01)  # 减慢训练速度以便观察
        
        self.finished_signal.emit()
    
    def stop(self):
        """停止训练"""
        self.is_running = False

class QuantumFractalGUI(QMainWindow):
    """量子-分形神经网络主界面"""
    def __init__(self):
        super(QuantumFractalGUI, self).__init__()
        self.model = None
        self.training_thread = None
        
        self.init_ui()
        self.init_model()
    
    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("Quantum-Fractal Neural Network Visualizer")
        self.setGeometry(100, 100, 1400, 900)
        
        # 设置样式
        self.set_dark_theme()
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QHBoxLayout(central_widget)
        
        # 左侧控制面板
        control_panel = self.create_control_panel()
        main_layout.addWidget(control_panel, 1)
        
        # 右侧可视化区域
        viz_splitter = QSplitter(Qt.Vertical)
        main_layout.addWidget(viz_splitter, 3)
        
        # 量子-分形可视化
        self.fractal_viz = QuantumFractalVisualizer(self, width=8, height=6)
        viz_splitter.addWidget(self.fractal_viz)
        
        # 日志区域
        log_widget = QWidget()
        log_layout = QVBoxLayout(log_widget)
        
        log_label = QLabel("Training Log")
        log_label.setFont(QFont("Arial", 12, QFont.Bold))
        log_layout.addWidget(log_label)
        
        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(200)
        log_layout.addWidget(self.log_text)
        
        viz_splitter.addWidget(log_widget)
        
        # 设置分割比例
        viz_splitter.setSizes([600, 200])
    
    def set_dark_theme(self):
        """设置暗色主题"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QWidget {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #555555;
                border-radius: 5px;
                margin-top: 1ex;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #88c9f2;
            }
            QPushButton {
                background-color: #404040;
                color: white;
                border: 1px solid #555555;
                border-radius: 3px;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: #505050;
            }
            QPushButton:pressed {
                background-color: #606060;
            }
            QSlider::groove:horizontal {
                border: 1px solid #999999;
                height: 8px;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #B1B1B1, stop:1 #c4c4c4);
                margin: 2px 0;
            }
            QSlider::handle:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #b4b4b4, stop:1 #8f8f8f);
                border: 1px solid #5c5c5c;
                width: 18px;
                margin: -2px 0;
                border-radius: 3px;
            }
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #555555;
                border-radius: 3px;
            }
            QComboBox {
                background-color: #404040;
                color: white;
                border: 1px solid #555555;
                border-radius: 3px;
                padding: 3px;
            }
            QSpinBox, QDoubleSpinBox {
                background-color: #404040;
                color: white;
                border: 1px solid #555555;
                border-radius: 3px;
                padding: 3px;
            }
            QCheckBox {
                spacing: 5px;
            }
            QCheckBox::indicator {
                width: 15px;
                height: 15px;
            }
            QCheckBox::indicator:unchecked {
                border: 1px solid #555555;
                background-color: #404040;
            }
            QCheckBox::indicator:checked {
                border: 1px solid #555555;
                background-color: #88c9f2;
            }
            QProgressBar {
                border: 1px solid #555555;
                border-radius: 3px;
                text-align: center;
                color: white;
            }
            QProgressBar::chunk {
                background-color: #88c9f2;
                width: 10px;
            }
        """)
    
    def create_control_panel(self):
        """创建控制面板"""
        control_widget = QWidget()
        control_layout = QVBoxLayout(control_widget)
        
        # 网络配置组
        network_group = QGroupBox("Quantum-Fractal Network Configuration")
        network_layout = QVBoxLayout(network_group)
        
        # 量子比特数
        qubit_layout = QHBoxLayout()
        qubit_layout.addWidget(QLabel("Number of Qubits:"))
        self.qubit_spin = QSpinBox()
        self.qubit_spin.setRange(2, 8)
        self.qubit_spin.setValue(4)
        qubit_layout.addWidget(self.qubit_spin)
        network_layout.addLayout(qubit_layout)
        
        # 分形深度
        fractal_depth_layout = QHBoxLayout()
        fractal_depth_layout.addWidget(QLabel("Fractal Depth:"))
        self.fractal_depth_spin = QSpinBox()
        self.fractal_depth_spin.setRange(1, 5)
        self.fractal_depth_spin.setValue(3)
        fractal_depth_layout.addWidget(self.fractal_depth_spin)
        network_layout.addLayout(fractal_depth_layout)
        
        # 混沌参数
        chaos_layout = QHBoxLayout()
        chaos_layout.addWidget(QLabel("Chaos Parameter:"))
        self.chaos_spin = QDoubleSpinBox()
        self.chaos_spin.setRange(3.0, 4.0)
        self.chaos_spin.setValue(3.57)
        self.chaos_spin.setSingleStep(0.01)
        chaos_layout.addWidget(self.chaos_spin)
        network_layout.addLayout(chaos_layout)
        
        control_layout.addWidget(network_group)
        
        # 训练控制组
        training_group = QGroupBox("Training Control")
        training_layout = QVBoxLayout(training_group)
        
        # 训练按钮
        self.train_button = QPushButton("Start Quantum-Fractal Training")
        self.train_button.clicked.connect(self.toggle_training)
        training_layout.addWidget(self.train_button)
        
        # 训练参数
        epochs_layout = QHBoxLayout()
        epochs_layout.addWidget(QLabel("Training Epochs:"))
        self.epochs_spin = QSpinBox()
        self.epochs_spin.setRange(1, 100)
        self.epochs_spin.setValue(10)
        epochs_layout.addWidget(self.epochs_spin)
        training_layout.addLayout(epochs_layout)
        
        # 进度条
        self.progress_bar = QProgressBar()
        training_layout.addWidget(self.progress_bar)
        
        control_layout.addWidget(training_group)
        
        # 可视化选项组
        viz_group = QGroupBox("Visualization Options")
        viz_layout = QVBoxLayout(viz_group)
        
        # 可视化类型
        viz_type_layout = QHBoxLayout()
        viz_type_layout.addWidget(QLabel("Visualization Type:"))
        self.viz_combo = QComboBox()
        self.viz_combo.addItems(["Quantum States", "Fractal Patterns", "Fusion Matrix", "Training Dynamics"])
        viz_type_layout.addWidget(self.viz_combo)
        viz_layout.addLayout(viz_type_layout)
        
        # 实时更新选项
        self.realtime_check = QCheckBox("Real-time Visualization Update")
        self.realtime_check.setChecked(True)
        viz_layout.addWidget(self.realtime_check)
        
        # 更新频率
        freq_layout = QHBoxLayout()
        freq_layout.addWidget(QLabel("Update Frequency (Hz):"))
        self.freq_slider = QSlider(Qt.Horizontal)
        self.freq_slider.setRange(1, 30)
        self.freq_slider.setValue(10)
        freq_layout.addWidget(self.freq_slider)
        viz_layout.addLayout(freq_layout)
        
        control_layout.addWidget(viz_group)
        
        # 添加弹性空间
        control_layout.addStretch(1)
        
        return control_widget
    
    def init_model(self):
        """初始化模型"""
        num_qubits = self.qubit_spin.value()
        fractal_depth = self.fractal_depth_spin.value()
        
        self.model = QuantumFractalCNN(
            num_classes=10, 
            num_qubits=num_qubits, 
            fractal_depth=fractal_depth
        )
        
        self.log_text.append("Quantum-Fractal Neural Network initialized.")
        self.log_text.append(f"Qubits: {num_qubits}, Fractal Depth: {fractal_depth}")
    
    def toggle_training(self):
        """开始/停止训练"""
        if self.training_thread and self.training_thread.isRunning():
            self.training_thread.stop()
            self.train_button.setText("Start Quantum-Fractal Training")
            self.log_text.append("Training stopped.")
        else:
            self.start_training()
    
    def start_training(self):
        """开始训练"""
        # 创建模拟数据加载器
        dataset = torch.utils.data.TensorDataset(
            torch.randn(100, 3, 32, 32),  # 模拟图像数据
            torch.randint(0, 10, (100,))   # 模拟标签
        )
        dataloader = torch.utils.data.DataLoader(dataset, batch_size=10, shuffle=True)
        
        # 创建训练线程
        self.training_thread = TrainingThread(
            self.model, 
            dataloader, 
            self.epochs_spin.value()
        )
        
        # 连接信号
        self.training_thread.update_signal.connect(self.update_visualization)
        self.training_thread.finished_signal.connect(self.training_finished)
        
        # 开始训练
        self.training_thread.start()
        self.train_button.setText("Stop Training")
        self.log_text.append("Quantum-Fractal training started...")
    
    def update_visualization(self, quantum_state, fractal_pattern, iteration):
        """更新可视化"""
        if self.realtime_check.isChecked():
            self.fractal_viz.update_visualization(quantum_state, fractal_pattern, iteration)
        
        # 更新进度条
        progress = min(100, int(iteration / (self.epochs_spin.value() * 10) * 100))
        self.progress_bar.setValue(progress)
        
        # 更新日志
        if iteration % 50 == 0:
            self.log_text.append(f"Iteration {iteration}: Quantum-Fractal fusion active")
    
    def training_finished(self):
        """训练完成"""
        self.train_button.setText("Start Quantum-Fractal Training")
        self.log_text.append("Training completed successfully!")
        self.progress_bar.setValue(100)

def main():
    app = QApplication(sys.argv)
    
    # 设置应用程序字体
    font = QFont("Arial", 10)
    app.setFont(font)
    
    window = QuantumFractalGUI()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()