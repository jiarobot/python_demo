import sys
import random
import time
import numpy as np
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QGroupBox, QSlider, QComboBox, QLabel, 
                             QPushButton, QProgressBar, QGraphicsScene, QGraphicsView, 
                             QTextEdit, QTabWidget, QSplitter, QFrame, QGridLayout)
from PyQt5.QtCore import Qt, QTimer, QRectF, QPointF
from PyQt5.QtGui import QColor, QBrush, QPen, QFont, QPainter, QPainterPath
from PyQt5.QtChart import QChart, QChartView, QLineSeries, QValueAxis, QDateTimeAxis

class HumanBodyWidget(QGraphicsView):
    def __init__(self):
        super().__init__()
        self.scene = QGraphicsScene()
        self.setScene(self.scene)
        self.setRenderHint(QPainter.Antialiasing)
        self.setMinimumSize(400, 600)
        
        # 身体部位定义 - 更详细的人体模型
        self.body_parts = {
            'head': QRectF(90, 20, 60, 60),
            'forehead': QRectF(95, 25, 50, 15),
            'face': QRectF(95, 40, 50, 35),
            'neck': QRectF(95, 80, 50, 30),
            'shoulders': QRectF(60, 110, 120, 40),
            'upper_back': QRectF(80, 150, 80, 50),
            'lower_back': QRectF(80, 200, 80, 50),
            'chest': QRectF(80, 150, 80, 40),
            'abdomen': QRectF(80, 190, 80, 30),
            'left_upper_arm': QRectF(40, 110, 25, 50),
            'left_lower_arm': QRectF(40, 160, 25, 50),
            'right_upper_arm': QRectF(195, 110, 25, 50),
            'right_lower_arm': QRectF(195, 160, 25, 50),
            'left_hand': QRectF(40, 210, 25, 20),
            'right_hand': QRectF(195, 210, 25, 20),
            'left_thigh': QRectF(85, 250, 30, 50),
            'right_thigh': QRectF(125, 250, 30, 50),
            'left_calf': QRectF(85, 300, 30, 50),
            'right_calf': QRectF(125, 300, 30, 50),
            'left_foot': QRectF(85, 350, 30, 20),
            'right_foot': QRectF(125, 350, 30, 20)
        }
        
        # 身体部位状态 (0-100, 表示放松/按摩程度)
        self.part_states = {part: 50 for part in self.body_parts.keys()}
        
        # 绘制人体
        self.draw_body()
        
    def draw_body(self):
        self.scene.clear()
        
        # 绘制每个身体部位
        for part, rect in self.body_parts.items():
            # 根据状态计算颜色
            state = self.part_states[part]
            color_value = max(0, min(255, int(255 - state * 2.55)))
            part_color = QColor(255, color_value, color_value)
            part_color.setAlpha(150 + int(state * 1.05))
            
            # 绘制部位
            self.scene.addRect(rect, QPen(Qt.black, 1), QBrush(part_color))
            
            # 添加部位标签
            text = self.scene.addText(part.replace('_', '\n'))
            text.setPos(rect.center().x() - 10, rect.center().y() - 10)
            text.setFont(QFont("Arial", 6))
    
    def update_part_state(self, part, value):
        if part in self.part_states:
            self.part_states[part] = max(0, min(100, value))
            self.draw_body()

class MassageSimulator(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("高级全身按摩器模拟系统")
        self.setGeometry(100, 100, 1400, 900)
        
        # 按摩器状态
        self.is_running = False
        self.massage_intensity = 50
        self.massage_mode = "放松模式"
        self.massage_technique = "振动"
        self.current_position = "upper_back"
        self.massage_direction = 1  # 1 for clockwise, -1 for counterclockwise
        self.heat_level = 0  # 0-100
        self.timer_counter = 0
        
        # 用户状态 - 更多生理指标
        self.user_relaxation = 50
        self.user_heart_rate = 75
        self.user_blood_pressure = (120, 80)  # (systolic, diastolic)
        self.user_muscle_tension = 50
        self.user_comfort = 50
        self.user_stress_level = 50
        self.user_circulation = 50
        self.user_pain_level = 30  # 0-100, 0表示无痛
        
        # 心理状态
        self.mental_states = {
            "anxiety": 40,
            "happiness": 50,
            "fatigue": 60,
            "alertness": 50
        }
        
        # 历史数据记录
        self.history_data = {
            "time": [],
            "relaxation": [],
            "heart_rate": [],
            "comfort": [],
            "stress": []
        }
        
        # 初始化UI
        self.init_ui()
        
        # 设置定时器用于模拟按摩过程
        self.timer = QTimer()
        self.timer.timeout.connect(self.simulate_massage)
        self.timer.start(100)  # 更新间隔100ms
    
    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout()
        central_widget.setLayout(main_layout)
        
        # 左侧控制面板
        left_panel = QWidget()
        left_layout = QVBoxLayout()
        left_panel.setLayout(left_layout)
        
        # 控制面板
        control_panel = QGroupBox("按摩器控制")
        control_layout = QVBoxLayout()
        
        # 开关按钮
        self.power_button = QPushButton("启动按摩")
        self.power_button.clicked.connect(self.toggle_power)
        control_layout.addWidget(self.power_button)
        
        # 强度控制
        intensity_label = QLabel("按摩强度:")
        control_layout.addWidget(intensity_label)
        
        self.intensity_slider = QSlider(Qt.Horizontal)
        self.intensity_slider.setMinimum(10)
        self.intensity_slider.setMaximum(100)
        self.intensity_slider.setValue(50)
        self.intensity_slider.valueChanged.connect(self.set_intensity)
        control_layout.addWidget(self.intensity_slider)
        
        self.intensity_value = QLabel("50%")
        control_layout.addWidget(self.intensity_value)
        
        # 加热控制
        heat_label = QLabel("加热水平:")
        control_layout.addWidget(heat_label)
        
        self.heat_slider = QSlider(Qt.Horizontal)
        self.heat_slider.setMinimum(0)
        self.heat_slider.setMaximum(100)
        self.heat_slider.setValue(0)
        self.heat_slider.valueChanged.connect(self.set_heat_level)
        control_layout.addWidget(self.heat_slider)
        
        self.heat_value = QLabel("0%")
        control_layout.addWidget(self.heat_value)
        
        # 模式选择
        mode_label = QLabel("按摩模式:")
        control_layout.addWidget(mode_label)
        
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["放松模式", "深层组织", "敲击模式", "揉捏模式", "综合模式", "睡眠辅助", "运动恢复"])
        self.mode_combo.currentTextChanged.connect(self.set_mode)
        control_layout.addWidget(self.mode_combo)
        
        # 技术选择
        technique_label = QLabel("按摩技术:")
        control_layout.addWidget(technique_label)
        
        self.technique_combo = QComboBox()
        self.technique_combo.addItems(["振动", "滚动", "叩击", "揉捏", "指压", "推拿", "综合"])
        self.technique_combo.currentTextChanged.connect(self.set_technique)
        control_layout.addWidget(self.technique_combo)
        
        # 定时器设置
        timer_label = QLabel("按摩时间:")
        control_layout.addWidget(timer_label)
        
        self.timer_combo = QComboBox()
        self.timer_combo.addItems(["10分钟", "20分钟", "30分钟", "45分钟", "60分钟", "自定义"])
        control_layout.addWidget(self.timer_combo)
        
        control_panel.setLayout(control_layout)
        left_layout.addWidget(control_panel)
        
        # 用户状态显示
        status_group = QGroupBox("实时生理指标")
        status_layout = QGridLayout()
        
        # 放松程度
        relaxation_label = QLabel("放松程度:")
        status_layout.addWidget(relaxation_label, 0, 0)
        
        self.relaxation_bar = QProgressBar()
        self.relaxation_bar.setValue(50)
        status_layout.addWidget(self.relaxation_bar, 0, 1)
        
        self.relaxation_value = QLabel("50%")
        status_layout.addWidget(self.relaxation_value, 0, 2)
        
        # 心率
        heart_rate_label = QLabel("心率:")
        status_layout.addWidget(heart_rate_label, 1, 0)
        
        self.heart_rate_display = QLabel("75 BPM")
        status_layout.addWidget(self.heart_rate_display, 1, 1, 1, 2)
        
        # 血压
        bp_label = QLabel("血压:")
        status_layout.addWidget(bp_label, 2, 0)
        
        self.bp_display = QLabel("120/80 mmHg")
        status_layout.addWidget(self.bp_display, 2, 1, 1, 2)
        
        # 肌肉紧张度
        tension_label = QLabel("肌肉紧张度:")
        status_layout.addWidget(tension_label, 3, 0)
        
        self.tension_bar = QProgressBar()
        self.tension_bar.setValue(50)
        status_layout.addWidget(self.tension_bar, 3, 1)
        
        self.tension_value = QLabel("50%")
        status_layout.addWidget(self.tension_value, 3, 2)
        
        # 舒适度
        comfort_label = QLabel("舒适度:")
        status_layout.addWidget(comfort_label, 4, 0)
        
        self.comfort_bar = QProgressBar()
        self.comfort_bar.setValue(50)
        status_layout.addWidget(self.comfort_bar, 4, 1)
        
        self.comfort_value = QLabel("50%")
        status_layout.addWidget(self.comfort_value, 4, 2)
        
        # 压力水平
        stress_label = QLabel("压力水平:")
        status_layout.addWidget(stress_label, 5, 0)
        
        self.stress_bar = QProgressBar()
        self.stress_bar.setValue(50)
        status_layout.addWidget(self.stress_bar, 5, 1)
        
        self.stress_value = QLabel("50%")
        status_layout.addWidget(self.stress_value, 5, 2)
        
        # 血液循环
        circulation_label = QLabel("血液循环:")
        status_layout.addWidget(circulation_label, 6, 0)
        
        self.circulation_bar = QProgressBar()
        self.circulation_bar.setValue(50)
        status_layout.addWidget(self.circulation_bar, 6, 1)
        
        self.circulation_value = QLabel("50%")
        status_layout.addWidget(self.circulation_value, 6, 2)
        
        # 疼痛水平
        pain_label = QLabel("疼痛水平:")
        status_layout.addWidget(pain_label, 7, 0)
        
        self.pain_bar = QProgressBar()
        self.pain_bar.setValue(30)
        status_layout.addWidget(self.pain_bar, 7, 1)
        
        self.pain_value = QLabel("30%")
        status_layout.addWidget(self.pain_value, 7, 2)
        
        status_group.setLayout(status_layout)
        left_layout.addWidget(status_group)
        
        # 心理状态显示
        mental_group = QGroupBox("心理状态")
        mental_layout = QVBoxLayout()
        
        self.mental_state = QLabel("心理状态: 正常")
        self.mental_state.setWordWrap(True)
        mental_layout.addWidget(self.mental_state)
        
        # 心理指标细节
        mental_grid = QGridLayout()
        
        anxiety_label = QLabel("焦虑:")
        mental_grid.addWidget(anxiety_label, 0, 0)
        self.anxiety_bar = QProgressBar()
        mental_grid.addWidget(self.anxiety_bar, 0, 1)
        
        happiness_label = QLabel("愉悦:")
        mental_grid.addWidget(happiness_label, 1, 0)
        self.happiness_bar = QProgressBar()
        mental_grid.addWidget(self.happiness_bar, 1, 1)
        
        fatigue_label = QLabel("疲劳:")
        mental_grid.addWidget(fatigue_label, 2, 0)
        self.fatigue_bar = QProgressBar()
        mental_grid.addWidget(self.fatigue_bar, 2, 1)
        
        alertness_label = QLabel("警觉:")
        mental_grid.addWidget(alertness_label, 3, 0)
        self.alertness_bar = QProgressBar()
        mental_grid.addWidget(self.alertness_bar, 3, 1)
        
        mental_layout.addLayout(mental_grid)
        mental_group.setLayout(mental_layout)
        left_layout.addWidget(mental_group)
        
        # 日志区域
        log_group = QGroupBox("按摩日志")
        log_layout = QVBoxLayout()
        
        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(150)
        log_layout.addWidget(self.log_text)
        
        log_group.setLayout(log_layout)
        left_layout.addWidget(log_group)
        
        main_layout.addWidget(left_panel, 1)
        
        # 右侧显示区域
        right_panel = QWidget()
        right_layout = QVBoxLayout()
        right_panel.setLayout(right_layout)
        
        # 人体显示
        display_panel = QGroupBox("按摩效果可视化")
        display_layout = QVBoxLayout()
        
        self.body_widget = HumanBodyWidget()
        display_layout.addWidget(self.body_widget)
        
        # 当前按摩信息
        self.massage_info = QLabel("当前按摩: 上背部 - 放松模式 - 振动技术 - 中等强度")
        self.massage_info.setFont(QFont("Arial", 12, QFont.Bold))
        display_layout.addWidget(self.massage_info)
        
        # 加热指示
        self.heat_info = QLabel("加热: 关闭")
        display_layout.addWidget(self.heat_info)
        
        display_panel.setLayout(display_layout)
        right_layout.addWidget(display_panel)
        
        # 数据图表
        chart_group = QGroupBox("生理指标变化趋势")
        chart_layout = QVBoxLayout()
        
        # 创建图表
        self.chart = QChart()
        self.chart.setTitle("实时生理指标监测")
        self.chart.legend().setVisible(True)
        self.chart.legend().setAlignment(Qt.AlignBottom)
        
        # 创建系列
        self.relaxation_series = QLineSeries()
        self.relaxation_series.setName("放松程度")
        
        self.heart_rate_series = QLineSeries()
        self.heart_rate_series.setName("心率")
        
        self.comfort_series = QLineSeries()
        self.comfort_series.setName("舒适度")
        
        # 添加到图表
        self.chart.addSeries(self.relaxation_series)
        self.chart.addSeries(self.heart_rate_series)
        self.chart.addSeries(self.comfort_series)
        
        # 创建坐标轴
        self.axisX = QDateTimeAxis()
        self.axisX.setFormat("hh:mm:ss")
        self.axisX.setTitleText("时间")
        self.chart.addAxis(self.axisX, Qt.AlignBottom)
        
        self.axisY = QValueAxis()
        self.axisY.setTitleText("数值")
        self.axisY.setRange(0, 100)
        self.chart.addAxis(self.axisY, Qt.AlignLeft)
        
        # 将系列附加到坐标轴
        self.relaxation_series.attachAxis(self.axisX)
        self.relaxation_series.attachAxis(self.axisY)
        self.heart_rate_series.attachAxis(self.axisX)
        self.heart_rate_series.attachAxis(self.axisY)
        self.comfort_series.attachAxis(self.axisX)
        self.comfort_series.attachAxis(self.axisY)
        
        # 创建图表视图
        self.chart_view = QChartView(self.chart)
        self.chart_view.setRenderHint(QPainter.Antialiasing)
        chart_layout.addWidget(self.chart_view)
        
        chart_group.setLayout(chart_layout)
        right_layout.addWidget(chart_group)
        
        main_layout.addWidget(right_panel, 2)
    
    def toggle_power(self):
        self.is_running = not self.is_running
        if self.is_running:
            self.power_button.setText("停止按摩")
            self.log_message("按摩开始")
        else:
            self.power_button.setText("启动按摩")
            self.log_message("按摩结束")
    
    def set_intensity(self, value):
        self.massage_intensity = value
        self.intensity_value.setText(f"{value}%")
    
    def set_heat_level(self, value):
        self.heat_level = value
        self.heat_value.setText(f"{value}%")
        if value > 0:
            self.heat_info.setText(f"加热: {value}% - 温暖")
        else:
            self.heat_info.setText("加热: 关闭")
    
    def set_mode(self, mode):
        self.massage_mode = mode
        self.log_message(f"模式切换到: {mode}")
    
    def set_technique(self, technique):
        self.massage_technique = technique
        self.log_message(f"技术切换到: {technique}")
    
    def log_message(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
        # 自动滚动到底部
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )
    
    def simulate_massage(self):
        if not self.is_running:
            return
        
        self.timer_counter += 1
        
        # 模拟按摩器移动
        positions = list(self.body_widget.body_parts.keys())
        current_index = positions.index(self.current_position)
        
        # 根据模式和技术决定移动频率
        move_frequency = self.get_move_frequency()
        
        # 每隔一段时间改变位置
        if random.random() < move_frequency:
            current_index = (current_index + self.massage_direction) % len(positions)
            self.current_position = positions[current_index]
            
            # 偶尔改变方向
            if random.random() < 0.2:  # 20%的概率改变方向
                self.massage_direction *= -1
        
        # 更新当前按摩部位的状态
        intensity_factor = self.massage_intensity / 100.0
        mode_factor = self.get_mode_factor()
        technique_factor = self.get_technique_factor()
        heat_factor = self.heat_level / 200.0  # 加热效果较温和
        
        # 计算按摩效果 - 更复杂的公式
        base_effect = intensity_factor * mode_factor * technique_factor
        randomness = random.uniform(0.8, 1.2)
        massage_effect = base_effect * randomness + heat_factor
        
        # 更新身体部位状态
        current_state = self.body_widget.part_states[self.current_position]
        new_state = min(100, current_state + massage_effect * 5)
        self.body_widget.update_part_state(self.current_position, new_state)
        
        # 更新用户状态
        self.update_user_state(massage_effect)
        
        # 每5秒记录一次数据
        if self.timer_counter % 50 == 0:
            self.record_data()
        
        # 更新信息显示
        position_name = self.get_position_name(self.current_position)
        self.massage_info.setText(f"当前按摩: {position_name} - {self.massage_mode} - {self.massage_technique} - 强度: {self.massage_intensity}%")
    
    def get_move_frequency(self):
        # 不同模式和技术下的移动频率
        mode_freq = {
            "放松模式": 0.05,
            "深层组织": 0.03,
            "敲击模式": 0.08,
            "揉捏模式": 0.04,
            "综合模式": 0.06,
            "睡眠辅助": 0.02,
            "运动恢复": 0.07
        }
        
        technique_freq = {
            "振动": 0.06,
            "滚动": 0.04,
            "叩击": 0.08,
            "揉捏": 0.05,
            "指压": 0.03,
            "推拿": 0.04,
            "综合": 0.06
        }
        
        return (mode_freq.get(self.massage_mode, 0.05) + 
                technique_freq.get(self.massage_technique, 0.05)) / 2
    
    def get_mode_factor(self):
        # 不同模式的效果因子
        modes = {
            "放松模式": 0.8,
            "深层组织": 1.5,
            "敲击模式": 1.2,
            "揉捏模式": 1.0,
            "综合模式": 1.3,
            "睡眠辅助": 0.7,
            "运动恢复": 1.4
        }
        return modes.get(self.massage_mode, 1.0)
    
    def get_technique_factor(self):
        # 不同技术的效果因子
        techniques = {
            "振动": 0.9,
            "滚动": 1.0,
            "叩击": 1.1,
            "揉捏": 1.2,
            "指压": 1.3,
            "推拿": 1.1,
            "综合": 1.15
        }
        return techniques.get(self.massage_technique, 1.0)
    
    def get_position_name(self, position):
        # 获取身体部位的中文名称
        names = {
            "head": "头部",
            "forehead": "前额",
            "face": "面部",
            "neck": "颈部",
            "shoulders": "肩部",
            "upper_back": "上背部",
            "lower_back": "下背部",
            "chest": "胸部",
            "abdomen": "腹部",
            "left_upper_arm": "左上臂",
            "left_lower_arm": "左下臂",
            "right_upper_arm": "右上臂",
            "right_lower_arm": "右下臂",
            "left_hand": "左手",
            "right_hand": "右手",
            "left_thigh": "左大腿",
            "right_thigh": "右大腿",
            "left_calf": "左小腿",
            "right_calf": "右小腿",
            "left_foot": "左脚",
            "right_foot": "右脚"
        }
        return names.get(position, position)
    
    def update_user_state(self, massage_effect):
        # 更新放松程度 (按摩效果越好，放松程度增加)
        relaxation_change = massage_effect * 0.5 - 0.1
        self.user_relaxation = max(0, min(100, self.user_relaxation + relaxation_change))
        self.relaxation_bar.setValue(int(self.user_relaxation))
        self.relaxation_value.setText(f"{int(self.user_relaxation)}%")
        
        # 更新心率 (适度按摩降低心率，过度按摩可能增加心率)
        hr_change = -massage_effect * 0.8 if massage_effect < 1.2 else massage_effect * 0.5
        self.user_heart_rate = max(60, min(120, self.user_heart_rate + hr_change))
        self.heart_rate_display.setText(f"{int(self.user_heart_rate)} BPM")
        
        # 更新血压 (适度按摩降低血压)
        bp_change = -massage_effect * 0.5 if massage_effect < 1.5 else massage_effect * 0.3
        new_systolic = max(90, min(140, self.user_blood_pressure[0] + bp_change))
        new_diastolic = max(60, min(90, self.user_blood_pressure[1] + bp_change * 0.7))
        self.user_blood_pressure = (new_systolic, new_diastolic)
        self.bp_display.setText(f"{int(new_systolic)}/{int(new_diastolic)} mmHg")
        
        # 更新肌肉紧张度 (按摩降低紧张度)
        tension_change = -massage_effect * 0.7
        self.user_muscle_tension = max(0, min(100, self.user_muscle_tension + tension_change))
        self.tension_bar.setValue(int(self.user_muscle_tension))
        self.tension_value.setText(f"{int(self.user_muscle_tension)}%")
        
        # 更新舒适度 (适度按摩增加舒适度，过度按摩降低舒适度)
        comfort_change = massage_effect * 0.6 if massage_effect < 1.5 else -massage_effect * 0.4
        self.user_comfort = max(0, min(100, self.user_comfort + comfort_change))
        self.comfort_bar.setValue(int(self.user_comfort))
        self.comfort_value.setText(f"{int(self.user_comfort)}%")
        
        # 更新压力水平 (按摩降低压力)
        stress_change = -massage_effect * 0.5
        self.user_stress_level = max(0, min(100, self.user_stress_level + stress_change))
        self.stress_bar.setValue(int(self.user_stress_level))
        self.stress_value.setText(f"{int(self.user_stress_level)}%")
        
        # 更新血液循环 (按摩促进血液循环)
        circulation_change = massage_effect * 0.4
        self.user_circulation = max(0, min(100, self.user_circulation + circulation_change))
        self.circulation_bar.setValue(int(self.user_circulation))
        self.circulation_value.setText(f"{int(self.user_circulation)}%")
        
        # 更新疼痛水平 (按摩缓解疼痛)
        pain_change = -massage_effect * 0.6
        self.user_pain_level = max(0, min(100, self.user_pain_level + pain_change))
        self.pain_bar.setValue(int(self.user_pain_level))
        self.pain_value.setText(f"{int(self.user_pain_level)}%")
        
        # 更新心理状态
        self.update_mental_state(massage_effect)
        
        # 更新心理指标
        self.update_mental_indicators(massage_effect)
    
    def update_mental_state(self, massage_effect):
        # 更复杂的心理状态判断
        if self.user_relaxation > 85 and self.user_comfort > 85 and self.user_stress_level < 15:
            state = "非常放松和愉悦，几乎达到冥想状态"
        elif self.user_relaxation > 70 and self.user_comfort > 70:
            state = "放松舒适，心情愉快"
        elif self.user_comfort < 20 or self.user_pain_level > 70:
            state = "不适和烦躁，可能需要调整设置"
        elif self.user_stress_level > 70:
            state = "压力较大，按摩效果尚未显现"
        elif self.mental_states["fatigue"] > 70 and self.user_relaxation > 60:
            state = "放松但疲劳，可能很快会入睡"
        elif self.mental_states["alertness"] > 70:
            state = "精神警觉，按摩提供了能量"
        else:
            state = "状态正常"
        
        self.mental_state.setText(f"心理状态: {state}")
    
    def update_mental_indicators(self, massage_effect):
        # 更新焦虑水平 (按摩降低焦虑)
        anxiety_change = -massage_effect * 0.4
        self.mental_states["anxiety"] = max(0, min(100, self.mental_states["anxiety"] + anxiety_change))
        self.anxiety_bar.setValue(int(self.mental_states["anxiety"]))
        
        # 更新愉悦程度 (按摩增加愉悦)
        happiness_change = massage_effect * 0.5 if massage_effect < 1.5 else -massage_effect * 0.2
        self.mental_states["happiness"] = max(0, min(100, self.mental_states["happiness"] + happiness_change))
        self.happiness_bar.setValue(int(self.mental_states["happiness"]))
        
        # 更新疲劳程度 (按摩可能缓解或增加疲劳，取决于模式)
        if self.massage_mode == "睡眠辅助":
            fatigue_change = massage_effect * 0.6
        else:
            fatigue_change = -massage_effect * 0.3 if massage_effect < 1.2 else massage_effect * 0.2
        
        self.mental_states["fatigue"] = max(0, min(100, self.mental_states["fatigue"] + fatigue_change))
        self.fatigue_bar.setValue(int(self.mental_states["fatigue"]))
        
        # 更新警觉程度 (按摩可能提高或降低警觉性，取决于模式)
        if self.massage_mode == "运动恢复":
            alertness_change = massage_effect * 0.5
        else:
            alertness_change = -massage_effect * 0.4
        
        self.mental_states["alertness"] = max(0, min(100, self.mental_states["alertness"] + alertness_change))
        self.alertness_bar.setValue(int(self.mental_states["alertness"]))
    
    def record_data(self):
        # 记录当前时间戳和数据
        current_time = datetime.now()
        
        self.history_data["time"].append(current_time)
        self.history_data["relaxation"].append(self.user_relaxation)
        self.history_data["heart_rate"].append(self.user_heart_rate)
        self.history_data["comfort"].append(self.user_comfort)
        self.history_data["stress"].append(self.user_stress_level)
        
        # 更新图表
        self.update_chart()
    
    def update_chart(self):
        # 清除旧数据
        self.relaxation_series.clear()
        self.heart_rate_series.clear()
        self.comfort_series.clear()
        
        # 添加新数据
        for i in range(len(self.history_data["time"])):
            time_val = self.history_data["time"][i]
            relaxation_val = self.history_data["relaxation"][i]
            heart_rate_val = self.history_data["heart_rate"][i]
            comfort_val = self.history_data["comfort"][i]
            
            # 将时间转换为毫秒
            msecs = time_val.timestamp() * 1000
            
            self.relaxation_series.append(msecs, relaxation_val)
            self.heart_rate_series.append(msecs, heart_rate_val)
            self.comfort_series.append(msecs, comfort_val)
        
        # 调整X轴范围以显示所有数据
        if self.history_data["time"]:
            min_time = self.history_data["time"][0]
            max_time = self.history_data["time"][-1]
            
            self.axisX.setMin(min_time)
            self.axisX.setMax(max_time)
        
        # 调整Y轴范围
        all_values = (self.history_data["relaxation"] + 
                     self.history_data["heart_rate"] + 
                     self.history_data["comfort"] + 
                     self.history_data["stress"])
        
        if all_values:
            min_val = min(all_values) * 0.9
            max_val = max(all_values) * 1.1
            self.axisY.setMin(min_val)
            self.axisY.setMax(max_val)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    simulator = MassageSimulator()
    simulator.show()
    sys.exit(app.exec_())