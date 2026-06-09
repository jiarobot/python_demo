import sys
import math
import json
import csv
import numpy as np
from datetime import datetime
from PyQt5.QtCore import Qt, QPoint, QPointF, QRectF, QLineF, QSize, QVariant, QTimer
from PyQt5.QtGui import (QPainter, QPen, QBrush, QColor, QFont, QPainterPath, 
                         QTransform, QKeySequence, QIcon, QPixmap, QImage, QMatrix4x4,
                         QVector3D, QQuaternion, QLinearGradient, QRadialGradient)
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QToolBar, 
                            QAction, QStatusBar, QMessageBox, QDockWidget,
                            QListWidget, QVBoxLayout, QHBoxLayout, QSplitter,
                            QPushButton, QColorDialog, QSpinBox, QLabel,
                            QFileDialog, QInputDialog, QGraphicsView, QActionGroup,
                            QGraphicsScene, QGraphicsItem, QGraphicsRectItem,
                            QGraphicsLineItem, QGraphicsTextItem, QMenu, QTabWidget,
                            QTreeWidget, QTreeWidgetItem, QDoubleSpinBox, QComboBox,
                            QGroupBox, QCheckBox, QSlider, QDialog, QTextEdit,
                            QProgressBar, QTableWidget, QTableWidgetItem, QHeaderView,
                            QToolBox, QScrollArea, QFrame, QSizePolicy, QGridLayout, QListWidgetItem,
                            QLineEdit, QRadioButton, QButtonGroup, QTextBrowser,
                            QFormLayout, QProgressDialog, QApplication, QStyleFactory)

class Vector3D:
    """简化的3D向量类"""
    def __init__(self, x=0.0, y=0.0, z=0.0):
        self.x = x
        self.y = y
        self.z = z
        
    def to_qvector3d(self):
        return QVector3D(self.x, self.y, self.z)
    
    @staticmethod
    def from_qvector3d(vec):
        return Vector3D(vec.x(), vec.y(), vec.z())
    
    def __add__(self, other):
        return Vector3D(self.x + other.x, self.y + other.y, self.z + other.z)
    
    def __sub__(self, other):
        return Vector3D(self.x - other.x, self.y - other.y, self.z - other.z)
    
    def __mul__(self, scalar):
        return Vector3D(self.x * scalar, self.y * scalar, self.z * scalar)
    
    def length(self):
        return math.sqrt(self.x*self.x + self.y*self.y + self.z*self.z)
    
    def normalized(self):
        length = self.length()
        if length > 0:
            return Vector3D(self.x/length, self.y/length, self.z/length)
        return Vector3D()
    
    def cross(self, other):
        return Vector3D(
            self.y * other.z - self.z * other.y,
            self.z * other.x - self.x * other.z,
            self.x * other.y - self.y * other.x
        )
    
    def dot(self, other):
        return self.x * other.x + self.y * other.y + self.z * other.z

class Material:
    """材料类"""
    def __init__(self, name, color, texture=None, cost_per_sqm=0.0, category="默认", 
                 durability=5, maintenance=0.0, eco_friendly=False, description=""):
        self.name = name
        self.color = color
        self.texture = texture
        self.cost_per_sqm = cost_per_sqm
        self.category = category
        self.durability = durability  # 耐久性评级 (1-10)
        self.maintenance = maintenance  # 年维护成本比例
        self.eco_friendly = eco_friendly  # 是否环保
        self.description = description
        
    def to_dict(self):
        return {
            "name": self.name,
            "color": (self.color.red(), self.color.green(), self.color.blue(), self.color.alpha()),
            "cost_per_sqm": self.cost_per_sqm,
            "category": self.category,
            "durability": self.durability,
            "maintenance": self.maintenance,
            "eco_friendly": self.eco_friendly,
            "description": self.description
        }
    
    @staticmethod
    def from_dict(data):
        color_data = data.get("color", (200, 200, 200, 255))
        color = QColor(*color_data)
        material = Material(
            data.get("name", "未知材料"),
            color,
            cost_per_sqm=data.get("cost_per_sqm", 0.0),
            category=data.get("category", "默认"),
            durability=data.get("durability", 5),
            maintenance=data.get("maintenance", 0.0),
            eco_friendly=data.get("eco_friendly", False),
            description=data.get("description", "")
        )
        return material

class MaterialLibrary:
    """材料库"""
    def __init__(self):
        self.materials = {}
        self.load_default_materials()
    
    def load_default_materials(self):
        # 墙体材料
        self.add_material(Material("白墙", QColor(255, 255, 255), cost_per_sqm=25.0, category="墙体", 
                                  durability=7, maintenance=0.05, description="标准白色墙面漆"))
        self.add_material(Material("砖墙", QColor(200, 150, 120), cost_per_sqm=45.0, category="墙体", 
                                  durability=9, maintenance=0.02, description="红砖墙面"))
        self.add_material(Material("混凝土", QColor(180, 180, 180), cost_per_sqm=35.0, category="墙体", 
                                  durability=10, maintenance=0.01, description="混凝土墙面"))
        self.add_material(Material("木板墙", QColor(210, 180, 140), cost_per_sqm=60.0, category="墙体", 
                                  durability=6, maintenance=0.08, eco_friendly=True, description="天然木质墙面"))
        
        # 地板材料
        self.add_material(Material("木地板", QColor(180, 150, 110), cost_per_sqm=85.0, category="地板", 
                                  durability=8, maintenance=0.07, description="实木地板"))
        self.add_material(Material("瓷砖", QColor(240, 240, 240), cost_per_sqm=75.0, category="地板", 
                                  durability=9, maintenance=0.03, description="陶瓷地砖"))
        self.add_material(Material("大理石", QColor(220, 220, 220), cost_per_sqm=120.0, category="地板", 
                                  durability=10, maintenance=0.04, description="天然大理石地板"))
        self.add_material(Material("地毯", QColor(150, 100, 80), cost_per_sqm=45.0, category="地板", 
                                  durability=5, maintenance=0.12, description="羊毛地毯"))
        
        # 天花板材料
        self.add_material(Material("石膏板", QColor(245, 245, 245), cost_per_sqm=30.0, category="天花板", 
                                  durability=7, maintenance=0.04, description="标准石膏板吊顶"))
        self.add_material(Material("铝扣板", QColor(230, 230, 230), cost_per_sqm=65.0, category="天花板", 
                                  durability=8, maintenance=0.02, description="铝合金扣板吊顶"))
        self.add_material(Material("木质吊顶", QColor(200, 170, 140), cost_per_sqm=90.0, category="天花板", 
                                  durability=6, maintenance=0.08, eco_friendly=True, description="实木吊顶"))
        
        # 门窗材料
        self.add_material(Material("木门", QColor(150, 120, 90), cost_per_sqm=200.0, category="门窗", 
                                  durability=7, maintenance=0.06, description="实木门"))
        self.add_material(Material("铝合金门", QColor(200, 200, 200), cost_per_sqm=150.0, category="门窗", 
                                  durability=9, maintenance=0.03, description="铝合金框架门"))
        self.add_material(Material("玻璃窗", QColor(200, 220, 240, 128), cost_per_sqm=180.0, category="门窗", 
                                  durability=8, maintenance=0.04, description="双层玻璃窗"))
    
    def add_material(self, material):
        self.materials[material.name] = material
    
    def get_material(self, name):
        return self.materials.get(name, Material("默认", QColor(200, 200, 200)))
    
    def get_materials_by_category(self, category):
        return [mat for mat in self.materials.values() if mat.category == category]
    
    def to_dict(self):
        return {name: mat.to_dict() for name, mat in self.materials.items()}
    
    def load_from_dict(self, data):
        self.materials = {}
        for name, mat_data in data.items():
            self.materials[name] = Material.from_dict(mat_data)

class WallItem(QGraphicsLineItem):
    """墙体项"""
    def __init__(self, start_point, end_point, height=280, thickness=20, material=None):
        super().__init__(QLineF(start_point, end_point))
        self.setPen(QPen(Qt.black, 2, Qt.SolidLine, Qt.RoundCap))
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.thickness = thickness
        self.height = height
        self.start_point = start_point
        self.end_point = end_point
        self.material = material if material else MaterialLibrary().get_material("白墙")
        self.windows = []
        self.doors = []
        self.setZValue(10)
        
    def get_length(self):
        return self.line().length()
    
    def get_area(self):
        return self.get_length() * self.height / 10000  # 转换为平方米
    
    def get_cost(self):
        return self.get_area() * self.material.cost_per_sqm
    
    def get_maintenance_cost(self, years=1):
        return self.get_cost() * self.material.maintenance * years
    
    def add_window(self, window):
        self.windows.append(window)
    
    def add_door(self, door):
        self.doors.append(door)
    
    def paint(self, painter, option, widget=None):
        # 绘制墙体两侧的线
        line = self.line()
        length = line.length()
        
        # 计算墙体的法向量
        dx = line.dx() / length
        dy = line.dy() / length
        offset_x = -dy * self.thickness / 2
        offset_y = dx * self.thickness / 2
        
        # 绘制墙体填充
        path = QPainterPath()
        path.moveTo(line.x1() + offset_x, line.y1() + offset_y)
        path.lineTo(line.x2() + offset_x, line.y2() + offset_y)
        path.lineTo(line.x2() - offset_x, line.y2() - offset_y)
        path.lineTo(line.x1() - offset_x, line.y1() - offset_y)
        path.closeSubpath()
        
        # 使用材质颜色填充
        painter.fillPath(path, QBrush(self.material.color))
        
        # 绘制墙体轮廓
        painter.setPen(QPen(Qt.black, 2, Qt.SolidLine))
        painter.drawPath(path)
        
        # 绘制门窗位置
        for window in self.windows:
            pos = window['position']  # 0-1之间的相对位置
            width = window['width']
            
            # 计算窗口的起点和终点
            window_start_x = line.x1() + line.dx() * pos - dy * self.thickness / 2
            window_start_y = line.y1() + line.dy() * pos + dx * self.thickness / 2
            window_end_x = window_start_x + dx * width
            window_end_y = window_start_y + dy * width
            
            # 绘制窗户
            window_path = QPainterPath()
            window_path.moveTo(window_start_x, window_start_y)
            window_path.lineTo(window_end_x, window_end_y)
            
            painter.setPen(QPen(Qt.blue, 4, Qt.SolidLine, Qt.RoundCap))
            painter.drawPath(window_path)
        
        for door in self.doors:
            pos = door['position']  # 0-1之间的相对位置
            width = door['width']
            
            # 计算门的起点和终点
            door_start_x = line.x1() + line.dx() * pos - dy * self.thickness / 2
            door_start_y = line.y1() + line.dy() * pos + dx * self.thickness / 2
            door_end_x = door_start_x + dx * width
            door_end_y = door_start_y + dy * width
            
            # 绘制门
            door_path = QPainterPath()
            door_path.moveTo(door_start_x, door_start_y)
            door_path.lineTo(door_end_x, door_end_y)
            
            painter.setPen(QPen(Qt.darkGreen, 4, Qt.SolidLine, Qt.RoundCap))
            painter.drawPath(door_path)
            
            # 绘制门扇弧线
            arc_rect = QRectF(door_start_x - width/2, door_start_y - width/2, width, width)
            arc_path = QPainterPath()
            arc_path.moveTo(door_start_x, door_start_y)
            arc_path.arcTo(arc_rect, 0, 90)
            
            painter.setPen(QPen(Qt.darkGreen, 2, Qt.SolidLine))
            painter.drawPath(arc_path)
        
        # 如果被选中，绘制选择框
        if self.isSelected():
            painter.setPen(QPen(Qt.blue, 2, Qt.DashLine))
            painter.drawPath(path)
            
        # 显示墙体长度
        mid_x = (line.x1() + line.x2()) / 2
        mid_y = (line.y1() + line.y2()) / 2
        painter.setPen(QPen(Qt.darkGray))
        painter.setFont(QFont("Arial", 8))
        painter.drawText(QPointF(mid_x, mid_y), f"{length:.0f}cm")

class FloorItem(QGraphicsRectItem):
    """地板项"""
    def __init__(self, rect, material=None):
        super().__init__(rect)
        self.material = material if material else MaterialLibrary().get_material("木地板")
        self.setPen(QPen(Qt.transparent))
        self.setBrush(QBrush(self.material.color))
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setZValue(-10)  # 确保地板在底层
        
    def get_area(self):
        rect = self.rect()
        return rect.width() * rect.height() / 10000  # 转换为平方米
    
    def get_cost(self):
        return self.get_area() * self.material.cost_per_sqm
    
    def get_maintenance_cost(self, years=1):
        return self.get_cost() * self.material.maintenance * years

class DoorItem:
    """门项"""
    def __init__(self, wall, position, width=80, height=200):
        self.wall = wall
        self.position = position  # 在墙上的相对位置 (0-1)
        self.width = width
        self.height = height
        self.material = MaterialLibrary().get_material("木门")
        
    def get_cost(self):
        return (self.width * self.height / 10000) * self.material.cost_per_sqm
    
    def get_maintenance_cost(self, years=1):
        return self.get_cost() * self.material.maintenance * years

class WindowItem:
    """窗项"""
    def __init__(self, wall, position, width=100, height=120):
        self.wall = wall
        self.position = position  # 在墙上的相对位置 (0-1)
        self.width = width
        self.height = height
        self.material = MaterialLibrary().get_material("玻璃窗")
        
    def get_cost(self):
        return (self.width * self.height / 10000) * self.material.cost_per_sqm
    
    def get_maintenance_cost(self, years=1):
        return self.get_cost() * self.material.maintenance * years

class FurnitureItem(QGraphicsRectItem):
    """家具项"""
    def __init__(self, x, y, width, height, name, color=QColor(200, 150, 100), height_3d=80, material=None):
        super().__init__(x, y, width, height)
        self.name = name
        self.color = color
        self.height_3d = height_3d
        self.material = material if material else MaterialLibrary().get_material("木质家具")
        self.setPen(QPen(Qt.black, 1))
        self.setBrush(QBrush(color))
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setFlag(QGraphicsItem.ItemIsFocusable, True)
        
    def get_volume(self):
        rect = self.rect()
        return rect.width() * rect.height() * self.height_3d / 1e6  # 转换为立方米
    
    def get_cost(self):
        rect = self.rect()
        area = (rect.width() * rect.height() * 2 + 
                rect.width() * self.height_3d * 2 + 
                rect.height() * self.height_3d * 2) / 10000  # 表面积平方米
        return area * self.material.cost_per_sqm
    
    def get_maintenance_cost(self, years=1):
        return self.get_cost() * self.material.maintenance * years
        
    def paint(self, painter, option, widget=None):
        super().paint(painter, option, widget)
        
        # 绘制家具名称
        painter.setPen(QPen(Qt.black))
        rect = self.rect()
        painter.drawText(rect, Qt.AlignCenter, self.name)
        
        # 如果被选中，绘制高度信息
        if self.isSelected():
            painter.drawText(rect, Qt.AlignBottom | Qt.AlignRight, f"{self.height_3d}cm")

class DimensionItem(QGraphicsLineItem):
    """尺寸标注项"""
    def __init__(self, start_point, end_point, text):
        super().__init__(QLineF(start_point, end_point))
        self.text = text
        self.setPen(QPen(Qt.darkGray, 1, Qt.DashLine))
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        
    def paint(self, painter, option, widget=None):
        super().paint(painter, option, widget)
        
        # 绘制尺寸文本
        mid_x = (self.line().x1() + self.line().x2()) / 2
        mid_y = (self.line().y1() + self.line().y2()) / 2
        
        painter.setPen(QPen(Qt.black))
        painter.drawText(QPointF(mid_x, mid_y), self.text)

class RoomLabelItem(QGraphicsTextItem):
    """房间标签项"""
    def __init__(self, x, y, name, area):
        super().__init__(f"{name}\n{area:.2f}㎡")
        self.setPos(x, y)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setDefaultTextColor(Qt.darkBlue)
        self.setFont(QFont("Arial", 10, QFont.Bold))
        
        # 添加背景
        self.setBackgroundBrush(QBrush(QColor(255, 255, 255, 200)))

class HouseDesignView(QGraphicsView):
    """房屋设计视图"""
    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)
        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.scale(1.0, 1.0)
        self._zoom = 0
        self._pan_start = QPoint()
        self._panning = False
        
    def wheelEvent(self, event):
        # 缩放视图
        if event.angleDelta().y() > 0:
            factor = 1.25
            self._zoom += 1
        else:
            factor = 0.8
            self._zoom -= 1
            
        if self._zoom > 0:
            self.scale(factor, factor)
        elif self._zoom == 0:
            self.fitInView(self.sceneRect(), Qt.KeepAspectRatio)
        else:
            self._zoom = 0
            
    def mousePressEvent(self, event):
        if event.button() == Qt.MiddleButton:
            self._pan_start = event.pos()
            self._panning = True
            self.setCursor(Qt.ClosedHandCursor)
        else:
            super().mousePressEvent(event)
            
    def mouseMoveEvent(self, event):
        if self._panning:
            delta = event.pos() - self._pan_start
            self._pan_start = event.pos()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
        else:
            super().mouseMoveEvent(event)
            
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MiddleButton:
            self._panning = False
            self.setCursor(Qt.ArrowCursor)
        else:
            super().mouseReleaseEvent(event)

class ThreeDView(QWidget):
    """3D预览视图"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(400, 400)
        self.camera_position = Vector3D(500, 500, 500)
        self.camera_target = Vector3D(0, 0, 0)
        self.camera_up = Vector3D(0, 0, 1)
        self.rotation_x = 30
        self.rotation_y = 45
        self.scale = 0.5
        self.walls = []
        self.furniture = []
        self.floors = []
        self._pan_start = QPoint()
        self._panning = False
        
    def set_scene_data(self, walls, furniture, floors):
        self.walls = walls
        self.furniture = furniture
        self.floors = floors
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 设置背景渐变
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0, QColor(200, 220, 255))
        gradient.setColorAt(1, QColor(240, 240, 255))
        painter.fillRect(self.rect(), gradient)
        
        # 设置视图变换
        width, height = self.width(), self.height()
        center_x, center_y = width // 2, height // 2
        
        # 简单的3D投影
        painter.setPen(QPen(Qt.black, 1))
        
        # 绘制地板
        for floor in self.floors:
            if isinstance(floor, FloorItem):
                rect = floor.rect()
                points = [
                    self.project_3d(Vector3D(rect.x(), rect.y(), 0)),
                    self.project_3d(Vector3D(rect.x() + rect.width(), rect.y(), 0)),
                    self.project_3d(Vector3D(rect.x() + rect.width(), rect.y() + rect.height(), 0)),
                    self.project_3d(Vector3D(rect.x(), rect.y() + rect.height(), 0))
                ]
                
                # 只绘制可见的面
                if self.is_face_visible(points):
                    path = QPainterPath()
                    path.moveTo(points[0].x(), points[0].y())
                    for point in points[1:]:
                        path.lineTo(point.x(), point.y())
                    path.closeSubpath()
                    
                    # 使用地板材质颜色
                    color = floor.material.color
                    painter.fillPath(path, QBrush(color))
                    painter.drawPath(path)
        
        # 绘制墙体
        for wall in self.walls:
            if isinstance(wall, WallItem):
                line = wall.line()
                height = wall.height
                
                # 计算墙体的法向量
                dx = line.dx() / line.length()
                dy = line.dy() / line.length()
                offset_x = -dy * wall.thickness / 2
                offset_y = dx * wall.thickness / 2
                
                # 墙体的四个角点
                points_3d = [
                    Vector3D(line.x1() + offset_x, line.y1() + offset_y, 0),
                    Vector3D(line.x2() + offset_x, line.y2() + offset_y, 0),
                    Vector3D(line.x2() + offset_x, line.y2() + offset_y, height),
                    Vector3D(line.x1() + offset_x, line.y1() + offset_y, height),
                    Vector3D(line.x1() - offset_x, line.y1() - offset_y, 0),
                    Vector3D(line.x2() - offset_x, line.y2() - offset_y, 0),
                    Vector3D(line.x2() - offset_x, line.y2() - offset_y, height),
                    Vector3D(line.x1() - offset_x, line.y1() - offset_y, height)
                ]
                
                # 绘制墙体的六个面
                faces = [
                    [0, 1, 2, 3],  # 前面
                    [4, 5, 6, 7],  # 后面
                    [0, 3, 7, 4],  # 左面
                    [1, 2, 6, 5],  # 右面
                    [3, 2, 6, 7],  # 顶面
                    [0, 1, 5, 4]   # 底面
                ]
                
                for face in faces:
                    points = [self.project_3d(points_3d[i]) for i in face]
                    
                    # 只绘制可见的面
                    if self.is_face_visible(points):
                        path = QPainterPath()
                        path.moveTo(points[0].x(), points[0].y())
                        for point in points[1:]:
                            path.lineTo(point.x(), point.y())
                        path.closeSubpath()
                        
                        # 使用墙体材质颜色
                        color = wall.material.color
                        painter.fillPath(path, QBrush(color))
                        painter.drawPath(path)
        
        # 绘制家具
        for item in self.furniture:
            if isinstance(item, FurnitureItem):
                rect = item.rect()
                height = item.height_3d
                
                points_3d = [
                    Vector3D(rect.x(), rect.y(), 0),
                    Vector3D(rect.x() + rect.width(), rect.y(), 0),
                    Vector3D(rect.x() + rect.width(), rect.y() + rect.height(), 0),
                    Vector3D(rect.x(), rect.y() + rect.height(), 0),
                    Vector3D(rect.x(), rect.y(), height),
                    Vector3D(rect.x() + rect.width(), rect.y(), height),
                    Vector3D(rect.x() + rect.width(), rect.y() + rect.height(), height),
                    Vector3D(rect.x(), rect.y() + rect.height(), height)
                ]
                
                # 绘制立方体的六个面
                faces = [
                    [0, 1, 2, 3],  # 底面
                    [4, 5, 6, 7],  # 顶面
                    [0, 1, 5, 4],  # 前面
                    [2, 3, 7, 6],  # 后面
                    [0, 3, 7, 4],  # 左面
                    [1, 2, 6, 5]   # 右面
                ]
                
                for face in faces:
                    points = [self.project_3d(points_3d[i]) for i in face]
                    
                    # 只绘制可见的面
                    if self.is_face_visible(points):
                        path = QPainterPath()
                        path.moveTo(points[0].x(), points[0].y())
                        for point in points[1:]:
                            path.lineTo(point.x(), point.y())
                        path.closeSubpath()
                        
                        # 使用家具颜色
                        painter.fillPath(path, QBrush(item.color))
                        painter.drawPath(path)
        
        # 绘制坐标轴
        painter.setPen(QPen(Qt.red, 2))
        origin = self.project_3d(Vector3D(0, 0, 0))
        x_axis = self.project_3d(Vector3D(100, 0, 0))
        painter.drawLine(int(origin.x()), int(origin.y()), int(x_axis.x()), int(x_axis.y()))
        painter.drawText(int(x_axis.x()), int(x_axis.y()), "X")
        
        painter.setPen(QPen(Qt.green, 2))
        y_axis = self.project_3d(Vector3D(0, 100, 0))
        painter.drawLine(int(origin.x()), int(origin.y()), int(y_axis.x()), int(y_axis.y()))
        painter.drawText(int(y_axis.x()), int(y_axis.y()), "Y")
        
        painter.setPen(QPen(Qt.blue, 2))
        z_axis = self.project_3d(Vector3D(0, 0, 100))
        painter.drawLine(int(origin.x()), int(origin.y()), int(z_axis.x()), int(z_axis.y()))
        painter.drawText(int(z_axis.x()), int(z_axis.y()), "Z")
        
        # 绘制视角指示器
        painter.setPen(QPen(Qt.black, 1))
        painter.drawText(10, 20, f"视角: X={self.rotation_x:.1f}°, Y={self.rotation_y:.1f}°")
        painter.drawText(10, 40, f"缩放: {self.scale:.2f}")
        
    def is_face_visible(self, points):
        """判断面是否可见（简单的背面剔除）"""
        if len(points) < 3:
            return True
            
        # 计算面的法向量（使用前三个点）
        p0, p1, p2 = points[0], points[1], points[2]
        v1 = QPointF(p1.x() - p0.x(), p1.y() - p0.y())
        v2 = QPointF(p2.x() - p0.x(), p2.y() - p0.y())
        
        # 计算叉积（法向量的Z分量）
        cross = v1.x() * v2.y() - v1.y() * v2.x()
        
        # 如果叉积为正，则面朝向观众
        return cross > 0
    
    def project_3d(self, point):
        """简单的3D到2D投影"""
        # 应用旋转
        angle_x = math.radians(self.rotation_x)
        angle_y = math.radians(self.rotation_y)
        
        # 绕X轴旋转
        y_rot = point.y * math.cos(angle_x) - point.z * math.sin(angle_x)
        z_rot = point.y * math.sin(angle_x) + point.z * math.cos(angle_x)
        
        # 绕Y轴旋转
        x_rot = point.x * math.cos(angle_y) + z_rot * math.sin(angle_y)
        z_rot = -point.x * math.sin(angle_y) + z_rot * math.cos(angle_y)
        
        # 应用透视
        if z_rot > 0:
            factor = 500 / (z_rot + 500)
        else:
            factor = 1.0
            
        x = x_rot * factor * self.scale + self.width() / 2
        y = -y_rot * factor * self.scale + self.height() / 2
        
        return QPointF(x, y)
    
    def wheelEvent(self, event):
        # 缩放3D视图
        if event.angleDelta().y() > 0:
            self.scale *= 1.1
        else:
            self.scale /= 1.1
        self.update()
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._pan_start = event.pos()
            self._panning = True
            self.setCursor(Qt.ClosedHandCursor)
    
    def mouseMoveEvent(self, event):
        if self._panning:
            dx = event.x() - self._pan_start.x()
            dy = event.y() - self._pan_start.y()
            
            self.rotation_x += dy * 0.5
            self.rotation_y += dx * 0.5
            
            # 限制旋转角度
            self.rotation_x = max(-90, min(90, self.rotation_x))
            
            self._pan_start = event.pos()
            self.update()
    
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._panning = False
            self.setCursor(Qt.ArrowCursor)

class HouseDesignScene(QGraphicsScene):
    """房屋设计场景"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSceneRect(0, 0, 2000, 2000)
        self.grid_size = 20
        self.snap_to_grid = True
        self.current_tool = None
        self.temp_item = None
        self.start_point = None
        self.drawing = False
        self.current_material = MaterialLibrary().get_material("白墙")
        self.current_floor_material = MaterialLibrary().get_material("木地板")
        self.room_labels = []
        
    def drawBackground(self, painter, rect):
        # 绘制网格
        painter.fillRect(rect, QBrush(Qt.white))
        
        left = int(rect.left()) - (int(rect.left()) % self.grid_size)
        top = int(rect.top()) - (int(rect.top()) % self.grid_size)
        right = int(rect.right())
        bottom = int(rect.bottom())
        
        lines = []
        for x in range(left, right, self.grid_size):
            lines.append(QLineF(x, rect.top(), x, rect.bottom()))
        for y in range(top, bottom, self.grid_size):
            lines.append(QLineF(rect.left(), y, rect.right(), y))
            
        painter.setPen(QPen(QColor(220, 220, 220), 0))
        painter.drawLines(lines)
        
    def snapPointToGrid(self, point):
        if self.snap_to_grid:
            x = round(point.x() / self.grid_size) * self.grid_size
            y = round(point.y() / self.grid_size) * self.grid_size
            return QPointF(x, y)
        return point
        
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            scene_pos = self.snapPointToGrid(event.scenePos())
            
            if self.current_tool == "wall":
                self.start_point = scene_pos
                self.drawing = True
                
            elif self.current_tool == "floor":
                self.start_point = scene_pos
                self.drawing = True
                
            elif self.current_tool == "door":
                # 找到最近的墙
                closest_wall = None
                min_distance = float('inf')
                
                for item in self.items():
                    if isinstance(item, WallItem):
                        line = item.line()
                        # 计算点到线段的距离
                        distance = self.point_to_line_distance(scene_pos, line)
                        if distance < min_distance and distance < 20:  # 20像素内的墙
                            min_distance = distance
                            closest_wall = item
                
                if closest_wall:
                    # 计算门在墙上的位置
                    line = closest_wall.line()
                    length = line.length()
                    # 计算点在墙上的投影位置
                    t = self.point_to_line_projection(scene_pos, line)
                    if 0 <= t <= 1:
                        door = DoorItem(closest_wall, t)
                        closest_wall.add_door({"position": t, "width": door.width})
                        self.update()
                
            elif self.current_tool == "window":
                # 找到最近的墙
                closest_wall = None
                min_distance = float('inf')
                
                for item in self.items():
                    if isinstance(item, WallItem):
                        line = item.line()
                        # 计算点到线段的距离
                        distance = self.point_to_line_distance(scene_pos, line)
                        if distance < min_distance and distance < 20:  # 20像素内的墙
                            min_distance = distance
                            closest_wall = item
                
                if closest_wall:
                    # 计算窗在墙上的位置
                    line = closest_wall.line()
                    length = line.length()
                    # 计算点在墙上的投影位置
                    t = self.point_to_line_projection(scene_pos, line)
                    if 0 <= t <= 1:
                        window = WindowItem(closest_wall, t)
                        closest_wall.add_window({"position": t, "width": window.width})
                        self.update()
                
            elif self.current_tool == "select":
                super().mousePressEvent(event)
                
        else:
            super().mousePressEvent(event)
            
    def mouseMoveEvent(self, event):
        scene_pos = self.snapPointToGrid(event.scenePos())
        
        if self.drawing and self.current_tool == "wall":
            if self.temp_item:
                self.removeItem(self.temp_item)
            self.temp_item = WallItem(self.start_point, scene_pos, material=self.current_material)
            self.addItem(self.temp_item)
            
        elif self.drawing and self.current_tool == "floor":
            if self.temp_item:
                self.removeItem(self.temp_item)
            rect = QRectF(self.start_point, scene_pos).normalized()
            self.temp_item = FloorItem(rect, material=self.current_floor_material)
            self.addItem(self.temp_item)
            
        super().mouseMoveEvent(event)
        
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.drawing:
            scene_pos = self.snapPointToGrid(event.scenePos())
            
            if self.current_tool == "wall" and self.start_point != scene_pos:
                if self.temp_item:
                    self.removeItem(self.temp_item)
                wall = WallItem(self.start_point, scene_pos, material=self.current_material)
                self.addItem(wall)
                
            elif self.current_tool == "floor" and self.start_point != scene_pos:
                if self.temp_item:
                    self.removeItem(self.temp_item)
                rect = QRectF(self.start_point, scene_pos).normalized()
                floor = FloorItem(rect, material=self.current_floor_material)
                self.addItem(floor)
                
            self.drawing = False
            self.temp_item = None
            
        super().mouseReleaseEvent(event)
    
    def point_to_line_distance(self, point, line):
        """计算点到线段的距离"""
        x1, y1 = line.x1(), line.y1()
        x2, y2 = line.x2(), line.y2()
        x0, y0 = point.x(), point.y()
        
        # 线段长度的平方
        l2 = (x2 - x1)**2 + (y2 - y1)**2
        
        # 如果线段长度为0，直接返回点到端点的距离
        if l2 == 0:
            return math.sqrt((x0 - x1)**2 + (y0 - y1)**2)
        
        # 计算投影比例 t
        t = max(0, min(1, ((x0 - x1) * (x2 - x1) + (y0 - y1) * (y2 - y1)) / l2))
        
        # 计算投影点
        projection_x = x1 + t * (x2 - x1)
        projection_y = y1 + t * (y2 - y1)
        
        # 返回点到投影点的距离
        return math.sqrt((x0 - projection_x)**2 + (y0 - projection_y)**2)
    
    def point_to_line_projection(self, point, line):
        """计算点在线段上的投影比例 (0-1)"""
        x1, y1 = line.x1(), line.y1()
        x2, y2 = line.x2(), line.y2()
        x0, y0 = point.x(), point.y()
        
        # 线段长度的平方
        l2 = (x2 - x1)**2 + (y2 - y1)**2
        
        # 如果线段长度为0，返回0
        if l2 == 0:
            return 0
        
        # 计算投影比例 t
        t = ((x0 - x1) * (x2 - x1) + (y0 - y1) * (y2 - y1)) / l2
        
        return max(0, min(1, t))
    
    def auto_detect_rooms(self):
        """自动检测房间并添加标签"""
        # 清除现有标签
        for label in self.room_labels:
            self.removeItem(label)
        self.room_labels = []
        
        # 获取所有墙体
        walls = []
        for item in self.items():
            if isinstance(item, WallItem):
                walls.append(item)
        
        # 简单的房间检测算法 - 查找封闭区域
        # 这里只是一个示例实现，实际应用可能需要更复杂的算法
        
        # 假设房间是由墙体围成的矩形区域
        # 在实际应用中，可以使用更复杂的方法如平面图分析
        
        # 创建一些示例房间
        room_count = 1
        for wall in walls[:4]:  # 只为前四面墙创建房间
            line = wall.line()
            mid_x = (line.x1() + line.x2()) / 2
            mid_y = (line.y1() + line.y2()) / 2
            
            # 创建房间标签
            room_name = f"房间{room_count}"
            room_area = 10 + room_count * 5  # 示例面积
            label = RoomLabelItem(mid_x, mid_y, room_name, room_area)
            self.addItem(label)
            self.room_labels.append(label)
            
            room_count += 1

class MaterialEditor(QDialog):
    """材料编辑器"""
    def __init__(self, material_lib, parent=None):
        super().__init__(parent)
        self.material_lib = material_lib
        self.setWindowTitle("材料编辑器")
        self.setModal(True)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # 材料列表
        self.material_list = QListWidget()
        self.update_material_list()
        self.material_list.currentItemChanged.connect(self.on_material_selected)
        layout.addWidget(QLabel("材料列表:"))
        layout.addWidget(self.material_list)
        
        # 材料属性编辑
        prop_group = QGroupBox("材料属性")
        prop_layout = QFormLayout()
        
        self.name_edit = QLineEdit()
        prop_layout.addRow("名称:", self.name_edit)
        
        self.category_combo = QComboBox()
        self.category_combo.addItems(["墙体", "地板", "天花板", "门窗", "家具"])
        prop_layout.addRow("类别:", self.category_combo)
        
        self.color_btn = QPushButton()
        self.color_btn.clicked.connect(self.choose_color)
        self.color_btn.setFixedSize(50, 25)
        prop_layout.addRow("颜色:", self.color_btn)
        
        self.cost_spin = QDoubleSpinBox()
        self.cost_spin.setRange(0, 10000)
        self.cost_spin.setDecimals(2)
        self.cost_spin.setSuffix(" 元/㎡")
        prop_layout.addRow("成本:", self.cost_spin)
        
        self.durability_spin = QSpinBox()
        self.durability_spin.setRange(1, 10)
        prop_layout.addRow("耐久性 (1-10):", self.durability_spin)
        
        self.maintenance_spin = QDoubleSpinBox()
        self.maintenance_spin.setRange(0, 1)
        self.maintenance_spin.setDecimals(3)
        self.maintenance_spin.setSuffix(" %/年")
        prop_layout.addRow("维护成本:", self.maintenance_spin)
        
        self.eco_check = QCheckBox("环保材料")
        prop_layout.addRow("环保:", self.eco_check)
        
        self.desc_edit = QTextEdit()
        self.desc_edit.setMaximumHeight(60)
        prop_layout.addRow("描述:", self.desc_edit)
        
        prop_group.setLayout(prop_layout)
        layout.addWidget(prop_group)
        
        # 按钮
        btn_layout = QHBoxLayout()
        self.add_btn = QPushButton("添加")
        self.add_btn.clicked.connect(self.add_material)
        btn_layout.addWidget(self.add_btn)
        
        self.update_btn = QPushButton("更新")
        self.update_btn.clicked.connect(self.update_material)
        btn_layout.addWidget(self.update_btn)
        
        self.delete_btn = QPushButton("删除")
        self.delete_btn.clicked.connect(self.delete_material)
        btn_layout.addWidget(self.delete_btn)
        
        self.close_btn = QPushButton("关闭")
        self.close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self.close_btn)
        
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
        self.resize(500, 600)
        
    def update_material_list(self):
        self.material_list.clear()
        for name in sorted(self.material_lib.materials.keys()):
            self.material_list.addItem(name)
    
    def on_material_selected(self, current, previous):
        if current:
            material = self.material_lib.get_material(current.text())
            self.name_edit.setText(material.name)
            self.category_combo.setCurrentText(material.category)
            self.color_btn.setStyleSheet(f"background-color: {material.color.name()}")
            self.cost_spin.setValue(material.cost_per_sqm)
            self.durability_spin.setValue(material.durability)
            self.maintenance_spin.setValue(material.maintenance)
            self.eco_check.setChecked(material.eco_friendly)
            self.desc_edit.setPlainText(material.description)
    
    def choose_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.color_btn.setStyleSheet(f"background-color: {color.name()}")
            self.current_color = color
    
    def add_material(self):
        name = self.name_edit.text()
        if not name:
            QMessageBox.warning(self, "警告", "请输入材料名称")
            return
            
        if name in self.material_lib.materials:
            QMessageBox.warning(self, "警告", "材料已存在")
            return
            
        material = Material(
            name,
            self.current_color if hasattr(self, 'current_color') else QColor(200, 200, 200),
            cost_per_sqm=self.cost_spin.value(),
            category=self.category_combo.currentText(),
            durability=self.durability_spin.value(),
            maintenance=self.maintenance_spin.value(),
            eco_friendly=self.eco_check.isChecked(),
            description=self.desc_edit.toPlainText()
        )
        self.material_lib.add_material(material)
        self.update_material_list()
        
    def update_material(self):
        current_item = self.material_list.currentItem()
        if not current_item:
            return
            
        name = current_item.text()
        material = self.material_lib.get_material(name)
        
        new_name = self.name_edit.text()
        if new_name and new_name != name:
            # 更新名称
            self.material_lib.materials[new_name] = material
            del self.material_lib.materials[name]
            name = new_name
            
        material.name = name
        if hasattr(self, 'current_color'):
            material.color = self.current_color
        material.cost_per_sqm = self.cost_spin.value()
        material.category = self.category_combo.currentText()
        material.durability = self.durability_spin.value()
        material.maintenance = self.maintenance_spin.value()
        material.eco_friendly = self.eco_check.isChecked()
        material.description = self.desc_edit.toPlainText()
        
        self.update_material_list()
        
    def delete_material(self):
        current_item = self.material_list.currentItem()
        if not current_item:
            return
            
        name = current_item.text()
        reply = QMessageBox.question(self, "确认删除", f"确定要删除材料 '{name}' 吗?")
        if reply == QMessageBox.Yes:
            del self.material_lib.materials[name]
            self.update_material_list()

class CostCalculator(QDockWidget):
    """成本计算器"""
    def __init__(self, parent=None):
        super().__init__("成本计算", parent)
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        
        self.scene = None
        self.setup_ui()
        
    def setup_ui(self):
        widget = QWidget()
        layout = QVBoxLayout()
        
        # 计算选项
        options_group = QGroupBox("计算选项")
        options_layout = QHBoxLayout()
        
        options_layout.addWidget(QLabel("年限:"))
        self.years_spin = QSpinBox()
        self.years_spin.setRange(1, 50)
        self.years_spin.setValue(5)
        options_layout.addWidget(self.years_spin)
        
        options_layout.addWidget(QLabel("包含维护成本:"))
        self.maintenance_check = QCheckBox()
        self.maintenance_check.setChecked(True)
        options_layout.addWidget(self.maintenance_check)
        
        options_group.setLayout(options_layout)
        layout.addWidget(options_group)
        
        # 计算按钮
        self.calc_btn = QPushButton("计算成本")
        self.calc_btn.clicked.connect(self.calculate_costs)
        layout.addWidget(self.calc_btn)
        
        # 成本表格
        self.cost_table = QTableWidget()
        self.cost_table.setColumnCount(4)
        self.cost_table.setHorizontalHeaderLabels(["项目", "数量", "成本(元)", "维护成本(元)"])
        self.cost_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.cost_table)
        
        # 总计
        total_layout = QHBoxLayout()
        total_layout.addWidget(QLabel("初始成本:"))
        self.initial_cost_label = QLabel("0.00 元")
        self.initial_cost_label.setStyleSheet("font-weight: bold;")
        total_layout.addWidget(self.initial_cost_label)
        
        total_layout.addWidget(QLabel("维护成本:"))
        self.maintenance_cost_label = QLabel("0.00 元")
        self.maintenance_cost_label.setStyleSheet("font-weight: bold;")
        total_layout.addWidget(self.maintenance_cost_label)
        
        total_layout.addWidget(QLabel("总计:"))
        self.total_label = QLabel("0.00 元")
        self.total_label.setStyleSheet("font-weight: bold; font-size: 14pt; color: red;")
        total_layout.addWidget(self.total_label)
        
        layout.addLayout(total_layout)
        
        # 导出按钮
        self.export_btn = QPushButton("导出到CSV")
        self.export_btn.clicked.connect(self.export_to_csv)
        layout.addWidget(self.export_btn)
        
        widget.setLayout(layout)
        self.setWidget(widget)
        
    def set_scene(self, scene):
        self.scene = scene
        
    def calculate_costs(self):
        if not self.scene:
            return
            
        # 收集所有项目
        items = {
            "墙体": [],
            "地板": [],
            "门窗": [],
            "家具": []
        }
        
        for item in self.scene.items():
            if isinstance(item, WallItem):
                items["墙体"].append(item)
            elif isinstance(item, FloorItem):
                items["地板"].append(item)
            elif isinstance(item, FurnitureItem):
                items["家具"].append(item)
        
        # 计算成本
        initial_cost = 0
        maintenance_cost = 0
        years = self.years_spin.value()
        include_maintenance = self.maintenance_check.isChecked()
        
        self.cost_table.setRowCount(0)
        
        # 墙体成本
        wall_cost = 0
        wall_maintenance = 0
        for wall in items["墙体"]:
            wall_cost += wall.get_cost()
            if include_maintenance:
                wall_maintenance += wall.get_maintenance_cost(years)
        
        if wall_cost > 0:
            row = self.cost_table.rowCount()
            self.cost_table.insertRow(row)
            self.cost_table.setItem(row, 0, QTableWidgetItem("墙体"))
            self.cost_table.setItem(row, 1, QTableWidgetItem(f"{len(items['墙体'])} 面"))
            self.cost_table.setItem(row, 2, QTableWidgetItem(f"{wall_cost:.2f}"))
            self.cost_table.setItem(row, 3, QTableWidgetItem(f"{wall_maintenance:.2f}"))
            initial_cost += wall_cost
            maintenance_cost += wall_maintenance
        
        # 地板成本
        floor_cost = 0
        floor_maintenance = 0
        for floor in items["地板"]:
            floor_cost += floor.get_cost()
            if include_maintenance:
                floor_maintenance += floor.get_maintenance_cost(years)
        
        if floor_cost > 0:
            row = self.cost_table.rowCount()
            self.cost_table.insertRow(row)
            self.cost_table.setItem(row, 0, QTableWidgetItem("地板"))
            self.cost_table.setItem(row, 1, QTableWidgetItem(f"{len(items['地板'])} 块"))
            self.cost_table.setItem(row, 2, QTableWidgetItem(f"{floor_cost:.2f}"))
            self.cost_table.setItem(row, 3, QTableWidgetItem(f"{floor_maintenance:.2f}"))
            initial_cost += floor_cost
            maintenance_cost += floor_maintenance
        
        # 家具成本
        furniture_cost = 0
        furniture_maintenance = 0
        for furniture in items["家具"]:
            furniture_cost += furniture.get_cost()
            if include_maintenance:
                furniture_maintenance += furniture.get_maintenance_cost(years)
        
        if furniture_cost > 0:
            row = self.cost_table.rowCount()
            self.cost_table.insertRow(row)
            self.cost_table.setItem(row, 0, QTableWidgetItem("家具"))
            self.cost_table.setItem(row, 1, QTableWidgetItem(f"{len(items['家具'])} 件"))
            self.cost_table.setItem(row, 2, QTableWidgetItem(f"{furniture_cost:.2f}"))
            self.cost_table.setItem(row, 3, QTableWidgetItem(f"{furniture_maintenance:.2f}"))
            initial_cost += furniture_cost
            maintenance_cost += furniture_maintenance
        
        # 门窗成本 (需要从墙体中提取)
        door_window_cost = 0
        door_window_maintenance = 0
        door_count = 0
        window_count = 0
        
        for wall in items["墙体"]:
            for door in wall.doors:
                door_item = DoorItem(wall, door['position'])
                door_cost = door_item.get_cost()
                door_window_cost += door_cost
                if include_maintenance:
                    door_window_maintenance += door_item.get_maintenance_cost(years)
                door_count += 1
                
            for window in wall.windows:
                window_item = WindowItem(wall, window['position'])
                window_cost = window_item.get_cost()
                door_window_cost += window_cost
                if include_maintenance:
                    door_window_maintenance += window_item.get_maintenance_cost(years)
                window_count += 1
        
        if door_window_cost > 0:
            row = self.cost_table.rowCount()
            self.cost_table.insertRow(row)
            self.cost_table.setItem(row, 0, QTableWidgetItem("门窗"))
            self.cost_table.setItem(row, 1, QTableWidgetItem(f"{door_count}门 {window_count}窗"))
            self.cost_table.setItem(row, 2, QTableWidgetItem(f"{door_window_cost:.2f}"))
            self.cost_table.setItem(row, 3, QTableWidgetItem(f"{door_window_maintenance:.2f}"))
            initial_cost += door_window_cost
            maintenance_cost += door_window_maintenance
        
        total_cost = initial_cost + maintenance_cost
        
        self.initial_cost_label.setText(f"{initial_cost:.2f} 元")
        self.maintenance_cost_label.setText(f"{maintenance_cost:.2f} 元")
        self.total_label.setText(f"{total_cost:.2f} 元")
    
    def export_to_csv(self):
        if self.cost_table.rowCount() == 0:
            QMessageBox.warning(self, "警告", "没有数据可导出")
            return
            
        file_name, _ = QFileDialog.getSaveFileName(self, "导出CSV", "", "CSV文件 (*.csv)")
        if file_name:
            try:
                with open(file_name, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    
                    # 写入表头
                    headers = []
                    for col in range(self.cost_table.columnCount()):
                        headers.append(self.cost_table.horizontalHeaderItem(col).text())
                    writer.writerow(headers)
                    
                    # 写入数据
                    for row in range(self.cost_table.rowCount()):
                        row_data = []
                        for col in range(self.cost_table.columnCount()):
                            item = self.cost_table.item(row, col)
                            row_data.append(item.text() if item else "")
                        writer.writerow(row_data)
                    
                    # 写入总计
                    writer.writerow([])
                    writer.writerow(["初始成本:", self.initial_cost_label.text()])
                    writer.writerow(["维护成本:", self.maintenance_cost_label.text()])
                    writer.writerow(["总计:", self.total_label.text()])
                    
                QMessageBox.information(self, "成功", f"数据已导出到 {file_name}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导出失败: {str(e)}")

class FurnitureLibrary(QDockWidget):
    """家具库"""
    def __init__(self, parent=None):
        super().__init__("家具库", parent)
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        
        self.scene = None
        self.setup_ui()
        
    def setup_ui(self):
        widget = QWidget()
        layout = QVBoxLayout()
        
        # 搜索框
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("搜索:"))
        self.search_edit = QLineEdit()
        self.search_edit.textChanged.connect(self.filter_furniture)
        search_layout.addWidget(self.search_edit)
        layout.addLayout(search_layout)
        
        # 分类筛选
        category_layout = QHBoxLayout()
        category_layout.addWidget(QLabel("分类:"))
        self.category_combo = QComboBox()
        self.category_combo.addItems(["全部", "客厅", "卧室", "厨房", "浴室", "办公室"])
        self.category_combo.currentTextChanged.connect(self.filter_furniture)
        category_layout.addWidget(self.category_combo)
        layout.addLayout(category_layout)
        
        # 家具列表
        self.furniture_list = QListWidget()
        self.furniture_list.itemDoubleClicked.connect(self.add_furniture_to_scene)
        layout.addWidget(self.furniture_list)
        
        # 家具属性
        prop_group = QGroupBox("家具属性")
        prop_layout = QGridLayout()
        
        prop_layout.addWidget(QLabel("宽度(cm):"), 0, 0)
        self.width_spin = QSpinBox()
        self.width_spin.setRange(10, 500)
        self.width_spin.setValue(100)
        prop_layout.addWidget(self.width_spin, 0, 1)
        
        prop_layout.addWidget(QLabel("深度(cm):"), 1, 0)
        self.depth_spin = QSpinBox()
        self.depth_spin.setRange(10, 500)
        self.depth_spin.setValue(60)
        prop_layout.addWidget(self.depth_spin, 1, 1)
        
        prop_layout.addWidget(QLabel("高度(cm):"), 2, 0)
        self.height_spin = QSpinBox()
        self.height_spin.setRange(10, 300)
        self.height_spin.setValue(80)
        prop_layout.addWidget(self.height_spin, 2, 1)
        
        prop_layout.addWidget(QLabel("颜色:"), 3, 0)
        self.color_btn = QPushButton()
        self.color_btn.clicked.connect(self.choose_color)
        self.color_btn.setStyleSheet("background-color: rgb(200, 150, 100)")
        self.color_btn.setFixedSize(50, 25)
        prop_layout.addWidget(self.color_btn, 3, 1)
        
        prop_group.setLayout(prop_layout)
        layout.addWidget(prop_group)
        
        # 添加按钮
        self.add_btn = QPushButton("添加到场景")
        self.add_btn.clicked.connect(self.add_furniture_to_scene)
        layout.addWidget(self.add_btn)
        
        widget.setLayout(layout)
        self.setWidget(widget)
        
        # 加载家具数据
        self.furniture_items = [
            {"name": "沙发", "width": 200, "depth": 80, "height": 80, "color": QColor(200, 150, 100), "category": "客厅"},
            {"name": "餐桌", "width": 150, "depth": 100, "height": 75, "color": QColor(150, 120, 90), "category": "厨房"},
            {"name": "床", "width": 180, "depth": 200, "height": 50, "color": QColor(180, 140, 120), "category": "卧室"},
            {"name": "椅子", "width": 50, "depth": 50, "height": 90, "color": QColor(150, 130, 110), "category": "餐厅"},
            {"name": "书桌", "width": 120, "depth": 70, "height": 75, "color": QColor(160, 140, 120), "category": "办公室"},
            {"name": "衣柜", "width": 100, "depth": 60, "height": 200, "color": QColor(170, 150, 130), "category": "卧室"},
            {"name": "书柜", "width": 120, "depth": 40, "height": 200, "color": QColor(160, 140, 120), "category": "办公室"},
            {"name": "电视柜", "width": 180, "depth": 40, "height": 50, "color": QColor(170, 150, 130), "category": "客厅"},
            {"name": "洗手台", "width": 100, "depth": 50, "height": 85, "color": QColor(200, 200, 200), "category": "浴室"},
            {"name": "马桶", "width": 70, "depth": 60, "height": 40, "color": QColor(200, 200, 200), "category": "浴室"},
        ]
        
        self.update_furniture_list()
        
    def set_scene(self, scene):
        self.scene = scene
        
    def choose_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.color_btn.setStyleSheet(f"background-color: {color.name()}")
            self.current_color = color
            
    def update_furniture_list(self):
        self.furniture_list.clear()
        for item in self.furniture_items:
            self.furniture_list.addItem(item["name"])
            
    def filter_furniture(self):
        search_text = self.search_edit.text().lower()
        category = self.category_combo.currentText()
        
        self.furniture_list.clear()
        for item in self.furniture_items:
            if (search_text in item["name"].lower() or not search_text) and \
               (category == "全部" or category == item["category"]):
                self.furniture_list.addItem(item["name"])
                
    def add_furniture_to_scene(self, item=None):
        if not self.scene:
            return
            
        if isinstance(item, QListWidgetItem):
            # 从列表双击添加
            index = self.furniture_list.row(item)
            if 0 <= index < len(self.furniture_items):
                furniture_data = self.furniture_items[index]
                furniture = FurnitureItem(
                    100, 100, 
                    furniture_data["width"], 
                    furniture_data["depth"],
                    furniture_data["name"],
                    furniture_data["color"],
                    furniture_data["height"]
                )
                self.scene.addItem(furniture)
        else:
            # 从属性设置添加
            current_item = self.furniture_list.currentItem()
            if current_item:
                index = self.furniture_list.row(current_item)
                furniture_data = self.furniture_items[index]
                
                furniture = FurnitureItem(
                    100, 100,
                    self.width_spin.value(),
                    self.depth_spin.value(),
                    furniture_data["name"],
                    self.current_color if hasattr(self, 'current_color') else furniture_data["color"],
                    self.height_spin.value()
                )
                self.scene.addItem(furniture)

class HouseDesignToolBar(QToolBar):
    """房屋设计工具栏"""
    def __init__(self, parent=None):
        super().__init__("工具", parent)
        
        self.parent = parent
        
        # 选择工具
        select_action = QAction(QIcon(":/icons/select.png"), "选择", self)
        select_action.setCheckable(True)
        select_action.setChecked(True)
        select_action.triggered.connect(lambda: self.set_tool("select"))
        self.addAction(select_action)
        
        # 墙体工具
        wall_action = QAction(QIcon(":/icons/wall.png"), "墙体", self)
        wall_action.setCheckable(True)
        wall_action.triggered.connect(lambda: self.set_tool("wall"))
        self.addAction(wall_action)
        
        # 地板工具
        floor_action = QAction(QIcon(":/icons/floor.png"), "地板", self)
        floor_action.setCheckable(True)
        floor_action.triggered.connect(lambda: self.set_tool("floor"))
        self.addAction(floor_action)
        
        # 门工具
        door_action = QAction(QIcon(":/icons/door.png"), "门", self)
        door_action.setCheckable(True)
        door_action.triggered.connect(lambda: self.set_tool("door"))
        self.addAction(door_action)
        
        # 窗工具
        window_action = QAction(QIcon(":/icons/window.png"), "窗", self)
        window_action.setCheckable(True)
        window_action.triggered.connect(lambda: self.set_tool("window"))
        self.addAction(window_action)
        
        self.addSeparator()
        
        # 删除工具
        delete_action = QAction(QIcon(":/icons/delete.png"), "删除", self)
        delete_action.triggered.connect(self.delete_selected)
        self.addAction(delete_action)
        
        # 材料工具
        material_action = QAction(QIcon(":/icons/material.png"), "材料编辑器", self)
        material_action.triggered.connect(self.open_material_editor)
        self.addAction(material_action)
        
        # 房间检测工具
        room_action = QAction(QIcon(":/icons/room.png"), "检测房间", self)
        room_action.triggered.connect(self.detect_rooms)
        self.addAction(room_action)
        
        # 创建动作组确保只有一个工具被选中
        self.action_group = QActionGroup(self)
        self.action_group.addAction(select_action)
        self.action_group.addAction(wall_action)
        self.action_group.addAction(floor_action)
        self.action_group.addAction(door_action)
        self.action_group.addAction(window_action)
        self.action_group.setExclusive(True)
        
    def set_tool(self, tool):
        if hasattr(self.parent, 'scene'):
            self.parent.scene.current_tool = tool
            
    def delete_selected(self):
        if hasattr(self.parent, 'scene'):
            for item in self.parent.scene.selectedItems():
                self.parent.scene.removeItem(item)
                
    def open_material_editor(self):
        if hasattr(self.parent, 'material_lib'):
            editor = MaterialEditor(self.parent.material_lib, self.parent)
            editor.exec_()
            
    def detect_rooms(self):
        if hasattr(self.parent, 'scene'):
            self.parent.scene.auto_detect_rooms()

class HouseDesignMainWindow(QMainWindow):
    """房屋设计主窗口"""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("高级房屋设计工具")
        self.setGeometry(100, 100, 1400, 900)
        
        # 初始化材料库
        self.material_lib = MaterialLibrary()
        
        # 创建场景和视图
        self.scene = HouseDesignScene()
        self.view = HouseDesignView(self.scene)
        self.setCentralWidget(self.view)
        
        # 创建3D视图
        self.three_d_view = ThreeDView()
        self.three_d_dock = QDockWidget("3D预览", self)
        self.three_d_dock.setWidget(self.three_d_view)
        self.addDockWidget(Qt.RightDockWidgetArea, self.three_d_dock)
        
        # 创建工具栏
        self.toolbar = HouseDesignToolBar(self)
        self.addToolBar(self.toolbar)
        
        # 创建状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪")
        
        # 创建家具库
        self.furniture_lib = FurnitureLibrary(self)
        self.furniture_lib.set_scene(self.scene)
        self.addDockWidget(Qt.RightDockWidgetArea, self.furniture_lib)
        
        # 创建成本计算器
        self.cost_calculator = CostCalculator(self)
        self.cost_calculator.set_scene(self.scene)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.cost_calculator)
        
        # 创建菜单
        self.create_menus()
        
        # 添加一些示例家具
        self.add_sample_furniture()
        
        # 定时更新3D视图
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_3d_view)
        self.timer.start(1000)  # 每秒更新一次
        
    def update_3d_view(self):
        # 收集场景中的墙体、家具和地板
        walls = []
        furniture = []
        floors = []
        
        for item in self.scene.items():
            if isinstance(item, WallItem):
                walls.append(item)
            elif isinstance(item, FurnitureItem):
                furniture.append(item)
            elif isinstance(item, FloorItem):
                floors.append(item)
                
        self.three_d_view.set_scene_data(walls, furniture, floors)
        
    def create_menus(self):
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu("文件")
        
        new_action = QAction("新建", self)
        new_action.setShortcut(QKeySequence.New)
        new_action.triggered.connect(self.new_file)
        file_menu.addAction(new_action)
        
        open_action = QAction("打开", self)
        open_action.setShortcut(QKeySequence.Open)
        open_action.triggered.connect(self.open_file)
        file_menu.addAction(open_action)
        
        save_action = QAction("保存", self)
        save_action.setShortcut(QKeySequence.Save)
        save_action.triggered.connect(self.save_file)
        file_menu.addAction(save_action)
        
        export_3d_action = QAction("导出3D模型", self)
        export_3d_action.triggered.connect(self.export_3d_model)
        file_menu.addAction(export_3d_action)
        
        export_image_action = QAction("导出图像", self)
        export_image_action.triggered.connect(self.export_image)
        file_menu.addAction(export_image_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("退出", self)
        exit_action.setShortcut(QKeySequence.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 编辑菜单
        edit_menu = menubar.addMenu("编辑")
        
        undo_action = QAction("撤销", self)
        undo_action.setShortcut(QKeySequence.Undo)
        edit_menu.addAction(undo_action)
        
        redo_action = QAction("重做", self)
        redo_action.setShortcut(QKeySequence.Redo)
        edit_menu.addAction(redo_action)
        
        edit_menu.addSeparator()
        
        delete_action = QAction("删除", self)
        delete_action.setShortcut(QKeySequence.Delete)
        delete_action.triggered.connect(self.delete_selected)
        edit_menu.addAction(delete_action)
        
        # 视图菜单
        view_menu = menubar.addMenu("视图")
        
        zoom_in_action = QAction("放大", self)
        zoom_in_action.setShortcut(QKeySequence.ZoomIn)
        zoom_in_action.triggered.connect(self.zoom_in)
        view_menu.addAction(zoom_in_action)
        
        zoom_out_action = QAction("缩小", self)
        zoom_out_action.setShortcut(QKeySequence.ZoomOut)
        zoom_out_action.triggered.connect(self.zoom_out)
        view_menu.addAction(zoom_out_action)
        
        reset_zoom_action = QAction("重置缩放", self)
        reset_zoom_action.triggered.connect(self.reset_zoom)
        view_menu.addAction(reset_zoom_action)
        
        view_menu.addSeparator()
        
        grid_action = QAction("显示网格", self)
        grid_action.setCheckable(True)
        grid_action.setChecked(True)
        grid_action.triggered.connect(self.toggle_grid)
        view_menu.addAction(grid_action)
        
        snap_action = QAction("吸附到网格", self)
        snap_action.setCheckable(True)
        snap_action.setChecked(True)
        snap_action.triggered.connect(self.toggle_snap)
        view_menu.addAction(snap_action)
        
        view_menu.addSeparator()
        
        show_3d_action = QAction("显示3D视图", self)
        show_3d_action.setCheckable(True)
        show_3d_action.setChecked(True)
        show_3d_action.triggered.connect(self.toggle_3d_view)
        view_menu.addAction(show_3d_action)
        
        # 工具菜单
        tools_menu = menubar.addMenu("工具")
        
        add_dimension_action = QAction("添加尺寸标注", self)
        add_dimension_action.triggered.connect(self.add_dimension)
        tools_menu.addAction(add_dimension_action)
        
        calculate_cost_action = QAction("计算成本", self)
        calculate_cost_action.triggered.connect(self.calculate_cost)
        tools_menu.addAction(calculate_cost_action)
        
        material_editor_action = QAction("材料编辑器", self)
        material_editor_action.triggered.connect(self.open_material_editor)
        tools_menu.addAction(material_editor_action)
        
        detect_rooms_action = QAction("检测房间", self)
        detect_rooms_action.triggered.connect(self.detect_rooms)
        tools_menu.addAction(detect_rooms_action)
        
        # 设置菜单
        settings_menu = menubar.addMenu("设置")
        
        wall_properties_action = QAction("墙体属性", self)
        wall_properties_action.triggered.connect(self.wall_properties)
        settings_menu.addAction(wall_properties_action)
        
        floor_properties_action = QAction("地板属性", self)
        floor_properties_action.triggered.connect(self.floor_properties)
        settings_menu.addAction(floor_properties_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu("帮助")
        
        about_action = QAction("关于", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
    def add_sample_furniture(self):
        # 添加一些示例家具
        sofa = FurnitureItem(300, 300, 200, 80, "沙发", QColor(200, 150, 100), 80)
        self.scene.addItem(sofa)
        
        table = FurnitureItem(500, 400, 150, 100, "餐桌", QColor(150, 120, 90), 75)
        self.scene.addItem(table)
        
        bed = FurnitureItem(800, 300, 180, 200, "床", QColor(180, 140, 120), 50)
        self.scene.addItem(bed)
        
    def new_file(self):
        reply = QMessageBox.question(self, "新建文件", 
                                   "是否保存当前设计？",
                                   QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
        if reply == QMessageBox.Save:
            self.save_file()
        elif reply == QMessageBox.Discard:
            self.scene.clear()
            self.status_bar.showMessage("已创建新文件")
        # 如果选择取消，不做任何操作
        
    def open_file(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "打开设计文件", "", "设计文件 (*.json)")
        if file_name:
            try:
                with open(file_name, 'r') as f:
                    data = json.load(f)
                    
                self.scene.clear()
                
                # 加载材料
                if "materials" in data:
                    self.material_lib.load_from_dict(data["materials"])
                
                # 加载墙体
                if "walls" in data:
                    for wall_data in data["walls"]:
                        start = QPointF(wall_data["start"]["x"], wall_data["start"]["y"])
                        end = QPointF(wall_data["end"]["x"], wall_data["end"]["y"])
                        wall = WallItem(start, end, wall_data["height"], wall_data["thickness"])
                        wall.material = self.material_lib.get_material(wall_data["material"])
                        wall.windows = wall_data["windows"]
                        wall.doors = wall_data["doors"]
                        self.scene.addItem(wall)
                
                # 加载地板
                if "floors" in data:
                    for floor_data in data["floors"]:
                        rect = QRectF(floor_data["x"], floor_data["y"], floor_data["width"], floor_data["height"])
                        floor = FloorItem(rect)
                        floor.material = self.material_lib.get_material(floor_data["material"])
                        self.scene.addItem(floor)
                
                # 加载家具
                if "furniture" in data:
                    for furniture_data in data["furniture"]:
                        furniture = FurnitureItem(
                            furniture_data["x"], furniture_data["y"],
                            furniture_data["width"], furniture_data["height"],
                            furniture_data["name"], QColor(*furniture_data["color"]),
                            furniture_data["height_3d"]
                        )
                        furniture.material = self.material_lib.get_material(furniture_data["material"])
                        self.scene.addItem(furniture)
                
                self.status_bar.showMessage(f"已打开文件: {file_name}")
                
            except Exception as e:
                QMessageBox.critical(self, "错误", f"打开文件时出错: {str(e)}")
            
    def save_file(self):
        file_name, _ = QFileDialog.getSaveFileName(self, "保存设计文件", "", "设计文件 (*.json)")
        if file_name:
            try:
                data = {
                    "materials": self.material_lib.to_dict(),
                    "walls": [],
                    "floors": [],
                    "furniture": []
                }
                
                # 保存墙体
                for item in self.scene.items():
                    if isinstance(item, WallItem):
                        wall_data = {
                            "start": {"x": item.start_point.x(), "y": item.start_point.y()},
                            "end": {"x": item.end_point.x(), "y": item.end_point.y()},
                            "height": item.height,
                            "thickness": item.thickness,
                            "material": item.material.name,
                            "windows": item.windows,
                            "doors": item.doors
                        }
                        data["walls"].append(wall_data)
                    
                    elif isinstance(item, FloorItem):
                        rect = item.rect()
                        floor_data = {
                            "x": rect.x(),
                            "y": rect.y(),
                            "width": rect.width(),
                            "height": rect.height(),
                            "material": item.material.name
                        }
                        data["floors"].append(floor_data)
                    
                    elif isinstance(item, FurnitureItem):
                        rect = item.rect()
                        furniture_data = {
                            "x": rect.x(),
                            "y": rect.y(),
                            "width": rect.width(),
                            "height": rect.height(),
                            "name": item.name,
                            "color": (item.color.red(), item.color.green(), item.color.blue(), item.color.alpha()),
                            "height_3d": item.height_3d,
                            "material": item.material.name
                        }
                        data["furniture"].append(furniture_data)
                
                with open(file_name, 'w') as f:
                    json.dump(data, f, indent=4)
                
                self.status_bar.showMessage(f"已保存文件: {file_name}")
                
            except Exception as e:
                QMessageBox.critical(self, "错误", f"保存文件时出错: {str(e)}")
            
    def delete_selected(self):
        for item in self.scene.selectedItems():
            self.scene.removeItem(item)
            
    def zoom_in(self):
        self.view.scale(1.25, 1.25)
        
    def zoom_out(self):
        self.view.scale(0.8, 0.8)
        
    def reset_zoom(self):
        self.view.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)
        
    def toggle_grid(self):
        # 切换网格显示
        self.scene.grid_size = 20 if self.scene.grid_size == 0 else 0
        self.scene.update()
        
    def toggle_snap(self):
        self.scene.snap_to_grid = not self.scene.snap_to_grid
        
    def toggle_3d_view(self):
        if self.three_d_dock.isVisible():
            self.three_d_dock.hide()
        else:
            self.three_d_dock.show()
        
    def add_dimension(self):
        # 添加尺寸标注
        if len(self.scene.selectedItems()) == 1:
            item = self.scene.selectedItems()[0]
            if isinstance(item, WallItem):
                line = item.line()
                length = line.length()
                dimension = DimensionItem(line.p1(), line.p2(), f"{length:.0f} cm")
                self.scene.addItem(dimension)
                
    def calculate_cost(self):
        self.cost_calculator.calculate_costs()
        
    def open_material_editor(self):
        editor = MaterialEditor(self.material_lib, self)
        editor.exec_()
        
    def detect_rooms(self):
        self.scene.auto_detect_rooms()
        
    def wall_properties(self):
        if len(self.scene.selectedItems()) == 1:
            item = self.scene.selectedItems()[0]
            if isinstance(item, WallItem):
                dialog = QDialog(self)
                dialog.setWindowTitle("墙体属性")
                layout = QVBoxLayout()
                
                # 高度设置
                height_layout = QHBoxLayout()
                height_layout.addWidget(QLabel("高度(cm):"))
                height_spin = QSpinBox()
                height_spin.setRange(100, 500)
                height_spin.setValue(item.height)
                height_layout.addWidget(height_spin)
                layout.addLayout(height_layout)
                
                # 厚度设置
                thickness_layout = QHBoxLayout()
                thickness_layout.addWidget(QLabel("厚度(cm):"))
                thickness_spin = QSpinBox()
                thickness_spin.setRange(5, 50)
                thickness_spin.setValue(item.thickness)
                thickness_layout.addWidget(thickness_spin)
                layout.addLayout(thickness_layout)
                
                # 材料选择
                material_layout = QHBoxLayout()
                material_layout.addWidget(QLabel("材料:"))
                material_combo = QComboBox()
                materials = self.material_lib.get_materials_by_category("墙体")
                for material in materials:
                    material_combo.addItem(material.name, material)
                material_combo.setCurrentText(item.material.name)
                material_layout.addWidget(material_combo)
                layout.addLayout(material_layout)
                
                # 按钮
                btn_layout = QHBoxLayout()
                ok_btn = QPushButton("确定")
                ok_btn.clicked.connect(dialog.accept)
                btn_layout.addWidget(ok_btn)
                
                cancel_btn = QPushButton("取消")
                cancel_btn.clicked.connect(dialog.reject)
                btn_layout.addWidget(cancel_btn)
                
                layout.addLayout(btn_layout)
                dialog.setLayout(layout)
                
                if dialog.exec_() == QDialog.Accepted:
                    item.height = height_spin.value()
                    item.thickness = thickness_spin.value()
                    item.material = material_combo.currentData()
                    self.scene.update()
                    
    def floor_properties(self):
        if len(self.scene.selectedItems()) == 1:
            item = self.scene.selectedItems()[0]
            if isinstance(item, FloorItem):
                dialog = QDialog(self)
                dialog.setWindowTitle("地板属性")
                layout = QVBoxLayout()
                
                # 材料选择
                material_layout = QHBoxLayout()
                material_layout.addWidget(QLabel("材料:"))
                material_combo = QComboBox()
                materials = self.material_lib.get_materials_by_category("地板")
                for material in materials:
                    material_combo.addItem(material.name, material)
                material_combo.setCurrentText(item.material.name)
                material_layout.addWidget(material_combo)
                layout.addLayout(material_layout)
                
                # 按钮
                btn_layout = QHBoxLayout()
                ok_btn = QPushButton("确定")
                ok_btn.clicked.connect(dialog.accept)
                btn_layout.addWidget(ok_btn)
                
                cancel_btn = QPushButton("取消")
                cancel_btn.clicked.connect(dialog.reject)
                btn_layout.addWidget(cancel_btn)
                
                layout.addLayout(btn_layout)
                dialog.setLayout(layout)
                
                if dialog.exec_() == QDialog.Accepted:
                    item.material = material_combo.currentData()
                    item.setBrush(QBrush(item.material.color))
                    self.scene.update()
    
    def export_3d_model(self):
        # 这里应该实现导出为OBJ或其他3D格式的功能
        QMessageBox.information(self, "导出3D模型", "3D模型导出功能将在未来版本中提供")
    
    def export_image(self):
        file_name, _ = QFileDialog.getSaveFileName(self, "导出图像", "", "PNG图像 (*.png);;JPEG图像 (*.jpg)")
        if file_name:
            try:
                # 创建图像
                img = QImage(self.view.viewport().size(), QImage.Format_ARGB32)
                img.fill(Qt.white)
                
                # 绘制场景到图像
                painter = QPainter(img)
                self.view.render(painter)
                painter.end()
                
                # 保存图像
                img.save(file_name)
                QMessageBox.information(self, "成功", f"图像已导出到 {file_name}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导出图像失败: {str(e)}")
            
    def show_about(self):
        QMessageBox.about(self, "关于高级房屋设计工具", 
                         "这是一个基于PyQt的高级房屋设计工具\n\n"
                         "功能包括:\n"
                         "- 2D/3D视图设计\n"
                         "- 墙体、地板、门窗设计\n"
                         "- 家具布局\n"
                         "- 材料管理和成本计算\n"
                         "- 尺寸标注和房间检测\n\n"
                         "版本 2.0")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 设置应用程序图标和样式
    app.setApplicationName("高级房屋设计工具")
    app.setStyle("Fusion")
    
    window = HouseDesignMainWindow()
    window.show()
    
    sys.exit(app.exec_())