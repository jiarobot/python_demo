import sys
import math
import random
from datetime import datetime, timedelta
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QGridLayout, QSplitter, QTabWidget,
                             QLabel, QPushButton, QComboBox, QSpinBox, 
                             QDoubleSpinBox, QTextEdit, QListWidget, 
                             QListWidgetItem, QGroupBox, QFrame, QMessageBox,
                             QSlider, QProgressBar, QToolBar, QAction, 
                             QStatusBar, QDialog, QDialogButtonBox, QLineEdit)
from PyQt5.QtCore import Qt, QTimer, QPoint, QRect, pyqtSignal, QSize
from PyQt5.QtGui import QPainter, QPen, QBrush, QColor, QFont, QIcon, QPixmap, QPolygon

# 战场实体类
class BattleEntity:
    def __init__(self, entity_id, name, entity_type, x, y, strength=100, side="Allied"):
        self.id = entity_id
        self.name = name
        self.type = entity_type  # "Infantry", "Tank", "Artillery", "Air", "Naval", "HQ"
        self.x = x
        self.y = y
        self.strength = strength  # 0-100
        self.side = side  # "Allied" or "Axis"
        self.movement_range = self.get_movement_range()
        self.attack_range = self.get_attack_range()
        self.orders = []
        self.status = "Idle"
        self.supply_level = 100
        self.morale = 100
        
    def get_movement_range(self):
        ranges = {
            "Infantry": 20,
            "Tank": 40,
            "Artillery": 15,
            "Air": 100,
            "Naval": 30,
            "HQ": 10
        }
        return ranges.get(self.type, 20)
    
    def get_attack_range(self):
        ranges = {
            "Infantry": 10,
            "Tank": 15,
            "Artillery": 30,
            "Air": 50,
            "Naval": 25,
            "HQ": 5
        }
        return ranges.get(self.type, 10)
    
    def can_reach(self, target_x, target_y):
        distance = math.sqrt((self.x - target_x)**2 + (self.y - target_y)**2)
        return distance <= self.movement_range
    
    def move_to(self, x, y):
        if self.can_reach(x, y):
            self.x = x
            self.y = y
            self.supply_level -= 5
            return True
        return False
    
    def attack(self, target):
        if target.side == self.side:
            return False, "Cannot attack friendly units"
            
        distance = math.sqrt((self.x - target.x)**2 + (self.y - target.y)**2)
        if distance > self.attack_range:
            return False, "Target out of range"
            
        # 计算攻击效果
        base_damage = random.randint(10, 30)
        type_modifier = self.get_type_modifier(target.type)
        damage = int(base_damage * type_modifier)
        
        target.strength = max(0, target.strength - damage)
        self.supply_level -= 10
        
        result = f"{self.name} attacked {target.name} for {damage} damage"
        if target.strength <= 0:
            result += f" - {target.name} destroyed!"
            
        return True, result
    
    def get_type_modifier(self, target_type):
        modifiers = {
            "Infantry": {"Infantry": 1.0, "Tank": 0.5, "Artillery": 1.2, "Air": 0.3, "Naval": 0.2, "HQ": 1.5},
            "Tank": {"Infantry": 1.5, "Tank": 1.0, "Artillery": 1.3, "Air": 0.5, "Naval": 0.3, "HQ": 1.5},
            "Artillery": {"Infantry": 1.3, "Tank": 1.1, "Artillery": 1.0, "Air": 0.7, "Naval": 0.8, "HQ": 1.5},
            "Air": {"Infantry": 1.5, "Tank": 1.2, "Artillery": 1.3, "Air": 1.0, "Naval": 1.5, "HQ": 1.8},
            "Naval": {"Infantry": 0.5, "Tank": 0.3, "Artillery": 0.7, "Air": 0.8, "Naval": 1.0, "HQ": 1.2},
            "HQ": {"Infantry": 0.8, "Tank": 0.5, "Artillery": 0.7, "Air": 0.3, "Naval": 0.2, "HQ": 1.0}
        }
        return modifiers.get(self.type, {}).get(target_type, 1.0)
    
    def resupply(self):
        self.supply_level = min(100, self.supply_level + 20)
        return f"{self.name} resupplied"

# 战场地图部件
class BattleMapWidget(QWidget):
    entity_selected = pyqtSignal(object)
    move_order_requested = pyqtSignal(object, int, int)
    attack_order_requested = pyqtSignal(object, object)
    
    def __init__(self):
        super().__init__()
        self.setMinimumSize(800, 600)
        self.entities = []
        self.selected_entity = None
        self.hover_entity = None
        self.show_ranges = False
        self.show_supply_lines = True
        self.terrain = self.generate_terrain()
        
    def generate_terrain(self):
        # 生成简单的地形数据
        terrain = []
        for x in range(0, 100, 10):
            for y in range(0, 100, 10):
                terrain_type = random.choice(["Plains", "Forest", "Hills", "Mountains", "Water"])
                terrain.append({"x": x, "y": y, "type": terrain_type})
        return terrain
    
    def add_entity(self, entity):
        self.entities.append(entity)
        self.update()
    
    def remove_entity(self, entity):
        if entity in self.entities:
            self.entities.remove(entity)
            if self.selected_entity == entity:
                self.selected_entity = None
            self.update()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 绘制地形
        self.draw_terrain(painter)
        
        # 绘制补给线
        if self.show_supply_lines:
            self.draw_supply_lines(painter)
        
        # 绘制实体
        for entity in self.entities:
            self.draw_entity(painter, entity)
        
        # 绘制选中实体的范围
        if self.selected_entity and self.show_ranges:
            self.draw_entity_ranges(painter, self.selected_entity)
    
    def draw_terrain(self, painter):
        width = self.width()
        height = self.height()
        
        # 绘制基础网格
        painter.setPen(QPen(QColor(200, 200, 200), 1))
        for x in range(0, width, 50):
            painter.drawLine(x, 0, x, height)
        for y in range(0, height, 50):
            painter.drawLine(0, y, width, y)
        
        # 绘制地形类型
        for tile in self.terrain:
            x = tile["x"] * width / 100
            y = tile["y"] * height / 100
            w = 10 * width / 100
            h = 10 * height / 100
            
            if tile["type"] == "Forest":
                painter.fillRect(int(x), int(y), int(w), int(h), QColor(34, 139, 34, 100))
            elif tile["type"] == "Hills":
                painter.fillRect(int(x), int(y), int(w), int(h), QColor(139, 137, 137, 100))
            elif tile["type"] == "Mountains":
                painter.fillRect(int(x), int(y), int(w), int(h), QColor(105, 105, 105, 100))
            elif tile["type"] == "Water":
                painter.fillRect(int(x), int(y), int(w), int(h), QColor(30, 144, 255, 100))
    
    def draw_supply_lines(self, painter):
        painter.setPen(QPen(QColor(255, 165, 0, 150), 2, Qt.DashLine))
        
        for entity in self.entities:
            if entity.supply_level < 50:
                # 找到最近的友军HQ
                nearest_hq = None
                min_dist = float('inf')
                
                for other in self.entities:
                    if other.side == entity.side and other.type == "HQ":
                        dist = math.sqrt((entity.x - other.x)**2 + (entity.y - other.y)**2)
                        if dist < min_dist:
                            min_dist = dist
                            nearest_hq = other
                
                if nearest_hq:
                    # 绘制补给线
                    start_x = entity.x * self.width() / 100
                    start_y = entity.y * self.height() / 100
                    end_x = nearest_hq.x * self.width() / 100
                    end_y = nearest_hq.y * self.height() / 100
                    
                    painter.drawLine(int(start_x), int(start_y), int(end_x), int(end_y))
    
    def draw_entity(self, painter, entity):
        x = entity.x * self.width() / 100
        y = entity.y * self.height() / 100
        
        # 选择颜色
        if entity.side == "Allied":
            color = QColor(0, 0, 255)  # 蓝色
        else:
            color = QColor(255, 0, 0)  # 红色
            
        # 根据实体类型选择形状
        if entity.type == "Infantry":
            self.draw_infantry(painter, x, y, color, entity.strength)
        elif entity.type == "Tank":
            self.draw_tank(painter, x, y, color, entity.strength)
        elif entity.type == "Artillery":
            self.draw_artillery(painter, x, y, color, entity.strength)
        elif entity.type == "Air":
            self.draw_air(painter, x, y, color, entity.strength)
        elif entity.type == "Naval":
            self.draw_naval(painter, x, y, color, entity.strength)
        elif entity.type == "HQ":
            self.draw_hq(painter, x, y, color, entity.strength)
        
        # 如果实体被选中，绘制高亮边框
        if entity == self.selected_entity:
            painter.setPen(QPen(QColor(255, 255, 0), 3))
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(int(x-15), int(y-15), 30, 30)
        
        # 绘制实体名称和状态
        painter.setPen(Qt.black)
        painter.drawText(int(x-20), int(y-20), f"{entity.name} ({entity.strength}%)")
    
    def draw_infantry(self, painter, x, y, color, strength):
        painter.setPen(QPen(color, 2))
        painter.setBrush(QBrush(color.lighter(150)))
        
        # 绘制步兵符号
        painter.drawEllipse(int(x-8), int(y-8), 16, 16)
        
        # 绘制强度指示器
        self.draw_strength_indicator(painter, x, y, strength)
    
    def draw_tank(self, painter, x, y, color, strength):
        painter.setPen(QPen(color, 2))
        painter.setBrush(QBrush(color.lighter(150)))
        
        # 绘制坦克符号
        painter.drawRect(int(x-10), int(y-6), 20, 12)
        painter.drawRect(int(x-8), int(y-10), 16, 4)
        
        # 绘制强度指示器
        self.draw_strength_indicator(painter, x, y, strength)
    
    def draw_artillery(self, painter, x, y, color, strength):
        painter.setPen(QPen(color, 2))
        painter.setBrush(QBrush(color.lighter(150)))
        
        # 绘制炮兵符号
        painter.drawRect(int(x-8), int(y-8), 16, 16)
        painter.drawLine(int(x), int(y-8), int(x), int(y-16))
        
        # 绘制强度指示器
        self.draw_strength_indicator(painter, x, y, strength)
    
    def draw_air(self, painter, x, y, color, strength):
        painter.setPen(QPen(color, 2))
        painter.setBrush(QBrush(color.lighter(150)))
        
        # 绘制飞机符号
        points = [
            QPoint(int(x), int(y-10)),
            QPoint(int(x-8), int(y+5)),
            QPoint(int(x+8), int(y+5))
        ]
        painter.drawPolygon(QPolygon(points))
        
        # 绘制强度指示器
        self.draw_strength_indicator(painter, x, y, strength)
    
    def draw_naval(self, painter, x, y, color, strength):
        painter.setPen(QPen(color, 2))
        painter.setBrush(QBrush(color.lighter(150)))
        
        # 绘制海军符号
        painter.drawEllipse(int(x-12), int(y-4), 24, 8)
        painter.drawRect(int(x-8), int(y-8), 16, 4)
        
        # 绘制强度指示器
        self.draw_strength_indicator(painter, x, y, strength)
    
    def draw_hq(self, painter, x, y, color, strength):
        painter.setPen(QPen(color, 2))
        painter.setBrush(QBrush(color.lighter(200)))
        
        # 绘制指挥部符号
        painter.drawRect(int(x-10), int(y-10), 20, 20)
        painter.drawLine(int(x-10), int(y-10), int(x+10), int(y+10))
        painter.drawLine(int(x+10), int(y-10), int(x-10), int(y+10))
        
        # 绘制强度指示器
        self.draw_strength_indicator(painter, x, y, strength)
    
    def draw_strength_indicator(self, painter, x, y, strength):
        # 在实体下方绘制强度条
        bar_width = 20
        bar_height = 4
        bar_x = x - bar_width/2
        bar_y = y + 15
        
        # 背景条
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor(100, 100, 100)))
        painter.drawRect(int(bar_x), int(bar_y), bar_width, bar_height)
        
        # 强度条
        if strength > 70:
            color = QColor(0, 255, 0)
        elif strength > 30:
            color = QColor(255, 255, 0)
        else:
            color = QColor(255, 0, 0)
            
        painter.setBrush(QBrush(color))
        filled_width = bar_width * strength / 100
        painter.drawRect(int(bar_x), int(bar_y), int(filled_width), bar_height)
    
    def draw_entity_ranges(self, painter, entity):
        x = entity.x * self.width() / 100
        y = entity.y * self.height() / 100
        
        # 绘制移动范围
        painter.setPen(QPen(QColor(0, 255, 0, 100), 2))
        painter.setBrush(QBrush(QColor(0, 255, 0, 30)))
        move_range = entity.movement_range * self.width() / 100
        painter.drawEllipse(int(x - move_range), int(y - move_range), 
                           int(move_range * 2), int(move_range * 2))
        
        # 绘制攻击范围
        painter.setPen(QPen(QColor(255, 0, 0, 100), 2))
        painter.setBrush(QBrush(QColor(255, 0, 0, 30)))
        attack_range = entity.attack_range * self.width() / 100
        painter.drawEllipse(int(x - attack_range), int(y - attack_range), 
                           int(attack_range * 2), int(attack_range * 2))
    
    def mousePressEvent(self, event):
        x = event.x() * 100 / self.width()
        y = event.y() * 100 / self.height()
        
        # 检查是否点击了实体
        clicked_entity = None
        for entity in self.entities:
            entity_x = entity.x * self.width() / 100
            entity_y = entity.y * self.height() / 100
            distance = math.sqrt((entity_x - event.x())**2 + (entity_y - event.y())**2)
            
            if distance < 15:  # 点击半径
                clicked_entity = entity
                break
        
        if clicked_entity:
            self.selected_entity = clicked_entity
            self.entity_selected.emit(clicked_entity)
        else:
            self.selected_entity = None
            self.entity_selected.emit(None)
            
            # 如果有选中的实体，并且是右键点击，则发出移动命令
            if event.button() == Qt.RightButton and self.selected_entity:
                self.move_order_requested.emit(self.selected_entity, x, y)
        
        self.update()
    
    def mouseMoveEvent(self, event):
        x = event.x() * 100 / self.width()
        y = event.y() * 100 / self.height()
        
        # 检查鼠标是否悬停在实体上
        hover_entity = None
        for entity in self.entities:
            entity_x = entity.x * self.width() / 100
            entity_y = entity.y * self.height() / 100
            distance = math.sqrt((entity_x - event.x())**2 + (entity_y - event.y())**2)
            
            if distance < 15:  # 悬停半径
                hover_entity = entity
                break
        
        if hover_entity != self.hover_entity:
            self.hover_entity = hover_entity
            self.update()

# 实体信息面板
class EntityInfoWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.entity = None
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 基本信息组
        info_group = QGroupBox("单位信息")
        info_layout = QGridLayout()
        
        self.name_label = QLabel("名称: -")
        self.type_label = QLabel("类型: -")
        self.side_label = QLabel("阵营: -")
        self.position_label = QLabel("位置: -")
        
        info_layout.addWidget(self.name_label, 0, 0)
        info_layout.addWidget(self.type_label, 0, 1)
        info_layout.addWidget(self.side_label, 1, 0)
        info_layout.addWidget(self.position_label, 1, 1)
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # 状态组
        status_group = QGroupBox("状态")
        status_layout = QGridLayout()
        
        self.strength_label = QLabel("强度: -")
        self.strength_bar = QProgressBar()
        self.strength_bar.setMinimum(0)
        self.strength_bar.setMaximum(100)
        
        self.supply_label = QLabel("补给: -")
        self.supply_bar = QProgressBar()
        self.supply_bar.setMinimum(0)
        self.supply_bar.setMaximum(100)
        
        self.morale_label = QLabel("士气: -")
        self.morale_bar = QProgressBar()
        self.morale_bar.setMinimum(0)
        self.morale_bar.setMaximum(100)
        
        self.status_label = QLabel("状态: -")
        
        status_layout.addWidget(QLabel("强度:"), 0, 0)
        status_layout.addWidget(self.strength_bar, 0, 1)
        status_layout.addWidget(QLabel("补给:"), 1, 0)
        status_layout.addWidget(self.supply_bar, 1, 1)
        status_layout.addWidget(QLabel("士气:"), 2, 0)
        status_layout.addWidget(self.morale_bar, 2, 1)
        status_layout.addWidget(self.status_label, 3, 0, 1, 2)
        
        status_group.setLayout(status_layout)
        layout.addWidget(status_group)
        
        # 能力组
        capabilities_group = QGroupBox("能力")
        capabilities_layout = QGridLayout()
        
        self.movement_label = QLabel("移动范围: -")
        self.attack_label = QLabel("攻击范围: -")
        
        capabilities_layout.addWidget(self.movement_label, 0, 0)
        capabilities_layout.addWidget(self.attack_label, 0, 1)
        
        capabilities_group.setLayout(capabilities_layout)
        layout.addWidget(capabilities_group)
        
        # 命令按钮
        command_group = QGroupBox("命令")
        command_layout = QHBoxLayout()
        
        self.move_button = QPushButton("移动")
        self.attack_button = QPushButton("攻击")
        self.resupply_button = QPushButton("补给")
        
        command_layout.addWidget(self.move_button)
        command_layout.addWidget(self.attack_button)
        command_layout.addWidget(self.resupply_button)
        
        command_group.setLayout(command_layout)
        layout.addWidget(command_group)
        
        # 订单列表
        self.orders_list = QListWidget()
        layout.addWidget(QLabel("当前订单:"))
        layout.addWidget(self.orders_list)
        
        layout.addStretch()
        self.setLayout(layout)
    
    def set_entity(self, entity):
        self.entity = entity
        self.update_display()
    
    def update_display(self):
        if self.entity:
            self.name_label.setText(f"名称: {self.entity.name}")
            self.type_label.setText(f"类型: {self.entity.type}")
            self.side_label.setText(f"阵营: {self.entity.side}")
            self.position_label.setText(f"位置: ({self.entity.x:.1f}, {self.entity.y:.1f})")
            
            self.strength_label.setText(f"强度: {self.entity.strength}%")
            self.strength_bar.setValue(self.entity.strength)
            
            self.supply_label.setText(f"补给: {self.entity.supply_level}%")
            self.supply_bar.setValue(self.entity.supply_level)
            
            self.morale_label.setText(f"士气: {self.entity.morale}%")
            self.morale_bar.setValue(self.entity.morale)
            
            self.status_label.setText(f"状态: {self.entity.status}")
            
            self.movement_label.setText(f"移动范围: {self.entity.movement_range}")
            self.attack_label.setText(f"攻击范围: {self.entity.attack_range}")
            
            # 更新订单列表
            self.orders_list.clear()
            for order in self.entity.orders:
                self.orders_list.addItem(order)
        else:
            self.name_label.setText("名称: -")
            self.type_label.setText("类型: -")
            self.side_label.setText("阵营: -")
            self.position_label.setText("位置: -")
            
            self.strength_bar.setValue(0)
            self.supply_bar.setValue(0)
            self.morale_bar.setValue(0)
            self.status_label.setText("状态: -")
            
            self.movement_label.setText("移动范围: -")
            self.attack_label.setText("攻击范围: -")
            
            self.orders_list.clear()

# 命令控制面板
class CommandPanel(QWidget):
    def __init__(self, battle_map):
        super().__init__()
        self.battle_map = battle_map
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 实体选择
        entity_group = QGroupBox("选择单位")
        entity_layout = QVBoxLayout()
        
        self.entity_list = QListWidget()
        self.entity_list.itemSelectionChanged.connect(self.on_entity_selected)
        entity_layout.addWidget(self.entity_list)
        
        entity_group.setLayout(entity_layout)
        layout.addWidget(entity_group)
        
        # 命令组
        command_group = QGroupBox("战场命令")
        command_layout = QGridLayout()
        
        self.add_entity_button = QPushButton("部署新单位")
        self.remove_entity_button = QPushButton("移除单位")
        self.toggle_ranges_button = QPushButton("显示范围")
        self.toggle_supply_button = QPushButton("显示补给线")
        
        command_layout.addWidget(self.add_entity_button, 0, 0)
        command_layout.addWidget(self.remove_entity_button, 0, 1)
        command_layout.addWidget(self.toggle_ranges_button, 1, 0)
        command_layout.addWidget(self.toggle_supply_button, 1, 1)
        
        command_group.setLayout(command_layout)
        layout.addWidget(command_group)
        
        # 阵营信息
        side_group = QGroupBox("阵营状态")
        side_layout = QGridLayout()
        
        self.allied_count_label = QLabel("盟军单位: 0")
        self.axis_count_label = QLabel("轴心国单位: 0")
        self.allied_strength_label = QLabel("盟军总强度: 0%")
        self.axis_strength_label = QLabel("轴心国总强度: 0%")
        
        side_layout.addWidget(self.allied_count_label, 0, 0)
        side_layout.addWidget(self.axis_count_label, 0, 1)
        side_layout.addWidget(self.allied_strength_label, 1, 0)
        side_layout.addWidget(self.axis_strength_label, 1, 1)
        
        side_group.setLayout(side_layout)
        layout.addWidget(side_group)
        
        layout.addStretch()
        self.setLayout(layout)
        
        # 连接信号
        self.add_entity_button.clicked.connect(self.show_add_entity_dialog)
        self.remove_entity_button.clicked.connect(self.remove_selected_entity)
        self.toggle_ranges_button.clicked.connect(self.toggle_ranges)
        self.toggle_supply_button.clicked.connect(self.toggle_supply_lines)
    
    def update_entity_list(self, entities):
        self.entity_list.clear()
        for entity in entities:
            item = QListWidgetItem(f"{entity.name} ({entity.type}) - {entity.side}")
            item.setData(Qt.UserRole, entity)
            self.entity_list.addItem(item)
        
        self.update_side_info(entities)
    
    def update_side_info(self, entities):
        allied_count = 0
        axis_count = 0
        allied_strength = 0
        axis_strength = 0
        
        for entity in entities:
            if entity.side == "Allied":
                allied_count += 1
                allied_strength += entity.strength
            else:
                axis_count += 1
                axis_strength += entity.strength
        
        self.allied_count_label.setText(f"盟军单位: {allied_count}")
        self.axis_count_label.setText(f"轴心国单位: {axis_count}")
        
        if allied_count > 0:
            self.allied_strength_label.setText(f"盟军平均强度: {allied_strength/allied_count:.1f}%")
        else:
            self.allied_strength_label.setText("盟军平均强度: 0%")
            
        if axis_count > 0:
            self.axis_strength_label.setText(f"轴心国平均强度: {axis_strength/axis_count:.1f}%")
        else:
            self.axis_strength_label.setText("轴心国平均强度: 0%")
    
    def on_entity_selected(self):
        selected_items = self.entity_list.selectedItems()
        if selected_items:
            entity = selected_items[0].data(Qt.UserRole)
            self.battle_map.selected_entity = entity
            self.battle_map.entity_selected.emit(entity)
            self.battle_map.update()
    
    def show_add_entity_dialog(self):
        dialog = AddEntityDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            entity_data = dialog.get_entity_data()
            entity = BattleEntity(
                entity_id=len(self.battle_map.entities) + 1,
                name=entity_data["name"],
                entity_type=entity_data["type"],
                x=entity_data["x"],
                y=entity_data["y"],
                strength=entity_data["strength"],
                side=entity_data["side"]
            )
            self.battle_map.add_entity(entity)
            self.update_entity_list(self.battle_map.entities)
    
    def remove_selected_entity(self):
        selected_items = self.entity_list.selectedItems()
        if selected_items:
            entity = selected_items[0].data(Qt.UserRole)
            self.battle_map.remove_entity(entity)
            self.update_entity_list(self.battle_map.entities)
    
    def toggle_ranges(self):
        self.battle_map.show_ranges = not self.battle_map.show_ranges
        self.battle_map.update()
    
    def toggle_supply_lines(self):
        self.battle_map.show_supply_lines = not self.battle_map.show_supply_lines
        self.battle_map.update()

# 添加实体对话框
class AddEntityDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("部署新单位")
        self.setModal(True)
        self.init_ui()
    
    def init_ui(self):
        layout = QGridLayout()
        
        # 名称
        layout.addWidget(QLabel("名称:"), 0, 0)
        self.name_edit = QLineEdit()
        self.name_edit.setText(f"单位_{random.randint(1000, 9999)}")
        layout.addWidget(self.name_edit, 0, 1)
        
        # 类型
        layout.addWidget(QLabel("类型:"), 1, 0)
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Infantry", "Tank", "Artillery", "Air", "Naval", "HQ"])
        layout.addWidget(self.type_combo, 1, 1)
        
        # 阵营
        layout.addWidget(QLabel("阵营:"), 2, 0)
        self.side_combo = QComboBox()
        self.side_combo.addItems(["Allied", "Axis"])
        layout.addWidget(self.side_combo, 2, 1)
        
        # 位置
        layout.addWidget(QLabel("X位置:"), 3, 0)
        self.x_spin = QSpinBox()
        self.x_spin.setRange(0, 100)
        self.x_spin.setValue(random.randint(10, 90))
        layout.addWidget(self.x_spin, 3, 1)
        
        layout.addWidget(QLabel("Y位置:"), 4, 0)
        self.y_spin = QSpinBox()
        self.y_spin.setRange(0, 100)
        self.y_spin.setValue(random.randint(10, 90))
        layout.addWidget(self.y_spin, 4, 1)
        
        # 强度
        layout.addWidget(QLabel("初始强度:"), 5, 0)
        self.strength_spin = QSpinBox()
        self.strength_spin.setRange(1, 100)
        self.strength_spin.setValue(100)
        layout.addWidget(self.strength_spin, 5, 1)
        
        # 按钮
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box, 6, 0, 1, 2)
        
        self.setLayout(layout)
    
    def get_entity_data(self):
        return {
            "name": self.name_edit.text(),
            "type": self.type_combo.currentText(),
            "side": self.side_combo.currentText(),
            "x": self.x_spin.value(),
            "y": self.y_spin.value(),
            "strength": self.strength_spin.value()
        }

# 主窗口
class WWIICommandPlatform(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("二战指挥平台 - 可视化战场管理系统")
        self.setGeometry(100, 100, 1400, 900)
        
        self.battle_map = BattleMapWidget()
        self.entity_info = EntityInfoWidget()
        self.command_panel = CommandPanel(self.battle_map)
        
        self.init_ui()
        self.create_demo_entities()
        
        # 连接信号
        self.battle_map.entity_selected.connect(self.entity_info.set_entity)
        self.battle_map.move_order_requested.connect(self.issue_move_order)
    
    def init_ui(self):
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        main_layout = QHBoxLayout(central_widget)
        
        # 左侧命令面板
        main_layout.addWidget(self.command_panel, 1)
        
        # 中央地图
        main_layout.addWidget(self.battle_map, 3)
        
        # 右侧信息面板
        main_layout.addWidget(self.entity_info, 1)
        
        # 创建工具栏
        self.create_toolbar()
        
        # 创建状态栏
        self.statusBar().showMessage("就绪 - 二战指挥平台已启动")
    
    def create_toolbar(self):
        toolbar = QToolBar("主工具栏")
        toolbar.setIconSize(QSize(24, 24))
        self.addToolBar(toolbar)
        
        # 添加动作
        new_battle_action = QAction("新建战场", self)
        new_battle_action.setStatusTip("创建新的战场")
        new_battle_action.triggered.connect(self.new_battle)
        toolbar.addAction(new_battle_action)
        
        toolbar.addSeparator()
        
        save_action = QAction("保存战场", self)
        save_action.setStatusTip("保存当前战场状态")
        save_action.triggered.connect(self.save_battle)
        toolbar.addAction(save_action)
        
        load_action = QAction("加载战场", self)
        load_action.setStatusTip("加载已保存的战场")
        load_action.triggered.connect(self.load_battle)
        toolbar.addAction(load_action)
        
        toolbar.addSeparator()
        
        simulate_action = QAction("模拟回合", self)
        simulate_action.setStatusTip("执行一轮战斗模拟")
        simulate_action.triggered.connect(self.simulate_turn)
        toolbar.addAction(simulate_action)
    
    def create_demo_entities(self):
        # 创建演示单位
        entities = [
            BattleEntity(1, "第1步兵师", "Infantry", 20, 30, 100, "Allied"),
            BattleEntity(2, "第2装甲师", "Tank", 25, 35, 90, "Allied"),
            BattleEntity(3, "第1炮兵营", "Artillery", 30, 25, 85, "Allied"),
            BattleEntity(4, "盟军总部", "HQ", 15, 20, 100, "Allied"),
            
            BattleEntity(5, "德军第5装甲师", "Tank", 70, 60, 95, "Axis"),
            BattleEntity(6, "德军第8步兵师", "Infantry", 75, 65, 80, "Axis"),
            BattleEntity(7, "德军炮兵部队", "Artillery", 65, 70, 75, "Axis"),
            BattleEntity(8, "德军指挥部", "HQ", 80, 55, 100, "Axis"),
        ]
        
        for entity in entities:
            self.battle_map.add_entity(entity)
        
        self.command_panel.update_entity_list(entities)
    
    def issue_move_order(self, entity, x, y):
        if entity.move_to(x, y):
            entity.orders.append(f"移动到 ({x:.1f}, {y:.1f})")
            self.statusBar().showMessage(f"{entity.name} 已移动到 ({x:.1f}, {y:.1f})")
            self.battle_map.update()
            self.entity_info.update_display()
        else:
            QMessageBox.warning(self, "移动失败", "目标位置超出移动范围")
    
    def new_battle(self):
        reply = QMessageBox.question(self, "新建战场", 
                                    "这将清除当前战场。确定要继续吗？",
                                    QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.battle_map.entities.clear()
            self.battle_map.selected_entity = None
            self.battle_map.update()
            self.entity_info.set_entity(None)
            self.command_panel.update_entity_list([])
            self.statusBar().showMessage("已创建新战场")
    
    def save_battle(self):
        # 简化版保存功能
        QMessageBox.information(self, "保存战场", 
                              "战场状态已保存（演示功能）")
    
    def load_battle(self):
        # 简化版加载功能
        QMessageBox.information(self, "加载战场", 
                              "战场状态已加载（演示功能）")
    
    def simulate_turn(self):
        # 简化版战斗模拟
        if not self.battle_map.entities:
            QMessageBox.information(self, "模拟回合", "战场上没有单位")
            return
        
        # 随机选择一些单位进行移动和攻击
        for entity in self.battle_map.entities:
            if random.random() < 0.3:  # 30%概率移动
                new_x = max(0, min(100, entity.x + random.randint(-10, 10)))
                new_y = max(0, min(100, entity.y + random.randint(-10, 10)))
                if entity.can_reach(new_x, new_y):
                    entity.move_to(new_x, new_y)
                    entity.orders.append(f"自动移动到 ({new_x:.1f}, {new_y:.1f})")
            
            if random.random() < 0.2:  # 20%概率攻击
                # 寻找敌方目标
                targets = [e for e in self.battle_map.entities if e.side != entity.side]
                if targets:
                    target = random.choice(targets)
                    success, result = entity.attack(target)
                    if success:
                        entity.orders.append(f"攻击 {target.name}: {result}")
                        if target.strength <= 0:
                            self.battle_map.remove_entity(target)
                            self.statusBar().showMessage(f"{target.name} 已被摧毁!")
            
            if random.random() < 0.1:  # 10%概率补给
                result = entity.resupply()
                entity.orders.append(result)
        
        self.battle_map.update()
        self.command_panel.update_entity_list(self.battle_map.entities)
        if self.entity_info.entity:
            self.entity_info.update_display()
        
        self.statusBar().showMessage("回合模拟完成")

# 主程序
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("二战指挥平台")
    
    # 设置应用程序样式
    app.setStyle("Fusion")
    
    window = WWIICommandPlatform()
    window.show()
    
    sys.exit(app.exec_())