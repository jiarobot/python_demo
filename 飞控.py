import sys
import time
import json
import logging
import threading
from datetime import datetime
from collections import deque

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTabWidget, QGroupBox, QLabel, 
                             QPushButton, QComboBox, QSpinBox, QDoubleSpinBox,
                             QTextEdit, QTableWidget, QTableWidgetItem, 
                             QHeaderView, QProgressBar, QSplitter, QCheckBox,
                             QMessageBox, QFileDialog, QLineEdit)
from PyQt5.QtCore import QTimer, Qt, pyqtSignal, QThread
from PyQt5.QtGui import QFont, QColor

from pymavlink import mavutil
import serial.tools.list_ports

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class MavlinkThread(QThread):
    """MAVLink通信线程"""
    
    # 定义信号
    message_received = pyqtSignal(object)
    connected = pyqtSignal()
    disconnected = pyqtSignal()
    error_occurred = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.master = None
        self.running = False
        self.connection_type = "serial"
        self.port = "COM3"
        self.baud = 57600
        self.host = "127.0.0.1"
        self.port_tcp = 14550
        
    def connect_serial(self, port, baud):
        """连接串口设备"""
        try:
            self.connection_type = "serial"
            self.port = port
            self.baud = baud
            self.master = mavutil.mavlink_connection(port, baud=baud)
            self.running = True
            self.connected.emit()
            return True
        except Exception as e:
            self.error_occurred.emit(f"连接失败: {str(e)}")
            return False
            
    def connect_tcp(self, host, port):
        """连接TCP设备"""
        try:
            self.connection_type = "tcp"
            self.host = host
            self.port_tcp = port
            self.master = mavutil.mavlink_connection(f"tcp:{host}:{port}")
            self.running = True
            self.connected.emit()
            return True
        except Exception as e:
            self.error_occurred.emit(f"连接失败: {str(e)}")
            return False
            
    def disconnect(self):
        """断开连接"""
        self.running = False
        if self.master:
            self.master.close()
        self.disconnected.emit()
        
    def run(self):
        """主循环"""
        while self.running:
            try:
                if self.master:
                    msg = self.master.recv_match(blocking=False, timeout=0.1)
                    if msg:
                        self.message_received.emit(msg)
                else:
                    time.sleep(0.1)
            except Exception as e:
                self.error_occurred.emit(f"接收错误: {str(e)}")
                time.sleep(0.1)
                
    def send_command(self, command, params=[], confirmation=0):
        """发送命令"""
        if self.master and self.running:
            try:
                self.master.mav.command_long_send(
                    self.master.target_system,
                    self.master.target_component,
                    command,
                    confirmation,
                    *params
                )
                return True
            except Exception as e:
                self.error_occurred.emit(f"发送命令失败: {str(e)}")
                return False
        return False
        
    def request_data_stream(self, stream_id, rate):
        """请求数据流"""
        if self.master and self.running:
            try:
                self.master.mav.request_data_stream_send(
                    self.master.target_system,
                    self.master.target_component,
                    stream_id,
                    rate,
                    1  # 开始流
                )
                return True
            except Exception as e:
                self.error_occurred.emit(f"请求数据流失败: {str(e)}")
                return False
        return False

class MavlinkGroundStation(QMainWindow):
    """MAVLink地面站主窗口"""
    
    def __init__(self):
        super().__init__()
        self.mavlink_thread = MavlinkThread()
        self.message_counters = {}
        self.parameters = {}
        self.waypoints = []
        self.setup_ui()
        self.setup_connections()
        self.discover_serial_ports()
        
    def setup_ui(self):
        """设置用户界面"""
        self.setWindowTitle("MAVLink地面站")
        self.setGeometry(100, 100, 1200, 800)
        
        # 中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QVBoxLayout(central_widget)
        
        # 连接状态栏
        self.setup_status_bar(main_layout)
        
        # 连接控制
        self.setup_connection_controls(main_layout)
        
        # 选项卡
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        # 添加各个选项卡
        self.setup_dashboard_tab()
        self.setup_mission_tab()
        self.setup_parameters_tab()
        self.setup_telemetry_tab()
        self.setup_command_tab()
        self.setup_log_tab()
        
    def setup_status_bar(self, layout):
        """设置状态栏"""
        status_group = QGroupBox("连接状态")
        status_layout = QHBoxLayout()
        
        self.connection_status = QLabel("未连接")
        self.connection_status.setStyleSheet("color: red; font-weight: bold;")
        
        self.heartbeat_status = QLabel("无心跳")
        self.heartbeat_status.setStyleSheet("color: red;")
        
        self.message_count_label = QLabel("消息: 0")
        
        self.battery_status = QLabel("电池: N/A")
        
        self.gps_status = QLabel("GPS: 无信号")
        self.gps_status.setStyleSheet("color: red;")
        
        status_layout.addWidget(self.connection_status)
        status_layout.addWidget(self.heartbeat_status)
        status_layout.addWidget(self.message_count_label)
        status_layout.addWidget(self.battery_status)
        status_layout.addWidget(self.gps_status)
        status_layout.addStretch()
        
        status_group.setLayout(status_layout)
        layout.addWidget(status_group)
        
    def setup_connection_controls(self, layout):
        """设置连接控制"""
        connection_group = QGroupBox("连接设置")
        connection_layout = QHBoxLayout()
        
        # 连接类型
        self.connection_type = QComboBox()
        self.connection_type.addItems(["串口", "TCP"])
        self.connection_type.currentTextChanged.connect(self.on_connection_type_changed)
        
        # 串口设置
        self.serial_port = QComboBox()
        self.serial_baud = QComboBox()
        self.serial_baud.addItems(["9600", "19200", "38400", "57600", "115200", "230400"])
        self.serial_baud.setCurrentText("57600")
        
        # TCP设置
        self.tcp_host = QLineEdit("127.0.0.1")
        self.tcp_port = QSpinBox()
        self.tcp_port.setRange(1, 65535)
        self.tcp_port.setValue(14550)
        
        # 连接按钮
        self.connect_btn = QPushButton("连接")
        self.connect_btn.clicked.connect(self.toggle_connection)
        
        # 刷新串口按钮
        self.refresh_ports_btn = QPushButton("刷新串口")
        self.refresh_ports_btn.clicked.connect(self.discover_serial_ports)
        
        connection_layout.addWidget(QLabel("连接类型:"))
        connection_layout.addWidget(self.connection_type)
        connection_layout.addWidget(QLabel("串口:"))
        connection_layout.addWidget(self.serial_port)
        connection_layout.addWidget(QLabel("波特率:"))
        connection_layout.addWidget(self.serial_baud)
        connection_layout.addWidget(QLabel("主机:"))
        connection_layout.addWidget(self.tcp_host)
        connection_layout.addWidget(QLabel("端口:"))
        connection_layout.addWidget(self.tcp_port)
        connection_layout.addWidget(self.connect_btn)
        connection_layout.addWidget(self.refresh_ports_btn)
        
        connection_group.setLayout(connection_layout)
        layout.addWidget(connection_group)
        
        # 初始隐藏TCP控件
        self.tcp_host.setVisible(False)
        self.tcp_port.setVisible(False)
        
    def setup_dashboard_tab(self):
        """设置仪表盘选项卡"""
        dashboard_tab = QWidget()
        layout = QHBoxLayout(dashboard_tab)
        
        # 左侧状态信息
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        # 姿态显示
        attitude_group = QGroupBox("姿态")
        attitude_layout = QVBoxLayout()
        
        self.roll_label = QLabel("横滚: N/A")
        self.pitch_label = QLabel("俯仰: N/A")
        self.yaw_label = QLabel("偏航: N/A")
        
        attitude_layout.addWidget(self.roll_label)
        attitude_layout.addWidget(self.pitch_label)
        attitude_layout.addWidget(self.yaw_label)
        attitude_group.setLayout(attitude_layout)
        left_layout.addWidget(attitude_group)
        
        # GPS信息
        gps_group = QGroupBox("GPS")
        gps_layout = QVBoxLayout()
        
        self.gps_lat_label = QLabel("纬度: N/A")
        self.gps_lon_label = QLabel("经度: N/A")
        self.gps_alt_label = QLabel("海拔: N/A")
        self.gps_satellites_label = QLabel("卫星: N/A")
        
        gps_layout.addWidget(self.gps_lat_label)
        gps_layout.addWidget(self.gps_lon_label)
        gps_layout.addWidget(self.gps_alt_label)
        gps_layout.addWidget(self.gps_satellites_label)
        gps_group.setLayout(gps_layout)
        left_layout.addWidget(gps_group)
        
        # 电池信息
        battery_group = QGroupBox("电池")
        battery_layout = QVBoxLayout()
        
        self.battery_voltage_label = QLabel("电压: N/A")
        self.battery_current_label = QLabel("电流: N/A")
        self.battery_remaining_label = QLabel("剩余: N/A")
        
        battery_layout.addWidget(self.battery_voltage_label)
        battery_layout.addWidget(self.battery_current_label)
        battery_layout.addWidget(self.battery_remaining_label)
        battery_group.setLayout(battery_layout)
        left_layout.addWidget(battery_group)
        
        # 系统状态
        system_group = QGroupBox("系统状态")
        system_layout = QVBoxLayout()
        
        self.system_mode_label = QLabel("模式: N/A")
        self.system_status_label = QLabel("状态: N/A")
        self.system_arm_label = QLabel("解锁: N/A")
        
        system_layout.addWidget(self.system_mode_label)
        system_layout.addWidget(self.system_status_label)
        system_layout.addWidget(self.system_arm_label)
        system_group.setLayout(system_layout)
        left_layout.addWidget(system_group)
        
        left_layout.addStretch()
        
        # 右侧消息统计
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        # 消息统计
        message_group = QGroupBox("消息统计")
        message_layout = QVBoxLayout()
        
        self.message_table = QTableWidget()
        self.message_table.setColumnCount(2)
        self.message_table.setHorizontalHeaderLabels(["消息类型", "计数"])
        self.message_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        message_layout.addWidget(self.message_table)
        message_group.setLayout(message_layout)
        right_layout.addWidget(message_group)
        
        # 数据流控制
        stream_group = QGroupBox("数据流控制")
        stream_layout = QVBoxLayout()
        
        self.stream_all_check = QCheckBox("所有数据流")
        self.stream_all_check.setChecked(True)
        self.stream_all_check.stateChanged.connect(self.on_stream_all_changed)
        
        stream_rate_layout = QHBoxLayout()
        stream_rate_layout.addWidget(QLabel("流速率:"))
        self.stream_rate = QSpinBox()
        self.stream_rate.setRange(1, 50)
        self.stream_rate.setValue(4)
        stream_rate_layout.addWidget(self.stream_rate)
        stream_rate_layout.addStretch()
        
        self.apply_stream_btn = QPushButton("应用设置")
        self.apply_stream_btn.clicked.connect(self.apply_stream_settings)
        
        stream_layout.addWidget(self.stream_all_check)
        stream_layout.addLayout(stream_rate_layout)
        stream_layout.addWidget(self.apply_stream_btn)
        stream_group.setLayout(stream_layout)
        right_layout.addWidget(stream_group)
        
        right_layout.addStretch()
        
        # 分割左右布局
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([400, 400])
        
        layout.addWidget(splitter)
        
        self.tab_widget.addTab(dashboard_tab, "仪表盘")
        
    def setup_mission_tab(self):
        """设置任务选项卡"""
        mission_tab = QWidget()
        layout = QVBoxLayout(mission_tab)
        
        # 任务控制按钮
        mission_controls = QHBoxLayout()
        
        self.load_mission_btn = QPushButton("加载任务")
        self.load_mission_btn.clicked.connect(self.load_mission)
        
        self.save_mission_btn = QPushButton("保存任务")
        self.save_mission_btn.clicked.connect(self.save_mission)
        
        self.upload_mission_btn = QPushButton("上传任务")
        self.upload_mission_btn.clicked.connect(self.upload_mission)
        
        self.download_mission_btn = QPushButton("下载任务")
        self.download_mission_btn.clicked.connect(self.download_mission)
        
        mission_controls.addWidget(self.load_mission_btn)
        mission_controls.addWidget(self.save_mission_btn)
        mission_controls.addWidget(self.upload_mission_btn)
        mission_controls.addWidget(self.download_mission_btn)
        mission_controls.addStretch()
        
        layout.addLayout(mission_controls)
        
        # 航点表格
        self.waypoint_table = QTableWidget()
        self.waypoint_table.setColumnCount(8)
        self.waypoint_table.setHorizontalHeaderLabels([
            "序号", "经度", "纬度", "海拔", "命令", "参数1", "参数2", "参数3"
        ])
        self.waypoint_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        layout.addWidget(self.waypoint_table)
        
        self.tab_widget.addTab(mission_tab, "任务规划")
        
    def setup_parameters_tab(self):
        """设置参数选项卡"""
        parameters_tab = QWidget()
        layout = QVBoxLayout(parameters_tab)
        
        # 参数控制按钮
        param_controls = QHBoxLayout()
        
        self.refresh_params_btn = QPushButton("刷新参数")
        self.refresh_params_btn.clicked.connect(self.refresh_parameters)
        
        self.save_params_btn = QPushButton("保存参数")
        self.save_params_btn.clicked.connect(self.save_parameters)
        
        self.load_params_btn = QPushButton("加载参数")
        self.load_params_btn.clicked.connect(self.load_parameters)
        
        param_controls.addWidget(self.refresh_params_btn)
        param_controls.addWidget(self.save_params_btn)
        param_controls.addWidget(self.load_params_btn)
        param_controls.addStretch()
        
        layout.addLayout(param_controls)
        
        # 参数表格
        self.parameter_table = QTableWidget()
        self.parameter_table.setColumnCount(3)
        self.parameter_table.setHorizontalHeaderLabels(["参数名", "值", "类型"])
        self.parameter_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.parameter_table.cellChanged.connect(self.on_parameter_changed)
        
        layout.addWidget(self.parameter_table)
        
        self.tab_widget.addTab(parameters_tab, "参数配置")
        
    def setup_telemetry_tab(self):
        """设置遥测数据选项卡"""
        telemetry_tab = QWidget()
        layout = QVBoxLayout(telemetry_tab)
        
        # 遥测数据显示
        self.telemetry_text = QTextEdit()
        self.telemetry_text.setReadOnly(True)
        font = QFont("Courier New", 9)
        self.telemetry_text.setFont(font)
        
        layout.addWidget(self.telemetry_text)
        
        self.tab_widget.addTab(telemetry_tab, "遥测数据")
        
    def setup_command_tab(self):
        """设置命令选项卡"""
        command_tab = QWidget()
        layout = QVBoxLayout(command_tab)
        
        # 飞行控制
        flight_control_group = QGroupBox("飞行控制")
        flight_layout = QHBoxLayout()
        
        self.arm_btn = QPushButton("解锁")
        self.arm_btn.clicked.connect(lambda: self.send_flight_command(1))
        
        self.disarm_btn = QPushButton("锁定")
        self.disarm_btn.clicked.connect(lambda: self.send_flight_command(0))
        
        self.takeoff_btn = QPushButton("起飞")
        self.takeoff_btn.clicked.connect(self.send_takeoff_command)
        
        self.land_btn = QPushButton("降落")
        self.land_btn.clicked.connect(self.send_land_command)
        
        self.rtl_btn = QPushButton("返航")
        self.rtl_btn.clicked.connect(self.send_rtl_command)
        
        flight_layout.addWidget(self.arm_btn)
        flight_layout.addWidget(self.disarm_btn)
        flight_layout.addWidget(self.takeoff_btn)
        flight_layout.addWidget(self.land_btn)
        flight_layout.addWidget(self.rtl_btn)
        flight_layout.addStretch()
        
        flight_control_group.setLayout(flight_layout)
        layout.addWidget(flight_control_group)
        
        # 模式选择
        mode_group = QGroupBox("飞行模式")
        mode_layout = QHBoxLayout()
        
        self.mode_combo = QComboBox()
        self.mode_combo.addItems([
            "稳定", "特技", "定高", "悬停", "返航", "任务", "降落", "引导"
        ])
        
        self.set_mode_btn = QPushButton("设置模式")
        self.set_mode_btn.clicked.connect(self.set_flight_mode)
        
        mode_layout.addWidget(QLabel("模式:"))
        mode_layout.addWidget(self.mode_combo)
        mode_layout.addWidget(self.set_mode_btn)
        mode_layout.addStretch()
        
        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)
        
        # 自定义命令
        custom_group = QGroupBox("自定义命令")
        custom_layout = QVBoxLayout()
        
        command_input_layout = QHBoxLayout()
        command_input_layout.addWidget(QLabel("命令:"))
        self.custom_command = QSpinBox()
        self.custom_command.setRange(0, 1000)
        command_input_layout.addWidget(self.custom_command)
        
        command_input_layout.addWidget(QLabel("参数1:"))
        self.param1 = QDoubleSpinBox()
        self.param1.setRange(-1000, 1000)
        command_input_layout.addWidget(self.param1)
        
        command_input_layout.addWidget(QLabel("参数2:"))
        self.param2 = QDoubleSpinBox()
        self.param2.setRange(-1000, 1000)
        command_input_layout.addWidget(self.param2)
        
        command_input_layout.addWidget(QLabel("参数3:"))
        self.param3 = QDoubleSpinBox()
        self.param3.setRange(-1000, 1000)
        command_input_layout.addWidget(self.param3)
        
        custom_layout.addLayout(command_input_layout)
        
        self.send_custom_btn = QPushButton("发送自定义命令")
        self.send_custom_btn.clicked.connect(self.send_custom_command)
        custom_layout.addWidget(self.send_custom_btn)
        
        custom_group.setLayout(custom_layout)
        layout.addWidget(custom_group)
        
        layout.addStretch()
        
        self.tab_widget.addTab(command_tab, "命令控制")
        
    def setup_log_tab(self):
        """设置日志选项卡"""
        log_tab = QWidget()
        layout = QVBoxLayout(log_tab)
        
        # 日志控制
        log_controls = QHBoxLayout()
        
        self.clear_log_btn = QPushButton("清空日志")
        self.clear_log_btn.clicked.connect(self.clear_log)
        
        self.save_log_btn = QPushButton("保存日志")
        self.save_log_btn.clicked.connect(self.save_log)
        
        log_controls.addWidget(self.clear_log_btn)
        log_controls.addWidget(self.save_log_btn)
        log_controls.addStretch()
        
        layout.addLayout(log_controls)
        
        # 日志显示
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        font = QFont("Courier New", 9)
        self.log_text.setFont(font)
        
        layout.addWidget(self.log_text)
        
        self.tab_widget.addTab(log_tab, "系统日志")
        
    def setup_connections(self):
        """设置信号连接"""
        self.mavlink_thread.message_received.connect(self.on_message_received)
        self.mavlink_thread.connected.connect(self.on_connected)
        self.mavlink_thread.disconnected.connect(self.on_disconnected)
        self.mavlink_thread.error_occurred.connect(self.on_error)
        
        # 状态更新定时器
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_status)
        self.status_timer.start(1000)  # 1秒更新一次
        
    def discover_serial_ports(self):
        """发现可用的串口"""
        self.serial_port.clear()
        ports = serial.tools.list_ports.comports()
        for port in ports:
            self.serial_port.addItem(port.device)
            
    def on_connection_type_changed(self, text):
        """连接类型改变"""
        if text == "串口":
            self.serial_port.setVisible(True)
            self.serial_baud.setVisible(True)
            self.tcp_host.setVisible(False)
            self.tcp_port.setVisible(False)
        else:
            self.serial_port.setVisible(False)
            self.serial_baud.setVisible(False)
            self.tcp_host.setVisible(True)
            self.tcp_port.setVisible(True)
            
    def toggle_connection(self):
        """切换连接状态"""
        if self.mavlink_thread.running:
            self.mavlink_thread.disconnect()
        else:
            if self.connection_type.currentText() == "串口":
                port = self.serial_port.currentText()
                baud = int(self.serial_baud.currentText())
                if port:
                    self.mavlink_thread.connect_serial(port, baud)
                else:
                    QMessageBox.warning(self, "警告", "请选择串口")
            else:
                host = self.tcp_host.text()
                port = self.tcp_port.value()
                if host:
                    self.mavlink_thread.connect_tcp(host, port)
                else:
                    QMessageBox.warning(self, "警告", "请输入主机地址")
                    
    def on_connected(self):
        """连接成功"""
        self.connection_status.setText("已连接")
        self.connection_status.setStyleSheet("color: green; font-weight: bold;")
        self.connect_btn.setText("断开连接")
        self.log_message("系统", "连接成功")
        
        # 启动MAVLink线程
        self.mavlink_thread.start()
        
        # 请求数据流
        self.apply_stream_settings()
        
    def on_disconnected(self):
        """连接断开"""
        self.connection_status.setText("未连接")
        self.connection_status.setStyleSheet("color: red; font-weight: bold;")
        self.connect_btn.setText("连接")
        self.heartbeat_status.setText("无心跳")
        self.heartbeat_status.setStyleSheet("color: red;")
        self.log_message("系统", "连接断开")
        
    def on_error(self, error_msg):
        """错误处理"""
        self.log_message("错误", error_msg)
        QMessageBox.critical(self, "错误", error_msg)
        
    def on_message_received(self, msg):
        """处理接收到的MAVLink消息"""
        msg_type = msg.get_type()
        
        # 更新消息计数
        if msg_type in self.message_counters:
            self.message_counters[msg_type] += 1
        else:
            self.message_counters[msg_type] = 1
            
        # 处理特定消息类型
        if msg_type == 'HEARTBEAT':
            self.process_heartbeat(msg)
        elif msg_type == 'ATTITUDE':
            self.process_attitude(msg)
        elif msg_type == 'GPS_RAW_INT':
            self.process_gps(msg)
        elif msg_type == 'SYS_STATUS':
            self.process_sys_status(msg)
        elif msg_type == 'VFR_HUD':
            self.process_vfr_hud(msg)
        elif msg_type == 'PARAM_VALUE':
            self.process_param_value(msg)
            
        # 更新遥测显示
        self.update_telemetry_display(msg)
        
    def process_heartbeat(self, msg):
        """处理心跳消息"""
        self.heartbeat_status.setText("心跳正常")
        self.heartbeat_status.setStyleSheet("color: green;")
        
        # 更新系统状态
        mode_mapping = {
            0: "自稳", 1: "特技", 2: "定高", 3: "悬停", 4: "返航", 
            5: "任务", 6: "降落", 7: "引导"
        }
        
        status_mapping = {
            0: "未初始化", 1: "系统启动", 2: "待机", 3: "活跃", 4: "关键",
            5: "紧急", 6: "关机", 7: "终止"
        }
        
        mode = mode_mapping.get(msg.custom_mode, "未知")
        status = status_mapping.get(msg.system_status, "未知")
        armed = "是" if msg.base_mode & 0x80 else "否"
        
        self.system_mode_label.setText(f"模式: {mode}")
        self.system_status_label.setText(f"状态: {status}")
        self.system_arm_label.setText(f"解锁: {armed}")
        
    def process_attitude(self, msg):
        """处理姿态消息"""
        roll_deg = msg.roll * 180 / 3.14159
        pitch_deg = msg.pitch * 180 / 3.14159
        yaw_deg = msg.yaw * 180 / 3.14159
        
        self.roll_label.setText(f"横滚: {roll_deg:.2f}°")
        self.pitch_label.setText(f"俯仰: {pitch_deg:.2f}°")
        self.yaw_label.setText(f"偏航: {yaw_deg:.2f}°")
        
    def process_gps(self, msg):
        """处理GPS消息"""
        if msg.fix_type >= 2:  # 2D或3D定位
            self.gps_status.setText(f"GPS: {msg.fix_type}D定位")
            self.gps_status.setStyleSheet("color: green;")
            
            lat = msg.lat / 1e7
            lon = msg.lon / 1e7
            alt = msg.alt / 1e3
            
            self.gps_lat_label.setText(f"纬度: {lat:.6f}°")
            self.gps_lon_label.setText(f"经度: {lon:.6f}°")
            self.gps_alt_label.setText(f"海拔: {alt:.2f}m")
            self.gps_satellites_label.setText(f"卫星: {msg.satellites_visible}")
        else:
            self.gps_status.setText("GPS: 无信号")
            self.gps_status.setStyleSheet("color: red;")
            
    def process_sys_status(self, msg):
        """处理系统状态消息"""
        voltage = msg.voltage_battery / 1000.0
        current = msg.current_battery / 100.0
        remaining = msg.battery_remaining
        
        self.battery_voltage_label.setText(f"电压: {voltage:.1f}V")
        self.battery_current_label.setText(f"电流: {current:.1f}A")
        self.battery_remaining_label.setText(f"剩余: {remaining}%")
        
        self.battery_status.setText(f"电池: {voltage:.1f}V ({remaining}%)")
        
    def process_vfr_hud(self, msg):
        """处理VFR_HUD消息"""
        # 可以在这里处理空速、地速等信息
        pass
        
    def process_param_value(self, msg):
        """处理参数值消息"""
        param_id = msg.param_id.decode('utf-8').rstrip('\x00')
        self.parameters[param_id] = msg.param_value
        
        # 更新参数表格
        self.update_parameter_table()
        
    def update_telemetry_display(self, msg):
        """更新遥测数据显示"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        telemetry_text = f"[{timestamp}] {msg.get_type()}: {msg}"
        
        # 限制显示行数
        current_text = self.telemetry_text.toPlainText()
        lines = current_text.split('\n')
        if len(lines) > 100:
            lines = lines[-100:]
            
        lines.append(telemetry_text)
        self.telemetry_text.setText('\n'.join(lines))
        
        # 自动滚动到底部
        self.telemetry_text.verticalScrollBar().setValue(
            self.telemetry_text.verticalScrollBar().maximum()
        )
        
    def update_status(self):
        """更新状态显示"""
        total_messages = sum(self.message_counters.values())
        self.message_count_label.setText(f"消息: {total_messages}")
        
        # 更新消息统计表格
        self.update_message_table()
        
    def update_message_table(self):
        """更新消息统计表格"""
        self.message_table.setRowCount(len(self.message_counters))
        
        for i, (msg_type, count) in enumerate(self.message_counters.items()):
            self.message_table.setItem(i, 0, QTableWidgetItem(msg_type))
            self.message_table.setItem(i, 1, QTableWidgetItem(str(count)))
            
    def update_parameter_table(self):
        """更新参数表格"""
        self.parameter_table.blockSignals(True)  # 防止触发cellChanged信号
        
        self.parameter_table.setRowCount(len(self.parameters))
        
        for i, (param_id, value) in enumerate(self.parameters.items()):
            self.parameter_table.setItem(i, 0, QTableWidgetItem(param_id))
            self.parameter_table.setItem(i, 1, QTableWidgetItem(str(value)))
            self.parameter_table.setItem(i, 2, QTableWidgetItem("浮点" if isinstance(value, float) else "整数"))
            
        self.parameter_table.blockSignals(False)
        
    def on_stream_all_changed(self, state):
        """数据流选择改变"""
        if state == Qt.Checked:
            self.apply_stream_settings()
            
    def apply_stream_settings(self):
        """应用数据流设置"""
        if self.mavlink_thread.running:
            rate = self.stream_rate.value()
            
            if self.stream_all_check.isChecked():
                # 请求所有数据流
                self.mavlink_thread.request_data_stream(
                    mavutil.mavlink.MAV_DATA_STREAM_ALL, rate)
            else:
                # 请求特定数据流
                streams = [
                    mavutil.mavlink.MAV_DATA_STREAM_RAW_SENSORS,
                    mavutil.mavlink.MAV_DATA_STREAM_EXTENDED_STATUS,
                    mavutil.mavlink.MAV_DATA_STREAM_RC_CHANNELS,
                    mavutil.mavlink.MAV_DATA_STREAM_POSITION,
                    mavutil.mavlink.MAV_DATA_STREAM_EXTRA1,
                    mavutil.mavlink.MAV_DATA_STREAM_EXTRA2,
                    mavutil.mavlink.MAV_DATA_STREAM_EXTRA3
                ]
                
                for stream in streams:
                    self.mavlink_thread.request_data_stream(stream, rate)
                    
            self.log_message("系统", f"数据流速率设置为 {rate}Hz")
            
    def send_flight_command(self, arm):
        """发送解锁/锁定命令"""
        # MAV_CMD_COMPONENT_ARM_DISARM
        command = 400
        param1 = 1.0 if arm else 0.0
        
        if self.mavlink_thread.send_command(command, [param1, 0, 0, 0, 0, 0, 0]):
            action = "解锁" if arm else "锁定"
            self.log_message("命令", f"发送{action}命令")
        else:
            self.log_message("错误", f"发送{action}命令失败")
            
    def send_takeoff_command(self):
        """发送起飞命令"""
        # MAV_CMD_NAV_TAKEOFF
        command = 22
        alt = 10  # 起飞高度10米
        
        if self.mavlink_thread.send_command(command, [0, 0, 0, 0, 0, 0, alt]):
            self.log_message("命令", f"发送起飞命令，高度{alt}米")
        else:
            self.log_message("错误", "发送起飞命令失败")
            
    def send_land_command(self):
        """发送降落命令"""
        # MAV_CMD_NAV_LAND
        command = 21
        
        if self.mavlink_thread.send_command(command, [0, 0, 0, 0, 0, 0, 0]):
            self.log_message("命令", "发送降落命令")
        else:
            self.log_message("错误", "发送降落命令失败")
            
    def send_rtl_command(self):
        """发送返航命令"""
        # MAV_CMD_NAV_RETURN_TO_LAUNCH
        command = 20
        
        if self.mavlink_thread.send_command(command, [0, 0, 0, 0, 0, 0, 0]):
            self.log_message("命令", "发送返航命令")
        else:
            self.log_message("错误", "发送返航命令失败")
            
    def set_flight_mode(self):
        """设置飞行模式"""
        mode_text = self.mode_combo.currentText()
        mode_mapping = {
            "稳定": 0, "特技": 1, "定高": 2, "悬停": 3, 
            "返航": 4, "任务": 5, "降落": 6, "引导": 7
        }
        
        mode = mode_mapping.get(mode_text, 0)
        
        # 使用MAV_CMD_DO_SET_MODE命令
        command = 176
        param1 = 1  # MAV_MODE_FLAG_CUSTOM_MODE_ENABLED
        param2 = mode
        
        if self.mavlink_thread.send_command(command, [param1, param2, 0, 0, 0, 0, 0]):
            self.log_message("命令", f"设置飞行模式为: {mode_text}")
        else:
            self.log_message("错误", "设置飞行模式失败")
            
    def send_custom_command(self):
        """发送自定义命令"""
        command = self.custom_command.value()
        param1 = self.param1.value()
        param2 = self.param2.value()
        param3 = self.param3.value()
        
        if self.mavlink_thread.send_command(command, [param1, param2, param3, 0, 0, 0, 0]):
            self.log_message("命令", f"发送自定义命令: {command}")
        else:
            self.log_message("错误", "发送自定义命令失败")
            
    def load_mission(self):
        """加载任务文件"""
        filename, _ = QFileDialog.getOpenFileName(
            self, "打开任务文件", "", "任务文件 (*.json *.mission);;所有文件 (*)")
        
        if filename:
            try:
                with open(filename, 'r') as f:
                    self.waypoints = json.load(f)
                    
                self.update_waypoint_table()
                self.log_message("任务", f"加载任务文件: {filename}")
            except Exception as e:
                self.log_message("错误", f"加载任务文件失败: {str(e)}")
                
    def save_mission(self):
        """保存任务文件"""
        filename, _ = QFileDialog.getSaveFileName(
            self, "保存任务文件", "", "任务文件 (*.json);;所有文件 (*)")
        
        if filename:
            try:
                with open(filename, 'w') as f:
                    json.dump(self.waypoints, f, indent=2)
                    
                self.log_message("任务", f"保存任务文件: {filename}")
            except Exception as e:
                self.log_message("错误", f"保存任务文件失败: {str(e)}")
                
    def upload_mission(self):
        """上传任务到飞行器"""
        self.log_message("任务", "开始上传任务")
        # 这里需要实现MAVLink任务上传协议
        # 由于实现较复杂，这里只显示日志
        
    def download_mission(self):
        """从飞行器下载任务"""
        self.log_message("任务", "开始下载任务")
        # 这里需要实现MAVLink任务下载协议
        # 由于实现较复杂，这里只显示日志
        
    def update_waypoint_table(self):
        """更新航点表格"""
        self.waypoint_table.setRowCount(len(self.waypoints))
        
        for i, wp in enumerate(self.waypoints):
            self.waypoint_table.setItem(i, 0, QTableWidgetItem(str(i)))
            self.waypoint_table.setItem(i, 1, QTableWidgetItem(str(wp.get('lon', 0))))
            self.waypoint_table.setItem(i, 2, QTableWidgetItem(str(wp.get('lat', 0))))
            self.waypoint_table.setItem(i, 3, QTableWidgetItem(str(wp.get('alt', 0))))
            self.waypoint_table.setItem(i, 4, QTableWidgetItem(str(wp.get('command', 0))))
            self.waypoint_table.setItem(i, 5, QTableWidgetItem(str(wp.get('param1', 0))))
            self.waypoint_table.setItem(i, 6, QTableWidgetItem(str(wp.get('param2', 0))))
            self.waypoint_table.setItem(i, 7, QTableWidgetItem(str(wp.get('param3', 0))))
            
    def refresh_parameters(self):
        """刷新参数"""
        self.log_message("参数", "开始刷新参数")
        # 这里需要实现MAVLink参数请求协议
        # 由于实现较复杂，这里只显示日志
        
    def save_parameters(self):
        """保存参数到文件"""
        filename, _ = QFileDialog.getSaveFileName(
            self, "保存参数文件", "", "参数文件 (*.json);;所有文件 (*)")
        
        if filename:
            try:
                with open(filename, 'w') as f:
                    json.dump(self.parameters, f, indent=2)
                    
                self.log_message("参数", f"保存参数文件: {filename}")
            except Exception as e:
                self.log_message("错误", f"保存参数文件失败: {str(e)}")
                
    def load_parameters(self):
        """从文件加载参数"""
        filename, _ = QFileDialog.getOpenFileName(
            self, "打开参数文件", "", "参数文件 (*.json);;所有文件 (*)")
        
        if filename:
            try:
                with open(filename, 'r') as f:
                    self.parameters = json.load(f)
                    
                self.update_parameter_table()
                self.log_message("参数", f"加载参数文件: {filename}")
            except Exception as e:
                self.log_message("错误", f"加载参数文件失败: {str(e)}")
                
    def on_parameter_changed(self, row, column):
        """参数表格单元格改变"""
        if column == 1:  # 值列
            param_name = self.parameter_table.item(row, 0).text()
            try:
                new_value = float(self.parameter_table.item(row, 1).text())
                # 这里应该发送参数设置命令到飞行器
                self.log_message("参数", f"参数 {param_name} 改为 {new_value}")
            except ValueError:
                self.log_message("错误", f"参数值无效: {self.parameter_table.item(row, 1).text()}")
                
    def clear_log(self):
        """清空日志"""
        self.log_text.clear()
        
    def save_log(self):
        """保存日志到文件"""
        filename, _ = QFileDialog.getSaveFileName(
            self, "保存日志文件", "", "日志文件 (*.log);;文本文件 (*.txt);;所有文件 (*)")
        
        if filename:
            try:
                with open(filename, 'w') as f:
                    f.write(self.log_text.toPlainText())
                    
                self.log_message("系统", f"保存日志文件: {filename}")
            except Exception as e:
                self.log_message("错误", f"保存日志文件失败: {str(e)}")
                
    def log_message(self, category, message):
        """记录日志消息"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] [{category}] {message}"
        
        # 添加到日志显示
        current_text = self.log_text.toPlainText()
        if current_text:
            current_text += '\n'
        current_text += log_entry
        
        self.log_text.setText(current_text)
        
        # 自动滚动到底部
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )
        
        # 同时在控制台输出
        print(log_entry)
        
    def closeEvent(self, event):
        """关闭事件处理"""
        if self.mavlink_thread.running:
            self.mavlink_thread.disconnect()
            self.mavlink_thread.wait(2000)  # 等待线程结束
            
        event.accept()

def main():
    """主函数"""
    app = QApplication(sys.argv)
    
    # 设置应用程序属性
    app.setApplicationName("MAVLink地面站")
    app.setApplicationVersion("1.0")
    app.setOrganizationName("MAVLink开发者")
    
    # 创建并显示主窗口
    window = MavlinkGroundStation()
    window.show()
    
    # 运行应用程序
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()