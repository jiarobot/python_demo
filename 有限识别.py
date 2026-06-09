import sys
import os
import numpy as np
import cv2
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QTextEdit, 
                             QFileDialog, QMessageBox, QTabWidget, QGroupBox,
                             QSpinBox, QDoubleSpinBox, QCheckBox, QComboBox,
                             QProgressBar, QSlider, QSplitter, QListWidget)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QPixmap, QImage, QFont
from sklearn.svm import SVC
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import pickle
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

# 图像处理工具类
class ImageProcessor:
    @staticmethod
    def preprocess_image(image, resize_dim=(100, 100), 
                        apply_gaussian=True, apply_hist_eq=True):
        """图像预处理"""
        # 转换为灰度图
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
            
        # 调整大小
        resized = cv2.resize(gray, resize_dim)
        
        # 高斯模糊
        if apply_gaussian:
            resized = cv2.GaussianBlur(resized, (5, 5), 0)
            
        # 直方图均衡化
        if apply_hist_eq:
            resized = cv2.equalizeHist(resized)
            
        return resized
    
    @staticmethod
    def extract_features(image, method='hog'):
        """特征提取"""
        if method == 'hog':
            # HOG特征
            hog = cv2.HOGDescriptor()
            features = hog.compute(image)
            return features.flatten()
        elif method == 'lbp':
            # LBP特征
            lbp = LocalBinaryPatterns(24, 8)
            features = lbp.describe(image)
            return features
        else:
            # 简单的像素值作为特征
            return image.flatten()

# LBP特征提取类
class LocalBinaryPatterns:
    def __init__(self, numPoints, radius):
        self.numPoints = numPoints
        self.radius = radius
        
    def describe(self, image, eps=1e-7):
        # 计算LBP表示
        lbp = self.local_binary_pattern(image, self.numPoints, self.radius)
        
        # 计算直方图
        hist, _ = np.histogram(lbp.ravel(), 
                              bins=np.arange(0, self.numPoints + 3),
                              range=(0, self.numPoints + 2))
        
        # 归一化直方图
        hist = hist.astype("float")
        hist /= (hist.sum() + eps)
        
        return hist
    
    def local_binary_pattern(self, image, numPoints, radius):
        # 实现LBP算法
        lbp = np.zeros_like(image)
        for y in range(radius, image.shape[0]-radius):
            for x in range(radius, image.shape[1]-radius):
                center = image[y, x]
                binary_code = 0
                for i in range(numPoints):
                    # 计算采样点坐标
                    theta = 2 * np.pi * i / numPoints
                    x_sample = x + int(radius * np.cos(theta))
                    y_sample = y + int(radius * np.sin(theta))
                    
                    # 比较像素值
                    if image[y_sample, x_sample] >= center:
                        binary_code |= (1 << i)
                
                lbp[y, x] = binary_code
                
        return lbp

# 识别模型类
class RecognitionModel:
    def __init__(self):
        self.model = None
        self.is_trained = False
        self.feature_method = 'hog'
        self.preprocessing_params = {
            'resize_dim': (100, 100),
            'apply_gaussian': True,
            'apply_hist_eq': True
        }
        
    def train(self, features, labels):
        """训练模型"""
        if len(np.unique(labels)) < 2:
            raise ValueError("至少需要两个类别进行训练")
            
        # 使用SVM分类器
        self.model = SVC(kernel='linear', probability=True)
        self.model.fit(features, labels)
        self.is_trained = True
        
    def predict(self, features):
        """预测"""
        if not self.is_trained:
            raise ValueError("模型尚未训练")
            
        return self.model.predict(features)
    
    def predict_proba(self, features):
        """预测概率"""
        if not self.is_trained:
            raise ValueError("模型尚未训练")
            
        return self.model.predict_proba(features)
    
    def save_model(self, filepath):
        """保存模型"""
        if not self.is_trained:
            raise ValueError("模型尚未训练")
            
        model_data = {
            'model': self.model,
            'feature_method': self.feature_method,
            'preprocessing_params': self.preprocessing_params
        }
        
        with open(filepath, 'wb') as f:
            pickle.dump(model_data, f)
    
    def load_model(self, filepath):
        """加载模型"""
        with open(filepath, 'rb') as f:
            model_data = pickle.load(f)
            
        self.model = model_data['model']
        self.feature_method = model_data['feature_method']
        self.preprocessing_params = model_data['preprocessing_params']
        self.is_trained = True

# 训练线程类
class TrainingThread(QThread):
    progress_signal = pyqtSignal(int)
    finished_signal = pyqtSignal(float)  # 准确率
    error_signal = pyqtSignal(str)
    
    def __init__(self, model, images, labels):
        super().__init__()
        self.model = model
        self.images = images
        self.labels = labels
        
    def run(self):
        try:
            # 预处理和特征提取
            features = []
            total = len(self.images)
            
            for i, image in enumerate(self.images):
                # 预处理
                processed = ImageProcessor.preprocess_image(
                    image, **self.model.preprocessing_params)
                
                # 特征提取
                feature = ImageProcessor.extract_features(
                    processed, self.model.feature_method)
                features.append(feature)
                
                # 更新进度
                progress = int((i + 1) / total * 50)  # 特征提取占50%
                self.progress_signal.emit(progress)
                
            features = np.array(features)
            
            # 分割训练集和测试集
            X_train, X_test, y_train, y_test = train_test_split(
                features, self.labels, test_size=0.2, random_state=42)
            
            # 训练模型
            self.model.train(X_train, y_train)
            
            # 评估模型
            y_pred = self.model.predict(X_test)
            accuracy = accuracy_score(y_test, y_pred)
            
            self.progress_signal.emit(100)
            self.finished_signal.emit(accuracy)
            
        except Exception as e:
            self.error_signal.emit(str(e))

# 主界面类
class RecognitionSystem(QMainWindow):
    def __init__(self):
        super().__init__()
        self.model = RecognitionModel()
        self.images = []
        self.labels = []
        self.current_image = None
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("有限识别系统高级工具库")
        self.setGeometry(100, 100, 1200, 800)
        
        # 创建中央部件和主布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        # 左侧面板
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # 图像显示区域
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setMinimumSize(400, 300)
        self.image_label.setStyleSheet("border: 1px solid gray;")
        left_layout.addWidget(self.image_label)
        
        # 图像控制按钮
        image_control_group = QGroupBox("图像控制")
        image_control_layout = QHBoxLayout(image_control_group)
        
        self.load_image_btn = QPushButton("加载图像")
        self.load_image_btn.clicked.connect(self.load_image)
        
        self.preprocess_btn = QPushButton("预处理图像")
        self.preprocess_btn.clicked.connect(self.preprocess_image)
        
        self.extract_features_btn = QPushButton("提取特征")
        self.extract_features_btn.clicked.connect(self.extract_features)
        
        image_control_layout.addWidget(self.load_image_btn)
        image_control_layout.addWidget(self.preprocess_btn)
        image_control_layout.addWidget(self.extract_features_btn)
        left_layout.addWidget(image_control_group)
        
        # 日志区域
        log_group = QGroupBox("系统日志")
        log_layout = QVBoxLayout(log_group)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)
        
        left_layout.addWidget(log_group)
        
        # 右侧面板
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # 创建标签页
        self.tabs = QTabWidget()
        right_layout.addWidget(self.tabs)
        
        # 预处理设置标签页
        preprocess_tab = QWidget()
        preprocess_layout = QVBoxLayout(preprocess_tab)
        
        # 预处理参数设置
        preprocess_params_group = QGroupBox("预处理参数")
        preprocess_params_layout = QVBoxLayout(preprocess_params_group)
        
        # 图像尺寸设置
        size_layout = QHBoxLayout()
        size_layout.addWidget(QLabel("图像尺寸:"))
        self.width_spin = QSpinBox()
        self.width_spin.setRange(50, 500)
        self.width_spin.setValue(100)
        self.width_spin.valueChanged.connect(self.update_preprocess_params)
        size_layout.addWidget(self.width_spin)
        
        self.height_spin = QSpinBox()
        self.height_spin.setRange(50, 500)
        self.height_spin.setValue(100)
        self.height_spin.valueChanged.connect(self.update_preprocess_params)
        size_layout.addWidget(self.height_spin)
        preprocess_params_layout.addLayout(size_layout)
        
        # 预处理选项
        self.gaussian_check = QCheckBox("应用高斯模糊")
        self.gaussian_check.setChecked(True)
        self.gaussian_check.stateChanged.connect(self.update_preprocess_params)
        preprocess_params_layout.addWidget(self.gaussian_check)
        
        self.hist_eq_check = QCheckBox("应用直方图均衡化")
        self.hist_eq_check.setChecked(True)
        self.hist_eq_check.stateChanged.connect(self.update_preprocess_params)
        preprocess_params_layout.addWidget(self.hist_eq_check)
        
        preprocess_layout.addWidget(preprocess_params_group)
        preprocess_layout.addStretch()
        
        self.tabs.addTab(preprocess_tab, "预处理设置")
        
        # 特征提取设置标签页
        feature_tab = QWidget()
        feature_layout = QVBoxLayout(feature_tab)
        
        feature_params_group = QGroupBox("特征提取参数")
        feature_params_layout = QVBoxLayout(feature_params_group)
        
        feature_params_layout.addWidget(QLabel("特征提取方法:"))
        self.feature_method_combo = QComboBox()
        self.feature_method_combo.addItems(['hog', 'lbp', 'pixel'])
        self.feature_method_combo.currentTextChanged.connect(self.update_feature_method)
        feature_params_layout.addWidget(self.feature_method_combo)
        
        feature_layout.addWidget(feature_params_group)
        feature_layout.addStretch()
        
        self.tabs.addTab(feature_tab, "特征提取设置")
        
        # 训练标签页
        training_tab = QWidget()
        training_layout = QVBoxLayout(training_tab)
        
        # 训练控制
        training_control_group = QGroupBox("训练控制")
        training_control_layout = QVBoxLayout(training_control_group)
        
        self.load_dataset_btn = QPushButton("加载数据集")
        self.load_dataset_btn.clicked.connect(self.load_dataset)
        training_control_layout.addWidget(self.load_dataset_btn)
        
        self.train_btn = QPushButton("开始训练")
        self.train_btn.clicked.connect(self.start_training)
        training_control_layout.addWidget(self.train_btn)
        
        self.save_model_btn = QPushButton("保存模型")
        self.save_model_btn.clicked.connect(self.save_model)
        training_control_layout.addWidget(self.save_model_btn)
        
        self.load_model_btn = QPushButton("加载模型")
        self.load_model_btn.clicked.connect(self.load_model)
        training_control_layout.addWidget(self.load_model_btn)
        
        training_layout.addWidget(training_control_group)
        
        # 训练进度
        self.progress_bar = QProgressBar()
        training_layout.addWidget(self.progress_bar)
        
        # 训练结果
        self.result_label = QLabel("训练结果将显示在这里")
        training_layout.addWidget(self.result_label)
        
        self.tabs.addTab(training_tab, "模型训练")
        
        # 识别标签页
        recognition_tab = QWidget()
        recognition_layout = QVBoxLayout(recognition_tab)
        
        recognition_control_group = QGroupBox("识别控制")
        recognition_control_layout = QVBoxLayout(recognition_control_group)
        
        self.recognize_btn = QPushButton("识别图像")
        self.recognize_btn.clicked.connect(self.recognize_image)
        recognition_control_layout.addWidget(self.recognize_btn)
        
        self.camera_btn = QPushButton("开启摄像头识别")
        self.camera_btn.clicked.connect(self.toggle_camera)
        recognition_control_layout.addWidget(self.camera_btn)
        
        recognition_layout.addWidget(recognition_control_group)
        
        # 识别结果
        self.recognition_result = QLabel("识别结果将显示在这里")
        recognition_layout.addWidget(self.recognition_result)
        
        self.tabs.addTab(recognition_tab, "图像识别")
        
        # 将左右面板添加到分割器
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([600, 600])
        
        # 状态栏
        self.statusBar().showMessage("就绪")
        
        # 初始化参数
        self.update_preprocess_params()
        self.update_feature_method()
        
        # 摄像头相关
        self.camera_timer = QTimer()
        self.camera_timer.timeout.connect(self.update_camera_frame)
        self.camera_active = False
        self.cap = None
        
        self.log_message("系统初始化完成")
        
    def log_message(self, message):
        """添加日志消息"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
        
    def update_preprocess_params(self):
        """更新预处理参数"""
        self.model.preprocessing_params = {
            'resize_dim': (self.width_spin.value(), self.height_spin.value()),
            'apply_gaussian': self.gaussian_check.isChecked(),
            'apply_hist_eq': self.hist_eq_check.isChecked()
        }
        
    def update_feature_method(self):
        """更新特征提取方法"""
        self.model.feature_method = self.feature_method_combo.currentText()
        
    def load_image(self):
        """加载图像"""
        filepath, _ = QFileDialog.getOpenFileName(
            self, "选择图像", "", "图像文件 (*.png *.jpg *.jpeg *.bmp)")
        
        if filepath:
            image = cv2.imread(filepath)
            if image is not None:
                self.current_image = image
                self.display_image(image)
                self.log_message(f"已加载图像: {os.path.basename(filepath)}")
            else:
                QMessageBox.warning(self, "错误", "无法加载图像")
                
    def display_image(self, image):
        """显示图像"""
        # 转换图像格式用于显示
        if len(image.shape) == 3:
            if image.shape[2] == 3:  # BGR
                rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            else:  # BGRA
                rgb_image = cv2.cvtColor(image, cv2.COLOR_BGRA2RGB)
        else:  # 灰度图
            rgb_image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
            
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        
        # 缩放图像以适应标签
        pixmap = QPixmap.fromImage(qt_image)
        scaled_pixmap = pixmap.scaled(
            self.image_label.width(), 
            self.image_label.height(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        self.image_label.setPixmap(scaled_pixmap)
        
    def preprocess_image(self):
        """预处理图像"""
        if self.current_image is None:
            QMessageBox.warning(self, "错误", "请先加载图像")
            return
            
        processed = ImageProcessor.preprocess_image(
            self.current_image, **self.model.preprocessing_params)
        self.display_image(processed)
        self.log_message("图像预处理完成")
        
    def extract_features(self):
        """提取特征"""
        if self.current_image is None:
            QMessageBox.warning(self, "错误", "请先加载图像")
            return
            
        processed = ImageProcessor.preprocess_image(
            self.current_image, **self.model.preprocessing_params)
        features = ImageProcessor.extract_features(
            processed, self.model.feature_method)
        
        self.log_message(f"特征提取完成，特征维度: {features.shape}")
        
    def load_dataset(self):
        """加载数据集"""
        directory = QFileDialog.getExistingDirectory(
            self, "选择数据集目录")
        
        if directory:
            self.images = []
            self.labels = []
            
            # 假设目录结构为: dataset/label/image.jpg
            for label_name in os.listdir(directory):
                label_dir = os.path.join(directory, label_name)
                if os.path.isdir(label_dir):
                    for image_name in os.listdir(label_dir):
                        image_path = os.path.join(label_dir, image_name)
                        image = cv2.imread(image_path)
                        if image is not None:
                            self.images.append(image)
                            self.labels.append(label_name)
            
            self.log_message(f"数据集加载完成: {len(self.images)} 张图像, {len(set(self.labels))} 个类别")
            
    def start_training(self):
        """开始训练"""
        if len(self.images) == 0:
            QMessageBox.warning(self, "错误", "请先加载数据集")
            return
            
        # 创建训练线程
        self.training_thread = TrainingThread(self.model, self.images, self.labels)
        self.training_thread.progress_signal.connect(self.update_progress)
        self.training_thread.finished_signal.connect(self.training_finished)
        self.training_thread.error_signal.connect(self.training_error)
        
        # 禁用训练按钮
        self.train_btn.setEnabled(False)
        
        # 开始训练
        self.training_thread.start()
        self.log_message("开始训练模型...")
        
    def update_progress(self, value):
        """更新进度条"""
        self.progress_bar.setValue(value)
        
    def training_finished(self, accuracy):
        """训练完成"""
        self.train_btn.setEnabled(True)
        self.result_label.setText(f"训练完成，测试准确率: {accuracy:.2f}")
        self.log_message(f"模型训练完成，准确率: {accuracy:.2f}")
        
    def training_error(self, error_message):
        """训练错误"""
        self.train_btn.setEnabled(True)
        self.result_label.setText(f"训练错误: {error_message}")
        self.log_message(f"训练错误: {error_message}")
        
    def save_model(self):
        """保存模型"""
        if not self.model.is_trained:
            QMessageBox.warning(self, "错误", "模型尚未训练")
            return
            
        filepath, _ = QFileDialog.getSaveFileName(
            self, "保存模型", "", "模型文件 (*.pkl)")
        
        if filepath:
            try:
                self.model.save_model(filepath)
                self.log_message(f"模型已保存: {filepath}")
            except Exception as e:
                QMessageBox.warning(self, "错误", f"保存模型失败: {str(e)}")
                
    def load_model(self):
        """加载模型"""
        filepath, _ = QFileDialog.getOpenFileName(
            self, "加载模型", "", "模型文件 (*.pkl)")
        
        if filepath:
            try:
                self.model.load_model(filepath)
                self.log_message(f"模型已加载: {filepath}")
                
                # 更新UI参数
                params = self.model.preprocessing_params
                self.width_spin.setValue(params['resize_dim'][0])
                self.height_spin.setValue(params['resize_dim'][1])
                self.gaussian_check.setChecked(params['apply_gaussian'])
                self.hist_eq_check.setChecked(params['apply_hist_eq'])
                self.feature_method_combo.setCurrentText(self.model.feature_method)
                
            except Exception as e:
                QMessageBox.warning(self, "错误", f"加载模型失败: {str(e)}")
                
    def recognize_image(self):
        """识别图像"""
        if not self.model.is_trained:
            QMessageBox.warning(self, "错误", "模型尚未训练或加载")
            return
            
        if self.current_image is None:
            QMessageBox.warning(self, "错误", "请先加载图像")
            return
            
        try:
            # 预处理和特征提取
            processed = ImageProcessor.preprocess_image(
                self.current_image, **self.model.preprocessing_params)
            features = ImageProcessor.extract_features(
                processed, self.model.feature_method)
            
            # 预测
            prediction = self.model.predict([features])[0]
            probability = self.model.predict_proba([features])[0]
            
            # 显示结果
            max_prob = np.max(probability)
            result_text = f"识别结果: {prediction} (置信度: {max_prob:.2f})"
            self.recognition_result.setText(result_text)
            self.log_message(f"图像识别完成: {result_text}")
            
        except Exception as e:
            QMessageBox.warning(self, "错误", f"识别失败: {str(e)}")
            
    def toggle_camera(self):
        """切换摄像头"""
        if not self.camera_active:
            # 开启摄像头
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                QMessageBox.warning(self, "错误", "无法打开摄像头")
                return
                
            self.camera_active = True
            self.camera_btn.setText("关闭摄像头")
            self.camera_timer.start(30)  # 30ms更新一帧
            self.log_message("摄像头已开启")
        else:
            # 关闭摄像头
            self.camera_active = False
            self.camera_btn.setText("开启摄像头识别")
            self.camera_timer.stop()
            if self.cap:
                self.cap.release()
            self.log_message("摄像头已关闭")
            
    def update_camera_frame(self):
        """更新摄像头帧"""
        if self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                # 显示原始帧
                self.current_image = frame
                self.display_image(frame)
                
                # 如果模型已训练，进行实时识别
                if self.model.is_trained:
                    try:
                        processed = ImageProcessor.preprocess_image(
                            frame, **self.model.preprocessing_params)
                        features = ImageProcessor.extract_features(
                            processed, self.model.feature_method)
                        
                        prediction = self.model.predict([features])[0]
                        probability = self.model.predict_proba([features])[0]
                        max_prob = np.max(probability)
                        
                        # 在状态栏显示结果
                        self.statusBar().showMessage(
                            f"实时识别: {prediction} (置信度: {max_prob:.2f})")
                    except Exception as e:
                        self.statusBar().showMessage("实时识别错误")
                        
    def closeEvent(self, event):
        """关闭事件"""
        if self.camera_active:
            self.camera_timer.stop()
            if self.cap:
                self.cap.release()
        event.accept()

# 主函数
def main():
    app = QApplication(sys.argv)
    
    # 设置应用样式
    app.setStyle('Fusion')
    
    # 创建并显示主窗口
    window = RecognitionSystem()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()