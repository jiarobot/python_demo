import sys
import random
import math
import json
import os
import time
from datetime import datetime
from collections import deque
import matplotlib.pyplot as plt
import matplotlib
matplotlib.rc("font", family='Microsoft YaHei')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from PyQt5.QtWidgets import (
    QApplication, QFormLayout, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QPushButton, QLabel, QScrollArea, QGroupBox, QLineEdit, QComboBox,
    QListWidget, QListWidgetItem, QSlider, QTabWidget, QFileDialog, QMessageBox,
    QSizePolicy, QFrame, QProgressBar, QDoubleSpinBox
)
from PyQt5.QtCore import QPoint, Qt, QTimer, QSize
from PyQt5.QtGui import QPainter, QColor, QPen, QFont, QPixmap, QIcon

class Gene:
    def __init__(self, name, min_val, max_val, value=None, is_int=False, dominant=True):
        self.name = name
        self.min = min_val
        self.max = max_val
        self.is_int = is_int
        self.dominant = dominant  # 显性基因
        
        if value is None:
            self.value = random.uniform(min_val, max_val)
            if is_int:
                self.value = int(self.value)
        else:
            self.value = value
    
    def mutate(self, mutation_rate=0.1):
        """以一定概率突变基因"""
        if random.random() < mutation_rate:
            # 突变范围在10%-30%之间
            mutation_range = (self.max - self.min) * random.uniform(0.1, 0.3)
            new_value = self.value + random.uniform(-mutation_range, mutation_range)
            
            # 确保值在范围内
            new_value = max(self.min, min(self.max, new_value))
            
            if self.is_int:
                new_value = int(new_value)
            
            # 创建突变后的基因副本
            mutated = Gene(self.name, self.min, self.max, new_value, self.is_int, self.dominant)
            mutated.mutated = True
            return mutated
        return self
    
    def crossover(self, other_gene):
        """与另一个基因交叉（遗传）"""
        # 显性基因优先
        if self.dominant and not other_gene.dominant:
            return self.copy()
        elif not self.dominant and other_gene.dominant:
            return other_gene.copy()
        
        # 如果都是显性或都是隐性，则混合
        ratio = random.uniform(0.3, 0.7)
        new_value = self.value * ratio + other_gene.value * (1 - ratio)
        
        if self.is_int:
            new_value = int(new_value)
        
        return Gene(self.name, self.min, self.max, new_value, self.is_int, self.dominant)
    
    def copy(self):
        """创建基因的副本"""
        return Gene(self.name, self.min, self.max, self.value, self.is_int, self.dominant)
    
    def __repr__(self):
        return f"{self.name}: {self.value:.2f}" if not self.is_int else f"{self.name}: {self.value}"

class Genome:
    def __init__(self, genes=None):
        if genes is None:
            self.genes = self.create_default_genome()
        else:
            self.genes = genes
    
    def create_default_genome(self):
        """创建默认基因组"""
        return [
            Gene("size", 0.5, 2.0),  # 体型
            Gene("symmetry", 0.0, 1.0),  # 对称性
            Gene("complexity", 0.2, 1.0),  # 复杂度
            Gene("spikiness", 0.0, 1.0),  # 尖刺度
            Gene("leg_count", 0, 8, is_int=True),  # 腿数量
            Gene("mobility", 0.2, 1.0),  # 移动能力
            Gene("color_r", 50, 200, is_int=True),  # 颜色R
            Gene("color_g", 50, 200, is_int=True),  # 颜色G
            Gene("color_b", 50, 200, is_int=True),  # 颜色B
            Gene("pattern", 0, 3, is_int=True),  # 图案类型
            Gene("eye_count", 1, 6, is_int=True),  # 眼睛数量
            Gene("aggression", 0.0, 1.0),  # 攻击性
            Gene("fertility", 0.1, 1.0),  # 繁殖力
            Gene("metabolism", 0.2, 1.5),  # 新陈代谢
            Gene("lifespan", 0.5, 2.0),  # 寿命倍数
            Gene("intelligence", 0.0, 1.0),  # 智力
            Gene("camouflage", 0.0, 1.0),  # 伪装能力
            Gene("toxicity", 0.0, 1.0),  # 毒性
        ]
    
    def mutate(self, mutation_rate=0.15):
        """使基因组发生突变"""
        mutated_genes = []
        for gene in self.genes:
            mutated_genes.append(gene.mutate(mutation_rate))
        return Genome(mutated_genes)
    
    def crossover(self, other_genome):
        """与另一个基因组交叉（有性繁殖）"""
        new_genes = []
        for i in range(len(self.genes)):
            new_gene = self.genes[i].crossover(other_genome.genes[i])
            new_genes.append(new_gene)
        return Genome(new_genes)
    
    def get_value(self, name):
        """获取特定基因的值"""
        for gene in self.genes:
            if gene.name == name:
                return gene.value
        return None
    
    def copy(self):
        """创建基因组的副本"""
        return Genome([gene.copy() for gene in self.genes])
    
    def to_dict(self):
        """将基因组转换为字典"""
        return {gene.name: gene.value for gene in self.genes}
    
    def from_dict(self, data):
        """从字典创建基因组"""
        genes = []
        for gene in self.create_default_genome():
            if gene.name in data:
                value = data[gene.name]
                genes.append(Gene(gene.name, gene.min, gene.max, value, gene.is_int, gene.dominant))
            else:
                genes.append(gene.copy())
        return Genome(genes)
    
    def __repr__(self):
        return "\n".join(str(gene) for gene in self.genes)

class Species:
    def __init__(self, genome=None, name="未命名物种", generation=1, parents=None):
        if genome is None:
            self.genome = Genome()
        else:
            self.genome = genome
            
        self.name = name
        self.generation = generation
        self.parents = parents if parents else []
        self.birth_date = datetime.now()
        self.id = f"{name}_{int(time.time())}"
        self.generate_shape()
    
    def copy(self):
        """创建物种的副本"""
        copied_genome = self.genome.copy()
        return Species(
            copied_genome,
            f"{self.name}副本",
            self.generation,
            self.parents.copy() if self.parents else None
        )
    
    def generate_shape(self):
        """根据基因组生成物种形状"""
        # 获取基因值
        size = self.genome.get_value("size")
        symmetry = self.genome.get_value("symmetry")
        complexity = self.genome.get_value("complexity")
        spikiness = self.genome.get_value("spikiness")
        leg_count = self.genome.get_value("leg_count")
        mobility = self.genome.get_value("mobility")
        color_r = self.genome.get_value("color_r")
        color_g = self.genome.get_value("color_g")
        color_b = self.genome.get_value("color_b")
        pattern = self.genome.get_value("pattern")
        eye_count = self.genome.get_value("eye_count")
        
        self.color = (color_r, color_g, color_b)
        self.pattern = pattern
        
        # 生成身体形状
        self.points = []
        num_points = 20 + int(40 * complexity)
        base_radius = 40 + 60 * size
        
        for i in range(num_points):
            angle = (i / num_points) * 2 * math.pi
            
            # 应用对称性
            symmetry_effect = math.sin(angle * (symmetry * 4 + 1))
            
            # 应用尖刺效果
            spike_effect = 1 + spikiness * math.sin(angle * 10)
            
            radius = base_radius * (0.8 + 0.2 * symmetry_effect) * spike_effect
            
            # 添加一些随机性使形状更自然
            radius *= random.uniform(0.95, 1.05)
            
            x = radius * math.cos(angle)
            y = radius * math.sin(angle)
            self.points.append((x, y))
            
        # 生成腿
        self.legs = []
        for i in range(leg_count):
            angle = (i / leg_count) * 2 * math.pi + random.uniform(-0.1, 0.1)
            leg_length = 20 + 40 * mobility
            leg_x = base_radius * 0.8 * math.cos(angle)
            leg_y = base_radius * 0.8 * math.sin(angle)
            end_x = leg_x + leg_length * math.cos(angle + random.uniform(-0.3, 0.3))
            end_y = leg_y + leg_length * math.sin(angle + random.uniform(-0.3, 0.3))
            
            self.legs.append(((leg_x, leg_y), (end_x, end_y)))
            
        # 生成眼睛
        self.eyes = []
        for i in range(eye_count):
            angle = random.uniform(0, 2 * math.pi)
            distance = base_radius * (0.4 + 0.2 * random.random())
            size = 5 + 10 * complexity
            self.eyes.append((
                distance * math.cos(angle),
                distance * math.sin(angle),
                size
            ))
    
    def get_fitness(self):
        """计算物种的适应度"""
        # 基于多个基因计算适应度
        size = self.genome.get_value("size")
        symmetry = self.genome.get_value("symmetry")
        complexity = self.genome.get_value("complexity")
        mobility = self.genome.get_value("mobility")
        aggression = self.genome.get_value("aggression")
        fertility = self.genome.get_value("fertility")
        lifespan = self.genome.get_value("lifespan")
        intelligence = self.genome.get_value("intelligence")
        camouflage = self.genome.get_value("camouflage")
        toxicity = self.genome.get_value("toxicity")
        
        # 计算适应度（这里只是一个示例公式）
        fitness = (
            mobility * 0.3 +
            fertility * 0.2 +
            lifespan * 0.2 +
            intelligence * 0.15 +
            camouflage * 0.1 +
            toxicity * 0.05
        )
        
        # 调整适应度范围
        return max(0.1, min(1.0, fitness))
    
    def mutate(self, mutation_rate=0.15):
        """创建突变后的新物种"""
        mutated_genome = self.genome.mutate(mutation_rate)
        new_species = Species(mutated_genome, f"{self.name}突变体", self.generation + 1, [self])
        return new_species
    
    def breed_with(self, other):
        """与另一个物种繁殖"""
        child_genome = self.genome.crossover(other.genome)
        child_name = f"{self.name[:3]}-{other.name[:3]}后代"
        new_species = Species(child_genome, child_name, max(self.generation, other.generation) + 1, [self, other])
        return new_species
    
    def save_to_file(self, filename=None):
        """保存物种到文件"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"species_{self.name}_{timestamp}.json"
        
        data = {
            "name": self.name,
            "generation": self.generation,
            "parents": [p.name for p in self.parents],
            "genome": self.genome.to_dict(),
            "created_at": self.birth_date.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        
        return filename
    
    @classmethod
    def load_from_file(cls, filename):
        """从文件加载物种"""
        with open(filename, 'r') as f:
            data = json.load(f)
        
        genome = Genome().from_dict(data["genome"])
        species = cls(genome, data["name"], data.get("generation", 1))
        species.birth_date = datetime.strptime(data["created_at"], "%Y-%m-%d %H:%M:%S")
        return species

class GenePool:
    def __init__(self):
        self.species = []
        self.selected_species = [None, None]  # 用于繁殖的两个选择
        self.population_history = deque(maxlen=100)
        self.fitness_history = deque(maxlen=100)
    
    def add_species(self, species):
        self.species.append(species)
        self.record_population()
    
    def remove_species(self, species):
        if species in self.species:
            self.species.remove(species)
        
        # 如果被移除的是选中的物种，清除选择
        if species == self.selected_species[0]:
            self.selected_species[0] = None
        if species == self.selected_species[1]:
            self.selected_species[1] = None
        
        self.record_population()
    
    def select_for_breeding(self, species, index):
        if 0 <= index < 2:
            self.selected_species[index] = species
    
    def breed_selected(self):
        if self.selected_species[0] and self.selected_species[1]:
            return self.selected_species[0].breed_with(self.selected_species[1])
        return None
    
    def record_population(self):
        """记录种群数量和平均适应度"""
        self.population_history.append(len(self.species))
        
        if self.species:
            avg_fitness = sum(s.get_fitness() for s in self.species) / len(self.species)
            self.fitness_history.append(avg_fitness)
        else:
            self.fitness_history.append(0)
    
    def save_pool(self, filename="gene_pool.json"):
        """保存整个基因库到文件"""
        data = {
            "species": [{ 
                "name": s.name,
                "generation": s.generation,
                "parents": [p.name for p in s.parents],
                "genome": s.genome.to_dict(),
                "created_at": s.birth_date.strftime("%Y-%m-%d %H:%M:%S")
            } for s in self.species]
        }
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
    
    def load_pool(self, filename="gene_pool.json"):
        """从文件加载基因库"""
        if not os.path.exists(filename):
            return
        
        with open(filename, 'r') as f:
            data = json.load(f)
        
        self.species = []
        for species_data in data["species"]:
            genome = Genome().from_dict(species_data["genome"])
            species = Species(genome, species_data["name"], species_data.get("generation", 1))
            species.birth_date = datetime.strptime(species_data["created_at"], "%Y-%m-%d %H:%M:%S")
            self.species.append(species)
        
        self.record_population()

class SpeciesWidget(QWidget):
    """用于绘制物种的组件"""
    def __init__(self, species, parent=None):
        super().__init__(parent)
        self.species = species
        self.setMinimumSize(300, 300)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.scale = 1.0
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 绘制背景
        painter.fillRect(self.rect(), QColor(30, 45, 70))
        
        # 绘制物种
        if self.species:
            self.draw_species(painter, self.width()//2, self.height()//2, self.scale)
    
    def draw_species(self, painter, center_x, center_y, size_scale=1.0):
        """绘制物种"""
        scaled_size = size_scale
        color = QColor(*self.species.color)
        
        # 绘制腿 - 修复坐标类型
        for start, end in self.species.legs:
            pen = QPen(color, max(1, int(4 * self.species.genome.get_value("size") * scaled_size)))
            painter.setPen(pen)
            
            # 将浮点坐标转换为整数
            start_x = int(center_x + start[0] * scaled_size)
            start_y = int(center_y + start[1] * scaled_size)
            end_x = int(center_x + end[0] * scaled_size)
            end_y = int(center_y + end[1] * scaled_size)
            
            painter.drawLine(start_x, start_y, end_x, end_y)
        
        # 绘制身体 - 修复坐标类型
        points = []
        for p in self.species.points:
            x = int(center_x + p[0] * scaled_size)
            y = int(center_y + p[1] * scaled_size)
            points.append(QPoint(x, y))
        
        painter.setBrush(color)
        painter.setPen(Qt.NoPen)
        painter.drawPolygon(points)
        
        # 绘制身体轮廓 - 修复坐标类型
        outline_color = QColor(
            max(0, self.species.color[0]-30), 
            max(0, self.species.color[1]-30),  # 修正：min->max
            max(0, self.species.color[2]-30)
        )
        painter.setPen(QPen(outline_color, 2))
        painter.setBrush(Qt.NoBrush)
        painter.drawPolygon(points)
        
        # 绘制图案 - 修复坐标类型
        if self.species.pattern == 1:  # 斑点
            spot_color = QColor(
                min(255, self.species.color[0]+50),
                min(255, self.species.color[1]+50),
                min(255, self.species.color[2]+50)
            )
            painter.setBrush(spot_color)
            painter.setPen(Qt.NoPen)
            
            for _ in range(int(10 * self.species.genome.get_value("complexity"))):
                angle = random.uniform(0, 2 * math.pi)
                distance = random.uniform(0, 40 * self.species.genome.get_value("size") * scaled_size)
                x = int(center_x + distance * math.cos(angle))
                y = int(center_y + distance * math.sin(angle))
                size = int(random.uniform(2, 8) * scaled_size)
                painter.drawEllipse(x - size//2, y - size//2, size, size)
                
        elif self.species.pattern == 2:  # 条纹
            stripe_color = QColor(
                min(255, self.species.color[0]+50),
                min(255, self.species.color[1]+50),
                min(255, self.species.color[2]+50)
            )
            painter.setPen(QPen(stripe_color, max(1, int(3 * scaled_size))))
            
            for i in range(6):
                angle = (i / 6) * 2 * math.pi
                start_x = int(center_x + 20 * self.species.genome.get_value("size") * scaled_size * math.cos(angle))
                start_y = int(center_y + 20 * self.species.genome.get_value("size") * scaled_size * math.sin(angle))
                end_x = int(center_x + (40 + 20 * self.species.genome.get_value("size")) * scaled_size * math.cos(angle))
                end_y = int(center_y + (40 + 20 * self.species.genome.get_value("size")) * scaled_size * math.sin(angle))
                painter.drawLine(start_x, start_y, end_x, end_y)
        
        # 绘制眼睛 - 修复坐标类型
        painter.setBrush(QColor(255, 255, 255))
        painter.setPen(Qt.NoPen)
        for x, y, size in self.species.eyes:
            eye_size = int(size * scaled_size)
            eye_x = int(center_x + x * scaled_size)
            eye_y = int(center_y + y * scaled_size)
            painter.drawEllipse(eye_x - eye_size//2, eye_y - eye_size//2, eye_size, eye_size)
            
            # 绘制瞳孔
            pupil_size = eye_size // 2
            painter.setBrush(QColor(0, 0, 0))
            painter.drawEllipse(eye_x - pupil_size//2, eye_y - pupil_size//2, pupil_size, pupil_size)

class GeneEditor(QWidget):
    """基因编辑面板"""
    def __init__(self, species, parent=None):
        super().__init__(parent)
        self.species = species
        self.layout = QVBoxLayout(self)
        self.gene_widgets = {}
        
        self.init_ui()
    
    def init_ui(self):
        # 标题
        title = QLabel("基因编辑")
        title.setFont(QFont("Arial", 14, QFont.Bold))
        self.layout.addWidget(title)
        
        # 创建基因滑块
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        
        for gene in self.species.genome.genes:
            group = QGroupBox(gene.name)
            group_layout = QVBoxLayout(group)
            
            # 值标签
            value_label = QLabel()
            value_label.setAlignment(Qt.AlignCenter)
            group_layout.addWidget(value_label)
            
            # 滑块
            slider = QSlider(Qt.Horizontal)
            slider.setRange(0, 1000)  # 使用高精度滑块
            slider.setValue(int((gene.value - gene.min) / (gene.max - gene.min) * 1000))
            group_layout.addWidget(slider)
            
            # 最小值、最大值标签
            min_max_layout = QHBoxLayout()
            min_label = QLabel(f"{gene.min}")
            max_label = QLabel(f"{gene.max}")
            min_max_layout.addWidget(min_label)
            min_max_layout.addStretch()
            min_max_layout.addWidget(max_label)
            group_layout.addLayout(min_max_layout)
            
            # 保存引用
            self.gene_widgets[gene.name] = {
                "slider": slider,
                "value_label": value_label,
                "gene": gene
            }
            
            # 更新标签
            self.update_gene_label(gene.name)
            
            # 连接信号
            slider.valueChanged.connect(lambda value, gn=gene.name: self.on_gene_slider_change(gn, value))
            
            content_layout.addWidget(group)
        
        content_layout.addStretch()
        scroll_area.setWidget(content)
        self.layout.addWidget(scroll_area)
    
    def update_gene_label(self, gene_name):
        gene_data = self.gene_widgets[gene_name]
        gene = gene_data["gene"]
        value = gene.value
        if gene.is_int:
            text = f"当前值: {int(value)}"
        else:
            text = f"当前值: {value:.3f}"
        gene_data["value_label"].setText(text)
    
    def on_gene_slider_change(self, gene_name, value):
        gene_data = self.gene_widgets[gene_name]
        gene = gene_data["gene"]
        
        # 将滑块值转换为实际值
        ratio = value / 1000.0
        actual_value = gene.min + ratio * (gene.max - gene.min)
        if gene.is_int:
            actual_value = int(actual_value)
        
        # 更新基因值
        gene.value = actual_value
        self.update_gene_label(gene_name)
        
        # 重新生成物种形状
        self.species.generate_shape()
        
        # 通知外部更新 - 修复方法调用
        # 通过主窗口引用直接调用更新方法
        main_window = self.window()  # 获取顶级窗口（主窗口）
        if hasattr(main_window, 'update_species_display'):
            main_window.update_species_display()

class GenePoolWidget(QWidget):
    """基因库显示组件"""
    def __init__(self, gene_pool, parent=None):
        super().__init__(parent)
        self.gene_pool = gene_pool
        self.layout = QVBoxLayout(self)
        
        # 标题和按钮
        header_layout = QHBoxLayout()
        title = QLabel("基因库")
        title.setFont(QFont("Arial", 14, QFont.Bold))
        header_layout.addWidget(title)
        
        clear_btn = QPushButton("清除基因库")
        clear_btn.clicked.connect(self.clear_gene_pool)
        header_layout.addWidget(clear_btn)
        
        save_btn = QPushButton("保存基因库")
        save_btn.clicked.connect(self.save_gene_pool)
        header_layout.addWidget(save_btn)
        
        load_btn = QPushButton("加载基因库")
        load_btn.clicked.connect(self.load_gene_pool)
        header_layout.addWidget(load_btn)
        
        header_layout.addStretch()
        self.layout.addLayout(header_layout)
        
        # 选中的亲本
        parents_layout = QHBoxLayout()
        self.parent1_label = QLabel("亲本1: 未选择")
        self.parent2_label = QLabel("亲本2: 未选择")
        parents_layout.addWidget(self.parent1_label)
        parents_layout.addWidget(self.parent2_label)
        self.layout.addLayout(parents_layout)
        
        # 物种网格
        self.species_grid = QListWidget()
        self.species_grid.setViewMode(QListWidget.IconMode)
        self.species_grid.setIconSize(QSize(120, 120))
        self.species_grid.setResizeMode(QListWidget.Adjust)
        self.species_grid.setSpacing(10)
        self.species_grid.itemSelectionChanged.connect(self.on_selection_changed)
        self.layout.addWidget(self.species_grid)
        
        # 繁殖按钮
        breed_btn = QPushButton("繁殖后代")
        breed_btn.clicked.connect(self.breed_selected)
        self.layout.addWidget(breed_btn)
        
        self.update_gene_pool()
    
    def update_gene_pool(self):
        self.species_grid.clear()
        
        for species in self.gene_pool.species:
            # 创建缩略图
            thumb_widget = SpeciesWidget(species)
            thumb_widget.scale = 0.4
            thumb_widget.setFixedSize(120, 120)
            
            # 渲染为图片
            pixmap = QPixmap(thumb_widget.size())
            thumb_widget.render(pixmap)
            
            # 创建列表项
            item = QListWidgetItem()
            item.setIcon(QIcon(pixmap))
            item.setText(species.name)
            item.setData(Qt.UserRole, species)
            self.species_grid.addItem(item)
        
        # 更新亲本显示
        self.update_parents_display()
    
    def update_parents_display(self):
        parent1 = self.gene_pool.selected_species[0]
        parent2 = self.gene_pool.selected_species[1]
        
        self.parent1_label.setText(f"亲本1: {parent1.name if parent1 else '未选择'}")
        self.parent2_label.setText(f"亲本2: {parent2.name if parent2 else '未选择'}")
    
    def on_selection_changed(self):
        selected_items = self.species_grid.selectedItems()
        if not selected_items:
            return
        
        item = selected_items[0]
        species = item.data(Qt.UserRole)
        
        # 检查是否按住Ctrl键选择第二个亲本
        modifiers = QApplication.keyboardModifiers()
        if modifiers == Qt.ControlModifier:
            self.gene_pool.select_for_breeding(species, 1)
        else:
            self.gene_pool.select_for_breeding(species, 0)
        
        self.update_parents_display()
    
    def breed_selected(self):
        child = self.gene_pool.breed_selected()
        if child:
            self.gene_pool.add_species(child)
            self.update_gene_pool()
            
            # 安全地获取主窗口引用
            main_window = None
            parent_widget = self.parent()
            while parent_widget:
                if isinstance(parent_widget, EvolutionSimulator):
                    main_window = parent_widget
                    break
                parent_widget = parent_widget.parent()
            
            if main_window:
                main_window.set_current_species(child)
                QMessageBox.information(self, "繁殖成功", f"新物种 '{child.name}' 已创建并添加到基因库!")
            else:
                QMessageBox.warning(self, "错误", "无法访问主窗口")
    
    def clear_gene_pool(self):
        reply = QMessageBox.question(self, '确认清除', 
                                    '确定要清除整个基因库吗？此操作不可恢复！',
                                    QMessageBox.Yes | QMessageBox.No, 
                                    QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.gene_pool.species.clear()
            self.gene_pool.selected_species = [None, None]
            self.update_gene_pool()
    
    def save_gene_pool(self):
        filename, _ = QFileDialog.getSaveFileName(self, "保存基因库", "", "JSON Files (*.json)")
        if filename:
            self.gene_pool.save_pool(filename)
            QMessageBox.information(self, "保存成功", f"基因库已保存到 {filename}")
    
    def load_gene_pool(self):
        filename, _ = QFileDialog.getOpenFileName(self, "加载基因库", "", "JSON Files (*.json)")
        if filename:
            self.gene_pool.load_pool(filename)
            self.update_gene_pool()
            QMessageBox.information(self, "加载成功", f"基因库已从 {filename} 加载")

class StatsWidget(QWidget):
    """统计信息面板"""
    def __init__(self, gene_pool, parent=None):
        super().__init__(parent)
        self.gene_pool = gene_pool
        self.layout = QVBoxLayout(self)
        
        # 创建图表
        self.figure, self.ax = plt.subplots(figsize=(8, 6))
        self.canvas = FigureCanvas(self.figure)
        self.layout.addWidget(self.canvas)
        
        # 创建数据表格
        self.table_layout = QVBoxLayout()
        self.layout.addLayout(self.table_layout)
        
        self.update_stats()
    
    def update_stats(self):
        """更新统计信息"""
        # 清除旧图表
        self.ax.clear()
        
        if not self.gene_pool.species:
            self.ax.text(0.5, 0.5, '没有数据', ha='center', va='center')
            self.canvas.draw()
            return
        
        # 绘制种群数量历史
        self.ax.plot(range(len(self.gene_pool.population_history)), 
                    list(self.gene_pool.population_history), 
                    'b-', label='种群数量')
        self.ax.set_xlabel('时间')
        self.ax.set_ylabel('数量', color='b')
        self.ax.tick_params('y', colors='b')
        
        # 绘制适应度历史
        ax2 = self.ax.twinx()
        ax2.plot(range(len(self.gene_pool.fitness_history)), 
                list(self.gene_pool.fitness_history), 
                'r-', label='平均适应度')
        ax2.set_ylabel('适应度', color='r')
        ax2.tick_params('y', colors='r')
        
        self.ax.set_title('种群数量和适应度变化')
        self.ax.legend(loc='upper left')
        ax2.legend(loc='upper right')
        
        self.canvas.draw()
        
        # 更新数据表格
        # 清除旧表格 - 修复清除逻辑
        for i in reversed(range(self.table_layout.count())):
            item = self.table_layout.itemAt(i)
            if item.widget() is not None:
                item.widget().setParent(None)
            else:
                # 如果是布局项，清除其包含的小部件
                layout = item.layout()
                if layout:
                    while layout.count():
                        layout_item = layout.takeAt(0)
                        if layout_item.widget():
                            layout_item.widget().deleteLater()
        
        # 创建新表格
        table_title = QLabel("物种统计")
        table_title.setFont(QFont("Arial", 12, QFont.Bold))
        self.table_layout.addWidget(table_title)
        
        # 添加表头
        header_layout = QHBoxLayout()
        headers = ["名称", "代数", "适应度", "大小", "移动力", "智力"]
        for header in headers:
            label = QLabel(header)
            label.setFont(QFont("Arial", 10, QFont.Bold))
            header_layout.addWidget(label)
        self.table_layout.addLayout(header_layout)
        
        # 添加物种数据
        for species in self.gene_pool.species:
            row_layout = QHBoxLayout()
            
            # 名称
            name_label = QLabel(species.name)
            row_layout.addWidget(name_label)
            
            # 代数
            gen_label = QLabel(str(species.generation))
            row_layout.addWidget(gen_label)
            
            # 适应度
            fitness = species.get_fitness()
            fitness_bar = QProgressBar()
            fitness_bar.setRange(0, 100)
            fitness_bar.setValue(int(fitness * 100))
            fitness_bar.setFormat(f"{fitness:.2f}")
            row_layout.addWidget(fitness_bar)
            
            # 大小
            size = species.genome.get_value("size")
            size_label = QLabel(f"{size:.2f}")
            row_layout.addWidget(size_label)
            
            # 移动力
            mobility = species.genome.get_value("mobility")
            mobility_label = QLabel(f"{mobility:.2f}")
            row_layout.addWidget(mobility_label)
            
            # 智力
            intelligence = species.genome.get_value("intelligence")
            intelligence_label = QLabel(f"{intelligence:.2f}")
            row_layout.addWidget(intelligence_label)
            
            self.table_layout.addLayout(row_layout)

class EnvironmentSimulator(QWidget):
    """环境模拟面板"""
    def __init__(self, gene_pool, parent=None):
        super().__init__(parent)
        self.gene_pool = gene_pool
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.simulate_step)
        self.simulation_speed = 1  # 模拟速度（步数/秒）
        self.current_step = 0
        
        self.layout = QVBoxLayout(self)
        
        # 控制面板
        control_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("开始模拟")
        self.start_btn.clicked.connect(self.toggle_simulation)
        control_layout.addWidget(self.start_btn)
        
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setRange(1, 10)
        self.speed_slider.setValue(self.simulation_speed)
        self.speed_slider.valueChanged.connect(self.set_simulation_speed)
        control_layout.addWidget(QLabel("速度:"))
        control_layout.addWidget(self.speed_slider)
        
        self.step_label = QLabel("步骤: 0")
        control_layout.addWidget(self.step_label)
        
        self.layout.addLayout(control_layout)
        
        # 环境参数
        env_group = QGroupBox("环境参数")
        env_layout = QFormLayout(env_group)
        
        self.temperature_spin = QDoubleSpinBox()
        self.temperature_spin.setRange(-10, 50)
        self.temperature_spin.setValue(25)
        env_layout.addRow("温度 (°C):", self.temperature_spin)
        
        self.humidity_spin = QDoubleSpinBox()
        self.humidity_spin.setRange(0, 100)
        self.humidity_spin.setValue(50)
        env_layout.addRow("湿度 (%):", self.humidity_spin)
        
        self.food_spin = QDoubleSpinBox()
        self.food_spin.setRange(0, 100)
        self.food_spin.setValue(70)
        env_layout.addRow("食物丰富度:", self.food_spin)
        
        self.layout.addWidget(env_group)
        
        # 物种显示区域
        self.species_display = QScrollArea()
        self.species_display.setWidgetResizable(True)
        self.display_widget = QWidget()
        self.display_layout = QVBoxLayout(self.display_widget)
        self.species_display.setWidget(self.display_widget)
        self.layout.addWidget(self.species_display)
        
        self.update_display()
    
    def toggle_simulation(self):
        if self.timer.isActive():
            self.timer.stop()
            self.start_btn.setText("开始模拟")
        else:
            self.timer.start(1000 // self.simulation_speed)
            self.start_btn.setText("停止模拟")
    
    def set_simulation_speed(self, speed):
        self.simulation_speed = speed
        if self.timer.isActive():
            self.timer.setInterval(1000 // speed)
    
    def simulate_step(self):
        """执行一个模拟步骤"""
        self.current_step += 1
        self.step_label.setText(f"步骤: {self.current_step}")
        
        # 获取环境参数
        temperature = self.temperature_spin.value()
        humidity = self.humidity_spin.value()
        food = self.food_spin.value()
        
        # 在这里添加模拟逻辑
        # 例如：根据环境条件调整物种的适应度
        # 模拟物种的繁殖和死亡
        # 等等...
        
        # 简单示例：随机添加一个新物种
        if random.random() < 0.1 and self.gene_pool.species:
            parent = random.choice(self.gene_pool.species)
            new_species = parent.mutate()
            self.gene_pool.add_species(new_species)
        
        # 随机移除一个物种
        if random.random() < 0.05 and len(self.gene_pool.species) > 1:
            species = random.choice(self.gene_pool.species)
            self.gene_pool.remove_species(species)
        
        # 更新显示
        self.update_display()
    
    def update_display(self):
        """更新物种显示"""
        # 清除旧显示
        for i in reversed(range(self.display_layout.count())):
            self.display_layout.itemAt(i).widget().setParent(None)
        
        # 添加新物种
        for species in self.gene_pool.species:
            species_frame = QFrame()
            species_frame.setFrameShape(QFrame.StyledPanel)
            frame_layout = QHBoxLayout(species_frame)
            
            # 物种图像
            species_widget = SpeciesWidget(species)
            species_widget.setFixedSize(150, 150)
            species_widget.scale = 0.6
            frame_layout.addWidget(species_widget)
            
            # 物种信息
            info_layout = QVBoxLayout()
            info_layout.addWidget(QLabel(f"名称: {species.name}"))
            info_layout.addWidget(QLabel(f"代数: {species.generation}"))
            
            # 适应度
            fitness = species.get_fitness()
            fitness_bar = QProgressBar()
            fitness_bar.setRange(0, 100)
            fitness_bar.setValue(int(fitness * 100))
            fitness_bar.setFormat(f"适应度: {fitness:.2f}")
            info_layout.addWidget(fitness_bar)
            
            frame_layout.addLayout(info_layout)
            
            self.display_layout.addWidget(species_frame)

class EvolutionSimulator(QMainWindow):
    """主应用程序窗口"""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("进化物种创造系统 - 基因模拟")
        self.setGeometry(100, 100, 1200, 800)
        
        # 创建基因库和初始物种
        self.gene_pool = GenePool()
        self.current_species = Species(name="初始物种")
        self.gene_pool.add_species(self.current_species)
        
        # 创建主布局
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        
        # 创建标签页
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        # 创建物种编辑标签页
        self.create_species_tab()
        
        # 创建基因库标签页
        self.gene_pool_tab = GenePoolWidget(self.gene_pool)
        self.tab_widget.addTab(self.gene_pool_tab, "基因库")
        
        # 创建统计标签页
        self.stats_tab = StatsWidget(self.gene_pool)
        self.tab_widget.addTab(self.stats_tab, "统计信息")
        
        # 创建环境模拟标签页
        self.env_sim_tab = EnvironmentSimulator(self.gene_pool)
        self.tab_widget.addTab(self.env_sim_tab, "环境模拟")
        
        # 状态栏
        self.statusBar().showMessage("就绪")
    
    def create_species_tab(self):
        """创建物种编辑标签页"""
        tab = QWidget()
        layout = QHBoxLayout(tab)
        
        # 左侧：物种展示
        left_panel = QVBoxLayout()
        
        # 物种名称
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("物种名称:"))
        self.name_edit = QLineEdit(self.current_species.name)
        self.name_edit.textChanged.connect(self.update_species_name)
        name_layout.addWidget(self.name_edit)
        left_panel.addLayout(name_layout)
        
        # 物种展示区
        self.species_display = SpeciesWidget(self.current_species)
        self.species_display.setMinimumSize(400, 400)
        left_panel.addWidget(self.species_display)
        
        # 物种信息
        info_layout = QVBoxLayout()
        self.generation_label = QLabel(f"代数: {self.current_species.generation}")
        info_layout.addWidget(self.generation_label)
        
        self.parents_label = QLabel(f"父母: {', '.join(p.name for p in self.current_species.parents) if self.current_species.parents else '无'}")
        info_layout.addWidget(self.parents_label)
        
        self.fitness_label = QLabel(f"适应度: {self.current_species.get_fitness():.2f}")
        info_layout.addWidget(self.fitness_label)
        left_panel.addLayout(info_layout)
        
        # 操作按钮
        btn_layout = QHBoxLayout()
        
        mutate_btn = QPushButton("随机突变")
        mutate_btn.clicked.connect(self.mutate_current)
        btn_layout.addWidget(mutate_btn)
        
        add_to_pool_btn = QPushButton("添加到基因库")
        add_to_pool_btn.clicked.connect(self.add_to_pool)
        btn_layout.addWidget(add_to_pool_btn)
        
        save_btn = QPushButton("保存物种")
        save_btn.clicked.connect(self.save_species)
        btn_layout.addWidget(save_btn)
        
        left_panel.addLayout(btn_layout)
        
        # 右侧：基因编辑器
        self.gene_editor = GeneEditor(self.current_species)
        
        # 添加到布局
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self.create_widget_from_layout(left_panel))
        splitter.addWidget(self.gene_editor)
        splitter.setSizes([500, 500])
        layout.addWidget(splitter)
        
        self.tab_widget.addTab(tab, "物种编辑")
    
    def create_widget_from_layout(self, layout):
        """从布局创建小部件"""
        widget = QWidget()
        widget.setLayout(layout)
        return widget
    
    def update_species_display(self):
        """更新物种显示"""
        self.species_display.update()
        self.fitness_label.setText(f"适应度: {self.current_species.get_fitness():.2f}")
        self.stats_tab.update_stats()
    
    def update_species_name(self, name):
        """更新物种名称"""
        self.current_species.name = name
        self.name_edit.setText(name)
    
    def mutate_current(self):
        """突变当前物种"""
        self.current_species = self.current_species.mutate()
        self.update_editor()
        self.statusBar().showMessage(f"创建了突变体: {self.current_species.name}", 3000)
    
    def add_to_pool(self):
        """添加当前物种到基因库"""
        self.gene_pool.add_species(self.current_species.copy())
        self.gene_pool_tab.update_gene_pool()
        self.statusBar().showMessage(f"物种 '{self.current_species.name}' 已添加到基因库", 3000)
    
    def save_species(self):
        """保存当前物种到文件"""
        filename, _ = QFileDialog.getSaveFileName(self, "保存物种", "", "JSON Files (*.json)")
        if filename:
            self.current_species.save_to_file(filename)
            self.statusBar().showMessage(f"物种已保存到 {filename}", 5000)
    
    def set_current_species(self, species):
        """设置当前编辑的物种"""
        self.current_species = species
        self.update_editor()
    
    def update_editor(self):
        """更新编辑器"""
        # 更新名称
        self.name_edit.setText(self.current_species.name)
        
        # 更新信息
        self.generation_label.setText(f"代数: {self.current_species.generation}")
        self.parents_label.setText(f"父母: {', '.join(p.name for p in self.current_species.parents) if self.current_species.parents else '无'}")
        self.fitness_label.setText(f"适应度: {self.current_species.get_fitness():.2f}")
        
        # 重新创建基因编辑器
        old_editor = self.gene_editor
        self.gene_editor = GeneEditor(self.current_species)
        
        # 替换编辑器
        tab = self.tab_widget.widget(0)
        layout = tab.layout()
        splitter = layout.itemAt(0).widget()
        splitter.replaceWidget(1, self.gene_editor)
        old_editor.deleteLater()
        
        # 更新显示
        self.update_species_display()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = EvolutionSimulator()
    window.show()
    sys.exit(app.exec_())