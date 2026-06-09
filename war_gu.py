# -*- coding: utf-8 -*-
"""
Created on Wed Jun 18 13:32:11 2025

@author: 10166
"""

import sys
import random
import numpy as np
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib import cm
import pandas as pd
from collections import deque
import time
import math
from enum import Enum
matplotlib.rc("font", family='Microsoft YaHei')
class UnitType(Enum):
    INFANTRY = 1
    ARCHER = 2
    CAVALRY = 3
    SIEGE = 4
    SCOUT = 5
    MEDIC = 6
    COMMANDER = 7

class FormationType(Enum):
    SQUARE = "方阵"
    WEDGE = "锥形阵"
    CRESCENT = "雁行阵"
    CIRCLE = "圆阵"
    PHALANX = "方阵枪兵阵"
    TESTUDO = "龟甲阵"
    SKIRMISH = "散兵阵"
    COLUMN = "纵队阵"

class TacticalObjective(Enum):
    DEFEND_POSITION = "防守位置"
    CAPTURE_POINT = "占领据点"
    FLANK_ATTACK = "侧翼攻击"
    SUPPORT_UNIT = "支援单位"
    BREACH_WALL = "突破城墙"
    AMBUSH = "埋伏"
    RETREAT = "撤退"

class Communication:
    """战场通信系统"""
    def __init__(self, reliability=0.8):
        self.reliability = reliability  # 通信可靠性
        self.command_queue = deque()
        self.message_delay = 1.0  # 命令传递延迟(秒)
        self.command_history = []
    
    def send_command(self, command, sender, receiver):
        """发送命令"""
        # 通信可能失败
        if random.random() > self.reliability:
            return False
        
        # 记录命令
        self.command_queue.append({
            'command': command,
            'sender': sender,
            'receiver': receiver,
            'delivery_time': time.time() + self.message_delay
        })
        self.command_history.append({
            'time': time.time(),
            'command': command,
            'sender': sender.id if hasattr(sender, 'id') else "HQ",
            'receiver': receiver.id
        })
        return True
    
    def update(self):
        """更新通信状态"""
        current_time = time.time()
        delivered = []
        
        for i, cmd in enumerate(self.command_queue):
            if current_time >= cmd['delivery_time']:
                cmd['receiver'].receive_command(cmd['command'], cmd['sender'])
                delivered.append(i)
        
        # 移除已送达的命令
        for i in sorted(delivered, reverse=True):
            if i < len(self.command_queue):
                self.command_queue.remove(self.command_queue[i])

class BattleUnit:
    """基本作战单元(小队)"""
    def __init__(self, unit_id, unit_type, position, army, formation_type=FormationType.SQUARE):
        self.id = unit_id
        self.type = unit_type
        self.position = np.array(position, dtype=float)
        self.formation_position = position
        self.velocity = np.array([0, 0], dtype=float)
        self.army = army
        self.formation = formation_type
        self.objective = None
        self.subordinates = []  # 下属单位
        self.commander = None  # 上级指挥官
        self.soldiers = []
        self.status = "active"  # active, engaged, retreating, regrouping
        self.cohesion = 100  # 部队凝聚力
        self.supply = 100  # 补给水平
        self.morale = 100  # 士气
        self.combat_power = self._calculate_combat_power()
        self.engagement_range = self._get_engagement_range()
        self.color = (0, 0.5, 1) if army.id == 0 else (1, 0.2, 0.2)
        self.size = self._get_unit_size()
        self.last_command_time = 0
        self.command_cooldown = 5  # 命令冷却时间
        self.target_unit = None
        self.supporting_unit = None
        self.supported_by = None
        
        # 创建士兵
        self.create_soldiers()
    
    def _get_unit_size(self):
        """获取单位规模"""
        if self.type == UnitType.COMMANDER:
            return 15
        return 30 if self.type in [UnitType.INFANTRY, UnitType.CAVALRY] else 20
    
    def _get_engagement_range(self):
        """获取交战范围"""
        ranges = {
            UnitType.INFANTRY: 2.0,
            UnitType.ARCHER: 15.0,
            UnitType.CAVALRY: 3.0,
            UnitType.SIEGE: 25.0,
            UnitType.SCOUT: 5.0,
            UnitType.MEDIC: 3.0,
            UnitType.COMMANDER: 3.0
        }
        return ranges.get(self.type, 2.0)
    
    def _calculate_combat_power(self):
        """计算初始战斗力"""
        base_power = {
            UnitType.INFANTRY: 80,
            UnitType.ARCHER: 70,
            UnitType.CAVALRY: 100,
            UnitType.SIEGE: 150,
            UnitType.SCOUT: 40,
            UnitType.MEDIC: 30,
            UnitType.COMMANDER: 60
        }
        return base_power.get(self.type, 50)
    
    def create_soldiers(self):
        """创建单位内的士兵"""
        soldier_types = {
            UnitType.INFANTRY: ['infantry'] * 10,
            UnitType.ARCHER: ['archer'] * 8,
            UnitType.CAVALRY: ['cavalry'] * 6,
            UnitType.SIEGE: ['siege'] * 4,
            UnitType.SCOUT: ['scout'] * 6,
            UnitType.MEDIC: ['medic'] * 5,
            UnitType.COMMANDER: ['commander'] * 4
        }
        
        for soldier_type in soldier_types.get(self.type, ['infantry']):
            offset = np.array([random.uniform(-1, 1), random.uniform(-1, 1)])
            self.soldiers.append({
                'position': self.position + offset,
                'type': soldier_type,
                'health': 100
            })
    
    def update(self, dt, all_units, terrain, communication):
        """更新单位状态"""
        # 更新位置
        self.position += self.velocity * dt
        
        # 更新士兵位置
        for soldier in self.soldiers:
            soldier['position'] += self.velocity * dt
        
        # 更新补给和士气
        self.supply = max(0, self.supply - 0.01 * dt)
        if self.supply < 30:
            self.morale = max(0, self.morale - 0.05 * dt)
        
        # 处理命令
        current_time = time.time()
        if current_time - self.last_command_time > self.command_cooldown:
            self.evaluate_situation(all_units)
            self.last_command_time = current_time
        
        # 执行当前目标
        self.execute_objective(all_units, terrain)
        
        # 协同作战逻辑
        self.cooperative_actions(all_units)
        
        # 更新凝聚力
        self.update_cohesion()
    
    def evaluate_situation(self, all_units):
        """评估战场形势"""
        # 如果当前没有目标，寻找最近敌人
        if self.objective is None:
            self.find_engage_target(all_units)
        
        # 如果处于劣势，请求支援
        if self.cohesion < 50 and self.supported_by is None:
            self.request_support(all_units)
    
    def find_engage_target(self, all_units):
        """寻找交战目标"""
        min_dist = float('inf')
        target = None
        
        for unit in all_units:
            if unit.army != self.army and unit.status == "active":
                dist = np.linalg.norm(unit.position - self.position)
                # 优先攻击被克制的单位
                if self.type == UnitType.CAVALRY and unit.type == UnitType.ARCHER:
                    dist *= 0.7
                if dist < min_dist:
                    min_dist = dist
                    target = unit
        
        if target:
            self.objective = TacticalObjective.DEFEND_POSITION
            self.target_unit = target
            # 如果是远程单位，保持距离
            if self.type == UnitType.ARCHER and min_dist < self.engagement_range * 0.7:
                self.objective = TacticalObjective.RETREAT
    
    def request_support(self, all_units):
        """请求支援"""
        # 寻找最近的友军单位
        min_dist = float('inf')
        support_unit = None
        
        for unit in all_units:
            if unit.army == self.army and unit != self and unit.status == "active":
                dist = np.linalg.norm(unit.position - self.position)
                if dist < min_dist:
                    min_dist = dist
                    support_unit = unit
        
        if support_unit and min_dist < 50:  # 在合理距离内
            # 通过通信系统发送支援请求
            if self.army.communication.send_command(
                {'type': 'support_request', 'target': self.id}, 
                self, 
                support_unit
            ):
                self.supported_by = support_unit
    
    def execute_objective(self, all_units, terrain):
        """执行当前目标"""
        if self.objective == TacticalObjective.DEFEND_POSITION:
            self.defend_position()
        elif self.objective == TacticalObjective.FLANK_ATTACK:
            self.execute_flank_attack(all_units)
        elif self.objective == TacticalObjective.SUPPORT_UNIT:
            self.support_other_unit()
        elif self.objective == TacticalObjective.CAPTURE_POINT:
            self.capture_objective()
        elif self.objective == TacticalObjective.AMBUSH:
            self.execute_ambush()
        elif self.objective == TacticalObjective.RETREAT:
            self.retreat_to_position()
    
    def defend_position(self):
        """防守位置"""
        if self.target_unit:
            direction = self.target_unit.position - self.position
            distance = np.linalg.norm(direction)
            
            # 根据单位类型调整战术
            if self.type == UnitType.ARCHER:
                # 弓箭手保持距离
                if distance < self.engagement_range * 0.8:
                    self.velocity = -direction / distance * 0.4
                elif distance > self.engagement_range * 1.2:
                    self.velocity = direction / distance * 0.3
                else:
                    self.velocity = np.array([0, 0])
            elif self.type == UnitType.CAVALRY:
                # 骑兵冲锋
                if distance > self.engagement_range:
                    self.velocity = direction / distance * 0.7
                else:
                    self.velocity = np.array([0, 0])
            else:
                # 步兵稳步推进
                if distance > self.engagement_range:
                    self.velocity = direction / distance * 0.4
                else:
                    self.velocity = np.array([0, 0])
    
    def execute_flank_attack(self, all_units):
        """执行侧翼攻击"""
        if not self.target_unit:
            return
        
        # 计算目标单位的侧翼位置
        flank_vector = np.array([self.target_unit.position[1] - self.position[1], 
                               self.position[0] - self.target_unit.position[0]])
        flank_vector = flank_vector / np.linalg.norm(flank_vector) * 15
        
        flank_position = self.target_unit.position + flank_vector
        
        # 向侧翼位置移动
        direction = flank_position - self.position
        distance = np.linalg.norm(direction)
        
        if distance > 5:
            self.velocity = direction / distance * 0.5
        else:
            # 到达侧翼位置，转为攻击
            self.objective = TacticalObjective.DEFEND_POSITION
    
    def support_other_unit(self):
        """支援其他单位"""
        if not self.supporting_unit:
            return
        
        # 移动到被支援单位附近
        support_position = self.supporting_unit.position + np.array([5, 5])
        direction = support_position - self.position
        distance = np.linalg.norm(direction)
        
        if distance > 5:
            self.velocity = direction / distance * 0.5
        else:
            # 到达支援位置，协助防守
            self.target_unit = self.supporting_unit.target_unit
            self.objective = TacticalObjective.DEFEND_POSITION
    
    def capture_objective(self):
        """占领目标点"""
        if not hasattr(self, 'objective_position'):
            return
        
        direction = self.objective_position - self.position
        distance = np.linalg.norm(direction)
        
        if distance > 2:
            self.velocity = direction / distance * 0.4
        else:
            # 已到达目标点
            self.objective = None
            self.velocity = np.array([0, 0])
    
    def execute_ambush(self):
        """执行埋伏"""
        if not hasattr(self, 'ambush_position'):
            return
        
        # 移动到埋伏位置
        direction = self.ambush_position - self.position
        distance = np.linalg.norm(direction)
        
        if distance > 2:
            self.velocity = direction / distance * 0.3
        else:
            # 已到达埋伏位置，等待
            self.velocity = np.array([0, 0])
            self.status = "ambushing"
    
    def retreat_to_position(self):
        """撤退到指定位置"""
        if not hasattr(self, 'retreat_position'):
            # 默认向后方撤退
            self.retreat_position = self.position - np.array([20, 0]) if self.army.id == 0 else self.position + np.array([20, 0])
        
        direction = self.retreat_position - self.position
        distance = np.linalg.norm(direction)
        
        if distance > 5:
            self.velocity = direction / distance * 0.6
        else:
            # 已到达撤退位置，重组
            self.status = "regrouping"
            self.velocity = np.array([0, 0])
    
    def cooperative_actions(self, all_units):
        """协同作战行动"""
        # 与支援单位协同
        if self.supporting_unit:
            # 保持适当距离
            direction = self.supporting_unit.position - self.position
            distance = np.linalg.norm(direction)
            
            if distance > 15:
                # 靠近支援单位
                self.velocity = direction / distance * 0.4
            elif distance < 8:
                # 避免拥挤
                self.velocity = -direction / distance * 0.2
        
        # 与指挥官协同
        if self.commander:
            direction = self.commander.position - self.position
            distance = np.linalg.norm(direction)
            
            if distance > 20:
                # 靠近指挥官
                self.velocity = direction / distance * 0.3
    
    def update_cohesion(self):
        """更新部队凝聚力"""
        # 基础凝聚力衰减
        self.cohesion -= 0.01
        
        # 士气影响
        if self.morale > 70:
            self.cohesion += 0.02
        elif self.morale < 30:
            self.cohesion -= 0.03
        
        # 战斗状态影响
        if self.status == "engaged":
            self.cohesion -= 0.02
        elif self.status == "retreating":
            self.cohesion -= 0.05
        
        # 确保凝聚力在合理范围内
        self.cohesion = max(0, min(100, self.cohesion))
        
        # 凝聚力低于阈值时状态变化
        if self.cohesion < 30 and self.status != "retreating":
            self.status = "retreating"
            self.objective = TacticalObjective.RETREAT
    
    def receive_command(self, command, sender):
        """接收命令"""
        if command['type'] == 'support_request':
            # 收到支援请求
            target_unit = self.army.get_unit_by_id(command['target'])
            if target_unit:
                self.supporting_unit = target_unit
                self.objective = TacticalObjective.SUPPORT_UNIT
                target_unit.supported_by = self
        elif command['type'] == 'flank_attack':
            # 收到侧翼攻击命令
            target_unit = self.army.get_unit_by_id(command['target'])
            if target_unit:
                self.target_unit = target_unit
                self.objective = TacticalObjective.FLANK_ATTACK
        elif command['type'] == 'capture_point':
            # 收到占领据点命令
            self.objective_position = np.array(command['position'])
            self.objective = TacticalObjective.CAPTURE_POINT
        elif command['type'] == 'ambush':
            # 收到埋伏命令
            self.ambush_position = np.array(command['position'])
            self.objective = TacticalObjective.AMBUSH
        elif command['type'] == 'retreat':
            # 收到撤退命令
            self.retreat_position = np.array(command['position'])
            self.objective = TacticalObjective.RETREAT
            self.status = "retreating"

class CommanderUnit(BattleUnit):
    """指挥官单位"""
    def __init__(self, unit_id, position, army):
        super().__init__(unit_id, UnitType.COMMANDER, position, army)
        self.strategy = "balanced"  # balanced, aggressive, defensive
        self.command_range = 50  # 命令范围
        self.command_power = 1.2  # 指挥加成
        self.aura_effect = 0.1  # 光环效果
        self.unit_assignments = {}  # 单位分配的任务
        self.objectives = []  # 战术目标列表
    
    def update(self, dt, all_units, terrain, communication):
        """更新指挥官状态"""
        super().update(dt, all_units, terrain, communication)
        
        # 应用指挥官光环
        self.apply_commander_aura(all_units)
        
        # 战略决策
        self.strategic_decision_making(all_units, communication)
    
    def apply_commander_aura(self, all_units):
        """应用指挥官光环效果"""
        for unit in all_units:
            if unit.army == self.army:
                dist = np.linalg.norm(unit.position - self.position)
                if dist < self.command_range:
                    # 增加士气和凝聚力
                    unit.morale = min(100, unit.morale + self.aura_effect)
                    unit.cohesion = min(100, unit.cohesion + self.aura_effect)
    
    def strategic_decision_making(self, all_units, communication):
        """战略决策"""
        # 评估战场形势
        enemy_units = [u for u in all_units if u.army != self.army]
        friendly_units = [u for u in all_units if u.army == self.army]
        
        # 计算双方力量对比
        friendly_power = sum(u.combat_power for u in friendly_units)
        enemy_power = sum(u.combat_power for u in enemy_units)
        
        # 根据战略类型决策
        if self.strategy == "aggressive":
            self.aggressive_strategy(friendly_units, enemy_units, communication)
        elif self.strategy == "defensive":
            self.defensive_strategy(friendly_units, enemy_units, communication)
        else:
            self.balanced_strategy(friendly_units, enemy_units, communication)
    
    def aggressive_strategy(self, friendly_units, enemy_units, communication):
        """进攻性策略"""
        # 寻找主要目标
        primary_target = None
        max_power = 0
        for unit in enemy_units:
            if unit.combat_power > max_power:
                max_power = unit.combat_power
                primary_target = unit
        
        if primary_target:
            # 分配单位执行侧翼攻击
            flank_units = self.select_units_for_flank(friendly_units, primary_target)
            for unit in flank_units:
                if unit != self and communication.send_command(
                    {'type': 'flank_attack', 'target': primary_target.id}, 
                    self, 
                    unit
                ):
                    self.unit_assignments[unit.id] = "flank_attack"
            
            # 其他单位正面进攻
            for unit in friendly_units:
                if unit.id not in self.unit_assignments and unit != self:
                    unit.target_unit = primary_target
                    unit.objective = TacticalObjective.DEFEND_POSITION
    
    def defensive_strategy(self, friendly_units, enemy_units, communication):
        """防御性策略"""
        # 识别最近的威胁
        closest_threat = None
        min_dist = float('inf')
        for unit in enemy_units:
            dist = np.linalg.norm(unit.position - self.position)
            if dist < min_dist:
                min_dist = dist
                closest_threat = unit
        
        if closest_threat:
            # 分配单位防御关键位置
            key_position = self.position + np.array([5, 0]) if self.army.id == 0 else self.position - np.array([5, 0])
            
            for unit in friendly_units:
                if unit.type == UnitType.INFANTRY and communication.send_command(
                    {'type': 'capture_point', 'position': key_position.tolist()}, 
                    self, 
                    unit
                ):
                    self.unit_assignments[unit.id] = "defend_position"
            
            # 设置埋伏
            ambush_position = closest_threat.position + np.array([0, 15])
            ambush_units = [u for u in friendly_units if u.type == UnitType.CAVALRY]
            if ambush_units:
                ambush_unit = random.choice(ambush_units)
                if communication.send_command(
                    {'type': 'ambush', 'position': ambush_position.tolist()}, 
                    self, 
                    ambush_unit
                ):
                    self.unit_assignments[ambush_unit.id] = "ambush"
    
    def balanced_strategy(self, friendly_units, enemy_units, communication):
        """平衡策略"""
        # 识别最弱的敌人单位
        weakest_enemy = None
        min_power = float('inf')
        for unit in enemy_units:
            if unit.combat_power < min_power:
                min_power = unit.combat_power
                weakest_enemy = unit
        
        if weakest_enemy:
            # 集中优势兵力攻击最弱点
            attack_units = self.select_units_for_attack(friendly_units, weakest_enemy)
            for unit in attack_units:
                if communication.send_command(
                    {'type': 'flank_attack', 'target': weakest_enemy.id}, 
                    self, 
                    unit
                ):
                    self.unit_assignments[unit.id] = "attack_weakest"
            
            # 其他单位防御
            for unit in friendly_units:
                if unit.id not in self.unit_assignments and unit != self:
                    unit.objective = TacticalObjective.DEFEND_POSITION
    
    def select_units_for_flank(self, friendly_units, target):
        """选择执行侧翼攻击的单位"""
        # 优先选择骑兵和机动性强的单位
        flank_units = []
        for unit in friendly_units:
            if unit.type in [UnitType.CAVALRY, UnitType.SCOUT] and unit.status == "active":
                flank_units.append(unit)
        
        # 如果没有合适的单位，选择最近的单位
        if not flank_units:
            min_dist = float('inf')
            closest_unit = None
            for unit in friendly_units:
                if unit.status == "active" and unit != self:
                    dist = np.linalg.norm(unit.position - target.position)
                    if dist < min_dist:
                        min_dist = dist
                        closest_unit = unit
            if closest_unit:
                flank_units.append(closest_unit)
        
        return flank_units[:3]  # 最多选择3个单位
    
    def select_units_for_attack(self, friendly_units, target):
        """选择执行攻击的单位"""
        # 根据距离和单位类型选择
        eligible_units = []
        for unit in friendly_units:
            if unit.type not in [UnitType.SIEGE, UnitType.MEDIC] and unit.status == "active":
                dist = np.linalg.norm(unit.position - target.position)
                if dist < 40:  # 在合理距离内
                    eligible_units.append((unit, dist))
        
        # 按距离排序
        eligible_units.sort(key=lambda x: x[1])
        return [u[0] for u in eligible_units[:5]]  # 最多选择5个单位

class Army:
    """军队组织"""
    def __init__(self, army_id, strategy="balanced"):
        self.id = army_id
        self.strategy = strategy
        self.units = []
        self.commander = None
        self.communication = Communication()
        self.supply_depot = None
        self.objectives = []
        self.strength_history = []
        self.cohesion_history = []
    
    def add_unit(self, unit):
        """添加作战单位"""
        self.units.append(unit)
        # 如果是指挥官单位，设置为军队指挥官
        if unit.type == UnitType.COMMANDER:
            self.commander = unit
        # 设置单位所属军队
        unit.army = self
    
    def get_unit_by_id(self, unit_id):
        """通过ID获取单位"""
        for unit in self.units:
            if unit.id == unit_id:
                return unit
        return None
    
    def update(self, dt, all_units, terrain):
        """更新军队状态"""
        # 更新通信系统
        self.communication.update()
        
        # 更新所有单位
        for unit in self.units:
            unit.update(dt, all_units, terrain, self.communication)
        
        # 记录军队状态
        self.record_army_status()
    
    def record_army_status(self):
        """记录军队状态"""
        total_strength = 0
        total_cohesion = 0
        active_units = 0
        
        for unit in self.units:
            if unit.status != "retreating":
                total_strength += unit.combat_power * (unit.cohesion / 100)
                total_cohesion += unit.cohesion
                active_units += 1
        
        avg_cohesion = total_cohesion / len(self.units) if self.units else 0
        
        self.strength_history.append(total_strength)
        self.cohesion_history.append(avg_cohesion)
    
    def issue_strategic_command(self, command):
        """发布战略命令"""
        if self.commander:
            # 命令传递给指挥官
            self.communication.send_command(command, "HQ", self.commander)

class BattleSimulation:
    """协同作战模拟系统"""
    def __init__(self):
        self.army1 = None
        self.army2 = None
        self.time = 0
        self.battle_history = []
        self.simulation_speed = 1.0
        self.battle_recording = []
        self.key_positions = self.generate_key_positions()
    
    def generate_key_positions(self):
        """生成关键战略位置"""
        return {
            "hill": [30, 70],
            "bridge": [50, 40],
            "village": [70, 30],
            "forest": [40, 20]
        }
    
    def initialize_battle(self, army1_strategy="balanced", army2_strategy="aggressive"):
        """初始化战斗"""
        self.army1 = Army(0, army1_strategy)
        self.army2 = Army(1, army2_strategy)
        self.time = 0
        self.battle_history = []
        self.battle_recording = []
        
        # 创建蓝方单位
        self.create_units(self.army1, 0)
        # 创建红方单位
        self.create_units(self.army2, 100)
        
        # 设置初始目标
        self.set_initial_objectives()
        
        # 记录初始状态
        self.record_full_state()
    
    def create_units(self, army, x_offset):
        """创建军队单位"""
        # 创建指挥官
        commander = CommanderUnit(1000 + army.id * 100, [x_offset + 10, 50], army)
        army.add_unit(commander)
        
        # 创建步兵单位
        for i in range(3):
            unit = BattleUnit(
                100 + i + army.id * 100,
                UnitType.INFANTRY,
                [x_offset + 15 + i * 5, 45 + i * 2],
                army
            )
            unit.commander = commander
            army.add_unit(unit)
        
        # 创建弓箭手单位
        for i in range(2):
            unit = BattleUnit(
                200 + i + army.id * 100,
                UnitType.ARCHER,
                [x_offset + 12 + i * 6, 55 + i * 2],
                army
            )
            unit.commander = commander
            army.add_unit(unit)
        
        # 创建骑兵单位
        for i in range(2):
            unit = BattleUnit(
                300 + i + army.id * 100,
                UnitType.CAVALRY,
                [x_offset + 20 + i * 8, 35 - i * 3],
                army
            )
            unit.commander = commander
            army.add_unit(unit)
        
        # 创建侦察单位
        unit = BattleUnit(
            400 + army.id * 100,
            UnitType.SCOUT,
            [x_offset + 5, 60],
            army
        )
        unit.commander = commander
        army.add_unit(unit)
        
        # 创建医疗单位
        unit = BattleUnit(
            500 + army.id * 100,
            UnitType.MEDIC,
            [x_offset + 8, 40],
            army
        )
        unit.commander = commander
        army.add_unit(unit)
    
    def set_initial_objectives(self):
        """设置初始战术目标"""
        # 蓝方目标：占领高地
        if self.army1.commander:
            self.army1.commander.objective_position = self.key_positions["hill"]
            self.army1.commander.objective = TacticalObjective.CAPTURE_POINT
        
        # 红方目标：进攻村庄
        if self.army2.commander:
            self.army2.commander.objective_position = self.key_positions["village"]
            self.army2.commander.objective = TacticalObjective.CAPTURE_POINT
    
    def update(self, dt):
        """更新模拟状态"""
        # 应用模拟速度
        dt *= self.simulation_speed
        self.time += dt
        
        # 获取所有单位
        all_units = self.army1.units + self.army2.units
        
        # 更新军队
        self.army1.update(dt, all_units, None)
        self.army2.update(dt, all_units, None)
        
        # 记录战斗状态
        if int(self.time) % 2 == 0:  # 每2秒记录一次
            self.record_battle_state()
            self.record_full_state()
    
    def record_full_state(self):
        """记录完整战场状态"""
        state = {
            "time": self.time,
            "army1": [],
            "army2": [],
            "communications": self.army1.communication.command_history[-5:] + self.army2.communication.command_history[-5:]
        }
        
        # 记录蓝方单位
        for unit in self.army1.units:
            soldiers_data = []
            for soldier in unit.soldiers:
                soldiers_data.append({
                    "position": soldier['position'].tolist(),
                    "type": soldier['type'],
                    "health": soldier['health']
                })
            
            state["army1"].append({
                "id": unit.id,
                "type": unit.type.name,
                "position": unit.position.tolist(),
                "status": unit.status,
                "objective": unit.objective.name if unit.objective else None,
                "target": unit.target_unit.id if unit.target_unit else None,
                "supporting": unit.supporting_unit.id if unit.supporting_unit else None,
                "supported_by": unit.supported_by.id if unit.supported_by else None,
                "cohesion": unit.cohesion,
                "morale": unit.morale,
                "combat_power": unit.combat_power,
                "soldiers": soldiers_data
            })
        
        # 记录红方单位
        for unit in self.army2.units:
            soldiers_data = []
            for soldier in unit.soldiers:
                soldiers_data.append({
                    "position": soldier['position'].tolist(),
                    "type": soldier['type'],
                    "health": soldier['health']
                })
            
            state["army2"].append({
                "id": unit.id,
                "type": unit.type.name,
                "position": unit.position.tolist(),
                "status": unit.status,
                "objective": unit.objective.name if unit.objective else None,
                "target": unit.target_unit.id if unit.target_unit else None,
                "supporting": unit.supporting_unit.id if unit.supporting_unit else None,
                "supported_by": unit.supported_by.id if unit.supported_by else None,
                "cohesion": unit.cohesion,
                "morale": unit.morale,
                "combat_power": unit.combat_power,
                "soldiers": soldiers_data
            })
        
        self.battle_recording.append(state)
    
    def record_battle_state(self):
        """记录战斗关键状态"""
        state = {
            "time": self.time,
            "army1_strength": self.army1.strength_history[-1] if self.army1.strength_history else 0,
            "army2_strength": self.army2.strength_history[-1] if self.army2.strength_history else 0,
            "army1_cohesion": self.army1.cohesion_history[-1] if self.army1.cohesion_history else 0,
            "army2_cohesion": self.army2.cohesion_history[-1] if self.army2.cohesion_history else 0,
            "army1_active_units": sum(1 for u in self.army1.units if u.status != "retreating"),
            "army2_active_units": sum(1 for u in self.army2.units if u.status != "retreating"),
            "cooperative_actions": self.count_cooperative_actions()
        }
        self.battle_history.append(state)
    
    def count_cooperative_actions(self):
        """计算协同行动数量"""
        count = 0
        for unit in self.army1.units + self.army2.units:
            if unit.supporting_unit or unit.supported_by:
                count += 1
        return count
    
    def get_battle_result(self):
        """获取战斗结果"""
        if not self.battle_history:
            return "战斗未开始"
        
        last_state = self.battle_history[-1]
        if last_state["army1_active_units"] == 0 and last_state["army2_active_units"] > 0:
            return "红方胜利"
        elif last_state["army2_active_units"] == 0 and last_state["army1_active_units"] > 0:
            return "蓝方胜利"
        elif last_state["army1_strength"] > last_state["army2_strength"]:
            return "蓝方战术胜利"
        elif last_state["army2_strength"] > last_state["army1_strength"]:
            return "红方战术胜利"
        return "平局"

class BattleCanvas(FigureCanvas):
    """战场可视化画布"""
    def __init__(self, width=10, height=8, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        super().__init__(self.fig)
        
        # 设置战场主视图
        self.ax = self.fig.add_subplot(111)
        self.ax.set_xlim(0, 100)
        self.ax.set_ylim(0, 100)
        self.ax.set_facecolor('#e0e0c0')
        self.ax.set_title('协同作战战场态势', fontsize=14, fontweight='bold')
        self.ax.set_xlabel('战场宽度', fontsize=10)
        self.ax.set_ylabel('战场高度', fontsize=10)
        
        # 士兵散点图
        self.soldier_scatter = self.ax.scatter([], [], s=30, alpha=0.8)
        
        # 单位标记
        self.unit_scatter = self.ax.scatter([], [], s=100, alpha=0.9)
        
        # 指挥线
        self.command_lines = []
        
        # 支援线
        self.support_lines = []
        
        # 关键位置标记
        self.key_positions = []
        
        # 添加图例
        from matplotlib.lines import Line2D
        legend_elements = [
            Line2D([0], [0], marker='o', color='w', markerfacecolor=(0, 0.5, 1), markersize=10, label='蓝方士兵'),
            Line2D([0], [0], marker='o', color='w', markerfacecolor=(1, 0.2, 0.2), markersize=10, label='红方士兵'),
            Line2D([0], [0], marker='s', color=(0, 0.2, 0.8), markersize=12, label='蓝方单位'),
            Line2D([0], [0], marker='s', color=(0.8, 0.1, 0.1), markersize=12, label='红方单位'),
            Line2D([0], [0], marker='*', color=(0, 0.8, 0.2), markersize=15, label='关键位置'),
            Line2D([0], [0], color='blue', lw=2, label='指挥关系'),
            Line2D([0], [0], color='green', lw=2, label='支援关系')
        ]
        self.ax.legend(handles=legend_elements, loc='upper right', framealpha=0.7)
        
    def update_battlefield(self, army1, army2, key_positions):
        """更新战场显示"""
        # 清除旧绘图元素
        for line in self.command_lines + self.support_lines:
            if line in self.ax.lines:
                line.remove()
        for marker in self.key_positions:
            if marker in self.ax.collections:
                marker.remove()
        
        self.command_lines = []
        self.support_lines = []
        self.key_positions = []
        
        # 收集所有士兵的位置和颜色
        soldier_positions = []
        soldier_colors = []
        
        # 收集所有单位的位置和颜色
        unit_positions = []
        unit_colors = []
        unit_sizes = []
        
        # 处理蓝方
        for unit in army1.units:
            # 添加单位位置
            unit_positions.append(unit.position)
            unit_colors.append(unit.color)
            unit_sizes.append(100 + unit.cohesion)
            
            # 添加士兵位置
            for soldier in unit.soldiers:
                soldier_positions.append(soldier['position'])
                soldier_colors.append(unit.color)
            
            # 绘制指挥关系
            if unit.commander:
                self.command_lines.append(self.ax.plot(
                    [unit.position[0], unit.commander.position[0]],
                    [unit.position[1], unit.commander.position[1]],
                    'b-', alpha=0.4, linewidth=1
                )[0])
            
            # 绘制支援关系
            if unit.supporting_unit:
                self.support_lines.append(self.ax.plot(
                    [unit.position[0], unit.supporting_unit.position[0]],
                    [unit.position[1], unit.supporting_unit.position[1]],
                    'g-', alpha=0.6, linewidth=1.5
                )[0])
        
        # 处理红方
        for unit in army2.units:
            # 添加单位位置
            unit_positions.append(unit.position)
            unit_colors.append(unit.color)
            unit_sizes.append(100 + unit.cohesion)
            
            # 添加士兵位置
            for soldier in unit.soldiers:
                soldier_positions.append(soldier['position'])
                soldier_colors.append(unit.color)
            
            # 绘制指挥关系
            if unit.commander:
                self.command_lines.append(self.ax.plot(
                    [unit.position[0], unit.commander.position[0]],
                    [unit.position[1], unit.commander.position[1]],
                    'r-', alpha=0.4, linewidth=1
                )[0])
            
            # 绘制支援关系
            if unit.supporting_unit:
                self.support_lines.append(self.ax.plot(
                    [unit.position[0], unit.supporting_unit.position[0]],
                    [unit.position[1], unit.supporting_unit.position[1]],
                    'g-', alpha=0.6, linewidth=1.5
                )[0])
        
        # 标记关键位置
        for name, pos in key_positions.items():
            marker = self.ax.scatter([pos[0]], [pos[1]], s=200, marker='*', c='green', alpha=0.7)
            self.ax.text(pos[0], pos[1]+3, name, fontsize=9, ha='center')
            self.key_positions.append(marker)
        
        # 更新士兵散点图
        if soldier_positions:
            soldier_positions = np.array(soldier_positions)
            self.soldier_scatter.set_offsets(soldier_positions)
            self.soldier_scatter.set_color(soldier_colors)
        
        # 更新单位散点图
        if unit_positions:
            unit_positions = np.array(unit_positions)
            self.unit_scatter.set_offsets(unit_positions)
            self.unit_scatter.set_color(unit_colors)
            self.unit_scatter.set_sizes(unit_sizes)
        
        self.draw()


class CommandLog(QTextEdit):
    """指挥命令日志"""
    def __init__(self):
        super().__init__()
        self.setReadOnly(True)
        self.setMinimumHeight(150)
        self.setStyleSheet("""
            background-color: #1e1e1e;
            color: #d4d4d4;
            font-family: Consolas, monospace;
            font-size: 10pt;
            border: 1px solid #3c3c3c;
        """)
    
    def add_command(self, command):
        """添加命令到日志"""
        timestamp = time.strftime("%H:%M:%S", time.localtime(command['time']))
        sender = command['sender']
        receiver = command['receiver']
        cmd_type = command['command']['type']
        
        # 创建HTML格式的日志条目
        html = f"""
        <div style="margin-bottom: 4px;">
            <span style="color: #6a9955;">[{timestamp}]</span>
            <span style="color: #9cdcfe;">{sender}</span> → 
            <span style="color: #4ec9b0;">{receiver}</span>:
            <span style="color: #dcdcaa;">{cmd_type}</span>
        </div>
        """
        
        # 保持滚动条在底部
        scrollbar = self.verticalScrollBar()
        at_bottom = scrollbar.value() == scrollbar.maximum()
        
        # 插入新日志
        self.insertHtml(html)
        
        if at_bottom:
            scrollbar.setValue(scrollbar.maximum())


class BattleSimulator(QMainWindow):
    """主应用窗口"""
    def __init__(self):
        super().__init__()
        
        self.simulation = BattleSimulation()
        self.initUI()
        self.initSimulation()
        
        # 设置动画定时器
        self.timer = QTimer()
        self.timer.timeout.connect(self.updateSimulation)
        self.timer.start(50)  # 20 FPS
        
    def initUI(self):
        """初始化用户界面"""
        self.setWindowTitle('复杂协同作战兵阵模拟系统')
        self.setGeometry(100, 100, 1600, 900)
        
        # 创建主布局
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        
        # 顶部控制面板
        control_panel = QFrame()
        control_panel.setFrameShape(QFrame.StyledPanel)
        control_layout = QHBoxLayout(control_panel)
        
        # 蓝方策略
        blue_group = QGroupBox("蓝方策略")
        blue_layout = QVBoxLayout(blue_group)
        self.blue_strategy = QComboBox()
        self.blue_strategy.addItems(["平衡", "进攻", "防守"])
        blue_layout.addWidget(self.blue_strategy)
        
        # 红方策略
        red_group = QGroupBox("红方策略")
        red_layout = QVBoxLayout(red_group)
        self.red_strategy = QComboBox()
        self.red_strategy.addItems(["平衡", "进攻", "防守"])
        self.red_strategy.setCurrentIndex(1)
        red_layout.addWidget(self.red_strategy)
        
        # 控制按钮
        btn_layout = QVBoxLayout()
        self.start_btn = QPushButton("开始模拟")
        self.start_btn.setStyleSheet("background-color: #4CAF50; color: white;")
        self.start_btn.clicked.connect(self.startSimulation)
        btn_layout.addWidget(self.start_btn)
        
        self.pause_btn = QPushButton("暂停")
        self.pause_btn.setStyleSheet("background-color: #f0ad4e; color: white;")
        self.pause_btn.clicked.connect(self.pauseSimulation)
        btn_layout.addWidget(self.pause_btn)
        
        self.reset_btn = QPushButton("重置")
        self.reset_btn.setStyleSheet("background-color: #d9534f; color: white;")
        self.reset_btn.clicked.connect(self.resetSimulation)
        btn_layout.addWidget(self.reset_btn)
        
        # 速度控制
        speed_layout = QHBoxLayout()
        speed_layout.addWidget(QLabel("速度:"))
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setRange(1, 10)
        self.speed_slider.setValue(5)
        self.speed_slider.valueChanged.connect(self.update_simulation_speed)
        speed_layout.addWidget(self.speed_slider)
        
        # 添加到控制面板
        control_layout.addWidget(blue_group)
        control_layout.addWidget(red_group)
        control_layout.addLayout(btn_layout)
        control_layout.addLayout(speed_layout)
        
        main_layout.addWidget(control_panel)
        
        # 中央区域
        center_widget = QWidget()
        center_layout = QHBoxLayout(center_widget)
        
        # 左侧战场可视化
        self.battle_canvas = BattleCanvas(width=10, height=8, dpi=80)
        center_layout.addWidget(self.battle_canvas, 70)  # 70%宽度
        
        # 右侧信息面板
        info_panel = QFrame()
        info_panel.setFrameShape(QFrame.StyledPanel)
        info_layout = QVBoxLayout(info_panel)
        
        # 单位状态表格
        self.unit_table = QTableWidget()
        self.unit_table.setColumnCount(7)
        self.unit_table.setHorizontalHeaderLabels(["ID", "类型", "位置", "状态", "目标", "凝聚力", "战斗力"])
        self.unit_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.unit_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.unit_table.verticalHeader().setVisible(False)
        info_layout.addWidget(QLabel("单位状态"))
        info_layout.addWidget(self.unit_table, 40)  # 40%高度
        
        # 指挥命令日志
        self.command_log = CommandLog()
        info_layout.addWidget(QLabel("指挥命令"))
        info_layout.addWidget(self.command_log, 60)  # 60%高度
        
        center_layout.addWidget(info_panel, 30)  # 30%宽度
        
        main_layout.addWidget(center_widget, 90)  # 90%高度
        
        # 底部状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("准备就绪")
        
        # 设置样式
        self.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid gray;
                border-radius: 5px;
                margin-top: 1ex;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px 0 3px;
            }
            QTableWidget {
                gridline-color: #d0d0d0;
                font-size: 10pt;
            }
            QHeaderView::section {
                background-color: #f0f0f0;
                padding: 4px;
                border: 1px solid #d0d0d0;
            }
            QStatusBar {
                background-color: #f0f0f0;
                border-top: 1px solid #d0d0d0;
            }
        """)
    
    def initSimulation(self):
        """初始化模拟"""
        self.simulation.initialize_battle(
            army1_strategy=self.get_strategy_name(self.blue_strategy.currentIndex()),
            army2_strategy=self.get_strategy_name(self.red_strategy.currentIndex())
        )
        self.updateVisualization()
        self.updateUnitTable()
        self.status_bar.showMessage("模拟已初始化")
    
    def get_strategy_name(self, index):
        """获取策略名称"""
        strategies = ["balanced", "aggressive", "defensive"]
        return strategies[index]
    
    def update_simulation_speed(self, value):
        """更新模拟速度"""
        self.simulation.simulation_speed = value / 5.0
        self.status_bar.showMessage(f"模拟速度: {self.simulation.simulation_speed:.1f}x")
    
    def startSimulation(self):
        """开始模拟"""
        self.status_bar.showMessage("模拟运行中...")
        self.timer.start(50)
    
    def pauseSimulation(self):
        """暂停模拟"""
        self.status_bar.showMessage("模拟已暂停")
        self.timer.stop()
    
    def resetSimulation(self):
        """重置模拟"""
        self.status_bar.showMessage("重置模拟")
        self.timer.stop()
        self.initSimulation()
    
    def updateSimulation(self):
        """更新模拟状态"""
        self.simulation.update(0.5)  # 更新模拟，时间步长为0.5秒
        self.updateVisualization()
        self.updateUnitTable()
        self.updateCommandLog()
        
        # 检查战斗是否结束
        last_state = self.simulation.battle_history[-1] if self.simulation.battle_history else None
        if last_state and (last_state["army1_active_units"] == 0 or last_state["army2_active_units"] == 0):
            self.timer.stop()
            result = self.simulation.get_battle_result()
            self.status_bar.showMessage(f"战斗结束: {result}")
    
    def updateVisualization(self):
        """更新可视化"""
        if self.simulation.army1 and self.simulation.army2:
            self.battle_canvas.update_battlefield(
                self.simulation.army1, 
                self.simulation.army2,
                self.simulation.key_positions
            )
    
    def updateUnitTable(self):
        """更新单位状态表格"""
        if not self.simulation.army1 or not self.simulation.army2:
            return
        
        # 合并所有单位
        all_units = self.simulation.army1.units + self.simulation.army2.units
        
        self.unit_table.setRowCount(len(all_units))
        
        for i, unit in enumerate(all_units):
            # 创建所有表格项
            id_item = QTableWidgetItem(str(unit.id))
            type_item = QTableWidgetItem(unit.type.name)
            pos_text = f"({unit.position[0]:.1f}, {unit.position[1]:.1f})"
            pos_item = QTableWidgetItem(pos_text)
            status_item = QTableWidgetItem(unit.status)
            
            objective = unit.objective.name if unit.objective else "无"
            obj_item = QTableWidgetItem(objective)
            
            cohesion_item = QTableWidgetItem(f"{unit.cohesion:.1f}")
            if unit.cohesion > 70:
                cohesion_item.setForeground(QColor(0, 128, 0))
            elif unit.cohesion > 40:
                cohesion_item.setForeground(QColor(200, 100, 0))
            else:
                cohesion_item.setForeground(QColor(220, 0, 0))
            
            power_item = QTableWidgetItem(f"{unit.combat_power:.1f}")
            
            # 添加到表格
            self.unit_table.setItem(i, 0, id_item)
            self.unit_table.setItem(i, 1, type_item)
            self.unit_table.setItem(i, 2, pos_item)
            self.unit_table.setItem(i, 3, status_item)
            self.unit_table.setItem(i, 4, obj_item)
            self.unit_table.setItem(i, 5, cohesion_item)
            self.unit_table.setItem(i, 6, power_item)
            
            # 设置行背景色 - 修复部分
            for col in range(self.unit_table.columnCount()):
                item = self.unit_table.item(i, col)
                if item:  # 确保item存在
                    if unit.army.id == 0:
                        item.setBackground(QColor(230, 240, 255))
                    else:
                        item.setBackground(QColor(255, 230, 230))
        
        # 调整列宽
        self.unit_table.resizeColumnsToContents()
    
    def updateCommandLog(self):
        """更新指挥命令日志"""
        if not self.simulation.army1 or not self.simulation.army2:
            return
        
        # 获取最新命令
        all_commands = []
        if self.simulation.army1.communication.command_history:
            all_commands.extend(self.simulation.army1.communication.command_history[-3:])
        if self.simulation.army2.communication.command_history:
            all_commands.extend(self.simulation.army2.communication.command_history[-3:])
        
        # 按时间排序
        all_commands.sort(key=lambda x: x['time'], reverse=True)
        
        # 显示最新命令
        for command in all_commands[:5]:  # 显示最新的5条命令
            self.command_log.add_command(command)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # 使用Fusion样式
    
    # 设置应用样式
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(240, 240, 240))
    palette.setColor(QPalette.WindowText, QColor(0, 0, 0))
    app.setPalette(palette)
    
    window = BattleSimulator()
    window.show()
    sys.exit(app.exec_())