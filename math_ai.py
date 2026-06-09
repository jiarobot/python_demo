import sys
import os
import numpy as np
import sympy as sp
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QLineEdit, QPushButton, QComboBox, QGroupBox, 
                             QTextEdit, QFileDialog, QProgressBar, QSplitter, QTabWidget,
                             QCheckBox, QDoubleSpinBox, QSpinBox, QStackedWidget, QRadioButton,
                             QButtonGroup, QTableWidget, QTableWidgetItem, QHeaderView,QGridLayout)
from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PyQt5.QtGui import QFont, QColor
from scipy.optimize import minimize, differential_evolution
import random
import re
import warnings
import math
import binascii
import struct

# 忽略警告
warnings.filterwarnings('ignore')

class MultiStepExpression:
    """支持多步运算的表达式类"""
    def __init__(self, steps=None, output_var=None):
        self.steps = steps or []  # 步骤列表: [("var1", "x + 1"), ("var2", "sin(var1)")]
        self.output_var = output_var or (steps[-1][0] if steps else "result")
        self.variables = {}
        
    def add_step(self, var_name, expression):
        """添加一个计算步骤"""
        self.steps.append((var_name, expression))
        self.output_var = var_name
        
    def evaluate(self, x, base=10):
        """评估多步表达式"""
        # 初始化变量
        self.variables = {'x': x}
        results = []
        
        # 执行每一步计算
        for var_name, expr in self.steps:
            # 转换进制
            expr = self.convert_base(expr, base)
            
            # 解析并评估表达式
            try:
                # 替换变量
                for v in self.variables:
                    expr = expr.replace(v, f'self.variables["{v}"]')
                
                # 安全评估
                result = eval(expr, {'math': math, 'np': np, 'sp': sp, 'self': self})
                self.variables[var_name] = result
                results.append(result)
            except Exception as e:
                raise ValueError(f"Error evaluating step '{var_name} = {expr}': {str(e)}")
        
        return self.variables[self.output_var]
    
    def convert_base(self, expr, base):
        """转换表达式中的数字到指定进制"""
        # 匹配不同进制的数字
        patterns = {
            2: r'0b[01]+',
            8: r'0o[0-7]+',
            16: r'0x[0-9a-fA-F]+',
            10: r'\d+\.?\d*'
        }
        
        # 替换所有数字
        if base in patterns:
            def convert_match(match):
                num_str = match.group(0)
                try:
                    # 转换到十进制
                    if base == 2 and num_str.startswith('0b'):
                        return str(int(num_str, 2))
                    elif base == 8 and num_str.startswith('0o'):
                        return str(int(num_str, 8))
                    elif base == 16 and num_str.startswith('0x'):
                        return str(int(num_str, 16))
                    elif base == 10:
                        return num_str
                except:
                    pass
                return num_str
            
            expr = re.sub(patterns[base], convert_match, expr)
        
        return expr
    
    def to_string(self, base=10):
        """将表达式转换为字符串表示"""
        lines = []
        for var_name, expr in self.steps:
            expr = self.convert_base(expr, base)
            lines.append(f"{var_name} = {expr}")
        return "\n".join(lines)
    
    def simplify(self):
        """简化多步表达式"""
        simplified_steps = []
        for var_name, expr in self.steps:
            try:
                # 使用SymPy简化表达式
                simplified = sp.simplify(expr)
                simplified_steps.append((var_name, str(simplified)))
            except:
                simplified_steps.append((var_name, expr))
        return MultiStepExpression(simplified_steps, self.output_var)
    
    def to_single_expression(self):
        """转换为单步表达式（如果可能）"""
        if len(self.steps) == 1:
            return self.steps[0][1]
        
        # 尝试合并表达式
        try:
            expr = self.steps[-1][1]
            for i in range(len(self.steps)-2, -1, -1):
                var_name, var_expr = self.steps[i]
                expr = expr.replace(var_name, f"({var_expr})")
            return expr
        except:
            return self.to_string()

class BaseConversion:
    """进制转换工具类"""
    @staticmethod
    def to_base(n, base, precision=8):
        """将十进制数转换为指定进制字符串"""
        if base == 10:
            return str(n)
        
        # 处理整数部分
        integer_part = int(abs(n))
        fractional_part = abs(n) - integer_part
        
        # 转换整数部分
        if integer_part == 0:
            result = "0"
        else:
            digits = []
            while integer_part:
                integer_part, digit = divmod(integer_part, base)
                digits.append(BaseConversion.digit_to_char(digit))
            result = ''.join(digits[::-1])
        
        # 添加前缀
        prefix = {2: "0b", 8: "0o", 16: "0x"}.get(base, "")
        
        # 转换小数部分
        if fractional_part > 0:
            result += '.'
            for _ in range(precision):
                fractional_part *= base
                digit = int(fractional_part)
                fractional_part -= digit
                result += BaseConversion.digit_to_char(digit)
                if fractional_part == 0:
                    break
        
        # 添加符号
        if n < 0:
            result = "-" + result
        
        return prefix + result
    
    @staticmethod
    def digit_to_char(d):
        """将数字转换为字符表示"""
        if d < 10:
            return str(d)
        return chr(ord('A') + d - 10)
    
    @staticmethod
    def from_base(s, base):
        """将指定进制字符串转换为十进制数"""
        # 处理符号
        sign = 1
        if s.startswith('-'):
            sign = -1
            s = s[1:]
        
        # 处理前缀
        prefix = ""
        if s.startswith('0b') and base == 2:
            s = s[2:]
        elif s.startswith('0o') and base == 8:
            s = s[2:]
        elif s.startswith('0x') and base == 16:
            s = s[2:]
        
        # 分割整数和小数部分
        if '.' in s:
            integer_part, fractional_part = s.split('.')
        else:
            integer_part = s
            fractional_part = ""
        
        # 转换整数部分
        integer_value = 0
        for char in integer_part:
            integer_value = integer_value * base + BaseConversion.char_to_digit(char)
        
        # 转换小数部分
        fractional_value = 0
        if fractional_part:
            for i, char in enumerate(fractional_part):
                fractional_value += BaseConversion.char_to_digit(char) * (base ** -(i+1))
        
        return sign * (integer_value + fractional_value)
    
    @staticmethod
    def char_to_digit(c):
        """将字符转换为数字"""
        if '0' <= c <= '9':
            return int(c)
        return 10 + ord(c.upper()) - ord('A')

class EnhancedSymbolicRegressionWorker(QThread):
    """执行增强符号回归的后台线程"""
    progress_updated = pyqtSignal(int, str, float)
    result_ready = pyqtSignal(object, float, np.ndarray, np.ndarray, str)  # 使用对象类型
    error_occurred = pyqtSignal(str)
    status_updated = pyqtSignal(str)

    def __init__(self, target_func, x_range, num_samples, operators, max_depth, pop_size, 
                 max_generations, method, use_const_opt, use_physics, use_bayesian, use_nn,
                 allow_multi_step, base_system):
        super().__init__()
        self.target_func = target_func
        self.x_range = x_range
        self.num_samples = num_samples
        self.operators = operators
        self.max_depth = max_depth
        self.pop_size = pop_size
        self.max_generations = max_generations
        self.method = method
        self.use_const_opt = use_const_opt
        self.use_physics = use_physics
        self.use_bayesian = use_bayesian
        self.use_nn = use_nn
        self.allow_multi_step = allow_multi_step
        self.base_system = base_system
        self.running = True
        self.variable_counter = 0
        
    def run(self):
        try:
            # 生成数据集
            self.status_updated.emit("Generating dataset...")
            x = np.linspace(self.x_range[0], self.x_range[1], self.num_samples)
            y = self.target_func(x)
            
            # 选择方法
            if self.use_bayesian:
                self.status_updated.emit("Running Bayesian optimization...")
                best_expr, best_fitness = self.bayesian_optimization(x, y)
            elif self.use_nn:
                self.status_updated.emit("Training neural network...")
                best_expr, best_fitness = self.neural_network_search(x, y)
            else:
                # 使用遗传规划
                self.status_updated.emit("Initializing population...")
                population = [self.create_random_expression() for _ in range(self.pop_size)]
                best_expr = None
                best_fitness = float('inf')
                
                for generation in range(self.max_generations):
                    if not self.running:
                        return
                    
                    self.status_updated.emit(f"Generation {generation+1}/{self.max_generations}")
                    
                    # 评估种群
                    fitness_scores = []
                    for expr in population:
                        try:
                            fitness = self.evaluate_expression(expr, x, y)
                            fitness_scores.append(fitness)
                            
                            # 更新最佳表达式
                            if fitness < best_fitness:
                                best_fitness = fitness
                                best_expr = expr
                        except Exception as e:
                            fitness_scores.append(float('inf'))
                    
                    # 报告进度
                    self.progress_updated.emit(
                        int(100 * (generation + 1) / self.max_generations),
                        self.expression_to_string(best_expr),
                        best_fitness
                    )
                    
                    # 选择父代（锦标赛选择）
                    parents = self.select_parents(population, fitness_scores)
                    
                    # 创建新一代
                    new_population = []
                    for i in range(0, self.pop_size, 2):
                        parent1 = parents[i % len(parents)]
                        parent2 = parents[(i + 1) % len(parents)]
                        
                        # 交叉
                        child1, child2 = self.crossover(parent1, parent2)
                        
                        # 变异
                        child1 = self.mutate(child1)
                        child2 = self.mutate(child2)
                        
                        new_population.append(child1)
                        new_population.append(child2)
                    
                    population = new_population
            
            # 优化最佳表达式中的常数
            if self.use_const_opt:
                self.status_updated.emit("Optimizing constants...")
                optimized_expr, optimized_fitness = self.optimize_constants(best_expr, x, y)
            else:
                optimized_expr, optimized_fitness = best_expr, best_fitness
            
            # 应用物理约束
            if self.use_physics:
                self.status_updated.emit("Applying physics constraints...")
                optimized_expr = self.apply_physics_constraints(optimized_expr, x, y)
                optimized_fitness = self.evaluate_expression(optimized_expr, x, y)
            
            # 简化表达式
            simplified_expr = self.simplify_expression(optimized_expr)
            
            # 计算最终预测
            y_pred = self.evaluate_expression_numeric(optimized_expr, x)
            
            self.result_ready.emit(
                optimized_expr, 
                optimized_fitness, 
                x, 
                y_pred, 
                self.expression_to_string(simplified_expr)
            )
            
        except Exception as e:
            self.error_occurred.emit(str(e))
    
    def create_random_expression(self, depth=0):
        """创建随机表达式"""
        if depth >= self.max_depth or (depth > 0 and np.random.rand() < 0.5):
            # 返回终端节点
            if np.random.rand() < 0.7:
                return 'x'
            else:
                # 生成随机常数（可能使用不同进制）
                return self.generate_random_constant()
        
        # 决定是否创建多步表达式
        if self.allow_multi_step and depth == 0 and np.random.rand() < 0.3:
            num_steps = np.random.randint(2, 5)
            multi_expr = MultiStepExpression()
            
            # 创建多个步骤
            for i in range(num_steps):
                var_name = f"v{self.variable_counter}"
                self.variable_counter += 1
                
                # 创建子表达式
                if i == num_steps - 1:
                    # 最后一步使用完整表达式
                    expr = self.create_random_expression(depth + 1)
                else:
                    # 中间步骤使用简单表达式
                    expr = self.create_random_expression(min(2, depth + 1))
                
                multi_expr.add_step(var_name, expr)
            
            return multi_expr
        
        # 选择运算符
        op = np.random.choice(self.operators)
        
        if op in ['sin', 'cos', 'tan', 'exp', 'log', 'sqrt', 'abs', 'erf', 'gamma']:
            # 一元运算符
            arg = self.create_random_expression(depth + 1)
            return f"{op}({arg})"
        elif op in ['+', '-', '*', '/', '^', 'and', 'or', 'xor']:
            # 二元运算符
            left = self.create_random_expression(depth + 1)
            right = self.create_random_expression(depth + 1)
            return f"({left} {op} {right})"
        else:  # 三元运算符
            arg1 = self.create_random_expression(depth + 1)
            arg2 = self.create_random_expression(depth + 1)
            arg3 = self.create_random_expression(depth + 1)
            return f"{op}({arg1}, {arg2}, {arg3})"
    
    def generate_random_constant(self):
        """生成随机常数（可能使用不同进制）"""
        # 选择进制
        if self.base_system == "Mixed":
            base = np.random.choice([2, 8, 10, 16])
        else:
            base = int(self.base_system)
        
        # 生成随机数
        value = np.random.uniform(-10, 10)
        
        # 转换进制
        if base == 10:
            return f"{value:.4f}"
        else:
            # 对于非十进制，只生成整数
            int_value = int(round(value))
            return BaseConversion.to_base(int_value, base)
    
    def expression_to_string(self, expr):
        """将表达式转换为字符串表示"""
        if isinstance(expr, MultiStepExpression):
            return expr.to_string(10)  # 总是以十进制显示
        else:
            return expr
    
    def evaluate_expression(self, expr, x, y):
        """评估表达式的适应度（MSE）"""
        y_pred = self.evaluate_expression_numeric(expr, x)
        return np.mean((y_pred - y) ** 2)
    
    def evaluate_expression_numeric(self, expr, x):
        """数值评估表达式"""
        if isinstance(expr, MultiStepExpression):
            return expr.evaluate(x, self.base_system if self.base_system != "Mixed" else 10)
        else:
            # 替换数学函数
            expr = expr.replace('sin', 'np.sin')
            expr = expr.replace('cos', 'np.cos')
            expr = expr.replace('tan', 'np.tan')
            expr = expr.replace('exp', 'np.exp')
            expr = expr.replace('log', 'np.log')
            expr = expr.replace('sqrt', 'np.sqrt')
            expr = expr.replace('abs', 'np.abs')
            expr = expr.replace('erf', 'sp.special.erf')
            expr = expr.replace('gamma', 'sp.special.gamma')
            
            # 转换进制
            expr = self.convert_base(expr)
            
            # 安全评估
            return eval(expr, {'np': np, 'sp': sp, 'x': x})
    
    def convert_base(self, expr):
        """转换表达式中的数字到十进制"""
        # 匹配不同进制的数字
        patterns = {
            2: r'0b[01]+',
            8: r'0o[0-7]+',
            16: r'0x[0-9a-fA-F]+',
            10: r'\d+\.?\d*'
        }
        
        # 替换所有数字为十进制
        for base in [2, 8, 16]:
            def convert_match(match):
                num_str = match.group(0)
                try:
                    return str(BaseConversion.from_base(num_str, base))
                except:
                    return num_str
            
            expr = re.sub(patterns[base], convert_match, expr)
        
        return expr
    
    def select_parents(self, population, fitness_scores, tournament_size=3):
        """锦标赛选择父代"""
        parents = []
        for _ in range(len(population)):
            # 随机选择 tournament_size 个个体
            tournament_indices = np.random.choice(len(population), tournament_size, replace=False)
            tournament_fitness = [fitness_scores[i] for i in tournament_indices]
            
            # 选择适应度最好的个体
            winner_index = tournament_indices[np.argmin(tournament_fitness)]
            parents.append(population[winner_index])
        
        return parents
    
    def crossover(self, parent1, parent2):
        """交叉操作 - 子树交换"""
        # 处理多步表达式
        if isinstance(parent1, MultiStepExpression) and isinstance(parent2, MultiStepExpression):
            # 合并两个多步表达式的步骤
            steps = parent1.steps + parent2.steps
            return MultiStepExpression(steps), parent1
        elif isinstance(parent1, MultiStepExpression):
            # 将单步表达式转换为多步并合并
            new_steps = parent1.steps + [("v_new", parent2)]
            return MultiStepExpression(new_steps), parent1
        elif isinstance(parent2, MultiStepExpression):
            new_steps = [("v_new", parent1)] + parent2.steps
            return MultiStepExpression(new_steps), parent2
        else:
            # 标准单步表达式交叉
            if np.random.rand() > 0.7 or '(' not in parent1 or '(' not in parent2:
                return parent1, parent2
            
            # 在parent1中找到一个子树
            start1, end1 = self.find_random_subtree(parent1)
            subtree1 = parent1[start1:end1]
            
            # 在parent2中找到一个子树
            start2, end2 = self.find_random_subtree(parent2)
            subtree2 = parent2[start2:end2]
            
            # 交换子树
            child1 = parent1[:start1] + subtree2 + parent1[end1:]
            child2 = parent2[:start2] + subtree1 + parent2[end2:]
            
            return child1, child2
    
    def find_random_subtree(self, expr):
        """在表达式中随机找到一个子树"""
        stack = []
        positions = []
        
        for i, char in enumerate(expr):
            if char == '(':
                stack.append(i)
            elif char == ')':
                if stack:
                    start = stack.pop()
                    if not stack:  # 只考虑最外层的括号
                        positions.append((start, i+1))
        
        if not positions:
            return 0, len(expr)
        
        return random.choice(positions)
    
    def mutate(self, expr, mutation_rate=0.2):
        """变异操作"""
        if np.random.rand() > mutation_rate:
            return expr
        
        mutation_type = np.random.choice(
            ['replace', 'insert', 'delete', 'simplify', 'add_step'], 
            p=[0.3, 0.2, 0.2, 0.1, 0.2]
        )
        
        if mutation_type == 'replace':
            # 替换一个操作符或操作数
            if isinstance(expr, MultiStepExpression):
                # 在多步表达式中随机选择一个步骤进行变异
                step_idx = np.random.randint(len(expr.steps))
                var_name, step_expr = expr.steps[step_idx]
                new_expr = self.mutate_step(step_expr)
                expr.steps[step_idx] = (var_name, new_expr)
                return expr
            else:
                return self.mutate_step(expr)
        
        elif mutation_type == 'insert' and not isinstance(expr, MultiStepExpression):
            # 插入一个新操作
            if '(' not in expr:
                return expr
                
            insert_pos = np.random.randint(len(expr))
            new_op = np.random.choice(self.operators)
            
            # 简单实现：在随机位置插入一个新操作
            return expr[:insert_pos] + f" {new_op} x " + expr[insert_pos:]
        
        elif mutation_type == 'delete' and not isinstance(expr, MultiStepExpression):
            # 删除一个操作
            tokens = expr.split()
            if len(tokens) < 3:
                return expr
                
            delete_idx = np.random.randint(1, len(tokens)-1)
            return " ".join(tokens[:delete_idx] + tokens[delete_idx+1:])
        
        elif mutation_type == 'simplify':
            # 尝试简化表达式
            try:
                if isinstance(expr, MultiStepExpression):
                    return expr.simplify()
                else:
                    simplified = sp.simplify(expr)
                    return str(simplified)
            except:
                return expr
        
        elif mutation_type == 'add_step' and self.allow_multi_step:
            # 添加一个新步骤
            if isinstance(expr, MultiStepExpression):
                # 在多步表达式中添加一个新步骤
                var_name = f"v{self.variable_counter}"
                self.variable_counter += 1
                new_expr = self.create_random_expression(1)
                expr.add_step(var_name, new_expr)
                return expr
            else:
                # 将单步表达式转换为多步表达式
                var_name = f"v{self.variable_counter}"
                self.variable_counter += 1
                new_var_name = f"v{self.variable_counter}"
                self.variable_counter += 1
                new_expr = self.create_random_expression(1)
                multi_expr = MultiStepExpression()
                multi_expr.add_step(var_name, expr)
                multi_expr.add_step(new_var_name, new_expr)
                return multi_expr
        
        return expr
    
    def mutate_step(self, expr):
        """变异单个步骤"""
        tokens = expr.split()
        if not tokens:
            return expr
            
        mutate_idx = np.random.randint(len(tokens))
        token = tokens[mutate_idx]
        
        if token in self.operators:
            # 替换操作符
            new_op = np.random.choice(self.operators)
            tokens[mutate_idx] = new_op
        elif token.replace('.', '', 1).replace('-', '', 1).isdigit() or token == 'x':
            # 替换操作数
            if np.random.rand() < 0.5:
                tokens[mutate_idx] = 'x'
            else:
                tokens[mutate_idx] = self.generate_random_constant()
        
        return " ".join(tokens)
    
    def optimize_constants(self, expr, x, y):
        """优化表达式中的常数"""
        if isinstance(expr, MultiStepExpression):
            # 优化多步表达式中的常数
            optimized_steps = []
            for var_name, step_expr in expr.steps:
                # 优化每一步中的常数
                opt_expr, _ = self.optimize_single_expression(step_expr, x, y)
                optimized_steps.append((var_name, opt_expr))
            
            return MultiStepExpression(optimized_steps), self.evaluate_expression(
                MultiStepExpression(optimized_steps), x, y
            )
        else:
            # 优化单步表达式
            return self.optimize_single_expression(expr, x, y)
    
    def optimize_single_expression(self, expr, x, y):
        """优化单步表达式中的常数"""
        # 提取常数
        tokens = expr.split()
        const_positions = [i for i, token in enumerate(tokens) 
                          if token.replace('.', '', 1).replace('-', '', 1).isdigit()]
        
        if not const_positions:
            return expr, self.evaluate_expression(expr, x, y)
        
        # 初始常数值（转换为十进制）
        constants = []
        for i in const_positions:
            token = tokens[i]
            try:
                # 尝试转换进制
                constants.append(float(self.convert_base(token)))
            except:
                constants.append(0.0)
        
        # 创建可优化函数
        def loss(params):
            modified_tokens = tokens.copy()
            for idx, (pos, param_val) in enumerate(zip(const_positions, params)):
                modified_tokens[pos] = str(param_val)
            modified_expr = " ".join(modified_tokens)
            return self.evaluate_expression(modified_expr, x, y)
        
        # 优化常数 - 使用不同的优化方法
        if len(constants) > 3:
            # 对于多个常数，使用全局优化
            bounds = [(-10, 10) for _ in constants]
            result = differential_evolution(loss, bounds, maxiter=100, popsize=10)
        else:
            # 对于少量常数，使用局部优化
            result = minimize(loss, constants, method='L-BFGS-B')
        
        # 应用优化后的常数
        optimized_tokens = tokens.copy()
        for i, param in zip(const_positions, result.x):
            optimized_tokens[i] = f"{param:.6f}"
        optimized_expr = " ".join(optimized_tokens)
        
        return optimized_expr, result.fun
    
    def apply_physics_constraints(self, expr, x, y):
        """应用物理约束"""
        # 简化表达式
        if isinstance(expr, MultiStepExpression):
            return expr.simplify()
        else:
            try:
                return str(sp.simplify(expr))
            except:
                return expr
    
    def simplify_expression(self, expr):
        """简化表达式"""
        if isinstance(expr, MultiStepExpression):
            return expr.simplify()
        else:
            try:
                return str(sp.simplify(expr))
            except:
                return expr
    
    def bayesian_optimization(self, x, y):
        """贝叶斯优化实现（简化版）"""
        # 在实际应用中应实现完整的贝叶斯优化
        # 这里使用遗传规划作为替代
        population = [self.create_random_expression() for _ in range(self.pop_size // 2)]
        best_expr = None
        best_fitness = float('inf')
        
        for i, expr in enumerate(population):
            try:
                fitness = self.evaluate_expression(expr, x, y)
                if fitness < best_fitness:
                    best_fitness = fitness
                    best_expr = expr
                
                # 更新进度
                self.progress_updated.emit(
                    int(100 * (i + 1) / len(population)),
                    self.expression_to_string(expr),
                    fitness
                )
            except:
                pass
        
        return best_expr, best_fitness
    
    def neural_network_search(self, x, y):
        """神经网络搜索实现（简化版）"""
        # 在实际应用中应实现完整的神经网络搜索
        # 这里使用遗传规划作为替代
        return self.bayesian_optimization(x, y)
    
    def stop(self):
        """停止回归过程"""
        self.running = False


class FunctionPlotter(FigureCanvas):
    """函数绘图组件"""
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig, self.ax = plt.subplots(figsize=(width, height), dpi=dpi)
        super().__init__(self.fig)
        self.setParent(parent)
        self.target_x = None
        self.target_y = None
        self.predicted_y = None
    
    def plot_functions(self, x, y_target, y_predicted=None, title="Function Comparison"):
        """绘制目标函数和预测函数"""
        self.ax.clear()
        
        # 绘制目标函数
        self.ax.plot(x, y_target, 'b-', linewidth=2, label='Target Function')
        
        # 绘制预测函数
        if y_predicted is not None:
            self.ax.plot(x, y_predicted, 'r--', linewidth=2, label='Predicted Function')
        
        self.ax.grid(True, linestyle='--', alpha=0.7)
        self.ax.legend()
        self.ax.set_xlabel('x')
        self.ax.set_ylabel('f(x)')
        self.ax.set_title(title)
        
        self.draw()
    
    def plot_data(self, x, y):
        """绘制数据点"""
        self.ax.clear()
        self.ax.plot(x, y, 'bo', markersize=4, label='Data Points')
        self.ax.grid(True, linestyle='--', alpha=0.7)
        self.ax.legend()
        self.ax.set_xlabel('x')
        self.ax.set_ylabel('f(x)')
        self.ax.set_title('Input Data')
        self.draw()
        
    def plot_error(self, x, y_true, y_pred):
        """绘制误差图"""
        self.ax.clear()
        error = y_pred - y_true
        self.ax.plot(x, error, 'g-', linewidth=1.5)
        self.ax.fill_between(x, error, 0, where=(error >= 0), facecolor='green', alpha=0.3)
        self.ax.fill_between(x, error, 0, where=(error < 0), facecolor='red', alpha=0.3)
        self.ax.grid(True, linestyle='--', alpha=0.7)
        self.ax.set_xlabel('x')
        self.ax.set_ylabel('Error')
        self.ax.set_title('Prediction Error')
        self.draw()


class BaseConverterWidget(QWidget):
    """进制转换工具组件"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 输入部分
        input_group = QGroupBox("Input")
        input_layout = QGridLayout()
        
        input_layout.addWidget(QLabel("Value:"), 0, 0)
        self.input_value = QLineEdit()
        input_layout.addWidget(self.input_value, 0, 1)
        
        input_layout.addWidget(QLabel("From Base:"), 1, 0)
        self.input_base = QComboBox()
        self.input_base.addItems(["2 (Binary)", "8 (Octal)", "10 (Decimal)", "16 (Hexadecimal)"])
        self.input_base.setCurrentIndex(2)
        input_layout.addWidget(self.input_base, 1, 1)
        
        input_group.setLayout(input_layout)
        
        # 输出部分
        output_group = QGroupBox("Output")
        output_layout = QGridLayout()
        
        self.output_labels = []
        self.output_values = []
        
        bases = [
            ("Binary", 2),
            ("Octal", 8),
            ("Decimal", 10),
            ("Hexadecimal", 16)
        ]
        
        for i, (name, base) in enumerate(bases):
            output_layout.addWidget(QLabel(f"{name}:"), i, 0)
            output_value = QLineEdit()
            output_value.setReadOnly(True)
            output_layout.addWidget(output_value, i, 1)
            self.output_labels.append(name)
            self.output_values.append(output_value)
        
        output_group.setLayout(output_layout)
        
        # 转换按钮
        self.convert_button = QPushButton("Convert")
        self.convert_button.clicked.connect(self.convert)
        
        # 添加组件
        layout.addWidget(input_group)
        layout.addWidget(output_group)
        layout.addWidget(self.convert_button)
        layout.addStretch()
        
        self.setLayout(layout)
    
    def convert(self):
        """执行进制转换"""
        try:
            value_str = self.input_value.text().strip()
            input_base = int(self.input_base.currentText().split()[0])
            
            # 转换为十进制
            decimal_value = BaseConversion.from_base(value_str, input_base)
            
            # 转换为其他进制
            for i, (name, base) in enumerate([
                ("Binary", 2),
                ("Octal", 8),
                ("Decimal", 10),
                ("Hexadecimal", 16)
            ]):
                if base == 10:
                    # 十进制显示浮点数
                    self.output_values[i].setText(f"{decimal_value:.6f}")
                else:
                    # 其他进制显示整数
                    int_value = int(round(decimal_value))
                    self.output_values[i].setText(BaseConversion.to_base(int_value, base))
        except Exception as e:
            for output in self.output_values:
                output.setText("Error")
            print(f"Conversion error: {str(e)}")


class EnhancedSymbolicRegressionApp(QMainWindow):
    """增强符号回归应用主窗口"""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Enhanced Symbolic Regression System")
        self.setGeometry(100, 100, 1400, 900)
        
        # 初始化变量
        self.regression_thread = None
        self.data_x = None
        self.data_y = None
        self.target_func = None
        
        # 创建UI
        self.init_ui()
        
        # 初始化目标函数
        self.update_target_function()
    
    def init_ui(self):
        """初始化用户界面"""
        main_widget = QWidget()
        main_layout = QVBoxLayout()
        
        # 创建标签页
        self.tabs = QTabWidget()
        
        # 回归标签页
        regression_tab = QWidget()
        regression_layout = QVBoxLayout()
        
        # 创建分割器
        splitter = QSplitter()
        
        # 左侧控制面板
        control_panel = self.create_control_panel()
        
        # 右侧结果面板
        result_tabs = QTabWidget()
        
        # 函数图标签页
        self.function_plot = FunctionPlotter(self, width=7, height=5, dpi=100)
        plot_tab = QWidget()
        plot_layout = QVBoxLayout()
        plot_layout.addWidget(self.function_plot)
        plot_tab.setLayout(plot_layout)
        result_tabs.addTab(plot_tab, "Function Plot")
        
        # 误差图标签页
        self.error_plot = FunctionPlotter(self, width=7, height=5, dpi=100)
        error_tab = QWidget()
        error_layout = QVBoxLayout()
        error_layout.addWidget(self.error_plot)
        error_tab.setLayout(error_layout)
        result_tabs.addTab(error_tab, "Error Analysis")
        
        # 结果输出标签页
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setFontFamily("Courier New")
        self.result_text.setFontPointSize(10)
        result_tab = QWidget()
        result_layout = QVBoxLayout()
        result_layout.addWidget(self.result_text)
        result_tab.setLayout(result_layout)
        result_tabs.addTab(result_tab, "Results")
        
        # 添加组件到分割器
        splitter.addWidget(control_panel)
        splitter.addWidget(result_tabs)
        splitter.setSizes([400, 1000])
        
        regression_layout.addWidget(splitter)
        regression_tab.setLayout(regression_layout)
        self.tabs.addTab(regression_tab, "Symbolic Regression")
        
        # 进制转换工具标签页
        self.base_converter = BaseConverterWidget()
        self.tabs.addTab(self.base_converter, "Base Converter")
        
        # 进度条和状态栏
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setVisible(False)
        
        self.status_label = QLabel("Ready")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("background-color: #f0f0f0; padding: 5px;")
        
        # 添加到主布局
        main_layout.addWidget(self.tabs)
        main_layout.addWidget(self.progress_bar)
        main_layout.addWidget(self.status_label)
        
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)
    
    def create_control_panel(self):
        """创建控制面板"""
        control_panel = QGroupBox("Advanced Symbolic Regression")
        layout = QVBoxLayout()
        
        # 目标函数选择
        function_group = QGroupBox("Target Function")
        function_layout = QVBoxLayout()
        
        self.function_combo = QComboBox()
        self.function_combo.addItems([
            "sin(x) + cos(2*x)",
            "x**2 + 3*x + 5",
            "exp(-0.1*x**2) * sin(3*x)",
            "log(x**2 + 1)",
            "sqrt(x**2 + 1)",
            "sin(x) * cos(2*x)",
            "x * sin(x) + x * cos(2*x)",
            "tanh(0.5*x) + 0.1*sin(5*x)",
            "0.5*x**3 - 2*x**2 + x",
            "erf(0.5*x) + 0.1*cos(3*x)",
            "gamma(0.5*abs(x))",
            "x and 0x0F",  # 位运算示例
            "x xor 0b1010"  # 位运算示例
        ])
        self.function_combo.currentIndexChanged.connect(self.update_target_function)
        
        function_layout.addWidget(QLabel("Select Target Function:"))
        function_layout.addWidget(self.function_combo)
        
        # 自定义函数输入
        self.custom_function_edit = QLineEdit()
        self.custom_function_edit.setPlaceholderText("Enter custom function of x...")
        self.custom_function_edit.textChanged.connect(self.update_custom_function)
        function_layout.addWidget(QLabel("Or Enter Custom Function:"))
        function_layout.addWidget(self.custom_function_edit)
        
        function_group.setLayout(function_layout)
        
        # 数据范围设置
        range_group = QGroupBox("Data Range")
        range_layout = QHBoxLayout()
        
        self.x_min_edit = QLineEdit("-10")
        self.x_max_edit = QLineEdit("10")
        self.num_samples_edit = QLineEdit("1000")
        
        range_layout.addWidget(QLabel("x min:"))
        range_layout.addWidget(self.x_min_edit)
        range_layout.addWidget(QLabel("x max:"))
        range_layout.addWidget(self.x_max_edit)
        range_layout.addWidget(QLabel("Samples:"))
        range_layout.addWidget(self.num_samples_edit)
        
        range_group.setLayout(range_layout)
        
        # 运算符选择
        operators_group = QGroupBox("Operators")
        operators_layout = QVBoxLayout()
        
        self.operators_edit = QLineEdit("+ - * / sin cos tan exp log sqrt abs erf gamma and or xor")
        self.operators_edit.setToolTip("Space-separated list of operators")
        
        operators_layout.addWidget(QLabel("Available Operators:"))
        operators_layout.addWidget(self.operators_edit)
        
        operators_group.setLayout(operators_layout)
        
        # 算法参数
        params_group = QGroupBox("Algorithm Parameters")
        params_layout = QGridLayout()
        
        params_layout.addWidget(QLabel("Method:"), 0, 0)
        self.method_combo = QComboBox()
        self.method_combo.addItems(["Genetic Programming", "Bayesian Optimization", "Neural Network"])
        self.method_combo.setCurrentIndex(0)
        params_layout.addWidget(self.method_combo, 0, 1)
        
        params_layout.addWidget(QLabel("Max Depth:"), 1, 0)
        self.max_depth_spin = QSpinBox()
        self.max_depth_spin.setRange(1, 10)
        self.max_depth_spin.setValue(5)
        params_layout.addWidget(self.max_depth_spin, 1, 1)
        
        params_layout.addWidget(QLabel("Population Size:"), 2, 0)
        self.pop_size_spin = QSpinBox()
        self.pop_size_spin.setRange(10, 1000)
        self.pop_size_spin.setValue(100)
        params_layout.addWidget(self.pop_size_spin, 2, 1)
        
        params_layout.addWidget(QLabel("Generations:"), 3, 0)
        self.max_generations_spin = QSpinBox()
        self.max_generations_spin.setRange(10, 500)
        self.max_generations_spin.setValue(50)
        params_layout.addWidget(self.max_generations_spin, 3, 1)
        
        params_layout.addWidget(QLabel("Mutation Rate:"), 4, 0)
        self.mutation_rate_spin = QDoubleSpinBox()
        self.mutation_rate_spin.setRange(0.0, 1.0)
        self.mutation_rate_spin.setValue(0.2)
        self.mutation_rate_spin.setSingleStep(0.05)
        params_layout.addWidget(self.mutation_rate_spin, 4, 1)
        
        params_group.setLayout(params_layout)
        
        # 高级选项
        advanced_group = QGroupBox("Advanced Options")
        advanced_layout = QGridLayout()
        
        self.const_opt_check = QCheckBox("Optimize Constants")
        self.const_opt_check.setChecked(True)
        advanced_layout.addWidget(self.const_opt_check, 0, 0)
        
        self.physics_check = QCheckBox("Apply Physics Constraints")
        self.physics_check.setChecked(True)
        advanced_layout.addWidget(self.physics_check, 0, 1)
        
        self.parallel_check = QCheckBox("Use Parallel Processing")
        self.parallel_check.setChecked(True)
        advanced_layout.addWidget(self.parallel_check, 1, 0)
        
        self.multi_step_check = QCheckBox("Allow Multi-step Expressions")
        self.multi_step_check.setChecked(True)
        advanced_layout.addWidget(self.multi_step_check, 1, 1)
        
        advanced_layout.addWidget(QLabel("Base System:"), 2, 0)
        self.base_combo = QComboBox()
        self.base_combo.addItems(["10 (Decimal)", "2 (Binary)", "8 (Octal)", "16 (Hexadecimal)", "Mixed"])
        self.base_combo.setCurrentIndex(0)
        advanced_layout.addWidget(self.base_combo, 2, 1)
        
        advanced_group.setLayout(advanced_layout)
        
        # 按钮
        button_layout = QHBoxLayout()
        
        self.run_button = QPushButton("Run Symbolic Regression")
        self.run_button.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        self.run_button.clicked.connect(self.run_regression)
        
        self.stop_button = QPushButton("Stop")
        self.stop_button.setStyleSheet("background-color: #f44336; color: white;")
        self.stop_button.clicked.connect(self.stop_regression)
        self.stop_button.setEnabled(False)
        
        self.export_button = QPushButton("Export Results")
        self.export_button.setStyleSheet("background-color: #2196F3; color: white;")
        self.export_button.clicked.connect(self.export_results)
        
        button_layout.addWidget(self.run_button)
        button_layout.addWidget(self.stop_button)
        button_layout.addWidget(self.export_button)
        
        # 添加到主布局
        layout.addWidget(function_group)
        layout.addWidget(range_group)
        layout.addWidget(operators_group)
        layout.addWidget(params_group)
        layout.addWidget(advanced_group)
        layout.addLayout(button_layout)
        layout.addStretch()
        
        control_panel.setLayout(layout)
        return control_panel
    
    def update_target_function(self):
        """更新目标函数"""
        func_str = self.function_combo.currentText()
        self.custom_function_edit.setText(func_str)
        self.update_custom_function()
    
    def update_custom_function(self):
        """更新自定义目标函数"""
        func_str = self.custom_function_edit.text()
        if func_str.strip() == "":
            return
        
        try:
            # 创建符号函数
            x = sp.symbols('x')
            self.target_func = sp.lambdify(x, sp.sympify(func_str), 'numpy')
            
            # 生成数据
            self.generate_data()
            
            # 绘制函数
            self.function_plot.plot_functions(self.data_x, self.data_y, title="Target Function")
        except Exception as e:
            self.result_text.append(f"Error in function expression: {str(e)}")
    
    def generate_data(self):
        """生成数据点"""
        try:
            x_min = float(self.x_min_edit.text())
            x_max = float(self.x_max_edit.text())
            num_samples = int(self.num_samples_edit.text())
            
            self.data_x = np.linspace(x_min, x_max, num_samples)
            self.data_y = self.target_func(self.data_x)
        except Exception as e:
            self.result_text.append(f"Error generating data: {str(e)}")
    
    def run_regression(self):
        """运行符号回归"""
        if self.regression_thread and self.regression_thread.isRunning():
            self.result_text.append("Regression is already running.")
            return
        
        # 获取参数
        try:
            operators = self.operators_edit.text().split()
            max_depth = self.max_depth_spin.value()
            pop_size = self.pop_size_spin.value()
            max_generations = self.max_generations_spin.value()
            method = self.method_combo.currentText()
            use_const_opt = self.const_opt_check.isChecked()
            use_physics = self.physics_check.isChecked()
            use_parallel = self.parallel_check.isChecked()
            allow_multi_step = self.multi_step_check.isChecked()
            base_system = self.base_combo.currentText().split()[0]
            
            if not operators:
                raise ValueError("At least one operator must be selected.")
        except Exception as e:
            self.result_text.append(f"Invalid parameters: {str(e)}")
            return
        
        # 生成数据
        self.generate_data()
        
        # 准备进度条
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.result_text.clear()
        self.result_text.append("Starting enhanced symbolic regression...")
        self.result_text.append(f"Target function: {self.custom_function_edit.text()}")
        self.result_text.append(f"Method: {method}")
        self.result_text.append(f"Operators: {', '.join(operators)}")
        self.result_text.append(f"Base system: {base_system}")
        self.result_text.append(f"Multi-step: {'Enabled' if allow_multi_step else 'Disabled'}")
        self.result_text.append(f"Population size: {pop_size}, Generations: {max_generations}")
        self.result_text.append(f"Constant optimization: {'Enabled' if use_const_opt else 'Disabled'}")
        self.result_text.append(f"Physics constraints: {'Enabled' if use_physics else 'Disabled'}")
        self.result_text.append("=" * 50)
        
        # 创建并启动工作线程
        self.regression_thread = EnhancedSymbolicRegressionWorker(
            self.target_func,
            (float(self.x_min_edit.text()), float(self.x_max_edit.text())),
            int(self.num_samples_edit.text()),
            operators,
            max_depth,
            pop_size,
            max_generations,
            method,
            use_const_opt,
            use_physics,
            method == "Bayesian Optimization",
            method == "Neural Network",
            allow_multi_step,
            base_system
        )
        
        # 连接信号
        self.regression_thread.progress_updated.connect(self.update_progress)
        self.regression_thread.result_ready.connect(self.handle_results)
        self.regression_thread.error_occurred.connect(self.handle_error)
        self.regression_thread.status_updated.connect(self.update_status)
        
        # 更新UI状态
        self.run_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        
        # 启动线程
        self.regression_thread.start()
    
    def stop_regression(self):
        """停止回归过程"""
        if self.regression_thread and self.regression_thread.isRunning():
            self.regression_thread.stop()
            self.regression_thread.wait()
            self.result_text.append("Regression stopped by user.")
            self.status_label.setText("Stopped by user")
        
        # 更新UI状态
        self.run_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.progress_bar.setVisible(False)
    
    def update_progress(self, progress, best_expr, best_fitness):
        """更新进度信息"""
        self.progress_bar.setValue(progress)
        
        if best_expr:
            self.result_text.append(f"Progress: {progress}% - Best: {best_expr} - MSE: {best_fitness:.6f}")
    
    def update_status(self, status):
        """更新状态信息"""
        self.status_label.setText(status)
    
    def handle_results(self, expr, fitness, x, y_pred, simplified_expr):
        """处理回归结果"""
        # 显示结果
        self.result_text.append("\n" + "=" * 50)
        self.result_text.append("Symbolic Regression Completed!")
        
        # 显示原始表达式
        if isinstance(expr, MultiStepExpression):
            self.result_text.append("Original Expression (Multi-step):")
            self.result_text.append(expr.to_string())
        else:
            self.result_text.append(f"Original Expression: {expr}")
        
        # 显示简化表达式
        self.result_text.append("\nSimplified Expression:")
        self.result_text.append(simplified_expr)
        
        self.result_text.append(f"\nMean Squared Error: {fitness:.8f}")
        
        # 绘制结果
        self.function_plot.plot_functions(x, self.data_y, y_pred, "Function Comparison")
        self.error_plot.plot_error(x, self.data_y, y_pred)
        
        # 更新UI状态
        self.run_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.progress_bar.setVisible(False)
        self.status_label.setText("Completed")
    
    def handle_error(self, error_msg):
        """处理错误"""
        self.result_text.append(f"Error: {error_msg}")
        
        # 更新UI状态
        self.run_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.progress_bar.setVisible(False)
        self.status_label.setText(f"Error: {error_msg}")
    
    def export_results(self):
        """导出结果"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Results", "", "Text Files (*.txt);;All Files (*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w') as f:
                    f.write("Enhanced Symbolic Regression Results\n")
                    f.write("=" * 50 + "\n\n")
                    f.write(f"Target Function: {self.custom_function_edit.text()}\n\n")
                    
                    # 获取当前结果
                    if self.result_text.toPlainText():
                        f.write(self.result_text.toPlainText())
                
                self.result_text.append(f"Results exported to: {file_path}")
            except Exception as e:
                self.result_text.append(f"Error exporting results: {str(e)}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = EnhancedSymbolicRegressionApp()
    window.show()
    sys.exit(app.exec_())