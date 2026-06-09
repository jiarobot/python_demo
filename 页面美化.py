import sys
import os
import json
from typing import Dict, List, Optional, Union, Callable
from dataclasses import dataclass
from enum import Enum

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtSvg import *


class Theme(Enum):
    DARK = "dark"
    LIGHT = "light"
    BLUE = "blue"
    GREEN = "green"
    PURPLE = "purple"


@dataclass
class ThemeConfig:
    name: str
    primary_color: str
    secondary_color: str
    background_color: str
    surface_color: str
    text_primary: str
    text_secondary: str
    accent_color: str


class ThemeManager:
    """主题管理器"""
    
    _themes = {
        Theme.DARK: ThemeConfig(
            name="Dark",
            primary_color="#2E3440",
            secondary_color="#3B4252",
            background_color="#1E2128",
            surface_color="#2A2E38",
            text_primary="#ECEFF4",
            text_secondary="#D8DEE9",
            accent_color="#88C0D0"
        ),
        Theme.LIGHT: ThemeConfig(
            name="Light",
            primary_color="#FFFFFF",
            secondary_color="#F5F5F5",
            background_color="#FAFAFA",
            surface_color="#FFFFFF",
            text_primary="#212121",
            text_secondary="#757575",
            accent_color="#2196F3"
        ),
        Theme.BLUE: ThemeConfig(
            name="Blue",
            primary_color="#1565C0",
            secondary_color="#1E88E5",
            background_color="#0D47A1",
            surface_color="#1976D2",
            text_primary="#E3F2FD",
            text_secondary="#BBDEFB",
            accent_color="#82B1FF"
        ),
        Theme.GREEN: ThemeConfig(
            name="Green",
            primary_color="#2E7D32",
            secondary_color="#4CAF50",
            background_color="#1B5E20",
            surface_color="#388E3C",
            text_primary="#E8F5E9",
            text_secondary="#C8E6C9",
            accent_color="#69F0AE"
        ),
        Theme.PURPLE: ThemeConfig(
            name="Purple",
            primary_color="#6A1B9A",
            secondary_color="#8E24AA",
            background_color="#4A148C",
            surface_color="#7B1FA2",
            text_primary="#F3E5F5",
            text_secondary="#E1BEE7",
            accent_color="#EA80FC"
        )
    }
    
    @classmethod
    def get_theme(cls, theme: Theme) -> ThemeConfig:
        return cls._themes[theme]
    
    @classmethod
    def get_theme_css(cls, theme: Theme) -> str:
        config = cls.get_theme(theme)
        return f"""
        /* 主窗口样式 */
        QMainWindow {{
            background-color: {config.background_color};
            color: {config.text_primary};
        }}
        
        /* 通用部件样式 */
        QWidget {{
            background-color: {config.background_color};
            color: {config.text_primary};
            border: none;
            font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
        }}
        
        /* 按钮样式 */
        QPushButton {{
            background-color: {config.primary_color};
            color: {config.text_primary};
            border: 1px solid {config.secondary_color};
            border-radius: 6px;
            padding: 10px 20px;
            font-weight: 600;
            font-size: 14px;
            min-height: 20px;
        }}
        
        QPushButton:hover {{
            background-color: {config.secondary_color};
            border: 1px solid {config.accent_color};
        }}
        
        QPushButton:pressed {{
            background-color: {config.accent_color};
        }}
        
        QPushButton:disabled {{
            background-color: #555555;
            color: #888888;
        }}
        
        /* 输入框样式 */
        QLineEdit, QTextEdit, QPlainTextEdit {{
            background-color: {config.surface_color};
            color: {config.text_primary};
            border: 1px solid {config.primary_color};
            border-radius: 4px;
            padding: 8px 12px;
            font-size: 14px;
        }}
        
        QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
            border: 2px solid {config.accent_color};
            padding: 7px 11px;
        }}
        
        /* 标签样式 */
        QLabel {{
            color: {config.text_primary};
            background-color: transparent;
            font-size: 14px;
        }}
        
        /* 进度条样式 */
        QProgressBar {{
            border: 1px solid {config.primary_color};
            border-radius: 4px;
            text-align: center;
            color: {config.text_primary};
            background-color: {config.surface_color};
        }}
        
        QProgressBar::chunk {{
            background-color: {config.accent_color};
            border-radius: 3px;
        }}
        
        /* 滑块样式 */
        QSlider::groove:horizontal {{
            border: 1px solid {config.primary_color};
            height: 6px;
            background: {config.surface_color};
            border-radius: 3px;
        }}
        
        QSlider::handle:horizontal {{
            background: {config.accent_color};
            border: 1px solid {config.primary_color};
            width: 16px;
            margin: -5px 0;
            border-radius: 8px;
        }}
        
        /* 复选框样式 */
        QCheckBox {{
            color: {config.text_primary};
            spacing: 8px;
        }}
        
        QCheckBox::indicator {{
            width: 16px;
            height: 16px;
            border: 1px solid {config.primary_color};
            border-radius: 3px;
            background-color: {config.surface_color};
        }}
        
        QCheckBox::indicator:checked {{
            background-color: {config.accent_color};
            border: 1px solid {config.accent_color};
        }}
        
        /* 单选框样式 */
        QRadioButton {{
            color: {config.text_primary};
            spacing: 8px;
        }}
        
        QRadioButton::indicator {{
            width: 16px;
            height: 16px;
            border-radius: 8px;
            border: 1px solid {config.primary_color};
            background-color: {config.surface_color};
        }}
        
        QRadioButton::indicator:checked {{
            background-color: {config.accent_color};
            border: 1px solid {config.accent_color};
        }}
        
        /* 组合框样式 */
        QComboBox {{
            background-color: {config.surface_color};
            color: {config.text_primary};
            border: 1px solid {config.primary_color};
            border-radius: 4px;
            padding: 8px 12px;
            min-width: 100px;
        }}
        
        QComboBox::drop-down {{
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 20px;
            border-left: 1px solid {config.primary_color};
        }}
        
        QComboBox::down-arrow {{
            image: none;
            border-left: 4px solid transparent;
            border-right: 4px solid transparent;
            border-top: 5px solid {config.text_primary};
            width: 0px;
            height: 0px;
        }}
        
        QComboBox QAbstractItemView {{
            background-color: {config.surface_color};
            color: {config.text_primary};
            border: 1px solid {config.primary_color};
            selection-background-color: {config.accent_color};
        }}
        
        /* 标签页样式 */
        QTabWidget::pane {{
            border: 1px solid {config.primary_color};
            border-radius: 4px;
            background-color: {config.surface_color};
        }}
        
        QTabWidget::tab-bar {{
            alignment: center;
        }}
        
        QTabBar::tab {{
            background-color: {config.primary_color};
            color: {config.text_primary};
            padding: 10px 20px;
            margin: 2px;
            border-radius: 4px 4px 0 0;
        }}
        
        QTabBar::tab:selected {{
            background-color: {config.surface_color};
            color: {config.accent_color};
            font-weight: bold;
        }}
        
        QTabBar::tab:hover:!selected {{
            background-color: {config.secondary_color};
        }}
        
        /* 滚动条样式 */
        QScrollBar:vertical {{
            background-color: {config.surface_color};
            width: 12px;
            border-radius: 6px;
        }}
        
        QScrollBar::handle:vertical {{
            background-color: {config.primary_color};
            border-radius: 6px;
            min-height: 20px;
        }}
        
        QScrollBar::handle:vertical:hover {{
            background-color: {config.secondary_color};
        }}
        
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
        }}
        
        /* 菜单样式 */
        QMenu {{
            background-color: {config.surface_color};
            color: {config.text_primary};
            border: 1px solid {config.primary_color};
            border-radius: 4px;
        }}
        
        QMenu::item {{
            padding: 8px 16px;
            border-radius: 2px;
        }}
        
        QMenu::item:selected {{
            background-color: {config.accent_color};
        }}
        
        /* 工具栏样式 */
        QToolBar {{
            background-color: {config.primary_color};
            border: none;
            spacing: 5px;
            padding: 5px;
        }}
        
        QToolButton {{
            background-color: transparent;
            border: 1px solid transparent;
            border-radius: 4px;
            padding: 5px;
        }}
        
        QToolButton:hover {{
            background-color: {config.secondary_color};
            border: 1px solid {config.accent_color};
        }}
        
        /* 状态栏样式 */
        QStatusBar {{
            background-color: {config.primary_color};
            color: {config.text_primary};
        }}
        """


class AdvancedRoundedButton(QPushButton):
    """高级圆角按钮，支持图标和加载动画"""
    
    def __init__(self, text: str = "", icon: QIcon = None, parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.PointingHandCursor)
        self._icon = icon
        self._loading = False
        self._loading_angle = 0
        self._loading_timer = QTimer(self)
        self._loading_timer.timeout.connect(self.update_loading)
        
        if icon:
            self.setIcon(icon)
            self.setIconSize(QSize(16, 16))
    
    def set_loading(self, loading: bool):
        """设置加载状态"""
        self._loading = loading
        self.setEnabled(not loading)
        
        if loading:
            self._loading_timer.start(30)  # 30ms更新一次
        else:
            self._loading_timer.stop()
            self._loading_angle = 0
            
        self.update()
    
    def update_loading(self):
        """更新加载动画"""
        self._loading_angle = (self._loading_angle + 10) % 360
        self.update()
    
    def paintEvent(self, event):
        """自定义绘制"""
        if self._loading:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            
            # 绘制加载动画
            painter.setPen(QPen(QColor("#3498db"), 3))
            painter.drawArc(5, 5, self.height()-10, self.height()-10, 
                           self._loading_angle * 16, 270 * 16)
        else:
            super().paintEvent(event)


class GradientButton(QPushButton):
    """渐变按钮，支持多种渐变方向"""
    
    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.PointingHandCursor)
        self._gradient_direction = "horizontal"  # horizontal, vertical, diagonal
        self._color1 = QColor("#3498db")
        self._color2 = QColor("#2980b9")
    
    def set_gradient(self, color1: QColor, color2: QColor, direction: str = "horizontal"):
        """设置渐变参数"""
        self._color1 = color1
        self._color2 = color2
        self._gradient_direction = direction
        self.update()
    
    def paintEvent(self, event):
        """自定义绘制渐变"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 创建渐变
        if self._gradient_direction == "horizontal":
            gradient = QLinearGradient(0, 0, self.width(), 0)
        elif self._gradient_direction == "vertical":
            gradient = QLinearGradient(0, 0, 0, self.height())
        else:  # diagonal
            gradient = QLinearGradient(0, 0, self.width(), self.height())
        
        gradient.setColorAt(0, self._color1)
        gradient.setColorAt(1, self._color2)
        
        # 绘制背景
        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(self.rect(), 8, 8)
        
        # 绘制文本
        painter.setPen(QPen(Qt.white))
        painter.setFont(self.font())
        painter.drawText(self.rect(), Qt.AlignCenter, self.text())


class MaterialCard(QFrame):
    """Material Design风格卡片"""
    
    def __init__(self, title: str = "", content: str = "", parent=None):
        super().__init__(parent)
        self.title = title
        self.content = content
        self.elevation = 2  # 阴影级别
        self.setup_ui()
    
    def setup_ui(self):
        """设置UI"""
        self.setFrameStyle(QFrame.StyledPanel)
        self.setMinimumHeight(120)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # 标题
        if self.title:
            title_label = QLabel(self.title)
            title_label.setStyleSheet("""
                QLabel {
                    font-size: 20px;
                    font-weight: bold;
                    color: #2c3e50;
                }
            """)
            layout.addWidget(title_label)
        
        # 内容
        if self.content:
            content_label = QLabel(self.content)
            content_label.setWordWrap(True)
            content_label.setStyleSheet("""
                QLabel {
                    font-size: 14px;
                    color: #34495e;
                    line-height: 1.5;
                }
            """)
            layout.addWidget(content_label)
        
        self.setLayout(layout)
        self.update_style()
    
    def set_elevation(self, elevation: int):
        """设置阴影级别 (0-5)"""
        self.elevation = max(0, min(5, elevation))
        self.update_style()
    
    def update_style(self):
        """更新样式"""
        shadow_blur = 5 + self.elevation * 3
        shadow_offset = self.elevation
        
        self.setStyleSheet(f"""
            MaterialCard {{
                background-color: white;
                border-radius: 8px;
                border: none;
            }}
        """)
        
        # 添加阴影效果
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(shadow_blur)
        shadow.setColor(QColor(0, 0, 0, 30 + self.elevation * 10))
        shadow.setOffset(shadow_offset, shadow_offset)
        self.setGraphicsEffect(shadow)


class AnimatedProgressBar(QProgressBar):
    """带动画的进度条"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._animation = QPropertyAnimation(self, b"value")
        self._animation.setDuration(800)  # 动画时长
        self._animation.setEasingCurve(QEasingCurve.OutCubic)
    
    def setValueAnimated(self, value: int):
        """设置动画值"""
        self._animation.setStartValue(self.value())
        self._animation.setEndValue(value)
        self._animation.start()


class CircularProgressBar(QWidget):
    """圆形进度条"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._value = 0
        self._maximum = 100
        self._text_visible = True
        self._line_width = 8
        self._progress_color = QColor("#3498db")
        self._background_color = QColor("#ecf0f1")
        self.setMinimumSize(80, 80)
    
    def setValue(self, value: int):
        """设置值"""
        self._value = max(0, min(value, self._maximum))
        self.update()
    
    def setMaximum(self, maximum: int):
        """设置最大值"""
        self._maximum = maximum
        self.update()
    
    def setTextVisible(self, visible: bool):
        """设置文本是否可见"""
        self._text_visible = visible
        self.update()
    
    def setLineWidth(self, width: int):
        """设置线条宽度"""
        self._line_width = width
        self.update()
    
    def setProgressColor(self, color: QColor):
        """设置进度颜色"""
        self._progress_color = color
        self.update()
    
    def paintEvent(self, event):
        """绘制圆形进度条"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 计算尺寸
        size = min(self.width(), self.height()) - self._line_width
        rect = QRectF(
            (self.width() - size) / 2,
            (self.height() - size) / 2,
            size, size
        )
        
        # 绘制背景圆
        pen = QPen(self._background_color, self._line_width)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        painter.drawArc(rect, 0, 360 * 16)
        
        # 绘制进度圆
        if self._value > 0:
            pen = QPen(self._progress_color, self._line_width)
            pen.setCapStyle(Qt.RoundCap)
            painter.setPen(pen)
            
            # 计算角度 (从顶部开始，顺时针)
            angle = int((self._value / self._maximum) * 360 * 16)
            painter.drawArc(rect, 90 * 16, -angle)
        
        # 绘制文本
        if self._text_visible:
            painter.setPen(QPen(QColor("#2c3e50")))
            painter.setFont(QFont("Arial", 12, QFont.Bold))
            text = f"{int((self._value / self._maximum) * 100)}%"
            painter.drawText(rect, Qt.AlignCenter, text)


class ToastNotification(QWidget):
    """Toast通知组件"""
    
    def __init__(self, message: str, duration: int = 3000, parent=None):
        super().__init__(parent)
        self.message = message
        self.duration = duration
        
        self.setup_ui()
        self.setup_animation()
    
    def setup_ui(self):
        """设置UI"""
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedHeight(60)
        
        layout = QHBoxLayout()
        layout.setContentsMargins(20, 10, 20, 10)
        
        # 消息标签
        label = QLabel(self.message)
        label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 14px;
                font-weight: 500;
            }
        """)
        
        # 关闭按钮
        close_btn = QPushButton("×")
        close_btn.setFixedSize(24, 24)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                color: white;
                font-size: 18px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.2);
                border-radius: 12px;
            }
        """)
        close_btn.clicked.connect(self.hide)
        
        layout.addWidget(label)
        layout.addWidget(close_btn)
        
        self.setLayout(layout)
        
        # 设置样式
        self.setStyleSheet("""
            ToastNotification {
                background-color: rgba(0, 0, 0, 0.8);
                border-radius: 8px;
            }
        """)
    
    def setup_animation(self):
        """设置动画"""
        # 淡入动画
        self.fade_in = QPropertyAnimation(self, b"windowOpacity")
        self.fade_in.setDuration(300)
        self.fade_in.setStartValue(0)
        self.fade_in.setEndValue(1)
        
        # 淡出动画
        self.fade_out = QPropertyAnimation(self, b"windowOpacity")
        self.fade_out.setDuration(300)
        self.fade_out.setStartValue(1)
        self.fade_out.setEndValue(0)
        self.fade_out.finished.connect(self.hide)
    
    def showEvent(self, event):
        """显示事件"""
        super().showEvent(event)
        self.fade_in.start()
        
        # 定时关闭
        QTimer.singleShot(self.duration, self.hide_with_animation)
    
    def hide_with_animation(self):
        """带动画隐藏"""
        self.fade_out.start()
    
    def hide(self):
        """隐藏"""
        super().hide()
        self.deleteLater()


class NotificationManager:
    """通知管理器"""
    
    def __init__(self, parent=None):
        self.parent = parent
        self.notifications = []
        self.spacing = 10
    
    def show_notification(self, message: str, duration: int = 3000):
        """显示通知"""
        toast = ToastNotification(message, duration, self.parent)
        
        # 计算位置 (右上角)
        screen_geo = QApplication.desktop().availableGeometry()
        x = screen_geo.width() - toast.width() - 20
        y = 20 + len(self.notifications) * (toast.height() + self.spacing)
        
        toast.move(x, y)
        toast.show()
        
        self.notifications.append(toast)
        
        # 清理已隐藏的通知
        self.cleanup_notifications()
    
    def cleanup_notifications(self):
        """清理已隐藏的通知"""
        self.notifications = [n for n in self.notifications if n.isVisible()]


class AdvancedTabWidget(QTabWidget):
    """高级标签页组件，支持可关闭标签和拖拽排序"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMovable(True)
        self.setTabsClosable(True)
        self.tabCloseRequested.connect(self.close_tab)
        
        # 自定义标签栏
        self.tab_bar = AdvancedTabBar()
        self.setTabBar(self.tab_bar)
    
    def close_tab(self, index):
        """关闭标签页"""
        if index >= 0:
            widget = self.widget(index)
            if widget:
                widget.deleteLater()
            self.removeTab(index)
    
    def add_tab(self, widget: QWidget, title: str, icon: QIcon = None) -> int:
        """添加标签页"""
        index = self.addTab(widget, title)
        if icon:
            self.setTabIcon(index, icon)
        return index


class AdvancedTabBar(QTabBar):
    """高级标签栏，支持拖拽和关闭按钮"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
    
    def mousePressEvent(self, event):
        """鼠标按下事件"""
        if event.button() == Qt.MiddleButton:
            # 中键关闭标签
            tab_index = self.tabAt(event.pos())
            if tab_index >= 0:
                self.tabCloseRequested.emit(tab_index)
        
        super().mousePressEvent(event)
    
    def paintEvent(self, event):
        """自定义绘制"""
        super().paintEvent(event)
        
        # 绘制关闭按钮
        painter = QPainter(self)
        for index in range(self.count()):
            rect = self.tabRect(index)
            close_rect = QRect(rect.right() - 20, rect.top() + 8, 12, 12)
            
            painter.setPen(QPen(QColor("#777777"), 2))
            painter.drawLine(close_rect.topLeft(), close_rect.bottomRight())
            painter.drawLine(close_rect.topRight(), close_rect.bottomLeft())


class ModernSidebar(QWidget):
    """现代化侧边栏"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(240)
        self.setup_ui()
    
    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 标题区域
        title_widget = QWidget()
        title_widget.setFixedHeight(60)
        title_widget.setStyleSheet("""
            QWidget {
                background-color: #2c3e50;
                border-bottom: 1px solid #34495e;
            }
        """)
        
        title_layout = QHBoxLayout()
        title_layout.setContentsMargins(20, 0, 20, 0)
        
        title_label = QLabel("应用名称")
        title_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 18px;
                font-weight: bold;
            }
        """)
        
        title_layout.addWidget(title_label)
        title_widget.setLayout(title_layout)
        
        # 菜单区域
        menu_widget = QWidget()
        menu_widget.setStyleSheet("""
            QWidget {
                background-color: #34495e;
            }
        """)
        
        menu_layout = QVBoxLayout()
        menu_layout.setContentsMargins(0, 20, 0, 20)
        menu_layout.setSpacing(5)
        
        # 菜单项
        menu_items = [
            ("仪表盘", "dashboard"),
            ("设置", "settings"),
            ("用户", "users"),
            ("统计", "analytics"),
            ("帮助", "help")
        ]
        
        for text, icon_name in menu_items:
            btn = QPushButton(text)
            btn.setFixedHeight(40)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #bdc3c7;
                    text-align: left;
                    padding-left: 20px;
                    border: none;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background-color: #2c3e50;
                    color: white;
                }
                QPushButton:pressed {
                    background-color: #2980b9;
                }
            """)
            menu_layout.addWidget(btn)
        
        menu_layout.addStretch()
        menu_widget.setLayout(menu_layout)
        
        # 添加到主布局
        layout.addWidget(title_widget)
        layout.addWidget(menu_widget)
        
        self.setLayout(layout)


class DashboardGauge(QWidget):
    """仪表盘组件"""
    
    def __init__(self, title: str = "", min_value: float = 0, max_value: float = 100, parent=None):
        super().__init__(parent)
        self.title = title
        self.min_value = min_value
        self.max_value = max_value
        self.current_value = min_value
        self.setMinimumSize(200, 150)
    
    def set_value(self, value: float):
        """设置当前值"""
        self.current_value = max(self.min_value, min(value, self.max_value))
        self.update()
    
    def paintEvent(self, event):
        """绘制仪表盘"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 计算尺寸
        size = min(self.width(), self.height() - 30)
        rect = QRectF(
            (self.width() - size) / 2,
            10,
            size, size
        )
        
        # 绘制外圆弧
        pen = QPen(QColor("#34495e"), 10)
        painter.setPen(pen)
        painter.drawArc(rect, 45 * 16, 270 * 16)
        
        # 绘制内圆弧 (进度)
        progress_ratio = (self.current_value - self.min_value) / (self.max_value - self.min_value)
        progress_angle = int(270 * progress_ratio)
        
        pen = QPen(QColor("#3498db"), 10)
        painter.setPen(pen)
        painter.drawArc(rect, 45 * 16, -progress_angle)
        
        # 绘制刻度
        self.draw_scale(painter, rect)
        
        # 绘制数值
        painter.setPen(QPen(QColor("#2c3e50")))
        painter.setFont(QFont("Arial", 16, QFont.Bold))
        value_rect = QRectF(rect.x(), rect.center().y() - 10, rect.width(), 40)
        painter.drawText(value_rect, Qt.AlignCenter, f"{self.current_value:.1f}")
        
        # 绘制标题
        painter.setFont(QFont("Arial", 10))
        title_rect = QRectF(0, self.height() - 25, self.width(), 20)
        painter.drawText(title_rect, Qt.AlignCenter, self.title)
    
    def draw_scale(self, painter, rect):
        """绘制刻度"""
        painter.save()
        
        # 绘制主要刻度
        pen = QPen(QColor("#2c3e50"), 2)
        painter.setPen(pen)
        
        for i in range(0, 11):  # 11个主要刻度
            angle = 45 + (270 * i / 10)
            rad = angle * 3.14159 / 180
            
            # 计算内外点
            inner_radius = rect.width() / 2 - 20
            outer_radius = rect.width() / 2 - 5
            
            center = rect.center()
            inner_point = QPointF(
                center.x() + inner_radius * math.cos(rad),
                center.y() - inner_radius * math.sin(rad)
            )
            outer_point = QPointF(
                center.x() + outer_radius * math.cos(rad),
                center.y() - outer_radius * math.sin(rad)
            )
            
            painter.drawLine(inner_point, outer_point)
            
            # 绘制刻度值
            value = self.min_value + (self.max_value - self.min_value) * i / 10
            text_point = QPointF(
                center.x() + (outer_radius + 15) * math.cos(rad),
                center.y() - (outer_radius + 15) * math.sin(rad)
            )
            
            painter.drawText(
                QRectF(text_point.x() - 15, text_point.y() - 10, 30, 20),
                Qt.AlignCenter,
                f"{value:.0f}"
            )
        
        painter.restore()


import math  # 添加math导入用于仪表盘计算


class ModernUIExample(QMainWindow):
    """现代化UI示例"""
    
    def __init__(self):
        super().__init__()
        self.current_theme = Theme.DARK
        self.notification_manager = NotificationManager(self)
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("PyQt 高级现代化UI示例")
        self.setGeometry(100, 100, 1200, 800)
        
        # 应用主题
        self.apply_theme(self.current_theme)
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QHBoxLayout()
        central_widget.setLayout(main_layout)
        
        # 侧边栏
        sidebar = ModernSidebar()
        main_layout.addWidget(sidebar)
        
        # 内容区域
        content_widget = QWidget()
        content_layout = QVBoxLayout()
        content_widget.setLayout(content_layout)
        main_layout.addWidget(content_widget)
        
        # 标题
        title_label = QLabel("高级现代化UI组件库")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("""
            QLabel {
                font-size: 28px;
                font-weight: bold;
                color: #3498db;
                padding: 20px;
            }
        """)
        content_layout.addWidget(title_label)
        
        # 主题选择
        theme_layout = QHBoxLayout()
        theme_label = QLabel("选择主题:")
        theme_combo = QComboBox()
        theme_combo.addItems(["Dark", "Light", "Blue", "Green", "Purple"])
        theme_combo.currentTextChanged.connect(self.change_theme)
        
        theme_layout.addWidget(theme_label)
        theme_layout.addWidget(theme_combo)
        theme_layout.addStretch()
        content_layout.addLayout(theme_layout)
        
        # 标签页
        tab_widget = AdvancedTabWidget()
        content_layout.addWidget(tab_widget)
        
        # 按钮标签页
        button_tab = QWidget()
        self.setup_button_tab(button_tab)
        tab_widget.addTab(button_tab, "按钮")
        
        # 进度条标签页
        progress_tab = QWidget()
        self.setup_progress_tab(progress_tab)
        tab_widget.addTab(progress_tab, "进度指示器")
        
        # 卡片标签页
        card_tab = QWidget()
        self.setup_card_tab(card_tab)
        tab_widget.addTab(card_tab, "卡片")
        
        # 仪表盘标签页
        gauge_tab = QWidget()
        self.setup_gauge_tab(gauge_tab)
        tab_widget.addTab(gauge_tab, "仪表盘")
        
        # 状态栏
        self.statusBar().showMessage("就绪")
    
    def apply_theme(self, theme: Theme):
        """应用主题"""
        self.current_theme = theme
        self.setStyleSheet(ThemeManager.get_theme_css(theme))
    
    def change_theme(self, theme_name: str):
        """切换主题"""
        theme_map = {
            "Dark": Theme.DARK,
            "Light": Theme.LIGHT,
            "Blue": Theme.BLUE,
            "Green": Theme.GREEN,
            "Purple": Theme.PURPLE
        }
        
        if theme_name in theme_map:
            self.apply_theme(theme_map[theme_name])
    
    def setup_button_tab(self, parent):
        """设置按钮标签页"""
        layout = QGridLayout()
        parent.setLayout(layout)
        
        # 圆角按钮
        rounded_btn = AdvancedRoundedButton("圆角按钮")
        layout.addWidget(rounded_btn, 0, 0)
        
        # 渐变按钮
        gradient_btn = GradientButton("渐变按钮")
        gradient_btn.set_gradient(QColor("#3498db"), QColor("#2980b9"))
        layout.addWidget(gradient_btn, 0, 1)
        
        # 加载按钮
        loading_btn = AdvancedRoundedButton("加载按钮")
        loading_btn.clicked.connect(lambda: loading_btn.set_loading(True))
        QTimer.singleShot(3000, lambda: loading_btn.set_loading(False))  # 3秒后停止加载
        layout.addWidget(loading_btn, 1, 0)
        
        # 通知按钮
        notify_btn = QPushButton("显示通知")
        notify_btn.clicked.connect(lambda: self.notification_manager.show_notification("这是一个Toast通知!"))
        layout.addWidget(notify_btn, 1, 1)
        
        # 添加阴影效果
        UIEffectManager.add_shadow_effect(rounded_btn)
        UIEffectManager.add_shadow_effect(gradient_btn)
    
    def setup_progress_tab(self, parent):
        """设置进度条标签页"""
        layout = QVBoxLayout()
        parent.setLayout(layout)
        
        # 水平进度条
        h_progress = AnimatedProgressBar()
        h_progress.setValue(75)
        layout.addWidget(QLabel("水平进度条:"))
        layout.addWidget(h_progress)
        
        # 圆形进度条
        circular_progress = CircularProgressBar()
        circular_progress.setValue(75)
        circular_progress.setLineWidth(10)
        layout.addWidget(QLabel("圆形进度条:"))
        
        progress_layout = QHBoxLayout()
        progress_layout.addWidget(circular_progress)
        
        # 控制滑块
        slider = QSlider(Qt.Horizontal)
        slider.setRange(0, 100)
        slider.setValue(75)
        slider.valueChanged.connect(h_progress.setValueAnimated)
        slider.valueChanged.connect(circular_progress.setValue)
        progress_layout.addWidget(slider)
        
        layout.addLayout(progress_layout)
    
    def setup_card_tab(self, parent):
        """设置卡片标签页"""
        layout = QVBoxLayout()
        parent.setLayout(layout)
        
        # 创建卡片容器
        card_container = QWidget()
        card_layout = QHBoxLayout()
        card_container.setLayout(card_layout)
        
        # 创建卡片
        card1 = MaterialCard("卡片标题", "这是一个Material Design风格的卡片组件。")
        card1.set_elevation(3)
        
        card2 = MaterialCard("可调整阴影", "通过set_elevation()方法可以调整阴影级别。")
        card2.set_elevation(1)
        
        card_layout.addWidget(card1)
        card_layout.addWidget(card2)
        
        layout.addWidget(card_container)
        
        # 阴影控制
        shadow_layout = QHBoxLayout()
        shadow_label = QLabel("阴影级别:")
        shadow_slider = QSlider(Qt.Horizontal)
        shadow_slider.setRange(0, 5)
        shadow_slider.setValue(3)
        shadow_slider.valueChanged.connect(card1.set_elevation)
        
        shadow_layout.addWidget(shadow_label)
        shadow_layout.addWidget(shadow_slider)
        layout.addLayout(shadow_layout)
    
    def setup_gauge_tab(self, parent):
        """设置仪表盘标签页"""
        layout = QVBoxLayout()
        parent.setLayout(layout)
        
        # 仪表盘容器
        gauge_container = QWidget()
        gauge_layout = QHBoxLayout()
        gauge_container.setLayout(gauge_layout)
        
        # 创建仪表盘
        gauge1 = DashboardGauge("CPU使用率", 0, 100)
        gauge1.set_value(65)
        
        gauge2 = DashboardGauge("内存使用", 0, 16)
        gauge2.set_value(10.5)
        
        gauge3 = DashboardGauge("温度", -20, 80)
        gauge3.set_value(45)
        
        gauge_layout.addWidget(gauge1)
        gauge_layout.addWidget(gauge2)
        gauge_layout.addWidget(gauge3)
        
        layout.addWidget(gauge_container)
        
        # 控制区域
        control_layout = QHBoxLayout()
        control_label = QLabel("仪表盘值:")
        control_slider = QSlider(Qt.Horizontal)
        control_slider.setRange(0, 100)
        control_slider.setValue(65)
        control_slider.valueChanged.connect(lambda v: gauge1.set_value(v))
        
        control_layout.addWidget(control_label)
        control_layout.addWidget(control_slider)
        layout.addLayout(control_layout)


class UIEffectManager:
    """UI效果管理器"""
    
    @staticmethod
    def add_shadow_effect(widget: QWidget, blur_radius: int = 10, offset: tuple = (0, 0), color: QColor = None):
        """添加阴影效果"""
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(blur_radius)
        shadow.setOffset(*offset)
        
        if color:
            shadow.setColor(color)
        else:
            shadow.setColor(QColor(0, 0, 0, 80))
            
        widget.setGraphicsEffect(shadow)
    
    @staticmethod
    def add_fade_animation(widget: QWidget, duration: int = 300):
        """添加淡入淡出动画"""
        fade_animation = QPropertyAnimation(widget, b"windowOpacity")
        fade_animation.setDuration(duration)
        return fade_animation
    
    @staticmethod
    def add_slide_animation(widget: QWidget, duration: int = 300):
        """添加滑动动画"""
        slide_animation = QPropertyAnimation(widget, b"geometry")
        slide_animation.setDuration(duration)
        return slide_animation
    
    @staticmethod
    def add_color_animation(widget: QWidget, property_name: bytes, 
                           start_color: QColor, end_color: QColor, duration: int = 300):
        """添加颜色动画"""
        color_animation = QPropertyAnimation(widget, property_name)
        color_animation.setDuration(duration)
        color_animation.setStartValue(start_color)
        color_animation.setEndValue(end_color)
        return color_animation


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 设置应用程序样式
    app.setStyle("Fusion")
    
    # 设置应用程序字体
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    
    # 创建并显示主窗口
    window = ModernUIExample()
    window.show()
    
    # 显示欢迎通知
    QTimer.singleShot(1000, lambda: window.notification_manager.show_notification("欢迎使用高级UI组件库!"))
    
    sys.exit(app.exec_())