import sys
import os
import pandas as pd
import numpy as np
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QTabWidget, QPushButton, QLabel, QLineEdit, QTextEdit, 
                             QTableWidget, QTableWidgetItem, QHeaderView, QFileDialog,
                             QMessageBox, QProgressBar, QGroupBox, QComboBox, QCheckBox,
                             QSpinBox, QDoubleSpinBox, QSplitter, QTreeWidget, QTreeWidgetItem,
                             QListWidget, QListWidgetItem, QAction, QToolBar, QStatusBar,
                             QDialog, QDialogButtonBox, QFormLayout, QScrollArea)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QSettings
from PyQt5.QtGui import QIcon, QFont, QPixmap, QPainter, QColor
import matplotlib
matplotlib.rc("font", family='Microsoft YaHei')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import seaborn as sns
from scipy import stats
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import sqlite3
from datetime import datetime
import json


class DatabaseManager:
    """数据库管理类，用于处理实验数据和结果存储"""
    
    def __init__(self, db_path="biopharma_data.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """初始化数据库表结构"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建实验数据表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS experiments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                date_created TEXT,
                researcher TEXT,
                status TEXT
            )
        ''')
        
        # 创建化合物数据表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS compounds (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                formula TEXT,
                molecular_weight REAL,
                smiles TEXT,
                experimental_data TEXT
            )
        ''')
        
        # 创建分析结果表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS analysis_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                experiment_id INTEGER,
                analysis_type TEXT,
                parameters TEXT,
                results TEXT,
                date_created TEXT,
                FOREIGN KEY (experiment_id) REFERENCES experiments (id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def add_experiment(self, name, description, researcher):
        """添加新实验"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO experiments (name, description, date_created, researcher, status)
            VALUES (?, ?, ?, ?, ?)
        ''', (name, description, datetime.now().isoformat(), researcher, "Active"))
        
        experiment_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return experiment_id
    
    def get_experiments(self):
        """获取所有实验"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM experiments ORDER BY date_created DESC')
        experiments = cursor.fetchall()
        
        conn.close()
        return experiments


class AnalysisWorker(QThread):
    """后台分析工作线程"""
    
    progress_updated = pyqtSignal(int)
    analysis_finished = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, analysis_type, data, parameters):
        super().__init__()
        self.analysis_type = analysis_type
        self.data = data
        self.parameters = parameters
    
    def run(self):
        try:
            if self.analysis_type == "pca":
                result = self.perform_pca()
            elif self.analysis_type == "cluster":
                result = self.perform_clustering()
            elif self.analysis_type == "stats":
                result = self.perform_statistical_analysis()
            else:
                raise ValueError(f"未知的分析类型: {self.analysis_type}")
            
            self.analysis_finished.emit(result)
        except Exception as e:
            self.error_occurred.emit(str(e))
    
    def perform_pca(self):
        """执行PCA分析"""
        self.progress_updated.emit(10)
        
        # 数据预处理
        scaler = StandardScaler()
        scaled_data = scaler.fit_transform(self.data)
        
        self.progress_updated.emit(30)
        
        # 执行PCA
        n_components = self.parameters.get('n_components', 2)
        pca = PCA(n_components=n_components)
        principal_components = pca.fit_transform(scaled_data)
        
        self.progress_updated.emit(70)
        
        # 准备结果
        result = {
            'components': principal_components,
            'explained_variance': pca.explained_variance_ratio_,
            'feature_importance': pca.components_,
            'scaler': scaler,
            'pca': pca
        }
        
        self.progress_updated.emit(100)
        return result
    
    def perform_clustering(self):
        """执行聚类分析"""
        self.progress_updated.emit(10)
        
        # 数据预处理
        scaler = StandardScaler()
        scaled_data = scaler.fit_transform(self.data)
        
        self.progress_updated.emit(30)
        
        # 执行K-means聚类
        n_clusters = self.parameters.get('n_clusters', 3)
        kmeans = KMeans(n_clusters=n_clusters, random_state=42)
        clusters = kmeans.fit_predict(scaled_data)
        
        self.progress_updated.emit(70)
        
        # 准备结果
        result = {
            'clusters': clusters,
            'centers': kmeans.cluster_centers_,
            'inertia': kmeans.inertia_,
            'scaler': scaler,
            'model': kmeans
        }
        
        self.progress_updated.emit(100)
        return result
    
    def perform_statistical_analysis(self):
        """执行统计分析"""
        self.progress_updated.emit(10)
        
        results = {}
        
        # 基本统计量
        results['descriptive'] = {
            'mean': self.data.mean().to_dict(),
            'std': self.data.std().to_dict(),
            'min': self.data.min().to_dict(),
            'max': self.data.max().to_dict()
        }
        
        self.progress_updated.emit(40)
        
        # 相关性分析
        if len(self.data.columns) > 1:
            results['correlation'] = self.data.corr().to_dict()
        
        self.progress_updated.emit(70)
        
        # 正态性检验（对数值列）
        normality_tests = {}
        for col in self.data.select_dtypes(include=[np.number]).columns:
            if len(self.data[col].dropna()) > 3:  # 需要有足够的数据点
                _, p_value = stats.normaltest(self.data[col].dropna())
                normality_tests[col] = p_value
        
        results['normality'] = normality_tests
        
        self.progress_updated.emit(100)
        return results


class MplCanvas(FigureCanvas):
    """Matplotlib画布"""
    
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_subplot(111)
        super(MplCanvas, self).__init__(self.fig)
        self.setParent(parent)
        
        # 设置样式
        plt.style.use('seaborn-v0_8-whitegrid')
    
    def clear(self):
        """清除图形"""
        self.axes.clear()
        self.draw()


class DataVisualizationWidget(QWidget):
    """数据可视化组件"""
    
    def __init__(self):
        super().__init__()
        self.data = None
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 控制面板
        control_layout = QHBoxLayout()
        
        self.plot_type_combo = QComboBox()
        self.plot_type_combo.addItems(["散点图", "柱状图", "箱线图", "热图", "PCA分析", "聚类分析"])
        self.plot_type_combo.currentTextChanged.connect(self.update_plot_options)
        
        self.x_axis_combo = QComboBox()
        self.y_axis_combo = QComboBox()
        
        self.color_by_combo = QComboBox()
        self.color_by_combo.addItem("无")
        
        control_layout.addWidget(QLabel("图表类型:"))
        control_layout.addWidget(self.plot_type_combo)
        control_layout.addWidget(QLabel("X轴:"))
        control_layout.addWidget(self.x_axis_combo)
        control_layout.addWidget(QLabel("Y轴:"))
        control_layout.addWidget(self.y_axis_combo)
        control_layout.addWidget(QLabel("颜色依据:"))
        control_layout.addWidget(self.color_by_combo)
        
        self.plot_button = QPushButton("生成图表")
        self.plot_button.clicked.connect(self.generate_plot)
        control_layout.addWidget(self.plot_button)
        
        control_layout.addStretch()
        
        layout.addLayout(control_layout)
        
        # 画布
        self.canvas = MplCanvas(self, width=10, height=8, dpi=100)
        layout.addWidget(self.canvas)
        
        self.setLayout(layout)
    
    def set_data(self, data):
        """设置数据"""
        self.data = data
        
        # 更新轴选择
        self.x_axis_combo.clear()
        self.y_axis_combo.clear()
        self.color_by_combo.clear()
        self.color_by_combo.addItem("无")
        
        if data is not None:
            columns = data.columns.tolist()
            self.x_axis_combo.addItems(columns)
            self.y_axis_combo.addItems(columns)
            self.color_by_combo.addItems(columns)
    
    def update_plot_options(self, plot_type):
        """根据图表类型更新选项"""
        # 根据不同的图表类型启用/禁用不同的选项
        if plot_type in ["散点图", "柱状图"]:
            self.x_axis_combo.setEnabled(True)
            self.y_axis_combo.setEnabled(True)
            self.color_by_combo.setEnabled(True)
        elif plot_type in ["箱线图", "热图"]:
            self.x_axis_combo.setEnabled(False)
            self.y_axis_combo.setEnabled(False)
            self.color_by_combo.setEnabled(False)
        elif plot_type in ["PCA分析", "聚类分析"]:
            self.x_axis_combo.setEnabled(False)
            self.y_axis_combo.setEnabled(False)
            self.color_by_combo.setEnabled(True)
    
    def generate_plot(self):
        """生成图表"""
        if self.data is None or self.data.empty:
            QMessageBox.warning(self, "警告", "没有数据可可视化")
            return
        
        plot_type = self.plot_type_combo.currentText()
        
        try:
            self.canvas.clear()
            
            if plot_type == "散点图":
                self.create_scatter_plot()
            elif plot_type == "柱状图":
                self.create_bar_plot()
            elif plot_type == "箱线图":
                self.create_box_plot()
            elif plot_type == "热图":
                self.create_heatmap()
            elif plot_type == "PCA分析":
                self.create_pca_plot()
            elif plot_type == "聚类分析":
                self.create_cluster_plot()
            
            self.canvas.fig.tight_layout()
            self.canvas.draw()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"生成图表时出错: {str(e)}")
    
    def create_scatter_plot(self):
        """创建散点图"""
        x_col = self.x_axis_combo.currentText()
        y_col = self.y_axis_combo.currentText()
        color_col = self.color_by_combo.currentText()
        
        if color_col == "无":
            self.canvas.axes.scatter(self.data[x_col], self.data[y_col], alpha=0.7)
        else:
            unique_colors = self.data[color_col].nunique()
            scatter = self.canvas.axes.scatter(
                self.data[x_col], self.data[y_col], 
                c=self.data[color_col], alpha=0.7, cmap='viridis'
            )
            self.canvas.fig.colorbar(scatter, ax=self.canvas.axes, label=color_col)
        
        self.canvas.axes.set_xlabel(x_col)
        self.canvas.axes.set_ylabel(y_col)
        self.canvas.axes.set_title(f"{y_col} vs {x_col}")
    
    def create_bar_plot(self):
        """创建柱状图"""
        x_col = self.x_axis_combo.currentText()
        y_col = self.y_axis_combo.currentText()
        
        # 如果X轴是分类变量，则分组计算
        if self.data[x_col].dtype == 'object' or self.data[x_col].nunique() < 10:
            grouped = self.data.groupby(x_col)[y_col].mean()
            grouped.plot(kind='bar', ax=self.canvas.axes)
        else:
            # 如果X轴是连续变量，则创建直方图
            self.data[y_col].plot(kind='hist', ax=self.canvas.axes, alpha=0.7)
            y_col = f"{y_col}分布"
        
        self.canvas.axes.set_xlabel(x_col)
        self.canvas.axes.set_ylabel(y_col)
        self.canvas.axes.set_title(f"{y_col} by {x_col}")
    
    def create_box_plot(self):
        """创建箱线图"""
        # 选择数值列
        numeric_cols = self.data.select_dtypes(include=[np.number]).columns.tolist()
        
        if len(numeric_cols) == 0:
            QMessageBox.warning(self, "警告", "没有数值列可用于箱线图")
            return
        
        # 只显示前10列以避免过于拥挤
        if len(numeric_cols) > 10:
            numeric_cols = numeric_cols[:10]
        
        self.data[numeric_cols].plot(kind='box', ax=self.canvas.axes)
        self.canvas.axes.set_title("数据分布箱线图")
        self.canvas.axes.tick_params(axis='x', rotation=45)
    
    def create_heatmap(self):
        """创建热图"""
        # 计算相关性矩阵
        numeric_data = self.data.select_dtypes(include=[np.number])
        
        if len(numeric_data.columns) < 2:
            QMessageBox.warning(self, "警告", "需要至少两个数值列来创建热图")
            return
        
        corr_matrix = numeric_data.corr()
        
        # 创建热图
        sns.heatmap(corr_matrix, annot=True, cmap='coolwarm', center=0, ax=self.canvas.axes)
        self.canvas.axes.set_title("相关性热图")
    
    def create_pca_plot(self):
        """创建PCA图"""
        # 选择数值列
        numeric_data = self.data.select_dtypes(include=[np.number]).dropna()
        
        if len(numeric_data.columns) < 2:
            QMessageBox.warning(self, "警告", "需要至少两个数值列来执行PCA")
            return
        
        # 执行PCA
        scaler = StandardScaler()
        scaled_data = scaler.fit_transform(numeric_data)
        
        pca = PCA(n_components=2)
        principal_components = pca.fit_transform(scaled_data)
        
        # 创建散点图
        scatter = self.canvas.axes.scatter(principal_components[:, 0], principal_components[:, 1], alpha=0.7)
        self.canvas.axes.set_xlabel(f'PC1 ({pca.explained_variance_ratio_[0]:.2%} 方差)')
        self.canvas.axes.set_ylabel(f'PC2 ({pca.explained_variance_ratio_[1]:.2%} 方差)')
        self.canvas.axes.set_title("PCA分析")
        
        # 添加颜色编码（如果选择了颜色依据）
        color_col = self.color_by_combo.currentText()
        if color_col != "无" and color_col in self.data.columns:
            unique_colors = self.data[color_col].nunique()
            scatter = self.canvas.axes.scatter(
                principal_components[:, 0], principal_components[:, 1], 
                c=self.data[color_col], alpha=0.7, cmap='viridis'
            )
            self.canvas.fig.colorbar(scatter, ax=self.canvas.axes, label=color_col)
    
    def create_cluster_plot(self):
        """创建聚类图"""
        # 选择数值列
        numeric_data = self.data.select_dtypes(include=[np.number]).dropna()
        
        if len(numeric_data.columns) < 2:
            QMessageBox.warning(self, "警告", "需要至少两个数值列来执行聚类")
            return
        
        # 执行K-means聚类
        scaler = StandardScaler()
        scaled_data = scaler.fit_transform(numeric_data)
        
        kmeans = KMeans(n_clusters=3, random_state=42)
        clusters = kmeans.fit_predict(scaled_data)
        
        # 使用前两个特征创建散点图
        scatter = self.canvas.axes.scatter(scaled_data[:, 0], scaled_data[:, 1], c=clusters, alpha=0.7, cmap='viridis')
        self.canvas.axes.set_xlabel(numeric_data.columns[0])
        self.canvas.axes.set_ylabel(numeric_data.columns[1])
        self.canvas.axes.set_title("K-means聚类分析")
        self.canvas.fig.colorbar(scatter, ax=self.canvas.axes, label='聚类')


class DataTableWidget(QWidget):
    """数据表格组件"""
    
    def __init__(self):
        super().__init__()
        self.data = None
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 工具栏
        toolbar_layout = QHBoxLayout()
        
        self.load_button = QPushButton("加载数据")
        self.load_button.clicked.connect(self.load_data)
        
        self.save_button = QPushButton("保存数据")
        self.save_button.clicked.connect(self.save_data)
        
        self.filter_button = QPushButton("筛选数据")
        self.filter_button.clicked.connect(self.filter_data)
        
        self.stats_button = QPushButton("显示统计信息")
        self.stats_button.clicked.connect(self.show_statistics)
        
        toolbar_layout.addWidget(self.load_button)
        toolbar_layout.addWidget(self.save_button)
        toolbar_layout.addWidget(self.filter_button)
        toolbar_layout.addWidget(self.stats_button)
        toolbar_layout.addStretch()
        
        layout.addLayout(toolbar_layout)
        
        # 数据表格
        self.table = QTableWidget()
        layout.addWidget(self.table)
        
        self.setLayout(layout)
    
    def load_data(self):
        """加载数据"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "打开数据文件", "", 
            "CSV文件 (*.csv);;Excel文件 (*.xlsx *.xls);;所有文件 (*)"
        )
        
        if file_path:
            try:
                if file_path.endswith('.csv'):
                    self.data = pd.read_csv(file_path)
                else:  # Excel文件
                    self.data = pd.read_excel(file_path)
                
                self.populate_table()
                QMessageBox.information(self, "成功", f"已加载数据: {len(self.data)} 行, {len(self.data.columns)} 列")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"加载数据时出错: {str(e)}")
    
    def save_data(self):
        """保存数据"""
        if self.data is None:
            QMessageBox.warning(self, "警告", "没有数据可保存")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存数据文件", "", 
            "CSV文件 (*.csv);;Excel文件 (*.xlsx);;所有文件 (*)"
        )
        
        if file_path:
            try:
                if file_path.endswith('.csv'):
                    self.data.to_csv(file_path, index=False)
                else:  # Excel文件
                    self.data.to_excel(file_path, index=False)
                
                QMessageBox.information(self, "成功", f"数据已保存到: {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"保存数据时出错: {str(e)}")
    
    def populate_table(self):
        """填充表格"""
        if self.data is None:
            return
        
        self.table.setRowCount(len(self.data))
        self.table.setColumnCount(len(self.data.columns))
        self.table.setHorizontalHeaderLabels(self.data.columns)
        
        for i in range(len(self.data)):
            for j in range(len(self.data.columns)):
                item = QTableWidgetItem(str(self.data.iloc[i, j]))
                self.table.setItem(i, j, item)
        
        # 调整列宽
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
    
    def filter_data(self):
        """筛选数据"""
        if self.data is None:
            QMessageBox.warning(self, "警告", "没有数据可筛选")
            return
        
        # 创建筛选对话框
        dialog = QDialog(self)
        dialog.setWindowTitle("数据筛选")
        dialog.setModal(True)
        dialog.resize(400, 300)
        
        layout = QFormLayout()
        
        column_combo = QComboBox()
        column_combo.addItems(self.data.columns.tolist())
        
        operator_combo = QComboBox()
        operator_combo.addItems([">", ">=", "=", "!=", "<", "<=", "包含"])
        
        value_edit = QLineEdit()
        
        layout.addRow("列:", column_combo)
        layout.addRow("操作符:", operator_combo)
        layout.addRow("值:", value_edit)
        
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        
        layout.addRow(button_box)
        dialog.setLayout(layout)
        
        if dialog.exec_() == QDialog.Accepted:
            column = column_combo.currentText()
            operator = operator_combo.currentText()
            value = value_edit.text()
            
            try:
                if operator == ">":
                    filtered_data = self.data[self.data[column] > float(value)]
                elif operator == ">=":
                    filtered_data = self.data[self.data[column] >= float(value)]
                elif operator == "=":
                    if self.data[column].dtype == 'object':
                        filtered_data = self.data[self.data[column] == value]
                    else:
                        filtered_data = self.data[self.data[column] == float(value)]
                elif operator == "!=":
                    if self.data[column].dtype == 'object':
                        filtered_data = self.data[self.data[column] != value]
                    else:
                        filtered_data = self.data[self.data[column] != float(value)]
                elif operator == "<":
                    filtered_data = self.data[self.data[column] < float(value)]
                elif operator == "<=":
                    filtered_data = self.data[self.data[column] <= float(value)]
                elif operator == "包含":
                    filtered_data = self.data[self.data[column].astype(str).str.contains(value, na=False)]
                
                self.data = filtered_data
                self.populate_table()
                QMessageBox.information(self, "成功", f"筛选后数据: {len(self.data)} 行")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"筛选数据时出错: {str(e)}")
    
    def show_statistics(self):
        """显示统计信息"""
        if self.data is None:
            QMessageBox.warning(self, "警告", "没有数据可分析")
            return
        
        # 创建统计信息对话框
        dialog = QDialog(self)
        dialog.setWindowTitle("数据统计信息")
        dialog.setModal(True)
        dialog.resize(500, 400)
        
        layout = QVBoxLayout()
        
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        
        # 生成统计信息
        stats_text = f"数据形状: {self.data.shape[0]} 行, {self.data.shape[1]} 列\n\n"
        
        # 基本统计信息
        stats_text += "基本统计信息:\n"
        stats_text += self.data.describe().to_string()
        
        # 缺失值信息
        stats_text += "\n\n缺失值统计:\n"
        missing_stats = self.data.isnull().sum()
        for col, count in missing_stats.items():
            stats_text += f"{col}: {count} 个缺失值 ({count/len(self.data)*100:.2f}%)\n"
        
        # 数据类型信息
        stats_text += "\n数据类型:\n"
        dtypes_info = self.data.dtypes.value_counts()
        for dtype, count in dtypes_info.items():
            stats_text += f"{dtype}: {count} 列\n"
        
        text_edit.setText(stats_text)
        layout.addWidget(text_edit)
        
        button_box = QDialogButtonBox(QDialogButtonBox.Close)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        
        dialog.setLayout(layout)
        dialog.exec_()


class ExperimentManagerWidget(QWidget):
    """实验管理组件"""
    
    def __init__(self, db_manager):
        super().__init__()
        self.db_manager = db_manager
        self.init_ui()
        self.load_experiments()
    
    def init_ui(self):
        layout = QHBoxLayout()
        
        # 左侧：实验列表
        left_widget = QWidget()
        left_layout = QVBoxLayout()
        
        # 工具栏
        toolbar_layout = QHBoxLayout()
        
        self.add_button = QPushButton("新建实验")
        self.add_button.clicked.connect(self.add_experiment)
        
        self.edit_button = QPushButton("编辑实验")
        self.edit_button.clicked.connect(self.edit_experiment)
        
        self.delete_button = QPushButton("删除实验")
        self.delete_button.clicked.connect(self.delete_experiment)
        
        toolbar_layout.addWidget(self.add_button)
        toolbar_layout.addWidget(self.edit_button)
        toolbar_layout.addWidget(self.delete_button)
        toolbar_layout.addStretch()
        
        left_layout.addLayout(toolbar_layout)
        
        # 实验列表
        self.experiment_list = QListWidget()
        self.experiment_list.itemSelectionChanged.connect(self.on_experiment_selected)
        left_layout.addWidget(self.experiment_list)
        
        left_widget.setLayout(left_layout)
        
        # 右侧：实验详情
        right_widget = QWidget()
        right_layout = QVBoxLayout()
        
        # 实验信息
        info_group = QGroupBox("实验信息")
        info_layout = QFormLayout()
        
        self.name_label = QLabel()
        self.description_label = QLabel()
        self.researcher_label = QLabel()
        self.date_label = QLabel()
        self.status_label = QLabel()
        
        info_layout.addRow("名称:", self.name_label)
        info_layout.addRow("描述:", self.description_label)
        info_layout.addRow("研究人员:", self.researcher_label)
        info_layout.addRow("创建日期:", self.date_label)
        info_layout.addRow("状态:", self.status_label)
        
        info_group.setLayout(info_layout)
        right_layout.addWidget(info_group)
        
        # 分析结果
        results_group = QGroupBox("分析结果")
        results_layout = QVBoxLayout()
        
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(4)
        self.results_table.setHorizontalHeaderLabels(["分析类型", "参数", "结果", "日期"])
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        
        results_layout.addWidget(self.results_table)
        results_group.setLayout(results_layout)
        right_layout.addWidget(results_group)
        
        right_widget.setLayout(right_layout)
        
        # 分割器
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([300, 500])
        
        layout.addWidget(splitter)
        self.setLayout(layout)
    
    def load_experiments(self):
        """加载实验列表"""
        self.experiment_list.clear()
        experiments = self.db_manager.get_experiments()
        
        for exp in experiments:
            item = QListWidgetItem(f"{exp[1]} ({exp[4]})")
            item.setData(Qt.UserRole, exp[0])  # 存储实验ID
            self.experiment_list.addItem(item)
    
    def on_experiment_selected(self):
        """当选择实验时更新详情"""
        selected_items = self.experiment_list.selectedItems()
        
        if not selected_items:
            return
        
        experiment_id = selected_items[0].data(Qt.UserRole)
        
        # 获取实验详情
        conn = sqlite3.connect(self.db_manager.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM experiments WHERE id = ?', (experiment_id,))
        experiment = cursor.fetchone()
        
        if experiment:
            self.name_label.setText(experiment[1])
            self.description_label.setText(experiment[2] or "无")
            self.researcher_label.setText(experiment[4] or "未知")
            self.date_label.setText(experiment[3] or "未知")
            self.status_label.setText(experiment[5] or "未知")
        
        # 获取分析结果
        cursor.execute('SELECT * FROM analysis_results WHERE experiment_id = ? ORDER BY date_created DESC', (experiment_id,))
        results = cursor.fetchall()
        
        self.results_table.setRowCount(len(results))
        for i, result in enumerate(results):
            self.results_table.setItem(i, 0, QTableWidgetItem(result[2]))
            self.results_table.setItem(i, 1, QTableWidgetItem(result[3] or "无"))
            self.results_table.setItem(i, 2, QTableWidgetItem(result[4] or "无"))
            self.results_table.setItem(i, 3, QTableWidgetItem(result[5] or "未知"))
        
        conn.close()
    
    def add_experiment(self):
        """添加新实验"""
        dialog = QDialog(self)
        dialog.setWindowTitle("新建实验")
        dialog.setModal(True)
        
        layout = QFormLayout()
        
        name_edit = QLineEdit()
        description_edit = QTextEdit()
        description_edit.setMaximumHeight(100)
        researcher_edit = QLineEdit()
        
        layout.addRow("实验名称:", name_edit)
        layout.addRow("实验描述:", description_edit)
        layout.addRow("研究人员:", researcher_edit)
        
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        
        layout.addRow(button_box)
        dialog.setLayout(layout)
        
        if dialog.exec_() == QDialog.Accepted:
            name = name_edit.text().strip()
            description = description_edit.toPlainText().strip()
            researcher = researcher_edit.text().strip()
            
            if not name:
                QMessageBox.warning(self, "警告", "实验名称不能为空")
                return
            
            try:
                self.db_manager.add_experiment(name, description, researcher)
                self.load_experiments()
                QMessageBox.information(self, "成功", "实验已创建")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"创建实验时出错: {str(e)}")
    
    def edit_experiment(self):
        """编辑实验"""
        # 实现编辑实验功能
        QMessageBox.information(self, "信息", "编辑实验功能待实现")
    
    def delete_experiment(self):
        """删除实验"""
        selected_items = self.experiment_list.selectedItems()
        
        if not selected_items:
            QMessageBox.warning(self, "警告", "请先选择一个实验")
            return
        
        experiment_name = selected_items[0].text()
        
        reply = QMessageBox.question(
            self, "确认删除", 
            f"确定要删除实验 '{experiment_name}' 吗？此操作不可撤销。",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # 实现删除实验功能
            QMessageBox.information(self, "信息", "删除实验功能待实现")


class AdvancedAnalysisWidget(QWidget):
    """高级分析组件"""
    
    def __init__(self):
        super().__init__()
        self.data = None
        self.analysis_thread = None
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 控制面板
        control_layout = QHBoxLayout()
        
        self.analysis_type_combo = QComboBox()
        self.analysis_type_combo.addItems(["PCA分析", "聚类分析", "统计分析"])
        
        self.parameters_group = QGroupBox("分析参数")
        parameters_layout = QFormLayout()
        
        self.n_components_spin = QSpinBox()
        self.n_components_spin.setRange(2, 10)
        self.n_components_spin.setValue(2)
        
        self.n_clusters_spin = QSpinBox()
        self.n_clusters_spin.setRange(2, 10)
        self.n_clusters_spin.setValue(3)
        
        parameters_layout.addRow("主成分数量:", self.n_components_spin)
        parameters_layout.addRow("聚类数量:", self.n_clusters_spin)
        
        self.parameters_group.setLayout(parameters_layout)
        
        self.run_button = QPushButton("运行分析")
        self.run_button.clicked.connect(self.run_analysis)
        
        control_layout.addWidget(QLabel("分析类型:"))
        control_layout.addWidget(self.analysis_type_combo)
        control_layout.addWidget(self.parameters_group)
        control_layout.addWidget(self.run_button)
        control_layout.addStretch()
        
        layout.addLayout(control_layout)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # 结果展示区域
        self.results_tabs = QTabWidget()
        
        # 文本结果标签页
        self.text_results = QTextEdit()
        self.text_results.setReadOnly(True)
        self.results_tabs.addTab(self.text_results, "文本结果")
        
        # 可视化结果标签页
        self.viz_widget = DataVisualizationWidget()
        self.results_tabs.addTab(self.viz_widget, "可视化")
        
        layout.addWidget(self.results_tabs)
        
        self.setLayout(layout)
    
    def set_data(self, data):
        """设置数据"""
        self.data = data
        self.viz_widget.set_data(data)
    
    def run_analysis(self):
        """运行分析"""
        if self.data is None or self.data.empty:
            QMessageBox.warning(self, "警告", "没有数据可分析")
            return
        
        analysis_type = self.analysis_type_combo.currentText()
        
        # 准备参数
        parameters = {}
        if analysis_type == "PCA分析":
            parameters['n_components'] = self.n_components_spin.value()
            analysis_key = "pca"
        elif analysis_type == "聚类分析":
            parameters['n_clusters'] = self.n_clusters_spin.value()
            analysis_key = "cluster"
        else:  # 统计分析
            analysis_key = "stats"
        
        # 只使用数值列
        numeric_data = self.data.select_dtypes(include=[np.number]).dropna()
        
        if len(numeric_data.columns) == 0:
            QMessageBox.warning(self, "警告", "没有数值列可用于分析")
            return
        
        # 禁用运行按钮，显示进度条
        self.run_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # 创建并启动分析线程
        self.analysis_thread = AnalysisWorker(analysis_key, numeric_data, parameters)
        self.analysis_thread.progress_updated.connect(self.progress_bar.setValue)
        self.analysis_thread.analysis_finished.connect(self.on_analysis_finished)
        self.analysis_thread.error_occurred.connect(self.on_analysis_error)
        self.analysis_thread.start()
    
    def on_analysis_finished(self, result):
        """分析完成"""
        self.run_button.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        # 显示结果
        analysis_type = self.analysis_type_combo.currentText()
        
        if analysis_type == "PCA分析":
            self.display_pca_results(result)
        elif analysis_type == "聚类分析":
            self.display_cluster_results(result)
        else:  # 统计分析
            self.display_statistical_results(result)
    
    def on_analysis_error(self, error_message):
        """分析出错"""
        self.run_button.setEnabled(True)
        self.progress_bar.setVisible(False)
        QMessageBox.critical(self, "分析错误", error_message)
    
    def display_pca_results(self, result):
        """显示PCA结果"""
        text = "PCA分析结果:\n\n"
        text += f"解释方差比例: {result['explained_variance']}\n"
        text += f"累计解释方差: {sum(result['explained_variance']):.4f}\n\n"
        
        text += "主成分特征重要性:\n"
        for i, component in enumerate(result['feature_importance']):
            text += f"PC{i+1}: {component}\n"
        
        self.text_results.setText(text)
        
        # 更新可视化组件
        pca_data = pd.DataFrame(result['components'], columns=[f'PC{i+1}' for i in range(result['components'].shape[1])])
        self.viz_widget.set_data(pca_data)
        self.viz_widget.plot_type_combo.setCurrentText("散点图")
        self.viz_widget.generate_plot()
    
    def display_cluster_results(self, result):
        """显示聚类结果"""
        text = "聚类分析结果:\n\n"
        text += f"聚类数量: {len(np.unique(result['clusters']))}\n"
        text += f"聚类内平方和 (Inertia): {result['inertia']:.4f}\n\n"
        
        text += "聚类中心:\n"
        for i, center in enumerate(result['centers']):
            text += f"聚类 {i}: {center}\n"
        
        self.text_results.setText(text)
        
        # 更新可视化组件
        cluster_data = self.data.select_dtypes(include=[np.number]).dropna().copy()
        cluster_data['Cluster'] = result['clusters']
        self.viz_widget.set_data(cluster_data)
        self.viz_widget.plot_type_combo.setCurrentText("聚类分析")
        self.viz_widget.generate_plot()
    
    def display_statistical_results(self, result):
        """显示统计分析结果"""
        text = "统计分析结果:\n\n"
        
        # 描述性统计
        text += "描述性统计:\n"
        for col, stats in result['descriptive'].items():
            text += f"{col}:\n"
            text += f"  均值: {stats['mean']:.4f}\n"
            text += f"  标准差: {stats['std']:.4f}\n"
            text += f"  最小值: {stats['min']:.4f}\n"
            text += f"  最大值: {stats['max']:.4f}\n\n"
        
        # 相关性分析
        if 'correlation' in result:
            text += "相关性矩阵:\n"
            for col1, corrs in result['correlation'].items():
                text += f"{col1}:\n"
                for col2, corr in corrs.items():
                    text += f"  {col2}: {corr:.4f}\n"
                text += "\n"
        
        # 正态性检验
        if 'normality' in result:
            text += "正态性检验 (p值):\n"
            for col, p_value in result['normality'].items():
                text += f"{col}: {p_value:.4f} "
                text += "(正态分布)" if p_value > 0.05 else "(非正态分布)"
                text += "\n"
        
        self.text_results.setText(text)
        
        # 更新可视化组件
        self.viz_widget.plot_type_combo.setCurrentText("箱线图")
        self.viz_widget.generate_plot()


class BioPharmaToolkit(QMainWindow):
    """生物制药系统主窗口"""
    
    def __init__(self):
        super().__init__()
        self.data = None
        self.db_manager = DatabaseManager()
        self.init_ui()
        self.load_settings()
    
    def init_ui(self):
        self.setWindowTitle("生物制药系统高级工具库")
        self.setGeometry(100, 100, 1200, 800)
        
        # 创建中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        layout = QVBoxLayout()
        central_widget.setLayout(layout)
        
        # 创建标签页
        self.tabs = QTabWidget()
        
        # 数据管理标签页
        self.data_table = DataTableWidget()
        self.tabs.addTab(self.data_table, "数据管理")
        
        # 可视化标签页
        self.viz_widget = DataVisualizationWidget()
        self.tabs.addTab(self.viz_widget, "数据可视化")
        
        # 高级分析标签页
        self.analysis_widget = AdvancedAnalysisWidget()
        self.tabs.addTab(self.analysis_widget, "高级分析")
        
        # 实验管理标签页
        self.experiment_widget = ExperimentManagerWidget(self.db_manager)
        self.tabs.addTab(self.experiment_widget, "实验管理")
        
        layout.addWidget(self.tabs)
        
        # 创建菜单栏
        self.create_menubar()
        
        # 创建工具栏
        self.create_toolbar()
        
        # 创建状态栏
        self.statusBar().showMessage("就绪")
        
        # 连接信号
        self.data_table.table.itemChanged.connect(self.on_data_changed)
        self.tabs.currentChanged.connect(self.on_tab_changed)
    
    def create_menubar(self):
        """创建菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu("文件")
        
        load_action = QAction("加载数据", self)
        load_action.setShortcut("Ctrl+O")
        load_action.triggered.connect(self.data_table.load_data)
        file_menu.addAction(load_action)
        
        save_action = QAction("保存数据", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.data_table.save_data)
        file_menu.addAction(save_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("退出", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 分析菜单
        analysis_menu = menubar.addMenu("分析")
        
        pca_action = QAction("PCA分析", self)
        pca_action.triggered.connect(lambda: self.switch_to_analysis("PCA分析"))
        analysis_menu.addAction(pca_action)
        
        cluster_action = QAction("聚类分析", self)
        cluster_action.triggered.connect(lambda: self.switch_to_analysis("聚类分析"))
        analysis_menu.addAction(cluster_action)
        
        stats_action = QAction("统计分析", self)
        stats_action.triggered.connect(lambda: self.switch_to_analysis("统计分析"))
        analysis_menu.addAction(stats_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu("帮助")
        
        about_action = QAction("关于", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def create_toolbar(self):
        """创建工具栏"""
        toolbar = self.addToolBar("主工具栏")
        
        load_action = QAction("加载数据", self)
        load_action.triggered.connect(self.data_table.load_data)
        toolbar.addAction(load_action)
        
        save_action = QAction("保存数据", self)
        save_action.triggered.connect(self.data_table.save_data)
        toolbar.addAction(save_action)
        
        toolbar.addSeparator()
        
        viz_action = QAction("数据可视化", self)
        viz_action.triggered.connect(lambda: self.tabs.setCurrentIndex(1))
        toolbar.addAction(viz_action)
        
        analysis_action = QAction("高级分析", self)
        analysis_action.triggered.connect(lambda: self.tabs.setCurrentIndex(2))
        toolbar.addAction(analysis_action)
    
    def on_data_changed(self, item):
        """当数据更改时更新其他组件"""
        if self.data is not None:
            # 更新表格中的数据
            row = item.row()
            col = item.column()
            new_value = item.text()
            
            try:
                # 尝试转换为适当的数据类型
                if self.data.iloc[row, col] is not None:
                    if isinstance(self.data.iloc[row, col], (int, float)):
                        new_value = float(new_value) if '.' in new_value else int(new_value)
                
                self.data.iloc[row, col] = new_value
            except ValueError:
                QMessageBox.warning(self, "警告", f"无效的数据类型: {new_value}")
    
    def on_tab_changed(self, index):
        """当切换标签页时更新数据"""
        if index == 1:  # 可视化标签页
            self.viz_widget.set_data(self.data)
        elif index == 2:  # 高级分析标签页
            self.analysis_widget.set_data(self.data)
    
    def switch_to_analysis(self, analysis_type):
        """切换到分析标签页并设置分析类型"""
        self.tabs.setCurrentIndex(2)  # 切换到高级分析标签页
        self.analysis_widget.analysis_type_combo.setCurrentText(analysis_type)
    
    def show_about(self):
        """显示关于对话框"""
        QMessageBox.about(self, "关于", 
                         "生物制药系统高级工具库\n\n"
                         "版本: 1.0\n"
                         "版权所有 © 2023 生物制药研究团队\n\n"
                         "这是一个用于生物制药数据分析和可视化的高级工具库。")
    
    def load_settings(self):
        """加载设置"""
        settings = QSettings("BioPharma", "Toolkit")
        geometry = settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
    
    def closeEvent(self, event):
        """关闭事件处理"""
        # 保存设置
        settings = QSettings("BioPharma", "Toolkit")
        settings.setValue("geometry", self.saveGeometry())
        
        # 确认退出
        reply = QMessageBox.question(
            self, "确认退出", 
            "确定要退出应用程序吗？",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()


def main():
    """主函数"""
    app = QApplication(sys.argv)
    
    # 设置应用程序属性
    app.setApplicationName("生物制药系统高级工具库")
    app.setApplicationVersion("1.0")
    app.setOrganizationName("BioPharma")
    
    # 创建并显示主窗口
    window = BioPharmaToolkit()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()