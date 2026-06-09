import sys
import json
import time
import requests
import threading
import inspect
import csv
import sqlite3
import matplotlib.pyplot as plt
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QTextEdit, QTreeWidget, QTreeWidgetItem,
                             QLabel, QLineEdit, QSplitter, QFileDialog, QMessageBox, QProgressBar,
                             QGroupBox, QFormLayout, QComboBox, QTableWidget, QTableWidgetItem,
                             QHeaderView, QSpinBox, QDoubleSpinBox, QCheckBox, QListWidget,
                             QListWidgetItem, QToolBar, QAction, QStatusBar, QToolButton, QMenu,
                             QDialog, QDialogButtonBox, QInputDialog, QSystemTrayIcon, QStyle)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread, QSize, QSettings
from PyQt5.QtGui import QFont, QColor, QIcon, QPixmap, QTextCursor
import matplotlib
matplotlib.rc("font", family='Microsoft YaHei')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from faker import Faker

# 数据库管理类
class TestDatabase:
    def __init__(self):
        self.conn = sqlite3.connect('test_engineer_toolkit.db')
        self.create_tables()
        
    def create_tables(self):
        cursor = self.conn.cursor()
        
        # 测试用例表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS test_cases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                priority TEXT,
                type TEXT,
                created_date TEXT,
                modified_date TEXT,
                status TEXT DEFAULT '未执行'
            )
        ''')
        
        # 测试步骤表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS test_steps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id INTEGER,
                step_number INTEGER,
                action TEXT,
                expected_result TEXT,
                FOREIGN KEY (case_id) REFERENCES test_cases (id)
            )
        ''')
        
        # API测试历史表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS api_test_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT,
                method TEXT,
                status_code INTEGER,
                response_time REAL,
                timestamp TEXT,
                success INTEGER
            )
        ''')
        
        # 性能监控数据表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS performance_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                target_url TEXT,
                cpu_usage REAL,
                memory_usage REAL,
                response_time REAL,
                throughput REAL,
                timestamp TEXT
            )
        ''')
        
        self.conn.commit()
        
    def add_test_case(self, name, description, priority, type):
        cursor = self.conn.cursor()
        current_time = datetime.now().isoformat()
        cursor.execute(
            'INSERT INTO test_cases (name, description, priority, type, created_date, modified_date) VALUES (?, ?, ?, ?, ?, ?)',
            (name, description, priority, type, current_time, current_time)
        )
        self.conn.commit()
        return cursor.lastrowid
        
    def update_test_case(self, case_id, name, description, priority, type):
        cursor = self.conn.cursor()
        current_time = datetime.now().isoformat()
        cursor.execute(
            'UPDATE test_cases SET name=?, description=?, priority=?, type=?, modified_date=? WHERE id=?',
            (name, description, priority, type, current_time, case_id)
        )
        self.conn.commit()
        
    def add_test_step(self, case_id, step_number, action, expected_result):
        cursor = self.conn.cursor()
        cursor.execute(
            'INSERT INTO test_steps (case_id, step_number, action, expected_result) VALUES (?, ?, ?, ?)',
            (case_id, step_number, action, expected_result)
        )
        self.conn.commit()
        
    def get_test_cases(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM test_cases ORDER BY created_date DESC')
        return cursor.fetchall()
        
    def get_test_steps(self, case_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM test_steps WHERE case_id=? ORDER BY step_number', (case_id,))
        return cursor.fetchall()
        
    def save_api_test_result(self, url, method, status_code, response_time, success):
        cursor = self.conn.cursor()
        timestamp = datetime.now().isoformat()
        cursor.execute(
            'INSERT INTO api_test_history (url, method, status_code, response_time, timestamp, success) VALUES (?, ?, ?, ?, ?, ?)',
            (url, method, status_code, response_time, timestamp, success)
        )
        self.conn.commit()
        
    def get_api_test_history(self, limit=50):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM api_test_history ORDER BY timestamp DESC LIMIT ?', (limit,))
        return cursor.fetchall()
        
    def save_performance_data(self, target_url, cpu_usage, memory_usage, response_time, throughput):
        cursor = self.conn.cursor()
        timestamp = datetime.now().isoformat()
        cursor.execute(
            'INSERT INTO performance_data (target_url, cpu_usage, memory_usage, response_time, throughput, timestamp) VALUES (?, ?, ?, ?, ?, ?)',
            (target_url, cpu_usage, memory_usage, response_time, throughput, timestamp)
        )
        self.conn.commit()
        
    def get_performance_data(self, target_url, limit=100):
        cursor = self.conn.cursor()
        cursor.execute(
            'SELECT * FROM performance_data WHERE target_url=? ORDER BY timestamp DESC LIMIT ?',
            (target_url, limit)
        )
        return cursor.fetchall()

# 性能监控线程
class PerformanceMonitorThread(QThread):
    update_signal = pyqtSignal(dict)
    
    def __init__(self, target_url, interval, duration=None):
        super().__init__()
        self.target_url = target_url
        self.interval = interval
        self.duration = duration
        self.is_running = False
        
    def run(self):
        self.is_running = True
        start_time = time.time()
        
        while self.is_running:
            if self.duration and (time.time() - start_time) > self.duration:
                break
                
            try:
                # 模拟获取性能数据
                metrics = self.get_performance_metrics()
                self.update_signal.emit(metrics)
                
                # 保存到数据库
                db = TestDatabase()
                db.save_performance_data(
                    self.target_url,
                    metrics['cpu_usage'],
                    metrics['memory_usage'],
                    metrics['response_time'],
                    metrics['throughput']
                )
                
                time.sleep(self.interval)
            except Exception as e:
                print(f"性能监控错误: {e}")
                break
                
    def stop(self):
        self.is_running = False
        
    def get_performance_metrics(self):
        # 这里应该是实际的性能监控代码
        # 为了演示，我们使用随机数据
        import random
        return {
            'cpu_usage': random.uniform(1.0, 100.0),
            'memory_usage': random.uniform(100, 2000),
            'response_time': random.uniform(10, 500),
            'throughput': random.uniform(10, 1000)
        }

# 测试用例执行线程
class TestCaseRunnerThread(QThread):
    update_signal = pyqtSignal(str, str)  # 测试用例ID, 状态
    log_signal = pyqtSignal(str, str)  # 测试用例ID, 日志消息
    
    def __init__(self, case_id, steps):
        super().__init__()
        self.case_id = case_id
        self.steps = steps
        self.is_running = False
        
    def run(self):
        self.is_running = True
        self.update_signal.emit(self.case_id, "执行中")
        
        for step in self.steps:
            if not self.is_running:
                break
                
            step_num, action, expected = step
            self.log_signal.emit(self.case_id, f"执行步骤 {step_num}: {action}")
            
            # 模拟执行测试步骤
            time.sleep(1)  # 模拟执行时间
            
            # 模拟随机成功或失败
            import random
            success = random.choice([True, False, True])  # 2/3的成功率
            
            if success:
                self.log_signal.emit(self.case_id, f"步骤 {step_num} 成功: 结果符合预期")
            else:
                self.log_signal.emit(self.case_id, f"步骤 {step_num} 失败: 结果不符合预期")
                self.update_signal.emit(self.case_id, "失败")
                return
                
        self.update_signal.emit(self.case_id, "成功")
        
    def stop(self):
        self.is_running = False

# 实时图表组件
class RealTimeChart(FigureCanvas):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        super().__init__(self.fig)
        self.setParent(parent)
        
        self.axes = self.fig.add_subplot(111)
        self.axes.set_ylabel('数值')
        self.axes.set_xlabel('时间')
        self.axes.grid(True)
        
        self.data = {'x': [], 'y': []}
        self.line, = self.axes.plot([], [], 'r-')
        
    def update_chart(self, x, y, title="实时数据", ylabel="数值"):
        self.data['x'] = x
        self.data['y'] = y
        
        self.axes.clear()
        self.axes.plot(x, y, 'r-')
        self.axes.set_title(title)
        self.axes.set_ylabel(ylabel)
        self.axes.set_xlabel('时间')
        self.axes.grid(True)
        
        # 自动调整坐标轴
        if x and y:
            self.axes.set_xlim(min(x), max(x))
            self.axes.set_ylim(min(y) * 0.9, max(y) * 1.1)
            
        self.draw()

# 增强的测试用例管理器
class EnhancedTestCaseManager(QWidget):
    def __init__(self):
        super().__init__()
        self.db = TestDatabase()
        self.test_case_runners = {}  # 存储正在运行的测试用例线程
        self.init_ui()
        self.load_test_cases()
        
    def init_ui(self):
        layout = QHBoxLayout()
        
        # 左侧测试用例树
        left_panel = QWidget()
        left_layout = QVBoxLayout()
        
        # 搜索和过滤
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索测试用例...")
        self.search_input.textChanged.connect(self.filter_test_cases)
        
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["全部", "未执行", "执行中", "成功", "失败"])
        self.filter_combo.currentTextChanged.connect(self.filter_test_cases)
        
        search_layout.addWidget(QLabel("搜索:"))
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(QLabel("过滤:"))
        search_layout.addWidget(self.filter_combo)
        
        # 测试用例树
        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderLabels(["测试用例", "状态", "优先级", "类型"])
        self.tree_widget.setColumnWidth(0, 200)
        self.tree_widget.itemClicked.connect(self.on_test_case_selected)
        
        # 操作按钮
        button_layout = QHBoxLayout()
        self.new_btn = QPushButton("新建用例")
        self.import_btn = QPushButton("导入")
        self.export_btn = QPushButton("导出")
        self.run_btn = QPushButton("运行选中")
        self.run_all_btn = QPushButton("运行全部")
        self.stop_btn = QPushButton("停止运行")
        
        self.new_btn.clicked.connect(self.new_test_case)
        self.import_btn.clicked.connect(self.import_test_cases)
        self.export_btn.clicked.connect(self.export_test_cases)
        self.run_btn.clicked.connect(self.run_selected_test_cases)
        self.run_all_btn.clicked.connect(self.run_all_test_cases)
        self.stop_btn.clicked.connect(self.stop_test_cases)
        
        button_layout.addWidget(self.new_btn)
        button_layout.addWidget(self.import_btn)
        button_layout.addWidget(self.export_btn)
        button_layout.addWidget(self.run_btn)
        button_layout.addWidget(self.run_all_btn)
        button_layout.addWidget(self.stop_btn)
        
        # 组装左侧面板
        left_layout.addLayout(search_layout)
        left_layout.addWidget(self.tree_widget)
        left_layout.addLayout(button_layout)
        left_panel.setLayout(left_layout)
        
        # 右侧详情面板
        self.detail_widget = QWidget()
        self.detail_layout = QVBoxLayout()
        
        # 基本信息
        info_group = QGroupBox("测试用例信息")
        info_form = QFormLayout()
        
        self.case_id = None
        self.case_name = QLineEdit()
        self.case_description = QTextEdit()
        self.case_priority = QComboBox()
        self.case_priority.addItems(["低", "中", "高"])
        self.case_type = QComboBox()
        self.case_type.addItems(["功能测试", "性能测试", "安全测试", "兼容性测试", "API测试", "UI测试"])
        self.case_status = QLabel("未执行")
        
        info_form.addRow("ID:", QLabel("自动生成"))
        info_form.addRow("名称:", self.case_name)
        info_form.addRow("描述:", self.case_description)
        info_form.addRow("优先级:", self.case_priority)
        info_form.addRow("类型:", self.case_type)
        info_form.addRow("状态:", self.case_status)
        info_group.setLayout(info_form)
        
        # 步骤管理
        steps_group = QGroupBox("测试步骤")
        steps_layout = QVBoxLayout()
        
        self.steps_table = QTableWidget()
        self.steps_table.setColumnCount(3)
        self.steps_table.setHorizontalHeaderLabels(["步骤", "操作", "预期结果"])
        self.steps_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        steps_buttons = QHBoxLayout()
        add_step_btn = QPushButton("添加步骤")
        remove_step_btn = QPushButton("删除步骤")
        move_up_btn = QPushButton("上移")
        move_down_btn = QPushButton("下移")
        
        add_step_btn.clicked.connect(self.add_test_step)
        remove_step_btn.clicked.connect(self.remove_test_step)
        move_up_btn.clicked.connect(self.move_step_up)
        move_down_btn.clicked.connect(self.move_step_down)
        
        steps_buttons.addWidget(add_step_btn)
        steps_buttons.addWidget(remove_step_btn)
        steps_buttons.addWidget(move_up_btn)
        steps_buttons.addWidget(move_down_btn)
        
        steps_layout.addWidget(self.steps_table)
        steps_layout.addLayout(steps_buttons)
        steps_group.setLayout(steps_layout)
        
        # 执行日志
        log_group = QGroupBox("执行日志")
        log_layout = QVBoxLayout()
        self.execution_log = QTextEdit()
        self.execution_log.setReadOnly(True)
        log_layout.addWidget(self.execution_log)
        log_group.setLayout(log_layout)
        
        # 操作按钮
        save_btn = QPushButton("保存")
        delete_btn = QPushButton("删除")
        duplicate_btn = QPushButton("复制")
        
        save_btn.clicked.connect(self.save_test_case)
        delete_btn.clicked.connect(self.delete_test_case)
        duplicate_btn.clicked.connect(self.duplicate_test_case)
        
        button_layout2 = QHBoxLayout()
        button_layout2.addWidget(save_btn)
        button_layout2.addWidget(delete_btn)
        button_layout2.addWidget(duplicate_btn)
        
        # 组装右侧面板
        self.detail_layout.addWidget(info_group)
        self.detail_layout.addWidget(steps_group)
        self.detail_layout.addWidget(log_group)
        self.detail_layout.addLayout(button_layout2)
        self.detail_widget.setLayout(self.detail_layout)
        
        # 初始隐藏详情面板
        self.detail_widget.setVisible(False)
        
        # 整体布局
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(self.detail_widget)
        splitter.setSizes([300, 500])
        layout.addWidget(splitter)
        
        self.setLayout(layout)
        
    def load_test_cases(self):
        self.tree_widget.clear()
        test_cases = self.db.get_test_cases()
        
        for case in test_cases:
            case_id, name, description, priority, type, created_date, modified_date, status = case
            item = QTreeWidgetItem(self.tree_widget)
            item.setText(0, name)
            item.setText(1, status)
            item.setText(2, priority)
            item.setText(3, type)
            item.setData(0, Qt.UserRole, case_id)
            
            # 根据状态设置颜色
            if status == "成功":
                item.setForeground(1, QColor(0, 128, 0))  # 绿色
            elif status == "失败":
                item.setForeground(1, QColor(255, 0, 0))  # 红色
            elif status == "执行中":
                item.setForeground(1, QColor(0, 0, 255))  # 蓝色
        
    def filter_test_cases(self):
        search_text = self.search_input.text().lower()
        filter_text = self.filter_combo.currentText()
        
        for i in range(self.tree_widget.topLevelItemCount()):
            item = self.tree_widget.topLevelItem(i)
            name = item.text(0).lower()
            status = item.text(1)
            
            # 应用搜索和过滤
            match_search = search_text in name
            match_filter = (filter_text == "全部") or (filter_text == status)
            
            item.setHidden(not (match_search and match_filter))
            
    def on_test_case_selected(self, item, column):
        case_id = item.data(0, Qt.UserRole)
        self.load_test_case_details(case_id)
        self.detail_widget.setVisible(True)
        
    def load_test_case_details(self, case_id):
        self.case_id = case_id
        test_cases = self.db.get_test_cases()
        
        for case in test_cases:
            if case[0] == case_id:
                _, name, description, priority, type, _, _, status = case
                self.case_name.setText(name)
                self.case_description.setPlainText(description)
                self.case_priority.setCurrentText(priority)
                self.case_type.setCurrentText(type)
                self.case_status.setText(status)
                break
                
        # 加载测试步骤
        self.steps_table.setRowCount(0)
        steps = self.db.get_test_steps(case_id)
        
        for step in steps:
            _, _, step_number, action, expected_result = step
            row = self.steps_table.rowCount()
            self.steps_table.insertRow(row)
            self.steps_table.setItem(row, 0, QTableWidgetItem(str(step_number)))
            self.steps_table.setItem(row, 1, QTableWidgetItem(action))
            self.steps_table.setItem(row, 2, QTableWidgetItem(expected_result))
            
        # 清空日志
        self.execution_log.clear()
        
    def add_test_step(self):
        row_count = self.steps_table.rowCount()
        self.steps_table.insertRow(row_count)
        self.steps_table.setItem(row_count, 0, QTableWidgetItem(str(row_count + 1)))
        self.steps_table.setItem(row_count, 1, QTableWidgetItem(""))
        self.steps_table.setItem(row_count, 2, QTableWidgetItem(""))
        
    def remove_test_step(self):
        current_row = self.steps_table.currentRow()
        if current_row >= 0:
            self.steps_table.removeRow(current_row)
            # 重新编号步骤
            for row in range(self.steps_table.rowCount()):
                self.steps_table.setItem(row, 0, QTableWidgetItem(str(row + 1)))
                
    def move_step_up(self):
        current_row = self.steps_table.currentRow()
        if current_row > 0:
            # 交换行
            self.swap_table_rows(current_row, current_row - 1)
            self.steps_table.setCurrentCell(current_row - 1, 0)
            
    def move_step_down(self):
        current_row = self.steps_table.currentRow()
        if current_row < self.steps_table.rowCount() - 1:
            # 交换行
            self.swap_table_rows(current_row, current_row + 1)
            self.steps_table.setCurrentCell(current_row + 1, 0)
            
    def swap_table_rows(self, row1, row2):
        for col in range(self.steps_table.columnCount()):
            item1 = self.steps_table.takeItem(row1, col)
            item2 = self.steps_table.takeItem(row2, col)
            self.steps_table.setItem(row1, col, item2)
            self.steps_table.setItem(row2, col, item1)
            
    def save_test_case(self):
        if not self.case_id:
            # 新建测试用例
            case_id = self.db.add_test_case(
                self.case_name.text(),
                self.case_description.toPlainText(),
                self.case_priority.currentText(),
                self.case_type.currentText()
            )
            self.case_id = case_id
        else:
            # 更新测试用例
            self.db.update_test_case(
                self.case_id,
                self.case_name.text(),
                self.case_description.toPlainText(),
                self.case_priority.currentText(),
                self.case_type.currentText()
            )
            
        # 保存测试步骤
        # 先删除所有现有步骤
        cursor = self.db.conn.cursor()
        cursor.execute('DELETE FROM test_steps WHERE case_id=?', (self.case_id,))
        self.db.conn.commit()
        
        # 添加新步骤
        for row in range(self.steps_table.rowCount()):
            step_number = int(self.steps_table.item(row, 0).text())
            action = self.steps_table.item(row, 1).text()
            expected_result = self.steps_table.item(row, 2).text()
            self.db.add_test_step(self.case_id, step_number, action, expected_result)
            
        QMessageBox.information(self, "成功", "测试用例已保存")
        self.load_test_cases()
        
    def delete_test_case(self):
        if not self.case_id:
            return
            
        reply = QMessageBox.question(
            self, "确认删除", 
            "确定要删除这个测试用例吗？此操作不可恢复。",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            cursor = self.db.conn.cursor()
            cursor.execute('DELETE FROM test_cases WHERE id=?', (self.case_id,))
            cursor.execute('DELETE FROM test_steps WHERE case_id=?', (self.case_id,))
            self.db.conn.commit()
            
            self.case_id = None
            self.detail_widget.setVisible(False)
            self.load_test_cases()
            
    def duplicate_test_case(self):
        if not self.case_id:
            return
            
        # 获取当前测试用例数据
        test_cases = self.db.get_test_cases()
        for case in test_cases:
            if case[0] == self.case_id:
                _, name, description, priority, type, _, _, status = case
                break
                
        # 创建新测试用例
        new_name = f"{name} - 副本"
        new_case_id = self.db.add_test_case(
            new_name, description, priority, type
        )
        
        # 复制测试步骤
        steps = self.db.get_test_steps(self.case_id)
        for step in steps:
            _, _, step_number, action, expected_result = step
            self.db.add_test_step(new_case_id, step_number, action, expected_result)
            
        QMessageBox.information(self, "成功", "测试用例已复制")
        self.load_test_cases()
        
    def run_selected_test_cases(self):
        selected_items = self.tree_widget.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "警告", "请先选择要运行的测试用例")
            return
            
        for item in selected_items:
            case_id = item.data(0, Qt.UserRole)
            self.run_test_case(case_id)
            
    def run_all_test_cases(self):
        if self.tree_widget.topLevelItemCount() == 0:
            QMessageBox.warning(self, "警告", "没有可运行的测试用例")
            return
            
        for i in range(self.tree_widget.topLevelItemCount()):
            item = self.tree_widget.topLevelItem(i)
            if not item.isHidden():  # 只运行未过滤的测试用例
                case_id = item.data(0, Qt.UserRole)
                self.run_test_case(case_id)
                
    def run_test_case(self, case_id):
        # 检查是否已经在运行
        if case_id in self.test_case_runners:
            QMessageBox.warning(self, "警告", "该测试用例正在运行中")
            return
            
        # 获取测试步骤
        steps = []
        db_steps = self.db.get_test_steps(case_id)
        for step in db_steps:
            _, _, step_number, action, expected_result = step
            steps.append((step_number, action, expected_result))
            
        # 创建并启动测试线程
        runner = TestCaseRunnerThread(case_id, steps)
        runner.update_signal.connect(self.on_test_case_status_updated)
        runner.log_signal.connect(self.on_test_case_log)
        runner.finished.connect(lambda: self.on_test_case_finished(case_id))
        
        self.test_case_runners[case_id] = runner
        runner.start()
        
    def stop_test_cases(self):
        for case_id, runner in self.test_case_runners.items():
            runner.stop()
            runner.wait()
            
        self.test_case_runners.clear()
        QMessageBox.information(self, "信息", "已停止所有测试用例运行")
        
    def on_test_case_status_updated(self, case_id, status):
        # 更新数据库状态
        cursor = self.db.conn.cursor()
        cursor.execute('UPDATE test_cases SET status=? WHERE id=?', (status, case_id))
        self.db.conn.commit()
        
        # 更新UI
        for i in range(self.tree_widget.topLevelItemCount()):
            item = self.tree_widget.topLevelItem(i)
            if item.data(0, Qt.UserRole) == case_id:
                item.setText(1, status)
                
                # 根据状态设置颜色
                if status == "成功":
                    item.setForeground(1, QColor(0, 128, 0))  # 绿色
                elif status == "失败":
                    item.setForeground(1, QColor(255, 0, 0))  # 红色
                elif status == "执行中":
                    item.setForeground(1, QColor(0, 0, 255))  # 蓝色
                    
                break
                
        # 如果当前正在查看这个测试用例，更新状态标签
        if self.case_id == case_id:
            self.case_status.setText(status)
            
    def on_test_case_log(self, case_id, message):
        # 如果当前正在查看这个测试用例，添加日志
        if self.case_id == case_id:
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.execution_log.append(f"[{timestamp}] {message}")
            
    def on_test_case_finished(self, case_id):
        # 从运行列表中移除
        if case_id in self.test_case_runners:
            del self.test_case_runners[case_id]
            
    def new_test_case(self):
        self.case_id = None
        self.case_name.clear()
        self.case_description.clear()
        self.case_priority.setCurrentIndex(0)
        self.case_type.setCurrentIndex(0)
        self.case_status.setText("未执行")
        self.steps_table.setRowCount(0)
        self.execution_log.clear()
        self.detail_widget.setVisible(True)
        
    def import_test_cases(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "导入测试用例", "", 
            "JSON Files (*.json);;CSV Files (*.csv);;All Files (*)"
        )
        
        if file_path:
            try:
                if file_path.endswith('.json'):
                    self.import_from_json(file_path)
                elif file_path.endswith('.csv'):
                    self.import_from_csv(file_path)
                    
                QMessageBox.information(self, "成功", "测试用例导入成功")
                self.load_test_cases()
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导入失败: {str(e)}")
                
    def export_test_cases(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出测试用例", "", 
            "JSON Files (*.json);;CSV Files (*.csv);;All Files (*)"
        )
        
        if file_path:
            try:
                if file_path.endswith('.json'):
                    self.export_to_json(file_path)
                elif file_path.endswith('.csv'):
                    self.export_to_csv(file_path)
                    
                QMessageBox.information(self, "成功", "测试用例导出成功")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导出失败: {str(e)}")
                
    def import_from_json(self, file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        for case_data in data:
            case_id = self.db.add_test_case(
                case_data['name'],
                case_data.get('description', ''),
                case_data.get('priority', '中'),
                case_data.get('type', '功能测试')
            )
            
            for step_data in case_data.get('steps', []):
                self.db.add_test_step(
                    case_id,
                    step_data['step_number'],
                    step_data['action'],
                    step_data['expected_result']
                )
                
    def export_to_json(self, file_path):
        test_cases = self.db.get_test_cases()
        data = []
        
        for case in test_cases:
            case_id, name, description, priority, type, created_date, modified_date, status = case
            case_data = {
                'name': name,
                'description': description,
                'priority': priority,
                'type': type,
                'status': status,
                'created_date': created_date,
                'modified_date': modified_date,
                'steps': []
            }
            
            steps = self.db.get_test_steps(case_id)
            for step in steps:
                _, _, step_number, action, expected_result = step
                case_data['steps'].append({
                    'step_number': step_number,
                    'action': action,
                    'expected_result': expected_result
                })
                
            data.append(case_data)
            
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            
    def import_from_csv(self, file_path):
        # CSV导入逻辑
        pass
        
    def export_to_csv(self, file_path):
        # CSV导出逻辑
        pass

# 增强的性能监控器
class EnhancedPerformanceMonitor(QWidget):
    def __init__(self):
        super().__init__()
        self.db = TestDatabase()
        self.monitor_thread = None
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 控制面板
        control_group = QGroupBox("监控控制")
        control_layout = QFormLayout()
        
        self.monitor_target = QLineEdit("http://example.com")
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(1, 60)
        self.interval_spin.setValue(5)
        self.interval_spin.setSuffix(" 秒")
        
        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(0, 24*60)  # 0分钟到24小时
        self.duration_spin.setValue(0)
        self.duration_spin.setSuffix(" 分钟")
        self.duration_spin.setSpecialValueText("无限")
        
        self.start_btn = QPushButton("开始监控")
        self.stop_btn = QPushButton("停止监控")
        self.stop_btn.setEnabled(False)
        self.export_btn = QPushButton("导出数据")
        
        control_layout.addRow("监控目标:", self.monitor_target)
        control_layout.addRow("监控间隔:", self.interval_spin)
        control_layout.addRow("监控时长:", self.duration_spin)
        control_layout.addRow(self.start_btn, self.stop_btn)
        control_layout.addRow("", self.export_btn)
        
        control_group.setLayout(control_layout)
        
        # 指标显示
        metrics_group = QGroupBox("实时指标")
        metrics_layout = QHBoxLayout()
        
        self.cpu_label = QLabel("0%")
        self.cpu_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.memory_label = QLabel("0 MB")
        self.memory_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.response_label = QLabel("0 ms")
        self.response_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.throughput_label = QLabel("0 req/s")
        self.throughput_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        
        metrics_layout.addWidget(QLabel("CPU:"))
        metrics_layout.addWidget(self.cpu_label)
        metrics_layout.addWidget(QLabel("内存:"))
        metrics_layout.addWidget(self.memory_label)
        metrics_layout.addWidget(QLabel("响应时间:"))
        metrics_layout.addWidget(self.response_label)
        metrics_layout.addWidget(QLabel("吞吐量:"))
        metrics_layout.addWidget(self.throughput_label)
        
        metrics_group.setLayout(metrics_layout)
        
        # 图表区域
        chart_group = QGroupBox("性能图表")
        chart_layout = QVBoxLayout()
        
        self.chart_tabs = QTabWidget()
        
        # CPU图表
        self.cpu_chart = RealTimeChart()
        cpu_tab = QWidget()
        cpu_layout = QVBoxLayout()
        cpu_layout.addWidget(self.cpu_chart)
        cpu_tab.setLayout(cpu_layout)
        self.chart_tabs.addTab(cpu_tab, "CPU使用率")
        
        # 内存图表
        self.memory_chart = RealTimeChart()
        memory_tab = QWidget()
        memory_layout = QVBoxLayout()
        memory_layout.addWidget(self.memory_chart)
        memory_tab.setLayout(memory_layout)
        self.chart_tabs.addTab(memory_tab, "内存使用")
        
        # 响应时间图表
        self.response_chart = RealTimeChart()
        response_tab = QWidget()
        response_layout = QVBoxLayout()
        response_layout.addWidget(self.response_chart)
        response_tab.setLayout(response_layout)
        self.chart_tabs.addTab(response_tab, "响应时间")
        
        # 吞吐量图表
        self.throughput_chart = RealTimeChart()
        throughput_tab = QWidget()
        throughput_layout = QVBoxLayout()
        throughput_layout.addWidget(self.throughput_chart)
        throughput_tab.setLayout(throughput_layout)
        self.chart_tabs.addTab(throughput_tab, "吞吐量")
        
        chart_layout.addWidget(self.chart_tabs)
        chart_group.setLayout(chart_layout)
        
        # 历史数据
        history_group = QGroupBox("历史数据")
        history_layout = QVBoxLayout()
        
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(6)
        self.history_table.setHorizontalHeaderLabels(["时间", "目标", "CPU(%)", "内存(MB)", "响应时间(ms)", "吞吐量(req/s)"])
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        history_layout.addWidget(self.history_table)
        history_group.setLayout(history_layout)
        
        # 添加到主布局
        layout.addWidget(control_group)
        layout.addWidget(metrics_group)
        layout.addWidget(chart_group)
        layout.addWidget(history_group)
        
        self.setLayout(layout)
        
        # 连接信号
        self.start_btn.clicked.connect(self.start_monitoring)
        self.stop_btn.clicked.connect(self.stop_monitoring)
        self.export_btn.clicked.connect(self.export_data)
        
        # 加载历史数据
        self.load_history_data()
        
    def start_monitoring(self):
        target_url = self.monitor_target.text()
        interval = self.interval_spin.value()
        duration = self.duration_spin.value() * 60 if self.duration_spin.value() > 0 else None
        
        if not target_url:
            QMessageBox.warning(self, "警告", "请输入监控目标")
            return
            
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        
        # 清空图表数据
        self.chart_data = {
            'timestamps': [],
            'cpu_usage': [],
            'memory_usage': [],
            'response_time': [],
            'throughput': []
        }
        
        # 创建并启动监控线程
        self.monitor_thread = PerformanceMonitorThread(target_url, interval, duration)
        self.monitor_thread.update_signal.connect(self.update_metrics_display)
        self.monitor_thread.finished.connect(self.on_monitoring_finished)
        self.monitor_thread.start()
        
    def stop_monitoring(self):
        if self.monitor_thread:
            self.monitor_thread.stop()
            self.monitor_thread.wait()
            
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        
    def on_monitoring_finished(self):
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        # 重新加载历史数据
        self.load_history_data()
        
    def update_metrics_display(self, metrics):
        # 更新指标标签
        self.cpu_label.setText(f"{metrics['cpu_usage']:.1f}%")
        self.memory_label.setText(f"{metrics['memory_usage']:.1f} MB")
        self.response_label.setText(f"{metrics['response_time']:.1f} ms")
        self.throughput_label.setText(f"{metrics['throughput']:.1f} req/s")
        
        # 更新图表数据
        timestamp = datetime.now()
        time_str = timestamp.strftime("%H:%M:%S")
        
        self.chart_data['timestamps'].append(time_str)
        self.chart_data['cpu_usage'].append(metrics['cpu_usage'])
        self.chart_data['memory_usage'].append(metrics['memory_usage'])
        self.chart_data['response_time'].append(metrics['response_time'])
        self.chart_data['throughput'].append(metrics['throughput'])
        
        # 限制数据点数量
        max_points = 20
        if len(self.chart_data['timestamps']) > max_points:
            for key in self.chart_data:
                self.chart_data[key] = self.chart_data[key][-max_points:]
                
        # 更新图表
        self.cpu_chart.update_chart(
            self.chart_data['timestamps'], 
            self.chart_data['cpu_usage'],
            "CPU使用率",
            "百分比 (%)"
        )
        
        self.memory_chart.update_chart(
            self.chart_data['timestamps'], 
            self.chart_data['memory_usage'],
            "内存使用",
            "MB"
        )
        
        self.response_chart.update_chart(
            self.chart_data['timestamps'], 
            self.chart_data['response_time'],
            "响应时间",
            "毫秒 (ms)"
        )
        
        self.throughput_chart.update_chart(
            self.chart_data['timestamps'], 
            self.chart_data['throughput'],
            "吞吐量",
            "请求/秒 (req/s)"
        )
        
    def load_history_data(self):
        target_url = self.monitor_target.text()
        if not target_url:
            return
            
        data = self.db.get_performance_data(target_url, 50)
        self.history_table.setRowCount(len(data))
        
        for row, record in enumerate(data):
            _, target, cpu, memory, response, throughput, timestamp = record
            time_str = datetime.fromisoformat(timestamp).strftime("%Y-%m-%d %H:%M:%S")
            
            self.history_table.setItem(row, 0, QTableWidgetItem(time_str))
            self.history_table.setItem(row, 1, QTableWidgetItem(target))
            self.history_table.setItem(row, 2, QTableWidgetItem(f"{cpu:.1f}"))
            self.history_table.setItem(row, 3, QTableWidgetItem(f"{memory:.1f}"))
            self.history_table.setItem(row, 4, QTableWidgetItem(f"{response:.1f}"))
            self.history_table.setItem(row, 5, QTableWidgetItem(f"{throughput:.1f}"))
            
    def export_data(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出性能数据", "", 
            "CSV Files (*.csv);;JSON Files (*.json);;All Files (*)"
        )
        
        if file_path:
            try:
                target_url = self.monitor_target.text()
                data = self.db.get_performance_data(target_url, 1000)
                
                if file_path.endswith('.csv'):
                    with open(file_path, 'w', newline='', encoding='utf-8') as f:
                        writer = csv.writer(f)
                        writer.writerow(['时间', '目标', 'CPU(%)', '内存(MB)', '响应时间(ms)', '吞吐量(req/s)'])
                        
                        for record in data:
                            _, target, cpu, memory, response, throughput, timestamp = record
                            time_str = datetime.fromisoformat(timestamp).strftime("%Y-%m-%d %H:%M:%S")
                            writer.writerow([time_str, target, f"{cpu:.1f}", f"{memory:.1f}", f"{response:.1f}", f"{throughput:.1f}"])
                            
                elif file_path.endswith('.json'):
                    json_data = []
                    for record in data:
                        _, target, cpu, memory, response, throughput, timestamp = record
                        time_str = datetime.fromisoformat(timestamp).strftime("%Y-%m-%d %H:%M:%S")
                        json_data.append({
                            'timestamp': time_str,
                            'target': target,
                            'cpu_usage': cpu,
                            'memory_usage': memory,
                            'response_time': response,
                            'throughput': throughput
                        })
                        
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump(json_data, f, ensure_ascii=False, indent=2)
                        
                QMessageBox.information(self, "成功", "数据导出成功")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导出失败: {str(e)}")

# 增强的API测试器
class EnhancedAPITester(QWidget):
    def __init__(self):
        super().__init__()
        self.db = TestDatabase()
        self.init_ui()
        self.load_history()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # API 请求配置
        config_group = QGroupBox("API 配置")
        config_layout = QFormLayout()
        
        self.url_input = QLineEdit("https://jsonplaceholder.typicode.com/posts")
        self.method_combo = QComboBox()
        self.method_combo.addItems(["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"])
        
        self.auth_check = QCheckBox("需要认证")
        self.auth_type = QComboBox()
        self.auth_type.addItems(["Basic", "Bearer Token", "API Key", "OAuth 2.0"])
        self.auth_type.setEnabled(False)
        
        self.auth_check.stateChanged.connect(lambda state: self.auth_type.setEnabled(state == Qt.Checked))
        
        config_layout.addRow("URL:", self.url_input)
        config_layout.addRow("方法:", self.method_combo)
        config_layout.addRow(self.auth_check, self.auth_type)
        
        config_group.setLayout(config_layout)
        
        # 请求参数
        params_group = QGroupBox("请求参数")
        params_layout = QVBoxLayout()
        
        # 参数表格
        self.params_table = QTableWidget()
        self.params_table.setColumnCount(2)
        self.params_table.setHorizontalHeaderLabels(["参数", "值"])
        self.params_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        params_buttons = QHBoxLayout()
        add_param_btn = QPushButton("添加参数")
        remove_param_btn = QPushButton("删除参数")
        
        add_param_btn.clicked.connect(self.add_parameter)
        remove_param_btn.clicked.connect(self.remove_parameter)
        
        params_buttons.addWidget(add_param_btn)
        params_buttons.addWidget(remove_param_btn)
        
        params_layout.addWidget(QLabel("查询参数:"))
        params_layout.addWidget(self.params_table)
        params_layout.addLayout(params_buttons)
        
        # 请求头
        self.headers_input = QTextEdit()
        self.headers_input.setPlaceholderText('{"Content-Type": "application/json"}')
        
        # 请求体
        self.body_input = QTextEdit()
        self.body_input.setPlaceholderText('{"key": "value"}')
        
        params_layout.addWidget(QLabel("请求头:"))
        params_layout.addWidget(self.headers_input)
        params_layout.addWidget(QLabel("请求体:"))
        params_layout.addWidget(self.body_input)
        
        params_group.setLayout(params_layout)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        self.send_btn = QPushButton("发送请求")
        self.save_btn = QPushButton("保存为测试用例")
        self.history_btn = QPushButton("查看历史")
        
        button_layout.addWidget(self.send_btn)
        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.history_btn)
        
        # 响应显示
        response_group = QGroupBox("响应")
        response_layout = QVBoxLayout()
        
        self.status_label = QLabel("状态: 未发送")
        self.time_label = QLabel("时间: -")
        self.size_label = QLabel("大小: -")
        
        info_layout = QHBoxLayout()
        info_layout.addWidget(self.status_label)
        info_layout.addWidget(self.time_label)
        info_layout.addWidget(self.size_label)
        
        self.response_output = QTextEdit()
        self.response_output.setReadOnly(True)
        
        response_layout.addLayout(info_layout)
        response_layout.addWidget(self.response_output)
        
        response_group.setLayout(response_layout)
        
        # 历史记录
        self.history_group = QGroupBox("历史记录")
        history_layout = QVBoxLayout()
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(5)
        self.history_table.setHorizontalHeaderLabels(["时间", "方法", "URL", "状态码", "响应时间"])
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.history_table.doubleClicked.connect(self.load_history_item)
        
        history_layout.addWidget(self.history_table)
        self.history_group.setLayout(history_layout)
        self.history_group.setVisible(False)
        
        # 组装主布局
        layout.addWidget(config_group)
        layout.addWidget(params_group)
        layout.addLayout(button_layout)
        layout.addWidget(response_group)
        layout.addWidget(self.history_group)
        
        self.setLayout(layout)
        
        # 连接信号
        self.send_btn.clicked.connect(self.send_api_request)
        self.save_btn.clicked.connect(self.save_as_test_case)
        self.history_btn.clicked.connect(self.toggle_history)
        
    def add_parameter(self):
        row_count = self.params_table.rowCount()
        self.params_table.insertRow(row_count)
        self.params_table.setItem(row_count, 0, QTableWidgetItem(""))
        self.params_table.setItem(row_count, 1, QTableWidgetItem(""))
        
    def remove_parameter(self):
        current_row = self.params_table.currentRow()
        if current_row >= 0:
            self.params_table.removeRow(current_row)
            
    def send_api_request(self):
        url = self.url_input.text()
        method = self.method_combo.currentText()
        
        if not url:
            QMessageBox.warning(self, "警告", "请输入URL")
            return
            
        # 构建查询参数
        params = {}
        for row in range(self.params_table.rowCount()):
            key_item = self.params_table.item(row, 0)
            value_item = self.params_table.item(row, 1)
            
            if key_item and value_item and key_item.text():
                params[key_item.text()] = value_item.text()
                
        # 如果有参数，添加到URL
        if params:
            from urllib.parse import urlencode
            url += '?' + urlencode(params)
            
        try:
            headers = {}
            if self.headers_input.toPlainText().strip():
                headers = json.loads(self.headers_input.toPlainText())
                
            body = None
            if self.body_input.toPlainText().strip():
                body = json.loads(self.body_input.toPlainText())
                
        except json.JSONDecodeError as e:
            QMessageBox.warning(self, "格式错误", f"JSON 格式错误: {e}")
            return
            
        try:
            start_time = time.time()
            
            if method == "GET":
                response = requests.get(url, headers=headers)
            elif method == "POST":
                response = requests.post(url, json=body, headers=headers)
            elif method == "PUT":
                response = requests.put(url, json=body, headers=headers)
            elif method == "DELETE":
                response = requests.delete(url, headers=headers)
            elif method == "PATCH":
                response = requests.patch(url, json=body, headers=headers)
            elif method == "HEAD":
                response = requests.head(url, headers=headers)
            elif method == "OPTIONS":
                response = requests.options(url, headers=headers)
                
            end_time = time.time()
            response_time = round((end_time - start_time) * 1000, 2)
            
            # 显示响应
            self.status_label.setText(f"状态: {response.status_code}")
            self.time_label.setText(f"时间: {response_time}ms")
            self.size_label.setText(f"大小: {len(response.content)} bytes")
            
            # 根据状态码设置颜色
            if response.status_code >= 200 and response.status_code < 300:
                self.status_label.setStyleSheet("color: green;")
            elif response.status_code >= 400 and response.status_code < 500:
                self.status_label.setStyleSheet("color: orange;")
            elif response.status_code >= 500:
                self.status_label.setStyleSheet("color: red;")
            else:
                self.status_label.setStyleSheet("")
                
            try:
                formatted_json = json.dumps(response.json(), indent=2)
                self.response_output.setPlainText(formatted_json)
            except:
                self.response_output.setPlainText(response.text)
                
            # 保存到历史记录
            success = response.status_code >= 200 and response.status_code < 300
            self.db.save_api_test_result(url, method, response.status_code, response_time, success)
            self.load_history()
            
        except Exception as e:
            self.status_label.setText(f"错误: {str(e)}")
            self.status_label.setStyleSheet("color: red;")
            self.response_output.setPlainText("")
            
    def save_as_test_case(self):
        # 保存为测试用例的逻辑
        name, ok = QInputDialog.getText(self, "保存测试用例", "请输入测试用例名称:")
        if ok and name:
            db = TestDatabase()
            case_id = db.add_test_case(
                name,
                f"API测试: {self.method_combo.currentText()} {self.url_input.text()}",
                "中",
                "API测试"
            )
            
            # 添加测试步骤
            db.add_test_step(case_id, 1, f"发送{self.method_combo.currentText()}请求到{self.url_input.text()}", "返回状态码2xx")
            
            QMessageBox.information(self, "成功", "测试用例已保存")
            
    def load_history(self):
        history = self.db.get_api_test_history(20)
        self.history_table.setRowCount(len(history))
        
        for row, record in enumerate(history):
            _, url, method, status_code, response_time, timestamp, success = record
            time_str = datetime.fromisoformat(timestamp).strftime("%Y-%m-%d %H:%M:%S")
            
            self.history_table.setItem(row, 0, QTableWidgetItem(time_str))
            self.history_table.setItem(row, 1, QTableWidgetItem(method))
            self.history_table.setItem(row, 2, QTableWidgetItem(url))
            self.history_table.setItem(row, 3, QTableWidgetItem(str(status_code)))
            self.history_table.setItem(row, 4, QTableWidgetItem(f"{response_time}ms"))
            
            # 根据成功状态设置颜色
            if success:
                self.history_table.item(row, 3).setForeground(QColor(0, 128, 0))
            else:
                self.history_table.item(row, 3).setForeground(QColor(255, 0, 0))
                
    def toggle_history(self):
        self.history_group.setVisible(not self.history_group.isVisible())
        if self.history_group.isVisible():
            self.history_btn.setText("隐藏历史")
        else:
            self.history_btn.setText("查看历史")
            
    def load_history_item(self, index):
        row = index.row()
        method = self.history_table.item(row, 1).text()
        url = self.history_table.item(row, 2).text()
        
        self.method_combo.setCurrentText(method)
        self.url_input.setText(url)

# 增强的UI自动化工具
class EnhancedUIAutomation(QWidget):
    def __init__(self):
        super().__init__()
        self.recording = False
        self.actions = []
        self.driver = None
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 浏览器控制
        browser_group = QGroupBox("浏览器控制")
        browser_layout = QHBoxLayout()
        
        self.browser_type = QComboBox()
        self.browser_type.addItems(["Chrome", "Firefox", "Edge"])
        
        self.start_browser_btn = QPushButton("启动浏览器")
        self.stop_browser_btn = QPushButton("关闭浏览器")
        self.stop_browser_btn.setEnabled(False)
        
        self.url_input = QLineEdit("https://www.example.com")
        self.go_btn = QPushButton("转到")
        
        browser_layout.addWidget(QLabel("浏览器:"))
        browser_layout.addWidget(self.browser_type)
        browser_layout.addWidget(self.start_browser_btn)
        browser_layout.addWidget(self.stop_browser_btn)
        browser_layout.addWidget(QLabel("URL:"))
        browser_layout.addWidget(self.url_input)
        browser_layout.addWidget(self.go_btn)
        
        browser_group.setLayout(browser_layout)
        
        # 录制控制
        record_group = QGroupBox("录制控制")
        record_layout = QHBoxLayout()
        
        self.record_btn = QPushButton("开始录制")
        self.stop_btn = QPushButton("停止录制")
        self.playback_btn = QPushButton("回放")
        self.export_btn = QPushButton("导出脚本")
        self.import_btn = QPushButton("导入脚本")
        
        record_layout.addWidget(self.record_btn)
        record_layout.addWidget(self.stop_btn)
        record_layout.addWidget(self.playback_btn)
        record_layout.addWidget(self.export_btn)
        record_layout.addWidget(self.import_btn)
        
        record_group.setLayout(record_layout)
        
        # 动作列表
        actions_group = QGroupBox("录制动作")
        actions_layout = QVBoxLayout()
        
        self.actions_table = QTableWidget()
        self.actions_table.setColumnCount(4)
        self.actions_table.setHorizontalHeaderLabels(["时间", "元素", "动作", "值"])
        self.actions_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        actions_buttons = QHBoxLayout()
        self.clear_btn = QPushButton("清空动作")
        self.edit_btn = QPushButton("编辑动作")
        self.delete_btn = QPushButton("删除动作")
        
        actions_buttons.addWidget(self.clear_btn)
        actions_buttons.addWidget(self.edit_btn)
        actions_buttons.addWidget(self.delete_btn)
        
        actions_layout.addWidget(self.actions_table)
        actions_layout.addLayout(actions_buttons)
        actions_group.setLayout(actions_layout)
        
        # 元素定位
        element_group = QGroupBox("元素定位")
        element_layout = QFormLayout()
        
        self.locator_type = QComboBox()
        self.locator_type.addItems(["ID", "Name", "XPath", "CSS Selector", "Class Name", "Tag Name", "Link Text"])
        
        self.locator_value = QLineEdit()
        self.test_locator_btn = QPushButton("测试定位")
        
        element_layout.addRow("定位类型:", self.locator_type)
        element_layout.addRow("定位值:", self.locator_value)
        element_layout.addRow(self.test_locator_btn)
        
        element_group.setLayout(element_layout)
        
        # 日志输出
        log_group = QGroupBox("日志")
        log_layout = QVBoxLayout()
        
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        
        log_layout.addWidget(self.log_output)
        log_group.setLayout(log_layout)
        
        # 组装主布局
        layout.addWidget(browser_group)
        layout.addWidget(record_group)
        layout.addWidget(actions_group)
        layout.addWidget(element_group)
        layout.addWidget(log_group)
        
        self.setLayout(layout)
        
        # 连接信号
        self.start_browser_btn.clicked.connect(self.start_browser)
        self.stop_browser_btn.clicked.connect(self.stop_browser)
        self.go_btn.clicked.connect(self.navigate_to_url)
        self.record_btn.clicked.connect(self.start_recording)
        self.stop_btn.clicked.connect(self.stop_recording)
        self.playback_btn.clicked.connect(self.playback)
        self.export_btn.clicked.connect(self.export_script)
        self.import_btn.clicked.connect(self.import_script)
        self.clear_btn.clicked.connect(self.clear_actions)
        self.test_locator_btn.clicked.connect(self.test_locator)
        
    def start_browser(self):
        browser = self.browser_type.currentText()
        self.log_output.append(f"启动 {browser} 浏览器...")
        
        try:
            if browser == "Chrome":
                from selenium.webdriver.chrome.options import Options
                options = Options()
                options.add_argument("--disable-notifications")
                self.driver = webdriver.Chrome(options=options)
            elif browser == "Firefox":
                from selenium.webdriver.firefox.options import Options
                options = Options()
                options.set_preference("dom.webnotifications.enabled", False)
                self.driver = webdriver.Firefox(options=options)
            elif browser == "Edge":
                from selenium.webdriver.edge.options import Options
                options = Options()
                options.add_argument("--disable-notifications")
                self.driver = webdriver.Edge(options=options)
                
            self.driver.maximize_window()
            self.navigate_to_url()
            
            self.start_browser_btn.setEnabled(False)
            self.stop_browser_btn.setEnabled(True)
            self.record_btn.setEnabled(True)
            
            self.log_output.append("浏览器启动成功")
        except Exception as e:
            self.log_output.append(f"浏览器启动失败: {str(e)}")
            
    def stop_browser(self):
        if self.driver:
            self.driver.quit()
            self.driver = None
            
        self.start_browser_btn.setEnabled(True)
        self.stop_browser_btn.setEnabled(False)
        self.record_btn.setEnabled(False)
        self.log_output.append("浏览器已关闭")
        
    def navigate_to_url(self):
        if not self.driver:
            self.log_output.append("请先启动浏览器")
            return
            
        url = self.url_input.text()
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
            
        try:
            self.driver.get(url)
            self.log_output.append(f"已导航到: {url}")
        except Exception as e:
            self.log_output.append(f"导航失败: {str(e)}")
            
    def start_recording(self):
        if not self.driver:
            self.log_output.append("请先启动浏览器")
            return
            
        self.recording = True
        self.record_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.log_output.append("开始录制 UI 操作...")
        
        # 这里应该添加事件监听器来捕获用户操作
        # 由于Selenium的限制，这需要复杂的实现
        # 此处仅作演示
        
    def stop_recording(self):
        self.recording = False
        self.record_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.log_output.append("停止录制 UI 操作")
        
    def playback(self):
        if not self.driver:
            self.log_output.append("请先启动浏览器")
            return
            
        if not self.actions:
            self.log_output.append("没有可回放的录制动作")
            return
            
        self.log_output.append("开始回放 UI 操作")
        
        # 这里应该实现回放录制的动作
        # 此处仅作演示
        
    def export_script(self):
        if not self.actions:
            QMessageBox.warning(self, "警告", "没有可导出的录制动作")
            return
            
        file_path, _ = QFileDialog.getSaveFileName(self, "导出脚本", "", "Python Files (*.py);;All Files (*)")
        if file_path:
            try:
                # 这里应该生成Python脚本代码
                script = "# 自动化测试脚本\n# 生成时间: {}\n\n".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                script += "from selenium import webdriver\nfrom selenium.webdriver.common.by import By\nfrom selenium.webdriver.support.ui import WebDriverWait\nfrom selenium.webdriver.support import expected_conditions as EC\n\n"
                script += "driver = webdriver.Chrome()\n"
                script += "driver.get('{}')\n\n".format(self.url_input.text())
                
                for action in self.actions:
                    script += "# {}\n".format(action['description'])
                    # 这里应该根据动作类型生成相应的代码
                    
                script += "\ndriver.quit()\n"
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(script)
                    
                self.log_output.append(f"脚本已导出到: {file_path}")
            except Exception as e:
                self.log_output.append(f"导出失败: {str(e)}")
                
    def import_script(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "导入脚本", "", "Python Files (*.py);;All Files (*)")
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    script = f.read()
                    
                # 这里应该解析脚本并转换为动作列表
                # 此处仅作演示
                self.log_output.append(f"脚本已从 {file_path} 导入")
            except Exception as e:
                self.log_output.append(f"导入失败: {str(e)}")
                
    def clear_actions(self):
        self.actions_table.setRowCount(0)
        self.actions = []
        self.log_output.append("已清空所有动作")
        
    def test_locator(self):
        if not self.driver:
            self.log_output.append("请先启动浏览器")
            return
            
        locator_type = self.locator_type.currentText()
        locator_value = self.locator_value.text()
        
        if not locator_value:
            self.log_output.append("请输入定位值")
            return
            
        try:
            if locator_type == "ID":
                element = self.driver.find_element(By.ID, locator_value)
            elif locator_type == "Name":
                element = self.driver.find_element(By.NAME, locator_value)
            elif locator_type == "XPath":
                element = self.driver.find_element(By.XPATH, locator_value)
            elif locator_type == "CSS Selector":
                element = self.driver.find_element(By.CSS_SELECTOR, locator_value)
            elif locator_type == "Class Name":
                element = self.driver.find_element(By.CLASS_NAME, locator_value)
            elif locator_type == "Tag Name":
                element = self.driver.find_element(By.TAG_NAME, locator_value)
            elif locator_type == "Link Text":
                element = self.driver.find_element(By.LINK_TEXT, locator_value)
                
            # 高亮显示找到的元素
            self.driver.execute_script("arguments[0].style.border='3px solid red'", element)
            self.log_output.append(f"找到元素: {element.tag_name}")
            
        except Exception as e:
            self.log_output.append(f"元素定位失败: {str(e)}")

# 主窗口
class TestEngineerToolkit(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("测试工程师高级工具库")
        self.setGeometry(100, 100, 1400, 900)
        
        # 初始化数据库
        self.db = TestDatabase()
        
        # 创建中央部件和选项卡
        self.tabs = QTabWidget()
        
        # 添加各个功能模块
        self.test_case_manager = EnhancedTestCaseManager()
        self.performance_monitor = EnhancedPerformanceMonitor()
        self.api_tester = EnhancedAPITester()
        self.ui_automation = EnhancedUIAutomation()
        
        self.tabs.addTab(self.test_case_manager, "测试用例管理")
        self.tabs.addTab(self.performance_monitor, "性能监控")
        self.tabs.addTab(self.api_tester, "API 测试")
        self.tabs.addTab(self.ui_automation, "UI 自动化")
        
        self.setCentralWidget(self.tabs)
        
        # 创建菜单栏
        self.create_menu_bar()
        
        # 创建工具栏
        self.create_tool_bar()
        
        # 创建状态栏
        self.statusBar().showMessage("就绪")
        
        # 加载设置
        self.load_settings()
        
    def create_menu_bar(self):
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
        
        settings_action = QAction("设置", self)
        tools_menu.addAction(settings_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu("帮助")
        
        about_action = QAction("关于", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
    def create_tool_bar(self):
        toolbar = QToolBar("主工具栏")
        toolbar.setIconSize(QSize(16, 16))
        self.addToolBar(toolbar)
        
        new_btn = QAction(QIcon.fromTheme("document-new"), "新建", self)
        toolbar.addAction(new_btn)
        
        save_btn = QAction(QIcon.fromTheme("document-save"), "保存", self)
        toolbar.addAction(save_btn)
        
        toolbar.addSeparator()
        
        run_btn = QAction(QIcon.fromTheme("media-playback-start"), "运行", self)
        toolbar.addAction(run_btn)
        
        stop_btn = QAction(QIcon.fromTheme("media-playback-stop"), "停止", self)
        toolbar.addAction(stop_btn)
        
    def load_settings(self):
        settings = QSettings("TestEngineer", "Toolkit")
        geometry = settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
            
        window_state = settings.value("windowState")
        if window_state:
            self.restoreState(window_state)
            
    def save_settings(self):
        settings = QSettings("TestEngineer", "Toolkit")
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("windowState", self.saveState())
        
    def show_about(self):
        QMessageBox.about(self, "关于测试工程师工具库", 
                         "测试工程师高级工具库\n\n"
                         "一个功能强大的测试工程师工具集合，包含:\n"
                         "- 测试用例管理\n"
                         "- 性能监控\n"
                         "- API测试\n"
                         "- UI自动化\n\n"
                         "版本: 2.0\n"
                         "版权所有 © 2025")
        
    def closeEvent(self, event):
        self.save_settings()
        
        # 停止所有正在运行的线程
        if hasattr(self.test_case_manager, 'test_case_runners'):
            for runner in self.test_case_manager.test_case_runners.values():
                runner.stop()
                runner.wait()
                
        if hasattr(self.performance_monitor, 'monitor_thread') and self.performance_monitor.monitor_thread:
            self.performance_monitor.monitor_thread.stop()
            self.performance_monitor.monitor_thread.wait()
            
        if hasattr(self.ui_automation, 'driver') and self.ui_automation.driver:
            self.ui_automation.driver.quit()
            
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")  # 使用 Fusion 样式，看起来更现代
    
    # 设置应用程序信息
    app.setApplicationName("测试工程师高级工具库")
    app.setApplicationVersion("2.0")
    app.setOrganizationName("TestEngineer")
    
    window = TestEngineerToolkit()
    window.show()
    
    sys.exit(app.exec_())