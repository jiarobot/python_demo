import sys
import json
import numpy as np
import pandas as pd
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QSplitter, QTreeWidget, QTreeWidgetItem, QTabWidget, QTextEdit,
                             QTableWidget, QTableWidgetItem, QHeaderView, QToolBar, QAction,
                             QStatusBar, QLabel, QComboBox, QPushButton, QFileDialog, QMessageBox,
                             QDockWidget, QFormLayout, QLineEdit, QSpinBox, QDoubleSpinBox,
                             QGroupBox, QCheckBox, QProgressBar, QListWidget, QListView)
from PyQt5.QtCore import Qt, QSize, QThread, pyqtSignal
from PyQt5.QtGui import QIcon, QFont, QColor, QPixmap
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import seaborn as sns
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings('ignore')


class AnalysisThread(QThread):
    """分析线程，用于执行耗时的分析任务"""
    progress_signal = pyqtSignal(int)
    result_signal = pyqtSignal(dict)
    
    def __init__(self, analysis_type, data):
        super().__init__()
        self.analysis_type = analysis_type
        self.data = data
        
    def run(self):
        """执行分析"""
        try:
            if self.analysis_type == "risk_analysis":
                result = self.risk_analysis()
            elif self.analysis_type == "feasibility_prediction":
                result = self.feasibility_prediction()
            elif self.analysis_type == "sensitivity_analysis":
                result = self.sensitivity_analysis()
            else:
                result = {"error": "未知的分析类型"}
                
            self.result_signal.emit(result)
        except Exception as e:
            self.result_signal.emit({"error": str(e)})
    
    def risk_analysis(self):
        """风险分析"""
        result = {}
        
        # 模拟风险分析
        for i in range(5):
            self.progress_signal.emit(i * 20)
            self.msleep(500)  # 模拟耗时操作
            
        result["risk_score"] = np.random.randint(1, 100)
        result["high_risks"] = [
            {"name": "技术依赖", "probability": 0.7, "impact": 0.8},
            {"name": "资源不足", "probability": 0.6, "impact": 0.7},
            {"name": "时间压力", "probability": 0.5, "impact": 0.9}
        ]
        result["recommendations"] = [
            "建立备用技术方案",
            "增加资源预算",
            "制定详细的时间管理计划"
        ]
        
        return result
    
    def feasibility_prediction(self):
        """可行性预测"""
        result = {}
        
        # 模拟机器学习预测
        for i in range(10):
            self.progress_signal.emit(i * 10)
            self.msleep(300)  # 模拟耗时操作
            
        # 使用简单的随机森林分类器进行演示
        X, y = self.generate_sample_data()
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        
        clf = RandomForestClassifier(n_estimators=100, random_state=42)
        clf.fit(X_train_scaled, y_train)
        
        y_pred = clf.predict(X_test_scaled)
        accuracy = accuracy_score(y_test, y_pred)
        
        result["accuracy"] = accuracy
        result["feature_importance"] = dict(zip(
            ["技术复杂度", "资源可用性", "时间压力", "团队经验", "预算充足性"],
            clf.feature_importances_
        ))
        result["prediction"] = "可行" if np.random.random() > 0.3 else "需重新评估"
        
        return result
    
    def sensitivity_analysis(self):
        """敏感性分析"""
        result = {}
        
        # 模拟敏感性分析
        for i in range(8):
            self.progress_signal.emit(i * 12)
            self.msleep(400)  # 模拟耗时操作
            
        factors = ["预算", "时间", "资源", "技术复杂度", "市场需求"]
        sensitivities = np.random.random(5) * 100
        
        result["sensitivity_analysis"] = dict(zip(factors, sensitivities))
        result["critical_factors"] = [factors[i] for i in np.argsort(sensitivities)[-2:]]
        
        return result
    
    def generate_sample_data(self):
        """生成示例数据"""
        np.random.seed(42)
        n_samples = 1000
        
        # 特征：技术复杂度、资源可用性、时间压力、团队经验、预算充足性
        X = np.random.randn(n_samples, 5)
        
        # 目标变量：项目是否可行 (1=可行, 0=不可行)
        y = (X[:, 0] * 0.3 + X[:, 1] * 0.4 + X[:, 2] * (-0.2) + X[:, 3] * 0.5 + X[:, 4] * 0.4 > 0).astype(int)
        
        return X, y


class MplCanvas(FigureCanvas):
    """Matplotlib图表画布"""
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_subplot(111)
        super(MplCanvas, self).__init__(self.fig)
        self.setParent(parent)


class AdvancedProjectAnalysisSystem(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_project = None
        self.analysis_data = {}
        self.initUI()
        
    def initUI(self):
        """初始化用户界面"""
        self.setWindowTitle('高级项目技术可行性研究分析系统')
        self.setGeometry(100, 100, 1600, 1000)
        
        # 创建中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QHBoxLayout(central_widget)
        
        # 左侧导航树
        self.navigation_tree = QTreeWidget()
        self.navigation_tree.setHeaderLabel('分析模块')
        self.navigation_tree.setMaximumWidth(250)
        
        # 添加分析模块
        modules = {
            '项目概况': ['基本信息', '项目描述', '目标分析', '利益相关者'],
            '技术分析': ['技术评估', '技术风险', '技术依赖', '技术趋势'],
            '资源分析': ['人力资源', '设备资源', '财务资源', '时间资源'],
            '市场分析': ['市场需求', '竞争分析', '市场趋势', 'SWOT分析'],
            '风险评估': ['技术风险', '市场风险', '管理风险', '综合风险'],
            '可行性分析': ['技术可行性', '经济可行性', '操作可行性', '综合评估'],
            '高级分析': ['敏感性分析', '蒙特卡洛模拟', '机器学习预测', '优化方案']
        }
        
        for module, sub_modules in modules.items():
            parent = QTreeWidgetItem(self.navigation_tree, [module])
            for sub_module in sub_modules:
                child = QTreeWidgetItem(parent, [sub_module])
            parent.setExpanded(True)
        
        self.navigation_tree.itemClicked.connect(self.on_module_selected)
        
        # 右侧选项卡区域
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.tabCloseRequested.connect(self.close_tab)
        
        # 分割器
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self.navigation_tree)
        splitter.addWidget(self.tab_widget)
        splitter.setSizes([250, 1350])
        
        main_layout.addWidget(splitter)
        
        # 创建工具栏
        self.create_toolbar()
        
        # 创建状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage('就绪')
        
        # 创建数据视图停靠窗口
        self.create_data_dock()
        
        # 创建分析工具停靠窗口
        self.create_tools_dock()
        
        # 创建高级分析停靠窗口
        self.create_advanced_analysis_dock()
        
        # 显示欢迎页面
        self.show_welcome_page()
        
    def create_toolbar(self):
        """创建工具栏"""
        toolbar = QToolBar('主工具栏')
        toolbar.setIconSize(QSize(24, 24))
        self.addToolBar(toolbar)
        
        # 新建项目
        new_action = QAction(QIcon('icons/new.png'), '新建项目', self)
        new_action.setShortcut('Ctrl+N')
        new_action.triggered.connect(self.new_project)
        toolbar.addAction(new_action)
        
        # 打开项目
        open_action = QAction(QIcon('icons/open.png'), '打开项目', self)
        open_action.setShortcut('Ctrl+O')
        open_action.triggered.connect(self.open_project)
        toolbar.addAction(open_action)
        
        # 保存项目
        save_action = QAction(QIcon('icons/save.png'), '保存项目', self)
        save_action.setShortcut('Ctrl+S')
        save_action.triggered.connect(self.save_project)
        toolbar.addAction(save_action)
        
        toolbar.addSeparator()
        
        # 导入数据
        import_action = QAction(QIcon('icons/import.png'), '导入数据', self)
        import_action.triggered.connect(self.import_data)
        toolbar.addAction(import_action)
        
        # 导出数据
        export_action = QAction(QIcon('icons/export.png'), '导出数据', self)
        export_action.triggered.connect(self.export_data)
        toolbar.addAction(export_action)
        
        toolbar.addSeparator()
        
        # 数据分析
        analysis_action = QAction(QIcon('icons/analysis.png'), '数据分析', self)
        analysis_action.triggered.connect(self.run_analysis)
        toolbar.addAction(analysis_action)
        
        # 生成报告
        report_action = QAction(QIcon('icons/report.png'), '生成报告', self)
        report_action.triggered.connect(self.generate_report)
        toolbar.addAction(report_action)
        
        toolbar.addSeparator()
        
        # 图表工具
        chart_action = QAction(QIcon('icons/chart.png'), '图表分析', self)
        chart_action.triggered.connect(self.show_charts)
        toolbar.addAction(chart_action)
        
        # 设置
        settings_action = QAction(QIcon('icons/settings.png'), '设置', self)
        settings_action.triggered.connect(self.show_settings)
        toolbar.addAction(settings_action)
        
    def create_data_dock(self):
        """创建数据视图停靠窗口"""
        data_dock = QDockWidget('项目数据', self)
        data_dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        
        data_widget = QWidget()
        data_layout = QVBoxLayout(data_widget)
        
        # 数据筛选器
        filter_group = QGroupBox("数据筛选")
        filter_layout = QHBoxLayout(filter_group)
        
        filter_combo = QComboBox()
        filter_combo.addItems(["全部", "技术数据", "资源数据", "市场数据", "风险数据"])
        filter_layout.addWidget(filter_combo)
        
        filter_btn = QPushButton("筛选")
        filter_btn.clicked.connect(self.filter_data)
        filter_layout.addWidget(filter_btn)
        
        data_layout.addWidget(filter_group)
        
        # 数据表格
        self.data_table = QTableWidget()
        self.data_table.setColumnCount(5)
        self.data_table.setHorizontalHeaderLabels(['ID', '指标', '当前值', '预期值', '偏差'])
        self.data_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        # 填充示例数据
        self.populate_sample_data()
        
        data_layout.addWidget(self.data_table)
        
        # 数据操作按钮
        button_layout = QHBoxLayout()
        add_btn = QPushButton('添加数据')
        add_btn.clicked.connect(self.add_data_row)
        edit_btn = QPushButton('编辑数据')
        edit_btn.clicked.connect(self.edit_data)
        delete_btn = QPushButton('删除数据')
        delete_btn.clicked.connect(self.delete_data)
        import_btn = QPushButton('导入CSV')
        import_btn.clicked.connect(self.import_csv)
        
        button_layout.addWidget(add_btn)
        button_layout.addWidget(edit_btn)
        button_layout.addWidget(delete_btn)
        button_layout.addWidget(import_btn)
        data_layout.addLayout(button_layout)
        
        data_dock.setWidget(data_widget)
        self.addDockWidget(Qt.RightDockWidgetArea, data_dock)
        
    def create_tools_dock(self):
        """创建分析工具停靠窗口"""
        tools_dock = QDockWidget('分析工具', self)
        tools_dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        
        tools_widget = QWidget()
        tools_layout = QVBoxLayout(tools_widget)
        
        # 分析工具选择
        tool_form = QFormLayout()
        self.tool_combo = QComboBox()
        self.tool_combo.addItems(['SWOT分析', 'PEST分析', '成本效益分析', '风险矩阵', '技术成熟度评估'])
        tool_form.addRow('分析工具:', self.tool_combo)
        
        # 参数输入
        self.param1_input = QLineEdit()
        tool_form.addRow('参数1:', self.param1_input)
        
        self.param2_input = QDoubleSpinBox()
        self.param2_input.setRange(0, 100)
        self.param2_input.setValue(50)
        tool_form.addRow('参数2:', self.param2_input)
        
        self.param3_input = QSpinBox()
        self.param3_input.setRange(1, 10)
        self.param3_input.setValue(5)
        tool_form.addRow('参数3:', self.param3_input)
        
        tools_layout.addLayout(tool_form)
        
        # 执行按钮
        run_btn = QPushButton('执行分析')
        run_btn.clicked.connect(self.run_tool_analysis)
        tools_layout.addWidget(run_btn)
        
        # 结果展示
        self.tool_result = QTextEdit()
        self.tool_result.setMaximumHeight(200)
        tools_layout.addWidget(QLabel('分析结果:'))
        tools_layout.addWidget(self.tool_result)
        
        tools_dock.setWidget(tools_widget)
        self.addDockWidget(Qt.RightDockWidgetArea, tools_dock)
        
    def create_advanced_analysis_dock(self):
        """创建高级分析停靠窗口"""
        advanced_dock = QDockWidget('高级分析', self)
        advanced_dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        
        advanced_widget = QWidget()
        advanced_layout = QVBoxLayout(advanced_widget)
        
        # 分析类型选择
        analysis_combo = QComboBox()
        analysis_combo.addItems(["风险分析", "可行性预测", "敏感性分析"])
        advanced_layout.addWidget(QLabel("分析类型:"))
        advanced_layout.addWidget(analysis_combo)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        advanced_layout.addWidget(self.progress_bar)
        
        # 执行按钮
        run_advanced_btn = QPushButton("执行高级分析")
        run_advanced_btn.clicked.connect(lambda: self.run_advanced_analysis(analysis_combo.currentText()))
        advanced_layout.addWidget(run_advanced_btn)
        
        # 结果展示
        self.advanced_result = QTextEdit()
        self.advanced_result.setMaximumHeight(300)
        advanced_layout.addWidget(QLabel('分析结果:'))
        advanced_layout.addWidget(self.advanced_result)
        
        advanced_dock.setWidget(advanced_widget)
        self.addDockWidget(Qt.RightDockWidgetArea, advanced_dock)
        
    def show_welcome_page(self):
        """显示欢迎页面"""
        welcome_widget = QWidget()
        layout = QVBoxLayout(welcome_widget)
        
        # 欢迎标题
        title = QLabel("高级项目技术可行性研究分析系统")
        title.setAlignment(Qt.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(20)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)
        
        # 欢迎图片
        pixmap = QPixmap(400, 300)
        pixmap.fill(QColor(200, 230, 255))
        image_label = QLabel()
        image_label.setPixmap(pixmap)
        image_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(image_label)
        
        # 欢迎文本
        welcome_text = QLabel(
            "<h3>欢迎使用高级项目技术可行性研究分析系统</h3>"
            "<p>本系统提供全面的项目技术可行性分析功能，包括:</p>"
            "<ul>"
            "<li>项目概况管理</li>"
            "<li>技术分析与评估</li>"
            "<li>资源与市场分析</li>"
            "<li>风险评估与管理</li>"
            "<li>可行性综合评估</li>"
            "<li>高级分析与预测</li>"
            "</ul>"
            "<p>请从左侧导航树选择分析模块，或使用工具栏开始新的项目。</p>"
        )
        welcome_text.setAlignment(Qt.AlignCenter)
        welcome_text.setWordWrap(True)
        layout.addWidget(welcome_text)
        
        # 最近项目列表
        recent_group = QGroupBox("最近项目")
        recent_layout = QVBoxLayout(recent_group)
        
        recent_list = QListWidget()
        recent_list.addItems(["项目A - 技术平台开发", "项目B - 市场分析", "项目C - 产品可行性研究"])
        recent_layout.addWidget(recent_list)
        
        layout.addWidget(recent_group)
        
        self.tab_widget.addTab(welcome_widget, "欢迎")
        self.tab_widget.setCurrentIndex(0)
        
    def populate_sample_data(self):
        """填充示例数据"""
        indicators = [
            ("TECH-001", "技术复杂度", 7.2, 6.5, 0.7),
            ("TECH-002", "技术成熟度", 8.1, 7.8, 0.3),
            ("TECH-003", "团队经验", 6.8, 7.5, -0.7),
            ("RES-001", "预算充足性", 7.5, 8.0, -0.5),
            ("RES-002", "时间资源", 6.2, 7.0, -0.8),
            ("RES-003", "人力资源", 7.8, 7.5, 0.3),
            ("MRKT-001", "市场需求", 8.5, 8.2, 0.3),
            ("MRKT-002", "竞争强度", 6.5, 7.0, -0.5),
            ("RISK-001", "技术风险", 6.8, 6.0, 0.8),
            ("RISK-002", "市场风险", 5.9, 6.5, -0.6)
        ]
        
        self.data_table.setRowCount(len(indicators))
        for i, (id, name, current, expected, deviation) in enumerate(indicators):
            self.data_table.setItem(i, 0, QTableWidgetItem(id))
            self.data_table.setItem(i, 1, QTableWidgetItem(name))
            self.data_table.setItem(i, 2, QTableWidgetItem(str(current)))
            self.data_table.setItem(i, 3, QTableWidgetItem(str(expected)))
            
            # 根据偏差值设置颜色
            deviation_item = QTableWidgetItem(str(deviation))
            if deviation > 0:
                deviation_item.setForeground(QColor(0, 128, 0))  # 绿色
            else:
                deviation_item.setForeground(QColor(255, 0, 0))  # 红色
                
            self.data_table.setItem(i, 4, deviation_item)
        
    def on_module_selected(self, item, column):
        """处理模块选择事件"""
        if not item.parent():  # 顶级项目
            return
            
        module_name = item.text(0)
        parent_name = item.parent().text(0)
        
        # 检查是否已打开该模块
        for i in range(self.tab_widget.count()):
            if self.tab_widget.tabText(i) == f"{parent_name} - {module_name}":
                self.tab_widget.setCurrentIndex(i)
                return
                
        # 创建新选项卡
        tab_content = self.create_module_content(parent_name, module_name)
        if tab_content:
            self.tab_widget.addTab(tab_content, f"{parent_name} - {module_name}")
            self.tab_widget.setCurrentIndex(self.tab_widget.count() - 1)
        
    def create_module_content(self, parent_name, module_name):
        """创建模块内容"""
        if parent_name == '项目概况' and module_name == '基本信息':
            return self.create_basic_info_widget()
        elif parent_name == '技术分析' and module_name == '技术评估':
            return self.create_tech_assessment_widget()
        elif parent_name == '风险评估' and module_name == '综合风险':
            return self.create_risk_matrix_widget()
        elif parent_name == '可行性分析' and module_name == '综合评估':
            return self.create_summary_widget()
        elif parent_name == '高级分析' and module_name == '敏感性分析':
            return self.create_sensitivity_analysis_widget()
        else:
            # 默认文本内容
            text_edit = QTextEdit()
            text_edit.setHtml(f"<h2>{parent_name} - {module_name}</h2>"
                             f"<p>这是{module_name}模块的内容区域。</p>"
                             f"<p>您可以根据需要添加自定义内容和分析工具。</p>")
            return text_edit
            
    def create_basic_info_widget(self):
        """创建基本信息部件"""
        widget = QWidget()
        layout = QFormLayout(widget)
        
        self.project_name = QLineEdit()
        self.project_manager = QLineEdit()
        self.project_department = QComboBox()
        self.project_department.addItems(['研发部', '技术部', '市场部', '产品部', '创新中心'])
        self.project_budget = QDoubleSpinBox()
        self.project_budget.setRange(0, 10000000)
        self.project_budget.setPrefix('¥ ')
        self.project_duration = QSpinBox()
        self.project_duration.setRange(1, 60)
        self.project_duration.setSuffix(' 月')
        self.project_start_date = QLineEdit(datetime.now().strftime('%Y-%m-%d'))
        self.project_description = QTextEdit()
        self.project_description.setMaximumHeight(150)
        
        layout.addRow('项目名称:', self.project_name)
        layout.addRow('项目经理:', self.project_manager)
        layout.addRow('负责部门:', self.project_department)
        layout.addRow('项目预算:', self.project_budget)
        layout.addRow('项目周期:', self.project_duration)
        layout.addRow('开始日期:', self.project_start_date)
        layout.addRow('项目描述:', self.project_description)
        
        save_btn = QPushButton('保存信息')
        save_btn.clicked.connect(self.save_basic_info)
        layout.addRow(save_btn)
        
        return widget
        
    def create_tech_assessment_widget(self):
        """创建技术评估部件"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 技术评估表格
        table = QTableWidget()
        table.setColumnCount(4)
        table.setRowCount(5)
        table.setHorizontalHeaderLabels(['技术领域', '成熟度', '复杂度', '资源需求'])
        
        tech_areas = ['前端技术', '后端技术', '数据库', '安全性', '性能']
        for i, area in enumerate(tech_areas):
            table.setItem(i, 0, QTableWidgetItem(area))
            table.setItem(i, 1, QTableWidgetItem(str(np.random.randint(1, 6))))
            table.setItem(i, 2, QTableWidgetItem(str(np.random.randint(1, 6))))
            table.setItem(i, 3, QTableWidgetItem(str(np.random.randint(1, 6))))
            
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(table)
        
        # 图表区域
        chart_widget = QWidget()
        chart_layout = QVBoxLayout(chart_widget)
        
        # 创建Matplotlib图表
        fig = Figure(figsize=(10, 8))
        canvas = FigureCanvas(fig)
        toolbar = NavigationToolbar(canvas, self)
        
        # 添加子图
        ax1 = fig.add_subplot(221)
        ax2 = fig.add_subplot(222)
        ax3 = fig.add_subplot(212)
        
        # 生成示例数据
        categories = ['前端', '后端', '数据库', '安全', '性能']
        values = [4, 3, 5, 2, 4]
        
        # 柱状图
        ax1.bar(categories, values)
        ax1.set_title('技术领域评分')
        ax1.set_ylim(0, 6)
        
        # 饼图
        maturity = [60, 25, 15]
        labels = ['成熟技术', '中等技术', '新技术']
        ax2.pie(maturity, labels=labels, autopct='%1.1f%%')
        ax2.set_title('技术成熟度分布')
        
        # 折线图 - 技术趋势
        months = ['1月', '2月', '3月', '4月', '5月', '6月']
        frontend_trend = [3.2, 3.5, 3.8, 4.2, 4.5, 4.3]
        backend_trend = [4.1, 4.3, 4.0, 4.5, 4.7, 4.8]
        
        ax3.plot(months, frontend_trend, marker='o', label='前端技术')
        ax3.plot(months, backend_trend, marker='s', label='后端技术')
        ax3.set_title('技术趋势分析')
        ax3.legend()
        ax3.grid(True)
        
        chart_layout.addWidget(toolbar)
        chart_layout.addWidget(canvas)
        layout.addWidget(chart_widget)
        
        return widget
        
    def create_risk_matrix_widget(self):
        """创建风险矩阵部件"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 创建Matplotlib图表
        fig = Figure(figsize=(10, 8))
        canvas = FigureCanvas(fig)
        toolbar = NavigationToolbar(canvas, self)
        
        ax = fig.add_subplot(111)
        
        # 生成随机风险数据
        risks = [
            ('技术依赖', 4, 3),
            ('性能问题', 3, 4),
            ('安全漏洞', 5, 5),
            ('兼容性问题', 2, 3),
            ('技术过时', 3, 2),
            ('资源不足', 4, 4),
            ('时间压力', 5, 3)
        ]
        
        # 绘制风险矩阵
        for risk, impact, prob in risks:
            color = 'red' if impact * prob >= 12 else ('orange' if impact * prob >= 8 else 'green')
            ax.scatter(prob, impact, s=impact*prob*50, alpha=0.6, c=color)
            ax.annotate(risk, (prob, impact), xytext=(5, 5), textcoords='offset points')
        
        # 添加矩阵线
        ax.axhline(y=2.5, color='gray', linestyle='--', alpha=0.7)
        ax.axvline(x=2.5, color='gray', linestyle='--', alpha=0.7)
        
        ax.set_xlabel('发生概率 (1-5)')
        ax.set_ylabel('影响程度 (1-5)')
        ax.set_title('风险矩阵分析')
        ax.set_xlim(0, 6)
        ax.set_ylim(0, 6)
        ax.grid(True)
        
        # 添加图例
        ax.scatter([], [], c='green', alpha=0.6, s=100, label='低风险')
        ax.scatter([], [], c='orange', alpha=0.6, s=100, label='中风险')
        ax.scatter([], [], c='red', alpha=0.6, s=100, label='高风险')
        ax.legend()
        
        layout.addWidget(toolbar)
        layout.addWidget(canvas)
        
        return widget
        
    def create_summary_widget(self):
        """创建综合评估部件"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 可行性评分
        score_widget = QWidget()
        score_layout = QHBoxLayout(score_widget)
        
        scores = {
            '技术可行性': 85,
            '经济可行性': 70,
            '操作可行性': 80,
            '时间可行性': 75,
            '资源可行性': 65
        }
        
        for name, score in scores.items():
            score_label = QLabel(f"{name}\n{score}%")
            score_label.setAlignment(Qt.AlignCenter)
            score_label.setStyleSheet(
                f"border: 2px solid #333; border-radius: 10px; padding: 10px;"
                f"background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #{self.get_color(score)}99, stop:1 #{self.get_color(score)}33);"
                f"font-weight: bold; font-size: 14px; min-width: 80px; min-height: 80px;"
            )
            score_layout.addWidget(score_label)
        
        layout.addWidget(score_widget)
        
        # 雷达图
        fig = Figure(figsize=(10, 8))
        canvas = FigureCanvas(fig)
        toolbar = NavigationToolbar(canvas, self)
        
        ax = fig.add_subplot(111, polar=True)
        
        categories = list(scores.keys())
        values = list(scores.values())
        values += values[:1]  # 闭合雷达图
        N = len(categories)
        
        angles = [n / float(N) * 2 * np.pi for n in range(N)]
        angles += angles[:1]
        
        ax.plot(angles, values, linewidth=2, linestyle='solid')
        ax.fill(angles, values, 'b', alpha=0.1)
        ax.set_thetagrids([a * 180 / np.pi for a in angles[:-1]], categories)
        ax.set_ylim(0, 100)
        ax.set_title('项目可行性雷达图', size=14, y=1.05)
        
        layout.addWidget(toolbar)
        layout.addWidget(canvas)
        
        # 结论文本
        conclusion = QTextEdit()
        conclusion.setHtml(
            "<h3>可行性结论</h3>"
            "<p>综合评估表明，该项目在技术和操作方面具有较高的可行性，"
            "但在资源和预算方面存在一定挑战。</p>"
            "<h4>建议措施:</h4>"
            "<ul>"
            "<li>加强资源规划和调配</li>"
            "<li>制定详细的风险应对策略</li>"
            "<li>分阶段实施，降低初期投入</li>"
            "<li>建立持续监控和评估机制</li>"
            "</ul>"
        )
        layout.addWidget(conclusion)
        
        return widget
        
    def create_sensitivity_analysis_widget(self):
        """创建敏感性分析部件"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 创建Matplotlib图表
        fig = Figure(figsize=(10, 8))
        canvas = FigureCanvas(fig)
        toolbar = NavigationToolbar(canvas, self)
        
        ax = fig.add_subplot(111)
        
        # 生成敏感性分析数据
        factors = ['预算', '时间', '资源', '技术复杂度', '市场需求']
        sensitivities = np.random.random(5) * 100
        
        # 绘制条形图
        bars = ax.bar(factors, sensitivities, color=['#FF9999', '#66B2FF', '#99FF99', '#FFCC99', '#FF99CC'])
        
        # 添加数值标签
        for bar, value in zip(bars, sensitivities):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                   f'{value:.1f}%', ha='center', va='bottom')
        
        ax.set_ylabel('敏感度 (%)')
        ax.set_title('项目因素敏感性分析')
        ax.set_ylim(0, 100)
        
        # 旋转x轴标签以避免重叠
        plt.setp(ax.get_xticklabels(), rotation=45, ha='right')
        
        layout.addWidget(toolbar)
        layout.addWidget(canvas)
        
        # 分析结论
        conclusion = QTextEdit()
        conclusion.setHtml(
            "<h3>敏感性分析结论</h3>"
            "<p>敏感性分析显示，项目的成功最受以下因素影响:</p>"
            "<ul>"
            "<li><b>技术复杂度</b> - 对项目成功影响最大，需重点关注</li>"
            "<li><b>资源可用性</b> - 对项目进度和成本有显著影响</li>"
            "</ul>"
            "<p>建议采取以下措施降低敏感性:</p>"
            "<ol>"
            "<li>制定技术备选方案，降低技术复杂度风险</li>"
            "<li>建立资源缓冲机制，应对资源波动</li>"
            "<li>加强项目监控，及时发现偏差</li>"
            "</ol>"
        )
        layout.addWidget(conclusion)
        
        return widget
        
    def get_color(self, score):
        """根据分数获取颜色"""
        if score >= 80:
            return "00ff00"  # 绿色
        elif score >= 60:
            return "ffff00"  # 黄色
        else:
            return "ff0000"  # 红色
            
    def new_project(self):
        """新建项目"""
        self.current_project = {
            'name': '未命名项目',
            'basic_info': {},
            'analysis_data': {}
        }
        self.status_bar.showMessage('已创建新项目')
        
    def open_project(self):
        """打开项目"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, '打开项目', '', '可行性分析文件 (*.fap);;所有文件 (*)'
        )
        if file_path:
            try:
                with open(file_path, 'r') as f:
                    self.current_project = json.load(f)
                self.status_bar.showMessage(f'已打开项目: {self.current_project["name"]}')
                self.load_project_data()
            except Exception as e:
                QMessageBox.critical(self, '错误', f'打开文件失败: {str(e)}')
                
    def save_project(self):
        """保存项目"""
        if not self.current_project:
            QMessageBox.warning(self, '警告', '没有当前项目可保存')
            return
            
        file_path, _ = QFileDialog.getSaveFileName(
            self, '保存项目', self.current_project.get('name', '未命名项目'), '可行性分析文件 (*.fap);;所有文件 (*)'
        )
        if file_path:
            try:
                with open(file_path, 'w') as f:
                    json.dump(self.current_project, f, indent=4)
                self.status_bar.showMessage(f'项目已保存: {file_path}')
            except Exception as e:
                QMessageBox.critical(self, '错误', f'保存文件失败: {str(e)}')
                
    def import_data(self):
        """导入数据"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, '导入数据', '', 'CSV文件 (*.csv);;Excel文件 (*.xlsx);;所有文件 (*)'
        )
        if file_path:
            try:
                if file_path.endswith('.csv'):
                    data = pd.read_csv(file_path)
                else:
                    data = pd.read_excel(file_path)
                
                # 显示数据预览
                self.show_data_preview(data)
                self.status_bar.showMessage(f'已导入数据: {file_path}')
            except Exception as e:
                QMessageBox.critical(self, '错误', f'导入数据失败: {str(e)}')
                
    def export_data(self):
        """导出数据"""
        if not self.current_project:
            QMessageBox.warning(self, '警告', '没有当前项目可导出')
            return
            
        file_path, _ = QFileDialog.getSaveFileName(
            self, '导出数据', 'project_data', 'CSV文件 (*.csv);;Excel文件 (*.xlsx);;所有文件 (*)'
        )
        if file_path:
            try:
                # 这里只是示例，实际应根据项目数据创建DataFrame
                data = pd.DataFrame({
                    '指标': ['技术可行性', '经济可行性', '操作可行性'],
                    '得分': [85, 70, 80]
                })
                
                if file_path.endswith('.csv'):
                    data.to_csv(file_path, index=False)
                else:
                    data.to_excel(file_path, index=False)
                    
                self.status_bar.showMessage(f'数据已导出: {file_path}')
            except Exception as e:
                QMessageBox.critical(self, '错误', f'导出数据失败: {str(e)}')
                
    def show_data_preview(self, data):
        """显示数据预览"""
        preview_dialog = QMainWindow(self)
        preview_dialog.setWindowTitle('数据预览')
        preview_dialog.setGeometry(200, 200, 800, 600)
        
        central_widget = QWidget()
        layout = QVBoxLayout(central_widget)
        
        # 数据显示表格
        table = QTableWidget()
        table.setRowCount(min(20, len(data)))
        table.setColumnCount(len(data.columns))
        table.setHorizontalHeaderLabels(data.columns)
        
        for i in range(min(20, len(data))):
            for j in range(len(data.columns)):
                table.setItem(i, j, QTableWidgetItem(str(data.iloc[i, j])))
                
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(table)
        
        # 数据信息
        info_text = QTextEdit()
        info_text.setHtml(
            f"<h3>数据概览</h3>"
            f"<p>行数: {len(data)}</p>"
            f"<p>列数: {len(data.columns)}</p>"
            f"<p>列名: {', '.join(data.columns)}</p>"
        )
        info_text.setMaximumHeight(150)
        layout.addWidget(info_text)
        
        # 操作按钮
        button_layout = QHBoxLayout()
        confirm_btn = QPushButton('确认导入')
        confirm_btn.clicked.connect(preview_dialog.close)
        cancel_btn = QPushButton('取消')
        cancel_btn.clicked.connect(preview_dialog.close)
        
        button_layout.addWidget(confirm_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)
        
        preview_dialog.setCentralWidget(central_widget)
        preview_dialog.show()
                
    def load_project_data(self):
        """加载项目数据"""
        # 实现项目数据加载逻辑
        pass
        
    def save_basic_info(self):
        """保存基本信息"""
        if not self.current_project:
            self.current_project = {'name': '未命名项目', 'basic_info': {}}
            
        self.current_project['basic_info'] = {
            'name': self.project_name.text(),
            'manager': self.project_manager.text(),
            'department': self.project_department.currentText(),
            'budget': self.project_budget.value(),
            'duration': self.project_duration.value(),
            'start_date': self.project_start_date.text(),
            'description': self.project_description.toPlainText()
        }
        
        self.status_bar.showMessage('基本信息已保存')
        
    def run_analysis(self):
        """执行分析"""
        if not self.current_project:
            QMessageBox.information(self, '提示', '请先创建或打开一个项目')
            return
            
        # 模拟分析过程
        self.status_bar.showMessage('正在分析...')
        
        # 模拟耗时操作
        QApplication.processEvents()
        
        # 生成分析结果
        self.analysis_data = {
            'technical_feasibility': np.random.randint(60, 95),
            'economic_feasibility': np.random.randint(50, 90),
            'operational_feasibility': np.random.randint(70, 95),
            'schedule_feasibility': np.random.randint(60, 85),
            'risk_level': np.random.randint(1, 6)
        }
        
        self.status_bar.showMessage('分析完成')
        QMessageBox.information(self, '完成', '项目分析已完成')
        
    def generate_report(self):
        """生成报告"""
        if not self.current_project:
            QMessageBox.information(self, '提示', '请先创建或打开一个项目')
            return
            
        # 模拟报告生成过程
        self.status_bar.showMessage('正在生成报告...')
        QApplication.processEvents()
        
        # 模拟耗时操作
        import time
        time.sleep(1)
        
        # 创建报告预览
        report_tab = QWidget()
        layout = QVBoxLayout(report_tab)
        
        report_view = QTextEdit()
        report_view.setHtml(
            "<h1 align='center'>项目技术可行性分析报告</h1>"
            f"<h2>项目名称: {self.current_project.get('name', '未命名项目')}</h2>"
            f"<p>生成日期: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>"
            "<hr>"
            "<h3>1. 执行摘要</h3>"
            "<p>本项目在技术可行性方面表现良好，但在资源和预算方面存在一定挑战。</p>"
            "<h3>2. 详细分析</h3>"
            "<h4>2.1 技术可行性</h4>"
            "<p>技术评估显示，项目所需技术成熟度较高，团队具备相关经验。</p>"
            "<h4>2.2 经济可行性</h4>"
            "<p>预算分析表明，项目投资回报率预计为25%，投资回收期约2.5年。</p>"
            "<h3>3. 风险评估</h3>"
            "<p>识别出主要风险包括技术依赖、资源不足和时间压力。</p>"
            "<h3>4. 结论与建议</h3>"
            "<p>项目总体可行，建议采取分阶段实施策略，并建立风险应对机制。</p>"
        )
        
        layout.addWidget(report_view)
        
        # 导出按钮
        export_btn = QPushButton('导出报告')
        export_btn.clicked.connect(self.export_report)
        layout.addWidget(export_btn)
        
        self.tab_widget.addTab(report_tab, "分析报告")
        self.tab_widget.setCurrentIndex(self.tab_widget.count() - 1)
        
        self.status_bar.showMessage('报告生成完成')
        
    def export_report(self):
        """导出报告"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, '导出报告', 'project_report', 'PDF文件 (*.pdf);;Word文件 (*.docx);;所有文件 (*)'
        )
        if file_path:
            self.status_bar.showMessage(f'报告已导出: {file_path}')
            QMessageBox.information(self, '成功', f'报告已导出到: {file_path}')
        
    def show_charts(self):
        """显示图表"""
        # 创建图表窗口
        chart_tab = QWidget()
        layout = QVBoxLayout(chart_tab)
        
        # 创建Matplotlib图表
        fig = Figure(figsize=(12, 10))
        canvas = FigureCanvas(fig)
        toolbar = NavigationToolbar(canvas, self)
        
        # 添加子图
        ax1 = fig.add_subplot(221)
        ax2 = fig.add_subplot(222)
        ax3 = fig.add_subplot(223)
        ax4 = fig.add_subplot(224)
        
        # 生成示例数据
        categories = ['技术', '经济', '操作', '进度', '资源']
        values = [85, 70, 80, 75, 65]
        
        # 柱状图
        ax1.bar(categories, values, color=['#FF9999', '#66B2FF', '#99FF99', '#FFCC99', '#FF99CC'])
        ax1.set_title('可行性评分')
        ax1.set_ylim(0, 100)
        
        # 饼图
        ax2.pie(values, labels=categories, autopct='%1.1f%%', colors=['#FF9999', '#66B2FF', '#99FF99', '#FFCC99', '#FF99CC'])
        ax2.set_title('可行性分布')
        
        # 折线图
        timeline = ['Q1', 'Q2', 'Q3', 'Q4']
        tech_progress = [20, 45, 70, 90]
        budget_usage = [15, 40, 65, 80]
        
        ax3.plot(timeline, tech_progress, marker='o', label='技术进度')
        ax3.plot(timeline, budget_usage, marker='s', label='预算使用')
        ax3.set_title('项目进度')
        ax3.legend()
        ax3.grid(True)
        
        # 散点图 - 风险分布
        risk_prob = np.random.rand(20) * 5
        risk_impact = np.random.rand(20) * 5
        risk_size = risk_prob * risk_impact * 20
        
        ax4.scatter(risk_prob, risk_impact, s=risk_size, alpha=0.6, c=risk_prob*risk_impact, cmap='Reds')
        ax4.set_xlabel('发生概率')
        ax4.set_ylabel('影响程度')
        ax4.set_title('风险分布')
        ax4.grid(True)
        
        # 添加颜色条
        plt.colorbar(ax4.collections[0], ax=ax4)
        
        layout.addWidget(toolbar)
        layout.addWidget(canvas)
        
        self.tab_widget.addTab(chart_tab, "分析图表")
        self.tab_widget.setCurrentIndex(self.tab_widget.count() - 1)
        
    def show_settings(self):
        """显示设置对话框"""
        settings_dialog = QMainWindow(self)
        settings_dialog.setWindowTitle('系统设置')
        settings_dialog.setGeometry(300, 300, 400, 300)
        
        central_widget = QWidget()
        layout = QFormLayout(central_widget)
        
        # 设置选项
        theme_combo = QComboBox()
        theme_combo.addItems(['默认主题', '深色主题', '浅色主题'])
        layout.addRow('界面主题:', theme_combo)
        
        auto_save = QCheckBox('启用自动保存')
        auto_save.setChecked(True)
        layout.addRow(auto_save)
        
        save_interval = QSpinBox()
        save_interval.setRange(1, 60)
        save_interval.setValue(10)
        save_interval.setSuffix(' 分钟')
        layout.addRow('自动保存间隔:', save_interval)
        
        # 按钮
        button_layout = QHBoxLayout()
        save_btn = QPushButton('保存设置')
        save_btn.clicked.connect(settings_dialog.close)
        cancel_btn = QPushButton('取消')
        cancel_btn.clicked.connect(settings_dialog.close)
        
        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)
        layout.addRow(button_layout)
        
        settings_dialog.setCentralWidget(central_widget)
        settings_dialog.show()
        
    def run_tool_analysis(self):
        """运行工具分析"""
        tool_name = self.tool_combo.currentText()
        param1 = self.param1_input.text()
        param2 = self.param2_input.value()
        param3 = self.param3_input.value()
        
        # 模拟分析结果
        result = f"""执行 {tool_name} 分析完成!
        
参数设置:
- 参数1: {param1}
- 参数2: {param2}
- 参数3: {param3}

分析结果:
- 可行性评分: {np.random.randint(60, 95)}/100
- 风险级别: {np.random.randint(1, 6)}/5
- 推荐指数: {np.random.randint(3, 6)}/5

建议措施:
- 加强技术方案验证
- 制定详细实施计划
- 建立风险应对机制
"""
        
        self.tool_result.setPlainText(result)
        self.status_bar.showMessage(f'{tool_name} 分析完成')
        
    def run_advanced_analysis(self, analysis_type):
        """运行高级分析"""
        if not self.current_project:
            QMessageBox.information(self, '提示', '请先创建或打开一个项目')
            return
            
        self.progress_bar.setVisible(True)
        self.status_bar.showMessage(f'正在执行{analysis_type}...')
        
        # 创建分析线程
        self.analysis_thread = AnalysisThread(analysis_type.lower().replace(' ', '_'), self.analysis_data)
        self.analysis_thread.progress_signal.connect(self.progress_bar.setValue)
        self.analysis_thread.result_signal.connect(self.handle_analysis_result)
        self.analysis_thread.start()
        
    def handle_analysis_result(self, result):
        """处理分析结果"""
        self.progress_bar.setVisible(False)
        
        if "error" in result:
            QMessageBox.critical(self, '错误', f'分析失败: {result["error"]}')
            return
            
        # 显示分析结果
        result_text = "高级分析完成!\n\n"
        
        if "risk_score" in result:
            result_text += f"风险评分: {result['risk_score']}/100\n\n"
            result_text += "高风险因素:\n"
            for risk in result["high_risks"]:
                result_text += f"- {risk['name']} (概率: {risk['probability']}, 影响: {risk['impact']})\n"
                
            result_text += "\n建议措施:\n"
            for rec in result["recommendations"]:
                result_text += f"- {rec}\n"
                
        elif "accuracy" in result:
            result_text += f"预测准确率: {result['accuracy']:.2%}\n\n"
            result_text += "特征重要性:\n"
            for feature, importance in result["feature_importance"].items():
                result_text += f"- {feature}: {importance:.2%}\n"
                
            result_text += f"\n项目可行性预测: {result['prediction']}\n"
            
        elif "sensitivity_analysis" in result:
            result_text += "敏感性分析结果:\n"
            for factor, sensitivity in result["sensitivity_analysis"].items():
                result_text += f"- {factor}: {sensitivity:.1f}%\n"
                
            result_text += f"\n关键因素: {', '.join(result['critical_factors'])}\n"
            
        self.advanced_result.setPlainText(result_text)
        self.status_bar.showMessage('高级分析完成')
        
    def add_data_row(self):
        """添加数据行"""
        row_count = self.data_table.rowCount()
        self.data_table.insertRow(row_count)
        
    def edit_data(self):
        """编辑数据"""
        current_row = self.data_table.currentRow()
        if current_row >= 0:
            QMessageBox.information(self, '编辑', f'编辑第 {current_row + 1} 行数据')
        else:
            QMessageBox.warning(self, '警告', '请先选择一行数据')
            
    def delete_data(self):
        """删除数据"""
        current_row = self.data_table.currentRow()
        if current_row >= 0:
            self.data_table.removeRow(current_row)
        else:
            QMessageBox.warning(self, '警告', '请先选择一行数据')
            
    def import_csv(self):
        """导入CSV数据"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, '导入CSV', '', 'CSV文件 (*.csv);;所有文件 (*)'
        )
        if file_path:
            try:
                data = pd.read_csv(file_path)
                # 这里可以添加将数据加载到表格的逻辑
                QMessageBox.information(self, '成功', f'已导入 {len(data)} 行数据')
            except Exception as e:
                QMessageBox.critical(self, '错误', f'导入CSV失败: {str(e)}')
            
    def filter_data(self):
        """筛选数据"""
        QMessageBox.information(self, '筛选', '数据筛选功能')
            
    def close_tab(self, index):
        """关闭选项卡"""
        self.tab_widget.removeTab(index)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # 设置应用程序样式
    app.setStyle('Fusion')
    
    # 创建并显示主窗口
    window = AdvancedProjectAnalysisSystem()
    window.show()
    
    sys.exit(app.exec_())