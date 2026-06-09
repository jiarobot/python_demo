import sys
import numpy as np
from PyQt5.QtWidgets import (QActionGroup, QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                             QWidget, QPushButton, QSlider, QLabel, QGroupBox,
                             QComboBox, QSpinBox, QDoubleSpinBox, QCheckBox,
                             QTabWidget, QSplitter, QFrame, QFileDialog, QMessageBox,
                             QListWidget, QListWidgetItem, QTreeWidget, QTreeWidgetItem,
                             QDockWidget, QToolBar, QAction, QToolButton, QMenu,
                             QProgressDialog, QInputDialog, QColorDialog, QDialog,
                             QGridLayout, QScrollArea, QSizePolicy)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QPoint, QSize, QRect, QThread, pyqtSlot
from PyQt5.QtGui import (QPainter, QColor, QPen, QFont, QIcon, QPixmap, QCursor, 
                         QLinearGradient, QRadialGradient, QPainterPath, QBrush,
                         QKeySequence, QPalette)
from PyQt5.QtOpenGL import QGLWidget, QGLFormat
from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *
import OpenGL.GL as gl
import math
import json
import time
import os
import copy
from collections import deque
import pickle
import zlib


# 增强的网格数据结构
class EnhancedMesh:
    """增强的网格数据结构，支持多分辨率和动态拓扑"""
    def __init__(self):
        self.vertices = np.array([], dtype=np.float32)
        self.faces = np.array([], dtype=np.int32)
        self.normals = np.array([], dtype=np.float32)
        self.colors = np.array([], dtype=np.float32)
        self.vertex_mask = np.array([], dtype=np.float32)
        self.vertex_weights = np.array([], dtype=np.float32)  # 顶点权重
        self.uvs = np.array([], dtype=np.float32)  # UV坐标
        self.modified = False
        
        # 多分辨率数据
        self.multires_levels = []  # 多分辨率级别
        self.current_level = 0
        self.multires_displacement = []  # 位移贴图
        
        # 动态拓扑数据
        self.dynamic_topology = False
        self.edge_length_threshold = 0.1
        self.subdivision_level = 0
        
        # 雕刻图层
        self.sculpt_layers = []
        self.active_layer = 0
        
    def create_sphere(self, radius, slices, stacks):
        """创建球体网格"""
        vertices = []
        faces = []
        normals = []
        uvs = []
        
        for i in range(stacks + 1):
            phi = math.pi * i / stacks
            v = i / stacks
            for j in range(slices + 1):
                theta = 2 * math.pi * j / slices
                u = j / slices
                
                x = radius * math.sin(phi) * math.cos(theta)
                y = radius * math.cos(phi)
                z = radius * math.sin(phi) * math.sin(theta)
                
                vertices.append([x, y, z])
                normals.append([x, y, z])
                uvs.append([u, v])
                
        for i in range(stacks):
            for j in range(slices):
                first = i * (slices + 1) + j
                second = first + slices + 1
                
                faces.append([first, second, first + 1])
                faces.append([second, second + 1, first + 1])
                
        self.vertices = np.array(vertices, dtype=np.float32).flatten()
        self.faces = np.array(faces, dtype=np.int32).flatten()
        self.normals = np.array(normals, dtype=np.float32).flatten()
        self.uvs = np.array(uvs, dtype=np.float32).flatten()
        self.colors = np.ones(len(vertices) * 3, dtype=np.float32) * 0.7
        self.vertex_mask = np.zeros(len(vertices), dtype=np.float32)
        self.vertex_weights = np.ones(len(vertices), dtype=np.float32)
        
        # 保存为基础级别
        self.multires_levels = [{
            'vertices': self.vertices.copy(),
            'faces': self.faces.copy(),
            'level': 0
        }]
        
        self.modified = True
        
    def subdivide(self, levels=1):
        """网格细分（Loop细分算法简化版）"""
        for _ in range(levels):
            new_vertices = []
            new_faces = []
            
            # 这里应该实现完整的Loop细分算法
            # 简化实现：仅做基本细分
            
            # 将每个三角形细分为四个小三角形
            faces = self.faces.reshape(-1, 3)
            vertices = self.vertices.reshape(-1, 3)
            
            for face in faces:
                # 计算新顶点（边中点）
                v0 = vertices[face[0]]
                v1 = vertices[face[1]]
                v2 = vertices[face[2]]
                
                # 简化细分：仅添加面中心点
                center = [(v0[i] + v1[i] + v2[i]) / 3 for i in range(3)]
                center_idx = len(new_vertices)
                new_vertices.append(center)
                
                # 添加新面
                new_faces.extend([
                    [face[0], face[1], center_idx],
                    [face[1], face[2], center_idx],
                    [face[2], face[0], center_idx],
                    [face[0], center_idx, face[2]] ] # 修正面方向
                )
            
            # 更新网格
            self.vertices = np.array(new_vertices, dtype=np.float32).flatten()
            self.faces = np.array(new_faces, dtype=np.int32).flatten()
            self.subdivision_level += 1
            
        self.update_normals()
        self.modified = True
        
    def decimate(self, ratio=0.5):
        """网格简化（简化实现）"""
        # 实际实现应该使用QEM等算法
        # 这里只是简单删除部分面
        if len(self.faces) < 100:
            return
            
        faces = self.faces.reshape(-1, 3)
        keep_count = int(len(faces) * ratio)
        
        if keep_count < 4:
            keep_count = 4
            
        # 随机保留部分面（实际应该基于曲率等标准）
        indices = np.random.choice(len(faces), keep_count, replace=False)
        self.faces = faces[indices].flatten()
        
        # 重新计算顶点
        self.remap_vertices()
        self.update_normals()
        self.modified = True
        
    def remap_vertices(self):
        """重新映射顶点（删除未使用的顶点）"""
        # 实际实现需要更复杂的顶点重映射
        pass
        
    def update_normals(self):
        """更新顶点法线"""
        if len(self.vertices) == 0 or len(self.faces) == 0:
            return
            
        vertices = self.vertices.reshape(-1, 3)
        faces = self.faces.reshape(-1, 3)
        normals = np.zeros_like(vertices)
        
        # 计算面法线并累加到顶点
        for face in faces:
            if face[0] >= len(vertices) or face[1] >= len(vertices) or face[2] >= len(vertices):
                continue
                
            v0 = vertices[face[0]]
            v1 = vertices[face[1]]
            v2 = vertices[face[2]]
            
            # 计算面法线
            edge1 = v1 - v0
            edge2 = v2 - v0
            normal = np.cross(edge1, edge2)
            normal_length = np.linalg.norm(normal)
            
            if normal_length > 0:
                normal = normal / normal_length
                
                # 累加到顶点法线
                for vertex_idx in face:
                    if vertex_idx < len(normals):
                        normals[vertex_idx] += normal
        
        # 归一化顶点法线
        for i in range(len(normals)):
            length = np.linalg.norm(normals[i])
            if length > 0:
                normals[i] = normals[i] / length
                
        self.normals = normals.flatten()
        
    def apply_sculpt(self, tool, intensity, brush_center, brush_radius, brush_falloff, symmetry=False):
        """应用雕刻工具到网格"""
        if len(self.vertices) == 0:
            return
            
        brush_center = np.array(brush_center)
        vertices = self.vertices.reshape(-1, 3)
        normals = self.normals.reshape(-1, 3)
        
        # 动态拓扑：检查是否需要细分
        if self.dynamic_topology:
            self.check_dynamic_topology(brush_center, brush_radius)
        
        for i in range(len(vertices)):
            vertex = vertices[i]
            normal = normals[i]
            distance = np.linalg.norm(vertex - brush_center)
            
            if distance < brush_radius:
                # 计算笔刷衰减
                falloff = 1.0 - (distance / brush_radius)
                falloff = math.pow(falloff, brush_falloff)
                
                # 应用顶点权重
                weight = self.vertex_weights[i] if i < len(self.vertex_weights) else 1.0
                effective_intensity = intensity * weight * falloff
                
                # 根据工具类型应用不同的雕刻效果
                if tool == "sculpt":
                    # 沿法线方向移动顶点
                    displacement = normal * effective_intensity * 0.1
                    vertices[i] += displacement
                elif tool == "smooth":
                    # 平滑工具 - 拉普拉斯平滑
                    neighbors = self.get_vertex_neighbors(i)
                    if neighbors:
                        avg = np.mean([vertices[j] for j in neighbors], axis=0)
                        vertices[i] = vertices[i] * 0.7 + avg * 0.3
                elif tool == "flatten":
                    # 平整工具 - 将顶点投影到平面上
                    pass  # 需要更复杂的实现
                elif tool == "inflate":
                    displacement = normal * effective_intensity * 0.05
                    vertices[i] += displacement
                elif tool == "pinch":
                    displacement = -normal * effective_intensity * 0.05
                    vertices[i] += displacement
                elif tool == "grab":
                    # 抓取工具 - 移动顶点
                    direction = brush_center - vertex
                    direction_length = np.linalg.norm(direction)
                    if direction_length > 0:
                        direction = direction / direction_length
                        displacement = direction * effective_intensity * 0.1
                        vertices[i] += displacement
                elif tool == "mask":
                    # 蒙版工具 - 设置顶点蒙版值
                    if i < len(self.vertex_mask):
                        self.vertex_mask[i] = min(1.0, self.vertex_mask[i] + effective_intensity * 0.1)
                        
        self.vertices = vertices.flatten()
        self.update_normals()
        self.modified = True
        
        # 对称雕刻
        if symmetry:
            self.apply_symmetry(tool, intensity, brush_center, brush_radius, brush_falloff)
        
    def apply_symmetry(self, tool, intensity, brush_center, brush_radius, brush_falloff):
        """应用对称雕刻"""
        # X轴对称
        symmetric_center = [-brush_center[0], brush_center[1], brush_center[2]]
        self.apply_sculpt(tool, intensity, symmetric_center, brush_radius, brush_falloff, False)
        
    def get_vertex_neighbors(self, vertex_index):
        """获取顶点的邻居顶点（简化实现）"""
        # 实际实现需要建立顶点-面关系图
        neighbors = set()
        faces = self.faces.reshape(-1, 3)
        
        for face in faces:
            if vertex_index in face:
                for v in face:
                    if v != vertex_index:
                        neighbors.add(v)
                        
        return list(neighbors)
        
    def check_dynamic_topology(self, brush_center, brush_radius):
        """检查并应用动态拓扑"""
        vertices = self.vertices.reshape(-1, 3)
        faces = self.faces.reshape(-1, 3)
        
        # 检查笔刷区域内的边长度
        for face in faces:
            if face[0] >= len(vertices) or face[1] >= len(vertices) or face[2] >= len(vertices):
                continue
                
            # 计算面中心
            center = np.mean([vertices[face[0]], vertices[face[1]], vertices[face[2]]], axis=0)
            distance = np.linalg.norm(center - brush_center)
            
            if distance < brush_radius * 1.5:
                # 检查边长度
                edges = [
                    (face[0], face[1]),
                    (face[1], face[2]),
                    (face[2], face[0])
                ]
                
                for edge in edges:
                    v1 = vertices[edge[0]]
                    v2 = vertices[edge[1]]
                    edge_length = np.linalg.norm(v1 - v2)
                    
                    # 如果边太长，细分
                    if edge_length > self.edge_length_threshold * 2:
                        self.subdivide_face(face)
                        return
                    
                    # 如果边太短，合并
                    elif edge_length < self.edge_length_threshold * 0.5:
                        self.collapse_edge(edge)
                        return
    
    def subdivide_face(self, face):
        """细分面（简化实现）"""
        # 实际实现应该使用更完善的细分算法
        pass
        
    def collapse_edge(self, edge):
        """塌陷边（简化实现）"""
        # 实际实现应该使用边塌陷算法
        pass


# 增强的3D查看器
class EnhancedSculptureViewer(QGLWidget):
    """增强的3D雕塑查看器，支持高级渲染和交互"""
    
    toolApplied = pyqtSignal(str, float, list, float, float, bool)
    cameraMoved = pyqtSignal(float, float, float)
    
    def __init__(self, parent=None):
        # 直接调用父类初始化，不使用特殊格式
        super(EnhancedSculptureViewer, self).__init__(parent)
        
        # 其余初始化代码保持不变
        self.mesh = EnhancedMesh()
        self.current_tool = "sculpt"
        self.tool_intensity = 1.0
        self.brush_radius = 0.5
        self.brush_falloff = 2.0
        self.brush_position = [0, 0, 0]
        self.is_dragging = False
        self.last_mouse_pos = None
        
        # 高级渲染设置
        self.display_mode = "shaded"  # shaded, wireframe, textured, matcap
        self.show_wireframe = False
        self.show_vertices = False
        self.show_normals = False
        self.show_mask = False
        
        # 相机参数
        self.camera_distance = 5.0
        self.camera_rotation_x = 0.0
        self.camera_rotation_y = 0.0
        self.camera_translation = [0, 0, 0]
        self.camera_fov = 45.0
        self.camera_near = 0.1
        self.camera_far = 100.0
        
        # 光照参数
        self.light_position = [2.0, 2.0, 2.0, 1.0]
        self.light_intensity = 1.0
        self.ambient_intensity = 0.3
        
        # 笔刷纹理
        self.brush_texture = None
        self.brush_stencil = None
        
        # 选择系统
        self.selected_vertices = set()
        self.selection_radius = 0.2
        
        # 变换工具
        self.transform_mode = None  # translate, rotate, scale
        self.transform_gizmo = None
        
        self.setFocusPolicy(Qt.StrongFocus)
        self.setMouseTracking(True)
        
        # 设置多采样抗锯齿
        #self.setFormat(fmt)
        
    def initializeGL(self):
        """初始化OpenGL"""
        try:
            import OpenGL.GLE as gle
            gle.glewInit()
        except:
            pass
            
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_MULTISAMPLE)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        
        # 设置光源 - 使用正确的函数调用
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        
        # 设置光源位置
        glLightfv(GL_LIGHT0, GL_POSITION, self.light_position)
        
        # 设置光源属性（使用glLightfv）
        diffuse_color = [0.8, 0.8, 0.8, 1.0]  # 漫反射光
        ambient_color = [0.3, 0.3, 0.3, 1.0]  # 环境光
        specular_color = [1.0, 1.0, 1.0, 1.0]  # 镜面反射光
        
        glLightfv(GL_LIGHT0, GL_DIFFUSE, diffuse_color)
        glLightfv(GL_LIGHT0, GL_AMBIENT, ambient_color)
        glLightfv(GL_LIGHT0, GL_SPECULAR, specular_color)
        
        # 设置衰减系数
        glLightf(GL_LIGHT0, GL_CONSTANT_ATTENUATION, 1.0)
        glLightf(GL_LIGHT0, GL_LINEAR_ATTENUATION, 0.05)
        glLightf(GL_LIGHT0, GL_QUADRATIC_ATTENUATION, 0.01)
        
        glEnable(GL_COLOR_MATERIAL)
        glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
        
        # 设置材质属性
        glMaterialfv(GL_FRONT, GL_SPECULAR, [1.0, 1.0, 1.0, 1.0])
        glMaterialf(GL_FRONT, GL_SHININESS, 100.0)
        
        # 创建初始网格
        self.mesh.create_sphere(1.0, 32, 32)
        
        # 加载笔刷纹理
        self.load_brush_texture()
        
    def resizeGL(self, w, h):
        """调整视图大小"""
        glViewport(0, 0, w, h)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(self.camera_fov, w / h, self.camera_near, self.camera_far)
        glMatrixMode(GL_MODELVIEW)
        
    def paintGL(self):
        """渲染场景"""
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        
        # 设置相机
        glTranslatef(0, 0, -self.camera_distance)
        glRotatef(self.camera_rotation_x, 1, 0, 0)
        glRotatef(self.camera_rotation_y, 0, 1, 0)
        glTranslatef(*self.camera_translation)
        
        # 更新光源位置
        light_pos = [self.light_position[0], self.light_position[1], self.light_position[2], 1.0]
        glLightfv(GL_LIGHT0, GL_POSITION, light_pos)
        
        # 动态更新光照强度（使用正确的函数）
        diffuse_intensity = [self.light_intensity, self.light_intensity, self.light_intensity, 1.0]
        ambient_intensity = [self.ambient_intensity, self.ambient_intensity, self.ambient_intensity, 1.0]
        
        glLightfv(GL_LIGHT0, GL_DIFFUSE, diffuse_intensity)
        glLightfv(GL_LIGHT0, GL_AMBIENT, ambient_intensity)
        
        # 根据显示模式渲染网格
        if self.display_mode == "wireframe":
            glDisable(GL_LIGHTING)
            self.draw_wireframe()
            glEnable(GL_LIGHTING)
        elif self.display_mode == "textured":
            self.draw_textured()
        elif self.display_mode == "matcap":
            self.draw_matcap()
        else:  # shaded
            self.draw_shaded()
            
        # 叠加显示选项
        if self.show_wireframe and self.display_mode != "wireframe":
            glDisable(GL_LIGHTING)
            glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
            self.draw_wireframe_overlay()
            glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
            glEnable(GL_LIGHTING)
            
        if self.show_vertices:
            self.draw_vertices()
            
        if self.show_normals:
            self.draw_normals()
            
        if self.show_mask:
            self.draw_mask()
            
        # 绘制笔刷
        if self.is_dragging or self.underMouse():
            self.draw_brush()
            
        # 绘制选择
        if self.selected_vertices:
            self.draw_selection()
            
        # 绘制变换Gizmo
        if self.transform_mode:
            self.draw_transform_gizmo()
            
    def draw_shaded(self):
        """绘制着色网格"""
        if len(self.mesh.vertices) == 0:
            return
            
        vertices = self.mesh.vertices.reshape(-1, 3)
        normals = self.mesh.normals.reshape(-1, 3)
        colors = self.mesh.colors.reshape(-1, 3)
        faces = self.mesh.faces.reshape(-1, 3)
        
        glBegin(GL_TRIANGLES)
        for face in faces:
            for vertex_idx in face:
                if vertex_idx < len(colors):
                    # 应用蒙版颜色
                    if self.mesh.vertex_mask[vertex_idx] > 0 and self.show_mask:
                        mask_val = self.mesh.vertex_mask[vertex_idx]
                        glColor3f(0.8, 0.2, 0.2)  # 红色蒙版
                    else:
                        glColor3f(*colors[vertex_idx])
                if vertex_idx < len(normals):
                    glNormal3f(*normals[vertex_idx])
                if vertex_idx < len(vertices):
                    glVertex3f(*vertices[vertex_idx])
        glEnd()
        
    def draw_wireframe(self):
        """绘制线框"""
        if len(self.mesh.vertices) == 0:
            return
            
        vertices = self.mesh.vertices.reshape(-1, 3)
        faces = self.mesh.faces.reshape(-1, 3)
        
        glColor3f(0.3, 0.3, 0.3)
        glBegin(GL_LINES)
        for face in faces:
            for i in range(3):
                v1 = vertices[face[i]]
                v2 = vertices[face[(i+1)%3]]
                glVertex3f(*v1)
                glVertex3f(*v2)
        glEnd()
        
    def draw_wireframe_overlay(self):
        """绘制线框叠加层"""
        if len(self.mesh.vertices) == 0:
            return
            
        vertices = self.mesh.vertices.reshape(-1, 3)
        faces = self.mesh.faces.reshape(-1, 3)
        
        glColor4f(0.0, 0.0, 0.0, 0.3)
        glLineWidth(1.0)
        glBegin(GL_LINES)
        for face in faces:
            for i in range(3):
                v1 = vertices[face[i]]
                v2 = vertices[face[(i+1)%3]]
                glVertex3f(*v1)
                glVertex3f(*v2)
        glEnd()
        
    def draw_textured(self):
        """绘制纹理网格"""
        # 需要实现纹理坐标和纹理加载
        self.draw_shaded()  # 暂时回退到着色模式
        
    def draw_matcap(self):
        """绘制材质捕捉（MatCap）"""
        # 需要实现MatCap着色器
        self.draw_shaded()  # 暂时回退到着色模式
        
    def draw_vertices(self):
        """绘制顶点"""
        if len(self.mesh.vertices) == 0:
            return
            
        vertices = self.mesh.vertices.reshape(-1, 3)
        
        glDisable(GL_LIGHTING)
        glPointSize(3.0)
        glColor3f(0.0, 0.0, 1.0)
        glBegin(GL_POINTS)
        for vertex in vertices:
            glVertex3f(*vertex)
        glEnd()
        glEnable(GL_LIGHTING)
        
    def draw_normals(self):
        """绘制法线"""
        if len(self.mesh.vertices) == 0 or len(self.mesh.normals) == 0:
            return
            
        vertices = self.mesh.vertices.reshape(-1, 3)
        normals = self.mesh.normals.reshape(-1, 3)
        
        glDisable(GL_LIGHTING)
        glColor3f(0.0, 1.0, 0.0)
        glBegin(GL_LINES)
        for i in range(len(vertices)):
            if i < len(normals):
                start = vertices[i]
                end = start + normals[i] * 0.1  # 法线长度
                glVertex3f(*start)
                glVertex3f(*end)
        glEnd()
        glEnable(GL_LIGHTING)
        
    def draw_mask(self):
        """绘制蒙版（叠加显示）"""
        # 已经在draw_shaded中处理
        
    def draw_brush(self):
        """绘制笔刷指示器"""
        glPushMatrix()
        glTranslatef(*self.brush_position)
        
        glDisable(GL_LIGHTING)
        
        # 根据工具类型绘制不同笔刷
        if self.current_tool == "mask":
            glColor4f(1.0, 0.0, 0.0, 0.3)  # 红色蒙版笔刷
        else:
            glColor4f(1.0, 0.5, 0.0, 0.3)  # 橙色雕刻笔刷
            
        # 绘制笔刷球体
        quadric = gluNewQuadric()
        gluSphere(quadric, self.brush_radius, 32, 32)
        
        # 绘制笔刷轮廓
        glColor4f(1.0, 0.8, 0.0, 0.8)
        glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
        gluSphere(quadric, self.brush_radius, 32, 32)
        glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
        
        gluDeleteQuadric(quadric)
        glEnable(GL_LIGHTING)
        glPopMatrix()
        
    def draw_selection(self):
        """绘制选择顶点"""
        if not self.selected_vertices or len(self.mesh.vertices) == 0:
            return
            
        vertices = self.mesh.vertices.reshape(-1, 3)
        
        glDisable(GL_LIGHTING)
        glPointSize(5.0)
        glColor3f(1.0, 1.0, 0.0)  # 黄色选择
        
        glBegin(GL_POINTS)
        for vertex_idx in self.selected_vertices:
            if vertex_idx < len(vertices):
                glVertex3f(*vertices[vertex_idx])
        glEnd()
        glEnable(GL_LIGHTING)
        
    def draw_transform_gizmo(self):
        """绘制变换Gizmo"""
        glDisable(GL_LIGHTING)
        
        # 绘制坐标轴
        glLineWidth(3.0)
        
        # X轴 - 红色
        glColor3f(1.0, 0.0, 0.0)
        glBegin(GL_LINES)
        glVertex3f(0, 0, 0)
        glVertex3f(1, 0, 0)
        glEnd()
        
        # Y轴 - 绿色
        glColor3f(0.0, 1.0, 0.0)
        glBegin(GL_LINES)
        glVertex3f(0, 0, 0)
        glVertex3f(0, 1, 0)
        glEnd()
        
        # Z轴 - 蓝色
        glColor3f(0.0, 0.0, 1.0)
        glBegin(GL_LINES)
        glVertex3f(0, 0, 0)
        glVertex3f(0, 0, 1)
        glEnd()
        
        glEnable(GL_LIGHTING)
        
    def load_brush_texture(self):
        """加载笔刷纹理（简化实现）"""
        # 实际实现应该从文件加载笔刷纹理
        pass
        
    def mousePressEvent(self, event):
        """鼠标按下事件"""
        if event.button() == Qt.LeftButton:
            # 检查是否在变换Gizmo上
            if self.transform_mode and self.check_gizmo_hit(event.pos()):
                self.is_dragging = True
                self.last_mouse_pos = event.pos()
                return
                
            # 检查是否在选择模式下
            if self.current_tool == "select":
                self.select_vertices(event.pos())
            else:
                # 应用雕刻工具
                self.is_dragging = True
                self.last_mouse_pos = event.pos()
                self.apply_tool()
                
        elif event.button() == Qt.RightButton:
            self.last_mouse_pos = event.pos()
            
        elif event.button() == Qt.MiddleButton:
            self.last_mouse_pos = event.pos()
            
    def mouseMoveEvent(self, event):
        """鼠标移动事件"""
        if self.is_dragging and event.buttons() & Qt.LeftButton:
            if self.transform_mode:
                # 处理变换
                self.handle_transform(event.pos())
            elif self.current_tool == "select":
                # 继续选择
                self.select_vertices(event.pos(), additive=True)
            else:
                # 应用工具
                self.update_brush_position(event.pos())
                self.apply_tool()
                
        elif event.buttons() & Qt.RightButton:
            # 旋转相机
            if self.last_mouse_pos:
                dx = event.x() - self.last_mouse_pos.x()
                dy = event.y() - self.last_mouse_pos.y()
                
                self.camera_rotation_y += dx * 0.5
                self.camera_rotation_x += dy * 0.5
                self.camera_rotation_x = max(-90, min(90, self.camera_rotation_x))
                
                self.last_mouse_pos = event.pos()
                self.update()
                self.cameraMoved.emit(self.camera_rotation_x, self.camera_rotation_y, self.camera_distance)
                
        elif event.buttons() & Qt.MiddleButton:
            # 平移相机
            if self.last_mouse_pos:
                dx = event.x() - self.last_mouse_pos.x()
                dy = event.y() - self.last_mouse_pos.y()
                
                self.camera_translation[0] += dx * 0.01
                self.camera_translation[1] -= dy * 0.01
                
                self.last_mouse_pos = event.pos()
                self.update()
                self.cameraMoved.emit(self.camera_rotation_x, self.camera_rotation_y, self.camera_distance)
                
        else:
            # 更新笔刷位置
            self.update_brush_position(event.pos())
            self.update()
            
    def mouseReleaseEvent(self, event):
        """鼠标释放事件"""
        if event.button() == Qt.LeftButton:
            self.is_dragging = False
            
    def wheelEvent(self, event):
        """鼠标滚轮事件"""
        # 调整笔刷大小或相机距离
        if event.modifiers() & Qt.ControlModifier:
            # 调整笔刷大小
            self.brush_radius = max(0.1, self.brush_radius + event.angleDelta().y() * 0.001)
        elif event.modifiers() & Qt.ShiftModifier:
            # 调整笔刷强度
            self.tool_intensity = max(0.01, self.tool_intensity + event.angleDelta().y() * 0.01)
        else:
            # 调整相机距离
            self.camera_distance = max(1.0, self.camera_distance - event.angleDelta().y() * 0.01)
            
        self.update()
        
    def keyPressEvent(self, event):
        """键盘事件"""
        key = event.key()
        
        # 工具快捷键
        if key == Qt.Key_S:
            self.current_tool = "sculpt"
        elif key == Qt.Key_M:
            self.current_tool = "mask"
        elif key == Qt.Key_G:
            self.current_tool = "grab"
        elif key == Qt.Key_T:
            self.current_tool = "select"
        elif key == Qt.Key_W:
            self.display_mode = "wireframe" if self.display_mode != "wireframe" else "shaded"
        elif key == Qt.Key_Z and event.modifiers() & Qt.ControlModifier:
            self.undo()
            
        self.update()
        
    def update_brush_position(self, mouse_pos):
        """更新笔刷位置（使用射线投射）"""
        # 将鼠标坐标归一化
        x = (mouse_pos.x() / self.width()) * 2 - 1
        y = -((mouse_pos.y() / self.height()) * 2 - 1)
        
        # 创建射线
        ray_origin, ray_dir = self.screen_to_world(x, y)
        
        # 简化：假设网格在原点，半径为1的球体
        t = self.ray_sphere_intersect(ray_origin, ray_dir, [0, 0, 0], 1.0)
        
        if t > 0:
            # 确保 brush_position 是 numpy 数组
            self.brush_position = np.array(ray_origin + ray_dir * t)
        else:
            # 如果没有相交，将笔刷放在近裁剪平面上
            self.brush_position = np.array(ray_origin + ray_dir * 0.1)
            
    def screen_to_world(self, x, y):
        """将屏幕坐标转换为世界坐标射线"""
        # 获取投影和模型视图矩阵
        modelview = glGetDoublev(GL_MODELVIEW_MATRIX)
        projection = glGetDoublev(GL_PROJECTION_MATRIX)
        viewport = glGetIntegerv(GL_VIEWPORT)
        
        # 将2D屏幕坐标转换为3D世界坐标
        # 近平面点
        near_point = gluUnProject(x, y, 0.0, modelview, projection, viewport)
        # 远平面点
        far_point = gluUnProject(x, y, 1.0, modelview, projection, viewport)
        
        # 计算射线方向和原点
        ray_origin = np.array(near_point)
        ray_dir = np.array(far_point) - ray_origin
        ray_dir = ray_dir / np.linalg.norm(ray_dir)
        
        return ray_origin, ray_dir
        
    def ray_sphere_intersect(self, ray_origin, ray_dir, sphere_center, sphere_radius):
        """计算射线与球体的相交"""
        oc = ray_origin - sphere_center
        a = np.dot(ray_dir, ray_dir)
        b = 2.0 * np.dot(oc, ray_dir)
        c = np.dot(oc, oc) - sphere_radius * sphere_radius
        discriminant = b * b - 4 * a * c
        
        if discriminant < 0:
            return -1.0
        else:
            return (-b - math.sqrt(discriminant)) / (2.0 * a)
            
    def select_vertices(self, mouse_pos, additive=False):
        """选择顶点"""
        if not additive:
            self.selected_vertices.clear()
            
        # 将鼠标位置转换为世界坐标
        x = (mouse_pos.x() / self.width()) * 2 - 1
        y = -((mouse_pos.y() / self.height()) * 2 - 1)
        
        ray_origin, ray_dir = self.screen_to_world(x, y)
        
        # 查找射线附近的顶点
        vertices = self.mesh.vertices.reshape(-1, 3)
        
        for i, vertex in enumerate(vertices):
            # 计算顶点到射线的距离
            vertex_to_ray = vertex - ray_origin
            projection = np.dot(vertex_to_ray, ray_dir)
            closest_point = ray_origin + ray_dir * projection
            distance = np.linalg.norm(vertex - closest_point)
            
            if distance < self.selection_radius:
                self.selected_vertices.add(i)
                
        self.update()
        
    def check_gizmo_hit(self, mouse_pos):
        """检查是否点击了变换Gizmo"""
        # 简化实现
        return False
        
    def handle_transform(self, mouse_pos):
        """处理变换操作"""
        # 简化实现
        pass
        
    def apply_tool(self):
        """应用当前工具到网格"""
        symmetry = False  # 从设置中获取
        
        # 修复：将 numpy 数组转换为 Python 列表
        brush_position_list = self.brush_position.tolist() if hasattr(self.brush_position, 'tolist') else self.brush_position
        
        self.toolApplied.emit(
            self.current_tool, 
            self.tool_intensity, 
            brush_position_list,  # 使用转换后的列表
            self.brush_radius, 
            self.brush_falloff,
            symmetry
        )
        
        # 直接调用网格的雕刻方法（这里不需要转换，因为 apply_sculpt 内部会处理）
        self.mesh.apply_sculpt(
            self.current_tool,
            self.tool_intensity,
            self.brush_position,
            self.brush_radius,
            self.brush_falloff,
            symmetry
        )
        
        self.update()
        
    def undo(self):
        """撤销操作"""
        # 实现撤销逻辑
        pass


# 高级工具设置面板
class AdvancedToolSettings(QWidget):
    """高级工具设置面板"""
    
    def __init__(self, parent=None):
        super(AdvancedToolSettings, self).__init__(parent)
        
        self.init_ui()
        
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout()
        
        # 创建选项卡
        self.tabs = QTabWidget()
        
        # 笔刷选项卡
        self.brush_tab = self.create_brush_tab()
        self.tabs.addTab(self.brush_tab, "笔刷")
        
        # 雕刻选项卡
        self.sculpt_tab = self.create_sculpt_tab()
        self.tabs.addTab(self.sculpt_tab, "雕刻")
        
        # 拓扑选项卡
        self.topology_tab = self.create_topology_tab()
        self.tabs.addTab(self.topology_tab, "拓扑")
        
        # 显示选项卡
        self.display_tab = self.create_display_tab()
        self.tabs.addTab(self.display_tab, "显示")
        
        layout.addWidget(self.tabs)
        self.setLayout(layout)
        
    def create_brush_tab(self):
        """创建笔刷设置选项卡"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # 笔刷类型
        brush_type_group = QGroupBox("笔刷类型")
        brush_type_layout = QVBoxLayout()
        
        self.brush_type_combo = QComboBox()
        self.brush_type_combo.addItems(["标准", "黏土", "平面", "刮痕", "填充", "自定义"])
        brush_type_layout.addWidget(self.brush_type_combo)
        
        # 笔刷形状
        self.brush_shape_combo = QComboBox()
        self.brush_shape_combo.addItems(["圆形", "方形", "自定义"])
        brush_type_layout.addWidget(QLabel("笔刷形状:"))
        brush_type_layout.addWidget(self.brush_shape_combo)
        
        brush_type_group.setLayout(brush_type_layout)
        layout.addWidget(brush_type_group)
        
        # 笔刷参数
        brush_params_group = QGroupBox("笔刷参数")
        brush_params_layout = QGridLayout()
        
        # 大小
        brush_params_layout.addWidget(QLabel("大小:"), 0, 0)
        self.brush_size_slider = QSlider(Qt.Horizontal)
        self.brush_size_slider.setRange(1, 100)
        self.brush_size_slider.setValue(50)
        brush_params_layout.addWidget(self.brush_size_slider, 0, 1)
        self.brush_size_label = QLabel("0.5")
        brush_params_layout.addWidget(self.brush_size_label, 0, 2)
        
        # 强度
        brush_params_layout.addWidget(QLabel("强度:"), 1, 0)
        self.brush_strength_slider = QSlider(Qt.Horizontal)
        self.brush_strength_slider.setRange(1, 100)
        self.brush_strength_slider.setValue(50)
        brush_params_layout.addWidget(self.brush_strength_slider, 1, 1)
        self.brush_strength_label = QLabel("1.0")
        brush_params_layout.addWidget(self.brush_strength_label, 1, 2)
        
        # 衰减
        brush_params_layout.addWidget(QLabel("衰减:"), 2, 0)
        self.brush_falloff_slider = QSlider(Qt.Horizontal)
        self.brush_falloff_slider.setRange(1, 100)
        self.brush_falloff_slider.setValue(50)
        brush_params_layout.addWidget(self.brush_falloff_slider, 2, 1)
        self.brush_falloff_label = QLabel("2.0")
        brush_params_layout.addWidget(self.brush_falloff_label, 2, 2)
        
        # 间距
        brush_params_layout.addWidget(QLabel("间距:"), 3, 0)
        self.brush_spacing_slider = QSlider(Qt.Horizontal)
        self.brush_spacing_slider.setRange(1, 100)
        self.brush_spacing_slider.setValue(20)
        brush_params_layout.addWidget(self.brush_spacing_slider, 3, 1)
        self.brush_spacing_label = QLabel("0.1")
        brush_params_layout.addWidget(self.brush_spacing_label, 3, 2)
        
        brush_params_group.setLayout(brush_params_layout)
        layout.addWidget(brush_params_group)
        
        # 笔刷纹理
        brush_texture_group = QGroupBox("笔刷纹理")
        brush_texture_layout = QVBoxLayout()
        
        self.brush_texture_combo = QComboBox()
        self.brush_texture_combo.addItems(["柔和", "锐利", "纹理1", "纹理2", "自定义"])
        brush_texture_layout.addWidget(self.brush_texture_combo)
        
        brush_texture_group.setLayout(brush_texture_layout)
        layout.addWidget(brush_texture_group)
        
        layout.addStretch()
        widget.setLayout(layout)
        
        # 连接信号
        self.brush_size_slider.valueChanged.connect(self.update_brush_size)
        self.brush_strength_slider.valueChanged.connect(self.update_brush_strength)
        self.brush_falloff_slider.valueChanged.connect(self.update_brush_falloff)
        self.brush_spacing_slider.valueChanged.connect(self.update_brush_spacing)
        
        return widget
        
    def create_sculpt_tab(self):
        """创建雕刻设置选项卡"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # 对称设置
        symmetry_group = QGroupBox("对称")
        symmetry_layout = QGridLayout()
        
        self.symmetry_x = QCheckBox("X轴对称")
        self.symmetry_y = QCheckBox("Y轴对称")
        self.symmetry_z = QCheckBox("Z轴对称")
        self.radial_symmetry = QCheckBox("径向对称")
        
        symmetry_layout.addWidget(self.symmetry_x, 0, 0)
        symmetry_layout.addWidget(self.symmetry_y, 0, 1)
        symmetry_layout.addWidget(self.symmetry_z, 1, 0)
        symmetry_layout.addWidget(self.radial_symmetry, 1, 1)
        
        self.radial_count = QSpinBox()
        self.radial_count.setRange(2, 32)
        self.radial_count.setValue(6)
        symmetry_layout.addWidget(QLabel("径向数量:"), 2, 0)
        symmetry_layout.addWidget(self.radial_count, 2, 1)
        
        symmetry_group.setLayout(symmetry_layout)
        layout.addWidget(symmetry_group)
        
        # 高级选项
        advanced_group = QGroupBox("高级选项")
        advanced_layout = QVBoxLayout()
        
        self.dynamic_topology = QCheckBox("动态拓扑")
        self.sculpt_layers = QCheckBox("雕刻图层")
        self.multires_sculpting = QCheckBox("多分辨率雕刻")
        self.auto_smooth = QCheckBox("自动平滑")
        
        advanced_layout.addWidget(self.dynamic_topology)
        advanced_layout.addWidget(self.sculpt_layers)
        advanced_layout.addWidget(self.multires_sculpting)
        advanced_layout.addWidget(self.auto_smooth)
        
        advanced_group.setLayout(advanced_layout)
        layout.addWidget(advanced_group)
        
        # 变形目标
        deformation_group = QGroupBox("变形目标")
        deformation_layout = QVBoxLayout()
        
        self.deformation_combo = QComboBox()
        self.deformation_combo.addItems(["无", "膨胀", "收缩", "扭曲", "弯曲"])
        deformation_layout.addWidget(self.deformation_combo)
        
        deformation_group.setLayout(deformation_layout)
        layout.addWidget(deformation_group)
        
        layout.addStretch()
        widget.setLayout(layout)
        
        return widget
        
    def create_topology_tab(self):
        """创建拓扑设置选项卡"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # 动态拓扑设置
        dynotopo_group = QGroupBox("动态拓扑")
        dynotopo_layout = QGridLayout()
        
        self.dynotopo_enabled = QCheckBox("启用动态拓扑")
        dynotopo_layout.addWidget(self.dynotopo_enabled, 0, 0, 1, 2)
        
        dynotopo_layout.addWidget(QLabel("细节大小:"), 1, 0)
        self.detail_size_slider = QSlider(Qt.Horizontal)
        self.detail_size_slider.setRange(1, 100)
        self.detail_size_slider.setValue(50)
        dynotopo_layout.addWidget(self.detail_size_slider, 1, 1)
        
        dynotopo_layout.addWidget(QLabel("细分强度:"), 2, 0)
        self.subdivision_strength_slider = QSlider(Qt.Horizontal)
        self.subdivision_strength_slider.setRange(1, 100)
        self.subdivision_strength_slider.setValue(50)
        dynotopo_layout.addWidget(self.subdivision_strength_slider, 2, 1)
        
        dynotopo_group.setLayout(dynotopo_layout)
        layout.addWidget(dynotopo_group)
        
        # 重拓扑工具
        retopo_group = QGroupBox("重拓扑工具")
        retopo_layout = QVBoxLayout()
        
        self.retopo_combo = QComboBox()
        self.retopo_combo.addItems(["绘制流线", "自动重拓扑", "网格提取", "四边形绘制"])
        retopo_layout.addWidget(self.retopo_combo)
        
        retopo_buttons_layout = QHBoxLayout()
        self.retopo_generate_btn = QPushButton("生成网格")
        self.retopo_optimize_btn = QPushButton("优化拓扑")
        retopo_buttons_layout.addWidget(self.retopo_generate_btn)
        retopo_buttons_layout.addWidget(self.retopo_optimize_btn)
        retopo_layout.addLayout(retopo_buttons_layout)
        
        retopo_group.setLayout(retopo_layout)
        layout.addWidget(retopo_group)
        
        layout.addStretch()
        widget.setLayout(layout)
        
        return widget
        
    def create_display_tab(self):
        """创建显示设置选项卡"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # 显示模式
        display_mode_group = QGroupBox("显示模式")
        display_mode_layout = QVBoxLayout()
        
        self.display_mode_combo = QComboBox()
        self.display_mode_combo.addItems(["着色", "线框", "纹理", "材质捕捉", "顶点"])
        display_mode_layout.addWidget(self.display_mode_combo)
        
        display_mode_group.setLayout(display_mode_layout)
        layout.addWidget(display_mode_group)
        
        # 叠加显示
        overlay_group = QGroupBox("叠加显示")
        overlay_layout = QVBoxLayout()
        
        self.show_wireframe = QCheckBox("显示线框")
        self.show_vertices = QCheckBox("显示顶点")
        self.show_normals = QCheckBox("显示法线")
        self.show_mask = QCheckBox("显示蒙版")
        
        overlay_layout.addWidget(self.show_wireframe)
        overlay_layout.addWidget(self.show_vertices)
        overlay_layout.addWidget(self.show_normals)
        overlay_layout.addWidget(self.show_mask)
        
        overlay_group.setLayout(overlay_layout)
        layout.addWidget(overlay_group)
        
        # 光照设置
        lighting_group = QGroupBox("光照")
        lighting_layout = QGridLayout()
        
        lighting_layout.addWidget(QLabel("光源强度:"), 0, 0)
        self.light_intensity_slider = QSlider(Qt.Horizontal)
        self.light_intensity_slider.setRange(1, 100)
        self.light_intensity_slider.setValue(80)
        lighting_layout.addWidget(self.light_intensity_slider, 0, 1)
        
        lighting_layout.addWidget(QLabel("环境光:"), 1, 0)
        self.ambient_intensity_slider = QSlider(Qt.Horizontal)
        self.ambient_intensity_slider.setRange(1, 100)
        self.ambient_intensity_slider.setValue(30)
        lighting_layout.addWidget(self.ambient_intensity_slider, 1, 1)
        
        lighting_group.setLayout(lighting_layout)
        layout.addWidget(lighting_group)
        
        layout.addStretch()
        widget.setLayout(layout)
        
        return widget
        
    def update_brush_size(self, value):
        """更新笔刷大小显示"""
        size = value / 100.0 * 2.0
        self.brush_size_label.setText(f"{size:.1f}")
        
    def update_brush_strength(self, value):
        """更新笔刷强度显示"""
        strength = value / 100.0 * 2.0
        self.brush_strength_label.setText(f"{strength:.1f}")
        
    def update_brush_falloff(self, value):
        """更新笔刷衰减显示"""
        falloff = value / 100.0 * 5.0
        self.brush_falloff_label.setText(f"{falloff:.1f}")
        
    def update_brush_spacing(self, value):
        """更新笔刷间距显示"""
        spacing = value / 100.0 * 0.5
        self.brush_spacing_label.setText(f"{spacing:.2f}")


# 图层管理面板
class LayerManager(QWidget):
    """图层管理面板"""
    
    layerSelected = pyqtSignal(int)
    layerVisibilityChanged = pyqtSignal(int, bool)
    
    def __init__(self, parent=None):
        super(LayerManager, self).__init__(parent)
        
        self.layers = []
        self.init_ui()
        
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout()
        
        # 工具栏
        toolbar_layout = QHBoxLayout()
        
        self.add_layer_btn = QPushButton("+")
        self.add_layer_btn.setMaximumWidth(30)
        self.remove_layer_btn = QPushButton("-")
        self.remove_layer_btn.setMaximumWidth(30)
        self.duplicate_layer_btn = QPushButton("复制")
        
        toolbar_layout.addWidget(self.add_layer_btn)
        toolbar_layout.addWidget(self.remove_layer_btn)
        toolbar_layout.addWidget(self.duplicate_layer_btn)
        toolbar_layout.addStretch()
        
        layout.addLayout(toolbar_layout)
        
        # 图层列表
        self.layer_list = QListWidget()
        layout.addWidget(self.layer_list)
        
        self.setLayout(layout)
        
        # 连接信号
        self.add_layer_btn.clicked.connect(self.add_layer)
        self.remove_layer_btn.clicked.connect(self.remove_layer)
        self.duplicate_layer_btn.clicked.connect(self.duplicate_layer)
        self.layer_list.itemSelectionChanged.connect(self.on_layer_selected)
        
        # 添加初始图层
        self.add_layer("基础网格")
        
    def add_layer(self, name=None):
        """添加图层"""
        if name is None:
            name = f"图层 {len(self.layers) + 1}"
            
        layer = {
            'name': name,
            'visible': True,
            'opacity': 1.0,
            'blend_mode': 'add',
            'data': None  # 图层数据
        }
        
        self.layers.append(layer)
        
        # 添加到列表
        item = QListWidgetItem(name)
        item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
        item.setCheckState(Qt.Checked)
        self.layer_list.addItem(item)
        
        # 选择新图层
        self.layer_list.setCurrentItem(item)
        
    def remove_layer(self):
        """移除当前图层"""
        current_row = self.layer_list.currentRow()
        if current_row >= 0 and len(self.layers) > 1:  # 至少保留一个图层
            self.layer_list.takeItem(current_row)
            self.layers.pop(current_row)
            
    def duplicate_layer(self):
        """复制当前图层"""
        current_row = self.layer_list.currentRow()
        if current_row >= 0:
            current_layer = self.layers[current_row]
            new_name = f"{current_layer['name']} 复制"
            self.add_layer(new_name)
            
    def on_layer_selected(self):
        """图层选择变化"""
        current_row = self.layer_list.currentRow()
        if current_row >= 0:
            self.layerSelected.emit(current_row)
            
    def on_item_changed(self, item):
        """图层项变化（可见性）"""
        row = self.layer_list.row(item)
        if row >= 0:
            visible = item.checkState() == Qt.Checked
            self.layers[row]['visible'] = visible
            self.layerVisibilityChanged.emit(row, visible)


# 增强版主窗口
class EnhancedSculptureSystem(QMainWindow):
    """增强版雕塑系统主窗口"""
    
    def __init__(self):
        super(EnhancedSculptureSystem, self).__init__()
        
        self.undo_stack = deque(maxlen=50)  # 撤销栈
        self.redo_stack = deque(maxlen=50)  # 重做栈
        
        self.init_ui()
        
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("高级雕塑系统 - 专业版")
        self.setGeometry(100, 100, 1600, 1000)
        
        # 设置应用程序图标和样式
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2b2b2b;
                color: #cccccc;
            }
            QToolBar {
                background-color: #3c3c3c;
                border: none;
                spacing: 2px;
            }
            QToolButton {
                background-color: #404040;
                border: 1px solid #5a5a5a;
                border-radius: 3px;
                padding: 5px;
                color: #cccccc;
            }
            QToolButton:hover {
                background-color: #505050;
            }
            QToolButton:pressed {
                background-color: #606060;
            }
            QToolButton:checked {
                background-color: #0078d7;
            }
            QDockWidget {
                titlebar-close-icon: url(close.png);
                titlebar-normal-icon: url(float.png);
            }
            QDockWidget::title {
                background-color: #404040;
                padding: 5px;
                text-align: center;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #5a5a5a;
                border-radius: 5px;
                margin-top: 1ex;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 5px;
            }
        """)
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout()
        central_widget.setLayout(main_layout)
        
        # 创建3D视图
        self.viewer = EnhancedSculptureViewer()
        main_layout.addWidget(self.viewer)
        
        # 创建工具设置面板
        self.tool_settings = AdvancedToolSettings()
        
        # 创建图层管理器
        self.layer_manager = LayerManager()
        
        # 创建停靠窗口
        self.create_dock_widgets()
        
        # 创建工具栏
        self.create_toolbars()
        
        # 创建菜单栏
        self.create_menubar()
        
        # 创建状态栏
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("就绪")
        
        # 连接信号
        self.viewer.toolApplied.connect(self.on_tool_applied)
        self.viewer.cameraMoved.connect(self.on_camera_moved)
        self.layer_manager.layerSelected.connect(self.on_layer_selected)
        self.layer_manager.layerVisibilityChanged.connect(self.on_layer_visibility_changed)
        
        # 初始化网格
        self.viewer.mesh.create_sphere(1.0, 32, 32)
        
    def create_dock_widgets(self):
        """创建停靠窗口"""
        # 工具设置停靠窗口
        tool_dock = QDockWidget("工具设置", self)
        tool_dock.setWidget(self.tool_settings)
        tool_dock.setAllowedAreas(Qt.RightDockWidgetArea | Qt.LeftDockWidgetArea)
        self.addDockWidget(Qt.RightDockWidgetArea, tool_dock)
        
        # 图层管理停靠窗口
        layer_dock = QDockWidget("图层管理", self)
        layer_dock.setWidget(self.layer_manager)
        layer_dock.setAllowedAreas(Qt.RightDockWidgetArea | Qt.LeftDockWidgetArea)
        self.addDockWidget(Qt.RightDockWidgetArea, layer_dock)
        
        # 对象管理停靠窗口
        self.object_manager = QTreeWidget()
        self.object_manager.setHeaderLabel("场景对象")
        object_dock = QDockWidget("场景", self)
        object_dock.setWidget(self.object_manager)
        object_dock.setAllowedAreas(Qt.RightDockWidgetArea | Qt.LeftDockWidgetArea)
        self.addDockWidget(Qt.LeftDockWidgetArea, object_dock)
        
    def create_toolbars(self):
        """创建工具栏"""
        # 主工具栏
        main_toolbar = QToolBar("主工具栏")
        main_toolbar.setIconSize(QSize(24, 24))
        self.addToolBar(Qt.TopToolBarArea, main_toolbar)
        
        # 工具按钮
        self.sculpt_tool = QAction(QIcon("icons/sculpt.png"), "雕刻工具", self)
        self.sculpt_tool.setCheckable(True)
        self.sculpt_tool.setChecked(True)
        self.sculpt_tool.setShortcut(QKeySequence("S"))
        main_toolbar.addAction(self.sculpt_tool)
        
        self.smooth_tool = QAction(QIcon("icons/smooth.png"), "平滑工具", self)
        self.smooth_tool.setCheckable(True)
        self.smooth_tool.setShortcut(QKeySequence("Shift+S"))
        main_toolbar.addAction(self.smooth_tool)
        
        self.flatten_tool = QAction(QIcon("icons/flatten.png"), "平整工具", self)
        self.flatten_tool.setCheckable(True)
        main_toolbar.addAction(self.flatten_tool)
        
        self.grab_tool = QAction(QIcon("icons/grab.png"), "抓取工具", self)
        self.grab_tool.setCheckable(True)
        self.grab_tool.setShortcut(QKeySequence("G"))
        main_toolbar.addAction(self.grab_tool)
        
        self.mask_tool = QAction(QIcon("icons/mask.png"), "蒙版工具", self)
        self.mask_tool.setCheckable(True)
        self.mask_tool.setShortcut(QKeySequence("M"))
        main_toolbar.addAction(self.mask_tool)
        
        main_toolbar.addSeparator()
        
        # 变换工具
        self.move_tool = QAction(QIcon("icons/move.png"), "移动工具", self)
        self.move_tool.setCheckable(True)
        self.move_tool.setShortcut(QKeySequence("W"))
        main_toolbar.addAction(self.move_tool)
        
        self.rotate_tool = QAction(QIcon("icons/rotate.png"), "旋转工具", self)
        self.rotate_tool.setCheckable(True)
        self.rotate_tool.setShortcut(QKeySequence("E"))
        main_toolbar.addAction(self.rotate_tool)
        
        self.scale_tool = QAction(QIcon("icons/scale.png"), "缩放工具", self)
        self.scale_tool.setCheckable(True)
        self.scale_tool.setShortcut(QKeySequence("R"))
        main_toolbar.addAction(self.scale_tool)
        
        # 创建工具组（互斥）
        self.tool_group = QActionGroup(self)
        self.tool_group.addAction(self.sculpt_tool)
        self.tool_group.addAction(self.smooth_tool)
        self.tool_group.addAction(self.flatten_tool)
        self.tool_group.addAction(self.grab_tool)
        self.tool_group.addAction(self.mask_tool)
        self.tool_group.addAction(self.move_tool)
        self.tool_group.addAction(self.rotate_tool)
        self.tool_group.addAction(self.scale_tool)
        
        # 连接工具信号
        self.sculpt_tool.triggered.connect(lambda: self.set_tool("sculpt"))
        self.smooth_tool.triggered.connect(lambda: self.set_tool("smooth"))
        self.flatten_tool.triggered.connect(lambda: self.set_tool("flatten"))
        self.grab_tool.triggered.connect(lambda: self.set_tool("grab"))
        self.mask_tool.triggered.connect(lambda: self.set_tool("mask"))
        self.move_tool.triggered.connect(lambda: self.set_tool("move"))
        self.rotate_tool.triggered.connect(lambda: self.set_tool("rotate"))
        self.scale_tool.triggered.connect(lambda: self.set_tool("scale"))
        
        # 显示工具栏
        display_toolbar = QToolBar("显示工具栏")
        self.addToolBar(Qt.TopToolBarArea, display_toolbar)
        
        self.shaded_mode = QAction(QIcon("icons/shaded.png"), "着色模式", self)
        self.shaded_mode.setCheckable(True)
        self.shaded_mode.setChecked(True)
        display_toolbar.addAction(self.shaded_mode)
        
        self.wireframe_mode = QAction(QIcon("icons/wireframe.png"), "线框模式", self)
        self.wireframe_mode.setCheckable(True)
        self.wireframe_mode.setShortcut(QKeySequence("Z"))
        display_toolbar.addAction(self.wireframe_mode)
        
        self.textured_mode = QAction(QIcon("icons/textured.png"), "纹理模式", self)
        self.textured_mode.setCheckable(True)
        display_toolbar.addAction(self.textured_mode)
        
        # 显示模式组
        self.display_group = QActionGroup(self)
        self.display_group.addAction(self.shaded_mode)
        self.display_group.addAction(self.wireframe_mode)
        self.display_group.addAction(self.textured_mode)
        
        # 连接显示模式信号
        self.shaded_mode.triggered.connect(lambda: self.set_display_mode("shaded"))
        self.wireframe_mode.triggered.connect(lambda: self.set_display_mode("wireframe"))
        self.textured_mode.triggered.connect(lambda: self.set_display_mode("textured"))
        
    def create_menubar(self):
        """创建菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu('文件')
        
        new_action = QAction('新建项目', self)
        new_action.setShortcut(QKeySequence.New)
        new_action.triggered.connect(self.new_project)
        file_menu.addAction(new_action)
        
        open_action = QAction('打开项目', self)
        open_action.setShortcut(QKeySequence.Open)
        open_action.triggered.connect(self.open_project)
        file_menu.addAction(open_action)
        
        save_action = QAction('保存项目', self)
        save_action.setShortcut(QKeySequence.Save)
        save_action.triggered.connect(self.save_project)
        file_menu.addAction(save_action)
        
        file_menu.addSeparator()
        
        import_action = QAction('导入模型', self)
        import_action.triggered.connect(self.import_model)
        file_menu.addAction(import_action)
        
        export_action = QAction('导出模型', self)
        export_action.triggered.connect(self.export_model)
        file_menu.addAction(export_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction('退出', self)
        exit_action.setShortcut(QKeySequence.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 编辑菜单
        edit_menu = menubar.addMenu('编辑')
        
        undo_action = QAction('撤销', self)
        undo_action.setShortcut(QKeySequence.Undo)
        undo_action.triggered.connect(self.undo)
        edit_menu.addAction(undo_action)
        
        redo_action = QAction('重做', self)
        redo_action.setShortcut(QKeySequence.Redo)
        redo_action.triggered.connect(self.redo)
        edit_menu.addAction(redo_action)
        
        edit_menu.addSeparator()
        
        preferences_action = QAction('偏好设置', self)
        preferences_action.triggered.connect(self.show_preferences)
        edit_menu.addAction(preferences_action)
        
        # 雕刻菜单
        sculpt_menu = menubar.addMenu('雕刻')
        
        dynotopo_action = QAction('动态拓扑', self)
        dynotopo_action.setCheckable(True)
        dynotopo_action.triggered.connect(self.toggle_dynotopo)
        sculpt_menu.addAction(dynotopo_action)
        
        multires_action = QAction('多分辨率雕刻', self)
        multires_action.triggered.connect(self.multires_sculpt)
        sculpt_menu.addAction(multires_action)
        
        sculpt_menu.addSeparator()
        
        symmetrize_action = QAction('对称化', self)
        symmetrize_action.triggered.connect(self.symmetrize)
        sculpt_menu.addAction(symmetrize_action)
        
        # 网格菜单
        mesh_menu = menubar.addMenu('网格')
        
        subdivide_action = QAction('细分', self)
        subdivide_action.triggered.connect(self.subdivide_mesh)
        mesh_menu.addAction(subdivide_action)
        
        decimate_action = QAction('简化', self)
        decimate_action.triggered.connect(self.decimate_mesh)
        mesh_menu.addAction(decimate_action)
        
        mesh_menu.addSeparator()
        
        retopologize_action = QAction('自动重拓扑', self)
        retopologize_action.triggered.connect(self.retopologize)
        mesh_menu.addAction(retopologize_action)
        
    def set_tool(self, tool):
        """设置当前工具"""
        self.viewer.current_tool = tool
        self.status_bar.showMessage(f"当前工具: {tool}")
        
        # 更新变换模式
        if tool in ["move", "rotate", "scale"]:
            self.viewer.transform_mode = tool
        else:
            self.viewer.transform_mode = None
            
        self.viewer.update()
        
    def set_display_mode(self, mode):
        """设置显示模式"""
        self.viewer.display_mode = mode
        self.viewer.update()
        
    def on_tool_applied(self, tool, intensity, position, radius, falloff, symmetry):
        """工具应用事件处理"""
        # 保存状态到撤销栈
        self.save_undo_state()
        
        tool_name = tool.capitalize()
        pos_str = f"{position[0]:.2f}, {position[1]:.2f}, {position[2]:.2f}"
        self.status_bar.showMessage(f"应用工具: {tool_name} - 位置: {pos_str}")
        
    def on_camera_moved(self, rx, ry, distance):
        """相机移动事件处理"""
        self.status_bar.showMessage(f"相机: 距离={distance:.1f}, 旋转=({rx:.1f}, {ry:.1f})")
        
    def on_layer_selected(self, layer_index):
        """图层选择事件处理"""
        self.viewer.mesh.active_layer = layer_index
        self.status_bar.showMessage(f"切换到图层: {layer_index}")
        
    def on_layer_visibility_changed(self, layer_index, visible):
        """图层可见性变化事件处理"""
        state = "显示" if visible else "隐藏"
        self.status_bar.showMessage(f"{state}图层: {layer_index}")
        
    def new_project(self):
        """新建项目"""
        reply = QMessageBox.question(self, '新建项目', 
                                    '是否保存当前项目?',
                                    QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
        
        if reply == QMessageBox.Yes:
            self.save_project()
        elif reply == QMessageBox.Cancel:
            return
            
        # 重置场景
        self.viewer.mesh = EnhancedMesh()
        self.viewer.mesh.create_sphere(1.0, 32, 32)
        self.layer_manager.layers.clear()
        self.layer_manager.layer_list.clear()
        self.layer_manager.add_layer("基础网格")
        
        self.viewer.update()
        self.status_bar.showMessage("已创建新项目")
        
    def open_project(self):
        """打开项目"""
        filename, _ = QFileDialog.getOpenFileName(self, '打开项目', 
                                                 '', '雕塑项目 (*.sculpt)')
        if filename:
            # 这里应该实现实际的项目加载逻辑
            self.status_bar.showMessage(f"已打开项目: {filename}")
            
    def save_project(self):
        """保存项目"""
        filename, _ = QFileDialog.getSaveFileName(self, '保存项目', 
                                                 '', '雕塑项目 (*.sculpt)')
        if filename:
            # 这里应该实现实际的项目保存逻辑
            self.status_bar.showMessage(f"已保存项目: {filename}")
            
    def import_model(self):
        """导入模型"""
        filename, _ = QFileDialog.getOpenFileName(self, '导入模型', 
                                                 '', '3D模型 (*.obj *.stl *.ply)')
        if filename:
            # 这里应该实现实际的模型导入逻辑
            self.status_bar.showMessage(f"已导入模型: {filename}")
            
    def export_model(self):
        """导出模型"""
        filename, _ = QFileDialog.getSaveFileName(self, '导出模型', 
                                                 '', '3D模型 (*.obj *.stl *.ply)')
        if filename:
            # 这里应该实现实际的模型导出逻辑
            self.status_bar.showMessage(f"已导出模型: {filename}")
            
    def undo(self):
        """撤销操作"""
        if self.undo_stack:
            state = self.undo_stack.pop()
            self.redo_stack.append(self.get_current_state())
            self.apply_state(state)
            self.status_bar.showMessage("撤销")
            
    def redo(self):
        """重做操作"""
        if self.redo_stack:
            state = self.redo_stack.pop()
            self.undo_stack.append(self.get_current_state())
            self.apply_state(state)
            self.status_bar.showMessage("重做")
            
    def save_undo_state(self):
        """保存当前状态到撤销栈"""
        state = self.get_current_state()
        self.undo_stack.append(state)
        self.redo_stack.clear()  # 清空重做栈
        
    def get_current_state(self):
        """获取当前状态"""
        # 简化实现：保存网格数据
        return {
            'vertices': self.viewer.mesh.vertices.copy(),
            'faces': self.viewer.mesh.faces.copy(),
            'normals': self.viewer.mesh.normals.copy()
        }
        
    def apply_state(self, state):
        """应用保存的状态"""
        self.viewer.mesh.vertices = state['vertices']
        self.viewer.mesh.faces = state['faces']
        self.viewer.mesh.normals = state['normals']
        self.viewer.mesh.modified = True
        self.viewer.update()
        
    def toggle_dynotopo(self, enabled):
        """切换动态拓扑"""
        self.viewer.mesh.dynamic_topology = enabled
        state = "启用" if enabled else "禁用"
        self.status_bar.showMessage(f"{state}动态拓扑")
        
    def multires_sculpt(self):
        """多分辨率雕刻"""
        self.status_bar.showMessage("进入多分辨率雕刻模式")
        
    def symmetrize(self):
        """对称化网格"""
        self.status_bar.showMessage("应用对称化")
        
    def subdivide_mesh(self):
        """细分网格"""
        self.viewer.mesh.subdivide()
        self.viewer.update()
        self.status_bar.showMessage("网格已细分")
        
    def decimate_mesh(self):
        """简化网格"""
        self.viewer.mesh.decimate()
        self.viewer.update()
        self.status_bar.showMessage("网格已简化")
        
    def retopologize(self):
        """自动重拓扑"""
        self.status_bar.showMessage("开始自动重拓扑...")
        
    def show_preferences(self):
        """显示偏好设置对话框"""
        self.status_bar.showMessage("打开偏好设置")


def main():
    """主函数"""
    app = QApplication(sys.argv)
    
    # 设置应用程序样式
    app.setStyle('Fusion')
    
    # 设置应用程序字体
    font = QFont("Arial", 10)
    app.setFont(font)
    
    # 创建并显示主窗口
    window = EnhancedSculptureSystem()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()