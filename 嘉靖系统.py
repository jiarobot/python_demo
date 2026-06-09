import sys
import pandas as pd
import numpy as np
from datetime import datetime
import matplotlib
matplotlib.rc("font", family='Microsoft YaHei')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QTabWidget, QTableWidget, QTableWidgetItem, QPushButton, 
                             QLabel, QLineEdit, QComboBox, QDateEdit, QMessageBox,
                             QFileDialog, QSplitter, QHeaderView, QProgressBar, QToolBar,
                             QStatusBar, QAction, QDockWidget, QTreeWidget, QTreeWidgetItem,
                             QGroupBox, QFormLayout, QSpinBox, QDoubleSpinBox, QTextEdit)
from PyQt5.QtCore import Qt, QDate, QThread, pyqtSignal
from PyQt5.QtGui import QIcon, QFont, QPalette, QColor
from PyQt5.QtChart import QChart, QChartView, QBarSeries, QBarSet, QBarCategoryAxis, QValueAxis

# 数据管理模块
class FinancialDataManager:
    def __init__(self):
        self.data = pd.DataFrame()
        self.categories = ["收入", "支出", "税收", "俸禄", "军费", "工程", "赈灾"]
        
    def load_data(self, file_path):
        try:
            if file_path.endswith('.csv'):
                self.data = pd.read_csv(file_path)
            elif file_path.endswith('.xlsx'):
                self.data = pd.read_excel(file_path)
            else:
                return False
                
            # 确保有必要的列
            required_columns = ['日期', '类别', '金额', '描述']
            for col in required_columns:
                if col not in self.data.columns:
                    self.data[col] = None
                    
            # 转换日期格式
            if '日期' in self.data.columns:
                self.data['日期'] = pd.to_datetime(self.data['日期'], errors='coerce')
                
            return True
        except Exception as e:
            print(f"数据加载错误: {e}")
            return False
            
    def save_data(self, file_path):
        try:
            if file_path.endswith('.csv'):
                self.data.to_csv(file_path, index=False)
            elif file_path.endswith('.xlsx'):
                self.data.to_excel(file_path, index=False)
            else:
                return False
            return True
        except Exception as e:
            print(f"数据保存错误: {e}")
            return False
            
    def add_record(self, date, category, amount, description):
        new_record = {
            '日期': pd.to_datetime(date),
            '类别': category,
            '金额': amount,
            '描述': description
        }
        self.data = pd.concat([self.data, pd.DataFrame([new_record])], ignore_index=True)
        return True
        
    def get_summary(self):
        if self.data.empty:
            return {}
            
        summary = {}
        # 按类别汇总
        summary['by_category'] = self.data.groupby('类别')['金额'].sum().to_dict()
        
        # 按时间汇总（月度）
        self.data['年月'] = self.data['日期'].dt.to_period('M')
        summary['by_month'] = self.data.groupby('年月')['金额'].sum().to_dict()
        
        # 总体统计
        summary['total_income'] = self.data[self.data['金额'] > 0]['金额'].sum()
        summary['total_expense'] = self.data[self.data['金额'] < 0]['金额'].sum() * -1
        summary['balance'] = summary['total_income'] - summary['total_expense']
        
        return summary

# 数据分析线程
class AnalysisThread(QThread):
    progress_updated = pyqtSignal(int)
    analysis_completed = pyqtSignal(dict)
    
    def __init__(self, data_manager):
        super().__init__()
        self.data_manager = data_manager
        
    def run(self):
        try:
            summary = self.data_manager.get_summary()
            self.progress_updated.emit(100)
            self.analysis_completed.emit(summary)
        except Exception as e:
            print(f"分析错误: {e}")

# 自定义图表组件
class FinancialChart(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.figure = Figure(figsize=(10, 6))
        self.canvas = FigureCanvas(self.figure)
        self.layout = QVBoxLayout()
        self.layout.addWidget(self.canvas)
        self.setLayout(self.layout)
        
    def plot_bar_chart(self, data, title="财务统计"):
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        
        categories = list(data.keys())
        values = list(data.values())
        
        bars = ax.bar(categories, values)
        ax.set_title(title)
        ax.tick_params(axis='x', rotation=45)
        
        # 添加数值标签
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:,.0f}', ha='center', va='bottom')
                    
        self.figure.tight_layout()
        self.canvas.draw()
        
    def plot_pie_chart(self, data, title="支出分布"):
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        
        # 过滤掉小数值
        threshold = sum(data.values()) * 0.01  # 1%阈值
        filtered_data = {k: v for k, v in data.items() if v > threshold}
        if len(filtered_data) < len(data):
            other = sum(v for k, v in data.items() if v <= threshold)
            filtered_data['其他'] = other
            
        ax.pie(filtered_data.values(), labels=filtered_data.keys(), autopct='%1.1f%%')
        ax.set_title(title)
        
        self.figure.tight_layout()
        self.canvas.draw()

# 主窗口
class JiajingFinanceSystem(QMainWindow):
    def __init__(self):
        super().__init__()
        self.data_manager = FinancialDataManager()
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("嘉靖户部管理系统")
        self.setGeometry(100, 100, 1200, 800)
        
        # 创建中央部件和主布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # 创建左侧导航栏
        left_dock = QDockWidget("导航", self)
        left_dock.setFeatures(QDockWidget.DockWidgetMovable)
        left_dock.setAllowedAreas(Qt.LeftDockWidgetArea)
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        # 导航树
        self.nav_tree = QTreeWidget()
        self.nav_tree.setHeaderLabel("功能模块")
        
        # 添加顶级项目
        modules = ["数据管理", "财务报表", "统计分析", "系统设置"]
        for module in modules:
            item = QTreeWidgetItem([module])
            self.nav_tree.addTopLevelItem(item)
            
        # 添加子项目
        data_management_items = ["数据导入", "数据录入", "数据导出"]
        for item_text in data_management_items:
            child = QTreeWidgetItem([item_text])
            self.nav_tree.topLevelItem(0).addChild(child)
            
        report_items = ["月度报表", "年度报表", "自定义报表"]
        for item_text in report_items:
            child = QTreeWidgetItem([item_text])
            self.nav_tree.topLevelItem(1).addChild(child)
            
        left_layout.addWidget(self.nav_tree)
        left_dock.setWidget(left_widget)
        self.addDockWidget(Qt.LeftDockWidgetArea, left_dock)
        
        # 创建右侧主区域
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        # 创建选项卡
        self.tab_widget = QTabWidget()
        
        # 数据管理选项卡
        self.data_tab = QWidget()
        self.setup_data_tab()
        self.tab_widget.addTab(self.data_tab, "数据管理")
        
        # 报表选项卡
        self.report_tab = QWidget()
        self.setup_report_tab()
        self.tab_widget.addTab(self.report_tab, "财务报表")
        
        # 分析选项卡
        self.analysis_tab = QWidget()
        self.setup_analysis_tab()
        self.tab_widget.addTab(self.analysis_tab, "统计分析")
        
        right_layout.addWidget(self.tab_widget)
        
        # 状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(200)
        self.status_bar.addPermanentWidget(self.progress_bar)
        
        main_layout.addWidget(right_widget)
        
        # 创建菜单栏
        self.create_menus()
        
        # 连接信号和槽
        self.nav_tree.itemClicked.connect(self.on_nav_item_clicked)
        
    def create_menus(self):
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu('文件')
        
        import_action = QAction('导入数据', self)
        import_action.triggered.connect(self.import_data)
        file_menu.addAction(import_action)
        
        export_action = QAction('导出数据', self)
        export_action.triggered.connect(self.export_data)
        file_menu.addAction(export_action)
        
        exit_action = QAction('退出', self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 工具菜单
        tools_menu = menubar.addMenu('工具')
        
        analyze_action = QAction('分析数据', self)
        analyze_action.triggered.connect(self.analyze_data)
        tools_menu.addAction(analyze_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu('帮助')
        
        about_action = QAction('关于', self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
    def setup_data_tab(self):
        layout = QVBoxLayout(self.data_tab)
        
        # 数据表格
        self.data_table = QTableWidget()
        layout.addWidget(self.data_table)
        
        # 数据操作按钮
        button_layout = QHBoxLayout()
        
        self.refresh_btn = QPushButton("刷新数据")
        self.refresh_btn.clicked.connect(self.refresh_data)
        button_layout.addWidget(self.refresh_btn)
        
        self.add_btn = QPushButton("添加记录")
        self.add_btn.clicked.connect(self.show_add_record_dialog)
        button_layout.addWidget(self.add_btn)
        
        self.delete_btn = QPushButton("删除记录")
        self.delete_btn.clicked.connect(self.delete_record)
        button_layout.addWidget(self.delete_btn)
        
        layout.addLayout(button_layout)
        
    def setup_report_tab(self):
        layout = QVBoxLayout(self.report_tab)
        
        # 报表选项
        options_layout = QHBoxLayout()
        
        options_layout.addWidget(QLabel("报表类型:"))
        self.report_type_combo = QComboBox()
        self.report_type_combo.addItems(["月度报表", "年度报表", "分类报表"])
        options_layout.addWidget(self.report_type_combo)
        
        options_layout.addWidget(QLabel("时间范围:"))
        self.start_date_edit = QDateEdit()
        self.start_date_edit.setDate(QDate.currentDate().addMonths(-1))
        options_layout.addWidget(self.start_date_edit)
        
        options_layout.addWidget(QLabel("至"))
        self.end_date_edit = QDateEdit()
        self.end_date_edit.setDate(QDate.currentDate())
        options_layout.addWidget(self.end_date_edit)
        
        self.generate_btn = QPushButton("生成报表")
        self.generate_btn.clicked.connect(self.generate_report)
        options_layout.addWidget(self.generate_btn)
        
        options_layout.addStretch()
        layout.addLayout(options_layout)
        
        # 报表显示区域
        self.report_text = QTextEdit()
        layout.addWidget(self.report_text)
        
    def setup_analysis_tab(self):
        layout = QVBoxLayout(self.analysis_tab)
        
        # 分析选项
        options_layout = QHBoxLayout()
        
        options_layout.addWidget(QLabel("分析类型:"))
        self.analysis_type_combo = QComboBox()
        self.analysis_type_combo.addItems(["收支趋势", "类别分布", "同比分析"])
        options_layout.addWidget(self.analysis_type_combo)
        
        self.analyze_btn = QPushButton("开始分析")
        self.analyze_btn.clicked.connect(self.analyze_data)
        options_layout.addWidget(self.analyze_btn)
        
        options_layout.addStretch()
        layout.addLayout(options_layout)
        
        # 图表区域
        self.chart_widget = FinancialChart()
        layout.addWidget(self.chart_widget)
        
    def import_data(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择数据文件", "", "CSV文件 (*.csv);;Excel文件 (*.xlsx)"
        )
        
        if file_path:
            success = self.data_manager.load_data(file_path)
            if success:
                self.refresh_data()
                self.status_bar.showMessage("数据导入成功", 3000)
            else:
                QMessageBox.warning(self, "错误", "数据导入失败")
                
    def export_data(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存数据文件", "", "CSV文件 (*.csv);;Excel文件 (*.xlsx)"
        )
        
        if file_path:
            success = self.data_manager.save_data(file_path)
            if success:
                self.status_bar.showMessage("数据导出成功", 3000)
            else:
                QMessageBox.warning(self, "错误", "数据导出失败")
                
    def refresh_data(self):
        if not self.data_manager.data.empty:
            self.data_table.setRowCount(len(self.data_manager.data))
            self.data_table.setColumnCount(len(self.data_manager.data.columns))
            self.data_table.setHorizontalHeaderLabels(self.data_manager.data.columns)
            
            for row in range(len(self.data_manager.data)):
                for col in range(len(self.data_manager.data.columns)):
                    item = QTableWidgetItem(str(self.data_manager.data.iloc[row, col]))
                    self.data_table.setItem(row, col, item)
                    
            self.data_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            
    def show_add_record_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("添加财务记录")
        dialog.setModal(True)
        layout = QFormLayout(dialog)
        
        date_edit = QDateEdit()
        date_edit.setDate(QDate.currentDate())
        layout.addRow("日期:", date_edit)
        
        category_combo = QComboBox()
        category_combo.addItems(self.data_manager.categories)
        layout.addRow("类别:", category_combo)
        
        amount_spin = QDoubleSpinBox()
        amount_spin.setRange(-9999999, 9999999)
        amount_spin.setDecimals(2)
        layout.addRow("金额:", amount_spin)
        
        desc_edit = QLineEdit()
        layout.addRow("描述:", desc_edit)
        
        buttons_layout = QHBoxLayout()
        ok_btn = QPushButton("确定")
        cancel_btn = QPushButton("取消")
        buttons_layout.addWidget(ok_btn)
        buttons_layout.addWidget(cancel_btn)
        layout.addRow(buttons_layout)
        
        def add_record():
            date = date_edit.date().toString("yyyy-MM-dd")
            category = category_combo.currentText()
            amount = amount_spin.value()
            description = desc_edit.text()
            
            self.data_manager.add_record(date, category, amount, description)
            self.refresh_data()
            dialog.accept()
            
        ok_btn.clicked.connect(add_record)
        cancel_btn.clicked.connect(dialog.reject)
        
        dialog.exec_()
        
    def delete_record(self):
        selected = self.data_table.currentRow()
        if selected >= 0:
            reply = QMessageBox.question(
                self, "确认删除", 
                "确定要删除选中的记录吗?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.data_manager.data.drop(selected, inplace=True)
                self.data_manager.data.reset_index(drop=True, inplace=True)
                self.refresh_data()
        else:
            QMessageBox.warning(self, "警告", "请先选择要删除的记录")
            
    def generate_report(self):
        if self.data_manager.data.empty:
            QMessageBox.warning(self, "警告", "没有数据可生成报表")
            return
            
        report_type = self.report_type_combo.currentText()
        start_date = self.start_date_edit.date().toString("yyyy-MM-dd")
        end_date = self.end_date_edit.date().toString("yyyy-MM-dd")
        
        # 过滤数据
        filtered_data = self.data_manager.data[
            (self.data_manager.data['日期'] >= start_date) & 
            (self.data_manager.data['日期'] <= end_date)
        ]
        
        if filtered_data.empty:
            QMessageBox.warning(self, "警告", "选定时间范围内没有数据")
            return
            
        # 生成报表内容
        report_content = f"嘉靖户部系统报表\n"
        report_content += f"时间范围: {start_date} 至 {end_date}\n"
        report_content += f"报表类型: {report_type}\n"
        report_content += "=" * 50 + "\n\n"
        
        if report_type == "月度报表":
            # 按月汇总
            filtered_data['年月'] = pd.to_datetime(filtered_data['日期']).dt.to_period('M')
            monthly_summary = filtered_data.groupby('年月')['金额'].agg(['sum', 'count'])
            
            report_content += "月度收支汇总:\n"
            for period, row in monthly_summary.iterrows():
                report_content += f"{period}: {row['sum']:,.2f} (共{row['count']}笔记录)\n"
                
        elif report_type == "年度报表":
            # 按年汇总
            filtered_data['年份'] = pd.to_datetime(filtered_data['日期']).dt.year
            yearly_summary = filtered_data.groupby('年份')['金额'].agg(['sum', 'count'])
            
            report_content += "年度收支汇总:\n"
            for year, row in yearly_summary.iterrows():
                report_content += f"{year}年: {row['sum']:,.2f} (共{row['count']}笔记录)\n"
                
        elif report_type == "分类报表":
            # 按类别汇总
            category_summary = filtered_data.groupby('类别')['金额'].agg(['sum', 'count'])
            
            report_content += "分类收支汇总:\n"
            for category, row in category_summary.iterrows():
                report_content += f"{category}: {row['sum']:,.2f} (共{row['count']}笔记录)\n"
                
        # 总体统计
        total_income = filtered_data[filtered_data['金额'] > 0]['金额'].sum()
        total_expense = filtered_data[filtered_data['金额'] < 0]['金额'].sum() * -1
        balance = total_income - total_expense
        
        report_content += "\n总体统计:\n"
        report_content += f"总收入: {total_income:,.2f}\n"
        report_content += f"总支出: {total_expense:,.2f}\n"
        report_content += f"结余: {balance:,.2f}\n"
        
        self.report_text.setPlainText(report_content)
        
    def analyze_data(self):
        if self.data_manager.data.empty:
            QMessageBox.warning(self, "警告", "没有数据可分析")
            return
            
        analysis_type = self.analysis_type_combo.currentText()
        summary = self.data_manager.get_summary()
        
        if analysis_type == "收支趋势":
            # 显示月度收支趋势
            monthly_data = summary.get('by_month', {})
            if monthly_data:
                self.chart_widget.plot_bar_chart(monthly_data, "月度收支趋势")
            else:
                QMessageBox.warning(self, "警告", "没有足够的数据进行趋势分析")
                
        elif analysis_type == "类别分布":
            # 显示支出类别分布
            category_data = summary.get('by_category', {})
            expense_data = {k: v for k, v in category_data.items() if v < 0}
            if expense_data:
                # 转换为正数用于饼图
                positive_data = {k: -v for k, v in expense_data.items()}
                self.chart_widget.plot_pie_chart(positive_data, "支出分布")
            else:
                QMessageBox.warning(self, "警告", "没有支出数据进行分析")
                
    def on_nav_item_clicked(self, item, column):
        text = item.text(column)
        
        if text == "数据导入":
            self.import_data()
        elif text == "数据录入":
            self.show_add_record_dialog()
        elif text == "数据导出":
            self.export_data()
        elif text in ["月度报表", "年度报表", "自定义报表"]:
            self.tab_widget.setCurrentIndex(1)  # 切换到报表选项卡
            self.report_type_combo.setCurrentText(text)
        elif text == "统计分析":
            self.tab_widget.setCurrentIndex(2)  # 切换到分析选项卡
            
    def show_about(self):
        QMessageBox.about(self, "关于嘉靖户部系统", 
                         "嘉靖户部管理系统 v1.0\n\n"
                         "基于PyQt开发的明代财政管理系统\n"
                         "提供财务数据管理、报表生成和统计分析功能")

# 主程序入口
if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # 设置应用程序样式
    app.setStyle('Fusion')
    
    # 创建并显示主窗口
    window = JiajingFinanceSystem()
    window.show()
    
    sys.exit(app.exec_())