import sys
import numpy as np
import matplotlib

matplotlib.rc("font", family='Microsoft YaHei')
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.animation import FuncAnimation
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter, 
    QGroupBox, QLabel, QPushButton, QSlider, QComboBox, QListWidget, 
    QTableWidget, QTableWidgetItem, QTabWidget, QTextEdit, QCheckBox, 
    QDoubleSpinBox, QSpinBox, QFormLayout, QStyleFactory
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QPalette, QColor, QIcon
import networkx as nx

class WarringStatesSimulator(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # 设置主窗口属性
        self.setWindowTitle("战国合纵连横策略模拟系统")
        self.setGeometry(100, 50, 1600, 900)
        
        # 设置应用样式
        self.setStyle(QStyleFactory.create('Fusion'))
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(250, 245, 230))
        palette.setColor(QPalette.WindowText, QColor(90, 45, 0))
        palette.setColor(QPalette.Base, QColor(255, 250, 240))
        palette.setColor(QPalette.AlternateBase, QColor(250, 240, 230))
        palette.setColor(QPalette.ToolTipBase, QColor(139, 69, 19))
        palette.setColor(QPalette.ToolTipText, Qt.white)
        palette.setColor(QPalette.Text, QColor(101, 67, 33))
        palette.setColor(QPalette.Button, QColor(210, 180, 140))
        palette.setColor(QPalette.ButtonText, QColor(101, 67, 33))
        palette.setColor(QPalette.Highlight, QColor(160, 82, 45).lighter())
        palette.setColor(QPalette.HighlightedText, Qt.white)
        self.setPalette(palette)
        
        # 初始化数据
        self.init_data()
        
        # 创建主控件
        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)
        self.main_layout = QHBoxLayout(self.main_widget)
        
        # 创建左侧控制面板
        self.create_control_panel()
        
        # 创建右侧可视化区域
        self.create_visualization_area()
        
        # 初始化动画
        self.init_animation()
        
        # 状态栏
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("战国合纵连横策略模拟系统已就绪")
        
        # 加载初始状态
        self.update_display(-350)
        
    def init_data(self):
        # 战国七雄数据
        self.states = ['秦', '楚', '齐', '燕', '赵', '魏', '韩']
        self.colors = {
            '秦': '#8B0000',  # 深红
            '楚': '#006400',  # 深绿
            '齐': '#FF8C00',  # 橙
            '燕': '#4B0082',  # 紫
            '赵': '#00008B',  # 深蓝
            '魏': '#8B4513',  # 棕
            '韩': '#2F4F4F'   # 暗灰
        }
        
        # 国家地理位置坐标
        self.positions = {
            '秦': np.array([0.2, 0.5]),
            '楚': np.array([0.5, 0.1]),
            '齐': np.array([0.8, 0.7]),
            '燕': np.array([0.7, 0.9]),
            '赵': np.array([0.5, 0.7]),
            '魏': np.array([0.4, 0.5]),
            '韩': np.array([0.3, 0.6])
        }
        
        # 初始国力值
        self.state_power = {
            '秦': 80,
            '楚': 70,
            '齐': 75,
            '燕': 60,
            '赵': 65,
            '魏': 65,
            '韩': 55
        }
        
        # 国家关系矩阵 (初始值)
        self.relations = np.array([
            [0, -0.2, -0.2, -0.1, -0.1, -0.3, -0.3],  # 秦
            [-0.3, 0, -0.1, -0.1, -0.1, -0.2, -0.1],  # 楚
            [-0.2, -0.1, 0, -0.2, -0.1, -0.1, -0.1],  # 齐
            [-0.1, -0.1, -0.2, 0, -0.3, -0.1, -0.1],  # 燕
            [-0.3, -0.1, -0.1, -0.3, 0, -0.2, -0.1],  # 赵
            [-0.4, -0.2, -0.1, -0.1, -0.2, 0, -0.3],  # 魏
            [-0.4, -0.1, -0.1, -0.1, -0.1, -0.3, 0]   # 韩
        ])
        
        # 历史事件时间线
        self.events = [
            {"year": -350, "event": "商鞅变法", "effect": {"秦": 15}, "type": "改革", "duration": 10},
            {"year": -334, "event": "苏秦合纵", "effect": {"楚": 5, "齐": 5, "燕": 5, "赵": 5, "魏": 5, "韩": 5}, 
             "type": "外交", "duration": 5},
            {"year": -328, "event": "张仪连横", "effect": {"秦": 10, "魏": -5, "韩": -5}, "type": "外交", "duration": 5},
            {"year": -318, "event": "五国伐秦", "effect": {"秦": -10, "楚": -3, "齐": -3, "赵": -3, "魏": -3, "韩": -3}, 
             "type": "战争", "duration": 2},
            {"year": -312, "event": "秦楚之战", "effect": {"秦": 5, "楚": -15}, "type": "战争", "duration": 3},
            {"year": -284, "event": "乐毅伐齐", "effect": {"齐": -25, "燕": 10}, "type": "战争", "duration": 4},
            {"year": -278, "event": "白起破郢", "effect": {"秦": 10, "楚": -20}, "type": "战争", "duration": 2},
            {"year": -260, "event": "长平之战", "effect": {"秦": 15, "赵": -25}, "type": "战争", "duration": 3},
            {"year": -256, "event": "秦灭西周", "effect": {"秦": 10}, "type": "战争", "duration": 1},
            {"year": -230, "event": "秦灭韩", "effect": {"秦": 20, "韩": -100}, "type": "战争", "duration": 1}
        ]
        
        # 联盟关系变化
        self.alliances = [
            {"year": -350, "vertical": [], "horizontal": []},
            {"year": -334, "vertical": ["楚", "齐", "燕", "赵", "魏", "韩"], "horizontal": ["秦"]},
            {"year": -328, "vertical": ["齐", "燕", "赵"], "horizontal": ["秦", "魏", "韩"]},
            {"year": -312, "vertical": ["齐", "燕", "赵", "魏", "韩"], "horizontal": ["秦", "楚"]},
            {"year": -284, "vertical": ["秦", "赵", "魏", "韩", "燕"], "horizontal": ["齐", "楚"]},
            {"year": -260, "vertical": ["齐", "楚", "燕"], "horizontal": ["秦", "赵", "魏", "韩"]},
            {"year": -230, "vertical": [], "horizontal": ["秦"]}
        ]
        
        # 当前年份
        self.current_year = -350
        self.min_year = -350
        self.max_year = -230
        self.simulation_speed = 500  # ms
        self.is_playing = False
        
        # 历史记录
        self.history = {
            'year': [-350],
            'power': {state: [self.state_power[state]] for state in self.states},
            'alliances': [{"vertical": [], "horizontal": []}],
            'events': []
        }
    
    def create_control_panel(self):
        """创建左侧控制面板"""
        control_panel = QGroupBox("控制面板")
        control_layout = QVBoxLayout()
        
        # 时间控制部分
        time_group = QGroupBox("时间控制")
        time_layout = QVBoxLayout()
        
        # 年份显示
        self.year_label = QLabel(f"年份: {abs(self.current_year)}年 公元前")
        self.year_label.setFont(QFont("Arial", 12, QFont.Bold))
        time_layout.addWidget(self.year_label)
        
        # 时间滑块
        self.time_slider = QSlider(Qt.Horizontal)
        self.time_slider.setRange(self.min_year, self.max_year)
        self.time_slider.setValue(self.current_year)
        self.time_slider.setTickInterval(10)
        self.time_slider.setTickPosition(QSlider.TicksBelow)
        self.time_slider.valueChanged.connect(self.slider_changed)
        time_layout.addWidget(self.time_slider)
        
        # 播放控制按钮
        btn_layout = QHBoxLayout()
        self.play_btn = QPushButton("播放")
        self.play_btn.setIcon(QIcon.fromTheme("media-playback-start"))
        self.play_btn.clicked.connect(self.toggle_play)
        btn_layout.addWidget(self.play_btn)
        
        self.pause_btn = QPushButton("暂停")
        self.pause_btn.setIcon(QIcon.fromTheme("media-playback-pause"))
        self.pause_btn.clicked.connect(self.pause_simulation)
        btn_layout.addWidget(self.pause_btn)
        
        self.reset_btn = QPushButton("重置")
        self.reset_btn.setIcon(QIcon.fromTheme("view-refresh"))
        self.reset_btn.clicked.connect(self.reset_simulation)
        btn_layout.addWidget(self.reset_btn)
        time_layout.addLayout(btn_layout)
        
        # 速度控制
        speed_layout = QHBoxLayout()
        speed_layout.addWidget(QLabel("速度:"))
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setRange(100, 2000)
        self.speed_slider.setValue(self.simulation_speed)
        self.speed_slider.setTickInterval(100)
        self.speed_slider.valueChanged.connect(self.speed_changed)
        speed_layout.addWidget(self.speed_slider)
        time_layout.addLayout(speed_layout)
        
        time_group.setLayout(time_layout)
        control_layout.addWidget(time_group)
        
        # 策略模拟部分
        strategy_group = QGroupBox("策略模拟")
        strategy_layout = QVBoxLayout()
        
        # 国家选择
        form_layout = QFormLayout()
        self.state_combo = QComboBox()
        self.state_combo.addItems(self.states)
        form_layout.addRow("选择国家:", self.state_combo)
        
        # 策略选择
        self.strategy_combo = QComboBox()
        self.strategy_combo.addItems(["合纵", "连横", "改革", "战争", "中立"])
        form_layout.addRow("选择策略:", self.strategy_combo)
        
        # 目标国家选择
        self.target_combo = QComboBox()
        self.target_combo.addItems(["无"] + self.states)
        form_layout.addRow("目标国家:", self.target_combo)
        
        # 策略强度
        self.strength_spin = QDoubleSpinBox()
        self.strength_spin.setRange(1, 50)
        self.strength_spin.setValue(10)
        self.strength_spin.setSingleStep(1)
        form_layout.addRow("策略强度:", self.strength_spin)
        
        # 策略持续时间
        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(1, 20)
        self.duration_spin.setValue(5)
        form_layout.addRow("持续时间(年):", self.duration_spin)
        
        # 应用策略按钮
        self.apply_strategy_btn = QPushButton("应用策略")
        self.apply_strategy_btn.clicked.connect(self.apply_strategy)
        form_layout.addRow(self.apply_strategy_btn)
        
        strategy_layout.addLayout(form_layout)
        
        # 关系矩阵
        self.relation_table = QTableWidget(len(self.states), len(self.states))
        self.relation_table.setHorizontalHeaderLabels(self.states)
        self.relation_table.setVerticalHeaderLabels(self.states)
        self.relation_table.setMaximumHeight(200)
        self.update_relation_table()
        strategy_layout.addWidget(QLabel("国家关系矩阵:"))
        strategy_layout.addWidget(self.relation_table)
        
        strategy_group.setLayout(strategy_layout)
        control_layout.addWidget(strategy_group)
        
        # 事件日志
        event_group = QGroupBox("事件日志")
        event_layout = QVBoxLayout()
        self.event_list = QListWidget()
        self.event_list.setMaximumHeight(200)
        event_layout.addWidget(self.event_list)
        event_group.setLayout(event_layout)
        control_layout.addWidget(event_group)
        
        control_panel.setLayout(control_layout)
        control_panel.setMaximumWidth(400)
        self.main_layout.addWidget(control_panel)
    
    def create_visualization_area(self):
        """创建右侧可视化区域"""
        # 使用分割器创建多面板布局
        splitter = QSplitter(Qt.Vertical)
        
        # 第一行：地图和实力图表
        top_splitter = QSplitter(Qt.Horizontal)
        
        # 地图可视化
        map_group = QGroupBox("战国地图与联盟关系")
        map_layout = QVBoxLayout()
        self.map_figure = Figure(figsize=(8, 6), facecolor='#f5f5dc')
        self.map_canvas = FigureCanvas(self.map_figure)
        map_layout.addWidget(self.map_canvas)
        map_group.setLayout(map_layout)
        top_splitter.addWidget(map_group)
        
        # 实力图表
        power_group = QGroupBox("国家实力变化")
        power_layout = QVBoxLayout()
        self.power_figure = Figure(figsize=(6, 6), facecolor='#f5f5dc')
        self.power_canvas = FigureCanvas(self.power_figure)
        power_layout.addWidget(self.power_canvas)
        power_group.setLayout(power_layout)
        top_splitter.addWidget(power_group)
        
        top_splitter.setSizes([600, 400])
        splitter.addWidget(top_splitter)
        
        # 第二行：国家信息和策略分析
        bottom_splitter = QSplitter(Qt.Horizontal)
        
        # 国家信息
        state_info_group = QGroupBox("国家详细信息")
        state_info_layout = QVBoxLayout()
        
        self.state_info_label = QLabel("请选择一个国家查看详细信息")
        self.state_info_label.setFont(QFont("Arial", 10))
        state_info_layout.addWidget(self.state_info_label)
        
        # 国家属性表格
        self.state_table = QTableWidget(7, 2)
        self.state_table.setHorizontalHeaderLabels(["属性", "值"])
        self.state_table.setVerticalHeaderLabels(["国家", "国力", "地理位置", "威胁等级", "外交策略", "军事力量", "经济实力"])
        self.state_table.setMaximumHeight(200)
        state_info_layout.addWidget(self.state_table)
        
        # 策略分析
        self.strategy_text = QTextEdit()
        self.strategy_text.setReadOnly(True)
        self.strategy_text.setFont(QFont("Arial", 10))
        self.strategy_text.setHtml("<center><b>策略分析</b></center><hr>选择国家查看策略建议")
        state_info_layout.addWidget(self.strategy_text)
        
        state_info_group.setLayout(state_info_layout)
        bottom_splitter.addWidget(state_info_group)
        
        # 联盟分析
        alliance_group = QGroupBox("联盟分析")
        alliance_layout = QVBoxLayout()
        
        # 当前联盟状态
        self.alliance_label = QLabel("当前联盟状态")
        self.alliance_label.setFont(QFont("Arial", 10, QFont.Bold))
        alliance_layout.addWidget(self.alliance_label)
        
        # 联盟力量对比
        self.alliance_text = QTextEdit()
        self.alliance_text.setReadOnly(True)
        self.alliance_text.setFont(QFont("Arial", 10))
        self.alliance_text.setHtml("<center><b>联盟力量对比</b></center><hr>未检测到有效联盟")
        alliance_layout.addWidget(self.alliance_text)
        
        # 联盟稳定性分析
        self.stability_text = QTextEdit()
        self.stability_text.setReadOnly(True)
        self.stability_text.setFont(QFont("Arial", 10))
        self.stability_text.setHtml("<center><b>联盟稳定性分析</b></center><hr>无联盟数据")
        alliance_layout.addWidget(self.stability_text)
        
        alliance_group.setLayout(alliance_layout)
        bottom_splitter.addWidget(alliance_group)
        
        bottom_splitter.setSizes([500, 500])
        splitter.addWidget(bottom_splitter)
        
        splitter.setSizes([600, 300])
        self.main_layout.addWidget(splitter)
    
    def init_animation(self):
        """初始化地图动画"""
        # 设置地图图形
        self.map_ax = self.map_figure.add_subplot(111)
        self.map_ax.set_title('战国七雄势力与联盟变化', fontsize=14)
        self.map_ax.set_xlim(0, 1)
        self.map_ax.set_ylim(0, 1)
        self.map_ax.set_xticks([])
        self.map_ax.set_yticks([])
        
        # 绘制河流
        river_x = np.linspace(0.3, 0.8, 100)
        river_y = 0.3 + 0.1 * np.sin(10 * river_x)
        self.map_ax.plot(river_x, river_y, 'b-', alpha=0.3, linewidth=3)
        
        # 绘制山脉
        mountain_x = [0.15, 0.25, 0.35, 0.45, 0.55]
        mountain_y = [0.85, 0.75, 0.8, 0.7, 0.78]
        for x, y in zip(mountain_x, mountain_y):
            self.map_ax.plot([x, x+0.05], [y, y+0.05], 'k-', linewidth=1)
            self.map_ax.plot([x+0.05, x+0.1], [y+0.05, y], 'k-', linewidth=1)
        
        # 添加地图标签
        self.map_ax.text(0.1, 0.9, '函谷关', fontsize=10, color='#8B4513', 
                        bbox=dict(facecolor='wheat', alpha=0.7, edgecolor='none'))
        self.map_ax.text(0.65, 0.15, '长江', fontsize=10, color='blue', rotation=20,
                        bbox=dict(facecolor='lightblue', alpha=0.3, edgecolor='none'))
        self.map_ax.text(0.45, 0.8, '太行山', fontsize=10, color='#2F4F4F', rotation=45,
                        bbox=dict(facecolor='#D2B48C', alpha=0.5, edgecolor='none'))
        
        # 初始化国家节点
        self.state_nodes = {}
        for state in self.states:
            x, y = self.positions[state]
            node = self.map_ax.scatter(x, y, s=self.state_power[state]*20, 
                                     c=self.colors[state], alpha=0.9, 
                                     edgecolors='k', linewidths=1.5)
            self.state_nodes[state] = node
            self.map_ax.text(x, y+0.03, state, fontsize=14, fontweight='bold', 
                           ha='center', va='center', color='black')
        
        # 初始化联盟连线
        self.vertical_lines = []
        self.horizontal_lines = []
        
        # 设置实力图表
        self.power_ax = self.power_figure.add_subplot(111)
        self.power_ax.set_title('国家实力变化', fontsize=14)
        self.power_ax.set_xlabel('年份 (公元前)', fontsize=10)
        self.power_ax.set_ylabel('国力值', fontsize=10)
        self.power_ax.grid(True, linestyle='--', alpha=0.3)
        
        # 绘制实力曲线
        self.power_lines = {}
        for state in self.states:
            line, = self.power_ax.plot([], [], label=state, 
                                     color=self.colors[state], linewidth=2)
            self.power_lines[state] = line
        self.power_ax.legend(loc='upper left', fontsize=9)
        
        # 设置定时器用于动画
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.advance_year)
    
    def update_display(self, year):
        """更新所有显示元素"""
        # 确保年份在有效范围内
        year = max(self.min_year, min(year, self.max_year))
        
        # 添加缺失年份的历史记录
        if year not in self.history['year']:
            # 找到最近的历史年份
            prev_year = max(y for y in self.history['year'] if y < year)
            prev_idx = self.history['year'].index(prev_year)
            
            # 复制前一年的数据
            for state in self.states:
                prev_power = self.history['power'][state][prev_idx]
                self.history['power'][state].append(prev_power)
            
            # 添加新年份的记录
            self.history['year'].append(year)
            self.history['alliances'].append(self.get_current_alliance(year))
            self.history['events'].append([])
        
        # 更新当前年份
        self.current_year = year
        self.year_label.setText(f"年份: {abs(year)}年 公元前")
        self.time_slider.setValue(year)
        
        # 更新地图
        self.update_map(year)
        
        # 更新实力图表
        self.update_power_chart()
        
        # 更新关系表
        self.update_relation_table()
        
        # 更新事件列表
        self.update_event_list()
        
        # 更新国家信息
        self.update_state_info()
        
        # 更新联盟分析
        self.update_alliance_analysis()
    
    def get_current_alliance(self, year):
        """获取指定年份的联盟配置"""
        current_alliance = {"vertical": [], "horizontal": []}
        for alliance in reversed(self.alliances):
            if alliance['year'] <= year:
                current_alliance = alliance
                break
        return current_alliance
    def update_map(self, year):
        """更新地图显示"""
        # 清除旧的联盟连线
        for line in self.vertical_lines:
            line.remove()
        self.vertical_lines.clear()
        
        for line in self.horizontal_lines:
            line.remove()
        self.horizontal_lines.clear()
        
        # 更新国家节点大小
        for state in self.states:
            power = self.history['power'][state][self.history['year'].index(year)]
            self.state_nodes[state].set_sizes([power * 20])
        
        # 获取当前联盟
        current_alliance = {"vertical": [], "horizontal": []}
        for alliance in self.alliances:
            if alliance['year'] >= year:
                current_alliance = alliance
                break
        
        # 绘制新的合纵连线 (红色)
        if current_alliance['vertical']:
            for i in range(len(current_alliance['vertical'])):
                for j in range(i+1, len(current_alliance['vertical'])):
                    state1 = current_alliance['vertical'][i]
                    state2 = current_alliance['vertical'][j]
                    x1, y1 = self.positions[state1]
                    x2, y2 = self.positions[state2]
                    line = self.map_ax.plot([x1, x2], [y1, y2], 'r-', alpha=0.4, linewidth=2)[0]
                    self.vertical_lines.append(line)
        
        # 绘制新的连横连线 (蓝色)
        if current_alliance['horizontal']:
            for i in range(len(current_alliance['horizontal'])):
                for j in range(i+1, len(current_alliance['horizontal'])):
                    state1 = current_alliance['horizontal'][i]
                    state2 = current_alliance['horizontal'][j]
                    x1, y1 = self.positions[state1]
                    x2, y2 = self.positions[state2]
                    line = self.map_ax.plot([x1, x2], [y1, y2], 'b--', alpha=0.6, linewidth=2)[0]
                    self.horizontal_lines.append(line)
        
        # 重绘地图
        self.map_canvas.draw()
    
    def update_power_chart(self):
        """更新实力图表"""
        years = self.history['year']
        for state in self.states:
            powers = self.history['power'][state][:len(years)]
            self.power_lines[state].set_data(years, powers)
        
        # 调整图表范围
        self.power_ax.set_xlim(min(years), max(years))
        max_power = max(max(self.history['power'][state]) for state in self.states)
        self.power_ax.set_ylim(0, max(120, max_power * 1.1))
        
        # 添加秦国统一提示
        if self.current_year <= -230:
            self.power_ax.text(-240, 110, "秦国灭韩，统一进程开始", 
                             fontsize=12, color='red', ha='center')
        
        self.power_canvas.draw()
    
    def update_relation_table(self):
        """更新关系矩阵表"""
        for i in range(len(self.states)):
            for j in range(len(self.states)):
                value = self.relations[i][j]
                item = QTableWidgetItem(f"{value:.2f}")
                
                # 根据值设置背景色
                if value > 0.3:
                    item.setBackground(QColor(144, 238, 144))  # 浅绿
                elif value > 0.1:
                    item.setBackground(QColor(152, 251, 152))  # 更浅绿
                elif value < -0.3:
                    item.setBackground(QColor(255, 99, 71))    # 番茄红
                elif value < -0.1:
                    item.setBackground(QColor(255, 160, 122))  # 浅鲑鱼色
                else:
                    item.setBackground(QColor(240, 248, 255))  # 爱丽丝蓝
                
                self.relation_table.setItem(i, j, item)
    
    def update_event_list(self):
        """更新事件列表"""
        self.event_list.clear()
        for event in self.events:
            if event['year'] == self.current_year:
                event_text = f"{abs(event['year'])}年: {event['event']} ({event['type']})"
                self.event_list.addItem(event_text)
    
    def update_state_info(self):
        """更新国家详细信息"""
        selected_state = self.state_combo.currentText()
        power = self.history['power'][selected_state][self.history['year'].index(self.current_year)]
        
        # 更新标签
        self.state_info_label.setText(f"{selected_state}国 ({abs(self.current_year)}年 公元前)")
        
        # 更新表格
        self.state_table.setItem(0, 1, QTableWidgetItem(selected_state))
        self.state_table.setItem(1, 1, QTableWidgetItem(f"{power:.1f}"))
        self.state_table.setItem(2, 1, QTableWidgetItem(self.get_geography_desc(selected_state)))
        self.state_table.setItem(3, 1, QTableWidgetItem(self.get_threat_level(selected_state)))
        self.state_table.setItem(4, 1, QTableWidgetItem(self.get_diplomatic_strategy(selected_state)))
        self.state_table.setItem(5, 1, QTableWidgetItem(self.get_military_strength(selected_state, power)))
        self.state_table.setItem(6, 1, QTableWidgetItem(self.get_economic_strength(selected_state, power)))
        
        # 更新策略分析
        self.strategy_text.setHtml(self.generate_strategy_analysis(selected_state))
    
    def get_geography_desc(self, state):
        """获取地理位置描述"""
        descriptions = {
            '秦': "西据函谷关，易守难攻，关中沃野千里",
            '楚': "地广人稀，长江流域，水网纵横",
            '齐': "东临大海，鱼盐之利，经济富庶",
            '燕': "北疆苦寒之地，易守难攻，但经济较弱",
            '赵': "北有胡骑之利，南有中原之便，四战之地",
            '魏': "中原腹地，四通八达，四战之地",
            '韩': "地处中原，土地狭小，强国环伺"
        }
        return descriptions.get(state, "未知")
    
    def get_threat_level(self, state):
        """获取威胁等级"""
        # 计算秦国与其他国家的关系平均值作为威胁参考
        qin_index = self.states.index('秦')
        threat_level = -np.mean([self.relations[i][qin_index] for i, s in enumerate(self.states) if s != '秦'])
        
        # 根据国家调整
        if state == '秦':
            return "低 (霸主地位)"
        
        levels = {
            '楚': threat_level * 0.8,
            '齐': threat_level * 0.9,
            '燕': threat_level * 0.6,
            '赵': threat_level * 1.0,
            '魏': threat_level * 1.2,
            '韩': threat_level * 1.3
        }
        
        level_val = levels.get(state, threat_level)
        
        if level_val > 0.8:
            return "极高"
        elif level_val > 0.6:
            return "高"
        elif level_val > 0.4:
            return "中"
        else:
            return "低"
    
    def get_diplomatic_strategy(self, state):
        """获取外交策略描述"""
        strategies = {
            '秦': "连横策略：分化六国，各个击破",
            '楚': "摇摆策略：时而抗秦，时而亲秦",
            '齐': "自保策略：避免直接冲突，保存实力",
            '燕': "依附策略：依附强国以求自保",
            '赵': "抗秦策略：坚决抵抗秦国扩张",
            '魏': "实用主义：根据利益调整外交策略",
            '韩': "亲秦策略：屈服于秦国以求生存"
        }
        return strategies.get(state, "未知")
    
    def get_military_strength(self, state, power):
        """获取军事实力描述"""
        strength = power * 0.8 if state in ['秦', '楚'] else power * 0.7
        
        if strength > 70:
            return f"极强 ({strength:.1f})"
        elif strength > 50:
            return f"强 ({strength:.1f})"
        elif strength > 30:
            return f"中等 ({strength:.1f})"
        else:
            return f"弱 ({strength:.1f})"
    
    def get_economic_strength(self, state, power):
        """获取经济实力描述"""
        strength = power * 1.2 if state == '齐' else power * 0.9
        
        if strength > 80:
            return f"极强 ({strength:.1f})"
        elif strength > 60:
            return f"强 ({strength:.1f})"
        elif strength > 40:
            return f"中等 ({strength:.1f})"
        else:
            return f"弱 ({strength:.1f})"
    
    def generate_strategy_analysis(self, state):
        """生成策略分析HTML"""
        analysis = f"<h2 align='center'>{state}国策略分析</h2><hr>"
        
        # 当前形势分析
        analysis += "<h3>当前形势分析:</h3>"
        analysis += f"<p>· 国力排名: {self.get_power_rank(state)}/7</p>"
        analysis += f"<p>· 主要威胁: {self.get_main_threat(state)}</p>"
        analysis += f"<p>· 潜在盟友: {self.get_potential_ally(state)}</p>"
        
        # 策略建议
        analysis += "<h3>策略建议:</h3>"
        
        if state == '秦':
            analysis += "<p>1. <b>连横策略</b>: 继续分化六国联盟，挑拨各国关系</p>"
            analysis += "<p>2. <b>远交近攻</b>: 与远国交好，集中力量进攻邻国</p>"
            analysis += "<p>3. <b>军事改革</b>: 进一步提升军队战斗力，发展新兵器</p>"
        else:
            analysis += "<p>1. <b>合纵策略</b>: 联合其他国家共同抗秦</p>"
            
            if state in ['楚', '齐']:
                analysis += "<p>2. <b>发展经济</b>: 增强国力，为长期对抗做准备</p>"
            elif state in ['赵', '魏']:
                analysis += "<p>2. <b>军事改革</b>: 强化军队战斗力，建立精锐部队</p>"
            else:
                analysis += "<p>2. <b>外交斡旋</b>: 在强国间周旋以求生存空间</p>"
            
            analysis += "<p>3. <b>改善关系</b>: 改善与潜在盟友的关系，增强互信</p>"
        
        # 风险提示
        analysis += "<h3>风险提示:</h3>"
        if self.get_threat_level(state) in ["高", "极高"]:
            analysis += f"<p style='color:red'>· 秦国威胁极大，需立即采取应对措施</p>"
        
        if state in ['韩', '魏']:
            analysis += f"<p style='color:red'>· 地处四战之地，面临多线作战风险</p>"
        
        return analysis
    
    def get_power_rank(self, state):
        """获取国力排名"""
        powers = []
        for s in self.states:
            power = self.history['power'][s][self.history['year'].index(self.current_year)]
            powers.append((s, power))
        
        powers.sort(key=lambda x: x[1], reverse=True)
        
        for rank, (s, _) in enumerate(powers, 1):
            if s == state:
                return rank
        
        return 7
    
    def get_main_threat(self, state):
        """获取主要威胁"""
        if state == '秦':
            return "六国合纵联盟"
        
        qin_power = self.history['power']['秦'][self.history['year'].index(self.current_year)]
        state_power = self.history['power'][state][self.history['year'].index(self.current_year)]
        
        if qin_power > state_power * 2:
            return "秦国 (压倒性优势)"
        elif qin_power > state_power * 1.5:
            return "秦国 (显著优势)"
        else:
            return "秦国 (潜在威胁)"
    
    def get_potential_ally(self, state):
        """获取潜在盟友"""
        if state == '秦':
            return "韩、魏等弱国"
        
        # 找到对秦国关系最差的国家
        allies = []
        qin_index = self.states.index('秦')
        
        for i, s in enumerate(self.states):
            if s != state and s != '秦' and self.relations[i][qin_index] < -0.2:
                allies.append(s)
        
        if not allies:
            return "无明确盟友"
        
        return "、".join(allies)
    
    def update_alliance_analysis(self):
        """更新联盟分析"""
        # 获取当前联盟
        current_alliance = {"vertical": [], "horizontal": []}
        for alliance in self.alliances:
            if alliance['year'] >= self.current_year:
                current_alliance = alliance
                break
        
        # 更新联盟状态标签
        vertical_text = "、".join(current_alliance['vertical']) if current_alliance['vertical'] else "无"
        horizontal_text = "、".join(current_alliance['horizontal']) if current_alliance['horizontal'] else "无"
        self.alliance_label.setText(f"合纵联盟: {vertical_text} | 连横联盟: {horizontal_text}")
        
        # 更新联盟力量对比
        self.update_alliance_power_comparison(current_alliance)
        
        # 更新联盟稳定性分析
        self.update_alliance_stability(current_alliance)
    
    def update_alliance_power_comparison(self, alliance):
        """更新联盟力量对比"""
        content = "<h3 align='center'>联盟力量对比</h3><hr>"
        
        # 计算合纵联盟力量
        vertical_power = sum(
            self.history['power'][s][self.history['year'].index(self.current_year)]
            for s in alliance['vertical']
        ) if alliance['vertical'] else 0
        
        # 计算连横联盟力量
        horizontal_power = sum(
            self.history['power'][s][self.history['year'].index(self.current_year)]
            for s in alliance['horizontal']
        ) if alliance['horizontal'] else 0
        
        # 计算秦国单独力量
        qin_power = self.history['power']['秦'][self.history['year'].index(self.current_year)]
        
        # 创建对比表格
        content += "<table border='1' cellpadding='5' style='border-collapse:collapse; width:100%'>"
        content += "<tr><th>联盟</th><th>国家</th><th>总实力</th><th>实力占比</th></tr>"
        
        # 合纵联盟
        if alliance['vertical']:
            content += f"<tr><td rowspan='{len(alliance['vertical'])}'>合纵联盟</td>"
            for i, state in enumerate(alliance['vertical']):
                if i > 0:
                    content += "<tr>"
                power = self.history['power'][state][self.history['year'].index(self.current_year)]
                content += f"<td>{state}</td><td>{power:.1f}</td>"
                if i == 0:
                    content += f"<td rowspan='{len(alliance['vertical'])}'>{vertical_power:.1f}</td>"
                    content += f"<td rowspan='{len(alliance['vertical'])}'>{vertical_power/(vertical_power+horizontal_power)*100:.1f}%</td>"
                content += "</tr>"
        else:
            content += "<tr><td>合纵联盟</td><td colspan='3'>无</td></tr>"
        
        # 连横联盟
        if alliance['horizontal']:
            content += f"<tr><td rowspan='{len(alliance['horizontal'])}'>连横联盟</td>"
            for i, state in enumerate(alliance['horizontal']):
                if i > 0:
                    content += "<tr>"
                power = self.history['power'][state][self.history['year'].index(self.current_year)]
                content += f"<td>{state}</td><td>{power:.1f}</td>"
                if i == 0:
                    content += f"<td rowspan='{len(alliance['horizontal'])}'>{horizontal_power:.1f}</td>"
                    content += f"<td rowspan='{len(alliance['horizontal'])}'>{horizontal_power/(vertical_power+horizontal_power)*100:.1f}%</td>"
                content += "</tr>"
        else:
            content += "<tr><td>连横联盟</td><td colspan='3'>无</td></tr>"
        
        content += "</table>"
        
        # 添加对比分析
        content += "<h4>力量对比分析:</h4>"
        if vertical_power > horizontal_power * 1.5:
            content += "<p>合纵联盟占据绝对优势，连横策略面临严峻挑战</p>"
        elif vertical_power > horizontal_power:
            content += "<p>合纵联盟占据优势，但连横联盟仍有反击机会</p>"
        elif horizontal_power > vertical_power * 1.5:
            content += "<p>连横联盟占据绝对优势，合纵策略难以维系</p>"
        elif horizontal_power > vertical_power:
            content += "<p>连横联盟占据优势，合纵联盟面临瓦解风险</p>"
        else:
            content += "<p>双方力量基本平衡，外交策略成为关键</p>"
        
        self.alliance_text.setHtml(content)
    
    def update_alliance_stability(self, alliance):
        """更新联盟稳定性分析"""
        content = "<h3 align='center'>联盟稳定性分析</h3><hr>"
        
        # 分析合纵联盟稳定性
        if alliance['vertical']:
            content += "<h4>合纵联盟稳定性:</h4>"
            
            # 计算平均关系值
            relations = []
            for i in range(len(alliance['vertical'])):
                for j in range(i+1, len(alliance['vertical'])):
                    idx1 = self.states.index(alliance['vertical'][i])
                    idx2 = self.states.index(alliance['vertical'][j])
                    relations.append(self.relations[idx1][idx2])
            
            avg_relation = np.mean(relations) if relations else 0
            
            if avg_relation > 0.2:
                content += "<p>联盟内部关系良好，稳定性高</p>"
            elif avg_relation > 0:
                content += "<p>联盟内部关系一般，存在不稳定因素</p>"
            else:
                content += "<p style='color:red'>联盟内部关系紧张，面临瓦解风险</p>"
            
            content += f"<p>平均内部关系值: {avg_relation:.2f}</p>"
            
            # 找出最弱关系
            min_relation = min(relations) if relations else 0
            if min_relation < -0.3:
                content += "<p style='color:red'>存在严重对立关系，可能成为联盟突破口</p>"
            elif min_relation < -0.1:
                content += "<p>存在潜在冲突关系，需加强外交斡旋</p>"
        else:
            content += "<p>当前无合纵联盟</p>"
        
        # 分析连横联盟稳定性
        if alliance['horizontal']:
            content += "<h4>连横联盟稳定性:</h4>"
            
            # 计算与秦国的平均关系
            qin_idx = self.states.index('秦')
            relations = []
            for state in alliance['horizontal']:
                if state != '秦':
                    idx = self.states.index(state)
                    relations.append(self.relations[idx][qin_idx])
            
            avg_relation = np.mean(relations) if relations else 0
            
            if avg_relation > 0.3:
                content += "<p>各国与秦国关系稳固，联盟稳定性高</p>"
            elif avg_relation > 0.1:
                content += "<p>各国与秦国关系一般，存在不稳定因素</p>"
            else:
                content += "<p style='color:red'>各国与秦国关系紧张，联盟面临瓦解风险</p>"
            
            content += f"<p>平均与秦关系值: {avg_relation:.2f}</p>"
        else:
            content += "<p>当前无连横联盟</p>"
        
        # 总体稳定性分析
        content += "<h4>总体稳定性预测:</h4>"
        if not alliance['vertical'] and not alliance['horizontal']:
            content += "<p>当前无有效联盟，各国各自为政</p>"
        elif alliance['vertical'] and not alliance['horizontal']:
            content += "<p>合纵联盟主导局势，但需警惕秦国分化策略</p>"
        elif not alliance['vertical'] and alliance['horizontal']:
            content += "<p>连横联盟主导局势，秦国占据优势</p>"
        else:
            # 计算实力差
            vertical_power = sum(
                self.history['power'][s][self.history['year'].index(self.current_year)]
                for s in alliance['vertical']
            )
            horizontal_power = sum(
                self.history['power'][s][self.history['year'].index(self.current_year)]
                for s in alliance['horizontal']
            )
            
            if abs(vertical_power - horizontal_power) < 20:
                content += "<p>两大联盟势均力敌，稳定性较高</p>"
            else:
                content += "<p>联盟力量失衡，弱势方可能寻求改变</p>"
        
        self.stability_text.setHtml(content)
    
    def slider_changed(self, value):
        """时间滑块变化事件"""
        self.update_display(value)
    
    def toggle_play(self):
        """切换播放状态"""
        self.is_playing = not self.is_playing
        if self.is_playing:
            self.play_btn.setText("暂停")
            self.timer.start(self.simulation_speed)
        else:
            self.play_btn.setText("播放")
            self.timer.stop()
    
    def pause_simulation(self):
        """暂停模拟"""
        self.is_playing = False
        self.play_btn.setText("播放")
        self.timer.stop()
    
    def reset_simulation(self):
        """重置模拟"""
        self.pause_simulation()
        self.current_year = self.min_year
        self.update_display(self.current_year)
    
    def speed_changed(self, value):
        """速度变化事件"""
        self.simulation_speed = value
        if self.is_playing:
            self.timer.start(self.simulation_speed)
    
    def advance_year(self):
        """推进到下一年"""
        if self.current_year < self.max_year:
            self.current_year += 1
            self.update_display(self.current_year)
        else:
            self.pause_simulation()
    
    def apply_strategy(self):
        """应用策略"""
        state = self.state_combo.currentText()
        strategy = self.strategy_combo.currentText()
        target = self.target_combo.currentText() if self.target_combo.currentText() != "无" else None
        strength = self.strength_spin.value()
        duration = self.duration_spin.value()
        
        # 创建自定义事件
        event = {
            "year": self.current_year,
            "event": f"自定义策略: {state}{strategy}" + (f"({target})" if target else ""),
            "effect": {},
            "type": "策略",
            "duration": duration
        }
        
        # 根据策略类型设置效果
        if strategy == "合纵":
            # 增强与所有国家的关系
            state_idx = self.states.index(state)
            for i in range(len(self.states)):
                if i != state_idx:
                    self.relations[state_idx][i] += strength * 0.02
                    self.relations[i][state_idx] += strength * 0.02
            
            # 添加到事件
            event["effect"]["type"] = "关系增强"
        
        elif strategy == "连横":
            if target:
                # 增强与目标国的关系
                state_idx = self.states.index(state)
                target_idx = self.states.index(target)
                self.relations[state_idx][target_idx] += strength * 0.05
                self.relations[target_idx][state_idx] += strength * 0.03
                
                # 添加到事件
                event["effect"]["type"] = f"与{target}关系增强"
        
        elif strategy == "改革":
            # 增强自身实力
            self.state_power[state] = min(100, self.state_power[state] + strength)
            
            # 添加到事件
            event["effect"][state] = strength
        
        elif strategy == "战争":
            if target:
                # 战争影响
                self.state_power[state] = max(10, self.state_power[state] - strength * 0.3)
                self.state_power[target] = max(10, self.state_power[target] - strength * 0.7)
                
                # 关系恶化
                state_idx = self.states.index(state)
                target_idx = self.states.index(target)
                self.relations[state_idx][target_idx] -= strength * 0.05
                self.relations[target_idx][state_idx] -= strength * 0.08
                
                # 添加到事件
                event["effect"][state] = -strength * 0.3
                event["effect"][target] = -strength * 0.7
        
        # 添加事件到历史
        self.events.append(event)
        
        # 更新显示
        self.update_display(self.current_year)
        
        # 显示成功消息
        self.status_bar.showMessage(f"已应用策略: {state}{strategy}" + (f"({target})" if target else ""))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    # 设置全局字体
    font = QFont("Microsoft YaHei", 9)
    app.setFont(font)
    
    window = WarringStatesSimulator()
    window.show()
    sys.exit(app.exec_())