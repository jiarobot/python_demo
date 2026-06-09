import sys
import os
import json
import serial
import serial.tools.list_ports
import socket
import struct
import time
import csv
import importlib
import inspect
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QComboBox, QTextEdit, QLabel, QSpinBox, QDoubleSpinBox,
                             QSplitter, QTabWidget, QTreeWidget, QTreeWidgetItem, QFileDialog,
                             QProgressBar, QGroupBox, QCheckBox, QLineEdit, QMessageBox,
                             QDockWidget, QListWidget, QListWidgetItem, QAction, QMenu,
                             QToolBar, QStatusBar, QDialog, QFormLayout, QDialogButtonBox,
                             QPlainTextEdit, QFontDialog, QColorDialog, QTableWidget, QTableWidgetItem,
                             QHeaderView, QToolButton, QMenuBar, QSystemTrayIcon, QStyle)
from PyQt5.QtCore import QTimer, Qt, QThread, pyqtSignal, QSettings, QSize, QEvent, QPoint
from PyQt5.QtGui import (QFont, QColor, QTextCursor, QIcon, QPalette, QSyntaxHighlighter,
                         QTextCharFormat, QKeySequence, QPainter, QPixmap)
import pyqtgraph as pg
import numpy as np
from collections import deque

# 自定义语法高亮器
class PythonHighlighter(QSyntaxHighlighter):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 关键字格式
        self.keyword_format = QTextCharFormat()
        self.keyword_format.setForeground(Qt.darkBlue)
        self.keyword_format.setFontWeight(QFont.Bold)
        
        # 字符串格式
        self.string_format = QTextCharFormat()
        self.string_format.setForeground(Qt.darkGreen)
        
        # 注释格式
        self.comment_format = QTextCharFormat()
        self.comment_format.setForeground(Qt.darkGray)
        self.comment_format.setFontItalic(True)
        
        # 构建关键字模式
        self.keywords = [
            'and', 'as', 'assert', 'break', 'class', 'continue', 'def',
            'del', 'elif', 'else', 'except', 'False', 'finally', 'for',
            'from', 'global', 'if', 'import', 'in', 'is', 'lambda', 'None',
            'nonlocal', 'not', 'or', 'pass', 'raise', 'return', 'True',
            'try', 'while', 'with', 'yield'
        ]
        
        self.keyword_patterns = [r'\b' + keyword + r'\b' for keyword in self.keywords]
        
        # 构建规则
        self.rules = []
        
        # 关键字规则
        for pattern in self.keyword_patterns:
            self.rules.append((pattern, self.keyword_format))
        
        # 字符串规则
        self.rules.append((r'\"\"\"(.*?)\"\"\"', self.string_format))  # 多行字符串
        self.rules.append((r'\'(.*?)\'', self.string_format))  # 单引号字符串
        self.rules.append((r'\"(.*?)\"', self.string_format))  # 双引号字符串
        
        # 注释规则
        self.rules.append((r'#.*', self.comment_format))  # 单行注释
        
    def highlightBlock(self, text):
        for pattern, format in self.rules:
            expression = QtCore.QRegExp(pattern)
            index = expression.indexIn(text)
            while index >= 0:
                length = expression.matchedLength()
                self.setFormat(index, length, format)
                index = expression.indexIn(text, index + length)
        
        self.setCurrentBlockState(0)

# 协议解析器基类
class ProtocolParser:
    def __init__(self):
        self.name = "Generic Protocol"
        self.version = "1.0"
        
    def parse(self, data):
        """解析数据，返回解析后的结果"""
        return {"raw": data, "parsed": None, "error": "Not implemented"}
    
    def generate(self, command, parameters):
        """根据命令和参数生成数据"""
        return b''

# 示例协议解析器
class ExampleProtocolParser(ProtocolParser):
    def __init__(self):
        super().__init__()
        self.name = "Example Protocol"
        self.version = "1.0"
        
    def parse(self, data):
        try:
            # 假设协议格式: [START][LENGTH][COMMAND][DATA][CRC][END]
            if len(data) < 5:
                return {"raw": data, "parsed": None, "error": "Data too short"}
                
            start_byte = data[0]
            if start_byte != 0xAA:
                return {"raw": data, "parsed": None, "error": "Invalid start byte"}
                
            length = data[1]
            if len(data) != length + 4:  # 包括起始、长度、CRC和结束字节
                return {"raw": data, "parsed": None, "error": "Length mismatch"}
                
            command = data[2]
            payload = data[3:3+length-3]  # 减去命令字节和CRC
            
            # 计算CRC (简单示例)
            crc = sum(data[1:-2]) & 0xFF
            if crc != data[-2]:
                return {"raw": data, "parsed": None, "error": "CRC mismatch"}
                
            end_byte = data[-1]
            if end_byte != 0x55:
                return {"raw": data, "parsed": None, "error": "Invalid end byte"}
                
            # 解析成功
            return {
                "raw": data,
                "parsed": {
                    "command": command,
                    "payload": payload,
                    "crc": crc
                },
                "error": None
            }
        except Exception as e:
            return {"raw": data, "parsed": None, "error": f"Parse error: {str(e)}"}
    
    def generate(self, command, parameters):
        # 生成协议数据包
        start_byte = 0xAA
        payload = bytes([command]) + parameters.get('data', b'')
        length = len(payload) + 3  # 包括命令字节和CRC
        
        # 计算CRC
        data_for_crc = bytes([length]) + payload
        crc = sum(data_for_crc) & 0xFF
        end_byte = 0x55
        
        return bytes([start_byte, length]) + payload + bytes([crc, end_byte])

# 插件系统基类
class PluginBase:
    def __init__(self, main_window):
        self.main_window = main_window
        self.name = "Unnamed Plugin"
        self.version = "1.0"
        self.description = "No description"
        
    def initialize(self):
        """插件初始化"""
        pass
        
    def cleanup(self):
        """插件清理"""
        pass

# 示例插件
class ExamplePlugin(PluginBase):
    def __init__(self, main_window):
        super().__init__(main_window)
        self.name = "Example Plugin"
        self.version = "1.0"
        self.description = "An example plugin for the embedded development tool"
        
    def initialize(self):
        # 添加自定义菜单项
        self.action = QAction("Example Plugin Action", self.main_window)
        self.action.triggered.connect(self.on_action_triggered)
        self.main_window.plugins_menu.addAction(self.action)
        
        # 添加自定义工具栏按钮
        self.toolbar_button = QToolButton()
        self.toolbar_button.setText("Example")
        self.toolbar_button.clicked.connect(self.on_action_triggered)
        self.main_window.plugin_toolbar.addWidget(self.toolbar_button)
        
        self.main_window.log("Example plugin initialized")
        
    def cleanup(self):
        self.main_window.plugins_menu.removeAction(self.action)
        self.toolbar_button.deleteLater()
        self.main_window.log("Example plugin cleaned up")
        
    def on_action_triggered(self):
        self.main_window.log("Example plugin action triggered")
        QMessageBox.information(self.main_window, "Example Plugin", "This is an example plugin!")

# 串口通信线程
class SerialThread(QThread):
    data_received = pyqtSignal(bytes)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, port, baudrate, parent=None):
        super().__init__(parent)
        self.port = port
        self.baudrate = baudrate
        self.serial = None
        self.running = False
        
    def run(self):
        try:
            self.serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=0.1  # 更短的超时时间以提高响应性
            )
            self.running = True
            
            while self.running:
                if self.serial.in_waiting > 0:
                    data = self.serial.read(self.serial.in_waiting)
                    self.data_received.emit(data)
                else:
                    time.sleep(0.001)  # 短暂休眠以减少CPU占用
                    
        except Exception as e:
            self.error_occurred.emit(str(e))
        finally:
            if self.serial and self.serial.is_open:
                self.serial.close()
                
    def stop(self):
        self.running = False
        self.wait(1000)  # 等待最多1秒
        
    def write_data(self, data):
        if self.serial and self.serial.is_open:
            try:
                self.serial.write(data)
            except Exception as e:
                self.error_occurred.emit(str(e))

# TCP客户端线程
class TCPClientThread(QThread):
    data_received = pyqtSignal(bytes)
    error_occurred = pyqtSignal(str)
    connected = pyqtSignal()
    disconnected = pyqtSignal()
    
    def __init__(self, host, port, parent=None):
        super().__init__(parent)
        self.host = host
        self.port = port
        self.socket = None
        self.running = False
        
    def run(self):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            self.socket.settimeout(0.1)  # 设置超时时间
            self.connected.emit()
            self.running = True
            
            while self.running:
                try:
                    data = self.socket.recv(4096)
                    if data:
                        self.data_received.emit(data)
                    else:
                        # 连接已关闭
                        self.disconnected.emit()
                        break
                except socket.timeout:
                    continue
                except Exception as e:
                    self.error_occurred.emit(str(e))
                    break
                    
        except Exception as e:
            self.error_occurred.emit(str(e))
        finally:
            if self.socket:
                self.socket.close()
                
    def stop(self):
        self.running = False
        self.wait(1000)  # 等待最多1秒
        
    def write_data(self, data):
        if self.socket:
            try:
                self.socket.sendall(data)
            except Exception as e:
                self.error_occurred.emit(str(e))

# 脚本执行线程
class ScriptThread(QThread):
    output = pyqtSignal(str)
    error = pyqtSignal(str)
    finished = pyqtSignal()
    
    def __init__(self, script, globals_dict, parent=None):
        super().__init__(parent)
        self.script = script
        self.globals_dict = globals_dict
        
    def run(self):
        try:
            # 重定向输出
            import sys
            from io import StringIO
            
            old_stdout = sys.stdout
            old_stderr = sys.stderr
            sys.stdout = stdout_capture = StringIO()
            sys.stderr = stderr_capture = StringIO()
            
            # 执行脚本
            exec(self.script, self.globals_dict)
            
            # 恢复标准输出
            sys.stdout = old_stdout
            sys.stderr = old_stderr
            
            # 获取输出
            output = stdout_capture.getvalue()
            error = stderr_capture.getvalue()
            
            if output:
                self.output.emit(output)
            if error:
                self.error.emit(error)
                
        except Exception as e:
            self.error.emit(str(e))
        finally:
            self.finished.emit()

# 固件管理类
class FirmwareManager:
    def __init__(self):
        self.firmware_list = []
        self.load_firmware_list()
        
    def load_firmware_list(self):
        try:
            if os.path.exists('firmware_list.json'):
                with open('firmware_list.json', 'r') as f:
                    self.firmware_list = json.load(f)
        except:
            self.firmware_list = []
            
    def save_firmware_list(self):
        with open('firmware_list.json', 'w') as f:
            json.dump(self.firmware_list, f, indent=4)
            
    def add_firmware(self, name, path, version, description):
        firmware = {
            'name': name,
            'path': path,
            'version': version,
            'description': description,
            'date_added': datetime.now().isoformat()
        }
        self.firmware_list.append(firmware)
        self.save_firmware_list()
        
    def remove_firmware(self, index):
        if 0 <= index < len(self.firmware_list):
            self.firmware_list.pop(index)
            self.save_firmware_list()

# 数据记录器
class DataLogger:
    def __init__(self):
        self.file = None
        self.writer = None
        self.is_logging = False
        
    def start_logging(self, filename):
        try:
            self.file = open(filename, 'w', newline='')
            self.writer = csv.writer(self.file)
            self.is_logging = True
            return True
        except Exception as e:
            return False, str(e)
            
    def stop_logging(self):
        if self.file:
            self.file.close()
            self.file = None
            self.writer = None
        self.is_logging = False
        
    def log_data(self, timestamp, data):
        if self.is_logging and self.writer:
            self.writer.writerow([timestamp] + data)

# 主窗口类
class EmbeddedDevelopmentTool(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("高级嵌入式开发系统工具")
        self.setGeometry(100, 100, 1400, 900)
        
        # 初始化组件
        self.serial_thread = None
        self.tcp_thread = None
        self.script_thread = None
        self.firmware_manager = FirmwareManager()
        self.data_logger = DataLogger()
        self.protocol_parsers = {}
        self.plugins = {}
        
        self.data_buffer = deque(maxlen=10000)
        self.plot_data = {}
        self.max_data_points = 1000
        
        # 应用设置
        self.settings = QSettings("YourCompany", "EmbeddedDevelopmentTool")
        
        self.init_ui()
        self.load_settings()
        self.scan_serial_ports()
        self.load_protocol_parsers()
        self.load_plugins()
        
    def init_ui(self):
        # 创建中央部件和主布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # 创建菜单栏
        self.create_menus()
        
        # 创建工具栏
        self.create_toolbars()
        
        # 创建状态栏
        self.statusBar().showMessage("就绪")
        
        # 创建左侧面板
        left_panel = QWidget()
        left_panel.setMaximumWidth(350)
        left_layout = QVBoxLayout(left_panel)
        
        # 连接设置组
        connection_group = QGroupBox("连接设置")
        connection_layout = QVBoxLayout(connection_group)
        
        # 连接类型选择
        conn_type_layout = QHBoxLayout()
        conn_type_layout.addWidget(QLabel("类型:"))
        self.conn_type_combo = QComboBox()
        self.conn_type_combo.addItems(["串口", "TCP客户端"])
        self.conn_type_combo.currentTextChanged.connect(self.on_connection_type_changed)
        conn_type_layout.addWidget(self.conn_type_combo)
        connection_layout.addLayout(conn_type_layout)
        
        # 串口设置
        self.serial_widget = QWidget()
        serial_layout = QVBoxLayout(self.serial_widget)
        
        port_layout = QHBoxLayout()
        port_layout.addWidget(QLabel("端口:"))
        self.port_combo = QComboBox()
        port_layout.addWidget(self.port_combo)
        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.clicked.connect(self.scan_serial_ports)
        port_layout.addWidget(self.refresh_btn)
        serial_layout.addLayout(port_layout)
        
        baud_layout = QHBoxLayout()
        baud_layout.addWidget(QLabel("波特率:"))
        self.baud_combo = QComboBox()
        self.baud_combo.addItems(["9600", "19200", "38400", "57600", "115200", "230400", "460800", "921600"])
        self.baud_combo.setCurrentText("115200")
        baud_layout.addWidget(self.baud_combo)
        serial_layout.addLayout(baud_layout)
        
        connection_layout.addWidget(self.serial_widget)
        
        # TCP设置
        self.tcp_widget = QWidget()
        self.tcp_widget.setVisible(False)
        tcp_layout = QVBoxLayout(self.tcp_widget)
        
        host_layout = QHBoxLayout()
        host_layout.addWidget(QLabel("主机:"))
        self.host_edit = QLineEdit("127.0.0.1")
        host_layout.addWidget(self.host_edit)
        tcp_layout.addLayout(host_layout)
        
        port_layout = QHBoxLayout()
        port_layout.addWidget(QLabel("端口:"))
        self.port_edit = QLineEdit("8080")
        port_layout.addWidget(self.port_edit)
        tcp_layout.addLayout(port_layout)
        
        connection_layout.addWidget(self.tcp_widget)
        
        # 协议解析器选择
        protocol_layout = QHBoxLayout()
        protocol_layout.addWidget(QLabel("协议:"))
        self.protocol_combo = QComboBox()
        self.protocol_combo.addItems(list(self.protocol_parsers.keys()))
        protocol_layout.addWidget(self.protocol_combo)
        connection_layout.addLayout(protocol_layout)
        
        self.connect_btn = QPushButton("连接")
        self.connect_btn.clicked.connect(self.toggle_connection)
        connection_layout.addWidget(self.connect_btn)
        
        left_layout.addWidget(connection_group)
        
        # 数据发送组
        send_group = QGroupBox("数据发送")
        send_layout = QVBoxLayout(send_group)
        
        self.send_text = QTextEdit()
        self.send_text.setMaximumHeight(100)
        send_layout.addWidget(self.send_text)
        
        send_btn_layout = QHBoxLayout()
        self.send_btn = QPushButton("发送")
        self.send_btn.clicked.connect(self.send_data)
        send_btn_layout.addWidget(self.send_btn)
        
        self.hex_send = QCheckBox("十六进制发送")
        send_btn_layout.addWidget(self.hex_send)
        send_layout.addLayout(send_btn_layout)
        
        left_layout.addWidget(send_group)
        
        # 命令模板组
        self.command_group = QGroupBox("命令模板")
        command_layout = QVBoxLayout(self.command_group)
        
        self.command_list = QListWidget()
        self.load_command_templates()
        self.command_list.itemDoubleClicked.connect(self.on_command_template_selected)
        command_layout.addWidget(self.command_list)
        
        command_btn_layout = QHBoxLayout()
        self.add_cmd_btn = QPushButton("添加")
        self.add_cmd_btn.clicked.connect(self.add_command_template)
        command_btn_layout.addWidget(self.add_cmd_btn)
        
        self.edit_cmd_btn = QPushButton("编辑")
        self.edit_cmd_btn.clicked.connect(self.edit_command_template)
        command_btn_layout.addWidget(self.edit_cmd_btn)
        
        self.del_cmd_btn = QPushButton("删除")
        self.del_cmd_btn.clicked.connect(self.delete_command_template)
        command_btn_layout.addWidget(self.del_cmd_btn)
        
        command_layout.addLayout(command_btn_layout)
        left_layout.addWidget(self.command_group)
        
        # 固件管理组
        firmware_group = QGroupBox("固件管理")
        firmware_layout = QVBoxLayout(firmware_group)
        
        self.firmware_tree = QTreeWidget()
        self.firmware_tree.setHeaderLabels(["名称", "版本", "日期"])
        firmware_layout.addWidget(self.firmware_tree)
        
        firmware_btn_layout = QHBoxLayout()
        self.add_firmware_btn = QPushButton("添加固件")
        self.add_firmware_btn.clicked.connect(self.add_firmware)
        firmware_btn_layout.addWidget(self.add_firmware_btn)
        
        self.flash_btn = QPushButton("刷写固件")
        self.flash_btn.clicked.connect(self.flash_firmware)
        firmware_btn_layout.addWidget(self.flash_btn)
        firmware_layout.addLayout(firmware_btn_layout)
        
        left_layout.addWidget(firmware_group)
        left_layout.addStretch()
        
        # 创建右侧面板（标签页）
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.tabCloseRequested.connect(self.close_tab)
        
        # 终端标签页
        self.terminal_tab = QWidget()
        terminal_layout = QVBoxLayout(self.terminal_tab)
        
        self.terminal = QTextEdit()
        self.terminal.setReadOnly(True)
        terminal_layout.addWidget(self.terminal)
        
        terminal_controls = QHBoxLayout()
        self.clear_btn = QPushButton("清空终端")
        self.clear_btn.clicked.connect(self.terminal.clear)
        terminal_controls.addWidget(self.clear_btn)
        
        self.hex_display = QCheckBox("十六进制显示")
        terminal_controls.addWidget(self.hex_display)
        
        self.timestamp = QCheckBox("时间戳")
        terminal_controls.addWidget(self.timestamp)
        
        self.log_data = QCheckBox("记录数据")
        self.log_data.stateChanged.connect(self.toggle_data_logging)
        terminal_controls.addWidget(self.log_data)
        
        terminal_layout.addLayout(terminal_controls)
        
        self.tab_widget.addTab(self.terminal_tab, "终端")
        
        # 绘图标签页
        self.plot_tab = QWidget()
        plot_layout = QVBoxLayout(self.plot_tab)
        
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.addLegend()
        self.plot_curves = {}
        plot_layout.addWidget(self.plot_widget)
        
        plot_controls = QHBoxLayout()
        plot_controls.addWidget(QLabel("最大数据点:"))
        self.max_points_spin = QSpinBox()
        self.max_points_spin.setRange(100, 100000)
        self.max_points_spin.setValue(1000)
        self.max_points_spin.valueChanged.connect(self.update_max_data_points)
        plot_controls.addWidget(self.max_points_spin)
        
        self.add_plot_btn = QPushButton("添加曲线")
        self.add_plot_btn.clicked.connect(self.add_plot_curve)
        plot_controls.addWidget(self.add_plot_btn)
        
        self.clear_plot_btn = QPushButton("清除图表")
        self.clear_plot_btn.clicked.connect(self.clear_plot)
        plot_controls.addWidget(self.clear_plot_btn)
        plot_layout.addLayout(plot_controls)
        
        self.tab_widget.addTab(self.plot_tab, "数据绘图")
        
        # 脚本编辑标签页
        self.script_tab = QWidget()
        script_layout = QVBoxLayout(self.script_tab)
        
        self.script_editor = QPlainTextEdit()
        self.script_editor.setPlaceholderText("输入Python脚本代码...")
        
        # 设置语法高亮
        self.highlighter = PythonHighlighter(self.script_editor.document())
        
        script_layout.addWidget(self.script_editor)
        
        script_controls = QHBoxLayout()
        self.run_script_btn = QPushButton("运行脚本")
        self.run_script_btn.clicked.connect(self.run_script)
        script_controls.addWidget(self.run_script_btn)
        
        self.load_script_btn = QPushButton("加载脚本")
        self.load_script_btn.clicked.connect(self.load_script)
        script_controls.addWidget(self.load_script_btn)
        
        self.save_script_btn = QPushButton("保存脚本")
        self.save_script_btn.clicked.connect(self.save_script)
        script_controls.addWidget(self.save_script_btn)
        script_layout.addLayout(script_controls)
        
        self.tab_widget.addTab(self.script_tab, "脚本编辑")
        
        # 数据查看标签页
        self.data_tab = QWidget()
        data_layout = QVBoxLayout(self.data_tab)
        
        self.data_table = QTableWidget()
        self.data_table.setColumnCount(3)
        self.data_table.setHorizontalHeaderLabels(["时间戳", "原始数据", "解析数据"])
        self.data_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        data_layout.addWidget(self.data_table)
        
        data_controls = QHBoxLayout()
        self.export_data_btn = QPushButton("导出数据")
        self.export_data_btn.clicked.connect(self.export_data)
        data_controls.addWidget(self.export_data_btn)
        
        self.clear_data_btn = QPushButton("清除数据")
        self.clear_data_btn.clicked.connect(self.clear_data_table)
        data_controls.addWidget(self.clear_data_btn)
        data_layout.addLayout(data_controls)
        
        self.tab_widget.addTab(self.data_tab, "数据查看")
        
        # 添加到主布局
        main_layout.addWidget(left_panel)
        main_layout.addWidget(self.tab_widget)
        
        # 创建停靠窗口
        self.create_dock_windows()
        
        # 更新固件列表
        self.update_firmware_list()
        
    def create_menus(self):
        # 文件菜单
        file_menu = self.menuBar().addMenu("文件")
        
        new_action = QAction("新建", self)
        new_action.setShortcut(QKeySequence.New)
        file_menu.addAction(new_action)
        
        open_action = QAction("打开", self)
        open_action.setShortcut(QKeySequence.Open)
        file_menu.addAction(open_action)
        
        save_action = QAction("保存", self)
        save_action.setShortcut(QKeySequence.Save)
        file_menu.addAction(save_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("退出", self)
        exit_action.setShortcut(QKeySequence.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 编辑菜单
        edit_menu = self.menuBar().addMenu("编辑")
        
        undo_action = QAction("撤销", self)
        undo_action.setShortcut(QKeySequence.Undo)
        edit_menu.addAction(undo_action)
        
        redo_action = QAction("重做", self)
        redo_action.setShortcut(QKeySequence.Redo)
        edit_menu.addAction(redo_action)
        
        edit_menu.addSeparator()
        
        cut_action = QAction("剪切", self)
        cut_action.setShortcut(QKeySequence.Cut)
        edit_menu.addAction(cut_action)
        
        copy_action = QAction("复制", self)
        copy_action.setShortcut(QKeySequence.Copy)
        edit_menu.addAction(copy_action)
        
        paste_action = QAction("粘贴", self)
        paste_action.setShortcut(QKeySequence.Paste)
        edit_menu.addAction(paste_action)
        
        # 视图菜单
        view_menu = self.menuBar().addMenu("视图")
        
        self.toggle_dock_action = QAction("切换停靠窗口", self)
        self.toggle_dock_action.setCheckable(True)
        self.toggle_dock_action.setChecked(True)
        self.toggle_dock_action.triggered.connect(self.toggle_dock_windows)
        view_menu.addAction(self.toggle_dock_action)
        
        # 工具菜单
        tools_menu = self.menuBar().addMenu("工具")
        
        settings_action = QAction("设置", self)
        settings_action.triggered.connect(self.show_settings)
        tools_menu.addAction(settings_action)
        
        # 插件菜单
        self.plugins_menu = self.menuBar().addMenu("插件")
        
        # 帮助菜单
        help_menu = self.menuBar().addMenu("帮助")
        
        about_action = QAction("关于", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
    def create_toolbars(self):
        # 主工具栏
        self.main_toolbar = self.addToolBar("主工具栏")
        self.main_toolbar.setIconSize(QSize(16, 16))
        
        # 连接工具栏
        self.conn_toolbar = self.addToolBar("连接工具栏")
        self.conn_toolbar.setIconSize(QSize(16, 16))
        
        # 插件工具栏
        self.plugin_toolbar = self.addToolBar("插件工具栏")
        self.plugin_toolbar.setIconSize(QSize(16, 16))
        
    def create_dock_windows(self):
        # 创建日志停靠窗口
        self.log_dock = QDockWidget("日志", self)
        self.log_widget = QTextEdit()
        self.log_widget.setReadOnly(True)
        self.log_dock.setWidget(self.log_widget)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.log_dock)
        
        # 创建变量监视停靠窗口
        self.watch_dock = QDockWidget("变量监视", self)
        self.watch_widget = QTableWidget()
        self.watch_widget.setColumnCount(3)
        self.watch_widget.setHorizontalHeaderLabels(["名称", "值", "类型"])
        self.watch_dock.setWidget(self.watch_widget)
        self.addDockWidget(Qt.RightDockWidgetArea, self.watch_dock)
        
    def toggle_dock_windows(self, visible):
        self.log_dock.setVisible(visible)
        self.watch_dock.setVisible(visible)
        
    def load_settings(self):
        # 加载窗口几何状态
        geometry = self.settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
            
        window_state = self.settings.value("windowState")
        if window_state:
            self.restoreState(window_state)
            
        # 加载其他设置
        self.hex_display.setChecked(self.settings.value("hexDisplay", False, type=bool))
        self.timestamp.setChecked(self.settings.value("timestamp", True, type=bool))
        self.max_points_spin.setValue(self.settings.value("maxDataPoints", 1000, type=int))
        
    def save_settings(self):
        # 保存窗口几何状态
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("windowState", self.saveState())
        
        # 保存其他设置
        self.settings.setValue("hexDisplay", self.hex_display.isChecked())
        self.settings.setValue("timestamp", self.timestamp.isChecked())
        self.settings.setValue("maxDataPoints", self.max_points_spin.value())
        
    def closeEvent(self, event):
        self.save_settings()
        
        # 停止所有线程
        if self.serial_thread and self.serial_thread.isRunning():
            self.serial_thread.stop()
            
        if self.tcp_thread and self.tcp_thread.isRunning():
            self.tcp_thread.stop()
            
        if self.script_thread and self.script_thread.isRunning():
            self.script_thread.quit()
            self.script_thread.wait()
            
        # 停止数据记录
        if self.data_logger.is_logging:
            self.data_logger.stop_logging()
            
        # 清理插件
        for plugin in self.plugins.values():
            plugin.cleanup()
            
        event.accept()
        
    def scan_serial_ports(self):
        self.port_combo.clear()
        ports = serial.tools.list_ports.comports()
        for port in ports:
            self.port_combo.addItem(port.device, port.description)
            
    def on_connection_type_changed(self, text):
        if text == "串口":
            self.serial_widget.setVisible(True)
            self.tcp_widget.setVisible(False)
        else:
            self.serial_widget.setVisible(False)
            self.tcp_widget.setVisible(True)
            
    def toggle_connection(self):
        if (self.serial_thread and self.serial_thread.isRunning()) or \
           (self.tcp_thread and self.tcp_thread.isRunning()):
            self.disconnect()
        else:
            self.connect()
            
    def connect(self):
        conn_type = self.conn_type_combo.currentText()
        
        if conn_type == "串口":
            port = self.port_combo.currentText()
            baudrate = int(self.baud_combo.currentText())
            
            if not port:
                QMessageBox.warning(self, "警告", "请选择串口")
                return
                
            try:
                self.serial_thread = SerialThread(port, baudrate)
                self.serial_thread.data_received.connect(self.handle_data_received)
                self.serial_thread.error_occurred.connect(self.handle_connection_error)
                self.serial_thread.start()
                
                self.connect_btn.setText("断开")
                self.statusBar().showMessage(f"已连接到 {port}，波特率 {baudrate}")
                self.log(f"已连接到串口 {port}，波特率 {baudrate}")
                
            except Exception as e:
                QMessageBox.critical(self, "错误", f"无法打开串口: {str(e)}")
                
        else:  # TCP客户端
            host = self.host_edit.text()
            try:
                port = int(self.port_edit.text())
            except ValueError:
                QMessageBox.warning(self, "警告", "端口号必须是整数")
                return
                
            try:
                self.tcp_thread = TCPClientThread(host, port)
                self.tcp_thread.data_received.connect(self.handle_data_received)
                self.tcp_thread.error_occurred.connect(self.handle_connection_error)
                self.tcp_thread.connected.connect(self.on_tcp_connected)
                self.tcp_thread.disconnected.connect(self.on_tcp_disconnected)
                self.tcp_thread.start()
                
                self.connect_btn.setText("断开")
                self.statusBar().showMessage(f"正在连接到 {host}:{port}...")
                self.log(f"正在连接到 {host}:{port}...")
                
            except Exception as e:
                QMessageBox.critical(self, "错误", f"无法连接到服务器: {str(e)}")
                
    def disconnect(self):
        if self.serial_thread:
            self.serial_thread.stop()
            self.serial_thread = None
            
        if self.tcp_thread:
            self.tcp_thread.stop()
            self.tcp_thread = None
            
        self.connect_btn.setText("连接")
        self.statusBar().showMessage("已断开连接")
        self.log("连接已断开")
        
    def on_tcp_connected(self):
        host = self.host_edit.text()
        port = self.port_edit.text()
        self.statusBar().showMessage(f"已连接到 {host}:{port}")
        self.log(f"已连接到 {host}:{port}")
        
    def on_tcp_disconnected(self):
        self.disconnect()
        
    def handle_connection_error(self, error_msg):
        QMessageBox.critical(self, "连接错误", error_msg)
        self.disconnect()
        
    def handle_data_received(self, data):
        # 记录原始数据
        timestamp = datetime.now()
        self.data_buffer.append((timestamp, data))
        
        # 更新数据表格
        self.update_data_table(timestamp, data)
        
        # 记录数据到文件
        if self.data_logger.is_logging:
            self.data_logger.log_data(timestamp.isoformat(), [b.hex() for b in data])
            
        # 协议解析
        protocol_name = self.protocol_combo.currentText()
        if protocol_name in self.protocol_parsers:
            parser = self.protocol_parsers[protocol_name]
            result = parser.parse(data)
            
            if result["error"]:
                self.log(f"协议解析错误: {result['error']}")
            else:
                self.log(f"解析结果: {result['parsed']}")
                # 处理解析后的数据，例如更新变量监视器
                self.process_parsed_data(result['parsed'])
        else:
            # 直接显示数据
            if self.hex_display.isChecked():
                display_data = ' '.join([f'{b:02X}' for b in data])
            else:
                display_data = data.decode('utf-8', errors='replace')
                
            if self.timestamp.isChecked():
                timestamp_str = timestamp.strftime("%H:%M:%S.%f")[:-3]
                display_data = f"[{timestamp_str}] {display_data}"
                
            self.terminal.moveCursor(self.terminal.textCursor().End)
            self.terminal.insertPlainText(display_data)
            self.terminal.moveCursor(self.terminal.textCursor().End)
            
            # 尝试解析数据用于绘图
            self.process_data_for_plotting(data)
            
    def process_parsed_data(self, parsed_data):
        # 这里可以根据解析结果更新变量监视器或其他UI元素
        if isinstance(parsed_data, dict):
            for key, value in parsed_data.items():
                self.update_watch_table(key, value, type(value).__name__)
                
    def update_watch_table(self, name, value, value_type):
        # 查找是否已存在该变量
        for row in range(self.watch_widget.rowCount()):
            if self.watch_widget.item(row, 0).text() == name:
                # 更新现有行
                self.watch_widget.item(row, 1).setText(str(value))
                self.watch_widget.item(row, 2).setText(value_type)
                return
                
        # 添加新行
        row = self.watch_widget.rowCount()
        self.watch_widget.insertRow(row)
        self.watch_widget.setItem(row, 0, QTableWidgetItem(name))
        self.watch_widget.setItem(row, 1, QTableWidgetItem(str(value)))
        self.watch_widget.setItem(row, 2, QTableWidgetItem(value_type))
        
    def update_data_table(self, timestamp, data):
        # 限制数据表行数
        if self.data_table.rowCount() > 1000:
            self.data_table.removeRow(0)
            
        # 添加新行
        row = self.data_table.rowCount()
        self.data_table.insertRow(row)
        
        # 时间戳
        timestamp_item = QTableWidgetItem(timestamp.strftime("%H:%M:%S.%f")[:-3])
        self.data_table.setItem(row, 0, timestamp_item)
        
        # 原始数据
        hex_data = ' '.join([f'{b:02X}' for b in data])
        hex_item = QTableWidgetItem(hex_data)
        self.data_table.setItem(row, 1, hex_item)
        
        # 解析数据
        protocol_name = self.protocol_combo.currentText()
        if protocol_name in self.protocol_parsers:
            parser = self.protocol_parsers[protocol_name]
            result = parser.parse(data)
            if result["error"]:
                parsed_item = QTableWidgetItem(f"错误: {result['error']}")
            else:
                parsed_item = QTableWidgetItem(str(result['parsed']))
        else:
            try:
                text_data = data.decode('utf-8', errors='replace')
                parsed_item = QTableWidgetItem(text_data)
            except:
                parsed_item = QTableWidgetItem("二进制数据")
                
        self.data_table.setItem(row, 2, parsed_item)
        
        # 自动滚动到最后一行
        self.data_table.scrollToItem(parsed_item)
        
    def send_data(self):
        if (not self.serial_thread or not self.serial_thread.isRunning()) and \
           (not self.tcp_thread or not self.tcp_thread.isRunning()):
            QMessageBox.warning(self, "警告", "请先连接")
            return
            
        text = self.send_text.toPlainText()
        if not text:
            return
            
        if self.hex_send.isChecked():
            # 尝试将十六进制字符串转换为字节
            try:
                text = text.strip()
                # 移除可能的分隔符
                text = text.replace(' ', '').replace('\n', '').replace('\t', '')
                data = bytes.fromhex(text)
            except ValueError:
                QMessageBox.warning(self, "错误", "无效的十六进制数据")
                return
        else:
            data = text.encode('utf-8')
            
        if self.serial_thread and self.serial_thread.isRunning():
            self.serial_thread.write_data(data)
        elif self.tcp_thread and self.tcp_thread.isRunning():
            self.tcp_thread.write_data(data)
            
    def process_data_for_plotting(self, data):
        # 简单的数据处理，实际应用中可能需要更复杂的协议解析
        try:
            # 假设数据是逗号分隔的数值
            text = data.decode('utf-8', errors='ignore')
            lines = text.split('\n')
            
            for line in lines:
                line = line.strip()
                if line:
                    values = line.split(',')
                    for i, val in enumerate(values):
                        try:
                            num = float(val)
                            curve_name = f"曲线 {i+1}"
                            
                            if curve_name not in self.plot_data:
                                self.plot_data[curve_name] = deque(maxlen=self.max_data_points)
                                # 添加新曲线
                                color = pg.intColor(len(self.plot_curves) * 30, hues=len(self.plot_curves) + 1)
                                curve = self.plot_widget.plot(pen=color, name=curve_name)
                                self.plot_curves[curve_name] = curve
                                
                            self.plot_data[curve_name].append(num)
                            
                        except ValueError:
                            pass
                            
            # 更新所有曲线
            for curve_name, curve in self.plot_curves.items():
                if curve_name in self.plot_data and self.plot_data[curve_name]:
                    x_data = list(range(len(self.plot_data[curve_name])))
                    curve.setData(x_data, list(self.plot_data[curve_name]))
                
        except:
            pass
            
    def update_max_data_points(self, value):
        self.max_data_points = value
        # 裁剪现有数据
        for curve_name in self.plot_data:
            if len(self.plot_data[curve_name]) > self.max_data_points:
                self.plot_data[curve_name] = deque(list(self.plot_data[curve_name])[-self.max_data_points:], 
                                                 maxlen=self.max_data_points)
                
    def add_plot_curve(self):
        name, ok = QInputDialog.getText(self, "添加曲线", "请输入曲线名称:")
        if ok and name:
            if name not in self.plot_data:
                self.plot_data[name] = deque(maxlen=self.max_data_points)
                # 添加新曲线
                color = pg.intColor(len(self.plot_curves) * 30, hues=len(self.plot_curves) + 1)
                curve = self.plot_widget.plot(pen=color, name=name)
                self.plot_curves[name] = curve
                self.log(f"已添加曲线: {name}")
            else:
                QMessageBox.warning(self, "警告", "曲线名称已存在")
                
    def clear_plot(self):
        self.plot_data.clear()
        self.plot_curves.clear()
        self.plot_widget.clear()
        self.log("图表已清除")
        
    def update_firmware_list(self):
        self.firmware_tree.clear()
        for fw in self.firmware_manager.firmware_list:
            item = QTreeWidgetItem([fw['name'], fw['version'], fw['date_added']])
            self.firmware_tree.addTopLevelItem(item)
            
    def add_firmware(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择固件文件", "", "二进制文件 (*.bin *.hex);;所有文件 (*)"
        )
        
        if file_path:
            name = os.path.basename(file_path)
            
            dialog = QDialog(self)
            dialog.setWindowTitle("固件信息")
            layout = QFormLayout(dialog)
            
            name_edit = QLineEdit(name)
            version_edit = QLineEdit("1.0.0")
            desc_edit = QLineEdit()
            
            layout.addRow("名称:", name_edit)
            layout.addRow("版本:", version_edit)
            layout.addRow("描述:", desc_edit)
            
            buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
            buttons.accepted.connect(dialog.accept)
            buttons.rejected.connect(dialog.reject)
            layout.addRow(buttons)
            
            if dialog.exec_() == QDialog.Accepted:
                self.firmware_manager.add_firmware(
                    name_edit.text(),
                    file_path,
                    version_edit.text(),
                    desc_edit.text()
                )
                self.update_firmware_list()
                self.log(f"已添加固件: {name_edit.text()}")
                
    def flash_firmware(self):
        current_item = self.firmware_tree.currentItem()
        if not current_item:
            QMessageBox.warning(self, "警告", "请先选择要刷写的固件")
            return
            
        index = self.firmware_tree.indexOfTopLevelItem(current_item)
        firmware = self.firmware_manager.firmware_list[index]
        
        # 这里应该实现实际的固件刷写逻辑
        # 这通常涉及通过串口发送特定的 bootloader 命令和固件数据
        reply = QMessageBox.question(self, "确认", f"确定要刷写固件 {firmware['name']} 吗?")
        
        if reply == QMessageBox.Yes:
            # 模拟刷写过程
            progress = QProgressDialog("刷写固件...", "取消", 0, 100, self)
            progress.setWindowModality(Qt.WindowModal)
            
            for i in range(101):
                progress.setValue(i)
                QApplication.processEvents()
                if progress.wasCanceled():
                    break
                time.sleep(0.05)
                
            progress.setValue(100)
            self.log(f"固件 {firmware['name']} 刷写完成")
            
    def toggle_data_logging(self, state):
        if state == Qt.Checked:
            file_path, _ = QFileDialog.getSaveFileName(
                self, "选择日志文件", "", "CSV文件 (*.csv);;所有文件 (*)"
            )
            
            if file_path:
                success, error = self.data_logger.start_logging(file_path)
                if success:
                    self.log(f"开始记录数据到: {file_path}")
                else:
                    self.log(f"无法开始记录数据: {error}")
                    self.log_data.setChecked(False)
        else:
            self.data_logger.stop_logging()
            self.log("停止记录数据")
            
    def export_data(self):
        if not self.data_buffer:
            QMessageBox.warning(self, "警告", "没有数据可导出")
            return
            
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出数据", "", "CSV文件 (*.csv);;所有文件 (*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(["Timestamp", "Data"])
                    
                    for timestamp, data in self.data_buffer:
                        hex_data = ' '.join([f'{b:02X}' for b in data])
                        writer.writerow([timestamp.isoformat(), hex_data])
                        
                self.log(f"数据已导出到: {file_path}")
            except Exception as e:
                self.log(f"导出数据失败: {str(e)}")
                
    def clear_data_table(self):
        self.data_table.setRowCount(0)
        self.data_buffer.clear()
        self.log("数据表已清除")
        
    def load_script(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "打开脚本", "", "Python文件 (*.py);;所有文件 (*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'r') as f:
                    self.script_editor.setPlainText(f.read())
                self.log(f"已加载脚本: {file_path}")
            except Exception as e:
                self.log(f"加载脚本失败: {str(e)}")
                
    def save_script(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存脚本", "", "Python文件 (*.py);;所有文件 (*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w') as f:
                    f.write(self.script_editor.toPlainText())
                self.log(f"脚本已保存到: {file_path}")
            except Exception as e:
                self.log(f"保存脚本失败: {str(e)}")
                
    def run_script(self):
        script = self.script_editor.toPlainText()
        if not script:
            QMessageBox.warning(self, "警告", "脚本为空")
            return
            
        # 创建脚本执行环境
        globals_dict = {
            'app': QApplication.instance(),
            'main_window': self,
            'serial_thread': self.serial_thread,
            'tcp_thread': self.tcp_thread,
            'log': self.log,
            'send_data': self.send_data_from_script,
            'plot_data': self.add_plot_data
        }
        
        # 启动脚本执行线程
        self.script_thread = ScriptThread(script, globals_dict)
        self.script_thread.output.connect(self.handle_script_output)
        self.script_thread.error.connect(self.handle_script_error)
        self.script_thread.finished.connect(self.on_script_finished)
        self.script_thread.start()
        
        self.log("开始执行脚本")
        
    def handle_script_output(self, output):
        self.terminal.moveCursor(self.terminal.textCursor().End)
        self.terminal.insertPlainText(output)
        self.terminal.moveCursor(self.terminal.textCursor().End)
        
    def handle_script_error(self, error):
        self.terminal.moveCursor(self.terminal.textCursor().End)
        self.terminal.insertPlainText(f"脚本错误: {error}")
        self.terminal.moveCursor(self.terminal.textCursor().End)
        
    def on_script_finished(self):
        self.log("脚本执行完成")
        
    def send_data_from_script(self, data):
        if isinstance(data, str):
            data = data.encode('utf-8')
            
        if self.serial_thread and self.serial_thread.isRunning():
            self.serial_thread.write_data(data)
        elif self.tcp_thread and self.tcp_thread.isRunning():
            self.tcp_thread.write_data(data)
            
    def add_plot_data(self, name, value):
        if name not in self.plot_data:
            self.plot_data[name] = deque(maxlen=self.max_data_points)
            # 添加新曲线
            color = pg.intColor(len(self.plot_curves) * 30, hues=len(self.plot_curves) + 1)
            curve = self.plot_widget.plot(pen=color, name=name)
            self.plot_curves[name] = curve
            
        self.plot_data[name].append(value)
        
        # 更新曲线
        x_data = list(range(len(self.plot_data[name])))
        self.plot_curves[name].setData(x_data, list(self.plot_data[name]))
        
    def load_command_templates(self):
        # 从文件加载命令模板
        try:
            if os.path.exists('command_templates.json'):
                with open('command_templates.json', 'r') as f:
                    self.command_templates = json.load(f)
            else:
                self.command_templates = []
                
            self.update_command_list()
        except Exception as e:
            self.log(f"加载命令模板失败: {str(e)}")
            self.command_templates = []
            
    def save_command_templates(self):
        # 保存命令模板到文件
        try:
            with open('command_templates.json', 'w') as f:
                json.dump(self.command_templates, f, indent=4)
        except Exception as e:
            self.log(f"保存命令模板失败: {str(e)}")
            
    def update_command_list(self):
        self.command_list.clear()
        for cmd in self.command_templates:
            self.command_list.addItem(cmd['name'])
            
    def add_command_template(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("添加命令模板")
        layout = QFormLayout(dialog)
        
        name_edit = QLineEdit()
        command_edit = QTextEdit()
        command_edit.setMaximumHeight(100)
        
        layout.addRow("名称:", name_edit)
        layout.addRow("命令:", command_edit)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)
        
        if dialog.exec_() == QDialog.Accepted:
            name = name_edit.text()
            command = command_edit.toPlainText()
            
            if name and command:
                self.command_templates.append({
                    'name': name,
                    'command': command
                })
                self.save_command_templates()
                self.update_command_list()
                self.log(f"已添加命令模板: {name}")
            else:
                QMessageBox.warning(self, "警告", "名称和命令不能为空")
                
    def edit_command_template(self):
        current_row = self.command_list.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "警告", "请先选择要编辑的命令模板")
            return
            
        dialog = QDialog(self)
        dialog.setWindowTitle("编辑命令模板")
        layout = QFormLayout(dialog)
        
        name_edit = QLineEdit(self.command_templates[current_row]['name'])
        command_edit = QTextEdit()
        command_edit.setPlainText(self.command_templates[current_row]['command'])
        command_edit.setMaximumHeight(100)
        
        layout.addRow("名称:", name_edit)
        layout.addRow("命令:", command_edit)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)
        
        if dialog.exec_() == QDialog.Accepted:
            name = name_edit.text()
            command = command_edit.toPlainText()
            
            if name and command:
                self.command_templates[current_row] = {
                    'name': name,
                    'command': command
                }
                self.save_command_templates()
                self.update_command_list()
                self.log(f"已更新命令模板: {name}")
            else:
                QMessageBox.warning(self, "警告", "名称和命令不能为空")
                
    def delete_command_template(self):
        current_row = self.command_list.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "警告", "请先选择要删除的命令模板")
            return
            
        name = self.command_templates[current_row]['name']
        reply = QMessageBox.question(self, "确认", f"确定要删除命令模板 '{name}' 吗?")
        
        if reply == QMessageBox.Yes:
            self.command_templates.pop(current_row)
            self.save_command_templates()
            self.update_command_list()
            self.log(f"已删除命令模板: {name}")
            
    def on_command_template_selected(self, item):
        # 找到选中的命令模板
        for cmd in self.command_templates:
            if cmd['name'] == item.text():
                self.send_text.setPlainText(cmd['command'])
                break
                
    def close_tab(self, index):
        if index > 0:  # 不允许关闭第一个标签页
            self.tab_widget.removeTab(index)
            
    def show_settings(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("设置")
        layout = QFormLayout(dialog)
        
        # 添加设置控件
        font_btn = QPushButton("选择终端字体")
        font_btn.clicked.connect(self.select_terminal_font)
        layout.addRow("终端字体:", font_btn)
        
        theme_combo = QComboBox()
        theme_combo.addItems(["浅色", "深色", "系统"])
        layout.addRow("主题:", theme_combo)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)
        
        if dialog.exec_() == QDialog.Accepted:
            # 保存设置
            self.log("设置已保存")
            
    def select_terminal_font(self):
        font, ok = QFontDialog.getFont(self.terminal.font(), self)
        if ok:
            self.terminal.setFont(font)
            self.log(f"终端字体已设置为: {font.family()}, {font.pointSize()}pt")
            
    def show_about(self):
        QMessageBox.about(self, "关于", 
                         "高级嵌入式开发系统工具\n\n"
                         "版本: 2.0\n"
                         "作者: Your Name\n"
                         "版权所有 © 2023 Your Company")
        
    def log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_widget.append(f"[{timestamp}] {message}")
        
    def load_protocol_parsers(self):
        # 加载内置协议解析器
        example_parser = ExampleProtocolParser()
        self.protocol_parsers[example_parser.name] = example_parser
        
        # 从plugins目录加载协议解析器
        plugins_dir = "protocol_parsers"
        if os.path.exists(plugins_dir):
            for filename in os.listdir(plugins_dir):
                if filename.endswith(".py") and filename != "__init__.py":
                    module_name = filename[:-3]
                    try:
                        spec = importlib.util.spec_from_file_location(module_name, os.path.join(plugins_dir, filename))
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)
                        
                        for name, obj in inspect.getmembers(module):
                            if (inspect.isclass(obj) and 
                                issubclass(obj, ProtocolParser) and 
                                obj != ProtocolParser):
                                parser = obj()
                                self.protocol_parsers[parser.name] = parser
                                self.log(f"已加载协议解析器: {parser.name}")
                                
                    except Exception as e:
                        self.log(f"加载协议解析器 {filename} 失败: {str(e)}")
                        
        # 更新协议选择框
        self.protocol_combo.clear()
        self.protocol_combo.addItems(list(self.protocol_parsers.keys()))
        
    def load_plugins(self):
        # 从plugins目录加载插件
        plugins_dir = "plugins"
        if os.path.exists(plugins_dir):
            for filename in os.listdir(plugins_dir):
                if filename.endswith(".py") and filename != "__init__.py":
                    module_name = filename[:-3]
                    try:
                        spec = importlib.util.spec_from_file_location(module_name, os.path.join(plugins_dir, filename))
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)
                        
                        for name, obj in inspect.getmembers(module):
                            if (inspect.isclass(obj) and 
                                issubclass(obj, PluginBase) and 
                                obj != PluginBase):
                                plugin = obj(self)
                                plugin.initialize()
                                self.plugins[plugin.name] = plugin
                                self.log(f"已加载插件: {plugin.name}")
                                
                    except Exception as e:
                        self.log(f"加载插件 {filename} 失败: {str(e)}")

# 应用程序入口
if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 设置应用程序样式
    app.setStyle("Fusion")
    
    # 创建并显示主窗口
    window = EmbeddedDevelopmentTool()
    window.show()
    
    sys.exit(app.exec_())