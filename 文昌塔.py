import sys
import math
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QSlider, QLabel, QGroupBox, 
                             QPushButton, QCheckBox, QComboBox, QSpinBox,
                             QDoubleSpinBox, QSplitter)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QKeyEvent, QFont
from PyQt5.QtOpenGL import QGLWidget, QGLFormat
from OpenGL.GL import *
from OpenGL.GLU import *
import numpy as np


class WenChangTower:
    def __init__(self):
        self.layers = 7  # 文昌塔通常为7层
        self.base_radius = 1.5
        self.layer_height = 0.8
        self.taper_factor = 0.85  # 每层缩小的比例
        self.eaves_overhang = 0.2  # 檐的悬挑长度
        self.show_windows = True
        self.show_decorations = True
        self.show_details = True
        self.material_type = 0  # 0: 石材, 1: 木材, 2: 混合
        
    def set_material(self, material_type):
        """设置材质类型"""
        self.material_type = material_type
        
    def set_layers(self, layers):
        """设置塔的层数"""
        self.layers = layers
        
    def set_show_windows(self, show):
        """设置是否显示窗户"""
        self.show_windows = show
        
    def set_show_decorations(self, show):
        """设置是否显示装饰"""
        self.show_decorations = show
        
    def set_show_details(self, show):
        """设置是否显示细节"""
        self.show_details = show
        
    def get_material_colors(self, layer_index):
        """根据材质类型和层数返回对应的颜色"""
        if self.material_type == 0:  # 石材
            if layer_index == 0:
                return (0.7, 0.6, 0.5)  # 基座颜色
            else:
                return (0.8, 0.75, 0.7)  # 塔身颜色
        elif self.material_type == 1:  # 木材
            if layer_index == 0:
                return (0.6, 0.4, 0.2)  # 基座颜色
            else:
                return (0.8, 0.7, 0.5)  # 塔身颜色
        else:  # 混合
            if layer_index == 0:
                return (0.7, 0.6, 0.5)  # 基座颜色
            elif layer_index % 2 == 0:
                return (0.8, 0.75, 0.7)  # 石材层
            else:
                return (0.8, 0.7, 0.5)  # 木材层
                
    def draw_base(self):
        """绘制塔基"""
        glColor3f(*self.get_material_colors(0))
        glPushMatrix()
        glTranslatef(0, -0.2, 0)
        glScalef(2.0, 0.4, 2.0)
        self.draw_cube()
        glPopMatrix()
        
    def draw_cube(self):
        """绘制立方体"""
        glBegin(GL_QUADS)
        
        # 前面
        glNormal3f(0, 0, 1)
        glVertex3f(-0.5, -0.5, 0.5)
        glVertex3f(0.5, -0.5, 0.5)
        glVertex3f(0.5, 0.5, 0.5)
        glVertex3f(-0.5, 0.5, 0.5)
        
        # 后面
        glNormal3f(0, 0, -1)
        glVertex3f(-0.5, -0.5, -0.5)
        glVertex3f(-0.5, 0.5, -0.5)
        glVertex3f(0.5, 0.5, -0.5)
        glVertex3f(0.5, -0.5, -0.5)
        
        # 左面
        glNormal3f(-1, 0, 0)
        glVertex3f(-0.5, -0.5, -0.5)
        glVertex3f(-0.5, -0.5, 0.5)
        glVertex3f(-0.5, 0.5, 0.5)
        glVertex3f(-0.5, 0.5, -0.5)
        
        # 右面
        glNormal3f(1, 0, 0)
        glVertex3f(0.5, -0.5, -0.5)
        glVertex3f(0.5, 0.5, -0.5)
        glVertex3f(0.5, 0.5, 0.5)
        glVertex3f(0.5, -0.5, 0.5)
        
        # 上面
        glNormal3f(0, 1, 0)
        glVertex3f(-0.5, 0.5, -0.5)
        glVertex3f(-0.5, 0.5, 0.5)
        glVertex3f(0.5, 0.5, 0.5)
        glVertex3f(0.5, 0.5, -0.5)
        
        # 下面
        glNormal3f(0, -1, 0)
        glVertex3f(-0.5, -0.5, -0.5)
        glVertex3f(0.5, -0.5, -0.5)
        glVertex3f(0.5, -0.5, 0.5)
        glVertex3f(-0.5, -0.5, 0.5)
        
        glEnd()
        
    def draw_octagon_prism(self, sides, radius, height):
        """绘制八角棱柱"""
        # 侧面
        glBegin(GL_QUAD_STRIP)
        for i in range(sides + 1):
            angle = 2.0 * math.pi * i / sides
            x = radius * math.cos(angle)
            z = radius * math.sin(angle)
            
            glNormal3f(math.cos(angle), 0, math.sin(angle))
            glVertex3f(x, 0, z)
            glVertex3f(x, height, z)
        glEnd()
        
        # 顶部
        glBegin(GL_POLYGON)
        glNormal3f(0, 1, 0)
        for i in range(sides):
            angle = 2.0 * math.pi * i / sides
            x = radius * math.cos(angle)
            z = radius * math.sin(angle)
            glVertex3f(x, height, z)
        glEnd()
        
        # 底部
        glBegin(GL_POLYGON)
        glNormal3f(0, -1, 0)
        for i in range(sides):
            angle = 2.0 * math.pi * i / sides
            x = radius * math.cos(angle)
            z = radius * math.sin(angle)
            glVertex3f(x, 0, z)
        glEnd()
    
    def draw_eaves(self, radius, height, layer_index):
        """绘制塔檐"""
        glColor3f(0.7, 0.6, 0.3)  # 木质檐颜色
        glPushMatrix()
        glTranslatef(0, height, 0)
        
        # 主檐
        glPushMatrix()
        glScalef(radius + self.eaves_overhang, 0.05, radius + self.eaves_overhang)
        self.draw_cube()
        glPopMatrix()
        
        # 檐角装饰
        if self.show_decorations and layer_index < self.layers - 1:  # 顶层不加装饰
            for i in range(8):
                angle = 2.0 * math.pi * i / 8
                x = (radius + self.eaves_overhang * 0.5) * math.cos(angle)
                z = (radius + self.eaves_overhang * 0.5) * math.sin(angle)
                
                glPushMatrix()
                glTranslatef(x, 0.05, z)
                
                # 檐角上翘
                glColor3f(0.9, 0.1, 0.1)  # 红色装饰
                glRotatef(45, 0, 0, 1)
                glScalef(0.05, 0.2, 0.05)
                self.draw_cone(10, 2)
                
                glPopMatrix()
        
        glPopMatrix()
    
    def draw_cone(self, slices, stacks):
        """绘制圆锥"""
        glBegin(GL_TRIANGLE_FAN)
        glNormal3f(0, 1, 0)
        glVertex3f(0, 1, 0)  # 顶点
        
        for i in range(slices + 1):
            angle = 2.0 * math.pi * i / slices
            x = math.cos(angle)
            z = math.sin(angle)
            glNormal3f(x, 0.5, z)
            glVertex3f(x, 0, z)
        glEnd()
        
        # 底面
        glBegin(GL_POLYGON)
        glNormal3f(0, -1, 0)
        for i in range(slices):
            angle = 2.0 * math.pi * i / slices
            x = math.cos(angle)
            z = math.sin(angle)
            glVertex3f(x, 0, z)
        glEnd()
    
    def draw_windows(self, radius, height, layer_index):
        """绘制窗户"""
        if not self.show_windows:
            return
            
        glColor3f(0.3, 0.3, 0.5)  # 窗框颜色
        
        for i in range(4):  # 四个主要方向开窗
            angle = 2.0 * math.pi * i / 4
            x = radius * 0.9 * math.cos(angle)
            z = radius * 0.9 * math.sin(angle)
            
            glPushMatrix()
            glTranslatef(x, height * 0.5, z)
            
            # 面向外侧
            if abs(x) > abs(z):
                glRotatef(90, 0, 1, 0)
            else:
                glRotatef(0, 0, 1, 0)
            
            # 绘制窗框
            glScalef(0.15, 0.2, 0.02)
            self.draw_cube()
            
            glPopMatrix()
    
    def draw_doors(self, radius, height):
        """绘制门"""
        if not self.show_details:
            return
            
        glColor3f(0.4, 0.2, 0.1)  # 木门颜色
        
        glPushMatrix()
        glTranslatef(0, height * 0.3, radius * 0.9)
        glScalef(0.3, 0.5, 0.05)
        self.draw_cube()
        glPopMatrix()
    
    def draw_pagoda_top(self, radius):
        """绘制塔顶"""
        if not self.show_details:
            return
            
        # 塔刹基座
        glColor3f(0.9, 0.8, 0.1)  # 金色
        glPushMatrix()
        glTranslatef(0, self.layer_height, 0)
        glScalef(radius * 0.5, 0.1, radius * 0.5)
        self.draw_cube()
        glPopMatrix()
        
        # 塔刹主体
        glPushMatrix()
        glTranslatef(0, self.layer_height + 0.1, 0)
        glScalef(0.1, 0.8, 0.1)
        self.draw_cube()
        glPopMatrix()
        
        # 相轮（多层圆环）
        for i in range(5):
            glPushMatrix()
            glTranslatef(0, self.layer_height + 0.2 + i * 0.15, 0)
            self.draw_sphere(0.08 + (4-i)*0.02, 10, 10)
            glPopMatrix()
        
        # 宝珠
        glColor3f(1.0, 0.9, 0.1)  # 亮金色
        glPushMatrix()
        glTranslatef(0, self.layer_height + 1.0, 0)
        self.draw_sphere(0.1, 15, 15)
        glPopMatrix()
    
    def draw_sphere(self, radius, slices, stacks):
        """绘制球体"""
        for i in range(stacks):
            lat0 = math.pi * (-0.5 + float(i) / stacks)
            z0 = math.sin(lat0)
            zr0 = math.cos(lat0)
            
            lat1 = math.pi * (-0.5 + float(i+1) / stacks)
            z1 = math.sin(lat1)
            zr1 = math.cos(lat1)
            
            glBegin(GL_QUAD_STRIP)
            for j in range(slices + 1):
                lng = 2 * math.pi * float(j) / slices
                x = math.cos(lng)
                y = math.sin(lng)
                
                glNormal3f(x * zr0, y * zr0, z0)
                glVertex3f(radius * x * zr0, radius * y * zr0, radius * z0)
                glNormal3f(x * zr1, y * zr1, z1)
                glVertex3f(radius * x * zr1, radius * y * zr1, radius * z1)
            glEnd()
    
    def draw(self):
        """绘制整个文昌塔"""
        current_radius = self.base_radius
        current_height = 0
        
        # 绘制塔基
        self.draw_base()
        
        # 绘制各层塔身
        for i in range(self.layers):
            # 塔身
            glColor3f(*self.get_material_colors(i+1))
            glPushMatrix()
            glTranslatef(0, current_height, 0)
            self.draw_octagon_prism(8, current_radius, self.layer_height)
            glPopMatrix()
            
            # 窗户
            self.draw_windows(current_radius, current_height, i)
            
            # 第一层有门
            if i == 0:
                self.draw_doors(current_radius, self.layer_height)
            
            # 塔檐
            self.draw_eaves(current_radius, current_height + self.layer_height, i)
            
            # 更新下一层的位置和尺寸
            current_height += self.layer_height + 0.1  # 加上檐的高度
            current_radius *= self.taper_factor
        
        # 绘制塔顶
        self.draw_pagoda_top(current_radius)


class GLWidget(QGLWidget):
    def __init__(self, parent=None):
        # 设置OpenGL格式
        fmt = QGLFormat()
        fmt.setSampleBuffers(True)
        fmt.setSamples(4)  # 4x多重采样抗锯齿
        super(GLWidget, self).__init__(fmt, parent)
        
        self.tower = WenChangTower()
        self.x_rotation = 0
        self.y_rotation = 0
        self.z_rotation = 0
        self.zoom = -15
        self.auto_rotate = False
        self.show_axes = True
        self.show_grid = True
        self.lighting_enabled = True
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.updateGL)
        self.timer.start(30)  # 约33 FPS
        
    def initializeGL(self):
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        glEnable(GL_COLOR_MATERIAL)
        glEnable(GL_NORMALIZE)
        
        # 设置光源
        glLightfv(GL_LIGHT0, GL_POSITION, [5, 5, 5, 1])
        glLightfv(GL_LIGHT0, GL_AMBIENT, [0.3, 0.3, 0.3, 1])
        glLightfv(GL_LIGHT0, GL_DIFFUSE, [0.8, 0.8, 0.8, 1])
        glLightfv(GL_LIGHT0, GL_SPECULAR, [1, 1, 1, 1])
        
        # 设置材质属性
        glMaterialfv(GL_FRONT, GL_SPECULAR, [1, 1, 1, 1])
        glMaterialf(GL_FRONT, GL_SHININESS, 50.0)
        
        glClearColor(0.53, 0.81, 0.98, 1.0)  # 天蓝色背景
        
    def resizeGL(self, w, h):
        glViewport(0, 0, w, h)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        aspect = w / h if h != 0 else 1.0
        gluPerspective(45, aspect, 1.0, 100.0)
        glMatrixMode(GL_MODELVIEW)
        
    def paintGL(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        
        glTranslatef(0, 0, self.zoom)
        glRotatef(self.x_rotation, 1, 0, 0)
        glRotatef(self.y_rotation, 0, 1, 0)
        glRotatef(self.z_rotation, 0, 0, 1)
        
        # 自动旋转
        if self.auto_rotate:
            self.y_rotation += 0.5
        
        # 绘制坐标轴
        if self.show_axes:
            self.draw_axes()
            
        # 绘制网格地面
        if self.show_grid:
            self.draw_grid()
        
        # 绘制文昌塔
        self.tower.draw()
        
    def draw_axes(self):
        """绘制坐标轴"""
        glDisable(GL_LIGHTING)
        glBegin(GL_LINES)
        
        # X轴 - 红色
        glColor3f(1, 0, 0)
        glVertex3f(0, 0, 0)
        glVertex3f(3, 0, 0)
        
        # Y轴 - 绿色
        glColor3f(0, 1, 0)
        glVertex3f(0, 0, 0)
        glVertex3f(0, 3, 0)
        
        # Z轴 - 蓝色
        glColor3f(0, 0, 1)
        glVertex3f(0, 0, 0)
        glVertex3f(0, 0, 3)
        
        glEnd()
        glEnable(GL_LIGHTING)
        
    def draw_grid(self):
        """绘制网格地面"""
        glDisable(GL_LIGHTING)
        glColor3f(0.5, 0.5, 0.5)
        glBegin(GL_LINES)
        
        size = 10
        step = 1
        
        for i in range(-size, size+1, step):
            glVertex3f(i, -0.5, -size)
            glVertex3f(i, -0.5, size)
            glVertex3f(-size, -0.5, i)
            glVertex3f(size, -0.5, i)
            
        glEnd()
        glEnable(GL_LIGHTING)
        
    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_Left:
            self.y_rotation -= 5
        elif event.key() == Qt.Key_Right:
            self.y_rotation += 5
        elif event.key() == Qt.Key_Up:
            self.x_rotation -= 5
        elif event.key() == Qt.Key_Down:
            self.x_rotation += 5
        elif event.key() == Qt.Key_A:
            self.zoom += 0.5
        elif event.key() == Qt.Key_Z:
            self.zoom -= 0.5
        elif event.key() == Qt.Key_R:
            self.reset_view()
        elif event.key() == Qt.Key_L:
            self.lighting_enabled = not self.lighting_enabled
            if self.lighting_enabled:
                glEnable(GL_LIGHTING)
            else:
                glDisable(GL_LIGHTING)
        self.updateGL()
        
    def reset_view(self):
        """重置视图"""
        self.x_rotation = 0
        self.y_rotation = 0
        self.z_rotation = 0
        self.zoom = -15
        self.updateGL()
        
    def set_auto_rotate(self, enabled):
        """设置自动旋转"""
        self.auto_rotate = enabled
        
    def set_show_axes(self, show):
        """设置是否显示坐标轴"""
        self.show_axes = show
        
    def set_show_grid(self, show):
        """设置是否显示网格"""
        self.show_grid = show


class ControlPanel(QWidget):
    """控制面板"""
    material_changed = pyqtSignal(int)
    layers_changed = pyqtSignal(int)
    show_windows_changed = pyqtSignal(bool)
    show_decorations_changed = pyqtSignal(bool)
    show_details_changed = pyqtSignal(bool)
    auto_rotate_changed = pyqtSignal(bool)
    show_axes_changed = pyqtSignal(bool)
    show_grid_changed = pyqtSignal(bool)
    reset_view_signal = pyqtSignal()
    
    def __init__(self, parent=None):
        super(ControlPanel, self).__init__(parent)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # 文昌塔介绍
        info_group = QGroupBox("文昌塔介绍")
        info_layout = QVBoxLayout(info_group)
        info_label = QLabel(
            "文昌塔是中国传统风水建筑，通常为七层或九层的八角形塔。"
            "文昌塔象征学业进步、功名成就，常用于改善学业运势。"
            "塔的每一层都有特定的象征意义，代表不同的学习阶段和成就。"
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("QLabel { padding: 10px; }")
        info_layout.addWidget(info_label)
        layout.addWidget(info_group)
        
        # 塔结构控制
        structure_group = QGroupBox("塔结构控制")
        structure_layout = QVBoxLayout(structure_group)
        
        # 材质选择
        material_layout = QHBoxLayout()
        material_layout.addWidget(QLabel("材质:"))
        material_combo = QComboBox()
        material_combo.addItems(["石材", "木材", "混合"])
        material_combo.currentIndexChanged.connect(self.material_changed.emit)
        material_layout.addWidget(material_combo)
        structure_layout.addLayout(material_layout)
        
        # 层数控制
        layers_layout = QHBoxLayout()
        layers_layout.addWidget(QLabel("层数:"))
        layers_spin = QSpinBox()
        layers_spin.setRange(3, 13)
        layers_spin.setValue(7)
        layers_spin.valueChanged.connect(self.layers_changed.emit)
        layers_layout.addWidget(layers_spin)
        structure_layout.addLayout(layers_layout)
        
        layout.addWidget(structure_group)
        
        # 显示选项
        display_group = QGroupBox("显示选项")
        display_layout = QVBoxLayout(display_group)
        
        windows_check = QCheckBox("显示窗户")
        windows_check.setChecked(True)
        windows_check.toggled.connect(self.show_windows_changed.emit)
        display_layout.addWidget(windows_check)
        
        decorations_check = QCheckBox("显示装饰")
        decorations_check.setChecked(True)
        decorations_check.toggled.connect(self.show_decorations_changed.emit)
        display_layout.addWidget(decorations_check)
        
        details_check = QCheckBox("显示细节")
        details_check.setChecked(True)
        details_check.toggled.connect(self.show_details_changed.emit)
        display_layout.addWidget(details_check)
        
        axes_check = QCheckBox("显示坐标轴")
        axes_check.setChecked(True)
        axes_check.toggled.connect(self.show_axes_changed.emit)
        display_layout.addWidget(axes_check)
        
        grid_check = QCheckBox("显示网格")
        grid_check.setChecked(True)
        grid_check.toggled.connect(self.show_grid_changed.emit)
        display_layout.addWidget(grid_check)
        
        layout.addWidget(display_group)
        
        # 视图控制
        view_group = QGroupBox("视图控制")
        view_layout = QVBoxLayout(view_group)
        
        auto_rotate_check = QCheckBox("自动旋转")
        auto_rotate_check.toggled.connect(self.auto_rotate_changed.emit)
        view_layout.addWidget(auto_rotate_check)
        
        reset_btn = QPushButton("重置视图")
        reset_btn.clicked.connect(self.reset_view_signal.emit)
        view_layout.addWidget(reset_btn)
        
        layout.addWidget(view_group)
        
        # 控制说明
        control_group = QGroupBox("控制说明")
        control_layout = QVBoxLayout(control_group)
        control_label = QLabel(
            "键盘控制:\n"
            "← → : 左右旋转\n"
            "↑ ↓ : 上下旋转\n"
            "A/Z : 缩放\n"
            "R : 重置视图\n"
            "L : 切换光照\n\n"
            "鼠标控制:\n"
            "左键拖动: 旋转\n"
            "右键拖动: 缩放"
        )
        control_label.setWordWrap(True)
        control_label.setStyleSheet("QLabel { padding: 10px; }")
        control_layout.addWidget(control_label)
        layout.addWidget(control_group)
        
        layout.addStretch(1)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("文昌塔3D模型 - 完整实现")
        self.setGeometry(100, 100, 1400, 900)
        
        # 创建中央部件和布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # 创建OpenGL部件
        self.gl_widget = GLWidget()
        
        # 创建控制面板
        self.control_panel = ControlPanel()
        self.control_panel.setMaximumWidth(300)
        
        # 连接信号
        self.control_panel.material_changed.connect(self.gl_widget.tower.set_material)
        self.control_panel.layers_changed.connect(self.gl_widget.tower.set_layers)
        self.control_panel.show_windows_changed.connect(self.gl_widget.tower.set_show_windows)
        self.control_panel.show_decorations_changed.connect(self.gl_widget.tower.set_show_decorations)
        self.control_panel.show_details_changed.connect(self.gl_widget.tower.set_show_details)
        self.control_panel.auto_rotate_changed.connect(self.gl_widget.set_auto_rotate)
        self.control_panel.show_axes_changed.connect(self.gl_widget.set_show_axes)
        self.control_panel.show_grid_changed.connect(self.gl_widget.set_show_grid)
        self.control_panel.reset_view_signal.connect(self.gl_widget.reset_view)
        
        # 使用分割器
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self.gl_widget)
        splitter.addWidget(self.control_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 0)
        
        main_layout.addWidget(splitter)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # 设置应用程序字体
    font = QFont("Microsoft YaHei", 10)
    app.setFont(font)
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec_())