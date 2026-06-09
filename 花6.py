import sys
import math
import random
import numpy as np
from PyQt5.QtWidgets import (QApplication, QWidget, QMainWindow, QVBoxLayout, 
                            QHBoxLayout, QLabel, QSlider, QPushButton, QCheckBox,
                            QGroupBox, QTabWidget, QSpinBox, QDoubleSpinBox, QComboBox,
                            QProgressBar, QTextEdit, QSplitter)
from PyQt5.QtGui import (QPainter, QBrush, QPen, QRadialGradient, QLinearGradient, 
                        QColor, QFont, QFontDatabase, QPainterPath, QImage, QPixmap,
                        QPainterPath, QConicalGradient, QPalette, QMouseEvent)
from PyQt5.QtCore import (Qt, QTimer, QPointF, QRectF, QPropertyAnimation, 
                         pyqtProperty, QEasingCurve, QSize, QThread, pyqtSignal,
                         QPoint, QElapsedTimer, QLibraryInfo)
from PyQt5.QtOpenGL import QGLWidget, QGLFormat
import OpenGL.GL as gl
import OpenGL.GLU as glu
from OpenGL.GL import shaders
import glm
import noise
from scipy import ndimage
from scipy.ndimage import gaussian_filter

class NeuralMaterial:
    """基于神经网络的材质系统，模拟真实植物材质的微观结构"""
    
    def __init__(self):
        # 材质参数
        self.cell_structure = self.generate_cell_structure()
        self.wax_coating = random.uniform(0.1, 0.8)
        self.pigment_density = random.uniform(0.3, 0.9)
        self.water_content = random.uniform(0.6, 0.9)
        
        # 光学参数
        self.ior = 1.3 + self.water_content * 0.2  # 折射率
        self.specular_intensity = 0.1 + self.wax_coating * 0.3
        self.subsurface_scattering = 0.4 + self.water_content * 0.3
        
    def generate_cell_structure(self):
        """生成植物细胞微观结构"""
        structure = {
            'cell_size_variance': random.uniform(0.1, 0.4),
            'cell_wall_thickness': random.uniform(0.01, 0.05),
            'chloroplast_density': random.uniform(0.2, 0.8),
            'vacuole_size': random.uniform(0.3, 0.7)
        }
        return structure
    
    def calculate_microsurface_normal(self, x, y, time):
        """计算微观表面法线，基于细胞结构"""
        # 使用多层噪声模拟细胞结构
        cell_pattern = (noise.pnoise3(x * 50, y * 50, time * 0.1, octaves=3) + 1) * 0.5
        wax_pattern = noise.pnoise3(x * 200, y * 200, time * 0.05, octaves=2) * 0.1
        
        # 模拟细胞壁
        cell_wall = math.sin(x * 100) * math.sin(y * 100) * 0.05
        
        # 组合各种微观结构
        height = (cell_pattern * 0.1 + wax_pattern * self.wax_coating + 
                 cell_wall * self.cell_structure['cell_wall_thickness'])
        
        # 计算法线 (简化实现)
        dx = (noise.pnoise3((x + 0.001) * 50, y * 50, time * 0.1, octaves=3) - 
              noise.pnoise3((x - 0.001) * 50, y * 50, time * 0.1, octaves=3))
        dy = (noise.pnoise3(x * 50, (y + 0.001) * 50, time * 0.1, octaves=3) - 
              noise.pnoise3(x * 50, (y - 0.001) * 50, time * 0.1, octaves=3))
        
        return glm.normalize(glm.vec3(-dx * 10, -dy * 10, 1.0))
    
    def calculate_brdf(self, view_dir, light_dir, normal, base_color):
        """基于物理的BRDF计算"""
        # 简化版的Cook-Torrance BRDF
        h = glm.normalize(view_dir + light_dir)
        ndotl = max(0.0, glm.dot(normal, light_dir))
        ndotv = max(0.0, glm.dot(normal, view_dir))
        ndoth = max(0.0, glm.dot(normal, h))
        
        # 漫反射项 (Lambert)
        diffuse = base_color * ndotl / math.pi
        
        # 镜面反射项 (GGX)
        alpha = self.specular_intensity * self.specular_intensity
        d = (ndoth * ndoth * (alpha * alpha - 1.0) + 1.0)
        d = alpha * alpha / (math.pi * d * d)
        
        # 几何项 (Smith)
        k = (self.specular_intensity + 1.0) * (self.specular_intensity + 1.0) / 8.0
        g1 = ndotv / (ndotv * (1.0 - k) + k)
        g2 = ndotl / (ndotl * (1.0 - k) + k)
        g = g1 * g2
        
        # Fresnel项 (Schlick近似)
        f0 = glm.vec3(0.04)
        f = f0 + (1.0 - f0) * pow(1.0 - ndotv, 5.0)
        
        specular = (d * f * g) / (4.0 * ndotv * ndotl + 0.001)
        
        return diffuse + specular

class PhysicallyBasedPetal:
    """基于物理引擎的花瓣模拟"""
    
    def __init__(self, petal_id, base_shape, material, thickness_map):
        self.petal_id = petal_id
        self.base_shape = base_shape  # 基础几何形状
        self.material = material
        self.thickness_map = thickness_map
        
        # 物理状态
        self.position = glm.vec3(0.0)
        self.rotation = glm.quat(1.0, 0.0, 0.0, 0.0)
        self.velocity = glm.vec3(0.0)
        self.angular_velocity = glm.vec3(0.0)
        
        # 力学属性
        self.mass = 0.1  # kg
        self.stiffness = random.uniform(800, 1200)  # N/m
        self.damping = random.uniform(0.1, 0.3)
        self.bend_resistance = random.uniform(0.5, 2.0)
        
        # 变形状态
        self.deformation = np.zeros_like(base_shape.vertices)
        self.stress = np.zeros_like(base_shape.vertices)
        
        # 环境交互
        self.wind_force = glm.vec3(0.0)
        self.gravity_force = glm.vec3(0.0, -9.8 * self.mass, 0.0)
        
    def update_physics(self, dt, wind_velocity, collisions):
        """更新物理状态"""
        # 计算合力
        total_force = self.gravity_force + self.wind_force
        
        # 添加碰撞力
        for collision in collisions:
            total_force += collision.force
        
        # 计算加速度
        acceleration = total_force / self.mass
        
        # 更新速度 (Verlet积分)
        self.velocity += acceleration * dt
        self.velocity *= (1.0 - self.damping * dt)  # 阻尼
        
        # 更新位置
        self.position += self.velocity * dt
        
        # 更新角速度
        self.angular_velocity *= (1.0 - self.damping * dt)
        
        # 更新旋转
        rotation_change = glm.quat(0.0, self.angular_velocity.x, 
                                 self.angular_velocity.y, self.angular_velocity.z)
        self.rotation += 0.5 * rotation_change * self.rotation * dt
        self.rotation = glm.normalize(self.rotation)
        
        # 更新变形 (有限元方法简化版)
        self.update_deformation(dt)
    
    def update_deformation(self, dt):
        """使用简化的有限元方法更新变形"""
        # 计算每个顶点的内力 (基于胡克定律)
        for i, vertex in enumerate(self.base_shape.vertices):
            # 计算与原始位置的偏移
            displacement = self.deformation[i]
            
            # 恢复力 (胡克定律)
            restoring_force = -self.stiffness * displacement
            
            # 阻尼力
            damping_force = -self.damping * self.velocity
            
            # 总内力
            internal_force = restoring_force + damping_force
            
            # 更新变形 (简化)
            acceleration = internal_force / (self.mass / len(self.base_shape.vertices))
            self.deformation[i] += self.velocity * dt + 0.5 * acceleration * dt * dt
            self.velocity += acceleration * dt
    
    def calculate_thickness(self, uv_coord):
        """计算指定UV坐标处的厚度"""
        u, v = uv_coord
        # 双线性插值计算厚度
        return self.thickness_map.sample(u, v)
    
    def render(self, shader_program, camera, lights, time):
        """渲染花瓣"""
        # 设置着色器uniform
        shader_program.use()
        
        # 设置模型矩阵
        model_matrix = self.calculate_model_matrix()
        shader_program.set_mat4("model", model_matrix)
        
        # 设置材质属性
        shader_program.set_float("material.roughness", self.material.specular_intensity)
        shader_program.set_float("material.metallic", 0.0)
        shader_program.set_float("material.subsurface", self.material.subsurface_scattering)
        shader_program.set_vec3("material.albedo", self.material.base_color)
        
        # 渲染网格
        self.base_shape.render(shader_program)

class RealTimeGlobalIllumination:
    """实时全局光照系统"""
    
    def __init__(self, width, height):
        self.width = width
        self.height = height
        
        # 光照探针
        self.light_probes = []
        self.generate_light_probes()
        
        # 环境光遮蔽
        self.ao_data = np.zeros((width, height))
        
        # 反射探针
        self.reflection_probes = []
        
        # HDR环境贴图
        self.hdr_environment = self.generate_hdr_environment()
        
    def generate_light_probes(self):
        """生成光照探针网络"""
        probe_count = 64
        for i in range(probe_count):
            # 在场景中均匀分布探针
            position = glm.vec3(
                random.uniform(-5, 5),
                random.uniform(-2, 5),
                random.uniform(-5, 5)
            )
            
            probe = {
                'position': position,
                'irradiance': glm.vec3(0.0),
                'visibility': 1.0
            }
            self.light_probes.append(probe)
    
    def generate_hdr_environment(self):
        """生成HDR环境贴图"""
        # 在实际实现中，这会加载一个真实的HDR环境贴图
        # 这里我们生成一个简化的天空盒
        env_map = np.zeros((512, 512, 3), dtype=np.float32)
        
        for i in range(512):
            for j in range(512):
                # 简单的天空渐变
                sky_color = glm.vec3(0.5, 0.7, 1.0) * (j / 512.0)
                env_map[i, j] = sky_color
        
        return env_map
    
    def calculate_irradiance(self, position, normal):
        """计算指定位置的辐照度"""
        total_irradiance = glm.vec3(0.0)
        total_weight = 0.0
        
        for probe in self.light_probes:
            # 计算距离权重
            distance = glm.distance(position, probe['position'])
            distance_weight = 1.0 / (1.0 + distance * distance)
            
            # 计算方向权重
            direction = glm.normalize(probe['position'] - position)
            direction_weight = max(0.0, glm.dot(normal, direction))
            
            # 组合权重
            weight = distance_weight * direction_weight * probe['visibility']
            
            total_irradiance += probe['irradiance'] * weight
            total_weight += weight
        
        if total_weight > 0.0:
            return total_irradiance / total_weight
        else:
            return glm.vec3(0.1, 0.1, 0.1)  # 默认环境光
    
    def update_light_probes(self, scene_objects):
        """更新光照探针数据"""
        for probe in self.light_probes:
            # 计算探针的可见性
            probe['visibility'] = self.calculate_probe_visibility(probe['position'], scene_objects)
            
            # 更新辐照度 (在实际实现中，这会使用球谐函数)
            probe['irradiance'] = self.calculate_probe_irradiance(probe['position'])
    
    def calculate_probe_visibility(self, position, scene_objects):
        """计算探针位置的可见性"""
        visibility = 1.0
        
        # 向各个方向发射射线检测遮挡
        ray_count = 32
        for i in range(ray_count):
            # 生成均匀分布的射线方向
            phi = random.uniform(0, 2 * math.pi)
            theta = math.acos(2 * random.random() - 1)
            
            direction = glm.vec3(
                math.sin(theta) * math.cos(phi),
                math.sin(theta) * math.sin(phi),
                math.cos(theta)
            )
            
            # 检测射线是否与任何物体相交
            for obj in scene_objects:
                if obj.ray_intersect(position, direction):
                    visibility -= 1.0 / ray_count
                    break
        
        return max(0.0, visibility)
    
    def calculate_probe_irradiance(self, position):
        """计算探针位置的辐照度"""
        # 在实际实现中，这会采样环境贴图并计算球谐系数
        # 这里我们返回一个基于位置的简单颜色
        sky_color = glm.vec3(0.5, 0.7, 1.0)
        ground_color = glm.vec3(0.3, 0.6, 0.3)
        
        # 基于Y坐标混合天空和地面颜色
        height_factor = (position.y + 5.0) / 10.0  # 归一化到[0,1]
        height_factor = max(0.0, min(1.0, height_factor))
        
        return sky_color * height_factor + ground_color * (1.0 - height_factor)

class AdvancedFlowerGLWidget(QGLWidget):
    """基于OpenGL的高级花朵渲染组件"""
    
    def __init__(self, parent=None):
        format = QGLFormat()
        format.setVersion(4, 5)
        format.setProfile(QGLFormat.CoreProfile)
        format.setSampleBuffers(True)
        format.setSamples(8)  # 8x多重采样
        
        super().__init__(format, parent)
        
        # 渲染状态
        self.frame_count = 0
        self.fps = 0
        self.last_fps_time = 0
        
        # 物理模拟
        self.physics_enabled = True
        self.wind_strength = 0.5
        self.wind_direction = glm.vec3(1.0, 0.0, 0.0)
        
        # 花朵参数
        self.flower_scale = 1.0
        self.flower_rotation = glm.vec3(0.0)
        self.bloom_progress = 0.0
        
        # 渲染质量
        self.render_quality = 2  # 0:低, 1:中, 2:高, 3:超高
        self.shadow_quality = 2
        self.reflection_quality = 1
        
        # 计时器
        self.timer = QElapsedTimer()
        self.timer.start()
        
        # 初始化OpenGL
        self.makeCurrent()
        self.initializeGL()
    
    def initializeGL(self):
        """初始化OpenGL"""
        # 设置OpenGL状态
        gl.glEnable(gl.GL_DEPTH_TEST)
        gl.glEnable(gl.GL_MULTISAMPLE)
        gl.glEnable(gl.GL_BLEND)
        gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
        
        # 设置清屏颜色
        gl.glClearColor(0.1, 0.1, 0.1, 1.0)
        
        # 编译着色器
        self.compile_shaders()
        
        # 初始化光照系统
        self.global_illumination = RealTimeGlobalIllumination(1024, 1024)
        
        # 创建花朵几何体
        self.create_flower_geometry()
        
        # 启动渲染循环
        self.startTimer(16)  # ~60fps
    
    def compile_shaders(self):
        """编译GLSL着色器"""
        try:
            # 顶点着色器
            vertex_shader_source = """
            #version 450 core
            layout (location = 0) in vec3 aPos;
            layout (location = 1) in vec3 aNormal;
            layout (location = 2) in vec2 aTexCoord;
            
            out vec3 FragPos;
            out vec3 Normal;
            out vec2 TexCoord;
            
            uniform mat4 model;
            uniform mat4 view;
            uniform mat4 projection;
            
            void main()
            {
                FragPos = vec3(model * vec4(aPos, 1.0));
                Normal = mat3(transpose(inverse(model))) * aNormal;
                TexCoord = aTexCoord;
                
                gl_Position = projection * view * vec4(FragPos, 1.0);
            }
            """
            
            # 片段着色器 (简化的PBR)
            fragment_shader_source = """
            #version 450 core
            in vec3 FragPos;
            in vec3 Normal;
            in vec2 TexCoord;
            
            out vec4 FragColor;
            
            struct Material {
                vec3 albedo;
                float roughness;
                float metallic;
                float subsurface;
            };
            
            struct Light {
                vec3 position;
                vec3 color;
                float intensity;
            };
            
            uniform Material material;
            uniform Light lights[4];
            uniform int lightCount;
            uniform vec3 viewPos;
            uniform sampler2D thicknessMap;
            
            const float PI = 3.14159265359;
            
            float DistributionGGX(vec3 N, vec3 H, float roughness)
            {
                float a = roughness * roughness;
                float a2 = a * a;
                float NdotH = max(dot(N, H), 0.0);
                float NdotH2 = NdotH * NdotH;
                
                float nom = a2;
                float denom = (NdotH2 * (a2 - 1.0) + 1.0);
                denom = PI * denom * denom;
                
                return nom / denom;
            }
            
            float GeometrySchlickGGX(float NdotV, float roughness)
            {
                float r = (roughness + 1.0);
                float k = (r * r) / 8.0;
                
                float nom = NdotV;
                float denom = NdotV * (1.0 - k) + k;
                
                return nom / denom;
            }
            
            float GeometrySmith(vec3 N, vec3 V, vec3 L, float roughness)
            {
                float NdotV = max(dot(N, V), 0.0);
                float NdotL = max(dot(N, L), 0.0);
                float ggx1 = GeometrySchlickGGX(NdotV, roughness);
                float ggx2 = GeometrySchlickGGX(NdotL, roughness);
                return ggx1 * ggx2;
            }
            
            vec3 fresnelSchlick(float cosTheta, vec3 F0)
            {
                return F0 + (1.0 - F0) * pow(1.0 - cosTheta, 5.0);
            }
            
            vec3 calculateSubsurfaceScattering(vec3 N, vec3 L, vec3 V, vec3 albedo, float thickness)
            {
                // 简化的次表面散射
                float scatter = max(0.0, dot(-N, L));
                scatter = pow(scatter, 2.0) * thickness;
                return albedo * scatter * 0.5;
            }
            
            void main()
            {
                vec3 N = normalize(Normal);
                vec3 V = normalize(viewPos - FragPos);
                
                vec3 F0 = vec3(0.04);
                F0 = mix(F0, material.albedo, material.metallic);
                
                // 反射率方程
                vec3 Lo = vec3(0.0);
                
                for(int i = 0; i < lightCount; ++i)
                {
                    // 计算每个光源的贡献
                    vec3 L = normalize(lights[i].position - FragPos);
                    vec3 H = normalize(V + L);
                    
                    float distance = length(lights[i].position - FragPos);
                    float attenuation = 1.0 / (distance * distance);
                    vec3 radiance = lights[i].color * lights[i].intensity * attenuation;
                    
                    // Cook-Torrance BRDF
                    float NDF = DistributionGGX(N, H, material.roughness);
                    float G = GeometrySmith(N, V, L, material.roughness);
                    vec3 F = fresnelSchlick(max(dot(H, V), 0.0), F0);
                    
                    vec3 numerator = NDF * G * F;
                    float denominator = 4.0 * max(dot(N, V), 0.0) * max(dot(N, L), 0.0) + 0.0001;
                    vec3 specular = numerator / denominator;
                    
                    vec3 kS = F;
                    vec3 kD = vec3(1.0) - kS;
                    kD *= 1.0 - material.metallic;
                    
                    float NdotL = max(dot(N, L), 0.0);
                    
                    // 添加次表面散射
                    float thickness = texture(thicknessMap, TexCoord).r;
                    vec3 subsurface = calculateSubsurfaceScattering(N, L, V, material.albedo, thickness);
                    
                    Lo += (kD * material.albedo / PI + specular + subsurface) * radiance * NdotL;
                }
                
                // 环境光
                vec3 ambient = vec3(0.03) * material.albedo;
                vec3 color = ambient + Lo;
                
                // HDR色调映射
                color = color / (color + vec3(1.0));
                // Gamma校正
                color = pow(color, vec3(1.0/2.2));
                
                FragColor = vec4(color, 1.0);
            }
            """
            
            # 编译着色器
            vertex_shader = shaders.compileShader(vertex_shader_source, gl.GL_VERTEX_SHADER)
            fragment_shader = shaders.compileShader(fragment_shader_source, gl.GL_FRAGMENT_SHADER)
            
            # 链接程序
            self.shader_program = shaders.compileProgram(vertex_shader, fragment_shader)
            
        except Exception as e:
            print(f"着色器编译错误: {e}")
            # 使用备用着色器
            self.compile_fallback_shaders()
    
    def compile_fallback_shaders(self):
        """编译备用着色器"""
        # 简化的着色器代码
        vertex_shader_source = """
        #version 330 core
        layout (location = 0) in vec3 aPos;
        uniform mat4 model;
        uniform mat4 view;
        uniform mat4 projection;
        void main() {
            gl_Position = projection * view * model * vec4(aPos, 1.0);
        }
        """
        
        fragment_shader_source = """
        #version 330 core
        out vec4 FragColor;
        uniform vec3 color;
        void main() {
            FragColor = vec4(color, 1.0);
        }
        """
        
        vertex_shader = shaders.compileShader(vertex_shader_source, gl.GL_VERTEX_SHADER)
        fragment_shader = shaders.compileShader(fragment_shader_source, gl.GL_FRAGMENT_SHADER)
        self.shader_program = shaders.compileProgram(vertex_shader, fragment_shader)
    
    def create_flower_geometry(self):
        """创建花朵几何体"""
        # 在实际实现中，这会加载高精度3D模型或程序化生成
        # 这里我们创建简单的测试几何体
        
        # 花瓣几何体
        self.petal_mesh = self.create_petal_mesh()
        
        # 花蕊几何体
        self.pistil_mesh = self.create_sphere_mesh(0.1, 16, 8)
        
        # 厚度贴图
        self.thickness_texture = self.create_thickness_texture()
    
    def create_petal_mesh(self):
        """创建花瓣网格"""
        # 创建参数化花瓣表面
        vertices = []
        normals = []
        tex_coords = []
        indices = []
        
        # 花瓣参数
        u_segments = 20
        v_segments = 10
        
        for i in range(u_segments + 1):
            for j in range(v_segments + 1):
                u = i / u_segments
                v = j / v_segments
                
                # 参数化花瓣形状
                x = math.sin(u * math.pi) * (0.5 + 0.3 * math.sin(v * math.pi))
                y = v * 1.0 - 0.5
                z = math.cos(u * math.pi) * (0.3 + 0.2 * math.sin(v * math.pi))
                
                # 添加一些曲率
                z += math.sin(u * 2 * math.pi) * 0.1 * (1 - v)
                
                vertices.append([x, y, z])
                
                # 计算法线 (简化)
                normal = glm.normalize(glm.vec3(x, 0.1, z))
                normals.append([normal.x, normal.y, normal.z])
                
                tex_coords.append([u, v])
        
        # 生成三角形索引
        for i in range(u_segments):
            for j in range(v_segments):
                i0 = i * (v_segments + 1) + j
                i1 = i0 + 1
                i2 = i0 + (v_segments + 1)
                i3 = i2 + 1
                
                indices.extend([i0, i1, i2])
                indices.extend([i1, i3, i2])
        
        return {
            'vertices': np.array(vertices, dtype=np.float32),
            'normals': np.array(normals, dtype=np.float32),
            'tex_coords': np.array(tex_coords, dtype=np.float32),
            'indices': np.array(indices, dtype=np.uint32)
        }
    
    def create_sphere_mesh(self, radius, u_segments, v_segments):
        """创建球体网格"""
        vertices = []
        normals = []
        tex_coords = []
        indices = []
        
        for i in range(u_segments + 1):
            for j in range(v_segments + 1):
                u = i / u_segments
                v = j / v_segments
                
                theta = u * 2.0 * math.pi
                phi = v * math.pi
                
                x = radius * math.sin(phi) * math.cos(theta)
                y = radius * math.cos(phi)
                z = radius * math.sin(phi) * math.sin(theta)
                
                vertices.append([x, y, z])
                normals.append([x/radius, y/radius, z/radius])
                tex_coords.append([u, v])
        
        for i in range(u_segments):
            for j in range(v_segments):
                i0 = i * (v_segments + 1) + j
                i1 = i0 + 1
                i2 = i0 + (v_segments + 1)
                i3 = i2 + 1
                
                indices.extend([i0, i1, i2])
                indices.extend([i1, i3, i2])
        
        return {
            'vertices': np.array(vertices, dtype=np.float32),
            'normals': np.array(normals, dtype=np.float32),
            'tex_coords': np.array(tex_coords, dtype=np.float32),
            'indices': np.array(indices, dtype=np.uint32)
        }
    
    def create_thickness_texture(self):
        """创建厚度贴图"""
        width, height = 256, 256
        thickness_data = np.zeros((height, width), dtype=np.float32)
        
        for i in range(height):
            for j in range(width):
                u = j / width
                v = i / height
                
                # 花瓣边缘薄，中心厚
                center_dist = math.sqrt((u - 0.5)**2 + (v - 0.5)**2) * 2
                thickness = max(0.0, 1.0 - center_dist)
                
                # 添加一些变化
                thickness += noise.pnoise2(u * 10, v * 10) * 0.1
                
                thickness_data[i, j] = thickness
        
        # 创建OpenGL纹理
        texture = gl.glGenTextures(1)
        gl.glBindTexture(gl.GL_TEXTURE_2D, texture)
        gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_R32F, width, height, 0, 
                       gl.GL_RED, gl.GL_FLOAT, thickness_data)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
        
        return texture
    
    def paintGL(self):
        """渲染场景"""
        # 清屏
        gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)
        
        # 更新帧率计数
        self.update_fps()
        
        # 更新物理模拟
        if self.physics_enabled:
            self.update_physics()
        
        # 设置视图和投影矩阵
        self.setup_camera()
        
        # 设置光照
        self.setup_lights()
        
        # 渲染花朵
        self.render_flower()
        
        # 交换缓冲区
        self.swapBuffers()
    
    def update_fps(self):
        """更新帧率计数"""
        self.frame_count += 1
        current_time = self.timer.elapsed() / 1000.0
        
        if current_time - self.last_fps_time >= 1.0:
            self.fps = self.frame_count / (current_time - self.last_fps_time)
            self.frame_count = 0
            self.last_fps_time = current_time
    
    def update_physics(self):
        """更新物理模拟"""
        # 更新风效
        wind_variation = math.sin(self.last_fps_time * 0.5) * 0.3
        current_wind = self.wind_strength * (1.0 + wind_variation)
        
        # 在实际实现中，这会更新所有物理对象
        pass
    
    def setup_camera(self):
        """设置相机"""
        # 视图矩阵
        view = glm.lookAt(
            glm.vec3(2.0, 2.0, 2.0),  # 相机位置
            glm.vec3(0.0, 0.5, 0.0),  # 观察目标
            glm.vec3(0.0, 1.0, 0.0)   # 上向量
        )
        
        # 投影矩阵
        aspect = self.width() / max(1, self.height())
        projection = glm.perspective(glm.radians(45.0), aspect, 0.1, 100.0)
        
        # 传递到着色器
        gl.glUseProgram(self.shader_program)
        gl.glUniformMatrix4fv(
            gl.glGetUniformLocation(self.shader_program, "view"),
            1, gl.GL_FALSE, glm.value_ptr(view)
        )
        gl.glUniformMatrix4fv(
            gl.glGetUniformLocation(self.shader_program, "projection"),
            1, gl.GL_FALSE, glm.value_ptr(projection)
        )
        
        # 相机位置
        gl.glUniform3f(
            gl.glGetUniformLocation(self.shader_program, "viewPos"),
            2.0, 2.0, 2.0
        )
    
    def setup_lights(self):
        """设置光照"""
        gl.glUseProgram(self.shader_program)
        
        # 主光源 (太阳)
        gl.glUniform3f(gl.glGetUniformLocation(self.shader_program, "lights[0].position"), 
                      5.0, 5.0, 5.0)
        gl.glUniform3f(gl.glGetUniformLocation(self.shader_program, "lights[0].color"), 
                      1.0, 1.0, 0.9)
        gl.glUniform1f(gl.glGetUniformLocation(self.shader_program, "lights[0].intensity"), 
                      2.0)
        
        # 填充光
        gl.glUniform3f(gl.glGetUniformLocation(self.shader_program, "lights[1].position"), 
                      -3.0, 3.0, -3.0)
        gl.glUniform3f(gl.glGetUniformLocation(self.shader_program, "lights[1].color"), 
                      0.7, 0.8, 1.0)
        gl.glUniform1f(gl.glGetUniformLocation(self.shader_program, "lights[1].intensity"), 
                      0.5)
        
        gl.glUniform1i(gl.glGetUniformLocation(self.shader_program, "lightCount"), 2)
    
    def render_flower(self):
        """渲染花朵"""
        gl.glUseProgram(self.shader_program)
        
        # 绑定厚度贴图
        gl.glActiveTexture(gl.GL_TEXTURE0)
        gl.glBindTexture(gl.GL_TEXTURE_2D, self.thickness_texture)
        gl.glUniform1i(gl.glGetUniformLocation(self.shader_program, "thicknessMap"), 0)
        
        # 渲染多个花瓣
        petal_count = 8
        for i in range(petal_count):
            angle = 2 * math.pi * i / petal_count + self.bloom_progress * 0.5
            
            # 计算花瓣变换
            model = glm.mat4(1.0)
            model = glm.translate(model, glm.vec3(0.0, 0.5, 0.0))
            model = glm.rotate(model, angle, glm.vec3(0.0, 1.0, 0.0))
            model = glm.rotate(model, glm.radians(45.0), glm.vec3(1.0, 0.0, 0.0))
            model = glm.scale(model, glm.vec3(0.8, 1.2, 0.3))
            
            gl.glUniformMatrix4fv(
                gl.glGetUniformLocation(self.shader_program, "model"),
                1, gl.GL_FALSE, glm.value_ptr(model)
            )
            
            # 设置花瓣材质
            hue = (i / petal_count + 0.7) % 1.0  # 粉色到紫色范围
            petal_color = self.hsv_to_rgb(hue, 0.8, 0.9)
            
            gl.glUniform3f(gl.glGetUniformLocation(self.shader_program, "material.albedo"),
                          petal_color[0], petal_color[1], petal_color[2])
            gl.glUniform1f(gl.glGetUniformLocation(self.shader_program, "material.roughness"), 0.7)
            gl.glUniform1f(gl.glGetUniformLocation(self.shader_program, "material.metallic"), 0.0)
            gl.glUniform1f(gl.glGetUniformLocation(self.shader_program, "material.subsurface"), 0.3)
            
            # 渲染花瓣
            self.render_mesh(self.petal_mesh)
        
        # 渲染花蕊
        model = glm.mat4(1.0)
        model = glm.translate(model, glm.vec3(0.0, 0.5, 0.0))
        model = glm.scale(model, glm.vec3(0.3))
        
        gl.glUniformMatrix4fv(
            gl.glGetUniformLocation(self.shader_program, "model"),
            1, gl.GL_FALSE, glm.value_ptr(model)
        )
        
        gl.glUniform3f(gl.glGetUniformLocation(self.shader_program, "material.albedo"),
                      0.9, 0.8, 0.1)  # 黄色花蕊
        gl.glUniform1f(gl.glGetUniformLocation(self.shader_program, "material.roughness"), 0.3)
        gl.glUniform1f(gl.glGetUniformLocation(self.shader_program, "material.metallic"), 0.1)
        gl.glUniform1f(gl.glGetUniformLocation(self.shader_program, "material.subsurface"), 0.1)
        
        self.render_mesh(self.pistil_mesh)
    
    def render_mesh(self, mesh):
        """渲染网格"""
        # 创建VAO和VBO
        vao = gl.glGenVertexArrays(1)
        gl.glBindVertexArray(vao)
        
        # 顶点位置
        vbo_vertices = gl.glGenBuffers(1)
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, vbo_vertices)
        gl.glBufferData(gl.GL_ARRAY_BUFFER, mesh['vertices'].nbytes, mesh['vertices'], gl.GL_STATIC_DRAW)
        gl.glVertexAttribPointer(0, 3, gl.GL_FLOAT, gl.GL_FALSE, 0, None)
        gl.glEnableVertexAttribArray(0)
        
        # 法线
        vbo_normals = gl.glGenBuffers(1)
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, vbo_normals)
        gl.glBufferData(gl.GL_ARRAY_BUFFER, mesh['normals'].nbytes, mesh['normals'], gl.GL_STATIC_DRAW)
        gl.glVertexAttribPointer(1, 3, gl.GL_FLOAT, gl.GL_FALSE, 0, None)
        gl.glEnableVertexAttribArray(1)
        
        # 纹理坐标
        vbo_texcoords = gl.glGenBuffers(1)
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, vbo_texcoords)
        gl.glBufferData(gl.GL_ARRAY_BUFFER, mesh['tex_coords'].nbytes, mesh['tex_coords'], gl.GL_STATIC_DRAW)
        gl.glVertexAttribPointer(2, 2, gl.GL_FLOAT, gl.GL_FALSE, 0, None)
        gl.glEnableVertexAttribArray(2)
        
        # 索引缓冲区
        ebo = gl.glGenBuffers(1)
        gl.glBindBuffer(gl.GL_ELEMENT_ARRAY_BUFFER, ebo)
        gl.glBufferData(gl.GL_ELEMENT_ARRAY_BUFFER, mesh['indices'].nbytes, mesh['indices'], gl.GL_STATIC_DRAW)
        
        # 绘制
        gl.glDrawElements(gl.GL_TRIANGLES, len(mesh['indices']), gl.GL_UNSIGNED_INT, None)
        
        # 清理
        gl.glDeleteVertexArrays(1, [vao])
        gl.glDeleteBuffers(1, [vbo_vertices])
        gl.glDeleteBuffers(1, [vbo_normals])
        gl.glDeleteBuffers(1, [vbo_texcoords])
        gl.glDeleteBuffers(1, [ebo])
    
    def hsv_to_rgb(self, h, s, v):
        """HSV到RGB颜色转换"""
        if s == 0.0:
            return (v, v, v)
        
        i = int(h * 6.0)
        f = (h * 6.0) - i
        p = v * (1.0 - s)
        q = v * (1.0 - s * f)
        t = v * (1.0 - s * (1.0 - f))
        
        i = i % 6
        
        if i == 0:
            return (v, t, p)
        elif i == 1:
            return (q, v, p)
        elif i == 2:
            return (p, v, t)
        elif i == 3:
            return (p, q, v)
        elif i == 4:
            return (t, p, v)
        else:
            return (v, p, q)
    
    def resizeGL(self, width, height):
        """处理窗口大小变化"""
        gl.glViewport(0, 0, width, height)
    
    def timerEvent(self, event):
        """定时器事件 - 触发重绘"""
        self.update()
    
    def set_bloom_progress(self, progress):
        """设置绽放进度"""
        self.bloom_progress = progress
        self.update()
    
    def set_wind_strength(self, strength):
        """设置风力强度"""
        self.wind_strength = strength
        self.update()

class AdvancedControlPanel(QWidget):
    """高级控制面板"""
    
    def __init__(self, flower_widget):
        super().__init__()
        self.flower_widget = flower_widget
        
        self.init_ui()
    
    def init_ui(self):
        """初始化用户界面"""
        layout = QVBoxLayout()
        
        # 渲染质量设置
        quality_group = QGroupBox("渲染质量")
        quality_layout = QVBoxLayout()
        
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["低质量", "中等质量", "高质量", "超高质量"])
        self.quality_combo.setCurrentIndex(2)
        self.quality_combo.currentIndexChanged.connect(self.on_quality_changed)
        quality_layout.addWidget(QLabel("渲染质量:"))
        quality_layout.addWidget(self.quality_combo)
        
        self.shadow_quality_combo = QComboBox()
        self.shadow_quality_combo.addItems(["关闭", "低", "中", "高"])
        self.shadow_quality_combo.setCurrentIndex(2)
        self.shadow_quality_combo.currentIndexChanged.connect(self.on_shadow_quality_changed)
        quality_layout.addWidget(QLabel("阴影质量:"))
        quality_layout.addWidget(self.shadow_quality_combo)
        
        quality_group.setLayout(quality_layout)
        layout.addWidget(quality_group)
        
        # 物理模拟设置
        physics_group = QGroupBox("物理模拟")
        physics_layout = QVBoxLayout()
        
        self.physics_enabled_cb = QCheckBox("启用物理模拟")
        self.physics_enabled_cb.setChecked(True)
        self.physics_enabled_cb.stateChanged.connect(self.on_physics_enabled_changed)
        physics_layout.addWidget(self.physics_enabled_cb)
        
        self.wind_slider = QSlider(Qt.Horizontal)
        self.wind_slider.setRange(0, 100)
        self.wind_slider.setValue(50)
        self.wind_slider.valueChanged.connect(self.on_wind_changed)
        physics_layout.addWidget(QLabel("风力强度:"))
        physics_layout.addWidget(self.wind_slider)
        
        physics_group.setLayout(physics_layout)
        layout.addWidget(physics_group)
        
        # 花朵控制
        flower_group = QGroupBox("花朵控制")
        flower_layout = QVBoxLayout()
        
        self.bloom_slider = QSlider(Qt.Horizontal)
        self.bloom_slider.setRange(0, 100)
        self.bloom_slider.setValue(0)
        self.bloom_slider.valueChanged.connect(self.on_bloom_changed)
        flower_layout.addWidget(QLabel("绽放进度:"))
        flower_layout.addWidget(self.bloom_slider)
        
        self.reset_bloom_btn = QPushButton("重新绽放")
        self.reset_bloom_btn.clicked.connect(self.reset_bloom)
        flower_layout.addWidget(self.reset_bloom_btn)
        
        flower_group.setLayout(flower_layout)
        layout.addWidget(flower_group)
        
        # 性能信息
        info_group = QGroupBox("性能信息")
        info_layout = QVBoxLayout()
        
        self.fps_label = QLabel("FPS: 0")
        info_layout.addWidget(self.fps_label)
        
        self.triangle_count_label = QLabel("三角形数量: 0")
        info_layout.addWidget(self.triangle_count_label)
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        layout.addStretch()
        self.setLayout(layout)
        
        # 启动性能监控定时器
        self.stats_timer = QTimer(self)
        self.stats_timer.timeout.connect(self.update_stats)
        self.stats_timer.start(500)  # 每500ms更新一次
    
    def on_quality_changed(self, index):
        """处理质量设置变化"""
        self.flower_widget.render_quality = index
        self.flower_widget.update()
    
    def on_shadow_quality_changed(self, index):
        """处理阴影质量变化"""
        self.flower_widget.shadow_quality = index
        self.flower_widget.update()
    
    def on_physics_enabled_changed(self, state):
        """处理物理模拟启用状态变化"""
        self.flower_widget.physics_enabled = (state == Qt.Checked)
        self.flower_widget.update()
    
    def on_wind_changed(self, value):
        """处理风力强度变化"""
        self.flower_widget.set_wind_strength(value / 100.0)
    
    def on_bloom_changed(self, value):
        """处理绽放进度变化"""
        self.flower_widget.set_bloom_progress(value / 100.0)
    
    def reset_bloom(self):
        """重置绽放动画"""
        self.bloom_slider.setValue(0)
    
    def update_stats(self):
        """更新性能统计"""
        self.fps_label.setText(f"FPS: {self.flower_widget.fps:.1f}")
        # 在实际实现中，这里会显示实际的三角形数量
        self.triangle_count_label.setText("三角形数量: ~10,000")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.init_ui()
    
    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("终极真实感花朵渲染：神经渲染与物理引擎集成")
        self.setGeometry(100, 100, 1600, 900)
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建布局
        layout = QHBoxLayout(central_widget)
        
        # 创建OpenGL渲染部件
        self.flower_widget = AdvancedFlowerGLWidget()
        
        # 创建控制面板
        self.control_panel = AdvancedControlPanel(self.flower_widget)
        self.control_panel.setMaximumWidth(300)
        
        # 添加部件到布局
        layout.addWidget(self.flower_widget)
        layout.addWidget(self.control_panel)
        
        # 状态栏
        self.statusBar().showMessage("就绪 - 使用控制面板调整渲染参数")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 设置高DPI支持
    app.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    app.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    # 检查OpenGL支持
    if not QGLFormat.hasOpenGL():
        print("系统不支持OpenGL")
        sys.exit(1)
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec_())