import sys
import math
import json
import datetime
import numpy as np
from PyQt5.QtCore import (Qt, QPoint, QPointF, QRectF, QSize, QTimer, 
                         QDateTime, QPropertyAnimation, QEasingCurve,
                         pyqtSignal, pyqtProperty, QVariantAnimation)
from PyQt5.QtGui import (QColor, QConicalGradient, QFont, QFontMetrics, 
                        QLinearGradient, QPainter, QPainterPath, QPalette, 
                        QPen, QRadialGradient, QBrush, QPolygonF, QIcon)
from PyQt5.QtWidgets import (QApplication, QDoubleSpinBox, QFormLayout, 
                            QGridLayout, QGroupBox, QHBoxLayout, QLabel, 
                            QMainWindow, QSlider, QVBoxLayout, QWidget, 
                            QSizePolicy, QCheckBox, QComboBox, QPushButton,
                            QTabWidget, QTextEdit, QListView, QListWidget,
                            QListWidgetItem, QSplitter, QToolBar, QStatusBar,
                            QAction, QMenu, QFileDialog, QMessageBox, QDialog,
                            QProgressBar, QDial, QSpinBox, QLineEdit)

# 数据记录器类
class DataLogger:
    def __init__(self, max_records=1000):
        self.max_records = max_records
        self.data = {}
        self.timestamps = []
        
    def log_data(self, name, value, timestamp=None):
        if timestamp is None:
            timestamp = datetime.datetime.now()
            
        if name not in self.data:
            self.data[name] = []
            
        self.data[name].append((timestamp, value))
        self.timestamps.append(timestamp)
        
        # 保持数据量不超过最大值
        if len(self.timestamps) > self.max_records:
            oldest = self.timestamps.pop(0)
            for name in self.data:
                if self.data[name] and self.data[name][0][0] == oldest:
                    self.data[name].pop(0)
                    
    def get_data(self, name, start_time=None, end_time=None):
        if name not in self.data:
            return []
            
        if start_time is None and end_time is None:
            return self.data[name]
            
        result = []
        for timestamp, value in self.data[name]:
            if start_time and timestamp < start_time:
                continue
            if end_time and timestamp > end_time:
                continue
            result.append((timestamp, value))
            
        return result
        
    def export_to_json(self, filename):
        export_data = {}
        for name in self.data:
            export_data[name] = [(ts.isoformat(), value) for ts, value in self.data[name]]
            
        with open(filename, 'w') as f:
            json.dump(export_data, f, indent=2)
            
    def import_from_json(self, filename):
        with open(filename, 'r') as f:
            import_data = json.load(f)
            
        for name in import_data:
            for ts_str, value in import_data[name]:
                timestamp = datetime.datetime.fromisoformat(ts_str)
                self.log_data(name, value, timestamp)

# 报警系统类
class AlarmSystem:
    def __init__(self):
        self.alarms = []
        self.triggered_alarms = []
        
    class Alarm:
        def __init__(self, name, condition, threshold, severity="warning", message=""):
            self.name = name
            self.condition = condition  # ">", "<", "==", "!=", ">=", "<="
            self.threshold = threshold
            self.severity = severity  # "info", "warning", "error", "critical"
            self.message = message
            self.triggered = False
            self.trigger_time = None
            
        def check(self, value):
            result = False
            if self.condition == ">":
                result = value > self.threshold
            elif self.condition == "<":
                result = value < self.threshold
            elif self.condition == "==":
                result = value == self.threshold
            elif self.condition == "!=":
                result = value != self.threshold
            elif self.condition == ">=":
                result = value >= self.threshold
            elif self.condition == "<=":
                result = value <= self.threshold
                
            # 状态变化检测
            if result and not self.triggered:
                self.triggered = True
                self.trigger_time = datetime.datetime.now()
                return True, self
            elif not result and self.triggered:
                self.triggered = False
                return True, self
                
            return False, self
            
    def add_alarm(self, name, condition, threshold, severity="warning", message=""):
        alarm = self.Alarm(name, condition, threshold, severity, message)
        self.alarms.append(alarm)
        return alarm
        
    def check_value(self, name, value):
        triggered = []
        for alarm in self.alarms:
            if alarm.name == name:
                changed, alarm_obj = alarm.check(value)
                if changed:
                    triggered.append(alarm_obj)
                    if alarm_obj.triggered:
                        self.triggered_alarms.append(alarm_obj)
                    else:
                        # 移除已解决的报警
                        self.triggered_alarms = [a for a in self.triggered_alarms if a != alarm_obj]
                        
        return triggered
        
    def get_active_alarms(self):
        return [a for a in self.alarms if a.triggered]
        
    def acknowledge_alarm(self, alarm):
        if alarm in self.triggered_alarms:
            self.triggered_alarms.remove(alarm)

# 主题管理器
class ThemeManager:
    themes = {
        "Dark": {
            "background": QColor(40, 40, 40),
            "foreground": QColor(200, 200, 200),
            "primary": QColor(50, 150, 250),
            "secondary": QColor(100, 100, 100),
            "accent": QColor(142, 45, 197),
            "text": QColor(255, 255, 255),
            "warning": QColor(255, 170, 0),
            "error": QColor(255, 0, 0),
            "success": QColor(0, 200, 0)
        },
        "Light": {
            "background": QColor(240, 240, 240),
            "foreground": QColor(50, 50, 50),
            "primary": QColor(0, 120, 215),
            "secondary": QColor(200, 200, 200),
            "accent": QColor(142, 45, 197),
            "text": QColor(0, 0, 0),
            "warning": QColor(255, 170, 0),
            "error": QColor(255, 0, 0),
            "success": QColor(0, 150, 0)
        },
        "Blue": {
            "background": QColor(30, 40, 60),
            "foreground": QColor(180, 190, 210),
            "primary": QColor(0, 150, 255),
            "secondary": QColor(60, 80, 100),
            "accent": QColor(255, 170, 0),
            "text": QColor(240, 240, 240),
            "warning": QColor(255, 170, 0),
            "error": QColor(255, 80, 80),
            "success": QColor(0, 200, 0)
        }
    }
    
    def __init__(self):
        self.current_theme = "Dark"
        
    def get_theme(self, name=None):
        if name is None:
            name = self.current_theme
        return self.themes.get(name, self.themes["Dark"])
        
    def set_theme(self, name):
        if name in self.themes:
            self.current_theme = name
            return True
        return False
        
    def get_theme_names(self):
        return list(self.themes.keys())

# 基础仪表控件
class GaugeWidget(QWidget):
    valueChanged = pyqtSignal(float)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._min_value = 0.0
        self._max_value = 100.0
        self._value = 0.0
        self._precision = 1
        self._units = "°C"
        self._scale_angle = 270
        self._start_angle = 135
        self._thresholds = []  # 多个阈值 [(value, color, name), ...]
        self._value_color = QColor(50, 150, 250)
        self._normal_color = QColor(100, 100, 100)
        self._text_color = QColor(255, 255, 255)
        self._backgroundColor = QColor(40, 40, 40)
        
        # 动画
        self._animation = QVariantAnimation(self)
        self._animation.valueChanged.connect(self._update_animated_value)
        self._animation.setEasingCurve(QEasingCurve.OutCubic)
        self._animation.setDuration(500)  # 500ms 动画
        
        # 主题
        self.theme_manager = ThemeManager()
        
        self.setMinimumSize(150, 150)
        
    def sizeHint(self):
        return QSize(300, 300)
        
    def setRange(self, min_val, max_val):
        self._min_value = min_val
        self._max_value = max_val
        if self._value < min_val:
            self._value = min_val
        elif self._value > max_val:
            self._value = max_val
        self.update()
        
    def setValue(self, value):
        if value < self._min_value:
            value = self._min_value
        elif value > self._max_value:
            value = self._max_value
            
        if value != self._value:
            self._value = value
            self.valueChanged.emit(value)
            self.update()
            
    def setAnimatedValue(self, value):
        """设置带动画的值"""
        target_value = max(self._min_value, min(self._max_value, value))
        if target_value != self._value:
            self._animation.stop()
            self._animation.setStartValue(self._value)
            self._animation.setEndValue(target_value)
            self._animation.start()
            
    def _update_animated_value(self, value):
        if value is not None:  # 添加 None 检查
            self._value = value
            self.valueChanged.emit(value)
            self.update()
        
    def setPrecision(self, precision):
        self._precision = precision
        self.update()
        
    def setUnits(self, units):
        self._units = units
        self.update()
        
    def addThreshold(self, value, color, name=""):
        self._thresholds.append((value, color, name))
        self.update()
        
    def clearThresholds(self):
        self._thresholds = []
        self.update()
        
    def setValueColor(self, color):
        self._value_color = color
        self.update()
        
    def setNormalColor(self, color):
        self._normal_color = color
        self.update()
        
    def setTextColor(self, color):
        self._text_color = color
        self.update()
        
    def setBackgroundColor(self, color):
        self._backgroundColor = color
        self.update()
        
    def setScaleAngle(self, angle):
        self._scale_angle = angle
        self.update()
        
    def setStartAngle(self, angle):
        self._start_angle = angle
        self.update()
        
    def applyTheme(self, theme_name):
        theme = self.theme_manager.get_theme(theme_name)
        self.setBackgroundColor(theme["background"])
        self.setNormalColor(theme["secondary"])
        self.setValueColor(theme["primary"])
        self.setTextColor(theme["text"])
        
    def getValue(self):
        return self._value
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        side = min(self.width(), self.height())
        center = QPointF(self.width() / 2, self.height() / 2)
        radius = side / 2 - 10
        
        self.drawBackground(painter, center, radius)
        self.drawTicks(painter, center, radius)
        self.drawThresholdArcs(painter, center, radius)
        self.drawValueArc(painter, center, radius)
        self.drawNeedle(painter, center, radius)
        self.drawText(painter, center, radius)
        
    def drawBackground(self, painter, center, radius):
        painter.setPen(QPen(self._normal_color, 2))
        gradient = QRadialGradient(center, radius, center)
        gradient.setColorAt(0, self._backgroundColor.lighter(120))
        gradient.setColorAt(1, self._backgroundColor.darker(120))
        painter.setBrush(gradient)
        painter.drawEllipse(center, radius, radius)
        
        inner_radius = radius * 0.7
        painter.setPen(Qt.NoPen)
        inner_gradient = QRadialGradient(center, inner_radius, center)
        inner_gradient.setColorAt(0, self._backgroundColor.lighter(150))
        inner_gradient.setColorAt(1, self._backgroundColor.darker(150))
        painter.setBrush(inner_gradient)
        painter.drawEllipse(center, inner_radius, inner_radius)
        
    def drawTicks(self, painter, center, radius):
        painter.save()
        painter.setPen(QPen(self._normal_color, 1))
        
        for i in range(0, 11):
            angle = self._start_angle + (i / 10) * self._scale_angle
            start_point = center + QPointF(
                (radius - 10) * math.cos(math.radians(angle)),
                (radius - 10) * math.sin(math.radians(angle))
            )
            end_point = center + QPointF(
                radius * math.cos(math.radians(angle)),
                radius * math.sin(math.radians(angle))
            )
            painter.drawLine(start_point, end_point)
            
            value = self._min_value + (i / 10) * (self._max_value - self._min_value)
            text_point = center + QPointF(
                (radius - 25) * math.cos(math.radians(angle)),
                (radius - 25) * math.sin(math.radians(angle))
            )
            painter.save()
            painter.translate(text_point)
            painter.rotate(angle + 90)
            font = QFont("Arial", max(8, int(radius / 20)))
            painter.setFont(font)
            painter.setPen(QPen(self._text_color))
            text_rect = QRectF(-20, -10, 40, 20)
            painter.drawText(text_rect, Qt.AlignCenter, f"{value:.0f}")
            painter.restore()
        
        for i in range(0, 51):
            if i % 5 == 0:
                continue
            angle = self._start_angle + (i / 50) * self._scale_angle
            start_point = center + QPointF(
                (radius - 5) * math.cos(math.radians(angle)),
                (radius - 5) * math.sin(math.radians(angle))
            )
            end_point = center + QPointF(
                radius * math.cos(math.radians(angle)),
                radius * math.sin(math.radians(angle))
            )
            painter.drawLine(start_point, end_point)
            
        painter.restore()
        
    def drawThresholdArcs(self, painter, center, radius):
        if not self._thresholds:
            return
            
        painter.save()
        
        # 按阈值排序
        sorted_thresholds = sorted(self._thresholds, key=lambda x: x[0])
        
        # 绘制每个阈值弧
        for i, (threshold, color, name) in enumerate(sorted_thresholds):
            if threshold <= self._min_value or threshold >= self._max_value:
                continue
                
            threshold_ratio = (threshold - self._min_value) / (self._max_value - self._min_value)
            threshold_angle = self._start_angle + threshold_ratio * self._scale_angle
            
            pen = QPen(color, 4)
            pen.setCapStyle(Qt.RoundCap)
            painter.setPen(pen)
            
            arc_rect = QRectF(center.x() - radius, center.y() - radius, 
                             radius * 2, radius * 2)
            
            # 确定弧的起始角度
            if i == 0:
                start_angle = self._start_angle
            else:
                prev_threshold = sorted_thresholds[i-1][0]
                prev_ratio = (prev_threshold - self._min_value) / (self._max_value - self._min_value)
                start_angle = self._start_angle + prev_ratio * self._scale_angle
                
            # 绘制弧
            painter.drawArc(arc_rect, 
                           int(start_angle * 16), 
                           int((threshold_angle - start_angle) * 16))
        
        painter.restore()
        
    def drawValueArc(self, painter, center, radius):
        painter.save()
        
        value_ratio = (self._value - self._min_value) / (self._max_value - self._min_value)
        value_angle = self._start_angle + value_ratio * self._scale_angle
        
        # 确定值的颜色（基于阈值）
        value_color = self._value_color
        for threshold, color, name in self._thresholds:
            if self._value >= threshold:
                value_color = color
                
        pen = QPen(value_color, 6)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        
        arc_rect = QRectF(center.x() - radius, center.y() - radius, 
                         radius * 2, radius * 2)
        
        painter.drawArc(arc_rect, 
                       int(self._start_angle * 16), 
                       int((value_angle - self._start_angle) * 16))
        
        painter.restore()
        
    def drawNeedle(self, painter, center, radius):
        painter.save()
        
        value_ratio = (self._value - self._min_value) / (self._max_value - self._min_value)
        angle = self._start_angle + value_ratio * self._scale_angle
        
        # 确定指针颜色
        needle_color = self._value_color
        for threshold, color, name in self._thresholds:
            if self._value >= threshold:
                needle_color = color
                
        painter.setPen(QPen(needle_color, 2))
        painter.setBrush(needle_color)
        
        painter.translate(center)
        painter.rotate(angle)
        
        needle_length = radius * 0.8
        needle_width = max(2, radius * 0.03)
        
        needle_path = QPainterPath()
        needle_path.moveTo(0, 0)
        needle_path.lineTo(-needle_width, -needle_width)
        needle_path.lineTo(needle_length, 0)
        needle_path.lineTo(-needle_width, needle_width)
        needle_path.closeSubpath()
        
        painter.drawPath(needle_path)
        
        painter.setPen(Qt.NoPen)
        painter.setBrush(self._backgroundColor)
        painter.drawEllipse(QPointF(0, 0), needle_width * 2, needle_width * 2)
        
        painter.setPen(QPen(needle_color, 1))
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(QPointF(0, 0), needle_width * 2, needle_width * 2)
        
        painter.restore()
        
    def drawText(self, painter, center, radius):
        painter.save()
        
        font = QFont("Arial", max(10, int(radius / 10)))
        painter.setFont(font)
        painter.setPen(QPen(self._text_color))
        
        value_text = f"{self._value:.{self._precision}f}"
        value_rect = QRectF(center.x() - radius * 0.5, 
                           center.y() + radius * 0.2, 
                           radius, radius * 0.3)
        painter.drawText(value_rect, Qt.AlignCenter, value_text)
        
        if self._units:
            units_font = QFont("Arial", max(8, int(radius / 15)))
            painter.setFont(units_font)
            units_rect = QRectF(center.x() - radius * 0.5, 
                               center.y() + radius * 0.5, 
                               radius, radius * 0.2)
            painter.drawText(units_rect, Qt.AlignCenter, self._units)
            
        painter.restore()

# 半圆仪表
class SemiCircularGauge(GaugeWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setScaleAngle(180)
        self.setStartAngle(180)
        
    def drawBackground(self, painter, center, radius):
        # 只绘制下半圆
        painter.setPen(QPen(self._normal_color, 2))
        gradient = QRadialGradient(center, radius, center)
        gradient.setColorAt(0, self._backgroundColor.lighter(120))
        gradient.setColorAt(1, self._backgroundColor.darker(120))
        painter.setBrush(gradient)
        
        path = QPainterPath()
        path.moveTo(center.x() - radius, center.y())
        path.arcTo(center.x() - radius, center.y() - radius, 
                  radius * 2, radius * 2, 180, 180)
        path.lineTo(center.x() + radius, center.y())
        path.closeSubpath()
        painter.drawPath(path)
        
        # 内圆
        inner_radius = radius * 0.7
        painter.setPen(Qt.NoPen)
        inner_gradient = QRadialGradient(center, inner_radius, center)
        inner_gradient.setColorAt(0, self._backgroundColor.lighter(150))
        inner_gradient.setColorAt(1, self._backgroundColor.darker(150))
        painter.setBrush(inner_gradient)
        
        inner_path = QPainterPath()
        inner_path.moveTo(center.x() - inner_radius, center.y())
        inner_path.arcTo(center.x() - inner_radius, center.y() - inner_radius, 
                        inner_radius * 2, inner_radius * 2, 180, 180)
        inner_path.lineTo(center.x() + inner_radius, center.y())
        inner_path.closeSubpath()
        painter.drawPath(inner_path)

# 线性仪表
class LinearGaugeWidget(QWidget):
    valueChanged = pyqtSignal(float)
    
    def __init__(self, orientation=Qt.Horizontal, parent=None):
        super().__init__(parent)
        self._min_value = 0.0
        self._max_value = 100.0
        self._value = 0.0
        self._precision = 1
        self._units = "%"
        self._orientation = orientation
        self._thresholds = []
        self._value_color = QColor(50, 150, 250)
        self._normal_color = QColor(100, 100, 100)
        self._text_color = QColor(255, 255, 255)
        self._backgroundColor = QColor(40, 40, 40)
        
        self._animation = QVariantAnimation(self)
        self._animation.valueChanged.connect(self._update_animated_value)
        self._animation.setEasingCurve(QEasingCurve.OutCubic)
        self._animation.setDuration(500)
        
        self.theme_manager = ThemeManager()
        
        self.setMinimumSize(100, 30)
    
    def setUnits(self, units):
        self._units = units
        self.update()
        
    def setPrecision(self, precision):
        self._precision = precision
        self.update()

    def setRange(self, min_val, max_val):
        self._min_value = min_val
        self._max_value = max_val
        if self._value < min_val:
            self._value = min_val
        elif self._value > max_val:
            self._value = max_val
        self.update()
        
    def setValue(self, value):
        if value < self._min_value:
            value = self._min_value
        elif value > self._max_value:
            value = self._max_value
            
        if value != self._value:
            self._value = value
            self.valueChanged.emit(value)
            self.update()
            
    def setAnimatedValue(self, value):
        target_value = max(self._min_value, min(self._max_value, value))
        if target_value != self._value:
            self._animation.stop()
            self._animation.setStartValue(self._value)
            self._animation.setEndValue(target_value)
            self._animation.start()
            
    def _update_animated_value(self, value):
        if value is not None:  # 添加 None 检查
            self._value = value
            self.valueChanged.emit(value)
            self.update()
        
    def addThreshold(self, value, color, name=""):
        self._thresholds.append((value, color, name))
        self.update()
        
    def clearThresholds(self):
        self._thresholds = []
        self.update()
        
    def applyTheme(self, theme_name):
        theme = self.theme_manager.get_theme(theme_name)
        self.setBackgroundColor(theme["background"])
        self.setNormalColor(theme["secondary"])
        self.setValueColor(theme["primary"])
        self.setTextColor(theme["text"])
        
    def setBackgroundColor(self, color):
        self._backgroundColor = color
        self.update()
        
    def setNormalColor(self, color):
        self._normal_color = color
        self.update()
        
    def setValueColor(self, color):
        self._value_color = color
        self.update()
        
    def setTextColor(self, color):
        self._text_color = color
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        rect = self.rect().adjusted(2, 2, -2, -2)
        
        self.drawBackground(painter, rect)
        self.drawTicks(painter, rect)
        self.drawValueBar(painter, rect)
        self.drawText(painter, rect)
        
    def drawBackground(self, painter, rect):
        painter.save()
        
        painter.setPen(Qt.NoPen)
        painter.setBrush(self._backgroundColor)
        painter.drawRoundedRect(rect, 3, 3)
        
        painter.setPen(QPen(self._normal_color, 1))
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(rect, 3, 3)
        
        painter.restore()
        
    def drawTicks(self, painter, rect):
        painter.save()
        painter.setPen(QPen(self._normal_color, 1))
        
        if self._orientation == Qt.Horizontal:
            for i in range(0, 11):
                x = rect.left() + (i / 10) * rect.width()
                painter.drawLine(QPointF(x, rect.bottom() - 5), QPointF(x, rect.bottom()))
                
                value = self._min_value + (i / 10) * (self._max_value - self._min_value)
                painter.drawText(QRectF(x - 20, rect.top(), 40, 15), 
                                Qt.AlignCenter, f"{value:.0f}")
                
                # 绘制阈值标记
                for threshold, color, name in self._thresholds:
                    threshold_ratio = (threshold - self._min_value) / (self._max_value - self._min_value)
                    threshold_x = rect.left() + threshold_ratio * rect.width()
                    painter.setPen(QPen(color, 2))
                    painter.drawLine(QPointF(threshold_x, rect.top() - 2), QPointF(threshold_x, rect.bottom() + 2))
                    painter.setPen(QPen(self._normal_color, 1))
        else:
            for i in range(0, 11):
                y = rect.bottom() - (i / 10) * rect.height()
                painter.drawLine(QPointF(rect.left(), y), QPointF(rect.left() + 5, y))
                
                value = self._min_value + (i / 10) * (self._max_value - self._min_value)
                painter.drawText(QRectF(rect.left() - 30, y - 10, 30, 20), 
                                Qt.AlignRight | Qt.AlignVCenter, f"{value:.0f}")
                
                # 绘制阈值标记
                for threshold, color, name in self._thresholds:
                    threshold_ratio = (threshold - self._min_value) / (self._max_value - self._min_value)
                    threshold_y = rect.bottom() - threshold_ratio * rect.height()
                    painter.setPen(QPen(color, 2))
                    painter.drawLine(QPointF(rect.left() - 2, threshold_y), QPointF(rect.right() + 2, threshold_y))
                    painter.setPen(QPen(self._normal_color, 1))
        
        painter.restore()
        
    def drawValueBar(self, painter, rect):
        painter.save()
        
        value_ratio = (self._value - self._min_value) / (self._max_value - self._min_value)
        
        # 确定值条颜色
        bar_color = self._value_color
        for threshold, color, name in self._thresholds:
            if self._value >= threshold:
                bar_color = color
                
        painter.setPen(Qt.NoPen)
        painter.setBrush(bar_color)
        
        if self._orientation == Qt.Horizontal:
            bar_width = value_ratio * rect.width()
            bar_rect = QRectF(rect.left(), rect.top(), bar_width, rect.height())
            painter.drawRoundedRect(bar_rect, 2, 2)
        else:
            bar_height = value_ratio * rect.height()
            bar_rect = QRectF(rect.left(), rect.bottom() - bar_height, rect.width(), bar_height)
            painter.drawRoundedRect(bar_rect, 2, 2)
        
        painter.restore()
        
    def drawText(self, painter, rect):
        painter.save()
        
        font = QFont("Arial", 10)
        painter.setFont(font)
        painter.setPen(QPen(self._text_color))
        
        value_text = f"{self._value:.{self._precision}f} {self._units}"
        
        if self._orientation == Qt.Horizontal:
            text_rect = QRectF(rect.left(), rect.top(), rect.width(), 15)
            painter.drawText(text_rect, Qt.AlignCenter, value_text)
        else:
            painter.translate(rect.left() - 20, rect.top() + rect.height() / 2)
            painter.rotate(-90)
            text_rect = QRectF(0, 0, rect.height(), 20)
            painter.drawText(text_rect, Qt.AlignCenter, value_text)
        
        painter.restore()

# 数字仪表
class DigitalGauge(QWidget):
    valueChanged = pyqtSignal(float)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._value = 0.0
        self._precision = 2
        self._units = "V"
        self._text_color = QColor(50, 200, 50)
        self._backgroundColor = QColor(20, 20, 20)
        self._border_color = QColor(100, 100, 100)
        
        self._animation = QVariantAnimation(self)
        self._animation.valueChanged.connect(self._update_animated_value)
        self._animation.setEasingCurve(QEasingCurve.OutCubic)
        self._animation.setDuration(500)
        
        self.setMinimumSize(100, 40)
        
    def setValue(self, value):
        if value != self._value:
            self._value = value
            self.valueChanged.emit(value)
            self.update()
            
    def setAnimatedValue(self, value):
        if value != self._value:
            self._animation.stop()
            self._animation.setStartValue(self._value)
            self._animation.setEndValue(value)
            self._animation.start()
            
    def _update_animated_value(self, value):
        if value is not None:  # 添加 None 检查
            self._value = value
            self.valueChanged.emit(value)
            self.update()
        
    def setPrecision(self, precision):
        self._precision = precision
        self.update()
        
    def setUnits(self, units):
        self._units = units
        self.update()
        
    def setTextColor(self, color):
        self._text_color = color
        self.update()
        
    def setBackgroundColor(self, color):
        self._backgroundColor = color
        self.update()
        
    def setBorderColor(self, color):
        self._border_color = color
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        rect = self.rect().adjusted(1, 1, -1, -1)
        
        # 绘制背景
        painter.setPen(QPen(self._border_color, 2))
        painter.setBrush(self._backgroundColor)
        painter.drawRoundedRect(rect, 5, 5)
        
        # 绘制文本
        font = QFont("Monospace", 14, QFont.Bold)
        painter.setFont(font)
        painter.setPen(QPen(self._text_color))
        
        value_text = f"{self._value:.{self._precision}f} {self._units}"
        painter.drawText(rect, Qt.AlignCenter, value_text)

# 指南针仪表
class CompassWidget(QWidget):
    valueChanged = pyqtSignal(float)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._value = 0.0  # 角度值，0-360
        self._backgroundColor = QColor(40, 40, 40)
        self._normal_color = QColor(100, 100, 100)
        self._needle_color = QColor(255, 50, 50)
        self._text_color = QColor(255, 255, 255)
        
        self._animation = QVariantAnimation(self)
        self._animation.valueChanged.connect(self._update_animated_value)
        self._animation.setEasingCurve(QEasingCurve.OutCubic)
        self._animation.setDuration(500)
        
        self.setMinimumSize(150, 150)
        
    def setValue(self, value):
        # 规范化角度到0-360范围
        value = value % 360
        if value != self._value:
            self._value = value
            self.valueChanged.emit(value)
            self.update()
            
    def setAnimatedValue(self, value):
        value = value % 360
        if value != self._value:
            self._animation.stop()
            self._animation.setStartValue(self._value)
            self._animation.setEndValue(value)
            self._animation.start()
            
    def _update_animated_value(self, value):
        if value is not None:  # 添加 None 检查
            self._value = value
            self.valueChanged.emit(value)
            self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        side = min(self.width(), self.height())
        center = QPointF(self.width() / 2, self.height() / 2)
        radius = side / 2 - 10
        
        # 绘制背景
        painter.setPen(QPen(self._normal_color, 2))
        gradient = QRadialGradient(center, radius, center)
        gradient.setColorAt(0, self._backgroundColor.lighter(120))
        gradient.setColorAt(1, self._backgroundColor.darker(120))
        painter.setBrush(gradient)
        painter.drawEllipse(center, radius, radius)
        
        # 绘制方向标记
        painter.setPen(QPen(self._text_color, 2))
        font = QFont("Arial", max(10, int(radius / 10)))
        painter.setFont(font)
        
        directions = ["N", "E", "S", "W"]
        for i, direction in enumerate(directions):
            angle = i * 90
            text_point = center + QPointF(
                (radius - 20) * math.cos(math.radians(angle)),
                (radius - 20) * math.sin(math.radians(angle))
            )
            text_rect = QRectF(text_point.x() - 10, text_point.y() - 10, 20, 20)
            painter.drawText(text_rect, Qt.AlignCenter, direction)
            
            # 绘制刻度线
            start_point = center + QPointF(
                (radius - 10) * math.cos(math.radians(angle)),
                (radius - 10) * math.sin(math.radians(angle))
            )
            end_point = center + QPointF(
                radius * math.cos(math.radians(angle)),
                radius * math.sin(math.radians(angle))
            )
            painter.drawLine(start_point, end_point)
        
        # 绘制指针
        painter.save()
        painter.translate(center)
        painter.rotate(self._value)
        
        painter.setPen(QPen(self._needle_color, 2))
        painter.setBrush(self._needle_color)
        
        # 绘制指针
        needle_length = radius * 0.7
        needle_path = QPainterPath()
        needle_path.moveTo(0, 0)
        needle_path.lineTo(-5, -10)
        needle_path.lineTo(0, -needle_length)
        needle_path.lineTo(5, -10)
        needle_path.closeSubpath()
        
        painter.drawPath(needle_path)
        
        # 绘制中心圆
        painter.setPen(Qt.NoPen)
        painter.setBrush(self._backgroundColor)
        painter.drawEllipse(QPointF(0, 0), 10, 10)
        
        painter.setPen(QPen(self._needle_color, 1))
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(QPointF(0, 0), 10, 10)
        
        painter.restore()
        
        # 绘制当前角度值
        font = QFont("Arial", max(12, int(radius / 8)))
        painter.setFont(font)
        value_text = f"{self._value:.1f}°"
        value_rect = QRectF(center.x() - radius * 0.5, center.y() + radius * 0.3, 
                           radius, radius * 0.3)
        painter.drawText(value_rect, Qt.AlignCenter, value_text)

# 数据曲线显示部件
class DataCurveWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.data = []
        self.max_points = 100
        self._min_value = 0.0
        self._max_value = 100.0
        self._line_color = QColor(50, 150, 250)
        self._background_color = QColor(40, 40, 40)
        self._grid_color = QColor(80, 80, 80)
        self._text_color = QColor(200, 200, 200)
        
        self.setMinimumSize(200, 100)
        
    def addDataPoint(self, value):
        self.data.append(value)
        if len(self.data) > self.max_points:
            self.data.pop(0)
        self.update()
        
    def setRange(self, min_val, max_val):
        self._min_value = min_val
        self._max_value = max_val
        self.update()
        
    def setLineColor(self, color):
        self._line_color = color
        self.update()
        
    def setBackgroundColor(self, color):
        self._background_color = color
        self.update()
        
    def setGridColor(self, color):
        self._grid_color = color
        self.update()
        
    def setTextColor(self, color):
        self._text_color = color
        self.update()
        
    def paintEvent(self, event):
        if not self.data:
            return
            
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        rect = self.rect().adjusted(5, 5, -5, -5)
        
        # 绘制背景和网格
        painter.setPen(Qt.NoPen)
        painter.setBrush(self._background_color)
        painter.drawRect(rect)
        
        painter.setPen(QPen(self._grid_color, 1))
        # 绘制水平网格线
        for i in range(0, 11):
            y = rect.bottom() - (i / 10) * rect.height()
            painter.drawLine(QPointF(rect.left(), y), QPointF(rect.right(), y))
            
            # 绘制刻度值
            value = self._min_value + (i / 10) * (self._max_value - self._min_value)
            painter.drawText(QRectF(rect.left() - 30, y - 10, 25, 20), 
                            Qt.AlignRight | Qt.AlignVCenter, f"{value:.1f}")
        
        # 绘制数据曲线
        if len(self.data) > 1:
            path = QPainterPath()
            x_step = rect.width() / (self.max_points - 1)
            
            # 第一个点
            value = self.data[0]
            y = rect.bottom() - ((value - self._min_value) / (self._max_value - self._min_value)) * rect.height()
            path.moveTo(rect.left(), y)
            
            # 后续点
            for i in range(1, len(self.data)):
                value = self.data[i]
                x = rect.left() + i * x_step
                y = rect.bottom() - ((value - self._min_value) / (self._max_value - self._min_value)) * rect.height()
                path.lineTo(x, y)
                
            painter.setPen(QPen(self._line_color, 2))
            painter.drawPath(path)

# 主仪表板演示
class AdvancedDashboardDemo(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("高级PyQt仪表系统")
        self.resize(1200, 800)
        
        # 初始化数据记录器和报警系统
        self.data_logger = DataLogger(max_records=500)
        self.alarm_system = AlarmSystem()
        self.theme_manager = ThemeManager()
        
        # 设置中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        main_layout = QHBoxLayout(central_widget)
        
        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        # 创建左侧控制面板
        control_panel = self.createControlPanel()
        splitter.addWidget(control_panel)
        
        # 创建右侧仪表板
        dashboard_tabs = self.createDashboardTabs()
        splitter.addWidget(dashboard_tabs)
        
        # 设置分割器比例
        splitter.setSizes([300, 900])
        
        # 创建菜单栏和状态栏
        self.createMenuBar()
        self.createStatusBar()
        
        # 设置定时器模拟数据变化
        self.simulation_timer = QTimer(self)
        self.simulation_timer.timeout.connect(self.updateSimulation)
        self.simulation_timer.start(100)  # 10Hz更新
        
        self.simulation_counter = 0
        
        # 应用初始主题
        self.applyTheme("Dark")
        
    def createMenuBar(self):
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu("文件")
        
        export_action = QAction("导出数据", self)
        export_action.triggered.connect(self.exportData)
        file_menu.addAction(export_action)
        
        import_action = QAction("导入数据", self)
        import_action.triggered.connect(self.importData)
        file_menu.addAction(import_action)
        
        exit_action = QAction("退出", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 视图菜单
        view_menu = menubar.addMenu("视图")
        
        theme_menu = view_menu.addMenu("主题")
        for theme_name in self.theme_manager.get_theme_names():
            theme_action = QAction(theme_name, self)
            theme_action.triggered.connect(lambda checked, name=theme_name: self.applyTheme(name))
            theme_menu.addAction(theme_action)
            
        # 工具菜单
        tools_menu = menubar.addMenu("工具")
        
        alarm_manager_action = QAction("报警管理", self)
        alarm_manager_action.triggered.connect(self.showAlarmManager)
        tools_menu.addAction(alarm_manager_action)
        
    def createStatusBar(self):
        status_bar = self.statusBar()
        self.status_label = QLabel("就绪")
        status_bar.addWidget(self.status_label)
        
        # 添加主题指示器
        self.theme_label = QLabel(f"主题: {self.theme_manager.current_theme}")
        status_bar.addPermanentWidget(self.theme_label)
        
    def createControlPanel(self):
        panel = QGroupBox("控制面板")
        layout = QVBoxLayout(panel)
        
        # 值控制
        value_group = QGroupBox("值控制")
        value_layout = QFormLayout(value_group)
        
        self.value_slider = QSlider(Qt.Horizontal)
        self.value_slider.setRange(0, 100)
        self.value_slider.setValue(50)
        self.value_slider.valueChanged.connect(self.onSliderValueChanged)
        value_layout.addRow("主值:", self.value_slider)
        
        self.value_spin = QDoubleSpinBox()
        self.value_spin.setRange(0, 100)
        self.value_spin.setValue(50)
        self.value_spin.valueChanged.connect(self.onSpinValueChanged)
        value_layout.addRow("精确值:", self.value_spin)
        
        layout.addWidget(value_group)
        
        # 范围控制
        range_group = QGroupBox("范围控制")
        range_layout = QFormLayout(range_group)
        
        self.min_spin = QDoubleSpinBox()
        self.min_spin.setRange(-100, 100)
        self.min_spin.setValue(0)
        self.min_spin.valueChanged.connect(self.onRangeChanged)
        range_layout.addRow("最小值:", self.min_spin)
        
        self.max_spin = QDoubleSpinBox()
        self.max_spin.setRange(-100, 200)
        self.max_spin.setValue(100)
        self.max_spin.valueChanged.connect(self.onRangeChanged)
        range_layout.addRow("最大值:", self.max_spin)
        
        layout.addWidget(range_group)
        
        # 阈值控制
        threshold_group = QGroupBox("阈值控制")
        threshold_layout = QFormLayout(threshold_group)
        
        self.threshold_spin = QDoubleSpinBox()
        self.threshold_spin.setRange(0, 100)
        self.threshold_spin.setValue(80)
        threshold_layout.addRow("阈值:", self.threshold_spin)
        
        self.threshold_color_combo = QComboBox()
        self.threshold_color_combo.addItems(["红色", "黄色", "橙色", "紫色"])
        threshold_layout.addRow("阈值颜色:", self.threshold_color_combo)
        
        add_threshold_btn = QPushButton("添加阈值")
        add_threshold_btn.clicked.connect(self.onAddThreshold)
        threshold_layout.addRow(add_threshold_btn)
        
        clear_thresholds_btn = QPushButton("清除所有阈值")
        clear_thresholds_btn.clicked.connect(self.onClearThresholds)
        threshold_layout.addRow(clear_thresholds_btn)
        
        layout.addWidget(threshold_group)
        
        # 选项控制
        options_group = QGroupBox("选项")
        options_layout = QVBoxLayout(options_group)
        
        self.animation_check = QCheckBox("启用动画")
        self.animation_check.setChecked(True)
        options_layout.addWidget(self.animation_check)
        
        self.simulation_check = QCheckBox("启用模拟")
        self.simulation_check.setChecked(True)
        options_layout.addWidget(self.simulation_check)
        
        self.logging_check = QCheckBox("启用数据记录")
        self.logging_check.setChecked(True)
        options_layout.addWidget(self.logging_check)
        
        layout.addWidget(options_group)
        
        # 报警控制
        alarm_group = QGroupBox("报警设置")
        alarm_layout = QFormLayout(alarm_group)
        
        self.alarm_threshold_spin = QDoubleSpinBox()
        self.alarm_threshold_spin.setRange(0, 100)
        self.alarm_threshold_spin.setValue(90)
        alarm_layout.addRow("报警阈值:", self.alarm_threshold_spin)
        
        self.alarm_severity_combo = QComboBox()
        self.alarm_severity_combo.addItems(["警告", "错误", "严重"])
        alarm_layout.addRow("报警级别:", self.alarm_severity_combo)
        
        add_alarm_btn = QPushButton("添加报警")
        add_alarm_btn.clicked.connect(self.onAddAlarm)
        alarm_layout.addRow(add_alarm_btn)
        
        layout.addWidget(alarm_group)
        
        layout.addStretch()
        
        return panel
        
    def createDashboardTabs(self):
        tabs = QTabWidget()
        
        # 第一页：圆形和半圆仪表
        page1 = QWidget()
        layout1 = QGridLayout(page1)
        
        # 圆形仪表
        self.circular_gauge = GaugeWidget()
        self.circular_gauge.setRange(0, 100)
        self.circular_gauge.setValue(50)
        self.circular_gauge.setUnits("°C")
        self.circular_gauge.setPrecision(1)
        layout1.addWidget(self.circular_gauge, 0, 0)
        
        # 半圆仪表
        self.semi_circular_gauge = SemiCircularGauge()
        self.semi_circular_gauge.setRange(0, 100)
        self.semi_circular_gauge.setValue(50)
        self.semi_circular_gauge.setUnits("MPa")
        self.semi_circular_gauge.setPrecision(2)
        layout1.addWidget(self.semi_circular_gauge, 0, 1)
        
        # 数字仪表
        self.digital_gauge = DigitalGauge()
        self.digital_gauge.setValue(50)
        self.digital_gauge.setUnits("V")
        self.digital_gauge.setPrecision(2)
        layout1.addWidget(self.digital_gauge, 1, 0)
        
        # 指南针仪表
        self.compass_gauge = CompassWidget()
        self.compass_gauge.setValue(45)
        layout1.addWidget(self.compass_gauge, 1, 1)
        
        tabs.addTab(page1, "圆形仪表")
        
        # 第二页：线性仪表
        page2 = QWidget()
        layout2 = QVBoxLayout(page2)
        
        # 水平线性仪表
        self.horizontal_gauge = LinearGaugeWidget(Qt.Horizontal)
        self.horizontal_gauge.setRange(0, 100)
        self.horizontal_gauge.setValue(50)
        self.horizontal_gauge.setUnits("%")
        self.horizontal_gauge.setPrecision(1)
        layout2.addWidget(self.horizontal_gauge)
        
        # 垂直线性仪表
        self.vertical_gauge = LinearGaugeWidget(Qt.Vertical)
        self.vertical_gauge.setRange(0, 100)
        self.vertical_gauge.setValue(50)
        self.vertical_gauge.setUnits("psi")
        self.vertical_gauge.setPrecision(1)
        self.vertical_gauge.setMinimumHeight(200)
        layout2.addWidget(self.vertical_gauge)
        
        tabs.addTab(page2, "线性仪表")
        
        # 第三页：数据曲线
        page3 = QWidget()
        layout3 = QVBoxLayout(page3)
        
        self.data_curve = DataCurveWidget()
        self.data_curve.setRange(0, 100)
        self.data_curve.setMinimumHeight(300)
        layout3.addWidget(self.data_curve)
        
        tabs.addTab(page3, "数据曲线")
        
        # 第四页：报警列表
        page4 = QWidget()
        layout4 = QVBoxLayout(page4)
        
        self.alarm_list = QListWidget()
        layout4.addWidget(self.alarm_list)
        
        tabs.addTab(page4, "报警列表")
        
        return tabs
        
    def onSliderValueChanged(self, value):
        self.value_spin.setValue(value)
        self.updateGauges(value)
        
    def onSpinValueChanged(self, value):
        self.value_slider.setValue(int(value))
        self.updateGauges(value)
        
    def updateGauges(self, value):
        if self.animation_check.isChecked():
            self.circular_gauge.setAnimatedValue(value)
            self.semi_circular_gauge.setAnimatedValue(value)
            self.horizontal_gauge.setAnimatedValue(value)
            self.vertical_gauge.setAnimatedValue(value)
            self.digital_gauge.setAnimatedValue(value)
        else:
            self.circular_gauge.setValue(value)
            self.semi_circular_gauge.setValue(value)
            self.horizontal_gauge.setValue(value)
            self.vertical_gauge.setValue(value)
            self.digital_gauge.setValue(value)
            
        # 更新指南针（使用不同的值范围）
        compass_value = (value / 100) * 360
        if self.animation_check.isChecked():
            self.compass_gauge.setAnimatedValue(compass_value)
        else:
            self.compass_gauge.setValue(compass_value)
            
        # 更新数据曲线
        self.data_curve.addDataPoint(value)
        
        # 记录数据
        if self.logging_check.isChecked():
            self.data_logger.log_data("main_value", value)
            
        # 检查报警
        alarms = self.alarm_system.check_value("main_value", value)
        for alarm in alarms:
            self.handleAlarm(alarm)
            
    def onRangeChanged(self):
        min_val = self.min_spin.value()
        max_val = self.max_spin.value()
        
        self.circular_gauge.setRange(min_val, max_val)
        self.semi_circular_gauge.setRange(min_val, max_val)
        self.horizontal_gauge.setRange(min_val, max_val)
        self.vertical_gauge.setRange(min_val, max_val)
        self.data_curve.setRange(min_val, max_val)
        
        # 更新滑块范围
        self.value_slider.setRange(int(min_val), int(max_val))
        self.value_spin.setRange(min_val, max_val)
        
    def onAddThreshold(self):
        threshold = self.threshold_spin.value()
        
        color_name = self.threshold_color_combo.currentText()
        if color_name == "红色":
            color = QColor(255, 0, 0)
        elif color_name == "黄色":
            color = QColor(255, 255, 0)
        elif color_name == "橙色":
            color = QColor(255, 165, 0)
        else:  # 紫色
            color = QColor(128, 0, 128)
            
        self.circular_gauge.addThreshold(threshold, color, f"阈值{threshold}")
        self.semi_circular_gauge.addThreshold(threshold, color, f"阈值{threshold}")
        self.horizontal_gauge.addThreshold(threshold, color, f"阈值{threshold}")
        self.vertical_gauge.addThreshold(threshold, color, f"阈值{threshold}")
        
    def onClearThresholds(self):
        self.circular_gauge.clearThresholds()
        self.semi_circular_gauge.clearThresholds()
        self.horizontal_gauge.clearThresholds()
        self.vertical_gauge.clearThresholds()
        
    def onAddAlarm(self):
        threshold = self.alarm_threshold_spin.value()
        severity = self.alarm_severity_combo.currentText()
        
        self.alarm_system.add_alarm(
            "main_value", ">", threshold, 
            severity.lower(), f"主值超过 {threshold}"
        )
        
        self.status_label.setText(f"已添加{severity}报警，阈值: {threshold}")
        
    def handleAlarm(self, alarm):
        if alarm.triggered:
            # 报警触发
            item = QListWidgetItem(
                f"[{alarm.trigger_time.strftime('%H:%M:%S')}] "
                f"{alarm.severity.upper()}: {alarm.message}"
            )
            
            # 根据严重级别设置颜色
            if alarm.severity == "warning":
                item.setForeground(QColor(255, 165, 0))  # 橙色
            elif alarm.severity == "error":
                item.setForeground(QColor(255, 0, 0))  # 红色
            elif alarm.severity == "critical":
                item.setForeground(QColor(255, 0, 0))  # 红色
                item.setBackground(QColor(255, 200, 200))  # 浅红色背景
                
            self.alarm_list.addItem(item)
            self.alarm_list.scrollToBottom()
            
            # 状态栏显示报警信息
            self.status_label.setText(f"报警: {alarm.message}")
        else:
            # 报警解除
            item = QListWidgetItem(
                f"[{datetime.datetime.now().strftime('%H:%M:%S')}] "
                f"报警解除: {alarm.message}"
            )
            item.setForeground(QColor(0, 150, 0))  # 绿色
            self.alarm_list.addItem(item)
            self.alarm_list.scrollToBottom()
            
    def updateSimulation(self):
        if not self.simulation_check.isChecked():
            return
            
        self.simulation_counter += 1
        
        # 模拟多种数据模式
        if self.simulation_counter < 200:
            # 正弦波
            value = 50 + 40 * math.sin(self.simulation_counter / 20)
        elif self.simulation_counter < 400:
            # 方波
            value = 30 if (self.simulation_counter // 20) % 2 == 0 else 70
        elif self.simulation_counter < 600:
            # 锯齿波
            value = (self.simulation_counter % 100)
        else:
            # 随机值
            value = np.random.normal(50, 15)
            value = max(0, min(100, value))
            self.simulation_counter = 0  # 重置计数器
            
        self.value_slider.setValue(int(value))
        
    def applyTheme(self, theme_name):
        if self.theme_manager.set_theme(theme_name):
            theme = self.theme_manager.get_theme(theme_name)
            
            # 应用主题到所有仪表
            self.circular_gauge.applyTheme(theme_name)
            self.semi_circular_gauge.applyTheme(theme_name)
            self.horizontal_gauge.applyTheme(theme_name)
            self.vertical_gauge.applyTheme(theme_name)
            
            # 更新状态栏
            self.theme_label.setText(f"主题: {theme_name}")
            
            # 设置应用程序调色板
            palette = QPalette()
            palette.setColor(QPalette.Window, theme["background"])
            palette.setColor(QPalette.WindowText, theme["text"])
            palette.setColor(QPalette.Base, theme["background"].darker(120))
            palette.setColor(QPalette.AlternateBase, theme["background"].lighter(120))
            palette.setColor(QPalette.ToolTipBase, theme["text"])
            palette.setColor(QPalette.ToolTipText, theme["background"])
            palette.setColor(QPalette.Text, theme["text"])
            palette.setColor(QPalette.Button, theme["background"])
            palette.setColor(QPalette.ButtonText, theme["text"])
            palette.setColor(QPalette.BrightText, theme["error"])
            palette.setColor(QPalette.Highlight, theme["accent"])
            palette.setColor(QPalette.HighlightedText, Qt.black)
            
            QApplication.instance().setPalette(palette)
            
    def exportData(self):
        filename, _ = QFileDialog.getSaveFileName(
            self, "导出数据", "", "JSON Files (*.json)"
        )
        if filename:
            self.data_logger.export_to_json(filename)
            self.status_label.setText(f"数据已导出到 {filename}")
            
    def importData(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, "导入数据", "", "JSON Files (*.json)"
        )
        if filename:
            self.data_logger.import_from_json(filename)
            self.status_label.setText(f"数据已从 {filename} 导入")
            
    def showAlarmManager(self):
        # 创建报警管理对话框
        dialog = QDialog(self)
        dialog.setWindowTitle("报警管理")
        dialog.resize(400, 300)
        
        layout = QVBoxLayout(dialog)
        
        # 显示当前报警列表
        alarm_list = QListWidget()
        for alarm in self.alarm_system.alarms:
            item = QListWidgetItem(
                f"{alarm.name} {alarm.condition} {alarm.threshold} "
                f"({alarm.severity}) - {alarm.message}"
            )
            alarm_list.addItem(item)
            
        layout.addWidget(alarm_list)
        
        # 添加按钮
        button_layout = QHBoxLayout()
        
        acknowledge_btn = QPushButton("确认选中报警")
        acknowledge_btn.clicked.connect(lambda: self.acknowledgeAlarm(alarm_list))
        button_layout.addWidget(acknowledge_btn)
        
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(dialog.accept)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
        
        dialog.exec_()
        
    def acknowledgeAlarm(self, alarm_list):
        current_row = alarm_list.currentRow()
        if 0 <= current_row < len(self.alarm_system.alarms):
            alarm = self.alarm_system.alarms[current_row]
            self.alarm_system.acknowledge_alarm(alarm)
            self.status_label.setText(f"已确认报警: {alarm.message}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 设置应用程序样式
    app.setStyle("Fusion")
    
    window = AdvancedDashboardDemo()
    window.show()
    
    sys.exit(app.exec_())