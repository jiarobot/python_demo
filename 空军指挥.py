import sys
import math
import random
from datetime import datetime, timedelta
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QSplitter, QTabWidget, QTableWidget,
                             QTableWidgetItem, QTreeWidget, QTreeWidgetItem,
                             QGroupBox, QLabel, QPushButton, QTextEdit,
                             QComboBox, QSpinBox, QDoubleSpinBox, QCheckBox,
                             QProgressBar, QMessageBox, QGraphicsView, 
                             QGraphicsScene, QGraphicsItem, QGraphicsEllipseItem,
                             QGraphicsLineItem, QMenu, QAction, QDialog, 
                             QDialogButtonBox, QFormLayout, QLineEdit)
from PyQt5.QtCore import Qt, QTimer, QPointF, QRectF, pyqtSignal, QThread, pyqtSlot
from PyQt5.QtGui import QFont, QColor, QPen, QBrush, QPainter, QIcon, QPainterPath
import numpy as np
from collections import deque
import json


# 数据模型类
class Aircraft:
    """战机数据模型"""
    def __init__(self, id, callsign, type, x, y, altitude, speed, heading, status="正常"):
        self.id = id
        self.callsign = callsign
        self.type = type
        self.x = x  # 经度坐标
        self.y = y  # 纬度坐标
        self.altitude = altitude  # 高度（米）
        self.speed = speed  # 速度（公里/小时）
        self.heading = heading  # 航向（度）
        self.status = status
        self.fuel = 100  # 燃油百分比
        self.ammo = 100  # 弹药百分比
        self.last_update = datetime.now()
        self.trajectory = deque(maxlen=50)  # 轨迹记录
        self.trajectory.append((x, y))
        
    def update_position(self, x, y, altitude, speed, heading):
        """更新战机位置和状态"""
        self.x = x
        self.y = y
        self.altitude = altitude
        self.speed = speed
        self.heading = heading
        self.trajectory.append((x, y))
        self.last_update = datetime.now()
        
    def update_status(self, status, fuel=None, ammo=None):
        """更新战机状态"""
        self.status = status
        if fuel is not None:
            self.fuel = max(0, min(100, fuel))
        if ammo is not None:
            self.ammo = max(0, min(100, ammo))
            
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'callsign': self.callsign,
            'type': self.type,
            'x': self.x,
            'y': self.y,
            'altitude': self.altitude,
            'speed': self.speed,
            'heading': self.heading,
            'status': self.status,
            'fuel': self.fuel,
            'ammo': self.ammo,
            'last_update': self.last_update.isoformat()
        }


class Threat:
    """威胁目标数据模型"""
    def __init__(self, id, type, x, y, range, threat_level):
        self.id = id
        self.type = type  # 导弹、雷达、防空等
        self.x = x
        self.y = y
        self.range = range  # 威胁范围
        self.threat_level = threat_level  # 威胁等级 1-10


class Mission:
    """任务数据模型"""
    def __init__(self, id, name, aircraft_ids, waypoints, objective, status="规划中"):
        self.id = id
        self.name = name
        self.aircraft_ids = aircraft_ids  # 参与任务的战机ID列表
        self.waypoints = waypoints  # 航路点列表 [(x1,y1), (x2,y2), ...]
        self.objective = objective  # 任务目标
        self.status = status
        self.start_time = None
        self.end_time = None


# 数据管理器
class DataManager:
    """数据管理器，负责管理所有系统数据"""
    def __init__(self):
        self.aircrafts = {}  # 战机字典 {id: Aircraft对象}
        self.threats = {}    # 威胁字典 {id: Threat对象}
        self.missions = {}   # 任务字典 {id: Mission对象}
        self.next_aircraft_id = 1
        self.next_threat_id = 1
        self.next_mission_id = 1
        
    def add_aircraft(self, callsign, type, x, y, altitude, speed, heading):
        """添加新战机"""
        aircraft_id = self.next_aircraft_id
        self.aircrafts[aircraft_id] = Aircraft(aircraft_id, callsign, type, x, y, altitude, speed, heading)
        self.next_aircraft_id += 1
        return aircraft_id
        
    def add_threat(self, type, x, y, range, threat_level):
        """添加新威胁"""
        threat_id = self.next_threat_id
        self.threats[threat_id] = Threat(threat_id, type, x, y, range, threat_level)
        self.next_threat_id += 1
        return threat_id
        
    def add_mission(self, name, aircraft_ids, waypoints, objective):
        """添加新任务"""
        mission_id = self.next_mission_id
        self.missions[mission_id] = Mission(mission_id, name, aircraft_ids, waypoints, objective)
        self.next_mission_id += 1
        return mission_id
        
    def get_aircraft_by_id(self, aircraft_id):
        """根据ID获取战机"""
        return self.aircrafts.get(aircraft_id)
        
    def get_threat_by_id(self, threat_id):
        """根据ID获取威胁"""
        return self.threats.get(threat_id)
        
    def get_mission_by_id(self, mission_id):
        """根据ID获取任务"""
        return self.missions.get(mission_id)
        
    def remove_aircraft(self, aircraft_id):
        """移除战机"""
        if aircraft_id in self.aircrafts:
            del self.aircrafts[aircraft_id]
            
    def remove_threat(self, threat_id):
        """移除威胁"""
        if threat_id in self.threats:
            del self.threats[threat_id]
            
    def remove_mission(self, mission_id):
        """移除任务"""
        if mission_id in self.missions:
            del self.missions[mission_id]
            
    def get_all_aircrafts(self):
        """获取所有战机"""
        return list(self.aircrafts.values())
        
    def get_all_threats(self):
        """获取所有威胁"""
        return list(self.threats.values())
        
    def get_all_missions(self):
        """获取所有任务"""
        return list(self.missions.values())


# 战术分析引擎
class TacticalAnalyzer:
    """战术分析引擎，负责计算战术数据"""
    
    @staticmethod
    def calculate_distance(x1, y1, x2, y2):
        """计算两点之间的距离"""
        return math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
        
    @staticmethod
    def calculate_intercept_point(interceptor_x, interceptor_y, interceptor_speed, 
                                 target_x, target_y, target_speed, target_heading):
        """计算拦截点"""
        # 简化拦截点计算（实际应用需要更复杂的算法）
        dx = target_x - interceptor_x
        dy = target_y - interceptor_y
        distance = TacticalAnalyzer.calculate_distance(interceptor_x, interceptor_y, target_x, target_y)
        
        if distance == 0:
            return target_x, target_y
            
        # 计算目标移动方向
        target_dx = math.cos(math.radians(target_heading)) * target_speed
        target_dy = math.sin(math.radians(target_heading)) * target_speed
        
        # 简化拦截时间计算
        time_to_intercept = distance / (interceptor_speed + target_speed) if interceptor_speed + target_speed > 0 else 0
        
        # 预测拦截点
        intercept_x = target_x + target_dx * time_to_intercept
        intercept_y = target_y + target_dy * time_to_intercept
        
        return intercept_x, intercept_y
        
    @staticmethod
    def assess_threat_level(aircraft, threat):
        """评估威胁等级"""
        distance = TacticalAnalyzer.calculate_distance(aircraft.x, aircraft.y, threat.x, threat.y)
        
        # 根据距离和威胁类型计算威胁等级
        if distance > threat.range:
            return 0  # 无威胁
            
        threat_factor = threat.threat_level / 10.0
        distance_factor = 1.0 - (distance / threat.range)
        
        return threat_factor * distance_factor * 10  # 返回0-10的威胁等级


# 地图视图组件
class BattlefieldView(QGraphicsView):
    """战场地图视图"""
    aircraft_selected = pyqtSignal(int)  # 战机选择信号
    threat_selected = pyqtSignal(int)    # 威胁选择信号
    
    def __init__(self, data_manager):
        super().__init__()
        self.data_manager = data_manager
        self.scene = QGraphicsScene()
        self.setScene(self.scene)
        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.RubberBandDrag)
        
        # 视图设置
        self.setMinimumSize(600, 400)
        self.scale_factor = 1.0
        self.center_point = QPointF(0, 0)
        
        # 图形项字典
        self.aircraft_items = {}  # {aircraft_id: QGraphicsItem}
        self.threat_items = {}    # {threat_id: QGraphicsItem}
        self.trajectory_items = {} # {aircraft_id: QGraphicsItem}
        self.waypoint_items = {}  # {mission_id: [QGraphicsItem]}
        
        # 初始化场景
        self.init_scene()
        
        # 定时刷新
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_display)
        self.refresh_timer.start(1000)  # 每秒刷新一次
        
    def init_scene(self):
        """初始化场景"""
        self.scene.clear()
        self.aircraft_items.clear()
        self.threat_items.clear()
        self.trajectory_items.clear()
        self.waypoint_items.clear()
        
        # 设置场景范围
        self.scene.setSceneRect(-1000, -1000, 2000, 2000)
        
        # 绘制网格
        self.draw_grid()
        
        # 添加所有现有对象
        for threat in self.data_manager.get_all_threats():
            self.add_threat_item(threat)
            
        for aircraft in self.data_manager.get_all_aircrafts():
            self.add_aircraft_item(aircraft)
            
        self.centerOn(self.center_point)
        
    def draw_grid(self):
        """绘制网格"""
        pen = QPen(QColor(200, 200, 200, 100))
        for i in range(-1000, 1001, 100):
            # 水平线
            self.scene.addLine(-1000, i, 1000, i, pen)
            # 垂直线
            self.scene.addLine(i, -1000, i, 1000, pen)
            
    def add_aircraft_item(self, aircraft):
        """添加战机图形项"""
        # 战机图标
        aircraft_item = QGraphicsEllipseItem(-10, -10, 20, 20)
        
        # 根据状态设置颜色
        if aircraft.status == "正常":
            aircraft_item.setBrush(QBrush(QColor(0, 255, 0, 200)))  # 绿色
        elif aircraft.status == "警告":
            aircraft_item.setBrush(QBrush(QColor(255, 255, 0, 200)))  # 黄色
        elif aircraft.status == "危险":
            aircraft_item.setBrush(QBrush(QColor(255, 0, 0, 200)))  # 红色
        else:
            aircraft_item.setBrush(QBrush(QColor(100, 100, 100, 200)))  # 灰色
            
        aircraft_item.setPos(aircraft.x, aircraft.y)
        aircraft_item.setData(0, aircraft.id)  # 存储ID
        aircraft_item.setFlag(QGraphicsItem.ItemIsSelectable)
        
        # 航向指示器
        heading_line = QGraphicsLineItem(0, 0, 0, -30, aircraft_item)
        heading_line.setPen(QPen(QColor(255, 255, 255), 2))
        
        # 设置航向
        aircraft_item.setRotation(aircraft.heading)
        
        self.scene.addItem(aircraft_item)
        self.aircraft_items[aircraft.id] = aircraft_item
        
        # 呼号标签
        label_item = self.scene.addText(aircraft.callsign)
        label_item.setPos(aircraft.x + 15, aircraft.y - 10)
        label_item.setData(0, aircraft.id)
        
        # 轨迹线
        self.update_trajectory(aircraft.id)
        
    def add_threat_item(self, threat):
        """添加威胁图形项"""
        # 威胁范围圆
        range_circle = QGraphicsEllipseItem(-threat.range, -threat.range, 
                                           threat.range*2, threat.range*2)
        
        # 根据威胁等级设置透明度
        alpha = min(100 + threat.threat_level * 15, 255)
        range_circle.setBrush(QBrush(QColor(255, 0, 0, alpha // 4)))
        range_circle.setPen(QPen(QColor(255, 0, 0, alpha), 2))
        range_circle.setPos(threat.x, threat.y)
        range_circle.setData(0, threat.id)
        range_circle.setFlag(QGraphicsItem.ItemIsSelectable)
        
        # 威胁中心点
        center_item = QGraphicsEllipseItem(-5, -5, 10, 10, range_circle)
        center_item.setBrush(QBrush(QColor(255, 0, 0)))
        
        # 威胁类型标签
        label_item = self.scene.addText(threat.type)
        label_item.setPos(threat.x + threat.range + 5, threat.y - 10)
        label_item.setData(0, threat.id)
        
        self.scene.addItem(range_circle)
        self.threat_items[threat.id] = range_circle
        
    def update_trajectory(self, aircraft_id):
        """更新战机轨迹"""
        aircraft = self.data_manager.get_aircraft_by_id(aircraft_id)
        if not aircraft or len(aircraft.trajectory) < 2:
            return
            
        # 移除旧轨迹
        if aircraft_id in self.trajectory_items:
            self.scene.removeItem(self.trajectory_items[aircraft_id])
            
        # 创建新轨迹路径
        path = QPainterPath()
        points = list(aircraft.trajectory)
        
        if points:
            path.moveTo(points[0][0], points[0][1])
            for point in points[1:]:
                path.lineTo(point[0], point[1])
                
            trajectory_item = self.scene.addPath(path, QPen(QColor(0, 255, 255, 150), 1))
            self.trajectory_items[aircraft_id] = trajectory_item
            
    def refresh_display(self):
        """刷新显示"""
        # 更新所有战机位置
        for aircraft in self.data_manager.get_all_aircrafts():
            if aircraft.id in self.aircraft_items:
                item = self.aircraft_items[aircraft.id]
                item.setPos(aircraft.x, aircraft.y)
                item.setRotation(aircraft.heading)
                
                # 更新状态颜色
                if aircraft.status == "正常":
                    item.setBrush(QBrush(QColor(0, 255, 0, 200)))
                elif aircraft.status == "警告":
                    item.setBrush(QBrush(QColor(255, 255, 0, 200)))
                elif aircraft.status == "危险":
                    item.setBrush(QBrush(QColor(255, 0, 0, 200)))
                    
                # 更新轨迹
                self.update_trajectory(aircraft.id)
                
    def wheelEvent(self, event):
        """鼠标滚轮缩放"""
        factor = 1.2
        if event.angleDelta().y() < 0:
            factor = 1.0 / factor
            
        self.scale(factor, factor)
        self.scale_factor *= factor
        
    def mousePressEvent(self, event):
        """鼠标点击事件"""
        if event.button() == Qt.RightButton:
            # 右键菜单
            self.show_context_menu(event.pos())
        else:
            super().mousePressEvent(event)
            
    def show_context_menu(self, pos):
        """显示右键菜单"""
        # 获取点击的图形项
        item = self.itemAt(pos)
        if not item:
            return
            
        menu = QMenu(self)
        
        # 根据图形项类型添加菜单项
        item_id = item.data(0)
        if item_id in self.aircraft_items:
            # 战机菜单
            aircraft = self.data_manager.get_aircraft_by_id(item_id)
            if aircraft:
                aircraft_action = QAction(f"选择战机 {aircraft.callsign}", self)
                aircraft_action.triggered.connect(lambda: self.aircraft_selected.emit(item_id))
                menu.addAction(aircraft_action)
                
                info_action = QAction("查看详细信息", self)
                info_action.triggered.connect(lambda: self.show_aircraft_info(item_id))
                menu.addAction(info_action)
                
        elif item_id in self.threat_items:
            # 威胁菜单
            threat = self.data_manager.get_threat_by_id(item_id)
            if threat:
                threat_action = QAction(f"选择威胁 {threat.type}", self)
                threat_action.triggered.connect(lambda: self.threat_selected.emit(item_id))
                menu.addAction(threat_action)
                
        menu.exec_(self.mapToGlobal(pos))
        
    def show_aircraft_info(self, aircraft_id):
        """显示战机信息对话框"""
        aircraft = self.data_manager.get_aircraft_by_id(aircraft_id)
        if aircraft:
            info_dialog = QDialog(self)
            info_dialog.setWindowTitle(f"战机信息 - {aircraft.callsign}")
            info_dialog.setModal(True)
            
            layout = QFormLayout()
            
            layout.addRow("呼号:", QLabel(aircraft.callsign))
            layout.addRow("类型:", QLabel(aircraft.type))
            layout.addRow("位置:", QLabel(f"({aircraft.x:.2f}, {aircraft.y:.2f})"))
            layout.addRow("高度:", QLabel(f"{aircraft.altitude} 米"))
            layout.addRow("速度:", QLabel(f"{aircraft.speed} 公里/小时"))
            layout.addRow("航向:", QLabel(f"{aircraft.heading}°"))
            layout.addRow("状态:", QLabel(aircraft.status))
            layout.addRow("燃油:", QLabel(f"{aircraft.fuel}%"))
            layout.addRow("弹药:", QLabel(f"{aircraft.ammo}%"))
            
            buttons = QDialogButtonBox(QDialogButtonBox.Ok)
            buttons.accepted.connect(info_dialog.accept)
            layout.addRow(buttons)
            
            info_dialog.setLayout(layout)
            info_dialog.exec_()


# 战机管理面板
class AircraftPanel(QWidget):
    """战机管理面板"""
    def __init__(self, data_manager):
        super().__init__()
        self.data_manager = data_manager
        self.init_ui()
        
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout()
        
        # 标题
        title = QLabel("战机管理")
        title.setFont(QFont("Arial", 14, QFont.Bold))
        layout.addWidget(title)
        
        # 战机列表表格
        self.aircraft_table = QTableWidget()
        self.aircraft_table.setColumnCount(8)
        self.aircraft_table.setHorizontalHeaderLabels(["ID", "呼号", "类型", "位置", "状态", "燃油", "弹药", "操作"])
        self.aircraft_table.setSortingEnabled(True)
        layout.addWidget(self.aircraft_table)
        
        # 控制按钮
        button_layout = QHBoxLayout()
        add_btn = QPushButton("添加战机")
        remove_btn = QPushButton("移除战机")
        refresh_btn = QPushButton("刷新")
        
        add_btn.clicked.connect(self.add_aircraft)
        remove_btn.clicked.connect(self.remove_aircraft)
        refresh_btn.clicked.connect(self.refresh_table)
        
        button_layout.addWidget(add_btn)
        button_layout.addWidget(remove_btn)
        button_layout.addWidget(refresh_btn)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
        
        # 初始刷新
        self.refresh_table()
        
    def refresh_table(self):
        """刷新表格数据"""
        self.aircraft_table.setRowCount(0)
        
        for aircraft in self.data_manager.get_all_aircrafts():
            row = self.aircraft_table.rowCount()
            self.aircraft_table.insertRow(row)
            
            self.aircraft_table.setItem(row, 0, QTableWidgetItem(str(aircraft.id)))
            self.aircraft_table.setItem(row, 1, QTableWidgetItem(aircraft.callsign))
            self.aircraft_table.setItem(row, 2, QTableWidgetItem(aircraft.type))
            self.aircraft_table.setItem(row, 3, QTableWidgetItem(f"({aircraft.x:.2f}, {aircraft.y:.2f})"))
            self.aircraft_table.setItem(row, 4, QTableWidgetItem(aircraft.status))
            self.aircraft_table.setItem(row, 5, QTableWidgetItem(f"{aircraft.fuel}%"))
            self.aircraft_table.setItem(row, 6, QTableWidgetItem(f"{aircraft.ammo}%"))
            
            # 操作按钮
            control_widget = QWidget()
            control_layout = QHBoxLayout(control_widget)
            
            info_btn = QPushButton("详情")
            command_btn = QPushButton("指挥")
            
            info_btn.clicked.connect(lambda checked, id=aircraft.id: self.show_aircraft_info(id))
            command_btn.clicked.connect(lambda checked, id=aircraft.id: self.send_command(id))
            
            control_layout.addWidget(info_btn)
            control_layout.addWidget(command_btn)
            control_layout.setContentsMargins(0, 0, 0, 0)
            
            self.aircraft_table.setCellWidget(row, 7, control_widget)
            
        self.aircraft_table.resizeColumnsToContents()
        
    def add_aircraft(self):
        """添加战机对话框"""
        dialog = QDialog(self)
        dialog.setWindowTitle("添加战机")
        dialog.setModal(True)
        
        layout = QFormLayout()
        
        callsign_edit = QLineEdit()
        type_combo = QComboBox()
        type_combo.addItems(["战斗机", "轰炸机", "侦察机", "预警机", "无人机"])
        x_edit = QDoubleSpinBox()
        x_edit.setRange(-1000, 1000)
        y_edit = QDoubleSpinBox()
        y_edit.setRange(-1000, 1000)
        altitude_edit = QSpinBox()
        altitude_edit.setRange(0, 20000)
        altitude_edit.setValue(5000)
        speed_edit = QSpinBox()
        speed_edit.setRange(0, 3000)
        speed_edit.setValue(800)
        heading_edit = QSpinBox()
        heading_edit.setRange(0, 359)
        
        layout.addRow("呼号:", callsign_edit)
        layout.addRow("类型:", type_combo)
        layout.addRow("X坐标:", x_edit)
        layout.addRow("Y坐标:", y_edit)
        layout.addRow("高度(米):", altitude_edit)
        layout.addRow("速度(公里/小时):", speed_edit)
        layout.addRow("航向(度):", heading_edit)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)
        
        dialog.setLayout(layout)
        
        if dialog.exec_() == QDialog.Accepted:
            # 添加战机
            self.data_manager.add_aircraft(
                callsign_edit.text(),
                type_combo.currentText(),
                x_edit.value(),
                y_edit.value(),
                altitude_edit.value(),
                speed_edit.value(),
                heading_edit.value()
            )
            self.refresh_table()
            
    def remove_aircraft(self):
        """移除选中战机"""
        current_row = self.aircraft_table.currentRow()
        if current_row >= 0:
            aircraft_id = int(self.aircraft_table.item(current_row, 0).text())
            self.data_manager.remove_aircraft(aircraft_id)
            self.refresh_table()
            
    def show_aircraft_info(self, aircraft_id):
        """显示战机详细信息"""
        aircraft = self.data_manager.get_aircraft_by_id(aircraft_id)
        if aircraft:
            QMessageBox.information(self, "战机信息", 
                                   f"呼号: {aircraft.callsign}\n"
                                   f"类型: {aircraft.type}\n"
                                   f"位置: ({aircraft.x:.2f}, {aircraft.y:.2f})\n"
                                   f"高度: {aircraft.altitude}米\n"
                                   f"速度: {aircraft.speed}公里/小时\n"
                                   f"航向: {aircraft.heading}°\n"
                                   f"状态: {aircraft.status}\n"
                                   f"燃油: {aircraft.fuel}%\n"
                                   f"弹药: {aircraft.ammo}%")
            
    def send_command(self, aircraft_id):
        """发送指挥命令"""
        dialog = QDialog(self)
        dialog.setWindowTitle("发送指挥命令")
        dialog.setModal(True)
        
        layout = QVBoxLayout()
        
        command_combo = QComboBox()
        command_combo.addItems(["改变航向", "改变高度", "改变速度", "攻击目标", "返航"])
        
        param_layout = QFormLayout()
        param1_edit = QDoubleSpinBox()
        param1_edit.setRange(-1000, 1000)
        param2_edit = QDoubleSpinBox()
        param2_edit.setRange(-1000, 1000)
        
        param_layout.addRow("参数1:", param1_edit)
        param_layout.addRow("参数2:", param2_edit)
        
        layout.addWidget(QLabel("选择命令:"))
        layout.addWidget(command_combo)
        layout.addLayout(param_layout)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        dialog.setLayout(layout)
        
        if dialog.exec_() == QDialog.Accepted:
            QMessageBox.information(self, "命令发送", "指挥命令已发送到战机")


# 战术分析面板
class TacticalPanel(QWidget):
    """战术分析面板"""
    def __init__(self, data_manager, tactical_analyzer):
        super().__init__()
        self.data_manager = data_manager
        self.tactical_analyzer = tactical_analyzer
        self.init_ui()
        
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout()
        
        # 标题
        title = QLabel("战术分析")
        title.setFont(QFont("Arial", 14, QFont.Bold))
        layout.addWidget(title)
        
        # 威胁评估区域
        threat_group = QGroupBox("威胁评估")
        threat_layout = QVBoxLayout()
        
        self.threat_table = QTableWidget()
        self.threat_table.setColumnCount(5)
        self.threat_table.setHorizontalHeaderLabels(["战机", "威胁目标", "距离", "威胁等级", "建议行动"])
        threat_layout.addWidget(self.threat_table)
        
        threat_group.setLayout(threat_layout)
        layout.addWidget(threat_group)
        
        # 战术建议区域
        advice_group = QGroupBox("战术建议")
        advice_layout = QVBoxLayout()
        
        self.advice_text = QTextEdit()
        self.advice_text.setReadOnly(True)
        advice_layout.addWidget(self.advice_text)
        
        advice_group.setLayout(advice_layout)
        layout.addWidget(advice_group)
        
        self.setLayout(layout)
        
        # 定时刷新
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_analysis)
        self.refresh_timer.start(2000)  # 每2秒刷新一次
        
        # 初始刷新
        self.refresh_analysis()
        
    def refresh_analysis(self):
        """刷新战术分析"""
        self.refresh_threat_assessment()
        self.refresh_tactical_advice()
        
    def refresh_threat_assessment(self):
        """刷新威胁评估"""
        self.threat_table.setRowCount(0)
        
        for aircraft in self.data_manager.get_all_aircrafts():
            for threat in self.data_manager.get_all_threats():
                threat_level = self.tactical_analyzer.assess_threat_level(aircraft, threat)
                if threat_level > 0:  # 只显示有威胁的目标
                    distance = self.tactical_analyzer.calculate_distance(
                        aircraft.x, aircraft.y, threat.x, threat.y)
                    
                    row = self.threat_table.rowCount()
                    self.threat_table.insertRow(row)
                    
                    self.threat_table.setItem(row, 0, QTableWidgetItem(aircraft.callsign))
                    self.threat_table.setItem(row, 1, QTableWidgetItem(threat.type))
                    self.threat_table.setItem(row, 2, QTableWidgetItem(f"{distance:.2f}"))
                    self.threat_table.setItem(row, 3, QTableWidgetItem(f"{threat_level:.1f}"))
                    
                    # 根据威胁等级提供建议
                    if threat_level > 7:
                        advice = "立即规避"
                    elif threat_level > 4:
                        advice = "保持警惕"
                    else:
                        advice = "正常飞行"
                        
                    self.threat_table.setItem(row, 4, QTableWidgetItem(advice))
                    
        self.threat_table.resizeColumnsToContents()
        
    def refresh_tactical_advice(self):
        """刷新战术建议"""
        advice_text = ""
        
        # 分析所有战机的总体状态
        aircrafts = self.data_manager.get_all_aircrafts()
        threats = self.data_manager.get_all_threats()
        
        if not aircrafts:
            advice_text = "当前没有战机在战场中"
        else:
            # 检查低燃油战机
            low_fuel_aircrafts = [a for a in aircrafts if a.fuel < 20]
            if low_fuel_aircrafts:
                advice_text += "警告: 以下战机燃油不足:\n"
                for aircraft in low_fuel_aircrafts:
                    advice_text += f"  - {aircraft.callsign} (燃油: {aircraft.fuel}%)\n"
                advice_text += "建议: 安排返航或空中加油\n\n"
                
            # 检查高风险战机
            high_risk_aircrafts = []
            for aircraft in aircrafts:
                max_threat = 0
                for threat in threats:
                    threat_level = self.tactical_analyzer.assess_threat_level(aircraft, threat)
                    max_threat = max(max_threat, threat_level)
                    
                if max_threat > 7:
                    high_risk_aircrafts.append((aircraft, max_threat))
                    
            if high_risk_aircrafts:
                advice_text += "高风险战机:\n"
                for aircraft, threat_level in high_risk_aircrafts:
                    advice_text += f"  - {aircraft.callsign} (威胁等级: {threat_level:.1f})\n"
                advice_text += "建议: 立即采取规避行动或提供支援\n\n"
                
            # 总体态势评估
            if not advice_text:
                advice_text = "当前战场态势良好，所有战机状态正常"
                
        self.advice_text.setText(advice_text)


# 系统状态面板
class StatusPanel(QWidget):
    """系统状态面板"""
    def __init__(self, data_manager):
        super().__init__()
        self.data_manager = data_manager
        self.init_ui()
        
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout()
        
        # 标题
        title = QLabel("系统状态")
        title.setFont(QFont("Arial", 14, QFont.Bold))
        layout.addWidget(title)
        
        # 系统信息区域
        info_group = QGroupBox("系统信息")
        info_layout = QFormLayout()
        
        self.aircraft_count_label = QLabel("0")
        self.threat_count_label = QLabel("0")
        self.mission_count_label = QLabel("0")
        self.system_status_label = QLabel("正常")
        self.last_update_label = QLabel("-")
        
        info_layout.addRow("战机数量:", self.aircraft_count_label)
        info_layout.addRow("威胁目标数量:", self.threat_count_label)
        info_layout.addRow("任务数量:", self.mission_count_label)
        info_layout.addRow("系统状态:", self.system_status_label)
        info_layout.addRow("最后更新:", self.last_update_label)
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # 数据统计区域
        stats_group = QGroupBox("数据统计")
        stats_layout = QVBoxLayout()
        
        self.stats_text = QTextEdit()
        self.stats_text.setReadOnly(True)
        stats_layout.addWidget(self.stats_text)
        
        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)
        
        self.setLayout(layout)
        
        # 定时刷新
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_status)
        self.refresh_timer.start(1000)  # 每秒刷新一次
        
        # 初始刷新
        self.refresh_status()
        
    def refresh_status(self):
        """刷新系统状态"""
        # 更新计数
        aircraft_count = len(self.data_manager.get_all_aircrafts())
        threat_count = len(self.data_manager.get_all_threats())
        mission_count = len(self.data_manager.get_all_missions())
        
        self.aircraft_count_label.setText(str(aircraft_count))
        self.threat_count_label.setText(str(threat_count))
        self.mission_count_label.setText(str(mission_count))
        
        # 更新最后更新时间
        now = datetime.now()
        self.last_update_label.setText(now.strftime("%H:%M:%S"))
        
        # 更新数据统计
        stats_text = f"数据统计 (更新时间: {now.strftime('%Y-%m-%d %H:%M:%S')})\n\n"
        
        if aircraft_count > 0:
            stats_text += "战机状态分布:\n"
            status_count = {}
            for aircraft in self.data_manager.get_all_aircrafts():
                status_count[aircraft.status] = status_count.get(aircraft.status, 0) + 1
                
            for status, count in status_count.items():
                stats_text += f"  {status}: {count}架\n"
                
            # 平均燃油和弹药
            avg_fuel = sum(a.fuel for a in self.data_manager.get_all_aircrafts()) / aircraft_count
            avg_ammo = sum(a.ammo for a in self.data_manager.get_all_aircrafts()) / aircraft_count
            stats_text += f"\n平均燃油: {avg_fuel:.1f}%\n"
            stats_text += f"平均弹药: {avg_ammo:.1f}%\n"
            
        self.stats_text.setText(stats_text)


# 数据模拟器
class DataSimulator(QThread):
    """数据模拟器，用于生成模拟数据"""
    data_updated = pyqtSignal()
    
    def __init__(self, data_manager):
        super().__init__()
        self.data_manager = data_manager
        self.running = False
        
    def run(self):
        """运行数据模拟"""
        self.running = True
        while self.running:
            # 更新所有战机位置
            for aircraft in self.data_manager.get_all_aircrafts():
                # 模拟战机移动
                dx = math.cos(math.radians(aircraft.heading)) * aircraft.speed / 3600  # 每秒移动距离
                dy = math.sin(math.radians(aircraft.heading)) * aircraft.speed / 3600
                
                new_x = aircraft.x + dx
                new_y = aircraft.y + dy
                
                # 边界检查
                if abs(new_x) > 900:
                    aircraft.heading = 180 - aircraft.heading
                    new_x = aircraft.x - dx
                    
                if abs(new_y) > 900:
                    aircraft.heading = -aircraft.heading
                    new_y = aircraft.y - dy
                    
                # 随机状态变化
                status_change = random.random()
                if status_change < 0.01:  # 1%概率状态变为警告
                    aircraft.update_status("警告")
                elif status_change < 0.02:  # 1%概率状态变为危险
                    aircraft.update_status("危险")
                elif status_change < 0.03:  # 1%概率状态恢复正常
                    aircraft.update_status("正常")
                    
                # 燃油和弹药消耗
                fuel_consumption = random.uniform(0.01, 0.05)
                ammo_consumption = random.uniform(0, 0.02)
                
                aircraft.update_status(
                    aircraft.status,
                    aircraft.fuel - fuel_consumption,
                    aircraft.ammo - ammo_consumption
                )
                
                # 更新位置
                aircraft.update_position(new_x, new_y, aircraft.altitude, aircraft.speed, aircraft.heading)
                
            # 发出数据更新信号
            self.data_updated.emit()
            
            # 休眠1秒
            self.msleep(1000)
            
    def stop(self):
        """停止数据模拟"""
        self.running = False


# 主窗口
class AirCombatCommandSystem(QMainWindow):
    """空战指挥系统主窗口"""
    def __init__(self):
        super().__init__()
        
        # 初始化数据管理和分析组件
        self.data_manager = DataManager()
        self.tactical_analyzer = TacticalAnalyzer()
        self.data_simulator = DataSimulator(self.data_manager)
        
        # 初始化UI
        self.init_ui()
        
        # 加载示例数据
        self.load_sample_data()
        
        # 启动数据模拟
        self.data_simulator.data_updated.connect(self.on_data_updated)
        self.data_simulator.start()
        
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("空战指挥系统")
        self.setGeometry(100, 100, 1400, 900)
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QHBoxLayout(central_widget)
        
        # 左侧面板（战场视图）
        left_panel = QVBoxLayout()
        
        # 战场视图
        self.battlefield_view = BattlefieldView(self.data_manager)
        self.battlefield_view.aircraft_selected.connect(self.on_aircraft_selected)
        self.battlefield_view.threat_selected.connect(self.on_threat_selected)
        left_panel.addWidget(self.battlefield_view)
        
        # 右侧面板（各种控制面板）
        right_panel = QSplitter(Qt.Vertical)
        
        # 战机管理面板
        self.aircraft_panel = AircraftPanel(self.data_manager)
        right_panel.addWidget(self.aircraft_panel)
        
        # 战术分析面板
        self.tactical_panel = TacticalPanel(self.data_manager, self.tactical_analyzer)
        right_panel.addWidget(self.tactical_panel)
        
        # 系统状态面板
        self.status_panel = StatusPanel(self.data_manager)
        right_panel.addWidget(self.status_panel)
        
        # 设置右侧面板比例
        right_panel.setSizes([400, 300, 200])
        
        # 添加到主布局
        main_layout.addLayout(left_panel, 2)  # 左侧占2/3空间
        main_layout.addWidget(right_panel, 1)  # 右侧占1/3空间
        
        # 创建菜单栏
        self.create_menu_bar()
        
        # 创建工具栏
        self.create_tool_bar()
        
    def create_menu_bar(self):
        """创建菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu('文件')
        
        new_action = QAction('新建', self)
        new_action.setShortcut('Ctrl+N')
        file_menu.addAction(new_action)
        
        open_action = QAction('打开', self)
        open_action.setShortcut('Ctrl+O')
        file_menu.addAction(open_action)
        
        save_action = QAction('保存', self)
        save_action.setShortcut('Ctrl+S')
        file_menu.addAction(save_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction('退出', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 视图菜单
        view_menu = menubar.addMenu('视图')
        
        zoom_in_action = QAction('放大', self)
        zoom_in_action.setShortcut('Ctrl++')
        zoom_in_action.triggered.connect(self.zoom_in)
        view_menu.addAction(zoom_in_action)
        
        zoom_out_action = QAction('缩小', self)
        zoom_out_action.setShortcut('Ctrl+-')
        zoom_out_action.triggered.connect(self.zoom_out)
        view_menu.addAction(zoom_out_action)
        
        reset_zoom_action = QAction('重置缩放', self)
        reset_zoom_action.setShortcut('Ctrl+0')
        reset_zoom_action.triggered.connect(self.reset_zoom)
        view_menu.addAction(reset_zoom_action)
        
        # 工具菜单
        tools_menu = menubar.addMenu('工具')
        
        add_aircraft_action = QAction('添加战机', self)
        add_aircraft_action.triggered.connect(self.aircraft_panel.add_aircraft)
        tools_menu.addAction(add_aircraft_action)
        
        add_threat_action = QAction('添加威胁', self)
        add_threat_action.triggered.connect(self.add_threat)
        tools_menu.addAction(add_threat_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu('帮助')
        
        about_action = QAction('关于', self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
    def create_tool_bar(self):
        """创建工具栏"""
        toolbar = self.addToolBar('主工具栏')
        
        add_aircraft_btn = QPushButton('添加战机')
        add_aircraft_btn.clicked.connect(self.aircraft_panel.add_aircraft)
        toolbar.addWidget(add_aircraft_btn)
        
        add_threat_btn = QPushButton('添加威胁')
        add_threat_btn.clicked.connect(self.add_threat)
        toolbar.addWidget(add_threat_btn)
        
        refresh_btn = QPushButton('刷新')
        refresh_btn.clicked.connect(self.refresh_all)
        toolbar.addWidget(refresh_btn)
        
    def load_sample_data(self):
        """加载示例数据"""
        # 添加示例战机
        self.data_manager.add_aircraft("鹰01", "战斗机", 100, 100, 8000, 900, 45)
        self.data_manager.add_aircraft("鹰02", "战斗机", -50, 200, 7500, 850, 120)
        self.data_manager.add_aircraft("雷01", "轰炸机", -200, -100, 10000, 700, 300)
        
        # 添加示例威胁
        self.data_manager.add_threat("防空导弹", 300, 300, 200, 8)
        self.data_manager.add_threat("雷达站", -300, -200, 300, 6)
        self.data_manager.add_threat("敌方战机", 150, -150, 150, 9)
        
        # 添加示例任务
        self.data_manager.add_mission(
            "巡逻任务", 
            [1, 2], 
            [(100, 100), (200, 200), (100, 300), (0, 200)], 
            "区域巡逻"
        )
        
    def on_data_updated(self):
        """数据更新时的处理"""
        # 刷新各个面板
        self.aircraft_panel.refresh_table()
        self.battlefield_view.refresh_display()
        
    def on_aircraft_selected(self, aircraft_id):
        """战机被选中时的处理"""
        aircraft = self.data_manager.get_aircraft_by_id(aircraft_id)
        if aircraft:
            QMessageBox.information(self, "战机选择", f"已选择战机: {aircraft.callsign}")
            
    def on_threat_selected(self, threat_id):
        """威胁被选中时的处理"""
        threat = self.data_manager.get_threat_by_id(threat_id)
        if threat:
            QMessageBox.information(self, "威胁选择", f"已选择威胁: {threat.type}")
            
    def add_threat(self):
        """添加威胁对话框"""
        dialog = QDialog(self)
        dialog.setWindowTitle("添加威胁")
        dialog.setModal(True)
        
        layout = QFormLayout()
        
        type_combo = QComboBox()
        type_combo.addItems(["防空导弹", "雷达站", "敌方战机", "防空炮", "电子干扰"])
        x_edit = QDoubleSpinBox()
        x_edit.setRange(-1000, 1000)
        y_edit = QDoubleSpinBox()
        y_edit.setRange(-1000, 1000)
        range_edit = QDoubleSpinBox()
        range_edit.setRange(10, 500)
        range_edit.setValue(150)
        threat_level_edit = QSpinBox()
        threat_level_edit.setRange(1, 10)
        threat_level_edit.setValue(5)
        
        layout.addRow("威胁类型:", type_combo)
        layout.addRow("X坐标:", x_edit)
        layout.addRow("Y坐标:", y_edit)
        layout.addRow("威胁范围:", range_edit)
        layout.addRow("威胁等级(1-10):", threat_level_edit)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)
        
        dialog.setLayout(layout)
        
        if dialog.exec_() == QDialog.Accepted:
            # 添加威胁
            self.data_manager.add_threat(
                type_combo.currentText(),
                x_edit.value(),
                y_edit.value(),
                range_edit.value(),
                threat_level_edit.value()
            )
            # 刷新战场视图
            self.battlefield_view.init_scene()
            
    def zoom_in(self):
        """放大视图"""
        self.battlefield_view.scale(1.2, 1.2)
        
    def zoom_out(self):
        """缩小视图"""
        self.battlefield_view.scale(1/1.2, 1/1.2)
        
    def reset_zoom(self):
        """重置缩放"""
        self.battlefield_view.resetTransform()
        
    def refresh_all(self):
        """刷新所有显示"""
        self.aircraft_panel.refresh_table()
        self.battlefield_view.refresh_display()
        self.tactical_panel.refresh_analysis()
        self.status_panel.refresh_status()
        
    def show_about(self):
        """显示关于对话框"""
        QMessageBox.about(self, "关于空战指挥系统", 
                         "空战指挥系统 v1.0\n\n"
                         "基于PyQt5开发的空战指挥模拟系统，提供战场可视化、"
                         "战机管理、战术分析和指挥控制功能。\n\n"
                         "版权所有 (C) 2023")
        
    def closeEvent(self, event):
        """关闭事件处理"""
        # 停止数据模拟线程
        self.data_simulator.stop()
        self.data_simulator.wait()
        event.accept()


# 主程序入口
if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # 设置应用程序样式
    app.setStyle('Fusion')
    
    # 创建并显示主窗口
    window = AirCombatCommandSystem()
    window.show()
    
    # 运行应用程序
    sys.exit(app.exec_())