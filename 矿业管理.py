import sys
import numpy as np
import pandas as pd
from PyQt5.QtCore import Qt, QTimer, QDateTime
from PyQt5.QtGui import QColor, QFont, QIcon, QPixmap, QPainter
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QSplitter, QTabWidget, QToolBar, QStatusBar, QAction, QToolButton,
                             QLabel, QComboBox, QSpinBox, QDoubleSpinBox, QSlider, QProgressBar,
                             QMessageBox, QFileDialog, QDockWidget, QTreeWidget, QTreeWidgetItem,
                             QListWidget, QTableWidget, QTableWidgetItem, QHeaderView, 
                             QGraphicsView, QGraphicsScene, QGraphicsItem, QGraphicsEllipseItem,
                             QGraphicsLineItem, QGraphicsTextItem, QGroupBox,
                             QFormLayout, QCheckBox, QRadioButton, QButtonGroup, QTextEdit,
                             QPushButton, QFrame, QSizePolicy, QStyleFactory, QDialog)

from PyQt5.QtChart import QChart, QChartView, QLineSeries, QValueAxis, QDateTimeAxis
import matplotlib
matplotlib.rc("font", family='Microsoft YaHei')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d import Axes3D
from matplotlib import cm

from scipy import stats
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings('ignore')


class MineralResourceCalculator:
    """矿产资源计算工具类"""
    
    def __init__(self):
        self.resource_data = {}
        
    def calculate_volume(self, area, thickness):
        """计算矿体体积"""
        return area * thickness
        
    def calculate_tonnage(self, volume, density):
        """计算矿石吨位"""
        return volume * density
        
    def estimate_reserves(self, tonnage, recovery_rate, dilution_rate):
        """估算可采储量"""
        recoverable = tonnage * recovery_rate
        diluted = recoverable * (1 - dilution_rate)
        return diluted
        
    def grade_estimation(self, samples, method='idw', power=2):
        """品位估算方法"""
        if method == 'idw':
            return self.inverse_distance_weighting(samples, power)
        elif method == 'kriging':
            return self.kriging(samples)
        else:
            return self.polygonal_method(samples)
            
    def inverse_distance_weighting(self, samples, power=2):
        """反距离加权插值法"""
        # 简化的IDW实现
        if len(samples) == 0:
            return 0
            
        total_weight = 0
        weighted_sum = 0
        
        for x, y, value in samples:
            distance = np.sqrt(x**2 + y**2)
            if distance == 0:
                return value
            weight = 1 / (distance ** power)
            weighted_sum += value * weight
            total_weight += weight
            
        return weighted_sum / total_weight if total_weight > 0 else 0
        
    def kriging(self, samples):
        """克里金插值法"""
        # 简化的克里金实现
        if len(samples) == 0:
            return 0
            
        values = [value for _, _, value in samples]
        return np.mean(values)
        
    def polygonal_method(self, samples):
        """多边形法"""
        if len(samples) == 0:
            return 0
            
        values = [value for _, _, value in samples]
        return np.mean(values)


class Geological3DVisualization(QWidget):
    """地质3D可视化组件 - 使用matplotlib实现"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.data = None
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # 创建控制面板
        control_panel = QWidget()
        control_layout = QHBoxLayout(control_panel)
        
        # 可视化类型选择
        control_layout.addWidget(QLabel("可视化类型:"))
        self.viz_type = QComboBox()
        self.viz_type.addItems(["表面图", "线框图", "散点图", "等高线图"])
        self.viz_type.currentTextChanged.connect(self.update_plot)
        control_layout.addWidget(self.viz_type)
        
        # 颜色映射选择
        control_layout.addWidget(QLabel("颜色映射:"))
        self.cmap_selector = QComboBox()
        self.cmap_selector.addItems(["viridis", "plasma", "inferno", "magma", "coolwarm", "jet"])
        self.cmap_selector.currentTextChanged.connect(self.update_plot)
        control_layout.addWidget(self.cmap_selector)
        
        # 数据生成按钮
        self.generate_btn = QPushButton("生成示例数据")
        self.generate_btn.clicked.connect(self.generate_sample_data)
        control_layout.addWidget(self.generate_btn)
        
        # 加载数据按钮
        self.load_btn = QPushButton("加载数据")
        self.load_btn.clicked.connect(self.load_data)
        control_layout.addWidget(self.load_btn)
        
        control_layout.addStretch()
        
        layout.addWidget(control_panel)
        
        # 创建matplotlib图形
        self.figure = Figure(figsize=(10, 8), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        
        # 添加matplotlib工具栏
        self.toolbar = NavigationToolbar(self.canvas, self)
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)
        
        # 生成初始示例数据
        self.generate_sample_data()
        
    def generate_sample_data(self):
        """生成示例地质数据"""
        x = np.linspace(-5, 5, 100)
        y = np.linspace(-5, 5, 100)
        X, Y = np.meshgrid(x, y)
        
        # 创建多个地质构造的合成数据
        Z1 = np.sin(np.sqrt(X**2 + Y**2))  # 圆形构造
        Z2 = 0.5 * np.sin(2*X) * np.cos(2*Y)  # 波状构造
        Z3 = 0.3 * np.exp(-(X**2 + Y**2)/4)  # 高斯构造
        
        # 添加一些随机噪声模拟实际地质数据
        noise = np.random.normal(0, 0.1, X.shape)
        
        self.data = Z1 + Z2 + Z3 + noise
        self.X, self.Y = X, Y
        self.update_plot()
        
    def load_data(self):
        """从文件加载数据"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "打开数据文件", "", "CSV文件 (*.csv);;NPY文件 (*.npy);;所有文件 (*)"
        )
        
        if file_path:
            try:
                if file_path.endswith('.csv'):
                    df = pd.read_csv(file_path)
                    # 假设CSV有三列：x, y, z
                    if len(df.columns) >= 3:
                        x = df.iloc[:, 0].values
                        y = df.iloc[:, 1].values
                        z = df.iloc[:, 2].values
                        
                        # 转换为网格数据
                        # 这里需要根据实际数据格式进行调整
                        # 简化的处理：如果数据已经是网格格式
                        grid_size = int(np.sqrt(len(x)))
                        if grid_size**2 == len(x):
                            self.X = x.reshape(grid_size, grid_size)
                            self.Y = y.reshape(grid_size, grid_size)
                            self.data = z.reshape(grid_size, grid_size)
                            self.update_plot()
                        else:
                            QMessageBox.warning(self, "警告", "数据格式不支持，请使用网格数据")
                    
                elif file_path.endswith('.npy'):
                    data = np.load(file_path)
                    if data.ndim == 2:
                        self.data = data
                        x = np.arange(data.shape[1])
                        y = np.arange(data.shape[0])
                        self.X, self.Y = np.meshgrid(x, y)
                        self.update_plot()
                    else:
                        QMessageBox.warning(self, "警告", "请提供2D数组数据")
                        
            except Exception as e:
                QMessageBox.critical(self, "错误", f"加载数据时出错: {str(e)}")
                
    def update_plot(self):
        """更新3D绘图"""
        if self.data is None:
            return
            
        self.figure.clear()
        viz_type = self.viz_type.currentText()
        cmap = self.cmap_selector.currentText()
        
        ax = self.figure.add_subplot(111, projection='3d')
        
        try:
            if viz_type == "表面图":
                surf = ax.plot_surface(self.X, self.Y, self.data, cmap=cmap, 
                                      alpha=0.8, antialiased=True)
                self.figure.colorbar(surf, ax=ax, shrink=0.5, aspect=5)
                
            elif viz_type == "线框图":
                ax.plot_wireframe(self.X, self.Y, self.data, color='blue', 
                                 alpha=0.6, linewidth=0.5)
                
            elif viz_type == "散点图":
                # 从网格数据中采样部分点显示
                stride = max(1, self.X.shape[0] // 20)
                X_sample = self.X[::stride, ::stride].flatten()
                Y_sample = self.Y[::stride, ::stride].flatten()
                Z_sample = self.data[::stride, ::stride].flatten()
                
                scatter = ax.scatter(X_sample, Y_sample, Z_sample, 
                                   c=Z_sample, cmap=cmap, s=20)
                self.figure.colorbar(scatter, ax=ax, shrink=0.5, aspect=5)
                
            elif viz_type == "等高线图":
                contour = ax.contour3D(self.X, self.Y, self.data, 50, cmap=cmap)
                self.figure.colorbar(contour, ax=ax, shrink=0.5, aspect=5)
                
            ax.set_xlabel('X坐标')
            ax.set_ylabel('Y坐标')
            ax.set_zlabel('高程/深度')
            ax.set_title('地质3D可视化')
            
            self.canvas.draw()
            
        except Exception as e:
            QMessageBox.critical(self, "绘图错误", f"绘制3D图形时出错: {str(e)}")


class RealTimeMonitor(QWidget):
    """增强的实时监控面板"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.data = {}
        self.timestamps = []
        self.max_data_points = 100
        self.monitoring = False
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # 创建控制面板
        control_panel = QWidget()
        control_layout = QHBoxLayout(control_panel)
        
        # 监控参数设置
        control_layout.addWidget(QLabel("监控参数:"))
        self.param_selector = QComboBox()
        self.param_selector.addItems(["产量", "效率", "能耗", "设备状态", "安全指标"])
        control_layout.addWidget(self.param_selector)
        
        # 数据源选择
        control_layout.addWidget(QLabel("数据源:"))
        self.source_selector = QComboBox()
        self.source_selector.addItems(["模拟数据", "文件数据", "实时传感器"])
        control_layout.addWidget(self.source_selector)
        
        # 监控按钮
        self.start_button = QPushButton("开始监控")
        self.stop_button = QPushButton("停止监控")
        self.reset_button = QPushButton("重置数据")
        self.export_button = QPushButton("导出数据")
        
        self.start_button.clicked.connect(self.start_monitoring)
        self.stop_button.clicked.connect(self.stop_monitoring)
        self.reset_button.clicked.connect(self.reset_data)
        self.export_button.clicked.connect(self.export_data)
        
        control_layout.addWidget(self.start_button)
        control_layout.addWidget(self.stop_button)
        control_layout.addWidget(self.reset_button)
        control_layout.addWidget(self.export_button)
        
        control_layout.addStretch()
        
        layout.addWidget(control_panel)
        
        # 创建图表区域
        chart_container = QWidget()
        chart_layout = QHBoxLayout(chart_container)
        
        # 主图表
        self.chart = QChart()
        self.chart.setTitle("实时生产监控")
        self.chart.legend().setVisible(True)
        
        # 创建多个数据系列
        self.series = {}
        parameters = ["产量", "效率", "能耗", "设备状态", "安全指标"]
        colors = [Qt.red, Qt.blue, Qt.green, Qt.yellow, Qt.magenta]
        
        for param, color in zip(parameters, colors):
            series = QLineSeries()
            series.setName(param)
            series.setColor(color)
            self.series[param] = series
            self.chart.addSeries(series)
        
        # 创建坐标轴
        self.axis_x = QDateTimeAxis()
        self.axis_x.setFormat("hh:mm:ss")
        self.axis_x.setTitleText("时间")
        
        self.axis_y = QValueAxis()
        self.axis_y.setTitleText("数值")
        self.axis_y.setRange(0, 100)
        
        self.chart.addAxis(self.axis_x, Qt.AlignBottom)
        self.chart.addAxis(self.axis_y, Qt.AlignLeft)
        
        for series in self.series.values():
            series.attachAxis(self.axis_x)
            series.attachAxis(self.axis_y)
        
        self.chart_view = QChartView(self.chart)
        chart_layout.addWidget(self.chart_view)
        
        # 右侧统计信息
        stats_panel = QWidget()
        stats_panel.setMaximumWidth(200)
        stats_layout = QVBoxLayout(stats_panel)
        
        self.stats_label = QLabel("统计信息")
        self.stats_label.setFont(QFont("Arial", 12, QFont.Bold))
        stats_layout.addWidget(self.stats_label)
        
        self.stats_text = QTextEdit()
        self.stats_text.setMaximumHeight(200)
        stats_layout.addWidget(self.stats_text)
        
        # 报警信息
        self.alarm_label = QLabel("报警信息")
        self.alarm_label.setFont(QFont("Arial", 12, QFont.Bold))
        stats_layout.addWidget(self.alarm_label)
        
        self.alarm_text = QTextEdit()
        stats_layout.addWidget(self.alarm_text)
        
        chart_layout.addWidget(stats_panel)
        layout.addWidget(chart_container)
        
        # 创建定时器
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_data)
        
        # 初始化数据
        self.reset_data()
        
    def start_monitoring(self):
        """开始监控"""
        self.monitoring = True
        self.timer.start(1000)  # 每秒更新一次
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        
    def stop_monitoring(self):
        """停止监控"""
        self.monitoring = False
        self.timer.stop()
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        
    def reset_data(self):
        """重置数据"""
        self.data = {param: [] for param in self.series.keys()}
        self.timestamps = []
        
        for series in self.series.values():
            series.clear()
            
        self.update_stats()
        
    def export_data(self):
        """导出监控数据"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出数据", "", "CSV文件 (*.csv)"
        )
        
        if file_path:
            try:
                df_data = {"时间": self.timestamps}
                df_data.update(self.data)
                
                df = pd.DataFrame(df_data)
                df.to_csv(file_path, index=False, encoding='utf-8')
                QMessageBox.information(self, "成功", f"数据已导出到: {file_path}")
                
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导出数据时出错: {str(e)}")
                
    def update_data(self):
        """更新监控数据"""
        if not self.monitoring:
            return
            
        current_time = QDateTime.currentDateTime()
        
        # 生成模拟数据（实际应用中应从传感器或数据库获取）
        simulated_data = {
            "产量": max(0, np.random.normal(80, 15)),
            "效率": max(0, min(100, np.random.normal(85, 8))),
            "能耗": max(0, np.random.normal(50, 10)),
            "设备状态": max(0, min(100, np.random.normal(90, 5))),
            "安全指标": max(0, min(100, np.random.normal(95, 3)))
        }
        
        # 限制数据点数量
        if len(self.timestamps) >= self.max_data_points:
            self.timestamps.pop(0)
            for param in self.data:
                self.data[param].pop(0)
                self.series[param].removePoints(0, 1)
        
        # 添加新数据
        self.timestamps.append(current_time)
        for param, value in simulated_data.items():
            self.data[param].append(value)
            self.series[param].append(current_time.toMSecsSinceEpoch(), value)
        
        # 更新坐标轴范围
        if self.timestamps:
            min_time = self.timestamps[0]
            max_time = current_time
            
            self.axis_x.setRange(min_time, max_time)
            
            # 动态调整Y轴范围
            all_values = [val for sublist in self.data.values() for val in sublist]
            if all_values:
                max_val = max(all_values)
                self.axis_y.setRange(0, max(100, max_val * 1.2))
        
        # 更新统计和报警信息
        self.update_stats()
        self.check_alarms()
        
    def update_stats(self):
        """更新统计信息"""
        if not any(self.data.values()):
            self.stats_text.clear()
            return
            
        stats_text = ""
        for param, values in self.data.items():
            if values:
                stats_text += f"{param}:\n"
                stats_text += f"  当前: {values[-1]:.2f}\n"
                stats_text += f"  平均: {np.mean(values):.2f}\n"
                stats_text += f"  最大: {max(values):.2f}\n"
                stats_text += f"  最小: {min(values):.2f}\n"
                stats_text += f"  标准差: {np.std(values):.2f}\n\n"
        
        self.stats_text.setText(stats_text)
        
    def check_alarms(self):
        """检查报警条件"""
        alarms = []
        
        # 产量报警
        if self.data["产量"] and self.data["产量"][-1] < 50:
            alarms.append("产量过低！当前值: {:.2f}".format(self.data["产量"][-1]))
            
        # 效率报警
        if self.data["效率"] and self.data["效率"][-1] < 70:
            alarms.append("效率过低！当前值: {:.2f}%".format(self.data["效率"][-1]))
            
        # 设备状态报警
        if self.data["设备状态"] and self.data["设备状态"][-1] < 80:
            alarms.append("设备状态异常！当前值: {:.2f}%".format(self.data["设备状态"][-1]))
            
        # 安全指标报警
        if self.data["安全指标"] and self.data["安全指标"][-1] < 90:
            alarms.append("安全指标警告！当前值: {:.2f}%".format(self.data["安全指标"][-1]))
        
        alarm_text = "\n".join(alarms) if alarms else "一切正常"
        self.alarm_text.setText(alarm_text)
        
        # 如果有报警，改变背景色
        if alarms:
            self.alarm_text.setStyleSheet("background-color: #ffcccc;")
        else:
            self.alarm_text.setStyleSheet("")


class DataAnalysisTool(QWidget):
    """增强的数据分析工具"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.data = None
        self.init_ui()
        
    def init_ui(self):
        layout = QHBoxLayout(self)
        
        # 左侧控制面板
        control_panel = QWidget()
        control_layout = QVBoxLayout(control_panel)
        control_panel.setMaximumWidth(300)
        
        # 数据加载部分
        load_group = QGroupBox("数据加载")
        load_layout = QVBoxLayout(load_group)
        
        self.load_button = QPushButton("加载数据文件")
        self.load_button.clicked.connect(self.load_data)
        
        self.file_label = QLabel("未加载数据")
        self.file_label.setWordWrap(True)
        
        self.preview_button = QPushButton("数据预览")
        self.preview_button.clicked.connect(self.preview_data)
        
        load_layout.addWidget(self.load_button)
        load_layout.addWidget(self.file_label)
        load_layout.addWidget(self.preview_button)
        
        # 数据预处理部分
        preprocess_group = QGroupBox("数据预处理")
        preprocess_layout = QVBoxLayout(preprocess_group)
        
        self.normalize_check = QCheckBox("标准化数据")
        self.remove_outliers_check = QCheckBox("移除异常值")
        self.fill_missing_check = QCheckBox("填充缺失值")
        
        preprocess_layout.addWidget(self.normalize_check)
        preprocess_layout.addWidget(self.remove_outliers_check)
        preprocess_layout.addWidget(self.fill_missing_check)
        
        # 分析选项部分
        analysis_group = QGroupBox("分析选项")
        analysis_layout = QVBoxLayout(analysis_group)
        
        self.analysis_type = QComboBox()
        self.analysis_type.addItems([
            "描述性统计", "相关性分析", "趋势分析", "聚类分析", 
            "分布分析", "回归分析", "时间序列分析"
        ])
        
        # 聚类数量设置（仅聚类分析时显示）
        self.cluster_label = QLabel("聚类数量:")
        self.cluster_spin = QSpinBox()
        self.cluster_spin.setRange(2, 10)
        self.cluster_spin.setValue(3)
        
        cluster_layout = QHBoxLayout()
        cluster_layout.addWidget(self.cluster_label)
        cluster_layout.addWidget(self.cluster_spin)
        
        self.run_analysis_button = QPushButton("执行分析")
        self.run_analysis_button.clicked.connect(self.run_analysis)
        
        self.export_button = QPushButton("导出结果")
        self.export_button.clicked.connect(self.export_results)
        
        analysis_layout.addWidget(QLabel("分析类型:"))
        analysis_layout.addWidget(self.analysis_type)
        analysis_layout.addLayout(cluster_layout)
        analysis_layout.addWidget(self.run_analysis_button)
        analysis_layout.addWidget(self.export_button)
        analysis_layout.addStretch()
        
        # 添加到控制面板
        control_layout.addWidget(load_group)
        control_layout.addWidget(preprocess_group)
        control_layout.addWidget(analysis_group)
        control_layout.addStretch()
        
        # 右侧结果显示
        result_panel = QWidget()
        result_layout = QVBoxLayout(result_panel)
        
        self.result_tabs = QTabWidget()
        
        # 统计结果标签
        self.stats_table = QTableWidget()
        self.result_tabs.addTab(self.stats_table, "统计结果")
        
        # 图表标签
        self.chart_widget = QWidget()
        chart_layout = QVBoxLayout(self.chart_widget)
        
        self.figure = Figure(figsize=(10, 8))
        self.canvas = FigureCanvas(self.figure)
        
        # 添加matplotlib工具栏
        self.toolbar = NavigationToolbar(self.canvas, self)
        
        chart_layout.addWidget(self.toolbar)
        chart_layout.addWidget(self.canvas)
        self.result_tabs.addTab(self.chart_widget, "可视化")
        
        # 详细结果标签
        self.detailed_text = QTextEdit()
        self.result_tabs.addTab(self.detailed_text, "详细结果")
        
        # 模型结果标签
        self.model_text = QTextEdit()
        self.result_tabs.addTab(self.model_text, "模型结果")
        
        result_layout.addWidget(self.result_tabs)
        
        # 添加到主布局
        layout.addWidget(control_panel)
        layout.addWidget(result_panel)
        
    def load_data(self):
        """加载数据文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "打开数据文件", "", "CSV文件 (*.csv);;Excel文件 (*.xlsx);;所有文件 (*)"
        )
        
        if file_path:
            try:
                if file_path.endswith('.csv'):
                    self.data = pd.read_csv(file_path)
                elif file_path.endswith('.xlsx'):
                    self.data = pd.read_excel(file_path)
                else:
                    QMessageBox.warning(self, "错误", "不支持的文件格式")
                    return
                    
                self.file_label.setText(f"已加载: {file_path.split('/')[-1]}\n"
                                       f"数据维度: {self.data.shape[0]}行 × {self.data.shape[1]}列")
                QMessageBox.information(self, "成功", 
                                      f"成功加载数据，共{len(self.data)}行{len(self.data.columns)}列")
                
            except Exception as e:
                QMessageBox.critical(self, "错误", f"加载文件时出错: {str(e)}")
                
    def preview_data(self):
        """数据预览"""
        if self.data is None:
            QMessageBox.warning(self, "警告", "请先加载数据")
            return
            
        # 创建预览对话框
        preview_dialog = QDialog(self)
        preview_dialog.setWindowTitle("数据预览")
        preview_dialog.resize(600, 400)
        
        layout = QVBoxLayout(preview_dialog)
        
        # 创建表格显示数据
        table = QTableWidget()
        table.setRowCount(min(100, len(self.data)))  # 最多显示100行
        table.setColumnCount(len(self.data.columns))
        table.setHorizontalHeaderLabels(self.data.columns)
        
        for i in range(table.rowCount()):
            for j in range(table.columnCount()):
                value = self.data.iloc[i, j]
                item = QTableWidgetItem(str(value))
                table.setItem(i, j, item)
                
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        layout.addWidget(QLabel(f"数据预览 (显示前{table.rowCount()}行):"))
        layout.addWidget(table)
        
        preview_dialog.exec_()
        
    def preprocess_data(self):
        """数据预处理"""
        if self.data is None:
            return self.data
            
        data = self.data.copy()
        
        # 只处理数值列
        numeric_columns = data.select_dtypes(include=[np.number]).columns
        
        if self.fill_missing_check.isChecked():
            # 填充缺失值
            data[numeric_columns] = data[numeric_columns].fillna(data[numeric_columns].mean())
            
        if self.remove_outliers_check.isChecked():
            # 移除异常值（使用3σ原则）
            for col in numeric_columns:
                mean = data[col].mean()
                std = data[col].std()
                data = data[(data[col] > mean - 3*std) & (data[col] < mean + 3*std)]
                
        if self.normalize_check.isChecked():
            # 标准化数据
            scaler = StandardScaler()
            data[numeric_columns] = scaler.fit_transform(data[numeric_columns])
            
        return data
        
    def run_analysis(self):
        """执行分析"""
        if self.data is None:
            QMessageBox.warning(self, "警告", "请先加载数据")
            return
            
        # 预处理数据
        analysis_data = self.preprocess_data()
        
        analysis_type = self.analysis_type.currentText()
        
        try:
            if analysis_type == "描述性统计":
                self.descriptive_statistics(analysis_data)
            elif analysis_type == "相关性分析":
                self.correlation_analysis(analysis_data)
            elif analysis_type == "趋势分析":
                self.trend_analysis(analysis_data)
            elif analysis_type == "聚类分析":
                self.cluster_analysis(analysis_data)
            elif analysis_type == "分布分析":
                self.distribution_analysis(analysis_data)
            elif analysis_type == "回归分析":
                self.regression_analysis(analysis_data)
            elif analysis_type == "时间序列分析":
                self.time_series_analysis(analysis_data)
                
        except Exception as e:
            QMessageBox.critical(self, "错误", f"分析过程中出错: {str(e)}")
            
    def descriptive_statistics(self, data):
        """执行描述性统计分析"""
        stats = data.describe()
        
        # 更新统计表格
        self.stats_table.setRowCount(len(stats.index))
        self.stats_table.setColumnCount(len(stats.columns))
        self.stats_table.setHorizontalHeaderLabels(stats.columns)
        self.stats_table.setVerticalHeaderLabels(stats.index)
        
        for i, row in enumerate(stats.iterrows()):
            for j, value in enumerate(row[1]):
                item = QTableWidgetItem(f"{value:.4f}")
                self.stats_table.setItem(i, j, item)
                
        # 更新详细文本
        self.detailed_text.clear()
        self.detailed_text.append("描述性统计分析结果:\n")
        self.detailed_text.append(stats.to_string())
        
        # 更新图表
        self.figure.clear()
        
        # 选择数值列进行可视化
        numeric_columns = data.select_dtypes(include=[np.number]).columns
        
        if len(numeric_columns) > 0:
            # 创建子图网格
            n_cols = min(3, len(numeric_columns))
            n_rows = (len(numeric_columns) + n_cols - 1) // n_cols
            
            for i, col in enumerate(numeric_columns):
                ax = self.figure.add_subplot(n_rows, n_cols, i+1)
                data[col].hist(bins=20, ax=ax, alpha=0.7)
                ax.set_title(f'{col}分布')
                ax.set_ylabel('频数')
                
            self.figure.tight_layout()
            self.canvas.draw()
            
    def correlation_analysis(self, data):
        """执行相关性分析"""
        numeric_data = data.select_dtypes(include=[np.number])
        
        if len(numeric_data.columns) < 2:
            QMessageBox.warning(self, "警告", "需要至少2个数值列进行相关性分析")
            return
            
        # 计算相关性矩阵
        corr_matrix = numeric_data.corr()
        
        # 更新统计表格
        self.stats_table.setRowCount(len(corr_matrix.index))
        self.stats_table.setColumnCount(len(corr_matrix.columns))
        self.stats_table.setHorizontalHeaderLabels(corr_matrix.columns)
        self.stats_table.setVerticalHeaderLabels(corr_matrix.index)
        
        for i, row in enumerate(corr_matrix.iterrows()):
            for j, value in enumerate(row[1]):
                item = QTableWidgetItem(f"{value:.4f}")
                # 根据相关性强度设置背景色
                if abs(value) > 0.7:
                    item.setBackground(QColor(255, 200, 200))  # 红色
                elif abs(value) > 0.5:
                    item.setBackground(QColor(255, 255, 200))  # 黄色
                    
                self.stats_table.setItem(i, j, item)
                
        # 更新详细文本
        self.detailed_text.clear()
        self.detailed_text.append("相关性分析结果:\n")
        self.detailed_text.append(corr_matrix.to_string())
        
        # 更新图表
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        
        # 创建热力图
        im = ax.imshow(corr_matrix.values, cmap='coolwarm', vmin=-1, vmax=1)
        
        # 设置刻度标签
        ax.set_xticks(range(len(corr_matrix.columns)))
        ax.set_yticks(range(len(corr_matrix.index)))
        ax.set_xticklabels(corr_matrix.columns, rotation=45)
        ax.set_yticklabels(corr_matrix.index)
        
        # 添加颜色条
        self.figure.colorbar(im, ax=ax)
        
        # 添加数值标注
        for i in range(len(corr_matrix.index)):
            for j in range(len(corr_matrix.columns)):
                ax.text(j, i, f'{corr_matrix.iloc[i, j]:.2f}', 
                       ha='center', va='center', color='black')
        
        ax.set_title('变量相关性热力图')
        self.figure.tight_layout()
        self.canvas.draw()
        
    def cluster_analysis(self, data):
        """执行聚类分析"""
        numeric_data = data.select_dtypes(include=[np.number])
        
        if len(numeric_data) < 2:
            QMessageBox.warning(self, "警告", "需要至少2个数据点进行聚类分析")
            return
            
        # 使用K-means聚类
        n_clusters = self.cluster_spin.value()
        kmeans = KMeans(n_clusters=n_clusters, random_state=42)
        clusters = kmeans.fit_predict(numeric_data)
        
        # 更新详细文本
        self.detailed_text.clear()
        self.detailed_text.append(f"K-means聚类分析结果 (k={n_clusters}):\n")
        self.detailed_text.append(f"聚类中心:\n{kmeans.cluster_centers_}\n")
        self.detailed_text.append(f"聚类标签:\n{clusters}\n")
        self.detailed_text.append(f" inertia (簇内平方和): {kmeans.inertia_:.2f}")
        
        # 更新模型结果
        self.model_text.clear()
        self.model_text.append("聚类模型信息:\n")
        self.model_text.append(f"算法: K-means\n")
        self.model_text.append(f"聚类数量: {n_clusters}\n")
        self.model_text.append(f"迭代次数: {kmeans.n_iter_}\n")
        self.model_text.append(f"簇内平方和: {kmeans.inertia_:.2f}\n")
        
        # 更新图表
        self.figure.clear()
        
        if len(numeric_data.columns) >= 2:
            # 使用前两个主成分进行可视化
            ax = self.figure.add_subplot(111)
            
            scatter = ax.scatter(numeric_data.iloc[:, 0], numeric_data.iloc[:, 1], 
                               c=clusters, cmap='viridis', alpha=0.7)
            
            # 标记聚类中心
            centers = kmeans.cluster_centers_
            ax.scatter(centers[:, 0], centers[:, 1], c='red', marker='x', s=200, linewidth=3)
            
            ax.set_xlabel(numeric_data.columns[0])
            ax.set_ylabel(numeric_data.columns[1])
            ax.set_title(f'K-means聚类结果 (k={n_clusters})')
            self.figure.colorbar(scatter, ax=ax)
            
        self.figure.tight_layout()
        self.canvas.draw()
        
    def trend_analysis(self, data):
        """执行趋势分析"""
        numeric_data = data.select_dtypes(include=[np.number])
        
        if len(numeric_data.columns) == 0:
            QMessageBox.warning(self, "警告", "没有数值列进行趋势分析")
            return
            
        # 更新详细文本
        self.detailed_text.clear()
        self.detailed_text.append("趋势分析结果:\n")
        
        # 更新图表
        self.figure.clear()
        
        n_cols = min(2, len(numeric_data.columns))
        n_rows = (len(numeric_data.columns) + n_cols - 1) // n_cols
        
        for i, col in enumerate(numeric_data.columns):
            ax = self.figure.add_subplot(n_rows, n_cols, i+1)
            
            # 原始数据
            ax.plot(numeric_data[col].values, 'b-', alpha=0.7, label='原始数据')
            
            # 移动平均趋势
            window = min(10, len(numeric_data) // 10)
            if window > 1:
                moving_avg = numeric_data[col].rolling(window=window).mean()
                ax.plot(moving_avg.values, 'r-', linewidth=2, label=f'{window}期移动平均')
                
            # 线性趋势线
            if len(numeric_data) > 1:
                x = np.arange(len(numeric_data))
                slope, intercept, r_value, p_value, std_err = stats.linregress(x, numeric_data[col])
                trend_line = slope * x + intercept
                ax.plot(trend_line, 'g--', linewidth=2, label='线性趋势')
                
                # 在详细文本中添加趋势信息
                self.detailed_text.append(f"\n{col}趋势分析:")
                self.detailed_text.append(f"  斜率: {slope:.4f} (正值表示上升趋势，负值表示下降趋势)")
                self.detailed_text.append(f"  相关系数: {r_value:.4f}")
                self.detailed_text.append(f"  P值: {p_value:.4f}")
                
            ax.set_title(f'{col}趋势分析')
            ax.set_ylabel(col)
            ax.legend()
            ax.grid(True, alpha=0.3)
            
        self.figure.tight_layout()
        self.canvas.draw()
        
    def distribution_analysis(self, data):
        """分布分析"""
        numeric_data = data.select_dtypes(include=[np.number])
        
        if len(numeric_data.columns) == 0:
            QMessageBox.warning(self, "警告", "没有数值列进行分布分析")
            return
            
        # 更新详细文本
        self.detailed_text.clear()
        self.detailed_text.append("分布分析结果:\n")
        
        # 更新图表
        self.figure.clear()
        
        n_cols = min(3, len(numeric_data.columns))
        n_rows = (len(numeric_data.columns) + n_cols - 1) // n_cols
        
        for i, col in enumerate(numeric_data.columns):
            ax = self.figure.add_subplot(n_rows, n_cols, i+1)
            
            # 绘制直方图和密度曲线
            values = numeric_data[col].dropna()
            ax.hist(values, bins=20, density=True, alpha=0.7, color='skyblue')
            
            # 添加密度曲线
            from scipy.stats import gaussian_kde
            if len(values) > 1:
                kde = gaussian_kde(values)
                x_range = np.linspace(values.min(), values.max(), 100)
                ax.plot(x_range, kde(x_range), 'r-', linewidth=2)
                
            # 添加正态分布曲线比较
            mu, sigma = values.mean(), values.std()
            normal_curve = stats.norm.pdf(x_range, mu, sigma)
            ax.plot(x_range, normal_curve, 'g--', alpha=0.7, label='正态分布')
            
            # 计算分布特征
            skewness = stats.skew(values)
            kurtosis = stats.kurtosis(values)
            normality_test = stats.normaltest(values)
            
            ax.set_title(f'{col}分布\n偏度: {skewness:.2f}, 峰度: {kurtosis:.2f}')
            ax.set_ylabel('密度')
            ax.legend()
            
            # 在详细文本中添加分布信息
            self.detailed_text.append(f"\n{col}分布特征:")
            self.detailed_text.append(f"  偏度: {skewness:.4f} (0表示对称分布)")
            self.detailed_text.append(f"  峰度: {kurtosis:.4f} (0表示正态分布)")
            self.detailed_text.append(f"  正态性检验P值: {normality_test.pvalue:.4f}")
            if normality_test.pvalue < 0.05:
                self.detailed_text.append("  拒绝正态性原假设（非正态分布）")
            else:
                self.detailed_text.append("  不能拒绝正态性原假设（可能是正态分布）")
                
        self.figure.tight_layout()
        self.canvas.draw()
        
    def regression_analysis(self, data):
        """回归分析"""
        numeric_data = data.select_dtypes(include=[np.number])
        
        if len(numeric_data.columns) < 2:
            QMessageBox.warning(self, "警告", "需要至少2个数值列进行回归分析")
            return
            
        # 使用第一列作为因变量，其他作为自变量
        y_col = numeric_data.columns[0]
        X_cols = numeric_data.columns[1:]
        
        if len(X_cols) == 0:
            QMessageBox.warning(self, "警告", "需要至少1个自变量进行回归分析")
            return
            
        # 简单线性回归（多变量时使用第一个自变量）
        x_col = X_cols[0]
        X = numeric_data[x_col].values
        y = numeric_data[y_col].values
        
        # 移除缺失值
        mask = ~(np.isnan(X) | np.isnan(y))
        X, y = X[mask], y[mask]
        
        if len(X) < 2:
            QMessageBox.warning(self, "警告", "有效数据点不足")
            return
            
        # 执行线性回归
        slope, intercept, r_value, p_value, std_err = stats.linregress(X, y)
        y_pred = slope * X + intercept
        
        # 更新详细文本
        self.detailed_text.clear()
        self.detailed_text.append(f"线性回归分析: {y_col} ~ {x_col}\n")
        self.detailed_text.append(f"回归方程: y = {slope:.4f}x + {intercept:.4f}\n")
        self.detailed_text.append(f"相关系数 (R): {r_value:.4f}\n")
        self.detailed_text.append(f"决定系数 (R²): {r_value**2:.4f}\n")
        self.detailed_text.append(f"P值: {p_value:.4f}\n")
        self.detailed_text.append(f"标准误差: {std_err:.4f}")
        
        # 更新模型结果
        self.model_text.clear()
        self.model_text.append("回归模型信息:\n")
        self.model_text.append(f"因变量: {y_col}\n")
        self.model_text.append(f"自变量: {x_col}\n")
        self.model_text.append(f"样本数量: {len(X)}\n")
        
        if p_value < 0.05:
            self.model_text.append("回归关系显著 (p < 0.05)")
        else:
            self.model_text.append("回归关系不显著 (p >= 0.05)")
            
        # 更新图表
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        
        # 散点图
        ax.scatter(X, y, alpha=0.7, label='实际数据')
        
        # 回归线
        ax.plot(X, y_pred, 'r-', linewidth=2, label='回归线')
        
        ax.set_xlabel(x_col)
        ax.set_ylabel(y_col)
        ax.set_title(f'线性回归: {y_col} ~ {x_col}\nR² = {r_value**2:.4f}')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        self.figure.tight_layout()
        self.canvas.draw()
        
    def time_series_analysis(self, data):
        """时间序列分析"""
        numeric_data = data.select_dtypes(include=[np.number])
        
        if len(numeric_data.columns) == 0:
            QMessageBox.warning(self, "警告", "没有数值列进行时间序列分析")
            return
            
        # 假设数据是按时间顺序的
        self.detailed_text.clear()
        self.detailed_text.append("时间序列分析结果:\n")
        
        # 更新图表
        self.figure.clear()
        
        n_cols = min(2, len(numeric_data.columns))
        n_rows = (len(numeric_data.columns) + n_cols - 1) // n_cols
        
        for i, col in enumerate(numeric_data.columns):
            ax = self.figure.add_subplot(n_rows, n_cols, i+1)
            
            series = numeric_data[col].dropna()
            
            # 绘制时间序列
            ax.plot(series.values, 'b-', alpha=0.7, label='时间序列')
            
            # 计算自相关性
            from pandas.plotting import autocorrelation_plot
            autocorrelation_plot(series, ax=ax.twinx())
            
            ax.set_title(f'{col}时间序列分析')
            ax.set_ylabel(col)
            ax.legend()
            ax.grid(True, alpha=0.3)
            
            # 计算基本时间序列统计
            self.detailed_text.append(f"\n{col}时间序列特征:")
            self.detailed_text.append(f"  均值: {series.mean():.4f}")
            self.detailed_text.append(f"  标准差: {series.std():.4f}")
            self.detailed_text.append(f"  趋势: {'上升' if series.iloc[-1] > series.iloc[0] else '下降'}")
            
        self.figure.tight_layout()
        self.canvas.draw()
        
    def export_results(self):
        """导出分析结果"""
        if self.data is None:
            QMessageBox.warning(self, "警告", "没有数据可导出")
            return
            
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出分析结果", "", "HTML文件 (*.html);;PDF文件 (*.pdf);;所有文件 (*)"
        )
        
        if file_path:
            try:
                # 这里可以添加更复杂的导出逻辑
                # 目前简单导出数据
                if file_path.endswith('.html'):
                    self.data.to_html(file_path)
                else:
                    self.data.to_csv(file_path, index=False)
                    
                QMessageBox.information(self, "成功", f"结果已导出到: {file_path}")
                
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导出结果时出错: {str(e)}")


class MiningManagementSystem(QMainWindow):
    """矿业管理系统主窗口"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("高级矿业管理系统")
        self.setGeometry(100, 100, 1400, 900)
        
        # 初始化工具库
        self.resource_calculator = MineralResourceCalculator()
        
        self.init_ui()
        
    def init_ui(self):
        # 创建中央部件和主布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        
        # 创建左侧导航树
        self.navigation_tree = QTreeWidget()
        self.navigation_tree.setHeaderLabel("功能导航")
        self.navigation_tree.setMaximumWidth(250)
        
        # 添加功能项
        monitoring_item = QTreeWidgetItem(self.navigation_tree, ["实时监控"])
        visualization_item = QTreeWidgetItem(self.navigation_tree, ["3D地质可视化"])
        analysis_item = QTreeWidgetItem(self.navigation_tree, ["数据分析"])
        calculation_item = QTreeWidgetItem(self.navigation_tree, ["资源计算"])
        report_item = QTreeWidgetItem(self.navigation_tree, ["报表生成"])
        
        self.navigation_tree.expandAll()
        
        # 创建右侧标签页
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabPosition(QTabWidget.North)
        self.tab_widget.setMovable(True)
        self.tab_widget.setTabsClosable(False)
        
        # 添加标签页
        self.monitor_tab = RealTimeMonitor()
        self.visualization_tab = Geological3DVisualization()
        self.analysis_tab = DataAnalysisTool()
        
        self.tab_widget.addTab(self.monitor_tab, "实时监控")
        self.tab_widget.addTab(self.visualization_tab, "3D地质可视化")
        self.tab_widget.addTab(self.analysis_tab, "数据分析")
        
        # 添加到分割器
        splitter.addWidget(self.navigation_tree)
        splitter.addWidget(self.tab_widget)
        splitter.setSizes([250, 1150])
        
        main_layout.addWidget(splitter)
        
        # 创建菜单栏
        self.create_menubar()
        
        # 创建工具栏
        self.create_toolbar()
        
        # 创建状态栏
        self.statusBar().showMessage("就绪")
        
        # 连接信号和槽
        self.navigation_tree.itemClicked.connect(self.on_navigation_item_clicked)
        
    def create_menubar(self):
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu("文件")
        
        new_action = QAction("新建", self)
        new_action.setShortcut("Ctrl+N")
        
        open_action = QAction("打开", self)
        open_action.setShortcut("Ctrl+O")
        
        save_action = QAction("保存", self)
        save_action.setShortcut("Ctrl+S")
        
        exit_action = QAction("退出", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        
        file_menu.addAction(new_action)
        file_menu.addAction(open_action)
        file_menu.addAction(save_action)
        file_menu.addSeparator()
        file_menu.addAction(exit_action)
        
        # 工具菜单
        tools_menu = menubar.addMenu("工具")
        
        calc_action = QAction("资源计算器", self)
        report_action = QAction("生成报表", self)
        settings_action = QAction("设置", self)
        
        tools_menu.addAction(calc_action)
        tools_menu.addAction(report_action)
        tools_menu.addAction(settings_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu("帮助")
        
        about_action = QAction("关于", self)
        about_action.triggered.connect(self.show_about)
        
        help_menu.addAction(about_action)
        
    def create_toolbar(self):
        toolbar = QToolBar("主工具栏")
        toolbar.setMovable(False)
        self.addToolBar(Qt.TopToolBarArea, toolbar)
        
        # 添加工具按钮
        monitor_btn = QToolButton()
        monitor_btn.setText("监控")
        monitor_btn.setToolTip("打开实时监控")
        monitor_btn.clicked.connect(lambda: self.tab_widget.setCurrentIndex(0))
        
        visualization_btn = QToolButton()
        visualization_btn.setText("3D可视化")
        visualization_btn.setToolTip("打开3D地质可视化")
        visualization_btn.clicked.connect(lambda: self.tab_widget.setCurrentIndex(1))
        
        analysis_btn = QToolButton()
        analysis_btn.setText("分析")
        analysis_btn.setToolTip("打开数据分析工具")
        analysis_btn.clicked.connect(lambda: self.tab_widget.setCurrentIndex(2))
        
        toolbar.addWidget(monitor_btn)
        toolbar.addWidget(visualization_btn)
        toolbar.addWidget(analysis_btn)
        toolbar.addSeparator()
        
        # 添加资源计算按钮
        calc_btn = QToolButton()
        calc_btn.setText("资源计算")
        calc_btn.setToolTip("打开资源计算工具")
        calc_btn.clicked.connect(self.open_resource_calculator)
        
        toolbar.addWidget(calc_btn)
        
    def on_navigation_item_clicked(self, item, column):
        """导航树项点击事件"""
        text = item.text(column)
        
        if text == "实时监控":
            self.tab_widget.setCurrentIndex(0)
        elif text == "3D地质可视化":
            self.tab_widget.setCurrentIndex(1)
        elif text == "数据分析":
            self.tab_widget.setCurrentIndex(2)
        elif text == "资源计算":
            self.open_resource_calculator()
        elif text == "报表生成":
            self.generate_report()
            
    def open_resource_calculator(self):
        """打开资源计算对话框"""
        dialog = ResourceCalculatorDialog(self.resource_calculator, self)
        dialog.exec_()
        
    def generate_report(self):
        """生成报表"""
        QMessageBox.information(self, "报表生成", "报表生成功能即将实现")
        
    def show_about(self):
        """显示关于对话框"""
        QMessageBox.about(self, "关于矿业管理系统", 
                         "高级矿业管理系统 v2.0\n\n"
                         "这是一个功能强大的矿业管理工具，包含实时监控、3D可视化、"
                         "数据分析和资源计算等高级功能。\n\n"
                         "主要特性:\n"
                         "- 实时生产监控与报警\n"
                         "- 3D地质数据可视化\n"
                         "- 高级数据分析工具\n"
                         "- 矿产资源计算\n"
                         "- 数据导入导出功能")


class ResourceCalculatorDialog(QDialog):
    """资源计算对话框"""
    
    def __init__(self, calculator, parent=None):
        super().__init__(parent)
        self.calculator = calculator
        self.setWindowTitle("矿产资源计算器")
        self.setModal(True)
        self.resize(500, 400)
        
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # 创建选项卡
        self.tabs = QTabWidget()
        
        # 基础计算选项卡
        basic_tab = QWidget()
        self.setup_basic_tab(basic_tab)
        self.tabs.addTab(basic_tab, "基础计算")
        
        # 品位估算选项卡
        grade_tab = QWidget()
        self.setup_grade_tab(grade_tab)
        self.tabs.addTab(grade_tab, "品位估算")
        
        layout.addWidget(self.tabs)
        
        # 按钮
        button_layout = QHBoxLayout()
        
        self.close_button = QPushButton("关闭")
        self.close_button.clicked.connect(self.close)
        
        button_layout.addStretch()
        button_layout.addWidget(self.close_button)
        
        layout.addLayout(button_layout)
        
    def setup_basic_tab(self, tab):
        layout = QVBoxLayout(tab)
        
        # 创建表单
        form_layout = QFormLayout()
        
        self.area_input = QDoubleSpinBox()
        self.area_input.setRange(0, 1000000)
        self.area_input.setSuffix(" m²")
        self.area_input.setValue(1000)
        
        self.thickness_input = QDoubleSpinBox()
        self.thickness_input.setRange(0, 1000)
        self.thickness_input.setSuffix(" m")
        self.thickness_input.setValue(10)
        
        self.density_input = QDoubleSpinBox()
        self.density_input.setRange(0, 10)
        self.density_input.setDecimals(2)
        self.density_input.setSuffix(" t/m³")
        self.density_input.setValue(2.5)
        
        self.recovery_input = QDoubleSpinBox()
        self.recovery_input.setRange(0, 100)
        self.recovery_input.setSuffix(" %")
        self.recovery_input.setValue(85)
        
        self.dilution_input = QDoubleSpinBox()
        self.dilution_input.setRange(0, 100)
        self.dilution_input.setSuffix(" %")
        self.dilution_input.setValue(10)
        
        form_layout.addRow("矿体面积:", self.area_input)
        form_layout.addRow("平均厚度:", self.thickness_input)
        form_layout.addRow("矿石密度:", self.density_input)
        form_layout.addRow("回收率:", self.recovery_input)
        form_layout.addRow("贫化率:", self.dilution_input)
        
        layout.addLayout(form_layout)
        
        # 计算按钮
        self.calculate_button = QPushButton("计算")
        self.calculate_button.clicked.connect(self.calculate)
        layout.addWidget(self.calculate_button)
        
        # 结果展示
        result_group = QGroupBox("计算结果")
        result_layout = QFormLayout(result_group)
        
        self.volume_result = QLabel("0 m³")
        self.tonnage_result = QLabel("0 t")
        self.reserves_result = QLabel("0 t")
        
        result_layout.addRow("矿体体积:", self.volume_result)
        result_layout.addRow("矿石吨位:", self.tonnage_result)
        result_layout.addRow("可采储量:", self.reserves_result)
        
        layout.addWidget(result_group)
        layout.addStretch()
        
    def setup_grade_tab(self, tab):
        layout = QVBoxLayout(tab)
        
        # 方法选择
        method_layout = QHBoxLayout()
        method_layout.addWidget(QLabel("估算方法:"))
        
        self.grade_method = QComboBox()
        self.grade_method.addItems(["反距离加权法", "克里金法", "多边形法"])
        method_layout.addWidget(self.grade_method)
        
        method_layout.addStretch()
        layout.addLayout(method_layout)
        
        # 样本数据输入
        sample_group = QGroupBox("样本数据")
        sample_layout = QVBoxLayout(sample_group)
        
        # 样本表格
        self.sample_table = QTableWidget()
        self.sample_table.setColumnCount(3)
        self.sample_table.setHorizontalHeaderLabels(["X坐标", "Y坐标", "品位值"])
        self.sample_table.setRowCount(5)
        
        # 添加示例数据
        sample_data = [
            [0, 0, 1.5], [10, 0, 1.8], [0, 10, 1.2], 
            [10, 10, 2.1], [5, 5, 1.6]
        ]
        
        for i, (x, y, grade) in enumerate(sample_data):
            self.sample_table.setItem(i, 0, QTableWidgetItem(str(x)))
            self.sample_table.setItem(i, 1, QTableWidgetItem(str(y)))
            self.sample_table.setItem(i, 2, QTableWidgetItem(str(grade)))
        
        sample_layout.addWidget(self.sample_table)
        
        # 样本控制按钮
        sample_control_layout = QHBoxLayout()
        
        add_sample_btn = QPushButton("添加样本")
        remove_sample_btn = QPushButton("删除样本")
        clear_samples_btn = QPushButton("清空样本")
        
        add_sample_btn.clicked.connect(self.add_sample)
        remove_sample_btn.clicked.connect(self.remove_sample)
        clear_samples_btn.clicked.connect(self.clear_samples)
        
        sample_control_layout.addWidget(add_sample_btn)
        sample_control_layout.addWidget(remove_sample_btn)
        sample_control_layout.addWidget(clear_samples_btn)
        sample_control_layout.addStretch()
        
        sample_layout.addLayout(sample_control_layout)
        layout.addWidget(sample_group)
        
        # 估算点输入
        point_layout = QFormLayout()
        
        self.estimate_x = QDoubleSpinBox()
        self.estimate_x.setRange(-1000, 1000)
        self.estimate_x.setValue(3)
        
        self.estimate_y = QDoubleSpinBox()
        self.estimate_y.setRange(-1000, 1000)
        self.estimate_y.setValue(3)
        
        point_layout.addRow("估算点X坐标:", self.estimate_x)
        point_layout.addRow("估算点Y坐标:", self.estimate_y)
        
        layout.addLayout(point_layout)
        
        # 估算按钮和结果
        estimate_btn = QPushButton("估算品位")
        estimate_btn.clicked.connect(self.estimate_grade)
        layout.addWidget(estimate_btn)
        
        self.grade_result = QLabel("估算结果将显示在这里")
        self.grade_result.setFrameStyle(QFrame.Box)
        self.grade_result.setMinimumHeight(50)
        layout.addWidget(self.grade_result)
        
        layout.addStretch()
        
    def add_sample(self):
        """添加样本行"""
        row = self.sample_table.rowCount()
        self.sample_table.insertRow(row)
        
    def remove_sample(self):
        """删除选中样本行"""
        current_row = self.sample_table.currentRow()
        if current_row >= 0:
            self.sample_table.removeRow(current_row)
            
    def clear_samples(self):
        """清空所有样本"""
        self.sample_table.setRowCount(0)
        
    def calculate(self):
        """执行基础计算"""
        try:
            area = self.area_input.value()
            thickness = self.thickness_input.value()
            density = self.density_input.value()
            recovery_rate = self.recovery_input.value() / 100
            dilution_rate = self.dilution_input.value() / 100
            
            volume = self.calculator.calculate_volume(area, thickness)
            tonnage = self.calculator.calculate_tonnage(volume, density)
            reserves = self.calculator.estimate_reserves(tonnage, recovery_rate, dilution_rate)
            
            self.volume_result.setText(f"{volume:.2f} m³")
            self.tonnage_result.setText(f"{tonnage:.2f} t")
            self.reserves_result.setText(f"{reserves:.2f} t")
            
        except Exception as e:
            QMessageBox.critical(self, "计算错误", f"计算过程中发生错误: {str(e)}")
            
    def estimate_grade(self):
        """执行品位估算"""
        try:
            # 获取样本数据
            samples = []
            for row in range(self.sample_table.rowCount()):
                x_item = self.sample_table.item(row, 0)
                y_item = self.sample_table.item(row, 1)
                grade_item = self.sample_table.item(row, 2)
                
                if x_item and y_item and grade_item:
                    try:
                        x = float(x_item.text())
                        y = float(y_item.text())
                        grade = float(grade_item.text())
                        samples.append((x, y, grade))
                    except ValueError:
                        continue
            
            if not samples:
                QMessageBox.warning(self, "警告", "没有有效的样本数据")
                return
                
            # 获取估算点
            x = self.estimate_x.value()
            y = self.estimate_y.value()
            
            # 添加估算点到样本中（用于插值）
            method_index = self.grade_method.currentIndex()
            method = ['idw', 'kriging', 'polygonal'][method_index]
            
            # 使用选定的方法进行估算
            estimated_grade = self.calculator.grade_estimation(samples, method)
            
            self.grade_result.setText(
                f"在点({x}, {y})处的估算品位: {estimated_grade:.4f}\n"
                f"使用方法: {self.grade_method.currentText()}\n"
                f"使用样本数: {len(samples)}"
            )
            
        except Exception as e:
            QMessageBox.critical(self, "估算错误", f"品位估算过程中发生错误: {str(e)}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 设置应用程序样式
    app.setStyle(QStyleFactory.create("Fusion"))
    
    # 创建并显示主窗口
    window = MiningManagementSystem()
    window.show()
    
    sys.exit(app.exec_())