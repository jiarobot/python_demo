import sys
import numpy as np
import cv2
from PIL import Image
import matplotlib
matplotlib.rc("font", family='Microsoft YaHei')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from scipy import ndimage

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QLabel, 
                             QSlider, QPushButton, QComboBox, QSpinBox,
                             QDoubleSpinBox, QFileDialog, QMessageBox,
                             QHBoxLayout, QVBoxLayout, QSplitter, QGroupBox,
                             QTabWidget, QCheckBox, QRadioButton, QButtonGroup,
                             QTextEdit, QScrollArea)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QPixmap, QImage, QIcon, QFont


class MplCanvas(FigureCanvas):
    """Matplotlib 画布用于显示直方图和图表"""
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_subplot(111)
        super().__init__(self.fig)
        self.setParent(parent)


class ImageAnalyzer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.original_image = None
        self.processed_image = None
        self.cv_original = None
        self.cv_processed = None
        self.initUI()
        
    def initUI(self):
        self.setWindowTitle('高级图像分析仪 - OpenCV + PyQt')
        self.setGeometry(100, 100, 1600, 900)
        
        # 创建中心部件和主布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        
        # 左侧面板 - 图像显示
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # 原始图像标签
        self.original_label = QLabel("原始图像")
        self.original_label.setAlignment(Qt.AlignCenter)
        self.original_label.setMinimumSize(400, 300)
        self.original_label.setStyleSheet("border: 1px solid gray;")
        left_layout.addWidget(self.original_label)
        
        # 处理后的图像标签
        self.processed_label = QLabel("处理后的图像")
        self.processed_label.setAlignment(Qt.AlignCenter)
        self.processed_label.setMinimumSize(400, 300)
        self.processed_label.setStyleSheet("border: 1px solid gray;")
        left_layout.addWidget(self.processed_label)
        
        # 右侧面板 - 控制和直方图
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # 创建选项卡
        self.tabs = QTabWidget()
        
        # 基本操作选项卡
        self.basic_tab = QWidget()
        self.setup_basic_tab()
        self.tabs.addTab(self.basic_tab, "基本操作")
        
        # 高级操作选项卡
        self.advanced_tab = QWidget()
        self.setup_advanced_tab()
        self.tabs.addTab(self.advanced_tab, "高级操作")
        
        # 特征检测选项卡
        self.features_tab = QWidget()
        self.setup_features_tab()
        self.tabs.addTab(self.features_tab, "特征检测")
        
        # 图像分割选项卡
        self.segmentation_tab = QWidget()
        self.setup_segmentation_tab()
        self.tabs.addTab(self.segmentation_tab, "图像分割")
        
        # 信息显示选项卡
        self.info_tab = QWidget()
        self.setup_info_tab()
        self.tabs.addTab(self.info_tab, "图像信息")
        
        right_layout.addWidget(self.tabs)
        
        # 直方图画布
        self.histogram_canvas = MplCanvas(self, width=5, height=4, dpi=100)
        right_layout.addWidget(self.histogram_canvas)
        
        # 添加到分割器
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([1000, 600])
        
        main_layout.addWidget(splitter)
        
        # 初始状态
        self.update_parameter_controls()
        
    def setup_basic_tab(self):
        """设置基本操作选项卡"""
        layout = QVBoxLayout(self.basic_tab)
        
        # 文件操作按钮
        file_group = QGroupBox("文件操作")
        file_layout = QHBoxLayout(file_group)
        self.open_button = QPushButton("打开图像")
        self.open_button.clicked.connect(self.open_image)
        self.save_button = QPushButton("保存结果")
        self.save_button.clicked.connect(self.save_image)
        self.reset_button = QPushButton("重置图像")
        self.reset_button.clicked.connect(self.reset_image)
        
        file_layout.addWidget(self.open_button)
        file_layout.addWidget(self.save_button)
        file_layout.addWidget(self.reset_button)
        layout.addWidget(file_group)
        
        # 基本处理类型选择
        process_group = QGroupBox("基本图像处理")
        process_layout = QVBoxLayout(process_group)
        
        process_layout.addWidget(QLabel("处理类型:"))
        self.process_combo = QComboBox()
        self.process_combo.addItems([
            "无", 
            "灰度化", 
            "二值化", 
            "高斯模糊", 
            "中值滤波",
            "双边滤波",
            "边缘检测", 
            "锐化", 
            "对比度增强", 
            "直方图均衡化",
            "形态学操作",
            "旋转",
            "缩放",
            "平移",
            "仿射变换",
            "透视变换"
        ])
        self.process_combo.currentTextChanged.connect(self.apply_processing)
        process_layout.addWidget(self.process_combo)
        
        # 参数控制
        self.basic_params_widget = QWidget()
        self.basic_params_layout = QVBoxLayout(self.basic_params_widget)
        process_layout.addWidget(self.basic_params_widget)
        
        layout.addWidget(process_group)
        
        # 添加一些空间
        layout.addStretch()
    
    def setup_advanced_tab(self):
        """设置高级操作选项卡"""
        layout = QVBoxLayout(self.advanced_tab)
        
        # 颜色空间转换
        colorspace_group = QGroupBox("颜色空间转换")
        colorspace_layout = QVBoxLayout(colorspace_group)
        
        colorspace_layout.addWidget(QLabel("目标颜色空间:"))
        self.colorspace_combo = QComboBox()
        self.colorspace_combo.addItems([
            "RGB", "BGR", "GRAY", "HSV", "LAB", "YUV", "YCrCb"
        ])
        self.colorspace_combo.currentTextChanged.connect(self.apply_colorspace)
        colorspace_layout.addWidget(self.colorspace_combo)
        
        layout.addWidget(colorspace_group)
        
        # 频域滤波
        freq_group = QGroupBox("频域滤波")
        freq_layout = QVBoxLayout(freq_group)
        
        freq_layout.addWidget(QLabel("滤波器类型:"))
        self.freq_filter_combo = QComboBox()
        self.freq_filter_combo.addItems([
            "理想低通", "理想高通", "巴特沃斯低通", "巴特沃斯高通", "高斯低通", "高斯高通"
        ])
        
        freq_layout.addWidget(QLabel("截止频率:"))
        self.cutoff_spinbox = QDoubleSpinBox()
        self.cutoff_spinbox.setRange(0.1, 100.0)
        self.cutoff_spinbox.setValue(30.0)
        self.cutoff_spinbox.setSingleStep(1.0)
        
        freq_layout.addWidget(self.freq_filter_combo)
        freq_layout.addWidget(self.cutoff_spinbox)
        
        self.apply_freq_button = QPushButton("应用频域滤波")
        self.apply_freq_button.clicked.connect(self.apply_frequency_filter)
        freq_layout.addWidget(self.apply_freq_button)
        
        layout.addWidget(freq_group)
        
        # 添加一些空间
        layout.addStretch()
    
    def setup_features_tab(self):
        """设置特征检测选项卡"""
        layout = QVBoxLayout(self.features_tab)
        
        # 角点检测
        corners_group = QGroupBox("角点检测")
        corners_layout = QVBoxLayout(corners_group)
        
        corners_layout.addWidget(QLabel("检测方法:"))
        self.corner_combo = QComboBox()
        self.corner_combo.addItems([
            "Harris角点检测", "Shi-Tomasi角点检测", "FAST角点检测", "ORB特征点", "SIFT特征点"
        ])
        
        corners_layout.addWidget(self.corner_combo)
        
        self.corner_threshold_label = QLabel("阈值/最大角点数:")
        self.corner_threshold_spinbox = QSpinBox()
        self.corner_threshold_spinbox.setRange(1, 1000)
        self.corner_threshold_spinbox.setValue(200)
        
        corners_layout.addWidget(self.corner_threshold_label)
        corners_layout.addWidget(self.corner_threshold_spinbox)
        
        self.detect_corners_button = QPushButton("检测角点")
        self.detect_corners_button.clicked.connect(self.detect_corners)
        corners_layout.addWidget(self.detect_corners_button)
        
        layout.addWidget(corners_group)
        
        # 边缘检测
        edges_group = QGroupBox("边缘检测")
        edges_layout = QVBoxLayout(edges_group)
        
        edges_layout.addWidget(QLabel("检测方法:"))
        self.edge_combo = QComboBox()
        self.edge_combo.addItems([
            "Canny边缘检测", "Sobel算子", "Laplacian算子", "Scharr算子"
        ])
        
        edges_layout.addWidget(self.edge_combo)
        
        self.edge_threshold1_label = QLabel("阈值1:")
        self.edge_threshold1_spinbox = QSpinBox()
        self.edge_threshold1_spinbox.setRange(0, 500)
        self.edge_threshold1_spinbox.setValue(100)
        
        self.edge_threshold2_label = QLabel("阈值2:")
        self.edge_threshold2_spinbox = QSpinBox()
        self.edge_threshold2_spinbox.setRange(0, 500)
        self.edge_threshold2_spinbox.setValue(200)
        
        edges_layout.addWidget(self.edge_threshold1_label)
        edges_layout.addWidget(self.edge_threshold1_spinbox)
        edges_layout.addWidget(self.edge_threshold2_label)
        edges_layout.addWidget(self.edge_threshold2_spinbox)
        
        self.detect_edges_button = QPushButton("检测边缘")
        self.detect_edges_button.clicked.connect(self.detect_edges)
        edges_layout.addWidget(self.detect_edges_button)
        
        layout.addWidget(edges_group)
        
        # 添加一些空间
        layout.addStretch()
    
    def setup_segmentation_tab(self):
        """设置图像分割选项卡"""
        layout = QVBoxLayout(self.segmentation_tab)
        
        # 阈值分割
        threshold_group = QGroupBox("阈值分割")
        threshold_layout = QVBoxLayout(threshold_group)
        
        threshold_layout.addWidget(QLabel("阈值方法:"))
        self.threshold_combo = QComboBox()
        self.threshold_combo.addItems([
            "简单阈值", "自适应阈值(均值)", "自适应阈值(高斯)", "Otsu阈值"
        ])
        
        threshold_layout.addWidget(self.threshold_combo)
        
        self.threshold_value_label = QLabel("阈值:")
        self.threshold_value_spinbox = QSpinBox()
        self.threshold_value_spinbox.setRange(0, 255)
        self.threshold_value_spinbox.setValue(127)
        
        threshold_layout.addWidget(self.threshold_value_label)
        threshold_layout.addWidget(self.threshold_value_spinbox)
        
        self.apply_threshold_button = QPushButton("应用阈值分割")
        self.apply_threshold_button.clicked.connect(self.apply_threshold)
        threshold_layout.addWidget(self.apply_threshold_button)
        
        layout.addWidget(threshold_group)
        
        # 区域分割
        region_group = QGroupBox("区域分割")
        region_layout = QVBoxLayout(region_group)
        
        region_layout.addWidget(QLabel("分割方法:"))
        self.region_combo = QComboBox()
        self.region_combo.addItems([
            "分水岭算法", "GrabCut算法"
        ])
        
        region_layout.addWidget(self.region_combo)
        
        self.apply_region_button = QPushButton("应用区域分割")
        self.apply_region_button.clicked.connect(self.apply_region_segmentation)
        region_layout.addWidget(self.apply_region_button)
        
        layout.addWidget(region_group)
        
        # 添加一些空间
        layout.addStretch()
    
    def setup_info_tab(self):
        """设置图像信息选项卡"""
        layout = QVBoxLayout(self.info_tab)
        
        # 图像信息显示
        self.info_text = QTextEdit()
        self.info_text.setReadOnly(True)
        self.info_text.setFont(QFont("Courier", 10))
        layout.addWidget(self.info_text)
        
        # 添加一些空间
        layout.addStretch()
    
    def update_parameter_controls(self):
        """根据选择的处理类型更新参数控件"""
        # 清除现有控件
        while self.basic_params_layout.count():
            child = self.basic_params_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        process_type = self.process_combo.currentText()
        
        if process_type == "二值化":
            self.threshold_label = QLabel("阈值:")
            self.threshold_slider = QSlider(Qt.Horizontal)
            self.threshold_slider.setRange(0, 255)
            self.threshold_slider.setValue(128)
            self.threshold_slider.valueChanged.connect(self.apply_processing)
            
            self.basic_params_layout.addWidget(self.threshold_label)
            self.basic_params_layout.addWidget(self.threshold_slider)
        
        elif process_type == "高斯模糊":
            self.blur_label = QLabel("模糊半径:")
            self.blur_spinbox = QSpinBox()
            self.blur_spinbox.setRange(1, 20)
            self.blur_spinbox.setValue(2)
            self.blur_spinbox.valueChanged.connect(self.apply_processing)
            
            self.basic_params_layout.addWidget(self.blur_label)
            self.basic_params_layout.addWidget(self.blur_spinbox)
        
        elif process_type == "中值滤波":
            self.median_label = QLabel("滤波器大小:")
            self.median_spinbox = QSpinBox()
            self.median_spinbox.setRange(1, 20)
            self.median_spinbox.setValue(3)
            self.median_spinbox.valueChanged.connect(self.apply_processing)
            
            self.basic_params_layout.addWidget(self.median_label)
            self.basic_params_layout.addWidget(self.median_spinbox)
        
        elif process_type == "双边滤波":
            self.bilateral_d_label = QLabel("直径:")
            self.bilateral_d_spinbox = QSpinBox()
            self.bilateral_d_spinbox.setRange(1, 20)
            self.bilateral_d_spinbox.setValue(9)
            
            self.bilateral_sigma_color_label = QLabel("颜色σ:")
            self.bilateral_sigma_color_spinbox = QSpinBox()
            self.bilateral_sigma_color_spinbox.setRange(1, 150)
            self.bilateral_sigma_color_spinbox.setValue(75)
            
            self.bilateral_sigma_space_label = QLabel("空间σ:")
            self.bilateral_sigma_space_spinbox = QSpinBox()
            self.bilateral_sigma_space_spinbox.setRange(1, 150)
            self.bilateral_sigma_space_spinbox.setValue(75)
            
            self.basic_params_layout.addWidget(self.bilateral_d_label)
            self.basic_params_layout.addWidget(self.bilateral_d_spinbox)
            self.basic_params_layout.addWidget(self.bilateral_sigma_color_label)
            self.basic_params_layout.addWidget(self.bilateral_sigma_color_spinbox)
            self.basic_params_layout.addWidget(self.bilateral_sigma_space_label)
            self.basic_params_layout.addWidget(self.bilateral_sigma_space_spinbox)
            
            # 连接信号
            self.bilateral_d_spinbox.valueChanged.connect(self.apply_processing)
            self.bilateral_sigma_color_spinbox.valueChanged.connect(self.apply_processing)
            self.bilateral_sigma_space_spinbox.valueChanged.connect(self.apply_processing)
        
        elif process_type == "对比度增强":
            self.contrast_label = QLabel("对比度:")
            self.contrast_slider = QSlider(Qt.Horizontal)
            self.contrast_slider.setRange(0, 200)
            self.contrast_slider.setValue(100)
            self.contrast_slider.valueChanged.connect(self.apply_processing)
            
            self.brightness_label = QLabel("亮度:")
            self.brightness_slider = QSlider(Qt.Horizontal)
            self.brightness_slider.setRange(-100, 100)
            self.brightness_slider.setValue(0)
            self.brightness_slider.valueChanged.connect(self.apply_processing)
            
            self.basic_params_layout.addWidget(self.contrast_label)
            self.basic_params_layout.addWidget(self.contrast_slider)
            self.basic_params_layout.addWidget(self.brightness_label)
            self.basic_params_layout.addWidget(self.brightness_slider)
        
        elif process_type == "形态学操作":
            self.morphology_label = QLabel("形态学操作:")
            self.morphology_combo = QComboBox()
            self.morphology_combo.addItems(["膨胀", "腐蚀", "开运算", "闭运算", "形态学梯度", "顶帽", "黑帽"])
            self.morphology_combo.currentTextChanged.connect(self.apply_processing)
            
            self.morphology_kernel_label = QLabel("核大小:")
            self.morphology_kernel_spinbox = QSpinBox()
            self.morphology_kernel_spinbox.setRange(1, 20)
            self.morphology_kernel_spinbox.setValue(3)
            self.morphology_kernel_spinbox.valueChanged.connect(self.apply_processing)
            
            self.basic_params_layout.addWidget(self.morphology_label)
            self.basic_params_layout.addWidget(self.morphology_combo)
            self.basic_params_layout.addWidget(self.morphology_kernel_label)
            self.basic_params_layout.addWidget(self.morphology_kernel_spinbox)
        
        elif process_type == "旋转":
            self.rotate_label = QLabel("旋转角度:")
            self.rotate_spinbox = QSpinBox()
            self.rotate_spinbox.setRange(-180, 180)
            self.rotate_spinbox.setValue(0)
            self.rotate_spinbox.valueChanged.connect(self.apply_processing)
            
            self.basic_params_layout.addWidget(self.rotate_label)
            self.basic_params_layout.addWidget(self.rotate_spinbox)
        
        elif process_type == "缩放":
            self.scale_label = QLabel("缩放比例:")
            self.scale_spinbox = QDoubleSpinBox()
            self.scale_spinbox.setRange(0.1, 5.0)
            self.scale_spinbox.setValue(1.0)
            self.scale_spinbox.setSingleStep(0.1)
            self.scale_spinbox.valueChanged.connect(self.apply_processing)
            
            self.basic_params_layout.addWidget(self.scale_label)
            self.basic_params_layout.addWidget(self.scale_spinbox)
    
    def open_image(self):
        """打开图像文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "打开图像", "", 
            "图像文件 (*.png *.jpg *.jpeg *.bmp *.tif *.tiff)"
        )
        
        if file_path:
            try:
                # 使用OpenCV读取图像
                self.cv_original = cv2.imread(file_path)
                if self.cv_original is None:
                    raise Exception("无法读取图像文件")
                
                # 转换为RGB格式用于显示
                self.cv_original = cv2.cvtColor(self.cv_original, cv2.COLOR_BGR2RGB)
                self.cv_processed = self.cv_original.copy()
                
                # 转换为PIL图像用于兼容性
                self.original_image = Image.fromarray(self.cv_original)
                self.processed_image = self.original_image.copy()
                
                self.display_image()
                self.update_histogram()
                self.update_image_info()
                
            except Exception as e:
                QMessageBox.critical(self, "错误", f"无法打开图像: {str(e)}")
    
    def save_image(self):
        """保存处理后的图像"""
        if self.processed_image is None:
            QMessageBox.warning(self, "警告", "没有图像可保存")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存图像", "", 
            "PNG文件 (*.png);;JPEG文件 (*.jpg *.jpeg);;BMP文件 (*.bmp);;TIFF文件 (*.tif)"
        )
        
        if file_path:
            try:
                # 使用OpenCV保存图像
                cv2.imwrite(file_path, cv2.cvtColor(self.cv_processed, cv2.COLOR_RGB2BGR))
                QMessageBox.information(self, "成功", "图像已保存")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"无法保存图像: {str(e)}")
    
    def reset_image(self):
        """重置图像到原始状态"""
        if self.cv_original is not None:
            self.cv_processed = self.cv_original.copy()
            self.processed_image = Image.fromarray(self.cv_processed)
            self.display_image()
            self.update_histogram()
    
    def display_image(self):
        """显示图像"""
        if self.cv_original is not None:
            # 显示原始图像
            original_qimage = self.cv_to_qimage(self.cv_original)
            self.original_label.setPixmap(
                QPixmap.fromImage(original_qimage).scaled(
                    self.original_label.width(), 
                    self.original_label.height(),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
            )
        
        if self.cv_processed is not None:
            # 显示处理后的图像
            processed_qimage = self.cv_to_qimage(self.cv_processed)
            self.processed_label.setPixmap(
                QPixmap.fromImage(processed_qimage).scaled(
                    self.processed_label.width(), 
                    self.processed_label.height(),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
            )
    
    def cv_to_qimage(self, cv_image):
        """将OpenCV图像转换为QImage"""
        height, width, channel = cv_image.shape
        bytes_per_line = 3 * width
        qimage = QImage(cv_image.data, width, height, bytes_per_line, QImage.Format_RGB888)
        return qimage
    
    def apply_processing(self):
        """应用图像处理"""
        if self.cv_original is None:
            return
        
        self.cv_processed = self.cv_original.copy()
        process_type = self.process_combo.currentText()
        
        try:
            if process_type == "灰度化":
                self.cv_processed = cv2.cvtColor(self.cv_processed, cv2.COLOR_RGB2GRAY)
                self.cv_processed = cv2.cvtColor(self.cv_processed, cv2.COLOR_GRAY2RGB)
            
            elif process_type == "二值化":
                gray = cv2.cvtColor(self.cv_processed, cv2.COLOR_RGB2GRAY)
                threshold = self.threshold_slider.value()
                _, binary = cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY)
                self.cv_processed = cv2.cvtColor(binary, cv2.COLOR_GRAY2RGB)
            
            elif process_type == "高斯模糊":
                ksize = self.blur_spinbox.value()
                # 确保ksize是奇数
                ksize = ksize if ksize % 2 == 1 else ksize + 1
                self.cv_processed = cv2.GaussianBlur(self.cv_processed, (ksize, ksize), 0)
            
            elif process_type == "中值滤波":
                ksize = self.median_spinbox.value()
                # 确保ksize是奇数
                ksize = ksize if ksize % 2 == 1 else ksize + 1
                self.cv_processed = cv2.medianBlur(self.cv_processed, ksize)
            
            elif process_type == "双边滤波":
                d = self.bilateral_d_spinbox.value()
                sigma_color = self.bilateral_sigma_color_spinbox.value()
                sigma_space = self.bilateral_sigma_space_spinbox.value()
                self.cv_processed = cv2.bilateralFilter(
                    self.cv_processed, d, sigma_color, sigma_space
                )
            
            elif process_type == "边缘检测":
                gray = cv2.cvtColor(self.cv_processed, cv2.COLOR_RGB2GRAY)
                edges = cv2.Laplacian(gray, cv2.CV_64F)
                edges = np.uint8(np.absolute(edges))
                self.cv_processed = cv2.cvtColor(edges, cv2.COLOR_GRAY2RGB)
            
            elif process_type == "锐化":
                kernel = np.array([[-1, -1, -1],
                                  [-1,  9, -1],
                                  [-1, -1, -1]])
                self.cv_processed = cv2.filter2D(self.cv_processed, -1, kernel)
            
            elif process_type == "对比度增强":
                contrast = self.contrast_slider.value() / 100.0
                brightness = self.brightness_slider.value()
                self.cv_processed = cv2.convertScaleAbs(
                    self.cv_processed, alpha=contrast, beta=brightness
                )
            
            elif process_type == "直方图均衡化":
                # 转换为YUV色彩空间，对Y通道进行均衡化
                yuv = cv2.cvtColor(self.cv_processed, cv2.COLOR_RGB2YUV)
                yuv[:, :, 0] = cv2.equalizeHist(yuv[:, :, 0])
                self.cv_processed = cv2.cvtColor(yuv, cv2.COLOR_YUV2RGB)
            
            elif process_type == "形态学操作":
                operation = self.morphology_combo.currentText()
                ksize = self.morphology_kernel_spinbox.value()
                kernel = np.ones((ksize, ksize), np.uint8)
                
                if operation == "膨胀":
                    self.cv_processed = cv2.dilate(self.cv_processed, kernel, iterations=1)
                elif operation == "腐蚀":
                    self.cv_processed = cv2.erode(self.cv_processed, kernel, iterations=1)
                elif operation == "开运算":
                    self.cv_processed = cv2.morphologyEx(self.cv_processed, cv2.MORPH_OPEN, kernel)
                elif operation == "闭运算":
                    self.cv_processed = cv2.morphologyEx(self.cv_processed, cv2.MORPH_CLOSE, kernel)
                elif operation == "形态学梯度":
                    self.cv_processed = cv2.morphologyEx(self.cv_processed, cv2.MORPH_GRADIENT, kernel)
                elif operation == "顶帽":
                    self.cv_processed = cv2.morphologyEx(self.cv_processed, cv2.MORPH_TOPHAT, kernel)
                elif operation == "黑帽":
                    self.cv_processed = cv2.morphologyEx(self.cv_processed, cv2.MORPH_BLACKHAT, kernel)
            
            elif process_type == "旋转":
                angle = self.rotate_spinbox.value()
                h, w = self.cv_processed.shape[:2]
                center = (w // 2, h // 2)
                M = cv2.getRotationMatrix2D(center, angle, 1.0)
                self.cv_processed = cv2.warpAffine(self.cv_processed, M, (w, h))
            
            elif process_type == "缩放":
                scale = self.scale_spinbox.value()
                self.cv_processed = cv2.resize(
                    self.cv_processed, None, fx=scale, fy=scale, interpolation=cv2.INTER_LINEAR
                )
            
            elif process_type == "平移":
                # 这里简化处理，使用固定平移值
                tx, ty = 50, 50  # 平移量
                h, w = self.cv_processed.shape[:2]
                M = np.float32([[1, 0, tx], [0, 1, ty]])
                self.cv_processed = cv2.warpAffine(self.cv_processed, M, (w, h))
            
            elif process_type == "仿射变换":
                # 这里简化处理，使用固定变换
                h, w = self.cv_processed.shape[:2]
                pts1 = np.float32([[50, 50], [200, 50], [50, 200]])
                pts2 = np.float32([[10, 100], [200, 50], [100, 250]])
                M = cv2.getAffineTransform(pts1, pts2)
                self.cv_processed = cv2.warpAffine(self.cv_processed, M, (w, h))
            
            elif process_type == "透视变换":
                # 这里简化处理，使用固定变换
                h, w = self.cv_processed.shape[:2]
                pts1 = np.float32([[56, 65], [368, 52], [28, 387], [389, 390]])
                pts2 = np.float32([[0, 0], [300, 0], [0, 300], [300, 300]])
                M = cv2.getPerspectiveTransform(pts1, pts2)
                self.cv_processed = cv2.warpPerspective(self.cv_processed, M, (300, 300))
            
            # 更新PIL图像
            self.processed_image = Image.fromarray(self.cv_processed)
            self.display_image()
            self.update_histogram()
            
        except Exception as e:
            QMessageBox.critical(self, "处理错误", f"图像处理失败: {str(e)}")
    
    def apply_colorspace(self):
        """应用颜色空间转换"""
        if self.cv_original is None:
            return
        
        colorspace = self.colorspace_combo.currentText()
        
        try:
            if colorspace == "RGB":
                self.cv_processed = self.cv_original.copy()
            elif colorspace == "BGR":
                self.cv_processed = cv2.cvtColor(self.cv_original, cv2.COLOR_RGB2BGR)
            elif colorspace == "GRAY":
                gray = cv2.cvtColor(self.cv_original, cv2.COLOR_RGB2GRAY)
                self.cv_processed = cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB)
            elif colorspace == "HSV":
                self.cv_processed = cv2.cvtColor(self.cv_original, cv2.COLOR_RGB2HSV)
            elif colorspace == "LAB":
                self.cv_processed = cv2.cvtColor(self.cv_original, cv2.COLOR_RGB2LAB)
            elif colorspace == "YUV":
                self.cv_processed = cv2.cvtColor(self.cv_original, cv2.COLOR_RGB2YUV)
            elif colorspace == "YCrCb":
                self.cv_processed = cv2.cvtColor(self.cv_original, cv2.COLOR_RGB2YCrCb)
            
            # 更新PIL图像
            self.processed_image = Image.fromarray(self.cv_processed)
            self.display_image()
            self.update_histogram()
            
        except Exception as e:
            QMessageBox.critical(self, "处理错误", f"颜色空间转换失败: {str(e)}")
    
    def apply_frequency_filter(self):
        """应用频域滤波"""
        if self.cv_original is None:
            return
        
        try:
            # 转换为灰度图像
            gray = cv2.cvtColor(self.cv_original, cv2.COLOR_RGB2GRAY)
            
            # 进行傅里叶变换
            f = np.fft.fft2(gray)
            fshift = np.fft.fftshift(f)
            
            # 创建滤波器
            rows, cols = gray.shape
            crow, ccol = rows // 2, cols // 2
            cutoff = self.cutoff_spinbox.value()
            filter_type = self.freq_filter_combo.currentText()
            
            # 创建掩模
            mask = np.zeros((rows, cols), np.uint8)
            
            if filter_type == "理想低通":
                r = cutoff
                cv2.circle(mask, (ccol, crow), int(r), 1, -1)
            elif filter_type == "理想高通":
                r = cutoff
                cv2.circle(mask, (ccol, crow), int(r), 1, -1)
                mask = 1 - mask
            elif filter_type == "巴特沃斯低通":
                n = 2  # 巴特沃斯阶数
                for i in range(rows):
                    for j in range(cols):
                        d = np.sqrt((i - crow)**2 + (j - ccol)**2)
                        mask[i, j] = 1 / (1 + (d / cutoff)**(2*n))
            elif filter_type == "巴特沃斯高通":
                n = 2  # 巴特沃斯阶数
                for i in range(rows):
                    for j in range(cols):
                        d = np.sqrt((i - crow)**2 + (j - ccol)**2)
                        mask[i, j] = 1 / (1 + (cutoff / d)**(2*n))
            elif filter_type == "高斯低通":
                for i in range(rows):
                    for j in range(cols):
                        d = np.sqrt((i - crow)**2 + (j - ccol)**2)
                        mask[i, j] = np.exp(-(d**2) / (2 * (cutoff**2)))
            elif filter_type == "高斯高通":
                for i in range(rows):
                    for j in range(cols):
                        d = np.sqrt((i - crow)**2 + (j - ccol)**2)
                        mask[i, j] = 1 - np.exp(-(d**2) / (2 * (cutoff**2)))
            
            # 应用滤波器
            fshift_filtered = fshift * mask
            
            # 逆傅里叶变换
            f_ishift = np.fft.ifftshift(fshift_filtered)
            img_back = np.fft.ifft2(f_ishift)
            img_back = np.abs(img_back)
            
            # 转换为8位图像
            img_back = np.uint8(255 * img_back / np.max(img_back))
            
            # 转换为RGB用于显示
            self.cv_processed = cv2.cvtColor(img_back, cv2.COLOR_GRAY2RGB)
            
            # 更新PIL图像
            self.processed_image = Image.fromarray(self.cv_processed)
            self.display_image()
            self.update_histogram()
            
        except Exception as e:
            QMessageBox.critical(self, "处理错误", f"频域滤波失败: {str(e)}")
    
    def detect_corners(self):
        """检测角点"""
        if self.cv_original is None:
            return
        
        try:
            gray = cv2.cvtColor(self.cv_original, cv2.COLOR_RGB2GRAY)
            method = self.corner_combo.currentText()
            max_corners = self.corner_threshold_spinbox.value()
            
            if method == "Harris角点检测":
                # Harris角点检测
                gray = np.float32(gray)
                dst = cv2.cornerHarris(gray, 2, 3, 0.04)
                dst = cv2.dilate(dst, None)
                
                # 标记角点
                self.cv_processed = self.cv_original.copy()
                self.cv_processed[dst > 0.01 * dst.max()] = [255, 0, 0]  # 红色角点
            
            elif method == "Shi-Tomasi角点检测":
                # Shi-Tomasi角点检测
                corners = cv2.goodFeaturesToTrack(gray, max_corners, 0.01, 10)
                corners = np.int0(corners)
                
                # 标记角点
                self.cv_processed = self.cv_original.copy()
                for i in corners:
                    x, y = i.ravel()
                    cv2.circle(self.cv_processed, (x, y), 3, (255, 0, 0), -1)  # 红色角点
            
            elif method == "FAST角点检测":
                # FAST角点检测
                fast = cv2.FastFeatureDetector_create()
                keypoints = fast.detect(gray, None)
                
                # 标记角点
                self.cv_processed = self.cv_original.copy()
                self.cv_processed = cv2.drawKeypoints(
                    self.cv_processed, keypoints, None, color=(255, 0, 0)
                )
            
            elif method == "ORB特征点":
                # ORB特征点检测
                orb = cv2.ORB_create(nfeatures=max_corners)
                keypoints = orb.detect(gray, None)
                
                # 标记特征点
                self.cv_processed = self.cv_original.copy()
                self.cv_processed = cv2.drawKeypoints(
                    self.cv_processed, keypoints, None, color=(255, 0, 0)
                )
            
            elif method == "SIFT特征点":
                # SIFT特征点检测
                sift = cv2.SIFT_create(nfeatures=max_corners)
                keypoints = sift.detect(gray, None)
                
                # 标记特征点
                self.cv_processed = self.cv_original.copy()
                self.cv_processed = cv2.drawKeypoints(
                    self.cv_processed, keypoints, None, color=(255, 0, 0)
                )
            
            # 更新PIL图像
            self.processed_image = Image.fromarray(self.cv_processed)
            self.display_image()
            
        except Exception as e:
            QMessageBox.critical(self, "处理错误", f"角点检测失败: {str(e)}")
    
    def detect_edges(self):
        """检测边缘"""
        if self.cv_original is None:
            return
        
        try:
            gray = cv2.cvtColor(self.cv_original, cv2.COLOR_RGB2GRAY)
            method = self.edge_combo.currentText()
            threshold1 = self.edge_threshold1_spinbox.value()
            threshold2 = self.edge_threshold2_spinbox.value()
            
            if method == "Canny边缘检测":
                edges = cv2.Canny(gray, threshold1, threshold2)
            elif method == "Sobel算子":
                sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=5)
                sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=5)
                edges = np.sqrt(sobelx**2 + sobely**2)
                edges = np.uint8(255 * edges / np.max(edges))
            elif method == "Laplacian算子":
                edges = cv2.Laplacian(gray, cv2.CV_64F)
                edges = np.uint8(np.absolute(edges))
            elif method == "Scharr算子":
                scharrx = cv2.Scharr(gray, cv2.CV_64F, 1, 0)
                scharry = cv2.Scharr(gray, cv2.CV_64F, 0, 1)
                edges = np.sqrt(scharrx**2 + scharry**2)
                edges = np.uint8(255 * edges / np.max(edges))
            
            # 转换为RGB用于显示
            self.cv_processed = cv2.cvtColor(edges, cv2.COLOR_GRAY2RGB)
            
            # 更新PIL图像
            self.processed_image = Image.fromarray(self.cv_processed)
            self.display_image()
            self.update_histogram()
            
        except Exception as e:
            QMessageBox.critical(self, "处理错误", f"边缘检测失败: {str(e)}")
    
    def apply_threshold(self):
        """应用阈值分割"""
        if self.cv_original is None:
            return
        
        try:
            gray = cv2.cvtColor(self.cv_original, cv2.COLOR_RGB2GRAY)
            method = self.threshold_combo.currentText()
            threshold_value = self.threshold_value_spinbox.value()
            
            if method == "简单阈值":
                _, thresh = cv2.threshold(gray, threshold_value, 255, cv2.THRESH_BINARY)
            elif method == "自适应阈值(均值)":
                thresh = cv2.adaptiveThreshold(
                    gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 11, 2
                )
            elif method == "自适应阈值(高斯)":
                thresh = cv2.adaptiveThreshold(
                    gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
                )
            elif method == "Otsu阈值":
                _, thresh = cv2.threshold(
                    gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
                )
            
            # 转换为RGB用于显示
            self.cv_processed = cv2.cvtColor(thresh, cv2.COLOR_GRAY2RGB)
            
            # 更新PIL图像
            self.processed_image = Image.fromarray(self.cv_processed)
            self.display_image()
            self.update_histogram()
            
        except Exception as e:
            QMessageBox.critical(self, "处理错误", f"阈值分割失败: {str(e)}")
    
    def apply_region_segmentation(self):
        """应用区域分割"""
        if self.cv_original is None:
            return
        
        try:
            method = self.region_combo.currentText()
            
            if method == "分水岭算法":
                # 转换为灰度图像
                gray = cv2.cvtColor(self.cv_original, cv2.COLOR_RGB2GRAY)
                
                # 应用Otsu阈值
                _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
                
                # 噪声去除
                kernel = np.ones((3, 3), np.uint8)
                opening = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel, iterations=2)
                
                # 确定背景区域
                sure_bg = cv2.dilate(opening, kernel, iterations=3)
                
                # 确定前景区域
                dist_transform = cv2.distanceTransform(opening, cv2.DIST_L2, 5)
                _, sure_fg = cv2.threshold(dist_transform, 0.7 * dist_transform.max(), 255, 0)
                
                # 找到未知区域
                sure_fg = np.uint8(sure_fg)
                unknown = cv2.subtract(sure_bg, sure_fg)
                
                # 标记标签
                _, markers = cv2.connectedComponents(sure_fg)
                
                # 为分水岭算法添加1到所有标签
                markers = markers + 1
                
                # 标记未知区域为0
                markers[unknown == 255] = 0
                
                # 应用分水岭算法
                markers = cv2.watershed(self.cv_original, markers)
                
                # 标记边界为红色
                self.cv_processed = self.cv_original.copy()
                self.cv_processed[markers == -1] = [255, 0, 0]
            
            elif method == "GrabCut算法":
                # 创建一个掩模
                mask = np.zeros(self.cv_original.shape[:2], np.uint8)
                
                # 创建用于前景和背景的临时数组
                bgd_model = np.zeros((1, 65), np.float64)
                fgd_model = np.zeros((1, 65), np.float64)
                
                # 定义ROI（这里使用整个图像）
                h, w = self.cv_original.shape[:2]
                rect = (10, 10, w-20, h-20)
                
                # 应用GrabCut
                cv2.grabCut(self.cv_original, mask, rect, bgd_model, fgd_model, 5, cv2.GC_INIT_WITH_RECT)
                
                # 创建掩模
                mask2 = np.where((mask == 2) | (mask == 0), 0, 1).astype('uint8')
                
                # 应用掩模
                self.cv_processed = self.cv_original * mask2[:, :, np.newaxis]
            
            # 更新PIL图像
            self.processed_image = Image.fromarray(self.cv_processed)
            self.display_image()
            
        except Exception as e:
            QMessageBox.critical(self, "处理错误", f"区域分割失败: {str(e)}")
    
    def update_histogram(self):
        """更新直方图显示"""
        if self.cv_processed is None:
            return
        
        # 清除之前的直方图
        self.histogram_canvas.axes.clear()
        
        # 转换为灰度图像进行直方图分析
        if len(self.cv_processed.shape) == 3:
            gray_image = cv2.cvtColor(self.cv_processed, cv2.COLOR_RGB2GRAY)
        else:
            gray_image = self.cv_processed
        
        # 计算直方图
        hist, bins = np.histogram(gray_image.flatten(), bins=256, range=(0, 255))
        
        # 绘制直方图
        self.histogram_canvas.axes.bar(bins[:-1], hist, width=1, edgecolor='none', alpha=0.7)
        self.histogram_canvas.axes.set_title('图像直方图')
        self.histogram_canvas.axes.set_xlabel('像素值')
        self.histogram_canvas.axes.set_ylabel('频率')
        self.histogram_canvas.axes.set_xlim(0, 255)
        
        # 刷新画布
        self.histogram_canvas.draw()
    
    def update_image_info(self):
        """更新图像信息"""
        if self.cv_original is None:
            self.info_text.setPlainText("没有加载图像")
            return
        
        info = f"图像信息:\n"
        info += f"尺寸: {self.cv_original.shape[1]} x {self.cv_original.shape[0]}\n"
        info += f"通道数: {self.cv_original.shape[2] if len(self.cv_original.shape) == 3 else 1}\n"
        info += f"数据类型: {self.cv_original.dtype}\n"
        
        # 计算统计信息
        if len(self.cv_original.shape) == 3:
            for i, channel in enumerate(['R', 'G', 'B']):
                info += f"\n{channel}通道:\n"
                info += f"  最小值: {np.min(self.cv_original[:, :, i])}\n"
                info += f"  最大值: {np.max(self.cv_original[:, :, i])}\n"
                info += f"  平均值: {np.mean(self.cv_original[:, :, i]):.2f}\n"
                info += f"  标准差: {np.std(self.cv_original[:, :, i]):.2f}\n"
        else:
            info += f"\n灰度通道:\n"
            info += f"  最小值: {np.min(self.cv_original)}\n"
            info += f"  最大值: {np.max(self.cv_original)}\n"
            info += f"  平均值: {np.mean(self.cv_original):.2f}\n"
            info += f"  标准差: {np.std(self.cv_original):.2f}\n"
        
        self.info_text.setPlainText(info)
    
    def resizeEvent(self, event):
        """处理窗口大小调整事件"""
        super().resizeEvent(event)
        self.display_image()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    analyzer = ImageAnalyzer()
    analyzer.show()
    sys.exit(app.exec_())