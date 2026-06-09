import sys
import numpy as np
import matplotlib
import json
import scipy.signal as signal
from scipy.integrate import solve_ivp
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QToolBar, QAction, QPushButton, QDockWidget, QListWidget, QLabel, QDialog,
    QLineEdit, QFormLayout, QDialogButtonBox, QTabWidget, QTextEdit, QComboBox,
    QSpinBox, QDoubleSpinBox, QFileDialog, QMessageBox, QGroupBox, QCheckBox,
    QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt5.QtCore import Qt, QPointF, QRectF, QTimer
from PyQt5.QtGui import QPainter, QPainterPath, QPen, QBrush, QColor, QFont, QPolygonF, QIcon
from enum import Enum, auto
import os
import time

class BlockType(Enum):
    SINE_GENERATOR = "Sine Wave"
    SQUARE_GENERATOR = "Square Wave"
    PULSE_GENERATOR = "Pulse Generator"
    RAMP_GENERATOR = "Ramp Generator"
    GAIN = "Gain"
    INTEGRATOR = "Integrator"
    DERIVATIVE = "Derivative"
    ADDER = "Adder"
    MULTIPLIER = "Multiplier"
    DIVIDER = "Divider"
    ABSOLUTE_VALUE = "Absolute Value"
    CONSTANT = "Constant"
    SCOPE = "Scope"
    XY_SCOPE = "XY Scope"
    SUBSYSTEM = "Subsystem"
    TRANSPORT_DELAY = "Transport Delay"
    SATURATION = "Saturation"
    DEAD_ZONE = "Dead Zone"
    QUANTIZER = "Quantizer"
    PID_CONTROLLER = "PID Controller"
    TRANSFER_FUNCTION = "Transfer Function"
    STATE_SPACE = "State Space"
    SWITCH = "Switch"
    RELATIONAL_OPERATOR = "Relational Operator"
    LOGICAL_OPERATOR = "Logical Operator"
    MATH_FUNCTION = "Math Function"
    LOOKUP_TABLE = "Lookup Table"
    SIGNAL_GENERATOR = "Signal Generator"
    NOISE_GENERATOR = "Noise Generator"
    DATA_STORE = "Data Store"
    FROM_FILE = "From File"
    TO_FILE = "To File"

class PortType(Enum):
    INPUT = 0
    OUTPUT = 1

class Block:
    def __init__(self, block_type, position=QPointF(0, 0), name=None):
        self.block_type = block_type
        self.position = position
        self.size = QPointF(100, 60)
        self.input_ports = []
        self.output_ports = []
        self.params = {}
        self.name = name if name else f"{block_type.value}_{id(self)}"
        self.id = id(self)
        self.color = QColor(70, 130, 180)
        self.subsystem_blocks = []  # For subsystem blocks
        self.subsystem_connections = []  # For subsystem connections
        self.data_store = []  # For data storage
        self.last_output = 0.0  # For transport delay
        
        # Initialize parameters based on block type
        if block_type in [BlockType.SINE_GENERATOR, BlockType.SQUARE_GENERATOR, 
                          BlockType.PULSE_GENERATOR, BlockType.RAMP_GENERATOR]:
            self.params = {
                'amplitude': 1.0, 
                'frequency': 1.0, 
                'phase': 0.0,
                'offset': 0.0,
                'duty_cycle': 50.0  # For pulse generator
            }
            self.output_ports = [Port(PortType.OUTPUT, self, 0)]
            
        elif block_type == BlockType.SIGNAL_GENERATOR:
            self.params = {
                'signal_type': 'sine',  # sine, square, sawtooth, triangle
                'amplitude': 1.0,
                'frequency': 1.0,
                'offset': 0.0
            }
            self.output_ports = [Port(PortType.OUTPUT, self, 0)]
            
        elif block_type == BlockType.NOISE_GENERATOR:
            self.params = {
                'noise_type': 'uniform',  # uniform, gaussian
                'amplitude': 1.0,
                'mean': 0.0,
                'std_dev': 0.1
            }
            self.output_ports = [Port(PortType.OUTPUT, self, 0)]
            
        elif block_type == BlockType.GAIN:
            self.params = {'gain': 2.0}
            self.input_ports = [Port(PortType.INPUT, self, 0)]
            self.output_ports = [Port(PortType.OUTPUT, self, 0)]
            
        elif block_type == BlockType.INTEGRATOR:
            self.params = {'initial': 0.0, 'limit_output': False, 'upper_limit': 10.0, 'lower_limit': -10.0}
            self.input_ports = [Port(PortType.INPUT, self, 0)]
            self.output_ports = [Port(PortType.OUTPUT, self, 0)]
            
        elif block_type == BlockType.DERIVATIVE:
            self.params = {'initial': 0.0}
            self.input_ports = [Port(PortType.INPUT, self, 0)]
            self.output_ports = [Port(PortType.OUTPUT, self, 0)]
            
        elif block_type == BlockType.ADDER:
            self.params = {'num_inputs': 2, 'signs': ['+', '+']}
            self.input_ports = [Port(PortType.INPUT, self, i) for i in range(2)]
            self.output_ports = [Port(PortType.OUTPUT, self, 0)]
            
        elif block_type == BlockType.MULTIPLIER:
            self.params = {}
            self.input_ports = [Port(PortType.INPUT, self, 0), Port(PortType.INPUT, self, 1)]
            self.output_ports = [Port(PortType.OUTPUT, self, 0)]
            
        elif block_type == BlockType.DIVIDER:
            self.params = {}
            self.input_ports = [Port(PortType.INPUT, self, 0), Port(PortType.INPUT, self, 1)]
            self.output_ports = [Port(PortType.OUTPUT, self, 0)]
            
        elif block_type == BlockType.ABSOLUTE_VALUE:
            self.params = {}
            self.input_ports = [Port(PortType.INPUT, self, 0)]
            self.output_ports = [Port(PortType.OUTPUT, self, 0)]
            
        elif block_type == BlockType.SCOPE:
            self.params = {'time_span': 10.0, 'num_inputs': 1}
            self.input_ports = [Port(PortType.INPUT, self, 0)]
            self.data = [[] for _ in range(self.params['num_inputs'])]
            
        elif block_type == BlockType.XY_SCOPE:
            self.params = {'x_min': -10, 'x_max': 10, 'y_min': -10, 'y_max': 10}
            self.input_ports = [Port(PortType.INPUT, self, 0), Port(PortType.INPUT, self, 1)]
            self.data = []
            
        elif block_type == BlockType.CONSTANT:
            self.params = {'value': 1.0}
            self.output_ports = [Port(PortType.OUTPUT, self, 0)]
            
        elif block_type == BlockType.SUBSYSTEM:
            self.params = {}
            self.input_ports = [Port(PortType.INPUT, self, i) for i in range(2)]
            self.output_ports = [Port(PortType.OUTPUT, self, 0)]
            self.color = QColor(100, 180, 100)
            
        elif block_type == BlockType.TRANSPORT_DELAY:
            self.params = {'delay_time': 1.0, 'initial_output': 0.0, 'buffer_size': 1000}
            self.input_ports = [Port(PortType.INPUT, self, 0)]
            self.output_ports = [Port(PortType.OUTPUT, self, 0)]
            self.delay_buffer = []
            
        elif block_type == BlockType.SATURATION:
            self.params = {'upper_limit': 10.0, 'lower_limit': -10.0}
            self.input_ports = [Port(PortType.INPUT, self, 0)]
            self.output_ports = [Port(PortType.OUTPUT, self, 0)]
            
        elif block_type == BlockType.DEAD_ZONE:
            self.params = {'start': -0.5, 'end': 0.5}
            self.input_ports = [Port(PortType.INPUT, self, 0)]
            self.output_ports = [Port(PortType.OUTPUT, self, 0)]
            
        elif block_type == BlockType.QUANTIZER:
            self.params = {'interval': 0.5}
            self.input_ports = [Port(PortType.INPUT, self, 0)]
            self.output_ports = [Port(PortType.OUTPUT, self, 0)]
            
        elif block_type == BlockType.PID_CONTROLLER:
            self.params = {'P': 1.0, 'I': 0.1, 'D': 0.01, 'N': 100.0, 'initial': 0.0}
            self.input_ports = [Port(PortType.INPUT, self, 0)]
            self.output_ports = [Port(PortType.OUTPUT, self, 0)]
            self.integral = 0.0
            self.prev_error = 0.0
            
        elif block_type == BlockType.TRANSFER_FUNCTION:
            self.params = {
                'numerator': [1.0],
                'denominator': [1.0, 1.0],
                'initial': [0.0]
            }
            self.input_ports = [Port(PortType.INPUT, self, 0)]
            self.output_ports = [Port(PortType.OUTPUT, self, 0)]
            self.state = np.zeros(len(self.params['denominator']) - 1)
            
        elif block_type == BlockType.STATE_SPACE:
            self.params = {
                'A': [[0, 1], [-1, -0.5]],
                'B': [[0], [1]],
                'C': [[1, 0]],
                'D': [[0]],
                'initial': [0, 0]
            }
            self.input_ports = [Port(PortType.INPUT, self, 0)]
            self.output_ports = [Port(PortType.OUTPUT, self, 0)]
            self.state = np.array(self.params['initial'])
            
        elif block_type == BlockType.SWITCH:
            self.params = {'threshold': 0.0, 'criteria': '>='}
            self.input_ports = [
                Port(PortType.INPUT, self, 0),  # Control input
                Port(PortType.INPUT, self, 1),  # First input
                Port(PortType.INPUT, self, 2)   # Second input
            ]
            self.output_ports = [Port(PortType.OUTPUT, self, 0)]
            
        elif block_type == BlockType.RELATIONAL_OPERATOR:
            self.params = {'operator': '=='}  # ==, !=, <, <=, >, >=
            self.input_ports = [Port(PortType.INPUT, self, 0), Port(PortType.INPUT, self, 1)]
            self.output_ports = [Port(PortType.OUTPUT, self, 0)]
            
        elif block_type == BlockType.LOGICAL_OPERATOR:
            self.params = {'operator': 'AND', 'num_inputs': 2}  # AND, OR, XOR, NOT
            self.input_ports = [Port(PortType.INPUT, self, i) for i in range(2)]
            self.output_ports = [Port(PortType.OUTPUT, self, 0)]
            
        elif block_type == BlockType.MATH_FUNCTION:
            self.params = {'function': 'exp'}  # exp, log, sqrt, sin, cos, tan
            self.input_ports = [Port(PortType.INPUT, self, 0)]
            self.output_ports = [Port(PortType.OUTPUT, self, 0)]
            
        elif block_type == BlockType.LOOKUP_TABLE:
            self.params = {
                'table': [0.0, 1.0, 2.0, 1.0, 0.0],
                'breakpoints': [0, 1, 2, 3, 4],
                'method': 'linear'  # linear, nearest, zero, slinear, quadratic, cubic
            }
            self.input_ports = [Port(PortType.INPUT, self, 0)]
            self.output_ports = [Port(PortType.OUTPUT, self, 0)]
            
        elif block_type == BlockType.DATA_STORE:
            self.params = {'size': 1000}
            self.input_ports = [Port(PortType.INPUT, self, 0)]
            self.output_ports = [Port(PortType.OUTPUT, self, 0)]
            
        elif block_type == BlockType.FROM_FILE:
            self.params = {'filename': '', 'variable': 'data', 'time_col': 0, 'data_col': 1}
            self.output_ports = [Port(PortType.OUTPUT, self, 0)]
            self.file_data = []
            
        elif block_type == BlockType.TO_FILE:
            self.params = {'filename': 'output.txt', 'format': '%.4f'}
            self.input_ports = [Port(PortType.INPUT, self, 0)]
            self.file_data = []
    
    def get_port_position(self, port, port_type):
        """Calculate port position relative to block position"""
        if port_type == PortType.INPUT:
            if not self.input_ports:
                return self.position + QPointF(0, self.size.y()/2)
            y = self.position.y() + (port.index + 1) * (self.size.y() / (len(self.input_ports) + 1))
            return QPointF(self.position.x(), y)
        else:  # OUTPUT
            if not self.output_ports:
                return self.position + QPointF(self.size.x(), self.size.y()/2)
            y = self.position.y() + (port.index + 1) * (self.size.y() / (len(self.output_ports) + 1))
            return QPointF(self.position.x() + self.size.x(), y)
    
    def compute(self, inputs, t, dt):
        """Compute the output based on block type"""
        try:
            if self.block_type == BlockType.SINE_GENERATOR:
                return [self.params['offset'] + self.params['amplitude'] * 
                        np.sin(2 * np.pi * self.params['frequency'] * t + self.params['phase'])]
            
            elif self.block_type == BlockType.SQUARE_GENERATOR:
                value = np.sin(2 * np.pi * self.params['frequency'] * t + self.params['phase'])
                return [self.params['offset'] + self.params['amplitude'] * (1 if value >= 0 else -1)]
            
            elif self.block_type == BlockType.PULSE_GENERATOR:
                period = 1.0 / self.params['frequency']
                cycle_pos = (t % period) / period * 100
                output = self.params['amplitude'] if cycle_pos < self.params['duty_cycle'] else 0
                return [self.params['offset'] + output]
            
            elif self.block_type == BlockType.RAMP_GENERATOR:
                return [self.params['offset'] + self.params['amplitude'] * t]
            
            elif self.block_type == BlockType.SIGNAL_GENERATOR:
                if self.params['signal_type'] == 'sine':
                    value = np.sin(2 * np.pi * self.params['frequency'] * t)
                elif self.params['signal_type'] == 'square':
                    value = 1 if np.sin(2 * np.pi * self.params['frequency'] * t) >= 0 else -1
                elif self.params['signal_type'] == 'sawtooth':
                    value = 2 * (t * self.params['frequency'] - np.floor(t * self.params['frequency'] + 0.5))
                elif self.params['signal_type'] == 'triangle':
                    value = 2 * np.abs(2 * (t * self.params['frequency'] - np.floor(t * self.params['frequency'] + 0.5))) - 1
                return [self.params['offset'] + self.params['amplitude'] * value]
            
            elif self.block_type == BlockType.NOISE_GENERATOR:
                if self.params['noise_type'] == 'uniform':
                    value = self.params['mean'] + self.params['amplitude'] * (2 * np.random.rand() - 1)
                else:  # gaussian
                    value = self.params['mean'] + self.params['amplitude'] * np.random.normal(0, self.params['std_dev'])
                return [value]
            
            elif self.block_type == BlockType.GAIN:
                return [self.params['gain'] * inputs[0]]
            
            elif self.block_type == BlockType.INTEGRATOR:
                if not hasattr(self, 'prev_input'):
                    self.prev_input = inputs[0]
                    self.integral = self.params['initial']
                else:
                    # Trapezoidal integration
                    self.integral += (self.prev_input + inputs[0]) * dt / 2
                    self.prev_input = inputs[0]
                
                # Apply output limits
                if self.params['limit_output']:
                    if self.integral > self.params['upper_limit']:
                        self.integral = self.params['upper_limit']
                    elif self.integral < self.params['lower_limit']:
                        self.integral = self.params['lower_limit']
                
                return [self.integral]
            
            elif self.block_type == BlockType.DERIVATIVE:
                if not hasattr(self, 'prev_input'):
                    self.prev_input = inputs[0]
                    return [0]
                
                derivative = (inputs[0] - self.prev_input) / dt
                self.prev_input = inputs[0]
                return [derivative]
            
            elif self.block_type == BlockType.ADDER:
                result = 0
                for i, sign in zip(inputs, self.params['signs']):
                    if sign == '+':
                        result += i
                    else:
                        result -= i
                return [result]
            
            elif self.block_type == BlockType.MULTIPLIER:
                return [inputs[0] * inputs[1]]
            
            elif self.block_type == BlockType.DIVIDER:
                if inputs[1] == 0:
                    return [0]  # Avoid division by zero
                return [inputs[0] / inputs[1]]
            
            elif self.block_type == BlockType.ABSOLUTE_VALUE:
                return [abs(inputs[0])]
            
            elif self.block_type == BlockType.CONSTANT:
                return [self.params['value']]
            
            elif self.block_type == BlockType.TRANSPORT_DELAY:
                # Add current input to buffer with timestamp
                self.delay_buffer.append((t, inputs[0]))
                
                # Remove old entries
                while self.delay_buffer and self.delay_buffer[0][0] < t - self.params['delay_time']:
                    self.delay_buffer.pop(0)
                
                # Find the value at the delayed time
                if not self.delay_buffer:
                    return [self.params['initial_output']]
                
                # Find the two points surrounding the delayed time
                delayed_time = t - self.params['delay_time']
                for i in range(len(self.delay_buffer)):
                    if self.delay_buffer[i][0] >= delayed_time:
                        if i == 0:
                            return [self.delay_buffer[0][1]]
                        else:
                            # Linear interpolation
                            t0, y0 = self.delay_buffer[i-1]
                            t1, y1 = self.delay_buffer[i]
                            alpha = (delayed_time - t0) / (t1 - t0)
                            return [y0 + alpha * (y1 - y0)]
                
                return [self.delay_buffer[-1][1]]
            
            elif self.block_type == BlockType.SATURATION:
                if inputs[0] > self.params['upper_limit']:
                    return [self.params['upper_limit']]
                elif inputs[0] < self.params['lower_limit']:
                    return [self.params['lower_limit']]
                else:
                    return [inputs[0]]
            
            elif self.block_type == BlockType.DEAD_ZONE:
                if inputs[0] > self.params['end']:
                    return [inputs[0] - self.params['end']]
                elif inputs[0] < self.params['start']:
                    return [inputs[0] - self.params['start']]
                else:
                    return [0.0]
            
            elif self.block_type == BlockType.QUANTIZER:
                return [self.params['interval'] * round(inputs[0] / self.params['interval'])]
            
            elif self.block_type == BlockType.PID_CONTROLLER:
                error = inputs[0]
                self.integral += error * dt
                derivative = (error - self.prev_error) / dt
                self.prev_error = error
                
                # Filter derivative term
                derivative = derivative / (1 + self.params['N'] * dt)
                
                output = (self.params['P'] * error + 
                         self.params['I'] * self.integral + 
                         self.params['D'] * derivative)
                return [output]
            
            elif self.block_type == BlockType.TRANSFER_FUNCTION:
                # Convert to state space and compute
                if not hasattr(self, 'sys'):
                    self.sys = signal.TransferFunction(
                        self.params['numerator'],
                        self.params['denominator']
                    )
                    self.ss = self.sys.to_ss()
                
                # Continuous-time state-space simulation
                def state_derivative(t, x):
                    return self.ss.A @ x + self.ss.B * inputs[0]
                
                sol = solve_ivp(state_derivative, [t-dt, t], self.state, t_eval=[t])
                self.state = sol.y[:, -1]
                output = self.ss.C @ self.state + self.ss.D * inputs[0]
                return [output[0]]
            
            elif self.block_type == BlockType.STATE_SPACE:
                # Continuous-time state-space simulation
                A = np.array(self.params['A'])
                B = np.array(self.params['B'])
                C = np.array(self.params['C'])
                D = np.array(self.params['D'])
                
                def state_derivative(t, x):
                    return A @ x + B * inputs[0]
                
                sol = solve_ivp(state_derivative, [t-dt, t], self.state, t_eval=[t])
                self.state = sol.y[:, -1]
                output = C @ self.state + D * inputs[0]
                return [output[0,0]]
            
            elif self.block_type == BlockType.SWITCH:
                control = inputs[0]
                in1 = inputs[1]
                in2 = inputs[2]
                
                criteria = self.params['criteria']
                threshold = self.params['threshold']
                
                if criteria == '>=' and control >= threshold:
                    return [in1]
                elif criteria == '>' and control > threshold:
                    return [in1]
                elif criteria == '<=' and control <= threshold:
                    return [in1]
                elif criteria == '<' and control < threshold:
                    return [in1]
                elif criteria == '==' and control == threshold:
                    return [in1]
                elif criteria == '!=' and control != threshold:
                    return [in1]
                else:
                    return [in2]
            
            elif self.block_type == BlockType.RELATIONAL_OPERATOR:
                op = self.params['operator']
                if op == '==':
                    return [1.0 if inputs[0] == inputs[1] else 0.0]
                elif op == '!=':
                    return [1.0 if inputs[0] != inputs[1] else 0.0]
                elif op == '<':
                    return [1.0 if inputs[0] < inputs[1] else 0.0]
                elif op == '<=':
                    return [1.0 if inputs[0] <= inputs[1] else 0.0]
                elif op == '>':
                    return [1.0 if inputs[0] > inputs[1] else 0.0]
                elif op == '>=':
                    return [1.0 if inputs[0] >= inputs[1] else 0.0]
            
            elif self.block_type == BlockType.LOGICAL_OPERATOR:
                op = self.params['operator']
                if op == 'AND':
                    return [1.0 if inputs[0] and inputs[1] else 0.0]
                elif op == 'OR':
                    return [1.0 if inputs[0] or inputs[1] else 0.0]
                elif op == 'XOR':
                    return [1.0 if bool(inputs[0]) != bool(inputs[1]) else 0.0]
                elif op == 'NOT':
                    return [0.0 if inputs[0] else 1.0]
            
            elif self.block_type == BlockType.MATH_FUNCTION:
                func = self.params['function']
                if func == 'exp':
                    return [np.exp(inputs[0])]
                elif func == 'log':
                    return [np.log(inputs[0]) if inputs[0] > 0 else 0]
                elif func == 'sqrt':
                    return [np.sqrt(inputs[0]) if inputs[0] >= 0 else 0]
                elif func == 'sin':
                    return [np.sin(inputs[0])]
                elif func == 'cos':
                    return [np.cos(inputs[0])]
                elif func == 'tan':
                    return [np.tan(inputs[0])]
            
            elif self.block_type == BlockType.LOOKUP_TABLE:
                x = inputs[0]
                bp = self.params['breakpoints']
                table = self.params['table']
                method = self.params['method']
                
                # Simple linear interpolation
                if method == 'linear':
                    if x <= bp[0]:
                        return [table[0]]
                    elif x >= bp[-1]:
                        return [table[-1]]
                    else:
                        for i in range(1, len(bp)):
                            if x <= bp[i]:
                                alpha = (x - bp[i-1]) / (bp[i] - bp[i-1])
                                return [table[i-1] + alpha * (table[i] - table[i-1])]
                
                # Nearest neighbor
                elif method == 'nearest':
                    idx = np.argmin(np.abs(np.array(bp) - x))
                    return [table[idx]]
            
            elif self.block_type == BlockType.DATA_STORE:
                if len(self.data_store) < self.params['size']:
                    self.data_store.append(inputs[0])
                return [inputs[0]]
            
            elif self.block_type == BlockType.SCOPE:
                for i in range(len(inputs)):
                    if i < len(self.data):
                        self.data[i].append((t, inputs[i]))
                return []
            
            elif self.block_type == BlockType.XY_SCOPE:
                if len(inputs) >= 2:
                    self.data.append((inputs[0], inputs[1]))
                return []
            
            elif self.block_type == BlockType.FROM_FILE:
                if not self.file_data and self.params['filename']:
                    try:
                        data = np.loadtxt(self.params['filename'])
                        if len(data.shape) == 1:
                            self.file_data = data
                        else:
                            self.file_data = data[:, self.params['data_col']]
                    except:
                        self.file_data = []
                
                if self.file_data:
                    idx = min(int(t / dt), len(self.file_data) - 1)
                    return [self.file_data[idx]]
                return [0.0]
            
            elif self.block_type == BlockType.TO_FILE:
                if inputs:
                    self.file_data.append((t, inputs[0]))
                return []
            
            return [0.0]
        
        except Exception as e:
            print(f"Error computing block {self.name}: {e}")
            return [0.0]

class Port:
    def __init__(self, port_type, block, index):
        self.port_type = port_type
        self.block = block
        self.index = index
        self.connections = []

class Connection:
    def __init__(self, output_port, input_port):
        self.output_port = output_port
        self.input_port = input_port
        self.output_port.connections.append(self)
        self.input_port.connections.append(self)
        self.active = True

class Canvas(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(1000, 600)
        self.setMouseTracking(True)
        
        # Drawing properties
        self.grid_size = 20
        self.background_color = QColor(240, 240, 240)
        self.grid_color = QColor(220, 220, 220)
        self.block_color = QColor(70, 130, 180)
        self.selected_color = QColor(255, 165, 0)
        self.port_color = QColor(50, 50, 50)
        self.connection_color = QColor(30, 30, 30)
        self.connection_active_color = QColor(0, 100, 0)
        self.connection_inactive_color = QColor(150, 150, 150)
        
        # Simulation data
        self.blocks = []
        self.connections = []
        self.selected_block = None
        self.selected_connection = None
        self.dragging = False
        self.drag_offset = QPointF(0, 0)
        self.connecting = False
        self.connection_start = None
        self.connection_start_port = None
        self.simulation_running = False
        self.simulation_time = 0.0
        
        # Add initial blocks for demonstration
        sine_block = Block(BlockType.SINE_GENERATOR, QPointF(100, 100), "Sine1")
        gain_block = Block(BlockType.GAIN, QPointF(300, 100), "Gain1")
        scope_block = Block(BlockType.SCOPE, QPointF(500, 100), "Scope1")
        
        self.blocks.append(sine_block)
        self.blocks.append(gain_block)
        self.blocks.append(scope_block)
        
        # Create connections
        if sine_block.output_ports and gain_block.input_ports:
            connection1 = Connection(sine_block.output_ports[0], gain_block.input_ports[0])
            self.connections.append(connection1)
        
        if gain_block.output_ports and scope_block.input_ports:
            connection2 = Connection(gain_block.output_ports[0], scope_block.input_ports[0])
            self.connections.append(connection2)
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw background grid
        painter.fillRect(self.rect(), self.background_color)
        painter.setPen(QPen(self.grid_color, 1, Qt.DotLine))
        
        for x in range(0, self.width(), self.grid_size):
            painter.drawLine(x, 0, x, self.height())
        for y in range(0, self.height(), self.grid_size):
            painter.drawLine(0, y, self.width(), y)
        
        # Draw connections
        for connection in self.connections:
            start_pos = connection.output_port.block.get_port_position(
                connection.output_port, PortType.OUTPUT
            )
            end_pos = connection.input_port.block.get_port_position(
                connection.input_port, PortType.INPUT
            )
            
            # Choose color based on connection state
            if connection.active:
                color = self.connection_active_color
            else:
                color = self.connection_inactive_color
                
            painter.setPen(QPen(color, 2))
            
            # Draw a bezier curve for the connection
            ctrl1 = QPointF(start_pos.x() + 50, start_pos.y())
            ctrl2 = QPointF(end_pos.x() - 50, end_pos.y())
            
            path = QPainterPath(start_pos)
            path.cubicTo(ctrl1, ctrl2, end_pos)
            painter.drawPath(path)
            
            # Draw arrow at the end
            arrow_size = 8
            angle = np.arctan2(end_pos.y() - ctrl2.y(), end_pos.x() - ctrl2.x())
            
            arrow_p1 = end_pos + QPointF(
                -arrow_size * np.cos(angle - np.pi/6),
                -arrow_size * np.sin(angle - np.pi/6)
            )
            arrow_p2 = end_pos + QPointF(
                -arrow_size * np.cos(angle + np.pi/6),
                -arrow_size * np.sin(angle + np.pi/6)
            )
            
            arrow = QPolygonF([end_pos, arrow_p1, arrow_p2])
            painter.setBrush(color)
            painter.drawPolygon(arrow)
            
            # Draw connection name if it exists
            if hasattr(connection, 'name'):
                mid_point = QPointF((start_pos.x() + end_pos.x())/2, (start_pos.y() + end_pos.y())/2)
                painter.setPen(QPen(QColor(50, 50, 50), 1))
                painter.drawText(mid_point, connection.name)
        
        # Draw blocks
        for block in self.blocks:
            # Block rectangle
            is_selected = (block == self.selected_block)
            color = block.color
            if is_selected:
                painter.setPen(QPen(self.selected_color, 2))
            else:
                painter.setPen(QPen(QColor(30, 30, 30), 1))
                
            painter.setBrush(QBrush(color))
            is_selected = (block == self.selected_block)
            color = block.color
            if is_selected:
                painter.setPen(QPen(self.selected_color, 2))
            else:
                painter.setPen(QPen(QColor(30, 30, 30), 1))
                
            painter.setBrush(QBrush(color))

            # FIXED: Create QRectF object before drawing
            rect = QRectF(
                block.position.x(), block.position.y(), 
                block.size.x(), block.size.y()
            )
            painter.drawRoundedRect(rect, 5, 5)
            
            # Block title
            painter.setPen(QColor(255, 255, 255))
            font = QFont("Arial", 9)
            font.setBold(True)
            painter.setFont(font)
            title = block.name
            text_rect = QRectF(
                block.position.x(), block.position.y(), 
                block.size.x(), 20
            )
            painter.drawText(text_rect, Qt.AlignCenter, title)
            
            # Block type
            painter.setPen(QColor(200, 200, 200))
            font.setBold(False)
            font.setPointSize(8)
            painter.setFont(font)
            type_rect = QRectF(
                block.position.x(), block.position.y() + 20, 
                block.size.x(), 15
            )
            painter.drawText(type_rect, Qt.AlignCenter, block.block_type.value)
            
            # Input ports
            for port in block.input_ports:
                pos = block.get_port_position(port, PortType.INPUT)
                painter.setPen(QPen(self.port_color, 2))
                painter.setBrush(QBrush(QColor(200, 200, 200)))
                painter.drawEllipse(pos, 5, 5)
                # Port label
                painter.setPen(QPen(QColor(50, 50, 50), 1))
                painter.drawText(pos - QPointF(15, -5), f"In{port.index}")
            
            # Output ports
            for port in block.output_ports:
                pos = block.get_port_position(port, PortType.OUTPUT)
                painter.setPen(QPen(self.port_color, 2))
                painter.setBrush(QBrush(QColor(200, 200, 200)))
                painter.drawEllipse(pos, 5, 5)
                # Port label
                painter.setPen(QPen(QColor(50, 50, 50), 1))
                painter.drawText(pos + QPointF(5, 5), f"Out{port.index}")
        
        # Draw temporary connection line if in connecting mode
        if self.connecting and self.connection_start:
            painter.setPen(QPen(self.connection_active_color, 2, Qt.DashLine))
            painter.drawLine(self.connection_start, self.mouse_pos)
    
    def mousePressEvent(self, event):
        self.mouse_pos = event.pos()
        
        # Check if clicking on a port
        clicked_port = None
        for block in self.blocks:
            for port in block.input_ports + block.output_ports:
                port_pos = block.get_port_position(port, port.port_type)
                if (port_pos - self.mouse_pos).manhattanLength() < 10:
                    clicked_port = port
                    break
            if clicked_port:
                break
        
        if clicked_port:
            if clicked_port.port_type == PortType.OUTPUT:
                self.connecting = True
                self.connection_start = clicked_port.block.get_port_position(
                    clicked_port, PortType.OUTPUT
                )
                self.connection_start_port = clicked_port
            else:  # Input port
                if clicked_port.connections:
                    # Disconnect existing connection
                    connection = clicked_port.connections[0]
                    self.connections.remove(connection)
                    connection.output_port.connections.remove(connection)
                    clicked_port.connections.remove(connection)
                else:
                    # Start new connection from input port
                    self.connecting = True
                    self.connection_start = clicked_port.block.get_port_position(
                        clicked_port, PortType.INPUT
                    )
                    self.connection_start_port = clicked_port
            self.update()
            return
        
        # Check if clicking on a connection
        self.selected_connection = None
        for connection in self.connections:
            start_pos = connection.output_port.block.get_port_position(
                connection.output_port, PortType.OUTPUT
            )
            end_pos = connection.input_port.block.get_port_position(
                connection.input_port, PortType.INPUT
            )
            
            # Simple hit test - check distance to line
            # In a real app, you'd want to compute distance to the bezier curve
            line_vector = end_pos - start_pos
            mouse_vector = self.mouse_pos - start_pos
            line_length = np.sqrt(line_vector.x()**2 + line_vector.y()**2)
            
            if line_length > 0:
                projection = (mouse_vector.x() * line_vector.x() + mouse_vector.y() * line_vector.y()) / line_length
                if 0 <= projection <= line_length:
                    distance = abs(mouse_vector.x() * line_vector.y() - mouse_vector.y() * line_vector.x()) / line_length
                    if distance < 8:  # Hit tolerance
                        self.selected_connection = connection
                        self.selected_block = None
                        self.update()
                        return
        
        # Check if clicking on a block
        self.selected_block = None
        for block in reversed(self.blocks):  # Check from top to bottom
            rect = QRectF(block.position.x(), block.position.y(), block.size.x(), block.size.y())
            if rect.contains(self.mouse_pos):
                self.selected_block = block
                self.selected_connection = None
                self.dragging = True
                self.drag_offset = self.mouse_pos - block.position
                self.update()
                break
    
    def mouseMoveEvent(self, event):
        self.mouse_pos = event.pos()
        if self.dragging and self.selected_block:
            self.selected_block.position = self.mouse_pos - self.drag_offset
            self.update()
        elif self.connecting:
            self.update()
    
    def mouseReleaseEvent(self, event):
        if self.dragging:
            self.dragging = False
            return
        
        if self.connecting and self.connection_start:
            # Check if releasing on a port
            release_port = None
            for block in self.blocks:
                for port in block.input_ports + block.output_ports:
                    port_pos = block.get_port_position(port, port.port_type)
                    if (port_pos - event.pos()).manhattanLength() < 10:
                        release_port = port
                        break
                if release_port:
                    break
            
            if release_port:
                # Validate connection
                valid = False
                if self.connection_start_port.port_type == PortType.OUTPUT and release_port.port_type == PortType.INPUT:
                    valid = True
                elif self.connection_start_port.port_type == PortType.INPUT and release_port.port_type == PortType.OUTPUT:
                    valid = True
                
                if valid and self.connection_start_port.block != release_port.block:
                    # Create new connection
                    if self.connection_start_port.port_type == PortType.OUTPUT:
                        connection = Connection(self.connection_start_port, release_port)
                    else:
                        connection = Connection(release_port, self.connection_start_port)
                    self.connections.append(connection)
            
            self.connecting = False
            self.update()
    
    def add_block(self, block_type, position=None, name=None):
        if position is None:
            position = QPointF(100, 100)
        block = Block(block_type, position, name)
        self.blocks.append(block)
        self.selected_block = block
        self.update()
        return block
    
    def delete_selected(self):
        if self.selected_block:
            # Remove all connections to this block
            for port in self.selected_block.input_ports + self.selected_block.output_ports:
                for connection in port.connections[:]:
                    self.connections.remove(connection)
                    if connection.output_port in connection.input_port.connections:
                        connection.input_port.connections.remove(connection)
                    if connection.input_port in connection.output_port.connections:
                        connection.output_port.connections.remove(connection)
            
            # Remove the block
            self.blocks.remove(self.selected_block)
            self.selected_block = None
            self.update()
        
        elif self.selected_connection:
            self.connections.remove(self.selected_connection)
            self.selected_connection.output_port.connections.remove(self.selected_connection)
            self.selected_connection.input_port.connections.remove(self.selected_connection)
            self.selected_connection = None
            self.update()
    
    def run_simulation(self, duration=10.0, dt=0.01):
        # Reset simulation time
        self.simulation_time = 0.0
        
        # Reset block states
        for block in self.blocks:
            # Reset integrators
            if block.block_type == BlockType.INTEGRATOR:
                if hasattr(block, 'prev_input'):
                    del block.prev_input
                if hasattr(block, 'integral'):
                    del block.integral
            
            # Reset derivatives
            if block.block_type == BlockType.DERIVATIVE:
                if hasattr(block, 'prev_input'):
                    del block.prev_input
            
            # Reset PID controllers
            if block.block_type == BlockType.PID_CONTROLLER:
                if hasattr(block, 'integral'):
                    del block.integral
                if hasattr(block, 'prev_error'):
                    del block.prev_error
            
            # Reset transport delays
            if block.block_type == BlockType.TRANSPORT_DELAY:
                block.delay_buffer = []
            
            # Reset scopes
            if block.block_type == BlockType.SCOPE:
                block.data = [[] for _ in range(block.params['num_inputs'])]
            
            # Reset XY scopes
            if block.block_type == BlockType.XY_SCOPE:
                block.data = []
            
            # Reset file blocks
            if block.block_type == BlockType.TO_FILE:
                block.file_data = []
        
        # Run simulation
        time = 0
        while time < duration:
            # Store outputs for this time step
            outputs = {}
            
            # Topological sort for execution order
            execution_order = []
            remaining_blocks = self.blocks.copy()
            
            while remaining_blocks:
                # Find a block with no unresolved inputs
                found = False
                for block in remaining_blocks[:]:
                    # Source blocks can always be executed
                    if not block.input_ports:
                        execution_order.append(block)
                        remaining_blocks.remove(block)
                        found = True
                        continue
                    
                    # Check if all input ports have connections
                    all_connected = True
                    for port in block.input_ports:
                        if not port.connections:
                            all_connected = False
                            break
                    
                    if all_connected:
                        execution_order.append(block)
                        remaining_blocks.remove(block)
                        found = True
                
                if not found:
                    # Couldn't find a block to execute - probably a cycle
                    print("Warning: Potential cycle in the diagram")
                    execution_order.extend(remaining_blocks)
                    break
            
            for block in execution_order:
                # Gather inputs
                inputs = []
                for port in block.input_ports:
                    if port.connections:
                        source_port = port.connections[0].output_port
                        source_block = source_port.block
                        # Get output from source block (already computed this time step)
                        inputs.append(outputs.get(source_block, [0])[source_port.index])
                    else:
                        inputs.append(0.0)  # Default input
                
                # Compute block output
                result = block.compute(inputs, time, dt)
                
                # Store output for downstream blocks
                outputs[block] = result
            
            time += dt
        
        self.simulation_time = duration
        self.update()
    
    def realtime_simulation_step(self, dt):
        # Store outputs for this time step
        outputs = {}
        
        # Topological sort for execution order
        execution_order = []
        remaining_blocks = self.blocks.copy()
        
        while remaining_blocks:
            # Find a block with no unresolved inputs
            found = False
            for block in remaining_blocks[:]:
                # Source blocks can always be executed
                if not block.input_ports:
                    execution_order.append(block)
                    remaining_blocks.remove(block)
                    found = True
                    continue
                
                # Check if all input ports have connections
                all_connected = True
                for port in block.input_ports:
                    if not port.connections:
                        all_connected = False
                        break
                
                if all_connected:
                    execution_order.append(block)
                    remaining_blocks.remove(block)
                    found = True
            
            if not found:
                # Couldn't find a block to execute - probably a cycle
                execution_order.extend(remaining_blocks)
                break
        
        for block in execution_order:
            # Gather inputs
            inputs = []
            for port in block.input_ports:
                if port.connections:
                    source_port = port.connections[0].output_port
                    source_block = source_port.block
                    # Get output from source block (already computed this time step)
                    inputs.append(outputs.get(source_block, [0])[source_port.index])
                else:
                    inputs.append(0.0)  # Default input
            
            # Compute block output
            result = block.compute(inputs, self.simulation_time, dt)
            
            # Store output for downstream blocks
            outputs[block] = result
        
        self.simulation_time += dt
        self.update()
    
    def save_model(self, filename):
        """Save the current model to a JSON file"""
        model_data = {
            "blocks": [],
            "connections": []
        }
        
        # Save blocks
        for block in self.blocks:
            block_data = {
                "id": block.id,
                "type": block.block_type.name,
                "name": block.name,
                "position": [block.position.x(), block.position.y()],
                "params": block.params
            }
            model_data["blocks"].append(block_data)
        
        # Save connections
        for connection in self.connections:
            conn_data = {
                "from_block": connection.output_port.block.id,
                "from_port": connection.output_port.index,
                "to_block": connection.input_port.block.id,
                "to_port": connection.input_port.index
            }
            model_data["connections"].append(conn_data)
        
        # Write to file
        with open(filename, 'w') as f:
            json.dump(model_data, f, indent=2)
    
    def load_model(self, filename):
        """Load a model from a JSON file"""
        try:
            with open(filename, 'r') as f:
                model_data = json.load(f)
            
            # Clear current model
            self.blocks = []
            self.connections = []
            
            # Create blocks
            id_map = {}  # Map old IDs to new block instances
            for block_data in model_data["blocks"]:
                block_type = BlockType[block_data["type"]]
                position = QPointF(block_data["position"][0], block_data["position"][1])
                block = self.add_block(block_type, position, block_data["name"])
                block.params = block_data["params"]
                id_map[block_data["id"]] = block
            
            # Create connections
            for conn_data in model_data["connections"]:
                from_block = id_map[conn_data["from_block"]]
                to_block = id_map[conn_data["to_block"]]
                
                if from_block.output_ports and to_block.input_ports:
                    from_port = from_block.output_ports[conn_data["from_port"]]
                    to_port = to_block.input_ports[conn_data["to_port"]]
                    connection = Connection(from_port, to_port)
                    self.connections.append(connection)
            
            self.update()
            return True
        except Exception as e:
            print(f"Error loading model: {e}")
            return False

class ParameterDialog(QDialog):
    def __init__(self, block, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Parameters: {block.name}")
        self.block = block
        self.setMinimumSize(400, 300)
        
        layout = QVBoxLayout()
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        
        # Main parameters tab
        main_tab = QWidget()
        main_layout = QFormLayout(main_tab)
        
        self.edits = {}
        for param, value in block.params.items():
            if isinstance(value, float):
                edit = QDoubleSpinBox()
                edit.setRange(-1e9, 1e9)
                edit.setDecimals(6)
                edit.setValue(value)
                self.edits[param] = edit
                main_layout.addRow(param, edit)
            elif isinstance(value, int):
                edit = QSpinBox()
                edit.setRange(-1000000, 1000000)
                edit.setValue(value)
                self.edits[param] = edit
                main_layout.addRow(param, edit)
            elif isinstance(value, list):
                if all(isinstance(x, (int, float)) for x in value):
                    # Numeric list
                    edit = QLineEdit(", ".join(map(str, value)))
                    self.edits[param] = edit
                    main_layout.addRow(param, edit)
                else:
                    # Other list types
                    edit = QLineEdit(str(value))
                    self.edits[param] = edit
                    main_layout.addRow(param, edit)
            elif isinstance(value, str):
                if param == 'signal_type' or param == 'noise_type' or param == 'function' or param == 'operator':
                    combo = QComboBox()
                    if param == 'signal_type':
                        combo.addItems(['sine', 'square', 'sawtooth', 'triangle'])
                    elif param == 'noise_type':
                        combo.addItems(['uniform', 'gaussian'])
                    elif param == 'function':
                        combo.addItems(['exp', 'log', 'sqrt', 'sin', 'cos', 'tan'])
                    elif param == 'operator':
                        if block.block_type == BlockType.RELATIONAL_OPERATOR:
                            combo.addItems(['==', '!=', '<', '<=', '>', '>='])
                        elif block.block_type == BlockType.LOGICAL_OPERATOR:
                            combo.addItems(['AND', 'OR', 'XOR', 'NOT'])
                    combo.setCurrentText(value)
                    self.edits[param] = combo
                    main_layout.addRow(param, combo)
                else:
                    edit = QLineEdit(value)
                    self.edits[param] = edit
                    main_layout.addRow(param, edit)
            else:
                edit = QLineEdit(str(value))
                self.edits[param] = edit
                main_layout.addRow(param, edit)
        
        self.tabs.addTab(main_tab, "Parameters")
        
        # Advanced tab for transfer function and state space
        if block.block_type in [BlockType.TRANSFER_FUNCTION, BlockType.STATE_SPACE]:
            advanced_tab = QWidget()
            advanced_layout = QVBoxLayout(advanced_tab)
            
            if block.block_type == BlockType.TRANSFER_FUNCTION:
                group = QGroupBox("Transfer Function Coefficients")
                form = QFormLayout(group)
                
                num_edit = QLineEdit(", ".join(map(str, block.params['numerator'])))
                den_edit = QLineEdit(", ".join(map(str, block.params['denominator'])))
                init_edit = QLineEdit(", ".join(map(str, block.params['initial'])))
                
                form.addRow("Numerator:", num_edit)
                form.addRow("Denominator:", den_edit)
                form.addRow("Initial Conditions:", init_edit)
                
                self.edits['numerator'] = num_edit
                self.edits['denominator'] = den_edit
                self.edits['initial'] = init_edit
                
                advanced_layout.addWidget(group)
            
            elif block.block_type == BlockType.STATE_SPACE:
                group = QGroupBox("State-Space Matrices")
                form = QFormLayout(group)
                
                # Create table for A matrix
                a_label = QLabel("A Matrix:")
                a_table = QTableWidget()
                a_matrix = np.array(block.params['A'])
                a_table.setRowCount(a_matrix.shape[0])
                a_table.setColumnCount(a_matrix.shape[1])
                for i in range(a_matrix.shape[0]):
                    for j in range(a_matrix.shape[1]):
                        item = QTableWidgetItem(str(a_matrix[i, j]))
                        a_table.setItem(i, j, item)
                a_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
                
                # Create table for B matrix
                b_label = QLabel("B Matrix:")
                b_table = QTableWidget()
                b_matrix = np.array(block.params['B'])
                b_table.setRowCount(b_matrix.shape[0])
                b_table.setColumnCount(b_matrix.shape[1])
                for i in range(b_matrix.shape[0]):
                    for j in range(b_matrix.shape[1]):
                        item = QTableWidgetItem(str(b_matrix[i, j]))
                        b_table.setItem(i, j, item)
                b_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
                
                # Create table for C matrix
                c_label = QLabel("C Matrix:")
                c_table = QTableWidget()
                c_matrix = np.array(block.params['C'])
                c_table.setRowCount(c_matrix.shape[0])
                c_table.setColumnCount(c_matrix.shape[1])
                for i in range(c_matrix.shape[0]):
                    for j in range(c_matrix.shape[1]):
                        item = QTableWidgetItem(str(c_matrix[i, j]))
                        c_table.setItem(i, j, item)
                c_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
                
                # Create table for D matrix
                d_label = QLabel("D Matrix:")
                d_table = QTableWidget()
                d_matrix = np.array(block.params['D'])
                d_table.setRowCount(d_matrix.shape[0])
                d_table.setColumnCount(d_matrix.shape[1])
                for i in range(d_matrix.shape[0]):
                    for j in range(d_matrix.shape[1]):
                        item = QTableWidgetItem(str(d_matrix[i, j]))
                        d_table.setItem(i, j, item)
                d_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
                
                # Initial conditions
                init_label = QLabel("Initial Conditions:")
                init_edit = QLineEdit(", ".join(map(str, block.params['initial'])))
                
                form.addRow(a_label)
                form.addRow(a_table)
                form.addRow(b_label)
                form.addRow(b_table)
                form.addRow(c_label)
                form.addRow(c_table)
                form.addRow(d_label)
                form.addRow(d_table)
                form.addRow(init_label, init_edit)
                
                self.edits['A'] = a_table
                self.edits['B'] = b_table
                self.edits['C'] = c_table
                self.edits['D'] = d_table
                self.edits['initial'] = init_edit
                
                advanced_layout.addWidget(group)
            
            self.tabs.addTab(advanced_tab, "Advanced")
        
        # Block name
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Block Name:"))
        name_edit = QLineEdit(block.name)
        self.edits['name'] = name_edit
        name_layout.addWidget(name_edit)
        layout.addLayout(name_layout)
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
    
    def get_params(self):
        params = {}
        for param, edit in self.edits.items():
            if param == 'name':
                continue  # Handled separately
                
            if isinstance(edit, QDoubleSpinBox):
                params[param] = edit.value()
            elif isinstance(edit, QSpinBox):
                params[param] = edit.value()
            elif isinstance(edit, QComboBox):
                params[param] = edit.currentText()
            elif isinstance(edit, QLineEdit):
                if param in ['numerator', 'denominator', 'initial']:
                    try:
                        # Parse comma-separated list of floats
                        params[param] = [float(x.strip()) for x in edit.text().split(',')]
                    except:
                        params[param] = self.block.params[param]
                else:
                    # Try to convert to number if possible
                    text = edit.text()
                    try:
                        if '.' in text:
                            params[param] = float(text)
                        else:
                            params[param] = int(text)
                    except ValueError:
                        params[param] = text
            elif isinstance(edit, QTableWidget):
                # Handle matrix tables
                rows = edit.rowCount()
                cols = edit.columnCount()
                matrix = []
                for i in range(rows):
                    row = []
                    for j in range(cols):
                        item = edit.item(i, j)
                        if item:
                            try:
                                row.append(float(item.text()))
                            except:
                                row.append(0.0)
                        else:
                            row.append(0.0)
                    matrix.append(row)
                params[param] = matrix
        
        # Update block name
        if 'name' in self.edits:
            self.block.name = self.edits['name'].text()
        
        return params

class PlotWidget(FigureCanvas):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        super().__init__(self.fig)
        self.setParent(parent)
        
        self.ax = self.fig.add_subplot(111)
        self.ax.grid(True)
        self.ax.set_xlabel('Time (s)')
        self.ax.set_ylabel('Value')
        self.ax.set_title('Simulation Results')
        
    def plot(self, data):
        """Plot simulation data"""
        self.ax.clear()
        
        if isinstance(data, list) and data:
            if isinstance(data[0], tuple) and len(data[0]) == 2:
                # Single signal: [(t, y)]
                t, y = zip(*data)
                self.ax.plot(t, y, 'b-', linewidth=2)
            elif isinstance(data[0], list):
                # Multiple signals: [[(t, y1)], [(t, y2)], ...]
                colors = ['b', 'g', 'r', 'c', 'm', 'y', 'k']
                for i, signal in enumerate(data):
                    if signal:
                        t, y = zip(*signal)
                        self.ax.plot(t, y, f'{colors[i % len(colors)]}-', linewidth=2, label=f'Signal {i+1}')
                if len(data) > 1:
                    self.ax.legend()
        
        self.ax.grid(True)
        self.ax.set_xlabel('Time (s)')
        self.ax.set_ylabel('Value')
        self.ax.set_title('Simulation Results')
        self.draw()
    
    def plot_xy(self, data):
        """Plot XY data"""
        self.ax.clear()
        
        if data:
            x, y = zip(*data)
            self.ax.plot(x, y, 'b-', linewidth=1)
            self.ax.plot(x, y, 'ro', markersize=2)
        
        self.ax.grid(True)
        self.ax.set_xlabel('X')
        self.ax.set_ylabel('Y')
        self.ax.set_title('XY Plot')
        self.draw()

class SimulinkApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Advanced Simulink-like Simulator")
        self.setGeometry(100, 100, 1400, 900)
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # Create splitter for canvas and plot
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        # Create canvas (left)
        self.canvas = Canvas()
        splitter.addWidget(self.canvas)
        
        # Create plot area (right)
        plot_dock = QDockWidget("Simulation Results", self)
        self.plot_widget = PlotWidget()
        self.plot_tabs = QTabWidget()
        self.plot_tabs.addTab(self.plot_widget, "Time Series")
        
        # Add XY plot tab
        self.xy_plot_widget = PlotWidget()
        self.plot_tabs.addTab(self.xy_plot_widget, "XY Plot")
        
        # Add data table tab
        self.data_table = QTableWidget()
        self.data_table.setColumnCount(3)
        self.data_table.setHorizontalHeaderLabels(["Time", "Signal 1", "Signal 2"])
        self.plot_tabs.addTab(self.data_table, "Data Table")
        
        plot_dock.setWidget(self.plot_tabs)
        self.addDockWidget(Qt.RightDockWidgetArea, plot_dock)
        
        # Create block library (left dock)
        block_library = QDockWidget("Block Library", self)
        self.block_list = QListWidget()
        
        # Categorize blocks
        categories = {
            "Sources": [
                BlockType.SINE_GENERATOR, BlockType.SQUARE_GENERATOR, BlockType.PULSE_GENERATOR,
                BlockType.RAMP_GENERATOR, BlockType.SIGNAL_GENERATOR, BlockType.NOISE_GENERATOR,
                BlockType.CONSTANT, BlockType.FROM_FILE
            ],
            "Sinks": [
                BlockType.SCOPE, BlockType.XY_SCOPE, BlockType.TO_FILE, BlockType.DATA_STORE
            ],
            "Continuous": [
                BlockType.INTEGRATOR, BlockType.DERIVATIVE, BlockType.TRANSFER_FUNCTION,
                BlockType.STATE_SPACE, BlockType.PID_CONTROLLER
            ],
            "Discrete": [
                BlockType.TRANSPORT_DELAY, BlockType.QUANTIZER
            ],
            "Math Operations": [
                BlockType.GAIN, BlockType.ADDER, BlockType.MULTIPLIER, BlockType.DIVIDER,
                BlockType.ABSOLUTE_VALUE, BlockType.SATURATION, BlockType.DEAD_ZONE,
                BlockType.MATH_FUNCTION, BlockType.LOOKUP_TABLE
            ],
            "Logic and Bit Operations": [
                BlockType.SWITCH, BlockType.RELATIONAL_OPERATOR, BlockType.LOGICAL_OPERATOR
            ],
            "Subsystems": [
                BlockType.SUBSYSTEM
            ]
        }
        
        # Add categories to block library
        for category, blocks in categories.items():
            self.block_list.addItem(f"--- {category} ---")
            for block_type in blocks:
                self.block_list.addItem(block_type.value)
        
        self.block_list.currentRowChanged.connect(self.block_selected)
        block_library.setWidget(self.block_list)
        self.addDockWidget(Qt.LeftDockWidgetArea, block_library)
        
        # Create toolbar
        toolbar = QToolBar("Main Toolbar")
        self.addToolBar(toolbar)
        
        # Add actions with icons
        run_action = QAction(QIcon(":/icons/run.png"), "Run Simulation", self)
        run_action.triggered.connect(self.run_simulation)
        toolbar.addAction(run_action)
        
        realtime_action = QAction(QIcon(":/icons/realtime.png"), "Real-time Simulation", self)
        realtime_action.triggered.connect(self.toggle_realtime)
        toolbar.addAction(realtime_action)
        
        stop_action = QAction(QIcon(":/icons/stop.png"), "Stop Simulation", self)
        stop_action.triggered.connect(self.stop_simulation)
        toolbar.addAction(stop_action)
        
        toolbar.addSeparator()
        
        delete_action = QAction(QIcon(":/icons/delete.png"), "Delete Selected", self)
        delete_action.triggered.connect(self.canvas.delete_selected)
        toolbar.addAction(delete_action)
        
        param_action = QAction(QIcon(":/icons/params.png"), "Parameters", self)
        param_action.triggered.connect(self.edit_parameters)
        toolbar.addAction(param_action)
        
        toolbar.addSeparator()
        
        save_action = QAction(QIcon(":/icons/save.png"), "Save Model", self)
        save_action.triggered.connect(self.save_model)
        toolbar.addAction(save_action)
        
        load_action = QAction(QIcon(":/icons/load.png"), "Load Model", self)
        load_action.triggered.connect(self.load_model)
        toolbar.addAction(load_action)
        
        toolbar.addSeparator()
        
        zoom_in_action = QAction(QIcon(":/icons/zoom_in.png"), "Zoom In", self)
        zoom_in_action.triggered.connect(self.zoom_in)
        toolbar.addAction(zoom_in_action)
        
        zoom_out_action = QAction(QIcon(":/icons/zoom_out.png"), "Zoom Out", self)
        zoom_out_action.triggered.connect(self.zoom_out)
        toolbar.addAction(zoom_out_action)
        
        # Simulation control panel
        sim_panel = QWidget()
        sim_layout = QHBoxLayout(sim_panel)
        
        self.duration_spin = QDoubleSpinBox()
        self.duration_spin.setRange(0.1, 1000)
        self.duration_spin.setValue(10.0)
        self.duration_spin.setSuffix(" s")
        sim_layout.addWidget(QLabel("Duration:"))
        sim_layout.addWidget(self.duration_spin)
        
        self.dt_spin = QDoubleSpinBox()
        self.dt_spin.setRange(0.001, 1.0)
        self.dt_spin.setValue(0.01)
        self.dt_spin.setSuffix(" s")
        sim_layout.addWidget(QLabel("Time Step:"))
        sim_layout.addWidget(self.dt_spin)
        
        toolbar.addWidget(sim_panel)
        
        # Status bar
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("Ready")
        
        # Realtime simulation timer
        self.realtime_timer = QTimer()
        self.realtime_timer.timeout.connect(self.realtime_step)
        self.realtime_mode = False
    
    def block_selected(self, index):
        text = self.block_list.currentItem().text()
        if not text.startswith("---"):
            # Find the block type from the text
            for block_type in BlockType:
                if block_type.value == text:
                    self.canvas.add_block(block_type)
                    break
    
    def run_simulation(self):
        duration = self.duration_spin.value()
        dt = self.dt_spin.value()
        
        start_time = time.time()
        self.canvas.run_simulation(duration, dt)
        elapsed = time.time() - start_time
        
        # Update plots
        self.update_plots()
        
        self.status_bar.showMessage(f"Simulation completed in {elapsed:.2f} seconds")
    
    def toggle_realtime(self):
        if self.realtime_mode:
            self.realtime_mode = False
            self.realtime_timer.stop()
            self.status_bar.showMessage("Real-time simulation stopped")
        else:
            self.realtime_mode = True
            dt = self.dt_spin.value()
            self.realtime_timer.start(int(dt * 1000))
            self.status_bar.showMessage("Real-time simulation running")
    
    def realtime_step(self):
        dt = self.dt_spin.value()
        self.canvas.realtime_simulation_step(dt)
        self.update_plots()
    
    def stop_simulation(self):
        if self.realtime_mode:
            self.toggle_realtime()
        self.status_bar.showMessage("Simulation stopped")
    
    def update_plots(self):
        # Find and plot the first scope block
        for block in self.canvas.blocks:
            if block.block_type == BlockType.SCOPE and hasattr(block, 'data') and block.data:
                self.plot_widget.plot(block.data)
                # Update data table
                self.update_data_table(block.data)
                break
            
            if block.block_type == BlockType.XY_SCOPE and hasattr(block, 'data') and block.data:
                self.xy_plot_widget.plot_xy(block.data)
                break
    
    def update_data_table(self, data):
        if not data:
            return
        
        # For simplicity, just show the first signal
        signal_data = data[0] if isinstance(data[0], list) else data
        num_rows = min(100, len(signal_data))  # Limit to 100 rows
        
        self.data_table.setRowCount(num_rows)
        self.data_table.setColumnCount(2)
        self.data_table.setHorizontalHeaderLabels(["Time", "Value"])
        
        for i in range(num_rows):
            t, value = signal_data[i]
            self.data_table.setItem(i, 0, QTableWidgetItem(f"{t:.4f}"))
            self.data_table.setItem(i, 1, QTableWidgetItem(f"{value:.4f}"))
    
    def edit_parameters(self):
        if self.canvas.selected_block:
            dialog = ParameterDialog(self.canvas.selected_block, self)
            if dialog.exec_() == QDialog.Accepted:
                new_params = dialog.get_params()
                self.canvas.selected_block.params.update(new_params)
                self.status_bar.showMessage(f"Parameters updated for {self.canvas.selected_block.name}")
    
    def save_model(self):
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Model", "", "JSON Files (*.json)"
        )
        if filename:
            if not filename.endswith('.json'):
                filename += '.json'
            self.canvas.save_model(filename)
            self.status_bar.showMessage(f"Model saved to {filename}")
    
    def load_model(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, "Load Model", "", "JSON Files (*.json)"
        )
        if filename:
            if self.canvas.load_model(filename):
                self.status_bar.showMessage(f"Model loaded from {filename}")
            else:
                QMessageBox.warning(self, "Load Error", "Failed to load the model file")
    
    def zoom_in(self):
        # For a real application, you'd need to implement canvas zooming
        self.status_bar.showMessage("Zoom In - Not implemented")
    
    def zoom_out(self):
        # For a real application, you'd need to implement canvas zooming
        self.status_bar.showMessage("Zoom Out - Not implemented")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SimulinkApp()
    window.show()
    sys.exit(app.exec_())