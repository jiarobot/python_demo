import sys
import json
import threading
import time
from datetime import datetime
from collections import defaultdict
import socket
import paramiko
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTabWidget, QTreeWidget, QTreeWidgetItem,
                             QTableWidget, QTableWidgetItem, QTextEdit, QPushButton,
                             QLabel, QLineEdit, QProgressBar, QMessageBox, QSplitter,
                             QHeaderView, QComboBox, QCheckBox, QGroupBox, QFormLayout,
                             QSpinBox, QDoubleSpinBox, QFileDialog, QAction, QMenu,
                             QSystemTrayIcon, QStyle, QDialog, QDialogButtonBox)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QSettings, QSize
from PyQt5.QtGui import QFont, QIcon, QPalette, QColor, QTextCursor
from PyQt5.QtChart import QChart, QChartView, QLineSeries, QValueAxis, QDateTimeAxis
from PyQt5.QtCore import QDateTime

# 模拟网络设备数据
class NetworkDevice:
    def __init__(self, ip, hostname, device_type, status="unknown", community="public"):
        self.ip = ip
        self.hostname = hostname
        self.device_type = device_type
        self.status = status
        self.community = community
        self.uptime = 0
        self.cpu_usage = 0
        self.memory_usage = 0
        self.interfaces = {}
        self.config = ""
        self.last_seen = datetime.now()

# 设备发现线程
class DeviceDiscoveryThread(QThread):
    progress_signal = pyqtSignal(int)
    device_found_signal = pyqtSignal(object)
    finished_signal = pyqtSignal(list)
    
    def __init__(self, ip_range, timeout=2):
        super().__init__()
        self.ip_range = ip_range
        self.timeout = timeout
        self.found_devices = []
        self.is_running = True
        
    def run(self):
        # 模拟设备发现过程
        start_ip, end_ip = self.ip_range.split('-')
        start_parts = list(map(int, start_ip.split('.')))
        end_parts = list(map(int, end_ip.split('.')))
        
        total_ips = (end_parts[3] - start_parts[3]) + 1
        current_ip = 0
        
        for i in range(start_parts[3], end_parts[3] + 1):
            if not self.is_running:
                break
                
            ip = f"{start_parts[0]}.{start_parts[1]}.{start_parts[2]}.{i}"
            
            # 模拟ping检测
            if self.simulate_ping(ip):
                # 模拟设备信息获取
                device = self.simulate_device_info(ip)
                self.found_devices.append(device)
                self.device_found_signal.emit(device)
            
            current_ip += 1
            progress = int((current_ip / total_ips) * 100)
            self.progress_signal.emit(progress)
            time.sleep(0.1)  # 避免UI冻结
            
        self.finished_signal.emit(self.found_devices)
    
    def stop(self):
        self.is_running = False
        
    def simulate_ping(self, ip):
        # 模拟ping响应，实际应用中应使用真实ping
        return int(ip.split('.')[-1]) % 3 != 0  # 模拟部分IP有响应
    
    def simulate_device_info(self, ip):
        # 模拟获取设备信息
        hostname = f"device-{ip.replace('.', '-')}"
        device_types = ["Router", "Switch", "Firewall", "Server"]
        device_type = device_types[int(ip.split('.')[-1]) % len(device_types)]
        
        statuses = ["up", "down"]
        status = statuses[0] if int(ip.split('.')[-1]) % 5 != 0 else statuses[1]
        
        return NetworkDevice(ip, hostname, device_type, status)

# 设备监控线程
class DeviceMonitorThread(QThread):
    update_signal = pyqtSignal(object)
    
    def __init__(self, devices, interval=30):
        super().__init__()
        self.devices = devices
        self.interval = interval
        self.is_running = True
        
    def run(self):
        while self.is_running:
            for device in self.devices:
                if not self.is_running:
                    break
                    
                # 模拟设备状态更新
                self.simulate_device_update(device)
                self.update_signal.emit(device)
                
            time.sleep(self.interval)
    
    def stop(self):
        self.is_running = False
        
    def simulate_device_update(self, device):
        # 模拟设备状态更新
        if device.status == "up":
            device.uptime += self.interval
            device.cpu_usage = max(0, min(100, device.cpu_usage + (10 - int(device.ip.split('.')[-1]) % 20)))
            device.memory_usage = max(0, min(100, device.memory_usage + (5 - int(device.ip.split('.')[-1]) % 10)))
            
            # 模拟接口状态
            if not device.interfaces:
                for i in range(1, 5):
                    device.interfaces[f"eth{i}"] = {
                        "status": "up" if (i + int(device.ip.split('.')[-1])) % 3 != 0 else "down",
                        "speed": "1Gbps",
                        "in_bytes": 1000 * i,
                        "out_bytes": 500 * i
                    }
            else:
                for intf in device.interfaces:
                    device.interfaces[intf]["in_bytes"] += 100
                    device.interfaces[intf]["out_bytes"] += 50

# 配置管理类
class ConfigurationManager:
    def __init__(self):
        self.configs = {}
        self.backups = {}
        
    def backup_config(self, device, config):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        key = f"{device.ip}_{timestamp}"
        self.backups[key] = {
            "device": device.ip,
            "timestamp": timestamp,
            "config": config
        }
        return key
    
    def get_config_backups(self, device_ip):
        return {k: v for k, v in self.backups.items() if v["device"] == device_ip}
    
    def restore_config(self, backup_key):
        if backup_key in self.backups:
            return self.backups[backup_key]["config"]
        return None

# 主窗口类
class NetworkManagerWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.devices = []
        self.selected_device = None
        self.config_manager = ConfigurationManager()
        self.monitor_thread = None
        self.discovery_thread = None
        
        self.init_ui()
        self.load_settings()
        
    def init_ui(self):
        self.setWindowTitle("高级网管管理系统")
        self.setGeometry(100, 100, 1200, 800)
        
        # 创建中央部件和主布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # 创建标签页
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)
        
        # 创建各个功能页面
        self.create_dashboard_tab()
        self.create_discovery_tab()
        self.create_monitoring_tab()
        self.create_configuration_tab()
        self.create_troubleshooting_tab()
        
        # 创建状态栏
        self.statusBar().showMessage("就绪")
        
        # 创建菜单栏
        self.create_menus()
        
        # 创建系统托盘图标
        self.create_tray_icon()
        
    def create_menus(self):
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu('文件')
        
        export_action = QAction('导出设备列表', self)
        export_action.triggered.connect(self.export_device_list)
        file_menu.addAction(export_action)
        
        import_action = QAction('导入设备列表', self)
        import_action.triggered.connect(self.import_device_list)
        file_menu.addAction(import_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction('退出', self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 工具菜单
        tools_menu = menubar.addMenu('工具')
        
        ping_action = QAction('Ping工具', self)
        ping_action.triggered.connect(self.show_ping_tool)
        tools_menu.addAction(ping_action)
        
        traceroute_action = QAction('Traceroute工具', self)
        traceroute_action.triggered.connect(self.show_traceroute_tool)
        tools_menu.addAction(traceroute_action)
        
        # 设置菜单
        settings_menu = menubar.addMenu('设置')
        
        preferences_action = QAction('首选项', self)
        preferences_action.triggered.connect(self.show_preferences)
        settings_menu.addAction(preferences_action)
        
    def create_tray_icon(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
            
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.style().standardIcon(QStyle.SP_ComputerIcon))
        
        tray_menu = QMenu(self)
        
        show_action = QAction("显示", self)
        show_action.triggered.connect(self.show)
        tray_menu.addAction(show_action)
        
        hide_action = QAction("隐藏", self)
        hide_action.triggered.connect(self.hide)
        tray_menu.addAction(hide_action)
        
        tray_menu.addSeparator()
        
        quit_action = QAction("退出", self)
        quit_action.triggered.connect(QApplication.quit)
        tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.tray_icon_activated)
        self.tray_icon.show()
        
    def tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self.show()
            self.activateWindow()
            
    def create_dashboard_tab(self):
        dashboard_tab = QWidget()
        layout = QVBoxLayout(dashboard_tab)
        
        # 创建统计信息区域
        stats_group = QGroupBox("系统概览")
        stats_layout = QHBoxLayout(stats_group)
        
        self.total_devices_label = QLabel("总设备: 0")
        self.up_devices_label = QLabel("在线设备: 0")
        self.down_devices_label = QLabel("离线设备: 0")
        self.alerts_label = QLabel("告警: 0")
        
        stats_layout.addWidget(self.total_devices_label)
        stats_layout.addWidget(self.up_devices_label)
        stats_layout.addWidget(self.down_devices_label)
        stats_layout.addWidget(self.alerts_label)
        stats_layout.addStretch()
        
        layout.addWidget(stats_group)
        
        # 创建设备列表
        self.device_tree = QTreeWidget()
        self.device_tree.setHeaderLabels(["IP地址", "主机名", "设备类型", "状态", "最后检测"])
        self.device_tree.itemSelectionChanged.connect(self.on_device_selected)
        layout.addWidget(self.device_tree)
        
        self.tabs.addTab(dashboard_tab, "仪表盘")
        
    def create_discovery_tab(self):
        discovery_tab = QWidget()
        layout = QVBoxLayout(discovery_tab)
        
        # 发现配置区域
        config_group = QGroupBox("发现配置")
        config_layout = QFormLayout(config_group)
        
        self.ip_range_input = QLineEdit("192.168.1.1-192.168.1.50")
        self.timeout_input = QSpinBox()
        self.timeout_input.setRange(1, 10)
        self.timeout_input.setValue(2)
        
        config_layout.addRow("IP范围:", self.ip_range_input)
        config_layout.addRow("超时(秒):", self.timeout_input)
        
        layout.addWidget(config_group)
        
        # 控制按钮
        button_layout = QHBoxLayout()
        
        self.discover_button = QPushButton("开始发现")
        self.discover_button.clicked.connect(self.start_discovery)
        
        self.stop_discover_button = QPushButton("停止发现")
        self.stop_discover_button.clicked.connect(self.stop_discovery)
        self.stop_discover_button.setEnabled(False)
        
        button_layout.addWidget(self.discover_button)
        button_layout.addWidget(self.stop_discover_button)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        
        # 进度条
        self.discovery_progress = QProgressBar()
        layout.addWidget(self.discovery_progress)
        
        # 发现结果
        self.discovery_results = QTableWidget()
        self.discovery_results.setColumnCount(5)
        self.discovery_results.setHorizontalHeaderLabels(["IP地址", "主机名", "设备类型", "状态", "操作"])
        layout.addWidget(self.discovery_results)
        
        self.tabs.addTab(discovery_tab, "设备发现")
        
    def create_monitoring_tab(self):
        monitoring_tab = QWidget()
        layout = QHBoxLayout(monitoring_tab)
        
        # 左侧设备列表
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        monitor_controls = QHBoxLayout()
        self.monitor_interval = QSpinBox()
        self.monitor_interval.setRange(10, 300)
        self.monitor_interval.setValue(30)
        self.monitor_interval.setSuffix("秒")
        
        self.start_monitor_button = QPushButton("开始监控")
        self.start_monitor_button.clicked.connect(self.start_monitoring)
        
        self.stop_monitor_button = QPushButton("停止监控")
        self.stop_monitor_button.clicked.connect(self.stop_monitoring)
        self.stop_monitor_button.setEnabled(False)
        
        monitor_controls.addWidget(QLabel("监控间隔:"))
        monitor_controls.addWidget(self.monitor_interval)
        monitor_controls.addWidget(self.start_monitor_button)
        monitor_controls.addWidget(self.stop_monitor_button)
        monitor_controls.addStretch()
        
        left_layout.addLayout(monitor_controls)
        
        self.monitor_device_tree = QTreeWidget()
        self.monitor_device_tree.setHeaderLabels(["设备", "状态", "CPU", "内存"])
        self.monitor_device_tree.itemSelectionChanged.connect(self.on_monitor_device_selected)
        left_layout.addWidget(self.monitor_device_tree)
        
        # 右侧图表区域
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        # 性能图表
        self.performance_chart = QChart()
        self.performance_chart.setTitle("设备性能")
        self.performance_chart.legend().setVisible(True)
        
        self.cpu_series = QLineSeries()
        self.cpu_series.setName("CPU使用率")
        
        self.memory_series = QLineSeries()
        self.memory_series.setName("内存使用率")
        
        self.performance_chart.addSeries(self.cpu_series)
        self.performance_chart.addSeries(self.memory_series)
        
        # 创建时间轴
        self.time_axis = QDateTimeAxis()
        self.time_axis.setTickCount(10)
        self.time_axis.setFormat("hh:mm:ss")
        self.performance_chart.addAxis(self.time_axis, Qt.AlignBottom)
        
        # 创建值轴
        self.value_axis = QValueAxis()
        self.value_axis.setLabelFormat("%d")
        self.value_axis.setTitleText("百分比")
        self.value_axis.setRange(0, 100)
        self.performance_chart.addAxis(self.value_axis, Qt.AlignLeft)
        
        # 将系列附加到轴
        self.cpu_series.attachAxis(self.time_axis)
        self.cpu_series.attachAxis(self.value_axis)
        self.memory_series.attachAxis(self.time_axis)
        self.memory_series.attachAxis(self.value_axis)
        
        self.chart_view = QChartView(self.performance_chart)
        right_layout.addWidget(self.chart_view)
        
        # 接口状态表格
        self.interface_table = QTableWidget()
        self.interface_table.setColumnCount(4)
        self.interface_table.setHorizontalHeaderLabels(["接口", "状态", "输入流量", "输出流量"])
        right_layout.addWidget(self.interface_table)
        
        # 使用分割器
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([300, 700])
        
        layout.addWidget(splitter)
        
        self.tabs.addTab(monitoring_tab, "性能监控")
        
    def create_configuration_tab(self):
        configuration_tab = QWidget()
        layout = QVBoxLayout(configuration_tab)
        
        # 配置操作区域
        config_controls = QHBoxLayout()
        
        self.backup_button = QPushButton("备份配置")
        self.backup_button.clicked.connect(self.backup_config)
        
        self.restore_button = QPushButton("恢复配置")
        self.restore_button.clicked.connect(self.restore_config)
        
        self.compare_button = QPushButton("比较配置")
        self.compare_button.clicked.connect(self.compare_configs)
        
        config_controls.addWidget(self.backup_button)
        config_controls.addWidget(self.restore_button)
        config_controls.addWidget(self.compare_button)
        config_controls.addStretch()
        
        layout.addLayout(config_controls)
        
        # 配置编辑区域
        config_edit_layout = QHBoxLayout()
        
        # 左侧备份列表
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        self.backup_list = QTreeWidget()
        self.backup_list.setHeaderLabels(["设备", "备份时间", "操作"])
        left_layout.addWidget(QLabel("配置备份:"))
        left_layout.addWidget(self.backup_list)
        
        # 右侧配置编辑器
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        self.config_editor = QTextEdit()
        self.config_editor.setPlaceholderText("设备配置将显示在这里...")
        right_layout.addWidget(QLabel("配置内容:"))
        right_layout.addWidget(self.config_editor)
        
        # 保存按钮
        self.save_config_button = QPushButton("保存配置")
        self.save_config_button.clicked.connect(self.save_config)
        right_layout.addWidget(self.save_config_button)
        
        config_edit_layout.addWidget(left_widget)
        config_edit_layout.addWidget(right_widget)
        config_edit_layout.setStretchFactor(right_widget, 2)
        
        layout.addLayout(config_edit_layout)
        
        self.tabs.addTab(configuration_tab, "配置管理")
        
    def create_troubleshooting_tab(self):
        troubleshooting_tab = QWidget()
        layout = QVBoxLayout(troubleshooting_tab)
        
        # 故障检测区域
        troubleshoot_controls = QHBoxLayout()
        
        self.diagnose_button = QPushButton("诊断设备")
        self.diagnose_button.clicked.connect(self.diagnose_device)
        
        self.ping_test_button = QPushButton("Ping测试")
        self.ping_test_button.clicked.connect(self.ping_test)
        
        self.port_scan_button = QPushButton("端口扫描")
        self.port_scan_button.clicked.connect(self.port_scan)
        
        troubleshoot_controls.addWidget(self.diagnose_button)
        troubleshoot_controls.addWidget(self.ping_test_button)
        troubleshoot_controls.addWidget(self.port_scan_button)
        troubleshoot_controls.addStretch()
        
        layout.addLayout(troubleshoot_controls)
        
        # 日志显示区域
        self.troubleshoot_log = QTextEdit()
        self.troubleshoot_log.setReadOnly(True)
        layout.addWidget(self.troubleshoot_log)
        
        self.tabs.addTab(troubleshooting_tab, "故障排查")
        
    def start_discovery(self):
        ip_range = self.ip_range_input.text()
        timeout = self.timeout_input.value()
        
        if not ip_range or '-' not in ip_range:
            QMessageBox.warning(self, "错误", "请输入有效的IP范围，格式如: 192.168.1.1-192.168.1.50")
            return
            
        self.discovery_thread = DeviceDiscoveryThread(ip_range, timeout)
        self.discovery_thread.progress_signal.connect(self.discovery_progress.setValue)
        self.discovery_thread.device_found_signal.connect(self.on_device_found)
        self.discovery_thread.finished_signal.connect(self.on_discovery_finished)
        
        self.discover_button.setEnabled(False)
        self.stop_discover_button.setEnabled(True)
        
        # 清空结果表
        self.discovery_results.setRowCount(0)
        
        self.discovery_thread.start()
        self.statusBar().showMessage("设备发现中...")
        
    def stop_discovery(self):
        if self.discovery_thread and self.discovery_thread.isRunning():
            self.discovery_thread.stop()
            self.discovery_thread.wait()
            
        self.discover_button.setEnabled(True)
        self.stop_discover_button.setEnabled(False)
        self.statusBar().showMessage("设备发现已停止")
        
    def on_device_found(self, device):
        # 添加到设备列表
        self.devices.append(device)
        
        # 更新发现结果表
        row = self.discovery_results.rowCount()
        self.discovery_results.insertRow(row)
        
        self.discovery_results.setItem(row, 0, QTableWidgetItem(device.ip))
        self.discovery_results.setItem(row, 1, QTableWidgetItem(device.hostname))
        self.discovery_results.setItem(row, 2, QTableWidgetItem(device.device_type))
        
        status_item = QTableWidgetItem(device.status)
        if device.status == "up":
            status_item.setBackground(QColor(0, 255, 0, 100))
        else:
            status_item.setBackground(QColor(255, 0, 0, 100))
        self.discovery_results.setItem(row, 3, status_item)
        
        # 添加操作按钮
        add_button = QPushButton("添加到监控")
        add_button.clicked.connect(lambda: self.add_to_monitoring(device))
        self.discovery_results.setCellWidget(row, 4, add_button)
        
        # 更新仪表盘
        self.update_dashboard()
        
    def on_discovery_finished(self, devices):
        self.discover_button.setEnabled(True)
        self.stop_discover_button.setEnabled(False)
        self.statusBar().showMessage(f"设备发现完成，找到 {len(devices)} 台设备")
        
    def add_to_monitoring(self, device):
        # 添加到监控设备树
        item = QTreeWidgetItem(self.monitor_device_tree)
        item.setText(0, f"{device.hostname} ({device.ip})")
        item.setText(1, device.status)
        item.setText(2, f"{device.cpu_usage}%")
        item.setText(3, f"{device.memory_usage}%")
        
        # 存储设备引用
        item.setData(0, Qt.UserRole, device)
        
        self.statusBar().showMessage(f"已添加 {device.ip} 到监控列表")
        
    def start_monitoring(self):
        if self.monitor_thread and self.monitor_thread.isRunning():
            return
            
        # 获取监控设备
        monitored_devices = []
        for i in range(self.monitor_device_tree.topLevelItemCount()):
            item = self.monitor_device_tree.topLevelItem(i)
            device = item.data(0, Qt.UserRole)
            if device:
                monitored_devices.append(device)
                
        if not monitored_devices:
            QMessageBox.information(self, "提示", "没有设备在监控列表中")
            return
            
        interval = self.monitor_interval.value()
        self.monitor_thread = DeviceMonitorThread(monitored_devices, interval)
        self.monitor_thread.update_signal.connect(self.on_device_updated)
        
        self.start_monitor_button.setEnabled(False)
        self.stop_monitor_button.setEnabled(True)
        
        self.monitor_thread.start()
        self.statusBar().showMessage("设备监控已启动")
        
    def stop_monitoring(self):
        if self.monitor_thread and self.monitor_thread.isRunning():
            self.monitor_thread.stop()
            self.monitor_thread.wait()
            
        self.start_monitor_button.setEnabled(True)
        self.stop_monitor_button.setEnabled(False)
        self.statusBar().showMessage("设备监控已停止")
        
    def on_device_updated(self, device):
        # 更新监控设备树
        for i in range(self.monitor_device_tree.topLevelItemCount()):
            item = self.monitor_device_tree.topLevelItem(i)
            item_device = item.data(0, Qt.UserRole)
            if item_device and item_device.ip == device.ip:
                item.setText(1, device.status)
                item.setText(2, f"{device.cpu_usage}%")
                item.setText(3, f"{device.memory_usage}%")
                
                # 更新状态颜色
                if device.status == "up":
                    item.setBackground(1, QColor(0, 255, 0, 100))
                else:
                    item.setBackground(1, QColor(255, 0, 0, 100))
                break
                
        # 如果当前选中的设备是更新的设备，更新图表和接口表
        if self.selected_device and self.selected_device.ip == device.ip:
            self.update_performance_chart(device)
            self.update_interface_table(device)
            
    def on_device_selected(self):
        selected_items = self.device_tree.selectedItems()
        if not selected_items:
            return
            
        item = selected_items[0]
        ip = item.text(0)
        
        # 查找对应的设备
        for device in self.devices:
            if device.ip == ip:
                self.selected_device = device
                break
                
    def on_monitor_device_selected(self):
        selected_items = self.monitor_device_tree.selectedItems()
        if not selected_items:
            return
            
        item = selected_items[0]
        device = item.data(0, Qt.UserRole)
        
        if device:
            self.selected_device = device
            self.update_performance_chart(device)
            self.update_interface_table(device)
            
    def update_performance_chart(self, device):
        # 清空现有数据
        self.cpu_series.clear()
        self.memory_series.clear()
        
        # 模拟性能数据（实际应用中应从设备获取历史数据）
        current_time = QDateTime.currentDateTime()
        
        for i in range(10):
            time_point = current_time.addSecs(-i * 10)
            cpu_value = max(0, min(100, device.cpu_usage + (i * 5 - 10)))
            memory_value = max(0, min(100, device.memory_usage + (i * 3 - 5)))
            
            self.cpu_series.append(time_point.toMSecsSinceEpoch(), cpu_value)
            self.memory_series.append(time_point.toMSecsSinceEpoch(), memory_value)
            
        # 调整时间轴范围
        self.time_axis.setRange(current_time.addSecs(-100), current_time.addSecs(10))
        
    def update_interface_table(self, device):
        self.interface_table.setRowCount(0)
        
        for intf_name, intf_data in device.interfaces.items():
            row = self.interface_table.rowCount()
            self.interface_table.insertRow(row)
            
            self.interface_table.setItem(row, 0, QTableWidgetItem(intf_name))
            
            status_item = QTableWidgetItem(intf_data["status"])
            if intf_data["status"] == "up":
                status_item.setBackground(QColor(0, 255, 0, 100))
            else:
                status_item.setBackground(QColor(255, 0, 0, 100))
            self.interface_table.setItem(row, 1, status_item)
            
            self.interface_table.setItem(row, 2, QTableWidgetItem(str(intf_data["in_bytes"])))
            self.interface_table.setItem(row, 3, QTableWidgetItem(str(intf_data["out_bytes"])))
            
    def backup_config(self):
        if not self.selected_device:
            QMessageBox.warning(self, "错误", "请先选择一个设备")
            return
            
        # 模拟配置备份
        config = f"# 设备 {self.selected_device.ip} 的配置\n# 备份时间: {datetime.now()}\n\ninterface eth0\n  ip address 192.168.1.1 255.255.255.0\n!"
        
        backup_key = self.config_manager.backup_config(self.selected_device, config)
        
        # 更新备份列表
        self.update_backup_list()
        
        QMessageBox.information(self, "成功", f"配置已备份: {backup_key}")
        
    def restore_config(self):
        selected_items = self.backup_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "错误", "请先选择一个备份")
            return
            
        item = selected_items[0]
        backup_key = item.data(0, Qt.UserRole)
        
        config = self.config_manager.restore_config(backup_key)
        if config:
            self.config_editor.setPlainText(config)
            QMessageBox.information(self, "成功", "配置已加载到编辑器")
        else:
            QMessageBox.warning(self, "错误", "无法恢复配置")
            
    def compare_configs(self):
        QMessageBox.information(self, "提示", "配置比较功能待实现")
        
    def save_config(self):
        if not self.selected_device:
            QMessageBox.warning(self, "错误", "请先选择一个设备")
            return
            
        config = self.config_editor.toPlainText()
        if not config:
            QMessageBox.warning(self, "错误", "配置内容为空")
            return
            
        # 模拟保存配置
        backup_key = self.config_manager.backup_config(self.selected_device, config)
        self.update_backup_list()
        
        QMessageBox.information(self, "成功", f"配置已保存并备份: {backup_key}")
        
    def update_backup_list(self):
        self.backup_list.clear()
        
        if not self.selected_device:
            return
            
        backups = self.config_manager.get_config_backups(self.selected_device.ip)
        
        for key, backup in backups.items():
            item = QTreeWidgetItem(self.backup_list)
            item.setText(0, backup["device"])
            item.setText(1, backup["timestamp"])
            item.setText(2, "查看/恢复")
            item.setData(0, Qt.UserRole, key)
            
    def diagnose_device(self):
        if not self.selected_device:
            QMessageBox.warning(self, "错误", "请先选择一个设备")
            return
            
        self.troubleshoot_log.append(f"[{datetime.now()}] 开始诊断设备 {self.selected_device.ip}")
        
        # 模拟诊断过程
        if self.selected_device.status == "up":
            self.troubleshoot_log.append("✓ 设备在线")
            self.troubleshoot_log.append(f"✓ CPU使用率: {self.selected_device.cpu_usage}%")
            self.troubleshoot_log.append(f"✓ 内存使用率: {self.selected_device.memory_usage}%")
            
            # 检查接口状态
            down_interfaces = [name for name, data in self.selected_device.interfaces.items() if data["status"] == "down"]
            if down_interfaces:
                self.troubleshoot_log.append(f"⚠ 以下接口异常: {', '.join(down_interfaces)}")
            else:
                self.troubleshoot_log.append("✓ 所有接口正常")
        else:
            self.troubleshoot_log.append("✗ 设备离线")
            
        self.troubleshoot_log.append("诊断完成\n")
        
    def ping_test(self):
        if not self.selected_device:
            QMessageBox.warning(self, "错误", "请先选择一个设备")
            return
            
        self.troubleshoot_log.append(f"[{datetime.now()}] Ping测试 {self.selected_device.ip}")
        
        # 模拟ping测试
        if self.selected_device.status == "up":
            self.troubleshoot_log.append("✓ Ping成功 - 设备响应正常")
        else:
            self.troubleshoot_log.append("✗ Ping失败 - 设备无响应")
            
    def port_scan(self):
        if not self.selected_device:
            QMessageBox.warning(self, "错误", "请先选择一个设备")
            return
            
        self.troubleshoot_log.append(f"[{datetime.now()}] 端口扫描 {self.selected_device.ip}")
        
        # 模拟端口扫描
        common_ports = [22, 23, 80, 443, 161, 162]
        
        for port in common_ports:
            # 模拟端口状态
            is_open = (int(self.selected_device.ip.split('.')[-1]) + port) % 3 != 0
            status = "开放" if is_open else "关闭"
            self.troubleshoot_log.append(f"{'✓' if is_open else '✗'} 端口 {port}: {status}")
            
    def update_dashboard(self):
        total = len(self.devices)
        up_count = sum(1 for d in self.devices if d.status == "up")
        down_count = total - up_count
        
        self.total_devices_label.setText(f"总设备: {total}")
        self.up_devices_label.setText(f"在线设备: {up_count}")
        self.down_devices_label.setText(f"离线设备: {down_count}")
        
        # 更新设备树
        self.device_tree.clear()
        
        for device in self.devices:
            item = QTreeWidgetItem(self.device_tree)
            item.setText(0, device.ip)
            item.setText(1, device.hostname)
            item.setText(2, device.device_type)
            item.setText(3, device.status)
            item.setText(4, device.last_seen.strftime("%Y-%m-%d %H:%M:%S"))
            
            # 设置状态颜色
            if device.status == "up":
                item.setBackground(3, QColor(0, 255, 0, 100))
            else:
                item.setBackground(3, QColor(255, 0, 0, 100))
                
    def export_device_list(self):
        filename, _ = QFileDialog.getSaveFileName(self, "导出设备列表", "", "JSON文件 (*.json)")
        if filename:
            device_data = []
            for device in self.devices:
                device_data.append({
                    "ip": device.ip,
                    "hostname": device.hostname,
                    "device_type": device.device_type,
                    "status": device.status
                })
                
            with open(filename, 'w') as f:
                json.dump(device_data, f, indent=2)
                
            QMessageBox.information(self, "成功", f"设备列表已导出到 {filename}")
            
    def import_device_list(self):
        filename, _ = QFileDialog.getOpenFileName(self, "导入设备列表", "", "JSON文件 (*.json)")
        if filename:
            try:
                with open(filename, 'r') as f:
                    device_data = json.load(f)
                    
                self.devices.clear()
                for data in device_data:
                    device = NetworkDevice(
                        data["ip"], 
                        data["hostname"], 
                        data["device_type"], 
                        data["status"]
                    )
                    self.devices.append(device)
                    
                self.update_dashboard()
                QMessageBox.information(self, "成功", f"已从 {filename} 导入设备列表")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导入失败: {str(e)}")
                
    def show_ping_tool(self):
        QMessageBox.information(self, "Ping工具", "Ping工具对话框待实现")
        
    def show_traceroute_tool(self):
        QMessageBox.information(self, "Traceroute工具", "Traceroute工具对话框待实现")
        
    def show_preferences(self):
        QMessageBox.information(self, "首选项", "首选项对话框待实现")
        
    def load_settings(self):
        settings = QSettings("NetworkManager", "AdvancedNMS")
        geometry = settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
            
    def closeEvent(self, event):
        # 停止所有线程
        if self.discovery_thread and self.discovery_thread.isRunning():
            self.discovery_thread.stop()
            self.discovery_thread.wait()
            
        if self.monitor_thread and self.monitor_thread.isRunning():
            self.monitor_thread.stop()
            self.monitor_thread.wait()
            
        # 保存设置
        settings = QSettings("NetworkManager", "AdvancedNMS")
        settings.setValue("geometry", self.saveGeometry())
        
        event.accept()

# 应用程序入口
if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 设置应用程序样式
    app.setStyle("Fusion")
    
    # 创建并显示主窗口
    window = NetworkManagerWindow()
    window.show()
    
    sys.exit(app.exec_())