import sys
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QSplitter, QTabWidget, QTableWidget, QTableWidgetItem, 
                             QTreeWidget, QTreeWidgetItem, QToolBar, QStatusBar, 
                             QAction, QFileDialog, QMessageBox, QComboBox, QPushButton,
                             QLabel, QTextEdit, QHeaderView, QProgressBar, QDialog,
                             QGridLayout, QLineEdit, QDialogButtonBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt5.QtGui import QIcon, QFont, QColor
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import seaborn as sns
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures
import plotly.graph_objs as go
import plotly.offline as pyo
import plotly.express as px
from plotly.subplots import make_subplots


class DatabaseWorker(QThread):
    """后台数据库工作线程"""
    progress = pyqtSignal(int)
    result = pyqtSignal(object)
    error = pyqtSignal(str)
    
    def __init__(self, db_path, query=None, parent=None):
        super().__init__(parent)
        self.db_path = db_path
        self.query = query
        self.conn = None
        
    def run(self):
        try:
            self.conn = sqlite3.connect(self.db_path)
            if self.query:
                df = pd.read_sql_query(self.query, self.conn)
                self.result.emit(df)
            else:
                # 获取数据库结构
                cursor = self.conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = cursor.fetchall()
                result = {}
                for table in tables:
                    table_name = table[0]
                    cursor.execute(f"PRAGMA table_info({table_name})")
                    columns = cursor.fetchall()
                    result[table_name] = [col[1] for col in columns]
                self.result.emit(result)
            self.conn.close()
        except Exception as e:
            self.error.emit(str(e))
            
    def cancel(self):
        if self.conn:
            self.conn.close()


class PredictionDialog(QDialog):
    """数据预测对话框"""
    def __init__(self, df, parent=None):
        super().__init__(parent)
        self.df = df
        self.setWindowTitle("数据预测分析")
        self.setGeometry(100, 100, 800, 600)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # 选择列进行预测
        grid_layout = QGridLayout()
        grid_layout.addWidget(QLabel("自变量(X):"), 0, 0)
        self.x_combo = QComboBox()
        self.x_combo.addItems(self.df.select_dtypes(include=[np.number]).columns.tolist())
        grid_layout.addWidget(self.x_combo, 0, 1)
        
        grid_layout.addWidget(QLabel("因变量(Y):"), 1, 0)
        self.y_combo = QComboBox()
        self.y_combo.addItems(self.df.select_dtypes(include=[np.number]).columns.tolist())
        grid_layout.addWidget(self.y_combo, 1, 1)
        
        grid_layout.addWidget(QLabel("预测点数:"), 2, 0)
        self.points_input = QLineEdit("10")
        grid_layout.addWidget(self.points_input, 2, 1)
        
        grid_layout.addWidget(QLabel("多项式次数:"), 3, 0)
        self.degree_input = QLineEdit("2")
        grid_layout.addWidget(self.degree_input, 3, 1)
        
        layout.addLayout(grid_layout)
        
        # 按钮
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
    
    def get_params(self):
        return {
            'x_col': self.x_combo.currentText(),
            'y_col': self.y_combo.currentText(),
            'points': int(self.points_input.text()),
            'degree': int(self.degree_input.text())
        }


class MplCanvas(FigureCanvas):
    """Matplotlib画布"""
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_subplot(111)
        super().__init__(self.fig)
        self.setParent(parent)


class DatabaseAnalyzer(QMainWindow):
    """主应用程序窗口"""
    def __init__(self):
        super().__init__()
        self.db_path = None
        self.current_df = None
        self.db_structure = {}
        self.setWindowTitle("高级数据库分析可视化工具")
        self.setGeometry(100, 50, 1400, 900)
        self.setup_ui()
        
    def setup_ui(self):
        # 创建中央部件和主布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        
        # 左侧数据库结构树
        self.db_tree = QTreeWidget()
        self.db_tree.setHeaderLabel("数据库结构")
        self.db_tree.itemClicked.connect(self.on_tree_item_clicked)
        splitter.addWidget(self.db_tree)
        
        # 右侧选项卡部件
        self.tab_widget = QTabWidget()
        
        # 数据表选项卡
        self.table_tab = QWidget()
        self.table_layout = QVBoxLayout(self.table_tab)
        self.data_table = QTableWidget()
        self.table_layout.addWidget(self.data_table)
        self.tab_widget.addTab(self.table_tab, "数据视图")
        
        # 查询编辑器选项卡
        self.query_tab = QWidget()
        self.query_layout = QVBoxLayout(self.query_tab)
        self.query_editor = QTextEdit()
        self.query_editor.setPlaceholderText("输入SQL查询语句...")
        self.query_layout.addWidget(QLabel("SQL查询:"))
        self.query_layout.addWidget(self.query_editor)
        
        query_btn_layout = QHBoxLayout()
        self.execute_btn = QPushButton("执行查询")
        self.execute_btn.clicked.connect(self.execute_query)
        self.clear_btn = QPushButton("清除")
        self.clear_btn.clicked.connect(self.clear_query)
        query_btn_layout.addWidget(self.execute_btn)
        query_btn_layout.addWidget(self.clear_btn)
        query_btn_layout.addStretch()
        self.query_layout.addLayout(query_btn_layout)
        
        self.tab_widget.addTab(self.query_tab, "查询编辑器")
        
        # 可视化选项卡
        self.viz_tab = QWidget()
        self.viz_layout = QVBoxLayout(self.viz_tab)
        
        # 可视化控制按钮
        viz_control_layout = QHBoxLayout()
        self.viz_type_combo = QComboBox()
        self.viz_type_combo.addItems(["折线图", "柱状图", "散点图", "饼图", "热力图", "箱线图"])
        viz_control_layout.addWidget(QLabel("图表类型:"))
        viz_control_layout.addWidget(self.viz_type_combo)
        
        self.x_axis_combo = QComboBox()
        viz_control_layout.addWidget(QLabel("X轴:"))
        viz_control_layout.addWidget(self.x_axis_combo)
        
        self.y_axis_combo = QComboBox()
        viz_control_layout.addWidget(QLabel("Y轴:"))
        viz_control_layout.addWidget(self.y_axis_combo)
        
        self.generate_viz_btn = QPushButton("生成图表")
        self.generate_viz_btn.clicked.connect(self.generate_visualization)
        viz_control_layout.addWidget(self.generate_viz_btn)
        
        self.predict_btn = QPushButton("预测分析")
        self.predict_btn.clicked.connect(self.show_prediction_dialog)
        viz_control_layout.addWidget(self.predict_btn)
        
        viz_control_layout.addStretch()
        self.viz_layout.addLayout(viz_control_layout)
        
        # Matplotlib画布
        self.canvas = MplCanvas(self, width=10, height=8, dpi=100)
        self.viz_layout.addWidget(self.canvas)
        
        self.tab_widget.addTab(self.viz_tab, "数据可视化")
        
        splitter.addWidget(self.tab_widget)
        splitter.setSizes([200, 1200])
        
        main_layout.addWidget(splitter)
        
        # 创建工具栏
        self.setup_toolbar()
        
        # 创建状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(200)
        self.progress_bar.setVisible(False)
        self.status_bar.addPermanentWidget(self.progress_bar)
        
    def setup_toolbar(self):
        toolbar = QToolBar("主工具栏")
        toolbar.setIconSize(QSize(32, 32))
        self.addToolBar(toolbar)
        
        # 打开数据库动作
        open_action = QAction(QIcon(":file-open.png"), "打开数据库", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.open_database)
        toolbar.addAction(open_action)
        
        toolbar.addSeparator()
        
        # 导出数据动作
        export_action = QAction(QIcon(":export.png"), "导出数据", self)
        export_action.setShortcut("Ctrl+E")
        export_action.triggered.connect(self.export_data)
        toolbar.addAction(export_action)
        
        # 刷新动作
        refresh_action = QAction(QIcon(":refresh.png"), "刷新", self)
        refresh_action.setShortcut("F5")
        refresh_action.triggered.connect(self.refresh_database)
        toolbar.addAction(refresh_action)
        
    def open_database(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "打开数据库文件", "", "SQLite数据库 (*.db *.sqlite *.sqlite3);;所有文件 (*)"
        )
        
        if file_path:
            self.db_path = file_path
            self.load_database_structure()
            
    def load_database_structure(self):
        self.status_bar.showMessage("正在加载数据库结构...")
        self.progress_bar.setVisible(True)
        
        self.worker = DatabaseWorker(self.db_path)
        self.worker.result.connect(self.handle_db_structure)
        self.worker.error.connect(self.handle_db_error)
        self.worker.start()
        
    def handle_db_structure(self, structure):
        self.db_structure = structure
        self.db_tree.clear()
        
        for table_name, columns in structure.items():
            table_item = QTreeWidgetItem(self.db_tree, [table_name])
            for column in columns:
                QTreeWidgetItem(table_item, [column])
                
        self.status_bar.showMessage(f"数据库加载成功: {self.db_path}")
        self.progress_bar.setVisible(False)
        
    def handle_db_error(self, error_msg):
        QMessageBox.critical(self, "数据库错误", f"加载数据库时出错:\n{error_msg}")
        self.status_bar.showMessage("数据库加载失败")
        self.progress_bar.setVisible(False)
        
    def on_tree_item_clicked(self, item, column):
        # 只处理表名点击，不处理列名点击
        if item.parent() is None:
            table_name = item.text(0)
            self.load_table_data(table_name)
            
    def load_table_data(self, table_name):
        self.status_bar.showMessage(f"正在加载表数据: {table_name}")
        self.progress_bar.setVisible(True)
        
        query = f"SELECT * FROM {table_name}"
        self.worker = DatabaseWorker(self.db_path, query)
        self.worker.result.connect(self.handle_table_data)
        self.worker.error.connect(self.handle_db_error)
        self.worker.start()
        
    def handle_table_data(self, df):
        self.current_df = df
        
        # 更新数据表
        self.data_table.setRowCount(df.shape[0])
        self.data_table.setColumnCount(df.shape[1])
        self.data_table.setHorizontalHeaderLabels(df.columns)
        
        for row in range(df.shape[0]):
            for col in range(df.shape[1]):
                value = df.iat[row, col]
                item = QTableWidgetItem(str(value) if value is not None else "NULL")
                self.data_table.setItem(row, col, item)
                
        self.data_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        # 更新可视化选项
        self.update_viz_comboboxes(df)
        
        self.status_bar.showMessage(f"已加载 {df.shape[0]} 行数据")
        self.progress_bar.setVisible(False)
        
    def update_viz_comboboxes(self, df):
        self.x_axis_combo.clear()
        self.y_axis_combo.clear()
        
        numeric_columns = df.select_dtypes(include=[np.number]).columns.tolist()
        categorical_columns = df.select_dtypes(exclude=[np.number]).columns.tolist()
        
        self.x_axis_combo.addItems(categorical_columns + numeric_columns)
        self.y_axis_combo.addItems(numeric_columns)
        
    def execute_query(self):
        query = self.query_editor.toPlainText().strip()
        if not query:
            QMessageBox.warning(self, "查询错误", "请输入SQL查询语句")
            return
            
        self.status_bar.showMessage("正在执行查询...")
        self.progress_bar.setVisible(True)
        
        self.worker = DatabaseWorker(self.db_path, query)
        self.worker.result.connect(self.handle_query_result)
        self.worker.error.connect(self.handle_query_error)
        self.worker.start()
        
    def handle_query_result(self, df):
        self.current_df = df
        
        # 切换到数据视图选项卡
        self.tab_widget.setCurrentIndex(0)
        
        # 更新数据表
        self.data_table.setRowCount(df.shape[0])
        self.data_table.setColumnCount(df.shape[1])
        self.data_table.setHorizontalHeaderLabels(df.columns)
        
        for row in range(df.shape[0]):
            for col in range(df.shape[1]):
                value = df.iat[row, col]
                item = QTableWidgetItem(str(value) if value is not None else "NULL")
                self.data_table.setItem(row, col, item)
                
        self.data_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        # 更新可视化选项
        self.update_viz_comboboxes(df)
        
        self.status_bar.showMessage(f"查询成功，返回 {df.shape[0]} 行数据")
        self.progress_bar.setVisible(False)
        
    def handle_query_error(self, error_msg):
        QMessageBox.critical(self, "查询错误", f"执行查询时出错:\n{error_msg}")
        self.status_bar.showMessage("查询执行失败")
        self.progress_bar.setVisible(False)
        
    def clear_query(self):
        self.query_editor.clear()
        
    def generate_visualization(self):
        if self.current_df is None or self.current_df.empty:
            QMessageBox.warning(self, "数据错误", "没有可用的数据用于可视化")
            return
            
        viz_type = self.viz_type_combo.currentText()
        x_col = self.x_axis_combo.currentText()
        y_col = self.y_axis_combo.currentText() if self.y_axis_combo.count() > 0 else None
        
        # 清除之前的图表
        self.canvas.axes.clear()
        
        try:
            if viz_type == "折线图" and y_col:
                if self.current_df[x_col].dtype in [np.number, np.datetime64]:
                    self.current_df.plot.line(x=x_col, y=y_col, ax=self.canvas.axes)
                else:
                    # 对于分类变量，使用分组平均值
                    grouped = self.current_df.groupby(x_col)[y_col].mean()
                    grouped.plot.line(ax=self.canvas.axes)
                    self.canvas.axes.set_xlabel(x_col)
                    self.canvas.axes.set_ylabel(f"平均 {y_col}")
                    
            elif viz_type == "柱状图" and y_col:
                if self.current_df[x_col].dtype in [np.number, np.datetime64]:
                    # 对数值型变量进行分箱
                    binned = pd.cut(self.current_df[x_col], bins=10)
                    grouped = self.current_df.groupby(binned)[y_col].mean()
                    grouped.plot.bar(ax=self.canvas.axes)
                    self.canvas.axes.set_xlabel(x_col)
                    self.canvas.axes.set_ylabel(f"平均 {y_col}")
                else:
                    self.current_df.groupby(x_col)[y_col].mean().plot.bar(ax=self.canvas.axes)
                    
            elif viz_type == "散点图" and y_col:
                self.current_df.plot.scatter(x=x_col, y=y_col, ax=self.canvas.axes)
                
            elif viz_type == "饼图":
                if y_col:
                    # 使用y_col的值
                    values = self.current_df.groupby(x_col)[y_col].sum()
                    values.plot.pie(ax=self.canvas.axes, autopct='%1.1f%%')
                    self.canvas.axes.set_ylabel('')
                else:
                    # 仅使用x_col计数
                    counts = self.current_df[x_col].value_counts()
                    counts.plot.pie(ax=self.canvas.axes, autopct='%1.1f%%')
                    self.canvas.axes.set_ylabel('')
                    
            elif viz_type == "热力图":
                # 选择数值列计算相关性
                numeric_df = self.current_df.select_dtypes(include=[np.number])
                if numeric_df.shape[1] < 2:
                    QMessageBox.warning(self, "数据错误", "需要至少两个数值列生成热力图")
                    return
                    
                corr = numeric_df.corr()
                im = self.canvas.axes.imshow(corr, cmap='coolwarm', interpolation='nearest')
                self.canvas.axes.set_xticks(range(len(corr.columns)))
                self.canvas.axes.set_yticks(range(len(corr.columns)))
                self.canvas.axes.set_xticklabels(corr.columns, rotation=45)
                self.canvas.axes.set_yticklabels(corr.columns)
                
                # 添加颜色条
                plt.colorbar(im, ax=self.canvas.axes)
                
                # 添加数值标注
                for i in range(len(corr.columns)):
                    for j in range(len(corr.columns)):
                        text = self.canvas.axes.text(j, i, f'{corr.iloc[i, j]:.2f}',
                                       ha="center", va="center", color="w")
                        
            elif viz_type == "箱线图" and y_col:
                if self.current_df[x_col].dtype in [np.number]:
                    # 对数值型变量进行分箱
                    binned = pd.cut(self.current_df[x_col], bins=5)
                    groups = [group for _, group in self.current_df.groupby(binned)[y_col]]
                    labels = [str(interval) for interval in self.current_df.groupby(binned).groups.keys()]
                    self.canvas.axes.boxplot(groups, labels=labels)
                    self.canvas.axes.set_xlabel(x_col)
                    self.canvas.axes.set_ylabel(y_col)
                else:
                    groups = [group for _, group in self.current_df.groupby(x_col)[y_col]]
                    labels = [str(key) for key in self.current_df.groupby(x_col).groups.keys()]
                    self.canvas.axes.boxplot(groups, labels=labels)
                    self.canvas.axes.set_xlabel(x_col)
                    self.canvas.axes.set_ylabel(y_col)
                    
            self.canvas.axes.set_title(f"{viz_type}: {x_col} vs {y_col}" if y_col else f"{viz_type}: {x_col}")
            self.canvas.draw()
            
        except Exception as e:
            QMessageBox.critical(self, "可视化错误", f"生成图表时出错:\n{str(e)}")
            
    def show_prediction_dialog(self):
        if self.current_df is None or self.current_df.empty:
            QMessageBox.warning(self, "数据错误", "没有可用的数据用于预测分析")
            return
            
        dialog = PredictionDialog(self.current_df, self)
        if dialog.exec_() == QDialog.Accepted:
            params = dialog.get_params()
            self.perform_prediction(params)
            
    def perform_prediction(self, params):
        x_col = params['x_col']
        y_col = params['y_col']
        points = params['points']
        degree = params['degree']
        
        # 准备数据
        X = self.current_df[x_col].values.reshape(-1, 1)
        y = self.current_df[y_col].values
        
        # 多项式特征
        poly = PolynomialFeatures(degree=degree)
        X_poly = poly.fit_transform(X)
        
        # 训练模型
        model = LinearRegression()
        model.fit(X_poly, y)
        
        # 生成预测点
        x_min, x_max = X.min(), X.max()
        x_range = x_max - x_min
        x_pred = np.linspace(x_min - 0.1*x_range, x_max + 0.1*x_range, points).reshape(-1, 1)
        x_pred_poly = poly.transform(x_pred)
        y_pred = model.predict(x_pred_poly)
        
        # 绘制结果
        self.canvas.axes.clear()
        self.canvas.axes.scatter(X, y, color='blue', label='实际数据')
        self.canvas.axes.plot(x_pred, y_pred, color='red', label='预测趋势')
        self.canvas.axes.set_xlabel(x_col)
        self.canvas.axes.set_ylabel(y_col)
        self.canvas.axes.set_title(f"{y_col} 基于 {x_col} 的预测 (多项式次数: {degree})")
        self.canvas.axes.legend()
        self.canvas.draw()
        
    def export_data(self):
        if self.current_df is None:
            QMessageBox.warning(self, "导出错误", "没有数据可导出")
            return
            
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出数据", "", "CSV文件 (*.csv);;Excel文件 (*.xlsx);;所有文件 (*)"
        )
        
        if file_path:
            try:
                if file_path.endswith('.csv'):
                    self.current_df.to_csv(file_path, index=False)
                elif file_path.endswith('.xlsx'):
                    self.current_df.to_excel(file_path, index=False)
                else:
                    self.current_df.to_csv(file_path, index=False)
                    
                QMessageBox.information(self, "导出成功", f"数据已导出到: {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "导出错误", f"导出数据时出错:\n{str(e)}")
                
    def refresh_database(self):
        if self.db_path:
            self.load_database_structure()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 设置应用程序样式
    app.setStyle("Fusion")
    
    # 创建并显示主窗口
    window = DatabaseAnalyzer()
    window.show()
    
    sys.exit(app.exec_())