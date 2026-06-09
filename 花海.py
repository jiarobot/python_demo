import sys
import random
import math
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget
from PyQt5.QtCore import Qt, QTimer, QPointF, QRectF
from PyQt5.QtGui import QPainter, QBrush, QColor, QRadialGradient, QPen, QFont
import numpy as np

class FlowerParticle:
    """单个花朵粒子类"""
    def __init__(self, x, y, size, color, petal_count):
        self.x = x
        self.y = y
        self.size = size
        self.base_size = size
        self.color = color
        self.petal_count = petal_count
        self.angle = random.uniform(0, 2 * math.pi)
        self.rotation_speed = random.uniform(-0.02, 0.02)
        self.pulse_speed = random.uniform(0.05, 0.1)
        self.pulse_offset = random.uniform(0, 2 * math.pi)
        self.velocity = QPointF(
            random.uniform(-0.5, 0.5),
            random.uniform(-0.5, 0.5)
        )
        self.life = 1.0
        self.decay_rate = random.uniform(0.002, 0.005)
        
    def update(self):
        """更新粒子状态"""
        self.x += self.velocity.x()
        self.y += self.velocity.y()
        self.angle += self.rotation_speed
        self.size = self.base_size * (0.8 + 0.2 * math.sin(self.pulse_offset + self.pulse_speed * QApplication.instance().timer_counter))
        self.life -= self.decay_rate
        return self.life > 0

class FlowerField(QWidget):
    """花海效果主窗口"""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("花海颠覆性震撼效果")
        self.setGeometry(100, 100, 1200, 800)
        
        # 设置黑色背景
        self.setStyleSheet("background-color: black;")
        
        # 初始化粒子列表
        self.flowers = []
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_field)
        self.timer.start(16)  # 约60FPS
        
        # 色彩方案
        self.color_schemes = [
            [(255, 20, 147), (255, 105, 180), (255, 182, 193)],  # 粉色系
            [(138, 43, 226), (147, 112, 219), (186, 85, 211)],   # 紫色系
            [(255, 215, 0), (255, 165, 0), (255, 140, 0)],       # 金色系
            [(0, 255, 127), (50, 205, 50), (144, 238, 144)],     # 绿色系
            [(30, 144, 255), (0, 191, 255), (135, 206, 250)]     # 蓝色系
        ]
        
        self.current_scheme = 0
        self.scheme_timer = 0
        self.timer_counter = 0
        
        # 初始生成花朵
        self.generate_flowers(500)
        
    def generate_flowers(self, count):
        """生成指定数量的花朵"""
        for _ in range(count):
            x = random.uniform(0, self.width())
            y = random.uniform(0, self.height())
            size = random.uniform(15, 40)
            color_scheme = self.color_schemes[self.current_scheme]
            color = random.choice(color_scheme)
            petal_count = random.randint(5, 8)
            
            self.flowers.append(FlowerParticle(x, y, size, color, petal_count))
    
    def update_field(self):
        """更新花海状态"""
        self.timer_counter += 1
        
        # 更新色彩方案
        self.scheme_timer += 1
        if self.scheme_timer > 300:  # 每300帧切换一次色彩方案
            self.current_scheme = (self.current_scheme + 1) % len(self.color_schemes)
            self.scheme_timer = 0
        
        # 更新所有花朵
        self.flowers = [flower for flower in self.flowers if flower.update()]
        
        # 补充新的花朵
        if len(self.flowers) < 500:
            self.generate_flowers(10)
            
        # 触发重绘
        self.update()
    
    def paintEvent(self, event):
        """绘制花海"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 绘制所有花朵
        for flower in self.flowers:
            self.draw_flower(painter, flower)
        
        # 绘制标题
        self.draw_title(painter)
    
    def draw_flower(self, painter, flower):
        """绘制单个花朵"""
        # 计算透明度
        alpha = int(255 * flower.life)
        
        # 绘制花瓣
        for i in range(flower.petal_count):
            angle = flower.angle + i * (2 * math.pi / flower.petal_count)
            
            # 花瓣位置
            petal_x = flower.x + math.cos(angle) * flower.size * 0.7
            petal_y = flower.y + math.sin(angle) * flower.size * 0.7
            
            # 花瓣大小
            petal_width = flower.size * 0.8
            petal_height = flower.size * 0.5
            
            # 创建花瓣颜色
            petal_color = QColor(*flower.color, alpha)
            
            # 绘制花瓣
            painter.save()
            painter.translate(petal_x, petal_y)
            painter.rotate(math.degrees(angle))
            
            # 花瓣渐变效果
            gradient = QRadialGradient(0, 0, petal_width/2)
            gradient.setColorAt(0, QColor(*flower.color, alpha))
            lighter_color = self.lighten_color(flower.color)
            gradient.setColorAt(1, QColor(*lighter_color, alpha//2))
            
            painter.setBrush(QBrush(gradient))
            painter.setPen(Qt.NoPen)
            
            # 绘制椭圆形花瓣
            painter.drawEllipse(QRectF(-petal_width/2, -petal_height/2, petal_width, petal_height))
            painter.restore()
        
        # 绘制花蕊
        center_color = QColor(255, 255, 0, alpha)  # 黄色花蕊
        painter.setBrush(QBrush(center_color))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(QPointF(flower.x, flower.y), flower.size * 0.2, flower.size * 0.2)
    
    def draw_title(self, painter):
        """绘制标题"""
        painter.setPen(QColor(255, 255, 255))
        font = QFont("Arial", 24, QFont.Bold)
        painter.setFont(font)
        painter.drawText(self.rect(), Qt.AlignTop | Qt.AlignHCenter, "花海颠覆性震撼效果")
        
        # 绘制说明文字
        font = QFont("Arial", 12)
        painter.setFont(font)
        painter.drawText(self.rect(), Qt.AlignBottom | Qt.AlignHCenter, "动态生成的花海粒子系统 - 按ESC退出")
    
    def lighten_color(self, color):
        """使颜色变亮"""
        r, g, b = color
        return (
            min(255, int(r * 1.3)),
            min(255, int(g * 1.3)),
            min(255, int(b * 1.3))
        )
    
    def keyPressEvent(self, event):
        """按键事件处理"""
        if event.key() == Qt.Key_Escape:
            self.close()
        elif event.key() == Qt.Key_Space:
            # 空格键添加更多花朵
            self.generate_flowers(100)

class MainWindow(QMainWindow):
    """主窗口"""
    def __init__(self):
        super().__init__()
        self.flower_field = FlowerField()
        self.setCentralWidget(self.flower_field)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 为应用程序添加一个计时器计数器
    app.timer_counter = 0
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec_())