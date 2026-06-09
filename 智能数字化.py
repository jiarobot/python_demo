import sys
import os
import json
import csv
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QLineEdit, QTextEdit, QTableWidget, 
                             QTableWidgetItem, QTabWidget, QComboBox, QCheckBox, 
                             QSpinBox, QDoubleSpinBox, QDateEdit, QProgressBar, 
                             QMessageBox, QFileDialog, QSplitter, QTreeWidget, 
                             QTreeWidgetItem, QHeaderView, QToolBar, QStatusBar,
                             QDialog, QGroupBox, QFormLayout, QListWidget, QMenu, QAction)
from PyQt5.QtCore import Qt, QTimer, QDate, QThread, pyqtSignal, QSettings
from PyQt5.QtGui import QFont, QIcon, QPixmap, QColor, QPainter
import matplotlib
matplotlib.rc("font", family='Microsoft YaHei')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import seaborn as sns
import requests
from bs4 import BeautifulSoup
import threading
import queue
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('DigitalManagementSystem')

class DataProcessor(QThread):
    """数据处理器 - 后台线程处理数据"""
    progress_updated = pyqtSignal(int)
    processing_finished = pyqtSignal(object)
    
    def __init__(self, data, operation):
        super().__init__()
        self.data = data
        self.operation = operation
        
    def run(self):
        try:
            result = None
            if self.operation == "sort":
                result = self._sort_data()
            elif self.operation == "filter":
                result = self._filter_data()
            elif self.operation == "analyze":
                result = self._analyze_data()
                
            self.processing_finished.emit(result)
        except Exception as e:
            logger.error(f"数据处理错误: {e}")
            self.processing_finished.emit(None)
    
    def _sort_data(self):
        # 模拟排序操作
        if isinstance(self.data, list):
            for i in range(len(self.data)):
                # 模拟处理进度
                progress = int((i + 1) / len(self.data) * 100)
                self.progress_updated.emit(progress)
                self.msleep(50)  # 模拟处理时间
            return sorted(self.data)
        return self.data
    
    def _filter_data(self):
        # 模拟过滤操作
        if isinstance(self.data, list):
            result = []
            for i, item in enumerate(self.data):
                # 模拟处理进度
                progress = int((i + 1) / len(self.data) * 100)
                self.progress_updated.emit(progress)
                self.msleep(50)
                if i % 2 == 0:  # 简单过滤条件
                    result.append(item)
            return result
        return self.data
    
    def _analyze_data(self):
        # 模拟数据分析
        if isinstance(self.data, list) and len(self.data) > 0:
            for i in range(100):
                progress = i + 1
                self.progress_updated.emit(progress)
                self.msleep(30)
            
            analysis = {
                "count": len(self.data),
                "sum": sum(self.data) if all(isinstance(x, (int, float)) for x in self.data) else 0,
                "average": sum(self.data)/len(self.data) if all(isinstance(x, (int, float)) for x in self.data) else 0,
                "min": min(self.data) if all(isinstance(x, (int, float)) for x in self.data) else 0,
                "max": max(self.data) if all(isinstance(x, (int, float)) for x in self.data) else 0
            }
            return analysis
        return {}

class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self, db_path="management_system.db"):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """初始化数据库表结构"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建用户表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                role TEXT NOT NULL,
                created_date TEXT NOT NULL
            )
        ''')
        
        # 创建数据记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                value REAL,
                date TEXT NOT NULL,
                status TEXT NOT NULL,
                created_by INTEGER,
                FOREIGN KEY (created_by) REFERENCES users (id)
            )
        ''')
        
        # 创建系统日志表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                level TEXT NOT NULL,
                module TEXT NOT NULL,
                message TEXT NOT NULL
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def execute_query(self, query, params=None):
        """执行SQL查询"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            if query.strip().upper().startswith('SELECT'):
                result = cursor.fetchall()
            else:
                conn.commit()
                result = cursor.lastrowid
            
            conn.close()
            return result
        except Exception as e:
            conn.close()
            logger.error(f"数据库查询错误: {e}")
            return None
    
    def add_record(self, category, title, description, value, date, status, created_by):
        """添加新记录"""
        query = '''
            INSERT INTO records (category, title, description, value, date, status, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        '''
        return self.execute_query(query, (category, title, description, value, date, status, created_by))
    
    def get_records(self, category=None, date_range=None, status=None):
        """获取记录"""
        query = "SELECT * FROM records WHERE 1=1"
        params = []
        
        if category:
            query += " AND category = ?"
            params.append(category)
        
        if date_range:
            query += " AND date BETWEEN ? AND ?"
            params.extend(date_range)
        
        if status:
            query += " AND status = ?"
            params.append(status)
        
        query += " ORDER BY date DESC"
        return self.execute_query(query, params)
    
    def log_system_event(self, level, module, message):
        """记录系统事件"""
        query = '''
            INSERT INTO system_logs (timestamp, level, module, message)
            VALUES (?, ?, ?, ?)
        '''
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return self.execute_query(query, (timestamp, level, module, message))

class DataVisualizationWidget(QWidget):
    """数据可视化组件"""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 图表类型选择
        chart_type_layout = QHBoxLayout()
        chart_type_layout.addWidget(QLabel("图表类型:"))
        self.chart_type_combo = QComboBox()
        self.chart_type_combo.addItems(["折线图", "柱状图", "饼图", "散点图"])
        self.chart_type_combo.currentTextChanged.connect(self.update_chart)
        chart_type_layout.addWidget(self.chart_type_combo)
        chart_type_layout.addStretch()
        layout.addLayout(chart_type_layout)
        
        # 图表显示区域
        self.figure, self.ax = plt.subplots(figsize=(8, 6))
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)
        
        self.setLayout(layout)
    
    def update_chart(self, chart_type=None):
        """更新图表显示"""
        if not chart_type:
            chart_type = self.chart_type_combo.currentText()
        
        # 清除现有图表
        self.ax.clear()
        
        # 生成示例数据
        x = list(range(1, 11))
        y = [i * 2 + np.random.randint(-2, 3) for i in x]
        categories = [f'类别 {i}' for i in range(1, 6)]
        values = [np.random.randint(10, 100) for _ in range(5)]
        
        # 根据选择的图表类型绘制
        if chart_type == "折线图":
            self.ax.plot(x, y, marker='o')
            self.ax.set_title('折线图示例')
            self.ax.set_xlabel('X轴')
            self.ax.set_ylabel('Y轴')
            self.ax.grid(True, linestyle='--', alpha=0.7)
        elif chart_type == "柱状图":
            self.ax.bar(categories, values, color=plt.cm.Set3(np.linspace(0, 1, len(categories))))
            self.ax.set_title('柱状图示例')
            self.ax.set_xlabel('类别')
            self.ax.set_ylabel('数值')
        elif chart_type == "饼图":
            self.ax.pie(values, labels=categories, autopct='%1.1f%%', startangle=90)
            self.ax.set_title('饼图示例')
        elif chart_type == "散点图":
            self.ax.scatter(x, y, c=y, cmap='viridis', s=100, alpha=0.7)
            self.ax.set_title('散点图示例')
            self.ax.set_xlabel('X轴')
            self.ax.set_ylabel('Y轴')
        
        self.canvas.draw()
    
    def plot_data(self, data, chart_type="折线图", title="数据图表"):
        """绘制自定义数据"""
        self.ax.clear()
        
        if chart_type == "折线图" and isinstance(data, dict) and 'x' in data and 'y' in data:
            self.ax.plot(data['x'], data['y'], marker='o')
        elif chart_type == "柱状图" and isinstance(data, dict) and 'categories' in data and 'values' in data:
            self.ax.bar(data['categories'], data['values'])
        
        self.ax.set_title(title)
        self.canvas.draw()

class DataTableWidget(QWidget):
    """数据表格组件"""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.data = []
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 工具栏
        toolbar = QHBoxLayout()
        
        self.import_btn = QPushButton("导入数据")
        self.import_btn.clicked.connect(self.import_data)
        toolbar.addWidget(self.import_btn)
        
        self.export_btn = QPushButton("导出数据")
        self.export_btn.clicked.connect(self.export_data)
        toolbar.addWidget(self.export_btn)
        
        self.filter_btn = QPushButton("过滤数据")
        self.filter_btn.clicked.connect(self.filter_data)
        toolbar.addWidget(self.filter_btn)
        
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["默认排序", "升序", "降序"])
        self.sort_combo.currentTextChanged.connect(self.sort_data)
        toolbar.addWidget(QLabel("排序:"))
        toolbar.addWidget(self.sort_combo)
        
        toolbar.addStretch()
        layout.addLayout(toolbar)
        
        # 数据表格
        self.table = QTableWidget()
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table)
        
        # 状态栏
        self.status_label = QLabel("就绪")
        layout.addWidget(self.status_label)
        
        self.setLayout(layout)
    
    def import_data(self):
        """导入数据"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择数据文件", "", "CSV文件 (*.csv);;Excel文件 (*.xlsx);;所有文件 (*)"
        )
        
        if file_path:
            try:
                if file_path.endswith('.csv'):
                    self.data = pd.read_csv(file_path)
                elif file_path.endswith('.xlsx'):
                    self.data = pd.read_excel(file_path)
                
                self.populate_table()
                self.status_label.setText(f"已导入数据: {len(self.data)} 行")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导入数据失败: {e}")
    
    def export_data(self):
        """导出数据"""
        if len(self.data) == 0:
            QMessageBox.warning(self, "警告", "没有数据可导出")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存数据文件", "", "CSV文件 (*.csv);;Excel文件 (*.xlsx)"
        )
        
        if file_path:
            try:
                if file_path.endswith('.csv'):
                    self.data.to_csv(file_path, index=False)
                elif file_path.endswith('.xlsx'):
                    self.data.to_excel(file_path, index=False)
                
                QMessageBox.information(self, "成功", "数据导出成功")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导出数据失败: {e}")
    
    def populate_table(self):
        """填充表格数据"""
        if len(self.data) == 0:
            return
        
        self.table.setRowCount(len(self.data))
        self.table.setColumnCount(len(self.data.columns))
        self.table.setHorizontalHeaderLabels(self.data.columns.tolist())
        
        for row in range(len(self.data)):
            for col in range(len(self.data.columns)):
                value = self.data.iloc[row, col]
                item = QTableWidgetItem(str(value))
                self.table.setItem(row, col, item)
    
    def filter_data(self):
        """过滤数据"""
        if len(self.data) == 0:
            return
        
        # 简单过滤对话框
        dialog = QDialog(self)
        dialog.setWindowTitle("数据过滤")
        layout = QVBoxLayout()
        
        form_layout = QFormLayout()
        column_combo = QComboBox()
        column_combo.addItems(self.data.columns.tolist())
        form_layout.addRow("列名:", column_combo)
        
        operator_combo = QComboBox()
        operator_combo.addItems([">", ">=", "=", "<=", "<", "包含"])
        form_layout.addRow("操作符:", operator_combo)
        
        value_edit = QLineEdit()
        form_layout.addRow("值:", value_edit)
        
        layout.addLayout(form_layout)
        
        button_layout = QHBoxLayout()
        apply_btn = QPushButton("应用")
        cancel_btn = QPushButton("取消")
        
        def apply_filter():
            column = column_combo.currentText()
            operator = operator_combo.currentText()
            value = value_edit.text()
            
            try:
                if operator == ">":
                    filtered_data = self.data[self.data[column] > float(value)]
                elif operator == ">=":
                    filtered_data = self.data[self.data[column] >= float(value)]
                elif operator == "=":
                    filtered_data = self.data[self.data[column] == value]
                elif operator == "<=":
                    filtered_data = self.data[self.data[column] <= float(value)]
                elif operator == "<":
                    filtered_data = self.data[self.data[column] < float(value)]
                elif operator == "包含":
                    filtered_data = self.data[self.data[column].astype(str).str.contains(value)]
                
                self.data = filtered_data
                self.populate_table()
                self.status_label.setText(f"过滤后数据: {len(self.data)} 行")
                dialog.close()
            except Exception as e:
                QMessageBox.critical(dialog, "错误", f"过滤失败: {e}")
        
        apply_btn.clicked.connect(apply_filter)
        cancel_btn.clicked.connect(dialog.close)
        
        button_layout.addWidget(apply_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)
        
        dialog.setLayout(layout)
        dialog.exec_()
    
    def sort_data(self, sort_type):
        """排序数据"""
        if len(self.data) == 0 or sort_type == "默认排序":
            return
        
        # 简单实现：按第一列排序
        column = self.data.columns[0]
        ascending = (sort_type == "升序")
        self.data = self.data.sort_values(by=column, ascending=ascending)
        self.populate_table()

class AdvancedToolsWidget(QWidget):
    """高级工具组件"""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 工具按钮组
        tools_group = QGroupBox("高级工具")
        tools_layout = QVBoxLayout()
        
        # 数据清洗工具
        self.data_cleaning_btn = QPushButton("数据清洗工具")
        self.data_cleaning_btn.clicked.connect(self.open_data_cleaning_tool)
        tools_layout.addWidget(self.data_cleaning_btn)
        
        # 数据分析工具
        self.data_analysis_btn = QPushButton("数据分析工具")
        self.data_analysis_btn.clicked.connect(self.open_data_analysis_tool)
        tools_layout.addWidget(self.data_analysis_btn)
        
        # 报告生成工具
        self.report_generator_btn = QPushButton("报告生成工具")
        self.report_generator_btn.clicked.connect(self.open_report_generator)
        tools_layout.addWidget(self.report_generator_btn)
        
        # 批量处理工具
        self.batch_processor_btn = QPushButton("批量处理工具")
        self.batch_processor_btn.clicked.connect(self.open_batch_processor)
        tools_layout.addWidget(self.batch_processor_btn)
        
        tools_group.setLayout(tools_layout)
        layout.addWidget(tools_group)
        
        # 工具输出区域
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        layout.addWidget(self.output_text)
        
        self.setLayout(layout)
    
    def open_data_cleaning_tool(self):
        """打开数据清洗工具"""
        dialog = QDialog(self)
        dialog.setWindowTitle("数据清洗工具")
        dialog.setMinimumSize(500, 400)
        
        layout = QVBoxLayout()
        
        # 数据输入区域
        input_group = QGroupBox("数据输入")
        input_layout = QVBoxLayout()
        
        self.data_input = QTextEdit()
        self.data_input.setPlaceholderText("请输入数据，每行一个值")
        input_layout.addWidget(self.data_input)
        
        input_group.setLayout(input_layout)
        layout.addWidget(input_group)
        
        # 清洗选项
        options_group = QGroupBox("清洗选项")
        options_layout = QHBoxLayout()
        
        self.remove_duplicates = QCheckBox("去除重复值")
        self.remove_duplicates.setChecked(True)
        options_layout.addWidget(self.remove_duplicates)
        
        self.fill_missing = QCheckBox("填充缺失值")
        options_layout.addWidget(self.fill_missing)
        
        self.normalize_data = QCheckBox("数据标准化")
        options_layout.addWidget(self.normalize_data)
        
        options_group.setLayout(options_layout)
        layout.addWidget(options_group)
        
        # 操作按钮
        button_layout = QHBoxLayout()
        
        process_btn = QPushButton("执行清洗")
        process_btn.clicked.connect(self.execute_data_cleaning)
        button_layout.addWidget(process_btn)
        
        clear_btn = QPushButton("清空")
        clear_btn.clicked.connect(self.data_input.clear)
        button_layout.addWidget(clear_btn)
        
        layout.addLayout(button_layout)
        
        # 结果展示
        result_group = QGroupBox("清洗结果")
        result_layout = QVBoxLayout()
        
        self.cleaning_result = QTextEdit()
        self.cleaning_result.setReadOnly(True)
        result_layout.addWidget(self.cleaning_result)
        
        result_group.setLayout(result_layout)
        layout.addWidget(result_group)
        
        dialog.setLayout(layout)
        dialog.exec_()
    
    def execute_data_cleaning(self):
        """执行数据清洗"""
        try:
            # 获取输入数据
            input_text = self.data_input.toPlainText()
            if not input_text.strip():
                QMessageBox.warning(self, "警告", "请输入数据")
                return
            
            # 解析数据
            data_lines = input_text.strip().split('\n')
            data = []
            for line in data_lines:
                try:
                    value = float(line.strip())
                    data.append(value)
                except ValueError:
                    # 如果不是数字，保留原始值
                    data.append(line.strip())
            
            original_count = len(data)
            
            # 执行清洗操作
            if self.remove_duplicates.isChecked():
                data = list(dict.fromkeys(data))  # 保持顺序的去重
            
            # 简单的缺失值处理（这里只是示例）
            if self.fill_missing.isChecked():
                numeric_data = [x for x in data if isinstance(x, (int, float))]
                if numeric_data:
                    avg = sum(numeric_data) / len(numeric_data)
                    data = [avg if x == '' or x is None else x for x in data]
            
            # 简单的标准化（这里只是示例）
            if self.normalize_data.isChecked():
                numeric_data = [x for x in data if isinstance(x, (int, float))]
                if numeric_data and max(numeric_data) != min(numeric_data):
                    normalized = [(x - min(numeric_data)) / (max(numeric_data) - min(numeric_data)) 
                                 for x in numeric_data]
                    # 替换原数据中的数值
                    num_idx = 0
                    for i in range(len(data)):
                        if isinstance(data[i], (int, float)):
                            data[i] = normalized[num_idx]
                            num_idx += 1
            
            # 显示结果
            result_text = f"原始数据量: {original_count}\n"
            result_text += f"清洗后数据量: {len(data)}\n"
            result_text += f"去除重复值: {self.remove_duplicates.isChecked()}\n"
            result_text += f"填充缺失值: {self.fill_missing.isChecked()}\n"
            result_text += f"数据标准化: {self.normalize_data.isChecked()}\n\n"
            result_text += "清洗后数据:\n" + "\n".join(str(x) for x in data)
            
            self.cleaning_result.setText(result_text)
            self.output_text.append(f"[{datetime.now().strftime('%H:%M:%S')}] 数据清洗完成")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"数据清洗失败: {e}")
    
    def open_data_analysis_tool(self):
        """打开数据分析工具"""
        self.output_text.append(f"[{datetime.now().strftime('%H:%M:%S')}] 数据分析工具已打开")
        QMessageBox.information(self, "信息", "数据分析工具功能开发中...")
    
    def open_report_generator(self):
        """打开报告生成工具"""
        self.output_text.append(f"[{datetime.now().strftime('%H:%M:%S')}] 报告生成工具已打开")
        QMessageBox.information(self, "信息", "报告生成工具功能开发中...")
    
    def open_batch_processor(self):
        """打开批量处理工具"""
        self.output_text.append(f"[{datetime.now().strftime('%H:%M:%S')}] 批量处理工具已打开")
        QMessageBox.information(self, "信息", "批量处理工具功能开发中...")

class DigitalManagementSystem(QMainWindow):
    """智能数字化管理系统主窗口"""
    
    def __init__(self):
        super().__init__()
        self.db_manager = DatabaseManager()
        self.init_ui()
        self.load_settings()
        
        # 记录系统启动
        self.db_manager.log_system_event("INFO", "System", "应用程序启动")
    
    def init_ui(self):
        self.setWindowTitle("智能数字化管理系统 - 高级工具库")
        self.setGeometry(100, 100, 1200, 800)
        
        # 创建中央部件和主布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # 创建左侧导航栏
        self.create_navigation_panel(main_layout)
        
        # 创建右侧内容区域
        self.create_content_area(main_layout)
        
        # 创建状态栏
        self.statusBar().showMessage("就绪")
        
        # 创建菜单栏
        self.create_menubar()
        
        # 创建工具栏
        self.create_toolbar()
    
    def create_navigation_panel(self, main_layout):
        """创建左侧导航面板"""
        nav_widget = QWidget()
        nav_widget.setMaximumWidth(200)
        nav_layout = QVBoxLayout(nav_widget)
        
        # 系统标题
        title_label = QLabel("智能管理系统")
        title_label.setFont(QFont("Arial", 14, QFont.Bold))
        nav_layout.addWidget(title_label)
        
        # 导航按钮
        self.nav_buttons = {}
        
        nav_items = [
            ("数据可视化", "chart-icon"),
            ("数据表格", "table-icon"),
            ("高级工具", "tools-icon"),
            ("系统设置", "settings-icon")
        ]
        
        for text, icon_name in nav_items:
            btn = QPushButton(text)
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, t=text: self.show_content(t))
            self.nav_buttons[text] = btn
            nav_layout.addWidget(btn)
        
        nav_layout.addStretch()
        main_layout.addWidget(nav_widget)
    
    def create_content_area(self, main_layout):
        """创建右侧内容区域"""
        self.content_stack = QTabWidget()
        
        # 数据可视化标签页
        self.viz_widget = DataVisualizationWidget()
        self.content_stack.addTab(self.viz_widget, "数据可视化")
        
        # 数据表格标签页
        self.table_widget = DataTableWidget()
        self.content_stack.addTab(self.table_widget, "数据表格")
        
        # 高级工具标签页
        self.tools_widget = AdvancedToolsWidget()
        self.content_stack.addTab(self.tools_widget, "高级工具")
        
        # 系统设置标签页
        self.settings_widget = self.create_settings_widget()
        self.content_stack.addTab(self.settings_widget, "系统设置")
        
        main_layout.addWidget(self.content_stack)
    
    def create_settings_widget(self):
        """创建系统设置组件"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # 数据库设置
        db_group = QGroupBox("数据库设置")
        db_layout = QFormLayout()
        
        self.db_host = QLineEdit("localhost")
        db_layout.addRow("主机:", self.db_host)
        
        self.db_name = QLineEdit("management_system.db")
        db_layout.addRow("数据库名:", self.db_name)
        
        db_group.setLayout(db_layout)
        layout.addWidget(db_group)
        
        # 界面设置
        ui_group = QGroupBox("界面设置")
        ui_layout = QVBoxLayout()
        
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["浅色主题", "深色主题", "自动"])
        ui_layout.addWidget(QLabel("主题:"))
        ui_layout.addWidget(self.theme_combo)
        
        self.font_size = QSpinBox()
        self.font_size.setRange(8, 20)
        self.font_size.setValue(10)
        ui_layout.addWidget(QLabel("字体大小:"))
        ui_layout.addWidget(self.font_size)
        
        ui_group.setLayout(ui_layout)
        layout.addWidget(ui_group)
        
        # 保存设置按钮
        save_btn = QPushButton("保存设置")
        save_btn.clicked.connect(self.save_settings)
        layout.addWidget(save_btn)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def create_menubar(self):
        """创建菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu('文件')
        
        new_action = QAction('新建', self)
        new_action.setShortcut('Ctrl+N')
        file_menu.addAction(new_action)
        
        open_action = QAction('打开', self)
        open_action.setShortcut('Ctrl+O')
        file_menu.addAction(open_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction('退出', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 工具菜单
        tools_menu = menubar.addMenu('工具')
        
        data_import_action = QAction('数据导入', self)
        tools_menu.addAction(data_import_action)
        
        data_export_action = QAction('数据导出', self)
        tools_menu.addAction(data_export_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu('帮助')
        
        about_action = QAction('关于', self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def create_toolbar(self):
        """创建工具栏"""
        toolbar = QToolBar("主工具栏")
        self.addToolBar(toolbar)
        
        # 添加工具栏按钮
        import_btn = QAction("导入", self)
        toolbar.addAction(import_btn)
        
        export_btn = QAction("导出", self)
        toolbar.addAction(export_btn)
        
        toolbar.addSeparator()
        
        refresh_btn = QAction("刷新", self)
        toolbar.addAction(refresh_btn)
    
    def show_content(self, content_name):
        """显示指定内容"""
        # 更新按钮状态
        for name, btn in self.nav_buttons.items():
            btn.setChecked(name == content_name)
        
        # 切换到对应标签页
        if content_name == "数据可视化":
            self.content_stack.setCurrentIndex(0)
            self.viz_widget.update_chart()
        elif content_name == "数据表格":
            self.content_stack.setCurrentIndex(1)
        elif content_name == "高级工具":
            self.content_stack.setCurrentIndex(2)
        elif content_name == "系统设置":
            self.content_stack.setCurrentIndex(3)
    
    def load_settings(self):
        """加载系统设置"""
        settings = QSettings("MyCompany", "DigitalManagementSystem")
        
        # 加载窗口尺寸和位置
        self.resize(settings.value("window/size", self.size()))
        self.move(settings.value("window/position", self.pos()))
    
    def save_settings(self):
        """保存系统设置"""
        settings = QSettings("MyCompany", "DigitalManagementSystem")
        
        # 保存窗口尺寸和位置
        settings.setValue("window/size", self.size())
        settings.setValue("window/position", self.pos())
        
        # 保存数据库设置
        settings.setValue("database/host", self.db_host.text())
        settings.setValue("database/name", self.db_name.text())
        
        # 保存界面设置
        settings.setValue("ui/theme", self.theme_combo.currentText())
        settings.setValue("ui/font_size", self.font_size.value())
        
        QMessageBox.information(self, "成功", "设置已保存")
        self.db_manager.log_system_event("INFO", "Settings", "系统设置已更新")
    
    def show_about(self):
        """显示关于对话框"""
        about_text = """
        <h2>智能数字化管理系统</h2>
        <p>版本: 1.0.0</p>
        <p>这是一个基于PyQt的智能数字化管理系统，提供数据可视化、数据管理和高级分析工具。</p>
        <p>开发团队: 智能系统开发组</p>
        <p>版权所有 © 2023</p>
        """
        QMessageBox.about(self, "关于", about_text)
    
    def closeEvent(self, event):
        """应用程序关闭事件"""
        # 记录系统关闭
        self.db_manager.log_system_event("INFO", "System", "应用程序关闭")
        
        # 保存设置
        self.save_settings()
        
        # 确认退出
        reply = QMessageBox.question(
            self, '确认退出', 
            '确定要退出系统吗？',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()

def main():
    app = QApplication(sys.argv)
    
    # 设置应用程序样式
    app.setStyle('Fusion')
    
    # 创建并显示主窗口
    window = DigitalManagementSystem()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()