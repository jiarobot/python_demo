import sys
import os
import cv2
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torchvision import transforms
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import random
import json
import time
from datetime import datetime
from pathlib import Path
import shutil
from collections import deque

# PyQt5 imports
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QPushButton, QLabel, QSlider, 
                            QComboBox, QCheckBox, QGroupBox, QFileDialog,
                            QProgressBar, QTextEdit, QListWidget, QSplitter,
                            QTabWidget, QSpinBox, QDoubleSpinBox, QMessageBox,
                            QFrame, QScrollArea, QGridLayout, QSizePolicy)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QSize
from PyQt5.QtGui import QPixmap, QImage, QPalette, QFont, QIcon

class AdvancedNeuralProcessor:
    """高级神经网络处理器 - 支持多种风格和GAN"""
    
    def __init__(self, input_size=512):
        self.input_size = input_size
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.models = {}
        self.current_model = None
        
    def create_gan_generator(self, latent_dim=100):
        """创建GAN生成器"""
        class Generator(nn.Module):
            def __init__(self, latent_dim, input_size):
                super().__init__()
                self.input_size = input_size
                self.init_size = self.input_size // 4
                # 修复：确保线性层的输出维度正确
                self.l1 = nn.Linear(latent_dim, 128 * self.init_size ** 2)

                self.conv_blocks = nn.Sequential(
                    nn.BatchNorm2d(128),
                    nn.Upsample(scale_factor=2),
                    nn.Conv2d(128, 128, 3, stride=1, padding=1),
                    nn.BatchNorm2d(128, 0.8),
                    nn.LeakyReLU(0.2, inplace=True),
                    nn.Upsample(scale_factor=2),
                    nn.Conv2d(128, 64, 3, stride=1, padding=1),
                    nn.BatchNorm2d(64, 0.8),
                    nn.LeakyReLU(0.2, inplace=True),
                    nn.Conv2d(64, 3, 3, stride=1, padding=1),
                    nn.Tanh(),
                )

            def forward(self, z):
                # 修复：确保输入维度正确
                batch_size = z.size(0)
                out = self.l1(z)
                out = out.view(batch_size, 128, self.init_size, self.init_size)
                img = self.conv_blocks(out)
                return img
        
        return Generator(latent_dim, self.input_size)
    
    def create_style_transfer_network(self):
        """创建风格迁移网络"""
        class StyleTransferNet(nn.Module):
            def __init__(self):
                super().__init__()
                # 编码器
                self.encoder = nn.Sequential(
                    nn.Conv2d(3, 32, 9, padding=4),
                    nn.InstanceNorm2d(32),
                    nn.ReLU(),
                    nn.Conv2d(32, 64, 3, stride=2, padding=1),
                    nn.InstanceNorm2d(64),
                    nn.ReLU(),
                    nn.Conv2d(64, 128, 3, stride=2, padding=1),
                    nn.InstanceNorm2d(128),
                    nn.ReLU(),
                )
                
                # 残差块
                self.residual_blocks = nn.Sequential(*[
                    self._make_residual_block(128) for _ in range(5)
                ])
                
                # 解码器
                self.decoder = nn.Sequential(
                    nn.ConvTranspose2d(128, 64, 3, stride=2, padding=1, output_padding=1),
                    nn.InstanceNorm2d(64),
                    nn.ReLU(),
                    nn.ConvTranspose2d(64, 32, 3, stride=2, padding=1, output_padding=1),
                    nn.InstanceNorm2d(32),
                    nn.ReLU(),
                    nn.Conv2d(32, 3, 9, padding=4),
                    nn.Tanh(),
                )
                
            def _make_residual_block(self, channels):
                return nn.Sequential(
                    nn.Conv2d(channels, channels, 3, padding=1),
                    nn.InstanceNorm2d(channels),
                    nn.ReLU(),
                    nn.Conv2d(channels, channels, 3, padding=1),
                    nn.InstanceNorm2d(channels),
                )
            
            def forward(self, x):
                # 随机风格权重
                style_weights = torch.randn(1, 128, 1, 1).to(x.device) * 0.5 + 1.0
                
                encoded = self.encoder(x)
                residual = self.residual_blocks(encoded)
                
                # 应用随机风格
                styled = residual * style_weights
                decoded = self.decoder(styled)
                
                return decoded
        
        return StyleTransferNet()
    
    def create_fractal_network(self):
        """创建分形网络"""
        class FractalNet(nn.Module):
            def __init__(self):
                super().__init__()
                self.layers = nn.ModuleList([
                    self._create_fractal_block(3, 32),
                    self._create_fractal_block(32, 64),
                    self._create_fractal_block(64, 128),
                    self._create_fractal_block(128, 64),
                    self._create_fractal_block(64, 32),
                    nn.Conv2d(32, 3, 3, padding=1),
                    nn.Tanh()
                ])
                
            def _create_fractal_block(self, in_ch, out_ch):
                return nn.Sequential(
                    nn.Conv2d(in_ch, out_ch, 3, padding=1),
                    nn.BatchNorm2d(out_ch),
                    nn.ReLU(),
                    nn.Conv2d(out_ch, out_ch, 3, padding=1),
                    nn.BatchNorm2d(out_ch),
                    nn.ReLU(),
                )
            
            def forward(self, x, iterations=3):
                """修复维度问题的前向传播"""
                for i, layer in enumerate(self.layers):
                    if i < len(self.layers) - 2:  # 对前面的层进行迭代
                        for _ in range(iterations):
                            # 确保残差连接的维度匹配
                            layer_output = layer(x)
                            if x.shape[1] == layer_output.shape[1]:  # 检查通道数是否匹配
                                x = layer_output + x
                            else:
                                x = layer_output  # 如果不匹配，不使用残差连接
                    else:
                        x = layer(x)
                return x
        
        return FractalNet()
    
    def initialize_models(self):
        """初始化所有模型 - 增强错误处理"""
        model_types = {
            'style_transfer': self.create_style_transfer_network,
            'gan': lambda: self.create_gan_generator(100),
            'fractal': self.create_fractal_network,
            'abstract': self.create_abstract_network,
            'neural_art': self.create_neural_art_network
        }
        
        for name, creator in model_types.items():
            try:
                model = creator()
                model.apply(self._init_weights)
                model.to(self.device)
                self.models[name] = model
                print(f"成功初始化模型: {name}")
            except Exception as e:
                print(f"初始化模型 {name} 时出错: {e}")
        
        if not self.models:
            raise RuntimeError("没有成功初始化任何模型")
        
        self.current_model = next(iter(self.models.values()))
    
    def _init_weights(self, m):
        """初始化权重"""
        if isinstance(m, nn.Conv2d):
            nn.init.normal_(m.weight, 0, 0.02)
            if m.bias is not None:
                nn.init.constant_(m.bias, 0)
    
    def set_model(self, model_name):
        """设置当前模型"""
        if model_name in self.models:
            self.current_model = self.models[model_name]
    
    def process_image(self, image, style_intensity=0.7, iterations=3):
        """处理图像 - 修复维度问题"""
        if self.current_model is None:
            return Image.fromarray(image) if isinstance(image, np.ndarray) else image
        
        try:
            # 确保图像是numpy数组格式
            if isinstance(image, Image.Image):
                image = np.array(image)
            
            # 确保图像是3通道
            if len(image.shape) == 2:  # 灰度图
                image = np.stack([image] * 3, axis=2)
            elif image.shape[2] == 4:  # RGBA
                image = image[:, :, :3]
            
            # 转换图像
            transform = transforms.Compose([
                transforms.ToPILImage(),
                transforms.Resize((self.input_size, self.input_size)),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5])
            ])
            
            image_tensor = transform(image).unsqueeze(0).to(self.device)
            
            with torch.no_grad():
                # 检查模型类型并相应处理
                model_class_name = self.current_model.__class__.__name__
                
                if model_class_name == 'FractalNet':
                    output = self.current_model(image_tensor, iterations)
                elif model_class_name == 'Generator':
                    # 对于GAN生成器，生成随机潜在向量
                    latent_dim = 100
                    z = torch.randn(1, latent_dim).to(self.device)
                    output = self.current_model(z)
                    # 调整输出大小以匹配输入
                    output = F.interpolate(output, size=(self.input_size, self.input_size), 
                                        mode='bilinear', align_corners=False)
                else:
                    # 确保输入通道匹配
                    if image_tensor.shape[1] != 3:
                        # 调整输入通道
                        if image_tensor.shape[1] == 1:
                            image_tensor = image_tensor.repeat(1, 3, 1, 1)
                        else:
                            image_tensor = image_tensor[:, :3, :, :]
                    
                    output = self.current_model(image_tensor)
            
            # 混合原始图像和处理结果
            if output.shape == image_tensor.shape:
                output = style_intensity * output + (1 - style_intensity) * image_tensor
            
            output = torch.clamp(output, -1, 1)
            
            # 转换回PIL图像
            output = (output.squeeze(0).cpu() * 0.5 + 0.5).clamp(0, 1)
            output = transforms.ToPILImage()(output)
            
            return output
            
        except Exception as e:
            print(f"图像处理错误: {e}")
            # 出错时返回原始图像
            return Image.fromarray(image) if isinstance(image, np.ndarray) else image
    
    def create_abstract_network(self):
        """创建抽象艺术网络 - 修复通道数问题"""
        class AbstractNet(nn.Module):
            def __init__(self):
                super().__init__()
                # 简化网络结构，确保输入输出通道匹配
                self.encoder = nn.Sequential(
                    nn.Conv2d(3, 16, 3, padding=1),  # 3->16
                    nn.ReLU(),
                    nn.Conv2d(16, 32, 3, padding=1), # 16->32
                    nn.ReLU(),
                    nn.MaxPool2d(2),
                )
                
                self.middle = nn.Sequential(
                    nn.Conv2d(32, 64, 3, padding=1), # 32->64
                    nn.ReLU(),
                    nn.Conv2d(64, 64, 3, padding=1), # 64->64
                    nn.ReLU(),
                )
                
                self.decoder = nn.Sequential(
                    nn.Upsample(scale_factor=2),
                    nn.Conv2d(64, 32, 3, padding=1), # 64->32
                    nn.ReLU(),
                    nn.Conv2d(32, 16, 3, padding=1), # 32->16
                    nn.ReLU(),
                    nn.Conv2d(16, 3, 3, padding=1),  # 16->3
                    nn.Tanh(),
                )
                
            def forward(self, x):
                # 确保输入是3通道
                if x.shape[1] != 3:
                    x = x[:, :3, :, :]  # 取前3个通道
                
                encoded = self.encoder(x)
                middle = self.middle(encoded)
                decoded = self.decoder(middle)
                return decoded
        
        return AbstractNet()
    
    def create_neural_art_network(self):
        """创建神经艺术网络 - 修复维度问题"""
        class NeuralArtNet(nn.Module):
            def __init__(self):
                super().__init__()
                # 简化的编码器-解码器结构，避免复杂的注意力机制
                self.encoder = nn.Sequential(
                    nn.Conv2d(3, 32, 3, padding=1),
                    nn.ReLU(),
                    nn.Conv2d(32, 64, 3, padding=1),
                    nn.ReLU(),
                    nn.MaxPool2d(2),
                    
                    nn.Conv2d(64, 128, 3, padding=1),
                    nn.ReLU(),
                    nn.Conv2d(128, 256, 3, padding=1),
                    nn.ReLU(),
                    nn.MaxPool2d(2),
                )
                
                self.decoder = nn.Sequential(
                    nn.Conv2d(256, 128, 3, padding=1),
                    nn.ReLU(),
                    nn.Upsample(scale_factor=2),
                    nn.Conv2d(128, 64, 3, padding=1),
                    nn.ReLU(),
                    nn.Upsample(scale_factor=2),
                    nn.Conv2d(64, 32, 3, padding=1),
                    nn.ReLU(),
                    nn.Conv2d(32, 3, 3, padding=1),
                    nn.Tanh(),
                )
                
            def forward(self, x):
                encoded = self.encoder(x)
                decoded = self.decoder(encoded)
                return decoded
        
        return NeuralArtNet()

class AdvancedCoinDesigner:
    """高级纪念币设计师"""
    
    def __init__(self):
        self.templates = {}
        self.textures = {}
        self.initialize_templates()
        self.initialize_textures()
    
    def initialize_templates(self):
        """初始化模板系统"""
        self.templates = {
            'classic_circular': self.create_classic_circular,
            'geometric_polygon': self.create_geometric_polygon,
            'organic_flow': self.create_organic_flow,
            'fractal_pattern': self.create_fractal_pattern,
            'crystal_lattice': self.create_crystal_lattice,
            'celestial_body': self.create_celestial_body,
            'ancient_symbol': self.create_ancient_symbol,
            'modern_abstract': self.create_modern_abstract,
        }
    
    def initialize_textures(self):
        """初始化纹理系统"""
        self.textures = {
            'metallic_brushed': self.create_brushed_metal,
            'gold_plated': self.create_gold_texture,
            'silver_polished': self.create_silver_texture,
            'bronze_aged': self.create_bronze_texture,
            'crystal_clear': self.create_crystal_texture,
            'holographic': self.create_holographic_texture,
            'glowing_edge': self.create_glowing_edge,
            'deep_engraved': self.create_engraved_texture,
        }
    
    def create_classic_circular(self, size):
        """经典圆形模板"""
        mask = Image.new('L', (size, size), 0)
        draw = ImageDraw.Draw(mask)
        
        # 主圆形
        draw.ellipse([5, 5, size-5, size-5], fill=255)
        
        # 装饰性边框
        for i in range(3):
            radius = size//2 - 10 - i*8
            draw.ellipse([size//2-radius, size//2-radius, 
                         size//2+radius, size//2+radius], 
                        outline=200, width=2)
        
        return mask
    
    def create_geometric_polygon(self, size):
        """几何多边形模板"""
        mask = Image.new('L', (size, size), 0)
        draw = ImageDraw.Draw(mask)
        
        sides = random.choice([5, 6, 7, 8, 12])
        radius = size // 2 - 15
        center = size // 2
        
        points = []
        for i in range(sides):
            angle = 2 * np.pi * i / sides + random.uniform(-0.1, 0.1)
            x = center + radius * np.cos(angle)
            y = center + radius * np.sin(angle)
            points.append((x, y))
        
        draw.polygon(points, fill=255)
        
        # 内部几何图案
        inner_radius = radius * 0.6
        inner_points = []
        for i in range(sides):
            angle = 2 * np.pi * i / sides
            x = center + inner_radius * np.cos(angle)
            y = center + inner_radius * np.sin(angle)
            inner_points.append((x, y))
        
        draw.polygon(inner_points, outline=200, width=3)
        
        return mask
    
    def create_organic_flow(self, size):
        """有机流动形状"""
        mask = Image.new('L', (size, size), 0)
        draw = ImageDraw.Draw(mask)
        
        center = size // 2
        base_radius = size // 3
        
        # 创建流动形状
        points = []
        num_points = random.randint(12, 24)
        
        for i in range(num_points):
            angle = 2 * np.pi * i / num_points
            # 添加随机波动
            wave = np.sin(angle * random.randint(3, 8)) * 0.2
            radius_variation = random.uniform(0.7, 1.3) + wave
            radius = base_radius * radius_variation
            x = center + radius * np.cos(angle)
            y = center + radius * np.sin(angle)
            points.append((x, y))
        
        draw.polygon(points, fill=255)
        
        # 添加内部细节
        for i in range(random.randint(3, 8)):
            inner_radius = base_radius * random.uniform(0.3, 0.6)
            inner_points = []
            for j in range(num_points // 2):
                angle = 4 * np.pi * j / (num_points // 2)
                x = center + inner_radius * np.cos(angle)
                y = center + inner_radius * np.sin(angle)
                inner_points.append((x, y))
            if len(inner_points) > 2:
                draw.polygon(inner_points, outline=180, width=2)
        
        return mask
    
    def create_fractal_pattern(self, size):
        """分形图案模板"""
        mask = Image.new('L', (size, size), 0)
        draw = ImageDraw.Draw(mask)
        
        def draw_fractal(x, y, size, depth):
            if depth == 0:
                return
            
            # 绘制当前层级
            draw.ellipse([x-size, y-size, x+size, y+size], outline=255, width=2)
            
            # 递归绘制子层级
            num_children = random.randint(3, 6)
            for i in range(num_children):
                angle = 2 * np.pi * i / num_children
                child_size = size * random.uniform(0.2, 0.4)
                distance = size - child_size
                child_x = x + distance * np.cos(angle)
                child_y = y + distance * np.sin(angle)
                draw_fractal(child_x, child_y, child_size, depth-1)
        
        draw_fractal(size//2, size//2, size//3, random.randint(3, 5))
        return mask
    
    def create_crystal_lattice(self, size):
        """水晶晶格模板"""
        mask = Image.new('L', (size, size), 0)
        draw = ImageDraw.Draw(mask)
        
        center = size // 2
        base_radius = size // 2 - 20
        
        # 创建晶格结构
        num_rings = random.randint(3, 6)
        for ring in range(num_rings):
            radius = base_radius * (ring + 1) / num_rings
            num_points = random.randint(6, 12) * (ring + 1)
            
            points = []
            for i in range(num_points):
                angle = 2 * np.pi * i / num_points
                x = center + radius * np.cos(angle)
                y = center + radius * np.sin(angle)
                points.append((x, y))
            
            # 连接点形成晶格
            for i, point in enumerate(points):
                next_point = points[(i + random.randint(1, 3)) % len(points)]
                draw.line([point, next_point], fill=200, width=2)
        
        # 填充中心区域
        draw.ellipse([center-base_radius//3, center-base_radius//3,
                     center+base_radius//3, center+base_radius//3], fill=255)
        
        return mask
    
    def create_celestial_body(self, size):
        """天体模板"""
        mask = Image.new('L', (size, size), 0)
        draw = ImageDraw.Draw(mask)
        
        # 主圆形
        center = size // 2
        main_radius = size // 2 - 10
        draw.ellipse([center-main_radius, center-main_radius,
                     center+main_radius, center+main_radius], fill=255)
        
        # 添加行星环
        ring_radius = main_radius * 1.3
        ring_width = main_radius * 0.1
        for i in range(int(ring_width)):
            current_radius = ring_radius + i
            draw.ellipse([center-current_radius, center-current_radius,
                         center+current_radius, center+current_radius], 
                        outline=180, width=1)
        
        # 添加星点
        for _ in range(random.randint(20, 50)):
            angle = random.uniform(0, 2*np.pi)
            distance = random.uniform(main_radius*1.5, ring_radius*1.2)
            x = center + distance * np.cos(angle)
            y = center + distance * np.sin(angle)
            star_size = random.randint(1, 3)
            draw.ellipse([x-star_size, y-star_size, x+star_size, y+star_size], 
                        fill=255)
        
        return mask
    
    def create_ancient_symbol(self, size):
        """古代符号模板"""
        mask = Image.new('L', (size, size), 0)
        draw = ImageDraw.Draw(mask)
        
        center = size // 2
        radius = size // 2 - 15
        
        # 创建神秘符号
        symbols = [
            self._draw_mandala,
            self._draw_triskelion,
            self._draw_labyrinth,
            self._draw_sacred_geometry
        ]
        
        random.choice(symbols)(draw, center, radius)
        return mask
    
    def _draw_mandala(self, draw, center, radius):
        """绘制曼陀罗"""
        num_rings = 4
        for ring in range(num_rings):
            current_radius = radius * (ring + 1) / num_rings
            num_petals = 8 * (ring + 1)
            
            for i in range(num_petals):
                angle = 2 * np.pi * i / num_petals
                start_angle = angle - np.pi / num_petals
                end_angle = angle + np.pi / num_petals
                
                # 绘制花瓣
                points = []
                points.append((center, center))
                for a in [start_angle, end_angle]:
                    x = center + current_radius * np.cos(a)
                    y = center + current_radius * np.sin(a)
                    points.append((x, y))
                
                if len(points) >= 3:
                    draw.polygon(points, outline=255, fill=255 if ring % 2 == 0 else 0)
    
    def _draw_triskelion(self, draw, center, radius):
        """绘制三曲腿图"""
        for i in range(3):
            angle = 2 * np.pi * i / 3
            # 绘制螺旋臂
            points = []
            for t in np.linspace(0, 1, 50):
                spiral_angle = angle + t * 2 * np.pi
                spiral_radius = radius * (0.3 + 0.7 * t)
                x = center + spiral_radius * np.cos(spiral_angle)
                y = center + spiral_radius * np.sin(spiral_angle)
                points.append((x, y))
            
            if len(points) > 1:
                for j in range(len(points)-1):
                    draw.line([points[j], points[j+1]], fill=255, width=3)
    
    def create_modern_abstract(self, size):
        """现代抽象模板"""
        mask = Image.new('L', (size, size), 0)
        draw = ImageDraw.Draw(mask)
        
        # 随机抽象形状
        num_shapes = random.randint(3, 8)
        for _ in range(num_shapes):
            shape_type = random.choice(['circle', 'rectangle', 'polygon'])
            
            if shape_type == 'circle':
                x = random.randint(0, size)
                y = random.randint(0, size)
                radius = random.randint(20, size//3)
                draw.ellipse([x-radius, y-radius, x+radius, y+radius], 
                            fill=255, outline=200)
            
            elif shape_type == 'rectangle':
                x1, y1 = random.randint(0, size//2), random.randint(0, size//2)
                x2, y2 = random.randint(size//2, size), random.randint(size//2, size)
                draw.rectangle([x1, y1, x2, y2], fill=255, outline=200)
            
            else:  # polygon
                num_points = random.randint(3, 7)
                points = []
                for __ in range(num_points):
                    points.append((random.randint(0, size), random.randint(0, size)))
                draw.polygon(points, fill=255, outline=200)
        
        return mask
    
    def create_brushed_metal(self, size):
        """刷痕金属纹理"""
        texture = Image.new('L', (size, size), 128)
        pixels = texture.load()
        
        # 创建线性刷痕
        for i in range(size):
            for j in range(size):
                # 主要刷痕方向
                brush_value = 128 + int(50 * np.sin(i * 0.05 + j * 0.02))
                # 添加细微噪声
                noise = random.randint(-10, 10)
                pixels[i, j] = max(0, min(255, brush_value + noise))
        
        return texture.filter(ImageFilter.GaussianBlur(0.5))
    
    def create_gold_texture(self, size):
        """黄金纹理"""
        texture = Image.new('RGB', (size, size))
        pixels = texture.load()
        
        for i in range(size):
            for j in range(size):
                # 黄金色基值
                base_r, base_g, base_b = 255, 215, 0
                
                # 添加纹理变化
                variation = random.uniform(0.9, 1.1)
                r = int(base_r * variation)
                g = int(base_g * variation)
                b = int(base_b * variation)
                
                # 添加高光
                highlight = int(50 * np.sin(i * 0.1) * np.cos(j * 0.1))
                r = min(255, r + highlight)
                g = min(255, g + highlight)
                b = min(255, b + highlight)
                
                pixels[i, j] = (r, g, b)
        
        return texture
    
    def create_silver_texture(self, size):
        """白银纹理"""
        texture = Image.new('RGB', (size, size))
        pixels = texture.load()
        
        for i in range(size):
            for j in range(size):
                # 银白色基值
                base_r = base_g = base_b = 192
                
                # 冷色调变化
                coolness = random.uniform(0.95, 1.05)
                r = int(base_r * coolness)
                g = int(base_g * coolness)
                b = int(min(255, base_b * coolness * 1.1))  # 稍微偏蓝
                
                # 镜面反射效果
                reflection = int(30 * (np.sin(i * 0.2) + np.cos(j * 0.2)))
                r = g = b = min(255, base_r + reflection)
                
                pixels[i, j] = (r, g, b)
        
        return texture
    
    def create_bronze_texture(self, size):
        """青铜纹理"""
        texture = Image.new('RGB', (size, size))
        pixels = texture.load()
        
        for i in range(size):
            for j in range(size):
                # 青铜色基值
                base_r, base_g, base_b = 205, 127, 50
                
                # 氧化效果
                oxidation = random.uniform(0.8, 1.2)
                r = int(base_r * oxidation)
                g = int(base_g * oxidation)
                b = int(base_b * oxidation)
                
                # 绿锈效果
                if random.random() < 0.1:
                    r = int(r * 0.8)
                    g = int(g * 1.1)
                    b = int(b * 0.9)
                
                pixels[i, j] = (r, g, b)
        
        return texture
    
    def create_crystal_texture(self, size):
        """水晶纹理"""
        texture = Image.new('RGBA', (size, size), (255, 255, 255, 0))
        draw = ImageDraw.Draw(texture)
        
        # 创建水晶折射效果
        for _ in range(100):
            x = random.randint(0, size)
            y = random.randint(0, size)
            length = random.randint(10, 50)
            angle = random.uniform(0, 2*np.pi)
            
            # 水晶面
            points = []
            for i in range(3):
                a = angle + i * 2 * np.pi / 3
                px = x + length * np.cos(a)
                py = y + length * np.sin(a)
                points.append((px, py))
            
            alpha = random.randint(50, 150)
            color = (200, 230, 255, alpha)
            draw.polygon(points, fill=color, outline=(180, 210, 240, alpha))
        
        return texture
    
    def create_holographic_texture(self, size):
        """全息纹理"""
        texture = Image.new('RGB', (size, size))
        pixels = texture.load()
        
        for i in range(size):
            for j in range(size):
                # 彩虹全息效果
                hue = (i + j) / (size * 2) * 360
                saturation = 0.8
                value = 0.9 + 0.1 * np.sin(i * 0.1) * np.cos(j * 0.1)
                
                # HSV to RGB
                h_i = int(hue / 60) % 6
                f = hue / 60 - h_i
                p = value * (1 - saturation)
                q = value * (1 - f * saturation)
                t = value * (1 - (1 - f) * saturation)
                
                if h_i == 0: r, g, b = value, t, p
                elif h_i == 1: r, g, b = q, value, p
                elif h_i == 2: r, g, b = p, value, t
                elif h_i == 3: r, g, b = p, q, value
                elif h_i == 4: r, g, b = t, p, value
                else: r, g, b = value, p, q
                
                pixels[i, j] = (int(r*255), int(g*255), int(b*255))
        
        return texture
    
    def create_glowing_edge(self, size):
        """发光边缘纹理"""
        texture = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(texture)
        
        center = size // 2
        max_radius = size // 2 - 5
        
        # 创建发光渐变
        for radius in range(max_radius, max_radius-20, -1):
            alpha = int(255 * (1 - (max_radius - radius) / 20))
            color = (255, 255, 200, alpha)
            draw.ellipse([center-radius, center-radius, center+radius, center+radius], 
                        outline=color, width=1)
        
        return texture
    
    def create_engraved_texture(self, size):
        """雕刻纹理"""
        texture = Image.new('L', (size, size), 128)
        draw = ImageDraw.Draw(texture)
        
        # 创建雕刻图案
        for i in range(0, size, 20):
            for j in range(0, size, 20):
                if (i // 20 + j // 20) % 2 == 0:
                    # 交叉影线
                    draw.line([(i, j), (i+15, j+15)], fill=100, width=2)
                    draw.line([(i+15, j), (i, j+15)], fill=100, width=2)
                else:
                    # 点刻
                    for x in range(5):
                        for y in range(5):
                            px = i + x * 3
                            py = j + y * 3
                            draw.ellipse([px-1, py-1, px+1, py+1], fill=100)
        
        return texture.filter(ImageFilter.GaussianBlur(1))
    
    def create_coin_design(self, artistic_image, template_name, texture_name, 
                        coin_size=800, add_inscription=True):
        """创建完整的纪念币设计 - 修复纹理混合问题"""
        try:
            # 调整图像大小
            base_image = artistic_image.resize((coin_size, coin_size), Image.LANCZOS)
            
            # 应用模板
            if template_name in self.templates:
                mask = self.templates[template_name](coin_size)
            else:
                mask = self.templates['classic_circular'](coin_size)
            
            # 创建基础硬币
            coin_image = Image.new('RGBA', (coin_size, coin_size), (0, 0, 0, 0))
            coin_image.paste(base_image, (0, 0), mask)
            
            # 应用纹理
            if texture_name in self.textures:
                texture = self.textures[texture_name](coin_size)
                if texture.mode == 'RGBA':
                    # 确保纹理大小匹配
                    texture = texture.resize(coin_image.size)
                    coin_image = Image.alpha_composite(
                        coin_image.convert('RGBA'), 
                        texture
                    )
                else:
                    # 对于RGB纹理，转换为RGBA并混合
                    texture_rgba = texture.convert('RGBA')
                    texture_rgba = texture_rgba.resize(coin_image.size)
                    # 使用更安全的混合方式
                    coin_image = Image.blend(coin_image, texture_rgba, 0.3)
            
            # 添加铭文
            if add_inscription:
                coin_image = self._add_detailed_inscription(coin_image, template_name)
            
            return coin_image
            
        except Exception as e:
            print(f"创建硬币设计时出错: {e}")
            # 返回一个简单的圆形设计作为备选
            return self.create_fallback_design(artistic_image, coin_size)
    
    def create_fallback_design(self, image, size):
        """创建备选设计 - 当主设计失败时使用"""
        try:
            image = image.resize((size, size), Image.LANCZOS)
            mask = Image.new('L', (size, size), 0)
            draw = ImageDraw.Draw(mask)
            draw.ellipse([10, 10, size-10, size-10], fill=255)
            
            result = Image.new('RGBA', (size, size), (0, 0, 0, 0))
            result.paste(image, (0, 0), mask)
            
            # 添加简单的边框
            draw = ImageDraw.Draw(result)
            draw.ellipse([5, 5, size-5, size-5], outline=(255, 255, 255, 255), width=3)
            
            return result
        except Exception as e:
            print(f"备选设计也失败: {e}")
            # 最后的手段：返回原始图像
            return image.resize((size, size), Image.LANCZOS)
    
    def _add_detailed_inscription(self, image, template_name):
        """添加详细铭文"""
        draw = ImageDraw.Draw(image)
        size = image.size[0]
        
        try:
            # 尝试加载字体
            font_size_large = max(size // 25, 12)
            font_size_small = max(size // 35, 10)
            
            try:
                font_large = ImageFont.truetype("arial.ttf", font_size_large)
                font_small = ImageFont.truetype("arial.ttf", font_size_small)
            except:
                # 回退到默认字体
                font_large = ImageFont.load_default()
                font_small = ImageFont.load_default()
            
            # 顶部文字
            top_text = "AI ARTISTIC COIN"
            bbox = draw.textbbox((0, 0), top_text, font=font_large)
            text_width = bbox[2] - bbox[0]
            top_position = ((size - text_width) // 2, size // 10)
            
            # 底部文字
            date_text = datetime.now().strftime('%Y.%m.%d')
            bbox = draw.textbbox((0, 0), date_text, font=font_small)
            text_width = bbox[2] - bbox[0]
            bottom_position = ((size - text_width) // 2, size - size // 8)
            
            # 模板名称
            template_text = f"Style: {template_name.replace('_', ' ').title()}"
            bbox = draw.textbbox((0, 0), template_text, font=font_small)
            text_width = bbox[2] - bbox[0]
            style_position = ((size - text_width) // 2, size // 6)
            
            # 绘制带阴影的文字
            shadow_color = (0, 0, 0, 180)
            text_color = (255, 255, 255, 255)
            
            for text, position, font in [(top_text, top_position, font_large),
                                       (date_text, bottom_position, font_small),
                                       (template_text, style_position, font_small)]:
                # 阴影
                shadow_pos = (position[0] + 2, position[1] + 2)
                draw.text(shadow_pos, text, fill=shadow_color, font=font)
                # 主文字
                draw.text(position, text, fill=text_color, font=font)
                
        except Exception as e:
            print(f"文字渲染错误: {e}")
        
        return image

    def _draw_sacred_geometry(self, draw, center, radius):
        """绘制神圣几何图案 - 修复缺失的方法"""
        # 创建神圣几何图案（基于黄金比例）
        num_circles = 8
        golden_ratio = 1.618
        
        # 绘制同心圆和连接线
        for i in range(num_circles):
            current_radius = radius * (i + 1) / num_circles
            
            # 绘制圆
            draw.ellipse([center-current_radius, center-current_radius,
                        center+current_radius, center+current_radius], 
                        outline=255, width=2)
            
            # 绘制几何连接
            num_points = 12
            for j in range(num_points):
                angle1 = 2 * np.pi * j / num_points
                angle2 = 2 * np.pi * (j * golden_ratio) / num_points
                
                x1 = center + current_radius * np.cos(angle1)
                y1 = center + current_radius * np.sin(angle1)
                x2 = center + current_radius * np.cos(angle2)
                y2 = center + current_radius * np.sin(angle2)
                
                draw.line([(x1, y1), (x2, y2)], fill=200, width=1)
        
        # 添加中心符号
        center_size = radius * 0.1
        draw.rectangle([center-center_size, center-center_size,
                    center+center_size, center+center_size], 
                    fill=255, outline=255)
    
    def _draw_labyrinth(self, draw, center, radius):
        """绘制迷宫图案 - 修复：添加缺失的方法"""
        # 创建同心圆迷宫
        num_circles = 6
        for i in range(num_circles):
            current_radius = radius * (i + 1) / num_circles
            draw.ellipse([center-current_radius, center-current_radius,
                        center+current_radius, center+current_radius], 
                        outline=255, width=2)
        
        # 添加迷宫路径
        angles = [0, np.pi/2, np.pi, 3*np.pi/2]
        for i, angle in enumerate(angles):
            start_radius = radius * 0.2
            end_radius = radius * 0.8
            
            # 创建弯曲路径
            points = []
            for r in np.linspace(start_radius, end_radius, 20):
                # 添加随机波动
                wave_angle = angle + np.sin(r * 0.5) * 0.5
                x = center + r * np.cos(wave_angle)
                y = center + r * np.sin(wave_angle)
                points.append((x, y))
            
            # 绘制路径
            if len(points) > 1:
                for j in range(len(points)-1):
                    draw.line([points[j], points[j+1]], fill=255, width=3)
        
        # 添加中心点
        draw.ellipse([center-5, center-5, center+5, center+5], fill=255)
        
        # 添加入口和出口
        entrance_angle = random.uniform(0, 2*np.pi)
        entrance_x = center + radius * 0.9 * np.cos(entrance_angle)
        entrance_y = center + radius * 0.9 * np.sin(entrance_angle)
        draw.ellipse([entrance_x-8, entrance_y-8, entrance_x+8, entrance_y+8], 
                    outline=255, width=3)
        
        exit_angle = entrance_angle + np.pi  # 出口在对面
        exit_x = center + radius * 0.9 * np.cos(exit_angle)
        exit_y = center + radius * 0.9 * np.sin(exit_angle)
        draw.ellipse([exit_x-8, exit_y-8, exit_x+8, exit_y+8], 
                    outline=255, width=3)
    
class VideoProcessorThread(QThread):
    """视频处理线程"""
    progress_updated = pyqtSignal(int)
    frame_processed = pyqtSignal(object, object)  # (原始帧, 处理后的硬币)
    processing_finished = pyqtSignal()
    error_occurred = pyqtSignal(str)
    
    def __init__(self, video_paths, config):
        super().__init__()
        self.video_paths = video_paths
        self.config = config
        self.is_running = True
        
        # 初始化处理器
        self.neural_processor = AdvancedNeuralProcessor()
        self.coin_designer = AdvancedCoinDesigner()
        
    def run(self):
        """视频处理线程主循环 - 增强错误处理"""
        try:
            self.neural_processor.initialize_models()
            total_coins = self.config.get('coins_per_video', 5) * len(self.video_paths)
            coins_generated = 0
            
            for video_idx, video_path in enumerate(self.video_paths):
                if not self.is_running:
                    break
                    
                frames = self.extract_frames(video_path, self.config.get('coins_per_video', 5))
                
                for frame_idx, frame in enumerate(frames):
                    if not self.is_running:
                        break
                        
                    try:
                        # 设置随机模型
                        model_names = list(self.neural_processor.models.keys())
                        if model_names:
                            model_name = random.choice(model_names)
                            self.neural_processor.set_model(model_name)
                            
                            # 处理图像
                            artistic_image = self.neural_processor.process_image(
                                frame, 
                                self.config.get('style_intensity', 0.7),
                                self.config.get('iterations', 3)
                            )
                            
                            # 随机选择模板和纹理
                            template_name = random.choice(list(self.coin_designer.templates.keys()))
                            texture_name = random.choice(list(self.coin_designer.textures.keys()))
                            
                            # 创建硬币
                            coin_image = self.coin_designer.create_coin_design(
                                artistic_image,
                                template_name,
                                texture_name,
                                self.config.get('coin_size', 800),
                                self.config.get('add_inscription', True)
                            )
                            
                            # 发射信号
                            self.frame_processed.emit(frame, coin_image)
                            
                            coins_generated += 1
                            progress = int((coins_generated / total_coins) * 100)
                            self.progress_updated.emit(progress)
                            
                            # 添加延迟以便观察进度
                            self.msleep(100)
                            
                    except Exception as e:
                        print(f"处理单个帧时出错: {e}")
                        continue
            
            self.processing_finished.emit()
            
        except Exception as e:
            self.error_occurred.emit(str(e))
    
    def extract_frames(self, video_path, num_frames):
        """提取视频帧"""
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"无法打开视频文件: {video_path}")
            
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        frames = []
        
        # 均匀选择帧
        frame_indices = np.linspace(0, total_frames-1, min(num_frames, total_frames), dtype=int)
        
        for idx in frame_indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ret, frame = cap.read()
            if ret:
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frames.append(frame_rgb)
        
        cap.release()
        return frames
    
    def stop(self):
        """停止处理"""
        self.is_running = False

class MainWindow(QMainWindow):
    """主窗口"""
    
    def __init__(self):
        super().__init__()
        self.video_paths = []
        self.output_dir = "ai_coin_output"
        self.processing_thread = None
        self.generated_coins = []
        
        self.init_ui()
        self.setup_connections()
        
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("AI艺术纪念币生成器 - 高级版")
        self.setGeometry(100, 100, 1400, 900)
        
        # 创建中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QHBoxLayout(central_widget)
        
        # 左侧控制面板
        control_panel = self.create_control_panel()
        main_layout.addWidget(control_panel, 1)
        
        # 右侧显示区域
        display_area = self.create_display_area()
        main_layout.addWidget(display_area, 2)
        
        # 设置样式
        self.set_dark_theme()
        
    def create_control_panel(self):
        """创建控制面板"""
        panel = QWidget()
        panel.setMaximumWidth(400)
        layout = QVBoxLayout(panel)
        
        # 项目标题
        title = QLabel("AI艺术纪念币生成器")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #4FC3F7; padding: 10px;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # 视频选择区域
        video_group = QGroupBox("视频源选择")
        video_layout = QVBoxLayout(video_group)
        
        self.video_list = QListWidget()
        self.video_list.setMaximumHeight(120)
        video_layout.addWidget(QLabel("已选择的视频:"))
        video_layout.addWidget(self.video_list)
        
        btn_layout = QHBoxLayout()
        self.add_video_btn = QPushButton("添加视频")
        self.clear_videos_btn = QPushButton("清空列表")
        btn_layout.addWidget(self.add_video_btn)
        btn_layout.addWidget(self.clear_videos_btn)
        video_layout.addLayout(btn_layout)
        
        layout.addWidget(video_group)
        
        # 处理设置
        settings_group = QGroupBox("处理设置")
        settings_layout = QGridLayout(settings_group)
        
        # 每视频硬币数量
        settings_layout.addWidget(QLabel("每视频硬币数:"), 0, 0)
        self.coins_per_video = QSpinBox()
        self.coins_per_video.setRange(1, 50)
        self.coins_per_video.setValue(8)
        settings_layout.addWidget(self.coins_per_video, 0, 1)
        
        # 硬币尺寸
        settings_layout.addWidget(QLabel("硬币尺寸:"), 1, 0)
        self.coin_size = QComboBox()
        self.coin_size.addItems(["400x400", "600x600", "800x800", "1000x1000"])
        self.coin_size.setCurrentIndex(2)
        settings_layout.addWidget(self.coin_size, 1, 1)
        
        # 风格强度
        settings_layout.addWidget(QLabel("风格强度:"), 2, 0)
        self.style_intensity = QDoubleSpinBox()
        self.style_intensity.setRange(0.1, 1.0)
        self.style_intensity.setSingleStep(0.1)
        self.style_intensity.setValue(0.7)
        settings_layout.addWidget(self.style_intensity, 2, 1)
        
        # 迭代次数
        settings_layout.addWidget(QLabel("迭代次数:"), 3, 0)
        self.iterations = QSpinBox()
        self.iterations.setRange(1, 10)
        self.iterations.setValue(3)
        settings_layout.addWidget(self.iterations, 3, 1)
        
        # 复选框
        self.add_inscription = QCheckBox("添加铭文")
        self.add_inscription.setChecked(True)
        settings_layout.addWidget(self.add_inscription, 4, 0, 1, 2)
        
        self.randomize_weights = QCheckBox("随机化网络权重")
        self.randomize_weights.setChecked(True)
        settings_layout.addWidget(self.randomize_weights, 5, 0, 1, 2)
        
        layout.addWidget(settings_group)
        
        # 模板选择
        template_group = QGroupBox("模板偏好")
        template_layout = QVBoxLayout(template_group)
        
        self.template_combo = QComboBox()
        self.template_combo.addItems(["随机选择", "经典圆形", "几何多边形", "有机流动", 
                                    "分形图案", "水晶晶格", "天体", "古代符号", "现代抽象"])
        template_layout.addWidget(QLabel("首选模板:"))
        template_layout.addWidget(self.template_combo)
        
        self.texture_combo = QComboBox()
        self.texture_combo.addItems(["随机选择", "刷痕金属", "黄金镀层", "白银抛光", 
                                   "青铜古旧", "水晶透明", "全息效果", "发光边缘", "深度雕刻"])
        template_layout.addWidget(QLabel("首选纹理:"))
        template_layout.addWidget(self.texture_combo)
        
        layout.addWidget(template_group)
        
        # 进度区域
        progress_group = QGroupBox("处理进度")
        progress_layout = QVBoxLayout(progress_group)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        progress_layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("准备就绪")
        progress_layout.addWidget(self.status_label)
        
        # 控制按钮
        btn_layout = QHBoxLayout()
        self.start_btn = QPushButton("开始生成")
        self.stop_btn = QPushButton("停止生成")
        self.stop_btn.setEnabled(False)
        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.stop_btn)
        progress_layout.addLayout(btn_layout)
        
        # 输出目录
        output_layout = QHBoxLayout()
        self.output_btn = QPushButton("设置输出目录")
        self.output_label = QLabel(self.output_dir)
        self.output_label.setWordWrap(True)
        output_layout.addWidget(self.output_btn)
        progress_layout.addLayout(output_layout)
        progress_layout.addWidget(self.output_label)
        
        layout.addWidget(progress_group)
        
        # 日志区域
        log_group = QGroupBox("处理日志")
        log_layout = QVBoxLayout(log_group)
        
        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(150)
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)
        
        layout.addWidget(log_group)
        
        layout.addStretch()
        
        return panel
    
    def create_display_area(self):
        """创建显示区域"""
        container = QWidget()
        layout = QVBoxLayout(container)
        
        # 标签页
        self.tab_widget = QTabWidget()
        
        # 实时预览标签页
        preview_tab = QWidget()
        preview_layout = QVBoxLayout(preview_tab)
        
        # 原始帧显示
        preview_layout.addWidget(QLabel("原始视频帧:"))
        self.original_frame = QLabel()
        self.original_frame.setAlignment(Qt.AlignCenter)
        self.original_frame.setMinimumHeight(200)
        self.original_frame.setStyleSheet("background-color: #2b2b2b; border: 1px solid #555;")
        preview_layout.addWidget(self.original_frame)
        
        # 生成的硬币显示
        preview_layout.addWidget(QLabel("生成的纪念币:"))
        self.coin_preview = QLabel()
        self.coin_preview.setAlignment(Qt.AlignCenter)
        self.coin_preview.setMinimumHeight(300)
        self.coin_preview.setStyleSheet("background-color: #2b2b2b; border: 1px solid #555;")
        preview_layout.addWidget(self.coin_preview)
        
        self.tab_widget.addTab(preview_tab, "实时预览")
        
        # 画廊标签页
        gallery_tab = QWidget()
        gallery_layout = QVBoxLayout(gallery_tab)
        
        gallery_controls = QHBoxLayout()
        self.clear_gallery_btn = QPushButton("清空画廊")
        self.save_gallery_btn = QPushButton("保存所有硬币")
        gallery_controls.addWidget(self.clear_gallery_btn)
        gallery_controls.addWidget(self.save_gallery_btn)
        gallery_controls.addStretch()
        
        gallery_layout.addLayout(gallery_controls)
        
        # 创建滚动区域用于画廊
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        self.gallery_layout = QGridLayout(scroll_widget)
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        
        gallery_layout.addWidget(scroll_area)
        self.tab_widget.addTab(gallery_tab, "硬币画廊")
        
        # 统计信息标签页
        stats_tab = QWidget()
        stats_layout = QVBoxLayout(stats_tab)
        
        self.stats_text = QTextEdit()
        self.stats_text.setReadOnly(True)
        stats_layout.addWidget(self.stats_text)
        
        self.tab_widget.addTab(stats_tab, "统计信息")
        
        layout.addWidget(self.tab_widget)
        
        return container
    
    def setup_connections(self):
        """设置信号连接"""
        self.add_video_btn.clicked.connect(self.add_videos)
        self.clear_videos_btn.clicked.connect(self.clear_videos)
        self.start_btn.clicked.connect(self.start_processing)
        self.stop_btn.clicked.connect(self.stop_processing)
        self.output_btn.clicked.connect(self.set_output_directory)
        self.clear_gallery_btn.clicked.connect(self.clear_gallery)
        self.save_gallery_btn.clicked.connect(self.save_all_coins)
        
    def set_dark_theme(self):
        """设置深色主题"""
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
                background-color: #3c3c3c;
                border: 2px solid #555;
                border-radius: 5px;
                margin-top: 1ex;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #4FC3F7;
            }
            QPushButton {
                background-color: #4CAF50;
                border: none;
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #666;
                color: #999;
            }
            QPushButton#stop_btn {
                background-color: #f44336;
            }
            QPushButton#stop_btn:hover {
                background-color: #da190b;
            }
            QListWidget {
                background-color: #1e1e1e;
                border: 1px solid #555;
                color: #fff;
            }
            QProgressBar {
                border: 1px solid #555;
                border-radius: 4px;
                text-align: center;
                color: white;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 3px;
            }
            QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox {
                background-color: #1e1e1e;
                border: 1px solid #555;
                color: white;
                padding: 4px;
                border-radius: 3px;
            }
            QTabWidget::pane {
                border: 1px solid #555;
                background-color: #3c3c3c;
            }
            QTabBar::tab {
                background-color: #2b2b2b;
                color: white;
                padding: 8px 16px;
                border: 1px solid #555;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background-color: #4FC3F7;
                color: #000;
            }
            QLabel {
                color: #fff;
            }
        """)
        
        # 为停止按钮设置特殊样式
        self.stop_btn.setObjectName("stop_btn")
    
    def add_videos(self):
        """添加视频文件"""
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择视频文件", "", 
            "视频文件 (*.mp4 *.avi *.mov *.mkv *.wmv);;所有文件 (*)"
        )
        
        for file in files:
            if file not in self.video_paths:
                self.video_paths.append(file)
                self.video_list.addItem(Path(file).name)
        
        self.update_status(f"已添加 {len(files)} 个视频文件")
    
    def clear_videos(self):
        """清空视频列表"""
        self.video_paths.clear()
        self.video_list.clear()
        self.update_status("已清空视频列表")
    
    def set_output_directory(self):
        """设置输出目录"""
        directory = QFileDialog.getExistingDirectory(self, "选择输出目录")
        if directory:
            self.output_dir = directory
            self.output_label.setText(directory)
            self.update_status(f"输出目录设置为: {directory}")
    
    def start_processing(self):
        """开始处理"""
        if not self.video_paths:
            QMessageBox.warning(self, "警告", "请先添加视频文件")
            return
        
        # 创建输出目录
        Path(self.output_dir).mkdir(exist_ok=True)
        
        # 准备配置
        config = {
            'coins_per_video': self.coins_per_video.value(),
            'coin_size': int(self.coin_size.currentText().split('x')[0]),
            'style_intensity': self.style_intensity.value(),
            'iterations': self.iterations.value(),
            'add_inscription': self.add_inscription.isChecked(),
            'randomize_weights': self.randomize_weights.isChecked()
        }
        
        # 更新UI状态
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # 启动处理线程
        self.processing_thread = VideoProcessorThread(self.video_paths, config)
        self.processing_thread.progress_updated.connect(self.update_progress)
        self.processing_thread.frame_processed.connect(self.update_preview)
        self.processing_thread.processing_finished.connect(self.processing_finished)
        self.processing_thread.error_occurred.connect(self.handle_error)
        
        self.processing_thread.start()
        self.update_status("开始处理视频...")
    
    def stop_processing(self):
        """停止处理"""
        if self.processing_thread and self.processing_thread.isRunning():
            self.processing_thread.stop()
            self.processing_thread.wait()
            self.update_status("处理已停止")
        
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
    
    def update_progress(self, value):
        """更新进度"""
        self.progress_bar.setValue(value)
        self.update_status(f"处理进度: {value}%")
    
    def update_preview(self, original_frame, coin_image):
        """更新预览"""
        # 显示原始帧
        original_qimage = self.numpy_to_qimage(original_frame)
        original_pixmap = QPixmap.fromImage(original_qimage).scaled(
            400, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self.original_frame.setPixmap(original_pixmap)
        
        # 显示生成的硬币
        coin_qimage = self.pil_to_qimage(coin_image)
        coin_pixmap = QPixmap.fromImage(coin_qimage).scaled(
            400, 400, Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self.coin_preview.setPixmap(coin_pixmap)
        
        # 添加到画廊
        self.add_to_gallery(coin_image, len(self.generated_coins))
        self.generated_coins.append(coin_image)
        
        # 更新统计信息
        self.update_statistics()
    
    def add_to_gallery(self, coin_image, index):
        """添加到画廊"""
        # 创建画廊项
        gallery_item = QWidget()
        item_layout = QVBoxLayout(gallery_item)
        
        # 硬币图像
        coin_label = QLabel()
        coin_qimage = self.pil_to_qimage(coin_image)
        coin_pixmap = QPixmap.fromImage(coin_qimage).scaled(
            150, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        coin_label.setPixmap(coin_pixmap)
        coin_label.setAlignment(Qt.AlignCenter)
        
        # 保存按钮
        save_btn = QPushButton(f"保存 #{index+1}")
        save_btn.clicked.connect(lambda checked, idx=index: self.save_single_coin(idx))
        
        item_layout.addWidget(coin_label)
        item_layout.addWidget(save_btn)
        
        # 添加到画廊布局
        row = index // 4
        col = index % 4
        self.gallery_layout.addWidget(gallery_item, row, col)
    
    def clear_gallery(self):
        """清空画廊"""
        for i in reversed(range(self.gallery_layout.count())):
            widget = self.gallery_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()
        
        self.generated_coins.clear()
        self.update_status("画廊已清空")
    
    def save_single_coin(self, index):
        """保存单个硬币"""
        if 0 <= index < len(self.generated_coins):
            filename = f"coin_{index+1:04d}_{datetime.now().strftime('%H%M%S')}.png"
            filepath = Path(self.output_dir) / filename
            self.generated_coins[index].save(str(filepath), "PNG")
            self.update_status(f"已保存: {filename}")
    
    def save_all_coins(self):
        """保存所有硬币"""
        if not self.generated_coins:
            QMessageBox.information(self, "信息", "没有可保存的硬币")
            return
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        for i, coin in enumerate(self.generated_coins):
            filename = f"coin_{i+1:04d}_{timestamp}.png"
            filepath = Path(self.output_dir) / filename
            coin.save(str(filepath), "PNG")
        
        self.update_status(f"已保存 {len(self.generated_coins)} 枚硬币")
    
    def update_statistics(self):
        """更新统计信息"""
        stats = f"""
        AI艺术纪念币生成统计
        ====================
        
        生成的硬币数量: {len(self.generated_coins)}
        使用的视频数量: {len(self.video_paths)}
        输出目录: {self.output_dir}
        
        处理设置:
        - 每视频硬币数: {self.coins_per_video.value()}
        - 硬币尺寸: {self.coin_size.currentText()}
        - 风格强度: {self.style_intensity.value()}
        - 迭代次数: {self.iterations.value()}
        - 添加铭文: {'是' if self.add_inscription.isChecked() else '否'}
        
        最后更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        
        self.stats_text.setPlainText(stats)
    
    def processing_finished(self):
        """处理完成"""
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress_bar.setVisible(False)
        self.update_status("处理完成!")
        
        QMessageBox.information(self, "完成", 
                              f"已成功生成 {len(self.generated_coins)} 枚纪念币!")
    
    def handle_error(self, error_msg):
        """处理错误"""
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress_bar.setVisible(False)
        
        self.log_message(f"错误: {error_msg}")
        QMessageBox.critical(self, "错误", f"处理过程中发生错误:\n{error_msg}")
    
    def update_status(self, message):
        """更新状态"""
        self.status_label.setText(message)
        self.log_message(message)
    
    def log_message(self, message):
        """添加日志消息"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.log_text.append(f"[{timestamp}] {message}")
    
    def numpy_to_qimage(self, numpy_array):
        """numpy数组转QImage"""
        height, width, channel = numpy_array.shape
        bytes_per_line = 3 * width
        return QImage(numpy_array.data, width, height, bytes_per_line, QImage.Format_RGB888)
    
    def pil_to_qimage(self, pil_image):
        """PIL图像转QImage"""
        if pil_image.mode == "RGB":
            r, g, b = pil_image.split()
            pil_image = Image.merge("RGB", (b, g, r))
            buf = pil_image.tobytes()
            return QImage(buf, pil_image.size[0], pil_image.size[1], QImage.Format_RGB888)
        elif pil_image.mode == "RGBA":
            r, g, b, a = pil_image.split()
            pil_image = Image.merge("RGBA", (b, g, r, a))
            buf = pil_image.tobytes()
            return QImage(buf, pil_image.size[0], pil_image.size[1], QImage.Format_RGBA8888)
        else:
            return QImage()

def main():
    """主函数"""
    app = QApplication(sys.argv)
    
    # 设置应用程序信息
    app.setApplicationName("AI艺术纪念币生成器")
    app.setApplicationVersion("2.0")
    app.setOrganizationName("AI Art Studio")
    
    # 创建并显示主窗口
    window = MainWindow()
    window.show()
    
    # 启动事件循环
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()