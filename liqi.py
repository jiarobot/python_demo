import sys
import numpy as np
import matplotlib
matplotlib.rc("font", family='Microsoft YaHei')
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.colors import Normalize
from matplotlib.tri import Triangulation
from scipy.sparse import coo_matrix, diags, linalg
from scipy.spatial import Delaunay
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QGroupBox, QPushButton, QSlider, QLabel, QComboBox, QDoubleSpinBox,
                             QSpinBox, QSplitter, QTabWidget, QFileDialog, QProgressBar, QCheckBox)
from PyQt5.QtCore import Qt, QTimer
import time

class RicciFlowSimulator:
    def __init__(self):
        self.vertices = None
        self.triangles = None
        self.initial_vertices = None
        self.curvature_history = []
        self.area_history = []
        self.step_count = 0
        self.surface_type = "gaussian"
        self.resolution = 30
        self.dt = 0.05
        self.paused = False
        self.curvature_visible = True
        
    def generate_initial_surface(self):
        """生成初始曲面"""
        if self.surface_type == "gaussian":
            self._gaussian_surface()
        elif self.surface_type == "sphere":
            self._spherical_surface()
        elif self.surface_type == "torus":
            self._torus_surface()
        elif self.surface_type == "saddle":
            self._saddle_surface()
        elif self.surface_type == "custom":
            self._custom_surface()
        else:
            self._gaussian_surface()
            
        self.initial_vertices = self.vertices.copy()
        self.curvature_history = []
        self.area_history = []
        self.step_count = 0
        
    def _gaussian_surface(self):
        """生成高斯曲面"""
        x = np.linspace(-2, 2, self.resolution)
        y = np.linspace(-2, 2, self.resolution)
        X, Y = np.meshgrid(x, y)
        
        # 多峰高斯曲面
        Z = (1.5 * np.exp(-(X-1)**2 - (Y-1)**2) +
             1.2 * np.exp(-(X+1)**2 - (Y+1)**2) +
             0.8 * np.exp(-(X-1)**2 - (Y+1)**2) +
             0.7 * np.exp(-(X+1)**2 - (Y-1)**2) -
             0.3 * (X**2 + Y**2))
        
        self._create_triangulation(X, Y, Z)
    
    def _spherical_surface(self):
        """生成球面"""
        u = np.linspace(0, 2 * np.pi, self.resolution)
        v = np.linspace(0, np.pi, self.resolution)
        U, V = np.meshgrid(u, v)
        
        # 球面参数方程
        X = np.cos(U) * np.sin(V)
        Y = np.sin(U) * np.sin(V)
        Z = np.cos(V)
        
        self._create_triangulation(X, Y, Z)
    
    def _torus_surface(self):
        """生成环面"""
        u = np.linspace(0, 2 * np.pi, self.resolution)
        v = np.linspace(0, 2 * np.pi, self.resolution)
        U, V = np.meshgrid(u, v)
        
        # 环面参数方程
        R, r = 1.5, 0.5
        X = (R + r * np.cos(V)) * np.cos(U)
        Y = (R + r * np.cos(V)) * np.sin(U)
        Z = r * np.sin(V)
        
        self._create_triangulation(X, Y, Z)
    
    def _saddle_surface(self):
        """生成鞍形曲面"""
        x = np.linspace(-2, 2, self.resolution)
        y = np.linspace(-2, 2, self.resolution)
        X, Y = np.meshgrid(x, y)
        Z = 0.5 * (X**2 - Y**2)
        
        self._create_triangulation(X, Y, Z)
        
    def _custom_surface(self):
        """生成自定义曲面"""
        x = np.linspace(-3, 3, self.resolution)
        y = np.linspace(-3, 3, self.resolution)
        X, Y = np.meshgrid(x, y)
        
        # 复杂的自定义曲面
        Z = (0.8 * np.sin(0.8*X) * np.cos(0.8*Y) +
            0.5 * np.exp(-0.3*(X**2 + Y**2)) -
            0.3 * np.sin(0.5*X) * np.cos(0.7*Y) +
            0.2 * np.cos(0.4*(X - Y)**2))
        
        self._create_triangulation(X, Y, Z)
    
    def _create_triangulation(self, X, Y, Z):
        """从网格点创建三角剖分"""
        points = np.column_stack([X.flatten(), Y.flatten()])
        tri = Delaunay(points)
        self.vertices = np.column_stack([X.flatten(), Y.flatten(), Z.flatten()])
        self.triangles = tri.simplices
    
    def compute_voronoi_areas(self):
        """计算每个顶点的Voronoi面积"""
        n_vertices = len(self.vertices)
        areas = np.zeros(n_vertices)
        
        for tri in self.triangles:
            v1, v2, v3 = self.vertices[tri]
            a = np.linalg.norm(v2 - v1)
            b = np.linalg.norm(v3 - v2)
            c = np.linalg.norm(v1 - v3)
            
            # 计算三角形面积 (海伦公式)
            s = (a + b + c) / 2
            tri_area = np.sqrt(s * (s - a) * (s - b) * (s - c))
            
            # 计算每个角的角度
            angles = np.zeros(3)
            angles[0] = np.arccos(np.clip((b**2 + c**2 - a**2) / (2 * b * c), -1, 1))
            angles[1] = np.arccos(np.clip((a**2 + c**2 - b**2) / (2 * a * c), -1, 1))
            angles[2] = np.arccos(np.clip((a**2 + b**2 - c**2) / (2 * a * b), -1, 1))
            
            # 计算每个顶点的贡献面积
            for i, idx in enumerate(tri):
                # 钝角三角形需要特殊处理
                if angles[i] > np.pi/2:
                    areas[idx] += tri_area / 2
                else:
                    areas[idx] += tri_area * (angles[i] / (2 * np.pi))
        
        return areas
    
    def compute_cotangent_weights(self):
        """计算余切权重拉普拉斯矩阵"""
        n_vertices = len(self.vertices)
        I = []
        J = []
        V = []
        diag = np.zeros(n_vertices)
        
        # 创建边的映射
        edge_map = {}
        for tri in self.triangles:
            for i in range(3):
                v1 = tri[i]
                v2 = tri[(i+1)%3]
                v3 = tri[(i+2)%3]
                
                # 确保v1 < v2
                if v1 > v2:
                    v1, v2 = v2, v1
                
                # 计算向量
                vec1 = self.vertices[v3] - self.vertices[v1]
                vec2 = self.vertices[v3] - self.vertices[v2]
                
                # 计算角度
                cos_angle = np.dot(vec1, vec2) / (np.linalg.norm(vec1)) * np.linalg.norm(vec2)
                angle = np.arccos(np.clip(cos_angle, -1, 1))
                cot = 1 / np.tan(angle)
                
                # 添加非对角元素
                key = (v1, v2)
                if key not in edge_map:
                    edge_map[key] = 0
                edge_map[key] += cot / 2
        
        # 构建矩阵
        for (i, j), w in edge_map.items():
            I.append(i)
            J.append(j)
            V.append(-w)
            
            I.append(j)
            J.append(i)
            V.append(-w)
            
            diag[i] += w
            diag[j] += w
        
        # 添加对角元素
        for i in range(n_vertices):
            I.append(i)
            J.append(i)
            V.append(diag[i])
        
        # 创建稀疏矩阵
        L = coo_matrix((V, (I, J)), shape=(n_vertices, n_vertices))
        return L.tocsr()
    
    def compute_discrete_curvature(self):
        """计算离散高斯曲率"""
        n_vertices = len(self.vertices)
        curvature = np.zeros(n_vertices)
        
        # 计算角度和
        angle_sums = np.zeros(n_vertices)
        for tri in self.triangles:
            v1, v2, v3 = self.vertices[tri]
            a = np.linalg.norm(v2 - v1)
            b = np.linalg.norm(v3 - v2)
            c = np.linalg.norm(v1 - v3)
            
            # 计算三角形内角
            angles = np.zeros(3)
            angles[0] = np.arccos(np.clip((b**2 + c**2 - a**2) / (2 * b * c), -1, 1))
            angles[1] = np.arccos(np.clip((a**2 + c**2 - b**2) / (2 * a * c), -1, 1))
            angles[2] = np.arccos(np.clip((a**2 + b**2 - c**2) / (2 * a * b), -1, 1))
            
            # 累加到顶点
            for i, idx in enumerate(tri):
                angle_sums[idx] += angles[i]
        
        # 计算曲率：2π - 角度和
        curvature = 2 * np.pi - angle_sums
        
        # 计算Voronoi面积
        areas = self.compute_voronoi_areas()
        
        # 避免除以零
        areas[areas == 0] = 1e-10
        
        # 曲率密度 = 曲率 / 面积
        curvature_density = curvature / areas
        
        return curvature_density, curvature, areas
    
    def ricci_flow_step(self):
        """执行一步李奇流演化"""
        if self.paused:
            return
            
        # 计算曲率
        curvature_density, curvature, areas = self.compute_discrete_curvature()
        
        # 计算平均曲率
        total_area = np.sum(areas)
        mean_curvature = np.sum(curvature) / total_area if total_area > 0 else 0
        
        # 计算余切权重拉普拉斯矩阵
        L = self.compute_cotangent_weights()
        
        # 构建演化方程
        n_vertices = len(self.vertices)
        new_vertices = self.vertices.copy()
        
        # 曲率演化项
        K_term = curvature_density - mean_curvature
        
        # 对每个维度求解演化方程
        for dim in range(3):
            # 构建右端项
            rhs = K_term * self.vertices[:, dim] * self.dt
            
            # 隐式求解
            A = L - self.dt * diags(K_term, 0, shape=(n_vertices, n_vertices))
            delta = linalg.spsolve(A.tocsc(), rhs)
            new_vertices[:, dim] -= delta
        
        # 更新顶点
        self.vertices = new_vertices
        
        # 记录历史数据
        self.curvature_history.append(curvature_density.copy())
        self.area_history.append(total_area)
        self.step_count += 1
        
        # 自适应时间步长
        max_curvature_change = np.max(np.abs(curvature_density - mean_curvature))
        new_dt = 0.1 / (max_curvature_change + 1e-5)
        self.dt = min(new_dt, 0.1)
        
    def reset_simulation(self):
        """重置模拟"""
        if self.initial_vertices is not None:
            self.vertices = self.initial_vertices.copy()
        self.curvature_history = []
        self.area_history = []
        self.step_count = 0
        self.paused = True


class Mpl3DCanvas(FigureCanvas):
    """Matplotlib 3D 可视化画布"""
    def __init__(self, parent=None, width=8, height=6, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        super(Mpl3DCanvas, self).__init__(self.fig)
        self.setParent(parent)
        
        self.ax = self.fig.add_subplot(111, projection='3d')
        self.ax.set_xlabel('X')
        self.ax.set_ylabel('Y')
        self.ax.set_zlabel('Z')
        self.ax.grid(True)
        self.cbar = None
        
    def plot_surface(self, vertices, triangles, curvature=None, title="", elevation=30, azimuth=45):
        """绘制曲面"""
        if self.cbar:
            try:
                self.cbar.remove()
            except:
                pass  # 忽略移除错误
            finally:
                self.cbar = None
        
        # 现在清除坐标轴
        self.ax.clear()
        
        # 移除旧的颜色条
        if self.cbar:
            self.cbar.remove()
            self.cbar = None
        
        X = vertices[:, 0]
        Y = vertices[:, 1]
        Z = vertices[:, 2]
        
        # 创建三角剖分对象
        tri = Triangulation(X, Y, triangles=triangles)
        
        # 绘制曲面 - 统一使用相同的参数
        surf = self.ax.plot_trisurf(tri, Z, 
                                    edgecolor='k', 
                                    alpha=0.9,
                                    linewidth=0.2)
        
        # 根据曲率数据设置颜色
        if curvature is not None and len(curvature) > 0:
            # 使用set_array设置颜色映射
            surf.set_array(curvature)
            surf.set_cmap('coolwarm')
            surf.set_clim(vmin=-5, vmax=5)
            
            # 添加颜色条
            self.cbar = self.fig.colorbar(surf, ax=self.ax, shrink=0.5, label='高斯曲率密度')
        else:
            # 没有曲率数据时使用默认颜色映射
            surf.set_cmap('viridis')
        
        # 设置标题和视图
        self.ax.set_title(title, fontsize=12)
        self.ax.view_init(elev=elevation, azim=azimuth)
        self.draw()


class Mpl2DCanvas(FigureCanvas):
    """Matplotlib 2D 可视化画布"""
    def __init__(self, parent=None, width=8, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        super(Mpl2DCanvas, self).__init__(self.fig)
        self.setParent(parent)
        
        self.ax = self.fig.add_subplot(111)
        self.ax.set_xlabel('演化步数')
        self.ax.set_ylabel('曲率密度')
        self.ax.grid(True)
        
    def plot_curvature_evolution(self, curvature_history):
        """绘制曲率演化过程"""
        self.ax.clear()
        
        if not curvature_history:
            self.ax.text(0.5, 0.5, '没有演化历史数据', 
                         horizontalalignment='center', verticalalignment='center',
                         transform=self.ax.transAxes)
            self.draw()
            return
        
        # 计算统计量
        mean_curvatures = [np.mean(np.abs(k)) for k in curvature_history]
        max_curvatures = [np.max(k) for k in curvature_history]
        min_curvatures = [np.min(k) for k in curvature_history]
        
        # 绘制曲率演化
        steps = range(len(curvature_history))
        self.ax.plot(steps, mean_curvatures, 'b-', label='平均曲率密度')
        self.ax.plot(steps, max_curvatures, 'r--', label='最大曲率密度')
        self.ax.plot(steps, min_curvatures, 'g--', label='最小曲率密度')
        
        self.ax.fill_between(steps, min_curvatures, max_curvatures, color='gray', alpha=0.2)
        
        # 设置标签和标题
        self.ax.set_title('曲率密度演化过程')
        self.ax.legend()
        self.draw()


class RicciFlowApp(QMainWindow):
    """李奇流模拟主应用程序"""
    def __init__(self):
        super().__init__()
        
        # 初始化模拟器
        self.simulator = RicciFlowSimulator()
        
        # 设置窗口属性
        self.setWindowTitle("李奇流模拟与可视化系统")
        self.setGeometry(100, 100, 1200, 800)
        
        # 创建主部件
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # 创建布局
        main_layout = QHBoxLayout(self.central_widget)
        
        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        
        # 左侧控制面板
        control_panel = QWidget()
        control_layout = QVBoxLayout(control_panel)
        
        # 控制面板组
        self.create_surface_controls(control_layout)
        self.create_simulation_controls(control_layout)
        self.create_visualization_controls(control_layout)
        self.create_export_controls(control_layout)
        
        # 右侧可视化区域
        visualization_widget = QTabWidget()
        
        # 3D可视化
        self.canvas_3d = Mpl3DCanvas(self, width=6, height=5, dpi=100)
        
        # 2D可视化
        self.canvas_2d = Mpl2DCanvas(self, width=6, height=4, dpi=100)
        
        # 添加标签页
        visualization_widget.addTab(self.canvas_3d, "3D 可视化")
        visualization_widget.addTab(self.canvas_2d, "曲率分析")
        
        # 添加部件到分割器
        splitter.addWidget(control_panel)
        splitter.addWidget(visualization_widget)
        splitter.setSizes([300, 900])
        
        # 添加到主布局
        main_layout.addWidget(splitter)
        
        # 初始化模拟
        self.simulator.generate_initial_surface()
        self.update_visualization()
        
        # 创建定时器用于连续模拟
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.step_simulation)
        self.timer.setInterval(100)  # 100ms更新一次
        
    def create_surface_controls(self, layout):
        """创建曲面控制组"""
        group = QGroupBox("曲面设置")
        group_layout = QVBoxLayout(group)
        
        # 曲面类型选择
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("曲面类型:"))
        self.surface_combo = QComboBox()
        self.surface_combo.addItems(["高斯曲面", "球面", "环面", "鞍形曲面", "自定义曲面"])
        self.surface_combo.currentIndexChanged.connect(self.change_surface_type)
        type_layout.addWidget(self.surface_combo)
        group_layout.addLayout(type_layout)
        
        # 分辨率设置
        res_layout = QHBoxLayout()
        res_layout.addWidget(QLabel("网格分辨率:"))
        self.resolution_spin = QSpinBox()
        self.resolution_spin.setRange(10, 100)
        self.resolution_spin.setValue(30)
        self.resolution_spin.valueChanged.connect(self.change_resolution)
        res_layout.addWidget(self.resolution_spin)
        group_layout.addLayout(res_layout)
        
        # 生成曲面按钮
        self.generate_btn = QPushButton("生成曲面")
        self.generate_btn.clicked.connect(self.generate_surface)
        group_layout.addWidget(self.generate_btn)
        
        layout.addWidget(group)
    
    def create_simulation_controls(self, layout):
        """创建模拟控制组"""
        group = QGroupBox("模拟控制")
        group_layout = QVBoxLayout(group)
        
        # 步长控制
        dt_layout = QHBoxLayout()
        dt_layout.addWidget(QLabel("时间步长:"))
        self.dt_spin = QDoubleSpinBox()
        self.dt_spin.setRange(0.001, 0.1)
        self.dt_spin.setSingleStep(0.005)
        self.dt_spin.setValue(0.05)
        self.dt_spin.valueChanged.connect(self.change_dt)
        dt_layout.addWidget(self.dt_spin)
        group_layout.addLayout(dt_layout)
        
        # 控制按钮
        btn_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("开始")
        self.start_btn.clicked.connect(self.start_simulation)
        btn_layout.addWidget(self.start_btn)
        
        self.pause_btn = QPushButton("暂停")
        self.pause_btn.clicked.connect(self.pause_simulation)
        btn_layout.addWidget(self.pause_btn)
        
        self.step_btn = QPushButton("单步执行")
        self.step_btn.clicked.connect(self.single_step)
        btn_layout.addWidget(self.step_btn)
        
        self.reset_btn = QPushButton("重置")
        self.reset_btn.clicked.connect(self.reset_simulation)
        btn_layout.addWidget(self.reset_btn)
        
        group_layout.addLayout(btn_layout)
        
        # 状态显示
        status_layout = QHBoxLayout()
        status_layout.addWidget(QLabel("当前步数:"))
        self.step_label = QLabel("0")
        status_layout.addWidget(self.step_label)
        
        status_layout.addWidget(QLabel("当前曲率:"))
        self.curvature_label = QLabel("0.000")
        status_layout.addWidget(self.curvature_label)
        
        group_layout.addLayout(status_layout)
        
        layout.addWidget(group)
    
    def create_visualization_controls(self, layout):
        """创建可视化控制组"""
        group = QGroupBox("可视化设置")
        group_layout = QVBoxLayout(group)
        
        # 视角控制
        view_layout = QHBoxLayout()
        view_layout.addWidget(QLabel("视角高度:"))
        self.elevation_slider = QSlider(Qt.Horizontal)
        self.elevation_slider.setRange(0, 90)
        self.elevation_slider.setValue(30)
        self.elevation_slider.valueChanged.connect(self.update_visualization)
        view_layout.addWidget(self.elevation_slider)
        
        view_layout.addWidget(QLabel("视角方位:"))
        self.azimuth_slider = QSlider(Qt.Horizontal)
        self.azimuth_slider.setRange(0, 360)
        self.azimuth_slider.setValue(45)
        self.azimuth_slider.valueChanged.connect(self.update_visualization)
        view_layout.addWidget(self.azimuth_slider)
        
        group_layout.addLayout(view_layout)
        
        # 曲率显示
        self.curvature_check = QCheckBox("显示曲率")
        self.curvature_check.setChecked(True)
        self.curvature_check.stateChanged.connect(self.toggle_curvature)
        group_layout.addWidget(self.curvature_check)
        
        layout.addWidget(group)
    
    def create_export_controls(self, layout):
        """创建导出控制组"""
        group = QGroupBox("数据导出")
        group_layout = QVBoxLayout(group)
        
        # 导出按钮
        btn_layout = QHBoxLayout()
        
        self.export_mesh_btn = QPushButton("导出网格")
        self.export_mesh_btn.clicked.connect(self.export_mesh)
        btn_layout.addWidget(self.export_mesh_btn)
        
        self.export_curvature_btn = QPushButton("导出曲率数据")
        self.export_curvature_btn.clicked.connect(self.export_curvature)
        btn_layout.addWidget(self.export_curvature_btn)
        
        group_layout.addLayout(btn_layout)
        
        layout.addWidget(group)
        layout.addStretch()
    
    def change_surface_type(self, index):
        """改变曲面类型"""
        types = ["gaussian", "sphere", "torus", "saddle", "custom"]
        self.simulator.surface_type = types[index]
    
    def change_resolution(self, value):
        """改变分辨率"""
        self.simulator.resolution = value
    
    def change_dt(self, value):
        """改变时间步长"""
        self.simulator.dt = value
    
    def generate_surface(self):
        """生成新曲面"""
        self.simulator.generate_initial_surface()
        self.update_visualization()
    
    def start_simulation(self):
        """开始模拟"""
        self.simulator.paused = False
        self.timer.start()
    
    def pause_simulation(self):
        """暂停模拟"""
        self.simulator.paused = True
        self.timer.stop()
    
    def single_step(self):
        """单步执行模拟"""
        self.simulator.ricci_flow_step()
        self.update_visualization()
    
    def reset_simulation(self):
        """重置模拟"""
        self.simulator.reset_simulation()
        self.update_visualization()
    
    def toggle_curvature(self, state):
        """切换曲率显示"""
        self.simulator.curvature_visible = (state == Qt.Checked)
        self.update_visualization()
    
    def step_simulation(self):
        """定时器触发的模拟步骤"""
        self.simulator.ricci_flow_step()
        self.update_visualization()
    
    def update_visualization(self):
        """更新可视化"""
        # 更新3D可视化
        curvature = None
        if self.simulator.curvature_visible and self.simulator.curvature_history:
            curvature = self.simulator.curvature_history[-1]
        
        title = f"曲面类型: {self.simulator.surface_type.capitalize()} - 演化步数: {self.simulator.step_count}"
        self.canvas_3d.plot_surface(
            self.simulator.vertices,
            self.simulator.triangles,
            curvature=curvature,
            title=title,
            elevation=self.elevation_slider.value(),
            azimuth=self.azimuth_slider.value()
        )
        
        # 更新2D可视化
        self.canvas_2d.plot_curvature_evolution(self.simulator.curvature_history)
        
        # 更新状态标签
        self.step_label.setText(str(self.simulator.step_count))
        
        if self.simulator.curvature_history:
            curv = np.mean(np.abs(self.simulator.curvature_history[-1]))
            self.curvature_label.setText(f"{curv:.4f}")
    
    def export_mesh(self):
        """导出网格数据"""
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getSaveFileName(
            self, "保存网格文件", "", "OBJ Files (*.obj);;All Files (*)", options=options)
        
        if file_name:
            # 写入OBJ文件
            with open(file_name, 'w') as f:
                # 写入顶点
                for v in self.simulator.vertices:
                    f.write(f"v {v[0]} {v[1]} {v[2]}\n")
                
                # 写入面
                for tri in self.simulator.triangles:
                    f.write(f"f {tri[0]+1} {tri[1]+1} {tri[2]+1}\n")
    
    def export_curvature(self):
        """导出曲率数据"""
        if not self.simulator.curvature_history:
            return
            
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getSaveFileName(
            self, "保存曲率数据", "", "CSV Files (*.csv);;All Files (*)", options=options)
        
        if file_name:
            with open(file_name, 'w') as f:
                # 写入标题
                f.write("Step,Mean_Curvature,Max_Curvature,Min_Curvature\n")
                
                # 写入数据
                for i, curv in enumerate(self.simulator.curvature_history):
                    mean_curv = np.mean(np.abs(curv))
                    max_curv = np.max(curv)
                    min_curv = np.min(curv)
                    f.write(f"{i},{mean_curv},{max_curv},{min_curv}\n")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = RicciFlowApp()
    window.show()
    sys.exit(app.exec_())