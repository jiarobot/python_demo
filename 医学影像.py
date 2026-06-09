import sys
import numpy as np
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QSlider, QPushButton, 
                             QFileDialog, QAction, QToolBar, QStatusBar,
                             QSplitter, QFrame, QComboBox, QSpinBox, 
                             QTabWidget, QGroupBox, QCheckBox, QDoubleSpinBox,
                             QMessageBox, QProgressDialog, QListWidget, QTextEdit)
from PyQt5.QtCore import Qt, QSize, QPoint, QRect, QThread, pyqtSignal
from PyQt5.QtGui import QPixmap, QImage, QIcon, QPainter, QPen, QColor, QFont, QCursor
import pydicom
from pydicom.data import get_testdata_file
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from scipy import ndimage
import os
import cv2
from skimage import filters, exposure, measure
from scipy.ndimage import zoom, rotate
import matplotlib.cm as cm
import json
from datetime import datetime

class DicomLoaderThread(QThread):
    """DICOM文件加载线程"""
    progress = pyqtSignal(int)
    finished_loading = pyqtSignal(list, object)
    error = pyqtSignal(str)
    
    def __init__(self, folder_path):
        super().__init__()
        self.folder_path = folder_path
    
    def run(self):
        try:
            dicom_files = []
            all_files = os.listdir(self.folder_path)
            total_files = len([f for f in all_files if f.endswith('.dcm')])
            
            for i, file in enumerate(all_files):
                if file.endswith('.dcm'):
                    file_path = os.path.join(self.folder_path, file)
                    try:
                        ds = pydicom.dcmread(file_path, force=True)
                        dicom_files.append((file_path, ds))
                    except Exception as e:
                        print(f"Error reading {file}: {e}")
                    
                    # 发射进度信号
                    self.progress.emit(int((i + 1) / total_files * 100))
            
            if not dicom_files:
                self.error.emit("未找到有效的DICOM文件")
                return
            
            # 按切片位置排序
            dicom_files.sort(key=lambda x: float(x[1].ImagePositionPatient[2] 
                                                if hasattr(x[1], 'ImagePositionPatient') 
                                                else x[1].InstanceNumber))
            
            # 构建3D体积数据
            volume_data = self.build_volume(dicom_files)
            self.finished_loading.emit(dicom_files, volume_data)
            
        except Exception as e:
            self.error.emit(f"加载错误: {str(e)}")
    
    def build_volume(self, dicom_files):
        """构建3D体积数据"""
        slices = []
        for file_path, ds in dicom_files:
            if hasattr(ds, 'pixel_array'):
                # 应用RescaleSlope和RescaleIntercept
                pixel_data = ds.pixel_array.astype(np.float32)
                if hasattr(ds, 'RescaleSlope'):
                    pixel_data *= ds.RescaleSlope
                if hasattr(ds, 'RescaleIntercept'):
                    pixel_data += ds.RescaleIntercept
                slices.append(pixel_data)
        
        if slices:
            return np.stack(slices, axis=0)
        return None

class Measurement:
    """测量结果类"""
    def __init__(self, type, points, value=None, unit="mm"):
        self.type = type  # 'length', 'angle', 'area'
        self.points = points  # 测量点坐标
        self.value = value
        self.unit = unit
        self.timestamp = datetime.now()
        self.id = f"{type}_{self.timestamp.strftime('%H%M%S')}"
    
    def to_dict(self):
        return {
            'id': self.id,
            'type': self.type,
            'points': self.points,
            'value': self.value,
            'unit': self.unit,
            'timestamp': self.timestamp.isoformat()
        }

class MedicalImageViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("高级医学影像可视化工具 v2.0")
        self.setGeometry(100, 100, 1400, 900)
        
        # 初始化变量
        self.dicom_files = []
        self.volume_data = None
        self.current_plane = "axial"  # axial, sagittal, coronal
        self.current_index = 0
        self.ww = 400
        self.wl = 40
        self.zoom_factor = 1.0
        self.pan_offset = QPoint(0, 0)
        self.pan_start = None
        self.is_panning = False
        
        # 测量相关
        self.measurement_mode = None  # 'length', 'angle', 'area'
        self.measurement_points = []
        self.measurements = []
        self.current_measurement = None
        
        # 图像处理参数
        self.colormap = "gray"
        self.invert_colors = False
        self.gamma = 1.0
        self.contrast = 1.0
        self.brightness = 0.0
        
        # 多平面重建缓存
        self.mpr_cache = {}
        
        self.init_ui()
        
    def init_ui(self):
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # 创建主分割器
        main_splitter = QSplitter(Qt.Horizontal)
        
        # 左侧图像显示区域
        image_widget = QWidget()
        image_layout = QVBoxLayout(image_widget)
        
        # 图像显示标签
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setMinimumSize(600, 600)
        self.image_label.setStyleSheet("background-color: black;")
        self.image_label.mousePressEvent = self.mouse_press_event
        self.image_label.mouseMoveEvent = self.mouse_move_event
        self.image_label.mouseReleaseEvent = self.mouse_release_event
        self.image_label.wheelEvent = self.wheel_event
        image_layout.addWidget(self.image_label)
        
        # 图像信息显示
        self.info_label = QLabel("加载图像以显示信息")
        self.info_label.setStyleSheet("background-color: #f0f0f0; padding: 5px;")
        image_layout.addWidget(self.info_label)
        
        # 右侧控制面板（使用选项卡）
        control_tabs = QTabWidget()
        control_tabs.setMaximumWidth(400)
        
        # 基本控制选项卡
        basic_tab = QWidget()
        basic_layout = QVBoxLayout(basic_tab)
        
        # 文件操作
        file_group = QGroupBox("文件操作")
        file_layout = QVBoxLayout(file_group)
        
        open_btn = QPushButton("打开DICOM文件夹")
        open_btn.clicked.connect(self.open_dicom_folder)
        file_layout.addWidget(open_btn)
        
        export_btn = QPushButton("导出当前图像")
        export_btn.clicked.connect(self.export_image)
        file_layout.addWidget(export_btn)
        
        basic_layout.addWidget(file_group)
        
        # 显示控制
        display_group = QGroupBox("显示控制")
        display_layout = QVBoxLayout(display_group)
        
        display_layout.addWidget(QLabel("窗宽:"))
        self.ww_slider = QSlider(Qt.Horizontal)
        self.ww_slider.setRange(1, 3000)
        self.ww_slider.setValue(self.ww)
        self.ww_slider.valueChanged.connect(self.update_display)
        display_layout.addWidget(self.ww_slider)
        
        display_layout.addWidget(QLabel("窗位:"))
        self.wl_slider = QSlider(Qt.Horizontal)
        self.wl_slider.setRange(-1000, 1000)
        self.wl_slider.setValue(self.wl)
        self.wl_slider.valueChanged.connect(self.update_display)
        display_layout.addWidget(self.wl_slider)
        
        display_layout.addWidget(QLabel("缩放:"))
        self.zoom_slider = QSlider(Qt.Horizontal)
        self.zoom_slider.setRange(10, 400)
        self.zoom_slider.setValue(100)
        self.zoom_slider.valueChanged.connect(self.update_zoom)
        display_layout.addWidget(self.zoom_slider)
        
        # 色彩映射
        color_layout = QHBoxLayout()
        color_layout.addWidget(QLabel("色彩:"))
        self.colormap_combo = QComboBox()
        self.colormap_combo.addItems(["gray", "hot", "cool", "bone", "jet", "viridis"])
        self.colormap_combo.currentTextChanged.connect(self.update_display)
        color_layout.addWidget(self.colormap_combo)
        
        self.invert_check = QCheckBox("反色")
        self.invert_check.stateChanged.connect(self.update_display)
        color_layout.addWidget(self.invert_check)
        display_layout.addLayout(color_layout)
        
        basic_layout.addWidget(display_group)
        
        # 切片导航
        slice_group = QGroupBox("切片导航")
        slice_layout = QVBoxLayout(slice_group)
        
        plane_layout = QHBoxLayout()
        plane_layout.addWidget(QLabel("平面:"))
        self.plane_combo = QComboBox()
        self.plane_combo.addItems(["轴向", "矢状", "冠状"])
        self.plane_combo.currentTextChanged.connect(self.change_plane)
        plane_layout.addWidget(self.plane_combo)
        slice_layout.addLayout(plane_layout)
        
        slice_control_layout = QHBoxLayout()
        self.slice_spinner = QSpinBox()
        self.slice_spinner.valueChanged.connect(self.change_slice)
        slice_control_layout.addWidget(self.slice_spinner)
        
        slice_prev_btn = QPushButton("◀")
        slice_prev_btn.clicked.connect(self.prev_slice)
        slice_control_layout.addWidget(slice_prev_btn)
        
        slice_next_btn = QPushButton("▶")
        slice_next_btn.clicked.connect(self.next_slice)
        slice_control_layout.addWidget(slice_next_btn)
        slice_layout.addLayout(slice_control_layout)
        
        # 切片预览
        self.slice_preview_label = QLabel("无预览")
        self.slice_preview_label.setFixedHeight(100)
        self.slice_preview_label.setStyleSheet("background-color: black;")
        slice_layout.addWidget(self.slice_preview_label)
        
        basic_layout.addWidget(slice_group)
        basic_layout.addStretch()
        
        # 图像处理选项卡
        processing_tab = QWidget()
        processing_layout = QVBoxLayout(processing_tab)
        
        # 滤波处理
        filter_group = QGroupBox("图像滤波")
        filter_layout = QVBoxLayout(filter_group)
        
        filter_buttons_layout = QHBoxLayout()
        gaussian_btn = QPushButton("高斯滤波")
        gaussian_btn.clicked.connect(self.apply_gaussian_filter)
        filter_buttons_layout.addWidget(gaussian_btn)
        
        median_btn = QPushButton("中值滤波")
        median_btn.clicked.connect(self.apply_median_filter)
        filter_buttons_layout.addWidget(median_btn)
        
        sobel_btn = QPushButton("边缘检测")
        sobel_btn.clicked.connect(self.apply_sobel_filter)
        filter_buttons_layout.addWidget(sobel_btn)
        filter_layout.addLayout(filter_buttons_layout)
        
        # 滤波参数
        param_layout = QHBoxLayout()
        param_layout.addWidget(QLabel("参数:"))
        self.filter_param = QDoubleSpinBox()
        self.filter_param.setRange(0.1, 10.0)
        self.filter_param.setValue(1.0)
        param_layout.addWidget(self.filter_param)
        filter_layout.addLayout(param_layout)
        
        processing_layout.addWidget(filter_group)
        
        # 对比度增强
        enhance_group = QGroupBox("对比度增强")
        enhance_layout = QVBoxLayout(enhance_group)
        
        gamma_layout = QHBoxLayout()
        gamma_layout.addWidget(QLabel("Gamma:"))
        self.gamma_slider = QSlider(Qt.Horizontal)
        self.gamma_slider.setRange(10, 400)
        self.gamma_slider.setValue(100)
        self.gamma_slider.valueChanged.connect(self.update_display)
        gamma_layout.addWidget(self.gamma_slider)
        enhance_layout.addLayout(gamma_layout)
        
        contrast_layout = QHBoxLayout()
        contrast_layout.addWidget(QLabel("对比度:"))
        self.contrast_slider = QSlider(Qt.Horizontal)
        self.contrast_slider.setRange(10, 400)
        self.contrast_slider.setValue(100)
        self.contrast_slider.valueChanged.connect(self.update_display)
        contrast_layout.addWidget(self.contrast_slider)
        enhance_layout.addLayout(contrast_layout)
        
        processing_layout.addWidget(enhance_group)
        
        # 三维处理
        volume_group = QGroupBox("三维处理")
        volume_layout = QVBoxLayout(volume_group)
        
        mip_btn = QPushButton("最大密度投影")
        mip_btn.clicked.connect(self.generate_mip)
        volume_layout.addWidget(mip_btn)
        
        volume_render_btn = QPushButton("体积渲染")
        volume_render_btn.clicked.connect(self.volume_render)
        volume_layout.addWidget(volume_render_btn)
        
        processing_layout.addWidget(volume_group)
        processing_layout.addStretch()
        
        # 测量工具选项卡
        measure_tab = QWidget()
        measure_layout = QVBoxLayout(measure_tab)
        
        # 测量工具选择
        tools_group = QGroupBox("测量工具")
        tools_layout = QVBoxLayout(tools_group)
        
        tool_buttons_layout = QHBoxLayout()
        length_btn = QPushButton("长度测量")
        length_btn.clicked.connect(lambda: self.set_measurement_mode('length'))
        tool_buttons_layout.addWidget(length_btn)
        
        angle_btn = QPushButton("角度测量")
        angle_btn.clicked.connect(lambda: self.set_measurement_mode('angle'))
        tool_buttons_layout.addWidget(angle_btn)
        
        area_btn = QPushButton("面积测量")
        area_btn.clicked.connect(lambda: self.set_measurement_mode('area'))
        tool_buttons_layout.addWidget(area_btn)
        tools_layout.addLayout(tool_buttons_layout)
        
        clear_btn = QPushButton("清除测量")
        clear_btn.clicked.connect(self.clear_measurements)
        tools_layout.addWidget(clear_btn)
        
        measure_layout.addWidget(tools_group)
        
        # 测量结果列表
        results_group = QGroupBox("测量结果")
        results_layout = QVBoxLayout(results_group)
        
        self.measurements_list = QListWidget()
        results_layout.addWidget(self.measurements_list)
        
        export_measures_btn = QPushButton("导出测量结果")
        export_measures_btn.clicked.connect(self.export_measurements)
        results_layout.addWidget(export_measures_btn)
        
        measure_layout.addWidget(results_group)
        measure_layout.addStretch()
        
        # 信息显示选项卡
        info_tab = QWidget()
        info_layout = QVBoxLayout(info_tab)
        
        info_text = QTextEdit()
        info_text.setReadOnly(True)
        info_layout.addWidget(info_text)
        self.info_text = info_text
        
        # 添加选项卡
        control_tabs.addTab(basic_tab, "基本控制")
        control_tabs.addTab(processing_tab, "图像处理")
        control_tabs.addTab(measure_tab, "测量工具")
        control_tabs.addTab(info_tab, "DICOM信息")
        
        # 将组件添加到主分割器
        main_splitter.addWidget(image_widget)
        main_splitter.addWidget(control_tabs)
        main_splitter.setSizes([1000, 400])
        
        main_layout.addWidget(main_splitter)
        
        # 创建工具栏
        self.create_toolbar()
        
        # 创建状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪")
        
        # 加载示例数据
        self.load_sample_data()
    
    def create_toolbar(self):
        """创建工具栏"""
        toolbar = QToolBar("主工具栏")
        toolbar.setIconSize(QSize(24, 24))
        self.addToolBar(toolbar)
        
        # 文件操作
        open_action = QAction("📁 打开", self)
        open_action.triggered.connect(self.open_dicom_folder)
        toolbar.addAction(open_action)
        
        toolbar.addSeparator()
        
        # 视图操作
        zoom_in_action = QAction("🔍 放大", self)
        zoom_in_action.triggered.connect(self.zoom_in)
        toolbar.addAction(zoom_in_action)
        
        zoom_out_action = QAction("🔎 缩小", self)
        zoom_out_action.triggered.connect(self.zoom_out)
        toolbar.addAction(zoom_out_action)
        
        pan_action = QAction("✋ 平移", self)
        pan_action.triggered.connect(self.activate_pan)
        toolbar.addAction(pan_action)
        
        reset_action = QAction("🔄 重置", self)
        reset_action.triggered.connect(self.reset_view)
        toolbar.addAction(reset_action)
        
        toolbar.addSeparator()
        
        # 测量工具
        length_action = QAction("📏 长度", self)
        length_action.triggered.connect(lambda: self.set_measurement_mode('length'))
        toolbar.addAction(length_action)
        
        angle_action = QAction("📐 角度", self)
        angle_action.triggered.connect(lambda: self.set_measurement_mode('angle'))
        toolbar.addAction(angle_action)
        
        toolbar.addSeparator()
        
        # 图像处理
        invert_action = QAction("🎨 反色", self)
        invert_action.triggered.connect(self.toggle_invert)
        toolbar.addAction(invert_action)
    
    def load_sample_data(self):
        """加载示例DICOM数据"""
        try:
            sample_file = get_testdata_file("CT_small.dcm")
            if sample_file:
                ds = pydicom.dcmread(sample_file)
                self.image_data = ds.pixel_array
                self.dicom_files = [(sample_file, ds)]
                self.volume_data = np.expand_dims(self.image_data, axis=0)
                self.update_slice_controls()
                self.update_image()
                self.update_dicom_info()
        except Exception as e:
            self.status_bar.showMessage(f"无法加载示例数据: {e}")
    
    def open_dicom_folder(self):
        """打开DICOM文件夹"""
        folder = QFileDialog.getExistingDirectory(self, "选择DICOM文件夹")
        if folder:
            # 显示进度对话框
            progress_dialog = QProgressDialog("加载DICOM文件中...", "取消", 0, 100, self)
            progress_dialog.setWindowTitle("加载中")
            progress_dialog.setWindowModality(Qt.WindowModal)
            
            # 创建加载线程
            self.loader_thread = DicomLoaderThread(folder)
            self.loader_thread.progress.connect(progress_dialog.setValue)
            self.loader_thread.finished_loading.connect(self.on_dicom_loaded)
            self.loader_thread.error.connect(self.on_dicom_load_error)
            
            # 连接取消按钮
            progress_dialog.canceled.connect(self.loader_thread.terminate)
            
            self.loader_thread.start()
            progress_dialog.exec_()
    
    def on_dicom_loaded(self, dicom_files, volume_data):
        """DICOM加载完成回调"""
        self.dicom_files = dicom_files
        self.volume_data = volume_data
        self.update_slice_controls()
        self.update_image()
        self.update_dicom_info()
        self.status_bar.showMessage(f"已加载 {len(dicom_files)} 个DICOM切片")
    
    def on_dicom_load_error(self, error_msg):
        """DICOM加载错误回调"""
        QMessageBox.critical(self, "加载错误", error_msg)
    
    def update_slice_controls(self):
        """更新切片控制"""
        if self.volume_data is not None:
            if self.current_plane == "axial":
                max_slices = self.volume_data.shape[0]
            elif self.current_plane == "sagittal":
                max_slices = self.volume_data.shape[1]
            else:  # coronal
                max_slices = self.volume_data.shape[2]
            
            self.slice_spinner.setRange(0, max_slices - 1)
            self.slice_spinner.setValue(0)
            self.current_index = 0
    
    def get_current_slice(self):
        """获取当前切片数据"""
        if self.volume_data is None:
            return None
        
        try:
            if self.current_plane == "axial":
                return self.volume_data[self.current_index, :, :]
            elif self.current_plane == "sagittal":
                return self.volume_data[:, self.current_index, :]
            else:  # coronal
                return self.volume_data[:, :, self.current_index]
        except IndexError:
            return None
    
    def update_image(self):
        """更新显示的图像"""
        slice_data = self.get_current_slice()
        if slice_data is None:
            return
        
        # 应用窗宽窗位
        min_val = self.wl - self.ww / 2
        max_val = self.wl + self.ww / 2
        clipped = np.clip(slice_data, min_val, max_val)
        
        # 归一化到0-1
        normalized = (clipped - min_val) / (max_val - min_val)
        
        # 应用Gamma校正
        normalized = normalized ** (1.0 / (self.gamma_slider.value() / 100.0))
        
        # 应用对比度
        normalized = np.clip((normalized - 0.5) * (self.contrast_slider.value() / 100.0) + 0.5, 0, 1)
        
        # 转换为8位
        image_8bit = (normalized * 255).astype(np.uint8)
        
        # 应用色彩映射
        if self.colormap != "gray":
            colormap_fn = plt.get_cmap(self.colormap)
            colored_image = (colormap_fn(image_8bit / 255.0) * 255).astype(np.uint8)
            image_8bit = cv2.cvtColor(colored_image, cv2.COLOR_RGBA2RGB)
        
        # 反色
        if self.invert_check.isChecked():
            image_8bit = 255 - image_8bit
        
        # 创建QImage
        if len(image_8bit.shape) == 2:  # 灰度图
            height, width = image_8bit.shape
            bytes_per_line = width
            q_img = QImage(image_8bit.data, width, height, bytes_per_line, QImage.Format_Grayscale8)
        else:  # 彩色图
            height, width, channels = image_8bit.shape
            bytes_per_line = channels * width
            q_img = QImage(image_8bit.data, width, height, bytes_per_line, QImage.Format_RGB888)
        
        # 应用缩放
        if self.zoom_factor != 1.0:
            new_width = int(width * self.zoom_factor)
            new_height = int(height * self.zoom_factor)
            q_img = q_img.scaled(new_width, new_height, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        
        # 创建Pixmap并绘制测量结果
        pixmap = QPixmap.fromImage(q_img)
        
        # 绘制测量结果
        if self.measurements:
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.Antialiasing)
            self.draw_measurements(painter, pixmap.rect())
            painter.end()
        
        self.image_label.setPixmap(pixmap)
        
        # 更新信息标签
        self.update_info_label()
    
    def draw_measurements(self, painter, rect):
        """绘制测量结果"""
        pen = QPen(QColor(255, 0, 0))
        pen.setWidth(2)
        painter.setPen(pen)
        
        font = QFont()
        font.setPointSize(10)
        painter.setFont(font)
        
        for measurement in self.measurements:
            if measurement.type == 'length' and len(measurement.points) == 2:
                p1, p2 = measurement.points
                painter.drawLine(p1[0], p1[1], p2[0], p2[1])
                
                # 绘制中点标注
                mid_x = (p1[0] + p2[0]) // 2
                mid_y = (p1[1] + p2[1]) // 2
                painter.drawText(mid_x, mid_y, f"{measurement.value:.1f}{measurement.unit}")
            
            elif measurement.type == 'angle' and len(measurement.points) == 3:
                p1, p2, p3 = measurement.points
                painter.drawLine(p1[0], p1[1], p2[0], p2[1])
                painter.drawLine(p2[0], p2[1], p3[0], p3[1])
                
                # 绘制角度标注
                painter.drawText(p2[0], p2[1], f"{measurement.value:.1f}°")
    
    def update_info_label(self):
        """更新信息标签"""
        if self.volume_data is not None:
            slice_data = self.get_current_slice()
            if slice_data is not None:
                info_text = (f"切片: {self.current_index + 1}/{self.get_max_slices()} | "
                           f"窗宽: {self.ww} | 窗位: {self.wl} | "
                           f"缩放: {self.zoom_factor:.1f}x | "
                           f"尺寸: {slice_data.shape[1]}×{slice_data.shape[0]}")
                self.info_label.setText(info_text)
    
    def get_max_slices(self):
        """获取最大切片数"""
        if self.volume_data is None:
            return 0
        
        if self.current_plane == "axial":
            return self.volume_data.shape[0]
        elif self.current_plane == "sagittal":
            return self.volume_data.shape[1]
        else:  # coronal
            return self.volume_data.shape[2]
    
    def update_dicom_info(self):
        """更新DICOM信息"""
        if self.dicom_files and self.info_text:
            info_str = "DICOM信息:\n\n"
            ds = self.dicom_files[0][1]  # 第一个文件的数据集
            
            # 基本信息
            if hasattr(ds, 'PatientName'):
                info_str += f"患者: {ds.PatientName}\n"
            if hasattr(ds, 'PatientID'):
                info_str += f"ID: {ds.PatientID}\n"
            if hasattr(ds, 'StudyDate'):
                info_str += f"检查日期: {ds.StudyDate}\n"
            if hasattr(ds, 'Modality'):
                info_str += f"模态: {ds.Modality}\n"
            if hasattr(ds, 'StudyDescription'):
                info_str += f"检查描述: {ds.StudyDescription}\n"
            
            # 图像信息
            info_str += f"\n图像信息:\n"
            info_str += f"切片数: {len(self.dicom_files)}\n"
            if hasattr(ds, 'Rows') and hasattr(ds, 'Columns'):
                info_str += f"图像尺寸: {ds.Rows}×{ds.Columns}\n"
            if hasattr(ds, 'PixelSpacing'):
                info_str += f"像素间距: {ds.PixelSpacing} mm\n"
            if hasattr(ds, 'SliceThickness'):
                info_str += f"层厚: {ds.SliceThickness} mm\n"
            
            self.info_text.setText(info_str)
    
    def update_display(self):
        """更新显示（窗宽窗位、色彩等变化时调用）"""
        self.ww = self.ww_slider.value()
        self.wl = self.wl_slider.value()
        self.colormap = self.colormap_combo.currentText()
        self.update_image()
    
    def update_zoom(self, value):
        """更新缩放"""
        self.zoom_factor = value / 100.0
        self.update_image()
    
    def change_slice(self, index):
        """改变当前切片"""
        if 0 <= index < self.get_max_slices():
            self.current_index = index
            self.update_image()
    
    def prev_slice(self):
        """前一张切片"""
        if self.current_index > 0:
            self.slice_spinner.setValue(self.current_index - 1)
    
    def next_slice(self):
        """后一张切片"""
        if self.current_index < self.get_max_slices() - 1:
            self.slice_spinner.setValue(self.current_index + 1)
    
    def change_plane(self, plane_text):
        """改变重建平面"""
        plane_map = {"轴向": "axial", "矢状": "sagittal", "冠状": "coronal"}
        self.current_plane = plane_map.get(plane_text, "axial")
        self.update_slice_controls()
        self.update_image()
        self.status_bar.showMessage(f"已切换到{plane_text}视图")
    
    def set_measurement_mode(self, mode):
        """设置测量模式"""
        self.measurement_mode = mode
        self.measurement_points = []
        mode_names = {'length': '长度', 'angle': '角度', 'area': '面积'}
        self.status_bar.showMessage(f"{mode_names[mode]}测量模式已激活")
        self.image_label.setCursor(QCursor(Qt.CrossCursor))
    
    def clear_measurements(self):
        """清除所有测量"""
        self.measurements = []
        self.measurement_points = []
        self.measurements_list.clear()
        self.update_image()
    
    def export_measurements(self):
        """导出测量结果"""
        if not self.measurements:
            QMessageBox.information(self, "导出", "没有测量结果可导出")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(self, "导出测量结果", "", "JSON文件 (*.json)")
        if file_path:
            try:
                measurements_data = [m.to_dict() for m in self.measurements]
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(measurements_data, f, indent=2, ensure_ascii=False)
                QMessageBox.information(self, "导出成功", f"测量结果已导出到: {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "导出错误", f"导出失败: {str(e)}")
    
    def apply_gaussian_filter(self):
        """应用高斯滤波"""
        if self.volume_data is not None:
            sigma = self.filter_param.value()
            self.volume_data = ndimage.gaussian_filter(self.volume_data, sigma=sigma)
            self.update_image()
            self.status_bar.showMessage(f"已应用高斯滤波 (σ={sigma})")
    
    def apply_median_filter(self):
        """应用中值滤波"""
        if self.volume_data is not None:
            size = int(self.filter_param.value())
            self.volume_data = ndimage.median_filter(self.volume_data, size=size)
            self.update_image()
            self.status_bar.showMessage(f"已应用中值滤波 (大小={size})")
    
    def apply_sobel_filter(self):
        """应用Sobel边缘检测"""
        slice_data = self.get_current_slice()
        if slice_data is not None:
            edges = filters.sobel(slice_data)
            # 替换当前切片数据（临时效果）
            temp_data = edges * 255  # 转换为8位范围
            min_val, max_val = temp_data.min(), temp_data.max()
            if max_val > min_val:
                temp_data = ((temp_data - min_val) / (max_val - min_val) * 255).astype(np.uint8)
            
            # 显示处理后的图像
            height, width = temp_data.shape
            q_img = QImage(temp_data.data, width, height, width, QImage.Format_Grayscale8)
            pixmap = QPixmap.fromImage(q_img)
            self.image_label.setPixmap(pixmap)
            self.status_bar.showMessage("已应用Sobel边缘检测")
    
    def generate_mip(self):
        """生成最大密度投影"""
        if self.volume_data is not None:
            mip = np.max(self.volume_data, axis=0)  # 沿Z轴的最大投影
            # 显示MIP
            self.show_processed_image(mip, "最大密度投影")
    
    def volume_render(self):
        """体积渲染（简化版）"""
        if self.volume_data is not None:
            # 简单的最大强度投影作为体积渲染
            render = np.mean(self.volume_data, axis=0)  # 沿Z轴的平均值
            self.show_processed_image(render, "体积渲染")
    
    def show_processed_image(self, image_data, title):
        """显示处理后的图像"""
        # 归一化显示
        min_val, max_val = image_data.min(), image_data.max()
        if max_val > min_val:
            normalized = ((image_data - min_val) / (max_val - min_val) * 255).astype(np.uint8)
        else:
            normalized = image_data.astype(np.uint8)
        
        height, width = normalized.shape
        q_img = QImage(normalized.data, width, height, width, QImage.Format_Grayscale8)
        pixmap = QPixmap.fromImage(q_img)
        
        # 在新窗口中显示
        preview_window = QMainWindow(self)
        preview_window.setWindowTitle(title)
        preview_label = QLabel()
        preview_label.setPixmap(pixmap)
        preview_window.setCentralWidget(preview_label)
        preview_window.resize(600, 600)
        preview_window.show()
    
    def export_image(self):
        """导出当前图像"""
        if self.image_label.pixmap():
            file_path, _ = QFileDialog.getSaveFileName(self, "导出图像", "", "PNG图像 (*.png);;JPEG图像 (*.jpg)")
            if file_path:
                self.image_label.pixmap().save(file_path)
                self.status_bar.showMessage(f"图像已导出到: {file_path}")
    
    def zoom_in(self):
        """放大图像"""
        self.zoom_slider.setValue(min(self.zoom_slider.value() + 10, self.zoom_slider.maximum()))
    
    def zoom_out(self):
        """缩小图像"""
        self.zoom_slider.setValue(max(self.zoom_slider.value() - 10, self.zoom_slider.minimum()))
    
    def activate_pan(self):
        """激活平移模式"""
        self.is_panning = True
        self.image_label.setCursor(QCursor(Qt.OpenHandCursor))
        self.status_bar.showMessage("平移模式已激活 - 点击并拖动来平移图像")
    
    def toggle_invert(self):
        """切换反色"""
        self.invert_check.setChecked(not self.invert_check.isChecked())
        self.update_image()
    
    def reset_view(self):
        """重置视图"""
        self.zoom_slider.setValue(100)
        self.pan_offset = QPoint(0, 0)
        self.ww_slider.setValue(400)
        self.wl_slider.setValue(40)
        self.update_image()
        self.status_bar.showMessage("视图已重置")
    
    def mouse_press_event(self, event):
        """鼠标按下事件"""
        if event.button() == Qt.LeftButton:
            if self.is_panning:
                self.pan_start = event.pos()
                self.image_label.setCursor(QCursor(Qt.ClosedHandCursor))
            elif self.measurement_mode:
                # 测量点采集
                pos = event.pos()
                pixmap_size = self.image_label.pixmap().size()
                label_size = self.image_label.size()
                
                # 计算在图像上的实际坐标
                x_scale = pixmap_size.width() / label_size.width()
                y_scale = pixmap_size.height() / label_size.height()
                scale = min(x_scale, y_scale)
                
                img_x = int((pos.x() - (label_size.width() - pixmap_size.width()/scale) / 2) * scale)
                img_y = int((pos.y() - (label_size.height() - pixmap_size.height()/scale) / 2) * scale)
                
                self.measurement_points.append((img_x, img_y))
                
                # 根据测量模式完成测量
                if self.measurement_mode == 'length' and len(self.measurement_points) == 2:
                    p1, p2 = self.measurement_points
                    distance = np.sqrt((p2[0]-p1[0])**2 + (p2[1]-p1[1])**2)
                    measurement = Measurement('length', self.measurement_points, distance)
                    self.measurements.append(measurement)
                    self.measurements_list.addItem(f"长度: {distance:.1f}像素")
                    self.measurement_points = []
                    
                elif self.measurement_mode == 'angle' and len(self.measurement_points) == 3:
                    p1, p2, p3 = self.measurement_points
                    # 计算角度
                    v1 = np.array([p1[0]-p2[0], p1[1]-p2[1]])
                    v2 = np.array([p3[0]-p2[0], p3[1]-p2[1]])
                    angle = np.degrees(np.arccos(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))))
                    measurement = Measurement('angle', self.measurement_points, angle, "°")
                    self.measurements.append(measurement)
                    self.measurements_list.addItem(f"角度: {angle:.1f}°")
                    self.measurement_points = []
                
                self.update_image()
    
    def mouse_move_event(self, event):
        """鼠标移动事件"""
        if self.is_panning and self.pan_start is not None:
            delta = event.pos() - self.pan_start
            self.pan_offset += delta
            self.pan_start = event.pos()
            # 这里可以实现实际的平移逻辑
            self.update_image()
    
    def mouse_release_event(self, event):
        """鼠标释放事件"""
        if event.button() == Qt.LeftButton:
            self.pan_start = None
            if self.is_panning:
                self.image_label.setCursor(QCursor(Qt.OpenHandCursor))
    
    def wheel_event(self, event):
        """鼠标滚轮事件 - 用于缩放"""
        if event.angleDelta().y() > 0:
            self.zoom_in()
        else:
            self.zoom_out()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # 使用Fusion样式获得更好的外观
    
    # 设置应用程序字体
    font = QFont("Microsoft YaHei", 9)
    app.setFont(font)
    
    viewer = MedicalImageViewer()
    viewer.show()
    sys.exit(app.exec_())