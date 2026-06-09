import sys
import numpy as np
import json
import time
import math
import random
from enum import Enum
from typing import List, Dict, Any, Optional, Tuple, Union

from PyQt5.QtCore import (Qt, QTimer, QPoint, QRectF, QSize, QPropertyAnimation, 
                         QEasingCurve, QTimeLine, QPointF, QDateTime, QSettings,
                         QObject, pyqtSignal)
from PyQt5.QtGui import (QPainter, QColor, QRadialGradient, QConicalGradient, 
                         QLinearGradient, QPainterPath, QBrush, QPen, QPixmap, 
                         QImage, QPolygonF, QFont, QPalette, QKeySequence, QFontMetrics,
                         QPainterPathStroker, QTransform)
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QSlider, 
                             QLabel, QVBoxLayout, QHBoxLayout, QGroupBox,
                             QComboBox, QPushButton, QColorDialog, QSpinBox,
                             QDoubleSpinBox, QCheckBox, QFrame, QTabWidget,
                             QListWidget, QListWidgetItem, QTreeWidget, QTreeWidgetItem,
                             QSplitter, QToolBar, QAction, QStatusBar, QMessageBox,
                             QFileDialog, QDockWidget, QTextEdit, QProgressBar,
                             QTimeEdit, QDial, QScrollArea, QGraphicsView, QGraphicsScene,
                             QGraphicsItem, QMenu, QToolButton, QGridLayout, QLineEdit,
                             QInputDialog, QHeaderView, QSizePolicy, QStyle, QStyleOptionSlider)

# 模拟DMX设备支持
try:
    import serial
    import socket
    DMX_AVAILABLE = True
except ImportError:
    DMX_AVAILABLE = False

# 尝试导入音频处理库
try:
    import pyaudio
    import audioop
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False


class EffectType(Enum):
    """灯光效果类型枚举"""
    RADIAL = 1
    CONICAL = 2
    PARTICLE = 3
    LINEAR = 4
    NOISE = 5
    STROBE = 6
    RAINBOW = 7
    FIRE = 8
    WATER = 9
    MATRIX = 10
    TEXT = 11
    SPOTLIGHT = 12
    LASER = 13
    GOBO = 14
    PRISM = 15


class BlendMode(Enum):
    """混合模式枚举"""
    NORMAL = 1
    ADD = 2
    SUBTRACT = 3
    MULTIPLY = 4
    SCREEN = 5
    OVERLAY = 6
    LIGHTEN = 7
    DARKEN = 8
    DIFFERENCE = 9
    EXCLUSION = 10
    SOURCE_OVER = 11
    PLUS = 12
    COLOR_DODGE = 13
    COLOR_BURN = 14
    HARD_LIGHT = 15
    SOFT_LIGHT = 16


class EasingFunction(Enum):
    """缓动函数枚举"""
    LINEAR = 1
    IN_QUAD = 2
    OUT_QUAD = 3
    IN_OUT_QUAD = 4
    IN_CUBIC = 5
    OUT_CUBIC = 6
    IN_OUT_CUBIC = 7
    IN_QUART = 8
    OUT_QUART = 9
    IN_OUT_QUART = 10
    IN_QUINT = 11
    OUT_QUINT = 12
    IN_OUT_QUINT = 13
    IN_SINE = 14
    OUT_SINE = 15
    IN_OUT_SINE = 16
    IN_EXPO = 17
    OUT_EXPO = 18
    IN_OUT_EXPO = 19
    IN_CIRC = 20
    OUT_CIRC = 21
    IN_OUT_CIRC = 22
    IN_ELASTIC = 23
    OUT_ELASTIC = 24
    IN_OUT_ELASTIC = 25
    IN_BACK = 26
    OUT_BACK = 27
    IN_OUT_BACK = 28
    IN_BOUNCE = 29
    OUT_BOUNCE = 30
    IN_OUT_BOUNCE = 31


class DMXUniverse:
    """DMX宇宙类，用于控制DMX设备"""
    
    def __init__(self, universe_id=1):
        self.universe_id = universe_id
        self.channels = [0] * 512  # DMX有512个通道
        self.devices = {}
        
    def set_channel(self, channel, value):
        """设置DMX通道值"""
        if 1 <= channel <= 512:
            self.channels[channel-1] = max(0, min(255, value))
            
    def get_channel(self, channel):
        """获取DMX通道值"""
        if 1 <= channel <= 512:
            return self.channels[channel-1]
        return 0
    
    def add_device(self, name, start_channel, num_channels, device_type="generic"):
        """添加DMX设备"""
        self.devices[name] = {
            'start': start_channel,
            'num': num_channels,
            'type': device_type,
            'values': [0] * num_channels
        }
        
    def set_device_channel(self, device_name, channel, value):
        """设置设备通道值"""
        if device_name in self.devices:
            device = self.devices[device_name]
            if 1 <= channel <= device['num']:
                device['values'][channel-1] = max(0, min(255, value))
                # 更新到DMX通道
                dmx_channel = device['start'] + channel - 1
                self.set_channel(dmx_channel, value)
                
    def get_device_channel(self, device_name, channel):
        """获取设备通道值"""
        if device_name in self.devices:
            device = self.devices[device_name]
            if 1 <= channel <= device['num']:
                return device['values'][channel-1]
        return 0
    
    def output(self, interface='serial', port='COM1', baudrate=115200):
        """输出DMX信号"""
        if interface == 'serial' and DMX_AVAILABLE:
            try:
                with serial.Serial(port, baudrate, timeout=1) as ser:
                    # DMX协议开始字节
                    ser.write(b'\x7E')
                    # 输出模式 (6 = DMX输出)
                    ser.write(b'\x06')
                    # 数据长度 (LSB and MSB)
                    length = len(self.channels) + 1
                    ser.write(bytes([length & 0xFF]))
                    ser.write(bytes([(length >> 8) & 0xFF]))
                    # DMX开始代码
                    ser.write(b'\x00')
                    # DMX数据
                    ser.write(bytes(self.channels))
                    # 结束字节
                    ser.write(b'\xE7')
            except Exception as e:
                print(f"DMX输出错误: {e}")
        elif interface == 'artnet':
            # 这里可以实现Art-Net协议输出
            pass


class Timeline:
    """时间线类，用于管理动画关键帧"""
    
    def __init__(self):
        self.keyframes = {}  # {property: [(time, value, easing), ...]}
        self.duration = 10.0  # 默认10秒
        self.loop = True
        self.current_time = 0.0
        self.playing = False
        self.speed = 1.0  # 播放速度
        
    def add_keyframe(self, property_name, time, value, easing=EasingFunction.LINEAR):
        """添加关键帧"""
        if property_name not in self.keyframes:
            self.keyframes[property_name] = []
            
        self.keyframes[property_name].append((time, value, easing))
        # 按时间排序
        self.keyframes[property_name].sort(key=lambda x: x[0])
        
    def remove_keyframe(self, property_name, index):
        """移除关键帧"""
        if property_name in self.keyframes and 0 <= index < len(self.keyframes[property_name]):
            del self.keyframes[property_name][index]
            
    def get_value(self, property_name, time):
        """获取属性在指定时间的值"""
        if property_name not in self.keyframes or not self.keyframes[property_name]:
            return None
            
        keyframes = self.keyframes[property_name]
        
        # 如果时间超出范围
        if time <= keyframes[0][0]:
            return keyframes[0][1]
        if time >= keyframes[-1][0]:
            return keyframes[-1][1]
            
        # 找到当前时间所在的关键帧区间
        for i in range(len(keyframes) - 1):
            if keyframes[i][0] <= time <= keyframes[i+1][0]:
                start_time, start_value, start_easing = keyframes[i]
                end_time, end_value, end_easing = keyframes[i+1]
                
                # 计算插值比例
                t = (time - start_time) / (end_time - start_time)
                
                # 应用缓动函数
                t = self.apply_easing(t, start_easing)
                
                # 线性插值
                if isinstance(start_value, (int, float)):
                    return start_value + (end_value - start_value) * t
                elif isinstance(start_value, QColor):
                    # 颜色插值
                    return QColor(
                        int(start_value.red() + (end_value.red() - start_value.red()) * t),
                        int(start_value.green() + (end_value.green() - start_value.green()) * t),
                        int(start_value.blue() + (end_value.blue() - start_value.blue()) * t),
                        int(start_value.alpha() + (end_value.alpha() - start_value.alpha()) * t)
                    )
                elif isinstance(start_value, QPointF):
                    # 点插值
                    return QPointF(
                        start_value.x() + (end_value.x() - start_value.x()) * t,
                        start_value.y() + (end_value.y() - start_value.y()) * t
                    )
                elif isinstance(start_value, list) and len(start_value) == 2:  # 大小/尺寸
                    return [
                        start_value[0] + (end_value[0] - start_value[0]) * t,
                        start_value[1] + (end_value[1] - start_value[1]) * t
                    ]
                
        return None
        
    def apply_easing(self, t, easing):
        """应用缓动函数"""
        if easing == EasingFunction.LINEAR:
            return t
        elif easing == EasingFunction.IN_QUAD:
            return t * t
        elif easing == EasingFunction.OUT_QUAD:
            return t * (2 - t)
        elif easing == EasingFunction.IN_OUT_QUAD:
            if t < 0.5:
                return 2 * t * t
            else:
                return -1 + (4 - 2 * t) * t
        elif easing == EasingFunction.IN_CUBIC:
            return t * t * t
        elif easing == EasingFunction.OUT_CUBIC:
            t -= 1
            return t * t * t + 1
        elif easing == EasingFunction.IN_OUT_CUBIC:
            if t < 0.5:
                return 4 * t * t * t
            else:
                t = 2 * t - 2
                return 0.5 * t * t * t + 1
        elif easing == EasingFunction.IN_QUART:
            return t * t * t * t
        elif easing == EasingFunction.OUT_QUART:
            t -= 1
            return 1 - (t * t * t * t)
        elif easing == EasingFunction.IN_OUT_QUART:
            if t < 0.5:
                return 8 * t * t * t * t
            else:
                t = 2 * t - 2
                return 1 - 0.5 * t * t * t * t
        elif easing == EasingFunction.IN_QUINT:
            return t * t * t * t * t
        elif easing == EasingFunction.OUT_QUINT:
            t -= 1
            return t * t * t * t * t + 1
        elif easing == EasingFunction.IN_OUT_QUINT:
            if t < 0.5:
                return 16 * t * t * t * t * t
            else:
                t = 2 * t - 2
                return 0.5 * t * t * t * t * t + 1
        elif easing == EasingFunction.IN_SINE:
            return 1 - math.cos(t * math.pi / 2)
        elif easing == EasingFunction.OUT_SINE:
            return math.sin(t * math.pi / 2)
        elif easing == EasingFunction.IN_OUT_SINE:
            return 0.5 * (1 - math.cos(math.pi * t))
        elif easing == EasingFunction.IN_EXPO:
            return math.pow(2, 10 * (t - 1)) if t != 0 else 0
        elif easing == EasingFunction.OUT_EXPO:
            return 1 - math.pow(2, -10 * t) if t != 1 else 1
        elif easing == EasingFunction.IN_OUT_EXPO:
            if t == 0 or t == 1:
                return t
            if t < 0.5:
                return 0.5 * math.pow(2, 20 * t - 10)
            else:
                return 1 - 0.5 * math.pow(2, -20 * t + 10)
        elif easing == EasingFunction.IN_CIRC:
            return 1 - math.sqrt(1 - t * t)
        elif easing == EasingFunction.OUT_CIRC:
            t -= 1
            return math.sqrt(1 - t * t)
        elif easing == EasingFunction.IN_OUT_CIRC:
            if t < 0.5:
                return 0.5 * (1 - math.sqrt(1 - 4 * t * t))
            else:
                t = 2 * t - 2
                return 0.5 * (math.sqrt(1 - t * t) + 1)
        else:
            return t  # 默认线性
        
    def update(self, elapsed):
        """更新时间线"""
        if self.playing:
            self.current_time += elapsed / 1000.0 * self.speed  # 转换为秒
            if self.current_time > self.duration:
                if self.loop:
                    self.current_time %= self.duration
                else:
                    self.current_time = self.duration
                    self.playing = False
                    
    def play(self):
        """开始播放"""
        self.playing = True
        
    def pause(self):
        """暂停播放"""
        self.playing = False
        
    def stop(self):
        """停止播放"""
        self.playing = False
        self.current_time = 0.0
        
    def reset(self):
        """重置时间线"""
        self.current_time = 0.0
        
    def set_speed(self, speed):
        """设置播放速度"""
        self.speed = max(0.1, min(10.0, speed))


class LightEffect(QObject):
    """灯光效果基类"""
    
    def __init__(self, name, effect_type):
        super().__init__()
        self.name = name
        self.type = effect_type
        self.enabled = True
        self.opacity = 1.0
        self.blend_mode = BlendMode.NORMAL
        self.timeline = Timeline()
        self.dmx_mapping = {}  # {property: (device, channel)}
        self.audio_sensitivity = 0.0  # 0.0-1.0
        self.audio_attack = 0.1  # 响应速度
        self.audio_release = 0.5  # 释放速度
        self.audio_value = 0.0  # 当前音频值
        self.position = QPointF(0, 0)
        self.rotation = 0.0
        self.scale = 1.0
        self.engine = None  # 将在添加到引擎时设置
        
    def update(self, elapsed, timeline_time, audio_level):
        """更新效果状态"""
        # 更新时间线
        self.timeline.update(elapsed)
        
        # 处理音频响应
        target_audio_value = audio_level * self.audio_sensitivity
        if target_audio_value > self.audio_value:
            # 攻击阶段
            self.audio_value += (target_audio_value - self.audio_value) * self.audio_attack
        else:
            # 释放阶段
            self.audio_value -= (self.audio_value - target_audio_value) * self.audio_release
            
        # 应用时间线到效果属性
        self.apply_timeline(timeline_time)
        
        # 应用DMX映射
        self.apply_dmx_mapping()
        
    def apply_timeline(self, time):
        """应用时间线到效果属性"""
        # 由子类实现具体属性的时间线应用
        pass
        
    def apply_dmx_mapping(self):
        """应用DMX映射"""
        if not self.engine:
            return
            
        for prop, (device, channel) in self.dmx_mapping.items():
            if hasattr(self, prop):
                value = getattr(self, prop)
                # 根据属性类型转换为DMX值
                if isinstance(value, (int, float)):
                    dmx_value = int(value * 255)
                elif isinstance(value, QColor):
                    # 可以选择映射RGB或亮度等
                    dmx_value = int(value.lightness() * 255 / 255)
                elif isinstance(value, QPointF):
                    # 将坐标映射到0-255范围
                    # 这里需要知道坐标的范围，假设为0-1000
                    dmx_value_x = int(max(0, min(255, value.x() * 255 / 1000)))
                    dmx_value_y = int(max(0, min(255, value.y() * 255 / 1000)))
                    # 这里需要两个通道来存储x和y坐标
                    # 简化处理，只使用第一个通道
                    dmx_value = dmx_value_x
                else:
                    dmx_value = 0
                    
                # 设置DMX通道
                self.engine.dmx_universe.set_device_channel(device, channel, dmx_value)
                
    def render(self, painter, rect):
        """渲染效果 - 由子类实现"""
        pass
        
    def set_opacity(self, opacity):
        """设置不透明度"""
        self.opacity = max(0.0, min(1.0, opacity))
        
    def set_blend_mode(self, mode):
        """设置混合模式"""
        self.blend_mode = mode
        
    def set_audio_sensitivity(self, sensitivity):
        """设置音频灵敏度"""
        self.audio_sensitivity = max(0.0, min(1.0, sensitivity))
        
    def set_audio_response(self, attack, release):
        """设置音频响应参数"""
        self.audio_attack = max(0.01, min(1.0, attack))
        self.audio_release = max(0.01, min(1.0, release))
        
    def map_to_dmx(self, property_name, device_name, channel):
        """映射属性到DMX通道"""
        self.dmx_mapping[property_name] = (device_name, channel)
        
    def apply_blend_mode(self, painter):
        """应用混合模式到画家"""
        if self.blend_mode == BlendMode.NORMAL:
            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
        elif self.blend_mode == BlendMode.ADD:
            painter.setCompositionMode(QPainter.CompositionMode_Plus)
        elif self.blend_mode == BlendMode.SUBTRACT:
            painter.setCompositionMode(QPainter.CompositionMode_Difference)
        elif self.blend_mode == BlendMode.MULTIPLY:
            painter.setCompositionMode(QPainter.CompositionMode_Multiply)
        elif self.blend_mode == BlendMode.SCREEN:
            painter.setCompositionMode(QPainter.CompositionMode_Screen)
        elif self.blend_mode == BlendMode.OVERLAY:
            painter.setCompositionMode(QPainter.CompositionMode_Overlay)
        elif self.blend_mode == BlendMode.LIGHTEN:
            painter.setCompositionMode(QPainter.CompositionMode_Lighten)
        elif self.blend_mode == BlendMode.DARKEN:
            painter.setCompositionMode(QPainter.CompositionMode_Darken)
        elif self.blend_mode == BlendMode.DIFFERENCE:
            painter.setCompositionMode(QPainter.CompositionMode_Difference)
        elif self.blend_mode == BlendMode.EXCLUSION:
            painter.setCompositionMode(QPainter.CompositionMode_Exclusion)
        elif self.blend_mode == BlendMode.SOURCE_OVER:
            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
        elif self.blend_mode == BlendMode.PLUS:
            painter.setCompositionMode(QPainter.CompositionMode_Plus)
        elif self.blend_mode == BlendMode.COLOR_DODGE:
            painter.setCompositionMode(QPainter.CompositionMode_ColorDodge)
        elif self.blend_mode == BlendMode.COLOR_BURN:
            painter.setCompositionMode(QPainter.CompositionMode_ColorBurn)
        elif self.blend_mode == BlendMode.HARD_LIGHT:
            painter.setCompositionMode(QPainter.CompositionMode_HardLight)
        elif self.blend_mode == BlendMode.SOFT_LIGHT:
            painter.setCompositionMode(QPainter.CompositionMode_SoftLight)
        
    def serialize(self):
        """序列化效果配置"""
        return {
            'type': self.type.name.lower(),
            'enabled': self.enabled,
            'opacity': self.opacity,
            'blend_mode': self.blend_mode.value,
            'audio_sensitivity': self.audio_sensitivity,
            'audio_attack': self.audio_attack,
            'audio_release': self.audio_release,
            'dmx_mapping': self.dmx_mapping,
            'position': {'x': self.position.x(), 'y': self.position.y()},
            'rotation': self.rotation,
            'scale': self.scale
        }
        
    def deserialize(self, data):
        """从配置数据加载效果"""
        self.enabled = data.get('enabled', True)
        self.opacity = data.get('opacity', 1.0)
        self.blend_mode = BlendMode(data.get('blend_mode', 1))
        self.audio_sensitivity = data.get('audio_sensitivity', 0.0)
        self.audio_attack = data.get('audio_attack', 0.1)
        self.audio_release = data.get('audio_release', 0.5)
        self.dmx_mapping = data.get('dmx_mapping', {})
        position_data = data.get('position', {})
        self.position = QPointF(position_data.get('x', 0), position_data.get('y', 0))
        self.rotation = data.get('rotation', 0.0)
        self.scale = data.get('scale', 1.0)


class RadialLightEffect(LightEffect):
    """径向光效果"""
    
    def __init__(self, name, center=None, radius=100, color=QColor(255, 255, 255)):
        super().__init__(name, EffectType.RADIAL)
        self.center = center or QPointF(0, 0)
        self.radius = radius
        self.color = color
        self.falloff = 1.5  # 衰减系数
        self.pulse_speed = 0.0  # 脉冲速度
        self.pulse_amount = 0.0  # 脉冲幅度
        self.gradient_stops = [(0.0, 1.0), (1.0, 0.0)]  # 渐变停止点 (位置, 透明度)
        
    def update(self, elapsed, timeline_time, audio_level):
        """更新效果状态"""
        super().update(elapsed, timeline_time, audio_level)
        
        # 应用脉冲效果
        if self.pulse_speed > 0:
            pulse = math.sin(timeline_time * self.pulse_speed * 2 * math.pi) * self.pulse_amount
            self.radius += pulse
            
    def apply_timeline(self, time):
        """应用时间线到效果属性"""
        center = self.timeline.get_value("center", time)
        if center is not None:
            self.center = center
            
        radius = self.timeline.get_value("radius", time)
        if radius is not None:
            self.radius = radius
            
        color = self.timeline.get_value("color", time)
        if color is not None:
            self.color = color
            
    def render(self, painter, rect):
        if not self.enabled:
            return
            
        # 保存画家状态
        painter.save()
        
        # 应用变换
        painter.translate(self.position)
        painter.rotate(self.rotation)
        painter.scale(self.scale, self.scale)
            
        # 创建径向渐变
        gradient = QRadialGradient(self.center, self.radius)
        center_color = QColor(self.color)
        
        # 设置渐变停止点
        for pos, alpha in self.gradient_stops:
            color = QColor(center_color)
            color.setAlphaF(alpha * self.opacity)
            
            # 应用音频响应
            if self.audio_sensitivity > 0 and pos == 0.0:  # 只对中心点应用音频响应
                color.setAlphaF(min(1.0, color.alphaF() + self.audio_value))
                
            gradient.setColorAt(pos, color)
        
        # 设置混合模式
        self.apply_blend_mode(painter)
            
        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(self.center, self.radius, self.radius)
        
        # 恢复画家状态
        painter.restore()
        
    def set_gradient_stops(self, stops):
        """设置渐变停止点"""
        self.gradient_stops = stops
        
    def serialize(self):
        """序列化效果配置"""
        data = super().serialize()
        data.update({
            'center': {'x': self.center.x(), 'y': self.center.y()},
            'radius': self.radius,
            'color': {
                'r': self.color.red(),
                'g': self.color.green(),
                'b': self.color.blue(),
                'a': self.color.alpha()
            },
            'falloff': self.falloff,
            'pulse_speed': self.pulse_speed,
            'pulse_amount': self.pulse_amount,
            'gradient_stops': self.gradient_stops
        })
        return data
        
    def deserialize(self, data):
        """从配置数据加载效果"""
        super().deserialize(data)
        center_data = data.get('center', {})
        self.center = QPointF(center_data.get('x', 0), center_data.get('y', 0))
        self.radius = data.get('radius', 100)
        color_data = data.get('color', {})
        self.color = QColor(
            color_data.get('r', 255),
            color_data.get('g', 255),
            color_data.get('b', 255),
            color_data.get('a', 255)
        )
        self.falloff = data.get('falloff', 1.5)
        self.pulse_speed = data.get('pulse_speed', 0.0)
        self.pulse_amount = data.get('pulse_amount', 0.0)
        self.gradient_stops = data.get('gradient_stops', [(0.0, 1.0), (1.0, 0.0)])


class ConicalLightEffect(LightEffect):
    """锥形光效果"""
    
    def __init__(self, name, center=None, angle=0, spread=90, color=QColor(255, 255, 255)):
        super().__init__(name, EffectType.CONICAL)
        self.center = center or QPointF(0, 0)
        self.angle = angle  # 角度 (0-360)
        self.spread = spread  # 扩散角度
        self.color = color
        self.radius = 200
        self.gradient_stops = [(0.0, 1.0), (0.5, 1.0), (1.0, 0.0)]  # 渐变停止点
        
    def update(self, elapsed, timeline_time, audio_level):
        """更新效果状态"""
        super().update(elapsed, timeline_time, audio_level)
        
    def apply_timeline(self, time):
        """应用时间线到效果属性"""
        center = self.timeline.get_value("center", time)
        if center is not None:
            self.center = center
            
        angle = self.timeline.get_value("angle", time)
        if angle is not None:
            self.angle = angle
            
        spread = self.timeline.get_value("spread", time)
        if spread is not None:
            self.spread = spread
            
        color = self.timeline.get_value("color", time)
        if color is not None:
            self.color = color
            
        radius = self.timeline.get_value("radius", time)
        if radius is not None:
            self.radius = radius
            
    def render(self, painter, rect):
        if not self.enabled:
            return
            
        # 保存画家状态
        painter.save()
        
        # 应用变换
        painter.translate(self.position)
        painter.rotate(self.rotation)
        painter.scale(self.scale, self.scale)
            
        # 创建锥形渐变
        gradient = QConicalGradient(self.center, self.angle)
        center_color = QColor(self.color)
        
        # 设置渐变停止点
        for pos, alpha in self.gradient_stops:
            color = QColor(center_color)
            color.setAlphaF(alpha * self.opacity)
            
            # 应用音频响应
            if self.audio_sensitivity > 0 and pos <= 0.5:  # 对前半部分应用音频响应
                color.setAlphaF(min(1.0, color.alphaF() + self.audio_value))
                
            gradient.setColorAt(pos, color)
        
        # 设置混合模式
        self.apply_blend_mode(painter)
            
        # 创建扇形路径
        path = QPainterPath()
        path.moveTo(self.center)
        path.arcTo(QRectF(self.center.x() - self.radius, self.center.y() - self.radius, 
                         self.radius * 2, self.radius * 2), 
                  self.angle - self.spread / 2, self.spread)
        path.closeSubpath()
        
        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.NoPen)
        painter.drawPath(path)
        
        # 恢复画家状态
        painter.restore()
        
    def set_gradient_stops(self, stops):
        """设置渐变停止点"""
        self.gradient_stops = stops
        
    def serialize(self):
        """序列化效果配置"""
        data = super().serialize()
        data.update({
            'center': {'x': self.center.x(), 'y': self.center.y()},
            'angle': self.angle,
            'spread': self.spread,
            'radius': self.radius,
            'color': {
                'r': self.color.red(),
                'g': self.color.green(),
                'b': self.color.blue(),
                'a': self.color.alpha()
            },
            'gradient_stops': self.gradient_stops
        })
        return data
        
    def deserialize(self, data):
        """从配置数据加载效果"""
        super().deserialize(data)
        center_data = data.get('center', {})
        self.center = QPointF(center_data.get('x', 0), center_data.get('y', 0))
        self.angle = data.get('angle', 0)
        self.spread = data.get('spread', 90)
        self.radius = data.get('radius', 200)
        color_data = data.get('color', {})
        self.color = QColor(
            color_data.get('r', 255),
            color_data.get('g', 255),
            color_data.get('b', 255),
            color_data.get('a', 255)
        )
        self.gradient_stops = data.get('gradient_stops', [(0.0, 1.0), (0.5, 1.0), (1.0, 0.0)])


class ParticleLightEffect(LightEffect):
    """粒子光效果"""
    
    def __init__(self, name, count=50):
        super().__init__(name, EffectType.PARTICLE)
        self.particles = []
        self.particle_count = count
        self.area = QRectF(0, 0, 400, 400)
        self.particle_size_range = (2, 10)
        self.particle_speed_range = (0.5, 2.0)
        self.particle_life_range = (1.0, 5.0)
        self.color = QColor(255, 200, 100)
        self.gravity = QPointF(0, 0.1)  # 重力加速度
        self.wind = QPointF(0, 0)  # 风力
        self.attractors = []  # 吸引点列表
        
        self.init_particles()
        
    def init_particles(self):
        """初始化粒子"""
        self.particles = []
        for _ in range(self.particle_count):
            self.add_particle()
            
    def add_particle(self):
        """添加一个新粒子"""
        size = np.random.uniform(*self.particle_size_range)
        speed = np.random.uniform(*self.particle_speed_range)
        life = np.random.uniform(*self.particle_life_range)
        x = np.random.uniform(self.area.left(), self.area.right())
        y = np.random.uniform(self.area.top(), self.area.bottom())
        
        angle = np.random.uniform(0, 2 * np.pi)
        vx = np.cos(angle) * speed
        vy = np.sin(angle) * speed
        
        color = QColor(self.color)
        color.setAlphaF(np.random.uniform(0.3, 0.8))
        
        self.particles.append({
            'x': x, 'y': y,
            'vx': vx, 'vy': vy,
            'size': size,
            'life': life,
            'max_life': life,
            'color': color
        })
        
    def update(self, elapsed, timeline_time, audio_level):
        """更新粒子状态"""
        super().update(elapsed, timeline_time, audio_level)
        
        dt = elapsed / 1000.0  # 转换为秒
        
        for particle in self.particles[:]:
            # 应用重力
            particle['vx'] += self.wind.x() * dt
            particle['vy'] += self.wind.y() * dt
            particle['vx'] += self.gravity.x() * dt
            particle['vy'] += self.gravity.y() * dt
            
            # 应用吸引点
            for attractor in self.attractors:
                dx = attractor['x'] - particle['x']
                dy = attractor['y'] - particle['y']
                dist = max(0.1, math.sqrt(dx*dx + dy*dy))
                force = attractor['strength'] / (dist * dist)
                particle['vx'] += dx / dist * force * dt
                particle['vy'] += dy / dist * force * dt
            
            # 更新位置
            particle['x'] += particle['vx'] * dt
            particle['y'] += particle['vy'] * dt
            
            # 更新生命值
            particle['life'] -= dt
            
            # 如果粒子生命结束或离开区域，重新生成
            if (particle['life'] <= 0 or 
                not self.area.contains(particle['x'], particle['y'])):
                self.particles.remove(particle)
                self.add_particle()
                
    def apply_timeline(self, time):
        """应用时间线到效果属性"""
        # 可以添加时间线控制的属性
        pass
                
    def render(self, painter, rect):
        if not self.enabled:
            return
            
        # 保存画家状态
        painter.save()
        
        # 应用变换
        painter.translate(self.position)
        painter.rotate(self.rotation)
        painter.scale(self.scale, self.scale)
            
        # 设置混合模式
        self.apply_blend_mode(painter)
            
        for particle in self.particles:
            alpha = particle['life'] / particle['max_life'] * self.opacity
            color = QColor(particle['color'])
            color.setAlphaF(alpha)
            
            # 应用音频响应
            if self.audio_sensitivity > 0:
                color.setAlphaF(min(1.0, color.alphaF() + self.audio_value))
            
            painter.setBrush(QBrush(color))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(QPointF(particle['x'], particle['y']), 
                               particle['size'], particle['size'])
        
        # 恢复画家状态
        painter.restore()
        
    def add_attractor(self, x, y, strength=1.0):
        """添加吸引点"""
        self.attractors.append({
            'x': x, 'y': y, 'strength': strength
        })
        
    def clear_attractors(self):
        """清除所有吸引点"""
        self.attractors = []
        
    def serialize(self):
        """序列化效果配置"""
        data = super().serialize()
        data.update({
            'particle_count': self.particle_count,
            'area': {
                'x': self.area.x(), 'y': self.area.y(),
                'width': self.area.width(), 'height': self.area.height()
            },
            'particle_size_range': self.particle_size_range,
            'particle_speed_range': self.particle_speed_range,
            'particle_life_range': self.particle_life_range,
            'color': {
                'r': self.color.red(),
                'g': self.color.green(),
                'b': self.color.blue(),
                'a': self.color.alpha()
            },
            'gravity': {'x': self.gravity.x(), 'y': self.gravity.y()},
            'wind': {'x': self.wind.x(), 'y': self.wind.y()},
            'attractors': self.attractors
        })
        return data
        
    def deserialize(self, data):
        """从配置数据加载效果"""
        super().deserialize(data)
        self.particle_count = data.get('particle_count', 50)
        area_data = data.get('area', {})
        self.area = QRectF(
            area_data.get('x', 0), area_data.get('y', 0),
            area_data.get('width', 400), area_data.get('height', 400)
        )
        self.particle_size_range = data.get('particle_size_range', (2, 10))
        self.particle_speed_range = data.get('particle_speed_range', (0.5, 2.0))
        self.particle_life_range = data.get('particle_life_range', (1.0, 5.0))
        color_data = data.get('color', {})
        self.color = QColor(
            color_data.get('r', 255),
            color_data.get('g', 200),
            color_data.get('b', 100),
            color_data.get('a', 255)
        )
        gravity_data = data.get('gravity', {})
        self.gravity = QPointF(gravity_data.get('x', 0), gravity_data.get('y', 0.1))
        wind_data = data.get('wind', {})
        self.wind = QPointF(wind_data.get('x', 0), wind_data.get('y', 0))
        self.attractors = data.get('attractors', [])
        
        # 重新初始化粒子
        self.init_particles()


class LinearLightEffect(LightEffect):
    """线性光效果"""
    
    def __init__(self, name, start=None, end=None, color=QColor(255, 255, 255), width=10):
        super().__init__(name, EffectType.LINEAR)
        self.start = start or QPointF(0, 0)
        self.end = end or QPointF(100, 0)
        self.color = color
        self.width = width
        self.gradient_stops = [(0.0, 1.0), (1.0, 1.0)]  # 渐变停止点
        
    def update(self, elapsed, timeline_time, audio_level):
        """更新效果状态"""
        super().update(elapsed, timeline_time, audio_level)
        
    def apply_timeline(self, time):
        """应用时间线到效果属性"""
        start = self.timeline.get_value("start", time)
        if start is not None:
            self.start = start
            
        end = self.timeline.get_value("end", time)
        if end is not None:
            self.end = end
            
        color = self.timeline.get_value("color", time)
        if color is not None:
            self.color = color
            
        width = self.timeline.get_value("width", time)
        if width is not None:
            self.width = width
            
    def render(self, painter, rect):
        if not self.enabled:
            return
            
        # 保存画家状态
        painter.save()
        
        # 应用变换
        painter.translate(self.position)
        painter.rotate(self.rotation)
        painter.scale(self.scale, self.scale)
            
        # 创建线性渐变
        gradient = QLinearGradient(self.start, self.end)
        line_color = QColor(self.color)
        
        # 设置渐变停止点
        for pos, alpha in self.gradient_stops:
            color = QColor(line_color)
            color.setAlphaF(alpha * self.opacity)
            
            # 应用音频响应
            if self.audio_sensitivity > 0:
                color.setAlphaF(min(1.0, color.alphaF() + self.audio_value))
                
            gradient.setColorAt(pos, color)
        
        # 设置混合模式
        self.apply_blend_mode(painter)
            
        # 创建路径
        path = QPainterPath()
        path.moveTo(self.start)
        path.lineTo(self.end)
        
        # 使用画笔绘制带宽度的线
        pen = QPen(QBrush(gradient), self.width)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(path)
        
        # 恢复画家状态
        painter.restore()
        
    def set_gradient_stops(self, stops):
        """设置渐变停止点"""
        self.gradient_stops = stops
        
    def serialize(self):
        """序列化效果配置"""
        data = super().serialize()
        data.update({
            'start': {'x': self.start.x(), 'y': self.start.y()},
            'end': {'x': self.end.x(), 'y': self.end.y()},
            'width': self.width,
            'color': {
                'r': self.color.red(),
                'g': self.color.green(),
                'b': self.color.blue(),
                'a': self.color.alpha()
            },
            'gradient_stops': self.gradient_stops
        })
        return data
        
    def deserialize(self, data):
        """从配置数据加载效果"""
        super().deserialize(data)
        start_data = data.get('start', {})
        self.start = QPointF(start_data.get('x', 0), start_data.get('y', 0))
        end_data = data.get('end', {})
        self.end = QPointF(end_data.get('x', 100), end_data.get('y', 0))
        self.width = data.get('width', 10)
        color_data = data.get('color', {})
        self.color = QColor(
            color_data.get('r', 255),
            color_data.get('g', 255),
            color_data.get('b', 255),
            color_data.get('a', 255)
        )
        self.gradient_stops = data.get('gradient_stops', [(0.0, 1.0), (1.0, 1.0)])


class StrobeLightEffect(LightEffect):
    """频闪效果"""
    
    def __init__(self, name, color=QColor(255, 255, 255)):
        super().__init__(name, EffectType.STROBE)
        self.color = color
        self.frequency = 5.0  # 频率 (Hz)
        self.duty_cycle = 0.5  # 占空比 (0.0-1.0)
        self.phase = 0.0  # 相位
        self.is_on = False
        
    def update(self, elapsed, timeline_time, audio_level):
        """更新效果状态"""
        super().update(elapsed, timeline_time, audio_level)
        
        # 计算频闪状态
        period = 1000.0 / self.frequency  # 周期 (ms)
        time_in_period = timeline_time * 1000 % period
        self.is_on = time_in_period < period * self.duty_cycle
        
    def apply_timeline(self, time):
        """应用时间线到效果属性"""
        color = self.timeline.get_value("color", time)
        if color is not None:
            self.color = color
            
        frequency = self.timeline.get_value("frequency", time)
        if frequency is not None:
            self.frequency = frequency
            
        duty_cycle = self.timeline.get_value("duty_cycle", time)
        if duty_cycle is not None:
            self.duty_cycle = duty_cycle
            
    def render(self, painter, rect):
        if not self.enabled or not self.is_on:
            return
            
        # 保存画家状态
        painter.save()
        
        # 应用变换
        painter.translate(self.position)
        painter.rotate(self.rotation)
        painter.scale(self.scale, self.scale)
            
        # 设置颜色
        color = QColor(self.color)
        color.setAlphaF(self.opacity)
        
        # 应用音频响应
        if self.audio_sensitivity > 0:
            color.setAlphaF(min(1.0, color.alphaF() + self.audio_value))
        
        # 设置混合模式
        self.apply_blend_mode(painter)
            
        painter.setBrush(QBrush(color))
        painter.setPen(Qt.NoPen)
        painter.drawRect(rect)
        
        # 恢复画家状态
        painter.restore()
        
    def serialize(self):
        """序列化效果配置"""
        data = super().serialize()
        data.update({
            'color': {
                'r': self.color.red(),
                'g': self.color.green(),
                'b': self.color.blue(),
                'a': self.color.alpha()
            },
            'frequency': self.frequency,
            'duty_cycle': self.duty_cycle,
            'phase': self.phase
        })
        return data
        
    def deserialize(self, data):
        """从配置数据加载效果"""
        super().deserialize(data)
        color_data = data.get('color', {})
        self.color = QColor(
            color_data.get('r', 255),
            color_data.get('g', 255),
            color_data.get('b', 255),
            color_data.get('a', 255)
        )
        self.frequency = data.get('frequency', 5.0)
        self.duty_cycle = data.get('duty_cycle', 0.5)
        self.phase = data.get('phase', 0.0)


class RainbowLightEffect(LightEffect):
    """彩虹效果"""
    
    def __init__(self, name, center=None, radius=100):
        super().__init__(name, EffectType.RAINBOW)
        self.center = center or QPointF(0, 0)
        self.radius = radius
        self.speed = 1.0  # 彩虹旋转速度
        self.saturation = 1.0  # 饱和度
        self.value = 1.0  # 亮度
        self.angle = 0.0  # 当前角度
        
    def update(self, elapsed, timeline_time, audio_level):
        """更新效果状态"""
        super().update(elapsed, timeline_time, audio_level)
        
        # 更新角度
        self.angle += elapsed / 1000.0 * self.speed * 36  # 36度/秒
        
    def apply_timeline(self, time):
        """应用时间线到效果属性"""
        center = self.timeline.get_value("center", time)
        if center is not None:
            self.center = center
            
        radius = self.timeline.get_value("radius", time)
        if radius is not None:
            self.radius = radius
            
        speed = self.timeline.get_value("speed", time)
        if speed is not None:
            self.speed = speed
            
    def render(self, painter, rect):
        if not self.enabled:
            return
            
        # 保存画家状态
        painter.save()
        
        # 应用变换
        painter.translate(self.position)
        painter.rotate(self.rotation)
        painter.scale(self.scale, self.scale)
            
        # 设置混合模式
        self.apply_blend_mode(painter)
            
        # 创建锥形渐变（彩虹）
        gradient = QConicalGradient(self.center, self.angle)
        
        # 添加彩虹颜色
        for i in range(12):
            hue = (i * 30) % 360
            pos = i / 12.0
            color = QColor.fromHsvF(hue / 360.0, self.saturation, self.value, self.opacity)
            gradient.setColorAt(pos, color)
        
        # 应用音频响应
        if self.audio_sensitivity > 0:
            # 增加饱和度响应音频
            saturation = min(1.0, self.saturation + self.audio_value)
            for i in range(12):
                hue = (i * 30) % 360
                pos = i / 12.0
                color = QColor.fromHsvF(hue / 360.0, saturation, self.value, self.opacity)
                gradient.setColorAt(pos, color)
        
        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(self.center, self.radius, self.radius)
        
        # 恢复画家状态
        painter.restore()
        
    def serialize(self):
        """序列化效果配置"""
        data = super().serialize()
        data.update({
            'center': {'x': self.center.x(), 'y': self.center.y()},
            'radius': self.radius,
            'speed': self.speed,
            'saturation': self.saturation,
            'value': self.value
        })
        return data
        
    def deserialize(self, data):
        """从配置数据加载效果"""
        super().deserialize(data)
        center_data = data.get('center', {})
        self.center = QPointF(center_data.get('x', 0), center_data.get('y', 0))
        self.radius = data.get('radius', 100)
        self.speed = data.get('speed', 1.0)
        self.saturation = data.get('saturation', 1.0)
        self.value = data.get('value', 1.0)


class LightEffectEngine:
    """灯光效果引擎"""
    
    def __init__(self):
        self.effects = {}
        self.active_effects = []
        self.global_brightness = 1.0
        self.global_color = QColor(255, 255, 255)
        self.master_timeline = Timeline()
        self.dmx_universe = DMXUniverse()
        self.audio_input = None
        self.audio_level = 0.0
        self.background_color = QColor(0, 0, 0)
        
    def add_effect(self, name, effect):
        """添加效果到引擎"""
        effect.engine = self  # 设置效果对引擎的引用
        self.effects[name] = effect
        
    def remove_effect(self, name):
        """从引擎移除效果"""
        if name in self.effects:
            if name in self.active_effects:
                self.active_effects.remove(name)
            del self.effects[name]
                
    def activate_effect(self, name):
        """激活效果"""
        if name in self.effects and name not in self.active_effects:
            self.active_effects.append(name)
            
    def deactivate_effect(self, name):
        """停用效果"""
        if name in self.active_effects:
            self.active_effects.remove(name)
            
    def render_effects(self, painter, rect):
        """渲染所有激活的效果"""
        # 绘制背景
        painter.fillRect(rect, self.background_color)
        
        # 应用全局亮度和颜色
        painter.setOpacity(self.global_brightness)
        
        for effect_name in self.active_effects:
            effect = self.effects[effect_name]
            if effect.enabled:
                effect.render(painter, rect)
                
    def update_effects(self, elapsed):
        """更新所有效果的状态"""
        # 更新时间线
        self.master_timeline.update(elapsed)
        
        # 应用主时间线到全局属性
        brightness = self.master_timeline.get_value("global_brightness", self.master_timeline.current_time)
        if brightness is not None:
            self.global_brightness = brightness
            
        color = self.master_timeline.get_value("global_color", self.master_timeline.current_time)
        if color is not None:
            self.global_color = color
            
        background_color = self.master_timeline.get_value("background_color", self.master_timeline.current_time)
        if background_color is not None:
            self.background_color = background_color
            
        # 更新所有效果
        for effect_name in self.active_effects:
            effect = self.effects[effect_name]
            effect.update(elapsed, self.master_timeline.current_time, self.audio_level)
            
    def set_global_brightness(self, brightness):
        """设置全局亮度"""
        self.global_brightness = max(0.0, min(1.0, brightness))
        
    def set_global_color(self, color):
        """设置全局颜色"""
        self.global_color = color
        
    def set_background_color(self, color):
        """设置背景颜色"""
        self.background_color = color
        
    def save_config(self, filename):
        """保存配置到文件"""
        config = {
            'global_brightness': self.global_brightness,
            'global_color': {
                'r': self.global_color.red(),
                'g': self.global_color.green(),
                'b': self.global_color.blue(),
                'a': self.global_color.alpha()
            },
            'background_color': {
                'r': self.background_color.red(),
                'g': self.background_color.green(),
                'b': self.background_color.blue(),
                'a': self.background_color.alpha()
            },
            'effects': {},
            'active_effects': self.active_effects,
            'timeline': {
                'duration': self.master_timeline.duration,
                'loop': self.master_timeline.loop,
                'playing': self.master_timeline.playing,
                'speed': self.master_timeline.speed,
                'keyframes': {}
            },
            'dmx_universe': {
                'devices': self.dmx_universe.devices
            }
        }
        
        # 保存效果配置
        for name, effect in self.effects.items():
            config['effects'][name] = effect.serialize()
            
        # 保存时间线关键帧
        for prop, keyframes in self.master_timeline.keyframes.items():
            config['timeline']['keyframes'][prop] = []
            for time, value, easing in keyframes:
                frame_data = {'time': time, 'easing': easing.value}
                
                if isinstance(value, (int, float)):
                    frame_data['value'] = value
                    frame_data['type'] = 'number'
                elif isinstance(value, QColor):
                    frame_data['value'] = {
                        'r': value.red(),
                        'g': value.green(),
                        'b': value.blue(),
                        'a': value.alpha()
                    }
                    frame_data['type'] = 'color'
                elif isinstance(value, QPointF):
                    frame_data['value'] = {
                        'x': value.x(),
                        'y': value.y()
                    }
                    frame_data['type'] = 'point'
                elif isinstance(value, list) and len(value) == 2:
                    frame_data['value'] = {
                        'w': value[0],
                        'h': value[1]
                    }
                    frame_data['type'] = 'size'
                    
                config['timeline']['keyframes'][prop].append(frame_data)
                
        with open(filename, 'w') as f:
            json.dump(config, f, indent=4)
            
    def load_config(self, filename):
        """从文件加载配置"""
        try:
            with open(filename, 'r') as f:
                config = json.load(f)
                
            self.global_brightness = config.get('global_brightness', 1.0)
            color_data = config.get('global_color', {})
            self.global_color = QColor(
                color_data.get('r', 255),
                color_data.get('g', 255),
                color_data.get('b', 255),
                color_data.get('a', 255)
            )
            
            bg_color_data = config.get('background_color', {})
            self.background_color = QColor(
                bg_color_data.get('r', 0),
                bg_color_data.get('g', 0),
                bg_color_data.get('b', 0),
                bg_color_data.get('a', 255)
            )
            
            # 清除现有效果
            self.effects.clear()
            self.active_effects.clear()
            
            # 加载效果
            effects_data = config.get('effects', {})
            for name, effect_data in effects_data.items():
                effect_type = effect_data.get('type')
                if effect_type == 'radial':
                    effect = RadialLightEffect(name)
                elif effect_type == 'conical':
                    effect = ConicalLightEffect(name)
                elif effect_type == 'particle':
                    effect = ParticleLightEffect(name)
                elif effect_type == 'linear':
                    effect = LinearLightEffect(name)
                elif effect_type == 'strobe':
                    effect = StrobeLightEffect(name)
                elif effect_type == 'rainbow':
                    effect = RainbowLightEffect(name)
                else:
                    continue
                    
                effect.deserialize(effect_data)
                self.add_effect(name, effect)
                
            # 激活效果
            self.active_effects = config.get('active_effects', [])
            
            # 加载时间线
            timeline_data = config.get('timeline', {})
            self.master_timeline.duration = timeline_data.get('duration', 10.0)
            self.master_timeline.loop = timeline_data.get('loop', True)
            self.master_timeline.playing = timeline_data.get('playing', False)
            self.master_timeline.speed = timeline_data.get('speed', 1.0)
            
            keyframes_data = timeline_data.get('keyframes', {})
            for prop, frames_data in keyframes_data.items():
                for frame_data in frames_data:
                    time = frame_data.get('time', 0)
                    easing = EasingFunction(frame_data.get('easing', 1))
                    value_data = frame_data.get('value', {})
                    value_type = frame_data.get('type', 'number')
                    
                    if value_type == 'number':
                        value = value_data
                    elif value_type == 'color':
                        value = QColor(
                            value_data.get('r', 255),
                            value_data.get('g', 255),
                            value_data.get('b', 255),
                            value_data.get('a', 255)
                        )
                    elif value_type == 'point':
                        value = QPointF(
                            value_data.get('x', 0),
                            value_data.get('y', 0)
                        )
                    elif value_type == 'size':
                        value = [
                            value_data.get('w', 0),
                            value_data.get('h', 0)
                        ]
                        
                    self.master_timeline.add_keyframe(prop, time, value, easing)
                    
            # 加载DMX设备
            dmx_data = config.get('dmx_universe', {})
            devices_data = dmx_data.get('devices', {})
            for name, device_data in devices_data.items():
                self.dmx_universe.add_device(
                    name,
                    device_data.get('start', 1),
                    device_data.get('num', 1),
                    device_data.get('type', 'generic')
                )
                    
            return True
        except Exception as e:
            print(f"加载配置错误: {e}")
            return False


# 由于篇幅限制，这里只实现了部分效果类
# 实际应用中需要实现所有效果类型

# 音频输入处理类
class AudioInput(QObject):
    """音频输入处理类"""
    
    level_updated = pyqtSignal(float)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.audio = None
        self.stream = None
        self.rate = 44100
        self.chunk = 1024
        self.running = False
        
    def start(self, device_index=None):
        """开始音频输入"""
        if not AUDIO_AVAILABLE:
            return False
            
        try:
            self.audio = pyaudio.PyAudio()
            
            # 获取设备信息
            device_info = None
            if device_index is not None:
                device_info = self.audio.get_device_info_by_index(device_index)
            
            # 打开音频流
            self.stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=self.rate,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=self.chunk,
                stream_callback=self.audio_callback
            )
            
            self.running = True
            self.stream.start_stream()
            return True
        except Exception as e:
            print(f"音频输入错误: {e}")
            return False
            
    def stop(self):
        """停止音频输入"""
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None
            
        if self.audio:
            self.audio.terminate()
            self.audio = None
            
        self.running = False
            
    def audio_callback(self, in_data, frame_count, time_info, status):
        """音频回调函数"""
        if self.running:
            # 计算音频电平
            level = audioop.rms(in_data, 2) / 32768.0
            self.level_updated.emit(level)
            
        return (in_data, pyaudio.paContinue)
        
    def get_available_devices(self):
        """获取可用音频设备"""
        if not AUDIO_AVAILABLE:
            return []
            
        devices = []
        try:
            audio = pyaudio.PyAudio()
            for i in range(audio.get_device_count()):
                info = audio.get_device_info_by_index(i)
                if info.get('maxInputChannels', 0) > 0:
                    devices.append((i, info.get('name', f'Device {i}')))
            audio.terminate()
        except:
            pass
            
        return devices


# 由于篇幅限制，UI部分代码将在此处省略
# 实际应用中需要实现完整的用户界面

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 创建引擎
    engine = LightEffectEngine()
    
    # 添加一些示例效果
    radial_effect = RadialLightEffect("Radial1", QPointF(200, 200), 100, QColor(255, 100, 100))
    engine.add_effect("radial1", radial_effect)
    engine.activate_effect("radial1")
    
    conical_effect = ConicalLightEffect("Conical1", QPointF(400, 200), 45, 90, QColor(100, 255, 100))
    engine.add_effect("conical1", conical_effect)
    engine.activate_effect("conical1")
    
    particle_effect = ParticleLightEffect("Particles1", 50)
    particle_effect.area = QRectF(0, 0, 600, 400)
    engine.add_effect("particles1", particle_effect)
    engine.activate_effect("particles1")
    
    # 创建显示窗口
    class PreviewWindow(QWidget):
        def __init__(self, engine, parent=None):
            super().__init__(parent)
            self.engine = engine
            self.timer = QTimer(self)
            self.last_time = 0
            self.fps = 0
            self.frame_count = 0
            self.fps_time = 0
            
            self.setWindowTitle("灯光效果预览")
            self.setGeometry(100, 100, 800, 600)
            
            self.timer.timeout.connect(self.update_animation)
            self.timer.start(16)  # 约60FPS
            
        def update_animation(self):
            current_time = QDateTime.currentMSecsSinceEpoch()
            elapsed = current_time - self.last_time if self.last_time > 0 else 0
            self.last_time = current_time
            
            # 计算FPS
            self.frame_count += 1
            if current_time - self.fps_time >= 1000:
                self.fps = self.frame_count
                self.frame_count = 0
                self.fps_time = current_time
                
            self.engine.update_effects(elapsed)
            self.update()
            
        def paintEvent(self, event):
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            
            self.engine.render_effects(painter, self.rect())
            
            # 显示FPS
            painter.setPen(Qt.white)
            painter.drawText(10, 20, f"FPS: {self.fps}")
            
    window = PreviewWindow(engine)
    window.show()
    
    sys.exit(app.exec_())