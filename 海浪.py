import sys
import math
import random
import numpy as np
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QSlider, QLabel, QComboBox, QGroupBox,
                             QCheckBox, QSpinBox, QDoubleSpinBox, QPushButton)
from PyQt5.QtCore import QTimer, Qt, QPointF, QRectF, pyqtSignal
from PyQt5.QtGui import (QPainter, QColor, QPen, QBrush, QRadialGradient, 
                         QLinearGradient, QFont, QPainterPath)

class OceanParameters:
    """海洋参数类，存储所有可调整的参数"""
    def __init__(self):
        # 基础参数
        self.wave_amplitude = 25.0
        self.wave_frequency = 0.03
        self.wave_speed = 0.05
        self.wave_roughness = 0.5
        
        # 风力参数
        self.wind_speed = 5.0
        self.wind_direction = 0.0  # 角度，0表示从左到右
        
        # 光照参数
        self.light_intensity = 1.0
        self.light_direction = 45.0  # 角度，0表示从左边
        self.water_color = QColor(0, 100, 200)
        self.foam_intensity = 0.7
        
        # 高级效果
        self.reflection_intensity = 0.8
        self.caustics_intensity = 0.6
        self.depth_effect = 0.7
        self.animation_speed = 1.0
        
        # 天气效果
        self.weather_type = "晴天"  # 晴天, 多云, 阴天, 暴风雨
        self.rain_intensity = 0.0
        
    def apply_weather_preset(self, weather_type):
        """应用天气预设"""
        self.weather_type = weather_type
        
        if weather_type == "晴天":
            self.wave_amplitude = 15.0
            self.wave_frequency = 0.02
            self.wind_speed = 3.0
            self.light_intensity = 1.0
            self.foam_intensity = 0.3
            self.water_color = QColor(0, 120, 220)
            
        elif weather_type == "多云":
            self.wave_amplitude = 20.0
            self.wave_frequency = 0.025
            self.wind_speed = 5.0
            self.light_intensity = 0.7
            self.foam_intensity = 0.5
            self.water_color = QColor(0, 90, 180)
            
        elif weather_type == "阴天":
            self.wave_amplitude = 25.0
            self.wave_frequency = 0.03
            self.wind_speed = 8.0
            self.light_intensity = 0.4
            self.foam_intensity = 0.7
            self.water_color = QColor(0, 70, 150)
            
        elif weather_type == "暴风雨":
            self.wave_amplitude = 40.0
            self.wave_frequency = 0.04
            self.wind_speed = 15.0
            self.light_intensity = 0.2
            self.foam_intensity = 0.9
            self.water_color = QColor(0, 50, 120)
            self.rain_intensity = 0.8

class WaveParticle:
    """波浪粒子类"""
    def __init__(self, x, y, params):
        self.x = x
        self.y = y
        self.base_y = y
        self.params = params
        
        # 粒子属性
        self.amplitude = random.uniform(0.5, 1.5) * params.wave_amplitude
        self.frequency = random.uniform(0.8, 1.2) * params.wave_frequency
        self.phase = random.uniform(0, 2 * math.pi)
        self.speed = random.uniform(0.8, 1.2) * params.wave_speed
        
        # 泡沫属性
        self.foam_amount = 0.0
        self.foam_decay = random.uniform(0.01, 0.05)
        
    def update(self, time):
        """更新粒子状态"""
        # 计算波浪高度
        wave_height = math.sin(self.x * self.frequency + time * self.speed + self.phase) * self.amplitude
        
        # 应用风力影响
        wind_effect = math.sin(self.x * 0.01 + time * 0.02) * self.params.wind_speed * 0.5
        self.y = self.base_y + wave_height + wind_effect
        
        # 更新泡沫
        if wave_height > self.amplitude * 0.7:
            self.foam_amount = min(1.0, self.foam_amount + 0.1)
        else:
            self.foam_amount = max(0.0, self.foam_amount - self.foam_decay)

class RainDrop:
    """雨滴类"""
    def __init__(self, width, height):
        self.x = random.uniform(0, width)
        self.y = random.uniform(-50, 0)
        self.speed = random.uniform(5, 15)
        self.length = random.uniform(5, 15)
        self.thickness = random.uniform(1, 2)
        
    def update(self, width, height):
        """更新雨滴位置"""
        self.y += self.speed
        if self.y > height:
            self.y = random.uniform(-50, 0)
            self.x = random.uniform(0, width)

class GlassOceanWidget(QWidget):
    """玻璃海效果主窗口"""
    
    # 定义信号
    parametersChanged = pyqtSignal()
    
    def __init__(self, params):
        super().__init__()
        self.params = params
        self.setFixedSize(1000, 700)
        
        # 初始化波浪粒子
        self.wave_particles = []
        self.init_wave_particles()
        
        # 初始化雨滴
        self.rain_drops = []
        self.init_rain_drops()
        
        # 时间计数器
        self.time = 0
        
        # 设置定时器
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_effect)
        self.timer.start(30)
        
        # 震撼效果参数
        self.shake_intensity = 0
        self.shake_decay = 0.9
        self.shake_offset = QPointF(0, 0)
        
        # 涟漪效果
        self.ripples = []
        
    def init_wave_particles(self):
        """初始化波浪粒子"""
        self.wave_particles = []
        particle_count = 200
        
        for i in range(particle_count):
            x = i * (self.width() / particle_count)
            y = self.height() * 0.6
            self.wave_particles.append(WaveParticle(x, y, self.params))
    
    def init_rain_drops(self):
        """初始化雨滴"""
        self.rain_drops = []
        for _ in range(100):
            self.rain_drops.append(RainDrop(self.width(), self.height()))
    
    def update_effect(self):
        """更新效果"""
        # 更新时间
        self.time += 0.05 * self.params.animation_speed
        
        # 更新波浪粒子
        for particle in self.wave_particles:
            particle.update(self.time)
            
        # 更新雨滴
        if self.params.rain_intensity > 0:
            for drop in self.rain_drops:
                drop.update(self.width(), self.height())
                
            # 随机添加新雨滴
            if random.random() < self.params.rain_intensity * 0.1:
                self.rain_drops.append(RainDrop(self.width(), self.height()))
                
            # 限制雨滴数量
            max_drops = int(self.params.rain_intensity * 150)
            if len(self.rain_drops) > max_drops:
                self.rain_drops = self.rain_drops[:max_drops]
        
        # 更新震撼效果
        if self.shake_intensity > 0.1:
            self.shake_offset = QPointF(
                random.uniform(-self.shake_intensity, self.shake_intensity),
                random.uniform(-self.shake_intensity, self.shake_intensity)
            )
            self.shake_intensity *= self.shake_decay
        else:
            self.shake_offset = QPointF(0, 0)
            self.shake_intensity = 0
            
        # 更新涟漪
        for ripple in self.ripples[:]:
            ripple['radius'] += 2
            ripple['alpha'] -= 3
            if ripple['alpha'] <= 0:
                self.ripples.remove(ripple)
                
        self.update()
        
    def add_ripple(self, x, y):
        """添加涟漪效果"""
        self.ripples.append({
            'x': x,
            'y': y,
            'radius': 5,
            'alpha': 255
        })
        
    def trigger_shockwave(self, x=None, y=None):
        """触发震撼波效果"""
        if x is None:
            x = self.width() / 2
        if y is None:
            y = self.height() / 2
            
        self.shake_intensity = 20
        
        # 添加涟漪
        for _ in range(5):
            self.add_ripple(
                x + random.uniform(-50, 50),
                y + random.uniform(-50, 50)
            )
    
    def mousePressEvent(self, event):
        """鼠标点击事件"""
        if event.button() == Qt.LeftButton:
            self.trigger_shockwave(event.x(), event.y())
            
    def paintEvent(self, event):
        """绘制事件"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 应用震撼偏移
        if self.shake_intensity > 0:
            painter.translate(self.shake_offset)
        
        # 绘制天空
        self.draw_sky(painter)
        
        # 绘制海洋
        self.draw_ocean(painter)
        
        # 绘制波浪
        self.draw_waves(painter)
        
        # 绘制光照效果
        self.draw_lighting(painter)
        
        # 绘制雨滴
        if self.params.rain_intensity > 0:
            self.draw_rain(painter)
            
        # 绘制涟漪
        self.draw_ripples(painter)
        
    def draw_sky(self, painter):
        """绘制天空"""
        # 根据天气类型选择天空颜色
        if self.params.weather_type == "晴天":
            gradient = QLinearGradient(0, 0, 0, self.height() * 0.6)
            gradient.setColorAt(0, QColor(135, 206, 235))
            gradient.setColorAt(1, QColor(255, 255, 255))
        elif self.params.weather_type == "多云":
            gradient = QLinearGradient(0, 0, 0, self.height() * 0.6)
            gradient.setColorAt(0, QColor(150, 180, 210))
            gradient.setColorAt(1, QColor(200, 210, 220))
        elif self.params.weather_type == "阴天":
            gradient = QLinearGradient(0, 0, 0, self.height() * 0.6)
            gradient.setColorAt(0, QColor(100, 120, 140))
            gradient.setColorAt(1, QColor(150, 160, 170))
        else:  # 暴风雨
            gradient = QLinearGradient(0, 0, 0, self.height() * 0.6)
            gradient.setColorAt(0, QColor(70, 80, 90))
            gradient.setColorAt(1, QColor(100, 110, 120))
            
        painter.fillRect(0, 0, self.width(), int(self.height() * 0.6), QBrush(gradient))
        
    def draw_ocean(self, painter):
        """绘制海洋背景"""
        # 创建海洋渐变
        water_color = self.params.water_color
        dark_color = QColor(
            max(0, water_color.red() - 50),
            max(0, water_color.green() - 30),
            max(0, water_color.blue() - 20)
        )
        
        light_color = QColor(
            min(255, water_color.red() + 50),
            min(255, water_color.green() + 30),
            min(255, water_color.blue() + 20)
        )
        
        gradient = QLinearGradient(0, self.height() * 0.6, 0, self.height())
        gradient.setColorAt(0, light_color)
        gradient.setColorAt(1, dark_color)
        
        painter.fillRect(0, int(self.height() * 0.6), self.width(), int(self.height() * 0.4), QBrush(gradient))
        
    def draw_waves(self, painter):
        """绘制波浪"""
        # 绘制多层波浪以增加深度感
        
        # 第一层波浪 - 主要波浪
        self.draw_wave_layer(painter, 0, 1.0, 1.0, 0, QColor(255, 255, 255, 150))
        
        # 第二层波浪 - 细节波浪
        self.draw_wave_layer(painter, 0.3, 0.7, 1.5, 0.3, QColor(255, 255, 255, 100))
        
        # 第三层波浪 - 泡沫效果
        self.draw_wave_layer(painter, 0.6, 0.3, 2.0, 0.6, QColor(255, 255, 255, 80))
        
        # 绘制泡沫
        self.draw_foam(painter)
        
    def draw_wave_layer(self, painter, y_offset, amplitude_factor, frequency_factor, phase_offset, color):
        """绘制单层波浪"""
        painter.setPen(QPen(color, 2))
        
        path = QPainterPath()
        path.moveTo(0, self.wave_particles[0].y + y_offset * 10)
        
        for i, particle in enumerate(self.wave_particles):
            if i == 0:
                continue
                
            # 计算控制点以实现平滑曲线
            if i < len(self.wave_particles) - 1:
                x1 = particle.x
                y1 = particle.y + y_offset * 10
                x2 = (particle.x + self.wave_particles[i+1].x) / 2
                y2 = (particle.y + self.wave_particles[i+1].y) / 2 + y_offset * 10
                
                path.cubicTo(x1, y1, x1, y1, x2, y2)
        
        painter.drawPath(path)
        
    def draw_foam(self, painter):
        """绘制泡沫效果"""
        foam_color = QColor(255, 255, 255, int(200 * self.params.foam_intensity))
        painter.setPen(QPen(foam_color, 1))
        painter.setBrush(QBrush(foam_color))
        
        for particle in self.wave_particles:
            if particle.foam_amount > 0.1:
                radius = particle.foam_amount * 3
                alpha = int(255 * particle.foam_amount * self.params.foam_intensity)
                foam_color.setAlpha(alpha)
                painter.setBrush(QBrush(foam_color))
                painter.drawEllipse(QPointF(particle.x, particle.y), radius, radius)
                
    def draw_lighting(self, painter):
        """绘制光照效果"""
        # 绘制反射光
        if self.params.reflection_intensity > 0:
            reflection_color = QColor(255, 255, 255, int(100 * self.params.reflection_intensity))
            painter.setPen(QPen(reflection_color, 1))
            
            # 根据光照方向计算反射位置
            light_angle = math.radians(self.params.light_direction)
            reflection_x = self.width() / 2 + math.cos(light_angle) * self.width() / 3
            reflection_y = self.height() * 0.6 + math.sin(light_angle) * self.height() / 4
            
            # 绘制反射光斑
            gradient = QRadialGradient(reflection_x, reflection_y, 200)
            gradient.setColorAt(0, reflection_color)
            gradient.setColorAt(1, QColor(255, 255, 255, 0))
            
            painter.setBrush(QBrush(gradient))
            painter.drawEllipse(QRectF(reflection_x - 200, reflection_y - 200, 400, 400))
            
        # 绘制焦散效果
        if self.params.caustics_intensity > 0:
            self.draw_caustics(painter)
            
    def draw_caustics(self, painter):
        """绘制焦散效果（水底光斑）"""
        caustics_color = QColor(255, 255, 255, int(50 * self.params.caustics_intensity))
        painter.setPen(QPen(caustics_color, 1))
        painter.setBrush(QBrush(caustics_color))
        
        # 在海底绘制随机光斑
        for _ in range(20):
            x = random.uniform(0, self.width())
            y = random.uniform(self.height() * 0.7, self.height() * 0.9)
            radius = random.uniform(5, 20)
            alpha = int(255 * random.uniform(0.1, 0.3) * self.params.caustics_intensity)
            caustics_color.setAlpha(alpha)
            painter.setBrush(QBrush(caustics_color))
            painter.drawEllipse(QPointF(x, y), radius, radius)
            
    def draw_rain(self, painter):
        """绘制雨滴"""
        rain_color = QColor(200, 200, 255, int(200 * self.params.rain_intensity))
        painter.setPen(QPen(rain_color, 1))
        
        for drop in self.rain_drops:
            painter.drawLine(
                QPointF(drop.x, drop.y),
                QPointF(drop.x, drop.y + drop.length)
            )
            
    def draw_ripples(self, painter):
        """绘制涟漪效果"""
        for ripple in self.ripples:
            ripple_color = QColor(255, 255, 255, ripple['alpha'])
            painter.setPen(QPen(ripple_color, 2))
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(
                QPointF(ripple['x'], ripple['y']),
                ripple['radius'],
                ripple['radius']
            )

class ControlPanel(QWidget):
    """控制面板"""
    
    def __init__(self, params):
        super().__init__()
        self.params = params
        self.init_ui()
        
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout()
        
        # 天气预设
        weather_group = QGroupBox("天气预设")
        weather_layout = QVBoxLayout()
        
        self.weather_combo = QComboBox()
        self.weather_combo.addItems(["晴天", "多云", "阴天", "暴风雨"])
        self.weather_combo.currentTextChanged.connect(self.change_weather)
        weather_layout.addWidget(self.weather_combo)
        
        weather_group.setLayout(weather_layout)
        layout.addWidget(weather_group)
        
        # 波浪参数
        wave_group = QGroupBox("波浪参数")
        wave_layout = QVBoxLayout()
        
        # 波浪振幅
        wave_layout.addWidget(QLabel("波浪振幅:"))
        self.amplitude_slider = QSlider(Qt.Horizontal)
        self.amplitude_slider.setRange(5, 50)
        self.amplitude_slider.setValue(int(self.params.wave_amplitude))
        self.amplitude_slider.valueChanged.connect(self.change_amplitude)
        wave_layout.addWidget(self.amplitude_slider)
        
        # 波浪频率
        wave_layout.addWidget(QLabel("波浪频率:"))
        self.frequency_slider = QSlider(Qt.Horizontal)
        self.frequency_slider.setRange(1, 100)
        self.frequency_slider.setValue(int(self.params.wave_frequency * 1000))
        self.frequency_slider.valueChanged.connect(self.change_frequency)
        wave_layout.addWidget(self.frequency_slider)
        
        # 波浪速度
        wave_layout.addWidget(QLabel("波浪速度:"))
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setRange(1, 100)
        self.speed_slider.setValue(int(self.params.wave_speed * 1000))
        self.speed_slider.valueChanged.connect(self.change_speed)
        wave_layout.addWidget(self.speed_slider)
        
        wave_group.setLayout(wave_layout)
        layout.addWidget(wave_group)
        
        # 风力参数
        wind_group = QGroupBox("风力参数")
        wind_layout = QVBoxLayout()
        
        # 风速
        wind_layout.addWidget(QLabel("风速:"))
        self.wind_slider = QSlider(Qt.Horizontal)
        self.wind_slider.setRange(0, 20)
        self.wind_slider.setValue(int(self.params.wind_speed))
        self.wind_slider.valueChanged.connect(self.change_wind_speed)
        wind_layout.addWidget(self.wind_slider)
        
        # 风向
        wind_layout.addWidget(QLabel("风向:"))
        self.direction_slider = QSlider(Qt.Horizontal)
        self.direction_slider.setRange(0, 360)
        self.direction_slider.setValue(int(self.params.wind_direction))
        self.direction_slider.valueChanged.connect(self.change_wind_direction)
        wind_layout.addWidget(self.direction_slider)
        
        wind_group.setLayout(wind_layout)
        layout.addWidget(wind_group)
        
        # 光照参数
        light_group = QGroupBox("光照参数")
        light_layout = QVBoxLayout()
        
        # 光照强度
        light_layout.addWidget(QLabel("光照强度:"))
        self.light_slider = QSlider(Qt.Horizontal)
        self.light_slider.setRange(0, 100)
        self.light_slider.setValue(int(self.params.light_intensity * 100))
        self.light_slider.valueChanged.connect(self.change_light_intensity)
        light_layout.addWidget(self.light_slider)
        
        # 光照方向
        light_layout.addWidget(QLabel("光照方向:"))
        self.light_direction_slider = QSlider(Qt.Horizontal)
        self.light_direction_slider.setRange(0, 360)
        self.light_direction_slider.setValue(int(self.params.light_direction))
        self.light_direction_slider.valueChanged.connect(self.change_light_direction)
        light_layout.addWidget(self.light_direction_slider)
        
        light_group.setLayout(light_layout)
        layout.addWidget(light_group)
        
        # 高级效果
        advanced_group = QGroupBox("高级效果")
        advanced_layout = QVBoxLayout()
        
        # 反射强度
        advanced_layout.addWidget(QLabel("反射强度:"))
        self.reflection_slider = QSlider(Qt.Horizontal)
        self.reflection_slider.setRange(0, 100)
        self.reflection_slider.setValue(int(self.params.reflection_intensity * 100))
        self.reflection_slider.valueChanged.connect(self.change_reflection)
        advanced_layout.addWidget(self.reflection_slider)
        
        # 焦散强度
        advanced_layout.addWidget(QLabel("焦散强度:"))
        self.caustics_slider = QSlider(Qt.Horizontal)
        self.caustics_slider.setRange(0, 100)
        self.caustics_slider.setValue(int(self.params.caustics_intensity * 100))
        self.caustics_slider.valueChanged.connect(self.change_caustics)
        advanced_layout.addWidget(self.caustics_slider)
        
        # 泡沫强度
        advanced_layout.addWidget(QLabel("泡沫强度:"))
        self.foam_slider = QSlider(Qt.Horizontal)
        self.foam_slider.setRange(0, 100)
        self.foam_slider.setValue(int(self.params.foam_intensity * 100))
        self.foam_slider.valueChanged.connect(self.change_foam)
        advanced_layout.addWidget(self.foam_slider)
        
        advanced_group.setLayout(advanced_layout)
        layout.addWidget(advanced_group)
        
        # 动画速度
        speed_group = QGroupBox("动画速度")
        speed_layout = QVBoxLayout()
        
        self.speed_spin = QDoubleSpinBox()
        self.speed_spin.setRange(0.1, 3.0)
        self.speed_spin.setSingleStep(0.1)
        self.speed_spin.setValue(self.params.animation_speed)
        self.speed_spin.valueChanged.connect(self.change_animation_speed)
        speed_layout.addWidget(self.speed_spin)
        
        speed_group.setLayout(speed_layout)
        layout.addWidget(speed_group)
        
        # 震撼波按钮
        self.shockwave_btn = QPushButton("触发震撼波")
        self.shockwave_btn.clicked.connect(self.trigger_shockwave)
        layout.addWidget(self.shockwave_btn)
        
        layout.addStretch()
        self.setLayout(layout)
        
    def change_weather(self, weather_type):
        """改变天气"""
        self.params.apply_weather_preset(weather_type)
        self.update_sliders()
        
    def change_amplitude(self, value):
        """改变波浪振幅"""
        self.params.wave_amplitude = value
        
    def change_frequency(self, value):
        """改变波浪频率"""
        self.params.wave_frequency = value / 1000.0
        
    def change_speed(self, value):
        """改变波浪速度"""
        self.params.wave_speed = value / 1000.0
        
    def change_wind_speed(self, value):
        """改变风速"""
        self.params.wind_speed = value
        
    def change_wind_direction(self, value):
        """改变风向"""
        self.params.wind_direction = value
        
    def change_light_intensity(self, value):
        """改变光照强度"""
        self.params.light_intensity = value / 100.0
        
    def change_light_direction(self, value):
        """改变光照方向"""
        self.params.light_direction = value
        
    def change_reflection(self, value):
        """改变反射强度"""
        self.params.reflection_intensity = value / 100.0
        
    def change_caustics(self, value):
        """改变焦散强度"""
        self.params.caustics_intensity = value / 100.0
        
    def change_foam(self, value):
        """改变泡沫强度"""
        self.params.foam_intensity = value / 100.0
        
    def change_animation_speed(self, value):
        """改变动画速度"""
        self.params.animation_speed = value
        
    def trigger_shockwave(self):
        """触发震撼波"""
        # 这个信号会被主窗口捕获
        pass
        
    def update_sliders(self):
        """更新滑块位置"""
        self.amplitude_slider.setValue(int(self.params.wave_amplitude))
        self.frequency_slider.setValue(int(self.params.wave_frequency * 1000))
        self.speed_slider.setValue(int(self.params.wave_speed * 1000))
        self.wind_slider.setValue(int(self.params.wind_speed))
        self.direction_slider.setValue(int(self.params.wind_direction))
        self.light_slider.setValue(int(self.params.light_intensity * 100))
        self.light_direction_slider.setValue(int(self.params.light_direction))
        self.reflection_slider.setValue(int(self.params.reflection_intensity * 100))
        self.caustics_slider.setValue(int(self.params.caustics_intensity * 100))
        self.foam_slider.setValue(int(self.params.foam_intensity * 100))
        self.speed_spin.setValue(self.params.animation_speed)

class MainWindow(QMainWindow):
    """主窗口"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("玻璃海效果模拟系统")
        
        # 初始化参数
        self.params = OceanParameters()
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建布局
        layout = QHBoxLayout()
        central_widget.setLayout(layout)
        
        # 创建海洋效果部件
        self.ocean_widget = GlassOceanWidget(self.params)
        layout.addWidget(self.ocean_widget, 4)
        
        # 创建控制面板
        self.control_panel = ControlPanel(self.params)
        layout.addWidget(self.control_panel, 1)
        
        # 连接信号
        self.control_panel.shockwave_btn.clicked.connect(self.ocean_widget.trigger_shockwave)
        
    def resizeEvent(self, event):
        """窗口大小改变事件"""
        # 当窗口大小改变时，重新初始化波浪粒子
        self.ocean_widget.init_wave_particles()
        super().resizeEvent(event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())