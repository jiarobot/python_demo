import sys
import os
import numpy as np
import pandas as pd
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QSplitter, QTabWidget, QToolBar,
                             QStatusBar, QDockWidget, QLabel, QComboBox,
                             QSlider, QSpinBox, QDoubleSpinBox, QCheckBox,
                             QAction, QFileDialog, QColorDialog, QMessageBox,
                             QProgressBar, QProgressDialog, QListWidget, 
                             QListWidgetItem, QTreeWidget, QTreeWidgetItem,
                             QGroupBox, QPushButton, QTextEdit, QMenu,
                             QDialog, QDialogButtonBox, QFormLayout)
from PyQt5.QtGui import QIcon, QColor, QPalette, QFont, QPixmap, QPainter
import pyqtgraph as pg
from pyqtgraph import PlotWidget, PlotItem, ImageView, ScatterPlotItem, GraphicsLayoutWidget
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.colors import LinearSegmentedColormap
import seaborn as sns
from scipy import stats, interpolate, signal
from scipy.optimize import curve_fit
from sklearn.decomposition import PCA, NMF
from sklearn.manifold import TSNE, Isomap, MDS
from sklearn.cluster import KMeans, DBSCAN
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.metrics import r2_score, mean_squared_error
import h5py
import json
import pickle
import warnings
warnings.filterwarnings('ignore')

# 设置样式
plt.style.use('seaborn-v0_8')
sns.set_palette("husl")
pg.setConfigOptions(antialias=True, useOpenGL=True)

class AnalysisWorker(QThread):
    """后台分析线程"""
    progress = pyqtSignal(int)
    finished = pyqtSignal(object)
    error = pyqtSignal(str)
    
    def __init__(self, data, method, params):
        super().__init__()
        self.data = data
        self.method = method
        self.params = params
        
    def run(self):
        try:
            result = self.perform_analysis()
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))
    
    def perform_analysis(self):
        """执行分析"""
        if self.method == "PCA":
            pca = PCA(n_components=self.params['n_components'])
            result = pca.fit_transform(self.data)
            return {'result': result, 'explained_variance': pca.explained_variance_ratio_}
            
        elif self.method == "t-SNE":
            tsne = TSNE(n_components=self.params['n_components'], 
                       perplexity=self.params.get('perplexity', 30),
                       random_state=42)
            result = tsne.fit_transform(self.data)
            return {'result': result}
            
        elif self.method == "K-Means":
            kmeans = KMeans(n_clusters=self.params['n_clusters'], 
                           random_state=42)
            labels = kmeans.fit_predict(self.data)
            return {'labels': labels, 'centers': kmeans.cluster_centers_}
            
        elif self.method == "Linear Regression":
            X = self.data[:, :-1]
            y = self.data[:, -1]
            model = LinearRegression()
            model.fit(X, y)
            y_pred = model.predict(X)
            return {'model': model, 'predictions': y_pred, 
                   'r2': r2_score(y, y_pred), 'coef': model.coef_}
        
        return None

class MplCanvas(FigureCanvas):
    """增强的Matplotlib画布组件"""
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_subplot(111)
        super().__init__(self.fig)
        self.setParent(parent)
        
        # 设置样式
        self.fig.tight_layout()
        self.fig.patch.set_facecolor('#F0F0F0')
        self.axes.set_facecolor('#FFFFFF')
        self.axes.grid(True, alpha=0.3)
        
    def clear(self):
        """清除画布"""
        self.axes.clear()
        self.axes.grid(True, alpha=0.3)
        self.draw()

class EnhancedPlotWidget(QWidget):
    """增强的绘图组件"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        
        # 创建工具栏
        self.setup_plot_toolbar()
        
        # 创建标签页
        self.tab_widget = QTabWidget()
        self.layout.addWidget(self.tab_widget)
        
        # 创建不同的绘图视图
        self.setup_pyqtgraph_tab()
        self.setup_matplotlib_tab()
        self.setup_3d_visualization_tab()
        self.setup_image_view_tab()
        self.setup_statistical_plots_tab()
        
        # 当前绘图数据
        self.plot_data = {}
        
    def setup_plot_toolbar(self):
        """设置绘图工具栏"""
        toolbar = QHBoxLayout()
        
        # 缩放控制
        toolbar.addWidget(QLabel("Zoom:"))
        self.zoom_slider = QSlider(Qt.Horizontal)
        self.zoom_slider.setRange(50, 200)
        self.zoom_slider.setValue(100)
        toolbar.addWidget(self.zoom_slider)
        
        # 平移控制
        toolbar.addWidget(QLabel("Pan:"))
        self.pan_checkbox = QCheckBox("Enable")
        toolbar.addWidget(self.pan_checkbox)
        
        # 自动范围
        self.auto_range_btn = QPushButton("Auto Range")
        toolbar.addWidget(self.auto_range_btn)
        
        # 保存图片
        self.save_plot_btn = QPushButton("Save Plot")
        toolbar.addWidget(self.save_plot_btn)
        
        toolbar.addStretch()
        self.layout.addLayout(toolbar)
        
    def setup_pyqtgraph_tab(self):
        """设置PyQtGraph标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 创建PyQtGraph绘图控件
        self.pg_plot = pg.PlotWidget()
        self.pg_plot.setBackground('w')
        self.pg_plot.showGrid(x=True, y=True, alpha=0.3)
        self.pg_plot.addLegend()
        self.pg_plot.setMenuEnabled(True)
        
        # 添加十字准线
        self.vLine = pg.InfiniteLine(angle=90, movable=False)
        self.hLine = pg.InfiniteLine(angle=0, movable=False)
        self.pg_plot.addItem(self.vLine, ignoreBounds=True)
        self.pg_plot.addItem(self.hLine, ignoreBounds=True)
        
        # 鼠标移动事件
        self.proxy = pg.SignalProxy(self.pg_plot.scene().sigMouseMoved, 
                                   rateLimit=60, slot=self.mouse_moved)
        
        layout.addWidget(self.pg_plot)
        self.tab_widget.addTab(widget, "PyQtGraph")
        
    def setup_matplotlib_tab(self):
        """设置Matplotlib标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 创建Matplotlib画布
        self.mpl_canvas = MplCanvas(self, width=8, height=6, dpi=100)
        layout.addWidget(self.mpl_canvas)
        
        self.tab_widget.addTab(widget, "Matplotlib")
        
    def setup_3d_visualization_tab(self):
        """设置3D可视化标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 创建3D可视化控件
        self.glw = pg.GraphicsLayoutWidget()
        self.view = self.glw.addViewBox()
        self.view.setAspectLocked(False)
        
        # 创建网格
        g = pg.GridItem()
        self.view.addItem(g)
        
        # 创建3D散点图
        self.scatter_3d = pg.ScatterPlotItem(size=10, pen=pg.mkPen(None), 
                                           brush=pg.mkBrush(255, 0, 0, 120))
        self.view.addItem(self.scatter_3d)
        
        layout.addWidget(self.glw)
        self.tab_widget.addTab(widget, "3D Visualization")
        
    def setup_image_view_tab(self):
        """设置图像视图标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 创建图像视图
        self.image_view = ImageView()
        layout.addWidget(self.image_view)
        
        self.tab_widget.addTab(widget, "Image View")
        
    def setup_statistical_plots_tab(self):
        """设置统计绘图标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 创建统计绘图区域
        self.stats_plot = pg.PlotWidget()
        self.stats_plot.setBackground('w')
        layout.addWidget(self.stats_plot)
        
        self.tab_widget.addTab(widget, "Statistical Plots")
        
    def mouse_moved(self, evt):
        """鼠标移动事件"""
        pos = evt[0]
        if self.pg_plot.sceneBoundingRect().contains(pos):
            mousePoint = self.pg_plot.plotItem.vb.mapSceneToView(pos)
            self.vLine.setPos(mousePoint.x())
            self.hLine.setPos(mousePoint.y())
            
    def plot_line(self, x, y, label="Data", color=None, width=2, style=Qt.SolidLine):
        """绘制线图"""
        if color is None:
            color = (np.random.randint(0, 255), np.random.randint(0, 255), np.random.randint(0, 255))
        
        pen = pg.mkPen(color, width=width, style=style)
        self.pg_plot.plot(x, y, name=label, pen=pen)
        
        # 同时绘制到matplotlib
        self.mpl_canvas.axes.plot(x, y, label=label, color=np.array(color)/255)
        self.mpl_canvas.axes.legend()
        self.mpl_canvas.draw()
        
    def plot_scatter(self, x, y, label="Data", color=None, size=10, symbol='o'):
        """绘制散点图"""
        if color is None:
            color = (np.random.randint(0, 255), np.random.randint(0, 255), np.random.randint(0, 255))
        
        self.pg_plot.plot(x, y, name=label, pen=None, symbol=symbol, 
                         symbolBrush=color, symbolSize=size)
        
        # 同时绘制到matplotlib
        self.mpl_canvas.axes.scatter(x, y, label=label, color=np.array(color)/255, s=size*10)
        self.mpl_canvas.axes.legend()
        self.mpl_canvas.draw()
        
    def plot_histogram(self, data, label="Data", color=None, bins=20):
        """绘制直方图"""
        if color is None:
            color = (np.random.randint(0, 255), np.random.randint(0, 255), np.random.randint(0, 255))
        
        y, x = np.histogram(data, bins=bins)
        self.pg_plot.plot(x, y, stepMode=True, fillLevel=0, 
                         brush=color, name=label)
        
        # 同时绘制到matplotlib
        self.mpl_canvas.axes.hist(data, bins=bins, alpha=0.7, label=label, 
                                 color=np.array(color)/255)
        self.mpl_canvas.axes.legend()
        self.mpl_canvas.draw()
        
    def plot_3d_scatter(self, data, colors=None, size=5):
        """绘制3D散点图"""
        if colors is None:
            colors = np.ones((data.shape[0], 4)) * [1, 0, 0, 1]
            
        self.scatter_3d.setData(pos=data[:, :2], size=size, brush=colors)
        
    def display_image(self, image, auto_range=True, auto_levels=True):
        """显示图像"""
        self.image_view.setImage(image, autoRange=auto_range, autoLevels=auto_levels)
        
    def clear_all(self):
        """清除所有绘图"""
        self.pg_plot.clear()
        self.mpl_canvas.clear()
        self.scatter_3d.clear()
        self.image_view.clear()
        self.stats_plot.clear()

class EnhancedDataTable(QWidget):
    """增强的数据表格组件"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        
        # 创建工具栏
        self.setup_table_toolbar()
        
        # 创建表格
        self.table = QtWidgets.QTableWidget()
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.table.setSortingEnabled(True)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        
        self.layout.addWidget(self.table)
        
        # 当前数据
        self.df = None
        
    def setup_table_toolbar(self):
        """设置表格工具栏"""
        toolbar = QHBoxLayout()
        
        self.filter_btn = QPushButton("Filter Data")
        self.sort_btn = QPushButton("Sort Data")
        self.stats_btn = QPushButton("Show Statistics")
        self.export_btn = QPushButton("Export Data")
        
        toolbar.addWidget(self.filter_btn)
        toolbar.addWidget(self.sort_btn)
        toolbar.addWidget(self.stats_btn)
        toolbar.addWidget(self.export_btn)
        toolbar.addStretch()
        
        self.layout.addLayout(toolbar)
        
    def show_context_menu(self, position):
        """显示右键菜单"""
        menu = QMenu(self)
        
        copy_action = menu.addAction("Copy Selection")
        delete_action = menu.addAction("Delete Selected Rows")
        plot_action = menu.addAction("Plot Selected Data")
        
        action = menu.exec_(self.table.mapToGlobal(position))
        
        if action == copy_action:
            self.copy_selection()
        elif action == delete_action:
            self.delete_selected_rows()
        elif action == plot_action:
            self.plot_selected_data()
            
    def copy_selection(self):
        """复制选中的数据"""
        selection = self.table.selectedRanges()
        if selection:
            text = ""
            for row in range(selection[0].topRow(), selection[0].bottomRow() + 1):
                row_data = []
                for col in range(selection[0].leftColumn(), selection[0].rightColumn() + 1):
                    item = self.table.item(row, col)
                    if item is not None:
                        row_data.append(item.text())
                    else:
                        row_data.append("")
                text += "\t".join(row_data) + "\n"
            
            clipboard = QApplication.clipboard()
            clipboard.setText(text)
            
    def delete_selected_rows(self):
        """删除选中的行"""
        selected_rows = set()
        for item in self.table.selectedItems():
            selected_rows.add(item.row())
            
        if selected_rows:
            reply = QMessageBox.question(self, "Confirm Delete", 
                                       f"Delete {len(selected_rows)} rows?",
                                       QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                # 从DataFrame中删除行
                rows_to_delete = sorted(selected_rows, reverse=True)
                for row in rows_to_delete:
                    self.df = self.df.drop(self.df.index[row])
                
                # 重新加载表格
                self.load_data(self.df)
                
    def plot_selected_data(self):
        """绘制选中的数据"""
        selected_rows = set()
        selected_cols = set()
        
        for item in self.table.selectedItems():
            selected_rows.add(item.row())
            selected_cols.add(item.column())
            
        if selected_rows and selected_cols:
            # 获取选中的数据
            selected_data = self.df.iloc[sorted(selected_rows), sorted(selected_cols)]
            return selected_data
            
        return None
        
    def load_data(self, data):
        """加载数据到表格"""
        if isinstance(data, pd.DataFrame):
            self.df = data.copy()
        else:
            self.df = pd.DataFrame(data)
            
        # 设置表格行和列
        self.table.setRowCount(self.df.shape[0])
        self.table.setColumnCount(self.df.shape[1])
        self.table.setHorizontalHeaderLabels(self.df.columns)
        
        # 填充数据
        for i in range(self.df.shape[0]):
            for j in range(self.df.shape[1]):
                value = self.df.iloc[i, j]
                item = QtWidgets.QTableWidgetItem(str(value))
                item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                
                # 根据数据类型设置对齐方式
                if isinstance(value, (int, float)):
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    
                self.table.setItem(i, j, item)
                
        self.table.resizeColumnsToContents()
        
    def get_selected_data(self):
        """获取选中的数据"""
        selected_rows = set()
        selected_cols = set()
        
        for item in self.table.selectedItems():
            selected_rows.add(item.row())
            selected_cols.add(item.column())
            
        if selected_rows and selected_cols:
            return self.df.iloc[sorted(selected_rows), sorted(selected_cols)]
        return None

class AdvancedControlPanel(QDockWidget):
    """高级控制面板"""
    def __init__(self, title="Advanced Control Panel", parent=None):
        super().__init__(title, parent)
        self.widget = QWidget()
        self.setWidget(self.widget)
        self.layout = QVBoxLayout(self.widget)
        
        # 创建可折叠分组
        self.setup_data_controls()
        self.setup_analysis_controls()
        self.setup_visualization_controls()
        self.setup_statistical_controls()
        self.setup_custom_functions()
        
    def setup_data_controls(self):
        """设置数据控制"""
        data_group = QGroupBox("Data Management")
        data_layout = QVBoxLayout(data_group)
        
        # 数据预处理选项
        preprocessing_layout = QHBoxLayout()
        preprocessing_layout.addWidget(QLabel("Preprocessing:"))
        self.preprocessing_combo = QComboBox()
        self.preprocessing_combo.addItems(["None", "Standardize", "Normalize", "Log Transform"])
        preprocessing_layout.addWidget(self.preprocessing_combo)
        data_layout.addLayout(preprocessing_layout)
        
        # 数据过滤
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Filter:"))
        self.filter_edit = QtWidgets.QLineEdit()
        self.filter_edit.setPlaceholderText("e.g., column > 0.5")
        filter_layout.addWidget(self.filter_edit)
        data_layout.addLayout(filter_layout)
        
        self.layout.addWidget(data_group)
        
    def setup_analysis_controls(self):
        """设置分析控制"""
        analysis_group = QGroupBox("Advanced Analysis")
        analysis_layout = QFormLayout(analysis_group)
        
        # 分析方法选择
        self.analysis_combo = QComboBox()
        self.analysis_combo.addItems(["PCA", "t-SNE", "K-Means", "Linear Regression", 
                                    "DBSCAN", "NMF", "Isomap", "MDS"])
        analysis_layout.addRow("Method:", self.analysis_combo)
        
        # 参数控制
        self.n_components_spin = QSpinBox()
        self.n_components_spin.setRange(1, 10)
        self.n_components_spin.setValue(2)
        analysis_layout.addRow("Components:", self.n_components_spin)
        
        self.n_clusters_spin = QSpinBox()
        self.n_clusters_spin.setRange(2, 20)
        self.n_clusters_spin.setValue(3)
        analysis_layout.addRow("Clusters:", self.n_clusters_spin)
        
        self.perplexity_spin = QSpinBox()
        self.perplexity_spin.setRange(5, 50)
        self.perplexity_spin.setValue(30)
        analysis_layout.addRow("Perplexity:", self.perplexity_spin)
        
        self.layout.addWidget(analysis_group)
        
    def setup_visualization_controls(self):
        """设置可视化控制"""
        vis_group = QGroupBox("Visualization Settings")
        vis_layout = QFormLayout(vis_group)
        
        # 绘图类型
        self.plot_type_combo = QComboBox()
        self.plot_type_combo.addItems(["Line", "Scatter", "Bar", "Histogram", 
                                      "Heatmap", "Contour", "Surface", "Error Bars"])
        vis_layout.addRow("Plot Type:", self.plot_type_combo)
        
        # 颜色映射
        self.colormap_combo = QComboBox()
        self.colormap_combo.addItems(["viridis", "plasma", "inferno", "magma", 
                                     "coolwarm", "rainbow", "jet"])
        vis_layout.addRow("Colormap:", self.colormap_combo)
        
        # 点大小
        self.point_size_slider = QSlider(Qt.Horizontal)
        self.point_size_slider.setRange(1, 20)
        self.point_size_slider.setValue(5)
        vis_layout.addRow("Point Size:", self.point_size_slider)
        
        # 线宽
        self.line_width_slider = QSlider(Qt.Horizontal)
        self.line_width_slider.setRange(1, 10)
        self.line_width_slider.setValue(2)
        vis_layout.addRow("Line Width:", self.line_width_slider)
        
        self.layout.addWidget(vis_group)
        
    def setup_statistical_controls(self):
        """设置统计控制"""
        stats_group = QGroupBox("Statistical Analysis")
        stats_layout = QFormLayout(stats_group)
        
        # 统计测试
        self.stats_test_combo = QComboBox()
        self.stats_test_combo.addItems(["t-test", "ANOVA", "Correlation", 
                                       "Regression", "Distribution Fit"])
        stats_layout.addRow("Test:", self.stats_test_combo)
        
        # 置信区间
        self.confidence_spin = QDoubleSpinBox()
        self.confidence_spin.setRange(0.8, 0.99)
        self.confidence_spin.setValue(0.95)
        self.confidence_spin.setSingleStep(0.01)
        stats_layout.addRow("Confidence:", self.confidence_spin)
        
        self.layout.addWidget(stats_group)
        
    def setup_custom_functions(self):
        """设置自定义函数"""
        func_group = QGroupBox("Custom Functions")
        func_layout = QVBoxLayout(func_group)
        
        # 函数输入
        self.function_edit = QtWidgets.QTextEdit()
        self.function_edit.setMaximumHeight(80)
        self.function_edit.setPlaceholderText("Enter custom function (Python syntax)...")
        func_layout.addWidget(self.function_edit)
        
        # 执行按钮
        self.execute_func_btn = QPushButton("Execute Function")
        func_layout.addWidget(self.execute_func_btn)
        
        self.layout.addWidget(func_group)

class StatisticsPanel(QDockWidget):
    """统计信息面板"""
    def __init__(self, title="Statistics", parent=None):
        super().__init__(title, parent)
        self.widget = QWidget()
        self.setWidget(self.widget)
        self.layout = QVBoxLayout(self.widget)
        
        # 创建统计信息显示
        self.stats_text = QTextEdit()
        self.stats_text.setReadOnly(True)
        self.stats_text.setFont(QFont("Courier", 9))
        
        self.layout.addWidget(self.stats_text)
        
    def update_statistics(self, data):
        """更新统计信息"""
        if data is None or len(data) == 0:
            self.stats_text.setText("No data available")
            return
            
        if isinstance(data, pd.DataFrame):
            # 只选择数值列进行统计
            numeric_data = data.select_dtypes(include=[np.number])
            
            if not numeric_data.empty:
                stats_desc = numeric_data.describe().to_string()
                
                # 只有多于一列数值数据时才计算相关性矩阵
                if numeric_data.shape[1] > 1:
                    corr_matrix = numeric_data.corr().to_string()
                else:
                    corr_matrix = "Not enough numeric columns for correlation matrix"
            else:
                stats_desc = "No numeric columns available"
                corr_matrix = "No numeric columns available"
            
            # 非数值列的统计信息
            non_numeric_data = data.select_dtypes(exclude=[np.number])
            non_numeric_info = ""
            if not non_numeric_data.empty:
                non_numeric_info = "\n\nNON-NUMERIC COLUMNS:\n"
                for col in non_numeric_data.columns:
                    unique_vals = data[col].nunique()
                    non_numeric_info += f"{col}: {unique_vals} unique values\n"
            
            stats_info = f"""DESCRIPTIVE STATISTICS (numeric columns only):
{stats_desc}

CORRELATION MATRIX (numeric columns only):
{corr_matrix}
{non_numeric_info}
SHAPE: {data.shape}
MEMORY USAGE: {data.memory_usage(deep=True).sum()} bytes"""
            
            self.stats_text.setText(stats_info)

class PDTAdvancedVisualizationTool(QMainWindow):
    """高级PDT可视化工具主窗口"""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Advanced PDT Visualization Tool v2.0")
        self.setGeometry(100, 100, 1600, 1000)
        
        # 初始化数据
        self.data = None
        self.current_plot_data = None
        self.analysis_results = {}
        
        # 创建UI
        self.create_ui()
        
        # 生成示例数据
        self.generate_sample_data()
        
        # 设置样式
        self.apply_stylesheet()
        
    def create_ui(self):
        """创建用户界面"""
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.main_layout = QHBoxLayout(central_widget)
        
        # 创建主分割器
        main_splitter = QSplitter(Qt.Horizontal)
        self.main_layout.addWidget(main_splitter)
        
        # 创建左侧分割器（绘图区域）
        left_splitter = QSplitter(Qt.Vertical)
        main_splitter.addWidget(left_splitter)
        
        # 创建绘图区域
        self.plot_widget = EnhancedPlotWidget()
        left_splitter.addWidget(self.plot_widget)
        
        # 创建数据表格
        self.data_table = EnhancedDataTable()
        left_splitter.addWidget(self.data_table)
        
        # 设置左侧分割器比例
        left_splitter.setSizes([600, 400])
        
        # 创建右侧面板
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # 创建控制面板
        self.control_panel = AdvancedControlPanel()
        right_layout.addWidget(self.control_panel.widget)
        
        main_splitter.addWidget(right_panel)
        
        # 设置主分割器比例
        main_splitter.setSizes([1000, 400])
        
        # 创建统计信息面板
        self.stats_panel = StatisticsPanel()
        self.addDockWidget(Qt.RightDockWidgetArea, self.stats_panel)
        
        # 创建工具栏
        self.create_toolbar()
        
        # 创建状态栏
        self.create_statusbar()
        
        # 连接信号和槽
        self.connect_signals()
        
    def create_toolbar(self):
        """创建工具栏"""
        # 主工具栏
        main_toolbar = QToolBar("Main Toolbar")
        main_toolbar.setIconSize(QtCore.QSize(24, 24))
        self.addToolBar(main_toolbar)
        
        # 文件操作
        open_action = QAction(QIcon.fromTheme("document-open"), "Open", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.open_file)
        main_toolbar.addAction(open_action)
        
        save_action = QAction(QIcon.fromTheme("document-save"), "Save", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.save_data)
        main_toolbar.addAction(save_action)
        
        save_plot_action = QAction(QIcon.fromTheme("image-x-generic"), "Save Plot", self)
        save_plot_action.setShortcut("Ctrl+Shift+S")
        save_plot_action.triggered.connect(self.save_plot)
        main_toolbar.addAction(save_plot_action)
        
        main_toolbar.addSeparator()
        
        # 数据操作
        generate_action = QAction(QIcon.fromTheme("document-new"), "Generate Data", self)
        generate_action.triggered.connect(self.generate_sample_data)
        main_toolbar.addAction(generate_action)
        
        import_action = QAction(QIcon.fromTheme("document-import"), "Import", self)
        import_action.triggered.connect(self.import_data)
        main_toolbar.addAction(import_action)
        
        export_action = QAction(QIcon.fromTheme("document-export"), "Export", self)
        export_action.triggered.connect(self.export_data)
        main_toolbar.addAction(export_action)
        
        main_toolbar.addSeparator()
        
        # 分析操作
        analyze_action = QAction(QIcon.fromTheme("document-properties"), "Analyze", self)
        analyze_action.triggered.connect(self.analyze_data)
        main_toolbar.addAction(analyze_action)
        
        plot_action = QAction(QIcon.fromTheme("office-chart-line"), "Plot", self)
        plot_action.triggered.connect(self.plot_data)
        main_toolbar.addAction(plot_action)
        
        clear_action = QAction(QIcon.fromTheme("edit-clear"), "Clear", self)
        clear_action.triggered.connect(self.clear_all)
        main_toolbar.addAction(clear_action)
        
        # 添加第二个工具栏用于快速操作
        quick_toolbar = QToolBar("Quick Tools")
        self.addToolBar(quick_toolbar)
        
        # 快速绘图类型
        quick_toolbar.addWidget(QLabel("Quick Plot:"))
        self.quick_plot_combo = QComboBox()
        self.quick_plot_combo.addItems(["Line", "Scatter", "Histogram", "Heatmap"])
        quick_toolbar.addWidget(self.quick_plot_combo)
        
        quick_plot_btn = QPushButton("Quick Plot")
        quick_plot_btn.clicked.connect(self.quick_plot)
        quick_toolbar.addWidget(quick_plot_btn)
        
    def create_statusbar(self):
        """创建状态栏"""
        self.status_bar = self.statusBar()
        
        # 添加进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(200)
        self.progress_bar.setVisible(False)
        self.status_bar.addPermanentWidget(self.progress_bar)
        
        # 添加状态标签
        self.status_label = QLabel("Ready")
        self.status_bar.addPermanentWidget(self.status_label)
        
        self.status_bar.showMessage("Application started successfully")
        
    def connect_signals(self):
        """连接信号和槽"""
        # 控制面板信号
        self.control_panel.execute_func_btn.clicked.connect(self.execute_custom_function)
        
        # 数据表格信号
        self.data_table.filter_btn.clicked.connect(self.filter_data)
        self.data_table.stats_btn.clicked.connect(self.show_detailed_statistics)
        self.data_table.export_btn.clicked.connect(self.export_selected_data)
        
        # 绘图部件信号
        self.plot_widget.save_plot_btn.clicked.connect(self.save_plot)
        self.plot_widget.auto_range_btn.clicked.connect(self.auto_range_plots)
        
    def apply_stylesheet(self):
        """应用样式表"""
        style = """
        QMainWindow {
            background-color: #F0F0F0;
        }
        QToolBar {
            background-color: #E0E0E0;
            border: none;
            spacing: 3px;
            padding: 2px;
        }
        QDockWidget {
            titlebar-close-icon: url(close.png);
            titlebar-normal-icon: url(float.png);
        }
        QDockWidget::title {
            background-color: #D0D0D0;
            padding: 4px;
            text-align: center;
        }
        QGroupBox {
            font-weight: bold;
            border: 1px solid #CCCCCC;
            border-radius: 4px;
            margin-top: 1ex;
            padding-top: 10px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top center;
            padding: 0 5px;
        }
        """
        self.setStyleSheet(style)
        
    def open_file(self):
        """打开文件"""
        options = QFileDialog.Options()
        file_name, selected_filter = QFileDialog.getOpenFileName(
            self, "Open Data File", "", 
            "All Supported Files (*.csv *.txt *.xlsx *.xls *.h5 *.hdf5 *.json *.pkl *.npy);;"
            "CSV Files (*.csv);;Excel Files (*.xlsx *.xls);;HDF5 Files (*.h5 *.hdf5);;"
            "JSON Files (*.json);;Pickle Files (*.pkl);;NumPy Files (*.npy);;All Files (*)",
            options=options
        )
        
        if file_name:
            try:
                self.status_bar.showMessage(f"Loading {file_name}...")
                self.progress_bar.setVisible(True)
                self.progress_bar.setValue(0)
                
                # 根据文件类型加载数据
                if file_name.endswith(('.csv', '.txt')):
                    self.data = pd.read_csv(file_name)
                elif file_name.endswith(('.xlsx', '.xls')):
                    self.data = pd.read_excel(file_name)
                elif file_name.endswith(('.h5', '.hdf5')):
                    with h5py.File(file_name, 'r') as f:
                        # 尝试读取第一个数据集
                        dataset_name = list(f.keys())[0]
                        self.data = pd.DataFrame(f[dataset_name][:])
                elif file_name.endswith('.json'):
                    with open(file_name, 'r') as f:
                        json_data = json.load(f)
                        self.data = pd.DataFrame(json_data)
                elif file_name.endswith('.pkl'):
                    with open(file_name, 'rb') as f:
                        self.data = pickle.load(f)
                elif file_name.endswith('.npy'):
                    array_data = np.load(file_name)
                    self.data = pd.DataFrame(array_data)
                
                self.progress_bar.setValue(100)
                QTimer.singleShot(500, lambda: self.progress_bar.setVisible(False))
                
                # 加载数据到表格和统计面板
                self.data_table.load_data(self.data)
                self.stats_panel.update_statistics(self.data)
                
                self.status_bar.showMessage(f"Successfully loaded {file_name}")
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load file: {str(e)}")
                self.status_bar.showMessage(f"Error loading file: {str(e)}")
                
    def save_data(self):
        """保存数据"""
        if self.data is None:
            QMessageBox.warning(self, "Warning", "No data to save")
            return
            
        options = QFileDialog.Options()
        file_name, selected_filter = QFileDialog.getSaveFileName(
            self, "Save Data", "", 
            "CSV Files (*.csv);;Excel Files (*.xlsx);;JSON Files (*.json);;"
            "Pickle Files (*.pkl);;HDF5 Files (*.h5)",
            options=options
        )
        
        if file_name:
            try:
                if file_name.endswith('.csv'):
                    self.data.to_csv(file_name, index=False)
                elif file_name.endswith('.xlsx'):
                    self.data.to_excel(file_name, index=False)
                elif file_name.endswith('.json'):
                    self.data.to_json(file_name, orient='records', indent=2)
                elif file_name.endswith('.pkl'):
                    self.data.to_pickle(file_name)
                elif file_name.endswith('.h5'):
                    self.data.to_hdf(file_name, key='data', mode='w')
                    
                self.status_bar.showMessage(f"Data saved to {file_name}")
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save file: {str(e)}")
                
    def save_plot(self):
        """保存绘图"""
        options = QFileDialog.Options()
        file_name, selected_filter = QFileDialog.getSaveFileName(
            self, "Save Plot", "", 
            "PNG Files (*.png);;JPEG Files (*.jpg);;PDF Files (*.pdf);;"
            "SVG Files (*.svg);;TIFF Files (*.tiff)",
            options=options
        )
        
        if file_name:
            try:
                # 获取当前活动的标签页
                current_tab = self.plot_widget.tab_widget.currentIndex()
                
                if current_tab == 0:  # PyQtGraph
                    exporter = pg.exporters.ImageExporter(self.plot_widget.pg_plot.plotItem)
                    exporter.export(file_name)
                elif current_tab == 1:  # Matplotlib
                    self.plot_widget.mpl_canvas.fig.savefig(file_name, dpi=300, 
                                                          bbox_inches='tight')
                    
                self.status_bar.showMessage(f"Plot saved to {file_name}")
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save plot: {str(e)}")
                
    def generate_sample_data(self):
        """生成示例数据"""
        np.random.seed(42)
        
        # 生成更丰富的示例数据
        n_points = 200
        x = np.linspace(0, 10, n_points)
        
        # 多种信号组合
        y_sin = np.sin(x) + np.random.normal(0, 0.1, n_points)
        y_cos = np.cos(x) + np.random.normal(0, 0.1, n_points)
        y_exp = np.exp(-x/3) + np.random.normal(0, 0.05, n_points)
        y_poly = 0.1*x**2 - x + 2 + np.random.normal(0, 0.2, n_points)
        
        # 分类数据
        categories = np.random.choice(['A', 'B', 'C'], n_points)
        values = np.random.normal(0, 1, n_points) + \
                (categories == 'B') * 1.5 + (categories == 'C') * 2.5
        
        # 创建DataFrame
        self.data = pd.DataFrame({
            'x': x,
            'sin(x)': y_sin,
            'cos(x)': y_cos,
            'exp(-x/3)': y_exp,
            'poly(x)': y_poly,
            'category': categories,
            'values': values
        })
        
        # 加载到表格和统计面板
        self.data_table.load_data(self.data)
        self.stats_panel.update_statistics(self.data)
        
        self.status_bar.showMessage("Generated rich sample dataset")
        
    def analyze_data(self):
        """分析数据"""
        if self.data is None:
            QMessageBox.warning(self, "Warning", "No data to analyze")
            return
            
        method = self.control_panel.analysis_combo.currentText()
        params = {
            'n_components': self.control_panel.n_components_spin.value(),
            'n_clusters': self.control_panel.n_clusters_spin.value(),
            'perplexity': self.control_panel.perplexity_spin.value()
        }
        
        # 准备数据（排除非数值列）
        numeric_data = self.data.select_dtypes(include=[np.number]).values
        
        if len(numeric_data) == 0:
            QMessageBox.warning(self, "Warning", "No numeric data to analyze")
            return
            
        # 创建进度对话框
        progress_dialog = QProgressDialog(f"Performing {method}...", "Cancel", 0, 100, self)
        progress_dialog.setWindowTitle("Analysis Progress")
        progress_dialog.setWindowModality(Qt.WindowModal)
        progress_dialog.show()
        
        # 创建工作线程
        self.analysis_worker = AnalysisWorker(numeric_data, method, params)
        self.analysis_worker.progress.connect(progress_dialog.setValue)
        self.analysis_worker.finished.connect(
            lambda result: self.on_analysis_finished(result, method, progress_dialog))
        self.analysis_worker.error.connect(
            lambda error: self.on_analysis_error(error, progress_dialog))
        
        self.analysis_worker.start()
        
    def on_analysis_finished(self, result, method, progress_dialog):
        """分析完成回调"""
        progress_dialog.close()
        self.analysis_results[method] = result
        self.current_plot_data = result.get('result', result.get('labels', None))
        
        # 显示结果信息
        if 'explained_variance' in result:
            variance_info = "Explained variance: " + \
                           ", ".join([f"{v*100:.1f}%" for v in result['explained_variance']])
            self.status_bar.showMessage(f"{method} completed. {variance_info}")
        else:
            self.status_bar.showMessage(f"{method} analysis completed")
            
        # 如果是聚类分析，用不同颜色显示结果
        if 'labels' in result:
            self.plot_cluster_results(result)
            
    def on_analysis_error(self, error, progress_dialog):
        """分析错误回调"""
        progress_dialog.close()
        QMessageBox.critical(self, "Analysis Error", f"Analysis failed: {error}")
        
    def plot_cluster_results(self, result):
        """绘制聚类结果"""
        labels = result['labels']
        unique_labels = np.unique(labels)
        
        # 为每个簇分配颜色
        colors = plt.cm.Set3(np.linspace(0, 1, len(unique_labels)))
        
        # 绘制散点图
        numeric_data = self.data.select_dtypes(include=[np.number]).values
        x = numeric_data[:, 0]
        y = numeric_data[:, 1] if numeric_data.shape[1] > 1 else np.zeros_like(x)
        
        self.plot_widget.pg_plot.clear()
        for i, label in enumerate(unique_labels):
            mask = labels == label
            color = tuple(int(c * 255) for c in colors[i][:3])
            self.plot_widget.plot_scatter(x[mask], y[mask], 
                                        label=f"Cluster {label}", color=color)
            
    def plot_data(self):
        """绘制数据"""
        if self.data is None:
            QMessageBox.warning(self, "Warning", "No data to plot")
            return
            
        plot_type = self.control_panel.plot_type_combo.currentText().lower()
        colormap = self.control_panel.colormap_combo.currentText()
        
        # 获取数值数据
        numeric_data = self.data.select_dtypes(include=[np.number])
        
        if plot_type == "line":
            self.plot_line_data(numeric_data)
        elif plot_type == "scatter":
            self.plot_scatter_data(numeric_data)
        elif plot_type == "histogram":
            self.plot_histogram_data(numeric_data)
        elif plot_type == "heatmap":
            self.plot_heatmap_data(numeric_data)
            
    def plot_line_data(self, data):
        """绘制线图"""
        x = data.iloc[:, 0].values
        for i in range(1, min(6, data.shape[1])):  # 最多绘制5条线
            y = data.iloc[:, i].values
            self.plot_widget.plot_line(x, y, label=data.columns[i])
            
    def plot_scatter_data(self, data):
        """绘制散点图"""
        if data.shape[1] >= 2:
            x = data.iloc[:, 0].values
            y = data.iloc[:, 1].values
            self.plot_widget.plot_scatter(x, y, label=f"{data.columns[0]} vs {data.columns[1]}")
            
    def plot_histogram_data(self, data):
        """绘制直方图"""
        for i in range(min(4, data.shape[1])):  # 最多绘制4个直方图
            self.plot_widget.plot_histogram(data.iloc[:, i].values, 
                                          label=data.columns[i])
            
    def plot_heatmap_data(self, data):
        """绘制热力图"""
        # 计算相关性矩阵
        corr_matrix = data.corr()
        
        # 创建热力图
        plt.figure(figsize=(8, 6))
        sns.heatmap(corr_matrix, annot=True, cmap='coolwarm', center=0)
        plt.tight_layout()
        plt.show()
        
    def quick_plot(self):
        """快速绘图"""
        plot_type = self.quick_plot_combo.currentText().lower()
        
        if self.data is not None:
            if plot_type == "line":
                self.plot_line_data(self.data.select_dtypes(include=[np.number]))
            elif plot_type == "scatter":
                self.plot_scatter_data(self.data.select_dtypes(include=[np.number]))
            elif plot_type == "histogram":
                self.plot_histogram_data(self.data.select_dtypes(include=[np.number]))
            elif plot_type == "heatmap":
                self.plot_heatmap_data(self.data.select_dtypes(include=[np.number]))
                
    def filter_data(self):
        """过滤数据"""
        if self.data is None:
            return
            
        filter_text = self.control_panel.filter_edit.text()
        if filter_text:
            try:
                # 简单的过滤实现（实际应用中需要更复杂的解析）
                filtered_data = self.data.query(filter_text)
                self.data_table.load_data(filtered_data)
                self.status_bar.showMessage(f"Filtered data: {len(filtered_data)} rows")
            except:
                QMessageBox.warning(self, "Warning", "Invalid filter expression")
                
    def show_detailed_statistics(self):
        """显示详细统计信息"""
        if self.data is not None:
            # 创建详细的统计信息对话框
            stats_dialog = QDialog(self)
            stats_dialog.setWindowTitle("Detailed Statistics")
            stats_dialog.resize(600, 400)
            
            layout = QVBoxLayout(stats_dialog)
            
            stats_text = QTextEdit()
            stats_text.setFont(QFont("Courier", 9))
            stats_text.setReadOnly(True)
            
            # 生成详细统计信息
            stats_info = self.generate_detailed_statistics()
            stats_text.setText(stats_info)
            
            layout.addWidget(stats_text)
            
            # 添加按钮
            button_box = QDialogButtonBox(QDialogButtonBox.Ok)
            button_box.accepted.connect(stats_dialog.accept)
            layout.addWidget(button_box)
            
            stats_dialog.exec_()
            
    def generate_detailed_statistics(self):
        """生成详细统计信息"""
        if self.data is None:
            return "No data available"
            
        numeric_data = self.data.select_dtypes(include=[np.number])
        non_numeric_data = self.data.select_dtypes(exclude=[np.number])
        stats_info = []
        
        stats_info.append("="*50)
        stats_info.append("DETAILED STATISTICAL ANALYSIS")
        stats_info.append("="*50)
        stats_info.append(f"Dataset shape: {self.data.shape}")
        stats_info.append(f"Memory usage: {self.data.memory_usage(deep=True).sum()} bytes")
        stats_info.append("")
        
        stats_info.append("DESCRIPTIVE STATISTICS (numeric columns):")
        stats_info.append("="*30)
        if not numeric_data.empty:
            stats_info.append(numeric_data.describe().to_string())
        else:
            stats_info.append("No numeric columns available")
        stats_info.append("")
        
        stats_info.append("CORRELATION MATRIX (numeric columns):")
        stats_info.append("="*30)
        if not numeric_data.empty and numeric_data.shape[1] > 1:
            stats_info.append(numeric_data.corr().to_string())
        else:
            stats_info.append("Not enough numeric columns for correlation matrix")
        stats_info.append("")
        
        stats_info.append("NON-NUMERIC COLUMNS:")
        stats_info.append("="*30)
        if not non_numeric_data.empty:
            for col in non_numeric_data.columns:
                unique_vals = self.data[col].nunique()
                stats_info.append(f"{col}: {unique_vals} unique values")
        else:
            stats_info.append("No non-numeric columns")
            
        return "\n".join(stats_info)
        
    def export_selected_data(self):
        """导出选中的数据"""
        selected_data = self.data_table.get_selected_data()
        if selected_data is None or selected_data.empty:
            QMessageBox.warning(self, "Warning", "No data selected")
            return
            
        options = QFileDialog.Options()
        file_name, selected_filter = QFileDialog.getSaveFileName(
            self, "Export Selected Data", "", 
            "CSV Files (*.csv);;Excel Files (*.xlsx);;JSON Files (*.json)",
            options=options
        )
        
        if file_name:
            try:
                if file_name.endswith('.csv'):
                    selected_data.to_csv(file_name, index=False)
                elif file_name.endswith('.xlsx'):
                    selected_data.to_excel(file_name, index=False)
                elif file_name.endswith('.json'):
                    selected_data.to_json(file_name, orient='records', indent=2)
                    
                self.status_bar.showMessage(f"Exported selected data to {file_name}")
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to export data: {str(e)}")
                
    def execute_custom_function(self):
        """执行自定义函数"""
        function_text = self.control_panel.function_edit.toPlainText()
        if not function_text.strip():
            QMessageBox.warning(self, "Warning", "No function provided")
            return
            
        try:
            # 在安全的环境中执行函数
            local_vars = {'data': self.data, 'np': np, 'pd': pd, 'plt': plt}
            exec(function_text, globals(), local_vars)
            
            # 检查是否有结果
            if 'result' in local_vars:
                result = local_vars['result']
                if isinstance(result, (pd.DataFrame, np.ndarray)):
                    self.data_table.load_data(result)
                    self.status_bar.showMessage("Custom function executed successfully")
                else:
                    QMessageBox.information(self, "Result", f"Function result: {result}")
            else:
                self.status_bar.showMessage("Custom function executed (no result returned)")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Function execution failed: {str(e)}")
            
    def import_data(self):
        """导入数据"""
        # 实现从数据库、API等导入数据的功能
        QMessageBox.information(self, "Info", "Import functionality would be implemented here")
        
    def export_data(self):
        """导出数据"""
        # 实现导出到各种格式的功能
        self.save_data()
        
    def auto_range_plots(self):
        """自动调整绘图范围"""
        self.plot_widget.pg_plot.autoRange()
        self.plot_widget.mpl_canvas.axes.relim()
        self.plot_widget.mpl_canvas.axes.autoscale_view()
        self.plot_widget.mpl_canvas.draw()
        
    def clear_all(self):
        """清除所有内容"""
        self.plot_widget.clear_all()
        if self.data is not None:
            self.data_table.load_data(self.data)  # 重新加载原始数据
        self.status_bar.showMessage("All plots cleared")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 设置应用程序样式
    app.setStyle('Fusion')
    
    # 设置应用程序字体
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    
    # 创建并显示主窗口
    window = PDTAdvancedVisualizationTool()
    window.show()
    
    sys.exit(app.exec_())