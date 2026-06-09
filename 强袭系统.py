import sys
import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QLineEdit, 
                             QTextEdit, QListWidget, QListWidgetItem, 
                             QTabWidget, QSplitter, QProgressBar, 
                             QMessageBox, QFileDialog, QComboBox, 
                             QCheckBox, QSpinBox, QDoubleSpinBox, 
                             QGroupBox, QTableWidget, QTableWidgetItem, 
                             QHeaderView, QTreeWidget, QTreeWidgetItem,
                             QMenu, QAction, QSystemTrayIcon, QStyle)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QSettings, QSize
from PyQt5.QtGui import QIcon, QFont, QPalette, QColor, QPixmap, QPainter
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply


class AsyncWorker(QThread):
    """异步工作线程基类"""
    finished = pyqtSignal(object)
    error = pyqtSignal(str)
    progress = pyqtSignal(int)
    
    def __init__(self, task_func, *args, **kwargs):
        super().__init__()
        self.task_func = task_func
        self.args = args
        self.kwargs = kwargs
        
    def run(self):
        try:
            result = self.task_func(*self.args, **self.kwargs)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class AdvancedLogger:
    """高级日志记录器"""
    def __init__(self, name="AdvancedToolkit"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        
        # 创建格式化器
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # 控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # 文件处理器
        file_handler = logging.FileHandler(f"{name}_{datetime.now().strftime('%Y%m%d')}.log")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
    
    def debug(self, msg):
        self.logger.debug(msg)
    
    def info(self, msg):
        self.logger.info(msg)
    
    def warning(self, msg):
        self.logger.warning(msg)
    
    def error(self, msg):
        self.logger.error(msg)
    
    def critical(self, msg):
        self.logger.critical(msg)


class SettingsManager:
    """设置管理器"""
    def __init__(self, company="AssaultSystem", app="AdvancedToolkit"):
        self.settings = QSettings(company, app)
    
    def set_value(self, key, value):
        self.settings.setValue(key, value)
    
    def get_value(self, key, default=None):
        return self.settings.value(key, default)
    
    def save_dict(self, key, data_dict):
        """保存字典到设置"""
        json_str = json.dumps(data_dict)
        self.set_value(key, json_str)
    
    def load_dict(self, key, default=None):
        """从设置加载字典"""
        if default is None:
            default = {}
        json_str = self.get_value(key, "{}")
        try:
            return json.loads(json_str)
        except:
            return default


class NetworkManager:
    """网络管理器"""
    def __init__(self):
        self.manager = QNetworkAccessManager()
        self.logger = AdvancedLogger("NetworkManager")
    
    def get(self, url, callback, error_callback=None):
        """发送GET请求"""
        request = QNetworkRequest(url)
        reply = self.manager.get(request)
        reply.finished.connect(lambda: self._handle_response(reply, callback, error_callback))
    
    def _handle_response(self, reply, callback, error_callback):
        """处理网络响应"""
        if reply.error() == QNetworkReply.NoError:
            data = reply.readAll().data().decode('utf-8')
            callback(data)
        else:
            error_msg = f"Network error: {reply.errorString()}"
            self.logger.error(error_msg)
            if error_callback:
                error_callback(error_msg)
        reply.deleteLater()


class CustomWidgets:
    """自定义小部件集合"""
    
    @staticmethod
    def create_styled_button(text, icon_path=None, tooltip="", style="primary"):
        """创建样式化按钮"""
        button = QPushButton(text)
        
        if icon_path and os.path.exists(icon_path):
            button.setIcon(QIcon(icon_path))
        
        if tooltip:
            button.setToolTip(tooltip)
        
        # 应用样式
        styles = {
            "primary": """
                QPushButton {
                    background-color: #007bff;
                    color: white;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 4px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #0056b3;
                }
                QPushButton:pressed {
                    background-color: #004085;
                }
            """,
            "success": """
                QPushButton {
                    background-color: #28a745;
                    color: white;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 4px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #1e7e34;
                }
            """,
            "danger": """
                QPushButton {
                    background-color: #dc3545;
                    color: white;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 4px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #c82333;
                }
            """
        }
        
        if style in styles:
            button.setStyleSheet(styles[style])
        
        return button
    
    @staticmethod
    def create_group_box(title, layout):
        """创建分组框"""
        group = QGroupBox(title)
        group.setLayout(layout)
        return group


class DataTableWidget(QWidget):
    """数据表格小部件"""
    def __init__(self, headers, parent=None):
        super().__init__(parent)
        self.headers = headers
        self.data = []
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 搜索框
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索...")
        self.search_input.textChanged.connect(self.filter_data)
        search_layout.addWidget(QLabel("搜索:"))
        search_layout.addWidget(self.search_input)
        layout.addLayout(search_layout)
        
        # 表格
        self.table = QTableWidget()
        self.table.setColumnCount(len(self.headers))
        self.table.setHorizontalHeaderLabels(self.headers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table)
        
        # 操作按钮
        button_layout = QHBoxLayout()
        self.export_btn = CustomWidgets.create_styled_button("导出数据", style="primary")
        self.export_btn.clicked.connect(self.export_data)
        self.refresh_btn = CustomWidgets.create_styled_button("刷新", style="success")
        self.refresh_btn.clicked.connect(self.refresh_data)
        
        button_layout.addWidget(self.export_btn)
        button_layout.addWidget(self.refresh_btn)
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def set_data(self, data):
        """设置表格数据"""
        self.data = data
        self.refresh_table()
    
    def refresh_table(self):
        """刷新表格显示"""
        self.table.setRowCount(0)
        for row_data in self.data:
            row = self.table.rowCount()
            self.table.insertRow(row)
            for col, value in enumerate(row_data):
                item = QTableWidgetItem(str(value))
                self.table.setItem(row, col, item)
    
    def filter_data(self):
        """根据搜索条件过滤数据"""
        search_text = self.search_input.text().lower()
        if not search_text:
            self.refresh_table()
            return
        
        filtered_data = []
        for row_data in self.data:
            if any(search_text in str(cell).lower() for cell in row_data):
                filtered_data.append(row_data)
        
        self.table.setRowCount(0)
        for row_data in filtered_data:
            row = self.table.rowCount()
            self.table.insertRow(row)
            for col, value in enumerate(row_data):
                item = QTableWidgetItem(str(value))
                self.table.setItem(row, col, item)
    
    def export_data(self):
        """导出数据到文件"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出数据", "", "CSV文件 (*.csv);;所有文件 (*)"
        )
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    # 写入表头
                    f.write(','.join(self.headers) + '\n')
                    # 写入数据
                    for row in self.data:
                        f.write(','.join(str(cell) for cell in row) + '\n')
                QMessageBox.information(self, "成功", f"数据已导出到 {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导出失败: {str(e)}")
    
    def refresh_data(self):
        """刷新数据（子类可重写此方法）"""
        self.refresh_table()


class TaskManager(QWidget):
    """任务管理器"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.tasks = {}
        self.task_id_counter = 0
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 任务列表
        self.task_list = QListWidget()
        layout.addWidget(self.task_list)
        
        # 控制按钮
        button_layout = QHBoxLayout()
        self.start_btn = CustomWidgets.create_styled_button("开始任务", style="primary")
        self.start_btn.clicked.connect(self.start_task)
        self.stop_btn = CustomWidgets.create_styled_button("停止任务", style="danger")
        self.stop_btn.clicked.connect(self.stop_task)
        self.clear_btn = CustomWidgets.create_styled_button("清除完成", style="success")
        self.clear_btn.clicked.connect(self.clear_completed)
        
        button_layout.addWidget(self.start_btn)
        button_layout.addWidget(self.stop_btn)
        button_layout.addWidget(self.clear_btn)
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def add_task(self, name, task_func, *args, **kwargs):
        """添加新任务"""
        task_id = self.task_id_counter
        self.task_id_counter += 1
        
        # 创建任务项
        item = QListWidgetItem(f"{name} (等待中)")
        item.setData(Qt.UserRole, task_id)
        self.task_list.addItem(item)
        
        # 存储任务信息
        self.tasks[task_id] = {
            'name': name,
            'worker': None,
            'item': item,
            'status': 'pending'  # pending, running, completed, error
        }
        
        # 创建异步工作线程
        worker = AsyncWorker(task_func, *args, **kwargs)
        worker.finished.connect(lambda result: self.task_finished(task_id, result))
        worker.error.connect(lambda error: self.task_error(task_id, error))
        worker.progress.connect(lambda progress: self.task_progress(task_id, progress))
        
        self.tasks[task_id]['worker'] = worker
        
        return task_id
    
    def start_task(self):
        """开始选中的任务"""
        current_item = self.task_list.currentItem()
        if current_item:
            task_id = current_item.data(Qt.UserRole)
            task = self.tasks.get(task_id)
            if task and task['status'] == 'pending':
                task['worker'].start()
                task['status'] = 'running'
                current_item.setText(f"{task['name']} (运行中)")
    
    def stop_task(self):
        """停止选中的任务"""
        current_item = self.task_list.currentItem()
        if current_item:
            task_id = current_item.data(Qt.UserRole)
            task = self.tasks.get(task_id)
            if task and task['status'] == 'running':
                task['worker'].terminate()
                task['worker'].wait()
                task['status'] = 'error'
                current_item.setText(f"{task['name']} (已停止)")
    
    def task_finished(self, task_id, result):
        """任务完成回调"""
        task = self.tasks.get(task_id)
        if task:
            task['status'] = 'completed'
            task['item'].setText(f"{task['name']} (已完成)")
    
    def task_error(self, task_id, error):
        """任务错误回调"""
        task = self.tasks.get(task_id)
        if task:
            task['status'] = 'error'
            task['item'].setText(f"{task['name']} (错误: {error})")
    
    def task_progress(self, task_id, progress):
        """任务进度回调"""
        task = self.tasks.get(task_id)
        if task:
            task['item'].setText(f"{task['name']} (进度: {progress}%)")
    
    def clear_completed(self):
        """清除已完成的任务"""
        items_to_remove = []
        for i in range(self.task_list.count()):
            item = self.task_list.item(i)
            task_id = item.data(Qt.UserRole)
            task = self.tasks.get(task_id)
            if task and task['status'] in ['completed', 'error']:
                items_to_remove.append(item)
        
        for item in items_to_remove:
            task_id = item.data(Qt.UserRole)
            self.tasks.pop(task_id, None)
            self.task_list.takeItem(self.task_list.row(item))


class AdvancedToolkit(QMainWindow):
    """强袭系统高级工具库主窗口"""
    def __init__(self):
        super().__init__()
        self.logger = AdvancedLogger("AdvancedToolkit")
        self.settings = SettingsManager()
        self.network = NetworkManager()
        
        self.init_ui()
        self.load_settings()
    
    def init_ui(self):
        self.setWindowTitle("强袭系统高级工具库")
        self.setGeometry(100, 100, 1200, 800)
        
        # 创建中央部件和主布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # 创建标签页
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        # 添加工具标签页
        self.setup_data_tab()
        self.setup_task_tab()
        self.setup_network_tab()
        self.setup_settings_tab()
        
        # 创建状态栏
        self.statusBar().showMessage("就绪")
        
        # 创建系统托盘图标
        self.setup_tray_icon()
    
    def setup_data_tab(self):
        """设置数据管理标签页"""
        data_tab = QWidget()
        layout = QVBoxLayout(data_tab)
        
        # 示例数据表格
        headers = ["ID", "名称", "状态", "创建时间"]
        sample_data = [
            [1, "任务A", "运行中", "2023-01-01 10:00"],
            [2, "任务B", "已完成", "2023-01-01 11:00"],
            [3, "任务C", "等待中", "2023-01-01 12:00"],
        ]
        
        self.data_table = DataTableWidget(headers)
        self.data_table.set_data(sample_data)
        layout.addWidget(self.data_table)
        
        self.tab_widget.addTab(data_tab, "数据管理")
    
    def setup_task_tab(self):
        """设置任务管理标签页"""
        task_tab = QWidget()
        layout = QVBoxLayout(task_tab)
        
        self.task_manager = TaskManager()
        layout.addWidget(self.task_manager)
        
        # 添加示例任务按钮
        demo_btn = CustomWidgets.create_styled_button("添加示例任务", style="primary")
        demo_btn.clicked.connect(self.add_demo_task)
        layout.addWidget(demo_btn)
        
        self.tab_widget.addTab(task_tab, "任务管理")
    
    def setup_network_tab(self):
        """设置网络工具标签页"""
        network_tab = QWidget()
        layout = QVBoxLayout(network_tab)
        
        # 网络请求演示
        network_group = CustomWidgets.create_group_box("网络请求", QVBoxLayout())
        
        url_layout = QHBoxLayout()
        url_layout.addWidget(QLabel("URL:"))
        self.url_input = QLineEdit("https://httpbin.org/json")
        url_layout.addWidget(self.url_input)
        
        request_btn = CustomWidgets.create_styled_button("发送请求", style="primary")
        request_btn.clicked.connect(self.send_network_request)
        url_layout.addWidget(request_btn)
        
        network_group.layout().addLayout(url_layout)
        
        self.response_text = QTextEdit()
        self.response_text.setPlaceholderText("响应将显示在这里...")
        network_group.layout().addWidget(self.response_text)
        
        layout.addWidget(network_group)
        layout.addStretch()
        
        self.tab_widget.addTab(network_tab, "网络工具")
    
    def setup_settings_tab(self):
        """设置设置标签页"""
        settings_tab = QWidget()
        layout = QVBoxLayout(settings_tab)
        
        # 主题设置
        theme_group = CustomWidgets.create_group_box("主题设置", QVBoxLayout())
        
        theme_layout = QHBoxLayout()
        theme_layout.addWidget(QLabel("主题:"))
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["默认", "深色", "浅色"])
        theme_layout.addWidget(self.theme_combo)
        
        apply_theme_btn = CustomWidgets.create_styled_button("应用主题", style="primary")
        apply_theme_btn.clicked.connect(self.apply_theme)
        theme_layout.addWidget(apply_theme_btn)
        
        theme_group.layout().addLayout(theme_layout)
        layout.addWidget(theme_group)
        
        # 其他设置
        other_group = CustomWidgets.create_group_box("其他设置", QVBoxLayout())
        
        auto_save_layout = QHBoxLayout()
        self.auto_save_check = QCheckBox("自动保存设置")
        auto_save_layout.addWidget(self.auto_save_check)
        other_group.layout().addLayout(auto_save_layout)
        
        layout.addWidget(other_group)
        layout.addStretch()
        
        self.tab_widget.addTab(settings_tab, "设置")
    
    def setup_tray_icon(self):
        """设置系统托盘图标"""
        if not QSystemTrayIcon.isSystemTrayAvailable():
            self.logger.warning("系统托盘不可用")
            return
        
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.style().standardIcon(QStyle.SP_ComputerIcon))
        
        # 创建托盘菜单
        tray_menu = QMenu()
        
        show_action = QAction("显示", self)
        show_action.triggered.connect(self.show)
        tray_menu.addAction(show_action)
        
        hide_action = QAction("隐藏", self)
        hide_action.triggered.connect(self.hide)
        tray_menu.addAction(hide_action)
        
        tray_menu.addSeparator()
        
        quit_action = QAction("退出", self)
        quit_action.triggered.connect(self.close_application)
        tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.tray_icon_activated)
        self.tray_icon.show()
    
    def tray_icon_activated(self, reason):
        """托盘图标激活处理"""
        if reason == QSystemTrayIcon.DoubleClick:
            if self.isVisible():
                self.hide()
            else:
                self.show()
                self.activateWindow()
    
    def add_demo_task(self):
        """添加演示任务"""
        def demo_task():
            import time
            for i in range(1, 101):
                time.sleep(0.05)  # 模拟工作
                self.task_manager.task_progress(task_id, i)
            return "任务完成"
        
        task_id = self.task_manager.add_task("演示任务", demo_task)
        self.task_manager.start_task()
    
    def send_network_request(self):
        """发送网络请求"""
        url = self.url_input.text()
        if not url:
            QMessageBox.warning(self, "警告", "请输入URL")
            return
        
        self.response_text.clear()
        self.response_text.append(f"正在请求: {url}")
        
        def handle_response(data):
            self.response_text.append("响应接收成功:")
            self.response_text.append(data)
        
        def handle_error(error):
            self.response_text.append(f"请求错误: {error}")
        
        self.network.get(url, handle_response, handle_error)
    
    def apply_theme(self):
        """应用主题"""
        theme = self.theme_combo.currentText()
        
        if theme == "深色":
            self.apply_dark_theme()
        elif theme == "浅色":
            self.apply_light_theme()
        else:
            self.apply_default_theme()
        
        self.logger.info(f"已应用主题: {theme}")
        QMessageBox.information(self, "成功", f"已应用{theme}主题")
    
    def apply_dark_theme(self):
        """应用深色主题"""
        dark_palette = QPalette()
        dark_palette.setColor(QPalette.Window, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.WindowText, Qt.white)
        dark_palette.setColor(QPalette.Base, QColor(25, 25, 25))
        dark_palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ToolTipBase, Qt.white)
        dark_palette.setColor(QPalette.ToolTipText, Qt.white)
        dark_palette.setColor(QPalette.Text, Qt.white)
        dark_palette.setColor(QPalette.Button, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ButtonText, Qt.white)
        dark_palette.setColor(QPalette.BrightText, Qt.red)
        dark_palette.setColor(QPalette.Link, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.HighlightedText, Qt.black)
        
        QApplication.setPalette(dark_palette)
    
    def apply_light_theme(self):
        """应用浅色主题"""
        QApplication.setPalette(QApplication.style().standardPalette())
    
    def apply_default_theme(self):
        """应用默认主题"""
        QApplication.setPalette(QApplication.style().standardPalette())
    
    def load_settings(self):
        """加载设置"""
        theme = self.settings.get_value("theme", "默认")
        index = self.theme_combo.findText(theme)
        if index >= 0:
            self.theme_combo.setCurrentIndex(index)
        
        auto_save = self.settings.get_value("auto_save", "true") == "true"
        self.auto_save_check.setChecked(auto_save)
    
    def save_settings(self):
        """保存设置"""
        self.settings.set_value("theme", self.theme_combo.currentText())
        self.settings.set_value("auto_save", "true" if self.auto_save_check.isChecked() else "false")
    
    def close_application(self):
        """关闭应用程序"""
        self.save_settings()
        self.logger.info("应用程序关闭")
        QApplication.quit()
    
    def closeEvent(self, event):
        """关闭事件处理"""
        if self.tray_icon.isVisible():
            self.hide()
            event.ignore()
        else:
            self.close_application()


def main():
    """主函数"""
    app = QApplication(sys.argv)
    app.setApplicationName("强袭系统高级工具库")
    app.setApplicationVersion("1.0.0")
    
    # 设置应用程序样式
    app.setStyle('Fusion')
    
    window = AdvancedToolkit()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()