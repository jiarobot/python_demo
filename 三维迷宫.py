import pygame
import numpy as np
import random
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import sys
import math
from collections import deque
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg

# 初始化pygame和OpenGL
pygame.init()
WIDTH, HEIGHT = 1200, 800
screen = pygame.display.set_mode((WIDTH, HEIGHT), DOUBLEBUF | OPENGL)
pygame.display.set_caption("三维自学习迷宫探索系统 - 强化学习智能体")
clock = pygame.time.Clock()

# OpenGL设置
glEnable(GL_DEPTH_TEST)
glEnable(GL_LIGHTING)
glEnable(GL_LIGHT0)
glEnable(GL_COLOR_MATERIAL)
glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)

# 常量定义
MAZE_SIZE = 8  # 迷宫尺寸 (x, y, z)
CELL_SIZE = 2.0
AGENT_SIZE = 0.5
FPS = 60

# 颜色定义
BACKGROUND = (0.05, 0.05, 0.1, 1.0)
WALL_COLOR = (0.5, 0.2, 0.7, 1.0)
PATH_COLOR = (0.2, 0.6, 0.4, 0.3)
START_COLOR = (0.0, 0.8, 0.0, 1.0)
END_COLOR = (0.9, 0.1, 0.1, 1.0)
AGENT_COLOR = (0.2, 0.7, 1.0, 1.0)
TEXT_COLOR = (0.9, 0.9, 1.0, 1.0)
BUTTON_COLOR = (0.2, 0.4, 0.8, 1.0)
BUTTON_HOVER = (0.3, 0.5, 0.9, 1.0)
PANEL_COLOR = (0.1, 0.1, 0.2, 0.8)

# 字体
font = pygame.font.SysFont('microsoftyahei', 18)
title_font = pygame.font.SysFont('microsoftyahei', 32, bold=True)

class NeuralNetwork:
    """简单的多层感知器神经网络"""
    def __init__(self, input_size, hidden_size, output_size, lr=0.01):
        self.weights1 = np.random.randn(input_size, hidden_size) * 0.1
        self.weights2 = np.random.randn(hidden_size, output_size) * 0.1
        self.lr = lr
        
    def forward(self, x):
        self.hidden = np.tanh(np.dot(x, self.weights1))
        return np.dot(self.hidden, self.weights2)
    
    def backward(self, x, y, output):
        # 简单反向传播
        error = y - output
        d_weights2 = np.dot(self.hidden.T, error)
        d_hidden = np.dot(error, self.weights2.T) * (1 - np.power(self.hidden, 2))
        d_weights1 = np.dot(x.T, d_hidden)
        
        self.weights1 += self.lr * d_weights1
        self.weights2 += self.lr * d_weights2

class MazeEnvironment3D:
    """三维迷宫环境"""
    def __init__(self, size):
        self.size = size
        self.grid = np.zeros((size, size, size))  # 0表示可通行
        self.start_pos = (1, 1, 1)
        self.end_pos = (size-2, size-2, size-2)
        self.dynamic_obstacles = []
        self._generate_maze()
        
    def _generate_maze(self):
        # 创建边界
        self.grid[0, :, :] = 1
        self.grid[-1, :, :] = 1
        self.grid[:, 0, :] = 1
        self.grid[:, -1, :] = 1
        self.grid[:, :, 0] = 1
        self.grid[:, :, -1] = 1
        
        # 添加随机障碍物
        for _ in range(int(self.size ** 3 * 0.15)):
            x, y, z = random.randint(1, self.size-2), random.randint(1, self.size-2), random.randint(1, self.size-2)
            self.grid[x, y, z] = 1
        
        # 确保起点和终点是开放的
        self.grid[self.start_pos] = 0
        self.grid[self.end_pos] = 0
        
        # 添加动态障碍物
        for _ in range(5):
            x, y, z = random.randint(1, self.size-2), random.randint(1, self.size-2), random.randint(1, self.size-2)
            if (x, y, z) != self.start_pos and (x, y, z) != self.end_pos:
                self.dynamic_obstacles.append((x, y, z))
                self.grid[x, y, z] = 2  # 2表示动态障碍物
    
    def reset(self):
        # 重置动态障碍物
        for x, y, z in self.dynamic_obstacles:
            self.grid[x, y, z] = 2
        return self.start_pos
    
    def step(self, state, action):
        x, y, z = state
        
        # 动作: 0=上, 1=右, 2=下, 3=左, 4=前, 5=后
        if action == 0: y += 1
        elif action == 1: x += 1
        elif action == 2: y -= 1
        elif action == 3: x -= 1
        elif action == 4: z += 1
        elif action == 5: z -= 1
        
        # 边界检查
        if x < 0 or x >= self.size or y < 0 or y >= self.size or z < 0 or z >= self.size:
            return state, -10, False  # 碰到边界，惩罚
        
        # 障碍物检查
        if self.grid[x, y, z] == 1 or self.grid[x, y, z] == 2:
            return state, -10, False  # 碰到障碍物，惩罚
        
        # 到达终点
        if (x, y, z) == self.end_pos:
            return (x, y, z), 100, True
        
        # 普通移动
        return (x, y, z), -0.1, False
    
    def update_dynamic_obstacles(self):
        # 随机移动动态障碍物
        for i, (x, y, z) in enumerate(self.dynamic_obstacles):
            # 清除当前位置
            self.grid[x, y, z] = 0
            
            # 随机选择新位置
            dx, dy, dz = random.choice([(1,0,0), (-1,0,0), (0,1,0), (0,-1,0), (0,0,1), (0,0,-1)])
            new_x, new_y, new_z = x + dx, y + dy, z + dz
            
            # 确保新位置在边界内且不是起点或终点
            if (0 < new_x < self.size-1 and 0 < new_y < self.size-1 and 0 < new_z < self.size-1 and
                (new_x, new_y, new_z) != self.start_pos and (new_x, new_y, new_z) != self.end_pos and
                self.grid[new_x, new_y, new_z] == 0):
                x, y, z = new_x, new_y, new_z
            
            # 更新障碍物位置
            self.dynamic_obstacles[i] = (x, y, z)
            self.grid[x, y, z] = 2

class QLearningAgent3D:
    """使用神经网络的Q-learning智能体"""
    def __init__(self, env, learning_rate=0.01, discount_factor=0.95, exploration_rate=1.0, 
                 exploration_decay=0.995, min_exploration=0.01):
        self.env = env
        self.lr = learning_rate
        self.gamma = discount_factor
        self.epsilon = exploration_rate
        self.epsilon_decay = exploration_decay
        self.min_epsilon = min_exploration
        
        # 使用神经网络替代Q表
        self.nn = NeuralNetwork(6, 64, 6, lr=learning_rate)  # 6个状态特征，6个动作
        
        # 经验回放缓冲区
        self.memory = deque(maxlen=10000)
        self.batch_size = 32
        
        # 训练统计
        self.episode_rewards = []
        self.episode_steps = []
        self.success_rate = []
        self.success_count = 0
        
    def get_state_features(self, state):
        x, y, z = state
        # 状态特征：当前位置 + 终点方向
        ex, ey, ez = self.env.end_pos
        return np.array([x/self.env.size, y/self.env.size, z/self.env.size, 
                        (ex-x)/self.env.size, (ey-y)/self.env.size, (ez-z)/self.env.size])
    
    def choose_action(self, state):
        # ε-贪婪策略
        if random.random() < self.epsilon:
            return random.randint(0, 5)  # 随机探索
        else:
            state_features = self.get_state_features(state)
            q_values = self.nn.forward(state_features)
            return np.argmax(q_values)  # 选择最优动作
    
    def remember(self, state, action, reward, next_state, done):
        self.memory.append((state, action, reward, next_state, done))
    
    def replay(self):
        if len(self.memory) < self.batch_size:
            return
        
        batch = random.sample(self.memory, self.batch_size)
        for state, action, reward, next_state, done in batch:
            state_features = self.get_state_features(state)
            next_state_features = self.get_state_features(next_state)
            
            q_values = self.nn.forward(state_features)
            next_q_values = self.nn.forward(next_state_features)
            
            target = reward
            if not done:
                target = reward + self.gamma * np.max(next_q_values)
            
            q_target = q_values.copy()
            q_target[action] = target
            
            # 训练神经网络
            self.nn.backward(state_features, q_target, q_values)
    
    def train(self, episodes=500):
        self.episode_rewards = []
        self.episode_steps = []
        self.success_rate = []
        self.success_count = 0
        
        for episode in range(episodes):
            state = self.env.reset()
            total_reward = 0
            steps = 0
            done = False
            
            while not done and steps < 1000:  # 防止无限循环
                action = self.choose_action(state)
                next_state, reward, done = self.env.step(state, action)
                
                self.remember(state, action, reward, next_state, done)
                
                state = next_state
                total_reward += reward
                steps += 1
                
                if done:
                    self.success_count += 1
                
                # 定期更新动态障碍物
                if steps % 20 == 0:
                    self.env.update_dynamic_obstacles()
            
            # 经验回放
            self.replay()
            
            # 更新探索率
            self.epsilon = max(self.min_epsilon, self.epsilon * self.epsilon_decay)
            
            # 记录统计数据
            self.episode_rewards.append(total_reward)
            self.episode_steps.append(steps)
            self.success_rate.append(self.success_count / (episode + 1))
            
            # 每50轮打印一次进度
            if (episode + 1) % 50 == 0:
                print(f"Episode {episode+1}/{episodes}: Reward={total_reward:.1f}, Steps={steps}, Success Rate={self.success_rate[-1]*100:.1f}%")
    
    def get_optimal_path(self):
        path = []
        state = self.env.reset()
        done = False
        
        while not done:
            path.append(state)
            action = self.choose_action(state)
            state, _, done = self.env.step(state, action)
        
        path.append(state)  # 添加终点
        return path

class Camera:
    """3D相机类"""
    def __init__(self):
        self.rotation_x = -30
        self.rotation_y = 45
        self.distance = 20
        self.fov = 60
        self.mode = "third_person"  # "first_person" 或 "third_person"
        self.position = [0, 0, 0]
    
    def apply(self):
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(self.fov, WIDTH/HEIGHT, 0.1, 100.0)
        
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        
        if self.mode == "third_person":
            # 第三人称视角
            glTranslatef(0, 0, -self.distance)
            glRotatef(self.rotation_x, 1, 0, 0)
            glRotatef(self.rotation_y, 0, 1, 0)
            glTranslatef(-MAZE_SIZE*CELL_SIZE/2, -MAZE_SIZE*CELL_SIZE/2, -MAZE_SIZE*CELL_SIZE/2)
        else:
            # 第一人称视角
            gluLookAt(
                self.position[0], self.position[1], self.position[2] + 1,  # 眼睛位置
                self.position[0], self.position[1], self.position[2],      # 看向的点
                0, 1, 0                                                   # 上方向
            )
    
    def set_first_person(self, position):
        self.mode = "first_person"
        self.position = [position[0]*CELL_SIZE, position[1]*CELL_SIZE, position[2]*CELL_SIZE]
    
    def set_third_person(self):
        self.mode = "third_person"

class Button:
    def __init__(self, x, y, width, height, text, action=None):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.action = action
        self.hovered = False
        
    def draw(self, surface):
        color = BUTTON_HOVER if self.hovered else BUTTON_COLOR
        pygame.draw.rect(surface, color, self.rect, border_radius=8)
        pygame.draw.rect(surface, (150, 180, 250), self.rect, 2, border_radius=8)
        
        text_surf = font.render(self.text, True, TEXT_COLOR)
        text_rect = text_surf.get_rect(center=self.rect.center)
        surface.blit(text_surf, text_rect)
        
    def check_hover(self, pos):
        self.hovered = self.rect.collidepoint(pos)
        
    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.hovered and self.action:
                self.action()
                return True
        return False

def draw_cube(x, y, z, size, color):
    """绘制立方体"""
    vertices = [
        [x, y, z],
        [x+size, y, z],
        [x+size, y+size, z],
        [x, y+size, z],
        [x, y, z+size],
        [x+size, y, z+size],
        [x+size, y+size, z+size],
        [x, y+size, z+size]
    ]
    
    edges = [
        [0, 1], [1, 2], [2, 3], [3, 0],
        [4, 5], [5, 6], [6, 7], [7, 4],
        [0, 4], [1, 5], [2, 6], [3, 7]
    ]
    
    faces = [
        [0, 1, 2, 3],  # 前
        [4, 5, 6, 7],  # 后
        [0, 1, 5, 4],  # 下
        [2, 3, 7, 6],  # 上
        [0, 3, 7, 4],  # 左
        [1, 2, 6, 5]   # 右
    ]
    
    glColor4f(*color)
    
    # 绘制面
    glBegin(GL_QUADS)
    for face in faces:
        for vertex in face:
            glVertex3fv(vertices[vertex])
    glEnd()
    
    # 绘制边线
    glColor4f(color[0]*0.7, color[1]*0.7, color[2]*0.7, color[3])
    glBegin(GL_LINES)
    for edge in edges:
        for vertex in edge:
            glVertex3fv(vertices[vertex])
    glEnd()

def draw_sphere(x, y, z, radius, color):
    """绘制球体"""
    glColor4f(*color)
    glPushMatrix()
    glTranslatef(x, y, z)
    quad = gluNewQuadric()
    gluSphere(quad, radius, 16, 16)
    gluDeleteQuadric(quad)
    glPopMatrix()

def draw_maze(env, agent_pos, path):
    """绘制迷宫"""
    # 绘制路径
    if path:
        glColor4f(1.0, 1.0, 0.3, 0.5)
        glBegin(GL_LINE_STRIP)
        for x, y, z in path:
            glVertex3f(x*CELL_SIZE + CELL_SIZE/2, y*CELL_SIZE + CELL_SIZE/2, z*CELL_SIZE + CELL_SIZE/2)
        glEnd()
    
    # 绘制迷宫单元格
    for x in range(env.size):
        for y in range(env.size):
            for z in range(env.size):
                if env.grid[x, y, z] == 1:  # 静态障碍物
                    draw_cube(x*CELL_SIZE, y*CELL_SIZE, z*CELL_SIZE, CELL_SIZE, WALL_COLOR)
                elif env.grid[x, y, z] == 2:  # 动态障碍物
                    draw_cube(x*CELL_SIZE, y*CELL_SIZE, z*CELL_SIZE, CELL_SIZE, (0.8, 0.4, 0.1, 1.0))
    
    # 绘制起点和终点
    sx, sy, sz = env.start_pos
    draw_sphere(sx*CELL_SIZE + CELL_SIZE/2, sy*CELL_SIZE + CELL_SIZE/2, sz*CELL_SIZE + CELL_SIZE/2, 
                CELL_SIZE/3, START_COLOR)
    
    ex, ey, ez = env.end_pos
    draw_sphere(ex*CELL_SIZE + CELL_SIZE/2, ey*CELL_SIZE + CELL_SIZE/2, ez*CELL_SIZE + CELL_SIZE/2, 
                CELL_SIZE/3, END_COLOR)
    
    # 绘制智能体
    ax, ay, az = agent_pos
    draw_sphere(ax*CELL_SIZE + CELL_SIZE/2, ay*CELL_SIZE + CELL_SIZE/2, az*CELL_SIZE + CELL_SIZE/2, 
                AGENT_SIZE, AGENT_COLOR)

def create_statistics_plot(agent):
    """创建统计图表"""
    fig, ax = plt.subplots(3, 1, figsize=(8, 6), dpi=80)
    fig.set_facecolor('#1a1a2e')
    
    # 奖励曲线
    ax[0].plot(agent.episode_rewards, color='cyan', linewidth=1.5)
    ax[0].set_title('每轮奖励', color='white', fontsize=10)
    ax[0].set_facecolor('#1a1a2e')
    ax[0].tick_params(colors='white', labelsize=8)
    
    # 步数曲线
    ax[1].plot(agent.episode_steps, color='magenta', linewidth=1.5)
    ax[1].set_title('每轮步数', color='white', fontsize=10)
    ax[1].set_facecolor('#1a1a2e')
    ax[1].tick_params(colors='white', labelsize=8)
    
    # 成功率曲线
    ax[2].plot(agent.success_rate, color='yellow', linewidth=1.5)
    ax[2].set_title('成功率', color='white', fontsize=10)
    ax[2].set_facecolor('#1a1a2e')
    ax[2].tick_params(colors='white', labelsize=8)
    
    fig.tight_layout(pad=2.0)
    
    # 将matplotlib图形转换为pygame surface
    canvas = FigureCanvasAgg(fig)
    canvas.draw()
    renderer = canvas.get_renderer()
    raw_data = renderer.tostring_rgb()
    size = canvas.get_width_height()
    
    return pygame.image.fromstring(raw_data, size, "RGB")

# 创建环境和智能体
env = MazeEnvironment3D(MAZE_SIZE)
agent = QLearningAgent3D(env)
camera = Camera()

# 训练状态
training = False
current_episode = 0
episodes_to_train = 500
optimal_path = []
show_path = False
agent_position = env.start_pos

# 创建按钮
def start_training():
    global training, current_episode, optimal_path, show_path
    training = True
    current_episode = 0
    optimal_path = []
    show_path = False
    agent.train(episodes_to_train)
    training = False

def show_optimal_path():
    global optimal_path, show_path, agent_position
    optimal_path = agent.get_optimal_path()
    show_path = True
    agent_position = env.start_pos

def reset_environment():
    global env, agent, training, current_episode, optimal_path, show_path, agent_position
    env = MazeEnvironment3D(MAZE_SIZE)
    agent = QLearningAgent3D(env)
    training = False
    current_episode = 0
    optimal_path = []
    show_path = False
    agent_position = env.start_pos

def toggle_camera_mode():
    if camera.mode == "third_person":
        camera.set_first_person(agent_position)
    else:
        camera.set_third_person()

buttons = [
    Button(WIDTH - 200, 20, 180, 40, "开始训练", start_training),
    Button(WIDTH - 200, 70, 180, 40, "显示最优路径", show_optimal_path),
    Button(WIDTH - 200, 120, 180, 40, "重置环境", reset_environment),
    Button(WIDTH - 200, 170, 180, 40, "切换视角", toggle_camera_mode),
]

# 主循环
running = True
mouse_dragging = False
last_mouse_pos = (0, 0)
last_update_time = pygame.time.get_ticks()

while running:
    current_time = pygame.time.get_ticks()
    delta_time = (current_time - last_update_time) / 1000.0
    last_update_time = current_time
    
    # 事件处理
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # 左键
                mouse_dragging = True
                last_mouse_pos = pygame.mouse.get_pos()
            elif event.button == 4:  # 滚轮上
                camera.distance = max(5, camera.distance - 1)
            elif event.button == 5:  # 滚轮下
                camera.distance = min(50, camera.distance + 1)
        
        if event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:  # 左键
                mouse_dragging = False
        
        if event.type == pygame.MOUSEMOTION and mouse_dragging and camera.mode == "third_person":
            x, y = event.pos
            dx = x - last_mouse_pos[0]
            dy = y - last_mouse_pos[1]
            camera.rotation_y += dx * 0.5
            camera.rotation_x -= dy * 0.5
            camera.rotation_x = max(-90, min(90, camera.rotation_x))
            last_mouse_pos = (x, y)
        
        if event.type == pygame.KEYDOWN:
            if camera.mode == "first_person":
                # 第一人称移动
                x, y, z = agent_position
                if event.key == pygame.K_w:  # 前
                    agent_position = (x, y+1, z)
                elif event.key == pygame.K_s:  # 后
                    agent_position = (x, y-1, z)
                elif event.key == pygame.K_a:  # 左
                    agent_position = (x-1, y, z)
                elif event.key == pygame.K_d:  # 右
                    agent_position = (x+1, y, z)
                elif event.key == pygame.K_q:  # 上
                    agent_position = (x, y, z+1)
                elif event.key == pygame.K_e:  # 下
                    agent_position = (x, y, z-1)
                
                # 边界和障碍物检查
                if (agent_position[0] < 0 or agent_position[0] >= env.size or
                    agent_position[1] < 0 or agent_position[1] >= env.size or
                    agent_position[2] < 0 or agent_position[2] >= env.size or
                    env.grid[agent_position] == 1 or env.grid[agent_position] == 2):
                    agent_position = (x, y, z)  # 恢复位置
                else:
                    camera.set_first_person(agent_position)
        
        mouse_pos = pygame.mouse.get_pos()
        for button in buttons:
            button.check_hover(mouse_pos)
            button.handle_event(event)
    
    # 清除屏幕
    glClearColor(*BACKGROUND)
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    
    # 应用相机变换
    camera.apply()
    
    # 设置光源
    glLightfv(GL_LIGHT0, GL_POSITION, [10, 10, 10, 1])
    glLightfv(GL_LIGHT0, GL_DIFFUSE, [1, 1, 1, 1])
    glLightfv(GL_LIGHT0, GL_AMBIENT, [0.3, 0.3, 0.3, 1])
    
    # 绘制迷宫
    draw_maze(env, agent_position, optimal_path if show_path else [])
    
    # 切换到2D模式绘制UI
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, WIDTH, HEIGHT, 0)
    
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    glDisable(GL_DEPTH_TEST)
    glDisable(GL_LIGHTING)
    
    # 绘制UI
    screen_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    
    # 绘制标题
    title = title_font.render("三维自学习迷宫探索系统", True, (100, 200, 255))
    screen_surface.blit(title, (WIDTH // 2 - title.get_width() // 2, 10))
    
    # 绘制信息面板
    pygame.draw.rect(screen_surface, PANEL_COLOR, (WIDTH - 220, 180, 200, 250), border_radius=10)
    pygame.draw.rect(screen_surface, (80, 100, 150), (WIDTH - 220, 180, 200, 250), 2, border_radius=10)
    
    # 显示训练信息
    info_y = 200
    lines = [
        f"训练轮数: {current_episode}/{episodes_to_train}",
        f"探索率: {agent.epsilon:.3f}",
        f"成功率: {agent.success_rate[-1]*100 if agent.success_rate else 0:.1f}%",
        f"学习率: {agent.lr}",
        f"折扣因子: {agent.gamma}",
        f"当前奖励: {agent.episode_rewards[-1] if agent.episode_rewards else 0:.1f}",
        f"视角模式: {camera.mode}",
        f"智能体位置: {agent_position}"
    ]
    
    for line in lines:
        text = font.render(line, True, TEXT_COLOR)
        screen_surface.blit(text, (WIDTH - 200, info_y))
        info_y += 30
    
    # 绘制按钮
    for button in buttons:
        button.draw(screen_surface)
    
    # 绘制学习曲线
    if agent.episode_rewards:
        plot_surface = create_statistics_plot(agent)
        screen_surface.blit(plot_surface, (50, HEIGHT - 300))
    
    # 状态说明
    pygame.draw.rect(screen_surface, PANEL_COLOR, (50, HEIGHT - 80, WIDTH - 100, 60), border_radius=10)
    pygame.draw.rect(screen_surface, (80, 100, 150), (50, HEIGHT - 80, WIDTH - 100, 60), 2, border_radius=10)
    instructions = [
        "系统说明: 基于神经网络Q-learning的三维迷宫探索系统，支持动态障碍物和视角切换",
        "绿色:起点  红色:终点  紫色:静态障碍物  橙色:动态障碍物  黄色:学习到的最优路径"
    ]
    
    for i, text in enumerate(instructions):
        text_surf = font.render(text, True, TEXT_COLOR)
        screen_surface.blit(text_surf, (70, HEIGHT - 60 + i * 25))
    
    # 将UI绘制到OpenGL窗口
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    
    glRasterPos2f(-1, 1)
    glPixelZoom(1, -1)
    
    data = pygame.image.tostring(screen_surface, "RGBA", True)
    glDrawPixels(WIDTH, HEIGHT, GL_RGBA, GL_UNSIGNED_BYTE, data)
    
    glDisable(GL_BLEND)
    
    # 恢复3D模式
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_LIGHTING)
    
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)
    glPopMatrix()
    
    # 更新屏幕
    pygame.display.flip()
    clock.tick(FPS)

pygame.quit()
sys.exit()