import sys
import math
import random
import json
import socket
import threading
import time
from datetime import datetime
from enum import Enum
from PyQt5.QtCore import (Qt, QTimer, QPropertyAnimation, QEasingCurve, 
                         pyqtProperty, QRectF, QPointF, QSize, QPoint,
                         QSequentialAnimationGroup, QParallelAnimationGroup)
from PyQt5.QtGui import (QFont, QPainter, QPen, QBrush, QColor, QLinearGradient, 
                        QRadialGradient, QPainterPath, QTransform, QFontDatabase,
                        QPixmap, QImage, QPainterPath, QKeyEvent, QMouseEvent)
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QLabel, QPushButton, QSlider, 
                            QComboBox, QSpinBox, QGroupBox, QFormLayout,
                            QColorDialog, QCheckBox, QDoubleSpinBox, QLineEdit,
                            QTextEdit, QListWidget, QListWidgetItem, QSplitter,
                            QTabWidget, QFrame, QMessageBox, QFileDialog,
                            QProgressBar, QDial, QGridLayout, QScrollArea,
                            QSizePolicy, QToolButton, QMenu, QAction,
                            QDockWidget, QTreeWidget, QTreeWidgetItem)

# ==================== 增强效果枚举 ====================
class EnhancedLightBoardEffect(Enum):
    STATIC = 0
    BLINK = 1
    FADE = 2
    SCROLL = 3
    RAINBOW = 4
    PULSE = 5
    NEON = 6
    FIRE = 7
    WATER = 8
    SNOW = 9
    MATRIX = 10
    PARTICLE = 11
    WAVE = 12
    SPIRAL = 13
    GLITCH = 14
    HOLOGRAM = 15
    CHRISTMAS = 16
    GALAXY = 17
    PLASMA = 18
    KALEIDOSCOPE = 19
    
    @staticmethod
    def get_effect_names():
        return ["静态", "闪烁", "淡入淡出", "滚动", "彩虹", "脉冲", "霓虹", 
                "火焰", "水波", "雪花", "矩阵", "粒子", "波浪", "螺旋", 
                "故障", "全息", "圣诞", "银河", "等离子", "万花筒"]

# ==================== 粒子系统 ====================
class Particle:
    def __init__(self, x, y, color=None):
        self.x = x
        self.y = y
        self.vx = random.uniform(-2, 2)
        self.vy = random.uniform(-2, 2)
        self.life = random.uniform(50, 200)
        self.max_life = self.life
        self.color = color or QColor(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
        self.size = random.uniform(1, 4)
        
    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.life -= 1
        self.vy += 0.05  # 重力效果
        
    def is_alive(self):
        return self.life > 0

class ParticleSystem:
    def __init__(self):
        self.particles = []
        
    def add_particle(self, x, y, color=None):
        self.particles.append(Particle(x, y, color))
        
    def update(self):
        for particle in self.particles[:]:
            particle.update()
            if not particle.is_alive():
                self.particles.remove(particle)
                
    def draw(self, painter):
        for particle in self.particles:
            alpha = int(255 * (particle.life / particle.max_life))
            color = QColor(particle.color)
            color.setAlpha(alpha)
            painter.setBrush(QBrush(color))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(QPointF(particle.x, particle.y), particle.size, particle.size)

# ==================== 3D变换系统 ====================
class Transform3D:
    def __init__(self):
        self.rotation_x = 0
        self.rotation_y = 0
        self.rotation_z = 0
        self.scale = 1.0
        self.translation_x = 0
        self.translation_y = 0
        
    def get_transform(self):
        transform = QTransform()
        transform.translate(self.translation_x, self.translation_y)
        transform.rotate(self.rotation_x, Qt.XAxis)
        transform.rotate(self.rotation_y, Qt.YAxis)
        transform.rotate(self.rotation_z, Qt.ZAxis)
        transform.scale(self.scale, self.scale)
        return transform

# ==================== 网络控制服务器 ====================
class LightBoardServer(threading.Thread):
    def __init__(self, port=8888, light_board=None):
        super().__init__()
        self.port = port
        self.light_board = light_board
        self.running = True
        self.clients = []
        
    def run(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            self.socket.bind(('0.0.0.0', self.port))
            self.socket.listen(5)
            print(f"灯牌服务器启动在端口 {self.port}")
            
            while self.running:
                try:
                    client_socket, addr = self.socket.accept()
                    print(f"新客户端连接: {addr}")
                    self.clients.append(client_socket)
                    client_thread = threading.Thread(target=self.handle_client, args=(client_socket,))
                    client_thread.start()
                except:
                    break
        except Exception as e:
            print(f"服务器错误: {e}")
            
    def handle_client(self, client_socket):
        try:
            while self.running:
                data = client_socket.recv(1024).decode('utf-8')
                if not data:
                    break
                    
                print(f"收到命令: {data}")
                self.process_command(data, client_socket)
                
        except Exception as e:
            print(f"客户端处理错误: {e}")
        finally:
            if client_socket in self.clients:
                self.clients.remove(client_socket)
            client_socket.close()
            
    def process_command(self, command, client_socket):
        try:
            data = json.loads(command)
            action = data.get('action', '')
            
            if self.light_board:
                if action == 'set_text':
                    self.light_board.set_text(data.get('text', ''))
                elif action == 'set_effect':
                    self.light_board.set_effect(data.get('effect', 0), 
                                              data.get('speed', 1.0),
                                              data.get('intensity', 1.0))
                elif action == 'set_color':
                    color = data.get('color', {})
                    self.light_board.set_text_color(QColor(
                        color.get('r', 0), color.get('g', 0), color.get('b', 0)
                    ))
                    
            # 发送响应
            response = {'status': 'ok', 'action': action}
            client_socket.send(json.dumps(response).encode('utf-8'))
            
        except Exception as e:
            print(f"命令处理错误: {e}")
            response = {'status': 'error', 'message': str(e)}
            client_socket.send(json.dumps(response).encode('utf-8'))
            
    def stop(self):
        self.running = False
        if hasattr(self, 'socket'):
            self.socket.close()

# ==================== 脚本引擎 ====================
class ScriptEngine:
    def __init__(self, light_board):
        self.light_board = light_board
        self.scripts = {}
        self.running_scripts = {}
        
    def load_script(self, name, script_code):
        self.scripts[name] = script_code
        
    def run_script(self, name, duration=0):
        if name not in self.scripts:
            return False
            
        script_code = self.scripts[name]
        thread = threading.Thread(target=self._execute_script, args=(script_code, duration))
        thread.daemon = True
        thread.start()
        
        self.running_scripts[name] = thread
        return True
        
    def _execute_script(self, script_code, duration):
        start_time = time.time()
        
        # 简单的脚本执行 - 实际应用中可以使用更复杂的解析器
        lines = script_code.split('\n')
        for line in lines:
            if not line.strip() or line.strip().startswith('#'):
                continue
                
            try:
                # 解析简单的命令
                if line.startswith('text:'):
                    text = line[5:].strip()
                    self.light_board.set_text(text)
                elif line.startswith('effect:'):
                    parts = line[7:].strip().split(',')
                    if len(parts) >= 1:
                        effect = int(parts[0])
                        speed = float(parts[1]) if len(parts) > 1 else 1.0
                        intensity = float(parts[2]) if len(parts) > 2 else 1.0
                        self.light_board.set_effect(effect, speed, intensity)
                elif line.startswith('color:'):
                    parts = line[6:].strip().split(',')
                    if len(parts) >= 3:
                        r, g, b = int(parts[0]), int(parts[1]), int(parts[2])
                        self.light_board.set_text_color(QColor(r, g, b))
                elif line.startswith('wait:'):
                    wait_time = float(line[5:].strip())
                    time.sleep(wait_time)
            except Exception as e:
                print(f"脚本执行错误: {e}")
                
            # 检查是否超时
            if duration > 0 and time.time() - start_time > duration:
                break
                
    def stop_script(self, name):
        if name in self.running_scripts:
            # 在实际应用中需要更优雅的停止机制
            del self.running_scripts[name]

# ==================== 增强版灯牌控件 ====================
class EnhancedLightBoard(QWidget):
    def __init__(self, text="LED", parent=None):
        super().__init__(parent)
        self.text = text
        self.font_size = 40
        self.text_color = QColor(0, 255, 0)
        self.bg_color = QColor(0, 0, 0)
        self.border_color = QColor(100, 100, 100)
        self.border_width = 2
        self.effect_type = EnhancedLightBoardEffect.STATIC.value
        self.effect_speed = 1.0
        self.effect_intensity = 1.0
        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self.update_animation)
        self.animation_frame = 0
        self.scroll_offset = 0
        self.blink_state = True
        
        # 增强属性
        self.particle_system = ParticleSystem()
        self.transform_3d = Transform3D()
        self.enable_3d = False
        self.enable_particles = False
        self.shadow_blur = 0
        self.shadow_color = QColor(0, 0, 0, 100)
        self.glow_effect = False
        self.glow_color = QColor(255, 255, 255, 100)
        self.glow_size = 10
        self.texture = None
        self.mask_shape = None  # 自定义形状遮罩
        
        # 矩阵效果专用
        self.matrix_chars = "01"
        self.matrix_streams = []
        self.init_matrix_streams()
        
        # 动画组
        self.animation_group = QParallelAnimationGroup(self)
        
        self.setMinimumSize(300, 100)
        self.start_animation()
        
    def init_matrix_streams(self):
        """初始化矩阵效果的字符流"""
        self.matrix_streams = []
        for i in range(50):  # 创建50个字符流
            stream = {
                'x': random.randint(0, self.width()),
                'y': random.randint(-100, 0),
                'speed': random.uniform(1, 5),
                'length': random.randint(5, 20),
                'chars': []
            }
            # 初始化字符
            for j in range(stream['length']):
                stream['chars'].append(random.choice(self.matrix_chars))
            self.matrix_streams.append(stream)
            
    def set_text(self, text):
        self.text = text
        self.update()
        
    def set_font_size(self, size):
        self.font_size = size
        self.update()
        
    def set_text_color(self, color):
        self.text_color = color
        self.update()
        
    def set_bg_color(self, color):
        self.bg_color = color
        self.update()
        
    def set_effect(self, effect_type, speed=1.0, intensity=1.0):
        self.effect_type = effect_type
        self.effect_speed = speed
        self.effect_intensity = intensity
        self.animation_frame = 0
        self.start_animation()
        
    def set_3d_enabled(self, enabled):
        self.enable_3d = enabled
        self.update()
        
    def set_particles_enabled(self, enabled):
        self.enable_particles = enabled
        self.update()
        
    def set_shadow(self, blur, color):
        self.shadow_blur = blur
        self.shadow_color = color
        self.update()
        
    def set_glow(self, enabled, color=None, size=10):
        self.glow_effect = enabled
        if color:
            self.glow_color = color
        self.glow_size = size
        self.update()
        
    def set_texture(self, pixmap):
        self.texture = pixmap
        self.update()
        
    def start_animation(self):
        if self.effect_type != EnhancedLightBoardEffect.STATIC.value:
            interval = max(10, int(50 / self.effect_speed))
            self.animation_timer.start(interval)
        else:
            self.animation_timer.stop()
        self.update()
        
    def update_animation(self):
        self.animation_frame += 1
        
        # 更新粒子系统
        if self.enable_particles:
            # 在文本位置添加粒子
            if random.random() < 0.3:
                x = random.randint(0, self.width())
                y = random.randint(0, self.height())
                self.particle_system.add_particle(x, y, self.text_color)
            self.particle_system.update()
            
        # 更新矩阵效果
        if self.effect_type == EnhancedLightBoardEffect.MATRIX.value:
            for stream in self.matrix_streams:
                stream['y'] += stream['speed']
                if stream['y'] > self.height():
                    stream['y'] = random.randint(-100, 0)
                    stream['x'] = random.randint(0, self.width())
                
                # 随机更新字符
                if random.random() < 0.1:
                    for i in range(len(stream['chars'])):
                        if random.random() < 0.05:
                            stream['chars'][i] = random.choice(self.matrix_chars)
        
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
        
        # 应用3D变换
        if self.enable_3d:
            painter.setTransform(self.transform_3d.get_transform())
        
        # 绘制背景
        painter.fillRect(self.rect(), self.bg_color)
        
        # 绘制边框
        if self.border_width > 0:
            painter.setPen(QPen(self.border_color, self.border_width))
            painter.drawRect(self.rect().adjusted(1, 1, -1, -1))
        
        # 绘制阴影
        if self.shadow_blur > 0:
            self.draw_shadow(painter)
            
        # 绘制发光效果
        if self.glow_effect:
            self.draw_glow(painter)
        
        # 根据效果类型绘制文本
        effect_methods = {
            EnhancedLightBoardEffect.STATIC.value: self.draw_static_text,
            EnhancedLightBoardEffect.BLINK.value: self.draw_blink_text,
            EnhancedLightBoardEffect.FADE.value: self.draw_fade_text,
            EnhancedLightBoardEffect.SCROLL.value: self.draw_scroll_text,
            EnhancedLightBoardEffect.RAINBOW.value: self.draw_rainbow_text,
            EnhancedLightBoardEffect.PULSE.value: self.draw_pulse_text,
            EnhancedLightBoardEffect.NEON.value: self.draw_neon_text,
            EnhancedLightBoardEffect.FIRE.value: self.draw_fire_text,
            EnhancedLightBoardEffect.WATER.value: self.draw_water_text,
            EnhancedLightBoardEffect.SNOW.value: self.draw_snow_text,
            EnhancedLightBoardEffect.MATRIX.value: self.draw_matrix_text,
            EnhancedLightBoardEffect.PARTICLE.value: self.draw_particle_text,
            EnhancedLightBoardEffect.WAVE.value: self.draw_wave_text,
            EnhancedLightBoardEffect.SPIRAL.value: self.draw_spiral_text,
            EnhancedLightBoardEffect.GLITCH.value: self.draw_glitch_text,
            EnhancedLightBoardEffect.HOLOGRAM.value: self.draw_hologram_text,
            EnhancedLightBoardEffect.CHRISTMAS.value: self.draw_christmas_text,
            EnhancedLightBoardEffect.GALAXY.value: self.draw_galaxy_text,
            EnhancedLightBoardEffect.PLASMA.value: self.draw_plasma_text,
            EnhancedLightBoardEffect.KALEIDOSCOPE.value: self.draw_kaleidoscope_text,
        }
        
        if self.effect_type in effect_methods:
            effect_methods[self.effect_type](painter)
        
        # 绘制粒子系统
        if self.enable_particles:
            self.particle_system.draw(painter)
            
    def draw_shadow(self, painter):
        """绘制阴影效果"""
        shadow_painter = QPainter(self)
        shadow_painter.setRenderHint(QPainter.Antialiasing)
        
        # 创建阴影路径
        path = QPainterPath()
        font = QFont("Arial", self.font_size, QFont.Bold)
        path.addText(0, 0, font, self.text)
        
        # 计算文本居中位置
        text_rect = path.boundingRect()
        x_offset = (self.width() - text_rect.width()) / 2
        y_offset = (self.height() + text_rect.height()) / 2 - text_rect.height() / 4
        
        path.translate(x_offset + self.shadow_blur/2, y_offset + self.shadow_blur/2)
        
        # 绘制阴影
        shadow_painter.setPen(Qt.NoPen)
        shadow_painter.setBrush(self.shadow_color)
        shadow_painter.drawPath(path)
        
    def draw_glow(self, painter):
        """绘制发光效果"""
        glow_painter = QPainter(self)
        glow_painter.setRenderHint(QPainter.Antialiasing)
        
        # 创建发光路径
        path = QPainterPath()
        font = QFont("Arial", self.font_size, QFont.Bold)
        path.addText(0, 0, font, self.text)
        
        # 计算文本居中位置
        text_rect = path.boundingRect()
        x_offset = (self.width() - text_rect.width()) / 2
        y_offset = (self.height() + text_rect.height()) / 2 - text_rect.height() / 4
        
        path.translate(x_offset, y_offset)
        
        # 绘制多层发光效果
        for i in range(self.glow_size, 0, -1):
            color = QColor(self.glow_color)
            color.setAlpha(100 // i)
            pen = QPen(color, i*2)
            pen.setJoinStyle(Qt.RoundJoin)
            glow_painter.setPen(pen)
            glow_painter.setBrush(Qt.NoBrush)
            glow_painter.drawPath(path)
    
    def draw_static_text(self, painter):
        font = QFont("Arial", self.font_size, QFont.Bold)
        painter.setFont(font)
        
        if self.texture:
            # 使用纹理填充文本
            painter.setPen(Qt.NoPen)
            brush = QBrush(self.texture)
            painter.setBrush(brush)
            
            path = QPainterPath()
            path.addText(0, 0, font, self.text)
            text_rect = path.boundingRect()
            x_offset = (self.width() - text_rect.width()) / 2
            y_offset = (self.height() + text_rect.height()) / 2 - text_rect.height() / 4
            path.translate(x_offset, y_offset)
            
            painter.drawPath(path)
        else:
            # 普通文本绘制
            painter.setPen(self.text_color)
            painter.drawText(self.rect(), Qt.AlignCenter, self.text)
    
    def draw_blink_text(self, painter):
        if self.blink_state:
            self.draw_static_text(painter)
        
        if self.animation_frame % 10 == 0:
            self.blink_state = not self.blink_state
    
    def draw_fade_text(self, painter):
        alpha = int(128 + 127 * math.sin(self.animation_frame * 0.1 * self.effect_speed))
        color = QColor(self.text_color)
        color.setAlpha(alpha)
        painter.setPen(color)
        font = QFont("Arial", self.font_size, QFont.Bold)
        painter.setFont(font)
        painter.drawText(self.rect(), Qt.AlignCenter, self.text)
    
    def draw_scroll_text(self, painter):
        self.scroll_offset -= int(2 * self.effect_speed)
        font = QFont("Arial", self.font_size, QFont.Bold)
        painter.setFont(font)
        text_width = painter.fontMetrics().width(self.text)
        
        if self.scroll_offset < -text_width:
            self.scroll_offset = self.width()
            
        painter.setPen(self.text_color)
        painter.drawText(self.scroll_offset, self.height()//2 + self.font_size//2, self.text)
    
    def draw_rainbow_text(self, painter):
        font = QFont("Arial", self.font_size, QFont.Bold)
        painter.setFont(font)
        
        gradient = QLinearGradient(0, 0, self.width(), 0)
        colors = [QColor(255, 0, 0), QColor(255, 165, 0), QColor(255, 255, 0),
                 QColor(0, 255, 0), QColor(0, 0, 255), QColor(75, 0, 130),
                 QColor(238, 130, 238)]
        
        for i, color in enumerate(colors):
            gradient.setColorAt(i / len(colors), color)
        
        offset = (self.animation_frame * 2) % self.width()
        gradient.setStart(offset, 0)
        gradient.setFinalStop(offset + self.width(), 0)
        
        painter.setPen(QPen(gradient, 1))
        painter.drawText(self.rect(), Qt.AlignCenter, self.text)
    
    def draw_pulse_text(self, painter):
        scale = 1.0 + 0.2 * math.sin(self.animation_frame * 0.1 * self.effect_speed)
        font_size = int(self.font_size * scale)
        
        painter.setPen(self.text_color)
        font = QFont("Arial", font_size, QFont.Bold)
        painter.setFont(font)
        painter.drawText(self.rect(), Qt.AlignCenter, self.text)
    
    def draw_neon_text(self, painter):
        font = QFont("Arial", self.font_size, QFont.Bold)
        painter.setFont(font)
        
        for i in range(5, 0, -1):
            color = QColor(self.text_color)
            color.setAlpha(30 * i)
            pen = QPen(color, i)
            pen.setJoinStyle(Qt.RoundJoin)
            painter.setPen(pen)
            painter.drawText(self.rect(), Qt.AlignCenter, self.text)
        
        painter.setPen(self.text_color)
        painter.drawText(self.rect(), Qt.AlignCenter, self.text)
    
    def draw_fire_text(self, painter):
        font = QFont("Arial", self.font_size, QFont.Bold)
        painter.setFont(font)
        
        for i in range(10):
            offset_x = random.randint(-3, 3)
            offset_y = random.randint(-2, 0)
            alpha = random.randint(50, 200)
            color = QColor(255, random.randint(100, 200), 0, alpha)
            painter.setPen(color)
            painter.drawText(self.rect().adjusted(offset_x, offset_y, offset_x, offset_y), 
                            Qt.AlignCenter, self.text)
    
    def draw_water_text(self, painter):
        font = QFont("Arial", self.font_size, QFont.Bold)
        painter.setFont(font)
        
        path = QPainterPath()
        y_center = self.height() / 2
        
        for i, char in enumerate(self.text):
            x_pos = (self.width() - painter.fontMetrics().width(self.text)) / 2 + i * painter.fontMetrics().width(char)
            y_offset = 5 * math.sin(self.animation_frame * 0.1 + i * 0.5) * self.effect_intensity
            path.addText(x_pos, y_center + y_offset, font, char)
        
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0, QColor(100, 100, 255))
        gradient.setColorAt(1, QColor(0, 0, 200))
        
        painter.setPen(QPen(QColor(0, 0, 150), 1))
        painter.setBrush(QBrush(gradient))
        painter.drawPath(path)
    
    def draw_snow_text(self, painter):
        font = QFont("Arial", self.font_size, QFont.Bold)
        painter.setFont(font)
        
        painter.setPen(self.text_color)
        painter.drawText(self.rect(), Qt.AlignCenter, self.text)
        
        painter.setPen(QColor(255, 255, 255))
        for _ in range(20):
            x = random.randint(0, self.width())
            y = random.randint(0, self.height())
            size = random.randint(1, 3)
            painter.drawEllipse(x, y, size, size)
    
    def draw_matrix_text(self, painter):
        font = QFont("Courier New", self.font_size, QFont.Bold)
        painter.setFont(font)
        
        for stream in self.matrix_streams:
            for i, char in enumerate(stream['chars']):
                y = stream['y'] + i * painter.fontMetrics().height()
                
                if 0 <= y < self.height():
                    # 渐变颜色 - 顶部亮绿色，底部暗绿色
                    intensity = 1.0 - (i / len(stream['chars']))
                    color = QColor(0, int(255 * intensity), 0)
                    
                    painter.setPen(color)
                    painter.drawText(int(stream['x']),int(y) , char)
    
    def draw_particle_text(self, painter):
        self.draw_static_text(painter)
        
        # 粒子效果已经在update_animation中处理
    
    def draw_wave_text(self, painter):
        font = QFont("Arial", self.font_size, QFont.Bold)
        painter.setFont(font)
        
        path = QPainterPath()
        y_center = self.height() / 2
        
        for i, char in enumerate(self.text):
            x_pos = (self.width() - painter.fontMetrics().width(self.text)) / 2 + i * painter.fontMetrics().width(char)
            y_offset = 10 * math.sin(self.animation_frame * 0.1 + i * 0.3) * self.effect_intensity
            path.addText(x_pos, y_center + y_offset, font, char)
        
        painter.setPen(self.text_color)
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(path)
    
    def draw_spiral_text(self, painter):
        font = QFont("Arial", self.font_size, QFont.Bold)
        painter.setFont(font)
        
        center_x, center_y = self.width() / 2, self.height() / 2
        radius = min(self.width(), self.height()) / 3
        angle_step = 2 * math.pi / len(self.text)
        
        for i, char in enumerate(self.text):
            angle = self.animation_frame * 0.02 + i * angle_step
            spiral_radius = radius * (1 + 0.2 * math.sin(angle * 2))
            x = center_x + spiral_radius * math.cos(angle)
            y = center_y + spiral_radius * math.sin(angle)
            
            # 旋转字符使其朝向中心
            painter.save()
            painter.translate(x, y)
            painter.rotate(angle * 180 / math.pi + 90)
            painter.setPen(self.text_color)
            painter.drawText(0, 0, char)
            painter.restore()
    
    def draw_glitch_text(self, painter):
        font = QFont("Arial", self.font_size, QFont.Bold)
        painter.setFont(font)
        
        # 绘制多个偏移的文本层
        for i in range(3):
            offset_x = random.randint(-5, 5)
            offset_y = random.randint(-3, 3)
            
            if i == 0:
                color = QColor(255, 0, 0)  # 红色
            elif i == 1:
                color = QColor(0, 255, 0)  # 绿色
            else:
                color = QColor(0, 0, 255)  # 蓝色
                
            painter.setPen(color)
            painter.drawText(self.rect().adjusted(offset_x, offset_y, offset_x, offset_y), 
                            Qt.AlignCenter, self.text)
    
    def draw_hologram_text(self, painter):
        font = QFont("Arial", self.font_size, QFont.Bold)
        painter.setFont(font)
        
        # 创建全息效果 - 多层半透明文本
        for i in range(10, 0, -1):
            offset_y = i * 2
            alpha = 100 - i * 8
            
            color = QColor(0, 255, 255, alpha)
            painter.setPen(color)
            painter.drawText(self.rect().adjusted(0, offset_y, 0, offset_y), 
                            Qt.AlignCenter, self.text)
    
    def draw_christmas_text(self, painter):
        font = QFont("Arial", self.font_size, QFont.Bold)
        painter.setFont(font)
        
        # 交替红色和绿色
        text_width = painter.fontMetrics().width(self.text)
        start_x = (self.width() - text_width) / 2
        
        for i, char in enumerate(self.text):
            if i % 2 == 0:
                color = QColor(255, 0, 0)  # 红色
            else:
                color = QColor(0, 255, 0)  # 绿色
                
            painter.setPen(color)
            painter.drawText(int(start_x + painter.fontMetrics().width(self.text[:i])), 
                            int(self.height()/2 + self.font_size/2), char)
        
        # 添加闪烁效果
        if self.animation_frame % 10 == 0:
            # 随机改变一些字符的颜色
            pass
    
    def draw_galaxy_text(self, painter):
        font = QFont("Arial", self.font_size, QFont.Bold)
        painter.setFont(font)
        
        # 星空背景
        for _ in range(100):
            x = random.randint(0, self.width())
            y = random.randint(0, self.height())
            size = random.randint(1, 3)
            brightness = random.randint(100, 255)
            painter.setPen(QColor(brightness, brightness, brightness))
            painter.drawEllipse(x, y, size, size)
        
        # 银河渐变文本
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0, QColor(100, 100, 255))
        gradient.setColorAt(0.5, QColor(200, 200, 255))
        gradient.setColorAt(1, QColor(100, 100, 255))
        
        painter.setPen(QPen(gradient, 1))
        painter.drawText(self.rect(), Qt.AlignCenter, self.text)
    
    def draw_plasma_text(self, painter):
        font = QFont("Arial", self.font_size, QFont.Bold)
        painter.setFont(font)
        
        # 等离子效果 - 动态变化的渐变
        time_factor = self.animation_frame * 0.01
        
        for i, char in enumerate(self.text):
            # 为每个字符计算不同的颜色
            hue = (time_factor * 50 + i * 30) % 360
            saturation = 200 + 55 * math.sin(time_factor * 2 + i * 0.5)
            value = 200 + 55 * math.cos(time_factor * 3 + i * 0.3)
            
            color = QColor.fromHsv(int(hue) % 360, int(saturation) % 255, int(value) % 255)
            painter.setPen(color)
            
            # 计算字符位置
            text_width = painter.fontMetrics().width(self.text)
            start_x = (self.width() - text_width) / 2
            painter.drawText(int(start_x + painter.fontMetrics().width(self.text[:i])), 
                            int(self.height()/2 + self.font_size/2), char)
    
    def draw_kaleidoscope_text(self, painter):
        font = QFont("Arial", self.font_size, QFont.Bold)
        painter.setFont(font)
        
        center_x, center_y = self.width() / 2, self.height() / 2
        segments = 8  # 万花筒分段数
        
        for i in range(segments):
            angle = i * (2 * math.pi / segments)
            
            painter.save()
            painter.translate(center_x, center_y)
            painter.rotate(angle * 180 / math.pi)
            
            # 为每个段应用不同的颜色
            hue = (i * 360 / segments + self.animation_frame * 2) % 360
            color = QColor.fromHsv(int(hue), 255, 255)
            painter.setPen(color)
            
            # 绘制文本
            text_rect = painter.fontMetrics().boundingRect(self.text)
            painter.drawText(int(-text_rect.width()/2), int(text_rect.height()/4), self.text)
            painter.restore()

# ==================== 增强控制面板 ====================
class EnhancedLightBoardControlPanel(QWidget):
    def __init__(self, light_board, parent=None):
        super().__init__(parent)
        self.light_board = light_board
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # 创建选项卡
        tab_widget = QTabWidget()
        layout.addWidget(tab_widget)
        
        # 基本设置选项卡
        basic_tab = QWidget()
        basic_layout = QFormLayout(basic_tab)
        self.setup_basic_tab(basic_layout)
        tab_widget.addTab(basic_tab, "基本设置")
        
        # 效果设置选项卡
        effect_tab = QWidget()
        effect_layout = QFormLayout(effect_tab)
        self.setup_effect_tab(effect_layout)
        tab_widget.addTab(effect_tab, "效果设置")
        
        # 高级效果选项卡
        advanced_tab = QWidget()
        advanced_layout = QFormLayout(advanced_tab)
        self.setup_advanced_tab(advanced_layout)
        tab_widget.addTab(advanced_tab, "高级效果")
        
        # 3D设置选项卡
        three_d_tab = QWidget()
        three_d_layout = QFormLayout(three_d_tab)
        self.setup_3d_tab(three_d_layout)
        tab_widget.addTab(three_d_tab, "3D设置")
        
    def setup_basic_tab(self, layout):
        self.text_input = QLineEdit(self.light_board.text)
        self.text_input.textChanged.connect(self.update_text)
        layout.addRow("文本内容:", self.text_input)
        
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(10, 100)
        self.font_size_spin.setValue(self.light_board.font_size)
        self.font_size_spin.valueChanged.connect(self.update_font_size)
        layout.addRow("字体大小:", self.font_size_spin)
        
        self.text_color_btn = QPushButton("选择文本颜色")
        self.text_color_btn.clicked.connect(self.choose_text_color)
        layout.addRow("文本颜色:", self.text_color_btn)
        
        self.bg_color_btn = QPushButton("选择背景颜色")
        self.bg_color_btn.clicked.connect(self.choose_bg_color)
        layout.addRow("背景颜色:", self.bg_color_btn)
        
        self.border_width_spin = QSpinBox()
        self.border_width_spin.setRange(0, 10)
        self.border_width_spin.setValue(self.light_board.border_width)
        self.border_width_spin.valueChanged.connect(self.update_border_width)
        layout.addRow("边框宽度:", self.border_width_spin)
        
        self.border_color_btn = QPushButton("选择边框颜色")
        self.border_color_btn.clicked.connect(self.choose_border_color)
        layout.addRow("边框颜色:", self.border_color_btn)
        
    def setup_effect_tab(self, layout):
        self.effect_combo = QComboBox()
        self.effect_combo.addItems(EnhancedLightBoardEffect.get_effect_names())
        self.effect_combo.setCurrentIndex(self.light_board.effect_type)
        self.effect_combo.currentIndexChanged.connect(self.update_effect)
        layout.addRow("效果类型:", self.effect_combo)
        
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setRange(1, 10)
        self.speed_slider.setValue(int(self.light_board.effect_speed * 5))
        self.speed_slider.valueChanged.connect(self.update_speed)
        layout.addRow("效果速度:", self.speed_slider)
        
        self.intensity_slider = QSlider(Qt.Horizontal)
        self.intensity_slider.setRange(1, 10)
        self.intensity_slider.setValue(int(self.light_board.effect_intensity * 5))
        self.intensity_slider.valueChanged.connect(self.update_intensity)
        layout.addRow("效果强度:", self.intensity_slider)
        
    def setup_advanced_tab(self, layout):
        self.shadow_check = QCheckBox("启用阴影")
        self.shadow_check.stateChanged.connect(self.toggle_shadow)
        layout.addRow(self.shadow_check)
        
        self.shadow_blur_spin = QSpinBox()
        self.shadow_blur_spin.setRange(0, 20)
        self.shadow_blur_spin.setValue(self.light_board.shadow_blur)
        self.shadow_blur_spin.valueChanged.connect(self.update_shadow)
        layout.addRow("阴影模糊:", self.shadow_blur_spin)
        
        self.shadow_color_btn = QPushButton("选择阴影颜色")
        self.shadow_color_btn.clicked.connect(self.choose_shadow_color)
        layout.addRow("阴影颜色:", self.shadow_color_btn)
        
        self.glow_check = QCheckBox("启用发光")
        self.glow_check.stateChanged.connect(self.toggle_glow)
        layout.addRow(self.glow_check)
        
        self.glow_size_spin = QSpinBox()
        self.glow_size_spin.setRange(1, 20)
        self.glow_size_spin.setValue(self.light_board.glow_size)
        self.glow_size_spin.valueChanged.connect(self.update_glow)
        layout.addRow("发光大小:", self.glow_size_spin)
        
        self.glow_color_btn = QPushButton("选择发光颜色")
        self.glow_color_btn.clicked.connect(self.choose_glow_color)
        layout.addRow("发光颜色:", self.glow_color_btn)
        
        self.particles_check = QCheckBox("启用粒子效果")
        self.particles_check.stateChanged.connect(self.toggle_particles)
        layout.addRow(self.particles_check)
        
        self.texture_btn = QPushButton("加载纹理")
        self.texture_btn.clicked.connect(self.load_texture)
        layout.addRow("纹理:", self.texture_btn)
        
    def setup_3d_tab(self, layout):
        self.enable_3d_check = QCheckBox("启用3D效果")
        self.enable_3d_check.stateChanged.connect(self.toggle_3d)
        layout.addRow(self.enable_3d_check)
        
        self.rotation_x_slider = QSlider(Qt.Horizontal)
        self.rotation_x_slider.setRange(0, 360)
        self.rotation_x_slider.setValue(int(self.light_board.transform_3d.rotation_x))
        self.rotation_x_slider.valueChanged.connect(self.update_3d_rotation)
        layout.addRow("X轴旋转:", self.rotation_x_slider)
        
        self.rotation_y_slider = QSlider(Qt.Horizontal)
        self.rotation_y_slider.setRange(0, 360)
        self.rotation_y_slider.setValue(int(self.light_board.transform_3d.rotation_y))
        self.rotation_y_slider.valueChanged.connect(self.update_3d_rotation)
        layout.addRow("Y轴旋转:", self.rotation_y_slider)
        
        self.rotation_z_slider = QSlider(Qt.Horizontal)
        self.rotation_z_slider.setRange(0, 360)
        self.rotation_z_slider.setValue(int(self.light_board.transform_3d.rotation_z))
        self.rotation_z_slider.valueChanged.connect(self.update_3d_rotation)
        layout.addRow("Z轴旋转:", self.rotation_z_slider)
        
        self.scale_slider = QSlider(Qt.Horizontal)
        self.scale_slider.setRange(50, 200)
        self.scale_slider.setValue(int(self.light_board.transform_3d.scale * 100))
        self.scale_slider.valueChanged.connect(self.update_3d_scale)
        layout.addRow("缩放:", self.scale_slider)
        
    def update_text(self):
        self.light_board.set_text(self.text_input.text())
        
    def update_font_size(self):
        self.light_board.set_font_size(self.font_size_spin.value())
        
    def choose_text_color(self):
        color = QColorDialog.getColor(self.light_board.text_color, self)
        if color.isValid():
            self.light_board.set_text_color(color)
            
    def choose_bg_color(self):
        color = QColorDialog.getColor(self.light_board.bg_color, self)
        if color.isValid():
            self.light_board.set_bg_color(color)
            
    def update_border_width(self):
        self.light_board.border_width = self.border_width_spin.value()
        self.light_board.update()
        
    def choose_border_color(self):
        color = QColorDialog.getColor(self.light_board.border_color, self)
        if color.isValid():
            self.light_board.border_color = color
            self.light_board.update()
            
    def update_effect(self):
        self.light_board.set_effect(self.effect_combo.currentIndex(), 
                                   self.speed_slider.value() / 5,
                                   self.intensity_slider.value() / 5)
        
    def update_speed(self):
        self.light_board.effect_speed = self.speed_slider.value() / 5
        self.light_board.start_animation()
        
    def update_intensity(self):
        self.light_board.effect_intensity = self.intensity_slider.value() / 5
        
    def toggle_shadow(self, state):
        if state == Qt.Checked:
            self.light_board.set_shadow(self.light_board.shadow_blur, self.light_board.shadow_color)
        else:
            self.light_board.set_shadow(0, self.light_board.shadow_color)
            
    def update_shadow(self):
        self.light_board.set_shadow(self.shadow_blur_spin.value(), self.light_board.shadow_color)
        
    def choose_shadow_color(self):
        color = QColorDialog.getColor(self.light_board.shadow_color, self)
        if color.isValid():
            self.light_board.set_shadow(self.light_board.shadow_blur, color)
            
    def toggle_glow(self, state):
        self.light_board.set_glow(state == Qt.Checked)
        
    def update_glow(self):
        self.light_board.set_glow(self.glow_check.isChecked(), self.light_board.glow_color, self.glow_size_spin.value())
        
    def choose_glow_color(self):
        color = QColorDialog.getColor(self.light_board.glow_color, self)
        if color.isValid():
            self.light_board.set_glow(self.glow_check.isChecked(), color, self.glow_size_spin.value())
            
    def toggle_particles(self, state):
        self.light_board.set_particles_enabled(state == Qt.Checked)
        
    def load_texture(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "选择纹理图片", "", "图片文件 (*.png *.jpg *.bmp)")
        if file_name:
            pixmap = QPixmap(file_name)
            self.light_board.set_texture(pixmap)
            
    def toggle_3d(self, state):
        self.light_board.set_3d_enabled(state == Qt.Checked)
        
    def update_3d_rotation(self):
        self.light_board.transform_3d.rotation_x = self.rotation_x_slider.value()
        self.light_board.transform_3d.rotation_y = self.rotation_y_slider.value()
        self.light_board.transform_3d.rotation_z = self.rotation_z_slider.value()
        self.light_board.update()
        
    def update_3d_scale(self):
        self.light_board.transform_3d.scale = self.scale_slider.value() / 100
        self.light_board.update()

# ==================== 网络控制面板 ====================
class NetworkControlPanel(QWidget):
    def __init__(self, light_board, parent=None):
        super().__init__(parent)
        self.light_board = light_board
        self.server = None
        self.script_engine = ScriptEngine(light_board)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # 服务器控制
        server_group = QGroupBox("网络服务器控制")
        server_layout = QFormLayout(server_group)
        
        self.port_spin = QSpinBox()
        self.port_spin.setRange(1000, 65535)
        self.port_spin.setValue(8888)
        server_layout.addRow("端口:", self.port_spin)
        
        self.start_server_btn = QPushButton("启动服务器")
        self.start_server_btn.clicked.connect(self.toggle_server)
        server_layout.addRow(self.start_server_btn)
        
        self.server_status_label = QLabel("服务器未运行")
        server_layout.addRow("状态:", self.server_status_label)
        
        layout.addWidget(server_group)
        
        # 脚本控制
        script_group = QGroupBox("脚本控制")
        script_layout = QVBoxLayout(script_group)
        
        self.script_edit = QTextEdit()
        self.script_edit.setPlaceholderText("输入脚本命令...\n示例:\ntext:Hello World\neffect:4,1.5,1.0\ncolor:255,0,0\nwait:2.0")
        script_layout.addWidget(self.script_edit)
        
        script_btn_layout = QHBoxLayout()
        self.load_script_btn = QPushButton("加载脚本")
        self.load_script_btn.clicked.connect(self.load_script)
        script_btn_layout.addWidget(self.load_script_btn)
        
        self.run_script_btn = QPushButton("运行脚本")
        self.run_script_btn.clicked.connect(self.run_script)
        script_btn_layout.addWidget(self.run_script_btn)
        
        script_layout.addLayout(script_btn_layout)
        
        layout.addWidget(script_group)
        
        layout.addStretch()
        
    def toggle_server(self):
        if self.server and self.server.is_alive():
            self.server.stop()
            self.server = None
            self.start_server_btn.setText("启动服务器")
            self.server_status_label.setText("服务器未运行")
        else:
            self.server = LightBoardServer(self.port_spin.value(), self.light_board)
            self.server.start()
            self.start_server_btn.setText("停止服务器")
            self.server_status_label.setText(f"服务器运行在端口 {self.port_spin.value()}")
            
    def load_script(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "选择脚本文件", "", "文本文件 (*.txt)")
        if file_name:
            try:
                with open(file_name, 'r', encoding='utf-8') as f:
                    script_content = f.read()
                self.script_edit.setPlainText(script_content)
            except Exception as e:
                QMessageBox.critical(self, "错误", f"加载脚本失败: {e}")
                
    def run_script(self):
        script_content = self.script_edit.toPlainText()
        if script_content:
            self.script_engine.load_script("custom", script_content)
            self.script_engine.run_script("custom")

# ==================== 主窗口 ====================
class EnhancedLightBoardDemo(QMainWindow):
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("增强版PyQt灯牌系统高级工具库演示")
        self.setGeometry(100, 100, 1200, 800)
        
        # 创建中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QHBoxLayout(central_widget)
        
        # 左侧灯牌区域
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        # 创建增强版灯牌
        self.light_board = EnhancedLightBoard("增强版灯牌系统")
        self.light_board.set_effect(EnhancedLightBoardEffect.PLASMA.value, 1.5, 1.0)
        left_layout.addWidget(self.light_board)
        
        # 创建时钟灯牌
        self.clock_board = EnhancedLightBoard()
        self.clock_board.set_effect(EnhancedLightBoardEffect.NEON.value, 1.0, 1.0)
        self.clock_board.set_text_color(QColor(255, 215, 0))
        left_layout.addWidget(self.clock_board)
        
        # 创建跑马灯
        self.marquee_board = EnhancedLightBoard("这是一个增强版跑马灯效果的演示文本")
        self.marquee_board.set_effect(EnhancedLightBoardEffect.SCROLL.value, 1.0, 1.0)
        self.marquee_board.set_text_color(QColor(50, 205, 50))
        left_layout.addWidget(self.marquee_board)
        
        main_layout.addWidget(left_widget, 3)  # 左侧占3份
        
        # 右侧控制面板
        right_widget = QTabWidget()
        
        # 灯牌控制面板
        self.control_panel = EnhancedLightBoardControlPanel(self.light_board)
        right_widget.addTab(self.control_panel, "灯牌控制")
        
        # 网络控制面板
        self.network_panel = NetworkControlPanel(self.light_board)
        right_widget.addTab(self.network_panel, "网络控制")
        
        main_layout.addWidget(right_widget, 1)  # 右侧占1份
        
        # 状态栏
        self.statusBar().showMessage("就绪")
        
        # 菜单栏
        self.create_menus()
        
        # 定时更新时钟
        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self.update_clock)
        self.clock_timer.start(1000)
        self.update_clock()
        
    def create_menus(self):
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu('文件')
        
        save_action = QAction('保存配置', self)
        save_action.triggered.connect(self.save_config)
        file_menu.addAction(save_action)
        
        load_action = QAction('加载配置', self)
        load_action.triggered.connect(self.load_config)
        file_menu.addAction(load_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction('退出', self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 效果菜单
        effect_menu = menubar.addMenu('预设效果')
        
        rainbow_action = QAction('彩虹效果', self)
        rainbow_action.triggered.connect(lambda: self.apply_preset('rainbow'))
        effect_menu.addAction(rainbow_action)
        
        neon_action = QAction('霓虹效果', self)
        neon_action.triggered.connect(lambda: self.apply_preset('neon'))
        effect_menu.addAction(neon_action)
        
        matrix_action = QAction('矩阵效果', self)
        matrix_action.triggered.connect(lambda: self.apply_preset('matrix'))
        effect_menu.addAction(matrix_action)
        
        plasma_action = QAction('等离子效果', self)
        plasma_action.triggered.connect(lambda: self.apply_preset('plasma'))
        effect_menu.addAction(plasma_action)
        
    def update_clock(self):
        current_time = datetime.now().strftime("%H:%M:%S")
        self.clock_board.set_text(current_time)
        
    def save_config(self):
        file_name, _ = QFileDialog.getSaveFileName(self, "保存配置", "", "JSON文件 (*.json)")
        if file_name:
            try:
                config = {
                    'text': self.light_board.text,
                    'font_size': self.light_board.font_size,
                    'text_color': {
                        'r': self.light_board.text_color.red(),
                        'g': self.light_board.text_color.green(),
                        'b': self.light_board.text_color.blue()
                    },
                    'bg_color': {
                        'r': self.light_board.bg_color.red(),
                        'g': self.light_board.bg_color.green(),
                        'b': self.light_board.bg_color.blue()
                    },
                    'effect_type': self.light_board.effect_type,
                    'effect_speed': self.light_board.effect_speed,
                    'effect_intensity': self.light_board.effect_intensity
                }
                
                with open(file_name, 'w', encoding='utf-8') as f:
                    json.dump(config, f, indent=4)
                    
                self.statusBar().showMessage("配置保存成功")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"保存配置失败: {e}")
                
    def load_config(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "加载配置", "", "JSON文件 (*.json)")
        if file_name:
            try:
                with open(file_name, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    
                self.light_board.set_text(config.get('text', 'LED'))
                self.light_board.set_font_size(config.get('font_size', 40))
                
                text_color = config.get('text_color', {})
                self.light_board.set_text_color(QColor(
                    text_color.get('r', 0), text_color.get('g', 255), text_color.get('b', 0)
                ))
                
                bg_color = config.get('bg_color', {})
                self.light_board.set_bg_color(QColor(
                    bg_color.get('r', 0), bg_color.get('g', 0), bg_color.get('b', 0)
                ))
                
                self.light_board.set_effect(
                    config.get('effect_type', 0),
                    config.get('effect_speed', 1.0),
                    config.get('effect_intensity', 1.0)
                )
                
                self.statusBar().showMessage("配置加载成功")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"加载配置失败: {e}")
                
    def apply_preset(self, preset_name):
        presets = {
            'rainbow': {
                'effect': EnhancedLightBoardEffect.RAINBOW.value,
                'color': QColor(255, 255, 255),
                'speed': 1.5,
                'intensity': 1.0
            },
            'neon': {
                'effect': EnhancedLightBoardEffect.NEON.value,
                'color': QColor(255, 20, 147),
                'speed': 1.0,
                'intensity': 1.0
            },
            'matrix': {
                'effect': EnhancedLightBoardEffect.MATRIX.value,
                'color': QColor(0, 255, 0),
                'speed': 1.0,
                'intensity': 1.0
            },
            'plasma': {
                'effect': EnhancedLightBoardEffect.PLASMA.value,
                'color': QColor(255, 255, 255),
                'speed': 1.5,
                'intensity': 1.0
            }
        }
        
        if preset_name in presets:
            preset = presets[preset_name]
            self.light_board.set_text_color(preset['color'])
            self.light_board.set_effect(preset['effect'], preset['speed'], preset['intensity'])
            self.statusBar().showMessage(f"已应用 {preset_name} 预设")

# ==================== 应用程序入口 ====================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 设置应用程序样式
    app.setStyle('Fusion')
    
    # 创建并显示主窗口
    demo = EnhancedLightBoardDemo()
    demo.show()
    
    # 应用程序退出时的清理工作
    def cleanup():
        if hasattr(demo, 'network_panel') and demo.network_panel.server:
            demo.network_panel.server.stop()
    
    app.aboutToQuit.connect(cleanup)
    
    sys.exit(app.exec_())