import sys
import math
import numpy as np
import json
from PyQt5.QtWidgets import (QApplication, QMainWindow, QGraphicsView, QGraphicsScene, 
                             QToolBar, QAction, QStatusBar, QDockWidget, QListWidget,QGraphicsPathItem,
                             QColorDialog, QSpinBox, QComboBox, QLabel, QSlider, QActionGroup, QGraphicsLineItem,
                             QMessageBox, QFileDialog, QInputDialog, QGraphicsItem,QGraphicsPolygonItem,QGraphicsTextItem,
                             QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QGraphicsEllipseItem,
                             QGroupBox, QTextEdit, QSplitter, QTabWidget, QLineEdit)
from PyQt5.QtGui import (QIcon, QColor, QPen, QBrush, QPixmap, QPainterPath, QFont, 
                         QPainter, QImage, QLinearGradient, QRadialGradient)
from PyQt5.QtCore import Qt, QPointF, QRectF, pyqtSignal, QSize, QLineF, QTimer, QObject

class MilitaryUnit(QGraphicsItem):
    """军事单位基类"""
    def __init__(self, x, y, unit_type, side, name="Unit", parent=None):
        super().__init__(parent)
        self.x = x
        self.y = y
        self.unit_type = unit_type  # 单位类型: infantry, armor, artillery等
        self.side = side  # 红方或蓝方
        self.name = name
        self.selected = False
        self.setPos(x, y)
        self.setFlags(QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemIsMovable)
        
        # 单位属性
        self.health = 100
        self.ammunition = 100
        self.fuel = 100
        self.movement_range = 100
        self.attack_range = 50
        self.visibility_range = 150
        self.speed = 1.0  # 移动速度
        
        # 颜色设置
        self.colors = {
            "red": QColor(255, 0, 0),
            "blue": QColor(0, 0, 255),
            "green": QColor(0, 255, 0),
            "yellow": QColor(255, 255, 0)
        }
        
        # 单位图标
        self.unit_shapes = {
            "infantry": self.draw_infantry,
            "armor": self.draw_armor,
            "artillery": self.draw_artillery,
            "helicopter": self.draw_helicopter,
            "command": self.draw_command,
            "supply": self.draw_supply
        }
        
    def boundingRect(self):
        return QRectF(-25, -25, 50, 50)
    
    def paint(self, painter, option, widget):
        # 绘制单位主体
        color = self.colors.get(self.side, QColor(128, 128, 128))
        painter.setBrush(QBrush(color))
        painter.setPen(QPen(Qt.black, 2))
        
        # 根据单位类型绘制不同形状
        draw_func = self.unit_shapes.get(self.unit_type, self.draw_infantry)
        draw_func(painter)
        
        # 如果被选中，绘制选择框
        if self.selected:
            painter.setPen(QPen(Qt.yellow, 2, Qt.DashLine))
            painter.drawRect(self.boundingRect())
            
        # 绘制单位状态信息
        painter.setPen(QPen(Qt.white))
        painter.setFont(QFont("Arial", 8))
        painter.drawText(-20, -30, f"{self.name}")
        painter.drawText(-20, 40, f"H:{self.health}%")
        
        # 绘制健康状态条
        health_width = int(40 * (self.health / 100))
        painter.setBrush(QBrush(QColor(0, 255, 0)))
        painter.setPen(QPen(Qt.black, 1))
        painter.drawRect(-20, -35, health_width, 5)
        
        # 绘制攻击范围（如果被选中）
        if self.selected:
            painter.setPen(QPen(QColor(255, 0, 0, 100), 1))
            painter.setBrush(QBrush(QColor(255, 0, 0, 50)))
            painter.drawEllipse(-self.attack_range, -self.attack_range, 
                               self.attack_range * 2, self.attack_range * 2)
            
        # 绘制视野范围（如果被选中）
        if self.selected:
            painter.setPen(QPen(QColor(0, 0, 255, 100), 1))
            painter.setBrush(QBrush(QColor(0, 0, 255, 30)))
            painter.drawEllipse(-self.visibility_range, -self.visibility_range, 
                               self.visibility_range * 2, self.visibility_range * 2)
        
    def draw_infantry(self, painter):
        painter.drawEllipse(-10, -10, 20, 20)
        painter.drawLine(0, 10, 0, 20)
        painter.drawLine(-5, 15, 5, 15)
        
    def draw_armor(self, painter):
        painter.drawRect(-15, -10, 30, 20)
        painter.drawRect(-10, -15, 20, 5)
        
    def draw_artillery(self, painter):
        points = [QPointF(-15, -10), QPointF(15, -10), QPointF(0, 15)]
        painter.drawPolygon(points)
        painter.drawLine(0, -10, 0, -20)
        
    def draw_helicopter(self, painter):
        painter.drawEllipse(-15, -5, 30, 10)
        painter.drawEllipse(-5, -15, 10, 30)
        painter.drawLine(-15, 0, -25, 0)
        
    def draw_command(self, painter):
        painter.drawRect(-15, -15, 30, 30)
        painter.drawLine(-15, -15, 15, 15)
        painter.drawLine(-15, 15, 15, -15)
        
    def draw_supply(self, painter):
        painter.drawRect(-15, -10, 30, 20)
        painter.drawEllipse(-5, -15, 10, 10)
        
    def mousePressEvent(self, event):
        # 发出单位被点击的信号
        if event.button() == Qt.LeftButton:
            self.setSelected(True)
            self.scene().views()[0].unit_clicked(self)
        super().mousePressEvent(event)
        
    def set_selected(self, selected):
        self.selected = selected
        self.update()
        
    def get_properties(self):
        return {
            "name": self.name,
            "type": self.unit_type,
            "side": self.side,
            "health": self.health,
            "ammunition": self.ammunition,
            "fuel": self.fuel,
            "movement_range": self.movement_range,
            "attack_range": self.attack_range,
            "visibility_range": self.visibility_range,
            "speed": self.speed,
            "position": (self.x, self.y)
        }
        
    def set_properties(self, properties):
        if "name" in properties:
            self.name = properties["name"]
        if "health" in properties:
            self.health = properties["health"]
        if "ammunition" in properties:
            self.ammunition = properties["ammunition"]
        if "fuel" in properties:
            self.fuel = properties["fuel"]
        if "movement_range" in properties:
            self.movement_range = properties["movement_range"]
        if "attack_range" in properties:
            self.attack_range = properties["attack_range"]
        if "visibility_range" in properties:
            self.visibility_range = properties["visibility_range"]
        if "speed" in properties:
            self.speed = properties["speed"]
        self.update()


class TerrainItem(QGraphicsItem):
    """地形元素类"""
    def __init__(self, x, y, width, height, terrain_type, parent=None):
        super().__init__(parent)
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.terrain_type = terrain_type  # 地形类型: grass, forest, water, mountain等
        self.setPos(x, y)
        
        # 地形颜色
        self.terrain_colors = {
            "grass": QColor(34, 139, 34),
            "forest": QColor(0, 100, 0),
            "water": QColor(65, 105, 225),
            "mountain": QColor(139, 137, 137),
            "road": QColor(210, 180, 140),
            "urban": QColor(128, 128, 128),
            "desert": QColor(210, 180, 140),
            "swamp": QColor(139, 115, 85)
        }
        
        # 地形纹理
        self.terrain_textures = {
            "grass": self.draw_grass_texture,
            "forest": self.draw_forest_texture,
            "water": self.draw_water_texture,
            "mountain": self.draw_mountain_texture,
            "road": self.draw_road_texture,
            "urban": self.draw_urban_texture,
            "desert": self.draw_desert_texture,
            "swamp": self.draw_swamp_texture
        }
        
        # 地形移动难度
        self.movement_difficulty = {
            "grass": 1.0,
            "forest": 1.5,
            "water": 2.0,
            "mountain": 3.0,
            "road": 0.7,
            "urban": 1.2,
            "desert": 1.3,
            "swamp": 2.5
        }
        
        # 地形防御加成
        self.defense_bonus = {
            "grass": 0,
            "forest": 2,
            "water": 0,
            "mountain": 4,
            "road": -1,
            "urban": 3,
            "desert": -1,
            "swamp": 1
        }
        
    def boundingRect(self):
        return QRectF(0, 0, self.width, self.height)
    
    def paint(self, painter, option, widget):
        # 绘制地形底色
        color = self.terrain_colors.get(self.terrain_type, QColor(128, 128, 128))
        painter.setBrush(QBrush(color))
        painter.setPen(QPen(Qt.black, 1))
        painter.drawRect(0, 0, self.width, self.height)
        
        # 绘制地形纹理
        texture_func = self.terrain_textures.get(self.terrain_type, self.draw_grass_texture)
        texture_func(painter, 0, 0, self.width, self.height)
        
        # 绘制地形类型文字
        painter.setPen(QPen(Qt.white))
        painter.setFont(QFont("Arial", 10))
        painter.drawText(5, 15, self.terrain_type)
        
    def draw_grass_texture(self, painter, x, y, width, height):
        painter.setPen(QPen(QColor(0, 200, 0), 1))
        for i in range(0, int(width), 5):
            for j in range(0, int(height), 5):
                if (i + j) % 10 == 0:
                    painter.drawPoint(x + i, y + j)
                    
    def draw_forest_texture(self, painter, x, y, width, height):
        painter.setPen(QPen(QColor(0, 100, 0), 2))
        for i in range(10, int(width), 20):
            for j in range(10, int(height), 20):
                painter.drawEllipse(x + i - 2, y + j - 2, 4, 4)
                
    def draw_water_texture(self, painter, x, y, width, height):
        painter.setPen(QPen(QColor(100, 100, 255), 1))
        for i in range(0, int(width), 8):
            painter.drawLine(x + i, y, x + i, y + height)
            
    def draw_mountain_texture(self, painter, x, y, width, height):
        painter.setPen(QPen(QColor(100, 100, 100), 2))
        for i in range(5, int(width), 15):
            for j in range(5, int(height), 15):
                points = [
                    QPointF(x + i, y + j - 5),
                    QPointF(x + i + 5, y + j),
                    QPointF(x + i, y + j + 5),
                    QPointF(x + i - 5, y + j)
                ]
                painter.drawPolygon(points)
                
    def draw_road_texture(self, painter, x, y, width, height):
        painter.setPen(QPen(QColor(150, 150, 150), 3))
        painter.drawLine(int(x), int(y + height/2), int(x + width), int(y + height/2))
        
    def draw_urban_texture(self, painter, x, y, width, height):
        painter.setPen(QPen(QColor(80, 80, 80), 1))
        for i in range(5, int(width), 10):
            for j in range(5, int(height), 10):
                painter.drawRect(x + i, y + j, 5, 5)
                
    def draw_desert_texture(self, painter, x, y, width, height):
        painter.setPen(QPen(QColor(220, 200, 170), 1))
        for i in range(0, int(width), 4):
            for j in range(0, int(height), 4):
                if (i + j) % 8 == 0:
                    painter.drawPoint(x + i, y + j)
                    
    def draw_swamp_texture(self, painter, x, y, width, height):
        painter.setPen(QPen(QColor(100, 120, 100), 1))
        for i in range(0, int(width), 6):
            painter.drawLine(x + i, y, x + i + 3, y + height)


class BattlefieldView(QGraphicsView):
    """战场视图类"""
    unit_selected = pyqtSignal(MilitaryUnit)
    terrain_added = pyqtSignal(TerrainItem)
    viewport_changed = pyqtSignal(QRectF)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(-1000, -1000, 2000, 2000)
        self.setScene(self.scene)
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        
        # 网格设置
        self.grid_visible = True
        self.grid_size = 50
        
        # 当前工具
        self.current_tool = "select"  # select, unit, terrain, path, measure, line, area
        
        # 当前单位类型和阵营
        self.current_unit_type = "infantry"
        self.current_side = "red"
        self.current_unit_name = "Unit"
        
        # 当前地形类型
        self.current_terrain_type = "grass"
        
        # 路径规划点
        self.path_points = []
        
        # 测量点
        self.measure_points = []
        
        # 线条起点和终点
        self.line_start_point = None
        self.line_end_point = None
        
        # 区域绘制点
        self.area_points = []
        
        # 缩放级别
        self.zoom_level = 0
        
        # 地图背景
        self.background_image = None
        
        # 视野范围
        self.visible_rect = QRectF(-1000, -1000, 2000, 2000)
        
        # 连接场景变化信号
        self.scene.changed.connect(self.on_scene_changed)
        
    def drawBackground(self, painter, rect):
        # 绘制背景
        if self.background_image:
            painter.drawImage(rect, self.background_image, rect)
        else:
            # 使用渐变背景
            gradient = QLinearGradient(rect.topLeft(), rect.bottomRight())
            gradient.setColorAt(0, QColor(100, 100, 200))
            gradient.setColorAt(1, QColor(200, 200, 255))
            painter.fillRect(rect, gradient)
        
        # 绘制网格
        if self.grid_visible:
            painter.setPen(QPen(QColor(180, 180, 180, 100), 1))
            left = int(rect.left()) - (int(rect.left()) % self.grid_size)
            top = int(rect.top()) - (int(rect.top()) % self.grid_size)
            
            # 确保使用浮点数坐标
            for x in range(left, int(rect.right()) + self.grid_size, self.grid_size):
                painter.drawLine(QLineF(x, rect.top(), x, rect.bottom()))
                
            for y in range(top, int(rect.bottom()) + self.grid_size, self.grid_size):
                painter.drawLine(QLineF(rect.left(), y, rect.right(), y))
                
            # 绘制坐标轴
            painter.setPen(QPen(QColor(255, 0, 0), 2))
            painter.drawLine(QLineF(0, rect.top(), 0, rect.bottom()))
            painter.drawLine(QLineF(rect.left(), 0, rect.right(), 0))
    
    def on_scene_changed(self):
        # 更新可见区域
        view_rect = self.mapToScene(self.viewport().rect()).boundingRect()
        if view_rect != self.visible_rect:
            self.visible_rect = view_rect
            self.viewport_changed.emit(view_rect)
    
    def mousePressEvent(self, event):
        scene_pos = self.mapToScene(event.pos())
        
        if event.button() == Qt.LeftButton:
            if self.current_tool == "unit":
                # 放置单位
                unit = MilitaryUnit(scene_pos.x(), scene_pos.y(), 
                                   self.current_unit_type, self.current_side,
                                   self.current_unit_name)
                self.scene.addItem(unit)
                
            elif self.current_tool == "terrain":
                # 放置地形
                terrain = TerrainItem(scene_pos.x(), scene_pos.y(), 
                                     self.grid_size * 2, self.grid_size * 2,
                                     self.current_terrain_type)
                self.scene.addItem(terrain)
                self.terrain_added.emit(terrain)
                
            elif self.current_tool == "path":
                # 添加路径点
                self.path_points.append(scene_pos)
                if len(self.path_points) > 1:
                    self.draw_path()
                    
            elif self.current_tool == "measure":
                # 添加测量点
                self.measure_points.append(scene_pos)
                if len(self.measure_points) > 1:
                    self.draw_measurement()
                    
            elif self.current_tool == "line":
                # 开始绘制线条
                if not self.line_start_point:
                    self.line_start_point = scene_pos
                else:
                    self.line_end_point = scene_pos
                    self.draw_line()
                    
            elif self.current_tool == "area":
                # 添加区域点
                self.area_points.append(scene_pos)
                if len(self.area_points) > 2:
                    self.draw_area()
                    
        elif event.button() == Qt.RightButton:
            # 右键取消当前操作
            if self.current_tool == "path":
                self.clear_path()
            elif self.current_tool == "measure":
                self.clear_measurement()
            elif self.current_tool == "line":
                self.clear_line()
            elif self.current_tool == "area":
                self.clear_area()
                
        super().mousePressEvent(event)
    
    def unit_clicked(self, unit):
        # 取消之前选中的单位
        for item in self.scene.items():
            if isinstance(item, MilitaryUnit) and item != unit:
                item.set_selected(False)
        
        # 选中当前单位
        unit.set_selected(True)
        self.unit_selected.emit(unit)
    
    def draw_path(self):
        # 绘制路径
        path = QPainterPath(self.path_points[0])
        for point in self.path_points[1:]:
            path.lineTo(point)
            
        # 清除之前的路径
        for item in self.scene.items():
            if isinstance(item, QGraphicsPathItem) and item.data(0) == "path":
                self.scene.removeItem(item)
                
        path_item = self.scene.addPath(path, QPen(QColor(255, 165, 0), 3))
        path_item.setData(0, "path")
        path_item.setZValue(-1)  # 确保路径在地形下方
        
        # 计算路径长度
        total_length = 0
        for i in range(len(self.path_points) - 1):
            dx = self.path_points[i+1].x() - self.path_points[i].x()
            dy = self.path_points[i+1].y() - self.path_points[i].y()
            total_length += math.sqrt(dx*dx + dy*dy)
            
        # 显示路径长度
        for item in self.scene.items():
            if isinstance(item, QGraphicsTextItem) and item.data(0) == "path_length":
                self.scene.removeItem(item)
                
        text_item = self.scene.addText(f"Path length: {total_length:.2f}")
        text_item.setPos(self.path_points[0])
        text_item.setData(0, "path_length")
        text_item.setDefaultTextColor(QColor(255, 165, 0))
        
        # 显示路径点标记
        for i, point in enumerate(self.path_points):
            marker = self.scene.addEllipse(point.x() - 3, point.y() - 3, 6, 6, 
                                         QPen(Qt.black), QBrush(QColor(255, 165, 0)))
            marker.setData(0, "path_marker")
            marker.setZValue(1)
            
            number = self.scene.addText(str(i+1))
            number.setPos(point.x() + 5, point.y() - 10)
            number.setData(0, "path_number")
            number.setDefaultTextColor(QColor(255, 165, 0))
    
    def draw_measurement(self):
        # 绘制测量线和距离
        if len(self.measure_points) >= 2:
            # 清除之前的测量
            for item in self.scene.items():
                if isinstance(item, QGraphicsLineItem) and item.data(0) == "measure":
                    self.scene.removeItem(item)
                if isinstance(item, QGraphicsTextItem) and item.data(0) == "measure_text":
                    self.scene.removeItem(item)
                    
            # 绘制测量线
            line = self.scene.addLine(
                self.measure_points[0].x(), self.measure_points[0].y(),
                self.measure_points[1].x(), self.measure_points[1].y(),
                QPen(QColor(0, 255, 0), 2)
            )
            line.setData(0, "measure")
            
            # 计算并显示距离
            dx = self.measure_points[1].x() - self.measure_points[0].x()
            dy = self.measure_points[1].y() - self.measure_points[0].y()
            distance = math.sqrt(dx*dx + dy*dy)
            
            mid_x = (self.measure_points[0].x() + self.measure_points[1].x()) / 2
            mid_y = (self.measure_points[0].y() + self.measure_points[1].y()) / 2
            
            text_item = self.scene.addText(f"{distance:.2f}")
            text_item.setPos(mid_x, mid_y)
            text_item.setData(0, "measure_text")
            text_item.setDefaultTextColor(QColor(0, 255, 0))
            
            # 显示测量点标记
            for i, point in enumerate(self.measure_points):
                marker = self.scene.addEllipse(point.x() - 3, point.y() - 3, 6, 6, 
                                             QPen(Qt.black), QBrush(QColor(0, 255, 0)))
                marker.setData(0, "measure_marker")
                marker.setZValue(1)
    
    def draw_line(self):
        if self.line_start_point and self.line_end_point:
            # 清除之前的线条
            for item in self.scene.items():
                if isinstance(item, QGraphicsLineItem) and item.data(0) == "line":
                    self.scene.removeItem(item)
                    
            # 绘制线条
            line = self.scene.addLine(
                self.line_start_point.x(), self.line_start_point.y(),
                self.line_end_point.x(), self.line_end_point.y(),
                QPen(QColor(255, 0, 255), 2)
            )
            line.setData(0, "line")
            
            # 计算线条长度
            dx = self.line_end_point.x() - self.line_start_point.x()
            dy = self.line_end_point.y() - self.line_start_point.y()
            length = math.sqrt(dx*dx + dy*dy)
            
            # 显示线条长度
            for item in self.scene.items():
                if isinstance(item, QGraphicsTextItem) and item.data(0) == "line_text":
                    self.scene.removeItem(item)
                    
            mid_x = (self.line_start_point.x() + self.line_end_point.x()) / 2
            mid_y = (self.line_start_point.y() + self.line_end_point.y()) / 2
            
            text_item = self.scene.addText(f"Line: {length:.2f}")
            text_item.setPos(mid_x, mid_y)
            text_item.setData(0, "line_text")
            text_item.setDefaultTextColor(QColor(255, 0, 255))
            
            # 重置线条点
            self.line_start_point = None
            self.line_end_point = None
    
    def draw_area(self):
        if len(self.area_points) > 2:
            # 清除之前的区域
            for item in self.scene.items():
                if isinstance(item, QGraphicsPolygonItem) and item.data(0) == "area":
                    self.scene.removeItem(item)
                if isinstance(item, QGraphicsTextItem) and item.data(0) == "area_text":
                    self.scene.removeItem(item)
                    
            # 绘制区域
            polygon = QPainterPath()
            polygon.moveTo(self.area_points[0])
            for point in self.area_points[1:]:
                polygon.lineTo(point)
            polygon.closeSubpath()
            
            area_item = self.scene.addPath(polygon, QPen(QColor(200, 100, 100), 2), 
                                         QBrush(QColor(200, 100, 100, 100)))
            area_item.setData(0, "area")
            area_item.setZValue(-2)  # 确保区域在地形下方
            
            # 计算区域面积
            area = 0
            for i in range(len(self.area_points)):
                x1, y1 = self.area_points[i].x(), self.area_points[i].y()
                x2, y2 = self.area_points[(i+1) % len(self.area_points)].x(), self.area_points[(i+1) % len(self.area_points)].y()
                area += (x1 * y2 - x2 * y1)
            area = abs(area) / 2
            
            # 显示区域面积
            center_x = sum(point.x() for point in self.area_points) / len(self.area_points)
            center_y = sum(point.y() for point in self.area_points) / len(self.area_points)
            
            text_item = self.scene.addText(f"Area: {area:.2f}")
            text_item.setPos(center_x, center_y)
            text_item.setData(0, "area_text")
            text_item.setDefaultTextColor(QColor(200, 100, 100))
            
            # 显示区域点标记
            for i, point in enumerate(self.area_points):
                marker = self.scene.addEllipse(point.x() - 3, point.y() - 3, 6, 6, 
                                             QPen(Qt.black), QBrush(QColor(200, 100, 100)))
                marker.setData(0, "area_marker")
                marker.setZValue(1)
                
                number = self.scene.addText(str(i+1))
                number.setPos(point.x() + 5, point.y() - 10)
                number.setData(0, "area_number")
                number.setDefaultTextColor(QColor(200, 100, 100))
    
    def wheelEvent(self, event):
        # 缩放视图
        if event.angleDelta().y() > 0:
            self.zoom_in()
        else:
            self.zoom_out()
    
    def zoom_in(self):
        if self.zoom_level < 10:
            self.scale(1.2, 1.2)
            self.zoom_level += 1
            
    def zoom_out(self):
        if self.zoom_level > -10:
            self.scale(1/1.2, 1/1.2)
            self.zoom_level -= 1
            
    def clear_path(self):
        # 清除路径
        self.path_points = []
        for item in self.scene.items():
            if (isinstance(item, (QGraphicsPathItem, QGraphicsEllipseItem, QGraphicsTextItem)) and 
                item.data(0) in ["path", "path_marker", "path_number", "path_length"]):
                self.scene.removeItem(item)
                
    def clear_measurement(self):
        # 清除测量
        self.measure_points = []
        for item in self.scene.items():
            if (isinstance(item, (QGraphicsLineItem, QGraphicsEllipseItem, QGraphicsTextItem)) and 
                item.data(0) in ["measure", "measure_marker", "measure_text"]):
                self.scene.removeItem(item)
                
    def clear_line(self):
        # 清除线条
        self.line_start_point = None
        self.line_end_point = None
        for item in self.scene.items():
            if (isinstance(item, (QGraphicsLineItem, QGraphicsTextItem)) and 
                item.data(0) in ["line", "line_text"]):
                self.scene.removeItem(item)
                
    def clear_area(self):
        # 清除区域
        self.area_points = []
        for item in self.scene.items():
            if (isinstance(item, (QGraphicsPathItem, QGraphicsEllipseItem, QGraphicsTextItem)) and 
                item.data(0) in ["area", "area_marker", "area_number", "area_text"]):
                self.scene.removeItem(item)
                
    def set_background_image(self, image_path):
        # 设置背景图片
        self.background_image = QImage(image_path)
        if not self.background_image.isNull():
            self.scene.setSceneRect(QRectF(0, 0, self.background_image.width(), self.background_image.height()))
            self.viewport().update()
            
    def clear_background_image(self):
        # 清除背景图片
        self.background_image = None
        self.scene.setSceneRect(-1000, -1000, 2000, 2000)
        self.viewport().update()


class BattlefieldSandTable(QMainWindow):
    """战场沙盘主窗口"""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("战场沙盘高级工具")
        self.setGeometry(100, 100, 1400, 900)
        
        # 创建视图
        self.view = BattlefieldView()
        self.setCentralWidget(self.view)
        
        # 创建状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪")
        
        # 当前选中的单位
        self.selected_unit = None
        
        # 模拟状态
        self.simulation_running = False
        self.simulation_timer = QTimer()
        self.simulation_timer.timeout.connect(self.update_simulation)
        
        # 初始化UI
        self.init_ui()
        
        # 连接信号和槽
        self.view.unit_selected.connect(self.on_unit_selected)
        self.view.terrain_added.connect(self.on_terrain_added)
        self.view.viewport_changed.connect(self.on_viewport_changed)
        
        # 创建计时器用于状态栏更新
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_status_bar)
        self.status_timer.start(1000)
        
    def init_ui(self):
        # 创建工具栏
        self.create_toolbar()
        
        # 创建侧边栏
        self.create_sidebar()
        
        # 创建菜单栏
        self.create_menubar()
        
    def create_menubar(self):
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu("文件")
        
        new_action = QAction("新建场景", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self.new_scenario)
        file_menu.addAction(new_action)
        
        open_action = QAction("打开场景", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.load_scenario)
        file_menu.addAction(open_action)
        
        save_action = QAction("保存场景", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.save_scenario)
        file_menu.addAction(save_action)
        
        file_menu.addSeparator()
        
        export_action = QAction("导出为图片", self)
        export_action.triggered.connect(self.export_as_image)
        file_menu.addAction(export_action)
        
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
        
        clear_all_action = QAction("清除所有", self)
        clear_all_action.triggered.connect(self.clear_all)
        edit_menu.addAction(clear_all_action)
        
        # 视图菜单
        view_menu = menubar.addMenu("视图")
        
        zoom_in_action = QAction("放大", self)
        zoom_in_action.setShortcut("Ctrl++")
        zoom_in_action.triggered.connect(self.view.zoom_in)
        view_menu.addAction(zoom_in_action)
        
        zoom_out_action = QAction("缩小", self)
        zoom_out_action.setShortcut("Ctrl+-")
        zoom_out_action.triggered.connect(self.view.zoom_out)
        view_menu.addAction(zoom_out_action)
        
        reset_zoom_action = QAction("重置缩放", self)
        reset_zoom_action.setShortcut("Ctrl+0")
        reset_zoom_action.triggered.connect(self.reset_zoom)
        view_menu.addAction(reset_zoom_action)
        
        view_menu.addSeparator()
        
        grid_action = QAction("显示/隐藏网格", self)
        grid_action.setShortcut("Ctrl+G")
        grid_action.triggered.connect(self.toggle_grid)
        view_menu.addAction(grid_action)
        
        # 工具菜单
        tools_menu = menubar.addMenu("工具")
        
        load_bg_action = QAction("加载背景图片", self)
        load_bg_action.triggered.connect(self.load_background_image)
        tools_menu.addAction(load_bg_action)
        
        clear_bg_action = QAction("清除背景图片", self)
        clear_bg_action.triggered.connect(self.view.clear_background_image)
        tools_menu.addAction(clear_bg_action)
        
        tools_menu.addSeparator()
        
        simulate_action = QAction("开始模拟", self)
        simulate_action.triggered.connect(self.start_simulation)
        tools_menu.addAction(simulate_action)
        
        stop_simulate_action = QAction("停止模拟", self)
        stop_simulate_action.triggered.connect(self.stop_simulation)
        tools_menu.addAction(stop_simulate_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu("帮助")
        
        about_action = QAction("关于", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
    def create_toolbar(self):
        # 主工具栏
        toolbar = QToolBar("主工具栏")
        toolbar.setIconSize(QSize(32, 32))
        self.addToolBar(toolbar)
        
        # 选择工具
        select_action = QAction("选择工具", self)
        select_action.setCheckable(True)
        select_action.setChecked(True)
        select_action.triggered.connect(lambda: self.set_tool("select"))
        toolbar.addAction(select_action)
        
        # 单位工具
        unit_action = QAction("单位工具", self)
        unit_action.setCheckable(True)
        unit_action.triggered.connect(lambda: self.set_tool("unit"))
        toolbar.addAction(unit_action)
        
        # 地形工具
        terrain_action = QAction("地形工具", self)
        terrain_action.setCheckable(True)
        terrain_action.triggered.connect(lambda: self.set_tool("terrain"))
        toolbar.addAction(terrain_action)
        
        # 路径规划工具
        path_action = QAction("路径规划", self)
        path_action.setCheckable(True)
        path_action.triggered.connect(lambda: self.set_tool("path"))
        toolbar.addAction(path_action)
        
        # 测量工具
        measure_action = QAction("测量工具", self)
        measure_action.setCheckable(True)
        measure_action.triggered.connect(lambda: self.set_tool("measure"))
        toolbar.addAction(measure_action)
        
        # 线条工具
        line_action = QAction("线条工具", self)
        line_action.setCheckable(True)
        line_action.triggered.connect(lambda: self.set_tool("line"))
        toolbar.addAction(line_action)
        
        # 区域工具
        area_action = QAction("区域工具", self)
        area_action.setCheckable(True)
        area_action.triggered.connect(lambda: self.set_tool("area"))
        toolbar.addAction(area_action)
        
        # 创建按钮组确保单选
        self.tool_actions = QActionGroup(self)
        self.tool_actions.addAction(select_action)
        self.tool_actions.addAction(unit_action)
        self.tool_actions.addAction(terrain_action)
        self.tool_actions.addAction(path_action)
        self.tool_actions.addAction(measure_action)
        self.tool_actions.addAction(line_action)
        self.tool_actions.addAction(area_action)
        self.tool_actions.setExclusive(True)
        
        toolbar.addSeparator()
        
        # 缩放工具
        zoom_in_action = QAction("放大", self)
        zoom_in_action.triggered.connect(self.view.zoom_in)
        toolbar.addAction(zoom_in_action)
        
        zoom_out_action = QAction("缩小", self)
        zoom_out_action.triggered.connect(self.view.zoom_out)
        toolbar.addAction(zoom_out_action)
        
        # 网格显示切换
        grid_action = QAction("显示/隐藏网格", self)
        grid_action.triggered.connect(self.toggle_grid)
        toolbar.addAction(grid_action)
        
        toolbar.addSeparator()
        
        # 清除工具
        clear_path_action = QAction("清除路径", self)
        clear_path_action.triggered.connect(self.view.clear_path)
        toolbar.addAction(clear_path_action)
        
        clear_measure_action = QAction("清除测量", self)
        clear_measure_action.triggered.connect(self.view.clear_measurement)
        toolbar.addAction(clear_measure_action)
        
        clear_line_action = QAction("清除线条", self)
        clear_line_action.triggered.connect(self.view.clear_line)
        toolbar.addAction(clear_line_action)
        
        clear_area_action = QAction("清除区域", self)
        clear_area_action.triggered.connect(self.view.clear_area)
        toolbar.addAction(clear_area_action)
        
        toolbar.addSeparator()
        
        # 模拟控制
        simulate_action = QAction("开始模拟", self)
        simulate_action.triggered.connect(self.start_simulation)
        toolbar.addAction(simulate_action)
        
        stop_simulate_action = QAction("停止模拟", self)
        stop_simulate_action.triggered.connect(self.stop_simulation)
        toolbar.addAction(stop_simulate_action)
        
    def create_sidebar(self):
        # 创建右侧面板
        right_dock = QDockWidget("控制面板", self)
        right_dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        right_dock.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)
        
        # 创建选项卡
        tab_widget = QTabWidget()
        
        # 单位选项卡
        unit_tab = QWidget()
        unit_layout = QVBoxLayout()
        
        # 单位类型选择
        unit_type_group = QGroupBox("单位设置")
        unit_type_layout = QVBoxLayout()
        
        unit_type_label = QLabel("单位类型:")
        self.unit_type_combo = QComboBox()
        self.unit_type_combo.addItems(["infantry", "armor", "artillery", "helicopter", "command", "supply"])
        self.unit_type_combo.currentTextChanged.connect(self.on_unit_type_changed)
        unit_type_layout.addWidget(unit_type_label)
        unit_type_layout.addWidget(self.unit_type_combo)
        
        side_label = QLabel("阵营:")
        self.side_combo = QComboBox()
        self.side_combo.addItems(["red", "blue", "green", "yellow"])
        self.side_combo.currentTextChanged.connect(self.on_side_changed)
        unit_type_layout.addWidget(side_label)
        unit_type_layout.addWidget(self.side_combo)
        
        name_label = QLabel("单位名称:")
        self.unit_name_edit = QLineEdit()
        self.unit_name_edit.setText("Unit")
        self.unit_name_edit.textChanged.connect(self.on_unit_name_changed)
        unit_type_layout.addWidget(name_label)
        unit_type_layout.addWidget(self.unit_name_edit)
        
        unit_type_group.setLayout(unit_type_layout)
        unit_layout.addWidget(unit_type_group)
        
        # 单位属性编辑
        unit_props_group = QGroupBox("单位属性")
        unit_props_layout = QVBoxLayout()
        
        health_label = QLabel("健康值:")
        self.health_spin = QSpinBox()
        self.health_spin.setRange(0, 100)
        self.health_spin.setValue(100)
        self.health_spin.valueChanged.connect(self.on_unit_property_changed)
        unit_props_layout.addWidget(health_label)
        unit_props_layout.addWidget(self.health_spin)
        
        ammo_label = QLabel("弹药量:")
        self.ammo_spin = QSpinBox()
        self.ammo_spin.setRange(0, 100)
        self.ammo_spin.setValue(100)
        self.ammo_spin.valueChanged.connect(self.on_unit_property_changed)
        unit_props_layout.addWidget(ammo_label)
        unit_props_layout.addWidget(self.ammo_spin)
        
        fuel_label = QLabel("燃料:")
        self.fuel_spin = QSpinBox()
        self.fuel_spin.setRange(0, 100)
        self.fuel_spin.setValue(100)
        self.fuel_spin.valueChanged.connect(self.on_unit_property_changed)
        unit_props_layout.addWidget(fuel_label)
        unit_props_layout.addWidget(self.fuel_spin)
        
        speed_label = QLabel("速度:")
        self.speed_spin = QSpinBox()
        self.speed_spin.setRange(1, 10)
        self.speed_spin.setValue(1)
        self.speed_spin.valueChanged.connect(self.on_unit_property_changed)
        unit_props_layout.addWidget(speed_label)
        unit_props_layout.addWidget(self.speed_spin)
        
        attack_range_label = QLabel("攻击范围:")
        self.attack_range_spin = QSpinBox()
        self.attack_range_spin.setRange(10, 200)
        self.attack_range_spin.setValue(50)
        self.attack_range_spin.valueChanged.connect(self.on_unit_property_changed)
        unit_props_layout.addWidget(attack_range_label)
        unit_props_layout.addWidget(self.attack_range_spin)
        
        visibility_range_label = QLabel("视野范围:")
        self.visibility_range_spin = QSpinBox()
        self.visibility_range_spin.setRange(10, 300)
        self.visibility_range_spin.setValue(150)
        self.visibility_range_spin.valueChanged.connect(self.on_unit_property_changed)
        unit_props_layout.addWidget(visibility_range_label)
        unit_props_layout.addWidget(self.visibility_range_spin)
        
        unit_props_group.setLayout(unit_props_layout)
        unit_layout.addWidget(unit_props_group)
        
        # 单位操作按钮
        unit_buttons_layout = QHBoxLayout()
        
        delete_unit_btn = QPushButton("删除单位")
        delete_unit_btn.clicked.connect(self.delete_selected_unit)
        unit_buttons_layout.addWidget(delete_unit_btn)
        
        clone_unit_btn = QPushButton("克隆单位")
        clone_unit_btn.clicked.connect(self.clone_selected_unit)
        unit_buttons_layout.addWidget(clone_unit_btn)
        
        unit_layout.addLayout(unit_buttons_layout)
        
        unit_tab.setLayout(unit_layout)
        tab_widget.addTab(unit_tab, "单位")
        
        # 地形选项卡
        terrain_tab = QWidget()
        terrain_layout = QVBoxLayout()
        
        terrain_type_label = QLabel("地形类型:")
        self.terrain_type_combo = QComboBox()
        self.terrain_type_combo.addItems(["grass", "forest", "water", "mountain", "road", "urban", "desert", "swamp"])
        self.terrain_type_combo.currentTextChanged.connect(self.on_terrain_type_changed)
        terrain_layout.addWidget(terrain_type_label)
        terrain_layout.addWidget(self.terrain_type_combo)
        
        terrain_size_label = QLabel("地形大小:")
        self.terrain_size_spin = QSpinBox()
        self.terrain_size_spin.setRange(10, 200)
        self.terrain_size_spin.setValue(100)
        self.terrain_size_spin.setSingleStep(10)
        terrain_layout.addWidget(terrain_size_label)
        terrain_layout.addWidget(self.terrain_size_spin)
        
        terrain_tab.setLayout(terrain_layout)
        tab_widget.addTab(terrain_tab, "地形")
        
        # 视图选项卡
        view_tab = QWidget()
        view_layout = QVBoxLayout()
        
        bg_image_btn = QPushButton("加载背景图片")
        bg_image_btn.clicked.connect(self.load_background_image)
        view_layout.addWidget(bg_image_btn)
        
        clear_bg_btn = QPushButton("清除背景图片")
        clear_bg_btn.clicked.connect(self.view.clear_background_image)
        view_layout.addWidget(clear_bg_btn)
        
        view_layout.addStretch()
        
        view_tab.setLayout(view_layout)
        tab_widget.addTab(view_tab, "视图")
        
        # 模拟选项卡
        simulation_tab = QWidget()
        simulation_layout = QVBoxLayout()
        
        simulation_group = QGroupBox("模拟设置")
        simulation_group_layout = QVBoxLayout()
        
        simulation_speed_label = QLabel("模拟速度:")
        self.simulation_speed_slider = QSlider(Qt.Horizontal)
        self.simulation_speed_slider.setRange(1, 10)
        self.simulation_speed_slider.setValue(5)
        simulation_group_layout.addWidget(simulation_speed_label)
        simulation_group_layout.addWidget(self.simulation_speed_slider)
        
        simulation_group.setLayout(simulation_group_layout)
        simulation_layout.addWidget(simulation_group)
        
        simulation_buttons_layout = QHBoxLayout()
        
        start_sim_btn = QPushButton("开始模拟")
        start_sim_btn.clicked.connect(self.start_simulation)
        simulation_buttons_layout.addWidget(start_sim_btn)
        
        stop_sim_btn = QPushButton("停止模拟")
        stop_sim_btn.clicked.connect(self.stop_simulation)
        simulation_buttons_layout.addWidget(stop_sim_btn)
        
        simulation_layout.addLayout(simulation_buttons_layout)
        simulation_layout.addStretch()
        
        simulation_tab.setLayout(simulation_layout)
        tab_widget.addTab(simulation_tab, "模拟")
        
        right_dock.setWidget(tab_widget)
        self.addDockWidget(Qt.RightDockWidgetArea, right_dock)
        
        # 创建底部面板 - 单位列表
        bottom_dock = QDockWidget("单位列表", self)
        bottom_dock.setAllowedAreas(Qt.BottomDockWidgetArea)
        bottom_dock.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)
        
        self.unit_list = QListWidget()
        self.unit_list.itemSelectionChanged.connect(self.on_unit_list_selection_changed)
        bottom_dock.setWidget(self.unit_list)
        
        self.addDockWidget(Qt.BottomDockWidgetArea, bottom_dock)
        
    def set_tool(self, tool):
        self.view.current_tool = tool
        self.status_bar.showMessage(f"当前工具: {tool}")
        
    def toggle_grid(self):
        self.view.grid_visible = not self.view.grid_visible
        self.view.viewport().update()
        
    def reset_zoom(self):
        self.view.resetTransform()
        self.view.zoom_level = 0
        
    def on_unit_type_changed(self, unit_type):
        self.view.current_unit_type = unit_type
        
    def on_side_changed(self, side):
        self.view.current_side = side
        
    def on_terrain_type_changed(self, terrain_type):
        self.view.current_terrain_type = terrain_type
        
    def on_unit_name_changed(self):
        self.view.current_unit_name = self.unit_name_edit.text()
        
    def on_unit_property_changed(self):
        if self.selected_unit:
            properties = {
                "health": self.health_spin.value(),
                "ammunition": self.ammo_spin.value(),
                "fuel": self.fuel_spin.value(),
                "speed": self.speed_spin.value(),
                "attack_range": self.attack_range_spin.value(),
                "visibility_range": self.visibility_range_spin.value()
            }
            self.selected_unit.set_properties(properties)
        
    def on_unit_selected(self, unit):
        self.selected_unit = unit
        self.update_unit_properties(unit)
        self.update_unit_list_selection(unit)
        
    def on_terrain_added(self, terrain):
        # 更新地形列表
        pass
        
    def on_unit_list_selection_changed(self):
        # 处理单位列表选择变化
        selected_items = self.unit_list.selectedItems()
        if selected_items:
            unit_id = int(selected_items[0].data(Qt.UserRole))
            # 查找并选中对应单位
            for item in self.view.scene.items():
                if isinstance(item, MilitaryUnit) and id(item) == unit_id:
                    item.set_selected(True)
                    self.view.unit_clicked(item)
                elif isinstance(item, MilitaryUnit):
                    item.set_selected(False)
                    
    def on_viewport_changed(self, rect):
        # 更新状态栏显示视图信息
        self.status_bar.showMessage(f"视图: X:{rect.x():.0f}, Y:{rect.y():.0f}, 宽度:{rect.width():.0f}, 高度:{rect.height():.0f}")
        
    def update_unit_properties(self, unit):
        # 更新单位属性控件
        properties = unit.get_properties()
        self.health_spin.setValue(properties["health"])
        self.ammo_spin.setValue(properties["ammunition"])
        self.fuel_spin.setValue(properties["fuel"])
        self.speed_spin.setValue(int(properties["speed"]))
        self.attack_range_spin.setValue(properties["attack_range"])
        self.visibility_range_spin.setValue(properties["visibility_range"])
        self.unit_name_edit.setText(properties["name"])
        self.unit_type_combo.setCurrentText(properties["type"])
        self.side_combo.setCurrentText(properties["side"])
        
    def update_unit_list_selection(self, unit):
        # 更新单位列表选择
        for i in range(self.unit_list.count()):
            item = self.unit_list.item(i)
            if item.data(Qt.UserRole) == id(unit):
                item.setSelected(True)
                break
                
    def update_unit_list(self):
        # 更新单位列表
        self.unit_list.clear()
        for item in self.view.scene.items():
            if isinstance(item, MilitaryUnit):
                list_item = QListWidgetItem(f"{item.name} ({item.unit_type}, {item.side})")
                list_item.setData(Qt.UserRole, id(item))
                self.unit_list.addItem(list_item)
                
    def delete_selected_unit(self):
        if self.selected_unit:
            self.view.scene.removeItem(self.selected_unit)
            self.selected_unit = None
            self.update_unit_list()
            
    def clone_selected_unit(self):
        if self.selected_unit:
            properties = self.selected_unit.get_properties()
            new_unit = MilitaryUnit(
                properties["position"][0] + 50, 
                properties["position"][1] + 50,
                properties["type"],
                properties["side"],
                f"{properties['name']}_Copy"
            )
            new_unit.set_properties(properties)
            self.view.scene.addItem(new_unit)
            self.update_unit_list()
            
    def update_status_bar(self):
        # 更新状态栏信息
        unit_count = 0
        terrain_count = 0
        for item in self.view.scene.items():
            if isinstance(item, MilitaryUnit):
                unit_count += 1
            elif isinstance(item, TerrainItem):
                terrain_count += 1
                
        status_text = f"单位: {unit_count} | 地形: {terrain_count} | 缩放: {self.view.zoom_level}%"
        if self.simulation_running:
            status_text += " | 模拟运行中"
        self.status_bar.showMessage(status_text)
        
    def new_scenario(self):
        # 创建新场景
        reply = QMessageBox.question(self, "确认", "确定要创建新场景吗？所有未保存的数据将会丢失。",
                                   QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.view.scene.clear()
            self.selected_unit = None
            self.update_unit_list()
            self.status_bar.showMessage("已创建新场景")
            
    def clear_all(self):
        # 清除所有内容
        reply = QMessageBox.question(self, "确认", "确定要清除所有内容吗？",
                                   QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.view.scene.clear()
            self.selected_unit = None
            self.update_unit_list()
            self.view.clear_path()
            self.view.clear_measurement()
            self.view.clear_line()
            self.view.clear_area()
            self.status_bar.showMessage("已清除所有内容")
            
    def save_scenario(self):
        # 保存场景到文件
        file_path, _ = QFileDialog.getSaveFileName(self, "保存场景", "", "JSON Files (*.json)")
        if file_path:
            try:
                scenario_data = {
                    "units": [],
                    "terrain": [],
                    "view": {
                        "zoom": self.view.zoom_level,
                        "center_x": self.view.mapToScene(self.view.viewport().rect().center()).x(),
                        "center_y": self.view.mapToScene(self.view.viewport().rect().center()).y()
                    }
                }
                
                # 收集单位数据
                for item in self.view.scene.items():
                    if isinstance(item, MilitaryUnit):
                        scenario_data["units"].append({
                            "name": item.name,
                            "type": item.unit_type,
                            "side": item.side,
                            "x": item.x,
                            "y": item.y,
                            "health": item.health,
                            "ammunition": item.ammunition,
                            "fuel": item.fuel,
                            "movement_range": item.movement_range,
                            "attack_range": item.attack_range,
                            "visibility_range": item.visibility_range,
                            "speed": item.speed
                        })
                    elif isinstance(item, TerrainItem):
                        scenario_data["terrain"].append({
                            "type": item.terrain_type,
                            "x": item.x,
                            "y": item.y,
                            "width": item.width,
                            "height": item.height
                        })
                
                # 保存到文件
                with open(file_path, 'w') as f:
                    json.dump(scenario_data, f, indent=4)
                    
                self.status_bar.showMessage(f"场景已保存到: {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"保存场景时出错: {str(e)}")
                
    def load_scenario(self):
        # 从文件加载场景
        file_path, _ = QFileDialog.getOpenFileName(self, "加载场景", "", "JSON Files (*.json)")
        if file_path:
            try:
                # 清除当前场景
                self.view.scene.clear()
                self.selected_unit = None
                
                # 从文件加载数据
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    
                # 创建单位
                for unit_data in data["units"]:
                    unit = MilitaryUnit(
                        unit_data["x"], 
                        unit_data["y"], 
                        unit_data["type"], 
                        unit_data["side"],
                        unit_data["name"]
                    )
                    unit.health = unit_data["health"]
                    unit.ammunition = unit_data["ammunition"]
                    unit.fuel = unit_data["fuel"]
                    unit.movement_range = unit_data["movement_range"]
                    unit.attack_range = unit_data["attack_range"]
                    unit.visibility_range = unit_data["visibility_range"]
                    unit.speed = unit_data["speed"]
                    self.view.scene.addItem(unit)
                    
                # 创建地形
                for terrain_data in data["terrain"]:
                    terrain = TerrainItem(
                        terrain_data["x"], 
                        terrain_data["y"],
                        terrain_data["width"], 
                        terrain_data["height"],
                        terrain_data["type"]
                    )
                    self.view.scene.addItem(terrain)
                    
                # 恢复视图状态
                if "view" in data:
                    self.view.zoom_level = data["view"]["zoom"]
                    self.view.centerOn(data["view"]["center_x"], data["view"]["center_y"])
                    self.view.resetTransform()
                    for _ in range(self.view.zoom_level):
                        self.view.scale(1.2, 1.2)
                
                self.update_unit_list()
                self.status_bar.showMessage(f"场景已从 {file_path} 加载")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"加载场景时出错: {str(e)}")
                
    def load_background_image(self):
        # 加载背景图片
        file_path, _ = QFileDialog.getOpenFileName(self, "选择背景图片", "", "Image Files (*.png *.jpg *.bmp)")
        if file_path:
            self.view.set_background_image(file_path)
            self.status_bar.showMessage(f"已加载背景图片: {file_path}")
            
    def export_as_image(self):
        # 导出为图片
        file_path, _ = QFileDialog.getSaveFileName(self, "导出为图片", "", "PNG Images (*.png);;JPEG Images (*.jpg);;BMP Images (*.bmp)")
        if file_path:
            try:
                # 获取场景矩形
                rect = self.view.scene.sceneRect()
                
                # 创建图像
                image = QImage(rect.width(), rect.height(), QImage.Format_ARGB32)
                image.fill(Qt.white)
                
                # 绘制场景到图像
                painter = QPainter(image)
                painter.setRenderHint(QPainter.Antialiasing)
                self.view.scene.render(painter)
                painter.end()
                
                # 保存图像
                image.save(file_path)
                self.status_bar.showMessage(f"已导出图片到: {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导出图片时出错: {str(e)}")
                
    def start_simulation(self):
        # 开始模拟
        self.simulation_running = True
        self.simulation_timer.start(1000 // self.simulation_speed_slider.value())
        self.status_bar.showMessage("模拟已开始")
        
    def stop_simulation(self):
        # 停止模拟
        self.simulation_running = False
        self.simulation_timer.stop()
        self.status_bar.showMessage("模拟已停止")
        
    def update_simulation(self):
        # 更新模拟状态
        if self.simulation_running:
            # 这里可以添加模拟逻辑
            # 例如：单位的移动、攻击等
            pass
            
    def show_about(self):
        # 显示关于对话框
        QMessageBox.about(self, "关于", "战场沙盘高级工具\n\n一个基于PyQt5的战场模拟和可视化工具")
        
    def closeEvent(self, event):
        # 关闭应用程序前的确认
        reply = QMessageBox.question(self, "确认退出", "确定要退出吗？所有未保存的数据将会丢失。",
                                   QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()


def main():
    app = QApplication(sys.argv)
    window = BattlefieldSandTable()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()