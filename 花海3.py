import sys
import random
import math
import numpy as np
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QSlider, QLabel, QCheckBox, QComboBox,
                             QGroupBox, QPushButton, QSpinBox, QDoubleSpinBox,
                             QTabWidget, QProgressBar, QSplitter, QFrame)
from PyQt5.QtCore import Qt, QTimer, QPointF, QRectF, QPropertyAnimation, pyqtProperty, QEasingCurve
from PyQt5.QtGui import (QPainter, QBrush, QColor, QRadialGradient, QPen, QFont, 
                         QLinearGradient, QPainterPath, QImage, QPixmap, QFontMetrics,
                         QConicalGradient)

class RealisticFlower:
    """真实花朵类 - 模拟植物生长和生物特性"""
    def __init__(self, width, height, environment):
        self.environment = environment
        self.width = width
        self.height = height
        
        # 位置和物理属性
        self.x = random.uniform(50, width - 50)
        self.y = random.uniform(50, height - 50)
        self.z = random.uniform(0.2, 1.0)  # 深度
        self.angle = random.uniform(0, 2 * math.pi)  # 添加这一行 - 花朵的初始角度
        
        # 生长阶段 (0-1)
        self.growth_stage = random.uniform(0, 1)  # 初始随机生长阶段
        self.growth_rate = random.uniform(0.001, 0.003)
        self.health = 1.0
        self.age = 0
        
        # 植物结构
        self.stem_height = random.uniform(30, 80) * self.z
        self.stem_thickness = random.uniform(2, 5) * self.z
        self.leaf_count = random.randint(2, 5)
        self.leaf_size = random.uniform(10, 25) * self.z
        
        # 花朵属性
        self.petal_count = random.randint(5, 8)
        self.petal_size = random.uniform(8, 20) * self.z
        self.flower_size = self.petal_size * 2
        self.bloom_level = 0.0  # 开花程度 (0-1)
        
        # 颜色和外观
        self.species = random.choice(["rose", "tulip", "daisy", "lily", "orchid"])
        self.base_color = self.get_species_color()
        self.variation_color = self.get_color_variation()
        
        # 物理属性
        self.velocity = QPointF(0, 0)
        self.angular_velocity = random.uniform(-0.01, 0.01)
        self.stem_flexibility = random.uniform(0.1, 0.3)
        
        # 环境响应
        self.water_level = random.uniform(0.5, 1.0)
        self.nutrient_level = random.uniform(0.5, 1.0)
        self.sunlight_exposure = 1.0
        
        # 动画状态
        self.wind_sway_phase = random.uniform(0, 2 * math.pi)
        self.growth_animation = 0.0
        
    def get_species_color(self):
        """根据物种获取基础颜色"""
        colors = {
            "rose": [(200, 20, 60), (255, 105, 180), (199, 21, 133)],
            "tulip": [(255, 0, 0), (255, 140, 0), (255, 215, 0)],
            "daisy": [(255, 255, 255), (255, 250, 205), (240, 230, 140)],
            "lily": [(255, 255, 255), (255, 240, 245), (230, 230, 250)],
            "orchid": [(186, 85, 211), (138, 43, 226), (147, 112, 219)]
        }
        return random.choice(colors[self.species])
    
    def get_color_variation(self):
        """获取颜色变异"""
        return (
            random.randint(-10, 10),
            random.randint(-10, 10),
            random.randint(-10, 10)
        )
    
    def update(self, delta_time, environment):
        """更新花朵状态 - 模拟生长和环境影响"""
        self.age += delta_time
        
        # 环境因素影响
        self.sunlight_exposure = environment.get_sunlight_at(self.x, self.y)
        temperature_factor = environment.get_temperature_factor()
        humidity_factor = environment.get_humidity_factor()
        
        # 计算生长速率（受环境影响）
        effective_growth_rate = self.growth_rate
        effective_growth_rate *= self.sunlight_exposure
        effective_growth_rate *= temperature_factor
        effective_growth_rate *= humidity_factor
        effective_growth_rate *= self.water_level
        effective_growth_rate *= self.nutrient_level
        
        # 更新生长阶段
        if self.growth_stage < 1.0:
            self.growth_stage = min(1.0, self.growth_stage + effective_growth_rate)
            
            # 生长动画
            self.growth_animation = math.sin(self.age * 2) * 0.1 + 0.9
            
            # 当生长到一定阶段开始开花
            if self.growth_stage > 0.7 and self.bloom_level < 1.0:
                self.bloom_level = min(1.0, self.bloom_level + effective_growth_rate * 2)
        
        # 物理模拟 - 风的影响
        wind_strength = environment.wind_strength
        wind_direction = environment.wind_direction
        
        # 茎干摇摆
        sway_frequency = 0.5 + wind_strength * 0.5
        sway_magnitude = wind_strength * self.stem_flexibility * 10
        
        self.wind_sway_phase += sway_frequency * delta_time
        sway_offset = math.sin(self.wind_sway_phase) * sway_magnitude
        
        # 应用风力
        wind_force_x = math.cos(wind_direction) * wind_strength * 0.1
        wind_force_y = math.sin(wind_direction) * wind_strength * 0.1
        
        self.velocity.setX(self.velocity.x() * 0.95 + wind_force_x)
        self.velocity.setY(self.velocity.y() * 0.95 + wind_force_y)
        
        # 更新位置（限制移动范围）
        new_x = self.x + self.velocity.x() + sway_offset
        new_y = self.y + self.velocity.y()
        
        # 边界检查
        if 0 <= new_x <= self.width:
            self.x = new_x
        if 0 <= new_y <= self.height:
            self.y = new_y
            
        # 健康度衰减（如果没有足够资源）
        health_decay = 0.0001
        if self.sunlight_exposure < 0.3:
            health_decay += 0.001
        if self.water_level < 0.3:
            health_decay += 0.001
            
        self.health = max(0, self.health - health_decay)
        
        # 如果健康度过低，开始凋谢
        if self.health < 0.3 and self.bloom_level > 0:
            self.bloom_level = max(0, self.bloom_level - 0.005)
            
        return self.health > 0
    
    def get_current_color(self):
        """获取当前颜色（考虑生长阶段和健康度）"""
        r, g, b = self.base_color
        
        # 生长阶段影响（幼苗更绿）
        if self.growth_stage < 0.5:
            green_factor = 1.0 - self.growth_stage * 2
            r = int(r * (1 - green_factor * 0.5) + 100 * green_factor)
            g = int(g * (1 - green_factor * 0.3) + 200 * green_factor)
            b = int(b * (1 - green_factor * 0.7) + 100 * green_factor)
        
        # 健康度影响
        r = int(r * self.health)
        g = int(g * self.health)
        b = int(b * self.health)
        
        # 添加颜色变异
        r = min(255, max(0, r + self.variation_color[0]))
        g = min(255, max(0, g + self.variation_color[1]))
        b = min(255, max(0, b + self.variation_color[2]))
        
        return (r, g, b)

class Environment:
    """环境模拟类 - 控制天气、季节和物理环境"""
    def __init__(self, width, height):
        self.width = width
        self.height = height
        
        # 时间系统
        self.time_of_day = 0.5  # 0-1 (0=午夜, 0.5=正午)
        self.day_night_cycle_speed = 0.001
        self.season = 0.0  # 0-1 (0=春, 0.25=夏, 0.5=秋, 0.75=冬)
        self.season_cycle_speed = 0.0001
        
        # 天气系统
        self.weather_type = "sunny"  # sunny, cloudy, rainy, stormy
        self.weather_transition = 0.0
        self.target_weather = "sunny"
        
        # 物理环境
        self.temperature = 20.0  # 摄氏度
        self.humidity = 0.5  # 0-1
        self.wind_strength = 0.0  # 0-1
        self.wind_direction = random.uniform(0, 2 * math.pi)
        self.wind_change_timer = 0
        
        # 光照系统
        self.sun_position = 0.0
        self.ambient_light = 1.0
        self.sun_color = (255, 255, 200)
        self.sky_color = (135, 206, 235)
        
        # 地形
        self.generate_terrain()
        
    def generate_terrain(self):
        """生成简单地形高度图"""
        size = 100
        self.terrain = np.random.rand(size, size) * 0.5
        # 平滑地形
        from scipy.ndimage import gaussian_filter
        self.terrain = gaussian_filter(self.terrain, sigma=2)
        
    def update(self, delta_time):
        """更新环境状态"""
        # 更新时间
        self.time_of_day = (self.time_of_day + self.day_night_cycle_speed * delta_time) % 1.0
        self.season = (self.season + self.season_cycle_speed * delta_time) % 1.0
        
        # 更新太阳位置
        self.sun_position = self.time_of_day
        
        # 计算环境光照
        self.calculate_lighting()
        
        # 更新温度（基于时间和季节）
        self.update_temperature()
        
        # 更新天气
        self.update_weather(delta_time)
        
        # 更新风力
        self.update_wind(delta_time)
        
    def calculate_lighting(self):
        """计算光照条件"""
        # 基于时间计算光照强度
        if 0.25 <= self.time_of_day <= 0.75:  # 白天
            sun_height = 1.0 - abs(self.time_of_day - 0.5) * 4  # 正午最高
            self.ambient_light = 0.3 + 0.7 * sun_height
        else:  # 夜晚
            self.ambient_light = 0.1
            
        # 天气影响
        if self.weather_type == "cloudy":
            self.ambient_light *= 0.7
        elif self.weather_type == "rainy":
            self.ambient_light *= 0.5
        elif self.weather_type == "stormy":
            self.ambient_light *= 0.3
            
        # 季节影响（冬季光照较弱）
        season_factor = 1.0 - abs(self.season - 0.75) * 0.5  # 冬季最弱
        self.ambient_light *= season_factor
        
    def update_temperature(self):
        """更新温度"""
        # 基于时间和季节的基础温度
        base_temp = 15 + 10 * math.sin(self.season * 2 * math.pi)  # 季节变化
        
        # 日变化
        day_temp_variation = 10 * math.sin(self.time_of_day * 2 * math.pi)
        
        # 天气影响
        if self.weather_type == "sunny":
            weather_effect = 5
        elif self.weather_type == "cloudy":
            weather_effect = -2
        elif self.weather_type == "rainy":
            weather_effect = -5
        elif self.weather_type == "stormy":
            weather_effect = -8
        else:
            weather_effect = 0
            
        self.temperature = base_temp + day_temp_variation + weather_effect
        
    def update_weather(self, delta_time):
        """更新天气状态"""
        # 随机改变天气
        if random.random() < 0.001:
            self.target_weather = random.choice(["sunny", "cloudy", "rainy", "stormy"])
            
        # 平滑过渡
        if self.weather_type != self.target_weather:
            self.weather_transition += 0.01
            if self.weather_transition >= 1.0:
                self.weather_type = self.target_weather
                self.weather_transition = 0.0
                
        # 根据天气设置湿度
        if self.weather_type == "rainy" or self.weather_type == "stormy":
            self.humidity = min(1.0, self.humidity + 0.01)
        else:
            self.humidity = max(0.3, self.humidity - 0.005)
            
    def update_wind(self, delta_time):
        """更新风力"""
        self.wind_change_timer -= delta_time
        if self.wind_change_timer <= 0:
            # 随机改变风力
            target_strength = random.uniform(0, 1)
            if self.weather_type == "stormy":
                target_strength = random.uniform(0.5, 1.0)
            elif self.weather_type == "rainy":
                target_strength = random.uniform(0.2, 0.6)
            else:
                target_strength = random.uniform(0, 0.3)
                
            # 平滑过渡
            self.wind_strength = self.wind_strength * 0.9 + target_strength * 0.1
            
            # 随机改变风向
            self.wind_direction = (self.wind_direction + random.uniform(-0.5, 0.5)) % (2 * math.pi)
            
            self.wind_change_timer = random.uniform(100, 300)
            
    def get_sunlight_at(self, x, y):
        """获取指定位置的光照强度"""
        base_light = self.ambient_light
        
        # 简单地形阴影
        terrain_x = int(x / self.width * 99)
        terrain_y = int(y / self.height * 99)
        terrain_factor = 1.0 - self.terrain[terrain_x, terrain_y] * 0.3
        
        return base_light * terrain_factor
    
    def get_temperature_factor(self):
        """获取温度因子（影响植物生长）"""
        # 植物最适温度 15-25°C
        optimal_temp = 20
        temp_diff = abs(self.temperature - optimal_temp)
        return max(0, 1.0 - temp_diff / 30)
    
    def get_humidity_factor(self):
        """获取湿度因子（影响植物生长）"""
        # 植物最适湿度 0.4-0.7
        if 0.4 <= self.humidity <= 0.7:
            return 1.0
        else:
            return 1.0 - abs(self.humidity - 0.55) / 0.45

class UltraRealisticFlowerField(QWidget):
    """超真实花海效果主窗口"""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("超真实花海生态系统模拟")
        self.setGeometry(50, 50, 1600, 1000)
        
        # 初始化参数
        self.flower_count = 300
        self.max_flowers = 1000
        
        # 创建环境
        self.environment = Environment(self.width(), self.height())
        
        # 初始化花朵
        self.flowers = []
        self.generate_flowers(self.flower_count)
        
        # 时间控制
        self.simulation_speed = 1.0
        self.last_time = 0
        self.frame_count = 0
        self.fps = 60
        
        # 视觉效果
        self.show_shadows = True
        self.show_terrain = False
        self.show_debug_info = False
        self.bloom_effect = True
        self.depth_of_field = True
        
        # 交互状态
        self.mouse_x = -1000
        self.mouse_y = -1000
        self.mouse_pressed = False
        self.selected_flower = None
        
        # 设置定时器
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_simulation)
        self.timer.start(16)  # 约60FPS
        
        # 初始化背景
        self.set_background()
        
    def set_background(self):
        """设置动态背景"""
        self.background = QImage(self.size(), QImage.Format_RGB32)
        self.update_background()
        
    def update_background(self):
        """更新背景（基于环境）"""
        painter = QPainter(self.background)
        
        # 基于时间和天气的天空颜色
        env = self.environment
        
        # 基础天空色
        if env.time_of_day < 0.25 or env.time_of_day > 0.75:  # 夜晚
            base_sky = QColor(10, 15, 40)
        elif env.time_of_day < 0.5:  # 早晨
            morning_factor = (env.time_of_day - 0.25) * 4
            base_sky = QColor(
                135 + int(120 * morning_factor),
                206 - int(50 * morning_factor),
                235 - int(135 * morning_factor)
            )
        else:  # 傍晚
            evening_factor = (0.75 - env.time_of_day) * 4
            base_sky = QColor(
                255 - int(120 * (1 - evening_factor)),
                165 - int(60 * (1 - evening_factor)),
                0 + int(235 * evening_factor)
            )
            
        # 天气影响
        if env.weather_type == "cloudy":
            base_sky = base_sky.darker(130)
        elif env.weather_type == "rainy":
            base_sky = base_sky.darker(150)
        elif env.weather_type == "stormy":
            base_sky = base_sky.darker(180)
            
        # 创建渐变背景
        gradient = QLinearGradient(0, 0, 0, self.height())
        
        # 天空渐变
        sky_top = base_sky.lighter(120)
        sky_bottom = base_sky.darker(120)
        
        gradient.setColorAt(0, sky_top)
        gradient.setColorAt(1, sky_bottom)
        
        painter.fillRect(self.rect(), QBrush(gradient))
        
        # 绘制太阳/月亮
        celestial_x = env.time_of_day * self.width()
        celestial_y = self.height() * 0.2 + math.sin(env.time_of_day * 2 * math.pi) * 50
        
        if 0.25 <= env.time_of_day <= 0.75:  # 白天 - 太阳
            sun_color = QColor(255, 255, 200)
            if env.weather_type != "sunny":
                sun_color = sun_color.darker(150)
                
            painter.setBrush(QBrush(sun_color))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(QPointF(celestial_x, celestial_y), 30, 30)
        else:  # 夜晚 - 月亮
            moon_color = QColor(200, 200, 220)
            painter.setBrush(QBrush(moon_color))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(QPointF(celestial_x, celestial_y), 25, 25)
            
        painter.end()
        
    def generate_flowers(self, count):
        """生成指定数量的花朵"""
        for _ in range(count):
            if len(self.flowers) < self.max_flowers:
                flower = RealisticFlower(self.width(), self.height(), self.environment)
                self.flowers.append(flower)
    
    def update_simulation(self):
        """更新整个模拟"""
        current_time = self.frame_count
        delta_time = 1.0 * self.simulation_speed
        
        # 更新环境
        self.environment.update(delta_time)
        
        # 更新背景
        if self.frame_count % 10 == 0:  # 每10帧更新一次背景
            self.update_background()
        
        # 更新所有花朵
        self.flowers = [flower for flower in self.flowers if flower.update(delta_time, self.environment)]
        
        # 自然繁殖 - 添加空列表检查
        if self.flowers and random.random() < 0.01 and len(self.flowers) < self.max_flowers:
            parent = random.choice(self.flowers)
            if parent.growth_stage > 0.8 and parent.health > 0.7:
                child = RealisticFlower(self.width(), self.height(), self.environment)
                child.x = parent.x + random.uniform(-50, 50)
                child.y = parent.y + random.uniform(-50, 50)
                child.base_color = parent.base_color
                self.flowers.append(child)
        
        self.frame_count += 1
        
        # 触发重绘
        self.update()
    
    def paintEvent(self, event):
        """绘制花海"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 绘制背景
        painter.drawImage(0, 0, self.background)
        
        # 绘制地形（如果启用）
        if self.show_terrain:
            self.draw_terrain(painter)
        
        # 绘制所有花朵（按深度排序）
        sorted_flowers = sorted(self.flowers, key=lambda f: f.z)
        for flower in sorted_flowers:
            self.draw_realistic_flower(painter, flower)
        
        # 绘制UI
        self.draw_ui(painter)
        
        # 绘制调试信息（如果启用）
        if self.show_debug_info:
            self.draw_debug_info(painter)
    
    def draw_terrain(self, painter):
        """绘制地形（简化版）"""
        env = self.environment
        cell_width = self.width() / 100
        cell_height = self.height() / 100
        
        for x in range(100):
            for y in range(100):
                height = env.terrain[x, y]
                terrain_color = QColor(50 + int(height * 100), 100 + int(height * 80), 50)
                painter.fillRect(
                    x * cell_width, y * cell_height,
                    cell_width, cell_height,
                    terrain_color
                )
    
    def draw_realistic_flower(self, painter, flower):
        """绘制真实花朵"""
        if flower.health <= 0:
            return
            
        # 计算全局光照影响
        env = self.environment
        global_light = env.ambient_light
        
        # 绘制茎干
        self.draw_stem(painter, flower, global_light)
        
        # 绘制叶子
        self.draw_leaves(painter, flower, global_light)
        
        # 绘制花朵
        if flower.bloom_level > 0:
            self.draw_bloom(painter, flower, global_light)
    
    def draw_stem(self, painter, flower, global_light):
        """绘制茎干"""
        stem_color = QColor(50, 120, 50)
        
        # 生长阶段影响
        stem_height = flower.stem_height * flower.growth_stage * flower.growth_animation
        stem_thickness = flower.stem_thickness * flower.growth_stage
        
        # 健康度影响
        stem_color = stem_color.darker(int(200 * (1 - flower.health)))
        
        # 光照影响
        stem_color = stem_color.lighter(int(100 + global_light * 100))
        
        # 绘制茎干
        painter.setBrush(QBrush(stem_color))
        painter.setPen(QPen(stem_color.darker(150), 1))
        
        # 茎干摇摆
        sway_x = math.sin(flower.wind_sway_phase) * flower.stem_flexibility * 20 * flower.growth_stage
        
        stem_path = QPainterPath()
        stem_path.moveTo(flower.x, flower.y)
        stem_path.cubicTo(
            flower.x + sway_x * 0.3, flower.y - stem_height * 0.3,
            flower.x + sway_x * 0.7, flower.y - stem_height * 0.7,
            flower.x + sway_x, flower.y - stem_height
        )
        
        painter.drawPath(stem_path)
        
        # 保存花朵顶部位置
        flower.flower_x = flower.x + sway_x
        flower.flower_y = flower.y - stem_height
    
    def draw_leaves(self, painter, flower, global_light):
        """绘制叶子"""
        leaf_color = QColor(60, 180, 60)
        leaf_color = leaf_color.darker(int(200 * (1 - flower.health)))
        leaf_color = leaf_color.lighter(int(100 + global_light * 100))
        
        stem_height = flower.stem_height * flower.growth_stage
        
        for i in range(flower.leaf_count):
            # 叶子位置沿茎干分布
            leaf_height = stem_height * (0.2 + 0.6 * i / max(1, flower.leaf_count - 1))
            
            # 叶子角度
            angle = math.pi * 0.3 + (i % 2) * math.pi * 0.4
            
            # 叶子大小
            leaf_size = flower.leaf_size * flower.growth_stage
            
            # 绘制叶子
            painter.save()
            painter.translate(flower.x, flower.y - leaf_height)
            painter.rotate(math.degrees(angle))
            
            leaf_path = QPainterPath()
            leaf_path.moveTo(0, 0)
            leaf_path.cubicTo(
                leaf_size * 0.5, -leaf_size * 0.2,
                leaf_size * 0.8, leaf_size * 0.3,
                0, leaf_size
            )
            leaf_path.cubicTo(
                -leaf_size * 0.8, leaf_size * 0.3,
                -leaf_size * 0.5, -leaf_size * 0.2,
                0, 0
            )
            
            painter.setBrush(QBrush(leaf_color))
            painter.setPen(QPen(leaf_color.darker(150), 1))
            painter.drawPath(leaf_path)
            
            painter.restore()
    
    def draw_bloom(self, painter, flower, global_light):
        """绘制花朵"""
        if not hasattr(flower, 'flower_x'):
            return
            
        flower_color = flower.get_current_color()
        qflower_color = QColor(*flower_color)
        
        # 光照影响
        qflower_color = qflower_color.lighter(int(100 + global_light * 100))
        
        # 开花程度影响大小
        bloom_size = flower.flower_size * flower.bloom_level
        
        # 绘制花瓣
        for i in range(flower.petal_count):
            angle = flower.angle + i * (2 * math.pi / flower.petal_count)
            
            # 花瓣位置
            petal_x = flower.flower_x + math.cos(angle) * bloom_size * 0.6
            petal_y = flower.flower_y + math.sin(angle) * bloom_size * 0.6
            
            # 花瓣大小
            petal_width = bloom_size * 0.8
            petal_height = bloom_size * 0.5
            
            # 绘制花瓣
            painter.save()
            painter.translate(petal_x, petal_y)
            painter.rotate(math.degrees(angle))
            
            # 花瓣形状根据物种变化
            if flower.species == "rose":
                self.draw_rose_petal(painter, petal_width, petal_height, qflower_color)
            elif flower.species == "tulip":
                self.draw_tulip_petal(painter, petal_width, petal_height, qflower_color)
            elif flower.species == "daisy":
                self.draw_daisy_petal(painter, petal_width, petal_height, qflower_color)
            elif flower.species == "lily":
                self.draw_lily_petal(painter, petal_width, petal_height, qflower_color)
            elif flower.species == "orchid":
                self.draw_orchid_petal(painter, petal_width, petal_height, qflower_color)
            
            painter.restore()
        
        # 绘制花蕊
        if flower.bloom_level > 0.5:
            stamen_color = QColor(255, 255, 0)
            stamen_color = stamen_color.lighter(int(100 + global_light * 100))
            
            painter.setBrush(QBrush(stamen_color))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(QPointF(flower.flower_x, flower.flower_y), 
                               bloom_size * 0.15, bloom_size * 0.15)
    
    def draw_rose_petal(self, painter, width, height, color):
        """绘制玫瑰花瓣"""
        path = QPainterPath()
        path.moveTo(0, -height/2)
        
        # 玫瑰花瓣有复杂的曲线
        path.cubicTo(width/3, -height/3, width/2, -height/6, width/2, height/6)
        path.cubicTo(width/2, height/3, width/4, height/2, 0, height/2)
        path.cubicTo(-width/4, height/2, -width/2, height/3, -width/2, height/6)
        path.cubicTo(-width/2, -height/6, -width/3, -height/3, 0, -height/2)
        
        gradient = QRadialGradient(0, 0, width/2)
        gradient.setColorAt(0, color.lighter(150))
        gradient.setColorAt(1, color.darker(150))
        
        painter.setBrush(QBrush(gradient))
        painter.setPen(QPen(color.darker(200), 1))
        painter.drawPath(path)
    
    def draw_tulip_petal(self, painter, width, height, color):
        """绘制郁金香花瓣"""
        path = QPainterPath()
        path.moveTo(0, -height/2)
        path.cubicTo(width/2, -height/3, width/2, height/3, 0, height/2)
        path.cubicTo(-width/2, height/3, -width/2, -height/3, 0, -height/2)
        
        gradient = QLinearGradient(0, -height/2, 0, height/2)
        gradient.setColorAt(0, color.lighter(150))
        gradient.setColorAt(1, color.darker(120))
        
        painter.setBrush(QBrush(gradient))
        painter.setPen(QPen(color.darker(200), 1))
        painter.drawPath(path)
    
    def draw_daisy_petal(self, painter, width, height, color):
        """绘制雏菊花瓣"""
        path = QPainterPath()
        path.moveTo(0, 0)
        path.cubicTo(width/3, -height/3, width/2, -height/2, 0, -height)
        path.cubicTo(-width/2, -height/2, -width/3, -height/3, 0, 0)
        
        painter.setBrush(QBrush(color))
        painter.setPen(QPen(color.darker(150), 1))
        painter.drawPath(path)
    
    def draw_lily_petal(self, painter, width, height, color):
        """绘制百合花瓣"""
        path = QPainterPath()
        path.moveTo(0, -height/2)
        path.cubicTo(width/3, -height/4, width/2, 0, 0, height/2)
        path.cubicTo(-width/2, 0, -width/3, -height/4, 0, -height/2)
        
        gradient = QRadialGradient(0, 0, width)
        gradient.setColorAt(0, color.lighter(180))
        gradient.setColorAt(1, color)
        
        painter.setBrush(QBrush(gradient))
        painter.setPen(QPen(color.darker(150), 1))
        painter.drawPath(path)
    
    def draw_orchid_petal(self, painter, width, height, color):
        """绘制兰花瓣"""
        path = QPainterPath()
        path.moveTo(0, -height/3)
        path.cubicTo(width/2, -height/2, width/2, height/4, 0, height/2)
        path.cubicTo(-width/2, height/4, -width/2, -height/2, 0, -height/3)
        
        # 兰花有斑点
        painter.setBrush(QBrush(color))
        painter.setPen(QPen(color.darker(150), 1))
        painter.drawPath(path)
        
        # 绘制斑点
        spot_color = color.darker(120)
        painter.setBrush(QBrush(spot_color))
        for _ in range(3):
            spot_x = random.uniform(-width/3, width/3)
            spot_y = random.uniform(-height/4, height/4)
            spot_size = random.uniform(2, 5)
            painter.drawEllipse(QPointF(spot_x, spot_y), spot_size, spot_size)
    
    def draw_ui(self, painter):
        """绘制UI信息"""
        # 绘制标题
        painter.setPen(QColor(255, 255, 255))
        font = QFont("Arial", 24, QFont.Bold)
        painter.setFont(font)
        painter.drawText(self.rect(), Qt.AlignTop | Qt.AlignHCenter, "超真实花海生态系统模拟")
        
        # 绘制环境信息
        env = self.environment
        time_str = f"时间: {self.get_time_string(env.time_of_day)}"
        season_str = f"季节: {self.get_season_string(env.season)}"
        weather_str = f"天气: {self.get_weather_string(env.weather_type)}"
        temp_str = f"温度: {env.temperature:.1f}°C"
        
        info_text = f"{time_str} | {season_str} | {weather_str} | {temp_str}"
        
        font = QFont("Arial", 12)
        painter.setFont(font)
        painter.drawText(10, 30, info_text)
        
        # 绘制统计信息
        stats_text = f"花朵数量: {len(self.flowers)} | 健康花朵: {sum(1 for f in self.flowers if f.health > 0.7)}"
        painter.drawText(10, 50, stats_text)
        
        # 绘制说明
        help_text = "鼠标悬停: 查看花朵信息 | 点击: 选择花朵 | 空格: 添加花朵 | R: 重置"
        painter.drawText(self.rect(), Qt.AlignBottom | Qt.AlignHCenter, help_text)
    
    def draw_debug_info(self, painter):
        """绘制调试信息"""
        painter.setPen(QColor(255, 255, 255))
        font = QFont("Arial", 10)
        painter.setFont(font)
        
        env = self.environment
        debug_lines = [
            f"帧率: {self.fps:.1f} FPS",
            f"环境光: {env.ambient_light:.2f}",
            f"湿度: {env.humidity:.2f}",
            f"风力: {env.wind_strength:.2f}",
            f"风向: {math.degrees(env.wind_direction):.1f}°"
        ]
        
        for i, line in enumerate(debug_lines):
            painter.drawText(10, 80 + i * 20, line)
    
    def get_time_string(self, time_of_day):
        """获取时间字符串"""
        hours = int(time_of_day * 24)
        minutes = int((time_of_day * 24 - hours) * 60)
        return f"{hours:02d}:{minutes:02d}"
    
    def get_season_string(self, season):
        """获取季节字符串"""
        if season < 0.25:
            return "春"
        elif season < 0.5:
            return "夏"
        elif season < 0.75:
            return "秋"
        else:
            return "冬"
    
    def get_weather_string(self, weather_type):
        """获取天气字符串"""
        weather_names = {
            "sunny": "晴朗",
            "cloudy": "多云", 
            "rainy": "雨天",
            "stormy": "暴风雨"
        }
        return weather_names.get(weather_type, weather_type)
    
    def mouseMoveEvent(self, event):
        """鼠标移动事件"""
        self.mouse_x = event.x()
        self.mouse_y = event.y()
        
        # 检查是否悬停在花朵上
        self.selected_flower = None
        for flower in self.flowers:
            if hasattr(flower, 'flower_x') and hasattr(flower, 'flower_y'):
                distance = math.sqrt((flower.flower_x - self.mouse_x)**2 + 
                                   (flower.flower_y - self.mouse_y)**2)
                if distance < flower.flower_size:
                    self.selected_flower = flower
                    break
    
    def mousePressEvent(self, event):
        """鼠标点击事件"""
        if event.button() == Qt.LeftButton and self.selected_flower:
            # 可以在这里添加选中花朵的交互逻辑
            pass
    
    def keyPressEvent(self, event):
        """按键事件处理"""
        if event.key() == Qt.Key_Escape:
            self.close()
        elif event.key() == Qt.Key_Space:
            # 空格键添加花朵
            self.generate_flowers(10)
        elif event.key() == Qt.Key_R:
            # R键重置
            self.flowers = []
            self.generate_flowers(self.flower_count)
        elif event.key() == Qt.Key_D:
            # D键切换调试信息
            self.show_debug_info = not self.show_debug_info
        elif event.key() == Qt.Key_T:
            # T键切换地形显示
            self.show_terrain = not self.show_terrain

class AdvancedControlPanel(QWidget):
    """高级控制面板"""
    def __init__(self, flower_field):
        super().__init__()
        self.flower_field = flower_field
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout()
        
        # 创建标签页
        tabs = QTabWidget()
        
        # 环境控制标签页
        env_tab = QWidget()
        env_layout = QVBoxLayout()
        env_tab.setLayout(env_layout)
        
        # 时间控制
        time_group = QGroupBox("时间控制")
        time_layout = QVBoxLayout()
        
        # 日夜循环速度
        day_night_layout = QHBoxLayout()
        day_night_layout.addWidget(QLabel("日夜循环速度:"))
        self.day_night_slider = QSlider(Qt.Horizontal)
        self.day_night_slider.setRange(0, 100)
        self.day_night_slider.setValue(int(self.flower_field.environment.day_night_cycle_speed * 10000))
        self.day_night_slider.valueChanged.connect(self.update_day_night_speed)
        day_night_layout.addWidget(self.day_night_slider)
        time_layout.addLayout(day_night_layout)
        
        # 季节循环速度
        season_layout = QHBoxLayout()
        season_layout.addWidget(QLabel("季节循环速度:"))
        self.season_slider = QSlider(Qt.Horizontal)
        self.season_slider.setRange(0, 100)
        self.season_slider.setValue(int(self.flower_field.environment.season_cycle_speed * 100000))
        self.season_slider.valueChanged.connect(self.update_season_speed)
        season_layout.addWidget(self.season_slider)
        time_layout.addLayout(season_layout)
        
        time_group.setLayout(time_layout)
        env_layout.addWidget(time_group)
        
        # 天气控制
        weather_group = QGroupBox("天气控制")
        weather_layout = QVBoxLayout()
        
        weather_buttons_layout = QHBoxLayout()
        self.sunny_btn = QPushButton("晴朗")
        self.sunny_btn.clicked.connect(lambda: self.set_weather("sunny"))
        weather_buttons_layout.addWidget(self.sunny_btn)
        
        self.cloudy_btn = QPushButton("多云")
        self.cloudy_btn.clicked.connect(lambda: self.set_weather("cloudy"))
        weather_buttons_layout.addWidget(self.cloudy_btn)
        
        self.rainy_btn = QPushButton("雨天")
        self.rainy_btn.clicked.connect(lambda: self.set_weather("rainy"))
        weather_buttons_layout.addWidget(self.rainy_btn)
        
        self.stormy_btn = QPushButton("暴风雨")
        self.stormy_btn.clicked.connect(lambda: self.set_weather("stormy"))
        weather_buttons_layout.addWidget(self.stormy_btn)
        
        weather_layout.addLayout(weather_buttons_layout)
        weather_group.setLayout(weather_layout)
        env_layout.addWidget(weather_group)
        
        # 模拟控制
        sim_group = QGroupBox("模拟控制")
        sim_layout = QVBoxLayout()
        
        # 模拟速度
        speed_layout = QHBoxLayout()
        speed_layout.addWidget(QLabel("模拟速度:"))
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setRange(0, 500)
        self.speed_slider.setValue(int(self.flower_field.simulation_speed * 100))
        self.speed_slider.valueChanged.connect(self.update_simulation_speed)
        speed_layout.addWidget(self.speed_slider)
        sim_layout.addLayout(speed_layout)
        
        # 花朵数量
        count_layout = QHBoxLayout()
        count_layout.addWidget(QLabel("花朵数量:"))
        self.count_spin = QSpinBox()
        self.count_spin.setRange(0, self.flower_field.max_flowers)
        self.count_spin.setValue(self.flower_field.flower_count)
        self.count_spin.valueChanged.connect(self.update_flower_count)
        count_layout.addWidget(self.count_spin)
        sim_layout.addLayout(count_layout)
        
        sim_group.setLayout(sim_layout)
        env_layout.addWidget(sim_group)
        
        # 视觉效果标签页
        visual_tab = QWidget()
        visual_layout = QVBoxLayout()
        visual_tab.setLayout(visual_layout)
        
        # 视觉效果开关
        effects_group = QGroupBox("视觉效果")
        effects_layout = QVBoxLayout()
        
        self.shadow_check = QCheckBox("显示阴影")
        self.shadow_check.setChecked(self.flower_field.show_shadows)
        self.shadow_check.stateChanged.connect(self.update_shadows)
        effects_layout.addWidget(self.shadow_check)
        
        self.terrain_check = QCheckBox("显示地形")
        self.terrain_check.setChecked(self.flower_field.show_terrain)
        self.terrain_check.stateChanged.connect(self.update_terrain)
        effects_layout.addWidget(self.terrain_check)
        
        self.debug_check = QCheckBox("显示调试信息")
        self.debug_check.setChecked(self.flower_field.show_debug_info)
        self.debug_check.stateChanged.connect(self.update_debug_info)
        effects_layout.addWidget(self.debug_check)
        
        self.bloom_check = QCheckBox("绽放效果")
        self.bloom_check.setChecked(self.flower_field.bloom_effect)
        self.bloom_check.stateChanged.connect(self.update_bloom_effect)
        effects_layout.addWidget(self.bloom_check)
        
        effects_group.setLayout(effects_layout)
        visual_layout.addWidget(effects_group)
        
        # 添加到标签页
        tabs.addTab(env_tab, "环境控制")
        tabs.addTab(visual_tab, "视觉效果")
        
        layout.addWidget(tabs)
        
        # 重置按钮
        reset_btn = QPushButton("重置生态系统")
        reset_btn.clicked.connect(self.reset_ecosystem)
        layout.addWidget(reset_btn)
        
        self.setLayout(layout)
    
    def update_day_night_speed(self, value):
        """更新日夜循环速度"""
        self.flower_field.environment.day_night_cycle_speed = value / 10000.0
    
    def update_season_speed(self, value):
        """更新季节循环速度"""
        self.flower_field.environment.season_cycle_speed = value / 100000.0
    
    def set_weather(self, weather_type):
        """设置天气"""
        self.flower_field.environment.weather_type = weather_type
        self.flower_field.environment.target_weather = weather_type
        self.flower_field.environment.weather_transition = 0.0
    
    def update_simulation_speed(self, value):
        """更新模拟速度"""
        self.flower_field.simulation_speed = value / 100.0
    
    def update_flower_count(self, value):
        """更新花朵数量"""
        self.flower_field.flower_count = value
        current_count = len(self.flower_field.flowers)
        if current_count < value:
            self.flower_field.generate_flowers(value - current_count)
        elif current_count > value:
            self.flower_field.flowers = self.flower_field.flowers[:value]
    
    def update_shadows(self, state):
        """更新阴影显示"""
        self.flower_field.show_shadows = (state == Qt.Checked)
    
    def update_terrain(self, state):
        """更新地形显示"""
        self.flower_field.show_terrain = (state == Qt.Checked)
    
    def update_debug_info(self, state):
        """更新调试信息显示"""
        self.flower_field.show_debug_info = (state == Qt.Checked)
    
    def update_bloom_effect(self, state):
        """更新绽放效果"""
        self.flower_field.bloom_effect = (state == Qt.Checked)
    
    def reset_ecosystem(self):
        """重置生态系统"""
        self.flower_field.flowers = []
        self.flower_field.generate_flowers(self.flower_field.flower_count)
        self.flower_field.environment = Environment(
            self.flower_field.width(), 
            self.flower_field.height()
        )

class UltraRealisticMainWindow(QMainWindow):
    """超真实花海主窗口"""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("超真实花海生态系统模拟 - 完整版")
        
        # 创建中央部件和布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QHBoxLayout(central_widget)
        
        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        
        # 创建花海效果区域
        self.flower_field = UltraRealisticFlowerField()
        splitter.addWidget(self.flower_field)
        
        # 创建控制面板
        self.control_panel = AdvancedControlPanel(self.flower_field)
        splitter.addWidget(self.control_panel)
        
        # 设置分割比例
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 1)
        
        layout.addWidget(splitter)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 设置应用程序样式
    app.setStyle('Fusion')
    
    window = UltraRealisticMainWindow()
    window.showMaximized()
    
    sys.exit(app.exec_())