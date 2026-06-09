import sys
import json
import math
from enum import Enum
from typing import List, Dict, Any, Optional, Tuple

from PyQt5.QtWidgets import (QActionGroup, QApplication, QListWidgetItem, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QToolBar, QAction, QLabel, QComboBox,
                             QSpinBox, QDoubleSpinBox, QColorDialog, QFileDialog,
                             QMessageBox, QDockWidget, QListWidget, QSplitter,
                             QGraphicsView, QGraphicsScene, QGraphicsItem,
                             QMenu, QInputDialog, QToolButton, QCheckBox)
from PyQt5.QtCore import Qt, QPointF, QRectF, pyqtSignal, QLineF, QSize
from PyQt5.QtGui import (QPainter, QPen, QBrush, QColor, QFont, QPainterPath,
                         QMouseEvent, QKeyEvent, QTransform, QIcon, QCursor,
                         QPixmap, QRadialGradient)

# 工具类型枚举
class ToolType(Enum):
    SELECT = 0
    PAN = 1
    ZOOM = 2
    POINT = 3
    LINE = 4
    RECTANGLE = 5
    CIRCLE = 6
    POLYGON = 7
    TEXT = 8
    MEASURE = 9

# 图层类型
class LayerType(Enum):
    BASE = 0
    OVERLAY = 1
    TEMPORARY = 2

# 地图对象基类
class MapObject(QGraphicsItem):
    def __init__(self, obj_id: str, layer_id: str):
        super().__init__()
        self.obj_id = obj_id
        self.layer_id = layer_id
        self.selected = False
        self.pen = QPen(Qt.black, 2)
        self.brush = QBrush(Qt.transparent)
        self.z_value = 0
        self.setZValue(self.z_value)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        
    def set_style(self, pen: QPen, brush: QBrush):
        self.pen = pen
        self.brush = brush
        self.update()
        
    def mousePressEvent(self, event):
        self.selected = True
        self.update()
        super().mousePressEvent(event)
        
    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        
    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemSelectedChange:
            self.selected = value
            self.update()
        return super().itemChange(change, value)

# 点对象
class PointObject(MapObject):
    def __init__(self, obj_id: str, layer_id: str, point: QPointF, radius=5):
        super().__init__(obj_id, layer_id)
        self.point = point
        self.radius = radius
        self.setPos(point)
        
    def boundingRect(self):
        return QRectF(-self.radius, -self.radius, 2*self.radius, 2*self.radius)
        
    def paint(self, painter, option, widget):
        painter.setPen(self.pen)
        painter.setBrush(self.brush if not self.selected else QBrush(QColor(255, 0, 0, 100)))
        painter.drawEllipse(-self.radius, -self.radius, 2*self.radius, 2*self.radius)

# 线对象
class LineObject(MapObject):
    def __init__(self, obj_id: str, layer_id: str, points: List[QPointF]):
        super().__init__(obj_id, layer_id)
        self.points = points
        self.update_path()
        
    def update_path(self):
        self.path = QPainterPath()
        if len(self.points) > 0:
            self.path.moveTo(self.points[0])
            for point in self.points[1:]:
                self.path.lineTo(point)
                
    def boundingRect(self):
        return self.path.boundingRect().adjusted(-5, -5, 5, 5)
        
    def paint(self, painter, option, widget):
        painter.setPen(self.pen)
        painter.setBrush(self.brush)
        painter.drawPath(self.path)
        
        if self.selected:
            painter.setPen(QPen(Qt.red, 1, Qt.DashLine))
            painter.setBrush(QBrush(Qt.transparent))
            painter.drawPath(self.path)
            
            # 绘制控制点
            painter.setPen(QPen(Qt.blue, 2))
            painter.setBrush(QBrush(Qt.blue))
            for point in self.points:
                painter.drawEllipse(point, 3, 3)

# 多边形对象
class PolygonObject(MapObject):
    def __init__(self, obj_id: str, layer_id: str, points: List[QPointF]):
        super().__init__(obj_id, layer_id)
        self.points = points
        self.update_polygon()
        
    def update_polygon(self):
        self.polygon = QPainterPath()
        if len(self.points) > 0:
            self.polygon.moveTo(self.points[0])
            for point in self.points[1:]:
                self.polygon.lineTo(point)
            self.polygon.closeSubpath()
                
    def boundingRect(self):
        return self.polygon.boundingRect().adjusted(-5, -5, 5, 5)
        
    def paint(self, painter, option, widget):
        painter.setPen(self.pen)
        painter.setBrush(self.brush)
        painter.drawPath(self.polygon)
        
        if self.selected:
            painter.setPen(QPen(Qt.red, 1, Qt.DashLine))
            painter.setBrush(QBrush(Qt.transparent))
            painter.drawPath(self.polygon)
            
            # 绘制控制点
            painter.setPen(QPen(Qt.blue, 2))
            painter.setBrush(QBrush(Qt.blue))
            for point in self.points:
                painter.drawEllipse(point, 3, 3)

# 文本对象
class TextObject(MapObject):
    def __init__(self, obj_id: str, layer_id: str, point: QPointF, text: str):
        super().__init__(obj_id, layer_id)
        self.point = point
        self.text = text
        self.font = QFont("Arial", 12)
        self.setPos(point)
        
    def boundingRect(self):
        fm = QFontMetrics(self.font)
        rect = fm.boundingRect(self.text)
        return QRectF(rect).adjusted(-2, -2, 2, 2)
        
    def paint(self, painter, option, widget):
        painter.setPen(self.pen)
        painter.setFont(self.font)
        painter.drawText(0, 0, self.text)
        
        if self.selected:
            rect = self.boundingRect()
            painter.setPen(QPen(Qt.red, 1, Qt.DashLine))
            painter.setBrush(QBrush(Qt.transparent))
            painter.drawRect(rect)

# 图层类
class MapLayer:
    def __init__(self, layer_id: str, name: str, layer_type: LayerType, visible=True):
        self.layer_id = layer_id
        self.name = name
        self.layer_type = layer_type
        self.visible = visible
        self.objects = {}  # obj_id -> MapObject
        self.z_index = 0
        
    def add_object(self, obj: MapObject):
        self.objects[obj.obj_id] = obj
        obj.setZValue(self.z_index)
        
    def remove_object(self, obj_id: str):
        if obj_id in self.objects:
            del self.objects[obj_id]
            
    def set_visible(self, visible: bool):
        self.visible = visible
        for obj in self.objects.values():
            obj.setVisible(visible)
            
    def clear(self):
        self.objects.clear()

# 地图视图类
class MapView(QGraphicsView):
    # 信号定义
    mouseMoved = pyqtSignal(QPointF)
    objectSelected = pyqtSignal(str, str)  # obj_id, layer_id
    toolChanged = pyqtSignal(ToolType)
    
    def __init__(self):
        super().__init__()
        self.scene = QGraphicsScene()
        self.setScene(self.scene)
        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        
        # 地图状态
        self.scale_factor = 1.0
        self.min_scale = 0.1
        self.max_scale = 10.0
        
        # 工具状态
        self.current_tool = ToolType.SELECT
        self.drawing = False
        self.temp_object = None
        self.current_points = []
        
        # 图层管理
        self.layers = {}  # layer_id -> MapLayer
        self.current_layer_id = None
        
        # 样式设置
        self.grid_visible = True
        self.snap_to_grid = False
        self.grid_size = 20
        
        # 测量工具
        self.measure_points = []
        self.measure_texts = []
        
    def add_layer(self, layer: MapLayer):
        self.layers[layer.layer_id] = layer
        if self.current_layer_id is None:
            self.current_layer_id = layer.layer_id
            
        # 将图层中的对象添加到场景
        for obj in layer.objects.values():
            self.scene.addItem(obj)
            
    def remove_layer(self, layer_id: str):
        if layer_id in self.layers:
            layer = self.layers[layer_id]
            for obj in layer.objects.values():
                self.scene.removeItem(obj)
            del self.layers[layer_id]
            
    def set_current_layer(self, layer_id: str):
        if layer_id in self.layers:
            self.current_layer_id = layer_id
            
    def get_current_layer(self) -> Optional[MapLayer]:
        if self.current_layer_id in self.layers:
            return self.layers[self.current_layer_id]
        return None
            
    def set_tool(self, tool: ToolType):
        self.current_tool = tool
        self.toolChanged.emit(tool)
        
        # 根据工具设置光标和拖拽模式
        if tool == ToolType.SELECT:
            self.setDragMode(QGraphicsView.RubberBandDrag)
            self.setCursor(Qt.ArrowCursor)
        elif tool == ToolType.PAN:
            self.setDragMode(QGraphicsView.ScrollHandDrag)
            self.setCursor(Qt.OpenHandCursor)
        elif tool == ToolType.ZOOM:
            self.setDragMode(QGraphicsView.NoDrag)
            self.setCursor(Qt.CrossCursor)
        else:  # 绘图工具
            self.setDragMode(QGraphicsView.NoDrag)
            self.setCursor(Qt.CrossCursor)
            
    def wheelEvent(self, event):
        if self.current_tool == ToolType.ZOOM:
            # 缩放处理
            factor = 1.2
            if event.angleDelta().y() < 0:
                factor = 1.0 / factor
                
            new_scale = self.scale_factor * factor
            if self.min_scale <= new_scale <= self.max_scale:
                self.scale_factor = new_scale
                self.setTransform(QTransform().scale(self.scale_factor, self.scale_factor))
        else:
            super().wheelEvent(event)
            
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            scene_pos = self.mapToScene(event.pos())
            
            if self.current_tool == ToolType.POINT:
                self.add_point(scene_pos)
            elif self.current_tool in [ToolType.LINE, ToolType.POLYGON, ToolType.RECTANGLE, ToolType.CIRCLE]:
                self.start_drawing(scene_pos)
            elif self.current_tool == ToolType.TEXT:
                self.add_text(scene_pos)
            elif self.current_tool == ToolType.MEASURE:
                self.start_measure(scene_pos)
                
        super().mousePressEvent(event)
        
    def mouseMoveEvent(self, event):
        scene_pos = self.mapToScene(event.pos())
        self.mouseMoved.emit(scene_pos)
        
        if self.drawing and self.temp_object:
            self.update_temp_object(scene_pos)
            
        super().mouseMoveEvent(event)
        
    def mouseDoubleClickEvent(self, event):
        if self.current_tool == ToolType.POLYGON and self.drawing:
            self.finish_drawing()
            
        super().mouseDoubleClickEvent(event)
        
    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_Escape and self.drawing:
            self.cancel_drawing()
            
        super().keyPressEvent(event)
        
    def start_drawing(self, start_point: QPointF):
        self.drawing = True
        self.current_points = [start_point]
        
        if self.current_tool == ToolType.LINE:
            self.temp_object = LineObject("temp", "temp", self.current_points)
        elif self.current_tool == ToolType.POLYGON:
            self.temp_object = PolygonObject("temp", "temp", self.current_points)
        elif self.current_tool == ToolType.RECTANGLE:
            self.temp_object = PolygonObject("temp", "temp", self.current_points)
        elif self.current_tool == ToolType.CIRCLE:
            self.temp_object = PolygonObject("temp", "temp", self.current_points)
            
        if self.temp_object:
            self.temp_object.setZValue(1000)  # 临时对象在最上层
            self.scene.addItem(self.temp_object)
            
    def update_temp_object(self, current_point: QPointF):
        if not self.temp_object or not self.current_points:
            return
            
        points = self.current_points.copy()
        points.append(current_point)
        
        if self.current_tool == ToolType.LINE:
            self.temp_object.points = points
            self.temp_object.update_path()
        elif self.current_tool == ToolType.POLYGON:
            self.temp_object.points = points
            self.temp_object.update_polygon()
        elif self.current_tool == ToolType.RECTANGLE:
            if len(points) >= 2:
                start = points[0]
                end = points[-1]
                rect_points = [
                    start,
                    QPointF(end.x(), start.y()),
                    end,
                    QPointF(start.x(), end.y())
                ]
                self.temp_object.points = rect_points
                self.temp_object.update_polygon()
        elif self.current_tool == ToolType.CIRCLE:
            if len(points) >= 2:
                center = points[0]
                radius = QLineF(center, points[-1]).length()
                
                # 近似圆为多边形
                circle_points = []
                for i in range(36):  # 36边近似圆
                    angle = i * 10 * math.pi / 180
                    x = center.x() + radius * math.cos(angle)
                    y = center.y() + radius * math.sin(angle)
                    circle_points.append(QPointF(x, y))
                    
                self.temp_object.points = circle_points
                self.temp_object.update_polygon()
                
        self.temp_object.update()
        
    def finish_drawing(self):
        if not self.drawing or not self.temp_object:
            return
            
        current_layer = self.get_current_layer()
        if not current_layer:
            return
            
        # 创建永久对象
        if self.current_tool == ToolType.LINE:
            obj = LineObject(f"line_{id(self.temp_object)}", current_layer.layer_id, self.temp_object.points)
        elif self.current_tool == ToolType.POLYGON:
            obj = PolygonObject(f"poly_{id(self.temp_object)}", current_layer.layer_id, self.temp_object.points)
        elif self.current_tool == ToolType.RECTANGLE:
            obj = PolygonObject(f"rect_{id(self.temp_object)}", current_layer.layer_id, self.temp_object.points)
        elif self.current_tool == ToolType.CIRCLE:
            obj = PolygonObject(f"circle_{id(self.temp_object)}", current_layer.layer_id, self.temp_object.points)
        else:
            return
            
        # 应用样式
        obj.set_style(self.temp_object.pen, self.temp_object.brush)
        
        # 添加到图层和场景
        current_layer.add_object(obj)
        self.scene.addItem(obj)
        
        # 清理临时对象
        self.scene.removeItem(self.temp_object)
        self.temp_object = None
        self.drawing = False
        self.current_points = []
        
    def cancel_drawing(self):
        if self.temp_object:
            self.scene.removeItem(self.temp_object)
            self.temp_object = None
        self.drawing = False
        self.current_points = []
        
    def add_point(self, point: QPointF):
        current_layer = self.get_current_layer()
        if current_layer:
            obj = PointObject(f"point_{id(self)}", current_layer.layer_id, point)
            current_layer.add_object(obj)
            self.scene.addItem(obj)
            
    def add_text(self, point: QPointF):
        text, ok = QInputDialog.getText(self, "添加文本", "请输入文本:")
        if ok and text:
            current_layer = self.get_current_layer()
            if current_layer:
                obj = TextObject(f"text_{id(self)}", current_layer.layer_id, point, text)
                current_layer.add_object(obj)
                self.scene.addItem(obj)
                
    def start_measure(self, point: QPointF):
        self.measure_points.append(point)
        
        # 绘制测量点
        measure_point = PointObject(f"measure_{len(self.measure_points)}", "measure", point)
        measure_point.set_style(QPen(Qt.red, 2), QBrush(Qt.red))
        measure_point.setZValue(1000)
        self.scene.addItem(measure_point)
        
        # 如果至少有两个点，绘制测量线和距离
        if len(self.measure_points) >= 2:
            start = self.measure_points[-2]
            end = self.measure_points[-1]
            
            # 绘制测量线
            measure_line = LineObject(f"measure_line_{len(self.measure_points)}", "measure", [start, end])
            measure_line.set_style(QPen(Qt.red, 1, Qt.DashLine), QBrush(Qt.transparent))
            measure_line.setZValue(1000)
            self.scene.addItem(measure_line)
            
            # 计算距离
            distance = QLineF(start, end).length()
            
            # 添加距离文本
            mid_point = QPointF((start.x() + end.x()) / 2, (start.y() + end.y()) / 2)
            text = TextObject(f"measure_text_{len(self.measure_points)}", "measure", mid_point, f"{distance:.2f}")
            text.set_style(QPen(Qt.red, 1), QBrush(Qt.transparent))
            text.setZValue(1000)
            self.scene.addItem(text)
            self.measure_texts.append(text)
            
    def clear_measure(self):
        # 清除所有测量对象
        for point in self.measure_points:
            # 查找并删除测量点
            for item in self.scene.items():
                if isinstance(item, PointObject) and item.obj_id.startswith("measure"):
                    self.scene.removeItem(item)
                    
        for text in self.measure_texts:
            self.scene.removeItem(text)
            
        # 查找并删除测量线
        for item in self.scene.items():
            if isinstance(item, LineObject) and item.obj_id.startswith("measure"):
                self.scene.removeItem(item)
                
        self.measure_points = []
        self.measure_texts = []
        
    def drawBackground(self, painter, rect):
        # 绘制网格
        if self.grid_visible:
            painter.setPen(QPen(QColor(200, 200, 200, 100), 0))
            
            left = int(rect.left()) - (int(rect.left()) % self.grid_size)
            top = int(rect.top()) - (int(rect.top()) % self.grid_size)
            right = int(rect.right())
            bottom = int(rect.bottom())
            
            # 垂直线
            x = left
            while x < right:
                painter.drawLine(x, top, x, bottom)
                x += self.grid_size
                
            # 水平线
            y = top
            while y < bottom:
                painter.drawLine(left, y, right, y)
                y += self.grid_size

# 主窗口类
class MapSystemMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("高级建图系统")
        self.setGeometry(100, 100, 1200, 800)
        
        # 创建中心部件
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # 创建布局
        self.main_layout = QHBoxLayout(self.central_widget)
        
        # 创建地图视图
        self.map_view = MapView()
        self.main_layout.addWidget(self.map_view)
        
        # 初始化UI
        self.init_ui()
        
        # 初始化图层
        self.init_layers()
        
        # 连接信号
        self.connect_signals()
        
    def init_ui(self):
        # 创建工具栏
        self.create_toolbar()
        
        # 创建图层面板
        self.create_layer_panel()
        
        # 创建属性面板
        self.create_property_panel()
        
        # 创建状态栏
        self.status_bar = self.statusBar()
        self.status_label = QLabel("就绪")
        self.status_bar.addWidget(self.status_label)
        
    def create_toolbar(self):
        # 主工具栏
        self.toolbar = QToolBar("主工具栏")
        self.toolbar.setIconSize(QSize(24, 24))
        self.addToolBar(Qt.TopToolBarArea, self.toolbar)
        
        # 工具按钮
        self.tool_actions = {}
        tools = [
            (ToolType.SELECT, "选择", "icons/select.png"),
            (ToolType.PAN, "平移", "icons/pan.png"),
            (ToolType.ZOOM, "缩放", "icons/zoom.png"),
            (ToolType.POINT, "点", "icons/point.png"),
            (ToolType.LINE, "线", "icons/line.png"),
            (ToolType.RECTANGLE, "矩形", "icons/rectangle.png"),
            (ToolType.CIRCLE, "圆", "icons/circle.png"),
            (ToolType.POLYGON, "多边形", "icons/polygon.png"),
            (ToolType.TEXT, "文本", "icons/text.png"),
            (ToolType.MEASURE, "测量", "icons/measure.png"),
        ]
        
        tool_group = QActionGroup(self)
        for tool_type, tool_name, icon_path in tools:
            action = QAction(QIcon(icon_path), tool_name, self)
            action.setCheckable(True)
            action.setData(tool_type)
            tool_group.addAction(action)
            self.toolbar.addAction(action)
            self.tool_actions[tool_type] = action
            
        # 默认选择工具
        self.tool_actions[ToolType.SELECT].setChecked(True)
        
        # 分隔符
        self.toolbar.addSeparator()
        
        # 文件操作
        self.toolbar.addAction(QIcon("icons/new.png"), "新建", self.new_map)
        self.toolbar.addAction(QIcon("icons/open.png"), "打开", self.open_map)
        self.toolbar.addAction(QIcon("icons/save.png"), "保存", self.save_map)
        
        # 编辑操作
        self.toolbar.addSeparator()
        self.toolbar.addAction(QIcon("icons/undo.png"), "撤销", self.undo)
        self.toolbar.addAction(QIcon("icons/redo.png"), "重做", self.redo)
        self.toolbar.addAction(QIcon("icons/delete.png"), "删除", self.delete_selected)
        
        # 视图操作
        self.toolbar.addSeparator()
        self.toolbar.addAction(QIcon("icons/zoom_in.png"), "放大", self.zoom_in)
        self.toolbar.addAction(QIcon("icons/zoom_out.png"), "缩小", self.zoom_out)
        self.toolbar.addAction(QIcon("icons/zoom_extent.png"), "全图", self.zoom_extent)
        self.toolbar.addAction(QIcon("icons/grid.png"), "网格", self.toggle_grid)
        
    def create_layer_panel(self):
        # 图层面板
        self.layer_dock = QDockWidget("图层管理", self)
        self.layer_dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        
        layer_widget = QWidget()
        layer_layout = QVBoxLayout(layer_widget)
        
        # 图层列表
        self.layer_list = QListWidget()
        layer_layout.addWidget(self.layer_list)
        
        # 图层操作按钮
        layer_buttons_layout = QHBoxLayout()
        self.add_layer_btn = QToolButton()
        self.add_layer_btn.setText("添加")
        self.add_layer_btn.clicked.connect(self.add_layer)
        
        self.remove_layer_btn = QToolButton()
        self.remove_layer_btn.setText("删除")
        self.remove_layer_btn.clicked.connect(self.remove_layer)
        
        self.layer_up_btn = QToolButton()
        self.layer_up_btn.setText("上移")
        self.layer_up_btn.clicked.connect(self.move_layer_up)
        
        self.layer_down_btn = QToolButton()
        self.layer_down_btn.setText("下移")
        self.layer_down_btn.clicked.connect(self.move_layer_down)
        
        layer_buttons_layout.addWidget(self.add_layer_btn)
        layer_buttons_layout.addWidget(self.remove_layer_btn)
        layer_buttons_layout.addWidget(self.layer_up_btn)
        layer_buttons_layout.addWidget(self.layer_down_btn)
        
        layer_layout.addLayout(layer_buttons_layout)
        
        self.layer_dock.setWidget(layer_widget)
        self.addDockWidget(Qt.RightDockWidgetArea, self.layer_dock)
        
    def create_property_panel(self):
        # 属性面板
        self.property_dock = QDockWidget("属性设置", self)
        self.property_dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        
        property_widget = QWidget()
        property_layout = QVBoxLayout(property_widget)
        
        # 线条属性
        property_layout.addWidget(QLabel("线条设置"))
        
        pen_width_layout = QHBoxLayout()
        pen_width_layout.addWidget(QLabel("宽度:"))
        self.pen_width_spin = QSpinBox()
        self.pen_width_spin.setRange(1, 10)
        self.pen_width_spin.setValue(2)
        self.pen_width_spin.valueChanged.connect(self.update_pen_style)
        pen_width_layout.addWidget(self.pen_width_spin)
        property_layout.addLayout(pen_width_layout)
        
        pen_color_layout = QHBoxLayout()
        pen_color_layout.addWidget(QLabel("颜色:"))
        self.pen_color_btn = QToolButton()
        self.pen_color_btn.setText("选择")
        self.pen_color_btn.clicked.connect(self.choose_pen_color)
        pen_color_layout.addWidget(self.pen_color_btn)
        property_layout.addLayout(pen_color_layout)
        
        # 填充属性
        property_layout.addWidget(QLabel("填充设置"))
        
        fill_color_layout = QHBoxLayout()
        fill_color_layout.addWidget(QLabel("颜色:"))
        self.fill_color_btn = QToolButton()
        self.fill_color_btn.setText("选择")
        self.fill_color_btn.clicked.connect(self.choose_fill_color)
        fill_color_layout.addWidget(self.fill_color_btn)
        property_layout.addLayout(fill_color_layout)
        
        # 其他设置
        property_layout.addWidget(QLabel("其他设置"))
        
        self.snap_to_grid_check = QCheckBox("吸附到网格")
        self.snap_to_grid_check.stateChanged.connect(self.toggle_snap_to_grid)
        property_layout.addWidget(self.snap_to_grid_check)
        
        property_layout.addStretch()
        
        self.property_dock.setWidget(property_widget)
        self.addDockWidget(Qt.RightDockWidgetArea, self.property_dock)
        
    def init_layers(self):
        # 创建默认图层
        base_layer = MapLayer("base", "基础图层", LayerType.BASE)
        self.map_view.add_layer(base_layer)
        self.map_view.set_current_layer("base")
        
        # 更新图层列表
        self.update_layer_list()
        
    def connect_signals(self):
        # 工具选择
        for tool_type, action in self.tool_actions.items():
            action.triggered.connect(lambda checked, tool=tool_type: self.map_view.set_tool(tool))
            
        # 地图视图信号
        self.map_view.mouseMoved.connect(self.update_status_bar)
        self.map_view.toolChanged.connect(self.on_tool_changed)
        
    def update_status_bar(self, point: QPointF):
        self.status_label.setText(f"坐标: ({point.x():.2f}, {point.y():.2f})")
        
    def on_tool_changed(self, tool: ToolType):
        # 更新工具栏按钮状态
        for tool_type, action in self.tool_actions.items():
            action.setChecked(tool_type == tool)
            
    def new_map(self):
        reply = QMessageBox.question(self, "新建地图", "是否保存当前地图?",
                                   QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
        
        if reply == QMessageBox.Cancel:
            return
        elif reply == QMessageBox.Yes:
            self.save_map()
            
        # 清空地图
        self.map_view.scene.clear()
        self.map_view.layers.clear()
        self.map_view.current_layer_id = None
        
        # 重新初始化图层
        self.init_layers()
        
    def open_map(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "打开地图文件", "", "地图文件 (*.map)")
        if file_path:
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    
                # 清空当前地图
                self.map_view.scene.clear()
                self.map_view.layers.clear()
                
                # 加载图层和数据
                for layer_data in data.get('layers', []):
                    layer = MapLayer(layer_data['id'], layer_data['name'], 
                                   LayerType(layer_data['type']), layer_data['visible'])
                    self.map_view.add_layer(layer)
                    
                    # 加载对象
                    for obj_data in layer_data.get('objects', []):
                        obj_type = obj_data['type']
                        if obj_type == 'point':
                            point = QPointF(obj_data['x'], obj_data['y'])
                            obj = PointObject(obj_data['id'], layer.layer_id, point)
                        elif obj_type == 'line':
                            points = [QPointF(p['x'], p['y']) for p in obj_data['points']]
                            obj = LineObject(obj_data['id'], layer.layer_id, points)
                        elif obj_type == 'polygon':
                            points = [QPointF(p['x'], p['y']) for p in obj_data['points']]
                            obj = PolygonObject(obj_data['id'], layer.layer_id, points)
                        elif obj_type == 'text':
                            point = QPointF(obj_data['x'], obj_data['y'])
                            obj = TextObject(obj_data['id'], layer.layer_id, point, obj_data['text'])
                            
                        # 设置样式
                        pen = QPen(QColor(obj_data['pen_color']), obj_data['pen_width'])
                        brush = QBrush(QColor(obj_data['brush_color']))
                        obj.set_style(pen, brush)
                        
                        layer.add_object(obj)
                        self.map_view.scene.addItem(obj)
                        
                # 更新图层列表
                self.update_layer_list()
                
                QMessageBox.information(self, "成功", "地图文件加载成功!")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"加载地图文件失败: {str(e)}")
                
    def save_map(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "保存地图文件", "", "地图文件 (*.map)")
        if file_path:
            try:
                data = {'layers': []}
                
                for layer in self.map_view.layers.values():
                    layer_data = {
                        'id': layer.layer_id,
                        'name': layer.name,
                        'type': layer.layer_type.value,
                        'visible': layer.visible,
                        'objects': []
                    }
                    
                    for obj in layer.objects.values():
                        obj_data = {
                            'id': obj.obj_id,
                            'type': '',
                            'pen_color': obj.pen.color().name(),
                            'pen_width': obj.pen.width(),
                            'brush_color': obj.brush.color().name()
                        }
                        
                        if isinstance(obj, PointObject):
                            obj_data['type'] = 'point'
                            obj_data['x'] = obj.point.x()
                            obj_data['y'] = obj.point.y()
                        elif isinstance(obj, LineObject):
                            obj_data['type'] = 'line'
                            obj_data['points'] = [{'x': p.x(), 'y': p.y()} for p in obj.points]
                        elif isinstance(obj, PolygonObject):
                            obj_data['type'] = 'polygon'
                            obj_data['points'] = [{'x': p.x(), 'y': p.y()} for p in obj.points]
                        elif isinstance(obj, TextObject):
                            obj_data['type'] = 'text'
                            obj_data['x'] = obj.point.x()
                            obj_data['y'] = obj.point.y()
                            obj_data['text'] = obj.text
                            
                        layer_data['objects'].append(obj_data)
                        
                    data['layers'].append(layer_data)
                    
                with open(file_path, 'w') as f:
                    json.dump(data, f, indent=2)
                    
                QMessageBox.information(self, "成功", "地图文件保存成功!")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"保存地图文件失败: {str(e)}")
                
    def undo(self):
        # 实现撤销功能
        pass
        
    def redo(self):
        # 实现重做功能
        pass
        
    def delete_selected(self):
        # 删除选中的对象
        selected_items = self.map_view.scene.selectedItems()
        for item in selected_items:
            if isinstance(item, MapObject):
                # 从图层中移除
                layer = self.map_view.layers.get(item.layer_id)
                if layer:
                    layer.remove_object(item.obj_id)
                # 从场景中移除
                self.map_view.scene.removeItem(item)
                
    def zoom_in(self):
        self.map_view.scale(1.2, 1.2)
        
    def zoom_out(self):
        self.map_view.scale(1/1.2, 1/1.2)
        
    def zoom_extent(self):
        self.map_view.fitInView(self.map_view.scene.itemsBoundingRect(), Qt.KeepAspectRatio)
        
    def toggle_grid(self):
        self.map_view.grid_visible = not self.map_view.grid_visible
        self.map_view.update()
        
    def add_layer(self):
        name, ok = QInputDialog.getText(self, "添加图层", "请输入图层名称:")
        if ok and name:
            layer_id = f"layer_{len(self.map_view.layers)}"
            layer = MapLayer(layer_id, name, LayerType.OVERLAY)
            self.map_view.add_layer(layer)
            self.update_layer_list()
            
    def remove_layer(self):
        current_row = self.layer_list.currentRow()
        if current_row >= 0:
            item = self.layer_list.item(current_row)
            layer_id = item.data(Qt.UserRole)
            self.map_view.remove_layer(layer_id)
            self.update_layer_list()
            
    def move_layer_up(self):
        # 实现图层上移
        pass
        
    def move_layer_down(self):
        # 实现图层下移
        pass
        
    def update_layer_list(self):
        self.layer_list.clear()
        for layer in self.map_view.layers.values():
            item = QListWidgetItem(layer.name)
            item.setData(Qt.UserRole, layer.layer_id)
            item.setCheckState(Qt.Checked if layer.visible else Qt.Unchecked)
            self.layer_list.addItem(item)
            
    def update_pen_style(self):
        # 更新选中对象的线条样式
        selected_items = self.map_view.scene.selectedItems()
        for item in selected_items:
            if isinstance(item, MapObject):
                pen = item.pen
                pen.setWidth(self.pen_width_spin.value())
                item.set_style(pen, item.brush)
                
    def choose_pen_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            selected_items = self.map_view.scene.selectedItems()
            for item in selected_items:
                if isinstance(item, MapObject):
                    pen = item.pen
                    pen.setColor(color)
                    item.set_style(pen, item.brush)
                    
    def choose_fill_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            selected_items = self.map_view.scene.selectedItems()
            for item in selected_items:
                if isinstance(item, MapObject):
                    brush = QBrush(color)
                    item.set_style(item.pen, brush)
                    
    def toggle_snap_to_grid(self, state):
        self.map_view.snap_to_grid = (state == Qt.Checked)

# 应用程序入口
if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 设置应用程序样式
    app.setStyle("Fusion")
    
    # 创建主窗口
    window = MapSystemMainWindow()
    window.show()
    
    sys.exit(app.exec_())