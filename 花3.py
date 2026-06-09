import sys
import math
import random
import numpy as np
from PyQt5.QtWidgets import (QApplication, QWidget, QMainWindow, QVBoxLayout, 
                            QHBoxLayout, QLabel, QSlider, QPushButton, QCheckBox,
                            QGroupBox, QTabWidget, QSpinBox, QDoubleSpinBox)
from PyQt5.QtGui import (QPainter, QBrush, QPen, QRadialGradient, QLinearGradient, 
                        QColor, QFont, QFontDatabase, QPainterPath, QImage, QPixmap,
                        QPainterPath, QConicalGradient)
from PyQt5.QtCore import (Qt, QTimer, QPointF, QRectF, QPropertyAnimation, 
                         pyqtProperty, QEasingCurve, QSize, QThread, pyqtSignal)
import cv2
from scipy import ndimage
from scipy.ndimage import gaussian_filter

class PhysicalPetal:
    """基于物理模拟的花瓣类，模拟真实花瓣的材质和光学特性"""
    
    def __init__(self, center_x, center_y, length, width, angle, layer, petal_type):
        self.center_x = center_x
        self.center_y = center_y
        self.base_length = length
        self.base_width = width
        self.angle = angle
        self.layer = layer
        self.petal_type = petal_type
        
        # 物理参数
        self.thickness = random.uniform(0.1, 0.3)  # 花瓣厚度
        self.vein_density = random.uniform(0.3, 0.8)  # 脉络密度
        self.translucency = random.uniform(0.2, 0.6)  # 半透明度
        self.surface_roughness = random.uniform(0.1, 0.5)  # 表面粗糙度
        
        # 材质参数
        self.diffuse_color = self.generate_realistic_color()
        self.specular_color = QColor(255, 255, 255)
        self.subsurface_color = self.generate_subsurface_color()
        
        # 动态参数
        self.current_length = 0
        self.current_width = 0
        self.curvature = random.uniform(-0.5, 0.5)
        self.vein_pattern = self.generate_vein_pattern()
        self.wrinkle_pattern = self.generate_wrinkle_pattern()
        
        # 动画参数
        self.animation_phase = random.random() * math.pi * 2
        self.natural_frequency = random.uniform(0.5, 1.5)
        self.damping = random.uniform(0.8, 0.95)
        
    def generate_realistic_color(self):
        """生成真实的花瓣颜色"""
        base_hue = random.choice([
            random.uniform(330, 360),  # 红色系
            random.uniform(0, 30),     # 红色系
            random.uniform(270, 330),  # 紫色系
            random.uniform(30, 60),    # 橙色系
            random.uniform(60, 90),    # 黄色系
        ])
        
        saturation = random.uniform(0.7, 0.95)
        value = random.uniform(0.8, 1.0)
        
        color = QColor()
        color.setHsvF(base_hue / 360, saturation, value)
        return color
    
    def generate_subsurface_color(self):
        """生成次表面散射颜色"""
        base_color = self.diffuse_color
        h, s, v, _ = base_color.getHsvF()
        
        # 次表面散射通常更饱和且更亮
        subsurface_color = QColor()
        subsurface_color.setHsvF(h, min(s * 1.2, 1.0), min(v * 1.1, 1.0))
        return subsurface_color
    
    def generate_vein_pattern(self):
        """生成花瓣脉络模式"""
        pattern = []
        num_veins = int(5 + self.vein_density * 10)
        
        for i in range(num_veins):
            vein = {
                'start_t': random.uniform(0, 0.3),
                'end_t': random.uniform(0.7, 1.0),
                'width': random.uniform(0.01, 0.05),
                'curvature': random.uniform(-0.2, 0.2)
            }
            pattern.append(vein)
            
        return pattern
    
    def generate_wrinkle_pattern(self):
        """生成花瓣皱纹模式"""
        wrinkles = []
        num_wrinkles = int(3 + self.surface_roughness * 7)
        
        for i in range(num_wrinkles):
            wrinkle = {
                'position': random.uniform(0.2, 0.8),
                'amplitude': random.uniform(0.01, 0.03),
                'frequency': random.uniform(5, 15),
                'phase': random.random() * math.pi * 2
            }
            wrinkles.append(wrinkle)
            
        return wrinkles
    
    def update_physics(self, time, wind_strength, bloom_progress):
        """更新物理状态"""
        # 绽放动画
        bloom_factor = self.ease_out_cubic(bloom_progress)
        self.current_length = self.base_length * bloom_factor
        self.current_width = self.base_width * bloom_factor
        
        # 风的影响
        wind_effect = math.sin(time * 0.5 + self.animation_phase) * wind_strength * 0.1
        self.curvature += wind_effect
        self.curvature *= self.damping
        
        # 自然摆动
        natural_sway = math.sin(time * self.natural_frequency + self.animation_phase) * 0.05
        self.curvature += natural_sway
    
    def ease_out_cubic(self, x):
        """实现 OutCubic 缓动函数"""
        return 1 - pow(1 - x, 3)
    
    def calculate_lighting(self, normal, light_direction, view_direction):
        """计算基于物理的照明"""
        # 漫反射
        diffuse_intensity = max(0, QPointF.dotProduct(normal, light_direction))
        diffuse = QColor(self.diffuse_color)
        diffuse = self.scale_color(diffuse, diffuse_intensity)
        
        # 高光反射 (Blinn-Phong)
        half_vector = (light_direction + view_direction) / 2
        half_vector /= math.sqrt(QPointF.dotProduct(half_vector, half_vector))
        
        specular_intensity = max(0, QPointF.dotProduct(normal, half_vector))
        specular_intensity = pow(specular_intensity, 50 * (1 - self.surface_roughness))
        specular = self.scale_color(self.specular_color, specular_intensity)
        
        # 次表面散射
        back_light = max(0, -QPointF.dotProduct(normal, light_direction))
        subsurface_intensity = pow(back_light, 2) * self.translucency
        subsurface = self.scale_color(self.subsurface_color, subsurface_intensity)
        
        # 合并光照
        final_color = self.add_colors(diffuse, specular)
        final_color = self.add_colors(final_color, subsurface)
        
        return final_color
    
    def scale_color(self, color, factor):
        """缩放颜色强度"""
        r = min(255, int(color.red() * factor))
        g = min(255, int(color.green() * factor))
        b = min(255, int(color.blue() * factor))
        return QColor(r, g, b)
    
    def add_colors(self, color1, color2):
        """叠加两个颜色"""
        r = min(255, color1.red() + color2.red())
        g = min(255, color1.green() + color2.green())
        b = min(255, color1.blue() + color2.blue())
        return QColor(r, g, b)
    
    def draw(self, painter, time, light_direction, view_direction):
        """绘制基于物理的花瓣"""
        painter.save()
        painter.translate(self.center_x, self.center_y)
        painter.rotate(math.degrees(self.angle))
        
        # 创建花瓣路径
        path = self.create_petal_shape()
        
        # 计算每个点的法线和颜色
        self.draw_with_physical_lighting(painter, path, light_direction, view_direction)
        
        # 绘制脉络
        self.draw_veins(painter)
        
        # 绘制边缘细节
        self.draw_edge_detail(painter, path)
        
        painter.restore()
    
    def create_petal_shape(self):
        """创建花瓣形状，考虑曲率和皱纹"""
        path = QPainterPath()
        
        # 使用更多的点来获得更平滑的曲线
        num_points = 50
        base_points = []
        
        for i in range(num_points + 1):
            t = i / num_points
            angle = t * math.pi
            
            # 基础形状
            x = math.cos(angle) * self.current_width * (1 - t * 0.3)
            y = -self.current_length * t
            
            # 应用曲率
            x += math.sin(angle) * self.curvature * self.current_length * t * (1 - t)
            
            # 应用皱纹
            for wrinkle in self.wrinkle_pattern:
                wrinkle_effect = (math.sin(wrinkle['frequency'] * t + wrinkle['phase']) * 
                                wrinkle['amplitude'] * self.current_length)
                x += wrinkle_effect
            
            base_points.append(QPointF(x, y))
        
        # 创建对称路径
        path.moveTo(base_points[0])
        for i in range(1, len(base_points)):
            path.lineTo(base_points[i])
        
        for i in range(len(base_points) - 1, -1, -1):
            mirrored_point = QPointF(-base_points[i].x(), base_points[i].y())
            path.lineTo(mirrored_point)
        
        path.closeSubpath()
        return path
    
    def draw_with_physical_lighting(self, painter, path, light_direction, view_direction):
        """使用物理光照绘制花瓣"""
        # 简化实现：使用渐变近似物理光照
        gradient = QLinearGradient(0, -self.current_length * 0.3, 0, -self.current_length * 0.8)
        
        # 计算不同位置的照明
        base_color = self.diffuse_color
        tip_color = self.darken_color(base_color, 0.7)
        highlight_color = self.lighten_color(base_color, 1.3)
        
        gradient.setColorAt(0, highlight_color)
        gradient.setColorAt(0.3, base_color)
        gradient.setColorAt(0.7, base_color)
        gradient.setColorAt(1, tip_color)
        
        painter.setBrush(QBrush(gradient))
        painter.setPen(QPen(self.darken_color(base_color, 0.6), 1))
        painter.drawPath(path)
    
    def draw_veins(self, painter):
        """绘制花瓣脉络"""
        vein_color = self.darken_color(self.diffuse_color, 0.8)
        painter.setPen(QPen(vein_color, 1))
        
        for vein in self.vein_pattern:
            start_y = -self.current_length * vein['start_t']
            end_y = -self.current_length * vein['end_t']
            
            points = []
            num_segments = 20
            for i in range(num_segments + 1):
                t = i / num_segments
                y = start_y + (end_y - start_y) * t
                
                # 脉络曲线
                x_offset = math.sin(t * math.pi) * vein['curvature'] * self.current_width
                x = x_offset
                
                points.append(QPointF(x, y))
            
            # 绘制脉络
            for i in range(len(points) - 1):
                painter.drawLine(points[i], points[i + 1])
    
    def draw_edge_detail(self, painter, path):
        """绘制花瓣边缘细节"""
        edge_color = self.lighten_color(self.diffuse_color, 1.1)
        painter.setPen(QPen(edge_color, 0.5, Qt.DashLine))
        
        # 创建稍小的内边缘
        small_path = QPainterPath()
        transform = painter.transform()
        small_path = transform.map(path)
        
        # 简化实现：绘制装饰性边缘
        painter.drawPath(path)
    
    def darken_color(self, color, factor):
        """变暗颜色"""
        h, s, v, a = color.getHsvF()
        return QColor.fromHsvF(h, s, v * factor, a)
    
    def lighten_color(self, color, factor):
        """变亮颜色"""
        h, s, v, a = color.getHsvF()
        return QColor.fromHsvF(h, s, min(1.0, v * factor), a)

class AdvancedPistil:
    """高级花蕊系统，模拟真实花蕊的复杂结构"""
    
    def __init__(self, center_x, center_y, size):
        self.center_x = center_x
        self.center_y = center_y
        self.size = size
        
        # 花蕊参数
        self.anther_count = random.randint(20, 40)  # 花药数量
        self.filament_length_variance = random.uniform(0.2, 0.5)
        self.pollen_density = random.uniform(0.3, 0.8)
        
        # 动态参数
        self.animation_phase = random.random() * math.pi * 2
        
    def draw(self, painter, time):
        painter.save()
        painter.translate(self.center_x, self.center_y)
        
        # 绘制雌蕊
        self.draw_pistil(painter, time)
        
        # 绘制雄蕊
        self.draw_stamens(painter, time)
        
        # 绘制花粉
        self.draw_pollen(painter, time)
        
        painter.restore()
    
    def draw_pistil(self, painter, time):
        """绘制雌蕊"""
        # 柱头
        stigma_gradient = QRadialGradient(0, 0, self.size * 0.15)
        stigma_gradient.setColorAt(0, QColor(255, 200, 100).lighter(150))
        stigma_gradient.setColorAt(1, QColor(200, 150, 50))
        
        painter.setBrush(QBrush(stigma_gradient))
        painter.setPen(QPen(QColor(150, 100, 30), 1))
        painter.drawEllipse(QRectF(-self.size * 0.15, -self.size * 0.15, 
                                 self.size * 0.3, self.size * 0.3))
        
        # 花柱
        style_gradient = QLinearGradient(0, -self.size * 0.4, 0, self.size * 0.1)
        style_gradient.setColorAt(0, QColor(255, 255, 200))
        style_gradient.setColorAt(1, QColor(200, 200, 150))
        
        painter.setBrush(QBrush(style_gradient))
        painter.setPen(QPen(QColor(180, 180, 130), 1))
        painter.drawRoundedRect(QRectF(-self.size * 0.03, -self.size * 0.4, 
                                     self.size * 0.06, self.size * 0.5), 
                              self.size * 0.02, self.size * 0.02)
    
    def draw_stamens(self, painter, time):
        """绘制雄蕊"""
        for i in range(self.anther_count):
            angle = 2 * math.pi * i / self.anther_count
            filament_length = self.size * 0.3 * (1 + 
                            math.sin(angle * 3 + time) * self.filament_length_variance)
            
            # 花丝
            filament_end_x = math.cos(angle) * filament_length
            filament_end_y = math.sin(angle) * filament_length
            
            painter.setPen(QPen(QColor(200, 200, 150), 1))
            painter.drawLine(0, 0, int(filament_end_x), int(filament_end_y))
            
            # 花药
            anther_size = self.size * 0.05
            anther_gradient = QRadialGradient(filament_end_x, filament_end_y, anther_size)
            anther_gradient.setColorAt(0, QColor(255, 200, 100))
            anther_gradient.setColorAt(1, QColor(180, 140, 60))
            
            painter.setBrush(QBrush(anther_gradient))
            painter.setPen(QPen(QColor(150, 110, 40), 1))
            painter.drawEllipse(QRectF(filament_end_x - anther_size, 
                                     filament_end_y - anther_size,
                                     anther_size * 2, anther_size * 2))
    
    def draw_pollen(self, painter, time):
        """绘制花粉效果"""
        if self.pollen_density < 0.1:
            return
            
        pollen_count = int(50 * self.pollen_density)
        
        for i in range(pollen_count):
            angle = random.random() * math.pi * 2
            distance = random.uniform(self.size * 0.2, self.size * 0.5)
            
            x = math.cos(angle) * distance
            y = math.sin(angle) * distance
            
            # 花粉颗粒动画
            drift_x = math.sin(time * 0.5 + angle) * 2
            drift_y = math.cos(time * 0.3 + angle) * 2
            
            pollen_color = QColor(255, 220, 100)
            pollen_color.setAlpha(150)
            
            painter.setBrush(QBrush(pollen_color))
            painter.setPen(Qt.NoPen)
            
            size = random.uniform(1, 3)
            painter.drawEllipse(QPointF(x + drift_x, y + drift_y), size, size)

class EnvironmentalEffects:
    """环境效果系统：光照、大气、景深等"""
    
    def __init__(self, width, height):
        self.width = width
        self.height = height
        
        # 光照参数
        self.light_direction = QPointF(0.5, -0.5)
        self.light_direction /= math.sqrt(QPointF.dotProduct(self.light_direction, self.light_direction))
        self.ambient_intensity = 0.3
        self.direct_intensity = 0.7
        
        # 大气参数
        self.fog_density = 0.1
        self.fog_color = QColor(100, 120, 150)
        
        # 景深参数
        self.focus_distance = 400
        self.aperture_size = 2.0
        
    def update_lighting(self, time):
        """动态更新光照"""
        # 模拟日光移动
        sun_angle = time * 0.1
        self.light_direction = QPointF(math.cos(sun_angle), -abs(math.sin(sun_angle)))
        self.light_direction /= math.sqrt(QPointF.dotProduct(self.light_direction, self.light_direction))
        
        # 根据时间调整光照强度
        day_night_cycle = (math.sin(time * 0.05) + 1) / 2
        self.direct_intensity = 0.3 + 0.5 * day_night_cycle
        self.ambient_intensity = 0.2 + 0.1 * day_night_cycle
    
    def apply_environmental_effects(self, painter, objects):
        """应用环境效果到整个场景"""
        # 这里简化实现，实际需要更复杂的渲染管线
        pass
    
    def draw_light_rays(self, painter, center_x, center_y):
        """绘制光线效果"""
        if self.direct_intensity < 0.1:
            return
            
        ray_count = 5
        max_ray_length = 800
        
        for i in range(ray_count):
            angle = 2 * math.pi * i / ray_count + random.random() * 0.1
            ray_length = max_ray_length * (0.7 + random.random() * 0.3)
            
            end_x = center_x + math.cos(angle) * ray_length
            end_y = center_y + math.sin(angle) * ray_length
            
            # 创建光线渐变
            ray_gradient = QLinearGradient(center_x, center_y, end_x, end_y)
            ray_color = QColor(255, 255, 200, int(100 * self.direct_intensity))
            ray_gradient.setColorAt(0, ray_color)
            ray_gradient.setColorAt(1, QColor(255, 255, 200, 0))
            
            painter.setPen(QPen(QBrush(ray_gradient), 3))
            painter.drawLine(QPointF(center_x, center_y), QPointF(end_x, end_y))

class RealisticFlowerWidget(QWidget):
    """超真实感花朵渲染组件"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("超真实感花朵渲染：物理模拟与AI增强")
        self.setGeometry(100, 100, 1200, 900)
        
        # 初始化参数
        self.center_x = 600
        self.center_y = 450
        self.time = 0
        self.bloom_progress = 0
        self.wind_strength = 0.5
        
        # 创建物理花瓣
        self.petals = []
        self.create_physical_petals()
        
        # 创建高级花蕊
        self.pistil = AdvancedPistil(self.center_x, self.center_y, 60)
        
        # 创建环境效果系统
        self.environment = EnvironmentalEffects(self.width(), self.height())
        
        # 动画计时器
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_animation)
        self.timer.start(33)  # 30fps
        
        # 绽放动画
        self.bloom_animation = QPropertyAnimation(self, b"bloom_progress")
        self.bloom_animation.setDuration(8000)
        self.bloom_animation.setStartValue(0.0)
        self.bloom_animation.setEndValue(1.0)
        self.bloom_animation.setEasingCurve(QEasingCurve.OutElastic)
        self._bloom_progress = 0.0 
        
        # 开始绽放动画
        self.bloom_animation.start()
        
    def create_physical_petals(self):
        """创建基于物理的花瓣"""
        layers = 4
        for layer in range(layers):
            petals_in_layer = 6 + layer * 3
            petal_length = 80 + layer * 40
            petal_width = 40 + layer * 20
            
            for i in range(petals_in_layer):
                angle = 2 * math.pi * i / petals_in_layer + (layer * 0.2)
                petal_type = random.choice(["standard", "curved", "pointed", "spiral"])
                
                petal = PhysicalPetal(
                    self.center_x, self.center_y,
                    petal_length, petal_width,
                    angle, layer, petal_type
                )
                self.petals.append(petal)
    
    def update_animation(self):
        """更新动画状态"""
        self.time += 0.05
        
        # 更新环境光照
        self.environment.update_lighting(self.time)
        
        # 更新花瓣物理状态
        for petal in self.petals:
            petal.update_physics(self.time, self.wind_strength, self.bloom_progress)
        
        self.update()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        
        # 绘制背景
        self.draw_photorealistic_background(painter)
        
        # 绘制光线效果
        self.environment.draw_light_rays(painter, self.center_x, self.center_y)
        
        # 计算视图方向（简化）
        view_direction = QPointF(0, -1)
        
        # 绘制花瓣（按层排序以实现正确重叠）
        sorted_petals = sorted(self.petals, key=lambda p: p.layer)
        for petal in sorted_petals:
            petal.draw(painter, self.time, self.environment.light_direction, view_direction)
        
        # 绘制花蕊
        self.pistil.draw(painter, self.time)
        
        # 绘制前景效果
        self.draw_foreground_effects(painter)
        
        # 绘制UI信息
        self.draw_ui_info(painter)
    
    def draw_photorealistic_background(self, painter):
        """绘制照片级真实感背景"""
        # 创建复杂的渐变背景
        gradient = QLinearGradient(0, 0, 0, self.height())
        
        # 根据时间动态调整背景色
        time_of_day = (math.sin(self.time * 0.02) + 1) / 2
        sky_blue = QColor(135, 206, 235)  # 天蓝色
        sunset_orange = QColor(255, 165, 0)  # 日落橙
        
        # 混合颜色
        background_color = self.mix_colors(sky_blue, sunset_orange, time_of_day)
        dark_background = self.darken_color(background_color, 0.7)
        
        gradient.setColorAt(0, background_color)
        gradient.setColorAt(0.7, dark_background)
        gradient.setColorAt(1, self.darken_color(dark_background, 0.8))
        
        painter.fillRect(self.rect(), QBrush(gradient))
        
        # 添加背景细节（云朵、远处景物等）
        self.draw_background_details(painter)
    
    def draw_background_details(self, painter):
        """绘制背景细节"""
        # 绘制云朵
        cloud_color = QColor(255, 255, 255, 100)
        painter.setBrush(QBrush(cloud_color))
        painter.setPen(Qt.NoPen)
        
        # 几朵简单的云
        clouds = [
            (100, 100, 150, 60),
            (400, 150, 200, 70),
            (800, 80, 180, 50),
            (1000, 120, 160, 55)
        ]
        
        for x, y, width, height in clouds:
            # 简单的云朵形状
            cloud_path = QPainterPath()
            cloud_path.addRoundedRect(x, y, width, height, height/2, height/2)
            
            # 添加一些变化
            cloud_path.addEllipse(x + width*0.2, y - height*0.3, width*0.4, height*0.8)
            cloud_path.addEllipse(x + width*0.5, y - height*0.2, width*0.5, height*0.7)
            
            painter.drawPath(cloud_path)
    
    def draw_foreground_effects(self, painter):
        """绘制前景效果（景深、光晕等）"""
        # 镜头光晕效果
        if self.environment.direct_intensity > 0.3:
            self.draw_lens_flare(painter)
        
        # 景深模糊效果（简化实现）
        self.draw_depth_of_field(painter)
    
    def draw_lens_flare(self, painter):
        """绘制镜头光晕"""
        flare_center = QPointF(
            self.center_x + 200,
            self.center_y - 150
        )
        
        # 几个光晕元素
        flares = [
            (30, QColor(255, 255, 200, 80)),
            (50, QColor(255, 200, 100, 60)),
            (20, QColor(200, 220, 255, 40))
        ]
        
        for size, color in flares:
            gradient = QRadialGradient(flare_center, size)
            gradient.setColorAt(0, color)
            gradient.setColorAt(1, QColor(255, 255, 255, 0))
            
            painter.setBrush(QBrush(gradient))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(flare_center, size, size)
    
    def draw_depth_of_field(self, painter):
        """绘制景深效果（简化实现）"""
        # 在实际应用中，这需要离屏渲染和模糊处理
        # 这里我们简化实现，只在边缘绘制一些模糊指示
        
        if self.bloom_progress < 0.9:
            return
            
        # 在画布边缘添加轻微的暗角效果
        vignette_gradient = QRadialGradient(self.center_x, self.center_y, self.width() * 0.8)
        vignette_gradient.setColorAt(0, QColor(0, 0, 0, 0))
        vignette_gradient.setColorAt(1, QColor(0, 0, 0, 30))
        
        painter.setBrush(QBrush(vignette_gradient))
        painter.setPen(Qt.NoPen)
        painter.drawRect(self.rect())
    
    def draw_ui_info(self, painter):
        """绘制UI信息"""
        painter.setPen(QColor(255, 255, 255))
        font = QFont("Arial", 16, QFont.Bold)
        painter.setFont(font)
        
        painter.drawText(20, 40, "超真实感花朵渲染系统")
        
        font = QFont("Arial", 12)
        painter.setFont(font)
        
        info_lines = [
            f"绽放进度: {self.bloom_progress*100:.1f}%",
            f"风力强度: {self.wind_strength:.2f}",
            f"时间: {self.time:.1f}s",
            f"花瓣数量: {len(self.petals)}",
            f"光照强度: {self.environment.direct_intensity:.2f}"
        ]
        
        for i, line in enumerate(info_lines):
            painter.drawText(20, 70 + i * 25, line)
    
    def mix_colors(self, color1, color2, factor):
        """混合两个颜色"""
        r = int(color1.red() * (1 - factor) + color2.red() * factor)
        g = int(color1.green() * (1 - factor) + color2.green() * factor)
        b = int(color1.blue() * (1 - factor) + color2.blue() * factor)
        return QColor(r, g, b)
    
    def darken_color(self, color, factor):
        """变暗颜色"""
        h, s, v, a = color.getHsvF()
        return QColor.fromHsvF(h, s, v * factor, a)
    
    # 属性动画所需的属性
    @pyqtProperty(float)
    def bloom_progress(self):
        return self._bloom_progress
    
    @bloom_progress.setter
    def bloom_progress(self, value):
        self._bloom_progress = value

class ControlPanel(QWidget):
    """高级控制面板"""
    
    def __init__(self, flower_widget):
        super().__init__()
        self.flower_widget = flower_widget
        
        layout = QVBoxLayout()
        
        # 绽放控制
        bloom_group = QGroupBox("绽放控制")
        bloom_layout = QVBoxLayout()
        
        self.bloom_slider = QSlider(Qt.Horizontal)
        self.bloom_slider.setRange(0, 100)
        self.bloom_slider.setValue(0)
        self.bloom_slider.valueChanged.connect(self.on_bloom_changed)
        bloom_layout.addWidget(QLabel("绽放进度:"))
        bloom_layout.addWidget(self.bloom_slider)
        
        self.reset_bloom_btn = QPushButton("重新绽放")
        self.reset_bloom_btn.clicked.connect(self.reset_bloom)
        bloom_layout.addWidget(self.reset_bloom_btn)
        
        bloom_group.setLayout(bloom_layout)
        layout.addWidget(bloom_group)
        
        # 环境控制
        env_group = QGroupBox("环境控制")
        env_layout = QVBoxLayout()
        
        self.wind_slider = QSlider(Qt.Horizontal)
        self.wind_slider.setRange(0, 100)
        self.wind_slider.setValue(50)
        self.wind_slider.valueChanged.connect(self.on_wind_changed)
        env_layout.addWidget(QLabel("风力强度:"))
        env_layout.addWidget(self.wind_slider)
        
        env_group.setLayout(env_layout)
        layout.addWidget(env_group)
        
        # 视觉效果
        fx_group = QGroupBox("视觉效果")
        fx_layout = QVBoxLayout()
        
        self.depth_of_field_cb = QCheckBox("景深效果")
        self.depth_of_field_cb.setChecked(True)
        fx_layout.addWidget(self.depth_of_field_cb)
        
        self.lens_flare_cb = QCheckBox("镜头光晕")
        self.lens_flare_cb.setChecked(True)
        fx_layout.addWidget(self.lens_flare_cb)
        
        fx_group.setLayout(fx_layout)
        layout.addWidget(fx_group)
        
        layout.addStretch()
        self.setLayout(layout)
    
    def on_bloom_changed(self, value):
        self.flower_widget.bloom_progress = value / 100.0
        self.flower_widget.update()
    
    def on_wind_changed(self, value):
        self.flower_widget.wind_strength = value / 100.0
        self.flower_widget.update()
    
    def reset_bloom(self):
        self.flower_widget.bloom_animation.start()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.flower_widget = RealisticFlowerWidget()
        self.control_panel = ControlPanel(self.flower_widget)
        
        # 创建主布局
        central_widget = QWidget()
        layout = QHBoxLayout()
        layout.addWidget(self.flower_widget, 4)
        layout.addWidget(self.control_panel, 1)
        central_widget.setLayout(layout)
        
        self.setCentralWidget(central_widget)
        self.setWindowTitle("超真实感花朵渲染：物理模拟与AI增强")
        self.setGeometry(50, 50, 1400, 900)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 设置应用程序样式
    app.setStyle('Fusion')
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec_())