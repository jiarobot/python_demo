import numpy as np
import math
import time
import threading
from scipy.spatial.transform import Rotation as R
from scipy.integrate import solve_ivp
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict, Callable
import json
import pickle
from enum import Enum
import logging
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                             QWidget, QPushButton, QSlider, QLabel, QGroupBox,
                             QTabWidget, QTextEdit, QDoubleSpinBox, QSpinBox,
                             QComboBox, QCheckBox, QProgressBar, QTableWidget,
                             QTableWidgetItem, QSplitter, QTreeWidget, QTreeWidgetItem,
                             QMessageBox, QFileDialog, QDial, QLCDNumber)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread, pyqtSlot
from PyQt5.QtGui import QColor, QFont, QPalette
import pyqtgraph.opengl as gl
import pyqtgraph as pg
import sys
import numpy as np
import math
from scipy.spatial.transform import Rotation as R
from dataclasses import dataclass
from typing import List, Tuple, Optional
import json

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SmartRobotArm")

@dataclass
class DHParameters:
    """DH参数数据结构"""
    a: float      # 连杆长度
    alpha: float  # 连杆扭角
    d: float      # 连杆偏移
    theta: float  # 关节角度

class Joint:
    """增强关节类"""
    def __init__(self, name: str, joint_type: str, limits: Tuple[float, float],
                 max_velocity: float, max_torque: float, gear_ratio: float = 1.0):
        self.name = name
        self.type = joint_type  # 'revolute' or 'prismatic'
        self.limits = limits
        self.max_velocity = max_velocity
        self.max_torque = max_torque
        self.gear_ratio = gear_ratio
        self.value = 0.0  # 确保这是浮点数
        self.velocity = 0.0
        self.torque = 0.0
        self.friction = 0.01  # 摩擦系数

class Link:
    """连杆类"""
    def __init__(self, name: str, dh_params: DHParameters, mass: float = 0.0):
        self.name = name
        self.dh_params = dh_params
        self.mass = mass
        self.length = math.sqrt(dh_params.a**2 + dh_params.d**2)

class RobotArm:
    """智能连杆机械臂主类"""
    
    def __init__(self, name: str):
        self.name = name
        self.links: List[Link] = []
        self.joints: List[Joint] = []
        self.base_position = np.array([0, 0, 0])
        
    def add_link(self, link: Link, joint: Joint):
        """添加连杆和关节"""
        self.links.append(link)
        self.joints.append(joint)
    
    def dh_matrix(self, a, alpha, d, theta):
        """计算DH变换矩阵"""
        cos_theta = math.cos(theta)
        sin_theta = math.sin(theta)
        cos_alpha = math.cos(alpha)
        sin_alpha = math.sin(alpha)
        
        return np.array([
            [cos_theta, -sin_theta*cos_alpha, sin_theta*sin_alpha, a*cos_theta],
            [sin_theta, cos_theta*cos_alpha, -cos_theta*sin_alpha, a*sin_theta],
            [0, sin_alpha, cos_alpha, d],
            [0, 0, 0, 1]
        ])
    
    def forward_kinematics(self, joint_angles: List[float]) -> np.ndarray:
        """正运动学求解"""
        if len(joint_angles) != len(self.joints):
            raise ValueError("关节角度数量不匹配")
        
        # 设置关节角度
        for i, angle in enumerate(joint_angles):
            self.joints[i].value = angle
            self.links[i].dh_params.theta = angle
        
        # 计算变换矩阵
        T = np.eye(4)
        T[0:3, 3] = self.base_position
        
        positions = [self.base_position]
        
        for i, link in enumerate(self.links):
            dh = link.dh_params
            T_i = self.dh_matrix(dh.a, dh.alpha, dh.d, dh.theta)
            T = T @ T_i
            
            # 提取位置
            position = T[0:3, 3]
            positions.append(position)
        
        return np.array(positions)
    
    def jacobian(self, joint_angles: List[float]) -> np.ndarray:
        """计算雅可比矩阵"""
        positions = self.forward_kinematics(joint_angles)
        end_effector_pos = positions[-1]
        
        jacobian = np.zeros((6, len(joint_angles)))
        
        for i in range(len(joint_angles)):
            if self.joints[i].type == 'revolute':
                # 旋转关节
                axis = np.array([0, 0, 1])  # 默认Z轴
                joint_pos = positions[i]
                jacobian[0:3, i] = np.cross(axis, end_effector_pos - joint_pos)
                jacobian[3:6, i] = axis
            else:
                # 移动关节
                jacobian[0:3, i] = np.array([0, 0, 1])  # 默认Z轴方向
        
        return jacobian
    
    def inverse_kinematics(self, target_position: np.ndarray, 
                        initial_angles: Optional[List[float]] = None,
                        max_iterations: int = 1000,
                        tolerance: float = 1e-6) -> List[float]:
        """逆运动学求解（数值方法）"""
        if initial_angles is None:
            initial_angles = [0.0] * len(self.joints)  # 使用浮点数
        
        # 确保 current_angles 是浮点数数组
        current_angles = np.array(initial_angles, dtype=np.float64)
        
        for iteration in range(max_iterations):
            # 计算当前末端位置
            current_positions = self.forward_kinematics(current_angles)
            current_end_pos = current_positions[-1]
            
            # 计算误差
            error = target_position - current_end_pos
            if np.linalg.norm(error) < tolerance:
                break
            
            # 计算雅可比矩阵
            J = self.jacobian(current_angles)
            
            # 使用伪逆求解
            J_pseudo = np.linalg.pinv(J)
            delta_angles = J_pseudo @ np.concatenate([error, [0, 0, 0]])
            
            # 更新角度
            current_angles += delta_angles[:len(self.joints)]
            
            # 应用关节限制
            for i in range(len(current_angles)):
                low, high = self.joints[i].limits
                current_angles[i] = np.clip(current_angles[i], low, high)
        
        return current_angles.tolist()

class Robot3DViewer(gl.GLViewWidget):
    """3D机械臂可视化组件"""
    
    joint_moved = pyqtSignal(list)  # 关节角度变化信号
    
    def __init__(self, robot_arm: RobotArm):
        super().__init__()
        self.robot_arm = robot_arm
        self.joint_angles = [0] * len(robot_arm.joints)
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle('智能连杆机械臂3D可视化')
        self.setCameraPosition(distance=5, elevation=30, azimuth=45)
        
        # 创建坐标系
        self.add_coordinate_system()
        
        # 初始绘制
        self.update_display()
    
    def add_coordinate_system(self):
        """添加坐标系"""
        # X轴 - 红色
        x_axis = gl.GLLinePlotItem(pos=np.array([[0,0,0], [1,0,0]]), 
                                 color=(1,0,0,1), width=3)
        self.addItem(x_axis)
        
        # Y轴 - 绿色
        y_axis = gl.GLLinePlotItem(pos=np.array([[0,0,0], [0,1,0]]), 
                                 color=(0,1,0,1), width=3)
        self.addItem(y_axis)
        
        # Z轴 - 蓝色
        z_axis = gl.GLLinePlotItem(pos=np.array([[0,0,0], [0,0,1]]), 
                                 color=(0,0,1,1), width=3)
        self.addItem(z_axis)
    
    def update_joints(self, angles: List[float]):
        """更新关节角度"""
        self.joint_angles = angles
        self.update_display()
        self.joint_moved.emit(angles)
    
    def update_display(self):
        """更新显示"""
        self.clear()
        self.add_coordinate_system()
        
        # 计算正运动学
        positions = self.robot_arm.forward_kinematics(self.joint_angles)
        
        # 绘制连杆
        for i in range(1, len(positions)):
            # 连杆线条
            link_line = gl.GLLinePlotItem(
                pos=np.array([positions[i-1], positions[i]]),
                color=(1, 1, 0, 1),  # 黄色
                width=5
            )
            self.addItem(link_line)
            
            # 关节球体
            joint_sphere = gl.MeshData.sphere(rows=10, cols=10, radius=0.05)
            joint_mesh = gl.GLMeshItem(
                meshdata=joint_sphere,
                color=(0, 1, 1, 1),  # 青色
                smooth=True,
                shader='shaded'
            )
            joint_mesh.translate(positions[i-1][0], positions[i-1][1], positions[i-1][2])
            self.addItem(joint_mesh)
        
        # 绘制末端执行器
        end_effector_sphere = gl.MeshData.sphere(rows=10, cols=10, radius=0.08)
        end_effector = gl.GLMeshItem(
            meshdata=end_effector_sphere,
            color=(1, 0, 1, 1),  # 洋红色
            smooth=True,
            shader='shaded'
        )
        end_effector.translate(positions[-1][0], positions[-1][1], positions[-1][2])
        self.addItem(end_effector)

class ControlMode(Enum):
    POSITION_CONTROL = 1
    VELOCITY_CONTROL = 2
    FORCE_CONTROL = 3
    IMPEDANCE_CONTROL = 4
    ADMITTANCE_CONTROL = 5

class TrajectoryType(Enum):
    LINEAR = 1
    CIRCULAR = 2
    POLYNOMIAL = 3
    SPLINE = 4
    MINIMUM_JERK = 5
    ADAPTIVE = 6

@dataclass
class DHParameters:
    """DH参数数据结构"""
    a: float      # 连杆长度
    alpha: float  # 连杆扭角
    d: float      # 连杆偏移
    theta: float  # 关节角度

@dataclass
class InertiaTensor:
    """惯性张量"""
    Ixx: float
    Iyy: float
    Izz: float
    Ixy: float = 0
    Ixz: float = 0
    Iyz: float = 0

class Joint:
    """增强关节类"""
    def __init__(self, name: str, joint_type: str, limits: Tuple[float, float],
                 max_velocity: float, max_torque: float, gear_ratio: float = 1.0):
        self.name = name
        self.type = joint_type  # 'revolute' or 'prismatic'
        self.limits = limits
        self.max_velocity = max_velocity
        self.max_torque = max_torque
        self.gear_ratio = gear_ratio
        self.value = 0.0
        self.velocity = 0.0
        self.torque = 0.0
        self.friction = 0.01  # 摩擦系数

class Link:
    """增强连杆类"""
    def __init__(self, name: str, dh_params: DHParameters, mass: float,
                 com: np.ndarray, inertia: InertiaTensor, color: str = "blue"):
        self.name = name
        self.dh_params = dh_params
        self.mass = mass
        self.com = com  # 质心位置
        self.inertia = inertia
        self.color = color
        self.length = math.sqrt(dh_params.a**2 + dh_params.d**2)

class SmartRobotArm(RobotArm):
    """增强版智能机械臂"""
    
    def __init__(self, name: str, control_frequency: float = 100.0):
        super().__init__(name)
        self.control_frequency = control_frequency
        self.control_mode = ControlMode.POSITION_CONTROL
        self.is_running = False
        self.control_thread = None
        self.sensors = {}
        self.controllers = {}
        self.trajectory_generator = AdvancedTrajectoryGenerator()
        self.force_controller = ForceController()
        self.impedance_controller = ImpedanceController()
        self.machine_learning_model = MachineLearningModel()
        self.vision_system = VisionSystem()
        self.data_logger = DataLogger()
        
        # PID控制器参数
        self.pid_controllers = []
        
        # 实时数据
        self.current_position = np.zeros(3)
        self.current_velocity = np.zeros(3)
        self.current_force = np.zeros(3)
        self.target_position = np.zeros(3)
        self.target_velocity = np.zeros(3)
        
        # 动力学参数
        self.gravity = np.array([0, 0, -9.81])
        
    def start_control_loop(self):
        """启动控制循环"""
        if self.is_running:
            return
            
        self.is_running = True
        self.control_thread = threading.Thread(target=self._control_loop)
        self.control_thread.daemon = True
        self.control_thread.start()
        logger.info("控制循环已启动")
    
    def stop_control_loop(self):
        """停止控制循环"""
        self.is_running = False
        if self.control_thread:
            self.control_thread.join()
        logger.info("控制循环已停止")
    
    def _control_loop(self):
        """控制循环主函数"""
        dt = 1.0 / self.control_frequency
        
        while self.is_running:
            start_time = time.time()
            
            # 读取传感器数据
            self._read_sensors()
            
            # 根据控制模式执行控制
            if self.control_mode == ControlMode.POSITION_CONTROL:
                self._position_control()
            elif self.control_mode == ControlMode.VELOCITY_CONTROL:
                self._velocity_control()
            elif self.control_mode == ControlMode.FORCE_CONTROL:
                self._force_control()
            elif self.control_mode == ControlMode.IMPEDANCE_CONTROL:
                self._impedance_control()
            elif self.control_mode == ControlMode.ADMITTANCE_CONTROL:
                self._admittance_control()
            
            # 记录数据
            self.data_logger.log({
                'timestamp': time.time(),
                'position': self.current_position.copy(),
                'velocity': self.current_velocity.copy(),
                'force': self.current_force.copy(),
                'target_position': self.target_position.copy(),
                'joint_angles': [j.value for j in self.joints]
            })
            
            # 保持恒定频率
            elapsed = time.time() - start_time
            sleep_time = max(0, dt - elapsed)
            time.sleep(sleep_time)
    
    def _read_sensors(self):
        """读取传感器数据（模拟）"""
        # 模拟读取位置、速度和力传感器
        positions = self.forward_kinematics([j.value for j in self.joints])
        self.current_position = positions[-1]
        
        # 计算速度（数值微分）
        if hasattr(self, '_last_position'):
            dt = 1.0 / self.control_frequency
            self.current_velocity = (self.current_position - self._last_position) / dt
        self._last_position = self.current_position.copy()
        
        # 模拟力传感器读数
        self.current_force = np.random.normal(0, 0.1, 3)  # 模拟噪声
    
    def _position_control(self):
        """位置控制"""
        # 计算逆运动学得到目标关节角度
        # 确保传递浮点数列表
        current_angles = [float(joint.value) for joint in self.joints]
        target_angles = self.inverse_kinematics(self.target_position, current_angles)
        
        # 应用PID控制
        for i, (joint, target_angle) in enumerate(zip(self.joints, target_angles)):
            error = target_angle - joint.value
            # 简化的PID控制（实际中需要更复杂的实现）
            control_signal = self._pid_control(i, error)
            # 应用控制信号（这里简化为直接设置关节角度）
            joint.value += control_signal * (1.0 / self.control_frequency)
    
    def _pid_control(self, joint_index, error):
        """PID控制"""
        # 简化的PID实现
        kp, ki, kd = 1.0, 0.01, 0.1  # PID参数
        
        if joint_index >= len(self.pid_controllers):
            # 初始化PID控制器
            self.pid_controllers.append({'integral': 0, 'last_error': 0})
        
        pid = self.pid_controllers[joint_index]
        pid['integral'] += error
        derivative = error - pid['last_error']
        pid['last_error'] = error
        
        return kp * error + ki * pid['integral'] + kd * derivative
    
    def _velocity_control(self):
        """速度控制"""
        # 简化的速度控制实现
        jacobian = self.jacobian([j.value for j in self.joints])
        target_joint_velocities = np.linalg.pinv(jacobian[:3, :]) @ self.target_velocity
        
        for i, (joint, target_vel) in enumerate(zip(self.joints, target_joint_velocities)):
            # 限制速度
            target_vel = np.clip(target_vel, -joint.max_velocity, joint.max_velocity)
            # 更新关节角度
            joint.value += target_vel * (1.0 / self.control_frequency)
    
    def _force_control(self):
        """力控制"""
        self.force_controller.update(self.current_force, self.target_position)
        control_signal = self.force_controller.get_control_signal()
        # 应用力控制信号（简化实现）
        # 实际中需要更复杂的力-位置/速度转换
    
    def _impedance_control(self):
        """阻抗控制"""
        self.impedance_controller.update(
            self.current_position, 
            self.target_position,
            self.current_force
        )
        # 应用阻抗控制
    
    def _admittance_control(self):
        """导纳控制"""
        # 导纳控制实现
        pass
    
    def compute_dynamics(self, joint_angles: List[float], 
                        joint_velocities: List[float],
                        joint_torques: List[float]) -> List[float]:
        """计算动力学（牛顿-欧拉法）"""
        n = len(self.joints)
        
        # 初始化变量
        w = [np.zeros(3) for _ in range(n+1)]  # 角速度
        w_dot = [np.zeros(3) for _ in range(n+1)]  # 角加速度
        v_dot = [np.zeros(3) for _ in range(n+1)]  # 线加速度
        v_dot[0] = -self.gravity  # 基座加速度（重力）
        
        f = [np.zeros(3) for _ in range(n+1)]  # 连杆受力
        n_force = [np.zeros(3) for _ in range(n+1)]  # 连杆受扭矩
        
        # 前向传递（从基座到末端）
        for i in range(n):
            # 计算变换矩阵
            dh = self.links[i].dh_params
            T = self.dh_matrix(dh.a, dh.alpha, dh.d, joint_angles[i])
            R_mat = T[0:3, 0:3]  # 旋转矩阵
            p = T[0:3, 3]  # 位置向量
            
            # 计算角速度和角加速度
            if self.joints[i].type == 'revolute':
                z = np.array([0, 0, 1])  # 关节轴
                w[i+1] = R_mat.T @ w[i] + joint_velocities[i] * z
                w_dot[i+1] = R_mat.T @ w_dot[i] + R_mat.T @ w[i] * joint_velocities[i] * z + joint_torques[i] * z
            else:
                w[i+1] = R_mat.T @ w[i]
                w_dot[i+1] = R_mat.T @ w_dot[i]
            
            # 计算线加速度
            v_dot[i+1] = R_mat.T @ (v_dot[i] + np.cross(w_dot[i], p) + 
                                   np.cross(w[i], np.cross(w[i], p)))
            
            # 如果关节是移动关节，添加线性加速度
            if self.joints[i].type == 'prismatic':
                z = np.array([0, 0, 1])
                v_dot[i+1] += joint_torques[i] * z + 2 * joint_velocities[i] * np.cross(w[i+1], z)
        
        # 反向传递（从末端到基座）
        joint_torques_out = [0.0] * n
        
        for i in range(n-1, -1, -1):
            # 计算变换矩阵
            dh = self.links[i].dh_params
            T = self.dh_matrix(dh.a, dh.alpha, dh.d, joint_angles[i])
            R_mat = T[0:3, 0:3]
            p = T[0:3, 3]
            
            # 计算连杆质心加速度
            com = self.links[i].com
            v_dot_com = v_dot[i+1] + np.cross(w_dot[i+1], com) + \
                       np.cross(w[i+1], np.cross(w[i+1], com))
            
            # 计算力和扭矩
            f[i] = R_mat @ f[i+1] + self.links[i].mass * v_dot_com
            n_force[i] = R_mat @ n_force[i+1] + np.cross(com, f[i]) + \
                        np.cross(p + com, R_mat @ f[i+1]) + \
                        self._inertia_tensor_to_matrix(self.links[i].inertia) @ w_dot[i+1] + \
                        np.cross(w[i+1], self._inertia_tensor_to_matrix(self.links[i].inertia) @ w[i+1])
            
            # 计算关节扭矩
            if self.joints[i].type == 'revolute':
                z = np.array([0, 0, 1])
                joint_torques_out[i] = n_force[i] @ z
            else:
                z = np.array([0, 0, 1])
                joint_torques_out[i] = f[i] @ z
        
        return joint_torques_out
    
    def _inertia_tensor_to_matrix(self, inertia: InertiaTensor) -> np.ndarray:
        """将惯性张量转换为矩阵形式"""
        return np.array([
            [inertia.Ixx, inertia.Ixy, inertia.Ixz],
            [inertia.Ixy, inertia.Iyy, inertia.Iyz],
            [inertia.Ixz, inertia.Iyz, inertia.Izz]
        ])
    
    def add_sensor(self, name: str, sensor_type: str, callback: Callable):
        """添加传感器"""
        self.sensors[name] = {
            'type': sensor_type,
            'callback': callback,
            'data': None
        }
    
    def add_controller(self, name: str, controller):
        """添加控制器"""
        self.controllers[name] = controller
    
    def set_trajectory(self, trajectory_type: TrajectoryType, **kwargs):
        """设置轨迹"""
        self.trajectory_generator.set_trajectory(trajectory_type, **kwargs)
    
    def execute_trajectory(self, duration: float):
        """执行轨迹"""
        self.trajectory_generator.execute(self, duration)

class AdvancedTrajectoryGenerator:
    """高级轨迹生成器"""
    
    def __init__(self):
        self.trajectory_type = TrajectoryType.LINEAR
        self.trajectory_params = {}
        self.current_trajectory = None
        self.start_time = None
        self.is_running = False
    
    def set_trajectory(self, trajectory_type: TrajectoryType, **kwargs):
        """设置轨迹类型和参数"""
        self.trajectory_type = trajectory_type
        self.trajectory_params = kwargs
    
    def execute(self, robot_arm: SmartRobotArm, duration: float):
        """执行轨迹"""
        self.start_time = time.time()
        self.is_running = True
        self.robot_arm = robot_arm
        
        # 根据轨迹类型生成轨迹
        if self.trajectory_type == TrajectoryType.LINEAR:
            self._linear_trajectory(duration)
        elif self.trajectory_type == TrajectoryType.SPLINE:
            self._spline_trajectory(duration)
        elif self.trajectory_type == TrajectoryType.MINIMUM_JERK:
            self._minimum_jerk_trajectory(duration)
        elif self.trajectory_type == TrajectoryType.ADAPTIVE:
            self._adaptive_trajectory(duration)
    
    def _linear_trajectory(self, duration: float):
        """线性轨迹"""
        start_pos = self.robot_arm.current_position
        end_pos = self.trajectory_params.get('end_position', start_pos)
        
        def trajectory_func(t):
            t_normalized = t / duration
            return start_pos + t_normalized * (end_pos - start_pos)
        
        self._follow_trajectory(trajectory_func, duration)
    
    def _spline_trajectory(self, duration: float):
        """样条轨迹"""
        waypoints = self.trajectory_params.get('waypoints', [])
        if len(waypoints) < 2:
            logger.error("样条轨迹需要至少两个路径点")
            return
        
        # 简化样条实现（实际中应使用更复杂的样条算法）
        segments = len(waypoints) - 1
        segment_duration = duration / segments
        
        def trajectory_func(t):
            segment_index = min(int(t / segment_duration), segments - 1)
            t_segment = (t - segment_index * segment_duration) / segment_duration
            
            if segment_index < segments - 1:
                # 线性插值
                return waypoints[segment_index] + t_segment * (waypoints[segment_index+1] - waypoints[segment_index])
            else:
                return waypoints[-1]
        
        self._follow_trajectory(trajectory_func, duration)
    
    def _minimum_jerk_trajectory(self, duration: float):
        """最小加加速度轨迹"""
        start_pos = self.robot_arm.current_position
        end_pos = self.trajectory_params.get('end_position', start_pos)
        
        def trajectory_func(t):
            t_normalized = t / duration
            # 最小加加速度轨迹的五次多项式
            t2 = t_normalized * t_normalized
            t3 = t2 * t_normalized
            t4 = t3 * t_normalized
            t5 = t4 * t_normalized
            
            scale = 10*t3 - 15*t4 + 6*t5
            return start_pos + scale * (end_pos - start_pos)
        
        self._follow_trajectory(trajectory_func, duration)
    
    def _adaptive_trajectory(self, duration: float):
        """自适应轨迹（根据环境调整）"""
        # 简化实现
        self._minimum_jerk_trajectory(duration)
    
    def _follow_trajectory(self, trajectory_func: Callable, duration: float):
        """跟随轨迹"""
        start_time = time.time()
        
        while time.time() - start_time < duration and self.is_running:
            t = time.time() - start_time
            target_pos = trajectory_func(t)
            self.robot_arm.target_position = target_pos
            time.sleep(0.01)  # 10ms控制周期
        
        self.is_running = False

class ForceController:
    """力控制器"""
    
    def __init__(self):
        self.kp = 1.0  # 比例增益
        self.ki = 0.1  # 积分增益
        self.kd = 0.01  # 微分增益
        self.integral = np.zeros(3)
        self.last_error = np.zeros(3)
        self.target_force = np.zeros(3)
    
    def update(self, current_force: np.ndarray, current_position: np.ndarray):
        """更新力控制器"""
        error = self.target_force - current_force
        self.integral += error
        derivative = error - self.last_error
        self.last_error = error
        
        # PID控制
        control_signal = self.kp * error + self.ki * self.integral + self.kd * derivative
        return control_signal
    
    def set_target_force(self, target_force: np.ndarray):
        """设置目标力"""
        self.target_force = target_force

class ImpedanceController:
    """阻抗控制器"""
    
    def __init__(self):
        self.M = np.eye(3)  # 惯性矩阵
        self.B = np.eye(3) * 10  # 阻尼矩阵
        self.K = np.eye(3) * 100  # 刚度矩阵
        self.position_error = np.zeros(3)
        self.velocity_error = np.zeros(3)
    
    def update(self, current_position: np.ndarray, 
               target_position: np.ndarray, 
               external_force: np.ndarray):
        """更新阻抗控制器"""
        self.position_error = target_position - current_position
        # 简化的阻抗控制方程
        target_acceleration = (external_force - self.B @ self.velocity_error - 
                              self.K @ self.position_error) / np.diag(self.M)
        return target_acceleration

class MachineLearningModel:
    """机器学习模型"""
    
    def __init__(self):
        self.model = None
        self.is_trained = False
        self.training_data = []
    
    def train_inverse_kinematics(self, robot_arm: RobotArm, num_samples: int = 10000):
        """训练逆运动学模型"""
        logger.info("开始训练逆运动学模型...")
        
        # 生成训练数据
        X = []  # 末端位置
        y = []  # 关节角度
        
        for _ in range(num_samples):
            # 随机生成关节角度
            joint_angles = []
            for joint in robot_arm.joints:
                low, high = joint.limits
                angle = np.random.uniform(low, high)
                joint_angles.append(angle)
            
            # 计算正运动学
            positions = robot_arm.forward_kinematics(joint_angles)
            end_effector_pos = positions[-1]
            
            X.append(end_effector_pos)
            y.append(joint_angles)
        
        # 转换为numpy数组
        X = np.array(X)
        y = np.array(y)
        
        # 这里使用简单的神经网络（实际中可以使用更复杂的模型）
        from sklearn.neural_network import MLPRegressor
        from sklearn.model_selection import train_test_split
        from sklearn.preprocessing import StandardScaler
        
        # 分割训练集和测试集
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)
        
        # 标准化
        self.scaler_X = StandardScaler()
        self.scaler_y = StandardScaler()
        
        X_train_scaled = self.scaler_X.fit_transform(X_train)
        y_train_scaled = self.scaler_y.fit_transform(y_train)
        
        # 训练模型
        self.model = MLPRegressor(
            hidden_layer_sizes=(100, 100, 50),
            activation='relu',
            solver='adam',
            max_iter=1000,
            random_state=42
        )
        
        self.model.fit(X_train_scaled, y_train_scaled)
        
        # 评估模型
        X_test_scaled = self.scaler_X.transform(X_test)
        y_pred_scaled = self.model.predict(X_test_scaled)
        y_pred = self.scaler_y.inverse_transform(y_pred_scaled)
        
        mse = np.mean((y_test - y_pred) ** 2)
        logger.info(f"逆运动学模型训练完成，测试集MSE: {mse:.6f}")
        
        self.is_trained = True
    
    def predict_inverse_kinematics(self, target_position: np.ndarray) -> List[float]:
        """使用机器学习模型预测逆运动学"""
        if not self.is_trained or self.model is None:
            raise ValueError("模型未训练")
        
        # 标准化输入
        target_scaled = self.scaler_X.transform([target_position])
        # 预测
        angles_scaled = self.model.predict(target_scaled)
        # 反标准化
        angles = self.scaler_y.inverse_transform(angles_scaled)
        
        return angles[0].tolist()

class VisionSystem:
    """视觉系统"""
    
    def __init__(self):
        self.cameras = {}
        self.object_detector = ObjectDetector()
        self.pose_estimator = PoseEstimator()
    
    def add_camera(self, name: str, intrinsic_matrix: np.ndarray, 
                   extrinsic_matrix: np.ndarray):
        """添加相机"""
        self.cameras[name] = {
            'intrinsic': intrinsic_matrix,
            'extrinsic': extrinsic_matrix
        }
    
    def detect_objects(self, image: np.ndarray) -> List[Dict]:
        """检测物体"""
        return self.object_detector.detect(image)
    
    def estimate_pose(self, object_points: np.ndarray, 
                      image_points: np.ndarray) -> np.ndarray:
        """估计物体姿态"""
        return self.pose_estimator.estimate(object_points, image_points)

class ObjectDetector:
    """物体检测器"""
    
    def detect(self, image: np.ndarray) -> List[Dict]:
        """检测物体（简化实现）"""
        # 实际中应使用深度学习模型如YOLO、Faster R-CNN等
        return []  # 返回检测到的物体列表

class PoseEstimator:
    """姿态估计器"""
    
    def estimate(self, object_points: np.ndarray, 
                 image_points: np.ndarray) -> np.ndarray:
        """估计物体姿态（简化实现）"""
        # 实际中应使用PnP算法等
        return np.eye(4)  # 返回变换矩阵

class DataLogger:
    """数据记录器"""
    
    def __init__(self):
        self.data = []
        self.max_records = 100000  # 最大记录数
        self.is_logging = False
    
    def start_logging(self):
        """开始记录"""
        self.is_logging = True
        self.data = []
        logger.info("数据记录已开始")
    
    def stop_logging(self):
        """停止记录"""
        self.is_logging = False
        logger.info("数据记录已停止")
    
    def log(self, record: Dict):
        """记录数据"""
        if self.is_logging and len(self.data) < self.max_records:
            self.data.append(record)
    
    def save(self, filename: str):
        """保存数据"""
        with open(filename, 'wb') as f:
            pickle.dump(self.data, f)
        logger.info(f"数据已保存到 {filename}")
    
    def load(self, filename: str):
        """加载数据"""
        with open(filename, 'rb') as f:
            self.data = pickle.load(f)
        logger.info(f"数据已从 {filename} 加载")
    
    def analyze_performance(self) -> Dict:
        """分析性能"""
        if not self.data:
            return {}
        
        # 计算各种性能指标
        positions = np.array([d['position'] for d in self.data])
        target_positions = np.array([d['target_position'] for d in self.data])
        
        # 位置误差
        position_errors = np.linalg.norm(positions - target_positions, axis=1)
        
        return {
            'max_position_error': np.max(position_errors),
            'mean_position_error': np.mean(position_errors),
            'std_position_error': np.std(position_errors),
            'smoothness': self._calculate_smoothness(positions)
        }
    
    def _calculate_smoothness(self, positions: np.ndarray) -> float:
        """计算运动平滑度"""
        if len(positions) < 3:
            return 0.0
        
        # 计算加速度的方差作为平滑度指标
        velocities = np.diff(positions, axis=0)
        accelerations = np.diff(velocities, axis=0)
        
        if len(accelerations) == 0:
            return 0.0
        
        acceleration_magnitudes = np.linalg.norm(accelerations, axis=1)
        return 1.0 / (1.0 + np.var(acceleration_magnitudes))  # 方差越小越平滑
    
class RealTimePlotWidget(pg.PlotWidget):
    """实时绘图组件"""
    
    def __init__(self, title="实时数据", max_points=1000):
        super().__init__(title=title)
        self.max_points = max_points
        self.data = {}
        self.curves = {}
        
        self.setBackground('w')
        self.showGrid(x=True, y=True)
        self.setLabel('left', '数值')
        self.setLabel('bottom', '时间', 's')
    
    def add_data_series(self, name, color='b'):
        """添加数据系列"""
        self.data[name] = []
        self.curves[name] = self.plot(pen=pg.mkPen(color, width=2))
    
    def update_data(self, name, value, timestamp):
        """更新数据"""
        if name not in self.data:
            self.add_data_series(name)
        
        self.data[name].append((timestamp, value))
        
        # 限制数据点数
        if len(self.data[name]) > self.max_points:
            self.data[name].pop(0)
        
        # 更新曲线
        if self.data[name]:
            times, values = zip(*self.data[name])
            self.curves[name].setData(times, values)

class EnhancedControlPanel(QWidget):
    """增强版控制面板"""
    
    def __init__(self, robot_arm: SmartRobotArm, viewer: Robot3DViewer):
        super().__init__()
        self.robot_arm = robot_arm
        self.viewer = viewer
        self.init_ui()
        self.setup_connections()
        
        # 启动控制循环
        self.robot_arm.start_control_loop()
    
    def init_ui(self):
        """初始化UI"""
        main_layout = QHBoxLayout()
        
        # 左侧：控制面板
        left_panel = QWidget()
        left_layout = QVBoxLayout()
        left_panel.setLayout(left_layout)
        
        # 标签页控件
        self.tab_widget = QTabWidget()
        left_layout.addWidget(self.tab_widget)
        
        # 基本控制标签页
        self.setup_basic_control_tab()
        
        # 高级控制标签页
        self.setup_advanced_control_tab()
        
        # 机器学习标签页
        self.setup_ml_tab()
        
        # 视觉标签页
        self.setup_vision_tab()
        
        # 数据分析标签页
        self.setup_analysis_tab()
        
        # 右侧：实时数据显示
        right_panel = QWidget()
        right_layout = QVBoxLayout()
        right_panel.setLayout(right_layout)
        
        # 3D可视化
        right_layout.addWidget(QLabel("3D可视化"))
        right_layout.addWidget(self.viewer)
        
        # 实时数据图表
        self.setup_realtime_plots(right_layout)
        
        # 主布局
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([400, 800])
        
        main_layout.addWidget(splitter)
        self.setLayout(main_layout)
    
    def setup_basic_control_tab(self):
        """设置基本控制标签页"""
        basic_tab = QWidget()
        layout = QVBoxLayout()
        basic_tab.setLayout(layout)
        
        # 控制模式选择
        control_mode_group = QGroupBox("控制模式")
        control_layout = QVBoxLayout()
        
        self.control_mode_combo = QComboBox()
        self.control_mode_combo.addItems([
            "位置控制", "速度控制", "力控制", "阻抗控制", "导纳控制"
        ])
        control_layout.addWidget(QLabel("控制模式:"))
        control_layout.addWidget(self.control_mode_combo)
        
        control_mode_group.setLayout(control_layout)
        layout.addWidget(control_mode_group)
        
        # 关节控制
        joint_group = QGroupBox("关节控制")
        joint_layout = QVBoxLayout()
        
        self.joint_sliders = []
        for i, joint in enumerate(self.robot_arm.joints):
            slider_widget = self.create_joint_slider(i, joint)
            joint_layout.addWidget(slider_widget)
        
        joint_group.setLayout(joint_layout)
        layout.addWidget(joint_group)
        
        # 逆运动学控制
        ik_group = QGroupBox("逆运动学控制")
        ik_layout = QVBoxLayout()
        
        pos_layout = QHBoxLayout()
        for axis, label_text in zip(['X', 'Y', 'Z'], ['X:', 'Y:', 'Z:']):
            pos_sublayout = QVBoxLayout()
            pos_sublayout.addWidget(QLabel(label_text))
            spinbox = QDoubleSpinBox()
            spinbox.setRange(-2.0, 2.0)
            spinbox.setSingleStep(0.1)
            spinbox.setValue(0.0)
            pos_sublayout.addWidget(spinbox)
            pos_layout.addLayout(pos_sublayout)
            setattr(self, f'pos_{axis.lower()}', spinbox)
        
        ik_layout.addLayout(pos_layout)
        
        solve_btn = QPushButton("逆运动学求解")
        solve_btn.clicked.connect(self.solve_inverse_kinematics)
        ik_layout.addWidget(solve_btn)
        
        ik_group.setLayout(ik_layout)
        layout.addWidget(ik_group)
        
        self.tab_widget.addTab(basic_tab, "基本控制")
    
    def setup_advanced_control_tab(self):
        """设置高级控制标签页"""
        advanced_tab = QWidget()
        layout = QVBoxLayout()
        advanced_tab.setLayout(layout)
        
        # 轨迹规划
        trajectory_group = QGroupBox("轨迹规划")
        trajectory_layout = QVBoxLayout()
        
        # 轨迹类型选择
        self.trajectory_type_combo = QComboBox()
        self.trajectory_type_combo.addItems([
            "直线", "圆弧", "多项式", "样条", "最小加加速度", "自适应"
        ])
        trajectory_layout.addWidget(QLabel("轨迹类型:"))
        trajectory_layout.addWidget(self.trajectory_type_combo)
        
        # 轨迹参数
        self.trajectory_params_widget = QWidget()
        trajectory_params_layout = QVBoxLayout()
        self.trajectory_params_widget.setLayout(trajectory_params_layout)
        trajectory_layout.addWidget(self.trajectory_params_widget)
        
        # 执行轨迹
        execute_btn = QPushButton("执行轨迹")
        execute_btn.clicked.connect(self.execute_trajectory)
        trajectory_layout.addWidget(execute_btn)
        
        trajectory_group.setLayout(trajectory_layout)
        layout.addWidget(trajectory_group)
        
        # 力控制参数
        force_control_group = QGroupBox("力控制")
        force_layout = QVBoxLayout()
        
        force_params_layout = QHBoxLayout()
        for axis, label_text in zip(['X', 'Y', 'Z'], ['Fx:', 'Fy:', 'Fz:']):
            force_sublayout = QVBoxLayout()
            force_sublayout.addWidget(QLabel(label_text))
            spinbox = QDoubleSpinBox()
            spinbox.setRange(-10.0, 10.0)
            spinbox.setSingleStep(0.1)
            spinbox.setValue(0.0)
            force_sublayout.addWidget(spinbox)
            force_params_layout.addLayout(force_sublayout)
            setattr(self, f'force_{axis.lower()}', spinbox)
        
        force_layout.addLayout(force_params_layout)
        
        set_force_btn = QPushButton("设置目标力")
        set_force_btn.clicked.connect(self.set_target_force)
        force_layout.addWidget(set_force_btn)
        
        force_control_group.setLayout(force_layout)
        layout.addWidget(force_control_group)
        
        self.tab_widget.addTab(advanced_tab, "高级控制")
    
    def setup_ml_tab(self):
        """设置机器学习标签页"""
        ml_tab = QWidget()
        layout = QVBoxLayout()
        ml_tab.setLayout(layout)
        
        # 模型训练
        training_group = QGroupBox("模型训练")
        training_layout = QVBoxLayout()
        
        self.training_progress = QProgressBar()
        training_layout.addWidget(QLabel("训练进度:"))
        training_layout.addWidget(self.training_progress)
        
        train_btn = QPushButton("训练逆运动学模型")
        train_btn.clicked.connect(self.train_ik_model)
        training_layout.addWidget(train_btn)
        
        training_group.setLayout(training_layout)
        layout.addWidget(training_group)
        
        # 模型使用
        inference_group = QGroupBox("模型推理")
        inference_layout = QVBoxLayout()
        
        use_ml_ik_check = QCheckBox("使用机器学习逆运动学")
        inference_layout.addWidget(use_ml_ik_check)
        
        inference_group.setLayout(inference_layout)
        layout.addWidget(inference_group)
        
        self.tab_widget.addTab(ml_tab, "机器学习")
    
    def setup_vision_tab(self):
        """设置视觉标签页"""
        vision_tab = QWidget()
        layout = QVBoxLayout()
        vision_tab.setLayout(layout)
        
        # 相机配置
        camera_group = QGroupBox("相机配置")
        camera_layout = QVBoxLayout()
        
        add_camera_btn = QPushButton("添加相机")
        add_camera_btn.clicked.connect(self.add_camera)
        camera_layout.addWidget(add_camera_btn)
        
        camera_group.setLayout(camera_layout)
        layout.addWidget(camera_group)
        
        # 物体检测
        detection_group = QGroupBox("物体检测")
        detection_layout = QVBoxLayout()
        
        detect_btn = QPushButton("检测物体")
        detect_btn.clicked.connect(self.detect_objects)
        detection_layout.addWidget(detect_btn)
        
        detection_group.setLayout(detection_layout)
        layout.addWidget(detection_group)
        
        self.tab_widget.addTab(vision_tab, "视觉系统")
    
    def setup_analysis_tab(self):
        """设置数据分析标签页"""
        analysis_tab = QWidget()
        layout = QVBoxLayout()
        analysis_tab.setLayout(layout)
        
        # 数据记录
        logging_group = QGroupBox("数据记录")
        logging_layout = QHBoxLayout()
        
        start_logging_btn = QPushButton("开始记录")
        start_logging_btn.clicked.connect(self.start_logging)
        logging_layout.addWidget(start_logging_btn)
        
        stop_logging_btn = QPushButton("停止记录")
        stop_logging_btn.clicked.connect(self.stop_logging)
        logging_layout.addWidget(stop_logging_btn)
        
        save_data_btn = QPushButton("保存数据")
        save_data_btn.clicked.connect(self.save_data)
        logging_layout.addWidget(save_data_btn)
        
        logging_group.setLayout(logging_layout)
        layout.addWidget(logging_group)
        
        # 性能分析
        analysis_group = QGroupBox("性能分析")
        analysis_layout = QVBoxLayout()
        
        self.performance_table = QTableWidget()
        self.performance_table.setColumnCount(2)
        self.performance_table.setHorizontalHeaderLabels(["指标", "数值"])
        analysis_layout.addWidget(self.performance_table)
        
        analyze_btn = QPushButton("分析性能")
        analyze_btn.clicked.connect(self.analyze_performance)
        analysis_layout.addWidget(analyze_btn)
        
        analysis_group.setLayout(analysis_layout)
        layout.addWidget(analysis_group)
        
        self.tab_widget.addTab(analysis_tab, "数据分析")
    
    def setup_realtime_plots(self, layout):
        """设置实时数据图表"""
        # 位置图表
        self.position_plot = RealTimePlotWidget("末端位置")
        self.position_plot.add_data_series("X", 'r')
        self.position_plot.add_data_series("Y", 'g')
        self.position_plot.add_data_series("Z", 'b')
        layout.addWidget(self.position_plot)
        
        # 误差图表
        self.error_plot = RealTimePlotWidget("位置误差")
        self.error_plot.add_data_series("误差", 'm')
        layout.addWidget(self.error_plot)
        
        # 力图表
        self.force_plot = RealTimePlotWidget("末端力")
        self.force_plot.add_data_series("Fx", 'r')
        self.force_plot.add_data_series("Fy", 'g')
        self.force_plot.add_data_series("Fz", 'b')
        layout.addWidget(self.force_plot)
    
    def create_joint_slider(self, index, joint):
        """创建关节滑块控件"""
        widget = QWidget()
        layout = QHBoxLayout()
        widget.setLayout(layout)
        
        label = QLabel(f"关节 {index+1}:")
        slider = QSlider(Qt.Horizontal)
        slider.setMinimum(int(math.degrees(joint.limits[0])))
        slider.setMaximum(int(math.degrees(joint.limits[1])))
        slider.setValue(0)
        
        value_label = QLabel("0°")
        value_lcd = QLCDNumber()
        value_lcd.display(0)
        
        # 连接信号
        slider.valueChanged.connect(
            lambda value, idx=index, lbl=value_label, lcd=value_lcd: 
            self.on_joint_slider_change(value, idx, lbl, lcd)
        )
        
        layout.addWidget(label)
        layout.addWidget(slider)
        layout.addWidget(value_label)
        layout.addWidget(value_lcd)
        
        self.joint_sliders.append((slider, value_label, value_lcd))
        return widget
    
    def setup_connections(self):
        """设置信号连接"""
        # 控制模式变化
        self.control_mode_combo.currentTextChanged.connect(self.on_control_mode_changed)
        
        # 定时器更新实时数据
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_realtime_data)
        self.update_timer.start(100)  # 10Hz更新
    
    def on_control_mode_changed(self, mode_text):
        """控制模式变化处理"""
        mode_mapping = {
            "位置控制": ControlMode.POSITION_CONTROL,
            "速度控制": ControlMode.VELOCITY_CONTROL,
            "力控制": ControlMode.FORCE_CONTROL,
            "阻抗控制": ControlMode.IMPEDANCE_CONTROL,
            "导纳控制": ControlMode.ADMITTANCE_CONTROL
        }
        
        if mode_text in mode_mapping:
            self.robot_arm.control_mode = mode_mapping[mode_text]
            logger.info(f"控制模式已切换为: {mode_text}")
    
    def on_joint_slider_change(self, value, joint_index, label, lcd):
        """关节滑块变化处理"""
        angle_rad = math.radians(value)
        label.setText(f"{value}°")
        lcd.display(value)
        
        # 更新关节角度
        current_angles = [j.value for j in self.robot_arm.joints]
        current_angles[joint_index] = angle_rad
        
        # 更新3D显示
        self.viewer.update_joints(current_angles)
    
    def solve_inverse_kinematics(self):
        """逆运动学求解"""
        target_pos = np.array([
            self.pos_x.value(),
            self.pos_y.value(),
            self.pos_z.value()
        ])
        
        try:
            if hasattr(self.robot_arm.machine_learning_model, 'is_trained') and \
               self.robot_arm.machine_learning_model.is_trained:
                # 使用机器学习模型
                solution = self.robot_arm.machine_learning_model.predict_inverse_kinematics(target_pos)
            else:
                # 使用数值方法
                initial_angles = [j.value for j in self.robot_arm.joints]
                solution = self.robot_arm.inverse_kinematics(target_pos, initial_angles)
            
            # 更新显示
            self.viewer.update_joints(solution)
            
            # 更新滑块
            for i, angle in enumerate(solution):
                slider, label, lcd = self.joint_sliders[i]
                angle_deg = math.degrees(angle)
                slider.setValue(int(angle_deg))
                label.setText(f"{int(angle_deg)}°")
                lcd.display(int(angle_deg))
                
        except Exception as e:
            QMessageBox.warning(self, "错误", f"逆运动学求解失败: {e}")
    
    def execute_trajectory(self):
        """执行轨迹"""
        trajectory_type_mapping = {
            "直线": TrajectoryType.LINEAR,
            "圆弧": TrajectoryType.CIRCULAR,
            "多项式": TrajectoryType.POLYNOMIAL,
            "样条": TrajectoryType.SPLINE,
            "最小加加速度": TrajectoryType.MINIMUM_JERK,
            "自适应": TrajectoryType.ADAPTIVE
        }
        
        trajectory_type = trajectory_type_mapping.get(
            self.trajectory_type_combo.currentText(), 
            TrajectoryType.LINEAR
        )
        
        # 设置轨迹参数
        self.robot_arm.set_trajectory(
            trajectory_type,
            end_position=np.array([self.pos_x.value(), self.pos_y.value(), self.pos_z.value()])
        )
        
        # 执行轨迹
        self.robot_arm.execute_trajectory(duration=5.0)  # 5秒轨迹
    
    def set_target_force(self):
        """设置目标力"""
        target_force = np.array([
            self.force_x.value(),
            self.force_y.value(),
            self.force_z.value()
        ])
        
        self.robot_arm.force_controller.set_target_force(target_force)
    
    def train_ik_model(self):
        """训练逆运动学模型"""
        # 在后台线程中训练模型
        self.training_thread = TrainingThread(self.robot_arm)
        self.training_thread.progress_updated.connect(self.update_training_progress)
        self.training_thread.training_finished.connect(self.on_training_finished)
        self.training_thread.start()
    
    def update_training_progress(self, progress):
        """更新训练进度"""
        self.training_progress.setValue(progress)
    
    def on_training_finished(self, success):
        """训练完成处理"""
        if success:
            QMessageBox.information(self, "成功", "逆运动学模型训练完成")
        else:
            QMessageBox.warning(self, "错误", "模型训练失败")
    
    def add_camera(self):
        """添加相机"""
        # 相机配置对话框
        pass
    
    def detect_objects(self):
        """检测物体"""
        # 物体检测功能
        pass
    
    def start_logging(self):
        """开始记录数据"""
        self.robot_arm.data_logger.start_logging()
    
    def stop_logging(self):
        """停止记录数据"""
        self.robot_arm.data_logger.stop_logging()
    
    def save_data(self):
        """保存数据"""
        filename, _ = QFileDialog.getSaveFileName(
            self, "保存数据", "", "数据文件 (*.pkl)"
        )
        if filename:
            self.robot_arm.data_logger.save(filename)
    
    def analyze_performance(self):
        """分析性能"""
        performance = self.robot_arm.data_logger.analyze_performance()
        
        self.performance_table.setRowCount(len(performance))
        for i, (key, value) in enumerate(performance.items()):
            self.performance_table.setItem(i, 0, QTableWidgetItem(key))
            self.performance_table.setItem(i, 1, QTableWidgetItem(f"{value:.6f}"))
    
    def update_realtime_data(self):
        """更新实时数据"""
        current_time = time.time()
        
        # 更新位置图表
        pos = self.robot_arm.current_position
        self.position_plot.update_data("X", pos[0], current_time)
        self.position_plot.update_data("Y", pos[1], current_time)
        self.position_plot.update_data("Z", pos[2], current_time)
        
        # 更新误差图表
        error = np.linalg.norm(pos - self.robot_arm.target_position)
        self.error_plot.update_data("误差", error, current_time)
        
        # 更新力图图表
        force = self.robot_arm.current_force
        self.force_plot.update_data("Fx", force[0], current_time)
        self.force_plot.update_data("Fy", force[1], current_time)
        self.force_plot.update_data("Fz", force[2], current_time)

class TrainingThread(QThread):
    """训练线程"""
    
    progress_updated = pyqtSignal(int)
    training_finished = pyqtSignal(bool)
    
    def __init__(self, robot_arm):
        super().__init__()
        self.robot_arm = robot_arm
    
    def run(self):
        """运行训练"""
        try:
            # 模拟训练过程
            for i in range(101):
                self.progress_updated.emit(i)
                time.sleep(0.05)  # 模拟训练时间
            
            # 实际训练
            self.robot_arm.machine_learning_model.train_inverse_kinematics(self.robot_arm, 1000)
            self.training_finished.emit(True)
        except Exception as e:
            logger.error(f"训练失败: {e}")
            self.training_finished.emit(False)

class EnhancedMainWindow(QMainWindow):
    """增强版主窗口"""
    
    def __init__(self):
        super().__init__()
        self.robot_arm = self.create_enhanced_robot()
        self.init_ui()
    
    def create_enhanced_robot(self) -> SmartRobotArm:
        """创建增强版机械臂"""
        robot = SmartRobotArm("智能六轴机械臂", control_frequency=100.0)
        
        # DH参数: a, alpha, d, theta
        dh_params = [
            DHParameters(0, math.pi/2, 0.5, 0),      # 关节1
            DHParameters(0.8, 0, 0, 0),              # 关节2
            DHParameters(0.6, 0, 0, 0),              # 关节3
            DHParameters(0, math.pi/2, 0.4, 0),      # 关节4
            DHParameters(0, -math.pi/2, 0, 0),       # 关节5
            DHParameters(0, 0, 0.2, 0)               # 关节6
        ]
        
        # 关节限制（弧度）和参数
        joint_specs = [
            ((-math.pi, math.pi), 1.0, 10.0),     # 关节1
            ((-math.pi/2, math.pi/2), 1.0, 8.0),  # 关节2
            ((-math.pi/2, math.pi/2), 1.0, 8.0),  # 关节3
            ((-math.pi, math.pi), 1.5, 5.0),      # 关节4
            ((-math.pi/2, math.pi/2), 2.0, 3.0),  # 关节5
            ((-math.pi, math.pi), 2.5, 2.0)       # 关节6
        ]
        
        for i, (dh, (limits, max_vel, max_torque)) in enumerate(zip(dh_params, joint_specs)):
            # 创建惯性张量（简化）
            inertia = InertiaTensor(0.1, 0.1, 0.1)
            
            link = Link(f"连杆{i+1}", dh, mass=1.0, com=np.array([0,0,0]), inertia=inertia)
            joint = Joint(f"关节{i+1}", "revolute", limits, max_vel, max_torque)
            robot.add_link(link, joint)
        
        return robot
    
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("智能连杆机械臂系统 - 增强版")
        self.setGeometry(100, 100, 1400, 900)
        
        # 中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 3D可视化
        self.viewer = Robot3DViewer(self.robot_arm)
        
        # 控制面板
        self.control_panel = EnhancedControlPanel(self.robot_arm, self.viewer)
        
        # 主布局
        main_layout = QHBoxLayout()
        main_layout.addWidget(self.control_panel)
        main_layout.addWidget(self.viewer)
        
        central_widget.setLayout(main_layout)
        
        # 状态栏
        self.statusBar().showMessage("智能机械臂系统就绪 - 增强版")
    
    def closeEvent(self, event):
        """关闭事件处理"""
        self.robot_arm.stop_control_loop()
        event.accept()

def main():
    """主函数"""
    app = QApplication([])
    
    # 设置应用程序样式
    app.setStyle('Fusion')
    
    window = EnhancedMainWindow()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()