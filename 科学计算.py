import sys
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from matplotlib import cm
from mpl_toolkits.mplot3d import Axes3D
from scipy import integrate, optimize, interpolate, linalg, fft, signal, special, stats
import sympy as sp
from sympy import symbols, diff, integrate as sympy_integrate, solve, simplify, lambdify
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QTabWidget, QTextEdit, QLineEdit, QPushButton, QLabel, 
                             QComboBox, QGroupBox, QDoubleSpinBox, QSpinBox, QSplitter,
                             QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
                             QFileDialog, QAction, QMenu, QToolBar, QStatusBar, QDockWidget,
                             QListWidget, QListWidgetItem, QCheckBox, QScrollArea, QFrame,
                             QProgressBar, QSlider, QDial, QRadioButton, QButtonGroup,QInputDialog,
                             QGridLayout, QSizePolicy, QTreeWidget, QTreeWidgetItem)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QSize
from PyQt5.QtGui import QFont, QIcon, QPalette, QColor, QPixmap, QImage
import pandas as pd
import pickle
import time
import numba
from numba import jit
import warnings
warnings.filterwarnings('ignore')

class WorkerThread(QThread):
    """工作线程，用于执行耗时的计算任务"""
    progress = pyqtSignal(int)
    result = pyqtSignal(object)
    finished = pyqtSignal()
    error = pyqtSignal(str)
    
    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs
        
    def run(self):
        try:
            # 如果函数支持进度回调，添加进度回调参数
            if hasattr(self.func, '__code__') and 'progress_callback' in self.func.__code__.co_varnames:
                result = self.func(*self.args, progress_callback=self.progress.emit, **self.kwargs)
            else:
                result = self.func(*self.args, **self.kwargs)
            self.result.emit(result)
        except Exception as e:
            self.error.emit(str(e))
        finally:
            self.finished.emit()

class ScientificCalculator(QWidget):
    """增强版科学计算器"""
    def __init__(self):
        super().__init__()
        self.variables = {}
        self.init_ui()
        
    def init_ui(self):
        main_layout = QHBoxLayout()
        
        # 左侧计算器面板
        calc_widget = QWidget()
        calc_layout = QVBoxLayout()
        
        # 显示区域
        self.display = QLineEdit()
        self.display.setReadOnly(True)
        self.display.setAlignment(Qt.AlignRight)
        self.display.setFont(QFont("Monospace", 16))
        self.display.setStyleSheet("background-color: #f0f0f0; border: 1px solid #ccc;")
        calc_layout.addWidget(self.display)
        
        # 输入区域
        self.input = QLineEdit()
        self.input.setFont(QFont("Monospace", 12))
        self.input.returnPressed.connect(self.calculate)
        calc_layout.addWidget(self.input)
        
        # 按钮网格
        buttons_grid = QGridLayout()
        
        # 数字按钮
        buttons = [
            ('7', 0, 0), ('8', 0, 1), ('9', 0, 2), ('/', 0, 3), ('C', 0, 4),
            ('4', 1, 0), ('5', 1, 1), ('6', 1, 2), ('*', 1, 3), ('(', 1, 4),
            ('1', 2, 0), ('2', 2, 1), ('3', 2, 2), ('-', 2, 3), (')', 2, 4),
            ('0', 3, 0), ('.', 3, 1), ('=', 3, 2), ('+', 3, 3), ('<-', 3, 4),
        ]
        
        for btn_text, row, col in buttons:
            btn = QPushButton(btn_text)
            btn.clicked.connect(self.on_button_click)
            btn.setFont(QFont("Arial", 12))
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            buttons_grid.addWidget(btn, row, col)
        
        calc_layout.addLayout(buttons_grid)
        
        # 函数按钮
        func_buttons = QHBoxLayout()
        functions = ['sin', 'cos', 'tan', 'log', 'exp', 'sqrt', 'pi', 'e']
        
        for func in functions:
            btn = QPushButton(func)
            btn.clicked.connect(lambda checked, f=func: self.input.insert(f"{f}("))
            btn.setFont(QFont("Arial", 10))
            func_buttons.addWidget(btn)
        
        calc_layout.addLayout(func_buttons)
        
        # 计算按钮
        self.calc_btn = QPushButton("计算")
        self.calc_btn.clicked.connect(self.calculate)
        self.calc_btn.setFont(QFont("Arial", 12))
        self.calc_btn.setStyleSheet("background-color: #4CAF50; color: white;")
        calc_layout.addWidget(self.calc_btn)
        
        calc_widget.setLayout(calc_layout)
        calc_widget.setMaximumWidth(400)
        
        # 右侧变量和历史面板
        right_widget = QWidget()
        right_layout = QVBoxLayout()
        
        # 变量管理
        var_group = QGroupBox("变量管理")
        var_layout = QVBoxLayout()
        
        self.var_table = QTableWidget()
        self.var_table.setColumnCount(2)
        self.var_table.setHorizontalHeaderLabels(["变量名", "值"])
        self.var_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        var_layout.addWidget(self.var_table)
        
        var_btn_layout = QHBoxLayout()
        self.add_var_btn = QPushButton("添加变量")
        self.add_var_btn.clicked.connect(self.add_variable)
        var_btn_layout.addWidget(self.add_var_btn)
        
        self.del_var_btn = QPushButton("删除变量")
        self.del_var_btn.clicked.connect(self.delete_variable)
        var_btn_layout.addWidget(self.del_var_btn)
        
        var_layout.addLayout(var_btn_layout)
        var_group.setLayout(var_layout)
        right_layout.addWidget(var_group)
        
        # 结果历史
        history_group = QGroupBox("历史记录")
        history_layout = QVBoxLayout()
        
        self.history = QListWidget()
        history_layout.addWidget(self.history)
        
        clear_btn = QPushButton("清除历史")
        clear_btn.clicked.connect(self.history.clear)
        history_layout.addWidget(clear_btn)
        
        history_group.setLayout(history_layout)
        right_layout.addWidget(history_group)
        
        right_widget.setLayout(right_layout)
        
        # 添加到主布局
        main_layout.addWidget(calc_widget)
        main_layout.addWidget(right_widget)
        self.setLayout(main_layout)
        
        # 初始化变量表
        self.update_variable_table()
        
    def on_button_click(self):
        button = self.sender()
        text = button.text()
        
        if text == '=':
            self.calculate()
        elif text == 'C':
            self.input.clear()
        elif text == '<-':
            self.input.backspace()
        else:
            self.input.insert(text)
            
    def calculate(self):
        try:
            expr = self.input.text()
            
            # 安全地计算表达式
            safe_dict = {
                'sin': np.sin, 'cos': np.cos, 'tan': np.tan,
                'asin': np.arcsin, 'acos': np.arccos, 'atan': np.arctan,
                'sinh': np.sinh, 'cosh': np.cosh, 'tanh': np.tanh,
                'exp': np.exp, 'log': np.log, 'log10': np.log10,
                'sqrt': np.sqrt, 'abs': np.abs, 'pi': np.pi, 'e': np.e
            }
            
            # 添加用户定义的变量
            safe_dict.update(self.variables)
            
            # 使用更安全的eval方法
            result = eval(expr, {"__builtins__": {}}, safe_dict)
            
            self.display.setText(str(result))
            self.history.addItem(f"{expr} = {result}")
            self.input.clear()
            
            # 自动保存结果到变量ans
            self.variables['ans'] = result
            self.update_variable_table()
            
        except Exception as e:
            self.display.setText(f"错误: {str(e)}")
            
    def add_variable(self):
        var_name, ok = QInputDialog.getText(self, "添加变量", "变量名:")
        if ok and var_name:
            var_value, ok = QInputDialog.getDouble(self, "添加变量", "值:")
            if ok:
                self.variables[var_name] = var_value
                self.update_variable_table()
                
    def delete_variable(self):
        current_row = self.var_table.currentRow()
        if current_row >= 0:
            var_name = self.var_table.item(current_row, 0).text()
            if var_name in self.variables:
                del self.variables[var_name]
                self.update_variable_table()
                
    def update_variable_table(self):
        self.var_table.setRowCount(len(self.variables))
        for i, (name, value) in enumerate(self.variables.items()):
            self.var_table.setItem(i, 0, QTableWidgetItem(name))
            self.var_table.setItem(i, 1, QTableWidgetItem(str(value)))


class FunctionPlotter(QWidget):
    """增强版函数绘图工具"""
    def __init__(self):
        super().__init__()
        self.plots = []  # 存储多个绘图配置
        self.init_ui()
        
    def init_ui(self):
        layout = QHBoxLayout()
        
        # 左侧控制面板
        control_panel = QWidget()
        control_layout = QVBoxLayout()
        
        # 绘图列表
        plot_list_group = QGroupBox("绘图列表")
        plot_list_layout = QVBoxLayout()
        
        self.plot_list = QListWidget()
        self.plot_list.currentRowChanged.connect(self.on_plot_selected)
        plot_list_layout.addWidget(self.plot_list)
        
        plot_buttons = QHBoxLayout()
        self.add_plot_btn = QPushButton("添加绘图")
        self.add_plot_btn.clicked.connect(self.add_plot)
        plot_buttons.addWidget(self.add_plot_btn)
        
        self.remove_plot_btn = QPushButton("删除绘图")
        self.remove_plot_btn.clicked.connect(self.remove_plot)
        plot_buttons.addWidget(self.remove_plot_btn)
        
        plot_list_layout.addLayout(plot_buttons)
        plot_list_group.setLayout(plot_list_layout)
        control_layout.addWidget(plot_list_group)
        
        # 函数设置
        func_group = QGroupBox("函数设置")
        func_layout = QVBoxLayout()
        
        func_layout.addWidget(QLabel("函数表达式:"))
        self.func_input = QLineEdit("sin(x)")
        func_layout.addWidget(self.func_input)
        
        # 范围设置
        range_layout = QHBoxLayout()
        range_layout.addWidget(QLabel("从"))
        self.xmin = QDoubleSpinBox()
        self.xmin.setRange(-10000, 10000)
        self.xmin.setValue(0)
        range_layout.addWidget(self.xmin)
        
        range_layout.addWidget(QLabel("到"))
        self.xmax = QDoubleSpinBox()
        self.xmax.setRange(-10000, 10000)
        self.xmax.setValue(10)
        range_layout.addWidget(self.xmax)
        
        func_layout.addLayout(range_layout)
        
        # 参数设置
        param_layout = QHBoxLayout()
        param_layout.addWidget(QLabel("参数:"))
        self.param_input = QLineEdit("")
        self.param_input.setPlaceholderText("例如: a=1, b=2")
        param_layout.addWidget(self.param_input)
        func_layout.addLayout(param_layout)
        
        func_group.setLayout(func_layout)
        control_layout.addWidget(func_group)
        
        # 绘图选项
        options_group = QGroupBox("绘图选项")
        options_layout = QGridLayout()
        
        options_layout.addWidget(QLabel("点数:"), 0, 0)
        self.points = QSpinBox()
        self.points.setRange(10, 100000)
        self.points.setValue(1000)
        options_layout.addWidget(self.points, 0, 1)
        
        options_layout.addWidget(QLabel("颜色:"), 1, 0)
        self.color = QComboBox()
        self.color.addItems(["blue", "red", "green", "black", "purple", "orange", "brown", "pink", "gray"])
        options_layout.addWidget(self.color, 1, 1)
        
        options_layout.addWidget(QLabel("线型:"), 2, 0)
        self.linestyle = QComboBox()
        self.linestyle.addItems(["-", "--", "-.", ":", "None"])
        options_layout.addWidget(self.linestyle, 2, 1)
        
        options_layout.addWidget(QLabel("线宽:"), 3, 0)
        self.linewidth = QDoubleSpinBox()
        self.linewidth.setRange(0.1, 10)
        self.linewidth.setValue(1.5)
        options_layout.addWidget(self.linewidth, 3, 1)
        
        options_layout.addWidget(QLabel("标记:"), 4, 0)
        self.marker = QComboBox()
        self.marker.addItems(["None", ".", ",", "o", "v", "^", "<", ">", "s", "p", "*", "+", "x"])
        options_layout.addWidget(self.marker, 4, 1)
        
        options_group.setLayout(options_layout)
        control_layout.addWidget(options_group)
        
        # 3D绘图选项
        self.three_d_check = QCheckBox("3D绘图")
        self.three_d_check.stateChanged.connect(self.toggle_3d_options)
        control_layout.addWidget(self.three_d_check)
        
        # 3D选项面板
        self.three_d_panel = QWidget()
        three_d_layout = QVBoxLayout()
        
        three_d_range = QHBoxLayout()
        three_d_range.addWidget(QLabel("Y从"))
        self.ymin = QDoubleSpinBox()
        self.ymin.setRange(-10000, 10000)
        self.ymin.setValue(0)
        three_d_range.addWidget(self.ymin)
        
        three_d_range.addWidget(QLabel("到"))
        self.ymax = QDoubleSpinBox()
        self.ymax.setRange(-10000, 10000)
        self.ymax.setValue(10)
        three_d_range.addWidget(self.ymax)
        
        three_d_layout.addLayout(three_d_range)
        
        three_d_layout.addWidget(QLabel("3D函数表达式 (使用x和y):"))
        self.func_3d_input = QLineEdit("sin(sqrt(x**2 + y**2))")
        three_d_layout.addWidget(self.func_3d_input)
        
        three_d_layout.addWidget(QLabel("颜色映射:"))
        self.colormap = QComboBox()
        self.colormap.addItems(["viridis", "plasma", "inferno", "magma", "coolwarm", "jet"])
        three_d_layout.addWidget(self.colormap)
        
        self.three_d_panel.setLayout(three_d_layout)
        self.three_d_panel.setVisible(False)
        control_layout.addWidget(self.three_d_panel)
        
        # 绘图按钮
        btn_layout = QHBoxLayout()
        self.update_btn = QPushButton("更新绘图")
        self.update_btn.clicked.connect(self.update_plot)
        btn_layout.addWidget(self.update_btn)
        
        self.plot_btn = QPushButton("绘制所有")
        self.plot_btn.clicked.connect(self.plot_all)
        btn_layout.addWidget(self.plot_btn)
        
        control_layout.addLayout(btn_layout)
        
        control_layout.addStretch()
        control_panel.setLayout(control_layout)
        control_panel.setMaximumWidth(350)
        
        # 右侧绘图区域
        self.figure = Figure(figsize=(10, 8))
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)
        
        plot_layout = QVBoxLayout()
        plot_layout.addWidget(self.toolbar)
        plot_layout.addWidget(self.canvas)
        
        plot_widget = QWidget()
        plot_widget.setLayout(plot_layout)
        
        # 添加到主布局
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(control_panel)
        splitter.addWidget(plot_widget)
        splitter.setSizes([300, 700])
        
        layout.addWidget(splitter)
        self.setLayout(layout)
        
        # 添加初始绘图
        self.add_plot()
        
    def toggle_3d_options(self, state):
        self.three_d_panel.setVisible(state == Qt.Checked)
        
    def add_plot(self):
        plot_id = f"绘图 {len(self.plots) + 1}"
        self.plots.append({
            'id': plot_id,
            'function': 'sin(x)',
            'xmin': 0,
            'xmax': 10,
            'params': '',
            'points': 1000,
            'color': 'blue',
            'linestyle': '-',
            'linewidth': 1.5,
            'marker': 'None',
            'is_3d': False,
            'func_3d': 'sin(sqrt(x**2 + y**2))',
            'ymin': 0,
            'ymax': 10,
            'colormap': 'viridis'
        })
        
        self.plot_list.addItem(plot_id)
        self.plot_list.setCurrentRow(len(self.plots) - 1)
        
    def remove_plot(self):
        current_row = self.plot_list.currentRow()
        if current_row >= 0:
            self.plots.pop(current_row)
            self.plot_list.takeItem(current_row)
            
    def on_plot_selected(self, row):
        if row >= 0 and row < len(self.plots):
            plot = self.plots[row]
            self.func_input.setText(plot['function'])
            self.xmin.setValue(plot['xmin'])
            self.xmax.setValue(plot['xmax'])
            self.param_input.setText(plot['params'])
            self.points.setValue(plot['points'])
            self.color.setCurrentText(plot['color'])
            self.linestyle.setCurrentText(plot['linestyle'])
            self.linewidth.setValue(plot['linewidth'])
            self.marker.setCurrentText(plot['marker'])
            self.three_d_check.setChecked(plot['is_3d'])
            self.func_3d_input.setText(plot['func_3d'])
            self.ymin.setValue(plot['ymin'])
            self.ymax.setValue(plot['ymax'])
            self.colormap.setCurrentText(plot['colormap'])
            
    def update_plot(self):
        current_row = self.plot_list.currentRow()
        if current_row >= 0:
            plot = self.plots[current_row]
            plot['function'] = self.func_input.text()
            plot['xmin'] = self.xmin.value()
            plot['xmax'] = self.xmax.value()
            plot['params'] = self.param_input.text()
            plot['points'] = self.points.value()
            plot['color'] = self.color.currentText()
            plot['linestyle'] = self.linestyle.currentText()
            plot['linewidth'] = self.linewidth.value()
            plot['marker'] = self.marker.currentText()
            plot['is_3d'] = self.three_d_check.isChecked()
            plot['func_3d'] = self.func_3d_input.text()
            plot['ymin'] = self.ymin.value()
            plot['ymax'] = self.ymax.value()
            plot['colormap'] = self.colormap.currentText()
            
            self.plot_current()
            
    def plot_current(self):
        current_row = self.plot_list.currentRow()
        if current_row >= 0:
            self.plot_function(self.plots[current_row])
            
    def plot_all(self):
        self.figure.clear()
        
        if any(plot['is_3d'] for plot in self.plots):
            # 如果有3D图，单独绘制
            self.plot_3d_functions()
        else:
            # 绘制2D图
            ax = self.figure.add_subplot(111)
            
            for plot in self.plots:
                self.plot_single_function(ax, plot)
                
            ax.grid(True)
            ax.legend([plot['id'] for plot in self.plots])
            
        self.canvas.draw()
        
    def plot_function(self, plot):
        self.figure.clear()
        
        if plot['is_3d']:
            self.plot_single_3d_function(plot)
        else:
            ax = self.figure.add_subplot(111)
            self.plot_single_function(ax, plot)
            ax.grid(True)
            ax.legend([plot['id']])
            
        self.canvas.draw()
        
    def plot_single_function(self, ax, plot):
        try:
            # 解析参数
            params = {}
            if plot['params']:
                for param in plot['params'].split(','):
                    if '=' in param:
                        key, value = param.split('=')
                        params[key.strip()] = float(value.strip())
            
            # 创建x值数组
            x = np.linspace(plot['xmin'], plot['xmax'], plot['points'])
            
            # 定义函数
            func_str = plot['function']
            func = eval(f"lambda x, **kwargs: {func_str}", {"__builtins__": None}, 
                       {"sin": np.sin, "cos": np.cos, "tan": np.tan,
                        "exp": np.exp, "log": np.log, "sqrt": np.sqrt,
                        "pi": np.pi, "e": np.e, **params})
            
            # 计算y值
            y = func(x)
            
            # 绘图
            ax.plot(x, y, 
                   color=plot['color'],
                   linestyle=plot['linestyle'],
                   linewidth=plot['linewidth'],
                   marker=plot['marker'],
                   label=plot['id'])
            
            ax.set_xlabel('x')
            ax.set_ylabel('f(x)')
            ax.set_title('函数图')
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"绘图时发生错误: {str(e)}")
            
    def plot_3d_functions(self):
        try:
            ax = self.figure.add_subplot(111, projection='3d')
            
            for plot in self.plots:
                if plot['is_3d']:
                    # 创建x和y网格
                    x = np.linspace(plot['xmin'], plot['xmax'], plot['points'])
                    y = np.linspace(plot['ymin'], plot['ymax'], plot['points'])
                    X, Y = np.meshgrid(x, y)
                    
                    # 解析参数
                    params = {}
                    if plot['params']:
                        for param in plot['params'].split(','):
                            if '=' in param:
                                key, value = param.split('=')
                                params[key.strip()] = float(value.strip())
                    
                    # 定义函数
                    func_str = plot['func_3d']
                    func = eval(f"lambda x, y, **kwargs: {func_str}", {"__builtins__": None}, 
                               {"sin": np.sin, "cos": np.cos, "tan": np.tan,
                                "exp": np.exp, "log": np.log, "sqrt": np.sqrt,
                                "pi": np.pi, "e": np.e, **params})
                    
                    # 计算z值
                    Z = func(X, Y)
                    
                    # 绘制3D曲面
                    surf = ax.plot_surface(X, Y, Z, cmap=plot['colormap'], alpha=0.8)
                    self.figure.colorbar(surf, ax=ax, shrink=0.5, aspect=5)
            
            ax.set_xlabel('X')
            ax.set_ylabel('Y')
            ax.set_zlabel('Z')
            ax.set_title('3D函数图')
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"3D绘图时发生错误: {str(e)}")


class DataAnalysisTool(QWidget):
    """增强版数据分析工具"""
    def __init__(self):
        super().__init__()
        self.data = None
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 工具栏
        toolbar = QHBoxLayout()
        
        self.load_btn = QPushButton("加载数据")
        self.load_btn.clicked.connect(self.load_data)
        toolbar.addWidget(self.load_btn)
        
        self.analyze_btn = QPushButton("分析数据")
        self.analyze_btn.clicked.connect(self.analyze_data)
        toolbar.addWidget(self.analyze_btn)
        
        self.visualize_btn = QPushButton("可视化")
        self.visualize_btn.clicked.connect(self.visualize_data)
        toolbar.addWidget(self.visualize_btn)
        
        self.export_btn = QPushButton("导出结果")
        self.export_btn.clicked.connect(self.export_results)
        toolbar.addWidget(self.export_btn)
        
        self.clear_btn = QPushButton("清除数据")
        self.clear_btn.clicked.connect(self.clear_data)
        toolbar.addWidget(self.clear_btn)
        
        layout.addLayout(toolbar)
        
        # 主内容区域
        content_splitter = QSplitter(Qt.Horizontal)
        
        # 左侧数据面板
        data_widget = QWidget()
        data_layout = QVBoxLayout()
        
        # 数据显示表格
        self.table = QTableWidget()
        data_layout.addWidget(self.table)
        
        # 数据信息
        info_group = QGroupBox("数据信息")
        info_layout = QVBoxLayout()
        
        self.info_text = QTextEdit()
        self.info_text.setReadOnly(True)
        self.info_text.setMaximumHeight(150)
        info_layout.addWidget(self.info_text)
        
        info_group.setLayout(info_layout)
        data_layout.addWidget(info_group)
        
        data_widget.setLayout(data_layout)
        
        # 右侧分析面板
        analysis_widget = QWidget()
        analysis_layout = QVBoxLayout()
        
        # 分析选项
        options_group = QGroupBox("分析选项")
        options_layout = QVBoxLayout()
        
        # 统计检验选项
        stats_test_layout = QHBoxLayout()
        stats_test_layout.addWidget(QLabel("统计检验:"))
        self.stats_test = QComboBox()
        self.stats_test.addItems(["t检验", "方差分析", "卡方检验", "相关分析", "回归分析"])
        stats_test_layout.addWidget(self.stats_test)
        options_layout.addLayout(stats_test_layout)
        
        # 分组变量选择
        group_layout = QHBoxLayout()
        group_layout.addWidget(QLabel("分组变量:"))
        self.group_var = QComboBox()
        group_layout.addWidget(self.group_var)
        options_layout.addLayout(group_layout)
        
        # 分析变量选择
        analysis_var_layout = QHBoxLayout()
        analysis_var_layout.addWidget(QLabel("分析变量:"))
        self.analysis_var = QComboBox()
        analysis_var_layout.addWidget(self.analysis_var)
        options_layout.addLayout(analysis_var_layout)
        
        options_group.setLayout(options_layout)
        analysis_layout.addWidget(options_group)
        
        # 分析结果显示
        results_group = QGroupBox("分析结果")
        results_layout = QVBoxLayout()
        
        self.results = QTextEdit()
        self.results.setReadOnly(True)
        results_layout.addWidget(self.results)
        
        results_group.setLayout(results_layout)
        analysis_layout.addWidget(results_group)
        
        analysis_widget.setLayout(analysis_layout)
        
        # 添加到分割器
        content_splitter.addWidget(data_widget)
        content_splitter.addWidget(analysis_widget)
        content_splitter.setSizes([400, 600])
        
        layout.addWidget(content_splitter)
        self.setLayout(layout)
        
    def load_data(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "打开数据文件", "", 
            "CSV文件 (*.csv);;Excel文件 (*.xlsx *.xls);;文本文件 (*.txt);;所有文件 (*)")
        
        if file_path:
            try:
                if file_path.endswith('.csv'):
                    self.data = pd.read_csv(file_path)
                elif file_path.endswith(('.xlsx', '.xls')):
                    self.data = pd.read_excel(file_path)
                else:
                    self.data = pd.read_table(file_path)
                    
                self.display_data()
                self.update_variable_lists()
                
            except Exception as e:
                QMessageBox.critical(self, "错误", f"无法加载文件: {str(e)}")
    
    def display_data(self):
        if self.data is not None:
            self.table.setRowCount(self.data.shape[0])
            self.table.setColumnCount(self.data.shape[1])
            self.table.setHorizontalHeaderLabels(self.data.columns)
            
            for i in range(self.data.shape[0]):
                for j in range(self.data.shape[1]):
                    self.table.setItem(i, j, QTableWidgetItem(str(self.data.iat[i, j])))
            
            self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            
            # 更新数据信息
            info_text = f"数据形状: {self.data.shape[0]} 行 × {self.data.shape[1]} 列\n"
            info_text += f"数据类型:\n{self.data.dtypes.to_string()}\n\n"
            info_text += "缺失值统计:\n"
            for col in self.data.columns:
                missing = self.data[col].isnull().sum()
                if missing > 0:
                    info_text += f"{col}: {missing} 个缺失值\n"
                    
            self.info_text.setText(info_text)
    
    def update_variable_lists(self):
        self.group_var.clear()
        self.analysis_var.clear()
        
        if self.data is not None:
            for col in self.data.columns:
                self.group_var.addItem(col)
                self.analysis_var.addItem(col)
    
    def analyze_data(self):
        if self.data is None:
            QMessageBox.warning(self, "警告", "没有数据可分析")
            return
        
        try:
            test_type = self.stats_test.currentText()
            group_col = self.group_var.currentText()
            analysis_col = self.analysis_var.currentText()
            
            results_text = f"{test_type} 分析结果:\n\n"
            
            if test_type == "t检验":
                # 独立样本t检验
                groups = self.data[group_col].unique()
                if len(groups) != 2:
                    results_text += "分组变量必须恰好有两个水平才能进行t检验。\n"
                else:
                    group1 = self.data[self.data[group_col] == groups[0]][analysis_col]
                    group2 = self.data[self.data[group_col] == groups[1]][analysis_col]
                    
                    t_stat, p_value = stats.ttest_ind(group1, group2, nan_policy='omit')
                    
                    results_text += f"组1 ({groups[0]}): n={len(group1)}, 均值={group1.mean():.3f}, 标准差={group1.std():.3f}\n"
                    results_text += f"组2 ({groups[1]}): n={len(group2)}, 均值={group2.mean():.3f}, 标准差={group2.std():.3f}\n"
                    results_text += f"t统计量: {t_stat:.3f}, p值: {p_value:.3f}\n"
                    
                    if p_value < 0.05:
                        results_text += "结果显著 (p < 0.05)，拒绝零假设。\n"
                    else:
                        results_text += "结果不显著 (p >= 0.05)，不能拒绝零假设。\n"
                        
            elif test_type == "相关分析":
                # 计算相关性
                numeric_cols = self.data.select_dtypes(include=[np.number]).columns
                correlation_matrix = self.data[numeric_cols].corr()
                
                results_text += "相关性矩阵:\n"
                results_text += correlation_matrix.to_string()
                results_text += "\n\n"
                
                # 特定变量的相关性
                if analysis_col in numeric_cols:
                    correlations = self.data.corr()[analysis_col].sort_values(key=abs, ascending=False)
                    results_text += f"与 '{analysis_col}' 最相关的变量:\n"
                    for var, corr in correlations.items():
                        if var != analysis_col:
                            results_text += f"{var}: {corr:.3f}\n"
            
            elif test_type == "回归分析":
                # 简单线性回归
                from sklearn.linear_model import LinearRegression
                from sklearn.metrics import r2_score
                
                X = self.data[[group_col]]
                y = self.data[analysis_col]
                
                # 删除缺失值
                mask = ~(X.isnull().any(axis=1) | y.isnull())
                X = X[mask]
                y = y[mask]
                
                model = LinearRegression()
                model.fit(X, y)
                
                y_pred = model.predict(X)
                r2 = r2_score(y, y_pred)
                
                results_text += f"回归模型: {analysis_col} ~ {group_col}\n"
                results_text += f"截距: {model.intercept_:.3f}\n"
                results_text += f"斜率: {model.coef_[0]:.3f}\n"
                results_text += f"R²: {r2:.3f}\n"
            
            self.results.setText(results_text)
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"分析数据时发生错误: {str(e)}")
    
    def visualize_data(self):
        if self.data is None:
            QMessageBox.warning(self, "警告", "没有数据可可视化")
            return
        
        try:
            # 创建图形窗口
            fig = Figure(figsize=(10, 8))
            canvas = FigureCanvas(fig)
            
            # 根据数据类型选择可视化方式
            numeric_cols = self.data.select_dtypes(include=[np.number]).columns
            
            if len(numeric_cols) >= 2:
                # 散点图矩阵
                from pandas.plotting import scatter_matrix
                
                ax = fig.add_subplot(111)
                scatter_matrix(self.data[numeric_cols], ax=ax)
                fig.tight_layout()
                
            elif len(numeric_cols) == 1:
                # 直方图
                ax = fig.add_subplot(111)
                self.data[numeric_cols[0]].hist(ax=ax)
                ax.set_title(f"{numeric_cols[0]} 的分布")
                
            # 显示图形窗口
            graph_window = QMainWindow()
            graph_window.setWindowTitle("数据可视化")
            graph_window.setCentralWidget(canvas)
            graph_window.resize(1000, 800)
            graph_window.show()
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"可视化数据时发生错误: {str(e)}")
    
    def export_results(self):
        if self.results.toPlainText().strip():
            file_path, _ = QFileDialog.getSaveFileName(
                self, "导出结果", "", "文本文件 (*.txt);;所有文件 (*)")
            
            if file_path:
                try:
                    with open(file_path, 'w') as f:
                        f.write(self.results.toPlainText())
                    QMessageBox.information(self, "成功", "结果已导出")
                except Exception as e:
                    QMessageBox.critical(self, "错误", f"导出结果时发生错误: {str(e)}")
    
    def clear_data(self):
        self.data = None
        self.table.setRowCount(0)
        self.table.setColumnCount(0)
        self.info_text.clear()
        self.results.clear()
        self.group_var.clear()
        self.analysis_var.clear()


class EquationSolver(QWidget):
    """增强版方程求解工具"""
    def __init__(self):
        super().__init__()
        self.equations = []  # 存储多个方程
        self.solutions = {}  # 存储解决方案
        self.init_ui()
        
    def init_ui(self):
        layout = QHBoxLayout()
        
        # 左侧方程管理面板
        left_panel = QWidget()
        left_layout = QVBoxLayout()
        
        # 方程列表
        eq_list_group = QGroupBox("方程列表")
        eq_list_layout = QVBoxLayout()
        
        self.eq_list = QListWidget()
        self.eq_list.currentRowChanged.connect(self.on_equation_selected)
        eq_list_layout.addWidget(self.eq_list)
        
        eq_buttons = QHBoxLayout()
        self.add_eq_btn = QPushButton("添加方程")
        self.add_eq_btn.clicked.connect(self.add_equation)
        eq_buttons.addWidget(self.add_eq_btn)
        
        self.remove_eq_btn = QPushButton("删除方程")
        self.remove_eq_btn.clicked.connect(self.remove_equation)
        eq_buttons.addWidget(self.remove_eq_btn)
        
        eq_list_layout.addLayout(eq_buttons)
        eq_list_group.setLayout(eq_list_layout)
        left_layout.addWidget(eq_list_group)
        
        # 方程编辑
        eq_edit_group = QGroupBox("方程编辑")
        eq_edit_layout = QVBoxLayout()
        
        eq_edit_layout.addWidget(QLabel("方程表达式:"))
        self.eq_input = QTextEdit()
        self.eq_input.setMaximumHeight(100)
        eq_edit_layout.addWidget(self.eq_input)
        
        # 变量定义
        var_layout = QHBoxLayout()
        var_layout.addWidget(QLabel("变量:"))
        self.var_input = QLineEdit()
        self.var_input.setPlaceholderText("例如: x, y, z")
        var_layout.addWidget(self.var_input)
        eq_edit_layout.addLayout(var_layout)
        
        # 方程类型
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("方程类型:"))
        self.eq_type = QComboBox()
        self.eq_type.addItems(["代数方程", "微分方程", "方程组"])
        type_layout.addWidget(self.eq_type)
        eq_edit_layout.addLayout(type_layout)
        
        # 更新按钮
        self.update_eq_btn = QPushButton("更新方程")
        self.update_eq_btn.clicked.connect(self.update_equation)
        eq_edit_layout.addWidget(self.update_eq_btn)
        
        eq_edit_group.setLayout(eq_edit_layout)
        left_layout.addWidget(eq_edit_group)
        
        left_panel.setLayout(left_layout)
        left_panel.setMaximumWidth(400)
        
        # 右侧求解面板
        right_panel = QWidget()
        right_layout = QVBoxLayout()
        
        # 求解选项
        solve_options_group = QGroupBox("求解选项")
        solve_options_layout = QVBoxLayout()
        
        # 初始条件/猜测值
        ic_layout = QHBoxLayout()
        ic_layout.addWidget(QLabel("初始条件/猜测值:"))
        self.ic_input = QLineEdit()
        self.ic_input.setPlaceholderText("例如: x0=1, y0=2")
        ic_layout.addWidget(self.ic_input)
        solve_options_layout.addLayout(ic_layout)
        
        # 求解范围
        range_layout = QHBoxLayout()
        range_layout.addWidget(QLabel("求解范围:"))
        self.range_min = QDoubleSpinBox()
        self.range_min.setRange(-1000, 1000)
        self.range_min.setValue(0)
        range_layout.addWidget(self.range_min)
        
        range_layout.addWidget(QLabel("到"))
        self.range_max = QDoubleSpinBox()
        self.range_max.setRange(-1000, 1000)
        self.range_max.setValue(10)
        range_layout.addWidget(self.range_max)
        solve_options_layout.addLayout(range_layout)
        
        # 求解方法
        method_layout = QHBoxLayout()
        method_layout.addWidget(QLabel("求解方法:"))
        self.method = QComboBox()
        self.method.addItems(["数值求解", "符号求解", "优化方法"])
        method_layout.addWidget(self.method)
        solve_options_layout.addLayout(method_layout)
        
        solve_options_group.setLayout(solve_options_layout)
        right_layout.addWidget(solve_options_group)
        
        # 求解按钮
        self.solve_btn = QPushButton("求解")
        self.solve_btn.clicked.connect(self.solve_equations)
        self.solve_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        right_layout.addWidget(self.solve_btn)
        
        # 进度条
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        right_layout.addWidget(self.progress)
        
        # 结果显示
        results_group = QGroupBox("求解结果")
        results_layout = QVBoxLayout()
        
        self.solution = QTextEdit()
        self.solution.setReadOnly(True)
        results_layout.addWidget(self.solution)
        
        # 可视化按钮
        self.visualize_btn = QPushButton("可视化结果")
        self.visualize_btn.clicked.connect(self.visualize_solution)
        self.visualize_btn.setEnabled(False)
        results_layout.addWidget(self.visualize_btn)
        
        results_group.setLayout(results_layout)
        right_layout.addWidget(results_group)
        
        right_panel.setLayout(right_layout)
        
        # 添加到主布局
        layout.addWidget(left_panel)
        layout.addWidget(right_panel)
        self.setLayout(layout)
        
        # 添加初始方程
        self.add_equation()
        
    def add_equation(self):
        eq_id = f"方程 {len(self.equations) + 1}"
        self.equations.append({
            'id': eq_id,
            'expression': 'x**2 - 4',
            'variables': 'x',
            'type': '代数方程'
        })
        
        self.eq_list.addItem(eq_id)
        self.eq_list.setCurrentRow(len(self.equations) - 1)
        
    def remove_equation(self):
        current_row = self.eq_list.currentRow()
        if current_row >= 0:
            eq_id = self.equations[current_row]['id']
            self.equations.pop(current_row)
            self.eq_list.takeItem(current_row)
            
            # 清除相关解决方案
            if eq_id in self.solutions:
                del self.solutions[eq_id]
                
    def on_equation_selected(self, row):
        if row >= 0 and row < len(self.equations):
            eq = self.equations[row]
            self.eq_input.setPlainText(eq['expression'])
            self.var_input.setText(eq['variables'])
            self.eq_type.setCurrentText(eq['type'])
            
            # 启用/禁用可视化按钮
            self.visualize_btn.setEnabled(eq['id'] in self.solutions)
            
    def update_equation(self):
        current_row = self.eq_list.currentRow()
        if current_row >= 0:
            eq = self.equations[current_row]
            eq['expression'] = self.eq_input.toPlainText()
            eq['variables'] = self.var_input.text()
            eq['type'] = self.eq_type.currentText()
            
            # 更新列表显示
            self.eq_list.currentItem().setText(f"{eq['id']}: {eq['expression']}")
            
            # 清除旧解决方案
            if eq['id'] in self.solutions:
                del self.solutions[eq['id']]
                self.visualize_btn.setEnabled(False)
                
    def solve_equations(self):
        if not self.equations:
            QMessageBox.warning(self, "警告", "请先添加方程")
            return
            
        current_row = self.eq_list.currentRow()
        if current_row < 0:
            return
            
        eq = self.equations[current_row]
        
        # 显示进度条
        self.progress.setVisible(True)
        self.progress.setRange(0, 0)  # 不确定进度
        
        # 在工作线程中执行求解
        self.worker = WorkerThread(self.solve_equation, eq)
        self.worker.result.connect(self.on_solution_ready)
        self.worker.error.connect(self.on_solution_error)
        self.worker.finished.connect(lambda: self.progress.setVisible(False))
        self.worker.start()
        
    def solve_equation(self, eq, progress_callback=None):
        try:
            expression = eq['expression']
            variables = [v.strip() for v in eq['variables'].split(',')]
            eq_type = eq['type']
            
            # 解析初始条件/猜测值
            initial_conditions = {}
            if self.ic_input.text():
                for ic in self.ic_input.text().split(','):
                    if '=' in ic:
                        key, value = ic.split('=')
                        initial_conditions[key.strip()] = float(value.strip())
            
            # 根据方程类型选择求解方法
            if eq_type == "代数方程":
                if self.method.currentText() == "符号求解":
                    # 使用SymPy进行符号求解
                    sym_vars = sp.symbols(variables)
                    eq_expr = sp.sympify(expression)
                    solutions = sp.solve(eq_expr, sym_vars)
                    
                    # 转换为数值解
                    if solutions:
                        if isinstance(solutions, list):
                            result = [complex(sol).real for sol in solutions]
                        else:
                            result = complex(solutions).real
                    else:
                        result = "无解"
                        
                else:
                    # 使用SciPy进行数值求解
                    func = eval(f"lambda {','.join(variables)}: {expression}")
                    
                    if len(variables) == 1:
                        # 单变量方程
                        x0 = initial_conditions.get(variables[0], 0)
                        result = optimize.root_scalar(func, bracket=[self.range_min.value(), self.range_max.value()], x0=x0).root
                    else:
                        # 多变量方程
                        x0 = [initial_conditions.get(var, 0) for var in variables]
                        result = optimize.root(func, x0).x
                        
            elif eq_type == "微分方程":
                # 求解微分方程
                t_range = (self.range_min.value(), self.range_max.value())
                t_eval = np.linspace(t_range[0], t_range[1], 1000)
                
                # 解析微分方程
                if '=' in expression:
                    # 形式为 dy/dt = f(t, y)
                    lhs, rhs = expression.split('=')
                    derivative_var = lhs.strip().split('/')[-1].strip('d ')
                    
                    # 创建微分方程函数
                    func = eval(f"lambda t, y: {rhs}")
                    
                    # 初始条件
                    y0 = initial_conditions.get(derivative_var, 0)
                    
                    # 求解ODE
                    result = integrate.solve_ivp(func, t_range, [y0], t_eval=t_eval)
                else:
                    result = "无效的微分方程格式，请使用 'dy/dt = f(t, y)' 格式"
                    
            elif eq_type == "方程组":
                # 求解方程组
                equations = [eq.strip() for eq in expression.split('\n') if eq.strip()]
                
                if self.method.currentText() == "符号求解":
                    # 使用SymPy求解方程组
                    sym_vars = sp.symbols(variables)
                    eq_exprs = [sp.sympify(eq) for eq in equations]
                    solutions = sp.solve(eq_exprs, sym_vars)
                    
                    if solutions:
                        result = {str(k): float(v) for k, v in solutions.items()}
                    else:
                        result = "无解"
                else:
                    # 使用SciPy求解方程组
                    def system_func(x):
                        result = []
                        local_vars = dict(zip(variables, x))
                        for eq in equations:
                            result.append(eval(eq, {"__builtins__": None}, local_vars))
                        return result
                    
                    x0 = [initial_conditions.get(var, 0) for var in variables]
                    result = optimize.root(system_func, x0).x
                    
            return result
            
        except Exception as e:
            raise Exception(f"求解错误: {str(e)}")
            
    def on_solution_ready(self, result):
        current_row = self.eq_list.currentRow()
        if current_row >= 0:
            eq_id = self.equations[current_row]['id']
            self.solutions[eq_id] = result
            
            # 显示结果
            if isinstance(result, np.ndarray):
                result_text = "解: " + np.array2string(result, precision=6)
            elif isinstance(result, dict):
                result_text = "解:\n"
                for var, value in result.items():
                    result_text += f"{var} = {value}\n"
            elif hasattr(result, 'y') and hasattr(result, 't'):  # ODE结果
                result_text = f"微分方程已求解，时间点: {len(result.t)}个，解的形状: {result.y.shape}"
            else:
                result_text = str(result)
                
            self.solution.setText(result_text)
            self.visualize_btn.setEnabled(True)
            
    def on_solution_error(self, error_msg):
        self.solution.setText(f"求解错误: {error_msg}")
        self.visualize_btn.setEnabled(False)
        
    def visualize_solution(self):
        current_row = self.eq_list.currentRow()
        if current_row < 0 or self.equations[current_row]['id'] not in self.solutions:
            return
            
        eq = self.equations[current_row]
        solution = self.solutions[eq['id']]
        
        try:
            fig = Figure(figsize=(10, 8))
            canvas = FigureCanvas(fig)
            
            if eq['type'] == "代数方程":
                # 绘制函数和解
                ax = fig.add_subplot(111)
                
                # 定义函数
                variables = [v.strip() for v in eq['variables'].split(',')]
                if len(variables) == 1:
                    x_var = variables[0]
                    func = eval(f"lambda {x_var}: {eq['expression']}")
                    
                    # 创建x值数组
                    x = np.linspace(self.range_min.value(), self.range_max.value(), 1000)
                    y = func(x)
                    
                    # 绘制函数
                    ax.plot(x, y, 'b-', label='f(x)')
                    
                    # 绘制解
                    if isinstance(solution, (int, float, complex)):
                        ax.plot(solution, func(solution), 'ro', label='解')
                    elif isinstance(solution, list):
                        for sol in solution:
                            ax.plot(sol, func(sol), 'ro')
                    
                    ax.axhline(0, color='k', linestyle='--', alpha=0.3)
                    ax.grid(True)
                    ax.legend()
                    ax.set_xlabel(x_var)
                    ax.set_ylabel('f(x)')
                    ax.set_title(f'函数 {eq["expression"]} 及其解')
                    
            elif eq['type'] == "微分方程":
                # 绘制微分方程解
                ax = fig.add_subplot(111)
                ax.plot(solution.t, solution.y[0])
                ax.set_xlabel('时间 t')
                ax.set_ylabel('解 y')
                ax.set_title('微分方程解')
                ax.grid(True)
                
            elif eq['type'] == "方程组":
                # 对于方程组，显示解的值
                ax = fig.add_subplot(111)
                if isinstance(solution, dict):
                    variables = list(solution.keys())
                    values = list(solution.values())
                    ax.bar(variables, values)
                    ax.set_ylabel('值')
                    ax.set_title('方程组的解')
                elif isinstance(solution, np.ndarray):
                    variables = [v.strip() for v in eq['variables'].split(',')]
                    ax.bar(variables, solution)
                    ax.set_ylabel('值')
                    ax.set_title('方程组的解')
                    
            # 显示图形窗口
            graph_window = QMainWindow()
            graph_window.setWindowTitle("解的可视化")
            graph_window.setCentralWidget(canvas)
            graph_window.resize(1000, 800)
            graph_window.show()
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"可视化时发生错误: {str(e)}")


class SignalProcessingTool(QWidget):
    """增强版信号处理工具"""
    def __init__(self):
        super().__init__()
        self.signals = {}  # 存储多个信号
        self.current_signal = None
        self.init_ui()
        
    def init_ui(self):
        layout = QHBoxLayout()
        
        # 左侧控制面板
        control_panel = QWidget()
        control_layout = QVBoxLayout()
        
        # 信号列表
        signal_list_group = QGroupBox("信号列表")
        signal_list_layout = QVBoxLayout()
        
        self.signal_list = QListWidget()
        self.signal_list.currentRowChanged.connect(self.on_signal_selected)
        signal_list_layout.addWidget(self.signal_list)
        
        signal_buttons = QHBoxLayout()
        self.add_signal_btn = QPushButton("添加信号")
        self.add_signal_btn.clicked.connect(self.add_signal)
        signal_buttons.addWidget(self.add_signal_btn)
        
        self.remove_signal_btn = QPushButton("删除信号")
        self.remove_signal_btn.clicked.connect(self.remove_signal)
        signal_buttons.addWidget(self.remove_signal_btn)
        
        signal_list_layout.addLayout(signal_buttons)
        signal_list_group.setLayout(signal_list_layout)
        control_layout.addWidget(signal_list_group)
        
        # 信号生成选项
        gen_group = QGroupBox("信号生成")
        gen_layout = QVBoxLayout()
        
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("信号类型:"))
        self.signal_type = QComboBox()
        self.signal_type.addItems(["正弦波", "方波", "锯齿波", "三角波", "白噪声", "脉冲", "自定义"])
        type_layout.addWidget(self.signal_type)
        gen_layout.addLayout(type_layout)
        
        # 参数设置
        param_layout = QGridLayout()
        
        param_layout.addWidget(QLabel("频率 (Hz):"), 0, 0)
        self.frequency = QDoubleSpinBox()
        self.frequency.setRange(0.1, 10000)
        self.frequency.setValue(5)
        param_layout.addWidget(self.frequency, 0, 1)
        
        param_layout.addWidget(QLabel("振幅:"), 1, 0)
        self.amplitude = QDoubleSpinBox()
        self.amplitude.setRange(0.1, 10)
        self.amplitude.setValue(1)
        param_layout.addWidget(self.amplitude, 1, 1)
        
        param_layout.addWidget(QLabel("相位:"), 2, 0)
        self.phase = QDoubleSpinBox()
        self.phase.setRange(0, 2*np.pi)
        self.phase.setValue(0)
        param_layout.addWidget(self.phase, 2, 1)
        
        param_layout.addWidget(QLabel("偏移:"), 3, 0)
        self.offset = QDoubleSpinBox()
        self.offset.setRange(-10, 10)
        self.offset.setValue(0)
        param_layout.addWidget(self.offset, 3, 1)
        
        gen_layout.addLayout(param_layout)
        
        # 时间设置
        time_layout = QGridLayout()
        
        time_layout.addWidget(QLabel("持续时间 (s):"), 0, 0)
        self.duration = QDoubleSpinBox()
        self.duration.setRange(0.1, 100)
        self.duration.setValue(1)
        time_layout.addWidget(self.duration, 0, 1)
        
        time_layout.addWidget(QLabel("采样率 (Hz):"), 1, 0)
        self.sample_rate = QSpinBox()
        self.sample_rate.setRange(10, 100000)
        self.sample_rate.setValue(1000)
        time_layout.addWidget(self.sample_rate, 1, 1)
        
        gen_layout.addLayout(time_layout)
        
        # 自定义信号表达式
        self.custom_signal_panel = QWidget()
        custom_layout = QVBoxLayout()
        custom_layout.addWidget(QLabel("自定义信号表达式 (使用t):"))
        self.custom_expr = QLineEdit("sin(2*pi*5*t) + 0.5*sin(2*pi*10*t)")
        custom_layout.addWidget(self.custom_expr)
        self.custom_signal_panel.setLayout(custom_layout)
        self.custom_signal_panel.setVisible(False)
        gen_layout.addWidget(self.custom_signal_panel)
        
        # 信号类型变化时显示/隐藏自定义面板
        self.signal_type.currentTextChanged.connect(self.toggle_custom_panel)
        
        self.generate_btn = QPushButton("生成信号")
        self.generate_btn.clicked.connect(self.generate_signal)
        gen_layout.addWidget(self.generate_btn)
        
        gen_group.setLayout(gen_layout)
        control_layout.addWidget(gen_group)
        
        # 信号处理选项
        process_group = QGroupBox("信号处理")
        process_layout = QVBoxLayout()
        
        process_layout.addWidget(QLabel("滤波器类型:"))
        self.filter_type = QComboBox()
        self.filter_type.addItems(["低通", "高通", "带通", "带阻", "移动平均", "中值滤波"])
        process_layout.addWidget(self.filter_type)
        
        cutoff_layout = QHBoxLayout()
        cutoff_layout.addWidget(QLabel("截止频率 (Hz):"))
        self.cutoff = QDoubleSpinBox()
        self.cutoff.setRange(0.1, 5000)
        self.cutoff.setValue(50)
        cutoff_layout.addWidget(self.cutoff)
        process_layout.addLayout(cutoff_layout)
        
        # 滤波器参数
        filter_param_layout = QHBoxLayout()
        filter_param_layout.addWidget(QLabel("滤波器阶数:"))
        self.filter_order = QSpinBox()
        self.filter_order.setRange(1, 20)
        self.filter_order.setValue(4)
        filter_param_layout.addWidget(self.filter_order)
        process_layout.addLayout(filter_param_layout)
        
        self.process_btn = QPushButton("处理信号")
        self.process_btn.clicked.connect(self.process_signal)
        process_layout.addWidget(self.process_btn)
        
        process_group.setLayout(process_layout)
        control_layout.addWidget(process_group)
        
        # 频谱分析
        spectrum_group = QGroupBox("频谱分析")
        spectrum_layout = QVBoxLayout()
        
        spectrum_layout.addWidget(QLabel("窗口函数:"))
        self.window_func = QComboBox()
        self.window_func.addItems(["矩形窗", "汉宁窗", "汉明窗", "布莱克曼窗"])
        spectrum_layout.addWidget(self.window_func)
        
        self.spectrum_btn = QPushButton("频谱分析")
        self.spectrum_btn.clicked.connect(self.spectrum_analysis)
        spectrum_layout.addWidget(self.spectrum_btn)
        
        spectrum_group.setLayout(spectrum_layout)
        control_layout.addWidget(spectrum_group)
        
        control_layout.addStretch()
        control_panel.setLayout(control_layout)
        control_panel.setMaximumWidth(400)
        
        # 右侧显示面板
        display_panel = QWidget()
        display_layout = QVBoxLayout()
        
        # 信号显示选项卡
        self.display_tabs = QTabWidget()
        
        # 时域显示
        time_domain_widget = QWidget()
        time_domain_layout = QVBoxLayout()
        
        self.time_figure = Figure(figsize=(10, 6))
        self.time_canvas = FigureCanvas(self.time_figure)
        self.time_toolbar = NavigationToolbar(self.time_canvas, self)
        
        time_domain_layout.addWidget(self.time_toolbar)
        time_domain_layout.addWidget(self.time_canvas)
        
        time_domain_widget.setLayout(time_domain_layout)
        self.display_tabs.addTab(time_domain_widget, "时域")
        
        # 频域显示
        freq_domain_widget = QWidget()
        freq_domain_layout = QVBoxLayout()
        
        self.freq_figure = Figure(figsize=(10, 6))
        self.freq_canvas = FigureCanvas(self.freq_figure)
        self.freq_toolbar = NavigationToolbar(self.freq_canvas, self)
        
        freq_domain_layout.addWidget(self.freq_toolbar)
        freq_domain_layout.addWidget(self.freq_canvas)
        
        freq_domain_widget.setLayout(freq_domain_layout)
        self.display_tabs.addTab(freq_domain_widget, "频域")
        
        display_layout.addWidget(self.display_tabs)
        
        # 信号信息
        info_group = QGroupBox("信号信息")
        info_layout = QVBoxLayout()
        
        self.signal_info = QTextEdit()
        self.signal_info.setReadOnly(True)
        self.signal_info.setMaximumHeight(150)
        info_layout.addWidget(self.signal_info)
        
        info_group.setLayout(info_layout)
        display_layout.addWidget(info_group)
        
        display_panel.setLayout(display_layout)
        
        # 添加到主布局
        layout.addWidget(control_panel)
        layout.addWidget(display_panel)
        self.setLayout(layout)
        
        # 添加初始信号
        self.add_signal()
        
    def toggle_custom_panel(self, signal_type):
        self.custom_signal_panel.setVisible(signal_type == "自定义")
        
    def add_signal(self):
        signal_id = f"信号 {len(self.signals) + 1}"
        self.signals[signal_id] = {
            'type': '正弦波',
            'frequency': 5,
            'amplitude': 1,
            'phase': 0,
            'offset': 0,
            'duration': 1,
            'sample_rate': 1000,
            'data': None,
            'time': None
        }
        
        self.signal_list.addItem(signal_id)
        self.signal_list.setCurrentRow(len(self.signals) - 1)
        
    def remove_signal(self):
        current_row = self.signal_list.currentRow()
        if current_row >= 0:
            signal_id = self.signal_list.currentItem().text()
            del self.signals[signal_id]
            self.signal_list.takeItem(current_row)
            
    def on_signal_selected(self, row):
        if row >= 0:
            signal_id = self.signal_list.item(row).text()
            if signal_id in self.signals:
                signal = self.signals[signal_id]
                self.current_signal = signal_id
                
                # 更新控件值
                self.signal_type.setCurrentText(signal['type'])
                self.frequency.setValue(signal['frequency'])
                self.amplitude.setValue(signal['amplitude'])
                self.phase.setValue(signal['phase'])
                self.offset.setValue(signal['offset'])
                self.duration.setValue(signal['duration'])
                self.sample_rate.setValue(signal['sample_rate'])
                
                # 显示信号
                if signal['data'] is not None:
                    self.display_signal(signal)
                    
    def generate_signal(self):
        if self.current_signal is None:
            return
            
        signal = self.signals[self.current_signal]
        
        # 更新信号参数
        signal['type'] = self.signal_type.currentText()
        signal['frequency'] = self.frequency.value()
        signal['amplitude'] = self.amplitude.value()
        signal['phase'] = self.phase.value()
        signal['offset'] = self.offset.value()
        signal['duration'] = self.duration.value()
        signal['sample_rate'] = self.sample_rate.value()
        
        # 生成时间向量
        t = np.linspace(0, signal['duration'], int(signal['sample_rate'] * signal['duration']), endpoint=False)
        signal['time'] = t
        
        # 生成信号
        try:
            if signal['type'] == "正弦波":
                signal['data'] = signal['amplitude'] * np.sin(2 * np.pi * signal['frequency'] * t + signal['phase']) + signal['offset']
            elif signal['type'] == "方波":
                signal['data'] = signal['amplitude'] * signal.square(2 * np.pi * signal['frequency'] * t + signal['phase']) + signal['offset']
            elif signal['type'] == "锯齿波":
                signal['data'] = signal['amplitude'] * signal.sawtooth(2 * np.pi * signal['frequency'] * t + signal['phase']) + signal['offset']
            elif signal['type'] == "三角波":
                signal['data'] = signal['amplitude'] * signal.sawtooth(2 * np.pi * signal['frequency'] * t + signal['phase'], width=0.5) + signal['offset']
            elif signal['type'] == "白噪声":
                signal['data'] = signal['amplitude'] * np.random.normal(0, 1, len(t)) + signal['offset']
            elif signal['type'] == "脉冲":
                signal['data'] = np.zeros_like(t)
                pulse_idx = int(len(t) / 2)
                signal['data'][pulse_idx] = signal['amplitude']
            elif signal['type'] == "自定义":
                expr = self.custom_expr.text()
                func = eval(f"lambda t: {expr}")
                signal['data'] = func(t)
                
            # 显示信号
            self.display_signal(signal)
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"生成信号时发生错误: {str(e)}")
            
    def display_signal(self, signal):
        # 更新时域图
        self.time_figure.clear()
        ax = self.time_figure.add_subplot(111)
        ax.plot(signal['time'], signal['data'])
        ax.set_xlabel('时间 (s)')
        ax.set_ylabel('幅度')
        ax.set_title('时域信号')
        ax.grid(True)
        self.time_canvas.draw()
        
        # 更新频域图
        self.freq_figure.clear()
        ax = self.freq_figure.add_subplot(111)
        
        # 计算FFT
        n = len(signal['data'])
        fft_result = fft.fft(signal['data'])
        freqs = fft.fftfreq(n, 1/signal['sample_rate'])
        
        # 只取正频率部分
        positive_freqs = freqs[:n//2]
        magnitude = np.abs(fft_result[:n//2]) / n
        
        ax.plot(positive_freqs, magnitude)
        ax.set_xlabel('频率 (Hz)')
        ax.set_ylabel('幅度')
        ax.set_title('信号频谱')
        ax.grid(True)
        self.freq_canvas.draw()
        
        # 更新信号信息
        info_text = f"信号类型: {signal['type']}\n"
        info_text += f"长度: {len(signal['data'])} 点\n"
        info_text += f"持续时间: {signal['duration']} 秒\n"
        info_text += f"采样率: {signal['sample_rate']} Hz\n"
        info_text += f"均值: {np.mean(signal['data']):.4f}\n"
        info_text += f"标准差: {np.std(signal['data']):.4f}\n"
        info_text += f"最大值: {np.max(signal['data']):.4f}\n"
        info_text += f"最小值: {np.min(signal['data']):.4f}\n"
        
        self.signal_info.setText(info_text)
        
    def process_signal(self):
        if self.current_signal is None or self.signals[self.current_signal]['data'] is None:
            QMessageBox.warning(self, "警告", "请先生成信号")
            return
        
        signal = self.signals[self.current_signal]
        
        try:
            # 应用滤波器
            filter_type = self.filter_type.currentText()
            cutoff = self.cutoff.value()
            order = self.filter_order.value()
            
            if filter_type == "低通":
                # 巴特沃斯低通滤波器
                nyquist = signal['sample_rate'] / 2
                normal_cutoff = cutoff / nyquist
                b, a = signal.butter(order, normal_cutoff, btype='low', analog=False)
                processed_signal = signal.filtfilt(b, a, signal['data'])
            elif filter_type == "高通":
                # 巴特沃斯高通滤波器
                nyquist = signal['sample_rate'] / 2
                normal_cutoff = cutoff / nyquist
                b, a = signal.butter(order, normal_cutoff, btype='high', analog=False)
                processed_signal = signal.filtfilt(b, a, signal['data'])
            elif filter_type == "带通":
                # 巴特沃斯带通滤波器
                nyquist = signal['sample_rate'] / 2
                low_cutoff = cutoff * 0.8  # 带宽的80%
                high_cutoff = cutoff * 1.2  # 带宽的120%
                normal_low = low_cutoff / nyquist
                normal_high = high_cutoff / nyquist
                b, a = signal.butter(order, [normal_low, normal_high], btype='band', analog=False)
                processed_signal = signal.filtfilt(b, a, signal['data'])
            elif filter_type == "带阻":
                # 巴特沃斯带阻滤波器
                nyquist = signal['sample_rate'] / 2
                low_cutoff = cutoff * 0.8  # 带宽的80%
                high_cutoff = cutoff * 1.2  # 带宽的120%
                normal_low = low_cutoff / nyquist
                normal_high = high_cutoff / nyquist
                b, a = signal.butter(order, [normal_low, normal_high], btype='bandstop', analog=False)
                processed_signal = signal.filtfilt(b, a, signal['data'])
            elif filter_type == "移动平均":
                # 移动平均滤波器
                window_size = order
                processed_signal = np.convolve(signal['data'], np.ones(window_size)/window_size, mode='same')
            elif filter_type == "中值滤波":
                # 中值滤波器
                processed_signal = signal.medfilt(signal['data'], kernel_size=order)
            
            # 创建处理后的信号副本
            processed_id = f"{self.current_signal} (滤波后)"
            self.signals[processed_id] = {
                'type': f"{signal['type']} (滤波后)",
                'frequency': signal['frequency'],
                'amplitude': signal['amplitude'],
                'phase': signal['phase'],
                'offset': signal['offset'],
                'duration': signal['duration'],
                'sample_rate': signal['sample_rate'],
                'data': processed_signal,
                'time': signal['time']
            }
            
            # 添加到信号列表
            self.signal_list.addItem(processed_id)
            self.signal_list.setCurrentRow(self.signal_list.count() - 1)
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"处理信号时发生错误: {str(e)}")
            
    def spectrum_analysis(self):
        if self.current_signal is None or self.signals[self.current_signal]['data'] is None:
            QMessageBox.warning(self, "警告", "请先生成信号")
            return
        
        signal = self.signals[self.current_signal]
        
        try:
            # 应用窗函数
            window_name = self.window_func.currentText()
            n = len(signal['data'])
            
            if window_name == "矩形窗":
                window = np.ones(n)
            elif window_name == "汉宁窗":
                window = np.hanning(n)
            elif window_name == "汉明窗":
                window = np.hamming(n)
            elif window_name == "布莱克曼窗":
                window = np.blackman(n)
            
            # 应用窗函数
            windowed_signal = signal['data'] * window
            
            # 计算FFT
            fft_result = fft.fft(windowed_signal)
            freqs = fft.fftfreq(n, 1/signal['sample_rate'])
            
            # 只取正频率部分
            positive_freqs = freqs[:n//2]
            magnitude = np.abs(fft_result[:n//2]) / n
            
            # 显示频谱
            fig = Figure(figsize=(10, 6))
            canvas = FigureCanvas(fig)
            ax = fig.add_subplot(111)
            ax.plot(positive_freqs, magnitude)
            ax.set_xlabel('频率 (Hz)')
            ax.set_ylabel('幅度')
            ax.set_title(f'信号频谱 ({window_name})')
            ax.grid(True)
            
            # 显示图形窗口
            graph_window = QMainWindow()
            graph_window.setWindowTitle("频谱分析")
            graph_window.setCentralWidget(canvas)
            graph_window.resize(1000, 800)
            graph_window.show()
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"频谱分析时发生错误: {str(e)}")


class NumericalMethodsTool(QWidget):
    """数值方法工具"""
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 方法选择
        method_layout = QHBoxLayout()
        method_layout.addWidget(QLabel("数值方法:"))
        self.method = QComboBox()
        self.method.addItems(["数值积分", "数值微分", "插值", "优化", "常微分方程求解"])
        self.method.currentTextChanged.connect(self.update_interface)
        method_layout.addWidget(self.method)
        layout.addLayout(method_layout)
        
        # 参数输入区域
        self.param_widget = QWidget()
        self.param_layout = QVBoxLayout()  # 添加这一行
        self.param_widget.setLayout(self.param_layout)  # 添加这一行
        layout.addWidget(self.param_widget)
        
        # 计算按钮
        self.calculate_btn = QPushButton("计算")
        self.calculate_btn.clicked.connect(self.calculate)
        layout.addWidget(self.calculate_btn)
        
        # 进度条
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        layout.addWidget(self.progress)
        
        # 结果显示
        self.result = QTextEdit()
        self.result.setReadOnly(True)
        layout.addWidget(self.result)
        
        self.setLayout(layout)
        self.update_interface()
        
    def update_interface(self):
        # 清除现有参数界面
        while self.param_layout.count():  # 修改这一行
            child = self.param_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        method = self.method.currentText()
        
        if method == "数值积分":
            self.param_layout.addWidget(QLabel("被积函数:"))
            self.func_input = QLineEdit("sin(x)")
            self.param_layout.addWidget(self.func_input)
            
            range_layout = QHBoxLayout()
            range_layout.addWidget(QLabel("从"))
            self.lower_limit = QDoubleSpinBox()
            self.lower_limit.setRange(-1000, 1000)
            self.lower_limit.setValue(0)
            range_layout.addWidget(self.lower_limit)
            
            range_layout.addWidget(QLabel("到"))
            self.upper_limit = QDoubleSpinBox()
            self.upper_limit.setRange(-1000, 1000)
            self.upper_limit.setValue(np.pi)
            range_layout.addWidget(self.upper_limit)
            
            self.param_layout.addLayout(range_layout)
            
            self.param_layout.addWidget(QLabel("积分方法:"))
            self.integration_method = QComboBox()
            self.integration_method.addItems(["quad", "fixed_quad", "quadrature", "romberg", "trapezoid", "simpson"])
            self.param_layout.addWidget(self.integration_method)
            
        elif method == "数值微分":
            self.param_layout.addWidget(QLabel("函数:"))
            self.func_input = QLineEdit("sin(x)")
            self.param_layout.addWidget(self.func_input)
            
            self.param_layout.addWidget(QLabel("求导点:"))
            self.diff_point = QDoubleSpinBox()
            self.diff_point.setRange(-1000, 1000)
            self.diff_point.setValue(0)
            self.param_layout.addWidget(self.diff_point)
            
            self.param_layout.addWidget(QLabel("微分方法:"))
            self.differentiation_method = QComboBox()
            self.differentiation_method.addItems(["中心差分", "前向差分", "后向差分"])
            self.param_layout.addWidget(self.differentiation_method)
            
        elif method == "插值":
            self.param_layout.addWidget(QLabel("数据点 x (逗号分隔):"))
            self.x_points = QLineEdit("0, 1, 2, 3, 4")
            self.param_layout.addWidget(self.x_points)
            
            self.param_layout.addWidget(QLabel("数据点 y (逗号分隔):"))
            self.y_points = QLineEdit("0, 1, 4, 9, 16")
            self.param_layout.addWidget(self.y_points)
            
            self.param_layout.addWidget(QLabel("插值点:"))
            self.interp_point = QDoubleSpinBox()
            self.interp_point.setRange(-1000, 1000)
            self.interp_point.setValue(2.5)
            self.param_layout.addWidget(self.interp_point)
            
            self.param_layout.addWidget(QLabel("插值方法:"))
            self.interpolation_method = QComboBox()
            self.interpolation_method.addItems(["线性", "多项式", "样条", "最近邻"])
            self.param_layout.addWidget(self.interpolation_method)
            
        elif method == "优化":
            self.param_layout.addWidget(QLabel("目标函数:"))
            self.objective_func = QLineEdit("x**2 + 10*sin(x)")
            self.param_layout.addWidget(self.objective_func)
            
            range_layout = QHBoxLayout()
            range_layout.addWidget(QLabel("从"))
            self.opt_lower = QDoubleSpinBox()
            self.opt_lower.setRange(-1000, 1000)
            self.opt_lower.setValue(-5)
            range_layout.addWidget(self.opt_lower)
            
            range_layout.addWidget(QLabel("到"))
            self.opt_upper = QDoubleSpinBox()
            self.opt_upper.setRange(-1000, 1000)
            self.opt_upper.setValue(5)
            range_layout.addWidget(self.opt_upper)
            
            self.param_layout.addLayout(range_layout)
            
            self.param_layout.addWidget(QLabel("优化方法:"))
            self.optimization_method = QComboBox()
            self.optimization_method.addItems(["BFGS", "Nelder-Mead", "Powell", "CG", "L-BFGS-B"])
            self.param_layout.addWidget(self.optimization_method)
            
        elif method == "常微分方程求解":
            self.param_layout.addWidget(QLabel("微分方程:"))
            self.ode_func = QLineEdit("-2*y + t")
            self.param_layout.addWidget(self.ode_func)
            
            self.param_layout.addWidget(QLabel("初始条件:"))
            self.initial_condition = QLineEdit("y0=1")
            self.param_layout.addWidget(self.initial_condition)
            
            range_layout = QHBoxLayout()
            range_layout.addWidget(QLabel("从 t="))
            self.ode_t0 = QDoubleSpinBox()
            self.ode_t0.setRange(0, 1000)
            self.ode_t0.setValue(0)
            range_layout.addWidget(self.ode_t0)
            
            range_layout.addWidget(QLabel("到 t="))
            self.ode_t1 = QDoubleSpinBox()
            self.ode_t1.setRange(0, 1000)
            self.ode_t1.setValue(5)
            range_layout.addWidget(self.ode_t1)
            
            self.param_layout.addLayout(range_layout)
            
            self.param_layout.addWidget(QLabel("求解方法:"))
            self.ode_method = QComboBox()
            self.ode_method.addItems(["RK45", "RK23", "DOP853", "Radau", "BDF"])
            self.param_layout.addWidget(self.ode_method)
            
        self.param_widget.setLayout(self.param_layout)
        
    def calculate(self):
        method = self.method.currentText()
        
        # 显示进度条
        self.progress.setVisible(True)
        self.progress.setRange(0, 0)  # 不确定进度
        
        # 在工作线程中执行计算
        self.worker = WorkerThread(self.calculate_method, method)
        self.worker.result.connect(self.on_result_ready)
        self.worker.error.connect(self.on_result_error)
        self.worker.finished.connect(lambda: self.progress.setVisible(False))
        self.worker.start()
        
    def calculate_method(self, method, progress_callback=None):
        try:
            if method == "数值积分":
                return self.calculate_integration()
            elif method == "数值微分":
                return self.calculate_differentiation()
            elif method == "插值":
                return self.calculate_interpolation()
            elif method == "优化":
                return self.calculate_optimization()
            elif method == "常微分方程求解":
                return self.calculate_ode()
        except Exception as e:
            raise Exception(f"计算错误: {str(e)}")
            
    def calculate_integration(self):
        func_str = self.func_input.text()
        a = self.lower_limit.value()
        b = self.upper_limit.value()
        method = self.integration_method.currentText()
        
        # 定义函数
        func = eval(f"lambda x: {func_str}")
        
        # 选择积分方法
        if method == "quad":
            result, error = integrate.quad(func, a, b)
            return f"积分结果: {result}\n估计误差: {error}"
        elif method == "fixed_quad":
            result = integrate.fixed_quad(func, a, b)[0]
            return f"固定阶高斯积分结果: {result}"
        elif method == "quadrature":
            result, error = integrate.quadrature(func, a, b)
            return f"积分结果: {result}\n估计误差: {error}"
        elif method == "romberg":
            result = integrate.romberg(func, a, b)
            return f"Romberg积分结果: {result}"
        elif method == "trapezoid":
            x = np.linspace(a, b, 1000)
            y = func(x)
            result = integrate.trapz(y, x)
            return f"梯形法积分结果: {result}"
        elif method == "simpson":
            x = np.linspace(a, b, 1000)
            y = func(x)
            result = integrate.simpson(y, x)
            return f"Simpson法积分结果: {result}"
            
    def calculate_differentiation(self):
        func_str = self.func_input.text()
        x0 = self.diff_point.value()
        method = self.differentiation_method.currentText()
        
        # 定义函数
        func = eval(f"lambda x: {func_str}")
        
        # 选择微分方法
        h = 1e-5  # 步长
        
        if method == "中心差分":
            derivative = (func(x0 + h) - func(x0 - h)) / (2 * h)
        elif method == "前向差分":
            derivative = (func(x0 + h) - func(x0)) / h
        elif method == "后向差分":
            derivative = (func(x0) - func(x0 - h)) / h
            
        return f"在 x = {x0} 处的导数: {derivative}"
        
    def calculate_interpolation(self):
        x_points = [float(x.strip()) for x in self.x_points.text().split(',')]
        y_points = [float(y.strip()) for y in self.y_points.text().split(',')]
        x = self.interp_point.value()
        method = self.interpolation_method.currentText()
        
        # 选择插值方法
        if method == "线性":
            result = np.interp(x, x_points, y_points)
            return f"在 x = {x} 处的线性插值结果: {result}"
        elif method == "多项式":
            poly = np.polyfit(x_points, y_points, len(x_points)-1)
            result = np.polyval(poly, x)
            return f"在 x = {x} 处的多项式插值结果: {result}"
        elif method == "样条":
            from scipy.interpolate import CubicSpline
            cs = CubicSpline(x_points, y_points)
            result = cs(x)
            return f"在 x = {x} 处的样条插值结果: {result}"
        elif method == "最近邻":
            idx = np.argmin(np.abs(np.array(x_points) - x))
            result = y_points[idx]
            return f"在 x = {x} 处的最近邻插值结果: {result}"
            
    def calculate_optimization(self):
        func_str = self.objective_func.text()
        bounds = (self.opt_lower.value(), self.opt_upper.value())
        method = self.optimization_method.currentText()
        
        # 定义函数
        func = eval(f"lambda x: {func_str}")
        
        # 执行优化
        result = optimize.minimize(func, x0=[(bounds[0] + bounds[1])/2], 
                                  bounds=[bounds], method=method)
        
        return f"优化结果:\n最优解: x = {result.x[0]}\n函数值: {result.fun}\n是否成功: {result.success}\n迭代次数: {result.nit}"
        
    def calculate_ode(self):
        func_str = self.ode_func.text()
        t_span = (self.ode_t0.value(), self.ode_t1.value())
        method = self.ode_method.currentText()
        
        # 解析初始条件
        ic_str = self.initial_condition.text()
        if '=' in ic_str:
            _, y0 = ic_str.split('=')
            y0 = float(y0.strip())
        else:
            y0 = 1.0  # 默认值
            
        # 定义微分方程
        def ode_func(t, y):
            return eval(func_str, {'t': t, 'y': y})
        
        # 求解ODE
        result = integrate.solve_ivp(ode_func, t_span, [y0], method=method, dense_output=True)
        
        return f"ODE求解结果:\n时间点: {len(result.t)}个\n解的形状: {result.y.shape}\n是否成功: {result.success}\n消息: {result.message}"
        
    def on_result_ready(self, result):
        self.result.setText(result)
        
    def on_result_error(self, error_msg):
        self.result.setText(f"计算错误: {error_msg}")


class MainWindow(QMainWindow):
    """主窗口"""
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("高级PyQt科学计算系统")
        self.setGeometry(100, 100, 1400, 900)
        
        # 设置应用程序样式
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f0f0f0;
            }
            QWidget {
                font-family: Segoe UI, Arial;
                font-size: 11px;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #cccccc;
                border-radius: 4px;
                margin-top: 1ex;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QPushButton {
                background-color: #e0e0e0;
                border: 1px solid #cccccc;
                border-radius: 4px;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: #d0d0d0;
            }
            QPushButton:pressed {
                background-color: #c0c0c0;
            }
            QTabWidget::pane {
                border: 1px solid #cccccc;
                border-radius: 4px;
            }
            QTabBar::tab {
                background: #e0e0e0;
                border: 1px solid #cccccc;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                padding: 5px 15px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background: #ffffff;
                border-bottom: 1px solid #ffffff;
            }
        """)
        
        # 创建中心部件和选项卡
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout()
        central_widget.setLayout(layout)
        
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        
        # 添加各个工具选项卡
        self.tabs.addTab(ScientificCalculator(), "科学计算器")
        self.tabs.addTab(FunctionPlotter(), "函数绘图")
        self.tabs.addTab(DataAnalysisTool(), "数据分析")
        self.tabs.addTab(EquationSolver(), "方程求解")
        self.tabs.addTab(SignalProcessingTool(), "信号处理")
        self.tabs.addTab(NumericalMethodsTool(), "数值方法")
        
        # 创建菜单栏
        self.create_menus()
        
        # 创建工具栏
        self.create_toolbar()
        
        # 创建状态栏
        self.statusBar().showMessage("就绪")
        
        # 创建停靠窗口
        self.create_dock_widgets()
        
    def create_menus(self):
        # 文件菜单
        file_menu = self.menuBar().addMenu("文件")
        
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
        tools_menu = self.menuBar().addMenu("工具")
        
        calc_action = QAction("科学计算器", self)
        calc_action.triggered.connect(lambda: self.tabs.setCurrentIndex(0))
        tools_menu.addAction(calc_action)
        
        plot_action = QAction("函数绘图", self)
        plot_action.triggered.connect(lambda: self.tabs.setCurrentIndex(1))
        tools_menu.addAction(plot_action)
        
        data_action = QAction("数据分析", self)
        data_action.triggered.connect(lambda: self.tabs.setCurrentIndex(2))
        tools_menu.addAction(data_action)
        
        eq_action = QAction("方程求解", self)
        eq_action.triggered.connect(lambda: self.tabs.setCurrentIndex(3))
        tools_menu.addAction(eq_action)
        
        signal_action = QAction("信号处理", self)
        signal_action.triggered.connect(lambda: self.tabs.setCurrentIndex(4))
        tools_menu.addAction(signal_action)
        
        num_action = QAction("数值方法", self)
        num_action.triggered.connect(lambda: self.tabs.setCurrentIndex(5))
        tools_menu.addAction(num_action)
        
        # 视图菜单
        view_menu = self.menuBar().addMenu("视图")
        
        toolbar_action = QAction("工具栏", self, checkable=True, checked=True)
        toolbar_action.triggered.connect(self.toggle_toolbar)
        view_menu.addAction(toolbar_action)
        
        statusbar_action = QAction("状态栏", self, checkable=True, checked=True)
        statusbar_action.triggered.connect(self.toggle_statusbar)
        view_menu.addAction(statusbar_action)
        
        # 帮助菜单
        help_menu = self.menuBar().addMenu("帮助")
        
        docs_action = QAction("文档", self)
        help_menu.addAction(docs_action)
        
        examples_action = QAction("示例", self)
        help_menu.addAction(examples_action)
        
        help_menu.addSeparator()
        
        about_action = QAction("关于", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def create_toolbar(self):
        toolbar = QToolBar("主工具栏")
        toolbar.setIconSize(QSize(16, 16))
        self.addToolBar(toolbar)
        
        # 添加工具栏动作
        new_action = QAction(QIcon(":/icons/new.png"), "新建", self)
        toolbar.addAction(new_action)
        
        open_action = QAction(QIcon(":/icons/open.png"), "打开", self)
        toolbar.addAction(open_action)
        
        save_action = QAction(QIcon(":/icons/save.png"), "保存", self)
        toolbar.addAction(save_action)
        
        toolbar.addSeparator()
        
        calc_action = QAction(QIcon(":/icons/calculator.png"), "计算器", self)
        calc_action.triggered.connect(lambda: self.tabs.setCurrentIndex(0))
        toolbar.addAction(calc_action)
        
        plot_action = QAction(QIcon(":/icons/plot.png"), "绘图", self)
        plot_action.triggered.connect(lambda: self.tabs.setCurrentIndex(1))
        toolbar.addAction(plot_action)
        
        data_action = QAction(QIcon(":/icons/data.png"), "数据分析", self)
        data_action.triggered.connect(lambda: self.tabs.setCurrentIndex(2))
        toolbar.addAction(data_action)
        
    def create_dock_widgets(self):
        # 历史记录停靠窗口
        history_dock = QDockWidget("最近计算", self)
        history_dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        
        history_widget = QListWidget()
        history_dock.setWidget(history_widget)
        
        self.addDockWidget(Qt.RightDockWidgetArea, history_dock)
        
        # 变量监视停靠窗口
        variables_dock = QDockWidget("变量监视", self)
        variables_dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        
        variables_widget = QTableWidget()
        variables_widget.setColumnCount(2)
        variables_widget.setHorizontalHeaderLabels(["变量", "值"])
        variables_dock.setWidget(variables_widget)
        
        self.addDockWidget(Qt.RightDockWidgetArea, variables_dock)
        
    def toggle_toolbar(self, visible):
        self.toolbar.setVisible(visible)
        
    def toggle_statusbar(self, visible):
        self.statusBar().setVisible(visible)
    
    def show_about(self):
        about_text = """
        <h2>高级PyQt科学计算系统</h2>
        <p>一个功能强大的科学计算平台，集成多种科学计算和数据分析工具。</p>
        <p>功能包括：</p>
        <ul>
            <li>科学计算器 - 支持变量管理和历史记录</li>
            <li>函数绘图 - 支持2D和3D函数绘图，多图管理</li>
            <li>数据分析 - 支持数据加载、统计分析和可视化</li>
            <li>方程求解 - 支持代数方程、微分方程和方程组的求解</li>
            <li>信号处理 - 支持信号生成、滤波和频谱分析</li>
            <li>数值方法 - 支持数值积分、微分、插值和优化</li>
        </ul>
        <p>版本: 2.0</p>
        <p>版权所有 © 2025 科学计算系统团队</p>
        """
        
        QMessageBox.about(self, "关于", about_text)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")  # 使用Fusion风格，使界面看起来更现代
    
    # 设置应用程序字体
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec_())