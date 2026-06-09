import pygame
import numpy as np
import random
import math
import json
import time
from datetime import datetime
from sklearn.cluster import DBSCAN
from sklearn.manifold import TSNE
import tensorflow as tf
from transformers import pipeline, AutoTokenizer, AutoModel
import openai
from diffusers import StableDiffusionPipeline
import torch
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import networkx as nx
from scipy import spatial
import warnings
warnings.filterwarnings('ignore')

# 初始化pygame
pygame.init()
W, H = 1400, 900
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("超维灵感设计引擎")

# 颜色配置
COLORS = {
    'background': (8, 5, 40),
    'ui_dark': (20, 15, 60),
    'ui_medium': (42, 30, 90),
    'ui_light': (70, 50, 120),
    'core_idea': (255, 105, 180),
    'related_idea': (138, 43, 226),
    'idea_fragment': (65, 105, 225),
    'connection': (123, 104, 238),
    'text_primary': (255, 255, 255),
    'text_secondary': (200, 200, 220),
    'accent1': (0, 255, 255),
    'accent2': (255, 215, 0),
    'accent3': (50, 205, 50)
}

# 量子启发粒子系统
class QuantumParticle:
    def __init__(self, position, idea_strength=1.0, coherence=0.8):
        self.position = np.array(position, dtype=float)
        self.velocity = np.random.normal(0, 0.5, 2)
        self.acceleration = np.zeros(2)
        self.idea_strength = idea_strength  # 0-1之间的灵感强度
        self.coherence = coherence  # 相干性，影响量子行为
        self.quantum_state = np.random.random(4)  # 模拟量子态
        self.entangled_particles = []  # 纠缠粒子列表
        self.history = []  # 历史轨迹
        self.superposition = False  # 是否处于叠加态
        self.collapsed = False  # 是否已坍缩
        self.type = self.determine_type()
        self.color = self.calculate_color()
        self.lifespan = np.random.randint(300, 800)
        self.age = 0
        self.energy = 1.0
        
    def determine_type(self):
        if self.idea_strength > 0.8:
            return "core"
        elif self.idea_strength > 0.5:
            return "related"
        else:
            return "fragment"
    
    def calculate_color(self):
        base_colors = {
            "core": COLORS['core_idea'],
            "related": COLORS['related_idea'], 
            "fragment": COLORS['idea_fragment']
        }
        base = base_colors[self.type]
        
        # 量子态影响颜色
        r = min(255, base[0] + int(50 * self.quantum_state[0]))
        g = min(255, base[1] + int(50 * self.quantum_state[1]))
        b = min(255, base[2] + int(50 * self.quantum_state[2]))
        
        return (r, g, b)
    
    def apply_quantum_force(self, particles, dt):
        """应用量子力学启发的力"""
        # 量子隧穿效应
        if random.random() < 0.01 * (1 - self.coherence):
            self.velocity = np.random.normal(0, 2, 2)
            
        # 纠缠效应
        for other in self.entangled_particles:
            if other in particles:
                direction = other.position - self.position
                distance = np.linalg.norm(direction)
                if distance > 0:
                    direction /= distance
                    # 纠缠力随距离增加而增强（非局域性）
                    force = direction * 0.5 * self.coherence * other.coherence
                    self.acceleration += force
        
        # 叠加态行为
        if self.superposition and not self.collapsed:
            # 在多个位置之间"闪烁"
            if random.random() < 0.05:
                self.position += np.random.normal(0, 10, 2)
                
        # 波函数坍缩
        if random.random() < 0.005 and self.superposition:
            self.collapse()
    
    def collapse(self):
        """波函数坍缩"""
        self.superposition = False
        self.collapsed = True
        # 坍缩后获得确定的位置和速度
        self.position += np.random.normal(0, 5, 2)
        self.velocity = np.random.normal(0, 1, 2)
        self.idea_strength = min(1.0, self.idea_strength + 0.1)
    
    def entangle(self, other_particle):
        """与另一个粒子建立纠缠"""
        if other_particle not in self.entangled_particles:
            self.entangled_particles.append(other_particle)
            other_particle.entangled_particles.append(self)
    
    def update(self, particles, dt):
        self.age += 1
        self.energy = max(0, 1 - self.age / self.lifespan)
        
        # 保存历史
        self.history.append(self.position.copy())
        if len(self.history) > 50:
            self.history.pop(0)
        
        # 应用量子力
        self.apply_quantum_force(particles, dt)
        
        # 更新物理状态
        self.velocity += self.acceleration * dt
        self.position += self.velocity * dt
        self.acceleration = np.zeros(2)
        
        # 边界处理
        self.position[0] = np.clip(self.position[0], 0, W)
        self.position[1] = np.clip(self.position[1], 0, H)
        
        # 能量衰减
        if self.energy <= 0:
            return False
            
        return True
    
    def draw(self, surface):
        # 绘制历史轨迹
        for i, pos in enumerate(self.history):
            alpha = int(100 * i / len(self.history))
            radius = max(1, int(3 * i / len(self.history)))
            color = (*self.color, alpha)
            pygame.draw.circle(surface, color, pos.astype(int), radius)
        
        # 绘制粒子
        radius = int(5 + 5 * self.idea_strength)
        pygame.draw.circle(surface, self.color, self.position.astype(int), radius)
        
        # 叠加态效果
        if self.superposition:
            for _ in range(3):
                offset = np.random.normal(0, 3, 2)
                pygame.draw.circle(surface, (*self.color, 100), 
                                 (self.position + offset).astype(int), 
                                 radius // 2)
        
        # 核心灵感发光效果
        if self.type == "core":
            glow_radius = int(radius * 3)
            glow_surf = pygame.Surface((glow_radius*2, glow_radius*2), pygame.SRCALPHA)
            pygame.draw.circle(glow_surf, (*self.color, 80), 
                              (glow_radius, glow_radius), glow_radius)
            surface.blit(glow_surf, (self.position[0]-glow_radius, self.position[1]-glow_radius))

# 多维灵感场
class MultidimensionalField:
    def __init__(self, width, height, dimensions=5):
        self.width = width
        self.height = height
        self.dimensions = dimensions
        self.grid_size = 25
        self.rows = height // self.grid_size
        self.cols = width // self.grid_size
        
        # 创建多维场（每个网格点有多个维度的向量）
        self.field = np.random.normal(0, 0.3, (self.rows, self.cols, dimensions, 2))
        
        # 添加周期性结构
        self.create_periodic_structures()
        
    def create_periodic_structures(self):
        """创建周期性场结构（类似晶体或波）"""
        for y in range(self.rows):
            for x in range(self.cols):
                # 基础波场
                angle1 = 2 * math.pi * (x / 10 + y / 15)
                angle2 = 2 * math.pi * (x / 7 - y / 12)
                
                # 不同维度的场有不同的周期性
                for d in range(self.dimensions):
                    freq = 1 + d * 0.5
                    self.field[y, x, d, 0] += 0.2 * math.sin(angle1 * freq)
                    self.field[y, x, d, 1] += 0.2 * math.cos(angle2 * freq)
    
    def get_force(self, position, particle_state):
        """根据粒子状态获取多维场力"""
        x_idx = min(max(int(position[0] / self.grid_size), 0), self.cols-1)
        y_idx = min(max(int(position[1] / self.grid_size), 0), self.rows-1)
        
        # 根据粒子的量子态选择场维度
        dominant_dim = np.argmax(particle_state[:self.dimensions])
        
        return self.field[y_idx, x_idx, dominant_dim]
    
    def evolve(self, dt):
        """场的动态演化"""
        # 简单的扩散和波动
        for y in range(1, self.rows-1):
            for x in range(1, self.cols-1):
                for d in range(self.dimensions):
                    # 拉普拉斯算子近似（扩散）
                    laplacian = (self.field[y-1, x, d] + self.field[y+1, x, d] + 
                                self.field[y, x-1, d] + self.field[y, x+1, d] - 
                                4 * self.field[y, x, d]) * 0.1
                    
                    # 波动项
                    wave = np.array([-self.field[y, x, d, 1], self.field[y, x, d, 0]]) * 0.05
                    
                    self.field[y, x, d] += (laplacian + wave) * dt
    
    def draw(self, surface):
        """绘制场可视化"""
        for y in range(0, self.rows, 2):
            for x in range(0, self.cols, 2):
                center = (x*self.grid_size + self.grid_size//2, 
                         y*self.grid_size + self.grid_size//2)
                
                # 计算平均场强
                avg_force = np.mean(self.field[y, x], axis=0)
                strength = np.linalg.norm(avg_force)
                
                # 绘制场线
                if strength > 0.1:
                    end = (center[0] + avg_force[0]*20, center[1] + avg_force[1]*20)
                    color_intensity = min(255, int(150 + 100 * strength))
                    color = (100, color_intensity, 200, 150)
                    pygame.draw.line(surface, color, center, end, 1)
                
                # 绘制场强点
                radius = int(2 + 3 * strength)
                pygame.draw.circle(surface, (80, 120, 200, 100), center, radius)

# AI集成系统
class AIIntegration:
    def __init__(self):
        self.concept_graph = nx.Graph()
        self.semantic_space = {}
        self.inspiration_history = []
        
        # 初始化各种AI模型（简化版本，实际使用需要相应API密钥）
        try:
            self.sentiment_analyzer = pipeline("sentiment-analysis")
            self.text_generator = pipeline("text-generation", model="gpt2")
        except:
            print("部分AI模型初始化失败，使用模拟模式")
            self.sentiment_analyzer = None
            self.text_generator = None
            
        # 概念数据库
        self.concept_database = self.load_concept_database()
        
    def load_concept_database(self):
        """加载概念数据库"""
        concepts = {
            "量子": ["纠缠", "叠加", "隧穿", "计算", "比特"],
            "神经": ["网络", "科学", "可塑性", "编码", "连接"],
            "混沌": ["理论", "边缘", "吸引子", "分形", "系统"],
            "生物": ["灵感", "模拟", "进化", "形态", "智能"],
            "数学": ["拓扑", "几何", "群论", "流形", "对称"],
            "艺术": ["生成", "算法", "交互", "沉浸", "表现"]
        }
        return concepts
    
    def analyze_particle_system(self, particles):
        """分析粒子系统并生成洞察"""
        if not particles:
            return "系统等待灵感输入..."
        
        # 提取系统特征
        positions = [p.position for p in particles]
        strengths = [p.idea_strength for p in particles]
        types = [p.type for p in particles]
        
        # 计算系统指标
        avg_strength = np.mean(strengths)
        coherence = np.std(strengths)
        core_count = sum(1 for t in types if t == "core")
        entropy = self.calculate_entropy(positions)
        
        # 生成系统洞察
        if core_count == 0:
            stage = "混沌初开"
        elif core_count < 3:
            stage = "灵感萌芽"
        elif core_count < 7:
            stage = "创意汇聚"
        else:
            stage = "系统涌现"
            
        insight = f"{stage} | 核心灵感:{core_count} | 平均强度:{avg_strength:.2f} | 熵:{entropy:.2f}"
        
        # 添加AI生成的描述
        if self.text_generator and random.random() < 0.3:
            try:
                prompt = f"在{stage}阶段，灵感系统表现出"
                description = self.text_generator(prompt, max_length=30, num_return_sequences=1)[0]['generated_text']
                insight += " | " + description[len(prompt):]
            except:
                pass
                
        return insight
    
    def calculate_entropy(self, positions):
        """计算位置分布的熵"""
        if len(positions) < 2:
            return 0
            
        # 将空间划分为网格
        grid_size = 10
        x_bins = np.linspace(0, W, grid_size)
        y_bins = np.linspace(0, H, grid_size)
        
        # 计算2D直方图
        hist, _, _ = np.histogram2d([p[0] for p in positions], [p[1] for p in positions], 
                                   bins=[x_bins, y_bins])
        hist = hist.flatten()
        hist = hist[hist > 0]  # 移除空桶
        hist = hist / hist.sum()  # 归一化
        
        # 计算香农熵
        entropy = -np.sum(hist * np.log(hist))
        return entropy
    
    def generate_concept_fusion(self, count=3):
        """生成概念融合"""
        domains = random.sample(list(self.concept_database.keys()), 2)
        concepts = []
        
        for domain in domains:
            concept = random.choice(self.concept_database[domain])
            concepts.append(domain + concept)
            
        # 添加连接词
        connectors = ["-", "×", "⊗", "⊕", "◊"]
        connector = random.choice(connectors)
        
        return connector.join(concepts)
    
    def build_concept_graph(self, particles):
        """构建概念图"""
        self.concept_graph.clear()
        
        for i, particle in enumerate(particles):
            concept = self.generate_concept_fusion()
            self.concept_graph.add_node(i, 
                                      concept=concept,
                                      strength=particle.idea_strength,
                                      position=particle.position)
            
        # 添加边（基于距离和强度）
        for i in range(len(particles)):
            for j in range(i+1, len(particles)):
                dist = np.linalg.norm(particles[i].position - particles[j].position)
                if dist < 150:  # 距离阈值
                    weight = (particles[i].idea_strength + particles[j].idea_strength) / (dist + 1)
                    self.concept_graph.add_edge(i, j, weight=weight)

# 3D可视化系统
class Visualization3D:
    def __init__(self):
        self.fig = None
        self.ax = None
        self.last_update = 0
        
    def create_3d_visualization(self, particles, filename="inspiration_3d.png"):
        """创建3D灵感可视化"""
        if not particles:
            return None
            
        # 防止过于频繁更新
        current_time = time.time()
        if current_time - self.last_update < 5:  # 5秒冷却
            return filename
        self.last_update = current_time
        
        # 准备数据
        positions = np.array([p.position for p in particles])
        strengths = np.array([p.idea_strength for p in particles])
        types = [p.type for p in particles]
        
        # 使用t-SNE降维到3D
        if len(positions) > 3:
            try:
                tsne = TSNE(n_components=3, random_state=42)
                positions_3d = tsne.fit_transform(positions)
            except:
                # 如果t-SNE失败，使用PCA近似
                cov = np.cov(positions.T)
                eigvals, eigvecs = np.linalg.eig(cov)
                positions_3d = positions @ eigvecs[:, :3]
        else:
            positions_3d = np.column_stack([positions, np.zeros(len(positions))])
        
        # 创建3D图
        self.fig = plt.figure(figsize=(12, 9), facecolor='#080528')
        self.ax = self.fig.add_subplot(111, projection='3d')
        
        # 根据类型绘制点
        colors = {'core': 'magenta', 'related': 'purple', 'fragment': 'blue'}
        sizes = {'core': 100, 'related': 50, 'fragment': 20}
        
        for p_type in colors.keys():
            mask = [t == p_type for t in types]
            if any(mask):
                self.ax.scatter(positions_3d[mask, 0], positions_3d[mask, 1], positions_3d[mask, 2],
                              c=colors[p_type], s=sizes[p_type], alpha=0.7, label=p_type)
        
        # 添加连接线
        for i in range(len(positions_3d)):
            for j in range(i+1, len(positions_3d)):
                dist = np.linalg.norm(positions_3d[i] - positions_3d[j])
                if dist < np.percentile([np.linalg.norm(positions_3d[k] - positions_3d[l]) 
                                       for k in range(len(positions_3d)) 
                                       for l in range(k+1, len(positions_3d))], 30):
                    self.ax.plot([positions_3d[i, 0], positions_3d[j, 0]],
                               [positions_3d[i, 1], positions_3d[j, 1]],
                               [positions_3d[i, 2], positions_3d[j, 2]], 
                               'gray', alpha=0.3, linewidth=0.5)
        
        # 美化图表
        self.ax.set_facecolor('#080528')
        self.ax.xaxis.pane.fill = False
        self.ax.yaxis.pane.fill = False
        self.ax.zaxis.pane.fill = False
        self.ax.grid(True, color='gray', alpha=0.3)
        self.ax.set_title("灵感三维分布", color='white', fontsize=16)
        self.ax.legend()
        
        # 保存图像
        plt.tight_layout()
        plt.savefig(filename, dpi=120, facecolor='#080528', edgecolor='none',
                   bbox_inches='tight', pad_inches=0.1)
        plt.close()
        
        return filename

# 高级UI组件
class AdvancedUI:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.panels = {}
        self.buttons = {}
        self.sliders = {}
        self.init_ui()
        
    def init_ui(self):
        """初始化UI元素"""
        # 控制面板
        self.panels['control'] = {
            'rect': pygame.Rect(10, 10, 300, 200),
            'color': COLORS['ui_dark'],
            'alpha': 220
        }
        
        # 信息面板
        self.panels['info'] = {
            'rect': pygame.Rect(10, 220, 300, 400),
            'color': COLORS['ui_dark'], 
            'alpha': 200
        }
        
        # 可视化面板
        self.panels['visualization'] = {
            'rect': pygame.Rect(320, 10, W-330, H-20),
            'color': COLORS['background'],
            'alpha': 255
        }
        
        # 按钮
        button_y = 30
        buttons = [
            ("生成灵感", "generate", (30, button_y)),
            ("清空画布", "clear", (30, button_y+40)),
            ("3D可视化", "visualize_3d", (30, button_y+80)),
            ("保存状态", "save", (30, button_y+120)),
            ("量子隧穿", "quantum_tunnel", (160, button_y)),
            ("建立纠缠", "entangle", (160, button_y+40)),
            ("概念图谱", "concept_map", (160, button_y+80))
        ]
        
        for text, action, pos in buttons:
            self.buttons[action] = {
                'rect': pygame.Rect(pos[0], pos[1], 120, 30),
                'text': text,
                'color': COLORS['ui_light'],
                'hover_color': COLORS['accent1'],
                'action': action
            }
    
    def draw(self, surface, system_insight, particle_count):
        """绘制UI"""
        # 绘制面板
        for panel in self.panels.values():
            panel_surface = pygame.Surface(panel['rect'].size, pygame.SRCALPHA)
            panel_surface.fill((*panel['color'], panel['alpha']))
            surface.blit(panel_surface, panel['rect'])
            
            # 面板边框
            pygame.draw.rect(surface, COLORS['accent1'], panel['rect'], 2, border_radius=5)
        
        # 绘制按钮
        mouse_pos = pygame.mouse.get_pos()
        for button in self.buttons.values():
            color = button['hover_color'] if button['rect'].collidepoint(mouse_pos) else button['color']
            pygame.draw.rect(surface, color, button['rect'], border_radius=5)
            pygame.draw.rect(surface, COLORS['text_primary'], button['rect'], 2, border_radius=5)
            
            # 按钮文字
            font = pygame.font.SysFont('microsoftyaheiui', 14)
            text = font.render(button['text'], True, COLORS['text_primary'])
            text_rect = text.get_rect(center=button['rect'].center)
            surface.blit(text, text_rect)
        
        # 绘制系统信息
        self.draw_system_info(surface, system_insight, particle_count)
    
    def draw_system_info(self, surface, system_insight, particle_count):
        """绘制系统信息"""
        font_small = pygame.font.SysFont('microsoftyaheiui', 12)
        font_medium = pygame.font.SysFont('microsoftyaheiui', 14)
        
        info_y = 230
        lines = [
            f"粒子数量: {particle_count}",
            f"系统状态: {system_insight}",
            "",
            "操作指南:",
            "- 点击画布: 生成灵感粒子",
            "- 拖拽粒子: 移动灵感位置", 
            "- 右键粒子: 建立量子纠缠",
            "- 空格键: 切换场可视化",
            "- V键: 生成3D可视化",
            "- C键: 清空画布"
        ]
        
        for line in lines:
            text = font_small.render(line, True, COLORS['text_secondary'])
            surface.blit(text, (20, info_y))
            info_y += 20
    
    def check_click(self, pos):
        """检查UI点击"""
        for button_id, button in self.buttons.items():
            if button['rect'].collidepoint(pos):
                return button['action']
        return None

# 主应用类
class HyperdimensionalInspirationEngine:
    def __init__(self):
        self.screen = pygame.display.set_mode((W, H))
        self.clock = pygame.time.Clock()
        self.running = True
        
        # 初始化系统组件
        self.particles = []
        self.field = MultidimensionalField(W, H)
        self.ai_system = AIIntegration()
        self.visualization_3d = Visualization3D()
        self.ui = AdvancedUI(W, H)
        
        # 系统状态
        self.system_insight = "系统初始化完成"
        self.show_field = False
        self.dragging_particle = None
        self.concept_map_image = None
        self.visualization_image = None
        self.last_ai_analysis = 0
        
        # 性能优化
        self.last_particle_update = 0
        self.particle_update_interval = 0.016  # ~60fps
        
        # 字体
        self.font = pygame.font.SysFont('microsoftyaheiui', 16)
        self.title_font = pygame.font.SysFont('microsoftyaheiui', 24, bold=True)
        
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                
            elif event.type == pygame.MOUSEBUTTONDOWN:
                # 检查UI点击
                ui_action = self.ui.check_click(event.pos)
                if ui_action:
                    self.handle_ui_action(ui_action)
                else:
                    # 处理画布点击
                    if event.button == 1:  # 左键
                        self.handle_canvas_click(event.pos)
                    elif event.button == 3:  # 右键
                        self.handle_right_click(event.pos)
                        
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    self.dragging_particle = None
                    
            elif event.type == pygame.MOUSEMOTION:
                if self.dragging_particle is not None:
                    self.dragging_particle.position = np.array(event.pos)
                    
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    self.show_field = not self.show_field
                elif event.key == pygame.K_v:
                    self.generate_3d_visualization()
                elif event.key == pygame.K_c:
                    self.particles = []
                    self.system_insight = "画布已清空"
                elif event.key == pygame.K_s:
                    self.save_system_state()
    
    def handle_ui_action(self, action):
        """处理UI动作"""
        if action == "generate":
            x, y = random.randint(100, W-100), random.randint(100, H-100)
            self.spawn_particles(x, y, random.randint(5, 15))
        elif action == "clear":
            self.particles = []
            self.system_insight = "画布已清空"
        elif action == "visualize_3d":
            self.generate_3d_visualization()
        elif action == "save":
            self.save_system_state()
        elif action == "quantum_tunnel":
            self.trigger_quantum_tunnel()
        elif action == "entangle":
            self.trigger_entanglement()
        elif action == "concept_map":
            self.generate_concept_map()
    
    def handle_canvas_click(self, pos):
        """处理画布点击"""
        # 检查是否点击了粒子
        for particle in self.particles:
            if np.linalg.norm(particle.position - pos) < 10:
                self.dragging_particle = particle
                return
        
        # 如果没有点击粒子，生成新粒子
        self.spawn_particles(pos[0], pos[1], random.randint(8, 20))
    
    def handle_right_click(self, pos):
        """处理右键点击（建立纠缠）"""
        clicked_particles = []
        for particle in self.particles:
            if np.linalg.norm(particle.position - pos) < 15:
                clicked_particles.append(particle)
        
        # 如果点击了多个粒子，建立纠缠
        if len(clicked_particles) >= 2:
            for i in range(len(clicked_particles)):
                for j in range(i+1, len(clicked_particles)):
                    clicked_particles[i].entangle(clicked_particles[j])
            
            self.system_insight = f"建立了{len(clicked_particles)}个粒子之间的量子纠缠"
    
    def spawn_particles(self, x, y, count):
        """生成粒子"""
        for _ in range(count):
            idea_strength = random.random()
            coherence = random.uniform(0.5, 0.95)
            particle = QuantumParticle([x, y], idea_strength, coherence)
            
            # 随机设置叠加态
            if random.random() < 0.2:
                particle.superposition = True
                
            self.particles.append(particle)
        
        self.system_insight = self.ai_system.analyze_particle_system(self.particles)
    
    def trigger_quantum_tunnel(self):
        """触发量子隧穿事件"""
        if not self.particles:
            return
            
        # 随机选择一些粒子进行隧穿
        for _ in range(min(5, len(self.particles))):
            particle = random.choice(self.particles)
            particle.velocity = np.random.normal(0, 3, 2)
            particle.superposition = True
            
        self.system_insight = "量子隧穿事件已触发"
    
    def trigger_entanglement(self):
        """触发纠缠事件"""
        if len(self.particles) < 2:
            return
            
        # 随机建立一些纠缠对
        for _ in range(min(10, len(self.particles) // 2)):
            p1, p2 = random.sample(self.particles, 2)
            p1.entangle(p2)
            
        self.system_insight = f"建立了多个量子纠缠对"
    
    def generate_3d_visualization(self):
        """生成3D可视化"""
        if self.particles:
            filename = self.visualization_3d.create_3d_visualization(self.particles)
            if filename:
                try:
                    self.visualization_image = pygame.image.load(filename)
                    # 缩放图像以适应UI
                    target_rect = self.ui.panels['visualization']['rect']
                    scaled_width = target_rect.width - 40
                    scaled_height = target_rect.height - 40
                    self.visualization_image = pygame.transform.scale(
                        self.visualization_image, (scaled_width, scaled_height))
                except:
                    self.visualization_image = None
    
    def generate_concept_map(self):
        """生成概念图谱"""
        self.ai_system.build_concept_graph(self.particles)
        
        # 这里可以添加概念图谱的可视化代码
        # 由于复杂度，这里简化为文本显示
        if self.ai_system.concept_graph.nodes():
            concepts = [self.ai_system.concept_graph.nodes[i]['concept'] 
                       for i in self.ai_system.concept_graph.nodes()]
            self.system_insight = f"概念图谱: {', '.join(concepts[:5])}..."
    
    def save_system_state(self):
        """保存系统状态"""
        state = {
            'timestamp': datetime.now().isoformat(),
            'particle_count': len(self.particles),
            'system_insight': self.system_insight
        }
        
        try:
            with open('inspiration_state.json', 'w') as f:
                json.dump(state, f, indent=2)
            self.system_insight = "系统状态已保存"
        except:
            self.system_insight = "保存失败"
    
    def update(self, dt):
        """更新系统状态"""
        current_time = time.time()
        
        # 更新场
        self.field.evolve(dt)
        
        # 更新粒子（性能优化）
        if current_time - self.last_particle_update >= self.particle_update_interval:
            self.particles = [p for p in self.particles if p.update(self.particles, dt)]
            self.last_particle_update = current_time
        
        # 定期AI分析
        if current_time - self.last_ai_analysis > 3:  # 每3秒分析一次
            self.system_insight = self.ai_system.analyze_particle_system(self.particles)
            self.last_ai_analysis = current_time
    
    def draw(self):
        """绘制系统"""
        # 绘制背景
        self.screen.fill(COLORS['background'])
        
        # 绘制场
        if self.show_field:
            self.field.draw(self.screen)
        
        # 绘制粒子
        for particle in self.particles:
            particle.draw(self.screen)
        
        # 绘制连接线（纠缠关系）
        for particle in self.particles:
            for other in particle.entangled_particles:
                if other in self.particles:
                    pygame.draw.line(self.screen, COLORS['connection'], 
                                   particle.position.astype(int), 
                                   other.position.astype(int), 1)
        
        # 绘制3D可视化
        if self.visualization_image:
            viz_rect = self.ui.panels['visualization']['rect']
            self.screen.blit(self.visualization_image, 
                           (viz_rect.x + 20, viz_rect.y + 20))
        
        # 绘制UI
        self.ui.draw(self.screen, self.system_insight, len(self.particles))
        
        # 绘制标题
        title = self.title_font.render("超维灵感设计引擎", True, COLORS['accent1'])
        self.screen.blit(title, (W//2 - title.get_width()//2, 15))
    
    def run(self):
        """主循环"""
        while self.running:
            dt = self.clock.tick(60) / 1000.0  # 转换为秒
            
            self.handle_events()
            self.update(dt)
            self.draw()
            
            pygame.display.flip()
        
        pygame.quit()

# 运行应用
if __name__ == "__main__":
    app = HyperdimensionalInspirationEngine()
    app.run()