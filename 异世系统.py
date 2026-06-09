import sys
import os
import json
import sqlite3
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QTextEdit, 
                             QListWidget, QListWidgetItem, QTabWidget, 
                             QTreeWidget, QTreeWidgetItem, QTableWidget, 
                             QTableWidgetItem, QHeaderView, QSplitter, 
                             QProgressBar, QMessageBox, QFileDialog, 
                             QInputDialog, QLineEdit, QComboBox, QCheckBox,
                             QGroupBox, QSpinBox, QDoubleSpinBox, QSlider,
                             QCalendarWidget, QDateTimeEdit, QMenu, QAction,
                             QSystemTrayIcon, QStyle, QToolBar, QStatusBar)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QSettings, QSize, QDate
from PyQt5.QtGui import QIcon, QFont, QPalette, QColor, QPixmap, QPainter
from PyQt5.QtChart import QChart, QChartView, QLineSeries, QValueAxis


# ========== 日志系统 ==========
class AdvancedLogger:
    """高级日志系统"""
    
    def __init__(self, name="异世系统"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        
        # 创建格式化器
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # 控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # 文件处理器
        file_handler = logging.FileHandler(f"{name}_system.log", encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
    
    def info(self, msg):
        self.logger.info(msg)
    
    def warning(self, msg):
        self.logger.warning(msg)
    
    def error(self, msg):
        self.logger.error(msg)
    
    def debug(self, msg):
        self.logger.debug(msg)


# ========== 数据库管理器 ==========
class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self, db_path="异世系统.db"):
        self.db_path = db_path
        self.connection = None
        self.connect()
        self.init_tables()
    
    def connect(self):
        """连接数据库"""
        try:
            self.connection = sqlite3.connect(self.db_path)
            self.connection.row_factory = sqlite3.Row
        except sqlite3.Error as e:
            print(f"数据库连接错误: {e}")
    
    def init_tables(self):
        """初始化数据表"""
        try:
            cursor = self.connection.cursor()
            
            # 创建系统配置表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS system_config (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT UNIQUE NOT NULL,
                    value TEXT,
                    description TEXT,
                    created_time DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 创建任务记录表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS task_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    start_time DATETIME,
                    end_time DATETIME,
                    result TEXT,
                    parameters TEXT,
                    created_time DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 创建用户数据表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT NOT NULL,
                    name TEXT NOT NULL,
                    data TEXT,
                    tags TEXT,
                    created_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_time DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            self.connection.commit()
        except sqlite3.Error as e:
            print(f"初始化数据表错误: {e}")
    
    def execute_query(self, query, params=None):
        """执行查询"""
        try:
            cursor = self.connection.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            return cursor
        except sqlite3.Error as e:
            print(f"查询执行错误: {e}")
            return None
    
    def get_config(self, key, default=None):
        """获取配置"""
        cursor = self.execute_query("SELECT value FROM system_config WHERE key = ?", (key,))
        result = cursor.fetchone()
        return result['value'] if result else default
    
    def set_config(self, key, value, description=""):
        """设置配置"""
        self.execute_query(
            "INSERT OR REPLACE INTO system_config (key, value, description) VALUES (?, ?, ?)",
            (key, value, description)
        )
        self.connection.commit()


# ========== 异步任务系统 ==========
class WorkerThread(QThread):
    """工作线程"""
    
    progress_signal = pyqtSignal(int)
    result_signal = pyqtSignal(object)
    message_signal = pyqtSignal(str)
    
    def __init__(self, task_func, *args, **kwargs):
        super().__init__()
        self.task_func = task_func
        self.args = args
        self.kwargs = kwargs
        self.is_running = True
    
    def run(self):
        """执行任务"""
        try:
            self.message_signal.emit("任务开始执行...")
            result = self.task_func(*self.args, **self.kwargs)
            self.result_signal.emit(result)
            self.message_signal.emit("任务完成!")
        except Exception as e:
            self.message_signal.emit(f"任务错误: {str(e)}")
            self.result_signal.emit(None)
    
    def stop(self):
        """停止任务"""
        self.is_running = False


class TaskManager:
    """任务管理器"""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.workers = {}
        self.task_id_counter = 0
    
    def start_task(self, task_name, task_func, *args, **kwargs):
        """启动任务"""
        task_id = self.task_id_counter
        self.task_id_counter += 1
        
        # 记录任务开始
        self.db_manager.execute_query(
            "INSERT INTO task_records (task_name, status, start_time) VALUES (?, ?, ?)",
            (task_name, "运行中", datetime.now())
        )
        self.db_manager.connection.commit()
        
        # 创建工作线程
        worker = WorkerThread(task_func, *args, **kwargs)
        worker.result_signal.connect(lambda result: self.on_task_finished(task_id, task_name, result))
        worker.message_signal.connect(lambda msg: self.on_task_message(task_id, msg))
        
        self.workers[task_id] = worker
        worker.start()
        
        return task_id
    
    def on_task_finished(self, task_id, task_name, result):
        """任务完成回调"""
        status = "成功" if result is not None else "失败"
        
        self.db_manager.execute_query(
            "UPDATE task_records SET status = ?, end_time = ?, result = ? WHERE task_name = ? AND status = '运行中'",
            (status, datetime.now(), str(result), task_name)
        )
        self.db_manager.connection.commit()
        
        if task_id in self.workers:
            del self.workers[task_id]
    
    def on_task_message(self, task_id, message):
        """任务消息回调"""
        print(f"任务 {task_id}: {message}")


# ========== 主题管理器 ==========
class ThemeManager:
    """主题管理器"""
    
    def __init__(self):
        self.themes = {
            "暗黑主题": self.dark_theme(),
            "明亮主题": self.light_theme(),
            "蓝色主题": self.blue_theme(),
            "绿色主题": self.green_theme()
        }
        self.current_theme = "暗黑主题"
    
    def dark_theme(self):
        """暗黑主题"""
        return {
            "background": "#2b2b2b",
            "foreground": "#ffffff",
            "primary": "#bb86fc",
            "secondary": "#03dac6",
            "accent": "#cf6679",
            "text": "#ffffff",
            "border": "#444444"
        }
    
    def light_theme(self):
        """明亮主题"""
        return {
            "background": "#ffffff",
            "foreground": "#000000",
            "primary": "#6200ee",
            "secondary": "#03dac6",
            "accent": "#cf6679",
            "text": "#000000",
            "border": "#dddddd"
        }
    
    def blue_theme(self):
        """蓝色主题"""
        return {
            "background": "#1a237e",
            "foreground": "#ffffff",
            "primary": "#5c6bc0",
            "secondary": "#29b6f6",
            "accent": "#ff7043",
            "text": "#e8eaf6",
            "border": "#3949ab"
        }
    
    def green_theme(self):
        """绿色主题"""
        return {
            "background": "#1b5e20",
            "foreground": "#ffffff",
            "primary": "#4caf50",
            "secondary": "#81c784",
            "accent": "#ff9800",
            "text": "#e8f5e9",
            "border": "#388e3c"
        }
    
    def apply_theme(self, app, theme_name):
        """应用主题"""
        if theme_name not in self.themes:
            theme_name = "暗黑主题"
        
        self.current_theme = theme_name
        theme = self.themes[theme_name]
        
        # 设置应用程序样式
        app.setStyle("Fusion")
        
        # 创建调色板
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(theme["background"]))
        palette.setColor(QPalette.WindowText, QColor(theme["text"]))
        palette.setColor(QPalette.Base, QColor(theme["background"]))
        palette.setColor(QPalette.AlternateBase, QColor(theme["primary"]))
        palette.setColor(QPalette.ToolTipBase, QColor(theme["foreground"]))
        palette.setColor(QPalette.ToolTipText, QColor(theme["text"]))
        palette.setColor(QPalette.Text, QColor(theme["text"]))
        palette.setColor(QPalette.Button, QColor(theme["background"]))
        palette.setColor(QPalette.ButtonText, QColor(theme["text"]))
        palette.setColor(QPalette.BrightText, QColor(theme["accent"]))
        palette.setColor(QPalette.Highlight, QColor(theme["primary"]))
        palette.setColor(QPalette.HighlightedText, QColor(theme["background"]))
        
        app.setPalette(palette)
        
        # 设置样式表
        style_sheet = f"""
            QMainWindow {{
                background-color: {theme["background"]};
                color: {theme["text"]};
            }}
            QWidget {{
                background-color: {theme["background"]};
                color: {theme["text"]};
                border: 1px solid {theme["border"]};
            }}
            QPushButton {{
                background-color: {theme["primary"]};
                color: {theme["background"]};
                border: none;
                padding: 5px 10px;
                border-radius: 3px;
            }}
            QPushButton:hover {{
                background-color: {theme["secondary"]};
            }}
            QTabWidget::pane {{
                border: 1px solid {theme["border"]};
            }}
            QTabBar::tab {{
                background-color: {theme["background"]};
                color: {theme["text"]};
                padding: 8px 20px;
                border: 1px solid {theme["border"]};
            }}
            QTabBar::tab:selected {{
                background-color: {theme["primary"]};
                color: {theme["background"]};
            }}
            QListWidget {{
                background-color: {theme["background"]};
                color: {theme["text"]};
                border: 1px solid {theme["border"]};
            }}
            QTextEdit {{
                background-color: {theme["background"]};
                color: {theme["text"]};
                border: 1px solid {theme["border"]};
            }}
            QLineEdit {{
                background-color: {theme["background"]};
                color: {theme["text"]};
                border: 1px solid {theme["border"]};
                padding: 5px;
            }}
        """
        
        app.setStyleSheet(style_sheet)


# ========== 自定义组件 ==========
class AnimatedButton(QPushButton):
    """动画按钮"""
    
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setMouseTracking(True)
        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self.animate)
        self.animation_step = 0
        self.is_hovered = False
    
    def enterEvent(self, event):
        """鼠标进入事件"""
        self.is_hovered = True
        self.animation_timer.start(30)
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """鼠标离开事件"""
        self.is_hovered = False
        self.animation_timer.start(30)
        super().leaveEvent(event)
    
    def animate(self):
        """动画效果"""
        if self.is_hovered and self.animation_step < 10:
            self.animation_step += 1
        elif not self.is_hovered and self.animation_step > 0:
            self.animation_step -= 1
        else:
            self.animation_timer.stop()
            return
        
        # 计算颜色渐变
        base_color = self.palette().button().color()
        hover_color = QColor(66, 135, 245)  # 蓝色
        
        r = base_color.red() + (hover_color.red() - base_color.red()) * self.animation_step / 10
        g = base_color.green() + (hover_color.green() - base_color.green()) * self.animation_step / 10
        b = base_color.blue() + (hover_color.blue() - base_color.blue()) * self.animation_step / 10
        
        color = QColor(int(r), int(g), int(b))
        
        # 应用样式
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: rgb({color.red()}, {color.green()}, {color.blue()});
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 15px;
            }}
        """)


class DataTableWidget(QTableWidget):
    """数据表格组件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QTableWidget.SelectRows)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.verticalHeader().setVisible(False)
    
    def load_data(self, data, headers=None):
        """加载数据"""
        if not data:
            return
        
        if headers is None:
            headers = list(data[0].keys()) if data else []
        
        self.setColumnCount(len(headers))
        self.setHorizontalHeaderLabels(headers)
        self.setRowCount(len(data))
        
        for row_idx, row_data in enumerate(data):
            for col_idx, header in enumerate(headers):
                value = row_data.get(header, "") if isinstance(row_data, dict) else row_data[col_idx]
                item = QTableWidgetItem(str(value))
                self.setItem(row_idx, col_idx, item)


class ChartWidget(QWidget):
    """图表组件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.chart = QChart()
        self.chart_view = QChartView(self.chart)
        self.layout.addWidget(self.chart_view)
    
    def create_line_chart(self, title, x_data, y_data, x_title="X轴", y_title="Y轴"):
        """创建折线图"""
        self.chart.removeAllSeries()
        
        series = QLineSeries()
        for x, y in zip(x_data, y_data):
            series.append(x, y)
        
        self.chart.addSeries(series)
        self.chart.setTitle(title)
        self.chart.createDefaultAxes()
        self.chart.axisX().setTitleText(x_title)
        self.chart.axisY().setTitleText(y_title)
        
        self.chart.legend().setVisible(True)
        self.chart.legend().setAlignment(Qt.AlignBottom)


# ========== 主界面 ==========
class MainWindow(QMainWindow):
    """主窗口"""
    
    def __init__(self):
        super().__init__()
        
        # 初始化系统组件
        self.logger = AdvancedLogger("异世系统")
        self.db_manager = DatabaseManager()
        self.task_manager = TaskManager(self.db_manager)
        self.theme_manager = ThemeManager()
        
        # 设置窗口属性
        self.setWindowTitle("异世系统 - 强大高级工具库")
        self.setGeometry(100, 100, 1200, 800)
        
        # 创建中央部件
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # 创建布局
        self.main_layout = QHBoxLayout(self.central_widget)
        
        # 初始化UI
        self.init_ui()
        
        # 加载设置
        self.load_settings()
        
        self.logger.info("异世系统启动成功")
    
    def init_ui(self):
        """初始化用户界面"""
        # 创建左侧导航栏
        self.create_navigation()
        
        # 创建右侧内容区域
        self.create_content_area()
        
        # 创建状态栏
        self.create_status_bar()
        
        # 创建菜单栏
        self.create_menubar()
        
        # 创建工具栏
        self.create_toolbar()
    
    def create_navigation(self):
        """创建导航栏"""
        navigation_widget = QWidget()
        navigation_layout = QVBoxLayout(navigation_widget)
        
        # 系统标题
        title_label = QLabel("异世系统")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setFont(QFont("Arial", 16, QFont.Bold))
        navigation_layout.addWidget(title_label)
        
        # 导航按钮
        nav_buttons = [
            ("系统概览", self.show_system_overview),
            ("数据管理", self.show_data_management),
            ("任务调度", self.show_task_scheduler),
            ("图表分析", self.show_chart_analysis),
            ("系统设置", self.show_system_settings)
        ]
        
        for text, slot in nav_buttons:
            button = AnimatedButton(text)
            button.clicked.connect(slot)
            navigation_layout.addWidget(button)
        
        navigation_layout.addStretch()
        
        # 添加到主布局
        self.main_layout.addWidget(navigation_widget, 1)
    
    def create_content_area(self):
        """创建内容区域"""
        # 创建选项卡部件
        self.tab_widget = QTabWidget()
        self.tab_widget.setDocumentMode(True)
        self.tab_widget.tabBar().setExpanding(True)
        
        # 创建各个功能页面
        self.system_overview_tab = self.create_system_overview()
        self.data_management_tab = self.create_data_management()
        self.task_scheduler_tab = self.create_task_scheduler()
        self.chart_analysis_tab = self.create_chart_analysis()
        self.system_settings_tab = self.create_system_settings()
        
        # 添加选项卡
        self.tab_widget.addTab(self.system_overview_tab, "系统概览")
        self.tab_widget.addTab(self.data_management_tab, "数据管理")
        self.tab_widget.addTab(self.task_scheduler_tab, "任务调度")
        self.tab_widget.addTab(self.chart_analysis_tab, "图表分析")
        self.tab_widget.addTab(self.system_settings_tab, "系统设置")
        
        # 添加到主布局
        self.main_layout.addWidget(self.tab_widget, 4)
    
    def create_system_overview(self):
        """创建系统概览页面"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 系统信息组
        system_group = QGroupBox("系统信息")
        system_layout = QVBoxLayout(system_group)
        
        info_text = QTextEdit()
        info_text.setReadOnly(True)
        info_text.setText(f"""
        异世系统 v1.0
        启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        数据库路径: {self.db_manager.db_path}
        日志文件: 异世系统_system.log
        
        系统功能:
        - 高级数据管理
        - 异步任务调度
        - 多种主题切换
        - 图表数据分析
        - 系统配置管理
        """)
        
        system_layout.addWidget(info_text)
        layout.addWidget(system_group)
        
        # 系统状态组
        status_group = QGroupBox("系统状态")
        status_layout = QVBoxLayout(status_group)
        
        self.status_table = DataTableWidget()
        status_data = [
            {"组件": "数据库", "状态": "正常", "说明": "连接成功"},
            {"组件": "日志系统", "状态": "正常", "说明": "运行中"},
            {"组件": "任务管理器", "状态": "正常", "说明": "就绪"},
            {"组件": "主题管理器", "状态": "正常", "说明": f"当前主题: {self.theme_manager.current_theme}"}
        ]
        self.status_table.load_data(status_data)
        
        status_layout.addWidget(self.status_table)
        layout.addWidget(status_group)
        
        layout.addStretch()
        return widget
    
    def create_data_management(self):
        """创建数据管理页面"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 数据操作工具栏
        toolbar = QHBoxLayout()
        
        add_button = AnimatedButton("添加数据")
        add_button.clicked.connect(self.add_data)
        toolbar.addWidget(add_button)
        
        edit_button = AnimatedButton("编辑数据")
        edit_button.clicked.connect(self.edit_data)
        toolbar.addWidget(edit_button)
        
        delete_button = AnimatedButton("删除数据")
        delete_button.clicked.connect(self.delete_data)
        toolbar.addWidget(delete_button)
        
        refresh_button = AnimatedButton("刷新数据")
        refresh_button.clicked.connect(self.refresh_data)
        toolbar.addWidget(refresh_button)
        
        layout.addLayout(toolbar)
        
        # 数据表格
        self.data_table = DataTableWidget()
        layout.addWidget(self.data_table)
        
        # 加载示例数据
        self.load_sample_data()
        
        return widget
    
    def create_task_scheduler(self):
        """创建任务调度页面"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 任务创建区域
        task_creation_group = QGroupBox("创建新任务")
        task_creation_layout = QVBoxLayout(task_creation_group)
        
        # 任务名称输入
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("任务名称:"))
        self.task_name_input = QLineEdit()
        name_layout.addWidget(self.task_name_input)
        task_creation_layout.addLayout(name_layout)
        
        # 任务类型选择
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("任务类型:"))
        self.task_type_combo = QComboBox()
        self.task_type_combo.addItems(["数据处理", "文件操作", "网络请求", "计算任务"])
        type_layout.addWidget(self.task_type_combo)
        task_creation_layout.addLayout(type_layout)
        
        # 任务参数
        param_layout = QHBoxLayout()
        param_layout.addWidget(QLabel("任务参数:"))
        self.task_param_input = QLineEdit()
        param_layout.addWidget(self.task_param_input)
        task_creation_layout.addLayout(param_layout)
        
        # 创建任务按钮
        create_task_button = AnimatedButton("创建并执行任务")
        create_task_button.clicked.connect(self.create_and_run_task)
        task_creation_layout.addWidget(create_task_button)
        
        layout.addWidget(task_creation_group)
        
        # 任务列表
        task_list_group = QGroupBox("任务列表")
        task_list_layout = QVBoxLayout(task_list_group)
        
        self.task_list = QListWidget()
        task_list_layout.addWidget(self.task_list)
        
        layout.addWidget(task_list_group)
        
        return widget
    
    def create_chart_analysis(self):
        """创建图表分析页面"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 图表控制工具栏
        chart_toolbar = QHBoxLayout()
        
        chart_type_combo = QComboBox()
        chart_type_combo.addItems(["折线图", "柱状图", "饼图", "散点图"])
        chart_toolbar.addWidget(QLabel("图表类型:"))
        chart_toolbar.addWidget(chart_type_combo)
        
        generate_button = AnimatedButton("生成图表")
        generate_button.clicked.connect(lambda: self.generate_sample_chart())
        chart_toolbar.addWidget(generate_button)
        
        layout.addLayout(chart_toolbar)
        
        # 图表显示区域
        self.chart_widget = ChartWidget()
        layout.addWidget(self.chart_widget)
        
        return widget
    
    def create_system_settings(self):
        """创建系统设置页面"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 主题设置
        theme_group = QGroupBox("主题设置")
        theme_layout = QVBoxLayout(theme_group)
        
        theme_combo = QComboBox()
        theme_combo.addItems(list(self.theme_manager.themes.keys()))
        theme_combo.setCurrentText(self.theme_manager.current_theme)
        theme_combo.currentTextChanged.connect(self.change_theme)
        
        theme_layout.addWidget(QLabel("选择主题:"))
        theme_layout.addWidget(theme_combo)
        layout.addWidget(theme_group)
        
        # 系统设置
        system_group = QGroupBox("系统设置")
        system_layout = QVBoxLayout(system_group)
        
        # 自动保存设置
        auto_save_check = QCheckBox("启用自动保存")
        auto_save_check.setChecked(True)
        system_layout.addWidget(auto_save_check)
        
        # 日志级别设置
        log_level_layout = QHBoxLayout()
        log_level_layout.addWidget(QLabel("日志级别:"))
        log_level_combo = QComboBox()
        log_level_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR"])
        log_level_combo.setCurrentText("INFO")
        log_level_layout.addWidget(log_level_combo)
        system_layout.addLayout(log_level_layout)
        
        layout.addWidget(system_group)
        
        # 保存设置按钮
        save_button = AnimatedButton("保存设置")
        save_button.clicked.connect(self.save_settings)
        layout.addWidget(save_button)
        
        layout.addStretch()
        return widget
    
    def create_menubar(self):
        """创建菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu("文件")
        
        new_action = QAction("新建", self)
        new_action.setShortcut("Ctrl+N")
        file_menu.addAction(new_action)
        
        open_action = QAction("打开", self)
        open_action.setShortcut("Ctrl+O")
        file_menu.addAction(open_action)
        
        save_action = QAction("保存", self)
        save_action.setShortcut("Ctrl+S")
        file_menu.addAction(save_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("退出", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 工具菜单
        tools_menu = menubar.addMenu("工具")
        
        data_manager_action = QAction("数据管理器", self)
        data_manager_action.triggered.connect(self.show_data_management)
        tools_menu.addAction(data_manager_action)
        
        task_scheduler_action = QAction("任务调度器", self)
        task_scheduler_action.triggered.connect(self.show_task_scheduler)
        tools_menu.addAction(task_scheduler_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu("帮助")
        
        about_action = QAction("关于", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def create_toolbar(self):
        """创建工具栏"""
        toolbar = QToolBar("主工具栏")
        self.addToolBar(toolbar)
        
        # 添加工具按钮
        refresh_action = QAction("刷新", self)
        refresh_action.triggered.connect(self.refresh_system)
        toolbar.addAction(refresh_action)
        
        settings_action = QAction("设置", self)
        settings_action.triggered.connect(self.show_system_settings)
        toolbar.addAction(settings_action)
    
    def create_status_bar(self):
        """创建状态栏"""
        status_bar = QStatusBar()
        self.setStatusBar(status_bar)
        
        # 状态标签
        self.status_label = QLabel("就绪")
        status_bar.addWidget(self.status_label)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(200)
        self.progress_bar.setVisible(False)
        status_bar.addPermanentWidget(self.progress_bar)
        
        # 时间标签
        self.time_label = QLabel()
        self.update_time()
        status_bar.addPermanentWidget(self.time_label)
        
        # 更新时间定时器
        self.time_timer = QTimer(self)
        self.time_timer.timeout.connect(self.update_time)
        self.time_timer.start(1000)  # 每秒更新一次
    
    def update_time(self):
        """更新时间显示"""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.time_label.setText(current_time)
    
    # ========== 页面切换方法 ==========
    def show_system_overview(self):
        self.tab_widget.setCurrentIndex(0)
    
    def show_data_management(self):
        self.tab_widget.setCurrentIndex(1)
    
    def show_task_scheduler(self):
        self.tab_widget.setCurrentIndex(2)
    
    def show_chart_analysis(self):
        self.tab_widget.setCurrentIndex(3)
    
    def show_system_settings(self):
        self.tab_widget.setCurrentIndex(4)
    
    # ========== 数据管理方法 ==========
    def load_sample_data(self):
        """加载示例数据"""
        sample_data = [
            {"ID": 1, "名称": "示例项目1", "类别": "开发", "状态": "进行中", "创建时间": "2023-01-01"},
            {"ID": 2, "名称": "示例项目2", "类别": "测试", "状态": "已完成", "创建时间": "2023-01-02"},
            {"ID": 3, "名称": "示例项目3", "类别": "文档", "状态": "待开始", "创建时间": "2023-01-03"},
            {"ID": 4, "名称": "示例项目4", "类别": "研究", "状态": "进行中", "创建时间": "2023-01-04"},
        ]
        self.data_table.load_data(sample_data)
    
    def add_data(self):
        """添加数据"""
        name, ok = QInputDialog.getText(self, "添加数据", "请输入名称:")
        if ok and name:
            # 在实际应用中，这里应该将数据保存到数据库
            QMessageBox.information(self, "成功", f"已添加数据: {name}")
            self.refresh_data()
    
    def edit_data(self):
        """编辑数据"""
        current_row = self.data_table.currentRow()
        if current_row >= 0:
            # 在实际应用中，这里应该编辑选中的数据
            QMessageBox.information(self, "编辑", "编辑功能待实现")
        else:
            QMessageBox.warning(self, "警告", "请先选择要编辑的数据行")
    
    def delete_data(self):
        """删除数据"""
        current_row = self.data_table.currentRow()
        if current_row >= 0:
            reply = QMessageBox.question(
                self, "确认删除", 
                "确定要删除选中的数据吗?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                # 在实际应用中，这里应该从数据库删除数据
                self.data_table.removeRow(current_row)
        else:
            QMessageBox.warning(self, "警告", "请先选择要删除的数据行")
    
    def refresh_data(self):
        """刷新数据"""
        self.load_sample_data()
        QMessageBox.information(self, "刷新", "数据已刷新")
    
    # ========== 任务管理方法 ==========
    def create_and_run_task(self):
        """创建并执行任务"""
        task_name = self.task_name_input.text()
        task_type = self.task_type_combo.currentText()
        task_params = self.task_param_input.text()
        
        if not task_name:
            QMessageBox.warning(self, "警告", "请输入任务名称")
            return
        
        # 模拟任务函数
        def sample_task():
            import time
            for i in range(5):
                time.sleep(1)  # 模拟耗时操作
                print(f"任务执行中... {i+1}/5")
            return f"任务完成: {task_name}"
        
        # 启动任务
        task_id = self.task_manager.start_task(task_name, sample_task)
        
        # 添加到任务列表
        item = QListWidgetItem(f"{task_name} - {task_type} - 运行中")
        self.task_list.addItem(item)
        
        self.status_label.setText(f"任务已启动: {task_name}")
        QMessageBox.information(self, "成功", f"任务 '{task_name}' 已启动")
    
    # ========== 图表分析方法 ==========
    def generate_sample_chart(self):
        """生成示例图表"""
        # 示例数据
        x_data = [i for i in range(10)]
        y_data = [i * i for i in range(10)]
        
        self.chart_widget.create_line_chart(
            "示例图表: y = x²", 
            x_data, y_data, 
            "X值", "Y值"
        )
    
    # ========== 主题切换方法 ==========
    def change_theme(self, theme_name):
        """切换主题"""
        self.theme_manager.apply_theme(QApplication.instance(), theme_name)
        self.db_manager.set_config("current_theme", theme_name, "当前主题")
    
    # ========== 设置管理方法 ==========
    def save_settings(self):
        """保存设置"""
        # 在实际应用中，这里应该保存所有设置到数据库
        self.db_manager.set_config("auto_save", "true", "自动保存设置")
        QMessageBox.information(self, "成功", "设置已保存")
    
    def load_settings(self):
        """加载设置"""
        current_theme = self.db_manager.get_config("current_theme", "暗黑主题")
        self.theme_manager.apply_theme(QApplication.instance(), current_theme)
    
    # ========== 系统方法 ==========
    def refresh_system(self):
        """刷新系统"""
        self.status_label.setText("系统刷新中...")
        QTimer.singleShot(1000, lambda: self.status_label.setText("系统已刷新"))
    
    def show_about(self):
        """显示关于对话框"""
        QMessageBox.about(
            self, 
            "关于异世系统",
            "异世系统 v1.0\n\n"
            "一个基于PyQt的强大高级工具库\n"
            "提供数据管理、任务调度、图表分析等功能\n\n"
            "开发团队: 异世开发组\n"
            "版权所有 © 2023"
        )
    
    def closeEvent(self, event):
        """关闭事件处理"""
        reply = QMessageBox.question(
            self, "确认退出",
            "确定要退出异世系统吗?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # 保存设置
            self.save_settings()
            
            # 停止所有任务
            for worker in self.task_manager.workers.values():
                worker.stop()
            
            # 关闭数据库连接
            if self.db_manager.connection:
                self.db_manager.connection.close()
            
            self.logger.info("异世系统正常退出")
            event.accept()
        else:
            event.ignore()


# ========== 应用程序入口 ==========
def main():
    """主函数"""
    # 创建应用程序
    app = QApplication(sys.argv)
    app.setApplicationName("异世系统")
    app.setApplicationVersion("1.0")
    app.setOrganizationName("异世开发组")
    
    # 创建并显示主窗口
    window = MainWindow()
    window.show()
    
    # 运行应用程序
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()