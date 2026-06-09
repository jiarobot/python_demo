import sys
import os
import numpy as np
import json
from datetime import datetime
from PIL import Image, ImageFilter, ImageEnhance, ImageDraw, ImageFont, ImageOps
import cv2
import torch
import torch.nn as nn
import torchvision.transforms as transforms
from torchvision.models import vgg19
import dlib
import requests
from io import BytesIO
import random
import math

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QPushButton, QSlider, 
                             QFileDialog, QMessageBox, QComboBox, QSpinBox,
                             QDoubleSpinBox, QGroupBox, QCheckBox, QSplitter,
                             QTabWidget, QScrollArea, QFrame, QToolBar, QAction,
                             QColorDialog, QToolButton, QSizePolicy, QProgressBar,
                             QListWidget, QListWidgetItem, QDockWidget, QTextEdit,
                             QTableWidget, QTableWidgetItem, QHeaderView, QTreeWidget,
                             QTreeWidgetItem, QMenu, QInputDialog, QLineEdit)
from PyQt5.QtCore import Qt, QSize, pyqtSignal, QThread, QTimer, QSettings, QPoint, QRect
from PyQt5.QtGui import QPixmap, QImage, QIcon, QPainter, QPen, QColor, QFont, QPalette, QCursor

# ============================ AI模型相关 ============================

class SimpleNianHuaGAN(nn.Module):
    """简化的年画风格生成对抗网络"""
    def __init__(self):
        super(SimpleNianHuaGAN, self).__init__()
        # 生成器
        self.generator = nn.Sequential(
            nn.Conv2d(3, 64, 9, padding=4),
            nn.ReLU(),
            nn.Conv2d(64, 128, 3, stride=2, padding=1),
            nn.ReLU(),
            nn.Conv2d(128, 256, 3, stride=2, padding=1),
            nn.ReLU(),
            nn.ConvTranspose2d(256, 128, 3, stride=2, padding=1, output_padding=1),
            nn.ReLU(),
            nn.ConvTranspose2d(128, 64, 3, stride=2, padding=1, output_padding=1),
            nn.ReLU(),
            nn.Conv2d(64, 3, 9, padding=4),
            nn.Tanh()
        )
        
    def forward(self, x):
        return self.generator(x)

class AINianHuaModel:
    """AI年画生成模型"""
    
    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = SimpleNianHuaGAN().to(self.device)
        self.detector = dlib.get_frontal_face_detector()
        
        # 加载预训练的面部特征点检测器
        try:
            self.predictor = dlib.shape_predictor("shape_predictor_68_face_landmarks.dat")
        except:
            self.predictor = None
            
        # 图像预处理
        self.preprocess = transforms.Compose([
            transforms.Resize((256, 256)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5])
        ])
    
    def apply_ai_style(self, image, style_type="traditional"):
        """应用AI风格转换"""
        if isinstance(image, np.ndarray):
            pil_img = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        else:
            pil_img = image
            
        # 这里应该是实际的AI模型推理代码
        # 由于完整模型训练需要大量资源，这里使用传统方法模拟AI效果
        if style_type == "traditional":
            return self.simulate_traditional_style(pil_img)
        elif style_type == "ink_wash":
            return self.simulate_ink_wash_style(pil_img)
        elif style_type == "new_year":
            return self.simulate_new_year_style(pil_img)
        else:
            return pil_img
    
    def simulate_traditional_style(self, image):
        """模拟传统年画风格"""
        # 增强颜色
        enhancer = ImageEnhance.Color(image)
        image = enhancer.enhance(1.8)
        
        # 增强对比度
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.5)
        
        # 添加纹理
        texture = self.create_texture_pattern(image.size)
        image = Image.blend(image, texture, 0.1)
        
        return image
    
    def simulate_ink_wash_style(self, image):
        """模拟水墨画风格"""
        # 转换为灰度
        gray = image.convert('L')
        
        # 应用边缘检测
        edges = gray.filter(ImageFilter.FIND_EDGES)
        
        # 反转颜色
        edges = ImageOps.invert(edges)
        
        # 模糊边缘
        edges = edges.filter(ImageFilter.GaussianBlur(1))
        
        return edges.convert('RGB')
    
    def simulate_new_year_style(self, image):
        """模拟新年风格"""
        # 增强红色调
        np_img = np.array(image)
        np_img = np_img.astype(np.float32)
        
        # 增强红色通道
        np_img[:, :, 0] = np.minimum(np_img[:, :, 0] * 1.3, 255)
        
        # 降低蓝色通道
        np_img[:, :, 2] = np_img[:, :, 2] * 0.8
        
        np_img = np.clip(np_img, 0, 255).astype(np.uint8)
        
        return Image.fromarray(np_img)
    
    def create_texture_pattern(self, size):
        """创建纸质纹理"""
        texture = Image.new('RGB', size, (250, 240, 230))
        draw = ImageDraw.Draw(texture)
        
        # 添加细微纹理
        for i in range(0, size[0], 5):
            for j in range(0, size[1], 5):
                if (i + j) % 10 == 0:
                    draw.point((i, j), fill=(240, 230, 220))
                    
        return texture
    
    def detect_faces(self, image):
        """检测人脸并返回位置"""
        if isinstance(image, np.ndarray):
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = np.array(image.convert('L'))
            
        faces = self.detector(gray)
        return [(face.left(), face.top(), face.width(), face.height()) for face in faces]
    
    def beautify_face(self, image, face_rect):
        """美化面部"""
        x, y, w, h = face_rect
        
        # 提取面部区域
        face_region = image[y:y+h, x:x+w]
        
        # 应用美颜效果（简化版）
        # 高斯模糊
        face_region = cv2.GaussianBlur(face_region, (15, 15), 0)
        
        # 将处理后的区域放回原图
        result = image.copy()
        result[y:y+h, x:x+w] = face_region
        
        return result

# ============================ 高级图像处理工具 ============================

class AdvancedNianHuaTools:
    """增强版年画工具类"""
    
    @staticmethod
    def apply_ai_style_transfer(image, style_image=None, intensity=0.7):
        """应用AI风格迁移"""
        if isinstance(image, np.ndarray):
            pil_img = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        else:
            pil_img = image
            
        # 这里应该是实际的风格迁移算法
        # 简化实现：使用传统方法模拟风格迁移效果
        result = AdvancedNianHuaTools.apply_traditional_style(pil_img, intensity)
        
        if style_image is not None:
            # 如果有风格图像，进行混合
            if isinstance(style_image, np.ndarray):
                style_pil = Image.fromarray(cv2.cvtColor(style_image, cv2.COLOR_BGR2RGB))
            else:
                style_pil = style_image
                
            style_pil = style_pil.resize(pil_img.size)
            result = Image.blend(result, style_pil, 0.3)
            
        return result
    
    @staticmethod
    def apply_traditional_style(image, intensity=0.7):
        """应用传统年画风格"""
        if isinstance(image, np.ndarray):
            pil_img = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        else:
            pil_img = image
            
        # 增强对比度
        enhancer = ImageEnhance.Contrast(pil_img)
        pil_img = enhancer.enhance(1.3)
        
        # 增强饱和度
        enhancer = ImageEnhance.Color(pil_img)
        pil_img = enhancer.enhance(1.5)
        
        # 应用锐化
        pil_img = pil_img.filter(ImageFilter.SHARPEN)
        
        # 添加轻微油画效果
        pil_img = pil_img.filter(ImageFilter.MedianFilter(3))
        
        # 添加红色调（年画特色）
        r, g, b = pil_img.split()
        r = r.point(lambda i: min(i * 1.1, 255))
        pil_img = Image.merge('RGB', (r, g, b))
        
        return pil_img
    
    @staticmethod
    def add_woodblock_effect(image, intensity=0.7):
        """添加木版画效果"""
        if isinstance(image, np.ndarray):
            img_array = image
        else:
            img_array = np.array(image)
            if len(img_array.shape) == 3:
                img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        
        # 转换为灰度
        gray = cv2.cvtColor(img_array, cv2.COLOR_BGR2GRAY)
        
        # 应用边缘检测
        edges = cv2.Canny(gray, 50, 150)
        
        # 膨胀边缘以增强效果
        kernel = np.ones((3, 3), np.uint8)
        edges = cv2.dilate(edges, kernel, iterations=1)
        
        # 创建木版画效果
        result = np.zeros_like(img_array)
        result[edges > 0] = [0, 0, 0]  # 边缘为黑色
        result[edges == 0] = [255, 255, 255]  # 其他区域为白色
        
        # 添加木质纹理
        texture = AdvancedNianHuaTools.create_wood_texture(img_array.shape[:2])
        result = cv2.addWeighted(result, 1 - intensity, texture, intensity, 0)
        
        return Image.fromarray(cv2.cvtColor(result.astype(np.uint8), cv2.COLOR_BGR2RGB))
    
    @staticmethod
    def apply_ink_wash_effect(image, intensity=0.7):
        """应用水墨画效果"""
        if isinstance(image, np.ndarray):
            img_array = image
        else:
            img_array = np.array(image)
            if len(img_array.shape) == 3:
                img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        
        # 转换为灰度
        gray = cv2.cvtColor(img_array, cv2.COLOR_BGR2GRAY)
        
        # 应用高斯模糊
        blurred = cv2.GaussianBlur(gray, (15, 15), 0)
        
        # 应用自适应阈值
        thresh = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_MEAN_C, 
                                      cv2.THRESH_BINARY, 11, 2)
        
        # 反转图像
        thresh = 255 - thresh
        
        # 应用距离变换
        dist = cv2.distanceTransform(thresh, cv2.DIST_L2, 5)
        
        # 归一化距离变换
        cv2.normalize(dist, dist, 0, 1.0, cv2.NORM_MINMAX)
        
        # 创建水墨效果
        result = np.zeros_like(img_array)
        for i in range(3):
            result[:, :, i] = (dist * 255).astype(np.uint8)
        
        return Image.fromarray(cv2.cvtColor(result.astype(np.uint8), cv2.COLOR_BGR2RGB))
    
    @staticmethod
    def add_gold_foil_effect(image):
        """添加金箔效果"""
        if isinstance(image, np.ndarray):
            pil_img = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        else:
            pil_img = image
            
        # 创建金色渐变
        width, height = pil_img.size
        gold_gradient = Image.new('RGB', (width, height), (255, 215, 0))
        
        # 添加渐变效果
        for y in range(height):
            for x in range(width):
                r, g, b = pil_img.getpixel((x, y))
                # 计算亮度
                brightness = (r + g + b) / 3
                # 根据亮度混合金色
                if brightness > 128:
                    gold_r, gold_g, gold_b = gold_gradient.getpixel((x, y))
                    new_r = int(r * 0.3 + gold_r * 0.7)
                    new_g = int(g * 0.3 + gold_g * 0.7)
                    new_b = int(b * 0.3 + gold_b * 0.7)
                    gold_gradient.putpixel((x, y), (new_r, new_g, new_b))
        
        return gold_gradient
    
    @staticmethod
    def add_red_seal(image, text="福", position="bottom_right"):
        """添加红色印章"""
        if isinstance(image, np.ndarray):
            pil_img = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        else:
            pil_img = image
            
        # 创建印章图像
        seal_size = min(pil_img.size) // 5
        seal = Image.new('RGBA', (seal_size, seal_size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(seal)
        
        # 绘制圆形印章
        draw.ellipse([5, 5, seal_size-5, seal_size-5], outline=(255, 0, 0, 255), width=5)
        
        # 添加文字
        try:
            font = ImageFont.truetype("simhei.ttf", seal_size // 3)
        except:
            font = ImageFont.load_default()
        
        # 计算文字位置
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = (seal_size - text_width) // 2
        y = (seal_size - text_height) // 2
        
        draw.text((x, y), text, fill=(255, 0, 0, 255), font=font)
        
        # 确定印章位置
        if position == "bottom_right":
            x_pos = pil_img.width - seal_size - 20
            y_pos = pil_img.height - seal_size - 20
        elif position == "bottom_left":
            x_pos = 20
            y_pos = pil_img.height - seal_size - 20
        elif position == "top_right":
            x_pos = pil_img.width - seal_size - 20
            y_pos = 20
        else:  # top_left
            x_pos = 20
            y_pos = 20
        
        # 将印章添加到图像上
        pil_img = pil_img.convert('RGBA')
        pil_img.paste(seal, (x_pos, y_pos), seal)
        
        return pil_img.convert('RGB')
    
    @staticmethod
    def create_wood_texture(size):
        """创建木质纹理"""
        height, width = size
        texture = np.zeros((height, width, 3), dtype=np.uint8)
        
        # 基础木质颜色
        base_color = [160, 120, 80]
        
        # 添加木质纹理
        for y in range(height):
            for x in range(width):
                # 添加木纹效果
                wood_grain = math.sin(x / 20) * 10 + math.sin(y / 30) * 5
                noise = random.randint(-10, 10)
                
                r = max(0, min(255, base_color[0] + wood_grain + noise))
                g = max(0, min(255, base_color[1] + wood_grain + noise))
                b = max(0, min(255, base_color[2] + wood_grain + noise))
                
                texture[y, x] = [b, g, r]  # OpenCV使用BGR格式
        
        return texture
    
    @staticmethod
    def semantic_segmentation(image):
        """语义分割（简化版）"""
        if isinstance(image, np.ndarray):
            img_array = image
        else:
            img_array = np.array(image)
            if len(img_array.shape) == 3:
                img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        
        # 简化版语义分割 - 使用颜色阈值
        hsv = cv2.cvtColor(img_array, cv2.COLOR_BGR2HSV)
        
        # 检测红色区域（常用于年画）
        lower_red = np.array([0, 50, 50])
        upper_red = np.array([10, 255, 255])
        mask_red = cv2.inRange(hsv, lower_red, upper_red)
        
        # 检测皮肤区域
        lower_skin = np.array([0, 20, 70])
        upper_skin = np.array([20, 255, 255])
        mask_skin = cv2.inRange(hsv, lower_skin, upper_skin)
        
        # 创建分割结果
        height, width = img_array.shape[:2]
        segmentation = np.zeros((height, width, 3), dtype=np.uint8)
        
        # 红色区域
        segmentation[mask_red > 0] = [255, 0, 0]  # 红色
        
        # 皮肤区域
        segmentation[mask_skin > 0] = [255, 200, 150]  # 肤色
        
        # 其他区域
        gray = cv2.cvtColor(img_array, cv2.COLOR_BGR2GRAY)
        segmentation[(mask_red == 0) & (mask_skin == 0)] = [gray, gray, gray][(mask_red == 0) & (mask_skin == 0)]
        
        return Image.fromarray(cv2.cvtColor(segmentation, cv2.COLOR_BGR2RGB))
    
    @staticmethod
    def apply_artistic_filter(image, filter_type="watercolor", intensity=0.5):
        """应用艺术滤镜"""
        if isinstance(image, np.ndarray):
            pil_img = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        else:
            pil_img = image
            
        if filter_type == "watercolor":
            # 水彩画效果
            result = pil_img.filter(ImageFilter.GaussianBlur(1))
            for _ in range(2):
                result = result.filter(ImageFilter.MedianFilter(3))
        elif filter_type == "oil_painting":
            # 油画效果
            result = pil_img.filter(ImageFilter.MedianFilter(5))
        elif filter_type == "pencil_sketch":
            # 铅笔素描效果
            gray = pil_img.convert('L')
            inverted = ImageOps.invert(gray)
            blurred = inverted.filter(ImageFilter.GaussianBlur(10))
            result = Image.blend(gray, blurred, 0.7)
            result = result.convert('RGB')
        else:
            result = pil_img
            
        return Image.blend(pil_img, result, intensity)
    
    @staticmethod
    def create_collage(images, layout="grid", background_color=(255, 255, 255)):
        """创建拼贴画"""
        if not images:
            return None
            
        if layout == "grid":
            # 网格布局
            cols = int(np.ceil(np.sqrt(len(images))))
            rows = int(np.ceil(len(images) / cols))
            
            # 计算每个图像的大小
            sample_img = images[0]
            if isinstance(sample_img, np.ndarray):
                h, w = sample_img.shape[:2]
            else:
                w, h = sample_img.size
                
            collage_width = w * cols
            collage_height = h * rows
            
            # 创建画布
            collage = Image.new('RGB', (collage_width, collage_height), background_color)
            
            # 排列图像
            for i, img in enumerate(images):
                if isinstance(img, np.ndarray):
                    img_pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
                else:
                    img_pil = img
                    
                # 调整大小
                img_pil = img_pil.resize((w, h))
                
                # 计算位置
                row = i // cols
                col = i % cols
                x = col * w
                y = row * h
                
                collage.paste(img_pil, (x, y))
                
            return collage
            
        elif layout == "circle":
            # 圆形布局
            # 简化实现 - 返回第一个图像
            return images[0] if isinstance(images[0], Image.Image) else Image.fromarray(
                cv2.cvtColor(images[0], cv2.COLOR_BGR2RGB))
        
        return images[0] if isinstance(images[0], Image.Image) else Image.fromarray(
            cv2.cvtColor(images[0], cv2.COLOR_BGR2RGB))
    
    @staticmethod
    def add_animated_effect(image, effect_type="sparkle"):
        """添加动画效果（返回多帧图像）"""
        if isinstance(image, np.ndarray):
            base_img = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        else:
            base_img = image
            
        frames = []
        
        if effect_type == "sparkle":
            # 闪烁效果
            for i in range(5):
                frame = base_img.copy()
                if i % 2 == 0:
                    # 添加闪光点
                    draw = ImageDraw.Draw(frame)
                    width, height = frame.size
                    for _ in range(20):
                        x = np.random.randint(0, width)
                        y = np.random.randint(0, height)
                        size = np.random.randint(2, 6)
                        draw.ellipse([x, y, x+size, y+size], fill=(255, 255, 200))
                frames.append(frame)
                
        elif effect_type == "glow":
            # 发光效果
            for i in range(5):
                frame = base_img.copy()
                # 添加发光边框
                border_size = 10 + i * 2
                border_color = (255, 200, 100, 100)
                
                # 创建边框图像
                border = Image.new('RGBA', frame.size, (0, 0, 0, 0))
                draw = ImageDraw.Draw(border)
                draw.rectangle([0, 0, frame.size[0]-1, frame.size[1]-1], 
                              outline=border_color, width=border_size)
                
                # 合并边框
                frame = frame.convert('RGBA')
                frame = Image.alpha_composite(frame, border)
                frames.append(frame)
                
        return frames
    
    @staticmethod
    def apply_3d_effect(image, depth_map=None):
        """应用3D效果（需要深度图）"""
        if isinstance(image, np.ndarray):
            img_array = image
        else:
            img_array = np.array(image)
            if len(img_array.shape) == 3:
                img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
                
        if depth_map is None:
            # 生成简单的深度图（基于边缘检测）
            gray = cv2.cvtColor(img_array, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 50, 150)
            depth_map = cv2.GaussianBlur(edges, (15, 15), 0)
            
        # 应用深度效果（简化版）
        result = img_array.copy()
        for y in range(img_array.shape[0]):
            shift = int(depth_map[y].mean() / 20)
            if shift > 0:
                result[y, shift:] = img_array[y, :-shift]
                
        return Image.fromarray(cv2.cvtColor(result, cv2.COLOR_BGR2RGB))
    
    @staticmethod
    def add_text_to_image(image, text, position=(0, 0), font_size=30, color=(255, 0, 0)):
        """在图像上添加文字"""
        if isinstance(image, np.ndarray):
            pil_img = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        else:
            pil_img = image
            
        draw = ImageDraw.Draw(pil_img)
        
        try:
            font = ImageFont.truetype("simhei.ttf", font_size)
        except:
            font = ImageFont.load_default()
            
        draw.text(position, text, fill=color, font=font)
        
        return pil_img
    
    @staticmethod
    def apply_cartoon_effect(image):
        """应用卡通效果"""
        if isinstance(image, np.ndarray):
            img_array = image
        else:
            img_array = np.array(image)
            if len(img_array.shape) == 3:
                img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        
        # 应用双边滤波
        color = cv2.bilateralFilter(img_array, 9, 300, 300)
        
        # 转换为灰度
        gray = cv2.cvtColor(img_array, cv2.COLOR_BGR2GRAY)
        
        # 应用中值滤波
        gray = cv2.medianBlur(gray, 7)
        
        # 检测边缘
        edges = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, 
                                     cv2.THRESH_BINARY, 9, 2)
        
        # 转换为彩色边缘
        edges = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
        
        # 合并颜色和边缘
        cartoon = cv2.bitwise_and(color, edges)
        
        return Image.fromarray(cv2.cvtColor(cartoon, cv2.COLOR_BGR2RGB))
    
    @staticmethod
    def enhance_image_quality(image, sharpness=1.5, brightness=1.1, contrast=1.2):
        """增强图像质量"""
        if isinstance(image, np.ndarray):
            pil_img = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        else:
            pil_img = image
            
        # 增强锐度
        enhancer = ImageEnhance.Sharpness(pil_img)
        pil_img = enhancer.enhance(sharpness)
        
        # 增强亮度
        enhancer = ImageEnhance.Brightness(pil_img)
        pil_img = enhancer.enhance(brightness)
        
        # 增强对比度
        enhancer = ImageEnhance.Contrast(pil_img)
        pil_img = enhancer.enhance(contrast)
        
        return pil_img

# ============================ 高级UI组件 ============================

class HistoryItemWidget(QWidget):
    """历史记录项组件"""
    def __init__(self, thumbnail, timestamp, operation, parent=None):
        super().__init__(parent)
        self.thumbnail = thumbnail
        self.timestamp = timestamp
        self.operation = operation
        
        self.init_ui()
        
    def init_ui(self):
        layout = QHBoxLayout()
        
        # 缩略图
        thumbnail_label = QLabel()
        pixmap = QPixmap.fromImage(self.thumbnail)
        thumbnail_label.setPixmap(pixmap.scaled(60, 60, Qt.KeepAspectRatio))
        layout.addWidget(thumbnail_label)
        
        # 信息
        info_layout = QVBoxLayout()
        info_layout.addWidget(QLabel(f"操作: {self.operation}"))
        info_layout.addWidget(QLabel(f"时间: {self.timestamp}"))
        
        layout.addLayout(info_layout)
        self.setLayout(layout)

class LayerItemWidget(QWidget):
    """图层项组件"""
    def __init__(self, name, visible=True, parent=None):
        super().__init__(parent)
        self.name = name
        self.visible = visible
        
        self.init_ui()
        
    def init_ui(self):
        layout = QHBoxLayout()
        
        # 可见性复选框
        self.visibility_check = QCheckBox()
        self.visibility_check.setChecked(self.visible)
        layout.addWidget(self.visibility_check)
        
        # 图层名称
        name_label = QLabel(self.name)
        layout.addWidget(name_label)
        
        layout.addStretch()
        self.setLayout(layout)

class AdvancedImageViewer(QWidget):
    """高级图像查看器，支持缩放、平移等操作"""
    def __init__(self):
        super().__init__()
        self.original_pixmap = None
        self.current_scale = 1.0
        self.max_scale = 5.0
        self.min_scale = 0.1
        self.pan_start = QPoint()
        self.pan_offset = QPoint(0, 0)
        self.is_panning = False
        
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 工具栏
        toolbar = QHBoxLayout()
        
        self.zoom_in_btn = QPushButton("放大")
        self.zoom_in_btn.clicked.connect(self.zoom_in)
        toolbar.addWidget(self.zoom_in_btn)
        
        self.zoom_out_btn = QPushButton("缩小")
        self.zoom_out_btn.clicked.connect(self.zoom_out)
        toolbar.addWidget(self.zoom_out_btn)
        
        self.reset_view_btn = QPushButton("重置视图")
        self.reset_view_btn.clicked.connect(self.reset_view)
        toolbar.addWidget(self.reset_view_btn)
        
        toolbar.addStretch()
        layout.addLayout(toolbar)
        
        # 图像显示区域
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("border: 1px solid gray; background-color: white;")
        self.image_label.setMinimumSize(400, 300)
        
        # 启用鼠标跟踪
        self.image_label.setMouseTracking(True)
        self.image_label.mousePressEvent = self.mouse_press_event
        self.image_label.mouseMoveEvent = self.mouse_move_event
        self.image_label.mouseReleaseEvent = self.mouse_release_event
        
        layout.addWidget(self.image_label)
        self.setLayout(layout)
        
    def set_image(self, image):
        """设置图像"""
        if image is None:
            self.image_label.clear()
            self.original_pixmap = None
            return
            
        # 转换为QPixmap
        if isinstance(image, np.ndarray):
            # 转换OpenCV图像为QImage
            if len(image.shape) == 2:  # 灰度图
                h, w = image.shape
                bytes_per_line = w
                q_img = QImage(image.data, w, h, bytes_per_line, QImage.Format_Grayscale8)
            else:  # 彩色图
                h, w, ch = image.shape
                bytes_per_line = ch * w
                rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                q_img = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        else:
            # 如果是PIL图像，转换为QImage
            if image.mode == "RGB":
                r, g, b = image.split()
                image = Image.merge("RGB", (b, g, r))
                data = image.tobytes("raw", "RGB")
                q_img = QImage(data, image.size[0], image.size[1], QImage.Format_RGB888)
            elif image.mode == "RGBA":
                r, g, b, a = image.split()
                image = Image.merge("RGBA", (b, g, r, a))
                data = image.tobytes("raw", "RGBA")
                q_img = QImage(data, image.size[0], image.size[1], QImage.Format_RGBA8888)
            else:
                # 转换为RGB
                image = image.convert("RGB")
                r, g, b = image.split()
                image = Image.merge("RGB", (b, g, r))
                data = image.tobytes("raw", "RGB")
                q_img = QImage(data, image.size[0], image.size[1], QImage.Format_RGB888)
        
        self.original_pixmap = QPixmap.fromImage(q_img)
        self.reset_view()
        
    def reset_view(self):
        """重置视图"""
        self.current_scale = 1.0
        self.pan_offset = QPoint(0, 0)
        self.update_display()
        
    def zoom_in(self):
        """放大"""
        if self.original_pixmap:
            self.current_scale = min(self.current_scale * 1.2, self.max_scale)
            self.update_display()
            
    def zoom_out(self):
        """缩小"""
        if self.original_pixmap:
            self.current_scale = max(self.current_scale / 1.2, self.min_scale)
            self.update_display()
            
    def update_display(self):
        """更新显示"""
        if self.original_pixmap:
            # 计算缩放后的尺寸
            scaled_width = int(self.original_pixmap.width() * self.current_scale)
            scaled_height = int(self.original_pixmap.height() * self.current_scale)
            
            # 缩放图像
            scaled_pixmap = self.original_pixmap.scaled(
                scaled_width, scaled_height, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            
            # 创建显示图像（考虑平移）
            display_pixmap = QPixmap(self.image_label.size())
            display_pixmap.fill(Qt.white)
            
            painter = QPainter(display_pixmap)
            
            # 计算绘制位置（居中 + 平移）
            x_offset = (self.image_label.width() - scaled_pixmap.width()) // 2 + self.pan_offset.x()
            y_offset = (self.image_label.height() - scaled_pixmap.height()) // 2 + self.pan_offset.y()
            
            painter.drawPixmap(x_offset, y_offset, scaled_pixmap)
            painter.end()
            
            self.image_label.setPixmap(display_pixmap)
            
    def mouse_press_event(self, event):
        """鼠标按下事件"""
        if event.button() == Qt.LeftButton:
            self.is_panning = True
            self.pan_start = event.pos()
            self.image_label.setCursor(QCursor(Qt.ClosedHandCursor))
            
    def mouse_move_event(self, event):
        """鼠标移动事件"""
        if self.is_panning and self.original_pixmap:
            delta = event.pos() - self.pan_start
            self.pan_offset += delta
            self.pan_start = event.pos()
            self.update_display()
            
    def mouse_release_event(self, event):
        """鼠标释放事件"""
        if event.button() == Qt.LeftButton:
            self.is_panning = False
            self.image_label.setCursor(QCursor(Qt.ArrowCursor))

# ============================ 批量处理线程 ============================

class BatchProcessingThread(QThread):
    """批量处理线程"""
    progress_updated = pyqtSignal(int)
    finished_batch = pyqtSignal()
    
    def __init__(self, file_paths, process_function):
        super().__init__()
        self.file_paths = file_paths
        self.process_function = process_function
        self.output_dir = "output"
        
    def run(self):
        """执行批量处理"""
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            
        total_files = len(self.file_paths)
        for i, file_path in enumerate(self.file_paths):
            try:
                # 处理图像
                image = cv2.imread(file_path)
                if image is not None:
                    processed_image = self.process_function(image)
                    
                    # 保存处理后的图像
                    filename = os.path.basename(file_path)
                    output_path = os.path.join(self.output_dir, f"processed_{filename}")
                    cv2.imwrite(output_path, processed_image)
                    
                # 更新进度
                progress = int((i + 1) / total_files * 100)
                self.progress_updated.emit(progress)
                
            except Exception as e:
                print(f"处理文件 {file_path} 时出错: {str(e)}")
                
        self.finished_batch.emit()

# ============================ 主系统 ============================

class EnhancedNianHuaSystem(QMainWindow):
    """增强版智能年画系统"""
    
    def __init__(self):
        super().__init__()
        self.current_image = None
        self.processed_image = None
        self.original_image = None
        self.ai_model = AINianHuaModel()
        self.history = []
        self.layers = []
        self.current_layer = 0
        self.settings = QSettings("NianHuaStudio", "SmartNianHua")
        self.batch_thread = None
        
        self.init_ui()
        self.load_settings()
        
    def init_ui(self):
        self.setWindowTitle("智能年画系统 - 专业版")
        self.setGeometry(100, 50, 1600, 1000)
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QHBoxLayout(central_widget)
        
        # 左侧面板（工具箱和图层）
        left_panel = QVBoxLayout()
        left_panel.setContentsMargins(0, 0, 0, 0)
        
        # 工具箱
        self.tool_tabs = QTabWidget()
        self.create_basic_tools_tab()
        self.create_ai_tools_tab()
        self.create_advanced_tools_tab()
        self.create_batch_tools_tab()
        left_panel.addWidget(self.tool_tabs)
        
        # 图层面板
        layer_group = QGroupBox("图层")
        layer_layout = QVBoxLayout()
        
        self.layer_list = QListWidget()
        self.layer_list.itemClicked.connect(self.on_layer_selected)
        layer_layout.addWidget(self.layer_list)
        
        layer_buttons = QHBoxLayout()
        self.add_layer_btn = QPushButton("添加图层")
        self.add_layer_btn.clicked.connect(self.add_layer)
        layer_buttons.addWidget(self.add_layer_btn)
        
        self.remove_layer_btn = QPushButton("删除图层")
        self.remove_layer_btn.clicked.connect(self.remove_layer)
        layer_buttons.addWidget(self.remove_layer_btn)
        
        layer_layout.addLayout(layer_buttons)
        layer_group.setLayout(layer_layout)
        left_panel.addWidget(layer_group)
        
        main_layout.addLayout(left_panel)
        
        # 右侧面板（图像显示和历史）
        right_panel = QVBoxLayout()
        
        # 工具栏
        toolbar = QToolBar()
        self.add_toolbar_actions(toolbar)
        right_panel.addWidget(toolbar)
        
        # 图像显示区域
        self.image_viewer = AdvancedImageViewer()
        right_panel.addWidget(self.image_viewer, 1)
        
        # 历史记录
        history_group = QGroupBox("历史记录")
        history_layout = QVBoxLayout()
        
        self.history_list = QListWidget()
        self.history_list.itemClicked.connect(self.on_history_selected)
        history_layout.addWidget(self.history_list)
        
        history_group.setLayout(history_layout)
        right_panel.addWidget(history_group)
        
        main_layout.addLayout(right_panel, 1)
        
        # 创建状态栏
        self.statusBar().showMessage("就绪")
        
        # 创建菜单栏
        self.create_menus()
        
    def create_menus(self):
        """创建菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu('文件')
        
        new_action = QAction('新建', self)
        new_action.setShortcut('Ctrl+N')
        new_action.triggered.connect(self.new_file)
        file_menu.addAction(new_action)
        
        open_action = QAction('打开', self)
        open_action.setShortcut('Ctrl+O')
        open_action.triggered.connect(self.open_image)
        file_menu.addAction(open_action)
        
        save_action = QAction('保存', self)
        save_action.setShortcut('Ctrl+S')
        save_action.triggered.connect(self.save_image)
        file_menu.addAction(save_action)
        
        file_menu.addSeparator()
        
        batch_action = QAction('批量处理', self)
        batch_action.triggered.connect(self.batch_process)
        file_menu.addAction(batch_action)
        
        # 编辑菜单
        edit_menu = menubar.addMenu('编辑')
        
        undo_action = QAction('撤销', self)
        undo_action.setShortcut('Ctrl+Z')
        undo_action.triggered.connect(self.undo)
        edit_menu.addAction(undo_action)
        
        redo_action = QAction('重做', self)
        redo_action.setShortcut('Ctrl+Y')
        redo_action.triggered.connect(self.redo)
        edit_menu.addAction(redo_action)
        
        # 视图菜单
        view_menu = menubar.addMenu('视图')
        
        zoom_in_action = QAction('放大', self)
        zoom_in_action.setShortcut('Ctrl++')
        zoom_in_action.triggered.connect(self.image_viewer.zoom_in)
        view_menu.addAction(zoom_in_action)
        
        zoom_out_action = QAction('缩小', self)
        zoom_out_action.setShortcut('Ctrl+-')
        zoom_out_action.triggered.connect(self.image_viewer.zoom_out)
        view_menu.addAction(zoom_out_action)
        
        reset_view_action = QAction('重置视图', self)
        reset_view_action.setShortcut('Ctrl+0')
        reset_view_action.triggered.connect(self.image_viewer.reset_view)
        view_menu.addAction(reset_view_action)
        
    def add_toolbar_actions(self, toolbar):
        """添加工具栏操作"""
        self.open_btn = QAction(QIcon(), "打开", self)
        self.open_btn.triggered.connect(self.open_image)
        toolbar.addAction(self.open_btn)
        
        self.save_btn = QAction(QIcon(), "保存", self)
        self.save_btn.triggered.connect(self.save_image)
        toolbar.addAction(self.save_btn)
        
        toolbar.addSeparator()
        
        self.undo_btn = QAction(QIcon(), "撤销", self)
        self.undo_btn.triggered.connect(self.undo)
        toolbar.addAction(self.undo_btn)
        
        self.redo_btn = QAction(QIcon(), "重做", self)
        self.redo_btn.triggered.connect(self.redo)
        toolbar.addAction(self.redo_btn)
        
        toolbar.addSeparator()
        
        self.reset_btn = QAction(QIcon(), "重置", self)
        self.reset_btn.triggered.connect(self.reset_image)
        toolbar.addAction(self.reset_btn)
        
    def create_basic_tools_tab(self):
        """创建基础工具选项卡"""
        basic_tab = QWidget()
        layout = QVBoxLayout()
        
        # 传统风格组
        style_group = QGroupBox("传统风格")
        style_layout = QVBoxLayout()
        
        self.traditional_btn = QPushButton("传统年画风格")
        self.traditional_btn.clicked.connect(lambda: self.apply_effect("traditional"))
        style_layout.addWidget(self.traditional_btn)
        
        self.woodblock_btn = QPushButton("木版画效果")
        self.woodblock_btn.clicked.connect(lambda: self.apply_effect("woodblock"))
        style_layout.addWidget(self.woodblock_btn)
        
        self.ink_wash_btn = QPushButton("水墨画效果")
        self.ink_wash_btn.clicked.connect(lambda: self.apply_effect("ink_wash"))
        style_layout.addWidget(self.ink_wash_btn)
        
        style_group.setLayout(style_layout)
        layout.addWidget(style_group)
        
        # 装饰效果组
        decor_group = QGroupBox("装饰效果")
        decor_layout = QVBoxLayout()
        
        self.gold_foil_btn = QPushButton("金箔效果")
        self.gold_foil_btn.clicked.connect(lambda: self.apply_effect("gold_foil"))
        decor_layout.addWidget(self.gold_foil_btn)
        
        self.red_seal_btn = QPushButton("添加印章")
        self.red_seal_btn.clicked.connect(lambda: self.apply_effect("red_seal"))
        decor_layout.addWidget(self.red_seal_btn)
        
        self.add_text_btn = QPushButton("添加文字")
        self.add_text_btn.clicked.connect(self.add_text_to_image)
        decor_layout.addWidget(self.add_text_btn)
        
        decor_group.setLayout(decor_layout)
        layout.addWidget(decor_group)
        
        # 图像增强组
        enhance_group = QGroupBox("图像增强")
        enhance_layout = QVBoxLayout()
        
        self.enhance_btn = QPushButton("增强图像质量")
        self.enhance_btn.clicked.connect(self.enhance_image_quality)
        enhance_layout.addWidget(self.enhance_btn)
        
        enhance_group.setLayout(enhance_layout)
        layout.addWidget(enhance_group)
        
        layout.addStretch()
        basic_tab.setLayout(layout)
        self.tool_tabs.addTab(basic_tab, "基础工具")
        
    def create_ai_tools_tab(self):
        """创建AI工具选项卡"""
        ai_tab = QWidget()
        layout = QVBoxLayout()
        
        # AI风格组
        ai_group = QGroupBox("AI风格转换")
        ai_layout = QVBoxLayout()
        
        self.ai_traditional_btn = QPushButton("AI传统年画")
        self.ai_traditional_btn.clicked.connect(lambda: self.apply_ai_effect("traditional"))
        ai_layout.addWidget(self.ai_traditional_btn)
        
        self.ai_ink_wash_btn = QPushButton("AI水墨风格")
        self.ai_ink_wash_btn.clicked.connect(lambda: self.apply_ai_effect("ink_wash"))
        ai_layout.addWidget(self.ai_ink_wash_btn)
        
        self.ai_new_year_btn = QPushButton("AI新年风格")
        self.ai_new_year_btn.clicked.connect(lambda: self.apply_ai_effect("new_year"))
        ai_layout.addWidget(self.ai_new_year_btn)
        
        ai_group.setLayout(ai_layout)
        layout.addWidget(ai_group)
        
        # 人脸美化组
        face_group = QGroupBox("人脸美化")
        face_layout = QVBoxLayout()
        
        self.face_detect_btn = QPushButton("检测人脸")
        self.face_detect_btn.clicked.connect(self.detect_faces)
        face_layout.addWidget(self.face_detect_btn)
        
        self.face_beautify_btn = QPushButton("美颜")
        self.face_beautify_btn.clicked.connect(self.beautify_faces)
        face_layout.addWidget(self.face_beautify_btn)
        
        face_group.setLayout(face_layout)
        layout.addWidget(face_group)
        
        layout.addStretch()
        ai_tab.setLayout(layout)
        self.tool_tabs.addTab(ai_tab, "AI工具")
        
    def create_advanced_tools_tab(self):
        """创建高级工具选项卡"""
        advanced_tab = QWidget()
        layout = QVBoxLayout()
        
        # 艺术滤镜组
        filter_group = QGroupBox("艺术滤镜")
        filter_layout = QVBoxLayout()
        
        self.watercolor_btn = QPushButton("水彩画")
        self.watercolor_btn.clicked.connect(lambda: self.apply_artistic_filter("watercolor"))
        filter_layout.addWidget(self.watercolor_btn)
        
        self.oil_painting_btn = QPushButton("油画")
        self.oil_painting_btn.clicked.connect(lambda: self.apply_artistic_filter("oil_painting"))
        filter_layout.addWidget(self.oil_painting_btn)
        
        self.pencil_sketch_btn = QPushButton("铅笔素描")
        self.pencil_sketch_btn.clicked.connect(lambda: self.apply_artistic_filter("pencil_sketch"))
        filter_layout.addWidget(self.pencil_sketch_btn)
        
        self.cartoon_btn = QPushButton("卡通效果")
        self.cartoon_btn.clicked.connect(self.apply_cartoon_effect)
        filter_layout.addWidget(self.cartoon_btn)
        
        filter_group.setLayout(filter_layout)
        layout.addWidget(filter_group)
        
        # 高级效果组
        effect_group = QGroupBox("高级效果")
        effect_layout = QVBoxLayout()
        
        self.semantic_seg_btn = QPushButton("语义分割")
        self.semantic_seg_btn.clicked.connect(self.apply_semantic_segmentation)
        effect_layout.addWidget(self.semantic_seg_btn)
        
        self.collage_btn = QPushButton("创建拼贴画")
        self.collage_btn.clicked.connect(self.create_collage)
        effect_layout.addWidget(self.collage_btn)
        
        self.three_d_btn = QPushButton("3D效果")
        self.three_d_btn.clicked.connect(self.apply_3d_effect)
        effect_layout.addWidget(self.three_d_btn)
        
        effect_group.setLayout(effect_layout)
        layout.addWidget(effect_group)
        
        layout.addStretch()
        advanced_tab.setLayout(layout)
        self.tool_tabs.addTab(advanced_tab, "高级工具")
        
    def create_batch_tools_tab(self):
        """创建批量处理选项卡"""
        batch_tab = QWidget()
        layout = QVBoxLayout()
        
        # 批量处理组
        batch_group = QGroupBox("批量处理")
        batch_layout = QVBoxLayout()
        
        self.batch_select_btn = QPushButton("选择文件夹")
        self.batch_select_btn.clicked.connect(self.select_batch_folder)
        batch_layout.addWidget(self.batch_select_btn)
        
        self.batch_process_btn = QPushButton("开始批量处理")
        self.batch_process_btn.clicked.connect(self.start_batch_processing)
        batch_layout.addWidget(self.batch_process_btn)
        
        # 进度条
        self.batch_progress = QProgressBar()
        batch_layout.addWidget(self.batch_progress)
        
        # 处理选项
        options_layout = QHBoxLayout()
        options_layout.addWidget(QLabel("处理方式:"))
        
        self.batch_method_combo = QComboBox()
        self.batch_method_combo.addItems(["传统年画风格", "水墨画效果", "增强图像质量", "卡通效果"])
        options_layout.addWidget(self.batch_method_combo)
        
        batch_layout.addLayout(options_layout)
        
        batch_group.setLayout(batch_layout)
        layout.addWidget(batch_group)
        
        layout.addStretch()
        batch_tab.setLayout(layout)
        self.tool_tabs.addTab(batch_tab, "批量处理")
        
    def open_image(self):
        """打开图像文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "打开图像", "", 
            "图像文件 (*.png *.jpg *.jpeg *.bmp *.tiff *.gif)"
        )
        
        if file_path:
            try:
                # 使用OpenCV读取图像
                self.original_image = cv2.imread(file_path)
                if self.original_image is not None:
                    self.current_image = self.original_image.copy()
                    self.processed_image = self.current_image.copy()
                    self.image_viewer.set_image(self.current_image)
                    self.add_to_history("打开图像", file_path)
                    self.statusBar().showMessage(f"已加载: {os.path.basename(file_path)}")
                    
                    # 重置图层
                    self.layers = [{"name": "背景", "image": self.current_image, "visible": True}]
                    self.update_layer_list()
                else:
                    QMessageBox.warning(self, "错误", "无法加载图像文件")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"加载图像时出错: {str(e)}")
    
    def save_image(self):
        """保存处理后的图像"""
        if self.processed_image is None:
            QMessageBox.warning(self, "警告", "没有图像可保存")
            return
            
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存图像", "", 
            "PNG图像 (*.png);;JPEG图像 (*.jpg *.jpeg);;所有文件 (*)"
        )
        
        if file_path:
            try:
                if isinstance(self.processed_image, np.ndarray):
                    cv2.imwrite(file_path, self.processed_image)
                else:
                    self.processed_image.save(file_path)
                self.add_to_history("保存图像", file_path)
                self.statusBar().showMessage(f"已保存: {os.path.basename(file_path)}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"保存图像时出错: {str(e)}")
    
    def reset_image(self):
        """重置图像到原始状态"""
        if self.original_image is not None:
            self.current_image = self.original_image.copy()
            self.processed_image = self.current_image.copy()
            self.image_viewer.set_image(self.current_image)
            self.add_to_history("重置图像", "")
            self.statusBar().showMessage("图像已重置")
    
    def apply_effect(self, effect_name):
        """应用图像效果"""
        if self.current_image is None:
            QMessageBox.warning(self, "警告", "请先打开一张图像")
            return
            
        try:
            # 获取当前强度参数
            intensity = 0.7  # 可以从UI控件获取
            
            if effect_name == "traditional":
                result = AdvancedNianHuaTools.apply_traditional_style(self.current_image, intensity)
            elif effect_name == "woodblock":
                result = AdvancedNianHuaTools.add_woodblock_effect(self.current_image, intensity)
            elif effect_name == "ink_wash":
                result = AdvancedNianHuaTools.apply_ink_wash_effect(self.current_image, intensity)
            elif effect_name == "gold_foil":
                result = AdvancedNianHuaTools.add_gold_foil_effect(self.current_image)
            elif effect_name == "red_seal":
                result = AdvancedNianHuaTools.add_red_seal(self.current_image)
            else:
                result = self.current_image
                
            self.processed_image = result
            self.current_image = result
            self.image_viewer.set_image(result)
            self.add_to_history(f"应用{effect_name}效果", "")
            self.statusBar().showMessage(f"{effect_name}效果应用完成")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"应用效果时出错: {str(e)}")
    
    def apply_ai_effect(self, style_type):
        """应用AI效果"""
        if self.current_image is None:
            QMessageBox.warning(self, "警告", "请先打开一张图像")
            return
            
        try:
            result = self.ai_model.apply_ai_style(self.current_image, style_type)
            self.processed_image = result
            self.current_image = result
            self.image_viewer.set_image(result)
            self.add_to_history(f"应用AI{style_type}风格", "")
            self.statusBar().showMessage(f"AI{style_type}风格应用完成")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"应用AI效果时出错: {str(e)}")
    
    def detect_faces(self):
        """检测人脸"""
        if self.current_image is None:
            QMessageBox.warning(self, "警告", "请先打开一张图像")
            return
            
        try:
            faces = self.ai_model.detect_faces(self.current_image)
            
            # 在图像上标记人脸
            if isinstance(self.current_image, np.ndarray):
                result = self.current_image.copy()
            else:
                result = np.array(self.current_image)
                if len(result.shape) == 3:
                    result = cv2.cvtColor(result, cv2.COLOR_RGB2BGR)
                    
            for (x, y, w, h) in faces:
                cv2.rectangle(result, (x, y), (x+w, y+h), (0, 255, 0), 2)
                
            self.processed_image = result
            self.image_viewer.set_image(result)
            self.add_to_history("检测人脸", f"检测到{len(faces)}个人脸")
            self.statusBar().showMessage(f"检测到{len(faces)}个人脸")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"人脸检测时出错: {str(e)}")
    
    def beautify_faces(self):
        """美颜"""
        if self.current_image is None:
            QMessageBox.warning(self, "警告", "请先打开一张图像")
            return
            
        try:
            faces = self.ai_model.detect_faces(self.current_image)
            
            if isinstance(self.current_image, np.ndarray):
                result = self.current_image.copy()
            else:
                result = np.array(self.current_image)
                if len(result.shape) == 3:
                    result = cv2.cvtColor(result, cv2.COLOR_RGB2BGR)
                    
            for face in faces:
                result = self.ai_model.beautify_face(result, face)
                
            self.processed_image = result
            self.current_image = result
            self.image_viewer.set_image(result)
            self.add_to_history("人脸美颜", "")
            self.statusBar().showMessage("人脸美颜完成")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"美颜时出错: {str(e)}")
    
    def apply_artistic_filter(self, filter_type):
        """应用艺术滤镜"""
        if self.current_image is None:
            QMessageBox.warning(self, "警告", "请先打开一张图像")
            return
            
        try:
            result = AdvancedNianHuaTools.apply_artistic_filter(self.current_image, filter_type)
            self.processed_image = result
            self.current_image = result
            self.image_viewer.set_image(result)
            self.add_to_history(f"应用{filter_type}滤镜", "")
            self.statusBar().showMessage(f"{filter_type}滤镜应用完成")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"应用滤镜时出错: {str(e)}")
    
    def apply_cartoon_effect(self):
        """应用卡通效果"""
        if self.current_image is None:
            QMessageBox.warning(self, "警告", "请先打开一张图像")
            return
            
        try:
            result = AdvancedNianHuaTools.apply_cartoon_effect(self.current_image)
            self.processed_image = result
            self.current_image = result
            self.image_viewer.set_image(result)
            self.add_to_history("应用卡通效果", "")
            self.statusBar().showMessage("卡通效果应用完成")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"应用卡通效果时出错: {str(e)}")
    
    def enhance_image_quality(self):
        """增强图像质量"""
        if self.current_image is None:
            QMessageBox.warning(self, "警告", "请先打开一张图像")
            return
            
        try:
            result = AdvancedNianHuaTools.enhance_image_quality(self.current_image)
            self.processed_image = result
            self.current_image = result
            self.image_viewer.set_image(result)
            self.add_to_history("增强图像质量", "")
            self.statusBar().showMessage("图像质量增强完成")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"增强图像质量时出错: {str(e)}")
    
    def add_text_to_image(self):
        """在图像上添加文字"""
        if self.current_image is None:
            QMessageBox.warning(self, "警告", "请先打开一张图像")
            return
            
        try:
            text, ok = QInputDialog.getText(self, "添加文字", "请输入要添加的文字:")
            if ok and text:
                result = AdvancedNianHuaTools.add_text_to_image(self.current_image, text)
                self.processed_image = result
                self.current_image = result
                self.image_viewer.set_image(result)
                self.add_to_history("添加文字", text)
                self.statusBar().showMessage("文字添加完成")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"添加文字时出错: {str(e)}")
    
    def apply_semantic_segmentation(self):
        """应用语义分割"""
        if self.current_image is None:
            QMessageBox.warning(self, "警告", "请先打开一张图像")
            return
            
        try:
            result = AdvancedNianHuaTools.semantic_segmentation(self.current_image)
            self.processed_image = result
            self.image_viewer.set_image(result)
            self.add_to_history("语义分割", "")
            self.statusBar().showMessage("语义分割完成")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"语义分割时出错: {str(e)}")
    
    def create_collage(self):
        """创建拼贴画"""
        # 简化实现 - 使用当前图像创建简单拼贴
        if self.current_image is None:
            QMessageBox.warning(self, "警告", "请先打开一张图像")
            return
            
        try:
            # 使用当前图像创建多个副本
            images = [self.current_image] * 4
            result = AdvancedNianHuaTools.create_collage(images, "grid")
            self.processed_image = result
            self.current_image = result
            self.image_viewer.set_image(result)
            self.add_to_history("创建拼贴画", "")
            self.statusBar().showMessage("拼贴画创建完成")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"创建拼贴画时出错: {str(e)}")
    
    def apply_3d_effect(self):
        """应用3D效果"""
        if self.current_image is None:
            QMessageBox.warning(self, "警告", "请先打开一张图像")
            return
            
        try:
            result = AdvancedNianHuaTools.apply_3d_effect(self.current_image)
            self.processed_image = result
            self.current_image = result
            self.image_viewer.set_image(result)
            self.add_to_history("应用3D效果", "")
            self.statusBar().showMessage("3D效果应用完成")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"应用3D效果时出错: {str(e)}")
    
    def select_batch_folder(self):
        """选择批量处理文件夹"""
        folder_path = QFileDialog.getExistingDirectory(self, "选择包含图像的文件夹")
        if folder_path:
            self.batch_folder = folder_path
            self.statusBar().showMessage(f"已选择文件夹: {folder_path}")
    
    def start_batch_processing(self):
        """开始批量处理"""
        if not hasattr(self, 'batch_folder') or not self.batch_folder:
            QMessageBox.warning(self, "警告", "请先选择包含图像的文件夹")
            return
            
        # 获取文件夹中的所有图像文件
        image_extensions = ('.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.gif')
        file_paths = []
        for filename in os.listdir(self.batch_folder):
            if filename.lower().endswith(image_extensions):
                file_paths.append(os.path.join(self.batch_folder, filename))
        
        if not file_paths:
            QMessageBox.warning(self, "警告", "选择的文件夹中没有图像文件")
            return
            
        # 根据选择的处理方式创建处理函数
        method = self.batch_method_combo.currentText()
        if method == "传统年画风格":
            process_func = lambda img: np.array(AdvancedNianHuaTools.apply_traditional_style(img))
        elif method == "水墨画效果":
            process_func = lambda img: np.array(AdvancedNianHuaTools.apply_ink_wash_effect(img))
        elif method == "增强图像质量":
            process_func = lambda img: np.array(AdvancedNianHuaTools.enhance_image_quality(img))
        elif method == "卡通效果":
            process_func = lambda img: np.array(AdvancedNianHuaTools.apply_cartoon_effect(img))
        else:
            process_func = lambda img: img
            
        # 创建并启动批量处理线程
        self.batch_thread = BatchProcessingThread(file_paths, process_func)
        self.batch_thread.progress_updated.connect(self.update_batch_progress)
        self.batch_thread.finished_batch.connect(self.batch_processing_finished)
        self.batch_thread.start()
        
        self.statusBar().showMessage("批量处理开始...")
    
    def update_batch_progress(self, progress):
        """更新批量处理进度"""
        self.batch_progress.setValue(progress)
    
    def batch_processing_finished(self):
        """批量处理完成"""
        self.batch_progress.setValue(0)
        self.statusBar().showMessage("批量处理完成")
        QMessageBox.information(self, "完成", "批量处理已完成！")
    
    def add_to_history(self, operation, details):
        """添加到历史记录"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # 创建缩略图
        if self.processed_image is not None:
            if isinstance(self.processed_image, np.ndarray):
                # 转换为PIL图像
                pil_img = Image.fromarray(cv2.cvtColor(self.processed_image, cv2.COLOR_BGR2RGB))
            else:
                pil_img = self.processed_image
                
            # 创建缩略图
            thumbnail = pil_img.resize((60, 60), Image.Resampling.LANCZOS)
            
            # 转换为QImage
            if thumbnail.mode == "RGB":
                data = thumbnail.tobytes("raw", "RGB")
                q_img = QImage(data, thumbnail.width, thumbnail.height, QImage.Format_RGB888)
            else:
                thumbnail = thumbnail.convert("RGB")
                data = thumbnail.tobytes("raw", "RGB")
                q_img = QImage(data, thumbnail.width, thumbnail.height, QImage.Format_RGB888)
                
            # 创建历史记录项
            item = QListWidgetItem()
            widget = HistoryItemWidget(q_img, timestamp, operation)
            item.setSizeHint(widget.sizeHint())
            
            self.history_list.addItem(item)
            self.history_list.setItemWidget(item, widget)
            
            # 保存历史记录信息
            self.history.append({
                "timestamp": timestamp,
                "operation": operation,
                "details": details,
                "image": self.processed_image.copy() if hasattr(self.processed_image, 'copy') else self.processed_image
            })
    
    def on_history_selected(self, item):
        """历史记录项被选中"""
        index = self.history_list.row(item)
        if 0 <= index < len(self.history):
            history_item = self.history[index]
            self.processed_image = history_item["image"]
            self.current_image = history_item["image"]
            self.image_viewer.set_image(self.current_image)
            self.statusBar().showMessage(f"已恢复到: {history_item['operation']}")
    
    def add_layer(self):
        """添加图层"""
        layer_name, ok = QInputDialog.getText(self, "添加图层", "图层名称:")
        if ok and layer_name:
            new_layer = {
                "name": layer_name,
                "image": None,
                "visible": True
            }
            self.layers.append(new_layer)
            self.update_layer_list()
    
    def remove_layer(self):
        """删除图层"""
        if self.layers and self.current_layer < len(self.layers):
            del self.layers[self.current_layer]
            self.update_layer_list()
    
    def update_layer_list(self):
        """更新图层列表"""
        self.layer_list.clear()
        for i, layer in enumerate(self.layers):
            item = QListWidgetItem()
            widget = LayerItemWidget(layer["name"], layer["visible"])
            item.setSizeHint(widget.sizeHint())
            self.layer_list.addItem(item)
            self.layer_list.setItemWidget(item, widget)
    
    def on_layer_selected(self, item):
        """图层被选中"""
        self.current_layer = self.layer_list.row(item)
    
    def undo(self):
        """撤销操作"""
        if len(self.history) > 1:
            # 移除当前状态
            self.history.pop()
            # 恢复到上一个状态
            prev_item = self.history[-1]
            self.processed_image = prev_item["image"]
            self.current_image = prev_item["image"]
            self.image_viewer.set_image(self.current_image)
            self.statusBar().showMessage(f"已撤销: {prev_item['operation']}")
    
    def redo(self):
        """重做操作"""
        # 简化实现 - 在实际应用中需要维护重做栈
        self.statusBar().showMessage("重做功能暂未实现")
    
    def batch_process(self):
        """批量处理"""
        # 切换到批量处理选项卡
        self.tool_tabs.setCurrentIndex(3)
    
    def new_file(self):
        """新建文件"""
        # 创建一个空白画布
        width, ok1 = QInputDialog.getInt(self, "新建文件", "宽度:", 800, 100, 5000, 100)
        if ok1:
            height, ok2 = QInputDialog.getInt(self, "新建文件", "高度:", 600, 100, 5000, 100)
            if ok2:
                # 创建白色画布
                blank_image = np.ones((height, width, 3), dtype=np.uint8) * 255
                self.original_image = blank_image
                self.current_image = blank_image.copy()
                self.processed_image = self.current_image.copy()
                self.image_viewer.set_image(self.current_image)
                self.add_to_history("新建文件", f"{width}x{height}")
                self.statusBar().showMessage(f"已创建新画布: {width}x{height}")
    
    def load_settings(self):
        """加载设置"""
        geometry = self.settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
    
    def closeEvent(self, event):
        """关闭事件"""
        self.settings.setValue("geometry", self.saveGeometry())
        event.accept()

def main():
    app = QApplication(sys.argv)
    
    # 设置应用程序样式
    app.setStyle('Fusion')
    
    # 设置应用程序字体
    font = QFont("Microsoft YaHei", 10)
    app.setFont(font)
    
    # 创建并显示主窗口
    window = EnhancedNianHuaSystem()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()