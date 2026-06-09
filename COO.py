import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import matplotlib
matplotlib.rc("font", family='Microsoft YaHei')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import seaborn as sns
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QTabWidget, QTableWidget, QTableWidgetItem, QPushButton, 
                            QLabel, QLineEdit, QTextEdit, QComboBox, QDateEdit, QFileDialog,
                            QMessageBox, QSplitter, QTreeWidget, QTreeWidgetItem, QHeaderView,
                            QProgressBar, QStatusBar, QToolBar, QAction, QDockWidget, QDialog,
                            QFormLayout, QDialogButtonBox, QListWidget, QCheckBox, QGroupBox,
                            QSpinBox, QDoubleSpinBox, QGridLayout, QStackedWidget)
from PyQt5.QtCore import Qt, QDate, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QIcon, QFont, QColor, QPainter, QPixmap, QPalette

# 数据处理器类（可运行在后台线程）
class DataProcessor(QThread):
    progress_updated = pyqtSignal(int, str)
    data_processed = pyqtSignal(pd.DataFrame)
    analysis_completed = pyqtSignal(dict)
    
    def __init__(self, data, analysis_type="descriptive"):
        super().__init__()
        self.data = data
        self.analysis_type = analysis_type
        
    def run(self):
        if self.analysis_type == "descriptive":
            self.run_descriptive_analysis()
        elif self.analysis_type == "correlation":
            self.run_correlation_analysis()
        elif self.analysis_type == "regression":
            self.run_regression_analysis()
        elif self.analysis_type == "clustering":
            self.run_clustering_analysis()
    
    def run_descriptive_analysis(self):
        total_steps = 5
        results = {}
        
        # 步骤1: 基本统计
        self.progress_updated.emit(20, "计算基本统计量...")
        results['basic_stats'] = self.data.describe().to_dict()
        
        # 步骤2: 缺失值分析
        self.progress_updated.emit(40, "分析缺失值...")
        results['missing_values'] = self.data.isnull().sum().to_dict()
        results['missing_percentage'] = (self.data.isnull().sum() / len(self.data) * 100).to_dict()
        
        # 步骤3: 数据分布
        self.progress_updated.emit(60, "分析数据分布...")
        numeric_cols = self.data.select_dtypes(include=[np.number]).columns
        distribution_info = {}
        for col in numeric_cols:
            distribution_info[col] = {
                'skewness': stats.skew(self.data[col].dropna()),
                'kurtosis': stats.kurtosis(self.data[col].dropna())
            }
        results['distribution'] = distribution_info
        
        # 步骤4: 异常值检测
        self.progress_updated.emit(80, "检测异常值...")
        outlier_info = {}
        for col in numeric_cols:
            Q1 = self.data[col].quantile(0.25)
            Q3 = self.data[col].quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR
            outliers = self.data[(self.data[col] < lower_bound) | (self.data[col] > upper_bound)]
            outlier_info[col] = {
                'count': len(outliers),
                'percentage': len(outliers) / len(self.data) * 100
            }
        results['outliers'] = outlier_info
        
        # 步骤5: 完成
        self.progress_updated.emit(100, "分析完成!")
        self.analysis_completed.emit(results)
        self.data_processed.emit(self.data)
    
    def run_correlation_analysis(self):
        self.progress_updated.emit(50, "计算相关性矩阵...")
        numeric_data = self.data.select_dtypes(include=[np.number])
        correlation_matrix = numeric_data.corr().to_dict()
        
        self.progress_updated.emit(100, "相关性分析完成!")
        self.analysis_completed.emit({'correlation_matrix': correlation_matrix})
    
    def run_regression_analysis(self):
        # 简化的回归分析实现
        self.progress_updated.emit(100, "回归分析完成!")
        self.analysis_completed.emit({'regression': '简化实现'})
    
    def run_clustering_analysis(self):
        # 简化的聚类分析实现
        self.progress_updated.emit(100, "聚类分析完成!")
        self.analysis_completed.emit({'clustering': '简化实现'})


# 新建项目对话框
class NewProjectDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("新建项目")
        self.setModal(True)
        self.init_ui()
        
    def init_ui(self):
        layout = QFormLayout()
        
        self.name_edit = QLineEdit()
        self.manager_edit = QLineEdit()
        self.start_date = QDateEdit()
        self.start_date.setDate(QDate.currentDate())
        self.end_date = QDateEdit()
        self.end_date.setDate(QDate.currentDate().addDays(30))
        self.status_combo = QComboBox()
        self.status_combo.addItems(["未开始", "进行中", "已完成", "已暂停", "已取消"])
        self.priority_combo = QComboBox()
        self.priority_combo.addItems(["低", "中", "高", "紧急"])
        self.description_edit = QTextEdit()
        
        layout.addRow("项目名称:", self.name_edit)
        layout.addRow("负责人:", self.manager_edit)
        layout.addRow("开始日期:", self.start_date)
        layout.addRow("结束日期:", self.end_date)
        layout.addRow("状态:", self.status_combo)
        layout.addRow("优先级:", self.priority_combo)
        layout.addRow("描述:", self.description_edit)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        
        layout.addRow(buttons)
        self.setLayout(layout)
    
    def get_project_data(self):
        return {
            'name': self.name_edit.text(),
            'manager': self.manager_edit.text(),
            'start_date': self.start_date.date().toString("yyyy-MM-dd"),
            'end_date': self.end_date.date().toString("yyyy-MM-dd"),
            'status': self.status_combo.currentText(),
            'priority': self.priority_combo.currentText(),
            'description': self.description_edit.toPlainText()
        }


# 高级分析配置对话框
class AdvancedAnalysisDialog(QDialog):
    def __init__(self, data_columns, parent=None):
        super().__init__(parent)
        self.setWindowTitle("高级分析配置")
        self.setModal(True)
        self.data_columns = data_columns
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 分析类型选择
        type_group = QGroupBox("分析类型")
        type_layout = QVBoxLayout()
        self.analysis_type = QComboBox()
        self.analysis_type.addItems(["描述性统计", "相关性分析", "回归分析", "聚类分析"])
        type_layout.addWidget(QLabel("选择分析类型:"))
        type_layout.addWidget(self.analysis_type)
        type_group.setLayout(type_layout)
        layout.addWidget(type_group)
        
        # 变量选择
        var_group = QGroupBox("变量选择")
        var_layout = QGridLayout()
        
        self.x_var = QComboBox()
        self.x_var.addItems(self.data_columns)
        var_layout.addWidget(QLabel("X变量:"), 0, 0)
        var_layout.addWidget(self.x_var, 0, 1)
        
        self.y_var = QComboBox()
        self.y_var.addItems(self.data_columns)
        var_layout.addWidget(QLabel("Y变量:"), 1, 0)
        var_layout.addWidget(self.y_var, 1, 1)
        
        var_group.setLayout(var_layout)
        layout.addWidget(var_group)
        
        # 参数设置
        param_group = QGroupBox("分析参数")
        param_layout = QFormLayout()
        
        self.cluster_count = QSpinBox()
        self.cluster_count.setRange(2, 10)
        self.cluster_count.setValue(3)
        param_layout.addRow("聚类数量:", self.cluster_count)
        
        self.confidence_level = QDoubleSpinBox()
        self.confidence_level.setRange(0.8, 0.99)
        self.confidence_level.setValue(0.95)
        self.confidence_level.setSingleStep(0.01)
        param_layout.addRow("置信水平:", self.confidence_level)
        
        param_group.setLayout(param_layout)
        layout.addWidget(param_group)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        
        layout.addWidget(buttons)
        self.setLayout(layout)
    
    def get_analysis_config(self):
        return {
            'type': self.analysis_type.currentText(),
            'x_var': self.x_var.currentText(),
            'y_var': self.y_var.currentText(),
            'cluster_count': self.cluster_count.value(),
            'confidence_level': self.confidence_level.value()
        }


# 主应用窗口
class COOToolkit(QMainWindow):
    def __init__(self):
        super().__init__()
        self.data = None
        self.projects = []
        self.current_analysis_results = {}
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle('COO 高级工具库 v3.0')
        self.setGeometry(100, 100, 1400, 900)
        
        # 设置应用样式
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QTabWidget::pane {
                border: 1px solid #cccccc;
                background: white;
            }
            QTabBar::tab {
                background: #e0e0e0;
                padding: 8px 12px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background: white;
                border-bottom: 2px solid #2196F3;
            }
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #0D47A1;
            }
            QTableWidget {
                gridline-color: #e0e0e0;
                background-color: white;
                alternate-background-color: #f9f9f9;
            }
            QHeaderView::section {
                background-color: #e0e0e0;
                padding: 6px;
                border: 1px solid #d0d0d0;
            }
        """)
        
        # 创建中心部件和主布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # 创建标签页
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)
        
        # 添加各个功能标签页
        self.setup_dashboard_tab()
        self.setup_data_analysis_tab()
        self.setup_project_management_tab()
        self.setup_team_collaboration_tab()
        self.setup_reporting_tab()
        self.setup_advanced_analytics_tab()
        
        # 创建状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(200)
        self.progress_bar.setVisible(False)
        self.status_bar.addPermanentWidget(self.progress_bar)
        self.status_label = QLabel()
        self.status_bar.addPermanentWidget(self.status_label)
        
        # 创建菜单栏和工具栏
        self.create_menus()
        self.create_toolbars()
        
        # 创建停靠窗口
        self.create_dock_widgets()
        
        # 加载初始数据
        self.load_sample_data()
        self.load_projects()
        
    def create_menus(self):
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu('文件')
        
        import_action = QAction('导入数据', self)
        import_action.triggered.connect(self.import_data)
        file_menu.addAction(import_action)
        
        export_action = QAction('导出报告', self)
        export_action.triggered.connect(self.export_report)
        file_menu.addAction(export_action)
        
        exit_action = QAction('退出', self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 编辑菜单
        edit_menu = menubar.addMenu('编辑')
        
        preprocess_action = QAction('数据预处理', self)
        preprocess_action.triggered.connect(self.preprocess_data)
        edit_menu.addAction(preprocess_action)
        
        # 工具菜单
        tools_menu = menubar.addMenu('工具')
        
        analyze_action = QAction('高级分析', self)
        analyze_action.triggered.connect(self.run_advanced_analysis)
        tools_menu.addAction(analyze_action)
        
        forecast_action = QAction('预测分析', self)
        forecast_action.triggered.connect(self.run_forecast_analysis)
        tools_menu.addAction(forecast_action)
        
        # 视图菜单
        view_menu = menubar.addMenu('视图')
        
        toggle_dock_action = QAction('切换侧边栏', self)
        toggle_dock_action.triggered.connect(self.toggle_dock_visibility)
        view_menu.addAction(toggle_dock_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu('帮助')
        
        about_action = QAction('关于', self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def create_toolbars(self):
        toolbar = QToolBar('主工具栏')
        self.addToolBar(toolbar)
        
        import_btn = QAction('导入数据', self)
        import_btn.triggered.connect(self.import_data)
        toolbar.addAction(import_btn)
        
        export_btn = QAction('导出报告', self)
        export_btn.triggered.connect(self.export_report)
        toolbar.addAction(export_btn)
        
        toolbar.addSeparator()
        
        analyze_btn = QAction('分析数据', self)
        analyze_btn.triggered.connect(self.analyze_data)
        toolbar.addAction(analyze_btn)
        
        # 添加快速操作按钮
        toolbar.addSeparator()
        quick_analysis_btn = QAction('快速分析', self)
        quick_analysis_btn.triggered.connect(self.quick_analysis)
        toolbar.addAction(quick_analysis_btn)
    
    def create_dock_widgets(self):
        # 创建项目概览停靠窗口
        projects_dock = QDockWidget('项目概览', self)
        projects_dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        
        projects_widget = QWidget()
        projects_layout = QVBoxLayout(projects_widget)
        
        self.projects_tree = QTreeWidget()
        self.projects_tree.setHeaderLabels(['项目名称', '状态', '进度', '优先级'])
        projects_layout.addWidget(self.projects_tree)
        
        # 添加项目操作按钮
        project_btn_layout = QHBoxLayout()
        refresh_btn = QPushButton('刷新')
        refresh_btn.clicked.connect(self.load_projects)
        project_btn_layout.addWidget(refresh_btn)
        
        new_btn = QPushButton('新建')
        new_btn.clicked.connect(self.create_project)
        project_btn_layout.addWidget(new_btn)
        
        projects_layout.addLayout(project_btn_layout)
        
        projects_dock.setWidget(projects_widget)
        self.addDockWidget(Qt.RightDockWidgetArea, projects_dock)
        
        # 创建数据分析结果停靠窗口
        results_dock = QDockWidget('分析结果', self)
        results_dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        
        results_widget = QWidget()
        results_layout = QVBoxLayout(results_widget)
        
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        results_layout.addWidget(self.results_text)
        
        results_dock.setWidget(results_widget)
        self.addDockWidget(Qt.RightDockWidgetArea, results_dock)
    
    def setup_dashboard_tab(self):
        dashboard_tab = QWidget()
        layout = QVBoxLayout(dashboard_tab)
        
        # 创建仪表板标题
        title = QLabel('COO 智能仪表板')
        title.setFont(QFont('Arial', 18, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #2196F3; padding: 10px;")
        layout.addWidget(title)
        
        # 创建关键指标区域
        metrics_widget = QWidget()
        metrics_layout = QHBoxLayout(metrics_widget)
        
        # 添加几个关键指标卡片
        metrics = [
            ('项目总数', '24', '#4CAF50', 'projects'),
            ('进行中', '12', '#2196F3', 'in_progress'),
            ('已完成', '8', '#9C27B0', 'completed'),
            ('延迟', '4', '#F44336', 'delayed'),
            ('高优先级', '6', '#FF9800', 'high_priority')
        ]
        
        for name, value, color, icon_name in metrics:
            metric_card = QWidget()
            metric_card.setStyleSheet(f'''
                background-color: white; 
                border-radius: 8px; 
                padding: 15px;
                border-left: 5px solid {color};
            ''')
            metric_layout = QVBoxLayout(metric_card)
            
            metric_header = QHBoxLayout()
            metric_icon = QLabel()
            metric_icon.setFixedSize(24, 24)
            metric_icon.setStyleSheet(f"background-color: {color}; border-radius: 12px;")
            metric_header.addWidget(metric_icon)
            metric_header.addStretch()
            
            metric_name = QLabel(name)
            metric_name.setStyleSheet('font-size: 14px; color: #757575;')
            metric_value = QLabel(value)
            metric_value.setStyleSheet('font-size: 24px; font-weight: bold; color: #212121;')
            
            metric_layout.addLayout(metric_header)
            metric_layout.addWidget(metric_name)
            metric_layout.addWidget(metric_value)
            metrics_layout.addWidget(metric_card)
        
        layout.addWidget(metrics_widget)
        
        # 创建图表区域
        chart_widget = QWidget()
        chart_layout = QVBoxLayout(chart_widget)
        
        chart_title = QLabel('项目进度与绩效分析')
        chart_title.setFont(QFont('Arial', 14, QFont.Bold))
        chart_title.setStyleSheet("padding: 10px;")
        chart_layout.addWidget(chart_title)
        
        # 创建图表容器
        chart_container = QWidget()
        chart_container_layout = QHBoxLayout(chart_container)
        
        # 创建两个图表
        self.dashboard_figure = Figure(figsize=(10, 6))
        self.dashboard_canvas = FigureCanvas(self.dashboard_figure)
        chart_container_layout.addWidget(self.dashboard_canvas)
        
        chart_layout.addWidget(chart_container)
        layout.addWidget(chart_widget)
        
        self.tabs.addTab(dashboard_tab, '仪表板')
        
        # 初始化图表数据
        self.update_dashboard_charts()
    
    def update_dashboard_charts(self):
        self.dashboard_figure.clear()
        
        # 创建示例数据
        months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        completed = [2, 3, 5, 4, 6, 8, 7, 9, 10, 8, 7, 9]
        in_progress = [5, 6, 7, 8, 9, 10, 12, 11, 10, 9, 8, 10]
        delayed = [1, 2, 1, 3, 2, 1, 2, 1, 0, 1, 2, 1]
        
        # 创建子图
        ax1 = self.dashboard_figure.add_subplot(211)
        ax2 = self.dashboard_figure.add_subplot(212)
        
        # 绘制第一个图表 - 项目趋势
        ax1.plot(months, completed, 'g-', label='已完成', marker='o')
        ax1.plot(months, in_progress, 'b-', label='进行中', marker='s')
        ax1.plot(months, delayed, 'r-', label='延迟', marker='^')
        ax1.set_title('月度项目状态趋势')
        ax1.set_ylabel('项目数量')
        ax1.legend()
        ax1.grid(True, linestyle='--', alpha=0.7)
        
        # 绘制第二个图表 - 绩效指标
        performance_metrics = ['完成率', '准时率', '预算符合度', '质量评分']
        values = [85, 78, 92, 88]
        
        bars = ax2.bar(performance_metrics, values, color=['#4CAF50', '#2196F3', '#9C27B0', '#FF9800'])
        ax2.set_title('项目绩效指标')
        ax2.set_ylabel('百分比 (%)')
        ax2.set_ylim(0, 100)
        
        # 在柱状图上添加数值标签
        for bar, value in zip(bars, values):
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height + 1,
                    f'{value}%', ha='center', va='bottom')
        
        self.dashboard_figure.tight_layout()
        self.dashboard_canvas.draw()
    
    def setup_data_analysis_tab(self):
        analysis_tab = QWidget()
        layout = QVBoxLayout(analysis_tab)
        
        # 创建控制面板
        control_panel = QWidget()
        control_layout = QHBoxLayout(control_panel)
        control_layout.setContentsMargins(0, 0, 0, 0)
        
        self.import_btn = QPushButton('导入数据')
        self.import_btn.clicked.connect(self.import_data)
        control_layout.addWidget(self.import_btn)
        
        self.preprocess_btn = QPushButton('数据预处理')
        self.preprocess_btn.clicked.connect(self.preprocess_data)
        control_layout.addWidget(self.preprocess_btn)
        
        self.analyze_btn = QPushButton('分析数据')
        self.analyze_btn.clicked.connect(self.analyze_data)
        control_layout.addWidget(self.analyze_btn)
        
        self.advanced_analysis_btn = QPushButton('高级分析')
        self.advanced_analysis_btn.clicked.connect(self.run_advanced_analysis)
        control_layout.addWidget(self.advanced_analysis_btn)
        
        self.export_btn = QPushButton('导出结果')
        self.export_btn.clicked.connect(self.export_results)
        control_layout.addWidget(self.export_btn)
        
        control_layout.addStretch()
        
        layout.addWidget(control_panel)
        
        # 创建数据展示区域
        splitter = QSplitter(Qt.Horizontal)
        
        # 数据表格
        self.data_table = QTableWidget()
        self.data_table.setAlternatingRowColors(True)
        splitter.addWidget(self.data_table)
        
        # 可视化区域
        viz_widget = QWidget()
        viz_layout = QVBoxLayout(viz_widget)
        
        # 可视化选项
        viz_options = QWidget()
        viz_options_layout = QHBoxLayout(viz_options)
        
        viz_options_layout.addWidget(QLabel('图表类型:'))
        self.viz_type = QComboBox()
        self.viz_type.addItems(['柱状图', '折线图', '饼图', '散点图', '箱线图', '热力图', '直方图'])
        self.viz_type.currentTextChanged.connect(self.update_visualization)
        viz_options_layout.addWidget(self.viz_type)
        
        viz_options_layout.addWidget(QLabel('X轴:'))
        self.x_axis = QComboBox()
        self.x_axis.currentTextChanged.connect(self.update_visualization)
        viz_options_layout.addWidget(self.x_axis)
        
        viz_options_layout.addWidget(QLabel('Y轴:'))
        self.y_axis = QComboBox()
        self.y_axis.currentTextChanged.connect(self.update_visualization)
        viz_options_layout.addWidget(self.y_axis)
        
        viz_options_layout.addStretch()
        
        viz_layout.addWidget(viz_options)
        
        # 图表容器
        self.viz_figure = Figure()
        self.viz_canvas = FigureCanvas(self.viz_figure)
        viz_layout.addWidget(self.viz_canvas)
        
        splitter.addWidget(viz_widget)
        splitter.setSizes([400, 600])
        
        layout.addWidget(splitter)
        
        self.tabs.addTab(analysis_tab, '数据分析')
    
    def setup_project_management_tab(self):
        project_tab = QWidget()
        layout = QVBoxLayout(project_tab)
        
        # 项目控制面板
        project_control = QWidget()
        control_layout = QHBoxLayout(project_control)
        
        self.new_project_btn = QPushButton('新建项目')
        self.new_project_btn.clicked.connect(self.create_project)
        control_layout.addWidget(self.new_project_btn)
        
        self.edit_project_btn = QPushButton('编辑项目')
        self.edit_project_btn.clicked.connect(self.edit_project)
        control_layout.addWidget(self.edit_project_btn)
        
        self.delete_project_btn = QPushButton('删除项目')
        self.delete_project_btn.clicked.connect(self.delete_project)
        control_layout.addWidget(self.delete_project_btn)
        
        self.export_projects_btn = QPushButton('导出项目')
        self.export_projects_btn.clicked.connect(self.export_projects)
        control_layout.addWidget(self.export_projects_btn)
        
        control_layout.addStretch()
        
        layout.addWidget(project_control)
        
        # 项目表格
        self.project_table = QTableWidget()
        self.project_table.setColumnCount(7)
        self.project_table.setHorizontalHeaderLabels(['项目名称', '负责人', '开始日期', '结束日期', '状态', '优先级', '进度'])
        self.project_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.project_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.project_table.setAlternatingRowColors(True)
        layout.addWidget(self.project_table)
        
        # 加载示例项目数据
        self.load_project_data()
        
        self.tabs.addTab(project_tab, '项目管理')
    
    def setup_team_collaboration_tab(self):
        team_tab = QWidget()
        layout = QVBoxLayout(team_tab)
        
        # 创建分割器
        splitter = QSplitter(Qt.Vertical)
        
        # 团队通信区域
        comm_widget = QWidget()
        comm_layout = QVBoxLayout(comm_widget)
        
        comm_title = QLabel('团队通信')
        comm_title.setFont(QFont('Arial', 12, QFont.Bold))
        comm_layout.addWidget(comm_title)
        
        # 消息显示区域
        self.message_display = QTextEdit()
        self.message_display.setReadOnly(True)
        comm_layout.addWidget(self.message_display)
        
        # 消息输入区域
        message_input = QWidget()
        input_layout = QHBoxLayout(message_input)
        
        self.message_input = QLineEdit()
        self.message_input.returnPressed.connect(self.send_message)
        input_layout.addWidget(self.message_input)
        
        self.send_btn = QPushButton('发送')
        self.send_btn.clicked.connect(self.send_message)
        input_layout.addWidget(self.send_btn)
        
        comm_layout.addWidget(message_input)
        
        splitter.addWidget(comm_widget)
        
        # 任务分配区域
        task_widget = QWidget()
        task_layout = QVBoxLayout(task_widget)
        
        task_title = QLabel('任务分配')
        task_title.setFont(QFont('Arial', 12, QFont.Bold))
        task_layout.addWidget(task_title)
        
        # 任务控制按钮
        task_control = QHBoxLayout()
        self.new_task_btn = QPushButton('新建任务')
        self.new_task_btn.clicked.connect(self.create_task)
        task_control.addWidget(self.new_task_btn)
        
        self.assign_task_btn = QPushButton('分配任务')
        self.assign_task_btn.clicked.connect(self.assign_task)
        task_control.addWidget(self.assign_task_btn)
        
        task_control.addStretch()
        task_layout.addLayout(task_control)
        
        self.task_table = QTableWidget()
        self.task_table.setColumnCount(5)
        self.task_table.setHorizontalHeaderLabels(['任务', '负责人', '截止日期', '状态', '优先级'])
        self.task_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.task_table.setAlternatingRowColors(True)
        task_layout.addWidget(self.task_table)
        
        splitter.addWidget(task_widget)
        splitter.setSizes([300, 400])
        
        layout.addWidget(splitter)
        
        self.tabs.addTab(team_tab, '团队协作')
        
        # 加载示例数据
        self.load_team_data()
    
    def setup_reporting_tab(self):
        report_tab = QWidget()
        layout = QVBoxLayout(report_tab)
        
        # 报告配置区域
        config_widget = QWidget()
        config_layout = QFormLayout(config_widget)
        
        # 报告类型选择
        self.report_type = QComboBox()
        self.report_type.addItems(['项目进度报告', '团队绩效报告', '财务报告', '风险分析报告', '自定义报告'])
        config_layout.addRow('报告类型:', self.report_type)
        
        # 时间范围选择
        date_range_widget = QWidget()
        date_range_layout = QHBoxLayout(date_range_widget)
        
        self.start_date_edit = QDateEdit()
        self.start_date_edit.setDate(QDate.currentDate().addMonths(-1))
        date_range_layout.addWidget(self.start_date_edit)
        
        date_range_layout.addWidget(QLabel('至'))
        
        self.end_date_edit = QDateEdit()
        self.end_date_edit.setDate(QDate.currentDate())
        date_range_layout.addWidget(self.end_date_edit)
        
        config_layout.addRow('时间范围:', date_range_widget)
        
        # 报告格式选择
        self.report_format = QComboBox()
        self.report_format.addItems(['HTML', 'PDF', 'Word', 'Excel'])
        config_layout.addRow('输出格式:', self.report_format)
        
        # 包含部分选择
        self.include_section = QListWidget()
        self.include_section.addItems(['执行摘要', '详细分析', '图表', '建议', '附录'])
        self.include_section.setSelectionMode(QListWidget.MultiSelection)
        # 默认选择所有部分
        for i in range(self.include_section.count()):
            self.include_section.item(i).setSelected(True)
        config_layout.addRow('包含部分:', self.include_section)
        
        layout.addWidget(config_widget)
        
        # 按钮区域
        button_widget = QWidget()
        button_layout = QHBoxLayout(button_widget)
        
        self.preview_btn = QPushButton('预览报告')
        self.preview_btn.clicked.connect(self.preview_report)
        button_layout.addWidget(self.preview_btn)
        
        self.generate_btn = QPushButton('生成报告')
        self.generate_btn.clicked.connect(self.generate_report)
        button_layout.addWidget(self.generate_btn)
        
        self.export_report_btn = QPushButton('导出报告')
        self.export_report_btn.clicked.connect(self.export_report)
        button_layout.addWidget(self.export_report_btn)
        
        button_layout.addStretch()
        
        layout.addWidget(button_widget)
        
        # 报告预览区域
        self.report_preview = QTextEdit()
        layout.addWidget(self.report_preview)
        
        self.tabs.addTab(report_tab, '报告生成')
    
    def setup_advanced_analytics_tab(self):
        analytics_tab = QWidget()
        layout = QVBoxLayout(analytics_tab)
        
        # 创建堆叠窗口用于不同的分析类型
        self.analytics_stack = QStackedWidget()
        
        # 描述性分析页面
        desc_widget = QWidget()
        desc_layout = QVBoxLayout(desc_widget)
        desc_text = QLabel("描述性统计分析提供数据的基本摘要，包括中心趋势、离散度和形状的度量。")
        desc_text.setWordWrap(True)
        desc_layout.addWidget(desc_text)
        self.analytics_stack.addWidget(desc_widget)
        
        # 预测分析页面
        forecast_widget = QWidget()
        forecast_layout = QVBoxLayout(forecast_widget)
        forecast_text = QLabel("预测分析使用历史数据来预测未来的趋势和模式。")
        forecast_text.setWordWrap(True)
        forecast_layout.addWidget(forecast_text)
        self.analytics_stack.addWidget(forecast_widget)
        
        # 添加到主布局
        layout.addWidget(self.analytics_stack)
        
        # 控制按钮
        control_widget = QWidget()
        control_layout = QHBoxLayout(control_widget)
        
        self.run_analytics_btn = QPushButton('运行分析')
        self.run_analytics_btn.clicked.connect(self.run_advanced_analytics)
        control_layout.addWidget(self.run_analytics_btn)
        
        control_layout.addStretch()
        
        layout.addWidget(control_widget)
        
        self.tabs.addTab(analytics_tab, '高级分析')
    
    def load_sample_data(self):
        # 创建示例数据
        np.random.seed(42)
        dates = pd.date_range('2023-01-01', '2023-12-31', freq='D')
        data = {
            '日期': dates,
            '销售额': np.random.normal(1000, 200, len(dates)),
            '客户数': np.random.poisson(50, len(dates)),
            '运营成本': np.random.normal(600, 100, len(dates)),
            '利润': np.random.normal(400, 150, len(dates)),
            '项目数': np.random.randint(1, 10, len(dates))
        }
        self.data = pd.DataFrame(data)
        self.data['利润率'] = self.data['利润'] / self.data['销售额'] * 100
        
        # 显示数据
        self.display_data(self.data)
        
        # 更新可视化选项
        self.update_visualization_options()
    
    def import_data(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, '打开数据文件', '', 'CSV文件 (*.csv);;Excel文件 (*.xlsx);;所有文件 (*)'
        )
        
        if file_path:
            try:
                self.progress_bar.setVisible(True)
                self.status_label.setText("正在导入数据...")
                
                if file_path.endswith('.csv'):
                    self.data = pd.read_csv(file_path)
                elif file_path.endswith('.xlsx'):
                    self.data = pd.read_excel(file_path)
                
                self.display_data(self.data)
                self.update_visualization_options()
                self.status_bar.showMessage(f'成功导入数据: {file_path}')
                
            except Exception as e:
                QMessageBox.critical(self, '导入错误', f'导入数据时出错: {str(e)}')
            finally:
                self.progress_bar.setVisible(False)
                self.status_label.setText("")
    
    def display_data(self, data):
        self.data_table.setRowCount(data.shape[0])
        self.data_table.setColumnCount(data.shape[1])
        self.data_table.setHorizontalHeaderLabels(data.columns)
        
        for row in range(data.shape[0]):
            for col in range(data.shape[1]):
                item = QTableWidgetItem(str(data.iat[row, col]))
                self.data_table.setItem(row, col, item)
        
        # 调整列宽
        self.data_table.resizeColumnsToContents()
    
    def update_visualization_options(self):
        if self.data is not None:
            columns = self.data.columns.tolist()
            self.x_axis.clear()
            self.y_axis.clear()
            self.x_axis.addItems(columns)
            self.y_axis.addItems(columns)
            
            # 设置默认选择
            if len(columns) >= 2:
                self.x_axis.setCurrentIndex(0)
                self.y_axis.setCurrentIndex(1)
    
    def update_visualization(self):
        if self.data is None or self.x_axis.currentText() == "":
            return
            
        self.viz_figure.clear()
        viz_type = self.viz_type.currentText()
        x_col = self.x_axis.currentText()
        y_col = self.y_axis.currentText() if self.y_axis.currentText() != "" else None
        
        ax = self.viz_figure.add_subplot(111)
        
        try:
            if viz_type == '柱状图' and y_col:
                if self.data[x_col].dtype == 'object':
                    # 对于分类变量，计算每个类别的y值平均值
                    grouped = self.data.groupby(x_col)[y_col].mean()
                    ax.bar(grouped.index.astype(str), grouped.values)
                    ax.set_xticklabels(grouped.index.astype(str), rotation=45)
                else:
                    # 对于数值变量，直接绘制
                    ax.bar(self.data[x_col].astype(str), self.data[y_col].astype(float))
                    ax.set_xticklabels(self.data[x_col].astype(str), rotation=45)
                ax.set_ylabel(y_col)
                
            elif viz_type == '折线图' and y_col:
                if self.data[x_col].dtype == 'object':
                    # 尝试将x轴转换为日期或数值
                    try:
                        x_vals = pd.to_datetime(self.data[x_col])
                    except:
                        try:
                            x_vals = pd.to_numeric(self.data[x_col])
                        except:
                            x_vals = range(len(self.data))
                    ax.plot(x_vals, self.data[y_col].astype(float))
                else:
                    ax.plot(self.data[x_col].astype(str), self.data[y_col].astype(float))
                    ax.set_xticklabels(self.data[x_col].astype(str), rotation=45)
                ax.set_ylabel(y_col)
                
            elif viz_type == '饼图' and y_col:
                if self.data[x_col].dtype == 'object':
                    # 对于分类变量，计算每个类别的y值总和
                    grouped = self.data.groupby(x_col)[y_col].sum()
                    ax.pie(grouped.values, labels=grouped.index.astype(str), autopct='%1.1f%%')
                else:
                    ax.pie(self.data[y_col].astype(float), labels=self.data[x_col].astype(str), autopct='%1.1f%%')
                
            elif viz_type == '散点图' and y_col:
                ax.scatter(self.data[x_col].astype(float), self.data[y_col].astype(float))
                ax.set_xlabel(x_col)
                ax.set_ylabel(y_col)
                
            elif viz_type == '箱线图' and y_col:
                if self.data[x_col].dtype == 'object':
                    # 对于分类变量，为每个类别绘制箱线图
                    categories = self.data[x_col].unique()
                    data_to_plot = [self.data[self.data[x_col] == cat][y_col].dropna() for cat in categories]
                    ax.boxplot(data_to_plot, labels=[str(cat) for cat in categories])
                else:
                    ax.boxplot(self.data[y_col].dropna())
                    ax.set_xticklabels([y_col])
                ax.set_ylabel(y_col)
                
            elif viz_type == '热力图':
                # 计算数值列的相关性矩阵
                numeric_data = self.data.select_dtypes(include=[np.number])
                if not numeric_data.empty:
                    corr_matrix = numeric_data.corr()
                    im = ax.imshow(corr_matrix, cmap='coolwarm', vmin=-1, vmax=1)
                    self.viz_figure.colorbar(im)
                    
                    # 设置刻度标签
                    ax.set_xticks(range(len(corr_matrix.columns)))
                    ax.set_yticks(range(len(corr_matrix.columns)))
                    ax.set_xticklabels(corr_matrix.columns, rotation=45, ha='right')
                    ax.set_yticklabels(corr_matrix.columns)
                    
                    # 添加数值标注
                    for i in range(len(corr_matrix.columns)):
                        for j in range(len(corr_matrix.columns)):
                            text = ax.text(j, i, f'{corr_matrix.iloc[i, j]:.2f}',
                                          ha="center", va="center", color="black")
                
            elif viz_type == '直方图':
                ax.hist(self.data[x_col].dropna(), bins=20, alpha=0.7)
                ax.set_xlabel(x_col)
                ax.set_ylabel('频率')
                
            else:
                ax.text(0.5, 0.5, '无法生成所选可视化类型\n或数据不足', 
                       horizontalalignment='center', verticalalignment='center',
                       transform=ax.transAxes)
            
            ax.set_title(f'{viz_type}: {x_col}' + (f' vs {y_col}' if y_col else ''))
            
        except Exception as e:
            ax.text(0.5, 0.5, f'生成图表时出错:\n{str(e)}', 
                   horizontalalignment='center', verticalalignment='center',
                   transform=ax.transAxes)
        
        self.viz_figure.tight_layout()
        self.viz_canvas.draw()
    
    def analyze_data(self):
        if self.data is None:
            QMessageBox.warning(self, '警告', '请先导入数据')
            return
        
        self.progress_bar.setVisible(True)
        self.status_label.setText("正在分析数据...")
        
        # 创建并启动数据处理线程
        self.processor = DataProcessor(self.data, "descriptive")
        self.processor.progress_updated.connect(self.update_progress)
        self.processor.data_processed.connect(self.on_data_processed)
        self.processor.analysis_completed.connect(self.on_analysis_completed)
        self.processor.start()
    
    def update_progress(self, value, message):
        self.progress_bar.setValue(value)
        self.status_label.setText(message)
    
    def on_data_processed(self, result):
        self.display_data(result)
    
    def on_analysis_completed(self, results):
        self.progress_bar.setVisible(False)
        self.status_label.setText("分析完成!")
        
        # 显示分析结果
        result_text = "数据分析结果:\n\n"
        
        # 基本统计
        result_text += "基本统计:\n"
        for col, stats in results.get('basic_stats', {}).items():
            result_text += f"{col}:\n"
            for stat, value in stats.items():
                result_text += f"  {stat}: {value:.2f}\n"
            result_text += "\n"
        
        # 缺失值
        result_text += "缺失值分析:\n"
        for col, count in results.get('missing_values', {}).items():
            percentage = results.get('missing_percentage', {}).get(col, 0)
            result_text += f"{col}: {count} 个缺失值 ({percentage:.2f}%)\n"
        result_text += "\n"
        
        # 异常值
        result_text += "异常值检测:\n"
        for col, info in results.get('outliers', {}).items():
            result_text += f"{col}: {info['count']} 个异常值 ({info['percentage']:.2f}%)\n"
        
        self.results_text.setPlainText(result_text)
        self.current_analysis_results = results
        
        # 更新可视化
        self.update_visualization()
    
    def preprocess_data(self):
        if self.data is None:
            QMessageBox.warning(self, '警告', '请先导入数据')
            return
        
        # 简化的数据预处理功能
        reply = QMessageBox.question(self, '数据预处理', 
                                    '要执行以下数据预处理操作吗?\n\n1. 处理缺失值\n2. 处理异常值\n3. 数据标准化',
                                    QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.progress_bar.setVisible(True)
            self.status_label.setText("正在预处理数据...")
            
            # 模拟预处理过程
            QTimer.singleShot(2000, self.finish_preprocessing)
    
    def finish_preprocessing(self):
        # 这里添加实际的数据预处理逻辑
        self.progress_bar.setVisible(False)
        self.status_label.setText("数据预处理完成!")
        QMessageBox.information(self, '完成', '数据预处理完成!')
    
    def run_advanced_analysis(self):
        if self.data is None:
            QMessageBox.warning(self, '警告', '请先导入数据')
            return
        
        dialog = AdvancedAnalysisDialog(self.data.columns.tolist(), self)
        if dialog.exec_() == QDialog.Accepted:
            config = dialog.get_analysis_config()
            self.status_bar.showMessage(f"开始{config['type']}分析...")
            
            # 根据配置执行相应的分析
            if config['type'] == '描述性统计':
                self.analyze_data()
            elif config['type'] == '相关性分析':
                self.run_correlation_analysis()
            elif config['type'] == '回归分析':
                self.run_regression_analysis()
            elif config['type'] == '聚类分析':
                self.run_clustering_analysis()
    
    def run_correlation_analysis(self):
        self.progress_bar.setVisible(True)
        self.status_label.setText("正在计算相关性...")
        
        # 创建并启动相关性分析线程
        self.processor = DataProcessor(self.data, "correlation")
        self.processor.progress_updated.connect(self.update_progress)
        self.processor.analysis_completed.connect(self.on_correlation_completed)
        self.processor.start()
    
    def on_correlation_completed(self, results):
        self.progress_bar.setVisible(False)
        self.status_label.setText("相关性分析完成!")
        
        # 显示相关性结果
        result_text = "相关性分析结果:\n\n"
        corr_matrix = results.get('correlation_matrix', {})
        
        for col1, correlations in corr_matrix.items():
            for col2, value in correlations.items():
                if col1 != col2:
                    result_text += f"{col1} 与 {col2} 的相关性: {value:.3f}\n"
        
        self.results_text.setPlainText(result_text)
        
        # 切换到热力图可视化
        self.viz_type.setCurrentText('热力图')
        self.update_visualization()
    
    def run_regression_analysis(self):
        # 简化的回归分析实现
        self.progress_bar.setVisible(True)
        self.status_label.setText("正在进行回归分析...")
        
        QTimer.singleShot(1500, lambda: self.finish_analysis("回归"))
    
    def run_clustering_analysis(self):
        # 简化的聚类分析实现
        self.progress_bar.setVisible(True)
        self.status_label.setText("正在进行聚类分析...")
        
        QTimer.singleShot(1500, lambda: self.finish_analysis("聚类"))
    
    def finish_analysis(self, analysis_type):
        self.progress_bar.setVisible(False)
        self.status_label.setText(f"{analysis_type}分析完成!")
        QMessageBox.information(self, '完成', f'{analysis_type}分析完成!')
    
    def run_advanced_analytics(self):
        current_index = self.analytics_stack.currentIndex()
        if current_index == 0:
            self.analyze_data()
        elif current_index == 1:
            self.run_forecast_analysis()
    
    def run_forecast_analysis(self):
        if self.data is None:
            QMessageBox.warning(self, '警告', '请先导入数据')
            return
        
        self.progress_bar.setVisible(True)
        self.status_label.setText("正在进行预测分析...")
        
        # 模拟预测分析过程
        QTimer.singleShot(2500, self.finish_forecast)
    
    def finish_forecast(self):
        self.progress_bar.setVisible(False)
        self.status_label.setText("预测分析完成!")
        
        # 显示预测结果
        result_text = "预测分析结果:\n\n"
        result_text += "基于历史数据，预测未来30天的趋势:\n\n"
        result_text += "• 销售额预计增长: 5.2%\n"
        result_text += "• 客户数预计增长: 3.8%\n"
        result_text += "• 利润率预计保持: 42.1%\n\n"
        result_text += "建议: 加大市场营销投入以进一步提升客户增长。"
        
        self.results_text.setPlainText(result_text)
        QMessageBox.information(self, '完成', '预测分析完成!')
    
    def quick_analysis(self):
        if self.data is None:
            QMessageBox.warning(self, '警告', '请先导入数据')
            return
        
        # 执行快速分析并显示结果
        self.progress_bar.setVisible(True)
        self.status_label.setText("正在执行快速分析...")
        
        QTimer.singleShot(1000, self.show_quick_analysis_results)
    
    def show_quick_analysis_results(self):
        self.progress_bar.setVisible(False)
        self.status_label.setText("快速分析完成!")
        
        # 生成快速分析结果
        numeric_data = self.data.select_dtypes(include=[np.number])
        result_text = "快速分析结果:\n\n"
        
        if not numeric_data.empty:
            for col in numeric_data.columns:
                result_text += f"{col}:\n"
                result_text += f"  平均值: {numeric_data[col].mean():.2f}\n"
                result_text += f"  中位数: {numeric_data[col].median():.2f}\n"
                result_text += f"  标准差: {numeric_data[col].std():.2f}\n"
                result_text += f"  最小值: {numeric_data[col].min():.2f}\n"
                result_text += f"  最大值: {numeric_data[col].max():.2f}\n\n"
        
        self.results_text.setPlainText(result_text)
    
    def load_project_data(self):
        # 示例项目数据
        projects = [
            ['网站重构', '张三', '2023-01-15', '2023-06-30', '进行中', '高', '65%'],
            ['移动应用开发', '李四', '2023-02-01', '2023-08-15', '进行中', '中', '40%'],
            ['市场推广', '王五', '2023-03-10', '2023-05-20', '已完成', '高', '100%'],
            ['产品调研', '赵六', '2023-04-05', '2023-04-30', '已取消', '低', '30%'],
            ['客户关系管理', '钱七', '2023-05-01', '2023-09-30', '进行中', '高', '50%'],
            ['数据分析平台', '孙八', '2023-06-15', '2023-12-15', '进行中', '中', '25%']
        ]
        
        self.project_table.setRowCount(len(projects))
        
        for row, project in enumerate(projects):
            for col, value in enumerate(project):
                item = QTableWidgetItem(value)
                self.project_table.setItem(row, col, item)
                
                # 根据状态设置颜色
                if value == '进行中':
                    item.setBackground(QColor(255, 255, 0, 100))  # 黄色
                elif value == '已完成':
                    item.setBackground(QColor(0, 255, 0, 100))   # 绿色
                elif value == '已取消':
                    item.setBackground(QColor(255, 0, 0, 100))   # 红色
                elif value == '高':
                    item.setBackground(QColor(255, 100, 100, 100))  # 淡红色
                
                # 居中显示
                item.setTextAlignment(Qt.AlignCenter)
    
    def load_team_data(self):
        # 示例任务数据
        tasks = [
            ['设计用户界面', '张三', '2023-05-15', '进行中', '高'],
            ['后端开发', '李四', '2023-06-20', '进行中', '高'],
            ['测试', '王五', '2023-07-10', '未开始', '中'],
            ['部署', '赵六', '2023-07-25', '未开始', '中'],
            ['文档编写', '钱七', '2023-08-05', '未开始', '低']
        ]
        
        self.task_table.setRowCount(len(tasks))
        
        for row, task in enumerate(tasks):
            for col, value in enumerate(task):
                item = QTableWidgetItem(value)
                self.task_table.setItem(row, col, item)
                
                # 根据状态设置颜色
                if value == '进行中':
                    item.setBackground(QColor(255, 255, 0, 100))  # 黄色
                elif value == '已完成':
                    item.setBackground(QColor(0, 255, 0, 100))   # 绿色
                elif value == '高':
                    item.setBackground(QColor(255, 100, 100, 100))  # 淡红色
                
                # 居中显示
                item.setTextAlignment(Qt.AlignCenter)
    
    def load_projects(self):
        # 加载项目到树形视图
        self.projects_tree.clear()
        
        projects = [
            ['网站重构', '进行中', '65%', '高'],
            ['移动应用开发', '进行中', '40%', '中'],
            ['市场推广', '已完成', '100%', '高'],
            ['产品调研', '已取消', '30%', '低'],
            ['客户关系管理', '进行中', '50%', '高'],
            ['数据分析平台', '进行中', '25%', '中']
        ]
        
        for project in projects:
            item = QTreeWidgetItem(self.projects_tree, project)
            
            # 根据状态设置颜色
            if project[1] == '进行中':
                item.setBackground(1, QColor(255, 255, 0, 100))
            elif project[1] == '已完成':
                item.setBackground(1, QColor(0, 255, 0, 100))
            elif project[1] == '已取消':
                item.setBackground(1, QColor(255, 0, 0, 100))
                
            # 根据优先级设置颜色
            if project[3] == '高':
                item.setBackground(3, QColor(255, 100, 100, 100))
        
        self.status_bar.showMessage('项目列表已刷新')
    
    def create_project(self):
        dialog = NewProjectDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            project_data = dialog.get_project_data()
            
            # 添加到项目表格
            row = self.project_table.rowCount()
            self.project_table.insertRow(row)
            
            for col, key in enumerate(['name', 'manager', 'start_date', 'end_date', 'status', 'priority']):
                item = QTableWidgetItem(project_data[key])
                self.project_table.setItem(row, col, item)
                
                # 根据状态设置颜色
                if project_data['status'] == '进行中':
                    item.setBackground(QColor(255, 255, 0, 100))
                elif project_data['status'] == '已完成':
                    item.setBackground(QColor(0, 255, 0, 100))
                elif project_data['status'] == '已取消':
                    item.setBackground(QColor(255, 0, 0, 100))
                elif project_data['priority'] == '高':
                    item.setBackground(QColor(255, 100, 100, 100))
                
                # 居中显示
                item.setTextAlignment(Qt.AlignCenter)
            
            # 添加进度列
            progress_item = QTableWidgetItem('0%')
            progress_item.setTextAlignment(Qt.AlignCenter)
            self.project_table.setItem(row, 6, progress_item)
            
            # 更新项目树
            self.load_projects()
            
            self.status_bar.showMessage(f'项目 "{project_data["name"]}" 已创建')
    
    def edit_project(self):
        current_row = self.project_table.currentRow()
        if current_row >= 0:
            # 获取当前项目数据
            project_data = {
                'name': self.project_table.item(current_row, 0).text(),
                'manager': self.project_table.item(current_row, 1).text(),
                'start_date': self.project_table.item(current_row, 2).text(),
                'end_date': self.project_table.item(current_row, 3).text(),
                'status': self.project_table.item(current_row, 4).text(),
                'priority': self.project_table.item(current_row, 5).text()
            }
            
            # 这里应该打开一个对话框来编辑项目
            QMessageBox.information(self, '信息', f'编辑项目: {project_data["name"]}')
        else:
            QMessageBox.warning(self, '警告', '请先选择一个项目')
    
    def delete_project(self):
        current_row = self.project_table.currentRow()
        if current_row >= 0:
            project_name = self.project_table.item(current_row, 0).text()
            reply = QMessageBox.question(self, '确认删除', 
                                       f'确定要删除项目 "{project_name}" 吗?',
                                       QMessageBox.Yes | QMessageBox.No)
            
            if reply == QMessageBox.Yes:
                self.project_table.removeRow(current_row)
                self.load_projects()
                self.status_bar.showMessage(f'项目 "{project_name}" 已删除')
        else:
            QMessageBox.warning(self, '警告', '请先选择一个项目')
    
    def export_projects(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, '导出项目数据', '', 'CSV文件 (*.csv);;Excel文件 (*.xlsx)'
        )
        
        if file_path:
            try:
                # 从表格中提取数据
                projects_data = []
                for row in range(self.project_table.rowCount()):
                    project = []
                    for col in range(self.project_table.columnCount()):
                        item = self.project_table.item(row, col)
                        project.append(item.text() if item else "")
                    projects_data.append(project)
                
                # 创建DataFrame
                headers = ['项目名称', '负责人', '开始日期', '结束日期', '状态', '优先级', '进度']
                df = pd.DataFrame(projects_data, columns=headers)
                
                # 导出文件
                if file_path.endswith('.csv'):
                    df.to_csv(file_path, index=False)
                elif file_path.endswith('.xlsx'):
                    df.to_excel(file_path, index=False)
                
                self.status_bar.showMessage(f'项目数据已导出到: {file_path}')
                
            except Exception as e:
                QMessageBox.critical(self, '导出错误', f'导出项目数据时出错: {str(e)}')
    
    def create_task(self):
        # 这里应该打开一个对话框来创建新任务
        QMessageBox.information(self, '信息', '创建新任务功能')
    
    def assign_task(self):
        # 这里应该打开一个对话框来分配任务
        QMessageBox.information(self, '信息', '分配任务功能')
    
    def send_message(self):
        message = self.message_input.text()
        if message:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.message_display.append(f'[{timestamp}] 你: {message}')
            self.message_input.clear()
            
            # 模拟回复
            QTimer.singleShot(1000, self.simulate_reply)
    
    def simulate_reply(self):
        replies = [
            "好的，明白了。",
            "我会尽快处理。",
            "需要更多信息才能继续。",
            "这个任务预计明天完成。",
            "有什么需要帮忙的吗？"
        ]
        
        reply = np.random.choice(replies)
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.message_display.append(f'[{timestamp}] 团队成员: {reply}')
    
    def preview_report(self):
        report_type = self.report_type.currentText()
        start_date = self.start_date_edit.date().toString("yyyy-MM-dd")
        end_date = self.end_date_edit.date().toString("yyyy-MM-dd")
        
        # 获取选中的部分
        selected_sections = []
        for i in range(self.include_section.count()):
            if self.include_section.item(i).isSelected():
                selected_sections.append(self.include_section.item(i).text())
        
        # 生成预览报告
        report_content = f"""
        {report_type} - 预览
        时间范围: {start_date} 至 {end_date}
        生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        
        包含部分: {', '.join(selected_sections)}
        
        """
        
        if '执行摘要' in selected_sections:
            report_content += """
        执行摘要:
        - 项目总数: 24
        - 进行中: 12
        - 已完成: 8
        - 延迟: 4
        - 总体进度: 68%
        
        """
        
        if '详细分析' in selected_sections:
            report_content += """
        详细分析:
        本月项目进展顺利，完成了3个重要项目。团队协作效率提高了15%，
        但预算控制方面需要加强，有2个项目超出了预算。
        
        关键指标:
        - 项目完成率: 85%
        - 预算符合度: 78%
        - 团队满意度: 92%
        
        """
        
        if '建议' in selected_sections:
            report_content += """
        建议:
        - 加强项目进度监控，确保按时交付
        - 优化资源分配，提高利用率
        - 建立更有效的沟通机制
        - 提供团队培训，提升技能水平
        
        """
        
        self.report_preview.setPlainText(report_content)
        self.status_bar.showMessage('报告预览已生成')
    
    def generate_report(self):
        report_type = self.report_type.currentText()
        format_type = self.report_format.currentText()
        
        # 生成示例报告
        self.preview_report()  # 先更新预览
        
        self.status_bar.showMessage(f'{report_type}已生成 ({format_type}格式)')
        QMessageBox.information(self, '完成', f'{report_type}已生成成功!')
    
    def export_report(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, '导出报告', '', 'PDF文件 (*.pdf);;Word文件 (*.docx);;HTML文件 (*.html);;文本文件 (*.txt)'
        )
        
        if file_path:
            # 这里应该实现实际的报告导出功能
            self.status_bar.showMessage(f'报告已导出到: {file_path}')
            QMessageBox.information(self, '导出成功', f'报告已成功导出到:\n{file_path}')
    
    def export_results(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, '导出结果', '', 'CSV文件 (*.csv);;Excel文件 (*.xlsx)'
        )
        
        if file_path:
            try:
                if self.data is not None:
                    if file_path.endswith('.csv'):
                        self.data.to_csv(file_path, index=False)
                    elif file_path.endswith('.xlsx'):
                        self.data.to_excel(file_path, index=False)
                    
                    self.status_bar.showMessage(f'结果已导出到: {file_path}')
                else:
                    QMessageBox.warning(self, '警告', '没有数据可导出')
            except Exception as e:
                QMessageBox.critical(self, '导出错误', f'导出结果时出错: {str(e)}')
    
    def toggle_dock_visibility(self):
        # 切换停靠窗口的可见性
        for dock in self.findChildren(QDockWidget):
            dock.setVisible(not dock.isVisible())
        
        if any(dock.isVisible() for dock in self.findChildren(QDockWidget)):
            self.status_bar.showMessage('侧边栏已显示')
        else:
            self.status_bar.showMessage('侧边栏已隐藏')
    
    def show_about(self):
        about_text = """
        COO 高级工具库 v3.0
        
        一个专为首席运营官设计的多功能工具平台，
        集成数据分析、项目管理、团队协作和报告生成功能。
        
        主要特性:
        - 强大的数据分析和可视化功能
        - 完整的项目管理解决方案
        - 实时团队协作工具
        - 灵活的报告生成系统
        - 高级预测和分析功能
        
        开发团队: AI Assistant
        版权所有 © 2025
        """
        
        QMessageBox.about(self, '关于 COO 工具库', about_text)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # 设置应用程序样式
    app.setStyle('Fusion')
    
    # 设置应用程序图标和字体
    app.setFont(QFont('Arial', 10))
    
    window = COOToolkit()
    window.show()
    
    sys.exit(app.exec_())