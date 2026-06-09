import sys
import random
import math
from datetime import datetime, timedelta
from PyQt5.QtCore import (QTimer, Qt, QPoint, QRect, QSize, QPropertyAnimation, 
                         QEasingCurve, pyqtProperty, QSequentialAnimationGroup,
                         QParallelAnimationGroup, QPointF, QRectF, QTimeLine,
                         QEvent, QObject, pyqtSignal)
from PyQt5.QtGui import (QPainter, QColor, QLinearGradient, QFont, QFontDatabase, 
                        QPen, QBrush, QPixmap, QPainterPath, QConicalGradient, QTextCursor,
                        QRadialGradient, QImage, QPolygonF, QTransform, QKeyEvent,
                        QMouseEvent, QPalette, QGuiApplication)
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QPushButton, QSlider, QLabel, 
                            QProgressBar, QFrame, QGroupBox, QCheckBox, 
                            QRadioButton, QSpinBox, QDoubleSpinBox, QComboBox,
                            QTabWidget, QScrollArea, QSizePolicy, QGridLayout,
                            QSplitter, QTextEdit, QLineEdit, QListView, QTreeView,
                            QTableView, QHeaderView, QStyleOption, QStyle,
                            QGraphicsDropShadowEffect, QMessageBox, QFileDialog,
                            QMenu, QAction, QToolBar, QStatusBar, QDockWidget,
                            QStackedWidget, QDial, QToolButton, QSizeGrip,
                            QGraphicsView, QGraphicsScene, QGraphicsItem,
                            QGraphicsProxyWidget, QButtonGroup, QSpacerItem,
                            QInputDialog, QColorDialog, QFontDialog)

class CyberpunkTheme:
    """赛博朋克主题颜色和字体配置"""
    # 颜色定义
    DARK_BG = QColor(10, 10, 20)
    LIGHT_BG = QColor(20, 20, 40)
    ACCENT = QColor(0, 255, 255)  # 青色
    ACCENT2 = QColor(255, 0, 255)  # 洋红色
    ACCENT3 = QColor(255, 255, 0)  # 黄色
    TEXT = QColor(220, 220, 220)
    HIGHLIGHT = QColor(0, 200, 255)
    ERROR = QColor(255, 50, 50)
    SUCCESS = QColor(50, 255, 50)
    WARNING = QColor(255, 200, 0)
    
    # 动画速度
    ANIMATION_SPEED = 500  # ms
    
    # 字体
    @staticmethod
    def load_fonts():
        """加载赛博朋克风格字体"""
        # 尝试加载一些科技感字体
        font_paths = [
            "fonts/cyberpunk.ttf",  # 假设的字体路径
            "fonts/technology.ttf",
            "fonts/digital.ttf"
        ]
        
        for path in font_paths:
            try:
                QFontDatabase.addApplicationFont(path)
            except:
                pass  # 如果字体不存在，忽略错误
    
    @staticmethod
    def font(size=10, bold=False, family="Monospace"):
        """获取赛博朋克风格字体"""
        font = QFont(family, size)
        font.setBold(bold)
        return font
    
    @classmethod
    def gradient(cls, rect, type="linear"):
        """创建赛博朋克风格渐变"""
        if type == "linear":
            gradient = QLinearGradient(rect.topLeft(), rect.topRight())
        elif type == "radial":
            gradient = QRadialGradient(rect.center(), min(rect.width(), rect.height()) / 2)
        else:
            gradient = QLinearGradient(rect.topLeft(), rect.topRight())
        
        gradient.setColorAt(0, cls.ACCENT)
        gradient.setColorAt(0.5, cls.ACCENT2)
        gradient.setColorAt(1, cls.ACCENT)
        
        return gradient


class CyberAnimationManager(QObject):
    """动画管理器"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.animations = {}
        
    def register_animation(self, name, animation):
        """注册动画"""
        self.animations[name] = animation
        
    def start_animation(self, name):
        """启动动画"""
        if name in self.animations:
            self.animations[name].start()
            
    def stop_animation(self, name):
        """停止动画"""
        if name in self.animations:
            self.animations[name].stop()
            
    def pause_animation(self, name):
        """暂停动画"""
        if name in self.animations:
            self.animations[name].pause()


class CyberGlowEffect(QObject):
    """赛博朋克发光效果管理类"""
    glowChanged = pyqtSignal(int)
    
    def __init__(self, widget, parent=None):
        super().__init__(parent)
        self.widget = widget
        self._glow_intensity = 0
        self.glow_color = CyberpunkTheme.ACCENT
        self.glow_timer = QTimer()
        self.glow_timer.timeout.connect(self.update_glow)
        self.glow_direction = 1  # 1 for increasing, -1 for decreasing
        self.glow_speed = 5
        self.pulse_enabled = True
        
    def get_glow_intensity(self):
        return self._glow_intensity
        
    def set_glow_intensity(self, value):
        self._glow_intensity = max(0, min(100, value))
        self.glowChanged.emit(self._glow_intensity)
        if self.widget:
            self.widget.update()
            
    glow_intensity = pyqtProperty(int, get_glow_intensity, set_glow_intensity)
        
    def update_glow(self):
        """更新发光效果"""
        if self.pulse_enabled:
            self.glow_intensity += self.glow_direction * self.glow_speed
            
            if self.glow_intensity >= 100:
                self.glow_intensity = 100
                self.glow_direction = -1
            elif self.glow_intensity <= 0:
                self.glow_intensity = 0
                self.glow_direction = 1
                
    def start_glow(self, pulse=True):
        """开始发光动画"""
        self.pulse_enabled = pulse
        self.glow_timer.start(50)
        
    def stop_glow(self):
        """停止发光动画"""
        self.glow_timer.stop()
        
    def set_glow_color(self, color):
        """设置发光颜色"""
        self.glow_color = color
        if self.widget:
            self.widget.update()


class CyberButton(QPushButton):
    """赛博朋克风格按钮 - 增强版"""
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setFont(CyberpunkTheme.font(10, True))
        self.setMinimumHeight(35)
        self.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        
        # 发光效果
        self.glow_effect = CyberGlowEffect(self)
        self.hover_glow = 0
        self.pressed = False
        self._animation = None
        
        # 点击动画
        self.click_animation = QPropertyAnimation(self, b"geometry")
        self.click_animation.setDuration(150)
        self.click_animation.setEasingCurve(QEasingCurve.OutQuad)
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 绘制背景
        rect = self.rect()
        bg_color = CyberpunkTheme.DARK_BG
        
        if self.pressed:
            bg_color = CyberpunkTheme.LIGHT_BG
            bg_color = bg_color.lighter(120)
        
        painter.setBrush(QBrush(bg_color))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(rect, 4, 4)
        
        # 绘制边框和发光效果
        border_width = 2
        glow_intensity = self.glow_effect.glow_intensity
        
        if self.underMouse():
            self.hover_glow = min(self.hover_glow + 10, 100)
        else:
            self.hover_glow = max(self.hover_glow - 10, 0)
            
        glow_alpha = max(glow_intensity, self.hover_glow)
        
        # 外发光
        if glow_alpha > 0:
            glow_color = self.glow_effect.glow_color
            glow_color.setAlpha(glow_alpha)
            pen = QPen(glow_color, border_width)
            pen.setJoinStyle(Qt.RoundJoin)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(rect.adjusted(border_width//2, border_width//2, 
                                                -border_width//2, -border_width//2), 4, 4)
        
        # 内边框
        pen = QPen(CyberpunkTheme.ACCENT, 1)
        pen.setJoinStyle(Qt.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(rect.adjusted(1, 1, -1, -1), 4, 4)
        
        # 绘制文本
        painter.setPen(QPen(CyberpunkTheme.TEXT))
        painter.drawText(rect, Qt.AlignCenter, self.text())
        
        # 绘制焦点指示器
        if self.hasFocus():
            focus_rect = rect.adjusted(3, 3, -3, -3)
            painter.setPen(QPen(CyberpunkTheme.HIGHLIGHT, 1, Qt.DashLine))
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(focus_rect, 2, 2)
        
    def enterEvent(self, event):
        super().enterEvent(event)
        self.glow_effect.start_glow(False)
        self.glow_effect.glow_intensity = 30
        self.update()
        
    def leaveEvent(self, event):
        super().leaveEvent(event)
        self.glow_effect.stop_glow()
        self.glow_effect.glow_intensity = 0
        self.update()
        
    def mousePressEvent(self, event):
        self.pressed = True
        
        # 点击动画
        if self._animation is None:
            self._animation = QPropertyAnimation(self, b"geometry")
            self._animation.setDuration(100)
            self._animation.setEasingCurve(QEasingCurve.OutQuad)
        
        start_rect = self.geometry()
        end_rect = QRect(start_rect.x(), start_rect.y() + 2, 
                        start_rect.width(), start_rect.height())
        
        self._animation.setStartValue(start_rect)
        self._animation.setEndValue(end_rect)
        self._animation.start()
        
        self.update()
        super().mousePressEvent(event)
        
    def mouseReleaseEvent(self, event):
        self.pressed = False
        
        if self._animation:
            start_rect = self.geometry()
            end_rect = QRect(start_rect.x(), start_rect.y() - 2, 
                            start_rect.width(), start_rect.height())
            
            self._animation.setStartValue(start_rect)
            self._animation.setEndValue(end_rect)
            self._animation.start()
        
        self.update()
        super().mouseReleaseEvent(event)
        
    def setGlowColor(self, color):
        """设置发光颜色"""
        self.glow_effect.set_glow_color(color)


class CyberProgressBar(QProgressBar):
    """赛博朋克风格进度条 - 增强版"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFont(CyberpunkTheme.font(8))
        self.setTextVisible(True)
        self.setMinimumHeight(25)
        self._animation = None
        self._value = 0
        
        # 扫描线动画
        self.scan_pos = 0
        self.scan_timer = QTimer(self)
        self.scan_timer.timeout.connect(self.update_scan)
        self.scan_timer.start(30)
        
    def update_scan(self):
        """更新扫描线位置"""
        self.scan_pos = (self.scan_pos + 2) % 100
        self.update()
        
    def setValue(self, value):
        """设置值并添加动画效果"""
        if self._animation is None:
            self._animation = QPropertyAnimation(self, b"value")
            self._animation.setDuration(500)
            self._animation.setEasingCurve(QEasingCurve.OutQuad)
        
        self._animation.setStartValue(self.value())
        self._animation.setEndValue(value)
        self._animation.start()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        rect = self.rect()
        progress = self.value() / (self.maximum() - self.minimum()) if self.maximum() > self.minimum() else 0
        
        # 绘制背景
        bg_rect = rect.adjusted(0, 0, 0, 0)
        painter.setBrush(QBrush(CyberpunkTheme.DARK_BG))
        painter.setPen(QPen(CyberpunkTheme.ACCENT, 1))
        painter.drawRoundedRect(bg_rect, 3, 3)
        
        # 绘制进度
        if progress > 0:
            progress_width = int(rect.width() * progress)
            progress_rect = QRect(rect.x(), rect.y(), progress_width, rect.height())
            
            # 创建渐变
            gradient = QLinearGradient(progress_rect.topLeft(), progress_rect.topRight())
            gradient.setColorAt(0, CyberpunkTheme.ACCENT)
            gradient.setColorAt(0.5, CyberpunkTheme.ACCENT2)
            gradient.setColorAt(1, CyberpunkTheme.ACCENT)
            
            painter.setBrush(QBrush(gradient))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(progress_rect, 3, 3)
            
            # 添加进度条内部的扫描线效果
            scan_line_y = int((self.scan_pos / 100) * rect.height())
            scan_line_color = QColor(255, 255, 255, 100)
            painter.setPen(QPen(scan_line_color, 1))
            painter.drawLine(progress_rect.left(), scan_line_y, progress_rect.right(), scan_line_y)
            
            # 添加数字指示器
            indicator_text = f"{int(progress * 100)}%"
            indicator_rect = QRect(progress_rect.right() - 40, progress_rect.top(), 40, progress_rect.height())
            painter.setPen(QPen(CyberpunkTheme.DARK_BG))
            painter.drawText(indicator_rect, Qt.AlignCenter, indicator_text)
        
        # 绘制边框
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(CyberpunkTheme.ACCENT, 1))
        painter.drawRoundedRect(rect, 3, 3)
        
        # 绘制文本
        if self.text():
            painter.setPen(QPen(CyberpunkTheme.TEXT))
            painter.drawText(rect, Qt.AlignCenter, self.text())


class CyberSlider(QSlider):
    """赛博朋克风格滑块 - 增强版"""
    def __init__(self, orientation=Qt.Horizontal, parent=None):
        super().__init__(orientation, parent)
        self.setMinimumHeight(25)
        self.glow_effect = CyberGlowEffect(self)
        self._animation = None
        
    def setValue(self, value):
        """设置值并添加动画效果"""
        if self._animation is None:
            self._animation = QPropertyAnimation(self, b"value")
            self._animation.setDuration(300)
            self._animation.setEasingCurve(QEasingCurve.OutQuad)
        
        self._animation.setStartValue(self.value())
        self._animation.setEndValue(value)
        self._animation.start()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        rect = self.rect()
        if self.orientation() == Qt.Horizontal:
            groove_height = 6
            handle_size = 20
        else:
            groove_width = 6
            handle_size = 20
            
        # 绘制滑道
        if self.orientation() == Qt.Horizontal:
            groove_rect = QRect(handle_size//2, (rect.height() - groove_height)//2, 
                               rect.width() - handle_size, groove_height)
        else:
            groove_rect = QRect((rect.width() - groove_width)//2, handle_size//2,
                               groove_width, rect.height() - handle_size)
            
        # 滑道背景
        painter.setBrush(QBrush(CyberpunkTheme.DARK_BG))
        painter.setPen(QPen(CyberpunkTheme.ACCENT, 1))
        painter.drawRoundedRect(groove_rect, 3, 3)
        
        # 绘制填充部分
        progress = (self.value() - self.minimum()) / (self.maximum() - self.minimum()) if self.maximum() > self.minimum() else 0
        
        if self.orientation() == Qt.Horizontal:
            fill_width = int(groove_rect.width() * progress)
            fill_rect = QRect(groove_rect.x(), groove_rect.y(), fill_width, groove_rect.height())
        else:
            fill_height = int(groove_rect.height() * progress)
            fill_rect = QRect(groove_rect.x(), groove_rect.y() + groove_rect.height() - fill_height, 
                            groove_rect.width(), fill_height)
            
        if progress > 0:
            gradient = QLinearGradient(fill_rect.topLeft(), fill_rect.topRight() if self.orientation() == Qt.Horizontal else fill_rect.bottomLeft())
            gradient.setColorAt(0, CyberpunkTheme.ACCENT)
            gradient.setColorAt(0.5, CyberpunkTheme.ACCENT2)
            gradient.setColorAt(1, CyberpunkTheme.ACCENT)
            
            painter.setBrush(QBrush(gradient))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(fill_rect, 3, 3)
        
        # 绘制滑块
        if self.orientation() == Qt.Horizontal:
            handle_pos = int(handle_size//2 + (rect.width() - handle_size) * progress)
            handle_rect = QRect(handle_pos - handle_size//2, (rect.height() - handle_size)//2,
                               handle_size, handle_size)
        else:
            handle_pos = int(rect.height() - handle_size//2 - (rect.height() - handle_size) * progress)
            handle_rect = QRect((rect.width() - handle_size)//2, handle_pos - handle_size//2,
                               handle_size, handle_size)
            
        # 绘制滑块发光效果
        glow_alpha = self.glow_effect.glow_intensity
        if glow_alpha > 0:
            glow_color = CyberpunkTheme.ACCENT
            glow_color.setAlpha(glow_alpha)
            painter.setBrush(QBrush(glow_color))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(handle_rect)
        
        # 绘制滑块主体
        gradient = QRadialGradient(handle_rect.center(), handle_size//2)
        gradient.setColorAt(0, CyberpunkTheme.ACCENT)
        gradient.setColorAt(1, CyberpunkTheme.DARK_BG)
        
        painter.setBrush(QBrush(gradient))
        painter.setPen(QPen(CyberpunkTheme.ACCENT, 1))
        painter.drawEllipse(handle_rect)
        
        # 绘制当前值
        if self.underMouse():
            value_text = str(self.value())
            text_rect = QRect(handle_rect.x() - 10, handle_rect.y() - 20, 
                             handle_rect.width() + 20, 15)
            painter.setBrush(QBrush(CyberpunkTheme.DARK_BG))
            painter.setPen(QPen(CyberpunkTheme.ACCENT, 1))
            painter.drawRect(text_rect)
            
            painter.setPen(QPen(CyberpunkTheme.TEXT))
            painter.drawText(text_rect, Qt.AlignCenter, value_text)
        
    def mousePressEvent(self, event):
        self.glow_effect.start_glow()
        super().mousePressEvent(event)
        
    def mouseReleaseEvent(self, event):
        self.glow_effect.stop_glow()
        self.glow_effect.glow_intensity = 0
        self.update()
        super().mouseReleaseEvent(event)
        
    def enterEvent(self, event):
        super().enterEvent(event)
        self.update()
        
    def leaveEvent(self, event):
        super().leaveEvent(event)
        self.update()


class CyberTerminal(QTextEdit):
    """赛博朋克风格终端 - 增强版"""
    commandExecuted = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFont(CyberpunkTheme.font(10))
        self.setStyleSheet(f"""
            QTextEdit {{
                background-color: {CyberpunkTheme.DARK_BG.name()};
                color: {CyberpunkTheme.ACCENT.name()};
                border: 1px solid {CyberpunkTheme.ACCENT.name()};
                border-radius: 4px;
                selection-background-color: {CyberpunkTheme.ACCENT2.name()};
            }}
        """)
        self.setFrameStyle(QFrame.NoFrame)
        
        # 命令历史
        self.command_history = []
        self.history_index = -1
        self.current_command = ""
        
        # 启动闪烁光标效果
        self.cursor_visible = True
        self.cursor_timer = QTimer(self)
        self.cursor_timer.timeout.connect(self.toggle_cursor)
        self.cursor_timer.start(500)
        
        # 添加提示符
        self.setPrompt("> ")
        
    def setPrompt(self, prompt):
        """设置终端提示符"""
        self.prompt = prompt
        self.clear()
        self.append(f"{prompt}")
        
    def toggle_cursor(self):
        """切换光标可见性"""
        self.cursor_visible = not self.cursor_visible
        self.update()
        
    def keyPressEvent(self, event):
        """处理键盘事件"""
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            # 执行命令
            command = self.toPlainText().split('\n')[-1].replace(self.prompt, "")
            if command.strip():
                self.command_history.append(command)
                self.history_index = len(self.command_history)
                self.commandExecuted.emit(command)
                self.append(f"\n{self.prompt}")
            else:
                self.append(f"{self.prompt}")
            event.accept()
        elif event.key() == Qt.Key_Up:
            # 上一条命令
            if self.command_history and self.history_index > 0:
                self.history_index -= 1
                self.replaceCurrentLine(f"{self.prompt}{self.command_history[self.history_index]}")
            event.accept()
        elif event.key() == Qt.Key_Down:
            # 下一条命令
            if self.command_history and self.history_index < len(self.command_history) - 1:
                self.history_index += 1
                self.replaceCurrentLine(f"{self.prompt}{self.command_history[self.history_index]}")
            else:
                self.history_index = len(self.command_history)
                self.replaceCurrentLine(f"{self.prompt}")
            event.accept()
        elif event.key() == Qt.Key_Backspace:
            # 防止删除提示符
            cursor = self.textCursor()
            if cursor.positionInBlock() > len(self.prompt):
                super().keyPressEvent(event)
        else:
            super().keyPressEvent(event)
            
    def replaceCurrentLine(self, text):
        """替换当前行文本"""
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.select(QTextCursor.LineUnderCursor)
        cursor.removeSelectedText()
        cursor.insertText(text)
        self.setTextCursor(cursor)
        
    def appendOutput(self, text):
        """添加输出到终端"""
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(f"\n{text}")
        self.setTextCursor(cursor)
        
    def paintEvent(self, event):
        super().paintEvent(event)
        
        if self.cursor_visible and self.hasFocus():
            painter = QPainter(self.viewport())
            cursor_rect = self.cursorRect()
            painter.fillRect(cursor_rect, CyberpunkTheme.ACCENT)


class CyberRadar(QWidget):
    """赛博朋克风格雷达显示器 - 增强版"""
    targetDetected = pyqtSignal(float, float)  # 角度, 距离
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(250, 250)
        
        self.rotation_angle = 0
        self.blips = []
        self.targets = []  # 跟踪的目标
        self.range = 1000  # 雷达范围(米)
        self.scan_speed = 2  # 扫描速度
        
        # 旋转动画
        self.rotation_timer = QTimer(self)
        self.rotation_timer.timeout.connect(self.update_rotation)
        self.rotation_timer.start(50)
        
        # 目标检测定时器
        self.detection_timer = QTimer(self)
        self.detection_timer.timeout.connect(self.detect_targets)
        self.detection_timer.start(2000)
        
        # 随机生成雷达点
        self.generate_blips()
        
    def update_rotation(self):
        """更新雷达旋转角度"""
        self.rotation_angle = (self.rotation_angle + self.scan_speed) % 360
        self.update()
        
    def generate_blips(self):
        """生成随机雷达点"""
        self.blips = []
        for _ in range(random.randint(5, 20)):
            angle = random.randint(0, 359)
            distance = random.uniform(0.1, 0.9)
            size = random.uniform(0.03, 0.08)
            intensity = random.uniform(0.5, 1.0)
            self.blips.append((angle, distance, size, intensity))
        
    def detect_targets(self):
        """模拟目标检测"""
        # 清除旧目标
        self.targets = []
        
        # 检测新目标 (模拟)
        for angle, distance, size, intensity in self.blips:
            if intensity > 0.8 and random.random() > 0.7:  # 高强度的点有概率被检测为目标
                self.targets.append((angle, distance))
                self.targetDetected.emit(angle, distance * self.range)
        
    def setRange(self, range):
        """设置雷达范围"""
        self.range = range
        self.update()
        
    def setScanSpeed(self, speed):
        """设置扫描速度"""
        self.scan_speed = speed
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 设置绘制区域为正方形
        size = min(self.width(), self.height())
        rect = QRect((self.width() - size) // 2, (self.height() - size) // 2, size, size)
        
        # 绘制背景
        bg_gradient = QRadialGradient(rect.center(), size/2)
        bg_gradient.setColorAt(0, QColor(10, 20, 30))
        bg_gradient.setColorAt(1, QColor(5, 10, 15))
        
        painter.setBrush(QBrush(bg_gradient))
        painter.setPen(QPen(CyberpunkTheme.ACCENT, 1))
        painter.drawEllipse(rect)
        
        # 绘制雷达网格
        pen = QPen(CyberpunkTheme.ACCENT, 1)
        pen.setStyle(Qt.DotLine)
        painter.setPen(pen)
        
        # 绘制同心圆和距离标记
        for i in range(1, 5):
            radius = size * i / 10
            painter.drawEllipse(rect.center(), radius // 2, radius // 2)
            
            # 绘制距离标记
            distance = self.range * i / 5
            painter.drawText(rect.center().x() + radius//2 + 5, 
                            rect.center().y(), 
                            f"{distance:.0f}m")
        
        # 绘制十字线
        painter.drawLine(rect.center().x(), rect.y(), rect.center().x(), rect.bottom())
        painter.drawLine(rect.x(), rect.center().y(), rect.right(), rect.center().y())
        
        # 绘制角度标记
        for angle in range(0, 360, 30):
            rad = angle * 3.14159 / 180
            x = rect.center().x() + (size/2 - 10) * math.cos(rad)
            y = rect.center().y() + (size/2 - 10) * math.sin(rad)
            
            painter.drawText(int(x) - 10, int(y) - 10, 20, 20, 
                            Qt.AlignCenter, f"{angle}°")
        
        # 绘制扫描线
        scan_gradient = QConicalGradient(rect.center(), self.rotation_angle)
        scan_gradient.setColorAt(0, QColor(0, 255, 255, 150))
        scan_gradient.setColorAt(0.1, QColor(0, 255, 255, 50))
        scan_gradient.setColorAt(0.2, QColor(0, 255, 255, 0))
        
        painter.setBrush(QBrush(scan_gradient))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(rect)
        
        # 绘制雷达点
        for angle, distance, size, intensity in self.blips:
            # 计算点的位置
            rad = angle * 3.14159 / 180
            x = rect.center().x() + distance * (size // 2) * math.cos(rad)
            y = rect.center().y() + distance * (size // 2) * math.sin(rad)
            
            # 根据强度设置颜色
            alpha = int(255 * intensity)
            color = QColor(CyberpunkTheme.ACCENT2)
            color.setAlpha(alpha)
            
            # 绘制点
            blip_size = max(3, int(size * size * 10))
            blip_rect = QRect(int(x - blip_size//2), int(y - blip_size//2),
                             blip_size, blip_size)
            
            painter.setBrush(QBrush(color))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(blip_rect)
            
        # 绘制目标
        for angle, distance in self.targets:
            # 计算目标位置
            rad = angle * 3.14159 / 180
            x = rect.center().x() + distance * (size // 2) * math.cos(rad)
            y = rect.center().y() + distance * (size // 2) * math.sin(rad)
            
            # 绘制目标指示器
            target_size = size / 20
            target_rect = QRect(int(x - target_size//2), int(y - target_size//2),
                               int(target_size), int(target_size))
            
            painter.setBrush(Qt.NoBrush)
            painter.setPen(QPen(CyberpunkTheme.ERROR, 2))
            painter.drawEllipse(target_rect)
            
            # 绘制十字线
            painter.drawLine(int(x - target_size), int(y), int(x + target_size), int(y))
            painter.drawLine(int(x), int(y - target_size), int(x), int(y + target_size))
            
        # 绘制外圈
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(CyberpunkTheme.ACCENT, 2))
        painter.drawEllipse(rect)
        
        # 绘制标题
        painter.setPen(QPen(CyberpunkTheme.TEXT))
        painter.drawText(rect.x(), rect.y() - 10, rect.width(), 20,
                        Qt.AlignCenter, f"雷达扫描 - 范围: {self.range}m")


class CyberPanel(QGroupBox):
    """赛博朋克风格面板 - 增强版"""
    def __init__(self, title="", parent=None):
        super().__init__(title, parent)
        self.setFont(CyberpunkTheme.font(10, True))
        self.setMinimumHeight(100)
        self.glow_effect = CyberGlowEffect(self)
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 绘制背景
        rect = self.rect()
        bg_color = CyberpunkTheme.DARK_BG
        
        # 发光效果
        glow_alpha = self.glow_effect.glow_intensity
        if glow_alpha > 0:
            glow_color = CyberpunkTheme.ACCENT
            glow_color.setAlpha(glow_alpha)
            
            glow_rect = rect.adjusted(-5, -5, 5, 5)
            painter.setBrush(QBrush(glow_color))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(glow_rect, 5, 5)
        
        painter.setBrush(QBrush(bg_color))
        painter.setPen(QPen(CyberpunkTheme.ACCENT, 1))
        painter.drawRoundedRect(rect, 5, 5)
        
        # 绘制标题背景
        title_width = self.fontMetrics().width(self.title()) + 20
        title_rect = QRect(10, 0, title_width, 20)
        
        title_gradient = QLinearGradient(title_rect.topLeft(), title_rect.topRight())
        title_gradient.setColorAt(0, CyberpunkTheme.ACCENT)
        title_gradient.setColorAt(1, CyberpunkTheme.ACCENT2)
        
        painter.setBrush(QBrush(title_gradient))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(title_rect, 3, 3)
        
        # 绘制标题文本
        painter.setPen(QPen(CyberpunkTheme.DARK_BG))
        painter.drawText(title_rect, Qt.AlignCenter, self.title())
        
    def enterEvent(self, event):
        super().enterEvent(event)
        self.glow_effect.start_glow(False)
        self.glow_effect.glow_intensity = 20
        self.update()
        
    def leaveEvent(self, event):
        super().leaveEvent(event)
        self.glow_effect.stop_glow()
        self.glow_effect.glow_intensity = 0
        self.update()


class CyberMenu(QMenu):
    """赛博朋克风格菜单"""
    def __init__(self, title="", parent=None):
        super().__init__(title, parent)
        self.setFont(CyberpunkTheme.font(9))
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 绘制背景
        rect = self.rect()
        painter.setBrush(QBrush(CyberpunkTheme.DARK_BG))
        painter.setPen(QPen(CyberpunkTheme.ACCENT, 1))
        painter.drawRoundedRect(rect, 3, 3)
        
        # 让父类绘制菜单内容
        super().paintEvent(event)


class CyberMessageBox(QMessageBox):
    """赛博朋克风格消息框"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            QMessageBox {{
                background-color: {CyberpunkTheme.DARK_BG.name()};
                color: {CyberpunkTheme.TEXT.name()};
            }}
            QMessageBox QLabel {{
                color: {CyberpunkTheme.TEXT.name()};
            }}
            QMessageBox QPushButton {{
                background-color: {CyberpunkTheme.DARK_BG.name()};
                color: {CyberpunkTheme.TEXT.name()};
                border: 1px solid {CyberpunkTheme.ACCENT.name()};
                border-radius: 3px;
                padding: 5px 10px;
                min-width: 60px;
            }}
            QMessageBox QPushButton:hover {{
                background-color: {CyberpunkTheme.ACCENT.name()};
                color: {CyberpunkTheme.DARK_BG.name()};
            }}
        """)


class CyberDigitalClock(QLabel):
    """赛博朋克风格数字时钟"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFont(CyberpunkTheme.font(20, True, "Digital"))
        self.setAlignment(Qt.AlignCenter)
        
        # 更新时间
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_time)
        self.timer.start(1000)
        
        self.update_time()
        
    def update_time(self):
        """更新时间显示"""
        current_time = datetime.now()
        time_text = current_time.strftime("%H:%M:%S")
        date_text = current_time.strftime("%Y-%m-%d")
        
        self.setText(f"{time_text}\n{date_text}")
        
        # 随机改变颜色
        if random.random() < 0.1:  # 10%的概率改变颜色
            color = random.choice([CyberpunkTheme.ACCENT, CyberpunkTheme.ACCENT2, CyberpunkTheme.ACCENT3])
            self.setStyleSheet(f"color: {color.name()};")


class CyberParticleSystem(QWidget):
    """赛博朋克风格粒子系统"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.particles = []
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_particles)
        self.timer.start(30)
        
        # 设置为透明背景
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("background:transparent;")
        
    def add_particle(self, x, y, color=None, size=3, speed=2, life=100):
        """添加粒子"""
        if color is None:
            color = random.choice([CyberpunkTheme.ACCENT, CyberpunkTheme.ACCENT2, CyberpunkTheme.ACCENT3])
            
        particle = {
            'x': x,
            'y': y,
            'color': color,
            'size': size,
            'speed_x': random.uniform(-speed, speed),
            'speed_y': random.uniform(-speed, speed),
            'life': life,
            'max_life': life
        }
        
        self.particles.append(particle)
        
    def update_particles(self):
        """更新粒子状态"""
        for particle in self.particles[:]:
            particle['x'] += particle['speed_x']
            particle['y'] += particle['speed_y']
            particle['life'] -= 1
            
            if particle['life'] <= 0:
                self.particles.remove(particle)
                
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        for particle in self.particles:
            alpha = int(255 * (particle['life'] / particle['max_life']))
            color = QColor(particle['color'])
            color.setAlpha(alpha)
            
            painter.setBrush(QBrush(color))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(QPointF(particle['x'], particle['y']), 
                               particle['size'], particle['size'])


class CyberpunkToolkitDemo(QMainWindow):
    """赛博朋克工具库演示窗口 - 增强版"""
    def __init__(self):
        super().__init__()
        self.initUI()
        
    def initUI(self):
        self.setWindowTitle('赛博朋克高级工具库 - 增强版')
        self.setGeometry(100, 100, 1200, 800)
        
        # 设置应用程序图标
        self.setWindowIcon(self.style().standardIcon(QStyle.SP_ComputerIcon))
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QHBoxLayout(central_widget)
        
        # 创建左侧控制面板
        left_panel = self.create_left_panel()
        main_layout.addWidget(left_panel)
        
        # 创建右侧主内容区域
        right_panel = self.create_right_panel()
        main_layout.addWidget(right_panel, 1)  # 右侧区域占据更多空间
        
        # 创建菜单栏
        self.create_menu()
        
        # 创建状态栏
        self.statusBar().showMessage("系统就绪 | 所有模块在线 | 欢迎使用赛博朋克工具库")
        
        # 创建工具栏
        self.create_toolbar()
        
        # 启动定时器更新进度条
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_progress)
        self.update_timer.start(100)
        
        # 设置样式
        self.apply_style()
        
        # 粒子系统
        self.particle_system = CyberParticleSystem(self)
        self.particle_system.setGeometry(0, 0, self.width(), self.height())
        self.particle_system.raise_()  # 确保粒子系统在最上层
        
        # 粒子生成定时器
        self.particle_timer = QTimer(self)
        self.particle_timer.timeout.connect(self.generate_particles)
        self.particle_timer.start(100)
        
    def create_left_panel(self):
        """创建左侧控制面板"""
        panel = CyberPanel("控制中心")
        panel.setMaximumWidth(300)
        layout = QVBoxLayout(panel)
        
        # 数字时钟
        self.clock = CyberDigitalClock()
        layout.addWidget(self.clock)
        
        # 系统状态
        status_group = CyberPanel("系统状态")
        status_layout = QVBoxLayout(status_group)
        
        status_labels = [
            ("CPU使用率", "45%"), ("内存使用", "62%"),
            ("网络流量", "1.2 Gb/s"), ("温度", "42°C"),
            ("正常运行时间", "12:45:32"), ("安全状态", "正常")
        ]
        
        for label, value in status_labels:
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(5, 2, 5, 2)
            
            label_widget = QLabel(label + ":")
            label_widget.setFont(CyberpunkTheme.font(9))
            value_widget = QLabel(value)
            value_widget.setFont(CyberpunkTheme.font(9, True))
            value_widget.setStyleSheet(f"color: {CyberpunkTheme.ACCENT.name()};")
            
            row_layout.addWidget(label_widget)
            row_layout.addWidget(value_widget)
            row_layout.addStretch()
            
            status_layout.addWidget(row)
        
        layout.addWidget(status_group)
        
        # 控制按钮
        control_group = CyberPanel("系统控制")
        control_layout = QVBoxLayout(control_group)
        
        self.power_button = CyberButton("启动系统")
        self.power_button.clicked.connect(self.toggle_power)
        control_layout.addWidget(self.power_button)
        
        self.emergency_button = CyberButton("紧急停止")
        self.emergency_button.setGlowColor(CyberpunkTheme.ERROR)
        self.emergency_button.clicked.connect(self.emergency_stop)
        control_layout.addWidget(self.emergency_button)
        
        layout.addWidget(control_group)
        
        # 进度条
        progress_group = CyberPanel("系统负载")
        progress_layout = QVBoxLayout(progress_group)
        
        self.progress_bar = CyberProgressBar()
        self.progress_bar.setValue(45)
        progress_layout.addWidget(self.progress_bar)
        
        layout.addWidget(progress_group)
        
        # 滑块
        slider_group = CyberPanel("灵敏度调节")
        slider_layout = QVBoxLayout(slider_group)
        
        self.slider = CyberSlider()
        self.slider.setValue(75)
        slider_layout.addWidget(self.slider)
        
        layout.addWidget(slider_group)
        
        # 复选框和单选按钮
        layout.addWidget(self.create_checkbox_group())
        layout.addWidget(self.create_radio_group())
        
        layout.addStretch()
        
        return panel
        
    def create_right_panel(self):
        """创建右侧主内容区域"""
        tab_widget = QTabWidget()
        tab_widget.setDocumentMode(True)
        tab_widget.setTabPosition(QTabWidget.North)
        
        # 终端标签
        terminal_tab = QWidget()
        terminal_layout = QVBoxLayout(terminal_tab)
        self.terminal = CyberTerminal()
        self.terminal.setPlainText("> 系统初始化完成\n> 所有模块在线\n> 准备就绪")
        self.terminal.commandExecuted.connect(self.handle_command)
        terminal_layout.addWidget(self.terminal)
        tab_widget.addTab(terminal_tab, "终端")
        
        # 雷达标签
        radar_tab = QWidget()
        radar_layout = QVBoxLayout(radar_tab)
        self.radar = CyberRadar()
        self.radar.targetDetected.connect(self.handle_target_detected)
        radar_layout.addWidget(self.radar)
        
        # 雷达控制
        radar_control = QWidget()
        radar_control_layout = QHBoxLayout(radar_control)
        
        range_label = QLabel("雷达范围:")
        range_label.setFont(CyberpunkTheme.font(9))
        radar_control_layout.addWidget(range_label)
        
        self.range_slider = QSlider(Qt.Horizontal)
        self.range_slider.setRange(100, 5000)
        self.range_slider.setValue(1000)
        self.range_slider.valueChanged.connect(self.radar.setRange)
        radar_control_layout.addWidget(self.range_slider)
        
        speed_label = QLabel("扫描速度:")
        speed_label.setFont(CyberpunkTheme.font(9))
        radar_control_layout.addWidget(speed_label)
        
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setRange(1, 10)
        self.speed_slider.setValue(2)
        self.speed_slider.valueChanged.connect(self.radar.setScanSpeed)
        radar_control_layout.addWidget(self.speed_slider)
        
        radar_layout.addWidget(radar_control)
        tab_widget.addTab(radar_tab, "雷达")
        
        # 数据可视化标签
        viz_tab = QWidget()
        viz_layout = QVBoxLayout(viz_tab)
        viz_layout.addWidget(QLabel("数据可视化面板 (开发中)"))
        tab_widget.addTab(viz_tab, "可视化")
        
        # 系统设置标签
        settings_tab = QWidget()
        settings_layout = QVBoxLayout(settings_tab)
        settings_layout.addWidget(QLabel("系统设置面板 (开发中)"))
        tab_widget.addTab(settings_tab, "设置")
        
        return tab_widget
        
    def create_menu(self):
        """创建菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = CyberMenu("文件", self)
        new_action = QAction("新建", self)
        open_action = QAction("打开", self)
        save_action = QAction("保存", self)
        exit_action = QAction("退出", self)
        exit_action.triggered.connect(self.close)
        
        file_menu.addAction(new_action)
        file_menu.addAction(open_action)
        file_menu.addAction(save_action)
        file_menu.addSeparator()
        file_menu.addAction(exit_action)
        
        # 编辑菜单
        edit_menu = CyberMenu("编辑", self)
        edit_menu.addAction("撤销")
        edit_menu.addAction("重做")
        edit_menu.addSeparator()
        edit_menu.addAction("剪切")
        edit_menu.addAction("复制")
        edit_menu.addAction("粘贴")
        
        # 视图菜单
        view_menu = CyberMenu("视图", self)
        view_menu.addAction("全屏")
        view_menu.addAction("面板布局")
        
        # 帮助菜单
        help_menu = CyberMenu("帮助", self)
        help_menu.addAction("关于")
        
        menubar.addMenu(file_menu)
        menubar.addMenu(edit_menu)
        menubar.addMenu(view_menu)
        menubar.addMenu(help_menu)
        
    def create_toolbar(self):
        """创建工具栏"""
        toolbar = QToolBar("主工具栏")
        toolbar.setIconSize(QSize(16, 16))
        self.addToolBar(toolbar)
        
        toolbar.addAction(self.style().standardIcon(QStyle.SP_ComputerIcon), "系统信息")
        toolbar.addAction(self.style().standardIcon(QStyle.SP_FileIcon), "打开")
        toolbar.addAction(self.style().standardIcon(QStyle.SP_MediaPlay), "启动")
        toolbar.addAction(self.style().standardIcon(QStyle.SP_MediaStop), "停止")
        toolbar.addSeparator()
        toolbar.addAction(self.style().standardIcon(QStyle.SP_MessageBoxQuestion), "帮助")
        
    def create_checkbox_group(self):
        """创建复选框组"""
        group = CyberPanel("选项")
        layout = QVBoxLayout(group)
        
        options = ["启用加密", "日志记录", "自动更新", "远程访问", "高级监控"]
        self.checkboxes = []
        
        for option in options:
            checkbox = QCheckBox(option)
            checkbox.setFont(CyberpunkTheme.font(9))
            layout.addWidget(checkbox)
            self.checkboxes.append(checkbox)
            
        return group
        
    def create_radio_group(self):
        """创建单选按钮组"""
        group = CyberPanel("模式选择")
        layout = QVBoxLayout(group)
        
        modes = ["标准模式", "性能模式", "节能模式", "隐身模式", "战斗模式"]
        self.radios = []
        
        for mode in modes:
            radio = QRadioButton(mode)
            radio.setFont(CyberpunkTheme.font(9))
            layout.addWidget(radio)
            self.radios.append(radio)
            
        # 设置默认选中
        self.radios[0].setChecked(True)
            
        return group
        
    def update_progress(self):
        """更新进度条"""
        value = self.progress_bar.value()
        value = (value + 1) % 100
        self.progress_bar.setValue(value)
        
    def toggle_power(self):
        """切换系统电源状态"""
        if self.power_button.text() == "启动系统":
            self.power_button.setText("关闭系统")
            self.statusBar().showMessage("系统已启动 | 运行中")
            self.terminal.appendOutput("> 系统启动完成")
        else:
            self.power_button.setText("启动系统")
            self.statusBar().showMessage("系统已关闭 | 待机中")
            self.terminal.appendOutput("> 系统已关闭")
            
    def emergency_stop(self):
        """紧急停止"""
        reply = CyberMessageBox.question(self, "确认", "确定要执行紧急停止吗?",
                                       QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.power_button.setText("启动系统")
            self.statusBar().showMessage("紧急停止已激活 | 系统关闭")
            self.terminal.appendOutput("> 紧急停止已激活")
            
            # 闪烁效果
            self.flash_emergency()
            
    def flash_emergency(self):
        """紧急状态闪烁效果"""
        self.original_style = self.styleSheet()
        
        self.flash_timer = QTimer(self)
        self.flash_timer.timeout.connect(self.toggle_flash)
        self.flash_count = 0
        self.flash_timer.start(200)
        
    def toggle_flash(self):
        """切换闪烁状态"""
        if self.flash_count % 2 == 0:
            self.setStyleSheet(f"background-color: {CyberpunkTheme.ERROR.name()};")
        else:
            self.setStyleSheet(self.original_style)
            
        self.flash_count += 1
        
        if self.flash_count >= 10:  # 闪烁5次后停止
            self.flash_timer.stop()
            self.setStyleSheet(self.original_style)
            
    def handle_command(self, command):
        """处理终端命令"""
        self.terminal.appendOutput(f"执行命令: {command}")
        
        # 简单的命令处理
        if command.lower() == "help":
            self.terminal.appendOutput("可用命令: help, clear, time, date, status")
        elif command.lower() == "clear":
            self.terminal.clear()
            self.terminal.setPrompt("> ")
        elif command.lower() == "time":
            current_time = datetime.now().strftime("%H:%M:%S")
            self.terminal.appendOutput(f"当前时间: {current_time}")
        elif command.lower() == "date":
            current_date = datetime.now().strftime("%Y-%m-%d")
            self.terminal.appendOutput(f"当前日期: {current_date}")
        elif command.lower() == "status":
            self.terminal.appendOutput("系统状态: 正常")
            self.terminal.appendOutput("所有模块: 在线")
        else:
            self.terminal.appendOutput(f"未知命令: {command}")
            
    def handle_target_detected(self, angle, distance):
        """处理雷达目标检测"""
        self.terminal.appendOutput(f"目标检测: 角度 {angle:.1f}°, 距离 {distance:.1f}m")
        self.statusBar().showMessage(f"目标 detected at {angle:.1f}°, {distance:.1f}m")
        
    def generate_particles(self):
        """生成粒子效果"""
        if random.random() < 0.3:  # 30%的概率生成粒子
            x = random.randint(0, self.width())
            y = random.randint(0, self.height())
            self.particle_system.add_particle(x, y)
            
    def apply_style(self):
        """应用全局样式"""
        self.setStyleSheet(f"""
            QMainWindow, QWidget {{
                background-color: {CyberpunkTheme.DARK_BG.name()};
                color: {CyberpunkTheme.TEXT.name()};
            }}
            QLabel {{
                color: {CyberpunkTheme.TEXT.name()};
            }}
            QTabWidget::pane {{
                border: 1px solid {CyberpunkTheme.ACCENT.name()};
                background: {CyberpunkTheme.DARK_BG.name()};
                border-radius: 4px;
            }}
            QTabBar::tab {{
                background: {CyberpunkTheme.DARK_BG.name()};
                color: {CyberpunkTheme.TEXT.name()};
                padding: 8px;
                border: 1px solid {CyberpunkTheme.ACCENT.name()};
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                margin-right: 2px;
            }}
            QTabBar::tab:selected {{
                background: {CyberpunkTheme.ACCENT.name()};
                color: {CyberpunkTheme.DARK_BG.name()};
            }}
            QTabBar::tab:hover:!selected {{
                background: {CyberpunkTheme.LIGHT_BG.name()};
            }}
            QCheckBox, QRadioButton {{
                color: {CyberpunkTheme.TEXT.name()};
                spacing: 8px;
            }}
            QCheckBox::indicator, QRadioButton::indicator {{
                width: 16px;
                height: 16px;
                border: 1px solid {CyberpunkTheme.ACCENT.name()};
                background: {CyberpunkTheme.DARK_BG.name()};
                border-radius: 3px;
            }}
            QCheckBox::indicator:checked {{
                background: {CyberpunkTheme.ACCENT.name()};
            }}
            QRadioButton::indicator:checked {{
                border: 5px solid {CyberpunkTheme.ACCENT.name()};
                border-radius: 8px;
            }}
            QSlider::groove:horizontal {{
                border: 1px solid {CyberpunkTheme.ACCENT.name()};
                height: 6px;
                background: {CyberpunkTheme.DARK_BG.name()};
                border-radius: 3px;
            }}
            QSlider::handle:horizontal {{
                background: {CyberpunkTheme.ACCENT.name()};
                border: 1px solid {CyberpunkTheme.ACCENT.name()};
                width: 20px;
                margin: -8px 0;
                border-radius: 10px;
            }}
            QStatusBar {{
                background: {CyberpunkTheme.LIGHT_BG.name()};
                color: {CyberpunkTheme.TEXT.name()};
            }}
            QMenuBar {{
                background: transparent;
                color: {CyberpunkTheme.TEXT.name()};
            }}
            QMenuBar::item:selected {{
                background: {CyberpunkTheme.ACCENT.name()};
                color: {CyberpunkTheme.DARK_BG.name()};
            }}
            QToolBar {{
                background: {CyberpunkTheme.LIGHT_BG.name()};
                border: 1px solid {CyberpunkTheme.ACCENT.name()};
                spacing: 3px;
                padding: 3px;
            }}
            QToolButton {{
                background: transparent;
                border: 1px solid transparent;
                border-radius: 3px;
                padding: 3px;
            }}
            QToolButton:hover {{
                background: {CyberpunkTheme.ACCENT.name()};
                border: 1px solid {CyberpunkTheme.ACCENT.name()};
            }}
        """)
        
    def resizeEvent(self, event):
        """处理窗口大小变化事件"""
        super().resizeEvent(event)
        self.particle_system.setGeometry(0, 0, self.width(), self.height())


if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # 加载赛博朋克字体
    CyberpunkTheme.load_fonts()
    
    # 创建并显示演示窗口
    demo = CyberpunkToolkitDemo()
    demo.show()
    
    sys.exit(app.exec_())