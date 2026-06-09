import sys
import json
import time
import math
import sqlite3
from datetime import datetime, timedelta
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QTabWidget, 
                             QSpinBox, QComboBox, QSlider, QProgressBar,
                             QGroupBox, QFormLayout, QMessageBox, QListWidget,
                             QCalendarWidget, QSplitter, QFrame, QTextEdit)
from PyQt5.QtCore import QTimer, Qt, pyqtSignal, QSize
from PyQt5.QtGui import QFont, QPalette, QColor, QPainter, QPen, QBrush
from PyQt5.QtChart import QChart, QChartView, QPieSeries, QBarSet, QBarSeries, QBarCategoryAxis

class CircularProgressBar(QWidget):
    """圆形进度条控件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.value = 0
        self.max_value = 100
        self.setMinimumSize(200, 200)
        
    def setValue(self, value):
        self.value = value
        self.update()
        
    def setMaximum(self, max_value):
        self.max_value = max_value
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 绘制背景圆
        pen = QPen(QColor(200, 200, 200), 10, Qt.SolidLine)
        painter.setPen(pen)
        painter.drawEllipse(10, 10, self.width()-20, self.height()-20)
        
        # 绘制进度圆
        pen = QPen(QColor(0, 150, 136), 10, Qt.SolidLine)
        painter.setPen(pen)
        
        # 计算角度
        angle = 360 * self.value / self.max_value
        
        # 绘制圆弧
        painter.drawArc(10, 10, self.width()-20, self.height()-20, 90*16, -int(angle*16))
        
        # 绘制文本
        font = QFont("Arial", 20, QFont.Bold)
        painter.setFont(font)
        painter.setPen(QColor(50, 50, 50))
        painter.drawText(self.rect(), Qt.AlignCenter, f"{self.value}/{self.max_value}")

class MeditationTimer(QWidget):
    """禅定计时器组件"""
    
    timer_finished = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.is_running = False
        self.remaining_time = 0
        self.total_time = 600  # 默认10分钟
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_timer)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 进度条
        self.progress_bar = CircularProgressBar()
        self.progress_bar.setMaximum(self.total_time)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar, 1, Qt.AlignCenter)
        
        # 时间显示
        self.time_label = QLabel(self.format_time(self.total_time))
        self.time_label.setFont(QFont("Arial", 24, QFont.Bold))
        self.time_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.time_label)
        
        # 控制按钮
        button_layout = QHBoxLayout()
        
        self.start_button = QPushButton("开始")
        self.start_button.clicked.connect(self.start_timer)
        button_layout.addWidget(self.start_button)
        
        self.pause_button = QPushButton("暂停")
        self.pause_button.clicked.connect(self.pause_timer)
        self.pause_button.setEnabled(False)
        button_layout.addWidget(self.pause_button)
        
        self.reset_button = QPushButton("重置")
        self.reset_button.clicked.connect(self.reset_timer)
        button_layout.addWidget(self.reset_button)
        
        layout.addLayout(button_layout)
        
        # 时间设置
        settings_group = QGroupBox("时间设置")
        settings_layout = QHBoxLayout()
        
        settings_layout.addWidget(QLabel("时长(分钟):"))
        self.time_spinbox = QSpinBox()
        self.time_spinbox.setRange(1, 120)
        self.time_spinbox.setValue(10)
        self.time_spinbox.valueChanged.connect(self.set_total_time)
        settings_layout.addWidget(self.time_spinbox)
        
        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)
        
        self.setLayout(layout)
        
    def format_time(self, seconds):
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes:02d}:{seconds:02d}"
        
    def set_total_time(self, minutes):
        self.total_time = minutes * 60
        self.remaining_time = self.total_time
        self.progress_bar.setMaximum(self.total_time)
        self.progress_bar.setValue(0)
        self.time_label.setText(self.format_time(self.remaining_time))
        
    def start_timer(self):
        if not self.is_running:
            self.is_running = True
            self.timer.start(1000)  # 每秒更新
            self.start_button.setEnabled(False)
            self.pause_button.setEnabled(True)
            
    def pause_timer(self):
        if self.is_running:
            self.is_running = False
            self.timer.stop()
            self.start_button.setEnabled(True)
            self.pause_button.setEnabled(False)
            
    def reset_timer(self):
        self.pause_timer()
        self.remaining_time = self.total_time
        self.progress_bar.setValue(0)
        self.time_label.setText(self.format_time(self.remaining_time))
        
    def update_timer(self):
        self.remaining_time -= 1
        self.progress_bar.setValue(self.total_time - self.remaining_time)
        self.time_label.setText(self.format_time(self.remaining_time))
        
        if self.remaining_time <= 0:
            self.timer_finished.emit()
            self.pause_timer()

class StatisticsWidget(QWidget):
    """统计信息组件"""
    
    def __init__(self, db_manager):
        super().__init__()
        self.db_manager = db_manager
        self.init_ui()
        self.load_data()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 统计概览
        overview_group = QGroupBox("统计概览")
        overview_layout = QFormLayout()
        
        self.total_sessions_label = QLabel("0")
        overview_layout.addRow("总冥想次数:", self.total_sessions_label)
        
        self.total_time_label = QLabel("0 分钟")
        overview_layout.addRow("总冥想时间:", self.total_time_label)
        
        self.avg_duration_label = QLabel("0 分钟")
        overview_layout.addRow("平均时长:", self.avg_duration_label)
        
        self.current_streak_label = QLabel("0 天")
        overview_layout.addRow("当前连续天数:", self.current_streak_label)
        
        overview_group.setLayout(overview_layout)
        layout.addWidget(overview_group)
        
        # 图表区域
        chart_tabs = QTabWidget()
        
        # 时长分布图
        self.duration_chart_view = QChartView()
        chart_tabs.addTab(self.duration_chart_view, "时长分布")
        
        # 每日统计图
        self.daily_chart_view = QChartView()
        chart_tabs.addTab(self.daily_chart_view, "每日统计")
        
        layout.addWidget(chart_tabs)
        
        self.setLayout(layout)
        
    def load_data(self):
        # 获取统计数据
        stats = self.db_manager.get_statistics()
        
        # 更新概览
        self.total_sessions_label.setText(str(stats['total_sessions']))
        self.total_time_label.setText(f"{stats['total_time']} 分钟")
        self.avg_duration_label.setText(f"{stats['avg_duration']:.1f} 分钟")
        self.current_streak_label.setText(f"{stats['current_streak']} 天")
        
        # 更新图表
        self.update_duration_chart(stats['duration_distribution'])
        self.update_daily_chart(stats['daily_data'])
        
    def update_duration_chart(self, distribution):
        series = QPieSeries()
        
        for duration, count in distribution.items():
            slice = series.append(f"{duration}分钟", count)
            
        chart = QChart()
        chart.addSeries(series)
        chart.setTitle("冥想时长分布")
        chart.legend().setVisible(True)
        
        self.duration_chart_view.setChart(chart)
        
    def update_daily_chart(self, daily_data):
        # 这里简化实现，实际应用中需要更复杂的图表
        chart = QChart()
        chart.setTitle("每日冥想时间")
        
        self.daily_chart_view.setChart(chart)

class SettingsWidget(QWidget):
    """设置组件"""
    
    settings_changed = pyqtSignal(dict)
    
    def __init__(self):
        super().__init__()
        self.settings = self.load_settings()
        self.init_ui()
        
    def load_settings(self):
        # 从文件加载设置，这里使用默认值
        default_settings = {
            'default_duration': 10,
            'sound_enabled': True,
            'background_music': 'None',
            'reminder_enabled': True,
            'reminder_interval': 60,
            'theme': 'light'
        }
        
        try:
            with open('meditation_settings.json', 'r') as f:
                loaded_settings = json.load(f)
                default_settings.update(loaded_settings)
        except FileNotFoundError:
            pass
            
        return default_settings
        
    def save_settings(self):
        with open('meditation_settings.json', 'w') as f:
            json.dump(self.settings, f, indent=4)
            
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 基本设置
        basic_group = QGroupBox("基本设置")
        basic_layout = QFormLayout()
        
        self.duration_spinbox = QSpinBox()
        self.duration_spinbox.setRange(1, 120)
        self.duration_spinbox.setValue(self.settings['default_duration'])
        self.duration_spinbox.valueChanged.connect(self.on_setting_changed)
        basic_layout.addRow("默认时长(分钟):", self.duration_spinbox)
        
        self.sound_checkbox = QPushButton("启用声音" if self.settings['sound_enabled'] else "禁用声音")
        self.sound_checkbox.setCheckable(True)
        self.sound_checkbox.setChecked(self.settings['sound_enabled'])
        self.sound_checkbox.clicked.connect(self.on_setting_changed)
        basic_layout.addRow("声音:", self.sound_checkbox)
        
        self.music_combo = QComboBox()
        self.music_combo.addItems(["无", "自然声音", "冥想音乐", "白噪音"])
        self.music_combo.setCurrentText(self.settings['background_music'])
        self.music_combo.currentTextChanged.connect(self.on_setting_changed)
        basic_layout.addRow("背景音乐:", self.music_combo)
        
        basic_group.setLayout(basic_layout)
        layout.addWidget(basic_group)
        
        # 提醒设置
        reminder_group = QGroupBox("提醒设置")
        reminder_layout = QFormLayout()
        
        self.reminder_checkbox = QPushButton("启用提醒" if self.settings['reminder_enabled'] else "禁用提醒")
        self.reminder_checkbox.setCheckable(True)
        self.reminder_checkbox.setChecked(self.settings['reminder_enabled'])
        self.reminder_checkbox.clicked.connect(self.on_setting_changed)
        reminder_layout.addRow("提醒:", self.reminder_checkbox)
        
        self.interval_slider = QSlider(Qt.Horizontal)
        self.interval_slider.setRange(15, 120)
        self.interval_slider.setValue(self.settings['reminder_interval'])
        self.interval_slider.valueChanged.connect(self.on_setting_changed)
        reminder_layout.addRow("提醒间隔(分钟):", self.interval_slider)
        
        reminder_group.setLayout(reminder_layout)
        layout.addWidget(reminder_group)
        
        # 主题设置
        theme_group = QGroupBox("主题设置")
        theme_layout = QHBoxLayout()
        
        self.light_theme_btn = QPushButton("浅色主题")
        self.light_theme_btn.setCheckable(True)
        self.light_theme_btn.clicked.connect(lambda: self.set_theme('light'))
        
        self.dark_theme_btn = QPushButton("深色主题")
        self.dark_theme_btn.setCheckable(True)
        self.dark_theme_btn.clicked.connect(lambda: self.set_theme('dark'))
        
        # 设置初始状态
        if self.settings['theme'] == 'light':
            self.light_theme_btn.setChecked(True)
        else:
            self.dark_theme_btn.setChecked(True)
            
        theme_layout.addWidget(self.light_theme_btn)
        theme_layout.addWidget(self.dark_theme_btn)
        theme_group.setLayout(theme_layout)
        layout.addWidget(theme_group)
        
        # 保存按钮
        self.save_button = QPushButton("保存设置")
        self.save_button.clicked.connect(self.save_settings)
        layout.addWidget(self.save_button)
        
        layout.addStretch()
        self.setLayout(layout)
        
    def on_setting_changed(self):
        # 更新设置字典
        self.settings['default_duration'] = self.duration_spinbox.value()
        self.settings['sound_enabled'] = self.sound_checkbox.isChecked()
        self.settings['background_music'] = self.music_combo.currentText()
        self.settings['reminder_enabled'] = self.reminder_checkbox.isChecked()
        self.settings['reminder_interval'] = self.interval_slider.value()
        
        # 更新按钮文本
        self.sound_checkbox.setText("启用声音" if self.settings['sound_enabled'] else "禁用声音")
        self.reminder_checkbox.setText("启用提醒" if self.settings['reminder_enabled'] else "禁用提醒")
        
        # 发射信号
        self.settings_changed.emit(self.settings)
        
    def set_theme(self, theme):
        self.settings['theme'] = theme
        self.on_setting_changed()

class GuidedMeditationWidget(QWidget):
    """引导冥想组件"""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 冥想类型选择
        type_group = QGroupBox("冥想类型")
        type_layout = QVBoxLayout()
        
        self.meditation_type_combo = QComboBox()
        self.meditation_type_combo.addItems([
            "呼吸冥想", "身体扫描", "慈心冥想", 
            "正念冥想", "行走冥想", "睡眠冥想"
        ])
        type_layout.addWidget(self.meditation_type_combo)
        
        type_group.setLayout(type_layout)
        layout.addWidget(type_group)
        
        # 引导文本
        self.guide_text = QTextEdit()
        self.guide_text.setReadOnly(True)
        self.guide_text.setPlainText(
            "欢迎使用引导冥想。\n\n"
            "请选择一个冥想类型，然后点击开始按钮。\n"
            "系统将引导您完成整个冥想过程。"
        )
        layout.addWidget(self.guide_text)
        
        # 控制按钮
        button_layout = QHBoxLayout()
        
        self.start_guide_button = QPushButton("开始引导")
        self.start_guide_button.clicked.connect(self.start_guided_meditation)
        button_layout.addWidget(self.start_guide_button)
        
        self.pause_guide_button = QPushButton("暂停引导")
        self.pause_guide_button.setEnabled(False)
        button_layout.addWidget(self.pause_guide_button)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
    def start_guided_meditation(self):
        meditation_type = self.meditation_type_combo.currentText()
        self.guide_text.setPlainText(f"开始{meditation_type}...\n\n请跟随引导进行冥想。")

class DatabaseManager:
    """数据库管理类"""
    
    def __init__(self):
        self.conn = sqlite3.connect('meditation.db')
        self.create_tables()
        
    def create_tables(self):
        cursor = self.conn.cursor()
        
        # 创建冥想记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS meditation_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                start_time TEXT NOT NULL,
                duration INTEGER NOT NULL,
                type TEXT,
                notes TEXT
            )
        ''')
        
        self.conn.commit()
        
    def add_session(self, start_time, duration, meditation_type=None, notes=None):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO meditation_sessions (start_time, duration, type, notes)
            VALUES (?, ?, ?, ?)
        ''', (start_time.isoformat(), duration, meditation_type, notes))
        self.conn.commit()
        
    def get_statistics(self):
        cursor = self.conn.cursor()
        
        # 获取总次数和总时间
        cursor.execute('SELECT COUNT(*), SUM(duration) FROM meditation_sessions')
        result = cursor.fetchone()
        total_sessions = result[0] or 0
        total_time = result[1] or 0
        
        # 计算平均时长
        avg_duration = total_time / total_sessions if total_sessions > 0 else 0
        
        # 获取连续天数（简化实现）
        cursor.execute('SELECT DISTINCT DATE(start_time) FROM meditation_sessions ORDER BY start_time DESC LIMIT 7')
        dates = [row[0] for row in cursor.fetchall()]
        current_streak = self.calculate_streak(dates)
        
        # 获取时长分布（简化实现）
        duration_distribution = {
            "5": 0,
            "10": 0,
            "15": 0,
            "20": 0,
            "30+": 0
        }
        
        cursor.execute('SELECT duration FROM meditation_sessions')
        for row in cursor.fetchall():
            duration = row[0]
            if duration <= 5:
                duration_distribution["5"] += 1
            elif duration <= 10:
                duration_distribution["10"] += 1
            elif duration <= 15:
                duration_distribution["15"] += 1
            elif duration <= 20:
                duration_distribution["20"] += 1
            else:
                duration_distribution["30+"] += 1
                
        return {
            'total_sessions': total_sessions,
            'total_time': total_time,
            'avg_duration': avg_duration,
            'current_streak': current_streak,
            'duration_distribution': duration_distribution,
            'daily_data': {}  # 简化实现
        }
        
    def calculate_streak(self, dates):
        # 简化实现，实际需要更复杂的逻辑
        if not dates:
            return 0
            
        today = datetime.now().date()
        streak = 0
        
        for i, date_str in enumerate(dates):
            date = datetime.fromisoformat(date_str).date()
            if date == today - timedelta(days=i):
                streak += 1
            else:
                break
                
        return streak

class MeditationSystem(QMainWindow):
    """禅定系统主窗口"""
    
    def __init__(self):
        super().__init__()
        self.db_manager = DatabaseManager()
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("禅定系统")
        self.setGeometry(100, 100, 900, 700)
        
        # 创建中央部件和布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # 创建标签页
        self.tabs = QTabWidget()
        
        # 计时器标签页
        self.timer_widget = MeditationTimer()
        self.timer_widget.timer_finished.connect(self.on_timer_finished)
        self.tabs.addTab(self.timer_widget, "冥想计时")
        
        # 统计标签页
        self.stats_widget = StatisticsWidget(self.db_manager)
        self.tabs.addTab(self.stats_widget, "统计数据")
        
        # 引导冥想标签页
        self.guide_widget = GuidedMeditationWidget()
        self.tabs.addTab(self.guide_widget, "引导冥想")
        
        # 设置标签页
        self.settings_widget = SettingsWidget()
        self.settings_widget.settings_changed.connect(self.on_settings_changed)
        self.tabs.addTab(self.settings_widget, "设置")
        
        layout.addWidget(self.tabs)
        
    def on_timer_finished(self):
        # 计时器完成时的处理
        session_duration = self.timer_widget.total_time // 60  # 转换为分钟
        start_time = datetime.now() - timedelta(seconds=self.timer_widget.total_time)
        
        # 保存到数据库
        self.db_manager.add_session(start_time, session_duration)
        
        # 显示完成消息
        QMessageBox.information(self, "冥想完成", 
                               f"恭喜！您已完成 {session_duration} 分钟的冥想。")
        
        # 更新统计页面
        self.stats_widget.load_data()
        
    def on_settings_changed(self, settings):
        # 应用设置更改
        if 'default_duration' in settings:
            self.timer_widget.set_total_time(settings['default_duration'])

def main():
    app = QApplication(sys.argv)
    
    # 设置应用样式
    app.setStyle('Fusion')
    
    # 创建并显示主窗口
    window = MeditationSystem()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()