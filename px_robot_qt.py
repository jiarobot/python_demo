import sys
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QGroupBox, QPushButton, QLabel, QSlider, QComboBox, QListWidget,
                             QTabWidget, QStatusBar, QSplitter, QDoubleSpinBox, QCheckBox)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QPalette, QColor
from mpl_toolkits.mplot3d import Axes3D
from scipy.integrate import solve_ivp
from scipy.spatial.transform import Rotation as R
from scipy.spatial import KDTree
import matplotlib.animation as animation
import time
import pickle
import json
from datetime import datetime
import matplotlib
matplotlib.rc("font", family='Microsoft YaHei')

# ==================== 核心无人机模型 ====================
class Drone:
    def __init__(self, drone_id, config):
        # 物理参数
        self.id = drone_id
        self.m = config.get('mass', 1.2)
        self.g = 9.80665
        self.I = np.diag(config.get('inertia', [0.015, 0.015, 0.025]))
        self.l = config.get('arm_length', 0.25)
        self.kf = config.get('thrust_coeff', 8.5e-6)
        self.km = config.get('torque_coeff', 1.5e-7)
        self.c_drag = config.get('drag_coeff', 0.1)
        self.max_rpm = config.get('max_rpm', 15000)
        self.battery_capacity = config.get('battery', 2200)  # mAh
        self.payload = config.get('payload', 0.2)  # kg
        
        # 状态变量 [x, y, z, vx, vy, vz, qw, qx, qy, qz, p, q, r]
        self.state = np.zeros(13)
        self.state[6] = 1.0  # 四元数初始值
        
        # 控制器参数
        self.controller_type = config.get('controller', 'PID')
        self.controller_params = config.get('controller_params', {})
        
        # 传感器
        self.sensors = {
            'gps': {'noise': 0.02, 'update_rate': 10},
            'imu': {'noise': 0.005, 'update_rate': 100},
            'baro': {'noise': 0.1, 'update_rate': 20},
            'lidar': {'range': 20.0, 'fov': 120, 'resolution': 1.0},
            'camera': {'fov': 90, 'resolution': (640, 480)}
        }
        
        # 通信
        self.comms = {
            'range': 100.0,  # 米
            'bandwidth': 10,  # Mbps
            'latency': 0.1  # 秒
        }
        
        # 数据记录
        self.log = []
        self.control_history = []
        self.energy_consumed = 0.0
        self.communication_log = []
        self.sensor_data = []
        self.status = "IDLE"
        self.last_update = 0.0
        self.battery_level = 100.0  # 百分比
        
    def set_initial_state(self, pos, vel=None, att=None):
        self.state[0:3] = pos
        if vel is not None:
            self.state[3:6] = vel
        if att is not None:
            r = R.from_euler('zyx', att, degrees=True)
            self.state[6:10] = r.as_quat()
    
    def update_dynamics(self, t, dt, control_input, environment):
        """更新无人机动力学状态"""
        # 解包状态变量
        x, y, z, vx, vy, vz, qw, qx, qy, qz, p, q, r = self.state
        
        # === 改进数值稳定性 ===
        # 1. 限制控制输入范围
        control_input = np.clip(control_input, 0, self.max_rpm)
        
        # === 更健壮的四元数处理 ===
        # 创建当前旋转矩阵前的保护
        quat = np.array([qx, qy, qz, qw])
        quat_norm = np.linalg.norm(quat)
        
        if quat_norm < 1e-8:
            # 使用单位四元数作为后备
            rot = R.from_quat([0, 0, 0, 1])
        else:
            # 归一化四元数
            quat_normalized = quat / quat_norm
            try:
                # 正常计算当前旋转矩阵
                rot = R.from_quat(quat_normalized)
            except:
                # 如果创建失败，使用单位四元数
                rot = R.from_quat([0, 0, 0, 1])
        
        R_matrix = rot.as_matrix()
        
        # 平移动力学
        Fg = np.array([0, 0, -self.m * self.g])  # 重力
        
        # 空气阻力
        vel = np.array([vx, vy, vz])
        F_drag = -self.c_drag * np.linalg.norm(vel) * vel
        
        # 风扰
        wind = environment.get_wind(t, np.array([x, y, z]))
        wind_force = wind * 0.1  # 风对机体的影响系数
        
        # 环境力 (如热气流)
        env_force = environment.get_environmental_force(t, np.array([x, y, z]))
        Tb = np.array([0, 0, self.kf * np.sum(control_input**2)])
        F_total = R_matrix @ Tb + Fg + F_drag + wind_force + env_force
        dvdt = F_total / self.m
        
        # 姿态动力学
        tau = np.array([
            self.l * self.kf * (control_input[1]**2 - control_input[3]**2),
            self.l * self.kf * (control_input[2]**2 - control_input[0]**2),
            self.km * (control_input[0]**2 - control_input[1]**2 + control_input[2]**2 - control_input[3]**2)
        ])
        
        omega = np.array([p, q, r])
        domega_dt = np.linalg.inv(self.I) @ (tau - np.cross(omega, self.I @ omega))
        
        # 四元数运动学
        quat = np.array([qw, qx, qy, qz])
        omega_quat = np.array([0, p, q, r])
        dqdt = 0.5 * self.quaternion_multiply(quat, omega_quat)
        
        # === 改进数值稳定性 ===
        # 2. 限制角速度范围
        max_ang_vel = 20.0  # 最大角速度 (rad/s)
        omega = np.clip(omega, -max_ang_vel, max_ang_vel)
        
        # 3. 限制四元数更新步长
        max_dq = 1.0  # 最大四元数变化量
        dqdt = np.clip(dqdt, -max_dq, max_dq)
        
        # 更新状态 (欧拉积分)
        self.state[0] += vx * dt
        self.state[1] += vy * dt
        self.state[2] += vz * dt
        self.state[3] += dvdt[0] * dt
        self.state[4] += dvdt[1] * dt
        self.state[5] += dvdt[2] * dt
        self.state[6] += dqdt[0] * dt
        self.state[7] += dqdt[1] * dt
        self.state[8] += dqdt[2] * dt
        self.state[9] += dqdt[3] * dt
        self.state[10] += domega_dt[0] * dt
        self.state[11] += domega_dt[1] * dt
        self.state[12] += domega_dt[2] * dt
        
        # 5. 归一化前检查NaN值
        if not np.all(np.isfinite(self.state)):
            print(f"警告：无人机 {self.id} 状态包含非有限值，重置为安全状态")
            # 保留位置但重置其他状态
            safe_pos = np.nan_to_num(self.state[0:3], nan=0.0, posinf=100.0, neginf=-100.0)
            self.state = np.zeros(13)
            self.state[0:3] = safe_pos
            self.state[6] = 1.0  # 重置四元数
        if np.any(np.isnan(self.state[6:10])):
            self.state[6:10] = np.array([1.0, 0.0, 0.0, 0.0])
        
        # 归一化四元数并防止零模长
        quat = self.state[6:10]
        if np.any(np.isnan(quat)) or np.linalg.norm(quat) < 1e-8:
            quat = np.array([1.0, 0.0, 0.0, 0.0])  # 单位四元数
        else:
            quat = quat / np.linalg.norm(quat)  # 确保归一化
        
        try:
            rot = R.from_quat(quat)
            rpy = rot.as_euler('zyx', degrees=True)[::-1]
        except:
            rot = R.from_quat([1.0, 0.0, 0.0, 0.0])
            rpy = [0, 0, 0]
        
        # 记录状态
        self.log.append((t, self.state.copy()))
        self.control_history.append((t, control_input.copy()))
        
        # 更新能量消耗
        power = np.sum(control_input**3) * 1e-6  # 功率近似 (W)
        self.energy_consumed += power * dt / 3600  # Wh
        self.battery_level = max(0, 100 - (self.energy_consumed / (self.battery_capacity / 1000)) * 100)
        
        # 更新状态
        self.last_update = t
        
    def quaternion_multiply(self, q1, q2):
        w1, x1, y1, z1 = q1
        w2, x2, y2, z2 = q2
        return np.array([
            w1*w2 - x1*x2 - y1*y2 - z1*z2,
            w1*x2 + x1*w2 + y1*z2 - z1*y2,
            w1*y2 - x1*z2 + y1*w2 + z1*x2,
            w1*z2 + x1*y2 - y1*x2 + z1*w2
        ])
    
    def get_sensor_data(self, t, environment):
        """获取带噪声的传感器数据"""
        # 真实状态
        pos = self.state[0:3]
        vel = self.state[3:6]
        quat = self.state[6:10]
        omega = self.state[10:13]
        
        # 添加噪声
        noisy_pos = pos + np.random.normal(0, self.sensors['gps']['noise'], 3)
        noisy_vel = vel + np.random.normal(0, self.sensors['gps']['noise']/2, 3)
        noisy_omega = omega + np.random.normal(0, self.sensors['imu']['noise'], 3)
        noisy_alt = pos[2] + np.random.normal(0, self.sensors['baro']['noise'])
        
        # === 更健壮的四元数处理 ===
        # 检查NaN值
        if np.any(np.isnan(quat)):
            quat = np.array([1.0, 0.0, 0.0, 0.0])
        
        quat_norm = np.linalg.norm(quat)
        
        # 处理零模长和接近零模长的情况
        if quat_norm < 1e-8:
            rot = R.from_quat([1.0, 0.0, 0.0, 0.0])
            rpy = [0, 0, 0]
        else:
            quat_normalized = quat / quat_norm
            
            # 再次检查归一化后的模长
            normalized_norm = np.linalg.norm(quat_normalized)
            if normalized_norm < 1e-8:
                rot = R.from_quat([1.0, 0.0, 0.0, 0.0])
                rpy = [0, 0, 0]
            else:
                try:
                    rot = R.from_quat(quat_normalized)
                    rpy = rot.as_euler('zyx', degrees=True)[::-1]
                except:
                    # 如果创建旋转对象失败，使用默认值
                    rot = R.from_quat([1.0, 0.0, 0.0, 0.0])
                    rpy = [0, 0, 0]
        
        # 获取环境数据
        obstacles = environment.get_nearby_obstacles(pos, self.sensors['lidar']['range'])
        
        # 相机数据 (模拟)
        camera_data = {
            'image': None,  # 实际应用中为图像数据
            'objects': environment.get_visible_objects(pos, rot, self.sensors['camera']['fov'])
        }
        
        data = {
            "time": t,
            "position": noisy_pos,
            "velocity": noisy_vel,
            "attitude": rpy,
            "angular_vel": noisy_omega,
            "altitude": noisy_alt,
            "obstacles": obstacles,
            "camera": camera_data,
            "battery": self.battery_level
        }
        
        self.sensor_data.append(data)
        return data
    
    def communicate(self, other_drones, t):
        """与其他无人机通信"""
        messages = []
        for drone in other_drones:
            if drone.id == self.id:
                continue
                
            # 检查通信范围
            dist = np.linalg.norm(self.state[0:3] - drone.state[0:3])
            if dist <= self.comms['range']:
                # 模拟通信延迟 - 确保所有NumPy数组转换为列表
                message = {
                    "from": self.id,
                    "to": drone.id,
                    "time": t,
                    "position": self.state[0:3].tolist(),  # 转换为列表
                    "velocity": self.state[3:6].tolist(),  # 转换为列表
                    "status": self.status,
                    "sensor_summary": self.get_sensor_summary()
                }
                messages.append(message)
                
                # 记录通信
                self.communication_log.append({
                    "time": t,
                    "to": drone.id,
                    "data_size": len(json.dumps(message)),
                    "latency": self.comms['latency']
                })
        
        return messages
    
    def get_sensor_summary(self):
        """获取传感器数据摘要"""
        if not self.sensor_data:
            return {}
        last_data = self.sensor_data[-1]
        return {
            "position": last_data['position'].tolist() if hasattr(last_data['position'], 'tolist') else last_data['position'],  # 确保转换为列表
            "obstacles": len(last_data['obstacles']),
            "battery": last_data['battery']
        }
    
    def lqr_controller(self, t, target_pos, target_vel, target_yaw):
        """LQR控制器实现"""
        # 简化的LQR实现 - 实际应用需要更复杂的实现
        Kp_pos = np.diag([1.5, 1.5, 2.0])
        Kd_pos = np.diag([0.8, 0.8, 1.0])
        Kp_att = np.diag([8.0, 8.0, 3.0])
        Kd_att = np.diag([2.0, 2.0, 1.0])
        
        # 位置控制
        pos_error = target_pos - self.state[0:3]
        vel_error = target_vel - self.state[3:6]
        des_acc = Kp_pos @ pos_error + Kd_pos @ vel_error + np.array([0, 0, self.g])
        
        # 姿态控制 - 修复除零问题和无效值
        des_yaw = np.radians(target_yaw)
        
        # 安全计算 des_roll
        roll_arg = (des_acc[0]*np.sin(des_yaw) - des_acc[1]*np.cos(des_yaw)) / self.g
        roll_arg = np.clip(roll_arg, -1.0, 1.0)  # 确保在有效范围内
        des_roll = np.arcsin(roll_arg)
        
        # 安全计算 des_pitch
        cos_roll = np.cos(des_roll)
        if np.abs(cos_roll) < 1e-3:  # 避免除零
            des_pitch = 0.0
        else:
            pitch_arg = des_acc[0] / (self.g * cos_roll)
            pitch_arg = np.clip(pitch_arg, -1.0, 1.0)  # 确保在有效范围内
            des_pitch = np.arcsin(pitch_arg)
        
        current_rot = R.from_quat(self.state[6:10])
        current_rpy = current_rot.as_euler('zyx')[::-1]
        
        # 修复：验证旋转有效性
        if np.any(np.isnan([des_yaw, des_pitch, des_roll])):
            # 如果计算出NaN，使用当前姿态
            des_rot = current_rot
        else:
            des_rot = R.from_euler('zyx', [des_yaw, des_pitch, des_roll])
        
        # 计算姿态误差
        quat_error = des_rot.inv() * current_rot
        
        # 确保四元数有效
        if np.linalg.norm(quat_error.as_quat()) < 1e-6:
            att_error = np.zeros(3)
        else:
            att_error = quat_error.as_euler('zyx')[::-1]
        
        des_torque = Kp_att @ att_error + Kd_att @ -self.state[10:13]
        
        # 计算电机转速
        des_thrust = self.m * np.linalg.norm(des_acc)
        u1 = des_thrust / (4 * self.kf)
        u2 = des_torque[0] / (self.l * self.kf)
        u3 = des_torque[1] / (self.l * self.kf)
        u4 = des_torque[2] / (4 * self.km)
        
        # 确保电机转速有效
        w_sq = np.abs(np.array([
            u1 - u2 + u3 + u4,
            u1 + u2 - u3 + u4,
            u1 + u2 + u3 - u4,
            u1 - u2 - u3 - u4
        ]))
        
        # 防止负值平方根
        w_sq = np.maximum(w_sq, 0)
        w = np.sqrt(w_sq)
        
        return np.clip(w, 0, self.max_rpm)
    
    def mpc_controller(self, t, target_trajectory, environment):
        """模型预测控制器 - 简化实现"""
        # 实际应用中需要更复杂的优化求解
        # 这里使用简化的预测控制
        
        # 预测时域
        if not hasattr(target_trajectory, 'get_target'):
            # 如果不是，回退到LQR控制
            return self.lqr_controller(t, np.array([0,0,5]), np.zeros(3), 0)
        
        # 预测时域
        horizon = 5
        dt = 0.1
        
        best_control = None
        min_cost = float('inf')
        
        # 生成候选控制序列
        for _ in range(50):
            candidate = np.random.uniform(0, self.max_rpm, (horizon, 4))
            
            # 模拟预测
            cost = 0
            state = self.state.copy()
            for i in range(horizon):
                # 简化的动力学更新
                # 实际应用中应使用完整的动力学模型
                state[0:3] += state[3:6] * dt
                state[3:6] += np.array([0, 0, -self.g]) * dt
                
                # 目标成本 - 使用轨迹规划器获取目标
                target = target_trajectory.get_target(t + i * dt, state[0:3], state[3:6])
                pos_error = np.linalg.norm(target[0] - state[0:3])
                vel_error = np.linalg.norm(target[1] - state[3:6])
                cost += pos_error + 0.1 * vel_error
                
                # 障碍物成本
                obstacles = environment.get_nearby_obstacles(state[0:3], 5.0)
                for obs in obstacles:
                    dist = np.linalg.norm(obs['position'] - state[0:3])
                    if dist < obs['radius'] + 1.0:
                        cost += 1000 / max(0.1, dist - obs['radius'])
            
            if cost < min_cost:
                min_cost = cost
                best_control = candidate[0]
        
        return best_control

    def get_control_input(self, t, target, environment, sensor_data):
        """根据控制器类型获取控制输入"""
        if self.controller_type == "LQR":
            return self.lqr_controller(t, target[0], target[1], target[2])
        elif self.controller_type == "MPC":
            # 确保传递的是轨迹规划器对象而不是目标元组
            if hasattr(self, 'trajectory'):
                return self.mpc_controller(t, self.trajectory, environment)
            else:
                # 如果没有轨迹规划器，回退到LQR控制
                return self.lqr_controller(t, target[0], target[1], target[2])
        elif self.controller_type == "NN":
            # 简化实现，实际应使用神经网络
            return self.lqr_controller(t, target[0], target[1], target[2])
        else:  # PID
            return self.lqr_controller(t, target[0], target[1], target[2])  # 简化实现

# ==================== 环境模型 ====================
class Environment:
    def __init__(self, size=(100, 100, 50)):
        self.size = size
        self.obstacles = []
        self.wind_model = None
        self.thermal_model = None
        self.weather = "CLEAR"
        self.time_of_day = 12.0  # 小时
        self.gravity = 9.80665
        self.air_density = 1.225  # kg/m³
        
    def add_obstacle(self, position, radius, height=None, type="building"):
        if height is None:
            height = self.size[2] - position[2]
        self.obstacles.append({
            "position": np.array(position),
            "radius": radius,
            "height": height,
            "type": type
        })
    
    def generate_city_environment(self, num_buildings=20):
        """生成城市环境"""
        for _ in range(num_buildings):
            x = np.random.uniform(-self.size[0]/2, self.size[0]/2)
            y = np.random.uniform(-self.size[1]/2, self.size[1]/2)
            radius = np.random.uniform(3, 10)
            height = np.random.uniform(10, min(50, self.size[2]-5))
            self.add_obstacle([x, y, height/2], radius, height)
    
    def set_wind_model(self, wind_model):
        self.wind_model = wind_model
    
    def set_thermal_model(self, thermal_model):
        self.thermal_model = thermal_model
    
    def get_wind(self, t, position):
        """获取位置处的风速"""
        if self.wind_model:
            return self.wind_model(t, position)
        return np.zeros(3)
    
    def get_environmental_force(self, t, position):
        """获取环境力（如热气流）"""
        force = np.zeros(3)
        
        # 热气流
        if self.thermal_model:
            thermal_strength = self.thermal_model(t, position)
            force[2] = thermal_strength * 0.1  # 转换为力
        
        return force
    
    def get_nearby_obstacles(self, position, radius):
        """获取附近的障碍物"""
        nearby = []
        for obs in self.obstacles:
            dist = np.linalg.norm(obs['position'][0:2] - position[0:2])
            if dist < radius + obs['radius']:
                # 检查高度
                if abs(position[2] - obs['position'][2]) < obs['height']/2 + 5:
                    nearby.append(obs)
        return nearby
    
    def get_visible_objects(self, position, rotation, fov):
        """获取相机视野内的物体"""
        # 简化实现 - 实际应用中应使用3D几何计算
        visible = []
        forward = rotation.apply([0, 0, 1])
        
        for obs in self.obstacles:
            dir_to_obs = obs['position'] - position
            dist = np.linalg.norm(dir_to_obs)
            dir_to_obs /= dist
            
            # 检查是否在视野内
            angle = np.degrees(np.arccos(np.dot(forward, dir_to_obs)))
            if angle < fov/2 and dist < 50:
                visible.append({
                    "type": obs["type"],
                    "position": obs["position"],
                    "distance": dist
                })
        
        return visible
    
    def collision_check(self, position, radius=1.0):
        """检查碰撞"""
        for obs in self.obstacles:
            dist = np.linalg.norm(obs['position'][0:2] - position[0:2])
            height_diff = abs(position[2] - obs['position'][2])
            
            if dist < radius + obs['radius'] and height_diff < obs['height']/2 + radius:
                return True
        return False

# ==================== 风场模型 ====================
class WindModel:
    def __init__(self, base_wind=(0, 0, 0), turbulence=0.1, gusts=None):
        self.base_wind = np.array(base_wind)
        self.turbulence = turbulence
        self.gusts = gusts or []
        
    def add_gust(self, start_time, duration, strength, direction):
        self.gusts.append({
            "start": start_time,
            "duration": duration,
            "strength": strength,
            "direction": np.radians(direction)
        })
    
    def __call__(self, t, position):
        wind = self.base_wind.copy()
        
        # 添加湍流
        wind[0] += np.random.normal(0, self.turbulence)
        wind[1] += np.random.normal(0, self.turbulence)
        
        # 添加阵风
        for gust in self.gusts:
            if gust["start"] <= t <= gust["start"] + gust["duration"]:
                dir_vec = np.array([np.cos(gust["direction"]), np.sin(gust["direction"]), 0])
                wind += dir_vec * gust["strength"]
        
        # 添加地形影响
        wind[0] *= (1 - np.exp(-position[2]/20))
        wind[1] *= (1 - np.exp(-position[2]/20))
        
        return wind

# ==================== 轨迹规划器 ====================
class TrajectoryPlanner:
    def __init__(self, environment):
        self.environment = environment
        self.waypoints = []
        self.current_waypoint = 0
        self.path = []
        self.safe_altitude = 15.0
    
    def add_waypoint(self, position, arrival_time=None):
        self.waypoints.append({
            "position": np.array(position),
            "arrival_time": arrival_time
        })
    
    def plan_path(self, start_pos, end_pos):
        """A*路径规划 - 简化实现"""
        # 实际应用中应使用3D A*算法
        # 这里使用直线路径，避免障碍物
        
        self.path = [start_pos]
        
        # 检查直线路径是否安全
        if self.is_path_safe(start_pos, end_pos):
            self.path.append(end_pos)
            return self.path
        
        # 否则添加中间点
        mid_alt = max(start_pos[2], end_pos[2], self.safe_altitude) + 5
        self.path.append(np.array([start_pos[0], start_pos[1], mid_alt]))
        self.path.append(np.array([end_pos[0], end_pos[1], mid_alt]))
        self.path.append(end_pos)
        
        return self.path
    
    def is_path_safe(self, start, end, step=1.0):
        """检查路径是否安全"""
        direction = end - start
        distance = np.linalg.norm(direction)
        direction = direction / distance
        
        for d in np.arange(0, distance, step):
            pos = start + direction * d
            if self.environment.collision_check(pos):
                return False
        return True
    
    def get_target(self, t, current_pos, current_vel):
        """获取当前位置的目标状态"""
        if not self.waypoints:
            return current_pos, np.zeros(3), 0
        
        target_wp = self.waypoints[self.current_waypoint]
        target_pos = target_wp["position"]
        
        # 计算期望速度 (指向目标)
        to_target = target_pos - current_pos
        dist = np.linalg.norm(to_target)
        if dist < 1.0:  # 到达航点
            if self.current_waypoint < len(self.waypoints) - 1:
                self.current_waypoint += 1
                target_wp = self.waypoints[self.current_waypoint]
                target_pos = target_wp["position"]
                dist = np.linalg.norm(target_pos - current_pos)
        
        # 计算期望速度
        if dist > 0:
            desired_vel = (to_target / dist) * min(5.0, dist * 0.5)  # 接近时减速
        else:
            desired_vel = np.zeros(3)
        
        # 计算偏航角 (朝向运动方向)
        if np.linalg.norm(desired_vel) > 0.1:
            desired_yaw = np.degrees(np.arctan2(desired_vel[1], desired_vel[0]))
        else:
            desired_yaw = 0
        
        return target_pos, desired_vel, desired_yaw

# ==================== 多智能体协调器 ====================
class SwarmCoordinator:
    def __init__(self, drones, environment):
        self.drones = drones
        self.environment = environment
        self.formation = "VEE"  # 编队类型
        self.formation_params = {}
        self.mission = None
        self.task_allocation = {}
        self.swarm_path = []
    
    def set_formation(self, formation_type, **params):
        self.formation = formation_type
        self.formation_params = params
    
    def assign_mission(self, mission_type, **params):
        self.mission = mission_type
        if mission_type == "SURVEY":
            self._setup_survey_mission(params)
        elif mission_type == "DELIVERY":
            self._setup_delivery_mission(params)
        elif mission_type == "SEARCH":
            self._setup_search_mission(params)
    
    def _setup_survey_mission(self, params):
        """设置勘测任务"""
        area = params.get("area", [(-50, -50), (50, 50)])
        altitude = params.get("altitude", 30)
        resolution = params.get("resolution", 10)
        
        # 划分区域给每架无人机
        x_min, y_min = area[0]
        x_max, y_max = area[1]
        width = x_max - x_min
        height = y_max - y_min
        
        num_drones = len(self.drones)
        for i, drone in enumerate(self.drones):
            drone_path = []
            # 简化路径 - 实际应用中应使用更复杂的覆盖路径
            for y in np.linspace(y_min, y_max, int(height/resolution)):
                x_start = x_min + (i * width / num_drones)
                x_end = x_min + ((i+1) * width / num_drones)
                drone_path.append([x_start, y, altitude])
                drone_path.append([x_end, y, altitude])
            
            # 设置无人机路径
            planner = TrajectoryPlanner(self.environment)
            for pt in drone_path:
                planner.add_waypoint(pt)
            drone.trajectory = planner
    
    def update(self, t):
        """更新协调逻辑"""
        if self.mission == "SURVEY":
            # 检查任务完成情况
            completed = True
            for drone in self.drones:
                if drone.trajectory.current_waypoint < len(drone.trajectory.waypoints) - 1:
                    completed = False
            
            if completed:
                self.return_to_base(t)
        
        # 防碰撞检查
        self.collision_avoidance(t)
    
    def collision_avoidance(self, t):
        """群体防碰撞"""
        positions = []
        velocities = []  # 添加速度列表
        for drone in self.drones:
            pos = drone.state[0:3]
            vel = drone.state[3:6]  # 获取速度状态
            
            # 检查并清理位置数据
            if not np.all(np.isfinite(pos)):
                pos = np.zeros(3)
                print(f"警告：无人机 {drone.id} 位置无效，已重置")
            positions.append(pos)
            
            # 检查并清理速度数据
            if not np.all(np.isfinite(vel)):
                vel = np.zeros(3)
                print(f"警告：无人机 {drone.id} 速度无效，已重置")
            velocities.append(vel)
        
        # 构建KDTree前再次检查
        positions = np.array(positions)
        if not np.all(np.isfinite(positions)):
            print("严重错误：位置数据包含非有限值，跳过防碰撞检查")
            return
        
        # 构建KD树进行快速邻近搜索
        kdtree = KDTree(positions)
        
        for i, drone in enumerate(self.drones):
            # 查找附近无人机
            neighbors = kdtree.query_ball_point(positions[i], 10.0)
            
            for j in neighbors:
                if i == j:
                    continue
                
                # 计算距离和相对速度
                dist = np.linalg.norm(positions[i] - positions[j])
                rel_vel = velocities[i] - velocities[j]  # 使用定义好的velocities列表
                
                # 如果太近且正在接近
                if dist < 5.0 and np.dot(positions[i]-positions[j], rel_vel) < 0:
                    # 计算避让方向
                    avoid_dir = positions[i] - positions[j]
                    avoid_dir = avoid_dir / np.linalg.norm(avoid_dir)
                    
                    # 调整无人机路径
                    if hasattr(drone, 'trajectory'):
                        wp_index = drone.trajectory.current_waypoint
                        if wp_index < len(drone.trajectory.waypoints):
                            new_pos = drone.trajectory.waypoints[wp_index]["position"] + avoid_dir * 2.0
                            drone.trajectory.waypoints[wp_index]["position"] = new_pos
    
    def return_to_base(self, t):
        """返回基地"""
        base_pos = np.array([0, 0, 5])
        for drone in self.drones:
            planner = TrajectoryPlanner(self.environment)
            planner.add_waypoint(drone.state[0:3])
            planner.add_waypoint(base_pos)
            drone.trajectory = planner

# ==================== PyQt5 界面组件 ====================
class DroneSimulationApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("高级无人机集群仿真系统")
        self.setGeometry(100, 100, 1200, 800)
        
        # 设置深色主题
        self.set_dark_theme()
        
        # 创建环境
        self.env = Environment(size=(200, 200, 100))
        self.env.generate_city_environment(num_buildings=20)
        
        # 创建风场模型
        self.wind_model = WindModel(base_wind=(2.0, 1.0, 0), turbulence=0.2)
        self.wind_model.add_gust(start_time=10, duration=5, strength=5.0, direction=45)
        self.env.set_wind_model(self.wind_model)
        
        # 创建无人机
        self.drones = []
        drone_configs = [
            {"controller": "LQR", "color": (255, 0, 0)},
            {"controller": "PID", "color": (0, 255, 0)},
            {"controller": "MPC", "color": (0, 0, 255)}
        ]
        
        for i, config in enumerate(drone_configs):
            drone = Drone(f"Drone_{i+1}", config)
            initial_pos = np.array([-5 + i*5, -5 + i*5, 5])
            drone.set_initial_state(initial_pos)
            self.drones.append(drone)
        
        # 设置轨迹
        for drone in self.drones:
            planner = TrajectoryPlanner(self.env)
            planner.add_waypoint([0, 0, 10])
            planner.add_waypoint([20, 20, 15])
            planner.add_waypoint([40, 0, 20])
            planner.add_waypoint([0, 40, 25])
            planner.add_waypoint([0, 0, 5])
            drone.trajectory = planner
        
        # 创建协调器
        self.coordinator = SwarmCoordinator(self.drones, self.env)
        self.coordinator.assign_mission("SURVEY", area=[(-40, -40), (40, 40)], altitude=30)
        
        # 创建仿真引擎
        self.sim_time = 0.0
        self.sim_dt = 0.05
        self.sim_running = False
        self.sim_speed = 1.0
        
        # 创建UI
        self.init_ui()
        
        # 启动更新定时器
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_simulation)
        self.timer.start(50)  # 20 FPS
        
    def set_dark_theme(self):
        # 设置深色主题
        dark_palette = QPalette()
        dark_palette.setColor(QPalette.Window, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.WindowText, Qt.white)
        dark_palette.setColor(QPalette.Base, QColor(25, 25, 25))
        dark_palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ToolTipBase, Qt.white)
        dark_palette.setColor(QPalette.ToolTipText, Qt.white)
        dark_palette.setColor(QPalette.Text, Qt.white)
        dark_palette.setColor(QPalette.Button, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ButtonText, Qt.white)
        dark_palette.setColor(QPalette.BrightText, Qt.red)
        dark_palette.setColor(QPalette.Link, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.HighlightedText, Qt.black)
        self.setPalette(dark_palette)
        
        # 设置全局样式
        self.setStyleSheet("""
            QGroupBox {
                border: 1px solid gray;
                border-radius: 5px;
                margin-top: 1ex;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px 0 3px;
                color: #42a2d8;
            }
            QPushButton {
                background-color: #424242;
                color: white;
                border: 1px solid #616161;
                padding: 5px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #535353;
            }
            QPushButton:pressed {
                background-color: #323232;
            }
            QComboBox, QListWidget, QDoubleSpinBox {
                background-color: #353535;
                color: white;
                border: 1px solid #616161;
                padding: 2px;
            }
            QLabel {
                color: white;
            }
            QSlider::groove:horizontal {
                border: 1px solid #616161;
                height: 8px;
                background: #353535;
                margin: 2px 0;
            }
            QSlider::handle:horizontal {
                background: #42a2d8;
                border: 1px solid #616161;
                width: 12px;
                margin: -4px 0;
                border-radius: 6px;
            }
        """)
    
    def init_ui(self):
        # 创建主布局
        main_widget = QWidget()
        main_layout = QHBoxLayout(main_widget)
        
        # 左侧控制面板
        control_panel = self.create_control_panel()
        main_layout.addWidget(control_panel, 1)
        
        # 右侧可视化区域
        vis_tabs = QTabWidget()
        
        # 3D轨迹图
        self.figure_3d = plt.figure()
        self.canvas_3d = FigureCanvas(self.figure_3d)
        vis_tabs.addTab(self.canvas_3d, "3D轨迹")
        
        # 状态图
        self.figure_status = plt.figure()
        self.canvas_status = FigureCanvas(self.figure_status)
        vis_tabs.addTab(self.canvas_status, "状态监控")
        
        # 电池图
        self.figure_battery = plt.figure()
        self.canvas_battery = FigureCanvas(self.figure_battery)
        vis_tabs.addTab(self.canvas_battery, "电池状态")
        
        main_layout.addWidget(vis_tabs, 3)
        
        # 设置主窗口
        self.setCentralWidget(main_widget)
        
        # 状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪 - 按开始按钮启动仿真")
        
        # 初始化绘图
        self.update_plots()
    
    def create_control_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # 仿真控制组
        sim_group = QGroupBox("仿真控制")
        sim_layout = QVBoxLayout()
        
        # 控制按钮
        btn_layout = QHBoxLayout()
        self.btn_start = QPushButton("开始")
        self.btn_start.clicked.connect(self.start_simulation)
        btn_layout.addWidget(self.btn_start)
        
        self.btn_pause = QPushButton("暂停")
        self.btn_pause.clicked.connect(self.pause_simulation)
        btn_layout.addWidget(self.btn_pause)
        
        self.btn_reset = QPushButton("重置")
        self.btn_reset.clicked.connect(self.reset_simulation)
        btn_layout.addWidget(self.btn_reset)
        
        sim_layout.addLayout(btn_layout)
        
        # 仿真速度控制
        speed_layout = QHBoxLayout()
        speed_layout.addWidget(QLabel("仿真速度:"))
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setMinimum(1)
        self.speed_slider.setMaximum(10)
        self.speed_slider.setValue(5)
        self.speed_slider.valueChanged.connect(self.set_sim_speed)
        speed_layout.addWidget(self.speed_slider)
        
        sim_layout.addLayout(speed_layout)
        
        # 时间信息
        time_layout = QHBoxLayout()
        time_layout.addWidget(QLabel("仿真时间:"))
        self.time_label = QLabel("0.00 s")
        time_layout.addWidget(self.time_label)
        
        sim_layout.addLayout(time_layout)
        
        sim_group.setLayout(sim_layout)
        layout.addWidget(sim_group)
        
        # 无人机选择组
        drone_group = QGroupBox("无人机选择")
        drone_layout = QVBoxLayout()
        
        self.drone_list = QListWidget()
        for drone in self.drones:
            self.drone_list.addItem(drone.id)
        self.drone_list.setCurrentRow(0)
        drone_layout.addWidget(self.drone_list)
        
        # 无人机信息
        self.drone_info = QLabel("选择无人机查看详细信息")
        drone_layout.addWidget(self.drone_info)
        
        drone_group.setLayout(drone_layout)
        layout.addWidget(drone_group)
        
        # 环境控制组
        env_group = QGroupBox("环境设置")
        env_layout = QVBoxLayout()
        
        # 风控制
        wind_layout = QHBoxLayout()
        wind_layout.addWidget(QLabel("风速 (m/s):"))
        self.wind_spin = QDoubleSpinBox()
        self.wind_spin.setRange(0, 10)
        self.wind_spin.setValue(2.0)
        self.wind_spin.valueChanged.connect(self.update_wind)
        wind_layout.addWidget(self.wind_spin)
        
        wind_layout.addWidget(QLabel("方向 (°):"))
        self.wind_dir_spin = QDoubleSpinBox()
        self.wind_dir_spin.setRange(0, 360)
        self.wind_dir_spin.setValue(45)
        self.wind_dir_spin.valueChanged.connect(self.update_wind)
        wind_layout.addWidget(self.wind_dir_spin)
        
        env_layout.addLayout(wind_layout)
        
        # 阵风控制
        self.gust_check = QCheckBox("启用阵风")
        self.gust_check.stateChanged.connect(self.update_wind)
        env_layout.addWidget(self.gust_check)
        
        # 建筑控制
        build_layout = QHBoxLayout()
        build_layout.addWidget(QLabel("建筑数量:"))
        self.build_spin = QDoubleSpinBox()
        self.build_spin.setRange(0, 100)
        self.build_spin.setValue(20)
        self.build_spin.valueChanged.connect(self.update_buildings)
        build_layout.addWidget(self.build_spin)
        
        env_layout.addLayout(build_layout)
        
        env_group.setLayout(env_layout)
        layout.addWidget(env_group)
        
        # 任务控制组
        task_group = QGroupBox("任务设置")
        task_layout = QVBoxLayout()
        
        # 任务选择
        self.mission_combo = QComboBox()
        self.mission_combo.addItems(["勘测任务", "运输任务", "搜救任务"])
        task_layout.addWidget(self.mission_combo)
        
        # 编队选择
        self.formation_combo = QComboBox()
        self.formation_combo.addItems(["V字队形", "一字队形", "菱形队形"])
        task_layout.addWidget(self.formation_combo)
        
        task_group.setLayout(task_layout)
        layout.addWidget(task_group)
        
        # 添加拉伸因子
        layout.addStretch(1)
        
        return panel
    
    def start_simulation(self):
        self.sim_running = True
        self.status_bar.showMessage("仿真运行中...")
        self.btn_start.setEnabled(False)
        self.btn_pause.setEnabled(True)
    
    def pause_simulation(self):
        self.sim_running = False
        self.status_bar.showMessage("仿真已暂停")
        self.btn_start.setEnabled(True)
        self.btn_pause.setEnabled(False)
    
    def reset_simulation(self):
        self.sim_running = False
        self.sim_time = 0.0
        
        # 重置无人机状态
        for i, drone in enumerate(self.drones):
            initial_pos = np.array([-5 + i*5, -5 + i*5, 5])
            drone.set_initial_state(initial_pos)
            drone.log = []
            drone.control_history = []
            drone.energy_consumed = 0.0
            drone.communication_log = []
            drone.sensor_data = []
            drone.status = "IDLE"
            drone.battery_level = 100.0
        
        self.status_bar.showMessage("仿真已重置")
        self.btn_start.setEnabled(True)
        self.btn_pause.setEnabled(False)
        self.update_plots()
    
    def set_sim_speed(self, value):
        self.sim_speed = value / 5.0
    
    def update_wind(self):
        # 更新风模型
        wind_speed = self.wind_spin.value()
        wind_dir = self.wind_dir_spin.value()
        
        # 创建新风模型
        wind_model = WindModel(base_wind=(
            wind_speed * np.cos(np.radians(wind_dir)),
            wind_speed * np.sin(np.radians(wind_dir)),
            0
        ), turbulence=0.2)
        
        # 如果启用阵风
        if self.gust_check.isChecked():
            wind_model.add_gust(start_time=10, duration=5, strength=5.0, direction=wind_dir)
        
        self.env.set_wind_model(wind_model)
    
    def update_buildings(self):
        num_buildings = int(self.build_spin.value())
        self.env.obstacles = []
        self.env.generate_city_environment(num_buildings=num_buildings)
    
    def update_simulation(self):
        if not self.sim_running:
            return
        
        # 计算时间步长
        dt = self.sim_dt * self.sim_speed
        self.sim_time += dt
        
        # 更新每架无人机
        for drone in self.drones:
            # 获取传感器数据
            sensor_data = drone.get_sensor_data(self.sim_time, self.env)
            
            # 获取目标状态
            if hasattr(drone, 'trajectory'):
                target = drone.trajectory.get_target(self.sim_time, drone.state[0:3], drone.state[3:6])
            else:
                target = (np.array([0, 0, 5]), np.zeros(3), 0)
            
            # 计算控制输入
            control_input = drone.get_control_input(self.sim_time, target, self.env, sensor_data)
            
            # 更新动力学
            drone.update_dynamics(self.sim_time, dt, control_input, self.env)
            
            # 通信
            messages = drone.communicate(self.drones, self.sim_time)
        
        # 更新协调器
        if self.coordinator:
            self.coordinator.update(self.sim_time)
        
        # 更新UI
        self.time_label.setText(f"{self.sim_time:.2f} s")
        self.update_drone_info()
        self.update_plots()
        
        # 检查是否完成
        if self.sim_time > 120:  # 120秒后自动停止
            self.pause_simulation()
            self.status_bar.showMessage("仿真已完成")
    
    def update_drone_info(self):
        current_idx = self.drone_list.currentRow()
        if current_idx < 0 or current_idx >= len(self.drones):
            return
        
        drone = self.drones[current_idx]
        pos = drone.state[0:3]
        battery = drone.battery_level
        
        info = f"""
        <b>{drone.id} 状态信息</b>
        <hr>
        <b>位置:</b> X={pos[0]:.2f}m, Y={pos[1]:.2f}m, Z={pos[2]:.2f}m<br>
        <b>电池:</b> {battery:.1f}%<br>
        <b>控制器:</b> {drone.controller_type}<br>
        <b>状态:</b> {drone.status}<br>
        <b>任务:</b> 航点 {drone.trajectory.current_waypoint+1}/{len(drone.trajectory.waypoints)}<br>
        """
        
        self.drone_info.setText(info)
    
    def update_plots(self):
        # 更新3D轨迹图
        self.figure_3d.clear()
        ax = self.figure_3d.add_subplot(111, projection='3d')
        
        # 绘制障碍物
        for obs in self.env.obstacles:
            pos = obs["position"]
            radius = obs["radius"]
            height = obs["height"]
            
            # 绘制圆柱体
            z = np.linspace(pos[2] - height/2, pos[2] + height/2, 10)
            theta = np.linspace(0, 2 * np.pi, 20)
            theta_grid, z_grid = np.meshgrid(theta, z)
            x_grid = pos[0] + radius * np.cos(theta_grid)
            y_grid = pos[1] + radius * np.sin(theta_grid)
            
            ax.plot_surface(x_grid, y_grid, z_grid, color='gray', alpha=0.5)
        
        # 绘制无人机轨迹
        colors = ['red', 'green', 'blue']
        for i, drone in enumerate(self.drones):
            if not drone.log:
                continue
                
            log_times, log_states = zip(*drone.log)
            positions = np.array([state[0:3] for state in log_states])
            
            # 绘制轨迹
            ax.plot(positions[:, 0], positions[:, 1], positions[:, 2], 
                    color=colors[i], linewidth=2, label=drone.id)
            
            # 绘制当前位置
            current_pos = positions[-1]
            ax.scatter(current_pos[0], current_pos[1], current_pos[2], 
                       color=colors[i], s=100, edgecolors='black')
        
        ax.set_xlabel('X (m)')
        ax.set_ylabel('Y (m)')
        ax.set_zlabel('Z (m)')
        ax.set_title('无人机3D轨迹')
        ax.legend()
        ax.grid(True)
        
        self.canvas_3d.draw()
        
        # 更新状态图
        self.figure_status.clear()
        ax_status = self.figure_status.add_subplot(111)
        
        if self.drones[0].log:
            log_times, log_states = zip(*self.drones[0].log)
            positions = np.array([state[0:3] for state in log_states])
            velocities = np.array([state[3:6] for state in log_states])
            
            # 位置变化
            ax_status.plot(log_times, positions[:, 0], 'r-', label='X位置')
            ax_status.plot(log_times, positions[:, 1], 'g-', label='Y位置')
            ax_status.plot(log_times, positions[:, 2], 'b-', label='Z位置')
            
            # 速度变化
            ax_status.plot(log_times, velocities[:, 0], 'r--', label='X速度')
            ax_status.plot(log_times, velocities[:, 1], 'g--', label='Y速度')
            ax_status.plot(log_times, velocities[:, 2], 'b--', label='Z速度')
            
            ax_status.set_xlabel('时间 (s)')
            ax_status.set_ylabel('值')
            ax_status.set_title('无人机状态变化')
            ax_status.legend()
            ax_status.grid(True)
        
        self.canvas_status.draw()
        
        # 更新电池图
        self.figure_battery.clear()
        ax_battery = self.figure_battery.add_subplot(111)
        
        if self.drones[0].log:
            for i, drone in enumerate(self.drones):
                if not drone.log:
                    continue
                    
                log_times, log_states = zip(*drone.log)
                battery_levels = [data['battery'] for data in drone.sensor_data]
                battery_times = [data['time'] for data in drone.sensor_data]
                
                ax_battery.plot(battery_times, battery_levels, 
                               color=colors[i], linewidth=2, label=drone.id)
            
            ax_battery.set_xlabel('时间 (s)')
            ax_battery.set_ylabel('电池电量 (%)')
            ax_battery.set_title('无人机电池状态')
            ax_battery.legend()
            ax_battery.grid(True)
            ax_battery.set_ylim(0, 100)
        
        self.canvas_battery.draw()

# ==================== 主程序入口 ====================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setFont(QFont("Arial", 10))
    
    window = DroneSimulationApp()
    window.show()
    
    sys.exit(app.exec_())