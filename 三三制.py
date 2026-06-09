import sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.rc("font", family='Microsoft YaHei')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d import Axes3D
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QGroupBox, QLabel, QLineEdit, QPushButton,
                             QComboBox, QTabWidget, QTableWidget, QTableWidgetItem,
                             QHeaderView, QMessageBox, QSpinBox, QDoubleSpinBox,
                             QSlider, QCheckBox, QSplitter, QTextEdit, QProgressBar,
                             QFileDialog, QListWidget, QTreeWidget, QTreeWidgetItem)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QPalette, QColor, QIcon
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error, r2_score
import random
import time
import json
from datetime import datetime
import socket
import threading
import os
from scipy import stats


class AIPredictor(QThread):
    """AI预测线程"""
    prediction_ready = pyqtSignal(dict)
    training_progress = pyqtSignal(int)
    
    def __init__(self, historical_data):
        super().__init__()
        self.historical_data = historical_data
        self.model = RandomForestRegressor(n_estimators=100, random_state=42)
        self.scaler = StandardScaler()
        
    def run(self):
        """训练模型并做出预测"""
        try:
            # 准备数据
            X = self.historical_data[['troops', 'front_width', 'depth', 'firepower', 'terrain_factor']]
            y = self.historical_data[['effectiveness']]
            
            # 分割数据
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
            
            # 标准化
            X_train_scaled = self.scaler.fit_transform(X_train)
            X_test_scaled = self.scaler.transform(X_test)
            
            # 训练模型 - 模拟进度
            self.model.fit(X_train_scaled, y_train.values.ravel())
            
            # 预测最新数据
            latest_data = X.iloc[-1:].values
            latest_scaled = self.scaler.transform(latest_data)
            prediction = self.model.predict(latest_scaled)[0]
            
            # 计算特征重要性
            feature_importance = dict(zip(X.columns, self.model.feature_importances_))
            
            # 计算模型评估指标
            y_pred = self.model.predict(X_test_scaled)
            mse = mean_squared_error(y_test, y_pred)
            r2 = r2_score(y_test, y_pred)
            
            # 发送结果
            result = {
                'predicted_effectiveness': prediction,
                'feature_importance': feature_importance,
                'model_score': self.model.score(X_test_scaled, y_test),
                'mse': mse,
                'r2': r2
            }
            
            self.prediction_ready.emit(result)
            
        except Exception as e:
            print(f"AI预测错误: {e}")
            self.prediction_ready.emit({'error': str(e)})


class BattlefieldSimulator(QWidget):
    """战场动态模拟器"""
    
    def __init__(self):
        super().__init__()
        self.units = []
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_simulation)
        self.initUI()
        
    def initUI(self):
        """初始化模拟器界面"""
        layout = QVBoxLayout(self)
        
        # 控制面板
        control_panel = QHBoxLayout()
        self.start_btn = QPushButton("开始模拟")
        self.start_btn.clicked.connect(self.toggle_simulation)
        self.reset_btn = QPushButton("重置")
        self.reset_btn.clicked.connect(self.reset_simulation)
        
        control_panel.addWidget(self.start_btn)
        control_panel.addWidget(self.reset_btn)
        control_panel.addStretch()
        
        # 速度控制
        control_panel.addWidget(QLabel("模拟速度:"))
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setRange(1, 10)
        self.speed_slider.setValue(5)
        control_panel.addWidget(self.speed_slider)
        
        # 地形影响因子
        control_panel.addWidget(QLabel("地形影响:"))
        self.terrain_effect = QComboBox()
        self.terrain_effect.addItems(["低", "中", "高"])
        self.terrain_effect.setCurrentIndex(1)
        control_panel.addWidget(self.terrain_effect)
        
        layout.addLayout(control_panel)
        
        # 模拟画布
        self.figure = Figure(figsize=(10, 8))
        self.canvas = FigureCanvas(self.figure)
        self.ax = self.figure.add_subplot(111)
        layout.addWidget(self.canvas)
        
        # 状态显示
        self.status_label = QLabel("就绪")
        layout.addWidget(self.status_label)
        
    def setup_simulation(self, units_data, terrain_type="平原", terrain_factor=0.5):
        """设置模拟参数"""
        self.units = []
        self.terrain_type = terrain_type
        self.terrain_factor = terrain_factor
        
        # 创建单位
        for unit_type, count in units_data.items():
            for i in range(count):
                unit = {
                    'type': unit_type,
                    'x': random.uniform(0, 100),
                    'y': random.uniform(0, 100),
                    'health': 100,
                    'color': self.get_unit_color(unit_type),
                    'size': self.get_unit_size(unit_type),
                    'speed': self.get_unit_speed(unit_type),
                    'firepower': self.get_unit_firepower(unit_type)
                }
                self.units.append(unit)
        
        self.draw_battlefield()
        self.status_label.setText("模拟已设置，点击开始模拟")
        
    def get_unit_color(self, unit_type):
        """根据单位类型获取颜色"""
        colors = {
            'squad': 'blue',
            'platoon': 'green',
            'company': 'red',
            'battalion': 'purple'
        }
        return colors.get(unit_type, 'gray')
    
    def get_unit_size(self, unit_type):
        """根据单位类型获取大小"""
        sizes = {
            'squad': 30,
            'platoon': 50,
            'company': 70,
            'battalion': 100
        }
        return sizes.get(unit_type, 40)
    
    def get_unit_speed(self, unit_type):
        """根据单位类型获取速度"""
        speeds = {
            'squad': 1.5,
            'platoon': 1.2,
            'company': 1.0,
            'battalion': 0.8
        }
        return speeds.get(unit_type, 1.0)
    
    def get_unit_firepower(self, unit_type):
        """根据单位类型获取火力"""
        firepowers = {
            'squad': 10,
            'platoon': 30,
            'company': 90,
            'battalion': 270
        }
        return firepowers.get(unit_type, 10)
    
    def draw_battlefield(self):
        """绘制战场"""
        self.ax.clear()
        
        # 绘制地形背景
        if self.terrain_type == "平原":
            self.ax.set_facecolor('#c9e3ac')  # 浅绿色
        elif self.terrain_type == "山地":
            self.ax.set_facecolor('#a3927c')  # 土棕色
            # 添加一些随机山丘
            for _ in range(5):
                x, y = random.uniform(0, 100), random.uniform(0, 100)
                size = random.uniform(5, 15)
                circle = plt.Circle((x, y), size, color='#8a795d', alpha=0.5)
                self.ax.add_patch(circle)
        elif self.terrain_type == "城市":
            self.ax.set_facecolor('#b3b3b3')  # 灰色
            # 添加一些建筑物
            for _ in range(8):
                x, y = random.uniform(0, 100), random.uniform(0, 100)
                width, height = random.uniform(3, 8), random.uniform(5, 15)
                rect = plt.Rectangle((x, y), width, height, color='#808080', alpha=0.7)
                self.ax.add_patch(rect)
        
        # 绘制单位
        for unit in self.units:
            if unit['health'] > 0:
                circle = plt.Circle(
                    (unit['x'], unit['y']), 
                    unit['size']/50,  # 缩放大小以适应画布
                    color=unit['color'],
                    alpha=unit['health']/100
                )
                self.ax.add_patch(circle)
                self.ax.text(unit['x'], unit['y'], unit['type'][0].upper(), 
                            ha='center', va='center', color='white', fontweight='bold')
        
        self.ax.set_xlim(0, 100)
        self.ax.set_ylim(0, 100)
        self.ax.set_title(f'{self.terrain_type}战场模拟 (地形影响因子: {self.terrain_factor})')
        self.ax.set_aspect('equal')
        self.canvas.draw()
    
    def toggle_simulation(self):
        """切换模拟状态"""
        if self.timer.isActive():
            self.timer.stop()
            self.start_btn.setText("开始模拟")
            self.status_label.setText("模拟暂停")
        else:
            interval = 1100 - (self.speed_slider.value() * 100)  # 100-1000ms
            self.timer.start(interval)
            self.start_btn.setText("暂停模拟")
            self.status_label.setText("模拟进行中...")
    
    def reset_simulation(self):
        """重置模拟"""
        self.timer.stop()
        self.start_btn.setText("开始模拟")
        # 获取地形影响因子
        terrain_effect_map = {"低": 0.3, "中": 0.5, "高": 0.8}
        terrain_factor = terrain_effect_map[self.terrain_effect.currentText()]
        
        self.setup_simulation(
            {unit['type']: sum(1 for u in self.units if u['type'] == unit['type']) 
             for unit in self.units},
            self.terrain_type,
            terrain_factor
        )
    
    def update_simulation(self):
        """更新模拟状态"""
        # 获取地形影响因子
        terrain_effect_map = {"低": 0.3, "中": 0.5, "高": 0.8}
        terrain_factor = terrain_effect_map[self.terrain_effect.currentText()]
        
        # 移动单位
        for unit in self.units:
            if unit['health'] > 0:
                # 根据单位速度和地形影响计算移动距离
                move_distance = unit['speed'] * (1 - terrain_factor * 0.5)
                unit['x'] += random.uniform(-move_distance, move_distance)
                unit['y'] += random.uniform(-move_distance, move_distance)
                
                # 确保单位在战场范围内
                unit['x'] = max(0, min(100, unit['x']))
                unit['y'] = max(0, min(100, unit['y']))
                
                # 随机减少生命值（模拟战斗）
                if random.random() < 0.05:  # 5%的概率受到伤害
                    damage = random.uniform(5, 15) * (1 + terrain_factor)
                    unit['health'] -= damage
                    unit['health'] = max(0, unit['health'])
        
        self.draw_battlefield()
        
        # 检查是否所有单位都"阵亡"
        if all(unit['health'] <= 0 for unit in self.units):
            self.timer.stop()
            self.start_btn.setText("开始模拟")
            self.status_label.setText("模拟结束 - 所有单位已退出战斗")


class ThreeDVisualization(FigureCanvas):
    """三维可视化组件"""
    
    def __init__(self, parent=None):
        self.fig = Figure(figsize=(10, 8))
        super(ThreeDVisualization, self).__init__(self.fig)
        self.setParent(parent)
        self.ax = self.fig.add_subplot(111, projection='3d')
        
    def plot_3d_organization(self, units_data, terrain_type="平原"):
        """绘制三维组织结构图"""
        self.ax.clear()
        
        # 定义颜色和位置
        colors = {'squad': 'blue', 'platoon': 'green', 'company': 'red', 'battalion': 'purple'}
        sizes = {'squad': 30, 'platoon': 50, 'company': 70, 'battalion': 100}
        
        # 绘制单位
        z_offset = 0
        for unit_type, count in units_data.items():
            if count == 0:
                continue
                
            # 创建网格位置
            grid_size = int(np.ceil(np.sqrt(count)))
            x_positions = np.linspace(0, 10, grid_size)
            y_positions = np.linspace(0, 10, grid_size)
            
            for i in range(count):
                x = x_positions[i % grid_size]
                y = y_positions[i // grid_size]
                
                # 绘制球体
                self.ax.scatter(
                    x, y, z_offset, 
                    s=sizes[unit_type], 
                    c=colors[unit_type], 
                    alpha=0.7,
                    edgecolors='w'
                )
                
                # 添加标签
                self.ax.text(x, y, z_offset, unit_type[0].upper(), 
                            ha='center', va='center', color='white')
            
            z_offset += 5
        
        # 设置图表属性
        self.ax.set_xlabel('X 轴')
        self.ax.set_ylabel('Y 轴')
        self.ax.set_zlabel('层级')
        self.ax.set_title(f'三维组织结构 - {terrain_type}地形')
        
        self.draw()
    
    def plot_3d_coverage(self, front_width, depth, height_variation=0):
        """绘制三维覆盖范围"""
        self.ax.clear()
        
        # 创建网格数据
        x = np.linspace(0, front_width, 20)
        y = np.linspace(0, depth, 20)
        X, Y = np.meshgrid(x, y)
        
        # 根据地形类型创建高度变化
        if height_variation > 0:
            Z = np.sin(X/front_width * 4 * np.pi) * np.cos(Y/depth * 4 * np.pi) * height_variation
        else:
            Z = np.zeros_like(X)
        
        # 绘制表面
        surf = self.ax.plot_surface(X, Y, Z, cmap='terrain', alpha=0.7)
        
        # 添加颜色条
        self.fig.colorbar(surf, ax=self.ax, shrink=0.5, aspect=5)
        
        # 设置图表属性
        self.ax.set_xlabel('正面宽度 (米)')
        self.ax.set_ylabel('纵深 (米)')
        self.ax.set_zlabel('高度变化 (米)')
        self.ax.set_title('三维地形覆盖分析')
        
        self.draw()
    
    def plot_3d_effectiveness(self, historical_data):
        """绘制三维效能分析图"""
        self.ax.clear()
        
        if len(historical_data) < 3:
            return
        
        # 提取数据
        troops = historical_data['troops'].values
        front_width = historical_data['front_width'].values
        depth = historical_data['depth'].values
        effectiveness = historical_data['effectiveness'].values
        
        # 创建网格
        xi = np.linspace(troops.min(), troops.max(), 20)
        yi = np.linspace(front_width.min(), front_width.max(), 20)
        X, Y = np.meshgrid(xi, yi)
        
        # 插值计算Z值
        Z = griddata((troops, front_width), effectiveness, (X, Y), method='cubic')
        
        # 绘制表面
        surf = self.ax.plot_surface(X, Y, Z, cmap='viridis', alpha=0.8)
        
        # 添加散点图
        self.ax.scatter(troops, front_width, effectiveness, c='red', marker='o', s=50)
        
        # 添加颜色条
        self.fig.colorbar(surf, ax=self.ax, shrink=0.5, aspect=5)
        
        # 设置图表属性
        self.ax.set_xlabel('兵力')
        self.ax.set_ylabel('正面宽度')
        self.ax.set_zlabel('效能')
        self.ax.set_title('兵力-正面宽度-效能三维分析')
        
        self.draw()


class NetworkCollaboration(QThread):
    """网络协作线程"""
    message_received = pyqtSignal(dict)
    
    def __init__(self, port=12345):
        super().__init__()
        self.port = port
        self.running = False
        self.clients = []
        
    def run(self):
        """启动网络服务器"""
        self.running = True
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(('', self.port))
        
        while self.running:
            try:
                data, addr = self.socket.recvfrom(1024)
                if addr not in self.clients:
                    self.clients.append(addr)
                
                message = json.loads(data.decode())
                message['sender'] = addr
                self.message_received.emit(message)
                
            except Exception as e:
                if self.running:
                    print(f"网络错误: {e}")
    
    def stop(self):
        """停止网络服务器"""
        self.running = False
        if hasattr(self, 'socket'):
            self.socket.close()
    
    def send_message(self, message, address):
        """发送消息到指定地址"""
        try:
            data = json.dumps(message).encode()
            self.socket.sendto(data, address)
        except Exception as e:
            print(f"发送错误: {e}")


class RevolutionaryThreeThreeAnalysisApp(QMainWindow):
    """颠覆性的三三制高级分析工具"""
    
    def __init__(self):
        super().__init__()
        self.historical_data = pd.DataFrame(columns=[
            'troops', 'front_width', 'depth', 'firepower', 'terrain_factor', 'effectiveness'
        ])
        self.network = NetworkCollaboration()
        self.network.message_received.connect(self.handle_network_message)
        self.initUI()
        
    def initUI(self):
        """初始化用户界面"""
        self.setWindowTitle('颠覆性三三制高级分析工具 v2.0')
        self.setGeometry(100, 100, 1600, 1000)
        
        # 设置应用样式
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2b2b2b;
                color: #cccccc;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #555555;
                border-radius: 5px;
                margin-top: 1ex;
                padding-top: 10px;
                background-color: #3c3f41;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #cccccc;
            }
            QPushButton {
                background-color: #4CAF50;
                border: none;
                color: white;
                padding: 8px 16px;
                text-align: center;
                text-decoration: none;
                font-size: 14px;
                margin: 4px 2px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #555555;
            }
            QLabel {
                font-weight: bold;
                color: #cccccc;
            }
            QTabWidget::pane {
                border: 1px solid #555555;
                background-color: #3c3f41;
            }
            QTabBar::tab {
                background: #2b2b2b;
                color: #cccccc;
                padding: 8px 12px;
                border: 1px solid #555555;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background: #3c3f41;
                border-color: #555555;
            }
            QTableWidget {
                background-color: #3c3f41;
                color: #cccccc;
                gridline-color: #555555;
            }
            QHeaderView::section {
                background-color: #2b2b2b;
                color: #cccccc;
                padding: 4px;
                border: 1px solid #555555;
            }
            QTextEdit {
                background-color: #3c3f41;
                color: #cccccc;
            }
            QLineEdit {
                background-color: #3c3f41;
                color: #cccccc;
                border: 1px solid #555555;
                padding: 5px;
            }
        """)
        
        # 创建中心部件和主布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # 创建选项卡
        tab_widget = QTabWidget()
        main_layout.addWidget(tab_widget)
        
        # 添加多个功能选项卡
        self.setup_analysis_tab(tab_widget)
        self.setup_simulation_tab(tab_widget)
        self.setup_3d_visualization_tab(tab_widget)
        self.setup_ai_prediction_tab(tab_widget)
        self.setup_network_tab(tab_widget)
        self.setup_historical_analysis_tab(tab_widget)
        self.setup_statistical_analysis_tab(tab_widget)
        
        # 状态栏
        self.statusBar().showMessage("就绪")
        
        # 启动网络协作
        self.network.start()
        
    def setup_analysis_tab(self, tab_widget):
        """设置分析选项卡"""
        tab = QWidget()
        tab_widget.addTab(tab, "基础分析")
        layout = QHBoxLayout(tab)
        
        # 左侧输入区域
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        # 兵力输入组
        troops_group = QGroupBox("兵力配置")
        troops_layout = QVBoxLayout(troops_group)
        
        troops_form = QHBoxLayout()
        troops_form.addWidget(QLabel("总兵力:"))
        self.total_troops_spin = QSpinBox()
        self.total_troops_spin.setRange(0, 10000)
        self.total_troops_spin.setValue(1000)
        troops_form.addWidget(self.total_troops_spin)
        troops_layout.addLayout(troops_form)
        
        structure_form = QHBoxLayout()
        structure_form.addWidget(QLabel("结构层级:"))
        self.structure_combo = QComboBox()
        self.structure_combo.addItems(["班", "排", "连", "营"])
        structure_form.addWidget(self.structure_combo)
        troops_layout.addLayout(structure_form)
        
        left_layout.addWidget(troops_group)
        
        # 战术参数组
        tactics_group = QGroupBox("战术参数")
        tactics_layout = QVBoxLayout(tactics_group)
        
        front_form = QHBoxLayout()
        front_form.addWidget(QLabel("每班正面宽度:"))
        self.front_width_spin = QDoubleSpinBox()
        self.front_width_spin.setRange(0, 1000)
        self.front_width_spin.setValue(50)
        self.front_width_spin.setSuffix(" 米")
        front_form.addWidget(self.front_width_spin)
        tactics_layout.addLayout(front_form)
        
        depth_form = QHBoxLayout()
        depth_form.addWidget(QLabel("每班纵深:"))
        self.depth_spin = QDoubleSpinBox()
        self.depth_spin.setRange(0, 1000)
        self.depth_spin.setValue(100)
        self.depth_spin.setSuffix(" 米")
        depth_form.addWidget(self.depth_spin)
        tactics_layout.addLayout(depth_form)
        
        firepower_form = QHBoxLayout()
        firepower_form.addWidget(QLabel("每班火力指数:"))
        self.firepower_spin = QDoubleSpinBox()
        self.firepower_spin.setRange(0, 1000)
        self.firepower_spin.setValue(10)
        firepower_form.addWidget(self.firepower_spin)
        tactics_layout.addLayout(firepower_form)
        
        terrain_form = QHBoxLayout()
        terrain_form.addWidget(QLabel("地形类型:"))
        self.terrain_combo = QComboBox()
        self.terrain_combo.addItems(["平原", "山地", "城市"])
        terrain_form.addWidget(self.terrain_combo)
        tactics_layout.addLayout(terrain_form)
        
        terrain_factor_form = QHBoxLayout()
        terrain_factor_form.addWidget(QLabel("地形影响因子:"))
        self.terrain_factor_spin = QDoubleSpinBox()
        self.terrain_factor_spin.setRange(0, 1)
        self.terrain_factor_spin.setValue(0.5)
        self.terrain_factor_spin.setSingleStep(0.1)
        terrain_factor_form.addWidget(self.terrain_factor_spin)
        tactics_layout.addLayout(terrain_factor_form)
        
        left_layout.addWidget(tactics_group)
        
        # 分析按钮
        analyze_btn = QPushButton("开始分析")
        analyze_btn.clicked.connect(self.analyze)
        left_layout.addWidget(analyze_btn)
        
        # 保存配置按钮
        save_config_btn = QPushButton("保存配置")
        save_config_btn.clicked.connect(self.save_config)
        left_layout.addWidget(save_config_btn)
        
        # 加载配置按钮
        load_config_btn = QPushButton("加载配置")
        load_config_btn.clicked.connect(self.load_config)
        left_layout.addWidget(load_config_btn)
        
        left_layout.addStretch()
        
        # 右侧结果区域
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        # 结果表格
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(2)
        self.results_table.setHorizontalHeaderLabels(["指标", "值"])
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        right_layout.addWidget(self.results_table)
        
        # 将左右两部分添加到主布局
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([300, 700])
        layout.addWidget(splitter)
        
    def setup_simulation_tab(self, tab_widget):
        """设置模拟选项卡"""
        tab = QWidget()
        tab_widget.addTab(tab, "战场模拟")
        layout = QVBoxLayout(tab)
        
        self.simulator = BattlefieldSimulator()
        layout.addWidget(self.simulator)
        
    def setup_3d_visualization_tab(self, tab_widget):
        """设置3D可视化选项卡"""
        tab = QWidget()
        tab_widget.addTab(tab, "3D可视化")
        layout = QVBoxLayout(tab)
        
        # 3D可视化控制
        viz_control = QHBoxLayout()
        viz_control.addWidget(QLabel("可视化类型:"))
        self.viz_type_combo = QComboBox()
        self.viz_type_combo.addItems(["组织结构", "地形覆盖", "效能分析"])
        self.viz_type_combo.currentTextChanged.connect(self.update_3d_visualization)
        viz_control.addWidget(self.viz_type_combo)
        
        layout.addLayout(viz_control)
        
        self.visualization_3d = ThreeDVisualization()
        layout.addWidget(self.visualization_3d)
        
    def setup_ai_prediction_tab(self, tab_widget):
        """设置AI预测选项卡"""
        tab = QWidget()
        tab_widget.addTab(tab, "AI预测")
        layout = QVBoxLayout(tab)
        
        # AI预测控制
        ai_control = QHBoxLayout()
        self.ai_train_btn = QPushButton("训练AI模型")
        self.ai_train_btn.clicked.connect(self.train_ai_model)
        ai_control.addWidget(self.ai_train_btn)
        
        self.ai_predict_btn = QPushButton("进行预测")
        self.ai_predict_btn.clicked.connect(self.predict_with_ai)
        self.ai_predict_btn.setEnabled(False)
        ai_control.addWidget(self.ai_predict_btn)
        
        self.ai_optimize_btn = QPushButton("优化参数")
        self.ai_optimize_btn.clicked.connect(self.optimize_parameters)
        self.ai_optimize_btn.setEnabled(False)
        ai_control.addWidget(self.ai_optimize_btn)
        
        layout.addLayout(ai_control)
        
        # 训练进度
        self.ai_progress = QProgressBar()
        self.ai_progress.setVisible(False)
        layout.addWidget(self.ai_progress)
        
        # 预测结果
        self.ai_results = QTextEdit()
        self.ai_results.setReadOnly(True)
        layout.addWidget(self.ai_results)
        
    def setup_network_tab(self, tab_widget):
        """设置网络协作选项卡"""
        tab = QWidget()
        tab_widget.addTab(tab, "网络协作")
        layout = QVBoxLayout(tab)
        
        # 网络状态
        network_status = QHBoxLayout()
        network_status.addWidget(QLabel("网络状态:"))
        self.network_status_label = QLabel("运行中")
        network_status.addWidget(self.network_status_label)
        
        network_status.addWidget(QLabel("端口:"))
        self.port_input = QLineEdit("12345")
        network_status.addWidget(self.port_input)
        
        restart_btn = QPushButton("重启网络")
        restart_btn.clicked.connect(self.restart_network)
        network_status.addWidget(restart_btn)
        
        network_status.addStretch()
        
        layout.addLayout(network_status)
        
        # 消息发送
        message_send = QHBoxLayout()
        message_send.addWidget(QLabel("发送消息:"))
        self.message_input = QLineEdit()
        message_send.addWidget(self.message_input)
        
        self.send_message_btn = QPushButton("发送")
        self.send_message_btn.clicked.connect(self.send_network_message)
        message_send.addWidget(self.send_message_btn)
        
        layout.addLayout(message_send)
        
        # 消息历史
        layout.addWidget(QLabel("消息历史:"))
        self.message_history = QTextEdit()
        self.message_history.setReadOnly(True)
        layout.addWidget(self.message_history)
        
    def setup_historical_analysis_tab(self, tab_widget):
        """设置历史分析选项卡"""
        tab = QWidget()
        tab_widget.addTab(tab, "历史分析")
        layout = QVBoxLayout(tab)
        
        # 历史数据操作
        history_controls = QHBoxLayout()
        self.import_history_btn = QPushButton("导入历史数据")
        self.import_history_btn.clicked.connect(self.import_historical_data)
        history_controls.addWidget(self.import_history_btn)
        
        self.export_history_btn = QPushButton("导出历史数据")
        self.export_history_btn.clicked.connect(self.export_historical_data)
        history_controls.addWidget(self.export_history_btn)
        
        self.clear_history_btn = QPushButton("清除历史数据")
        self.clear_history_btn.clicked.connect(self.clear_historical_data)
        history_controls.addWidget(self.clear_history_btn)
        
        self.plot_history_btn = QPushButton("绘制历史趋势")
        self.plot_history_btn.clicked.connect(self.plot_historical_trend)
        history_controls.addWidget(self.plot_history_btn)
        
        layout.addLayout(history_controls)
        
        # 历史数据表格
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(6)
        self.history_table.setHorizontalHeaderLabels(["兵力", "正面宽度", "纵深", "火力", "地形因子", "效能"])
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.history_table)
        
    def setup_statistical_analysis_tab(self, tab_widget):
        """设置统计分析选项卡"""
        tab = QWidget()
        tab_widget.addTab(tab, "统计分析")
        layout = QVBoxLayout(tab)
        
        # 统计分析控制
        stats_control = QHBoxLayout()
        stats_control.addWidget(QLabel("分析类型:"))
        self.stats_type_combo = QComboBox()
        self.stats_type_combo.addItems(["相关性分析", "回归分析", "假设检验"])
        stats_control.addWidget(self.stats_type_combo)
        
        self.run_stats_btn = QPushButton("执行分析")
        self.run_stats_btn.clicked.connect(self.run_statistical_analysis)
        stats_control.addWidget(self.run_stats_btn)
        
        layout.addLayout(stats_control)
        
        # 分析结果
        self.stats_results = QTextEdit()
        self.stats_results.setReadOnly(True)
        layout.addWidget(self.stats_results)
        
    def analyze(self):
        """执行分析"""
        try:
            # 获取输入值
            total_troops = self.total_troops_spin.value()
            structure_level = self.structure_combo.currentText()
            front_width = self.front_width_spin.value()
            depth = self.depth_spin.value()
            firepower = self.firepower_spin.value()
            terrain_type = self.terrain_combo.currentText()
            terrain_factor = self.terrain_factor_spin.value()
            
            # 映射中文层级到英文键
            level_map = {"班": "squad", "排": "platoon", "连": "company", "营": "battalion"}
            structure_key = level_map[structure_level]
            
            # 执行计算
            analyzer = ThreeThreeSystemAnalyzer()
            units = analyzer.calculate_units(total_troops, structure_key)
            
            # 检查单位数量是否有效
            if units['squads'] <= 0:
                QMessageBox.warning(self, "警告", "计算出的班数量为0或负数，请调整兵力配置")
                return
                
            coverage = analyzer.calculate_coverage(front_width, depth)
            firepower_data = analyzer.calculate_firepower(firepower)
            
            # 计算效能指标（考虑地形因素）
            effectiveness = (units['squads'] * 0.3 + 
                           coverage['front_width'] * 0.2 + 
                           coverage['depth'] * 0.1 + 
                           firepower_data['total_firepower'] * 0.4) * (1 - terrain_factor * 0.2)
            
            # 更新结果表格
            data = [
                ["总兵力", f"{total_troops} 人"],
                ["班数量", f"{units['squads']} 个"],
                ["排数量", f"{units['platoons']} 个"],
                ["连数量", f"{units['companies']} 个"],
                ["营数量", f"{units['battalions']} 个"],
                ["正面宽度", f"{coverage['front_width']:.2f} 米"],
                ["纵深", f"{coverage['depth']:.2f} 米"],
                ["总火力指数", f"{firepower_data['total_firepower']:.2f}"],
                ["平均火力密度", f"{firepower_data['firepower_density']:.2f} 每班"],
                ["控制区域", f"{coverage['front_width'] * coverage['depth']:.2f} 平方米"],
                ["地形类型", terrain_type],
                ["地形影响因子", f"{terrain_factor:.2f}"],
                ["综合效能指标", f"{effectiveness:.2f}"]
            ]
            
            self.results_table.setRowCount(len(data))
            for i, (key, value) in enumerate(data):
                self.results_table.setItem(i, 0, QTableWidgetItem(key))
                self.results_table.setItem(i, 1, QTableWidgetItem(value))
            
            # 设置模拟器
            self.simulator.setup_simulation(units, terrain_type, terrain_factor)
            
            # 设置3D可视化
            self.update_3d_visualization()
            
            # 保存到历史数据
            new_data = pd.DataFrame({
                'troops': [total_troops],
                'front_width': [front_width],
                'depth': [depth],
                'firepower': [firepower],
                'terrain_factor': [terrain_factor],
                'effectiveness': [effectiveness]
            })
            self.historical_data = pd.concat([self.historical_data, new_data], ignore_index=True)
            self.update_history_table()
            
            # 启用AI预测按钮
            self.ai_predict_btn.setEnabled(len(self.historical_data) >= 10)
            self.ai_optimize_btn.setEnabled(len(self.historical_data) >= 10)
            
            self.statusBar().showMessage("分析完成")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"分析过程中发生错误: {str(e)}")
            self.statusBar().showMessage(f"错误: {str(e)}")
            
    def update_3d_visualization(self):
        """更新3D可视化"""
        viz_type = self.viz_type_combo.currentText()
        
        if viz_type == "组织结构":
            # 获取当前单位数据
            total_troops = self.total_troops_spin.value()
            structure_level = self.structure_combo.currentText()
            level_map = {"班": "squad", "排": "platoon", "连": "company", "营": "battalion"}
            structure_key = level_map[structure_level]
            
            analyzer = ThreeThreeSystemAnalyzer()
            units = analyzer.calculate_units(total_troops, structure_key)
            terrain_type = self.terrain_combo.currentText()
            
            self.visualization_3d.plot_3d_organization(units, terrain_type)
            
        elif viz_type == "地形覆盖":
            front_width = self.front_width_spin.value()
            depth = self.depth_spin.value()
            terrain_type = self.terrain_combo.currentText()
            
            # 根据地形类型设置高度变化
            height_variation = 0
            if terrain_type == "山地":
                height_variation = 50
            elif terrain_type == "城市":
                height_variation = 30
                
            self.visualization_3d.plot_3d_coverage(front_width, depth, height_variation)
            
        elif viz_type == "效能分析" and len(self.historical_data) >= 3:
            self.visualization_3d.plot_3d_effectiveness(self.historical_data)
            
    def update_history_table(self):
        """更新历史数据表格"""
        self.history_table.setRowCount(len(self.historical_data))
        for i, row in self.historical_data.iterrows():
            self.history_table.setItem(i, 0, QTableWidgetItem(str(row['troops'])))
            self.history_table.setItem(i, 1, QTableWidgetItem(str(row['front_width'])))
            self.history_table.setItem(i, 2, QTableWidgetItem(str(row['depth'])))
            self.history_table.setItem(i, 3, QTableWidgetItem(str(row['firepower'])))
            self.history_table.setItem(i, 4, QTableWidgetItem(str(row['terrain_factor'])))
            self.history_table.setItem(i, 5, QTableWidgetItem(str(row['effectiveness'])))
    
    def train_ai_model(self):
        """训练AI模型"""
        if len(self.historical_data) < 10:
            QMessageBox.warning(self, "警告", "需要至少10条历史数据才能训练AI模型")
            return
        
        self.ai_results.append("开始训练AI模型...")
        self.ai_train_btn.setEnabled(False)
        self.ai_progress.setVisible(True)
        self.ai_progress.setRange(0, 0)  # 不确定进度
        
        # 在后台线程中训练模型
        self.ai_predictor = AIPredictor(self.historical_data)
        self.ai_predictor.prediction_ready.connect(self.handle_ai_prediction)
        self.ai_predictor.training_progress.connect(self.update_ai_progress)
        self.ai_predictor.start()
    
    def update_ai_progress(self, progress):
        """更新AI训练进度"""
        self.ai_progress.setValue(progress)
    
    def predict_with_ai(self):
        """使用AI进行预测"""
        if not hasattr(self, 'ai_predictor') or self.ai_predictor is None:
            QMessageBox.warning(self, "警告", "请先训练AI模型")
            return
        
        # 获取当前输入值
        total_troops = self.total_troops_spin.value()
        front_width = self.front_width_spin.value()
        depth = self.depth_spin.value()
        firepower = self.firepower_spin.value()
        terrain_factor = self.terrain_factor_spin.value()
        
        # 使用当前数据进行预测
        current_data = pd.DataFrame({
            'troops': [total_troops],
            'front_width': [front_width],
            'depth': [depth],
            'firepower': [firepower],
            'terrain_factor': [terrain_factor]
        })
        
        try:
            current_scaled = self.ai_predictor.scaler.transform(current_data)
            prediction = self.ai_predictor.model.predict(current_scaled)[0]
            
            self.ai_results.append(f"AI预测结果: 效能指标 = {prediction:.2f}")
            self.statusBar().showMessage(f"AI预测完成: 效能指标 = {prediction:.2f}")
            
        except Exception as e:
            self.ai_results.append(f"预测错误: {str(e)}")
            self.statusBar().showMessage(f"预测错误: {str(e)}")
    
    def optimize_parameters(self):
        """优化参数"""
        if not hasattr(self, 'ai_predictor') or self.ai_predictor is None:
            QMessageBox.warning(self, "警告", "请先训练AI模型")
            return
        
        self.ai_results.append("开始参数优化...")
        
        # 获取特征重要性
        feature_importance = self.ai_predictor.model.feature_importances_
        features = ['troops', 'front_width', 'depth', 'firepower', 'terrain_factor']
        
        # 找到最重要的特征
        most_important_feature = features[np.argmax(feature_importance)]
        self.ai_results.append(f"最重要的参数: {most_important_feature}")
        
        # 提供优化建议
        if most_important_feature == 'troops':
            self.ai_results.append("优化建议: 考虑增加总兵力以提高效能")
        elif most_important_feature == 'front_width':
            self.ai_results.append("优化建议: 调整正面宽度以优化部署")
        elif most_important_feature == 'depth':
            self.ai_results.append("优化建议: 调整纵深以增强防御")
        elif most_important_feature == 'firepower':
            self.ai_results.append("优化建议: 增强火力配置以提高作战能力")
        elif most_important_feature == 'terrain_factor':
            self.ai_results.append("优化建议: 选择更有利的地形或调整地形影响因子")
        
        self.statusBar().showMessage("参数优化完成")
    
    def handle_ai_prediction(self, result):
        """处理AI预测结果"""
        self.ai_train_btn.setEnabled(True)
        self.ai_progress.setVisible(False)
        
        if 'error' in result:
            self.ai_results.append(f"AI训练错误: {result['error']}")
            self.statusBar().showMessage(f"AI训练错误: {result['error']}")
            return
        
        self.ai_results.append("AI模型训练完成!")
        self.ai_results.append(f"模型评分: {result['model_score']:.4f}")
        self.ai_results.append(f"均方误差: {result['mse']:.4f}")
        self.ai_results.append(f"R²分数: {result['r2']:.4f}")
        self.ai_results.append("特征重要性:")
        
        for feature, importance in result['feature_importance'].items():
            self.ai_results.append(f"  {feature}: {importance:.4f}")
        
        self.ai_results.append(f"预测效能: {result['predicted_effectiveness']:.2f}")
        self.statusBar().showMessage("AI模型训练完成")
    
    def send_network_message(self):
        """发送网络消息"""
        message = self.message_input.text()
        if not message:
            return
        
        # 构建消息对象
        message_obj = {
            'type': 'chat',
            'content': message,
            'timestamp': datetime.now().isoformat(),
            'sender': '本地用户'
        }
        
        # 添加到消息历史
        self.message_history.append(f"[本地] {datetime.now().strftime('%H:%M:%S')}: {message}")
        self.message_input.clear()
        
        # 发送给所有客户端
        for client in self.network.clients:
            self.network.send_message(message_obj, client)
    
    def handle_network_message(self, message):
        """处理接收到的网络消息"""
        if message['type'] == 'chat':
            sender = message['sender'][0] if isinstance(message['sender'], tuple) else str(message['sender'])
            timestamp = datetime.fromisoformat(message['timestamp']).strftime('%H:%M:%S')
            self.message_history.append(f"[{sender}] {timestamp}: {message['content']}")
    
    def restart_network(self):
        """重启网络服务"""
        try:
            port = int(self.port_input.text())
            self.network.stop()
            self.network.wait()
            self.network = NetworkCollaboration(port)
            self.network.message_received.connect(self.handle_network_message)
            self.network.start()
            self.network_status_label.setText("运行中")
            self.statusBar().showMessage("网络服务已重启")
        except Exception as e:
            self.network_status_label.setText("错误")
            self.statusBar().showMessage(f"网络重启错误: {str(e)}")
    
    def import_historical_data(self):
        """导入历史数据"""
        file_path, _ = QFileDialog.getOpenFileName(self, "导入历史数据", "", "CSV文件 (*.csv)")
        if file_path:
            try:
                new_data = pd.read_csv(file_path)
                required_cols = ['troops', 'front_width', 'depth', 'firepower', 'terrain_factor', 'effectiveness']
                
                if all(col in new_data.columns for col in required_cols):
                    self.historical_data = pd.concat([self.historical_data, new_data[required_cols]], ignore_index=True)
                    self.update_history_table()
                    self.ai_predict_btn.setEnabled(len(self.historical_data) >= 10)
                    self.ai_optimize_btn.setEnabled(len(self.historical_data) >= 10)
                    QMessageBox.information(self, "成功", "历史数据导入成功")
                    self.statusBar().showMessage("历史数据导入成功")
                else:
                    QMessageBox.warning(self, "错误", "CSV文件缺少必要的列")
                    self.statusBar().showMessage("CSV文件缺少必要的列")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导入失败: {str(e)}")
                self.statusBar().showMessage(f"导入失败: {str(e)}")
    
    def export_historical_data(self):
        """导出历史数据"""
        if self.historical_data.empty:
            QMessageBox.warning(self, "警告", "没有历史数据可导出")
            self.statusBar().showMessage("没有历史数据可导出")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(self, "导出历史数据", "", "CSV文件 (*.csv)")
        if file_path:
            try:
                self.historical_data.to_csv(file_path, index=False)
                QMessageBox.information(self, "成功", "历史数据导出成功")
                self.statusBar().showMessage("历史数据导出成功")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导出失败: {str(e)}")
                self.statusBar().showMessage(f"导出失败: {str(e)}")
    
    def clear_historical_data(self):
        """清除历史数据"""
        if QMessageBox.question(self, "确认", "确定要清除所有历史数据吗?") == QMessageBox.Yes:
            self.historical_data = pd.DataFrame(columns=[
                'troops', 'front_width', 'depth', 'firepower', 'terrain_factor', 'effectiveness'
            ])
            self.update_history_table()
            self.ai_predict_btn.setEnabled(False)
            self.ai_optimize_btn.setEnabled(False)
            self.statusBar().showMessage("历史数据已清除")
    
    def plot_historical_trend(self):
        """绘制历史趋势图"""
        if len(self.historical_data) < 2:
            QMessageBox.warning(self, "警告", "需要至少2条历史数据才能绘制趋势图")
            return
        
        # 创建趋势图
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # 绘制效能趋势
        ax.plot(self.historical_data.index, self.historical_data['effectiveness'], 
                'b-', label='效能指标')
        
        # 添加趋势线
        z = np.polyfit(self.historical_data.index, self.historical_data['effectiveness'], 1)
        p = np.poly1d(z)
        ax.plot(self.historical_data.index, p(self.historical_data.index), 
                "r--", alpha=0.5, label='趋势线')
        
        ax.set_xlabel('数据点')
        ax.set_ylabel('效能指标')
        ax.set_title('历史效能趋势')
        ax.legend()
        ax.grid(True)
        
        plt.tight_layout()
        plt.show()
    
    def run_statistical_analysis(self):
        """执行统计分析"""
        if len(self.historical_data) < 3:
            QMessageBox.warning(self, "警告", "需要至少3条历史数据才能进行统计分析")
            return
        
        analysis_type = self.stats_type_combo.currentText()
        self.stats_results.clear()
        
        if analysis_type == "相关性分析":
            self.correlation_analysis()
        elif analysis_type == "回归分析":
            self.regression_analysis()
        elif analysis_type == "假设检验":
            self.hypothesis_testing()
    
    def correlation_analysis(self):
        """相关性分析"""
        correlation_matrix = self.historical_data.corr()
        effectiveness_corr = correlation_matrix['effectiveness'].sort_values(ascending=False)
        
        self.stats_results.append("=== 相关性分析 ===")
        self.stats_results.append("各参数与效能指标的相关性:")
        
        for param, corr in effectiveness_corr.items():
            if param != 'effectiveness':
                self.stats_results.append(f"{param}: {corr:.4f}")
        
        # 解释相关性
        self.stats_results.append("\n相关性解释:")
        for param, corr in effectiveness_corr.items():
            if param != 'effectiveness':
                if abs(corr) >= 0.7:
                    strength = "强"
                elif abs(corr) >= 0.5:
                    strength = "中等"
                elif abs(corr) >= 0.3:
                    strength = "弱"
                else:
                    strength = "极弱"
                
                direction = "正" if corr > 0 else "负"
                self.stats_results.append(f"{param}与效能呈{strength}{direction}相关")
    
    def regression_analysis(self):
        """回归分析"""
        try:
            # 准备数据
            X = self.historical_data[['troops', 'front_width', 'depth', 'firepower', 'terrain_factor']]
            y = self.historical_data['effectiveness']
            
            # 添加常数项
            X = sm.add_constant(X)
            
            # 执行回归分析
            model = sm.OLS(y, X).fit()
            
            self.stats_results.append("=== 回归分析 ===")
            self.stats_results.append(str(model.summary()))
            
        except Exception as e:
            self.stats_results.append(f"回归分析错误: {str(e)}")
    
    def hypothesis_testing(self):
        """假设检验"""
        # 检查地形因子对效能的影响
        terrain_high = self.historical_data[self.historical_data['terrain_factor'] > 0.5]['effectiveness']
        terrain_low = self.historical_data[self.historical_data['terrain_factor'] <= 0.5]['effectiveness']
        
        if len(terrain_high) > 1 and len(terrain_low) > 1:
            t_stat, p_value = stats.ttest_ind(terrain_high, terrain_low)
            
            self.stats_results.append("=== 假设检验 ===")
            self.stats_results.append("零假设: 高地形因子和低地形因子对效能的影响无显著差异")
            self.stats_results.append(f"t统计量: {t_stat:.4f}")
            self.stats_results.append(f"p值: {p_value:.4f}")
            
            if p_value < 0.05:
                self.stats_results.append("结论: 拒绝零假设，地形因子对效能有显著影响")
            else:
                self.stats_results.append("结论: 无法拒绝零假设，地形因子对效能无显著影响")
        else:
            self.stats_results.append("数据不足，无法进行假设检验")
    
    def save_config(self):
        """保存当前配置"""
        config = {
            'total_troops': self.total_troops_spin.value(),
            'structure_level': self.structure_combo.currentText(),
            'front_width': self.front_width_spin.value(),
            'depth': self.depth_spin.value(),
            'firepower': self.firepower_spin.value(),
            'terrain_type': self.terrain_combo.currentText(),
            'terrain_factor': self.terrain_factor_spin.value()
        }
        
        file_path, _ = QFileDialog.getSaveFileName(self, "保存配置", "", "JSON文件 (*.json)")
        if file_path:
            try:
                with open(file_path, 'w') as f:
                    json.dump(config, f)
                self.statusBar().showMessage("配置保存成功")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"保存配置失败: {str(e)}")
                self.statusBar().showMessage(f"保存配置失败: {str(e)}")
    
    def load_config(self):
        """加载配置"""
        file_path, _ = QFileDialog.getOpenFileName(self, "加载配置", "", "JSON文件 (*.json)")
        if file_path:
            try:
                with open(file_path, 'r') as f:
                    config = json.load(f)
                
                self.total_troops_spin.setValue(config.get('total_troops', 1000))
                self.structure_combo.setCurrentText(config.get('structure_level', '班'))
                self.front_width_spin.setValue(config.get('front_width', 50))
                self.depth_spin.setValue(config.get('depth', 100))
                self.firepower_spin.setValue(config.get('firepower', 10))
                self.terrain_combo.setCurrentText(config.get('terrain_type', '平原'))
                self.terrain_factor_spin.setValue(config.get('terrain_factor', 0.5))
                
                self.statusBar().showMessage("配置加载成功")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"加载配置失败: {str(e)}")
                self.statusBar().showMessage(f"加载配置失败: {str(e)}")
    
    def closeEvent(self, event):
        """应用关闭事件"""
        self.network.stop()
        self.network.wait()
        event.accept()


class ThreeThreeSystemAnalyzer:
    """三三制分析核心类"""
    
    def __init__(self):
        self.squads = 0  # 班数量
        self.platoons = 0  # 排数量
        self.companies = 0  # 连数量
        self.battalions = 0  # 营数量
        
    def calculate_units(self, total_troops, structure_level):
        """根据总兵力和结构层级计算各单位数量"""
        if structure_level == "squad":
            self.squads = max(0, total_troops // 9)
            self.platoons = max(0, self.squads // 3)
            self.companies = max(0, self.platoons // 3)
            self.battalions = max(0, self.companies // 3)
        elif structure_level == "platoon":
            self.platoons = max(0, total_troops // 27)
            self.squads = max(0, self.platoons * 3)
            self.companies = max(0, self.platoons // 3)
            self.battalions = max(0, self.companies // 3)
        elif structure_level == "company":
            self.companies = max(0, total_troops // 81)
            self.platoons = max(0, self.companies * 3)
            self.squads = max(0, self.platoons * 3)
            self.battalions = max(0, self.companies // 3)
        elif structure_level == "battalion":
            self.battalions = max(0, total_troops // 243)
            self.companies = max(0, self.battalions * 3)
            self.platoons = max(0, self.companies * 3)
            self.squads = max(0, self.platoons * 3)
        else:
            # 默认按班计算
            self.squads = max(0, total_troops // 9)
            self.platoons = max(0, self.squads // 3)
            self.companies = max(0, self.platoons // 3)
            self.battalions = max(0, self.companies // 3)
            
        return {
            "squads": self.squads,
            "platoons": self.platoons,
            "companies": self.companies,
            "battalions": self.battalions
        }
    
    def calculate_coverage(self, front_width_per_squad, depth_per_squad):
        """计算部队的正面宽度和纵深"""
        return {
            "front_width": self.squads * front_width_per_squad,
            "depth": self.squads * depth_per_squad
        }
    
    def calculate_firepower(self, firepower_per_squad):
        """计算总火力和火力密度"""
        total_firepower = self.squads * firepower_per_squad
        return {
            "total_firepower": total_firepower,
            "firepower_density": total_firepower / self.squads if self.squads > 0 else 0
        }


# 添加缺失的导入
try:
    from scipy.interpolate import griddata
    import statsmodels.api as sm
except ImportError:
    print("警告: 缺少scipy或statsmodels库，部分功能可能无法使用")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # 设置应用字体
    font = QFont("Microsoft YaHei", 10)
    app.setFont(font)
    
    window = RevolutionaryThreeThreeAnalysisApp()
    window.show()
    
    sys.exit(app.exec_())