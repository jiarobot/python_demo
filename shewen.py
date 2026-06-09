import pygame
import numpy as np
import math
import random
from pygame import gfxdraw

# 初始化pygame
pygame.init()
WIDTH, HEIGHT = 1000, 700
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("舌吻交互式生物反馈可视化系统")

# 颜色定义
BACKGROUND = (10, 10, 20)
MOUTH_COLOR = (180, 70, 70)
TONGUE_COLOR = (255, 150, 150)
HIGHLIGHT_COLOR = (255, 200, 200)
HEART_COLOR = (255, 50, 50)
TEXT_COLOR = (220, 220, 255)
UI_COLOR = (70, 130, 180)

# 字体
font_large = pygame.font.SysFont("simhei", 36)
font_medium = pygame.font.SysFont("simhei", 24)
font_small = pygame.font.SysFont("simhei", 18)

class KissSimulation:
    def __init__(self):
        self.intensity = 0.0  # 吻的强度 (0-1)
        self.duration = 0.0   # 吻的持续时间 (秒)
        self.heart_rate = 70  # 心率 (bpm)
        self.saliva = 0.5     # 唾液分泌量 (0-1)
        self.tongue_movement = 0.0  # 舌头运动频率
        self.sensitivity = 0.5  # 敏感度
        
        # 生物传感器数据
        self.heart_rate_data = []
        self.saliva_data = []
        self.movement_data = []
        
        # 粒子系统
        self.particles = []
        
        # 时间跟踪
        self.time_elapsed = 0
        
    def update(self, dt, intensity_input=None):
        self.time_elapsed += dt
        
        # 更新吻的强度
        if intensity_input is not None:
            self.intensity = max(0, min(1, self.intensity + intensity_input * 0.1))
        else:
            # 随时间自然衰减
            self.intensity = max(0, self.intensity - 0.01)
        
        # 更新持续时间
        if self.intensity > 0.1:
            self.duration += dt
        
        # 模拟生理反应
        self.heart_rate = 70 + int(40 * self.intensity * (0.8 + 0.2 * math.sin(self.time_elapsed)))
        self.saliva = max(0, min(1, 0.3 + 0.7 * self.intensity * (0.9 + 0.1 * math.sin(self.time_elapsed * 2))))
        self.tongue_movement = self.intensity * (0.8 + 0.2 * math.sin(self.time_elapsed * 3))
        
        # 记录数据
        if len(self.heart_rate_data) > 200:
            self.heart_rate_data.pop(0)
            self.saliva_data.pop(0)
            self.movement_data.pop(0)
        
        self.heart_rate_data.append(self.heart_rate)
        self.saliva_data.append(self.saliva)
        self.movement_data.append(self.tongue_movement)
        
        # 更新粒子系统
        if random.random() < self.intensity * 0.3:
            self.add_particle()
            
        for particle in self.particles[:]:
            particle[0] += particle[2] * dt * 60
            particle[1] += particle[3] * dt * 60
            particle[4] -= 0.02 * dt * 60
            if particle[4] <= 0:
                self.particles.remove(particle)
    
    def add_particle(self):
        # 在嘴部区域添加粒子
        x = random.randint(WIDTH//2 - 100, WIDTH//2 + 100)
        y = random.randint(HEIGHT//2 - 50, HEIGHT//2 + 50)
        dx = random.uniform(-1, 1) * self.intensity
        dy = random.uniform(-1, 1) * self.intensity
        size = random.randint(2, 6)
        alpha = random.uniform(0.5, 1.0)
        self.particles.append([x, y, dx, dy, alpha, size])
    
    def draw(self, screen):
        # 绘制背景
        screen.fill(BACKGROUND)
        
        # 绘制网格
        for i in range(0, WIDTH, 20):
            alpha = 30 if i % 100 != 0 else 60
            pygame.draw.line(screen, (40, 40, 60), (i, 0), (i, HEIGHT), 1)
        for i in range(0, HEIGHT, 20):
            alpha = 30 if i % 100 != 0 else 60
            pygame.draw.line(screen, (40, 40, 60), (0, i), (WIDTH, i), 1)
        
        # 绘制粒子
        for particle in self.particles:
            x, y, dx, dy, alpha, size = particle
            color = (255, 200, 200, int(255 * alpha))
            pygame.gfxdraw.filled_circle(screen, int(x), int(y), size, (*color[:3], 128))
            pygame.gfxdraw.aacircle(screen, int(x), int(y), size, (*color[:3], 200))
        
        # 绘制嘴部
        self.draw_mouth(screen)
        
        # 绘制数据图表
        self.draw_charts(screen)
        
        # 绘制UI
        self.draw_ui(screen)
    
    def draw_mouth(self, screen):
        # 绘制嘴部
        center_x, center_y = WIDTH // 2, HEIGHT // 2
        mouth_width = 200 + 50 * self.intensity
        mouth_height = 80 + 40 * self.intensity
        
        # 绘制下嘴唇
        pygame.draw.ellipse(screen, MOUTH_COLOR, 
                           (center_x - mouth_width//2, center_y - mouth_height//3, 
                            mouth_width, mouth_height))
        
        # 绘制上嘴唇
        pygame.draw.ellipse(screen, MOUTH_COLOR, 
                           (center_x - mouth_width//2, center_y - mouth_height//3 - 20, 
                            mouth_width, mouth_height))
        
        # 绘制舌头
        if self.intensity > 0.2:
            tongue_height = 40 + 30 * self.intensity
            tongue_width = 120 + 30 * self.tongue_movement
            
            # 舌头动态效果
            tongue_offset = 5 * math.sin(self.time_elapsed * 5) * self.tongue_movement
            
            # 绘制舌头主体
            pygame.draw.ellipse(screen, TONGUE_COLOR, 
                              (center_x - tongue_width//2, center_y - tongue_height//2 + tongue_offset, 
                               tongue_width, tongue_height))
            
            # 绘制舌头细节
            for i in range(3):
                wave = 10 * math.sin(self.time_elapsed * 3 + i) * self.tongue_movement
                pygame.draw.circle(screen, HIGHLIGHT_COLOR, 
                                  (center_x - tongue_width//4 + i*tongue_width//3, 
                                   center_y + 10 + wave),
                                  8 + 2 * math.sin(self.time_elapsed * 2 + i))
        
        # 绘制嘴唇高光
        pygame.draw.arc(screen, HIGHLIGHT_COLOR, 
                       (center_x - mouth_width//2, center_y - mouth_height//3 - 20, 
                        mouth_width, mouth_height),
                       math.pi, 2 * math.pi, 3)
        
        # 绘制心跳效果
        if self.intensity > 0.3:
            heart_size = 5 + 15 * (self.heart_rate - 70) / 40
            for i in range(3):
                offset = i * 10
                pygame.draw.circle(screen, (*HEART_COLOR, 150 - i*50), 
                                  (center_x, center_y - 100 - offset), 
                                  heart_size - i*2, 1)
    
    def draw_charts(self, screen):
        # 绘制心率图表
        pygame.draw.rect(screen, (30, 30, 40), (50, 50, 300, 150), border_radius=10)
        pygame.draw.rect(screen, (60, 60, 80), (50, 50, 300, 150), 2, border_radius=10)
        
        title = font_medium.render("心率变化", True, TEXT_COLOR)
        screen.blit(title, (60, 55))
        
        if len(self.heart_rate_data) > 1:
            points = []
            for i, hr in enumerate(self.heart_rate_data[-30:]):
                x = 50 + 10 * i
                y = 180 - (hr - 60) * 1.5
                points.append((x, y))
            
            if len(points) > 1:
                pygame.draw.lines(screen, HEART_COLOR, False, points, 3)
        
        # 绘制唾液分泌图表
        pygame.draw.rect(screen, (30, 30, 40), (50, 220, 300, 150), border_radius=10)
        pygame.draw.rect(screen, (60, 60, 80), (50, 220, 300, 150), 2, border_radius=10)
        
        title = font_medium.render("唾液分泌", True, TEXT_COLOR)
        screen.blit(title, (60, 225))
        
        if len(self.saliva_data) > 1:
            points = []
            for i, s in enumerate(self.saliva_data[-30:]):
                x = 50 + 10 * i
                y = 350 - s * 100
                points.append((x, y))
            
            if len(points) > 1:
                pygame.draw.lines(screen, (100, 200, 255), False, points, 3)
        
        # 绘制舌头运动图表
        pygame.draw.rect(screen, (30, 30, 40), (50, 390, 300, 150), border_radius=10)
        pygame.draw.rect(screen, (60, 60, 80), (50, 390, 300, 150), 2, border_radius=10)
        
        title = font_medium.render("舌头运动频率", True, TEXT_COLOR)
        screen.blit(title, (60, 395))
        
        if len(self.movement_data) > 1:
            points = []
            for i, m in enumerate(self.movement_data[-30:]):
                x = 50 + 10 * i
                y = 520 - m * 100
                points.append((x, y))
            
            if len(points) > 1:
                pygame.draw.lines(screen, (255, 150, 200), False, points, 3)
    
    def draw_ui(self, screen):
        # 绘制标题
        title = font_large.render("舌吻交互式生物反馈可视化系统", True, TEXT_COLOR)
        screen.blit(title, (WIDTH//2 - title.get_width()//2, 15))
        
        # 绘制数据面板
        pygame.draw.rect(screen, (30, 30, 40), (WIDTH - 350, 50, 300, 200), border_radius=10)
        pygame.draw.rect(screen, (60, 60, 80), (WIDTH - 350, 50, 300, 200), 2, border_radius=10)
        
        # 绘制实时数据
        hr_text = font_medium.render(f"心率: {self.heart_rate} BPM", True, HEART_COLOR)
        saliva_text = font_medium.render(f"唾液分泌: {int(self.saliva * 100)}%", True, (100, 200, 255))
        move_text = font_medium.render(f"舌头运动: {int(self.tongue_movement * 100)}%", True, (255, 150, 200))
        intensity_text = font_medium.render(f"吻强度: {int(self.intensity * 100)}%", True, TEXT_COLOR)
        duration_text = font_medium.render(f"持续时间: {self.duration:.1f}秒", True, TEXT_COLOR)
        
        screen.blit(hr_text, (WIDTH - 330, 70))
        screen.blit(saliva_text, (WIDTH - 330, 110))
        screen.blit(move_text, (WIDTH - 330, 150))
        screen.blit(intensity_text, (WIDTH - 330, 190))
        screen.blit(duration_text, (WIDTH - 330, 230))
        
        # 绘制控制说明
        pygame.draw.rect(screen, (30, 40, 50), (WIDTH - 350, HEIGHT - 120, 300, 80), border_radius=10)
        pygame.draw.rect(screen, (70, 100, 120), (WIDTH - 350, HEIGHT - 120, 300, 80), 2, border_radius=10)
        
        ctrl1 = font_small.render("空格键: 增加吻强度", True, TEXT_COLOR)
        ctrl2 = font_small.render("R键: 重置模拟", True, TEXT_COLOR)
        screen.blit(ctrl1, (WIDTH - 330, HEIGHT - 100))
        screen.blit(ctrl2, (WIDTH - 330, HEIGHT - 70))
        
        # 绘制科学信息
        info = [
            "舌吻科学信息:",
            "- 平均持续时间为5-17秒",
            "- 可消耗6.4卡路里/分钟",
            "- 刺激唾液分泌，有益牙齿健康",
            "- 释放内啡肽，减轻压力"
        ]
        
        pygame.draw.rect(screen, (40, 30, 50), (50, HEIGHT - 180, 400, 160), border_radius=10)
        pygame.draw.rect(screen, (100, 70, 120), (50, HEIGHT - 180, 400, 160), 2, border_radius=10)
        
        for i, text in enumerate(info):
            rendered = font_small.render(text, True, TEXT_COLOR)
            screen.blit(rendered, (70, HEIGHT - 160 + i * 25))

def main():
    clock = pygame.time.Clock()
    simulation = KissSimulation()
    running = True
    
    while running:
        dt = clock.tick(60) / 1000.0  # 转换为秒
        intensity_input = None
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    intensity_input = 1.0
                elif event.key == pygame.K_r:
                    simulation = KissSimulation()
        
        # 持续按键检测
        keys = pygame.key.get_pressed()
        if keys[pygame.K_SPACE]:
            intensity_input = 1.0
        
        simulation.update(dt, intensity_input)
        simulation.draw(screen)
        
        pygame.display.flip()
    
    pygame.quit()

if __name__ == "__main__":
    main()