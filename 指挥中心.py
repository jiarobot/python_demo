import sys
import random
import json
import numpy as np
from datetime import datetime, timedelta
from PyQt5.QtCore import QSize, Qt, QTimer, QDateTime, pyqtSignal, QThread, QPointF, QRectF
from PyQt5.QtGui import (QFont, QColor, QKeySequence, QPalette, QIcon, QPixmap, QPainter, QPen, 
                         QBrush, QLinearGradient, QRadialGradient, QImage, QPolygonF)
from PyQt5.QtWidgets import (QApplication, QGraphicsRectItem, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QSplitter, QTabWidget, QLabel, QPushButton, QFrame, QGridLayout,
                             QGroupBox, QTextEdit, QListWidget, QListWidgetItem, QComboBox,
                             QSlider, QDial, QProgressBar, QToolBar, QStatusBar, QAction,
                             QMessageBox, QInputDialog, QFileDialog, QDockWidget, QTreeWidget,
                             QTreeWidgetItem, QTableWidget, QTableWidgetItem, QHeaderView,
                             QSpinBox, QDoubleSpinBox, QCheckBox, QRadioButton, QButtonGroup,
                             QStackedWidget, QSizePolicy, QGraphicsView, QGraphicsScene,
                             QGraphicsItem, QGraphicsEllipseItem, QGraphicsLineItem,
                             QGraphicsTextItem, QMenu, QSystemTrayIcon, QStyle, QLineEdit,
                             QToolBox, QFormLayout, QScrollArea, QProgressDialog, QShortcut)

# ==================== 自定义高级组件 ====================

class AdvancedRealTimeMonitor(QWidget):
    """高级实时监控面板，包含图表和更多指标"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.data_points = []
        self.max_data_points = 50
        self.setup_ui()
        self.setup_data_timers()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(5)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # 标题
        title = QLabel("高级实时监控系统")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #3498db; margin: 5px;")
        layout.addWidget(title)
        
        # 创建选项卡
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        layout.addWidget(self.tabs)
        
        # 系统状态选项卡
        sys_tab = QWidget()
        sys_layout = QVBoxLayout(sys_tab)
        self.setup_system_status(sys_layout)
        self.tabs.addTab(sys_tab, "系统状态")
        
        # 网络监控选项卡
        net_tab = QWidget()
        net_layout = QVBoxLayout(net_tab)
        self.setup_network_monitor(net_layout)
        self.tabs.addTab(net_tab, "网络监控")
        
        # 安全态势选项卡
        sec_tab = QWidget()
        sec_layout = QVBoxLayout(sec_tab)
        self.setup_security_status(sec_layout)
        self.tabs.addTab(sec_tab, "安全态势")
        
        self.setLayout(layout)
    
    def setup_system_status(self, layout):
        # 系统资源网格
        grid = QGridLayout()
        grid.setSpacing(10)
        
        # CPU使用率
        cpu_group = QGroupBox("CPU使用率")
        cpu_layout = QVBoxLayout(cpu_group)
        self.cpu_progress = QProgressBar()
        self.cpu_progress.setRange(0, 100)
        self.cpu_progress.setFormat("%v%")
        self.cpu_progress.setTextVisible(True)
        cpu_layout.addWidget(self.cpu_progress)
        grid.addWidget(cpu_group, 0, 0)
        
        # 内存使用
        mem_group = QGroupBox("内存使用")
        mem_layout = QVBoxLayout(mem_group)
        self.mem_progress = QProgressBar()
        self.mem_progress.setRange(0, 100)
        self.mem_progress.setFormat("%v%")
        self.mem_progress.setTextVisible(True)
        mem_layout.addWidget(self.mem_progress)
        grid.addWidget(mem_group, 0, 1)
        
        # 磁盘使用
        disk_group = QGroupBox("磁盘使用")
        disk_layout = QVBoxLayout(disk_group)
        self.disk_progress = QProgressBar()
        self.disk_progress.setRange(0, 100)
        self.disk_progress.setFormat("%v%")
        self.disk_progress.setTextVisible(True)
        disk_layout.addWidget(self.disk_progress)
        grid.addWidget(disk_group, 1, 0)
        
        # 温度监控
        temp_group = QGroupBox("系统温度")
        temp_layout = QVBoxLayout(temp_group)
        self.temp_label = QLabel("45°C")
        self.temp_label.setAlignment(Qt.AlignCenter)
        self.temp_label.setFont(QFont("Arial", 16, QFont.Bold))
        temp_layout.addWidget(self.temp_label)
        grid.addWidget(temp_group, 1, 1)
        
        layout.addLayout(grid)
        
        # 历史图表区域
        chart_group = QGroupBox("资源使用历史")
        chart_layout = QVBoxLayout(chart_group)
        self.chart_widget = QWidget()
        self.chart_widget.setMinimumHeight(150)
        chart_layout.addWidget(self.chart_widget)
        layout.addWidget(chart_group)
    
    def setup_network_monitor(self, layout):
        # 网络流量监控
        traffic_group = QGroupBox("网络流量")
        traffic_layout = QVBoxLayout(traffic_group)
        
        # 上传下载速度
        speed_layout = QHBoxLayout()
        upload_group = QGroupBox("上传速度")
        upload_layout = QVBoxLayout(upload_group)
        self.upload_speed = QLabel("0.0 Mbps")
        self.upload_speed.setAlignment(Qt.AlignCenter)
        self.upload_speed.setFont(QFont("Arial", 12))
        upload_layout.addWidget(self.upload_speed)
        
        download_group = QGroupBox("下载速度")
        download_layout = QVBoxLayout(download_group)
        self.download_speed = QLabel("0.0 Mbps")
        self.download_speed.setAlignment(Qt.AlignCenter)
        self.download_speed.setFont(QFont("Arial", 12))
        download_layout.addWidget(self.download_speed)
        
        speed_layout.addWidget(upload_group)
        speed_layout.addWidget(download_group)
        traffic_layout.addLayout(speed_layout)
        
        # 连接数
        conn_group = QGroupBox("活跃连接")
        conn_layout = QVBoxLayout(conn_group)
        self.conn_count = QLabel("0")
        self.conn_count.setAlignment(Qt.AlignCenter)
        self.conn_count.setFont(QFont("Arial", 16, QFont.Bold))
        conn_layout.addWidget(self.conn_count)
        traffic_layout.addWidget(conn_group)
        
        layout.addWidget(traffic_group)
        
        # 网络延迟
        latency_group = QGroupBox("网络延迟")
        latency_layout = QVBoxLayout(latency_group)
        self.latency_value = QLabel("0 ms")
        self.latency_value.setAlignment(Qt.AlignCenter)
        self.latency_value.setFont(QFont("Arial", 14))
        latency_layout.addWidget(self.latency_value)
        layout.addWidget(latency_group)
    
    def setup_security_status(self, layout):
        # 安全态势
        threat_group = QGroupBox("威胁级别")
        threat_layout = QVBoxLayout(threat_group)
        self.threat_level = QLabel("低")
        self.threat_level.setAlignment(Qt.AlignCenter)
        self.threat_level.setFont(QFont("Arial", 20, QFont.Bold))
        self.threat_level.setStyleSheet("color: green;")
        threat_layout.addWidget(self.threat_level)
        layout.addWidget(threat_group)
        
        # 安全事件
        events_group = QGroupBox("安全事件")
        events_layout = QVBoxLayout(events_group)
        self.events_list = QListWidget()
        events_layout.addWidget(self.events_list)
        layout.addWidget(events_group)
        
        # 防火墙状态
        firewall_group = QGroupBox("防火墙状态")
        firewall_layout = QVBoxLayout(firewall_group)
        self.firewall_status = QLabel("已启用")
        self.firewall_status.setAlignment(Qt.AlignCenter)
        self.firewall_status.setStyleSheet("color: green;")
        firewall_layout.addWidget(self.firewall_status)
        layout.addWidget(firewall_group)
    
    def setup_data_timers(self):
        # 系统数据更新定时器
        self.sys_timer = QTimer(self)
        self.sys_timer.timeout.connect(self.update_system_data)
        self.sys_timer.start(1000)
        
        # 网络数据更新定时器
        self.net_timer = QTimer(self)
        self.net_timer.timeout.connect(self.update_network_data)
        self.net_timer.start(2000)
        
        # 安全数据更新定时器
        self.sec_timer = QTimer(self)
        self.sec_timer.timeout.connect(self.update_security_data)
        self.sec_timer.start(5000)
    
    def update_system_data(self):
        # 更新系统数据
        cpu_usage = random.randint(10, 90)
        mem_usage = random.randint(20, 95)
        disk_usage = random.randint(30, 99)
        temp = random.randint(35, 75)
        
        self.cpu_progress.setValue(cpu_usage)
        self.mem_progress.setValue(mem_usage)
        self.disk_progress.setValue(disk_usage)
        self.temp_label.setText(f"{temp}°C")
        
        # 根据温度改变颜色
        if temp > 65:
            self.temp_label.setStyleSheet("color: red;")
        elif temp > 55:
            self.temp_label.setStyleSheet("color: orange;")
        else:
            self.temp_label.setStyleSheet("color: green;")
    
    def update_network_data(self):
        # 更新网络数据
        upload = random.uniform(0.1, 100.0)
        download = random.uniform(0.1, 500.0)
        connections = random.randint(50, 500)
        latency = random.randint(1, 100)
        
        self.upload_speed.setText(f"{upload:.1f} Mbps")
        self.download_speed.setText(f"{download:.1f} Mbps")
        self.conn_count.setText(f"{connections}")
        self.latency_value.setText(f"{latency} ms")
    
    def update_security_data(self):
        # 更新安全数据
        threats = ["低", "中", "高"]
        threat = random.choice(threats)
        
        self.threat_level.setText(threat)
        
        # 根据威胁级别改变颜色
        if threat == "高":
            self.threat_level.setStyleSheet("color: red;")
            # 添加安全事件
            events = ["检测到DDoS攻击", "未授权访问尝试", "可疑流量模式"]
            self.events_list.addItem(QDateTime.currentDateTime().toString("hh:mm:ss") + " - " + random.choice(events))
            # 限制事件列表长度
            if self.events_list.count() > 10:
                self.events_list.takeItem(0)
        elif threat == "中":
            self.threat_level.setStyleSheet("color: orange;")
        else:
            self.threat_level.setStyleSheet("color: green;")
        
        # 随机防火墙状态变化
        if random.random() < 0.1:  # 10%的概率改变状态
            status = random.choice(["已启用", "部分启用", "已禁用"])
            self.firewall_status.setText(status)
            if status == "已启用":
                self.firewall_status.setStyleSheet("color: green;")
            elif status == "部分启用":
                self.firewall_status.setStyleSheet("color: orange;")
            else:
                self.firewall_status.setStyleSheet("color: red;")
    
    def paintEvent(self, event):
        # 绘制简单的历史图表
        if not self.data_points:
            return
            
        painter = QPainter(self.chart_widget)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 绘制背景
        painter.fillRect(self.chart_widget.rect(), QColor(30, 30, 40))
        
        # 绘制网格
        painter.setPen(QPen(QColor(60, 60, 70), 1, Qt.DotLine))
        width = self.chart_widget.width()
        height = self.chart_widget.height()
        
        # 水平网格线
        for i in range(1, 5):
            y = i * height / 5
            painter.drawLine(0, y, width, y)
        
        # 垂直网格线
        for i in range(1, 10):
            x = i * width / 10
            painter.drawLine(x, 0, x, height)
        
        # 绘制数据线
        if len(self.data_points) > 1:
            painter.setPen(QPen(QColor(0, 200, 255), 2))
            
            # 计算数据点的位置
            points = []
            max_val = max(self.data_points)
            if max_val == 0:
                max_val = 1
                
            for i, value in enumerate(self.data_points):
                x = i * width / (len(self.data_points) - 1)
                y = height - (value / max_val) * height
                points.append(QPointF(x, y))
            
            # 绘制线条
            for i in range(len(points) - 1):
                painter.drawLine(points[i], points[i+1])
        
        painter.end()


class AdvancedMapWidget(QGraphicsView):
    """高级地图可视化组件，使用QGraphicsView"""
    unit_selected = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene()
        self.setScene(self.scene)
        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setup_ui()
        self.setup_map()
        
    def setup_ui(self):
        # 设置视图属性
        self.setMinimumSize(600, 400)
        self.setBackgroundBrush(QBrush(QColor(10, 20, 30)))
        
        # 缩放控制
        self.zoom_level = 1.0
        
    def setup_map(self):
        # 清除场景
        self.scene.clear()
        
        # 添加地图背景
        background = QGraphicsRectItem(0, 0, 1000, 1000)
        background.setBrush(QBrush(QColor(20, 30, 40)))
        self.scene.addItem(background)
        
        # 添加网格
        pen = QPen(QColor(40, 50, 60))
        for i in range(0, 1001, 50):
            self.scene.addLine(0, i, 1000, i, pen)
            self.scene.addLine(i, 0, i, 1000, pen)
        
        # 添加一些模拟单位
        unit_types = ["指挥中心", "雷达站", "导弹基地", "无人机", "护卫舰", "战斗机"]
        unit_icons = {
            "指挥中心": QColor(0, 255, 0),
            "雷达站": QColor(0, 200, 255),
            "导弹基地": QColor(255, 100, 0),
            "无人机": QColor(200, 200, 0),
            "护卫舰": QColor(0, 150, 255),
            "战斗机": QColor(255, 50, 50)
        }
        
        self.units = []
        for i in range(20):
            unit_type = random.choice(unit_types)
            x = random.randint(50, 950)
            y = random.randint(50, 950)
            
            # 创建单位图形
            unit = QGraphicsEllipseItem(x, y, 30, 30)
            unit.setBrush(QBrush(unit_icons[unit_type]))
            unit.setPen(QPen(Qt.black, 2))
            unit.setData(0, unit_type)  # 存储单位类型
            unit.setData(1, f"单位_{i+1}")  # 存储单位名称
            
            # 使单位可选
            unit.setFlag(QGraphicsItem.ItemIsSelectable)
            
            self.scene.addItem(unit)
            self.units.append(unit)
            
            # 添加单位标签
            label = QGraphicsTextItem(f"单位_{i+1}")
            label.setPos(x - 10, y + 35)
            label.setDefaultTextColor(Qt.white)
            label.setFont(QFont("Arial", 8))
            self.scene.addItem(label)
        
        # 添加一些连接线表示通信或关系
        for i in range(15):
            if len(self.units) < 2:
                continue
                
            unit1 = random.choice(self.units)
            unit2 = random.choice(self.units)
            
            if unit1 != unit2:
                line = QGraphicsLineItem(
                    unit1.rect().center().x() + unit1.x(),
                    unit1.rect().center().y() + unit1.y(),
                    unit2.rect().center().x() + unit2.x(),
                    unit2.rect().center().y() + unit2.y()
                )
                line.setPen(QPen(QColor(150, 150, 150), 1, Qt.DashLine))
                self.scene.addItem(line)
        
        # 设置场景范围
        self.scene.setSceneRect(0, 0, 1000, 1000)
        
    def wheelEvent(self, event):
        # 缩放控制
        zoom_factor = 1.2
        if event.angleDelta().y() < 0:
            zoom_factor = 1.0 / zoom_factor
            
        self.zoom_level *= zoom_factor
        self.scale(zoom_factor, zoom_factor)
        
    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            # 显示上下文菜单
            self.show_context_menu(event.pos())
        else:
            super().mousePressEvent(event)
            
    def show_context_menu(self, pos):
        # 获取场景坐标
        scene_pos = self.mapToScene(pos)
        
        # 查找点击的单位
        clicked_item = None
        for item in self.scene.items(scene_pos):
            if isinstance(item, QGraphicsEllipseItem):
                clicked_item = item
                break
                
        # 创建上下文菜单
        menu = QMenu(self)
        
        if clicked_item:
            unit_name = clicked_item.data(1)
            unit_type = clicked_item.data(0)
            
            menu.addAction(f"选择 {unit_name}")
            menu.addAction(f"查看 {unit_type} 详情")
            menu.addSeparator()
            menu.addAction("发送指令")
            menu.addAction("部署资源")
            menu.addSeparator()
            
            # 连接菜单动作
            action = menu.exec_(self.mapToGlobal(pos))
            if action:
                if "选择" in action.text():
                    self.unit_selected.emit(unit_name)
        else:
            menu.addAction("添加新单位")
            menu.addAction("扫描区域")
            menu.addSeparator()
            menu.addAction("放大")
            menu.addAction("缩小")
            menu.addAction("重置视图")
            
            # 连接菜单动作
            action = menu.exec_(self.mapToGlobal(pos))
            if action:
                if "重置视图" in action.text():
                    self.reset_view()
                    
    def reset_view(self):
        # 重置视图
        self.resetTransform()
        self.zoom_level = 1.0
        self.centerOn(500, 500)


class AdvancedCommunicationControl(QWidget):
    """高级通信控制面板，支持多频道、加密和文件传输"""
    message_received = pyqtSignal(str, str, bool)  # channel, message, encrypted
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.setup_connections()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(5)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # 标题
        title = QLabel("高级通信控制中心")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #3498db; margin: 5px;")
        layout.addWidget(title)
        
        # 频道和加密控制
        control_layout = QHBoxLayout()
        
        # 频道选择
        channel_layout = QVBoxLayout()
        channel_layout.addWidget(QLabel("频道:"))
        self.channel_combo = QComboBox()
        self.channel_combo.addItems(["指挥频道", "战术频道", "后勤频道", "紧急频道", "广播频道"])
        channel_layout.addWidget(self.channel_combo)
        control_layout.addLayout(channel_layout)
        
        # 加密选择
        encryption_layout = QVBoxLayout()
        encryption_layout.addWidget(QLabel("加密:"))
        self.encryption_combo = QComboBox()
        self.encryption_combo.addItems(["无加密", "AES-128", "AES-256", "RSA-2048", "量子加密"])
        encryption_layout.addWidget(self.encryption_combo)
        control_layout.addLayout(encryption_layout)
        
        # 优先级选择
        priority_layout = QVBoxLayout()
        priority_layout.addWidget(QLabel("优先级:"))
        self.priority_combo = QComboBox()
        self.priority_combo.addItems(["低", "普通", "高", "紧急"])
        priority_layout.addWidget(self.priority_combo)
        control_layout.addLayout(priority_layout)
        
        layout.addLayout(control_layout)
        
        # 消息显示区域
        display_group = QGroupBox("消息记录")
        display_layout = QVBoxLayout(display_group)
        self.message_display = QTextEdit()
        self.message_display.setReadOnly(True)
        display_layout.addWidget(self.message_display)
        layout.addWidget(display_group)
        
        # 消息发送区域
        send_group = QGroupBox("发送消息")
        send_layout = QVBoxLayout(send_group)
        
        # 消息输入
        self.message_input = QTextEdit()
        self.message_input.setMaximumHeight(80)
        send_layout.addWidget(self.message_input)
        
        # 发送按钮和文件传输
        button_layout = QHBoxLayout()
        
        self.send_btn = QPushButton("发送消息")
        self.send_btn.setIcon(self.style().standardIcon(QStyle.SP_MessageBoxInformation))
        button_layout.addWidget(self.send_btn)
        
        self.file_btn = QPushButton("发送文件")
        self.file_btn.setIcon(self.style().standardIcon(QStyle.SP_FileIcon))
        button_layout.addWidget(self.file_btn)
        
        self.voice_btn = QPushButton("语音通信")
        self.voice_btn.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        button_layout.addWidget(self.voice_btn)
        
        send_layout.addLayout(button_layout)
        layout.addWidget(send_group)
        
        # 连接状态
        status_layout = QHBoxLayout()
        self.connection_status = QLabel("连接状态: 已连接")
        self.connection_status.setStyleSheet("color: green;")
        status_layout.addWidget(self.connection_status)
        
        status_layout.addStretch()
        
        self.encryption_status = QLabel("加密状态: 无")
        status_layout.addWidget(self.encryption_status)
        
        layout.addLayout(status_layout)
        
        self.setLayout(layout)
    
    def setup_connections(self):
        # 连接按钮信号
        self.send_btn.clicked.connect(self.send_message)
        self.file_btn.clicked.connect(self.send_file)
        self.voice_btn.clicked.connect(self.toggle_voice)
        
        # 加密选择变化
        self.encryption_combo.currentTextChanged.connect(self.update_encryption_status)
        
        # 模拟接收消息的定时器
        self.receive_timer = QTimer(self)
        self.receive_timer.timeout.connect(self.simulate_receive_message)
        self.receive_timer.start(8000)  # 每8秒模拟接收一条消息
        
        # 模拟连接状态变化
        self.connection_timer = QTimer(self)
        self.connection_timer.timeout.connect(self.simulate_connection_change)
        self.connection_timer.start(30000)  # 每30秒模拟连接状态变化
    
    def send_message(self):
        message = self.message_input.toPlainText().strip()
        if message:
            channel = self.channel_combo.currentText()
            encryption = self.encryption_combo.currentText()
            priority = self.priority_combo.currentText()
            
            # 生成消息ID和时间戳
            message_id = f"MSG{random.randint(10000, 99999)}"
            timestamp = QDateTime.currentDateTime().toString("yyyy-MM-dd hh:mm:ss.zzz")
            
            # 格式化显示
            encrypted = encryption != "无加密"
            display_text = f"[{timestamp}] [{message_id}] [{priority}] {channel}"
            if encrypted:
                display_text += " [加密]"
            display_text += f" 发送: {message}"
            
            self.message_display.append(display_text)
            self.message_input.clear()
            
            # 发出信号，其他组件可以监听
            self.message_received.emit(channel, message, encrypted)
            
            # 模拟消息发送到网络
            print(f"消息已发送到 {channel} (加密: {encryption}, 优先级: {priority}): {message}")
    
    def send_file(self):
        # 打开文件选择对话框
        file_path, _ = QFileDialog.getOpenFileName(self, "选择要发送的文件", "", "所有文件 (*)")
        if file_path:
            # 模拟文件发送
            file_name = file_path.split("/")[-1]
            channel = self.channel_combo.currentText()
            encryption = self.encryption_combo.currentText()
            
            timestamp = QDateTime.currentDateTime().toString("yyyy-MM-dd hh:mm:ss")
            display_text = f"[{timestamp}] {channel} 发送文件: {file_name} (加密: {encryption})"
            self.message_display.append(display_text)
            
            print(f"文件已发送到 {channel}: {file_name}")
    
    def toggle_voice(self):
        # 切换语音通信状态
        if self.voice_btn.text() == "语音通信":
            self.voice_btn.setText("结束语音")
            self.voice_btn.setStyleSheet("background-color: red; color: white;")
            print("语音通信已启动")
        else:
            self.voice_btn.setText("语音通信")
            self.voice_btn.setStyleSheet("")
            print("语音通信已结束")
    
    def simulate_receive_message(self):
        # 模拟接收消息
        channels = ["指挥频道", "战术频道", "后勤频道", "紧急频道", "广播频道"]
        messages = [
            "所有单位报告状态",
            "侦察完成，区域安全",
            "需要额外资源",
            "检测到异常活动",
            "任务完成",
            "请求支援",
            "情报更新可用",
            "系统维护计划",
            "天气警报",
            "卫星图像已就绪"
        ]
        
        channel = random.choice(channels)
        message = random.choice(messages)
        encrypted = random.choice([True, False])
        priority = random.choice(["低", "普通", "高", "紧急"])
        
        # 生成消息ID和时间戳
        message_id = f"MSG{random.randint(10000, 99999)}"
        timestamp = QDateTime.currentDateTime().toString("yyyy-MM-dd hh:mm:ss.zzz")
        
        # 格式化显示
        display_text = f"[{timestamp}] [{message_id}] [{priority}] {channel}"
        if encrypted:
            display_text += " [加密]"
        display_text += f" 接收: {message}"
        
        self.message_display.append(display_text)
        
        # 发出信号，其他组件可以监听
        self.message_received.emit(channel, message, encrypted)
    
    def simulate_connection_change(self):
        # 模拟连接状态变化
        states = ["已连接", "连接中", "连接不稳定", "已断开"]
        state = random.choice(states)
        
        self.connection_status.setText(f"连接状态: {state}")
        
        if state == "已连接":
            self.connection_status.setStyleSheet("color: green;")
        elif state == "连接中":
            self.connection_status.setStyleSheet("color: orange;")
        else:
            self.connection_status.setStyleSheet("color: red;")
    
    def update_encryption_status(self, encryption):
        # 更新加密状态显示
        self.encryption_status.setText(f"加密状态: {encryption}")
        
        if encryption == "无加密":
            self.encryption_status.setStyleSheet("color: gray;")
        else:
            self.encryption_status.setStyleSheet("color: green;")


class AIAssistantWidget(QWidget):
    """人工智能辅助决策组件"""
    analysis_complete = pyqtSignal(str, str)  # analysis_type, result
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.setup_ai_models()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(5)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # 标题
        title = QLabel("人工智能辅助决策")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #3498db; margin: 5px;")
        layout.addWidget(title)
        
        # 分析类型选择
        analysis_layout = QHBoxLayout()
        analysis_layout.addWidget(QLabel("分析类型:"))
        self.analysis_combo = QComboBox()
        self.analysis_combo.addItems([
            "威胁评估", 
            "资源优化", 
            "路径规划", 
            "模式识别",
            "预测分析",
            "战略建议"
        ])
        analysis_layout.addWidget(self.analysis_combo)
        
        self.analyze_btn = QPushButton("开始分析")
        self.analyze_btn.setIcon(self.style().standardIcon(QStyle.SP_ComputerIcon))
        analysis_layout.addWidget(self.analyze_btn)
        
        layout.addLayout(analysis_layout)
        
        # 参数设置
        params_group = QGroupBox("分析参数")
        params_layout = QGridLayout(params_group)
        
        params_layout.addWidget(QLabel("数据范围:"), 0, 0)
        self.data_range = QComboBox()
        self.data_range.addItems(["最近1小时", "最近6小时", "最近24小时", "全部数据"])
        params_layout.addWidget(self.data_range, 0, 1)
        
        params_layout.addWidget(QLabel("置信阈值:"), 1, 0)
        self.confidence_threshold = QSlider(Qt.Horizontal)
        self.confidence_threshold.setRange(50, 100)
        self.confidence_threshold.setValue(80)
        params_layout.addWidget(self.confidence_threshold, 1, 1)
        
        params_layout.addWidget(QLabel("详细程度:"), 2, 0)
        self.detail_level = QComboBox()
        self.detail_level.addItems(["简要", "标准", "详细", "全面"])
        params_layout.addWidget(self.detail_level, 2, 1)
        
        layout.addWidget(params_group)
        
        # 分析结果
        result_group = QGroupBox("分析结果")
        result_layout = QVBoxLayout(result_group)
        self.result_display = QTextEdit()
        self.result_display.setReadOnly(True)
        result_layout.addWidget(self.result_display)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        result_layout.addWidget(self.progress_bar)
        
        layout.addWidget(result_group)
        
        # 操作按钮
        button_layout = QHBoxLayout()
        
        self.save_btn = QPushButton("保存结果")
        self.save_btn.setIcon(self.style().standardIcon(QStyle.SP_DialogSaveButton))
        button_layout.addWidget(self.save_btn)
        
        self.export_btn = QPushButton("导出报告")
        self.export_btn.setIcon(self.style().standardIcon(QStyle.SP_DriveHDIcon))
        button_layout.addWidget(self.export_btn)
        
        self.share_btn = QPushButton("共享分析")
        self.share_btn.setIcon(self.style().standardIcon(QStyle.SP_FileLinkIcon))
        button_layout.addWidget(self.share_btn)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
        # 连接信号
        self.analyze_btn.clicked.connect(self.start_analysis)
        self.save_btn.clicked.connect(self.save_results)
        self.export_btn.clicked.connect(self.export_report)
        self.share_btn.clicked.connect(self.share_analysis)
        self.analysis_complete.connect(self.on_analysis_complete)
    
    def setup_ai_models(self):
        # 模拟AI模型
        self.models = {
            "威胁评估": self.analyze_threats,
            "资源优化": self.optimize_resources,
            "路径规划": self.plan_paths,
            "模式识别": self.recognize_patterns,
            "预测分析": self.predict_trends,
            "战略建议": self.provide_strategy
        }
        
        self.analysis_thread = None
    
    def start_analysis(self):
        analysis_type = self.analysis_combo.currentText()
        data_range = self.data_range.currentText()
        confidence = self.confidence_threshold.value()
        detail_level = self.detail_level.currentText()
        
        # 显示进度条
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # 不确定进度
        
        # 更新结果显示
        self.result_display.clear()
        self.result_display.append(f"开始{analysis_type}分析...")
        self.result_display.append(f"参数: 数据范围={data_range}, 置信度={confidence}%, 详细程度={detail_level}")
        self.result_display.append("分析中，请稍候...")
        
        # 在后台线程中执行分析
        self.analysis_thread = AIAnalysisThread(
            analysis_type, 
            self.models[analysis_type],
            data_range,
            confidence,
            detail_level
        )
        self.analysis_thread.analysis_complete.connect(self.on_analysis_complete)
        self.analysis_thread.start()
    
    def on_analysis_complete(self, analysis_type, result):
        # 隐藏进度条
        self.progress_bar.setVisible(False)
        
        # 显示分析结果
        self.result_display.clear()
        self.result_display.append(f"{analysis_type}分析完成!")
        self.result_display.append("=" * 50)
        self.result_display.append(result)
    
    def save_results(self):
        # 保存分析结果
        file_path, _ = QFileDialog.getSaveFileName(self, "保存分析结果", "", "文本文件 (*.txt);;所有文件 (*)")
        if file_path:
            with open(file_path, 'w') as f:
                f.write(self.result_display.toPlainText())
            print(f"分析结果已保存到: {file_path}")
    
    def export_report(self):
        # 导出详细报告
        QMessageBox.information(self, "导出报告", "报告导出功能即将推出!")
    
    def share_analysis(self):
        # 共享分析结果
        QMessageBox.information(self, "共享分析", "分析共享功能即将推出!")
    
    # AI分析函数
    def analyze_threats(self, data_range, confidence, detail_level):
        # 模拟威胁评估分析
        time.sleep(3)  # 模拟处理时间
        
        threats = [
            "检测到潜在网络入侵尝试",
            "物理安全边界存在薄弱点",
            "社交媒体监控发现可疑活动",
            "供应链安全风险增加"
        ]
        
        recommendations = [
            "加强网络监控和入侵检测",
            "增加物理安全巡逻频率",
            "提高社交媒体监控级别",
            "审查供应链安全协议"
        ]
        
        result = "威胁评估分析结果:\n\n"
        result += "检测到的威胁:\n"
        for threat in threats:
            result += f"- {threat}\n"
        
        result += "\n建议措施:\n"
        for rec in recommendations:
            result += f"- {rec}\n"
        
        result += f"\n置信度: {confidence}%"
        return result
    
    def optimize_resources(self, data_range, confidence, detail_level):
        # 模拟资源优化分析
        time.sleep(2)
        
        result = "资源优化分析结果:\n\n"
        result += "当前资源分配:\n"
        result += "- CPU使用率: 65% (可优化)\n"
        result += "- 内存使用率: 80% (接近上限)\n"
        result += "- 网络带宽: 45% (良好)\n"
        result += "- 存储空间: 70% (注意监控)\n\n"
        
        result += "优化建议:\n"
        result += "- 重新分配计算任务以平衡CPU负载\n"
        result += "- 考虑增加内存或优化内存使用\n"
        result += "- 压缩存储数据以节省空间\n"
        result += "- 实施自动扩展策略应对峰值负载\n"
        
        return result
    
    def plan_paths(self, data_range, confidence, detail_level):
        # 模拟路径规划分析
        time.sleep(4)
        
        result = "路径规划分析结果:\n\n"
        result += "最优路径建议:\n"
        result += "- 从A点到B点: 路径1 (最短时间)\n"
        result += "- 从C点到D点: 路径3 (最低风险)\n"
        result += "- 从E点到F点: 路径2 (平衡方案)\n\n"
        
        result += "注意事项:\n"
        result += "- 路径1可能存在天气风险\n"
        result += "- 路径3需要额外资源支持\n"
        result += "- 所有路径都已考虑当前威胁情况\n"
        
        return result
    
    def recognize_patterns(self, data_range, confidence, detail_level):
        # 模拟模式识别分析
        time.sleep(5)
        
        result = "模式识别分析结果:\n\n"
        result += "检测到的模式:\n"
        result += "- 周期性网络活动峰值 (每6小时)\n"
        result += "- 异常登录模式 (非工作时间访问)\n"
        result += "- 数据访问模式变化 (可疑数据下载)\n"
        result += "- 通信模式异常 (加密通信增加)\n\n"
        
        result += "评估:\n"
        result += "检测到3个高风险模式，2个中等风险模式\n"
        result += "建议立即调查高风险模式\n"
        
        return result
    
    def predict_trends(self, data_range, confidence, detail_level):
        # 模拟预测分析
        time.sleep(3)
        
        result = "预测分析结果:\n\n"
        result += "未来24小时预测:\n"
        result += "- 网络流量: 增加15-20%\n"
        result += "- 系统负载: 保持稳定\n"
        result += "- 安全事件: 可能增加\n"
        result += "- 资源使用: 内存可能达到85%\n\n"
        
        result += "建议:\n"
        result += "- 提前分配额外资源应对流量增长\n"
        result += "- 加强安全监控\n"
        result += "- 准备应对可能的内存压力\n"
        
        return result
    
    def provide_strategy(self, data_range, confidence, detail_level):
        # 模拟战略建议
        time.sleep(4)
        
        result = "战略建议分析结果:\n\n"
        result += "当前态势评估:\n"
        result += "- 整体安全态势: 中等风险\n"
        result += "- 资源充足性: 良好\n"
        result += "- 响应能力: 高效\n"
        result += "- 威胁等级: 中等\n\n"
        
        result += "战略建议:\n"
        result += "- 采取防御性策略，加强监控\n"
        result += "- 分配20%资源作为应急储备\n"
        result += "- 启动第二阶段安全协议\n"
        result += "- 加强与盟友的信息共享\n"
        
        return result


class AIAnalysisThread(QThread):
    """AI分析线程"""
    analysis_complete = pyqtSignal(str, str)  # analysis_type, result
    
    def __init__(self, analysis_type, analysis_func, data_range, confidence, detail_level):
        super().__init__()
        self.analysis_type = analysis_type
        self.analysis_func = analysis_func
        self.data_range = data_range
        self.confidence = confidence
        self.detail_level = detail_level
    
    def run(self):
        # 执行分析函数
        result = self.analysis_func(self.data_range, self.confidence, self.detail_level)
        
        # 发出完成信号
        self.analysis_complete.emit(self.analysis_type, result)


class AdvancedEmergencyResponse(QWidget):
    """高级紧急响应系统，支持多协议和自动化响应"""
    emergency_triggered = pyqtSignal(str, str)  # emergency_type, protocol
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_protocols()
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(5)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # 标题
        title = QLabel("高级紧急响应系统")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: red; margin: 5px;")
        layout.addWidget(title)
        
        # 紧急按钮网格
        button_grid = QGridLayout()
        
        emergency_types = [
            ("安全漏洞", "red", "协议Alpha"),
            ("系统故障", "orange", "协议Beta"),
            ("网络攻击", "purple", "协议Gamma"),
            ("物理入侵", "darkred", "协议Delta"),
            ("数据泄露", "darkblue", "协议Epsilon"),
            ("通信中断", "brown", "协议Zeta"),
            ("电力故障", "darkgray", "协议Eta"),
            ("自然灾害", "teal", "协议Theta")
        ]
        
        self.emergency_buttons = []
        
        for i, (emergency, color, protocol) in enumerate(emergency_types):
            btn = QPushButton(emergency)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {color};
                    color: white;
                    font-weight: bold;
                    padding: 10px;
                    border-radius: 5px;
                }}
                QPushButton:hover {{
                    background-color: {self.lighten_color(color)};
                }}
            """)
            btn.setProperty("protocol", protocol)
            btn.clicked.connect(lambda _, e=emergency, p=protocol: self.trigger_emergency(e, p))
            button_grid.addWidget(btn, i // 2, i % 2)
            self.emergency_buttons.append(btn)
        
        layout.addLayout(button_grid)
        
        # 协议自定义区域
        protocol_group = QGroupBox("应急协议配置")
        protocol_layout = QVBoxLayout(protocol_group)
        
        # 协议选择
        protocol_select_layout = QHBoxLayout()
        protocol_select_layout.addWidget(QLabel("选择协议:"))
        self.protocol_combo = QComboBox()
        self.protocol_combo.addItems(["协议Alpha", "协议Beta", "协议Gamma", "协议Delta", 
                                    "协议Epsilon", "协议Zeta", "协议Eta", "协议Theta"])
        protocol_select_layout.addWidget(self.protocol_combo)
        
        self.load_protocol_btn = QPushButton("加载协议")
        self.load_protocol_btn.clicked.connect(self.load_protocol)
        protocol_select_layout.addWidget(self.load_protocol_btn)
        
        protocol_layout.addLayout(protocol_select_layout)
        
        # 协议详情
        self.protocol_details = QTextEdit()
        self.protocol_details.setReadOnly(True)
        protocol_layout.addWidget(self.protocol_details)
        
        # 协议操作按钮
        protocol_btn_layout = QHBoxLayout()
        
        self.execute_btn = QPushButton("执行协议")
        self.execute_btn.setStyleSheet("background-color: darkgreen; color: white; font-weight: bold;")
        self.execute_btn.clicked.connect(self.execute_protocol)
        protocol_btn_layout.addWidget(self.execute_btn)
        
        self.save_btn = QPushButton("保存协议")
        self.save_btn.clicked.connect(self.save_protocol)
        protocol_btn_layout.addWidget(self.save_btn)
        
        self.edit_btn = QPushButton("编辑协议")
        self.edit_btn.clicked.connect(self.edit_protocol)
        protocol_btn_layout.addWidget(self.edit_btn)
        
        protocol_layout.addLayout(protocol_btn_layout)
        layout.addWidget(protocol_group)
        
        # 状态显示
        status_group = QGroupBox("响应状态")
        status_layout = QVBoxLayout(status_group)
        self.status_display = QTextEdit()
        self.status_display.setReadOnly(True)
        status_layout.addWidget(self.status_display)
        layout.addWidget(status_group)
        
        self.setLayout(layout)
        
        # 加载默认协议
        self.load_protocol()
    
    def lighten_color(self, color_name):
        # 简单实现颜色变亮
        color_map = {
            "red": "#ff6666",
            "orange": "#ffb366",
            "purple": "#c266ff",
            "darkred": "#ff4d4d",
            "darkblue": "#4d4dff",
            "brown": "#cc9933",
            "darkgray": "#a6a6a6",
            "teal": "#33cccc"
        }
        return color_map.get(color_name, color_name)
    
    def setup_protocols(self):
        # 预定义协议
        self.protocols = {
            "协议Alpha": {
                "name": "协议Alpha",
                "description": "安全漏洞响应协议",
                "steps": [
                    "隔离受影响系统",
                    "启动取证分析",
                    "通知安全团队",
                    "应用紧急补丁",
                    "验证修复效果"
                ],
                "automated": True
            },
            "协议Beta": {
                "name": "协议Beta",
                "description": "系统故障响应协议",
                "steps": [
                    "切换到备份系统",
                    "诊断故障原因",
                    "恢复服务",
                    "测试系统稳定性",
                    "提交故障报告"
                ],
                "automated": False
            },
            "协议Gamma": {
                "name": "协议Gamma",
                "description": "网络攻击响应协议",
                "steps": [
                    "识别攻击类型",
                    "阻断攻击源",
                    "加强防御措施",
                    "监控异常活动",
                    "更新安全策略"
                ],
                "automated": True
            },
            "协议Delta": {
                "name": "协议Delta",
                "description": "物理入侵响应协议",
                "steps": [
                    "启动物理安全措施",
                    "通知安保人员",
                    "封锁相关区域",
                    "收集证据",
                    "提交安全报告"
                ],
                "automated": False
            },
            "协议Epsilon": {
                "name": "协议Epsilon",
                "description": "数据泄露响应协议",
                "steps": [
                    "确定泄露范围",
                    "阻止进一步泄露",
                    "通知受影响方",
                    "加强数据保护",
                    "审查访问控制"
                ],
                "automated": True
            },
            "协议Zeta": {
                "name": "协议Zeta",
                "description": "通信中断响应协议",
                "steps": [
                    "启用备用通信渠道",
                    "诊断中断原因",
                    "恢复主要通信",
                    "测试通信质量",
                    "更新通信预案"
                ],
                "automated": True
            },
            "协议Eta": {
                "name": "协议Eta",
                "description": "电力故障响应协议",
                "steps": [
                    "切换到备用电源",
                    "评估电力恢复时间",
                    "优先保障关键系统",
                    "监控电源状态",
                    "恢复正常供电后检查"
                ],
                "automated": True
            },
            "协议Theta": {
                "name": "协议Theta",
                "description": "自然灾害响应协议",
                "steps": [
                    "评估灾害影响",
                    "启动灾难恢复计划",
                    "确保人员安全",
                    "保护关键资产",
                    "协调外部支援"
                ],
                "automated": False
            }
        }
    
    def trigger_emergency(self, emergency_type, protocol):
        timestamp = QDateTime.currentDateTime().toString("yyyy-MM-dd hh:mm:ss")
        message = f"[{timestamp}] 紧急事件: {emergency_type}，启动协议: {protocol}"
        self.status_display.append(message)
        
        # 触发警报
        QApplication.beep()
        
        # 自动加载对应协议
        self.protocol_combo.setCurrentText(protocol)
        self.load_protocol()
        
        # 发出信号
        self.emergency_triggered.emit(emergency_type, protocol)
        
        # 如果是自动化协议，自动执行
        protocol_data = self.protocols.get(protocol, {})
        if protocol_data.get("automated", False):
            self.execute_protocol()
    
    def load_protocol(self):
        protocol_name = self.protocol_combo.currentText()
        protocol = self.protocols.get(protocol_name, {})
        
        # 显示协议详情
        details = f"协议名称: {protocol.get('name', '未知')}\n\n"
        details += f"描述: {protocol.get('description', '无描述')}\n\n"
        details += "步骤:\n"
        
        for i, step in enumerate(protocol.get('steps', []), 1):
            details += f"{i}. {step}\n"
        
        details += f"\n自动化: {'是' if protocol.get('automated', False) else '否'}"
        
        self.protocol_details.setPlainText(details)
    
    def execute_protocol(self):
        protocol_name = self.protocol_combo.currentText()
        protocol = self.protocols.get(protocol_name, {})
        
        timestamp = QDateTime.currentDateTime().toString("yyyy-MM-dd hh:mm:ss")
        self.status_display.append(f"[{timestamp}] 执行协议: {protocol_name}")
        
        # 模拟协议执行步骤
        for i, step in enumerate(protocol.get('steps', []), 1):
            self.status_display.append(f"步骤 {i}: {step}")
            # 这里可以添加实际的协议执行逻辑
            QApplication.processEvents()  # 更新UI
            QThread.msleep(500)  # 模拟执行时间
        
        self.status_display.append("协议执行完成!\n")
    
    def save_protocol(self):
        # 保存协议修改
        QMessageBox.information(self, "保存协议", "协议已保存!")
    
    def edit_protocol(self):
        # 编辑协议
        QMessageBox.information(self, "编辑协议", "协议编辑器即将推出!")


class AdvancedCommandCenter(QMainWindow):
    """高级指挥中心主窗口"""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("前沿最高指挥中心系统 - 高级版")
        self.setGeometry(100, 100, 1600, 1000)
        
        # 设置应用程序图标
        self.setWindowIcon(self.style().standardIcon(QStyle.SP_ComputerIcon))
        
        # 设置样式
        self.setup_style()
        
        # 初始化UI
        self.setup_ui()
        
        # 初始化数据线程
        self.setup_data_thread()
        
        # 初始化系统托盘
        self.setup_system_tray()
        
        # 初始化快捷键
        self.setup_shortcuts()
    
    def setup_style(self):
        # 设置应用程序样式
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2c3e50;
            }
            QWidget {
                color: #ecf0f1;
                font-family: Arial;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #34495e;
                border-radius: 5px;
                margin-top: 1ex;
                padding-top: 10px;
                background-color: #34495e;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #3498db;
            }
            QPushButton {
                background-color: #34495e;
                border: none;
                color: white;
                padding: 5px 10px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #4a6a8a;
            }
            QPushButton:pressed {
                background-color: #2c3e50;
            }
            QTextEdit, QListWidget {
                background-color: #2c3e50;
                border: 1px solid #34495e;
                border-radius: 3px;
                color: #ecf0f1;
            }
            QLabel {
                color: #ecf0f1;
            }
            QTabWidget::pane {
                border: 1px solid #34495e;
                background-color: #2c3e50;
            }
            QTabBar::tab {
                background-color: #34495e;
                color: #ecf0f1;
                padding: 8px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background-color: #3498db;
                color: white;
            }
            QComboBox {
                background-color: #2c3e50;
                color: #ecf0f1;
                border: 1px solid #34495e;
                padding: 5px;
                border-radius: 3px;
            }
            QComboBox QAbstractItemView {
                background-color: #2c3e50;
                color: #ecf0f1;
                selection-background-color: #3498db;
            }
            QProgressBar {
                border: 1px solid #34495e;
                border-radius: 3px;
                text-align: center;
                background-color: #2c3e50;
            }
            QProgressBar::chunk {
                background-color: #3498db;
            }
        """)
    
    def setup_ui(self):
        # 创建中央部件和主布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        # 左侧面板
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_panel.setMinimumWidth(350)
        
        # 高级实时监控
        monitor_group = QGroupBox("高级系统监控")
        monitor_layout = QVBoxLayout(monitor_group)
        self.monitor = AdvancedRealTimeMonitor()
        monitor_layout.addWidget(self.monitor)
        left_layout.addWidget(monitor_group)
        
        # 紧急响应
        emergency_group = QGroupBox("高级应急响应")
        emergency_layout = QVBoxLayout(emergency_group)
        self.emergency = AdvancedEmergencyResponse()
        emergency_layout.addWidget(self.emergency)
        left_layout.addWidget(emergency_group)
        
        # 中央区域 - 选项卡
        central_tabs = QTabWidget()
        central_tabs.setDocumentMode(True)
        
        # 地图选项卡
        map_tab = QWidget()
        map_layout = QVBoxLayout(map_tab)
        self.map_widget = AdvancedMapWidget()
        map_layout.addWidget(self.map_widget)
        central_tabs.addTab(map_tab, "战略地图")
        
        # 通信选项卡
        comm_tab = QWidget()
        comm_layout = QVBoxLayout(comm_tab)
        self.comm_widget = AdvancedCommunicationControl()
        comm_layout.addWidget(self.comm_widget)
        central_tabs.addTab(comm_tab, "高级通信")
        
        # AI辅助选项卡
        ai_tab = QWidget()
        ai_layout = QVBoxLayout(ai_tab)
        self.ai_widget = AIAssistantWidget()
        ai_layout.addWidget(self.ai_widget)
        central_tabs.addTab(ai_tab, "AI辅助决策")
        
        # 数据选项卡
        data_tab = QWidget()
        data_layout = QVBoxLayout(data_tab)
        data_display = QTextEdit()
        data_display.setReadOnly(True)
        data_display.setPlainText("高级数据监控将在这里显示...")
        data_layout.addWidget(data_display)
        central_tabs.addTab(data_tab, "数据监控")
        
        # 资源选项卡
        resource_tab = QWidget()
        resource_layout = QVBoxLayout(resource_tab)
        resource_display = QTextEdit()
        resource_display.setReadOnly(True)
        resource_display.setPlainText("高级资源管理将在这里显示...")
        resource_layout.addWidget(resource_display)
        central_tabs.addTab(resource_tab, "资源管理")
        
        # 右侧面板
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_panel.setMinimumWidth(350)
        
        # 系统状态
        status_group = QGroupBox("高级系统状态")
        status_layout = QVBoxLayout(status_group)
        
        # 使用表格显示状态
        status_table = QTableWidget()
        status_table.setColumnCount(2)
        status_table.setHorizontalHeaderLabels(["指标", "值"])
        status_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        status_table.setRowCount(6)
        
        status_data = [
            ("CPU使用率", "45%"),
            ("内存使用", "62%"),
            ("磁盘空间", "78%"),
            ("网络状态", "正常"),
            ("安全状态", "受保护"),
            ("系统温度", "45°C")
        ]
        
        for i, (name, value) in enumerate(status_data):
            status_table.setItem(i, 0, QTableWidgetItem(name))
            status_table.setItem(i, 1, QTableWidgetItem(value))
        
        status_table.setEditTriggers(QTableWidget.NoEditTriggers)
        status_layout.addWidget(status_table)
        right_layout.addWidget(status_group)
        
        # 活动日志
        log_group = QGroupBox("高级活动日志")
        log_layout = QVBoxLayout(log_group)
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        log_layout.addWidget(self.log_display)
        log_group.setLayout(log_layout)
        right_layout.addWidget(log_group)
        
        # 快速操作
        quick_group = QGroupBox("快速操作")
        quick_layout = QVBoxLayout(quick_group)
        
        quick_actions = [
            ("系统扫描", self.run_system_scan),
            ("备份数据", self.backup_data),
            ("更新系统", self.update_system),
            ("紧急锁定", self.emergency_lock)
        ]
        
        for action_name, action_func in quick_actions:
            btn = QPushButton(action_name)
            btn.clicked.connect(action_func)
            quick_layout.addWidget(btn)
        
        right_layout.addWidget(quick_group)
        
        # 添加到分割器
        splitter.addWidget(left_panel)
        splitter.addWidget(central_tabs)
        splitter.addWidget(right_panel)
        
        # 设置分割器初始大小
        splitter.setSizes([350, 900, 350])
        
        # 创建菜单栏
        self.setup_menu_bar()
        
        # 创建工具栏
        self.setup_tool_bar()
        
        # 创建状态栏
        self.setup_status_bar()
        
        # 创建停靠窗口
        self.setup_dock_widgets()
        
        # 连接信号
        self.comm_widget.message_received.connect(self.handle_message)
        self.emergency.emergency_triggered.connect(self.handle_emergency)
        self.map_widget.unit_selected.connect(self.handle_unit_selected)
    
    def setup_menu_bar(self):
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu("文件")
        
        new_action = QAction("新建项目", self)
        new_action.setShortcut("Ctrl+N")
        file_menu.addAction(new_action)
        
        open_action = QAction("打开项目", self)
        open_action.setShortcut("Ctrl+O")
        file_menu.addAction(open_action)
        
        save_action = QAction("保存项目", self)
        save_action.setShortcut("Ctrl+S")
        file_menu.addAction(save_action)
        
        file_menu.addSeparator()
        
        export_action = QAction("导出数据", self)
        file_menu.addAction(export_action)
        
        import_action = QAction("导入数据", self)
        file_menu.addAction(import_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("退出", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 编辑菜单
        edit_menu = menubar.addMenu("编辑")
        
        undo_action = QAction("撤销", self)
        undo_action.setShortcut("Ctrl+Z")
        edit_menu.addAction(undo_action)
        
        redo_action = QAction("重做", self)
        redo_action.setShortcut("Ctrl+Y")
        edit_menu.addAction(redo_action)
        
        edit_menu.addSeparator()
        
        pref_action = QAction("首选项", self)
        pref_action.setShortcut("Ctrl+P")
        edit_menu.addAction(pref_action)
        
        # 视图菜单
        view_menu = menubar.addMenu("视图")
        
        monitor_action = QAction("监控面板", self, checkable=True)
        monitor_action.setChecked(True)
        view_menu.addAction(monitor_action)
        
        map_action = QAction("地图视图", self, checkable=True)
        map_action.setChecked(True)
        view_menu.addAction(map_action)
        
        view_menu.addSeparator()
        
        fullscreen_action = QAction("全屏模式", self, checkable=True)
        fullscreen_action.setShortcut("F11")
        view_menu.addAction(fullscreen_action)
        
        # 工具菜单
        tools_menu = menubar.addMenu("工具")
        
        settings_action = QAction("系统设置", self)
        tools_menu.addAction(settings_action)
        
        analysis_action = QAction("数据分析", self)
        tools_menu.addAction(analysis_action)
        
        tools_menu.addSeparator()
        
        script_action = QAction("脚本编辑器", self)
        tools_menu.addAction(script_action)
        
        macro_action = QAction("宏管理器", self)
        tools_menu.addAction(macro_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu("帮助")
        
        docs_action = QAction("文档", self)
        help_menu.addAction(docs_action)
        
        about_action = QAction("关于", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def setup_tool_bar(self):
        # 主工具栏
        main_toolbar = QToolBar("主工具栏")
        main_toolbar.setIconSize(QSize(32, 32))
        self.addToolBar(main_toolbar)
        
        # 添加工具按钮
        new_btn = QAction(self.style().standardIcon(QStyle.SP_FileIcon), "新建", self)
        main_toolbar.addAction(new_btn)
        
        save_btn = QAction(self.style().standardIcon(QStyle.SP_DialogSaveButton), "保存", self)
        main_toolbar.addAction(save_btn)
        
        main_toolbar.addSeparator()
        
        monitor_btn = QAction(self.style().standardIcon(QStyle.SP_ComputerIcon), "监控", self)
        main_toolbar.addAction(monitor_btn)
        
        map_btn = QAction(self.style().standardIcon(QStyle.SP_DirHomeIcon), "地图", self)
        main_toolbar.addAction(map_btn)
        
        comm_btn = QAction(self.style().standardIcon(QStyle.SP_FileLinkIcon), "通信", self)
        main_toolbar.addAction(comm_btn)
        
        main_toolbar.addSeparator()
        
        emergency_btn = QAction(self.style().standardIcon(QStyle.SP_MessageBoxWarning), "应急", self)
        emergency_btn.triggered.connect(self.trigger_emergency_mode)
        main_toolbar.addAction(emergency_btn)
        
        # 辅助工具栏
        aux_toolbar = QToolBar("辅助工具栏")
        self.addToolBar(Qt.RightToolBarArea, aux_toolbar)
        
        # 添加辅助工具
        ai_btn = QAction(self.style().standardIcon(QStyle.SP_ComputerIcon), "AI辅助", self)
        aux_toolbar.addAction(ai_btn)
        
        scan_btn = QAction(self.style().standardIcon(QStyle.SP_BrowserReload), "扫描", self)
        aux_toolbar.addAction(scan_btn)
        
        report_btn = QAction(self.style().standardIcon(QStyle.SP_FileDialogDetailedView), "报告", self)
        aux_toolbar.addAction(report_btn)
    
    def setup_status_bar(self):
        statusbar = QStatusBar()
        self.setStatusBar(statusbar)
        
        # 添加状态标签
        self.status_label = QLabel("系统就绪")
        statusbar.addWidget(self.status_label)
        
        # 添加系统状态指示器
        self.system_status = QLabel("●")
        self.system_status.setStyleSheet("color: green; font-weight: bold;")
        statusbar.addWidget(self.system_status)
        
        # 添加时间标签
        self.time_label = QLabel()
        self.update_time()
        statusbar.addPermanentWidget(self.time_label)
        
        # 添加用户标签
        self.user_label = QLabel("用户: admin")
        statusbar.addPermanentWidget(self.user_label)
        
        # 更新时间定时器
        self.time_timer = QTimer(self)
        self.time_timer.timeout.connect(self.update_time)
        self.time_timer.start(1000)  # 每秒更新一次
    
    def setup_dock_widgets(self):
        # 创建停靠窗口 - 资源监控
        resource_dock = QDockWidget("资源监控", self)
        resource_widget = QWidget()
        resource_layout = QVBoxLayout(resource_widget)
        
        # 添加资源监控内容
        resource_table = QTableWidget()
        resource_table.setColumnCount(3)
        resource_table.setHorizontalHeaderLabels(["资源", "使用率", "状态"])
        resource_table.setRowCount(5)
        
        resource_data = [
            ("CPU", "45%", "正常"),
            ("内存", "62%", "正常"),
            ("磁盘", "78%", "警告"),
            ("网络", "35%", "正常"),
            ("GPU", "28%", "正常")
        ]
        
        for i, (name, usage, status) in enumerate(resource_data):
            resource_table.setItem(i, 0, QTableWidgetItem(name))
            resource_table.setItem(i, 1, QTableWidgetItem(usage))
            resource_table.setItem(i, 2, QTableWidgetItem(status))
        
        resource_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        resource_layout.addWidget(resource_table)
        
        resource_dock.setWidget(resource_widget)
        self.addDockWidget(Qt.LeftDockWidgetArea, resource_dock)
        
        # 创建停靠窗口 - 警报列表
        alert_dock = QDockWidget("警报列表", self)
        alert_widget = QWidget()
        alert_layout = QVBoxLayout(alert_widget)
        
        alert_list = QListWidget()
        alert_list.addItem("警告: 磁盘使用率超过75%")
        alert_list.addItem("信息: 系统备份已完成")
        alert_list.addItem("警告: 检测到异常网络活动")
        
        alert_layout.addWidget(alert_list)
        
        alert_dock.setWidget(alert_widget)
        self.addDockWidget(Qt.RightDockWidgetArea, alert_dock)
    
    def setup_data_thread(self):
        self.data_thread = DataThread()
        self.data_thread.data_updated.connect(self.handle_data_update)
        self.data_thread.start()
    
    def setup_system_tray(self):
        # 检查系统是否支持系统托盘
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
            
        # 创建系统托盘图标
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.style().standardIcon(QStyle.SP_ComputerIcon))
        
        # 创建托盘菜单
        tray_menu = QMenu(self)
        
        show_action = tray_menu.addAction("显示")
        show_action.triggered.connect(self.show)
        
        hide_action = tray_menu.addAction("隐藏")
        hide_action.triggered.connect(self.hide)
        
        tray_menu.addSeparator()
        
        quit_action = tray_menu.addAction("退出")
        quit_action.triggered.connect(self.close)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()
        
        # 托盘图标点击事件
        self.tray_icon.activated.connect(self.tray_icon_activated)
    
    def setup_shortcuts(self):
        # 添加快捷键
        fullscreen_shortcut = QShortcut(QKeySequence("F11"), self)
        fullscreen_shortcut.activated.connect(self.toggle_fullscreen)
        
        emergency_shortcut = QShortcut(QKeySequence("Ctrl+E"), self)
        emergency_shortcut.activated.connect(self.trigger_emergency_mode)
        
        screenshot_shortcut = QShortcut(QKeySequence("Ctrl+Shift+S"), self)
        screenshot_shortcut.activated.connect(self.take_screenshot)
    
    def update_time(self):
        current_time = QDateTime.currentDateTime().toString("yyyy-MM-dd hh:mm:ss")
        self.time_label.setText(current_time)
    
    def handle_data_update(self, data):
        # 处理数据更新
        log_entry = f"[数据更新] 温度: {data['temperature']:.1f}°C, 湿度: {data['humidity']:.1f}%"
        self.log_display.append(log_entry)
        
        # 限制日志长度
        if self.log_display.document().lineCount() > 1000:
            cursor = self.log_display.textCursor()
            cursor.movePosition(QTextCursor.Start)
            cursor.select(QTextCursor.LineUnderCursor)
            cursor.removeSelectedText()
            cursor.deleteChar()
    
    def handle_message(self, channel, message, encrypted):
        # 处理接收到的消息
        log_entry = f"[消息] {channel}: {message}"
        if encrypted:
            log_entry += " [加密]"
        self.log_display.append(log_entry)
        
        # 如果是紧急频道，特别处理
        if channel == "紧急频道":
            self.status_label.setText(f"紧急消息: {message}")
            self.status_label.setStyleSheet("color: red; font-weight: bold;")
            
            # 显示系统通知
            if hasattr(self, 'tray_icon'):
                self.tray_icon.showMessage("紧急消息", message, QSystemTrayIcon.Critical, 5000)
    
    def handle_emergency(self, emergency_type, protocol):
        # 处理紧急事件
        log_entry = f"[紧急] {emergency_type} - 启动协议: {protocol}"
        self.log_display.append(log_entry)
        
        # 更新状态栏
        self.status_label.setText(f"紧急事件: {emergency_type}")
        self.status_label.setStyleSheet("color: red; font-weight: bold;")
        self.system_status.setStyleSheet("color: red; font-weight: bold;")
        
        # 显示系统通知
        if hasattr(self, 'tray_icon'):
            self.tray_icon.showMessage("紧急事件", f"{emergency_type} - {protocol}", QSystemTrayIcon.Warning, 5000)
    
    def handle_unit_selected(self, unit_name):
        # 处理地图单位选择
        log_entry = f"[地图] 选择单位: {unit_name}"
        self.log_display.append(log_entry)
        
        # 显示单位信息
        self.status_label.setText(f"已选择: {unit_name}")
    
    def trigger_emergency_mode(self):
        # 触发紧急模式
        reply = QMessageBox.question(self, "确认紧急模式", 
                                    "确定要启动紧急模式吗？这将触发警报和应急协议。",
                                    QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            # 随机选择一个紧急事件
            emergencies = ["安全漏洞", "系统故障", "网络攻击", "物理入侵", "数据泄露"]
            emergency = random.choice(emergencies)
            
            self.emergency.trigger_emergency(emergency, "协议Alpha")
            self.setStyleSheet("QMainWindow { background-color: #500000; }")
            
            # 恢复正常模式的定时器
            QTimer.singleShot(10000, self.restore_normal_mode)
    
    def restore_normal_mode(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2c3e50;
            }
        """)
        self.status_label.setText("系统恢复正常模式")
        self.status_label.setStyleSheet("")
        self.system_status.setStyleSheet("color: green; font-weight: bold;")
    
    def show_about(self):
        QMessageBox.about(self, "关于指挥中心系统", 
                         "前沿最高指挥中心系统 - 高级版 v3.0\n\n"
                         "高级指挥与控制平台\n"
                         "集成AI辅助决策和高级可视化\n"
                         "版权所有 © 2023 安全技术部门")
    
    def tray_icon_activated(self, reason):
        # 系统托盘图标激活事件
        if reason == QSystemTrayIcon.DoubleClick:
            if self.isVisible():
                self.hide()
            else:
                self.show()
                self.activateWindow()
    
    def toggle_fullscreen(self):
        # 切换全屏模式
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()
    
    def take_screenshot(self):
        # 截取屏幕截图
        screenshot = QApplication.primaryScreen().grabWindow(0)
        
        # 保存截图
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存截图", 
            f"screenshot_{QDateTime.currentDateTime().toString('yyyyMMdd_hhmmss')}.png",
            "PNG图像 (*.png);;所有文件 (*)"
        )
        
        if file_path:
            screenshot.save(file_path)
            self.log_display.append(f"[系统] 截图已保存: {file_path}")
    
    def run_system_scan(self):
        # 运行系统扫描
        self.log_display.append("[系统] 开始系统扫描...")
        
        # 模拟扫描过程
        progress = QProgressDialog("正在扫描系统...", "取消", 0, 100, self)
        progress.setWindowModality(Qt.WindowModal)
        
        for i in range(101):
            progress.setValue(i)
            QApplication.processEvents()
            if progress.wasCanceled():
                break
            QThread.msleep(50)
        
        progress.setValue(100)
        self.log_display.append("[系统] 系统扫描完成")
        
        # 显示扫描结果
        QMessageBox.information(self, "扫描完成", "系统扫描完成，未发现严重问题。")
    
    def backup_data(self):
        # 备份数据
        self.log_display.append("[系统] 开始数据备份...")
        
        # 模拟备份过程
        progress = QProgressDialog("正在备份数据...", "取消", 0, 100, self)
        progress.setWindowModality(Qt.WindowModal)
        
        for i in range(101):
            progress.setValue(i)
            QApplication.processEvents()
            if progress.wasCanceled():
                break
            QThread.msleep(30)
        
        progress.setValue(100)
        self.log_display.append("[系统] 数据备份完成")
        
        # 显示备份结果
        QMessageBox.information(self, "备份完成", "数据备份已成功完成。")
    
    def update_system(self):
        # 更新系统
        reply = QMessageBox.question(self, "确认更新", 
                                    "确定要检查系统更新吗？",
                                    QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.log_display.append("[系统] 检查系统更新...")
            
            # 模拟更新检查
            QTimer.singleShot(2000, lambda: self.log_display.append("[系统] 系统已是最新版本"))
    
    def emergency_lock(self):
        # 紧急锁定系统
        reply = QMessageBox.question(self, "确认锁定", 
                                    "确定要紧急锁定系统吗？这将终止所有非关键进程。",
                                    QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.log_display.append("[系统] 紧急锁定系统...")
            
            # 模拟锁定过程
            progress = QProgressDialog("正在锁定系统...", "取消", 0, 100, self)
            progress.setWindowModality(Qt.WindowModal)
            
            for i in range(101):
                progress.setValue(i)
                QApplication.processEvents()
                if progress.wasCanceled():
                    break
                QThread.msleep(20)
            
            progress.setValue(100)
            self.log_display.append("[系统] 系统已锁定")
            
            # 显示锁定结果
            QMessageBox.information(self, "锁定完成", "系统已紧急锁定。")
    
    def closeEvent(self, event):
        # 确认退出
        reply = QMessageBox.question(self, "确认退出", 
                                    "确定要退出指挥中心系统吗？",
                                    QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            # 停止数据线程
            self.data_thread.stop()
            self.data_thread.wait()
            event.accept()
        else:
            event.ignore()


# ==================== 数据线程 ====================

class DataThread(QThread):
    """数据更新线程"""
    data_updated = pyqtSignal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.running = True
        
    def run(self):
        while self.running:
            # 模拟数据收集
            data = {
                "temperature": random.uniform(10, 40),
                "pressure": random.uniform(980, 1040),
                "humidity": random.uniform(20, 95),
                "network_traffic": random.uniform(100, 1000),
            }
            self.data_updated.emit(data)
            self.msleep(3000)  # 每3秒更新一次
    
    def stop(self):
        self.running = False
        self.wait()


# ==================== 主程序入口 ====================

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 设置应用程序信息
    app.setApplicationName("前沿最高指挥中心系统 - 高级版")
    app.setApplicationVersion("3.0")
    app.setApplicationDisplayName("指挥中心系统")
    
    # 创建并显示主窗口
    window = AdvancedCommandCenter()
    window.show()
    
    sys.exit(app.exec_())