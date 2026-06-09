import sys
import math
import json
import socket
import threading
from datetime import datetime, timedelta
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QPushButton, QTextEdit, QTabWidget, QTableWidget, 
                             QTableWidgetItem, QGroupBox, QSplitter, QMessageBox, QToolBar,
                             QStatusBar, QAction, QFileDialog, QComboBox, QSpinBox, QDoubleSpinBox,
                             QCheckBox, QProgressBar, QListWidget, QTreeWidget, QTreeWidgetItem,
                             QGraphicsView, QGraphicsScene, QGraphicsItem, QGraphicsEllipseItem,
                             QGraphicsLineItem, QGraphicsTextItem, QMenu, QDialog, QGridLayout,
                             QInputDialog, QLineEdit)
from PyQt5.QtCore import QLineF, Qt, QTimer, QPointF, QRectF, pyqtSignal, QThread, QObject, QDateTime, QPoint
from PyQt5.QtGui import QFont, QColor, QPen, QBrush, QPainter, QIcon, QPixmap, QKeySequence
from PyQt5.QtNetwork import QTcpServer, QTcpSocket, QHostAddress


# ============================ 数据模型类 ============================

class BattleUnit:
    """战斗单元基类"""
    def __init__(self, unit_id, name, position, faction):
        self.id = unit_id
        self.name = name
        self.position = position  # (x, y) 坐标
        self.faction = faction  # 阵营
        self.health = 100
        self.max_health = 100
        self.speed = 0
        self.heading = 0  # 航向，角度制
        self.status = "正常"  # 状态：正常、受损、沉没等
        self.sensors = {}  # 传感器数据
        self.weapons = {}  # 武器系统
        self.destination = None  # 目标位置
        self.waypoints = []  # 航路点列表
        self.orders = []  # 命令队列
        
    def update_position(self, new_position):
        self.position = new_position
        
    def update_health(self, damage):
        self.health = max(0, self.health - damage)
        if self.health <= 0:
            self.status = "沉没"
            
    def set_destination(self, destination):
        """设置目标位置"""
        self.destination = destination
        self.waypoints = [destination]  # 简化处理，直接设置目标点
        
    def add_waypoint(self, waypoint):
        """添加航路点"""
        self.waypoints.append(waypoint)
        
    def add_order(self, order):
        """添加命令"""
        self.orders.append(order)
        
    def clear_orders(self):
        """清除所有命令"""
        self.orders = []
        self.waypoints = []
        self.destination = None
        
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'position': self.position,
            'faction': self.faction,
            'health': self.health,
            'speed': self.speed,
            'heading': self.heading,
            'status': self.status,
            'destination': self.destination,
            'waypoints': self.waypoints
        }


class Warship(BattleUnit):
    """战舰类"""
    def __init__(self, unit_id, name, position, faction, ship_type):
        super().__init__(unit_id, name, position, faction)
        self.ship_type = ship_type  # 舰船类型
        self.displacement = 0  # 排水量
        self.radar_range = 100  # 雷达探测范围
        self.sonar_range = 50   # 声纳探测范围
        self.max_speed = 30  # 最大速度（节）


class Aircraft(BattleUnit):
    """飞机类"""
    def __init__(self, unit_id, name, position, faction, aircraft_type):
        super().__init__(unit_id, name, position, faction)
        self.aircraft_type = aircraft_type  # 飞机类型
        self.altitude = 0  # 高度
        self.fuel = 100  # 燃油量
        self.max_speed = 300  # 最大速度（节）


class Submarine(BattleUnit):
    """潜艇类"""
    def __init__(self, unit_id, name, position, faction, submarine_type):
        super().__init__(unit_id, name, position, faction)
        self.submarine_type = submarine_type
        self.depth = 0  # 深度
        self.silent_mode = False  # 静默模式
        self.max_speed = 25  # 最大速度（节）


class WeaponSystem:
    """武器系统类"""
    def __init__(self, name, weapon_type, range, damage, ammunition=10):
        self.name = name
        self.weapon_type = weapon_type  # 导弹、鱼雷、火炮等
        self.range = range  # 射程
        self.damage = damage  # 伤害值
        self.ammunition = ammunition  # 弹药量
        self.cooldown = 0  # 冷却时间
        self.max_cooldown = 5  # 最大冷却时间（秒）
        
    def fire(self, target):
        """发射武器"""
        if self.ammunition > 0 and self.cooldown <= 0:
            self.ammunition -= 1
            self.cooldown = self.max_cooldown
            return self.damage
        return 0
    
    def update(self, delta_time):
        """更新武器状态"""
        if self.cooldown > 0:
            self.cooldown -= delta_time


class BattleScenario:
    """战斗场景类"""
    def __init__(self, name, description, size=(1000, 1000)):
        self.name = name
        self.description = description
        self.size = size  # 场景尺寸
        self.units = {}  # 所有战斗单元
        self.time = datetime.now()  # 场景时间
        self.weather = "晴朗"  # 天气状况
        self.sea_state = 1  # 海况
        self.events = []  # 事件记录
        self.simulation_speed = 1.0  # 模拟速度倍数
        
    def add_unit(self, unit):
        self.units[unit.id] = unit
        
    def remove_unit(self, unit_id):
        if unit_id in self.units:
            del self.units[unit_id]
            
    def get_units_by_faction(self, faction):
        return [unit for unit in self.units.values() if unit.faction == faction]
    
    def add_event(self, event_type, description, unit_id=None, position=None):
        """添加事件记录"""
        event = {
            'time': self.time,
            'type': event_type,
            'description': description,
            'unit_id': unit_id,
            'position': position
        }
        self.events.append(event)
        
    def to_dict(self):
        return {
            'name': self.name,
            'description': self.description,
            'size': self.size,
            'units': {uid: unit.to_dict() for uid, unit in self.units.items()},
            'time': self.time.isoformat(),
            'weather': self.weather,
            'sea_state': self.sea_state,
            'events': self.events
        }


# ============================ 模拟引擎 ============================

class SimulationEngine(QThread):
    """模拟引擎线程"""
    simulation_updated = pyqtSignal()  # 信号：模拟更新
    
    def __init__(self, scenario):
        super().__init__()
        self.scenario = scenario
        self.running = False
        self.last_update = datetime.now()
        
    def run(self):
        self.running = True
        while self.running:
            current_time = datetime.now()
            delta_time = (current_time - self.last_update).total_seconds()
            self.last_update = current_time
            
            # 更新模拟
            self.update_simulation(delta_time * self.scenario.simulation_speed)
            
            # 发射更新信号
            self.simulation_updated.emit()
            
            # 控制更新频率
            self.msleep(50)  # 约20Hz
            
    def stop(self):
        self.running = False
        
    def update_simulation(self, delta_time):
        """更新模拟状态"""
        # 更新单位位置
        for unit in self.scenario.units.values():
            self.update_unit_movement(unit, delta_time)
            
        # 更新武器系统
        for unit in self.scenario.units.values():
            for weapon in unit.weapons.values():
                weapon.update(delta_time)
                
        # 更新场景时间
        self.scenario.time += timedelta(seconds=delta_time)
        
    def update_unit_movement(self, unit, delta_time):
        """更新单位移动"""
        if unit.destination and unit.speed > 0:
            # 计算到目标点的方向
            dx = unit.destination[0] - unit.position[0]
            dy = unit.destination[1] - unit.position[1]
            distance = math.sqrt(dx**2 + dy**2)
            
            if distance > 5:  # 距离阈值
                # 计算目标航向
                target_heading = math.degrees(math.atan2(dy, dx))
                
                # 平滑转向（最大转向速率）
                heading_diff = (target_heading - unit.heading) % 360
                if heading_diff > 180:
                    heading_diff -= 360
                    
                max_turn_rate = 10  # 最大转向速率（度/秒）
                turn_amount = max_turn_rate * delta_time
                
                if abs(heading_diff) <= turn_amount:
                    unit.heading = target_heading
                else:
                    unit.heading += turn_amount if heading_diff > 0 else -turn_amount
                unit.heading %= 360
                
                # 移动单位
                heading_rad = math.radians(unit.heading)
                move_distance = unit.speed * delta_time / 3.6  # 节转换为米/秒
                new_x = unit.position[0] + math.cos(heading_rad) * move_distance
                new_y = unit.position[1] + math.sin(heading_rad) * move_distance
                
                unit.position = (new_x, new_y)
            else:
                # 到达目标点
                if unit.waypoints:
                    unit.waypoints.pop(0)  # 移除当前航路点
                    if unit.waypoints:
                        unit.destination = unit.waypoints[0]
                    else:
                        unit.destination = None
                        unit.speed = 0


# ============================ 通信模块 ============================

class CommunicationServer(QObject):
    """通信服务器"""
    message_received = pyqtSignal(str, dict)  # 信号：接收到消息
    client_connected = pyqtSignal(str)  # 信号：客户端连接
    client_disconnected = pyqtSignal(str)  # 信号：客户端断开连接
    
    def __init__(self, port=8888):
        super().__init__()
        self.port = port
        self.server = QTcpServer()
        self.clients = {}
        
    def start_server(self):
        if self.server.listen(QHostAddress.Any, self.port):
            self.server.newConnection.connect(self.on_new_connection)
            return True
        return False
        
    def on_new_connection(self):
        client_socket = self.server.nextPendingConnection()
        client_address = client_socket.peerAddress().toString()
        client_socket.readyRead.connect(lambda: self.read_data(client_socket))
        client_socket.disconnected.connect(lambda: self.remove_client(client_socket))
        self.clients[client_address] = client_socket
        self.client_connected.emit(client_address)
        
    def read_data(self, client_socket):
        data = client_socket.readAll().data().decode('utf-8')
        try:
            message = json.loads(data)
            self.message_received.emit(client_socket.peerAddress().toString(), message)
        except json.JSONDecodeError:
            pass
            
    def remove_client(self, client_socket):
        client_address = client_socket.peerAddress().toString()
        if client_address in self.clients:
            del self.clients[client_address]
            self.client_disconnected.emit(client_address)
            
    def broadcast_message(self, message):
        data = json.dumps(message).encode('utf-8')
        for client in self.clients.values():
            client.write(data)
            
    def send_to_client(self, client_address, message):
        """向特定客户端发送消息"""
        if client_address in self.clients:
            data = json.dumps(message).encode('utf-8')
            self.clients[client_address].write(data)


class CommunicationClient(QObject):
    """通信客户端"""
    message_received = pyqtSignal(dict)  # 信号：接收到消息
    connected = pyqtSignal()  # 信号：连接成功
    disconnected = pyqtSignal()  # 信号：连接断开
    
    def __init__(self):
        super().__init__()
        self.socket = QTcpSocket()
        self.socket.readyRead.connect(self.read_data)
        self.socket.connected.connect(self.connected)
        self.socket.disconnected.connect(self.disconnected)
        
    def connect_to_server(self, host, port):
        self.socket.connectToHost(host, port)
        return self.socket.waitForConnected()
        
    def send_message(self, message):
        data = json.dumps(message).encode('utf-8')
        self.socket.write(data)
        
    def read_data(self):
        data = self.socket.readAll().data().decode('utf-8')
        try:
            message = json.loads(data)
            self.message_received.emit(message)
        except json.JSONDecodeError:
            pass


# ============================ 地图显示模块 ============================

class BattleMapView(QGraphicsView):
    """战场地图视图"""
    unit_selected = pyqtSignal(str)  # 信号：单元被选中
    position_clicked = pyqtSignal(tuple)  # 信号：位置被点击
    context_menu_requested = pyqtSignal(tuple, QPoint)  # 信号：右键菜单请求
    
    def __init__(self):
        super().__init__()
        self.scene = QGraphicsScene()
        self.setScene(self.scene)
        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        
        # 地图背景
        self.setBackgroundBrush(QBrush(QColor(30, 30, 60)))
        
        # 缩放控制
        self.zoom_level = 1.0
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        
        # 网格和坐标
        self.show_grid = True
        self.show_coordinates = True
        
        # 战斗单元图形项
        self.unit_items = {}
        
        # 战术标记
        self.tactical_marks = {}
        
        # 航路点显示
        self.show_waypoints = True
        
    def wheelEvent(self, event):
        # 鼠标滚轮缩放
        factor = 1.2
        if event.angleDelta().y() < 0:
            factor = 1.0 / factor
            
        self.zoom_level *= factor
        self.scale(factor, factor)
        
    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            # 右键点击获取坐标
            scene_pos = self.mapToScene(event.pos())
            self.position_clicked.emit((scene_pos.x(), scene_pos.y()))
            self.context_menu_requested.emit((scene_pos.x(), scene_pos.y()), event.globalPos())
        else:
            super().mousePressEvent(event)
            
    def drawBackground(self, painter, rect):
        # 绘制背景网格和坐标
        painter.fillRect(rect, self.backgroundBrush())
        
        if self.show_grid:
            pen = QPen(QColor(60, 60, 90))
            pen.setWidth(0)
            painter.setPen(pen)
            
            grid_size = 50
            left = int(rect.left()) - (int(rect.left()) % grid_size)
            top = int(rect.top()) - (int(rect.top()) % grid_size)
            
            # 使用QLineF对象
            x = left
            while x < rect.right():
                line = QLineF(x, rect.top(), x, rect.bottom())
                painter.drawLine(line)
                x += grid_size
                
            y = top
            while y < rect.bottom():
                line = QLineF(rect.left(), y, rect.right(), y)
                painter.drawLine(line)
                y += grid_size
                
        if self.show_coordinates:
            font = QFont("Arial", 8)
            painter.setFont(font)
            painter.setPen(QColor(150, 150, 150))
            
            # 绘制坐标标签
            grid_size = 100
            left = int(rect.left()) - (int(rect.left()) % grid_size)
            top = int(rect.top()) - (int(rect.top()) % grid_size)
            
            x = left
            while x < rect.right():
                y = top
                while y < rect.bottom():
                    painter.drawText(QRectF(x+2, y+2, 50, 20), f"{x},{y}")
                    y += grid_size
                x += grid_size
                
    def update_units(self, units):
        # 更新战斗单元显示
        current_ids = set(self.unit_items.keys())
        new_ids = set(units.keys())
        
        # 移除不存在的单元
        for uid in current_ids - new_ids:
            if uid in self.unit_items:
                self.scene.removeItem(self.unit_items[uid])
                del self.unit_items[uid]
                
        # 添加或更新单元
        for uid, unit in units.items():
            if uid not in self.unit_items:
                # 创建新的单元图形项
                item = UnitGraphicsItem(unit)
                self.unit_items[uid] = item
                self.scene.addItem(item)
            else:
                # 更新现有单元
                self.unit_items[uid].update_unit(unit)
                
        # 更新航路点显示
        if self.show_waypoints:
            self.update_waypoints(units)
                
    def update_waypoints(self, units):
        # 更新航路点显示
        # 先清除所有航路线
        for item in self.scene.items():
            if isinstance(item, WaypointLineItem):
                self.scene.removeItem(item)
                
        # 绘制新的航路线
        for unit in units.values():
            if unit.waypoints:
                # 绘制从当前位置到第一个航路点的线
                start_pos = unit.position
                for i, waypoint in enumerate(unit.waypoints):
                    if i == 0:
                        end_pos = waypoint
                    else:
                        start_pos = unit.waypoints[i-1]
                        end_pos = waypoint
                    
                    line = WaypointLineItem(start_pos, end_pos, unit.faction)
                    self.scene.addItem(line)
        
    def add_tactical_mark(self, mark_id, position, mark_type, text=""):
        # 添加战术标记
        if mark_id in self.tactical_marks:
            self.scene.removeItem(self.tactical_marks[mark_id])
            
        mark = TacticalMarkItem(position, mark_type, text)
        self.tactical_marks[mark_id] = mark
        self.scene.addItem(mark)
        
    def clear_tactical_marks(self):
        # 清除所有战术标记
        for mark in self.tactical_marks.values():
            self.scene.removeItem(mark)
        self.tactical_marks.clear()


class UnitGraphicsItem(QGraphicsItem):
    """战斗单元图形项"""
    def __init__(self, unit):
        super().__init__()
        self.unit = unit
        self.setPos(unit.position[0], unit.position[1])
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        
        # 根据阵营设置颜色
        if unit.faction == "蓝方":
            self.color = QColor(0, 100, 255)
        elif unit.faction == "红方":
            self.color = QColor(255, 50, 50)
        else:
            self.color = QColor(150, 150, 150)
            
    def boundingRect(self):
        return QRectF(-10, -10, 20, 20)
        
    def paint(self, painter, option, widget):
        # 绘制单元图形
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 绘制主体
        brush = QBrush(self.color)
        painter.setBrush(brush)
        painter.setPen(QPen(Qt.black, 1))
        
        # 根据单元类型绘制不同形状
        if isinstance(self.unit, Warship):
            # 战舰绘制为船形
            painter.drawEllipse(-8, -8, 16, 16)
            # 航向指示器
            painter.drawLine(0, 0, 0, -15)
        elif isinstance(self.unit, Aircraft):
            # 飞机绘制为三角形
            points = [QPointF(0, -10), QPointF(-8, 8), QPointF(8, 8)]
            painter.drawPolygon(points)
        elif isinstance(self.unit, Submarine):
            # 潜艇绘制为椭圆
            painter.drawEllipse(-10, -5, 20, 10)
            
        # 绘制健康状态条
        health_ratio = self.unit.health / self.unit.max_health
        health_width = 20 * health_ratio
        
        if health_ratio > 0.7:
            health_color = QColor(0, 255, 0)
        elif health_ratio > 0.3:
            health_color = QColor(255, 255, 0)
        else:
            health_color = QColor(255, 0, 0)
            
        painter.setBrush(QBrush(health_color))
        painter.setPen(QPen(Qt.black, 1))
        painter.drawRect(-10, -15, int(health_width), 3)
        
        # 绘制名称标签
        painter.setPen(QPen(Qt.white, 1))
        painter.drawText(QRectF(-30, 10, 60, 20), Qt.AlignCenter, self.unit.name)
        
    def update_unit(self, unit):
        self.unit = unit
        self.setPos(unit.position[0], unit.position[1])
        self.update()
        
    def mousePressEvent(self, event):
        self.setSelected(True)
        super().mousePressEvent(event)


class TacticalMarkItem(QGraphicsItem):
    """战术标记图形项"""
    def __init__(self, position, mark_type, text=""):
        super().__init__()
        self.position = position
        self.mark_type = mark_type
        self.text = text
        self.setPos(position[0], position[1])
        
    def boundingRect(self):
        return QRectF(-15, -15, 30, 30)
        
    def paint(self, painter, option, widget):
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QPen(QColor(255, 255, 0), 2))
        
        if self.mark_type == "目标":
            # 绘制目标标记
            painter.drawEllipse(-10, -10, 20, 20)
            painter.drawLine(-10, 0, 10, 0)
            painter.drawLine(0, -10, 0, 10)
        elif self.mark_type == "危险区域":
            # 绘制危险区域标记
            painter.drawEllipse(-15, -15, 30, 30)
            painter.drawLine(-10, -10, 10, 10)
            painter.drawLine(-10, 10, 10, -10)
            
        if self.text:
            painter.drawText(QRectF(-30, 15, 60, 20), Qt.AlignCenter, self.text)


class WaypointLineItem(QGraphicsLineItem):
    """航路点连线项"""
    def __init__(self, start_pos, end_pos, faction):
        super().__init__(start_pos[0], start_pos[1], end_pos[0], end_pos[1])
        
        # 根据阵营设置颜色
        if faction == "蓝方":
            color = QColor(0, 100, 255, 150)
        elif faction == "红方":
            color = QColor(255, 50, 50, 150)
        else:
            color = QColor(150, 150, 150, 150)
            
        pen = QPen(color, 2, Qt.DashLine)
        self.setPen(pen)
        
        self.setZValue(-1)  # 确保在单位下方


# ============================ 战术分析模块 ============================

class TacticalAnalyzer:
    """战术分析器"""
    def __init__(self, scenario):
        self.scenario = scenario
        
    def calculate_threat_level(self, unit):
        """计算单位的威胁等级"""
        threat = 0
        
        # 基于健康状态
        health_factor = unit.health / unit.max_health
        
        # 基于单位类型
        if isinstance(unit, Warship):
            type_factor = 1.0
        elif isinstance(unit, Aircraft):
            type_factor = 1.5
        elif isinstance(unit, Submarine):
            type_factor = 1.2
        else:
            type_factor = 0.5
            
        threat = health_factor * type_factor * 100
        return min(100, threat)
        
    def find_nearest_enemy(self, unit, max_range=500):
        """查找最近的敌方单位"""
        nearest = None
        min_distance = float('inf')
        
        for other_unit in self.scenario.units.values():
            if other_unit.faction != unit.faction and other_unit.health > 0:
                distance = self.calculate_distance(unit.position, other_unit.position)
                if distance < min_distance and distance <= max_range:
                    min_distance = distance
                    nearest = other_unit
                    
        return nearest, min_distance
        
    def calculate_distance(self, pos1, pos2):
        """计算两点之间的距离"""
        return math.sqrt((pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2)
        
    def predict_interception_point(self, interceptor, target, interceptor_speed):
        """预测拦截点"""
        # 简单的线性预测
        target_speed = target.speed
        target_heading = math.radians(target.heading)
        
        # 目标速度向量
        target_vx = target_speed * math.cos(target_heading)
        target_vy = target_speed * math.sin(target_heading)
        
        # 拦截器到目标的向量
        dx = target.position[0] - interceptor.position[0]
        dy = target.position[1] - interceptor.position[1]
        
        # 计算拦截时间（简化模型）
        # 使用相对速度计算拦截时间
        relative_speed = interceptor_speed - target_speed
        if relative_speed <= 0:
            return None  # 无法拦截
            
        time_to_intercept = math.sqrt(dx**2 + dy**2) / relative_speed
        
        # 预测拦截点
        intercept_x = target.position[0] + target_vx * time_to_intercept
        intercept_y = target.position[1] + target_vy * time_to_intercept
        
        return (intercept_x, intercept_y)
        
    def analyze_tactical_situation(self, faction):
        """分析战术态势"""
        friendly_units = self.scenario.get_units_by_faction(faction)
        enemy_units = [u for u in self.scenario.units.values() 
                      if u.faction != faction and u.health > 0]
        
        analysis = {
            'friendly_units': len(friendly_units),
            'enemy_units': len(enemy_units),
            'total_threat': sum(self.calculate_threat_level(u) for u in enemy_units),
            'average_health': sum(u.health for u in friendly_units) / len(friendly_units) if friendly_units else 0,
            'recommendations': [],
            'threat_assessment': {}
        }
        
        # 生成威胁评估
        for enemy in enemy_units:
            nearest_friendly, distance = self.find_nearest_enemy(enemy)
            threat_level = self.calculate_threat_level(enemy)
            analysis['threat_assessment'][enemy.id] = {
                'name': enemy.name,
                'threat_level': threat_level,
                'distance': distance,
                'nearest_friendly': nearest_friendly.name if nearest_friendly else "无"
            }
        
        # 生成战术建议
        if analysis['enemy_units'] > analysis['friendly_units'] * 1.5:
            analysis['recommendations'].append("敌众我寡，建议采取防御态势")
        elif analysis['friendly_units'] > analysis['enemy_units'] * 1.5:
            analysis['recommendations'].append("我众敌寡，建议采取进攻态势")
            
        if analysis['average_health'] < 50:
            analysis['recommendations'].append("我方单位损伤严重，建议撤退维修")
            
        # 添加基于威胁评估的建议
        high_threats = [e for e in enemy_units if self.calculate_threat_level(e) > 70]
        if high_threats:
            analysis['recommendations'].append(f"检测到 {len(high_threats)} 个高威胁目标，建议优先处理")
            
        return analysis


# ============================ 命令对话框 ============================

class UnitCommandDialog(QDialog):
    """单位命令对话框"""
    def __init__(self, unit, parent=None):
        super().__init__(parent)
        self.unit = unit
        self.setWindowTitle(f"命令控制 - {unit.name}")
        self.setModal(True)
        self.resize(400, 300)
        
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 单位信息
        info_group = QGroupBox("单位信息")
        info_layout = QGridLayout()
        
        info_layout.addWidget(QLabel("名称:"), 0, 0)
        info_layout.addWidget(QLabel(self.unit.name), 0, 1)
        
        info_layout.addWidget(QLabel("位置:"), 1, 0)
        info_layout.addWidget(QLabel(f"{self.unit.position[0]:.1f}, {self.unit.position[1]:.1f}"), 1, 1)
        
        info_layout.addWidget(QLabel("健康度:"), 2, 0)
        info_layout.addWidget(QLabel(f"{self.unit.health}/{self.unit.max_health}"), 2, 1)
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # 移动命令
        move_group = QGroupBox("移动命令")
        move_layout = QGridLayout()
        
        move_layout.addWidget(QLabel("目标X:"), 0, 0)
        self.target_x = QDoubleSpinBox()
        self.target_x.setRange(0, 10000)
        self.target_x.setValue(self.unit.position[0])
        move_layout.addWidget(self.target_x, 0, 1)
        
        move_layout.addWidget(QLabel("目标Y:"), 1, 0)
        self.target_y = QDoubleSpinBox()
        self.target_y.setRange(0, 10000)
        self.target_y.setValue(self.unit.position[1])
        move_layout.addWidget(self.target_y, 1, 1)
        
        move_layout.addWidget(QLabel("速度:"), 2, 0)
        self.speed = QDoubleSpinBox()
        self.speed.setRange(0, self.unit.max_speed)
        self.speed.setValue(self.unit.speed)
        move_layout.addWidget(self.speed, 2, 1)
        
        move_group.setLayout(move_layout)
        layout.addWidget(move_group)
        
        # 按钮
        button_layout = QHBoxLayout()
        
        move_btn = QPushButton("移动到目标")
        move_btn.clicked.connect(self.move_to_target)
        button_layout.addWidget(move_btn)
        
        stop_btn = QPushButton("停止移动")
        stop_btn.clicked.connect(self.stop_movement)
        button_layout.addWidget(stop_btn)
        
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
    def move_to_target(self):
        """移动到目标位置"""
        target = (self.target_x.value(), self.target_y.value())
        self.unit.set_destination(target)
        self.unit.speed = self.speed.value()
        self.accept()
        
    def stop_movement(self):
        """停止移动"""
        self.unit.speed = 0
        self.unit.clear_orders()
        self.accept()


# ============================ 主界面 ============================

class BattleCommandSystem(QMainWindow):
    """海战指挥系统主窗口"""
    def __init__(self):
        super().__init__()
        self.scenario = None
        self.communication_server = CommunicationServer()
        self.communication_client = CommunicationClient()
        self.tactical_analyzer = None
        self.simulation_engine = None
        self.selected_unit_id = None
        
        self.init_ui()
        self.init_communication()
        
    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("海战指挥系统")
        self.setGeometry(100, 100, 1400, 900)
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QHBoxLayout(central_widget)
        
        # 左侧面板
        left_panel = self.create_left_panel()
        main_layout.addWidget(left_panel, 1)  # 比例1
        
        # 中央地图区域
        central_area = self.create_central_area()
        main_layout.addWidget(central_area, 3)  # 比例3
        
        # 右侧面板
        right_panel = self.create_right_panel()
        main_layout.addWidget(right_panel, 1)  # 比例1
        
        # 创建菜单栏
        self.create_menubar()
        
        # 创建工具栏
        self.create_toolbar()
        
        # 创建状态栏
        self.statusBar().showMessage("系统就绪")
        
        # 创建定时器用于更新显示
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_display)
        self.update_timer.start(100)  # 每100毫秒更新一次
        
    def create_menubar(self):
        """创建菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu('文件')
        
        new_action = QAction('新建场景', self)
        new_action.setShortcut(QKeySequence.New)
        new_action.triggered.connect(self.new_scenario)
        file_menu.addAction(new_action)
        
        load_action = QAction('加载场景', self)
        load_action.setShortcut(QKeySequence.Open)
        load_action.triggered.connect(self.load_scenario)
        file_menu.addAction(load_action)
        
        save_action = QAction('保存场景', self)
        save_action.setShortcut(QKeySequence.Save)
        save_action.triggered.connect(self.save_scenario)
        file_menu.addAction(save_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction('退出', self)
        exit_action.setShortcut(QKeySequence.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 视图菜单
        view_menu = menubar.addMenu('视图')
        
        toggle_grid_action = QAction('显示网格', self, checkable=True)
        toggle_grid_action.setChecked(True)
        toggle_grid_action.triggered.connect(self.toggle_grid)
        view_menu.addAction(toggle_grid_action)
        
        toggle_coords_action = QAction('显示坐标', self, checkable=True)
        toggle_coords_action.setChecked(True)
        toggle_coords_action.triggered.connect(self.toggle_coordinates)
        view_menu.addAction(toggle_coords_action)
        
        toggle_waypoints_action = QAction('显示航路点', self, checkable=True)
        toggle_waypoints_action.setChecked(True)
        toggle_waypoints_action.triggered.connect(self.toggle_waypoints)
        view_menu.addAction(toggle_waypoints_action)
        
        # 单位菜单
        unit_menu = menubar.addMenu('单位')
        
        add_unit_action = QAction('添加单位', self)
        add_unit_action.triggered.connect(self.add_unit)
        unit_menu.addAction(add_unit_action)
        
        remove_unit_action = QAction('删除单位', self)
        remove_unit_action.triggered.connect(self.remove_unit)
        unit_menu.addAction(remove_unit_action)
        
        # 工具菜单
        tools_menu = menubar.addMenu('工具')
        
        analyze_action = QAction('战术分析', self)
        analyze_action.triggered.connect(self.run_tactical_analysis)
        tools_menu.addAction(analyze_action)
        
        # 模拟菜单
        sim_menu = menubar.addMenu('模拟')
        
        start_sim_action = QAction('开始模拟', self)
        start_sim_action.triggered.connect(self.start_simulation)
        sim_menu.addAction(start_sim_action)
        
        stop_sim_action = QAction('停止模拟', self)
        stop_sim_action.triggered.connect(self.stop_simulation)
        sim_menu.addAction(stop_sim_action)
        
        # 通信菜单
        comm_menu = menubar.addMenu('通信')
        
        start_server_action = QAction('启动服务器', self)
        start_server_action.triggered.connect(self.start_communication_server)
        comm_menu.addAction(start_server_action)
        
        connect_action = QAction('连接服务器', self)
        connect_action.triggered.connect(self.connect_to_server)
        comm_menu.addAction(connect_action)
        
    def create_toolbar(self):
        """创建工具栏"""
        toolbar = QToolBar("主工具栏")
        self.addToolBar(toolbar)
        
        # 添加工具按钮
        new_btn = QAction("新建", self)
        new_btn.triggered.connect(self.new_scenario)
        toolbar.addAction(new_btn)
        
        save_btn = QAction("保存", self)
        save_btn.triggered.connect(self.save_scenario)
        toolbar.addAction(save_btn)
        
        toolbar.addSeparator()
        
        analyze_btn = QAction("分析", self)
        analyze_btn.triggered.connect(self.run_tactical_analysis)
        toolbar.addAction(analyze_btn)
        
        toolbar.addSeparator()
        
        sim_start_btn = QAction("开始模拟", self)
        sim_start_btn.triggered.connect(self.start_simulation)
        toolbar.addAction(sim_start_btn)
        
        sim_stop_btn = QAction("停止模拟", self)
        sim_stop_btn.triggered.connect(self.stop_simulation)
        toolbar.addAction(sim_stop_btn)
        
    def create_left_panel(self):
        """创建左侧面板"""
        left_panel = QWidget()
        layout = QVBoxLayout(left_panel)  # 修复拼写错误
        
        # 单位列表
        units_group = QGroupBox("战斗单位")
        units_layout = QVBoxLayout()
        
        self.units_table = QTableWidget()
        self.units_table.setColumnCount(4)
        self.units_table.setHorizontalHeaderLabels(["ID", "名称", "类型", "状态"])
        self.units_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.units_table.itemSelectionChanged.connect(self.on_unit_selected)
        
        units_layout.addWidget(self.units_table)
        units_group.setLayout(units_layout)
        layout.addWidget(units_group)
        
        # 单位详情
        details_group = QGroupBox("单位详情")
        details_layout = QVBoxLayout()
        
        self.unit_details = QTextEdit()
        self.unit_details.setReadOnly(True)
        details_layout.addWidget(self.unit_details)
        
        # 单位控制按钮
        control_layout = QHBoxLayout()
        
        command_btn = QPushButton("命令控制")
        command_btn.clicked.connect(self.open_unit_command)
        control_layout.addWidget(command_btn)
        
        delete_btn = QPushButton("删除单位")
        delete_btn.clicked.connect(self.delete_selected_unit)
        control_layout.addWidget(delete_btn)
        
        details_layout.addLayout(control_layout)
        details_group.setLayout(details_layout)
        layout.addWidget(details_group)
        
        return left_panel
        
    def create_central_area(self):
        """创建中央区域"""
        central_widget = QWidget()
        layout = QVBoxLayout(central_widget)
        
        # 地图视图
        self.map_view = BattleMapView()
        self.map_view.unit_selected.connect(self.on_map_unit_selected)
        self.map_view.position_clicked.connect(self.on_map_position_clicked)
        self.map_view.context_menu_requested.connect(self.show_map_context_menu)
        layout.addWidget(self.map_view)
        
        # 控制按钮
        control_layout = QHBoxLayout()
        
        zoom_in_btn = QPushButton("放大")
        zoom_in_btn.clicked.connect(self.zoom_in)
        control_layout.addWidget(zoom_in_btn)
        
        zoom_out_btn = QPushButton("缩小")
        zoom_out_btn.clicked.connect(self.zoom_out)
        control_layout.addWidget(zoom_out_btn)
        
        center_btn = QPushButton("居中")
        center_btn.clicked.connect(self.center_map)
        control_layout.addWidget(center_btn)
        
        clear_marks_btn = QPushButton("清除标记")
        clear_marks_btn.clicked.connect(self.clear_tactical_marks)
        control_layout.addWidget(clear_marks_btn)
        
        control_layout.addStretch()
        
        # 模拟控制
        sim_speed_label = QLabel("模拟速度:")
        control_layout.addWidget(sim_speed_label)
        
        self.sim_speed = QDoubleSpinBox()
        self.sim_speed.setRange(0.1, 10.0)
        self.sim_speed.setValue(1.0)
        self.sim_speed.valueChanged.connect(self.change_simulation_speed)
        control_layout.addWidget(self.sim_speed)
        
        layout.addLayout(control_layout)
        
        return central_widget
        
    def create_right_panel(self):
        """创建右侧面板"""
        right_panel = QWidget()
        layout = QVBoxLayout(right_panel)
        
        # 战术信息
        tactical_group = QGroupBox("战术信息")
        tactical_layout = QVBoxLayout()
        
        self.tactical_display = QTextEdit()
        self.tactical_display.setReadOnly(True)
        tactical_layout.addWidget(self.tactical_display)
        
        tactical_group.setLayout(tactical_layout)
        layout.addWidget(tactical_group)
        
        # 事件日志
        events_group = QGroupBox("事件日志")
        events_layout = QVBoxLayout()
        
        self.events_log = QListWidget()
        events_layout.addWidget(self.events_log)
        
        events_group.setLayout(events_layout)
        layout.addWidget(events_group)
        
        # 通信日志
        comm_group = QGroupBox("通信日志")
        comm_layout = QVBoxLayout()
        
        self.comm_log = QTextEdit()
        self.comm_log.setReadOnly(True)
        comm_layout.addWidget(self.comm_log)
        
        comm_group.setLayout(comm_layout)
        layout.addWidget(comm_group)
        
        # 命令输入
        command_group = QGroupBox("命令输入")
        command_layout = QVBoxLayout()
        
        self.command_input = QTextEdit()
        self.command_input.setMaximumHeight(100)
        command_layout.addWidget(self.command_input)
        
        send_btn = QPushButton("发送命令")
        send_btn.clicked.connect(self.send_command)
        command_layout.addWidget(send_btn)
        
        command_group.setLayout(command_layout)
        layout.addWidget(command_group)
        
        return right_panel
        
    def init_communication(self):
        """初始化通信系统"""
        self.communication_server.message_received.connect(self.on_server_message_received)
        self.communication_client.message_received.connect(self.on_client_message_received)
        self.communication_server.client_connected.connect(self.on_client_connected)
        self.communication_server.client_disconnected.connect(self.on_client_disconnected)
        
    def new_scenario(self):
        """创建新场景"""
        self.scenario = BattleScenario("新场景", "海战训练场景")
        self.tactical_analyzer = TacticalAnalyzer(self.scenario)
        
        # 添加示例单位
        warship1 = Warship("ship1", "驱逐舰01", (100, 100), "蓝方", "驱逐舰")
        warship2 = Warship("ship2", "护卫舰01", (200, 150), "蓝方", "护卫舰")
        enemy_ship = Warship("ship3", "敌舰01", (500, 500), "红方", "巡洋舰")
        
        # 添加武器系统
        missile = WeaponSystem("反舰导弹", "导弹", 200, 30)
        warship1.weapons["missile"] = missile
        
        self.scenario.add_unit(warship1)
        self.scenario.add_unit(warship2)
        self.scenario.add_unit(enemy_ship)
        
        self.update_display()
        self.statusBar().showMessage("新场景已创建")
        
    def load_scenario(self):
        """加载场景"""
        filename, _ = QFileDialog.getOpenFileName(self, "加载场景", "", "JSON文件 (*.json)")
        if filename:
            try:
                with open(filename, 'r') as f:
                    data = json.load(f)
                    
                self.scenario = BattleScenario(data['name'], data['description'], tuple(data['size']))
                self.scenario.time = datetime.fromisoformat(data['time'])
                self.scenario.weather = data['weather']
                self.scenario.sea_state = data['sea_state']
                
                # 加载单位
                for uid, unit_data in data['units'].items():
                    if unit_data.get('ship_type'):
                        unit = Warship(uid, unit_data['name'], tuple(unit_data['position']), 
                                     unit_data['faction'], unit_data['ship_type'])
                    elif unit_data.get('aircraft_type'):
                        unit = Aircraft(uid, unit_data['name'], tuple(unit_data['position']), 
                                      unit_data['faction'], unit_data['aircraft_type'])
                    elif unit_data.get('submarine_type'):
                        unit = Submarine(uid, unit_data['name'], tuple(unit_data['position']), 
                                       unit_data['faction'], unit_data['submarine_type'])
                    else:
                        unit = BattleUnit(uid, unit_data['name'], tuple(unit_data['position']), 
                                        unit_data['faction'])
                    
                    unit.health = unit_data['health']
                    unit.speed = unit_data['speed']
                    unit.heading = unit_data['heading']
                    unit.status = unit_data['status']
                    
                    if 'destination' in unit_data and unit_data['destination']:
                        unit.destination = tuple(unit_data['destination'])
                    if 'waypoints' in unit_data:
                        unit.waypoints = [tuple(wp) for wp in unit_data['waypoints']]
                    
                    self.scenario.add_unit(unit)
                    
                self.tactical_analyzer = TacticalAnalyzer(self.scenario)
                self.update_display()
                self.statusBar().showMessage(f"场景已加载: {filename}")
                
            except Exception as e:
                QMessageBox.critical(self, "错误", f"加载场景失败: {str(e)}")
                
    def save_scenario(self):
        """保存场景"""
        if not self.scenario:
            QMessageBox.warning(self, "警告", "没有可保存的场景")
            return
            
        filename, _ = QFileDialog.getSaveFileName(self, "保存场景", "", "JSON文件 (*.json)")
        if filename:
            try:
                with open(filename, 'w') as f:
                    json.dump(self.scenario.to_dict(), f, indent=2)
                    
                self.statusBar().showMessage(f"场景已保存: {filename}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"保存场景失败: {str(e)}")
                
    def update_display(self):
        """更新显示"""
        if not self.scenario:
            return
            
        # 更新地图显示
        self.map_view.update_units(self.scenario.units)
        
        # 更新单位列表
        self.update_units_table()
        
        # 更新战术信息
        self.update_tactical_display()
        
        # 更新事件日志
        self.update_events_log()
        
    def update_units_table(self):
        """更新单位表格"""
        self.units_table.setRowCount(len(self.scenario.units))
        
        for row, (uid, unit) in enumerate(self.scenario.units.items()):
            self.units_table.setItem(row, 0, QTableWidgetItem(uid))
            self.units_table.setItem(row, 1, QTableWidgetItem(unit.name))
            
            if isinstance(unit, Warship):
                unit_type = "战舰"
            elif isinstance(unit, Aircraft):
                unit_type = "飞机"
            elif isinstance(unit, Submarine):
                unit_type = "潜艇"
            else:
                unit_type = "单位"
                
            self.units_table.setItem(row, 2, QTableWidgetItem(unit_type))
            self.units_table.setItem(row, 3, QTableWidgetItem(unit.status))
            
    def update_tactical_display(self):
        """更新战术信息显示"""
        if not self.tactical_analyzer:
            return
            
        analysis = self.tactical_analyzer.analyze_tactical_situation("蓝方")
        
        text = f"""战术态势分析:
        
我方单位: {analysis['friendly_units']}
敌方单位: {analysis['enemy_units']}
总威胁等级: {analysis['total_threat']:.1f}
平均健康度: {analysis['average_health']:.1f}%

威胁评估:
"""
        for enemy_id, threat_info in analysis['threat_assessment'].items():
            text += f"- {threat_info['name']}: 威胁等级 {threat_info['threat_level']:.1f}, 距离 {threat_info['distance']:.1f}\n"

        text += "\n战术建议:\n"
        for rec in analysis['recommendations']:
            text += f"- {rec}\n"
            
        self.tactical_display.setPlainText(text)
        
    def update_events_log(self):
        """更新事件日志"""
        self.events_log.clear()
        
        if not self.scenario:
            return
            
        # 显示最近20个事件
        recent_events = self.scenario.events[-20:]
        for event in recent_events:
            time_str = event['time'].strftime("%H:%M:%S")
            self.events_log.addItem(f"[{time_str}] {event['description']}")
            
        # 滚动到底部
        self.events_log.scrollToBottom()
        
    def on_unit_selected(self):
        """当单位被选中时"""
        selected_items = self.units_table.selectedItems()
        if selected_items:
            unit_id = selected_items[0].text()
            if unit_id in self.scenario.units:
                unit = self.scenario.units[unit_id]
                self.selected_unit_id = unit_id
                self.show_unit_details(unit)
                
    def on_map_unit_selected(self, unit_id):
        """当地图上的单位被选中时"""
        if unit_id in self.scenario.units:
            # 在表格中选中对应行
            for row in range(self.units_table.rowCount()):
                if self.units_table.item(row, 0).text() == unit_id:
                    self.units_table.selectRow(row)
                    break
                    
            unit = self.scenario.units[unit_id]
            self.selected_unit_id = unit_id
            self.show_unit_details(unit)
            
    def on_map_position_clicked(self, position):
        """当地图位置被点击时"""
        # 如果已选择单位，则设置目标位置
        if self.selected_unit_id and self.selected_unit_id in self.scenario.units:
            unit = self.scenario.units[self.selected_unit_id]
            unit.set_destination(position)
            unit.speed = unit.max_speed * 0.5  # 默认以50%最大速度移动
            
            # 添加事件记录
            self.scenario.add_event("移动命令", f"{unit.name} 移动到位置 {position}", unit.id, position)
            
            self.log_communication(f"命令 {unit.name} 移动到位置 {position}")
            
    def show_map_context_menu(self, position, global_pos):
        """显示地图右键菜单"""
        if not self.scenario:
            return
            
        menu = QMenu(self)
        
        # 添加标记动作
        add_mark_action = menu.addAction("添加战术标记")
        add_mark_action.triggered.connect(lambda: self.add_tactical_mark(position))
        
        # 如果已选择单位，添加移动命令
        if self.selected_unit_id:
            move_action = menu.addAction(f"移动选中单位到此")
            move_action.triggered.connect(lambda: self.move_selected_unit(position))
            
        menu.exec_(global_pos)
        
    def add_tactical_mark(self, position):
        """添加战术标记"""
        mark_id = f"mark_{datetime.now().strftime('%H%M%S')}"
        self.map_view.add_tactical_mark(mark_id, position, "目标", f"目标点{mark_id}")
        
        # 记录到通信日志
        self.log_communication(f"在位置 {position} 添加战术标记")
        
    def move_selected_unit(self, position):
        """移动选中单位到指定位置"""
        if self.selected_unit_id and self.selected_unit_id in self.scenario.units:
            unit = self.scenario.units[self.selected_unit_id]
            unit.set_destination(position)
            unit.speed = unit.max_speed * 0.5
            
            # 添加事件记录
            self.scenario.add_event("移动命令", f"{unit.name} 移动到位置 {position}", unit.id, position)
            
            self.log_communication(f"命令 {unit.name} 移动到位置 {position}")
        
    def show_unit_details(self, unit):
        """显示单位详情"""
        details = f"""单位详情:

ID: {unit.id}
名称: {unit.name}
阵营: {unit.faction}
位置: {unit.position}
健康度: {unit.health}/{unit.max_health}
速度: {unit.speed} 节
航向: {unit.heading}°
状态: {unit.status}

"""
        if isinstance(unit, Warship):
            details += f"舰船类型: {unit.ship_type}\n"
            details += f"雷达范围: {unit.radar_range} 公里\n"
            details += f"声纳范围: {unit.sonar_range} 公里\n"
        elif isinstance(unit, Aircraft):
            details += f"飞机类型: {unit.aircraft_type}\n"
            details += f"高度: {unit.altitude} 米\n"
            details += f"燃油: {unit.fuel}%\n"
        elif isinstance(unit, Submarine):
            details += f"潜艇类型: {unit.submarine_type}\n"
            details += f"深度: {unit.depth} 米\n"
            details += f"静默模式: {'是' if unit.silent_mode else '否'}\n"
            
        # 显示武器信息
        if unit.weapons:
            details += "\n武器系统:\n"
            for weapon_name, weapon in unit.weapons.items():
                details += f"- {weapon_name}: 弹药 {weapon.ammunition}, 冷却 {weapon.cooldown:.1f}s\n"
            
        self.unit_details.setPlainText(details)
        
    def open_unit_command(self):
        """打开单位命令对话框"""
        if not self.selected_unit_id or self.selected_unit_id not in self.scenario.units:
            QMessageBox.warning(self, "警告", "请先选择一个单位")
            return
            
        unit = self.scenario.units[self.selected_unit_id]
        dialog = UnitCommandDialog(unit, self)
        dialog.exec_()
        
    def delete_selected_unit(self):
        """删除选中单位"""
        if not self.selected_unit_id or self.selected_unit_id not in self.scenario.units:
            QMessageBox.warning(self, "警告", "请先选择一个单位")
            return
            
        unit = self.scenario.units[self.selected_unit_id]
        reply = QMessageBox.question(self, "确认删除", f"确定要删除单位 {unit.name} 吗？",
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.scenario.remove_unit(self.selected_unit_id)
            self.selected_unit_id = None
            self.update_display()
            
    def add_unit(self):
        """添加新单位"""
        if not self.scenario:
            QMessageBox.warning(self, "警告", "请先创建一个场景")
            return
            
        # 获取单位信息
        name, ok = QInputDialog.getText(self, "添加单位", "单位名称:")
        if not ok or not name:
            return
            
        unit_types = ["战舰", "飞机", "潜艇"]
        unit_type, ok = QInputDialog.getItem(self, "添加单位", "单位类型:", unit_types, 0, False)
        if not ok:
            return
            
        factions = ["蓝方", "红方", "中立"]
        faction, ok = QInputDialog.getItem(self, "添加单位", "阵营:", factions, 0, False)
        if not ok:
            return
            
        # 创建单位
        unit_id = f"unit_{datetime.now().strftime('%H%M%S')}"
        position = (500, 500)  # 默认位置
        
        if unit_type == "战舰":
            ship_types = ["驱逐舰", "护卫舰", "巡洋舰", "航空母舰"]
            ship_type, ok = QInputDialog.getItem(self, "添加战舰", "舰船类型:", ship_types, 0, False)
            if ok:
                unit = Warship(unit_id, name, position, faction, ship_type)
        elif unit_type == "飞机":
            aircraft_types = ["战斗机", "轰炸机", "预警机", "反潜机"]
            aircraft_type, ok = QInputDialog.getItem(self, "添加飞机", "飞机类型:", aircraft_types, 0, False)
            if ok:
                unit = Aircraft(unit_id, name, position, faction, aircraft_type)
        else:  # 潜艇
            submarine_types = ["攻击潜艇", "弹道导弹潜艇", "巡航导弹潜艇"]
            submarine_type, ok = QInputDialog.getItem(self, "添加潜艇", "潜艇类型:", submarine_types, 0, False)
            if ok:
                unit = Submarine(unit_id, name, position, faction, submarine_type)
                
        if unit:
            self.scenario.add_unit(unit)
            self.update_display()
            self.scenario.add_event("单位添加", f"添加单位 {name} ({unit_type})", unit_id, position)
            
    def remove_unit(self):
        """删除单位"""
        self.delete_selected_unit()
        
    def run_tactical_analysis(self):
        """运行战术分析"""
        if not self.tactical_analyzer:
            QMessageBox.warning(self, "警告", "请先创建或加载一个场景")
            return
            
        # 这里可以添加更复杂的分析逻辑
        self.update_tactical_display()
        self.statusBar().showMessage("战术分析完成")
        
    def start_simulation(self):
        """开始模拟"""
        if not self.scenario:
            QMessageBox.warning(self, "警告", "请先创建或加载一个场景")
            return
            
        if self.simulation_engine and self.simulation_engine.isRunning():
            QMessageBox.information(self, "信息", "模拟已在运行中")
            return
            
        self.simulation_engine = SimulationEngine(self.scenario)
        self.simulation_engine.simulation_updated.connect(self.update_display)
        self.simulation_engine.start()
        
        self.statusBar().showMessage("模拟已开始")
        self.scenario.add_event("模拟控制", "模拟开始")
        
    def stop_simulation(self):
        """停止模拟"""
        if self.simulation_engine and self.simulation_engine.isRunning():
            self.simulation_engine.stop()
            self.simulation_engine.wait()
            self.statusBar().showMessage("模拟已停止")
            self.scenario.add_event("模拟控制", "模拟停止")
        else:
            QMessageBox.information(self, "信息", "模拟未在运行中")
            
    def change_simulation_speed(self, speed):
        """改变模拟速度"""
        if self.scenario:
            self.scenario.simulation_speed = speed
            
    def zoom_in(self):
        """放大地图"""
        self.map_view.scale(1.2, 1.2)
        
    def zoom_out(self):
        """缩小地图"""
        self.map_view.scale(1/1.2, 1/1.2)
        
    def center_map(self):
        """居中地图"""
        self.map_view.fitInView(self.map_view.sceneRect(), Qt.KeepAspectRatio)
        
    def clear_tactical_marks(self):
        """清除战术标记"""
        self.map_view.clear_tactical_marks()
        
    def toggle_grid(self, checked):
        """切换网格显示"""
        self.map_view.show_grid = checked
        self.map_view.update()
        
    def toggle_coordinates(self, checked):
        """切换坐标显示"""
        self.map_view.show_coordinates = checked
        self.map_view.update()
        
    def toggle_waypoints(self, checked):
        """切换航路点显示"""
        self.map_view.show_waypoints = checked
        self.update_display()
        
    def start_communication_server(self):
        """启动通信服务器"""
        if self.communication_server.start_server():
            self.statusBar().showMessage(f"通信服务器已启动，端口: {self.communication_server.port}")
            self.log_communication("通信服务器已启动")
        else:
            QMessageBox.critical(self, "错误", "无法启动通信服务器")
            
    def connect_to_server(self):
        """连接到服务器"""
        host, ok = QInputDialog.getText(self, "连接服务器", "服务器地址:", text="localhost")
        if not ok:
            return
            
        port, ok = QInputDialog.getInt(self, "连接服务器", "端口:", value=8888, min=1, max=65535)
        if not ok:
            return
        
        if self.communication_client.connect_to_server(host, port):
            self.statusBar().showMessage(f"已连接到服务器 {host}:{port}")
            self.log_communication(f"已连接到服务器 {host}:{port}")
        else:
            QMessageBox.critical(self, "错误", "无法连接到服务器")
            
    def on_client_connected(self, client_address):
        """当客户端连接时"""
        self.log_communication(f"客户端连接: {client_address}")
        
    def on_client_disconnected(self, client_address):
        """当客户端断开连接时"""
        self.log_communication(f"客户端断开: {client_address}")
            
    def send_command(self):
        """发送命令"""
        command = self.command_input.toPlainText()
        if command:
            # 发送到通信服务器（如果已连接）
            if self.communication_client.socket.state() == QTcpSocket.ConnectedState:
                message = {
                    'type': 'command',
                    'content': command,
                    'timestamp': datetime.now().isoformat()
                }
                self.communication_client.send_message(message)
                
            self.log_communication(f"发送命令: {command}")
            self.command_input.clear()
            
    def on_server_message_received(self, client_address, message):
        """当服务器接收到消息时"""
        self.log_communication(f"来自 {client_address} 的消息: {message.get('content', '')}")
        
    def on_client_message_received(self, message):
        """当客户端接收到消息时"""
        self.log_communication(f"服务器消息: {message.get('content', '')}")
        
    def log_communication(self, message):
        """记录通信日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.comm_log.append(f"[{timestamp}] {message}")


# ============================ 主程序入口 ============================

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 设置应用程序样式
    app.setStyle("Fusion")
    
    # 创建并显示主窗口
    window = BattleCommandSystem()
    window.show()
    
    sys.exit(app.exec_())