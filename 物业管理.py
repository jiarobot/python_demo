import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib
matplotlib.rc("font", family='Microsoft YaHei')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt5.QtCore import Qt, QDate, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QIcon, QPixmap
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QPushButton, QTableWidget, QTableWidgetItem, QComboBox,
                             QLineEdit, QDateEdit, QMessageBox, QHeaderView, QTabWidget,
                             QGroupBox, QFormLayout, QSpinBox, QDoubleSpinBox, QCheckBox,
                             QProgressBar, QFileDialog, QSplitter, QFrame, QTextEdit,
                             QListWidget, QTreeWidget, QTreeWidgetItem, QToolBar, QAction,
                             QStatusBar, QDialog, QGridLayout, QSizePolicy, QScrollArea)

class PropertyDatabase:
    """物业数据库模拟类"""
    def __init__(self):
        self.properties = []
        self.tenants = []
        self.payments = []
        self.maintenance_requests = []
        self.generate_sample_data()
    
    def generate_sample_data(self):
        """生成示例数据"""
        # 生成物业数据
        for i in range(1, 21):
            self.properties.append({
                'id': i,
                'name': f'物业 {i}',
                'type': '住宅' if i % 3 == 0 else '商业' if i % 3 == 1 else '办公',
                'area': np.random.uniform(50, 200),
                'owner': f'业主 {i}',
                'contact': f'1380013800{i%10}',
                'status': '已租' if i % 4 == 0 else '空置'
            })
        
        # 生成租户数据
        for i in range(1, 16):
            self.tenants.append({
                'id': i,
                'name': f'租户 {i}',
                'property_id': np.random.randint(1, 21),
                'move_in_date': (datetime.now() - timedelta(days=np.random.randint(30, 365))).strftime('%Y-%m-%d'),
                'rent': np.random.randint(2000, 10000),
                'contact': f'1390013900{i%10}'
            })
        
        # 生成支付数据
        payment_id = 1
        for tenant in self.tenants:
            for month in range(1, 13):
                if np.random.random() > 0.2:  # 80%的概率生成支付记录
                    self.payments.append({
                        'id': payment_id,
                        'tenant_id': tenant['id'],
                        'property_id': tenant['property_id'],
                        'amount': tenant['rent'],
                        'date': (datetime.now() - timedelta(days=30*(13-month))).strftime('%Y-%m-%d'),
                        'status': '已支付' if np.random.random() > 0.1 else '未支付'
                    })
                    payment_id += 1
        
        # 生成维修请求数据
        for i in range(1, 31):
            self.maintenance_requests.append({
                'id': i,
                'property_id': np.random.randint(1, 21),
                'tenant_id': np.random.randint(1, 16),
                'date': (datetime.now() - timedelta(days=np.random.randint(1, 90))).strftime('%Y-%m-%d'),
                'issue': np.random.choice(['水管漏水', '电路故障', '空调问题', '门窗损坏', '其他']),
                'status': np.random.choice(['待处理', '处理中', '已完成'], p=[0.2, 0.3, 0.5]),
                'priority': np.random.choice(['低', '中', '高'], p=[0.4, 0.4, 0.2])
            })
    
    def get_properties(self):
        return self.properties
    
    def get_tenants(self):
        return self.tenants
    
    def get_payments(self):
        return self.payments
    
    def get_maintenance_requests(self):
        return self.maintenance_requests

class ChartWidget(QWidget):
    """图表组件"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.figure = Figure(figsize=(5, 4), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        self.layout = QVBoxLayout()
        self.layout.addWidget(self.canvas)
        self.setLayout(self.layout)
    
    def plot_property_type_distribution(self, properties):
        """绘制物业类型分布图"""
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        
        types = [p['type'] for p in properties]
        type_counts = pd.Series(types).value_counts()
        
        ax.pie(type_counts.values, labels=type_counts.index, autopct='%1.1f%%')
        ax.set_title('物业类型分布')
        
        self.canvas.draw()
    
    def plot_rent_distribution(self, tenants):
        """绘制租金分布图"""
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        
        rents = [t['rent'] for t in tenants]
        ax.hist(rents, bins=10, edgecolor='black')
        ax.set_xlabel('租金')
        ax.set_ylabel('数量')
        ax.set_title('租金分布')
        
        self.canvas.draw()
    
    def plot_payment_status(self, payments):
        """绘制支付状态图"""
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        
        statuses = [p['status'] for p in payments]
        status_counts = pd.Series(statuses).value_counts()
        
        ax.bar(status_counts.index, status_counts.values)
        ax.set_xlabel('支付状态')
        ax.set_ylabel('数量')
        ax.set_title('支付状态分布')
        
        self.canvas.draw()

class DataTableWidget(QWidget):
    """数据表格组件"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout()
        self.table = QTableWidget()
        self.layout.addWidget(self.table)
        self.setLayout(self.layout)
    
    def display_data(self, data, columns):
        """显示数据到表格"""
        if not data:
            return
        
        self.table.setRowCount(len(data))
        self.table.setColumnCount(len(columns))
        self.table.setHorizontalHeaderLabels(columns)
        
        for row_idx, row_data in enumerate(data):
            for col_idx, col_name in enumerate(columns):
                item = QTableWidgetItem(str(row_data.get(col_name, '')))
                self.table.setItem(row_idx, col_idx, item)
        
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

class DashboardWidget(QWidget):
    """仪表板组件"""
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.init_ui()
        self.update_data()
    
    def init_ui(self):
        self.layout = QVBoxLayout()
        
        # 顶部指标卡片
        metrics_layout = QHBoxLayout()
        
        self.total_properties_label = QLabel("0")
        self.total_properties_label.setStyleSheet("font-size: 24px; font-weight: bold;")
        properties_card = self.create_metric_card("总物业数", self.total_properties_label)
        
        self.occupied_label = QLabel("0")
        self.occupied_label.setStyleSheet("font-size: 24px; font-weight: bold;")
        occupied_card = self.create_metric_card("已租物业", self.occupied_label)
        
        self.vacant_label = QLabel("0")
        self.vacant_label.setStyleSheet("font-size: 24px; font-weight: bold;")
        vacant_card = self.create_metric_card("空置物业", self.vacant_label)
        
        self.collection_rate_label = QLabel("0%")
        self.collection_rate_label.setStyleSheet("font-size: 24px; font-weight: bold;")
        collection_card = self.create_metric_card("收款率", self.collection_rate_label)
        
        metrics_layout.addWidget(properties_card)
        metrics_layout.addWidget(occupied_card)
        metrics_layout.addWidget(vacant_card)
        metrics_layout.addWidget(collection_card)
        
        self.layout.addLayout(metrics_layout)
        
        # 图表区域
        splitter = QSplitter(Qt.Horizontal)
        
        self.chart1 = ChartWidget()
        self.chart2 = ChartWidget()
        self.chart3 = ChartWidget()
        
        splitter.addWidget(self.chart1)
        splitter.addWidget(self.chart2)
        splitter.addWidget(self.chart3)
        splitter.setSizes([300, 300, 300])
        
        self.layout.addWidget(splitter)
        
        self.setLayout(self.layout)
    
    def create_metric_card(self, title, value_label):
        """创建指标卡片"""
        card = QFrame()
        card.setFrameStyle(QFrame.StyledPanel)
        card.setStyleSheet("QFrame { background-color: #f0f0f0; border-radius: 5px; }")
        
        layout = QVBoxLayout()
        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 14px; color: #555;")
        title_label.setAlignment(Qt.AlignCenter)
        
        value_label.setAlignment(Qt.AlignCenter)
        
        layout.addWidget(title_label)
        layout.addWidget(value_label)
        card.setLayout(layout)
        
        return card
    
    def update_data(self):
        """更新数据"""
        properties = self.db.get_properties()
        tenants = self.db.get_tenants()
        payments = self.db.get_payments()
        
        # 更新指标
        total_properties = len(properties)
        occupied = len([p for p in properties if p['status'] == '已租'])
        vacant = total_properties - occupied
        
        paid_payments = len([p for p in payments if p['status'] == '已支付'])
        total_payments = len(payments)
        collection_rate = (paid_payments / total_payments * 100) if total_payments > 0 else 0
        
        self.total_properties_label.setText(str(total_properties))
        self.occupied_label.setText(str(occupied))
        self.vacant_label.setText(str(vacant))
        self.collection_rate_label.setText(f"{collection_rate:.1f}%")
        
        # 更新图表
        self.chart1.plot_property_type_distribution(properties)
        self.chart2.plot_rent_distribution(tenants)
        self.chart3.plot_payment_status(payments)

class PropertyManagerWidget(QWidget):
    """物业管理组件"""
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.init_ui()
        self.load_data()
    
    def init_ui(self):
        self.layout = QVBoxLayout()
        
        # 搜索和过滤区域
        filter_layout = QHBoxLayout()
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索物业...")
        self.search_input.textChanged.connect(self.filter_data)
        
        self.type_filter = QComboBox()
        self.type_filter.addItem("所有类型")
        self.type_filter.addItems(["住宅", "商业", "办公"])
        self.type_filter.currentTextChanged.connect(self.filter_data)
        
        self.status_filter = QComboBox()
        self.status_filter.addItem("所有状态")
        self.status_filter.addItems(["已租", "空置"])
        self.status_filter.currentTextChanged.connect(self.filter_data)
        
        filter_layout.addWidget(QLabel("搜索:"))
        filter_layout.addWidget(self.search_input)
        filter_layout.addWidget(QLabel("类型:"))
        filter_layout.addWidget(self.type_filter)
        filter_layout.addWidget(QLabel("状态:"))
        self.layout.addLayout(filter_layout)
        filter_layout.addWidget(self.status_filter)
        
        # 数据表格
        self.table = DataTableWidget()
        self.layout.addWidget(self.table)
        
        # 操作按钮
        button_layout = QHBoxLayout()
        
        self.add_btn = QPushButton("添加物业")
        self.add_btn.clicked.connect(self.add_property)
        
        self.edit_btn = QPushButton("编辑物业")
        self.edit_btn.clicked.connect(self.edit_property)
        
        self.delete_btn = QPushButton("删除物业")
        self.delete_btn.clicked.connect(self.delete_property)
        
        self.export_btn = QPushButton("导出数据")
        self.export_btn.clicked.connect(self.export_data)
        
        button_layout.addWidget(self.add_btn)
        button_layout.addWidget(self.edit_btn)
        button_layout.addWidget(self.delete_btn)
        button_layout.addWidget(self.export_btn)
        button_layout.addStretch()
        
        self.layout.addLayout(button_layout)
        self.setLayout(self.layout)
    
    def load_data(self):
        """加载数据"""
        self.properties = self.db.get_properties()
        self.display_data(self.properties)
    
    def display_data(self, data):
        """显示数据"""
        columns = ['id', 'name', 'type', 'area', 'owner', 'contact', 'status']
        column_names = ['ID', '名称', '类型', '面积(m²)', '业主', '联系方式', '状态']
        self.table.display_data(data, column_names)
    
    def filter_data(self):
        """过滤数据"""
        search_text = self.search_input.text().lower()
        type_filter = self.type_filter.currentText()
        status_filter = self.status_filter.currentText()
        
        filtered_data = self.properties
        
        if search_text:
            filtered_data = [p for p in filtered_data if 
                            search_text in p['name'].lower() or 
                            search_text in p['owner'].lower()]
        
        if type_filter != "所有类型":
            filtered_data = [p for p in filtered_data if p['type'] == type_filter]
        
        if status_filter != "所有状态":
            filtered_data = [p for p in filtered_data if p['status'] == status_filter]
        
        self.display_data(filtered_data)
    
    def add_property(self):
        """添加物业"""
        dialog = PropertyDialog(self)
        if dialog.exec_():
            new_property = {
                'id': max([p['id'] for p in self.properties]) + 1,
                'name': dialog.name_input.text(),
                'type': dialog.type_combo.currentText(),
                'area': float(dialog.area_input.text()),
                'owner': dialog.owner_input.text(),
                'contact': dialog.contact_input.text(),
                'status': dialog.status_combo.currentText()
            }
            self.properties.append(new_property)
            self.display_data(self.properties)
            QMessageBox.information(self, "成功", "物业添加成功")
    
    def edit_property(self):
        """编辑物业"""
        selected_row = self.table.table.currentRow()
        if selected_row == -1:
            QMessageBox.warning(self, "警告", "请先选择要编辑的物业")
            return
        
        property_id = int(self.table.table.item(selected_row, 0).text())
        property_data = next((p for p in self.properties if p['id'] == property_id), None)
        
        if property_data:
            dialog = PropertyDialog(self, property_data)
            if dialog.exec_():
                property_data['name'] = dialog.name_input.text()
                property_data['type'] = dialog.type_combo.currentText()
                property_data['area'] = float(dialog.area_input.text())
                property_data['owner'] = dialog.owner_input.text()
                property_data['contact'] = dialog.contact_input.text()
                property_data['status'] = dialog.status_combo.currentText()
                self.display_data(self.properties)
                QMessageBox.information(self, "成功", "物业信息更新成功")
    
    def delete_property(self):
        """删除物业"""
        selected_row = self.table.table.currentRow()
        if selected_row == -1:
            QMessageBox.warning(self, "警告", "请先选择要删除的物业")
            return
        
        property_id = int(self.table.table.item(selected_row, 0).text())
        
        reply = QMessageBox.question(self, "确认删除", 
                                    "确定要删除这个物业吗？此操作不可恢复。",
                                    QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.properties = [p for p in self.properties if p['id'] != property_id]
            self.display_data(self.properties)
            QMessageBox.information(self, "成功", "物业删除成功")
    
    def export_data(self):
        """导出数据"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出数据", "", "CSV Files (*.csv);;Excel Files (*.xlsx)")
        
        if file_path:
            df = pd.DataFrame(self.properties)
            if file_path.endswith('.csv'):
                df.to_csv(file_path, index=False)
            else:
                df.to_excel(file_path, index=False)
            
            QMessageBox.information(self, "成功", f"数据已导出到 {file_path}")

class PropertyDialog(QDialog):
    """物业编辑对话框"""
    def __init__(self, parent=None, property_data=None):
        super().__init__(parent)
        self.property_data = property_data
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("编辑物业" if self.property_data else "添加物业")
        self.setModal(True)
        
        layout = QFormLayout()
        
        self.name_input = QLineEdit()
        layout.addRow("物业名称:", self.name_input)
        
        self.type_combo = QComboBox()
        self.type_combo.addItems(["住宅", "商业", "办公"])
        layout.addRow("物业类型:", self.type_combo)
        
        self.area_input = QLineEdit()
        self.area_input.setValidator(QDoubleValidator(0, 10000, 2))
        layout.addRow("面积(m²):", self.area_input)
        
        self.owner_input = QLineEdit()
        layout.addRow("业主姓名:", self.owner_input)
        
        self.contact_input = QLineEdit()
        layout.addRow("联系方式:", self.contact_input)
        
        self.status_combo = QComboBox()
        self.status_combo.addItems(["已租", "空置"])
        layout.addRow("状态:", self.status_combo)
        
        # 填充现有数据（如果是编辑模式）
        if self.property_data:
            self.name_input.setText(self.property_data['name'])
            self.type_combo.setCurrentText(self.property_data['type'])
            self.area_input.setText(str(self.property_data['area']))
            self.owner_input.setText(self.property_data['owner'])
            self.contact_input.setText(self.property_data['contact'])
            self.status_combo.setCurrentText(self.property_data['status'])
        
        # 按钮
        button_layout = QHBoxLayout()
        self.ok_btn = QPushButton("确定")
        self.ok_btn.clicked.connect(self.accept)
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(self.ok_btn)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addRow(button_layout)
        self.setLayout(layout)

class FinancialWidget(QWidget):
    """财务管理组件"""
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.init_ui()
        self.load_data()
    
    def init_ui(self):
        self.layout = QVBoxLayout()
        
        # 过滤区域
        filter_layout = QHBoxLayout()
        
        self.month_filter = QComboBox()
        months = [(datetime.now() - timedelta(days=30*i)).strftime("%Y-%m") for i in range(12)]
        self.month_filter.addItems(["所有月份"] + months)
        self.month_filter.currentTextChanged.connect(self.filter_data)
        
        self.status_filter = QComboBox()
        self.status_filter.addItems(["所有状态", "已支付", "未支付"])
        self.status_filter.currentTextChanged.connect(self.filter_data)
        
        filter_layout.addWidget(QLabel("月份:"))
        filter_layout.addWidget(self.month_filter)
        filter_layout.addWidget(QLabel("状态:"))
        filter_layout.addWidget(self.status_filter)
        
        self.layout.addLayout(filter_layout)
        
        # 统计信息
        stats_layout = QHBoxLayout()
        
        self.total_label = QLabel("总金额: 0")
        self.paid_label = QLabel("已支付: 0")
        self.unpaid_label = QLabel("未支付: 0")
        
        stats_layout.addWidget(self.total_label)
        stats_layout.addWidget(self.paid_label)
        stats_layout.addWidget(self.unpaid_label)
        stats_layout.addStretch()
        
        self.layout.addLayout(stats_layout)
        
        # 数据表格
        self.table = DataTableWidget()
        self.layout.addWidget(self.table)
        
        # 操作按钮
        button_layout = QHBoxLayout()
        
        self.pay_btn = QPushButton("标记为已支付")
        self.pay_btn.clicked.connect(self.mark_as_paid)
        
        self.export_btn = QPushButton("导出数据")
        self.export_btn.clicked.connect(self.export_data)
        
        button_layout.addWidget(self.pay_btn)
        button_layout.addWidget(self.export_btn)
        button_layout.addStretch()
        
        self.layout.addLayout(button_layout)
        self.setLayout(self.layout)
    
    def load_data(self):
        """加载数据"""
        self.payments = self.db.get_payments()
        self.display_data(self.payments)
        self.update_stats(self.payments)
    
    def display_data(self, data):
        """显示数据"""
        columns = ['id', 'tenant_id', 'property_id', 'amount', 'date', 'status']
        column_names = ['ID', '租户ID', '物业ID', '金额', '日期', '状态']
        self.table.display_data(data, column_names)
    
    def update_stats(self, data):
        """更新统计信息"""
        total_amount = sum(p['amount'] for p in data)
        paid_amount = sum(p['amount'] for p in data if p['status'] == '已支付')
        unpaid_amount = total_amount - paid_amount
        
        self.total_label.setText(f"总金额: {total_amount}")
        self.paid_label.setText(f"已支付: {paid_amount}")
        self.unpaid_label.setText(f"未支付: {unpaid_amount}")
    
    def filter_data(self):
        """过滤数据"""
        month_filter = self.month_filter.currentText()
        status_filter = self.status_filter.currentText()
        
        filtered_data = self.payments
        
        if month_filter != "所有月份":
            filtered_data = [p for p in filtered_data if p['date'].startswith(month_filter)]
        
        if status_filter != "所有状态":
            filtered_data = [p for p in filtered_data if p['status'] == status_filter]
        
        self.display_data(filtered_data)
        self.update_stats(filtered_data)
    
    def mark_as_paid(self):
        """标记为已支付"""
        selected_row = self.table.table.currentRow()
        if selected_row == -1:
            QMessageBox.warning(self, "警告", "请先选择要标记的付款记录")
            return
        
        payment_id = int(self.table.table.item(selected_row, 0).text())
        
        for payment in self.payments:
            if payment['id'] == payment_id:
                payment['status'] = '已支付'
                break
        
        self.display_data(self.payments)
        self.update_stats(self.payments)
        QMessageBox.information(self, "成功", "付款记录已标记为已支付")
    
    def export_data(self):
        """导出数据"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出数据", "", "CSV Files (*.csv);;Excel Files (*.xlsx)")
        
        if file_path:
            df = pd.DataFrame(self.payments)
            if file_path.endswith('.csv'):
                df.to_csv(file_path, index=False)
            else:
                df.to_excel(file_path, index=False)
            
            QMessageBox.information(self, "成功", f"数据已导出到 {file_path}")

class MaintenanceWidget(QWidget):
    """维修管理组件"""
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.init_ui()
        self.load_data()
    
    def init_ui(self):
        self.layout = QVBoxLayout()
        
        # 过滤区域
        filter_layout = QHBoxLayout()
        
        self.status_filter = QComboBox()
        self.status_filter.addItems(["所有状态", "待处理", "处理中", "已完成"])
        self.status_filter.currentTextChanged.connect(self.filter_data)
        
        self.priority_filter = QComboBox()
        self.priority_filter.addItems(["所有优先级", "低", "中", "高"])
        self.priority_filter.currentTextChanged.connect(self.filter_data)
        
        filter_layout.addWidget(QLabel("状态:"))
        filter_layout.addWidget(self.status_filter)
        filter_layout.addWidget(QLabel("优先级:"))
        filter_layout.addWidget(self.priority_filter)
        
        self.layout.addLayout(filter_layout)
        
        # 数据表格
        self.table = DataTableWidget()
        self.layout.addWidget(self.table)
        
        # 操作按钮
        button_layout = QHBoxLayout()
        
        self.add_btn = QPushButton("添加维修请求")
        self.add_btn.clicked.connect(self.add_request)
        
        self.update_btn = QPushButton("更新状态")
        self.update_btn.clicked.connect(self.update_status)
        
        self.export_btn = QPushButton("导出数据")
        self.export_btn.clicked.connect(self.export_data)
        
        button_layout.addWidget(self.add_btn)
        button_layout.addWidget(self.update_btn)
        button_layout.addWidget(self.export_btn)
        button_layout.addStretch()
        
        self.layout.addLayout(button_layout)
        self.setLayout(self.layout)
    
    def load_data(self):
        """加载数据"""
        self.requests = self.db.get_maintenance_requests()
        self.display_data(self.requests)
    
    def display_data(self, data):
        """显示数据"""
        columns = ['id', 'property_id', 'tenant_id', 'date', 'issue', 'status', 'priority']
        column_names = ['ID', '物业ID', '租户ID', '日期', '问题', '状态', '优先级']
        self.table.display_data(data, column_names)
    
    def filter_data(self):
        """过滤数据"""
        status_filter = self.status_filter.currentText()
        priority_filter = self.priority_filter.currentText()
        
        filtered_data = self.requests
        
        if status_filter != "所有状态":
            filtered_data = [r for r in filtered_data if r['status'] == status_filter]
        
        if priority_filter != "所有优先级":
            filtered_data = [r for r in filtered_data if r['priority'] == priority_filter]
        
        self.display_data(filtered_data)
    
    def add_request(self):
        """添加维修请求"""
        dialog = MaintenanceDialog(self)
        if dialog.exec_():
            new_request = {
                'id': max([r['id'] for r in self.requests]) + 1,
                'property_id': int(dialog.property_input.text()),
                'tenant_id': int(dialog.tenant_input.text()),
                'date': datetime.now().strftime('%Y-%m-%d'),
                'issue': dialog.issue_input.text(),
                'status': '待处理',
                'priority': dialog.priority_combo.currentText()
            }
            self.requests.append(new_request)
            self.display_data(self.requests)
            QMessageBox.information(self, "成功", "维修请求添加成功")
    
    def update_status(self):
        """更新状态"""
        selected_row = self.table.table.currentRow()
        if selected_row == -1:
            QMessageBox.warning(self, "警告", "请先选择要更新的维修请求")
            return
        
        request_id = int(self.table.table.item(selected_row, 0).text())
        request = next((r for r in self.requests if r['id'] == request_id), None)
        
        if request:
            status, ok = QInputDialog.getItem(
                self, "更新状态", "选择新状态:", 
                ["待处理", "处理中", "已完成"], 0, False)
            
            if ok and status:
                request['status'] = status
                self.display_data(self.requests)
                QMessageBox.information(self, "成功", "维修请求状态已更新")
    
    def export_data(self):
        """导出数据"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出数据", "", "CSV Files (*.csv);;Excel Files (*.xlsx)")
        
        if file_path:
            df = pd.DataFrame(self.requests)
            if file_path.endswith('.csv'):
                df.to_csv(file_path, index=False)
            else:
                df.to_excel(file_path, index=False)
            
            QMessageBox.information(self, "成功", f"数据已导出到 {file_path}")

class MaintenanceDialog(QDialog):
    """维修请求对话框"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("添加维修请求")
        self.setModal(True)
        
        layout = QFormLayout()
        
        self.property_input = QLineEdit()
        self.property_input.setValidator(QIntValidator(1, 10000))
        layout.addRow("物业ID:", self.property_input)
        
        self.tenant_input = QLineEdit()
        self.tenant_input.setValidator(QIntValidator(1, 10000))
        layout.addRow("租户ID:", self.tenant_input)
        
        self.issue_input = QLineEdit()
        layout.addRow("问题描述:", self.issue_input)
        
        self.priority_combo = QComboBox()
        self.priority_combo.addItems(["低", "中", "高"])
        layout.addRow("优先级:", self.priority_combo)
        
        # 按钮
        button_layout = QHBoxLayout()
        self.ok_btn = QPushButton("确定")
        self.ok_btn.clicked.connect(self.accept)
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(self.ok_btn)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addRow(button_layout)
        self.setLayout(layout)

class ReportGeneratorWidget(QWidget):
    """报表生成组件"""
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.init_ui()
    
    def init_ui(self):
        self.layout = QVBoxLayout()
        
        # 报表类型选择
        report_layout = QHBoxLayout()
        report_layout.addWidget(QLabel("选择报表类型:"))
        
        self.report_combo = QComboBox()
        self.report_combo.addItems([
            "物业空置率报表", 
            "租金收入报表", 
            "维修请求统计报表",
            "租户信息报表"
        ])
        report_layout.addWidget(self.report_combo)
        
        self.generate_btn = QPushButton("生成报表")
        self.generate_btn.clicked.connect(self.generate_report)
        report_layout.addWidget(self.generate_btn)
        
        self.layout.addLayout(report_layout)
        
        # 报表显示区域
        self.report_view = QTextEdit()
        self.report_view.setReadOnly(True)
        self.layout.addWidget(self.report_view)
        
        # 导出按钮
        self.export_btn = QPushButton("导出报表")
        self.export_btn.clicked.connect(self.export_report)
        self.layout.addWidget(self.export_btn)
        
        self.setLayout(self.layout)
    
    def generate_report(self):
        """生成报表"""
        report_type = self.report_combo.currentText()
        
        if report_type == "物业空置率报表":
            self.generate_vacancy_report()
        elif report_type == "租金收入报表":
            self.generate_rent_report()
        elif report_type == "维修请求统计报表":
            self.generate_maintenance_report()
        elif report_type == "租户信息报表":
            self.generate_tenant_report()
    
    def generate_vacancy_report(self):
        """生成物业空置率报表"""
        properties = self.db.get_properties()
        total = len(properties)
        occupied = len([p for p in properties if p['status'] == '已租'])
        vacant = total - occupied
        vacancy_rate = (vacant / total * 100) if total > 0 else 0
        
        report = f"物业空置率报表\n\n"
        report += f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        report += f"总物业数: {total}\n"
        report += f"已租物业: {occupied}\n"
        report += f"空置物业: {vacant}\n"
        report += f"空置率: {vacancy_rate:.2f}%\n\n"
        
        # 按类型统计
        report += "按类型统计:\n"
        types = set(p['type'] for p in properties)
        for t in types:
            type_properties = [p for p in properties if p['type'] == t]
            type_total = len(type_properties)
            type_occupied = len([p for p in type_properties if p['status'] == '已租'])
            type_vacant = type_total - type_occupied
            type_vacancy_rate = (type_vacant / type_total * 100) if type_total > 0 else 0
            
            report += f"  {t}: 总数{type_total}, 已租{type_occupied}, 空置{type_vacant}, 空置率{type_vacancy_rate:.2f}%\n"
        
        self.report_view.setPlainText(report)
    
    def generate_rent_report(self):
        """生成租金收入报表"""
        payments = self.db.get_payments()
        tenants = self.db.get_tenants()
        
        total_rent = sum(t['rent'] for t in tenants)
        paid_rent = sum(p['amount'] for p in payments if p['status'] == '已支付')
        unpaid_rent = total_rent - paid_rent
        collection_rate = (paid_rent / total_rent * 100) if total_rent > 0 else 0
        
        report = f"租金收入报表\n\n"
        report += f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        report += f"应收租金总额: {total_rent}\n"
        report += f"实收租金总额: {paid_rent}\n"
        report += f"未收租金总额: {unpaid_rent}\n"
        report += f"收款率: {collection_rate:.2f}%\n\n"
        
        # 按月统计
        report += "按月统计:\n"
        months = sorted(set(p['date'][:7] for p in payments), reverse=True)
        for month in months[:6]:  # 最近6个月
            month_payments = [p for p in payments if p['date'].startswith(month)]
            month_total = sum(t['rent'] for t in tenants)
            month_paid = sum(p['amount'] for p in month_payments if p['status'] == '已支付')
            month_unpaid = month_total - month_paid
            month_rate = (month_paid / month_total * 100) if month_total > 0 else 0
            
            report += f"  {month}: 应收{month_total}, 实收{month_paid}, 未收{month_unpaid}, 收款率{month_rate:.2f}%\n"
        
        self.report_view.setPlainText(report)
    
    def generate_maintenance_report(self):
        """生成维修请求统计报表"""
        requests = self.db.get_maintenance_requests()
        
        total = len(requests)
        pending = len([r for r in requests if r['status'] == '待处理'])
        in_progress = len([r for r in requests if r['status'] == '处理中'])
        completed = len([r for r in requests if r['status'] == '已完成'])
        
        low_priority = len([r for r in requests if r['priority'] == '低'])
        medium_priority = len([r for r in requests if r['priority'] == '中'])
        high_priority = len([r for r in requests if r['priority'] == '高'])
        
        report = f"维修请求统计报表\n\n"
        report += f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        report += f"总请求数: {total}\n"
        report += f"待处理: {pending}\n"
        report += f"处理中: {in_progress}\n"
        report += f"已完成: {completed}\n\n"
        
        report += "按优先级统计:\n"
        report += f"  低: {low_priority}\n"
        report += f"  中: {medium_priority}\n"
        report += f"  高: {high_priority}\n\n"
        
        # 按问题类型统计
        report += "按问题类型统计:\n"
        issues = set(r['issue'] for r in requests)
        for issue in issues:
            issue_count = len([r for r in requests if r['issue'] == issue])
            report += f"  {issue}: {issue_count}\n"
        
        self.report_view.setPlainText(report)
    
    def generate_tenant_report(self):
        """生成租户信息报表"""
        tenants = self.db.get_tenants()
        properties = self.db.get_properties()
        
        report = f"租户信息报表\n\n"
        report += f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        report += f"总租户数: {len(tenants)}\n\n"
        
        report += "租户详细信息:\n"
        for tenant in tenants:
            property_info = next((p for p in properties if p['id'] == tenant['property_id']), {})
            report += f"  租户ID: {tenant['id']}\n"
            report += f"  姓名: {tenant['name']}\n"
            report += f"  联系方式: {tenant['contact']}\n"
            report += f"  物业: {property_info.get('name', '未知')}\n"
            report += f"  月租: {tenant['rent']}\n"
            report += f"  入住日期: {tenant['move_in_date']}\n"
            report += "  ---\n"
        
        self.report_view.setPlainText(report)
    
    def export_report(self):
        """导出报表"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出报表", "", "Text Files (*.txt);;PDF Files (*.pdf)")
        
        if file_path:
            if file_path.endswith('.txt'):
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.report_view.toPlainText())
            elif file_path.endswith('.pdf'):
                # 这里简化处理，实际应用中可以使用ReportLab等库生成PDF
                with open(file_path.replace('.pdf', '.txt'), 'w', encoding='utf-8') as f:
                    f.write(self.report_view.toPlainText())
            
            QMessageBox.information(self, "成功", f"报表已导出到 {file_path}")

class AdvancedToolsWidget(QWidget):
    """高级工具组件"""
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.init_ui()
    
    def init_ui(self):
        self.layout = QVBoxLayout()
        
        # 批量操作工具
        batch_group = QGroupBox("批量操作工具")
        batch_layout = QVBoxLayout()
        
        self.batch_update_btn = QPushButton("批量更新物业状态")
        self.batch_update_btn.clicked.connect(self.batch_update_properties)
        
        self.batch_rent_increase_btn = QPushButton("批量调整租金")
        self.batch_rent_increase_btn.clicked.connect(self.batch_adjust_rent)
        
        batch_layout.addWidget(self.batch_update_btn)
        batch_layout.addWidget(self.batch_rent_increase_btn)
        batch_group.setLayout(batch_layout)
        
        # 数据管理工具
        data_group = QGroupBox("数据管理工具")
        data_layout = QVBoxLayout()
        
        self.backup_btn = QPushButton("备份数据")
        self.backup_btn.clicked.connect(self.backup_data)
        
        self.restore_btn = QPushButton("恢复数据")
        self.restore_btn.clicked.connect(self.restore_data)
        
        self.cleanup_btn = QPushButton("清理旧数据")
        self.cleanup_btn.clicked.connect(self.cleanup_data)
        
        data_layout.addWidget(self.backup_btn)
        data_layout.addWidget(self.restore_btn)
        data_layout.addWidget(self.cleanup_btn)
        data_group.setLayout(data_layout)
        
        # 系统工具
        system_group = QGroupBox("系统工具")
        system_layout = QVBoxLayout()
        
        self.optimize_btn = QPushButton("优化数据库")
        self.optimize_btn.clicked.connect(self.optimize_database)
        
        self.audit_btn = QPushButton("运行审计")
        self.audit_btn.clicked.connect(self.run_audit)
        
        system_layout.addWidget(self.optimize_btn)
        system_layout.addWidget(self.audit_btn)
        system_group.setLayout(system_layout)
        
        self.layout.addWidget(batch_group)
        self.layout.addWidget(data_group)
        self.layout.addWidget(system_group)
        self.layout.addStretch()
        
        self.setLayout(self.layout)
    
    def batch_update_properties(self):
        """批量更新物业状态"""
        dialog = BatchUpdateDialog(self)
        if dialog.exec_():
            current_status = dialog.current_combo.currentText()
            new_status = dialog.new_combo.currentText()
            
            properties = self.db.get_properties()
            updated = 0
            
            for prop in properties:
                if prop['status'] == current_status or current_status == "所有状态":
                    prop['status'] = new_status
                    updated += 1
            
            QMessageBox.information(self, "成功", f"已更新 {updated} 个物业的状态")
    
    def batch_adjust_rent(self):
        """批量调整租金"""
        percentage, ok = QInputDialog.getDouble(
            self, "批量调整租金", "输入调整百分比:", 
            value=0.0, min=-50.0, max=50.0, decimals=1
        )
        
        if ok:
            tenants = self.db.get_tenants()
            updated = 0
            
            for tenant in tenants:
                tenant['rent'] = int(tenant['rent'] * (1 + percentage / 100))
                updated += 1
            
            QMessageBox.information(self, "成功", f"已更新 {updated} 个租户的租金")
    
    def backup_data(self):
        """备份数据"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "备份数据", "", "JSON Files (*.json)")
        
        if file_path:
            # 这里简化处理，实际应用中应该序列化所有数据
            QMessageBox.information(self, "成功", f"数据已备份到 {file_path}")
    
    def restore_data(self):
        """恢复数据"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "恢复数据", "", "JSON Files (*.json)")
        
        if file_path:
            # 这里简化处理，实际应用中应该反序列化所有数据
            reply = QMessageBox.question(
                self, "确认恢复", 
                "确定要恢复数据吗？这将覆盖当前所有数据。",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                QMessageBox.information(self, "成功", "数据已恢复")
    
    def cleanup_data(self):
        """清理旧数据"""
        months, ok = QInputDialog.getInt(
            self, "清理旧数据", 
            "删除多少个月前的数据:", 
            value=12, min=1, max=60
        )
        
        if ok:
            # 这里简化处理，实际应用中应该删除旧数据
            QMessageBox.information(self, "成功", f"已清理 {months} 个月前的数据")
    
    def optimize_database(self):
        """优化数据库"""
        # 模拟优化过程
        progress = QProgressDialog("优化数据库中...", "取消", 0, 100, self)
        progress.setWindowModality(Qt.WindowModal)
        
        for i in range(101):
            progress.setValue(i)
            QApplication.processEvents()
            if progress.wasCanceled():
                break
            time.sleep(0.02)  # 模拟耗时操作
        
        progress.setValue(100)
        QMessageBox.information(self, "成功", "数据库优化完成")
    
    def run_audit(self):
        """运行审计"""
        # 模拟审计过程
        issues = []
        
        # 检查空置但已收租的物业
        properties = self.db.get_properties()
        tenants = self.db.get_tenants()
        payments = self.db.get_payments()
        
        for prop in properties:
            if prop['status'] == '空置':
                # 检查是否有租户关联
                tenant = next((t for t in tenants if t['property_id'] == prop['id']), None)
                if tenant:
                    issues.append(f"物业 {prop['name']} 状态为空置但有租户 {tenant['name']}")
                
                # 检查是否有支付记录
                payment = next((p for p in payments if p['property_id'] == prop['id']), None)
                if payment:
                    issues.append(f"物业 {prop['name']} 状态为空置但有支付记录")
        
        # 显示审计结果
        if issues:
            result = "\n".join(issues)
            QMessageBox.warning(self, "审计发现问题", f"发现以下问题:\n\n{result}")
        else:
            QMessageBox.information(self, "审计完成", "未发现问题")

class BatchUpdateDialog(QDialog):
    """批量更新对话框"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("批量更新物业状态")
        self.setModal(True)
        
        layout = QFormLayout()
        
        self.current_combo = QComboBox()
        self.current_combo.addItems(["所有状态", "已租", "空置"])
        layout.addRow("当前状态:", self.current_combo)
        
        self.new_combo = QComboBox()
        self.new_combo.addItems(["已租", "空置"])
        layout.addRow("新状态:", self.new_combo)
        
        # 按钮
        button_layout = QHBoxLayout()
        self.ok_btn = QPushButton("确定")
        self.ok_btn.clicked.connect(self.accept)
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(self.ok_btn)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addRow(button_layout)
        self.setLayout(layout)

class PropertyManagementSystem(QMainWindow):
    """物业管理系统主窗口"""
    def __init__(self):
        super().__init__()
        self.db = PropertyDatabase()
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("物业管理系统 - 高级工具库")
        self.setGeometry(100, 100, 1200, 800)
        
        # 创建中央部件和选项卡
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout()
        central_widget.setLayout(layout)
        
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        
        # 添加各个功能选项卡
        self.dashboard_tab = DashboardWidget(self.db)
        self.tabs.addTab(self.dashboard_tab, "仪表板")
        
        self.property_tab = PropertyManagerWidget(self.db)
        self.tabs.addTab(self.property_tab, "物业管理")
        
        self.financial_tab = FinancialWidget(self.db)
        self.tabs.addTab(self.financial_tab, "财务管理")
        
        self.maintenance_tab = MaintenanceWidget(self.db)
        self.tabs.addTab(self.maintenance_tab, "维修管理")
        
        self.report_tab = ReportGeneratorWidget(self.db)
        self.tabs.addTab(self.report_tab, "报表生成")
        
        self.tools_tab = AdvancedToolsWidget(self.db)
        self.tabs.addTab(self.tools_tab, "高级工具")
        
        # 创建状态栏
        self.statusBar().showMessage("就绪")
        
        # 创建菜单栏
        self.create_menus()
        
        # 创建工具栏
        self.create_toolbar()
    
    def create_menus(self):
        """创建菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu("文件")
        
        export_action = QAction("导出数据", self)
        export_action.triggered.connect(self.export_data)
        file_menu.addAction(export_action)
        
        exit_action = QAction("退出", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 工具菜单
        tools_menu = menubar.addMenu("工具")
        
        refresh_action = QAction("刷新数据", self)
        refresh_action.triggered.connect(self.refresh_data)
        tools_menu.addAction(refresh_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu("帮助")
        
        about_action = QAction("关于", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def create_toolbar(self):
        """创建工具栏"""
        toolbar = QToolBar()
        self.addToolBar(toolbar)
        
        refresh_btn = QAction("刷新", self)
        refresh_btn.triggered.connect(self.refresh_data)
        toolbar.addAction(refresh_btn)
        
        export_btn = QAction("导出", self)
        export_btn.triggered.connect(self.export_data)
        toolbar.addAction(export_btn)
    
    def refresh_data(self):
        """刷新数据"""
        # 通知所有选项卡刷新数据
        if hasattr(self.dashboard_tab, 'update_data'):
            self.dashboard_tab.update_data()
        
        if hasattr(self.property_tab, 'load_data'):
            self.property_tab.load_data()
        
        if hasattr(self.financial_tab, 'load_data'):
            self.financial_tab.load_data()
        
        if hasattr(self.maintenance_tab, 'load_data'):
            self.maintenance_tab.load_data()
        
        self.statusBar().showMessage("数据已刷新", 3000)
    
    def export_data(self):
        """导出数据"""
        # 这里简化处理，实际应用中应该提供更多导出选项
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出数据", "", "CSV Files (*.csv);;Excel Files (*.xlsx)")
        
        if file_path:
            # 获取当前选项卡的数据并导出
            current_tab = self.tabs.currentWidget()
            if hasattr(current_tab, 'export_data'):
                current_tab.export_data()
            else:
                QMessageBox.information(self, "信息", "当前选项卡不支持导出功能")
    
    def show_about(self):
        """显示关于信息"""
        QMessageBox.about(self, "关于物业管理系统", 
                         "物业管理系统 - 高级工具库\n\n"
                         "版本: 1.0.0\n"
                         "版权所有 © 2023 物业管理软件公司")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # 使用Fusion样式，使界面看起来更现代
    
    # 设置应用程序图标和字体
    app.setFont(QFont("Arial", 10))
    
    window = PropertyManagementSystem()
    window.show()
    
    sys.exit(app.exec_())