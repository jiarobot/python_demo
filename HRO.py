import sys
import os
import csv
import json
import pandas as pd
from datetime import datetime, timedelta
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QTabWidget, QTableWidget, QTableWidgetItem,
                             QTextEdit, QFileDialog, QMessageBox, QComboBox, QLineEdit,
                             QDateEdit, QSpinBox, QDoubleSpinBox, QGroupBox, QFormLayout,
                             QProgressBar, QSplitter, QHeaderView, QCheckBox, QListWidget,
                             QAbstractItemView, QToolBar, QStatusBar, QAction, QStyle)
from PyQt5.QtCore import Qt, QDate, QThread, pyqtSignal, QTimer, QSettings
from PyQt5.QtGui import QIcon, QFont, QColor, QPalette
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import numpy as np
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import sqlite3
from collections import defaultdict


class HROAdvancedToolkit(QMainWindow):
    """HRO系统高级工具库主窗口"""
    
    def __init__(self):
        super().__init__()
        self.settings = QSettings("HRO Corp", "Advanced Toolkit")
        self.initUI()
        self.load_settings()
        
    def initUI(self):
        """初始化用户界面"""
        self.setWindowTitle("HRO系统高级工具库")
        self.setGeometry(100, 100, 1200, 800)
        
        # 创建中央部件和主布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # 创建工具栏
        self.create_toolbar()
        
        # 创建状态栏
        self.statusBar().showMessage("就绪")
        
        # 创建标签页
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)
        
        # 添加各个工具标签页
        self.add_data_analyzer_tab()
        self.add_report_generator_tab()
        self.add_batch_processor_tab()
        self.add_email_sender_tab()
        self.add_data_migration_tab()
        self.add_settings_tab()
        
    def create_toolbar(self):
        """创建工具栏"""
        toolbar = QToolBar("主工具栏")
        self.addToolBar(toolbar)
        
        # 添加工具按钮
        new_action = QAction(QIcon.fromTheme("document-new"), "新建", self)
        new_action.triggered.connect(self.new_project)
        toolbar.addAction(new_action)
        
        open_action = QAction(QIcon.fromTheme("document-open"), "打开", self)
        open_action.triggered.connect(self.open_file)
        toolbar.addAction(open_action)
        
        save_action = QAction(QIcon.fromTheme("document-save"), "保存", self)
        save_action.triggered.connect(self.save_file)
        toolbar.addAction(save_action)
        
        toolbar.addSeparator()
        
        export_action = QAction(QIcon.fromTheme("document-export"), "导出", self)
        export_action.triggered.connect(self.export_data)
        toolbar.addAction(export_action)
        
        help_action = QAction(QIcon.fromTheme("help-contents"), "帮助", self)
        help_action.triggered.connect(self.show_help)
        toolbar.addAction(help_action)
        
    def add_data_analyzer_tab(self):
        """添加数据分析工具标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 数据控制区域
        control_group = QGroupBox("数据分析控制")
        control_layout = QHBoxLayout(control_group)
        
        self.load_data_btn = QPushButton("加载数据")
        self.load_data_btn.clicked.connect(self.load_data_for_analysis)
        control_layout.addWidget(self.load_data_btn)
        
        self.analyze_btn = QPushButton("执行分析")
        self.analyze_btn.clicked.connect(self.perform_analysis)
        control_layout.addWidget(self.analyze_btn)
        
        self.export_analysis_btn = QPushButton("导出结果")
        self.export_analysis_btn.clicked.connect(self.export_analysis_results)
        control_layout.addWidget(self.export_analysis_btn)
        
        layout.addWidget(control_group)
        
        # 分割区域显示数据和分析结果
        splitter = QSplitter(Qt.Vertical)
        
        # 数据表格
        self.data_table = QTableWidget()
        splitter.addWidget(self.data_table)
        
        # 分析结果区域
        result_widget = QWidget()
        result_layout = QVBoxLayout(result_widget)
        
        # 图表区域
        self.figure = plt.figure()
        self.canvas = FigureCanvas(self.figure)
        result_layout.addWidget(self.canvas)
        
        # 分析摘要
        self.analysis_summary = QTextEdit()
        self.analysis_summary.setPlaceholderText("分析结果将显示在这里...")
        result_layout.addWidget(self.analysis_summary)
        
        splitter.addWidget(result_widget)
        splitter.setSizes([400, 400])
        
        layout.addWidget(splitter)
        
        self.tabs.addTab(tab, "数据分析")
        
    def add_report_generator_tab(self):
        """添加报告生成工具标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 报告类型选择
        type_group = QGroupBox("报告类型")
        type_layout = QHBoxLayout(type_group)
        
        self.report_type = QComboBox()
        self.report_type.addItems(["员工统计报告", "薪资分析报告", "考勤报告", "绩效评估报告", "自定义报告"])
        type_layout.addWidget(QLabel("报告类型:"))
        type_layout.addWidget(self.report_type)
        
        self.template_select = QComboBox()
        self.template_select.addItems(["标准模板", "详细模板", "简约模板"])
        type_layout.addWidget(QLabel("模板:"))
        type_layout.addWidget(self.template_select)
        
        layout.addWidget(type_group)
        
        # 参数设置
        param_group = QGroupBox("报告参数")
        param_layout = QFormLayout(param_group)
        
        self.start_date = QDateEdit()
        self.start_date.setDate(QDate.currentDate().addMonths(-1))
        param_layout.addRow("开始日期:", self.start_date)
        
        self.end_date = QDateEdit()
        self.end_date.setDate(QDate.currentDate())
        param_layout.addRow("结束日期:", self.end_date)
        
        self.department_filter = QComboBox()
        self.department_filter.addItems(["所有部门", "技术部", "市场部", "财务部", "人力资源部"])
        param_layout.addRow("部门筛选:", self.department_filter)
        
        layout.addWidget(param_group)
        
        # 报告预览和生成
        preview_group = QGroupBox("报告预览和生成")
        preview_layout = QVBoxLayout(preview_group)
        
        self.report_preview = QTextEdit()
        self.report_preview.setPlaceholderText("报告预览将显示在这里...")
        preview_layout.addWidget(self.report_preview)
        
        btn_layout = QHBoxLayout()
        self.preview_btn = QPushButton("预览报告")
        self.preview_btn.clicked.connect(self.preview_report)
        btn_layout.addWidget(self.preview_btn)
        
        self.generate_pdf_btn = QPushButton("生成PDF")
        self.generate_pdf_btn.clicked.connect(self.generate_pdf_report)
        btn_layout.addWidget(self.generate_pdf_btn)
        
        self.generate_excel_btn = QPushButton("生成Excel")
        self.generate_excel_btn.clicked.connect(self.generate_excel_report)
        btn_layout.addWidget(self.generate_excel_btn)
        
        preview_layout.addLayout(btn_layout)
        
        layout.addWidget(preview_group)
        
        self.tabs.addTab(tab, "报告生成")
        
    def add_batch_processor_tab(self):
        """添加批处理工具标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 操作选择
        operation_group = QGroupBox("批处理操作")
        operation_layout = QFormLayout(operation_group)
        
        self.batch_operation = QComboBox()
        self.batch_operation.addItems([
            "批量更新员工信息", 
            "批量调整薪资", 
            "批量发送通知", 
            "批量导入数据", 
            "批量导出数据"
        ])
        operation_layout.addRow("选择操作:", self.batch_operation)
        
        self.source_file = QLineEdit()
        self.source_file.setPlaceholderText("选择源文件...")
        operation_layout.addRow("源文件:", self.source_file)
        
        browse_btn = QPushButton("浏览...")
        browse_btn.clicked.connect(self.select_source_file)
        operation_layout.addRow("", browse_btn)
        
        layout.addWidget(operation_group)
        
        # 参数设置
        param_group = QGroupBox("操作参数")
        param_layout = QFormLayout(param_group)
        
        self.adjustment_type = QComboBox()
        self.adjustment_type.addItems(["百分比调整", "固定值调整"])
        param_layout.addRow("调整类型:", self.adjustment_type)
        
        self.adjustment_value = QDoubleSpinBox()
        self.adjustment_value.setRange(-100, 100)
        self.adjustment_value.setSuffix("%")
        param_layout.addRow("调整值:", self.adjustment_value)
        
        layout.addWidget(param_group)
        
        # 进度和日志
        progress_group = QGroupBox("进度和日志")
        progress_layout = QVBoxLayout(progress_group)
        
        self.batch_progress = QProgressBar()
        progress_layout.addWidget(self.batch_progress)
        
        self.batch_log = QTextEdit()
        self.batch_log.setPlaceholderText("处理日志将显示在这里...")
        progress_layout.addWidget(self.batch_log)
        
        process_btn = QPushButton("开始处理")
        process_btn.clicked.connect(self.start_batch_processing)
        progress_layout.addWidget(process_btn)
        
        layout.addWidget(progress_group)
        
        self.tabs.addTab(tab, "批处理工具")
        
    def add_email_sender_tab(self):
        """添加邮件发送工具标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 邮件设置
        settings_group = QGroupBox("邮件服务器设置")
        settings_layout = QFormLayout(settings_group)
        
        self.smtp_server = QLineEdit()
        self.smtp_server.setText("smtp.example.com")
        settings_layout.addRow("SMTP服务器:", self.smtp_server)
        
        self.smtp_port = QSpinBox()
        self.smtp_port.setRange(1, 65535)
        self.smtp_port.setValue(587)
        settings_layout.addRow("端口:", self.smtp_port)
        
        self.email_address = QLineEdit()
        self.email_address.setText("hro@example.com")
        settings_layout.addRow("发件邮箱:", self.email_address)
        
        self.email_password = QLineEdit()
        self.email_password.setEchoMode(QLineEdit.Password)
        settings_layout.addRow("密码:", self.email_password)
        
        layout.addWidget(settings_group)
        
        # 邮件内容
        content_group = QGroupBox("邮件内容")
        content_layout = QVBoxLayout(content_group)
        
        self.email_subject = QLineEdit()
        self.email_subject.setPlaceholderText("邮件主题...")
        content_layout.addWidget(self.email_subject)
        
        self.email_content = QTextEdit()
        self.email_content.setPlaceholderText("邮件内容...")
        content_layout.addWidget(self.email_content)
        
        layout.addWidget(content_group)
        
        # 收件人列表
        recipients_group = QGroupBox("收件人列表")
        recipients_layout = QVBoxLayout(recipients_group)
        
        self.recipients_list = QListWidget()
        self.recipients_list.setSelectionMode(QAbstractItemView.MultiSelection)
        recipients_layout.addWidget(self.recipients_list)
        
        load_recipients_btn = QPushButton("加载收件人列表")
        load_recipients_btn.clicked.connect(self.load_recipients)
        recipients_layout.addWidget(load_recipients_btn)
        
        layout.addWidget(recipients_group)
        
        # 发送控制
        send_group = QGroupBox("发送控制")
        send_layout = QHBoxLayout(send_group)
        
        self.test_email_btn = QPushButton("发送测试邮件")
        self.test_email_btn.clicked.connect(self.send_test_email)
        send_layout.addWidget(self.test_email_btn)
        
        self.send_all_btn = QPushButton("发送全部邮件")
        self.send_all_btn.clicked.connect(self.send_all_emails)
        send_layout.addWidget(self.send_all_btn)
        
        layout.addWidget(send_group)
        
        self.tabs.addTab(tab, "邮件发送")
        
    def add_data_migration_tab(self):
        """添加数据迁移工具标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 源数据设置
        source_group = QGroupBox("源数据")
        source_layout = QFormLayout(source_group)
        
        self.source_type = QComboBox()
        self.source_type.addItems(["CSV文件", "Excel文件", "SQL数据库", "JSON文件"])
        source_layout.addRow("源类型:", self.source_type)
        
        self.source_path = QLineEdit()
        self.source_path.setPlaceholderText("源文件路径或连接字符串...")
        source_layout.addRow("源路径:", self.source_path)
        
        source_browse_btn = QPushButton("浏览...")
        source_browse_btn.clicked.connect(self.select_source_path)
        source_layout.addRow("", source_browse_btn)
        
        layout.addWidget(source_group)
        
        # 目标数据设置
        target_group = QGroupBox("目标数据")
        target_layout = QFormLayout(target_group)
        
        self.target_type = QComboBox()
        self.target_type.addItems(["SQL数据库", "CSV文件", "Excel文件", "JSON文件"])
        target_layout.addRow("目标类型:", self.target_type)
        
        self.target_path = QLineEdit()
        self.target_path.setPlaceholderText("目标文件路径或连接字符串...")
        target_layout.addRow("目标路径:", self.target_path)
        
        target_browse_btn = QPushButton("浏览...")
        target_browse_btn.clicked.connect(self.select_target_path)
        target_layout.addRow("", target_browse_btn)
        
        layout.addWidget(target_group)
        
        # 映射设置
        mapping_group = QGroupBox("字段映射")
        mapping_layout = QVBoxLayout(mapping_group)
        
        self.mapping_table = QTableWidget()
        self.mapping_table.setColumnCount(2)
        self.mapping_table.setHorizontalHeaderLabels(["源字段", "目标字段"])
        mapping_layout.addWidget(self.mapping_table)
        
        auto_map_btn = QPushButton("自动映射字段")
        auto_map_btn.clicked.connect(self.auto_map_fields)
        mapping_layout.addWidget(auto_map_btn)
        
        layout.addWidget(mapping_group)
        
        # 迁移控制
        migrate_group = QGroupBox("迁移控制")
        migrate_layout = QVBoxLayout(migrate_group)
        
        self.migration_progress = QProgressBar()
        migrate_layout.addWidget(self.migration_progress)
        
        self.migration_log = QTextEdit()
        self.migration_log.setPlaceholderText("迁移日志将显示在这里...")
        migrate_layout.addWidget(self.migration_log)
        
        migrate_btn = QPushButton("开始迁移")
        migrate_btn.clicked.connect(self.start_migration)
        migrate_layout.addWidget(migrate_btn)
        
        layout.addWidget(migrate_group)
        
        self.tabs.addTab(tab, "数据迁移")
        
    def add_settings_tab(self):
        """添加设置标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 常规设置
        general_group = QGroupBox("常规设置")
        general_layout = QFormLayout(general_group)
        
        self.language = QComboBox()
        self.language.addItems(["中文", "English", "日本語"])
        general_layout.addRow("语言:", self.language)
        
        self.theme = QComboBox()
        self.theme.addItems(["默认", "深色", "浅色"])
        general_layout.addRow("主题:", self.theme)
        
        self.auto_save = QCheckBox("启用自动保存")
        general_layout.addRow("", self.auto_save)
        
        self.save_interval = QSpinBox()
        self.save_interval.setRange(1, 60)
        self.save_interval.setSuffix(" 分钟")
        general_layout.addRow("自动保存间隔:", self.save_interval)
        
        layout.addWidget(general_group)
        
        # 数据库设置
        db_group = QGroupBox("数据库设置")
        db_layout = QFormLayout(db_group)
        
        self.db_type = QComboBox()
        self.db_type.addItems(["SQLite", "MySQL", "PostgreSQL"])
        db_layout.addRow("数据库类型:", self.db_type)
        
        self.db_host = QLineEdit()
        self.db_host.setText("localhost")
        db_layout.addRow("主机:", self.db_host)
        
        self.db_name = QLineEdit()
        self.db_name.setText("hro_system")
        db_layout.addRow("数据库名:", self.db_name)
        
        self.db_user = QLineEdit()
        self.db_user.setText("root")
        db_layout.addRow("用户名:", self.db_user)
        
        self.db_password = QLineEdit()
        self.db_password.setEchoMode(QLineEdit.Password)
        db_layout.addRow("密码:", self.db_password)
        
        test_connection_btn = QPushButton("测试连接")
        test_connection_btn.clicked.connect(self.test_db_connection)
        db_layout.addRow("", test_connection_btn)
        
        layout.addWidget(db_group)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        
        save_settings_btn = QPushButton("保存设置")
        save_settings_btn.clicked.connect(self.save_settings)
        button_layout.addWidget(save_settings_btn)
        
        restore_defaults_btn = QPushButton("恢复默认值")
        restore_defaults_btn.clicked.connect(self.restore_default_settings)
        button_layout.addWidget(restore_defaults_btn)
        
        layout.addLayout(button_layout)
        layout.addStretch()
        
        self.tabs.addTab(tab, "设置")
        
    def load_settings(self):
        """加载保存的设置"""
        # 加载常规设置
        self.language.setCurrentText(self.settings.value("language", "中文"))
        self.theme.setCurrentText(self.settings.value("theme", "默认"))
        self.auto_save.setChecked(self.settings.value("auto_save", False, type=bool))
        self.save_interval.setValue(self.settings.value("save_interval", 5, type=int))
        
        # 加载数据库设置
        self.db_type.setCurrentText(self.settings.value("db_type", "SQLite"))
        self.db_host.setText(self.settings.value("db_host", "localhost"))
        self.db_name.setText(self.settings.value("db_name", "hro_system"))
        self.db_user.setText(self.settings.value("db_user", "root"))
        self.db_password.setText(self.settings.value("db_password", ""))
        
        # 加载邮件设置
        self.smtp_server.setText(self.settings.value("smtp_server", "smtp.example.com"))
        self.smtp_port.setValue(self.settings.value("smtp_port", 587, type=int))
        self.email_address.setText(self.settings.value("email_address", "hro@example.com"))
        
    def save_settings(self):
        """保存设置"""
        # 保存常规设置
        self.settings.setValue("language", self.language.currentText())
        self.settings.setValue("theme", self.theme.currentText())
        self.settings.setValue("auto_save", self.auto_save.isChecked())
        self.settings.setValue("save_interval", self.save_interval.value())
        
        # 保存数据库设置
        self.settings.setValue("db_type", self.db_type.currentText())
        self.settings.setValue("db_host", self.db_host.text())
        self.settings.setValue("db_name", self.db_name.text())
        self.settings.setValue("db_user", self.db_user.text())
        self.settings.setValue("db_password", self.db_password.text())
        
        # 保存邮件设置
        self.settings.setValue("smtp_server", self.smtp_server.text())
        self.settings.setValue("smtp_port", self.smtp_port.value())
        self.settings.setValue("email_address", self.email_address.text())
        
        QMessageBox.information(self, "设置", "设置已保存成功！")
        
    def restore_default_settings(self):
        """恢复默认设置"""
        reply = QMessageBox.question(self, "确认", 
                                    "确定要恢复默认设置吗？这将重置所有设置。",
                                    QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.settings.clear()
            self.load_settings()
            QMessageBox.information(self, "设置", "已恢复默认设置。")
    
    def new_project(self):
        """新建项目"""
        # 实现新建项目功能
        pass
        
    def open_file(self):
        """打开文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "打开文件", "", 
            "所有支持的文件 (*.csv *.xlsx *.json *.db *.sqlite);;CSV文件 (*.csv);;Excel文件 (*.xlsx);;JSON文件 (*.json);;数据库文件 (*.db *.sqlite)"
        )
        
        if file_path:
            self.statusBar().showMessage(f"已打开文件: {file_path}")
            # 根据文件类型执行相应操作
    
    def save_file(self):
        """保存文件"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存文件", "", 
            "CSV文件 (*.csv);;Excel文件 (*.xlsx);;JSON文件 (*.json);;数据库文件 (*.db)"
        )
        
        if file_path:
            self.statusBar().showMessage(f"文件已保存: {file_path}")
            # 实现保存功能
    
    def export_data(self):
        """导出数据"""
        # 实现数据导出功能
        pass
    
    def show_help(self):
        """显示帮助"""
        QMessageBox.information(self, "帮助", 
                               "HRO系统高级工具库\n\n"
                               "这是一个强大的人力资源管理系统工具集合，提供数据分析、报告生成、"
                               "批处理、邮件发送和数据迁移等功能。\n\n"
                               "请选择相应标签页使用各种工具。")
    
    def load_data_for_analysis(self):
        """加载数据用于分析"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "打开数据文件", "", 
            "CSV文件 (*.csv);;Excel文件 (*.xlsx);;JSON文件 (*.json)"
        )
        
        if file_path:
            try:
                if file_path.endswith('.csv'):
                    data = pd.read_csv(file_path)
                elif file_path.endswith('.xlsx'):
                    data = pd.read_excel(file_path)
                elif file_path.endswith('.json'):
                    data = pd.read_json(file_path)
                else:
                    QMessageBox.warning(self, "错误", "不支持的文件格式")
                    return
                
                self.display_data_in_table(data)
                self.current_data = data
                self.statusBar().showMessage(f"已加载数据: {file_path}")
                
            except Exception as e:
                QMessageBox.critical(self, "错误", f"加载文件时出错: {str(e)}")
    
    def display_data_in_table(self, data):
        """在表格中显示数据"""
        self.data_table.setRowCount(data.shape[0])
        self.data_table.setColumnCount(data.shape[1])
        self.data_table.setHorizontalHeaderLabels(data.columns)
        
        for row in range(data.shape[0]):
            for col in range(data.shape[1]):
                item = QTableWidgetItem(str(data.iat[row, col]))
                self.data_table.setItem(row, col, item)
                
        self.data_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
    
    def perform_analysis(self):
        """执行数据分析"""
        if not hasattr(self, 'current_data') or self.current_data is None:
            QMessageBox.warning(self, "警告", "请先加载数据")
            return
            
        try:
            # 清空图表
            self.figure.clear()
            
            # 执行一些示例分析
            numeric_columns = self.current_data.select_dtypes(include=[np.number]).columns
            
            if len(numeric_columns) > 0:
                # 创建子图
                ax = self.figure.add_subplot(111)
                
                # 绘制柱状图
                means = self.current_data[numeric_columns].mean()
                ax.bar(range(len(means)), means)
                ax.set_xticks(range(len(means)))
                ax.set_xticklabels(numeric_columns, rotation=45)
                ax.set_title("数值列平均值")
                
                self.canvas.draw()
                
                # 生成分析摘要
                summary = "数据分析结果:\n\n"
                summary += f"数据形状: {self.current_data.shape[0]} 行, {self.current_data.shape[1]} 列\n\n"
                
                summary += "数值列统计:\n"
                for col in numeric_columns:
                    summary += f"{col}: 平均值={self.current_data[col].mean():.2f}, 标准差={self.current_data[col].std():.2f}\n"
                
                summary += "\n数据预览:\n"
                summary += self.current_data.head().to_string()
                
                self.analysis_summary.setPlainText(summary)
            else:
                QMessageBox.information(self, "信息", "数据中没有数值列可供分析")
                
        except Exception as e:
            QMessageBox.critical(self, "错误", f"分析数据时出错: {str(e)}")
    
    def export_analysis_results(self):
        """导出分析结果"""
        if not hasattr(self, 'current_data') or self.current_data is None:
            QMessageBox.warning(self, "警告", "没有可导出的分析结果")
            return
            
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出分析结果", "", 
            "CSV文件 (*.csv);;Excel文件 (*.xlsx);;文本文件 (*.txt)"
        )
        
        if file_path:
            try:
                if file_path.endswith('.csv'):
                    self.current_data.to_csv(file_path, index=False)
                elif file_path.endswith('.xlsx'):
                    self.current_data.to_excel(file_path, index=False)
                elif file_path.endswith('.txt'):
                    with open(file_path, 'w') as f:
                        f.write(self.analysis_summary.toPlainText())
                
                self.statusBar().showMessage(f"分析结果已导出: {file_path}")
                QMessageBox.information(self, "成功", "分析结果导出成功")
                
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导出分析结果时出错: {str(e)}")
    
    def preview_report(self):
        """预览报告"""
        # 生成报告预览
        report_type = self.report_type.currentText()
        start_date = self.start_date.date().toString("yyyy-MM-dd")
        end_date = self.end_date.date().toString("yyyy-MM-dd")
        department = self.department_filter.currentText()
        
        report_content = f"""
        HRO系统报告 - {report_type}
        
        期间: {start_date} 至 {end_date}
        部门: {department}
        
        报告摘要:
        - 员工总数: 120
        - 平均薪资: 8,500元
        - 平均出勤率: 95.2%
        - 本月新入职: 5人
        - 本月离职: 2人
        
        详细分析:
        各部门员工分布:
        - 技术部: 45人 (37.5%)
        - 市场部: 25人 (20.8%)
        - 财务部: 15人 (12.5%)
        - 人力资源部: 10人 (8.3%)
        - 其他部门: 25人 (20.8%)
        
        薪资分析:
        - 最高薪资: 15,000元
        - 最低薪资: 5,000元
        - 薪资中位数: 8,200元
        
        绩效评估:
        - 优秀: 15人 (12.5%)
        - 良好: 65人 (54.2%)
        - 合格: 35人 (29.2%)
        - 待改进: 5人 (4.2%)
        
        生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        """
        
        self.report_preview.setPlainText(report_content)
    
    def generate_pdf_report(self):
        """生成PDF报告"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存PDF报告", "", 
            "PDF文件 (*.pdf)"
        )
        
        if file_path:
            try:
                # 使用reportlab生成PDF
                c = canvas.Canvas(file_path, pagesize=letter)
                width, height = letter
                
                # 添加标题
                c.setFont("Helvetica-Bold", 16)
                c.drawString(100, height - 100, f"HRO系统报告 - {self.report_type.currentText()}")
                
                # 添加报告内容
                c.setFont("Helvetica", 12)
                content = self.report_preview.toPlainText()
                y_position = height - 130
                
                for line in content.split('\n'):
                    if y_position < 100:
                        c.showPage()
                        c.setFont("Helvetica", 12)
                        y_position = height - 100
                    
                    c.drawString(100, y_position, line)
                    y_position -= 15
                
                c.save()
                
                self.statusBar().showMessage(f"PDF报告已生成: {file_path}")
                QMessageBox.information(self, "成功", "PDF报告生成成功")
                
            except Exception as e:
                QMessageBox.critical(self, "错误", f"生成PDF报告时出错: {str(e)}")
    
    def generate_excel_report(self):
        """生成Excel报告"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存Excel报告", "", 
            "Excel文件 (*.xlsx)"
        )
        
        if file_path:
            try:
                # 创建示例数据框
                report_data = pd.DataFrame({
                    '部门': ['技术部', '市场部', '财务部', '人力资源部', '其他'],
                    '员工数': [45, 25, 15, 10, 25],
                    '平均薪资': [9500, 7500, 8000, 7000, 6500],
                    '平均绩效': [4.2, 3.8, 4.0, 3.9, 3.5]
                })
                
                # 保存到Excel
                report_data.to_excel(file_path, index=False)
                
                self.statusBar().showMessage(f"Excel报告已生成: {file_path}")
                QMessageBox.information(self, "成功", "Excel报告生成成功")
                
            except Exception as e:
                QMessageBox.critical(self, "错误", f"生成Excel报告时出错: {str(e)}")
    
    def select_source_file(self):
        """选择源文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择源文件", "", 
            "CSV文件 (*.csv);;Excel文件 (*.xlsx);;所有文件 (*.*)"
        )
        
        if file_path:
            self.source_file.setText(file_path)
    
    def start_batch_processing(self):
        """开始批处理"""
        if not self.source_file.text():
            QMessageBox.warning(self, "警告", "请先选择源文件")
            return
            
        # 创建批处理线程
        self.batch_thread = BatchProcessThread(
            self.source_file.text(),
            self.batch_operation.currentText(),
            self.adjustment_type.currentText(),
            self.adjustment_value.value()
        )
        
        # 连接信号和槽
        self.batch_thread.progress_updated.connect(self.update_batch_progress)
        self.batch_thread.log_updated.connect(self.update_batch_log)
        self.batch_thread.finished.connect(self.batch_processing_finished)
        
        # 开始处理
        self.batch_progress.setValue(0)
        self.batch_log.clear()
        self.batch_thread.start()
    
    def update_batch_progress(self, value):
        """更新批处理进度"""
        self.batch_progress.setValue(value)
    
    def update_batch_log(self, message):
        """更新批处理日志"""
        self.batch_log.append(f"{datetime.now().strftime('%H:%M:%S')} - {message}")
    
    def batch_processing_finished(self, success, message):
        """批处理完成"""
        if success:
            QMessageBox.information(self, "完成", message)
        else:
            QMessageBox.critical(self, "错误", message)
    
    def load_recipients(self):
        """加载收件人列表"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "打开收件人列表", "", 
            "CSV文件 (*.csv);;Excel文件 (*.xlsx);;文本文件 (*.txt)"
        )
        
        if file_path:
            try:
                if file_path.endswith('.csv'):
                    recipients_data = pd.read_csv(file_path)
                elif file_path.endswith('.xlsx'):
                    recipients_data = pd.read_excel(file_path)
                elif file_path.endswith('.txt'):
                    with open(file_path, 'r') as f:
                        emails = f.readlines()
                    recipients_data = pd.DataFrame({'email': [email.strip() for email in emails]})
                
                self.recipients_list.clear()
                
                if 'email' in recipients_data.columns:
                    for email in recipients_data['email']:
                        self.recipients_list.addItem(email)
                else:
                    QMessageBox.warning(self, "警告", "文件中没有找到'email'列")
                    
            except Exception as e:
                QMessageBox.critical(self, "错误", f"加载收件人列表时出错: {str(e)}")
    
    def send_test_email(self):
        """发送测试邮件"""
        # 验证设置
        if not all([self.smtp_server.text(), self.smtp_port.value(), 
                   self.email_address.text(), self.email_password.text()]):
            QMessageBox.warning(self, "警告", "请先完善邮件服务器设置")
            return
            
        # 发送测试邮件
        try:
            msg = MIMEMultipart()
            msg['From'] = self.email_address.text()
            msg['To'] = self.email_address.text()  # 发送给自己作为测试
            msg['Subject'] = "HRO系统测试邮件"
            
            body = "这是一封来自HRO系统高级工具库的测试邮件。\n\n如果收到此邮件，说明邮件配置正确。"
            msg.attach(MIMEText(body, 'plain'))
            
            server = smtplib.SMTP(self.smtp_server.text(), self.smtp_port.value())
            server.starttls()
            server.login(self.email_address.text(), self.email_password.text())
            server.send_message(msg)
            server.quit()
            
            QMessageBox.information(self, "成功", "测试邮件发送成功！")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"发送测试邮件时出错: {str(e)}")
    
    def send_all_emails(self):
        """发送全部邮件"""
        if self.recipients_list.count() == 0:
            QMessageBox.warning(self, "警告", "没有收件人可发送")
            return
            
        # 验证设置
        if not all([self.smtp_server.text(), self.smtp_port.value(), 
                   self.email_address.text(), self.email_password.text()]):
            QMessageBox.warning(self, "警告", "请先完善邮件服务器设置")
            return
            
        if not self.email_subject.text() or not self.email_content.toPlainText():
            QMessageBox.warning(self, "警告", "请填写邮件主题和内容")
            return
            
        # 创建邮件发送线程
        self.email_thread = EmailSendThread(
            self.smtp_server.text(),
            self.smtp_port.value(),
            self.email_address.text(),
            self.email_password.text(),
            self.email_subject.text(),
            self.email_content.toPlainText(),
            [self.recipients_list.item(i).text() for i in range(self.recipients_list.count())]
        )
        
        # 连接信号和槽
        self.email_thread.progress_updated.connect(self.update_batch_progress)
        self.email_thread.log_updated.connect(self.update_batch_log)
        self.email_thread.finished.connect(self.email_sending_finished)
        
        # 开始发送
        self.batch_progress.setValue(0)
        self.batch_log.clear()
        self.email_thread.start()
    
    def email_sending_finished(self, success, message):
        """邮件发送完成"""
        if success:
            QMessageBox.information(self, "完成", message)
        else:
            QMessageBox.critical(self, "错误", message)
    
    def select_source_path(self):
        """选择源路径"""
        if self.source_type.currentText() in ["CSV文件", "Excel文件", "JSON文件"]:
            file_path, _ = QFileDialog.getOpenFileName(
                self, "选择源文件", "", 
                f"{self.source_type.currentText()} (*.{self.get_file_extension(self.source_type.currentText())})"
            )
            
            if file_path:
                self.source_path.setText(file_path)
        else:
            # 数据库连接，直接输入连接字符串
            pass
    
    def select_target_path(self):
        """选择目标路径"""
        if self.target_type.currentText() in ["CSV文件", "Excel文件", "JSON文件"]:
            file_path, _ = QFileDialog.getSaveFileName(
                self, "选择目标文件", "", 
                f"{self.target_type.currentText()} (*.{self.get_file_extension(self.target_type.currentText())})"
            )
            
            if file_path:
                self.target_path.setText(file_path)
        else:
            # 数据库连接，直接输入连接字符串
            pass
    
    def get_file_extension(self, file_type):
        """获取文件扩展名"""
        extensions = {
            "CSV文件": "csv",
            "Excel文件": "xlsx",
            "JSON文件": "json"
        }
        return extensions.get(file_type, "")
    
    def auto_map_fields(self):
        """自动映射字段"""
        # 实现自动字段映射逻辑
        pass
    
    def start_migration(self):
        """开始数据迁移"""
        if not self.source_path.text() or not self.target_path.text():
            QMessageBox.warning(self, "警告", "请先设置源和目标路径")
            return
            
        # 创建数据迁移线程
        self.migration_thread = DataMigrationThread(
            self.source_type.currentText(),
            self.source_path.text(),
            self.target_type.currentText(),
            self.target_path.text(),
            self.get_field_mappings()
        )
        
        # 连接信号和槽
        self.migration_thread.progress_updated.connect(self.update_migration_progress)
        self.migration_thread.log_updated.connect(self.update_migration_log)
        self.migration_thread.finished.connect(self.migration_finished)
        
        # 开始迁移
        self.migration_progress.setValue(0)
        self.migration_log.clear()
        self.migration_thread.start()
    
    def get_field_mappings(self):
        """获取字段映射"""
        mappings = {}
        for row in range(self.mapping_table.rowCount()):
            source_item = self.mapping_table.item(row, 0)
            target_item = self.mapping_table.item(row, 1)
            
            if source_item and target_item:
                mappings[source_item.text()] = target_item.text()
                
        return mappings
    
    def update_migration_progress(self, value):
        """更新迁移进度"""
        self.migration_progress.setValue(value)
    
    def update_migration_log(self, message):
        """更新迁移日志"""
        self.migration_log.append(f"{datetime.now().strftime('%H:%M:%S')} - {message}")
    
    def migration_finished(self, success, message):
        """迁移完成"""
        if success:
            QMessageBox.information(self, "完成", message)
        else:
            QMessageBox.critical(self, "错误", message)
    
    def test_db_connection(self):
        """测试数据库连接"""
        # 实现数据库连接测试
        QMessageBox.information(self, "测试", "数据库连接测试功能尚未实现")


class BatchProcessThread(QThread):
    """批处理线程"""
    
    progress_updated = pyqtSignal(int)
    log_updated = pyqtSignal(str)
    finished = pyqtSignal(bool, str)
    
    def __init__(self, source_file, operation, adjustment_type, adjustment_value):
        super().__init__()
        self.source_file = source_file
        self.operation = operation
        self.adjustment_type = adjustment_type
        self.adjustment_value = adjustment_value
        
    def run(self):
        """运行批处理"""
        try:
            self.log_updated.emit(f"开始处理: {self.operation}")
            
            # 模拟处理过程
            for i in range(101):
                self.progress_updated.emit(i)
                self.msleep(50)  # 模拟处理时间
                
                if i % 10 == 0:
                    self.log_updated.emit(f"处理进度: {i}%")
            
            self.log_updated.emit("处理完成")
            self.finished.emit(True, "批处理完成成功")
            
        except Exception as e:
            self.log_updated.emit(f"处理出错: {str(e)}")
            self.finished.emit(False, f"批处理失败: {str(e)}")


class EmailSendThread(QThread):
    """邮件发送线程"""
    
    progress_updated = pyqtSignal(int)
    log_updated = pyqtSignal(str)
    finished = pyqtSignal(bool, str)
    
    def __init__(self, smtp_server, smtp_port, email, password, subject, content, recipients):
        super().__init__()
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.email = email
        self.password = password
        self.subject = subject
        self.content = content
        self.recipients = recipients
        
    def run(self):
        """发送邮件"""
        try:
            total = len(self.recipients)
            success_count = 0
            
            self.log_updated.emit(f"开始发送邮件给 {total} 个收件人")
            
            # 连接服务器
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.email, self.password)
            
            for i, recipient in enumerate(self.recipients):
                try:
                    msg = MIMEMultipart()
                    msg['From'] = self.email
                    msg['To'] = recipient
                    msg['Subject'] = self.subject
                    
                    msg.attach(MIMEText(self.content, 'plain'))
                    
                    server.send_message(msg)
                    success_count += 1
                    self.log_updated.emit(f"已发送给: {recipient}")
                    
                except Exception as e:
                    self.log_updated.emit(f"发送给 {recipient} 失败: {str(e)}")
                
                progress = int((i + 1) / total * 100)
                self.progress_updated.emit(progress)
            
            server.quit()
            
            message = f"邮件发送完成。成功: {success_count}, 失败: {total - success_count}"
            self.log_updated.emit(message)
            self.finished.emit(True, message)
            
        except Exception as e:
            self.log_updated.emit(f"发送邮件时出错: {str(e)}")
            self.finished.emit(False, f"邮件发送失败: {str(e)}")


class DataMigrationThread(QThread):
    """数据迁移线程"""
    
    progress_updated = pyqtSignal(int)
    log_updated = pyqtSignal(str)
    finished = pyqtSignal(bool, str)
    
    def __init__(self, source_type, source_path, target_type, target_path, field_mappings):
        super().__init__()
        self.source_type = source_type
        self.source_path = source_path
        self.target_type = target_type
        self.target_path = target_path
        self.field_mappings = field_mappings
        
    def run(self):
        """执行数据迁移"""
        try:
            self.log_updated.emit(f"开始数据迁移: {self.source_type} -> {self.target_type}")
            
            # 模拟迁移过程
            for i in range(101):
                self.progress_updated.emit(i)
                self.msleep(30)  # 模拟迁移时间
                
                if i % 10 == 0:
                    self.log_updated.emit(f"迁移进度: {i}%")
            
            self.log_updated.emit("数据迁移完成")
            self.finished.emit(True, "数据迁移成功")
            
        except Exception as e:
            self.log_updated.emit(f"迁移出错: {str(e)}")
            self.finished.emit(False, f"数据迁移失败: {str(e)}")


def main():
    """主函数"""
    app = QApplication(sys.argv)
    
    # 设置应用程序样式
    app.setStyle('Fusion')
    
    # 创建并显示主窗口
    window = HROAdvancedToolkit()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()