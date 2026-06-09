import sys
import json
import numpy as np
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtPrintSupport import QPrintDialog, QPrinter
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from scipy.sparse import lil_matrix
from scipy.sparse.linalg import spsolve
import networkx as nx

# 电路元件基类
class CircuitComponent:
    def __init__(self, name, value, x, y):
        self.name = name
        self.value = value
        self.x = x
        self.y = y
        self.connections = []
        self.rotation = 0  # 0, 90, 180, 270 degrees
    
    def draw(self, painter):
        pass
    
    def get_connection_points(self):
        return []
    
    def rotate(self):
        self.rotation = (self.rotation + 90) % 360
    
    def get_bounding_rect(self):
        points = self.get_connection_points()
        if points:
            min_x = min(p[0] for p in points)
            max_x = max(p[0] for p in points)
            min_y = min(p[1] for p in points)
            max_y = max(p[1] for p in points)
            return QRect(min_x - 10, min_y - 10, max_x - min_x + 20, max_y - min_y + 20)
        return QRect(self.x - 10, self.y - 10, 20, 20)
    
    def to_dict(self):
        return {
            'type': self.__class__.__name__,
            'name': self.name,
            'value': self.value,
            'x': self.x,
            'y': self.y,
            'rotation': self.rotation
        }
    
    @classmethod
    def from_dict(cls, data):
        comp_type = data['type']
        if comp_type == 'Resistor':
            component = Resistor(data['name'], data['value'], data['x'], data['y'])
        elif comp_type == 'Capacitor':
            component = Capacitor(data['name'], data['value'], data['x'], data['y'])
        elif comp_type == 'Inductor':
            component = Inductor(data['name'], data['value'], data['x'], data['y'])
        elif comp_type == 'VoltageSource':
            component = VoltageSource(data['name'], data['value'], data['x'], data['y'])
        elif comp_type == 'CurrentSource':
            component = CurrentSource(data['name'], data['value'], data['x'], data['y'])
        elif comp_type == 'Diode':
            component = Diode(data['name'], data['value'], data['x'], data['y'])
        elif comp_type == 'Ground':
            component = Ground(data['name'], data['value'], data['x'], data['y'])
        
        component.rotation = data.get('rotation', 0)
        return component

# 具体电路元件实现
class Resistor(CircuitComponent):
    def __init__(self, name, value, x, y):
        super().__init__(name, value, x, y)
        self.width = 60
        self.height = 20
    
    def draw(self, painter):
        painter.save()
        painter.translate(self.x + 30, self.y)
        painter.rotate(self.rotation)
        
        painter.setPen(QPen(Qt.black, 2))
        painter.drawLine(-30, 0, -15, 0)
        painter.drawRect(-15, -10, 30, 20)
        painter.drawLine(15, 0, 30, 0)
        
        # 绘制标签
        painter.rotate(-self.rotation)
        painter.translate(-self.x - 30, -self.y)
        painter.drawText(QRect(self.x, self.y - 30, 60, 20), Qt.AlignCenter, f"{self.name}\n{self.value}Ω")
        painter.restore()
    
    def get_connection_points(self):
        if self.rotation == 0 or self.rotation == 180:
            return [(self.x, self.y), (self.x + 60, self.y)]
        else:
            return [(self.x, self.y), (self.x, self.y + 60)]

class Capacitor(CircuitComponent):
    def __init__(self, name, value, x, y):
        super().__init__(name, value, x, y)
        self.width = 40
        self.height = 20
    
    def draw(self, painter):
        painter.save()
        painter.translate(self.x + 20, self.y)
        painter.rotate(self.rotation)
        
        painter.setPen(QPen(Qt.black, 2))
        painter.drawLine(-20, 0, -10, 0)
        painter.drawLine(-10, -10, -10, 10)
        painter.drawLine(10, -10, 10, 10)
        painter.drawLine(10, 0, 20, 0)
        
        # 绘制标签
        painter.rotate(-self.rotation)
        painter.translate(-self.x - 20, -self.y)
        painter.drawText(QRect(self.x, self.y - 30, 40, 20), Qt.AlignCenter, f"{self.name}\n{self.value}F")
        painter.restore()
    
    def get_connection_points(self):
        if self.rotation == 0 or self.rotation == 180:
            return [(self.x, self.y), (self.x + 40, self.y)]
        else:
            return [(self.x, self.y), (self.x, self.y + 40)]

class Inductor(CircuitComponent):
    def __init__(self, name, value, x, y):
        super().__init__(name, value, x, y)
        self.width = 60
        self.height = 20
    
    def draw(self, painter):
        painter.save()
        painter.translate(self.x + 30, self.y)
        painter.rotate(self.rotation)
        
        painter.setPen(QPen(Qt.black, 2))
        painter.drawLine(-30, 0, -25, 0)
        
        # 绘制电感符号（几个半圆）
        for i in range(3):
            painter.drawArc(-20 + i*10, -5, 10, 10, 0, 180 * 16)
            painter.drawArc(-15 + i*10, -5, 10, 10, 0, -180 * 16)
        
        painter.drawLine(25, 0, 30, 0)
        
        # 绘制标签
        painter.rotate(-self.rotation)
        painter.translate(-self.x - 30, -self.y)
        painter.drawText(QRect(self.x, self.y - 30, 60, 20), Qt.AlignCenter, f"{self.name}\n{self.value}H")
        painter.restore()
    
    def get_connection_points(self):
        if self.rotation == 0 or self.rotation == 180:
            return [(self.x, self.y), (self.x + 60, self.y)]
        else:
            return [(self.x, self.y), (self.x, self.y + 60)]

class VoltageSource(CircuitComponent):
    def __init__(self, name, value, x, y):
        super().__init__(name, value, x, y)
        self.width = 40
        self.height = 40
    
    def draw(self, painter):
        painter.save()
        painter.translate(self.x + 20, self.y)
        painter.rotate(self.rotation)
        
        painter.setPen(QPen(Qt.black, 2))
        painter.drawLine(-20, 0, -10, 0)
        painter.drawEllipse(-10, -10, 20, 20)
        painter.drawText(-5, -5, "+")
        painter.drawText(-5, 15, "-")
        painter.drawLine(10, 0, 20, 0)
        
        # 绘制标签
        painter.rotate(-self.rotation)
        painter.translate(-self.x - 20, -self.y)
        painter.drawText(QRect(self.x, self.y - 40, 40, 20), Qt.AlignCenter, f"{self.name}\n{self.value}V")
        painter.restore()
    
    def get_connection_points(self):
        if self.rotation == 0 or self.rotation == 180:
            return [(self.x, self.y), (self.x + 40, self.y)]
        else:
            return [(self.x, self.y), (self.x, self.y + 40)]

class CurrentSource(CircuitComponent):
    def __init__(self, name, value, x, y):
        super().__init__(name, value, x, y)
        self.width = 40
        self.height = 40
    
    def draw(self, painter):
        painter.save()
        painter.translate(self.x + 20, self.y)
        painter.rotate(self.rotation)
        
        painter.setPen(QPen(Qt.black, 2))
        painter.drawLine(-20, 0, -10, 0)
        painter.drawEllipse(-10, -10, 20, 20)
        
        # 绘制箭头表示电流方向
        painter.drawLine(0, -5, 0, 5)
        painter.drawLine(0, -5, -5, 0)
        painter.drawLine(0, -5, 5, 0)
        
        painter.drawLine(10, 0, 20, 0)
        
        # 绘制标签
        painter.rotate(-self.rotation)
        painter.translate(-self.x - 20, -self.y)
        painter.drawText(QRect(self.x, self.y - 40, 40, 20), Qt.AlignCenter, f"{self.name}\n{self.value}A")
        painter.restore()
    
    def get_connection_points(self):
        if self.rotation == 0 or self.rotation == 180:
            return [(self.x, self.y), (self.x + 40, self.y)]
        else:
            return [(self.x, self.y), (self.x, self.y + 40)]

class Diode(CircuitComponent):
    def __init__(self, name, value, x, y):
        super().__init__(name, value, x, y)
        self.width = 40
        self.height = 20
    
    def draw(self, painter):
        painter.save()
        painter.translate(self.x + 20, self.y)
        painter.rotate(self.rotation)
        
        painter.setPen(QPen(Qt.black, 2))
        painter.drawLine(-20, 0, -10, 0)
        
        # 绘制二极管符号
        path = QPainterPath()
        path.moveTo(-10, -10)
        path.lineTo(10, 0)
        path.lineTo(-10, 10)
        path.closeSubpath()
        painter.drawPath(path)
        
        painter.drawLine(-10, -10, -10, 10)  # 垂直线
        painter.drawLine(10, 0, 20, 0)
        
        # 绘制标签
        painter.rotate(-self.rotation)
        painter.translate(-self.x - 20, -self.y)
        painter.drawText(QRect(self.x, self.y - 30, 40, 20), Qt.AlignCenter, f"{self.name}\nDiode")
        painter.restore()
    
    def get_connection_points(self):
        if self.rotation == 0 or self.rotation == 180:
            return [(self.x, self.y), (self.x + 40, self.y)]
        else:
            return [(self.x, self.y), (self.x, self.y + 40)]

class Ground(CircuitComponent):
    def __init__(self, name, value, x, y):
        super().__init__(name, value, x, y)
        self.width = 30
        self.height = 30
    
    def draw(self, painter):
        painter.save()
        painter.translate(self.x + 15, self.y)
        painter.rotate(self.rotation)
        
        painter.setPen(QPen(Qt.black, 2))
        painter.drawLine(0, 0, 0, 10)
        painter.drawLine(-10, 10, 10, 10)
        painter.drawLine(-7, 15, 7, 15)
        painter.drawLine(-4, 20, 4, 20)
        
        # 绘制标签
        painter.rotate(-self.rotation)
        painter.translate(-self.x - 15, -self.y)
        painter.drawText(QRect(self.x, self.y - 20, 30, 20), Qt.AlignCenter, f"{self.name}\nGND")
        painter.restore()
    
    def get_connection_points(self):
        return [(self.x + 15, self.y)]

# 电路画布类
class CircuitCanvas(QWidget):
    canvasUpdated = pyqtSignal()
    def __init__(self):
        super().__init__()
        self.components = []
        self.wires = []
        self.selected_component = None
        self.dragging = False
        self.drag_offset = QPoint(0, 0)
        self.wire_start = None
        self.wire_end = None
        self.drawing_wire = False
        self.wire_start_component = None
        self.wire_start_point_idx = 0
        self.setMinimumSize(800, 600)
        self.setMouseTracking(True)
        self.grid_size = 20
        self.show_grid = True
        self.zoom_factor = 1.0
    
    def add_component(self, component):
        self.components.append(component)
        self.update()
        self.canvasUpdated.emit()
    
    def remove_component(self, component):
        if component in self.components:
            self.components.remove(component)
            
            # 移除与该元件相关的导线
            self.wires = [wire for wire in self.wires 
                         if not (wire[0] == component or wire[1] == component)]
            
            if self.selected_component == component:
                self.selected_component = None
            
            self.update()
            self.canvasUpdated.emit() 
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 应用缩放
        painter.scale(self.zoom_factor, self.zoom_factor)
        
        # 绘制网格
        if self.show_grid:
            painter.setPen(QPen(QColor(220, 220, 220), 1))
            for x in range(0, int(self.width()/self.zoom_factor), self.grid_size):
                painter.drawLine(x, 0, x, int(self.height()/self.zoom_factor))
            for y in range(0, int(self.height()/self.zoom_factor), self.grid_size):
                painter.drawLine(0, y, int(self.width()/self.zoom_factor), y)
        
        # 绘制导线
        painter.setPen(QPen(Qt.black, 3))
        for wire in self.wires:
            comp1, point1_idx, comp2, point2_idx = wire
            points1 = comp1.get_connection_points()
            points2 = comp2.get_connection_points()
            if points1 and points2:
                p1 = points1[point1_idx]
                p2 = points2[point2_idx]
                painter.drawLine(p1[0], p1[1], p2[0], p2[1])
        
        # 绘制正在绘制的导线
        if self.drawing_wire and self.wire_start and self.wire_end:
            painter.setPen(QPen(Qt.blue, 2, Qt.DashLine))
            painter.drawLine(self.wire_start, self.wire_end)
        
        # 绘制元件
        for component in self.components:
            component.draw(painter)
        
        # 绘制选中框
        if self.selected_component:
            painter.setPen(QPen(Qt.blue, 2, Qt.DashLine))
            rect = self.selected_component.get_bounding_rect()
            painter.drawRect(rect)
    
    def mousePressEvent(self, event):
        pos = event.pos() / self.zoom_factor
        
        # 检查是否点击了元件
        for component in reversed(self.components):  # 从最上面的元件开始检查
            rect = component.get_bounding_rect()
            if rect.contains(pos.toPoint()):
                self.selected_component = component
                self.dragging = True
                self.drag_offset = QPoint(pos.x() - component.x, pos.y() - component.y)
                
                # 如果是右键点击，开始绘制导线
                if event.button() == Qt.RightButton:
                    self.drawing_wire = True
                    points = component.get_connection_points()
                    # 找到最近的连接点
                    min_dist = float('inf')
                    closest_point_idx = 0
                    for i, point in enumerate(points):
                        dist = (point[0] - pos.x())**2 + (point[1] - pos.y())**2
                        if dist < min_dist:
                            min_dist = dist
                            closest_point_idx = i
                    
                    self.wire_start = QPoint(points[closest_point_idx][0], points[closest_point_idx][1])
                    self.wire_end = pos
                    self.wire_start_component = component
                    self.wire_start_point_idx = closest_point_idx
                break
        else:
            self.selected_component = None
        
        self.update()
        self.componentSelected.emit(self.selected_component)
    
    def mouseMoveEvent(self, event):
        pos = event.pos() / self.zoom_factor
        
        if self.dragging and self.selected_component:
            # 对齐到网格
            self.selected_component.x = (pos.x() - self.drag_offset.x()) // self.grid_size * self.grid_size
            self.selected_component.y = (pos.y() - self.drag_offset.y()) // self.grid_size * self.grid_size
            self.update()
        
        if self.drawing_wire and self.wire_start:
            self.wire_end = pos
            self.update()
    
    def mouseReleaseEvent(self, event):
        if self.dragging:
            self.dragging = False
        
        if self.drawing_wire and self.wire_start and self.wire_end:
            pos = event.pos() / self.zoom_factor
            
            # 检查是否连接到另一个元件
            for component in self.components:
                if component != self.wire_start_component:
                    points = component.get_connection_points()
                    for i, point in enumerate(points):
                        if abs(point[0] - pos.x()) < 10 and abs(point[1] - pos.y()) < 10:
                            # 连接到元件
                            self.wires.append((self.wire_start_component, self.wire_start_point_idx, 
                                             component, i))
                            break
            
            self.drawing_wire = False
            self.wire_start = None
            self.wire_end = None
            self.wire_start_component = None
            self.update()
            self.canvasUpdated.emit()
            
    
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Delete and self.selected_component:
            self.remove_component(self.selected_component)
        elif event.key() == Qt.Key_R and self.selected_component:
            self.selected_component.rotate()
            self.update()
        elif event.key() == Qt.Key_Plus:
            self.zoom_in()
        elif event.key() == Qt.Key_Minus:
            self.zoom_out()
    
    def zoom_in(self):
        self.zoom_factor *= 1.1
        self.update()
    
    def zoom_out(self):
        self.zoom_factor /= 1.1
        self.update()
    
    def reset_zoom(self):
        self.zoom_factor = 1.0
        self.update()
    
    # 信号定义
    componentSelected = pyqtSignal(object)

# 元件库面板
class ComponentLibrary(QDockWidget):
    def __init__(self):
        super().__init__("元件库")
        self.widget = QWidget()
        self.layout = QGridLayout(self.widget)
        
        # 创建元件按钮
        self.resistor_btn = QPushButton("电阻")
        self.capacitor_btn = QPushButton("电容")
        self.inductor_btn = QPushButton("电感")
        self.voltage_btn = QPushButton("电压源")
        self.current_btn = QPushButton("电流源")
        self.diode_btn = QPushButton("二极管")
        self.ground_btn = QPushButton("接地")
        
        # 设置按钮图标（简化版，实际应用中可以使用真实图标）
        self.resistor_btn.setIcon(QApplication.style().standardIcon(QStyle.SP_FileIcon))
        self.capacitor_btn.setIcon(QApplication.style().standardIcon(QStyle.SP_FileIcon))
        self.inductor_btn.setIcon(QApplication.style().standardIcon(QStyle.SP_FileIcon))
        self.voltage_btn.setIcon(QApplication.style().standardIcon(QStyle.SP_FileIcon))
        self.current_btn.setIcon(QApplication.style().standardIcon(QStyle.SP_FileIcon))
        self.diode_btn.setIcon(QApplication.style().standardIcon(QStyle.SP_FileIcon))
        self.ground_btn.setIcon(QApplication.style().standardIcon(QStyle.SP_FileIcon))
        
        # 添加到布局
        self.layout.addWidget(self.resistor_btn, 0, 0)
        self.layout.addWidget(self.capacitor_btn, 0, 1)
        self.layout.addWidget(self.inductor_btn, 1, 0)
        self.layout.addWidget(self.voltage_btn, 1, 1)
        self.layout.addWidget(self.current_btn, 2, 0)
        self.layout.addWidget(self.diode_btn, 2, 1)
        self.layout.addWidget(self.ground_btn, 3, 0)
        
        self.setWidget(self.widget)

# 属性面板
class PropertiesPanel(QDockWidget):
    def __init__(self):
        super().__init__("属性")
        self.widget = QWidget()
        self.layout = QFormLayout(self.widget)
        
        self.name_edit = QLineEdit()
        self.value_edit = QLineEdit()
        self.x_edit = QLineEdit()
        self.y_edit = QLineEdit()
        self.rotation_edit = QComboBox()
        self.rotation_edit.addItems(["0°", "90°", "180°", "270°"])
        
        self.layout.addRow("名称:", self.name_edit)
        self.layout.addRow("值:", self.value_edit)
        self.layout.addRow("X坐标:", self.x_edit)
        self.layout.addRow("Y坐标:", self.y_edit)
        self.layout.addRow("旋转:", self.rotation_edit)
        
        self.apply_btn = QPushButton("应用")
        self.layout.addRow(self.apply_btn)
        
        self.setWidget(self.widget)
        
        self.current_component = None
    
    def set_component(self, component):
        self.current_component = component
        if component:
            self.name_edit.setText(component.name)
            self.value_edit.setText(str(component.value))
            self.x_edit.setText(str(component.x))
            self.y_edit.setText(str(component.y))
            self.rotation_edit.setCurrentIndex(component.rotation // 90)
        else:
            self.name_edit.clear()
            self.value_edit.clear()
            self.x_edit.clear()
            self.y_edit.clear()
            self.rotation_edit.setCurrentIndex(0)
    
    def apply_changes(self):
        if self.current_component:
            self.current_component.name = self.name_edit.text()
            self.current_component.value = self.value_edit.text()
            self.current_component.x = int(self.x_edit.text())
            self.current_component.y = int(self.y_edit.text())
            self.current_component.rotation = self.rotation_edit.currentIndex() * 90

# 仿真结果图表
class SimulationPlot(QDockWidget):
    def __init__(self):
        super().__init__("仿真结果")
        self.widget = QWidget()
        self.layout = QVBoxLayout(self.widget)
        
        self.figure = plt.figure()
        self.canvas = FigureCanvas(self.figure)
        self.layout.addWidget(self.canvas)
        
        self.setWidget(self.widget)
    
    def plot_dc_sweep(self, voltages, currents):
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        ax.plot(voltages, currents)
        ax.set_xlabel('电压 (V)')
        ax.set_ylabel('电流 (A)')
        ax.set_title('直流扫描分析')
        ax.grid(True)
        self.canvas.draw()
    
    def plot_ac_analysis(self, frequencies, magnitudes, phases):
        self.figure.clear()
        
        ax1 = self.figure.add_subplot(211)
        ax1.semilogx(frequencies, magnitudes)
        ax1.set_ylabel('幅度 (dB)')
        ax1.set_title('交流分析 - 幅频特性')
        ax1.grid(True)
        
        ax2 = self.figure.add_subplot(212)
        ax2.semilogx(frequencies, phases)
        ax2.set_xlabel('频率 (Hz)')
        ax2.set_ylabel('相位 (度)')
        ax2.set_title('交流分析 - 相频特性')
        ax2.grid(True)
        
        self.figure.tight_layout()
        self.canvas.draw()
    
    def plot_transient(self, time, voltages):
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        ax.plot(time, voltages)
        ax.set_xlabel('时间 (s)')
        ax.set_ylabel('电压 (V)')
        ax.set_title('瞬态分析')
        ax.grid(True)
        self.canvas.draw()

# 改进的仿真引擎
class CircuitSimulator:
    def __init__(self):
        self.components = []
        self.connections = []
        self.nodes = {}
        self.node_count = 0
    
    def add_component(self, component):
        self.components.append(component)
    
    def add_connection(self, connection):
        self.connections.append(connection)
    
    def build_circuit_graph(self):
        # 创建电路图
        G = nx.Graph()
        
        # 添加元件作为节点
        for comp in self.components:
            G.add_node(comp.name, type=type(comp).__name__, value=comp.value)
        
        # 添加连接作为边
        for conn in self.connections:
            comp1, point1_idx, comp2, point2_idx = conn
            G.add_edge(comp1.name, comp2.name)
        
        return G
    
    def assign_nodes(self):
        # 为电路分配节点编号
        self.nodes = {}
        self.node_count = 0
        
        # 接地节点为0
        self.nodes['GND'] = 0
        self.node_count = 1
        
        # 为其他节点分配编号
        for comp in self.components:
            if not isinstance(comp, Ground):
                if comp.name not in self.nodes:
                    self.nodes[comp.name] = self.node_count
                    self.node_count += 1
    
    def analyze_dc(self):
        # 使用改进的节点分析法进行直流分析
        self.assign_nodes()
        n = self.node_count
        
        # 创建节点电压方程矩阵
        G = lil_matrix((n, n))  # 电导矩阵
        I = np.zeros(n)         # 电流源向量
        
        # 处理电阻
        for comp in self.components:
            if isinstance(comp, Resistor):
                try:
                    value = float(comp.value)
                    if value == 0:
                        continue  # 避免除以零
                    conductance = 1.0 / value
                    
                    # 假设电阻连接在节点1和节点2之间
                    # 在实际应用中，需要根据实际连接确定节点
                    node1 = self.nodes.get(comp.name, 0)
                    node2 = 0  # 假设另一端接地
                    
                    if node1 != 0:
                        G[node1, node1] += conductance
                        if node2 != 0:
                            G[node1, node2] -= conductance
                            G[node2, node1] -= conductance
                            G[node2, node2] += conductance
                except ValueError:
                    pass
        
        # 处理电压源
        for comp in self.components:
            if isinstance(comp, VoltageSource):
                try:
                    value = float(comp.value)
                    
                    # 增加一个方程来处理电压源
                    # 在实际应用中，需要扩展矩阵大小
                    pass
                except ValueError:
                    pass
        
        # 求解节点电压
        try:
            # 转换为压缩稀疏行格式以提高求解效率
            G_csr = G.tocsr()
            
            # 移除接地节点对应的行和列
            if n > 1:
                G_reduced = G_csr[1:, 1:]
                I_reduced = I[1:]
                
                # 求解节点电压
                V_reduced = spsolve(G_reduced, I_reduced)
                
                # 构建完整的节点电压向量（接地节点电压为0）
                V = np.zeros(n)
                V[1:] = V_reduced
            else:
                V = np.zeros(n)
            
            # 计算支路电流
            results = {}
            for comp in self.components:
                if isinstance(comp, Resistor):
                    try:
                        value = float(comp.value)
                        node1 = self.nodes.get(comp.name, 0)
                        voltage = V[node1]  # 假设另一端接地
                        current = voltage / value if value != 0 else 0
                        results[comp.name] = {
                            'type': '电阻',
                            'value': f"{value}Ω",
                            '电压': f"{voltage:.3f}V",
                            '电流': f"{current:.3f}A"
                        }
                    except ValueError:
                        results[comp.name] = {
                            'type': '电阻',
                            'value': f"{comp.value}Ω",
                            '电压': '计算错误',
                            '电流': '计算错误'
                        }
                elif isinstance(comp, VoltageSource):
                    results[comp.name] = {
                        'type': '电压源',
                        'value': f"{comp.value}V",
                        '状态': '激活'
                    }
            
            return results
        except Exception as e:
            return {'错误': f'仿真失败: {str(e)}'}
    
    def analyze_ac(self, frequency):
        # 简化的交流分析实现
        results = {}
        for component in self.components:
            if isinstance(component, Resistor):
                results[component.name] = f"电阻 {component.value}Ω (阻抗: {component.value}Ω)"
            elif isinstance(component, Capacitor):
                try:
                    impedance = 1 / (2 * np.pi * frequency * float(component.value))
                    results[component.name] = f"电容 {component.value}F (阻抗: {impedance:.2f}Ω)"
                except ValueError:
                    results[component.name] = f"电容 {component.value}F (阻抗: 计算错误)"
            elif isinstance(component, Inductor):
                try:
                    impedance = 2 * np.pi * frequency * float(component.value)
                    results[component.name] = f"电感 {component.value}H (阻抗: {impedance:.2f}Ω)"
                except ValueError:
                    results[component.name] = f"电感 {component.value}H (阻抗: 计算错误)"
        
        return results
    
    def dc_sweep(self, source_name, start, stop, steps):
        # 直流扫描分析
        voltages = np.linspace(start, stop, steps)
        currents = []
        
        # 简化的直流扫描实现
        for v in voltages:
            # 在实际应用中，这里应该重新计算电路响应
            # 这里使用一个简单的线性模型作为示例
            total_resistance = 0
            for comp in self.components:
                if isinstance(comp, Resistor):
                    try:
                        total_resistance += float(comp.value)
                    except ValueError:
                        pass
            
            if total_resistance > 0:
                current = v / total_resistance
            else:
                current = 0
            currents.append(current)
        
        return voltages, currents
    
    def transient_analysis(self, duration, time_step):
        # 瞬态分析
        time = np.arange(0, duration, time_step)
        voltages = []
        
        # 简化的瞬态分析实现
        for t in time:
            # 在实际应用中，这里应该求解微分方程
            # 这里使用一个简单的正弦波作为示例
            voltage = 5 * np.sin(2 * np.pi * 50 * t)  # 50Hz正弦波
            voltages.append(voltage)
        
        return time, voltages

# 主窗口
class CircuitDesigner(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("智能电路设计系统 - 增强版")
        self.setGeometry(100, 100, 1400, 900)
        
        # 创建中心画布
        self.canvas = CircuitCanvas()
        self.setCentralWidget(self.canvas)
        
        # 创建停靠窗口
        self.library = ComponentLibrary()
        self.properties = PropertiesPanel()
        self.simulation_plot = SimulationPlot()
        
        self.addDockWidget(Qt.LeftDockWidgetArea, self.library)
        self.addDockWidget(Qt.RightDockWidgetArea, self.properties)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.simulation_plot)
        
        # 创建菜单栏
        self.create_menus()
        
        # 创建工具栏
        self.create_toolbar()
        
        # 连接信号和槽
        self.connect_signals()
        
        # 创建仿真引擎
        self.simulator = CircuitSimulator()
        
        # 状态栏
        self.statusBar().showMessage("就绪")
        
        # 撤销/重做栈
        self.undo_stack = []
        self.redo_stack = []
        self.max_undo_steps = 50
        
        # 保存当前状态到撤销栈
        self.save_state()
    
    def create_menus(self):
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu("文件")
        
        new_action = QAction("新建", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self.new_circuit)
        
        open_action = QAction("打开", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.open_circuit)
        
        save_action = QAction("保存", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.save_circuit)
        
        export_action = QAction("导出为图片", self)
        export_action.triggered.connect(self.export_image)
        
        print_action = QAction("打印", self)
        print_action.setShortcut("Ctrl+P")
        print_action.triggered.connect(self.print_circuit)
        
        file_menu.addAction(new_action)
        file_menu.addAction(open_action)
        file_menu.addAction(save_action)
        file_menu.addSeparator()
        file_menu.addAction(export_action)
        file_menu.addAction(print_action)
        
        # 编辑菜单
        edit_menu = menubar.addMenu("编辑")
        
        undo_action = QAction("撤销", self)
        undo_action.setShortcut("Ctrl+Z")
        undo_action.triggered.connect(self.undo)
        
        redo_action = QAction("重做", self)
        redo_action.setShortcut("Ctrl+Y")
        redo_action.triggered.connect(self.redo)
        
        delete_action = QAction("删除", self)
        delete_action.setShortcut("Del")
        delete_action.triggered.connect(self.delete_selected)
        
        rotate_action = QAction("旋转", self)
        rotate_action.setShortcut("R")
        rotate_action.triggered.connect(self.rotate_selected)
        
        edit_menu.addAction(undo_action)
        edit_menu.addAction(redo_action)
        edit_menu.addSeparator()
        edit_menu.addAction(delete_action)
        edit_menu.addAction(rotate_action)
        
        # 视图菜单
        view_menu = menubar.addMenu("视图")
        
        zoom_in_action = QAction("放大", self)
        zoom_in_action.setShortcut("Ctrl++")
        zoom_in_action.triggered.connect(self.canvas.zoom_in)
        
        zoom_out_action = QAction("缩小", self)
        zoom_out_action.setShortcut("Ctrl+-")
        zoom_out_action.triggered.connect(self.canvas.zoom_out)
        
        reset_zoom_action = QAction("重置缩放", self)
        reset_zoom_action.setShortcut("Ctrl+0")
        reset_zoom_action.triggered.connect(self.canvas.reset_zoom)
        
        toggle_grid_action = QAction("显示/隐藏网格", self)
        toggle_grid_action.setShortcut("G")
        toggle_grid_action.triggered.connect(self.toggle_grid)
        
        view_menu.addAction(zoom_in_action)
        view_menu.addAction(zoom_out_action)
        view_menu.addAction(reset_zoom_action)
        view_menu.addSeparator()
        view_menu.addAction(toggle_grid_action)
        
        # 仿真菜单
        sim_menu = menubar.addMenu("仿真")
        
        dc_analysis = QAction("直流分析", self)
        dc_analysis.triggered.connect(self.dc_analysis)
        
        ac_analysis = QAction("交流分析", self)
        ac_analysis.triggered.connect(self.ac_analysis)
        
        dc_sweep = QAction("直流扫描", self)
        dc_sweep.triggered.connect(self.dc_sweep)
        
        transient_analysis = QAction("瞬态分析", self)
        transient_analysis.triggered.connect(self.transient_analysis)
        
        sim_menu.addAction(dc_analysis)
        sim_menu.addAction(ac_analysis)
        sim_menu.addAction(dc_sweep)
        sim_menu.addAction(transient_analysis)
        
        # 工具菜单
        tool_menu = menubar.addMenu("工具")
        
        auto_wire = QAction("自动布线", self)
        auto_wire.triggered.connect(self.auto_wire)
        
        align_components = QAction("对齐元件", self)
        align_components.triggered.connect(self.align_components)
        
        circuit_check = QAction("电路检查", self)
        circuit_check.triggered.connect(self.circuit_check)
        
        tool_menu.addAction(auto_wire)
        tool_menu.addAction(align_components)
        tool_menu.addAction(circuit_check)
    
    def create_toolbar(self):
        toolbar = QToolBar("主工具栏")
        self.addToolBar(toolbar)
        
        # 添加工具按钮
        new_btn = QAction(QIcon(), "新建", self)
        new_btn.triggered.connect(self.new_circuit)
        toolbar.addAction(new_btn)
        
        save_btn = QAction(QIcon(), "保存", self)
        save_btn.triggered.connect(self.save_circuit)
        toolbar.addAction(save_btn)
        
        toolbar.addSeparator()
        
        undo_btn = QAction(QIcon(), "撤销", self)
        undo_btn.triggered.connect(self.undo)
        toolbar.addAction(undo_btn)
        
        redo_btn = QAction(QIcon(), "重做", self)
        redo_btn.triggered.connect(self.redo)
        toolbar.addAction(redo_btn)
        
        toolbar.addSeparator()
        
        sim_btn = QAction(QIcon(), "仿真", self)
        sim_btn.triggered.connect(self.dc_analysis)
        toolbar.addAction(sim_btn)
        
        toolbar.addSeparator()
        
        zoom_in_btn = QAction(QIcon(), "放大", self)
        zoom_in_btn.triggered.connect(self.canvas.zoom_in)
        toolbar.addAction(zoom_in_btn)
        
        zoom_out_btn = QAction(QIcon(), "缩小", self)
        zoom_out_btn.triggered.connect(self.canvas.zoom_out)
        toolbar.addAction(zoom_out_btn)
    
    def connect_signals(self):
        # 连接元件库按钮
        self.library.resistor_btn.clicked.connect(self.add_resistor)
        self.library.capacitor_btn.clicked.connect(self.add_capacitor)
        self.library.inductor_btn.clicked.connect(self.add_inductor)
        self.library.voltage_btn.clicked.connect(self.add_voltage_source)
        self.library.current_btn.clicked.connect(self.add_current_source)
        self.library.diode_btn.clicked.connect(self.add_diode)
        self.library.ground_btn.clicked.connect(self.add_ground)
        
        # 连接属性面板
        self.properties.apply_btn.clicked.connect(self.apply_properties)
        
        # 连接画布选择事件
        self.canvas.componentSelected.connect(self.properties.set_component)
        
        # 连接画布变化事件（用于撤销/重做）
        self.canvas.canvasUpdated.connect(self.on_canvas_change)
    
    def on_canvas_change(self):
        # 当画布发生变化时保存状态（简化实现）
        pass
    
    def save_state(self):
        # 保存当前电路状态到撤销栈
        state = {
            'components': [comp.to_dict() for comp in self.canvas.components],
            'wires': [(wire[0].name, wire[1], wire[2].name, wire[3]) for wire in self.canvas.wires]
        }
        
        self.undo_stack.append(state)
        if len(self.undo_stack) > self.max_undo_steps:
            self.undo_stack.pop(0)
        
        # 清空重做栈
        self.redo_stack.clear()
    
    def restore_state(self, state):
        # 从状态字典恢复电路
        self.canvas.components.clear()
        self.canvas.wires.clear()
        
        # 重建元件
        component_map = {}
        for comp_data in state['components']:
            component = CircuitComponent.from_dict(comp_data)
            self.canvas.add_component(component)
            self.simulator.add_component(component)
            component_map[comp_data['name']] = component
        
        # 重建导线
        for wire_data in state['wires']:
            comp1 = component_map.get(wire_data[0])
            comp2 = component_map.get(wire_data[2])
            if comp1 and comp2:
                self.canvas.wires.append((comp1, wire_data[1], comp2, wire_data[3]))
        
        self.canvas.update()
    
    def undo(self):
        if len(self.undo_stack) > 1:  # 保留初始状态
            # 将当前状态移到重做栈
            self.redo_stack.append(self.undo_stack.pop())
            
            # 恢复上一个状态
            if self.undo_stack:
                self.restore_state(self.undo_stack[-1])
    
    def redo(self):
        if self.redo_stack:
            # 将重做栈顶状态移到撤销栈
            state = self.redo_stack.pop()
            self.undo_stack.append(state)
            
            # 恢复状态
            self.restore_state(state)
    
    def apply_properties(self):
        self.properties.apply_changes()
        self.canvas.update()
        self.save_state()
    
    def add_resistor(self):
        resistor = Resistor(f"R{len(self.canvas.components)+1}", "100", 100, 100)
        self.add_component_with_undo(resistor)
    
    def add_capacitor(self):
        capacitor = Capacitor(f"C{len(self.canvas.components)+1}", "0.001", 200, 100)
        self.add_component_with_undo(capacitor)
    
    def add_inductor(self):
        inductor = Inductor(f"L{len(self.canvas.components)+1}", "0.001", 300, 100)
        self.add_component_with_undo(inductor)
    
    def add_voltage_source(self):
        voltage = VoltageSource(f"V{len(self.canvas.components)+1}", "5", 400, 100)
        self.add_component_with_undo(voltage)
    
    def add_current_source(self):
        current = CurrentSource(f"I{len(self.canvas.components)+1}", "0.1", 500, 100)
        self.add_component_with_undo(current)
    
    def add_diode(self):
        diode = Diode(f"D{len(self.canvas.components)+1}", "", 600, 100)
        self.add_component_with_undo(diode)
    
    def add_ground(self):
        ground = Ground(f"GND{len(self.canvas.components)+1}", "", 700, 100)
        self.add_component_with_undo(ground)
    
    def add_component_with_undo(self, component):
        self.save_state()
        self.canvas.add_component(component)
        self.simulator.add_component(component)
    
    def delete_selected(self):
        if self.canvas.selected_component:
            self.save_state()
            self.canvas.remove_component(self.canvas.selected_component)
    
    def rotate_selected(self):
        if self.canvas.selected_component:
            self.save_state()
            self.canvas.selected_component.rotate()
            self.canvas.update()
    
    def toggle_grid(self):
        self.canvas.show_grid = not self.canvas.show_grid
        self.canvas.update()
    
    def new_circuit(self):
        self.save_state()
        self.canvas.components.clear()
        self.canvas.wires.clear()
        self.canvas.update()
        self.simulator = CircuitSimulator()
        self.statusBar().showMessage("新建电路")
    
    def save_circuit(self):
        filename, _ = QFileDialog.getSaveFileName(self, "保存电路", "", "电路文件 (*.circuit)")
        if filename:
            circuit_data = {
                'components': [comp.to_dict() for comp in self.canvas.components],
                'wires': [(wire[0].name, wire[1], wire[2].name, wire[3]) for wire in self.canvas.wires]
            }
            
            with open(filename, 'w') as f:
                json.dump(circuit_data, f, indent=2)
            
            self.statusBar().showMessage(f"电路已保存到 {filename}")
    
    def open_circuit(self):
        filename, _ = QFileDialog.getOpenFileName(self, "打开电路", "", "电路文件 (*.circuit)")
        if filename:
            with open(filename, 'r') as f:
                circuit_data = json.load(f)
            
            self.save_state()
            self.new_circuit()
            
            # 重建元件
            component_map = {}
            for comp_data in circuit_data['components']:
                component = CircuitComponent.from_dict(comp_data)
                self.canvas.add_component(component)
                self.simulator.add_component(component)
                component_map[comp_data['name']] = component
            
            # 重建导线
            for wire_data in circuit_data['wires']:
                comp1 = component_map.get(wire_data[0])
                comp2 = component_map.get(wire_data[2])
                if comp1 and comp2:
                    self.canvas.wires.append((comp1, wire_data[1], comp2, wire_data[3]))
            
            self.canvas.update()
            self.statusBar().showMessage(f"已打开电路 {filename}")
    
    def export_image(self):
        filename, _ = QFileDialog.getSaveFileName(self, "导出为图片", "", "PNG图像 (*.png);;JPEG图像 (*.jpg)")
        if filename:
            # 创建与画布相同大小的图像
            image = QImage(self.canvas.size(), QImage.Format_ARGB32)
            image.fill(Qt.white)
            
            # 在图像上绘制电路
            painter = QPainter(image)
            self.canvas.paintEvent(QPaintEvent(self.canvas.rect()))
            painter.end()
            
            # 保存图像
            image.save(filename)
            self.statusBar().showMessage(f"电路已导出为 {filename}")
    
    def print_circuit(self):
        printer = QPrinter(QPrinter.HighResolution)
        dialog = QPrintDialog(printer, self)
        if dialog.exec_() == QPrintDialog.Accepted:
            painter = QPainter(printer)
            self.canvas.render(painter)
            painter.end()
            self.statusBar().showMessage("电路已打印")
    
    def dc_analysis(self):
        results = self.simulator.analyze_dc()
        
        # 显示结果对话框
        dialog = QDialog(self)
        dialog.setWindowTitle("直流分析结果")
        dialog.resize(400, 300)
        layout = QVBoxLayout()
        
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        
        result_text = "直流分析结果:\n\n"
        for name, result in results.items():
            if isinstance(result, dict):
                result_text += f"{name} ({result['type']}):\n"
                for key, value in result.items():
                    if key != 'type':
                        result_text += f"  {key}: {value}\n"
            else:
                result_text += f"{name}: {result}\n"
        
        text_edit.setText(result_text)
        layout.addWidget(text_edit)
        
        ok_btn = QPushButton("确定")
        ok_btn.clicked.connect(dialog.accept)
        layout.addWidget(ok_btn)
        
        dialog.setLayout(layout)
        dialog.exec_()
    
    def ac_analysis(self):
        freq, ok = QInputDialog.getDouble(self, "交流分析", "输入频率 (Hz):", 1000, 0.1, 1000000, 2)
        if ok:
            results = self.simulator.analyze_ac(freq)
            
            # 显示结果对话框
            dialog = QDialog(self)
            dialog.setWindowTitle("交流分析结果")
            layout = QVBoxLayout()
            
            text_edit = QTextEdit()
            text_edit.setReadOnly(True)
            
            result_text = f"频率 {freq} Hz 的交流分析结果:\n\n"
            for name, result in results.items():
                result_text += f"{name}: {result}\n"
            
            text_edit.setText(result_text)
            layout.addWidget(text_edit)
            
            ok_btn = QPushButton("确定")
            ok_btn.clicked.connect(dialog.accept)
            layout.addWidget(ok_btn)
            
            dialog.setLayout(layout)
            dialog.exec_()
    
    def dc_sweep(self):
        # 获取扫描参数
        source, ok1 = QInputDialog.getItem(self, "直流扫描", "选择扫描源:", 
                                          [comp.name for comp in self.canvas.components 
                                           if isinstance(comp, VoltageSource)], 0, False)
        
        if not ok1:
            return
        
        start, ok2 = QInputDialog.getDouble(self, "直流扫描", "起始电压 (V):", 0, -100, 100, 2)
        stop, ok3 = QInputDialog.getDouble(self, "直流扫描", "结束电压 (V):", 5, -100, 100, 2)
        steps, ok4 = QInputDialog.getInt(self, "直流扫描", "步数:", 100, 10, 1000, 10)
        
        if ok2 and ok3 and ok4:
            voltages, currents = self.simulator.dc_sweep(source, start, stop, steps)
            self.simulation_plot.plot_dc_sweep(voltages, currents)
    
    def transient_analysis(self):
        duration, ok1 = QInputDialog.getDouble(self, "瞬态分析", "仿真时长 (s):", 0.1, 0.001, 10, 3)
        time_step, ok2 = QInputDialog.getDouble(self, "瞬态分析", "时间步长 (s):", 0.001, 0.0001, 1, 4)
        
        if ok1 and ok2:
            time, voltages = self.simulator.transient_analysis(duration, time_step)
            self.simulation_plot.plot_transient(time, voltages)
    
    def auto_wire(self):
        # 简化的自动布线实现
        # 在实际应用中，这里应该实现更复杂的自动布线算法
        if len(self.canvas.components) >= 2:
            self.save_state()
            
            # 简单地将所有元件按顺序连接
            for i in range(len(self.canvas.components) - 1):
                comp1 = self.canvas.components[i]
                comp2 = self.canvas.components[i + 1]
                
                points1 = comp1.get_connection_points()
                points2 = comp2.get_connection_points()
                
                if points1 and points2:
                    # 连接两个元件的第一个连接点
                    self.canvas.wires.append((comp1, 0, comp2, 0))
            
            self.canvas.update()
            self.statusBar().showMessage("自动布线完成")
    
    def align_components(self):
        # 简化的对齐功能
        if self.canvas.components:
            self.save_state()
            
            # 将所有元件垂直对齐到第一个元件的位置
            base_y = self.canvas.components[0].y
            x_pos = 100
            for component in self.canvas.components:
                component.y = base_y
                component.x = x_pos
                x_pos += 100
            
            self.canvas.update()
            self.statusBar().showMessage("元件已对齐")
    
    def circuit_check(self):
        # 简化的电路检查功能
        errors = []
        warnings = []
        
        # 检查是否有未连接的元件
        connected_components = set()
        for wire in self.canvas.wires:
            connected_components.add(wire[0])
            connected_components.add(wire[2])
        
        for comp in self.canvas.components:
            if comp not in connected_components and not isinstance(comp, Ground):
                warnings.append(f"元件 {comp.name} 未连接")
        
        # 检查是否有短路
        # 在实际应用中，这里应该实现更复杂的短路检测算法
        
        # 显示检查结果
        dialog = QDialog(self)
        dialog.setWindowTitle("电路检查结果")
        layout = QVBoxLayout()
        
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        
        result_text = "电路检查结果:\n\n"
        
        if errors:
            result_text += "错误:\n"
            for error in errors:
                result_text += f"• {error}\n"
            result_text += "\n"
        
        if warnings:
            result_text += "警告:\n"
            for warning in warnings:
                result_text += f"• {warning}\n"
        
        if not errors and not warnings:
            result_text += "电路检查通过，未发现问题。"
        
        text_edit.setText(result_text)
        layout.addWidget(text_edit)
        
        ok_btn = QPushButton("确定")
        ok_btn.clicked.connect(dialog.accept)
        layout.addWidget(ok_btn)
        
        dialog.setLayout(layout)
        dialog.exec_()

# 应用程序入口
if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 设置应用程序样式
    app.setStyle("Fusion")
    
    # 创建主窗口
    window = CircuitDesigner()
    window.show()
    
    sys.exit(app.exec_())