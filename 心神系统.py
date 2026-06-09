import sys
import os
import logging
from typing import Dict, Any, Optional, Callable
from datetime import datetime

from PyQt5.QtCore import (QObject, QTimer, pyqtSignal, QPropertyAnimation, 
                         QEasingCurve, QPoint, QRect, QSize, Qt, QThread)
from PyQt5.QtGui import (QFont, QFontDatabase, QIcon, QPixmap, QColor, 
                        QPainter, QLinearGradient, QPalette)
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QLabel, QPushButton, QFrame, 
                           QMessageBox, QProgressBar, QTextEdit, QTabWidget,
                           QSystemTrayIcon, QMenu, QAction, QStyle)

# 设置日志系统
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("xinshen_system.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("XinShenSystem")

class XinShenTheme:
    """心神系统主题管理类"""
    
    THEMES = {
        "light": {
            "primary": "#3498db",
            "secondary": "#2ecc71",
            "accent": "#e74c3c",
            "background": "#ecf0f1",
            "surface": "#ffffff",
            "text_primary": "#2c3e50",
            "text_secondary": "#7f8c8d",
            "border": "#bdc3c7"
        },
        "dark": {
            "primary": "#2980b9",
            "secondary": "#27ae60",
            "accent": "#c0392b",
            "background": "#2c3e50",
            "surface": "#34495e",
            "text_primary": "#ecf0f1",
            "text_secondary": "#bdc3c7",
            "border": "#7f8c8d"
        },
        "purple": {
            "primary": "#9b59b6",
            "secondary": "#8e44ad",
            "accent": "#e67e22",
            "background": "#1a1a2e",
            "surface": "#16213e",
            "text_primary": "#e6e6e6",
            "text_secondary": "#b8b8b8",
            "border": "#4a4a6a"
        }
    }
    
    def __init__(self, theme_name: str = "light"):
        self.current_theme = theme_name
        self.colors = self.THEMES.get(theme_name, self.THEMES["light"])
    
    def apply_theme(self, app: QApplication):
        """应用主题到整个应用程序"""
        palette = QPalette()
        
        # 设置调色板颜色
        palette.setColor(QPalette.Window, QColor(self.colors["background"]))
        palette.setColor(QPalette.WindowText, QColor(self.colors["text_primary"]))
        palette.setColor(QPalette.Base, QColor(self.colors["surface"]))
        palette.setColor(QPalette.AlternateBase, QColor(self.colors["background"]))
        palette.setColor(QPalette.ToolTipBase, QColor(self.colors["primary"]))
        palette.setColor(QPalette.ToolTipText, QColor(self.colors["text_primary"]))
        palette.setColor(QPalette.Text, QColor(self.colors["text_primary"]))
        palette.setColor(QPalette.Button, QColor(self.colors["surface"]))
        palette.setColor(QPalette.ButtonText, QColor(self.colors["text_primary"]))
        palette.setColor(QPalette.BrightText, QColor(self.colors["accent"]))
        palette.setColor(QPalette.Highlight, QColor(self.colors["primary"]))
        palette.setColor(QPalette.HighlightedText, QColor(self.colors["text_primary"]))
        
        app.setPalette(palette)
        app.setStyle("Fusion")  # 使用Fusion风格以获得更好的跨平台体验
    
    def set_theme(self, theme_name: str):
        """切换主题"""
        if theme_name in self.THEMES:
            self.current_theme = theme_name
            self.colors = self.THEMES[theme_name]
            return True
        return False
    
    def get_color(self, color_name: str) -> str:
        """获取主题颜色"""
        return self.colors.get(color_name, "#000000")


class XinShenAnimation:
    """心神系统动画效果类"""
    
    @staticmethod
    def fade_in(widget: QWidget, duration: int = 300):
        """淡入动画"""
        animation = QPropertyAnimation(widget, b"windowOpacity")
        animation.setDuration(duration)
        animation.setStartValue(0)
        animation.setEndValue(1)
        animation.setEasingCurve(QEasingCurve.InOutCubic)
        animation.start()
    
    @staticmethod
    def fade_out(widget: QWidget, duration: int = 300):
        """淡出动画"""
        animation = QPropertyAnimation(widget, b"windowOpacity")
        animation.setDuration(duration)
        animation.setStartValue(1)
        animation.setEndValue(0)
        animation.setEasingCurve(QEasingCurve.InOutCubic)
        animation.start()
    
    @staticmethod
    def slide_in(widget: QWidget, direction: str = "right", duration: int = 300):
        """滑动进入动画"""
        start_pos = QPoint(0, 0)
        end_pos = QPoint(0, 0)
        parent_rect = widget.parent().rect() if widget.parent() else QRect(0, 0, 800, 600)
        
        if direction == "right":
            start_pos = QPoint(parent_rect.width(), 0)
        elif direction == "left":
            start_pos = QPoint(-widget.width(), 0)
        elif direction == "top":
            start_pos = QPoint(0, -widget.height())
        elif direction == "bottom":
            start_pos = QPoint(0, parent_rect.height())
        
        widget.move(start_pos)
        widget.show()
        
        animation = QPropertyAnimation(widget, b"pos")
        animation.setDuration(duration)
        animation.setStartValue(start_pos)
        animation.setEndValue(end_pos)
        animation.setEasingCurve(QEasingCurve.OutCubic)
        animation.start()
    
    @staticmethod
    def pulse(widget: QWidget, duration: int = 1000):
        """脉冲动画效果"""
        animation = QPropertyAnimation(widget, b"geometry")
        animation.setDuration(duration)
        animation.setLoopCount(-1)  # 无限循环
        
        original_rect = widget.geometry()
        scaled_rect = QRect(
            original_rect.x() - 5,
            original_rect.y() - 5,
            original_rect.width() + 10,
            original_rect.height() + 10
        )
        
        animation.setKeyValueAt(0, original_rect)
        animation.setKeyValueAt(0.5, scaled_rect)
        animation.setKeyValueAt(1, original_rect)
        
        animation.start()


class XinShenButton(QPushButton):
    """心神系统自定义按钮"""
    
    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self.setMinimumHeight(35)
        self.setCursor(Qt.PointingHandCursor)
        
        # 设置默认样式
        self.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #21618c;
            }
        """)


class XinShenProgressBar(QProgressBar):
    """心神系统自定义进度条"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTextVisible(True)
        self.setMinimum(0)
        self.setMaximum(100)
        
        # 设置样式
        self.setStyleSheet("""
            QProgressBar {
                border: 2px solid #bdc3c7;
                border-radius: 5px;
                text-align: center;
                background-color: #ecf0f1;
            }
            QProgressBar::chunk {
                background-color: #2ecc71;
                border-radius: 3px;
            }
        """)


class XinShenCard(QFrame):
    """心神系统卡片组件"""
    
    def __init__(self, title: str = "", parent=None):
        super().__init__(parent)
        self.title = title
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        # 标题标签
        if self.title:
            title_label = QLabel(self.title)
            title_font = QFont()
            title_font.setBold(True)
            title_font.setPointSize(12)
            title_label.setFont(title_font)
            layout.addWidget(title_label)
        
        # 内容区域
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.content_widget)
        
        # 设置样式
        self.setStyleSheet("""
            XinShenCard {
                background-color: white;
                border: 1px solid #bdc3c7;
                border-radius: 8px;
            }
        """)


class XinShenWorker(QThread):
    """心神系统后台工作线程"""
    
    # 定义信号
    progress_updated = pyqtSignal(int)
    result_ready = pyqtSignal(object)
    error_occurred = pyqtSignal(str)
    finished_signal = pyqtSignal()
    
    def __init__(self, task_func: Callable, *args, **kwargs):
        super().__init__()
        self.task_func = task_func
        self.args = args
        self.kwargs = kwargs
        self.is_running = True
    
    def run(self):
        """执行任务"""
        try:
            result = self.task_func(*self.args, **self.kwargs)
            self.result_ready.emit(result)
        except Exception as e:
            self.error_occurred.emit(str(e))
        finally:
            self.finished_signal.emit()
    
    def stop(self):
        """停止任务"""
        self.is_running = False


class XinShenLogger(QTextEdit):
    """心神系统日志显示组件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setMaximumHeight(150)
        
        # 设置样式
        self.setStyleSheet("""
            QTextEdit {
                background-color: #2c3e50;
                color: #ecf0f1;
                border: 1px solid #34495e;
                border-radius: 5px;
                font-family: Consolas, monospace;
            }
        """)
    
    def log(self, message: str, level: str = "INFO"):
        """添加日志消息"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        color = {
            "INFO": "#3498db",
            "WARNING": "#f39c12",
            "ERROR": "#e74c3c",
            "SUCCESS": "#2ecc71"
        }.get(level, "#3498db")
        
        html_message = f"""
            <div style="margin: 2px 0;">
                <span style="color: #95a5a6;">[{timestamp}]</span>
                <span style="color: {color}; font-weight: bold;">[{level}]</span>
                <span style="color: #ecf0f1;"> {message}</span>
            </div>
        """
        
        self.append(html_message)
        # 自动滚动到底部
        self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())
    
    def clear_logs(self):
        """清空日志"""
        self.clear()


class XinShenSystemTray(QSystemTrayIcon):
    """心神系统托盘图标"""
    
    def __init__(self, icon_path: str, parent=None):
        super().__init__(QIcon(icon_path), parent)
        self.parent = parent
        
        # 创建托盘菜单
        self.menu = QMenu(parent)
        
        self.show_action = QAction("显示主窗口", self)
        self.show_action.triggered.connect(self.show_parent)
        
        self.hide_action = QAction("隐藏主窗口", self)
        self.hide_action.triggered.connect(self.hide_parent)
        
        self.quit_action = QAction("退出", self)
        self.quit_action.triggered.connect(self.quit_application)
        
        self.menu.addAction(self.show_action)
        self.menu.addAction(self.hide_action)
        self.menu.addSeparator()
        self.menu.addAction(self.quit_action)
        
        self.setContextMenu(self.menu)
        self.activated.connect(self.on_tray_activated)
        
        # 显示托盘图标
        self.show()
        self.showMessage("心神系统", "应用程序已启动", QSystemTrayIcon.Information, 2000)
    
    def on_tray_activated(self, reason):
        """托盘图标激活事件"""
        if reason == QSystemTrayIcon.DoubleClick:
            if self.parent.isVisible():
                self.hide_parent()
            else:
                self.show_parent()
    
    def show_parent(self):
        """显示主窗口"""
        if self.parent:
            self.parent.show()
            self.parent.activateWindow()
    
    def hide_parent(self):
        """隐藏主窗口"""
        if self.parent:
            self.parent.hide()
    
    def quit_application(self):
        """退出应用程序"""
        if self.parent:
            self.parent.close()


class XinShenMainWindow(QMainWindow):
    """心神系统主窗口"""
    
    def __init__(self):
        super().__init__()
        self.theme_manager = XinShenTheme("light")
        # 先初始化logger为None
        self.logger = None
        self.setup_ui()
        self.setup_tray()
        
        logger.info("心神系统主窗口初始化完成")
    
    def setup_ui(self):
        """设置用户界面"""
        self.setWindowTitle("心神系统 - 高级工具库")
        self.setGeometry(100, 100, 1000, 700)
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # 创建标题
        title_label = QLabel("心神系统 - 高级工具库")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)
        
        # 创建选项卡
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        # 先创建日志组件，然后再设置各个选项卡
        main_layout.addWidget(QLabel("系统日志:"))
        self.logger = XinShenLogger()
        main_layout.addWidget(self.logger)
        
        # 添加各个功能选项卡
        self.setup_animation_tab()
        self.setup_theme_tab()
        self.setup_worker_tab()
        self.setup_log_tab()
        
        # 记录初始化完成
        self.logger.log("心神系统初始化完成", "SUCCESS")
    
    def setup_animation_tab(self):
        """设置动画演示选项卡"""
        animation_tab = QWidget()
        layout = QVBoxLayout(animation_tab)
        
        # 创建卡片
        card = XinShenCard("动画效果演示")
        
        # 添加动画演示按钮
        btn_fade = XinShenButton("淡入淡出动画")
        btn_fade.clicked.connect(self.demo_fade_animation)
        
        btn_slide = XinShenButton("滑动动画")
        btn_slide.clicked.connect(self.demo_slide_animation)
        
        btn_pulse = XinShenButton("脉冲动画")
        btn_pulse.clicked.connect(self.demo_pulse_animation)
        
        # 添加到卡片布局
        card.content_layout.addWidget(btn_fade)
        card.content_layout.addWidget(btn_slide)
        card.content_layout.addWidget(btn_pulse)
        
        layout.addWidget(card)
        self.tab_widget.addTab(animation_tab, "动画效果")
    
    def setup_theme_tab(self):
        """设置主题切换选项卡"""
        theme_tab = QWidget()
        layout = QVBoxLayout(theme_tab)
        
        # 创建卡片
        card = XinShenCard("主题切换")
        
        # 添加主题切换按钮
        btn_light = XinShenButton("浅色主题")
        btn_light.clicked.connect(lambda: self.change_theme("light"))
        
        btn_dark = XinShenButton("深色主题")
        btn_dark.clicked.connect(lambda: self.change_theme("dark"))
        
        btn_purple = XinShenButton("紫色主题")
        btn_purple.clicked.connect(lambda: self.change_theme("purple"))
        
        # 添加到卡片布局
        card.content_layout.addWidget(btn_light)
        card.content_layout.addWidget(btn_dark)
        card.content_layout.addWidget(btn_purple)
        
        layout.addWidget(card)
        self.tab_widget.addTab(theme_tab, "主题切换")
    
    def setup_worker_tab(self):
        """设置后台任务选项卡"""
        worker_tab = QWidget()
        layout = QVBoxLayout(worker_tab)
        
        # 创建卡片
        card = XinShenCard("后台任务演示")
        
        # 添加进度条
        self.progress_bar = XinShenProgressBar()
        card.content_layout.addWidget(self.progress_bar)
        
        # 添加任务控制按钮
        btn_start = XinShenButton("开始任务")
        btn_start.clicked.connect(self.start_worker_task)
        
        btn_stop = XinShenButton("停止任务")
        btn_stop.clicked.connect(self.stop_worker_task)
        
        # 添加到卡片布局
        card.content_layout.addWidget(btn_start)
        card.content_layout.addWidget(btn_stop)
        
        layout.addWidget(card)
        self.tab_widget.addTab(worker_tab, "后台任务")
        
        # 初始化工作线程
        self.worker = None
    
    def setup_log_tab(self):
        """设置日志管理选项卡"""
        log_tab = QWidget()
        layout = QVBoxLayout(log_tab)
        
        # 创建卡片
        card = XinShenCard("日志管理")
        
        # 添加日志控制按钮
        btn_info = XinShenButton("添加INFO日志")
        btn_info.clicked.connect(lambda: self.logger.log("这是一条INFO级别的日志", "INFO"))
        
        btn_warning = XinShenButton("添加WARNING日志")
        btn_warning.clicked.connect(lambda: self.logger.log("这是一条WARNING级别的日志", "WARNING"))
        
        btn_error = XinShenButton("添加ERROR日志")
        btn_error.clicked.connect(lambda: self.logger.log("这是一条ERROR级别的日志", "ERROR"))
        
        btn_success = XinShenButton("添加SUCCESS日志")
        btn_success.clicked.connect(lambda: self.logger.log("这是一条SUCCESS级别的日志", "SUCCESS"))
        
        btn_clear = XinShenButton("清空日志")
        btn_clear.clicked.connect(self.logger.clear_logs)
        
        # 添加到卡片布局
        card.content_layout.addWidget(btn_info)
        card.content_layout.addWidget(btn_warning)
        card.content_layout.addWidget(btn_error)
        card.content_layout.addWidget(btn_success)
        card.content_layout.addWidget(btn_clear)
        
        layout.addWidget(card)
        self.tab_widget.addTab(log_tab, "日志管理")
    
    def setup_tray(self):
        """设置系统托盘"""
        # 创建托盘图标（使用系统默认图标）
        icon = self.style().standardIcon(QStyle.SP_ComputerIcon)
        self.tray_icon = XinShenSystemTray(icon, self)
    
    def demo_fade_animation(self):
        """演示淡入淡出动画"""
        self.logger.log("开始演示淡入淡出动画", "INFO")
        XinShenAnimation.fade_out(self, 500)
        QTimer.singleShot(600, lambda: XinShenAnimation.fade_in(self, 500))
    
    def demo_slide_animation(self):
        """演示滑动动画"""
        self.logger.log("开始演示滑动动画", "INFO")
        
        # 创建一个临时窗口演示滑动效果
        temp_window = QWidget(self, Qt.Popup)
        temp_window.setGeometry(100, 100, 200, 100)
        temp_window.setStyleSheet("background-color: #3498db; color: white;")
        
        label = QLabel("滑动演示窗口", temp_window)
        label.setAlignment(Qt.AlignCenter)
        label.setGeometry(0, 0, 200, 100)
        
        XinShenAnimation.slide_in(temp_window, "right", 500)
        QTimer.singleShot(2000, temp_window.close)
    
    def demo_pulse_animation(self):
        """演示脉冲动画"""
        self.logger.log("开始演示脉冲动画", "INFO")
        
        # 对标题进行脉冲动画
        title_label = self.centralWidget().layout().itemAt(0).widget()
        XinShenAnimation.pulse(title_label, 1000)
        
        # 3秒后停止动画
        QTimer.singleShot(3000, lambda: title_label.setGeometry(title_label.geometry()))
    
    def change_theme(self, theme_name: str):
        """切换主题"""
        if self.theme_manager.set_theme(theme_name):
            self.theme_manager.apply_theme(QApplication.instance())
            self.logger.log(f"已切换到 {theme_name} 主题", "SUCCESS")
        else:
            self.logger.log(f"主题 {theme_name} 不存在", "ERROR")
    
    def start_worker_task(self):
        """开始后台任务"""
        if self.worker and self.worker.isRunning():
            self.logger.log("任务已在运行中", "WARNING")
            return
        
        # 模拟长时间任务
        def long_running_task():
            import time
            for i in range(1, 101):
                if not QThread.currentThread().is_running:
                    return
                time.sleep(0.05)  # 模拟工作
                self.progress_bar.setValue(i)
            return "任务完成"
        
        self.worker = XinShenWorker(long_running_task)
        self.worker.progress_updated.connect(self.progress_bar.setValue)
        self.worker.result_ready.connect(lambda result: self.logger.log(result, "SUCCESS"))
        self.worker.error_occurred.connect(lambda error: self.logger.log(f"任务错误: {error}", "ERROR"))
        self.worker.finished_signal.connect(lambda: self.logger.log("任务已完成", "INFO"))
        
        self.worker.start()
        self.logger.log("后台任务已开始", "INFO")
    
    def stop_worker_task(self):
        """停止后台任务"""
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait()
            self.logger.log("后台任务已停止", "WARNING")
        else:
            self.logger.log("没有运行中的任务", "INFO")
    
    def closeEvent(self, event):
        """重写关闭事件"""
        reply = QMessageBox.question(
            self, "确认退出", 
            "确定要退出心神系统吗？", 
            QMessageBox.Yes | QMessageBox.No, 
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # 停止所有工作线程
            if self.worker and self.worker.isRunning():
                self.worker.stop()
                self.worker.wait()
            
            self.logger.log("心神系统已关闭", "INFO")
            event.accept()
        else:
            event.ignore()


def main():
    """主函数"""
    app = QApplication(sys.argv)
    
    # 设置应用程序属性
    app.setApplicationName("心神系统")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("心神科技")
    
    # 创建并显示主窗口
    window = XinShenMainWindow()
    window.show()
    
    # 应用默认主题
    window.theme_manager.apply_theme(app)
    
    # 添加启动动画
    XinShenAnimation.fade_in(window, 1000)
    
    logger.info("心神系统启动成功")
    
    # 运行应用程序
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()