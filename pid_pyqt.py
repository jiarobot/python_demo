import sys
import numpy as np
from scipy import signal
from scipy.integrate import odeint
from scipy.optimize import minimize
import matplotlib
matplotlib.rc("font", family='Microsoft YaHei')
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from matplotlib import cm
from mpl_toolkits.mplot3d import Axes3D
import matplotlib.pyplot as plt

from PyQt5.QtWidgets import (QApplication, QMainWindow, QProgressDialog, QWidget, QVBoxLayout, 
                             QHBoxLayout, QGroupBox, QLabel, QDoubleSpinBox, 
                             QSlider, QComboBox, QPushButton, QSplitter, QTabWidget,
                             QGridLayout, QCheckBox, QSpinBox, QTextEdit, QFileDialog,
                             QMessageBox, QProgressBar, QTableWidget, QTableWidgetItem,
                             QHeaderView, QDockWidget, QListWidget, QTreeWidget, QTreeWidgetItem,
                             QLineEdit, QDialog, QDialogButtonBox, QFormLayout, QSizePolicy)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QSettings
from PyQt5.QtGui import QFont, QColor, QIcon

# 添加高级控制算法
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
import control as ctrl
import pandas as pd
import json
from datetime import datetime
import os

class SystemIdentification:
    """系统辨识模块"""
    def __init__(self):
        self.methods = {
            "最小二乘法": self.least_squares,
            "最大似然法": self.maximum_likelihood,
            "子空间法": self.subspace_method,
            "神经网络": self.neural_network
        }
    
    def least_squares(self, u, y, order=2):
        """最小二乘法系统辨识"""
        n = len(y)
        phi = np.zeros((n - order, 2 * order))
        
        for i in range(order, n):
            phi[i - order, :order] = -y[i-1:i-order-1:-1]
            phi[i - order, order:] = u[i-1:i-order-1:-1]
        
        theta = np.linalg.lstsq(phi, y[order:], rcond=None)[0]
        num = theta[order:]
        den = np.concatenate(([1], theta[:order]))
        
        return signal.TransferFunction(num, den, dt=0.01)
    
    def maximum_likelihood(self, u, y, order=2):
        """最大似然法系统辨识"""
        # 简化实现 - 实际应使用更复杂的算法
        return self.least_squares(u, y, order)
    
    def subspace_method(self, u, y, order=2):
        """子空间法系统辨识"""
        # 简化实现
        return self.least_squares(u, y, order)
    
    def neural_network(self, u, y, order=2):
        """神经网络系统辨识"""
        n = len(y)
        X = np.zeros((n - order, 2 * order))
        
        for i in range(order, n):
            X[i - order, :order] = y[i-1:i-order-1:-1]
            X[i - order, order:] = u[i-1:i-order-1:-1]
        
        y_target = y[order:]
        
        model = Pipeline([
            ('scaler', StandardScaler()),
            ('mlp', MLPRegressor(hidden_layer_sizes=(20, 10), max_iter=1000))
        ])
        
        model.fit(X, y_target)
        
        # 转换为传递函数形式（简化处理）
        return self.least_squares(u, y, order)


class RobustnessAnalysis:
    """鲁棒性分析模块"""
    def __init__(self):
        pass
    
    def sensitivity_analysis(self, system, param_ranges, n_points=10):
        """灵敏度分析"""
        results = {}
        param_names = list(param_ranges.keys())
        
        for param_name in param_names:
            param_values = np.linspace(param_ranges[param_name][0], 
                                      param_ranges[param_name][1], n_points)
            results[param_name] = {
                'values': param_values,
                'performance': np.zeros(n_points)
            }
            
            for i, value in enumerate(param_values):
                # 修改系统参数
                modified_system = self._modify_system_param(system, param_name, value)
                
                # 评估性能
                performance = self._evaluate_performance(modified_system)
                results[param_name]['performance'][i] = performance
        
        return results
    
    def monte_carlo_analysis(self, system, param_distributions, n_samples=100):
        """蒙特卡洛分析"""
        results = {
            'performance': np.zeros(n_samples),
            'parameters': {}
        }
        
        param_names = list(param_distributions.keys())
        for name in param_names:
            results['parameters'][name] = np.zeros(n_samples)
        
        for i in range(n_samples):
            # 采样参数
            sampled_params = {}
            for name, dist in param_distributions.items():
                if dist['type'] == 'uniform':
                    value = np.random.uniform(dist['min'], dist['max'])
                elif dist['type'] == 'normal':
                    value = np.random.normal(dist['mean'], dist['std'])
                sampled_params[name] = value
                results['parameters'][name][i] = value
            
            # 修改系统
            modified_system = system
            for name, value in sampled_params.items():
                modified_system = self._modify_system_param(modified_system, name, value)
            
            # 评估性能
            performance = self._evaluate_performance(modified_system)
            results['performance'][i] = performance
        
        return results
    
    def _modify_system_param(self, system, param_name, value):
        """修改系统参数（简化实现）"""
        # 在实际应用中，这里需要根据系统类型修改特定参数
        return system
    
    def _evaluate_performance(self, system):
        """评估系统性能（简化实现）"""
        # 在实际应用中，这里需要定义适当的性能指标
        return np.random.rand()


class DataLogger:
    """数据记录模块"""
    def __init__(self):
        self.data = {
            'time': [],
            'setpoint': [],
            'output': [],
            'control': [],
            'parameters': []
        }
        self.filename = None
    
    def log(self, time, setpoint, output, control, parameters=None):
        """记录数据"""
        self.data['time'].append(time)
        self.data['setpoint'].append(setpoint)
        self.data['output'].append(output)
        self.data['control'].append(control)
        self.data['parameters'].append(parameters or {})
    
    def save(self, filename=None):
        """保存数据到文件"""
        if filename:
            self.filename = filename
        
        if not self.filename:
            return False
        
        try:
            # 转换为DataFrame以便保存
            df_data = {
                'time': self.data['time'],
                'setpoint': self.data['setpoint'],
                'output': self.data['output'],
                'control': self.data['control']
            }
            
            # 添加参数数据
            for i, params in enumerate(self.data['parameters']):
                for key, value in params.items():
                    if key not in df_data:
                        df_data[key] = [None] * len(self.data['time'])
                    df_data[key][i] = value
            
            df = pd.DataFrame(df_data)
            df.to_csv(self.filename, index=False)
            return True
        except Exception as e:
            print(f"保存数据时出错: {e}")
            return False
    
    def load(self, filename):
        """从文件加载数据"""
        try:
            df = pd.read_csv(filename)
            self.data = {
                'time': df['time'].tolist(),
                'setpoint': df['setpoint'].tolist(),
                'output': df['output'].tolist(),
                'control': df['control'].tolist(),
                'parameters': []
            }
            
            # 提取参数数据
            param_columns = [col for col in df.columns if col not in ['time', 'setpoint', 'output', 'control']]
            for _, row in df.iterrows():
                params = {}
                for col in param_columns:
                    if not pd.isna(row[col]):
                        params[col] = row[col]
                self.data['parameters'].append(params)
            
            self.filename = filename
            return True
        except Exception as e:
            print(f"加载数据时出错: {e}")
            return False
    
    def clear(self):
        """清除数据"""
        self.data = {
            'time': [],
            'setpoint': [],
            'output': [],
            'control': [],
            'parameters': []
        }
        self.filename = None


class AdvancedPIDController:
    """高级PID控制器，包含多种变体和自适应功能"""
    def __init__(self, Kp, Ki, Kd, setpoint=0, output_limits=(None, None), 
                 sample_time=0.01, variant='standard', adaptive_params=None):
        self.Kp = Kp
        self.Ki = Ki
        self.Kd = Kd
        self.setpoint = setpoint
        self.output_limits = output_limits
        self.sample_time = sample_time
        self.variant = variant  # 'standard', 'series', 'parallel', 'ideal'
        self.adaptive_params = adaptive_params or {}
        
        self.reset()
    
    def reset(self):
        """重置控制器状态"""
        self._integral = 0
        self._prev_error = 0
        self._prev_measurement = 0
        self._last_time = None
        self._last_output = None
        
        # 自适应参数
        self.adaptive_gain = 1.0
        self.error_history = []
        self.performance_index = 0
    
    def update_adaptive_gain(self, error):
        """根据性能指标自适应调整增益"""
        if not self.adaptive_params:
            return
        
        # 记录误差历史
        self.error_history.append(abs(error))
        if len(self.error_history) > self.adaptive_params.get('window_size', 100):
            self.error_history.pop(0)
        
        # 计算性能指标 (IAE)
        self.performance_index = sum(self.error_history)
        
        # 简单的自适应规则
        if self.performance_index > self.adaptive_params.get('threshold_high', 10.0):
            self.adaptive_gain *= self.adaptive_params.get('gain_increase', 1.05)
        elif self.performance_index < self.adaptive_params.get('threshold_low', 2.0):
            self.adaptive_gain *= self.adaptive_params.get('gain_decrease', 0.95)
        
        # 限制增益范围
        self.adaptive_gain = np.clip(
            self.adaptive_gain, 
            self.adaptive_params.get('min_gain', 0.1),
            self.adaptive_params.get('max_gain', 10.0)
        )
    
    def __call__(self, measurement, dt=None):
        """计算控制输出"""
        error = self.setpoint - measurement
        
        # 自适应增益调整
        if self.adaptive_params:
            self.update_adaptive_gain(error)
            Kp = self.Kp * self.adaptive_gain
            Ki = self.Ki * self.adaptive_gain
            Kd = self.Kd * self.adaptive_gain
        else:
            Kp, Ki, Kd = self.Kp, self.Ki, self.Kd
        
        if dt is None:
            dt = self.sample_time
        
        # 防止除零错误
        if dt <= 0:
            dt = self.sample_time
        
        # 不同PID变体的实现
        if self.variant == 'standard':
            # 标准PID形式
            p_term = Kp * error
            self._integral += Ki * error * dt
            i_term = self._integral
            d_term = Kd * (error - self._prev_error) / dt
            
        elif self.variant == 'series':
            # 串联PID形式
            p_term = Kp * error
            self._integral += Ki * p_term * dt
            i_term = self._integral
            d_term = Kd * (p_term - self._prev_error) / dt
            
        elif self.variant == 'parallel':
            # 并联PID形式
            p_term = Kp * error
            self._integral += Ki * error * dt
            i_term = self._integral
            d_term = Kd * (measurement - self._prev_measurement) / dt
            
        elif self.variant == 'ideal':
            # 理想PID形式
            p_term = Kp * error
            self._integral += error * dt
            i_term = Ki * self._integral
            d_term = Kd * (error - self._prev_error) / dt
        
        # 计算总输出
        output = p_term + i_term + d_term
        
        # 应用输出限制
        if self.output_limits[0] is not None:
            output = max(self.output_limits[0], output)
            # 抗积分饱和
            if output == self.output_limits[0] and i_term < 0:
                self._integral -= i_term
        if self.output_limits[1] is not None:
            output = min(self.output_limits[1], output)
            # 抗积分饱和
            if output == self.output_limits[1] and i_term > 0:
                self._integral -= i_term
        
        # 更新状态
        self._prev_error = error
        self._prev_measurement = measurement
        
        return output


class ModelPredictiveController:
    """模型预测控制器（简化实现）"""
    def __init__(self, model, horizon=10, control_weight=0.1, output_limits=(None, None)):
        self.model = model  # 系统模型
        self.horizon = horizon  # 预测时域
        self.control_weight = control_weight  # 控制权重
        self.output_limits = output_limits  # 输出限制
        self.setpoint = 0
        self.reset()
    
    def reset(self):
        """重置控制器状态"""
        self._past_controls = []
        self._past_outputs = []
    
    def predict(self, current_output, future_controls):
        """预测系统输出"""
        # 简化实现 - 使用系统模型进行预测
        predictions = [current_output]
        
        for u in future_controls:
            # 使用系统模型进行一步预测
            next_output = self.model(predictions[-1], u)
            predictions.append(next_output)
        
        return predictions[1:]  # 返回未来的预测
    
    def optimize_controls(self, current_output):
        """优化控制序列"""
        # 初始化控制序列
        controls = np.zeros(self.horizon)
        
        # 定义目标函数
        def objective(future_controls):
            predictions = self.predict(current_output, future_controls)
            
            # 计算跟踪误差
            error = sum((p - self.setpoint)**2 for p in predictions)
            
            # 计算控制代价
            control_cost = self.control_weight * sum(u**2 for u in future_controls)
            
            return error + control_cost
        
        # 优化控制序列
        result = minimize(objective, controls, method='L-BFGS-B')
        
        return result.x[0]  # 返回第一个控制量
    
    def __call__(self, measurement, dt=0.01):
        """计算控制输出"""
        # 优化控制序列
        control = self.optimize_controls(measurement)
        
        # 应用输出限制
        if self.output_limits[0] is not None:
            control = max(self.output_limits[0], control)
        if self.output_limits[1] is not None:
            control = min(self.output_limits[1], control)
        
        return control


class NeuralNetworkPIDController:
    """神经网络PID控制器"""
    def __init__(self, Kp, Ki, Kd, setpoint=0, output_limits=(None, None)):
        self.Kp = Kp
        self.Ki = Ki
        self.Kd = Kd
        self.setpoint = setpoint
        self.output_limits = output_limits
        
        # 创建神经网络
        self.create_neural_network()
        
        self.reset()
    
    def create_neural_network(self):
        """创建神经网络模型"""
        self.nn_model = Pipeline([
            ('scaler', StandardScaler()),
            ('mlp', MLPRegressor(
                hidden_layer_sizes=(10, 5),
                activation='tanh',
                max_iter=1000,
                random_state=42
            ))
        ])
        
        # 初始训练数据
        self.X_train = np.zeros((1, 3))  # error, integral, derivative
        self.y_train = np.zeros(1)       # control output
    
    def reset(self):
        """重置控制器状态"""
        self._integral = 0
        self._prev_error = 0
        self._training_data = []
    
    def update_neural_network(self, error, integral, derivative, output):
        """更新神经网络训练数据"""
        # 收集训练数据
        self._training_data.append([error, integral, derivative, output])
        
        # 定期重新训练神经网络
        if len(self._training_data) % 100 == 0:
            data = np.array(self._training_data)
            X = data[:, :3]
            y = data[:, 3]
            
            if len(X) > 10:  # 确保有足够的数据
                self.nn_model.fit(X, y)
    
    def __call__(self, measurement, dt=0.01):
        """计算控制输出"""
        error = self.setpoint - measurement
        derivative = (error - self._prev_error) / max(dt, 1e-10)  # 防止除零错误
        self._integral += error * dt
        
        # 使用神经网络调整PID参数或直接计算输出
        if len(self._training_data) > 10:
            # 使用神经网络计算输出
            X = np.array([[error, self._integral, derivative]])
            output = self.nn_model.predict(X)[0]
        else:
            # 使用常规PID
            p_term = self.Kp * error
            i_term = self.Ki * self._integral
            d_term = self.Kd * derivative
            output = p_term + i_term + d_term
        
        # 应用输出限制
        if self.output_limits[0] is not None:
            output = max(self.output_limits[0], output)
        if self.output_limits[1] is not None:
            output = min(self.output_limits[1], output)
        
        # 更新神经网络
        self.update_neural_network(error, self._integral, derivative, output)
        
        # 更新状态
        self._prev_error = error
        
        return output


class ReinforcementLearningController:
    """强化学习控制器（简化实现）"""
    def __init__(self, state_size=3, action_size=1, output_limits=(None, None)):
        self.state_size = state_size
        self.action_size = action_size
        self.output_limits = output_limits
        self.setpoint = 0
        
        # Q-learning参数
        self.learning_rate = 0.1
        self.discount_factor = 0.95
        self.epsilon = 1.0
        self.epsilon_min = 0.01
        self.epsilon_decay = 0.995
        
        # 创建Q表
        self.q_table = np.zeros((10, 10, 10, 3))  # 简化状态空间
        
        self.reset()
    
    def reset(self):
        """重置控制器状态"""
        self._integral = 0
        self._prev_error = 0
        self._state = (0, 0, 0)
    
    def discretize_state(self, error, integral, derivative):
        """将连续状态离散化"""
        # 简化实现
        e_idx = min(9, max(0, int((error + 5) / 10 * 10)))
        i_idx = min(9, max(0, int((integral + 5) / 10 * 10)))
        d_idx = min(9, max(0, int((derivative + 5) / 10 * 10)))
        
        return (e_idx, i_idx, d_idx)
    
    def choose_action(self, state):
        """选择动作（ε-贪婪策略）"""
        if np.random.rand() <= self.epsilon:
            # 探索：随机选择动作
            return np.random.choice([0, 1, 2])  # 0:减少控制, 1:保持, 2:增加控制
        else:
            # 利用：选择最优动作
            return np.argmax(self.q_table[state])
    
    def update_q_value(self, state, action, reward, next_state):
        """更新Q值"""
        old_value = self.q_table[state][action]
        next_max = np.max(self.q_table[next_state])
        
        # Q-learning更新公式
        new_value = old_value + self.learning_rate * (reward + self.discount_factor * next_max - old_value)
        self.q_table[state][action] = new_value
    
    def get_reward(self, error, prev_error):
        """计算奖励"""
        # 误差减小给予正奖励，误差增大给予负奖励
        if abs(error) < abs(prev_error):
            return 1.0
        else:
            return -1.0
    
    def __call__(self, measurement, dt=0.01):
        """计算控制输出"""
        error = self.setpoint - measurement
        derivative = (error - self._prev_error) / max(dt, 1e-10)  # 防止除零错误
        self._integral += error * dt
        
        # 离散化当前状态
        state = self.discretize_state(error, self._integral, derivative)
        
        # 选择动作
        action = self.choose_action(state)
        
        # 根据动作调整控制输出
        if action == 0:  # 减少控制
            control_change = -0.1
        elif action == 1:  # 保持
            control_change = 0
        else:  # 增加控制
            control_change = 0.1
        
        # 计算控制输出（简化实现）
        output = 0.5 * error + 0.3 * self._integral + 0.2 * derivative + control_change
        
        # 应用输出限制
        if self.output_limits[0] is not None:
            output = max(self.output_limits[0], output)
        if self.output_limits[1] is not None:
            output = min(self.output_limits[1], output)
        
        # 计算奖励
        reward = self.get_reward(error, self._prev_error)
        
        # 更新Q值
        next_state = self.discretize_state(error, self._integral, derivative)
        self.update_q_value(state, action, reward, next_state)
        
        # 衰减ε
        self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)
        
        # 更新状态
        self._prev_error = error
        
        return output


class MimoSystem:
    """多输入多输出系统"""
    def __init__(self, system_type="2x2", params=None):
        self.system_type = system_type
        self.params = params or {}
        
        # 定义系统模型
        if system_type == "2x2":
            # 二阶耦合系统
            self.A = np.array([[-2, 1], [1, -3]])
            self.B = np.array([[1, 0], [0, 1]])
            self.C = np.array([[1, 0], [0, 1]])
            self.D = np.array([[0, 0], [0, 0]])
        elif system_type == "3x3":
            # 三阶耦合系统
            self.A = np.array([[-2, 1, 0], [1, -3, 1], [0, 1, -2]])
            self.B = np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1]])
            self.C = np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1]])
            self.D = np.array([[0, 0, 0], [0, 0, 0], [0, 0, 0]])
        else:
            raise ValueError("Unsupported system type")
    
    def state_space_model(self, x, t, u):
        """状态空间模型"""
        return np.dot(self.A, x) + np.dot(self.B, u)
    
    def simulate(self, u, t, x0=None):
        """模拟系统响应"""
        n = len(t)
        m = self.B.shape[1]  # 输入数量
        p = self.C.shape[0]  # 输出数量
        
        if x0 is None:
            x0 = np.zeros(self.A.shape[0])
        
        # 确保u是适当形状
        if isinstance(u, (int, float)):
            u = np.full((n, m), u)
        elif len(u.shape) == 1:
            u = u.reshape(-1, 1)
            if u.shape[0] != n:
                u = np.tile(u, (1, n)).T
        
        # 模拟系统
        x = np.zeros((n, len(x0)))
        y = np.zeros((n, p))
        
        x[0, :] = x0
        y[0, :] = np.dot(self.C, x0) + np.dot(self.D, u[0, :])
        
        for i in range(1, n):
            dt = t[i] - t[i-1]
            dx = self.state_space_model(x[i-1, :], t[i-1], u[i-1, :])
            x[i, :] = x[i-1, :] + dx * dt
            y[i, :] = np.dot(self.C, x[i, :]) + np.dot(self.D, u[i, :])
        
        return y


class OptimizationThread(QThread):
    """参数优化线程"""
    progress = pyqtSignal(int)
    finished = pyqtSignal(dict)
    
    def __init__(self, system, controller_type, optimization_method, bounds, 
                 setpoint, simulation_time, sample_time):
        super().__init__()
        self.system = system
        self.controller_type = controller_type
        self.optimization_method = optimization_method
        self.bounds = bounds
        self.setpoint = setpoint
        self.simulation_time = simulation_time
        self.sample_time = sample_time
        self.t = np.arange(0, simulation_time, sample_time)
        self.progress_value = 0  # 初始化progress_value
    
    def run(self):
        """运行优化"""
        # 定义目标函数
        def objective(params):
            try:
                Kp, Ki, Kd = params
                
                # 创建控制器
                if self.controller_type == "PID":
                    controller = AdvancedPIDController(Kp, Ki, Kd, setpoint=self.setpoint)
                else:
                    controller = AdvancedPIDController(Kp, Ki, Kd, setpoint=self.setpoint)
                
                # 模拟系统
                y = np.zeros(len(self.t))
                u = np.zeros(len(self.t))
                measurement = 0
                
                for i, t_i in enumerate(self.t):
                    u[i] = controller(measurement)
                    # 简化系统模拟
                    measurement = self.system(measurement, t_i, u[i])
                    y[i] = measurement
                
                # 计算性能指标 (IAE)
                error = np.abs(self.setpoint - y)
                iae = np.trapz(error, self.t)
                
                return iae
            except Exception as e:
                # 如果出现数值错误，返回一个很大的值
                print(f"优化过程中出现数值错误: {e}")
                return float('inf')
        
        # 运行优化
        if self.optimization_method == "Nelder-Mead":
            result = minimize(
                objective, 
                x0=[(b[0] + b[1])/2 for b in self.bounds],
                method='Nelder-Mead',
                bounds=self.bounds,
                options={'maxiter': 50},
                callback=self.optimization_callback
            )
        elif self.optimization_method == "BFGS":
            result = minimize(
                objective,
                x0=[(b[0] + b[1])/2 for b in self.bounds],
                method='L-BFGS-B',
                bounds=self.bounds,
                options={'maxiter': 50},
                callback=self.optimization_callback
            )
        elif self.optimization_method == "Genetic":
            # 简化实现 - 实际应使用遗传算法库
            best_params = None
            best_value = float('inf')
            
            # 简单的网格搜索
            n_steps = 10
            Kp_range = np.linspace(self.bounds[0][0], self.bounds[0][1], n_steps)
            Ki_range = np.linspace(self.bounds[1][0], self.bounds[1][1], n_steps)
            Kd_range = np.linspace(self.bounds[2][0], self.bounds[2][1], n_steps)
            
            total_iterations = n_steps ** 3
            iteration = 0
            
            for Kp in Kp_range:
                for Ki in Ki_range:
                    for Kd in Kd_range:
                        value = objective([Kp, Ki, Kd])
                        if value < best_value:
                            best_value = value
                            best_params = [Kp, Ki, Kd]
                        
                        iteration += 1
                        progress = int(100 * iteration / total_iterations)
                        self.progress.emit(progress)
            
            result = type('obj', (object,), {
                'x': best_params,
                'fun': best_value,
                'success': True
            })()
        
        # 发送结果
        self.finished.emit({
            'Kp': result.x[0],
            'Ki': result.x[1],
            'Kd': result.x[2],
            'performance': result.fun
        })
    
    def optimization_callback(self, xk):
        """优化进度回调"""
        # 简化实现 - 实际应根据优化方法计算进度
        self.progress_value += 5
        self.progress.emit(min(100, self.progress_value))


class MplCanvas(FigureCanvas):
    """Matplotlib画布"""
    def __init__(self, parent=None, width=5, height=4, dpi=100, projection=None):
        if projection:
            self.fig = Figure(figsize=(width, height), dpi=dpi)
            self.axes = self.fig.add_subplot(111, projection=projection)
        else:
            self.fig = Figure(figsize=(width, height), dpi=dpi)
            self.axes = self.fig.add_subplot(111)
            
        super().__init__(self.fig)
        self.setParent(parent)
        
        # 设置样式
        if hasattr(self.axes, 'grid'):
            self.axes.grid(True, linestyle='--', alpha=0.7)
        self.fig.tight_layout()

class RealTimePlot(MplCanvas):
    """实时绘图组件"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.data_x = []
        self.data_y = []
        self.data_setpoint = []
        self.data_control = []
        
        # 创建第二个Y轴
        self.axes_right = self.axes.twinx()
        
        self.line_y, = self.axes.plot([], [], 'b-', label='输出')
        self.line_setpoint, = self.axes.plot([], [], 'r--', label='设定值')
        self.line_control, = self.axes_right.plot([], [], 'g-', alpha=0.5, label='控制信号')
        
        # 添加图例
        self.axes.legend(loc='upper left')
        self.axes_right.legend(loc='upper right')
        self.axes_right.set_ylabel('控制信号')
        
    def update_plot(self, t, y, setpoint, control):
        self.data_x = t
        self.data_y = y
        self.data_setpoint = [setpoint] * len(t)
        self.data_control = control
        
        self.line_y.set_data(self.data_x, self.data_y)
        self.line_setpoint.set_data(self.data_x, self.data_setpoint)
        self.line_control.set_data(self.data_x, self.data_control)
        
        self.axes.relim()
        self.axes.autoscale_view()
        self.axes_right.relim()
        self.axes_right.autoscale_view()
        self.draw()

class ThreeDPlot(MplCanvas):
    """3D绘图组件"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs, projection='3d')
        
    def plot_surface(self, X, Y, Z, title="参数优化曲面", xlabel="Kp", ylabel="Ki", zlabel="性能指标"):
        self.axes.clear()
        surf = self.axes.plot_surface(X, Y, Z, cmap=cm.coolwarm, linewidth=0, antialiased=True)
        self.axes.set_xlabel(xlabel)
        self.axes.set_ylabel(ylabel)
        self.axes.set_zlabel(zlabel)
        self.axes.set_title(title)
        self.fig.colorbar(surf, ax=self.axes, shrink=0.5, aspect=5)
        self.draw()

class BodePlot(MplCanvas):
    """波特图组件"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
    def plot_bode(self, system, title="波特图"):
        self.axes.clear()
        
        # 计算频率响应
        if hasattr(system, 'num') and hasattr(system, 'den'):
            # 连续系统传递函数
            w, mag, phase = signal.bode(system)
        else:
            # 默认频率范围
            w = np.logspace(-2, 2, 1000)
            mag = np.zeros_like(w)
            phase = np.zeros_like(w)
        
        # 幅频特性
        self.axes.semilogx(w, mag, 'b-')
        self.axes.set_xlabel('频率 [rad/s]')
        self.axes.set_ylabel('幅度 [dB]', color='b')
        self.axes.tick_params(axis='y', labelcolor='b')
        self.axes.grid(True, which='both', linestyle='--', alpha=0.7)
        
        # 相频特性
        ax2 = self.axes.twinx()
        ax2.semilogx(w, phase, 'r-')
        ax2.set_ylabel('相位 [度]', color='r')
        ax2.tick_params(axis='y', labelcolor='r')
        
        self.axes.set_title(title)
        self.fig.tight_layout()
        self.draw()

class NyquistPlot(MplCanvas):
    """奈奎斯特图组件"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
    def plot_nyquist(self, system, title="奈奎斯特图"):
        self.axes.clear()
        
        # 计算频率响应
        if hasattr(system, 'num') and hasattr(system, 'den'):
            w = np.logspace(-2, 2, 1000)
            w, H = signal.freqresp(system, w=w)
            real = H.real
            imag = H.imag
        else:
            real = np.array([0])
            imag = np.array([0])
        
        # 绘制奈奎斯特图
        self.axes.plot(real, imag, 'b-')
        self.axes.plot(real, -imag, 'b--')
        self.axes.axhline(0, color='black', linestyle='-', alpha=0.3)
        self.axes.axvline(0, color='black', linestyle='-', alpha=0.3)
        
        # 添加(-1,0)点
        self.axes.plot(-1, 0, 'ro', markersize=8)
        
        self.axes.set_xlabel('实部')
        self.axes.set_ylabel('虚部')
        self.axes.set_title(title)
        self.axes.grid(True, linestyle='--', alpha=0.7)
        self.axes.axis('equal')
        self.fig.tight_layout()
        self.draw()

class RootLocusPlot(MplCanvas):
    """根轨迹图组件"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
    def plot_root_locus(self, system, title="根轨迹"):
        self.axes.clear()
        
        # 计算根轨迹
        if hasattr(system, 'num') and hasattr(system, 'den'):
            k = np.logspace(-2, 2, 1000)
            r = np.zeros((len(k), len(system.den) - 1), dtype=complex)
            
            for i, ki in enumerate(k):
                closed_loop_den = system.den + ki * system.num
                roots = np.roots(closed_loop_den)
                r[i, :] = roots
            
            # 绘制根轨迹
            for i in range(r.shape[1]):
                self.axes.plot(r[:, i].real, r[:, i].imag, 'b-', linewidth=1)
            
            # 添加极点和零点
            poles = np.roots(system.den)
            zeros = np.roots(system.num) if len(system.num) > 1 else np.array([])
            
            self.axes.plot(poles.real, poles.imag, 'rx', markersize=8, markeredgewidth=2)
            if len(zeros) > 0:
                self.axes.plot(zeros.real, zeros.imag, 'ro', markersize=8, fillstyle='none', markeredgewidth=2)
        
        self.axes.axhline(0, color='black', linestyle='-', alpha=0.3)
        self.axes.axvline(0, color='black', linestyle='-', alpha=0.3)
        self.axes.set_xlabel('实部')
        self.axes.set_ylabel('虚部')
        self.axes.set_title(title)
        self.axes.grid(True, linestyle='--', alpha=0.7)
        self.fig.tight_layout()
        self.draw()

class SensitivityPlot(MplCanvas):
    """灵敏度分析图组件"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
    def plot_sensitivity(self, results, title="灵敏度分析"):
        self.axes.clear()
        
        param_names = list(results.keys())
        n_params = len(param_names)
        
        colors = ['b', 'g', 'r', 'c', 'm', 'y', 'k']
        
        for i, param_name in enumerate(param_names):
            color = colors[i % len(colors)]
            self.axes.plot(results[param_name]['values'], 
                          results[param_name]['performance'], 
                          color+'-o', label=param_name)
        
        self.axes.set_xlabel('参数值')
        self.axes.set_ylabel('性能指标')
        self.axes.set_title(title)
        self.axes.legend()
        self.axes.grid(True, linestyle='--', alpha=0.7)
        self.fig.tight_layout()
        self.draw()

class MonteCarloPlot(MplCanvas):
    """蒙特卡洛分析图组件"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
    def plot_monte_carlo(self, results, param_name=None, title="蒙特卡洛分析"):
        self.axes.clear()
        
        if param_name:
            # 绘制特定参数与性能的关系
            self.axes.scatter(results['parameters'][param_name], 
                             results['performance'], alpha=0.5)
            self.axes.set_xlabel(param_name)
            self.axes.set_ylabel('性能指标')
        else:
            # 绘制性能分布直方图
            self.axes.hist(results['performance'], bins=20, alpha=0.7)
            self.axes.set_xlabel('性能指标')
            self.axes.set_ylabel('频次')
        
        self.axes.set_title(title)
        self.axes.grid(True, linestyle='--', alpha=0.7)
        self.fig.tight_layout()
        self.draw()


class SystemIdentificationDialog(QDialog):
    """系统辨识对话框"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("系统辨识")
        self.setModal(True)
        self.setup_ui()
        
        # 初始化系统辨识模块
        self.sys_id = SystemIdentification()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # 数据加载部分
        data_group = QGroupBox("数据加载")
        data_layout = QVBoxLayout(data_group)
        
        load_layout = QHBoxLayout()
        self.data_file_edit = QLineEdit()
        self.data_file_edit.setReadOnly(True)
        load_layout.addWidget(self.data_file_edit)
        
        self.browse_button = QPushButton("浏览...")
        self.browse_button.clicked.connect(self.browse_data_file)
        load_layout.addWidget(self.browse_button)
        
        data_layout.addLayout(load_layout)
        
        # 数据显示
        self.data_table = QTableWidget()
        self.data_table.setColumnCount(3)
        self.data_table.setHorizontalHeaderLabels(["时间", "输入", "输出"])
        data_layout.addWidget(self.data_table)
        
        layout.addWidget(data_group)
        
        # 辨识参数部分
        param_group = QGroupBox("辨识参数")
        param_layout = QFormLayout(param_group)
        
        self.method_combo = QComboBox()
        self.method_combo.addItems(["最小二乘法", "最大似然法", "子空间法", "神经网络"])
        param_layout.addRow("辨识方法:", self.method_combo)
        
        self.order_spin = QSpinBox()
        self.order_spin.setRange(1, 10)
        self.order_spin.setValue(2)
        param_layout.addRow("模型阶次:", self.order_spin)
        
        layout.addWidget(param_group)
        
        # 按钮部分
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
    def browse_data_file(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, "打开数据文件", "", "CSV文件 (*.csv);;所有文件 (*)"
        )
        if filename:
            self.data_file_edit.setText(filename)
            self.load_data(filename)
    
    def load_data(self, filename):
        try:
            df = pd.read_csv(filename)
            self.data_table.setRowCount(min(100, len(df)))  # 只显示前100行
            
            for i, row in df.iterrows():
                if i >= 100:
                    break
                
                self.data_table.setItem(i, 0, QTableWidgetItem(str(row.get('time', ''))))
                self.data_table.setItem(i, 1, QTableWidgetItem(str(row.get('input', ''))))
                self.data_table.setItem(i, 2, QTableWidgetItem(str(row.get('output', ''))))
        
        except Exception as e:
            QMessageBox.warning(self, "错误", f"加载数据失败: {str(e)}")
    
    def get_identifaction_result(self):
        """获取辨识结果"""
        filename = self.data_file_edit.text()
        if not filename:
            return None
        
        try:
            df = pd.read_csv(filename)
            u = df['input'].values
            y = df['output'].values
            
            method = self.method_combo.currentText()
            order = self.order_spin.value()
            
            # 执行系统辨识
            tf = self.sys_id.methods[method](u, y, order)
            
            return {
                'transfer_function': tf,
                'method': method,
                'order': order
            }
        
        except Exception as e:
            QMessageBox.warning(self, "错误", f"系统辨识失败: {str(e)}")
            return None


class MainWindow(QMainWindow):
    """主窗口"""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("高级PID控制系统")
        self.setGeometry(100, 100, 1400, 900)
        
        # 初始化数据记录器
        self.data_logger = DataLogger()
        
        # 初始化设置
        self.settings = QSettings("MyCompany", "PIDControlSystem")
        
        # 创建中央部件和主布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        # 创建左侧控制面板
        control_panel = QWidget()
        control_layout = QVBoxLayout(control_panel)
        splitter.addWidget(control_panel)
        
        # 创建右侧图表区域
        self.tab_widget = QTabWidget()
        splitter.addWidget(self.tab_widget)
        
        # 设置分割器比例
        splitter.setSizes([400, 1000])
        
        # 初始化控制面板
        self.init_control_panel(control_layout)
        
        # 初始化图表
        self.init_plots()
        
        # 初始化系统
        self.system = self.create_system("一阶惯性环节")
        self.controller = AdvancedPIDController(1.0, 0.1, 0.01, setpoint=1.0)
        
        # 初始化仿真参数
        self.simulation_time = 10.0
        self.sample_time = 0.01
        self.t = np.arange(0, self.simulation_time, self.sample_time)
        self.y = np.zeros_like(self.t)
        self.u = np.zeros_like(self.t)
        
        # 启动定时器用于实时仿真
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_simulation)
        self.simulation_index = 0
        
        # 加载设置
        self.load_settings()
    
    def init_control_panel(self, layout):
        """初始化控制面板"""
        # 系统选择
        system_group = QGroupBox("系统选择")
        system_layout = QVBoxLayout(system_group)
        
        self.system_combo = QComboBox()
        self.system_combo.addItems(["一阶惯性环节", "二阶振荡环节", "积分环节", "时滞系统", "非线性系统", "MIMO系统"])
        system_layout.addWidget(QLabel("系统类型:"))
        system_layout.addWidget(self.system_combo)
        
        # 系统参数
        system_params_layout = QGridLayout()
        system_params_layout.addWidget(QLabel("增益:"), 0, 0)
        self.gain_spin = QDoubleSpinBox()
        self.gain_spin.setRange(0.1, 10.0)
        self.gain_spin.setValue(1.0)
        system_params_layout.addWidget(self.gain_spin, 0, 1)
        
        system_params_layout.addWidget(QLabel("时间常数:"), 1, 0)
        self.time_const_spin = QDoubleSpinBox()
        self.time_const_spin.setRange(0.1, 10.0)
        self.time_const_spin.setValue(1.0)
        system_params_layout.addWidget(self.time_const_spin, 1, 1)
        
        system_params_layout.addWidget(QLabel("阻尼比:"), 2, 0)
        self.damping_spin = QDoubleSpinBox()
        self.damping_spin.setRange(0.1, 2.0)
        self.damping_spin.setValue(0.7)
        system_params_layout.addWidget(self.damping_spin, 2, 1)
        
        system_params_layout.addWidget(QLabel("时滞:"), 3, 0)
        self.delay_spin = QDoubleSpinBox()
        self.delay_spin.setRange(0.0, 5.0)
        self.delay_spin.setValue(0.5)
        system_params_layout.addWidget(self.delay_spin, 3, 1)
        
        system_layout.addLayout(system_params_layout)
        layout.addWidget(system_group)
        
        # 控制器参数
        controller_group = QGroupBox("控制器参数")
        controller_layout = QGridLayout(controller_group)
        
        controller_layout.addWidget(QLabel("控制器类型:"), 0, 0)
        self.controller_combo = QComboBox()
        self.controller_combo.addItems(["PID", "自适应PID", "神经网络PID", "模型预测控制", "强化学习控制"])
        controller_layout.addWidget(self.controller_combo, 0, 1)
        
        controller_layout.addWidget(QLabel("Kp:"), 1, 0)
        self.kp_spin = QDoubleSpinBox()
        self.kp_spin.setRange(0.0, 100.0)
        self.kp_spin.setValue(1.0)
        controller_layout.addWidget(self.kp_spin, 1, 1)
        
        controller_layout.addWidget(QLabel("Ki:"), 2, 0)
        self.ki_spin = QDoubleSpinBox()
        self.ki_spin.setRange(0.0, 100.0)
        self.ki_spin.setValue(0.1)
        controller_layout.addWidget(self.ki_spin, 2, 1)
        
        controller_layout.addWidget(QLabel("Kd:"), 3, 0)
        self.kd_spin = QDoubleSpinBox()
        self.kd_spin.setRange(0.0, 100.0)
        self.kd_spin.setValue(0.01)
        controller_layout.addWidget(self.kd_spin, 3, 1)
        
        controller_layout.addWidget(QLabel("设定值:"), 4, 0)
        self.setpoint_spin = QDoubleSpinBox()
        self.setpoint_spin.setRange(-10.0, 10.0)
        self.setpoint_spin.setValue(1.0)
        controller_layout.addWidget(self.setpoint_spin, 4, 1)
        
        # PID变体选择
        controller_layout.addWidget(QLabel("PID变体:"), 5, 0)
        self.pid_variant_combo = QComboBox()
        self.pid_variant_combo.addItems(["standard", "series", "parallel", "ideal"])
        controller_layout.addWidget(self.pid_variant_combo, 5, 1)
        
        layout.addWidget(controller_group)
        
        # 仿真参数
        sim_group = QGroupBox("仿真参数")
        sim_layout = QGridLayout(sim_group)
        
        sim_layout.addWidget(QLabel("仿真时间:"), 0, 0)
        self.sim_time_spin = QDoubleSpinBox()
        self.sim_time_spin.setRange(1.0, 100.0)
        self.sim_time_spin.setValue(10.0)
        self.sim_time_spin.valueChanged.connect(self.update_simulation_time)
        sim_layout.addWidget(self.sim_time_spin, 0, 1)
        
        sim_layout.addWidget(QLabel("采样时间:"), 1, 0)
        self.sample_time_spin = QDoubleSpinBox()
        self.sample_time_spin.setRange(0.001, 1.0)
        self.sample_time_spin.setValue(0.01)
        self.sample_time_spin.setSingleStep(0.001)
        self.sample_time_spin.valueChanged.connect(self.update_sample_time)
        sim_layout.addWidget(self.sample_time_spin, 1, 1)
        
        layout.addWidget(sim_group)
        
        # 控制按钮
        button_layout = QHBoxLayout()
        self.start_button = QPushButton("开始")
        self.start_button.clicked.connect(self.start_simulation)
        button_layout.addWidget(self.start_button)
        
        self.stop_button = QPushButton("停止")
        self.stop_button.clicked.connect(self.stop_simulation)
        button_layout.addWidget(self.stop_button)
        
        self.reset_button = QPushButton("重置")
        self.reset_button.clicked.connect(self.reset_simulation)
        button_layout.addWidget(self.reset_button)
        
        layout.addLayout(button_layout)
        
        # 高级功能按钮
        advanced_layout = QHBoxLayout()
        self.optimize_button = QPushButton("参数优化")
        self.optimize_button.clicked.connect(self.optimize_parameters)
        advanced_layout.addWidget(self.optimize_button)
        
        self.identify_button = QPushButton("系统辨识")
        self.identify_button.clicked.connect(self.identify_system)
        advanced_layout.addWidget(self.identify_button)
        
        layout.addLayout(advanced_layout)
        
        # 数据记录按钮
        data_layout = QHBoxLayout()
        self.save_data_button = QPushButton("保存数据")
        self.save_data_button.clicked.connect(self.save_data)
        data_layout.addWidget(self.save_data_button)
        
        self.load_data_button = QPushButton("加载数据")
        self.load_data_button.clicked.connect(self.load_data)
        data_layout.addWidget(self.load_data_button)
        
        layout.addLayout(data_layout)
        
        # 鲁棒性分析按钮
        robustness_layout = QHBoxLayout()
        self.sensitivity_button = QPushButton("灵敏度分析")
        self.sensitivity_button.clicked.connect(self.sensitivity_analysis)
        robustness_layout.addWidget(self.sensitivity_button)
        
        self.monte_carlo_button = QPushButton("蒙特卡洛分析")
        self.monte_carlo_button.clicked.connect(self.monte_carlo_analysis)
        robustness_layout.addWidget(self.monte_carlo_button)
        
        layout.addLayout(robustness_layout)
        
        # 添加弹簧项使控件顶部对齐
        layout.addStretch()
    
    def init_plots(self):
        """初始化图表"""
        # 实时响应图
        self.realtime_plot = RealTimePlot(self, width=8, height=6, dpi=100)
        self.tab_widget.addTab(self.realtime_plot, "实时响应")
        
        # 波特图
        self.bode_plot = BodePlot(self, width=8, height=6, dpi=100)
        self.tab_widget.addTab(self.bode_plot, "波特图")
        
        # 奈奎斯特图
        self.nyquist_plot = NyquistPlot(self, width=8, height=6, dpi=100)
        self.tab_widget.addTab(self.nyquist_plot, "奈奎斯特图")
        
        # 根轨迹图
        self.root_locus_plot = RootLocusPlot(self, width=8, height=6, dpi=100)
        self.tab_widget.addTab(self.root_locus_plot, "根轨迹")
        
        # 3D参数优化图
        self.three_d_plot = ThreeDPlot(self, width=8, height=6, dpi=100)
        self.tab_widget.addTab(self.three_d_plot, "参数优化")
        
        # 灵敏度分析图
        self.sensitivity_plot = SensitivityPlot(self, width=8, height=6, dpi=100)
        self.tab_widget.addTab(self.sensitivity_plot, "灵敏度分析")
        
        # 蒙特卡洛分析图
        self.monte_carlo_plot = MonteCarloPlot(self, width=8, height=6, dpi=100)
        self.tab_widget.addTab(self.monte_carlo_plot, "蒙特卡洛分析")
    
    def create_system(self, system_type):
        """创建系统模型"""
        if system_type == "一阶惯性环节":
            gain = self.gain_spin.value()
            time_const = self.time_const_spin.value()
            return lambda y, t, u: (gain * u - y) / time_const
        elif system_type == "二阶振荡环节":
            gain = self.gain_spin.value()
            damping = self.damping_spin.value()
            omega_n = 1.0 / self.time_const_spin.value()
            return lambda y, t, u: [y[1], gain * u - 2 * damping * omega_n * y[1] - omega_n**2 * y[0]]
        elif system_type == "积分环节":
            gain = self.gain_spin.value()
            return lambda y, t, u: gain * u
        elif system_type == "时滞系统":
            gain = self.gain_spin.value()
            time_const = self.time_const_spin.value()
            delay = self.delay_spin.value()
            # 简化实现，实际时滞系统需要更复杂的处理
            return lambda y, t, u: (gain * u - y) / time_const
        elif system_type == "非线性系统":
            # 一个简单的非线性系统示例
            return lambda y, t, u: (1.0 * u - y - 0.1 * y**3) / 1.0
        elif system_type == "MIMO系统":
            # 返回一个MIMO系统对象
            return MimoSystem("2x2")
        else:
            # 默认一阶系统
            return lambda y, t, u: (1.0 * u - y) / 1.0
    
    def create_controller(self, controller_type):
        """创建控制器"""
        Kp = self.kp_spin.value()
        Ki = self.ki_spin.value()
        Kd = self.kd_spin.value()
        setpoint = self.setpoint_spin.value()
        variant = self.pid_variant_combo.currentText()
        
        if controller_type == "PID":
            return AdvancedPIDController(Kp, Ki, Kd, setpoint=setpoint, variant=variant)
        elif controller_type == "自适应PID":
            adaptive_params = {
                'window_size': 100,
                'threshold_high': 10.0,
                'threshold_low': 2.0,
                'gain_increase': 1.05,
                'gain_decrease': 0.95,
                'min_gain': 0.1,
                'max_gain': 10.0
            }
            return AdvancedPIDController(Kp, Ki, Kd, setpoint=setpoint, adaptive_params=adaptive_params, variant=variant)
        elif controller_type == "神经网络PID":
            return NeuralNetworkPIDController(Kp, Ki, Kd, setpoint=setpoint)
        elif controller_type == "模型预测控制":
            # 简化实现 - 使用一阶系统作为预测模型
            model = lambda y, u: y + (1.0 * u - y) / 1.0 * 0.01
            return ModelPredictiveController(model, horizon=10, control_weight=0.1)
        elif controller_type == "强化学习控制":
            return ReinforcementLearningController(state_size=3, action_size=1)
        else:
            return AdvancedPIDController(Kp, Ki, Kd, setpoint=setpoint, variant=variant)
    
    def update_simulation_time(self):
        """更新仿真时间"""
        self.simulation_time = self.sim_time_spin.value()
        self.t = np.arange(0, self.simulation_time, self.sample_time)
        self.y = np.zeros_like(self.t)
        self.u = np.zeros_like(self.t)
    
    def update_sample_time(self):
        """更新采样时间"""
        self.sample_time = self.sample_time_spin.value()
        self.t = np.arange(0, self.simulation_time, self.sample_time)
        self.y = np.zeros_like(self.t)
        self.u = np.zeros_like(self.t)
        self.timer.setInterval(int(self.sample_time * 1000))
    
    def start_simulation(self):
        """开始仿真"""
        # 更新系统和控制器
        self.system = self.create_system(self.system_combo.currentText())
        self.controller = self.create_controller(self.controller_combo.currentText())
        
        # 重置仿真数据
        self.t = np.arange(0, self.simulation_time, self.sample_time)
        self.y = np.zeros_like(self.t)
        self.u = np.zeros_like(self.t)
        self.simulation_index = 0
        
        # 重置数据记录器
        self.data_logger.clear()
        
        # 启动定时器
        self.timer.start(int(self.sample_time * 1000))
    
    def stop_simulation(self):
        """停止仿真"""
        self.timer.stop()
    
    def reset_simulation(self):
        """重置仿真"""
        self.timer.stop()
        self.y = np.zeros_like(self.t)
        self.u = np.zeros_like(self.t)
        self.simulation_index = 0
        self.realtime_plot.update_plot(self.t[:1], self.y[:1], self.setpoint_spin.value(), self.u[:1])
    
    def update_simulation(self):
        """更新仿真"""
        if self.simulation_index < len(self.t):
            # 计算控制输出
            measurement = self.y[self.simulation_index]
            control = self.controller(measurement)
            self.u[self.simulation_index] = control
            
            # 更新系统状态
            if self.simulation_index > 0:
                dt = self.t[self.simulation_index] - self.t[self.simulation_index-1]
                if callable(self.system):
                    # 一阶系统
                    if self.system_combo.currentText() in ["一阶惯性环节", "积分环节", "时滞系统", "非线性系统"]:
                        self.y[self.simulation_index] = self.y[self.simulation_index-1] + self.system(
                            self.y[self.simulation_index-1], 
                            self.t[self.simulation_index-1], 
                            control
                        ) * dt
                    # 二阶系统
                    elif self.system_combo.currentText() == "二阶振荡环节":
                        # 使用欧拉法积分
                        # 对于二阶系统，我们需要维护两个状态变量：位置和速度
                        if self.simulation_index == 1:
                            # 初始化状态
                            self.state = np.array([self.y[0], 0])  # [位置, 速度]
                        
                        # 计算导数
                        dy = self.system(self.state, self.t[self.simulation_index-1], control)
                        # 更新状态
                        self.state = self.state + np.array(dy) * dt
                        # 更新输出
                        self.y[self.simulation_index] = self.state[0]
                    # MIMO系统
                    elif self.system_combo.currentText() == "MIMO系统":
                        # 简化实现，只使用第一个输出
                        if self.simulation_index == 1:
                            self.mimo_state = np.zeros(self.system.A.shape[0])
                        
                        # 计算MIMO系统响应
                        u_vec = np.array([control, 0])  # 简化处理，只使用第一个输入
                        dx = self.system.state_space_model(self.mimo_state, self.t[self.simulation_index-1], u_vec)
                        self.mimo_state = self.mimo_state + dx * dt
                        y_vec = np.dot(self.system.C, self.mimo_state) + np.dot(self.system.D, u_vec)
                        self.y[self.simulation_index] = y_vec[0]  # 只使用第一个输出
            
            # 记录数据
            params = {
                'Kp': self.kp_spin.value(),
                'Ki': self.ki_spin.value(),
                'Kd': self.kd_spin.value()
            }
            self.data_logger.log(
                self.t[self.simulation_index],
                self.setpoint_spin.value(),
                self.y[self.simulation_index],
                self.u[self.simulation_index],
                params
            )
            
            # 更新图表
            if self.simulation_index % 10 == 0:  # 每10个点更新一次图表
                self.realtime_plot.update_plot(
                    self.t[:self.simulation_index+1], 
                    self.y[:self.simulation_index+1], 
                    self.setpoint_spin.value(), 
                    self.u[:self.simulation_index+1]
                )
            
            self.simulation_index += 1
        else:
            self.timer.stop()
    
    def optimize_parameters(self):
        """参数优化"""
        # 创建优化线程
        bounds = [(0.1, 10.0), (0.01, 5.0), (0.001, 2.0)]  # Kp, Ki, Kd的范围
        
        self.optimization_thread = OptimizationThread(
            system=self.system,
            controller_type=self.controller_combo.currentText(),
            optimization_method="Nelder-Mead",
            bounds=bounds,
            setpoint=self.setpoint_spin.value(),
            simulation_time=self.simulation_time,
            sample_time=self.sample_time
        )
        
        # 连接信号和槽
        self.optimization_thread.progress.connect(self.update_optimization_progress)
        self.optimization_thread.finished.connect(self.optimization_finished)
        
        # 显示进度对话框
        self.progress_dialog = QProgressDialog("优化进行中...", "取消", 0, 100, self)
        self.progress_dialog.setWindowTitle("参数优化")
        self.progress_dialog.canceled.connect(self.optimization_thread.terminate)
        self.progress_dialog.show()
        
        # 启动优化线程
        self.optimization_thread.start()
    
    def update_optimization_progress(self, value):
        """更新优化进度"""
        self.progress_dialog.setValue(value)
    
    def optimization_finished(self, result):
        """优化完成"""
        self.progress_dialog.close()
        
        # 更新控制器参数
        self.kp_spin.setValue(result['Kp'])
        self.ki_spin.setValue(result['Ki'])
        self.kd_spin.setValue(result['Kd'])
        
        # 显示优化结果
        QMessageBox.information(self, "优化完成", 
                               f"优化结果:\nKp = {result['Kp']:.4f}\nKi = {result['Ki']:.4f}\nKd = {result['Kd']:.4f}\n性能指标 = {result['performance']:.4f}")
    
    def identify_system(self):
        """系统辨识"""
        dialog = SystemIdentificationDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            result = dialog.get_identifaction_result()
            if result:
                # 显示辨识结果
                tf = result['transfer_function']
                message = f"系统辨识完成!\n方法: {result['method']}\n阶次: {result['order']}\n\n传递函数:\n"
                
                # 显示传递函数
                num_str = "[" + ", ".join([f"{x:.4f}" for x in tf.num]) + "]"
                den_str = "[" + ", ".join([f"{x:.4f}" for x in tf.den]) + "]"
                message += f"分子: {num_str}\n分母: {den_str}"
                
                QMessageBox.information(self, "系统辨识结果", message)
                
                # 更新波特图
                self.bode_plot.plot_bode(tf, "辨识系统波特图")
    
    def save_data(self):
        """保存数据"""
        filename, _ = QFileDialog.getSaveFileName(
            self, "保存数据", "", "CSV文件 (*.csv);;所有文件 (*)"
        )
        if filename:
            if self.data_logger.save(filename):
                QMessageBox.information(self, "成功", "数据保存成功!")
            else:
                QMessageBox.warning(self, "错误", "数据保存失败!")
    
    def load_data(self):
        """加载数据"""
        filename, _ = QFileDialog.getOpenFileName(
            self, "加载数据", "", "CSV文件 (*.csv);;所有文件 (*)"
        )
        if filename:
            if self.data_logger.load(filename):
                # 更新图表
                self.realtime_plot.update_plot(
                    self.data_logger.data['time'],
                    self.data_logger.data['output'],
                    self.data_logger.data['setpoint'][0] if self.data_logger.data['setpoint'] else 0,
                    self.data_logger.data['control']
                )
                QMessageBox.information(self, "成功", "数据加载成功!")
            else:
                QMessageBox.warning(self, "错误", "数据加载失败!")
    
    def sensitivity_analysis(self):
        """灵敏度分析"""
        # 创建鲁棒性分析模块
        robustness = RobustnessAnalysis()
        
        # 定义参数范围
        param_ranges = {
            'gain': (0.5, 2.0),
            'time_constant': (0.5, 2.0),
            'damping': (0.3, 1.5)
        }
        
        # 执行灵敏度分析
        results = robustness.sensitivity_analysis(self.system, param_ranges)
        
        # 显示结果
        self.sensitivity_plot.plot_sensitivity(results, "灵敏度分析")
    
    def monte_carlo_analysis(self):
        """蒙特卡洛分析"""
        # 创建鲁棒性分析模块
        robustness = RobustnessAnalysis()
        
        # 定义参数分布
        param_distributions = {
            'gain': {'type': 'normal', 'mean': 1.0, 'std': 0.2},
            'time_constant': {'type': 'normal', 'mean': 1.0, 'std': 0.2},
            'damping': {'type': 'uniform', 'min': 0.5, 'max': 1.5}
        }
        
        # 执行蒙特卡洛分析
        results = robustness.monte_carlo_analysis(self.system, param_distributions, n_samples=100)
        
        # 显示结果
        self.monte_carlo_plot.plot_monte_carlo(results, None, "蒙特卡洛分析")
    
    def load_settings(self):
        """加载设置"""
        # 加载窗口几何信息
        geometry = self.settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
        
        # 加载系统参数
        self.gain_spin.setValue(float(self.settings.value("gain", 1.0)))
        self.time_const_spin.setValue(float(self.settings.value("time_constant", 1.0)))
        self.damping_spin.setValue(float(self.settings.value("damping", 0.7)))
        self.delay_spin.setValue(float(self.settings.value("delay", 0.5)))
        
        # 加载控制器参数
        self.kp_spin.setValue(float(self.settings.value("Kp", 1.0)))
        self.ki_spin.setValue(float(self.settings.value("Ki", 0.1)))
        self.kd_spin.setValue(float(self.settings.value("Kd", 0.01)))
        self.setpoint_spin.setValue(float(self.settings.value("setpoint", 1.0)))
        
        # 加载仿真参数
        self.sim_time_spin.setValue(float(self.settings.value("sim_time", 10.0)))
        self.sample_time_spin.setValue(float(self.settings.value("sample_time", 0.01)))
    
    def save_settings(self):
        """保存设置"""
        # 保存窗口几何信息
        self.settings.setValue("geometry", self.saveGeometry())
        
        # 保存系统参数
        self.settings.setValue("gain", self.gain_spin.value())
        self.settings.setValue("time_constant", self.time_const_spin.value())
        self.settings.setValue("damping", self.damping_spin.value())
        self.settings.setValue("delay", self.delay_spin.value())
        
        # 保存控制器参数
        self.settings.setValue("Kp", self.kp_spin.value())
        self.settings.setValue("Ki", self.ki_spin.value())
        self.settings.setValue("Kd", self.kd_spin.value())
        self.settings.setValue("setpoint", self.setpoint_spin.value())
        
        # 保存仿真参数
        self.settings.setValue("sim_time", self.sim_time_spin.value())
        self.settings.setValue("sample_time", self.sample_time_spin.value())
    
    def closeEvent(self, event):
        """关闭事件"""
        self.save_settings()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    # 创建主窗口并显示
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec_())