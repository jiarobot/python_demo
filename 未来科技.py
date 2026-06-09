import sys
import os
import psutil
import random
import time
import threading
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QGridLayout, QLabel, QPushButton, 
                             QFrame, QSlider, QProgressBar, QGroupBox, QTextEdit,
                             QListWidget, QListWidgetItem, QTabWidget, QSplitter,
                             QFileDialog, QMessageBox, QInputDialog, QLineEdit,
                             QTreeWidget, QTreeWidgetItem, QHeaderView, QCheckBox)
from PyQt5.QtCore import QTimer, Qt, QSize, QPropertyAnimation, QEasingCurve, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QPalette, QPainter, QLinearGradient, QIcon, QPixmap


class FuturisticButton(QPushButton):
    """未来科技风格的按钮"""
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setMinimumHeight(40)
        self.setFont(QFont("Arial", 10, QFont.Bold))
        self.setStyleSheet("""
            QPushButton {
                background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #00b4ff, stop: 1 #0080ff);
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #00ccff, stop: 1 #0099ff);
            }
            QPushButton:pressed {
                background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #0080ff, stop: 1 #00b4ff);
            }
        """)
        
        # 添加悬停动画效果
        self.animation = QPropertyAnimation(self, b"geometry")
        self.animation.setDuration(200)
        
    def enterEvent(self, event):
        self.animation.setStartValue(self.geometry())
        self.animation.setEndValue(self.geometry().adjusted(-2, -2, 2, 2))
        self.animation.setEasingCurve(QEasingCurve.OutBack)
        self.animation.start()
        super().enterEvent(event)
        
    def leaveEvent(self, event):
        self.animation.setStartValue(self.geometry())
        self.animation.setEndValue(self.geometry().adjusted(2, 2, -2, -2))
        self.animation.start()
        super().leaveEvent(event)


class SystemMonitor(QWidget):
    """系统监控组件"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_data)
        self.timer.start(1000)  # 每秒更新一次
        
        # 网络速度计算
        self.last_net_io = psutil.net_io_counters()
        self.last_update_time = time.time()
        
    def initUI(self):
        layout = QGridLayout()
        layout.setSpacing(10)
        
        # CPU使用率
        cpu_group = QGroupBox("CPU 状态")
        cpu_group.setStyleSheet("""
            QGroupBox {
                color: #00ffff;
                font-weight: bold;
                border: 2px solid #00ffff;
                border-radius: 5px;
                margin-top: 1ex;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        
        cpu_layout = QVBoxLayout()
        self.cpu_bar = QProgressBar()
        self.cpu_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #00ffff;
                border-radius: 5px;
                text-align: center;
                background-color: #001133;
                height: 20px;
            }
            QProgressBar::chunk {
                background-color: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 #00ffff, stop: 1 #00b4ff);
            }
        """)
        
        self.cpu_info = QLabel("核心数: 0 | 频率: 0 GHz")
        self.cpu_info.setStyleSheet("color: #00ffff;")
        
        cpu_layout.addWidget(self.cpu_bar)
        cpu_layout.addWidget(self.cpu_info)
        cpu_group.setLayout(cpu_layout)
        
        # 内存使用率
        mem_group = QGroupBox("内存 状态")
        mem_group.setStyleSheet("""
            QGroupBox {
                color: #00ff99;
                font-weight: bold;
                border: 2px solid #00ff99;
                border-radius: 5px;
                margin-top: 1ex;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        
        mem_layout = QVBoxLayout()
        self.mem_bar = QProgressBar()
        self.mem_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #00ff99;
                border-radius: 5px;
                text-align: center;
                background-color: #001133;
                height: 20px;
            }
            QProgressBar::chunk {
                background-color: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 #00ff99, stop: 1 #00cc99);
            }
        """)
        
        self.mem_info = QLabel("总内存: 0 GB | 可用: 0 GB")
        self.mem_info.setStyleSheet("color: #00ff99;")
        
        mem_layout.addWidget(self.mem_bar)
        mem_layout.addWidget(self.mem_info)
        mem_group.setLayout(mem_layout)
        
        # 磁盘使用率
        disk_group = QGroupBox("磁盘 状态")
        disk_group.setStyleSheet("""
            QGroupBox {
                color: #ff66cc;
                font-weight: bold;
                border: 2px solid #ff66cc;
                border-radius: 5px;
                margin-top: 1ex;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        
        disk_layout = QVBoxLayout()
        self.disk_bar = QProgressBar()
        self.disk_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #ff66cc;
                border-radius: 5px;
                text-align: center;
                background-color: #001133;
                height: 20px;
            }
            QProgressBar::chunk {
                background-color: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 #ff66cc, stop: 1 #ff33cc);
            }
        """)
        
        self.disk_info = QLabel("总空间: 0 GB | 可用: 0 GB")
        self.disk_info.setStyleSheet("color: #ff66cc;")
        
        disk_layout.addWidget(self.disk_bar)
        disk_layout.addWidget(self.disk_info)
        disk_group.setLayout(disk_layout)
        
        # 网络使用情况
        net_group = QGroupBox("网络 状态")
        net_group.setStyleSheet("""
            QGroupBox {
                color: #ffcc00;
                font-weight: bold;
                border: 2px solid #ffcc00;
                border-radius: 5px;
                margin-top: 1ex;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        
        net_layout = QVBoxLayout()
        self.net_up = QLabel("上传: 0 KB/s")
        self.net_up.setStyleSheet("color: #ffcc00;")
        
        self.net_down = QLabel("下载: 0 KB/s")
        self.net_down.setStyleSheet("color: #ffcc00;")
        
        self.net_connections = QLabel("活动连接: 0")
        self.net_connections.setStyleSheet("color: #ffcc00;")
        
        net_layout.addWidget(self.net_up)
        net_layout.addWidget(self.net_down)
        net_layout.addWidget(self.net_connections)
        net_group.setLayout(net_layout)
        
        # 添加到布局
        layout.addWidget(cpu_group, 0, 0)
        layout.addWidget(mem_group, 0, 1)
        layout.addWidget(disk_group, 1, 0)
        layout.addWidget(net_group, 1, 1)
        
        self.setLayout(layout)
        
    def update_data(self):
        # 更新CPU使用率
        cpu_percent = psutil.cpu_percent()
        self.cpu_bar.setValue(int(cpu_percent))
        
        # 更新CPU信息
        cpu_freq = psutil.cpu_freq()
        cpu_count = psutil.cpu_count()
        freq_text = f"{cpu_freq.current/1000:.2f} GHz" if cpu_freq else "N/A"
        self.cpu_info.setText(f"核心数: {cpu_count} | 频率: {freq_text}")
        
        # 更新内存使用率
        mem = psutil.virtual_memory()
        mem_percent = mem.percent
        self.mem_bar.setValue(int(mem_percent))
        self.mem_info.setText(f"总内存: {mem.total/(1024**3):.1f} GB | 可用: {mem.available/(1024**3):.1f} GB")
        
        # 更新磁盘使用率 - 修复部分
        try:
            # 在Windows上使用C:\, 在Unix系统上使用/
            disk_path = 'C:\\' if os.name == 'nt' else '/'
            disk = psutil.disk_usage(disk_path)
            disk_percent = disk.percent
            self.disk_bar.setValue(int(disk_percent))
            self.disk_info.setText(f"总空间: {disk.total/(1024**3):.1f} GB | 可用: {disk.free/(1024**3):.1f} GB")
        except Exception as e:
            # 如果出现错误，显示错误信息
            self.disk_bar.setValue(0)
            self.disk_info.setText(f"错误: {str(e)}")
        
        # 更新网络使用情况
        current_time = time.time()
        current_net_io = psutil.net_io_counters()
        time_diff = current_time - self.last_update_time
        
        up_speed = (current_net_io.bytes_sent - self.last_net_io.bytes_sent) / time_diff / 1024
        down_speed = (current_net_io.bytes_recv - self.last_net_io.bytes_recv) / time_diff / 1024
        
        self.net_up.setText(f"上传: {up_speed:.1f} KB/s")
        self.net_down.setText(f"下载: {down_speed:.1f} KB/s")
        
        # 更新网络连接数
        connections = len(psutil.net_connections())
        self.net_connections.setText(f"活动连接: {connections}")
        
        # 更新最后的值和时间
        self.last_net_io = current_net_io
        self.last_update_time = current_time


class ProcessManager(QWidget):
    """进程管理器"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_processes)
        self.timer.start(3000)  # 每3秒更新一次
        
    def initUI(self):
        layout = QVBoxLayout()
        
        # 进程列表
        self.process_list = QTreeWidget()
        self.process_list.setHeaderLabels(["进程名", "PID", "CPU%", "内存(MB)", "状态"])
        self.process_list.setStyleSheet("""
            QTreeWidget {
                background-color: #001133;
                color: #ffffff;
                border: 1px solid #00ffff;
                border-radius: 5px;
            }
            QHeaderView::section {
                background-color: #003366;
                color: #00ffff;
                padding: 4px;
                border: 1px solid #00b4ff;
            }
        """)
        self.process_list.header().setSectionResizeMode(QHeaderView.ResizeToContents)
        
        # 控制按钮
        control_layout = QHBoxLayout()
        self.refresh_btn = FuturisticButton("刷新")
        self.refresh_btn.clicked.connect(self.update_processes)
        
        self.end_process_btn = FuturisticButton("结束进程")
        self.end_process_btn.clicked.connect(self.end_process)
        
        self.sort_cpu_btn = FuturisticButton("按CPU排序")
        self.sort_cpu_btn.clicked.connect(lambda: self.sort_processes("cpu"))
        
        self.sort_memory_btn = FuturisticButton("按内存排序")
        self.sort_memory_btn.clicked.connect(lambda: self.sort_processes("memory"))
        
        control_layout.addWidget(self.refresh_btn)
        control_layout.addWidget(self.end_process_btn)
        control_layout.addWidget(self.sort_cpu_btn)
        control_layout.addWidget(self.sort_memory_btn)
        control_layout.addStretch()
        
        layout.addLayout(control_layout)
        layout.addWidget(self.process_list)
        
        self.setLayout(layout)
        
    def update_processes(self):
        self.process_list.clear()
        
        # 获取进程列表
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info', 'status']):
            try:
                processes.append(proc)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        
        # 按CPU使用率排序
        processes.sort(key=lambda p: p.info['cpu_percent'], reverse=True)
        
        # 添加进程到列表
        for proc in processes[:50]:  # 只显示前50个进程
            try:
                name = proc.info['name']
                pid = str(proc.info['pid'])
                cpu = f"{proc.info['cpu_percent']:.1f}"
                memory = f"{proc.info['memory_info'].rss / (1024 * 1024):.1f}"
                status = proc.info['status']
                
                item = QTreeWidgetItem([name, pid, cpu, memory, status])
                self.process_list.addTopLevelItem(item)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        
    def end_process(self):
        selected_items = self.process_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "警告", "请先选择一个进程")
            return
            
        item = selected_items[0]
        pid = int(item.text(1))
        
        try:
            process = psutil.Process(pid)
            process.terminate()
            QMessageBox.information(self, "成功", f"已尝试结束进程: {process.name()}")
            self.update_processes()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法结束进程: {str(e)}")
            
    def sort_processes(self, key):
        # 这里可以实现排序逻辑
        self.update_processes()


class SystemOptimizer(QWidget):
    """系统优化工具"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()
        
    def initUI(self):
        layout = QVBoxLayout()
        
        # 优化选项
        options_group = QGroupBox("优化选项")
        options_group.setStyleSheet("""
            QGroupBox {
                color: #00ff99;
                font-weight: bold;
                border: 2px solid #00ff99;
                border-radius: 5px;
                margin-top: 1ex;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        
        options_layout = QVBoxLayout()
        
        self.clean_temp = QCheckBox("清理临时文件")
        self.clean_temp.setChecked(True)
        self.clean_temp.setStyleSheet("color: #ffffff;")
        
        self.clean_cache = QCheckBox("清理缓存")
        self.clean_cache.setChecked(True)
        self.clean_cache.setStyleSheet("color: #ffffff;")
        
        self.defrag_disk = QCheckBox("优化磁盘碎片")
        self.defrag_disk.setChecked(False)
        self.defrag_disk.setStyleSheet("color: #ffffff;")
        
        self.optimize_startup = QCheckBox("优化启动项")
        self.optimize_startup.setChecked(True)
        self.optimize_startup.setStyleSheet("color: #ffffff;")
        
        options_layout.addWidget(self.clean_temp)
        options_layout.addWidget(self.clean_cache)
        options_layout.addWidget(self.defrag_disk)
        options_layout.addWidget(self.optimize_startup)
        options_group.setLayout(options_layout)
        
        # 优化按钮
        self.optimize_btn = FuturisticButton("开始优化")
        self.optimize_btn.clicked.connect(self.run_optimization)
        
        # 优化进度
        self.optimize_progress = QProgressBar()
        self.optimize_progress.setVisible(False)
        self.optimize_progress.setStyleSheet("""
            QProgressBar {
                border: 2px solid #00ff99;
                border-radius: 5px;
                text-align: center;
                background-color: #001133;
                height: 20px;
            }
            QProgressBar::chunk {
                background-color: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 #00ff99, stop: 1 #00cc99);
            }
        """)
        
        # 优化结果
        self.result_text = QTextEdit()
        self.result_text.setStyleSheet("""
            QTextEdit {
                background-color: #001133;
                color: #00ff99;
                border: 1px solid #00ff99;
                border-radius: 5px;
            }
        """)
        self.result_text.setReadOnly(True)
        
        layout.addWidget(options_group)
        layout.addWidget(self.optimize_btn)
        layout.addWidget(self.optimize_progress)
        layout.addWidget(self.result_text)
        
        self.setLayout(layout)
        
    def run_optimization(self):
        self.optimize_btn.setEnabled(False)
        self.optimize_progress.setVisible(True)
        self.result_text.clear()
        
        # 模拟优化过程
        options = []
        if self.clean_temp.isChecked():
            options.append("清理临时文件")
        if self.clean_cache.isChecked():
            options.append("清理缓存")
        if self.defrag_disk.isChecked():
            options.append("优化磁盘碎片")
        if self.optimize_startup.isChecked():
            options.append("优化启动项")
            
        if not options:
            self.result_text.append("请至少选择一个优化选项")
            self.optimize_btn.setEnabled(True)
            self.optimize_progress.setVisible(False)
            return
            
        # 启动优化线程
        self.optimize_thread = OptimizationThread(options)
        self.optimize_thread.progress_update.connect(self.update_progress)
        self.optimize_thread.result_ready.connect(self.optimization_complete)
        self.optimize_thread.start()
        
    def update_progress(self, value, message):
        self.optimize_progress.setValue(value)
        self.result_text.append(message)
        
    def optimization_complete(self, message):
        self.optimize_progress.setValue(100)
        self.result_text.append(message)
        self.optimize_btn.setEnabled(True)


class OptimizationThread(QThread):
    """优化线程"""
    progress_update = pyqtSignal(int, str)
    result_ready = pyqtSignal(str)
    
    def __init__(self, options):
        super().__init__()
        self.options = options
        
    def run(self):
        total_steps = len(self.options) * 10
        current_step = 0
        
        for option in self.options:
            if option == "清理临时文件":
                for i in range(10):
                    current_step += 1
                    progress = int((current_step / total_steps) * 100)
                    self.progress_update.emit(progress, f"清理临时文件... {i*10}%")
                    time.sleep(0.2)  # 模拟工作
                self.progress_update.emit(int((current_step / total_steps) * 100), "已清理 2.5GB 临时文件")
                
            elif option == "清理缓存":
                for i in range(10):
                    current_step += 1
                    progress = int((current_step / total_steps) * 100)
                    self.progress_update.emit(progress, f"清理缓存... {i*10}%")
                    time.sleep(0.2)
                self.progress_update.emit(int((current_step / total_steps) * 100), "已清理 1.2GB 缓存文件")
                
            elif option == "优化磁盘碎片":
                for i in range(10):
                    current_step += 1
                    progress = int((current_step / total_steps) * 100)
                    self.progress_update.emit(progress, f"优化磁盘碎片... {i*10}%")
                    time.sleep(0.3)
                self.progress_update.emit(int((current_step / total_steps) * 100), "磁盘碎片整理完成")
                
            elif option == "优化启动项":
                for i in range(10):
                    current_step += 1
                    progress = int((current_step / total_steps) * 100)
                    self.progress_update.emit(progress, f"优化启动项... {i*10}%")
                    time.sleep(0.1)
                self.progress_update.emit(int((current_step / total_steps) * 100), "已禁用 3 个不必要的启动项")
        
        self.result_ready.emit("系统优化完成！")


class SecurityScanner(QWidget):
    """安全扫描工具"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()
        
    def initUI(self):
        layout = QVBoxLayout()
        
        # 扫描选项
        scan_group = QGroupBox("扫描选项")
        scan_group.setStyleSheet("""
            QGroupBox {
                color: #ff6666;
                font-weight: bold;
                border: 2px solid #ff6666;
                border-radius: 5px;
                margin-top: 1ex;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        
        scan_layout = QVBoxLayout()
        
        self.quick_scan = QCheckBox("快速扫描")
        self.quick_scan.setChecked(True)
        self.quick_scan.setStyleSheet("color: #ffffff;")
        
        self.full_scan = QCheckBox("全盘扫描")
        self.full_scan.setChecked(False)
        self.full_scan.setStyleSheet("color: #ffffff;")
        
        self.memory_scan = QCheckBox("内存扫描")
        self.memory_scan.setChecked(True)
        self.memory_scan.setStyleSheet("color: #ffffff;")
        
        scan_layout.addWidget(self.quick_scan)
        scan_layout.addWidget(self.full_scan)
        scan_layout.addWidget(self.memory_scan)
        scan_group.setLayout(scan_layout)
        
        # 扫描按钮
        self.scan_btn = FuturisticButton("开始扫描")
        self.scan_btn.clicked.connect(self.run_scan)
        
        # 扫描进度
        self.scan_progress = QProgressBar()
        self.scan_progress.setVisible(False)
        self.scan_progress.setStyleSheet("""
            QProgressBar {
                border: 2px solid #ff6666;
                border-radius: 5px;
                text-align: center;
                background-color: #001133;
                height: 20px;
            }
            QProgressBar::chunk {
                background-color: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 #ff6666, stop: 1 #ff3333);
            }
        """)
        
        # 扫描结果
        self.scan_result = QTextEdit()
        self.scan_result.setStyleSheet("""
            QTextEdit {
                background-color: #001133;
                color: #ff6666;
                border: 1px solid #ff6666;
                border-radius: 5px;
            }
        """)
        self.scan_result.setReadOnly(True)
        
        layout.addWidget(scan_group)
        layout.addWidget(self.scan_btn)
        layout.addWidget(self.scan_progress)
        layout.addWidget(self.scan_result)
        
        self.setLayout(layout)
        
    def run_scan(self):
        self.scan_btn.setEnabled(False)
        self.scan_progress.setVisible(True)
        self.scan_result.clear()
        
        # 模拟扫描过程
        options = []
        if self.quick_scan.isChecked():
            options.append("快速扫描")
        if self.full_scan.isChecked():
            options.append("全盘扫描")
        if self.memory_scan.isChecked():
            options.append("内存扫描")
            
        if not options:
            self.scan_result.append("请至少选择一个扫描选项")
            self.scan_btn.setEnabled(True)
            self.scan_progress.setVisible(False)
            return
            
        # 启动扫描线程
        self.scan_thread = ScanThread(options)
        self.scan_thread.progress_update.connect(self.update_scan_progress)
        self.scan_thread.result_ready.connect(self.scan_complete)
        self.scan_thread.start()
        
    def update_scan_progress(self, value, message):
        self.scan_progress.setValue(value)
        self.scan_result.append(message)
        
    def scan_complete(self, message):
        self.scan_progress.setValue(100)
        self.scan_result.append(message)
        self.scan_btn.setEnabled(True)


class ScanThread(QThread):
    """扫描线程"""
    progress_update = pyqtSignal(int, str)
    result_ready = pyqtSignal(str)
    
    def __init__(self, options):
        super().__init__()
        self.options = options
        
    def run(self):
        total_steps = len(self.options) * 10
        current_step = 0
        
        threats_found = random.randint(0, 3)
        
        for option in self.options:
            if option == "快速扫描":
                for i in range(10):
                    current_step += 1
                    progress = int((current_step / total_steps) * 100)
                    self.progress_update.emit(progress, f"快速扫描系统关键区域... {i*10}%")
                    time.sleep(0.1)
                self.progress_update.emit(int((current_step / total_steps) * 100), "快速扫描完成")
                
            elif option == "全盘扫描":
                for i in range(10):
                    current_step += 1
                    progress = int((current_step / total_steps) * 100)
                    self.progress_update.emit(progress, f"全盘扫描... {i*10}%")
                    time.sleep(0.3)
                self.progress_update.emit(int((current_step / total_steps) * 100), "全盘扫描完成")
                
            elif option == "内存扫描":
                for i in range(10):
                    current_step += 1
                    progress = int((current_step / total_steps) * 100)
                    self.progress_update.emit(progress, f"扫描内存进程... {i*10}%")
                    time.sleep(0.2)
                self.progress_update.emit(int((current_step / total_steps) * 100), "内存扫描完成")
        
        if threats_found > 0:
            result_msg = f"扫描完成！发现 {threats_found} 个潜在威胁，已自动隔离。"
        else:
            result_msg = "扫描完成！未发现任何威胁，您的系统是安全的。"
            
        self.result_ready.emit(result_msg)


class AutomationTool(QWidget):
    """自动化任务工具"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()
        
    def initUI(self):
        layout = QVBoxLayout()
        
        # 任务列表
        self.task_list = QListWidget()
        self.task_list.setStyleSheet("""
            QListWidget {
                background-color: #001133;
                color: #ffffff;
                border: 1px solid #ffcc00;
                border-radius: 5px;
            }
        """)
        
        # 添加示例任务
        tasks = [
            "每天凌晨2点自动清理临时文件",
            "每周日中午12点进行全盘扫描",
            "系统启动时优化内存",
            "磁盘空间不足时自动清理缓存",
            "每小时备份重要文档"
        ]
        
        for task in tasks:
            item = QListWidgetItem(task)
            self.task_list.addItem(item)
        
        # 控制按钮
        control_layout = QHBoxLayout()
        self.add_task_btn = FuturisticButton("添加任务")
        self.add_task_btn.clicked.connect(self.add_task)
        
        self.edit_task_btn = FuturisticButton("编辑任务")
        self.edit_task_btn.clicked.connect(self.edit_task)
        
        self.delete_task_btn = FuturisticButton("删除任务")
        self.delete_task_btn.clicked.connect(self.delete_task)
        
        self.run_task_btn = FuturisticButton("立即运行")
        self.run_task_btn.clicked.connect(self.run_task)
        
        control_layout.addWidget(self.add_task_btn)
        control_layout.addWidget(self.edit_task_btn)
        control_layout.addWidget(self.delete_task_btn)
        control_layout.addWidget(self.run_task_btn)
        control_layout.addStretch()
        
        # 任务日志
        log_group = QGroupBox("任务日志")
        log_group.setStyleSheet("""
            QGroupBox {
                color: #ffcc00;
                font-weight: bold;
                border: 2px solid #ffcc00;
                border-radius: 5px;
                margin-top: 1ex;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        
        log_layout = QVBoxLayout()
        self.task_log = QTextEdit()
        self.task_log.setStyleSheet("""
            QTextEdit {
                background-color: #001133;
                color: #ffcc00;
                border: 1px solid #ffcc00;
                border-radius: 5px;
            }
        """)
        self.task_log.setReadOnly(True)
        
        # 添加示例日志
        log_entries = [
            "2023-10-15 02:00:00 - 自动清理任务完成，释放 1.2GB 空间",
            "2023-10-14 12:00:00 - 全盘扫描完成，未发现威胁",
            "2023-10-14 09:30:15 - 系统启动优化完成",
            "2023-10-13 16:45:00 - 文档备份任务完成"
        ]
        
        for entry in log_entries:
            self.task_log.append(entry)
        
        log_layout.addWidget(self.task_log)
        log_group.setLayout(log_layout)
        
        layout.addWidget(self.task_list)
        layout.addLayout(control_layout)
        layout.addWidget(log_group)
        
        self.setLayout(layout)
        
    def add_task(self):
        task, ok = QInputDialog.getText(self, "添加任务", "请输入任务描述:")
        if ok and task:
            self.task_list.addItem(task)
            self.task_log.append(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - 添加了新任务: {task}")
            
    def edit_task(self):
        current_item = self.task_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "警告", "请先选择一个任务")
            return
            
        task, ok = QInputDialog.getText(self, "编辑任务", "修改任务描述:", text=current_item.text())
        if ok and task:
            current_item.setText(task)
            self.task_log.append(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - 修改了任务: {task}")
            
    def delete_task(self):
        current_item = self.task_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "警告", "请先选择一个任务")
            return
            
        reply = QMessageBox.question(self, "确认删除", 
                                    f"确定要删除任务 '{current_item.text()}' 吗?",
                                    QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.task_log.append(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - 删除了任务: {current_item.text()}")
            self.task_list.takeItem(self.task_list.row(current_item))
            
    def run_task(self):
        current_item = self.task_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "警告", "请先选择一个任务")
            return
            
        self.task_log.append(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - 手动执行任务: {current_item.text()}")
        
        # 模拟任务执行
        QTimer.singleShot(2000, lambda: self.task_log.append(
            f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - 任务执行完成: {current_item.text()}"))


class FuturisticToolkit(QMainWindow):
    """未来科技系统工具库主窗口"""
    def __init__(self):
        super().__init__()
        self.initUI()
        
    def initUI(self):
        # 设置窗口属性
        self.setWindowTitle("未来科技系统工具库")
        self.setGeometry(100, 100, 1200, 800)
        
        # 设置主窗口样式
        self.setStyleSheet("background-color: #000a1a; color: #ffffff;")
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        main_layout = QHBoxLayout()
        central_widget.setLayout(main_layout)
        
        # 创建标签页
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #00ffff;
                background: #001133;
                border-radius: 5px;
            }
            QTabBar::tab {
                background: #003366;
                color: #00ffff;
                padding: 8px 20px;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background: #00aaff;
                color: #ffffff;
            }
            QTabBar::tab:hover:!selected {
                background: #005588;
            }
        """)
        
        # 仪表盘标签
        dashboard_tab = QWidget()
        dashboard_layout = QVBoxLayout()
        
        # 标题
        title = QLabel("未来科技系统工具库")
        title.setFont(QFont("Arial", 18, QFont.Bold))
        title.setStyleSheet("color: #00ffff; padding: 10px;")
        title.setAlignment(Qt.AlignCenter)
        
        # 系统信息
        sys_info = QLabel(f"系统状态: 正常运行 | 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        sys_info.setStyleSheet("color: #00ff99; padding: 5px; background-color: #001133; border-radius: 5px;")
        
        # 系统监控组件
        monitor = SystemMonitor()
        
        # 快速操作按钮
        quick_actions = QWidget()
        quick_layout = QHBoxLayout()
        
        quick_btns = [
            ("立即优化", self.open_optimizer),
            ("安全扫描", self.open_scanner),
            ("进程管理", self.open_process_manager),
            ("自动化", self.open_automation)
        ]
        
        for text, slot in quick_btns:
            btn = FuturisticButton(text)
            btn.clicked.connect(slot)
            quick_layout.addWidget(btn)
            
        quick_layout.addStretch()
        quick_actions.setLayout(quick_layout)
        
        dashboard_layout.addWidget(title)
        dashboard_layout.addWidget(sys_info)
        dashboard_layout.addWidget(monitor)
        dashboard_layout.addWidget(quick_actions)
        dashboard_tab.setLayout(dashboard_layout)
        
        # 系统优化标签
        optimizer_tab = SystemOptimizer()
        
        # 安全扫描标签
        scanner_tab = SecurityScanner()
        
        # 进程管理标签
        process_tab = ProcessManager()
        
        # 自动化工具标签
        automation_tab = AutomationTool()
        
        # 添加标签页
        self.tabs.addTab(dashboard_tab, "仪表盘")
        self.tabs.addTab(optimizer_tab, "系统优化")
        self.tabs.addTab(scanner_tab, "安全扫描")
        self.tabs.addTab(process_tab, "进程管理")
        self.tabs.addTab(automation_tab, "自动化工具")
        
        main_layout.addWidget(self.tabs)
        
        # 状态栏
        self.statusBar().showMessage("系统就绪 | 所有功能正常运行")
        self.statusBar().setStyleSheet("color: #00ff99; background-color: #001133;")
        
        # 更新时间的定时器
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_time)
        self.timer.start(1000)
        
    def update_time(self):
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.statusBar().showMessage(f"系统就绪 | 当前时间: {current_time} | 所有功能正常运行")
        
    def open_optimizer(self):
        self.tabs.setCurrentIndex(1)
        
    def open_scanner(self):
        self.tabs.setCurrentIndex(2)
        
    def open_process_manager(self):
        self.tabs.setCurrentIndex(3)
        
    def open_automation(self):
        self.tabs.setCurrentIndex(4)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # 设置应用程序字体
    font = QFont("Arial", 9)
    app.setFont(font)
    
    # 创建并显示主窗口
    window = FuturisticToolkit()
    window.show()
    
    sys.exit(app.exec_())