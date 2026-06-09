import sys
import os
import sqlite3
import json
import datetime
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import seaborn as sns
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

from PyQt5.QtWidgets import (QApplication, QDialog, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QTabWidget, QTableWidget, QTableWidgetItem, 
                             QLabel, QLineEdit, QComboBox, QDateEdit, QSpinBox, 
                             QDoubleSpinBox, QMessageBox, QFileDialog, QProgressBar,
                             QGroupBox, QFormLayout, QSplitter, QTextEdit, QHeaderView,
                             QCheckBox, QListWidget, QListWidgetItem, QTreeWidget, QTreeWidgetItem)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QDate
from PyQt5.QtGui import QFont, QIcon, QPalette, QColor
from PyQt5.QtChart import QChart, QChartView, QLineSeries, QValueAxis, QBarSeries, QBarSet, QBarCategoryAxis


# ============================ 数据库管理类 ============================
class LivestockDatabase:
    """畜牧业数据库管理类"""
    
    def __init__(self, db_path="livestock.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """初始化数据库表结构"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 动物信息表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS animals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ear_tag TEXT UNIQUE NOT NULL,
                species TEXT NOT NULL,
                breed TEXT,
                birth_date TEXT,
                gender TEXT,
                weight REAL,
                health_status TEXT,
                location TEXT,
                notes TEXT,
                created_date TEXT,
                updated_date TEXT
            )
        ''')
        
        # 饲养记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS feeding_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ear_tag TEXT NOT NULL,
                feed_type TEXT NOT NULL,
                quantity REAL NOT NULL,
                feeding_date TEXT NOT NULL,
                notes TEXT,
                FOREIGN KEY (ear_tag) REFERENCES animals (ear_tag)
            )
        ''')
        
        # 健康记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS health_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ear_tag TEXT NOT NULL,
                checkup_date TEXT NOT NULL,
                veterinarian TEXT,
                diagnosis TEXT,
                treatment TEXT,
                medication TEXT,
                next_checkup TEXT,
                notes TEXT,
                FOREIGN KEY (ear_tag) REFERENCES animals (ear_tag)
            )
        ''')
        
        # 繁殖记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS breeding_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mother_tag TEXT NOT NULL,
                father_tag TEXT,
                breeding_date TEXT,
                expected_birth_date TEXT,
                actual_birth_date TEXT,
                offspring_count INTEGER,
                notes TEXT,
                FOREIGN KEY (mother_tag) REFERENCES animals (ear_tag)
            )
        ''')
        
        # 生产记录表 (牛奶、鸡蛋等)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS production_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ear_tag TEXT NOT NULL,
                product_type TEXT NOT NULL,
                quantity REAL NOT NULL,
                record_date TEXT NOT NULL,
                quality_grade TEXT,
                notes TEXT,
                FOREIGN KEY (ear_tag) REFERENCES animals (ear_tag)
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
            
        result = cursor.fetchall()
        conn.close()
        return result
    
    def execute_update(self, query, params=None):
        """执行更新操作"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Database error: {e}")
            conn.close()
            return False


# ============================ 数据分析类 ============================
class LivestockAnalyzer:
    """畜牧业数据分析类"""
    
    def __init__(self, db_manager):
        self.db = db_manager
    
    def get_animal_stats(self):
        """获取动物统计信息"""
        query = """
        SELECT species, COUNT(*) as count, 
               AVG(weight) as avg_weight,
               MAX(weight) as max_weight,
               MIN(weight) as min_weight
        FROM animals 
        GROUP BY species
        """
        return self.db.execute_query(query)
    
    def get_production_trends(self, days=30):
        """获取生产趋势数据"""
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        query = """
        SELECT record_date, product_type, SUM(quantity) as total
        FROM production_records
        WHERE record_date >= ?
        GROUP BY record_date, product_type
        ORDER BY record_date
        """
        return self.db.execute_query(query, (start_date,))
    
    def get_health_analysis(self):
        """获取健康分析数据"""
        query = """
        SELECT health_status, COUNT(*) as count
        FROM animals
        GROUP BY health_status
        """
        return self.db.execute_query(query)
    
    def get_feeding_efficiency(self):
        """获取饲养效率分析"""
        query = """
        SELECT a.species, 
               SUM(f.quantity) as total_feed,
               SUM(p.quantity) as total_production,
               CASE WHEN SUM(p.quantity) > 0 THEN SUM(f.quantity)/SUM(p.quantity) ELSE 0 END as efficiency
        FROM animals a
        LEFT JOIN feeding_records f ON a.ear_tag = f.ear_tag
        LEFT JOIN production_records p ON a.ear_tag = p.ear_tag
        GROUP BY a.species
        """
        return self.db.execute_query(query)


# ============================ 图表生成类 ============================
class LivestockChartGenerator:
    """畜牧业图表生成类"""
    
    def __init__(self):
        plt.style.use('seaborn-v0_8')
        sns.set_palette("husl")
    
    def create_species_distribution_chart(self, data):
        """创建物种分布饼图"""
        fig = Figure(figsize=(8, 6))
        ax = fig.add_subplot(111)
        
        species = [item[0] for item in data]
        counts = [item[1] for item in data]
        
        ax.pie(counts, labels=species, autopct='%1.1f%%', startangle=90)
        ax.set_title('动物物种分布')
        
        return fig
    
    def create_production_trend_chart(self, data):
        """创建生产趋势折线图"""
        if not data:
            fig = Figure(figsize=(8, 6))
            ax = fig.add_subplot(111)
            ax.text(0.5, 0.5, '暂无数据', ha='center', va='center', transform=ax.transAxes)
            return fig
        
        df = pd.DataFrame(data, columns=['date', 'product_type', 'quantity'])
        df['date'] = pd.to_datetime(df['date'])
        df_pivot = df.pivot_table(index='date', columns='product_type', values='quantity', aggfunc='sum').fillna(0)
        
        fig = Figure(figsize=(10, 6))
        ax = fig.add_subplot(111)
        
        for product in df_pivot.columns:
            ax.plot(df_pivot.index, df_pivot[product], marker='o', label=product)
        
        ax.set_xlabel('日期')
        ax.set_ylabel('产量')
        ax.set_title('生产趋势')
        ax.legend()
        ax.grid(True, linestyle='--', alpha=0.7)
        
        fig.autofmt_xdate()
        return fig
    
    def create_health_status_chart(self, data):
        """创建健康状态柱状图"""
        fig = Figure(figsize=(8, 6))
        ax = fig.add_subplot(111)
        
        statuses = [item[0] for item in data]
        counts = [item[1] for item in data]
        
        bars = ax.bar(statuses, counts, color=['green', 'yellow', 'orange', 'red'])
        ax.set_xlabel('健康状态')
        ax.set_ylabel('数量')
        ax.set_title('动物健康状态分布')
        
        # 在柱子上添加数值标签
        for bar, count in zip(bars, counts):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                    f'{count}', ha='center', va='bottom')
        
        return fig


# ============================ 报告生成类 ============================
class ReportGenerator:
    """报告生成类"""
    
    def __init__(self, db_manager):
        self.db = db_manager
    
    def generate_daily_report(self, date=None):
        """生成日报"""
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        
        # 获取当日数据
        feeding_query = "SELECT COUNT(*) FROM feeding_records WHERE feeding_date = ?"
        feeding_count = self.db.execute_query(feeding_query, (date,))[0][0]
        
        health_query = "SELECT COUNT(*) FROM health_records WHERE checkup_date = ?"
        health_count = self.db.execute_query(health_query, (date,))[0][0]
        
        production_query = "SELECT SUM(quantity) FROM production_records WHERE record_date = ?"
        production_total = self.db.execute_query(production_query, (date,))[0][0] or 0
        
        # 生成报告内容
        report = {
            'date': date,
            'feeding_records': feeding_count,
            'health_checkups': health_count,
            'production_total': production_total,
            'animals_count': self.db.execute_query("SELECT COUNT(*) FROM animals")[0][0]
        }
        
        return report
    
    def export_to_pdf(self, data, filename):
        """导出数据到PDF"""
        try:
            doc = SimpleDocTemplate(filename, pagesize=letter)
            styles = getSampleStyleSheet()
            story = []
            
            # 标题
            title = Paragraph("畜牧业系统报告", styles['Title'])
            story.append(title)
            story.append(Spacer(1, 12))
            
            # 报告日期
            date_str = Paragraph(f"生成日期: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['Normal'])
            story.append(date_str)
            story.append(Spacer(1, 12))
            
            # 数据表格
            if isinstance(data, list) and data:
                # 转换数据为表格格式
                table_data = [['项目', '数值']]
                for key, value in data.items():
                    table_data.append([key, str(value)])
                
                table = Table(table_data)
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 14),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 1), (-1, -1), 12),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                story.append(table)
            
            doc.build(story)
            return True
        except Exception as e:
            print(f"PDF导出错误: {e}")
            return False


# ============================ 数据导入导出类 ============================
class DataIOHandler:
    """数据导入导出处理类"""
    
    def __init__(self, db_manager):
        self.db = db_manager
    
    def import_from_csv(self, filepath, table_name):
        """从CSV文件导入数据"""
        try:
            df = pd.read_csv(filepath)
            
            # 根据表名处理数据
            if table_name == 'animals':
                for _, row in df.iterrows():
                    query = """
                    INSERT OR REPLACE INTO animals 
                    (ear_tag, species, breed, birth_date, gender, weight, health_status, location, notes, created_date, updated_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """
                    params = (
                        row.get('ear_tag', ''),
                        row.get('species', ''),
                        row.get('breed', ''),
                        row.get('birth_date', ''),
                        row.get('gender', ''),
                        row.get('weight', 0),
                        row.get('health_status', '良好'),
                        row.get('location', ''),
                        row.get('notes', ''),
                        datetime.now().strftime('%Y-%m-%d'),
                        datetime.now().strftime('%Y-%m-%d')
                    )
                    self.db.execute_update(query, params)
            
            return True
        except Exception as e:
            print(f"CSV导入错误: {e}")
            return False
    
    def export_to_csv(self, table_name, filepath):
        """导出数据到CSV文件"""
        try:
            query = f"SELECT * FROM {table_name}"
            data = self.db.execute_query(query)
            
            # 获取列名
            column_query = f"PRAGMA table_info({table_name})"
            columns = [col[1] for col in self.db.execute_query(column_query)]
            
            df = pd.DataFrame(data, columns=columns)
            df.to_csv(filepath, index=False, encoding='utf-8')
            return True
        except Exception as e:
            print(f"CSV导出错误: {e}")
            return False


# ============================ 主界面部件 ============================
class DashboardWidget(QWidget):
    """仪表板部件"""
    
    def __init__(self, db_manager):
        super().__init__()
        self.db = db_manager
        self.analyzer = LivestockAnalyzer(db_manager)
        self.chart_generator = LivestockChartGenerator()
        self.init_ui()
        self.load_data()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 顶部统计信息
        stats_layout = QHBoxLayout()
        
        # 动物总数
        self.total_animals_label = QLabel("0")
        self.total_animals_label.setFont(QFont("Arial", 24, QFont.Bold))
        self.total_animals_label.setAlignment(Qt.AlignCenter)
        total_animals_box = self.create_stat_box("动物总数", self.total_animals_label)
        stats_layout.addWidget(total_animals_box)
        
        # 健康动物数
        self.healthy_animals_label = QLabel("0")
        self.healthy_animals_label.setFont(QFont("Arial", 24, QFont.Bold))
        self.healthy_animals_label.setAlignment(Qt.AlignCenter)
        healthy_animals_box = self.create_stat_box("健康动物", self.healthy_animals_label)
        stats_layout.addWidget(healthy_animals_box)
        
        # 今日产量
        self.today_production_label = QLabel("0")
        self.today_production_label.setFont(QFont("Arial", 24, QFont.Bold))
        self.today_production_label.setAlignment(Qt.AlignCenter)
        today_production_box = self.create_stat_box("今日产量", self.today_production_label)
        stats_layout.addWidget(today_production_box)
        
        # 待处理事项
        self.pending_tasks_label = QLabel("0")
        self.pending_tasks_label.setFont(QFont("Arial", 24, QFont.Bold))
        self.pending_tasks_label.setAlignment(Qt.AlignCenter)
        pending_tasks_box = self.create_stat_box("待处理事项", self.pending_tasks_label)
        stats_layout.addWidget(pending_tasks_box)
        
        layout.addLayout(stats_layout)
        
        # 图表区域
        chart_splitter = QSplitter(Qt.Horizontal)
        
        # 物种分布图表
        self.species_chart_canvas = FigureCanvas(Figure(figsize=(5, 4)))
        chart_splitter.addWidget(self.species_chart_canvas)
        
        # 健康状态图表
        self.health_chart_canvas = FigureCanvas(Figure(figsize=(5, 4)))
        chart_splitter.addWidget(self.health_chart_canvas)
        
        chart_splitter.setSizes([400, 400])
        layout.addWidget(chart_splitter)
        
        self.setLayout(layout)
    
    def create_stat_box(self, title, value_label):
        """创建统计信息框"""
        box = QGroupBox(title)
        layout = QVBoxLayout()
        layout.addWidget(value_label)
        box.setLayout(layout)
        return box
    
    def load_data(self):
        """加载数据"""
        # 动物总数
        total_animals = self.db.execute_query("SELECT COUNT(*) FROM animals")[0][0]
        self.total_animals_label.setText(str(total_animals))
        
        # 健康动物数
        healthy_animals = self.db.execute_query("SELECT COUNT(*) FROM animals WHERE health_status = '良好'")[0][0]
        self.healthy_animals_label.setText(str(healthy_animals))
        
        # 今日产量
        today = datetime.now().strftime('%Y-%m-%d')
        today_production = self.db.execute_query(
            "SELECT SUM(quantity) FROM production_records WHERE record_date = ?", (today,)
        )[0][0] or 0
        self.today_production_label.setText(f"{today_production:.1f}")
        
        # 待处理事项 (今日需要喂养和检查的动物)
        feeding_tasks = self.db.execute_query(
            "SELECT COUNT(DISTINCT ear_tag) FROM feeding_records WHERE feeding_date = ?", (today,)
        )[0][0]
        health_tasks = self.db.execute_query(
            "SELECT COUNT(*) FROM health_records WHERE next_checkup <= ?", (today,)
        )[0][0]
        self.pending_tasks_label.setText(str(feeding_tasks + health_tasks))
        
        # 更新图表
        self.update_charts()
    
    def update_charts(self):
        """更新图表"""
        # 物种分布图表
        species_data = self.analyzer.get_animal_stats()
        if species_data:
            species_chart = self.chart_generator.create_species_distribution_chart(
                [(item[0], item[1]) for item in species_data]
            )
            self.species_chart_canvas.figure = species_chart
            self.species_chart_canvas.draw()
        
        # 健康状态图表
        health_data = self.analyzer.get_health_analysis()
        if health_data:
            health_chart = self.chart_generator.create_health_status_chart(health_data)
            self.health_chart_canvas.figure = health_chart
            self.health_chart_canvas.draw()


class AnimalManagementWidget(QWidget):
    """动物管理部件"""
    
    def __init__(self, db_manager):
        super().__init__()
        self.db = db_manager
        self.init_ui()
        self.load_animals()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 搜索和过滤区域
        search_layout = QHBoxLayout()
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索耳标、物种、品种...")
        self.search_input.textChanged.connect(self.filter_animals)
        search_layout.addWidget(QLabel("搜索:"))
        search_layout.addWidget(self.search_input)
        
        self.species_filter = QComboBox()
        self.species_filter.addItem("所有物种")
        self.species_filter.currentTextChanged.connect(self.filter_animals)
        search_layout.addWidget(QLabel("物种:"))
        search_layout.addWidget(self.species_filter)
        
        self.health_filter = QComboBox()
        self.health_filter.addItems(["所有状态", "良好", "一般", "需关注", "生病"])
        self.health_filter.currentTextChanged.connect(self.filter_animals)
        search_layout.addWidget(QLabel("健康状态:"))
        search_layout.addWidget(self.health_filter)
        
        layout.addLayout(search_layout)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        
        self.add_button = QPushButton("添加动物")
        self.add_button.clicked.connect(self.add_animal)
        button_layout.addWidget(self.add_button)
        
        self.edit_button = QPushButton("编辑选中")
        self.edit_button.clicked.connect(self.edit_animal)
        button_layout.addWidget(self.edit_button)
        
        self.delete_button = QPushButton("删除选中")
        self.delete_button.clicked.connect(self.delete_animal)
        button_layout.addWidget(self.delete_button)
        
        self.export_button = QPushButton("导出CSV")
        self.export_button.clicked.connect(self.export_animals)
        button_layout.addWidget(self.export_button)
        
        layout.addLayout(button_layout)
        
        # 动物表格
        self.animals_table = QTableWidget()
        self.animals_table.setColumnCount(8)
        self.animals_table.setHorizontalHeaderLabels([
            "耳标", "物种", "品种", "出生日期", "性别", "体重(kg)", "健康状态", "位置"
        ])
        self.animals_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.animals_table.doubleClicked.connect(self.edit_animal)
        
        layout.addWidget(self.animals_table)
        self.setLayout(layout)
    
    def load_animals(self):
        """加载动物数据"""
        animals = self.db.execute_query("SELECT * FROM animals ORDER BY ear_tag")
        
        self.animals_table.setRowCount(len(animals))
        
        for row, animal in enumerate(animals):
            self.animals_table.setItem(row, 0, QTableWidgetItem(animal[1]))  # 耳标
            self.animals_table.setItem(row, 1, QTableWidgetItem(animal[2]))  # 物种
            self.animals_table.setItem(row, 2, QTableWidgetItem(animal[3] or ""))  # 品种
            self.animals_table.setItem(row, 3, QTableWidgetItem(animal[4] or ""))  # 出生日期
            self.animals_table.setItem(row, 4, QTableWidgetItem(animal[5] or ""))  # 性别
            self.animals_table.setItem(row, 5, QTableWidgetItem(str(animal[6] or 0)))  # 体重
            self.animals_table.setItem(row, 6, QTableWidgetItem(animal[7] or ""))  # 健康状态
            self.animals_table.setItem(row, 7, QTableWidgetItem(animal[8] or ""))  # 位置
        
        # 更新物种过滤器
        species_list = self.db.execute_query("SELECT DISTINCT species FROM animals ORDER BY species")
        self.species_filter.clear()
        self.species_filter.addItem("所有物种")
        for species in species_list:
            self.species_filter.addItem(species[0])
    
    def filter_animals(self):
        """过滤动物列表"""
        search_text = self.search_input.text().lower()
        species_filter = self.species_filter.currentText()
        health_filter = self.health_filter.currentText()
        
        for row in range(self.animals_table.rowCount()):
            show_row = True
            
            # 文本搜索
            if search_text:
                row_text = ""
                for col in range(self.animals_table.columnCount()):
                    item = self.animals_table.item(row, col)
                    if item:
                        row_text += item.text().lower() + " "
                
                if search_text not in row_text:
                    show_row = False
            
            # 物种过滤
            if show_row and species_filter != "所有物种":
                species_item = self.animals_table.item(row, 1)
                if species_item and species_item.text() != species_filter:
                    show_row = False
            
            # 健康状态过滤
            if show_row and health_filter != "所有状态":
                health_item = self.animals_table.item(row, 6)
                if health_item and health_item.text() != health_filter:
                    show_row = False
            
            self.animals_table.setRowHidden(row, not show_row)
    
    def add_animal(self):
        """添加新动物"""
        dialog = AnimalDialog(self.db)
        if dialog.exec_():
            self.load_animals()
    
    def edit_animal(self):
        """编辑选中动物"""
        current_row = self.animals_table.currentRow()
        if current_row == -1:
            QMessageBox.warning(self, "警告", "请先选择一个动物")
            return
        
        ear_tag = self.animals_table.item(current_row, 0).text()
        dialog = AnimalDialog(self.db, ear_tag)
        if dialog.exec_():
            self.load_animals()
    
    def delete_animal(self):
        """删除选中动物"""
        current_row = self.animals_table.currentRow()
        if current_row == -1:
            QMessageBox.warning(self, "警告", "请先选择一个动物")
            return
        
        ear_tag = self.animals_table.item(current_row, 0).text()
        reply = QMessageBox.question(
            self, "确认删除", 
            f"确定要删除耳标为 {ear_tag} 的动物吗？此操作不可撤销。",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            if self.db.execute_update("DELETE FROM animals WHERE ear_tag = ?", (ear_tag,)):
                QMessageBox.information(self, "成功", "动物记录已删除")
                self.load_animals()
            else:
                QMessageBox.critical(self, "错误", "删除失败")
    
    def export_animals(self):
        """导出动物数据到CSV"""
        filepath, _ = QFileDialog.getSaveFileName(
            self, "导出动物数据", "", "CSV文件 (*.csv)"
        )
        
        if filepath:
            io_handler = DataIOHandler(self.db)
            if io_handler.export_to_csv('animals', filepath):
                QMessageBox.information(self, "成功", "数据导出成功")
            else:
                QMessageBox.critical(self, "错误", "数据导出失败")


class AnimalDialog(QDialog):
    """动物信息对话框"""
    
    def __init__(self, db_manager, ear_tag=None):
        super().__init__()
        self.db = db_manager
        self.ear_tag = ear_tag
        self.init_ui()
        self.load_animal_data()
    
    def init_ui(self):
        self.setWindowTitle("动物信息" if self.ear_tag else "添加动物")
        self.setModal(True)
        self.resize(400, 500)
        
        layout = QFormLayout()
        
        # 耳标
        self.ear_tag_input = QLineEdit()
        layout.addRow("耳标*:", self.ear_tag_input)
        
        # 物种
        self.species_combo = QComboBox()
        self.species_combo.addItems(["牛", "羊", "猪", "鸡", "鸭", "其他"])
        self.species_combo.setEditable(True)
        layout.addRow("物种*:", self.species_combo)
        
        # 品种
        self.breed_input = QLineEdit()
        layout.addRow("品种:", self.breed_input)
        
        # 出生日期
        self.birth_date_edit = QDateEdit()
        self.birth_date_edit.setCalendarPopup(True)
        self.birth_date_edit.setDate(QDate.currentDate())
        layout.addRow("出生日期:", self.birth_date_edit)
        
        # 性别
        self.gender_combo = QComboBox()
        self.gender_combo.addItems(["", "公", "母"])
        layout.addRow("性别:", self.gender_combo)
        
        # 体重
        self.weight_spin = QDoubleSpinBox()
        self.weight_spin.setSuffix(" kg")
        self.weight_spin.setRange(0, 1000)
        layout.addRow("体重:", self.weight_spin)
        
        # 健康状态
        self.health_combo = QComboBox()
        self.health_combo.addItems(["良好", "一般", "需关注", "生病"])
        layout.addRow("健康状态:", self.health_combo)
        
        # 位置
        self.location_input = QLineEdit()
        layout.addRow("位置:", self.location_input)
        
        # 备注
        self.notes_edit = QTextEdit()
        self.notes_edit.setMaximumHeight(100)
        layout.addRow("备注:", self.notes_edit)
        
        # 按钮
        button_layout = QHBoxLayout()
        
        self.save_button = QPushButton("保存")
        self.save_button.clicked.connect(self.save_animal)
        button_layout.addWidget(self.save_button)
        
        self.cancel_button = QPushButton("取消")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        layout.addRow(button_layout)
        
        self.setLayout(layout)
    
    def load_animal_data(self):
        """加载动物数据（编辑模式）"""
        if self.ear_tag:
            animal = self.db.execute_query(
                "SELECT * FROM animals WHERE ear_tag = ?", (self.ear_tag,)
            )
            
            if animal:
                animal = animal[0]
                self.ear_tag_input.setText(animal[1])
                self.ear_tag_input.setEnabled(False)  # 编辑模式下不能修改耳标
                
                self.species_combo.setCurrentText(animal[2] or "")
                self.breed_input.setText(animal[3] or "")
                
                if animal[4]:
                    birth_date = QDate.fromString(animal[4], 'yyyy-MM-dd')
                    self.birth_date_edit.setDate(birth_date)
                
                self.gender_combo.setCurrentText(animal[5] or "")
                self.weight_spin.setValue(animal[6] or 0)
                self.health_combo.setCurrentText(animal[7] or "良好")
                self.location_input.setText(animal[8] or "")
                self.notes_edit.setPlainText(animal[9] or "")
    
    def save_animal(self):
        """保存动物信息"""
        # 验证必填字段
        ear_tag = self.ear_tag_input.text().strip()
        species = self.species_combo.currentText().strip()
        
        if not ear_tag:
            QMessageBox.warning(self, "警告", "耳标不能为空")
            return
        
        if not species:
            QMessageBox.warning(self, "警告", "物种不能为空")
            return
        
        # 准备数据
        birth_date = self.birth_date_edit.date().toString('yyyy-MM-dd')
        current_date = datetime.now().strftime('%Y-%m-%d')
        
        if self.ear_tag:  # 更新现有记录
            query = """
            UPDATE animals SET 
            species=?, breed=?, birth_date=?, gender=?, weight=?, 
            health_status=?, location=?, notes=?, updated_date=?
            WHERE ear_tag=?
            """
            params = (
                species, self.breed_input.text(), birth_date, 
                self.gender_combo.currentText(), self.weight_spin.value(),
                self.health_combo.currentText(), self.location_input.text(),
                self.notes_edit.toPlainText(), current_date, ear_tag
            )
        else:  # 插入新记录
            query = """
            INSERT INTO animals 
            (ear_tag, species, breed, birth_date, gender, weight, health_status, location, notes, created_date, updated_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            params = (
                ear_tag, species, self.breed_input.text(), birth_date,
                self.gender_combo.currentText(), self.weight_spin.value(),
                self.health_combo.currentText(), self.location_input.text(),
                self.notes_edit.toPlainText(), current_date, current_date
            )
        
        if self.db.execute_update(query, params):
            QMessageBox.information(self, "成功", "动物信息已保存")
            self.accept()
        else:
            QMessageBox.critical(self, "错误", "保存失败，请检查耳标是否唯一")


# ============================ 主窗口 ============================
class LivestockSystem(QMainWindow):
    """畜牧业系统主窗口"""
    
    def __init__(self):
        super().__init__()
        self.db = LivestockDatabase()
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("高级畜牧业管理系统")
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
        
        self.animals_tab = AnimalManagementWidget(self.db)
        self.tabs.addTab(self.animals_tab, "动物管理")
        
        # 添加其他选项卡...
        self.feeding_tab = QWidget()  # 饲养管理
        self.tabs.addTab(self.feeding_tab, "饲养管理")
        
        self.health_tab = QWidget()  # 健康管理
        self.tabs.addTab(self.health_tab, "健康管理")
        
        self.breeding_tab = QWidget()  # 繁殖管理
        self.tabs.addTab(self.breeding_tab, "繁殖管理")
        
        self.production_tab = QWidget()  # 生产管理
        self.tabs.addTab(self.production_tab, "生产管理")
        
        self.analysis_tab = QWidget()  # 数据分析
        self.tabs.addTab(self.analysis_tab, "数据分析")
        
        self.reports_tab = QWidget()  # 报告生成
        self.tabs.addTab(self.reports_tab, "报告生成")
        
        # 创建状态栏
        self.statusBar().showMessage("就绪")
        
        # 创建菜单栏
        self.create_menubar()
    
    def create_menubar(self):
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu('文件')
        
        import_action = file_menu.addAction('导入数据')
        import_action.triggered.connect(self.import_data)
        
        export_action = file_menu.addAction('导出数据')
        export_action.triggered.connect(self.export_data)
        
        file_menu.addSeparator()
        
        exit_action = file_menu.addAction('退出')
        exit_action.triggered.connect(self.close)
        
        # 工具菜单
        tools_menu = menubar.addMenu('工具')
        
        backup_action = tools_menu.addAction('备份数据库')
        backup_action.triggered.connect(self.backup_database)
        
        restore_action = tools_menu.addAction('恢复数据库')
        restore_action.triggered.connect(self.restore_database)
        
        # 帮助菜单
        help_menu = menubar.addMenu('帮助')
        
        about_action = help_menu.addAction('关于')
        about_action.triggered.connect(self.show_about)
    
    def import_data(self):
        """导入数据"""
        filepath, _ = QFileDialog.getOpenFileName(
            self, "选择CSV文件", "", "CSV文件 (*.csv)"
        )
        
        if filepath:
            io_handler = DataIOHandler(self.db)
            if io_handler.import_from_csv(filepath, 'animals'):
                QMessageBox.information(self, "成功", "数据导入成功")
                # 刷新相关选项卡
                self.dashboard_tab.load_data()
                self.animals_tab.load_animals()
            else:
                QMessageBox.critical(self, "错误", "数据导入失败")
    
    def export_data(self):
        """导出数据"""
        # 简化实现，实际应用中可以根据需要扩展
        self.animals_tab.export_animals()
    
    def backup_database(self):
        """备份数据库"""
        filepath, _ = QFileDialog.getSaveFileName(
            self, "备份数据库", "", "SQLite数据库 (*.db)"
        )
        
        if filepath:
            import shutil
            try:
                shutil.copy2("livestock.db", filepath)
                QMessageBox.information(self, "成功", "数据库备份成功")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"备份失败: {str(e)}")
    
    def restore_database(self):
        """恢复数据库"""
        filepath, _ = QFileDialog.getOpenFileName(
            self, "选择备份文件", "", "SQLite数据库 (*.db)"
        )
        
        if filepath:
            reply = QMessageBox.question(
                self, "确认恢复", 
                "恢复数据库将覆盖当前所有数据，是否继续？",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                import shutil
                try:
                    shutil.copy2(filepath, "livestock.db")
                    QMessageBox.information(self, "成功", "数据库恢复成功")
                    # 重启应用或重新加载数据
                    QMessageBox.information(self, "提示", "请重启应用以加载恢复的数据")
                except Exception as e:
                    QMessageBox.critical(self, "错误", f"恢复失败: {str(e)}")
    
    def show_about(self):
        """显示关于信息"""
        QMessageBox.about(self, "关于", 
                         "高级畜牧业管理系统 v1.0\n\n"
                         "功能强大的畜牧业管理工具，提供完整的动物管理、"
                         "数据分析、报告生成等功能。")


# ============================ 应用启动 ============================
if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # 设置应用样式
    app.setStyle('Fusion')
    
    # 创建并显示主窗口
    window = LivestockSystem()
    window.show()
    
    sys.exit(app.exec_())