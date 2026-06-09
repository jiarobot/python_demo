import sys
import numpy as np
import cv2
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QGroupBox, QPushButton, QLabel, 
                            QSlider, QComboBox, QSpinBox, QDoubleSpinBox,
                            QFileDialog, QMessageBox, QSplitter, QScrollArea)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QPixmap, QImage, QFont
import matplotlib
matplotlib.rc("font", family='Microsoft YaHei')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


class OperatorLibrary:
    """算子库核心类，提供各种图像处理和数学运算功能"""
    
    @staticmethod
    def apply_gaussian_blur(image, kernel_size=5, sigma=1.0):
        """高斯模糊"""
        return cv2.GaussianBlur(image, (kernel_size, kernel_size), sigma)
    
    @staticmethod
    def apply_sobel_edge(image, direction='both'):
        """Sobel边缘检测"""
        if direction == 'x':
            return cv2.Sobel(image, cv2.CV_64F, 1, 0, ksize=3)
        elif direction == 'y':
            return cv2.Sobel(image, cv2.CV_64F, 0, 1, ksize=3)
        else:  # both
            sobelx = cv2.Sobel(image, cv2.CV_64F, 1, 0, ksize=3)
            sobely = cv2.Sobel(image, cv2.CV_64F, 0, 1, ksize=3)
            return cv2.magnitude(sobelx, sobely)
    
    @staticmethod
    def apply_canny_edge(image, threshold1=50, threshold2=150):
        """Canny边缘检测"""
        return cv2.Canny(image, threshold1, threshold2)
    
    @staticmethod
    def apply_median_blur(image, kernel_size=5):
        """中值滤波"""
        return cv2.medianBlur(image, kernel_size)
    
    @staticmethod
    def apply_bilateral_filter(image, d=9, sigma_color=75, sigma_space=75):
        """双边滤波"""
        return cv2.bilateralFilter(image, d, sigma_color, sigma_space)
    
    @staticmethod
    def apply_histogram_equalization(image):
        """直方图均衡化"""
        if len(image.shape) == 2:  # 灰度图
            return cv2.equalizeHist(image)
        else:  # 彩色图
            ycrcb = cv2.cvtColor(image, cv2.COLOR_BGR2YCrCb)
            ycrcb[:, :, 0] = cv2.equalizeHist(ycrcb[:, :, 0])
            return cv2.cvtColor(ycrcb, cv2.COLOR_YCrCb2BGR)
    
    @staticmethod
    def apply_morphology(image, operation='open', kernel_size=3):
        """形态学操作"""
        kernel = np.ones((kernel_size, kernel_size), np.uint8)
        if operation == 'open':
            return cv2.morphologyEx(image, cv2.MORPH_OPEN, kernel)
        elif operation == 'close':
            return cv2.morphologyEx(image, cv2.MORPH_CLOSE, kernel)
        elif operation == 'dilate':
            return cv2.dilate(image, kernel, iterations=1)
        elif operation == 'erode':
            return cv2.erode(image, kernel, iterations=1)
    
    @staticmethod
    def apply_threshold(image, threshold=127, max_value=255, method='binary'):
        """阈值处理"""
        if method == 'binary':
            _, result = cv2.threshold(image, threshold, max_value, cv2.THRESH_BINARY)
        elif method == 'binary_inv':
            _, result = cv2.threshold(image, threshold, max_value, cv2.THRESH_BINARY_INV)
        elif method == 'trunc':
            _, result = cv2.threshold(image, threshold, max_value, cv2.THRESH_TRUNC)
        elif method == 'tozero':
            _, result = cv2.threshold(image, threshold, max_value, cv2.THRESH_TOZERO)
        elif method == 'tozero_inv':
            _, result = cv2.threshold(image, threshold, max_value, cv2.THRESH_TOZERO_INV)
        elif method == 'otsu':
            _, result = cv2.threshold(image, 0, max_value, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        elif method == 'adaptive_mean':
            result = cv2.adaptiveThreshold(image, max_value, cv2.ADAPTIVE_THRESH_MEAN_C, 
                                          cv2.THRESH_BINARY, 11, 2)
        elif method == 'adaptive_gaussian':
            result = cv2.adaptiveThreshold(image, max_value, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                          cv2.THRESH_BINARY, 11, 2)
        return result
    
    @staticmethod
    def apply_laplacian(image):
        """拉普拉斯算子"""
        return cv2.Laplacian(image, cv2.CV_64F)
    
    @staticmethod
    def apply_scharr(image, direction='x'):
        """Scharr算子"""
        if direction == 'x':
            return cv2.Scharr(image, cv2.CV_64F, 1, 0)
        else:
            return cv2.Scharr(image, cv2.CV_64F, 0, 1)
    
    @staticmethod
    def apply_custom_kernel(image, kernel):
        """自定义卷积核"""
        return cv2.filter2D(image, -1, kernel)
    
    @staticmethod
    def create_custom_kernel(size=3, kernel_type='identity'):
        """创建自定义卷积核"""
        if kernel_type == 'identity':
            return np.eye(size, dtype=np.float32)
        elif kernel_type == 'sharpen':
            kernel = -np.ones((size, size), dtype=np.float32)
            kernel[size//2, size//2] = size*size
            return kernel
        elif kernel_type == 'edge_detect':
            kernel = -np.ones((size, size), dtype=np.float32)
            kernel[size//2, size//2] = size*size - 1
            return kernel
        elif kernel_type == 'gaussian':
            return OperatorLibrary._create_gaussian_kernel(size)
        elif kernel_type == 'box_blur':
            return np.ones((size, size), dtype=np.float32) / (size*size)
    
    @staticmethod
    def _create_gaussian_kernel(size, sigma=1.0):
        """创建高斯核"""
        ax = np.arange(-size // 2 + 1., size // 2 + 1.)
        xx, yy = np.meshgrid(ax, ax)
        kernel = np.exp(-(xx**2 + yy**2) / (2. * sigma**2))
        return kernel / np.sum(kernel)


class ImageDisplayWidget(QWidget):
    """图像显示组件"""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 图像显示标签
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setMinimumSize(400, 300)
        self.image_label.setText("请加载图像")
        self.image_label.setStyleSheet("border: 1px solid gray;")
        
        layout.addWidget(self.image_label)
        self.setLayout(layout)
    
    def display_image(self, image):
        """显示图像"""
        if image is None:
            return
            
        # 转换图像格式为QImage
        if len(image.shape) == 2:  # 灰度图
            h, w = image.shape
            bytes_per_line = w
            q_img = QImage(image.data, w, h, bytes_per_line, QImage.Format_Grayscale8)
        else:  # 彩色图
            h, w, ch = image.shape
            bytes_per_line = ch * w
            # OpenCV使用BGR，QImage使用RGB
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            q_img = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        
        # 缩放图像以适应显示区域
        pixmap = QPixmap.fromImage(q_img)
        scaled_pixmap = pixmap.scaled(self.image_label.width(), 
                                     self.image_label.height(),
                                     Qt.KeepAspectRatio, 
                                     Qt.SmoothTransformation)
        
        self.image_label.setPixmap(scaled_pixmap)


class OperatorControlPanel(QWidget):
    """算子控制面板"""
    
    operator_changed = pyqtSignal(dict)  # 信号：算子参数改变
    
    def __init__(self):
        super().__init__()
        self.current_operator = None
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 算子选择
        operator_group = QGroupBox("选择算子")
        operator_layout = QVBoxLayout()
        
        self.operator_combo = QComboBox()
        self.operator_combo.addItems([
            "高斯模糊", "Sobel边缘检测", "Canny边缘检测", "中值滤波", 
            "双边滤波", "直方图均衡化", "形态学操作", "阈值处理",
            "拉普拉斯算子", "Scharr算子", "自定义卷积核"
        ])
        self.operator_combo.currentTextChanged.connect(self.on_operator_changed)
        
        operator_layout.addWidget(QLabel("算子类型:"))
        operator_layout.addWidget(self.operator_combo)
        operator_group.setLayout(operator_layout)
        layout.addWidget(operator_group)
        
        # 参数控制区域
        self.param_group = QGroupBox("参数设置")
        self.param_layout = QVBoxLayout()
        self.param_group.setLayout(self.param_layout)
        layout.addWidget(self.param_group)
        
        # 应用按钮
        self.apply_button = QPushButton("应用算子")
        self.apply_button.clicked.connect(self.apply_operator)
        layout.addWidget(self.apply_button)
        
        layout.addStretch()
        self.setLayout(layout)
        
        # 初始化默认算子
        self.on_operator_changed(self.operator_combo.currentText())
    
    def on_operator_changed(self, operator_name):
        """当算子改变时更新参数控件"""
        self.current_operator = operator_name
        
        # 清空现有参数控件
        for i in reversed(range(self.param_layout.count())):
            self.param_layout.itemAt(i).widget().setParent(None)
        
        # 根据算子类型添加相应的参数控件
        if operator_name == "高斯模糊":
            self.add_slider_control("核大小", "kernel_size", 1, 15, 5, 2)
            self.add_double_spinbox_control("Sigma", "sigma", 0.1, 10.0, 1.0, 0.1)
            
        elif operator_name == "Sobel边缘检测":
            self.add_combo_control("方向", "direction", ["x", "y", "both"])
            
        elif operator_name == "Canny边缘检测":
            self.add_slider_control("阈值1", "threshold1", 0, 255, 50, 1)
            self.add_slider_control("阈值2", "threshold2", 0, 255, 150, 1)
            
        elif operator_name == "中值滤波":
            self.add_slider_control("核大小", "kernel_size", 1, 15, 5, 2)
            
        elif operator_name == "双边滤波":
            self.add_slider_control("直径", "d", 1, 15, 9, 2)
            self.add_slider_control("Sigma Color", "sigma_color", 1, 200, 75, 1)
            self.add_slider_control("Sigma Space", "sigma_space", 1, 200, 75, 1)
            
        elif operator_name == "形态学操作":
            self.add_combo_control("操作类型", "operation", 
                                  ["open", "close", "dilate", "erode"])
            self.add_slider_control("核大小", "kernel_size", 1, 15, 3, 2)
            
        elif operator_name == "阈值处理":
            self.add_combo_control("方法", "method", [
                "binary", "binary_inv", "trunc", "tozero", 
                "tozero_inv", "otsu", "adaptive_mean", "adaptive_gaussian"
            ])
            self.add_slider_control("阈值", "threshold", 0, 255, 127, 1)
            self.add_slider_control("最大值", "max_value", 0, 255, 255, 1)
            
        elif operator_name == "Scharr算子":
            self.add_combo_control("方向", "direction", ["x", "y"])
            
        elif operator_name == "自定义卷积核":
            self.add_combo_control("核类型", "kernel_type", [
                "identity", "sharpen", "edge_detect", "gaussian", "box_blur"
            ])
            self.add_slider_control("核大小", "kernel_size", 1, 15, 3, 2)
    
    def add_slider_control(self, label, param_name, min_val, max_val, default_val, step=1):
        """添加滑块控件"""
        widget = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        label_widget = QLabel(f"{label}:")
        value_label = QLabel(str(default_val))
        
        slider = QSlider(Qt.Horizontal)
        slider.setMinimum(min_val)
        slider.setMaximum(max_val)
        slider.setValue(default_val)
        slider.setSingleStep(step)
        
        # 连接信号
        def update_value(value):
            value_label.setText(str(value))
            setattr(self, f"{param_name}_value", value)
        
        slider.valueChanged.connect(update_value)
        setattr(self, f"{param_name}_value", default_val)
        setattr(self, f"{param_name}_slider", slider)
        setattr(self, f"{param_name}_label", value_label)
        
        layout.addWidget(label_widget)
        layout.addWidget(slider)
        layout.addWidget(value_label)
        widget.setLayout(layout)
        self.param_layout.addWidget(widget)
    
    def add_combo_control(self, label, param_name, items):
        """添加下拉框控件"""
        widget = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        label_widget = QLabel(f"{label}:")
        combo = QComboBox()
        combo.addItems(items)
        
        setattr(self, f"{param_name}_combo", combo)
        setattr(self, f"{param_name}_value", items[0])
        
        def update_value(index):
            value = combo.currentText()
            setattr(self, f"{param_name}_value", value)
        
        combo.currentTextChanged.connect(update_value)
        
        layout.addWidget(label_widget)
        layout.addWidget(combo)
        widget.setLayout(layout)
        self.param_layout.addWidget(widget)
    
    def add_double_spinbox_control(self, label, param_name, min_val, max_val, default_val, step=0.1):
        """添加双精度微调框控件"""
        widget = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        label_widget = QLabel(f"{label}:")
        spinbox = QDoubleSpinBox()
        spinbox.setMinimum(min_val)
        spinbox.setMaximum(max_val)
        spinbox.setValue(default_val)
        spinbox.setSingleStep(step)
        
        setattr(self, f"{param_name}_spinbox", spinbox)
        setattr(self, f"{param_name}_value", default_val)
        
        def update_value(value):
            setattr(self, f"{param_name}_value", value)
        
        spinbox.valueChanged.connect(update_value)
        
        layout.addWidget(label_widget)
        layout.addWidget(spinbox)
        widget.setLayout(layout)
        self.param_layout.addWidget(widget)
    
    def apply_operator(self):
        """应用算子并发射信号"""
        params = {
            'operator': self.current_operator,
        }
        
        # 根据当前算子收集参数
        if self.current_operator == "高斯模糊":
            params['kernel_size'] = self.kernel_size_value
            params['sigma'] = self.sigma_value
            
        elif self.current_operator == "Sobel边缘检测":
            params['direction'] = self.direction_value
            
        elif self.current_operator == "Canny边缘检测":
            params['threshold1'] = self.threshold1_value
            params['threshold2'] = self.threshold2_value
            
        elif self.current_operator == "中值滤波":
            params['kernel_size'] = self.kernel_size_value
            
        elif self.current_operator == "双边滤波":
            params['d'] = self.d_value
            params['sigma_color'] = self.sigma_color_value
            params['sigma_space'] = self.sigma_space_value
            
        elif self.current_operator == "形态学操作":
            params['operation'] = self.operation_value
            params['kernel_size'] = self.kernel_size_value
            
        elif self.current_operator == "阈值处理":
            params['method'] = self.method_value
            params['threshold'] = self.threshold_value
            params['max_value'] = self.max_value_value
            
        elif self.current_operator == "Scharr算子":
            params['direction'] = self.direction_value
            
        elif self.current_operator == "自定义卷积核":
            params['kernel_type'] = self.kernel_type_value
            params['kernel_size'] = self.kernel_size_value
        
        self.operator_changed.emit(params)


class PlotWidget(QWidget):
    """绘图组件，用于显示图像直方图等"""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        self.figure = Figure(figsize=(5, 4), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        
        layout.addWidget(self.canvas)
        self.setLayout(layout)
    
    def plot_histogram(self, image):
        """绘制图像直方图"""
        self.figure.clear()
        
        if len(image.shape) == 2:  # 灰度图
            ax = self.figure.add_subplot(111)
            ax.hist(image.ravel(), 256, [0, 256])
            ax.set_title('灰度直方图')
            ax.set_xlabel('像素值')
            ax.set_ylabel('频数')
        else:  # 彩色图
            colors = ('b', 'g', 'r')
            ax = self.figure.add_subplot(111)
            for i, color in enumerate(colors):
                hist = cv2.calcHist([image], [i], None, [256], [0, 256])
                ax.plot(hist, color=color)
                ax.set_xlim([0, 256])
            ax.set_title('彩色直方图')
            ax.set_xlabel('像素值')
            ax.set_ylabel('频数')
            ax.legend(['Blue', 'Green', 'Red'])
        
        self.canvas.draw()


class MainWindow(QMainWindow):
    """主窗口"""
    
    def __init__(self):
        super().__init__()
        self.original_image = None
        self.processed_image = None
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("PyQt 算子强大工具库")
        self.setGeometry(100, 100, 1200, 800)
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QHBoxLayout()
        central_widget.setLayout(main_layout)
        
        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        
        # 左侧：控制面板
        self.control_panel = OperatorControlPanel()
        self.control_panel.operator_changed.connect(self.apply_operator)
        
        # 右侧：图像显示和绘图区域
        right_widget = QWidget()
        right_layout = QVBoxLayout()
        
        # 图像显示区域
        image_splitter = QSplitter(Qt.Horizontal)
        
        self.original_display = ImageDisplayWidget()
        self.processed_display = ImageDisplayWidget()
        
        image_splitter.addWidget(self.original_display)
        image_splitter.addWidget(self.processed_display)
        image_splitter.setSizes([400, 400])
        
        right_layout.addWidget(image_splitter)
        
        # 绘图区域
        self.plot_widget = PlotWidget()
        right_layout.addWidget(self.plot_widget)
        
        right_widget.setLayout(right_layout)
        
        # 添加部件到分割器
        splitter.addWidget(self.control_panel)
        splitter.addWidget(right_widget)
        splitter.setSizes([300, 900])
        
        main_layout.addWidget(splitter)
        
        # 创建菜单栏
        self.create_menubar()
        
        # 状态栏
        self.statusBar().showMessage("就绪")
    
    def create_menubar(self):
        """创建菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu('文件')
        
        open_action = file_menu.addAction('打开图像')
        open_action.triggered.connect(self.open_image)
        
        save_action = file_menu.addAction('保存结果')
        save_action.triggered.connect(self.save_image)
        
        file_menu.addSeparator()
        
        exit_action = file_menu.addAction('退出')
        exit_action.triggered.connect(self.close)
        
        # 视图菜单
        view_menu = menubar.addMenu('视图')
        
        reset_view_action = view_menu.addAction('重置视图')
        reset_view_action.triggered.connect(self.reset_view)
    
    def open_image(self):
        """打开图像文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "打开图像", "", 
            "图像文件 (*.png *.jpg *.jpeg *.bmp *.tiff);;所有文件 (*)"
        )
        
        if file_path:
            # 读取图像
            self.original_image = cv2.imread(file_path)
            if self.original_image is None:
                QMessageBox.warning(self, "错误", "无法加载图像文件")
                return
            
            self.processed_image = self.original_image.copy()
            
            # 显示图像
            self.original_display.display_image(self.original_image)
            self.processed_display.display_image(self.processed_image)
            
            # 更新直方图
            self.plot_widget.plot_histogram(self.original_image)
            
            self.statusBar().showMessage(f"已加载图像: {file_path}")
    
    def save_image(self):
        """保存处理后的图像"""
        if self.processed_image is None:
            QMessageBox.warning(self, "警告", "没有可保存的图像")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存图像", "", 
            "PNG图像 (*.png);;JPEG图像 (*.jpg *.jpeg);;所有文件 (*)"
        )
        
        if file_path:
            success = cv2.imwrite(file_path, self.processed_image)
            if success:
                self.statusBar().showMessage(f"图像已保存: {file_path}")
            else:
                QMessageBox.warning(self, "错误", "保存图像失败")
    
    def reset_view(self):
        """重置视图"""
        if self.original_image is not None:
            self.processed_image = self.original_image.copy()
            self.processed_display.display_image(self.processed_image)
            self.plot_widget.plot_histogram(self.original_image)
            self.statusBar().showMessage("视图已重置")
    
    def apply_operator(self, params):
        """应用选择的算子"""
        if self.original_image is None:
            QMessageBox.warning(self, "警告", "请先加载图像")
            return
        
        try:
            operator_name = params['operator']
            
            # 根据算子类型应用不同的处理
            if operator_name == "高斯模糊":
                result = OperatorLibrary.apply_gaussian_blur(
                    self.original_image, 
                    params.get('kernel_size', 5),
                    params.get('sigma', 1.0)
                )
                
            elif operator_name == "Sobel边缘检测":
                result = OperatorLibrary.apply_sobel_edge(
                    self.original_image,
                    params.get('direction', 'both')
                )
                # 转换为8位无符号整数用于显示
                result = np.uint8(np.absolute(result))
                
            elif operator_name == "Canny边缘检测":
                result = OperatorLibrary.apply_canny_edge(
                    self.original_image,
                    params.get('threshold1', 50),
                    params.get('threshold2', 150)
                )
                
            elif operator_name == "中值滤波":
                result = OperatorLibrary.apply_median_blur(
                    self.original_image,
                    params.get('kernel_size', 5)
                )
                
            elif operator_name == "双边滤波":
                result = OperatorLibrary.apply_bilateral_filter(
                    self.original_image,
                    params.get('d', 9),
                    params.get('sigma_color', 75),
                    params.get('sigma_space', 75)
                )
                
            elif operator_name == "直方图均衡化":
                result = OperatorLibrary.apply_histogram_equalization(
                    self.original_image
                )
                
            elif operator_name == "形态学操作":
                result = OperatorLibrary.apply_morphology(
                    self.original_image,
                    params.get('operation', 'open'),
                    params.get('kernel_size', 3)
                )
                
            elif operator_name == "阈值处理":
                # 阈值处理需要灰度图像
                if len(self.original_image.shape) == 3:
                    gray_image = cv2.cvtColor(self.original_image, cv2.COLOR_BGR2GRAY)
                else:
                    gray_image = self.original_image
                
                result = OperatorLibrary.apply_threshold(
                    gray_image,
                    params.get('threshold', 127),
                    params.get('max_value', 255),
                    params.get('method', 'binary')
                )
                
            elif operator_name == "拉普拉斯算子":
                result = OperatorLibrary.apply_laplacian(self.original_image)
                result = np.uint8(np.absolute(result))
                
            elif operator_name == "Scharr算子":
                result = OperatorLibrary.apply_scharr(
                    self.original_image,
                    params.get('direction', 'x')
                )
                result = np.uint8(np.absolute(result))
                
            elif operator_name == "自定义卷积核":
                kernel = OperatorLibrary.create_custom_kernel(
                    params.get('kernel_size', 3),
                    params.get('kernel_type', 'identity')
                )
                result = OperatorLibrary.apply_custom_kernel(self.original_image, kernel)
            
            # 更新处理后的图像
            self.processed_image = result
            self.processed_display.display_image(self.processed_image)
            
            # 更新直方图
            self.plot_widget.plot_histogram(self.processed_image)
            
            self.statusBar().showMessage(f"已应用算子: {operator_name}")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"应用算子时发生错误: {str(e)}")


def main():
    app = QApplication(sys.argv)
    
    # 设置应用程序样式
    app.setStyle('Fusion')
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()