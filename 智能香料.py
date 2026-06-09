import sys
import json
import pandas as pd
import numpy as np
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTabWidget, QTableWidget, QTableWidgetItem,
                             QPushButton, QLabel, QLineEdit, QTextEdit, QComboBox,
                             QSpinBox, QDoubleSpinBox, QMessageBox, QFileDialog,
                             QProgressBar, QGroupBox, QSplitter, QTreeWidget, 
                             QTreeWidgetItem, QHeaderView, QCheckBox, QListWidget,
                             QListWidgetItem, QDialog, QDialogButtonBox)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QPalette
import sqlite3
from datetime import datetime
import matplotlib
matplotlib.rc("font", family='Microsoft YaHei')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
import warnings
warnings.filterwarnings('ignore')


# 香料数据库管理类
class SpiceDatabase:
    def __init__(self, db_path="spices.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建香料表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS spices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                category TEXT,
                origin TEXT,
                intensity REAL,
                price_per_kg REAL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 创建香料属性表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS spice_attributes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                spice_id INTEGER,
                attribute TEXT,
                value REAL,
                FOREIGN KEY (spice_id) REFERENCES spices (id)
            )
        ''')
        
        # 创建配方表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS recipes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                cuisine_type TEXT,
                difficulty TEXT,
                rating REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 创建配方成分表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS recipe_ingredients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recipe_id INTEGER,
                spice_id INTEGER,
                quantity REAL,
                unit TEXT,
                FOREIGN KEY (recipe_id) REFERENCES recipes (id),
                FOREIGN KEY (spice_id) REFERENCES spices (id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def add_spice(self, name, category, origin, intensity, price, description, attributes=None):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO spices (name, category, origin, intensity, price_per_kg, description)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (name, category, origin, intensity, price, description))
            
            spice_id = cursor.lastrowid
            
            if attributes:
                for attr, value in attributes.items():
                    cursor.execute('''
                        INSERT INTO spice_attributes (spice_id, attribute, value)
                        VALUES (?, ?, ?)
                    ''', (spice_id, attr, value))
            
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()
    
    def get_all_spices(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM spices')
        spices = cursor.fetchall()
        
        conn.close()
        return spices
    
    def get_spice_by_id(self, spice_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM spices WHERE id = ?', (spice_id,))
        spice = cursor.fetchone()
        
        cursor.execute('SELECT attribute, value FROM spice_attributes WHERE spice_id = ?', (spice_id,))
        attributes = cursor.fetchall()
        
        conn.close()
        return spice, attributes
    
    def search_spices(self, keyword):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM spices 
            WHERE name LIKE ? OR category LIKE ? OR origin LIKE ? OR description LIKE ?
        ''', (f'%{keyword}%', f'%{keyword}%', f'%{keyword}%', f'%{keyword}%'))
        
        spices = cursor.fetchall()
        conn.close()
        return spices
    
    def add_recipe(self, name, description, cuisine_type, difficulty, ingredients):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO recipes (name, description, cuisine_type, difficulty)
                VALUES (?, ?, ?, ?)
            ''', (name, description, cuisine_type, difficulty))
            
            recipe_id = cursor.lastrowid
            
            for spice_id, quantity, unit in ingredients:
                cursor.execute('''
                    INSERT INTO recipe_ingredients (recipe_id, spice_id, quantity, unit)
                    VALUES (?, ?, ?, ?)
                ''', (recipe_id, spice_id, quantity, unit))
            
            conn.commit()
            return True
        except Exception as e:
            print(f"Error adding recipe: {e}")
            return False
        finally:
            conn.close()


# 香料分析引擎
class SpiceAnalyzer:
    def __init__(self, db_manager):
        self.db = db_manager
    
    def get_spice_dataframe(self):
        spices = self.db.get_all_spices()
        if not spices:
            # 返回空的DataFrame，但包含正确的列
            return pd.DataFrame(columns=['id', 'name', 'category', 'origin', 'intensity', 'price_per_kg', 'description', 'created_at'])
        
        df = pd.DataFrame(spices, columns=['id', 'name', 'category', 'origin', 'intensity', 'price_per_kg', 'description', 'created_at'])
        return df
    
    def analyze_categories(self):
        df = self.get_spice_dataframe()
        if df.empty:
            return pd.Series([], dtype=float)  # 返回空的Series
        
        category_counts = df['category'].value_counts()
        return category_counts
    
    def analyze_origins(self):
        df = self.get_spice_dataframe()
        if df.empty:
            return pd.Series([], dtype=float)  # 返回空的Series
        
        origin_counts = df['origin'].value_counts()
        return origin_counts
    
    def price_analysis(self):
        df = self.get_spice_dataframe()
        if df.empty:
            # 返回空的统计信息
            return pd.Series([0, 0, 0, 0, 0, 0, 0, 0], 
                            index=['count', 'mean', 'std', 'min', '25%', '50%', '75%', 'max'])
        
        price_stats = df['price_per_kg'].describe()
        return price_stats
    
    def intensity_analysis(self):
        df = self.get_spice_dataframe()
        if df.empty:
            # 返回空的统计信息
            return pd.Series([0, 0, 0, 0, 0, 0, 0, 0], 
                            index=['count', 'mean', 'std', 'min', '25%', '50%', '75%', 'max'])
        
        intensity_stats = df['intensity'].describe()
        return intensity_stats
    
    def cluster_spices(self, n_clusters=3):
        df = self.get_spice_dataframe()
        if df.empty:
            return pd.DataFrame(columns=['name', 'intensity', 'price_per_kg', 'cluster'])
        
        features = df[['intensity', 'price_per_kg']].fillna(0)
        
        # 确保有足够的数据进行聚类
        if len(features) < n_clusters:
            n_clusters = max(1, len(features))
        
        kmeans = KMeans(n_clusters=n_clusters, random_state=42)
        df['cluster'] = kmeans.fit_predict(features)
        
        return df[['name', 'intensity', 'price_per_kg', 'cluster']]
    
    def recommend_spices(self, base_spice_id, n_recommendations=5):
        df = self.get_spice_dataframe()
        if df.empty:
            return pd.DataFrame(columns=['id', 'name', 'category', 'intensity', 'price_per_kg'])
        
        # 检查基础香料是否存在
        if base_spice_id not in df['id'].values:
            return pd.DataFrame(columns=['id', 'name', 'category', 'intensity', 'price_per_kg'])
        
        base_spice = df[df['id'] == base_spice_id].iloc[0]
        base_intensity = base_spice['intensity']
        
        # 计算与基础香料的强度差异
        df['intensity_diff'] = abs(df['intensity'] - base_intensity)
        
        # 排除基础香料本身
        df = df[df['id'] != base_spice_id]
        
        # 按强度差异排序，选择最相似的
        recommendations = df.nsmallest(min(n_recommendations, len(df)), 'intensity_diff')
        
        return recommendations[['id', 'name', 'category', 'intensity', 'price_per_kg']]


# 配方生成器
class RecipeGenerator:
    def __init__(self, db_manager):
        self.db = db_manager
    
    def generate_recipe(self, cuisine_type, difficulty, num_spices=5):
        spices = self.db.get_all_spices()
        
        if not spices:
            return None
        
        # 确保不会选择超过可用香料数量的香料
        num_spices = min(num_spices, len(spices))
        
        # 简单的随机配方生成
        selected_indices = np.random.choice(len(spices), num_spices, replace=False)
        selected_spices = [spices[i] for i in selected_indices]
        
        recipe = {
            'name': f"{cuisine_type} Spice Blend",
            'description': f"A {difficulty.lower()} {cuisine_type} spice blend",
            'cuisine_type': cuisine_type,
            'difficulty': difficulty,
            'ingredients': []
        }
        
        for spice in selected_spices:
            # 随机生成数量 (1-10克)
            quantity = np.random.uniform(1, 10)
            recipe['ingredients'].append((spice[0], round(quantity, 1), 'g'))
        
        return recipe


# 自定义图表组件
class SpiceChartWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.canvas = FigureCanvas(plt.Figure(figsize=(5, 4)))
        self.layout.addWidget(self.canvas)
        self.ax = self.canvas.figure.add_subplot(111)
    
    def plot_bar_chart(self, data, title, xlabel, ylabel):
        self.ax.clear()
        
        # 检查数据是否为空
        if data.empty:
            self.ax.text(0.5, 0.5, '无数据可用', horizontalalignment='center', 
                        verticalalignment='center', transform=self.ax.transAxes, fontsize=12)
            self.ax.set_title(title)
        else:
            # 确保数据是Series类型且有索引
            if not isinstance(data, pd.Series):
                data = pd.Series(data)
            
            # 绘制条形图
            data.plot(kind='bar', ax=self.ax)
            self.ax.set_title(title)
            self.ax.set_xlabel(xlabel)
            self.ax.set_ylabel(ylabel)
            
            # 旋转x轴标签以避免重叠
            plt.setp(self.ax.get_xticklabels(), rotation=45, ha='right')
        
        self.canvas.draw()
    
    def plot_pie_chart(self, data, title):
        self.ax.clear()
        
        # 检查数据是否为空
        if data.empty:
            self.ax.text(0.5, 0.5, '无数据可用', horizontalalignment='center', 
                        verticalalignment='center', transform=self.ax.transAxes, fontsize=12)
            self.ax.set_title(title)
        else:
            # 确保数据是Series类型
            if not isinstance(data, pd.Series):
                data = pd.Series(data)
            
            # 绘制饼图
            data.plot(kind='pie', ax=self.ax, autopct='%1.1f%%')
            self.ax.set_title(title)
            self.ax.set_ylabel('')  # 隐藏y轴标签
        
        self.canvas.draw()


# 香料管理界面
class SpiceManagerWidget(QWidget):
    def __init__(self, db_manager):
        super().__init__()
        self.db = db_manager
        self.init_ui()
        self.load_spices()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 搜索和添加区域
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索香料...")
        self.search_input.textChanged.connect(self.search_spices)
        search_layout.addWidget(self.search_input)
        
        self.add_button = QPushButton("添加新香料")
        self.add_button.clicked.connect(self.show_add_dialog)
        search_layout.addWidget(self.add_button)
        
        layout.addLayout(search_layout)
        
        # 香料表格
        self.spice_table = QTableWidget()
        self.spice_table.setColumnCount(7)
        self.spice_table.setHorizontalHeaderLabels(["ID", "名称", "类别", "产地", "强度", "价格(元/kg)", "描述"])
        self.spice_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.spice_table)
        
        # 操作按钮
        button_layout = QHBoxLayout()
        self.edit_button = QPushButton("编辑选中")
        self.edit_button.clicked.connect(self.edit_spice)
        button_layout.addWidget(self.edit_button)
        
        self.delete_button = QPushButton("删除选中")
        self.delete_button.clicked.connect(self.delete_spice)
        button_layout.addWidget(self.delete_button)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def load_spices(self):
        spices = self.db.get_all_spices()
        self.spice_table.setRowCount(len(spices))
        
        for row, spice in enumerate(spices):
            for col, value in enumerate(spice):
                item = QTableWidgetItem(str(value))
                self.spice_table.setItem(row, col, item)
    
    def search_spices(self):
        keyword = self.search_input.text()
        if keyword:
            spices = self.db.search_spices(keyword)
        else:
            spices = self.db.get_all_spices()
        
        self.spice_table.setRowCount(len(spices))
        for row, spice in enumerate(spices):
            for col, value in enumerate(spice):
                item = QTableWidgetItem(str(value))
                self.spice_table.setItem(row, col, item)
    
    def show_add_dialog(self):
        dialog = AddSpiceDialog(self.db, self)
        if dialog.exec_() == QDialog.Accepted:
            self.load_spices()
    
    def edit_spice(self):
        selected_row = self.spice_table.currentRow()
        if selected_row == -1:
            QMessageBox.warning(self, "警告", "请先选择一个香料")
            return
        
        spice_id = int(self.spice_table.item(selected_row, 0).text())
        dialog = EditSpiceDialog(self.db, spice_id, self)
        if dialog.exec_() == QDialog.Accepted:
            self.load_spices()
    
    def delete_spice(self):
        selected_row = self.spice_table.currentRow()
        if selected_row == -1:
            QMessageBox.warning(self, "警告", "请先选择一个香料")
            return
        
        spice_id = int(self.spice_table.item(selected_row, 0).text())
        spice_name = self.spice_table.item(selected_row, 1).text()
        
        reply = QMessageBox.question(self, "确认删除", 
                                    f"确定要删除香料 '{spice_name}' 吗？",
                                    QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            # 这里应该实现删除逻辑
            QMessageBox.information(self, "提示", "删除功能待实现")


# 添加香料对话框
class AddSpiceDialog(QDialog):
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.setWindowTitle("添加新香料")
        self.setModal(True)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 香料基本信息
        form_layout = QVBoxLayout()
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("香料名称")
        form_layout.addWidget(QLabel("名称:"))
        form_layout.addWidget(self.name_input)
        
        self.category_input = QComboBox()
        self.category_input.addItems(["草本", "种子", "果实", "根茎", "树皮", "花蕾", "混合香料", "其他"])
        form_layout.addWidget(QLabel("类别:"))
        form_layout.addWidget(self.category_input)
        
        self.origin_input = QLineEdit()
        self.origin_input.setPlaceholderText("产地")
        form_layout.addWidget(QLabel("产地:"))
        form_layout.addWidget(self.origin_input)
        
        self.intensity_input = QDoubleSpinBox()
        self.intensity_input.setRange(0, 10)
        self.intensity_input.setSingleStep(0.1)
        self.intensity_input.setValue(5.0)
        form_layout.addWidget(QLabel("强度 (0-10):"))
        form_layout.addWidget(self.intensity_input)
        
        self.price_input = QDoubleSpinBox()
        self.price_input.setRange(0, 10000)
        self.price_input.setSingleStep(10)
        self.price_input.setValue(100)
        form_layout.addWidget(QLabel("价格 (元/kg):"))
        form_layout.addWidget(self.price_input)
        
        self.description_input = QTextEdit()
        self.description_input.setMaximumHeight(100)
        self.description_input.setPlaceholderText("香料描述...")
        form_layout.addWidget(QLabel("描述:"))
        form_layout.addWidget(self.description_input)
        
        layout.addLayout(form_layout)
        
        # 按钮
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
    
    def accept(self):
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "警告", "请输入香料名称")
            return
        
        category = self.category_input.currentText()
        origin = self.origin_input.text().strip()
        intensity = self.intensity_input.value()
        price = self.price_input.value()
        description = self.description_input.toPlainText().strip()
        
        success = self.db.add_spice(name, category, origin, intensity, price, description)
        
        if success:
            QMessageBox.information(self, "成功", "香料添加成功")
            super().accept()
        else:
            QMessageBox.warning(self, "错误", "添加失败，可能已存在同名香料")


# 编辑香料对话框 (简化版，实际实现需要更完整)
class EditSpiceDialog(QDialog):
    def __init__(self, db_manager, spice_id, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.spice_id = spice_id
        self.setWindowTitle("编辑香料")
        self.setModal(True)
        self.init_ui()
        self.load_spice_data()
    
    def init_ui(self):
        # 类似于AddSpiceDialog的UI，但包含当前值
        layout = QVBoxLayout()
        
        # 这里简化实现，实际应该完整实现编辑功能
        self.info_label = QLabel("编辑功能待完整实现")
        layout.addWidget(self.info_label)
        
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
    
    def load_spice_data(self):
        # 加载香料数据并填充表单
        spice, attributes = self.db.get_spice_by_id(self.spice_id)
        if spice:
            self.info_label.setText(f"编辑香料: {spice[1]}")
    
    def accept(self):
        # 实现更新逻辑
        QMessageBox.information(self, "提示", "编辑功能待实现")
        super().accept()


# 数据分析界面
class AnalyticsWidget(QWidget):
    def __init__(self, db_manager):
        super().__init__()
        self.db = db_manager
        self.analyzer = SpiceAnalyzer(db_manager)
        self.init_ui()
        self.load_analytics()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 分析控制区域
        control_layout = QHBoxLayout()
        
        self.refresh_button = QPushButton("刷新分析")
        self.refresh_button.clicked.connect(self.load_analytics)
        control_layout.addWidget(self.refresh_button)
        
        self.cluster_button = QPushButton("香料聚类分析")
        self.cluster_button.clicked.connect(self.show_cluster_analysis)
        control_layout.addWidget(self.cluster_button)
        
        control_layout.addStretch()
        layout.addLayout(control_layout)
        
        # 图表区域
        splitter = QSplitter(Qt.Horizontal)
        
        # 左侧图表
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        self.category_chart = SpiceChartWidget()
        left_layout.addWidget(QLabel("香料类别分布"))
        left_layout.addWidget(self.category_chart)
        
        self.origin_chart = SpiceChartWidget()
        left_layout.addWidget(QLabel("香料产地分布"))
        left_layout.addWidget(self.origin_chart)
        
        splitter.addWidget(left_widget)
        
        # 右侧统计信息
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        self.stats_text = QTextEdit()
        self.stats_text.setReadOnly(True)
        right_layout.addWidget(QLabel("统计信息"))
        right_layout.addWidget(self.stats_text)
        
        splitter.addWidget(right_widget)
        splitter.setSizes([400, 300])
        
        layout.addWidget(splitter)
        self.setLayout(layout)
    
    def load_analytics(self):
        # 类别分析
        category_counts = self.analyzer.analyze_categories()
        self.category_chart.plot_pie_chart(category_counts, "香料类别分布")
        
        # 产地分析
        origin_counts = self.analyzer.analyze_origins()
        self.origin_chart.plot_bar_chart(origin_counts, "香料产地分布", "产地", "数量")
        
        # 统计信息
        price_stats = self.analyzer.price_analysis()
        intensity_stats = self.analyzer.intensity_analysis()
        
        # 检查是否有数据
        if price_stats['count'] == 0:
            stats_text = "暂无香料数据，请先添加香料。"
        else:
            stats_text = f"""
            === 价格统计 ===
            数量: {price_stats['count']}
            平均价格: {price_stats['mean']:.2f} 元/kg
            最低价格: {price_stats['min']:.2f} 元/kg
            最高价格: {price_stats['max']:.2f} 元/kg
            
            === 强度统计 ===
            平均强度: {intensity_stats['mean']:.2f}
            最低强度: {intensity_stats['min']:.2f}
            最高强度: {intensity_stats['max']:.2f}
            """
        
        self.stats_text.setText(stats_text)
    
    def show_cluster_analysis(self):
        cluster_df = self.analyzer.cluster_spices(3)
        
        # 检查是否有数据
        if cluster_df.empty:
            QMessageBox.information(self, "提示", "暂无香料数据，无法进行聚类分析。")
            return
        
        # 创建聚类分析窗口
        dialog = QDialog(self)
        dialog.setWindowTitle("香料聚类分析")
        dialog.setModal(True)
        dialog.resize(600, 400)
        
        layout = QVBoxLayout()
        
        # 聚类结果表格
        table = QTableWidget()
        table.setColumnCount(4)
        table.setHorizontalHeaderLabels(["名称", "强度", "价格", "聚类"])
        table.setRowCount(len(cluster_df))
        
        for row, (_, spice) in enumerate(cluster_df.iterrows()):
            table.setItem(row, 0, QTableWidgetItem(spice['name']))
            table.setItem(row, 1, QTableWidgetItem(str(spice['intensity'])))
            table.setItem(row, 2, QTableWidgetItem(str(spice['price_per_kg'])))
            table.setItem(row, 3, QTableWidgetItem(str(spice['cluster'])))
        
        layout.addWidget(table)
        
        # 关闭按钮
        close_button = QPushButton("关闭")
        close_button.clicked.connect(dialog.accept)
        layout.addWidget(close_button)
        
        dialog.setLayout(layout)
        dialog.exec_()


# 配方管理界面
class RecipeManagerWidget(QWidget):
    def __init__(self, db_manager):
        super().__init__()
        self.db = db_manager
        self.generator = RecipeGenerator(db_manager)
        self.init_ui()
        self.load_recipes()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 配方生成区域
        generate_layout = QHBoxLayout()
        
        self.cuisine_combo = QComboBox()
        self.cuisine_combo.addItems(["中式", "西式", "印度", "中东", "东南亚", "其他"])
        generate_layout.addWidget(QLabel("菜系:"))
        generate_layout.addWidget(self.cuisine_combo)
        
        self.difficulty_combo = QComboBox()
        self.difficulty_combo.addItems(["简单", "中等", "复杂"])
        generate_layout.addWidget(QLabel("难度:"))
        generate_layout.addWidget(self.difficulty_combo)
        
        self.spice_count = QSpinBox()
        self.spice_count.setRange(3, 10)
        self.spice_count.setValue(5)
        generate_layout.addWidget(QLabel("香料数量:"))
        generate_layout.addWidget(self.spice_count)
        
        self.generate_button = QPushButton("生成配方")
        self.generate_button.clicked.connect(self.generate_recipe)
        generate_layout.addWidget(self.generate_button)
        
        generate_layout.addStretch()
        layout.addLayout(generate_layout)
        
        # 配方表格
        self.recipe_table = QTableWidget()
        self.recipe_table.setColumnCount(5)
        self.recipe_table.setHorizontalHeaderLabels(["ID", "名称", "菜系", "难度", "评分"])
        self.recipe_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.recipe_table.doubleClicked.connect(self.view_recipe_details)
        layout.addWidget(self.recipe_table)
        
        self.setLayout(layout)
    
    def load_recipes(self):
        # 这里应该从数据库加载配方
        # 暂时使用示例数据
        self.recipe_table.setRowCount(0)
    
    def generate_recipe(self):
        cuisine = self.cuisine_combo.currentText()
        difficulty = self.difficulty_combo.currentText()
        num_spices = self.spice_count.value()
        
        recipe = self.generator.generate_recipe(cuisine, difficulty, num_spices)
        
        if recipe:
            # 显示生成的配方
            dialog = QDialog(self)
            dialog.setWindowTitle("生成的配方")
            dialog.setModal(True)
            dialog.resize(400, 300)
            
            layout = QVBoxLayout()
            
            # 配方信息
            info_text = f"""
            <h3>{recipe['name']}</h3>
            <p><b>菜系:</b> {recipe['cuisine_type']}</p>
            <p><b>难度:</b> {recipe['difficulty']}</p>
            <p><b>描述:</b> {recipe['description']}</p>
            <p><b>成分:</b></p>
            <ul>
            """
            
            for spice_id, quantity, unit in recipe['ingredients']:
                # 这里应该根据spice_id获取香料名称
                info_text += f"<li>{quantity} {unit} 香料ID: {spice_id}</li>"
            
            info_text += "</ul>"
            
            info_label = QLabel(info_text)
            info_label.setWordWrap(True)
            layout.addWidget(info_label)
            
            # 按钮
            button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
            button_box.accepted.connect(lambda: self.save_recipe(recipe, dialog))
            button_box.rejected.connect(dialog.reject)
            layout.addWidget(button_box)
            
            dialog.setLayout(layout)
            dialog.exec_()
        else:
            QMessageBox.warning(self, "警告", "无法生成配方，请先添加香料。")
    
    def save_recipe(self, recipe, dialog):
        # 保存配方到数据库
        ingredients = recipe['ingredients']
        success = self.db.add_recipe(
            recipe['name'], 
            recipe['description'], 
            recipe['cuisine_type'], 
            recipe['difficulty'], 
            ingredients
        )
        
        if success:
            QMessageBox.information(self, "成功", "配方保存成功")
            dialog.accept()
            self.load_recipes()
        else:
            QMessageBox.warning(self, "错误", "配方保存失败")
    
    def view_recipe_details(self, index):
        # 查看配方详情
        row = index.row()
        recipe_id = self.recipe_table.item(row, 0).text()
        
        # 这里应该实现查看配方详情的功能
        QMessageBox.information(self, "配方详情", f"查看配方ID: {recipe_id} 的详情")


# 主窗口
class SmartSpiceSystem(QMainWindow):
    def __init__(self):
        super().__init__()
        self.db = SpiceDatabase()
        self.init_ui()
        
        # 添加示例数据
        self.add_sample_data()
    
    def init_ui(self):
        self.setWindowTitle("智能香料系统 - 高级工具库")
        self.setGeometry(100, 100, 1200, 800)
        
        # 创建中央部件和选项卡
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        
        # 创建选项卡
        self.tabs = QTabWidget()
        
        # 香料管理选项卡
        self.spice_tab = SpiceManagerWidget(self.db)
        self.tabs.addTab(self.spice_tab, "香料管理")
        
        # 配方管理选项卡
        self.recipe_tab = RecipeManagerWidget(self.db)
        self.tabs.addTab(self.recipe_tab, "配方管理")
        
        # 数据分析选项卡
        self.analytics_tab = AnalyticsWidget(self.db)
        self.tabs.addTab(self.analytics_tab, "数据分析")
        
        layout.addWidget(self.tabs)
        
        # 状态栏
        self.statusBar().showMessage("智能香料系统已就绪")
    
    def add_sample_data(self):
        # 添加示例香料数据
        sample_spices = [
            ("肉桂", "树皮", "中国", 7.5, 150.0, "甜味香料，常用于烘焙和炖菜"),
            ("丁香", "花蕾", "印度尼西亚", 9.0, 200.0, "强烈芳香，常用于肉类和甜点"),
            ("八角", "果实", "中国", 8.0, 120.0, "甘草味，是中式五香粉的主要成分"),
            ("姜黄", "根茎", "印度", 6.5, 80.0, "黄色香料，是咖喱的主要成分"),
            ("小茴香", "种子", "中东", 6.0, 60.0, "坚果味，常用于中东和印度菜"),
            ("辣椒粉", "果实", "墨西哥", 8.5, 90.0, "辛辣，为菜肴增添热量和颜色"),
            ("肉豆蔻", "种子", "印度尼西亚", 7.0, 180.0, "温暖甜味，常用于甜点和饮料"),
        ]
        
        for spice in sample_spices:
            self.db.add_spice(*spice)


# 应用程序入口
def main():
    app = QApplication(sys.argv)
    
    # 设置应用程序样式
    app.setStyle('Fusion')
    
    # 创建并显示主窗口
    window = SmartSpiceSystem()
    window.show()
    
    # 运行应用程序
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()