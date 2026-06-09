import numpy as np
import sympy as sp
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QSplitter, QTabWidget, QGroupBox, QTextEdit, QPushButton,
                            QLabel, QLineEdit, QComboBox, QSlider, QCheckBox, QDialog,
                            QDialogButtonBox, QFormLayout, QMessageBox, QListWidget,
                            QTableWidget, QTableWidgetItem, QHeaderView, QTreeWidget,
                            QTreeWidgetItem, QStackedWidget, QToolBox, QSpinBox,
                            QDoubleSpinBox, QProgressBar,QListWidgetItem)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QColor, QPen, QBrush, QFont, QPalette, QLinearGradient
import matplotlib.gridspec as gridspec
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d import Axes3D
from matplotlib import cm
from collections import defaultdict
import random
import re
import math
import cmath
import numbers
import uuid
import time
from scipy.special import binom

# 修复Tensor导入问题
try:
    from sympy.tensor.tensor import TensorIndexType, tensor_indices, TensorHead
except ImportError:
    from sympy.tensor import TensorIndexType, tensor_indices, TensorHead

from sympy.tensor.array import Array
from sympy.physics.quantum import Dagger, Commutator, AntiCommutator
from sympy.physics.quantum import Operator, HermitianOperator, UnitaryOperator

class HyperBaseSystem:
    """超进制系统：支持量子、分形、张量等抽象进制"""
    def __init__(self):
        # 基础进制系统
        self.bases = {
            'integer': [2, 8, 10, 16, 60],
            'fractional': [1.5, 2.718, 3.14, 0.618, 1.414],
            'negative': [-2, -8, -10, -16],
            'complex': [1j, -1j, 0.5+0.5j, 0.618+1.618j],
            'irrational': [sp.pi, sp.E, sp.GoldenRatio, sp.sqrt(2)],
            'abstract': ['ℵ', '∞', '∇', 'Δ', 'Ψ', 'Ω', 'Σ', 'Π'],
            'quantum': ['|0>', '|1>', '|+>', '|->', '|ψ>'],
            'tensor': ['T³', 'T⁴', 'T⁵', 'T∞'],
            'fractal': ['Fⁿ', 'Fᵈ', 'Fᶜ', 'F∞']
        }
        
        # 进制转换规则
        self.conversion_rules = {}
        self._init_conversion_rules()
        
        # 进制代数结构
        self.base_algebra = defaultdict(dict)
        
        # 抽象进制映射
        self.abstract_base_map = {
            'ℵ': self.aleph_transform,
            '∞': self.infinity_transform,
            '∇': self.fractal_transform,
            'Δ': self.dirac_transform,
            'Ψ': self.quantum_state_transform,
            'Ω': self.omega_transform,
            'Σ': self.sigma_transform,
            'Π': self.pi_transform
        }
        
        # 量子态表示
        self.quantum_states = {}
        self._init_quantum_states()
        
        # 张量基础
        self._init_tensor_system()
        
        # 分形系统
        self.fractal_dimensions = {}
        
        # 超现实数系统
        self.surreal_numbers = {}
    
    def _init_conversion_rules(self):
        """初始化进制转换规则"""
        # 整数进制转换
        for base in self.bases['integer']:
            self.conversion_rules[(base, 10)] = lambda n, b=base: self.int_to_base(n, b)
            self.conversion_rules[(10, base)] = lambda n, b=base: self.base_to_int(n, b)
        
        # 分数进制转换
        for base in self.bases['fractional']:
            self.conversion_rules[(base, 10)] = lambda n, b=base: self.frac_to_decimal(n, b)
            self.conversion_rules[(10, base)] = lambda n, b=base: self.decimal_to_frac(n, b)
        
        # 负进制转换
        for base in self.bases['negative']:
            self.conversion_rules[(base, 10)] = lambda n, b=base: self.neg_base_to_decimal(n, b)
            self.conversion_rules[(10, base)] = lambda n, b=base: self.decimal_to_neg_base(n, b)
        
        # 复数进制转换
        for base in self.bases['complex']:
            self.conversion_rules[(base, 10)] = lambda n, b=base: self.complex_to_decimal(n, b)
            self.conversion_rules[(10, base)] = lambda n, b=base: self.decimal_to_complex(n, b)
    
    def _init_quantum_states(self):
        """初始化量子态表示"""
        self.quantum_states = {
            '|0>': np.array([1, 0]),
            '|1>': np.array([0, 1]),
            '|+>': np.array([1, 1])/np.sqrt(2),
            '|->': np.array([1, -1])/np.sqrt(2),
            '|ψ>': lambda alpha, beta: np.array([alpha, beta])
        }
    
    def _init_tensor_system(self):
        """初始化张量系统"""
        self.T = TensorIndexType('T', dummy_name='L')
        # 使用TensorHead替代tensor_heads
        self.tensor_heads = {
            'T³': TensorHead('T^3', [self.T, self.T, self.T]),
            'T⁴': TensorHead('T^4', [self.T, self.T, self.T, self.T]),
            'T⁵': TensorHead('T^5', [self.T]*5),
            'T∞': TensorHead('T^∞', [self.T])
        }
    
    def int_to_base(self, n, base):
        """整数到任意进制转换"""
        # 优化大数处理
        if abs(n) > 1e15:
            return self.large_number_representation(n, base)
        
        # 标准转换
        if n == 0:
            return "0"
        
        digits = []
        num = abs(n)
        while num:
            num, r = divmod(num, base)
            digits.append(str(r) if r < 10 else chr(ord('A') + r - 10))
        
        result = ''.join(digits[::-1])
        return ('-' if n < 0 else '') + result
    
    def large_number_representation(self, n, base):
        """大数优化表示"""
        log_val = math.log(abs(n), base)
        exponent = math.floor(log_val)
        mantissa = abs(n) / (base ** exponent)
        return f"{mantissa:.4f}×{base}^{exponent}"
    
    def base_to_int(self, n_str, base):
        """任意进制到整数转换"""
        # 处理科学计数法表示
        if '×' in n_str and '^' in n_str:
            parts = n_str.split('×')
            if len(parts) == 2:
                mantissa = float(parts[0])
                exp_part = parts[1].split('^')
                if len(exp_part) == 2 and exp_part[0] == str(base):
                    exponent = int(exp_part[1])
                    return mantissa * (base ** exponent)
        
        # 标准转换
        n_str = n_str.upper()
        valid_digits = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"[:base]
        
        if any(d not in valid_digits for d in n_str.lstrip('-')):
            raise ValueError(f"Invalid digit for base {base}")
        
        sign = -1 if n_str.startswith('-') else 1
        num_str = n_str.lstrip('-')
        
        result = 0
        for i, digit in enumerate(num_str[::-1]):
            d_val = ord(digit) - ord('0') if digit <= '9' else ord(digit) - ord('A') + 10
            result += d_val * (base ** i)
        
        return sign * result
    
    def frac_to_decimal(self, n_str, base):
        """分数进制到十进制转换"""
        # 处理科学计数法
        if '×' in n_str and '^' in n_str:
            return self.base_to_int(n_str, base)
        
        # 标准处理
        if '.' not in n_str:
            return self.base_to_int(n_str, base)
        
        int_part, frac_part = n_str.split('.')
        integer_val = self.base_to_int(int_part, base)
        
        fractional_val = 0
        for i, digit in enumerate(frac_part):
            d_val = ord(digit) - ord('0') if digit <= '9' else ord(digit) - ord('A') + 10
            fractional_val += d_val * (base ** (-i-1))
        
        return integer_val + fractional_val
    
    def decimal_to_frac(self, n, base):
        """十进制到分数进制转换"""
        # 大数优化
        if abs(n) > 1e15:
            return self.large_number_representation(n, base)
        
        # 标准转换
        integer = int(abs(n))
        sign = '-' if n < 0 else ''
        
        int_part = self.int_to_base(integer, base) if integer > 0 else "0"
        
        fractional = abs(n) - integer
        frac_digits = []
        precision = 20  # 更高精度
        
        for _ in range(precision):
            fractional *= base
            digit = int(fractional)
            fractional -= digit
            frac_digits.append(str(digit) if digit < 10 else chr(ord('A') + digit - 10))
            if abs(fractional) < 1e-10:
                break
        
        frac_str = ''.join(frac_digits)
        return sign + int_part + ('.' + frac_str if frac_str else '')
    
    def neg_base_to_decimal(self, n_str, base):
        """负进制到十进制转换"""
        base = abs(base)
        n_str = n_str.upper()
        sign = -1 if n_str.startswith('-') else 1
        num_str = n_str.lstrip('-')
        
        result = 0
        for i, digit in enumerate(num_str[::-1]):
            d_val = ord(digit) - ord('0') if digit <= '9' else ord(digit) - ord('A') + 10
            result += d_val * ((-base) ** i)
        
        return sign * result
    
    def decimal_to_neg_base(self, n, base):
        """十进制到负进制转换"""
        base = abs(base)
        if n == 0:
            return "0"
        
        digits = []
        num = abs(n)
        while num:
            num, r = divmod(num, base)
            if r < 0:
                r -= base
                num += 1
            digits.append(str(r) if r < 10 else chr(ord('A') + r - 10))
        
        result = ''.join(digits[::-1])
        return ('-' if n < 0 else '') + result
    
    def complex_to_decimal(self, n_str, base):
        """复数进制到十进制转换"""
        # 分离实部和虚部
        if '+' in n_str or '-' in n_str:
            parts = re.split(r'([+-])', n_str)
            real_part = parts[0]
            imag_part = parts[2] if len(parts) > 2 else ""
            
            # 处理虚部符号
            if parts[1] == '-':
                imag_sign = -1
            else:
                imag_sign = 1
            
            real_val = self.frac_to_decimal(real_part, base.real)
            imag_val = self.frac_to_decimal(imag_part.rstrip('i'), base.imag) * imag_sign
            
            return complex(real_val, imag_val)
        
        # 纯实数或纯虚数
        if 'i' in n_str:
            imag_val = self.frac_to_decimal(n_str.rstrip('i'), base.imag)
            return complex(0, imag_val)
        
        real_val = self.frac_to_decimal(n_str, base.real)
        return complex(real_val, 0)
    
    def decimal_to_complex(self, n, base):
        """十进制到复数进制转换"""
        real_part = self.decimal_to_frac(n.real, base.real)
        imag_part = self.decimal_to_frac(abs(n.imag), base.imag)
        
        if n.imag < 0:
            sign = '-'
        else:
            sign = '+'
        
        return f"{real_part}{sign}{imag_part}i"
    
    def aleph_transform(self, n):
        """阿列夫进制转换：处理无限集合大小"""
        if n == 0:
            return "ℵ₀"
        
        # 无限集合的基数
        if n < 0:
            sign = '-'
            abs_n = abs(n)
        else:
            sign = ''
            abs_n = n
        
        if abs_n < 1:
            return f"{sign}ℵ₋∞"
        elif abs_n == float('inf'):
            return f"{sign}ℵ_∞"
        
        # 使用对数尺度映射到阿列夫数
        aleph_index = math.floor(math.log(abs_n))
        return f"{sign}ℵ_{aleph_index}"
    
    def infinity_transform(self, n):
        """无限进制转换：基于渐近行为"""
        if n == 0:
            return "0"
        
        sign = '-' if n < 0 else ''
        abs_n = abs(n)
        
        # 渐近展开系数
        log_val = math.log(abs_n) if abs_n > 0 else 0
        return f"{sign}∞({log_val:.4f})"
    
    def fractal_transform(self, n):
        """分形进制转换：基于分形维度"""
        if n == 0:
            return "0"
        
        sign = '-' if n < 0 else ''
        abs_n = abs(n)
        
        # 计算分形维度
        fractal_dim = math.log(abs_n) / math.log(3)  # 三分形基准
        return f"{sign}F^{fractal_dim:.4f}"
    
    def dirac_transform(self, n):
        """狄拉克进制转换：量子概率幅"""
        if n == 0:
            return "0"
        
        sign = '-' if n < 0 else ''
        abs_n = abs(n)
        
        # 概率幅表示
        prob_amp = math.sqrt(abs_n)
        return f"{sign}Δ|{prob_amp:.4f}|"
    
    def quantum_state_transform(self, n):
        """量子态进制转换"""
        # 映射到Bloch球面坐标
        r = abs(n)
        theta = (n.real % (2*math.pi)) if n != 0 else 0
        phi = (n.imag % (2*math.pi)) if n != 0 else 0
        
        return f"|Ψ(r={r:.2f}, θ={theta:.2f}, φ={phi:.2f})>"
    
    def omega_transform(self, n):
        """Omega进制：超现实数表示"""
        if n == 0:
            return "{ | }"
        
        # 超现实数表示
        if n > 0:
            return f"{{ | {n-1} }}"
        else:
            return f"{{ {n+1} | }}"
    
    def sigma_transform(self, n):
        """Sigma进制：求和表示"""
        if n == 0:
            return "Σ(0)"
        
        # 整数部分求和表示
        int_part = int(n)
        if int_part > 0:
            terms = [str(i) for i in range(1, int_part+1)]
            return f"Σ({'+'.join(terms)})"
        else:
            terms = [str(i) for i in range(int_part, 0)]
            return f"Σ({'+'.join(terms)})"
    
    def pi_transform(self, n):
        """Pi进制：乘积表示"""
        if n == 0:
            return "Π(0)"
        if n == 1:
            return "Π(1)"
        
        # 整数部分乘积表示
        int_part = int(abs(n))
        sign = '-' if n < 0 else ''
        
        if int_part > 1:
            terms = [str(i) for i in range(2, int_part+1)]
            return f"{sign}Π({'×'.join(terms)})"
        return sign + str(n)
    
    def convert(self, value, from_base, to_base):
        """通用进制转换"""
        # 处理抽象进制输入
        if from_base in self.abstract_base_map:
            # 抽象进制转十进制
            decimal_value = self.abstract_base_map[from_base](value)
        elif isinstance(from_base, (int, float, complex)):
            # 数值进制转十进制
            if isinstance(from_base, int) or from_base.is_integer():
                decimal_value = self.base_to_int(str(value), int(from_base))
            else:
                decimal_value = self.frac_to_decimal(str(value), from_base)
        elif from_base in self.quantum_states:
            # 量子态转换
            decimal_value = self.quantum_state_to_decimal(value, from_base)
        elif from_base in self.tensor_heads:
            # 张量转换
            decimal_value = self.tensor_to_scalar(value, from_base)
        else:
            raise ValueError(f"Unsupported base type: {type(from_base)}")
        
        # 十进制转目标进制
        if to_base in self.abstract_base_map:
            return self.abstract_base_map[to_base](decimal_value)
        elif isinstance(to_base, (int, float, complex)):
            if isinstance(to_base, int) or to_base.is_integer():
                return self.int_to_base(int(decimal_value), int(to_base))
            else:
                return self.decimal_to_frac(decimal_value, to_base)
        elif to_base in self.quantum_states:
            # 转换为量子态
            return self.decimal_to_quantum(decimal_value, to_base)
        elif to_base in self.tensor_heads:
            # 转换为张量
            return self.scalar_to_tensor(decimal_value, to_base)
        else:
            raise ValueError(f"Unsupported base type: {type(to_base)}")
    
    def quantum_state_to_decimal(self, state, base):
        """量子态到十进制转换"""
        if base == '|ψ>':
            # 自定义量子态
            alpha, beta = state
            return complex(alpha, beta)
        else:
            # 标准量子态
            state_vector = self.quantum_states[base]
            if callable(state_vector):
                return state_vector(0, 1)  # 默认|1>态
            return state_vector
    
    def decimal_to_quantum(self, n, base):
        """十进制到量子态转换"""
        if base == '|ψ>':
            # 自定义量子态
            alpha = n.real
            beta = n.imag
            return (alpha, beta)
        else:
            # 标准量子态 - 返回名称
            return base
    
    def tensor_to_scalar(self, tensor, base):
        """张量到标量转换（取迹）"""
        if isinstance(tensor, Array):
            # 计算张量迹
            return tensor.trace().flatten()[0]
        return 0
    
    def scalar_to_tensor(self, n, base):
        """标量到张量转换（创建对角张量）"""
        tensor_head = self.tensor_heads[base]
        rank = len(tensor_head.index_types)
        shape = [3] * rank  # 3x3x...张量
        
        # 创建对角张量
        arr = Array(np.zeros(shape))
        for i in range(min(shape)):
            indices = [i] * rank
            arr[tuple(indices)] = n
        
        return arr
    
    def add_custom_base(self, base, converter, algebra_properties=None):
        """添加自定义进制"""
        if isinstance(base, str):
            self.bases['abstract'].append(base)
            self.abstract_base_map[base] = converter
        
        if algebra_properties:
            self.base_algebra[base] = algebra_properties
    
    def get_base_algebra(self, base):
        """获取进制的代数结构"""
        if base in self.base_algebra:
            return self.base_algebra[base]
        
        # 自动推导代数结构
        algebra = {
            'commutative': True,
            'associative': True,
            'distributive': True,
            'identity': '0',
            'inverse': True
        }
        
        # 特殊进制的特性
        if isinstance(base, int) and base < 0:
            algebra['non_standard'] = "Negative base"
        elif isinstance(base, complex):
            algebra['non_standard'] = "Complex arithmetic"
        elif base in ['∞', 'ℵ']:
            algebra['non_standard'] = "Infinite-dimensional"
            algebra['associative'] = False
        elif base in ['∇', 'Fⁿ']:
            algebra['non_standard'] = "Fractal properties"
            algebra['commutative'] = False
        elif base in ['Δ', '|ψ>']:
            algebra['non_standard'] = "Quantum properties"
            algebra['distributive'] = False
        
        self.base_algebra[base] = algebra
        return algebra
    
    def operate(self, a, b, operation, base):
        """在指定进制下执行运算"""
        # 转换为十进制
        dec_a = self.convert(a, base, 10)
        dec_b = self.convert(b, base, 10)
        
        # 执行运算
        if operation == '+':
            result = dec_a + dec_b
        elif operation == '-':
            result = dec_a - dec_b
        elif operation == '*':
            result = dec_a * dec_b
        elif operation == '/':
            result = dec_a / dec_b if dec_b != 0 else float('nan')
        elif operation == '^':
            result = dec_a ** dec_b
        else:
            raise ValueError(f"Unsupported operation: {operation}")
        
        # 转回目标进制
        return self.convert(result, 10, base)
    
    def solve_equation(self, equation, base):
        """在指定进制下解方程"""
        # 转换为符号表达式
        x = sp.symbols('x')
        expr = sp.sympify(equation)
        
        # 求解
        solutions = sp.solve(expr, x)
        
        # 转换为目标进制
        base_solutions = []
        for sol in solutions:
            try:
                # 尝试数值转换
                num_sol = complex(sol)
                base_sol = self.convert(num_sol, 10, base)
                base_solutions.append(base_sol)
            except:
                # 符号解保持原样
                base_solutions.append(str(sol))
        
        return base_solutions

class HyperBaseVisualizer:
    """超进制可视化工具"""
    def __init__(self, base_system):
        self.base_system = base_system
        self.color_map = self._create_color_map()
    
    def _create_color_map(self):
        """创建进制颜色映射"""
        return {
            2: 'red',
            8: 'green',
            10: 'blue',
            16: 'purple',
            1.5: 'orange',
            -2: 'cyan',
            1j: 'magenta',
            sp.pi: 'brown',
            'ℵ': 'pink',
            '∞': 'gray',
            '∇': 'olive',
            'Δ': 'teal',
            'Ψ': 'coral',
            'Ω': 'navy',
            'Σ': 'lime',
            'Π': 'indigo'
        }
    
    def visualize_base_landscape(self, fig, base, value_range=(-10, 10), resolution=100):
        """可视化进制的数学景观"""
        if isinstance(base, (int, float)):
            # 实数进制 - 3D表面图
            self._visualize_real_base(fig, base, value_range, resolution)
        elif isinstance(base, complex):
            # 复数进制 - 复平面热力图
            self._visualize_complex_base(fig, base, value_range, resolution)
        elif base in ['ℵ', '∞', '∇', 'Δ', 'Ψ', 'Ω', 'Σ', 'Π']:
            # 抽象进制 - 特殊可视化
            self._visualize_abstract_base(fig, base, value_range, resolution)
        else:
            # 默认可视化
            self._visualize_generic_base(fig, base, value_range, resolution)
    
    def _visualize_real_base(self, fig, base, value_range, resolution):
        """可视化实数进制"""
        ax = fig.add_subplot(111, projection='3d')
        
        # 创建网格
        x = np.linspace(value_range[0], value_range[1], resolution)
        y = np.linspace(value_range[0], value_range[1], resolution)
        X, Y = np.meshgrid(x, y)
        
        # 计算Z值（进制表示的长度）
        Z = np.zeros_like(X)
        
        for i in range(resolution):
            for j in range(resolution):
                # 计算复数值
                val = complex(X[i, j], Y[i, j])
                
                # 获取进制表示
                try:
                    rep = self.base_system.convert(val, 10, base)
                    # 使用表示长度作为Z值
                    Z[i, j] = len(str(rep))
                except:
                    Z[i, j] = 0
        
        # 绘制表面
        surf = ax.plot_surface(X, Y, Z, cmap=cm.viridis, alpha=0.8)
        
        # 添加标签
        base_name = str(base) if not isinstance(base, str) else base
        ax.set_title(f"Base {base_name} Representation Complexity")
        ax.set_xlabel("Real")
        ax.set_ylabel("Imaginary")
        ax.set_zlabel("Representation Length")
        
        fig.colorbar(surf)
    
    def _visualize_complex_base(self, fig, base, value_range, resolution):
        """可视化复数进制"""
        ax = fig.add_subplot(111)
        
        # 创建网格
        x = np.linspace(value_range[0], value_range[1], resolution)
        y = np.linspace(value_range[0], value_range[1], resolution)
        X, Y = np.meshgrid(x, y)
        
        # 计算表示长度
        Z = np.zeros_like(X, dtype=float)
        
        for i in range(resolution):
            for j in range(resolution):
                # 计算复数值
                val = complex(X[i, j], Y[i, j])
                
                # 获取进制表示
                try:
                    rep = self.base_system.convert(val, 10, base)
                    # 使用表示长度作为Z值
                    Z[i, j] = len(str(rep))
                except:
                    Z[i, j] = 0
        
        # 绘制热力图
        cax = ax.imshow(Z, extent=[value_range[0], value_range[1], value_range[0], value_range[1]], 
                       cmap=cm.plasma, origin='lower')
        
        # 添加标签
        base_name = f"({base.real}+{base.imag}i)"
        ax.set_title(f"Complex Base {base_name} Representation")
        ax.set_xlabel("Real")
        ax.set_ylabel("Imaginary")
        
        fig.colorbar(cax)
    
    def _visualize_abstract_base(self, fig, base, value_range, resolution):
        """可视化抽象进制"""
        ax = fig.add_subplot(111)
        
        # 生成值范围
        values = np.linspace(value_range[0], value_range[1], resolution)
        
        # 获取进制表示
        representations = []
        for val in values:
            try:
                rep = self.base_system.convert(val, 10, base)
                representations.append(rep)
            except:
                representations.append("")
        
        # 创建文本可视化
        ax.clear()
        ax.set_title(f"Base {base} Representations")
        ax.set_xlabel("Value")
        ax.set_ylabel("Representation")
        ax.grid(True)
        
        # 添加文本
        for i, val in enumerate(values):
            ax.text(val, i % 10, representations[i], fontsize=8)
    
    def _visualize_generic_base(self, fig, base, value_range, resolution):
        """通用可视化"""
        ax = fig.add_subplot(111)
        
        # 生成值范围
        values = np.linspace(value_range[0], value_range[1], resolution)
        
        # 计算表示长度
        lengths = []
        for val in values:
            try:
                rep = self.base_system.convert(val, 10, base)
                lengths.append(len(str(rep)))
            except:
                lengths.append(0)
        
        # 绘制曲线
        ax.plot(values, lengths, color=self.color_map.get(base, 'black'))
        
        # 添加标签
        base_name = str(base) if not isinstance(base, str) else base
        ax.set_title(f"Base {base_name} Representation Length")
        ax.set_xlabel("Value")
        ax.set_ylabel("Representation Length")
        ax.grid(True)
    
    def plot_base_comparison(self, fig, bases, value_range=(1, 100), num_points=50):
        """比较不同进制的表示效率"""
        ax = fig.add_subplot(111)
        
        x = np.linspace(value_range[0], value_range[1], num_points)
        
        for base in bases:
            lengths = []
            for val in x:
                try:
                    rep = self.base_system.convert(val, 10, base)
                    lengths.append(len(str(rep)))
                except:
                    lengths.append(0)
            
            color = self.color_map.get(base, 'black')
            label = str(base) if not isinstance(base, str) else base
            ax.plot(x, lengths, label=f"Base {label}", color=color)
        
        ax.set_title("Representation Length Comparison")
        ax.set_xlabel("Value")
        ax.set_ylabel("Representation Length")
        ax.legend()
        ax.grid(True)
    
    def visualize_base_transformation(self, fig, value, from_base, to_base):
        """可视化进制转换过程"""
        ax = fig.add_subplot(111)
        
        # 获取转换步骤
        steps = [
            f"Start: {value} in base {from_base}",
            f"Decimal: {self.base_system.convert(value, from_base, 10)}",
            f"Result: {self.base_system.convert(value, from_base, to_base)} in base {to_base}"
        ]
        
        # 创建流程图
        y_pos = np.arange(len(steps))
        ax.barh(y_pos, [1]*len(steps), color='skyblue')
        
        for i, step in enumerate(steps):
            ax.text(0.5, i, step, ha='center', va='center', fontsize=10)
        
        ax.set_yticks(y_pos)
        ax.set_yticklabels([f"Step {i+1}" for i in range(len(steps))])
        ax.set_title(f"Base Conversion: {from_base} → {to_base}")
        ax.axis('off')
    
    def visualize_quantum_state(self, fig, state, base):
        """可视化量子态"""
        if not hasattr(fig, 'bloch_ax'):
            from qutip import Bloch
            fig.bloch = Bloch()
            fig.bloch_ax = fig.add_subplot(111, projection='3d')
            fig.bloch.axes = fig.bloch_ax
        
        # 获取态矢量
        if base == '|ψ>':
            alpha, beta = state
            state_vector = np.array([alpha, beta])
        else:
            state_vector = self.base_system.quantum_states[base]
            if callable(state_vector):
                state_vector = state_vector(0, 1)  # 默认|1>态
        
        # 归一化
        norm = np.linalg.norm(state_vector)
        if norm > 0:
            state_vector = state_vector / norm
        
        # 更新Bloch球
        fig.bloch.clear()
        fig.bloch.add_vectors([state_vector])
        fig.bloch.render(fig.bloch_ax)
        
        # 设置标题
        base_name = str(base) if not isinstance(base, str) else base
        fig.bloch_ax.set_title(f"Quantum State in Base {base_name}")

class HyperBaseCalculatorGUI(QMainWindow):
    """超进制计算器GUI"""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("HyperBase Mathematical Reasoning System")
        self.setGeometry(100, 100, 1600, 900)
        
        # 创建多进制系统
        self.base_system = HyperBaseSystem()
        self.visualizer = HyperBaseVisualizer(self.base_system)
        
        # 当前表达式
        self.current_expression = None
        
        # 初始化UI
        self.init_ui()
        
        # 状态栏
        self.statusBar().showMessage("Ready")
    
    def init_ui(self):
        """初始化用户界面"""
        # 创建主中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # 左侧控制面板
        control_panel = QTabWidget()
        
        # 计算器标签页
        calculator_tab = QWidget()
        self.init_calculator_tab(calculator_tab)
        control_panel.addTab(calculator_tab, "Calculator")
        
        # 转换器标签页
        converter_tab = QWidget()
        self.init_converter_tab(converter_tab)
        control_panel.addTab(converter_tab, "Converter")
        
        # 代数标签页
        algebra_tab = QWidget()
        self.init_algebra_tab(algebra_tab)
        control_panel.addTab(algebra_tab, "Algebra")
        
        # 自定义标签页
        custom_tab = QWidget()
        self.init_custom_tab(custom_tab)
        control_panel.addTab(custom_tab, "Custom Bases")
        
        # 可视化面板
        self.visualization_tabs = QTabWidget()
        self.init_visualization_tabs()
        
        # 添加主布局
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(control_panel)
        splitter.addWidget(self.visualization_tabs)
        splitter.setSizes([500, 1100])
        main_layout.addWidget(splitter)
        
        # 初始可视化
        self.update_visualization()
    
    def init_calculator_tab(self, tab):
        """初始化计算器标签页"""
        layout = QVBoxLayout(tab)
        
        # 表达式输入
        expr_group = QGroupBox("Expression Input")
        expr_layout = QVBoxLayout(expr_group)
        
        expr_layout.addWidget(QLabel("Enter Expression:"))
        self.expr_input = QLineEdit("2^8 + sin(π/2)")
        expr_layout.addWidget(self.expr_input)
        
        expr_layout.addWidget(QLabel("Base:"))
        self.base_combo = QComboBox()
        self.populate_base_combo(self.base_combo)
        expr_layout.addWidget(self.base_combo)
        
        self.eval_btn = QPushButton("Evaluate Expression")
        self.eval_btn.clicked.connect(self.evaluate_expression)
        expr_layout.addWidget(self.eval_btn)
        
        self.result_display = QTextEdit()
        self.result_display.setReadOnly(True)
        expr_layout.addWidget(self.result_display)
        
        layout.addWidget(expr_group)
        
        # 方程求解
        equation_group = QGroupBox("Equation Solver")
        equation_layout = QVBoxLayout(equation_group)
        
        equation_layout.addWidget(QLabel("Enter Equation:"))
        self.equation_input = QLineEdit("x^2 + 2*x + 1 = 0")
        equation_layout.addWidget(self.equation_input)
        
        equation_layout.addWidget(QLabel("Base:"))
        self.equation_base_combo = QComboBox()
        self.populate_base_combo(self.equation_base_combo)
        equation_layout.addWidget(self.equation_base_combo)
        
        self.solve_btn = QPushButton("Solve Equation")
        self.solve_btn.clicked.connect(self.solve_equation)
        equation_layout.addWidget(self.solve_btn)
        
        self.solution_display = QTextEdit()
        self.solution_display.setReadOnly(True)
        equation_layout.addWidget(self.solution_display)
        
        layout.addWidget(equation_group)
    
    def init_converter_tab(self, tab):
        """初始化转换器标签页"""
        layout = QVBoxLayout(tab)
        
        # 进制转换
        conv_group = QGroupBox("Base Conversion")
        conv_layout = QVBoxLayout(conv_group)
        
        conv_layout.addWidget(QLabel("Value to Convert:"))
        self.conv_value_input = QLineEdit("42")
        conv_layout.addWidget(self.conv_value_input)
        
        conv_layout.addWidget(QLabel("From Base:"))
        self.from_base_combo = QComboBox()
        self.populate_base_combo(self.from_base_combo)
        conv_layout.addWidget(self.from_base_combo)
        
        conv_layout.addWidget(QLabel("To Base:"))
        self.to_base_combo = QComboBox()
        self.populate_base_combo(self.to_base_combo)
        self.to_base_combo.setCurrentIndex(2)  # 默认十进制
        conv_layout.addWidget(self.to_base_combo)
        
        self.conv_btn = QPushButton("Convert Base")
        self.conv_btn.clicked.connect(self.convert_base)
        conv_layout.addWidget(self.conv_btn)
        
        self.conv_result = QLabel("Result will appear here")
        self.conv_result.setStyleSheet("font-weight: bold; color: blue;")
        conv_layout.addWidget(self.conv_result)
        
        layout.addWidget(conv_group)
        
        # 批量转换
        batch_group = QGroupBox("Batch Conversion")
        batch_layout = QVBoxLayout(batch_group)
        
        batch_layout.addWidget(QLabel("Values (comma separated):"))
        self.batch_values_input = QLineEdit("10, 20, 30, 40, 50")
        batch_layout.addWidget(self.batch_values_input)
        
        batch_layout.addWidget(QLabel("From Base:"))
        self.batch_from_combo = QComboBox()
        self.populate_base_combo(self.batch_from_combo)
        batch_layout.addWidget(self.batch_from_combo)
        
        batch_layout.addWidget(QLabel("To Base:"))
        self.batch_to_combo = QComboBox()
        self.populate_base_combo(self.batch_to_combo)
        batch_layout.addWidget(self.batch_to_combo)
        
        self.batch_conv_btn = QPushButton("Convert All")
        self.batch_conv_btn.clicked.connect(self.batch_convert)
        batch_layout.addWidget(self.batch_conv_btn)
        
        self.batch_result = QTextEdit()
        self.batch_result.setReadOnly(True)
        batch_layout.addWidget(self.batch_result)
        
        layout.addWidget(batch_group)
    
    def init_algebra_tab(self, tab):
        """初始化代数标签页"""
        layout = QVBoxLayout(tab)
        
        # 代数特性
        algebra_group = QGroupBox("Base Algebra Properties")
        algebra_layout = QVBoxLayout(algebra_group)
        
        self.algebra_list = QListWidget()
        self.populate_algebra_list()
        algebra_layout.addWidget(self.algebra_list)
        
        self.algebra_info = QTextEdit()
        self.algebra_info.setReadOnly(True)
        algebra_layout.addWidget(self.algebra_info)
        
        self.algebra_list.itemClicked.connect(self.show_algebra_info)
        
        layout.addWidget(algebra_group)
        
        # 进制运算
        operation_group = QGroupBox("Base Operations")
        operation_layout = QFormLayout(operation_group)
        
        operation_layout.addRow(QLabel("Operand A:"))
        self.operand_a = QLineEdit("10")
        operation_layout.addRow(self.operand_a)
        
        operation_layout.addRow(QLabel("Operand B:"))
        self.operand_b = QLineEdit("5")
        operation_layout.addRow(self.operand_b)
        
        operation_layout.addRow(QLabel("Operation:"))
        self.operation_combo = QComboBox()
        self.operation_combo.addItems(["+", "-", "*", "/", "^"])
        operation_layout.addRow(self.operation_combo)
        
        operation_layout.addRow(QLabel("Base:"))
        self.operation_base_combo = QComboBox()
        self.populate_base_combo(self.operation_base_combo)
        operation_layout.addRow(self.operation_base_combo)
        
        self.calculate_btn = QPushButton("Calculate")
        self.calculate_btn.clicked.connect(self.perform_operation)
        operation_layout.addRow(self.calculate_btn)
        
        self.operation_result = QLabel("Result will appear here")
        self.operation_result.setStyleSheet("font-weight: bold; color: green;")
        operation_layout.addRow(self.operation_result)
        
        layout.addWidget(operation_group)
    
    def init_custom_tab(self, tab):
        """初始化自定义标签页"""
        layout = QVBoxLayout(tab)
        
        # 自定义进制
        custom_group = QGroupBox("Custom Base Creation")
        custom_layout = QFormLayout(custom_group)
        
        custom_layout.addRow(QLabel("Base Symbol:"))
        self.base_symbol_input = QLineEdit("Ψ")
        custom_layout.addRow(self.base_symbol_input)
        
        custom_layout.addRow(QLabel("Description:"))
        self.base_desc_input = QLineEdit("Quantum state base")
        custom_layout.addRow(self.base_desc_input)
        
        custom_layout.addRow(QLabel("Algebra Properties:"))
        
        prop_layout = QHBoxLayout()
        self.commutative_check = QCheckBox("Commutative")
        self.commutative_check.setChecked(True)
        prop_layout.addWidget(self.commutative_check)
        
        self.associative_check = QCheckBox("Associative")
        self.associative_check.setChecked(True)
        prop_layout.addWidget(self.associative_check)
        
        self.distributive_check = QCheckBox("Distributive")
        self.distributive_check.setChecked(True)
        prop_layout.addWidget(self.distributive_check)
        
        custom_layout.addRow(prop_layout)
        
        self.create_base_btn = QPushButton("Create Custom Base")
        self.create_base_btn.clicked.connect(self.create_custom_base)
        custom_layout.addRow(self.create_base_btn)
        
        layout.addWidget(custom_group)
        
        # 自定义进制库
        custom_lib_group = QGroupBox("Custom Base Library")
        custom_lib_layout = QVBoxLayout(custom_lib_group)
        
        self.custom_base_list = QListWidget()
        self.populate_custom_base_list()
        custom_lib_layout.addWidget(self.custom_base_list)
        
        self.remove_base_btn = QPushButton("Remove Selected Base")
        self.remove_base_btn.clicked.connect(self.remove_custom_base)
        custom_lib_layout.addWidget(self.remove_base_btn)
        
        layout.addWidget(custom_lib_group)
    
    def init_visualization_tabs(self):
        """初始化可视化标签页"""
        # 进制景观可视化
        self.landscape_canvas = FigureCanvas(Figure(figsize=(8, 6)))
        landscape_tab = QWidget()
        landscape_layout = QVBoxLayout(landscape_tab)
        landscape_layout.addWidget(self.landscape_canvas)
        self.visualization_tabs.addTab(landscape_tab, "Base Landscape")
        
        # 进制比较可视化
        self.comparison_canvas = FigureCanvas(Figure(figsize=(8, 6)))
        comparison_tab = QWidget()
        comparison_layout = QVBoxLayout(comparison_tab)
        comparison_layout.addWidget(self.comparison_canvas)
        self.visualization_tabs.addTab(comparison_tab, "Base Comparison")
        
        # 进制转换可视化
        self.conversion_canvas = FigureCanvas(Figure(figsize=(8, 6)))
        conversion_tab = QWidget()
        conversion_layout = QVBoxLayout(conversion_tab)
        conversion_layout.addWidget(self.conversion_canvas)
        self.visualization_tabs.addTab(conversion_tab, "Conversion Process")
        
        # 量子态可视化
        self.quantum_canvas = FigureCanvas(Figure(figsize=(8, 6)))
        quantum_tab = QWidget()
        quantum_layout = QVBoxLayout(quantum_tab)
        quantum_layout.addWidget(self.quantum_canvas)
        self.visualization_tabs.addTab(quantum_tab, "Quantum State")
        
        # 张量可视化
        self.tensor_canvas = FigureCanvas(Figure(figsize=(8, 6)))
        tensor_tab = QWidget()
        tensor_layout = QVBoxLayout(tensor_tab)
        tensor_layout.addWidget(self.tensor_canvas)
        self.visualization_tabs.addTab(tensor_tab, "Tensor Visualization")
    
    def populate_base_combo(self, combo):
        """填充进制选择框"""
        combo.clear()
        
        # 添加整数进制
        combo.addItem("Integer Bases", None)
        for base in self.base_system.bases['integer']:
            combo.addItem(f"Base {base}", base)
        
        # 添加分数进制
        combo.addItem("Fractional Bases", None)
        for base in self.base_system.bases['fractional']:
            combo.addItem(f"Base {base:.3f}", base)
        
        # 添加负进制
        combo.addItem("Negative Bases", None)
        for base in self.base_system.bases['negative']:
            combo.addItem(f"Base {base}", base)
        
        # 添加复数进制
        combo.addItem("Complex Bases", None)
        for base in self.base_system.bases['complex']:
            combo.addItem(f"Base {base}", base)
        
        # 添加无理数进制
        combo.addItem("Irrational Bases", None)
        for base in self.base_system.bases['irrational']:
            combo.addItem(f"Base {sp.pretty(base)}", base)
        
        # 添加抽象进制
        combo.addItem("Abstract Bases", None)
        for base in self.base_system.bases['abstract']:
            combo.addItem(f"Base {base}", base)
        
        # 添加量子进制
        combo.addItem("Quantum Bases", None)
        for base in self.base_system.bases['quantum']:
            combo.addItem(f"Base {base}", base)
        
        # 添加张量进制
        combo.addItem("Tensor Bases", None)
        for base in self.base_system.bases['tensor']:
            combo.addItem(f"Base {base}", base)
        
        # 添加分形进制
        combo.addItem("Fractal Bases", None)
        for base in self.base_system.bases['fractal']:
            combo.addItem(f"Base {base}", base)
    
    def populate_algebra_list(self):
        """填充代数特性列表"""
        self.algebra_list.clear()
        
        # 添加所有进制的代数特性项
        for category, bases in self.base_system.bases.items():
            self.algebra_list.addItem(f"--- {category.capitalize()} Bases ---")
            for base in bases:
                item = QListWidgetItem(f"Base {base}")
                item.setData(Qt.UserRole, base)
                self.algebra_list.addItem(item)
    
    def populate_custom_base_list(self):
        """填充自定义进制列表"""
        self.custom_base_list.clear()
        for base in self.base_system.bases['abstract']:
            self.custom_base_list.addItem(f"Base {base}")
    
    def evaluate_expression(self):
        """评估表达式"""
        expr_str = self.expr_input.text()
        base = self.base_combo.currentData()
        
        try:
            # 创建表达式
            self.current_expression = expr_str
            
            # 评估值
            value = sp.sympify(expr_str).evalf()
            in_base = self.base_system.convert(value, 10, base)
            
            # 显示结果
            result = f"Expression: {expr_str}\n"
            result += f"Base: {base}\n\n"
            result += f"Decimal value: {value}\n"
            result += f"Base {base} representation: {in_base}"
            
            self.result_display.setText(result)
            
            # 更新可视化
            self.update_visualization(base)
            
        except Exception as e:
            self.result_display.setText(f"Evaluation failed: {str(e)}")
    
    def solve_equation(self):
        """解方程"""
        equation_str = self.equation_input.text()
        base = self.equation_base_combo.currentData()
        
        try:
            # 解析方程
            if '=' in equation_str:
                parts = equation_str.split('=')
                lhs = sp.sympify(parts[0])
                rhs = sp.sympify(parts[1])
                expr = lhs - rhs
            else:
                expr = sp.sympify(equation_str)
            
            # 求解
            solutions = self.base_system.solve_equation(expr, base)
            
            # 显示结果
            result = f"Equation: {equation_str}\n"
            result += f"Base: {base}\n\n"
            result += "Solutions:\n"
            for i, sol in enumerate(solutions):
                result += f"  x_{i+1} = {sol}\n"
            
            self.solution_display.setText(result)
            
        except Exception as e:
            self.solution_display.setText(f"Solving failed: {str(e)}")
    
    def convert_base(self):
        """执行进制转换"""
        value_str = self.conv_value_input.text()
        from_base = self.from_base_combo.currentData()
        to_base = self.to_base_combo.currentData()
        
        try:
            # 转换进制
            result = self.base_system.convert(value_str, from_base, to_base)
            self.conv_result.setText(f"Result: {result}")
            
            # 更新转换可视化
            self.visualizer.visualize_base_transformation(
                self.conversion_canvas.figure, value_str, from_base, to_base)
            self.conversion_canvas.draw()
            
        except Exception as e:
            self.conv_result.setText(f"Conversion failed: {str(e)}")
    
    def batch_convert(self):
        """批量转换"""
        values_str = self.batch_values_input.text()
        from_base = self.batch_from_combo.currentData()
        to_base = self.batch_to_combo.currentData()
        
        values = [v.strip() for v in values_str.split(',')]
        
        results = []
        for value in values:
            try:
                result = self.base_system.convert(value, from_base, to_base)
                results.append(f"{value} ({from_base}) → {result} ({to_base})")
            except Exception as e:
                results.append(f"{value} ({from_base}) → Error: {str(e)}")
        
        self.batch_result.setText("\n".join(results))
    
    def show_algebra_info(self, item):
        """显示代数特性信息"""
        base = item.data(Qt.UserRole)
        if not base:
            return
        
        algebra = self.base_system.get_base_algebra(base)
        
        info = f"Algebraic Properties of Base {base}:\n\n"
        for prop, value in algebra.items():
            if isinstance(value, bool):
                value_str = "Yes" if value else "No"
            else:
                value_str = str(value)
            info += f"• {prop.capitalize()}: {value_str}\n"
        
        self.algebra_info.setText(info)
    
    def perform_operation(self):
        """执行运算"""
        operand_a_str = self.operand_a.text()
        operand_b_str = self.operand_b.text()
        operation = self.operation_combo.currentText()
        base = self.operation_base_combo.currentData()
        
        try:
            # 转换操作数
            a = self.base_system.convert(operand_a_str, base, 10)
            b = self.base_system.convert(operand_b_str, base, 10)
            
            # 执行运算
            if operation == '+':
                result = a + b
            elif operation == '-':
                result = a - b
            elif operation == '*':
                result = a * b
            elif operation == '/':
                result = a / b
            elif operation == '^':
                result = a ** b
            
            # 转换回目标进制
            base_result = self.base_system.convert(result, 10, base)
            
            # 显示结果
            self.operation_result.setText(f"Result: {base_result}")
            
        except Exception as e:
            self.operation_result.setText(f"Operation failed: {str(e)}")
    
    def create_custom_base(self):
        """创建自定义进制"""
        symbol = self.base_symbol_input.text().strip()
        description = self.base_desc_input.text().strip()
        
        if not symbol:
            QMessageBox.warning(self, "Error", "Base symbol cannot be empty")
            return
        
        # 定义代数特性
        algebra_props = {
            'commutative': self.commutative_check.isChecked(),
            'associative': self.associative_check.isChecked(),
            'distributive': self.distributive_check.isChecked(),
            'description': description
        }
        
        # 创建转换函数
        def custom_converter(x):
            if isinstance(x, complex):
                return f"{symbol}(Re:{x.real:.2f}, Im:{x.imag:.2f})"
            return f"{symbol}({x})"
        
        # 添加自定义进制
        self.base_system.add_custom_base(symbol, custom_converter, algebra_props)
        
        # 更新UI
        self.populate_base_combo(self.base_combo)
        self.populate_base_combo(self.from_base_combo)
        self.populate_base_combo(self.to_base_combo)
        self.populate_base_combo(self.equation_base_combo)
        self.populate_base_combo(self.operation_base_combo)
        self.populate_algebra_list()
        self.populate_custom_base_list()
        
        QMessageBox.information(self, "Success", f"Custom base '{symbol}' created")
    
    def remove_custom_base(self):
        """移除自定义进制"""
        selected_items = self.custom_base_list.selectedItems()
        if not selected_items:
            return
        
        item = selected_items[0]
        base_name = item.text().replace("Base ", "")
        
        # 从系统中移除
        if base_name in self.base_system.bases['abstract']:
            self.base_system.bases['abstract'].remove(base_name)
            if base_name in self.base_system.abstract_base_map:
                del self.base_system.abstract_base_map[base_name]
            
            # 更新UI
            self.populate_base_combo(self.base_combo)
            self.populate_base_combo(self.from_base_combo)
            self.populate_base_combo(self.to_base_combo)
            self.populate_base_combo(self.equation_base_combo)
            self.populate_base_combo(self.operation_base_combo)
            self.populate_algebra_list()
            self.populate_custom_base_list()
            
            QMessageBox.information(self, "Success", f"Base '{base_name}' removed")
    
    def update_visualization(self, base=None):
        """更新可视化"""
        if base is None:
            base = self.base_combo.currentData()
            if base is None:
                return
        
        # 更新进制景观
        self.visualizer.visualize_base_landscape(
            self.landscape_canvas.figure, base)
        self.landscape_canvas.draw()
        
        # 更新进制比较
        compare_bases = [2, 10, 1.5, -2, 1j, 'ℵ']
        self.visualizer.plot_base_comparison(
            self.comparison_canvas.figure, compare_bases)
        self.comparison_canvas.draw()
        
        # 量子态可视化
        if base in self.base_system.bases['quantum']:
            state = (0.6, 0.8)  # 示例量子态
            self.visualizer.visualize_quantum_state(
                self.quantum_canvas.figure, state, base)
            self.quantum_canvas.draw()

if __name__ == "__main__":
    app = QApplication([])
    window = HyperBaseCalculatorGUI()
    window.show()
    app.exec_()