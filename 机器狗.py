import sys
import numpy as np
import math
import json
import time
import random
from collections import deque
from scipy.spatial.transform import Rotation as R
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                             QWidget, QPushButton, QSlider, QLabel, QGroupBox,
                             QTabWidget, QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox,
                             QCheckBox, QFileDialog, QMessageBox, QProgressBar,
                             QSplitter, QTableWidget, QTableWidgetItem, QHeaderView,
                             QTreeWidget, QTreeWidgetItem, QListWidget, QLineEdit)
from PyQt5.QtCore import QTimer, Qt, QThread, pyqtSignal, QSettings, QDateTime
from PyQt5.QtGui import QFont, QPalette, QColor, QIcon, QPixmap, QPainter
from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import glutSolidSphere, glutSolidCube, glutSolidCone
from PyQt5.QtOpenGL import QGLWidget
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from OpenGL.GLUT import GLUT_DOUBLE, GLUT_RGB, GLUT_DEPTH

# 高级物理引擎
class AdvancedPhysicsEngine:
    def __init__(self):
        self.gravity = np.array([0, -9.81, 0])
        self.time_step = 0.001
        self.robots = []
        self.terrain = None
        self.air_density = 1.2
        self.friction_coefficient = 0.8
        
    def add_robot(self, robot):
        self.robots.append(robot)
        
    def set_terrain(self, terrain):
        self.terrain = terrain
        
    def update(self):
        for robot in self.robots:
            # 计算合力
            total_force = np.zeros(3)
            
            # 重力
            total_force += robot.mass * self.gravity
            
            # 空气阻力
            air_resistance = -0.5 * self.air_density * robot.drag_coefficient * \
                           robot.cross_sectional_area * np.linalg.norm(robot.velocity) * robot.velocity
            total_force += air_resistance
            
            # 地面反作用力
            ground_force = self.calculate_ground_force(robot)
            total_force += ground_force
            
            # 更新加速度、速度、位置
            robot.acceleration = total_force / robot.mass
            robot.velocity += robot.acceleration * self.time_step
            robot.position += robot.velocity * self.time_step
            
            # 更新角速度、角加速度
            robot.angular_acceleration = robot.torque / robot.moment_of_inertia
            robot.angular_velocity += robot.angular_acceleration * self.time_step
            robot.orientation = self.update_orientation(robot.orientation, robot.angular_velocity, self.time_step)
            
            # 更新足端位置
            robot.update_foot_positions()
            
            # 检测碰撞
            self.handle_collisions(robot)
    
    def calculate_ground_force(self, robot):
        ground_force = np.zeros(3)
        
        # 简化的地面接触模型
        for i, foot_pos in enumerate(robot.foot_positions):
            # 检查足端是否接触地面
            if foot_pos[1] <= 0.01:  # 接近地面
                # 法向力（支撑力）
                penetration_depth = max(0.01 - foot_pos[1], 0)
                normal_force = robot.leg_stiffness * penetration_depth
                ground_force[1] += normal_force
                
                # 摩擦力
                if np.linalg.norm(robot.velocity) > 0.01:
                    friction_direction = -robot.velocity / np.linalg.norm(robot.velocity)
                    friction_force = self.friction_coefficient * normal_force * friction_direction
                    friction_force[1] = 0  # 摩擦力只在水平方向
                    ground_force += friction_force
        
        return ground_force
    
    def update_orientation(self, orientation, angular_velocity, dt):
        # 使用四元数更新方向
        q = R.from_matrix(orientation)
        rotation_vector = angular_velocity * dt
        if np.linalg.norm(rotation_vector) > 0:
            q_rot = R.from_rotvec(rotation_vector)
            q = q_rot * q
        return q.as_matrix()
    
    def handle_collisions(self, robot):
        # 简化的碰撞处理
        if robot.position[1] < 0:
            robot.position[1] = 0
            robot.velocity[1] = max(0, robot.velocity[1])  # 不能向下穿透
            
            # 能量损失
            robot.velocity *= 0.8

# 高级机器狗模型
class AdvancedRobotDog:
    def __init__(self):
        # 身体参数
        self.body_length = 0.4
        self.body_width = 0.2
        self.body_height = 0.15
        self.mass = 5.0  # kg
        self.moment_of_inertia = np.array([0.1, 0.2, 0.1])  # 简化惯性张量
        self.drag_coefficient = 0.8
        self.cross_sectional_area = 0.1
        
        # 腿参数
        self.upper_leg_length = 0.2
        self.lower_leg_length = 0.2
        self.leg_stiffness = 1000.0  # N/m
        
        # 状态变量
        self.position = np.array([0.0, 0.4, 0.0])
        self.velocity = np.zeros(3)
        self.acceleration = np.zeros(3)
        self.orientation = np.eye(3)  # 初始方向矩阵
        self.angular_velocity = np.zeros(3)
        self.angular_acceleration = np.zeros(3)
        self.torque = np.zeros(3)
        
        # 关节参数（每条腿3个关节：髋、大腿、小腿）
        self.joint_angles = np.zeros((4, 3))  # 4条腿，每条腿3个关节
        self.joint_velocities = np.zeros((4, 3))
        self.joint_targets = np.zeros((4, 3))
        
        # 足端位置
        self.foot_positions = np.zeros((4, 3))
        
        # 传感器数据
        self.imu_data = {
            'acceleration': np.zeros(3),
            'gyro': np.zeros(3),
            'orientation': np.eye(3)
        }
        
        # 控制参数
        self.gait_type = "trot"  # 步态类型
        self.gait_phase = 0.0
        self.gait_frequency = 2.0  # Hz
        self.step_height = 0.1
        self.step_length = 0.2
        
        # 运动目标
        self.target_velocity = np.zeros(3)
        self.target_position = np.zeros(3)
        
        # 初始化足端位置
        self.update_foot_positions()
    
    def update_foot_positions(self):
        # 身体坐标系中的足端默认位置
        body_foot_positions = np.array([
            [-self.body_length/2, 0, self.body_width/2],   # 前左
            [-self.body_length/2, 0, -self.body_width/2],  # 前右
            [self.body_length/2, 0, self.body_width/2],    # 后左
            [self.body_length/2, 0, -self.body_width/2]    # 后右
        ])
        
        # 转换到世界坐标系
        for i in range(4):
            self.foot_positions[i] = self.position + np.dot(self.orientation, body_foot_positions[i])
    
    def update_sensors(self):
        # 更新IMU数据（简化模型）
        self.imu_data['acceleration'] = self.acceleration.copy()
        self.imu_data['gyro'] = self.angular_velocity.copy()
        self.imu_data['orientation'] = self.orientation.copy()
    
    def set_gait(self, gait_type, frequency=2.0, step_height=0.1, step_length=0.2):
        self.gait_type = gait_type
        self.gait_frequency = frequency
        self.step_height = step_height
        self.step_length = step_length
    
    def update_gait(self, dt):
        self.gait_phase += dt * self.gait_frequency * 2 * math.pi
        if self.gait_phase >= 2 * math.pi:
            self.gait_phase -= 2 * math.pi
            
        # 根据步态类型生成足端轨迹
        if self.gait_type == "trot":
            self.trot_gait(dt)
        elif self.gait_type == "walk":
            self.walk_gait(dt)
        elif self.gait_type == "pace":
            self.pace_gait(dt)
        elif self.gait_type == "gallop":
            self.gallop_gait(dt)
        
        # 更新关节目标
        self.update_joint_targets()
    
    def trot_gait(self, dt):
        # 对角步态
        phase_offsets = [0, math.pi, math.pi, 0]  # 前左、前右、后左、后右
        
        for i in range(4):
            phase = self.gait_phase + phase_offsets[i]
            swing_phase = math.sin(phase)
            
            # 摆动相和支撑相
            if swing_phase > 0:  # 摆动相
                # 足端轨迹（贝塞尔曲线简化）
                t = (swing_phase + 1) / 2  # 归一化到[0,1]
                foot_target = self.calculate_swing_trajectory(i, t)
            else:  # 支撑相
                foot_target = self.calculate_stance_position(i)
            
            # 逆运动学计算关节角度
            self.joint_targets[i] = self.inverse_kinematics(i, foot_target)
    
    def calculate_swing_trajectory(self, leg_index, t):
        # 简化的摆动轨迹（抛物线）
        start_pos = self.foot_positions[leg_index].copy()
        end_pos = start_pos + np.array([self.step_length, 0, 0])
        
        # 抛物线轨迹
        height = self.step_height * 4 * t * (1 - t)  # 抛物线
        
        # 线性插值
        foot_target = start_pos + (end_pos - start_pos) * t
        foot_target[1] = height
        
        return foot_target
    
    def calculate_stance_position(self, leg_index):
        # 支撑相，足端相对身体位置固定
        body_foot_positions = np.array([
            [-self.body_length/2, 0, self.body_width/2],
            [-self.body_length/2, 0, -self.body_width/2],
            [self.body_length/2, 0, self.body_width/2],
            [self.body_length/2, 0, -self.body_width/2]
        ])
        
        return self.position + np.dot(self.orientation, body_foot_positions[leg_index])
    
    def inverse_kinematics(self, leg_index, target_foot_position):
        # 简化的逆运动学
        # 实际应用中应使用更精确的模型
        
        # 身体坐标系中的目标位置
        body_target = np.dot(self.orientation.T, target_foot_position - self.position)
        
        # 髋关节位置（身体坐标系）
        hip_positions = np.array([
            [-self.body_length/2, 0, self.body_width/2],
            [-self.body_length/2, 0, -self.body_width/2],
            [self.body_length/2, 0, self.body_width/2],
            [self.body_length/2, 0, -self.body_width/2]
        ])
        
        hip_pos = hip_positions[leg_index]
        relative_pos = body_target - hip_pos
        
        # 计算关节角度（简化模型）
        x, y, z = relative_pos
        L = np.sqrt(y**2 + z**2)
        
        # 髋关节角度（绕Y轴）
        hip_angle = math.atan2(z, y) if abs(y) > 1e-6 or abs(z) > 1e-6 else 0.0
        
        # 大腿和小腿角度（在XZ平面）
        D = np.sqrt(x**2 + L**2)
        if D > self.upper_leg_length + self.lower_leg_length:
            D = self.upper_leg_length + self.lower_leg_length - 0.01
        
        # 安全检查：避免除以零
        if D < 1e-6 or self.upper_leg_length < 1e-6:
            # 返回默认角度
            return np.array([hip_angle, 0.0, -math.pi/2])
        
        # 使用余弦定理
        cos_alpha = (self.upper_leg_length**2 + D**2 - self.lower_leg_length**2) / (2 * self.upper_leg_length * D)
        cos_beta = (self.upper_leg_length**2 + self.lower_leg_length**2 - D**2) / (2 * self.upper_leg_length * self.lower_leg_length)
        
        # 限制余弦值在有效范围内
        cos_alpha = max(min(cos_alpha, 1.0), -1.0)
        cos_beta = max(min(cos_beta, 1.0), -1.0)
        
        alpha = math.acos(cos_alpha)
        beta = math.acos(cos_beta)
        
        # 安全检查：避免数学错误
        if L < 1e-6:
            thigh_angle = alpha
        else:
            thigh_angle = alpha + math.atan2(x, L)
        
        knee_angle = beta - math.pi  # 膝关节通常为负角度
        
        return np.array([hip_angle, thigh_angle, knee_angle])
    
    def apply_control(self, dt):
        # PD控制器控制关节
        kp = 100.0  # 比例增益
        kd = 10.0   # 微分增益
        
        for i in range(4):
            for j in range(3):
                error = self.joint_targets[i][j] - self.joint_angles[i][j]
                self.joint_velocities[i][j] = kp * error - kd * self.joint_velocities[i][j]
                self.joint_angles[i][j] += self.joint_velocities[i][j] * dt
        
        # 限制关节角度范围
        self.joint_angles = np.clip(self.joint_angles, 
                                   [-math.pi/2, -math.pi/2, -math.pi], 
                                   [math.pi/2, math.pi/2, 0])
        
    def update_joint_targets(self):
        """更新关节目标角度"""
        # 这个方法实际上已经在各个步态函数中直接设置了 joint_targets
        # 所以这里可以留空，或者添加一些额外的处理逻辑
        pass

    def walk_gait(self, dt):
        """行走步态"""
        # 四脚步态，相位偏移为90度
        phase_offsets = [0, math.pi/2, math.pi, 3*math.pi/2]  # 前左、前右、后左、后右
        
        for i in range(4):
            phase = self.gait_phase + phase_offsets[i]
            swing_phase = math.sin(phase)
            
            # 摆动相和支撑相
            if swing_phase > 0:  # 摆动相
                t = (swing_phase + 1) / 2  # 归一化到[0,1]
                foot_target = self.calculate_swing_trajectory(i, t)
            else:  # 支撑相
                foot_target = self.calculate_stance_position(i)
            
            self.joint_targets[i] = self.inverse_kinematics(i, foot_target)

    def pace_gait(self, dt):
        """溜蹄步态"""
        # 同侧步态
        phase_offsets = [0, math.pi, 0, math.pi]  # 前左、前右、后左、后右
        
        for i in range(4):
            phase = self.gait_phase + phase_offsets[i]
            swing_phase = math.sin(phase)
            
            if swing_phase > 0:  # 摆动相
                t = (swing_phase + 1) / 2
                foot_target = self.calculate_swing_trajectory(i, t)
            else:  # 支撑相
                foot_target = self.calculate_stance_position(i)
            
            self.joint_targets[i] = self.inverse_kinematics(i, foot_target)

    def gallop_gait(self, dt):
        """奔跑步态"""
        # 奔跑步态，前后腿几乎同时移动
        phase_offsets = [0, math.pi/4, math.pi/2, 3*math.pi/4]  # 前左、前右、后左、后右
        
        for i in range(4):
            phase = self.gait_phase + phase_offsets[i]
            swing_phase = math.sin(phase)
            
            if swing_phase > 0:  # 摆动相
                t = (swing_phase + 1) / 2
                foot_target = self.calculate_swing_trajectory(i, t)
            else:  # 支撑相
                foot_target = self.calculate_stance_position(i)
            
            self.joint_targets[i] = self.inverse_kinematics(i, foot_target)

# AI控制模块
class AIController:
    def __init__(self, robot):
        self.robot = robot
        self.mode = "manual"  # manual, autonomous, learning
        self.target_point = np.zeros(3)
        self.obstacles = []
        self.path = []
        self.current_path_index = 0
        
    def set_autonomous_mode(self, target_point):
        self.mode = "autonomous"
        self.target_point = target_point
        self.plan_path()
        
    def plan_path(self):
        # 简化的路径规划（A*算法简化版）
        start = self.robot.position.copy()
        goal = self.target_point.copy()
        
        # 直接路径（实际应用中应使用更复杂的路径规划算法）
        self.path = [start, goal]
        self.current_path_index = 0
        
    def update(self, dt):
        if self.mode == "autonomous":
            self.follow_path(dt)
            
    def follow_path(self, dt):
        if not self.path or self.current_path_index >= len(self.path):
            return
            
        current_target = self.path[self.current_path_index]
        direction = current_target - self.robot.position
        distance = np.linalg.norm(direction)
        
        if distance < 0.1:  # 到达路径点
            self.current_path_index += 1
            if self.current_path_index >= len(self.path):
                return
            current_target = self.path[self.current_path_index]
            direction = current_target - self.robot.position
            distance = np.linalg.norm(direction)
        
        if distance > 0:
            direction = direction / distance
            # 设置目标速度
            self.robot.target_velocity = direction * min(1.0, distance)  # 接近目标时减速
            
            # 设置身体方向
            if np.linalg.norm(self.robot.target_velocity) > 0.1:
                forward_dir = self.robot.target_velocity / np.linalg.norm(self.robot.target_velocity)
                # 简化的方向控制
                # 实际应用中应使用更精确的方向控制

# 环境模拟
class Environment:
    def __init__(self):
        self.terrain = None
        self.obstacles = []
        self.targets = []
        
    def generate_terrain(self, type="flat", size=10, complexity=0.5):
        if type == "flat":
            self.terrain = np.zeros((size, size))
        elif type == "hilly":
            self.terrain = self.generate_hilly_terrain(size, complexity)
        elif type == "stairs":
            self.terrain = self.generate_stair_terrain(size)
            
    def generate_hilly_terrain(self, size, complexity):
        terrain = np.zeros((size, size))
        # 简化的小山生成
        for i in range(size):
            for j in range(size):
                terrain[i][j] = 0.2 * math.sin(i * complexity) * math.cos(j * complexity)
        return terrain
    
    def generate_stair_terrain(self, size):
        terrain = np.zeros((size, size))
        # 生成阶梯地形
        step_height = 0.1
        for i in range(size):
            for j in range(size):
                terrain[i][j] = (i // 3) * step_height
        return terrain
    
    def add_obstacle(self, position, size, type="cube"):
        self.obstacles.append({
            'position': position,
            'size': size,
            'type': type
        })
    
    def add_target(self, position):
        self.targets.append(position)

# 数据记录和分析模块
class DataLogger:
    def __init__(self):
        self.data = {
            'time': [],
            'position': [],
            'velocity': [],
            'orientation': [],
            'joint_angles': [],
            'sensor_data': [],
            'control_inputs': []
        }
        self.start_time = time.time()
        
    def log(self, robot, control_inputs=None):
        current_time = time.time() - self.start_time
        self.data['time'].append(current_time)
        self.data['position'].append(robot.position.copy())
        self.data['velocity'].append(robot.velocity.copy())
        self.data['orientation'].append(robot.orientation.copy())
        self.data['joint_angles'].append(robot.joint_angles.copy())
        self.data['sensor_data'].append(robot.imu_data.copy())
        self.data['control_inputs'].append(control_inputs if control_inputs else {})
        
    def save_to_file(self, filename):
        # 转换为可序列化的格式
        serializable_data = {}
        for key, value in self.data.items():
            if key in ['position', 'velocity', 'orientation', 'joint_angles']:
                serializable_data[key] = [arr.tolist() for arr in value]
            elif key == 'sensor_data':
                serializable_data[key] = []
                for sensor_frame in value:
                    serializable_sensor = {}
                    for sensor_key, sensor_value in sensor_frame.items():
                        if isinstance(sensor_value, np.ndarray):
                            serializable_sensor[sensor_key] = sensor_value.tolist()
                        elif isinstance(sensor_value, np.ndarray):
                            serializable_sensor[sensor_key] = sensor_value.tolist()
                        else:
                            serializable_sensor[sensor_key] = sensor_value
                    serializable_data[key].append(serializable_sensor)
            else:
                serializable_data[key] = value
                
        with open(filename, 'w') as f:
            json.dump(serializable_data, f, indent=2)
            
    def load_from_file(self, filename):
        with open(filename, 'r') as f:
            serializable_data = json.load(f)
            
        # 转换回numpy数组
        self.data = {}
        for key, value in serializable_data.items():
            if key in ['position', 'velocity', 'joint_angles']:
                self.data[key] = [np.array(arr) for arr in value]
            elif key == 'orientation':
                self.data[key] = [np.array(arr) for arr in value]
            elif key == 'sensor_data':
                self.data[key] = []
                for sensor_frame in value:
                    sensor_data = {}
                    for sensor_key, sensor_value in sensor_frame.items():
                        if isinstance(sensor_value, list):
                            sensor_data[sensor_key] = np.array(sensor_value)
                        else:
                            sensor_data[sensor_key] = sensor_value
                    self.data[key].append(sensor_data)
            else:
                self.data[key] = value

# 高级3D可视化组件
class AdvancedGLWidget(QGLWidget):
    def __init__(self, parent=None):
        super(AdvancedGLWidget, self).__init__(parent)
        self.robot = None
        self.environment = None
        self.xRot = 0
        self.yRot = 0
        self.zRot = 0
        self.zoom = 5.0
        self.show_trajectory = True
        self.trajectory_points = deque(maxlen=1000)
        self.show_coordinates = True
        self.show_grid = True
        
        # 初始化glut（使用虚拟参数）
        try:
            import sys
            from OpenGL.GLUT import glutInit, glutInitDisplayMode
            # 保存原始argv
            old_argv = sys.argv
            sys.argv = [old_argv[0]]  # 只保留程序名
            glutInit(sys.argv)
            glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
            # 恢复原始argv
            sys.argv = old_argv
        except Exception as e:
            print(f"GLUT初始化警告: {e}")
        
    def initializeGL(self):
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        glLightfv(GL_LIGHT0, GL_POSITION, [5, 5, 5, 1])
        glLightfv(GL_LIGHT0, GL_AMBIENT, [0.2, 0.2, 0.2, 1])
        glLightfv(GL_LIGHT0, GL_DIFFUSE, [0.8, 0.8, 0.8, 1])
        glEnable(GL_COLOR_MATERIAL)
        glClearColor(0.1, 0.1, 0.2, 1.0)
        
    def resizeGL(self, w, h):
        glViewport(0, 0, w, h)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(45, w/h, 0.1, 100.0)
        glMatrixMode(GL_MODELVIEW)
        
    def paintGL(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        
        # 设置相机
        gluLookAt(0, 3, self.zoom, 0, 0, 0, 0, 1, 0)
        
        # 旋转场景
        glRotatef(self.xRot, 1.0, 0.0, 0.0)
        glRotatef(self.yRot, 0.0, 1.0, 0.0)
        glRotatef(self.zRot, 0.0, 0.0, 1.0)
        
        # 绘制坐标轴
        if self.show_coordinates:
            self.draw_axes()
        
        # 绘制网格
        if self.show_grid:
            self.draw_grid()
        
        # 绘制环境
        if self.environment:
            self.draw_environment()
        
        # 绘制轨迹
        if self.show_trajectory:
            self.draw_trajectory()
        
        # 绘制机器狗
        if self.robot:
            self.draw_robot()
            
    def draw_axes(self):
        glDisable(GL_LIGHTING)
        glBegin(GL_LINES)
        # X轴 - 红色
        glColor3f(1.0, 0.0, 0.0)
        glVertex3f(0.0, 0.0, 0.0)
        glVertex3f(1.0, 0.0, 0.0)
        # Y轴 - 绿色
        glColor3f(0.0, 1.0, 0.0)
        glVertex3f(0.0, 0.0, 0.0)
        glVertex3f(0.0, 1.0, 0.0)
        # Z轴 - 蓝色
        glColor3f(0.0, 0.0, 1.0)
        glVertex3f(0.0, 0.0, 0.0)
        glVertex3f(0.0, 0.0, 1.0)
        glEnd()
        glEnable(GL_LIGHTING)
        
    def draw_grid(self):
        glDisable(GL_LIGHTING)
        glColor3f(0.5, 0.5, 0.5)
        glBegin(GL_LINES)
        size = 10
        for i in range(-size, size+1):
            glVertex3f(i, 0, -size)
            glVertex3f(i, 0, size)
            glVertex3f(-size, 0, i)
            glVertex3f(size, 0, i)
        glEnd()
        glEnable(GL_LIGHTING)
        
    def draw_environment(self):
        # 绘制地形
        if self.environment.terrain is not None:
            glColor3f(0.3, 0.6, 0.3)
            size = len(self.environment.terrain)
            for i in range(size-1):
                for j in range(size-1):
                    glBegin(GL_QUADS)
                    glVertex3f(i-size/2, self.environment.terrain[i][j], j-size/2)
                    glVertex3f(i+1-size/2, self.environment.terrain[i+1][j], j-size/2)
                    glVertex3f(i+1-size/2, self.environment.terrain[i+1][j+1], j+1-size/2)
                    glVertex3f(i-size/2, self.environment.terrain[i][j+1], j+1-size/2)
                    glEnd()
        
        # 绘制障碍物 - 使用基本几何体替代glut函数
        for obstacle in self.environment.obstacles:
            glPushMatrix()
            glTranslatef(obstacle['position'][0], obstacle['position'][1], obstacle['position'][2])
            glColor3f(0.8, 0.2, 0.2)
            
            if obstacle['type'] == 'cube':
                # 使用基本立方体绘制替代glutSolidCube
                self.draw_cube(obstacle['size'][0])
            elif obstacle['type'] == 'sphere':
                # 使用基本球体绘制替代glutSolidSphere
                self.draw_sphere(obstacle['size'][0])
                
            glPopMatrix()
        
        # 绘制目标点 - 使用基本球体绘制
        for target in self.environment.targets:
            glPushMatrix()
            glTranslatef(target[0], target[1], target[2])
            glColor3f(0.2, 0.8, 0.2)
            self.draw_sphere(0.1)
            glPopMatrix()
            
    def draw_trajectory(self):
        if len(self.trajectory_points) < 2:
            return
            
        glDisable(GL_LIGHTING)
        glColor3f(1.0, 1.0, 0.0)
        glBegin(GL_LINE_STRIP)
        for point in self.trajectory_points:
            glVertex3f(point[0], point[1], point[2])
        glEnd()
        glEnable(GL_LIGHTING)
        
    def draw_robot(self):
        if not self.robot:
            return
            
        # 保存当前矩阵
        glPushMatrix()
        
        # 应用机器狗的位置和旋转
        glTranslatef(self.robot.position[0], self.robot.position[1], self.robot.position[2])
        
        # 应用方向矩阵
        rotation_matrix = np.identity(4)
        rotation_matrix[:3, :3] = self.robot.orientation
        glMultMatrixf(rotation_matrix.T.flatten())
        
        # 绘制身体 - 使用自定义立方体
        glColor3f(0.2, 0.6, 0.8)
        glPushMatrix()
        glScalef(self.robot.body_length, self.robot.body_height, self.robot.body_width)
        self.draw_cube(1.0)  # 替换glutSolidCube(1.0)
        glPopMatrix()
        
        # 绘制四条腿
        leg_colors = [
            (0.8, 0.2, 0.2),  # 前左 - 红色
            (0.8, 0.8, 0.2),  # 前右 - 黄色
            (0.2, 0.8, 0.2),  # 后左 - 绿色
            (0.2, 0.8, 0.8)   # 后右 - 青色
        ]
        
        # 身体坐标系中的髋关节位置
        hip_positions = np.array([
            [-self.robot.body_length/2, 0, self.robot.body_width/2],   # 前左
            [-self.robot.body_length/2, 0, -self.robot.body_width/2],  # 前右
            [self.robot.body_length/2, 0, self.robot.body_width/2],    # 后左
            [self.robot.body_length/2, 0, -self.robot.body_width/2]    # 后右
        ])
        
        for i in range(4):
            self.draw_leg(hip_positions[i], self.robot.joint_angles[i], leg_colors[i])
            
        glPopMatrix()
        
        # 添加当前位置到轨迹
        self.trajectory_points.append(self.robot.position.copy())
        
    def draw_leg(self, hip_position, joint_angles, color):
        glPushMatrix()
        glTranslatef(hip_position[0], hip_position[1], hip_position[2])
        
        # 髋关节 - 使用自定义球体
        glColor3f(*color)
        self.draw_sphere(0.02, 10, 10)  # 替换glutSolidSphere
        
        # 髋关节旋转（绕Z轴）
        glRotatef(joint_angles[0] * 180/math.pi, 0, 0, 1)
        
        # 大腿
        glColor3f(color[0]*0.8, color[1]*0.8, color[2]*0.8)
        glPushMatrix()
        glTranslatef(0, -self.robot.upper_leg_length/2, 0)
        glScalef(0.02, self.robot.upper_leg_length, 0.02)
        self.draw_cube(1.0)  # 替换glutSolidCube
        glPopMatrix()
        
        # 移动到膝关节
        glTranslatef(0, -self.robot.upper_leg_length, 0)
        
        # 膝关节 - 使用自定义球体
        self.draw_sphere(0.02, 10, 10)  # 替换glutSolidSphere
        
        # 大腿旋转（绕X轴）
        glRotatef(joint_angles[1] * 180/math.pi, 1, 0, 0)
        
        # 小腿
        glColor3f(color[0]*0.6, color[1]*0.6, color[2]*0.6)
        glPushMatrix()
        glTranslatef(0, -self.robot.lower_leg_length/2, 0)
        glScalef(0.02, self.robot.lower_leg_length, 0.02)
        self.draw_cube(1.0)  # 替换glutSolidCube
        glPopMatrix()
        
        # 移动到脚
        glTranslatef(0, -self.robot.lower_leg_length, 0)
        
        # 脚 - 使用自定义球体
        glColor3f(0.5, 0.5, 0.5)
        self.draw_sphere(0.03, 10, 10)  # 替换glutSolidSphere
        
        glPopMatrix()
        
    def set_rotation(self, x, y, z):
        self.xRot = x
        self.yRot = y
        self.zRot = z
        self.update()
        
    def set_zoom(self, zoom):
        self.zoom = zoom
        self.update()
        
    def wheelEvent(self, event):
        self.zoom += event.angleDelta().y() * 0.01
        if self.zoom < 1:
            self.zoom = 1
        self.update()
        
    def mousePressEvent(self, event):
        self.lastPos = event.pos()
        
    def mouseMoveEvent(self, event):
        dx = event.x() - self.lastPos.x()
        dy = event.y() - self.lastPos.y()
        
        if event.buttons() & Qt.LeftButton:
            self.xRot += dy
            self.yRot += dx
        elif event.buttons() & Qt.RightButton:
            self.zRot += dx
            
        self.lastPos = event.pos()
        self.update()

    def draw_cube(self, size):
        """绘制立方体的替代函数"""
        s = size / 2.0
        glBegin(GL_QUADS)
        
        # 前面
        glVertex3f(-s, -s, s)
        glVertex3f(s, -s, s)
        glVertex3f(s, s, s)
        glVertex3f(-s, s, s)
        
        # 后面
        glVertex3f(-s, -s, -s)
        glVertex3f(-s, s, -s)
        glVertex3f(s, s, -s)
        glVertex3f(s, -s, -s)
        
        # 上面
        glVertex3f(-s, s, -s)
        glVertex3f(-s, s, s)
        glVertex3f(s, s, s)
        glVertex3f(s, s, -s)
        
        # 下面
        glVertex3f(-s, -s, -s)
        glVertex3f(s, -s, -s)
        glVertex3f(s, -s, s)
        glVertex3f(-s, -s, s)
        
        # 右面
        glVertex3f(s, -s, -s)
        glVertex3f(s, s, -s)
        glVertex3f(s, s, s)
        glVertex3f(s, -s, s)
        
        # 左面
        glVertex3f(-s, -s, -s)
        glVertex3f(-s, -s, s)
        glVertex3f(-s, s, s)
        glVertex3f(-s, s, -s)
        
        glEnd()
    
    def draw_sphere(self, radius, slices=16, stacks=16):
        """绘制球体的替代函数"""
        for i in range(stacks):
            lat0 = math.pi * (-0.5 + float(i) / stacks)
            z0 = math.sin(lat0) * radius
            zr0 = math.cos(lat0) * radius
            
            lat1 = math.pi * (-0.5 + float(i+1) / stacks)
            z1 = math.sin(lat1) * radius
            zr1 = math.cos(lat1) * radius
            
            glBegin(GL_QUAD_STRIP)
            for j in range(slices + 1):
                lng = 2 * math.pi * float(j) / slices
                x = math.cos(lng)
                y = math.sin(lng)
                
                glNormal3f(x * zr0, y * zr0, z0)
                glVertex3f(x * zr0, y * zr0, z0)
                glNormal3f(x * zr1, y * zr1, z1)
                glVertex3f(x * zr1, y * zr1, z1)
            glEnd()

# 数据分析图表组件
class DataPlotWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.data_logger = None
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 图表类型选择
        self.plot_selector = QComboBox()
        self.plot_selector.addItems([
            "位置轨迹", "速度曲线", "关节角度", "传感器数据", "能量消耗"
        ])
        layout.addWidget(self.plot_selector)
        
        # 图表画布
        self.figure = Figure(figsize=(5, 4), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)
        
        # 更新按钮
        self.update_btn = QPushButton("更新图表")
        self.update_btn.clicked.connect(self.update_plot)
        layout.addWidget(self.update_btn)
        
        self.setLayout(layout)
        
    def set_data_logger(self, data_logger):
        self.data_logger = data_logger
        
    def update_plot(self):
        if not self.data_logger or not self.data_logger.data['time']:
            return
            
        self.figure.clear()
        plot_type = self.plot_selector.currentText()
        
        if plot_type == "位置轨迹":
            self.plot_position_trajectory()
        elif plot_type == "速度曲线":
            self.plot_velocity()
        elif plot_type == "关节角度":
            self.plot_joint_angles()
        elif plot_type == "传感器数据":
            self.plot_sensor_data()
        elif plot_type == "能量消耗":
            self.plot_energy_consumption()
            
        self.canvas.draw()
        
    def plot_position_trajectory(self):
        ax = self.figure.add_subplot(111, projection='3d')
        positions = self.data_logger.data['position']
        x = [p[0] for p in positions]
        y = [p[1] for p in positions]
        z = [p[2] for p in positions]
        
        ax.plot(x, z, y)  # 注意：OpenGL中Y是高度，但在图表中我们通常用Z表示高度
        ax.set_xlabel('X')
        ax.set_ylabel('Z')
        ax.set_zlabel('Y')
        ax.set_title('位置轨迹')
        
    def plot_velocity(self):
        ax = self.figure.add_subplot(111)
        times = self.data_logger.data['time']
        velocities = self.data_logger.data['velocity']
        speed = [np.linalg.norm(v) for v in velocities]
        
        ax.plot(times, speed)
        ax.set_xlabel('时间 (s)')
        ax.set_ylabel('速度 (m/s)')
        ax.set_title('速度曲线')
        
    def plot_joint_angles(self):
        ax = self.figure.add_subplot(111)
        times = self.data_logger.data['time']
        joint_angles = self.data_logger.data['joint_angles']
        
        # 绘制第一条腿的关节角度
        if joint_angles:
            leg0_joints = joint_angles[0]  # 第一条腿
            for j in range(3):
                angles = [ja[0][j] * 180/math.pi for ja in joint_angles]  # 转换为度
                ax.plot(times, angles, label=f'关节 {j+1}')
                
        ax.set_xlabel('时间 (s)')
        ax.set_ylabel('角度 (度)')
        ax.set_title('关节角度')
        ax.legend()
        
    def plot_sensor_data(self):
        ax = self.figure.add_subplot(111)
        times = self.data_logger.data['time']
        sensor_data = self.data_logger.data['sensor_data']
        
        if sensor_data:
            accel_x = [sd['acceleration'][0] for sd in sensor_data]
            ax.plot(times, accel_x, label='加速度 X')
            
        ax.set_xlabel('时间 (s)')
        ax.set_ylabel('加速度 (m/s²)')
        ax.set_title('传感器数据')
        ax.legend()
        
    def plot_energy_consumption(self):
        # 简化的能量消耗计算
        ax = self.figure.add_subplot(111)
        times = self.data_logger.data['time']
        velocities = self.data_logger.data['velocity']
        
        # 计算动能
        kinetic_energy = [0.5 * 5.0 * np.linalg.norm(v)**2 for v in velocities]  # 质量假设为5kg
        
        ax.plot(times, kinetic_energy)
        ax.set_xlabel('时间 (s)')
        ax.set_ylabel('动能 (J)')
        ax.set_title('能量消耗')

# 高级控制面板
class AdvancedControlPanel(QWidget):
    def __init__(self, robot, ai_controller):
        super().__init__()
        self.robot = robot
        self.ai_controller = ai_controller
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 控制模式选择
        mode_group = QGroupBox("控制模式")
        mode_layout = QHBoxLayout()
        
        self.manual_btn = QPushButton("手动控制")
        self.auto_btn = QPushButton("自动导航")
        self.learning_btn = QPushButton("学习模式")
        
        self.manual_btn.setCheckable(True)
        self.auto_btn.setCheckable(True)
        self.learning_btn.setCheckable(True)
        
        self.manual_btn.setChecked(True)
        
        mode_layout.addWidget(self.manual_btn)
        mode_layout.addWidget(self.auto_btn)
        mode_layout.addWidget(self.learning_btn)
        
        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)
        
        # 步态控制
        gait_group = QGroupBox("步态控制")
        gait_layout = QVBoxLayout()
        
        self.gait_selector = QComboBox()
        self.gait_selector.addItems(["行走", "小跑", "奔跑", "跳跃"])
        gait_layout.addWidget(QLabel("步态类型:"))
        gait_layout.addWidget(self.gait_selector)
        
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setMinimum(1)
        self.speed_slider.setMaximum(10)
        self.speed_slider.setValue(5)
        gait_layout.addWidget(QLabel("速度:"))
        gait_layout.addWidget(self.speed_slider)
        
        self.step_height_slider = QSlider(Qt.Horizontal)
        self.step_height_slider.setMinimum(1)
        self.step_height_slider.setMaximum(20)
        self.step_height_slider.setValue(10)
        gait_layout.addWidget(QLabel("步高:"))
        gait_layout.addWidget(self.step_height_slider)
        
        gait_group.setLayout(gait_layout)
        layout.addWidget(gait_group)
        
        # 方向控制
        direction_group = QGroupBox("方向控制")
        direction_layout = QVBoxLayout()
        
        # 方向按钮
        button_layout = QVBoxLayout()
        
        up_layout = QHBoxLayout()
        self.forward_btn = QPushButton("前进")
        up_layout.addWidget(self.forward_btn)
        
        mid_layout = QHBoxLayout()
        self.left_btn = QPushButton("左转")
        self.stop_btn = QPushButton("停止")
        self.right_btn = QPushButton("右转")
        mid_layout.addWidget(self.left_btn)
        mid_layout.addWidget(self.stop_btn)
        mid_layout.addWidget(self.right_btn)
        
        down_layout = QHBoxLayout()
        self.backward_btn = QPushButton("后退")
        down_layout.addWidget(self.backward_btn)
        
        button_layout.addLayout(up_layout)
        button_layout.addLayout(mid_layout)
        button_layout.addLayout(down_layout)
        
        direction_layout.addLayout(button_layout)
        direction_group.setLayout(direction_layout)
        layout.addWidget(direction_group)
        
        # 自动导航设置
        nav_group = QGroupBox("自动导航")
        nav_layout = QVBoxLayout()
        
        self.target_x = QDoubleSpinBox()
        self.target_x.setRange(-10, 10)
        self.target_x.setValue(5)
        nav_layout.addWidget(QLabel("目标 X:"))
        nav_layout.addWidget(self.target_x)
        
        self.target_y = QDoubleSpinBox()
        self.target_y.setRange(-10, 10)
        self.target_y.setValue(0)
        nav_layout.addWidget(QLabel("目标 Y:"))
        nav_layout.addWidget(self.target_y)
        
        self.target_z = QDoubleSpinBox()
        self.target_z.setRange(-10, 10)
        self.target_z.setValue(0)
        nav_layout.addWidget(QLabel("目标 Z:"))
        nav_layout.addWidget(self.target_z)
        
        self.set_target_btn = QPushButton("设置目标点")
        nav_layout.addWidget(self.set_target_btn)
        
        nav_group.setLayout(nav_layout)
        layout.addWidget(nav_group)
        
        # 环境设置
        env_group = QGroupBox("环境设置")
        env_layout = QVBoxLayout()
        
        self.terrain_selector = QComboBox()
        self.terrain_selector.addItems(["平地", "丘陵", "阶梯"])
        env_layout.addWidget(QLabel("地形类型:"))
        env_layout.addWidget(self.terrain_selector)
        
        self.generate_terrain_btn = QPushButton("生成地形")
        env_layout.addWidget(self.generate_terrain_btn)
        
        env_group.setLayout(env_layout)
        layout.addWidget(env_group)
        
        self.setLayout(layout)
        
        # 连接信号
        self.connect_signals()
        
    def connect_signals(self):
        self.manual_btn.clicked.connect(self.set_manual_mode)
        self.auto_btn.clicked.connect(self.set_auto_mode)
        self.learning_btn.clicked.connect(self.set_learning_mode)
        
        self.forward_btn.clicked.connect(self.move_forward)
        self.backward_btn.clicked.connect(self.move_backward)
        self.left_btn.clicked.connect(self.turn_left)
        self.right_btn.clicked.connect(self.turn_right)
        self.stop_btn.clicked.connect(self.stop)
        
        self.speed_slider.valueChanged.connect(self.update_speed)
        self.step_height_slider.valueChanged.connect(self.update_step_height)
        self.gait_selector.currentTextChanged.connect(self.update_gait)
        
        self.set_target_btn.clicked.connect(self.set_navigation_target)
        self.generate_terrain_btn.clicked.connect(self.generate_terrain)
        
    def set_manual_mode(self):
        self.manual_btn.setChecked(True)
        self.auto_btn.setChecked(False)
        self.learning_btn.setChecked(False)
        self.ai_controller.mode = "manual"
        
    def set_auto_mode(self):
        self.manual_btn.setChecked(False)
        self.auto_btn.setChecked(True)
        self.learning_btn.setChecked(False)
        
    def set_learning_mode(self):
        self.manual_btn.setChecked(False)
        self.auto_btn.setChecked(False)
        self.learning_btn.setChecked(True)
        
    def move_forward(self):
        self.robot.target_velocity = np.array([0, 0, -0.5]) * (self.speed_slider.value() / 5)
        
    def move_backward(self):
        self.robot.target_velocity = np.array([0, 0, 0.5]) * (self.speed_slider.value() / 5)
        
    def turn_left(self):
        self.robot.angular_velocity[1] = 0.5
        
    def turn_right(self):
        self.robot.angular_velocity[1] = -0.5
        
    def stop(self):
        self.robot.target_velocity = np.zeros(3)
        self.robot.angular_velocity = np.zeros(3)
        
    def update_speed(self):
        self.robot.gait_frequency = 1.0 + (self.speed_slider.value() / 10) * 3
        
    def update_step_height(self):
        self.robot.step_height = 0.05 + (self.step_height_slider.value() / 20) * 0.15
        
    def update_gait(self, gait_name):
        gait_map = {
            "行走": "walk",
            "小跑": "trot", 
            "奔跑": "gallop",
            "跳跃": "pace"
        }
        self.robot.set_gait(gait_map.get(gait_name, "trot"))
        
    def set_navigation_target(self):
        target = np.array([self.target_x.value(), self.target_y.value(), self.target_z.value()])
        self.ai_controller.set_autonomous_mode(target)
        self.set_auto_mode()
        
    def generate_terrain(self):
        terrain_type = self.terrain_selector.currentText()
        # 这里需要与环境对象交互，实际实现中需要传递到主窗口

# 状态监控面板
class AdvancedStatusPanel(QWidget):
    def __init__(self, robot, physics_engine):
        super().__init__()
        self.robot = robot
        self.physics_engine = physics_engine
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 基本信息
        info_group = QGroupBox("基本信息")
        info_layout = QVBoxLayout()
        
        self.pos_x_label = QLabel("X: 0.00")
        self.pos_y_label = QLabel("Y: 0.00")
        self.pos_z_label = QLabel("Z: 0.00")
        
        info_layout.addWidget(self.pos_x_label)
        info_layout.addWidget(self.pos_y_label)
        info_layout.addWidget(self.pos_z_label)
        
        self.velocity_label = QLabel("速度: 0.00 m/s")
        info_layout.addWidget(self.velocity_label)
        
        self.orientation_label = QLabel("朝向: 0.00°")
        info_layout.addWidget(self.orientation_label)
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # 关节状态
        joint_group = QGroupBox("关节状态")
        joint_layout = QVBoxLayout()
        
        self.joint_table = QTableWidget()
        self.joint_table.setColumnCount(5)
        self.joint_table.setHorizontalHeaderLabels(["腿部", "髋关节", "大腿", "小腿", "状态"])
        self.joint_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        joint_layout.addWidget(self.joint_table)
        joint_group.setLayout(joint_layout)
        layout.addWidget(joint_group)
        
        # 传感器数据
        sensor_group = QGroupBox("传感器数据")
        sensor_layout = QVBoxLayout()
        
        self.accel_label = QLabel("加速度: [0.00, 0.00, 0.00] m/s²")
        self.gyro_label = QLabel("陀螺仪: [0.00, 0.00, 0.00] rad/s")
        self.orientation_sensor_label = QLabel("姿态: [0.00, 0.00, 0.00]°")
        
        sensor_layout.addWidget(self.accel_label)
        sensor_layout.addWidget(self.gyro_label)
        sensor_layout.addWidget(self.orientation_sensor_label)
        
        sensor_group.setLayout(sensor_layout)
        layout.addWidget(sensor_group)
        
        # 性能指标
        perf_group = QGroupBox("性能指标")
        perf_layout = QVBoxLayout()
        
        self.stability_label = QLabel("稳定性: 良好")
        self.power_label = QLabel("功耗: 0.00 W")
        self.distance_label = QLabel("行走距离: 0.00 m")
        
        perf_layout.addWidget(self.stability_label)
        perf_layout.addWidget(self.power_label)
        perf_layout.addWidget(self.distance_label)
        
        perf_group.setLayout(perf_layout)
        layout.addWidget(perf_group)
        
        self.setLayout(layout)
        
    def update_status(self):
        # 更新位置信息
        self.pos_x_label.setText(f"X: {self.robot.position[0]:.2f}")
        self.pos_y_label.setText(f"Y: {self.robot.position[1]:.2f}")
        self.pos_z_label.setText(f"Z: {self.robot.position[2]:.2f}")
        
        # 更新速度信息
        speed = np.linalg.norm(self.robot.velocity)
        self.velocity_label.setText(f"速度: {speed:.2f} m/s")
        
        # 更新朝向信息
        # 从方向矩阵提取欧拉角
        try:
            r = R.from_matrix(self.robot.orientation)
            euler = r.as_euler('xyz', degrees=True)
            self.orientation_label.setText(f"朝向: [{euler[0]:.2f}°, {euler[1]:.2f}°, {euler[2]:.2f}°]")
        except:
            self.orientation_label.setText("朝向: 计算中...")
        
        # 更新关节状态表
        self.update_joint_table()
        
        # 更新传感器数据
        self.accel_label.setText(
            f"加速度: [{self.robot.imu_data['acceleration'][0]:.2f}, "
            f"{self.robot.imu_data['acceleration'][1]:.2f}, "
            f"{self.robot.imu_data['acceleration'][2]:.2f}] m/s²"
        )
        self.gyro_label.setText(
            f"陀螺仪: [{self.robot.imu_data['gyro'][0]:.2f}, "
            f"{self.robot.imu_data['gyro'][1]:.2f}, "
            f"{self.robot.imu_data['gyro'][2]:.2f}] rad/s"
        )
        
        # 更新性能指标
        self.update_performance_metrics()
        
    def update_joint_table(self):
        leg_names = ["前左腿", "前右腿", "后左腿", "后右腿"]
        
        self.joint_table.setRowCount(4)
        for i in range(4):
            # 腿部名称
            self.joint_table.setItem(i, 0, QTableWidgetItem(leg_names[i]))
            
            # 关节角度
            for j in range(3):
                angle_deg = self.robot.joint_angles[i][j] * 180 / math.pi
                self.joint_table.setItem(i, j+1, QTableWidgetItem(f"{angle_deg:.1f}°"))
            
            # 关节状态
            foot_height = self.robot.foot_positions[i][1]
            status = "支撑" if foot_height < 0.05 else "摆动"
            self.joint_table.setItem(i, 4, QTableWidgetItem(status))
            
    def update_performance_metrics(self):
        # 简化的稳定性评估
        body_tilt = abs(self.robot.orientation[0, 0] - 1)  # 简化的倾斜度指标
        stability = "优秀" if body_tilt < 0.1 else "良好" if body_tilt < 0.3 else "一般"
        self.stability_label.setText(f"稳定性: {stability}")
        
        # 简化的功耗计算
        power = np.linalg.norm(self.robot.velocity) * 10  # 简化模型
        self.power_label.setText(f"功耗: {power:.2f} W")
        
        # 行走距离（需要历史数据，这里简化）
        self.distance_label.setText("行走距离: 计算中...")

# 模拟线程
class AdvancedSimulationThread(QThread):
    update_signal = pyqtSignal()
    
    def __init__(self, physics_engine, robot, ai_controller, data_logger):
        super().__init__()
        self.physics_engine = physics_engine
        self.robot = robot
        self.ai_controller = ai_controller
        self.data_logger = data_logger
        self.running = True
        self.sim_speed = 1.0  # 模拟速度倍率
        
    def run(self):
        last_time = time.time()
        accumulated_time = 0.0
        
        while self.running:
            current_time = time.time()
            delta_time = (current_time - last_time) * self.sim_speed
            last_time = current_time
            accumulated_time += delta_time
            
            # 固定时间步长更新
            while accumulated_time >= self.physics_engine.time_step:
                # AI控制更新
                self.ai_controller.update(self.physics_engine.time_step)
                
                # 机器人步态更新
                self.robot.update_gait(self.physics_engine.time_step)
                
                # 应用控制
                self.robot.apply_control(self.physics_engine.time_step)
                
                # 物理模拟
                self.physics_engine.update()
                
                # 更新传感器
                self.robot.update_sensors()
                
                # 记录数据
                control_inputs = {
                    'target_velocity': self.robot.target_velocity.tolist(),
                    'gait_type': self.robot.gait_type
                }
                self.data_logger.log(self.robot, control_inputs)
                
                accumulated_time -= self.physics_engine.time_step
                
            # 发送更新信号（限制频率，避免UI过载）
            self.update_signal.emit()
            self.msleep(10)  # 约100Hz
            
    def stop(self):
        self.running = False
        
    def set_simulation_speed(self, speed):
        self.sim_speed = speed

# 主窗口
class AdvancedRobotSimulator(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = QSettings("RobotSimulator", "AdvancedDogSim")
        self.init_ui()
        self.load_settings()
        
    def init_ui(self):
        self.setWindowTitle("高级机器狗运动模拟系统")
        self.setGeometry(100, 50, 1600, 1000)
        
        # 创建中心部件和主布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # 创建左侧3D视图
        self.gl_widget = AdvancedGLWidget()
        main_layout.addWidget(self.gl_widget, 2)  # 2/5的空间
        
        # 创建右侧面板（使用分割器）
        right_splitter = QSplitter(Qt.Vertical)
        main_layout.addWidget(right_splitter, 1)  # 1/5的空间
        
        # 创建机器狗和物理引擎
        self.robot = AdvancedRobotDog()
        self.physics_engine = AdvancedPhysicsEngine()
        self.physics_engine.add_robot(self.robot)
        
        # 创建AI控制器
        self.ai_controller = AIController(self.robot)
        
        # 创建环境
        self.environment = Environment()
        self.environment.generate_terrain("flat")
        self.physics_engine.set_terrain(self.environment)
        
        # 创建数据记录器
        self.data_logger = DataLogger()
        
        # 设置3D视图的机器狗和环境
        self.gl_widget.robot = self.robot
        self.gl_widget.environment = self.environment
        
        # 创建控制面板
        self.control_panel = AdvancedControlPanel(self.robot, self.ai_controller)
        right_splitter.addWidget(self.control_panel)
        
        # 创建状态监控面板
        self.status_panel = AdvancedStatusPanel(self.robot, self.physics_engine)
        right_splitter.addWidget(self.status_panel)
        
        # 创建数据分析面板
        self.data_plot = DataPlotWidget()
        self.data_plot.set_data_logger(self.data_logger)
        right_splitter.addWidget(self.data_plot)
        
        # 设置分割器比例
        right_splitter.setSizes([300, 300, 400])
        
        # 创建菜单栏
        self.create_menu()
        
        # 创建工具栏
        self.create_toolbar()
        
        # 创建状态栏
        self.status_label = QLabel("就绪")
        self.statusBar().addWidget(self.status_label)
        
        # 创建模拟线程
        self.sim_thread = AdvancedSimulationThread(
            self.physics_engine, self.robot, self.ai_controller, self.data_logger
        )
        self.sim_thread.update_signal.connect(self.update_display)
        self.sim_thread.start()
        
        # 创建更新定时器（用于UI更新，频率低于模拟线程）
        self.ui_timer = QTimer()
        self.ui_timer.timeout.connect(self.update_ui)
        self.ui_timer.start(100)  # 10Hz
        
        # 初始化状态
        self.update_display()
        
    def create_menu(self):
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu('文件')
        
        new_action = file_menu.addAction('新建模拟')
        load_action = file_menu.addAction('加载数据')
        save_action = file_menu.addAction('保存数据')
        file_menu.addSeparator()
        exit_action = file_menu.addAction('退出')
        
        # 模拟菜单
        sim_menu = menubar.addMenu('模拟')
        
        start_action = sim_menu.addAction('开始模拟')
        pause_action = sim_menu.addAction('暂停模拟')
        reset_action = sim_menu.addAction('重置模拟')
        sim_menu.addSeparator()
        speed_menu = sim_menu.addMenu('模拟速度')
        
        # 视图菜单
        view_menu = menubar.addMenu('视图')
        
        trajectory_action = view_menu.addAction('显示轨迹')
        trajectory_action.setCheckable(True)
        trajectory_action.setChecked(True)
        grid_action = view_menu.addAction('显示网格')
        grid_action.setCheckable(True)
        grid_action.setChecked(True)
        
        # 连接菜单信号
        exit_action.triggered.connect(self.close)
        trajectory_action.triggered.connect(self.toggle_trajectory)
        grid_action.triggered.connect(self.toggle_grid)
        
    def create_toolbar(self):
        toolbar = self.addToolBar('主工具栏')
        
        # 添加工具按钮
        start_btn = QPushButton('开始')
        pause_btn = QPushButton('暂停')
        reset_btn = QPushButton('重置')
        
        toolbar.addWidget(start_btn)
        toolbar.addWidget(pause_btn)
        toolbar.addWidget(reset_btn)
        
        # 模拟速度控制
        toolbar.addSeparator()
        speed_label = QLabel('模拟速度:')
        toolbar.addWidget(speed_label)
        
        speed_slider = QSlider(Qt.Horizontal)
        speed_slider.setMinimum(1)
        speed_slider.setMaximum(10)
        speed_slider.setValue(5)
        speed_slider.setFixedWidth(100)
        toolbar.addWidget(speed_slider)
        
        # 连接信号
        speed_slider.valueChanged.connect(self.set_simulation_speed)
        
    def toggle_trajectory(self, checked):
        self.gl_widget.show_trajectory = checked
        
    def toggle_grid(self, checked):
        self.gl_widget.show_grid = checked
        
    def set_simulation_speed(self, speed):
        # 将滑块值转换为模拟速度（0.1x 到 2x）
        sim_speed = 0.1 + (speed - 1) * 0.2
        self.sim_thread.set_simulation_speed(sim_speed)
        self.status_label.setText(f"模拟速度: {sim_speed:.1f}x")
        
    def update_display(self):
        self.gl_widget.update()
        
    def update_ui(self):
        self.status_panel.update_status()
        # 更新其他UI元素...
        
    def closeEvent(self, event):
        # 停止模拟线程
        self.sim_thread.stop()
        self.sim_thread.wait()
        
        # 保存设置
        self.save_settings()
        
        event.accept()
        
    def save_settings(self):
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("windowState", self.saveState())
        
    def load_settings(self):
        if self.settings.contains("geometry"):
            self.restoreGeometry(self.settings.value("geometry"))
        if self.settings.contains("windowState"):
            self.restoreState(self.settings.value("windowState"))

# 主函数
if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # 设置应用程序样式
    app.setStyle('Fusion')
    
    # 设置应用程序图标和元数据
    app.setApplicationName("高级机器狗运动模拟系统")
    app.setApplicationVersion("1.0")
    app.setOrganizationName("机器人实验室")
    
    # 创建并显示主窗口
    simulator = AdvancedRobotSimulator()
    simulator.show()
    
    # 运行应用程序
    sys.exit(app.exec_())