import sys
import math
import random
import numpy as np
from datetime import datetime, timedelta
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QGridLayout, QLabel, QPushButton, 
                             QSlider, QProgressBar, QFrame, QTabWidget,
                             QGroupBox, QComboBox, QSpinBox, QDoubleSpinBox,
                             QTextEdit, QSplitter, QCheckBox, QDial)
from PyQt5.QtCore import QTimer, Qt, pyqtSignal, QPointF, QRectF
from PyQt5.QtGui import (QFont, QPalette, QColor, QPainter, QPen, QBrush, 
                         QLinearGradient, QRadialGradient, QPainterPath)
import json

class HighFidelityBattery:
    """高保真电池模型 - 基于特斯拉2170电池特性"""
    def __init__(self):
        # 电池规格 (基于特斯拉Model 3长续航版)
        self.cell_count = 4416  # 2170电池数量
        self.cell_nominal_voltage = 3.7  # V
        self.cell_capacity = 4.8  # Ah
        self.cell_energy = self.cell_nominal_voltage * self.cell_capacity  # Wh
        
        # 电池组参数
        self.nominal_voltage = self.cell_nominal_voltage * 96  # 串联96个电池
        self.total_capacity = self.cell_capacity * (self.cell_count / 96)  # Ah
        self.total_energy = self.total_capacity * self.nominal_voltage / 1000  # kWh
        
        # 状态变量
        self.state_of_charge = 0.75  # 0-1
        self.voltage = self.nominal_voltage
        self.current = 0  # A
        self.temperature = 25  # °C
        self.internal_resistance = 0.1  # Ω
        self.health = 1.0  # 0-1
        
        # 温度参数
        self.ambient_temperature = 25
        self.cooling_power = 0
        self.heating_power = 0
        
        # 充电参数
        self.charging_voltage = 0
        self.charging_current = 0
        self.is_charging = False
        self.charger_type = "AC"  # AC, DC
        
        # 历史数据
        self.cycle_count = 0
        self.total_energy_charged = 0  # kWh
        self.total_energy_discharged = 0  # kWh
        
    def update(self, dt, power_demand=0):
        """更新电池状态"""
        # 计算开路电压 (基于SOC)
        soc = self.state_of_charge
        # 锂离子电池开路电压曲线 (简化模型)
        if soc > 0.9:
            ocv = self.nominal_voltage * (1.05 - 0.1 * (1 - soc))
        elif soc > 0.2:
            ocv = self.nominal_voltage * (0.95 + 0.1 * (soc - 0.2) / 0.7)
        else:
            ocv = self.nominal_voltage * (0.85 + 0.1 * soc / 0.2)
        
        # 计算电流
        if self.is_charging:
            # 充电模式
            if self.charger_type == "DC":
                # DC快充 - 恒功率充电
                self.current = min(self.charging_current, 
                                 (self.total_energy * 1000 * (1 - soc)) / (self.voltage * dt) * 3600)
                self.voltage = ocv + self.current * self.internal_resistance
            else:
                # AC充电 - 恒流恒压
                self.current = self.charging_current
                self.voltage = min(ocv * 1.1, self.charging_voltage)
            
            # 更新SOC
            energy_added = self.voltage * self.current * dt / 3600 / 1000  # kWh
            self.state_of_charge = min(1.0, self.state_of_charge + energy_added / self.total_energy)
            self.total_energy_charged += energy_added
            
            # 充电热量
            heat_generated = self.current**2 * self.internal_resistance * dt / 3600  # Wh
        else:
            # 放电模式
            if power_demand > 0:
                # 计算最大可用功率
                max_power = (ocv**2) / (4 * self.internal_resistance)
                actual_power = min(power_demand * 1000, max_power)  # W
                
                # 计算电流和电压
                self.current = (ocv - math.sqrt(ocv**2 - 4 * self.internal_resistance * actual_power)) / (2 * self.internal_resistance)
                self.voltage = ocv - self.current * self.internal_resistance
                
                # 更新SOC
                energy_used = actual_power * dt / 3600 / 1000  # kWh
                self.state_of_charge = max(0, self.state_of_charge - energy_used / self.total_energy)
                self.total_energy_discharged += energy_used
                
                # 放电热量
                heat_generated = self.current**2 * self.internal_resistance * dt / 3600  # Wh
            else:
                # 空闲状态
                self.current = 0
                self.voltage = ocv
                heat_generated = 0
        
        # 温度更新
        self.update_temperature(dt, heat_generated)
        
        # 健康度衰减
        self.update_health(dt)
        
        # 返回实际提供的功率
        return self.voltage * self.current / 1000  # kW
    
    def update_temperature(self, dt, heat_generated):
        """更新电池温度"""
        # 热传递模型
        thermal_mass = 200  # J/°C 电池组热容
        thermal_resistance = 0.1  # °C/W 散热阻力
        
        # 温度变化
        if self.temperature > self.ambient_temperature:
            cooling = (self.temperature - self.ambient_temperature) / thermal_resistance
        else:
            cooling = 0
            
        # 主动冷却/加热
        active_thermal_control = self.cooling_power - self.heating_power
        
        # 温度变化率
        dT_dt = (heat_generated * 3600 / dt - cooling + active_thermal_control * 1000) / thermal_mass
        self.temperature += dT_dt * dt / 3600
        
        # 温度限制
        self.temperature = max(-20, min(60, self.temperature))
    
    def update_health(self, dt):
        """更新电池健康度"""
        # 基于温度、循环次数和时间的健康度衰减
        temp_factor = 1.0
        if self.temperature > 40:
            temp_factor = 1 + (self.temperature - 40) * 0.001
        elif self.temperature < 0:
            temp_factor = 1 + abs(self.temperature) * 0.0005
            
        cycle_factor = 1 + self.cycle_count * 0.00001
        time_factor = 1 + dt / (3600 * 24 * 365) * 0.05  # 每年5%自然衰减
        
        health_loss = (temp_factor * cycle_factor * time_factor - 1) * dt / (3600 * 24 * 365)
        self.health = max(0.7, self.health - health_loss)
    
    def start_charging(self, charger_type, power=0, voltage=0, current=0):
        """开始充电"""
        self.is_charging = True
        self.charger_type = charger_type
        
        if charger_type == "DC":
            # DC快充 - 基于功率
            self.charging_current = min(500, power * 1000 / self.nominal_voltage)  # 最大500A
        else:
            # AC充电 - 基于电压电流
            self.charging_voltage = voltage if voltage > 0 else 240
            self.charging_current = current if current > 0 else 32  # 默认32A
    
    def stop_charging(self):
        """停止充电"""
        self.is_charging = False
        self.charging_current = 0
        self.cycle_count += 0.01  # 部分循环计数
    
    def get_range(self, consumption=0.15):
        """计算续航里程"""
        return self.state_of_charge * self.total_energy / consumption
    
    def get_state_of_charge(self):
        """获取SOC百分比"""
        return self.state_of_charge * 100

class AdvancedDriveSystem:
    """高级驱动系统 - 基于特斯拉双电机全轮驱动"""
    def __init__(self):
        # 电机参数 (前和后)
        self.motor_power_front = 200  # kW
        self.motor_power_rear = 300   # kW
        self.motor_torque_front = 400  # Nm
        self.motor_torque_rear = 600   # Nm
        self.motor_efficiency = 0.95   # 峰值效率
        
        # 变速箱
        self.gear_ratio_front = 9.0
        self.gear_ratio_rear = 9.0
        
        # 车辆参数
        self.vehicle_mass = 2100  # kg
        self.wheel_radius = 0.34  # m
        self.drag_coefficient = 0.23
        self.frontal_area = 2.22  # m²
        self.rolling_resistance = 0.01
        
        # 状态变量
        self.speed = 0  # m/s
        self.acceleration = 0  # m/s²
        self.power = 0  # kW
        self.torque_front = 0
        self.torque_rear = 0
        self.motor_rpm_front = 0
        self.motor_rpm_rear = 0
        self.wheel_slip_front = 0
        self.wheel_slip_rear = 0
        
        # 温度
        self.motor_temp_front = 25
        self.motor_temp_rear = 25
        self.inverter_temp_front = 25
        self.inverter_temp_rear = 25
        
        # 驾驶模式
        self.drive_mode = "Normal"
        self.traction_control = True
        self.regenerative_braking = "Standard"
        
    def update(self, dt, throttle_input, brake_input, steering_angle, road_grade=0):
        """更新驱动系统"""
        # 计算阻力
        air_density = 1.225  # kg/m³
        air_resistance = 0.5 * air_density * self.drag_coefficient * self.frontal_area * self.speed**2
        
        rolling_resistance = self.rolling_resistance * self.vehicle_mass * 9.81 * math.cos(math.radians(road_grade))
        
        grade_resistance = self.vehicle_mass * 9.81 * math.sin(math.radians(road_grade))
        
        total_resistance = air_resistance + rolling_resistance + grade_resistance
        
        # 根据驾驶模式调整功率分配
        if self.drive_mode == "Normal":
            front_power_ratio = 0.3
            rear_power_ratio = 0.7
            power_limit = self.motor_power_front + self.motor_power_rear
        elif self.drive_mode == "Sport":
            front_power_ratio = 0.4
            rear_power_ratio = 0.8
            power_limit = (self.motor_power_front + self.motor_power_rear) * 1.1
        else:  # Ludicrous
            front_power_ratio = 0.5
            rear_power_ratio = 1.0
            power_limit = (self.motor_power_front + self.motor_power_rear) * 1.2
        
        # 计算需求扭矩
        if throttle_input > 0 and brake_input == 0:
            # 加速
            req_power = throttle_input * power_limit
            req_torque_wheel = req_power * 1000 / max(1, self.speed)  # 防止除零
            
            # 分配扭矩
            self.torque_front = min(req_torque_wheel * front_power_ratio / self.gear_ratio_front, 
                                   self.motor_torque_front)
            self.torque_rear = min(req_torque_wheel * rear_power_ratio / self.gear_ratio_rear, 
                                  self.motor_torque_rear)
            
            # 计算轮上扭矩
            total_wheel_torque = (self.torque_front * self.gear_ratio_front + 
                                 self.torque_rear * self.gear_ratio_rear)
            
            # 计算净加速度
            net_force = total_wheel_torque / self.wheel_radius - total_resistance
            self.acceleration = net_force / self.vehicle_mass
            
        elif brake_input > 0:
            # 制动
            if self.regenerative_braking != "Off" and self.speed > 1:
                # 能量回收制动
                regen_power = 0
                if self.regenerative_braking == "Standard":
                    regen_power = min(70, self.speed * 10) * brake_input  # kW
                else:  # "Low"
                    regen_power = min(50, self.speed * 7) * brake_input  # kW
                
                regen_torque = regen_power * 1000 / max(1, self.speed)
                net_force = -regen_torque / self.wheel_radius - total_resistance
                
                # 机械制动补充
                if brake_input > 0.5:
                    mechanical_brake = (brake_input - 0.5) * 2 * 10000  # N
                    net_force -= mechanical_brake
                
                self.acceleration = net_force / self.vehicle_mass
                self.power = -regen_power
            else:
                # 纯机械制动
                brake_force = brake_input * 15000  # N
                net_force = -brake_force - total_resistance
                self.acceleration = net_force / self.vehicle_mass
                self.power = 0
        else:
            # 滑行
            net_force = -total_resistance
            self.acceleration = net_force / self.vehicle_mass
            self.power = 0
        
        # 更新速度
        self.speed += self.acceleration * dt
        
        # 防止速度为负
        self.speed = max(0, self.speed)
        
        # 计算电机转速
        wheel_rpm = self.speed / (2 * math.pi * self.wheel_radius) * 60
        self.motor_rpm_front = wheel_rpm * self.gear_ratio_front
        self.motor_rpm_rear = wheel_rpm * self.gear_ratio_rear
        
        # 计算实际功率输出
        if self.power == 0 and throttle_input > 0:
            self.power = (abs(self.torque_front) * abs(self.motor_rpm_front) / 9549 + 
                         abs(self.torque_rear) * abs(self.motor_rpm_rear) / 9549)
        
        # 更新温度
        self.update_temperatures(dt)
        
        # 返回功率需求
        return abs(self.power)
    
    def update_temperatures(self, dt):
        """更新电机和逆变器温度"""
        # 电机温度
        motor_heat_front = (abs(self.torque_front) * abs(self.motor_rpm_front) / 9549 * 
                           (1 - self.motor_efficiency)) * 0.5
        motor_heat_rear = (abs(self.torque_rear) * abs(self.motor_rpm_rear) / 9549 * 
                          (1 - self.motor_efficiency)) * 0.5
        
        # 逆变器温度 (IGBT损耗)
        inverter_loss_front = self.power * 0.02 if self.power > 0 else 0
        inverter_loss_rear = self.power * 0.02 if self.power > 0 else 0
        
        # 温度更新 (简化热模型)
        ambient_temp = 25
        cooling_rate = 0.1
        
        self.motor_temp_front += (motor_heat_front - cooling_rate * (self.motor_temp_front - ambient_temp)) * dt / 60
        self.motor_temp_rear += (motor_heat_rear - cooling_rate * (self.motor_temp_rear - ambient_temp)) * dt / 60
        self.inverter_temp_front += (inverter_loss_front - cooling_rate * (self.inverter_temp_front - ambient_temp)) * dt / 60
        self.inverter_temp_rear += (inverter_loss_rear - cooling_rate * (self.inverter_temp_rear - ambient_temp)) * dt / 60
        
        # 温度限制
        self.motor_temp_front = max(ambient_temp, min(120, self.motor_temp_front))
        self.motor_temp_rear = max(ambient_temp, min(120, self.motor_temp_rear))
        self.inverter_temp_front = max(ambient_temp, min(100, self.inverter_temp_front))
        self.inverter_temp_rear = max(ambient_temp, min(100, self.inverter_temp_rear))

class EnhancedAutopilot:
    """增强版自动驾驶系统"""
    def __init__(self):
        self.enabled = False
        self.cruise_speed = 0  # m/s
        self.target_speed = 0  # m/s
        self.follow_distance = 2.0  # 秒
        self.steering_angle = 0  # 度
        self.lane_keeping = True
        self.auto_lane_change = False
        self.navigation_active = False
        self.destination = None
        
        # 传感器数据
        self.forward_obstacles = []
        self.surrounding_vehicles = []
        self.lane_geometry = []
        self.traffic_lights = []
        
        # 控制参数
        self.acceleration_pid = PIDController(0.5, 0.1, 0.2)
        self.steering_pid = PIDController(0.8, 0.05, 0.3)
        
        # 路径规划
        self.planned_path = []
        self.current_segment = 0
        
        # 状态
        self.emergency_braking = False
        self.blind_spot_warning = False
        self.collision_warning = False
        
    def update(self, dt, current_speed, current_position, road_conditions):
        """更新自动驾驶系统"""
        if not self.enabled:
            return 0, 0, 0  # 油门, 刹车, 转向
        
        # 更新传感器数据
        self.update_sensors(current_position, road_conditions)
        
        # 速度控制
        throttle, brake = self.acceleration_control(dt, current_speed)
        
        # 转向控制
        steering = self.steering_control(dt, current_position)
        
        # 紧急情况处理
        if self.emergency_braking:
            throttle = 0
            brake = 1.0
        
        return throttle, brake, steering
    
    def update_sensors(self, position, road_conditions):
        """模拟传感器数据更新"""
        # 模拟前方障碍物
        self.forward_obstacles = []
        if random.random() < 0.02:  # 2%概率检测到障碍物
            distance = random.uniform(10, 100)
            speed = random.uniform(0, 10)
            self.forward_obstacles.append({
                'distance': distance,
                'speed': speed,
                'type': 'vehicle' if random.random() < 0.7 else 'obstacle'
            })
        
        # 模拟周围车辆
        self.surrounding_vehicles = []
        for i in range(random.randint(0, 3)):
            lane_offset = random.choice([-3.5, 0, 3.5])
            relative_speed = random.uniform(-5, 5)
            self.surrounding_vehicles.append({
                'lane_offset': lane_offset,
                'relative_speed': relative_speed,
                'distance': random.uniform(5, 50)
            })
        
        # 模拟车道几何
        self.lane_geometry = [
            {'distance': 0, 'curvature': 0},
            {'distance': 50, 'curvature': 0.001},
            {'distance': 100, 'curvature': 0}
        ]
    
    def acceleration_control(self, dt, current_speed):
        """加速度控制"""
        # 目标速度
        if self.forward_obstacles:
            # 自适应巡航 - 跟随前车
            closest_obstacle = min(self.forward_obstacles, key=lambda x: x['distance'])
            safe_distance = current_speed * self.follow_distance
            if closest_obstacle['distance'] < safe_distance:
                self.target_speed = closest_obstacle['speed']
            else:
                self.target_speed = self.cruise_speed
        else:
            self.target_speed = self.cruise_speed
        
        # PID控制
        speed_error = self.target_speed - current_speed
        control_output = self.acceleration_pid.update(speed_error, dt)
        
        if control_output > 0:
            throttle = min(1.0, control_output / 5)  # 归一化
            brake = 0
        else:
            throttle = 0
            brake = min(1.0, abs(control_output) / 5)  # 归一化
        
        return throttle, brake
    
    def steering_control(self, dt, current_position):
        """转向控制"""
        if not self.lane_keeping or not self.lane_geometry:
            return 0
        
        # 简单的车道保持
        # 在实际系统中，这会基于摄像头和传感器数据
        lane_curvature = self.lane_geometry[0]['curvature']
        
        # 基于曲率的转向
        steering_angle = lane_curvature * 100  # 简化模型
        
        # 添加一些噪声和微小调整模拟真实传感器
        steering_angle += math.sin(datetime.now().timestamp()) * 0.5
        
        return max(-1.0, min(1.0, steering_angle))

class PIDController:
    """PID控制器"""
    def __init__(self, kp, ki, kd):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.previous_error = 0
        self.integral = 0
    
    def update(self, error, dt):
        """更新PID输出"""
        self.integral += error * dt
        derivative = (error - self.previous_error) / dt if dt > 0 else 0
        
        output = (self.kp * error + 
                 self.ki * self.integral + 
                 self.kd * derivative)
        
        self.previous_error = error
        return output

class WorldEnvironment:
    """世界环境模拟"""
    def __init__(self):
        self.time_of_day = 12  # 小时
        self.weather = "Clear"  # Clear, Rain, Snow, Fog
        self.road_type = "Highway"  # Highway, Urban, Rural
        self.traffic_density = 0.3  # 0-1
        self.temperature = 20  # °C
        self.humidity = 50  # %
        self.wind_speed = 5  # km/h
        self.wind_direction = 0  # 度
        
        # 道路参数
        self.road_grade = 0  # 坡度 %
        self.road_curvature = 0  # 曲率 1/m
        self.speed_limit = 120  # km/h
        
        # 时间流逝
        self.time_multiplier = 60  # 时间加速倍数
    
    def update(self, dt):
        """更新环境状态"""
        # 更新时间
        self.time_of_day += (dt * self.time_multiplier) / 3600
        if self.time_of_day >= 24:
            self.time_of_day -= 24
        
        # 更新温度 (日夜变化)
        self.temperature = 15 + 10 * math.sin(self.time_of_day * math.pi / 12)
        
        # 随机天气变化
        if random.random() < 0.001:
            self.weather = random.choice(["Clear", "Rain", "Snow", "Fog"])
        
        # 更新道路参数
        self.road_grade = math.sin(self.time_of_day * 0.5) * 5  # 模拟上下坡
        self.road_curvature = math.sin(self.time_of_day * 0.3) * 0.001  # 模拟弯道
    
    def get_road_conditions(self):
        """获取道路条件"""
        conditions = {
            "friction": 0.8,  # 默认摩擦系数
            "visibility": 1000,  # 能见度 m
            "water_level": 0  # 路面水位 mm
        }
        
        if self.weather == "Rain":
            conditions["friction"] = 0.5
            conditions["visibility"] = 200
            conditions["water_level"] = 2
        elif self.weather == "Snow":
            conditions["friction"] = 0.3
            conditions["visibility"] = 100
        elif self.weather == "Fog":
            conditions["visibility"] = 50
        
        return conditions

class HighFidelityTeslaModel:
    """高保真特斯拉模型"""
    def __init__(self):
        self.battery = HighFidelityBattery()
        self.drive_system = AdvancedDriveSystem()
        self.autopilot = EnhancedAutopilot()
        self.environment = WorldEnvironment()
        
        # 车辆状态
        self.position = [0, 0]  # x, y 坐标
        self.heading = 0  # 航向角
        self.odometer = 0  # km
        self.trip_meter = 0  # km
        self.total_energy_used = 0  # kWh
        self.total_energy_recovered = 0  # kWh
        
        # 时间
        self.simulation_time = datetime.now()
    
    def update(self, dt, throttle_input=0, brake_input=0, steering_input=0):
        """更新整个车辆模型"""
        # 更新环境
        self.environment.update(dt)
        
        # 更新自动驾驶
        ap_throttle, ap_brake, ap_steering = self.autopilot.update(
            dt, self.drive_system.speed, self.position, self.environment.get_road_conditions())
        
        # 选择控制输入
        if self.autopilot.enabled:
            throttle = ap_throttle
            brake = ap_brake
            steering = ap_steering
        else:
            throttle = throttle_input
            brake = brake_input
            steering = steering_input
        
        # 更新驱动系统
        road_grade = self.environment.road_grade
        drive_power = self.drive_system.update(dt, throttle, brake, steering, road_grade)
        
        # 更新电池
        climate_power = 1.0  # 简化气候系统功耗
        total_power = max(0, drive_power) + climate_power
        actual_power = self.battery.update(dt, total_power)
        
        # 记录能量使用
        if drive_power > 0:
            self.total_energy_used += drive_power * dt / 3600
        elif drive_power < 0:
            self.total_energy_recovered += abs(drive_power) * dt / 3600
        
        # 更新位置
        distance = self.drive_system.speed * dt  # m
        self.odometer += distance / 1000  # km
        self.trip_meter += distance / 1000  # km
        
        # 更新航向
        turn_radius = 10 / max(0.1, abs(steering))  # 简化转向模型
        if abs(steering) > 0.1:
            angular_velocity = self.drive_system.speed / turn_radius
            self.heading += angular_velocity * dt
        
        # 更新位置
        self.position[0] += distance * math.cos(math.radians(self.heading))
        self.position[1] += distance * math.sin(math.radians(self.heading))
        
        # 更新时间
        self.simulation_time += timedelta(seconds=dt * self.environment.time_multiplier)

# 以下是UI组件，由于代码长度限制，这里只提供关键UI组件
class AdvancedDashboard(QWidget):
    """高级仪表盘"""
    def __init__(self):
        super().__init__()
        self.speed = 0
        self.power = 0
        self.battery_soc = 75
        self.battery_temp = 25
        self.motor_temp = 25
        self.autopilot_status = False
        self.setMinimumSize(400, 300)
        
    def set_data(self, speed, power, battery_soc, battery_temp, motor_temp, autopilot_status):
        self.speed = speed
        self.power = power
        self.battery_soc = battery_soc
        self.battery_temp = battery_temp
        self.motor_temp = motor_temp
        self.autopilot_status = autopilot_status
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 绘制背景
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0, QColor(20, 20, 30))
        gradient.setColorAt(1, QColor(10, 10, 20))
        painter.fillRect(self.rect(), gradient)
        
        # 绘制速度表
        self.draw_speedometer(painter)
        
        # 绘制功率表
        self.draw_power_meter(painter)
        
        # 绘制电池状态
        self.draw_battery_status(painter)
        
        # 绘制自动驾驶状态
        self.draw_autopilot_status(painter)
    
    def draw_speedometer(self, painter):
        # 速度表绘制代码
        center_x = self.width() // 4
        center_y = self.height() // 2
        radius = min(center_x, center_y) - 20
        
        # 绘制外圈
        painter.setPen(QPen(QColor(100, 100, 150), 3))
        painter.setBrush(QBrush(QColor(40, 40, 60)))
        painter.drawEllipse(center_x - radius, center_y - radius, radius * 2, radius * 2)
        
        # 绘制刻度
        painter.setPen(QPen(QColor(200, 200, 255), 2))
        for i in range(0, 260, 20):
            angle = math.radians(i * 270 / 260 - 225)
            start_x = center_x + (radius - 15) * math.cos(angle)
            start_y = center_y + (radius - 15) * math.sin(angle)
            end_x = center_x + (radius - 5) * math.cos(angle)
            end_y = center_y + (radius - 5) * math.sin(angle)
            painter.drawLine(int(start_x), int(start_y), int(end_x), int(end_y))
            
            # 绘制数字
            text_x = center_x + (radius - 30) * math.cos(angle)
            text_y = center_y + (radius - 30) * math.sin(angle)
            painter.drawText(int(text_x)-15, int(text_y)-10, 30, 20, 
                            Qt.AlignCenter, str(i))
        
        # 绘制指针
        speed_angle = (self.speed * 3.6 / 260) * 270 - 225  # 转换为km/h并计算角度
        angle_rad = math.radians(speed_angle)
        pointer_x = center_x + (radius - 25) * math.cos(angle_rad)
        pointer_y = center_y + (radius - 25) * math.sin(angle_rad)
        
        painter.setPen(QPen(QColor(255, 80, 80), 4))
        painter.drawLine(center_x, center_y, int(pointer_x), int(pointer_y))
        
        # 绘制速度文本
        painter.setPen(QColor(255, 255, 255))
        painter.setFont(QFont("Arial", 16, QFont.Bold))
        painter.drawText(center_x - 50, center_y - 60, 100, 40, 
                        Qt.AlignCenter, f"{int(self.speed * 3.6)} km/h")
        
        # 绘制速度标签
        painter.setFont(QFont("Arial", 10))
        painter.drawText(center_x - 30, center_y + 40, 60, 20, 
                        Qt.AlignCenter, "SPEED")
    
    def draw_power_meter(self, painter):
        # 功率表绘制代码
        center_x = self.width() * 3 // 4
        center_y = self.height() // 2
        width = 40
        height = 150
        
        # 绘制背景
        painter.setPen(QPen(QColor(100, 100, 150), 2))
        painter.setBrush(QBrush(QColor(40, 40, 60)))
        painter.drawRect(center_x - width//2, center_y - height//2, width, height)
        
        # 绘制功率条
        power_ratio = abs(self.power) / 300  # 假设最大功率300kW
        power_height = int(height * power_ratio)
        
        if self.power >= 0:
            # 放电 - 红色
            power_color = QColor(255, 50, 50)
        else:
            # 充电 - 绿色
            power_color = QColor(50, 255, 50)
        
        painter.setPen(QPen(power_color, 1))
        painter.setBrush(QBrush(power_color))
        
        if self.power >= 0:
            # 从中间向上绘制
            painter.drawRect(center_x - width//2 + 5, 
                           center_y - power_height//2, 
                           width - 10, power_height)
        else:
            # 从中间向下绘制
            painter.drawRect(center_x - width//2 + 5, 
                           center_y, 
                           width - 10, power_height)
        
        # 绘制刻度
        painter.setPen(QPen(QColor(200, 200, 255), 1))
        for i in range(0, 101, 25):
            y_pos = center_y - height//2 + (height * i // 100)
            painter.drawLine(center_x - width//2, y_pos, 
                           center_x - width//2 - 5, y_pos)
            painter.drawText(center_x - width//2 - 30, y_pos - 10, 
                           25, 20, Qt.AlignRight, f"{i}%")
        
        # 绘制功率值
        painter.setPen(QColor(255, 255, 255))
        painter.setFont(QFont("Arial", 10))
        painter.drawText(center_x - width//2, center_y + height//2 + 10, 
                       width, 20, Qt.AlignCenter, f"{self.power:.1f} kW")
        
        # 绘制标签
        painter.drawText(center_x - width//2, center_y - height//2 - 20, 
                       width, 20, Qt.AlignCenter, "POWER")
    
    def draw_battery_status(self, painter):
        # 电池状态绘制代码
        battery_x = 20
        battery_y = 20
        battery_width = 150
        battery_height = 60
        
        # 绘制电池外壳
        painter.setPen(QPen(QColor(150, 150, 200), 2))
        painter.setBrush(QBrush(QColor(50, 50, 70)))
        painter.drawRoundedRect(battery_x, battery_y, battery_width, battery_height, 5, 5)
        
        # 绘制电池正极
        painter.drawRoundedRect(battery_x + battery_width//2 - 10, battery_y - 5, 20, 5, 2, 2)
        
        # 绘制电量
        charge_width = int((battery_width - 10) * self.battery_soc / 100)
        charge_color = QColor(0, 200, 0) if self.battery_soc > 20 else QColor(255, 100, 0)
        
        painter.setPen(QPen(charge_color, 1))
        painter.setBrush(QBrush(charge_color))
        painter.drawRoundedRect(battery_x + 5, battery_y + 5, charge_width, battery_height - 10, 3, 3)
        
        # 绘制SOC文本
        painter.setPen(QColor(255, 255, 255))
        painter.setFont(QFont("Arial", 12, QFont.Bold))
        painter.drawText(battery_x, battery_y, battery_width, battery_height, 
                        Qt.AlignCenter, f"{self.battery_soc:.1f}%")
        
        # 绘制温度
        temp_color = QColor(255, 255, 255)
        if self.battery_temp > 40:
            temp_color = QColor(255, 100, 0)
        elif self.battery_temp > 50:
            temp_color = QColor(255, 0, 0)
            
        painter.setPen(temp_color)
        painter.setFont(QFont("Arial", 10))
        painter.drawText(battery_x, battery_y + battery_height, battery_width, 20, 
                        Qt.AlignCenter, f"Batt: {self.battery_temp:.1f}°C")
        
        # 绘制电机温度
        painter.drawText(battery_x, battery_y + battery_height + 20, battery_width, 20, 
                        Qt.AlignCenter, f"Motor: {self.motor_temp:.1f}°C")
    
    def draw_autopilot_status(self, painter):
        # 自动驾驶状态绘制代码
        status_x = self.width() - 170
        status_y = 20
        status_width = 150
        status_height = 40
        
        # 绘制状态背景
        if self.autopilot_status:
            status_color = QColor(0, 150, 0)
            status_text = "AUTOPILOT ON"
        else:
            status_color = QColor(100, 100, 100)
            status_text = "AUTOPILOT OFF"
        
        painter.setPen(QPen(status_color, 2))
        painter.setBrush(QBrush(status_color))
        painter.drawRoundedRect(status_x, status_y, status_width, status_height, 5, 5)
        
        # 绘制状态文本
        painter.setPen(QColor(255, 255, 255))
        painter.setFont(QFont("Arial", 12, QFont.Bold))
        painter.drawText(status_x, status_y, status_width, status_height, 
                        Qt.AlignCenter, status_text)

# 主窗口类
class HighFidelityTeslaSimulator(QMainWindow):
    def __init__(self):
        super().__init__()
        self.tesla = HighFidelityTeslaModel()
        self.init_ui()
        self.init_simulation()
        
    def init_ui(self):
        self.setWindowTitle("Tesla High-Fidelity Simulation Platform")
        self.setGeometry(100, 100, 1400, 900)
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        main_layout = QHBoxLayout()
        central_widget.setLayout(main_layout)
        
        # 左侧控制面板
        control_panel = self.create_control_panel()
        main_layout.addWidget(control_panel, 1)
        
        # 右侧仪表板
        dashboard = self.create_dashboard()
        main_layout.addWidget(dashboard, 2)
        
    def create_control_panel(self):
        # 控制面板创建代码
        panel = QWidget()
        panel.setStyleSheet("background-color: #2b2b2b; color: white; border-radius: 10px;")
        layout = QVBoxLayout()
        panel.setLayout(layout)
        
        # 添加各种控制组
        layout.addWidget(self.create_drive_control_group())
        layout.addWidget(self.create_autopilot_control_group())
        layout.addWidget(self.create_charging_control_group())
        layout.addWidget(self.create_environment_control_group())
        
        layout.addStretch()
        return panel
    
    def create_drive_control_group(self):
        # 驾驶控制组
        group = QGroupBox("驾驶控制")
        group.setStyleSheet("QGroupBox { color: white; font-weight: bold; }")
        layout = QGridLayout()
        group.setLayout(layout)
        
        # 油门控制
        self.throttle_slider = QSlider(Qt.Vertical)
        self.throttle_slider.setRange(0, 100)
        self.throttle_slider.setValue(0)
        layout.addWidget(QLabel("油门"), 0, 0)
        layout.addWidget(self.throttle_slider, 1, 0)
        
        # 刹车控制
        self.brake_slider = QSlider(Qt.Vertical)
        self.brake_slider.setRange(0, 100)
        self.brake_slider.setValue(0)
        layout.addWidget(QLabel("刹车"), 0, 1)
        layout.addWidget(self.brake_slider, 1, 1)
        
        # 转向控制
        self.steering_dial = QDial()
        self.steering_dial.setRange(-100, 100)
        self.steering_dial.setValue(0)
        layout.addWidget(QLabel("转向"), 2, 0, 1, 2)
        layout.addWidget(self.steering_dial, 3, 0, 1, 2)
        
        # 驾驶模式
        self.drive_mode_combo = QComboBox()
        self.drive_mode_combo.addItems(["Normal", "Sport", "Ludicrous"])
        layout.addWidget(QLabel("驾驶模式"), 4, 0)
        layout.addWidget(self.drive_mode_combo, 5, 0, 1, 2)
        
        # 能量回收
        self.regen_combo = QComboBox()
        self.regen_combo.addItems(["Standard", "Low", "Off"])
        layout.addWidget(QLabel("能量回收"), 6, 0)
        layout.addWidget(self.regen_combo, 7, 0, 1, 2)
        
        return group
    
    def create_autopilot_control_group(self):
        # 自动驾驶控制组
        group = QGroupBox("自动驾驶")
        group.setStyleSheet("QGroupBox { color: white; font-weight: bold; }")
        layout = QVBoxLayout()
        group.setLayout(layout)
        
        self.ap_toggle = QPushButton("启用自动驾驶")
        self.ap_toggle.setCheckable(True)
        self.ap_toggle.setStyleSheet("QPushButton { background-color: #444; color: white; }"
                                   "QPushButton:checked { background-color: #2a7; }")
        layout.addWidget(self.ap_toggle)
        
        # 巡航速度
        cruise_layout = QHBoxLayout()
        cruise_layout.addWidget(QLabel("巡航速度:"))
        self.cruise_speed_spin = QSpinBox()
        self.cruise_speed_spin.setRange(0, 150)
        self.cruise_speed_spin.setValue(80)
        self.cruise_speed_spin.setSuffix(" km/h")
        cruise_layout.addWidget(self.cruise_speed_spin)
        layout.addLayout(cruise_layout)
        
        # 跟车距离
        follow_layout = QHBoxLayout()
        follow_layout.addWidget(QLabel("跟车距离:"))
        self.follow_distance_combo = QComboBox()
        self.follow_distance_combo.addItems(["1", "2", "3", "4", "5", "6", "7"])
        self.follow_distance_combo.setCurrentIndex(1)
        self.follow_distance_combo.setItemData(0, "1秒 - 最近", Qt.ToolTipRole)
        self.follow_distance_combo.setItemData(6, "7秒 - 最远", Qt.ToolTipRole)
        follow_layout.addWidget(self.follow_distance_combo)
        layout.addLayout(follow_layout)
        
        # 自动驾驶功能
        self.lane_keeping_check = QCheckBox("车道保持")
        self.lane_keeping_check.setChecked(True)
        layout.addWidget(self.lane_keeping_check)
        
        self.auto_lane_change_check = QCheckBox("自动变道")
        layout.addWidget(self.auto_lane_change_check)
        
        self.navigation_check = QCheckBox("导航自动驾驶")
        layout.addWidget(self.navigation_check)
        
        return group
    
    def create_charging_control_group(self):
        # 充电控制组
        group = QGroupBox("充电控制")
        group.setStyleSheet("QGroupBox { color: white; font-weight: bold; }")
        layout = QVBoxLayout()
        group.setLayout(layout)
        
        # 充电器类型
        charger_layout = QHBoxLayout()
        charger_layout.addWidget(QLabel("充电器:"))
        self.charger_type_combo = QComboBox()
        self.charger_type_combo.addItems(["AC Level 1 (1.4kW)", "AC Level 2 (11.5kW)", 
                                         "DC Supercharger V2 (150kW)", "DC Supercharger V3 (250kW)"])
        charger_layout.addWidget(self.charger_type_combo)
        layout.addLayout(charger_layout)
        
        # 充电控制
        charge_control_layout = QHBoxLayout()
        self.charge_toggle = QPushButton("开始充电")
        self.charge_toggle.setCheckable(True)
        self.charge_toggle.setStyleSheet("QPushButton { background-color: #444; color: white; }"
                                       "QPushButton:checked { background-color: #2a7; }")
        charge_control_layout.addWidget(self.charge_toggle)
        
        self.charge_limit_spin = QSpinBox()
        self.charge_limit_spin.setRange(50, 100)
        self.charge_limit_spin.setValue(90)
        self.charge_limit_spin.setSuffix("%")
        charge_control_layout.addWidget(QLabel("充电限制:"))
        charge_control_layout.addWidget(self.charge_limit_spin)
        layout.addLayout(charge_control_layout)
        
        # 充电信息
        self.charge_info_label = QLabel("未充电")
        self.charge_info_label.setStyleSheet("background-color: #333; padding: 5px; border-radius: 3px;")
        layout.addWidget(self.charge_info_label)
        
        return group
    
    def create_environment_control_group(self):
        # 环境控制组
        group = QGroupBox("环境控制")
        group.setStyleSheet("QGroupBox { color: white; font-weight: bold; }")
        layout = QVBoxLayout()
        group.setLayout(layout)
        
        # 天气控制
        weather_layout = QHBoxLayout()
        weather_layout.addWidget(QLabel("天气:"))
        self.weather_combo = QComboBox()
        self.weather_combo.addItems(["Clear", "Rain", "Snow", "Fog"])
        weather_layout.addWidget(self.weather_combo)
        layout.addLayout(weather_layout)
        
        # 道路类型
        road_layout = QHBoxLayout()
        road_layout.addWidget(QLabel("道路:"))
        self.road_type_combo = QComboBox()
        self.road_type_combo.addItems(["Highway", "Urban", "Rural", "Mountain"])
        road_layout.addWidget(self.road_type_combo)
        layout.addLayout(road_layout)
        
        # 时间控制
        time_layout = QHBoxLayout()
        time_layout.addWidget(QLabel("时间:"))
        self.time_slider = QSlider(Qt.Horizontal)
        self.time_slider.setRange(0, 24*60)  # 分钟
        self.time_slider.setValue(12*60)  # 中午
        time_layout.addWidget(self.time_slider)
        layout.addLayout(time_layout)
        
        # 时间加速
        speed_layout = QHBoxLayout()
        speed_layout.addWidget(QLabel("时间速度:"))
        self.time_speed_combo = QComboBox()
        self.time_speed_combo.addItems(["1x", "10x", "60x", "360x"])
        self.time_speed_combo.setCurrentIndex(1)  # 默认10x
        speed_layout.addWidget(self.time_speed_combo)
        layout.addLayout(speed_layout)
        
        return group
    
    def create_dashboard(self):
        # 创建仪表板
        dashboard = QWidget()
        dashboard.setStyleSheet("background-color: #1a1a1a; color: white; border-radius: 10px;")
        layout = QVBoxLayout()
        dashboard.setLayout(layout)
        
        # 高级仪表盘
        self.advanced_dashboard = AdvancedDashboard()
        layout.addWidget(self.advanced_dashboard)
        
        # 数据监控区域
        data_monitor = self.create_data_monitor()
        layout.addWidget(data_monitor)
        
        return dashboard
    
    def create_data_monitor(self):
        # 数据监控区域
        monitor = QWidget()
        layout = QGridLayout()
        monitor.setLayout(layout)
        
        # 电池信息
        battery_group = QGroupBox("电池信息")
        battery_layout = QVBoxLayout()
        battery_group.setLayout(battery_layout)
        
        self.battery_voltage_label = QLabel("电压: 0 V")
        battery_layout.addWidget(self.battery_voltage_label)
        
        self.battery_current_label = QLabel("电流: 0 A")
        battery_layout.addWidget(self.battery_current_label)
        
        self.battery_health_label = QLabel("健康度: 100 %")
        battery_layout.addWidget(self.battery_health_label)
        
        self.battery_range_label = QLabel("续航: 0 km")
        battery_layout.addWidget(self.battery_range_label)
        
        layout.addWidget(battery_group, 0, 0)
        
        # 驱动信息
        drive_group = QGroupBox("驱动信息")
        drive_layout = QVBoxLayout()
        drive_group.setLayout(drive_layout)
        
        self.drive_power_label = QLabel("总功率: 0 kW")
        drive_layout.addWidget(self.drive_power_label)
        
        self.drive_torque_label = QLabel("前扭矩: 0 Nm | 后扭矩: 0 Nm")
        drive_layout.addWidget(self.drive_torque_label)
        
        self.drive_rpm_label = QLabel("前电机: 0 RPM | 后电机: 0 RPM")
        drive_layout.addWidget(self.drive_rpm_label)
        
        self.drive_accel_label = QLabel("加速度: 0 m/s²")
        drive_layout.addWidget(self.drive_accel_label)
        
        layout.addWidget(drive_group, 0, 1)
        
        # 能量信息
        energy_group = QGroupBox("能量信息")
        energy_layout = QVBoxLayout()
        energy_group.setLayout(energy_layout)
        
        self.energy_used_label = QLabel("已用电量: 0 kWh")
        energy_layout.addWidget(self.energy_used_label)
        
        self.energy_recovered_label = QLabel("回收能量: 0 kWh")
        energy_layout.addWidget(self.energy_recovered_label)
        
        self.energy_efficiency_label = QLabel("能效: 0 Wh/km")
        energy_layout.addWidget(self.energy_efficiency_label)
        
        self.odometer_label = QLabel("总里程: 0 km")
        energy_layout.addWidget(self.odometer_label)
        
        layout.addWidget(energy_group, 1, 0)
        
        # 环境信息
        environment_group = QGroupBox("环境信息")
        environment_layout = QVBoxLayout()
        environment_group.setLayout(environment_layout)
        
        self.env_time_label = QLabel("时间: 12:00")
        environment_layout.addWidget(self.env_time_label)
        
        self.env_weather_label = QLabel("天气: Clear")
        environment_layout.addWidget(self.env_weather_label)
        
        self.env_temp_label = QLabel("温度: 20 °C")
        environment_layout.addWidget(self.env_temp_label)
        
        self.env_road_label = QLabel("道路: 坡度 0% | 曲率 0")
        environment_layout.addWidget(self.env_road_label)
        
        layout.addWidget(environment_group, 1, 1)
        
        return monitor
    
    def init_simulation(self):
        """初始化仿真"""
        self.simulation_timer = QTimer()
        self.simulation_timer.timeout.connect(self.update_simulation)
        self.simulation_timer.start(50)  # 20Hz更新频率
        
        # 初始化控制变量
        self.throttle_input = 0
        self.brake_input = 0
        self.steering_input = 0
        
        # 连接信号
        self.throttle_slider.valueChanged.connect(self.on_throttle_change)
        self.brake_slider.valueChanged.connect(self.on_brake_change)
        self.steering_dial.valueChanged.connect(self.on_steering_change)
        self.drive_mode_combo.currentTextChanged.connect(self.on_drive_mode_change)
        self.regen_combo.currentTextChanged.connect(self.on_regen_change)
        self.ap_toggle.toggled.connect(self.on_autopilot_toggle)
        self.cruise_speed_spin.valueChanged.connect(self.on_cruise_speed_change)
        self.follow_distance_combo.currentTextChanged.connect(self.on_follow_distance_change)
        self.lane_keeping_check.toggled.connect(self.on_lane_keeping_change)
        self.auto_lane_change_check.toggled.connect(self.on_auto_lane_change)
        self.charge_toggle.toggled.connect(self.on_charge_toggle)
        self.charger_type_combo.currentTextChanged.connect(self.on_charger_type_change)
        self.weather_combo.currentTextChanged.connect(self.on_weather_change)
        self.road_type_combo.currentTextChanged.connect(self.on_road_type_change)
        self.time_slider.valueChanged.connect(self.on_time_change)
        self.time_speed_combo.currentTextChanged.connect(self.on_time_speed_change)
    
    def update_simulation(self):
        """更新仿真"""
        dt = 0.05  # 50ms
        
        # 更新特斯拉模型
        self.tesla.update(dt, self.throttle_input/100, self.brake_input/100, self.steering_input/100)
        
        # 更新UI显示
        self.update_display()
    
    def update_display(self):
        """更新显示"""
        # 更新高级仪表盘
        self.advanced_dashboard.set_data(
            self.tesla.drive_system.speed,
            self.tesla.drive_system.power,
            self.tesla.battery.get_state_of_charge(),
            self.tesla.battery.temperature,
            max(self.tesla.drive_system.motor_temp_front, self.tesla.drive_system.motor_temp_rear),
            self.tesla.autopilot.enabled
        )
        
        # 更新电池信息
        self.battery_voltage_label.setText(f"电压: {self.tesla.battery.voltage:.1f} V")
        self.battery_current_label.setText(f"电流: {self.tesla.battery.current:.1f} A")
        self.battery_health_label.setText(f"健康度: {self.tesla.battery.health*100:.1f} %")
        self.battery_range_label.setText(f"续航: {self.tesla.battery.get_range():.1f} km")
        
        # 更新驱动信息
        self.drive_power_label.setText(f"总功率: {self.tesla.drive_system.power:.1f} kW")
        self.drive_torque_label.setText(f"前扭矩: {self.tesla.drive_system.torque_front:.1f} Nm | 后扭矩: {self.tesla.drive_system.torque_rear:.1f} Nm")
        self.drive_rpm_label.setText(f"前电机: {self.tesla.drive_system.motor_rpm_front:.0f} RPM | 后电机: {self.tesla.drive_system.motor_rpm_rear:.0f} RPM")
        self.drive_accel_label.setText(f"加速度: {self.tesla.drive_system.acceleration:.2f} m/s²")
        
        # 更新能量信息
        self.energy_used_label.setText(f"已用电量: {self.tesla.total_energy_used:.2f} kWh")
        self.energy_recovered_label.setText(f"回收能量: {self.tesla.total_energy_recovered:.2f} kWh")
        efficiency = self.tesla.total_energy_used / max(0.1, self.tesla.odometer) * 1000 if self.tesla.total_energy_used > 0 else 0
        self.energy_efficiency_label.setText(f"能效: {efficiency:.1f} Wh/km")
        self.odometer_label.setText(f"总里程: {self.tesla.odometer:.2f} km")
        
        # 更新环境信息
        time_str = f"{int(self.tesla.environment.time_of_day):02d}:{int((self.tesla.environment.time_of_day % 1) * 60):02d}"
        self.env_time_label.setText(f"时间: {time_str}")
        self.env_weather_label.setText(f"天气: {self.tesla.environment.weather}")
        self.env_temp_label.setText(f"温度: {self.tesla.environment.temperature:.1f} °C")
        self.env_road_label.setText(f"道路: 坡度 {self.tesla.environment.road_grade:.1f}% | 曲率 {self.tesla.environment.road_curvature:.4f}")
        
        # 更新充电信息
        if self.tesla.battery.is_charging:
            charge_rate = self.tesla.battery.charging_current * self.tesla.battery.charging_voltage / 1000
            time_to_full = (self.tesla.battery.total_energy * (1 - self.tesla.battery.state_of_charge)) / charge_rate if charge_rate > 0 else 0
            self.charge_info_label.setText(f"充电中: {charge_rate:.1f} kW, 充满需 {time_to_full:.1f} 小时")
        else:
            self.charge_info_label.setText("未充电")
    
    # 事件处理函数
    def on_throttle_change(self, value):
        self.throttle_input = value
    
    def on_brake_change(self, value):
        self.brake_input = value
    
    def on_steering_change(self, value):
        self.steering_input = value
    
    def on_drive_mode_change(self, mode):
        self.tesla.drive_system.drive_mode = mode
    
    def on_regen_change(self, mode):
        self.tesla.drive_system.regenerative_braking = mode
    
    def on_autopilot_toggle(self, enabled):
        self.tesla.autopilot.enabled = enabled
        if enabled:
            self.ap_toggle.setText("禁用自动驾驶")
            self.tesla.autopilot.cruise_speed = self.cruise_speed_spin.value() / 3.6  # 转换为m/s
        else:
            self.ap_toggle.setText("启用自动驾驶")
    
    def on_cruise_speed_change(self, speed):
        self.tesla.autopilot.cruise_speed = speed / 3.6  # 转换为m/s
    
    def on_follow_distance_change(self, distance):
        self.tesla.autopilot.follow_distance = float(distance)
    
    def on_lane_keeping_change(self, enabled):
        self.tesla.autopilot.lane_keeping = enabled
    
    def on_auto_lane_change(self, enabled):
        self.tesla.autopilot.auto_lane_change = enabled
    
    def on_charge_toggle(self, enabled):
        if enabled:
            charger_type = self.charger_type_combo.currentText()
            if "DC" in charger_type:
                # DC快充
                if "V3" in charger_type:
                    power = 250
                else:
                    power = 150
                self.tesla.battery.start_charging("DC", power=power)
            else:
                # AC充电
                if "Level 1" in charger_type:
                    voltage, current = 120, 12
                else:
                    voltage, current = 240, 48
                self.tesla.battery.start_charging("AC", voltage=voltage, current=current)
            
            self.charge_toggle.setText("停止充电")
        else:
            self.tesla.battery.stop_charging()
            self.charge_toggle.setText("开始充电")
    
    def on_charger_type_change(self, charger_type):
        # 充电器类型改变时更新充电状态
        if self.tesla.battery.is_charging:
            # 重新开始充电以应用新设置
            self.on_charge_toggle(False)
            self.on_charge_toggle(True)
    
    def on_weather_change(self, weather):
        self.tesla.environment.weather = weather
    
    def on_road_type_change(self, road_type):
        self.tesla.environment.road_type = road_type
        # 根据道路类型更新限速
        if road_type == "Highway":
            self.tesla.environment.speed_limit = 120
        elif road_type == "Urban":
            self.tesla.environment.speed_limit = 60
        elif road_type == "Rural":
            self.tesla.environment.speed_limit = 80
        else:  # Mountain
            self.tesla.environment.speed_limit = 40
    
    def on_time_change(self, minutes):
        hours = minutes / 60
        self.tesla.environment.time_of_day = hours
    
    def on_time_speed_change(self, speed):
        multiplier_map = {"1x": 1, "10x": 10, "60x": 60, "360x": 360}
        self.tesla.environment.time_multiplier = multiplier_map.get(speed, 10)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 设置应用程序样式
    app.setStyle("Fusion")
    
    # 创建暗色主题
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(53, 53, 53))
    palette.setColor(QPalette.WindowText, Qt.white)
    palette.setColor(QPalette.Base, QColor(25, 25, 25))
    palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
    palette.setColor(QPalette.ToolTipBase, Qt.white)
    palette.setColor(QPalette.ToolTipText, Qt.white)
    palette.setColor(QPalette.Text, Qt.white)
    palette.setColor(QPalette.Button, QColor(53, 53, 53))
    palette.setColor(QPalette.ButtonText, Qt.white)
    palette.setColor(QPalette.BrightText, Qt.red)
    palette.setColor(QPalette.Link, QColor(42, 130, 218))
    palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.HighlightedText, Qt.black)
    app.setPalette(palette)
    
    # 创建并显示主窗口
    simulator = HighFidelityTeslaSimulator()
    simulator.show()
    
    sys.exit(app.exec_())