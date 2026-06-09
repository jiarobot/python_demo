import sys
import numpy as np
from PyQt6 import QtWidgets, QtCore, QtGui
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap, QPainter, QColor, QPen, QAction
import cv2
import tifffile as tiff
import imageio
import skimage
from skimage import exposure, filters, restoration, segmentation, measure, feature
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d import Axes3D
import torch
import torchvision.transforms as transforms
from PIL import Image
import json
import pandas as pd
from scipy import ndimage
from sklearn.cluster import DBSCAN
import napari  # 可选：用于高级3D可视化
import pyqtgraph as pg  # 用于高性能可视化
import qimage2ndarray  # 高效图像转换
from datetime import datetime
import h5py
import tqdm

# 模拟AI模型（实际应用中替换为真实模型）
class CellSegmentationModel:
    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        # 这里应该加载预训练模型
        # self.model = load_pretrained_model()
        print(f"Cell segmentation model loaded on {self.device}")
    
    def predict(self, image):
        # 模拟推理过程
        # 实际应用中这里应该使用真实的模型推理
        if len(image.shape) == 3:
            image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # 使用传统图像处理方法模拟AI输出
        blurred = cv2.GaussianBlur(image, (5, 5), 0)
        _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # 模拟细胞检测
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # 创建分割掩码
        mask = np.zeros_like(image)
        for contour in contours:
            if cv2.contourArea(contour) > 100:  # 过滤小区域
                cv2.drawContours(mask, [contour], -1, 255, -1)
        
        return mask

class ParticleTracker:
    def __init__(self):
        self.tracks = {}
        self.next_id = 0
    
    def update(self, detections):
        # 简单的多目标跟踪实现
        # 实际应用中可以使用更复杂的算法如Kalman滤波
        updated_tracks = {}
        
        for detection in detections:
            # 查找最近的现有轨迹
            min_dist = float('inf')
            best_match = None
            
            for track_id, track in self.tracks.items():
                last_pos = track[-1]
                dist = np.linalg.norm(np.array(last_pos) - np.array(detection))
                
                if dist < min_dist and dist < 50:  # 距离阈值
                    min_dist = dist
                    best_match = track_id
            
            if best_match is not None:
                updated_tracks[best_match] = self.tracks[best_match] + [detection]
            else:
                updated_tracks[self.next_id] = [detection]
                self.next_id += 1
        
        self.tracks = updated_tracks
        return self.tracks

class ProcessingThread(QThread):
    """用于后台处理的线程"""
    progress = pyqtSignal(int)
    finished = pyqtSignal(object)
    
    def __init__(self, function, *args, **kwargs):
        super().__init__()
        self.function = function
        self.args = args
        self.kwargs = kwargs
    
    def run(self):
        result = self.function(*self.args, **self.kwargs)
        self.finished.emit(result)

class AdvancedMicroscopeViewer(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("高级智能显微图像分析系统")
        self.setGeometry(100, 100, 1920, 1080)
        
        # 初始化变量
        self.image_data = None
        self.video_capture = None
        self.current_frame = 0
        self.playing = False
        self.processed_data = None
        self.rois = []
        self.tracked_objects = []
        self.metadata = {}
        self.cell_seg_model = CellSegmentationModel()
        self.particle_tracker = ParticleTracker()
        self.current_tool = "select"  # 默认工具
        
        # 设置样式
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2b2b2b;
            }
            QGroupBox {
                color: #ffffff;
                font-weight: bold;
                border: 1px solid #555555;
                border-radius: 5px;
                margin-top: 1ex;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 5px;
            }
            QPushButton {
                background-color: #3b3b3b;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 3px;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #4b4b4b;
            }
            QPushButton:pressed {
                background-color: #5b5b5b;
            }
            QSlider::groove:horizontal {
                border: 1px solid #555555;
                height: 8px;
                background: #3b3b3b;
                margin: 2px 0;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #888888;
                border: 1px solid #555555;
                width: 18px;
                margin: -2px 0;
                border-radius: 9px;
            }
            QTableWidget {
                background-color: #2b2b2b;
                color: #ffffff;
                gridline-color: #555555;
                border: 1px solid #555555;
            }
            QHeaderView::section {
                background-color: #3b3b3b;
                color: #ffffff;
                padding: 4px;
                border: 1px solid #555555;
            }
        """)
        
        self.setup_ui()
        self.setup_menu()
        self.setup_toolbar()
        
    def setup_ui(self):
        # 创建中央部件和主布局
        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QtWidgets.QHBoxLayout(central_widget)
        
        # 左侧控制面板
        control_panel = QtWidgets.QWidget()
        control_panel.setMaximumWidth(350)
        control_layout = QtWidgets.QVBoxLayout(control_panel)
        
        # 文件操作组
        file_group = QtWidgets.QGroupBox("文件操作")
        file_layout = QtWidgets.QVBoxLayout(file_group)
        self.open_image_btn = QtWidgets.QPushButton("打开图像")
        self.open_video_btn = QtWidgets.QPushButton("打开视频")
        self.open_sequence_btn = QtWidgets.QPushButton("打开序列")
        self.open_folder_btn = QtWidgets.QPushButton("打开文件夹")
        self.export_btn = QtWidgets.QPushButton("导出数据")
        self.save_project_btn = QtWidgets.QPushButton("保存项目")
        
        for btn in [self.open_image_btn, self.open_video_btn, self.open_sequence_btn, 
                   self.open_folder_btn, self.export_btn, self.save_project_btn]:
            file_layout.addWidget(btn)
        
        # 图像处理组
        process_group = QtWidgets.QGroupBox("图像处理")
        process_layout = QtWidgets.QGridLayout(process_group)
        
        self.enhance_btn = QtWidgets.QPushButton("增强对比度")
        self.denoise_btn = QtWidgets.QPushButton("降噪")
        self.segment_btn = QtWidgets.QPushButton("分割图像")
        self.deconvolution_btn = QtWidgets.QPushButton("去卷积")
        self.align_btn = QtWidgets.QPushButton("图像对齐")
        self.stitch_btn = QtWidgets.QPushButton("图像拼接")
        
        process_layout.addWidget(self.enhance_btn, 0, 0)
        process_layout.addWidget(self.denoise_btn, 0, 1)
        process_layout.addWidget(self.segment_btn, 1, 0)
        process_layout.addWidget(self.deconvolution_btn, 1, 1)
        process_layout.addWidget(self.align_btn, 2, 0)
        process_layout.addWidget(self.stitch_btn, 2, 1)
        
        # AI分析组
        ai_group = QtWidgets.QGroupBox("智能分析")
        ai_layout = QtWidgets.QGridLayout(ai_group)
        
        self.detect_cells_btn = QtWidgets.QPushButton("检测细胞")
        self.track_particles_btn = QtWidgets.QPushButton("追踪颗粒")
        self.measure_btn = QtWidgets.QPushButton("测量参数")
        self.classify_btn = QtWidgets.QPushButton("分类细胞")
        self.count_btn = QtWidgets.QPushButton("计数对象")
        self.analyze_motion_btn = QtWidgets.QPushButton("分析运动")
        
        ai_layout.addWidget(self.detect_cells_btn, 0, 0)
        ai_layout.addWidget(self.track_particles_btn, 0, 1)
        ai_layout.addWidget(self.measure_btn, 1, 0)
        ai_layout.addWidget(self.classify_btn, 1, 1)
        ai_layout.addWidget(self.count_btn, 2, 0)
        ai_layout.addWidget(self.analyze_motion_btn, 2, 1)
        
        # 可视化组
        viz_group = QtWidgets.QGroupBox("可视化")
        viz_layout = QtWidgets.QGridLayout(viz_group)
        
        self.overlay_check = QtWidgets.QCheckBox("显示分析叠加")
        self.heatmap_check = QtWidgets.QCheckBox("热图显示")
        self.td_view_btn = QtWidgets.QPushButton("3D视图")
        self.channel_mixer_btn = QtWidgets.QPushButton("通道混合器")
        self.lut_btn = QtWidgets.QPushButton("LUT设置")
        self.volume_render_btn = QtWidgets.QPushButton("体积渲染")
        
        viz_layout.addWidget(self.overlay_check, 0, 0)
        viz_layout.addWidget(self.heatmap_check, 0, 1)
        viz_layout.addWidget(self.td_view_btn, 1, 0)
        viz_layout.addWidget(self.channel_mixer_btn, 1, 1)
        viz_layout.addWidget(self.lut_btn, 2, 0)
        viz_layout.addWidget(self.volume_render_btn, 2, 1)
        
        # 添加到控制面板
        control_layout.addWidget(file_group)
        control_layout.addWidget(process_group)
        control_layout.addWidget(ai_group)
        control_layout.addWidget(viz_group)
        control_layout.addStretch()
        
        # 右侧图像显示和分析区域
        display_panel = QtWidgets.QWidget()
        display_layout = QtWidgets.QVBoxLayout(display_panel)
        
        # 图像显示区域
        self.graphics_view = pg.GraphicsView()
        self.graphics_view.setBackground('#1f1f1f')
        self.image_item = pg.ImageItem()
        
        # 修复部分：正确创建 ViewBox
        self.view_box = pg.ViewBox()
        self.graphics_view.setCentralItem(self.view_box)  # 关键修复
        
        self.view_box.addItem(self.image_item)
        self.view_box.setAspectLocked(True)
        
        # 视频控制
        video_control = QtWidgets.QWidget()
        video_layout = QtWidgets.QHBoxLayout(video_control)
        self.play_btn = QtWidgets.QPushButton("播放")
        self.pause_btn = QtWidgets.QPushButton("暂停")
        self.stop_btn = QtWidgets.QPushButton("停止")
        self.frame_slider = QtWidgets.QSlider(Qt.Orientation.Horizontal)
        self.frame_label = QtWidgets.QLabel("帧: 0/0")
        
        video_layout.addWidget(self.play_btn)
        video_layout.addWidget(self.pause_btn)
        video_layout.addWidget(self.stop_btn)
        video_layout.addWidget(self.frame_slider)
        video_layout.addWidget(self.frame_label)
        
        # 分析结果显示
        self.result_table = QtWidgets.QTableWidget()
        self.result_table.setColumnCount(6)
        self.result_table.setHorizontalHeaderLabels(["ID", "位置", "大小", "强度", "形状", "分类"])
        
        # 图表显示
        self.figure = Figure(facecolor='#2b2b2b')
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setStyleSheet("background-color: #2b2b2b;")
        
        # 添加到显示面板
        display_layout.addWidget(self.graphics_view, 4)
        display_layout.addWidget(video_control, 1)
        
        # 创建标签页显示结果和图表
        results_tab = QtWidgets.QTabWidget()
        results_tab.addTab(self.result_table, "分析结果")
        results_tab.addTab(self.canvas, "图表")
        display_layout.addWidget(results_tab, 2)
        
        # 添加到主布局
        main_layout.addWidget(control_panel, 1)
        main_layout.addWidget(display_panel, 3)
        
        # 连接信号和槽
        self.connect_signals()
        
        # 初始化状态栏
        self.statusBar().showMessage("就绪")
        
    def setup_menu(self):
        menubar = self.menuBar()
        menubar.setStyleSheet("""
            QMenuBar {
                background-color: #3b3b3b;
                color: #ffffff;
            }
            QMenuBar::item:selected {
                background-color: #5b5b5b;
            }
            QMenu {
                background-color: #3b3b3b;
                color: #ffffff;
                border: 1px solid #555555;
            }
            QMenu::item:selected {
                background-color: #5b5b5b;
            }
        """)
        
        # 文件菜单
        file_menu = menubar.addMenu('文件')
        
        open_image_action = QAction('打开图像', self)
        open_image_action.triggered.connect(self.open_image)
        file_menu.addAction(open_image_action)
        
        open_video_action = QAction('打开视频', self)
        open_video_action.triggered.connect(self.open_video)
        file_menu.addAction(open_video_action)
        
        open_sequence_action = QAction('打开序列', self)
        open_sequence_action.triggered.connect(self.open_sequence)
        file_menu.addAction(open_sequence_action)
        
        file_menu.addSeparator()
        
        export_action = QAction('导出数据', self)
        export_action.triggered.connect(self.export_results)
        file_menu.addAction(export_action)
        
        # 编辑菜单
        edit_menu = menubar.addMenu('编辑')
        
        preferences_action = QAction('首选项', self)
        preferences_action.triggered.connect(self.show_preferences)
        edit_menu.addAction(preferences_action)
        
        # 分析菜单
        analysis_menu = menubar.addMenu('分析')
        
        cell_detection_action = QAction('细胞检测', self)
        cell_detection_action.triggered.connect(self.detect_cells)
        analysis_menu.addAction(cell_detection_action)
        
        particle_tracking_action = QAction('颗粒追踪', self)
        particle_tracking_action.triggered.connect(self.track_particles)
        analysis_menu.addAction(particle_tracking_action)
        
        # 视图菜单
        view_menu = menubar.addMenu('视图')
        
        overlay_action = QAction('叠加层', self)
        overlay_action.setCheckable(True)
        overlay_action.toggled.connect(self.toggle_overlay)
        view_menu.addAction(overlay_action)
        
        fullscreen_action = QAction('全屏', self)
        fullscreen_action.setCheckable(True)
        fullscreen_action.toggled.connect(self.toggle_fullscreen)
        view_menu.addAction(fullscreen_action)
        
    def setup_toolbar(self):
        toolbar = self.addToolBar("工具")
        toolbar.setIconSize(QtCore.QSize(24, 24))
        toolbar.setMovable(False)
        
        # 选择工具
        select_action = QAction(QtGui.QIcon("icons/select.png"), "选择", self)
        select_action.triggered.connect(lambda: self.set_tool("select"))
        toolbar.addAction(select_action)
        
        # ROI工具
        roi_action = QAction(QtGui.QIcon("icons/roi.png"), "ROI", self)
        roi_action.triggered.connect(lambda: self.set_tool("roi"))
        toolbar.addAction(roi_action)
        
        # 测量工具
        measure_action = QAction(QtGui.QIcon("icons/measure.png"), "测量", self)
        measure_action.triggered.connect(lambda: self.set_tool("measure"))
        toolbar.addAction(measure_action)
        
        # 缩放工具
        zoom_action = QAction(QtGui.QIcon("icons/zoom.png"), "缩放", self)
        zoom_action.triggered.connect(lambda: self.set_tool("zoom"))
        toolbar.addAction(zoom_action)
        
        # 平移工具
        pan_action = QAction(QtGui.QIcon("icons/pan.png"), "平移", self)
        pan_action.triggered.connect(lambda: self.set_tool("pan"))
        toolbar.addAction(pan_action)
        
    def connect_signals(self):
        # 文件操作
        self.open_image_btn.clicked.connect(self.open_image)
        self.open_video_btn.clicked.connect(self.open_video)
        self.open_sequence_btn.clicked.connect(self.open_sequence)
        self.open_folder_btn.clicked.connect(self.open_folder)
        self.export_btn.clicked.connect(self.export_results)
        self.save_project_btn.clicked.connect(self.save_project)
        
        # 图像处理
        self.enhance_btn.clicked.connect(self.enhance_image)
        self.denoise_btn.clicked.connect(self.denoise_image)
        self.segment_btn.clicked.connect(self.segment_image)
        self.deconvolution_btn.clicked.connect(self.deconvolve_image)
        self.align_btn.clicked.connect(self.align_images)
        self.stitch_btn.clicked.connect(self.stitch_images)
        
        # AI分析
        self.detect_cells_btn.clicked.connect(self.detect_cells)
        self.track_particles_btn.clicked.connect(self.track_particles)
        self.measure_btn.clicked.connect(self.measure_properties)
        self.classify_btn.clicked.connect(self.classify_objects)
        self.count_btn.clicked.connect(self.count_objects)
        self.analyze_motion_btn.clicked.connect(self.analyze_motion)
        
        # 可视化
        self.overlay_check.stateChanged.connect(self.toggle_overlay)
        self.heatmap_check.stateChanged.connect(self.toggle_heatmap)
        self.td_view_btn.clicked.connect(self.show_3d_view)
        self.channel_mixer_btn.clicked.connect(self.show_channel_mixer)
        self.lut_btn.clicked.connect(self.show_lut_settings)
        self.volume_render_btn.clicked.connect(self.volume_render)
        
        # 视频控制
        self.play_btn.clicked.connect(self.play_video)
        self.pause_btn.clicked.connect(self.pause_video)
        self.stop_btn.clicked.connect(self.stop_video)
        self.frame_slider.sliderMoved.connect(self.set_video_position)
        
    def set_tool(self, tool):
        self.current_tool = tool
        self.statusBar().showMessage(f"当前工具: {tool}")
        
    def open_image(self):
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "打开图像文件", "", 
            "图像文件 (*.tif *.tiff *.png *.jpg *.jpeg *.bmp *.lsm *.nd2 *.czi);;所有文件 (*)"
        )
        
        if file_path:
            try:
                self.statusBar().showMessage("正在加载图像...")
                
                # 使用线程加载大图像
                self.thread = ProcessingThread(self.load_image, file_path)
                self.thread.finished.connect(self.on_image_loaded)
                self.thread.start()
                
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "错误", f"无法打开图像: {str(e)}")
    
    def load_image(self, file_path):
        # 支持多种图像格式，包括多帧TIFF
        if file_path.endswith(('.tif', '.tiff', '.lsm')):
            image_data = tiff.imread(file_path)
        elif file_path.endswith(('.nd2')):
            # 使用ND2 reader (需要安装nd2reader库)
            try:
                import nd2reader
                image_data = nd2reader.Nd2(file_path).to_numpy()
            except ImportError:
                QtWidgets.QMessageBox.warning(self, "警告", "需要安装nd2reader库来读取ND2文件")
                return None
        elif file_path.endswith(('.czi')):
            # 使用CZI reader (需要安装czifile库)
            try:
                import czifile
                image_data = czifile.imread(file_path)
            except ImportError:
                QtWidgets.QMessageBox.warning(self, "警告", "需要安装czifile库来读取CZI文件")
                return None
        else:
            image_data = cv2.imread(file_path, cv2.IMREAD_ANYCOLOR | cv2.IMREAD_ANYDEPTH)
        
        return image_data
    
    def on_image_loaded(self, image_data):
        if image_data is None:
            self.statusBar().showMessage("图像加载失败")
            return
            
        self.image_data = image_data
        
        # 处理多维数据
        if len(self.image_data.shape) > 2:
            # 如果是多帧图像，使用第一帧
            if len(self.image_data.shape) == 3 and self.image_data.shape[0] > 1:
                self.current_frame = 0
                self.display_image(self.image_data[self.current_frame])
            else:
                self.display_image(self.image_data)
        else:
            self.display_image(self.image_data)
            
        self.statusBar().showMessage(f"图像已加载: {self.image_data.shape}")
    
    def open_video(self):
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "打开视频文件", "", 
            "视频文件 (*.avi *.mp4 *.mov *.tif *.tiff *.nd2);;所有文件 (*)"
        )
        
        if file_path:
            try:
                # 支持常规视频格式和TIFF序列
                if file_path.endswith(('.tif', '.tiff')):
                    self.video_data = tiff.imread(file_path)
                    self.video_capture = None
                    self.total_frames = self.video_data.shape[0]
                elif file_path.endswith(('.nd2')):
                    # 使用ND2 reader
                    try:
                        import nd2reader
                        nd2_file = nd2reader.Nd2(file_path)
                        self.video_data = nd2_file.to_numpy()
                        self.video_capture = None
                        self.total_frames = self.video_data.shape[0]
                    except ImportError:
                        QtWidgets.QMessageBox.warning(self, "警告", "需要安装nd2reader库来读取ND2文件")
                        return
                else:
                    self.video_capture = cv2.VideoCapture(file_path)
                    self.total_frames = int(self.video_capture.get(cv2.CAP_PROP_FRAME_COUNT))
                    self.video_data = None
                
                self.current_frame = 0
                self.frame_slider.setMaximum(self.total_frames - 1)
                self.frame_label.setText(f"帧: {self.current_frame+1}/{self.total_frames}")
                self.display_video_frame()
                
                self.statusBar().showMessage(f"视频已加载: {self.total_frames}帧")
                
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "错误", f"无法打开视频: {str(e)}")
    
    def open_sequence(self):
        folder_path = QtWidgets.QFileDialog.getExistingDirectory(self, "选择序列文件夹")
        
        if folder_path:
            try:
                # 读取文件夹中的所有图像文件
                import glob
                image_files = glob.glob(f"{folder_path}/*.tif") + glob.glob(f"{folder_path}/*.tiff") + \
                             glob.glob(f"{folder_path}/*.png") + glob.glob(f"{folder_path}/*.jpg") + \
                             glob.glob(f"{folder_path}/*.jpeg")
                
                image_files.sort()  # 确保按顺序加载
                
                if not image_files:
                    QtWidgets.QMessageBox.warning(self, "警告", "文件夹中没有找到图像文件")
                    return
                
                # 加载第一张图像以确定尺寸
                first_image = cv2.imread(image_files[0], cv2.IMREAD_ANYCOLOR | cv2.IMREAD_ANYDEPTH)
                
                # 创建数组存储所有图像
                if len(first_image.shape) == 2:
                    self.image_data = np.zeros((len(image_files), first_image.shape[0], first_image.shape[1]), 
                                              dtype=first_image.dtype)
                else:
                    self.image_data = np.zeros((len(image_files), first_image.shape[0], first_image.shape[1], first_image.shape[2]), 
                                              dtype=first_image.dtype)
                
                # 使用线程加载所有图像
                self.thread = ProcessingThread(self.load_image_sequence, image_files)
                self.thread.progress.connect(self.update_progress)
                self.thread.finished.connect(self.on_sequence_loaded)
                self.thread.start()
                
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "错误", f"无法打开序列: {str(e)}")
    
    def load_image_sequence(self, image_files):
        # 在后台线程中加载图像序列
        for i, file_path in enumerate(image_files):
            image = cv2.imread(file_path, cv2.IMREAD_ANYCOLOR | cv2.IMREAD_ANYDEPTH)
            self.image_data[i] = image
            self.progress.emit(int((i+1) / len(image_files) * 100))
        
        return self.image_data
    
    def update_progress(self, value):
        self.statusBar().showMessage(f"加载进度: {value}%")
    
    def on_sequence_loaded(self, image_data):
        self.image_data = image_data
        self.current_frame = 0
        self.display_image(self.image_data[self.current_frame])
        self.statusBar().showMessage(f"序列已加载: {self.image_data.shape}")
    
    def open_folder(self):
        # 打开整个文件夹进行处理
        folder_path = QtWidgets.QFileDialog.getExistingDirectory(self, "选择文件夹")
        
        if folder_path:
            # 这里可以实现批量处理功能
            self.statusBar().showMessage(f"已选择文件夹: {folder_path}")
    
    def display_image(self, image):
        # 确保图像数据是连续的
        image = np.ascontiguousarray(image)
        
        # 处理图像方向 - 根据用户设置调整旋转
        rotation_mode = getattr(self, 'rotation_mode', 0)  # 默认为0（不旋转）
        
        if rotation_mode == 1:  # 顺时针90度
            image = cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
        elif rotation_mode == 2:  # 逆时针90度
            image = cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
        elif rotation_mode == 3:  # 180度
            image = cv2.rotate(image, cv2.ROTATE_180)
        
        # 处理颜色通道
        if len(image.shape) == 3:
            # 如果是3通道图像，检查是BGR还是RGB
            if image.shape[2] == 3:
                # OpenCV默认使用BGR，但显示需要RGB
                image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            elif image.shape[2] == 4:
                # 如果是4通道图像（带透明度）
                image = cv2.cvtColor(image, cv2.COLOR_BGRA2RGBA)
        
        # 使用pyqtgraph高效显示图像
        self.image_item.setImage(image, autoLevels=True)
        
        # 如果有ROI，绘制它们
        if self.rois:
            self.draw_rois()

    def display_video_frame(self):
        if self.video_capture is not None:
            self.video_capture.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame)
            ret, frame = self.video_capture.read()
            if ret:
                # 处理视频帧的方向和颜色
                rotation_mode = getattr(self, 'rotation_mode', 0)  # 默认为0（不旋转）
                
                if rotation_mode == 1:  # 顺时针90度
                    frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
                elif rotation_mode == 2:  # 逆时针90度
                    frame = cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
                elif rotation_mode == 3:  # 180度
                    frame = cv2.rotate(frame, cv2.ROTATE_180)
                    
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)  # BGR转RGB
                self.display_image(frame)
        elif self.video_data is not None:
            frame = self.video_data[self.current_frame]
            # 处理视频数据的方向和颜色
            rotation_mode = getattr(self, 'rotation_mode', 0)  # 默认为0（不旋转）
            
            if rotation_mode == 1:  # 顺时针90度
                frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
            elif rotation_mode == 2:  # 逆时针90度
                frame = cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
            elif rotation_mode == 3:  # 180度
                frame = cv2.rotate(frame, cv2.ROTATE_180)
                
            if len(frame.shape) == 3 and frame.shape[2] == 3:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)  # BGR转RGB
            self.display_image(frame)
        
        self.frame_label.setText(f"帧: {self.current_frame+1}/{self.total_frames}")
    
    def set_rotation_mode(self, mode):
        """设置图像旋转模式
        0: 不旋转
        1: 顺时针90度
        2: 逆时针90度
        3: 180度
        """
        self.rotation_mode = mode
        # 刷新当前显示
        if self.image_data is not None:
            if len(self.image_data.shape) == 3 and self.image_data.shape[0] > 1:
                self.display_image(self.image_data[self.current_frame])
            else:
                self.display_image(self.image_data)
        elif self.video_data is not None or self.video_capture is not None:
            self.display_video_frame()

    def play_video(self):
        self.playing = True
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.next_frame)
        self.timer.start(int(1000 / 30))  # 30 FPS
    
    def pause_video(self):
        self.playing = False
        if hasattr(self, 'timer'):
            self.timer.stop()
    
    def stop_video(self):
        self.pause_video()
        self.current_frame = 0
        self.frame_slider.setValue(0)
        self.display_video_frame()
    
    def next_frame(self):
        if self.current_frame < self.total_frames - 1:
            self.current_frame += 1
            self.frame_slider.setValue(self.current_frame)
            self.display_video_frame()
        else:
            self.pause_video()
    
    def set_video_position(self, position):
        self.current_frame = position
        self.display_video_frame()
    
    def enhance_image(self):
        if self.image_data is None:
            return
        
        # 使用自适应直方图均衡化增强对比度
        if len(self.image_data.shape) == 2:
            enhanced = exposure.equalize_adapthist(self.image_data)
        else:
            enhanced = np.zeros_like(self.image_data)
            for i in range(self.image_data.shape[2]):
                enhanced[:, :, i] = exposure.equalize_adapthist(self.image_data[:, :, i])
        
        self.display_image(enhanced)
        self.processed_data = enhanced
        self.statusBar().showMessage("图像增强完成")
    
    def denoise_image(self):
        if self.image_data is None:
            return
        
        # 使用非局部均值去噪
        if len(self.image_data.shape) == 3:
            image = cv2.cvtColor(self.image_data, cv2.COLOR_BGR2GRAY)
        else:
            image = self.image_data
        
        # 将图像转换为0-1范围
        image_normalized = image.astype(np.float32) / np.max(image)
        
        # 使用非局部均值去噪
        denoised = restoration.denoise_nl_means(image_normalized, h=0.1, fast_mode=True)
        
        # 恢复原始范围
        denoised = (denoised * np.max(image)).astype(image.dtype)
        
        self.display_image(denoised)
        self.processed_data = denoised
        self.statusBar().showMessage("图像去噪完成")
    
    def segment_image(self):
        if self.image_data is None:
            return
        
        # 使用多种分割算法
        if len(self.image_data.shape) == 3:
            image = cv2.cvtColor(self.image_data, cv2.COLOR_BGR2GRAY)
        else:
            image = self.image_data
        
        # 使用Otsu阈值
        thresh = filters.threshold_otsu(image)
        binary = image > thresh
        
        # 使用分水岭算法
        distance = ndimage.distance_transform_edt(binary)
        local_maxi = feature.peak_local_max(distance, indices=False, footprint=np.ones((3, 3)), labels=binary)
        markers = measure.label(local_maxi)
        segmented = segmentation.watershed(-distance, markers, mask=binary)
        
        self.display_image(segmented)
        self.processed_data = segmented
        self.statusBar().showMessage("图像分割完成")
    
    def deconvolve_image(self):
        if self.image_data is None:
            return
        
        # 使用Richardson-Lucy去卷积
        if len(self.image_data.shape) == 3:
            image = cv2.cvtColor(self.image_data, cv2.COLOR_BGR2GRAY)
        else:
            image = self.image_data
        
        # 创建PSF（点扩散函数）
        psf = np.ones((5, 5)) / 25
        
        # 应用去卷积
        deconvolved = restoration.richardson_lucy(image, psf, num_iter=30)
        
        self.display_image(deconvolved)
        self.processed_data = deconvolved
        self.statusBar().showMessage("图像去卷积完成")
    
    def align_images(self):
        # 图像对齐功能
        if self.image_data is None:
            return
        
        if len(self.image_data.shape) < 3:
            QtWidgets.QMessageBox.warning(self, "警告", "需要多帧图像进行对齐")
            return
        
        self.statusBar().showMessage("正在对齐图像...")
        
        # 使用ECC算法进行图像对齐
        aligned_images = np.zeros_like(self.image_data)
        aligned_images[0] = self.image_data[0]  # 第一帧作为参考
        
        # 定义运动模型
        warp_mode = cv2.MOTION_TRANSLATION
        
        # 指定迭代次数
        number_of_iterations = 5000
        
        # 指定迭代终止条件
        termination_eps = 1e-10
        criteria = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, number_of_iterations, termination_eps)
        
        for i in range(1, self.image_data.shape[0]):
            # 使用ECC算法找到变换矩阵
            cc, warp_matrix = cv2.findTransformECC(
                cv2.cvtColor(aligned_images[0].astype(np.uint8), cv2.COLOR_BGR2GRAY),
                cv2.cvtColor(self.image_data[i].astype(np.uint8), cv2.COLOR_BGR2GRAY),
                warp_matrix=np.eye(2, 3, dtype=np.float32),
                motionType=warp_mode,
                criteria=criteria
            )
            
            # 应用变换
            aligned_images[i] = cv2.warpAffine(
                self.image_data[i], warp_matrix, 
                (self.image_data.shape[2], self.image_data.shape[1]),
                flags=cv2.INTER_LINEAR + cv2.WARP_INVERSE_MAP
            )
        
        self.image_data = aligned_images
        self.display_image(self.image_data[0])
        self.statusBar().showMessage("图像对齐完成")
    
    def stitch_images(self):
        # 图像拼接功能
        QtWidgets.QMessageBox.information(self, "信息", "图像拼接功能需要多张图像，请使用文件夹导入功能")
    
    def detect_cells(self):
        if self.image_data is None:
            return
        
        self.statusBar().showMessage("正在检测细胞...")
        
        # 使用AI模型进行细胞检测
        current_image = self.image_data
        if len(self.image_data.shape) > 2 and self.image_data.shape[0] > 1:
            current_image = self.image_data[self.current_frame]
        
        # 在后台线程中运行检测
        self.thread = ProcessingThread(self.cell_seg_model.predict, current_image)
        self.thread.finished.connect(self.on_cells_detected)
        self.thread.start()
    
    def on_cells_detected(self, mask):
        # 在原图上绘制检测结果
        if len(self.image_data.shape) == 3 and self.image_data.shape[0] > 1:
            image = self.image_data[self.current_frame]
        else:
            image = self.image_data
        
        if len(image.shape) == 2:
            display_image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        else:
            display_image = image.copy()
        
        # 找到轮廓
        contours, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # 绘制轮廓
        cv2.drawContours(display_image, contours, -1, (0, 255, 0), 2)
        
        # 绘制中心点
        for contour in contours:
            if cv2.contourArea(contour) > 100:
                M = cv2.moments(contour)
                if M["m00"] != 0:
                    cx = int(M["m10"] / M["m00"])
                    cy = int(M["m01"] / M["m00"])
                    cv2.circle(display_image, (cx, cy), 3, (255, 0, 0), -1)
        
        self.display_image(display_image)
        self.update_results_table(contours, image)
        self.statusBar().showMessage(f"检测到 {len(contours)} 个细胞")
    
    def track_particles(self):
        if self.video_data is None and self.video_capture is None:
            QtWidgets.QMessageBox.warning(self, "警告", "需要视频数据进行追踪")
            return
        
        self.statusBar().showMessage("正在追踪颗粒...")
        
        # 使用粒子追踪算法
        if self.video_data is not None:
            video = self.video_data
        else:
            # 从视频捕获对象中提取所有帧
            video = []
            self.video_capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
            for _ in range(self.total_frames):
                ret, frame = self.video_capture.read()
                if ret:
                    video.append(frame)
            video = np.array(video)
        
        # 在后台线程中运行追踪
        self.thread = ProcessingThread(self.perform_tracking, video)
        self.thread.progress.connect(self.update_progress)
        self.thread.finished.connect(self.on_tracking_completed)
        self.thread.start()
    
    def perform_tracking(self, video):
        tracks = {}
        
        for frame_idx in range(video.shape[0]):
            frame = video[frame_idx]
            
            if len(frame.shape) == 3:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            else:
                gray = frame
            
            # 检测颗粒（简单阈值方法）
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # 提取中心点
            detections = []
            for contour in contours:
                if cv2.contourArea(contour) > 50:  # 过滤小区域
                    M = cv2.moments(contour)
                    if M["m00"] != 0:
                        cx = int(M["m10"] / M["m00"])
                        cy = int(M["m01"] / M["m00"])
                        detections.append((cx, cy))
            
            # 更新追踪器
            tracks = self.particle_tracker.update(detections)
            
            self.progress.emit(int((frame_idx+1) / video.shape[0] * 100))
        
        return tracks
    
    def on_tracking_completed(self, tracks):
        self.tracked_objects = tracks
        
        # 显示追踪结果
        if self.video_data is not None:
            frame = self.video_data[0]
        else:
            self.video_capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
            _, frame = self.video_capture.read()
        
        display_frame = frame.copy()
        
        # 绘制追踪轨迹
        for track_id, track in tracks.items():
            if len(track) > 1:
                for i in range(1, len(track)):
                    cv2.line(display_frame, track[i-1], track[i], (0, 255, 0), 2)
                cv2.putText(display_frame, str(track_id), track[-1], 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        self.display_image(display_frame)
        
        # 创建运动分析图表
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        
        for track_id, track in tracks.items():
            if len(track) > 5:  # 只显示有足够点的轨迹
                x = [point[0] for point in track]
                y = [point[1] for point in track]
                ax.plot(x, y, label=f"粒子 {track_id}")
        
        ax.set_xlabel("X 位置")
        ax.set_ylabel("Y 位置")
        ax.set_title("粒子运动轨迹")
        ax.legend()
        self.canvas.draw()
        
        self.statusBar().showMessage(f"追踪到 {len(tracks)} 个粒子")
    
    def measure_properties(self):
        if self.image_data is None:
            return
        
        # 测量图像中对象的属性
        if len(self.image_data.shape) == 3 and self.image_data.shape[0] > 1:
            image = self.image_data[self.current_frame]
        else:
            image = self.image_data
        
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        
        # 阈值处理
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # 查找轮廓
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # 测量属性
        properties = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if area > 100:  # 过滤小区域
                M = cv2.moments(contour)
                if M["m00"] != 0:
                    cx = int(M["m10"] / M["m00"])
                    cy = int(M["m01"] / M["m00"])
                    
                    # 计算形状参数
                    perimeter = cv2.arcLength(contour, True)
                    circularity = 4 * np.pi * area / (perimeter * perimeter) if perimeter > 0 else 0
                    
                    properties.append({
                        'position': (cx, cy),
                        'area': area,
                        'perimeter': perimeter,
                        'circularity': circularity
                    })
        
        # 更新结果表格
        self.result_table.setRowCount(len(properties))
        for i, prop in enumerate(properties):
            self.result_table.setItem(i, 0, QtWidgets.QTableWidgetItem(str(i+1)))
            self.result_table.setItem(i, 1, QtWidgets.QTableWidgetItem(f"{prop['position']}"))
            self.result_table.setItem(i, 2, QtWidgets.QTableWidgetItem(f"{prop['area']:.2f}"))
            self.result_table.setItem(i, 3, QtWidgets.QTableWidgetItem("N/A"))  # 强度
            self.result_table.setItem(i, 4, QtWidgets.QTableWidgetItem(f"{prop['circularity']:.2f}"))
            self.result_table.setItem(i, 5, QtWidgets.QTableWidgetItem("N/A"))  # 分类
        
        self.statusBar().showMessage(f"测量了 {len(properties)} 个对象的属性")
    
    def classify_objects(self):
        # 对象分类功能
        QtWidgets.QMessageBox.information(self, "信息", "对象分类功能需要训练好的模型")
    
    def count_objects(self):
        if self.image_data is None:
            return
        
        # 计数图像中的对象
        if len(self.image_data.shape) == 3 and self.image_data.shape[0] > 1:
            image = self.image_data[self.current_frame]
        else:
            image = self.image_data
        
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        
        # 阈值处理
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # 查找轮廓
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # 过滤小区域
        valid_contours = [cnt for cnt in contours if cv2.contourArea(cnt) > 100]
        
        # 显示结果
        result_image = image.copy()
        if len(result_image.shape) == 2:
            result_image = cv2.cvtColor(result_image, cv2.COLOR_GRAY2BGR)
        
        cv2.drawContours(result_image, valid_contours, -1, (0, 255, 0), 2)
        
        # 添加计数文本
        cv2.putText(result_image, f"计数: {len(valid_contours)}", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        
        self.display_image(result_image)
        self.statusBar().showMessage(f"检测到 {len(valid_contours)} 个对象")
    
    def analyze_motion(self):
        # 运动分析功能
        if self.video_data is None and self.video_capture is None:
            QtWidgets.QMessageBox.warning(self, "警告", "需要视频数据进行运动分析")
            return
        
        self.statusBar().showMessage("正在分析运动...")
        
        # 使用光流法分析运动
        if self.video_data is not None:
            video = self.video_data
        else:
            # 从视频捕获对象中提取所有帧
            video = []
            self.video_capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
            for _ in range(self.total_frames):
                ret, frame = self.video_capture.read()
                if ret:
                    video.append(frame)
            video = np.array(video)
        
        # 计算光流
        prev_frame = cv2.cvtColor(video[0], cv2.COLOR_BGR2GRAY)
        flow_magnitudes = []
        
        for i in range(1, min(100, video.shape[0])):  # 只分析前100帧
            next_frame = cv2.cvtColor(video[i], cv2.COLOR_BGR2GRAY)
            
            # 计算密集光流
            flow = cv2.calcOpticalFlowFarneback(prev_frame, next_frame, None, 0.5, 3, 15, 3, 5, 1.2, 0)
            
            # 计算光流幅度
            magnitude, _ = cv2.cartToPolar(flow[..., 0], flow[..., 1])
            flow_magnitudes.append(np.mean(magnitude))
            
            prev_frame = next_frame
        
        # 创建运动分析图表
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        ax.plot(flow_magnitudes)
        ax.set_xlabel("帧")
        ax.set_ylabel("平均运动幅度")
        ax.set_title("运动分析")
        self.canvas.draw()
        
        self.statusBar().showMessage("运动分析完成")
    
    def toggle_overlay(self, state):
        # 切换分析叠加层的显示
        if state == Qt.CheckState.Checked.value and self.image_data is not None:
            # 重新运行检测以显示叠加层
            self.detect_cells()
        else:
            # 显示原始图像
            if self.image_data is not None:
                if len(self.image_data.shape) == 3 and self.image_data.shape[0] > 1:
                    self.display_image(self.image_data[self.current_frame])
                else:
                    self.display_image(self.image_data)
    
    def toggle_heatmap(self, state):
        # 切换热图显示
        if state == Qt.CheckState.Checked.value and self.image_data is not None:
            if len(self.image_data.shape) == 3 and self.image_data.shape[0] > 1:
                image = self.image_data[self.current_frame]
            else:
                image = self.image_data
            
            if len(image.shape) == 3:
                image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # 创建热图
            heatmap = cv2.applyColorMap(image, cv2.COLORMAP_JET)
            self.display_image(heatmap)
        else:
            self.toggle_overlay(self.overlay_check.isChecked())
    
    def show_3d_view(self):
        if self.image_data is None:
            return
        
        # 创建3D可视化
        if len(self.image_data.shape) == 3 and self.image_data.shape[0] > 1:
            # 使用matplotlib创建3D可视化
            self.figure.clear()
            ax = self.figure.add_subplot(111, projection='3d')
            
            # 创建网格
            z, y, x = np.mgrid[:self.image_data.shape[0], :self.image_data.shape[1], :self.image_data.shape[2]]
            
            # 只绘制一部分点以提高性能
            stride = 5
            ax.scatter(x[::stride, ::stride, ::stride], 
                      y[::stride, ::stride, ::stride], 
                      z[::stride, ::stride, ::stride], 
                      c=self.image_data[::stride, ::stride, ::stride], 
                      alpha=0.1, s=1)
            
            ax.set_xlabel('X')
            ax.set_ylabel('Y')
            ax.set_zlabel('Z')
            ax.set_title('3D 可视化')
            
            self.canvas.draw()
            self.statusBar().showMessage("3D可视化已创建")
        else:
            QtWidgets.QMessageBox.warning(self, "警告", "需要3D数据创建3D可视化")
    
    def show_channel_mixer(self):
        # 显示通道混合器对话框
        if self.image_data is None:
            return
        
        if len(self.image_data.shape) < 3 or self.image_data.shape[-1] < 3:
            QtWidgets.QMessageBox.warning(self, "警告", "需要多通道图像")
            return
        
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("通道混合器")
        dialog.setModal(True)
        dialog.resize(300, 200)
        
        layout = QtWidgets.QVBoxLayout(dialog)
        
        # 创建滑块控制每个通道的权重
        red_slider = QtWidgets.QSlider(Qt.Orientation.Horizontal)
        red_slider.setRange(0, 100)
        red_slider.setValue(100)
        red_label = QtWidgets.QQLabel("红色通道: 100%")
        
        green_slider = QtWidgets.QSlider(Qt.Orientation.Horizontal)
        green_slider.setRange(0, 100)
        green_slider.setValue(100)
        green_label = QtWidgets.QLabel("绿色通道: 100%")
        
        blue_slider = QtWidgets.QSlider(Qt.Orientation.Horizontal)
        blue_slider.setRange(0, 100)
        blue_slider.setValue(100)
        blue_label = QtWidgets.QLabel("蓝色通道: 100%")
        
        # 连接信号
        def update_channel_mixer():
            r_weight = red_slider.value() / 100.0
            g_weight = green_slider.value() / 100.0
            b_weight = blue_slider.value() / 100.0
            
            red_label.setText(f"红色通道: {red_slider.value()}%")
            green_label.setText(f"绿色通道: {green_slider.value()}%")
            blue_label.setText(f"蓝色通道: {blue_slider.value()}%")
            
            # 应用通道混合
            mixed = self.image_data.copy().astype(np.float32)
            mixed[..., 0] *= r_weight
            mixed[..., 1] *= g_weight
            mixed[..., 2] *= b_weight
            
            mixed = np.clip(mixed, 0, 255).astype(np.uint8)
            self.display_image(mixed)
        
        red_slider.valueChanged.connect(update_channel_mixer)
        green_slider.valueChanged.connect(update_channel_mixer)
        blue_slider.valueChanged.connect(update_channel_mixer)
        
        # 添加到布局
        layout.addWidget(red_label)
        layout.addWidget(red_slider)
        layout.addWidget(green_label)
        layout.addWidget(green_slider)
        layout.addWidget(blue_label)
        layout.addWidget(blue_slider)
        
        # 添加按钮
        button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Ok | QtWidgets.QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        
        dialog.exec()
    
    def show_lut_settings(self):
        # 显示LUT设置对话框
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("LUT设置")
        dialog.setModal(True)
        dialog.resize(300, 400)
        
        layout = QtWidgets.QVBoxLayout(dialog)
        
        # 创建LUT选择列表
        lut_list = QtWidgets.QListWidget()
        luts = ["灰度", "热力图", "彩虹", "冰火", "分类"]
        
        for lut in luts:
            lut_list.addItem(lut)
        
        layout.addWidget(QtWidgets.QLabel("选择颜色查找表:"))
        layout.addWidget(lut_list)
        
        # 添加按钮
        button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Ok | QtWidgets.QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        
        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            selected_lut = lut_list.currentItem().text()
            self.apply_lut(selected_lut)
    
    def apply_lut(self, lut_name):
        if self.image_data is None:
            return
        
        # 应用选择的LUT
        if len(self.image_data.shape) == 3 and self.image_data.shape[0] > 1:
            image = self.image_data[self.current_frame]
        else:
            image = self.image_data
        
        if len(image.shape) == 3:
            image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        if lut_name == "灰度":
            result = image
        elif lut_name == "热力图":
            result = cv2.applyColorMap(image, cv2.COLORMAP_JET)
        elif lut_name == "彩虹":
            result = cv2.applyColorMap(image, cv2.COLORMAP_RAINBOW)
        elif lut_name == "冰火":
            result = cv2.applyColorMap(image, cv2.COLORMAP_COOL)
        elif lut_name == "分类":
            # 使用伪彩色分类
            _, labeled = cv2.connectedComponents(image)
            result = cv2.applyColorMap((labeled * 10).astype(np.uint8), cv2.COLORMAP_JET)
        
        self.display_image(result)
        self.statusBar().showMessage(f"已应用 {lut_name} LUT")
    
    def volume_render(self):
        # 体积渲染功能
        if self.image_data is None or len(self.image_data.shape) != 3:
            QtWidgets.QMessageBox.warning(self, "警告", "需要3D数据进行体积渲染")
            return
        
        try:
            # 使用napari进行体积渲染
            import napari
            viewer = napari.Viewer()
            viewer.add_image(self.image_data)
            napari.run()
        except ImportError:
            QtWidgets.QMessageBox.warning(self, "警告", "需要安装napari库进行体积渲染")
    
    def update_results_table(self, contours, image):
        self.result_table.setRowCount(len(contours))
        
        for i, contour in enumerate(contours):
            area = cv2.contourArea(contour)
            if area > 100:
                M = cv2.moments(contour)
                if M["m00"] != 0:
                    cx = int(M["m10"] / M["m00"])
                    cy = int(M["m01"] / M["m00"])
                    
                    # 计算形状参数
                    perimeter = cv2.arcLength(contour, True)
                    circularity = 4 * np.pi * area / (perimeter * perimeter) if perimeter > 0 else 0
                    
                    # 计算强度
                    mask = np.zeros_like(image)
                    cv2.drawContours(mask, [contour], -1, 255, -1)
                    mean_intensity = cv2.mean(image, mask=mask)[0]
                    
                    self.result_table.setItem(i, 0, QtWidgets.QTableWidgetItem(str(i+1)))
                    self.result_table.setItem(i, 1, QtWidgets.QTableWidgetItem(f"({cx}, {cy})"))
                    self.result_table.setItem(i, 2, QtWidgets.QTableWidgetItem(f"{area:.2f}"))
                    self.result_table.setItem(i, 3, QtWidgets.QTableWidgetItem(f"{mean_intensity:.2f}"))
                    self.result_table.setItem(i, 4, QtWidgets.QTableWidgetItem(f"{circularity:.2f}"))
                    self.result_table.setItem(i, 5, QtWidgets.QTableWidgetItem("未知"))
    
    def export_results(self):
        # 导出分析结果
        if self.result_table.rowCount() == 0:
            QtWidgets.QMessageBox.warning(self, "警告", "没有分析结果可导出")
            return
        
        options = QtWidgets.QFileDialog.Option()
        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "导出结果", "", 
            "CSV文件 (*.csv);;JSON文件 (*.json);;Excel文件 (*.xlsx);;HDF5文件 (*.h5)", 
            options=options
        )
        
        if file_path:
            # 收集结果数据
            results = []
            for row in range(self.result_table.rowCount()):
                result = {
                    'ID': self.result_table.item(row, 0).text(),
                    '位置': self.result_table.item(row, 1).text(),
                    '大小': self.result_table.item(row, 2).text(),
                    '强度': self.result_table.item(row, 3).text(),
                    '形状': self.result_table.item(row, 4).text(),
                    '分类': self.result_table.item(row, 5).text()
                }
                results.append(result)
            
            # 根据文件类型导出
            if file_path.endswith('.csv'):
                df = pd.DataFrame(results)
                df.to_csv(file_path, index=False)
            elif file_path.endswith('.json'):
                with open(file_path, 'w') as f:
                    json.dump(results, f, indent=4)
            elif file_path.endswith('.xlsx'):
                df = pd.DataFrame(results)
                df.to_excel(file_path, index=False)
            elif file_path.endswith('.h5'):
                with h5py.File(file_path, 'w') as f:
                    # 保存结果数据
                    for i, result in enumerate(results):
                        group = f.create_group(f'object_{i}')
                        for key, value in result.items():
                            group.attrs[key] = value
                    
                    # 保存图像数据（如果存在）
                    if self.image_data is not None:
                        f.create_dataset('image_data', data=self.image_data)
            
            self.statusBar().showMessage(f"结果已导出到: {file_path}")
    
    def save_project(self):
        # 保存项目
        options = QtWidgets.QFileDialog.Option()
        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "保存项目", "", 
            "项目文件 (*.micproj);;所有文件 (*)", 
            options=options
        )
        
        if file_path:
            # 创建项目数据
            project_data = {
                'metadata': self.metadata,
                'image_shape': self.image_data.shape if self.image_data is not None else None,
                'image_dtype': str(self.image_data.dtype) if self.image_data is not None else None,
                'rois': self.rois,
                'tracked_objects': self.tracked_objects,
                'timestamp': datetime.now().isoformat()
            }
            
            # 保存项目文件
            with h5py.File(file_path, 'w') as f:
                # 保存元数据
                metadata_group = f.create_group('metadata')
                for key, value in project_data['metadata'].items():
                    metadata_group.attrs[key] = value
                
                # 保存图像数据
                if self.image_data is not None:
                    f.create_dataset('image_data', data=self.image_data, compression='gzip')
                
                # 保存ROI数据
                if self.rois:
                    roi_group = f.create_group('rois')
                    for i, roi in enumerate(self.rois):
                        roi_group.create_dataset(f'roi_{i}', data=roi)
                
                # 保存追踪数据
                if self.tracked_objects:
                    tracking_group = f.create_group('tracking')
                    for track_id, track in self.tracked_objects.items():
                        tracking_group.create_dataset(f'track_{track_id}', data=track)
                
                # 保存项目信息
                info_group = f.create_group('info')
                info_group.attrs['timestamp'] = project_data['timestamp']
            
            self.statusBar().showMessage(f"项目已保存: {file_path}")
    
    def show_preferences(self):
        # 显示首选项对话框
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("首选项")
        dialog.setModal(True)
        dialog.resize(400, 300)
        
        layout = QtWidgets.QVBoxLayout(dialog)
        
        # 创建选项卡
        tab_widget = QtWidgets.QTabWidget()
        
        # 常规设置
        general_tab = QtWidgets.QWidget()
        general_layout = QtWidgets.QVBoxLayout(general_tab)
        
        theme_label = QtWidgets.QLabel("主题:")
        theme_combo = QtWidgets.QComboBox()
        theme_combo.addItems(["暗色", "亮色", "系统默认"])
        
        general_layout.addWidget(theme_label)
        general_layout.addWidget(theme_combo)
        general_layout.addStretch()
        
        # 显示设置
        display_tab = QtWidgets.QWidget()
        display_layout = QtWidgets.QVBoxLayout(display_tab)
        
        default_lut_label = QtWidgets.QLabel("默认LUT:")
        default_lut_combo = QtWidgets.QComboBox()
        default_lut_combo.addItems(["灰度", "热力图", "彩虹", "冰火"])
        
        display_layout.addWidget(default_lut_label)
        display_layout.addWidget(default_lut_combo)
        display_layout.addStretch()
        
        # 分析设置
        analysis_tab = QtWidgets.QWidget()
        analysis_layout = QtWidgets.QVBoxLayout(analysis_tab)
        
        min_size_label = QtWidgets.QLabel("最小对象大小:")
        min_size_spin = QtWidgets.QSpinBox()
        min_size_spin.setRange(1, 1000)
        min_size_spin.setValue(100)
        
        analysis_layout.addWidget(min_size_label)
        analysis_layout.addWidget(min_size_spin)
        analysis_layout.addStretch()
        
        # 添加到选项卡
        tab_widget.addTab(general_tab, "常规")
        tab_widget.addTab(display_tab, "显示")
        tab_widget.addTab(analysis_tab, "分析")
        
        layout.addWidget(tab_widget)
        
        # 添加按钮
        button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Ok | QtWidgets.QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        
        dialog.exec()
    
    def toggle_fullscreen(self, state):
        if state:
            self.showFullScreen()
        else:
            self.showNormal()
    
    def draw_rois(self):
        # 绘制ROI到图像上
        if not self.rois:
            return
        
        # 获取当前图像
        if len(self.image_data.shape) == 3 and self.image_data.shape[0] > 1:
            image = self.image_data[self.current_frame]
        else:
            image = self.image_data
        
        if len(image.shape) == 2:
            display_image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        else:
            display_image = image.copy()
        
        # 绘制所有ROI
        for roi in self.rois:
            if len(roi) == 2:  # 矩形ROI [x, y, w, h]
                x, y, w, h = roi
                cv2.rectangle(display_image, (x, y), (x+w, y+h), (0, 255, 0), 2)
            elif len(roi) > 2:  # 多边形ROI
                pts = np.array(roi, np.int32)
                pts = pts.reshape((-1, 1, 2))
                cv2.polylines(display_image, [pts], True, (0, 255, 0), 2)
        
        self.display_image(display_image)


def main():
    app = QtWidgets.QApplication(sys.argv)
    
    # 设置应用程序样式
    app.setStyle('Fusion')
    
    # 创建并显示主窗口
    viewer = AdvancedMicroscopeViewer()
    viewer.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()