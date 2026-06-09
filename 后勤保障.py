import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sqlite3
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QTableWidget, QTableWidgetItem, QTabWidget, 
                             QLabel, QLineEdit, QTextEdit, QComboBox, QDateEdit, 
                             QSpinBox, QDoubleSpinBox, QCheckBox, QGroupBox, 
                             QMessageBox, QFileDialog, QProgressBar, QSplitter, 
                             QTreeWidget, QTreeWidgetItem, QHeaderView, QFormLayout,
                             QDialog, QDialogButtonBox, QListWidget, QListWidgetItem,
                             QToolBar, QAction, QStatusBar, QMenu, QSystemTrayIcon)
from PyQt5.QtCore import Qt, QTimer, QDate, QSize, QThread, pyqtSignal
from PyQt5.QtGui import QIcon, QFont, QPixmap, QPainter, QColor, QPalette
from PyQt5.QtChart import QChart, QChartView, QBarSeries, QBarSet, QBarCategoryAxis, QValueAxis
import matplotlib
matplotlib.rc("font", family='Microsoft YaHei')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import seaborn as sns
import warnings
warnings.filterwarnings('ignore')

# 数据库管理类
class DatabaseManager:
    def __init__(self, db_path="logistics.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """初始化数据库表结构"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建物资表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS supplies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                unit TEXT NOT NULL,
                min_stock INTEGER DEFAULT 0,
                max_stock INTEGER DEFAULT 100,
                supplier TEXT,
                purchase_date TEXT,
                expiry_date TEXT,
                status TEXT DEFAULT '正常',
                location TEXT,
                notes TEXT
            )
        ''')
        
        # 创建入库记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS inbound_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                supply_id INTEGER,
                quantity INTEGER NOT NULL,
                operator TEXT,
                date TEXT,
                notes TEXT,
                FOREIGN KEY (supply_id) REFERENCES supplies (id)
            )
        ''')
        
        # 创建出库记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS outbound_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                supply_id INTEGER,
                quantity INTEGER NOT NULL,
                recipient TEXT,
                purpose TEXT,
                operator TEXT,
                date TEXT,
                notes TEXT,
                FOREIGN KEY (supply_id) REFERENCES supplies (id)
            )
        ''')
        
        # 创建人员表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS personnel (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                department TEXT,
                position TEXT,
                contact TEXT,
                status TEXT DEFAULT '在职'
            )
        ''')
        
        # 创建设备表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS equipment (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT,
                status TEXT,
                location TEXT,
                maintenance_date TEXT,
                next_maintenance TEXT,
                responsible_person TEXT,
                notes TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def execute_query(self, query, params=None):
        """执行SQL查询"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        result = cursor.fetchall()
        conn.commit()
        conn.close()
        return result
    
    def get_supplies(self, category=None, status=None):
        """获取物资列表"""
        query = "SELECT * FROM supplies"
        conditions = []
        params = []
        
        if category:
            conditions.append("category = ?")
            params.append(category)
        if status:
            conditions.append("status = ?")
            params.append(status)
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        return self.execute_query(query, params)
    
    def add_supply(self, name, category, quantity, unit, min_stock=0, max_stock=100, 
                   supplier=None, purchase_date=None, expiry_date=None, location=None, notes=None):
        """添加物资"""
        query = """
        INSERT INTO supplies (name, category, quantity, unit, min_stock, max_stock, 
                             supplier, purchase_date, expiry_date, location, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (name, category, quantity, unit, min_stock, max_stock, 
                 supplier, purchase_date, expiry_date, location, notes)
        return self.execute_query(query, params)
    
    def update_supply_quantity(self, supply_id, new_quantity):
        """更新物资数量"""
        query = "UPDATE supplies SET quantity = ? WHERE id = ?"
        return self.execute_query(query, (new_quantity, supply_id))
    
    def record_inbound(self, supply_id, quantity, operator, date, notes=None):
        """记录入库"""
        # 更新库存
        current_quantity = self.execute_query("SELECT quantity FROM supplies WHERE id = ?", (supply_id,))[0][0]
        new_quantity = current_quantity + quantity
        self.update_supply_quantity(supply_id, new_quantity)
        
        # 记录入库
        query = "INSERT INTO inbound_records (supply_id, quantity, operator, date, notes) VALUES (?, ?, ?, ?, ?)"
        return self.execute_query(query, (supply_id, quantity, operator, date, notes))
    
    def record_outbound(self, supply_id, quantity, recipient, purpose, operator, date, notes=None):
        """记录出库"""
        # 检查库存是否足够
        current_quantity = self.execute_query("SELECT quantity FROM supplies WHERE id = ?", (supply_id,))[0][0]
        if current_quantity < quantity:
            return False, "库存不足"
        
        # 更新库存
        new_quantity = current_quantity - quantity
        self.update_supply_quantity(supply_id, new_quantity)
        
        # 记录出库
        query = "INSERT INTO outbound_records (supply_id, quantity, recipient, purpose, operator, date, notes) VALUES (?, ?, ?, ?, ?, ?, ?)"
        self.execute_query(query, (supply_id, quantity, recipient, purpose, operator, date, notes))
        return True, "出库成功"

# 报表生成类
class ReportGenerator:
    def __init__(self, db_manager):
        self.db_manager = db_manager
    
    def generate_supply_report(self, start_date=None, end_date=None):
        """生成物资报表"""
        # 获取物资数据
        supplies = self.db_manager.get_supplies()
        
        # 获取入库出库记录
        inbound_query = "SELECT supply_id, SUM(quantity) FROM inbound_records"
        outbound_query = "SELECT supply_id, SUM(quantity) FROM outbound_records"
        
        if start_date and end_date:
            inbound_query += f" WHERE date BETWEEN '{start_date}' AND '{end_date}'"
            outbound_query += f" WHERE date BETWEEN '{start_date}' AND '{end_date}'"
        
        inbound_query += " GROUP BY supply_id"
        outbound_query += " GROUP BY supply_id"
        
        inbound_data = self.db_manager.execute_query(inbound_query)
        outbound_data = self.db_manager.execute_query(outbound_query)
        
        # 转换为字典便于查找
        inbound_dict = {item[0]: item[1] for item in inbound_data}
        outbound_dict = {item[0]: item[1] for item in outbound_data}
        
        # 生成报表数据
        report_data = []
        for supply in supplies:
            supply_id = supply[0]
            inbound_qty = inbound_dict.get(supply_id, 0)
            outbound_qty = outbound_dict.get(supply_id, 0)
            
            report_data.append({
                'ID': supply_id,
                '名称': supply[1],
                '类别': supply[2],
                '当前库存': supply[3],
                '单位': supply[4],
                '最低库存': supply[5],
                '最高库存': supply[6],
                '入库数量': inbound_qty,
                '出库数量': outbound_qty,
                '状态': supply[10]
            })
        
        return pd.DataFrame(report_data)
    
    def generate_stock_alert_report(self):
        """生成库存预警报表"""
        supplies = self.db_manager.get_supplies()
        alert_data = []
        
        for supply in supplies:
            current_qty = supply[3]
            min_stock = supply[5]
            max_stock = supply[6]
            
            if current_qty < min_stock:
                status = "库存不足"
                alert_level = "高"
            elif current_qty > max_stock:
                status = "库存过剩"
                alert_level = "中"
            else:
                continue  # 只包含需要预警的物资
            
            alert_data.append({
                'ID': supply[0],
                '名称': supply[1],
                '类别': supply[2],
                '当前库存': current_qty,
                '最低库存': min_stock,
                '最高库存': max_stock,
                '预警状态': status,
                '预警级别': alert_level
            })
        
        return pd.DataFrame(alert_data)

# 图表生成类
class ChartGenerator:
    def __init__(self):
        self.fig, self.ax = plt.subplots(figsize=(10, 6))
    
    def generate_supply_category_chart(self, db_manager):
        """生成物资类别分布图"""
        supplies = db_manager.get_supplies()
        df = pd.DataFrame(supplies, columns=['id', 'name', 'category', 'quantity', 'unit', 
                                            'min_stock', 'max_stock', 'supplier', 'purchase_date', 
                                            'expiry_date', 'status', 'location', 'notes'])
        
        category_counts = df['category'].value_counts()
        
        self.ax.clear()
        category_counts.plot(kind='bar', ax=self.ax, color='skyblue')
        self.ax.set_title('物资类别分布')
        self.ax.set_xlabel('类别')
        self.ax.set_ylabel('数量')
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        return self.fig
    
    def generate_stock_status_chart(self, db_manager):
        """生成库存状态图"""
        supplies = db_manager.get_supplies()
        df = pd.DataFrame(supplies, columns=['id', 'name', 'category', 'quantity', 'unit', 
                                            'min_stock', 'max_stock', 'supplier', 'purchase_date', 
                                            'expiry_date', 'status', 'location', 'notes'])
        
        # 计算各类状态的数量
        status_counts = df['status'].value_counts()
        
        self.ax.clear()
        status_counts.plot(kind='pie', ax=self.ax, autopct='%1.1f%%')
        self.ax.set_title('库存状态分布')
        
        return self.fig

# 自定义表格组件
class CustomTableWidget(QTableWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        """设置表格UI"""
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QTableWidget.SelectRows)
        self.setSortingEnabled(True)
        header = self.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setStretchLastSection(True)
    
    def populate_table(self, data, headers):
        """填充表格数据"""
        self.setRowCount(len(data))
        self.setColumnCount(len(headers))
        self.setHorizontalHeaderLabels(headers)
        
        for row_idx, row_data in enumerate(data):
            for col_idx, cell_data in enumerate(row_data):
                item = QTableWidgetItem(str(cell_data))
                self.setItem(row_idx, col_idx, item)
        
        self.resizeColumnsToContents()

# 库存监控面板
class StockMonitorWidget(QWidget):
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.setup_ui()
        self.refresh_data()
    
    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout()
        
        # 标题
        title_label = QLabel("库存监控面板")
        title_label.setFont(QFont("Arial", 16, QFont.Bold))
        layout.addWidget(title_label)
        
        # 控制按钮
        control_layout = QHBoxLayout()
        self.refresh_btn = QPushButton("刷新数据")
        self.refresh_btn.clicked.connect(self.refresh_data)
        self.alert_btn = QPushButton("查看预警")
        self.alert_btn.clicked.connect(self.show_alerts)
        
        control_layout.addWidget(self.refresh_btn)
        control_layout.addWidget(self.alert_btn)
        control_layout.addStretch()
        
        layout.addLayout(control_layout)
        
        # 库存表格
        self.table_widget = CustomTableWidget()
        layout.addWidget(self.table_widget)
        
        # 状态标签
        self.status_label = QLabel("就绪")
        layout.addWidget(self.status_label)
        
        self.setLayout(layout)
    
    def refresh_data(self):
        """刷新数据"""
        try:
            supplies = self.db_manager.get_supplies()
            headers = ['ID', '名称', '类别', '数量', '单位', '最低库存', '最高库存', '状态']
            data = []
            
            for supply in supplies:
                # 确定库存状态
                quantity = supply[3]
                min_stock = supply[5]
                max_stock = supply[6]
                
                if quantity < min_stock:
                    status = "库存不足"
                elif quantity > max_stock:
                    status = "库存过剩"
                else:
                    status = "正常"
                
                data.append([
                    supply[0], supply[1], supply[2], quantity, supply[4],
                    min_stock, max_stock, status
                ])
            
            self.table_widget.populate_table(data, headers)
            self.status_label.setText(f"数据已更新，共 {len(supplies)} 条记录")
            
        except Exception as e:
            self.status_label.setText(f"错误: {str(e)}")
    
    def show_alerts(self):
        """显示库存预警"""
        try:
            report_generator = ReportGenerator(self.db_manager)
            alert_df = report_generator.generate_stock_alert_report()
            
            if alert_df.empty:
                QMessageBox.information(self, "库存预警", "当前没有库存预警")
                return
            
            # 创建预警对话框
            dialog = QDialog(self)
            dialog.setWindowTitle("库存预警")
            dialog.setModal(True)
            dialog.resize(600, 400)
            
            layout = QVBoxLayout()
            
            # 预警表格
            table = CustomTableWidget()
            headers = list(alert_df.columns)
            data = alert_df.values.tolist()
            table.populate_table(data, headers)
            
            layout.addWidget(table)
            
            # 按钮
            btn_box = QDialogButtonBox(QDialogButtonBox.Ok)
            btn_box.accepted.connect(dialog.accept)
            layout.addWidget(btn_box)
            
            dialog.setLayout(layout)
            dialog.exec_()
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"生成预警报表时出错: {str(e)}")

# 数据可视化面板
class DataVisualizationWidget(QWidget):
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.chart_generator = ChartGenerator()
        self.setup_ui()
        self.refresh_charts()
    
    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout()
        
        # 标题
        title_label = QLabel("数据可视化")
        title_label.setFont(QFont("Arial", 16, QFont.Bold))
        layout.addWidget(title_label)
        
        # 图表选择
        chart_layout = QHBoxLayout()
        chart_layout.addWidget(QLabel("选择图表类型:"))
        
        self.chart_combo = QComboBox()
        self.chart_combo.addItems(["物资类别分布", "库存状态分布"])
        self.chart_combo.currentTextChanged.connect(self.refresh_charts)
        
        chart_layout.addWidget(self.chart_combo)
        chart_layout.addStretch()
        
        layout.addLayout(chart_layout)
        
        # 图表容器
        self.chart_canvas = FigureCanvas(self.chart_generator.fig)
        layout.addWidget(self.chart_canvas)
        
        self.setLayout(layout)
    
    def refresh_charts(self):
        """刷新图表"""
        chart_type = self.chart_combo.currentText()
        
        try:
            if chart_type == "物资类别分布":
                fig = self.chart_generator.generate_supply_category_chart(self.db_manager)
            elif chart_type == "库存状态分布":
                fig = self.chart_generator.generate_stock_status_chart(self.db_manager)
            
            self.chart_canvas.figure = fig
            self.chart_canvas.draw()
            
        except Exception as e:
            print(f"生成图表时出错: {str(e)}")

# 物资管理面板
class SupplyManagementWidget(QWidget):
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.setup_ui()
        self.refresh_supplies()
    
    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout()
        
        # 标题
        title_label = QLabel("物资管理")
        title_label.setFont(QFont("Arial", 16, QFont.Bold))
        layout.addWidget(title_label)
        
        # 操作按钮
        btn_layout = QHBoxLayout()
        
        self.add_btn = QPushButton("添加物资")
        self.add_btn.clicked.connect(self.add_supply)
        
        self.edit_btn = QPushButton("编辑物资")
        self.edit_btn.clicked.connect(self.edit_supply)
        
        self.delete_btn = QPushButton("删除物资")
        self.delete_btn.clicked.connect(self.delete_supply)
        
        self.inbound_btn = QPushButton("入库操作")
        self.inbound_btn.clicked.connect(self.inbound_supply)
        
        self.outbound_btn = QPushButton("出库操作")
        self.outbound_btn.clicked.connect(self.outbound_supply)
        
        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.clicked.connect(self.refresh_supplies)
        
        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.edit_btn)
        btn_layout.addWidget(self.delete_btn)
        btn_layout.addWidget(self.inbound_btn)
        btn_layout.addWidget(self.outbound_btn)
        btn_layout.addWidget(self.refresh_btn)
        btn_layout.addStretch()
        
        layout.addLayout(btn_layout)
        
        # 物资表格
        self.table_widget = CustomTableWidget()
        layout.addWidget(self.table_widget)
        
        self.setLayout(layout)
    
    def refresh_supplies(self):
        """刷新物资列表"""
        try:
            supplies = self.db_manager.get_supplies()
            headers = ['ID', '名称', '类别', '数量', '单位', '最低库存', '最高库存', '供应商', '状态']
            data = []
            
            for supply in supplies:
                data.append([
                    supply[0], supply[1], supply[2], supply[3], supply[4],
                    supply[5], supply[6], supply[7] or "", supply[10]
                ])
            
            self.table_widget.populate_table(data, headers)
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"刷新物资列表时出错: {str(e)}")
    
    def add_supply(self):
        """添加物资"""
        dialog = SupplyDialog(self.db_manager, self)
        if dialog.exec_() == QDialog.Accepted:
            self.refresh_supplies()
    
    def edit_supply(self):
        """编辑物资"""
        selected_items = self.table_widget.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "警告", "请先选择要编辑的物资")
            return
        
        supply_id = int(self.table_widget.item(selected_items[0].row(), 0).text())
        dialog = SupplyDialog(self.db_manager, self, supply_id)
        if dialog.exec_() == QDialog.Accepted:
            self.refresh_supplies()
    
    def delete_supply(self):
        """删除物资"""
        selected_items = self.table_widget.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "警告", "请先选择要删除的物资")
            return
        
        supply_id = int(self.table_widget.item(selected_items[0].row(), 0).text())
        supply_name = self.table_widget.item(selected_items[0].row(), 1).text()
        
        reply = QMessageBox.question(
            self, "确认删除", 
            f"确定要删除物资 '{supply_name}' 吗？", 
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                self.db_manager.execute_query("DELETE FROM supplies WHERE id = ?", (supply_id,))
                self.refresh_supplies()
                QMessageBox.information(self, "成功", "物资删除成功")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"删除物资时出错: {str(e)}")
    
    def inbound_supply(self):
        """入库操作"""
        selected_items = self.table_widget.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "警告", "请先选择要入库的物资")
            return
        
        supply_id = int(self.table_widget.item(selected_items[0].row(), 0).text())
        supply_name = self.table_widget.item(selected_items[0].row(), 1).text()
        
        dialog = InboundDialog(self.db_manager, supply_id, supply_name, self)
        if dialog.exec_() == QDialog.Accepted:
            self.refresh_supplies()
    
    def outbound_supply(self):
        """出库操作"""
        selected_items = self.table_widget.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "警告", "请先选择要出库的物资")
            return
        
        supply_id = int(self.table_widget.item(selected_items[0].row(), 0).text())
        supply_name = self.table_widget.item(selected_items[0].row(), 1).text()
        
        dialog = OutboundDialog(self.db_manager, supply_id, supply_name, self)
        if dialog.exec_() == QDialog.Accepted:
            self.refresh_supplies()

# 物资对话框
class SupplyDialog(QDialog):
    def __init__(self, db_manager, parent=None, supply_id=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.supply_id = supply_id
        self.is_edit = supply_id is not None
        
        self.setup_ui()
        if self.is_edit:
            self.load_supply_data()
    
    def setup_ui(self):
        """设置UI"""
        self.setWindowTitle("编辑物资" if self.is_edit else "添加物资")
        self.setModal(True)
        self.resize(400, 500)
        
        layout = QVBoxLayout()
        
        # 表单
        form_layout = QFormLayout()
        
        self.name_edit = QLineEdit()
        form_layout.addRow("物资名称:", self.name_edit)
        
        self.category_combo = QComboBox()
        self.category_combo.addItems(["办公用品", "电子设备", "医疗物资", "食品饮料", "清洁用品", "其他"])
        form_layout.addRow("类别:", self.category_combo)
        
        self.quantity_spin = QSpinBox()
        self.quantity_spin.setRange(0, 100000)
        form_layout.addRow("数量:", self.quantity_spin)
        
        self.unit_edit = QLineEdit()
        self.unit_edit.setText("个")
        form_layout.addRow("单位:", self.unit_edit)
        
        self.min_stock_spin = QSpinBox()
        self.min_stock_spin.setRange(0, 100000)
        form_layout.addRow("最低库存:", self.min_stock_spin)
        
        self.max_stock_spin = QSpinBox()
        self.max_stock_spin.setRange(0, 100000)
        form_layout.addRow("最高库存:", self.max_stock_spin)
        
        self.supplier_edit = QLineEdit()
        form_layout.addRow("供应商:", self.supplier_edit)
        
        self.location_edit = QLineEdit()
        form_layout.addRow("存放位置:", self.location_edit)
        
        self.notes_edit = QTextEdit()
        self.notes_edit.setMaximumHeight(100)
        form_layout.addRow("备注:", self.notes_edit)
        
        layout.addLayout(form_layout)
        
        # 按钮
        btn_layout = QHBoxLayout()
        
        self.save_btn = QPushButton("保存")
        self.save_btn.clicked.connect(self.save_supply)
        
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
    
    def load_supply_data(self):
        """加载物资数据"""
        try:
            supply = self.db_manager.execute_query(
                "SELECT * FROM supplies WHERE id = ?", (self.supply_id,)
            )[0]
            
            self.name_edit.setText(supply[1])
            self.category_combo.setCurrentText(supply[2])
            self.quantity_spin.setValue(supply[3])
            self.unit_edit.setText(supply[4])
            self.min_stock_spin.setValue(supply[5])
            self.max_stock_spin.setValue(supply[6])
            self.supplier_edit.setText(supply[7] or "")
            self.location_edit.setText(supply[11] or "")
            self.notes_edit.setPlainText(supply[12] or "")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载物资数据时出错: {str(e)}")
    
    def save_supply(self):
        """保存物资"""
        try:
            name = self.name_edit.text().strip()
            if not name:
                QMessageBox.warning(self, "警告", "物资名称不能为空")
                return
            
            data = (
                name,
                self.category_combo.currentText(),
                self.quantity_spin.value(),
                self.unit_edit.text().strip(),
                self.min_stock_spin.value(),
                self.max_stock_spin.value(),
                self.supplier_edit.text().strip() or None,
                self.location_edit.text().strip() or None,
                self.notes_edit.toPlainText().strip() or None
            )
            
            if self.is_edit:
                # 更新现有物资
                query = """
                UPDATE supplies SET name=?, category=?, quantity=?, unit=?, 
                min_stock=?, max_stock=?, supplier=?, location=?, notes=?
                WHERE id=?
                """
                self.db_manager.execute_query(query, data + (self.supply_id,))
            else:
                # 添加新物资
                query = """
                INSERT INTO supplies (name, category, quantity, unit, min_stock, max_stock, supplier, location, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                self.db_manager.execute_query(query, data)
            
            self.accept()
            QMessageBox.information(self, "成功", "物资保存成功")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存物资时出错: {str(e)}")

# 入库对话框
class InboundDialog(QDialog):
    def __init__(self, db_manager, supply_id, supply_name, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.supply_id = supply_id
        self.supply_name = supply_name
        
        self.setup_ui()
    
    def setup_ui(self):
        """设置UI"""
        self.setWindowTitle(f"入库操作 - {self.supply_name}")
        self.setModal(True)
        self.resize(300, 200)
        
        layout = QVBoxLayout()
        
        # 表单
        form_layout = QFormLayout()
        
        self.quantity_spin = QSpinBox()
        self.quantity_spin.setRange(1, 100000)
        self.quantity_spin.setValue(1)
        form_layout.addRow("入库数量:", self.quantity_spin)
        
        self.operator_edit = QLineEdit()
        form_layout.addRow("操作员:", self.operator_edit)
        
        self.date_edit = QDateEdit()
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        form_layout.addRow("入库日期:", self.date_edit)
        
        self.notes_edit = QTextEdit()
        self.notes_edit.setMaximumHeight(80)
        form_layout.addRow("备注:", self.notes_edit)
        
        layout.addLayout(form_layout)
        
        # 按钮
        btn_layout = QHBoxLayout()
        
        self.save_btn = QPushButton("确认入库")
        self.save_btn.clicked.connect(self.save_inbound)
        
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
    
    def save_inbound(self):
        """保存入库记录"""
        try:
            operator = self.operator_edit.text().strip()
            if not operator:
                QMessageBox.warning(self, "警告", "操作员不能为空")
                return
            
            self.db_manager.record_inbound(
                self.supply_id,
                self.quantity_spin.value(),
                operator,
                self.date_edit.date().toString("yyyy-MM-dd"),
                self.notes_edit.toPlainText().strip() or None
            )
            
            self.accept()
            QMessageBox.information(self, "成功", "入库操作成功")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"入库操作时出错: {str(e)}")

# 出库对话框
class OutboundDialog(QDialog):
    def __init__(self, db_manager, supply_id, supply_name, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.supply_id = supply_id
        self.supply_name = supply_name
        
        self.setup_ui()
    
    def setup_ui(self):
        """设置UI"""
        self.setWindowTitle(f"出库操作 - {self.supply_name}")
        self.setModal(True)
        self.resize(300, 250)
        
        layout = QVBoxLayout()
        
        # 显示当前库存
        current_qty = self.db_manager.execute_query(
            "SELECT quantity FROM supplies WHERE id = ?", (self.supply_id,)
        )[0][0]
        
        stock_label = QLabel(f"当前库存: {current_qty}")
        stock_label.setStyleSheet("color: blue; font-weight: bold;")
        layout.addWidget(stock_label)
        
        # 表单
        form_layout = QFormLayout()
        
        self.quantity_spin = QSpinBox()
        self.quantity_spin.setRange(1, current_qty)
        self.quantity_spin.setValue(1)
        form_layout.addRow("出库数量:", self.quantity_spin)
        
        self.recipient_edit = QLineEdit()
        form_layout.addRow("领用人:", self.recipient_edit)
        
        self.purpose_edit = QLineEdit()
        form_layout.addRow("用途:", self.purpose_edit)
        
        self.operator_edit = QLineEdit()
        form_layout.addRow("操作员:", self.operator_edit)
        
        self.date_edit = QDateEdit()
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        form_layout.addRow("出库日期:", self.date_edit)
        
        self.notes_edit = QTextEdit()
        self.notes_edit.setMaximumHeight(60)
        form_layout.addRow("备注:", self.notes_edit)
        
        layout.addLayout(form_layout)
        
        # 按钮
        btn_layout = QHBoxLayout()
        
        self.save_btn = QPushButton("确认出库")
        self.save_btn.clicked.connect(self.save_outbound)
        
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
    
    def save_outbound(self):
        """保存出库记录"""
        try:
            recipient = self.recipient_edit.text().strip()
            purpose = self.purpose_edit.text().strip()
            operator = self.operator_edit.text().strip()
            
            if not recipient:
                QMessageBox.warning(self, "警告", "领用人不能为空")
                return
            if not purpose:
                QMessageBox.warning(self, "警告", "用途不能为空")
                return
            if not operator:
                QMessageBox.warning(self, "警告", "操作员不能为空")
                return
            
            success, message = self.db_manager.record_outbound(
                self.supply_id,
                self.quantity_spin.value(),
                recipient,
                purpose,
                operator,
                self.date_edit.date().toString("yyyy-MM-dd"),
                self.notes_edit.toPlainText().strip() or None
            )
            
            if success:
                self.accept()
                QMessageBox.information(self, "成功", message)
            else:
                QMessageBox.warning(self, "警告", message)
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"出库操作时出错: {str(e)}")

# 主窗口
class LogisticsSystemMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.db_manager = DatabaseManager()
        self.setup_ui()
    
    def setup_ui(self):
        """设置主窗口UI"""
        self.setWindowTitle("后勤保障系统 - 高级工具库")
        self.setGeometry(100, 50, 1200, 800)
        
        # 设置图标
        self.setWindowIcon(QIcon.fromTheme("applications-office"))
        
        # 创建中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)
        
        # 创建选项卡
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        # 添加各个功能面板
        self.stock_monitor_tab = StockMonitorWidget(self.db_manager)
        self.tab_widget.addTab(self.stock_monitor_tab, "库存监控")
        
        self.supply_management_tab = SupplyManagementWidget(self.db_manager)
        self.tab_widget.addTab(self.supply_management_tab, "物资管理")
        
        self.data_visualization_tab = DataVisualizationWidget(self.db_manager)
        self.tab_widget.addTab(self.data_visualization_tab, "数据可视化")
        
        # 创建菜单栏
        self.create_menubar()
        
        # 创建工具栏
        self.create_toolbar()
        
        # 创建状态栏
        self.statusBar().showMessage("就绪")
    
    def create_menubar(self):
        """创建菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu("文件")
        
        export_action = QAction("导出报表", self)
        export_action.triggered.connect(self.export_report)
        file_menu.addAction(export_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("退出", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 工具菜单
        tools_menu = menubar.addMenu("工具")
        
        backup_action = QAction("备份数据", self)
        backup_action.triggered.connect(self.backup_data)
        tools_menu.addAction(backup_action)
        
        restore_action = QAction("恢复数据", self)
        restore_action.triggered.connect(self.restore_data)
        tools_menu.addAction(restore_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu("帮助")
        
        about_action = QAction("关于", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def create_toolbar(self):
        """创建工具栏"""
        toolbar = self.addToolBar("主工具栏")
        
        refresh_action = QAction("刷新", self)
        refresh_action.triggered.connect(self.refresh_all)
        toolbar.addAction(refresh_action)
        
        toolbar.addSeparator()
        
        monitor_action = QAction("库存监控", self)
        monitor_action.triggered.connect(lambda: self.tab_widget.setCurrentIndex(0))
        toolbar.addAction(monitor_action)
        
        manage_action = QAction("物资管理", self)
        manage_action.triggered.connect(lambda: self.tab_widget.setCurrentIndex(1))
        toolbar.addAction(manage_action)
        
        chart_action = QAction("数据可视化", self)
        chart_action.triggered.connect(lambda: self.tab_widget.setCurrentIndex(2))
        toolbar.addAction(chart_action)
    
    def refresh_all(self):
        """刷新所有面板"""
        self.stock_monitor_tab.refresh_data()
        self.supply_management_tab.refresh_supplies()
        self.data_visualization_tab.refresh_charts()
        
        self.statusBar().showMessage("所有数据已刷新")
    
    def export_report(self):
        """导出报表"""
        try:
            # 选择保存路径
            file_path, _ = QFileDialog.getSaveFileName(
                self, "导出报表", "后勤保障系统报表.xlsx", "Excel Files (*.xlsx)"
            )
            
            if not file_path:
                return
            
            # 生成报表
            report_generator = ReportGenerator(self.db_manager)
            supply_report = report_generator.generate_supply_report()
            alert_report = report_generator.generate_stock_alert_report()
            
            # 保存到Excel
            with pd.ExcelWriter(file_path) as writer:
                supply_report.to_excel(writer, sheet_name='物资总览', index=False)
                if not alert_report.empty:
                    alert_report.to_excel(writer, sheet_name='库存预警', index=False)
            
            QMessageBox.information(self, "成功", f"报表已导出到: {file_path}")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"导出报表时出错: {str(e)}")
    
    def backup_data(self):
        """备份数据"""
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self, "备份数据", "logistics_backup.db", "Database Files (*.db)"
            )
            
            if not file_path:
                return
            
            # 简单的数据库备份（实际应用中可能需要更复杂的备份策略）
            import shutil
            shutil.copy2("logistics.db", file_path)
            
            QMessageBox.information(self, "成功", f"数据已备份到: {file_path}")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"备份数据时出错: {str(e)}")
    
    def restore_data(self):
        """恢复数据"""
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self, "恢复数据", "", "Database Files (*.db)"
            )
            
            if not file_path:
                return
            
            reply = QMessageBox.question(
                self, "确认恢复", 
                "恢复数据将覆盖当前所有数据，是否继续？", 
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                import shutil
                shutil.copy2(file_path, "logistics.db")
                
                # 重新初始化数据库管理器
                self.db_manager = DatabaseManager()
                
                # 刷新所有面板
                self.refresh_all()
                
                QMessageBox.information(self, "成功", "数据恢复完成")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"恢复数据时出错: {str(e)}")
    
    def show_about(self):
        """显示关于信息"""
        about_text = """
        <h2>后勤保障系统 - 高级工具库</h2>
        <p>版本: 1.0</p>
        <p>这是一个功能强大的后勤保障系统工具库，提供完整的物资管理、库存监控和数据可视化功能。</p>
        <p>主要功能:</p>
        <ul>
            <li>物资信息管理</li>
            <li>入库出库操作</li>
            <li>库存监控与预警</li>
            <li>数据可视化分析</li>
            <li>报表导出</li>
            <li>数据备份与恢复</li>
        </ul>
        <p>开发团队: 后勤保障系统开发组</p>
        """
        
        QMessageBox.about(self, "关于", about_text)

# 应用程序类
class LogisticsSystemApp(QApplication):
    def __init__(self, argv):
        super().__init__(argv)
        self.setApplicationName("后勤保障系统")
        self.setApplicationVersion("1.0")
        
        # 创建主窗口
        self.main_window = LogisticsSystemMainWindow()
        self.main_window.show()

# 启动应用程序
if __name__ == "__main__":
    app = LogisticsSystemApp(sys.argv)
    sys.exit(app.exec_())