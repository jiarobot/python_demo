import numpy as np
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from queue import PriorityQueue
import threading
import time
import random
import math
from scipy.spatial import KDTree
from datetime import datetime
import sys
import json
import csv
from pathlib import Path

# PyQt5 imports
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QComboBox, QSpinBox, QDoubleSpinBox, 
                             QGroupBox, QTabWidget, QTextEdit, QTableWidget, QTableWidgetItem,
                             QSlider, QCheckBox, QFileDialog, QMessageBox, QSplitter, QFrame)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QPalette

# ======================
# 增强版核心信念系统
# ======================
class EnhancedBeliefSystem:
    def __init__(self, passenger_id, destination, passenger_type="standard"):
        self.passenger_id = passenger_id
        self.destination = destination
        self.passenger_type = passenger_type  # standard, elderly, disabled, VIP
        
        # 根据乘客类型调整参数
        if passenger_type == "elderly":
            self.comfort_threshold = 0.9
            self.safety_margin = 2.0
            self.max_speed_factor = 0.7
        elif passenger_type == "disabled":
            self.comfort_threshold = 0.95
            self.safety_margin = 2.5
            self.max_speed_factor = 0.6
        elif passenger_type == "VIP":
            self.comfort_threshold = 0.85
            self.safety_margin = 2.0
            self.max_speed_factor = 0.8
        else:  # standard
            self.comfort_threshold = 0.8
            self.safety_margin = 1.5
            self.max_speed_factor = 1.0
            
        self.obstacle_history = {}
        self.other_bots_positions = {}
        self.update_beliefs()
    
    def update_beliefs(self, position=None, velocity=None, obstacles=None, other_bots=None):
        """根据传感器数据更新信念状态"""
        self.position = position if position is not None else np.array([0.0, 0.0])
        self.velocity = velocity if velocity is not None else np.array([0.0, 0.0])
        
        # 更新障碍物信息（带时间戳）
        current_time = time.time()
        if obstacles is not None:
            for obs in obstacles:
                obs_id = hash(tuple(obs))
                self.obstacle_history[obs_id] = (obs, current_time)
        
        # 清理过时的障碍物信息（5秒前）
        to_remove = [obs_id for obs_id, (obs, t) in self.obstacle_history.items() 
                    if current_time - t > 5.0]
        for obs_id in to_remove:
            del self.obstacle_history[obs_id]
            
        # 更新其他机器人位置
        if other_bots is not None:
            for bot_id, bot_pos, bot_vel in other_bots:
                self.other_bots_positions[bot_id] = (bot_pos, bot_vel, current_time)
        
        # 计算关键信念指标
        self.distance_to_dest = np.linalg.norm(self.destination - self.position)
        self.safety_status = self.calculate_safety()
        self.comfort_level = self.calculate_comfort()
        self.traffic_density = self.calculate_traffic_density()
        
    def calculate_safety(self):
        """计算安全系数(0-1)基于静态和动态障碍物"""
        if not self.obstacle_history:
            return 1.0
            
        min_dist = float('inf')
        for obs, t in self.obstacle_history.values():
            dist = np.linalg.norm(obs - self.position)
            if dist < min_dist:
                min_dist = dist
                
        # 考虑其他机器人的动态障碍
        for bot_id, (bot_pos, bot_vel, t) in self.other_bots_positions.items():
            dist = np.linalg.norm(bot_pos - self.position)
            if dist < min_dist:
                min_dist = dist
                
        return min(1.0, min_dist / self.safety_margin)
    
    def calculate_comfort(self):
        """计算舒适度(0-1)基于加速度和颠簸程度"""
        accel = np.linalg.norm(self.velocity)  # 简化计算
        comfort = 1.0 / (1.0 + 0.5 * accel)   # 加速度影响舒适度
        
        # 颠簸程度（基于方向变化率）
        if hasattr(self, 'prev_velocity'):
            dir_change = np.arccos(np.dot(self.velocity, self.prev_velocity) / 
                                  (np.linalg.norm(self.velocity) * np.linalg.norm(self.prev_velocity) + 1e-5))
            comfort *= 1.0 / (1.0 + 2.0 * dir_change)
        
        self.prev_velocity = self.velocity.copy()    
        return min(1.0, comfort * self.safety_status)
    
    def calculate_traffic_density(self):
        """计算周围交通密度(0-1)"""
        if not self.other_bots_positions:
            return 0.0
            
        nearby_bots = 0
        for bot_id, (bot_pos, bot_vel, t) in self.other_bots_positions.items():
            if np.linalg.norm(bot_pos - self.position) < 10.0:  # 10米范围内
                nearby_bots += 1
                
        return min(1.0, nearby_bots / 5.0)  # 最多考虑5个机器人

# ======================
# 增强版意图规划系统
# ======================
class EnhancedIntentPlanner:
    def __init__(self, belief_system):
        self.belief = belief_system
        self.path = []
        self.alternative_paths = []
        self.current_target = belief_system.destination
        self.last_replan_time = 0
        self.replan_interval = 2.0  # 重新规划间隔(秒)
        
    def plan_path(self, env_map, dynamic_obstacles=None):
        """A*路径规划算法，考虑动态障碍物"""
        current_time = time.time()
        if current_time - self.last_replan_time < self.replan_interval and self.path:
            return  # 不需要重新规划
            
        self.last_replan_time = current_time
        
        start = tuple(int(x) for x in self.belief.position)
        goal = tuple(int(x) for x in self.belief.destination)
        
        # 创建考虑动态障碍物的代价地图
        cost_map = self.create_cost_map(env_map, dynamic_obstacles)
        
        open_set = PriorityQueue()
        open_set.put((0, start))
        came_from = {}
        g_score = {start: 0}
        f_score = {start: np.linalg.norm(np.array(goal) - np.array(start))}
        
        while not open_set.empty():
            _, current = open_set.get()
            
            if current == goal:
                self.reconstruct_path(came_from, current)
                # 规划备选路径
                self.plan_alternative_paths(env_map, cost_map, came_from, goal)
                return
                
            for neighbor in self.get_neighbors(current, env_map):
                # 计算移动成本（考虑地形和动态障碍物）
                move_cost = 1.0 + cost_map[neighbor]
                
                tentative_g = g_score[current] + move_cost
                if neighbor not in g_score or tentative_g < g_score[neighbor]:
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g
                    f = tentative_g + np.linalg.norm(np.array(goal) - np.array(neighbor))
                    open_set.put((f, neighbor))
        
        # 未找到路径时使用直线路径
        self.path = [goal]
        
    def create_cost_map(self, env_map, dynamic_obstacles):
        """创建考虑动态障碍物的代价地图"""
        cost_map = np.zeros_like(env_map, dtype=float)
        
        # 静态障碍物有极高代价
        cost_map[env_map == 1] = 100.0
        
        # 动态障碍物增加代价
        if dynamic_obstacles:
            for obs_pos in dynamic_obstacles:
                x, y = int(obs_pos[0]), int(obs_pos[1])
                for dx in range(-2, 3):
                    for dy in range(-2, 3):
                        nx, ny = x + dx, y + dy
                        if 0 <= nx < env_map.shape[0] and 0 <= ny < env_map.shape[1]:
                            dist = np.sqrt(dx*dx + dy*dy)
                            cost = 10.0 / (dist + 1.0)
                            cost_map[nx, ny] += cost
        
        return cost_map
        
    def get_neighbors(self, pos, env_map):
        """获取可行走邻居节点"""
        neighbors = []
        for dx, dy in [(0,1), (1,0), (0,-1), (-1,0), (1,1), (-1,1), (1,-1), (-1,-1)]:
            nx, ny = pos[0] + dx, pos[1] + dy
            if 0 <= nx < env_map.shape[0] and 0 <= ny < env_map.shape[1]:
                if env_map[nx, ny] == 0:  # 0表示可通行
                    neighbors.append((nx, ny))
        return neighbors
        
    def reconstruct_path(self, came_from, current):
        """重建路径"""
        total_path = [current]
        while current in came_from:
            current = came_from[current]
            total_path.append(current)
        self.path = list(reversed(total_path))
        
    def plan_alternative_paths(self, env_map, cost_map, came_from, goal):
        """规划备选路径"""
        self.alternative_paths = []
        
        # 简单实现：对原路径进行微小变异
        if len(self.path) > 10:
            for i in range(3):  # 生成3条备选路径
                alt_path = self.path.copy()
                # 随机修改路径中的一些点
                for j in range(1, len(alt_path)-1):
                    if random.random() < 0.1:  # 10%的概率修改点
                        alt_path[j] = self.get_random_neighbor(alt_path[j], env_map)
                self.alternative_paths.append(alt_path)
        
    def get_random_neighbor(self, pos, env_map):
        """获取随机邻居节点"""
        neighbors = self.get_neighbors(pos, env_map)
        return random.choice(neighbors) if neighbors else pos
        
    def get_next_target(self):
        """获取下一个导航点"""
        if not self.path:
            return self.belief.destination
            
        # 找到最近的可达点
        min_idx = min(range(len(self.path)), 
                     key=lambda i: np.linalg.norm(np.array(self.path[i]) - self.belief.position))
        
        if min_idx + 1 < len(self.path):
            return np.array(self.path[min_idx + 1])
        return np.array(self.path[-1])
        
    def should_replan(self):
        """判断是否需要重新规划路径"""
        # 如果舒适度低且交通密度高，考虑重新规划
        if self.belief.comfort_level < 0.6 and self.belief.traffic_density > 0.7:
            return True
            
        # 如果长时间没有移动，考虑重新规划
        if hasattr(self, 'last_position'):
            if np.linalg.norm(self.belief.position - self.last_position) < 0.1:
                return time.time() - self.last_replan_time > 5.0
                
        self.last_position = self.belief.position.copy()
        return False

# ======================
# 增强版舒适控制器
# ======================
class EnhancedComfortController:
    def __init__(self, max_speed=5.0, max_accel=1.5, max_jerk=3.0):
        self.max_speed = max_speed
        self.max_accel = max_accel
        self.max_jerk = max_jerk
        self.prev_accel = np.array([0.0, 0.0])
        self.prev_velocity = np.array([0.0, 0.0])
        self.smooth_velocity = np.array([0.0, 0.0])
        
    def compute_velocity(self, current_vel, target_pos, current_pos, comfort_level, traffic_density, passenger_type):
        """计算满足舒适度要求的速度"""
        # 计算期望方向
        direction = target_pos - current_pos
        if np.linalg.norm(direction) < 0.1:
            return np.array([0.0, 0.0])
            
        direction = direction / np.linalg.norm(direction)
        
        # 基于舒适度和交通密度的速度调节
        speed_factor = comfort_level * (1.0 - 0.3 * traffic_density)
        
        # 根据乘客类型调整速度
        if passenger_type == "elderly":
            speed_factor *= 0.7
        elif passenger_type == "disabled":
            speed_factor *= 0.6
        elif passenger_type == "VIP":
            speed_factor *= 0.8
            
        target_speed = self.max_speed * speed_factor
        
        # 计算加速度限制
        current_accel_mag = np.linalg.norm(self.prev_accel)
        max_accel_mag = min(self.max_accel, current_accel_mag + self.max_jerk * 0.1)
        
        # 计算速度向量
        desired_vel = direction * target_speed
        delta_vel = desired_vel - current_vel
        
        # 应用加速度限制
        if np.linalg.norm(delta_vel) > max_accel_mag * 0.1:
            delta_vel = delta_vel / np.linalg.norm(delta_vel) * max_accel_mag * 0.1
            
        new_vel = current_vel + delta_vel
        
        # 应用平滑滤波
        alpha = 0.7  # 平滑系数
        self.smooth_velocity = alpha * self.smooth_velocity + (1 - alpha) * new_vel
        
        # 更新加速度记忆
        self.prev_accel = delta_vel / 0.1
        self.prev_velocity = current_vel
        
        return self.smooth_velocity

# ======================
# 增强版自主机器人主体
# ======================
class EnhancedBARbot:
    def __init__(self, bot_id, start_pos, destination, env_map, passenger_type="standard"):
        self.id = bot_id
        self.position = np.array(start_pos, dtype=float)
        self.velocity = np.array([0.0, 0.0])
        self.passenger_type = passenger_type
        self.belief_system = EnhancedBeliefSystem(bot_id, np.array(destination), passenger_type)
        self.intent_planner = EnhancedIntentPlanner(self.belief_system)
        self.controller = EnhancedComfortController()
        self.env_map = env_map
        self.path = []
        self.status = "Initializing"
        self.comfort_history = []
        self.safety_history = []
        self.traffic_history = []
        self.start_time = time.time()
        self.waiting_time = 0
        self.distance_traveled = 0
        self.last_position = self.position.copy()
        self.intent_planner.plan_path(env_map)
        
    def update(self, obstacles, all_bots):
        """更新机器人状态"""
        # 收集其他机器人信息
        other_bots_info = []
        for bot in all_bots:
            if bot != self:
                other_bots_info.append((bot.id, bot.position.copy(), bot.velocity.copy()))
        
        # 更新信念系统
        self.belief_system.update_beliefs(
            position=self.position,
            velocity=self.velocity,
            obstacles=obstacles,
            other_bots=other_bots_info
        )
        
        # 检查是否需要重新规划路径
        if self.intent_planner.should_replan():
            self.status = "Replanning"
            dynamic_obstacles = [bot.position for bot in all_bots if bot != self]
            self.intent_planner.plan_path(self.env_map, dynamic_obstacles)
        
        # 舒适度驱动的决策
        if self.belief_system.comfort_level < 0.5:
            self.status = "Adjusting for Comfort"
            # 舒适度过低时减速
            target_vel = self.velocity * 0.5
        elif self.belief_system.safety_status < 0.3:
            self.status = "Safety Critical"
            # 安全系数过低时紧急避让
            avoidance_vector = self.calculate_avoidance(obstacles, all_bots)
            target_vel = avoidance_vector * self.controller.max_speed * 0.3
        else:
            self.status = "Navigating"
            # 获取下一个目标点
            target_pos = self.intent_planner.get_next_target()
            # 计算满足舒适度的速度
            target_vel = self.controller.compute_velocity(
                self.velocity, 
                target_pos, 
                self.position,
                self.belief_system.comfort_level,
                self.belief_system.traffic_density,
                self.passenger_type
            )
        
        # 更新位置和速度
        self.velocity = target_vel
        new_position = self.position + self.velocity * 0.1  # 时间步0.1s
        
        # 更新行驶距离
        self.distance_traveled += np.linalg.norm(new_position - self.position)
        self.position = new_position
        
        # 记录历史数据
        self.comfort_history.append(self.belief_system.comfort_level)
        self.safety_history.append(self.belief_system.safety_status)
        self.traffic_history.append(self.belief_system.traffic_density)
        
        # 检查是否停滞
        if np.linalg.norm(self.position - self.last_position) < 0.01:
            self.waiting_time += 0.1
        else:
            self.waiting_time = 0
            
        self.last_position = self.position.copy()
        
        # 检查是否到达目的地
        if np.linalg.norm(self.position - self.belief_system.destination) < 0.5:
            self.status = "Arrived"
            self.velocity = np.array([0.0, 0.0])
            
        return self.position
        
    def calculate_avoidance(self, obstacles, all_bots):
        """计算避障方向"""
        # 简单实现：远离最近的障碍物
        nearest_obstacle = None
        min_dist = float('inf')
        
        # 检查静态障碍物
        for obs in obstacles:
            dist = np.linalg.norm(obs - self.position)
            if dist < min_dist:
                min_dist = dist
                nearest_obstacle = obs
                
        # 检查其他机器人
        for bot in all_bots:
            if bot != self:
                dist = np.linalg.norm(bot.position - self.position)
                if dist < min_dist:
                    min_dist = dist
                    nearest_obstacle = bot.position
        
        if nearest_obstacle is not None and min_dist < 2.0:
            # 计算远离方向
            avoid_direction = self.position - nearest_obstacle
            if np.linalg.norm(avoid_direction) > 0:
                return avoid_direction / np.linalg.norm(avoid_direction)
        
        # 默认继续前进
        if np.linalg.norm(self.velocity) > 0:
            return self.velocity / np.linalg.norm(self.velocity)
        else:
            return np.array([1.0, 0.0])
        
    def get_performance_metrics(self):
        """获取性能指标"""
        travel_time = time.time() - self.start_time
        avg_comfort = np.mean(self.comfort_history) if self.comfort_history else 0
        avg_safety = np.mean(self.safety_history) if self.safety_history else 0
        efficiency = self.distance_traveled / travel_time if travel_time > 0 else 0
        
        return {
            "travel_time": travel_time,
            "distance_traveled": self.distance_traveled,
            "avg_comfort": avg_comfort,
            "avg_safety": avg_safety,
            "waiting_time": self.waiting_time,
            "efficiency": efficiency
        }

# ======================
# 增强版交通管理系统
# ======================
class EnhancedTrafficManagementSystem:
    def __init__(self, env_size=(50, 50)):
        self.env_size = env_size
        self.env_map = self.generate_environment()
        self.bots = []
        self.obstacles = self.generate_obstacles()
        self.intersections = self.identify_intersections()
        self.heatmap = np.zeros(env_size)
        self.emergency_mode = False
        self.weather_impact = 1.0  # 1.0 = 正常, <1.0 = 恶劣天气
        self.simulation_speed = 1.0
        self.paused = False
        self.log = []
        
    def generate_environment(self):
        """生成环境地图 (0=可通行, 1=障碍)"""
        env_map = np.zeros(self.env_size)
        # 添加边界障碍
        env_map[0, :] = 1
        env_map[-1, :] = 1
        env_map[:, 0] = 1
        env_map[:, -1] = 1
        
        # 添加随机障碍
        for _ in range(30):
            x, y = random.randint(5, self.env_size[0]-6), random.randint(5, self.env_size[1]-6)
            w, h = random.randint(2, 5), random.randint(2, 5)
            env_map[x:x+w, y:y+h] = 1
            
        # 添加一些通道和房间
        self.add_corridors_and_rooms(env_map)
        
        return env_map
    
    def add_corridors_and_rooms(self, env_map):
        """添加走廊和房间结构"""
        # 添加横向走廊
        for i in range(10, self.env_size[0]-10, 15):
            env_map[i, 5:self.env_size[1]-5] = 0
            env_map[i:i+3, 5:self.env_size[1]-5] = 0
            
        # 添加纵向走廊
        for j in range(10, self.env_size[1]-10, 15):
            env_map[5:self.env_size[0]-5, j] = 0
            env_map[5:self.env_size[0]-5, j:j+3] = 0
            
        # 添加房间
        room_positions = [(8,8), (8,25), (25,8), (25,25)]
        for x, y in room_positions:
            env_map[x:x+10, y:y+10] = 0
            # 添加门口
            env_map[x+4:x+6, y+10] = 0
            env_map[x+10, y+4:y+6] = 0
    
    def generate_obstacles(self):
        """生成障碍物位置"""
        obstacles = []
        for i in range(self.env_size[0]):
            for j in range(self.env_size[1]):
                if self.env_map[i, j] == 1:
                    obstacles.append(np.array([i, j]))
        return obstacles
    
    def identify_intersections(self):
        """识别关键交叉点"""
        intersections = []
        for i in range(5, self.env_size[0]-5, 5):
            for j in range(5, self.env_size[1]-5, 5):
                # 检查是否是交叉点（四个方向都有通路）
                if (self.env_map[i, j] == 0 and 
                    self.env_map[i+1, j] == 0 and self.env_map[i-1, j] == 0 and
                    self.env_map[i, j+1] == 0 and self.env_map[i, j-1] == 0):
                    intersections.append(np.array([i, j]))
        return intersections
    
    def add_passenger(self, start, destination, passenger_type="standard"):
        """添加乘客运输任务"""
        bot_id = len(self.bots) + 1
        new_bot = EnhancedBARbot(bot_id, start, destination, self.env_map, passenger_type)
        self.bots.append(new_bot)
        self.log_event(f"添加机器人 {bot_id} ({passenger_type}), 起点: {start}, 终点: {destination}")
        return new_bot
    
    def remove_passenger(self, bot_id):
        """移除乘客运输任务"""
        for i, bot in enumerate(self.bots):
            if bot.id == bot_id:
                self.bots.pop(i)
                self.log_event(f"移除机器人 {bot_id}")
                return True
        return False
    
    def set_weather_impact(self, impact_factor):
        """设置天气影响系数"""
        self.weather_impact = max(0.1, min(1.0, impact_factor))
        self.log_event(f"设置天气影响系数: {impact_factor}")
        
    def set_emergency_mode(self, enabled):
        """设置紧急模式"""
        self.emergency_mode = enabled
        status = "开启" if enabled else "关闭"
        self.log_event(f"紧急模式{status}")
        
    def set_simulation_speed(self, speed):
        """设置仿真速度"""
        self.simulation_speed = speed
        self.log_event(f"设置仿真速度: {speed}x")
        
    def toggle_pause(self):
        """切换暂停状态"""
        self.paused = not self.paused
        status = "暂停" if self.paused else "继续"
        self.log_event(f"仿真{status}")
        
    def reset(self):
        """重置仿真"""
        self.bots = []
        self.heatmap = np.zeros(self.env_size)
        self.log_event("仿真重置")
        
    def log_event(self, message):
        """记录事件日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log.append(f"[{timestamp}] {message}")
        if len(self.log) > 1000:  # 限制日志长度
            self.log.pop(0)
            
    def coordinate_movement(self):
        """协调机器人运动"""
        # 更新热图
        for bot in self.bots:
            x, y = int(bot.position[0]), int(bot.position[1])
            if 0 <= x < self.env_size[0] and 0 <= y < self.env_size[1]:
                self.heatmap[x, y] += 1
        
        # 冲突避免策略
        for i, bot in enumerate(self.bots):
            if bot.status == "Arrived":
                continue
                
            # 检查与其他机器人的距离
            for other in self.bots[i+1:]:
                if other.status == "Arrived":
                    continue
                    
                dist = np.linalg.norm(bot.position - other.position)
                if dist < 2.0:  # 安全距离
                    # 基于优先级和舒适度的决策
                    bot_priority = self.get_priority(bot)
                    other_priority = self.get_priority(other)
                    
                    if bot_priority > other_priority:
                        other.velocity *= 0.7
                    elif other_priority > bot_priority:
                        bot.velocity *= 0.7
                    else:
                        # 相同优先级时，舒适度低的让行
                        if bot.belief_system.comfort_level > other.belief_system.comfort_level:
                            other.velocity *= 0.7
                        else:
                            bot.velocity *= 0.7
                            
                    # 紧急模式下，所有机器人为VIP让行
                    if self.emergency_mode:
                        if bot.passenger_type == "VIP":
                            other.velocity *= 0.5
                        elif other.passenger_type == "VIP":
                            bot.velocity *= 0.5
    
    def get_priority(self, bot):
        """获取机器人优先级"""
        if self.emergency_mode:
            if bot.passenger_type == "VIP":
                return 3
            elif bot.passenger_type == "disabled":
                return 2
            elif bot.passenger_type == "elderly":
                return 1
                
        # 正常模式下，所有乘客优先级相同
        return 0

    def update(self):
        """更新所有机器人状态"""
        if self.paused:
            return
            
        for bot in self.bots:
            if bot.status != "Arrived":
                bot.update(self.obstacles, self.bots)
        self.coordinate_movement()
        
    def get_traffic_report(self):
        """获取交通报告"""
        active_bots = [bot for bot in self.bots if bot.status != "Arrived"]
        arrived_bots = [bot for bot in self.bots if bot.status == "Arrived"]
        avg_comfort = np.mean([bot.belief_system.comfort_level for bot in active_bots]) if active_bots else 0
        avg_safety = np.mean([bot.belief_system.safety_status for bot in active_bots]) if active_bots else 0
        
        return {
            "total_robots": len(self.bots),
            "active_robots": len(active_bots),
            "arrived_robots": len(arrived_bots),
            "avg_comfort": avg_comfort,
            "avg_safety": avg_safety,
            "congestion_level": np.sum(self.heatmap > 0) / (self.env_size[0] * self.env_size[1]),
            "emergency_mode": self.emergency_mode,
            "weather_impact": self.weather_impact,
            "simulation_speed": self.simulation_speed,
            "paused": self.paused
        }
    
    def export_data(self, filename):
        """导出数据到CSV文件"""
        try:
            with open(filename, 'w', newline='') as csvfile:
                fieldnames = ['bot_id', 'passenger_type', 'travel_time', 'distance_traveled', 
                             'avg_comfort', 'avg_safety', 'waiting_time', 'efficiency']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                for bot in self.bots:
                    metrics = bot.get_performance_metrics()
                    writer.writerow({
                        'bot_id': bot.id,
                        'passenger_type': bot.passenger_type,
                        'travel_time': metrics['travel_time'],
                        'distance_traveled': metrics['distance_traveled'],
                        'avg_comfort': metrics['avg_comfort'],
                        'avg_safety': metrics['avg_safety'],
                        'waiting_time': metrics['waiting_time'],
                        'efficiency': metrics['efficiency']
                    })
            return True
        except Exception as e:
            return False

# ======================
# PyQt可视化界面
# ======================
class MplCanvas(FigureCanvas):
    def __init__(self, parent=None, width=8, height=8, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_subplot(111)
        super(MplCanvas, self).__init__(self.fig)
        self.setParent(parent)
        
        # 设置中文字体
        plt.rcParams['font.sans-serif'] = ['Microsoft YaHei']
        plt.rcParams['axes.unicode_minus'] = False

class SimulationThread(QThread):
    update_signal = pyqtSignal()
    
    def __init__(self, traffic_system):
        super().__init__()
        self.traffic_system = traffic_system
        self.running = True
        
    def run(self):
        while self.running:
            if not self.traffic_system.paused:
                self.traffic_system.update()
                self.update_signal.emit()
            time.sleep(0.1 / self.traffic_system.simulation_speed)
            
    def stop(self):
        self.running = False

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.traffic_system = EnhancedTrafficManagementSystem(env_size=(40, 40))
        self.initUI()
        self.initSimulation()
        
    def initUI(self):
        self.setWindowTitle("增强版信念自主机器人运输系统")
        self.setGeometry(100, 100, 1600, 900)
        
        # 创建中心部件和主布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # 创建左侧控制面板
        control_panel = QFrame()
        control_panel.setMaximumWidth(350)
        control_panel.setFrameStyle(QFrame.StyledPanel)
        control_layout = QVBoxLayout(control_panel)
        
        # 创建控制面板的选项卡
        control_tabs = QTabWidget()
        
        # 仿真控制选项卡
        sim_control_tab = QWidget()
        sim_control_layout = QVBoxLayout(sim_control_tab)
        
        # 仿真速度控制
        speed_group = QGroupBox("仿真速度")
        speed_layout = QVBoxLayout(speed_group)
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setMinimum(1)
        self.speed_slider.setMaximum(10)
        self.speed_slider.setValue(5)
        self.speed_slider.valueChanged.connect(self.change_simulation_speed)
        speed_layout.addWidget(QLabel("速度: 1x - 10x"))
        speed_layout.addWidget(self.speed_slider)
        sim_control_layout.addWidget(speed_group)
        
        # 环境控制
        env_group = QGroupBox("环境设置")
        env_layout = QVBoxLayout(env_group)
        
        weather_layout = QHBoxLayout()
        weather_layout.addWidget(QLabel("天气影响:"))
        self.weather_slider = QSlider(Qt.Horizontal)
        self.weather_slider.setMinimum(1)
        self.weather_slider.setMaximum(10)
        self.weather_slider.setValue(8)
        self.weather_slider.valueChanged.connect(self.change_weather)
        weather_layout.addWidget(self.weather_slider)
        env_layout.addLayout(weather_layout)
        
        self.emergency_check = QCheckBox("紧急模式")
        self.emergency_check.stateChanged.connect(self.toggle_emergency)
        env_layout.addWidget(self.emergency_check)
        
        sim_control_layout.addWidget(env_group)
        
        # 控制按钮
        button_layout = QHBoxLayout()
        self.start_button = QPushButton("开始")
        self.start_button.clicked.connect(self.start_simulation)
        button_layout.addWidget(self.start_button)
        
        self.pause_button = QPushButton("暂停")
        self.pause_button.clicked.connect(self.pause_simulation)
        button_layout.addWidget(self.pause_button)
        
        self.reset_button = QPushButton("重置")
        self.reset_button.clicked.connect(self.reset_simulation)
        button_layout.addWidget(self.reset_button)
        
        sim_control_layout.addLayout(button_layout)
        
        # 机器人管理选项卡
        bot_control_tab = QWidget()
        bot_control_layout = QVBoxLayout(bot_control_tab)
        
        # 添加机器人表单
        add_bot_group = QGroupBox("添加机器人")
        add_bot_layout = QVBoxLayout(add_bot_group)
        
        # 乘客类型选择
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("乘客类型:"))
        self.passenger_type = QComboBox()
        self.passenger_type.addItems(["standard", "elderly", "disabled", "VIP"])
        type_layout.addWidget(self.passenger_type)
        add_bot_layout.addLayout(type_layout)
        
        # 起点坐标
        start_layout = QHBoxLayout()
        start_layout.addWidget(QLabel("起点 X:"))
        self.start_x = QSpinBox()
        self.start_x.setMinimum(1)
        self.start_x.setMaximum(38)
        self.start_x.setValue(5)
        start_layout.addWidget(self.start_x)
        
        start_layout.addWidget(QLabel("Y:"))
        self.start_y = QSpinBox()
        self.start_y.setMinimum(1)
        self.start_y.setMaximum(38)
        self.start_y.setValue(5)
        start_layout.addWidget(self.start_y)
        add_bot_layout.addLayout(start_layout)
        
        # 终点坐标
        dest_layout = QHBoxLayout()
        dest_layout.addWidget(QLabel("终点 X:"))
        self.dest_x = QSpinBox()
        self.dest_x.setMinimum(1)
        self.dest_x.setMaximum(38)
        self.dest_x.setValue(35)
        dest_layout.addWidget(self.dest_x)
        
        dest_layout.addWidget(QLabel("Y:"))
        self.dest_y = QSpinBox()
        self.dest_y.setMinimum(1)
        self.dest_y.setMaximum(38)
        self.dest_y.setValue(35)
        dest_layout.addWidget(self.dest_y)
        add_bot_layout.addLayout(dest_layout)
        
        add_bot_button = QPushButton("添加机器人")
        add_bot_button.clicked.connect(self.add_bot)
        add_bot_layout.addWidget(add_bot_button)
        
        bot_control_layout.addWidget(add_bot_group)
        
        # 机器人列表
        bot_list_group = QGroupBox("机器人列表")
        bot_list_layout = QVBoxLayout(bot_list_group)
        
        self.bot_table = QTableWidget()
        self.bot_table.setColumnCount(5)
        self.bot_table.setHorizontalHeaderLabels(["ID", "类型", "状态", "位置", "操作"])
        bot_list_layout.addWidget(self.bot_table)
        
        bot_control_layout.addWidget(bot_list_group)
        
        # 数据导出选项卡
        data_tab = QWidget()
        data_layout = QVBoxLayout(data_tab)
        
        export_group = QGroupBox("数据导出")
        export_layout = QVBoxLayout(export_group)
        
        self.export_button = QPushButton("导出数据到CSV")
        self.export_button.clicked.connect(self.export_data)
        export_layout.addWidget(self.export_button)
        
        data_layout.addWidget(export_group)
        
        # 添加选项卡
        control_tabs.addTab(sim_control_tab, "仿真控制")
        control_tabs.addTab(bot_control_tab, "机器人管理")
        control_tabs.addTab(data_tab, "数据导出")
        
        control_layout.addWidget(control_tabs)
        
        # 状态信息
        status_group = QGroupBox("状态信息")
        status_layout = QVBoxLayout(status_group)
        self.status_text = QTextEdit()
        self.status_text.setMaximumHeight(150)
        status_layout.addWidget(self.status_text)
        control_layout.addWidget(status_group)
        
        # 创建右侧可视化区域
        viz_splitter = QSplitter(Qt.Vertical)
        
        # 主地图可视化
        self.map_canvas = MplCanvas(self, width=10, height=10, dpi=100)
        self.init_map_visualization()
        
        # 性能图表
        self.chart_canvas = MplCanvas(self, width=10, height=5, dpi=100)
        self.init_performance_chart()
        
        viz_splitter.addWidget(self.map_canvas)
        viz_splitter.addWidget(self.chart_canvas)
        viz_splitter.setSizes([600, 300])
        
        # 添加到主布局
        main_layout.addWidget(control_panel)
        main_layout.addWidget(viz_splitter)
        
        # 状态栏
        self.statusBar().showMessage("就绪")
        
        # 更新定时器
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_visualization)
        self.update_timer.start(100)  # 每100毫秒更新一次
        
    def initSimulation(self):
        # 添加初始机器人
        self.traffic_system.add_passenger(start=[5, 5], destination=[35, 35], passenger_type="standard")
        self.traffic_system.add_passenger(start=[5, 35], destination=[35, 5], passenger_type="elderly")
        self.traffic_system.add_passenger(start=[20, 5], destination=[20, 35], passenger_type="disabled")
        self.traffic_system.add_passenger(start=[35, 20], destination=[5, 20], passenger_type="VIP")
        
        # 启动仿真线程
        self.sim_thread = SimulationThread(self.traffic_system)
        self.sim_thread.update_signal.connect(self.update_visualization)
        self.sim_thread.start()
        
    def init_map_visualization(self):
        ax = self.map_canvas.axes
        ax.clear()
        
        # 绘制地图障碍物
        obstacles_x = [obs[0] for obs in self.traffic_system.obstacles]
        obstacles_y = [obs[1] for obs in self.traffic_system.obstacles]
        ax.scatter(obstacles_x, obstacles_y, c='black', s=50, marker='s', alpha=0.5, label='障碍物')
        
        # 绘制交叉点
        int_x = [intr[0] for intr in self.traffic_system.intersections]
        int_y = [intr[1] for intr in self.traffic_system.intersections]
        ax.scatter(int_x, int_y, c='yellow', s=30, marker='*', alpha=0.7, label='交通节点')
        
        ax.set_xlim(0, self.traffic_system.env_size[0])
        ax.set_ylim(0, self.traffic_system.env_size[1])
        ax.set_title("增强版信念自主机器人运输系统")
        ax.legend()
        
        self.map_canvas.draw()
        
    def init_performance_chart(self):
        ax = self.chart_canvas.axes
        ax.clear()
        ax.set_title("性能指标")
        ax.set_ylim(0, 1)
        ax.set_xlabel("时间步")
        ax.set_ylabel("数值")
        self.chart_canvas.draw()
        
    def update_visualization(self):
        # 更新地图可视化
        ax = self.map_canvas.axes
        ax.clear()
        
        # 绘制地图障碍物
        obstacles_x = [obs[0] for obs in self.traffic_system.obstacles]
        obstacles_y = [obs[1] for obs in self.traffic_system.obstacles]
        ax.scatter(obstacles_x, obstacles_y, c='black', s=50, marker='s', alpha=0.5, label='障碍物')
        
        # 绘制交叉点
        int_x = [intr[0] for intr in self.traffic_system.intersections]
        int_y = [intr[1] for intr in self.traffic_system.intersections]
        ax.scatter(int_x, int_y, c='yellow', s=30, marker='*', alpha=0.7, label='交通节点')
        
        # 绘制机器人
        bot_colors = []
        bot_positions_x = []
        bot_positions_y = []
        
        for bot in self.traffic_system.bots:
            bot_positions_x.append(bot.position[0])
            bot_positions_y.append(bot.position[1])
            
            # 根据状态选择颜色
            if bot.status == "Arrived":
                bot_colors.append('blue')
            elif bot.status == "Safety Critical":
                bot_colors.append('red')
            elif bot.status == "Adjusting for Comfort":
                bot_colors.append('orange')
            elif bot.status == "Replanning":
                bot_colors.append('purple')
            else:
                # 基于舒适度的颜色
                if bot.belief_system.comfort_level > 0.7:
                    bot_colors.append('green')
                elif bot.belief_system.comfort_level > 0.4:
                    bot_colors.append('yellow')
                else:
                    bot_colors.append('orange')
        
        # 绘制机器人位置
        ax.scatter(bot_positions_x, bot_positions_y, c=bot_colors, s=120, edgecolors='black')
        
        # 绘制目的地
        for bot in self.traffic_system.bots:
            ax.scatter(bot.belief_system.destination[0], bot.belief_system.destination[1], 
                      c='purple', s=200, marker='*', alpha=0.8)
        
        # 绘制热图
        heatmap_img = ax.imshow(self.traffic_system.heatmap.T, 
                               cmap='hot', alpha=0.3, 
                               extent=[0, self.traffic_system.env_size[0], 
                                       0, self.traffic_system.env_size[1]],
                               origin='lower')
        
        ax.set_xlim(0, self.traffic_system.env_size[0])
        ax.set_ylim(0, self.traffic_system.env_size[1])
        ax.set_title("增强版信念自主机器人运输系统")
        ax.legend()
        
        self.map_canvas.draw()
        
        # 更新性能图表
        self.update_performance_chart()
        
        # 更新状态信息
        self.update_status_info()
        
        # 更新机器人表格
        self.update_bot_table()
        
    def update_performance_chart(self):
        ax = self.chart_canvas.axes
        ax.clear()
        
        # 绘制舒适度和安全系数历史
        for i, bot in enumerate(self.traffic_system.bots):
            if len(bot.comfort_history) > 0:
                steps = range(len(bot.comfort_history))
                ax.plot(steps, bot.comfort_history, label=f'Bot {bot.id} 舒适度')
                ax.plot(steps, bot.safety_history, label=f'Bot {bot.id} 安全系数', linestyle='--')
        
        ax.set_title("性能指标")
        ax.set_ylim(0, 1)
        ax.set_xlabel("时间步")
        ax.set_ylabel("数值")
        ax.legend()
        
        self.chart_canvas.draw()
        
    def update_status_info(self):
        report = self.traffic_system.get_traffic_report()
        status_text = f"机器人总数: {report['total_robots']} | " \
                     f"活跃机器人: {report['active_robots']} | " \
                     f"已到达: {report['arrived_robots']}\n" \
                     f"平均舒适度: {report['avg_comfort']:.2f} | " \
                     f"平均安全系数: {report['avg_safety']:.2f} | " \
                     f"拥堵程度: {report['congestion_level']:.2f}\n" \
                     f"仿真速度: {report['simulation_speed']}x | " \
                     f"天气影响: {report['weather_impact']:.1f}"
        
        if report['emergency_mode']:
            status_text += " | 紧急模式: 开启"
        else:
            status_text += " | 紧急模式: 关闭"
            
        if report['paused']:
            status_text += " | 状态: 暂停"
        else:
            status_text += " | 状态: 运行中"
            
        self.status_text.setPlainText(status_text)
        self.statusBar().showMessage(status_text)
        
    def update_bot_table(self):
        self.bot_table.setRowCount(len(self.traffic_system.bots))
        
        for i, bot in enumerate(self.traffic_system.bots):
            # ID列
            self.bot_table.setItem(i, 0, QTableWidgetItem(str(bot.id)))
            
            # 类型列
            self.bot_table.setItem(i, 1, QTableWidgetItem(bot.passenger_type))
            
            # 状态列
            self.bot_table.setItem(i, 2, QTableWidgetItem(bot.status))
            
            # 位置列
            pos_text = f"({bot.position[0]:.1f}, {bot.position[1]:.1f})"
            self.bot_table.setItem(i, 3, QTableWidgetItem(pos_text))
            
            # 操作列
            remove_btn = QPushButton("移除")
            remove_btn.clicked.connect(lambda checked, id=bot.id: self.remove_bot(id))
            self.bot_table.setCellWidget(i, 4, remove_btn)
            
    def change_simulation_speed(self, value):
        self.traffic_system.set_simulation_speed(value)
        
    def change_weather(self, value):
        impact = value / 10.0
        self.traffic_system.set_weather_impact(impact)
        
    def toggle_emergency(self, state):
        self.traffic_system.set_emergency_mode(state == Qt.Checked)
        
    def start_simulation(self):
        self.traffic_system.paused = False
        
    def pause_simulation(self):
        self.traffic_system.paused = True
        
    def reset_simulation(self):
        self.traffic_system.reset()
        self.init_map_visualization()
        self.init_performance_chart()
        
    def add_bot(self):
        start = [self.start_x.value(), self.start_y.value()]
        destination = [self.dest_x.value(), self.dest_y.value()]
        passenger_type = self.passenger_type.currentText()
        
        self.traffic_system.add_passenger(start, destination, passenger_type)
        
    def remove_bot(self, bot_id):
        self.traffic_system.remove_passenger(bot_id)
        
    def export_data(self):
        options = QFileDialog.Options()
        filename, _ = QFileDialog.getSaveFileName(
            self, "导出数据", "", "CSV Files (*.csv)", options=options)
        
        if filename:
            success = self.traffic_system.export_data(filename)
            if success:
                QMessageBox.information(self, "成功", "数据已成功导出")
            else:
                QMessageBox.warning(self, "错误", "数据导出失败")
                
    def closeEvent(self, event):
        self.sim_thread.stop()
        self.sim_thread.wait()
        event.accept()

# ======================
# 主程序
# ======================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())