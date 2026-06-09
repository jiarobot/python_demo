import sys
import os
import json
import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QTextEdit, QListWidget, QLineEdit, 
                             QLabel, QCalendarWidget, QProgressBar, QMessageBox, QSplitter,
                             QFrame, QGroupBox, QCheckBox, QSpinBox, QComboBox, QSlider)
from PyQt5.QtCore import Qt, QTimer, QDate
from PyQt5.QtGui import QFont, QPalette, QColor, QIcon
import random
import math

class PleasureSystem(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.loadData()
        
    def initUI(self):
        self.setWindowTitle('愉悦自我系统 - 高级工具库')
        self.setGeometry(100, 100, 1200, 800)
        
        # 设置应用图标和样式
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f0f0f0;
            }
            QTabWidget::pane {
                border: 1px solid #C2C7CB;
                background-color: white;
            }
            QTabBar::tab {
                background-color: #E1E1E1;
                color: #333;
                padding: 8px 20px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background-color: #5D9BFF;
                color: white;
            }
            QPushButton {
                background-color: #5D9BFF;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #4A8AFF;
            }
            QPushButton:pressed {
                background-color: #3A7AFF;
            }
            QListWidget {
                border: 1px solid #CCC;
                border-radius: 4px;
                background-color: white;
            }
            QTextEdit {
                border: 1px solid #CCC;
                border-radius: 4px;
                background-color: white;
            }
            QLineEdit {
                border: 1px solid #CCC;
                border-radius: 4px;
                padding: 5px;
                background-color: white;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #CCC;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        
        # 创建中央部件和主布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # 创建标签页
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)
        
        # 创建各个功能标签页
        self.createJournalTab()
        self.createTaskManagerTab()
        self.createMoodTrackerTab()
        self.createMindfulnessTab()
        self.createProductivityTab()
        self.createSettingsTab()
        
        # 状态栏
        self.statusBar().showMessage('愉悦自我系统已就绪')
        
        # 自动保存计时器
        self.autosave_timer = QTimer()
        self.autosave_timer.timeout.connect(self.saveData)
        self.autosave_timer.start(30000)  # 每30秒自动保存
        
    def createJournalTab(self):
        """创建日记标签页"""
        journal_tab = QWidget()
        layout = QVBoxLayout(journal_tab)
        
        # 顶部控件
        top_layout = QHBoxLayout()
        self.journal_date = QCalendarWidget()
        self.journal_date.setGridVisible(True)
        self.journal_date.clicked.connect(self.loadJournalEntry)
        top_layout.addWidget(self.journal_date)
        
        # 右侧统计信息
        stats_group = QGroupBox("日记统计")
        stats_layout = QVBoxLayout()
        self.journal_stats = QLabel("总日记数: 0\n本月日记: 0")
        self.journal_stats.setFont(QFont("Arial", 10))
        stats_layout.addWidget(self.journal_stats)
        stats_group.setLayout(stats_layout)
        top_layout.addWidget(stats_group)
        
        layout.addLayout(top_layout)
        
        # 日记编辑区域
        journal_edit_layout = QVBoxLayout()
        journal_edit_layout.addWidget(QLabel("今日日记:"))
        
        self.journal_text = QTextEdit()
        self.journal_text.setPlaceholderText("记录今天的想法、感受和经历...")
        journal_edit_layout.addWidget(self.journal_text)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        save_btn = QPushButton("保存日记")
        save_btn.clicked.connect(self.saveJournalEntry)
        button_layout.addWidget(save_btn)
        
        clear_btn = QPushButton("清空")
        clear_btn.clicked.connect(lambda: self.journal_text.clear())
        button_layout.addWidget(clear_btn)
        
        journal_edit_layout.addLayout(button_layout)
        layout.addLayout(journal_edit_layout)
        
        self.tabs.addTab(journal_tab, "📔 日记")
        
    def createTaskManagerTab(self):
        """创建任务管理器标签页"""
        task_tab = QWidget()
        layout = QVBoxLayout(task_tab)
        
        # 任务输入区域
        input_layout = QHBoxLayout()
        self.task_input = QLineEdit()
        self.task_input.setPlaceholderText("输入新任务...")
        self.task_input.returnPressed.connect(self.addTask)
        input_layout.addWidget(self.task_input)
        
        add_btn = QPushButton("添加任务")
        add_btn.clicked.connect(self.addTask)
        input_layout.addWidget(add_btn)
        
        layout.addLayout(input_layout)
        
        # 任务列表
        task_list_layout = QHBoxLayout()
        
        # 待办任务列表
        todo_group = QGroupBox("待办任务")
        todo_layout = QVBoxLayout()
        self.todo_list = QListWidget()
        todo_layout.addWidget(self.todo_list)
        
        todo_btn_layout = QHBoxLayout()
        complete_btn = QPushButton("标记完成")
        complete_btn.clicked.connect(self.completeTask)
        todo_btn_layout.addWidget(complete_btn)
        
        delete_btn = QPushButton("删除任务")
        delete_btn.clicked.connect(self.deleteTask)
        todo_btn_layout.addWidget(delete_btn)
        
        todo_layout.addLayout(todo_btn_layout)
        todo_group.setLayout(todo_layout)
        task_list_layout.addWidget(todo_group)
        
        # 已完成任务列表
        done_group = QGroupBox("已完成任务")
        done_layout = QVBoxLayout()
        self.done_list = QListWidget()
        done_layout.addWidget(self.done_list)
        
        clear_done_btn = QPushButton("清空已完成")
        clear_done_btn.clicked.connect(self.clearCompletedTasks)
        done_layout.addWidget(clear_done_btn)
        
        done_group.setLayout(done_layout)
        task_list_layout.addWidget(done_group)
        
        layout.addLayout(task_list_layout)
        
        # 任务统计
        stats_layout = QHBoxLayout()
        self.task_progress = QProgressBar()
        self.task_progress.setValue(0)
        stats_layout.addWidget(QLabel("完成进度:"))
        stats_layout.addWidget(self.task_progress)
        
        self.task_stats = QLabel("今日任务: 0/0")
        stats_layout.addWidget(self.task_stats)
        
        layout.addLayout(stats_layout)
        
        self.tabs.addTab(task_tab, "✅ 任务管理")
        
    def createMoodTrackerTab(self):
        """创建心情追踪标签页"""
        mood_tab = QWidget()
        layout = QVBoxLayout(mood_tab)
        
        # 心情记录区域
        record_layout = QVBoxLayout()
        record_layout.addWidget(QLabel("当前心情:"))
        
        # 心情选择滑块
        mood_slider_layout = QHBoxLayout()
        mood_slider_layout.addWidget(QLabel("😢"))
        self.mood_slider = QSlider(Qt.Horizontal)
        self.mood_slider.setMinimum(1)
        self.mood_slider.setMaximum(5)
        self.mood_slider.setTickPosition(QSlider.TicksBelow)
        self.mood_slider.setTickInterval(1)
        mood_slider_layout.addWidget(self.mood_slider)
        mood_slider_layout.addWidget(QLabel("😊"))
        
        self.mood_value = QLabel("3 - 一般")
        mood_slider_layout.addWidget(self.mood_value)
        
        self.mood_slider.valueChanged.connect(self.updateMoodValue)
        record_layout.addLayout(mood_slider_layout)
        
        # 心情记录输入
        self.mood_notes = QTextEdit()
        self.mood_notes.setPlaceholderText("记录影响心情的因素...")
        self.mood_notes.setMaximumHeight(100)
        record_layout.addWidget(self.mood_notes)
        
        # 记录心情按钮
        record_btn = QPushButton("记录心情")
        record_btn.clicked.connect(self.recordMood)
        record_layout.addWidget(record_btn)
        
        layout.addLayout(record_layout)
        
        # 心情历史
        history_group = QGroupBox("心情历史")
        history_layout = QVBoxLayout()
        self.mood_history = QListWidget()
        history_layout.addWidget(self.mood_history)
        history_group.setLayout(history_layout)
        layout.addWidget(history_group)
        
        self.tabs.addTab(mood_tab, "😊 心情追踪")
        
    def createMindfulnessTab(self):
        """创建正念冥想标签页"""
        mindfulness_tab = QWidget()
        layout = QVBoxLayout(mindfulness_tab)
        
        # 冥想计时器
        timer_group = QGroupBox("冥想计时器")
        timer_layout = QVBoxLayout()
        
        # 时间显示
        self.meditation_timer = QLabel("00:00")
        self.meditation_timer.setAlignment(Qt.AlignCenter)
        self.meditation_timer.setFont(QFont("Arial", 48, QFont.Bold))
        timer_layout.addWidget(self.meditation_timer)
        
        # 控制按钮
        timer_control_layout = QHBoxLayout()
        self.start_meditation_btn = QPushButton("开始冥想")
        self.start_meditation_btn.clicked.connect(self.startMeditation)
        timer_control_layout.addWidget(self.start_meditation_btn)
        
        self.pause_meditation_btn = QPushButton("暂停")
        self.pause_meditation_btn.clicked.connect(self.pauseMeditation)
        self.pause_meditation_btn.setEnabled(False)
        timer_control_layout.addWidget(self.pause_meditation_btn)
        
        self.reset_meditation_btn = QPushButton("重置")
        self.reset_meditation_btn.clicked.connect(self.resetMeditation)
        timer_control_layout.addWidget(self.reset_meditation_btn)
        
        timer_layout.addLayout(timer_control_layout)
        
        # 时间设置
        time_setting_layout = QHBoxLayout()
        time_setting_layout.addWidget(QLabel("冥想时长(分钟):"))
        self.meditation_duration = QSpinBox()
        self.meditation_duration.setRange(1, 60)
        self.meditation_duration.setValue(10)
        time_setting_layout.addWidget(self.meditation_duration)
        time_setting_layout.addStretch()
        
        timer_layout.addLayout(time_setting_layout)
        timer_group.setLayout(timer_layout)
        layout.addWidget(timer_group)
        
        # 引导语
        guide_group = QGroupBox("冥想引导")
        guide_layout = QVBoxLayout()
        self.guide_text = QTextEdit()
        self.guide_text.setReadOnly(True)
        self.guide_text.setText("选择一个冥想时长，然后点击'开始冥想'。\n\n深呼吸，放松身体，将注意力集中在呼吸上。")
        guide_layout.addWidget(self.guide_text)
        guide_group.setLayout(guide_layout)
        layout.addWidget(guide_group)
        
        # 冥想统计
        stats_layout = QHBoxLayout()
        stats_layout.addWidget(QLabel("今日冥想: 0分钟"))
        stats_layout.addWidget(QLabel("本周冥想: 0分钟"))
        stats_layout.addWidget(QLabel("总冥想时间: 0分钟"))
        layout.addLayout(stats_layout)
        
        self.tabs.addTab(mindfulness_tab, "🧘 正念冥想")
        
    def createProductivityTab(self):
        """创建生产力工具标签页"""
        productivity_tab = QWidget()
        layout = QVBoxLayout(productivity_tab)
        
        # 番茄工作法
        pomodoro_group = QGroupBox("番茄工作法")
        pomodoro_layout = QVBoxLayout()
        
        # 时间显示
        self.pomodoro_timer = QLabel("25:00")
        self.pomodoro_timer.setAlignment(Qt.AlignCenter)
        self.pomodoro_timer.setFont(QFont("Arial", 36, QFont.Bold))
        pomodoro_layout.addWidget(self.pomodoro_timer)
        
        # 控制按钮
        pomodoro_control_layout = QHBoxLayout()
        self.start_pomodoro_btn = QPushButton("开始番茄钟")
        self.start_pomodoro_btn.clicked.connect(self.startPomodoro)
        pomodoro_control_layout.addWidget(self.start_pomodoro_btn)
        
        self.pause_pomodoro_btn = QPushButton("暂停")
        self.pause_pomodoro_btn.clicked.connect(self.pausePomodoro)
        self.pause_pomodoro_btn.setEnabled(False)
        pomodoro_control_layout.addWidget(self.pause_pomodoro_btn)
        
        self.reset_pomodoro_btn = QPushButton("重置")
        self.reset_pomodoro_btn.clicked.connect(self.resetPomodoro)
        pomodoro_control_layout.addWidget(self.reset_pomodoro_btn)
        
        pomodoro_layout.addLayout(pomodoro_control_layout)
        
        # 番茄钟设置
        pomodoro_setting_layout = QHBoxLayout()
        pomodoro_setting_layout.addWidget(QLabel("工作时间(分钟):"))
        self.work_duration = QSpinBox()
        self.work_duration.setRange(5, 60)
        self.work_duration.setValue(25)
        pomodoro_setting_layout.addWidget(self.work_duration)
        
        pomodoro_setting_layout.addWidget(QLabel("休息时间(分钟):"))
        self.break_duration = QSpinBox()
        self.break_duration.setRange(1, 30)
        self.break_duration.setValue(5)
        pomodoro_setting_layout.addWidget(self.break_duration)
        
        pomodoro_layout.addLayout(pomodoro_setting_layout)
        pomodoro_group.setLayout(pomodoro_layout)
        layout.addWidget(pomodoro_group)
        
        # 激励语录
        quote_group = QGroupBox("激励语录")
        quote_layout = QVBoxLayout()
        self.quote_text = QTextEdit()
        self.quote_text.setReadOnly(True)
        self.quote_text.setMaximumHeight(80)
        quote_layout.addWidget(self.quote_text)
        
        new_quote_btn = QPushButton("新语录")
        new_quote_btn.clicked.connect(self.showRandomQuote)
        quote_layout.addWidget(new_quote_btn)
        
        quote_group.setLayout(quote_layout)
        layout.addWidget(quote_group)
        
        self.tabs.addTab(productivity_tab, "⏱️ 生产力工具")
        
    def createSettingsTab(self):
        """创建设置标签页"""
        settings_tab = QWidget()
        layout = QVBoxLayout(settings_tab)
        
        # 数据管理
        data_group = QGroupBox("数据管理")
        data_layout = QVBoxLayout()
        
        backup_btn = QPushButton("备份数据")
        backup_btn.clicked.connect(self.backupData)
        data_layout.addWidget(backup_btn)
        
        restore_btn = QPushButton("恢复数据")
        restore_btn.clicked.connect(self.restoreData)
        data_layout.addWidget(restore_btn)
        
        clear_btn = QPushButton("清除所有数据")
        clear_btn.clicked.connect(self.clearAllData)
        data_layout.addWidget(clear_btn)
        
        data_group.setLayout(data_layout)
        layout.addWidget(data_group)
        
        # 个性化设置
        personalization_group = QGroupBox("个性化设置")
        personalization_layout = QVBoxLayout()
        
        theme_layout = QHBoxLayout()
        theme_layout.addWidget(QLabel("主题:"))
        self.theme_selector = QComboBox()
        self.theme_selector.addItems(["浅色", "深色", "蓝色", "绿色"])
        theme_layout.addWidget(self.theme_selector)
        personalization_layout.addLayout(theme_layout)
        
        self.auto_save_check = QCheckBox("启用自动保存")
        self.auto_save_check.setChecked(True)
        personalization_layout.addWidget(self.auto_save_check)
        
        personalization_group.setLayout(personalization_layout)
        layout.addWidget(personalization_group)
        
        layout.addStretch()
        
        self.tabs.addTab(settings_tab, "⚙️ 设置")
        
    # 日记功能方法
    def saveJournalEntry(self):
        date = self.journal_date.selectedDate().toString("yyyy-MM-dd")
        content = self.journal_text.toPlainText()
        
        if not content.strip():
            QMessageBox.warning(self, "警告", "日记内容不能为空!")
            return
            
        self.journal_entries[date] = content
        self.statusBar().showMessage(f"日记已保存: {date}")
        self.updateJournalStats()
        
    def loadJournalEntry(self, date):
        date_str = date.toString("yyyy-MM-dd")
        content = self.journal_entries.get(date_str, "")
        self.journal_text.setPlainText(content)
        
    def updateJournalStats(self):
        total = len(self.journal_entries)
        current_month = QDate.currentDate().toString("yyyy-MM")
        month_count = sum(1 for date in self.journal_entries.keys() if date.startswith(current_month))
        self.journal_stats.setText(f"总日记数: {total}\n本月日记: {month_count}")
        
    # 任务管理功能方法
    def addTask(self):
        task_text = self.task_input.text().strip()
        if not task_text:
            return
            
        self.todo_list.addItem(task_text)
        self.task_input.clear()
        self.updateTaskStats()
        
    def completeTask(self):
        current_row = self.todo_list.currentRow()
        if current_row >= 0:
            item = self.todo_list.takeItem(current_row)
            self.done_list.addItem(item)
            self.updateTaskStats()
            
    def deleteTask(self):
        current_row = self.todo_list.currentRow()
        if current_row >= 0:
            self.todo_list.takeItem(current_row)
            self.updateTaskStats()
            
    def clearCompletedTasks(self):
        self.done_list.clear()
        self.updateTaskStats()
        
    def updateTaskStats(self):
        total_tasks = self.todo_list.count() + self.done_list.count()
        completed_tasks = self.done_list.count()
        
        if total_tasks > 0:
            progress = int((completed_tasks / total_tasks) * 100)
        else:
            progress = 0
            
        self.task_progress.setValue(progress)
        self.task_stats.setText(f"今日任务: {completed_tasks}/{total_tasks}")
        
    # 心情追踪功能方法
    def updateMoodValue(self, value):
        mood_labels = {
            1: "1 - 非常差",
            2: "2 - 较差",
            3: "3 - 一般",
            4: "4 - 较好",
            5: "5 - 非常好"
        }
        self.mood_value.setText(mood_labels[value])
        
    def recordMood(self):
        mood_value = self.mood_slider.value()
        notes = self.mood_notes.toPlainText()
        date_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        
        mood_entry = f"{date_time} - 心情: {mood_value}/5"
        if notes:
            mood_entry += f" - {notes}"
            
        self.mood_history.addItem(mood_entry)
        self.mood_notes.clear()
        self.statusBar().showMessage("心情已记录")
        
    # 正念冥想功能方法
    def startMeditation(self):
        self.meditation_seconds = self.meditation_duration.value() * 60
        self.meditation_timer.setText(f"{self.meditation_duration.value():02d}:00")
        
        self.start_meditation_btn.setEnabled(False)
        self.pause_meditation_btn.setEnabled(True)
        
        self.meditation_timer_obj = QTimer()
        self.meditation_timer_obj.timeout.connect(self.updateMeditationTimer)
        self.meditation_timer_obj.start(1000)
        
    def pauseMeditation(self):
        if self.meditation_timer_obj.isActive():
            self.meditation_timer_obj.stop()
            self.pause_meditation_btn.setText("继续")
        else:
            self.meditation_timer_obj.start(1000)
            self.pause_meditation_btn.setText("暂停")
            
    def resetMeditation(self):
        if hasattr(self, 'meditation_timer_obj'):
            self.meditation_timer_obj.stop()
            
        self.meditation_timer.setText("00:00")
        self.start_meditation_btn.setEnabled(True)
        self.pause_meditation_btn.setEnabled(False)
        self.pause_meditation_btn.setText("暂停")
        
    def updateMeditationTimer(self):
        self.meditation_seconds -= 1
        if self.meditation_seconds <= 0:
            self.meditation_timer_obj.stop()
            self.meditation_timer.setText("时间到!")
            QMessageBox.information(self, "冥想完成", "恭喜你完成了一次冥想!")
            self.resetMeditation()
        else:
            minutes = self.meditation_seconds // 60
            seconds = self.meditation_seconds % 60
            self.meditation_timer.setText(f"{minutes:02d}:{seconds:02d}")
            
    # 生产力工具功能方法
    def startPomodoro(self):
        self.pomodoro_seconds = self.work_duration.value() * 60
        self.pomodoro_timer.setText(f"{self.work_duration.value():02d}:00")
        
        self.start_pomodoro_btn.setEnabled(False)
        self.pause_pomodoro_btn.setEnabled(True)
        
        self.pomodoro_timer_obj = QTimer()
        self.pomodoro_timer_obj.timeout.connect(self.updatePomodoroTimer)
        self.pomodoro_timer_obj.start(1000)
        
    def pausePomodoro(self):
        if self.pomodoro_timer_obj.isActive():
            self.pomodoro_timer_obj.stop()
            self.pause_pomodoro_btn.setText("继续")
        else:
            self.pomodoro_timer_obj.start(1000)
            self.pause_pomodoro_btn.setText("暂停")
            
    def resetPomodoro(self):
        if hasattr(self, 'pomodoro_timer_obj'):
            self.pomodoro_timer_obj.stop()
            
        self.pomodoro_timer.setText("25:00")
        self.start_pomodoro_btn.setEnabled(True)
        self.pause_pomodoro_btn.setEnabled(False)
        self.pause_pomodoro_btn.setText("暂停")
        
    def updatePomodoroTimer(self):
        self.pomodoro_seconds -= 1
        if self.pomodoro_seconds <= 0:
            self.pomodoro_timer_obj.stop()
            self.pomodoro_timer.setText("时间到!")
            QMessageBox.information(self, "番茄钟结束", "工作时间结束，该休息了!")
            self.resetPomodoro()
        else:
            minutes = self.pomodoro_seconds // 60
            seconds = self.pomodoro_seconds % 60
            self.pomodoro_timer.setText(f"{minutes:02d}:{seconds:02d}")
            
    def showRandomQuote(self):
        quotes = [
            "成功的秘诀在于始终如一地坚持自己的目标。",
            "每一天都是一个新的开始。",
            "不要等待机会，而要创造机会。",
            "行动是治愈恐惧的良药。",
            "只有不断努力，才能看起来毫不费力。",
            "相信自己，你已经走了一半的路。",
            "小小的进步也是进步。",
            "专注当下，未来自会到来。",
            "你的潜力超乎你的想象。",
            "坚持不是一次长跑，而是许多次短跑。"
        ]
        quote = random.choice(quotes)
        self.quote_text.setText(quote)
        
    # 数据管理方法
    def loadData(self):
        """加载保存的数据"""
        self.data_file = "pleasure_system_data.json"
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.journal_entries = data.get('journal_entries', {})
                    self.todo_tasks = data.get('todo_tasks', [])
                    self.done_tasks = data.get('done_tasks', [])
                    self.mood_history_data = data.get('mood_history', [])
            else:
                self.journal_entries = {}
                self.todo_tasks = []
                self.done_tasks = []
                self.mood_history_data = []
                
            # 更新UI以反映加载的数据
            self.updateUIFromData()
            
        except Exception as e:
            QMessageBox.warning(self, "错误", f"加载数据时出错: {str(e)}")
            self.journal_entries = {}
            self.todo_tasks = []
            self.done_tasks = []
            self.mood_history_data = []
            
    def saveData(self):
        """保存数据到文件"""
        if not hasattr(self, 'auto_save_check') or self.auto_save_check.isChecked():
            try:
                # 从UI收集数据
                self.collectDataFromUI()
                
                data = {
                    'journal_entries': self.journal_entries,
                    'todo_tasks': self.todo_tasks,
                    'done_tasks': self.done_tasks,
                    'mood_history': self.mood_history_data
                }
                
                with open(self.data_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                    
                self.statusBar().showMessage("数据已自动保存")
            except Exception as e:
                QMessageBox.warning(self, "错误", f"保存数据时出错: {str(e)}")
                
    def collectDataFromUI(self):
        """从UI收集数据"""
        # 收集任务数据
        self.todo_tasks = []
        for i in range(self.todo_list.count()):
            self.todo_tasks.append(self.todo_list.item(i).text())
            
        self.done_tasks = []
        for i in range(self.done_list.count()):
            self.done_tasks.append(self.done_list.item(i).text())
            
        # 收集心情历史数据
        self.mood_history_data = []
        for i in range(self.mood_history.count()):
            self.mood_history_data.append(self.mood_history.item(i).text())
            
    def updateUIFromData(self):
        """用加载的数据更新UI"""
        # 更新日记数据
        self.updateJournalStats()
        
        # 更新任务数据
        for task in self.todo_tasks:
            self.todo_list.addItem(task)
            
        for task in self.done_tasks:
            self.done_list.addItem(task)
            
        self.updateTaskStats()
        
        # 更新心情历史数据
        for mood_entry in self.mood_history_data:
            self.mood_history.addItem(mood_entry)
            
    def backupData(self):
        """备份数据"""
        try:
            backup_file = f"pleasure_system_backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(backup_file, 'w', encoding='utf-8') as f:
                self.collectDataFromUI()
                data = {
                    'journal_entries': self.journal_entries,
                    'todo_tasks': self.todo_tasks,
                    'done_tasks': self.done_tasks,
                    'mood_history': self.mood_history_data
                }
                json.dump(data, f, ensure_ascii=False, indent=2)
                
            QMessageBox.information(self, "备份成功", f"数据已备份到: {backup_file}")
        except Exception as e:
            QMessageBox.warning(self, "备份失败", f"备份数据时出错: {str(e)}")
            
    def restoreData(self):
        """恢复数据"""
        try:
            from PyQt5.QtWidgets import QFileDialog
            file_name, _ = QFileDialog.getOpenFileName(self, "选择备份文件", "", "JSON文件 (*.json)")
            if file_name:
                with open(file_name, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                # 清除当前数据
                self.journal_entries = {}
                self.todo_tasks = []
                self.done_tasks = []
                self.mood_history_data = []
                
                # 加载备份数据
                self.journal_entries = data.get('journal_entries', {})
                self.todo_tasks = data.get('todo_tasks', [])
                self.done_tasks = data.get('done_tasks', [])
                self.mood_history_data = data.get('mood_history', [])
                
                # 更新UI
                self.journal_text.clear()
                self.todo_list.clear()
                self.done_list.clear()
                self.mood_history.clear()
                
                self.updateUIFromData()
                
                QMessageBox.information(self, "恢复成功", "数据已从备份恢复")
        except Exception as e:
            QMessageBox.warning(self, "恢复失败", f"恢复数据时出错: {str(e)}")
            
    def clearAllData(self):
        """清除所有数据"""
        reply = QMessageBox.question(self, "确认清除", 
                                    "这将永久删除所有数据，确定要继续吗?",
                                    QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.journal_entries = {}
            self.todo_tasks = []
            self.done_tasks = []
            self.mood_history_data = []
            
            self.journal_text.clear()
            self.todo_list.clear()
            self.done_list.clear()
            self.mood_history.clear()
            
            if os.path.exists(self.data_file):
                os.remove(self.data_file)
                
            self.updateJournalStats()
            self.updateTaskStats()
            
            QMessageBox.information(self, "清除完成", "所有数据已清除")
            
    def closeEvent(self, event):
        """应用关闭时保存数据"""
        self.saveData()
        event.accept()

def main():
    app = QApplication(sys.argv)
    
    # 设置应用信息
    app.setApplicationName("愉悦自我系统")
    app.setApplicationVersion("1.0")
    
    # 创建并显示主窗口
    window = PleasureSystem()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()