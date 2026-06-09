import sys
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QTabWidget, QPushButton, QLabel, QComboBox, QDateEdit, 
                             QSplitter, QTableWidget, QTableWidgetItem, QHeaderView,
                             QFileDialog, QMessageBox, QToolBar, QStatusBar, QAction,
                             QDockWidget, QTreeWidget, QTreeWidgetItem, QListWidget,
                             QGroupBox, QCheckBox, QSpinBox, QDoubleSpinBox, QTextEdit,
                             QProgressBar, QSlider, QLineEdit, QFormLayout, QSizePolicy,
                             QDialog, QDialogButtonBox, QGridLayout, QStackedWidget)
from PyQt5.QtCore import Qt, QDate, QSize, QTimer, QThread, pyqtSignal
from PyQt5.QtGui import QIcon, QFont, QColor, QPalette, QPixmap, QPainter, QLinearGradient

import matplotlib
matplotlib.rc("font", family='Microsoft YaHei')
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.figure import Figure

# 财务分析库
from scipy import stats
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures
from sklearn.pipeline import Pipeline
import warnings
warnings.filterwarnings('ignore')

# 设置样式
plt.style.use('seaborn-v0_8')
sns.set_palette("husl")


class AnalysisWorker(QThread):
    """后台分析线程"""
    progress = pyqtSignal(int)
    finished = pyqtSignal(object)
    
    def __init__(self, data, analysis_type):
        super().__init__()
        self.data = data
        self.analysis_type = analysis_type
        
    def run(self):
        result = {}
        try:
            if self.analysis_type == "trend":
                # 趋势分析
                for i, col in enumerate(self.data.select_dtypes(include=[np.number]).columns):
                    self.progress.emit(int((i + 1) / len(self.data.columns) * 100))
                    result[col] = self.analyze_trend(self.data[col])
            
            elif self.analysis_type == "forecast":
                # 预测分析
                result = self.forecast_data(self.data)
                
            elif self.analysis_type == "ratio":
                # 财务比率分析
                result = self.calculate_ratios(self.data)
                
        except Exception as e:
            result = {"error": str(e)}
            
        self.finished.emit(result)
    
    def analyze_trend(self, series):
        """分析时间序列趋势"""
        if len(series) < 2:
            return {"trend": "insufficient_data", "slope": 0, "r_squared": 0}
        
        x = np.arange(len(series)).reshape(-1, 1)
        y = series.values
        
        model = LinearRegression()
        model.fit(x, y)
        
        slope = model.coef_[0]
        r_squared = model.score(x, y)
        
        if slope > 0:
            trend = "upward"
        elif slope < 0:
            trend = "downward"
        else:
            trend = "stable"
            
        return {"trend": trend, "slope": slope, "r_squared": r_squared}
    
    def forecast_data(self, data):
        """预测未来数据"""
        # 简化实现 - 实际应用中应使用更复杂的预测模型
        forecasts = {}
        numeric_data = data.select_dtypes(include=[np.number])
        
        for col in numeric_data.columns:
            series = numeric_data[col].dropna()
            if len(series) > 1:
                x = np.arange(len(series)).reshape(-1, 1)
                y = series.values
                
                # 使用多项式回归进行预测
                model = Pipeline([
                    ('poly', PolynomialFeatures(degree=2)),
                    ('linear', LinearRegression())
                ])
                model.fit(x, y)
                
                # 预测未来3个周期
                future_x = np.arange(len(series), len(series) + 3).reshape(-1, 1)
                future_y = model.predict(future_x)
                
                forecasts[col] = future_y.tolist()
        
        return forecasts
    
    def calculate_ratios(self, data):
        """计算财务比率"""
        ratios = {}
        
        # 假设数据包含特定的财务指标
        if 'revenue' in data.columns and 'expenses' in data.columns:
            ratios['gross_profit_margin'] = ((data['revenue'] - data['expenses']) / data['revenue']).mean()
            
        if 'assets' in data.columns and 'liabilities' in data.columns:
            ratios['current_ratio'] = (data['assets'] / data['liabilities']).mean()
            
        if 'net_income' in data.columns and 'revenue' in data.columns:
            ratios['net_profit_margin'] = (data['net_income'] / data['revenue']).mean()
            
        return ratios


class FinancialChart(FigureCanvas):
    """财务图表基类"""
    def __init__(self, parent=None, width=10, height=6, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        super().__init__(self.fig)
        self.setParent(parent)
        self.axes = self.fig.add_subplot(111)
        
    def plot_data(self, data):
        raise NotImplementedError("子类必须实现plot_data方法")


class TimeSeriesChart(FinancialChart):
    """时间序列图表"""
    def __init__(self, parent=None):
        super().__init__(parent)
        
    def plot_data(self, data, title="财务时间序列", xlabel="日期", ylabel="金额", forecast=None):
        self.axes.clear()
        
        if isinstance(data, pd.Series):
            line, = self.axes.plot(data.index, data.values, 'b-', marker='o', linewidth=2, markersize=4)
            
            # 添加趋势线
            if len(data) > 1:
                z = np.polyfit(range(len(data)), data.values, 1)
                p = np.poly1d(z)
                self.axes.plot(data.index, p(range(len(data))), "r--", alpha=0.7, linewidth=1.5, label='趋势线')
            
        elif isinstance(data, pd.DataFrame):
            lines = []
            for column in data.columns:
                line, = self.axes.plot(data.index, data[column], label=column, marker='o', linewidth=2)
                lines.append(line)
            
            self.axes.legend()
        
        # 添加预测数据
        if forecast is not None:
            last_date = data.index[-1]
            if isinstance(data, pd.Series):
                forecast_dates = pd.date_range(start=last_date, periods=len(forecast)+1, freq='M')[1:]
                self.axes.plot(forecast_dates, forecast, 'g--', marker='s', linewidth=2, label='预测')
            self.axes.legend()
        
        self.axes.set_title(title, fontsize=16, fontweight='bold')
        self.axes.set_xlabel(xlabel, fontsize=12)
        self.axes.set_ylabel(ylabel, fontsize=12)
        self.axes.grid(True, linestyle='--', alpha=0.7)
        
        # 格式化Y轴标签
        self.axes.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: format(int(x), ',')))
        
        self.fig.tight_layout()
        self.draw()


class BarChart(FinancialChart):
    """柱状图"""
    def __init__(self, parent=None):
        super().__init__(parent)
        
    def plot_data(self, data, title="财务对比", xlabel="类别", ylabel="金额"):
        self.axes.clear()
        
        if isinstance(data, pd.Series):
            bars = self.axes.bar(range(len(data)), data.values, color=sns.color_palette("husl", len(data)))
            
            # 在柱子上添加数值标签
            for i, bar in enumerate(bars):
                height = bar.get_height()
                self.axes.text(bar.get_x() + bar.get_width()/2., height + 0.01 * max(data.values),
                            f'{height:,.0f}', ha='center', va='bottom', fontweight='bold')
                
            self.axes.set_xticks(range(len(data)))
            self.axes.set_xticklabels(data.index, rotation=45, ha='right')
            
        elif isinstance(data, pd.DataFrame):
            data.plot(ax=self.axes, kind='bar')
        
        self.axes.set_title(title, fontsize=16, fontweight='bold')
        self.axes.set_xlabel(xlabel, fontsize=12)
        self.axes.set_ylabel(ylabel, fontsize=12)
        self.axes.grid(True, linestyle='--', alpha=0.7, axis='y')
        
        # 格式化Y轴标签
        self.axes.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: format(int(x), ',')))
        
        self.fig.tight_layout()
        self.draw()


class PieChart(FinancialChart):
    """饼图"""
    def __init__(self, parent=None):
        super().__init__(parent)
        
    def plot_data(self, data, title="财务占比"):
        self.axes.clear()
        
        if isinstance(data, pd.Series):
            # 只显示前8个最大的部分，其余合并为"其他"
            if len(data) > 8:
                sorted_data = data.sort_values(ascending=False)
                main_data = sorted_data[:7]
                other_sum = sorted_data[7:].sum()
                main_data['其他'] = other_sum
                data = main_data
            
            wedges, texts, autotexts = self.axes.pie(
                data.values, labels=data.index, autopct='%1.1f%%',
                colors=sns.color_palette("husl", len(data)),
                startangle=90, shadow=True
            )
            
            for autotext in autotexts:
                autotext.set_color('white')
                autotext.set_fontweight('bold')
        
        self.axes.set_title(title, fontsize=16, fontweight='bold')
        self.fig.tight_layout()
        self.draw()


class WaterfallChart(FinancialChart):
    """瀑布图"""
    def __init__(self, parent=None):
        super().__init__(parent)
        
    def plot_data(self, data, title="财务瀑布分析", xlabel="项目", ylabel="金额"):
        self.axes.clear()
        
        # 计算累计值
        cumulative = np.zeros(len(data))
        for i in range(1, len(data)):
            cumulative[i] = cumulative[i-1] + data.values[i-1]
        
        # 绘制瀑布图
        bars = self.axes.bar(range(len(data)), data.values, bottom=cumulative, 
                            color=['green' if x >= 0 else 'red' for x in data.values])
        
        # 添加连接线
        for i in range(len(data)-1):
            self.axes.plot([i + 0.5, i + 0.5], [cumulative[i], cumulative[i+1]], 'gray', linestyle='-', linewidth=1)
        
        # 添加数值标签
        for i, bar in enumerate(bars):
            height = bar.get_height()
            y_pos = cumulative[i] + height/2
            self.axes.text(bar.get_x() + bar.get_width()/2., y_pos,
                        f'{height:,.0f}', ha='center', va='center', fontweight='bold')
        
        self.axes.set_xticks(range(len(data)))
        self.axes.set_xticklabels(data.index, rotation=45, ha='right')
        self.axes.set_title(title, fontsize=16, fontweight='bold')
        self.axes.set_xlabel(xlabel, fontsize=12)
        self.axes.set_ylabel(ylabel, fontsize=12)
        self.axes.grid(True, linestyle='--', alpha=0.7, axis='y')
        
        # 格式化Y轴标签
        self.axes.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: format(int(x), ',')))
        
        self.fig.tight_layout()
        self.draw()


class FinancialTable(QTableWidget):
    """财务数据表格"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlternatingRowColors(True)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.verticalHeader().setVisible(False)
        self.setSortingEnabled(True)
        
    def display_data(self, data):
        if isinstance(data, pd.Series):
            data = pd.DataFrame(data)
            
        self.setRowCount(data.shape[0])
        self.setColumnCount(data.shape[1])
        self.setHorizontalHeaderLabels(data.columns)
        
        for i in range(data.shape[0]):
            for j in range(data.shape[1]):
                value = data.iloc[i, j]
                if isinstance(value, (int, float)):
                    item = QTableWidgetItem(f"{value:,.2f}")
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    
                    # 根据数值正负设置颜色
                    if value < 0:
                        item.setForeground(QColor('red'))
                    elif value > 0:
                        item.setForeground(QColor('green'))
                else:
                    item = QTableWidgetItem(str(value))
                self.setItem(i, j, item)
                
        self.resizeColumnsToContents()


class SettingsDialog(QDialog):
    """设置对话框"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置")
        self.setModal(True)
        self.resize(400, 300)
        
        layout = QVBoxLayout(self)
        
        # 主题设置
        theme_group = QGroupBox("主题设置")
        theme_layout = QVBoxLayout(theme_group)
        
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["浅色主题", "深色主题", "蓝色主题", "绿色主题"])
        theme_layout.addWidget(QLabel("选择主题:"))
        theme_layout.addWidget(self.theme_combo)
        
        # 数据设置
        data_group = QGroupBox("数据设置")
        data_layout = QVBoxLayout(data_group)
        
        self.auto_refresh = QCheckBox("自动刷新数据")
        self.refresh_interval = QSpinBox()
        self.refresh_interval.setRange(1, 60)
        self.refresh_interval.setSuffix(" 分钟")
        
        data_layout.addWidget(self.auto_refresh)
        data_layout.addWidget(QLabel("刷新间隔:"))
        data_layout.addWidget(self.refresh_interval)
        
        # 分析设置
        analysis_group = QGroupBox("分析设置")
        analysis_layout = QVBoxLayout(analysis_group)
        
        self.forecast_period = QSpinBox()
        self.forecast_period.setRange(1, 12)
        self.forecast_period.setSuffix(" 个月")
        
        analysis_layout.addWidget(QLabel("预测周期:"))
        analysis_layout.addWidget(self.forecast_period)
        
        layout.addWidget(theme_group)
        layout.addWidget(data_group)
        layout.addWidget(analysis_group)
        
        # 按钮
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
    def get_settings(self):
        return {
            "theme": self.theme_combo.currentText(),
            "auto_refresh": self.auto_refresh.isChecked(),
            "refresh_interval": self.refresh_interval.value(),
            "forecast_period": self.forecast_period.value()
        }
        
    def set_settings(self, settings):
        if "theme" in settings:
            index = self.theme_combo.findText(settings["theme"])
            if index >= 0:
                self.theme_combo.setCurrentIndex(index)
                
        if "auto_refresh" in settings:
            self.auto_refresh.setChecked(settings["auto_refresh"])
            
        if "refresh_interval" in settings:
            self.refresh_interval.setValue(settings["refresh_interval"])
            
        if "forecast_period" in settings:
            self.forecast_period.setValue(settings["forecast_period"])


class CFOAnalysisTool(QMainWindow):
    """CFO分析工具主窗口"""
    def __init__(self):
        super().__init__()
        self.data = None
        self.settings = {
            "theme": "浅色主题",
            "auto_refresh": False,
            "refresh_interval": 5,
            "forecast_period": 3
        }
        self.init_ui()
        self.generate_sample_data()
        
    def init_ui(self):
        self.setWindowTitle("高级CFO可视化分析工具")
        self.setGeometry(100, 50, 1800, 1000)
        
        # 创建菜单栏
        self.create_menus()
        
        # 创建工具栏
        self.create_toolbar()
        
        # 创建状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(200)
        self.progress_bar.setVisible(False)
        self.status_bar.addPermanentWidget(self.progress_bar)
        
        self.status_bar.showMessage("就绪")
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QHBoxLayout(central_widget)
        
        # 创建左侧控制面板
        control_panel = self.create_control_panel()
        main_layout.addWidget(control_panel, 1)
        
        # 创建右侧可视化区域
        visualization_area = self.create_visualization_area()
        main_layout.addWidget(visualization_area, 4)
        
        # 应用初始设置
        self.apply_theme(self.settings["theme"])
        
    def create_menus(self):
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu("文件")
        
        load_action = QAction("导入数据", self)
        load_action.setShortcut("Ctrl+O")
        load_action.triggered.connect(self.load_data)
        file_menu.addAction(load_action)
        
        export_action = QAction("导出报告", self)
        export_action.setShortcut("Ctrl+E")
        export_action.triggered.connect(self.export_report)
        file_menu.addAction(export_action)
        
        file_menu.addSeparator()
        
        settings_action = QAction("设置", self)
        settings_action.setShortcut("Ctrl+,")
        settings_action.triggered.connect(self.show_settings)
        file_menu.addAction(settings_action)
        
        exit_action = QAction("退出", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 分析菜单
        analysis_menu = menubar.addMenu("分析")
        
        trend_action = QAction("趋势分析", self)
        trend_action.triggered.connect(lambda: self.run_analysis("trend"))
        analysis_menu.addAction(trend_action)
        
        forecast_action = QAction("预测分析", self)
        forecast_action.triggered.connect(lambda: self.run_analysis("forecast"))
        analysis_menu.addAction(forecast_action)
        
        ratio_action = QAction("财务比率", self)
        ratio_action.triggered.connect(lambda: self.run_analysis("ratio"))
        analysis_menu.addAction(ratio_action)
        
        # 视图菜单
        view_menu = menubar.addMenu("视图")
        
        # 帮助菜单
        help_menu = menubar.addMenu("帮助")
        about_action = QAction("关于", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
    def create_toolbar(self):
        toolbar = QToolBar("主工具栏")
        toolbar.setIconSize(QSize(24, 24))
        self.addToolBar(toolbar)
        
        load_action = QAction(QIcon("icons/load.png"), "导入数据", self)
        load_action.triggered.connect(self.load_data)
        toolbar.addAction(load_action)
        
        export_action = QAction(QIcon("icons/export.png"), "导出报告", self)
        export_action.triggered.connect(self.export_report)
        toolbar.addAction(export_action)
        
        toolbar.addSeparator()
        
        refresh_action = QAction(QIcon("icons/refresh.png"), "刷新数据", self)
        refresh_action.triggered.connect(self.refresh_data)
        toolbar.addAction(refresh_action)
        
        analyze_action = QAction(QIcon("icons/analyze.png"), "分析数据", self)
        analyze_action.triggered.connect(self.analyze_data)
        toolbar.addAction(analyze_action)
        
        toolbar.addSeparator()
        
        settings_action = QAction(QIcon("icons/settings.png"), "设置", self)
        settings_action.triggered.connect(self.show_settings)
        toolbar.addAction(settings_action)
        
    def create_control_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # 数据选择
        data_group = QGroupBox("数据选择")
        data_layout = QVBoxLayout(data_group)
        
        self.data_selector = QComboBox()
        self.data_selector.addItems(["收入分析", "支出分析", "现金流", "利润分析", "资产负债表", "财务比率"])
        data_layout.addWidget(self.data_selector)
        
        # 时间范围选择
        data_layout.addWidget(QLabel("时间范围"))
        
        date_layout = QHBoxLayout()
        self.start_date = QDateEdit()
        self.start_date.setDate(QDate.currentDate().addMonths(-12))
        self.start_date.setCalendarPopup(True)
        date_layout.addWidget(self.start_date)
        
        date_layout.addWidget(QLabel("至"))
        
        self.end_date = QDateEdit()
        self.end_date.setDate(QDate.currentDate())
        self.end_date.setCalendarPopup(True)
        date_layout.addWidget(self.end_date)
        
        data_layout.addLayout(date_layout)
        
        # 图表类型选择
        data_layout.addWidget(QLabel("图表类型"))
        self.chart_selector = QComboBox()
        self.chart_selector.addItems(["折线图", "柱状图", "饼图", "面积图", "散点图", "瀑布图"])
        data_layout.addWidget(self.chart_selector)
        
        # 分析按钮
        analyze_btn = QPushButton("分析数据")
        analyze_btn.clicked.connect(self.analyze_data)
        data_layout.addWidget(analyze_btn)
        
        layout.addWidget(data_group)
        
        # 指标面板
        metrics_group = QGroupBox("关键指标")
        metrics_layout = QVBoxLayout(metrics_group)
        
        self.metrics_list = QListWidget()
        metrics_layout.addWidget(self.metrics_list)
        
        layout.addWidget(metrics_group)
        
        # 分析控制
        analysis_group = QGroupBox("分析控制")
        analysis_layout = QVBoxLayout(analysis_group)
        
        self.trend_check = QCheckBox("显示趋势线")
        self.trend_check.setChecked(True)
        analysis_layout.addWidget(self.trend_check)
        
        self.forecast_check = QCheckBox("显示预测")
        self.forecast_check.setChecked(True)
        analysis_layout.addWidget(self.forecast_check)
        
        forecast_period_layout = QHBoxLayout()
        forecast_period_layout.addWidget(QLabel("预测周期:"))
        self.forecast_period_spin = QSpinBox()
        self.forecast_period_spin.setRange(1, 12)
        self.forecast_period_spin.setValue(3)
        self.forecast_period_spin.setSuffix(" 个月")
        forecast_period_layout.addWidget(self.forecast_period_spin)
        analysis_layout.addLayout(forecast_period_layout)
        
        layout.addWidget(analysis_group)
        
        # 数据过滤器
        filter_group = QGroupBox("数据过滤器")
        filter_layout = QVBoxLayout(filter_group)
        
        self.filter_min = QDoubleSpinBox()
        self.filter_min.setMaximum(999999999)
        self.filter_min.setPrefix("最小值: ")
        
        self.filter_max = QDoubleSpinBox()
        self.filter_max.setMaximum(999999999)
        self.filter_max.setPrefix("最大值: ")
        
        filter_layout.addWidget(self.filter_min)
        filter_layout.addWidget(self.filter_max)
        
        filter_btn = QPushButton("应用过滤")
        filter_btn.clicked.connect(self.apply_filter)
        filter_layout.addWidget(filter_btn)
        
        layout.addWidget(filter_group)
        layout.addStretch()
        
        return panel
        
    def create_visualization_area(self):
        tab_widget = QTabWidget()
        tab_widget.setTabPosition(QTabWidget.North)
        tab_widget.setDocumentMode(True)
        
        # 创建各个标签页
        self.dashboard_tab = QWidget()
        self.income_tab = QWidget()
        self.cashflow_tab = QWidget()
        self.balance_tab = QWidget()
        self.forecast_tab = QWidget()
        self.ratio_tab = QWidget()
        
        # 设置各个标签页的布局
        self.setup_dashboard_tab()
        self.setup_income_tab()
        self.setup_cashflow_tab()
        self.setup_balance_tab()
        self.setup_forecast_tab()
        self.setup_ratio_tab()
        
        # 添加标签页
        tab_widget.addTab(self.dashboard_tab, "仪表盘")
        tab_widget.addTab(self.income_tab, "利润表")
        tab_widget.addTab(self.cashflow_tab, "现金流量")
        tab_widget.addTab(self.balance_tab, "资产负债表")
        tab_widget.addTab(self.forecast_tab, "预测分析")
        tab_widget.addTab(self.ratio_tab, "财务比率")
        
        return tab_widget
        
    def setup_dashboard_tab(self):
        layout = QVBoxLayout(self.dashboard_tab)
        
        # KPI 指标行
        kpi_layout = QHBoxLayout()
        
        kpis = [
            ("总收入", "¥12,345,678", "#4CAF50", "↑ 12.5%"),
            ("净利润", "¥2,345,678", "#2196F3", "↑ 8.2%"),
            ("现金流", "¥1,234,567", "#FF9800", "↓ 3.1%"),
            ("ROI", "18.5%", "#F44336", "↑ 2.3%"),
            ("流动比率", "2.4", "#9C27B0", "→ 稳定"),
            ("负债率", "42.3%", "#607D8B", "↓ 1.7%")
        ]
        
        for title, value, color, trend in kpis:
            kpi_widget = QWidget()
            kpi_widget.setStyleSheet(f"""
                background-color: {color}; 
                border-radius: 8px; 
                padding: 10px;
                color: white;
            """)
            kpi_layout_widget = QVBoxLayout(kpi_widget)
            
            title_label = QLabel(title)
            title_label.setStyleSheet("font-size: 14px; font-weight: bold;")
            
            value_label = QLabel(value)
            value_label.setStyleSheet("font-size: 20px; font-weight: bold;")
            
            trend_label = QLabel(trend)
            trend_label.setStyleSheet("font-size: 12px;")
            
            kpi_layout_widget.addWidget(title_label)
            kpi_layout_widget.addWidget(value_label)
            kpi_layout_widget.addWidget(trend_label)
            
            kpi_layout.addWidget(kpi_widget)
        
        layout.addLayout(kpi_layout)
        
        # 图表区域
        splitter = QSplitter(Qt.Vertical)
        
        # 上部图表
        upper_widget = QWidget()
        upper_layout = QHBoxLayout(upper_widget)
        
        self.chart1 = TimeSeriesChart()
        upper_layout.addWidget(self.chart1)
        
        self.chart2 = BarChart()
        upper_layout.addWidget(self.chart2)
        
        splitter.addWidget(upper_widget)
        
        # 下部图表和表格
        lower_widget = QWidget()
        lower_layout = QHBoxLayout(lower_widget)
        
        self.chart3 = PieChart()
        lower_layout.addWidget(self.chart3)
        
        self.table = FinancialTable()
        lower_layout.addWidget(self.table)
        
        splitter.addWidget(lower_widget)
        splitter.setSizes([400, 300])
        
        layout.addWidget(splitter)
        
    def setup_income_tab(self):
        layout = QVBoxLayout(self.income_tab)
        
        # 收入分析控件
        control_layout = QHBoxLayout()
        
        period_combo = QComboBox()
        period_combo.addItems(["月度", "季度", "年度"])
        control_layout.addWidget(QLabel("分析周期:"))
        control_layout.addWidget(period_combo)
        
        compare_check = QCheckBox("同比分析")
        compare_check.setChecked(True)
        control_layout.addWidget(compare_check)
        
        control_layout.addStretch()
        
        layout.addLayout(control_layout)
        
        # 收入图表
        self.income_chart = TimeSeriesChart()
        layout.addWidget(self.income_chart)
        
        # 收入表格
        self.income_table = FinancialTable()
        layout.addWidget(self.income_table)
        
    def setup_cashflow_tab(self):
        layout = QVBoxLayout(self.cashflow_tab)
        
        # 现金流分析控件
        control_layout = QHBoxLayout()
        
        cashflow_type = QComboBox()
        cashflow_type.addItems(["经营现金流", "投资现金流", "筹资现金流", "净现金流"])
        control_layout.addWidget(QLabel("现金流类型:"))
        control_layout.addWidget(cashflow_type)
        
        control_layout.addStretch()
        
        layout.addLayout(control_layout)
        
        # 现金流图表
        self.cashflow_chart = WaterfallChart()
        layout.addWidget(self.cashflow_chart)
        
        # 现金流表格
        self.cashflow_table = FinancialTable()
        layout.addWidget(self.cashflow_table)
        
    def setup_balance_tab(self):
        layout = QVBoxLayout(self.balance_tab)
        layout.addWidget(QLabel("资产负债表分析功能"))
        
        # 资产负债对比图表
        self.balance_chart = BarChart()
        layout.addWidget(self.balance_chart)
        
    def setup_forecast_tab(self):
        layout = QVBoxLayout(self.forecast_tab)
        
        # 预测控制
        forecast_layout = QHBoxLayout()
        
        model_combo = QComboBox()
        model_combo.addItems(["线性回归", "多项式回归", "时间序列", "机器学习"])
        forecast_layout.addWidget(QLabel("预测模型:"))
        forecast_layout.addWidget(model_combo)
        
        confidence_spin = QDoubleSpinBox()
        confidence_spin.setRange(50, 99)
        confidence_spin.setValue(95)
        confidence_spin.setSuffix("% 置信度")
        forecast_layout.addWidget(confidence_spin)
        
        forecast_btn = QPushButton("生成预测")
        forecast_btn.clicked.connect(self.generate_forecast)
        forecast_layout.addWidget(forecast_btn)
        
        forecast_layout.addStretch()
        
        layout.addLayout(forecast_layout)
        
        # 预测图表
        self.forecast_chart = TimeSeriesChart()
        layout.addWidget(self.forecast_chart)
        
        # 预测结果表格
        self.forecast_table = FinancialTable()
        layout.addWidget(self.forecast_table)
        
    def setup_ratio_tab(self):
        layout = QVBoxLayout(self.ratio_tab)
        
        # 比率分析控件
        ratio_layout = QHBoxLayout()
        
        ratio_type = QComboBox()
        ratio_type.addItems(["盈利能力", "偿债能力", "运营能力", "成长能力"])
        ratio_layout.addWidget(QLabel("比率类型:"))
        ratio_layout.addWidget(ratio_type)
        
        benchmark_check = QCheckBox("显示行业基准")
        benchmark_check.setChecked(True)
        ratio_layout.addWidget(benchmark_check)
        
        ratio_layout.addStretch()
        
        layout.addLayout(ratio_layout)
        
        # 比率图表
        self.ratio_chart = BarChart()
        layout.addWidget(self.ratio_chart)
        
        # 比率表格
        self.ratio_table = FinancialTable()
        layout.addWidget(self.ratio_table)
        
    def generate_sample_data(self):
        """生成示例数据"""
        dates = pd.date_range(start='2022-01-01', end='2023-12-31', freq='M')
        
        # 生成更真实的财务数据
        base_revenue = 1000000
        revenue = base_revenue + np.random.normal(0, 200000, len(dates))
        revenue = np.cumsum(revenue)  # 累积收入，模拟增长
        
        # 支出与收入相关但有一定波动
        expenses = revenue * 0.6 + np.random.normal(0, 50000, len(dates))
        profit = revenue - expenses
        
        # 生成资产和负债数据
        assets = np.cumsum(np.random.normal(500000, 100000, len(dates)))
        liabilities = assets * 0.4 + np.random.normal(0, 50000, len(dates))
        
        self.financial_data = pd.DataFrame({
            '日期': dates,
            '收入': revenue,
            '支出': expenses,
            '利润': profit,
            '资产': assets,
            '负债': liabilities,
            '净资产': assets - liabilities
        })
        self.financial_data.set_index('日期', inplace=True)
        
        # 更新图表
        self.update_charts()
        
    def update_charts(self):
        """更新所有图表"""
        if self.financial_data is not None:
            # 仪表盘图表
            self.chart1.plot_data(self.financial_data['收入'], "月度收入趋势", "月份", "收入 (元)")
            
            # 最近6个月的数据对比
            recent_data = self.financial_data[['收入', '支出', '利润']].tail(6)
            self.chart2.plot_data(recent_data.T, "近期财务对比", "类别", "金额 (元)")
            
            # 支出分布饼图
            expense_categories = ['工资', '租金', '营销', '研发', '行政', '其他']
            expense_values = np.random.dirichlet(np.ones(6), size=1)[0] * self.financial_data['支出'].mean() * 6
            pie_data = pd.Series(expense_values, index=expense_categories, name='支出分布')
            self.chart3.plot_data(pie_data, "支出分布")
            
            # 更新表格
            self.table.display_data(self.financial_data.tail(12))
            
            # 更新指标
            self.update_metrics()
            
            # 更新其他标签页的图表
            self.income_chart.plot_data(self.financial_data[['收入', '支出', '利润']], "利润表趋势", "日期", "金额")
            self.income_table.display_data(self.financial_data[['收入', '支出', '利润']].tail(12))
            
            # 现金流瀑布图
            cashflow_data = pd.Series({
                '期初现金': 500000,
                '经营现金': 750000,
                '投资现金': -300000,
                '筹资现金': 200000,
                '期末现金': 1150000
            })
            self.cashflow_chart.plot_data(cashflow_data, "现金流量分析", "项目", "金额")
            
            # 资产负债对比
            balance_data = self.financial_data[['资产', '负债', '净资产']].iloc[-1]
            self.balance_chart.plot_data(balance_data, "资产负债对比", "项目", "金额")
            
    def update_metrics(self):
        """更新关键指标"""
        if self.financial_data is not None:
            self.metrics_list.clear()
            
            # 计算各种财务指标
            total_revenue = self.financial_data['收入'].sum()
            total_expenses = self.financial_data['支出'].sum()
            net_profit = self.financial_data['利润'].sum()
            avg_monthly_revenue = self.financial_data['收入'].mean()
            revenue_growth = self.financial_data['收入'].pct_change().mean() * 100
            
            # 财务比率
            current_ratio = self.financial_data['资产'].iloc[-1] / self.financial_data['负债'].iloc[-1]
            profit_margin = net_profit / total_revenue * 100
            
            metrics = [
                f"总收入: {total_revenue:,.2f}",
                f"总支出: {total_expenses:,.2f}",
                f"净利润: {net_profit:,.2f}",
                f"平均月收入: {avg_monthly_revenue:,.2f}",
                f"收入增长率: {revenue_growth:.2f}%",
                f"流动比率: {current_ratio:.2f}",
                f"净利润率: {profit_margin:.2f}%",
                f"资产总额: {self.financial_data['资产'].iloc[-1]:,.2f}",
                f"负债总额: {self.financial_data['负债'].iloc[-1]:,.2f}",
                f"净资产: {self.financial_data['净资产'].iloc[-1]:,.2f}"
            ]
            self.metrics_list.addItems(metrics)
        
    def load_data(self):
        """加载数据"""
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(
            self, "打开财务数据文件", "", 
            "Excel Files (*.xlsx *.xls);;CSV Files (*.csv);;All Files (*)", 
            options=options
        )
        
        if file_name:
            try:
                self.status_bar.showMessage("正在加载数据...")
                self.progress_bar.setVisible(True)
                
                # 模拟加载过程
                for i in range(101):
                    QApplication.processEvents()
                    self.progress_bar.setValue(i)
                    QThread.msleep(20)  # 模拟耗时操作
                
                if file_name.endswith(('.xlsx', '.xls')):
                    self.data = pd.read_excel(file_name)
                else:
                    self.data = pd.read_csv(file_name)
                    
                QMessageBox.information(self, "成功", "数据加载成功！")
                self.status_bar.showMessage(f"已加载: {file_name}")
                
                # 更新UI
                self.update_charts()
                
            except Exception as e:
                QMessageBox.critical(self, "错误", f"加载数据时出错: {str(e)}")
            finally:
                self.progress_bar.setVisible(False)
                
    def export_report(self):
        """导出报告"""
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getSaveFileName(
            self, "导出财务报告", "", 
            "PDF Files (*.pdf);;HTML Files (*.html);;Excel Files (*.xlsx);;All Files (*)", 
            options=options
        )
        
        if file_name:
            try:
                self.status_bar.showMessage("正在生成报告...")
                self.progress_bar.setVisible(True)
                
                # 模拟报告生成过程
                for i in range(101):
                    QApplication.processEvents()
                    self.progress_bar.setValue(i)
                    QThread.msleep(30)  # 模拟耗时操作
                
                QMessageBox.information(self, "成功", f"报告已导出到: {file_name}")
                self.status_bar.showMessage(f"报告已导出: {file_name}")
                
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导出报告时出错: {str(e)}")
            finally:
                self.progress_bar.setVisible(False)
            
    def refresh_data(self):
        """刷新数据"""
        self.status_bar.showMessage("正在刷新数据...")
        self.generate_sample_data()
        self.status_bar.showMessage("数据已刷新")
        
    def analyze_data(self):
        """分析数据"""
        selected_analysis = self.data_selector.currentText()
        chart_type = self.chart_selector.currentText()
        
        self.status_bar.showMessage(f"正在分析: {selected_analysis} 使用: {chart_type}")
        
        # 模拟分析过程
        self.progress_bar.setVisible(True)
        for i in range(101):
            QApplication.processEvents()
            self.progress_bar.setValue(i)
            QThread.msleep(20)
            
        QMessageBox.information(self, "分析完成", f"{selected_analysis} 已完成，使用 {chart_type} 图表展示")
        self.progress_bar.setVisible(False)
        
    def run_analysis(self, analysis_type):
        """运行高级分析"""
        if self.financial_data is None:
            QMessageBox.warning(self, "警告", "请先加载数据")
            return
            
        self.status_bar.showMessage(f"正在运行{analysis_type}分析...")
        self.progress_bar.setVisible(True)
        
        # 创建分析线程
        self.analysis_worker = AnalysisWorker(self.financial_data, analysis_type)
        self.analysis_worker.progress.connect(self.progress_bar.setValue)
        self.analysis_worker.finished.connect(self.on_analysis_finished)
        self.analysis_worker.start()
        
    def on_analysis_finished(self, result):
        """分析完成处理"""
        self.progress_bar.setVisible(False)
        
        if "error" in result:
            QMessageBox.critical(self, "分析错误", result["error"])
            self.status_bar.showMessage("分析失败")
        else:
            QMessageBox.information(self, "分析完成", "数据分析已完成")
            self.status_bar.showMessage("分析完成")
            
            # 在这里处理分析结果
            print("分析结果:", result)
            
    def generate_forecast(self):
        """生成预测"""
        if self.financial_data is None:
            QMessageBox.warning(self, "警告", "请先加载数据")
            return
            
        self.status_bar.showMessage("正在生成预测...")
        self.progress_bar.setVisible(True)
        
        # 模拟预测过程
        for i in range(101):
            QApplication.processEvents()
            self.progress_bar.setValue(i)
            QThread.msleep(25)
            
        # 生成模拟预测数据
        forecast_dates = pd.date_range(
            start=self.financial_data.index[-1] + pd.DateOffset(months=1),
            periods=self.settings["forecast_period"],
            freq='M'
        )
        
        # 简单线性预测
        forecast_data = {}
        for column in self.financial_data.select_dtypes(include=[np.number]).columns:
            series = self.financial_data[column]
            x = np.arange(len(series)).reshape(-1, 1)
            y = series.values
            
            model = LinearRegression()
            model.fit(x, y)
            
            future_x = np.arange(len(series), len(series) + self.settings["forecast_period"]).reshape(-1, 1)
            future_y = model.predict(future_x)
            
            forecast_data[column] = future_y
        
        # 更新预测图表
        forecast_df = pd.DataFrame(forecast_data, index=forecast_dates)
        combined_data = pd.concat([self.financial_data, forecast_df])
        
        self.forecast_chart.plot_data(
            combined_data['收入'], 
            "收入预测", 
            "日期", 
            "金额 (元)",
            forecast=forecast_df['收入'].values
        )
        
        self.forecast_table.display_data(forecast_df)
        
        self.status_bar.showMessage("预测完成")
        self.progress_bar.setVisible(False)
        
    def apply_filter(self):
        """应用数据过滤器"""
        min_val = self.filter_min.value()
        max_val = self.filter_max.value()
        
        if min_val > max_val:
            QMessageBox.warning(self, "警告", "最小值不能大于最大值")
            return
            
        self.status_bar.showMessage(f"应用过滤: {min_val} 到 {max_val}")
        
        # 在实际应用中，这里会根据过滤条件筛选数据
        # 这里只是演示
        
    def show_settings(self):
        """显示设置对话框"""
        dialog = SettingsDialog(self)
        dialog.set_settings(self.settings)
        
        if dialog.exec_() == QDialog.Accepted:
            new_settings = dialog.get_settings()
            self.settings.update(new_settings)
            
            # 应用新设置
            self.apply_theme(self.settings["theme"])
            
            QMessageBox.information(self, "设置已保存", "应用程序设置已更新")
            
    def apply_theme(self, theme):
        """应用主题设置"""
        if theme == "浅色主题":
            self.apply_light_theme()
        elif theme == "深色主题":
            self.apply_dark_theme()
        elif theme == "蓝色主题":
            self.apply_blue_theme()
        elif theme == "绿色主题":
            self.apply_green_theme()
            
    def apply_light_theme(self):
        """应用浅色主题"""
        palette = QApplication.palette()
        QApplication.setPalette(palette)
        
    def apply_dark_theme(self):
        """应用深色主题"""
        dark_palette = QPalette()
        dark_palette.setColor(QPalette.Window, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.WindowText, Qt.white)
        dark_palette.setColor(QPalette.Base, QColor(25, 25, 25))
        dark_palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ToolTipBase, Qt.white)
        dark_palette.setColor(QPalette.ToolTipText, Qt.white)
        dark_palette.setColor(QPalette.Text, Qt.white)
        dark_palette.setColor(QPalette.Button, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ButtonText, Qt.white)
        dark_palette.setColor(QPalette.BrightText, Qt.red)
        dark_palette.setColor(QPalette.Link, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.HighlightedText, Qt.black)
        
        QApplication.setPalette(dark_palette)
        
    def apply_blue_theme(self):
        """应用蓝色主题"""
        blue_palette = QPalette()
        blue_palette.setColor(QPalette.Window, QColor(240, 248, 255))
        blue_palette.setColor(QPalette.WindowText, QColor(0, 0, 139))
        blue_palette.setColor(QPalette.Base, QColor(230, 240, 255))
        blue_palette.setColor(QPalette.Text, QColor(0, 0, 139))
        blue_palette.setColor(QPalette.Button, QColor(173, 216, 230))
        blue_palette.setColor(QPalette.ButtonText, QColor(0, 0, 139))
        
        QApplication.setPalette(blue_palette)
        
    def apply_green_theme(self):
        """应用绿色主题"""
        green_palette = QPalette()
        green_palette.setColor(QPalette.Window, QColor(240, 255, 240))
        green_palette.setColor(QPalette.WindowText, QColor(0, 100, 0))
        green_palette.setColor(QPalette.Base, QColor(230, 255, 230))
        green_palette.setColor(QPalette.Text, QColor(0, 100, 0))
        green_palette.setColor(QPalette.Button, QColor(144, 238, 144))
        green_palette.setColor(QPalette.ButtonText, QColor(0, 100, 0))
        
        QApplication.setPalette(green_palette)
        
    def show_about(self):
        """显示关于信息"""
        about_text = """
        <h2>高级CFO可视化分析工具</h2>
        <p>版本: 2.0.0</p>
        <p>© 2023 财务科技公司</p>
        <p>这是一个专业的财务数据分析工具，为CFO和财务团队提供深入的数据洞察和决策支持。</p>
        <p>功能特点:</p>
        <ul>
            <li>多维度财务数据分析</li>
            <li>高级可视化图表</li>
            <li>趋势分析和预测</li>
            <li>财务比率计算</li>
            <li>自定义报表生成</li>
            <li>多主题支持</li>
        </ul>
        """
        
        msg = QMessageBox(self)
        msg.setWindowTitle("关于 CFO 分析工具")
        msg.setText(about_text)
        msg.exec_()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    # 设置应用程序字体
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    
    window = CFOAnalysisTool()
    window.show()
    
    sys.exit(app.exec_())