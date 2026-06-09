import sys
import random
import numpy as np
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QSlider, QSpinBox,
                             QDoubleSpinBox, QGroupBox, QGraphicsView, QGraphicsScene,
                             QGraphicsEllipseItem, QGraphicsTextItem, QSplitter,
                             QTabWidget, QComboBox, QCheckBox, QFileDialog, QMessageBox,
                             QTableWidget, QTableWidgetItem, QHeaderView, QTextEdit)
from PyQt5.QtCore import Qt, QTimer, QPointF, QRectF, QSize
from PyQt5.QtGui import QColor, QPen, QBrush, QPainter, QFont, QIcon
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.gridspec import GridSpec
import pickle
import json
from datetime import datetime
import pandas as pd
from scipy import stats
from collections import defaultdict, deque
import math


class Gene:
    """基因类，表示生物的一个特征"""
    def __init__(self, name, value_range=(0.0, 1.0), mutation_rate=0.01, dominant=True):
        self.name = name
        self.value_range = value_range
        self.value = random.uniform(*value_range)
        self.mutation_rate = mutation_rate
        self.dominant = dominant
        self.alleles = [self.value]  # 等位基因
        self.current_allele = 0
    
    def mutate(self):
        """基因突变"""
        mutations = 0
        for i in range(len(self.alleles)):
            if random.random() < self.mutation_rate:
                # 小幅度随机变化
                change = random.gauss(0, 0.1)
                new_value = self.alleles[i] + change
                # 确保值在范围内
                self.alleles[i] = max(self.value_range[0], min(self.value_range[1], new_value))
                mutations += 1
        
        # 有概率添加新的等位基因
        if random.random() < self.mutation_rate / 10 and len(self.alleles) < 3:
            new_allele = random.uniform(*value_range)
            self.alleles.append(new_allele)
            mutations += 1
            
        return mutations
    
    def get_value(self):
        """获取当前表达的基因值"""
        return self.alleles[self.current_allele]
    
    def copy(self):
        """创建基因的副本"""
        new_gene = Gene(self.name, self.value_range, self.mutation_rate, self.dominant)
        new_gene.value = self.value
        new_gene.alleles = self.alleles.copy()
        new_gene.current_allele = self.current_allele
        return new_gene


class Genome:
    """基因组，包含多个基因"""
    def __init__(self):
        self.genes = {}
        self.gene_network = {}  # 基因调控网络
    
    def add_gene(self, gene):
        """添加基因"""
        self.genes[gene.name] = gene
    
    def add_gene_interaction(self, source_gene, target_gene, effect):
        """添加基因间相互作用"""
        if source_gene not in self.gene_network:
            self.gene_network[source_gene] = {}
        self.gene_network[source_gene][target_gene] = effect
    
    def get_value(self, gene_name):
        """获取基因值，考虑基因调控网络的影响"""
        if gene_name not in self.genes:
            return 0.0
            
        base_value = self.genes[gene_name].get_value()
        
        # 应用基因调控网络的影响
        total_effect = 1.0
        for source_gene, targets in self.gene_network.items():
            if source_gene in self.genes and gene_name in targets:
                source_value = self.genes[source_gene].get_value()
                effect = targets[gene_name]
                total_effect *= 1.0 + (source_value - 0.5) * effect
        
        return max(0.0, min(1.0, base_value * total_effect))
    
    def mutate(self):
        """基因组突变"""
        mutations = 0
        for gene in self.genes.values():
            mutations += gene.mutate()
        
        # 基因网络突变
        for source_gene, targets in list(self.gene_network.items()):
            for target_gene in list(targets.keys()):
                if random.random() < 0.001:  # 网络连接突变率
                    if random.random() < 0.5:
                        # 改变连接强度
                        self.gene_network[source_gene][target_gene] = random.gauss(0, 0.5)
                    else:
                        # 移除连接
                        del self.gene_network[source_gene][target_gene]
                        if not self.gene_network[source_gene]:
                            del self.gene_network[source_gene]
        
        # 添加新连接
        if random.random() < 0.001 and self.genes:
            source = random.choice(list(self.genes.keys()))
            target = random.choice(list(self.genes.keys()))
            if source != target:
                if source not in self.gene_network:
                    self.gene_network[source] = {}
                self.gene_network[source][target] = random.gauss(0, 0.5)
                mutations += 1
        
        return mutations
    
    def copy(self):
        """创建基因组的副本"""
        new_genome = Genome()
        for name, gene in self.genes.items():
            new_genome.genes[name] = gene.copy()
        
        # 复制基因网络
        for source, targets in self.gene_network.items():
            new_genome.gene_network[source] = targets.copy()
        
        return new_genome
    
    def crossover(self, other):
        """与另一个基因组交叉繁殖"""
        child_genome = Genome()
        
        # 交叉每个基因
        for name, gene in self.genes.items():
            if name in other.genes:
                # 随机选择父母一方的基因
                if random.random() < 0.5:
                    child_genome.genes[name] = gene.copy()
                else:
                    child_genome.genes[name] = other.genes[name].copy()
                
                # 等位基因随机选择
                if random.random() < 0.2:  # 20%概率选择另一个等位基因
                    if len(child_genome.genes[name].alleles) > 1:
                        child_genome.genes[name].current_allele = random.randint(0, len(child_genome.genes[name].alleles)-1)
        
        # 随机选择父母的基因网络连接
        all_sources = set(self.gene_network.keys()) | set(other.gene_network.keys())
        for source in all_sources:
            if source in self.gene_network and source in other.gene_network:
                # 两个父母都有这个源基因
                if random.random() < 0.5:
                    child_genome.gene_network[source] = self.gene_network[source].copy()
                else:
                    child_genome.gene_network[source] = other.gene_network[source].copy()
            elif source in self.gene_network:
                child_genome.gene_network[source] = self.gene_network[source].copy()
            else:
                child_genome.gene_network[source] = other.gene_network[source].copy()
        
        return child_genome


class Species:
    """物种类，用于分类和追踪生物"""
    species_counter = 0
    
    def __init__(self, representative):
        Species.species_counter += 1
        self.id = Species.species_counter
        self.representative = representative  # 代表个体
        self.members = []  # 属于该物种的所有个体
        self.color = self.generate_species_color()
        self.emergence_time = 0
        self.extinction_time = None
        self.common_ancestor = None
    
    def generate_species_color(self):
        """为物种生成一个独特的颜色"""
        return QColor(random.randint(50, 200), random.randint(50, 200), random.randint(50, 200))
    
    def add_member(self, organism):
        """添加成员到物种"""
        if organism not in self.members:
            self.members.append(organism)
            organism.species = self
    
    def remove_member(self, organism):
        """从物种中移除成员"""
        if organism in self.members:
            self.members.remove(organism)
        
        # 如果物种没有成员，标记为灭绝
        if not self.members:
            self.extinction_time = organism.environment.simulator.generation if hasattr(organism, 'environment') and hasattr(organism.environment, 'simulator') else 0
    
    def is_similar(self, organism, similarity_threshold=0.85):
        """检查生物是否与该物种相似"""
        # 基于基因组的相似性计算
        similarity = self.calculate_similarity(organism)
        return similarity >= similarity_threshold
    
    def calculate_similarity(self, organism):
        """计算与代表个体的基因相似性"""
        similarity = 0
        count = 0
        
        for gene_name, gene in self.representative.genome.genes.items():
            if gene_name in organism.genome.genes:
                value1 = gene.get_value()
                value2 = organism.genome.genes[gene_name].get_value()
                similarity += 1.0 - abs(value1 - value2)
                count += 1
        
        return similarity / count if count > 0 else 0


class Organism:
    """生物体类"""
    organism_counter = 0
    
    def __init__(self, genome=None, position=(0, 0), parent1=None, parent2=None):
        Organism.organism_counter += 1
        self.id = Organism.organism_counter
        self.genome = genome if genome else Genome()
        self.position = position
        self.age = 0
        self.energy = 100
        self.max_energy = 200
        self.alive = True
        self.children = 0
        self.last_reproduction = 0
        self.species = None
        self.parents = (parent1, parent2)
        self.generation = 0
        if parent1 and parent2:
            self.generation = max(parent1.generation, parent2.generation) + 1
        self.memory = deque(maxlen=10)  # 简单的记忆系统
        self.social_group = None
        self.cooperation_partners = []
        
        # 计算特征
        self.color = self.calculate_color()
        self.size = 5 + self.genome.get_value("size") * 10
        self.diet = "herbivore" if self.genome.get_value("diet") < 0.3 else \
                   "carnivore" if self.genome.get_value("diet") > 0.7 else "omnivore"
    
    def calculate_color(self):
        """根据基因计算颜色"""
        r = int(self.genome.get_value("color_red") * 255)
        g = int(self.genome.get_value("color_green") * 255)
        b = int(self.genome.get_value("color_blue") * 255)
        return QColor(r, g, b)
    
    def update(self, environment):
        """更新生物体状态"""
        if not self.alive:
            return False
        
        self.age += 1
        self.energy -= 1  # 基础代谢消耗
        
        # 环境适应性消耗
        env_factor = self.calculate_environment_fitness(environment)
        self.energy -= (1 - env_factor) * 5
        
        # 移动消耗
        speed = self.genome.get_value("speed")
        self.energy -= speed * 0.5
        
        # 获取食物
        self.feed(environment)
        
        # 社交行为
        self.social_behavior(environment)
        
        # 检查死亡
        if self.energy <= 0 or self.age > self.genome.get_value("lifespan") * 100:
            self.alive = False
            if self.species:
                self.species.remove_member(self)
            return False
        
        # 繁殖检查
        reproduction_cooldown = self.age - self.last_reproduction
        min_cooldown = max(10, 30 - self.genome.get_value("reproduction_rate") * 20)
        
        if (self.energy > 100 and self.age > 20 and 
            reproduction_cooldown > min_cooldown and
            random.random() < self.genome.get_value("reproduction_rate")):
            self.reproduce(environment)
        
        # 移动
        self.move(environment)
        
        return True
    
    def calculate_environment_fitness(self, environment):
        """计算环境适应性"""
        fitness = 1.0
        
        # 温度适应性
        temp_pref = self.genome.get_value("temperature_preference")
        temp_env = environment.get_temperature(self.position)
        temp_diff = abs(temp_pref - temp_env)
        fitness *= 1.0 - (temp_diff * 0.8)
        
        # 湿度适应性
        humidity_pref = self.genome.get_value("humidity_preference")
        humidity_env = environment.get_humidity(self.position)
        humidity_diff = abs(humidity_pref - humidity_env)
        fitness *= 1.0 - (humidity_diff * 0.8)
        
        # 季节适应性
        season_factor = environment.get_season_factor(self.genome.get_value("season_adaptation"))
        fitness *= season_factor
        
        return max(0.0, min(1.0, fitness))
    
    def feed(self, environment):
        """进食行为"""
        feeding_efficiency = self.genome.get_value("feeding_efficiency")
        
        if self.diet == "herbivore" or self.diet == "omnivore":
            # 食草动物吃植物
            food_value = environment.get_food(self.position)
            if food_value > 0:
                energy_gain = food_value * feeding_efficiency * 10
                self.energy = min(self.max_energy, self.energy + energy_gain)
                environment.consume_food(self.position, energy_gain / 10)
        
        if (self.diet == "carnivore" or self.diet == "omnivore") and self.energy < 100:
            # 食肉动物捕食其他生物
            prey = self.find_prey(environment)
            if prey and prey.alive:  # 确保猎物还活着
                attack_success = self.attack(prey)
                if attack_success:
                    energy_gain = prey.energy * 0.5 * feeding_efficiency
                    self.energy = min(self.max_energy, self.energy + energy_gain)
                    prey.alive = False
                    if prey.species:
                        prey.species.remove_member(prey)
                    # 不要在这里直接从环境中移除，让环境更新循环处理
    
    def find_prey(self, environment):
        """寻找猎物"""
        vision_range = self.genome.get_value("vision_range") * 20
        min_size_ratio = 0.5  # 只攻击比自己小的生物
        
        potential_prey = []
        for organism in environment.organisms:
            if (organism is not self and organism.alive and 
                organism.diet != "carnivore" and  # 通常不捕食食肉动物
                organism.size < self.size * min_size_ratio):
                
                distance = np.sqrt((self.position[0] - organism.position[0])**2 + 
                                  (self.position[1] - organism.position[1])**2)
                
                if distance < vision_range:
                    potential_prey.append((organism, distance))
        
        if potential_prey:
            # 选择最近的猎物
            potential_prey.sort(key=lambda x: x[1])
            return potential_prey[0][0]
        
        return None
    
    def attack(self, prey):
        """攻击猎物"""
        attack_strength = self.genome.get_value("attack_strength")
        defense_strength = prey.genome.get_value("defense_strength")
        
        # 攻击成功概率基于攻击和防御强度的比较
        success_probability = attack_strength / (attack_strength + defense_strength)
        return random.random() < success_probability
    
    def social_behavior(self, environment):
        """社交行为"""
        social_need = self.genome.get_value("social_need")
        
        if social_need > 0.5:
            # 寻找附近的同类
            nearby_organisms = []
            for organism in environment.organisms:
                if (organism is not self and organism.alive and 
                    organism.species == self.species):
                    
                    distance = np.sqrt((self.position[0] - organism.position[0])**2 + 
                                      (self.position[1] - organism.position[1])**2)
                    
                    if distance < 15:  # 社交距离
                        nearby_organisms.append(organism)
            
            # 如果有足够多的同类，形成社会群体
            if len(nearby_organisms) >= 3 and not self.social_group:
                self.form_social_group(nearby_organisms, environment)
            
            # 社会群体合作
            if self.social_group:
                self.cooperate(environment)
    
    def form_social_group(self, organisms, environment):
        """形成社会群体"""
        self.social_group = set(organisms)
        self.social_group.add(self)
        
        for organism in organisms:
            organism.social_group = self.social_group
    
    def cooperate(self, environment):
        """合作行为"""
        if random.random() < 0.1:  # 10%的概率进行合作
            # 共享食物信息
            food_locations = []
            for organism in self.social_group:
                if hasattr(organism, 'memory'):
                    food_locations.extend([pos for pos in organism.memory if environment.get_food(pos) > 0])
            
            if food_locations:
                # 记住食物位置
                self.memory.append(random.choice(food_locations))
            
            # 共享能量（亲属选择）
            if self.energy > 120:
                neediest = None
                min_energy = float('inf')
                
                for organism in self.social_group:
                    if organism.energy < min_energy and organism is not self and organism.alive:
                        min_energy = organism.energy
                        neediest = organism
                
                if neediest and min_energy < 50:
                    # 共享能量
                    share_amount = (self.energy - 100) * 0.3
                    self.energy -= share_amount
                    neediest.energy += share_amount
    
    def move(self, environment):
        """移动生物体"""
        speed = self.genome.get_value("speed")
        
        # 决定移动方向
        direction = self.decide_movement_direction(environment)
        
        dx = np.cos(direction) * speed
        dy = np.sin(direction) * speed
        
        new_x = self.position[0] + dx
        new_y = self.position[1] + dy
        
        # 确保在环境范围内
        new_x = max(0, min(environment.width - 1, new_x))
        new_y = max(0, min(environment.height - 1, new_y))
        
        self.position = (new_x, new_y)
    
    def decide_movement_direction(self, environment):
        """决定移动方向"""
        # 基本随机方向
        direction = random.uniform(0, 2 * np.pi)
        
        # 环境偏好影响
        temp_pref = self.genome.get_value("temperature_preference")
        temp_env = environment.get_temperature(self.position)
        if temp_env < temp_pref:
            # 向 warmer 区域移动
            direction += np.pi / 8 * random.choice([-1, 1])
        
        # 食物寻找行为
        if self.energy < 70:
            # 寻找食物
            food_direction = self.find_food_direction(environment)
            if food_direction is not None:
                direction = food_direction
        
        # 捕食者回避
        predator_direction = self.check_for_predators(environment)
        if predator_direction is not None:
            # 远离捕食者
            direction = predator_direction + np.pi
        
        # 社会行为影响
        if self.social_group and random.random() < self.genome.get_value("social_need"):
            # 向群体中心移动
            center_x = sum(o.position[0] for o in self.social_group if o.alive) / len([o for o in self.social_group if o.alive])
            center_y = sum(o.position[1] for o in self.social_group if o.alive) / len([o for o in self.social_group if o.alive])
            
            group_direction = np.arctan2(center_y - self.position[1], center_x - self.position[0])
            direction = 0.7 * direction + 0.3 * group_direction  # 混合方向
        
        return direction
    
    def find_food_direction(self, environment):
        """寻找食物方向"""
        vision_range = self.genome.get_value("vision_range") * 15
        
        # 检查记忆中的食物位置
        best_food_pos = None
        best_food_value = 0
        
        for pos in self.memory:
            food_value = environment.get_food(pos)
            if food_value > best_food_value:
                distance = np.sqrt((self.position[0] - pos[0])**2 + 
                                  (self.position[1] - pos[1])**2)
                if distance < vision_range:
                    best_food_value = food_value
                    best_food_pos = pos
        
        # 检查视线范围内的食物
        for x in range(int(self.position[0] - vision_range), int(self.position[0] + vision_range)):
            for y in range(int(self.position[1] - vision_range), int(self.position[1] + vision_range)):
                if (0 <= x < environment.width and 0 <= y < environment.height and
                    (x != int(self.position[0]) or y != int(self.position[1]))):
                    
                    food_value = environment.food_map[x, y]
                    if food_value > best_food_value:
                        best_food_value = food_value
                        best_food_pos = (x, y)
        
        if best_food_pos:
            # 计算方向
            dx = best_food_pos[0] - self.position[0]
            dy = best_food_pos[1] - self.position[1]
            return np.arctan2(dy, dx)
        
        return None
    
    def check_for_predators(self, environment):
        """检查捕食者"""
        vision_range = self.genome.get_value("vision_range") * 15
        
        for organism in environment.organisms:
            if (organism is not self and organism.alive and 
                organism.diet == "carnivore" and organism.size > self.size * 1.2):
                
                distance = np.sqrt((self.position[0] - organism.position[0])**2 + 
                                  (self.position[1] - organism.position[1])**2)
                
                if distance < vision_range:
                    # 计算捕食者方向
                    dx = organism.position[0] - self.position[0]
                    dy = organism.position[1] - self.position[1]
                    return np.arctan2(dy, dx)
        
        return None
    
    def reproduce(self, environment):
        """繁殖"""
        if self.energy < 80:
            return None
        
        # 寻找配偶
        mate = self.find_mate(environment)
        if not mate:
            return None
        
        # 消耗能量用于繁殖
        self.energy -= 70
        mate.energy -= 70
        self.children += 1
        mate.children += 1
        self.last_reproduction = self.age
        mate.last_reproduction = mate.age
        
        # 创建子代基因组
        child_genome = self.genome.crossover(mate.genome)
        
        # 突变
        mutations = child_genome.mutate()
        
        # 创建子代生物
        child = Organism(child_genome, self.position, self, mate)
        
        # 添加到环境
        environment.add_organism(child)
        
        # 物种分类
        environment.classify_organism(child)
        
        return child
    
    def find_mate(self, environment):
        """寻找配偶"""
        mating_distance = self.genome.get_value("mating_distance") * 20
        
        potential_mates = []
        for organism in environment.organisms:
            if (organism is not self and organism.alive and 
                organism.species == self.species and
                organism.age > 20 and organism.energy > 80 and
                organism.age - organism.last_reproduction > 10):
                
                distance = np.sqrt((self.position[0] - organism.position[0])**2 + 
                                  (self.position[1] - organism.position[1])**2)
                
                if distance < mating_distance:
                    potential_mates.append(organism)
        
        if potential_mates:
            return random.choice(potential_mates)
        
        return None


class Environment:
    """环境类"""
    def __init__(self, width, height, simulator):
        self.width = width
        self.height = height
        self.simulator = simulator
        self.organisms = []
        self.species = []
        self.temperature_map = np.zeros((width, height))
        self.humidity_map = np.zeros((width, height))
        self.food_map = np.zeros((width, height))
        self.season = 0  # 0-3: 春夏秋冬
        self.season_progress = 0  # 季节进度 0-1
        self.generate_environment()
    
    def generate_environment(self):
        """生成环境"""
        # 生成温度梯度
        for x in range(self.width):
            for y in range(self.height):
                # 从左上到右下的温度梯度
                self.temperature_map[x, y] = (x + y) / (self.width + self.height)
                
                # 从中心向四周的湿度梯度
                center_x, center_y = self.width / 2, self.height / 2
                distance = np.sqrt((x - center_x)**2 + (y - center_y)**2)
                max_distance = np.sqrt(center_x**2 + center_y**2)
                self.humidity_map[x, y] = 1.0 - (distance / max_distance)
        
        # 随机生成食物
        self.generate_food(100)
    
    def generate_food(self, amount):
        """生成食物"""
        for _ in range(amount):
            x = random.randint(0, self.width - 1)
            y = random.randint(0, self.height - 1)
            self.food_map[x, y] = random.uniform(0.5, 1.0)
    
    def add_organism(self, organism):
        """添加生物体到环境"""
        organism.environment = self
        self.organisms.append(organism)
        
        # 如果没有物种，创建第一个物种
        if not self.species:
            new_species = Species(organism)
            new_species.add_member(organism)
            new_species.emergence_time = self.simulator.generation
            self.species.append(new_species)
        else:
            self.classify_organism(organism)
    
    def classify_organism(self, organism):
        """将生物分类到物种"""
        # 尝试找到相似物种
        for species in self.species:
            if species.is_similar(organism):
                species.add_member(organism)
                return
        
        # 没有找到相似物种，创建新物种
        new_species = Species(organism)
        new_species.add_member(organism)
        new_species.emergence_time = self.simulator.generation
        self.species.append(new_species)
    
    def update(self):
        """更新环境状态"""
        # 更新季节
        self.update_season()
        
        # 更新所有生物
        dead_organisms = []
        for organism in self.organisms[:]:
            if not organism.update(self):
                dead_organisms.append(organism)
        
        # 移除死亡生物体
        for organism in dead_organisms:
            if organism in self.organisms:  # 确保生物体还在列表中
                self.organisms.remove(organism)
        
        # 环境变化
        self.environment_change()
        
        # 物种统计
        self.update_species_stats()
    
    def update_season(self):
        """更新季节"""
        # 每100代一个完整四季循环
        self.season_progress = (self.simulator.generation % 100) / 100
        self.season = int(self.season_progress * 4) % 4
    
    def get_season_factor(self, season_adaptation):
        """获取季节适应性因子"""
        # 计算生物的季节适应性与当前季节的匹配程度
        season_match = 1.0 - abs(season_adaptation - self.season_progress)
        return 0.2 + 0.8 * season_match  # 返回0.2-1.0之间的值
    
    def environment_change(self):
        """环境缓慢变化"""
        # 温度缓慢变化
        change = np.random.normal(0, 0.001, (self.width, self.height))
        self.temperature_map = np.clip(self.temperature_map + change, 0, 1)
        
        # 湿度缓慢变化
        change = np.random.normal(0, 0.001, (self.width, self.height))
        self.humidity_map = np.clip(self.humidity_map + change, 0, 1)
        
        # 食物再生
        self.generate_food(10)
        
        # 随机环境事件
        if random.random() < 0.01:  # 1%的概率发生环境事件
            self.environmental_event()
    
    def environmental_event(self):
        """环境事件"""
        event_type = random.choice(["drought", "flood", "heatwave", "coldwave"])
        
        if event_type == "drought":
            # 干旱：降低湿度
            self.humidity_map = np.clip(self.humidity_map - 0.2, 0, 1)
        elif event_type == "flood":
            # 洪水：增加湿度
            self.humidity_map = np.clip(self.humidity_map + 0.2, 0, 1)
        elif event_type == "heatwave":
            # 热浪：增加温度
            self.temperature_map = np.clip(self.temperature_map + 0.2, 0, 1)
        elif event_type == "coldwave":
            # 寒流：降低温度
            self.temperature_map = np.clip(self.temperature_map - 0.2, 0, 1)
    
    def update_species_stats(self):
        """更新物种统计"""
        # 移除没有成员的物种
        self.species = [s for s in self.species if s.members]
    
    def get_temperature(self, position):
        """获取位置的温度"""
        x, y = int(position[0]), int(position[1])
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.temperature_map[x, y]
        return 0.5
    
    def get_humidity(self, position):
        """获取位置的湿度"""
        x, y = int(position[0]), int(position[1])
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.humidity_map[x, y]
        return 0.5
    
    def get_food(self, position):
        """获取位置的食物"""
        x, y = int(position[0]), int(position[1])
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.food_map[x, y]
        return 0.0
    
    def consume_food(self, position, amount):
        """消耗食物"""
        x, y = int(position[0]), int(position[1])
        if 0 <= x < self.width and 0 <= y < self.height:
            self.food_map[x, y] = max(0, self.food_map[x, y] - amount)


class EvolutionChart(FigureCanvas):
    """进化图表"""
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        super().__init__(self.fig)
        self.setParent(parent)
        
        self.data = {
            'population': [],
            'species_count': [],
            'avg_lifespan': [],
            'avg_speed': [],
            'avg_energy': [],
            'diversity': [],
            'extinctions': [],
            'speciations': []
        }
        
    def update_chart(self, environment, generation):
        """更新图表数据"""
        if not environment.organisms:
            return
        
        # 收集统计数据
        lifespans = [o.genome.get_value("lifespan") for o in environment.organisms]
        speeds = [o.genome.get_value("speed") for o in environment.organisms]
        energies = [o.energy for o in environment.organisms if o.alive]
        
        # 计算基因多样性（基于颜色基因）
        color_diversity = 0
        if len(environment.organisms) > 1:
            reds = [o.genome.get_value("color_red") for o in environment.organisms]
            greens = [o.genome.get_value("color_green") for o in environment.organisms]
            blues = [o.genome.get_value("color_blue") for o in environment.organisms]
            color_diversity = np.std(reds) + np.std(greens) + np.std(blues)
        
        # 计算灭绝和物种形成事件
        extinctions = sum(1 for s in environment.species if s.extinction_time == generation)
        speciations = len([s for s in environment.species if s.emergence_time == generation])
        
        # 添加到数据
        self.data['population'].append(len(environment.organisms))
        self.data['species_count'].append(len(environment.species))
        self.data['avg_lifespan'].append(np.mean(lifespans) if lifespans else 0)
        self.data['avg_speed'].append(np.mean(speeds) if speeds else 0)
        self.data['avg_energy'].append(np.mean(energies) if energies else 0)
        self.data['diversity'].append(color_diversity)
        self.data['extinctions'].append(extinctions)
        self.data['speciations'].append(speciations)
        
        # 更新图表
        self.fig.clear()
        
        # 使用GridSpec创建更复杂的布局
        gs = GridSpec(2, 2, figure=self.fig)
        
        # 种群和物种数量
        ax1 = self.fig.add_subplot(gs[0, 0])
        generations = list(range(max(0, generation - len(self.data['population']) + 1), generation + 1))
        
        ax1.plot(generations, self.data['population'], label='Population', color='blue')
        ax1.plot(generations, self.data['species_count'], label='Species Count', color='green')
        ax1.set_xlabel('Generation')
        ax1.set_ylabel('Count')
        ax1.legend()
        ax1.grid(True)
        
        # 平均特征
        ax2 = self.fig.add_subplot(gs[0, 1])
        ax2.plot(generations, self.data['avg_lifespan'], label='Avg Lifespan', color='red')
        ax2.plot(generations, self.data['avg_speed'], label='Avg Speed', color='purple')
        ax2.plot(generations, self.data['avg_energy'], label='Avg Energy', color='orange')
        ax2.set_xlabel('Generation')
        ax2.set_ylabel('Value')
        ax2.legend()
        ax2.grid(True)
        
        # 多样性和事件
        ax3 = self.fig.add_subplot(gs[1, 0])
        ax3.plot(generations, self.data['diversity'], label='Diversity', color='brown')
        ax3.set_xlabel('Generation')
        ax3.set_ylabel('Diversity', color='brown')
        ax3.tick_params(axis='y', labelcolor='brown')
        ax3.legend(loc='upper left')
        ax3.grid(True)
        
        ax4 = ax3.twinx()
        ax4.plot(generations, self.data['extinctions'], label='Extinctions', color='black', linestyle='--')
        ax4.plot(generations, self.data['speciations'], label='Speciations', color='green', linestyle='--')
        ax4.set_ylabel('Events', color='black')
        ax4.tick_params(axis='y', labelcolor='black')
        ax4.legend(loc='upper right')
        
        # 基因频率（示例）
        ax5 = self.fig.add_subplot(gs[1, 1])
        if len(environment.organisms) > 0:
            diet_values = [o.genome.get_value("diet") for o in environment.organisms]
            hist, bins = np.histogram(diet_values, bins=10, range=(0, 1))
            ax5.bar(bins[:-1], hist, width=0.1, alpha=0.7, color='teal')
            ax5.set_xlabel('Diet Preference')
            ax5.set_ylabel('Frequency')
            ax5.set_title('Gene Frequency Distribution')
        
        self.fig.tight_layout()
        self.draw()


class EnvironmentView(QGraphicsView):
    """环境视图"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene()
        self.setScene(self.scene)
        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        
    def update_view(self, environment):
        """更新视图"""
        self.scene.clear()
        
        # 绘制环境背景（温度）
        cell_width = self.width() / environment.width
        cell_height = self.height() / environment.height
        
        for x in range(environment.width):
            for y in range(environment.height):
                temp = environment.temperature_map[x, y]
                color = QColor(int(255 * temp), 100, int(255 * (1 - temp)))
                brush = QBrush(color)
                pen = QPen(Qt.NoPen)
                
                rect = QRectF(x * cell_width, y * cell_height, cell_width, cell_height)
                self.scene.addRect(rect, pen, brush)
        
        # 绘制食物
        for x in range(environment.width):
            for y in range(environment.height):
                if environment.food_map[x, y] > 0:
                    food_size = environment.food_map[x, y] * 3
                    color = QColor(0, 200, 0, 100)  # 半透明绿色
                    brush = QBrush(color)
                    pen = QPen(Qt.NoPen)
                    
                    ellipse = QGraphicsEllipseItem(
                        x * cell_width - food_size/2, 
                        y * cell_height - food_size/2, 
                        food_size, food_size
                    )
                    ellipse.setBrush(brush)
                    ellipse.setPen(pen)
                    self.scene.addItem(ellipse)
        
        # 绘制生物
        for organism in environment.organisms:
            if organism.alive:
                x, y = organism.position
                size = organism.size
                
                # 使用物种颜色
                color = organism.species.color if organism.species else organism.color
                
                ellipse = QGraphicsEllipseItem(
                    x * cell_width - size/2, 
                    y * cell_height - size/2, 
                    size, size
                )
                
                brush = QBrush(color)
                pen = QPen(Qt.black, 1)
                
                ellipse.setBrush(brush)
                ellipse.setPen(pen)
                self.scene.addItem(ellipse)
                
                # 显示食肉动物特殊标记
                if organism.diet == "carnivore":
                    # 添加红色边框
                    predator_mark = QGraphicsEllipseItem(
                        x * cell_width - size/2 - 2, 
                        y * cell_height - size/2 - 2, 
                        size + 4, size + 4
                    )
                    predator_mark.setPen(QPen(Qt.red, 2))
                    predator_mark.setBrush(QBrush(Qt.NoBrush))
                    self.scene.addItem(predator_mark)
        
        self.setSceneRect(0, 0, environment.width * cell_width, environment.height * cell_height)


class SpeciesView(QGraphicsView):
    """物种进化树视图"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene()
        self.setScene(self.scene)
        self.setRenderHint(QPainter.Antialiasing)
        
    def update_view(self, environment, generation):
        """更新物种进化树"""
        self.scene.clear()
        
        if not environment.species:
            return
        
        # 计算布局参数
        margin = 50
        width = self.width() - 2 * margin
        height = self.height() - 2 * margin
        
        # 按出现时间排序物种
        sorted_species = sorted(environment.species, key=lambda s: s.emergence_time)
        
        # 计算每个物种的位置
        species_positions = {}
        max_time = max(s.emergence_time for s in sorted_species) if sorted_species else 1
        extinct_species = [s for s in sorted_species if s.extinction_time is not None]
        extant_species = [s for s in sorted_species if s.extinction_time is None]
        
        # 绘制进化树
        for i, species in enumerate(sorted_species):
            # X轴表示时间
            x = margin + (species.emergence_time / max(1, max_time)) * width
            
            # Y轴表示物种ID（简单布局）
            y = margin + (i / max(1, len(sorted_species))) * height
            
            species_positions[species.id] = (x, y)
            
            # 绘制物种节点
            color = species.color
            size = 10 + 5 * (len(species.members) / max(1, len(environment.organisms)))
            
            ellipse = QGraphicsEllipseItem(x - size/2, y - size/2, size, size)
            ellipse.setBrush(QBrush(color))
            ellipse.setPen(QPen(Qt.black, 1))
            self.scene.addItem(ellipse)
            
            # 绘制物种ID
            if size > 8:
                text = QGraphicsTextItem(str(species.id))
                text.setPos(x - text.boundingRect().width()/2, y - text.boundingRect().height()/2)
                self.scene.addItem(text)
            
            # 绘制灭绝时间线
            if species.extinction_time is not None:
                end_x = margin + (species.extinction_time / max(1, max_time)) * width
                line = self.scene.addLine(x, y, end_x, y, QPen(Qt.red, 2))
                
                # 添加灭绝标记
                extinction_marker = QGraphicsEllipseItem(
                    end_x - 4, y - 4, 8, 8
                )
                extinction_marker.setBrush(QBrush(Qt.red))
                extinction_marker.setPen(QPen(Qt.NoPen))
                self.scene.addItem(extinction_marker)
        
        # 绘制物种间的进化关系（简化版）
        # 注意：这是一个简化版本，真实的进化树需要更复杂的算法
        
        self.setSceneRect(0, 0, self.width(), self.height())


class EvolutionSimulator(QMainWindow):
    """进化模拟器主窗口"""
    def __init__(self):
        super().__init__()
        self.environment = Environment(50, 50, self)
        self.generation = 0
        self.timer = QTimer()
        self.is_running = False
        self.speed = 1
        self.history = deque(maxlen=1000)  # 历史记录
        
        self.init_ui()
        self.init_organisms()
        
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("物种起源进化强仿真系统 - 增强版")
        self.setGeometry(100, 100, 1600, 1000)
        
        # 中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QHBoxLayout(central_widget)
        
        # 左侧控制面板
        control_panel = QWidget()
        control_layout = QVBoxLayout(control_panel)
        control_panel.setMaximumWidth(350)
        
        # 环境控制
        env_group = QGroupBox("环境控制")
        env_layout = QVBoxLayout(env_group)
        
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setMinimum(1)
        self.speed_slider.setMaximum(20)
        self.speed_slider.setValue(1)
        self.speed_slider.valueChanged.connect(self.set_speed)
        
        env_layout.addWidget(QLabel("模拟速度:"))
        env_layout.addWidget(self.speed_slider)
        
        speed_control = QHBoxLayout()
        self.start_btn = QPushButton("开始")
        self.start_btn.clicked.connect(self.toggle_simulation)
        speed_control.addWidget(self.start_btn)
        
        self.step_btn = QPushButton("单步")
        self.step_btn.clicked.connect(self.step_simulation)
        speed_control.addWidget(self.step_btn)
        
        self.reset_btn = QPushButton("重置")
        self.reset_btn.clicked.connect(self.reset_simulation)
        speed_control.addWidget(self.reset_btn)
        
        env_layout.addLayout(speed_control)
        
        # 环境参数
        env_params = QHBoxLayout()
        env_params.addWidget(QLabel("季节:"))
        self.season_label = QLabel("春")
        env_params.addWidget(self.season_label)
        env_params.addStretch()
        
        env_layout.addLayout(env_params)
        
        control_layout.addWidget(env_group)
        
        # 参数控制
        param_group = QGroupBox("初始参数")
        param_layout = QVBoxLayout(param_group)
        
        param_layout.addWidget(QLabel("初始种群大小:"))
        self.population_spin = QSpinBox()
        self.population_spin.setRange(10, 500)
        self.population_spin.setValue(50)
        param_layout.addWidget(self.population_spin)
        
        param_layout.addWidget(QLabel("突变率:"))
        self.mutation_spin = QDoubleSpinBox()
        self.mutation_spin.setRange(0.001, 0.1)
        self.mutation_spin.setSingleStep(0.001)
        self.mutation_spin.setValue(0.01)
        param_layout.addWidget(self.mutation_spin)
        
        param_layout.addWidget(QLabel("食物生成率:"))
        self.food_rate_spin = QDoubleSpinBox()
        self.food_rate_spin.setRange(0.1, 10.0)
        self.food_rate_spin.setSingleStep(0.1)
        self.food_rate_spin.setValue(1.0)
        param_layout.addWidget(self.food_rate_spin)
        
        control_layout.addWidget(param_group)
        
        # 统计信息
        stats_group = QGroupBox("实时统计")
        stats_layout = QVBoxLayout(stats_group)
        
        self.stats_label = QLabel("统计信息将在这里显示")
        self.stats_label.setWordWrap(True)
        stats_layout.addWidget(self.stats_label)
        
        control_layout.addWidget(stats_group)
        
        # 物种信息
        species_group = QGroupBox("物种信息")
        species_layout = QVBoxLayout(species_group)
        
        self.species_table = QTableWidget()
        self.species_table.setColumnCount(4)
        self.species_table.setHorizontalHeaderLabels(["ID", "个体数", "出现时间", "状态"])
        self.species_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        species_layout.addWidget(self.species_table)
        
        control_layout.addWidget(species_group)
        
        # 保存/加载
        io_group = QGroupBox("保存/加载")
        io_layout = QHBoxLayout(io_group)
        
        self.save_btn = QPushButton("保存模拟")
        self.save_btn.clicked.connect(self.save_simulation)
        io_layout.addWidget(self.save_btn)
        
        self.load_btn = QPushButton("加载模拟")
        self.load_btn.clicked.connect(self.load_simulation)
        io_layout.addWidget(self.load_btn)
        
        self.export_btn = QPushButton("导出数据")
        self.export_btn.clicked.connect(self.export_data)
        io_layout.addWidget(self.export_btn)
        
        control_layout.addWidget(io_group)
        
        control_layout.addStretch()
        
        # 右侧视图
        right_panel = QSplitter(Qt.Vertical)
        
        # 顶部选项卡
        top_tabs = QTabWidget()
        
        # 环境视图
        self.env_view = EnvironmentView()
        top_tabs.addTab(self.env_view, "环境视图")
        
        # 物种进化树
        self.species_view = SpeciesView()
        top_tabs.addTab(self.species_view, "物种进化树")
        
        right_panel.addWidget(top_tabs)
        
        # 进化图表
        self.evolution_chart = EvolutionChart()
        right_panel.addWidget(self.evolution_chart)
        
        right_panel.setSizes([600, 400])
        
        # 添加到主布局
        main_layout.addWidget(control_panel)
        main_layout.addWidget(right_panel)
        
        # 设置定时器
        self.timer.timeout.connect(self.update_simulation)
        
        # 状态栏
        self.statusBar().showMessage("就绪")
        
    def init_organisms(self):
        """初始化生物种群"""
        num_organisms = self.population_spin.value()
        
        for _ in range(num_organisms):
            genome = Genome()
            
            # 添加各种基因
            genome.add_gene(Gene("size", (0.1, 2.0), self.mutation_spin.value()))
            genome.add_gene(Gene("speed", (0.1, 3.0), self.mutation_spin.value()))
            genome.add_gene(Gene("lifespan", (0.5, 2.0), self.mutation_spin.value()))
            genome.add_gene(Gene("temperature_preference", (0.0, 1.0), self.mutation_spin.value()))
            genome.add_gene(Gene("humidity_preference", (0.0, 1.0), self.mutation_spin.value()))
            genome.add_gene(Gene("color_red", (0.0, 1.0), self.mutation_spin.value()))
            genome.add_gene(Gene("color_green", (0.0, 1.0), self.mutation_spin.value()))
            genome.add_gene(Gene("color_blue", (0.0, 1.0), self.mutation_spin.value()))
            genome.add_gene(Gene("reproduction_rate", (0.01, 0.2), self.mutation_spin.value()))
            genome.add_gene(Gene("diet", (0.0, 1.0), self.mutation_spin.value()))
            genome.add_gene(Gene("attack_strength", (0.0, 1.0), self.mutation_spin.value()))
            genome.add_gene(Gene("defense_strength", (0.0, 1.0), self.mutation_spin.value()))
            genome.add_gene(Gene("vision_range", (0.1, 1.5), self.mutation_spin.value()))
            genome.add_gene(Gene("feeding_efficiency", (0.1, 1.0), self.mutation_spin.value()))
            genome.add_gene(Gene("mating_distance", (0.5, 5.0), self.mutation_spin.value()))
            genome.add_gene(Gene("social_need", (0.0, 1.0), self.mutation_spin.value()))
            genome.add_gene(Gene("season_adaptation", (0.0, 1.0), self.mutation_spin.value()))
            
            # 添加一些基因相互作用
            genome.add_gene_interaction("size", "speed", -0.5)  # 体型越大，速度越慢
            genome.add_gene_interaction("size", "attack_strength", 0.7)  # 体型越大，攻击力越强
            genome.add_gene_interaction("speed", "feeding_efficiency", 0.3)  # 速度越快，捕食效率越高
            
            position = (
                random.randint(0, self.environment.width - 1),
                random.randint(0, self.environment.height - 1)
            )
            
            organism = Organism(genome, position)
            self.environment.add_organism(organism)
    
    def toggle_simulation(self):
        """切换模拟状态"""
        if self.is_running:
            self.timer.stop()
            self.start_btn.setText("开始")
            self.statusBar().showMessage("模拟已暂停")
        else:
            self.timer.start(1000 // self.speed)
            self.start_btn.setText("暂停")
            self.statusBar().showMessage("模拟运行中")
        
        self.is_running = not self.is_running
    
    def step_simulation(self):
        """单步模拟"""
        if not self.is_running:
            self.update_simulation()
    
    def set_speed(self, speed):
        """设置模拟速度"""
        self.speed = speed
        if self.is_running:
            self.timer.setInterval(1000 // speed)
    
    def update_simulation(self):
        """更新模拟"""
        # 更新食物生成率
        self.environment.generate_food(int(self.food_rate_spin.value()))
        
        for _ in range(self.speed):
            self.environment.update()
            self.generation += 1
        
        # 更新季节显示
        season_names = ["春", "夏", "秋", "冬"]
        self.season_label.setText(season_names[self.environment.season])
        
        # 更新视图
        self.env_view.update_view(self.environment)
        self.species_view.update_view(self.environment, self.generation)
        self.evolution_chart.update_chart(self.environment, self.generation)
        self.update_stats()
        self.update_species_table()
        
        # 记录历史
        self.record_history()
    
    def update_stats(self):
        """更新统计信息"""
        if not self.environment.organisms:
            self.stats_label.setText("种群已灭绝")
            return
        
        stats_text = f"世代: {self.generation}\n"
        stats_text += f"种群数量: {len(self.environment.organisms)}\n"
        stats_text += f"物种数量: {len(self.environment.species)}\n"
        
        # 计算平均统计数据
        lifespans = [o.genome.get_value("lifespan") for o in self.environment.organisms]
        speeds = [o.genome.get_value("speed") for o in self.environment.organisms]
        sizes = [o.genome.get_value("size") for o in self.environment.organisms]
        energies = [o.energy for o in self.environment.organisms if o.alive]
        
        # 计算食性分布
        diets = [o.diet for o in self.environment.organisms]
        herbivores = diets.count("herbivore")
        carnivores = diets.count("carnivore")
        omnivores = diets.count("omnivore")
        
        stats_text += f"平均寿命: {np.mean(lifespans):.2f}\n"
        stats_text += f"平均速度: {np.mean(speeds):.2f}\n"
        stats_text += f"平均大小: {np.mean(sizes):.2f}\n"
        stats_text += f"平均能量: {np.mean(energies):.2f}\n"
        stats_text += f"食草动物: {herbivores} ({herbivores/len(diets)*100:.1f}%)\n"
        stats_text += f"食肉动物: {carnivores} ({carnivores/len(diets)*100:.1f}%)\n"
        stats_text += f"杂食动物: {omnivores} ({omnivores/len(diets)*100:.1f}%)\n"
        
        # 计算基因多样性
        if len(self.environment.organisms) > 1:
            reds = [o.genome.get_value("color_red") for o in self.environment.organisms]
            greens = [o.genome.get_value("color_green") for o in self.environment.organisms]
            blues = [o.genome.get_value("color_blue") for o in self.environment.organisms]
            diversity = np.std(reds) + np.std(greens) + np.std(blues)
            stats_text += f"基因多样性: {diversity:.4f}\n"
        
        self.stats_label.setText(stats_text)
    
    def update_species_table(self):
        """更新物种表格"""
        self.species_table.setRowCount(len(self.environment.species))
        
        for i, species in enumerate(self.environment.species):
            self.species_table.setItem(i, 0, QTableWidgetItem(str(species.id)))
            self.species_table.setItem(i, 1, QTableWidgetItem(str(len(species.members))))
            self.species_table.setItem(i, 2, QTableWidgetItem(str(species.emergence_time)))
            
            status = "存活" if species.extinction_time is None else f"灭绝于 {species.extinction_time}"
            self.species_table.setItem(i, 3, QTableWidgetItem(status))
    
    def record_history(self):
        """记录历史数据"""
        history_entry = {
            'generation': self.generation,
            'population': len(self.environment.organisms),
            'species_count': len(self.environment.species),
            'avg_lifespan': np.mean([o.genome.get_value("lifespan") for o in self.environment.organisms]) if self.environment.organisms else 0,
            'avg_speed': np.mean([o.genome.get_value("speed") for o in self.environment.organisms]) if self.environment.organisms else 0,
            'avg_size': np.mean([o.genome.get_value("size") for o in self.environment.organisms]) if self.environment.organisms else 0,
            'herbivore_ratio': len([o for o in self.environment.organisms if o.diet == "herbivore"]) / len(self.environment.organisms) if self.environment.organisms else 0,
            'carnivore_ratio': len([o for o in self.environment.organisms if o.diet == "carnivore"]) / len(self.environment.organisms) if self.environment.organisms else 0,
        }
        
        self.history.append(history_entry)
    
    def reset_simulation(self):
        """重置模拟"""
        self.timer.stop()
        self.is_running = False
        self.start_btn.setText("开始")
        self.generation = 0
        self.history.clear()
        
        # 创建新环境
        self.environment = Environment(50, 50, self)
        self.init_organisms()
        
        # 重置图表
        self.evolution_chart.data = {
            'population': [],
            'species_count': [],
            'avg_lifespan': [],
            'avg_speed': [],
            'avg_energy': [],
            'diversity': [],
            'extinctions': [],
            'speciations': []
        }
        
        # 更新视图
        self.env_view.update_view(self.environment)
        self.species_view.update_view(self.environment, self.generation)
        self.evolution_chart.update_chart(self.environment, self.generation)
        self.update_stats()
        self.update_species_table()
        
        self.statusBar().showMessage("模拟已重置")
    
    def save_simulation(self):
        """保存模拟状态"""
        try:
            filename, _ = QFileDialog.getSaveFileName(
                self, "保存模拟", "", "Evolution Files (*.evol)"
            )
            
            if filename:
                if not filename.endswith('.evol'):
                    filename += '.evol'
                
                data = {
                    'environment': self.environment,
                    'generation': self.generation,
                    'chart_data': self.evolution_chart.data,
                    'history': list(self.history)
                }
                
                with open(filename, 'wb') as f:
                    pickle.dump(data, f)
                
                QMessageBox.information(self, "成功", "模拟已保存")
                self.statusBar().showMessage("模拟已保存")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存失败: {str(e)}")
            self.statusBar().showMessage(f"保存失败: {str(e)}")
    
    def load_simulation(self):
        """加载模拟状态"""
        try:
            filename, _ = QFileDialog.getOpenFileName(
                self, "加载模拟", "", "Evolution Files (*.evol)"
            )
            
            if filename:
                with open(filename, 'rb') as f:
                    data = pickle.load(f)
                
                self.environment = data['environment']
                self.environment.simulator = self  # 恢复simulator引用
                self.generation = data['generation']
                self.evolution_chart.data = data['chart_data']
                self.history = deque(data['history'], maxlen=1000)
                
                # 更新视图
                self.env_view.update_view(self.environment)
                self.species_view.update_view(self.environment, self.generation)
                self.evolution_chart.update_chart(self.environment, self.generation)
                self.update_stats()
                self.update_species_table()
                
                QMessageBox.information(self, "成功", "模拟已加载")
                self.statusBar().showMessage("模拟已加载")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载失败: {str(e)}")
            self.statusBar().showMessage(f"加载失败: {str(e)}")
    
    def export_data(self):
        """导出数据到CSV"""
        try:
            filename, _ = QFileDialog.getSaveFileName(
                self, "导出数据", "", "CSV Files (*.csv)"
            )
            
            if filename:
                if not filename.endswith('.csv'):
                    filename += '.csv'
                
                # 创建DataFrame
                df = pd.DataFrame(self.history)
                df.to_csv(filename, index=False)
                
                QMessageBox.information(self, "成功", "数据已导出")
                self.statusBar().showMessage("数据已导出")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"导出失败: {str(e)}")
            self.statusBar().showMessage(f"导出失败: {str(e)}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    simulator = EvolutionSimulator()
    simulator.show()
    sys.exit(app.exec_())