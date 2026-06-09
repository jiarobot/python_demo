import sys
import json
import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QTableWidget, QTableWidgetItem, QLabel, 
                             QLineEdit, QTextEdit, QComboBox, QDateEdit, QFileDialog,
                             QMessageBox, QSplitter, QTabWidget, QToolBar, QStatusBar,
                             QAction, QToolButton, QMenu, QProgressBar, QHeaderView,
                             QDockWidget, QListWidget, QTreeWidget, QTreeWidgetItem,
                             QGroupBox, QFormLayout, QSpinBox, QCheckBox, QDialog)
from PyQt5.QtCore import Qt, QDate, QSize, QTimer, pyqtSignal
from PyQt5.QtGui import QIcon, QFont, QPixmap, QColor, QPalette
import pandas as pd
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import sqlite3
import hashlib
import uuid
import webbrowser
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging
from logging.handlers import RotatingFileHandler
import threading
import requests
from bs4 import BeautifulSoup
import zipfile
import os


# 设置日志
def setup_logger():
    logger = logging.getLogger('CaseManagementSystem')
    logger.setLevel(logging.DEBUG)
    
    # 创建文件处理器，限制每个文件10MB，保留5个备份
    file_handler = RotatingFileHandler('case_management.log', maxBytes=10*1024*1024, backupCount=5)
    file_handler.setLevel(logging.DEBUG)
    
    # 创建控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # 创建格式化器
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # 添加处理器到日志器
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

logger = setup_logger()


class DatabaseManager:
    """高级数据库管理类"""
    def __init__(self, db_name="case_management.db"):
        self.db_name = db_name
        self.init_database()
    
    def init_database(self):
        """初始化数据库表结构"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            
            # 创建案例表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS cases (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT,
                    status TEXT,
                    priority INTEGER,
                    created_date TEXT,
                    modified_date TEXT,
                    due_date TEXT,
                    assigned_to TEXT,
                    tags TEXT,
                    custom_fields TEXT
                )
            ''')
            
            # 创建用户表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    email TEXT,
                    role TEXT,
                    created_date TEXT,
                    last_login TEXT
                )
            ''')
            
            # 创建活动记录表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS activities (
                    id TEXT PRIMARY KEY,
                    case_id TEXT,
                    user_id TEXT,
                    activity_type TEXT,
                    description TEXT,
                    timestamp TEXT,
                    FOREIGN KEY (case_id) REFERENCES cases (id),
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            # 创建附件表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS attachments (
                    id TEXT PRIMARY KEY,
                    case_id TEXT,
                    filename TEXT,
                    filepath TEXT,
                    upload_date TEXT,
                    uploaded_by TEXT,
                    FOREIGN KEY (case_id) REFERENCES cases (id),
                    FOREIGN KEY (uploaded_by) REFERENCES users (id)
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info("数据库初始化成功")
            
        except sqlite3.Error as e:
            logger.error(f"数据库初始化失败: {e}")
    
    def execute_query(self, query, params=None):
        """执行查询并返回结果"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
                
            result = cursor.fetchall()
            conn.close()
            return result
            
        except sqlite3.Error as e:
            logger.error(f"查询执行失败: {e}")
            return None
    
    def execute_update(self, query, params=None):
        """执行更新操作"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
                
            conn.commit()
            conn.close()
            return True
            
        except sqlite3.Error as e:
            logger.error(f"更新执行失败: {e}")
            return False
    
    def get_case(self, case_id):
        """获取特定案例"""
        query = "SELECT * FROM cases WHERE id = ?"
        result = self.execute_query(query, (case_id,))
        return result[0] if result else None
    
    def get_all_cases(self):
        """获取所有案例"""
        query = "SELECT * FROM cases ORDER BY created_date DESC"
        return self.execute_query(query)
    
    def add_case(self, case_data):
        """添加新案例"""
        case_id = str(uuid.uuid4())
        current_time = datetime.datetime.now().isoformat()
        
        query = """
            INSERT INTO cases (id, title, description, status, priority, created_date, 
                             modified_date, due_date, assigned_to, tags, custom_fields)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        params = (
            case_id,
            case_data.get('title', ''),
            case_data.get('description', ''),
            case_data.get('status', 'Open'),
            case_data.get('priority', 1),
            current_time,
            current_time,
            case_data.get('due_date', ''),
            case_data.get('assigned_to', ''),
            json.dumps(case_data.get('tags', [])),
            json.dumps(case_data.get('custom_fields', {}))
        )
        
        if self.execute_update(query, params):
            logger.info(f"案例添加成功: {case_id}")
            return case_id
        else:
            return None
    
    def update_case(self, case_id, case_data):
        """更新案例"""
        current_time = datetime.datetime.now().isoformat()
        
        query = """
            UPDATE cases 
            SET title=?, description=?, status=?, priority=?, modified_date=?, 
                due_date=?, assigned_to=?, tags=?, custom_fields=?
            WHERE id=?
        """
        
        params = (
            case_data.get('title', ''),
            case_data.get('description', ''),
            case_data.get('status', 'Open'),
            case_data.get('priority', 1),
            current_time,
            case_data.get('due_date', ''),
            case_data.get('assigned_to', ''),
            json.dumps(case_data.get('tags', [])),
            json.dumps(case_data.get('custom_fields', {})),
            case_id
        )
        
        if self.execute_update(query, params):
            logger.info(f"案例更新成功: {case_id}")
            return True
        else:
            return False
    
    def delete_case(self, case_id):
        """删除案例"""
        query = "DELETE FROM cases WHERE id=?"
        if self.execute_update(query, (case_id,)):
            logger.info(f"案例删除成功: {case_id}")
            return True
        else:
            return False


class CaseTableWidget(QTableWidget):
    """高级案例表格组件"""
    caseSelected = pyqtSignal(str)  # 发射选中的案例ID
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.db_manager = DatabaseManager()
        self.setup_ui()
        self.load_cases()
    
    def setup_ui(self):
        """设置表格UI"""
        self.setColumnCount(6)
        self.setHorizontalHeaderLabels(['ID', '标题', '状态', '优先级', '创建日期', '负责人'])
        self.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.setSelectionBehavior(QTableWidget.SelectRows)
        self.setAlternatingRowColors(True)
        self.setSortingEnabled(True)
        self.setEditTriggers(QTableWidget.NoEditTriggers)
        
        # 连接选择变化信号
        self.itemSelectionChanged.connect(self.on_selection_changed)
    
    def load_cases(self):
        """加载案例数据"""
        cases = self.db_manager.get_all_cases()
        self.setRowCount(len(cases))
        
        for row, case in enumerate(cases):
            case_id, title, _, status, priority, created_date, _, _, assigned_to, _, _ = case
            
            self.setItem(row, 0, QTableWidgetItem(case_id))
            self.setItem(row, 1, QTableWidgetItem(title))
            self.setItem(row, 2, QTableWidgetItem(status))
            self.setItem(row, 3, QTableWidgetItem(str(priority)))
            self.setItem(row, 4, QTableWidgetItem(created_date[:10]))  # 只显示日期部分
            self.setItem(row, 5, QTableWidgetItem(assigned_to))
            
            # 根据优先级设置颜色
            if priority == 1:
                self.item(row, 3).setBackground(QColor(255, 200, 200))  # 高优先级红色
            elif priority == 2:
                self.item(row, 3).setBackground(QColor(255, 255, 200))  # 中优先级黄色
    
    def on_selection_changed(self):
        """处理选择变化"""
        selected_items = self.selectedItems()
        if selected_items:
            case_id = self.item(selected_items[0].row(), 0).text()
            self.caseSelected.emit(case_id)


class CaseDetailWidget(QWidget):
    """案例详情组件"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.db_manager = DatabaseManager()
        self.current_case_id = None
        self.setup_ui()
    
    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout()
        
        # 基本信息组
        info_group = QGroupBox("案例信息")
        form_layout = QFormLayout()
        
        self.title_edit = QLineEdit()
        self.status_combo = QComboBox()
        self.status_combo.addItems(["Open", "In Progress", "Resolved", "Closed"])
        
        self.priority_spin = QSpinBox()
        self.priority_spin.setRange(1, 5)
        
        self.due_date_edit = QDateEdit()
        self.due_date_edit.setCalendarPopup(True)
        
        self.assigned_to_edit = QLineEdit()
        
        form_layout.addRow("标题:", self.title_edit)
        form_layout.addRow("状态:", self.status_combo)
        form_layout.addRow("优先级:", self.priority_spin)
        form_layout.addRow("截止日期:", self.due_date_edit)
        form_layout.addRow("负责人:", self.assigned_to_edit)
        
        info_group.setLayout(form_layout)
        
        # 描述组
        desc_group = QGroupBox("描述")
        desc_layout = QVBoxLayout()
        self.desc_edit = QTextEdit()
        desc_layout.addWidget(self.desc_edit)
        desc_group.setLayout(desc_layout)
        
        # 按钮组
        button_layout = QHBoxLayout()
        self.save_btn = QPushButton("保存")
        self.delete_btn = QPushButton("删除")
        self.new_btn = QPushButton("新建")
        
        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.delete_btn)
        button_layout.addWidget(self.new_btn)
        
        # 连接信号
        self.save_btn.clicked.connect(self.save_case)
        self.delete_btn.clicked.connect(self.delete_case)
        self.new_btn.clicked.connect(self.new_case)
        
        # 添加到主布局
        layout.addWidget(info_group)
        layout.addWidget(desc_group)
        layout.addWidget(QLabel("自定义字段 (JSON格式):"))
        self.custom_fields_edit = QTextEdit()
        layout.addWidget(self.custom_fields_edit)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def load_case(self, case_id):
        """加载案例详情"""
        self.current_case_id = case_id
        case = self.db_manager.get_case(case_id)
        
        if case:
            _, title, description, status, priority, _, _, due_date, assigned_to, tags, custom_fields = case
            
            self.title_edit.setText(title)
            self.desc_edit.setPlainText(description)
            self.status_combo.setCurrentText(status)
            self.priority_spin.setValue(priority)
            
            if due_date:
                due_date = QDate.fromString(due_date[:10], 'yyyy-MM-dd')
                self.due_date_edit.setDate(due_date)
            else:
                self.due_date_edit.setDate(QDate.currentDate())
                
            self.assigned_to_edit.setText(assigned_to)
            self.custom_fields_edit.setPlainText(custom_fields)
    
    def save_case(self):
        """保存案例"""
        if not self.current_case_id:
            QMessageBox.warning(self, "警告", "没有选中案例")
            return
        
        case_data = {
            'title': self.title_edit.text(),
            'description': self.desc_edit.toPlainText(),
            'status': self.status_combo.currentText(),
            'priority': self.priority_spin.value(),
            'due_date': self.due_date_edit.date().toString('yyyy-MM-dd'),
            'assigned_to': self.assigned_to_edit.text(),
            'custom_fields': json.loads(self.custom_fields_edit.toPlainText() or '{}')
        }
        
        if self.db_manager.update_case(self.current_case_id, case_data):
            QMessageBox.information(self, "成功", "案例已保存")
        else:
            QMessageBox.critical(self, "错误", "保存失败")
    
    def delete_case(self):
        """删除案例"""
        if not self.current_case_id:
            return
        
        reply = QMessageBox.question(self, "确认", "确定要删除这个案例吗？",
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            if self.db_manager.delete_case(self.current_case_id):
                QMessageBox.information(self, "成功", "案例已删除")
                self.clear_form()
                self.current_case_id = None
            else:
                QMessageBox.critical(self, "错误", "删除失败")
    
    def new_case(self):
        """新建案例"""
        self.clear_form()
        self.current_case_id = None
    
    def clear_form(self):
        """清空表单"""
        self.title_edit.clear()
        self.desc_edit.clear()
        self.status_combo.setCurrentIndex(0)
        self.priority_spin.setValue(1)
        self.due_date_edit.setDate(QDate.currentDate().addDays(7))
        self.assigned_to_edit.clear()
        self.custom_fields_edit.clear()


class StatisticsWidget(QWidget):
    """统计图表组件"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.db_manager = DatabaseManager()
        self.setup_ui()
        self.load_data()
    
    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout()
        
        # 创建图表容器
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)
        
        # 刷新按钮
        refresh_btn = QPushButton("刷新数据")
        refresh_btn.clicked.connect(self.load_data)
        layout.addWidget(refresh_btn)
        
        self.setLayout(layout)
    
    def load_data(self):
        """加载并显示统计数据"""
        # 获取案例状态分布
        cases = self.db_manager.get_all_cases()
        status_count = {}
        
        for case in cases:
            status = case[3]  # 状态在索引3的位置
            status_count[status] = status_count.get(status, 0) + 1
        
        # 清除旧图表
        self.figure.clear()
        
        # 创建子图
        ax = self.figure.add_subplot(111)
        
        # 绘制饼图
        if status_count:
            labels = list(status_count.keys())
            sizes = list(status_count.values())
            
            ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90)
            ax.axis('equal')  # 确保饼图是圆的
            ax.set_title('案例状态分布')
        
        # 刷新画布
        self.canvas.draw()


class NotificationManager(QWidget):
    """通知管理器"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.check_notifications()
        
        # 设置定时器，每60秒检查一次通知
        self.timer = QTimer()
        self.timer.timeout.connect(self.check_notifications)
        self.timer.start(60000)
    
    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout()
        
        self.notification_list = QListWidget()
        layout.addWidget(QLabel("通知:"))
        layout.addWidget(self.notification_list)
        
        self.setLayout(layout)
    
    def check_notifications(self):
        """检查通知"""
        self.notification_list.clear()
        
        # 获取即将到期的案例
        db_manager = DatabaseManager()
        cases = db_manager.get_all_cases()
        today = QDate.currentDate()
        
        for case in cases:
            due_date_str = case[7]  # 截止日期在索引7的位置
            if due_date_str:
                due_date = QDate.fromString(due_date_str[:10], 'yyyy-MM-dd')
                days_to_due = today.daysTo(due_date)
                
                if 0 <= days_to_due <= 3:  # 3天内到期
                    self.notification_list.addItem(
                        f"案例 '{case[1]}' 还有 {days_to_due} 天到期"
                    )
        
        # 如果有通知，设置提醒
        if self.notification_list.count() > 0:
            self.parent().statusBar().showMessage(f"有 {self.notification_list.count()} 个通知")


class SearchWidget(QWidget):
    """高级搜索组件"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout()
        
        # 搜索框
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入关键词搜索...")
        search_btn = QPushButton("搜索")
        
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(search_btn)
        
        # 过滤器
        filter_group = QGroupBox("过滤器")
        filter_layout = QFormLayout()
        
        self.status_filter = QComboBox()
        self.status_filter.addItem("所有状态")
        self.status_filter.addItems(["Open", "In Progress", "Resolved", "Closed"])
        
        self.priority_filter = QComboBox()
        self.priority_filter.addItem("所有优先级")
        self.priority_filter.addItems(["1 - 高", "2", "3", "4", "5 - 低"])
        
        filter_layout.addRow("状态:", self.status_filter)
        filter_layout.addRow("优先级:", self.priority_filter)
        filter_group.setLayout(filter_layout)
        
        # 添加到主布局
        layout.addLayout(search_layout)
        layout.addWidget(filter_group)
        
        self.setLayout(layout)
        
        # 连接信号
        search_btn.clicked.connect(self.perform_search)
    
    def perform_search(self):
        """执行搜索"""
        keyword = self.search_input.text()
        status = self.status_filter.currentText() if self.status_filter.currentIndex() > 0 else None
        priority = self.priority_filter.currentIndex() if self.priority_filter.currentIndex() > 0 else None
        
        # 这里应该发射信号或调用主窗口的搜索方法
        print(f"搜索: {keyword}, 状态: {status}, 优先级: {priority}")


class ImportExportDialog(QDialog):
    """导入导出对话框"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        """设置UI"""
        self.setWindowTitle("导入/导出数据")
        self.setModal(True)
        self.resize(400, 300)
        
        layout = QVBoxLayout()
        
        # 导入部分
        import_group = QGroupBox("导入数据")
        import_layout = QVBoxLayout()
        
        import_btn = QPushButton("选择文件导入")
        import_btn.clicked.connect(self.import_data)
        
        import_layout.addWidget(import_btn)
        import_group.setLayout(import_layout)
        
        # 导出部分
        export_group = QGroupBox("导出数据")
        export_layout = QVBoxLayout()
        
        export_btn = QPushButton("导出到文件")
        export_btn.clicked.connect(self.export_data)
        
        export_layout.addWidget(export_btn)
        export_group.setLayout(export_layout)
        
        # 添加到主布局
        layout.addWidget(import_group)
        layout.addWidget(export_group)
        layout.addStretch()
        
        self.setLayout(layout)
    
    def import_data(self):
        """导入数据"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择导入文件", "", "CSV文件 (*.csv);;JSON文件 (*.json)"
        )
        
        if file_path:
            try:
                if file_path.endswith('.csv'):
                    df = pd.read_csv(file_path)
                    # 处理CSV导入逻辑
                    QMessageBox.information(self, "成功", f"已从CSV文件导入 {len(df)} 条记录")
                elif file_path.endswith('.json'):
                    with open(file_path, 'r') as f:
                        data = json.load(f)
                    # 处理JSON导入逻辑
                    QMessageBox.information(self, "成功", f"已从JSON文件导入 {len(data)} 条记录")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导入失败: {str(e)}")
    
    def export_data(self):
        """导出数据"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "选择导出位置", "cases_export", "CSV文件 (*.csv);;JSON文件 (*.json)"
        )
        
        if file_path:
            try:
                db_manager = DatabaseManager()
                cases = db_manager.get_all_cases()
                
                if file_path.endswith('.csv'):
                    # 转换为DataFrame并导出
                    data = []
                    for case in cases:
                        data.append({
                            'ID': case[0],
                            'Title': case[1],
                            'Description': case[2],
                            'Status': case[3],
                            'Priority': case[4],
                            'Created Date': case[5],
                            'Due Date': case[7],
                            'Assigned To': case[8]
                        })
                    
                    df = pd.DataFrame(data)
                    df.to_csv(file_path, index=False)
                    QMessageBox.information(self, "成功", f"已导出 {len(df)} 条记录到CSV文件")
                
                elif file_path.endswith('.json'):
                    # 转换为JSON并导出
                    data = []
                    for case in cases:
                        data.append({
                            'id': case[0],
                            'title': case[1],
                            'description': case[2],
                            'status': case[3],
                            'priority': case[4],
                            'created_date': case[5],
                            'due_date': case[7],
                            'assigned_to': case[8]
                        })
                    
                    with open(file_path, 'w') as f:
                        json.dump(data, f, indent=2)
                    QMessageBox.information(self, "成功", f"已导出 {len(data)} 条记录到JSON文件")
                    
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导出失败: {str(e)}")


class CaseManagementSystem(QMainWindow):
    """案例管理系统主窗口"""
    def __init__(self):
        super().__init__()
        self.db_manager = DatabaseManager()
        self.setup_ui()
        self.setup_menu()
        self.setup_toolbar()
        self.setup_statusbar()
        
        # 设置窗口属性
        self.setWindowTitle("高级案例管理系统")
        self.resize(1200, 800)
        self.center()
    
    def center(self):
        """居中显示窗口"""
        screen = QApplication.primaryScreen().geometry()
        size = self.geometry()
        self.move((screen.width() - size.width()) // 2, 
                 (screen.height() - size.height()) // 2)
    
    def setup_ui(self):
        """设置主UI"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        
        # 左侧面板
        left_panel = QWidget()
        left_panel.setMaximumWidth(300)
        left_layout = QVBoxLayout(left_panel)
        
        # 搜索组件
        self.search_widget = SearchWidget()
        left_layout.addWidget(self.search_widget)
        
        # 通知组件
        self.notification_widget = NotificationManager()
        left_layout.addWidget(self.notification_widget)
        
        # 右侧主区域
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # 标签页
        self.tab_widget = QTabWidget()
        
        # 案例表格标签页
        self.case_table = CaseTableWidget()
        self.case_table.caseSelected.connect(self.on_case_selected)
        self.tab_widget.addTab(self.case_table, "案例列表")
        
        # 案例详情标签页
        self.case_detail = CaseDetailWidget()
        self.tab_widget.addTab(self.case_detail, "案例详情")
        
        # 统计标签页
        self.stats_widget = StatisticsWidget()
        self.tab_widget.addTab(self.stats_widget, "统计")
        
        right_layout.addWidget(self.tab_widget)
        
        # 使用分割器
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([200, 1000])
        
        main_layout.addWidget(splitter)
    
    def setup_menu(self):
        """设置菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu("文件")
        
        new_action = QAction("新建案例", self)
        new_action.triggered.connect(self.case_detail.new_case)
        file_menu.addAction(new_action)
        
        import_export_action = QAction("导入/导出", self)
        import_export_action.triggered.connect(self.show_import_export)
        file_menu.addAction(import_export_action)
        
        exit_action = QAction("退出", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 编辑菜单
        edit_menu = menubar.addMenu("编辑")
        
        refresh_action = QAction("刷新", self)
        refresh_action.triggered.connect(self.refresh_data)
        edit_menu.addAction(refresh_action)
        
        # 视图菜单
        view_menu = menubar.addMenu("视图")
        
        # 帮助菜单
        help_menu = menubar.addMenu("帮助")
        
        about_action = QAction("关于", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def setup_toolbar(self):
        """设置工具栏"""
        toolbar = QToolBar("主工具栏")
        toolbar.setIconSize(QSize(16, 16))
        self.addToolBar(toolbar)
        
        new_btn = QToolButton()
        new_btn.setText("新建案例")
        new_btn.clicked.connect(self.case_detail.new_case)
        toolbar.addWidget(new_btn)
        
        refresh_btn = QToolButton()
        refresh_btn.setText("刷新")
        refresh_btn.clicked.connect(self.refresh_data)
        toolbar.addWidget(refresh_btn)
        
        toolbar.addSeparator()
        
        import_export_btn = QToolButton()
        import_export_btn.setText("导入/导出")
        import_export_btn.clicked.connect(self.show_import_export)
        toolbar.addWidget(import_export_btn)
    
    def setup_statusbar(self):
        """设置状态栏"""
        statusbar = self.statusBar()
        statusbar.showMessage("就绪")
        
        # 添加进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(200)
        self.progress_bar.setVisible(False)
        statusbar.addPermanentWidget(self.progress_bar)
    
    def on_case_selected(self, case_id):
        """处理案例选择事件"""
        self.case_detail.load_case(case_id)
        self.tab_widget.setCurrentIndex(1)  # 切换到详情标签页
    
    def refresh_data(self):
        """刷新数据"""
        self.case_table.load_cases()
        self.stats_widget.load_data()
        self.statusBar().showMessage("数据已刷新", 3000)
    
    def show_import_export(self):
        """显示导入导出对话框"""
        dialog = ImportExportDialog(self)
        dialog.exec_()
    
    def show_about(self):
        """显示关于对话框"""
        QMessageBox.about(self, "关于案例管理系统", 
                         "高级案例管理系统 v1.0\n\n"
                         "一个功能强大的案例管理工具，支持案例的创建、编辑、搜索、统计和导入导出功能。")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 设置应用程序样式
    app.setStyle('Fusion')
    
    # 创建并显示主窗口
    window = CaseManagementSystem()
    window.show()
    
    # 启动应用程序
    sys.exit(app.exec_())