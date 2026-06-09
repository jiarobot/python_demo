import pygame
import numpy as np
import cv2
import random
import time
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg
import threading
from queue import Queue
import matplotlib as mpl

mpl.rcParams['font.family'] = 'sans-serif'

mpl.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'SimSun', 'KaiTi', 'FangSong'] 
# 初始化pygame
pygame.init()
WIDTH, HEIGHT = 1200, 800
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("创新PX4无人机反制系统")
clock = pygame.time.Clock()

# 颜色定义
BACKGROUND = (10, 20, 30)
PANEL_BG = (25, 40, 60)
TEXT_COLOR = (220, 220, 255)
WARNING_COLOR = (255, 100, 100)
SAFE_COLOR = (100, 255, 150)
ACTIVE_COLOR = (70, 130, 255)
GRID_COLOR = (40, 70, 100)

# 字体
title_font = pygame.font.SysFont("simhei", 36)
header_font = pygame.font.SysFont("simhei", 28)
text_font = pygame.font.SysFont("simhei", 22)
small_font = pygame.font.SysFont("simhei", 18)

# 模拟无人机数据
class SimulatedDrone:
    def __init__(self, id):
        self.id = id
        self.position = np.array([random.uniform(-500, 500), random.uniform(-500, 500), random.uniform(50, 200)])
        self.velocity = np.array([random.uniform(-5, 5), random.uniform(-5, 5), random.uniform(-1, 1)])
        self.threat_level = random.uniform(0.1, 0.8)
        self.detected = False
        self.interfered = False
        self.color = (random.randint(150, 255), random.randint(150, 255), random.randint(150, 255))
        self.type = random.choice(["侦查型", "攻击型", "快递型", "未知型"])
        self.signal_strength = random.uniform(0.3, 0.9)
        self.last_update = time.time()
        
    def update(self):
        current_time = time.time()
        dt = current_time - self.last_update
        self.last_update = current_time
        
        # 随机移动
        self.velocity += np.array([random.uniform(-0.5, 0.5), random.uniform(-0.5, 0.5), random.uniform(-0.1, 0.1)])
        self.velocity = np.clip(self.velocity, [-10, -10, -2], [10, 10, 2])
        self.position += self.velocity * dt
        
        # 随机改变威胁等级
        self.threat_level += random.uniform(-0.05, 0.05)
        self.threat_level = np.clip(self.threat_level, 0.1, 0.95)
        
        # 随机改变信号强度
        self.signal_strength += random.uniform(-0.02, 0.02)
        self.signal_strength = np.clip(self.signal_strength, 0.1, 0.99)

# 反制系统类
class CounterDroneSystem:
    def __init__(self):
        self.drones = [SimulatedDrone(i) for i in range(8)]
        self.selected_drone = None
        self.system_active = True
        self.auto_mode = True
        self.interference_power = 75
        self.detection_range = 400
        self.interference_range = 300
        self.threat_threshold = 0.5
        self.alert_level = 0
        self.detection_history = []
        self.spectrum_data = np.zeros(100)
        self.last_spectrum_update = time.time()
        
    def update(self):
        # 更新所有无人机状态
        for drone in self.drones:
            drone.update()
            
        # 检测无人机
        self.detect_drones()
        
        # 自动反制逻辑
        if self.auto_mode:
            self.auto_counter_measure()
            
        # 更新频谱数据
        self.update_spectrum()
        
        # 更新检测历史
        if len(self.detection_history) > 100:
            self.detection_history.pop(0)
        self.detection_history.append(len([d for d in self.drones if d.detected]))
        
    def detect_drones(self):
        # 模拟检测逻辑
        for drone in self.drones:
            distance = np.linalg.norm(drone.position)
            detect_prob = 0.8 * (1 - distance / self.detection_range)
            drone.detected = random.random() < detect_prob and distance < self.detection_range
            
    def auto_counter_measure(self):
        # 自动反制威胁等级高的无人机
        for drone in self.drones:
            if drone.detected and drone.threat_level > self.threat_threshold:
                distance = np.linalg.norm(drone.position)
                if distance < self.interference_range:
                    drone.interfered = True
                else:
                    drone.interfered = False
            else:
                drone.interfered = False
                
    def update_spectrum(self):
        # 更新频谱图数据
        current_time = time.time()
        if current_time - self.last_spectrum_update > 0.1:
            self.last_spectrum_update = current_time
            # 随机生成频谱数据
            new_data = np.zeros(100)
            for drone in self.drones:
                if drone.detected:
                    # 每个检测到的无人机在频谱上产生一个峰
                    center = int(drone.id * 10 + 10)
                    width = 5 + int(drone.signal_strength * 10)
                    height = drone.signal_strength * 0.8
                    for i in range(max(0, center-width), min(100, center+width)):
                        dist = abs(i - center)
                        if dist < width:
                            value = height * (1 - dist/width)
                            new_data[i] += value
            
            # 添加一些随机噪声
            noise = np.random.normal(0, 0.05, 100)
            self.spectrum_data = np.clip(new_data + noise, 0, 1)
    
    def manual_counter_measure(self, drone_id):
        # 手动反制指定无人机
        if 0 <= drone_id < len(self.drones):
            drone = self.drones[drone_id]
            distance = np.linalg.norm(drone.position)
            if distance < self.interference_range:
                drone.interfered = True
                
    def release_counter_measure(self, drone_id):
        # 释放对指定无人机的反制
        if 0 <= drone_id < len(self.drones):
            drone = self.drones[drone_id]
            drone.interfered = False

# 创建系统实例
system = CounterDroneSystem()

# 绘制雷达图
def draw_radar(surface, x, y, radius):
    # 绘制雷达背景
    pygame.draw.circle(surface, (20, 40, 60), (x, y), radius, 0)
    pygame.draw.circle(surface, (30, 60, 90), (x, y), radius, 2)
    
    # 绘制同心圆
    for r in range(1, 4):
        pygame.draw.circle(surface, (40, 80, 120), (x, y), radius * r // 4, 1)
    
    # 绘制坐标轴
    pygame.draw.line(surface, (50, 100, 150), (x - radius, y), (x + radius, y), 1)
    pygame.draw.line(surface, (50, 100, 150), (x, y - radius), (x, y + radius), 1)
    
    # 绘制扫描线
    current_time = time.time()
    angle = (current_time * 50) % 360
    end_x = x + radius * np.cos(np.radians(angle))
    end_y = y - radius * np.sin(np.radians(angle))
    pygame.draw.line(surface, (100, 200, 100, 150), (x, y), (end_x, end_y), 2)
    
    # 绘制检测到的无人机
    for drone in system.drones:
        if drone.detected:
            # 将3D位置转换为2D雷达显示 (忽略高度)
            scale = 0.8 * radius / system.detection_range
            pos_x = x + drone.position[0] * scale
            pos_y = y + drone.position[1] * scale
            
            # 只显示在雷达范围内的无人机
            if np.linalg.norm([pos_x - x, pos_y - y]) <= radius:
                color = WARNING_COLOR if drone.threat_level > system.threat_threshold else SAFE_COLOR
                size = 6 + int(drone.threat_level * 10)
                pygame.draw.circle(surface, color, (int(pos_x), int(pos_y)), size)
                
                # 如果被干扰，绘制干扰效果
                if drone.interfered:
                    pygame.draw.circle(surface, (255, 50, 50, 150), (int(pos_x), int(pos_y)), size + 5, 2)
                    pygame.draw.circle(surface, (255, 50, 50, 100), (int(pos_x), int(pos_y)), size + 10, 1)
                    
                # 绘制无人机ID
                id_text = small_font.render(f"ID:{drone.id}", True, TEXT_COLOR)
                surface.blit(id_text, (int(pos_x) + 10, int(pos_y) - 10))

# 绘制频谱图
def draw_spectrum(surface, x, y, width, height):
    # 绘制背景
    pygame.draw.rect(surface, PANEL_BG, (x, y, width, height))
    pygame.draw.rect(surface, GRID_COLOR, (x, y, width, height), 1)
    
    # 绘制网格线
    for i in range(1, 5):
        pygame.draw.line(surface, GRID_COLOR, (x, y + i * height // 5), (x + width, y + i * height // 5), 1)
    
    # 绘制频谱
    bar_width = width / len(system.spectrum_data)
    for i, value in enumerate(system.spectrum_data):
        bar_height = value * height * 0.9
        color_value = int(100 + value * 155)
        color = (100, color_value, 255)
        pygame.draw.rect(surface, color, (x + i * bar_width, y + height - bar_height, max(1, bar_width - 1), bar_height))
    
    # 绘制标签
    title = header_font.render("射频频谱监测", True, TEXT_COLOR)
    surface.blit(title, (x + 10, y + 5))
    
    # 绘制频率标签
    for i in range(0, 11):
        freq = i * 2.4
        freq_text = small_font.render(f"{freq:.1f}GHz", True, TEXT_COLOR)
        surface.blit(freq_text, (x + i * width // 10, y + height - 20))

# 绘制系统状态面板
def draw_status_panel(surface, x, y, width, height):
    # 绘制面板背景
    pygame.draw.rect(surface, PANEL_BG, (x, y, width, height))
    pygame.draw.rect(surface, GRID_COLOR, (x, y, width, height), 2)
    
    # 标题
    title = header_font.render("系统状态", True, TEXT_COLOR)
    surface.blit(title, (x + 20, y + 15))
    
    # 系统状态
    status_color = SAFE_COLOR if system.alert_level < 0.5 else WARNING_COLOR
    status_text = text_font.render(f"警戒级别: {system.alert_level:.2f}", True, status_color)
    surface.blit(status_text, (x + 30, y + 60))
    
    # 检测到的无人机数量
    detected_count = len([d for d in system.drones if d.detected])
    detected_text = text_font.render(f"检测到目标: {detected_count}/{len(system.drones)}", True, TEXT_COLOR)
    surface.blit(detected_text, (x + 30, y + 90))
    
    # 被干扰的无人机数量
    interfered_count = len([d for d in system.drones if d.interfered])
    interfered_text = text_font.render(f"反制中目标: {interfered_count}", True, TEXT_COLOR)
    surface.blit(interfered_text, (x + 30, y + 120))
    
    # 系统模式
    mode_text = text_font.render(f"工作模式: {'自动' if system.auto_mode else '手动'}", True, TEXT_COLOR)
    surface.blit(mode_text, (x + 30, y + 150))
    
    # 干扰功率
    power_text = text_font.render(f"干扰功率: {system.interference_power}%", True, TEXT_COLOR)
    surface.blit(power_text, (x + 30, y + 180))
    
    # 威胁阈值
    threshold_text = text_font.render(f"威胁阈值: {system.threat_threshold:.2f}", True, TEXT_COLOR)
    surface.blit(threshold_text, (x + 30, y + 210))

# 绘制无人机详情面板
def draw_drone_details(surface, x, y, width, height, drone):
    # 绘制面板背景
    pygame.draw.rect(surface, PANEL_BG, (x, y, width, height))
    pygame.draw.rect(surface, GRID_COLOR, (x, y, width, height), 2)
    
    # 标题
    title = header_font.render(f"无人机详情 (ID: {drone.id})", True, drone.color)
    surface.blit(title, (x + 20, y + 15))
    
    # 无人机类型
    type_text = text_font.render(f"类型: {drone.type}", True, TEXT_COLOR)
    surface.blit(type_text, (x + 30, y + 60))
    
    # 威胁等级
    threat_color = WARNING_COLOR if drone.threat_level > system.threat_threshold else SAFE_COLOR
    threat_text = text_font.render(f"威胁等级: {drone.threat_level:.2f}", True, threat_color)
    surface.blit(threat_text, (x + 30, y + 90))
    
    # 信号强度
    signal_text = text_font.render(f"信号强度: {drone.signal_strength:.2f}", True, TEXT_COLOR)
    surface.blit(signal_text, (x + 30, y + 120))
    
    # 距离
    distance = np.linalg.norm(drone.position)
    distance_text = text_font.render(f"距离: {distance:.1f}米", True, TEXT_COLOR)
    surface.blit(distance_text, (x + 30, y + 150))
    
    # 位置
    pos_text = text_font.render(f"位置: ({drone.position[0]:.1f}, {drone.position[1]:.1f}, {drone.position[2]:.1f})", True, TEXT_COLOR)
    surface.blit(pos_text, (x + 30, y + 180))
    
    # 状态
    status = "已检测" if drone.detected else "未检测"
    status_color = (100, 255, 100) if drone.detected else (200, 200, 200)
    status_text = text_font.render(f"状态: {status}", True, status_color)
    surface.blit(status_text, (x + 30, y + 210))
    
    # 反制状态
    counter_status = "反制中" if drone.interfered else "未反制"
    counter_color = (255, 100, 100) if drone.interfered else (200, 200, 200)
    counter_text = text_font.render(f"反制状态: {counter_status}", True, counter_color)
    surface.blit(counter_text, (x + 30, y + 240))
    
    # 威胁指示器
    pygame.draw.rect(surface, (50, 60, 80), (x + 30, y + 280, 200, 20))
    pygame.draw.rect(surface, threat_color, (x + 30, y + 280, int(200 * drone.threat_level), 20))
    pygame.draw.rect(surface, GRID_COLOR, (x + 30, y + 280, 200, 20), 1)

# 绘制控制面板
def draw_control_panel(surface, x, y, width, height):
    # 绘制面板背景
    pygame.draw.rect(surface, PANEL_BG, (x, y, width, height))
    pygame.draw.rect(surface, GRID_COLOR, (x, y, width, height), 2)
    
    # 标题
    title = header_font.render("控制面板", True, TEXT_COLOR)
    surface.blit(title, (x + 20, y + 15))
    
    # 绘制按钮
    buttons = [
        {"rect": pygame.Rect(x + 30, y + 60, 160, 40), "text": "启动系统", "action": "start"},
        {"rect": pygame.Rect(x + 30, y + 110, 160, 40), "text": "关闭系统", "action": "stop"},
        {"rect": pygame.Rect(x + 30, y + 160, 160, 40), "text": "自动模式", "action": "auto"},
        {"rect": pygame.Rect(x + 30, y + 210, 160, 40), "text": "手动模式", "action": "manual"},
        {"rect": pygame.Rect(x + 30, y + 280, 160, 40), "text": "紧急干扰", "action": "emergency"},
    ]
    
    for button in buttons:
        color = ACTIVE_COLOR if system.system_active else (100, 100, 150)
        pygame.draw.rect(surface, color, button["rect"], 0, 5)
        pygame.draw.rect(surface, GRID_COLOR, button["rect"], 2, 5)
        text = text_font.render(button["text"], True, TEXT_COLOR)
        text_rect = text.get_rect(center=button["rect"].center)
        surface.blit(text, text_rect)
    
    return buttons

# 绘制检测历史图表
def draw_history_chart(surface, x, y, width, height):
    # 创建matplotlib图表
    fig = plt.figure(figsize=(width/100, height/100), dpi=100)
    ax = fig.add_subplot(111)
    
    # 绘制数据
    if len(system.detection_history) > 0:
        ax.plot(system.detection_history, color='cyan', linewidth=2)
        ax.fill_between(range(len(system.detection_history)), 
                        system.detection_history, color='cyan', alpha=0.2)
    
    # 设置图表样式
    ax.set_facecolor((0.1, 0.15, 0.2))
    fig.patch.set_facecolor((0.1, 0.15, 0.2))
    ax.spines['bottom'].set_color('white')
    ax.spines['top'].set_color('white') 
    ax.spines['right'].set_color('white')
    ax.spines['left'].set_color('white')
    ax.tick_params(axis='x', colors='white')
    ax.tick_params(axis='y', colors='white')
    ax.set_title('目标检测历史', color='white', fontsize=12)
    ax.set_ylim(0, len(system.drones) + 1)
    
    # 渲染到Surface
    canvas = FigureCanvasAgg(fig)
    canvas.draw()
    renderer = canvas.get_renderer()
    raw_data = renderer.tostring_rgb()
    
    # 转换为pygame图像
    img = pygame.image.fromstring(raw_data, canvas.get_width_height(), "RGB")
    surface.blit(img, (x, y))
    
    plt.close(fig)

# 主循环
running = True
last_update = time.time()
control_buttons = []

while running:
    current_time = time.time()
    dt = current_time - last_update
    last_update = current_time
    
    # 处理事件
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = pygame.mouse.get_pos()
            # 检查控制按钮点击
            for button in control_buttons:
                if button["rect"].collidepoint(mouse_pos):
                    if button["action"] == "start":
                        system.system_active = True
                    elif button["action"] == "stop":
                        system.system_active = False
                    elif button["action"] == "auto":
                        system.auto_mode = True
                    elif button["action"] == "manual":
                        system.auto_mode = False
                    elif button["action"] == "emergency":
                        # 紧急干扰所有检测到的无人机
                        for drone in system.drones:
                            if drone.detected:
                                drone.interfered = True
    
    # 更新系统
    if system.system_active:
        system.update()
    
    # 计算警报级别（基于检测到的威胁无人机数量）
    threat_drones = [d for d in system.drones if d.detected and d.threat_level > system.threat_threshold]
    system.alert_level = min(1.0, len(threat_drones) * 0.2)
    
    # 绘制界面
    screen.fill(BACKGROUND)
    
    # 绘制标题
    title = title_font.render("创新PX4无人机反制系统", True, TEXT_COLOR)
    screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 20))
    
    # 绘制时间
    time_text = text_font.render(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), True, TEXT_COLOR)
    screen.blit(time_text, (WIDTH - time_text.get_width() - 20, 25))
    
    # 绘制雷达
    draw_radar(screen, 300, 300, 250)
    
    # 绘制频谱
    draw_spectrum(screen, 600, 100, 550, 150)
    
    # 绘制状态面板
    draw_status_panel(screen, 50, 100, 220, 250)
    
    # 绘制控制面板
    control_buttons = draw_control_panel(screen, 50, 380, 220, 350)
    
    # 绘制历史图表
    draw_history_chart(screen, 600, 280, 550, 200)
    
    # 绘制无人机详情
    if system.selected_drone is not None:
        draw_drone_details(screen, 300, 570, 250, 350, system.drones[system.selected_drone])
    
    # 绘制无人机列表
    drone_list_rect = pygame.Rect(600, 500, 550, 280)
    pygame.draw.rect(screen, PANEL_BG, drone_list_rect)
    pygame.draw.rect(screen, GRID_COLOR, drone_list_rect, 2)
    
    list_title = header_font.render("检测到的无人机列表", True, TEXT_COLOR)
    screen.blit(list_title, (610, 510))
    
    # 列标题
    pygame.draw.line(screen, GRID_COLOR, (610, 550), (1130, 550), 2)
    headers = ["ID", "类型", "距离", "威胁等级", "状态", "操作"]
    for i, header in enumerate(headers):
        header_text = text_font.render(header, True, ACTIVE_COLOR)
        screen.blit(header_text, (620 + i * 180 if i > 3 else 610 + i * 120, 520))
    
    # 无人机列表
    detected_drones = [d for d in system.drones if d.detected]
    for i, drone in enumerate(detected_drones[:4]):  # 最多显示4个
        y_pos = 570 + i * 60
        
        # 绘制行背景
        if i % 2 == 0:
            pygame.draw.rect(screen, (35, 55, 80), (610, y_pos - 10, 520, 50))
        
        # ID
        id_text = text_font.render(str(drone.id), True, drone.color)
        screen.blit(id_text, (620, y_pos))
        
        # 类型
        type_text = text_font.render(drone.type, True, TEXT_COLOR)
        screen.blit(type_text, (700, y_pos))
        
        # 距离
        distance = np.linalg.norm(drone.position)
        dist_text = text_font.render(f"{distance:.1f}米", True, TEXT_COLOR)
        screen.blit(dist_text, (820, y_pos))
        
        # 威胁等级
        threat_color = WARNING_COLOR if drone.threat_level > system.threat_threshold else SAFE_COLOR
        threat_text = text_font.render(f"{drone.threat_level:.2f}", True, threat_color)
        screen.blit(threat_text, (930, y_pos))
        
        # 状态
        status_text = text_font.render("反制中" if drone.interfered else "已检测", True, 
                                     (255, 100, 100) if drone.interfered else (100, 255, 150))
        screen.blit(status_text, (1020, y_pos))
        
        # 操作按钮
        if not system.auto_mode:
            if not drone.interfered:
                button_rect = pygame.Rect(1120, y_pos - 5, 80, 30)
                pygame.draw.rect(screen, (100, 200, 100), button_rect, 0, 5)
                pygame.draw.rect(screen, GRID_COLOR, button_rect, 2, 5)
                btn_text = small_font.render("干扰", True, (0, 0, 0))
                screen.blit(btn_text, (button_rect.centerx - btn_text.get_width()//2, 
                                     button_rect.centery - btn_text.get_height()//2))
            else:
                button_rect = pygame.Rect(1120, y_pos - 5, 80, 30)
                pygame.draw.rect(screen, (200, 100, 100), button_rect, 0, 5)
                pygame.draw.rect(screen, GRID_COLOR, button_rect, 2, 5)
                btn_text = small_font.render("释放", True, (0, 0, 0))
                screen.blit(btn_text, (button_rect.centerx - btn_text.get_width()//2, 
                                     button_rect.centery - btn_text.get_height()//2))
    
    # 更新屏幕
    pygame.display.flip()
    clock.tick(30)

pygame.quit()