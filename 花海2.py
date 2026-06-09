import sys
import random
import math
import numpy as np
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QSlider, QLabel, QCheckBox, QComboBox,
                             QGroupBox, QPushButton, QSpinBox, QDoubleSpinBox)
from PyQt5.QtCore import Qt, QTimer, QPointF, QRectF, QPropertyAnimation, pyqtProperty
from PyQt5.QtGui import (QPainter, QBrush, QColor, QRadialGradient, QPen, QFont, 
                         QLinearGradient, QPainterPath, QImage, QPixmap)

class AdvancedFlowerParticle:
    """高级花朵粒子类，支持3D效果和物理模拟"""
    def __init__(self, width, height):
        # 位置和大小
        self.x = random.uniform(0, width)
        self.y = random.uniform(0, height)
        self.z = random.uniform(0.3, 1.0)  # 深度值，用于3D效果
        self.base_size = random.uniform(10, 35)
        self.size = self.base_size * self.z  # 根据深度调整大小
        
        # 颜色和外观
        self.color_scheme_idx = random.randint(0, 4)
        self.petal_count = random.randint(5, 9)
        self.petal_shape = random.choice(["oval", "teardrop", "star", "heart"])
        
        # 运动和物理
        self.velocity = QPointF(
            random.uniform(-1.5, 1.5) * (1/self.z),  # 远处移动更慢
            random.uniform(-1.5, 1.5) * (1/self.z)
        )
        self.angle = random.uniform(0, 2 * math.pi)
        self.rotation_speed = random.uniform(-0.03, 0.03)
        self.pulse_speed = random.uniform(0.05, 0.15)
        self.pulse_offset = random.uniform(0, 2 * math.pi)
        
        # 生命周期
        self.life = 1.0
        self.decay_rate = random.uniform(0.001, 0.004)
        self.age = 0
        
        # 物理属性
        self.mass = self.size * 0.1
        self.attraction_force = 0
        self.repulsion_force = 0
        
    def update(self, mouse_x, mouse_y, attraction_strength, repulsion_strength, wind_x, wind_y):
        """更新粒子状态，考虑物理交互"""
        self.age += 1
        
        # 计算鼠标交互力
        dx = mouse_x - self.x
        dy = mouse_y - self.y
        distance = max(math.sqrt(dx*dx + dy*dy), 0.1)
        
        # 吸引力/排斥力计算
        if distance < 150:  # 鼠标影响范围
            force_strength = (150 - distance) / 150
            self.attraction_force = attraction_strength * force_strength / distance
            self.repulsion_force = repulsion_strength * force_strength / distance
            
            # 计算力的方向
            force_x = dx * (self.attraction_force - self.repulsion_force)
            force_y = dy * (self.attraction_force - self.repulsion_force)
            
            # 应用力（考虑质量）
            self.velocity.setX(self.velocity.x() + force_x / self.mass)
            self.velocity.setY(self.velocity.y() + force_y / self.mass)
        
        # 应用风力
        self.velocity.setX(self.velocity.x() + wind_x * (1/self.z))
        self.velocity.setY(self.velocity.y() + wind_y * (1/self.z))
        
        # 应用速度
        self.x += self.velocity.x()
        self.y += self.velocity.y()
        
        # 边界检查
        if self.x < 0 or self.x > self.width:
            self.velocity.setX(-self.velocity.x() * 0.8)
        if self.y < 0 or self.y > self.height:
            self.velocity.setY(-self.velocity.y() * 0.8)
            
        # 旋转和脉动
        self.angle += self.rotation_speed
        self.size = self.base_size * self.z * (0.7 + 0.3 * math.sin(self.pulse_offset + self.pulse_speed * self.age))
        
        # 生命周期
        self.life -= self.decay_rate
        return self.life > 0
    
    def set_dimensions(self, width, height):
        """设置画布尺寸用于边界检查"""
        self.width = width
        self.height = height

class FlowerField(QWidget):
    """高级花海效果主窗口"""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("颠覆性花海震撼效果")
        self.setGeometry(50, 50, 1400, 900)
        
        # 初始化参数
        self.flower_count = 800
        self.attraction_strength = 0.0
        self.repulsion_strength = 0.0
        self.wind_x = 0.0
        self.wind_y = 0.0
        self.mouse_x = -1000  # 初始位置在屏幕外
        self.mouse_y = -1000
        self.mouse_pressed = False
        
        # 视觉效果参数
        self.bloom_intensity = 1.0
        self.color_cycle_speed = 0.01
        self.color_cycle_offset = 0.0
        self.trail_effect = True
        self.bloom_effect = True
        self.depth_effect = True
        
        # 色彩方案
        self.color_schemes = [
            # 粉色系
            [(255, 20, 147), (255, 105, 180), (255, 182, 193), (199, 21, 133), (219, 112, 147)],
            # 紫色系
            [(138, 43, 226), (147, 112, 219), (186, 85, 211), (153, 50, 204), (128, 0, 128)],
            # 金色系
            [(255, 215, 0), (255, 165, 0), (255, 140, 0), (218, 165, 32), (184, 134, 11)],
            # 绿色系
            [(0, 255, 127), (50, 205, 50), (144, 238, 144), (60, 179, 113), (46, 139, 87)],
            # 蓝色系
            [(30, 144, 255), (0, 191, 255), (135, 206, 250), (70, 130, 180), (65, 105, 225)]
        ]
        
        # 初始化粒子列表
        self.flowers = []
        self.trails = []  # 轨迹效果
        
        # 设置定时器
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_field)
        self.timer.start(16)  # 约60FPS
        
        # 初始化花海
        self.generate_flowers(self.flower_count)
        
        # 设置背景
        self.set_background()
        
    def set_background(self):
        """设置渐变背景"""
        self.background = QImage(self.size(), QImage.Format_RGB32)
        painter = QPainter(self.background)
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0, QColor(10, 5, 30))
        gradient.setColorAt(1, QColor(5, 15, 40))
        painter.fillRect(self.rect(), QBrush(gradient))
        painter.end()
        
    def generate_flowers(self, count):
        """生成指定数量的花朵"""
        for _ in range(count):
            flower = AdvancedFlowerParticle(self.width(), self.height())
            self.flowers.append(flower)
    
    def update_field(self):
        """更新花海状态"""
        # 更新颜色循环
        self.color_cycle_offset += self.color_cycle_speed
        
        # 更新所有花朵
        for flower in self.flowers:
            flower.set_dimensions(self.width(), self.height())
            if not flower.update(self.mouse_x, self.mouse_y, 
                               self.attraction_strength, self.repulsion_strength,
                               self.wind_x, self.wind_y):
                # 重置死亡的花朵
                flower.x = random.uniform(0, self.width())
                flower.y = random.uniform(0, self.height())
                flower.life = 1.0
                flower.velocity = QPointF(
                    random.uniform(-1.5, 1.5) * (1/flower.z),
                    random.uniform(-1.5, 1.5) * (1/flower.z)
                )
        
        # 更新轨迹效果
        if self.trail_effect:
            for flower in self.flowers:
                if random.random() < 0.1:  # 10%的概率添加轨迹点
                    trail_alpha = int(flower.life * 100)
                    trail_size = flower.size * 0.3
                    self.trails.append({
                        'x': flower.x,
                        'y': flower.y,
                        'size': trail_size,
                        'color': self.get_flower_color(flower),
                        'alpha': trail_alpha,
                        'life': 1.0
                    })
            
            # 更新和移除旧轨迹
            self.trails = [t for t in self.trails if t['life'] > 0]
            for trail in self.trails:
                trail['life'] -= 0.02
                trail['alpha'] = int(trail['alpha'] * 0.95)
        
        # 触发重绘
        self.update()
    
    def get_flower_color(self, flower):
        """根据花朵属性获取颜色"""
        base_color_idx = (flower.color_scheme_idx + int(self.color_cycle_offset)) % len(self.color_schemes)
        base_color = random.choice(self.color_schemes[base_color_idx])
        
        # 根据深度调整颜色亮度
        brightness_factor = 0.7 + 0.3 * flower.z
        return (
            int(base_color[0] * brightness_factor),
            int(base_color[1] * brightness_factor),
            int(base_color[2] * brightness_factor)
        )
    
    def paintEvent(self, event):
        """绘制花海"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 绘制背景
        painter.drawImage(0, 0, self.background)
        
        # 绘制轨迹效果
        if self.trail_effect:
            for trail in self.trails:
                alpha = trail['alpha']
                if alpha > 0:
                    color = QColor(*trail['color'], alpha)
                    painter.setBrush(QBrush(color))
                    painter.setPen(Qt.NoPen)
                    painter.drawEllipse(QPointF(trail['x'], trail['y']), 
                                       trail['size'], trail['size'])
        
        # 绘制所有花朵（按深度排序，实现正确遮挡）
        sorted_flowers = sorted(self.flowers, key=lambda f: f.z)
        for flower in sorted_flowers:
            self.draw_advanced_flower(painter, flower)
        
        # 绘制UI信息
        self.draw_ui(painter)
    
    def draw_advanced_flower(self, painter, flower):
        """绘制高级花朵"""
        alpha = int(255 * flower.life * self.bloom_intensity)
        if alpha <= 0:
            return
            
        flower_color = self.get_flower_color(flower)
        center_color = (255, 255, 0)  # 黄色花蕊
        
        # 根据深度调整透明度（实现大气透视）
        if self.depth_effect:
            depth_alpha = int(alpha * (0.3 + 0.7 * flower.z))
        else:
            depth_alpha = alpha
            
        # 绘制花瓣
        for i in range(flower.petal_count):
            angle = flower.angle + i * (2 * math.pi / flower.petal_count)
            
            # 花瓣位置（考虑深度）
            petal_x = flower.x + math.cos(angle) * flower.size * 0.7
            petal_y = flower.y + math.sin(angle) * flower.size * 0.7
            
            # 花瓣大小
            petal_width = flower.size * 0.8
            petal_height = flower.size * 0.5
            
            # 创建花瓣颜色
            petal_color = QColor(*flower_color, depth_alpha)
            
            # 绘制花瓣
            painter.save()
            painter.translate(petal_x, petal_y)
            painter.rotate(math.degrees(angle))
            
            # 根据花瓣形状绘制
            if flower.petal_shape == "oval":
                self.draw_oval_petal(painter, petal_width, petal_height, petal_color)
            elif flower.petal_shape == "teardrop":
                self.draw_teardrop_petal(painter, petal_width, petal_height, petal_color)
            elif flower.petal_shape == "star":
                self.draw_star_petal(painter, petal_width, petal_height, petal_color)
            elif flower.petal_shape == "heart":
                self.draw_heart_petal(painter, petal_width, petal_height, petal_color)
            
            painter.restore()
        
        # 绘制花蕊
        if self.bloom_effect:
            center_alpha = int(depth_alpha * 0.8)
            center_qcolor = QColor(*center_color, center_alpha)
            painter.setBrush(QBrush(center_qcolor))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(QPointF(flower.x, flower.y), 
                               flower.size * 0.2, flower.size * 0.2)
    
    def draw_oval_petal(self, painter, width, height, color):
        """绘制椭圆形花瓣"""
        gradient = QRadialGradient(0, 0, width/2)
        gradient.setColorAt(0, color)
        lighter_color = self.lighten_color((color.red(), color.green(), color.blue()))
        gradient.setColorAt(1, QColor(*lighter_color, color.alpha()//2))
        
        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(QRectF(-width/2, -height/2, width, height))
    
    def draw_teardrop_petal(self, painter, width, height, color):
        """绘制泪滴形花瓣"""
        path = QPainterPath()
        path.moveTo(0, -height/2)
        path.cubicTo(width/2, -height/4, width/2, height/4, 0, height/2)
        path.cubicTo(-width/2, height/4, -width/2, -height/4, 0, -height/2)
        
        gradient = QRadialGradient(0, 0, width/2)
        gradient.setColorAt(0, color)
        lighter_color = self.lighten_color((color.red(), color.green(), color.blue()))
        gradient.setColorAt(1, QColor(*lighter_color, color.alpha()//2))
        
        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.NoPen)
        painter.drawPath(path)
    
    def draw_star_petal(self, painter, width, height, color):
        """绘制星形花瓣"""
        path = QPainterPath()
        points = 5
        for i in range(points * 2):
            angle = i * math.pi / points
            radius = width/2 if i % 2 == 0 else width/4
            x = radius * math.cos(angle)
            y = radius * math.sin(angle) * (height/width)
            if i == 0:
                path.moveTo(x, y)
            else:
                path.lineTo(x, y)
        path.closeSubpath()
        
        gradient = QRadialGradient(0, 0, width/2)
        gradient.setColorAt(0, color)
        lighter_color = self.lighten_color((color.red(), color.green(), color.blue()))
        gradient.setColorAt(1, QColor(*lighter_color, color.alpha()//2))
        
        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.NoPen)
        painter.drawPath(path)
    
    def draw_heart_petal(self, painter, width, height, color):
        """绘制心形花瓣"""
        path = QPainterPath()
        path.moveTo(0, -height/3)
        path.cubicTo(width/2, -height/2, width/2, height/4, 0, height/2)
        path.cubicTo(-width/2, height/4, -width/2, -height/2, 0, -height/3)
        
        gradient = QRadialGradient(0, 0, width/2)
        gradient.setColorAt(0, color)
        lighter_color = self.lighten_color((color.red(), color.green(), color.blue()))
        gradient.setColorAt(1, QColor(*lighter_color, color.alpha()//2))
        
        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.NoPen)
        painter.drawPath(path)
    
    def draw_ui(self, painter):
        """绘制UI信息"""
        # 绘制标题
        painter.setPen(QColor(255, 255, 255))
        font = QFont("Arial", 28, QFont.Bold)
        painter.setFont(font)
        painter.drawText(self.rect(), Qt.AlignTop | Qt.AlignHCenter, "颠覆性花海震撼效果")
        
        # 绘制说明文字
        font = QFont("Arial", 12)
        painter.setFont(font)
        painter.drawText(self.rect(), Qt.AlignBottom | Qt.AlignHCenter, 
                        "鼠标移动: 吸引/排斥花朵 | 鼠标点击: 切换模式 | 空格: 重置 | ESC: 退出")
        
        # 绘制统计信息
        stats_text = f"花朵数量: {len(self.flowers)} | FPS: {self.calculate_fps():.1f}"
        painter.drawText(10, self.height() - 10, stats_text)
    
    def calculate_fps(self):
        """计算帧率（简化版）"""
        return 60  # 实际实现需要更复杂的计时逻辑
    
    def lighten_color(self, color):
        """使颜色变亮"""
        r, g, b = color
        return (
            min(255, int(r * 1.3)),
            min(255, int(g * 1.3)),
            min(255, int(b * 1.3))
        )
    
    def mouseMoveEvent(self, event):
        """鼠标移动事件"""
        self.mouse_x = event.x()
        self.mouse_y = event.y()
    
    def mousePressEvent(self, event):
        """鼠标点击事件"""
        self.mouse_pressed = True
        # 切换吸引/排斥模式
        if self.attraction_strength > 0:
            self.attraction_strength = 0
            self.repulsion_strength = 5.0
        else:
            self.attraction_strength = 5.0
            self.repulsion_strength = 0
    
    def mouseReleaseEvent(self, event):
        """鼠标释放事件"""
        self.mouse_pressed = False
    
    def leaveEvent(self, event):
        """鼠标离开窗口事件"""
        self.mouse_x = -1000
        self.mouse_y = -1000
    
    def keyPressEvent(self, event):
        """按键事件处理"""
        if event.key() == Qt.Key_Escape:
            self.close()
        elif event.key() == Qt.Key_Space:
            # 空格键重置花朵
            self.flowers = []
            self.generate_flowers(self.flower_count)
        elif event.key() == Qt.Key_Up:
            self.wind_y = -0.5
        elif event.key() == Qt.Key_Down:
            self.wind_y = 0.5
        elif event.key() == Qt.Key_Left:
            self.wind_x = -0.5
        elif event.key() == Qt.Key_Right:
            self.wind_x = 0.5
    
    def keyReleaseEvent(self, event):
        """按键释放事件"""
        if event.key() in (Qt.Key_Up, Qt.Key_Down):
            self.wind_y = 0.0
        elif event.key() in (Qt.Key_Left, Qt.Key_Right):
            self.wind_x = 0.0

class ControlPanel(QWidget):
    """控制面板"""
    def __init__(self, flower_field):
        super().__init__()
        self.flower_field = flower_field
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout()
        
        # 花朵数量控制
        flower_count_layout = QHBoxLayout()
        flower_count_layout.addWidget(QLabel("花朵数量:"))
        self.flower_count_spin = QSpinBox()
        self.flower_count_spin.setRange(100, 5000)
        self.flower_count_spin.setValue(self.flower_field.flower_count)
        self.flower_count_spin.valueChanged.connect(self.update_flower_count)
        flower_count_layout.addWidget(self.flower_count_spin)
        layout.addLayout(flower_count_layout)
        
        # 视觉效果控制
        effects_group = QGroupBox("视觉效果")
        effects_layout = QVBoxLayout()
        
        # 绽放强度
        bloom_layout = QHBoxLayout()
        bloom_layout.addWidget(QLabel("绽放强度:"))
        self.bloom_slider = QSlider(Qt.Horizontal)
        self.bloom_slider.setRange(0, 100)
        self.bloom_slider.setValue(int(self.flower_field.bloom_intensity * 100))
        self.bloom_slider.valueChanged.connect(self.update_bloom_intensity)
        bloom_layout.addWidget(self.bloom_slider)
        effects_layout.addLayout(bloom_layout)
        
        # 颜色循环速度
        color_speed_layout = QHBoxLayout()
        color_speed_layout.addWidget(QLabel("颜色速度:"))
        self.color_speed_slider = QSlider(Qt.Horizontal)
        self.color_speed_slider.setRange(0, 100)
        self.color_speed_slider.setValue(int(self.flower_field.color_cycle_speed * 1000))
        self.color_speed_slider.valueChanged.connect(self.update_color_speed)
        color_speed_layout.addWidget(self.color_speed_slider)
        effects_layout.addLayout(color_speed_layout)
        
        # 效果复选框
        self.trail_check = QCheckBox("轨迹效果")
        self.trail_check.setChecked(self.flower_field.trail_effect)
        self.trail_check.stateChanged.connect(self.update_trail_effect)
        effects_layout.addWidget(self.trail_check)
        
        self.bloom_check = QCheckBox("绽放效果")
        self.bloom_check.setChecked(self.flower_field.bloom_effect)
        self.bloom_check.stateChanged.connect(self.update_bloom_effect)
        effects_layout.addWidget(self.bloom_check)
        
        self.depth_check = QCheckBox("深度效果")
        self.depth_check.setChecked(self.flower_field.depth_effect)
        self.depth_check.stateChanged.connect(self.update_depth_effect)
        effects_layout.addWidget(self.depth_check)
        
        effects_group.setLayout(effects_layout)
        layout.addWidget(effects_group)
        
        # 物理控制
        physics_group = QGroupBox("物理控制")
        physics_layout = QVBoxLayout()
        
        # 吸引力
        attraction_layout = QHBoxLayout()
        attraction_layout.addWidget(QLabel("吸引力:"))
        self.attraction_slider = QSlider(Qt.Horizontal)
        self.attraction_slider.setRange(0, 100)
        self.attraction_slider.setValue(0)
        self.attraction_slider.valueChanged.connect(self.update_attraction)
        attraction_layout.addWidget(self.attraction_slider)
        physics_layout.addLayout(attraction_layout)
        
        # 排斥力
        repulsion_layout = QHBoxLayout()
        repulsion_layout.addWidget(QLabel("排斥力:"))
        self.repulsion_slider = QSlider(Qt.Horizontal)
        self.repulsion_slider.setRange(0, 100)
        self.repulsion_slider.setValue(0)
        self.repulsion_slider.valueChanged.connect(self.update_repulsion)
        repulsion_layout.addWidget(self.repulsion_slider)
        physics_layout.addLayout(repulsion_layout)
        
        # 风力
        wind_x_layout = QHBoxLayout()
        wind_x_layout.addWidget(QLabel("水平风力:"))
        self.wind_x_spin = QDoubleSpinBox()
        self.wind_x_spin.setRange(-2.0, 2.0)
        self.wind_x_spin.setSingleStep(0.1)
        self.wind_x_spin.setValue(self.flower_field.wind_x)
        self.wind_x_spin.valueChanged.connect(self.update_wind_x)
        wind_x_layout.addWidget(self.wind_x_spin)
        physics_layout.addLayout(wind_x_layout)
        
        wind_y_layout = QHBoxLayout()
        wind_y_layout.addWidget(QLabel("垂直风力:"))
        self.wind_y_spin = QDoubleSpinBox()
        self.wind_y_spin.setRange(-2.0, 2.0)
        self.wind_y_spin.setSingleStep(0.1)
        self.wind_y_spin.setValue(self.flower_field.wind_y)
        self.wind_y_spin.valueChanged.connect(self.update_wind_y)
        wind_y_layout.addWidget(self.wind_y_spin)
        physics_layout.addLayout(wind_y_layout)
        
        physics_group.setLayout(physics_layout)
        layout.addWidget(physics_group)
        
        # 重置按钮
        reset_button = QPushButton("重置场景")
        reset_button.clicked.connect(self.reset_scene)
        layout.addWidget(reset_button)
        
        layout.addStretch(1)
        self.setLayout(layout)
    
    def update_flower_count(self, value):
        """更新花朵数量"""
        self.flower_field.flower_count = value
        self.flower_field.flowers = []
        self.flower_field.generate_flowers(value)
    
    def update_bloom_intensity(self, value):
        """更新绽放强度"""
        self.flower_field.bloom_intensity = value / 100.0
    
    def update_color_speed(self, value):
        """更新颜色循环速度"""
        self.flower_field.color_cycle_speed = value / 1000.0
    
    def update_trail_effect(self, state):
        """更新轨迹效果"""
        self.flower_field.trail_effect = (state == Qt.Checked)
    
    def update_bloom_effect(self, state):
        """更新绽放效果"""
        self.flower_field.bloom_effect = (state == Qt.Checked)
    
    def update_depth_effect(self, state):
        """更新深度效果"""
        self.flower_field.depth_effect = (state == Qt.Checked)
    
    def update_attraction(self, value):
        """更新吸引力"""
        self.flower_field.attraction_strength = value / 10.0
    
    def update_repulsion(self, value):
        """更新排斥力"""
        self.flower_field.repulsion_strength = value / 10.0
    
    def update_wind_x(self, value):
        """更新水平风力"""
        self.flower_field.wind_x = value
    
    def update_wind_y(self, value):
        """更新垂直风力"""
        self.flower_field.wind_y = value
    
    def reset_scene(self):
        """重置场景"""
        self.flower_field.flowers = []
        self.flower_field.generate_flowers(self.flower_field.flower_count)
        self.flower_field.trails = []
        self.flower_field.wind_x = 0.0
        self.flower_field.wind_y = 0.0
        self.flower_field.attraction_strength = 0.0
        self.flower_field.repulsion_strength = 0.0
        
        # 重置UI控件
        self.wind_x_spin.setValue(0.0)
        self.wind_y_spin.setValue(0.0)
        self.attraction_slider.setValue(0)
        self.repulsion_slider.setValue(0)

class MainWindow(QMainWindow):
    """主窗口"""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("颠覆性花海震撼效果 - 完整版")
        
        # 创建中央部件和布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QHBoxLayout(central_widget)
        
        # 创建花海效果区域
        self.flower_field = FlowerField()
        layout.addWidget(self.flower_field, 4)  # 4/5的空间
        
        # 创建控制面板
        self.control_panel = ControlPanel(self.flower_field)
        layout.addWidget(self.control_panel, 1)  # 1/5的空间

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 设置应用程序样式
    app.setStyle('Fusion')
    
    window = MainWindow()
    window.showMaximized()
    
    sys.exit(app.exec_())