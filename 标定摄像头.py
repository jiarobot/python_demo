import sys
import os
import cv2
import numpy as np
import json
import matplotlib
matplotlib.rc("font", family='Microsoft YaHei')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from datetime import datetime
from scipy.optimize import least_squares
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QLabel, QPushButton, 
                             QVBoxLayout, QHBoxLayout, QGroupBox, QFileDialog, QMessageBox,
                             QSpinBox, QDoubleSpinBox, QListWidget, QTabWidget, QSplitter,
                             QSizePolicy, QProgressBar, QAction, QToolBar, QStatusBar,
                             QComboBox, QCheckBox, QSlider, QRadioButton, QButtonGroup,
                             QGridLayout, QTextEdit, QDockWidget, QTreeWidget, QTreeWidgetItem)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread, QSize
from PyQt5.QtGui import QCursor, QImage, QPainter, QPixmap, QIcon, QFont, QPalette, QColor

class CalibrationWorker(QThread):
    """标定工作线程，避免界面冻结"""
    finished = pyqtSignal(bool, str, object)
    progress = pyqtSignal(int)
    
    def __init__(self, calibration, obj_points, img_points, image_size, flags):
        super().__init__()
        self.calibration = calibration
        self.obj_points = obj_points
        self.img_points = img_points
        self.image_size = image_size
        self.flags = flags
        
    def run(self):
        try:
            # 执行标定
            ret, camera_matrix, dist_coeffs, rvecs, tvecs = cv2.calibrateCamera(
                self.obj_points, self.img_points, self.image_size, None, None, 
                flags=self.flags
            )
            
            # 计算重投影误差
            total_error = 0
            errors = []
            for i in range(len(self.obj_points)):
                imgpoints2, _ = cv2.projectPoints(
                    self.obj_points[i], rvecs[i], tvecs[i], camera_matrix, dist_coeffs
                )
                error = cv2.norm(self.img_points[i], imgpoints2, cv2.NORM_L2) / len(imgpoints2)
                total_error += error
                errors.append(error)
                
            reprojection_error = total_error / len(self.obj_points)
            
            # 优化参数（可选）
            if self.calibration.optimize_params:
                self.progress.emit(50)
                optimized_params = self.optimize_calibration(
                    camera_matrix, dist_coeffs, rvecs, tvecs, self.obj_points, self.img_points
                )
                camera_matrix = optimized_params['camera_matrix']
                dist_coeffs = optimized_params['dist_coeffs']
                reprojection_error = optimized_params['error']
            
            self.progress.emit(100)
            self.finished.emit(True, "标定成功", {
                'camera_matrix': camera_matrix,
                'dist_coeffs': dist_coeffs,
                'reprojection_error': reprojection_error,
                'rvecs': rvecs,
                'tvecs': tvecs,
                'errors': errors
            })
            
        except Exception as e:
            self.finished.emit(False, f"标定失败: {str(e)}", None)
    
    def optimize_calibration(self, camera_matrix, dist_coeffs, rvecs, tvecs, obj_points, img_points):
        """使用非线性优化进一步优化标定参数"""
        # 将参数扁平化
        init_params = self.params_to_vector(camera_matrix, dist_coeffs, rvecs, tvecs)
        
        # 定义误差函数
        def error_function(params):
            cam_matrix, dist, rvecs_opt, tvecs_opt = self.vector_to_params(
                params, camera_matrix.shape, dist_coeffs.shape, len(obj_points)
            )
            
            total_error = 0
            for i in range(len(obj_points)):
                img_points_proj, _ = cv2.projectPoints(
                    obj_points[i], rvecs_opt[i], tvecs_opt[i], cam_matrix, dist
                )
                error = np.sum((img_points[i] - img_points_proj) ** 2)
                total_error += error
                
            return total_error
        
        # 执行优化
        result = least_squares(error_function, init_params, verbose=0, max_nfev=20)
        
        # 提取优化后的参数
        cam_matrix_opt, dist_opt, rvecs_opt, tvecs_opt = self.vector_to_params(
            result.x, camera_matrix.shape, dist_coeffs.shape, len(obj_points)
        )
        
        # 计算最终误差
        final_error = error_function(result.x) / sum(len(pts) for pts in img_points)
        
        return {
            'camera_matrix': cam_matrix_opt,
            'dist_coeffs': dist_opt,
            'error': final_error,
            'rvecs': rvecs_opt,
            'tvecs': tvecs_opt
        }
    
    def params_to_vector(self, camera_matrix, dist_coeffs, rvecs, tvecs):
        """将参数转换为扁平向量"""
        params = []
        
        # 相机内参 (3x3)
        params.extend(camera_matrix.flatten())
        
        # 畸变系数
        params.extend(dist_coeffs.flatten())
        
        # 旋转和平移向量
        for i in range(len(rvecs)):
            params.extend(rvecs[i].flatten())
            params.extend(tvecs[i].flatten())
            
        return np.array(params)
    
    def vector_to_params(self, vector, cam_shape, dist_shape, num_views):
        """从向量中恢复参数"""
        idx = 0
        
        # 相机内参
        cam_matrix = vector[idx:idx+9].reshape(cam_shape)
        idx += 9
        
        # 畸变系数
        dist = vector[idx:idx+np.prod(dist_shape)].reshape(dist_shape)
        idx += np.prod(dist_shape)
        
        # 旋转和平移向量
        rvecs = []
        tvecs = []
        for i in range(num_views):
            rvec = vector[idx:idx+3].reshape(3, 1)
            idx += 3
            tvec = vector[idx:idx+3].reshape(3, 1)
            idx += 3
            rvecs.append(rvec)
            tvecs.append(tvec)
            
        return cam_matrix, dist, rvecs, tvecs

class CameraCalibration:
    """增强版相机标定类"""
    def __init__(self):
        self.camera_matrix = None
        self.dist_coeffs = None
        self.calibration_flags = 0
        self.criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
        self.obj_points = []  # 3D点
        self.img_points = []  # 2D点
        self.image_size = None
        self.calibrated = False
        self.reprojection_error = 0.0
        self.rvecs = []
        self.tvecs = []
        self.errors = []
        self.optimize_params = True
        self.calibration_pattern = "chessboard"  # 标定板类型
        self.pattern_sizes = {
            "chessboard": (9, 6),
            "circles": (10, 7),
            "asymmetric_circles": (5, 4)
        }
        
    def set_calibration_flags(self, flags):
        self.calibration_flags = flags
        
    def set_pattern_type(self, pattern_type):
        """设置标定板类型"""
        self.calibration_pattern = pattern_type
        
    def set_optimization(self, optimize):
        """设置是否优化参数"""
        self.optimize_params = optimize
        
    def add_points(self, image, pattern_size):
        """检测角点并添加到数据集中"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        self.image_size = gray.shape[::-1]
        
        # 准备对象点
        objp = np.zeros((pattern_size[0] * pattern_size[1], 3), np.float32)
        objp[:, :2] = np.mgrid[0:pattern_size[0], 0:pattern_size[1]].T.reshape(-1, 2)
        
        # 根据标定板类型查找角点
        ret = False
        points = None
        
        if self.calibration_pattern == "chessboard":
            ret, corners = cv2.findChessboardCorners(gray, pattern_size, 
                cv2.CALIB_CB_ADAPTIVE_THRESH + cv2.CALIB_CB_NORMALIZE_IMAGE + cv2.CALIB_CB_FAST_CHECK)
            if ret:
                corners_refined = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), self.criteria)
                points = corners_refined
                
        elif self.calibration_pattern == "circles":
            ret, centers = cv2.findCirclesGrid(gray, pattern_size, None, cv2.CALIB_CB_SYMMETRIC_GRID)
            if ret:
                points = centers
                
        elif self.calibration_pattern == "asymmetric_circles":
            ret, centers = cv2.findCirclesGrid(gray, pattern_size, None, cv2.CALIB_CB_ASYMMETRIC_GRID)
            if ret:
                points = centers
        
        if ret:
            self.obj_points.append(objp)
            self.img_points.append(points)
            return True, points
            
        return False, None
    
    def calibrate(self):
        """执行相机标定（使用工作线程）"""
        if len(self.obj_points) < 5:
            return False, "至少需要5张图像进行标定"
            
        # 创建工作线程
        self.worker = CalibrationWorker(
            self, self.obj_points, self.img_points, self.image_size, self.calibration_flags
        )
        return self.worker
    
    def undistort(self, image, crop=True):
        """校正图像畸变"""
        if not self.calibrated:
            return image
            
        h, w = image.shape[:2]
        new_camera_matrix, roi = cv2.getOptimalNewCameraMatrix(
            self.camera_matrix, self.dist_coeffs, (w, h), 1, (w, h)
        )
        dst = cv2.undistort(image, self.camera_matrix, self.dist_coeffs, None, new_camera_matrix)
        
        if crop:
            x, y, w, h = roi
            dst = dst[y:y+h, x:x+w]
            
        return dst
    
    def save_parameters(self, filename):
        """保存相机参数到文件"""
        if not self.calibrated:
            return False
            
        data = {
            "camera_matrix": self.camera_matrix.tolist(),
            "dist_coeffs": self.dist_coeffs.tolist(),
            "image_size": self.image_size,
            "reprojection_error": self.reprojection_error,
            "calibration_date": datetime.now().isoformat(),
            "calibration_pattern": self.calibration_pattern,
            "rvecs": [rvec.tolist() for rvec in self.rvecs],
            "tvecs": [tvec.tolist() for tvec in self.tvecs],
            "per_view_errors": self.errors
        }
        
        try:
            with open(filename, 'w') as f:
                json.dump(data, f, indent=4)
            return True
        except Exception as e:
            return False
    
    def load_parameters(self, filename):
        """从文件加载相机参数"""
        try:
            with open(filename, 'r') as f:
                data = json.load(f)
                
            self.camera_matrix = np.array(data["camera_matrix"])
            self.dist_coeffs = np.array(data["dist_coeffs"])
            self.image_size = tuple(data["image_size"])
            self.reprojection_error = data["reprojection_error"]
            self.calibration_pattern = data.get("calibration_pattern", "chessboard")
            self.rvecs = [np.array(rvec) for rvec in data.get("rvecs", [])]
            self.tvecs = [np.array(tvec) for tvec in data.get("tvecs", [])]
            self.errors = data.get("per_view_errors", [])
            self.calibrated = True
            return True
        except Exception as e:
            return False

class MplCanvas(FigureCanvas):
    """Matplotlib画布"""
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_subplot(111)
        super().__init__(self.fig)
        self.setParent(parent)
        
    def plot_errors(self, errors):
        """绘制误差分布图"""
        self.axes.clear()
        self.axes.bar(range(len(errors)), errors)
        self.axes.set_xlabel('图像索引')
        self.axes.set_ylabel('重投影误差 (像素)')
        self.axes.set_title('每幅图像的重投影误差')
        self.fig.tight_layout()
        self.draw()

class ImageViewer(QLabel):
    """增强版图像显示组件"""
    def __init__(self):
        super().__init__()
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumSize(640, 480)
        self.setText("无图像")
        self.setStyleSheet("border: 1px solid gray;")
        self.zoom_factor = 1.0
        self.pan_start = None
        self.pan_offset = [0, 0]
        
    def set_image(self, image):
        """设置显示的图像"""
        if image is None:
            self.setText("无图像")
            self.current_image = None
            return
            
        self.current_image = image
        self.update_display()
        
    def update_display(self):
        """更新显示图像"""
        if self.current_image is None:
            return
            
        h, w, ch = self.current_image.shape
        bytes_per_line = ch * w
        qt_image = QImage(self.current_image.data, w, h, bytes_per_line, QImage.Format_RGB888).rgbSwapped()
        
        # 应用缩放和平移
        if self.zoom_factor != 1.0:
            new_w = int(w * self.zoom_factor)
            new_h = int(h * self.zoom_factor)
            scaled_pixmap = QPixmap.fromImage(qt_image).scaled(
                new_w, new_h, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            
            # 应用平移
            if self.pan_offset != [0, 0]:
                # 创建一个更大的画布来容纳平移后的图像
                canvas = QPixmap(self.width(), self.height())
                canvas.fill(Qt.transparent)
                painter = QPainter(canvas)
                painter.drawPixmap(self.pan_offset[0], self.pan_offset[1], scaled_pixmap)
                painter.end()
                self.setPixmap(canvas)
            else:
                self.setPixmap(scaled_pixmap)
        else:
            self.setPixmap(QPixmap.fromImage(qt_image).scaled(
                self.width(), self.height(), Qt.KeepAspectRatio, Qt.SmoothTransformation
            ))
    
    def wheelEvent(self, event):
        """鼠标滚轮事件实现缩放"""
        zoom_in_factor = 1.25
        zoom_out_factor = 1 / zoom_in_factor
        
        # 保存旧的中心点
        old_pos = self.mapFromGlobal(QCursor.pos())
        old_x = old_pos.x()
        old_y = old_pos.y()
        
        # 计算旧的中心点在图像上的比例
        if self.pixmap():
            pixmap_size = self.pixmap().size()
            old_x_ratio = old_x / pixmap_size.width() if pixmap_size.width() > 0 else 0
            old_y_ratio = old_y / pixmap_size.height() if pixmap_size.height() > 0 else 0
            
            # 应用缩放
            if event.angleDelta().y() > 0:
                self.zoom_factor *= zoom_in_factor
            else:
                self.zoom_factor *= zoom_out_factor
                
            # 限制缩放范围
            self.zoom_factor = max(0.1, min(5.0, self.zoom_factor))
            
            # 更新显示
            self.update_display()
            
            # 计算新的中心点位置
            if self.pixmap():
                new_pixmap_size = self.pixmap().size()
                new_x = old_x_ratio * new_pixmap_size.width()
                new_y = old_y_ratio * new_pixmap_size.height()
                
                # 调整平移偏移量以保持缩放中心
                self.pan_offset[0] += (old_x - new_x)
                self.pan_offset[1] += (old_y - new_y)
                
            self.update_display()
    
    def mousePressEvent(self, event):
        """鼠标按下事件开始平移"""
        if event.button() == Qt.LeftButton and self.zoom_factor != 1.0:
            self.pan_start = event.pos()
            
    def mouseMoveEvent(self, event):
        """鼠标移动事件处理平移"""
        if self.pan_start is not None:
            delta = event.pos() - self.pan_start
            self.pan_offset[0] += delta.x()
            self.pan_offset[1] += delta.y()
            self.pan_start = event.pos()
            self.update_display()
            
    def mouseReleaseEvent(self, event):
        """鼠标释放事件结束平移"""
        if event.button() == Qt.LeftButton:
            self.pan_start = None
            
    def reset_view(self):
        """重置视图"""
        self.zoom_factor = 1.0
        self.pan_offset = [0, 0]
        self.update_display()

class CameraCalibrationApp(QMainWindow):
    """增强版主应用程序窗口"""
    def __init__(self):
        super().__init__()
        self.calibrations = {}  # 多相机标定数据
        self.current_camera = "Camera 0"  # 当前选中的相机
        self.calibration = CameraCalibration()  # 当前相机的标定对象
        self.calibrations[self.current_camera] = self.calibration
        
        self.current_image = None
        self.captured_images = {}
        self.captured_images[self.current_camera] = []
        
        self.pattern_size = (9, 6)  # 棋盘格内角点数量
        self.cell_size = 25.0  # 棋盘格方格大小（毫米）
        
        self.init_ui()
        self.init_camera()
        
    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("高级相机标定工具 - 专业版")
        self.setGeometry(100, 100, 1400, 900)
        
        # 设置应用程序样式
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2D2D30;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #3E3E42;
                border-radius: 4px;
                margin-top: 1ex;
                padding-top: 10px;
                background-color: #252526;
                color: #CCCCCC;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 5px;
            }
            QPushButton {
                background-color: #0E639C;
                color: white;
                border: none;
                padding: 5px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #1177BB;
            }
            QPushButton:disabled {
                background-color: #5A5A5A;
                color: #969696;
            }
            QListWidget {
                background-color: #1E1E1E;
                color: #CCCCCC;
                border: 1px solid #3E3E42;
                border-radius: 4px;
            }
            QLabel {
                color: #CCCCCC;
            }
            QSpinBox, QDoubleSpinBox, QComboBox {
                background-color: #3C3C3C;
                color: #CCCCCC;
                border: 1px solid #3E3E42;
                border-radius: 3px;
                padding: 3px;
            }
            QTabWidget::pane {
                border: 1px solid #3E3E42;
                background-color: #252526;
            }
            QTabBar::tab {
                background-color: #2D2D30;
                color: #CCCCCC;
                padding: 8px 12px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background-color: #007ACC;
                color: white;
            }
        """)
        
        # 创建中心部件和主布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # 创建左侧控制面板
        control_panel = QWidget()
        control_panel.setMaximumWidth(350)
        control_layout = QVBoxLayout(control_panel)
        
        # 相机选择组
        camera_select_group = QGroupBox("相机选择")
        camera_select_layout = QVBoxLayout(camera_select_group)
        
        self.camera_combo = QComboBox()
        self.camera_combo.addItem("Camera 0")
        self.camera_combo.currentTextChanged.connect(self.change_camera)
        camera_select_layout.addWidget(self.camera_combo)
        
        add_camera_btn = QPushButton("添加新相机")
        add_camera_btn.clicked.connect(self.add_camera)
        camera_select_layout.addWidget(add_camera_btn)
        
        remove_camera_btn = QPushButton("移除当前相机")
        remove_camera_btn.clicked.connect(self.remove_camera)
        camera_select_layout.addWidget(remove_camera_btn)
        
        control_layout.addWidget(camera_select_group)
        
        # 相机控制组
        camera_group = QGroupBox("相机控制")
        camera_layout = QVBoxLayout(camera_group)
        
        self.capture_btn = QPushButton("捕获图像")
        self.capture_btn.clicked.connect(self.capture_image)
        camera_layout.addWidget(self.capture_btn)
        
        self.calibrate_btn = QPushButton("执行标定")
        self.calibrate_btn.clicked.connect(self.calibrate_camera)
        self.calibrate_btn.setEnabled(False)
        camera_layout.addWidget(self.calibrate_btn)
        
        self.undistort_btn = QPushButton("畸变校正")
        self.undistort_btn.clicked.connect(self.toggle_undistort)
        self.undistort_btn.setEnabled(False)
        camera_layout.addWidget(self.undistort_btn)
        
        control_layout.addWidget(camera_group)
        
        # 参数设置组
        params_group = QGroupBox("标定参数")
        params_layout = QVBoxLayout(params_group)
        
        # 标定板类型选择
        pattern_type_layout = QHBoxLayout()
        pattern_type_layout.addWidget(QLabel("标定板类型:"))
        self.pattern_combo = QComboBox()
        self.pattern_combo.addItems(["chessboard", "circles", "asymmetric_circles"])
        self.pattern_combo.currentTextChanged.connect(self.change_pattern_type)
        pattern_type_layout.addWidget(self.pattern_combo)
        params_layout.addLayout(pattern_type_layout)
        
        pattern_layout = QHBoxLayout()
        pattern_layout.addWidget(QLabel("标定板尺寸:"))
        self.pattern_width = QSpinBox()
        self.pattern_width.setRange(2, 15)
        self.pattern_width.setValue(self.pattern_size[0])
        self.pattern_width.valueChanged.connect(self.update_pattern_size)
        pattern_layout.addWidget(self.pattern_width)
        
        self.pattern_height = QSpinBox()
        self.pattern_height.setRange(2, 15)
        self.pattern_height.setValue(self.pattern_size[1])
        self.pattern_height.valueChanged.connect(self.update_pattern_size)
        pattern_layout.addWidget(self.pattern_height)
        params_layout.addLayout(pattern_layout)
        
        cell_layout = QHBoxLayout()
        cell_layout.addWidget(QLabel("方格大小 (mm):"))
        self.cell_size_spin = QDoubleSpinBox()
        self.cell_size_spin.setRange(1.0, 100.0)
        self.cell_size_spin.setValue(self.cell_size)
        self.cell_size_spin.valueChanged.connect(self.update_cell_size)
        cell_layout.addWidget(self.cell_size_spin)
        params_layout.addLayout(cell_layout)
        
        # 标定选项
        self.optimize_check = QCheckBox("优化标定参数")
        self.optimize_check.setChecked(True)
        self.optimize_check.stateChanged.connect(self.toggle_optimization)
        params_layout.addWidget(self.optimize_check)
        
        # 畸变系数选项
        dist_coeffs_group = QGroupBox("畸变系数")
        dist_layout = QGridLayout(dist_coeffs_group)
        
        self.k1_check = QCheckBox("k1")
        self.k1_check.setChecked(True)
        dist_layout.addWidget(self.k1_check, 0, 0)
        
        self.k2_check = QCheckBox("k2")
        self.k2_check.setChecked(True)
        dist_layout.addWidget(self.k2_check, 0, 1)
        
        self.k3_check = QCheckBox("k3")
        self.k3_check.setChecked(False)
        dist_layout.addWidget(self.k3_check, 1, 0)
        
        self.p1_check = QCheckBox("p1")
        self.p1_check.setChecked(True)
        dist_layout.addWidget(self.p1_check, 1, 1)
        
        self.p2_check = QCheckBox("p2")
        self.p2_check.setChecked(True)
        dist_layout.addWidget(self.p2_check, 2, 0)
        
        params_layout.addWidget(dist_coeffs_group)
        
        control_layout.addWidget(params_group)
        
        # 图像列表组
        images_group = QGroupBox("已捕获图像")
        images_layout = QVBoxLayout(images_group)
        
        self.images_list = QListWidget()
        self.images_list.currentRowChanged.connect(self.select_image)
        images_layout.addWidget(self.images_list)
        
        self.remove_image_btn = QPushButton("移除选中图像")
        self.remove_image_btn.clicked.connect(self.remove_image)
        images_layout.addWidget(self.remove_image_btn)
        
        control_layout.addWidget(images_group)
        
        # 标定结果组
        results_group = QGroupBox("标定结果")
        results_layout = QVBoxLayout(results_group)
        
        self.reprojection_label = QLabel("重投影误差: N/A")
        results_layout.addWidget(self.reprojection_label)
        
        self.show_errors_btn = QPushButton("显示误差分布")
        self.show_errors_btn.clicked.connect(self.show_error_plot)
        self.show_errors_btn.setEnabled(False)
        results_layout.addWidget(self.show_errors_btn)
        
        self.save_params_btn = QPushButton("保存参数")
        self.save_params_btn.clicked.connect(self.save_parameters)
        self.save_params_btn.setEnabled(False)
        results_layout.addWidget(self.save_params_btn)
        
        self.load_params_btn = QPushButton("加载参数")
        self.load_params_btn.clicked.connect(self.load_parameters)
        results_layout.addWidget(self.load_params_btn)
        
        control_layout.addWidget(results_group)
        control_layout.addStretch()
        
        # 创建右侧图像显示区域
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # 创建标签页
        self.tabs = QTabWidget()
        
        # 实时预览标签页
        preview_tab = QWidget()
        preview_layout = QVBoxLayout(preview_tab)
        self.image_viewer = ImageViewer()
        preview_layout.addWidget(self.image_viewer)
        
        # 添加视图控制按钮
        view_controls = QHBoxLayout()
        self.zoom_in_btn = QPushButton("放大")
        self.zoom_in_btn.clicked.connect(self.zoom_in)
        view_controls.addWidget(self.zoom_in_btn)
        
        self.zoom_out_btn = QPushButton("缩小")
        self.zoom_out_btn.clicked.connect(self.zoom_out)
        view_controls.addWidget(self.zoom_out_btn)
        
        self.reset_view_btn = QPushButton("重置视图")
        self.reset_view_btn.clicked.connect(self.reset_view)
        view_controls.addWidget(self.reset_view_btn)
        
        preview_layout.addLayout(view_controls)
        
        # 3D可视化标签页
        vis_3d_tab = QWidget()
        vis_3d_layout = QVBoxLayout(vis_3d_tab)
        self.canvas_3d = MplCanvas(self, width=5, height=4, dpi=100)
        vis_3d_layout.addWidget(self.canvas_3d)
        
        # 添加标签页
        self.tabs.addTab(preview_tab, "实时预览")
        self.tabs.addTab(vis_3d_tab, "3D可视化")
        
        right_layout.addWidget(self.tabs)
        
        # 添加到主布局
        main_layout.addWidget(control_panel)
        main_layout.addWidget(right_panel)
        
        # 创建状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        self.status_label = QLabel("就绪")
        self.status_bar.addWidget(self.status_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(200)
        self.progress_bar.setVisible(False)
        self.status_bar.addWidget(self.progress_bar)
        
        # 创建工具栏
        self.create_toolbar()
        
        # 初始化变量
        self.undistort_mode = False
        
    def create_toolbar(self):
        """创建工具栏"""
        toolbar = QToolBar("主工具栏")
        toolbar.setIconSize(QSize(16, 16))
        self.addToolBar(toolbar)
        
        # 添加动作
        open_action = QAction(QIcon("icons/open.png"), "打开图像", self)
        open_action.triggered.connect(self.open_image)
        toolbar.addAction(open_action)
        
        capture_action = QAction(QIcon("icons/capture.png"), "捕获", self)
        capture_action.triggered.connect(self.capture_image)
        toolbar.addAction(capture_action)
        
        toolbar.addSeparator()
        
        save_action = QAction(QIcon("icons/save.png"), "保存参数", self)
        save_action.triggered.connect(self.save_parameters)
        toolbar.addAction(save_action)
        
        load_action = QAction(QIcon("icons/load.png"), "加载参数", self)
        load_action.triggered.connect(self.load_parameters)
        toolbar.addAction(load_action)
        
        toolbar.addSeparator()
        
        undistort_action = QAction(QIcon("icons/undistort.png"), "畸变校正", self)
        undistort_action.triggered.connect(self.toggle_undistort)
        toolbar.addAction(undistort_action)
        
    def init_camera(self):
        """初始化相机"""
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            QMessageBox.warning(self, "警告", "无法打开相机")
            return
            
        # 设置相机参数
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        self.cap.set(cv2.CAP_PROP_FPS, 30)
        
        # 创建定时器用于实时预览
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)  # 约30fps
        
    def update_frame(self):
        """更新相机帧"""
        ret, frame = self.cap.read()
        if ret:
            self.current_image = frame.copy()
            
            # 如果处于畸变校正模式且已标定
            display_image = frame
            if self.undistort_mode and self.calibration.calibrated:
                display_image = self.calibration.undistort(frame)
            
            # 检测并绘制角点
            success, corners = self.calibration.add_points(frame, self.pattern_size)
            
            if success:
                if self.calibration.calibration_pattern == "chessboard":
                    cv2.drawChessboardCorners(display_image, self.pattern_size, corners, success)
                else:
                    cv2.drawChessboardCorners(display_image, self.pattern_size, corners, success)
                
            # 显示图像
            self.image_viewer.set_image(display_image)
            
    def capture_image(self):
        """捕获当前帧用于标定"""
        if self.current_image is None:
            return
            
        # 检测角点
        success, corners = self.calibration.add_points(self.current_image, self.pattern_size)
        
        if success:
            # 添加图像到列表
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.captured_images[self.current_camera].append(self.current_image.copy())
            self.images_list.addItem(f"图像 {len(self.captured_images[self.current_camera])} - {timestamp}")
            
            # 启用标定按钮（如果有足够图像）
            if len(self.captured_images[self.current_camera]) >= 5:
                self.calibrate_btn.setEnabled(True)
                
            self.status_label.setText(f"已捕获图像 {len(self.captured_images[self.current_camera])}")
        else:
            QMessageBox.warning(self, "警告", "未检测到标定板角点")
            
    def select_image(self, index):
        """选择列表中的图像"""
        if 0 <= index < len(self.captured_images[self.current_camera]):
            self.image_viewer.set_image(self.captured_images[self.current_camera][index])
            
    def remove_image(self):
        """移除选中的图像"""
        current_row = self.images_list.currentRow()
        if current_row >= 0:
            self.images_list.takeItem(current_row)
            self.captured_images[self.current_camera].pop(current_row)
            self.calibration.obj_points.pop(current_row)
            self.calibration.img_points.pop(current_row)
            
            # 更新标定按钮状态
            self.calibrate_btn.setEnabled(len(self.captured_images[self.current_camera]) >= 5)
            
    def calibrate_camera(self):
        """执行相机标定"""
        # 设置标定标志
        flags = 0
        if not self.k1_check.isChecked(): flags |= cv2.CALIB_ZERO_TANGENT_DIST
        if not self.k2_check.isChecked(): flags |= cv2.CALIB_FIX_K1
        if not self.k3_check.isChecked(): flags |= cv2.CALIB_FIX_K2
        if not self.p1_check.isChecked(): flags |= cv2.CALIB_FIX_K3
        if not self.p2_check.isChecked(): flags |= cv2.CALIB_FIX_K4 | cv2.CALIB_FIX_K5 | cv2.CALIB_FIX_K6
        
        self.calibration.set_calibration_flags(flags)
        
        # 显示进度条
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.calibrate_btn.setEnabled(False)
        
        # 开始标定
        worker = self.calibration.calibrate()
        if worker:
            worker.finished.connect(self.on_calibration_finished)
            worker.progress.connect(self.progress_bar.setValue)
            worker.start()
            
    def on_calibration_finished(self, success, message, results):
        """标定完成回调"""
        self.progress_bar.setVisible(False)
        
        if success:
            self.calibration.camera_matrix = results['camera_matrix']
            self.calibration.dist_coeffs = results['dist_coeffs']
            self.calibration.reprojection_error = results['reprojection_error']
            self.calibration.rvecs = results['rvecs']
            self.calibration.tvecs = results['tvecs']
            self.calibration.errors = results['errors']
            self.calibration.calibrated = True
            
            self.status_label.setText(f"标定成功，重投影误差: {self.calibration.reprojection_error:.6f}")
            self.reprojection_label.setText(f"重投影误差: {self.calibration.reprojection_error:.6f}")
            self.undistort_btn.setEnabled(True)
            self.save_params_btn.setEnabled(True)
            self.show_errors_btn.setEnabled(True)
            
            # 更新3D可视化
            self.update_3d_visualization()
            
            # 显示相机矩阵
            QMessageBox.information(self, "成功", 
                                   f"标定完成!\n重投影误差: {self.calibration.reprojection_error:.6f}\n\n"
                                   f"相机矩阵:\n{self.calibration.camera_matrix}\n\n"
                                   f"畸变系数:\n{self.calibration.dist_coeffs}")
        else:
            QMessageBox.critical(self, "错误", message)
            self.calibrate_btn.setEnabled(True)
            
    def update_3d_visualization(self):
        """更新3D可视化"""
        if not self.calibration.calibrated:
            return
            
        # 创建3D坐标系
        self.canvas_3d.axes.clear()
        
        # 绘制相机位置
        for i, (rvec, tvec) in enumerate(zip(self.calibration.rvecs, self.calibration.tvecs)):
            # 将旋转向量转换为旋转矩阵
            R, _ = cv2.Rodrigues(rvec)
            
            # 相机坐标系的三轴
            axis_length = 0.5
            axis_points = np.float32([[0, 0, 0], [axis_length, 0, 0], [0, axis_length, 0], [0, 0, axis_length]]).reshape(-1, 3)
            
            # 转换到世界坐标系
            axis_points_world = np.dot(axis_points, R.T) + tvec.flatten()
            
            # 绘制相机位置
            self.canvas_3d.axes.scatter(tvec[0], tvec[1], tvec[2], c='r', marker='o')
            
            # 绘制坐标系
            self.canvas_3d.axes.plot([tvec[0], axis_points_world[1, 0]], 
                                    [tvec[1], axis_points_world[1, 1]], 
                                    [tvec[2], axis_points_world[1, 2]], c='r')  # X轴
            self.canvas_3d.axes.plot([tvec[0], axis_points_world[2, 0]], 
                                    [tvec[1], axis_points_world[2, 1]], 
                                    [tvec[2], axis_points_world[2, 2]], c='g')  # Y轴
            self.canvas_3d.axes.plot([tvec[0], axis_points_world[3, 0]], 
                                    [tvec[1], axis_points_world[3, 1]], 
                                    [tvec[2], axis_points_world[3, 2]], c='b')  # Z轴
            
            # 添加标签
            self.canvas_3d.axes.text(tvec[0], tvec[1], tvec[2], f'Cam {i}')
        
        # 设置坐标轴标签
        self.canvas_3d.axes.set_xlabel('X')
        self.canvas_3d.axes.set_ylabel('Y')
        self.canvas_3d.axes.set_zlabel('Z')
        self.canvas_3d.axes.set_title('相机位置和姿态')
        
        # 设置等比例坐标轴
        self.canvas_3d.axes.set_box_aspect([1, 1, 1])
        
        self.canvas_3d.draw()
            
    def toggle_undistort(self):
        """切换畸变校正模式"""
        self.undistort_mode = not self.undistort_mode
        if self.undistort_mode:
            self.undistort_btn.setText("原始图像")
        else:
            self.undistort_btn.setText("畸变校正")
            
    def save_parameters(self):
        """保存相机参数到文件"""
        if not self.calibration.calibrated:
            QMessageBox.warning(self, "警告", "尚未进行标定")
            return
            
        filename, _ = QFileDialog.getSaveFileName(
            self, "保存相机参数", "", "JSON文件 (*.json)"
        )
        
        if filename:
            if self.calibration.save_parameters(filename):
                QMessageBox.information(self, "成功", "参数已保存")
            else:
                QMessageBox.critical(self, "错误", "保存参数失败")
                
    def load_parameters(self):
        """从文件加载相机参数"""
        filename, _ = QFileDialog.getOpenFileName(
            self, "加载相机参数", "", "JSON文件 (*.json)"
        )
        
        if filename:
            if self.calibration.load_parameters(filename):
                self.undistort_btn.setEnabled(True)
                self.save_params_btn.setEnabled(True)
                self.show_errors_btn.setEnabled(True)
                self.reprojection_label.setText(f"重投影误差: {self.calibration.reprojection_error:.6f}")
                
                # 更新3D可视化
                self.update_3d_visualization()
                
                QMessageBox.information(self, "成功", "参数已加载")
            else:
                QMessageBox.critical(self, "错误", "加载参数失败")
                
    def open_image(self):
        """打开图像文件"""
        filename, _ = QFileDialog.getOpenFileName(
            self, "打开图像", "", "图像文件 (*.png *.jpg *.bmp *.tif)"
        )
        
        if filename:
            image = cv2.imread(filename)
            if image is not None:
                self.current_image = image
                self.image_viewer.set_image(image)
                
    def change_camera(self, camera_name):
        """切换当前相机"""
        if camera_name in self.calibrations:
            self.current_camera = camera_name
            self.calibration = self.calibrations[camera_name]
            
            # 更新图像列表
            self.images_list.clear()
            for i, img in enumerate(self.captured_images.get(camera_name, [])):
                self.images_list.addItem(f"图像 {i+1}")
                
            # 更新按钮状态
            self.calibrate_btn.setEnabled(len(self.captured_images.get(camera_name, [])) >= 5)
            self.undistort_btn.setEnabled(self.calibration.calibrated)
            self.save_params_btn.setEnabled(self.calibration.calibrated)
            self.show_errors_btn.setEnabled(self.calibration.calibrated)
            
            if self.calibration.calibrated:
                self.reprojection_label.setText(f"重投影误差: {self.calibration.reprojection_error:.6f}")
                
    def add_camera(self):
        """添加新相机"""
        camera_count = len(self.calibrations)
        new_camera_name = f"Camera {camera_count}"
        
        self.calibrations[new_camera_name] = CameraCalibration()
        self.captured_images[new_camera_name] = []
        
        self.camera_combo.addItem(new_camera_name)
        self.camera_combo.setCurrentText(new_camera_name)
        
    def remove_camera(self):
        """移除当前相机"""
        if len(self.calibrations) <= 1:
            QMessageBox.warning(self, "警告", "至少需要保留一个相机")
            return
            
        camera_name = self.current_camera
        del self.calibrations[camera_name]
        del self.captured_images[camera_name]
        
        self.camera_combo.removeItem(self.camera_combo.currentIndex())
        
    def change_pattern_type(self, pattern_type):
        """更改标定板类型"""
        self.calibration.set_pattern_type(pattern_type)
        self.pattern_size = self.calibration.pattern_sizes[pattern_type]
        self.pattern_width.setValue(self.pattern_size[0])
        self.pattern_height.setValue(self.pattern_size[1])
        
    def toggle_optimization(self, state):
        """切换优化选项"""
        self.calibration.set_optimization(state == Qt.Checked)
        
    def show_error_plot(self):
        """显示误差分布图"""
        if not self.calibration.calibrated:
            return
            
        # 创建新窗口显示误差分布
        error_window = QMainWindow(self)
        error_window.setWindowTitle("重投影误差分布")
        error_window.setGeometry(200, 200, 800, 600)
        
        canvas = MplCanvas(error_window, width=6, height=5, dpi=100)
        canvas.plot_errors(self.calibration.errors)
        
        error_window.setCentralWidget(canvas)
        error_window.show()
        
    def zoom_in(self):
        """放大图像"""
        self.image_viewer.zoom_factor *= 1.25
        self.image_viewer.zoom_factor = min(5.0, self.image_viewer.zoom_factor)
        self.image_viewer.update_display()
        
    def zoom_out(self):
        """缩小图像"""
        self.image_viewer.zoom_factor /= 1.25
        self.image_viewer.zoom_factor = max(0.1, self.image_viewer.zoom_factor)
        self.image_viewer.update_display()
        
    def reset_view(self):
        """重置视图"""
        self.image_viewer.reset_view()
        
    def update_pattern_size(self):
        """更新棋盘格尺寸"""
        self.pattern_size = (self.pattern_width.value(), self.pattern_height.value())
        
    def update_cell_size(self):
        """更新棋盘格方格大小"""
        self.cell_size = self.cell_size_spin.value()
        
    def closeEvent(self, event):
        """应用程序关闭事件"""
        if self.cap.isOpened():
            self.cap.release()
        event.accept()

def main():
    """主函数"""
    app = QApplication(sys.argv)
    
    # 设置应用程序样式和字体
    app.setStyle('Fusion')
    
    # 设置调色板以支持暗色主题
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(45, 45, 48))
    palette.setColor(QPalette.WindowText, Qt.white)
    palette.setColor(QPalette.Base, QColor(30, 30, 30))
    palette.setColor(QPalette.AlternateBase, QColor(45, 45, 48))
    palette.setColor(QPalette.ToolTipBase, Qt.white)
    palette.setColor(QPalette.ToolTipText, Qt.white)
    palette.setColor(QPalette.Text, Qt.white)
    palette.setColor(QPalette.Button, QColor(45, 45, 48))
    palette.setColor(QPalette.ButtonText, Qt.white)
    palette.setColor(QPalette.BrightText, Qt.red)
    palette.setColor(QPalette.Link, QColor(42, 130, 218))
    palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.HighlightedText, Qt.black)
    app.setPalette(palette)
    
    font = QFont("Microsoft YaHei", 10)
    app.setFont(font)
    
    window = CameraCalibrationApp()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()