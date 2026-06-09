import sys
import json
import sqlite3
import datetime
from typing import Dict, List, Optional, Tuple, Any
from PyQt5.QtWidgets import (QApplication, QDateEdit, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QGridLayout, QLabel, QLineEdit, 
                             QPushButton, QTableWidget, QTableWidgetItem, 
                             QComboBox, QSpinBox, QDoubleSpinBox, QTextEdit,
                             QMessageBox, QTabWidget, QGroupBox, QCheckBox,
                             QProgressBar, QSlider, QProgressDialog, QDialog,
                             QHeaderView, QSplitter, QFrame, QToolBar, QAction,
                             QStatusBar, QMenu, QSystemTrayIcon, QStyle)
from PyQt5.QtCore import Qt, QTimer, QDateTime, QDate, QTime, pyqtSignal, QSize
from PyQt5.QtGui import QFont, QIcon, QPixmap, QPainter, QColor, QPalette
from PyQt5.QtChart import QChart, QChartView, QPieSeries, QBarSeries, QBarSet, QBarCategoryAxis, QValueAxis
import qrcode
from io import BytesIO
import requests
import hashlib
import random
import string


class DatabaseManager:
    """高级数据库管理工具"""
    
    def __init__(self, db_path="restaurant.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """初始化数据库表结构"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 菜单表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS menu_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                price REAL NOT NULL,
                cost REAL NOT NULL,
                description TEXT,
                image_path TEXT,
                available BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 订单表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                table_number INTEGER NOT NULL,
                status TEXT DEFAULT 'pending',
                total_amount REAL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP
            )
        ''')
        
        # 订单详情表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS order_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER,
                menu_item_id INTEGER,
                quantity INTEGER DEFAULT 1,
                special_requests TEXT,
                FOREIGN KEY (order_id) REFERENCES orders (id),
                FOREIGN KEY (menu_item_id) REFERENCES menu_items (id)
            )
        ''')
        
        # 员工表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS employees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                role TEXT NOT NULL,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                permissions TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 库存表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_name TEXT NOT NULL,
                category TEXT NOT NULL,
                quantity REAL NOT NULL,
                unit TEXT NOT NULL,
                min_threshold REAL DEFAULT 0,
                supplier TEXT,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 插入默认管理员账户
        cursor.execute('''
            INSERT OR IGNORE INTO employees (name, role, username, password_hash, permissions)
            VALUES (?, ?, ?, ?, ?)
        ''', ('系统管理员', 'admin', 'admin', 
              hashlib.sha256('admin123'.encode()).hexdigest(), 
              json.dumps(['all'])))
        
        conn.commit()
        conn.close()
    
    def execute_query(self, query, params=()):
        """执行查询并返回结果"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(query, params)
        
        if query.strip().upper().startswith('SELECT'):
            result = cursor.fetchall()
        else:
            conn.commit()
            result = cursor.lastrowid
        
        conn.close()
        return result
    
    def get_menu_items(self, category=None, available_only=True):
        """获取菜单项"""
        query = "SELECT * FROM menu_items"
        params = []
        
        if category or available_only:
            query += " WHERE"
            conditions = []
            
            if category:
                conditions.append(" category = ?")
                params.append(category)
            
            if available_only:
                conditions.append(" available = 1")
            
            query += " AND".join(conditions)
        
        return self.execute_query(query, params)
    
    def add_order(self, table_number, items):
        """添加新订单"""
        # 计算总金额
        total = 0
        for item in items:
            menu_item = self.execute_query(
                "SELECT price FROM menu_items WHERE id = ?", 
                (item['menu_item_id'],)
            )[0]
            total += menu_item[0] * item['quantity']
        
        # 插入订单
        order_id = self.execute_query(
            "INSERT INTO orders (table_number, total_amount) VALUES (?, ?)",
            (table_number, total)
        )
        
        # 插入订单项
        for item in items:
            self.execute_query(
                '''INSERT INTO order_items 
                (order_id, menu_item_id, quantity, special_requests) 
                VALUES (?, ?, ?, ?)''',
                (order_id, item['menu_item_id'], item['quantity'], 
                 item.get('special_requests', ''))
            )
        
        return order_id


class AnalyticsEngine:
    """数据分析引擎"""
    
    def __init__(self, db_manager):
        self.db = db_manager
    
    def get_sales_report(self, start_date=None, end_date=None):
        """生成销售报告"""
        if not start_date:
            start_date = QDate.currentDate().addDays(-30).toString("yyyy-MM-dd")
        if not end_date:
            end_date = QDate.currentDate().toString("yyyy-MM-dd")
        
        query = """
            SELECT 
                DATE(o.created_at) as date,
                COUNT(o.id) as order_count,
                SUM(o.total_amount) as total_sales,
                AVG(o.total_amount) as avg_order_value
            FROM orders o
            WHERE DATE(o.created_at) BETWEEN ? AND ?
            GROUP BY DATE(o.created_at)
            ORDER BY date
        """
        
        return self.db.execute_query(query, (start_date, end_date))
    
    def get_popular_items(self, limit=10):
        """获取最受欢迎的菜品"""
        query = """
            SELECT 
                mi.name,
                mi.category,
                SUM(oi.quantity) as total_quantity,
                SUM(oi.quantity * mi.price) as total_revenue
            FROM order_items oi
            JOIN menu_items mi ON oi.menu_item_id = mi.id
            JOIN orders o ON oi.order_id = o.id
            WHERE o.status = 'completed'
            GROUP BY mi.id
            ORDER BY total_quantity DESC
            LIMIT ?
        """
        
        return self.db.execute_query(query, (limit,))
    
    def get_category_sales(self):
        """按类别统计销售情况"""
        query = """
            SELECT 
                mi.category,
                COUNT(oi.id) as item_count,
                SUM(oi.quantity * mi.price) as total_revenue
            FROM order_items oi
            JOIN menu_items mi ON oi.menu_item_id = mi.id
            JOIN orders o ON oi.order_id = o.id
            WHERE o.status = 'completed'
            GROUP BY mi.category
            ORDER BY total_revenue DESC
        """
        
        return self.db.execute_query(query)


class QRCodeGenerator:
    """二维码生成工具"""
    
    @staticmethod
    def generate_table_qr_code(table_number, base_url="http://your-restaurant.com/menu"):
        """为餐桌生成二维码"""
        url = f"{base_url}?table={table_number}"
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(url)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # 转换为QPixmap
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        pixmap = QPixmap()
        pixmap.loadFromData(buffer.getvalue())
        
        return pixmap
    
    @staticmethod
    def generate_payment_qr_code(order_id, amount, payment_method="wechat"):
        """生成支付二维码"""
        # 实际应用中这里会调用支付API
        payment_data = f"order_{order_id}_amount_{amount}_method_{payment_method}"
        
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=8,
            border=4,
        )
        qr.add_data(payment_data)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        pixmap = QPixmap()
        pixmap.loadFromData(buffer.getvalue())
        
        return pixmap


class SmartSearchWidget(QLineEdit):
    """智能搜索组件"""
    
    item_selected = pyqtSignal(dict)
    
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.menu_items = []
        self.filtered_items = []
        self.setPlaceholderText("搜索菜品...")
        self.textChanged.connect(self.on_text_changed)
        
        # 创建下拉菜单
        self.completer = QComboBox(self)
        self.completer.setWindowFlags(Qt.Popup)
        self.completer.setFocusPolicy(Qt.NoFocus)
        self.completer.activated.connect(self.on_completer_activated)
        
        self.load_menu_items()
    
    def load_menu_items(self):
        """加载菜单项"""
        self.menu_items = self.db.execute_query(
            "SELECT id, name, category, price FROM menu_items WHERE available = 1"
        )
    
    def on_text_changed(self, text):
        """文本变化时过滤菜单项"""
        if not text:
            self.completer.hide()
            return
        
        self.filtered_items = [
            item for item in self.menu_items 
            if text.lower() in item[1].lower() or text.lower() in item[2].lower()
        ][:10]  # 限制显示数量
        
        if self.filtered_items:
            self.show_completer()
        else:
            self.completer.hide()
    
    def show_completer(self):
        """显示自动完成下拉框"""
        self.completer.clear()
        
        for item in self.filtered_items:
            self.completer.addItem(f"{item[1]} - {item[2]} - ¥{item[3]}")
        
        # 定位下拉框
        rect = self.rect()
        point = self.mapToGlobal(rect.bottomLeft())
        self.completer.move(point)
        self.completer.show()
    
    def on_completer_activated(self, index):
        """选择自动完成项"""
        if 0 <= index < len(self.filtered_items):
            selected_item = self.filtered_items[index]
            item_data = {
                'id': selected_item[0],
                'name': selected_item[1],
                'category': selected_item[2],
                'price': selected_item[3]
            }
            self.item_selected.emit(item_data)
            self.clear()
            self.completer.hide()


class OrderManagerWidget(QWidget):
    """订单管理组件"""
    
    order_updated = pyqtSignal()
    
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.current_orders = []
        self.init_ui()
        self.load_orders()
    
    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout()
        
        # 工具栏
        toolbar = QHBoxLayout()
        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.clicked.connect(self.load_orders)
        
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["全部", "待处理", "进行中", "已完成"])
        self.filter_combo.currentTextChanged.connect(self.filter_orders)
        
        toolbar.addWidget(QLabel("状态筛选:"))
        toolbar.addWidget(self.filter_combo)
        toolbar.addWidget(self.refresh_btn)
        toolbar.addStretch()
        
        # 订单表格
        self.orders_table = QTableWidget()
        self.orders_table.setColumnCount(6)
        self.orders_table.setHorizontalHeaderLabels([
            "订单ID", "桌号", "状态", "总金额", "创建时间", "操作"
        ])
        
        layout.addLayout(toolbar)
        layout.addWidget(self.orders_table)
        self.setLayout(layout)
    
    def load_orders(self):
        """加载订单"""
        self.current_orders = self.db.execute_query(
            "SELECT * FROM orders ORDER BY created_at DESC"
        )
        self.update_table()
    
    def filter_orders(self, status_filter):
        """过滤订单"""
        if status_filter == "全部":
            filtered_orders = self.current_orders
        else:
            status_map = {"待处理": "pending", "进行中": "in_progress", "已完成": "completed"}
            status = status_map.get(status_filter, "pending")
            filtered_orders = [order for order in self.current_orders if order[2] == status]
        
        self.update_table(filtered_orders)
    
    def update_table(self, orders=None):
        """更新表格显示"""
        if orders is None:
            orders = self.current_orders
        
        self.orders_table.setRowCount(len(orders))
        
        for row, order in enumerate(orders):
            self.orders_table.setItem(row, 0, QTableWidgetItem(str(order[0])))
            self.orders_table.setItem(row, 1, QTableWidgetItem(str(order[1])))
            self.orders_table.setItem(row, 2, QTableWidgetItem(order[2]))
            self.orders_table.setItem(row, 3, QTableWidgetItem(f"¥{order[3]:.2f}"))
            self.orders_table.setItem(row, 4, QTableWidgetItem(order[4]))
            
            # 操作按钮
            action_widget = QWidget()
            action_layout = QHBoxLayout()
            action_layout.setContentsMargins(0, 0, 0, 0)
            
            if order[2] != "completed":
                complete_btn = QPushButton("完成")
                complete_btn.clicked.connect(lambda checked, oid=order[0]: self.complete_order(oid))
                action_layout.addWidget(complete_btn)
            
            details_btn = QPushButton("详情")
            details_btn.clicked.connect(lambda checked, oid=order[0]: self.show_order_details(oid))
            action_layout.addWidget(details_btn)
            
            action_widget.setLayout(action_layout)
            self.orders_table.setCellWidget(row, 5, action_widget)
        
        self.orders_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
    
    def complete_order(self, order_id):
        """完成订单"""
        self.db.execute_query(
            "UPDATE orders SET status = 'completed', completed_at = CURRENT_TIMESTAMP WHERE id = ?",
            (order_id,)
        )
        self.load_orders()
        self.order_updated.emit()
        QMessageBox.information(self, "成功", f"订单 {order_id} 已完成")
    
    def show_order_details(self, order_id):
        """显示订单详情"""
        order_items = self.db.execute_query('''
            SELECT mi.name, oi.quantity, mi.price, oi.special_requests
            FROM order_items oi
            JOIN menu_items mi ON oi.menu_item_id = mi.id
            WHERE oi.order_id = ?
        ''', (order_id,))
        
        details = f"订单 #{order_id} 详情:\n\n"
        total = 0
        
        for item in order_items:
            subtotal = item[1] * item[2]
            total += subtotal
            details += f"{item[0]} x{item[1]} = ¥{subtotal:.2f}"
            if item[3]:
                details += f" (备注: {item[3]})"
            details += "\n"
        
        details += f"\n总计: ¥{total:.2f}"
        
        QMessageBox.information(self, "订单详情", details)


class InventoryManagerWidget(QWidget):
    """库存管理组件"""
    
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.init_ui()
        self.load_inventory()
    
    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout()
        
        # 工具栏
        toolbar = QHBoxLayout()
        self.add_btn = QPushButton("添加物品")
        self.add_btn.clicked.connect(self.show_add_dialog)
        
        self.low_stock_btn = QPushButton("低库存预警")
        self.low_stock_btn.clicked.connect(self.show_low_stock)
        
        toolbar.addWidget(self.add_btn)
        toolbar.addWidget(self.low_stock_btn)
        toolbar.addStretch()
        
        # 库存表格
        self.inventory_table = QTableWidget()
        self.inventory_table.setColumnCount(7)
        self.inventory_table.setHorizontalHeaderLabels([
            "物品名称", "类别", "数量", "单位", "最低阈值", "供应商", "操作"
        ])
        
        layout.addLayout(toolbar)
        layout.addWidget(self.inventory_table)
        self.setLayout(layout)
    
    def load_inventory(self):
        """加载库存数据"""
        inventory = self.db.execute_query("SELECT * FROM inventory ORDER BY item_name")
        self.update_table(inventory)
    
    def update_table(self, inventory):
        """更新表格显示"""
        self.inventory_table.setRowCount(len(inventory))
        
        for row, item in enumerate(inventory):
            self.inventory_table.setItem(row, 0, QTableWidgetItem(item[1]))
            self.inventory_table.setItem(row, 1, QTableWidgetItem(item[2]))
            self.inventory_table.setItem(row, 2, QTableWidgetItem(str(item[3])))
            self.inventory_table.setItem(row, 3, QTableWidgetItem(item[4]))
            self.inventory_table.setItem(row, 4, QTableWidgetItem(str(item[5])))
            self.inventory_table.setItem(row, 5, QTableWidgetItem(item[6] or ""))
            
            # 操作按钮
            action_widget = QWidget()
            action_layout = QHBoxLayout()
            action_layout.setContentsMargins(0, 0, 0, 0)
            
            edit_btn = QPushButton("编辑")
            edit_btn.clicked.connect(lambda checked, iid=item[0]: self.edit_item(iid))
            action_layout.addWidget(edit_btn)
            
            delete_btn = QPushButton("删除")
            delete_btn.clicked.connect(lambda checked, iid=item[0]: self.delete_item(iid))
            action_layout.addWidget(delete_btn)
            
            action_widget.setLayout(action_layout)
            self.inventory_table.setCellWidget(row, 6, action_widget)
            
            # 低库存高亮
            if item[3] <= item[5]:
                for col in range(6):
                    self.inventory_table.item(row, col).setBackground(QColor(255, 200, 200))
        
        self.inventory_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
    
    def show_add_dialog(self):
        """显示添加物品对话框"""
        dialog = QDialog(self)
        dialog.setWindowTitle("添加库存物品")
        dialog.setModal(True)
        
        layout = QGridLayout()
        
        layout.addWidget(QLabel("物品名称:"), 0, 0)
        name_edit = QLineEdit()
        layout.addWidget(name_edit, 0, 1)
        
        layout.addWidget(QLabel("类别:"), 1, 0)
        category_combo = QComboBox()
        category_combo.addItems(["蔬菜", "肉类", "海鲜", "调料", "饮料", "其他"])
        layout.addWidget(category_combo, 1, 1)
        
        layout.addWidget(QLabel("数量:"), 2, 0)
        quantity_edit = QDoubleSpinBox()
        quantity_edit.setMinimum(0)
        quantity_edit.setMaximum(9999)
        layout.addWidget(quantity_edit, 2, 1)
        
        layout.addWidget(QLabel("单位:"), 3, 0)
        unit_edit = QLineEdit()
        unit_edit.setText("个")
        layout.addWidget(unit_edit, 3, 1)
        
        layout.addWidget(QLabel("最低阈值:"), 4, 0)
        threshold_edit = QDoubleSpinBox()
        threshold_edit.setMinimum(0)
        threshold_edit.setMaximum(9999)
        layout.addWidget(threshold_edit, 4, 1)
        
        layout.addWidget(QLabel("供应商:"), 5, 0)
        supplier_edit = QLineEdit()
        layout.addWidget(supplier_edit, 5, 1)
        
        button_layout = QHBoxLayout()
        save_btn = QPushButton("保存")
        cancel_btn = QPushButton("取消")
        
        save_btn.clicked.connect(lambda: self.save_item(
            dialog, name_edit.text(), category_combo.currentText(),
            quantity_edit.value(), unit_edit.text(), threshold_edit.value(),
            supplier_edit.text()
        ))
        cancel_btn.clicked.connect(dialog.reject)
        
        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout, 6, 0, 1, 2)
        dialog.setLayout(layout)
        dialog.exec_()
    
    def save_item(self, dialog, name, category, quantity, unit, threshold, supplier):
        """保存物品"""
        if not name:
            QMessageBox.warning(self, "错误", "请输入物品名称")
            return
        
        self.db.execute_query('''
            INSERT INTO inventory (item_name, category, quantity, unit, min_threshold, supplier)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (name, category, quantity, unit, threshold, supplier))
        
        dialog.accept()
        self.load_inventory()
        QMessageBox.information(self, "成功", "物品已添加")
    
    def edit_item(self, item_id):
        """编辑物品"""
        # 实现编辑逻辑
        pass
    
    def delete_item(self, item_id):
        """删除物品"""
        reply = QMessageBox.question(
            self, "确认删除", 
            "确定要删除这个物品吗？",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.db.execute_query("DELETE FROM inventory WHERE id = ?", (item_id,))
            self.load_inventory()
    
    def show_low_stock(self):
        """显示低库存物品"""
        low_stock = self.db.execute_query(
            "SELECT * FROM inventory WHERE quantity <= min_threshold"
        )
        
        if not low_stock:
            QMessageBox.information(self, "库存状态", "没有低库存物品")
            return
        
        message = "以下物品库存不足:\n\n"
        for item in low_stock:
            message += f"{item[1]} - 当前: {item[3]}{item[4]}, 最低: {item[5]}{item[4]}\n"
        
        QMessageBox.warning(self, "低库存预警", message)


class AnalyticsDashboard(QWidget):
    """数据分析仪表板"""
    
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.analytics = AnalyticsEngine(db_manager)
        self.init_ui()
        self.load_data()
    
    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout()
        
        # 日期选择
        date_layout = QHBoxLayout()
        date_layout.addWidget(QLabel("开始日期:"))
        self.start_date = QDateEdit()
        self.start_date.setDate(QDate.currentDate().addDays(-30))
        date_layout.addWidget(self.start_date)
        
        date_layout.addWidget(QLabel("结束日期:"))
        self.end_date = QDateEdit()
        self.end_date.setDate(QDate.currentDate())
        date_layout.addWidget(self.end_date)
        
        update_btn = QPushButton("更新数据")
        update_btn.clicked.connect(self.load_data)
        date_layout.addWidget(update_btn)
        
        date_layout.addStretch()
        
        # 标签页
        self.tabs = QTabWidget()
        
        # 销售概览标签页
        self.sales_tab = QWidget()
        self.setup_sales_tab()
        self.tabs.addTab(self.sales_tab, "销售概览")
        
        # 热门菜品标签页
        self.popular_tab = QWidget()
        self.setup_popular_tab()
        self.tabs.addTab(self.popular_tab, "热门菜品")
        
        # 库存分析标签页
        self.inventory_tab = QWidget()
        self.setup_inventory_tab()
        self.tabs.addTab(self.inventory_tab, "库存分析")
        
        layout.addLayout(date_layout)
        layout.addWidget(self.tabs)
        self.setLayout(layout)
    
    def setup_sales_tab(self):
        """设置销售概览标签页"""
        layout = QVBoxLayout()
        
        # KPI 指标
        kpi_layout = QHBoxLayout()
        
        self.total_sales_label = QLabel("总销售额: 加载中...")
        self.total_sales_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        kpi_layout.addWidget(self.total_sales_label)
        
        self.avg_order_label = QLabel("平均订单: 加载中...")
        self.avg_order_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        kpi_layout.addWidget(self.avg_order_label)
        
        self.order_count_label = QLabel("订单数量: 加载中...")
        self.order_count_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        kpi_layout.addWidget(self.order_count_label)
        
        layout.addLayout(kpi_layout)
        
        # 图表区域
        chart_layout = QHBoxLayout()
        
        # 销售趋势图
        self.sales_chart_view = QChartView()
        chart_layout.addWidget(self.sales_chart_view)
        
        # 类别分布图
        self.category_chart_view = QChartView()
        chart_layout.addWidget(self.category_chart_view)
        
        layout.addLayout(chart_layout)
        self.sales_tab.setLayout(layout)
    
    def setup_popular_tab(self):
        """设置热门菜品标签页"""
        layout = QVBoxLayout()
        
        self.popular_table = QTableWidget()
        self.popular_table.setColumnCount(4)
        self.popular_table.setHorizontalHeaderLabels([
            "菜品名称", "类别", "销售数量", "销售额"
        ])
        
        layout.addWidget(self.popular_table)
        self.popular_tab.setLayout(layout)
    
    def setup_inventory_tab(self):
        """设置库存分析标签页"""
        layout = QVBoxLayout()
        
        self.inventory_table = QTableWidget()
        self.inventory_table.setColumnCount(5)
        self.inventory_table.setHorizontalHeaderLabels([
            "物品名称", "类别", "当前库存", "最低阈值", "状态"
        ])
        
        layout.addWidget(self.inventory_table)
        self.inventory_tab.setLayout(layout)
    
    def load_data(self):
        """加载数据"""
        start_date = self.start_date.date().toString("yyyy-MM-dd")
        end_date = self.end_date.date().toString("yyyy-MM-dd")
        
        # 加载销售数据
        sales_data = self.analytics.get_sales_report(start_date, end_date)
        self.update_sales_display(sales_data)
        
        # 加载热门菜品
        popular_items = self.analytics.get_popular_items()
        self.update_popular_display(popular_items)
        
        # 加载库存数据
        inventory = self.db.execute_query("SELECT * FROM inventory")
        self.update_inventory_display(inventory)
    
    def update_sales_display(self, sales_data):
        """更新销售数据显示"""
        if not sales_data:
            self.total_sales_label.setText("总销售额: ¥0.00")
            self.avg_order_label.setText("平均订单: ¥0.00")
            self.order_count_label.setText("订单数量: 0")
            return
        
        total_sales = sum(row[2] for row in sales_data)
        total_orders = sum(row[1] for row in sales_data)
        avg_order = total_sales / total_orders if total_orders > 0 else 0
        
        self.total_sales_label.setText(f"总销售额: ¥{total_sales:.2f}")
        self.avg_order_label.setText(f"平均订单: ¥{avg_order:.2f}")
        self.order_count_label.setText(f"订单数量: {total_orders}")
        
        # 创建销售趋势图表
        chart = QChart()
        chart.setTitle("销售趋势")
        
        series = QBarSeries()
        bar_set = QBarSet("日销售额")
        
        dates = []
        for row in sales_data:
            bar_set.append(row[2])
            dates.append(row[0][5:])  # 只显示月-日
        
        series.append(bar_set)
        chart.addSeries(series)
        
        axis_x = QBarCategoryAxis()
        axis_x.append(dates)
        chart.createDefaultAxes()
        chart.setAxisX(axis_x, series)
        
        self.sales_chart_view.setChart(chart)
    
    def update_popular_display(self, popular_items):
        """更新热门菜品显示"""
        self.popular_table.setRowCount(len(popular_items))
        
        for row, item in enumerate(popular_items):
            self.popular_table.setItem(row, 0, QTableWidgetItem(item[0]))
            self.popular_table.setItem(row, 1, QTableWidgetItem(item[1]))
            self.popular_table.setItem(row, 2, QTableWidgetItem(str(item[2])))
            self.popular_table.setItem(row, 3, QTableWidgetItem(f"¥{item[3]:.2f}"))
        
        self.popular_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
    
    def update_inventory_display(self, inventory):
        """更新库存显示"""
        self.inventory_table.setRowCount(len(inventory))
        
        for row, item in enumerate(inventory):
            self.inventory_table.setItem(row, 0, QTableWidgetItem(item[1]))
            self.inventory_table.setItem(row, 1, QTableWidgetItem(item[2]))
            self.inventory_table.setItem(row, 2, QTableWidgetItem(str(item[3])))
            self.inventory_table.setItem(row, 3, QTableWidgetItem(str(item[5])))
            
            status = "充足" if item[3] > item[5] else "不足"
            status_item = QTableWidgetItem(status)
            
            if status == "不足":
                status_item.setBackground(QColor(255, 200, 200))
            
            self.inventory_table.setItem(row, 4, status_item)
        
        self.inventory_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)


class SmartRestaurantSystem(QMainWindow):
    """智能餐馆系统主窗口"""
    
    def __init__(self):
        super().__init__()
        self.db = DatabaseManager()
        self.init_ui()
        
        # 创建系统托盘图标
        self.create_system_tray()
    
    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("智能餐馆管理系统")
        self.setGeometry(100, 100, 1200, 800)
        
        # 创建中心部件
        central_widget = QTabWidget()
        self.setCentralWidget(central_widget)
        
        # 订单管理标签页
        self.order_manager = OrderManagerWidget(self.db)
        central_widget.addTab(self.order_manager, "订单管理")
        
        # 库存管理标签页
        self.inventory_manager = InventoryManagerWidget(self.db)
        central_widget.addTab(self.inventory_manager, "库存管理")
        
        # 数据分析标签页
        self.analytics_dashboard = AnalyticsDashboard(self.db)
        central_widget.addTab(self.analytics_dashboard, "数据分析")
        
        # 创建菜单栏
        self.create_menu_bar()
        
        # 创建状态栏
        self.statusBar().showMessage("系统就绪")
    
    def create_menu_bar(self):
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
        
        qr_action = QAction('生成餐桌二维码', self)
        qr_action.triggered.connect(self.generate_table_qr_codes)
        tools_menu.addAction(qr_action)
        
        backup_action = QAction('备份数据', self)
        backup_action.triggered.connect(self.backup_data)
        tools_menu.addAction(backup_action)
    
    def create_system_tray(self):
        """创建系统托盘图标"""
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.style().standardIcon(QStyle.SP_ComputerIcon))
        
        tray_menu = QMenu()
        
        show_action = tray_menu.addAction("显示主窗口")
        show_action.triggered.connect(self.show)
        
        hide_action = tray_menu.addAction("隐藏到托盘")
        hide_action.triggered.connect(self.hide)
        
        quit_action = tray_menu.addAction("退出")
        quit_action.triggered.connect(QApplication.quit)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.tray_icon_activated)
        self.tray_icon.show()
    
    def tray_icon_activated(self, reason):
        """托盘图标激活事件"""
        if reason == QSystemTrayIcon.DoubleClick:
            if self.isVisible():
                self.hide()
            else:
                self.show()
                self.activateWindow()
    
    def closeEvent(self, event):
        """关闭事件处理"""
        if self.tray_icon.isVisible():
            QMessageBox.information(self, "系统提示", 
                                  "程序将继续在系统托盘中运行")
            self.hide()
            event.ignore()
        else:
            event.accept()
    
    def export_data(self):
        """导出数据"""
        # 实现数据导出逻辑
        QMessageBox.information(self, "导出数据", "数据导出功能开发中...")
    
    def generate_table_qr_codes(self):
        """生成餐桌二维码"""
        # 实现二维码生成逻辑
        QMessageBox.information(self, "二维码生成", "二维码生成功能开发中...")
    
    def backup_data(self):
        """备份数据"""
        # 实现数据备份逻辑
        QMessageBox.information(self, "数据备份", "数据备份功能开发中...")


def main():
    """主函数"""
    app = QApplication(sys.argv)
    
    # 设置应用程序样式
    app.setStyle('Fusion')
    
    # 创建并显示主窗口
    window = SmartRestaurantSystem()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()