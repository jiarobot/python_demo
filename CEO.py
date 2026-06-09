import sys
import json
import csv
import math
from datetime import datetime, timedelta
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, 
                             QHBoxLayout, QGroupBox, QLabel, QLineEdit, QTextEdit, 
                             QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
                             QComboBox, QDateEdit, QSpinBox, QMessageBox, QFileDialog,
                             QGridLayout, QSplitter, QListWidget, QProgressBar, QFrame,
                             QCheckBox, QSlider, QTreeWidget, QTreeWidgetItem, QToolBar,
                             QStatusBar, QAction, QToolButton, QMenu, QDialog, QDialogButtonBox,
                             QFormLayout, QDoubleSpinBox, QSizePolicy, QScrollArea, QStyleFactory)
from PyQt5.QtCore import Qt, QDate, QSize, QTimer
from PyQt5.QtGui import QFont, QColor, QPainter, QPalette, QIcon, QPixmap, QLinearGradient, QBrush


class CustomProgressWidget(QWidget):
    """自定义进度指示器，用于替代QtChart的可视化"""
    def __init__(self, value=0, maximum=100, text=None, parent=None):
        super().__init__(parent)
        self.value = value
        self.maximum = maximum
        self.text = text or f"{value}/{maximum}"
        self.setMinimumHeight(30)
        self.setMinimumWidth(100)
        
    def setValue(self, value):
        self.value = value
        self.update()
        
    def setMaximum(self, maximum):
        self.maximum = maximum
        self.update()
        
    def setText(self, text):
        self.text = text
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 绘制背景
        bg_rect = self.rect().adjusted(2, 2, -2, -2)
        painter.setPen(QColor(200, 200, 200))
        painter.setBrush(QColor(240, 240, 240))
        painter.drawRoundedRect(bg_rect, 5, 5)
        
        # 计算进度条宽度
        if self.maximum > 0:
            progress_width = int(bg_rect.width() * self.value / self.maximum)
            progress_rect = bg_rect.adjusted(0, 0, - (bg_rect.width() - progress_width), 0)
            
            # 创建渐变
            gradient = QLinearGradient(progress_rect.topLeft(), progress_rect.topRight())
            if self.value / self.maximum < 0.3:
                gradient.setColorAt(0, QColor(255, 100, 100))
                gradient.setColorAt(1, QColor(220, 70, 70))
            elif self.value / self.maximum < 0.7:
                gradient.setColorAt(0, QColor(255, 200, 100))
                gradient.setColorAt(1, QColor(255, 170, 50))
            else:
                gradient.setColorAt(0, QColor(100, 220, 100))
                gradient.setColorAt(1, QColor(70, 190, 70))
                
            painter.setBrush(QBrush(gradient))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(progress_rect, 5, 5)
        
        # 绘制文本
        painter.setPen(QColor(0, 0, 0))
        painter.drawText(bg_rect, Qt.AlignCenter, self.text)
        
        painter.end()


class SWOTAnalysisWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        
    def initUI(self):
        main_layout = QVBoxLayout()
        
        # 标题
        title_label = QLabel("SWOT分析")
        title_label.setStyleSheet("font-size: 16pt; font-weight: bold; margin: 10px;")
        main_layout.addWidget(title_label)
        
        # SWOT矩阵
        matrix_layout = QGridLayout()
        
        # Strengths
        strengths_group = QGroupBox("优势 (Strengths)")
        strengths_layout = QVBoxLayout()
        self.strengths_list = QListWidget()
        self.strengths_list.setAlternatingRowColors(True)
        strengths_add_btn = QPushButton("添加优势")
        strengths_add_btn.clicked.connect(lambda: self.add_swot_item("strengths"))
        strengths_layout.addWidget(self.strengths_list)
        strengths_layout.addWidget(strengths_add_btn)
        strengths_group.setLayout(strengths_layout)
        
        # Weaknesses
        weaknesses_group = QGroupBox("劣势 (Weaknesses)")
        weaknesses_layout = QVBoxLayout()
        self.weaknesses_list = QListWidget()
        self.weaknesses_list.setAlternatingRowColors(True)
        weaknesses_add_btn = QPushButton("添加劣势")
        weaknesses_add_btn.clicked.connect(lambda: self.add_swot_item("weaknesses"))
        weaknesses_layout.addWidget(self.weaknesses_list)
        weaknesses_layout.addWidget(weaknesses_add_btn)
        weaknesses_group.setLayout(weaknesses_layout)
        
        # Opportunities
        opportunities_group = QGroupBox("机会 (Opportunities)")
        opportunities_layout = QVBoxLayout()
        self.opportunities_list = QListWidget()
        self.opportunities_list.setAlternatingRowColors(True)
        opportunities_add_btn = QPushButton("添加机会")
        opportunities_add_btn.clicked.connect(lambda: self.add_swot_item("opportunities"))
        opportunities_layout.addWidget(self.opportunities_list)
        opportunities_layout.addWidget(opportunities_add_btn)
        opportunities_group.setLayout(opportunities_layout)
        
        # Threats
        threats_group = QGroupBox("威胁 (Threats)")
        threats_layout = QVBoxLayout()
        self.threats_list = QListWidget()
        self.threats_list.setAlternatingRowColors(True)
        threats_add_btn = QPushButton("添加威胁")
        threats_add_btn.clicked.connect(lambda: self.add_swot_item("threats"))
        threats_layout.addWidget(self.threats_list)
        threats_layout.addWidget(threats_add_btn)
        threats_group.setLayout(threats_layout)
        
        # 添加矩阵到布局
        matrix_layout.addWidget(strengths_group, 0, 0)
        matrix_layout.addWidget(weaknesses_group, 0, 1)
        matrix_layout.addWidget(opportunities_group, 1, 0)
        matrix_layout.addWidget(threats_group, 1, 1)
        
        main_layout.addLayout(matrix_layout)
        
        # 分析按钮
        button_layout = QHBoxLayout()
        analyze_btn = QPushButton("生成SWOT分析报告")
        analyze_btn.clicked.connect(self.generate_swot_report)
        button_layout.addWidget(analyze_btn)
        
        save_btn = QPushButton("保存分析")
        save_btn.clicked.connect(self.save_analysis)
        button_layout.addWidget(save_btn)
        
        load_btn = QPushButton("加载分析")
        load_btn.clicked.connect(self.load_analysis)
        button_layout.addWidget(load_btn)
        
        main_layout.addLayout(button_layout)
        
        self.setLayout(main_layout)
    
    def add_swot_item(self, category):
        dialog = QDialog(self)
        dialog.setWindowTitle(f"添加{self.get_category_name(category)}")
        dialog.setModal(True)
        
        layout = QVBoxLayout()
        
        form_layout = QFormLayout()
        item_edit = QLineEdit()
        form_layout.addRow("项目:", item_edit)
        
        impact_combo = QComboBox()
        impact_combo.addItems(["高", "中", "低"])
        form_layout.addRow("影响程度:", impact_combo)
        
        probability_combo = QComboBox()
        probability_combo.addItems(["高", "中", "低"])
        form_layout.addRow("发生概率:", probability_combo)
        
        layout.addLayout(form_layout)
        
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        
        dialog.setLayout(layout)
        
        if dialog.exec_() == QDialog.Accepted and item_edit.text().strip():
            item_text = f"{item_edit.text()} [影响: {impact_combo.currentText()}, 概率: {probability_combo.currentText()}]"
            
            if category == "strengths":
                self.strengths_list.addItem(item_text)
            elif category == "weaknesses":
                self.weaknesses_list.addItem(item_text)
            elif category == "opportunities":
                self.opportunities_list.addItem(item_text)
            elif category == "threats":
                self.threats_list.addItem(item_text)
    
    def get_category_name(self, category):
        names = {
            "strengths": "优势",
            "weaknesses": "劣势",
            "opportunities": "机会",
            "threats": "威胁"
        }
        return names.get(category, "")
    
    def generate_swot_report(self):
        report = "SWOT分析报告\n"
        report += "生成时间: " + datetime.now().strftime("%Y-%m-%d %H:%M") + "\n\n"
        
        report += "优势 (Strengths):\n"
        for i in range(self.strengths_list.count()):
            report += f"  • {self.strengths_list.item(i).text()}\n"
        
        report += "\n劣势 (Weaknesses):\n"
        for i in range(self.weaknesses_list.count()):
            report += f"  • {self.weaknesses_list.item(i).text()}\n"
        
        report += "\n机会 (Opportunities):\n"
        for i in range(self.opportunities_list.count()):
            report += f"  • {self.opportunities_list.item(i).text()}\n"
        
        report += "\n威胁 (Threats):\n"
        for i in range(self.threats_list.count()):
            report += f"  • {self.threats_list.item(i).text()}\n"
        
        # 显示报告
        self.show_report_dialog(report)
    
    def show_report_dialog(self, report):
        dialog = QDialog(self)
        dialog.setWindowTitle("SWOT分析报告")
        dialog.setMinimumSize(500, 600)
        
        layout = QVBoxLayout()
        
        report_edit = QTextEdit()
        report_edit.setPlainText(report)
        report_edit.setReadOnly(True)
        layout.addWidget(report_edit)
        
        button_box = QDialogButtonBox(QDialogButtonBox.Ok)
        button_box.accepted.connect(dialog.accept)
        layout.addWidget(button_box)
        
        dialog.setLayout(layout)
        dialog.exec_()
    
    def save_analysis(self):
        data = {
            'strengths': [self.strengths_list.item(i).text() for i in range(self.strengths_list.count())],
            'weaknesses': [self.weaknesses_list.item(i).text() for i in range(self.weaknesses_list.count())],
            'opportunities': [self.opportunities_list.item(i).text() for i in range(self.opportunities_list.count())],
            'threats': [self.threats_list.item(i).text() for i in range(self.threats_list.count())]
        }
        
        file_path, _ = QFileDialog.getSaveFileName(self, "保存SWOT分析", "", "JSON Files (*.json)")
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=4)
                QMessageBox.information(self, "成功", "SWOT分析已保存!")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"保存失败: {str(e)}")
    
    def load_analysis(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "加载SWOT分析", "", "JSON Files (*.json)")
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                self.strengths_list.clear()
                for item in data.get('strengths', []):
                    self.strengths_list.addItem(item)
                
                self.weaknesses_list.clear()
                for item in data.get('weaknesses', []):
                    self.weaknesses_list.addItem(item)
                
                self.opportunities_list.clear()
                for item in data.get('opportunities', []):
                    self.opportunities_list.addItem(item)
                
                self.threats_list.clear()
                for item in data.get('threats', []):
                    self.threats_list.addItem(item)
                
                QMessageBox.information(self, "成功", "SWOT分析已加载!")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"加载失败: {str(e)}")


class StrategicGoalsWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.goals = []
        self.initUI()
        
    def initUI(self):
        main_layout = QVBoxLayout()
        
        # 标题
        title_label = QLabel("战略目标管理")
        title_label.setStyleSheet("font-size: 16pt; font-weight: bold; margin: 10px;")
        main_layout.addWidget(title_label)
        
        # 目标分类筛选
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("筛选:"))
        
        category_filter = QComboBox()
        category_filter.addItems(["所有类别", "财务", "客户", "内部流程", "学习与成长"])
        category_filter.currentTextChanged.connect(self.filter_goals)
        filter_layout.addWidget(category_filter)
        
        priority_filter = QComboBox()
        priority_filter.addItems(["所有优先级", "高", "中", "低"])
        priority_filter.currentTextChanged.connect(self.filter_goals)
        filter_layout.addWidget(priority_filter)
        
        filter_layout.addStretch()
        main_layout.addLayout(filter_layout)
        
        # 目标表格
        self.goals_table = QTableWidget()
        self.goals_table.setColumnCount(8)
        self.goals_table.setHorizontalHeaderLabels(["目标名称", "类别", "优先级", "截止日期", "进度", "负责人", "状态", "操作"])
        self.goals_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.goals_table.setAlternatingRowColors(True)
        main_layout.addWidget(self.goals_table)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        
        add_btn = QPushButton("添加目标")
        add_btn.clicked.connect(self.add_goal_dialog)
        button_layout.addWidget(add_btn)
        
        export_btn = QPushButton("导出目标")
        export_btn.clicked.connect(self.export_goals)
        button_layout.addWidget(export_btn)
        
        gantt_btn = QPushButton("查看甘特图")
        gantt_btn.clicked.connect(self.show_gantt_chart)
        button_layout.addWidget(gantt_btn)
        
        button_layout.addStretch()
        main_layout.addLayout(button_layout)
        
        self.setLayout(main_layout)
    
    def add_goal_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("添加战略目标")
        dialog.setModal(True)
        
        layout = QVBoxLayout()
        
        form_layout = QFormLayout()
        
        name_edit = QLineEdit()
        form_layout.addRow("目标名称:", name_edit)
        
        category_combo = QComboBox()
        category_combo.addItems(["财务", "客户", "内部流程", "学习与成长"])
        form_layout.addRow("类别:", category_combo)
        
        priority_combo = QComboBox()
        priority_combo.addItems(["高", "中", "低"])
        form_layout.addRow("优先级:", priority_combo)
        
        deadline_edit = QDateEdit()
        deadline_edit.setDate(QDate.currentDate().addMonths(6))
        deadline_edit.setCalendarPopup(True)
        form_layout.addRow("截止日期:", deadline_edit)
        
        owner_edit = QLineEdit()
        form_layout.addRow("负责人:", owner_edit)
        
        progress_spin = QSpinBox()
        progress_spin.setRange(0, 100)
        progress_spin.setSuffix("%")
        form_layout.addRow("进度:", progress_spin)
        
        description_edit = QTextEdit()
        description_edit.setMaximumHeight(100)
        form_layout.addRow("描述:", description_edit)
        
        layout.addLayout(form_layout)
        
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        
        dialog.setLayout(layout)
        
        if dialog.exec_() == QDialog.Accepted and name_edit.text().strip():
            goal = {
                'name': name_edit.text(),
                'category': category_combo.currentText(),
                'priority': priority_combo.currentText(),
                'deadline': deadline_edit.date().toString("yyyy-MM-dd"),
                'owner': owner_edit.text(),
                'progress': progress_spin.value(),
                'description': description_edit.toPlainText(),
                'status': "进行中" if progress_spin.value() < 100 else "已完成"
            }
            
            self.goals.append(goal)
            self.update_goals_table()
    
    def update_goals_table(self):
        self.goals_table.setRowCount(len(self.goals))
        
        for row, goal in enumerate(self.goals):
            self.goals_table.setItem(row, 0, QTableWidgetItem(goal['name']))
            self.goals_table.setItem(row, 1, QTableWidgetItem(goal['category']))
            self.goals_table.setItem(row, 2, QTableWidgetItem(goal['priority']))
            self.goals_table.setItem(row, 3, QTableWidgetItem(goal['deadline']))
            
            # 进度条
            progress_widget = CustomProgressWidget(goal['progress'], 100, f"{goal['progress']}%")
            self.goals_table.setCellWidget(row, 4, progress_widget)
            
            self.goals_table.setItem(row, 5, QTableWidgetItem(goal['owner']))
            self.goals_table.setItem(row, 6, QTableWidgetItem(goal['status']))
            
            # 操作按钮
            button_widget = QWidget()
            button_layout = QHBoxLayout()
            button_layout.setContentsMargins(5, 2, 5, 2)
            
            edit_btn = QPushButton("编辑")
            edit_btn.clicked.connect(lambda _, r=row: self.edit_goal(r))
            button_layout.addWidget(edit_btn)
            
            delete_btn = QPushButton("删除")
            delete_btn.clicked.connect(lambda _, r=row: self.delete_goal(r))
            button_layout.addWidget(delete_btn)
            
            button_widget.setLayout(button_layout)
            self.goals_table.setCellWidget(row, 7, button_widget)
    
    def edit_goal(self, row):
        dialog = QDialog(self)
        dialog.setWindowTitle("编辑战略目标")
        dialog.setModal(True)
        
        layout = QVBoxLayout()
        
        form_layout = QFormLayout()
        
        name_edit = QLineEdit(self.goals[row]['name'])
        form_layout.addRow("目标名称:", name_edit)
        
        category_combo = QComboBox()
        category_combo.addItems(["财务", "客户", "内部流程", "学习与成长"])
        category_combo.setCurrentText(self.goals[row]['category'])
        form_layout.addRow("类别:", category_combo)
        
        priority_combo = QComboBox()
        priority_combo.addItems(["高", "中", "低"])
        priority_combo.setCurrentText(self.goals[row]['priority'])
        form_layout.addRow("优先级:", priority_combo)
        
        deadline = QDate.fromString(self.goals[row]['deadline'], "yyyy-MM-dd")
        deadline_edit = QDateEdit(deadline)
        deadline_edit.setCalendarPopup(True)
        form_layout.addRow("截止日期:", deadline_edit)
        
        owner_edit = QLineEdit(self.goals[row]['owner'])
        form_layout.addRow("负责人:", owner_edit)
        
        progress_spin = QSpinBox()
        progress_spin.setRange(0, 100)
        progress_spin.setSuffix("%")
        progress_spin.setValue(self.goals[row]['progress'])
        form_layout.addRow("进度:", progress_spin)
        
        description_edit = QTextEdit(self.goals[row]['description'])
        description_edit.setMaximumHeight(100)
        form_layout.addRow("描述:", description_edit)
        
        layout.addLayout(form_layout)
        
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        
        dialog.setLayout(layout)
        
        if dialog.exec_() == QDialog.Accepted and name_edit.text().strip():
            self.goals[row] = {
                'name': name_edit.text(),
                'category': category_combo.currentText(),
                'priority': priority_combo.currentText(),
                'deadline': deadline_edit.date().toString("yyyy-MM-dd"),
                'owner': owner_edit.text(),
                'progress': progress_spin.value(),
                'description': description_edit.toPlainText(),
                'status': "进行中" if progress_spin.value() < 100 else "已完成"
            }
            
            self.update_goals_table()
    
    def delete_goal(self, row):
        reply = QMessageBox.question(self, "确认删除", "确定要删除这个目标吗?",
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QDialog.Yes:
            self.goals.pop(row)
            self.update_goals_table()
    
    def filter_goals(self, text):
        # 这里实现筛选逻辑
        self.update_goals_table()
    
    def export_goals(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "导出目标", "", "CSV Files (*.csv)")
        if file_path:
            try:
                with open(file_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(["目标名称", "类别", "优先级", "截止日期", "进度", "负责人", "状态", "描述"])
                    
                    for goal in self.goals:
                        writer.writerow([
                            goal['name'],
                            goal['category'],
                            goal['priority'],
                            goal['deadline'],
                            goal['progress'],
                            goal['owner'],
                            goal['status'],
                            goal['description']
                        ])
                
                QMessageBox.information(self, "成功", "目标已导出到CSV文件!")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导出失败: {str(e)}")
    
    def show_gantt_chart(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("战略目标甘特图")
        dialog.setMinimumSize(800, 500)
        
        layout = QVBoxLayout()
        
        # 创建简单的甘特图
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout()
        
        today = QDate.currentDate()
        
        for goal in self.goals:
            goal_frame = QFrame()
            goal_frame.setFrameStyle(QFrame.Box)
            goal_frame.setLineWidth(1)
            
            goal_layout = QHBoxLayout()
            
            # 目标名称
            name_label = QLabel(goal['name'])
            name_label.setMinimumWidth(150)
            goal_layout.addWidget(name_label)
            
            # 时间线
            timeline_widget = QWidget()
            timeline_widget.setMinimumHeight(30)
            timeline_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            goal_layout.addWidget(timeline_widget)
            
            # 进度标签
            progress_label = QLabel(f"{goal['progress']}%")
            progress_label.setMinimumWidth(40)
            goal_layout.addWidget(progress_label)
            
            goal_frame.setLayout(goal_layout)
            scroll_layout.addWidget(goal_frame)
            
            # 自定义绘制时间线
            timeline_widget.paintEvent = lambda event, g=goal, tw=timeline_widget: self.draw_timeline(event, g, tw, today)
        
        scroll_widget.setLayout(scroll_layout)
        scroll_area.setWidget(scroll_widget)
        layout.addWidget(scroll_area)
        
        button_box = QDialogButtonBox(QDialogButtonBox.Ok)
        button_box.accepted.connect(dialog.accept)
        layout.addWidget(button_box)
        
        dialog.setLayout(layout)
        dialog.exec_()
    
    def draw_timeline(self, event, goal, widget, today):
        painter = QPainter(widget)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 绘制背景
        rect = widget.rect().adjusted(2, 2, -2, -2)
        painter.setPen(QColor(200, 200, 200))
        painter.setBrush(QColor(240, 240, 240))
        painter.drawRoundedRect(rect, 3, 3)
        
        # 计算日期范围
        deadline = QDate.fromString(goal['deadline'], "yyyy-MM-dd")
        days_total = today.daysTo(deadline) + 30  # 假设项目开始于30天前
        
        if days_total <= 0:
            return
            
        # 计算进度位置
        progress_width = int(rect.width() * goal['progress'] / 100)
        
        # 绘制进度条
        if goal['progress'] > 0:
            progress_rect = rect.adjusted(0, 0, - (rect.width() - progress_width), 0)
            
            gradient = QLinearGradient(progress_rect.topLeft(), progress_rect.topRight())
            if goal['progress'] < 30:
                gradient.setColorAt(0, QColor(255, 100, 100))
                gradient.setColorAt(1, QColor(220, 70, 70))
            elif goal['progress'] < 70:
                gradient.setColorAt(0, QColor(255, 200, 100))
                gradient.setColorAt(1, QColor(255, 170, 50))
            else:
                gradient.setColorAt(0, QColor(100, 220, 100))
                gradient.setColorAt(1, QColor(70, 190, 70))
                
            painter.setBrush(QBrush(gradient))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(progress_rect, 3, 3)
        
        # 绘制当前日期标记
        days_passed = 30  # 假设项目开始于30天前
        today_pos = int(rect.width() * days_passed / days_total)
        painter.setPen(QColor(0, 0, 255))
        painter.drawLine(rect.left() + today_pos, rect.top(), rect.left() + today_pos, rect.bottom())
        
        painter.end()


class KPITrackingWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.kpis = []
        self.initUI()
        
    def initUI(self):
        main_layout = QVBoxLayout()
        
        # 标题
        title_label = QLabel("KPI绩效指标跟踪")
        title_label.setStyleSheet("font-size: 16pt; font-weight: bold; margin: 10px;")
        main_layout.addWidget(title_label)
        
        # KPI表格
        self.kpi_table = QTableWidget()
        self.kpi_table.setColumnCount(10)
        self.kpi_table.setHorizontalHeaderLabels(["KPI名称", "当前值", "目标值", "进度", "单位", "权重", "负责人", "更新日期", "趋势", "操作"])
        self.kpi_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.kpi_table.setAlternatingRowColors(True)
        main_layout.addWidget(self.kpi_table)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        
        add_btn = QPushButton("添加KPI")
        add_btn.clicked.connect(self.add_kpi_dialog)
        button_layout.addWidget(add_btn)
        
        history_btn = QPushButton("查看历史数据")
        history_btn.clicked.connect(self.show_history)
        button_layout.addWidget(history_btn)
        
        alert_btn = QPushButton("设置预警")
        alert_btn.clicked.connect(self.set_alerts)
        button_layout.addWidget(alert_btn)
        
        button_layout.addStretch()
        main_layout.addLayout(button_layout)
        
        self.setLayout(main_layout)
        
        # 添加示例数据
        self.add_sample_data()
    
    def add_sample_data(self):
        sample_kpis = [
            {
                'name': '市场份额',
                'current': 15.5,
                'target': 20.0,
                'unit': '百分比',
                'weight': 30,
                'owner': '销售部',
                'last_updated': QDate.currentDate().toString("yyyy-MM-dd"),
                'trend': '上升'
            },
            {
                'name': '客户满意度',
                'current': 85,
                'target': 90,
                'unit': '分数',
                'weight': 25,
                'owner': '客服部',
                'last_updated': QDate.currentDate().toString("yyyy-MM-dd"),
                'trend': '稳定'
            },
            {
                'name': '员工流失率',
                'current': 8.2,
                'target': 5.0,
                'unit': '百分比',
                'weight': 20,
                'owner': '人力资源',
                'last_updated': QDate.currentDate().toString("yyyy-MM-dd"),
                'trend': '下降'
            }
        ]
        
        for kpi in sample_kpis:
            kpi['progress'] = min(100, int((kpi['current'] / kpi['target']) * 100)) if kpi['target'] > 0 else 0
            self.kpis.append(kpi)
        
        self.update_kpi_table()
    
    def add_kpi_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("添加KPI指标")
        dialog.setModal(True)
        
        layout = QVBoxLayout()
        
        form_layout = QFormLayout()
        
        name_edit = QLineEdit()
        form_layout.addRow("KPI名称:", name_edit)
        
        current_spin = QDoubleSpinBox()
        current_spin.setRange(0, 10000)
        current_spin.setDecimals(2)
        form_layout.addRow("当前值:", current_spin)
        
        target_spin = QDoubleSpinBox()
        target_spin.setRange(0, 10000)
        target_spin.setDecimals(2)
        form_layout.addRow("目标值:", target_spin)
        
        unit_combo = QComboBox()
        unit_combo.addItems(["百分比", "数值", "金额(万元)", "分数", "其他"])
        form_layout.addRow("单位:", unit_combo)
        
        weight_spin = QSpinBox()
        weight_spin.setRange(0, 100)
        weight_spin.setSuffix("%")
        form_layout.addRow("权重:", weight_spin)
        
        owner_edit = QLineEdit()
        form_layout.addRow("负责人:", owner_edit)
        
        trend_combo = QComboBox()
        trend_combo.addItems(["上升", "下降", "稳定", "波动"])
        form_layout.addRow("趋势:", trend_combo)
        
        layout.addLayout(form_layout)
        
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        
        dialog.setLayout(layout)
        
        if dialog.exec_() == QDialog.Accepted and name_edit.text().strip():
            current = current_spin.value()
            target = target_spin.value()
            progress = min(100, int((current / target) * 100)) if target > 0 else 0
            
            kpi = {
                'name': name_edit.text(),
                'current': current,
                'target': target,
                'progress': progress,
                'unit': unit_combo.currentText(),
                'weight': weight_spin.value(),
                'owner': owner_edit.text(),
                'last_updated': QDate.currentDate().toString("yyyy-MM-dd"),
                'trend': trend_combo.currentText()
            }
            
            self.kpis.append(kpi)
            self.update_kpi_table()
    
    def update_kpi_table(self):
        self.kpi_table.setRowCount(len(self.kpis))
        
        for row, kpi in enumerate(self.kpis):
            self.kpi_table.setItem(row, 0, QTableWidgetItem(kpi['name']))
            self.kpi_table.setItem(row, 1, QTableWidgetItem(str(kpi['current'])))
            self.kpi_table.setItem(row, 2, QTableWidgetItem(str(kpi['target'])))
            
            # 进度条
            progress_widget = CustomProgressWidget(kpi['progress'], 100, f"{kpi['progress']}%")
            self.kpi_table.setCellWidget(row, 3, progress_widget)
            
            self.kpi_table.setItem(row, 4, QTableWidgetItem(kpi['unit']))
            self.kpi_table.setItem(row, 5, QTableWidgetItem(f"{kpi['weight']}%"))
            self.kpi_table.setItem(row, 6, QTableWidgetItem(kpi['owner']))
            self.kpi_table.setItem(row, 7, QTableWidgetItem(kpi['last_updated']))
            
            # 趋势指示器
            trend_label = QLabel(kpi['trend'])
            if kpi['trend'] == '上升':
                trend_label.setStyleSheet("color: green; font-weight: bold;")
            elif kpi['trend'] == '下降':
                trend_label.setStyleSheet("color: red; font-weight: bold;")
            elif kpi['trend'] == '稳定':
                trend_label.setStyleSheet("color: blue; font-weight: bold;")
            self.kpi_table.setCellWidget(row, 8, trend_label)
            
            # 操作按钮
            button_widget = QWidget()
            button_layout = QHBoxLayout()
            button_layout.setContentsMargins(5, 2, 5, 2)
            
            update_btn = QPushButton("更新")
            update_btn.clicked.connect(lambda _, r=row: self.update_kpi_value(r))
            button_layout.addWidget(update_btn)
            
            delete_btn = QPushButton("删除")
            delete_btn.clicked.connect(lambda _, r=row: self.delete_kpi(r))
            button_layout.addWidget(delete_btn)
            
            button_widget.setLayout(button_layout)
            self.kpi_table.setCellWidget(row, 9, button_widget)
    
    def update_kpi_value(self, row):
        dialog = QDialog(self)
        dialog.setWindowTitle("更新KPI值")
        dialog.setModal(True)
        
        layout = QVBoxLayout()
        
        form_layout = QFormLayout()
        
        current_spin = QDoubleSpinBox()
        current_spin.setRange(0, 10000)
        current_spin.setDecimals(2)
        current_spin.setValue(self.kpis[row]['current'])
        form_layout.addRow("新值:", current_spin)
        
        trend_combo = QComboBox()
        trend_combo.addItems(["上升", "下降", "稳定", "波动"])
        trend_combo.setCurrentText(self.kpis[row]['trend'])
        form_layout.addRow("趋势:", trend_combo)
        
        layout.addLayout(form_layout)
        
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        
        dialog.setLayout(layout)
        
        if dialog.exec_() == QDialog.Accepted:
            new_value = current_spin.value()
            target = self.kpis[row]['target']
            progress = min(100, int((new_value / target) * 100)) if target > 0 else 0
            
            self.kpis[row]['current'] = new_value
            self.kpis[row]['progress'] = progress
            self.kpis[row]['last_updated'] = QDate.currentDate().toString("yyyy-MM-dd")
            self.kpis[row]['trend'] = trend_combo.currentText()
            
            self.update_kpi_table()
    
    def delete_kpi(self, row):
        reply = QMessageBox.question(self, "确认删除", "确定要删除这个KPI吗?",
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QDialog.Yes:
            self.kpis.pop(row)
            self.update_kpi_table()
    
    def show_history(self):
        # 这里实现历史数据查看功能
        QMessageBox.information(self, "功能提示", "历史数据查看功能将在后续版本中实现")
    
    def set_alerts(self):
        # 这里实现预警设置功能
        QMessageBox.information(self, "功能提示", "预警设置功能将在后续版本中实现")


class DashboardWidget(QWidget):
    def __init__(self, goals_widget, kpi_widget):
        super().__init__()
        self.goals_widget = goals_widget
        self.kpi_widget = kpi_widget
        self.initUI()
        
        # 设置定时器，定期更新仪表盘
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_dashboard)
        self.timer.start(5000)  # 每5秒更新一次
        
    def initUI(self):
        layout = QVBoxLayout()
        
        # 标题
        title_label = QLabel("战略执行仪表盘")
        title_label.setStyleSheet("font-size: 16pt; font-weight: bold; margin: 10px;")
        layout.addWidget(title_label)
        
        # 关键指标卡片
        metrics_layout = QHBoxLayout()
        
        # 目标完成率卡片
        self.goals_card = QGroupBox("目标完成情况")
        goals_card_layout = QVBoxLayout()
        self.goals_progress = CustomProgressWidget(0, 100, "0%")
        self.goals_count_label = QLabel("总目标数: 0")
        self.completed_goals_label = QLabel("已完成: 0")
        goals_card_layout.addWidget(self.goals_progress)
        goals_card_layout.addWidget(self.goals_count_label)
        goals_card_layout.addWidget(self.completed_goals_label)
        self.goals_card.setLayout(goals_card_layout)
        metrics_layout.addWidget(self.goals_card)
        
        # KPI完成率卡片
        self.kpi_card = QGroupBox("KPI完成情况")
        kpi_card_layout = QVBoxLayout()
        self.kpi_progress = CustomProgressWidget(0, 100, "0%")
        self.kpi_count_label = QLabel("总KPI数: 0")
        self.on_track_kpi_label = QLabel("正常跟踪: 0")
        kpi_card_layout.addWidget(self.kpi_progress)
        kpi_card_layout.addWidget(self.kpi_count_label)
        kpi_card_layout.addWidget(self.on_track_kpi_label)
        self.kpi_card.setLayout(kpi_card_layout)
        metrics_layout.addWidget(self.kpi_card)
        
        # 风险预警卡片
        self.risk_card = QGroupBox("风险预警")
        risk_card_layout = QVBoxLayout()
        self.risk_count_label = QLabel("高风险项目: 0")
        self.risk_list = QListWidget()
        self.risk_list.setMaximumHeight(80)
        risk_card_layout.addWidget(self.risk_count_label)
        risk_card_layout.addWidget(self.risk_list)
        self.risk_card.setLayout(risk_card_layout)
        metrics_layout.addWidget(self.risk_card)
        
        layout.addLayout(metrics_layout)
        
        # 目标分类分布
        goals_distribution = QGroupBox("目标分类分布")
        goals_dist_layout = QHBoxLayout()
        
        self.category_bars = QWidget()
        self.category_bars.setMinimumHeight(150)
        goals_dist_layout.addWidget(self.category_bars)
        
        goals_distribution.setLayout(goals_dist_layout)
        layout.addWidget(goals_distribution)
        
        # 最近活动
        recent_activity = QGroupBox("最近活动")
        activity_layout = QVBoxLayout()
        self.activity_list = QListWidget()
        self.activity_list.setMaximumHeight(120)
        activity_layout.addWidget(self.activity_list)
        recent_activity.setLayout(activity_layout)
        layout.addWidget(recent_activity)
        
        self.setLayout(layout)
        
        # 初始更新
        self.update_dashboard()
    
    def update_dashboard(self):
        # 更新目标完成情况
        total_goals = len(self.goals_widget.goals)
        completed_goals = len([g for g in self.goals_widget.goals if g['progress'] >= 100])
        avg_progress = sum(g['progress'] for g in self.goals_widget.goals) / total_goals if total_goals > 0 else 0
        
        self.goals_progress.setValue(avg_progress)
        self.goals_progress.setText(f"{avg_progress:.1f}%")
        self.goals_count_label.setText(f"总目标数: {total_goals}")
        self.completed_goals_label.setText(f"已完成: {completed_goals}")
        
        # 更新KPI完成情况
        total_kpis = len(self.kpi_widget.kpis)
        on_track_kpis = len([k for k in self.kpi_widget.kpis if k['progress'] >= 70])
        avg_kpi_progress = sum(k['progress'] for k in self.kpi_widget.kpis) / total_kpis if total_kpis > 0 else 0
        
        self.kpi_progress.setValue(avg_kpi_progress)
        self.kpi_progress.setText(f"{avg_kpi_progress:.1f}%")
        self.kpi_count_label.setText(f"总KPI数: {total_kpis}")
        self.on_track_kpi_label.setText(f"正常跟踪: {on_track_kpis}")
        
        # 更新风险预警
        high_risk_goals = [g for g in self.goals_widget.goals 
                          if g['priority'] == '高' and g['progress'] < 30 
                          and QDate.fromString(g['deadline'], "yyyy-MM-dd").daysTo(QDate.currentDate()) > -30]
        
        self.risk_count_label.setText(f"高风险项目: {len(high_risk_goals)}")
        self.risk_list.clear()
        for goal in high_risk_goals:
            self.risk_list.addItem(f"{goal['name']} - 截止: {goal['deadline']}")
        
        # 更新目标分类分布
        self.category_bars.update = lambda: self.draw_category_bars()
        self.category_bars.update()
        
        # 更新最近活动
        self.update_recent_activity()
    
    def draw_category_bars(self):
        # 绘制目标分类分布条形图
        categories = ["财务", "客户", "内部流程", "学习与成长"]
        category_counts = {category: 0 for category in categories}
        
        for goal in self.goals_widget.goals:
            if goal['category'] in category_counts:
                category_counts[goal['category']] += 1
        
        total_goals = len(self.goals_widget.goals)
        if total_goals == 0:
            return
            
        painter = QPainter(self.category_bars)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 设置背景
        rect = self.category_bars.rect().adjusted(5, 5, -5, -5)
        painter.setPen(QColor(200, 200, 200))
        painter.setBrush(QColor(240, 240, 240))
        painter.drawRoundedRect(rect, 5, 5)
        
        # 计算条形图参数
        bar_width = (rect.width() - 100) / len(categories)
        max_count = max(category_counts.values()) or 1
        bar_height_unit = (rect.height() - 50) / max_count
        
        # 绘制条形图和标签
        for i, category in enumerate(categories):
            count = category_counts[category]
            bar_height = count * bar_height_unit
            bar_rect = rect.adjusted(
                50 + i * bar_width, 
                rect.height() - 30 - bar_height, 
                50 + (i + 1) * bar_width - 10, 
                rect.height() - 30
            )
            
            # 绘制条形
            gradient = QLinearGradient(bar_rect.topLeft(), bar_rect.bottomLeft())
            gradient.setColorAt(0, QColor(70, 130, 180))
            gradient.setColorAt(1, QColor(30, 90, 140))
            painter.setBrush(QBrush(gradient))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(bar_rect, 3, 3)
            
            # 绘制数量标签
            painter.setPen(QColor(0, 0, 0))
            painter.drawText(
                bar_rect.center().x() - 10, 
                bar_rect.top() - 5, 
                str(count)
            )
            
            # 绘制类别标签
            painter.drawText(
                bar_rect.center().x() - 15, 
                rect.height() - 10, 
                category
            )
        
        painter.end()
    
    def update_recent_activity(self):
        self.activity_list.clear()
        
        # 添加最近完成的目标
        recent_goals = [g for g in self.goals_widget.goals if g['progress'] == 100]
        for goal in recent_goals[:3]:  # 只显示最近3个
            self.activity_list.addItem(f"✅ 完成目标: {goal['name']}")
        
        # 添加最近更新的KPI
        if self.kpi_widget.kpis:
            recent_kpi = max(self.kpi_widget.kpis, key=lambda k: k['last_updated'])
            self.activity_list.addItem(f"📊 更新KPI: {recent_kpi['name']} -> {recent_kpi['current']}")
        
        # 添加一些模拟活动
        self.activity_list.addItem("👥 召开了战略评审会议")
        self.activity_list.addItem("📈 市场份额提升2%")


class RiskManagementWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.risks = []
        self.initUI()
        
    def initUI(self):
        main_layout = QVBoxLayout()
        
        # 标题
        title_label = QLabel("战略风险管理")
        title_label.setStyleSheet("font-size: 16pt; font-weight: bold; margin: 10px;")
        main_layout.addWidget(title_label)
        
        # 风险矩阵
        matrix_layout = QGridLayout()
        
        # 高风险区域
        high_risk_group = QGroupBox("高风险")
        high_risk_layout = QVBoxLayout()
        self.high_risk_list = QListWidget()
        self.high_risk_list.setStyleSheet("background-color: #ffcccc;")
        high_risk_layout.addWidget(self.high_risk_list)
        high_risk_group.setLayout(high_risk_layout)
        
        # 中等风险区域
        medium_risk_group = QGroupBox("中等风险")
        medium_risk_layout = QVBoxLayout()
        self.medium_risk_list = QListWidget()
        self.medium_risk_list.setStyleSheet("background-color: #ffffcc;")
        medium_risk_layout.addWidget(self.medium_risk_list)
        medium_risk_group.setLayout(medium_risk_layout)
        
        # 低风险区域
        low_risk_group = QGroupBox("低风险")
        low_risk_layout = QVBoxLayout()
        self.low_risk_list = QListWidget()
        self.low_risk_list.setStyleSheet("background-color: #ccffcc;")
        low_risk_layout.addWidget(self.low_risk_list)
        low_risk_group.setLayout(low_risk_layout)
        
        # 添加矩阵到布局
        matrix_layout.addWidget(high_risk_group, 0, 0)
        matrix_layout.addWidget(medium_risk_group, 0, 1)
        matrix_layout.addWidget(low_risk_group, 1, 0)
        
        # 风险应对策略区域
        response_group = QGroupBox("风险应对策略")
        response_layout = QVBoxLayout()
        self.response_edit = QTextEdit()
        response_layout.addWidget(self.response_edit)
        response_group.setLayout(response_layout)
        matrix_layout.addWidget(response_group, 1, 1)
        
        main_layout.addLayout(matrix_layout)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        
        add_btn = QPushButton("添加风险")
        add_btn.clicked.connect(self.add_risk_dialog)
        button_layout.addWidget(add_btn)
        
        analyze_btn = QPushButton("风险分析报告")
        analyze_btn.clicked.connect(self.generate_risk_report)
        button_layout.addWidget(analyze_btn)
        
        button_layout.addStretch()
        main_layout.addLayout(button_layout)
        
        self.setLayout(main_layout)
        
        # 添加示例数据
        self.add_sample_risks()
    
    def add_sample_risks(self):
        sample_risks = [
            {"description": "关键技术人才流失", "probability": "高", "impact": "高", "category": "人力资源"},
            {"description": "主要竞争对手推出新产品", "probability": "中", "impact": "高", "category": "市场竞争"},
            {"description": "原材料价格大幅上涨", "probability": "中", "impact": "中", "category": "供应链"},
            {"description": "新法规影响业务模式", "probability": "低", "impact": "高", "category": "法规政策"},
            {"description": "IT系统安全漏洞", "probability": "中", "impact": "中", "category": "技术"}
        ]
        
        for risk in sample_risks:
            self.risks.append(risk)
        
        self.update_risk_matrix()
    
    def add_risk_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("添加战略风险")
        dialog.setModal(True)
        
        layout = QVBoxLayout()
        
        form_layout = QFormLayout()
        
        description_edit = QLineEdit()
        form_layout.addRow("风险描述:", description_edit)
        
        probability_combo = QComboBox()
        probability_combo.addItems(["高", "中", "低"])
        form_layout.addRow("发生概率:", probability_combo)
        
        impact_combo = QComboBox()
        impact_combo.addItems(["高", "中", "低"])
        form_layout.addRow("影响程度:", impact_combo)
        
        category_combo = QComboBox()
        category_combo.addItems(["市场竞争", "技术", "人力资源", "财务", "供应链", "法规政策", "其他"])
        form_layout.addRow("风险类别:", category_combo)
        
        layout.addLayout(form_layout)
        
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        
        dialog.setLayout(layout)
        
        if dialog.exec_() == QDialog.Accepted and description_edit.text().strip():
            risk = {
                'description': description_edit.text(),
                'probability': probability_combo.currentText(),
                'impact': impact_combo.currentText(),
                'category': category_combo.currentText()
            }
            
            self.risks.append(risk)
            self.update_risk_matrix()
    
    def update_risk_matrix(self):
        self.high_risk_list.clear()
        self.medium_risk_list.clear()
        self.low_risk_list.clear()
        
        for risk in self.risks:
            # 根据概率和影响确定风险级别
            if risk['probability'] == '高' and risk['impact'] == '高':
                self.high_risk_list.addItem(f"{risk['description']} [{risk['category']}]")
            elif (risk['probability'] == '高' and risk['impact'] == '中') or \
                 (risk['probability'] == '中' and risk['impact'] == '高'):
                self.high_risk_list.addItem(f"{risk['description']} [{risk['category']}]")
            elif (risk['probability'] == '高' and risk['impact'] == '低') or \
                 (risk['probability'] == '中' and risk['impact'] == '中') or \
                 (risk['probability'] == '低' and risk['impact'] == '高'):
                self.medium_risk_list.addItem(f"{risk['description']} [{risk['category']}]")
            else:
                self.low_risk_list.addItem(f"{risk['description']} [{risk['category']}]")
    
    def generate_risk_report(self):
        report = "战略风险分析报告\n"
        report += "生成时间: " + datetime.now().strftime("%Y-%m-%d %H:%M") + "\n\n"
        
        report += "高风险项目:\n"
        for i in range(self.high_risk_list.count()):
            report += f"  • {self.high_risk_list.item(i).text()}\n"
        
        report += "\n中等风险项目:\n"
        for i in range(self.medium_risk_list.count()):
            report += f"  • {self.medium_risk_list.item(i).text()}\n"
        
        report += "\n低风险项目:\n"
        for i in range(self.low_risk_list.count()):
            report += f"  • {self.low_risk_list.item(i).text()}\n"
        
        # 显示报告
        self.show_report_dialog(report)
    
    def show_report_dialog(self, report):
        dialog = QDialog(self)
        dialog.setWindowTitle("风险分析报告")
        dialog.setMinimumSize(500, 400)
        
        layout = QVBoxLayout()
        
        report_edit = QTextEdit()
        report_edit.setPlainText(report)
        report_edit.setReadOnly(True)
        layout.addWidget(report_edit)
        
        button_box = QDialogButtonBox(QDialogButtonBox.Ok)
        button_box.accepted.connect(dialog.accept)
        layout.addWidget(button_box)
        
        dialog.setLayout(layout)
        dialog.exec_()


class CEOStrategyTool(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()
        
    def initUI(self):
        self.setWindowTitle("CEO战略制定高级工具")
        self.setGeometry(100, 100, 1400, 900)
        
        # 设置应用样式
        self.setStyle(QStyleFactory.create("Fusion"))
        
        # 创建中央部件和标签页
        self.central_widget = QTabWidget()
        self.setCentralWidget(self.central_widget)
        
        # 创建各个功能部件
        self.swot_widget = SWOTAnalysisWidget()
        self.goals_widget = StrategicGoalsWidget()
        self.kpi_widget = KPITrackingWidget()
        self.dashboard_widget = DashboardWidget(self.goals_widget, self.kpi_widget)
        self.risk_widget = RiskManagementWidget()
        
        # 添加标签页
        self.central_widget.addTab(self.dashboard_widget, "🏠 仪表盘")
        self.central_widget.addTab(self.swot_widget, "📊 SWOT分析")
        self.central_widget.addTab(self.goals_widget, "🎯 战略目标")
        self.central_widget.addTab(self.kpi_widget, "📈 KPI跟踪")
        self.central_widget.addTab(self.risk_widget, "⚠️ 风险管理")
        
        # 创建菜单栏
        self.create_menu_bar()
        
        # 创建工具栏
        self.create_tool_bar()
        
        # 创建状态栏
        self.statusBar().showMessage("就绪")
        
        # 初始仪表盘更新
        self.update_dashboard()
    
    def create_menu_bar(self):
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu("文件")
        
        new_action = QAction("新建", self)
        new_action.setShortcut("Ctrl+N")
        file_menu.addAction(new_action)
        
        export_action = QAction("导出数据", self)
        export_action.setShortcut("Ctrl+E")
        export_action.triggered.connect(self.export_data)
        file_menu.addAction(export_action)
        
        import_action = QAction("导入数据", self)
        import_action.setShortcut("Ctrl+I")
        import_action.triggered.connect(self.import_data)
        file_menu.addAction(import_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("退出", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 视图菜单
        view_menu = menubar.addMenu("视图")
        
        refresh_action = QAction("刷新仪表盘", self)
        refresh_action.setShortcut("F5")
        refresh_action.triggered.connect(self.update_dashboard)
        view_menu.addAction(refresh_action)
        
        # 工具菜单
        tools_menu = menubar.addMenu("工具")
        
        report_action = QAction("生成综合报告", self)
        report_action.triggered.connect(self.generate_comprehensive_report)
        tools_menu.addAction(report_action)
        
        settings_action = QAction("设置", self)
        tools_menu.addAction(settings_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu("帮助")
        
        about_action = QAction("关于", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def create_tool_bar(self):
        toolbar = QToolBar("主工具栏")
        toolbar.setIconSize(QSize(16, 16))
        self.addToolBar(toolbar)
        
        # 添加工具栏动作
        dashboard_action = QAction("仪表盘", self)
        dashboard_action.triggered.connect(lambda: self.central_widget.setCurrentIndex(0))
        toolbar.addAction(dashboard_action)
        
        swot_action = QAction("SWOT分析", self)
        swot_action.triggered.connect(lambda: self.central_widget.setCurrentIndex(1))
        toolbar.addAction(swot_action)
        
        goals_action = QAction("战略目标", self)
        goals_action.triggered.connect(lambda: self.central_widget.setCurrentIndex(2))
        toolbar.addAction(goals_action)
        
        toolbar.addSeparator()
        
        export_action = QAction("导出数据", self)
        export_action.triggered.connect(self.export_data)
        toolbar.addAction(export_action)
        
        refresh_action = QAction("刷新", self)
        refresh_action.triggered.connect(self.update_dashboard)
        toolbar.addAction(refresh_action)
    
    def update_dashboard(self):
        self.dashboard_widget.update_dashboard()
        self.statusBar().showMessage("仪表盘已更新: " + datetime.now().strftime("%Y-%m-%d %H:%M"))
    
    def export_data(self):
        data = {
            'swot': {
                'strengths': [self.swot_widget.strengths_list.item(i).text() for i in range(self.swot_widget.strengths_list.count())],
                'weaknesses': [self.swot_widget.weaknesses_list.item(i).text() for i in range(self.swot_widget.weaknesses_list.count())],
                'opportunities': [self.swot_widget.opportunities_list.item(i).text() for i in range(self.swot_widget.opportunities_list.count())],
                'threats': [self.swot_widget.threats_list.item(i).text() for i in range(self.swot_widget.threats_list.count())]
            },
            'goals': self.goals_widget.goals,
            'kpis': self.kpi_widget.kpis,
            'risks': self.risk_widget.risks
        }
        
        file_path, _ = QFileDialog.getSaveFileName(self, "导出数据", "", "JSON Files (*.json)")
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=4)
                self.statusBar().showMessage("数据已成功导出!")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导出失败: {str(e)}")
    
    def import_data(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "导入数据", "", "JSON Files (*.json)")
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 导入SWOT数据
                if 'swot' in data:
                    self.swot_widget.strengths_list.clear()
                    for item in data['swot'].get('strengths', []):
                        self.swot_widget.strengths_list.addItem(item)
                    
                    self.swot_widget.weaknesses_list.clear()
                    for item in data['swot'].get('weaknesses', []):
                        self.swot_widget.weaknesses_list.addItem(item)
                    
                    self.swot_widget.opportunities_list.clear()
                    for item in data['swot'].get('opportunities', []):
                        self.swot_widget.opportunities_list.addItem(item)
                    
                    self.swot_widget.threats_list.clear()
                    for item in data['swot'].get('threats', []):
                        self.swot_widget.threats_list.addItem(item)
                
                # 导入目标数据
                if 'goals' in data:
                    self.goals_widget.goals = data['goals']
                    self.goals_widget.update_goals_table()
                
                # 导入KPI数据
                if 'kpis' in data:
                    self.kpi_widget.kpis = data['kpis']
                    self.kpi_widget.update_kpi_table()
                
                # 导入风险数据
                if 'risks' in data:
                    self.risk_widget.risks = data['risks']
                    self.risk_widget.update_risk_matrix()
                
                self.update_dashboard()
                self.statusBar().showMessage("数据已成功导入!")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导入失败: {str(e)}")
    
    def generate_comprehensive_report(self):
        report = "CEO战略制定工具 - 综合报告\n"
        report += "生成时间: " + datetime.now().strftime("%Y-%m-%d %H:%M") + "\n\n"
        
        # SWOT分析摘要
        report += "1. SWOT分析摘要\n"
        report += "   优势: {}项\n".format(self.swot_widget.strengths_list.count())
        report += "   劣势: {}项\n".format(self.swot_widget.weaknesses_list.count())
        report += "   机会: {}项\n".format(self.swot_widget.opportunities_list.count())
        report += "   威胁: {}项\n\n".format(self.swot_widget.threats_list.count())
        
        # 战略目标摘要
        report += "2. 战略目标摘要\n"
        total_goals = len(self.goals_widget.goals)
        completed_goals = len([g for g in self.goals_widget.goals if g['progress'] >= 100])
        avg_progress = sum(g['progress'] for g in self.goals_widget.goals) / total_goals if total_goals > 0 else 0
        
        report += "   总目标数: {}\n".format(total_goals)
        report += "   已完成目标: {}\n".format(completed_goals)
        report += "   平均进度: {:.1f}%\n\n".format(avg_progress)
        
        # KPI跟踪摘要
        report += "3. KPI跟踪摘要\n"
        total_kpis = len(self.kpi_widget.kpis)
        on_track_kpis = len([k for k in self.kpi_widget.kpis if k['progress'] >= 70])
        avg_kpi_progress = sum(k['progress'] for k in self.kpi_widget.kpis) / total_kpis if total_kpis > 0 else 0
        
        report += "   总KPI数: {}\n".format(total_kpis)
        report += "   正常跟踪KPI: {}\n".format(on_track_kpis)
        report += "   平均进度: {:.1f}%\n\n".format(avg_kpi_progress)
        
        # 风险管理摘要
        report += "4. 风险管理摘要\n"
        high_risks = self.risk_widget.high_risk_list.count()
        medium_risks = self.risk_widget.medium_risk_list.count()
        low_risks = self.risk_widget.low_risk_list.count()
        
        report += "   高风险: {}项\n".format(high_risks)
        report += "   中等风险: {}项\n".format(medium_risks)
        report += "   低风险: {}项\n\n".format(low_risks)
        
        # 建议和下一步
        report += "5. 建议和下一步\n"
        if high_risks > 0:
            report += "   • 优先处理高风险项目\n"
        if avg_progress < 50:
            report += "   • 加强战略目标执行力度\n"
        if on_track_kpis < total_kpis / 2:
            report += "   • 关注落后KPI指标，制定改进计划\n"
        
        # 显示报告
        self.show_report_dialog(report)
    
    def show_report_dialog(self, report):
        dialog = QDialog(self)
        dialog.setWindowTitle("综合报告")
        dialog.setMinimumSize(600, 500)
        
        layout = QVBoxLayout()
        
        report_edit = QTextEdit()
        report_edit.setPlainText(report)
        report_edit.setReadOnly(True)
        layout.addWidget(report_edit)
        
        button_layout = QHBoxLayout()
        
        save_btn = QPushButton("保存报告")
        save_btn.clicked.connect(lambda: self.save_report(report))
        button_layout.addWidget(save_btn)
        
        print_btn = QPushButton("打印")
        button_layout.addWidget(print_btn)
        
        button_layout.addStretch()
        
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(dialog.accept)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
        
        dialog.setLayout(layout)
        dialog.exec_()
    
    def save_report(self, report):
        file_path, _ = QFileDialog.getSaveFileName(self, "保存报告", "", "Text Files (*.txt)")
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(report)
                self.statusBar().showMessage("报告已保存!")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"保存失败: {str(e)}")
    
    def show_about(self):
        about_text = """
        CEO战略制定高级工具
        
        版本: 2.0
        开发公司: 战略咨询科技有限公司
        
        功能:
        - SWOT分析
        - 战略目标管理
        - KPI跟踪与绩效管理
        - 战略仪表盘
        - 风险管理
        - 综合报告生成
        
        © 2025 版权所有
        """
        QMessageBox.about(self, "关于CEO战略制定工具", about_text)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # 设置应用样式
    app.setStyle(QStyleFactory.create("Fusion"))
    
    # 设置应用字体
    font = QFont("Microsoft YaHei", 10)
    app.setFont(font)
    
    window = CEOStrategyTool()
    window.show()
    
    sys.exit(app.exec_())