import sys
import random
import math
import json
import time
import numpy as np
from collections import deque
from PyQt5.QtCore import Qt, QTimer, QPointF, QRectF, QSize, QTimeLine, QVariantAnimation
from PyQt5.QtGui import (QColor, QPainter, QBrush, QPen, QLinearGradient, QRadialGradient, 
                         QFont, QFontDatabase, QPainterPath, QPixmap, QImage, QIcon, QTransform)
from PyQt5.QtWidgets import (QApplication, QMainWindow, QGraphicsView, QGraphicsScene, 
                             QGraphicsItem, QVBoxLayout, QWidget, QSlider, QLabel, QHBoxLayout, 
                             QGroupBox, QPushButton, QComboBox, QSpinBox, QDoubleSpinBox, 
                             QCheckBox, QTabWidget, QProgressBar, QTextEdit, QFileDialog,
                             QSplitter, QSizePolicy, QFrame, QGridLayout, QToolButton)

class Vehicle(QGraphicsItem):
    """车辆类 - 增强版"""
    def __init__(self, x, y, road, direction, speed, vehicle_type="car", color=None):
        super().__init__()
        self.road = road
        self.direction = direction  # 0: right, 1: down, 2: left, 3: up
        self.speed = speed
        self.max_speed = speed
        self.vehicle_type = vehicle_type
        self.setPos(x, y)
        self.setZValue(10)  # 确保车辆在道路上方
        
        # 车辆尺寸根据类型变化
        self.sizes = {
            "car": (20, 12),
            "bus": (30, 12),
            "truck": (35, 14),
            "emergency": (22, 12)
        }
        
        self.width, self.height = self.sizes[vehicle_type]
        self.corner_radius = 4
        
        # 随机颜色或指定颜色
        if color:
            self.color = color
        else:
            if vehicle_type == "car":
                self.color = QColor(random.randint(50, 255), random.randint(50, 255), random.randint(50, 255))
            elif vehicle_type == "bus":
                self.color = QColor(200, 50, 50)
            elif vehicle_type == "truck":
                self.color = QColor(100, 100, 150)
            elif vehicle_type == "emergency":
                self.color = QColor(255, 50, 50)
        
        # 灯光效果
        self.light_on = False
        self.light_timer = 0
        
        # 科技感元素
        self.glow_effect = 0
        self.glow_direction = 1
        
        # 车辆状态
        self.stopped = False
        self.waiting_time = 0
        self.total_waiting_time = 0
        self.distance_traveled = 0
        
        # 路径规划
        self.path = []
        self.current_path_index = 0
        self.destination = None
        
        # 紧急车辆特殊属性
        self.is_emergency = (vehicle_type == "emergency")
        self.siren_on = False
        self.siren_timer = 0
        
    def boundingRect(self):
        return QRectF(-self.width/2, -self.height/2, self.width, self.height)
    
    def paint(self, painter, option, widget):
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 根据方向旋转
        painter.save()
        painter.translate(self.pos())
        painter.rotate(self.direction * 90)
        
        # 绘制车身
        body = QRectF(-self.width/2, -self.height/2, self.width, self.height)
        
        # 科技感渐变
        gradient = QLinearGradient(-self.width/2, -self.height/2, self.width/2, self.height/2)
        gradient.setColorAt(0, self.color.lighter(150))
        gradient.setColorAt(0.7, self.color)
        gradient.setColorAt(1, self.color.darker(150))
        painter.setBrush(QBrush(gradient))
        
        # 绘制车身形状
        if self.vehicle_type == "bus":
            # 公交车有更长的车身
            painter.drawRoundedRect(body, self.corner_radius, self.corner_radius)
            # 绘制车窗
            painter.setBrush(QBrush(QColor(150, 200, 255, 200)))
            for i in range(3):
                window_rect = QRectF(-self.width/2 + 5 + i*10, -self.height/2+2, 8, self.height/3)
                painter.drawRoundedRect(window_rect, 2, 2)
        elif self.vehicle_type == "truck":
            # 卡车有驾驶室和货箱
            cab_rect = QRectF(-self.width/2, -self.height/2, self.width/2, self.height)
            trailer_rect = QRectF(0, -self.height/2, self.width/2, self.height)
            painter.drawRoundedRect(cab_rect, self.corner_radius, self.corner_radius)
            painter.setBrush(QBrush(self.color.darker(120)))
            painter.drawRect(trailer_rect)
        else:
            # 普通车辆和应急车辆
            painter.drawRoundedRect(body, self.corner_radius, self.corner_radius)
        
        # 绘制车窗
        if self.vehicle_type != "bus":  # 公交车已经绘制了车窗
            painter.setBrush(QBrush(QColor(150, 200, 255, 200)))
            window_rect = QRectF(-self.width/4, -self.height/2+2, self.width/2, self.height/3)
            painter.drawRoundedRect(window_rect, 2, 2)
        
        # 绘制车灯
        light_color = QColor(255, 200, 100) if self.light_on else QColor(100, 100, 100)
        painter.setBrush(QBrush(light_color))
        painter.drawEllipse(int(self.width/2-5), int(-self.height/4), 4, 4)
        painter.drawEllipse(int(self.width/2-5), int(self.height/4-4), 4, 4)
        
        # 绘制尾灯
        tail_color = QColor(255, 50, 50) if self.light_on else QColor(100, 30, 30)
        painter.setBrush(QBrush(tail_color))
        painter.drawEllipse(int(-self.width/2+1), int(-self.height/4), 4, 4)
        painter.drawEllipse(int(-self.width/2+1), int(self.height/4-4), 4, 4)
        
        # 应急车辆的特殊标记
        if self.is_emergency:
            # 闪光灯
            siren_color = QColor(255, 255, 0) if self.siren_on else QColor(100, 100, 100)
            painter.setBrush(QBrush(siren_color))
            painter.drawEllipse(int(-self.width/4), int(-self.height/2-3), 6, 6)
            painter.drawEllipse(int(self.width/4-6), int(-self.height/2-3), 6, 6)
            
            # 条纹
            painter.setBrush(QBrush(QColor(255, 255, 255)))
            for i in range(3):
                stripe_rect = QRectF(-self.width/2 + i*self.width/3, -self.height/2, self.width/6, self.height)
                painter.drawRect(stripe_rect)
        
        # 科技感发光效果
        if self.glow_effect > 0:
            glow_radius = self.glow_effect / 10.0
            glow_gradient = QRadialGradient(0, 0, self.width * glow_radius)
            glow_gradient.setColorAt(0, QColor(100, 200, 255, 100))
            glow_gradient.setColorAt(1, QColor(100, 200, 255, 0))
            painter.setBrush(QBrush(glow_gradient))
            painter.drawEllipse(int(-self.width*glow_radius), int(-self.height*glow_radius), 
                              int(self.width*glow_radius*2), int(self.height*glow_radius*2))
        
        painter.restore()
    
    def advance(self, phase):
        if phase == 0:
            # 更新灯光计时器
            self.light_timer += 1
            if self.light_timer >= 20:
                self.light_on = not self.light_on
                self.light_timer = 0
            
            # 更新应急车辆警报灯
            if self.is_emergency:
                self.siren_timer += 1
                if self.siren_timer >= 10:
                    self.siren_on = not self.siren_on
                    self.siren_timer = 0
            
            # 更新发光效果
            self.glow_effect += self.glow_direction * 0.2
            if self.glow_effect > 5:
                self.glow_effect = 5
                self.glow_direction = -1
            elif self.glow_effect < 0:
                self.glow_effect = 0
                self.glow_direction = 1
            
            # 如果车辆停止，增加等待时间
            if self.stopped:
                self.waiting_time += 1
                self.total_waiting_time += 1
                return
            
            # 检查前方是否有交通灯
            light_ahead = self.check_traffic_light_ahead()
            if light_ahead and light_ahead.state != 2:  # 不是绿灯
                self.stopped = True
                self.waiting_time = 0
                return
            
            # 检查前方是否有车辆
            vehicle_ahead = self.check_vehicle_ahead()
            if vehicle_ahead:
                # 减速或停止
                distance = self.distance_to(vehicle_ahead)
                if distance < 30:  # 安全距离
                    self.stopped = True
                    self.waiting_time = 0
                    return
                elif distance < 50:  # 减速区域
                    self.speed = min(self.speed, vehicle_ahead.speed * 0.8)
            
            # 如果没有停止，恢复速度
            self.stopped = False
            self.speed = min(self.max_speed, self.speed * 1.05)
            
            # 根据方向移动车辆
            dx, dy = 0, 0
            if self.direction == 0:  # right
                dx = self.speed
            elif self.direction == 1:  # down
                dy = self.speed
            elif self.direction == 2:  # left
                dx = -self.speed
            elif self.direction == 3:  # up
                dy = -self.speed
                
            self.setPos(self.x() + dx, self.y() + dy)
            self.distance_traveled += math.sqrt(dx*dx + dy*dy)
            
            # 如果车辆离开道路，则移动到下一段道路或重置位置
            if not self.road.contains(self.pos()):
                self.move_to_next_road()
    
    def check_traffic_light_ahead(self):
        """检查前方是否有交通灯"""
        scene = self.scene()
        if not scene:
            return None
            
        # 根据方向确定检查区域
        check_rect = QRectF(0, 0, 50, 20)
        if self.direction == 0:  # right
            check_rect.moveTopLeft(QPointF(self.width/2, -10))
        elif self.direction == 1:  # down
            check_rect.moveTopLeft(QPointF(-10, self.height/2))
        elif self.direction == 2:  # left
            check_rect.moveTopLeft(QPointF(-self.width/2-50, -10))
        elif self.direction == 3:  # up
            check_rect.moveTopLeft(QPointF(-10, -self.height/2-20))
            
        # 旋转检查区域以匹配车辆方向
        path = QPainterPath()
        path.addRect(check_rect)
        transform = QTransform().translate(self.x(), self.y()).rotate(self.direction * 90)
        check_area = path * transform
        
        # 查找检查区域内的交通灯
        for item in scene.items(check_area.boundingRect()):
            if isinstance(item, TrafficLight) and check_area.contains(item.pos()):
                return item
                
        return None
    
    def check_vehicle_ahead(self):
        """检查前方是否有车辆"""
        scene = self.scene()
        if not scene:
            return None
            
        # 根据方向确定检查区域
        check_distance = 100
        check_width = 20
        check_rect = QRectF(0, 0, check_distance, check_width)
        if self.direction == 0:  # right
            check_rect.moveTopLeft(QPointF(self.width/2, -check_width/2))
        elif self.direction == 1:  # down
            check_rect.moveTopLeft(QPointF(-check_width/2, self.height/2))
        elif self.direction == 2:  # left
            check_rect.moveTopLeft(QPointF(-self.width/2-check_distance, -check_width/2))
        elif self.direction == 3:  # up
            check_rect.moveTopLeft(QPointF(-check_width/2, -self.height/2-check_distance))
            
        # 旋转检查区域以匹配车辆方向
        path = QPainterPath()
        path.addRect(check_rect)
        transform = QTransform().translate(self.x(), self.y()).rotate(self.direction * 90)
        check_area = path * transform
        
        # 查找检查区域内的车辆
        for item in scene.items(check_area.boundingRect()):
            if isinstance(item, Vehicle) and item != self and check_area.contains(item.pos()):
                return item
                
        return None
    
    def distance_to(self, other_vehicle):
        """计算与另一辆车的距离"""
        dx = self.x() - other_vehicle.x()
        dy = self.y() - other_vehicle.y()
        return math.sqrt(dx*dx + dy*dy)
    
    def move_to_next_road(self):
        """移动到下一段道路"""
        if self.path and self.current_path_index < len(self.path) - 1:
            self.current_path_index += 1
            next_road = self.path[self.current_path_index]
            self.road = next_road
            
            # 确定在新道路上的方向
            if self.road.start_point == self.road.end_point:
                return
                
            dx = self.road.end_point.x() - self.road.start_point.x()
            dy = self.road.end_point.y() - self.road.start_point.y()
            
            if abs(dx) > abs(dy):
                self.direction = 0 if dx > 0 else 2
            else:
                self.direction = 1 if dy > 0 else 3
                
            # 将车辆放置在道路起点
            if self.direction == 0 or self.direction == 1:
                self.setPos(self.road.start_point.x(), self.road.start_point.y())
            else:
                self.setPos(self.road.end_point.x(), self.road.end_point.y())
        else:
            # 没有更多路径，重置车辆或移除
            self.reset_position()
    
    def reset_position(self):
        """重置车辆位置到道路起点"""
        if self.direction == 0:  # right
            self.setPos(self.road.start_point.x(), self.road.start_point.y())
        elif self.direction == 1:  # down
            self.setPos(self.road.start_point.x(), self.road.start_point.y())
        elif self.direction == 2:  # left
            self.setPos(self.road.end_point.x(), self.road.end_point.y())
        elif self.direction == 3:  # up
            self.setPos(self.road.end_point.x(), self.road.end_point.y())

class TrafficLight(QGraphicsItem):
    """交通信号灯类"""
    def __init__(self, x, y, orientation):
        super().__init__()
        self.setPos(x, y)
        self.orientation = orientation  # 0: horizontal, 1: vertical
        self.state = 0  # 0: red, 1: yellow, 2: green
        self.timer = 0
        self.cycle = [80, 10, 60]  # 红、黄、绿灯时间
        self.size = 12
        
    def boundingRect(self):
        return QRectF(-self.size, -self.size, self.size*2, self.size*2)
    
    def paint(self, painter, option, widget):
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 绘制灯柱
        painter.setPen(QPen(Qt.gray, 2))
        painter.setBrush(QBrush(QColor(70, 70, 70)))
        painter.drawRect(-3, int(-self.size*1.5), 6, int(self.size*1.5))
        
        # 绘制灯箱
        painter.setBrush(QBrush(QColor(40, 40, 40)))
        painter.drawRoundedRect(-self.size, -self.size, self.size*2, self.size*2, 3, 3)
        
        # 绘制红黄绿灯
        colors = [QColor(Qt.red), QColor(Qt.yellow), QColor(Qt.green)]
        radius = self.size / 2 - 1
        offset = self.size / 2
        
        # 根据方向调整灯的位置
        if self.orientation == 0:  # horizontal
            positions = [(-offset, 0), (0, 0), (offset, 0)]
        else:  # vertical
            positions = [(0, -offset), (0, 0), (0, offset)]
        
        for i, (x, y) in enumerate(positions):
            color = colors[i] if i == self.state else colors[i].darker(400)
            painter.setBrush(QBrush(color))
            painter.drawEllipse(int(x - radius), int(y - radius), int(radius*2), int(radius*2))
            
            # 添加发光效果
            if i == self.state:
                glow_gradient = QRadialGradient(x, y, radius*1.5)
                glow_gradient.setColorAt(0, color.lighter(150))
                glow_gradient.setColorAt(1, QColor(0, 0, 0, 0))
                painter.setBrush(QBrush(glow_gradient))
                painter.drawEllipse(int(x - radius*1.5), int(y - radius*1.5), int(radius*3), int(radius*3))
    
    def advance(self, phase):
        if phase == 0:
            self.timer += 1
            if self.timer >= self.cycle[self.state]:
                self.timer = 0
                self.state = (self.state + 1) % 3
                self.update()

class SmartTrafficLight(TrafficLight):
    """智能交通信号灯类，可以根据交通流量调整信号"""
    def __init__(self, x, y, orientation):
        super().__init__(x, y, orientation)
        self.vehicle_count = [0, 0, 0, 0]  # 四个方向的车辆计数
        self.adaptive_mode = False
        self.max_green_time = 100
        self.min_green_time = 30
        
    def advance(self, phase):
        if phase == 0:
            self.timer += 1
            
            if self.adaptive_mode:
                self.adaptive_control()
            
            if self.timer >= self.cycle[self.state]:
                self.timer = 0
                self.state = (self.state + 1) % 3
                self.update()
    
    def adaptive_control(self):
        """自适应控制信号灯时间"""
        total_vehicles = sum(self.vehicle_count)
        if total_vehicles == 0:
            return
            
        # 计算主要方向
        main_direction = self.vehicle_count.index(max(self.vehicle_count))
        
        # 调整绿灯时间基于交通流量
        green_ratio = self.vehicle_count[main_direction] / total_vehicles
        new_green_time = int(self.min_green_time + (self.max_green_time - self.min_green_time) * green_ratio)
        
        # 更新绿灯时间
        self.cycle[2] = new_green_time
        
        # 重置车辆计数
        self.vehicle_count = [0, 0, 0, 0]
    
    def detect_vehicle(self, direction):
        """检测到车辆，增加对应方向的计数"""
        if 0 <= direction < 4:
            self.vehicle_count[direction] += 1

class Road(QGraphicsItem):
    """道路类 - 增强版"""
    def __init__(self, start_point, end_point, width=40, is_main=False, road_id=None):
        super().__init__()
        self.start_point = start_point
        self.end_point = end_point
        self.width = width
        self.is_main = is_main  # 是否是主干道
        self.road_id = road_id or f"road_{id(self)}"
        self.setPos((start_point.x() + end_point.x())/2, (start_point.y() + end_point.y())/2)
        self.traffic_density = 0  # 交通密度
        self.average_speed = 0    # 平均速度
        self.congestion_level = 0 # 拥堵级别
        
    def boundingRect(self):
        # 计算道路的包围矩形
        length = math.sqrt((self.end_point.x() - self.start_point.x())**2 + 
                          (self.end_point.y() - self.start_point.y())**2)
        return QRectF(-length/2, -self.width/2, length, self.width)
    
    def paint(self, painter, option, widget):
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 计算道路的方向和长度
        start = self.start_point - self.pos()
        end = self.end_point - self.pos()
        length = math.sqrt((end.x() - start.x())**2 + (end.y() - start.y())**2)
        angle = math.atan2(end.y() - start.y(), end.x() - start.x())
        
        painter.save()
        painter.rotate(math.degrees(angle))
        
        # 根据拥堵级别选择道路颜色
        if self.congestion_level > 70:
            road_color = QColor(200, 50, 50)  # 红色表示拥堵
        elif self.congestion_level > 40:
            road_color = QColor(200, 150, 50)  # 黄色表示中等拥堵
        else:
            road_color = QColor(50, 50, 60) if self.is_main else QColor(70, 70, 80)
            
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(road_color))
        painter.drawRect(int(-length/2), int(-self.width/2), int(length), int(self.width))
        
        # 绘制道路标记
        painter.setPen(QPen(Qt.yellow, 1.5, Qt.SolidLine))
        center_line = length / 10
        for i in range(10):
            offset = -length/2 + i * center_line + center_line/2
            painter.drawLine(int(offset), 0, int(offset + center_line/2), 0)
        
        # 绘制道路边缘
        painter.setPen(QPen(QColor(100, 100, 100), 2))
        painter.drawLine(int(-length/2), int(-self.width/2), int(length/2), int(-self.width/2))
        painter.drawLine(int(-length/2), int(self.width/2), int(length/2), int(self.width/2))
        
        # 科技感道路装饰
        if self.is_main:
            painter.setPen(QPen(QColor(0, 200, 255, 100), 1, Qt.DotLine))
            painter.drawLine(int(-length/2), 0, int(length/2), 0)
            
            # 道路上的科技感光点
            painter.setBrush(QBrush(QColor(0, 200, 255)))
            for i in range(15):
                pos = -length/2 + (i + 0.5) * length / 15
                painter.drawEllipse(int(pos - 1), int(-self.width/4), 2, 2)
                painter.drawEllipse(int(pos - 1), int(self.width/4), 2, 2)
        
        # 显示道路ID（调试用）
        if hasattr(widget, 'show_road_ids') and widget.show_road_ids:
            painter.setPen(QPen(Qt.white))
            painter.drawText(0, -self.width/2 - 5, self.road_id)
        
        painter.restore()
    
    def contains(self, point):
        """检查点是否在道路上"""
        # 将点转换到道路的局部坐标系
        local_point = point - self.pos()
        
        # 计算道路的方向向量
        vec = self.end_point - self.start_point
        length = math.sqrt(vec.x()**2 + vec.y()**2)
        if length == 0:
            return False
            
        # 计算点到道路起点的向量
        point_vec = local_point - (self.start_point - self.pos())
        
        # 计算投影长度
        t = (point_vec.x() * vec.x() + point_vec.y() * vec.y()) / (length * length)
        
        # 检查投影是否在道路范围内
        if t < 0 or t > 1:
            return False
            
        # 计算投影点
        projection = QPointF(self.start_point.x() + t * vec.x(), 
                           self.start_point.y() + t * vec.y())
        
        # 计算点到投影点的距离
        dist = math.sqrt((local_point.x() - (projection.x() - self.pos().x()))**2 + 
                       (local_point.y() - (projection.y() - self.pos().y()))**2)
        
        return dist <= self.width / 2
    
    def update_traffic_data(self, density, avg_speed):
        """更新交通数据"""
        self.traffic_density = density
        self.average_speed = avg_speed
        self.congestion_level = min(100, density * 2)  # 简化计算拥堵级别
        self.update()

class Intersection(QGraphicsItem):
    """交叉口类"""
    def __init__(self, x, y, size=50):
        super().__init__()
        self.setPos(x, y)
        self.size = size
        self.traffic_lights = []
        
    def boundingRect(self):
        return QRectF(-self.size/2, -self.size/2, self.size, self.size)
    
    def paint(self, painter, option, widget):
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 绘制交叉口基础
        painter.setPen(QPen(QColor(40, 40, 40), 2))
        painter.setBrush(QBrush(QColor(60, 60, 70)))
        painter.drawRect(QRectF(-self.size/2, -self.size/2, self.size, self.size))
        
        # 绘制交叉口标记
        painter.setPen(QPen(QColor(100, 100, 100), 1))
        painter.drawLine(int(-self.size/2), 0, int(self.size/2), 0)
        painter.drawLine(0, int(-self.size/2), 0, int(self.size/2))
        
    def add_traffic_light(self, traffic_light):
        """添加交通信号灯到交叉口"""
        self.traffic_lights.append(traffic_light)

class CityMap(QGraphicsScene):
    """城市地图场景 - 增强版"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSceneRect(-600, -600, 1200, 1200)
        self.setBackgroundBrush(QColor(10, 15, 20))
        
        # 地图元素
        self.roads = []
        self.intersections = []
        self.traffic_lights = []
        self.vehicles = []
        self.buildings = []
        
        # 仿真设置
        self.vehicle_count = 30
        self.max_vehicles = 100
        self.spawn_rate = 1.0  # 车辆生成率
        self.spawn_timer = 0
        
        # 视图模式
        self.view_mode = "standard"  # standard, heatmap, traffic_flow, night
        self.show_road_ids = False
        
        # 日夜循环
        self.day_night_cycle = 0  # 0-100, 0=正午, 50=午夜
        self.day_night_speed = 0.1  # 日夜变化速度
        
        # 天气效果
        self.weather = "clear"  # clear, rain, snow, fog
        self.weather_intensity = 0  # 0-100
        
        # 创建道路网络
        self.create_road_network()
        
        # 创建交通信号灯
        self.create_traffic_lights()
        
        # 创建建筑物
        self.create_buildings()
        
        # 创建车辆
        self.create_vehicles()
        
        # 创建定时器
        self.timer = QTimer()
        self.timer.timeout.connect(self.advance)
        self.timer.start(50)  # 20 FPS
        
        # 数据收集
        self.simulation_time = 0
        self.data_history = {
            "vehicle_count": [],
            "avg_speed": [],
            "congestion": [],
            "waiting_time": []
        }
        
    def create_road_network(self):
        """创建道路网络"""
        # 清除现有道路
        self.roads.clear()
        
        # 主干道 - 形成网格
        main_road_points = [-500, -300, -100, 100, 300, 500]
        road_id = 1
        
        # 水平主干道
        for y in main_road_points:
            road = Road(QPointF(-500, y), QPointF(500, y), 50, True, f"MR_H_{y}")
            self.addItem(road)
            self.roads.append(road)
            road_id += 1
        
        # 垂直主干道
        for x in main_road_points:
            road = Road(QPointF(x, -500), QPointF(x, 500), 50, True, f"MR_V_{x}")
            self.addItem(road)
            self.roads.append(road)
            road_id += 1
        
        # 次干道 - 填充网格
        secondary_points = [-400, -200, 0, 200, 400]
        
        # 水平次干道
        for y in secondary_points:
            road = Road(QPointF(-500, y), QPointF(500, y), 40, False, f"SR_H_{y}")
            self.addItem(road)
            self.roads.append(road)
            road_id += 1
        
        # 垂直次干道
        for x in secondary_points:
            road = Road(QPointF(x, -500), QPointF(x, 500), 40, False, f"SR_V_{x}")
            self.addItem(road)
            self.roads.append(road)
            road_id += 1
        
        # 创建交叉口
        for x in main_road_points:
            for y in main_road_points:
                intersection = Intersection(x, y)
                self.addItem(intersection)
                self.intersections.append(intersection)
    
    def create_traffic_lights(self):
        """创建交通信号灯"""
        # 清除现有交通灯
        self.traffic_lights.clear()
        
        # 在主干道交叉口放置交通灯
        main_road_points = [-500, -300, -100, 100, 300, 500]
        
        for x in main_road_points:
            for y in main_road_points:
                # 水平方向的交通灯
                h_light = SmartTrafficLight(x, y, 0)
                self.addItem(h_light)
                self.traffic_lights.append(h_light)
                
                # 垂直方向的交通灯
                v_light = SmartTrafficLight(x, y, 1)
                self.addItem(v_light)
                self.traffic_lights.append(v_light)
                
                # 找到对应的交叉口并添加交通灯
                for intersection in self.intersections:
                    if intersection.x() == x and intersection.y() == y:
                        intersection.add_traffic_light(h_light)
                        intersection.add_traffic_light(v_light)
    
    def create_buildings(self):
        """创建建筑物"""
        # 清除现有建筑物
        self.buildings.clear()
        
        # 在道路之间创建建筑物
        building_points = [-450, -350, -250, -150, -50, 50, 150, 250, 350, 450]
        
        for i in range(len(building_points) - 1):
            for j in range(len(building_points) - 1):
                x1, x2 = building_points[i], building_points[i+1]
                y1, y2 = building_points[j], building_points[j+1]
                
                # 检查是否在道路上
                on_road = False
                for road in self.roads:
                    if (abs(road.start_point.x() - x1) < 10 and abs(road.start_point.y() - y1) < 10) or \
                       (abs(road.start_point.x() - x2) < 10 and abs(road.start_point.y() - y2) < 10):
                        on_road = True
                        break
                
                if not on_road:
                    # 创建建筑物
                    building = Building(x1, y1, x2-x1, y2-y1)
                    self.addItem(building)
                    self.buildings.append(building)
    
    def create_vehicles(self):
        """创建车辆"""
        # 清除现有车辆
        self.vehicles.clear()
        
        # 创建初始车辆
        for _ in range(self.vehicle_count):
            self.spawn_vehicle()
    
    def spawn_vehicle(self):
        """生成一辆新车"""
        if len(self.vehicles) >= self.max_vehicles:
            return
            
        # 随机选择一条道路
        road = random.choice(self.roads)
        
        # 随机选择方向
        direction = random.randint(0, 1)
        
        # 随机选择车辆类型
        vehicle_types = ["car", "car", "car", "car", "bus", "truck"]  # 小汽车更常见
        if random.random() < 0.05:  # 5%的概率生成应急车辆
            vehicle_type = "emergency"
        else:
            vehicle_type = random.choice(vehicle_types)
        
        # 设置车辆速度
        if vehicle_type == "car":
            speed = random.uniform(2.0, 4.0)
        elif vehicle_type == "bus":
            speed = random.uniform(1.5, 3.0)
        elif vehicle_type == "truck":
            speed = random.uniform(1.0, 2.5)
        else:  # emergency
            speed = random.uniform(3.0, 5.0)
        
        # 确定起始位置
        if direction == 0:
            start_x = road.start_point.x()
            start_y = road.start_point.y()
        else:
            start_x = road.end_point.x()
            start_y = road.end_point.y()
        
        # 创建车辆
        vehicle = Vehicle(start_x, start_y, road, direction, speed, vehicle_type)
        self.addItem(vehicle)
        self.vehicles.append(vehicle)
        
        # 为车辆生成路径
        self.generate_path_for_vehicle(vehicle)
    
    def generate_path_for_vehicle(self, vehicle):
        """为车辆生成行驶路径"""
        # 简单实现：随机选择3-5条道路作为路径
        path_length = random.randint(3, 5)
        vehicle.path = [vehicle.road]
        
        for _ in range(path_length - 1):
            # 找到与当前道路相连的道路
            connected_roads = self.find_connected_roads(vehicle.path[-1])
            if connected_roads:
                next_road = random.choice(connected_roads)
                vehicle.path.append(next_road)
            else:
                break
        
        # 设置目的地
        if vehicle.path:
            last_road = vehicle.path[-1]
            vehicle.destination = (last_road.end_point.x(), last_road.end_point.y())
    
    def find_connected_roads(self, road):
        """找到与给定道路相连的道路"""
        connected_roads = []
        
        for other_road in self.roads:
            if other_road == road:
                continue
                
            # 检查道路是否相连（有共同的端点）
            if (road.start_point == other_road.start_point or
                road.start_point == other_road.end_point or
                road.end_point == other_road.start_point or
                road.end_point == other_road.end_point):
                connected_roads.append(other_road)
                
        return connected_roads
    
    def advance(self):
        """推进场景中所有元素的状态"""
        # 更新仿真时间
        self.simulation_time += 1
        
        # 更新日夜循环
        self.day_night_cycle = (self.day_night_cycle + self.day_night_speed) % 100
        
        # 更新背景颜色基于日夜时间
        if self.day_night_cycle < 25:  # 白天
            intensity = 255 * (self.day_night_cycle / 25)
            bg_color = QColor(int(10 + intensity), int(15 + intensity), int(20 + intensity))
        elif self.day_night_cycle < 50:  # 傍晚到夜晚
            intensity = 255 * (1 - (self.day_night_cycle - 25) / 25)
            bg_color = QColor(int(10 + intensity), int(15 + intensity), int(20 + intensity))
        elif self.day_night_cycle < 75:  # 夜晚
            intensity = 0
            bg_color = QColor(10, 15, 20)
        else:  # 夜晚到早晨
            intensity = 255 * ((self.day_night_cycle - 75) / 25)
            bg_color = QColor(int(10 + intensity), int(15 + intensity), int(20 + intensity))
            
        self.setBackgroundBrush(bg_color)
        
        # 生成新车辆
        self.spawn_timer += 1
        if self.spawn_timer >= 100 / self.spawn_rate:
            self.spawn_timer = 0
            self.spawn_vehicle()
        
        # 更新所有元素
        for item in self.items():
            if isinstance(item, (Vehicle, TrafficLight)):
                item.advance(0)
                item.advance(1)
        
        # 收集数据
        self.collect_data()
        
        # 更新道路交通数据
        self.update_road_traffic_data()
        
        # 触发视图更新
        self.update()
    
    def collect_data(self):
        """收集仿真数据"""
        vehicle_count = len(self.vehicles)
        
        if vehicle_count > 0:
            avg_speed = sum(vehicle.speed for vehicle in self.vehicles) / vehicle_count
            avg_waiting = sum(vehicle.total_waiting_time for vehicle in self.vehicles) / vehicle_count
        else:
            avg_speed = 0
            avg_waiting = 0
            
        # 计算整体拥堵指数
        congestion = 0
        if self.roads:
            road_congestion = sum(road.congestion_level for road in self.roads) / len(self.roads)
            congestion = min(100, road_congestion + (vehicle_count / self.max_vehicles) * 50)
        
        # 保存历史数据
        self.data_history["vehicle_count"].append(vehicle_count)
        self.data_history["avg_speed"].append(avg_speed)
        self.data_history["congestion"].append(congestion)
        self.data_history["waiting_time"].append(avg_waiting)
        
        # 保持数据历史长度
        max_history = 1000
        for key in self.data_history:
            if len(self.data_history[key]) > max_history:
                self.data_history[key] = self.data_history[key][-max_history:]
    
    def update_road_traffic_data(self):
        """更新道路交通数据"""
        for road in self.roads:
            # 计算道路上的车辆数量
            vehicles_on_road = 0
            total_speed = 0
            
            for vehicle in self.vehicles:
                if vehicle.road == road:
                    vehicles_on_road += 1
                    total_speed += vehicle.speed
            
            # 计算道路长度
            length = math.sqrt((road.end_point.x() - road.start_point.x())**2 + 
                             (road.end_point.y() - road.start_point.y())**2)
            
            # 计算交通密度（车辆/单位长度）
            density = vehicles_on_road / length if length > 0 else 0
            
            # 计算平均速度
            avg_speed = total_speed / vehicles_on_road if vehicles_on_road > 0 else 0
            
            # 更新道路数据
            road.update_traffic_data(density, avg_speed)
    
    def set_view_mode(self, mode):
        """设置视图模式"""
        self.view_mode = mode
        self.update()
    
    def set_weather(self, weather, intensity):
        """设置天气效果"""
        self.weather = weather
        self.weather_intensity = intensity
        self.update()

class Building(QGraphicsItem):
    """建筑物类"""
    def __init__(self, x, y, width, height):
        super().__init__()
        self.setPos(x, y)
        self.width = width
        self.height = height
        self.color = QColor(random.randint(50, 150), random.randint(50, 150), random.randint(50, 150))
        self.window_color = QColor(200, 200, 100)
        self.window_light_on = random.random() > 0.5  # 随机决定窗户是否亮灯
        
    def boundingRect(self):
        return QRectF(-self.width/2, -self.height/2, self.width, self.height)
    
    def paint(self, painter, option, widget):
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 绘制建筑主体
        painter.setPen(QPen(QColor(30, 30, 40), 2))
        painter.setBrush(QBrush(self.color))
        painter.drawRect(QRectF(-self.width/2, -self.height/2, self.width, self.height))
        
        # 绘制窗户
        painter.setPen(Qt.NoPen)
        window_size = min(self.width, self.height) / 10
        window_spacing = window_size * 2
        
        for i in range(int(self.width / window_spacing) - 1):
            for j in range(int(self.height / window_spacing) - 1):
                x = -self.width/2 + (i + 1) * window_spacing
                y = -self.height/2 + (j + 1) * window_spacing
                
                if self.window_light_on:
                    painter.setBrush(QBrush(self.window_color))
                else:
                    painter.setBrush(QBrush(QColor(40, 40, 60)))
                    
                painter.drawRect(int(x - window_size/2), int(y - window_size/2), 
                               int(window_size), int(window_size))

class TrafficChart(QGraphicsItem):
    """交通数据图表"""
    def __init__(self, x, y, width, height, data_history):
        super().__init__()
        self.setPos(x, y)
        self.width = width
        self.height = height
        self.data_history = data_history
        self.chart_type = "line"  # line, bar
        self.data_key = "vehicle_count"  # vehicle_count, avg_speed, congestion, waiting_time
        
    def boundingRect(self):
        return QRectF(0, 0, self.width, self.height)
    
    def paint(self, painter, option, widget):
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 绘制图表背景
        painter.setPen(QPen(QColor(100, 100, 100)))
        painter.setBrush(QBrush(QColor(30, 35, 40, 200)))
        painter.drawRoundedRect(0, 0, self.width, self.height, 5, 5)
        
        # 绘制标题
        painter.setPen(QPen(Qt.white))
        titles = {
            "vehicle_count": "车辆数量",
            "avg_speed": "平均速度",
            "congestion": "拥堵指数",
            "waiting_time": "平均等待时间"
        }
        painter.drawText(10, 20, titles.get(self.data_key, "数据图表"))
        
        # 绘制坐标轴
        painter.drawLine(50, self.height - 30, self.width - 10, self.height - 30)  # X轴
        painter.drawLine(50, 30, 50, self.height - 30)  # Y轴
        
        # 绘制数据
        if self.data_key in self.data_history and self.data_history[self.data_key]:
            data = self.data_history[self.data_key]
            max_value = max(data) if max(data) > 0 else 1
            min_value = min(data)
            
            # 绘制数据点
            painter.setPen(QPen(QColor(0, 200, 255), 2))
            
            if self.chart_type == "line":
                path = QPainterPath()
                for i, value in enumerate(data[-100:]):  # 只显示最近100个数据点
                    x = 50 + (i / min(100, len(data))) * (self.width - 60)
                    y = self.height - 30 - (value / max_value) * (self.height - 60)
                    
                    if i == 0:
                        path.moveTo(x, y)
                    else:
                        path.lineTo(x, y)
                
                painter.drawPath(path)
                
                # 绘制数据点
                for i, value in enumerate(data[-100:]):
                    x = 50 + (i / min(100, len(data))) * (self.width - 60)
                    y = self.height - 30 - (value / max_value) * (self.height - 60)
                    painter.drawEllipse(int(x-2), int(y-2), 4, 4)
            
            # 绘制数值标签
            painter.setPen(QPen(Qt.white))
            painter.drawText(10, 30, f"最大: {max_value:.1f}")
            painter.drawText(10, 50, f"最小: {min_value:.1f}")
            painter.drawText(10, 70, f"当前: {data[-1]:.1f}")

class CityTrafficSimulator(QMainWindow):
    """城市交通仿真平台主窗口 - 增强版"""
    def __init__(self):
        super().__init__()
        
        # 设置窗口属性
        self.setWindowTitle("城市交通可视化仿真平台 - 增强版")
        self.setGeometry(100, 100, 1600, 900)
        
        # 设置科技感背景
        self.setStyleSheet("background-color: #0a0f14;")
        
        # 加载字体
        self.load_fonts()
        
        # 创建UI
        self.create_ui()
        
        # 创建状态栏
        self.statusBar().showMessage("城市交通仿真系统已启动 | 模拟中...")
        
        # 初始化数据导出
        self.export_data = []
        
    def load_fonts(self):
        """加载字体"""
        self.title_font = QFont("Arial", 18, QFont.Bold)
        self.subtitle_font = QFont("Arial", 14, QFont.Bold)
        self.label_font = QFont("Arial", 10)
        
    def create_ui(self):
        """创建用户界面"""
        # 主布局
        main_widget = QWidget()
        main_layout = QHBoxLayout()
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)
        
        # 左侧控制面板
        control_panel = QGroupBox("控制面板")
        control_panel.setMinimumWidth(300)
        control_panel.setStyleSheet("""
            QGroupBox {
                color: #00ccff;
                font-size: 14px;
                border: 2px solid #00aaff;
                border-radius: 10px;
                margin-top: 1ex;
                background-color: rgba(20, 30, 40, 200);
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        control_layout = QVBoxLayout()
        control_panel.setLayout(control_layout)
        
        # 控制面板内容
        # 标题
        title_label = QLabel("交通仿真控制")
        title_label.setFont(self.title_font)
        title_label.setStyleSheet("color: #00ccff; padding: 10px;")
        title_label.setAlignment(Qt.AlignCenter)
        control_layout.addWidget(title_label)
        
        # 创建选项卡
        control_tabs = QTabWidget()
        control_tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #00aaff;
                border-radius: 5px;
                background-color: rgba(20, 30, 40, 200);
            }
            QTabBar::tab {
                background-color: #1a2a3a;
                color: #ffffff;
                padding: 8px;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
            }
            QTabBar::tab:selected {
                background-color: #004466;
            }
        """)
        
        # 仿真控制选项卡
        sim_tab = QWidget()
        sim_layout = QVBoxLayout()
        sim_tab.setLayout(sim_layout)
        
        # 仿真速度控制
        speed_layout = QHBoxLayout()
        speed_label = QLabel("仿真速度:")
        speed_label.setFont(self.label_font)
        speed_label.setStyleSheet("color: #ffffff;")
        speed_layout.addWidget(speed_label)
        
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setRange(1, 10)
        self.speed_slider.setValue(5)
        self.speed_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #00aaff;
                height: 8px;
                background: #1a2a3a;
                margin: 2px 0;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #00ccff;
                border: 1px solid #00aaff;
                width: 18px;
                margin: -4px 0;
                border-radius: 9px;
            }
        """)
        speed_layout.addWidget(self.speed_slider)
        sim_layout.addLayout(speed_layout)
        
        # 车辆密度控制
        density_layout = QHBoxLayout()
        density_label = QLabel("车辆密度:")
        density_label.setFont(self.label_font)
        density_label.setStyleSheet("color: #ffffff;")
        density_layout.addWidget(density_label)
        
        self.density_slider = QSlider(Qt.Horizontal)
        self.density_slider.setRange(1, 100)
        self.density_slider.setValue(30)
        self.density_slider.setStyleSheet(self.speed_slider.styleSheet())
        density_layout.addWidget(self.density_slider)
        sim_layout.addLayout(density_layout)
        
        # 最大车辆数
        max_vehicles_layout = QHBoxLayout()
        max_vehicles_label = QLabel("最大车辆:")
        max_vehicles_label.setFont(self.label_font)
        max_vehicles_label.setStyleSheet("color: #ffffff;")
        max_vehicles_layout.addWidget(max_vehicles_label)
        
        self.max_vehicles_spin = QSpinBox()
        self.max_vehicles_spin.setRange(10, 500)
        self.max_vehicles_spin.setValue(100)
        self.max_vehicles_spin.setStyleSheet("""
            QSpinBox {
                background-color: #1a2a3a;
                color: #ffffff;
                border: 1px solid #00aaff;
                border-radius: 5px;
                padding: 3px;
            }
        """)
        max_vehicles_layout.addWidget(self.max_vehicles_spin)
        sim_layout.addLayout(max_vehicles_layout)
        
        # 视图模式
        view_layout = QHBoxLayout()
        view_label = QLabel("视图模式:")
        view_label.setFont(self.label_font)
        view_label.setStyleSheet("color: #ffffff;")
        view_layout.addWidget(view_label)
        
        self.view_combo = QComboBox()
        self.view_combo.addItems(["标准视图", "热力图", "交通流分析", "夜间模式"])
        self.view_combo.setStyleSheet("""
            QComboBox {
                background-color: #1a2a3a;
                color: #ffffff;
                border: 1px solid #00aaff;
                border-radius: 5px;
                padding: 3px;
            }
        """)
        view_layout.addWidget(self.view_combo)
        sim_layout.addLayout(view_layout)
        
        # 显示道路ID
        self.show_road_ids_cb = QCheckBox("显示道路ID")
        self.show_road_ids_cb.setFont(self.label_font)
        self.show_road_ids_cb.setStyleSheet("color: #ffffff;")
        sim_layout.addWidget(self.show_road_ids_cb)
        
        # 控制按钮
        button_layout = QHBoxLayout()
        self.start_btn = QPushButton("开始仿真")
        self.pause_btn = QPushButton("暂停")
        self.reset_btn = QPushButton("重置")
        
        for btn in [self.start_btn, self.pause_btn, self.reset_btn]:
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #004466;
                    color: #ffffff;
                    border: 1px solid #00aaff;
                    border-radius: 5px;
                    padding: 8px;
                }
                QPushButton:hover {
                    background-color: #006688;
                }
                QPushButton:pressed {
                    background-color: #002244;
                }
            """)
            button_layout.addWidget(btn)
        
        sim_layout.addLayout(button_layout)
        sim_layout.addStretch()
        
        # 环境控制选项卡
        env_tab = QWidget()
        env_layout = QVBoxLayout()
        env_tab.setLayout(env_layout)
        
        # 日夜循环控制
        day_night_layout = QHBoxLayout()
        day_night_label = QLabel("日夜循环:")
        day_night_label.setFont(self.label_font)
        day_night_label.setStyleSheet("color: #ffffff;")
        day_night_layout.addWidget(day_night_label)
        
        self.day_night_slider = QSlider(Qt.Horizontal)
        self.day_night_slider.setRange(0, 100)
        self.day_night_slider.setValue(10)
        self.day_night_slider.setStyleSheet(self.speed_slider.styleSheet())
        day_night_layout.addWidget(self.day_night_slider)
        env_layout.addLayout(day_night_layout)
        
        # 天气控制
        weather_layout = QHBoxLayout()
        weather_label = QLabel("天气:")
        weather_label.setFont(self.label_font)
        weather_label.setStyleSheet("color: #ffffff;")
        weather_layout.addWidget(weather_label)
        
        self.weather_combo = QComboBox()
        self.weather_combo.addItems(["晴朗", "雨天", "雪天", "雾天"])
        self.weather_combo.setStyleSheet(self.view_combo.styleSheet())
        weather_layout.addWidget(self.weather_combo)
        env_layout.addLayout(weather_layout)
        
        # 天气强度
        weather_intensity_layout = QHBoxLayout()
        weather_intensity_label = QLabel("天气强度:")
        weather_intensity_label.setFont(self.label_font)
        weather_intensity_label.setStyleSheet("color: #ffffff;")
        weather_intensity_layout.addWidget(weather_intensity_label)
        
        self.weather_intensity_slider = QSlider(Qt.Horizontal)
        self.weather_intensity_slider.setRange(0, 100)
        self.weather_intensity_slider.setValue(0)
        self.weather_intensity_slider.setStyleSheet(self.speed_slider.styleSheet())
        weather_intensity_layout.addWidget(self.weather_intensity_slider)
        env_layout.addLayout(weather_intensity_layout)
        
        env_layout.addStretch()
        
        # 交通控制选项卡
        traffic_tab = QWidget()
        traffic_layout = QVBoxLayout()
        traffic_tab.setLayout(traffic_layout)
        
        # 智能交通灯控制
        adaptive_lights_layout = QHBoxLayout()
        self.adaptive_lights_cb = QCheckBox("智能交通信号灯")
        self.adaptive_lights_cb.setFont(self.label_font)
        self.adaptive_lights_cb.setStyleSheet("color: #ffffff;")
        self.adaptive_lights_cb.setChecked(True)
        adaptive_lights_layout.addWidget(self.adaptive_lights_cb)
        traffic_layout.addLayout(adaptive_lights_layout)
        
        # 应急车辆生成率
        emergency_layout = QHBoxLayout()
        emergency_label = QLabel("应急车辆:")
        emergency_label.setFont(self.label_font)
        emergency_label.setStyleSheet("color: #ffffff;")
        emergency_layout.addWidget(emergency_label)
        
        self.emergency_spin = QDoubleSpinBox()
        self.emergency_spin.setRange(0, 20)
        self.emergency_spin.setValue(5)
        self.emergency_spin.setSuffix("%")
        self.emergency_spin.setStyleSheet(self.max_vehicles_spin.styleSheet())
        emergency_layout.addWidget(self.emergency_spin)
        traffic_layout.addLayout(emergency_layout)
        
        # 交通事故模拟
        accident_layout = QHBoxLayout()
        self.accident_cb = QCheckBox("模拟交通事故")
        self.accident_cb.setFont(self.label_font)
        self.accident_cb.setStyleSheet("color: #ffffff;")
        accident_layout.addWidget(self.accident_cb)
        traffic_layout.addLayout(accident_layout)
        
        # 事故发生率
        accident_rate_layout = QHBoxLayout()
        accident_rate_label = QLabel("事故发生率:")
        accident_rate_label.setFont(self.label_font)
        accident_rate_label.setStyleSheet("color: #ffffff;")
        accident_rate_layout.addWidget(accident_rate_label)
        
        self.accident_rate_spin = QDoubleSpinBox()
        self.accident_rate_spin.setRange(0, 10)
        self.accident_rate_spin.setValue(1)
        self.accident_rate_spin.setSuffix("%")
        self.accident_rate_spin.setStyleSheet(self.max_vehicles_spin.styleSheet())
        accident_rate_layout.addWidget(self.accident_rate_spin)
        traffic_layout.addLayout(accident_rate_layout)
        
        traffic_layout.addStretch()
        
        # 数据选项卡
        data_tab = QWidget()
        data_layout = QVBoxLayout()
        data_tab.setLayout(data_layout)
        
        # 数据导出按钮
        export_layout = QHBoxLayout()
        self.export_btn = QPushButton("导出数据")
        self.export_btn.setStyleSheet(self.start_btn.styleSheet())
        export_layout.addWidget(self.export_btn)
        
        self.clear_data_btn = QPushButton("清除数据")
        self.clear_data_btn.setStyleSheet(self.start_btn.styleSheet())
        export_layout.addWidget(self.clear_data_btn)
        data_layout.addLayout(export_layout)
        
        # 数据记录控制
        record_layout = QHBoxLayout()
        self.record_data_cb = QCheckBox("记录数据")
        self.record_data_cb.setFont(self.label_font)
        self.record_data_cb.setStyleSheet("color: #ffffff;")
        self.record_data_cb.setChecked(True)
        record_layout.addWidget(self.record_data_cb)
        data_layout.addLayout(record_layout)
        
        data_layout.addStretch()
        
        # 添加选项卡
        control_tabs.addTab(sim_tab, "仿真控制")
        control_tabs.addTab(env_tab, "环境设置")
        control_tabs.addTab(traffic_tab, "交通控制")
        control_tabs.addTab(data_tab, "数据管理")
        
        control_layout.addWidget(control_tabs)
        
        # 统计信息
        stats_group = QGroupBox("实时统计")
        stats_group.setStyleSheet(control_panel.styleSheet())
        stats_layout = QVBoxLayout()
        stats_group.setLayout(stats_layout)
        
        self.stats_labels = {}
        stats = ["车辆总数", "平均速度", "拥堵指数", "平均等待时间", "仿真时间"]
        for stat in stats:
            layout = QHBoxLayout()
            label = QLabel(f"{stat}:")
            label.setFont(self.label_font)
            label.setStyleSheet("color: #ffffff;")
            layout.addWidget(label)
            
            value = QLabel("0")
            value.setFont(self.label_font)
            value.setStyleSheet("color: #00ccff; font-weight: bold;")
            layout.addWidget(value)
            stats_layout.addLayout(layout)
            self.stats_labels[stat] = value
        
        control_layout.addWidget(stats_group)
        
        # 右侧视图区域
        right_widget = QWidget()
        right_layout = QVBoxLayout()
        right_widget.setLayout(right_layout)
        
        # 创建场景和视图
        self.scene = CityMap()
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.Antialiasing, True)
        self.view.setRenderHint(QPainter.SmoothPixmapTransform, True)
        self.view.setRenderHint(QPainter.TextAntialiasing, True)
        self.view.setStyleSheet("border: 2px solid #00aaff; border-radius: 10px; background-color: #0a0f14;")
        self.view.setMinimumSize(800, 600)
        right_layout.addWidget(self.view, 3)
        
        # 图表区域
        charts_widget = QWidget()
        charts_layout = QHBoxLayout()
        charts_widget.setLayout(charts_layout)
        
        # 创建数据图表
        self.charts = {}
        chart_types = ["vehicle_count", "avg_speed", "congestion", "waiting_time"]
        
        for chart_type in chart_types:
            chart = TrafficChart(0, 0, 200, 150, self.scene.data_history)
            chart.data_key = chart_type
            self.scene.addItem(chart)
            self.charts[chart_type] = chart
        
        right_layout.addWidget(charts_widget, 1)
        
        # 添加布局
        main_layout.addWidget(control_panel, 1)
        main_layout.addWidget(right_widget, 3)
        
        # 连接信号
        self.start_btn.clicked.connect(self.start_simulation)
        self.pause_btn.clicked.connect(self.pause_simulation)
        self.reset_btn.clicked.connect(self.reset_simulation)
        self.export_btn.clicked.connect(self.export_data)
        self.clear_data_btn.clicked.connect(self.clear_data)
        
        self.speed_slider.valueChanged.connect(self.update_simulation_speed)
        self.density_slider.valueChanged.connect(self.update_vehicle_density)
        self.max_vehicles_spin.valueChanged.connect(self.update_max_vehicles)
        self.view_combo.currentIndexChanged.connect(self.change_view_mode)
        self.show_road_ids_cb.stateChanged.connect(self.toggle_road_ids)
        
        self.day_night_slider.valueChanged.connect(self.update_day_night_cycle)
        self.weather_combo.currentIndexChanged.connect(self.change_weather)
        self.weather_intensity_slider.valueChanged.connect(self.update_weather_intensity)
        
        self.adaptive_lights_cb.stateChanged.connect(self.toggle_adaptive_lights)
        self.emergency_spin.valueChanged.connect(self.update_emergency_rate)
        self.accident_cb.stateChanged.connect(self.toggle_accident_simulation)
        self.accident_rate_spin.valueChanged.connect(self.update_accident_rate)
        
        # 初始化统计更新定时器
        self.stats_timer = QTimer()
        self.stats_timer.timeout.connect(self.update_stats)
        self.stats_timer.start(1000)
        
        # 初始化数据记录定时器
        self.data_timer = QTimer()
        self.data_timer.timeout.connect(self.record_data)
        self.data_timer.start(5000)  # 每5秒记录一次数据
    
    def start_simulation(self):
        """开始仿真"""
        self.scene.timer.start()
        self.statusBar().showMessage("仿真运行中...")
    
    def pause_simulation(self):
        """暂停仿真"""
        self.scene.timer.stop()
        self.statusBar().showMessage("仿真已暂停")
    
    def reset_simulation(self):
        """重置仿真"""
        # 停止所有定时器
        self.scene.timer.stop()
        
        # 清除所有现有项目
        self.scene.clear()
        
        # 重新初始化场景
        self.scene = CityMap()
        self.view.setScene(self.scene)
        
        # 重新连接信号（当前版本没有这些信号）
        # 如果需要添加信号，可以在这里添加
        
        # 更新状态
        self.statusBar().showMessage("仿真已重置")
        
        # 如果仿真原本是运行的，重新启动
        if hasattr(self, 'sim_status') and self.sim_status.text() == "运行中":
            self.start_simulation()
    
    def update_simulation_speed(self, value):
        """更新仿真速度"""
        # 调整定时器间隔来控制仿真速度
        interval = max(10, 100 - value * 9)  # 值越大，间隔越小，速度越快
        self.scene.timer.setInterval(interval)
    
    def update_vehicle_density(self, value):
        """更新车辆密度"""
        self.scene.spawn_rate = value / 10.0
    
    def update_max_vehicles(self, value):
        """更新最大车辆数"""
        self.scene.max_vehicles = value
    
    def change_view_mode(self, index):
        """更改视图模式"""
        modes = ["standard", "heatmap", "traffic_flow", "night"]
        if 0 <= index < len(modes):
            self.scene.set_view_mode(modes[index])
    
    def toggle_road_ids(self, state):
        """切换道路ID显示"""
        self.scene.show_road_ids = (state == Qt.Checked)
        self.scene.update()
    
    def update_day_night_cycle(self, value):
        """更新日夜循环"""
        self.scene.day_night_cycle = value
        self.scene.update()
    
    def change_weather(self, index):
        """更改天气"""
        weather_types = ["clear", "rain", "snow", "fog"]
        if 0 <= index < len(weather_types):
            self.scene.set_weather(weather_types[index], self.scene.weather_intensity)
    
    def update_weather_intensity(self, value):
        """更新天气强度"""
        self.scene.set_weather(self.scene.weather, value)
    
    def toggle_adaptive_lights(self, state):
        """切换智能交通灯"""
        enabled = (state == Qt.Checked)
        for light in self.scene.traffic_lights:
            if isinstance(light, SmartTrafficLight):
                light.adaptive_mode = enabled
    
    def update_emergency_rate(self, value):
        """更新应急车辆生成率"""
        # 这个值会在生成车辆时使用
        pass
    
    def toggle_accident_simulation(self, state):
        """切换事故模拟"""
        # 实现事故模拟逻辑
        pass
    
    def update_accident_rate(self, value):
        """更新事故发生率"""
        # 实现事故发生率调整
        pass
    
    def export_data(self):
        """导出数据"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出数据", "", "CSV Files (*.csv);;JSON Files (*.json)"
        )
        
        if file_path:
            if file_path.endswith('.csv'):
                self.export_to_csv(file_path)
            elif file_path.endswith('.json'):
                self.export_to_json(file_path)
    
    def export_to_csv(self, file_path):
        """导出数据到CSV"""
        try:
            with open(file_path, 'w') as f:
                f.write("时间,车辆数,平均速度,拥堵指数,平均等待时间\n")
                for i in range(len(self.export_data)):
                    data = self.export_data[i]
                    f.write(f"{i*5},{data['vehicle_count']},{data['avg_speed']:.2f},{data['congestion']:.2f},{data['waiting_time']:.2f}\n")
            
            self.statusBar().showMessage(f"数据已导出到 {file_path}")
        except Exception as e:
            self.statusBar().showMessage(f"导出失败: {str(e)}")
    
    def export_to_json(self, file_path):
        """导出数据到JSON"""
        try:
            with open(file_path, 'w') as f:
                json.dump(self.export_data, f, indent=2)
            
            self.statusBar().showMessage(f"数据已导出到 {file_path}")
        except Exception as e:
            self.statusBar().showMessage(f"导出失败: {str(e)}")
    
    def clear_data(self):
        """清除数据"""
        self.export_data = []
        self.scene.data_history = {
            "vehicle_count": [],
            "avg_speed": [],
            "congestion": [],
            "waiting_time": []
        }
        self.statusBar().showMessage("数据已清除")
    
    def record_data(self):
        """记录数据"""
        if not self.record_data_cb.isChecked():
            return
            
        vehicle_count = len(self.scene.vehicles)
        
        if vehicle_count > 0:
            avg_speed = sum(vehicle.speed for vehicle in self.scene.vehicles) / vehicle_count
            avg_waiting = sum(vehicle.total_waiting_time for vehicle in self.scene.vehicles) / vehicle_count
        else:
            avg_speed = 0
            avg_waiting = 0
            
        congestion = 0
        if self.scene.roads:
            road_congestion = sum(road.congestion_level for road in self.scene.roads) / len(self.scene.roads)
            congestion = min(100, road_congestion + (vehicle_count / self.scene.max_vehicles) * 50)
        
        data_point = {
            "timestamp": time.time(),
            "vehicle_count": vehicle_count,
            "avg_speed": avg_speed,
            "congestion": congestion,
            "waiting_time": avg_waiting
        }
        
        self.export_data.append(data_point)
    
    def update_stats(self):
        """更新统计信息"""
        vehicles = self.scene.vehicles
        vehicle_count = len(vehicles)
        
        if vehicle_count > 0:
            avg_speed = sum(vehicle.speed for vehicle in vehicles) / vehicle_count
            avg_waiting = sum(vehicle.total_waiting_time for vehicle in vehicles) / vehicle_count
        else:
            avg_speed = 0
            avg_waiting = 0
            
        congestion = 0
        if self.scene.roads:
            road_congestion = sum(road.congestion_level for road in self.scene.roads) / len(self.scene.roads)
            congestion = min(100, road_congestion + (vehicle_count / self.scene.max_vehicles) * 50)
        
        self.stats_labels["车辆总数"].setText(str(vehicle_count))
        self.stats_labels["平均速度"].setText(f"{avg_speed:.1f} 像素/帧")
        self.stats_labels["拥堵指数"].setText(f"{congestion:.1f}%")
        self.stats_labels["平均等待时间"].setText(f"{avg_waiting:.1f} 帧")
        self.stats_labels["仿真时间"].setText(f"{self.scene.simulation_time} 帧")
        
        # 更新图表
        for chart in self.charts.values():
            chart.update()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")  # 使用Fusion风格以获得现代外观
    
    # 设置全局样式
    app.setStyleSheet("""
        QMainWindow {
            background-color: #0a0f14;
        }
        QLabel {
            color: #ffffff;
        }
    """)
    
    window = CityTrafficSimulator()
    window.show()
    sys.exit(app.exec_())