import sys
import os
import json
import csv
import sqlite3
from datetime import datetime, timedelta
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QTableWidget, QTableWidgetItem, 
                             QLabel, QLineEdit, QTextEdit, QComboBox, QDateEdit, 
                             QMessageBox, QFileDialog, QProgressBar, QGroupBox, 
                             QSplitter, QTreeWidget, QTreeWidgetItem, QHeaderView)
from PyQt5.QtCore import Qt, QTimer, QDate
from PyQt5.QtGui import QFont, QIcon, QColor
from PyQt5.QtChart import QChart, QChartView, QPieSeries, QBarSeries, QBarSet, QBarCategoryAxis, QValueAxis
import matplotlib
matplotlib.rc("font", family='Microsoft YaHei')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import numpy as np
import pandas as pd


class AircraftMaintenanceToolkit(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("机务系统高级工具库")
        self.setGeometry(100, 100, 1200, 800)
        
        # 初始化数据库
        self.init_database()
        
        # 创建主界面
        self.create_main_ui()
        
        # 加载示例数据
        self.load_sample_data()
        
    def init_database(self):
        """初始化SQLite数据库"""
        self.conn = sqlite3.connect('aircraft_maintenance.db')
        self.cursor = self.conn.cursor()
        
        # 创建飞机信息表
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS aircrafts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tail_number TEXT UNIQUE,
                model TEXT,
                manufacturer TEXT,
                entry_date TEXT,
                status TEXT,
                last_maintenance TEXT,
                next_maintenance TEXT
            )
        ''')
        
        # 创建维护记录表
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS maintenance_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                aircraft_id INTEGER,
                maintenance_type TEXT,
                description TEXT,
                date TEXT,
                technician TEXT,
                duration_hours REAL,
                cost REAL,
                FOREIGN KEY (aircraft_id) REFERENCES aircrafts (id)
            )
        ''')
        
        # 创建部件库存表
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS parts_inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                part_number TEXT UNIQUE,
                name TEXT,
                category TEXT,
                quantity INTEGER,
                min_quantity INTEGER,
                supplier TEXT,
                price REAL
            )
        ''')
        
        self.conn.commit()
    
    def create_main_ui(self):
        """创建主界面"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        main_layout = QVBoxLayout(central_widget)
        
        # 创建标题
        title_label = QLabel("机务系统高级工具库")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setFont(QFont("Arial", 16, QFont.Bold))
        main_layout.addWidget(title_label)
        
        # 创建标签页
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        # 添加各个功能标签页
        self.create_aircraft_management_tab()
        self.create_maintenance_management_tab()
        self.create_parts_inventory_tab()
        self.create_maintenance_scheduler_tab()
        self.create_data_analysis_tab()
        self.create_report_generator_tab()
        
    def create_aircraft_management_tab(self):
        """创建飞机管理标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 顶部按钮组
        button_layout = QHBoxLayout()
        add_btn = QPushButton("添加飞机")
        add_btn.clicked.connect(self.add_aircraft)
        edit_btn = QPushButton("编辑飞机")
        edit_btn.clicked.connect(self.edit_aircraft)
        delete_btn = QPushButton("删除飞机")
        delete_btn.clicked.connect(self.delete_aircraft)
        refresh_btn = QPushButton("刷新")
        refresh_btn.clicked.connect(self.refresh_aircraft_table)
        
        button_layout.addWidget(add_btn)
        button_layout.addWidget(edit_btn)
        button_layout.addWidget(delete_btn)
        button_layout.addWidget(refresh_btn)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        
        # 飞机信息表格
        self.aircraft_table = QTableWidget()
        self.aircraft_table.setColumnCount(8)
        self.aircraft_table.setHorizontalHeaderLabels([
            "ID", "机尾号", "型号", "制造商", "入列日期", "状态", "上次维护", "下次维护"
        ])
        self.aircraft_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.aircraft_table)
        
        self.tab_widget.addTab(tab, "飞机管理")
        
    def create_maintenance_management_tab(self):
        """创建维护管理标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 顶部控件组
        top_layout = QHBoxLayout()
        
        # 左侧表单
        form_layout = QVBoxLayout()
        form_group = QGroupBox("维护记录信息")
        form_group_layout = QVBoxLayout(form_group)
        
        # 飞机选择
        aircraft_layout = QHBoxLayout()
        aircraft_layout.addWidget(QLabel("飞机:"))
        self.maintenance_aircraft_combo = QComboBox()
        aircraft_layout.addWidget(self.maintenance_aircraft_combo)
        form_group_layout.addLayout(aircraft_layout)
        
        # 维护类型
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("维护类型:"))
        self.maintenance_type_combo = QComboBox()
        self.maintenance_type_combo.addItems(["定期检查", "A检", "B检", "C检", "D检", "故障修复", "部件更换"])
        type_layout.addWidget(self.maintenance_type_combo)
        form_group_layout.addLayout(type_layout)
        
        # 维护日期
        date_layout = QHBoxLayout()
        date_layout.addWidget(QLabel("维护日期:"))
        self.maintenance_date_edit = QDateEdit()
        self.maintenance_date_edit.setDate(QDate.currentDate())
        date_layout.addWidget(self.maintenance_date_edit)
        form_group_layout.addLayout(date_layout)
        
        # 技术人员
        tech_layout = QHBoxLayout()
        tech_layout.addWidget(QLabel("技术人员:"))
        self.technician_edit = QLineEdit()
        tech_layout.addWidget(self.technician_edit)
        form_group_layout.addLayout(tech_layout)
        
        # 维护时长
        duration_layout = QHBoxLayout()
        duration_layout.addWidget(QLabel("维护时长(小时):"))
        self.duration_edit = QLineEdit()
        duration_layout.addWidget(self.duration_edit)
        form_group_layout.addLayout(duration_layout)
        
        # 维护成本
        cost_layout = QHBoxLayout()
        cost_layout.addWidget(QLabel("维护成本:"))
        self.cost_edit = QLineEdit()
        cost_layout.addWidget(self.cost_edit)
        form_group_layout.addLayout(cost_layout)
        
        # 维护描述
        desc_layout = QVBoxLayout()
        desc_layout.addWidget(QLabel("维护描述:"))
        self.description_edit = QTextEdit()
        self.description_edit.setMaximumHeight(100)
        desc_layout.addWidget(self.description_edit)
        form_group_layout.addLayout(desc_layout)
        
        # 按钮
        button_layout = QHBoxLayout()
        add_record_btn = QPushButton("添加记录")
        add_record_btn.clicked.connect(self.add_maintenance_record)
        clear_btn = QPushButton("清空")
        clear_btn.clicked.connect(self.clear_maintenance_form)
        button_layout.addWidget(add_record_btn)
        button_layout.addWidget(clear_btn)
        form_group_layout.addLayout(button_layout)
        
        form_layout.addWidget(form_group)
        top_layout.addLayout(form_layout, 1)
        
        # 右侧表格
        self.maintenance_table = QTableWidget()
        self.maintenance_table.setColumnCount(8)
        self.maintenance_table.setHorizontalHeaderLabels([
            "ID", "机尾号", "维护类型", "描述", "日期", "技术人员", "时长", "成本"
        ])
        self.maintenance_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        top_layout.addWidget(self.maintenance_table, 2)
        
        layout.addLayout(top_layout)
        
        self.tab_widget.addTab(tab, "维护管理")
        
    def create_parts_inventory_tab(self):
        """创建部件库存标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 顶部按钮组
        button_layout = QHBoxLayout()
        add_part_btn = QPushButton("添加部件")
        add_part_btn.clicked.connect(self.add_part)
        edit_part_btn = QPushButton("编辑部件")
        edit_part_btn.clicked.connect(self.edit_part)
        delete_part_btn = QPushButton("删除部件")
        delete_part_btn.clicked.connect(self.delete_part)
        low_stock_btn = QPushButton("低库存预警")
        low_stock_btn.clicked.connect(self.show_low_stock)
        import_btn = QPushButton("导入数据")
        import_btn.clicked.connect(self.import_parts_data)
        export_btn = QPushButton("导出数据")
        export_btn.clicked.connect(self.export_parts_data)
        
        button_layout.addWidget(add_part_btn)
        button_layout.addWidget(edit_part_btn)
        button_layout.addWidget(delete_part_btn)
        button_layout.addWidget(low_stock_btn)
        button_layout.addWidget(import_btn)
        button_layout.addWidget(export_btn)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        
        # 部件库存表格
        self.parts_table = QTableWidget()
        self.parts_table.setColumnCount(8)
        self.parts_table.setHorizontalHeaderLabels([
            "ID", "部件号", "名称", "类别", "库存量", "最小库存", "供应商", "价格"
        ])
        self.parts_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.parts_table)
        
        self.tab_widget.addTab(tab, "部件库存")
        
    def create_maintenance_scheduler_tab(self):
        """创建维护计划标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 顶部控件
        top_layout = QHBoxLayout()
        top_layout.addWidget(QLabel("筛选:"))
        self.schedule_filter_combo = QComboBox()
        self.schedule_filter_combo.addItems(["全部", "本周", "本月", "下月", "逾期"])
        self.schedule_filter_combo.currentTextChanged.connect(self.update_schedule_table)
        top_layout.addWidget(self.schedule_filter_combo)
        top_layout.addStretch()
        
        generate_btn = QPushButton("生成维护计划")
        generate_btn.clicked.connect(self.generate_maintenance_schedule)
        top_layout.addWidget(generate_btn)
        
        layout.addLayout(top_layout)
        
        # 维护计划表格
        self.schedule_table = QTableWidget()
        self.schedule_table.setColumnCount(6)
        self.schedule_table.setHorizontalHeaderLabels([
            "机尾号", "型号", "上次维护", "下次维护", "剩余天数", "状态"
        ])
        self.schedule_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.schedule_table)
        
        self.tab_widget.addTab(tab, "维护计划")
        
    def create_data_analysis_tab(self):
        """创建数据分析标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 分析类型选择
        analysis_layout = QHBoxLayout()
        analysis_layout.addWidget(QLabel("分析类型:"))
        self.analysis_type_combo = QComboBox()
        self.analysis_type_combo.addItems([
            "维护成本分析", 
            "飞机使用率分析", 
            "部件消耗分析", 
            "维护类型分布"
        ])
        self.analysis_type_combo.currentTextChanged.connect(self.update_analysis)
        analysis_layout.addWidget(self.analysis_type_combo)
        analysis_layout.addStretch()
        
        layout.addLayout(analysis_layout)
        
        # 图表区域
        self.analysis_chart_view = QChartView()
        self.analysis_chart_view.setMinimumHeight(400)
        layout.addWidget(self.analysis_chart_view)
        
        # 统计数据
        self.stats_text = QTextEdit()
        self.stats_text.setMaximumHeight(150)
        layout.addWidget(self.stats_text)
        
        self.tab_widget.addTab(tab, "数据分析")
        
    def create_report_generator_tab(self):
        """创建报告生成标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 报告类型选择
        report_layout = QHBoxLayout()
        report_layout.addWidget(QLabel("报告类型:"))
        self.report_type_combo = QComboBox()
        self.report_type_combo.addItems([
            "月度维护报告", 
            "飞机状态报告", 
            "库存报告", 
            "维护成本报告"
        ])
        report_layout.addWidget(self.report_type_combo)
        
        # 日期范围
        report_layout.addWidget(QLabel("开始日期:"))
        self.report_start_date = QDateEdit()
        self.report_start_date.setDate(QDate.currentDate().addMonths(-1))
        report_layout.addWidget(self.report_start_date)
        
        report_layout.addWidget(QLabel("结束日期:"))
        self.report_end_date = QDateEdit()
        self.report_end_date.setDate(QDate.currentDate())
        report_layout.addWidget(self.report_end_date)
        
        report_layout.addStretch()
        
        layout.addLayout(report_layout)
        
        # 报告内容
        self.report_text = QTextEdit()
        layout.addWidget(self.report_text)
        
        # 按钮
        button_layout = QHBoxLayout()
        generate_report_btn = QPushButton("生成报告")
        generate_report_btn.clicked.connect(self.generate_report)
        export_report_btn = QPushButton("导出报告")
        export_report_btn.clicked.connect(self.export_report)
        clear_report_btn = QPushButton("清空")
        clear_report_btn.clicked.connect(self.clear_report)
        
        button_layout.addWidget(generate_report_btn)
        button_layout.addWidget(export_report_btn)
        button_layout.addWidget(clear_report_btn)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        
        self.tab_widget.addTab(tab, "报告生成")
        
    def load_sample_data(self):
        """加载示例数据"""
        # 加载飞机数据
        self.refresh_aircraft_table()
        
        # 加载维护记录
        self.refresh_maintenance_table()
        
        # 加载部件库存
        self.refresh_parts_table()
        
        # 更新维护计划
        self.update_schedule_table()
        
        # 更新分析
        self.update_analysis()
        
    def refresh_aircraft_table(self):
        """刷新飞机表格"""
        self.cursor.execute("SELECT * FROM aircrafts")
        aircrafts = self.cursor.fetchall()
        
        self.aircraft_table.setRowCount(len(aircrafts))
        for row, aircraft in enumerate(aircrafts):
            for col, value in enumerate(aircraft):
                item = QTableWidgetItem(str(value))
                self.aircraft_table.setItem(row, col, item)
                
        # 更新维护管理页面的飞机选择
        self.maintenance_aircraft_combo.clear()
        for aircraft in aircrafts:
            self.maintenance_aircraft_combo.addItem(f"{aircraft[1]} - {aircraft[2]}", aircraft[0])
    
    def refresh_maintenance_table(self):
        """刷新维护记录表格"""
        self.cursor.execute('''
            SELECT mr.id, a.tail_number, mr.maintenance_type, mr.description, 
                   mr.date, mr.technician, mr.duration_hours, mr.cost
            FROM maintenance_records mr
            JOIN aircrafts a ON mr.aircraft_id = a.id
            ORDER BY mr.date DESC
        ''')
        records = self.cursor.fetchall()
        
        self.maintenance_table.setRowCount(len(records))
        for row, record in enumerate(records):
            for col, value in enumerate(record):
                item = QTableWidgetItem(str(value))
                self.maintenance_table.setItem(row, col, item)
    
    def refresh_parts_table(self):
        """刷新部件库存表格"""
        self.cursor.execute("SELECT * FROM parts_inventory")
        parts = self.cursor.fetchall()
        
        self.parts_table.setRowCount(len(parts))
        for row, part in enumerate(parts):
            for col, value in enumerate(part):
                item = QTableWidgetItem(str(value))
                # 标记低库存项目
                if col == 4 and value is not None and part[5] is not None and value <= part[5]:
                    item.setBackground(QColor(255, 200, 200))
                self.parts_table.setItem(row, col, item)
    
    def update_schedule_table(self):
        """更新维护计划表格"""
        # 获取筛选条件
        filter_text = self.schedule_filter_combo.currentText()
        
        # 构建查询条件
        today = datetime.now().date()
        if filter_text == "本周":
            end_date = today + timedelta(days=7)
            condition = f"WHERE next_maintenance BETWEEN '{today}' AND '{end_date}'"
        elif filter_text == "本月":
            end_date = today.replace(day=28) + timedelta(days=4)  # 获取本月最后一天
            condition = f"WHERE next_maintenance BETWEEN '{today}' AND '{end_date}'"
        elif filter_text == "下月":
            next_month = today.replace(day=28) + timedelta(days=4)  # 本月最后一天
            next_month = next_month.replace(day=1)  # 下月第一天
            end_date = next_month.replace(day=28) + timedelta(days=4)  # 下月最后一天
            condition = f"WHERE next_maintenance BETWEEN '{next_month}' AND '{end_date}'"
        elif filter_text == "逾期":
            condition = f"WHERE next_maintenance < '{today}'"
        else:
            condition = ""
        
        self.cursor.execute(f'''
            SELECT tail_number, model, last_maintenance, next_maintenance, 
                   julianday(next_maintenance) - julianday('now') as days_remaining,
                   CASE 
                     WHEN next_maintenance < date('now') THEN '逾期'
                     WHEN julianday(next_maintenance) - julianday('now') <= 7 THEN '紧急'
                     WHEN julianday(next_maintenance) - julianday('now') <= 30 THEN '即将到期'
                     ELSE '正常'
                   END as status
            FROM aircrafts
            {condition}
            ORDER BY next_maintenance
        ''')
        schedules = self.cursor.fetchall()
        
        self.schedule_table.setRowCount(len(schedules))
        for row, schedule in enumerate(schedules):
            for col, value in enumerate(schedule):
                item = QTableWidgetItem(str(value))
                
                # 根据状态设置颜色
                if col == 5:  # 状态列
                    if value == "逾期":
                        item.setBackground(QColor(255, 100, 100))
                    elif value == "紧急":
                        item.setBackground(QColor(255, 200, 100))
                    elif value == "即将到期":
                        item.setBackground(QColor(255, 255, 100))
                
                self.schedule_table.setItem(row, col, item)
    
    def update_analysis(self):
        """更新数据分析"""
        analysis_type = self.analysis_type_combo.currentText()
        
        if analysis_type == "维护成本分析":
            self.show_maintenance_cost_analysis()
        elif analysis_type == "飞机使用率分析":
            self.show_aircraft_utilization_analysis()
        elif analysis_type == "部件消耗分析":
            self.show_parts_consumption_analysis()
        elif analysis_type == "维护类型分布":
            self.show_maintenance_type_distribution()
    
    def show_maintenance_cost_analysis(self):
        """显示维护成本分析"""
        self.cursor.execute('''
            SELECT a.tail_number, SUM(mr.cost) as total_cost
            FROM maintenance_records mr
            JOIN aircrafts a ON mr.aircraft_id = a.id
            GROUP BY a.tail_number
            ORDER BY total_cost DESC
        ''')
        data = self.cursor.fetchall()
        
        # 创建图表
        chart = QChart()
        chart.setTitle("飞机维护成本分析")
        
        series = QBarSeries()
        
        aircrafts = [item[0] for item in data]
        costs = [item[1] for item in data]
        
        bar_set = QBarSet("维护成本")
        for cost in costs:
            bar_set.append(cost)
        
        series.append(bar_set)
        chart.addSeries(series)
        
        # 设置X轴
        axis_x = QBarCategoryAxis()
        axis_x.append(aircrafts)
        chart.addAxis(axis_x, Qt.AlignBottom)
        series.attachAxis(axis_x)
        
        # 设置Y轴
        axis_y = QValueAxis()
        axis_y.setLabelFormat("%.0f")
        chart.addAxis(axis_y, Qt.AlignLeft)
        series.attachAxis(axis_y)
        
        self.analysis_chart_view.setChart(chart)
        
        # 显示统计信息
        total_cost = sum(costs)
        avg_cost = total_cost / len(costs) if costs else 0
        max_cost = max(costs) if costs else 0
        min_cost = min(costs) if costs else 0
        
        stats_text = f"""
        维护成本统计:
        - 总维护成本: {total_cost:.2f} 元
        - 平均维护成本: {avg_cost:.2f} 元/飞机
        - 最高维护成本: {max_cost:.2f} 元
        - 最低维护成本: {min_cost:.2f} 元
        - 分析飞机数量: {len(aircrafts)} 架
        """
        self.stats_text.setText(stats_text)
    
    def show_aircraft_utilization_analysis(self):
        """显示飞机使用率分析"""
        # 这里简化处理，实际应根据飞行小时数等数据计算
        self.cursor.execute('''
            SELECT a.tail_number, COUNT(mr.id) as maintenance_count
            FROM aircrafts a
            LEFT JOIN maintenance_records mr ON a.id = mr.aircraft_id
            GROUP BY a.tail_number
            ORDER BY maintenance_count DESC
        ''')
        data = self.cursor.fetchall()
        
        # 创建饼图
        series = QPieSeries()
        series.setLabelsVisible(True)
        
        for item in data:
            series.append(f"{item[0]} ({item[1]})", item[1])
        
        chart = QChart()
        chart.addSeries(series)
        chart.setTitle("飞机维护次数分布")
        chart.legend().setVisible(True)
        chart.legend().setAlignment(Qt.AlignRight)
        
        self.analysis_chart_view.setChart(chart)
        
        # 显示统计信息
        total_count = sum(item[1] for item in data)
        avg_count = total_count / len(data) if data else 0
        max_count = max(item[1] for item in data) if data else 0
        
        stats_text = f"""
        飞机使用率统计:
        - 总维护次数: {total_count} 次
        - 平均维护次数: {avg_count:.1f} 次/飞机
        - 最高维护次数: {max_count} 次
        - 分析飞机数量: {len(data)} 架
        """
        self.stats_text.setText(stats_text)
    
    def show_parts_consumption_analysis(self):
        """显示部件消耗分析"""
        # 简化处理，实际应根据部件使用记录计算
        self.cursor.execute('''
            SELECT category, SUM(quantity) as total_quantity
            FROM parts_inventory
            GROUP BY category
            ORDER BY total_quantity DESC
        ''')
        data = self.cursor.fetchall()
        
        # 创建图表
        chart = QChart()
        chart.setTitle("部件库存分类分析")
        
        series = QBarSeries()
        
        categories = [item[0] for item in data]
        quantities = [item[1] for item in data]
        
        bar_set = QBarSet("库存数量")
        for quantity in quantities:
            bar_set.append(quantity)
        
        series.append(bar_set)
        chart.addSeries(series)
        
        # 设置X轴
        axis_x = QBarCategoryAxis()
        axis_x.append(categories)
        chart.addAxis(axis_x, Qt.AlignBottom)
        series.attachAxis(axis_x)
        
        # 设置Y轴
        axis_y = QValueAxis()
        axis_y.setLabelFormat("%.0f")
        chart.addAxis(axis_y, Qt.AlignLeft)
        series.attachAxis(axis_y)
        
        self.analysis_chart_view.setChart(chart)
        
        # 显示统计信息
        total_quantity = sum(quantities)
        category_count = len(categories)
        
        stats_text = f"""
        部件库存统计:
        - 总库存数量: {total_quantity} 个
        - 部件类别数量: {category_count} 类
        - 平均每类库存: {total_quantity/category_count:.1f} 个
        """
        self.stats_text.setText(stats_text)
    
    def show_maintenance_type_distribution(self):
        """显示维护类型分布"""
        self.cursor.execute('''
            SELECT maintenance_type, COUNT(*) as count
            FROM maintenance_records
            GROUP BY maintenance_type
            ORDER BY count DESC
        ''')
        data = self.cursor.fetchall()
        
        # 创建饼图
        series = QPieSeries()
        series.setLabelsVisible(True)
        
        for item in data:
            series.append(f"{item[0]} ({item[1]})", item[1])
        
        chart = QChart()
        chart.addSeries(series)
        chart.setTitle("维护类型分布")
        chart.legend().setVisible(True)
        chart.legend().setAlignment(Qt.AlignRight)
        
        self.analysis_chart_view.setChart(chart)
        
        # 显示统计信息
        total_count = sum(item[1] for item in data)
        
        stats_text = f"""
        维护类型统计:
        - 总维护记录: {total_count} 条
        - 维护类型数量: {len(data)} 种
        """
        self.stats_text.setText(stats_text)
    
    def add_aircraft(self):
        """添加飞机"""
        # 在实际应用中，这里应该打开一个对话框来输入飞机信息
        # 这里简化处理，直接插入示例数据
        sample_aircrafts = [
            ("B-1234", "A320", "Airbus", "2020-01-15", "运营中", "2023-06-01", "2023-12-01"),
            ("B-5678", "B737", "Boeing", "2019-08-20", "运营中", "2023-05-15", "2023-11-15"),
            ("B-9012", "A330", "Airbus", "2021-03-10", "维修中", "2023-07-01", "2024-01-01"),
            ("B-3456", "B787", "Boeing", "2022-05-05", "运营中", "2023-04-20", "2023-10-20")
        ]
        
        for aircraft in sample_aircrafts:
            try:
                self.cursor.execute('''
                    INSERT INTO aircrafts (tail_number, model, manufacturer, entry_date, status, last_maintenance, next_maintenance)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', aircraft)
            except sqlite3.IntegrityError:
                # 如果机尾号已存在，跳过
                pass
        
        self.conn.commit()
        self.refresh_aircraft_table()
        QMessageBox.information(self, "成功", "示例飞机数据已添加")
    
    def edit_aircraft(self):
        """编辑飞机"""
        current_row = self.aircraft_table.currentRow()
        if current_row == -1:
            QMessageBox.warning(self, "警告", "请先选择要编辑的飞机")
            return
        
        # 在实际应用中，这里应该打开一个对话框来编辑飞机信息
        # 这里简化处理，只显示提示
        tail_number = self.aircraft_table.item(current_row, 1).text()
        QMessageBox.information(self, "提示", f"编辑飞机 {tail_number} 的功能将在完整版本中实现")
    
    def delete_aircraft(self):
        """删除飞机"""
        current_row = self.aircraft_table.currentRow()
        if current_row == -1:
            QMessageBox.warning(self, "警告", "请先选择要删除的飞机")
            return
        
        aircraft_id = self.aircraft_table.item(current_row, 0).text()
        tail_number = self.aircraft_table.item(current_row, 1).text()
        
        reply = QMessageBox.question(self, "确认删除", 
                                    f"确定要删除飞机 {tail_number} 吗？",
                                    QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.cursor.execute("DELETE FROM aircrafts WHERE id = ?", (aircraft_id,))
            self.conn.commit()
            self.refresh_aircraft_table()
            QMessageBox.information(self, "成功", "飞机已删除")
    
    def add_maintenance_record(self):
        """添加维护记录"""
        # 获取表单数据
        aircraft_id = self.maintenance_aircraft_combo.currentData()
        maintenance_type = self.maintenance_type_combo.currentText()
        date = self.maintenance_date_edit.date().toString("yyyy-MM-dd")
        technician = self.technician_edit.text()
        description = self.description_edit.toPlainText()
        
        # 验证数据
        if not aircraft_id:
            QMessageBox.warning(self, "警告", "请选择飞机")
            return
        
        if not technician:
            QMessageBox.warning(self, "警告", "请输入技术人员")
            return
        
        try:
            duration = float(self.duration_edit.text()) if self.duration_edit.text() else 0
            cost = float(self.cost_edit.text()) if self.cost_edit.text() else 0
        except ValueError:
            QMessageBox.warning(self, "警告", "时长和成本必须是数字")
            return
        
        # 插入数据库
        self.cursor.execute('''
            INSERT INTO maintenance_records 
            (aircraft_id, maintenance_type, description, date, technician, duration_hours, cost)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (aircraft_id, maintenance_type, description, date, technician, duration, cost))
        
        # 更新飞机的上次维护日期
        self.cursor.execute('''
            UPDATE aircrafts 
            SET last_maintenance = ?
            WHERE id = ?
        ''', (date, aircraft_id))
        
        self.conn.commit()
        
        # 刷新表格
        self.refresh_maintenance_table()
        self.refresh_aircraft_table()
        
        QMessageBox.information(self, "成功", "维护记录已添加")
        self.clear_maintenance_form()
    
    def clear_maintenance_form(self):
        """清空维护表单"""
        self.maintenance_type_combo.setCurrentIndex(0)
        self.maintenance_date_edit.setDate(QDate.currentDate())
        self.technician_edit.clear()
        self.duration_edit.clear()
        self.cost_edit.clear()
        self.description_edit.clear()
    
    def add_part(self):
        """添加部件"""
        # 在实际应用中，这里应该打开一个对话框来输入部件信息
        # 这里简化处理，直接插入示例数据
        sample_parts = [
            ("PN-001", "发动机叶片", "发动机部件", 50, 10, "GE航空", 5000.00),
            ("PN-002", "起落架轮胎", "起落架部件", 20, 5, "米其林", 3000.00),
            ("PN-003", "机翼襟翼", "机翼部件", 10, 2, "波音", 15000.00),
            ("PN-004", "驾驶舱仪表", "电子设备", 30, 8, "霍尼韦尔", 8000.00),
            ("PN-005", "客舱座椅", "客舱设备", 40, 15, "赛峰", 2000.00)
        ]
        
        for part in sample_parts:
            try:
                self.cursor.execute('''
                    INSERT INTO parts_inventory (part_number, name, category, quantity, min_quantity, supplier, price)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', part)
            except sqlite3.IntegrityError:
                # 如果部件号已存在，跳过
                pass
        
        self.conn.commit()
        self.refresh_parts_table()
        QMessageBox.information(self, "成功", "示例部件数据已添加")
    
    def edit_part(self):
        """编辑部件"""
        current_row = self.parts_table.currentRow()
        if current_row == -1:
            QMessageBox.warning(self, "警告", "请先选择要编辑的部件")
            return
        
        # 在实际应用中，这里应该打开一个对话框来编辑部件信息
        # 这里简化处理，只显示提示
        part_number = self.parts_table.item(current_row, 1).text()
        QMessageBox.information(self, "提示", f"编辑部件 {part_number} 的功能将在完整版本中实现")
    
    def delete_part(self):
        """删除部件"""
        current_row = self.parts_table.currentRow()
        if current_row == -1:
            QMessageBox.warning(self, "警告", "请先选择要删除的部件")
            return
        
        part_id = self.parts_table.item(current_row, 0).text()
        part_number = self.parts_table.item(current_row, 1).text()
        
        reply = QMessageBox.question(self, "确认删除", 
                                    f"确定要删除部件 {part_number} 吗？",
                                    QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.cursor.execute("DELETE FROM parts_inventory WHERE id = ?", (part_id,))
            self.conn.commit()
            self.refresh_parts_table()
            QMessageBox.information(self, "成功", "部件已删除")
    
    def show_low_stock(self):
        """显示低库存预警"""
        self.cursor.execute('''
            SELECT part_number, name, quantity, min_quantity
            FROM parts_inventory
            WHERE quantity <= min_quantity
        ''')
        low_stock_parts = self.cursor.fetchall()
        
        if not low_stock_parts:
            QMessageBox.information(self, "库存状态", "当前没有低库存部件")
            return
        
        # 创建低库存报告
        report = "低库存预警:\n\n"
        for part in low_stock_parts:
            report += f"部件号: {part[0]}, 名称: {part[1]}, 当前库存: {part[2]}, 最小库存: {part[3]}\n"
        
        QMessageBox.warning(self, "低库存预警", report)
    
    def import_parts_data(self):
        """导入部件数据"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择数据文件", "", "CSV文件 (*.csv);;所有文件 (*)"
        )
        
        if file_path:
            try:
                # 读取CSV文件
                df = pd.read_csv(file_path)
                
                # 插入数据库
                for _, row in df.iterrows():
                    try:
                        self.cursor.execute('''
                            INSERT INTO parts_inventory 
                            (part_number, name, category, quantity, min_quantity, supplier, price)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            row.get('part_number', ''),
                            row.get('name', ''),
                            row.get('category', ''),
                            row.get('quantity', 0),
                            row.get('min_quantity', 0),
                            row.get('supplier', ''),
                            row.get('price', 0.0)
                        ))
                    except sqlite3.IntegrityError:
                        # 如果部件号已存在，跳过
                        pass
                
                self.conn.commit()
                self.refresh_parts_table()
                QMessageBox.information(self, "成功", "部件数据导入成功")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导入数据时出错: {str(e)}")
    
    def export_parts_data(self):
        """导出部件数据"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存数据文件", "parts_inventory.csv", "CSV文件 (*.csv)"
        )
        
        if file_path:
            try:
                # 从数据库获取数据
                self.cursor.execute("SELECT * FROM parts_inventory")
                parts = self.cursor.fetchall()
                
                # 写入CSV文件
                with open(file_path, 'w', newline='', encoding='utf-8') as file:
                    writer = csv.writer(file)
                    writer.writerow(['ID', '部件号', '名称', '类别', '库存量', '最小库存', '供应商', '价格'])
                    writer.writerows(parts)
                
                QMessageBox.information(self, "成功", "部件数据导出成功")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导出数据时出错: {str(e)}")
    
    def generate_maintenance_schedule(self):
        """生成维护计划"""
        # 在实际应用中，这里应根据维护规则生成计划
        # 这里简化处理，只显示提示
        QMessageBox.information(self, "提示", "维护计划生成功能将在完整版本中实现")
    
    def generate_report(self):
        """生成报告"""
        report_type = self.report_type_combo.currentText()
        start_date = self.report_start_date.date().toString("yyyy-MM-dd")
        end_date = self.report_end_date.date().toString("yyyy-MM-dd")
        
        if report_type == "月度维护报告":
            self.generate_monthly_maintenance_report(start_date, end_date)
        elif report_type == "飞机状态报告":
            self.generate_aircraft_status_report()
        elif report_type == "库存报告":
            self.generate_inventory_report()
        elif report_type == "维护成本报告":
            self.generate_maintenance_cost_report(start_date, end_date)
    
    def generate_monthly_maintenance_report(self, start_date, end_date):
        """生成月度维护报告"""
        self.cursor.execute('''
            SELECT a.tail_number, a.model, mr.maintenance_type, mr.date, 
                   mr.technician, mr.duration_hours, mr.cost, mr.description
            FROM maintenance_records mr
            JOIN aircrafts a ON mr.aircraft_id = a.id
            WHERE mr.date BETWEEN ? AND ?
            ORDER BY mr.date
        ''', (start_date, end_date))
        
        records = self.cursor.fetchall()
        
        # 计算统计信息
        total_records = len(records)
        total_cost = sum(record[6] for record in records) if records else 0
        total_duration = sum(record[5] for record in records) if records else 0
        
        # 生成报告
        report = f"""
        ==================== 月度维护报告 ====================
        报告期间: {start_date} 至 {end_date}
        生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        
        统计摘要:
        - 维护记录总数: {total_records} 条
        - 总维护成本: {total_cost:.2f} 元
        - 总维护时长: {total_duration:.2f} 小时
        
        详细记录:
        """
        
        for record in records:
            report += f"""
        机尾号: {record[0]}    型号: {record[1]}
        维护类型: {record[2]}    日期: {record[3]}
        技术人员: {record[4]}    时长: {record[5]}小时
        成本: {record[6]:.2f}元
        描述: {record[7]}
        -----------------------------------------
            """
        
        self.report_text.setText(report)
    
    def generate_aircraft_status_report(self):
        """生成飞机状态报告"""
        self.cursor.execute('''
            SELECT tail_number, model, manufacturer, entry_date, status, 
                   last_maintenance, next_maintenance
            FROM aircrafts
            ORDER BY status, next_maintenance
        ''')
        
        aircrafts = self.cursor.fetchall()
        
        # 统计各状态飞机数量
        status_count = {}
        for aircraft in aircrafts:
            status = aircraft[4]
            status_count[status] = status_count.get(status, 0) + 1
        
        # 生成报告
        report = f"""
        ==================== 飞机状态报告 ====================
        生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        
        状态统计:
        """
        
        for status, count in status_count.items():
            report += f"- {status}: {count} 架\n"
        
        report += f"\n飞机总数: {len(aircrafts)} 架\n\n详细列表:\n"
        
        for aircraft in aircrafts:
            report += f"""
        机尾号: {aircraft[0]}    型号: {aircraft[1]}
        制造商: {aircraft[2]}    入列日期: {aircraft[3]}
        状态: {aircraft[4]}    上次维护: {aircraft[5]}
        下次维护: {aircraft[6]}
        -----------------------------------------
            """
        
        self.report_text.setText(report)
    
    def generate_inventory_report(self):
        """生成库存报告"""
        self.cursor.execute('''
            SELECT part_number, name, category, quantity, min_quantity, supplier, price
            FROM parts_inventory
            ORDER BY category, part_number
        ''')
        
        parts = self.cursor.fetchall()
        
        # 统计各分类部件数量
        category_count = {}
        total_value = 0
        
        for part in parts:
            category = part[2]
            category_count[category] = category_count.get(category, 0) + 1
            total_value += part[3] * part[6]  # 数量 * 价格
        
        # 低库存部件
        low_stock_parts = [p for p in parts if p[3] <= p[4]]
        
        # 生成报告
        report = f"""
        ==================== 库存报告 ====================
        生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        
        分类统计:
        """
        
        for category, count in category_count.items():
            report += f"- {category}: {count} 种部件\n"
        
        report += f"""
        部件总数: {len(parts)} 种
        库存总价值: {total_value:.2f} 元
        低库存部件: {len(low_stock_parts)} 种
        
        低库存预警:
        """
        
        for part in low_stock_parts:
            report += f"- {part[0]} ({part[1]}): 当前库存 {part[3]}, 最小库存 {part[4]}\n"
        
        report += f"\n详细列表:\n"
        
        for part in parts:
            status = "低库存" if part[3] <= part[4] else "正常"
            report += f"""
        部件号: {part[0]}    名称: {part[1]}
        分类: {part[2]}    库存量: {part[3]} (最小: {part[4]})
        供应商: {part[5]}    单价: {part[6]:.2f}元
        状态: {status}
        -----------------------------------------
            """
        
        self.report_text.setText(report)
    
    def generate_maintenance_cost_report(self, start_date, end_date):
        """生成维护成本报告"""
        self.cursor.execute('''
            SELECT a.tail_number, a.model, SUM(mr.cost) as total_cost, COUNT(mr.id) as maintenance_count
            FROM maintenance_records mr
            JOIN aircrafts a ON mr.aircraft_id = a.id
            WHERE mr.date BETWEEN ? AND ?
            GROUP BY a.tail_number, a.model
            ORDER BY total_cost DESC
        ''', (start_date, end_date))
        
        cost_data = self.cursor.fetchall()
        
        # 总成本
        total_cost = sum(item[2] for item in cost_data) if cost_data else 0
        total_count = sum(item[3] for item in cost_data) if cost_data else 0
        
        # 生成报告
        report = f"""
        ==================== 维护成本报告 ====================
        报告期间: {start_date} 至 {end_date}
        生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        
        总体统计:
        - 总维护成本: {total_cost:.2f} 元
        - 总维护次数: {total_count} 次
        - 涉及飞机数量: {len(cost_data)} 架
        
        各飞机维护成本:
        """
        
        for item in cost_data:
            avg_cost = item[2] / item[3] if item[3] > 0 else 0
            report += f"""
        机尾号: {item[0]}    型号: {item[1]}
        总成本: {item[2]:.2f} 元    维护次数: {item[3]} 次
        平均每次成本: {avg_cost:.2f} 元
        -----------------------------------------
            """
        
        self.report_text.setText(report)
    
    def export_report(self):
        """导出报告"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存报告", "maintenance_report.txt", "文本文件 (*.txt)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as file:
                    file.write(self.report_text.toPlainText())
                QMessageBox.information(self, "成功", "报告导出成功")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导出报告时出错: {str(e)}")
    
    def clear_report(self):
        """清空报告"""
        self.report_text.clear()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("机务系统高级工具库")
    
    # 设置应用程序样式
    app.setStyle('Fusion')
    
    window = AircraftMaintenanceToolkit()
    window.show()
    
    sys.exit(app.exec_())