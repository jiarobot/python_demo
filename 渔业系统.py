import sys
import os
import json
import csv
import sqlite3
import math
from datetime import datetime, timedelta
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QTabWidget, QTableWidget, QTableWidgetItem, QPushButton, 
                             QLabel, QLineEdit, QTextEdit, QComboBox, QDateEdit, 
                             QSpinBox, QDoubleSpinBox, QProgressBar, QFileDialog, 
                             QMessageBox, QGroupBox, QFormLayout, QSplitter, QTreeWidget,
                             QTreeWidgetItem, QHeaderView, QCheckBox, QSlider, QProgressDialog)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QDate
from PyQt5.QtGui import QFont, QIcon, QPixmap, QColor
from PyQt5.QtChart import QChart, QChartView, QLineSeries, QBarSeries, QBarSet, QPieSeries, QValueAxis
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import numpy as np
import pandas as pd
from scipy import stats
import requests
from bs4 import BeautifulSoup
import folium
from folium.plugins import HeatMap
import webbrowser
import tempfile


class DatabaseManager:
    """数据库管理类"""
    
    def __init__(self, db_path="fishery.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """初始化数据库表结构"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建渔业资源表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS fishery_resources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                species TEXT NOT NULL,
                location TEXT NOT NULL,
                quantity REAL NOT NULL,
                date TEXT NOT NULL,
                temperature REAL,
                salinity REAL,
                notes TEXT
            )
        ''')
        
        # 创建渔船表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS fishing_vessels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                length REAL NOT NULL,
                tonnage REAL NOT NULL,
                captain TEXT,
                status TEXT,
                last_maintenance TEXT
            )
        ''')
        
        # 创建捕捞记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS fishing_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vessel_id INTEGER,
                species TEXT NOT NULL,
                quantity REAL NOT NULL,
                date TEXT NOT NULL,
                location TEXT NOT NULL,
                price REAL,
                FOREIGN KEY (vessel_id) REFERENCES fishing_vessels (id)
            )
        ''')
        
        # 创建环境监测表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS environmental_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                location TEXT NOT NULL,
                date TEXT NOT NULL,
                temperature REAL,
                salinity REAL,
                ph REAL,
                dissolved_oxygen REAL,
                turbidity REAL
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
    
    def insert_fishery_resource(self, species, location, quantity, date, temperature=None, salinity=None, notes=None):
        """插入渔业资源数据"""
        query = '''
            INSERT INTO fishery_resources (species, location, quantity, date, temperature, salinity, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        '''
        self.execute_query(query, (species, location, quantity, date, temperature, salinity, notes))
    
    def get_fishery_resources(self, species=None, location=None, start_date=None, end_date=None):
        """获取渔业资源数据"""
        query = "SELECT * FROM fishery_resources WHERE 1=1"
        params = []
        
        if species:
            query += " AND species = ?"
            params.append(species)
        
        if location:
            query += " AND location = ?"
            params.append(location)
        
        if start_date:
            query += " AND date >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND date <= ?"
            params.append(end_date)
        
        query += " ORDER BY date DESC"
        return self.execute_query(query, params)
    
    def get_statistics(self):
        """获取统计数据"""
        # 获取物种统计
        species_stats = self.execute_query(
            "SELECT species, SUM(quantity) as total_quantity, COUNT(*) as count FROM fishery_resources GROUP BY species"
        )
        
        # 获取位置统计
        location_stats = self.execute_query(
            "SELECT location, SUM(quantity) as total_quantity, COUNT(*) as count FROM fishery_resources GROUP BY location"
        )
        
        # 获取月度统计
        monthly_stats = self.execute_query(
            "SELECT strftime('%Y-%m', date) as month, SUM(quantity) as total_quantity FROM fishery_resources GROUP BY month ORDER BY month"
        )
        
        return {
            "species_stats": species_stats,
            "location_stats": location_stats,
            "monthly_stats": monthly_stats
        }


class DataAnalysisThread(QThread):
    """数据分析线程"""
    analysis_complete = pyqtSignal(dict)
    progress_updated = pyqtSignal(int)
    
    def __init__(self, data, analysis_type):
        super().__init__()
        self.data = data
        self.analysis_type = analysis_type
    
    def run(self):
        """执行数据分析"""
        result = {}
        
        if self.analysis_type == "trend":
            result = self.analyze_trends()
        elif self.analysis_type == "correlation":
            result = self.analyze_correlations()
        elif self.analysis_type == "forecast":
            result = self.forecast_future()
        
        self.analysis_complete.emit(result)
    
    def analyze_trends(self):
        """分析趋势"""
        # 模拟趋势分析
        self.progress_updated.emit(25)
        
        # 将数据转换为DataFrame
        df = pd.DataFrame(self.data, columns=['id', 'species', 'location', 'quantity', 'date', 'temperature', 'salinity', 'notes'])
        df['date'] = pd.to_datetime(df['date'])
        df['quantity'] = pd.to_numeric(df['quantity'])
        
        self.progress_updated.emit(50)
        
        # 按物种分组计算趋势
        trends = {}
        for species in df['species'].unique():
            species_data = df[df['species'] == species]
            monthly_avg = species_data.groupby(species_data['date'].dt.to_period('M'))['quantity'].mean()
            
            if len(monthly_avg) > 1:
                # 计算线性趋势
                x = range(len(monthly_avg))
                y = monthly_avg.values
                slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
                trends[species] = {
                    'slope': slope,
                    'r_squared': r_value**2,
                    'trend': '上升' if slope > 0 else '下降',
                    'strength': '强' if abs(r_value) > 0.7 else '中等' if abs(r_value) > 0.5 else '弱'
                }
        
        self.progress_updated.emit(100)
        
        return {'trends': trends, 'monthly_data': monthly_avg.to_dict()}
    
    def analyze_correlations(self):
        """分析相关性"""
        # 模拟相关性分析
        self.progress_updated.emit(25)
        
        df = pd.DataFrame(self.data, columns=['id', 'species', 'location', 'quantity', 'date', 'temperature', 'salinity', 'notes'])
        df['quantity'] = pd.to_numeric(df['quantity'])
        df['temperature'] = pd.to_numeric(df['temperature'])
        df['salinity'] = pd.to_numeric(df['salinity'])
        
        self.progress_updated.emit(50)
        
        # 计算相关性
        correlations = {}
        numeric_columns = ['quantity', 'temperature', 'salinity']
        
        for col1 in numeric_columns:
            for col2 in numeric_columns:
                if col1 != col2:
                    corr = df[col1].corr(df[col2])
                    correlations[f"{col1}_{col2}"] = corr
        
        self.progress_updated.emit(100)
        
        return {'correlations': correlations}
    
    def forecast_future(self):
        """预测未来趋势"""
        # 模拟预测
        self.progress_updated.emit(25)
        
        df = pd.DataFrame(self.data, columns=['id', 'species', 'location', 'quantity', 'date', 'temperature', 'salinity', 'notes'])
        df['date'] = pd.to_datetime(df['date'])
        df['quantity'] = pd.to_numeric(df['quantity'])
        
        self.progress_updated.emit(50)
        
        # 简单线性回归预测
        forecasts = {}
        for species in df['species'].unique():
            species_data = df[df['species'] == species]
            monthly_avg = species_data.groupby(species_data['date'].dt.to_period('M'))['quantity'].mean()
            
            if len(monthly_avg) > 1:
                x = np.array(range(len(monthly_avg))).reshape(-1, 1)
                y = monthly_avg.values
                
                # 线性回归
                slope, intercept, _, _, _ = stats.linregress(x.flatten(), y)
                
                # 预测未来3个月
                future_months = 3
                future_x = np.array(range(len(monthly_avg), len(monthly_avg) + future_months)).reshape(-1, 1)
                future_y = slope * future_x + intercept
                
                forecasts[species] = {
                    'current': y[-1],
                    'future': future_y.flatten().tolist(),
                    'trend': '上升' if slope > 0 else '下降'
                }
        
        self.progress_updated.emit(100)
        
        return {'forecasts': forecasts}


class MapGenerator:
    """地图生成器"""
    
    def __init__(self):
        self.locations = {}
    
    def add_location_data(self, location, quantity, latitude, longitude):
        """添加位置数据"""
        if location not in self.locations:
            self.locations[location] = {
                'quantity': 0,
                'latitude': latitude,
                'longitude': longitude,
                'count': 0
            }
        
        self.locations[location]['quantity'] += quantity
        self.locations[location]['count'] += 1
    
    def generate_heatmap(self, output_path="fishery_heatmap.html"):
        """生成热力图"""
        # 创建地图
        m = folium.Map(location=[30, 120], zoom_start=5)
        
        # 准备热力图数据
        heat_data = []
        for location, data in self.locations.items():
            heat_data.append([data['latitude'], data['longitude'], data['quantity']])
        
        # 添加热力图
        if heat_data:
            HeatMap(heat_data).add_to(m)
        
        # 保存地图
        m.save(output_path)
        return output_path


class ResourceManagementTab(QWidget):
    """资源管理标签页"""
    
    def __init__(self, db_manager):
        super().__init__()
        self.db_manager = db_manager
        self.init_ui()
        self.load_data()
    
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout()
        
        # 顶部工具栏
        toolbar = QHBoxLayout()
        
        self.species_filter = QComboBox()
        self.species_filter.addItem("所有物种")
        self.species_filter.currentTextChanged.connect(self.filter_data)
        
        self.location_filter = QComboBox()
        self.location_filter.addItem("所有位置")
        self.location_filter.currentTextChanged.connect(self.filter_data)
        
        self.start_date = QDateEdit()
        self.start_date.setDate(QDate.currentDate().addMonths(-1))
        self.start_date.dateChanged.connect(self.filter_data)
        
        self.end_date = QDateEdit()
        self.end_date.setDate(QDate.currentDate())
        self.end_date.dateChanged.connect(self.filter_data)
        
        refresh_btn = QPushButton("刷新")
        refresh_btn.clicked.connect(self.load_data)
        
        export_btn = QPushButton("导出数据")
        export_btn.clicked.connect(self.export_data)
        
        toolbar.addWidget(QLabel("物种:"))
        toolbar.addWidget(self.species_filter)
        toolbar.addWidget(QLabel("位置:"))
        toolbar.addWidget(self.location_filter)
        toolbar.addWidget(QLabel("开始日期:"))
        toolbar.addWidget(self.start_date)
        toolbar.addWidget(QLabel("结束日期:"))
        toolbar.addWidget(self.end_date)
        toolbar.addWidget(refresh_btn)
        toolbar.addWidget(export_btn)
        toolbar.addStretch()
        
        layout.addLayout(toolbar)
        
        # 数据表格
        self.table = QTableWidget()
        layout.addWidget(self.table)
        
        # 底部统计信息
        stats_layout = QHBoxLayout()
        
        self.total_quantity_label = QLabel("总数量: 0")
        self.species_count_label = QLabel("物种数: 0")
        self.avg_quantity_label = QLabel("平均数量: 0")
        
        stats_layout.addWidget(self.total_quantity_label)
        stats_layout.addWidget(self.species_count_label)
        stats_layout.addWidget(self.avg_quantity_label)
        stats_layout.addStretch()
        
        layout.addLayout(stats_layout)
        
        self.setLayout(layout)
    
    def load_data(self):
        """加载数据"""
        # 获取数据
        data = self.db_manager.get_fishery_resources()
        
        # 更新过滤器选项
        species_set = set()
        location_set = set()
        for row in data:
            species_set.add(row[1])
            location_set.add(row[2])
        
        self.species_filter.clear()
        self.species_filter.addItem("所有物种")
        self.species_filter.addItems(sorted(species_set))
        
        self.location_filter.clear()
        self.location_filter.addItem("所有位置")
        self.location_filter.addItems(sorted(location_set))
        
        # 显示数据
        self.display_data(data)
    
    def display_data(self, data):
        """显示数据"""
        self.table.setRowCount(len(data))
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "ID", "物种", "位置", "数量", "日期", "温度", "盐度", "备注"
        ])
        
        total_quantity = 0
        species_set = set()
        
        for row_idx, row in enumerate(data):
            for col_idx, value in enumerate(row):
                item = QTableWidgetItem(str(value) if value is not None else "")
                self.table.setItem(row_idx, col_idx, item)
            
            total_quantity += float(row[3]) if row[3] else 0
            species_set.add(row[1])
        
        # 调整列宽
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        
        # 更新统计信息
        self.total_quantity_label.setText(f"总数量: {total_quantity:.2f}")
        self.species_count_label.setText(f"物种数: {len(species_set)}")
        self.avg_quantity_label.setText(f"平均数量: {total_quantity/len(data) if len(data) > 0 else 0:.2f}")
    
    def filter_data(self):
        """过滤数据"""
        species = None if self.species_filter.currentText() == "所有物种" else self.species_filter.currentText()
        location = None if self.location_filter.currentText() == "所有位置" else self.location_filter.currentText()
        start_date = self.start_date.date().toString("yyyy-MM-dd")
        end_date = self.end_date.date().toString("yyyy-MM-dd")
        
        data = self.db_manager.get_fishery_resources(species, location, start_date, end_date)
        self.display_data(data)
    
    def export_data(self):
        """导出数据"""
        file_path, _ = QFileDialog.getSaveFileName(self, "导出数据", "fishery_data.csv", "CSV Files (*.csv)")
        
        if file_path:
            data = self.db_manager.get_fishery_resources()
            with open(file_path, 'w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                writer.writerow(["ID", "物种", "位置", "数量", "日期", "温度", "盐度", "备注"])
                writer.writerows(data)
            
            QMessageBox.information(self, "导出成功", f"数据已导出到 {file_path}")


class DataAnalysisTab(QWidget):
    """数据分析标签页"""
    
    def __init__(self, db_manager):
        super().__init__()
        self.db_manager = db_manager
        self.analysis_thread = None
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout()
        
        # 分析类型选择
        analysis_type_layout = QHBoxLayout()
        analysis_type_layout.addWidget(QLabel("分析类型:"))
        
        self.analysis_type = QComboBox()
        self.analysis_type.addItems(["趋势分析", "相关性分析", "预测分析"])
        analysis_type_layout.addWidget(self.analysis_type)
        
        self.analyze_btn = QPushButton("开始分析")
        self.analyze_btn.clicked.connect(self.start_analysis)
        analysis_type_layout.addWidget(self.analyze_btn)
        
        analysis_type_layout.addStretch()
        layout.addLayout(analysis_type_layout)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # 结果显示区域
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        layout.addWidget(self.results_text)
        
        # 图表区域
        self.chart_view = QChartView()
        self.chart_view.setMinimumHeight(300)
        layout.addWidget(self.chart_view)
        
        self.setLayout(layout)
    
    def start_analysis(self):
        """开始分析"""
        analysis_type = self.analysis_type.currentText()
        analysis_map = {
            "趋势分析": "trend",
            "相关性分析": "correlation",
            "预测分析": "forecast"
        }
        
        # 获取数据
        data = self.db_manager.get_fishery_resources()
        
        # 创建分析线程
        self.analysis_thread = DataAnalysisThread(data, analysis_map[analysis_type])
        self.analysis_thread.progress_updated.connect(self.update_progress)
        self.analysis_thread.analysis_complete.connect(self.display_results)
        self.analysis_thread.start()
        
        self.analyze_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
    
    def update_progress(self, value):
        """更新进度"""
        self.progress_bar.setValue(value)
    
    def display_results(self, results):
        """显示结果"""
        self.analyze_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        # 显示文本结果
        result_text = "分析结果:\n\n"
        
        if 'trends' in results:
            for species, trend in results['trends'].items():
                result_text += f"物种: {species}\n"
                result_text += f"趋势: {trend['trend']} ({trend['strength']})\n"
                result_text += f"R²: {trend['r_squared']:.3f}\n\n"
        
        elif 'correlations' in results:
            for pair, corr in results['correlations'].items():
                result_text += f"{pair}: {corr:.3f}\n"
        
        elif 'forecasts' in results:
            for species, forecast in results['forecasts'].items():
                result_text += f"物种: {species}\n"
                result_text += f"当前值: {forecast['current']:.2f}\n"
                result_text += f"趋势: {forecast['trend']}\n"
                result_text += f"未来预测: {', '.join([f'{x:.2f}' for x in forecast['future']])}\n\n"
        
        self.results_text.setText(result_text)
        
        # 显示图表
        self.display_chart(results)
    
    def display_chart(self, results):
        """显示图表"""
        chart = QChart()
        chart.setTitle("分析结果")
        
        if 'monthly_data' in results:
            # 创建折线图
            series = QLineSeries()
            
            for i, (month, value) in enumerate(results['monthly_data'].items()):
                series.append(i, value)
            
            chart.addSeries(series)
            
            # 设置坐标轴
            axis_x = QValueAxis()
            axis_x.setTitleText("月份")
            chart.addAxis(axis_x, Qt.AlignBottom)
            series.attachAxis(axis_x)
            
            axis_y = QValueAxis()
            axis_y.setTitleText("数量")
            chart.addAxis(axis_y, Qt.AlignLeft)
            series.attachAxis(axis_y)
        
        self.chart_view.setChart(chart)


class MapVisualizationTab(QWidget):
    """地图可视化标签页"""
    
    def __init__(self, db_manager):
        super().__init__()
        self.db_manager = db_manager
        self.map_generator = MapGenerator()
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout()
        
        # 控制区域
        controls_layout = QHBoxLayout()
        
        self.generate_btn = QPushButton("生成地图")
        self.generate_btn.clicked.connect(self.generate_map)
        controls_layout.addWidget(self.generate_btn)
        
        self.open_btn = QPushButton("打开地图")
        self.open_btn.clicked.connect(self.open_map)
        self.open_btn.setEnabled(False)
        controls_layout.addWidget(self.open_btn)
        
        controls_layout.addStretch()
        layout.addLayout(controls_layout)
        
        # 地图预览区域
        self.map_preview = QLabel()
        self.map_preview.setAlignment(Qt.AlignCenter)
        self.map_preview.setText("地图预览将在这里显示")
        self.map_preview.setStyleSheet("border: 1px solid gray; min-height: 400px;")
        layout.addWidget(self.map_preview)
        
        self.setLayout(layout)
    
    def generate_map(self):
        """生成地图"""
        # 获取数据
        data = self.db_manager.get_fishery_resources()
        
        # 清空现有数据
        self.map_generator = MapGenerator()
        
        # 添加数据到地图生成器（这里使用模拟的经纬度）
        locations_coords = {
            "东海": (30.5, 123.0),
            "黄海": (35.0, 122.0),
            "南海": (20.0, 113.0),
            "渤海": (39.0, 119.0)
        }
        
        for row in data:
            location = row[2]
            quantity = float(row[3])
            
            if location in locations_coords:
                lat, lon = locations_coords[location]
                self.map_generator.add_location_data(location, quantity, lat, lon)
        
        # 生成地图
        output_path = "fishery_heatmap.html"
        self.map_generator.generate_heatmap(output_path)
        
        # 显示预览
        pixmap = QPixmap(400, 300)
        pixmap.fill(Qt.white)
        self.map_preview.setPixmap(pixmap)
        self.map_preview.setText("热力图已生成，点击'打开地图'查看详情")
        
        self.open_btn.setEnabled(True)
        self.current_map_path = output_path
        
        QMessageBox.information(self, "生成成功", "地图已生成完成")
    
    def open_map(self):
        """打开地图"""
        if hasattr(self, 'current_map_path'):
            webbrowser.open('file://' + os.path.abspath(self.current_map_path))


class FisherySystem(QMainWindow):
    """渔业系统主窗口"""
    
    def __init__(self):
        super().__init__()
        self.db_manager = DatabaseManager()
        self.init_ui()
        self.load_sample_data()
    
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("渔业系统高级工具库")
        self.setGeometry(100, 100, 1200, 800)
        
        # 创建中心部件和布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        
        # 创建标签页
        self.tabs = QTabWidget()
        
        # 资源管理标签页
        self.resource_tab = ResourceManagementTab(self.db_manager)
        self.tabs.addTab(self.resource_tab, "资源管理")
        
        # 数据分析标签页
        self.analysis_tab = DataAnalysisTab(self.db_manager)
        self.tabs.addTab(self.analysis_tab, "数据分析")
        
        # 地图可视化标签页
        self.map_tab = MapVisualizationTab(self.db_manager)
        self.tabs.addTab(self.map_tab, "地图可视化")
        
        layout.addWidget(self.tabs)
    
    def load_sample_data(self):
        """加载示例数据"""
        # 检查是否已有数据
        existing_data = self.db_manager.get_fishery_resources()
        if existing_data:
            return
        
        # 添加示例数据
        species_list = ["大黄鱼", "小黄鱼", "带鱼", "鲳鱼", "墨鱼"]
        locations = ["东海", "黄海", "南海", "渤海"]
        
        # 生成过去一年的数据
        base_date = datetime.now() - timedelta(days=365)
        
        for i in range(100):
            species = species_list[i % len(species_list)]
            location = locations[i % len(locations)]
            quantity = np.random.normal(1000, 200)
            date = (base_date + timedelta(days=i*3)).strftime("%Y-%m-%d")
            temperature = np.random.normal(20, 5)
            salinity = np.random.normal(30, 5)
            
            self.db_manager.insert_fishery_resource(
                species, location, quantity, date, temperature, salinity
            )


def main():
    """主函数"""
    app = QApplication(sys.argv)
    
    # 设置应用程序样式
    app.setStyle('Fusion')
    
    # 创建并显示主窗口
    window = FisherySystem()
    window.show()
    
    # 运行应用程序
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()