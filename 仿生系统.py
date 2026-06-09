import sys
import os
import numpy as np
import json
import math
import random
import time
from datetime import datetime
from collections import deque
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QPoint, QRect, QSize, QThread, pyqtSignal
from PyQt5.QtGui import (QFont, QColor, QPalette, QLinearGradient, QPainter, QPen, 
                         QBrush, QPixmap, QIcon, QRadialGradient, QConicalGradient)
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QSlider, QProgressBar, QFrame, QTabWidget,
                             QListWidget, QListWidgetItem, QLineEdit, QTextEdit, QComboBox,
                             QCheckBox, QRadioButton, QGroupBox, QSpinBox, QDoubleSpinBox,
                             QFileDialog, QMessageBox, QSplitter, QScrollArea, QSizePolicy,
                             QGraphicsDropShadowEffect, QToolButton, QMenu, QAction, QTableWidget,
                             QTableWidgetItem, QHeaderView, QTreeWidget, QTreeWidgetItem, QDockWidget)

class GeneticAlgorithmThread(QThread):
    """遗传算法计算线程"""
    generation_completed = pyqtSignal(dict)
    simulation_finished = pyqtSignal(list)
    
    def __init__(self, population_size=100, mutation_rate=0.01, generations=100):
        super().__init__()
        self.population_size = population_size
        self.mutation_rate = mutation_rate
        self.generations = generations
        self.running = False
        self.paused = False
        
    def run(self):
        """运行遗传算法"""
        self.running = True
        population = self.initialize_population()
        
        for generation in range(self.generations):
            if not self.running:
                break
                
            while self.paused:
                time.sleep(0.1)
                if not self.running:
                    break
                    
            # 评估适应度
            fitness_scores = self.evaluate_fitness(population)
            
            # 选择
            selected = self.select(population, fitness_scores)
            
            # 交叉
            offspring = self.crossover(selected)
            
            # 变异
            population = self.mutate(offspring)
            
            # 发射信号
            best_individual = population[np.argmax(fitness_scores)]
            stats = {
                'generation': generation,
                'best_fitness': np.max(fitness_scores),
                'avg_fitness': np.mean(fitness_scores),
                'best_individual': best_individual
            }
            self.generation_completed.emit(stats)
            
            time.sleep(0.05)  # 控制速度
            
        self.simulation_finished.emit(population)
        self.running = False
        
    def initialize_population(self):
        """初始化种群"""
        return [np.random.uniform(-10, 10, 5) for _ in range(self.population_size)]
    
    def evaluate_fitness(self, population):
        """评估适应度（示例：求函数最大值）"""
        # 使用Rastrigin函数作为测试函数
        return [self.rastrigin_function(ind) for ind in population]
    
    def rastrigin_function(self, x):
        """Rastrigin测试函数"""
        A = 10
        return A * len(x) + sum([(xi**2 - A * np.cos(2 * math.pi * xi)) for xi in x])
    
    def select(self, population, fitness_scores):
        """选择操作"""
        # 轮盘赌选择
        probabilities = fitness_scores / np.sum(fitness_scores)
        selected_indices = np.random.choice(len(population), size=len(population), p=probabilities)
        return [population[i] for i in selected_indices]
    
    def crossover(self, selected):
        """交叉操作"""
        offspring = []
        for i in range(0, len(selected), 2):
            if i + 1 < len(selected):
                parent1, parent2 = selected[i], selected[i+1]
                crossover_point = np.random.randint(1, len(parent1))
                child1 = np.concatenate([parent1[:crossover_point], parent2[crossover_point:]])
                child2 = np.concatenate([parent2[:crossover_point], parent1[crossover_point:]])
                offspring.extend([child1, child2])
        return offspring
    
    def mutate(self, offspring):
        """变异操作"""
        for i in range(len(offspring)):
            if np.random.random() < self.mutation_rate:
                mutation_point = np.random.randint(len(offspring[i]))
                offspring[i][mutation_point] += np.random.normal(0, 1)
        return offspring

class ParticleSwarmWidget(QWidget):
    """粒子群优化算法可视化"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.particles = []
        self.global_best = None
        self.iteration = 0
        self.function_type = "sphere"  # 测试函数类型
        
        self.setMinimumSize(600, 400)
        self.setStyleSheet("background-color: #0a0a1a;")
        
        # 初始化粒子群
        self.initParticles(30)
        
        # 动画计时器
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.updateSwarm)
        self.timer.start(100)
    
    def initParticles(self, count):
        """初始化粒子"""
        self.particles = []
        for _ in range(count):
            particle = {
                'position': np.random.uniform(-5, 5, 2),
                'velocity': np.random.uniform(-0.5, 0.5, 2),
                'best_position': None,
                'best_fitness': float('inf')
            }
            particle['best_position'] = particle['position'].copy()
            particle['best_fitness'] = self.fitness_function(particle['position'])
            self.particles.append(particle)
        
        # 初始化全局最优
        self.updateGlobalBest()
    
    def fitness_function(self, position):
        """适应度函数"""
        x, y = position
        if self.function_type == "sphere":
            return x**2 + y**2
        elif self.function_type == "rastrigin":
            return 20 + (x**2 - 10*np.cos(2*math.pi*x)) + (y**2 - 10*np.cos(2*math.pi*y))
        else:  # rosenbrock
            return (1-x)**2 + 100*(y-x**2)**2
    
    def updateGlobalBest(self):
        """更新全局最优解"""
        for particle in self.particles:
            if self.global_best is None or particle['best_fitness'] < self.global_best['fitness']:
                self.global_best = {
                    'position': particle['best_position'].copy(),
                    'fitness': particle['best_fitness']
                }
    
    def updateSwarm(self):
        """更新粒子群状态"""
        w = 0.5  # 惯性权重
        c1, c2 = 1.5, 1.5  # 学习因子
        
        for particle in self.particles:
            # 更新速度
            r1, r2 = np.random.random(2), np.random.random(2)
            particle['velocity'] = (w * particle['velocity'] + 
                                  c1 * r1 * (particle['best_position'] - particle['position']) +
                                  c2 * r2 * (self.global_best['position'] - particle['position']))
            
            # 限制速度
            particle['velocity'] = np.clip(particle['velocity'], -1, 1)
            
            # 更新位置
            particle['position'] += particle['velocity']
            
            # 评估适应度
            fitness = self.fitness_function(particle['position'])
            
            # 更新个体最优
            if fitness < particle['best_fitness']:
                particle['best_position'] = particle['position'].copy()
                particle['best_fitness'] = fitness
        
        # 更新全局最优
        self.updateGlobalBest()
        self.iteration += 1
        self.update()
    
    def paintEvent(self, event):
        """绘制粒子群"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 绘制函数等高线背景
        self.drawFunctionContour(painter)
        
        # 绘制粒子
        for particle in self.particles:
            x, y = particle['position']
            # 转换为窗口坐标
            px = (x + 5) / 10 * self.width()
            py = (y + 5) / 10 * self.height()
            
            # 根据适应度确定颜色
            fitness = particle['best_fitness']
            color_value = max(0, min(255, int(fitness * 10)))
            color = QColor(255, 255 - color_value, 100)
            
            # 绘制粒子
            painter.setBrush(QBrush(color))
            painter.setPen(QPen(Qt.white, 1))
            painter.drawEllipse(int(px - 3), int(py - 3), 6, 6)
            
            # 绘制速度方向
            vx, vy = particle['velocity']
            painter.drawLine(int(px), int(py), int(px + vx * 10), int(py + vy * 10))
        
        # 绘制全局最优解
        if self.global_best:
            gx, gy = self.global_best['position']
            px = (gx + 5) / 10 * self.width()
            py = (gy + 5) / 10 * self.height()
            
            painter.setBrush(QBrush(Qt.red))
            painter.setPen(QPen(Qt.yellow, 2))
            painter.drawEllipse(int(px - 5), int(py - 5), 10, 10)
        
        # 绘制信息
        painter.setPen(QPen(Qt.white))
        painter.drawText(10, 20, f"迭代: {self.iteration}, 最优适应度: {self.global_best['fitness']:.4f}")
    
    def drawFunctionContour(self, painter):
        """绘制函数等高线"""
        for i in range(0, self.width(), 10):
            for j in range(0, self.height(), 10):
                # 转换为函数坐标
                x = (i / self.width()) * 10 - 5
                y = (j / self.height()) * 10 - 5
                
                fitness = self.fitness_function([x, y])
                intensity = max(0, min(255, int(fitness * 5)))
                
                color = QColor(intensity, intensity, 100)
                painter.fillRect(i, j, 10, 10, color)

class AntColonyWidget(QWidget):
    """蚁群算法可视化"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.cities = []
        self.pheromones = []
        self.ants = []
        self.best_path = None
        self.best_distance = float('inf')
        
        self.setMinimumSize(600, 400)
        self.setStyleSheet("background-color: #1a1a2e;")
        
        # 初始化城市
        self.initCities(15)
        self.initPheromones()
        
        # 动画计时器
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.updateColony)
        self.timer.start(200)
    
    def initCities(self, count):
        """初始化城市"""
        self.cities = []
        for i in range(count):
            self.cities.append({
                'id': i,
                'x': np.random.randint(50, self.width() - 50),
                'y': np.random.randint(50, self.height() - 50)
            })
    
    def initPheromones(self):
        """初始化信息素"""
        n = len(self.cities)
        self.pheromones = np.ones((n, n))
    
    def initAnts(self, count):
        """初始化蚂蚁"""
        self.ants = []
        for _ in range(count):
            start_city = np.random.randint(len(self.cities))
            ant = {
                'path': [start_city],
                'visited': set([start_city]),
                'distance': 0
            }
            self.ants.append(ant)
    
    def distance(self, city1, city2):
        """计算城市间距离"""
        dx = city1['x'] - city2['x']
        dy = city1['y'] - city2['y']
        return math.sqrt(dx**2 + dy**2)
    
    def updateColony(self):
        """更新蚁群状态"""
        if not self.ants:
            self.initAnts(20)
            return
        
        # 蚂蚁移动
        for ant in self.ants:
            if len(ant['path']) < len(self.cities):
                current_city = ant['path'][-1]
                
                # 选择下一个城市
                next_city = self.selectNextCity(ant, current_city)
                if next_city is not None:
                    ant['path'].append(next_city)
                    ant['visited'].add(next_city)
                    ant['distance'] += self.distance(self.cities[current_city], 
                                                    self.cities[next_city])
        
        # 更新信息素
        self.updatePheromones()
        
        # 检查是否所有蚂蚁都完成了路径
        if all(len(ant['path']) == len(self.cities) for ant in self.ants):
            # 找到最优路径
            for ant in self.ants:
                if ant['distance'] < self.best_distance:
                    self.best_distance = ant['distance']
                    self.best_path = ant['path'].copy()
            
            # 重新初始化蚂蚁
            self.initAnts(20)
        
        self.update()
    
    def selectNextCity(self, ant, current_city):
        """选择下一个城市"""
        unvisited = [i for i in range(len(self.cities)) if i not in ant['visited']]
        if not unvisited:
            return None
        
        # 计算概率
        probabilities = []
        alpha, beta = 1, 2  # 信息素和启发式因子的权重
        
        for city in unvisited:
            pheromone = self.pheromones[current_city][city]
            heuristic = 1 / self.distance(self.cities[current_city], self.cities[city])
            probabilities.append(pheromone**alpha * heuristic**beta)
        
        # 选择城市
        probabilities = np.array(probabilities)
        probabilities /= probabilities.sum()
        
        return np.random.choice(unvisited, p=probabilities)
    
    def updatePheromones(self):
        """更新信息素"""
        # 信息素挥发
        evaporation = 0.5
        self.pheromones *= (1 - evaporation)
        
        # 蚂蚁释放信息素
        for ant in self.ants:
            if len(ant['path']) == len(self.cities):
                pheromone_deposit = 100 / ant['distance']
                
                for i in range(len(ant['path']) - 1):
                    city1, city2 = ant['path'][i], ant['path'][i+1]
                    self.pheromones[city1][city2] += pheromone_deposit
                    self.pheromones[city2][city1] += pheromone_deposit
    
    def paintEvent(self, event):
        """绘制蚁群算法"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 绘制城市
        for city in self.cities:
            painter.setBrush(QBrush(QColor(100, 200, 255)))
            painter.setPen(QPen(Qt.white, 1))
            painter.drawEllipse(city['x'] - 5, city['y'] - 5, 10, 10)
            painter.drawText(city['x'] + 8, city['y'] + 8, str(city['id']))
        
        # 绘制信息素
        max_pheromone = np.max(self.pheromones)
        if max_pheromone > 0:
            for i in range(len(self.cities)):
                for j in range(i + 1, len(self.cities)):
                    if self.pheromones[i][j] > 0.1:
                        city1, city2 = self.cities[i], self.cities[j]
                        intensity = min(255, int(255 * self.pheromones[i][j] / max_pheromone))
                        color = QColor(255, 255, 100, intensity)
                        
                        painter.setPen(QPen(color, 2))
                        painter.drawLine(city1['x'], city1['y'], city2['x'], city2['y'])
        
        # 绘制蚂蚁路径
        for ant in self.ants:
            if len(ant['path']) > 1:
                path_color = QColor(255, 100, 100, 100)
                painter.setPen(QPen(path_color, 1))
                
                for i in range(len(ant['path']) - 1):
                    city1 = self.cities[ant['path'][i]]
                    city2 = self.cities[ant['path'][i+1]]
                    painter.drawLine(city1['x'], city1['y'], city2['x'], city2['y'])
        
        # 绘制最优路径
        if self.best_path and len(self.best_path) == len(self.cities):
            painter.setPen(QPen(Qt.green, 3))
            for i in range(len(self.best_path)):
                city1 = self.cities[self.best_path[i]]
                city2 = self.cities[self.best_path[(i + 1) % len(self.best_path)]]
                painter.drawLine(city1['x'], city1['y'], city2['x'], city2['y'])
        
        # 绘制信息
        painter.setPen(QPen(Qt.white))
        painter.drawText(10, 20, f"最优路径长度: {self.best_distance:.2f}" if self.best_distance != float('inf') else "计算中...")

class BioInspiredButton(QPushButton):
    """增强版仿生按钮控件"""
    
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setMouseTracking(True)
        self.setCursor(Qt.PointingHandCursor)
        
        # 动画效果
        self.animation = QPropertyAnimation(self, b"geometry")
        self.animation.setDuration(200)
        self.animation.setEasingCurve(QEasingCurve.OutBack)
        
        # 增强阴影效果
        self.shadow = QGraphicsDropShadowEffect()
        self.shadow.setBlurRadius(15)
        self.shadow.setColor(QColor(0, 0, 0, 80))
        self.shadow.setOffset(0, 3)
        self.setGraphicsEffect(self.shadow)
        
        # 脉冲动画计时器
        self.pulse_timer = QTimer(self)
        self.pulse_timer.timeout.connect(self.pulseEffect)
        self.pulse_phase = 0
        
        # 样式
        self.setMinimumHeight(40)
        self.setFont(QFont("Arial", 10, QFont.Bold))
        
    def enterEvent(self, event):
        """鼠标进入时的动画"""
        self.animation.stop()
        rect = self.geometry()
        self.animation.setStartValue(rect)
        self.animation.setEndValue(QRect(rect.x()-2, rect.y()-2, rect.width()+4, rect.height()+4))
        self.animation.start()
        
        # 增强阴影
        self.shadow.setBlurRadius(20)
        self.shadow.setColor(QColor(0, 0, 0, 100))
        
        # 开始脉冲效果
        self.pulse_timer.start(50)
        super().enterEvent(event)
        
    def leaveEvent(self, event):
        """鼠标离开时的动画"""
        self.animation.stop()
        rect = self.geometry()
        self.animation.setStartValue(rect)
        self.animation.setEndValue(QRect(rect.x()+2, rect.y()+2, rect.width()-4, rect.height()-4))
        self.animation.start()
        
        # 恢复阴影
        self.shadow.setBlurRadius(15)
        self.shadow.setColor(QColor(0, 0, 0, 80))
        
        # 停止脉冲效果
        self.pulse_timer.stop()
        self.pulse_phase = 0
        super().leaveEvent(event)
    
    def pulseEffect(self):
        """脉冲光效"""
        self.pulse_phase = (self.pulse_phase + 0.2) % (2 * math.pi)
        intensity = int(100 + 50 * math.sin(self.pulse_phase))
        self.shadow.setColor(QColor(100, 150, 255, intensity))
        self.update()

class NeuralNetworkWidget(QWidget):
    """增强版神经网络可视化控件"""
    
    def __init__(self, layers=[3, 4, 4, 2], parent=None):
        super().__init__(parent)
        self.layers = layers
        self.neurons = []
        self.connections = []
        self.active_neurons = set()
        self.active_connections = set()
        self.activation_history = deque(maxlen=100)
        
        # 设置背景
        self.setStyleSheet("background-color: #1a1a2e;")
        self.setMinimumSize(400, 300)
        
        # 动画计时器
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.animate)
        self.timer.start(100)
        
        # 初始化网络
        self.initNetwork()
        
    def initNetwork(self):
        """初始化神经网络结构"""
        self.neurons = []
        self.connections = []
        
        # 创建神经元
        layer_height = self.height() / (max(self.layers) + 1)
        for i, neurons_count in enumerate(self.layers):
            layer_width = self.width() / (len(self.layers) + 1)
            x = (i + 1) * layer_width
            neuron_layer = []
            
            # 垂直居中排列神经元
            start_y = (self.height() - (neurons_count - 1) * layer_height) / 2
            for j in range(neurons_count):
                y = start_y + j * layer_height
                neuron_layer.append((x, y))
            
            self.neurons.append(neuron_layer)
            
        # 创建连接
        for i in range(len(self.neurons) - 1):
            for j, neuron1 in enumerate(self.neurons[i]):
                for k, neuron2 in enumerate(self.neurons[i + 1]):
                    self.connections.append((i, j, i + 1, k))
    
    def resizeEvent(self, event):
        """窗口大小改变时重新初始化网络"""
        self.initNetwork()
        super().resizeEvent(event)
    
    def animate(self):
        """动画更新"""
        # 模拟神经网络激活
        if np.random.random() < 0.2:
            # 从输入层开始激活
            layer_idx = 0
            neuron_idx = np.random.randint(0, self.layers[layer_idx])
            self.propagateActivation(layer_idx, neuron_idx)
        
        # 随机激活一些神经元
        if np.random.random() < 0.1:
            layer_idx = np.random.randint(0, len(self.layers))
            neuron_idx = np.random.randint(0, self.layers[layer_idx])
            self.active_neurons.add((layer_idx, neuron_idx))
            
        # 限制活跃神经元数量
        if len(self.active_neurons) > 15:
            self.active_neurons.pop()
        
        self.update()
    
    def propagateActivation(self, start_layer, start_neuron):
        """模拟激活传播"""
        current_layer = start_layer
        current_neuron = start_neuron
        
        while current_layer < len(self.layers) - 1:
            # 激活当前神经元
            self.active_neurons.add((current_layer, current_neuron))
            
            # 选择下一层神经元（模拟前向传播）
            next_layer = current_layer + 1
            next_neuron = np.random.randint(0, self.layers[next_layer])
            
            # 激活连接
            conn_index = self.findConnection(current_layer, current_neuron, next_layer, next_neuron)
            if conn_index is not None:
                self.active_connections.add(conn_index)
                # 记录激活历史
                self.activation_history.append({
                    'from_layer': current_layer,
                    'from_neuron': current_neuron,
                    'to_layer': next_layer,
                    'to_neuron': next_neuron,
                    'timestamp': time.time()
                })
            
            current_layer = next_layer
            current_neuron = next_neuron
            
            # 有一定概率停止传播
            if np.random.random() < 0.3:
                break
    
    def findConnection(self, from_layer, from_neuron, to_layer, to_neuron):
        """查找连接索引"""
        for i, conn in enumerate(self.connections):
            l1, n1, l2, n2 = conn
            if l1 == from_layer and n1 == from_neuron and l2 == to_layer and n2 == to_neuron:
                return i
        return None
    
    def paintEvent(self, event):
        """绘制神经网络"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 绘制连接
        for i, conn in enumerate(self.connections):
            layer1_idx, neuron1_idx, layer2_idx, neuron2_idx = conn
            x1, y1 = self.neurons[layer1_idx][neuron1_idx]
            x2, y2 = self.neurons[layer2_idx][neuron2_idx]
            
            if i in self.active_connections:
                # 活跃连接使用脉冲效果
                active_phase = time.time() % 1
                alpha = int(150 + 100 * math.sin(active_phase * 2 * math.pi))
                active_pen = QPen(QColor(150, 150, 255, alpha))
                active_pen.setWidth(3)
                painter.setPen(active_pen)
            else:
                pen = QPen(QColor(100, 100, 200, 80))
                pen.setWidth(1)
                painter.setPen(pen)
            
            painter.drawLine(int(x1), int(y1), int(x2), int(y2))
        
        # 绘制神经元
        for i, layer in enumerate(self.neurons):
            for j, (x, y) in enumerate(layer):
                # 确定神经元状态
                is_active = (i, j) in self.active_neurons
                activation_time = 0
                
                # 查找最近的激活时间
                for activation in reversed(self.activation_history):
                    if (activation['to_layer'] == i and activation['to_neuron'] == j):
                        activation_time = time.time() - activation['timestamp']
                        break
                
                # 计算激活强度
                if is_active:
                    intensity = max(0.5, 1 - activation_time / 2)
                    color = QColor(100, 200, 255, int(255 * intensity))
                    size = 8 + 4 * intensity
                else:
                    color = QColor(150, 150, 200, 150)
                    size = 8
                
                # 绘制神经元
                gradient = QRadialGradient(x, y, size)
                gradient.setColorAt(0, color.lighter(150))
                gradient.setColorAt(1, color.darker(150))
                
                painter.setBrush(QBrush(gradient))
                painter.setPen(QPen(QColor(200, 200, 255), 1))
                painter.drawEllipse(int(x - size/2), int(y - size/2), int(size), int(size))
        
        # 清除非活跃连接
        if len(self.active_connections) > 10:
            self.active_connections.clear()

# 由于篇幅限制，这里只展示了部分增强代码
# 完整的增强版本还包括：
# 1. 更复杂的DNAStrandWidget（支持3D效果）
# 2. 增强的BioProgressBar（支持多种细胞类型）
# 3. 新增的EcosystemSimulationWidget（生态系统模拟）
# 4. 数据分析和可视化工具
# 5. 实验记录和导出功能

class EnhancedBioInspiredToolkit(QMainWindow):
    """增强版仿生系统工具库"""
    
    def __init__(self):
        super().__init__()
        self.genetic_algorithm = None
        self.simulation_data = []
        self.initUI()
        
    def initUI(self):
        """初始化增强的用户界面"""
        self.setWindowTitle("高级仿生系统工具库 v2.0")
        self.setGeometry(100, 100, 1400, 900)
        
        # 设置更丰富的样式
        self.setStyleSheet(self.getEnhancedStyle())
        
        # 创建中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # 创建标签页
        tab_widget = QTabWidget()
        main_layout.addWidget(tab_widget)
        
        # 添加增强的功能标签页
        self.createEnhancedVisualizationTab(tab_widget)
        self.createAlgorithmTab(tab_widget)
        self.createSimulationTab(tab_widget)
        self.createAnalysisTab(tab_widget)
        self.createDataTab(tab_widget)
        
        # 创建状态栏和工具栏
        self.createStatusBar()
        self.createToolBars()
        
        # 初始化数据
        self.loadDefaultSettings()
    
    def getEnhancedStyle(self):
        """返回增强的样式表"""
        return """
            QMainWindow {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                          stop:0 #2d2d44, stop:1 #1a1a2e);
                color: #e0e0e0;
                font-family: Arial;
            }
            QTabWidget::pane {
                border: 2px solid #444;
                background-color: #3a3a5a;
                border-radius: 8px;
            }
            QTabBar::tab {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                           stop:0 #3a3a5a, stop:1 #2a2a3a);
                color: #b0b0b0;
                padding: 10px 20px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                margin-right: 2px;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                           stop:0 #5a5a8a, stop:1 #4a4a7a);
                color: #ffffff;
                border-bottom: 3px solid #00aaff;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #555;
                border-radius: 8px;
                margin-top: 1ex;
                padding-top: 15px;
                background-color: #2a2a3a;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 5px 15px;
                background-color: #3a3a5a;
                color: #ffffff;
                border-radius: 5px;
            }
            QTextEdit, QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
                background-color: #2a2a3a;
                color: #ffffff;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 5px;
            }
            QSlider::groove:horizontal {
                border: 1px solid #555;
                height: 8px;
                background: #2a2a3a;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                          stop:0 #00aaff, stop:1 #0088cc);
                border: 1px solid #555;
                width: 18px;
                margin: -5px 0;
                border-radius: 9px;
            }
        """
    
    def createEnhancedVisualizationTab(self, tab_widget):
        """创建增强的可视化标签页"""
        tab = QWidget()
        layout = QHBoxLayout(tab)
        
        # 使用分割器创建更灵活的布局
        main_splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(main_splitter)
        
        # 左侧：算法可视化
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        # 粒子群优化
        pso_group = QGroupBox("粒子群优化算法")
        pso_layout = QVBoxLayout(pso_group)
        self.pso_widget = ParticleSwarmWidget()
        pso_layout.addWidget(self.pso_widget)
        
        # 控制面板
        pso_controls = QHBoxLayout()
        pso_controls.addWidget(QLabel("函数类型:"))
        self.pso_function = QComboBox()
        self.pso_function.addItems(["sphere", "rastrigin", "rosenbrock"])
        self.pso_function.currentTextChanged.connect(self.updatePSOFunction)
        pso_controls.addWidget(self.pso_function)
        pso_controls.addStretch()
        pso_layout.addLayout(pso_controls)
        
        left_layout.addWidget(pso_group)
        
        # 蚁群算法
        aco_group = QGroupBox("蚁群算法 - TSP问题")
        aco_layout = QVBoxLayout(aco_group)
        self.aco_widget = AntColonyWidget()
        aco_layout.addWidget(self.aco_widget)
        left_layout.addWidget(aco_group)
        
        # 右侧：神经网络和DNA
        right_splitter = QSplitter(Qt.Vertical)
        
        # 神经网络可视化
        nn_group = QGroupBox("神经网络可视化")
        nn_layout = QVBoxLayout(nn_group)
        self.nn_widget = NeuralNetworkWidget([5, 8, 6, 4, 3])
        nn_layout.addWidget(self.nn_widget)
        
        nn_controls = QHBoxLayout()
        nn_controls.addWidget(QLabel("网络结构:"))
        self.nn_structure = QLineEdit("5,8,6,4,3")
        nn_controls.addWidget(self.nn_structure)
        update_nn_btn = BioInspiredButton("更新网络")
        update_nn_btn.clicked.connect(self.updateNeuralNetwork)
        nn_controls.addWidget(update_nn_btn)
        nn_layout.addLayout(nn_controls)
        
        right_splitter.addWidget(nn_group)
        
        # DNA可视化区域（简化为占位符）
        dna_group = QGroupBox("生物分子可视化")
        dna_layout = QVBoxLayout(dna_group)
        dna_label = QLabel("DNA/蛋白质分子3D可视化区域")
        dna_label.setAlignment(Qt.AlignCenter)
        dna_label.setStyleSheet("font-size: 16px; color: #888; background-color: #1a1a2e;")
        dna_label.setMinimumHeight(150)
        dna_layout.addWidget(dna_label)
        right_splitter.addWidget(dna_group)
        
        # 设置分割器比例
        right_splitter.setSizes([400, 200])
        
        # 添加到主分割器
        main_splitter.addWidget(left_widget)
        main_splitter.addWidget(right_splitter)
        main_splitter.setSizes([700, 500])
        
        tab_widget.addTab(tab, "算法可视化")
    
    def createAlgorithmTab(self, tab_widget):
        """创建算法实验标签页"""
        # 实现遗传算法、模拟退火等算法的实验界面
        pass
    
    def createSimulationTab(self, tab_widget):
        """创建仿真标签页"""
        # 实现生态系统、进化过程等复杂仿真
        pass
    
    def createAnalysisTab(self, tab_widget):
        """创建数据分析标签页"""
        # 实现数据可视化、统计分析等功能
        pass
    
    def createDataTab(self, tab_widget):
        """创建数据管理标签页"""
        # 实现数据导入导出、项目管理等功能
        pass
    
    def createStatusBar(self):
        """创建状态栏"""
        status_bar = self.statusBar()
        status_bar.showMessage("高级仿生系统工具库已就绪 - 所有模块加载完成")
        
        # 添加系统状态指示器
        self.cpu_label = QLabel("CPU: 0%")
        self.memory_label = QLabel("内存: 0MB")
        status_bar.addPermanentWidget(self.cpu_label)
        status_bar.addPermanentWidget(self.memory_label)
    
    def createToolBars(self):
        """创建工具栏"""
        toolbar = self.addToolBar("主工具栏")
        
        # 添加工具按钮
        new_action = QAction(QIcon(), "新建项目", self)
        open_action = QAction(QIcon(), "打开项目", self)
        save_action = QAction(QIcon(), "保存项目", self)
        
        toolbar.addAction(new_action)
        toolbar.addAction(open_action)
        toolbar.addAction(save_action)
        toolbar.addSeparator()
    
    def updatePSOFunction(self, function_type):
        """更新粒子群优化函数"""
        self.pso_widget.function_type = function_type
        self.pso_widget.initParticles(30)
    
    def updateNeuralNetwork(self):
        """更新神经网络结构"""
        try:
            layers_text = self.nn_structure.text()
            layers = [int(x.strip()) for x in layers_text.split(',')]
            if len(layers) >= 2 and all(l > 0 for l in layers):
                self.nn_widget.layers = layers
                self.nn_widget.initNetwork()
                self.nn_widget.update()
        except ValueError:
            QMessageBox.warning(self, "输入错误", "请输入有效的网络结构")
    
    def loadDefaultSettings(self):
        """加载默认设置"""
        # 这里可以加载用户设置或默认配置
        pass

def main():
    """主函数"""
    app = QApplication(sys.argv)
    
    # 设置应用程序样式和字体
    app.setStyle('Fusion')
    app.setFont(QFont("Arial", 10))
    
    # 创建并显示主窗口
    window = EnhancedBioInspiredToolkit()
    window.show()
    
    # 运行应用程序
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()