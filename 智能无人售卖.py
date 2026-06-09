import sys
import json
import sqlite3
import datetime
from typing import Dict, List, Optional, Tuple
from decimal import Decimal

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QGridLayout, QLabel, QPushButton, 
                            QTableWidget, QTableWidgetItem, QLineEdit, 
                            QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox,
                            QMessageBox, QTabWidget, QProgressBar, QGroupBox,
                            QHeaderView, QSplitter, QFrame, QListWidget,
                            QListWidgetItem, QDialog, QDialogButtonBox)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread, pyqtSlot
from PyQt5.QtGui import QFont, QPixmap, QIcon, QPainter, QColor
from PyQt5.QtChart import QChart, QChartView, QPieSeries, QBarSeries, QBarSet, QBarCategoryAxis, QValueAxis

# 数据库管理类
class DatabaseManager:
    def __init__(self, db_path: str = "vending_machine.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """初始化数据库表结构"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 商品表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                price DECIMAL(10,2) NOT NULL,
                stock INTEGER NOT NULL,
                category TEXT,
                image_path TEXT,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 销售记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sales (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER,
                quantity INTEGER NOT NULL,
                total_price DECIMAL(10,2) NOT NULL,
                payment_method TEXT,
                sale_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (product_id) REFERENCES products (id)
            )
        ''')
        
        # 库存变更记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS inventory_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER,
                change_amount INTEGER NOT NULL,
                reason TEXT,
                log_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (product_id) REFERENCES products (id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def execute_query(self, query: str, params: tuple = ()) -> list:
        """执行查询并返回结果"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(query, params)
        result = cursor.fetchall()
        conn.close()
        return result
    
    def execute_update(self, query: str, params: tuple = ()) -> int:
        """执行更新操作并返回影响的行数"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        row_count = cursor.rowcount
        conn.close()
        return row_count

# 商品管理类
class ProductManager:
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def add_product(self, name: str, price: Decimal, stock: int, 
                   category: str = "", image_path: str = "", description: str = "") -> bool:
        """添加新商品"""
        try:
            query = """
                INSERT INTO products (name, price, stock, category, image_path, description)
                VALUES (?, ?, ?, ?, ?, ?)
            """
            self.db.execute_update(query, (name, float(price), stock, category, image_path, description))
            return True
        except Exception as e:
            print(f"添加商品失败: {e}")
            return False
    
    def update_product(self, product_id: int, name: str = None, price: Decimal = None, 
                      stock: int = None, category: str = None) -> bool:
        """更新商品信息"""
        try:
            updates = []
            params = []
            
            if name is not None:
                updates.append("name = ?")
                params.append(name)
            if price is not None:
                updates.append("price = ?")
                params.append(float(price))
            if stock is not None:
                updates.append("stock = ?")
                params.append(stock)
            if category is not None:
                updates.append("category = ?")
                params.append(category)
            
            if not updates:
                return False
                
            query = f"UPDATE products SET {', '.join(updates)} WHERE id = ?"
            params.append(product_id)
            
            self.db.execute_update(query, tuple(params))
            return True
        except Exception as e:
            print(f"更新商品失败: {e}")
            return False
    
    def get_all_products(self) -> List[Dict]:
        """获取所有商品"""
        query = "SELECT * FROM products ORDER BY name"
        results = self.db.execute_query(query)
        
        products = []
        for row in results:
            products.append({
                'id': row[0],
                'name': row[1],
                'price': Decimal(str(row[2])),
                'stock': row[3],
                'category': row[4],
                'image_path': row[5],
                'description': row[6],
                'created_at': row[7]
            })
        
        return products
    
    def get_product_by_id(self, product_id: int) -> Optional[Dict]:
        """根据ID获取商品"""
        query = "SELECT * FROM products WHERE id = ?"
        results = self.db.execute_query(query, (product_id,))
        
        if results:
            row = results[0]
            return {
                'id': row[0],
                'name': row[1],
                'price': Decimal(str(row[2])),
                'stock': row[3],
                'category': row[4],
                'image_path': row[5],
                'description': row[6],
                'created_at': row[7]
            }
        return None
    
    def update_stock(self, product_id: int, change: int, reason: str = "销售") -> bool:
        """更新商品库存"""
        try:
            # 更新商品库存
            query = "UPDATE products SET stock = stock + ? WHERE id = ?"
            self.db.execute_update(query, (change, product_id))
            
            # 记录库存变更
            log_query = "INSERT INTO inventory_logs (product_id, change_amount, reason) VALUES (?, ?, ?)"
            self.db.execute_update(log_query, (product_id, change, reason))
            
            return True
        except Exception as e:
            print(f"更新库存失败: {e}")
            return False

# 销售管理类
class SalesManager:
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def record_sale(self, product_id: int, quantity: int, total_price: Decimal, 
                   payment_method: str = "现金") -> bool:
        """记录销售"""
        try:
            query = """
                INSERT INTO sales (product_id, quantity, total_price, payment_method)
                VALUES (?, ?, ?, ?)
            """
            self.db.execute_update(query, (product_id, quantity, float(total_price), payment_method))
            return True
        except Exception as e:
            print(f"记录销售失败: {e}")
            return False
    
    def get_sales_report(self, start_date: str = None, end_date: str = None) -> Dict:
        """获取销售报告"""
        query = """
            SELECT p.name, SUM(s.quantity), SUM(s.total_price), COUNT(s.id)
            FROM sales s
            JOIN products p ON s.product_id = p.id
        """
        params = []
        
        if start_date and end_date:
            query += " WHERE s.sale_time BETWEEN ? AND ?"
            params.extend([start_date, end_date])
        
        query += " GROUP BY p.name ORDER BY SUM(s.total_price) DESC"
        
        results = self.db.execute_query(query, tuple(params))
        
        report = {
            'total_sales': 0,
            'total_revenue': Decimal('0'),
            'products': []
        }
        
        for row in results:
            product_sales = {
                'name': row[0],
                'quantity': row[1],
                'revenue': Decimal(str(row[2])),
                'transactions': row[3]
            }
            report['products'].append(product_sales)
            report['total_sales'] += row[1]
            report['total_revenue'] += Decimal(str(row[2]))
        
        return report
    
    def get_daily_sales(self, days: int = 30) -> List[Dict]:
        """获取最近N天的每日销售数据"""
        query = """
            SELECT DATE(sale_time), SUM(total_price), COUNT(id)
            FROM sales
            WHERE sale_time >= date('now', ?)
            GROUP BY DATE(sale_time)
            ORDER BY DATE(sale_time)
        """
        results = self.db.execute_query(query, (f'-{days} days',))
        
        daily_sales = []
        for row in results:
            daily_sales.append({
                'date': row[0],
                'revenue': Decimal(str(row[1])),
                'transactions': row[2]
            })
        
        return daily_sales

# 支付处理类
class PaymentProcessor:
    def __init__(self):
        self.supported_methods = ["现金", "微信支付", "支付宝", "银行卡"]
    
    def process_payment(self, amount: Decimal, method: str) -> Tuple[bool, str]:
        """处理支付"""
        if method not in self.supported_methods:
            return False, f"不支持的支付方式: {method}"
        
        # 模拟支付处理
        # 在实际应用中，这里会调用相应的支付API
        if method == "现金":
            return self.process_cash_payment(amount)
        elif method == "微信支付":
            return self.process_wechat_payment(amount)
        elif method == "支付宝":
            return self.process_alipay_payment(amount)
        elif method == "银行卡":
            return self.process_card_payment(amount)
    
    def process_cash_payment(self, amount: Decimal) -> Tuple[bool, str]:
        """处理现金支付"""
        # 模拟现金支付处理
        QTimer.singleShot(2000, lambda: None)  # 模拟2秒处理时间
        return True, "现金支付成功"
    
    def process_wechat_payment(self, amount: Decimal) -> Tuple[bool, str]:
        """处理微信支付"""
        # 模拟微信支付处理
        QTimer.singleShot(3000, lambda: None)  # 模拟3秒处理时间
        return True, "微信支付成功"
    
    def process_alipay_payment(self, amount: Decimal) -> Tuple[bool, str]:
        """处理支付宝支付"""
        # 模拟支付宝支付处理
        QTimer.singleShot(3000, lambda: None)  # 模拟3秒处理时间
        return True, "支付宝支付成功"
    
    def process_card_payment(self, amount: Decimal) -> Tuple[bool, str]:
        """处理银行卡支付"""
        # 模拟银行卡支付处理
        QTimer.singleShot(2500, lambda: None)  # 模拟2.5秒处理时间
        return True, "银行卡支付成功"

# 自定义组件 - 商品卡片
class ProductCard(QFrame):
    clicked = pyqtSignal(int)  # 商品ID
    
    def __init__(self, product: Dict):
        super().__init__()
        self.product = product
        self.init_ui()
    
    def init_ui(self):
        self.setFrameStyle(QFrame.Box)
        self.setLineWidth(1)
        self.setFixedSize(150, 180)
        
        layout = QVBoxLayout()
        
        # 商品图片
        image_label = QLabel()
        if self.product['image_path']:
            pixmap = QPixmap(self.product['image_path'])
            if not pixmap.isNull():
                pixmap = pixmap.scaled(100, 100, Qt.KeepAspectRatio)
                image_label.setPixmap(pixmap)
        else:
            image_label.setText("暂无图片")
            image_label.setAlignment(Qt.AlignCenter)
        
        image_label.setFixedSize(100, 100)
        image_label.setStyleSheet("border: 1px solid #ccc;")
        
        # 商品名称
        name_label = QLabel(self.product['name'])
        name_label.setAlignment(Qt.AlignCenter)
        name_label.setWordWrap(True)
        
        # 商品价格
        price_label = QLabel(f"¥{self.product['price']}")
        price_label.setAlignment(Qt.AlignCenter)
        price_label.setStyleSheet("color: #e74c3c; font-weight: bold;")
        
        # 库存信息
        stock_label = QLabel(f"库存: {self.product['stock']}")
        stock_label.setAlignment(Qt.AlignCenter)
        if self.product['stock'] <= 0:
            stock_label.setStyleSheet("color: #e74c3c;")
        elif self.product['stock'] < 10:
            stock_label.setStyleSheet("color: #f39c12;")
        else:
            stock_label.setStyleSheet("color: #27ae60;")
        
        layout.addWidget(image_label, 0, Qt.AlignCenter)
        layout.addWidget(name_label)
        layout.addWidget(price_label)
        layout.addWidget(stock_label)
        
        self.setLayout(layout)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.product['id'])

# 自定义组件 - 购物车项
class CartItemWidget(QWidget):
    quantity_changed = pyqtSignal(int, int)  # 商品ID, 新数量
    removed = pyqtSignal(int)  # 商品ID
    
    def __init__(self, product: Dict, quantity: int):
        super().__init__()
        self.product = product
        self.quantity = quantity
        self.init_ui()
    
    def init_ui(self):
        layout = QHBoxLayout()
        
        # 商品名称
        name_label = QLabel(self.product['name'])
        name_label.setMinimumWidth(150)
        
        # 单价
        price_label = QLabel(f"¥{self.product['price']}")
        price_label.setMinimumWidth(60)
        
        # 数量控制
        quantity_layout = QHBoxLayout()
        quantity_label = QLabel("数量:")
        
        quantity_spin = QSpinBox()
        quantity_spin.setMinimum(1)
        quantity_spin.setMaximum(self.product['stock'])
        quantity_spin.setValue(self.quantity)
        quantity_spin.valueChanged.connect(self.on_quantity_changed)
        
        quantity_layout.addWidget(quantity_label)
        quantity_layout.addWidget(quantity_spin)
        
        # 小计
        subtotal = self.product['price'] * self.quantity
        subtotal_label = QLabel(f"¥{subtotal}")
        subtotal_label.setMinimumWidth(80)
        subtotal_label.setStyleSheet("color: #e74c3c; font-weight: bold;")
        
        # 删除按钮
        remove_btn = QPushButton("删除")
        remove_btn.clicked.connect(self.on_remove)
        
        layout.addWidget(name_label)
        layout.addWidget(price_label)
        layout.addLayout(quantity_layout)
        layout.addWidget(subtotal_label)
        layout.addWidget(remove_btn)
        
        self.setLayout(layout)
    
    def on_quantity_changed(self, value):
        self.quantity = value
        self.quantity_changed.emit(self.product['id'], value)
    
    def on_remove(self):
        self.removed.emit(self.product['id'])

# 数据分析图表组件
class SalesChartWidget(QWidget):
    def __init__(self, sales_manager: SalesManager):
        super().__init__()
        self.sales_manager = sales_manager
        self.init_ui()
        self.load_data()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 图表标题
        title_label = QLabel("销售数据分析")
        title_label.setFont(QFont("Arial", 16, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        
        # 图表视图
        self.chart_view = QChartView()
        self.chart_view.setRenderHint(QPainter.Antialiasing)
        
        layout.addWidget(title_label)
        layout.addWidget(self.chart_view)
        
        self.setLayout(layout)
    
    def load_data(self):
        # 获取销售数据
        report = self.sales_manager.get_sales_report()
        
        # 创建饼图显示各商品销售占比
        series = QPieSeries()
        
        for product in report['products'][:5]:  # 只显示前5个商品
            slice = series.append(f"{product['name']}\n¥{product['revenue']}", 
                                float(product['revenue']))
            slice.setLabelVisible(True)
        
        # 创建图表
        chart = QChart()
        chart.addSeries(series)
        chart.setTitle("商品销售占比")
        chart.setAnimationOptions(QChart.SeriesAnimations)
        
        self.chart_view.setChart(chart)

# 主界面 - 智能无人售卖系统
class SmartVendingSystem(QMainWindow):
    def __init__(self):
        super().__init__()
        self.db_manager = DatabaseManager()
        self.product_manager = ProductManager(self.db_manager)
        self.sales_manager = SalesManager(self.db_manager)
        self.payment_processor = PaymentProcessor()
        
        self.cart = {}  # 购物车: {product_id: quantity}
        
        self.init_ui()
        self.load_products()
    
    def init_ui(self):
        self.setWindowTitle("智能无人售卖系统")
        self.setGeometry(100, 100, 1200, 800)
        
        # 创建中央部件和主布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout()
        central_widget.setLayout(main_layout)
        
        # 创建左侧商品展示区域
        left_widget = self.create_product_display()
        left_widget.setMinimumWidth(800)
        
        # 创建右侧购物车和支付区域
        right_widget = self.create_cart_and_payment()
        right_widget.setMinimumWidth(350)
        
        # 使用分割器
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([800, 350])
        
        main_layout.addWidget(splitter)
    
    def create_product_display(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout()
        
        # 标题
        title_label = QLabel("商品选择")
        title_label.setFont(QFont("Arial", 18, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        
        # 分类筛选
        filter_layout = QHBoxLayout()
        filter_label = QLabel("分类筛选:")
        self.category_combo = QComboBox()
        self.category_combo.addItem("所有分类")
        self.category_combo.currentTextChanged.connect(self.filter_products)
        
        filter_layout.addWidget(filter_label)
        filter_layout.addWidget(self.category_combo)
        filter_layout.addStretch()
        
        # 商品网格
        self.product_grid = QGridLayout()
        self.product_grid_widget = QWidget()
        self.product_grid_widget.setLayout(self.product_grid)
        
        # 滚动区域
        from PyQt5.QtWidgets import QScrollArea
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(self.product_grid_widget)
        
        layout.addWidget(title_label)
        layout.addLayout(filter_layout)
        layout.addWidget(scroll_area)
        
        widget.setLayout(layout)
        return widget
    
    def create_cart_and_payment(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout()
        
        # 购物车标题
        cart_title = QLabel("购物车")
        cart_title.setFont(QFont("Arial", 16, QFont.Bold))
        cart_title.setAlignment(Qt.AlignCenter)
        
        # 购物车内容
        self.cart_list = QListWidget()
        
        # 总计
        total_layout = QHBoxLayout()
        total_label = QLabel("总计:")
        self.total_amount_label = QLabel("¥0.00")
        self.total_amount_label.setFont(QFont("Arial", 18, QFont.Bold))
        self.total_amount_label.setStyleSheet("color: #e74c3c;")
        
        total_layout.addWidget(total_label)
        total_layout.addWidget(self.total_amount_label)
        total_layout.addStretch()
        
        # 支付方式选择
        payment_layout = QVBoxLayout()
        payment_label = QLabel("选择支付方式:")
        self.payment_combo = QComboBox()
        self.payment_combo.addItems(self.payment_processor.supported_methods)
        
        payment_layout.addWidget(payment_label)
        payment_layout.addWidget(self.payment_combo)
        
        # 支付按钮
        self.pay_button = QPushButton("立即支付")
        self.pay_button.setFont(QFont("Arial", 14, QFont.Bold))
        self.pay_button.setStyleSheet("background-color: #27ae60; color: white; padding: 10px;")
        self.pay_button.clicked.connect(self.process_payment)
        
        # 管理按钮
        manage_buttons_layout = QHBoxLayout()
        inventory_btn = QPushButton("库存管理")
        inventory_btn.clicked.connect(self.show_inventory_management)
        
        reports_btn = QPushButton("销售报告")
        reports_btn.clicked.connect(self.show_sales_reports)
        
        manage_buttons_layout.addWidget(inventory_btn)
        manage_buttons_layout.addWidget(reports_btn)
        
        layout.addWidget(cart_title)
        layout.addWidget(self.cart_list)
        layout.addLayout(total_layout)
        layout.addLayout(payment_layout)
        layout.addWidget(self.pay_button)
        layout.addLayout(manage_buttons_layout)
        layout.addStretch()
        
        widget.setLayout(layout)
        return widget
    
    def load_products(self):
        # 清空现有商品
        for i in reversed(range(self.product_grid.count())): 
            self.product_grid.itemAt(i).widget().setParent(None)
        
        # 获取商品数据
        products = self.product_manager.get_all_products()
        
        # 更新分类筛选器
        current_category = self.category_combo.currentText()
        self.category_combo.blockSignals(True)
        self.category_combo.clear()
        self.category_combo.addItem("所有分类")
        
        categories = set(product['category'] for product in products if product['category'])
        for category in categories:
            self.category_combo.addItem(category)
        
        if current_category in [self.category_combo.itemText(i) for i in range(self.category_combo.count())]:
            self.category_combo.setCurrentText(current_category)
        else:
            self.category_combo.setCurrentText("所有分类")
        
        self.category_combo.blockSignals(False)
        
        # 添加商品卡片到网格
        row, col = 0, 0
        max_cols = 4
        
        for product in products:
            # 分类筛选
            if self.category_combo.currentText() != "所有分类" and product['category'] != self.category_combo.currentText():
                continue
            
            # 创建商品卡片
            card = ProductCard(product)
            card.clicked.connect(self.add_to_cart)
            
            self.product_grid.addWidget(card, row, col)
            
            col += 1
            if col >= max_cols:
                col = 0
                row += 1
    
    def filter_products(self):
        self.load_products()
    
    def add_to_cart(self, product_id):
        product = self.product_manager.get_product_by_id(product_id)
        
        if not product:
            QMessageBox.warning(self, "错误", "商品不存在!")
            return
        
        if product['stock'] <= 0:
            QMessageBox.warning(self, "库存不足", "该商品已售罄!")
            return
        
        # 添加到购物车或增加数量
        if product_id in self.cart:
            if self.cart[product_id] < product['stock']:
                self.cart[product_id] += 1
            else:
                QMessageBox.warning(self, "库存不足", "已达到库存上限!")
                return
        else:
            self.cart[product_id] = 1
        
        self.update_cart_display()
    
    def update_cart_display(self):
        # 清空购物车显示
        self.cart_list.clear()
        
        # 计算总金额
        total = Decimal('0')
        
        # 添加购物车项
        for product_id, quantity in self.cart.items():
            product = self.product_manager.get_product_by_id(product_id)
            if product:
                item_widget = CartItemWidget(product, quantity)
                item_widget.quantity_changed.connect(self.update_cart_quantity)
                item_widget.removed.connect(self.remove_from_cart)
                
                list_item = QListWidgetItem()
                list_item.setSizeHint(item_widget.sizeHint())
                
                self.cart_list.addItem(list_item)
                self.cart_list.setItemWidget(list_item, item_widget)
                
                total += product['price'] * quantity
        
        # 更新总金额
        self.total_amount_label.setText(f"¥{total}")
        
        # 更新支付按钮状态
        self.pay_button.setEnabled(len(self.cart) > 0)
    
    def update_cart_quantity(self, product_id, quantity):
        product = self.product_manager.get_product_by_id(product_id)
        
        if product and quantity <= product['stock']:
            self.cart[product_id] = quantity
            self.update_cart_display()
        else:
            QMessageBox.warning(self, "库存不足", "库存不足，无法添加更多!")
    
    def remove_from_cart(self, product_id):
        if product_id in self.cart:
            del self.cart[product_id]
            self.update_cart_display()
    
    def process_payment(self):
        if not self.cart:
            QMessageBox.warning(self, "错误", "购物车为空!")
            return
        
        # 计算总金额
        total = Decimal('0')
        for product_id, quantity in self.cart.items():
            product = self.product_manager.get_product_by_id(product_id)
            if product:
                total += product['price'] * quantity
        
        # 获取支付方式
        payment_method = self.payment_combo.currentText()
        
        # 处理支付
        success, message = self.payment_processor.process_payment(total, payment_method)
        
        if success:
            # 记录销售并更新库存
            for product_id, quantity in self.cart.items():
                product = self.product_manager.get_product_by_id(product_id)
                if product:
                    # 记录销售
                    self.sales_manager.record_sale(product_id, quantity, product['price'] * quantity, payment_method)
                    
                    # 更新库存
                    self.product_manager.update_stock(product_id, -quantity, "销售")
            
            # 清空购物车
            self.cart.clear()
            self.update_cart_display()
            
            QMessageBox.information(self, "支付成功", f"{message}\n感谢您的购买!")
        else:
            QMessageBox.warning(self, "支付失败", message)
    
    def show_inventory_management(self):
        dialog = InventoryManagementDialog(self.product_manager, self)
        dialog.exec_()
        self.load_products()  # 刷新商品显示
    
    def show_sales_reports(self):
        dialog = SalesReportDialog(self.sales_manager, self)
        dialog.exec_()

# 库存管理对话框
class InventoryManagementDialog(QDialog):
    def __init__(self, product_manager: ProductManager, parent=None):
        super().__init__(parent)
        self.product_manager = product_manager
        self.init_ui()
        self.load_products()
    
    def init_ui(self):
        self.setWindowTitle("库存管理")
        self.setGeometry(200, 200, 800, 600)
        
        layout = QVBoxLayout()
        
        # 标题
        title_label = QLabel("库存管理")
        title_label.setFont(QFont("Arial", 16, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        
        # 产品表格
        self.products_table = QTableWidget()
        self.products_table.setColumnCount(6)
        self.products_table.setHorizontalHeaderLabels(["ID", "名称", "价格", "库存", "分类", "操作"])
        self.products_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        # 添加商品按钮
        add_product_btn = QPushButton("添加新商品")
        add_product_btn.clicked.connect(self.show_add_product_dialog)
        
        layout.addWidget(title_label)
        layout.addWidget(self.products_table)
        layout.addWidget(add_product_btn)
        
        self.setLayout(layout)
    
    def load_products(self):
        products = self.product_manager.get_all_products()
        
        self.products_table.setRowCount(len(products))
        
        for row, product in enumerate(products):
            # ID
            self.products_table.setItem(row, 0, QTableWidgetItem(str(product['id'])))
            
            # 名称
            self.products_table.setItem(row, 1, QTableWidgetItem(product['name']))
            
            # 价格
            self.products_table.setItem(row, 2, QTableWidgetItem(f"¥{product['price']}"))
            
            # 库存
            stock_item = QTableWidgetItem(str(product['stock']))
            if product['stock'] <= 0:
                stock_item.setBackground(QColor(255, 200, 200))  # 红色背景表示缺货
            elif product['stock'] < 10:
                stock_item.setBackground(QColor(255, 255, 200))  # 黄色背景表示库存低
            self.products_table.setItem(row, 3, stock_item)
            
            # 分类
            self.products_table.setItem(row, 4, QTableWidgetItem(product['category'] or ""))
            
            # 操作按钮
            button_widget = QWidget()
            button_layout = QHBoxLayout()
            button_layout.setContentsMargins(5, 5, 5, 5)
            
            edit_btn = QPushButton("编辑")
            edit_btn.clicked.connect(lambda checked, p=product: self.edit_product(p))
            
            stock_btn = QPushButton("调整库存")
            stock_btn.clicked.connect(lambda checked, p=product: self.adjust_stock(p))
            
            button_layout.addWidget(edit_btn)
            button_layout.addWidget(stock_btn)
            button_widget.setLayout(button_layout)
            
            self.products_table.setCellWidget(row, 5, button_widget)
    
    def show_add_product_dialog(self):
        dialog = AddProductDialog(self.product_manager, self)
        if dialog.exec_() == QDialog.Accepted:
            self.load_products()  # 刷新表格
    
    def edit_product(self, product):
        dialog = EditProductDialog(self.product_manager, product, self)
        if dialog.exec_() == QDialog.Accepted:
            self.load_products()  # 刷新表格
    
    def adjust_stock(self, product):
        dialog = AdjustStockDialog(self.product_manager, product, self)
        if dialog.exec_() == QDialog.Accepted:
            self.load_products()  # 刷新表格

# 添加商品对话框
class AddProductDialog(QDialog):
    def __init__(self, product_manager: ProductManager, parent=None):
        super().__init__(parent)
        self.product_manager = product_manager
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("添加新商品")
        self.setModal(True)
        
        layout = QVBoxLayout()
        
        # 表单
        form_layout = QGridLayout()
        
        # 商品名称
        form_layout.addWidget(QLabel("商品名称:"), 0, 0)
        self.name_edit = QLineEdit()
        form_layout.addWidget(self.name_edit, 0, 1)
        
        # 价格
        form_layout.addWidget(QLabel("价格:"), 1, 0)
        self.price_spin = QDoubleSpinBox()
        self.price_spin.setMinimum(0.01)
        self.price_spin.setMaximum(9999.99)
        self.price_spin.setDecimals(2)
        self.price_spin.setPrefix("¥")
        form_layout.addWidget(self.price_spin, 1, 1)
        
        # 库存
        form_layout.addWidget(QLabel("初始库存:"), 2, 0)
        self.stock_spin = QSpinBox()
        self.stock_spin.setMinimum(0)
        self.stock_spin.setMaximum(9999)
        form_layout.addWidget(self.stock_spin, 2, 1)
        
        # 分类
        form_layout.addWidget(QLabel("分类:"), 3, 0)
        self.category_edit = QLineEdit()
        form_layout.addWidget(self.category_edit, 3, 1)
        
        # 描述
        form_layout.addWidget(QLabel("描述:"), 4, 0)
        self.description_edit = QTextEdit()
        self.description_edit.setMaximumHeight(100)
        form_layout.addWidget(self.description_edit, 4, 1)
        
        layout.addLayout(form_layout)
        
        # 按钮
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        
        layout.addWidget(button_box)
        
        self.setLayout(layout)
    
    def accept(self):
        # 验证输入
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "输入错误", "请输入商品名称!")
            return
        
        # 添加商品
        success = self.product_manager.add_product(
            name=self.name_edit.text().strip(),
            price=Decimal(str(self.price_spin.value())),
            stock=self.stock_spin.value(),
            category=self.category_edit.text().strip(),
            description=self.description_edit.toPlainText().strip()
        )
        
        if success:
            QMessageBox.information(self, "成功", "商品添加成功!")
            super().accept()
        else:
            QMessageBox.warning(self, "错误", "添加商品失败!")

# 编辑商品对话框
class EditProductDialog(QDialog):
    def __init__(self, product_manager: ProductManager, product: Dict, parent=None):
        super().__init__(parent)
        self.product_manager = product_manager
        self.product = product
        self.init_ui()
        self.load_product_data()
    
    def init_ui(self):
        self.setWindowTitle("编辑商品")
        self.setModal(True)
        
        layout = QVBoxLayout()
        
        # 表单
        form_layout = QGridLayout()
        
        # 商品名称
        form_layout.addWidget(QLabel("商品名称:"), 0, 0)
        self.name_edit = QLineEdit()
        form_layout.addWidget(self.name_edit, 0, 1)
        
        # 价格
        form_layout.addWidget(QLabel("价格:"), 1, 0)
        self.price_spin = QDoubleSpinBox()
        self.price_spin.setMinimum(0.01)
        self.price_spin.setMaximum(9999.99)
        self.price_spin.setDecimals(2)
        self.price_spin.setPrefix("¥")
        form_layout.addWidget(self.price_spin, 1, 1)
        
        # 分类
        form_layout.addWidget(QLabel("分类:"), 2, 0)
        self.category_edit = QLineEdit()
        form_layout.addWidget(self.category_edit, 2, 1)
        
        layout.addLayout(form_layout)
        
        # 按钮
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        
        layout.addWidget(button_box)
        
        self.setLayout(layout)
    
    def load_product_data(self):
        self.name_edit.setText(self.product['name'])
        self.price_spin.setValue(float(self.product['price']))
        self.category_edit.setText(self.product['category'] or "")
    
    def accept(self):
        # 验证输入
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "输入错误", "请输入商品名称!")
            return
        
        # 更新商品
        success = self.product_manager.update_product(
            product_id=self.product['id'],
            name=self.name_edit.text().strip(),
            price=Decimal(str(self.price_spin.value())),
            category=self.category_edit.text().strip()
        )
        
        if success:
            QMessageBox.information(self, "成功", "商品更新成功!")
            super().accept()
        else:
            QMessageBox.warning(self, "错误", "更新商品失败!")

# 调整库存对话框
class AdjustStockDialog(QDialog):
    def __init__(self, product_manager: ProductManager, product: Dict, parent=None):
        super().__init__(parent)
        self.product_manager = product_manager
        self.product = product
        self.init_ui()
        self.load_product_data()
    
    def init_ui(self):
        self.setWindowTitle("调整库存")
        self.setModal(True)
        
        layout = QVBoxLayout()
        
        # 商品信息
        info_layout = QVBoxLayout()
        info_layout.addWidget(QLabel(f"商品: {self.product['name']}"))
        info_layout.addWidget(QLabel(f"当前库存: {self.product['stock']}"))
        
        # 调整选项
        adjust_layout = QHBoxLayout()
        adjust_layout.addWidget(QLabel("调整类型:"))
        
        self.adjust_type_combo = QComboBox()
        self.adjust_type_combo.addItems(["增加库存", "减少库存", "设置库存"])
        self.adjust_type_combo.currentTextChanged.connect(self.on_adjust_type_changed)
        
        adjust_layout.addWidget(self.adjust_type_combo)
        
        # 调整数量
        quantity_layout = QHBoxLayout()
        quantity_layout.addWidget(QLabel("数量:"))
        
        self.quantity_spin = QSpinBox()
        self.quantity_spin.setMinimum(1)
        self.quantity_spin.setMaximum(9999)
        
        quantity_layout.addWidget(self.quantity_spin)
        
        # 原因
        reason_layout = QHBoxLayout()
        reason_layout.addWidget(QLabel("原因:"))
        
        self.reason_edit = QLineEdit()
        self.reason_edit.setPlaceholderText("例如: 采购入库、盘点调整等")
        
        reason_layout.addWidget(self.reason_edit)
        
        layout.addLayout(info_layout)
        layout.addLayout(adjust_layout)
        layout.addLayout(quantity_layout)
        layout.addLayout(reason_layout)
        
        # 按钮
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        
        layout.addWidget(button_box)
        
        self.setLayout(layout)
    
    def load_product_data(self):
        # 初始化界面数据
        pass
    
    def on_adjust_type_changed(self, text):
        if text == "减少库存":
            self.quantity_spin.setMaximum(self.product['stock'])
        else:
            self.quantity_spin.setMaximum(9999)
    
    def accept(self):
        # 确定调整数量
        quantity = self.quantity_spin.value()
        adjust_type = self.adjust_type_combo.currentText()
        reason = self.reason_edit.text().strip() or "手动调整"
        
        if adjust_type == "增加库存":
            change = quantity
        elif adjust_type == "减少库存":
            change = -quantity
        else:  # 设置库存
            change = quantity - self.product['stock']
        
        # 更新库存
        success = self.product_manager.update_stock(
            product_id=self.product['id'],
            change=change,
            reason=reason
        )
        
        if success:
            QMessageBox.information(self, "成功", "库存调整成功!")
            super().accept()
        else:
            QMessageBox.warning(self, "错误", "库存调整失败!")

# 销售报告对话框
class SalesReportDialog(QDialog):
    def __init__(self, sales_manager: SalesManager, parent=None):
        super().__init__(parent)
        self.sales_manager = sales_manager
        self.init_ui()
        self.load_report()
    
    def init_ui(self):
        self.setWindowTitle("销售报告")
        self.setGeometry(200, 200, 900, 700)
        
        layout = QVBoxLayout()
        
        # 标题
        title_label = QLabel("销售报告")
        title_label.setFont(QFont("Arial", 16, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        
        # 日期筛选
        date_layout = QHBoxLayout()
        date_layout.addWidget(QLabel("开始日期:"))
        self.start_date_edit = QLineEdit()
        self.start_date_edit.setPlaceholderText("YYYY-MM-DD")
        
        date_layout.addWidget(QLabel("结束日期:"))
        self.end_date_edit = QLineEdit()
        self.end_date_edit.setPlaceholderText("YYYY-MM-DD")
        
        refresh_btn = QPushButton("刷新")
        refresh_btn.clicked.connect(self.load_report)
        
        date_layout.addWidget(refresh_btn)
        date_layout.addStretch()
        
        # 销售汇总
        summary_group = QGroupBox("销售汇总")
        summary_layout = QHBoxLayout()
        
        self.total_sales_label = QLabel("总销量: 0")
        self.total_revenue_label = QLabel("总收入: ¥0.00")
        
        summary_layout.addWidget(self.total_sales_label)
        summary_layout.addWidget(self.total_revenue_label)
        summary_layout.addStretch()
        
        summary_group.setLayout(summary_layout)
        
        # 商品销售表格
        self.sales_table = QTableWidget()
        self.sales_table.setColumnCount(4)
        self.sales_table.setHorizontalHeaderLabels(["商品名称", "销量", "收入", "交易次数"])
        self.sales_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        # 图表
        self.chart_widget = SalesChartWidget(self.sales_manager)
        
        layout.addWidget(title_label)
        layout.addLayout(date_layout)
        layout.addWidget(summary_group)
        layout.addWidget(QLabel("商品销售排行:"))
        layout.addWidget(self.sales_table)
        layout.addWidget(self.chart_widget)
        
        self.setLayout(layout)
    
    def load_report(self):
        # 获取日期范围
        start_date = self.start_date_edit.text().strip() or None
        end_date = self.end_date_edit.text().strip() or None
        
        # 获取销售报告
        report = self.sales_manager.get_sales_report(start_date, end_date)
        
        # 更新汇总信息
        self.total_sales_label.setText(f"总销量: {report['total_sales']}")
        self.total_revenue_label.setText(f"总收入: ¥{report['total_revenue']}")
        
        # 更新销售表格
        self.sales_table.setRowCount(len(report['products']))
        
        for row, product in enumerate(report['products']):
            self.sales_table.setItem(row, 0, QTableWidgetItem(product['name']))
            self.sales_table.setItem(row, 1, QTableWidgetItem(str(product['quantity'])))
            self.sales_table.setItem(row, 2, QTableWidgetItem(f"¥{product['revenue']}"))
            self.sales_table.setItem(row, 3, QTableWidgetItem(str(product['transactions'])))

# 主程序入口
def main():
    app = QApplication(sys.argv)
    
    # 设置应用样式
    app.setStyle("Fusion")
    
    # 创建并显示主窗口
    window = SmartVendingSystem()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()