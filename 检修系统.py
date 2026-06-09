import sys
import os
import json
import datetime
import sqlite3
from typing import Dict, List, Optional, Any

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QGridLayout, QTabWidget, QTableWidget,
                             QTableWidgetItem, QTreeWidget, QTreeWidgetItem,
                             QPushButton, QLabel, QLineEdit, QTextEdit, 
                             QComboBox, QDateEdit, QSpinBox, QDoubleSpinBox,
                             QCheckBox, QGroupBox, QProgressBar, QMessageBox,
                             QFileDialog, QSplitter, QHeaderView, QMenu, 
                             QAction, QToolBar, QStatusBar, QDialog, 
                             QDialogButtonBox, QFormLayout, QListWidget,
                             QListWidgetItem, QCalendarWidget)
from PyQt5.QtCore import Qt, QTimer, QDate, QDateTime, pyqtSignal, QThread, pyqtSlot
from PyQt5.QtGui import QIcon, QFont, QPalette, QColor, QPixmap, QPainter
import matplotlib
matplotlib.rc("font", family='Microsoft YaHei')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import numpy as np
import pandas as pd


class DatabaseManager:
    """数据库管理类"""
    
    def __init__(self, db_path="maintenance_system.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """初始化数据库表结构"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 设备表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS equipment (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                type TEXT,
                model TEXT,
                location TEXT,
                status TEXT DEFAULT '正常',
                last_maintenance DATE,
                next_maintenance DATE,
                maintenance_interval INTEGER DEFAULT 30,
                notes TEXT
            )
        ''')
        
        # 检修任务表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS maintenance_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                equipment_id INTEGER,
                task_name TEXT NOT NULL,
                priority TEXT DEFAULT '中等',
                status TEXT DEFAULT '待处理',
                assigned_to TEXT,
                scheduled_date DATE,
                completed_date DATE,
                description TEXT,
                FOREIGN KEY (equipment_id) REFERENCES equipment (id)
            )
        ''')
        
        # 检修记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS maintenance_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                equipment_id INTEGER,
                maintenance_date DATE,
                technician TEXT,
                work_description TEXT,
                parts_replaced TEXT,
                cost REAL,
                notes TEXT,
                FOREIGN KEY (equipment_id) REFERENCES equipment (id)
            )
        ''')
        
        # 备件库存表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS spare_parts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                part_name TEXT NOT NULL,
                part_number TEXT,
                category TEXT,
                quantity INTEGER DEFAULT 0,
                min_quantity INTEGER DEFAULT 5,
                supplier TEXT,
                price REAL,
                location TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def execute_query(self, query, params=None):
        """执行查询并返回结果"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        
        # 如果是SELECT查询，返回结果
        if query.strip().upper().startswith('SELECT'):
            result = cursor.fetchall()
        else:
            conn.commit()
            result = cursor.lastrowid
        
        conn.close()
        return result
    
    def get_equipment_list(self):
        """获取设备列表"""
        return self.execute_query("SELECT * FROM equipment ORDER BY name")
    
    def get_maintenance_tasks(self, status_filter=None):
        """获取检修任务列表"""
        if status_filter:
            return self.execute_query(
                "SELECT * FROM maintenance_tasks WHERE status = ? ORDER BY scheduled_date", 
                (status_filter,)
            )
        else:
            return self.execute_query("SELECT * FROM maintenance_tasks ORDER BY scheduled_date")
    
    def get_maintenance_records(self, equipment_id=None):
        """获取检修记录"""
        if equipment_id:
            return self.execute_query(
                "SELECT * FROM maintenance_records WHERE equipment_id = ? ORDER BY maintenance_date DESC",
                (equipment_id,)
            )
        else:
            return self.execute_query("SELECT * FROM maintenance_records ORDER BY maintenance_date DESC")
    
    def get_spare_parts(self, low_stock_only=False):
        """获取备件列表"""
        if low_stock_only:
            return self.execute_query(
                "SELECT * FROM spare_parts WHERE quantity <= min_quantity ORDER BY quantity"
            )
        else:
            return self.execute_query("SELECT * FROM spare_parts ORDER BY part_name")


class EquipmentWidget(QWidget):
    """设备管理组件"""
    
    equipment_selected = pyqtSignal(int)  # 设备选择信号
    
    def __init__(self, db_manager):
        super().__init__()
        self.db_manager = db_manager
        self.init_ui()
        self.load_equipment()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 工具栏
        toolbar = QHBoxLayout()
        self.add_btn = QPushButton("添加设备")
        self.edit_btn = QPushButton("编辑设备")
        self.delete_btn = QPushButton("删除设备")
        self.refresh_btn = QPushButton("刷新")
        
        toolbar.addWidget(self.add_btn)
        toolbar.addWidget(self.edit_btn)
        toolbar.addWidget(self.delete_btn)
        toolbar.addWidget(self.refresh_btn)
        toolbar.addStretch()
        
        # 搜索框
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("搜索设备...")
        toolbar.addWidget(QLabel("搜索:"))
        toolbar.addWidget(self.search_box)
        
        layout.addLayout(toolbar)
        
        # 设备表格
        self.equipment_table = QTableWidget()
        self.equipment_table.setColumnCount(8)
        self.equipment_table.setHorizontalHeaderLabels([
            "ID", "名称", "类型", "型号", "位置", "状态", "上次检修", "下次检修"
        ])
        self.equipment_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.equipment_table.doubleClicked.connect(self.on_equipment_double_click)
        
        layout.addWidget(self.equipment_table)
        
        # 连接信号
        self.add_btn.clicked.connect(self.add_equipment)
        self.edit_btn.clicked.connect(self.edit_equipment)
        self.delete_btn.clicked.connect(self.delete_equipment)
        self.refresh_btn.clicked.connect(self.load_equipment)
        self.search_box.textChanged.connect(self.filter_equipment)
        
        self.setLayout(layout)
    
    def load_equipment(self):
        """加载设备数据"""
        equipment = self.db_manager.get_equipment_list()
        self.equipment_table.setRowCount(len(equipment))
        
        for row, eq in enumerate(equipment):
            for col, value in enumerate(eq):
                item = QTableWidgetItem(str(value) if value is not None else "")
                self.equipment_table.setItem(row, col, item)
    
    def filter_equipment(self):
        """过滤设备"""
        search_text = self.search_box.text().lower()
        for row in range(self.equipment_table.rowCount()):
            match = False
            for col in range(self.equipment_table.columnCount()):
                item = self.equipment_table.item(row, col)
                if item and search_text in item.text().lower():
                    match = True
                    break
            self.equipment_table.setRowHidden(row, not match)
    
    def on_equipment_double_click(self, index):
        """设备双击事件"""
        row = index.row()
        equipment_id = int(self.equipment_table.item(row, 0).text())
        self.equipment_selected.emit(equipment_id)
    
    def add_equipment(self):
        """添加设备"""
        dialog = EquipmentDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            self.load_equipment()
    
    def edit_equipment(self):
        """编辑设备"""
        selected = self.equipment_table.selectedItems()
        if not selected:
            QMessageBox.warning(self, "警告", "请先选择要编辑的设备")
            return
        
        row = selected[0].row()
        equipment_id = int(self.equipment_table.item(row, 0).text())
        
        # 获取设备数据
        equipment_data = self.db_manager.execute_query(
            "SELECT * FROM equipment WHERE id = ?", (equipment_id,)
        )[0]
        
        dialog = EquipmentDialog(self, equipment_data)
        if dialog.exec_() == QDialog.Accepted:
            self.load_equipment()
    
    def delete_equipment(self):
        """删除设备"""
        selected = self.equipment_table.selectedItems()
        if not selected:
            QMessageBox.warning(self, "警告", "请先选择要删除的设备")
            return
        
        row = selected[0].row()
        equipment_id = int(self.equipment_table.item(row, 0).text())
        equipment_name = self.equipment_table.item(row, 1).text()
        
        reply = QMessageBox.question(
            self, "确认删除", 
            f"确定要删除设备 '{equipment_name}' 吗？",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.db_manager.execute_query(
                "DELETE FROM equipment WHERE id = ?", (equipment_id,)
            )
            self.load_equipment()


class EquipmentDialog(QDialog):
    """设备编辑对话框"""
    
    def __init__(self, parent, equipment_data=None):
        super().__init__(parent)
        self.equipment_data = equipment_data
        self.db_manager = parent.db_manager
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("设备信息")
        self.setModal(True)
        self.resize(400, 300)
        
        layout = QFormLayout()
        
        self.name_edit = QLineEdit()
        self.type_edit = QLineEdit()
        self.model_edit = QLineEdit()
        self.location_edit = QLineEdit()
        self.status_combo = QComboBox()
        self.status_combo.addItems(["正常", "检修中", "故障", "停用"])
        
        self.last_maintenance_edit = QDateEdit()
        self.last_maintenance_edit.setCalendarPopup(True)
        self.next_maintenance_edit = QDateEdit()
        self.next_maintenance_edit.setCalendarPopup(True)
        
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(1, 365)
        self.interval_spin.setSuffix(" 天")
        
        self.notes_edit = QTextEdit()
        self.notes_edit.setMaximumHeight(100)
        
        layout.addRow("设备名称:", self.name_edit)
        layout.addRow("设备类型:", self.type_edit)
        layout.addRow("设备型号:", self.model_edit)
        layout.addRow("安装位置:", self.location_edit)
        layout.addRow("设备状态:", self.status_combo)
        layout.addRow("上次检修:", self.last_maintenance_edit)
        layout.addRow("检修间隔:", self.interval_spin)
        layout.addRow("下次检修:", self.next_maintenance_edit)
        layout.addRow("备注:", self.notes_edit)
        
        # 按钮
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        
        layout.addRow(button_box)
        
        self.setLayout(layout)
        
        # 如果是编辑模式，填充数据
        if self.equipment_data:
            self.fill_data()
    
    def fill_data(self):
        """填充设备数据"""
        eq = self.equipment_data
        self.name_edit.setText(eq[1] or "")
        self.type_edit.setText(eq[2] or "")
        self.model_edit.setText(eq[3] or "")
        self.location_edit.setText(eq[4] or "")
        self.status_combo.setCurrentText(eq[5] or "正常")
        
        if eq[6]:
            self.last_maintenance_edit.setDate(QDate.fromString(eq[6], "yyyy-MM-dd"))
        else:
            self.last_maintenance_edit.setDate(QDate.currentDate())
            
        self.interval_spin.setValue(eq[8] or 30)
        
        if eq[7]:
            self.next_maintenance_edit.setDate(QDate.fromString(eq[7], "yyyy-MM-dd"))
        else:
            next_date = QDate.currentDate().addDays(self.interval_spin.value())
            self.next_maintenance_edit.setDate(next_date)
            
        self.notes_edit.setPlainText(eq[9] or "")
    
    def accept(self):
        """保存设备信息"""
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "警告", "设备名称不能为空")
            return
        
        # 准备数据
        data = {
            'name': name,
            'type': self.type_edit.text().strip(),
            'model': self.model_edit.text().strip(),
            'location': self.location_edit.text().strip(),
            'status': self.status_combo.currentText(),
            'last_maintenance': self.last_maintenance_edit.date().toString("yyyy-MM-dd"),
            'next_maintenance': self.next_maintenance_edit.date().toString("yyyy-MM-dd"),
            'maintenance_interval': self.interval_spin.value(),
            'notes': self.notes_edit.toPlainText().strip()
        }
        
        # 保存到数据库
        if self.equipment_data:
            # 更新现有设备
            query = """
                UPDATE equipment 
                SET name=?, type=?, model=?, location=?, status=?, 
                    last_maintenance=?, next_maintenance=?, maintenance_interval=?, notes=?
                WHERE id=?
            """
            params = (
                data['name'], data['type'], data['model'], data['location'], data['status'],
                data['last_maintenance'], data['next_maintenance'], data['maintenance_interval'],
                data['notes'], self.equipment_data[0]
            )
        else:
            # 添加新设备
            query = """
                INSERT INTO equipment 
                (name, type, model, location, status, last_maintenance, next_maintenance, maintenance_interval, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            params = (
                data['name'], data['type'], data['model'], data['location'], data['status'],
                data['last_maintenance'], data['next_maintenance'], data['maintenance_interval'],
                data['notes']
            )
        
        self.db_manager.execute_query(query, params)
        super().accept()


class MaintenanceTaskWidget(QWidget):
    """检修任务管理组件"""
    
    def __init__(self, db_manager):
        super().__init__()
        self.db_manager = db_manager
        self.init_ui()
        self.load_tasks()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 工具栏
        toolbar = QHBoxLayout()
        self.add_btn = QPushButton("添加任务")
        self.edit_btn = QPushButton("编辑任务")
        self.complete_btn = QPushButton("标记完成")
        self.delete_btn = QPushButton("删除任务")
        self.refresh_btn = QPushButton("刷新")
        
        toolbar.addWidget(self.add_btn)
        toolbar.addWidget(self.edit_btn)
        toolbar.addWidget(self.complete_btn)
        toolbar.addWidget(self.delete_btn)
        toolbar.addWidget(self.refresh_btn)
        toolbar.addStretch()
        
        # 状态筛选
        self.status_filter = QComboBox()
        self.status_filter.addItems(["全部", "待处理", "进行中", "已完成", "已取消"])
        toolbar.addWidget(QLabel("状态筛选:"))
        toolbar.addWidget(self.status_filter)
        
        layout.addLayout(toolbar)
        
        # 任务表格
        self.task_table = QTableWidget()
        self.task_table.setColumnCount(8)
        self.task_table.setHorizontalHeaderLabels([
            "ID", "设备", "任务名称", "优先级", "状态", "负责人", "计划日期", "完成日期"
        ])
        self.task_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        layout.addWidget(self.task_table)
        
        # 连接信号
        self.add_btn.clicked.connect(self.add_task)
        self.edit_btn.clicked.connect(self.edit_task)
        self.complete_btn.clicked.connect(self.complete_task)
        self.delete_btn.clicked.connect(self.delete_task)
        self.refresh_btn.clicked.connect(self.load_tasks)
        self.status_filter.currentTextChanged.connect(self.load_tasks)
        
        self.setLayout(layout)
    
    def load_tasks(self):
        """加载任务数据"""
        status_filter = self.status_filter.currentText()
        if status_filter == "全部":
            tasks = self.db_manager.get_maintenance_tasks()
        else:
            tasks = self.db_manager.get_maintenance_tasks(status_filter)
        
        self.task_table.setRowCount(len(tasks))
        
        for row, task in enumerate(tasks):
            # 获取设备名称
            equipment = self.db_manager.execute_query(
                "SELECT name FROM equipment WHERE id = ?", (task[1],)
            )
            equipment_name = equipment[0][0] if equipment else "未知设备"
            
            # 填充表格
            data = [task[0], equipment_name] + list(task[2:])
            for col, value in enumerate(data):
                item = QTableWidgetItem(str(value) if value is not None else "")
                self.task_table.setItem(row, col, item)
                
                # 根据状态设置颜色
                if col == 4:  # 状态列
                    if value == "已完成":
                        item.setBackground(QColor(200, 255, 200))
                    elif value == "进行中":
                        item.setBackground(QColor(255, 255, 200))
                    elif value == "待处理":
                        item.setBackground(QColor(255, 200, 200))
    
    def add_task(self):
        """添加任务"""
        dialog = MaintenanceTaskDialog(self.db_manager, self)
        if dialog.exec_() == QDialog.Accepted:
            self.load_tasks()
    
    def edit_task(self):
        """编辑任务"""
        selected = self.task_table.selectedItems()
        if not selected:
            QMessageBox.warning(self, "警告", "请先选择要编辑的任务")
            return
        
        row = selected[0].row()
        task_id = int(self.task_table.item(row, 0).text())
        
        # 获取任务数据
        task_data = self.db_manager.execute_query(
            "SELECT * FROM maintenance_tasks WHERE id = ?", (task_id,)
        )[0]
        
        dialog = MaintenanceTaskDialog(self.db_manager, self, task_data)
        if dialog.exec_() == QDialog.Accepted:
            self.load_tasks()
    
    def complete_task(self):
        """标记任务完成"""
        selected = self.task_table.selectedItems()
        if not selected:
            QMessageBox.warning(self, "警告", "请先选择要完成的任务")
            return
        
        row = selected[0].row()
        task_id = int(self.task_table.item(row, 0).text())
        task_name = self.task_table.item(row, 2).text()
        
        reply = QMessageBox.question(
            self, "确认完成", 
            f"确定要将任务 '{task_name}' 标记为已完成吗？",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.db_manager.execute_query(
                "UPDATE maintenance_tasks SET status = '已完成', completed_date = ? WHERE id = ?",
                (QDate.currentDate().toString("yyyy-MM-dd"), task_id)
            )
            self.load_tasks()
    
    def delete_task(self):
        """删除任务"""
        selected = self.task_table.selectedItems()
        if not selected:
            QMessageBox.warning(self, "警告", "请先选择要删除的任务")
            return
        
        row = selected[0].row()
        task_id = int(self.task_table.item(row, 0).text())
        task_name = self.task_table.item(row, 2).text()
        
        reply = QMessageBox.question(
            self, "确认删除", 
            f"确定要删除任务 '{task_name}' 吗？",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.db_manager.execute_query(
                "DELETE FROM maintenance_tasks WHERE id = ?", (task_id,)
            )
            self.load_tasks()


class MaintenanceTaskDialog(QDialog):
    """检修任务编辑对话框"""
    
    def __init__(self, db_manager, parent, task_data=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.task_data = task_data
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("检修任务")
        self.setModal(True)
        self.resize(500, 400)
        
        layout = QFormLayout()
        
        # 设备选择
        self.equipment_combo = QComboBox()
        self.load_equipment()
        
        self.task_name_edit = QLineEdit()
        self.priority_combo = QComboBox()
        self.priority_combo.addItems(["低", "中等", "高", "紧急"])
        
        self.status_combo = QComboBox()
        self.status_combo.addItems(["待处理", "进行中", "已完成", "已取消"])
        
        self.assigned_to_edit = QLineEdit()
        self.scheduled_date_edit = QDateEdit()
        self.scheduled_date_edit.setCalendarPopup(True)
        self.scheduled_date_edit.setDate(QDate.currentDate())
        
        self.completed_date_edit = QDateEdit()
        self.completed_date_edit.setCalendarPopup(True)
        self.completed_date_edit.setDate(QDate.currentDate())
        
        self.description_edit = QTextEdit()
        self.description_edit.setMaximumHeight(150)
        
        layout.addRow("设备:", self.equipment_combo)
        layout.addRow("任务名称:", self.task_name_edit)
        layout.addRow("优先级:", self.priority_combo)
        layout.addRow("状态:", self.status_combo)
        layout.addRow("负责人:", self.assigned_to_edit)
        layout.addRow("计划日期:", self.scheduled_date_edit)
        layout.addRow("完成日期:", self.completed_date_edit)
        layout.addRow("任务描述:", self.description_edit)
        
        # 按钮
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        
        layout.addRow(button_box)
        
        self.setLayout(layout)
        
        # 如果是编辑模式，填充数据
        if self.task_data:
            self.fill_data()
    
    def load_equipment(self):
        """加载设备列表"""
        equipment = self.db_manager.get_equipment_list()
        self.equipment_combo.clear()
        
        for eq in equipment:
            self.equipment_combo.addItem(f"{eq[1]} ({eq[2]})", eq[0])
    
    def fill_data(self):
        """填充任务数据"""
        task = self.task_data
        
        # 设置设备
        index = self.equipment_combo.findData(task[1])
        if index >= 0:
            self.equipment_combo.setCurrentIndex(index)
        
        self.task_name_edit.setText(task[2] or "")
        self.priority_combo.setCurrentText(task[3] or "中等")
        self.status_combo.setCurrentText(task[4] or "待处理")
        self.assigned_to_edit.setText(task[5] or "")
        
        if task[6]:
            self.scheduled_date_edit.setDate(QDate.fromString(task[6], "yyyy-MM-dd"))
        
        if task[7]:
            self.completed_date_edit.setDate(QDate.fromString(task[7], "yyyy-MM-dd"))
        
        self.description_edit.setPlainText(task[8] or "")
    
    def accept(self):
        """保存任务信息"""
        task_name = self.task_name_edit.text().strip()
        if not task_name:
            QMessageBox.warning(self, "警告", "任务名称不能为空")
            return
        
        equipment_id = self.equipment_combo.currentData()
        if not equipment_id:
            QMessageBox.warning(self, "警告", "请选择设备")
            return
        
        # 准备数据
        data = {
            'equipment_id': equipment_id,
            'task_name': task_name,
            'priority': self.priority_combo.currentText(),
            'status': self.status_combo.currentText(),
            'assigned_to': self.assigned_to_edit.text().strip(),
            'scheduled_date': self.scheduled_date_edit.date().toString("yyyy-MM-dd"),
            'completed_date': self.completed_date_edit.date().toString("yyyy-MM-dd") if self.status_combo.currentText() == "已完成" else None,
            'description': self.description_edit.toPlainText().strip()
        }
        
        # 保存到数据库
        if self.task_data:
            # 更新现有任务
            if data['status'] == "已完成" and not data['completed_date']:
                data['completed_date'] = QDate.currentDate().toString("yyyy-MM-dd")
            
            query = """
                UPDATE maintenance_tasks 
                SET equipment_id=?, task_name=?, priority=?, status=?, assigned_to=?, 
                    scheduled_date=?, completed_date=?, description=?
                WHERE id=?
            """
            params = (
                data['equipment_id'], data['task_name'], data['priority'], data['status'],
                data['assigned_to'], data['scheduled_date'], data['completed_date'],
                data['description'], self.task_data[0]
            )
        else:
            # 添加新任务
            query = """
                INSERT INTO maintenance_tasks 
                (equipment_id, task_name, priority, status, assigned_to, scheduled_date, completed_date, description)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """
            params = (
                data['equipment_id'], data['task_name'], data['priority'], data['status'],
                data['assigned_to'], data['scheduled_date'], data['completed_date'],
                data['description']
            )
        
        self.db_manager.execute_query(query, params)
        super().accept()


class DashboardWidget(QWidget):
    """仪表板组件"""
    
    def __init__(self, db_manager):
        super().__init__()
        self.db_manager = db_manager
        self.init_ui()
        self.load_data()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 标题
        title = QLabel("检修系统仪表板")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        layout.addWidget(title)
        
        # 统计信息
        stats_layout = QHBoxLayout()
        
        self.equipment_count_label = QLabel("0")
        self.equipment_count_label.setFont(QFont("Arial", 24, QFont.Bold))
        self.equipment_count_label.setAlignment(Qt.AlignCenter)
        equipment_box = self.create_stat_box("设备总数", self.equipment_count_label)
        
        self.pending_tasks_label = QLabel("0")
        self.pending_tasks_label.setFont(QFont("Arial", 24, QFont.Bold))
        self.pending_tasks_label.setAlignment(Qt.AlignCenter)
        tasks_box = self.create_stat_box("待处理任务", self.pending_tasks_label)
        
        self.overdue_tasks_label = QLabel("0")
        self.overdue_tasks_label.setFont(QFont("Arial", 24, QFont.Bold))
        self.overdue_tasks_label.setAlignment(Qt.AlignCenter)
        overdue_box = self.create_stat_box("逾期任务", self.overdue_tasks_label)
        
        self.low_stock_label = QLabel("0")
        self.low_stock_label.setFont(QFont("Arial", 24, QFont.Bold))
        self.low_stock_label.setAlignment(Qt.AlignCenter)
        stock_box = self.create_stat_box("低库存备件", self.low_stock_label)
        
        stats_layout.addWidget(equipment_box)
        stats_layout.addWidget(tasks_box)
        stats_layout.addWidget(overdue_box)
        stats_layout.addWidget(stock_box)
        
        layout.addLayout(stats_layout)
        
        # 图表区域
        tab_widget = QTabWidget()
        
        # 任务状态图表
        self.task_chart = MatplotlibWidget()
        tab_widget.addTab(self.task_chart, "任务状态")
        
        # 设备状态图表
        self.equipment_chart = MatplotlibWidget()
        tab_widget.addTab(self.equipment_chart, "设备状态")
        
        layout.addWidget(tab_widget)
        
        self.setLayout(layout)
    
    def create_stat_box(self, title, value_label):
        """创建统计信息框"""
        box = QGroupBox(title)
        layout = QVBoxLayout()
        layout.addWidget(value_label)
        box.setLayout(layout)
        return box
    
    def load_data(self):
        """加载数据并更新界面"""
        # 统计信息
        equipment_count = len(self.db_manager.get_equipment_list())
        pending_tasks = len(self.db_manager.get_maintenance_tasks("待处理"))
        
        # 计算逾期任务
        today = QDate.currentDate().toString("yyyy-MM-dd")
        overdue_tasks = self.db_manager.execute_query(
            "SELECT COUNT(*) FROM maintenance_tasks WHERE status != '已完成' AND scheduled_date < ?",
            (today,)
        )[0][0]
        
        low_stock_parts = len(self.db_manager.get_spare_parts(low_stock_only=True))
        
        self.equipment_count_label.setText(str(equipment_count))
        self.pending_tasks_label.setText(str(pending_tasks))
        self.overdue_tasks_label.setText(str(overdue_tasks))
        self.low_stock_label.setText(str(low_stock_parts))
        
        # 更新图表
        self.update_task_chart()
        self.update_equipment_chart()
    
    def update_task_chart(self):
        """更新任务状态图表"""
        # 获取任务状态分布
        status_counts = {}
        tasks = self.db_manager.get_maintenance_tasks()
        
        for task in tasks:
            status = task[4]
            status_counts[status] = status_counts.get(status, 0) + 1
        
        # 创建饼图
        self.task_chart.figure.clear()
        ax = self.task_chart.figure.add_subplot(111)
        
        if status_counts:
            labels = list(status_counts.keys())
            sizes = list(status_counts.values())
            
            # 设置颜色
            colors = ['#ff9999', '#66b3ff', '#99ff99', '#ffcc99']
            
            ax.pie(sizes, labels=labels, autopct='%1.1f%%', colors=colors[:len(labels)])
            ax.set_title('检修任务状态分布')
        
        self.task_chart.canvas.draw()
    
    def update_equipment_chart(self):
        """更新设备状态图表"""
        # 获取设备状态分布
        status_counts = {}
        equipment = self.db_manager.get_equipment_list()
        
        for eq in equipment:
            status = eq[5]
            status_counts[status] = status_counts.get(status, 0) + 1
        
        # 创建柱状图
        self.equipment_chart.figure.clear()
        ax = self.equipment_chart.figure.add_subplot(111)
        
        if status_counts:
            labels = list(status_counts.keys())
            counts = list(status_counts.values())
            
            bars = ax.bar(labels, counts, color=['#66b3ff', '#99ff99', '#ff9999', '#ffcc99'])
            ax.set_title('设备状态分布')
            ax.set_ylabel('设备数量')
            
            # 在柱子上显示数值
            for bar, count in zip(bars, counts):
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                        f'{count}', ha='center', va='bottom')
        
        self.equipment_chart.canvas.draw()


class MatplotlibWidget(QWidget):
    """Matplotlib图表组件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 创建图形和画布
        self.figure = plt.figure(figsize=(8, 6))
        self.canvas = FigureCanvas(self.figure)
        
        # 设置布局
        layout = QVBoxLayout()
        layout.addWidget(self.canvas)
        self.setLayout(layout)


class MaintenanceSystem(QMainWindow):
    """检修系统主窗口"""
    
    def __init__(self):
        super().__init__()
        self.db_manager = DatabaseManager()
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("高级检修管理系统")
        self.setGeometry(100, 100, 1200, 800)
        
        # 创建中心部件
        central_widget = QTabWidget()
        self.setCentralWidget(central_widget)
        
        # 仪表板
        self.dashboard = DashboardWidget(self.db_manager)
        central_widget.addTab(self.dashboard, "仪表板")
        
        # 设备管理
        self.equipment_widget = EquipmentWidget(self.db_manager)
        central_widget.addTab(self.equipment_widget, "设备管理")
        
        # 检修任务
        self.task_widget = MaintenanceTaskWidget(self.db_manager)
        central_widget.addTab(self.task_widget, "检修任务")
        
        # 连接信号
        self.equipment_widget.equipment_selected.connect(self.on_equipment_selected)
        
        # 创建菜单栏
        self.create_menus()
        
        # 创建状态栏
        self.statusBar().showMessage("就绪")
    
    def create_menus(self):
        """创建菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu('文件')
        
        export_action = QAction('导出数据', self)
        export_action.triggered.connect(self.export_data)
        file_menu.addAction(export_action)
        
        exit_action = QAction('退出', self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 工具菜单
        tools_menu = menubar.addMenu('工具')
        
        generate_report_action = QAction('生成报告', self)
        generate_report_action.triggered.connect(self.generate_report)
        tools_menu.addAction(generate_report_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu('帮助')
        
        about_action = QAction('关于', self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def on_equipment_selected(self, equipment_id):
        """设备选择事件"""
        # 这里可以打开设备详情页面或执行其他操作
        QMessageBox.information(self, "设备选择", f"已选择设备 ID: {equipment_id}")
    
    def export_data(self):
        """导出数据"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出数据", "", "CSV文件 (*.csv);;所有文件 (*)"
        )
        
        if file_path:
            # 这里可以实现数据导出逻辑
            QMessageBox.information(self, "导出成功", f"数据已导出到: {file_path}")
    
    def generate_report(self):
        """生成报告"""
        # 这里可以实现报告生成逻辑
        QMessageBox.information(self, "报告生成", "检修报告已生成")
    
    def show_about(self):
        """显示关于对话框"""
        QMessageBox.about(self, "关于", 
                         "高级检修管理系统 v1.0\n\n"
                         "这是一个功能强大的设备检修管理系统，"
                         "提供设备管理、任务调度、数据可视化等功能。")


def main():
    app = QApplication(sys.argv)
    
    # 设置应用程序样式
    app.setStyle('Fusion')
    
    # 创建并显示主窗口
    window = MaintenanceSystem()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()