import sys
import math
import random
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QSlider, QGroupBox,
                             QLCDNumber, QProgressBar, QFrame, QTabWidget, QDial,
                             QComboBox, QSpinBox, QDoubleSpinBox, QCheckBox, QMessageBox)
from PyQt5.QtCore import Qt, QTimer, QTime, QPropertyAnimation, QRect, QEasingCurve, pyqtProperty, QPoint, QSize
from PyQt5.QtGui import QFont, QPalette, QColor, QPainter, QPainterPath, QPen, QBrush, QPixmap, QImage
from PyQt5.QtWidgets import QInputDialog


class FootWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.massage_points = []
        self.pressure_level = 5
        self.is_gripping = False
        self._grip_progress = 0
        self.massage_mode = "Relax"
        self.massage_phase = 0
        self.heat_level = 0
        self.vibration_level = 0
        self.setMinimumSize(500, 400)
        self.foot_color = QColor(255, 200, 150)
        self.generate_massage_points()
        
    def set_pressure(self, level):
        self.pressure_level = level
        self.update()
        
    def set_gripping(self, gripping, progress):
        self.is_gripping = gripping
        self._grip_progress = progress
        self.update()
        
    def set_massage_mode(self, mode):
        self.massage_mode = mode
        self.update()
        
    def set_massage_phase(self, phase):
        self.massage_phase = phase
        self.update()
        
    def set_heat_level(self, level):
        self.heat_level = level
        self.update()
        
    def set_vibration_level(self, level):
        self.vibration_level = level
        self.update()
        
    def generate_massage_points(self):
        self.massage_points = []
        # 生成脚底穴位点
        for i in range(5):  # 脚趾区域
            x = random.randint(200, 280)
            y = random.randint(80, 120)
            self.massage_points.append((x, y, 8, "toe"))
            
        for i in range(8):  # 足弓区域
            x = random.randint(150, 250)
            y = random.randint(150, 220)
            self.massage_points.append((x, y, 10, "arch"))
            
        for i in range(7):  # 脚跟区域
            x = random.randint(120, 180)
            y = random.randint(250, 300)
            self.massage_points.append((x, y, 12, "heel"))
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        width = self.width()
        height = self.height()
        
        # 绘制背景
        painter.fillRect(0, 0, width, height, QColor(240, 240, 240))
        
        # 根据振动级别添加抖动效果
        if self.vibration_level > 0:
            offset_x = random.randint(-self.vibration_level, self.vibration_level)
            offset_y = random.randint(-self.vibration_level, self.vibration_level)
            painter.translate(offset_x, offset_y)
        
        # 绘制脚部轮廓
        foot_path = self.create_foot_path(width, height)
        
        # 根据抓紧进度调整脚的形状
        if self.is_gripping:
            grip_factor = self._grip_progress / 100.0
            # 应用挤压效果
            transform = painter.transform()
            transform.scale(1.0 - 0.2 * grip_factor, 1.0 + 0.1 * grip_factor)
            painter.setTransform(transform)
        
        # 填充脚部
        foot_color = self.foot_color
        if self.heat_level > 0:
            # 添加加热效果
            red = min(255, foot_color.red() + self.heat_level * 5)
            foot_color = QColor(red, foot_color.green() - self.heat_level * 2, foot_color.blue() - self.heat_level * 2)
        
        painter.fillPath(foot_path, QBrush(foot_color))
        
        # 绘制脚部轮廓
        pen = QPen(Qt.black, 2)
        painter.setPen(pen)
        painter.drawPath(foot_path)
        
        # 绘制按摩点
        self.draw_massage_points(painter)
        
        # 绘制压力指示器
        painter.resetTransform()
        pressure_text = f"压力级别: {self.pressure_level}/10"
        painter.drawText(10, 20, pressure_text)
        
        # 绘制当前模式
        mode_text = f"模式: {self.massage_mode}"
        painter.drawText(10, 40, mode_text)
        
        # 绘制抓紧状态
        grip_text = f"抓紧: {'是' if self.is_gripping else '否'} ({self._grip_progress}%)"
        painter.drawText(10, 60, grip_text)
        
        # 绘制加热状态
        if self.heat_level > 0:
            heat_text = f"加热: {self.heat_level}/10"
            painter.drawText(10, 80, heat_text)
            
        # 绘制振动状态
        if self.vibration_level > 0:
            vibration_text = f"振动: {self.vibration_level}/10"
            painter.drawText(10, 100, vibration_text)
            
    def create_foot_path(self, width, height):
        path = QPainterPath()
        
        # 创建脚部形状
        center_x = width / 2
        center_y = height / 2
        
        # 脚趾区域
        path.moveTo(center_x + 80, center_y - 100)
        path.cubicTo(center_x + 100, center_y - 120, center_x + 120, center_y - 110, center_x + 130, center_y - 90)
        
        # 脚侧
        path.cubicTo(center_x + 140, center_y - 70, center_x + 140, center_y + 30, center_x + 120, center_y + 80)
        
        # 脚跟
        path.cubicTo(center_x + 100, center_y + 130, center_x + 40, center_y + 130, center_x + 20, center_y + 80)
        
        # 脚内侧
        path.cubicTo(center_x, center_y + 30, center_x - 20, center_y - 50, center_x + 30, center_y - 90)
        
        # 闭合路径
        path.closeSubpath()
        
        return path
        
    def draw_massage_points(self, painter):
        if self.massage_mode in ["Knead", "Shiatsu", "Tap", "Rolling"]:
            for x, y, size, point_type in self.massage_points:
                # 根据按摩模式选择颜色
                if self.massage_mode == "Knead":
                    color = QColor(255, 100, 100, 150 + self.pressure_level * 10)
                elif self.massage_mode == "Shiatsu":
                    color = QColor(100, 100, 255, 150 + self.pressure_level * 10)
                elif self.massage_mode == "Tap":
                    color = QColor(100, 255, 100, 150 + self.pressure_level * 10)
                else:  # Rolling mode
                    color = QColor(255, 200, 100, 150 + self.pressure_level * 10)
                
                # 根据按摩相位调整点的位置和大小
                phase_offset = math.sin(self.massage_phase / 10.0) * 5
                point_size = size * (0.8 + self.pressure_level / 20.0) + phase_offset
                
                painter.setBrush(QBrush(color))
                painter.setPen(Qt.NoPen)
                
                # 绘制按摩点
                painter.drawEllipse(x - point_size/2, y - point_size/2, point_size, point_size)
                
                # 如果是指压模式，绘制压力指示线
                if self.massage_mode == "Shiatsu" and self.pressure_level > 7:
                    painter.setPen(QPen(QColor(255, 0, 0, 100), 2))
                    painter.drawLine(x, y, x, y - 20 - self.pressure_level * 2)


class FootMassagerSimulator(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.initSounds()
        self.initAnimations()
        
        # 状态变量
        self.current_mode = "Relax"
        self.intensity = 5
        self.pressure_level = 5
        self.heat_level = 0
        self.vibration_level = 0
        self.timer_seconds = 0
        self.is_running = False
        self.remaining_time = 0
        self.is_gripping = False
        self._grip_progress = 0
        self.massage_phase = 0
        self.user_presets = {}
        self.current_preset = None
        
    def initUI(self):
        self.setWindowTitle('高级智能足疗机模拟器')
        self.setGeometry(100, 100, 1200, 800)
        
        # 中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QHBoxLayout()
        central_widget.setLayout(main_layout)
        
        # 左侧控制面板
        control_panel = QGroupBox("控制面板")
        control_layout = QVBoxLayout()
        
        # 预设管理
        preset_group = QGroupBox("预设管理")
        preset_layout = QHBoxLayout()
        
        self.preset_combo = QComboBox()
        self.preset_combo.addItem("自定义")
        self.preset_combo.currentTextChanged.connect(self.load_preset)
        
        self.save_preset_btn = QPushButton("保存预设")
        self.save_preset_btn.clicked.connect(self.save_preset)
        
        self.delete_preset_btn = QPushButton("删除预设")
        self.delete_preset_btn.clicked.connect(self.delete_preset)
        
        preset_layout.addWidget(QLabel("预设:"))
        preset_layout.addWidget(self.preset_combo)
        preset_layout.addWidget(self.save_preset_btn)
        preset_layout.addWidget(self.delete_preset_btn)
        preset_group.setLayout(preset_layout)
        control_layout.addWidget(preset_group)
        
        # 模式选择
        mode_group = QGroupBox("按摩模式")
        mode_layout = QVBoxLayout()
        
        self.mode_buttons = {}
        modes = ["Relax", "Knead", "Tap", "Shiatsu", "Rolling", "Heat", "Grip", "Vibration", "Combination"]
        for mode in modes:
            btn = QPushButton(mode)
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, m=mode: self.set_mode(m))
            mode_layout.addWidget(btn)
            self.mode_buttons[mode] = btn
        
        self.mode_buttons["Relax"].setChecked(True)
        mode_group.setLayout(mode_layout)
        control_layout.addWidget(mode_group)
        
        # 强度控制
        intensity_group = QGroupBox("强度控制")
        intensity_layout = QVBoxLayout()
        
        self.intensity_slider = QSlider(Qt.Horizontal)
        self.intensity_slider.setMinimum(1)
        self.intensity_slider.setMaximum(10)
        self.intensity_slider.setValue(5)
        self.intensity_slider.valueChanged.connect(self.set_intensity)
        
        self.intensity_label = QLabel("强度: 5")
        intensity_layout.addWidget(self.intensity_label)
        intensity_layout.addWidget(self.intensity_slider)
        intensity_group.setLayout(intensity_layout)
        control_layout.addWidget(intensity_group)
        
        # 压力控制
        pressure_group = QGroupBox("压力控制")
        pressure_layout = QVBoxLayout()
        
        self.pressure_slider = QSlider(Qt.Horizontal)
        self.pressure_slider.setMinimum(1)
        self.pressure_slider.setMaximum(10)
        self.pressure_slider.setValue(5)
        self.pressure_slider.valueChanged.connect(self.set_pressure)
        
        self.pressure_label = QLabel("压力: 5")
        pressure_layout.addWidget(self.pressure_label)
        pressure_layout.addWidget(self.pressure_slider)
        pressure_group.setLayout(pressure_layout)
        control_layout.addWidget(pressure_group)
        
        # 加热控制
        heat_group = QGroupBox("加热控制")
        heat_layout = QVBoxLayout()
        
        self.heat_slider = QSlider(Qt.Horizontal)
        self.heat_slider.setMinimum(0)
        self.heat_slider.setMaximum(10)
        self.heat_slider.setValue(0)
        self.heat_slider.valueChanged.connect(self.set_heat_level)
        
        self.heat_label = QLabel("加热: 0")
        heat_layout.addWidget(self.heat_label)
        heat_layout.addWidget(self.heat_slider)
        heat_group.setLayout(heat_layout)
        control_layout.addWidget(heat_group)
        
        # 振动控制
        vibration_group = QGroupBox("振动控制")
        vibration_layout = QVBoxLayout()
        
        self.vibration_slider = QSlider(Qt.Horizontal)
        self.vibration_slider.setMinimum(0)
        self.vibration_slider.setMaximum(10)
        self.vibration_slider.setValue(0)
        self.vibration_slider.valueChanged.connect(self.set_vibration_level)
        
        self.vibration_label = QLabel("振动: 0")
        vibration_layout.addWidget(self.vibration_label)
        vibration_layout.addWidget(self.vibration_slider)
        vibration_group.setLayout(vibration_layout)
        control_layout.addWidget(vibration_group)
        
        # 定时设置
        timer_group = QGroupBox("定时设置")
        timer_layout = QVBoxLayout()
        
        self.timer_buttons = {}
        timers = ["5 min", "10 min", "15 min", "20 min", "30 min", "45 min", "60 min"]
        for t in timers:
            btn = QPushButton(t)
            btn.clicked.connect(lambda checked, t=t: self.set_timer(t))
            timer_layout.addWidget(btn)
            self.timer_buttons[t] = btn
        
        # 自定义定时
        custom_timer_layout = QHBoxLayout()
        self.custom_timer_spin = QSpinBox()
        self.custom_timer_spin.setMinimum(1)
        self.custom_timer_spin.setMaximum(120)
        self.custom_timer_spin.setValue(15)
        self.custom_timer_spin.setSuffix(" 分钟")
        
        self.set_custom_timer_btn = QPushButton("设置定时")
        self.set_custom_timer_btn.clicked.connect(self.set_custom_timer)
        
        custom_timer_layout.addWidget(self.custom_timer_spin)
        custom_timer_layout.addWidget(self.set_custom_timer_btn)
        timer_layout.addLayout(custom_timer_layout)
        
        timer_group.setLayout(timer_layout)
        control_layout.addWidget(timer_group)
        
        # 声音控制
        sound_group = QGroupBox("声音效果")
        sound_layout = QVBoxLayout()
        
        self.sound_btn = QPushButton("音效: 开")
        self.sound_btn.setCheckable(True)
        self.sound_btn.setChecked(True)
        self.sound_btn.clicked.connect(self.toggle_sound)
        sound_layout.addWidget(self.sound_btn)
        
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setMinimum(0)
        self.volume_slider.setMaximum(100)
        self.volume_slider.setValue(80)
        self.volume_slider.valueChanged.connect(self.set_volume)
        
        self.volume_label = QLabel("音量: 80%")
        sound_layout.addWidget(self.volume_label)
        sound_layout.addWidget(self.volume_slider)
        
        sound_group.setLayout(sound_layout)
        control_layout.addWidget(sound_group)
        
        # 开始/停止按钮
        btn_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("开始")
        self.start_btn.clicked.connect(self.toggle_massage)
        self.start_btn.setStyleSheet("background-color: #4CAF50; color: white; font-size: 16px;")
        
        self.stop_btn = QPushButton("停止")
        self.stop_btn.clicked.connect(self.stop_massage)
        self.stop_btn.setStyleSheet("background-color: #f44336; color: white; font-size: 16px;")
        
        self.emergency_stop_btn = QPushButton("紧急停止")
        self.emergency_stop_btn.clicked.connect(self.emergency_stop)
        self.emergency_stop_btn.setStyleSheet("background-color: #ff9800; color: white; font-size: 16px;")
        
        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.stop_btn)
        btn_layout.addWidget(self.emergency_stop_btn)
        
        control_layout.addLayout(btn_layout)
        
        control_panel.setLayout(control_layout)
        main_layout.addWidget(control_panel, 1)
        
        # 右侧显示面板
        display_panel = QGroupBox("状态显示")
        display_layout = QVBoxLayout()
        
        # 创建标签页
        self.tabs = QTabWidget()
        display_layout.addWidget(self.tabs)
        
        # 状态标签页
        status_tab = QWidget()
        status_layout = QVBoxLayout()
        
        # 当前状态显示
        status_group = QGroupBox("当前状态")
        status_layout_inner = QVBoxLayout()
        
        self.mode_display = QLabel("模式: Relax")
        self.mode_display.setFont(QFont("Arial", 14))
        
        self.intensity_display = QLabel("强度: 5")
        self.intensity_display.setFont(QFont("Arial", 14))
        
        self.pressure_display = QLabel("压力: 5")
        self.pressure_display.setFont(QFont("Arial", 14))
        
        self.heat_display = QLabel("加热: 0")
        self.heat_display.setFont(QFont("Arial", 14))
        
        self.vibration_display = QLabel("振动: 0")
        self.vibration_display.setFont(QFont("Arial", 14))
        
        self.timer_display = QLabel("剩余时间: 00:00")
        self.timer_display.setFont(QFont("Arial", 14))
        
        status_layout_inner.addWidget(self.mode_display)
        status_layout_inner.addWidget(self.intensity_display)
        status_layout_inner.addWidget(self.pressure_display)
        status_layout_inner.addWidget(self.heat_display)
        status_layout_inner.addWidget(self.vibration_display)
        status_layout_inner.addWidget(self.timer_display)
        status_group.setLayout(status_layout_inner)
        status_layout.addWidget(status_group)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        status_layout.addWidget(self.progress_bar)
        
        # LCD 显示
        self.lcd = QLCDNumber()
        self.lcd.setDigitCount(8)
        self.lcd.display("00:00:00")
        status_layout.addWidget(self.lcd)
        
        status_tab.setLayout(status_layout)
        self.tabs.addTab(status_tab, "状态")
        
        # 脚部显示标签页
        foot_tab = QWidget()
        foot_layout = QVBoxLayout()
        
        self.foot_widget = FootWidget()
        foot_layout.addWidget(self.foot_widget)
        
        # 生成按摩点按钮
        self.generate_btn = QPushButton("重新生成按摩点")
        self.generate_btn.clicked.connect(self.foot_widget.generate_massage_points)
        foot_layout.addWidget(self.generate_btn)
        
        foot_tab.setLayout(foot_layout)
        self.tabs.addTab(foot_tab, "脚部显示")
        
        # 使用说明标签页
        help_tab = QWidget()
        help_layout = QVBoxLayout()
        
        help_text = QLabel()
        help_text.setText("""
        <h2>足疗机使用说明</h2>
        <p><b>按摩模式:</b></p>
        <ul>
            <li><b>Relax</b> - 放松模式，轻柔按摩</li>
            <li><b>Knead</b> - 揉捏模式，模拟人手揉捏</li>
            <li><b>Tap</b> - 敲击模式，有节奏的敲击</li>
            <li><b>Shiatsu</b> - 指压模式，针对穴位按压</li>
            <li><b>Rolling</b> - 滚轮模式，滚动按摩</li>
            <li><b>Heat</b> - 加热模式，提供热敷效果</li>
            <li><b>Grip</b> - 抓紧模式，模拟足部被包裹</li>
            <li><b>Vibration</b> - 振动模式，提供震动按摩</li>
            <li><b>Combination</b> - 组合模式，多种模式组合</li>
        </ul>
        <p><b>控制说明:</b></p>
        <ul>
            <li>使用滑块调整强度和压力</li>
            <li>设置定时时间，或使用自定义定时</li>
            <li>保存您喜欢的设置作为预设</li>
            <li>点击"开始"启动按摩，"停止"结束按摩</li>
            <li>紧急情况下使用"紧急停止"按钮</li>
        </ul>
        """)
        help_text.setWordWrap(True)
        help_layout.addWidget(help_text)
        
        help_tab.setLayout(help_layout)
        self.tabs.addTab(help_tab, "使用说明")
        
        display_panel.setLayout(display_layout)
        main_layout.addWidget(display_panel, 2)
        
        # 定时器
        self.massage_timer = QTimer()
        self.massage_timer.timeout.connect(self.update_timer)
        
        self.massage_animation_timer = QTimer()
        self.massage_animation_timer.timeout.connect(self.update_massage_animation)
        
        # 初始生成按摩点
        self.foot_widget.generate_massage_points()
        
    def initSounds(self):
        # 初始化声音效果
        self.sounds = {}
        self.sound_enabled = True
        self.volume = 0.8
        
        # 这里应该是加载声音文件的代码
        # 由于没有实际文件，我们使用QSoundEffect但不加载文件
        
    def initAnimations(self):
        # 初始化动画
        self.grip_animation = QPropertyAnimation(self, b"grip_progress")
        self.grip_animation.setDuration(2000)  # 2秒完成抓紧/放松
        self.grip_animation.setEasingCurve(QEasingCurve.InOutQuad)
        
    def toggle_sound(self):
        self.sound_enabled = self.sound_btn.isChecked()
        self.sound_btn.setText("音效: " + ("开" if self.sound_enabled else "关"))
        
    def set_volume(self, value):
        self.volume = value / 100.0
        self.volume_label.setText(f"音量: {value}%")
        
    def set_mode(self, mode):
        self.current_mode = mode
        for m, btn in self.mode_buttons.items():
            btn.setChecked(m == mode)
        self.mode_display.setText(f"模式: {mode}")
        self.foot_widget.set_massage_mode(mode)
        
        # 如果切换到抓紧模式，启动抓紧动画
        if mode == "Grip":
            self.start_grip_animation()
        elif self.is_gripping:
            # 如果从抓紧模式切换到其他模式，停止抓紧
            self.stop_grip_animation()
            
    def set_intensity(self, value):
        self.intensity = value
        self.intensity_label.setText(f"强度: {value}")
        self.intensity_display.setText(f"强度: {value}")
        
    def set_pressure(self, value):
        self.pressure_level = value
        self.pressure_label.setText(f"压力: {value}")
        self.pressure_display.setText(f"压力: {value}")
        self.foot_widget.set_pressure(value)
        
    def set_heat_level(self, value):
        self.heat_level = value
        self.heat_label.setText(f"加热: {value}")
        self.heat_display.setText(f"加热: {value}")
        self.foot_widget.set_heat_level(value)
        
    def set_vibration_level(self, value):
        self.vibration_level = value
        self.vibration_label.setText(f"振动: {value}")
        self.vibration_display.setText(f"振动: {value}")
        self.foot_widget.set_vibration_level(value)
        
    def set_timer(self, timer_str):
        minutes = int(timer_str.split()[0])
        self.timer_seconds = minutes * 60
        self.remaining_time = self.timer_seconds
        self.update_timer_display()
        
    def set_custom_timer(self):
        minutes = self.custom_timer_spin.value()
        self.timer_seconds = minutes * 60
        self.remaining_time = self.timer_seconds
        self.update_timer_display()
        
    def toggle_massage(self):
        if not self.is_running:
            if self.timer_seconds > 0:
                self.is_running = True
                self.start_btn.setText("暂停")
                self.massage_timer.start(1000)  # 每秒更新一次
                self.massage_animation_timer.start(50)  # 每50ms更新动画
                
                # 播放启动声音
                if self.sound_enabled:
                    self.play_sound("start")
        else:
            self.is_running = False
            self.start_btn.setText("继续")
            self.massage_timer.stop()
            self.massage_animation_timer.stop()
            
            # 播放暂停声音
            if self.sound_enabled:
                self.play_sound("pause")
            
    def stop_massage(self):
        self.is_running = False
        self.start_btn.setText("开始")
        self.massage_timer.stop()
        self.massage_animation_timer.stop()
        self.remaining_time = self.timer_seconds
        self.update_timer_display()
        self.progress_bar.setValue(0)
        self.massage_phase = 0
        
        # 如果正在抓紧，恢复放松状态
        if self.is_gripping:
            self.stop_grip_animation()
            
        # 停止加热和振动
        self.set_heat_level(0)
        self.set_vibration_level(0)
        self.heat_slider.setValue(0)
        self.vibration_slider.setValue(0)
            
        # 播放停止声音
        if self.sound_enabled:
            self.play_sound("stop")
            
    def emergency_stop(self):
        self.stop_massage()
        # 播放紧急停止声音
        if self.sound_enabled:
            self.play_sound("emergency")
        QMessageBox.warning(self, "紧急停止", "按摩已紧急停止！")
            
    def update_timer(self):
        if self.remaining_time > 0:
            self.remaining_time -= 1
            self.update_timer_display()
            
            # 更新进度条
            progress = 100 - (self.remaining_time / self.timer_seconds * 100)
            self.progress_bar.setValue(int(progress))
        else:
            self.stop_massage()
            
    def update_timer_display(self):
        minutes = self.remaining_time // 60
        seconds = self.remaining_time % 60
        self.timer_display.setText(f"剩余时间: {minutes:02d}:{seconds:02d}")
        self.lcd.display(f"{minutes:02d}:{seconds:02d}")
        
    def update_massage_animation(self):
        # 更新按摩动画
        self.massage_phase = (self.massage_phase + 1) % 100
        self.foot_widget.set_massage_phase(self.massage_phase)
        
        # 根据模式播放不同的声音
        if self.sound_enabled:
            if self.current_mode == "Knead" and self.massage_phase % 10 == 0:
                self.play_sound("knead")
            elif self.current_mode == "Tap" and self.massage_phase % 5 == 0:
                self.play_sound("tap")
            elif self.current_mode == "Shiatsu" and self.massage_phase % 15 == 0:
                self.play_sound("shiatsu")
            elif self.current_mode == "Rolling" and self.massage_phase % 8 == 0:
                self.play_sound("rolling")
            elif self.current_mode == "Heat" and self.massage_phase % 20 == 0:
                self.play_sound("heat")
            elif self.current_mode == "Vibration" and self.massage_phase % 3 == 0:
                self.play_sound("vibration")
                
        # 组合模式特殊处理
        if self.current_mode == "Combination":
            # 每30秒切换一次模式
            elapsed = self.timer_seconds - self.remaining_time
            if elapsed % 30 == 0 and elapsed > 0:
                modes = ["Knead", "Tap", "Shiatsu", "Rolling"]
                next_mode = modes[(elapsed // 30) % len(modes)]
                self.set_mode(next_mode)
                if self.sound_enabled:
                    self.play_sound("mode_change")
        
    def start_grip_animation(self):
        if not self.is_gripping:
            self.is_gripping = True
            self.grip_animation.setStartValue(0)
            self.grip_animation.setEndValue(100)
            self.grip_animation.start()
            
            # 播放抓紧声音
            if self.sound_enabled:
                self.play_sound("grip_start")
                
    def stop_grip_animation(self):
        if self.is_gripping:
            self.is_gripping = False
            self.grip_animation.setStartValue(100)
            self.grip_animation.setEndValue(0)
            self.grip_animation.start()
            
            # 播放放松声音
            if self.sound_enabled:
                self.play_sound("grip_end")
                
    def get_grip_progress(self):
        if not hasattr(self, '_grip_progress'):
            self._grip_progress = 0
        return self._grip_progress
        
    def set_grip_progress(self, value):
        self._grip_progress = value
        self.foot_widget.set_gripping(self.is_gripping, value)
        
    grip_progress = pyqtProperty(int, get_grip_progress, set_grip_progress)
    
    def save_preset(self):
        name, ok = QInputDialog.getText(self, '保存预设', '请输入预设名称:')
        if ok and name:
            preset = {
                'mode': self.current_mode,
                'intensity': self.intensity,
                'pressure': self.pressure_level,
                'heat': self.heat_level,
                'vibration': self.vibration_level,
                'timer': self.timer_seconds
            }
            self.user_presets[name] = preset
            self.preset_combo.addItem(name)
            self.preset_combo.setCurrentText(name)
            self.current_preset = name
            
    def load_preset(self, name):
        if name == "自定义":
            self.current_preset = None
            return
            
        if name in self.user_presets:
            preset = self.user_presets[name]
            self.set_mode(preset['mode'])
            self.set_intensity(preset['intensity'])
            self.intensity_slider.setValue(preset['intensity'])
            self.set_pressure(preset['pressure'])
            self.pressure_slider.setValue(preset['pressure'])
            self.set_heat_level(preset['heat'])
            self.heat_slider.setValue(preset['heat'])
            self.set_vibration_level(preset['vibration'])
            self.vibration_slider.setValue(preset['vibration'])
            self.timer_seconds = preset['timer']
            self.remaining_time = self.timer_seconds
            self.update_timer_display()
            self.current_preset = name
            
    def delete_preset(self):
        if self.current_preset:
            reply = QMessageBox.question(self, '删除预设', 
                                        f'确定要删除预设 "{self.current_preset}" 吗?',
                                        QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                del self.user_presets[self.current_preset]
                index = self.preset_combo.findText(self.current_preset)
                self.preset_combo.removeItem(index)
                self.preset_combo.setCurrentText("自定义")
                self.current_preset = None
    
    def play_sound(self, sound_type):
        # 在实际应用中，这里应该播放真实的声音文件
        # 由于没有实际文件，我们只是打印一条消息
        print(f"Playing {sound_type} sound at volume {self.volume}")
        
        # 实际代码应该是这样的:
        # if sound_type in self.sounds:
        #     self.sounds[sound_type].setVolume(self.volume)
        #     self.sounds[sound_type].play()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    simulator = FootMassagerSimulator()
    simulator.show()
    sys.exit(app.exec_())