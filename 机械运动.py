import sys
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                             QWidget, QPushButton, QSlider, QLabel, QComboBox, 
                             QTabWidget, QGroupBox, QSpinBox, QDoubleSpinBox, 
                             QCheckBox, QTextEdit, QSplitter, QFileDialog, QMessageBox)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont
import json
import time
from scipy.integrate import solve_ivp
from dataclasses import dataclass
from typing import List, Tuple, Dict, Any
import math

# 机器部件基类
class MachineComponent:
    def __init__(self, name, position=(0, 0), rotation=0):
        self.name = name
        self.position = np.array(position, dtype=float)
        self.rotation = rotation
        self.children = []
        self.parent = None
        
    def add_child(self, component):
        component.parent = self
        self.children.append(component)
        
    def get_global_position(self):
        if self.parent is None:
            return self.position
        else:
            parent_pos = self.parent.get_global_position()
            parent_rot = self.parent.get_global_rotation()
            
            # 旋转矩阵
            cos_theta = np.cos(parent_rot)
            sin_theta = np.sin(parent_rot)
            rotation_matrix = np.array([[cos_theta, -sin_theta], 
                                       [sin_theta, cos_theta]])
            
            return parent_pos + rotation_matrix @ self.position
    
    def get_global_rotation(self):
        if self.parent is None:
            return self.rotation
        else:
            return self.parent.get_global_rotation() + self.rotation
    
    def update(self, dt):
        # 更新组件状态
        pass

# 运动学模型基类
class KinematicModel:
    def __init__(self, name):
        self.name = name
        self.dof = 0  # 自由度
        self.joint_limits = []  # 关节限制
        self.parameters = {}  # 模型参数
        
    def forward_kinematics(self, joint_angles):
        # 正向运动学
        raise NotImplementedError
    
    def inverse_kinematics(self, target_position):
        # 逆向运动学
        raise NotImplementedError
    
    def jacobian(self, joint_angles):
        # 雅可比矩阵
        raise NotImplementedError

# 二连杆机械臂模型
class TwoLinkArm(KinematicModel):
    def __init__(self, l1=1.0, l2=0.8):
        super().__init__("Two-Link Arm")
        self.dof = 2
        self.joint_limits = [(-np.pi, np.pi), (-np.pi, np.pi)]
        self.parameters = {"l1": l1, "l2": l2}
        
    def forward_kinematics(self, joint_angles):
        theta1, theta2 = joint_angles
        l1, l2 = self.parameters["l1"], self.parameters["l2"]
        
        x = l1 * np.cos(theta1) + l2 * np.cos(theta1 + theta2)
        y = l1 * np.sin(theta1) + l2 * np.sin(theta1 + theta2)
        
        return np.array([x, y])
    
    def inverse_kinematics(self, target_position):
        x, y = target_position
        l1, l2 = self.parameters["l1"], self.parameters["l2"]
        
        # 计算第二个关节角度
        D = (x**2 + y**2 - l1**2 - l2**2) / (2 * l1 * l2)
        D = np.clip(D, -1, 1)  # 避免数值误差
        
        theta2 = np.arccos(D)  # 肘部向上解
        # theta2 = -np.arccos(D)  # 肘部向下解
        
        # 计算第一个关节角度
        theta1 = np.arctan2(y, x) - np.arctan2(l2 * np.sin(theta2), l1 + l2 * np.cos(theta2))
        
        return np.array([theta1, theta2])
    
    def jacobian(self, joint_angles):
        theta1, theta2 = joint_angles
        l1, l2 = self.parameters["l1"], self.parameters["l2"]
        
        J11 = -l1 * np.sin(theta1) - l2 * np.sin(theta1 + theta2)
        J12 = -l2 * np.sin(theta1 + theta2)
        J21 = l1 * np.cos(theta1) + l2 * np.cos(theta1 + theta2)
        J22 = l2 * np.cos(theta1 + theta2)
        
        return np.array([[J11, J12], [J21, J22]])

# 运动轨迹规划器
class TrajectoryPlanner:
    def __init__(self):
        self.trajectory_types = ["Linear", "Circular", "Spline", "Point-to-Point"]
        
    def plan_linear_trajectory(self, start, end, num_points=100):
        """规划直线轨迹"""
        t = np.linspace(0, 1, num_points)
        trajectory = start + t[:, np.newaxis] * (end - start)
        return trajectory
    
    def plan_circular_trajectory(self, center, radius, start_angle, end_angle, num_points=100):
        """规划圆形轨迹"""
        angles = np.linspace(start_angle, end_angle, num_points)
        trajectory = center + radius * np.column_stack([np.cos(angles), np.sin(angles)])
        return trajectory
    
    def plan_point_to_point(self, via_points, num_points_per_segment=50):
        """规划点对点轨迹"""
        trajectory = []
        for i in range(len(via_points) - 1):
            segment = self.plan_linear_trajectory(via_points[i], via_points[i+1], num_points_per_segment)
            trajectory.extend(segment)
        return np.array(trajectory)

# 机器模拟器
class MachineSimulator:
    def __init__(self, kinematic_model):
        self.model = kinematic_model
        self.current_joint_angles = np.zeros(self.model.dof)
        self.target_position = np.array([0.0, 0.0])
        self.trajectory = None
        self.trajectory_index = 0
        self.is_moving = False
        self.speed = 1.0
        self.control_mode = "position"  # "position" or "velocity"
        
    def set_target(self, target_position):
        self.target_position = target_position
        self.is_moving = True
        
    def set_trajectory(self, trajectory):
        self.trajectory = trajectory
        self.trajectory_index = 0
        self.is_moving = True
        
    def update(self, dt):
        if not self.is_moving or self.trajectory is None:
            return
            
        if self.trajectory_index < len(self.trajectory):
            target = self.trajectory[self.trajectory_index]
            
            # 简单的位置控制
            current_pos = self.model.forward_kinematics(self.current_joint_angles)
            error = target - current_pos
            
            # 使用雅可比矩阵的伪逆进行控制
            J = self.model.jacobian(self.current_joint_angles)
            if np.linalg.matrix_rank(J) == J.shape[0]:  # 检查是否满秩
                J_inv = np.linalg.pinv(J)
                joint_velocity = J_inv @ error * self.speed
                self.current_joint_angles += joint_velocity * dt
            else:
                # 奇异位置，使用其他策略
                pass
                
            self.trajectory_index += 1
        else:
            self.is_moving = False

# 数据记录器
class DataLogger:
    def __init__(self):
        self.data = {}
        self.time_data = []
        
    def start_recording(self):
        self.data = {}
        self.time_data = []
        
    def log(self, time, **kwargs):
        self.time_data.append(time)
        for key, value in kwargs.items():
            if key not in self.data:
                self.data[key] = []
            self.data[key].append(value)
            
    def get_data(self, key):
        return self.data.get(key, [])
    
    def save_to_file(self, filename):
        data_to_save = {"time": self.time_data}
        data_to_save.update(self.data)
        
        with open(filename, 'w') as f:
            json.dump(data_to_save, f, indent=2)
            
    def load_from_file(self, filename):
        with open(filename, 'r') as f:
            data = json.load(f)
            
        self.time_data = data.get("time", [])
        self.data = {k: v for k, v in data.items() if k != "time"}

# 可视化组件
class MachineVisualization(FigureCanvas):
    def __init__(self, parent=None, width=8, height=6, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        super().__init__(self.fig)
        self.setParent(parent)
        
        self.axes = self.fig.add_subplot(111)
        self.axes.set_aspect('equal')
        self.axes.grid(True)
        self.axes.set_xlabel('X')
        self.axes.set_ylabel('Y')
        self.axes.set_title('Machine Simulation')
        
        # 初始化图形元素
        self.arm_line, = self.axes.plot([], [], 'o-', lw=2, markersize=8)
        self.target_point, = self.axes.plot([], [], 'rx', markersize=10)
        self.trajectory_line, = self.axes.plot([], [], 'g--', alpha=0.5)
        
        self.axes.set_xlim(-2, 2)
        self.axes.set_ylim(-2, 2)
        
    def update_visualization(self, simulator, trajectory=None):
        # 获取机械臂位置
        model = simulator.model
        angles = simulator.current_joint_angles
        
        # 计算关节位置
        l1, l2 = model.parameters["l1"], model.parameters["l2"]
        theta1, theta2 = angles
        
        x0, y0 = 0, 0
        x1 = l1 * np.cos(theta1)
        y1 = l1 * np.sin(theta1)
        x2 = x1 + l2 * np.cos(theta1 + theta2)
        y2 = y1 + l2 * np.sin(theta1 + theta2)
        
        # 更新机械臂图形
        self.arm_line.set_data([x0, x1, x2], [y0, y1, y2])
        
        # 更新目标点
        self.target_point.set_data([simulator.target_position[0]], 
                                  [simulator.target_position[1]])
        
        # 更新轨迹
        if trajectory is not None and len(trajectory) > 0:
            self.trajectory_line.set_data(trajectory[:, 0], trajectory[:, 1])
        else:
            self.trajectory_line.set_data([], [])
            
        self.draw()

# 主控制面板
class ControlPanel(QWidget):
    # 信号定义
    simulationStarted = pyqtSignal()
    simulationStopped = pyqtSignal()
    targetChanged = pyqtSignal(float, float)
    trajectoryChanged = pyqtSignal(object)
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 模型选择
        model_group = QGroupBox("Machine Model")
        model_layout = QVBoxLayout()
        
        self.model_combo = QComboBox()
        self.model_combo.addItems(["Two-Link Arm", "SCARA Robot", "Cartesian Robot"])
        model_layout.addWidget(QLabel("Select Model:"))
        model_layout.addWidget(self.model_combo)
        
        # 模型参数
        param_layout = QHBoxLayout()
        param_layout.addWidget(QLabel("Link 1:"))
        self.link1_spin = QDoubleSpinBox()
        self.link1_spin.setRange(0.1, 5.0)
        self.link1_spin.setValue(1.0)
        self.link1_spin.setSingleStep(0.1)
        param_layout.addWidget(self.link1_spin)
        
        param_layout.addWidget(QLabel("Link 2:"))
        self.link2_spin = QDoubleSpinBox()
        self.link2_spin.setRange(0.1, 5.0)
        self.link2_spin.setValue(0.8)
        self.link2_spin.setSingleStep(0.1)
        param_layout.addWidget(self.link2_spin)
        
        model_layout.addLayout(param_layout)
        model_group.setLayout(model_layout)
        layout.addWidget(model_group)
        
        # 控制模式
        control_group = QGroupBox("Control")
        control_layout = QVBoxLayout()
        
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("Control Mode:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Position Control", "Velocity Control", "Trajectory Tracking"])
        mode_layout.addWidget(self.mode_combo)
        control_layout.addLayout(mode_layout)
        
        # 目标位置
        target_layout = QHBoxLayout()
        target_layout.addWidget(QLabel("Target X:"))
        self.target_x_spin = QDoubleSpinBox()
        self.target_x_spin.setRange(-2.0, 2.0)
        self.target_x_spin.setValue(1.2)
        self.target_x_spin.setSingleStep(0.1)
        target_layout.addWidget(self.target_x_spin)
        
        target_layout.addWidget(QLabel("Y:"))
        self.target_y_spin = QDoubleSpinBox()
        self.target_y_spin.setRange(-2.0, 2.0)
        self.target_y_spin.setValue(0.5)
        self.target_y_spin.setSingleStep(0.1)
        target_layout.addWidget(self.target_y_spin)
        
        self.set_target_btn = QPushButton("Set Target")
        self.set_target_btn.clicked.connect(self.on_set_target)
        target_layout.addWidget(self.set_target_btn)
        
        control_layout.addLayout(target_layout)
        
        # 速度控制
        speed_layout = QHBoxLayout()
        speed_layout.addWidget(QLabel("Speed:"))
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setRange(1, 100)
        self.speed_slider.setValue(50)
        speed_layout.addWidget(self.speed_slider)
        
        self.speed_label = QLabel("0.5")
        speed_layout.addWidget(self.speed_label)
        
        control_layout.addLayout(speed_layout)
        control_group.setLayout(control_layout)
        layout.addWidget(control_group)
        
        # 轨迹规划
        trajectory_group = QGroupBox("Trajectory Planning")
        trajectory_layout = QVBoxLayout()
        
        traj_type_layout = QHBoxLayout()
        traj_type_layout.addWidget(QLabel("Trajectory Type:"))
        self.traj_combo = QComboBox()
        self.traj_combo.addItems(["Linear", "Circular", "Point-to-Point"])
        traj_type_layout.addWidget(self.traj_combo)
        trajectory_layout.addLayout(traj_type_layout)
        
        self.plan_trajectory_btn = QPushButton("Plan Trajectory")
        self.plan_trajectory_btn.clicked.connect(self.on_plan_trajectory)
        trajectory_layout.addWidget(self.plan_trajectory_btn)
        
        trajectory_group.setLayout(trajectory_layout)
        layout.addWidget(trajectory_group)
        
        # 仿真控制
        sim_group = QGroupBox("Simulation")
        sim_layout = QVBoxLayout()
        
        sim_btn_layout = QHBoxLayout()
        self.start_btn = QPushButton("Start")
        self.start_btn.clicked.connect(self.on_start)
        sim_btn_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.clicked.connect(self.on_stop)
        sim_btn_layout.addWidget(self.stop_btn)
        
        self.reset_btn = QPushButton("Reset")
        self.reset_btn.clicked.connect(self.on_reset)
        sim_btn_layout.addWidget(self.reset_btn)
        
        sim_layout.addLayout(sim_btn_layout)
        
        # 记录控制
        record_layout = QHBoxLayout()
        self.record_cb = QCheckBox("Record Data")
        record_layout.addWidget(self.record_cb)
        
        self.save_data_btn = QPushButton("Save Data")
        self.save_data_btn.clicked.connect(self.on_save_data)
        record_layout.addWidget(self.save_data_btn)
        
        sim_layout.addLayout(record_layout)
        sim_group.setLayout(sim_layout)
        layout.addWidget(sim_group)
        
        layout.addStretch()
        self.setLayout(layout)
        
        # 连接信号
        self.speed_slider.valueChanged.connect(self.on_speed_changed)
        
    def on_set_target(self):
        x = self.target_x_spin.value()
        y = self.target_y_spin.value()
        self.targetChanged.emit(x, y)
        
    def on_plan_trajectory(self):
        # 这里应该根据选择的轨迹类型规划轨迹
        # 简化实现：规划一个简单的圆形轨迹
        planner = TrajectoryPlanner()
        center = np.array([0.5, 0.5])
        trajectory = planner.plan_circular_trajectory(center, 0.8, 0, 2*np.pi, 100)
        self.trajectoryChanged.emit(trajectory)
        
    def on_start(self):
        self.simulationStarted.emit()
        
    def on_stop(self):
        self.simulationStopped.emit()
        
    def on_reset(self):
        # 重置仿真
        pass
        
    def on_save_data(self):
        # 保存数据
        pass
        
    def on_speed_changed(self, value):
        speed = value / 50.0  # 映射到0.02到2.0的范围
        self.speed_label.setText(f"{speed:.2f}")

# 数据可视化面板
class DataVisualization(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 创建标签页
        self.tabs = QTabWidget()
        
        # 位置标签页
        self.pos_tab = QWidget()
        pos_layout = QVBoxLayout()
        self.pos_fig = FigureCanvas(Figure(figsize=(8, 4)))
        pos_layout.addWidget(self.pos_fig)
        self.pos_tab.setLayout(pos_layout)
        self.tabs.addTab(self.pos_tab, "Position")
        
        # 速度标签页
        self.vel_tab = QWidget()
        vel_layout = QVBoxLayout()
        self.vel_fig = FigureCanvas(Figure(figsize=(8, 4)))
        vel_layout.addWidget(self.vel_fig)
        self.vel_tab.setLayout(vel_layout)
        self.tabs.addTab(self.vel_tab, "Velocity")
        
        # 误差标签页
        self.error_tab = QWidget()
        error_layout = QVBoxLayout()
        self.error_fig = FigureCanvas(Figure(figsize=(8, 4)))
        error_layout.addWidget(self.error_fig)
        self.error_tab.setLayout(error_layout)
        self.tabs.addTab(self.error_tab, "Error")
        
        layout.addWidget(self.tabs)
        self.setLayout(layout)
        
    def update_plots(self, logger):
        time_data = logger.time_data
        
        # 更新位置图
        self.pos_fig.figure.clear()
        ax = self.pos_fig.figure.add_subplot(111)
        
        if 'x_pos' in logger.data and 'y_pos' in logger.data:
            ax.plot(time_data, logger.data['x_pos'], label='X Position')
            ax.plot(time_data, logger.data['y_pos'], label='Y Position')
            ax.legend()
            ax.set_xlabel('Time (s)')
            ax.set_ylabel('Position')
            ax.grid(True)
            
        self.pos_fig.draw()
        
        # 更新速度图
        self.vel_fig.figure.clear()
        ax = self.vel_fig.figure.add_subplot(111)
        
        if 'x_vel' in logger.data and 'y_vel' in logger.data:
            ax.plot(time_data, logger.data['x_vel'], label='X Velocity')
            ax.plot(time_data, logger.data['y_vel'], label='Y Velocity')
            ax.legend()
            ax.set_xlabel('Time (s)')
            ax.set_ylabel('Velocity')
            ax.grid(True)
            
        self.vel_fig.draw()
        
        # 更新误差图
        self.error_fig.figure.clear()
        ax = self.error_fig.figure.add_subplot(111)
        
        if 'x_error' in logger.data and 'y_error' in logger.data:
            ax.plot(time_data, logger.data['x_error'], label='X Error')
            ax.plot(time_data, logger.data['y_error'], label='Y Error')
            ax.legend()
            ax.set_xlabel('Time (s)')
            ax.set_ylabel('Error')
            ax.grid(True)
            
        self.error_fig.draw()

# 主窗口
class MachineSimulationApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.init_simulation()
        
    def init_ui(self):
        self.setWindowTitle("Generic Machine Motion Simulation System")
        self.setGeometry(100, 100, 1400, 900)
        
        # 创建中央部件和布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 使用分割器布局
        splitter = QSplitter(Qt.Horizontal)
        
        # 左侧：控制面板
        self.control_panel = ControlPanel()
        splitter.addWidget(self.control_panel)
        
        # 右侧：可视化区域
        right_splitter = QSplitter(Qt.Vertical)
        
        # 机器可视化
        self.viz = MachineVisualization()
        right_splitter.addWidget(self.viz)
        
        # 数据可视化
        self.data_viz = DataVisualization()
        right_splitter.addWidget(self.data_viz)
        
        splitter.addWidget(right_splitter)
        
        # 设置分割器比例
        splitter.setSizes([400, 1000])
        right_splitter.setSizes([600, 400])
        
        # 主布局
        layout = QHBoxLayout()
        layout.addWidget(splitter)
        central_widget.setLayout(layout)
        
        # 连接信号
        self.control_panel.simulationStarted.connect(self.start_simulation)
        self.control_panel.simulationStopped.connect(self.stop_simulation)
        self.control_panel.targetChanged.connect(self.set_target)
        self.control_panel.trajectoryChanged.connect(self.set_trajectory)
        
        # 仿真定时器
        self.sim_timer = QTimer()
        self.sim_timer.timeout.connect(self.update_simulation)
        self.sim_dt = 0.05  # 20 Hz
        
        # 数据记录器
        self.logger = DataLogger()
        
    def init_simulation(self):
        # 创建二连杆机械臂模型
        self.model = TwoLinkArm()
        self.simulator = MachineSimulator(self.model)
        self.planner = TrajectoryPlanner()
        
        # 初始目标位置
        self.simulator.target_position = np.array([1.2, 0.5])
        
    def start_simulation(self):
        if self.control_panel.record_cb.isChecked():
            self.logger.start_recording()
            self.record_start_time = time.time()
            
        self.sim_timer.start(int(self.sim_dt * 1000))
        
    def stop_simulation(self):
        self.sim_timer.stop()
        
    def set_target(self, x, y):
        self.simulator.set_target(np.array([x, y]))
        
    def set_trajectory(self, trajectory):
        self.simulator.set_trajectory(trajectory)
        self.current_trajectory = trajectory
        
    def update_simulation(self):
        # 更新仿真
        self.simulator.update(self.sim_dt)
        
        # 更新可视化
        trajectory = self.current_trajectory if hasattr(self, 'current_trajectory') else None
        self.viz.update_visualization(self.simulator, trajectory)
        
        # 记录数据
        if self.control_panel.record_cb.isChecked():
            current_time = time.time() - self.record_start_time
            
            # 获取当前位置
            current_pos = self.model.forward_kinematics(self.simulator.current_joint_angles)
            
            # 计算误差
            error = self.simulator.target_position - current_pos
            
            # 记录数据
            self.logger.log(current_time, 
                          x_pos=current_pos[0], y_pos=current_pos[1],
                          x_target=self.simulator.target_position[0], 
                          y_target=self.simulator.target_position[1],
                          x_error=error[0], y_error=error[1])
            
            # 更新数据可视化
            self.data_viz.update_plots(self.logger)

# 应用启动
if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # 设置应用样式
    app.setStyle('Fusion')
    
    # 创建并显示主窗口
    window = MachineSimulationApp()
    window.show()
    
    sys.exit(app.exec_())