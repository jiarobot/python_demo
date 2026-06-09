import sys
import math
import random
import numpy as np
from PyQt5.QtWidgets import QApplication, QWidget, QMainWindow, QVBoxLayout, QHBoxLayout, QLabel, QSlider
from PyQt5.QtGui import QPainter, QBrush, QPen, QRadialGradient, QLinearGradient, QColor, QFont, QFontDatabase, QPainterPath
from PyQt5.QtCore import Qt, QTimer, QPointF, QRectF, QPropertyAnimation, pyqtProperty, QEasingCurve

class UniverseParticle:
    def __init__(self, x, y, universe_scale):
        self.x = x
        self.y = y
        self.vx = random.uniform(-0.5, 0.5) * universe_scale
        self.vy = random.uniform(-0.5, 0.5) * universe_scale
        self.life = 1.0
        self.max_life = random.uniform(200, 500)
        self.size = random.uniform(0.5, 2) * universe_scale
        self.color = random.choice([
            QColor(255, 255, 200),  # 星星
            QColor(200, 220, 255),  # 蓝色星星
            QColor(255, 200, 200),  # 红色星星
            QColor(200, 255, 200)   # 绿色星星
        ])
        self.twinkle_speed = random.uniform(0.05, 0.1)
        self.twinkle_offset = random.random() * math.pi * 2
        
    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.life -= 1.0 / self.max_life
        
    def draw(self, painter, time):
        twinkle = (math.sin(time * self.twinkle_speed + self.twinkle_offset) + 1) / 2
        alpha = int(255 * self.life * (0.5 + twinkle * 0.5))
        color = QColor(self.color)
        color.setAlpha(alpha)
        painter.setBrush(QBrush(color))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(QPointF(self.x, self.y), self.size, self.size)

class Galaxy:
    def __init__(self, x, y, size, color, rotation_speed):
        self.x = x
        self.y = y
        self.size = size
        self.color = color
        self.rotation = 0
        self.rotation_speed = rotation_speed
        self.stars = []
        self.generate_stars()
        
    def generate_stars(self):
        # 生成螺旋星系的星星
        num_arms = random.randint(2, 4)
        stars_per_arm = 50
        
        for arm in range(num_arms):
            angle_offset = 2 * math.pi * arm / num_arms
            for i in range(stars_per_arm):
                distance = random.uniform(0.1, 1) * self.size
                angle = angle_offset + 5 * distance + random.uniform(-0.2, 0.2)
                
                x = self.x + math.cos(angle) * distance * self.size
                y = self.y + math.sin(angle) * distance * self.size
                
                brightness = random.uniform(0.5, 1)
                star_color = QColor(self.color)
                star_color.setHsv(
                    star_color.hue(),
                    star_color.saturation(),
                    int(star_color.value() * brightness)
                )
                
                self.stars.append({
                    'x': x, 'y': y,
                    'size': random.uniform(0.5, 2),
                    'color': star_color,
                    'twinkle_speed': random.uniform(0.02, 0.05),
                    'twinkle_offset': random.random() * math.pi * 2
                })
    
    def update(self):
        self.rotation += self.rotation_speed
        
    def draw(self, painter, time):
        # 绘制星系核心
        core_gradient = QRadialGradient(self.x, self.y, self.size * 0.3)
        core_gradient.setColorAt(0, self.color.lighter(180))
        core_gradient.setColorAt(1, self.color.darker(150))
        painter.setBrush(QBrush(core_gradient))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(QPointF(self.x, self.y), self.size * 0.3, self.size * 0.3)
        
        # 绘制星星
        for star in self.stars:
            # 计算旋转后的位置
            dx = star['x'] - self.x
            dy = star['y'] - self.y
            cos_angle = math.cos(self.rotation)
            sin_angle = math.sin(self.rotation)
            rotated_x = self.x + dx * cos_angle - dy * sin_angle
            rotated_y = self.y + dx * sin_angle + dy * cos_angle
            
            # 闪烁效果
            twinkle = (math.sin(time * star['twinkle_speed'] + star['twinkle_offset']) + 1) / 2
            alpha = int(255 * (0.7 + 0.3 * twinkle))
            color = QColor(star['color'])
            color.setAlpha(alpha)
            
            painter.setBrush(QBrush(color))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(QPointF(rotated_x, rotated_y), star['size'], star['size'])

class FlowerPetal:
    def __init__(self, center_x, center_y, length, width, angle, color, layer, petal_type="standard"):
        self.center_x = center_x
        self.center_y = center_y
        self.length = length
        self.width = width
        self.angle = angle
        self.color = color
        self.layer = layer
        self.petal_type = petal_type
        self.animation_offset = random.random() * math.pi * 2
        self.animation_speed = 0.02 + random.random() * 0.03
        self.curvature = random.uniform(0.5, 1.5)
        
    def draw(self, painter, time, bloom_progress):
        painter.save()
        painter.translate(self.center_x, self.center_y)
        painter.rotate(math.degrees(self.angle))
        
        # 花瓣绽放动画
        current_bloom = bloom_progress ** (1 + self.layer * 0.3)
        current_length = self.length * current_bloom
        current_width = self.width * current_bloom
        
        # 花瓣摆动动画
        anim_factor = math.sin(time * self.animation_speed + self.animation_offset) * 0.1
        current_length *= (1 + anim_factor * 0.05)
        current_width *= (1 + anim_factor * 0.02)
        
        if self.petal_type == "standard":
            self.draw_standard_petal(painter, current_length, current_width)
        elif self.petal_type == "curved":
            self.draw_curved_petal(painter, current_length, current_width)
        elif self.petal_type == "pointed":
            self.draw_pointed_petal(painter, current_length, current_width)
        elif self.petal_type == "spiral":
            self.draw_spiral_petal(painter, current_length, current_width)
            
        painter.restore()
    
    def draw_standard_petal(self, painter, length, width):
        path = QPainterPath()
        path.moveTo(0, 0)
        path.cubicTo(width * 0.3, -length * 0.2, 
                     width * 0.5, -length * 0.8, 
                     0, -length)
        path.cubicTo(-width * 0.5, -length * 0.8, 
                     -width * 0.3, -length * 0.2, 
                     0, 0)
        
        gradient = QRadialGradient(0, -length * 0.3, length * 0.8)
        base_color = QColor(self.color)
        gradient.setColorAt(0, base_color.lighter(180))
        gradient.setColorAt(0.5, base_color)
        gradient.setColorAt(1, base_color.darker(120))
        
        painter.setBrush(QBrush(gradient))
        painter.setPen(QPen(base_color.darker(150), 1, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.drawPath(path)
    
    def draw_curved_petal(self, painter, length, width):
        path = QPainterPath()
        path.moveTo(0, 0)
        path.cubicTo(width * 0.5, -length * 0.3, 
                     width * 0.3, -length * 0.8, 
                     0, -length)
        path.cubicTo(-width * 0.3, -length * 0.8, 
                     -width * 0.5, -length * 0.3, 
                     0, 0)
        
        gradient = QLinearGradient(0, 0, 0, -length)
        base_color = QColor(self.color)
        gradient.setColorAt(0, base_color.lighter(200))
        gradient.setColorAt(0.7, base_color)
        gradient.setColorAt(1, base_color.darker(120))
        
        painter.setBrush(QBrush(gradient))
        painter.setPen(QPen(base_color.darker(150), 1, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.drawPath(path)
    
    def draw_pointed_petal(self, painter, length, width):
        path = QPainterPath()
        path.moveTo(0, 0)
        path.lineTo(width * 0.5, -length * 0.3)
        path.lineTo(0, -length)
        path.lineTo(-width * 0.5, -length * 0.3)
        path.closeSubpath()
        
        gradient = QRadialGradient(0, -length * 0.5, length * 0.7)
        base_color = QColor(self.color)
        gradient.setColorAt(0, base_color.lighter(180))
        gradient.setColorAt(0.7, base_color)
        gradient.setColorAt(1, base_color.darker(130))
        
        painter.setBrush(QBrush(gradient))
        painter.setPen(QPen(base_color.darker(150), 1, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.drawPath(path)
    
    def draw_spiral_petal(self, painter, length, width):
        path = QPainterPath()
        path.moveTo(0, 0)
        
        # 创建螺旋状花瓣
        points = 20
        for i in range(points + 1):
            t = i / points
            angle = t * math.pi
            radius = width * (1 - t * 0.5)
            spiral_factor = math.sin(angle * self.curvature) * 0.3
            
            x = radius * math.cos(angle + spiral_factor)
            y = -length * t
            
            if i == 0:
                path.moveTo(x, y)
            else:
                path.lineTo(x, y)
        
        # 对称的另一半
        for i in range(points, -1, -1):
            t = i / points
            angle = t * math.pi
            radius = -width * (1 - t * 0.5)
            spiral_factor = math.sin(angle * self.curvature) * 0.3
            
            x = radius * math.cos(angle + spiral_factor)
            y = -length * t
            path.lineTo(x, y)
        
        path.closeSubpath()
        
        gradient = QLinearGradient(0, 0, 0, -length)
        base_color = QColor(self.color)
        gradient.setColorAt(0, base_color.lighter(200))
        gradient.setColorAt(0.5, base_color)
        gradient.setColorAt(1, base_color.darker(120))
        
        painter.setBrush(QBrush(gradient))
        painter.setPen(QPen(base_color.darker(150), 1, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.drawPath(path)

class CosmicFlowerWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("一花一世界：创世震撼效果")
        self.setGeometry(100, 100, 1200, 900)
        
        # 初始化参数
        self.center_x = 600
        self.center_y = 450
        self.flower_rotation = 0
        self.time = 0
        self.bloom_progress = 0
        self.universe_scale = 1.0
        self.show_universe = False
        self.universe_intensity = 0
        
        # 创建花瓣
        self.petals = []
        self.create_flower()
        
        # 创建宇宙粒子
        self.universe_particles = []
        self.create_universe_particles(500)
        
        # 创建星系
        self.galaxies = []
        self.create_galaxies()
        
        # 动画计时器
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_animation)
        self.timer.start(30)  # 约33fps
        
        # 绽放动画
        self.bloom_animation = QPropertyAnimation(self, b"bloom_progress")
        self.bloom_animation.setDuration(5000)
        self.bloom_animation.setStartValue(0.0)
        self.bloom_animation.setEndValue(1.0)
        self.bloom_animation.setEasingCurve(QEasingCurve.OutElastic)
        
        # 宇宙显现动画
        self.universe_animation = QPropertyAnimation(self, b"universe_intensity")
        self.universe_animation.setDuration(3000)
        self.universe_animation.setStartValue(0.0)
        self.universe_animation.setEndValue(1.0)
        self.universe_animation.setEasingCurve(QEasingCurve.InOutQuad)
        
        # 开始绽放动画
        self.bloom_animation.start()
        
    def create_flower(self):
        # 创建多层花瓣
        petal_colors = [
            "#FF6B9D", "#FF8E53", "#FFCE54", "#A0D468", 
            "#4FC1E9", "#AC92EC", "#ED5565", "#48CFAD"
        ]
        petal_types = ["standard", "curved", "pointed", "spiral"]
        
        layers = 5
        for layer in range(layers):
            petals_in_layer = 8 + layer * 4
            petal_length = 120 + layer * 40
            petal_width = 60 + layer * 15
            
            for i in range(petals_in_layer):
                angle = 2 * math.pi * i / petals_in_layer + (layer * 0.1)
                color = petal_colors[(layer * 2 + i) % len(petal_colors)]
                petal_type = petal_types[(layer + i) % len(petal_types)]
                
                petal = FlowerPetal(
                    self.center_x, self.center_y,
                    petal_length, petal_width,
                    angle, color, layer, petal_type
                )
                self.petals.append(petal)
    
    def create_universe_particles(self, count):
        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            distance = random.uniform(100, 400)
            x = self.center_x + math.cos(angle) * distance
            y = self.center_y + math.sin(angle) * distance
            self.universe_particles.append(UniverseParticle(x, y, self.universe_scale))
    
    def create_galaxies(self):
        # 在花朵周围创建几个星系
        galaxy_positions = [
            (self.center_x - 200, self.center_y - 150),
            (self.center_x + 250, self.center_y - 100),
            (self.center_x - 150, self.center_y + 200),
            (self.center_x + 180, self.center_y + 180)
        ]
        
        galaxy_colors = [
            QColor(100, 150, 255),  # 蓝色星系
            QColor(255, 150, 100),  # 橙色星系
            QColor(150, 255, 150),  # 绿色星系
            QColor(255, 100, 255)   # 紫色星系
        ]
        
        for i, (x, y) in enumerate(galaxy_positions):
            size = random.uniform(40, 80)
            color = galaxy_colors[i % len(galaxy_colors)]
            rotation_speed = random.uniform(0.001, 0.005)
            self.galaxies.append(Galaxy(x, y, size, color, rotation_speed))
    
    def update_animation(self):
        self.time += 0.05
        self.flower_rotation += 0.2
        
        # 更新宇宙粒子
        for particle in self.universe_particles[:]:
            particle.update()
            if particle.life <= 0:
                self.universe_particles.remove(particle)
        
        # 添加新的宇宙粒子
        if len(self.universe_particles) < 500 and random.random() < 0.1:
            angle = random.uniform(0, 2 * math.pi)
            distance = random.uniform(100, 400)
            x = self.center_x + math.cos(angle) * distance
            y = self.center_y + math.sin(angle) * distance
            self.universe_particles.append(UniverseParticle(x, y, self.universe_scale))
        
        # 更新星系
        for galaxy in self.galaxies:
            galaxy.update()
        
        # 当花朵完全绽放时显示宇宙
        if self.bloom_progress > 0.8 and not self.show_universe:
            self.show_universe = True
            self.universe_animation.start()
        
        self.update()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 绘制背景
        self.draw_background(painter)
        
        # 绘制宇宙效果
        if self.show_universe:
            self.draw_universe(painter)
        
        # 绘制花瓣
        for petal in self.petals:
            petal.draw(painter, self.time, self.bloom_progress)
        
        # 绘制花蕊
        self.draw_center(painter)
        
        # 绘制标题和说明
        self.draw_text(painter)
    
    def draw_background(self, painter):
        # 创建深邃的宇宙背景
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0, QColor("#0f0c29"))
        gradient.setColorAt(0.5, QColor("#302b63"))
        gradient.setColorAt(1, QColor("#24243e"))
        painter.fillRect(self.rect(), QBrush(gradient))
        
        # 添加一些遥远的星星
        painter.setPen(QPen(QColor(255, 255, 255, 100), 1))
        for _ in range(100):
            x = random.randint(0, self.width())
            y = random.randint(0, self.height())
            size = random.randint(1, 2)
            painter.drawEllipse(x, y, size, size)
    
    def draw_universe(self, painter):
        # 绘制宇宙粒子
        for particle in self.universe_particles:
            particle.draw(painter, self.time)
        
        # 绘制星系
        for galaxy in self.galaxies:
            galaxy.draw(painter, self.time)
        
        # 添加宇宙光晕效果
        if self.universe_intensity > 0:
            glow_gradient = QRadialGradient(self.center_x, self.center_y, 500)
            glow_gradient.setColorAt(0, QColor(255, 255, 255, int(30 * self.universe_intensity)))
            glow_gradient.setColorAt(1, QColor(255, 255, 255, 0))
            painter.setBrush(QBrush(glow_gradient))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(QPointF(self.center_x, self.center_y), 500, 500)
    
    def draw_center(self, painter):
        painter.save()
        painter.translate(self.center_x, self.center_y)
        painter.rotate(self.flower_rotation)
        
        # 多层花蕊
        sizes = [80, 60, 40, 20]
        colors = [QColor("#FFCE54"), QColor("#FFA726"), QColor("#FF9800"), QColor("#F57C00")]
        
        for i, (size, color) in enumerate(zip(sizes, colors)):
            current_size = size * self.bloom_progress
            
            # 花蕊渐变
            gradient = QRadialGradient(0, 0, current_size * 0.8)
            gradient.setColorAt(0, color.lighter(180))
            gradient.setColorAt(0.7, color)
            gradient.setColorAt(1, color.darker(150))
            
            painter.setBrush(QBrush(gradient))
            painter.setPen(QPen(color.darker(200), 2))
            painter.drawEllipse(int(-current_size/2), int(-current_size/2), int(current_size), int(current_size))
            
            # 花蕊纹理
            painter.setPen(QPen(color.darker(150), 1))
            for j in range(12):
                angle = 2 * math.pi * j / 12
                inner_radius = current_size * 0.3
                outer_radius = current_size * 0.45
                
                x1 = int(math.cos(angle) * inner_radius)
                y1 = int(math.sin(angle) * inner_radius)
                x2 = int(math.cos(angle) * outer_radius)
                y2 = int(math.sin(angle) * outer_radius)
                
                painter.drawLine(x1, y1, x2, y2)
        
        # 中心光点
        if self.bloom_progress > 0.5:
            glow_intensity = min(1.0, (self.bloom_progress - 0.5) * 2)
            glow_gradient = QRadialGradient(0, 0, 30)
            glow_gradient.setColorAt(0, QColor(255, 255, 255, int(200 * glow_intensity)))
            glow_gradient.setColorAt(1, QColor(255, 255, 255, 0))
            painter.setBrush(QBrush(glow_gradient))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(-30, -30, 60, 60)
        
        painter.restore()
    
    def draw_text(self, painter):
        # 绘制标题
        painter.setPen(QColor(255, 255, 255))
        font = QFont("Arial", 32, QFont.Bold)
        painter.setFont(font)
        painter.drawText(20, 50, "一花一世界")
        
        font = QFont("Arial", 16)
        painter.setFont(font)
        painter.drawText(20, 80, "一叶一菩提")
        
        # 绘制说明
        if self.show_universe and self.universe_intensity > 0.5:
            font = QFont("Arial", 14)
            painter.setFont(font)
            alpha = int(255 * min(1.0, (self.universe_intensity - 0.5) * 2))
            painter.setPen(QColor(255, 255, 255, alpha))
            
            messages = [
                "在这朵花中，你看到了整个宇宙",
                "每一个花瓣都承载着无数星辰",
                "生命与宇宙的奥秘在此绽放",
                "微观与宏观的界限在此消融"
            ]
            
            for i, message in enumerate(messages):
                painter.drawText(20, 120 + i * 25, message)
    
    # 属性动画所需的属性
    @pyqtProperty(float)
    def bloom_progress(self):
        return self._bloom_progress
    
    @bloom_progress.setter
    def bloom_progress(self, value):
        self._bloom_progress = value
    
    @pyqtProperty(float)
    def universe_intensity(self):
        return self._universe_intensity
    
    @universe_intensity.setter
    def universe_intensity(self, value):
        self._universe_intensity = value

class ControlPanel(QWidget):
    def __init__(self, flower_widget):
        super().__init__()
        self.flower_widget = flower_widget
        
        layout = QVBoxLayout()
        
        # 添加控制按钮和滑块
        self.bloom_slider = QSlider(Qt.Horizontal)
        self.bloom_slider.setRange(0, 100)
        self.bloom_slider.setValue(0)
        self.bloom_slider.valueChanged.connect(self.on_bloom_changed)
        
        layout.addWidget(QLabel("绽放进度:"))
        layout.addWidget(self.bloom_slider)
        
        self.setLayout(layout)
    
    def on_bloom_changed(self, value):
        self.flower_widget.bloom_progress = value / 100.0
        self.flower_widget.update()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.flower_widget = CosmicFlowerWidget()
        self.control_panel = ControlPanel(self.flower_widget)
        
        # 创建主布局
        central_widget = QWidget()
        layout = QHBoxLayout()
        layout.addWidget(self.flower_widget, 4)
        layout.addWidget(self.control_panel, 1)
        central_widget.setLayout(layout)
        
        self.setCentralWidget(central_widget)
        self.setWindowTitle("一花一世界：创世震撼效果")
        self.setGeometry(50, 50, 1400, 900)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())