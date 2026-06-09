import sys
import numpy as np
import random
import math
import torch
import torch.nn as nn
import torch.optim as optim
from collections import deque, namedtuple
import matplotlib.pyplot as plt
from sklearn.preprocessing import StandardScaler
from datetime import datetime
import os
import json

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QPushButton, QSlider, QSpinBox, QDoubleSpinBox, 
                             QComboBox, QCheckBox, QGroupBox, QTabWidget, QTextEdit,
                             QSplitter, QFrame, QSizePolicy, QFileDialog, QMessageBox,
                             QGridLayout, QProgressBar, QTableWidget, QTableWidgetItem,
                             QHeaderView, QToolBar, QStatusBar, QDockWidget)
from PyQt6.QtCore import QPointF, Qt, QTimer, QSize, QRectF, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QPen, QFont, QBrush, QPixmap, QIcon, QAction
from PyQt6.QtCharts import QChart, QChartView, QLineSeries, QValueAxis

# 环境参数
TERRAIN_SIZE = 60
GRID_SIZE = 20
FPS = 60

# 颜色定义
BLUE = QColor(30, 144, 255)
RED = QColor(220, 20, 60)
GREEN = QColor(34, 139, 34)
BROWN = QColor(139, 69, 19)
GRAY = QColor(105, 105, 105)
BLACK = QColor(0, 0, 0)
WHITE = QColor(255, 255, 255)
YELLOW = QColor(255, 215, 0)
PURPLE = QColor(128, 0, 128)
CYAN = QColor(0, 255, 255)
ORANGE = QColor(255, 165, 0)

# 强化学习参数
BATCH_SIZE = 128
MEMORY_CAPACITY = 50000
GAMMA = 0.98
LR_ACTOR = 0.0001
LR_CRITIC = 0.001
EPSILON_START = 1.0
EPSILON_END = 0.01
EPSILON_DECAY = 0.998
TAU = 0.005  # 软更新参数
TARGET_UPDATE = 10
CLIP_GRAD = 1.0  # 梯度裁剪

# 地形类型
PLAIN = 0
FOREST = 1
MOUNTAIN = 2
WATER = 3
HILL = 4
ROAD = 5
BRIDGE = 6
CITY = 7

terrain_names = {
    PLAIN: "平原",
    FOREST: "森林",
    MOUNTAIN: "山地",
    WATER: "水域",
    HILL: "丘陵",
    ROAD: "道路",
    BRIDGE: "桥梁",
    CITY: "城市"
}

terrain_colors = {
    PLAIN: QColor(144, 238, 144),
    FOREST: QColor(0, 100, 0),
    MOUNTAIN: QColor(139, 137, 137),
    WATER: QColor(65, 105, 225),
    HILL: QColor(205, 133, 63),
    ROAD: QColor(169, 169, 169),
    BRIDGE: QColor(139, 69, 19),
    CITY: QColor(220, 20, 60)
}

# 单位类型
INFANTRY = 0
CAVALRY = 1
ARCHER = 2
ARTILLERY = 3
SCOUT = 4
MEDIC = 5
ENGINEER = 6
COMMANDER = 7

unit_names = {
    INFANTRY: "步兵",
    CAVALRY: "骑兵",
    ARCHER: "弓箭手",
    ARTILLERY: "炮兵",
    SCOUT: "侦察兵",
    MEDIC: "医疗兵",
    ENGINEER: "工程兵",
    COMMANDER: "指挥官"
}

unit_colors = {
    INFANTRY: BLUE,
    CAVALRY: RED,
    ARCHER: GREEN,
    ARTILLERY: YELLOW,
    SCOUT: WHITE,
    MEDIC: PURPLE,
    ENGINEER: ORANGE,
    COMMANDER: CYAN
}

# 单位属性 [攻击, 防御, 移动范围, 视野范围, 攻击范围, 特殊能力]
unit_stats = {
    INFANTRY: [6, 9, 3, 4, 1, "无"],
    CAVALRY: [9, 5, 6, 5, 1, "冲锋(移动后攻击伤害+2)"],
    ARCHER: [7, 4, 2, 5, 4, "远程攻击"],
    ARTILLERY: [12, 3, 1, 6, 6, "范围攻击"],
    SCOUT: [4, 4, 8, 9, 1, "隐身(森林中不可见)"],
    MEDIC: [3, 5, 3, 4, 1, "治疗(恢复20点生命)"],
    ENGINEER: [4, 6, 3, 4, 1, "建造(架桥/修路)"],
    COMMANDER: [5, 7, 4, 6, 1, "指挥(周围单位攻击+1,防御+1)"]
}

# 地形对移动的影响（移动消耗）
terrain_movement_cost = {
    PLAIN: 1,
    FOREST: 2,
    MOUNTAIN: 4,
    WATER: 10,
    HILL: 2,
    ROAD: 0.5,
    BRIDGE: 0.5,
    CITY: 1
}

# 地形对防御的影响（防御加成）
terrain_defense_bonus = {
    PLAIN: 0,
    FOREST: 2,
    MOUNTAIN: 4,
    WATER: 0,
    HILL: 1,
    ROAD: 0,
    BRIDGE: 0,
    CITY: 3
}

# 特殊能力消耗
ABILITY_COST = {
    "冲锋": 2,
    "治疗": 3,
    "建造": 4
}

# 天气类型
CLEAR = 0
RAIN = 1
FOG = 2
SNOW = 3

weather_names = {
    CLEAR: "晴",
    RAIN: "雨",
    FOG: "雾",
    SNOW: "雪"
}

weather_effects = {
    CLEAR: {"移动": 1.0, "视野": 1.0, "命中": 1.0},
    RAIN: {"移动": 0.8, "视野": 0.9, "命中": 0.9},
    FOG: {"移动": 1.0, "视野": 0.5, "命中": 0.8},
    SNOW: {"移动": 0.7, "视野": 0.8, "命中": 0.85}
}

# 经验元组
Experience = namedtuple('Experience', 
                        ['state', 'action', 'reward', 'next_state', 'done', 'unit_mask'])

class Unit:
    def __init__(self, unit_type, team, x, y, unit_id):
        self.unit_type = unit_type
        self.team = team  # 0: 蓝方, 1: 红方
        self.x = x
        self.y = y
        self.id = unit_id
        
        stats = unit_stats[unit_type]
        self.attack = stats[0]
        self.defense = stats[1]
        self.max_movement = stats[2]
        self.vision = stats[3]
        self.attack_range = stats[4]
        self.ability = stats[5]
        
        self.health = 100
        self.movement_left = self.max_movement
        self.has_acted = False
        self.is_selected = False
        self.special_used = False
        self.command_bonus = False  # 是否在指挥官范围内
        
    def reset_turn(self):
        self.movement_left = self.max_movement
        self.has_acted = False
        self.special_used = False
        self.command_bonus = False
        
    def move(self, new_x, new_y, terrain_cost, weather_factor):
        cost = terrain_cost * weather_factor
        if self.movement_left >= cost:
            self.x = new_x
            self.y = new_y
            self.movement_left -= cost
            return True
        return False
        
    def attack_unit(self, target, weather_factor):
        # 计算攻击效果
        base_attack = self.attack
        if "冲锋" in self.ability and not self.special_used:
            base_attack += 2
        
        if self.command_bonus:
            base_attack += 1
            
        defense = target.defense
        if target.command_bonus:
            defense += 1
            
        # 地形防御加成
        defense += terrain_defense_bonus.get(self.battlefield.terrain[target.x][target.y], 0)
        
        # 天气影响
        hit_chance = random.random()
        if hit_chance > weather_factor:
            return 0  # 攻击未命中
        
        damage = max(1, int(base_attack - defense / 2))
        target.health -= damage
        return damage
        
    def can_attack(self, target_x, target_y):
        distance = max(abs(self.x - target_x), abs(self.y - target_y))
        return distance <= self.attack_range
        
    def use_special_ability(self, target=None):
        if self.special_used or self.has_acted:
            return False, "无法使用技能"
            
        ability_cost = ABILITY_COST.get(self.ability.split('(')[0], 0)
        if ability_cost > self.movement_left:
            return False, "移动力不足"
            
        success = False
        message = ""
        
        if "治疗" in self.ability and target:
            if self.team == target.team and max(abs(self.x - target.x), abs(self.y - target.y)) <= 1:
                target.health = min(100, target.health + 20)
                success = True
                message = f"治疗了 {unit_names[target.unit_type]}"
                
        elif "建造" in self.ability:
            # 检查周围是否有水域或山地
            for dx, dy in [(0,1), (1,0), (0,-1), (-1,0)]:
                nx, ny = self.x + dx, self.y + dy
                if 0 <= nx < self.battlefield.width and 0 <= ny < self.battlefield.height:
                    if self.battlefield.terrain[nx][ny] == WATER:
                        self.battlefield.terrain[nx][ny] = BRIDGE
                        success = True
                        message = "建造了桥梁"
                        break
                    elif self.battlefield.terrain[nx][ny] == MOUNTAIN:
                        self.battlefield.terrain[nx][ny] = ROAD
                        success = True
                        message = "修建了道路"
                        break
        
        if success:
            self.special_used = True
            self.movement_left -= ability_cost
            self.has_acted = True
            
        return success, message
        
    def draw(self, painter, camera_x, camera_y, grid_size):
        screen_x = (self.x - camera_x) * grid_size + grid_size // 2
        screen_y = (self.y - camera_y) * grid_size + grid_size // 2
        
        # 绘制单位
        color = unit_colors[self.unit_type] if self.team == 0 else QColor(
            min(255, unit_colors[self.unit_type].red() + 100), 
            min(255, unit_colors[self.unit_type].green() + 30),
            min(255, unit_colors[self.unit_type].blue() + 30)
        )
        
        painter.setBrush(color)
        painter.setPen(QPen(BLACK, 1))
        
        # 指挥官有特殊标识
        if self.unit_type == COMMANDER:
            points = [
                (screen_x, screen_y - grid_size//3),
                (screen_x + grid_size//3, screen_y + grid_size//3),
                (screen_x - grid_size//3, screen_y + grid_size//3)
            ]
            painter.drawPolygon(*[QPointF(x, y) for x, y in points])
        else:
            painter.drawEllipse(screen_x - grid_size//3, screen_y - grid_size//3, 
                               grid_size*2//3, grid_size*2//3)
        
        # 绘制单位类型标识
        type_symbol = ["I", "C", "A", "T", "S", "M", "E", "CMD"][self.unit_type]
        font = QFont()
        font.setPointSize(8)
        painter.setFont(font)
        painter.drawText(screen_x - 5, screen_y - 8, 10, 10, Qt.AlignmentFlag.AlignCenter, type_symbol)
        
        # 绘制生命条
        bar_width = grid_size // 2
        bar_height = 4
        painter.setBrush(RED)
        painter.drawRect(screen_x - bar_width // 2, screen_y - grid_size // 2 - 5, bar_width, bar_height)
        painter.setBrush(GREEN)
        painter.drawRect(screen_x - bar_width // 2, screen_y - grid_size // 2 - 5, 
                        bar_width * self.health // 100, bar_height)
        
        # 如果被选中，绘制高亮圆圈
        if self.is_selected:
            painter.setPen(QPen(YELLOW, 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(screen_x - grid_size//2 - 2, screen_y - grid_size//2 - 2, 
                              grid_size + 4, grid_size + 4)
        
        # 如果有指挥加成，绘制光环
        if self.command_bonus:
            painter.setPen(QPen(CYAN, 1))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(screen_x - grid_size//2 - 5, screen_y - grid_size//2 - 5, 
                              grid_size + 10, grid_size + 10)


class Battlefield:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.terrain = np.zeros((width, height), dtype=int)
        self.generate_terrain()
        
        self.blue_units = []
        self.red_units = []
        self.all_units = []
        self.deploy_units()
        
        self.current_turn = 0  # 0: 蓝方回合, 1: 红方回合
        self.selected_unit = None
        self.camera_x = width // 2
        self.camera_y = height // 2
        self.game_over = False
        self.winner = None
        self.weather = CLEAR
        self.weather_timer = random.randint(20, 40)  # 天气持续时间
        self.turn_count = 0
        self.objectives = self.generate_objectives()
        
    def generate_terrain(self):
        # 生成随机地形
        for x in range(self.width):
            for y in range(self.height):
                # 基于噪声生成地形
                noise = random.random()
                if noise < 0.05:
                    self.terrain[x, y] = MOUNTAIN
                elif noise < 0.15:
                    self.terrain[x, y] = FOREST
                elif noise < 0.25:
                    self.terrain[x, y] = HILL
                elif noise < 0.30:
                    self.terrain[x, y] = WATER
                elif noise < 0.35:
                    self.terrain[x, y] = ROAD
                else:
                    self.terrain[x, y] = PLAIN
                    
        # 添加一条河流
        river_y = random.randint(5, self.height - 5)
        for x in range(self.width):
            for dy in range(-1, 2):
                if 0 <= river_y + dy < self.height:
                    self.terrain[x, river_y + dy] = WATER
                    
        # 添加城市
        for _ in range(3):
            city_x = random.randint(10, self.width - 10)
            city_y = random.randint(10, self.height - 10)
            for dx in range(-2, 3):
                for dy in range(-2, 3):
                    if 0 <= city_x + dx < self.width and 0 <= city_y + dy < self.height:
                        if abs(dx) < 2 and abs(dy) < 2:
                            self.terrain[city_x + dx, city_y + dy] = CITY
                        else:
                            self.terrain[city_x + dx, city_y + dy] = ROAD
        
    def deploy_units(self):
        # 部署蓝方单位（左侧）
        unit_id = 0
                # 修复部署蓝方单位的代码部分
        for i in range(4):
            self.blue_units.append(Unit(INFANTRY, 0, 2, 5 + i * 3, unit_id))
            unit_id += 1
        for i in range(3):
            self.blue_units.append(Unit(CAVALRY, 0, 1, 6 + i * 4, unit_id))
            unit_id += 1
        for i in range(3):
            self.blue_units.append(Unit(ARCHER, 0, 3, 5 + i * 5, unit_id))
            unit_id += 1
        self.blue_units.append(Unit(ARTILLERY, 0, 2, 10, unit_id))
        unit_id += 1
        self.blue_units.append(Unit(SCOUT, 0, 0, 8, unit_id))
        unit_id += 1
        self.blue_units.append(Unit(MEDIC, 0, 4, 7, unit_id))
        unit_id += 1
        self.blue_units.append(Unit(ENGINEER, 0, 1, 10, unit_id))
        unit_id += 1
        self.blue_units.append(Unit(COMMANDER, 0, 3, 8, unit_id))
        unit_id += 1

        # 修复部署红方单位的代码部分
        for i in range(4):
            self.red_units.append(Unit(INFANTRY, 1, self.width - 3, 5 + i * 3, unit_id))
            unit_id += 1
        for i in range(3):
            self.red_units.append(Unit(CAVALRY, 1, self.width - 2, 6 + i * 4, unit_id))
            unit_id += 1
        for i in range(3):
            self.red_units.append(Unit(ARCHER, 1, self.width - 4, 5 + i * 5, unit_id))
            unit_id += 1
        self.red_units.append(Unit(ARTILLERY, 1, self.width - 3, 10, unit_id))
        unit_id += 1
        self.red_units.append(Unit(SCOUT, 1, self.width - 1, 8, unit_id))
        unit_id += 1
        self.red_units.append(Unit(MEDIC, 1, self.width - 5, 7, unit_id))
        unit_id += 1
        self.red_units.append(Unit(ENGINEER, 1, self.width - 2, 10, unit_id))
        unit_id += 1
        self.red_units.append(Unit(COMMANDER, 1, self.width - 4, 8, unit_id))
        unit_id += 1
        
        self.all_units = self.blue_units + self.red_units
        
        # 设置战场引用
        for unit in self.all_units:
            unit.battlefield = self
    
    def generate_objectives(self):
        """生成战略目标"""
        objectives = []
        
        # 控制点
        for _ in range(3):
            x = random.randint(10, self.width - 10)
            y = random.randint(10, self.height - 10)
            objectives.append({
                "type": "control_point",
                "x": x,
                "y": y,
                "controlled_by": None,
                "value": 5  # 每回合得分
            })
            
        # 资源点
        for _ in range(2):
            x = random.randint(5, self.width - 5)
            y = random.randint(5, self.height - 5)
            objectives.append({
                "type": "resource",
                "x": x,
                "y": y,
                "controlled_by": None,
                "value": 2  # 每回合资源
            })
            
        return objectives
    
    def update_weather(self):
        """更新天气状态"""
        self.weather_timer -= 1
        if self.weather_timer <= 0:
            self.weather = random.choice(list(weather_effects.keys()))
            self.weather_timer = random.randint(15, 30)
    
    def update_command_bonus(self):
        """更新指挥官加成效果"""
        # 重置所有加成
        for unit in self.all_units:
            unit.command_bonus = False
        
        # 为指挥官周围的单位应用加成
        for commander in [u for u in self.all_units if u.unit_type == COMMANDER]:
            for unit in self.all_units:
                if unit.team == commander.team:
                    distance = max(abs(commander.x - unit.x), abs(commander.y - unit.y))
                    if distance <= 3:  # 指挥范围
                        unit.command_bonus = True
    
    def reset_turn(self):
        self.current_turn = 1 - self.current_turn
        self.turn_count += 1
        self.update_weather()
        self.update_command_bonus()
        
        for unit in (self.blue_units if self.current_turn == 0 else self.red_units):
            unit.reset_turn()
        self.selected_unit = None
        
        # 更新控制点
        for obj in self.objectives:
            if obj["type"] == "control_point":
                blue_units_near = 0
                red_units_near = 0
                
                # 检查控制点周围的单位
                for unit in self.all_units:
                    distance = max(abs(unit.x - obj["x"]), abs(unit.y - obj["y"]))
                    if distance <= 2:
                        if unit.team == 0:
                            blue_units_near += 1
                        else:
                            red_units_near += 1
                
                # 确定控制权
                if blue_units_near > red_units_near * 1.5:
                    obj["controlled_by"] = 0
                elif red_units_near > blue_units_near * 1.5:
                    obj["controlled_by"] = 1
                else:
                    obj["controlled_by"] = None
        
    def select_unit(self, x, y):
        # 取消所有单位的选择
        for unit in self.all_units:
            unit.is_selected = False
            
        # 尝试选择新单位
        for unit in (self.blue_units if self.current_turn == 0 else self.red_units):
            if unit.x == x and unit.y == y and not unit.has_acted:
                unit.is_selected = True
                self.selected_unit = unit
                return True
        return False
        
    def move_unit(self, x, y):
        if self.selected_unit is None:
            return False
            
        # 检查目标位置是否有效
        if not (0 <= x < self.width and 0 <= y < self.height):
            return False
            
        # 检查目标位置是否被其他单位占据
        for unit in self.all_units:
            if unit.x == x and unit.y == y:
                return False
                
        # 计算移动消耗
        terrain_type = self.terrain[x, y]
        base_cost = terrain_movement_cost[terrain_type]
        weather_factor = weather_effects[self.weather]["移动"]
        
        # 尝试移动
        if self.selected_unit.move(x, y, base_cost, weather_factor):
            return True
        return False
        
    def attack(self, target_x, target_y):
        if self.selected_unit is None:
            return False, 0
            
        # 查找目标单位
        target_unit = None
        for unit in (self.red_units if self.current_turn == 0 else self.blue_units):
            if unit.x == target_x and unit.y == target_y:
                target_unit = unit
                break
                
        if target_unit is None:
            return False, 0
            
        # 检查是否可以攻击
        if not self.selected_unit.can_attack(target_x, target_y):
            return False, 0
            
        # 天气影响
        weather_factor = weather_effects[self.weather]["命中"]
        
        # 执行攻击
        damage = self.selected_unit.attack_unit(target_unit, weather_factor)
        self.selected_unit.has_acted = True
        
        if damage > 0:
            # 检查目标是否被消灭
            if target_unit.health <= 0:
                if target_unit in self.blue_units:
                    self.blue_units.remove(target_unit)
                else:
                    self.red_units.remove(target_unit)
                self.all_units.remove(target_unit)
                
            # 检查游戏是否结束
            if len(self.blue_units) == 0:
                self.game_over = True
                self.winner = 1
            elif len(self.red_units) == 0:
                self.game_over = True
                self.winner = 0
                
        return True, damage
        
    def get_state(self, for_team=None):
        """获取当前战场状态（用于强化学习）"""
        # 状态包括地形、单位位置、单位状态等信息
        state = []
        
        # 地形信息
        for x in range(self.width):
            for y in range(self.height):
                terrain_type = self.terrain[x, y]
                # 编码为one-hot
                terrain_vec = [0] * 8
                terrain_vec[terrain_type] = 1
                state.extend(terrain_vec)
        
        # 单位信息
        for unit in self.all_units:
            unit_state = [
                unit.x / self.width,
                unit.y / self.height,
                unit.unit_type / 7.0,
                unit.team,
                unit.health / 100.0,
                unit.movement_left / unit.max_movement,
                int(unit.has_acted),
                int(unit.special_used),
                int(unit.command_bonus)
            ]
            state.extend(unit_state)
            
        # 天气信息
        weather_vec = [0] * 4
        weather_vec[self.weather] = 1
        state.extend(weather_vec)
        
        # 目标信息
        for obj in self.objectives:
            obj_state = [
                obj["x"] / self.width,
                obj["y"] / self.height,
                obj["controlled_by"] if obj["controlled_by"] is not None else -1,
                1 if obj["type"] == "control_point" else 0,
                1 if obj["type"] == "resource" else 0
            ]
            state.extend(obj_state)
            
        # 当前回合信息
        state.append(self.current_turn)
        
        # 转换为numpy数组
        state = np.array(state, dtype=np.float32)
        
        # 如果指定队伍，过滤不可见信息（战争迷雾）
        if for_team is not None:
            # 创建可见性掩码
            visibility = np.zeros((self.width, self.height), dtype=bool)
            
            # 添加己方单位视野
            for unit in (self.blue_units if for_team == 0 else self.red_units):
                for dx in range(-unit.vision, unit.vision + 1):
                    for dy in range(-unit.vision, unit.vision + 1):
                        nx, ny = unit.x + dx, unit.y + dy
                        if 0 <= nx < self.width and 0 <= ny < self.height:
                            if abs(dx) <= unit.vision and abs(dy) <= unit.vision:
                                visibility[nx, ny] = True
            
            # 应用战争迷雾
            # 这里简化处理：实际应用中需要修改状态向量
            # 本实现中在智能体层面处理战争迷雾
            
        return state
        
    def get_valid_actions(self, unit):
        """获取指定单位的有效动作"""
        valid_actions = []
        
        # 移动动作 (8个方向)
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                if dx == 0 and dy == 0:
                    continue
                    
                new_x, new_y = unit.x + dx, unit.y + dy
                if 0 <= new_x < self.width and 0 <= new_y < self.height:
                    # 检查位置是否被占据
                    occupied = False
                    for other in self.all_units:
                        if other.x == new_x and other.y == new_y:
                            occupied = True
                            break
                            
                    if not occupied:
                        terrain_type = self.terrain[new_x, new_y]
                        base_cost = terrain_movement_cost[terrain_type]
                        weather_factor = weather_effects[self.weather]["移动"]
                        cost = base_cost * weather_factor
                        if unit.movement_left >= cost:
                            valid_actions.append(("move", new_x, new_y))
        
        # 攻击动作 (周围单位)
        for target in (self.red_units if unit.team == 0 else self.blue_units):
            if unit.can_attack(target.x, target.y):
                valid_actions.append(("attack", target.x, target.y))
                
        # 特殊能力
        if not unit.special_used:
            if "治疗" in unit.ability:
                # 可以治疗周围友军
                for ally in (self.blue_units if unit.team == 0 else self.red_units):
                    if ally != unit and ally.health < 100:
                        distance = max(abs(unit.x - ally.x), abs(unit.y - ally.y))
                        if distance <= 1:
                            valid_actions.append(("heal", ally.x, ally.y))
                            
            if "建造" in unit.ability:
                # 可以建造桥梁或道路
                for dx, dy in [(0,1), (1,0), (0,-1), (-1,0)]:
                    nx, ny = unit.x + dx, unit.y + dy
                    if 0 <= nx < self.width and 0 <= ny < self.height:
                        if self.terrain[nx][ny] == WATER:
                            valid_actions.append(("build_bridge", nx, ny))
                        elif self.terrain[nx][ny] == MOUNTAIN:
                            valid_actions.append(("build_road", nx, ny))
        
        # 待机动作
        valid_actions.append(("wait", None, None))
        
        return valid_actions


class Actor(nn.Module):
    """Actor网络 - 策略网络"""
    def __init__(self, state_size, action_size, hidden_size=256):
        super(Actor, self).__init__()
        self.fc1 = nn.Linear(state_size, hidden_size)
        self.fc2 = nn.Linear(hidden_size, hidden_size)
        self.fc3 = nn.Linear(hidden_size, action_size)
        
    def forward(self, state):
        x = torch.relu(self.fc1(state))
        x = torch.relu(self.fc2(x))
        x = torch.tanh(self.fc3(x))  # 输出在[-1,1]范围内
        return x


class Critic(nn.Module):
    """Critic网络 - 价值网络"""
    def __init__(self, state_size, action_size, hidden_size=256):
        super(Critic, self).__init__()
        self.fc1 = nn.Linear(state_size + action_size, hidden_size)
        self.fc2 = nn.Linear(hidden_size, hidden_size)
        self.fc3 = nn.Linear(hidden_size, 1)
        
    def forward(self, state, action):
        x = torch.cat([state, action], dim=1)
        x = torch.relu(self.fc1(x))
        x = torch.relu(self.fc2(x))
        return self.fc3(x)


class MADDPGAgent:
    """多智能体DDPG智能体"""
    def __init__(self, state_size, action_size, num_agents, agent_id):
        self.state_size = state_size
        self.action_size = action_size
        self.num_agents = num_agents
        self.agent_id = agent_id
        self.epsilon = EPSILON_START
        
        # 设备配置
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        # 创建Actor和Critic网络
        self.actor = Actor(state_size, action_size).to(self.device)
        self.actor_target = Actor(state_size, action_size).to(self.device)
        self.actor_target.load_state_dict(self.actor.state_dict())
        
        self.critic = Critic(state_size * num_agents, action_size * num_agents).to(self.device)
        self.critic_target = Critic(state_size * num_agents, action_size * num_agents).to(self.device)
        self.critic_target.load_state_dict(self.critic.state_dict())
        
        # 优化器
        self.actor_optimizer = optim.Adam(self.actor.parameters(), lr=LR_ACTOR)
        self.critic_optimizer = optim.Adam(self.critic.parameters(), lr=LR_CRITIC)
        
        # 记忆回放
        self.memory = deque(maxlen=MEMORY_CAPACITY)
        
        # 状态归一化
        self.scaler = StandardScaler()
        self.scaler_fitted = False
        
    def select_action(self, state, valid_actions=None):
        """选择动作"""
        state = self.scale_state(state)
        state = torch.FloatTensor(state).unsqueeze(0).to(self.device)
        
        # 使用Actor网络获取动作
        with torch.no_grad():
            action = self.actor(state).cpu().data.numpy().flatten()
            
        # 添加探索噪声
        if self.epsilon > EPSILON_END:
            noise = np.random.normal(0, self.epsilon, size=self.action_size)
            action = (action + noise).clip(-1, 1)
            
        # 如果有有效动作限制，映射到有效动作
        if valid_actions:
            # 这里简化处理，实际应用中需要更复杂的映射
            action = self.map_to_valid_action(action, valid_actions)
            
        return action
        
    def map_to_valid_action(self, action, valid_actions):
        """将连续动作映射到离散的有效动作"""
        # 这里简化处理：选择最接近的有效动作
        best_action = None
        min_dist = float('inf')
        
        for va in valid_actions:
            # 简化：假设动作是二维的 (dx, dy)
            if va[0] == "move":
                dx = va[1] - self.current_x
                dy = va[2] - self.current_y
                dist = np.linalg.norm(action - [dx, dy])
                if dist < min_dist:
                    min_dist = dist
                    best_action = va
            # 其他动作类型处理...
            
        return best_action if best_action else ("wait", None, None)
        
    def remember(self, state, action, reward, next_state, done):
        """存储经验"""
        self.memory.append(Experience(state, action, reward, next_state, done))
        
    def learn(self, agents):
        """从经验中学习"""
        if len(self.memory) < BATCH_SIZE:
            return
            
        # 采样批次
        experiences = random.sample(self.memory, BATCH_SIZE)
        batch = Experience(*zip(*experiences))
        
        # 转换为张量
        states = torch.FloatTensor(batch.state).to(self.device)
        actions = torch.FloatTensor(batch.action).to(self.device)
        rewards = torch.FloatTensor(batch.reward).unsqueeze(1).to(self.device)
        next_states = torch.FloatTensor(batch.next_state).to(self.device)
        dones = torch.FloatTensor(batch.done).unsqueeze(1).to(self.device)
        
        # 训练Critic网络
        next_actions = torch.cat([agents[i].actor_target(next_states) for i in range(self.num_agents)], dim=1)
        q_targets_next = self.critic_target(next_states.view(BATCH_SIZE, -1), next_actions)
        q_targets = rewards + (GAMMA * q_targets_next * (1 - dones))
        
        q_expected = self.critic(states.view(BATCH_SIZE, -1), actions)
        critic_loss = nn.MSELoss()(q_expected, q_targets.detach())
        
        self.critic_optimizer.zero_grad()
        critic_loss.backward()
        torch.nn.utils.clip_grad_norm_(self.critic.parameters(), CLIP_GRAD)
        self.critic_optimizer.step()
        
        # 训练Actor网络
        actions_pred = [agents[i].actor(states) if i == self.agent_id else agents[i].actor(states).detach() 
                      for i in range(self.num_agents)]
        actions_pred = torch.cat(actions_pred, dim=1)
        
        actor_loss = -self.critic(states.view(BATCH_SIZE, -1), actions_pred).mean()
        
        self.actor_optimizer.zero_grad()
        actor_loss.backward()
        torch.nn.utils.clip_grad_norm_(self.actor.parameters(), CLIP_GRAD)
        self.actor_optimizer.step()
        
        # 更新目标网络
        self.soft_update(self.actor, self.actor_target, TAU)
        self.soft_update(self.critic, self.critic_target, TAU)
        
        # 更新epsilon
        self.epsilon = max(EPSILON_END, self.epsilon * EPSILON_DECAY)
        
        return critic_loss.item(), actor_loss.item()
        
    def soft_update(self, local_model, target_model, tau):
        """软更新模型参数"""
        for target_param, local_param in zip(target_model.parameters(), local_model.parameters()):
            target_param.data.copy_(tau * local_param.data + (1.0 - tau) * target_param.data)
            
    def scale_state(self, state):
        """标准化状态"""
        if not self.scaler_fitted:
            self.scaler.partial_fit([state])
            self.scaler_fitted = True
        return self.scaler.transform([state])[0]
    
    def save_model(self, path):
        """保存模型"""
        torch.save({
            'actor_state_dict': self.actor.state_dict(),
            'critic_state_dict': self.critic.state_dict(),
            'actor_optimizer_state_dict': self.actor_optimizer.state_dict(),
            'critic_optimizer_state_dict': self.critic_optimizer.state_dict(),
            'scaler': self.scaler
        }, path)
        
    def load_model(self, path):
        """加载模型"""
        checkpoint = torch.load(path)
        self.actor.load_state_dict(checkpoint['actor_state_dict'])
        self.critic.load_state_dict(checkpoint['critic_state_dict'])
        self.actor_optimizer.load_state_dict(checkpoint['actor_optimizer_state_dict'])
        self.critic_optimizer.load_state_dict(checkpoint['critic_optimizer_state_dict'])
        self.scaler = checkpoint['scaler']


class StrategicAgent:
    """战略级智能体（指挥官）"""
    def __init__(self, state_size, action_size):
        self.state_size = state_size
        self.action_size = action_size
        self.model = self.build_model()
        self.memory = deque(maxlen=10000)
        
    def build_model(self):
        """构建战略决策模型"""
        model = nn.Sequential(
            nn.Linear(self.state_size, 256),
            nn.ReLU(),
            nn.Linear(256, 256),
            nn.ReLU(),
            nn.Linear(256, self.action_size))
        return model
    
    def select_strategy(self, state):
        """选择战略"""
        state_tensor = torch.FloatTensor(state).unsqueeze(0)
        with torch.no_grad():
            strategy = self.model(state_tensor).numpy().flatten()
        return strategy
    
    def learn(self, states, actions, rewards):
        """学习战略决策"""
        # 这里简化处理，实际应用中需要更复杂的训练过程
        pass


class BattlefieldWidget(QWidget):
    """战场可视化组件"""
    unitSelected = pyqtSignal(int, int)
    cellClicked = pyqtSignal(int, int)
    rightClicked = pyqtSignal(int, int)
    
    def __init__(self, battlefield, parent=None):
        super().__init__(parent)
        self.battlefield = battlefield
        self.grid_size = GRID_SIZE
        self.camera_x = battlefield.camera_x
        self.camera_y = battlefield.camera_y
        self.show_fog_of_war = True
        self.visualize_strategy = True
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 绘制背景
        painter.fillRect(self.rect(), BLACK)
        
        # 计算可见区域
        width = self.width()
        height = self.height()
        center_x = width // 2
        center_y = height // 2
        
        # 绘制地形
        for x in range(self.battlefield.width):
            for y in range(self.battlefield.height):
                screen_x = (x - self.camera_x) * self.grid_size + center_x
                screen_y = (y - self.camera_y) * self.grid_size + center_y
                
                if not (0 <= screen_x < width and 0 <= screen_y < height):
                    continue
                
                # 绘制地形格子
                terrain_type = self.battlefield.terrain[x, y]
                painter.setBrush(terrain_colors[terrain_type])
                painter.setPen(QPen(BLACK, 1))
                painter.drawRect(screen_x, screen_y, self.grid_size, self.grid_size)
                
                # 显示特殊地形符号
                if terrain_type in [CITY, BRIDGE]:
                    symbol = "C" if terrain_type == CITY else "B"
                    font = QFont()
                    font.setPointSize(8)
                    painter.setFont(font)
                    painter.drawText(screen_x + 5, screen_y + 5, 10, 10, 
                                    Qt.AlignmentFlag.AlignCenter, symbol)
        
        # 绘制战略目标
        for obj in self.battlefield.objectives:
            screen_x = (obj["x"] - self.camera_x) * self.grid_size + center_x
            screen_y = (obj["y"] - self.camera_y) * self.grid_size + center_y
            
            color = BLUE if obj.get("controlled_by", None) == 0 else RED if obj.get("controlled_by", None) == 1 else WHITE
            
            if obj["type"] == "control_point":
                painter.setPen(QPen(color, 2))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawEllipse(screen_x - self.grid_size//3, screen_y - self.grid_size//3, 
                                  self.grid_size*2//3, self.grid_size*2//3)
                font = QFont()
                font.setPointSize(8)
                painter.setFont(font)
                painter.drawText(screen_x - 8, screen_y - 8, 16, 16, 
                                Qt.AlignmentFlag.AlignCenter, "CP")
            elif obj["type"] == "resource":
                painter.setPen(QPen(color, 2))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawRect(screen_x - self.grid_size//4, screen_y - self.grid_size//4, 
                               self.grid_size//2, self.grid_size//2)
                font = QFont()
                font.setPointSize(8)
                painter.setFont(font)
                painter.drawText(screen_x - 4, screen_y - 8, 8, 16, 
                                Qt.AlignmentFlag.AlignCenter, "R")
        
        # 绘制单位
        for unit in self.battlefield.all_units:
            # 战争迷雾处理
            if self.show_fog_of_war:
                visible = False
                for friendly in (self.battlefield.blue_units if unit.team == 0 else self.battlefield.red_units):
                    distance = max(abs(friendly.x - unit.x), abs(friendly.y - unit.y))
                    if distance <= friendly.vision:
                        visible = True
                        break
                if not visible and unit.team == 1:  # 红方单位在战争迷雾中
                    continue
                    
            unit.draw(painter, self.camera_x, self.camera_y, self.grid_size)
        
        # 绘制战略可视化
        if self.visualize_strategy and self.battlefield.current_turn == 1:
            # 获取战略决策
            state = self.battlefield.get_state()
            # 这里简化处理，实际应该使用战略智能体
            strategy_name = "进攻"  # 默认策略
            
            # 绘制战略名称
            font = QFont()
            font.setPointSize(12)
            painter.setFont(font)
            painter.setPen(RED)
            painter.drawText(10, 30, 200, 20, Qt.AlignmentFlag.AlignLeft, f"红方战略: {strategy_name}")
            
            # 根据战略绘制可视化元素
            if "进攻" in strategy_name:
                # 绘制进攻箭头
                for unit in self.battlefield.red_units:
                    if unit.unit_type != COMMANDER:
                        start_x = (unit.x - self.camera_x) * self.grid_size + center_x
                        start_y = (unit.y - self.camera_y) * self.grid_size + center_y
                        end_x = start_x + (self.battlefield.width//2 - unit.x) * 2
                        end_y = start_y
                        
                        painter.setPen(QPen(RED, 2))
                        painter.drawLine(start_x, start_y, end_x, end_y)
                        # 绘制箭头
                        painter.drawPolygon(
                            QPointF(end_x, end_y),
                            QPointF(end_x - 10, end_y - 5),
                            QPointF(end_x - 10, end_y + 5)
                        )
        
        # 绘制天气效果
        if self.battlefield.weather == RAIN:
            painter.setPen(QPen(QColor(100, 100, 255, 150), 1))
            for _ in range(50):
                x = random.randint(0, width)
                y = random.randint(0, height)
                painter.drawLine(x, y, x, y+10)
        elif self.battlefield.weather == FOG:
            painter.fillRect(self.rect(), QColor(200, 200, 200, 80))
        elif self.battlefield.weather == SNOW:
            painter.setPen(QPen(WHITE, 2))
            for _ in range(100):
                x = random.randint(0, width)
                y = random.randint(0, height)
                painter.drawPoint(x, y)
        
        # 绘制网格线
        painter.setPen(QPen(GRAY, 1, Qt.PenStyle.DotLine))
        for x in range(self.battlefield.width):
            screen_x = (x - self.camera_x) * self.grid_size + center_x
            if 0 <= screen_x < width:
                painter.drawLine(screen_x, 0, screen_x, height)
        
        for y in range(self.battlefield.height):
            screen_y = (y - self.camera_y) * self.grid_size + center_y
            if 0 <= screen_y < height:
                painter.drawLine(0, screen_y, width, screen_y)
    
    def mousePressEvent(self, event):
        center_x = self.width() // 2
        center_y = self.height() // 2
        
        grid_x = self.camera_x + (event.position().x() - center_x) // self.grid_size
        grid_y = self.camera_y + (event.position().y() - center_y) // self.grid_size
        
        if event.button() == Qt.MouseButton.LeftButton:
            self.cellClicked.emit(grid_x, grid_y)
        elif event.button() == Qt.MouseButton.RightButton:
            self.rightClicked.emit(grid_x, grid_y)
    
    def wheelEvent(self, event):
        # 滚轮缩放
        delta = event.angleDelta().y() / 120
        self.grid_size = max(10, min(40, self.grid_size + delta))
        self.update()
    
    def keyPressEvent(self, event):
        # 键盘控制摄像头移动
        if event.key() == Qt.Key.Key_Up:
            self.camera_y -= 1
        elif event.key() == Qt.Key.Key_Down:
            self.camera_y += 1
        elif event.key() == Qt.Key.Key_Left:
            self.camera_x -= 1
        elif event.key() == Qt.Key.Key_Right:
            self.camera_x += 1
        self.update()


class BattleSimulation(QMainWindow):
    """战场模拟主窗口"""
    def __init__(self):
        super().__init__()
        self.battlefield = Battlefield(TERRAIN_SIZE, TERRAIN_SIZE)
        
        # 创建强化学习智能体（红方）
        state_size = self.battlefield.get_state().shape[0]
        action_size = 2  # 简化动作空间 (dx, dy)
        num_agents = len(self.battlefield.red_units)
        
        self.agents = []
        for i in range(num_agents):
            self.agents.append(MADDPGAgent(state_size, action_size, num_agents, i))
        
        # 战略级智能体
        strategic_state_size = state_size
        strategic_action_size = 4  # 进攻、防御、侧翼包抄、占领目标
        self.strategic_agent = StrategicAgent(strategic_state_size, strategic_action_size)
        
        # 训练参数
        self.episode = 0
        self.max_episodes = 2000
        self.steps = 0
        self.total_rewards = []
        self.wins = 0
        self.losses = []
        
        # 可视化参数
        self.show_info = True
        self.auto_play = False
        self.training = True
        self.visualize_strategy = True
        self.show_fog_of_war = True
        
        self.initUI()
        self.initTimer()
        
    def initUI(self):
        self.setWindowTitle("强化学习军争模拟系统 - 增强版")
        self.setGeometry(100, 100, 1400, 900)
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QHBoxLayout(central_widget)
        
        # 左侧控制面板
        control_panel = QTabWidget()
        control_panel.setMaximumWidth(300)
        
        # 游戏控制选项卡
        game_tab = QWidget()
        game_layout = QVBoxLayout(game_tab)
        
        # 游戏状态组
        status_group = QGroupBox("游戏状态")
        status_layout = QVBoxLayout(status_group)
        
        self.turn_label = QLabel("蓝方回合")
        self.turn_label.setStyleSheet("font-weight: bold; color: blue;")
        status_layout.addWidget(self.turn_label)
        
        self.unit_count_label = QLabel("蓝方单位: 12  红方单位: 12")
        status_layout.addWidget(self.unit_count_label)
        
        self.weather_label = QLabel("天气: 晴 (移动:100% 视野:100% 命中:100%)")
        status_layout.addWidget(self.weather_label)
        
        game_layout.addWidget(status_group)
        
        # 训练控制组
        training_group = QGroupBox("训练控制")
        training_layout = QVBoxLayout(training_group)
        
        self.training_checkbox = QCheckBox("训练模式")
        self.training_checkbox.setChecked(True)
        self.training_checkbox.stateChanged.connect(self.toggleTraining)
        training_layout.addWidget(self.training_checkbox)
        
        self.episode_label = QLabel("训练回合: 0/2000")
        training_layout.addWidget(self.episode_label)
        
        self.win_rate_label = QLabel("胜率: 0.0%")
        training_layout.addWidget(self.win_rate_label)
        
        self.epsilon_label = QLabel("探索率: 1.000")
        training_layout.addWidget(self.epsilon_label)
        
        training_controls = QHBoxLayout()
        self.start_button = QPushButton("开始训练")
        self.start_button.clicked.connect(self.startTraining)
        training_controls.addWidget(self.start_button)
        
        self.pause_button = QPushButton("暂停")
        self.pause_button.clicked.connect(self.pauseTraining)
        training_controls.addWidget(self.pause_button)
        
        training_layout.addLayout(training_controls)
        
        game_layout.addWidget(training_group)
        
        # 可视化选项组
        visual_group = QGroupBox("可视化选项")
        visual_layout = QVBoxLayout(visual_group)
        
        self.fog_checkbox = QCheckBox("战争迷雾")
        self.fog_checkbox.setChecked(True)
        self.fog_checkbox.stateChanged.connect(self.toggleFogOfWar)
        visual_layout.addWidget(self.fog_checkbox)
        
        self.strategy_checkbox = QCheckBox("战略可视化")
        self.strategy_checkbox.setChecked(True)
        self.strategy_checkbox.stateChanged.connect(self.toggleStrategyVisualization)
        visual_layout.addWidget(self.strategy_checkbox)
        
        self.info_checkbox = QCheckBox("显示信息")
        self.info_checkbox.setChecked(True)
        self.info_checkbox.stateChanged.connect(self.toggleInfoDisplay)
        visual_layout.addWidget(self.info_checkbox)
        
        self.auto_checkbox = QCheckBox("自动播放")
        self.auto_checkbox.stateChanged.connect(self.toggleAutoPlay)
        visual_layout.addWidget(self.auto_checkbox)
        
        game_layout.addWidget(visual_group)
        
        # 单位信息组
        unit_group = QGroupBox("单位信息")
        unit_layout = QVBoxLayout(unit_group)
        
        self.unit_info_label = QLabel("选择单位查看详情")
        self.unit_info_label.setWordWrap(True)
        unit_layout.addWidget(self.unit_info_label)
        
        game_layout.addWidget(unit_group)
        
        game_layout.addStretch()
        
        # 动作按钮
        action_layout = QHBoxLayout()
        self.end_turn_button = QPushButton("结束回合")
        self.end_turn_button.clicked.connect(self.endTurn)
        action_layout.addWidget(self.end_turn_button)
        
        self.reset_button = QPushButton("重置游戏")
        self.reset_button.clicked.connect(self.resetGame)
        action_layout.addWidget(self.reset_button)
        
        game_layout.addLayout(action_layout)
        
        control_panel.addTab(game_tab, "游戏控制")
        
        # 智能体配置选项卡
        agent_tab = QWidget()
        agent_layout = QVBoxLayout(agent_tab)
        
        # 强化学习参数组
        rl_group = QGroupBox("强化学习参数")
        rl_layout = QGridLayout(rl_group)
        
        rl_layout.addWidget(QLabel("学习率 (Actor):"), 0, 0)
        self.actor_lr_spin = QDoubleSpinBox()
        self.actor_lr_spin.setRange(0.00001, 0.01)
        self.actor_lr_spin.setValue(LR_ACTOR)
        self.actor_lr_spin.setDecimals(5)
        rl_layout.addWidget(self.actor_lr_spin, 0, 1)
        
        rl_layout.addWidget(QLabel("学习率 (Critic):"), 1, 0)
        self.critic_lr_spin = QDoubleSpinBox()
        self.critic_lr_spin.setRange(0.0001, 0.1)
        self.critic_lr_spin.setValue(LR_CRITIC)
        self.critic_lr_spin.setDecimals(4)
        rl_layout.addWidget(self.critic_lr_spin, 1, 1)
        
        rl_layout.addWidget(QLabel("折扣因子:"), 2, 0)
        self.gamma_spin = QDoubleSpinBox()
        self.gamma_spin.setRange(0.1, 0.99)
        self.gamma_spin.setValue(GAMMA)
        self.gamma_spin.setSingleStep(0.01)
        rl_layout.addWidget(self.gamma_spin, 2, 1)
        
        rl_layout.addWidget(QLabel("探索率衰减:"), 3, 0)
        self.epsilon_decay_spin = QDoubleSpinBox()
        self.epsilon_decay_spin.setRange(0.9, 0.9999)
        self.epsilon_decay_spin.setValue(EPSILON_DECAY)
        self.epsilon_decay_spin.setSingleStep(0.0001)
        rl_layout.addWidget(self.epsilon_decay_spin, 3, 1)
        
        rl_layout.addWidget(QLabel("批次大小:"), 4, 0)
        self.batch_size_spin = QSpinBox()
        self.batch_size_spin.setRange(32, 1024)
        self.batch_size_spin.setValue(BATCH_SIZE)
        rl_layout.addWidget(self.batch_size_spin, 4, 1)
        
        agent_layout.addWidget(rl_group)
        
        # 网络结构组
        network_group = QGroupBox("网络结构")
        network_layout = QGridLayout(network_group)
        
        network_layout.addWidget(QLabel("隐藏层大小:"), 0, 0)
        self.hidden_size_spin = QSpinBox()
        self.hidden_size_spin.setRange(64, 1024)
        self.hidden_size_spin.setValue(256)
        network_layout.addWidget(self.hidden_size_spin, 0, 1)
        
        agent_layout.addWidget(network_group)
        
        # 模型操作组
        model_group = QGroupBox("模型操作")
        model_layout = QVBoxLayout(model_group)
        
        model_buttons = QHBoxLayout()
        self.save_button = QPushButton("保存模型")
        self.save_button.clicked.connect(self.saveModel)
        model_buttons.addWidget(self.save_button)
        
        self.load_button = QPushButton("加载模型")
        self.load_button.clicked.connect(self.loadModel)
        model_buttons.addWidget(self.load_button)
        
        model_layout.addLayout(model_buttons)
        
        agent_layout.addWidget(model_group)
        
        agent_layout.addStretch()
        
        control_panel.addTab(agent_tab, "智能体配置")
        
        # 统计信息选项卡
        stats_tab = QWidget()
        stats_layout = QVBoxLayout(stats_tab)
        
        # 奖励图表
        self.reward_chart = QChart()
        self.reward_series = QLineSeries()
        self.reward_chart.addSeries(self.reward_series)
        self.reward_chart.createDefaultAxes()
        self.reward_chart.setTitle("奖励曲线")
        
        self.reward_chart_view = QChartView(self.reward_chart)
        self.reward_chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        stats_layout.addWidget(self.reward_chart_view)
        
        # 胜率图表
        self.win_rate_chart = QChart()
        self.win_rate_series = QLineSeries()
        self.win_rate_chart.addSeries(self.win_rate_series)
        self.win_rate_chart.createDefaultAxes()
        self.win_rate_chart.setTitle("胜率曲线")
        
        self.win_rate_chart_view = QChartView(self.win_rate_chart)
        self.win_rate_chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        stats_layout.addWidget(self.win_rate_chart_view)
        
        control_panel.addTab(stats_tab, "统计信息")
        
        main_layout.addWidget(control_panel)
        
        # 战场可视化
        self.battlefield_widget = BattlefieldWidget(self.battlefield)
        self.battlefield_widget.cellClicked.connect(self.handleCellClick)
        self.battlefield_widget.rightClicked.connect(self.handleRightClick)
        main_layout.addWidget(self.battlefield_widget, 1)
        
        # 创建状态栏
        self.statusBar().showMessage("就绪")
        
        # 创建工具栏
        toolbar = QToolBar("主工具栏")
        toolbar.setIconSize(QSize(16, 16))
        self.addToolBar(toolbar)
        
        # 工具栏动作
        play_action = QAction("开始", self)
        play_action.triggered.connect(self.startTraining)
        toolbar.addAction(play_action)
        
        pause_action = QAction("暂停", self)
        pause_action.triggered.connect(self.pauseTraining)
        toolbar.addAction(pause_action)
        
        toolbar.addSeparator()
        
        reset_action = QAction("重置", self)
        reset_action.triggered.connect(self.resetGame)
        toolbar.addAction(reset_action)
        
        # 更新初始状态显示
        self.updateStatusDisplay()
    
    def initTimer(self):
        self.timer = QTimer()
        self.timer.timeout.connect(self.updateSimulation)
        self.timer.setInterval(1000 // FPS)
    
    def updateSimulation(self):
        if self.battlefield.game_over:
            self.handleGameOver()
            return
            
        # 红方回合：使用强化学习智能体进行决策
        if self.battlefield.current_turn == 1:
            # 获取当前状态
            state = self.battlefield.get_state()
            
            # 为每个智能体选择动作
            for i, agent in enumerate(self.agents):
                if i < len(self.battlefield.red_units) and not self.battlefield.red_units[i].has_acted:
                    unit = self.battlefield.red_units[i]
                    valid_actions = self.battlefield.get_valid_actions(unit)
                    action = agent.select_action(state, valid_actions)
                    
                    # 执行动作
                    if action[0] == "move":
                        self.battlefield.select_unit(unit.x, unit.y)
                        self.battlefield.move_unit(action[1], action[2])
                    elif action[0] == "attack":
                        self.battlefield.select_unit(unit.x, unit.y)
                        success, damage = self.battlefield.attack(action[1], action[2])
                        # 计算奖励
                        reward = self.get_reward(unit, action, success)
                        # 存储经验
                        next_state = self.battlefield.get_state()
                        done = self.battlefield.game_over
                        agent.remember(state, action, reward, next_state, done)
                    # 其他动作类型处理...
            
            # 学习
            if self.training:
                for agent in self.agents:
                    agent.learn(self.agents)
            
            # 检查是否所有单位都已行动
            all_acted = all(unit.has_acted for unit in self.battlefield.red_units)
            if all_acted:
                self.battlefield.reset_turn()
                self.steps += 1
                self.updateStatusDisplay()
        
        self.battlefield_widget.update()
    
    def handleCellClick(self, x, y):
        if self.battlefield.game_over:
            return
            
        # 尝试选择单位
        if not self.battlefield.select_unit(x, y):
            # 如果没有选择单位，尝试移动或攻击
            if self.battlefield.selected_unit:
                if self.battlefield.move_unit(x, y):
                    pass
                else:
                    self.battlefield.attack(x, y)
        
        self.updateStatusDisplay()
        self.battlefield_widget.update()
    
    def handleRightClick(self, x, y):
        if self.battlefield.selected_unit:
            # 查找目标单位
            target_unit = None
            for unit in self.battlefield.all_units:
                if unit.x == x and unit.y == y:
                    target_unit = unit
                    break
                    
            if target_unit:
                success, message = self.battlefield.selected_unit.use_special_ability(target_unit)
                if success:
                    self.statusBar().showMessage(message, 3000)
        
        self.updateStatusDisplay()
        self.battlefield_widget.update()
    
    def handleGameOver(self):
        # 记录胜利
        if self.battlefield.winner == 1:  # 红方胜利
            self.wins += 1
            
        # 记录总奖励
        self.total_rewards.append(0)  # 这里简化处理，实际应该计算总奖励
        
        # 更新图表
        self.updateCharts()
        
        # 如果正在训练，重置游戏
        if self.training and self.episode < self.max_episodes:
            self.episode += 1
            self.resetGame()
        else:
            self.timer.stop()
            self.statusBar().showMessage("游戏结束! " + 
                                        ("蓝方胜利!" if self.battlefield.winner == 0 else "红方胜利!"))
    
    def get_reward(self, unit, action, success):
        """计算奖励"""
        reward = 0
        
        # 基础移动惩罚
        if action[0] == "move":
            reward -= 0.1
            
        # 成功攻击奖励
        if action[0] == "attack" and success:
            reward += 5
            
        # 治疗奖励
        if action[0] == "heal" and success:
            reward += 3
            
        # 占领目标奖励
        for obj in self.battlefield.objectives:
            if max(abs(unit.x - obj["x"]), abs(unit.y - obj["y"])) <= 1:
                if obj["type"] == "control_point" and obj["controlled_by"] == unit.team:
                    reward += 1
                elif obj["type"] == "resource":
                    reward += 0.5
                    
        # 单位存活奖励
        if unit.health > 0:
            reward += 0.01 * unit.health
            
        # 指挥官保护奖励
        if unit.unit_type == COMMANDER:
            reward += 0.1
            
        # 战略目标奖励
        if self.battlefield.game_over:
            if (unit.team == self.battlefield.winner):
                reward += 100
            else:
                reward -= 50
                
        return reward
    
    def updateStatusDisplay(self):
        # 更新回合信息
        turn_text = "蓝方回合" if self.battlefield.current_turn == 0 else "红方回合"
        self.turn_label.setText(turn_text)
        self.turn_label.setStyleSheet(f"font-weight: bold; color: {'blue' if self.battlefield.current_turn == 0 else 'red'};")
        
        # 更新单位数量
        blue_count = len(self.battlefield.blue_units)
        red_count = len(self.battlefield.red_units)
        self.unit_count_label.setText(f"蓝方单位: {blue_count}  红方单位: {red_count}")
        
        # 更新天气信息
        weather_text = f"天气: {weather_names[self.battlefield.weather]} " \
                      f"(移动:{weather_effects[self.battlefield.weather]['移动']*100:.0f}% " \
                      f"视野:{weather_effects[self.battlefield.weather]['视野']*100:.0f}% " \
                      f"命中:{weather_effects[self.battlefield.weather]['命中']*100:.0f}%)"
        self.weather_label.setText(weather_text)
        
        # 更新训练信息
        win_rate = self.wins / self.episode * 100 if self.episode > 0 else 0
        self.episode_label.setText(f"训练回合: {self.episode}/{self.max_episodes}")
        self.win_rate_label.setText(f"胜率: {win_rate:.1f}%")
        
        if self.agents:
            self.epsilon_label.setText(f"探索率: {self.agents[0].epsilon:.3f}")
        
        # 更新单位信息
        if self.battlefield.selected_unit:
            unit = self.battlefield.selected_unit
            stats = unit_stats[unit.unit_type]
            terrain_type = self.battlefield.terrain[unit.x, unit.y]
            
            unit_info = f"{'蓝方' if unit.team == 0 else '红方'} {unit_names[unit.unit_type]}\n" \
                       f"HP: {unit.health}  移动: {unit.movement_left}/{unit.max_movement}\n" \
                       f"攻击: {stats[0]}  防御: {stats[1]}\n" \
                       f"视野: {stats[3]}  射程: {stats[4]}\n" \
                       f"能力: {stats[5]}\n" \
                       f"地形: {terrain_names[terrain_type]} (+{terrain_defense_bonus[terrain_type]}防御)"
            
            self.unit_info_label.setText(unit_info)
        else:
            self.unit_info_label.setText("选择单位查看详情")
    
    def updateCharts(self):
        # 更新奖励图表
        self.reward_series.clear()
        for i, reward in enumerate(self.total_rewards):
            self.reward_series.append(i, reward)
        
        # 更新胜率图表
        self.win_rate_series.clear()
        win_rates = []
        for i in range(len(self.total_rewards)):
            wins_up_to_episode = sum(1 for j in range(i+1) if self.total_rewards[j] > 0)  # 简化计算
            win_rate = wins_up_to_episode / (i+1) * 100 if i > 0 else 0
            win_rates.append(win_rate)
            self.win_rate_series.append(i, win_rate)
    
    def startTraining(self):
        self.timer.start()
        self.statusBar().showMessage("训练已开始")
    
    def pauseTraining(self):
        self.timer.stop()
        self.statusBar().showMessage("训练已暂停")
    
    def resetGame(self):
        self.battlefield = Battlefield(TERRAIN_SIZE, TERRAIN_SIZE)
        self.battlefield_widget.battlefield = self.battlefield
        self.battlefield_widget.camera_x = self.battlefield.camera_x
        self.battlefield_widget.camera_y = self.battlefield.camera_y
        self.steps = 0
        self.updateStatusDisplay()
        self.battlefield_widget.update()
        self.statusBar().showMessage("游戏已重置")
    
    def toggleTraining(self, state):
        self.training = state == Qt.CheckState.Checked.value
        self.statusBar().showMessage(f"训练模式: {'开启' if self.training else '关闭'}")
    
    def toggleFogOfWar(self, state):
        self.show_fog_of_war = state == Qt.CheckState.Checked.value
        self.battlefield_widget.show_fog_of_war = self.show_fog_of_war
        self.battlefield_widget.update()
    
    def toggleStrategyVisualization(self, state):
        self.visualize_strategy = state == Qt.CheckState.Checked.value
        self.battlefield_widget.visualize_strategy = self.visualize_strategy
        self.battlefield_widget.update()
    
    def toggleInfoDisplay(self, state):
        self.show_info = state == Qt.CheckState.Checked.value
        # 这里可以控制信息显示组件的可见性
    
    def toggleAutoPlay(self, state):
        self.auto_play = state == Qt.CheckState.Checked.value
        # 自动播放功能实现
    
    def endTurn(self):
        if self.battlefield.current_turn == 0:
            self.battlefield.reset_turn()
            self.updateStatusDisplay()
            self.battlefield_widget.update()
    
    def saveModel(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "保存模型", "models", "模型文件 (*.pth)")
        if file_path:
            try:
                for i, agent in enumerate(self.agents):
                    agent.save_model(f"{file_path}_agent_{i}.pth")
                self.statusBar().showMessage("模型已保存")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"保存模型时出错: {str(e)}")
    
    def loadModel(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "加载模型", "models", "模型文件 (*.pth)")
        if file_path:
            try:
                for i, agent in enumerate(self.agents):
                    agent.load_model(f"{file_path}_agent_{i}.pth")
                self.statusBar().showMessage("模型已加载")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"加载模型时出错: {str(e)}")
    
    def closeEvent(self, event):
        self.timer.stop()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    simulation = BattleSimulation()
    simulation.show()
    sys.exit(app.exec())