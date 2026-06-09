import sys
import cv2
import numpy as np
import math
from scipy import ndimage
from scipy.spatial import Voronoi, Delaunay
import random
from collections import deque
from numba import jit, prange
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QComboBox, QSlider, 
                             QLabel, QGroupBox, QCheckBox, QSpinBox, 
                             QDoubleSpinBox, QTabWidget, QSplitter, QFrame,
                             QFileDialog, QMessageBox, QProgressBar)
from PyQt5.QtCore import QTimer, Qt, pyqtSignal, QThread, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap, QFont, QPainter, QPen, QColor

class AdvancedMathVisualGenerator:
    def __init__(self, width=800, height=600):
        self.width = width
        self.height = height
        self.time = 0
        
        # 先初始化参数
        self.params = {
            'fluid_viscosity': 0.0001,
            'fluid_dt': 0.1,
            'rd_f': 0.035,
            'rd_k': 0.065,
            'lorenz_speed': 0.01,
            'fractal_iterations': 100,
            'particle_count': 500,
            'wave_speed': 0.5,
            'quantum_scale': 1.0,
            'morph_radius': 10,
            'optical_flow_threshold': 0.3,
            'heat_diffusion': 0.1,
            'em_frequency': 0.1,
            'ca_rule': 30,
            'ray_steps': 100,
            'flame_iterations': 20,
            'attractor_points': 1000
        }
        
        # 初始化各种数学系统
        self.init_fluid_simulation()
        self.init_reaction_diffusion()
        self.init_chaos_system()
        self.init_fractal_system()
        self.init_particle_system()
        self.init_wave_system()
        self.init_cellular_automata()
        self.init_ray_marching()
        self.init_fractal_flame()
        self.init_strange_attractor()
        
        self.effects = [
            "fluid_simulation", "reaction_diffusion", "lorenz_attractor", 
            "mandelbrot_zoom", "julia_set", "voronoi_diagram", 
            "wave_equation", "quantum_wave", "cellular_automata",
            "particle_system", "ray_marching", "morphological_operations",
            "optical_flow", "heat_equation", "electromagnetic_waves",
            "fractal_flame", "strange_attractor", "fluid_particles",
            "reaction_diffusion_3d", "neural_network"
        ]
        self.current_effect = "fluid_simulation"
        
        # 鼠标交互
        self.mouse_pos = None
        self.mouse_pressed = False

    def init_fluid_simulation(self):
        """初始化流体模拟参数"""
        self.fluid_size = 128
        self.velocity_x = np.zeros((self.fluid_size, self.fluid_size))
        self.velocity_y = np.zeros((self.fluid_size, self.fluid_size))
        self.density = np.zeros((self.fluid_size, self.fluid_size))
        self.pressure = np.zeros((self.fluid_size, self.fluid_size))
        
    def init_reaction_diffusion(self):
        """初始化反应扩散系统"""
        self.rd_size = 256
        self.U = np.ones((self.rd_size, self.rd_size))
        self.V = np.zeros((self.rd_size, self.rd_size))
        
        # 添加初始扰动
        h, w = self.rd_size, self.rd_size
        r = 20
        self.U[h//2-r:h//2+r, w//2-r:w//2+r] = 0.5
        self.V[h//2-r:h//2+r, w//2-r:w//2+r] = 0.25
        
        # Gray-Scott模型参数
        self.Du = 0.16
        self.Dv = 0.08
        
    def init_chaos_system(self):
        """初始化混沌系统"""
        self.lorenz_points = deque(maxlen=5000)
        self.lorenz_x, self.lorenz_y, self.lorenz_z = 0.1, 0.0, 0.0
        
        # Lorenz系统参数
        self.sigma = 10.0
        self.rho = 28.0
        self.beta = 8.0 / 3.0
        
    def init_fractal_system(self):
        """初始化分形系统"""
        self.mandelbrot_center = complex(-0.5, 0)
        self.mandelbrot_scale = 2.5
        self.julia_c = complex(0.7885, 0)
        
    def init_particle_system(self):
        """初始化粒子系统"""
        self.particles = []
        self.fluid_particles = []
        self.init_particles()
        
    def init_wave_system(self):
        """初始化波动系统"""
        self.wave_height = np.zeros((self.height, self.width))
        self.wave_velocity = np.zeros((self.height, self.width))
        cv2.circle(self.wave_height, (self.width//2, self.height//2), 30, 100, -1)
        
    def init_cellular_automata(self):
        """初始化元胞自动机"""
        self.ca_size = 200
        self.ca_grid = np.zeros((self.ca_size, self.ca_size))
        self.ca_grid[self.ca_size//2, self.ca_size//2] = 1
        
    def init_ray_marching(self):
        """初始化光线行进"""
        self.ray_time = 0
        
    def init_fractal_flame(self):
        """初始化分形火焰"""
        self.flame_points = []
        self.flame_x, self.flame_y = 0, 0
        
    def init_strange_attractor(self):
        """初始化奇异吸引子"""
        self.attractor_points = deque(maxlen=10000)
        
    def init_particles(self):
        """初始化粒子"""
        self.particles = []
        for _ in range(self.params['particle_count']):
            particle = {
                'x': random.uniform(0, self.width),
                'y': random.uniform(0, self.height),
                'vx': random.uniform(-2, 2),
                'vy': random.uniform(-2, 2),
                'life': random.uniform(50, 200),
                'color': (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
            }
            self.particles.append(particle)

    def solve_fluid_equations(self, u, v, p, density, dt=0.1, viscosity=0.0001):
        """求解Navier-Stokes方程"""
        h, w = u.shape
        
        # 扩散步骤
        for _ in range(4):
            u[1:-1, 1:-1] = (u[1:-1, 1:-1] + viscosity * dt * (
                u[2:, 1:-1] + u[:-2, 1:-1] + u[1:-1, 2:] + u[1:-1, :-2] - 4 * u[1:-1, 1:-1]
            )) / (1 + 4 * viscosity * dt)
            
            v[1:-1, 1:-1] = (v[1:-1, 1:-1] + viscosity * dt * (
                v[2:, 1:-1] + v[:-2, 1:-1] + v[1:-1, 2:] + v[1:-1, :-2] - 4 * v[1:-1, 1:-1]
            )) / (1 + 4 * viscosity * dt)
        
        # 投影步骤 (压力求解)
        for _ in range(20):
            p[1:-1, 1:-1] = (p[2:, 1:-1] + p[:-2, 1:-1] + p[1:-1, 2:] + p[1:-1, :-2] -
                            (u[1:-1, 2:] - u[1:-1, :-2] + v[2:, 1:-1] - v[:-2, 1:-1]) * 0.5) / 4
        
        # 应用压力梯度
        u[1:-1, 1:-1] -= 0.5 * (p[1:-1, 2:] - p[1:-1, :-2])
        v[1:-1, 1:-1] -= 0.5 * (p[2:, 1:-1] - p[:-2, 1:-1])
        
        # 密度扩散
        density[1:-1, 1:-1] = (density[1:-1, 1:-1] + 0.1 * dt * (
            density[2:, 1:-1] + density[:-2, 1:-1] + density[1:-1, 2:] + density[1:-1, :-2] - 4 * density[1:-1, 1:-1]
        )) / (1 + 4 * 0.1 * dt)
        
        # 密度对流
        for i in range(1, h-1):
            for j in range(1, w-1):
                x = j - u[i, j] * dt
                y = i - v[i, j] * dt
                x = max(1, min(w-2, x))
                y = max(1, min(h-2, y))
                density[i, j] = density[int(y), int(x)]
        
        return u, v, p, density
    
    def fluid_simulation_effect(self, frame):
        """基于Navier-Stokes方程的流体模拟"""
        h, w = self.fluid_size, self.fluid_size
        
        # 添加鼠标交互
        if self.mouse_pos and self.mouse_pressed:
            mx, my = self.mouse_pos
            mx = int(mx * w / self.width)
            my = int(my * h / self.height)
            
            if 0 <= mx < w and 0 <= my < h:
                self.density[my-2:my+2, mx-2:mx+2] += 10.0
                self.velocity_x[my-2:my+2, mx-2:mx+2] += (random.random() - 0.5) * 5
                self.velocity_y[my-2:my+2, mx-2:mx+2] += (random.random() - 0.5) * 5
        
        # 求解流体方程
        self.velocity_x, self.velocity_y, self.pressure, self.density = \
            self.solve_fluid_equations(self.velocity_x, self.velocity_y, 
                                     self.pressure, self.density, 
                                     self.params['fluid_dt'], self.params['fluid_viscosity'])
        
        # 创建可视化
        fluid_viz = np.zeros((h, w, 3), dtype=np.uint8)
        
        # 将密度映射到颜色
        density_norm = np.clip(self.density / 10.0, 0, 1)
        fluid_viz[:, :, 0] = (np.sin(density_norm * 2 * np.pi) * 127 + 128).astype(np.uint8)
        fluid_viz[:, :, 1] = (np.cos(density_norm * 3 * np.pi) * 127 + 128).astype(np.uint8)
        fluid_viz[:, :, 2] = (density_norm * 255).astype(np.uint8)
        
        # 缩放以适应输出
        result = cv2.resize(fluid_viz, (self.width, self.height), interpolation=cv2.INTER_LINEAR)
        return result
    
    def reaction_diffusion_step(self, U, V, Du, Dv, f, k, dt=1.0):
        """反应扩散系统单步计算"""
        h, w = U.shape
        U_new = U.copy()
        V_new = V.copy()
        
        laplacian_U = np.zeros((h, w))
        laplacian_V = np.zeros((h, w))
        
        # 计算拉普拉斯算子
        for i in range(1, h-1):
            for j in range(1, w-1):
                laplacian_U[i, j] = (U[i+1, j] + U[i-1, j] + U[i, j+1] + U[i, j-1] - 4 * U[i, j])
                laplacian_V[i, j] = (V[i+1, j] + V[i-1, j] + V[i, j+1] + V[i, j-1] - 4 * V[i, j])
        
        # 反应扩散方程
        for i in range(h):
            for j in range(w):
                reaction = U[i, j] * V[i, j] * V[i, j]
                U_new[i, j] = U[i, j] + (Du * laplacian_U[i, j] - reaction + f * (1 - U[i, j])) * dt
                V_new[i, j] = V[i, j] + (Dv * laplacian_V[i, j] + reaction - (f + k) * V[i, j]) * dt
        
        return np.clip(U_new, 0, 1), np.clip(V_new, 0, 1)
    
    def reaction_diffusion_effect(self, frame):
        """反应扩散模式生成"""
        # 更新反应扩散系统
        self.U, self.V = self.reaction_diffusion_step(
            self.U, self.V, self.Du, self.Dv, 
            self.params['rd_f'], self.params['rd_k']
        )
        
        # 创建可视化
        rd_viz = np.zeros((self.rd_size, self.rd_size, 3), dtype=np.uint8)
        rd_viz[:, :, 0] = (self.U * 255).astype(np.uint8)
        rd_viz[:, :, 1] = (self.V * 255).astype(np.uint8)
        rd_viz[:, :, 2] = ((1 - self.U) * 255).astype(np.uint8)
        
        # 缩放以适应输出
        result = cv2.resize(rd_viz, (self.width, self.height), interpolation=cv2.INTER_LINEAR)
        return result

    def lorenz_attractor_effect(self, frame):
        """Lorenz吸引子可视化"""
        # 更新Lorenz系统
        dt = self.params['lorenz_speed']
        dx = self.sigma * (self.lorenz_y - self.lorenz_x)
        dy = self.lorenz_x * (self.rho - self.lorenz_z) - self.lorenz_y
        dz = self.lorenz_x * self.lorenz_y - self.beta * self.lorenz_z
        
        self.lorenz_x += dx * dt
        self.lorenz_y += dy * dt
        self.lorenz_z += dz * dt
        
        # 将3D点映射到2D屏幕
        scale = 10
        x_proj = int(self.lorenz_x * scale + self.width // 2)
        y_proj = int(self.lorenz_y * scale + self.height // 2)
        
        self.lorenz_points.append((x_proj, y_proj))
        
        # 创建可视化
        result = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        
        # 绘制轨迹
        points = list(self.lorenz_points)
        for i in range(1, len(points)):
            cv2.line(result, points[i-1], points[i], 
                    (int(255 * i / len(points)), 255, int(255 * (1 - i / len(points)))), 1)
        
        return result

    def mandelbrot_iteration(self, c, max_iter):
        """Mandelbrot集迭代计算"""
        z = 0j
        for i in range(max_iter):
            z = z * z + c
            if abs(z) > 2:
                return i
        return max_iter

    def mandelbrot_zoom_effect(self, frame):
        """Mandelbrot集缩放动画"""
        result = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        
        # 动态缩放
        zoom_factor = 0.9 + 0.1 * math.sin(self.time * 0.1)
        self.mandelbrot_scale *= zoom_factor
        
        # 计算Mandelbrot集
        max_iter = self.params['fractal_iterations']
        for y in range(self.height):
            for x in range(self.width):
                # 将像素坐标转换为复数
                re = (x - self.width / 2) / (0.5 * self.mandelbrot_scale * self.width) + self.mandelbrot_center.real
                im = (y - self.height / 2) / (0.5 * self.mandelbrot_scale * self.height) + self.mandelbrot_center.imag
                c = complex(re, im)
                
                # 计算迭代次数
                iter_count = self.mandelbrot_iteration(c, max_iter)
                
                # 根据迭代次数设置颜色
                if iter_count == max_iter:
                    result[y, x] = (0, 0, 0)
                else:
                    hue = int(255 * iter_count / max_iter)
                    hsv_color = np.uint8([[[hue, 255, 255]]])
                    bgr_color = cv2.cvtColor(hsv_color, cv2.COLOR_HSV2BGR)
                    result[y, x] = bgr_color[0, 0]
        
        return result

    def julia_set_effect(self, frame):
        """Julia集可视化"""
        result = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        
        # 动态变化的Julia参数
        self.julia_c = complex(0.7885 * math.cos(self.time * 0.05), 
                              0.7885 * math.sin(self.time * 0.05))
        
        max_iter = self.params['fractal_iterations']
        for y in range(self.height):
            for x in range(self.width):
                # 将像素坐标转换为复数
                re = (x - self.width / 2) / (self.width / 4)
                im = (y - self.height / 2) / (self.height / 4)
                z = complex(re, im)
                
                # Julia集迭代
                for i in range(max_iter):
                    z = z * z + self.julia_c
                    if abs(z) > 2:
                        break
                
                # 设置颜色
                color_intensity = min(255, i * 8)
                result[y, x] = (color_intensity, 
                               (color_intensity * 2) % 256, 
                               (color_intensity * 3) % 256)
        
        return result

    def voronoi_diagram_effect(self, frame):
        """Voronoi图生成"""
        # 生成随机点
        n_points = 50
        points = np.random.rand(n_points, 2) * np.array([self.width, self.height])
        
        # 创建Voronoi图
        vor = Voronoi(points)
        
        # 创建可视化
        result = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        
        # 绘制Voronoi区域
        for region in vor.regions:
            if not region or -1 in region:
                continue
            
            polygon = [vor.vertices[i] for i in region]
            polygon = np.array(polygon, dtype=np.int32)
            
            # 随机颜色
            color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
            cv2.fillPoly(result, [polygon], color)
        
        # 绘制点
        for point in points:
            cv2.circle(result, (int(point[0]), int(point[1])), 3, (255, 255, 255), -1)
        
        return result

    def wave_equation_effect(self, frame):
        """波动方程模拟"""
        # 波动方程求解
        laplacian = ndimage.laplace(self.wave_height)
        damping = 0.99
        wave_speed = self.params['wave_speed']
        
        self.wave_velocity += wave_speed * laplacian
        self.wave_velocity *= damping
        self.wave_height += self.wave_velocity
        
        # 边界条件
        self.wave_height[0, :] = 0
        self.wave_height[-1, :] = 0
        self.wave_height[:, 0] = 0
        self.wave_height[:, -1] = 0
        
        # 添加鼠标交互
        if self.mouse_pos and self.mouse_pressed:
            mx, my = self.mouse_pos
            cv2.circle(self.wave_height, (int(mx), int(my)), 20, 50, -1)
        
        # 创建可视化
        result = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        wave_norm = (self.wave_height - self.wave_height.min()) / (self.wave_height.max() - self.wave_height.min() + 1e-8)
        
        # 使用颜色映射
        result[:, :, 0] = (wave_norm * 255).astype(np.uint8)
        result[:, :, 1] = ((1 - wave_norm) * 255).astype(np.uint8)
        result[:, :, 2] = (128 + 127 * np.sin(wave_norm * 2 * np.pi)).astype(np.uint8)
        
        return result

    #@jit(nopython=True, parallel=True)
    def quantum_wave_function(self, time, width, height, scale):
        """量子波函数可视化"""
        result = np.zeros((height, width, 3), dtype=np.uint8)
        
        for y in prange(height):
            for x in prange(width):
                # 归一化坐标
                u = (x - width/2) / (width/4)
                v = (y - height/2) / (height/4)
                
                # 时间相关的波函数
                t = time * 0.01 * scale
                wave1 = math.sin(u * 5 + t) * math.cos(v * 3 + t)
                wave2 = math.sin(u * 3 - t) * math.cos(v * 5 - t)
                wave3 = math.sin(math.sqrt(u*u + v*v) * 8 + t)
                
                # 组合波函数
                combined = (wave1 + wave2 + wave3) / 3
                
                # 转换为颜色
                r = int((math.sin(combined * math.pi) + 1) * 127)
                g = int((math.cos(combined * math.pi * 2) + 1) * 127)
                b = int((combined + 1) * 127)
                
                result[y, x] = (r, g, b)
        
        return result

    def particle_system_effect(self, frame):
        """粒子系统"""
        if len(self.particles) < self.params['particle_count']:
            self.init_particles()
        
        result = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        
        # 更新和绘制粒子
        new_particles = []
        for particle in self.particles:
            # 更新位置
            particle['x'] += particle['vx']
            particle['y'] += particle['vy']
            particle['life'] -= 1
            
            # 边界反弹
            if particle['x'] < 0 or particle['x'] >= self.width:
                particle['vx'] *= -1
            if particle['y'] < 0 or particle['y'] >= self.height:
                particle['vy'] *= -1
            
            # 绘制粒子
            x, y = int(particle['x']), int(particle['y'])
            if 0 <= x < self.width and 0 <= y < self.height:
                cv2.circle(result, (x, y), 2, particle['color'], -1)
            
            # 如果粒子还活着，保留它
            if particle['life'] > 0:
                new_particles.append(particle)
        
        self.particles = new_particles
        
        return result

    def cellular_automata_effect(self, frame):
        """元胞自动机"""
        # 应用规则
        new_grid = np.zeros((self.ca_size, self.ca_size))
        
        rule = self.params['ca_rule']
        rule_bin = [int(x) for x in format(rule, '08b')]
        
        for i in range(1, self.ca_size-1):
            for j in range(1, self.ca_size-1):
                # 获取邻居状态
                left = self.ca_grid[i, j-1]
                center = self.ca_grid[i, j]
                right = self.ca_grid[i, j+1]
                
                # 计算规则索引
                pattern = int(left * 4 + center * 2 + right)
                new_grid[i, j] = rule_bin[7 - pattern]
        
        self.ca_grid = new_grid
        
        # 创建可视化
        result = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        ca_viz = cv2.resize(self.ca_grid, (self.width, self.height), interpolation=cv2.INTER_NEAREST)
        
        # 应用颜色
        result[:, :, 0] = (ca_viz * 255).astype(np.uint8)
        result[:, :, 1] = ((1 - ca_viz) * 255).astype(np.uint8)
        result[:, :, 2] = (ca_viz * 128).astype(np.uint8)
        
        return result

    def ray_marching_effect(self, frame):
        """光线行进3D场景"""
        result = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        
        self.ray_time += 0.05
        
        for y in range(self.height):
            for x in range(self.width):
                # 归一化坐标
                u = (x - self.width/2) / self.width
                v = (y - self.height/2) / self.height
                
                # 光线方向
                ray_dir = np.array([u, v, 1])
                ray_dir = ray_dir / np.linalg.norm(ray_dir)
                
                # 光线起点
                ray_origin = np.array([0, 0, -3])
                
                # 光线行进
                t = 0
                for _ in range(self.params['ray_steps']):
                    # 当前点
                    p = ray_origin + t * ray_dir
                    
                    # 距离函数 (球体 + 扰动)
                    d = np.linalg.norm(p) - 1
                    d += 0.1 * math.sin(5*p[0] + self.ray_time) * math.sin(5*p[1] + self.ray_time) * math.sin(5*p[2] + self.ray_time)
                    
                    if d < 0.01:
                        # 命中表面，计算颜色
                        normal = p / np.linalg.norm(p)
                        light_dir = np.array([0.5, 0.5, 1])
                        light_dir = light_dir / np.linalg.norm(light_dir)
                        
                        diffuse = max(0, np.dot(normal, light_dir))
                        color = (int(diffuse * 255), int(diffuse * 200), int(diffuse * 150))
                        result[y, x] = color
                        break
                    
                    t += d
                    
                    if t > 10:
                        break
        
        return result

    def fractal_flame_effect(self, frame):
        """分形火焰效果"""
        if len(self.flame_points) > 10000:
            self.flame_points = self.flame_points[-5000:]
        
        # 迭代函数系统
        for _ in range(100):
            r = random.random()
            
            if r < 0.5:
                # 线性变换
                self.flame_x = 0.5 * self.flame_x
                self.flame_y = 0.5 * self.flame_y
            elif r < 0.75:
                # 正弦变换
                self.flame_x = math.sin(self.flame_x)
                self.flame_y = math.sin(self.flame_y)
            else:
                # 球形变换
                r2 = self.flame_x * self.flame_x + self.flame_y * self.flame_y
                self.flame_x = self.flame_x / r2
                self.flame_y = self.flame_y / r2
            
            # 添加随机扰动
            self.flame_x += random.uniform(-0.1, 0.1)
            self.flame_y += random.uniform(-0.1, 0.1)
            
            # 映射到屏幕坐标
            px = int((self.flame_x + 1) * self.width / 2)
            py = int((self.flame_y + 1) * self.height / 2)
            
            if 0 <= px < self.width and 0 <= py < self.height:
                self.flame_points.append((px, py))
        
        # 创建可视化
        result = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        
        # 绘制点
        for px, py in self.flame_points:
            if 0 <= px < self.width and 0 <= py < self.height:
                # 根据位置设置颜色
                hue = int(255 * (px + py) / (self.width + self.height))
                result[py, px] = (hue, (hue + 85) % 255, (hue + 170) % 255)
        
        return result

    def strange_attractor_effect(self, frame):
        """奇异吸引子"""
        # Clifford吸引子
        a, b, c, d = -1.3, -1.3, -1.8, -1.9
        
        x, y = 0, 0
        for _ in range(self.params['attractor_points']):
            x_new = math.sin(a * y) + c * math.cos(a * x)
            y_new = math.sin(b * x) + d * math.cos(b * y)
            x, y = x_new, y_new
            
            # 映射到屏幕
            px = int((x + 2) * self.width / 4)
            py = int((y + 2) * self.height / 4)
            
            if 0 <= px < self.width and 0 <= py < self.height:
                self.attractor_points.append((px, py))
        
        # 创建可视化
        result = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        
        # 绘制轨迹
        points = list(self.attractor_points)
        for i in range(1, len(points)):
            cv2.line(result, points[i-1], points[i], 
                    (int(255 * i / len(points)), 
                     int(255 * (1 - i / len(points))), 
                     255), 1)
        
        return result

    def morphological_operations_effect(self, frame):
        """形态学操作效果"""
        if frame is None:
            # 生成测试图案
            frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
            for i in range(10):
                x = random.randint(0, self.width-1)
                y = random.randint(0, self.height-1)
                cv2.circle(frame, (x, y), 30, (255, 255, 255), -1)
        
        # 转换为灰度
        gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
        
        # 形态学操作
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, 
                                         (self.params['morph_radius'], 
                                          self.params['morph_radius']))
        
        # 应用不同的形态学操作
        operations = [
            gray,
            cv2.erode(gray, kernel),
            cv2.dilate(gray, kernel),
            cv2.morphologyEx(gray, cv2.MORPH_OPEN, kernel),
            cv2.morphologyEx(gray, cv2.MORPH_CLOSE, kernel),
            cv2.morphologyEx(gray, cv2.MORPH_GRADIENT, kernel)
        ]
        
        # 选择当前操作
        op_index = int(self.time / 30) % len(operations)
        result_gray = operations[op_index]
        
        # 转换回彩色
        result = cv2.cvtColor(result_gray, cv2.COLOR_GRAY2RGB)
        
        return result

    def set_mouse_position(self, x, y, pressed=False):
        """设置鼠标位置用于交互"""
        self.mouse_pos = (x, y)
        self.mouse_pressed = pressed
    
    def process_frame(self, frame=None):
        """处理帧并应用当前效果"""
        self.time += 1
        
        if self.current_effect == "fluid_simulation":
            return self.fluid_simulation_effect(frame)
        elif self.current_effect == "reaction_diffusion":
            return self.reaction_diffusion_effect(frame)
        elif self.current_effect == "lorenz_attractor":
            return self.lorenz_attractor_effect(frame)
        elif self.current_effect == "mandelbrot_zoom":
            return self.mandelbrot_zoom_effect(frame)
        elif self.current_effect == "julia_set":
            return self.julia_set_effect(frame)
        elif self.current_effect == "voronoi_diagram":
            return self.voronoi_diagram_effect(frame)
        elif self.current_effect == "wave_equation":
            return self.wave_equation_effect(frame)
        elif self.current_effect == "quantum_wave":
            return self.quantum_wave_function(self.time, self.width, self.height, self.params['quantum_scale'])
        elif self.current_effect == "particle_system":
            return self.particle_system_effect(frame)
        elif self.current_effect == "cellular_automata":
            return self.cellular_automata_effect(frame)
        elif self.current_effect == "ray_marching":
            return self.ray_marching_effect(frame)
        elif self.current_effect == "fractal_flame":
            return self.fractal_flame_effect(frame)
        elif self.current_effect == "strange_attractor":
            return self.strange_attractor_effect(frame)
        elif self.current_effect == "morphological_operations":
            return self.morphological_operations_effect(frame)
        else:
            # 默认返回黑色图像
            return np.zeros((self.height, self.width, 3), dtype=np.uint8)

class CameraThread:
    """摄像头线程模拟"""
    def __init__(self, camera_index=0):
        self.camera_index = camera_index
        self.cap = None
        self.frame = None
        self.running = False
        
    def start(self):
        """启动摄像头"""
        self.cap = cv2.VideoCapture(self.camera_index)
        if not self.cap.isOpened():
            return False
        
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.running = True
        return True
    
    def read_frame(self):
        """读取帧"""
        if self.cap and self.running:
            ret, frame = self.cap.read()
            if ret:
                self.frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                return True
        return False
    
    def stop(self):
        """停止摄像头"""
        self.running = False
        if self.cap:
            self.cap.release()

class VideoDisplayWidget(QWidget):
    """视频显示组件"""
    mouseMoved = pyqtSignal(int, int)
    mousePressed = pyqtSignal(int, int, bool)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.image_label = QLabel(self)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setMinimumSize(800, 600)
        self.image_label.setMouseTracking(True)
        
        layout = QVBoxLayout()
        layout.addWidget(self.image_label)
        self.setLayout(layout)
        
        # 鼠标跟踪
        self.image_label.mouseMoveEvent = self.mouse_move_event
        self.image_label.mousePressEvent = self.mouse_press_event
        self.image_label.mouseReleaseEvent = self.mouse_release_event
    
    def mouse_move_event(self, event):
        """鼠标移动事件"""
        x = event.pos().x()
        y = event.pos().y()
        self.mouseMoved.emit(x, y)
    
    def mouse_press_event(self, event):
        """鼠标按下事件"""
        x = event.pos().x()
        y = event.pos().y()
        self.mousePressed.emit(x, y, True)
    
    def mouse_release_event(self, event):
        """鼠标释放事件"""
        x = event.pos().x()
        y = event.pos().y()
        self.mousePressed.emit(x, y, False)
    
    def update_image(self, image):
        """更新显示的图像"""
        if image is not None:
            height, width, channel = image.shape
            bytes_per_line = 3 * width
            q_img = QImage(image.data, width, height, bytes_per_line, QImage.Format_RGB888)
            self.image_label.setPixmap(QPixmap.fromImage(q_img))

class ControlPanel(QWidget):
    """控制面板"""
    def __init__(self, generator, parent=None):
        super().__init__(parent)
        self.generator = generator
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout()
        
        # 效果选择
        effect_group = QGroupBox("效果选择")
        effect_layout = QVBoxLayout()
        
        self.effect_combo = QComboBox()
        self.effect_combo.addItems(self.generator.effects)
        self.effect_combo.setCurrentText(self.generator.current_effect)
        self.effect_combo.currentTextChanged.connect(self.on_effect_changed)
        effect_layout.addWidget(QLabel("选择效果:"))
        effect_layout.addWidget(self.effect_combo)
        
        effect_group.setLayout(effect_layout)
        layout.addWidget(effect_group)
        
        # 创建选项卡
        self.tab_widget = QTabWidget()
        
        # 流体参数选项卡
        fluid_tab = QWidget()
        fluid_layout = QVBoxLayout()
        
        # 流体粘度
        viscosity_layout = QHBoxLayout()
        viscosity_layout.addWidget(QLabel("流体粘度:"))
        self.viscosity_slider = QSlider(Qt.Horizontal)
        self.viscosity_slider.setRange(1, 1000)
        self.viscosity_slider.setValue(int(self.generator.params['fluid_viscosity'] * 1000000))
        self.viscosity_slider.valueChanged.connect(self.on_viscosity_changed)
        viscosity_layout.addWidget(self.viscosity_slider)
        fluid_layout.addLayout(viscosity_layout)
        
        # 流体时间步长
        dt_layout = QHBoxLayout()
        dt_layout.addWidget(QLabel("时间步长:"))
        self.dt_spin = QDoubleSpinBox()
        self.dt_spin.setRange(0.01, 1.0)
        self.dt_spin.setSingleStep(0.01)
        self.dt_spin.setValue(self.generator.params['fluid_dt'])
        self.dt_spin.valueChanged.connect(self.on_dt_changed)
        dt_layout.addWidget(self.dt_spin)
        fluid_layout.addLayout(dt_layout)
        
        fluid_tab.setLayout(fluid_layout)
        self.tab_widget.addTab(fluid_tab, "流体")
        
        # 反应扩散参数选项卡
        rd_tab = QWidget()
        rd_layout = QVBoxLayout()
        
        # 反应速率 F
        rd_f_layout = QHBoxLayout()
        rd_f_layout.addWidget(QLabel("反应速率 F:"))
        self.rd_f_spin = QDoubleSpinBox()
        self.rd_f_spin.setRange(0.01, 0.1)
        self.rd_f_spin.setSingleStep(0.001)
        self.rd_f_spin.setValue(self.generator.params['rd_f'])
        self.rd_f_spin.valueChanged.connect(self.on_rd_f_changed)
        rd_f_layout.addWidget(self.rd_f_spin)
        rd_layout.addLayout(rd_f_layout)
        
        # 反应速率 K
        rd_k_layout = QHBoxLayout()
        rd_k_layout.addWidget(QLabel("反应速率 K:"))
        self.rd_k_spin = QDoubleSpinBox()
        self.rd_k_spin.setRange(0.01, 0.1)
        self.rd_k_spin.setSingleStep(0.001)
        self.rd_k_spin.setValue(self.generator.params['rd_k'])
        self.rd_k_spin.valueChanged.connect(self.on_rd_k_changed)
        rd_k_layout.addWidget(self.rd_k_spin)
        rd_layout.addLayout(rd_k_layout)
        
        rd_tab.setLayout(rd_layout)
        self.tab_widget.addTab(rd_tab, "反应扩散")
        
        # 分形参数选项卡
        fractal_tab = QWidget()
        fractal_layout = QVBoxLayout()
        
        # 分形迭代
        fractal_layout = QHBoxLayout()
        fractal_layout.addWidget(QLabel("分形迭代:"))
        self.fractal_iter_spin = QSpinBox()
        self.fractal_iter_spin.setRange(10, 500)
        self.fractal_iter_spin.setValue(self.generator.params['fractal_iterations'])
        self.fractal_iter_spin.valueChanged.connect(self.on_fractal_iter_changed)
        fractal_layout.addWidget(self.fractal_iter_spin)
        fractal_tab.setLayout(fractal_layout)
        self.tab_widget.addTab(fractal_tab, "分形")
        
        # 粒子参数选项卡
        particle_tab = QWidget()
        particle_layout = QVBoxLayout()
        
        # 粒子数量
        particle_layout = QHBoxLayout()
        particle_layout.addWidget(QLabel("粒子数量:"))
        self.particle_spin = QSpinBox()
        self.particle_spin.setRange(10, 2000)
        self.particle_spin.setValue(self.generator.params['particle_count'])
        self.particle_spin.valueChanged.connect(self.on_particle_count_changed)
        particle_layout.addWidget(self.particle_spin)
        particle_tab.setLayout(particle_layout)
        self.tab_widget.addTab(particle_tab, "粒子")
        
        # 其他参数选项卡
        other_tab = QWidget()
        other_layout = QVBoxLayout()
        
        # 波动速度
        wave_layout = QHBoxLayout()
        wave_layout.addWidget(QLabel("波动速度:"))
        self.wave_speed_spin = QDoubleSpinBox()
        self.wave_speed_spin.setRange(0.1, 2.0)
        self.wave_speed_spin.setSingleStep(0.1)
        self.wave_speed_spin.setValue(self.generator.params['wave_speed'])
        self.wave_speed_spin.valueChanged.connect(self.on_wave_speed_changed)
        wave_layout.addWidget(self.wave_speed_spin)
        other_layout.addLayout(wave_layout)
        
        # 量子尺度
        quantum_layout = QHBoxLayout()
        quantum_layout.addWidget(QLabel("量子尺度:"))
        self.quantum_scale_spin = QDoubleSpinBox()
        self.quantum_scale_spin.setRange(0.1, 5.0)
        self.quantum_scale_spin.setSingleStep(0.1)
        self.quantum_scale_spin.setValue(self.generator.params['quantum_scale'])
        self.quantum_scale_spin.valueChanged.connect(self.on_quantum_scale_changed)
        quantum_layout.addWidget(self.quantum_scale_spin)
        other_layout.addLayout(quantum_layout)
        
        # 元胞自动机规则
        ca_layout = QHBoxLayout()
        ca_layout.addWidget(QLabel("CA规则:"))
        self.ca_rule_spin = QSpinBox()
        self.ca_rule_spin.setRange(0, 255)
        self.ca_rule_spin.setValue(self.generator.params['ca_rule'])
        self.ca_rule_spin.valueChanged.connect(self.on_ca_rule_changed)
        ca_layout.addWidget(self.ca_rule_spin)
        other_layout.addLayout(ca_layout)
        
        other_tab.setLayout(other_layout)
        self.tab_widget.addTab(other_tab, "其他")
        
        layout.addWidget(self.tab_widget)
        
        # 控制按钮
        button_layout = QHBoxLayout()
        
        self.reset_btn = QPushButton("重置效果")
        self.reset_btn.clicked.connect(self.on_reset_clicked)
        button_layout.addWidget(self.reset_btn)
        
        self.screenshot_btn = QPushButton("截图")
        self.screenshot_btn.clicked.connect(self.on_screenshot_clicked)
        button_layout.addWidget(self.screenshot_btn)
        
        layout.addLayout(button_layout)
        
        # 性能显示
        self.fps_label = QLabel("FPS: --")
        layout.addWidget(self.fps_label)
        
        layout.addStretch()
        self.setLayout(layout)
        
        # 初始化定时器用于FPS计算
        self.frame_count = 0
        self.fps_timer = QTimer()
        self.fps_timer.timeout.connect(self.update_fps)
        self.fps_timer.start(1000)  # 每秒更新一次
    
    def update_fps(self):
        """更新FPS显示"""
        fps = self.frame_count
        self.fps_label.setText(f"FPS: {fps}")
        self.frame_count = 0
    
    def increment_frame_count(self):
        """增加帧计数"""
        self.frame_count += 1
    
    def on_effect_changed(self, effect):
        """效果改变回调"""
        self.generator.current_effect = effect
    
    def on_viscosity_changed(self, value):
        """粘度改变回调"""
        self.generator.params['fluid_viscosity'] = value / 1000000.0
    
    def on_dt_changed(self, value):
        """时间步长改变回调"""
        self.generator.params['fluid_dt'] = value
    
    def on_rd_f_changed(self, value):
        """反应速率F改变回调"""
        self.generator.params['rd_f'] = value
    
    def on_rd_k_changed(self, value):
        """反应速率K改变回调"""
        self.generator.params['rd_k'] = value
    
    def on_fractal_iter_changed(self, value):
        """分形迭代次数改变回调"""
        self.generator.params['fractal_iterations'] = value
    
    def on_particle_count_changed(self, value):
        """粒子数量改变回调"""
        self.generator.params['particle_count'] = value
        self.generator.init_particles()
    
    def on_wave_speed_changed(self, value):
        """波动速度改变回调"""
        self.generator.params['wave_speed'] = value
    
    def on_quantum_scale_changed(self, value):
        """量子尺度改变回调"""
        self.generator.params['quantum_scale'] = value
    
    def on_ca_rule_changed(self, value):
        """元胞自动机规则改变回调"""
        self.generator.params['ca_rule'] = value
    
    def on_reset_clicked(self):
        """重置效果"""
        # 重新初始化相关系统
        if self.generator.current_effect == "fluid_simulation":
            self.generator.init_fluid_simulation()
        elif self.generator.current_effect == "reaction_diffusion":
            self.generator.init_reaction_diffusion()
        elif self.generator.current_effect == "lorenz_attractor":
            self.generator.init_chaos_system()
        elif self.generator.current_effect == "particle_system":
            self.generator.init_particle_system()
        elif self.generator.current_effect == "wave_equation":
            self.generator.init_wave_system()
        elif self.generator.current_effect == "cellular_automata":
            self.generator.init_cellular_automata()
        elif self.generator.current_effect == "fractal_flame":
            self.generator.init_fractal_flame()
        elif self.generator.current_effect == "strange_attractor":
            self.generator.init_strange_attractor()
    
    def on_screenshot_clicked(self):
        """截图回调"""
        self.parent().take_screenshot()

class MainWindow(QMainWindow):
    """主窗口"""
    def __init__(self):
        super().__init__()
        self.generator = AdvancedMathVisualGenerator()
        self.camera = CameraThread()
        self.use_camera = False
        self.init_ui()
        self.init_timer()
    
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("高级数学视觉生成器 - 增强版")
        self.setGeometry(100, 100, 1400, 900)
        
        # 中央组件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QHBoxLayout()
        
        # 视频显示区域
        self.video_display = VideoDisplayWidget()
        
        # 控制面板
        self.control_panel = ControlPanel(self.generator, self)
        
        # 分割器
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self.video_display)
        splitter.addWidget(self.control_panel)
        splitter.setSizes([1000, 400])
        
        main_layout.addWidget(splitter)
        central_widget.setLayout(main_layout)
        
        # 菜单栏
        self.create_menu_bar()
        
        # 状态栏
        self.statusBar().showMessage("就绪")
        
        # 连接鼠标事件
        self.video_display.mouseMoved.connect(self.on_mouse_moved)
        self.video_display.mousePressed.connect(self.on_mouse_pressed)
    
    def create_menu_bar(self):
        """创建菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu('文件')
        
        screenshot_action = file_menu.addAction('截图')
        screenshot_action.triggered.connect(self.take_screenshot)
        
        export_video_action = file_menu.addAction('导出视频')
        export_video_action.triggered.connect(self.export_video)
        
        file_menu.addSeparator()
        
        exit_action = file_menu.addAction('退出')
        exit_action.triggered.connect(self.close)
        
        # 视图菜单
        view_menu = menubar.addMenu('视图')
        
        camera_action = view_menu.addAction('使用摄像头')
        camera_action.setCheckable(True)
        camera_action.triggered.connect(self.toggle_camera)
        
        fullscreen_action = view_menu.addAction('全屏')
        fullscreen_action.triggered.connect(self.toggle_fullscreen)
    
    def init_timer(self):
        """初始化定时器"""
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(33)  # 约30fps
    
    def toggle_camera(self, checked):
        """切换摄像头使用"""
        self.use_camera = checked
        if checked:
            if not self.camera.start():
                self.statusBar().showMessage("无法打开摄像头")
                self.use_camera = False
            else:
                self.statusBar().showMessage("摄像头已开启")
        else:
            self.camera.stop()
            self.statusBar().showMessage("摄像头已关闭")
    
    def toggle_fullscreen(self):
        """切换全屏"""
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()
    
    def on_mouse_moved(self, x, y):
        """鼠标移动事件"""
        self.generator.set_mouse_position(x, y, self.generator.mouse_pressed)
    
    def on_mouse_pressed(self, x, y, pressed):
        """鼠标按下/释放事件"""
        self.generator.set_mouse_position(x, y, pressed)
    
    def update_frame(self):
        """更新帧"""
        if self.use_camera:
            if self.camera.read_frame():
                frame = self.camera.frame
                # 处理摄像头帧
                processed_frame = self.generator.process_frame(frame)
                self.video_display.update_image(processed_frame)
        else:
            # 生成数学效果
            processed_frame = self.generator.process_frame()
            self.video_display.update_image(processed_frame)
        
        # 更新FPS计数
        self.control_panel.increment_frame_count()
    
    def take_screenshot(self):
        """截图"""
        # 获取当前显示的图像
        pixmap = self.video_display.image_label.pixmap()
        if pixmap:
            from datetime import datetime
            filename = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            pixmap.save(filename)
            self.statusBar().showMessage(f"截图已保存: {filename}")
    
    def export_video(self):
        """导出视频"""
        # 这个功能需要更复杂的实现
        QMessageBox.information(self, "导出视频", "视频导出功能需要额外的实现")
    
    def closeEvent(self, event):
        """关闭事件"""
        self.camera.stop()
        event.accept()

def main():
    app = QApplication(sys.argv)
    app.setFont(QFont("Arial", 10))
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()