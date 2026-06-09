import sys
import tempfile
from reportlab.lib import colors
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from scipy import signal, optimize, interpolate
from scipy.optimize import differential_evolution, minimize
from PyQt5.QtWidgets import (QApplication, QDialog, QMainWindow, QProgressDialog, QWidget, QVBoxLayout, QHBoxLayout, 
                             QTabWidget, QGroupBox, QPushButton, QLabel, QLineEdit, 
                             QComboBox, QSlider, QDoubleSpinBox, QCheckBox, QSplitter,
                             QFileDialog, QMessageBox, QStatusBar, QTableWidget, 
                             QTableWidgetItem, QHeaderView, QGridLayout, QFormLayout,
                             QProgressBar, QSpinBox, QTextEdit, QSizePolicy)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
import control as ctrl
import pandas as pd
import pickle
import time
import json
import os
from collections import deque
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph, Spacer, Image

class PIDController:
    def __init__(self, Kp, Ki, Kd, dt, setpoint, output_limits=(-np.inf, np.inf), 
                 derivative_filter=True, filter_coeff=0.1, anti_windup=True):
        self.Kp = Kp
        self.Ki = Ki
        self.Kd = Kd
        self.dt = dt
        self.setpoint = setpoint
        self.output_limits = output_limits
        self.derivative_filter = derivative_filter
        self.filter_coeff = filter_coeff
        self.anti_windup = anti_windup
        
        # State variables
        self.integral = 0
        self.previous_error = 0
        self.previous_derivative = 0
        self.previous_output = 0
        self.output = 0
        self.time = 0
        
    def update(self, measurement):
        error = self.setpoint - measurement
        
        # Proportional term
        P = self.Kp * error
        
        # Integral term
        self.integral += error * self.dt
        I = self.Ki * self.integral
        
        # Derivative term (with filtering)
        derivative = (error - self.previous_error) / self.dt
        if self.derivative_filter:
            derivative = self.filter_coeff * derivative + (1 - self.filter_coeff) * self.previous_derivative
        D = self.Kd * derivative
        
        # Calculate output
        self.output = P + I + D
        
        # Apply output limits and anti-windup
        saturated = False
        if self.output > self.output_limits[1]:
            self.output = self.output_limits[1]
            saturated = True
        elif self.output < self.output_limits[0]:
            self.output = self.output_limits[0]
            saturated = True
        
        # Anti-windup: only integrate when not saturated
        if self.anti_windup and saturated:
            self.integral = self.integral - error * self.dt  
        
        # Update state
        self.previous_error = error
        self.previous_derivative = derivative
        self.time += self.dt
        
        return self.output
    
    def reset(self):
        """Reset controller state"""
        self.integral = 0
        self.previous_error = 0
        self.previous_derivative = 0
        self.previous_output = 0
        self.output = 0
        self.time = 0

class AdaptivePIDController(PIDController):
    def __init__(self, Kp, Ki, Kd, dt, setpoint, output_limits=(-np.inf, np.inf), 
                 derivative_filter=True, filter_coeff=0.1, anti_windup=True,
                 adaptation_rate=0.01):
        super().__init__(Kp, Ki, Kd, dt, setpoint, output_limits, 
                         derivative_filter, filter_coeff, anti_windup)
        self.adaptation_rate = adaptation_rate
        self.error_history = deque(maxlen=100)
        self.gain_history = []
        
    def update(self, measurement):
        error = self.setpoint - measurement
        self.error_history.append(error)
        
        # Simple gain scheduling based on error magnitude
        error_mag = abs(error)
        if error_mag > 1.0:
            # High error: increase proportional gain
            self.Kp = min(10.0, self.Kp * (1 + self.adaptation_rate))
        elif error_mag < 0.1:
            # Low error: reduce proportional gain to prevent oscillations
            self.Kp = max(0.1, self.Kp * (1 - self.adaptation_rate))
        
        # Call base class update
        output = super().update(measurement)
        
        # Record gain changes
        self.gain_history.append((self.time, self.Kp, self.Ki, self.Kd))
        
        return output

class SystemModel:
    def __init__(self, model_type="second_order", params=None, delay=0.0, noise_level=0.0):
        self.model_type = model_type
        self.delay = delay
        self.noise_level = noise_level
        self.delay_buffer = []
        self.max_delay_steps = 0
        self.state_history = []
        self.input_history = []
        
        if params is None:
            if model_type == "second_order":
                self.params = [1.0, 0.5, 0.2]  # [m, c, k]
            elif model_type == "first_order":
                self.params = [0.5, 0.1]  # [tau, K]
            elif model_type == "integrator":
                self.params = [0.1]  # [gain]
            elif model_type == "nonlinear":
                self.params = [1.0, 0.5, 0.2, 0.1]  # [m, c, k, nonlinearity]
            elif model_type == "transfer_function":
                self.params = [[1.0], [1.0, 0.5]]  # [num, den]
            elif model_type == "custom":
                self.params = {"A": 1.0, "B": 0.5, "C": 0.2}
        else:
            self.params = params
                
        # Initialize state based on model type
        self.reset()
        
    def reset(self):
        """Reset model state"""
        if self.model_type == "transfer_function":
            # Create transfer function and convert to state space
            num, den = self.params
            sys = ctrl.TransferFunction(num, den)
            sys_ss = ctrl.tf2ss(sys)
            self.A = sys_ss.A
            self.B = sys_ss.B
            self.C = sys_ss.C
            self.D = sys_ss.D
            # Initialize state based on state space dimension
            self.state = np.zeros(sys_ss.A.shape[0])
        elif self.model_type == "custom":
            # Custom model: use provided state initialization
            self.state = np.array(self.params.get("initial_state", [0.0, 0.0]))
        else:
            # For other models, keep the original 2D state
            self.state = np.zeros(2)
            
        # Clear history
        self.state_history = []
        self.input_history = []
        self.delay_buffer = []
        
    def update(self, u, dt):
        # Record input
        self.input_history.append(u)
        
        # Handle time delay
        if self.delay > 0:
            delay_steps = int(self.delay / dt)
            self.delay_buffer.append(u)
            if len(self.delay_buffer) > delay_steps:
                u = self.delay_buffer.pop(0)
            else:
                u = 0.0
        
        # Model-specific update logic
        if self.model_type == "second_order":
            # Second-order system: m*x'' + c*x' + k*x = u
            m, c, k = self.params
            dxdt = np.zeros_like(self.state)
            dxdt[0] = self.state[1]
            dxdt[1] = (u - c*self.state[1] - k*self.state[0]) / m
            self.state += dxdt * dt
            output = self.state[0]
            
        elif self.model_type == "first_order":
            # First-order system: tau*x' + x = K*u
            tau, K = self.params
            dxdt = (K*u - self.state[0]) / tau
            self.state[0] += dxdt * dt
            output = self.state[0]
            
        elif self.model_type == "integrator":
            # Integrator system: x' = K*u
            if isinstance(self.params, (list, tuple)):  # 检查是否是列表/元组
                K = self.params[0]
            else:  # 如果是单个值
                K = self.params
            self.state[0] += K * u * dt
            output = self.state[0]
            
        elif self.model_type == "nonlinear":
            # Nonlinear system: m*x'' + c*x' + k*x^3 = u
            m, c, k, nl = self.params
            dxdt = np.zeros_like(self.state)
            dxdt[0] = self.state[1]
            dxdt[1] = (u - c*self.state[1] - k*(self.state[0]**3)) / m
            self.state += dxdt * dt
            output = self.state[0]
            
        elif self.model_type == "transfer_function":
            # Update state using state-space matrices
            dx = self.A @ self.state + self.B * u
            # Convert to 1D array before updating state
            self.state += np.squeeze(dx * dt)
            output = float(self.C @ self.state + self.D * u)
            
        elif self.model_type == "custom":
            # Custom model: simple example with nonlinearity
            A, B, C = self.params["A"], self.params["B"], self.params["C"]
            dxdt = np.zeros_like(self.state)
            dxdt[0] = self.state[1]
            dxdt[1] = (u - B*self.state[1] - C*self.state[0] - 0.1*self.state[0]**3) / A
            self.state += dxdt * dt
            output = self.state[0]
            
        else:
            output = 0.0
        
        # Add measurement noise
        if self.noise_level > 0:
            output += np.random.normal(0, self.noise_level)
        
        # Record state
        self.state_history.append(output)
        
        return output

class SimulationEngine:
    def __init__(self):
        self.reset()
        
    def reset(self):
        self.time = []
        self.measurements = []
        self.setpoints = []
        self.outputs = []
        self.errors = []
        self.disturbances = []
        self.state = []
        self.system = None
        self.pid = None
        self.scenario = ""
        self.dt = 0.01
        self.current_time = 0
        self.running = False
        self.paused = False
        self.realtime = False
        self.adaptive_pid = False
        self.noise_level = 0.0
        self.control_mode = "PID"  # PID, Manual, Open-loop
        
    def configure(self, scenario, system_params, pid_params, dt=0.01, 
                 adaptive=False, noise_level=0.0, control_mode="PID"):
        self.reset()
        self.dt = dt
        self.scenario = scenario
        self.adaptive_pid = adaptive
        self.noise_level = noise_level
        self.control_mode = control_mode
        
        # Create system model
        self.system = SystemModel(model_type=system_params['type'], 
                                 params=system_params['params'],
                                 delay=system_params.get('delay', 0.0),
                                 noise_level=noise_level)
        
        # Create PID controller
        if adaptive:
            self.pid = AdaptivePIDController(
                Kp=pid_params['Kp'], 
                Ki=pid_params['Ki'], 
                Kd=pid_params['Kd'], 
                dt=dt,
                setpoint=0,
                output_limits=pid_params.get('output_limits', (-10, 10)),
                adaptation_rate=pid_params.get('adaptation_rate', 0.01)
            )
        else:
            self.pid = PIDController(
                Kp=pid_params['Kp'], 
                Ki=pid_params['Ki'], 
                Kd=pid_params['Kd'], 
                dt=dt,
                setpoint=0,
                output_limits=pid_params.get('output_limits', (-10, 10)),
                derivative_filter=pid_params.get('derivative_filter', True),
                filter_coeff=pid_params.get('filter_coeff', 0.1),
                anti_windup=pid_params.get('anti_windup', True)
            )
        
    def step(self):
        if not self.running or self.paused:
            return False
            
        # Generate setpoint
        setpoint = self._generate_setpoint(self.current_time)
        self.setpoints.append(setpoint)
        if self.pid:
            self.pid.setpoint = setpoint
        
        # Generate disturbance
        disturbance = self._generate_disturbance(self.current_time)
        self.disturbances.append(disturbance)
        
        # Get measurement
        if self.system:
            if self.control_mode == "Manual":
                # In manual mode, output is directly set
                measurement = self.system.update(self.manual_output, self.dt)
            else:
                measurement = self.system.update(self.pid.output, self.dt)
        else:
            measurement = 0
        self.measurements.append(measurement)
        
        # Update controller or use manual output
        if self.control_mode == "PID":
            u = self.pid.update(measurement)
            u += disturbance
            self.outputs.append(u)
        elif self.control_mode == "Manual":
            u = self.manual_output
            self.outputs.append(u)
        else:  # Open-loop
            u = self._generate_open_loop_input(self.current_time)
            self.outputs.append(u)
        
        # Record data
        self.errors.append(setpoint - measurement)
        self.time.append(self.current_time)
        
        # Increment time
        self.current_time += self.dt
        
        return True
    
    def run(self, duration=10):
        self.running = True
        self.paused = False
        while self.current_time < duration:
            if not self.step():
                break
        self.running = False
        
    def run_realtime(self, duration=10):
        self.running = True
        self.paused = False
        self.duration = duration
        self.realtime = True
        
    def pause(self):
        self.paused = True
        
    def resume(self):
        self.paused = False
        
    def set_manual_output(self, value):
        self.manual_output = value
        
    def _generate_setpoint(self, t):
        if self.scenario == "step_response":
            return 1.0 if t > 1.0 else 0.0
        elif self.scenario == "sinusoidal":
            return np.sin(0.5*t)
        elif self.scenario == "disturbance_rejection":
            return 0.5
        elif self.scenario == "varying_period":
            return 0.5*np.sin(0.2*t) if t < 5 else 0.5*np.sin(1.0*t)
        elif self.scenario == "ramp":
            return 0.2 * t if t < 5 else 1.0
        elif self.scenario == "square_wave":
            period = 2.0
            return 1.0 if (t % period) < period/2 else -1.0
        elif self.scenario == "multi_step":
            if t < 2: return 0.0
            elif t < 4: return 0.5
            elif t < 6: return 1.0
            elif t < 8: return 0.2
            else: return 0.8
        elif self.scenario == "random_setpoint":
            if t < 2: return 0.0
            elif t < 4: return 0.7
            elif t < 6: return 0.3
            elif t < 8: return 1.2
            else: return 0.4
        elif self.scenario == "chirp":
            return 0.5 * np.sin(0.1 * t**2)
        return 0.0
    
    def _generate_disturbance(self, t):
        if self.scenario == "disturbance_rejection":
            if 3.0 <= t < 3.5:
                return 0.8
            elif 6.0 <= t < 6.5:
                return -0.6
        elif self.scenario == "varying_period":
            return 0.1*np.random.randn()
        elif self.scenario == "random_disturbance":
            if t > 2.0:
                return 0.5 * np.random.randn()
        elif self.scenario == "impulse_disturbance":
            if 4.0 <= t < 4.1:
                return 1.0
        elif self.scenario == "step_disturbance":
            if t > 5.0:
                return 0.5
        return 0.0
    
    def _generate_open_loop_input(self, t):
        """Generate input for open-loop testing"""
        if t < 2.0:
            return 0.0
        elif t < 4.0:
            return 0.5
        elif t < 6.0:
            return 1.0
        elif t < 8.0:
            return 0.0
        else:
            return -0.5
    
    def calculate_performance_metrics(self):
        if not self.time:
            return {}
        
        if any(np.isnan(x) for x in self.measurements):
            return {'error': 'NaN detected in measurements'}
        # Convert to numpy arrays for calculations
        time = np.array(self.time)
        error = np.array(self.errors)
        output = np.array(self.outputs)
        
        # Calculate metrics
        metrics = {}
        
        # Rise time (10% to 90%)
        if self.scenario in ["step_response", "multi_step"]:
            try:
                target = self.setpoints[-1]  # Final setpoint
                idx_10 = np.where(self.measurements >= 0.1 * target)[0][0]
                idx_90 = np.where(self.measurements >= 0.9 * target)[0][0]
                metrics['rise_time'] = time[idx_90] - time[idx_10]
            except:
                metrics['rise_time'] = np.nan
        
        # Overshoot
        if self.scenario in ["step_response", "multi_step"]:
            try:
                max_val = np.max(self.measurements)
                target = self.setpoints[-1]  # Final setpoint
                metrics['overshoot'] = (max_val - target) / target * 100
            except:
                metrics['overshoot'] = np.nan
        
        # Settling time (within 2% of target)
        if self.scenario in ["step_response", "multi_step"]:
            try:
                target = self.setpoints[-1]  # Final setpoint
                settling_idx = np.where(np.abs(self.measurements - target) <= 0.02 * target)[0]
                if len(settling_idx) > 0:
                    metrics['settling_time'] = time[settling_idx[0]]
                else:
                    metrics['settling_time'] = np.nan
            except:
                metrics['settling_time'] = np.nan
        
        # Steady-state error
        if self.scenario in ["step_response", "disturbance_rejection", "multi_step"]:
            try:
                # Use last 10% of simulation
                start_idx = int(0.9 * len(time))
                metrics['steady_state_error'] = np.mean(np.abs(error[start_idx:]))
            except:
                metrics['steady_state_error'] = np.nan
        
        # ITAE (Integral of Time-weighted Absolute Error)
        metrics['ITAE'] = np.sum(time * np.abs(error)) * self.dt
        
        # IAE (Integral of Absolute Error)
        metrics['IAE'] = np.sum(np.abs(error)) * self.dt
        
        # ISE (Integral of Squared Error)
        metrics['ISE'] = np.sum(error**2) * self.dt
        
        # ITSE (Integral of Time-weighted Squared Error)
        metrics['ITSE'] = np.sum(time * error**2) * self.dt
        
        # Control effort
        metrics['control_effort'] = np.sum(np.abs(output)) * self.dt
        
        # Variation of control signal
        metrics['control_variation'] = np.sum(np.abs(np.diff(output))) / len(output)
        
        # RMSE (Root Mean Square Error)
        metrics['RMSE'] = np.sqrt(np.mean(error**2))
        
        # Stability metrics
        metrics['max_overshoot'] = np.max(np.abs(error))
        
        # Robustness metrics
        metrics['gain_margin'], metrics['phase_margin'] = self.calculate_stability_margins()
        
        for key in list(metrics.keys()):
            if np.isnan(metrics[key]) or np.isinf(metrics[key]):
                metrics[key] = 1e6  # 大惩罚值
                
        return metrics
    
    def calculate_stability_margins(self):
        """Estimate stability margins from time response"""
        gm, pm = np.nan, np.nan
        try:
            # Simple estimation based on overshoot and damping
            overshoot = self.calculate_performance_metrics().get('overshoot', 0)
            if not np.isnan(overshoot):
                damping = -np.log(overshoot/100) / np.sqrt(np.pi**2 + np.log(overshoot/100)**2)
                pm = 100 * damping  # Approximate phase margin
                gm = 1 / (2 * damping) if damping > 0 else np.inf  # Approximate gain margin
        except:
            pass
        return gm, pm

class SystemIdentifier:
    def __init__(self):
        self.models = {
            "First Order": self.identify_first_order,
            "Second Order": self.identify_second_order,
            "Integrator": self.identify_integrator,
            "Transfer Function": self.identify_transfer_function
        }
        
    def identify(self, time, input_data, output_data, model_type="First Order"):
        if model_type in self.models:
            return self.models[model_type](time, input_data, output_data)
        else:
            raise ValueError(f"Unknown model type: {model_type}")
    
    def identify_first_order(self, time, input_data, output_data):
        """Identify first-order system: tau*dy/dt + y = K*u"""
        # Find steady-state gain
        u_ss = np.mean(input_data[-100:])
        y_ss = np.mean(output_data[-100:])
        K = y_ss / u_ss if u_ss != 0 else 1.0
        
        # Find time constant using step response
        step_idx = np.argmax(np.abs(np.diff(input_data)) > 0.1)
        if step_idx == 0:
            step_idx = 1
            
        # Calculate time to reach 63.2% of steady-state
        target = 0.632 * y_ss
        tau_idx = np.argmax(output_data[step_idx:] >= target)
        if tau_idx == 0:
            tau_idx = len(output_data) - step_idx - 1
        tau = time[step_idx + tau_idx] - time[step_idx]
        
        return {"type": "first_order", "params": [tau, K]}
    
    def identify_second_order(self, time, input_data, output_data):
        """Identify second-order system: m*d²y/dt² + c*dy/dt + k*y = u"""
        # Find steady-state gain
        u_ss = np.mean(input_data[-100:])
        y_ss = np.mean(output_data[-100:])
        K = y_ss / u_ss if u_ss != 0 else 1.0
        
        # Find step response characteristics
        step_idx = np.argmax(np.abs(np.diff(input_data)) > 0.1)
        if step_idx == 0:
            step_idx = 1
            
        # Find overshoot and peak time
        peak_idx = np.argmax(output_data[step_idx:]) + step_idx
        overshoot = (output_data[peak_idx] - y_ss) / y_ss if y_ss != 0 else 0
        peak_time = time[peak_idx] - time[step_idx]
        
        # Calculate damping ratio and natural frequency
        if overshoot > 0:
            damping = -np.log(overshoot) / np.sqrt(np.pi**2 + np.log(overshoot)**2)
        else:
            damping = 1.0
            
        wn = np.pi / (peak_time * np.sqrt(1 - damping**2)) if damping < 1 else 4 / (damping * peak_time)
        
        # Convert to mass-spring-damper parameters
        m = 1.0
        k = m * wn**2
        c = 2 * damping * wn * m
        
        return {"type": "second_order", "params": [m, c, k]}
    
    def identify_integrator(self, time, input_data, output_data):
        """Identify integrator system: dy/dt = K*u"""
        # Calculate derivative of output
        dy = np.gradient(output_data, time)
        
        # Fit slope: dy = K * u
        A = np.vstack([input_data]).T
        K = np.linalg.lstsq(A, dy, rcond=None)[0][0]
        
        return {"type": "integrator", "params": [K]}
    
    def identify_transfer_function(self, time, input_data, output_data, order=2):
        """Identify transfer function using least squares"""
        # Create time vector
        dt = time[1] - time[0]
        
        # Create regression matrix
        n = len(time)
        A = np.zeros((n - order, 2 * order))
        
        # Fill with delayed inputs and outputs
        for i in range(order, n):
            # Output terms
            for j in range(1, order + 1):
                A[i - order, j - 1] = -output_data[i - j]
            # Input terms
            for j in range(order):
                A[i - order, order + j] = input_data[i - j]
        
        # Target vector (current output)
        b = output_data[order:]
        
        # Solve least squares problem
        theta = np.linalg.lstsq(A, b, rcond=None)[0]
        
        # Extract numerator and denominator
        den = [1.0] + list(theta[:order])
        num = list(theta[order:])
        
        return {"type": "transfer_function", "params": [num, den]}

class PlotCanvas(FigureCanvas):
    def __init__(self, parent=None, width=8, height=6, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)
        super().__init__(fig)
        self.setParent(parent)
        
        # Set up plot
        self.grid = True
        self.xlabel = 'Time (s)'
        self.ylabel = 'Value'
        self.title = "PID Simulation Results"
        
        # Initialize plot data
        self.lines = {}
        
    def plot(self, time, data_dict):
        """Plot multiple data series on the same axes"""
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        
        # Set title and labels
        ax.set_title(self.title)
        ax.set_xlabel(self.xlabel)
        ax.set_ylabel(self.ylabel)
        ax.grid(self.grid)
        
        # Plot each data series
        self.lines = {}
        for label, data in data_dict.items():
            line, = ax.plot(time, data, label=label)
            self.lines[label] = line
        
        # Add legend
        ax.legend()
        
        # Redraw
        self.draw()
    
    def plot_multiple(self, data_dict):
        """Plot multiple subplots"""
        self.figure.clear()
        
        n_plots = len(data_dict)
        if n_plots == 0:
            return
            
        # Create subplots
        axes = self.figure.subplots(n_plots, 1, sharex=True)
        if n_plots == 1:
            axes = [axes]
        
        for i, (title, data) in enumerate(data_dict.items()):
            ax = axes[i]
            time, values = data
            ax.plot(time, values)
            ax.set_title(title)
            ax.grid(True)
            ax.set_xlabel(self.xlabel if i == n_plots-1 else '')
        
        self.draw()
    
    def plot_bode(self, w, mag, phase, gm=None, pm=None, wg=None, wp=None):
        """Plot Bode diagram with stability margins"""
        self.figure.clear()
        ax1 = self.figure.add_subplot(211)
        ax2 = self.figure.add_subplot(212, sharex=ax1)
        
        ax1.semilogx(w, mag, 'b-', linewidth=2)
        ax1.set_title('Bode Plot')
        ax1.set_ylabel('Magnitude (dB)', color='b')
        ax1.grid(True)
        
        ax2.semilogx(w, phase, 'r-', linewidth=2)
        ax2.set_ylabel('Phase (deg)', color='r')
        ax2.set_xlabel('Frequency (rad/s)')
        ax2.grid(True)
        
        # Add gain and phase margins if provided
        if gm is not None and wg is not None:
            ax1.axvline(x=wg, color='g', linestyle='--')
            ax1.text(wg, min(mag), f"GM: {gm:.2f} dB", fontsize=10)
        if pm is not None and wp is not None:
            ax2.axvline(x=wp, color='m', linestyle='--')
            ax2.text(wp, min(phase), f"PM: {pm:.2f}°", fontsize=10)
        
        self.draw()
    
    def plot_nyquist(self, real, imag):
        """Plot Nyquist diagram"""
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        
        # Plot Nyquist curve
        ax.plot(real, imag, 'b')
        ax.plot(real, -imag, 'r')
        
        # Add unit circle
        theta = np.linspace(0, 2*np.pi, 100)
        ax.plot(np.cos(theta), np.sin(theta), 'k--')
        
        # Add (-1,0) point
        ax.plot(-1, 0, 'ro')
        
        ax.set_title('Nyquist Plot')
        ax.set_xlabel('Real')
        ax.set_ylabel('Imaginary')
        ax.grid(True)
        ax.axis('equal')
        
        self.draw()
    
    def plot_pole_zero(self, poles, zeros):
        """Plot pole-zero map"""
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        
        # Plot poles and zeros
        ax.plot(np.real(poles), np.imag(poles), 'x', markersize=10, label='Poles')
        if len(zeros) > 0:
            ax.plot(np.real(zeros), np.imag(zeros), 'o', markersize=10, fillstyle='none', label='Zeros')
        
        # Add unit circle and axes
        ax.axhline(y=0, color='k', linestyle='-', alpha=0.3)
        ax.axvline(x=0, color='k', linestyle='-', alpha=0.3)
        
        # Set plot limits
        all_points = np.concatenate([poles, zeros])
        if len(all_points) > 0:
            max_val = max(1, np.max(np.abs(all_points)))
            ax.set_xlim([-max_val*1.1, max_val*1.1])
            ax.set_ylim([-max_val*1.1, max_val*1.1])
        
        ax.set_title('Pole-Zero Map')
        ax.set_xlabel('Real')
        ax.set_ylabel('Imaginary')
        ax.grid(True)
        ax.legend()
        
        self.draw()
    
    def plot_control_diagram(self):
        """Plot control system block diagram"""
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        
        # Hide axes
        ax.set_axis_off()
        
        # Set diagram dimensions
        ax.set_xlim(0, 10)
        ax.set_ylim(0, 6)
        
        # Draw blocks
        pid_block = plt.Rectangle((3, 2.5), 2, 1, fill=False)
        system_block = plt.Rectangle((6, 2.5), 2, 1, fill=False)
        sum_block = plt.Circle((2, 3), 0.4, fill=False)
        
        # Add blocks to plot
        ax.add_patch(pid_block)
        ax.add_patch(system_block)
        ax.add_patch(sum_block)
        
        # Add text
        ax.text(2, 3, '+', ha='center', va='center', fontsize=12)
        ax.text(2.5, 3.4, '-', ha='center', va='center', fontsize=10)
        ax.text(4, 3, 'PID', ha='center', va='center', fontsize=10)
        ax.text(7, 3, 'System', ha='center', va='center', fontsize=10)
        ax.text(1, 3, 'Setpoint', ha='right', va='center', fontsize=9)
        ax.text(8.5, 3, 'Output', ha='left', va='center', fontsize=9)
        
        # Draw arrows
        arrow_props = dict(arrowstyle='->', lw=1.5)
        ax.annotate('', xy=(1.6, 3), xytext=(0.5, 3), arrowprops=arrow_props)
        ax.annotate('', xy=(2.4, 3), xytext=(1.6, 3), arrowprops=arrow_props)
        ax.annotate('', xy=(5, 3), xytext=(3, 3), arrowprops=arrow_props)
        ax.annotate('', xy=(8, 3), xytext=(6, 3), arrowprops=arrow_props)
        ax.annotate('', xy=(9, 3), xytext=(8, 3), arrowprops=arrow_props)
        ax.annotate('', xy=(7, 2), xytext=(7, 1), arrowprops=arrow_props)
        ax.annotate('', xy=(2, 2.6), xytext=(2, 1), arrowprops=arrow_props)
        ax.annotate('', xy=(7.5, 1), xytext=(2.5, 1), arrowprops=arrow_props)
        ax.annotate('', xy=(2.5, 1.4), xytext=(2.5, 1), arrowprops=arrow_props)
        
        # Add labels
        ax.text(7, 1.5, 'Measurement', ha='center', va='bottom', fontsize=8)
        ax.text(2.5, 1.5, 'Feedback', ha='center', va='bottom', fontsize=8)
        ax.text(5, 3.3, 'Control Signal', ha='center', va='bottom', fontsize=8)
        
        self.draw()
    
    def clear(self):
        self.figure.clear()
        self.draw()

class PIDTunerGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.sim_engine = SimulationEngine()
        self.system_identifier = SystemIdentifier()
        self.init_ui()
        self.init_defaults()
        
        # Setup real-time simulation timer
        self.sim_timer = QTimer()
        self.sim_timer.timeout.connect(self.realtime_step)
        self.realtime_update_interval = 50  # ms
        
        # Setup parameter update timer
        self.param_update_timer = QTimer()
        self.param_update_timer.timeout.connect(self.param_update_step)
        self.param_update_timer.start(100)  # Update every 100ms
        
        # Create results directory if not exists
        self.results_dir = "pid_tuner_results"
        if not os.path.exists(self.results_dir):
            os.makedirs(self.results_dir)
    
    def init_ui(self):
        self.setWindowTitle("Advanced PID Tuner Pro")
        self.setGeometry(100, 100, 1800, 1200)
        
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Create splitter for left and right panels
        splitter = QSplitter(Qt.Horizontal)
        
        # Left panel (control settings)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(5, 5, 5, 5)
        
        # System settings group
        system_group = QGroupBox("System Model")
        system_layout = QFormLayout()
        
        self.system_type_combo = QComboBox()
        self.system_type_combo.addItems(["second_order", "first_order", "integrator", 
                                       "nonlinear", "transfer_function", "custom"])
        self.system_type_combo.currentIndexChanged.connect(self.update_system_params_default)
        system_layout.addRow("System Type:", self.system_type_combo)
        
        self.system_params_edit = QLineEdit("1.0, 0.5, 0.2")
        system_layout.addRow("System Parameters:", self.system_params_edit)
        
        self.delay_spin = QDoubleSpinBox()
        self.delay_spin.setRange(0.0, 5.0)
        self.delay_spin.setSingleStep(0.1)
        self.delay_spin.setValue(0.0)
        system_layout.addRow("Time Delay (s):", self.delay_spin)
        
        self.noise_level_spin = QDoubleSpinBox()
        self.noise_level_spin.setRange(0.0, 1.0)
        self.noise_level_spin.setSingleStep(0.01)
        self.noise_level_spin.setValue(0.0)
        system_layout.addRow("Measurement Noise:", self.noise_level_spin)
        
        system_group.setLayout(system_layout)
        left_layout.addWidget(system_group)
        
        # PID settings group
        pid_group = QGroupBox("PID Controller")
        pid_layout = QGridLayout()
        
        # PID parameters
        self.kp_spin = QDoubleSpinBox()
        self.kp_spin.setRange(0.0, 20.0)
        self.kp_spin.setSingleStep(0.01)
        self.kp_spin.setValue(1.0)
        pid_layout.addWidget(QLabel("Proportional Gain (Kp):"), 0, 0)
        pid_layout.addWidget(self.kp_spin, 0, 1)
        
        self.ki_spin = QDoubleSpinBox()
        self.ki_spin.setRange(0.0, 10.0)
        self.ki_spin.setSingleStep(0.01)
        self.ki_spin.setValue(0.1)
        pid_layout.addWidget(QLabel("Integral Gain (Ki):"), 1, 0)
        pid_layout.addWidget(self.ki_spin, 1, 1)
        
        self.kd_spin = QDoubleSpinBox()
        self.kd_spin.setRange(0.0, 10.0)
        self.kd_spin.setSingleStep(0.01)
        self.kd_spin.setValue(0.5)
        pid_layout.addWidget(QLabel("Derivative Gain (Kd):"), 2, 0)
        pid_layout.addWidget(self.kd_spin, 2, 1)
        
        # PID options
        self.derivative_filter_cb = QCheckBox("Derivative Filter")
        self.derivative_filter_cb.setChecked(True)
        pid_layout.addWidget(self.derivative_filter_cb, 3, 0)
        
        self.filter_coeff_spin = QDoubleSpinBox()
        self.filter_coeff_spin.setRange(0.01, 1.0)
        self.filter_coeff_spin.setValue(0.1)
        pid_layout.addWidget(QLabel("Filter Coefficient:"), 3, 1)
        pid_layout.addWidget(self.filter_coeff_spin, 3, 2)
        
        self.anti_windup_cb = QCheckBox("Anti-Windup")
        self.anti_windup_cb.setChecked(True)
        pid_layout.addWidget(self.anti_windup_cb, 4, 0)
        
        # Output limits
        self.min_output_spin = QDoubleSpinBox()
        self.min_output_spin.setRange(-100.0, 0.0)
        self.min_output_spin.setValue(-10.0)
        pid_layout.addWidget(QLabel("Min Output:"), 5, 0)
        pid_layout.addWidget(self.min_output_spin, 5, 1)
        
        self.max_output_spin = QDoubleSpinBox()
        self.max_output_spin.setRange(0.0, 100.0)
        self.max_output_spin.setValue(10.0)
        pid_layout.addWidget(QLabel("Max Output:"), 5, 2)
        pid_layout.addWidget(self.max_output_spin, 5, 3)
        
        pid_group.setLayout(pid_layout)
        left_layout.addWidget(pid_group)
        
        # Scenario settings group
        scenario_group = QGroupBox("Simulation Scenario")
        scenario_layout = QFormLayout()
        
        self.scenario_combo = QComboBox()
        self.scenario_combo.addItems([
            "step_response", 
            "sinusoidal", 
            "disturbance_rejection", 
            "varying_period",
            "ramp",
            "square_wave",
            "multi_step",
            "random_setpoint",
            "chirp",
            "step_disturbance"
        ])
        scenario_layout.addRow("Scenario:", self.scenario_combo)
        
        self.control_mode_combo = QComboBox()
        self.control_mode_combo.addItems(["PID", "Manual", "Open-loop"])
        scenario_layout.addRow("Control Mode:", self.control_mode_combo)
        
        self.dt_spin = QDoubleSpinBox()
        self.dt_spin.setRange(0.001, 0.1)
        self.dt_spin.setSingleStep(0.001)
        self.dt_spin.setValue(0.01)
        scenario_layout.addRow("Time Step (s):", self.dt_spin)
        
        self.duration_spin = QDoubleSpinBox()
        self.duration_spin.setRange(1.0, 120.0)
        self.duration_spin.setSingleStep(1.0)
        self.duration_spin.setValue(10.0)
        scenario_layout.addRow("Duration (s):", self.duration_spin)
        
        self.adaptive_pid_cb = QCheckBox("Adaptive PID")
        scenario_layout.addWidget(self.adaptive_pid_cb)
        
        self.adaptation_rate_spin = QDoubleSpinBox()
        self.adaptation_rate_spin.setRange(0.001, 0.1)
        self.adaptation_rate_spin.setValue(0.01)
        scenario_layout.addRow("Adaptation Rate:", self.adaptation_rate_spin)
        
        scenario_group.setLayout(scenario_layout)
        left_layout.addWidget(scenario_group)
        
        # Real-time controls
        rt_group = QGroupBox("Simulation Controls")
        rt_layout = QGridLayout()
        
        self.run_button = QPushButton("Run Simulation")
        self.run_button.clicked.connect(self.run_simulation)
        rt_layout.addWidget(self.run_button, 0, 0)
        
        self.pause_button = QPushButton("Pause")
        self.pause_button.clicked.connect(self.pause_simulation)
        self.pause_button.setEnabled(False)
        rt_layout.addWidget(self.pause_button, 0, 1)
        
        self.reset_button = QPushButton("Reset")
        self.reset_button.clicked.connect(self.reset_simulation)
        rt_layout.addWidget(self.reset_button, 0, 2)
        
        self.realtime_update_cb = QCheckBox("Real-time Update")
        self.realtime_update_cb.setChecked(True)
        rt_layout.addWidget(self.realtime_update_cb, 1, 0)
        
        self.manual_output_slider = QSlider(Qt.Horizontal)
        self.manual_output_slider.setRange(-100, 100)
        self.manual_output_slider.setValue(0)
        self.manual_output_slider.valueChanged.connect(self.update_manual_output)
        rt_layout.addWidget(QLabel("Manual Output:"), 2, 0)
        rt_layout.addWidget(self.manual_output_slider, 2, 1, 1, 2)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        rt_layout.addWidget(self.progress_bar, 3, 0, 1, 3)
        
        rt_group.setLayout(rt_layout)
        left_layout.addWidget(rt_group)
        
        # Optimization buttons
        opt_group = QGroupBox("Optimization & Identification")
        opt_layout = QGridLayout()
        
        self.optimize_button = QPushButton("Optimize PID")
        self.optimize_button.clicked.connect(self.optimize_pid)
        opt_layout.addWidget(self.optimize_button, 0, 0)
        
        self.zn_button = QPushButton("Ziegler-Nichols")
        self.zn_button.clicked.connect(self.ziegler_nichols)
        opt_layout.addWidget(self.zn_button, 0, 1)
        
        self.identify_button = QPushButton("System Identification")
        self.identify_button.clicked.connect(self.identify_system)
        opt_layout.addWidget(self.identify_button, 1, 0)
        
        self.model_type_combo = QComboBox()
        self.model_type_combo.addItems(["First Order", "Second Order", "Integrator", "Transfer Function"])
        opt_layout.addWidget(QLabel("Model Type:"), 1, 1)
        opt_layout.addWidget(self.model_type_combo, 1, 2)
        
        self.robustness_button = QPushButton("Robustness Analysis")
        self.robustness_button.clicked.connect(self.robustness_analysis)
        opt_layout.addWidget(self.robustness_button, 2, 0)
        
        self.sensitivity_button = QPushButton("Sensitivity Analysis")
        self.sensitivity_button.clicked.connect(self.sensitivity_analysis)
        opt_layout.addWidget(self.sensitivity_button, 2, 1)
        
        opt_group.setLayout(opt_layout)
        left_layout.addWidget(opt_group)
        
        # Data buttons
        data_group = QGroupBox("Data Management")
        data_layout = QGridLayout()
        
        self.save_button = QPushButton("Save Results")
        self.save_button.clicked.connect(self.save_results)
        data_layout.addWidget(self.save_button, 0, 0)
        
        self.load_button = QPushButton("Load Results")
        self.load_button.clicked.connect(self.load_results)
        data_layout.addWidget(self.load_button, 0, 1)
        
        self.export_button = QPushButton("Export Plot")
        self.export_button.clicked.connect(self.export_plot)
        data_layout.addWidget(self.export_button, 0, 2)
        
        self.report_button = QPushButton("Generate Report")
        self.report_button.clicked.connect(self.generate_report)
        data_layout.addWidget(self.report_button, 1, 0)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(100)
        data_layout.addWidget(self.log_text, 2, 0, 1, 3)
        
        data_group.setLayout(data_layout)
        left_layout.addWidget(data_group)
        
        # Performance metrics table
        metrics_group = QGroupBox("Performance Metrics")
        metrics_layout = QVBoxLayout()
        
        self.metrics_table = QTableWidget()
        self.metrics_table.setColumnCount(2)
        self.metrics_table.setHorizontalHeaderLabels(["Metric", "Value"])
        self.metrics_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        metrics_layout.addWidget(self.metrics_table)
        
        metrics_group.setLayout(metrics_layout)
        left_layout.addWidget(metrics_group)
        
        # Add stretch to push everything up
        left_layout.addStretch()
        
        # Right panel (visualization)
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(5, 5, 5, 5)
        
        # Create tab widget for different visualizations
        self.tab_widget = QTabWidget()
        
        # Main plot tab
        self.plot_tab = QWidget()
        plot_layout = QVBoxLayout(self.plot_tab)
        
        self.main_plot = PlotCanvas(self, width=10, height=7)
        plot_layout.addWidget(self.main_plot)
        
        self.toolbar = NavigationToolbar(self.main_plot, self)
        plot_layout.addWidget(self.toolbar)
        
        self.tab_widget.addTab(self.plot_tab, "Time Response")
        
        # Multi-plot tab
        self.multiplot_tab = QWidget()
        multiplot_layout = QVBoxLayout(self.multiplot_tab)
        
        self.multiplot = PlotCanvas(self, width=10, height=7)
        multiplot_layout.addWidget(self.multiplot)
        
        self.tab_widget.addTab(self.multiplot_tab, "Multi-Plot")
        
        # Bode plot tab
        self.bode_tab = QWidget()
        bode_layout = QVBoxLayout(self.bode_tab)
        
        self.bode_plot = PlotCanvas(self, width=10, height=7)
        bode_layout.addWidget(self.bode_plot)
        
        self.tab_widget.addTab(self.bode_tab, "Frequency Response")
        
        # Nyquist plot tab
        self.nyquist_tab = QWidget()
        nyquist_layout = QVBoxLayout(self.nyquist_tab)
        
        self.nyquist_plot = PlotCanvas(self, width=10, height=7)
        nyquist_layout.addWidget(self.nyquist_plot)
        
        self.tab_widget.addTab(self.nyquist_tab, "Nyquist Plot")
        
        # Pole-zero plot tab
        self.polezero_tab = QWidget()
        polezero_layout = QVBoxLayout(self.polezero_tab)
        
        self.polezero_plot = PlotCanvas(self, width=10, height=7)
        polezero_layout.addWidget(self.polezero_plot)
        
        self.tab_widget.addTab(self.polezero_tab, "Pole-Zero Map")
        
        # Control diagram tab
        self.control_diagram_tab = QWidget()
        control_diagram_layout = QVBoxLayout(self.control_diagram_tab)
        
        self.control_diagram = PlotCanvas(self, width=10, height=7)
        control_diagram_layout.addWidget(self.control_diagram)
        
        self.tab_widget.addTab(self.control_diagram_tab, "Control Diagram")
        
        # Add tabs to right layout
        right_layout.addWidget(self.tab_widget)
        
        # Add panels to splitter
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([500, 1300])
        
        main_layout.addWidget(splitter)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
        
        # Initial control diagram
        self.control_diagram.plot_control_diagram()
    
    def init_defaults(self):
        # Set default parameters
        self.system_type_combo.setCurrentIndex(0)
        self.scenario_combo.setCurrentIndex(0)
        self.control_mode_combo.setCurrentIndex(0)
        self.model_type_combo.setCurrentIndex(1)
        
    def update_system_params_default(self):
        """Update parameter field when system type changes"""
        system_type = self.system_type_combo.currentText()
        if system_type == "second_order":
            self.system_params_edit.setText("1.0, 0.5, 0.2")
        elif system_type == "first_order":
            self.system_params_edit.setText("0.5, 0.1")
        elif system_type == "integrator":
            self.system_params_edit.setText("0.1")
        elif system_type == "nonlinear":
            self.system_params_edit.setText("1.0, 0.5, 0.2, 0.1")
        elif system_type == "transfer_function":
            self.system_params_edit.setText("[1.0], [1.0, 0.5]")
        elif system_type == "custom":
            self.system_params_edit.setText('{"A": 1.0, "B": 0.5, "C": 0.2, "initial_state": [0.0, 0.0]}')
    
    def update_manual_output(self, value):
        """Update manual output value from slider"""
        self.sim_engine.set_manual_output(value / 10.0)
    
    def run_simulation(self):
        # Get parameters from UI
        system_params = {
            'type': self.system_type_combo.currentText(),
            'params': self.parse_params(self.system_params_edit.text()),
            'delay': self.delay_spin.value()
        }
        
        pid_params = {
            'Kp': self.kp_spin.value(),
            'Ki': self.ki_spin.value(),
            'Kd': self.kd_spin.value(),
            'output_limits': (self.min_output_spin.value(), self.max_output_spin.value()),
            'derivative_filter': self.derivative_filter_cb.isChecked(),
            'filter_coeff': self.filter_coeff_spin.value(),
            'anti_windup': self.anti_windup_cb.isChecked(),
            'adaptation_rate': self.adaptation_rate_spin.value()
        }
        
        scenario = self.scenario_combo.currentText()
        control_mode = self.control_mode_combo.currentText()
        adaptive = self.adaptive_pid_cb.isChecked()
        noise_level = self.noise_level_spin.value()
        dt = self.dt_spin.value()
        duration = self.duration_spin.value()
        
        # Configure simulation
        self.sim_engine.configure(
            scenario, 
            system_params, 
            pid_params, 
            dt, 
            adaptive=adaptive,
            noise_level=noise_level,
            control_mode=control_mode
        )
        
        # Reset progress bar
        self.progress_bar.setValue(0)
        
        # Run simulation
        if self.realtime_update_cb.isChecked():
            # Run in real-time mode
            self.sim_engine.run_realtime(duration)
            self.sim_timer.start(self.realtime_update_interval)
            self.run_button.setText("Running...")
            self.pause_button.setEnabled(True)
        else:
            # Run full simulation at once
            self.sim_engine.run(duration)
            self.update_plots_and_metrics()
            self.run_button.setText("Run Simulation")
            self.pause_button.setEnabled(True)
        
        # Update status
        self.status_bar.showMessage(f"Running simulation: {scenario} scenario")
        self.log_text.append(f"Started simulation: {scenario} at {time.strftime('%H:%M:%S')}")
    
    def realtime_step(self):
        if self.sim_engine.current_time < self.sim_engine.duration:
            self.sim_engine.step()
            self.update_main_plot()
            # Update progress bar
            progress = int(100 * self.sim_engine.current_time / self.sim_engine.duration)
            self.progress_bar.setValue(progress)
        else:
            self.sim_timer.stop()
            self.run_button.setText("Run Simulation")
            self.pause_button.setEnabled(False)
            self.update_plots_and_metrics()
            self.log_text.append(f"Simulation completed at {time.strftime('%H:%M:%S')}")
    
    def param_update_step(self):
        """Periodically update plots when parameters change"""
        if self.sim_engine.running and self.realtime_update_cb.isChecked():
            self.update_main_plot()
    
    def pause_simulation(self):
        if self.sim_timer.isActive():
            self.sim_timer.stop()
            self.pause_button.setText("Resume")
            self.status_bar.showMessage("Simulation paused")
        else:
            self.sim_timer.start(self.realtime_update_interval)
            self.pause_button.setText("Pause")
            self.status_bar.showMessage("Simulation resumed")
    
    def reset_simulation(self):
        self.sim_timer.stop()
        self.sim_engine.reset()
        self.main_plot.clear()
        self.run_button.setText("Run Simulation")
        self.pause_button.setText("Pause")
        self.pause_button.setEnabled(False)
        self.progress_bar.setValue(0)
        self.status_bar.showMessage("Simulation reset")
        self.log_text.append("Simulation reset")
    
    def update_plots_and_metrics(self):
        """Update all plots and metrics after simulation"""
        self.update_main_plot()
        self.update_multi_plot()
        self.update_bode_plot()
        self.update_nyquist_plot()
        self.update_polezero_plot()
        self.update_performance_metrics()
    
    def update_main_plot(self):
        if not self.sim_engine.time:
            return
            
        time = self.sim_engine.time
        data = {
            'Setpoint': self.sim_engine.setpoints,
            'Response': self.sim_engine.measurements,
            'Control Output': self.sim_engine.outputs,
            'Error': self.sim_engine.errors
        }
        
        # For adaptive PID, show gain history
        if self.sim_engine.adaptive_pid and hasattr(self.sim_engine.pid, 'gain_history'):
            gain_time, Kp, Ki, Kd = zip(*self.sim_engine.pid.gain_history)
            data['Kp'] = Kp
            data['Ki'] = Ki
            data['Kd'] = Kd
        
        self.main_plot.plot(time, data)
    
    def update_multi_plot(self):
        if not self.sim_engine.time:
            return
            
        time = self.sim_engine.time
        data = {
            "System Response": (time, self.sim_engine.measurements),
            "Control Signal": (time, self.sim_engine.outputs),
            "Tracking Error": (time, self.sim_engine.errors),
            "Disturbances": (time, self.sim_engine.disturbances)
        }
        
        self.multiplot.plot_multiple(data)
    
    def update_bode_plot(self):
        # Get system parameters
        system_params = {
            'type': self.system_type_combo.currentText(),
            'params': self.parse_params(self.system_params_edit.text()),
            'delay': self.delay_spin.value()
        }
        
        # Get PID parameters
        Kp = self.kp_spin.value()
        Ki = self.ki_spin.value()
        Kd = self.kd_spin.value()
        
        # Create PID transfer function
        num_pid = [Kd, Kp, Ki]
        den_pid = [1, 0]  # s in denominator for derivative term
        pid_sys = signal.TransferFunction(num_pid, den_pid)
        
        # Create system transfer function
        if system_params['type'] == "transfer_function":
            num_sys = system_params['params'][0]
            den_sys = system_params['params'][1]
            sys_sys = signal.TransferFunction(num_sys, den_sys)
        else:
            # Default to second-order system for demonstration
            m, c, k = 1.0, 0.5, 0.2
            num_sys = [1]
            den_sys = [m, c, k]
            sys_sys = signal.TransferFunction(num_sys, den_sys)
        
        # Create open-loop system
        open_loop = signal.TransferFunction(
            np.convolve(pid_sys.num, sys_sys.num),
            np.convolve(pid_sys.den, sys_sys.den)
        )
        
        # Calculate frequency response
        w = np.logspace(-2, 2, 500)
        w, mag, phase = signal.bode(open_loop, w)
        
        # Calculate stability margins
        gm, pm, wg, wp = self.calculate_stability_margins(open_loop)
        
        # Plot Bode diagram
        self.bode_plot.plot_bode(w, mag, phase, gm, pm, wg, wp)
    
    def calculate_stability_margins(self, sys):
        """Calculate gain and phase margins"""
        gm, pm, wg, wp = 0, 0, 0, 0
        try:
            gm, pm, wg, wp = signal.margin(sys)
        except:
            pass
        return gm, pm, wg, wp
    
    def update_nyquist_plot(self):
        # Get system parameters
        system_params = {
            'type': self.system_type_combo.currentText(),
            'params': self.parse_params(self.system_params_edit.text()),
            'delay': self.delay_spin.value()
        }
        
        # Get PID parameters
        Kp = self.kp_spin.value()
        Ki = self.ki_spin.value()
        Kd = self.kd_spin.value()
        
        # Create PID transfer function
        num_pid = [Kd, Kp, Ki]
        den_pid = [1, 0]  # s in denominator for derivative term
        pid_sys = signal.TransferFunction(num_pid, den_pid)
        
        # Create system transfer function
        if system_params['type'] == "transfer_function":
            num_sys = system_params['params'][0]
            den_sys = system_params['params'][1]
            sys_sys = signal.TransferFunction(num_sys, den_sys)
        else:
            # Default to second-order system
            m, c, k = 1.0, 0.5, 0.2
            num_sys = [1]
            den_sys = [m, c, k]
            sys_sys = signal.TransferFunction(num_sys, den_sys)
        
        # Create open-loop system
        open_loop = signal.TransferFunction(
            np.convolve(pid_sys.num, sys_sys.num),
            np.convolve(pid_sys.den, sys_sys.den)
        )
        
        # Calculate Nyquist plot
        w = np.logspace(-2, 2, 1000)
        w, H = signal.freqresp(open_loop, w)
        
        # Plot Nyquist diagram
        self.nyquist_plot.plot_nyquist(H.real, H.imag)
    
    def update_polezero_plot(self):
        # Get system parameters
        system_params = {
            'type': self.system_type_combo.currentText(),
            'params': self.parse_params(self.system_params_edit.text()),
            'delay': self.delay_spin.value()
        }
        
        # Get PID parameters
        Kp = self.kp_spin.value()
        Ki = self.ki_spin.value()
        Kd = self.kd_spin.value()
        
        # Create PID transfer function
        num_pid = [Kd, Kp, Ki]
        den_pid = [1, 0]  # s in denominator for derivative term
        pid_sys = signal.TransferFunction(num_pid, den_pid)
        
        # Create system transfer function
        if system_params['type'] == "transfer_function":
            num_sys = system_params['params'][0]
            den_sys = system_params['params'][1]
            sys_sys = signal.TransferFunction(num_sys, den_sys)
        else:
            # Default to second-order system
            m, c, k = 1.0, 0.5, 0.2
            num_sys = [1]
            den_sys = [m, c, k]
            sys_sys = signal.TransferFunction(num_sys, den_sys)
        
        # Create closed-loop system
        ol_num = np.convolve(pid_sys.num, sys_sys.num)
        ol_den = np.convolve(pid_sys.den, sys_sys.den)

        # 确保分子和分母长度相同（在较短数组前补零）
        max_len = max(len(ol_num), len(ol_den))
        padded_ol_num = np.pad(ol_num, (0, max_len - len(ol_num)), 'constant')
        padded_ol_den = np.pad(ol_den, (0, max_len - len(ol_den)), 'constant')

        # 计算闭环传递函数
        closed_loop_num = padded_ol_num
        closed_loop_den = padded_ol_den + padded_ol_num
        closed_loop = signal.TransferFunction(closed_loop_num, closed_loop_den)
        
        # Get poles and zeros
        poles = closed_loop.poles
        zeros = closed_loop.zeros
        
        # Plot pole-zero map
        self.polezero_plot.plot_pole_zero(poles, zeros)
    
    def update_performance_metrics(self):
        metrics = self.sim_engine.calculate_performance_metrics()
        
        self.metrics_table.setRowCount(len(metrics))
        for i, (key, value) in enumerate(metrics.items()):
            self.metrics_table.setItem(i, 0, QTableWidgetItem(key))
            self.metrics_table.setItem(i, 1, QTableWidgetItem(f"{value:.4f}"))
    
    def optimize_pid(self):
        # Get system parameters
        system_params = {
            'type': self.system_type_combo.currentText(),
            'params': self.parse_params(self.system_params_edit.text()),
            'delay': self.delay_spin.value()
        }
        
        scenario = self.scenario_combo.currentText()
        dt = self.dt_spin.value()
        duration = self.duration_spin.value()
        
        # Get current values for bounds
        kp0 = self.kp_spin.value() or 0.01  # 确保非零
        ki0 = self.ki_spin.value() or 0.001
        kd0 = self.kd_spin.value() or 0.001
        
        # 更安全的边界计算
        bounds = [
        (max(0.001, kp0/100), min(100.0, kp0*100)),  # 扩大边界范围
        (max(0.0001, ki0/100), min(50.0, ki0*100)),
        (max(0.001, kd0/100), min(50.0, kd0*100))
        ]
        
        # 确保上界>下界
        bounds = [(lb, max(lb+0.001, ub)) for lb, ub in bounds]
        
        # Optimization function
        def objective(params):
            try:
                Kp, Ki, Kd = params
                
                # 参数有效性检查
                if any(p <= 0 for p in params):
                    return 1e10  # 返回大惩罚值
                    
                # Configure simulation
                pid_params = {
                    'Kp': Kp, 
                    'Ki': Ki, 
                    'Kd': Kd,
                    'output_limits': (self.min_output_spin.value(), self.max_output_spin.value())
                }
                self.sim_engine.configure(scenario, system_params, pid_params, dt)
                self.sim_engine.run(duration)
                
                # 添加更严格的稳定性检查
                measurements = np.array(self.sim_engine.measurements)
                if (np.any(np.isnan(measurements)) or 
                    np.any(np.abs(measurements) > 1e6) or 
                    np.any(np.abs(self.sim_engine.outputs) > 1e6)):
                    return 1e10  # 返回大惩罚值
                
                # Calculate performance metric
                metrics = self.sim_engine.calculate_performance_metrics()
                itae = metrics.get('ITAE', 1000)
                effort = metrics.get('control_effort', 0)
                
                # 确保返回有效数值
                if np.isnan(itae) or np.isinf(itae):
                    return 1e10
                    
                return itae + 0.01 * effort
            except Exception as e:
                print(f"Optimization error: {e}")
                return 1e10  # 异常时返回大惩罚值
            
            # Calculate performance metric
            metrics = self.sim_engine.calculate_performance_metrics()
            itae = metrics.get('ITAE', 1000)
            effort = metrics.get('control_effort', 0)
            
            # 确保返回有效数值
            if np.isnan(itae) or np.isinf(itae):
                return 1e10
                
            return itae + 0.01 * effort
        
        # Show progress dialog
        progress_dialog = QProgressDialog("Optimizing PID parameters...", "Cancel", 0, 100, self)
        progress_dialog.setWindowTitle("Optimization in Progress")
        progress_dialog.setWindowModality(Qt.WindowModal)
        progress_dialog.show()
        n_iter = [0]

        
        # Callback function for progress
        def callback(xk):
            """更新后的回调函数，适应新版本Scipy"""
            if progress_dialog.wasCanceled():
                return True
            n_iter[0] += 1
            progress = int(n_iter[0] / 50 * 100)
            progress_dialog.setValue(min(progress, 100))
            return False
        
        # Run optimization
        result = minimize(objective, [kp0, ki0, kd0], bounds=bounds, method='L-BFGS-B', 
                     callback=callback, 
                     options={
                         'maxiter': 200,    # 从50增加到200
                         'ftol': 1e-4,      # 收敛容差从1e-5放宽到1e-4
                         'gtol': 1e-4,
                         'eps': 0.01,       # 有限差分步长
                         'maxfun': 500       # 最大函数评估次数
                     })
        
        progress_dialog.close()
        
        if result.success:
            # Update UI with optimized parameters
            self.kp_spin.setValue(result.x[0])
            self.ki_spin.setValue(result.x[1])
            self.kd_spin.setValue(result.x[2])
            
            # Run simulation with optimized parameters
            self.run_simulation()
            
            # Show optimization result
            QMessageBox.information(self, "Optimization Complete", 
                                f"Optimized parameters:\nKp={result.x[0]:.4f}\nKi={result.x[1]:.4f}\nKd={result.x[2]:.4f}\nCost={result.fun:.4f}")
            self.log_text.append(f"Optimized PID: Kp={result.x[0]:.4f}, Ki={result.x[1]:.4f}, Kd={result.x[2]:.4f}")
        else:
            QMessageBox.warning(self, "Optimization Failed", 
                               f"Optimization did not converge: {result.message}")
            self.log_text.append(f"Optimization failed: {result.message}")
    
    def ziegler_nichols(self):
        """Apply Ziegler-Nichols tuning rules"""
        # Get system parameters
        system_params = {
            'type': self.system_type_combo.currentText(),
            'params': self.parse_params(self.system_params_edit.text()),
            'delay': self.delay_spin.value()
        }
        
        # Create system model
        system = SystemModel(model_type=system_params['type'], 
                            params=system_params['params'],
                            delay=system_params['delay'])
        
        # Find ultimate gain and period using relay method
        amplitude = 1.0
        hysteresis = 0.01
        dt = self.dt_spin.value()
        duration = self.duration_spin.value()
        
        # Run relay test
        Ku, Tu = self.relay_test(system, amplitude, hysteresis, dt, duration)
        
        if Ku is None or Tu is None:
            QMessageBox.warning(self, "Auto-Tuning Failed", "Could not find sustained oscillations")
            self.log_text.append("Ziegler-Nichols: Failed to find oscillations")
            return
        
        # Apply Ziegler-Nichols rules
        controller_type = "PID"  # Can be extended to PI or P
        if controller_type == "P":
            Kp = 0.5 * Ku
            Ki = 0.0
            Kd = 0.0
        elif controller_type == "PI":
            Kp = 0.45 * Ku
            Ki = 0.54 * Ku / Tu
            Kd = 0.0
        else:  # PID
            Kp = 0.6 * Ku
            Ki = 1.2 * Ku / Tu
            Kd = 0.075 * Ku * Tu
        
        # Update UI
        self.kp_spin.setValue(Kp)
        self.ki_spin.setValue(Ki)
        self.kd_spin.setValue(Kd)
        
        # Show result
        msg = (f"Ultimate Gain (Ku): {Ku:.4f}\n"
               f"Ultimate Period (Tu): {Tu:.4f}\n\n"
               f"Tuned Parameters:\n"
               f"Kp = {Kp:.4f}\n"
               f"Ki = {Ki:.4f}\n"
               f"Kd = {Kd:.4f}")
        QMessageBox.information(self, "Ziegler-Nichols Tuning", msg)
        self.log_text.append(f"Ziegler-Nichols tuning: Kp={Kp:.4f}, Ki={Ki:.4f}, Kd={Kd:.4f}")
    
    def relay_test(self, system, amplitude, hysteresis, dt, duration):
        """Perform relay feedback test to find Ku and Tu"""
        # Initialize simulation
        time = 0.0
        measurements = []
        outputs = []
        times = []
        
        # Relay controller state
        last_output = amplitude
        last_error = 0.0
        
        # Run simulation
        while time < duration:
            # Setpoint is 0 for relay test
            setpoint = 0.0
            
            # Get measurement
            measurement = system.update(last_output, dt)
            measurements.append(measurement)
            
            # Calculate error
            error = setpoint - measurement
            
            # Relay control logic
            if error > hysteresis and last_output < 0:
                last_output = amplitude
            elif error < -hysteresis and last_output > 0:
                last_output = -amplitude
                
            outputs.append(last_output)
            times.append(time)
            time += dt
        
        # Find oscillations in the last 80% of the simulation
        start_idx = int(0.2 * len(measurements))
        osc_measurements = measurements[start_idx:]
        osc_times = times[start_idx:]
        
        # Find peaks
        peaks, _ = signal.find_peaks(osc_measurements)
        if len(peaks) < 2:
            # Try negative peaks
            peaks, _ = signal.find_peaks([-m for m in osc_measurements])
        
        if len(peaks) < 2:
            return None, None
        
        # Calculate average period
        periods = []
        for i in range(1, len(peaks)):
            periods.append(osc_times[peaks[i]] - osc_times[peaks[i-1]])
        Tu = np.mean(periods)
        
        # Calculate amplitude
        peak_values = [osc_measurements[p] for p in peaks]
        Au = (max(peak_values) - min(peak_values)) / 2
        
        # Calculate ultimate gain
        Ku = 4 * amplitude / (np.pi * Au)
        
        return Ku, Tu
    
    def identify_system(self):
        """Identify system model from simulation data"""
        if not self.sim_engine.time:
            QMessageBox.warning(self, "No Data", "Run a simulation first to collect data")
            return
            
        # Get time, input, and output data
        time_data = self.sim_engine.time
        input_data = self.sim_engine.outputs
        output_data = self.sim_engine.measurements
        
        # Get selected model type
        model_type = self.model_type_combo.currentText()
        
        try:
            # Perform system identification
            model = self.system_identifier.identify(time_data, input_data, output_data, model_type)
            
            # Update system parameters
            self.system_type_combo.setCurrentText(model['type'])
            
            # Format parameters for display
            if model['type'] == "transfer_function":
                params_str = f"[{','.join(map(str, model['params'][0]))}, [{','.join(map(str, model['params'][1]))}]"
            else:
                params_str = ", ".join(map(str, model['params']))
            self.system_params_edit.setText(params_str)
            
            # Show result
            QMessageBox.information(self, "System Identification", 
                                  f"Identified {model_type} model:\nType: {model['type']}\nParameters: {params_str}")
            self.log_text.append(f"System identified: {model_type} with params {params_str}")
        except Exception as e:
            QMessageBox.critical(self, "Identification Failed", f"Error during system identification: {str(e)}")
            self.log_text.append(f"System identification failed: {str(e)}")
    
    def robustness_analysis(self):
        """Perform robustness analysis by varying system parameters"""
        if not self.sim_engine.time:
            QMessageBox.warning(self, "No Data", "Run a simulation first to establish baseline")
            return
            
        # Get baseline metrics
        baseline_metrics = self.sim_engine.calculate_performance_metrics()
        
        # Vary system parameters
        param_variations = [-0.2, -0.1, 0, 0.1, 0.2]  # ±20% variations
        results = []
        
        # Show progress dialog
        progress_dialog = QProgressDialog("Performing robustness analysis...", "Cancel", 0, len(param_variations), self)
        progress_dialog.setWindowTitle("Robustness Analysis")
        progress_dialog.setWindowModality(Qt.WindowModal)
        progress_dialog.show()
        
        for i, variation in enumerate(param_variations):
            if progress_dialog.wasCanceled():
                break
                
            # Create modified system parameters
            original_params = self.parse_params(self.system_params_edit.text())
            modified_params = []
            
            # 应用变化到每个参数
            for param in original_params:
                if isinstance(param, list):
                    # 处理列表参数（如传递函数的分子/分母）
                    modified_params.append([p * (1 + variation) for p in param])
                elif isinstance(param, (int, float)):
                    # 处理数值参数
                    modified_params.append(param * (1 + variation))
                else:
                    # 其他类型保持不变
                    modified_params.append(param)
            
            system_params = {
                'type': self.system_type_combo.currentText(),
                'params': modified_params,
                'delay': self.delay_spin.value()
            }
            
            # Get PID parameters
            pid_params = {
                'Kp': self.kp_spin.value(),
                'Ki': self.ki_spin.value(),
                'Kd': self.kd_spin.value(),
                'output_limits': (self.min_output_spin.value(), self.max_output_spin.value())
            }
            
            # Configure and run simulation
            self.sim_engine.configure(
                self.sim_engine.scenario, 
                system_params, 
                pid_params, 
                self.sim_engine.dt
            )
            self.sim_engine.run(self.duration_spin.value())
            
            # Calculate metrics
            metrics = self.sim_engine.calculate_performance_metrics()
            results.append({
                'variation': variation,
                'metrics': metrics,
                'params': modified_params
            })
            
            progress_dialog.setValue(i+1)
        
        progress_dialog.close()
        
        # Display results
        report = "Robustness Analysis Report\n"
        report += "=" * 30 + "\n"
        report += f"Baseline ITAE: {baseline_metrics.get('ITAE', 0):.4f}\n"
        report += f"Baseline Overshoot: {baseline_metrics.get('overshoot', 0):.2f}%\n\n"
        
        for result in results:
            report += f"Parameter variation: {result['variation']*100:.0f}%\n"
            report += f"  ITAE: {result['metrics'].get('ITAE', 0):.4f} ({result['metrics'].get('ITAE', 0)/baseline_metrics.get('ITAE', 1):.2%} of baseline)\n"
            report += f"  Overshoot: {result['metrics'].get('overshoot', 0):.2f}%\n\n"
        
        # Show report in dialog
        report_dialog = QDialog(self)
        report_dialog.setWindowTitle("Robustness Analysis Results")
        layout = QVBoxLayout()
        text_edit = QTextEdit()
        text_edit.setPlainText(report)
        text_edit.setReadOnly(True)
        layout.addWidget(text_edit)
        report_dialog.setLayout(layout)
        report_dialog.exec_()
        
        self.log_text.append("Completed robustness analysis")
    
    def sensitivity_analysis(self):
        """Perform sensitivity analysis by varying PID parameters"""
        # Vary PID parameters
        variations = [-0.3, -0.15, 0, 0.15, 0.3]  # ±30% variations
        results = []
        
        # Show progress dialog
        progress_dialog = QProgressDialog("Performing sensitivity analysis...", "Cancel", 0, len(variations)*3, self)
        progress_dialog.setWindowTitle("Sensitivity Analysis")
        progress_dialog.setWindowModality(Qt.WindowModal)
        progress_dialog.show()
        
        # Get baseline
        self.run_simulation()
        baseline_metrics = self.sim_engine.calculate_performance_metrics()
        progress_counter = 0
        
        # Vary Kp
        kp_results = []
        original_kp = self.kp_spin.value()
        for var in variations:
            self.kp_spin.setValue(original_kp * (1 + var))
            self.run_simulation()
            metrics = self.sim_engine.calculate_performance_metrics()
            kp_results.append(metrics)
            progress_counter += 1
            progress_dialog.setValue(progress_counter)
        
        # Vary Ki
        ki_results = []
        original_ki = self.ki_spin.value()
        for var in variations:
            self.ki_spin.setValue(original_ki * (1 + var))
            self.run_simulation()
            metrics = self.sim_engine.calculate_performance_metrics()
            ki_results.append(metrics)
            progress_counter += 1
            progress_dialog.setValue(progress_counter)
        
        # Vary Kd
        kd_results = []
        original_kd = self.kd_spin.value()
        for var in variations:
            self.kd_spin.setValue(original_kd * (1 + var))
            self.run_simulation()
            metrics = self.sim_engine.calculate_performance_metrics()
            kd_results.append(metrics)
            progress_counter += 1
            progress_dialog.setValue(progress_counter)
        
        # Restore original values
        self.kp_spin.setValue(original_kp)
        self.ki_spin.setValue(original_ki)
        self.kd_spin.setValue(original_kd)
        
        progress_dialog.close()
        
        # Generate report
        report = "Sensitivity Analysis Report\n"
        report += "=" * 30 + "\n"
        report += f"Baseline ITAE: {baseline_metrics.get('ITAE', 0):.4f}\n"
        report += f"Baseline Overshoot: {baseline_metrics.get('overshoot', 0):.2f}%\n\n"
        
        report += "Kp Variations:\n"
        for i, var in enumerate(variations):
            report += f"  {var*100:.0f}%: ITAE={kp_results[i].get('ITAE', 0):.4f}, Overshoot={kp_results[i].get('overshoot', 0):.2f}%\n"
        
        report += "\nKi Variations:\n"
        for i, var in enumerate(variations):
            report += f"  {var*100:.0f}%: ITAE={ki_results[i].get('ITAE', 0):.4f}, Overshoot={ki_results[i].get('overshoot', 0):.2f}%\n"
        
        report += "\nKd Variations:\n"
        for i, var in enumerate(variations):
            report += f"  {var*100:.0f}%: ITAE={kd_results[i].get('ITAE', 0):.4f}, Overshoot={kd_results[i].get('overshoot', 0):.2f}%\n"
        
        # Show report in dialog
        report_dialog = QDialog(self)
        report_dialog.setWindowTitle("Sensitivity Analysis Results")
        layout = QVBoxLayout()
        text_edit = QTextEdit()
        text_edit.setPlainText(report)
        text_edit.setReadOnly(True)
        layout.addWidget(text_edit)
        report_dialog.setLayout(layout)
        report_dialog.exec_()
        
        self.log_text.append("Completed sensitivity analysis")
    
    def save_results(self):
        if not self.sim_engine.time:
            QMessageBox.warning(self, "No Data", "No simulation data to save.")
            return
            
        # Get file path
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Simulation Data", self.results_dir, 
            "CSV Files (*.csv);;MAT Files (*.mat);;Pickle Files (*.pkl);;JSON Files (*.json);;All Files (*)"
        )
        
        if not file_path:
            return
            
        try:
            if file_path.endswith('.csv'):
                # Save data to CSV
                data = {
                    'Time': self.sim_engine.time,
                    'Setpoint': self.sim_engine.setpoints,
                    'Response': self.sim_engine.measurements,
                    'Output': self.sim_engine.outputs,
                    'Error': self.sim_engine.errors,
                    'Disturbance': self.sim_engine.disturbances
                }
                df = pd.DataFrame(data)
                df.to_csv(file_path, index=False)
                
                # Save plot
                plot_path = file_path.replace('.csv', '_plot.png')
                self.main_plot.figure.savefig(plot_path, dpi=150)
            
            elif file_path.endswith('.mat'):
                # Save to MATLAB format
                from scipy.io import savemat
                data = {
                    'time': np.array(self.sim_engine.time),
                    'setpoint': np.array(self.sim_engine.setpoints),
                    'response': np.array(self.sim_engine.measurements),
                    'output': np.array(self.sim_engine.outputs),
                    'error': np.array(self.sim_engine.errors),
                    'disturbance': np.array(self.sim_engine.disturbances)
                }
                savemat(file_path, data)
            
            elif file_path.endswith('.pkl'):
                # Save as pickle
                data = {
                    'time': self.sim_engine.time,
                    'setpoint': self.sim_engine.setpoints,
                    'response': self.sim_engine.measurements,
                    'output': self.sim_engine.outputs,
                    'error': self.sim_engine.errors,
                    'disturbance': self.sim_engine.disturbances,
                    'params': {
                        'system': self.system_type_combo.currentText(),
                        'pid': (self.kp_spin.value(), self.ki_spin.value(), self.kd_spin.value()),
                        'scenario': self.scenario_combo.currentText()
                    }
                }
                with open(file_path, 'wb') as f:
                    pickle.dump(data, f)
            
            elif file_path.endswith('.json'):
                # Save as JSON
                data = {
                    'time': self.sim_engine.time,
                    'setpoint': self.sim_engine.setpoints,
                    'response': self.sim_engine.measurements,
                    'output': self.sim_engine.outputs,
                    'error': self.sim_engine.errors,
                    'disturbance': self.sim_engine.disturbances,
                    'params': {
                        'system': self.system_type_combo.currentText(),
                        'pid': {
                            'Kp': self.kp_spin.value(),
                            'Ki': self.ki_spin.value(),
                            'Kd': self.kd_spin.value()
                        },
                        'scenario': self.scenario_combo.currentText()
                    }
                }
                with open(file_path, 'w') as f:
                    json.dump(data, f, indent=4)
            
            self.status_bar.showMessage(f"Results saved to {file_path}")
            self.log_text.append(f"Saved results to {file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save results: {str(e)}")
            self.log_text.append(f"Save error: {str(e)}")
    
    def load_results(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load Simulation Data", self.results_dir, 
            "Data Files (*.csv *.mat *.pkl *.json);;All Files (*)"
        )
        
        if not file_path:
            return
            
        try:
            if file_path.endswith('.csv'):
                df = pd.read_csv(file_path)
                self.sim_engine.time = df['Time'].tolist()
                self.sim_engine.setpoints = df['Setpoint'].tolist()
                self.sim_engine.measurements = df['Response'].tolist()
                self.sim_engine.outputs = df['Output'].tolist()
                self.sim_engine.errors = df['Error'].tolist()
                self.sim_engine.disturbances = df['Disturbance'].tolist()
                
            elif file_path.endswith('.mat'):
                from scipy.io import loadmat
                data = loadmat(file_path)
                self.sim_engine.time = data['time'].flatten().tolist()
                self.sim_engine.setpoints = data['setpoint'].flatten().tolist()
                self.sim_engine.measurements = data['response'].flatten().tolist()
                self.sim_engine.outputs = data['output'].flatten().tolist()
                self.sim_engine.errors = data['error'].flatten().tolist()
                self.sim_engine.disturbances = data['disturbance'].flatten().tolist()
            
            elif file_path.endswith('.pkl'):
                with open(file_path, 'rb') as f:
                    data = pickle.load(f)
                self.sim_engine.time = data['time']
                self.sim_engine.setpoints = data['setpoint']
                self.sim_engine.measurements = data['response']
                self.sim_engine.outputs = data['output']
                self.sim_engine.errors = data['error']
                self.sim_engine.disturbances = data['disturbance']
                
                # Update parameters if available
                if 'params' in data:
                    params = data['params']
                    idx = self.system_type_combo.findText(params['system'])
                    if idx >= 0:
                        self.system_type_combo.setCurrentIndex(idx)
                    self.kp_spin.setValue(params['pid'][0])
                    self.ki_spin.setValue(params['pid'][1])
                    self.kd_spin.setValue(params['pid'][2])
                    idx = self.scenario_combo.findText(params['scenario'])
                    if idx >= 0:
                        self.scenario_combo.setCurrentIndex(idx)
            
            elif file_path.endswith('.json'):
                with open(file_path, 'r') as f:
                    data = json.load(f)
                self.sim_engine.time = data['time']
                self.sim_engine.setpoints = data['setpoint']
                self.sim_engine.measurements = data['response']
                self.sim_engine.outputs = data['output']
                self.sim_engine.errors = data['error']
                self.sim_engine.disturbances = data['disturbance']
                
                # Update parameters if available
                if 'params' in data:
                    params = data['params']
                    idx = self.system_type_combo.findText(params['system'])
                    if idx >= 0:
                        self.system_type_combo.setCurrentIndex(idx)
                    self.kp_spin.setValue(params['pid']['Kp'])
                    self.ki_spin.setValue(params['pid']['Ki'])
                    self.kd_spin.setValue(params['pid']['Kd'])
                    idx = self.scenario_combo.findText(params['scenario'])
                    if idx >= 0:
                        self.scenario_combo.setCurrentIndex(idx)
            
            # Update plots and metrics
            self.update_plots_and_metrics()
            self.status_bar.showMessage(f"Results loaded from {file_path}")
            self.log_text.append(f"Loaded results from {file_path}")
            
        except Exception as e:
            QMessageBox.critical(self, "Load Error", f"Failed to load results: {str(e)}")
            self.log_text.append(f"Load error: {str(e)}")
    
    def export_plot(self):
        """Export current plot to image file"""
        if not self.sim_engine.time:
            QMessageBox.warning(self, "No Data", "No plot to export")
            return
            
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Plot", self.results_dir, 
            "PNG Files (*.png);;PDF Files (*.pdf);;SVG Files (*.svg);;All Files (*)"
        )
        
        if not file_path:
            return
            
        try:
            # Determine which plot to export based on current tab
            current_tab = self.tab_widget.currentIndex()
            if current_tab == 0:  # Main plot
                self.main_plot.figure.savefig(file_path, dpi=150)
            elif current_tab == 1:  # Multi-plot
                self.multiplot.figure.savefig(file_path, dpi=150)
            elif current_tab == 2:  # Bode plot
                self.bode_plot.figure.savefig(file_path, dpi=150)
            elif current_tab == 3:  # Nyquist plot
                self.nyquist_plot.figure.savefig(file_path, dpi=150)
            elif current_tab == 4:  # Pole-zero plot
                self.polezero_plot.figure.savefig(file_path, dpi=150)
            elif current_tab == 5:  # Control diagram
                self.control_diagram.figure.savefig(file_path, dpi=150)
            
            self.status_bar.showMessage(f"Plot exported to {file_path}")
            self.log_text.append(f"Exported plot to {file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export plot: {str(e)}")
            self.log_text.append(f"Export error: {str(e)}")
    
    def generate_report(self):
        """Generate a comprehensive report of the current simulation"""
        if not self.sim_engine.time:
            QMessageBox.warning(self, "No Data", "Run a simulation first to generate report")
            return
            
        # Get file path
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Report", self.results_dir, 
            "PDF Files (*.pdf);;HTML Files (*.html);;Text Files (*.txt);;All Files (*)"
        )
        
        if not file_path:
            return
            
        try:
            # 创建报告内容
            report = "PID Tuner Simulation Report\n" + "="*40 + "\n\n"
            report += f"Date: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            
            # System parameters
            report += "System Parameters:\n"
            report += f"  Type: {self.system_type_combo.currentText()}\n"
            report += f"  Parameters: {self.system_params_edit.text()}\n"
            report += f"  Time Delay: {self.delay_spin.value()} s\n"
            report += f"  Noise Level: {self.noise_level_spin.value()}\n\n"
            
            # PID parameters
            report += "PID Parameters:\n"
            report += f"  Kp: {self.kp_spin.value()}\n"
            report += f"  Ki: {self.ki_spin.value()}\n"
            report += f"  Kd: {self.kd_spin.value()}\n"
            report += f"  Min Output: {self.min_output_spin.value()}\n"
            report += f"  Max Output: {self.max_output_spin.value()}\n\n"
            
            # Simulation settings
            report += "Simulation Settings:\n"
            report += f"  Scenario: {self.scenario_combo.currentText()}\n"
            report += f"  Control Mode: {self.control_mode_combo.currentText()}\n"
            report += f"  Time Step: {self.dt_spin.value()} s\n"
            report += f"  Duration: {self.duration_spin.value()} s\n"
            report += f"  Adaptive PID: {'Yes' if self.adaptive_pid_cb.isChecked() else 'No'}\n\n"
            
            # Performance metrics
            metrics = self.sim_engine.calculate_performance_metrics()
            report += "Performance Metrics:\n"
            for key, value in metrics.items():
                report += f"  {key}: {value:.4f}\n"
            
            # Save report
            if file_path.endswith('.pdf'):
                # 创建PDF文档
                c = canvas.Canvas(file_path, pagesize=letter)
                width, height = letter
                
                # 设置样式
                styles = getSampleStyleSheet()
                title_style = styles['Title']
                heading_style = styles['Heading2']
                body_style = styles['BodyText']
                
                # 添加标题
                title = "PID Tuner Simulation Report"
                c.setFont("Helvetica-Bold", 16)
                c.drawCentredString(width/2, height-50, title)
                
                # 添加日期
                c.setFont("Helvetica", 10)
                c.drawString(50, height-80, f"Generated on: {time.strftime('%Y-%m-%d %H:%M:%S')}")
                
                # 添加文本内容
                y_position = height - 120
                text = c.beginText(50, y_position)
                text.setFont("Helvetica", 12)
                
                # 添加系统参数
                text.textLine("System Parameters:")
                text.textLine(f"  Type: {self.system_type_combo.currentText()}")
                text.textLine(f"  Parameters: {self.system_params_edit.text()}")
                text.textLine(f"  Time Delay: {self.delay_spin.value()} s")
                text.textLine(f"  Noise Level: {self.noise_level_spin.value()}")
                text.textLine("")
                
                # PID参数
                text.textLine("PID Parameters:")
                text.textLine(f"  Kp: {self.kp_spin.value()}")
                text.textLine(f"  Ki: {self.ki_spin.value()}")
                text.textLine(f"  Kd: {self.kd_spin.value()}")
                text.textLine(f"  Min Output: {self.min_output_spin.value()}")
                text.textLine(f"  Max Output: {self.max_output_spin.value()}")
                text.textLine("")
                
                # 仿真设置
                text.textLine("Simulation Settings:")
                text.textLine(f"  Scenario: {self.scenario_combo.currentText()}")
                text.textLine(f"  Control Mode: {self.control_mode_combo.currentText()}")
                text.textLine(f"  Time Step: {self.dt_spin.value()} s")
                text.textLine(f"  Duration: {self.duration_spin.value()} s")
                text.textLine(f"  Adaptive PID: {'Yes' if self.adaptive_pid_cb.isChecked() else 'No'}")
                text.textLine("")
                
                c.drawText(text)
                
                # 添加性能指标表格
                c.showPage()  # 新的一页
                c.setFont("Helvetica-Bold", 14)
                c.drawString(50, height-50, "Performance Metrics")
                
                # 创建表格数据
                metrics = self.sim_engine.calculate_performance_metrics()
                table_data = [["Metric", "Value"]]
                for key, value in metrics.items():
                    table_data.append([key, f"{value:.4f}"])
                
                # 手动绘制表格
                col_width = 250
                row_height = 20
                table_top = height - 100
                
                # 绘制表头
                c.setFillColor(colors.lightgrey)
                c.rect(50, table_top - row_height, col_width, row_height, fill=1, stroke=1)
                c.rect(50 + col_width, table_top - row_height, col_width, row_height, fill=1, stroke=1)
                c.setFillColor(colors.black)
                
                c.setFont("Helvetica-Bold", 12)
                c.drawCentredString(50 + col_width/2, table_top - row_height + 6, "Metric")
                c.drawCentredString(50 + col_width + col_width/2, table_top - row_height + 6, "Value")
                
                # 绘制表格内容
                c.setFont("Helvetica", 10)
                for i, row in enumerate(table_data[1:]):
                    y_pos = table_top - row_height * (i + 2)
                    c.rect(50, y_pos, col_width, row_height, fill=0, stroke=1)
                    c.rect(50 + col_width, y_pos, col_width, row_height, fill=0, stroke=1)
                    
                    c.drawString(60, y_pos + 6, row[0])
                    c.drawString(50 + col_width + 10, y_pos + 6, row[1])
                
                # 添加图表
                if self.sim_engine.time:
                    c.showPage()  # 新的一页
                    c.setFont("Helvetica-Bold", 14)
                    c.drawString(50, height-50, "Response Plot")
                    
                    # 保存临时图片
                    plot_path = os.path.join(tempfile.gettempdir(), "pid_plot.png")
                    self.main_plot.figure.savefig(plot_path, dpi=150)
                    
                    # 在PDF中添加图片
                    c.drawImage(plot_path, 50, height-450, width=500, height=300)
                
                c.save()
                
                self.status_bar.showMessage(f"PDF report saved to {file_path}")
                self.log_text.append(f"Generated PDF report: {file_path}")
            else:
                with open(file_path, 'w') as f:
                    f.write(report)
            
            # Save plot
            plot_path = file_path.rsplit('.', 1)[0] + "_plot.png"
            self.main_plot.figure.savefig(plot_path, dpi=150)
            
            self.status_bar.showMessage(f"Report saved to {file_path}")
            self.log_text.append(f"Generated report: {file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Report Error", f"Failed to generate report: {str(e)}")
            self.log_text.append(f"Report error: {str(e)}")
    
    def parse_params(self, params_str):
        """Parse parameters from string, handling different formats"""
        try:
            # Try to parse as JSON
            return json.loads(params_str)
        except:
            pass
        
        try:
            # Try to parse as Python literal
            return eval(params_str)
        except:
            pass
        
        # Special handling for integrator
        if self.system_type_combo.currentText() == "integrator":
            try:
                return float(params_str)
            except:
                return params_str
        
        return params_str

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")  # Modern style
    
    # Set application font
    font = app.font()
    font.setPointSize(10)
    app.setFont(font)
    
    window = PIDTunerGUI()
    window.show()
    sys.exit(app.exec_())