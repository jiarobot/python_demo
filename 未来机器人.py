import sys
import random
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QGridLayout, QGroupBox, QLabel, 
                            QProgressBar, QPushButton, QTabWidget, QFrame,
                            QSlider, QTextEdit, QSplitter, QComboBox)
from PyQt6.QtCore import QTimer, Qt, pyqtSignal
from PyQt6.QtGui import QFont, QPalette, QColor, QPainter, QLinearGradient
from PyQt6.QtCharts import QChart, QChartView, QLineSeries, QValueAxis
from PyQt6.QtCore import QPointF

class SystemIndicator(QWidget):
    """自定义系统状态指示器"""
    def __init__(self, system_name, parent=None):
        super().__init__(parent)
        self.system_name = system_name
        self.status = "正常"  # 正常, 警告, 危险
        self.value = 0
        self.setMinimumHeight(80)
        
    def set_status(self, status, value):
        self.status = status
        self.value = value
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 根据状态设置颜色
        if self.status == "正常":
            color = QColor(0, 255, 0)
        elif self.status == "警告":
            color = QColor(255, 255, 0)
        else:
            color = QColor(255, 0, 0)
            
        # 绘制背景
        gradient = QLinearGradient(0, 0, self.width(), 0)
        gradient.setColorAt(0, QColor(50, 50, 50))
        gradient.setColorAt(1, QColor(80, 80, 80))
        painter.fillRect(self.rect(), gradient)
        
        # 绘制状态条
        status_width = int(self.width() * self.value / 100)
        painter.fillRect(0, 0, status_width, self.height(), color)
        
        # 绘制文本
        painter.setPen(QColor(255, 255, 255))
        font = QFont("Arial", 10, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, 
                        f"{self.system_name}\n{self.status}")

class BloodSystemPanel(QWidget):
    """血液系统控制面板"""
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        layout = QGridLayout()
        
        # 能量状态
        energy_group = QGroupBox("能量循环状态")
        energy_layout = QVBoxLayout()
        
        self.energy_level = QProgressBar()
        self.energy_level.setFormat("能量水平: %p%")
        self.energy_level.setStyleSheet("QProgressBar::chunk { background-color: #ff4444; }")
        
        self.flow_rate = QProgressBar()
        self.flow_rate.setFormat("循环流速: %p%")
        self.flow_rate.setStyleSheet("QProgressBar::chunk { background-color: #44ff44; }")
        
        self.temperature = QProgressBar()
        self.temperature.setFormat("系统温度: %p%")
        self.temperature.setStyleSheet("QProgressBar::chunk { background-color: #4444ff; }")
        
        energy_layout.addWidget(QLabel("液态电池状态:"))
        energy_layout.addWidget(self.energy_level)
        energy_layout.addWidget(QLabel("液压循环:"))
        energy_layout.addWidget(self.flow_rate)
        energy_layout.addWidget(QLabel("热管理:"))
        energy_layout.addWidget(self.temperature)
        energy_group.setLayout(energy_layout)
        
        # 控制面板
        control_group = QGroupBox("循环网络控制")
        control_layout = QVBoxLayout()
        
        self.pump_slider = QSlider(Qt.Orientation.Horizontal)
        self.pump_slider.setRange(0, 100)
        self.pump_slider.setValue(50)
        
        self.cooling_btn = QPushButton("激活主动冷却")
        self.energy_boost_btn = QPushButton("能量增压")
        
        control_layout.addWidget(QLabel("主泵功率:"))
        control_layout.addWidget(self.pump_slider)
        control_layout.addWidget(self.cooling_btn)
        control_layout.addWidget(self.energy_boost_btn)
        control_group.setLayout(control_layout)
        
        layout.addWidget(energy_group, 0, 0)
        layout.addWidget(control_group, 0, 1)
        
        self.setLayout(layout)

class SkinSystemPanel(QWidget):
    """皮肤嗅觉系统控制面板"""
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        layout = QGridLayout()
        
        # 感知状态
        sense_group = QGroupBox("多模态感知状态")
        sense_layout = QVBoxLayout()
        
        self.chemical_sense = QProgressBar()
        self.chemical_sense.setFormat("化学感知: %p%")
        
        self.tactile_sense = QProgressBar()
        self.tactile_sense.setFormat("触觉感知: %p%")
        
        self.temp_sense = QProgressBar()
        self.temp_sense.setFormat("温度感知: %p%")
        
        sense_layout.addWidget(self.chemical_sense)
        sense_layout.addWidget(self.tactile_sense)
        sense_layout.addWidget(self.temp_sense)
        sense_group.setLayout(sense_layout)
        
        # 神经形态计算
        neuro_group = QGroupBox("神经形态计算")
        neuro_layout = QVBoxLayout()
        
        self.process_load = QProgressBar()
        self.process_load.setFormat("处理负载: %p%")
        
        self.reaction_time = QLabel("反应延迟: 12ms")
        self.pattern_recognition = QLabel("模式识别: 98.7%")
        
        neuro_layout.addWidget(self.process_load)
        neuro_layout.addWidget(self.reaction_time)
        neuro_layout.addWidget(self.pattern_recognition)
        neuro_group.setLayout(neuro_layout)
        
        # 控制面板
        control_group = QGroupBox("感知控制")
        control_layout = QVBoxLayout()
        
        self.sensitivity = QSlider(Qt.Orientation.Horizontal)
        self.sensitivity.setRange(0, 100)
        self.sensitivity.setValue(75)
        
        self.chem_filter = QComboBox()
        self.chem_filter.addItems(["全谱感知", "危险品检测", "环境监测", "医疗诊断"])
        
        control_layout.addWidget(QLabel("感知灵敏度:"))
        control_layout.addWidget(self.sensitivity)
        control_layout.addWidget(QLabel("化学过滤器:"))
        control_layout.addWidget(self.chem_filter)
        control_group.setLayout(control_layout)
        
        layout.addWidget(sense_group, 0, 0)
        layout.addWidget(neuro_group, 1, 0)
        layout.addWidget(control_group, 0, 1, 2, 1)
        
        self.setLayout(layout)

class VisionSystemPanel(QWidget):
    """视觉系统面板"""
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 视觉处理状态
        self.processing_rate = QProgressBar()
        self.processing_rate.setFormat("视觉处理帧率: %p%")
        
        self.object_detection = QLabel("目标检测准确率: 96.3%")
        self.depth_perception = QLabel("深度感知: 正常")
        
        layout.addWidget(self.processing_rate)
        layout.addWidget(self.object_detection)
        layout.addWidget(self.depth_perception)
        
        self.setLayout(layout)

class AISystemPanel(QWidget):
    """AI大脑系统面板"""
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        self.neural_load = QProgressBar()
        self.neural_load.setFormat("神经网络负载: %p%")
        
        self.inference_speed = QLabel("推理速度: 245 FPS")
        self.learning_rate = QLabel("学习速率: 0.001")
        
        layout.addWidget(self.neural_load)
        layout.addWidget(self.inference_speed)
        layout.addWidget(self.learning_rate)
        
        self.setLayout(layout)

class LanguageSystemPanel(QWidget):
    """语言系统面板"""
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        self.response_time = QProgressBar()
        self.response_time.setFormat("响应时间: %p ms")
        
        self.conversation_log = QTextEdit()
        self.conversation_log.setPlainText("系统就绪...\n等待语音输入...")
        
        layout.addWidget(self.response_time)
        layout.addWidget(QLabel("对话记录:"))
        layout.addWidget(self.conversation_log)
        
        self.setLayout(layout)

class MotionSystemPanel(QWidget):
    """运动系统面板"""
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        self.hydraulic_pressure = QProgressBar()
        self.hydraulic_pressure.setFormat("液压压力: %p%")
        
        self.joint_flexibility = QLabel("关节柔顺度: 85%")
        self.power_efficiency = QLabel("能量效率: 92%")
        
        layout.addWidget(self.hydraulic_pressure)
        layout.addWidget(self.joint_flexibility)
        layout.addWidget(self.power_efficiency)
        
        self.setLayout(layout)

class IntegratedChart(QChartView):
    """集成状态图表"""
    def __init__(self):
        super().__init__()
        self.chart = QChart()
        self.setChart(self.chart)
        self.chart.setTitle("系统集成状态趋势")
        self.chart.legend().setVisible(True)
        
        # 创建数据系列
        self.series_energy = QLineSeries()
        self.series_energy.setName("能量水平")
        
        self.series_perception = QLineSeries()
        self.series_perception.setName("感知效率")
        
        self.series_processing = QLineSeries()
        self.series_processing.setName("处理负载")
        
        self.chart.addSeries(self.series_energy)
        self.chart.addSeries(self.series_perception)
        self.chart.addSeries(self.series_processing)
        
        # 设置坐标轴
        self.axis_x = QValueAxis()
        self.axis_x.setTitleText("时间")
        self.axis_x.setRange(0, 100)
        
        self.axis_y = QValueAxis()
        self.axis_y.setTitleText("百分比")
        self.axis_y.setRange(0, 100)
        
        self.chart.addAxis(self.axis_x, Qt.AlignmentFlag.AlignBottom)
        self.chart.addAxis(self.axis_y, Qt.AlignmentFlag.AlignLeft)
        
        self.series_energy.attachAxis(self.axis_x)
        self.series_energy.attachAxis(self.axis_y)
        self.series_perception.attachAxis(self.axis_x)
        self.series_perception.attachAxis(self.axis_y)
        self.series_processing.attachAxis(self.axis_x)
        self.series_processing.attachAxis(self.axis_y)
        
        self.data_points = 0
        
    def add_data_point(self, energy, perception, processing):
        self.series_energy.append(QPointF(self.data_points, energy))
        self.series_perception.append(QPointF(self.data_points, perception))
        self.series_processing.append(QPointF(self.data_points, processing))
        
        if self.data_points > 100:
            self.series_energy.remove(0)
            self.series_perception.remove(0)
            self.series_processing.remove(0)
            self.axis_x.setRange(self.data_points - 100, self.data_points)
        else:
            self.axis_x.setRange(0, 100)
            
        self.data_points += 1

class FutureRobotControl(QMainWindow):
    """未来机器人主控界面"""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.setup_data_simulation()
        
    def init_ui(self):
        self.setWindowTitle("未来机器人集成控制系统 - 机体系统 v2.0")
        self.setGeometry(100, 100, 1400, 900)
        
        # 设置深色主题
        self.set_dark_theme()
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # 顶部状态栏
        top_layout = QHBoxLayout()
        self.system_indicators = {}
        
        systems = ["视觉系统", "AI大脑", "语言模型", "循环网络", "运动系统", "感知皮肤"]
        for system in systems:
            indicator = SystemIndicator(system)
            self.system_indicators[system] = indicator
            top_layout.addWidget(indicator)
            
        main_layout.addLayout(top_layout)
        
        # 创建标签页
        self.tabs = QTabWidget()
        
        # 血液系统标签页
        self.blood_tab = BloodSystemPanel()
        self.tabs.addTab(self.blood_tab, "🩸 循环功能网络")
        
        # 皮肤系统标签页
        self.skin_tab = SkinSystemPanel()
        self.tabs.addTab(self.skin_tab, "👃 分布式感知皮肤")
        
        # 视觉系统标签页
        self.vision_tab = VisionSystemPanel()
        self.tabs.addTab(self.vision_tab, "👁️ 机器视觉")
        
        # AI系统标签页
        self.ai_tab = AISystemPanel()
        self.tabs.addTab(self.ai_tab, "🧠 神经网络")
        
        # 语言系统标签页
        self.language_tab = LanguageSystemPanel()
        self.tabs.addTab(self.language_tab, "🗣️ 大语言模型")
        
        # 运动系统标签页
        self.motion_tab = MotionSystemPanel()
        self.tabs.addTab(self.motion_tab, "🤖 液压运动系统")
        
        main_layout.addWidget(self.tabs)
        
        # 底部集成状态区域
        bottom_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 集成状态图表
        self.integrated_chart = IntegratedChart()
        bottom_splitter.addWidget(self.integrated_chart)
        
        # 系统日志
        log_group = QGroupBox("系统集成日志")
        log_layout = QVBoxLayout()
        self.system_log = QTextEdit()
        self.system_log.setMaximumWidth(400)
        log_layout.addWidget(self.system_log)
        log_group.setLayout(log_layout)
        bottom_splitter.addWidget(log_group)
        
        bottom_splitter.setSizes([800, 400])
        main_layout.addWidget(bottom_splitter)
        
        # 添加系统日志
        self.log_message("系统启动: 未来机器人机体系统初始化完成")
        self.log_message("循环功能网络: 液态电池在线, 液压系统加压中")
        self.log_message("分布式感知皮肤: 神经形态芯片激活, 多模态传感器校准")
        self.log_message("系统集成: 各子系统协同运行模式启动")
        
    def set_dark_theme(self):
        """设置深色主题"""
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(30, 30, 30))
        palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.Base, QColor(25, 25, 25))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(35, 35, 35))
        palette.setColor(QPalette.ColorRole.ToolTipBase, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.ToolTipText, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.Button, QColor(50, 50, 50))
        palette.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.Highlight, QColor(142, 45, 197).lighter())
        palette.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.black)
        self.setPalette(palette)
        
    def setup_data_simulation(self):
        """设置数据模拟定时器"""
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_system_data)
        self.timer.start(1000)  # 每秒更新一次
        
        self.simulation_counter = 0
        
    def update_system_data(self):
        """更新所有系统数据"""
        self.simulation_counter += 1
        
        # 模拟血液系统数据
        energy_level = 70 + 20 * random.random()
        flow_rate = 60 + 30 * random.random()
        temperature = 30 + 20 * random.random()
        
        self.blood_tab.energy_level.setValue(int(energy_level))
        self.blood_tab.flow_rate.setValue(int(flow_rate))
        self.blood_tab.temperature.setValue(int(temperature))
        
        # 模拟皮肤系统数据
        chem_sense = 80 + 15 * random.random()
        tactile_sense = 85 + 10 * random.random()
        temp_sense = 75 + 20 * random.random()
        process_load = 40 + 40 * random.random()
        
        self.skin_tab.chemical_sense.setValue(int(chem_sense))
        self.skin_tab.tactile_sense.setValue(int(tactile_sense))
        self.skin_tab.temp_sense.setValue(int(temp_sense))
        self.skin_tab.process_load.setValue(int(process_load))
        
        # 更新其他系统
        self.vision_tab.processing_rate.setValue(int(80 + 15 * random.random()))
        self.ai_tab.neural_load.setValue(int(50 + 40 * random.random()))
        self.language_tab.response_time.setValue(int(20 + 30 * random.random()))
        self.motion_tab.hydraulic_pressure.setValue(int(65 + 25 * random.random()))
        
        # 更新系统指示器
        systems_status = {
            "视觉系统": ("正常", 85 + 10 * random.random()),
            "AI大脑": ("正常", 60 + 30 * random.random()),
            "语言模型": ("正常", 75 + 20 * random.random()),
            "循环网络": ("正常", 70 + 20 * random.random()),
            "运动系统": ("正常", 70 + 25 * random.random()),
            "感知皮肤": ("正常", 80 + 15 * random.random())
        }
        
        for system, (status, value) in systems_status.items():
            self.system_indicators[system].set_status(status, value)
            
        # 更新集成图表
        self.integrated_chart.add_data_point(energy_level, chem_sense, process_load)
        
        # 偶尔添加日志
        if random.random() < 0.2:
            messages = [
                "循环网络: 能量分布优化完成",
                "感知皮肤: 检测到环境化学变化",
                "液压系统: 压力稳定在最佳范围",
                "神经形态计算: 模式识别准确率提升",
                "系统集成: 各模块协同运行正常"
            ]
            self.log_message(random.choice(messages))
            
    def log_message(self, message):
        """添加系统日志"""
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.system_log.append(f"[{timestamp}] {message}")
        
        # 保持日志长度
        if self.system_log.document().lineCount() > 100:
            cursor = self.system_log.textCursor()
            cursor.movePosition(cursor.MoveOperation.Start)
            cursor.select(cursor.SelectionType.BlockUnderCursor)
            cursor.removeSelectedText()

def main():
    app = QApplication(sys.argv)
    
    # 设置应用程序字体
    font = QFont("Arial", 10)
    app.setFont(font)
    
    window = FutureRobotControl()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()