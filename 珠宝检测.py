import sys
import os
import numpy as np
import cv2
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QPushButton, QFileDialog, 
                             QMessageBox, QTabWidget, QGroupBox, QSlider, 
                             QSpinBox, QDoubleSpinBox, QCheckBox, QComboBox,
                             QProgressBar, QSplitter, QListWidget, QTextEdit)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QPixmap, QImage, QFont, QPalette, QColor
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from sklearn.cluster import KMeans
from sklearn.svm import SVC
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
import pandas as pd
import json
from datetime import datetime


class ImageProcessingThread(QThread):
    """图像处理线程"""
    progress_updated = pyqtSignal(int)
    processing_finished = pyqtSignal(object)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, image_path, operation, parameters):
        super().__init__()
        self.image_path = image_path
        self.operation = operation
        self.parameters = parameters
        self.result = None
    
    def run(self):
        try:
            # 读取图像
            image = cv2.imread(self.image_path)
            if image is None:
                self.error_occurred.emit("无法读取图像文件")
                return
            
            # 根据操作类型执行不同的图像处理
            if self.operation == "preprocess":
                self.result = self.preprocess_image(image)
            elif self.operation == "edge_detection":
                self.result = self.edge_detection(image)
            elif self.operation == "color_analysis":
                self.result = self.color_analysis(image)
            elif self.operation == "feature_extraction":
                self.result = self.extract_features(image)
            
            self.processing_finished.emit(self.result)
            
        except Exception as e:
            self.error_occurred.emit(str(e))
    
    def preprocess_image(self, image):
        """图像预处理"""
        self.progress_updated.emit(10)
        
        # 转换为灰度图
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        
        self.progress_updated.emit(30)
        
        # 高斯模糊
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        
        self.progress_updated.emit(50)
        
        # 直方图均衡化
        equalized = cv2.equalizeHist(blurred)
        
        self.progress_updated.emit(70)
        
        # 二值化
        _, binary = cv2.threshold(equalized, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        self.progress_updated.emit(90)
        
        # 形态学操作
        kernel = np.ones((3, 3), np.uint8)
        morph = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        
        self.progress_updated.emit(100)
        
        return {
            "original": image,
            "gray": gray,
            "blurred": blurred,
            "equalized": equalized,
            "binary": binary,
            "morph": morph
        }
    
    def edge_detection(self, image):
        """边缘检测"""
        self.progress_updated.emit(10)
        
        # 转换为灰度图
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        
        self.progress_updated.emit(30)
        
        # Canny边缘检测
        edges = cv2.Canny(gray, 
                         self.parameters.get("canny_low", 50),
                         self.parameters.get("canny_high", 150))
        
        self.progress_updated.emit(60)
        
        # Sobel边缘检测
        sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=5)
        sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=5)
        sobel = np.sqrt(sobelx**2 + sobely**2)
        sobel = np.uint8(255 * sobel / np.max(sobel))
        
        self.progress_updated.emit(90)
        
        # Laplacian边缘检测
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        laplacian = np.uint8(np.absolute(laplacian))
        
        self.progress_updated.emit(100)
        
        return {
            "original": image,
            "gray": gray,
            "canny": edges,
            "sobel": sobel,
            "laplacian": laplacian
        }
    
    def color_analysis(self, image):
        """颜色分析"""
        self.progress_updated.emit(10)
        
        # 转换为RGB
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        self.progress_updated.emit(30)
        
        # 转换为HSV
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        self.progress_updated.emit(50)
        
        # 颜色量化
        pixels = rgb.reshape((-1, 3))
        kmeans = KMeans(n_clusters=self.parameters.get("n_colors", 5), random_state=42)
        kmeans.fit(pixels)
        
        self.progress_updated.emit(80)
        
        # 获取主要颜色
        colors = kmeans.cluster_centers_.astype(int)
        color_counts = np.bincount(kmeans.labels_)
        color_percentages = color_counts / len(pixels) * 100
        
        self.progress_updated.emit(100)
        
        return {
            "original": image,
            "rgb": rgb,
            "hsv": hsv,
            "dominant_colors": colors,
            "color_percentages": color_percentages
        }
    
    def extract_features(self, image):
        """特征提取"""
        self.progress_updated.emit(10)
        
        # 转换为灰度图
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        
        self.progress_updated.emit(30)
        
        # 二值化
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        self.progress_updated.emit(50)
        
        # 轮廓检测
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # 筛选最大的轮廓
        if contours:
            main_contour = max(contours, key=cv2.contourArea)
            
            # 计算轮廓特征
            area = cv2.contourArea(main_contour)
            perimeter = cv2.arcLength(main_contour, True)
            
            # 计算轮廓的边界矩形
            x, y, w, h = cv2.boundingRect(main_contour)
            aspect_ratio = float(w) / h
            
            # 计算轮廓的圆形度
            circularity = 4 * np.pi * area / (perimeter ** 2) if perimeter > 0 else 0
            
            # 计算Hu矩
            moments = cv2.moments(main_contour)
            hu_moments = cv2.HuMoments(moments).flatten()
            
            self.progress_updated.emit(80)
            
            # 计算颜色特征
            hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
            h_mean, s_mean, v_mean = np.mean(hsv, axis=(0, 1))
            h_std, s_std, v_std = np.std(hsv, axis=(0, 1))
            
            self.progress_updated.emit(100)
            
            features = {
                "area": area,
                "perimeter": perimeter,
                "aspect_ratio": aspect_ratio,
                "circularity": circularity,
                "hu_moments": hu_moments.tolist(),
                "color_mean": [h_mean, s_mean, v_mean],
                "color_std": [h_std, s_std, v_std],
                "contour": main_contour
            }
        else:
            features = {}
        
        return {
            "original": image,
            "gray": gray,
            "binary": binary,
            "contours": contours,
            "features": features
        }


class JewelryClassifier:
    """珠宝分类器"""
    
    def __init__(self):
        self.model = None
        self.scaler = StandardScaler()
        self.is_trained = False
        self.classes = []
    
    def train(self, features, labels):
        """训练分类器"""
        if len(features) == 0:
            return False
        
        # 标准化特征
        X_scaled = self.scaler.fit_transform(features)
        
        # 训练SVM分类器
        self.model = SVC(kernel='rbf', probability=True, random_state=42)
        self.model.fit(X_scaled, labels)
        
        self.classes = list(set(labels))
        self.is_trained = True
        
        return True
    
    def predict(self, features):
        """预测珠宝类型"""
        if not self.is_trained or self.model is None:
            return None, None
        
        # 标准化特征
        X_scaled = self.scaler.transform([features])
        
        # 预测
        prediction = self.model.predict(X_scaled)[0]
        probability = self.model.predict_proba(X_scaled)[0]
        
        return prediction, max(probability)


class ImageCanvas(FigureCanvas):
    """图像显示画布"""
    
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig, self.ax = plt.subplots(figsize=(width, height), dpi=dpi)
        super().__init__(self.fig)
        self.setParent(parent)
        
        self.ax.set_xticks([])
        self.ax.set_yticks([])
        self.fig.tight_layout()
    
    def display_image(self, image, title="", cmap=None):
        """显示图像"""
        self.ax.clear()
        
        if len(image.shape) == 2:  # 灰度图
            self.ax.imshow(image, cmap=cmap or 'gray')
        else:  # 彩色图
            # 如果是BGR格式，转换为RGB
            if image.shape[2] == 3:
                image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                self.ax.imshow(image_rgb)
            else:
                self.ax.imshow(image)
        
        self.ax.set_title(title)
        self.ax.set_xticks([])
        self.ax.set_yticks([])
        self.draw()


class JewelryDetectionToolkit(QMainWindow):
    """珠宝检测系统主窗口"""
    
    def __init__(self):
        super().__init__()
        self.current_image = None
        self.image_path = None
        self.processing_thread = None
        self.classifier = JewelryClassifier()
        self.features_db = {}  # 特征数据库
        
        self.init_ui()
        self.load_feature_database()
    
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("高级珠宝检测系统")
        self.setGeometry(100, 100, 1400, 900)
        
        # 设置中心窗口
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QHBoxLayout(central_widget)
        
        # 左侧控制面板
        control_panel = self.create_control_panel()
        main_layout.addWidget(control_panel, 1)
        
        # 右侧显示区域
        display_area = self.create_display_area()
        main_layout.addWidget(display_area, 3)
        
        # 状态栏
        self.statusBar().showMessage("就绪")
    
    def create_control_panel(self):
        """创建控制面板"""
        panel = QWidget()
        panel.setMaximumWidth(400)
        layout = QVBoxLayout(panel)
        
        # 文件操作组
        file_group = QGroupBox("文件操作")
        file_layout = QVBoxLayout(file_group)
        
        self.btn_open = QPushButton("打开图像")
        self.btn_open.clicked.connect(self.open_image)
        file_layout.addWidget(self.btn_open)
        
        self.btn_save = QPushButton("保存结果")
        self.btn_save.clicked.connect(self.save_results)
        file_layout.addWidget(self.btn_save)
        
        layout.addWidget(file_group)
        
        # 图像处理组
        processing_group = QGroupBox("图像处理")
        processing_layout = QVBoxLayout(processing_group)
        
        self.btn_preprocess = QPushButton("图像预处理")
        self.btn_preprocess.clicked.connect(lambda: self.process_image("preprocess"))
        processing_layout.addWidget(self.btn_preprocess)
        
        self.btn_edges = QPushButton("边缘检测")
        self.btn_edges.clicked.connect(lambda: self.process_image("edge_detection"))
        processing_layout.addWidget(self.btn_edges)
        
        self.btn_color = QPushButton("颜色分析")
        self.btn_color.clicked.connect(lambda: self.process_image("color_analysis"))
        processing_layout.addWidget(self.btn_color)
        
        self.btn_features = QPushButton("特征提取")
        self.btn_features.clicked.connect(lambda: self.process_image("feature_extraction"))
        processing_layout.addWidget(self.btn_features)
        
        layout.addWidget(processing_group)
        
        # 参数设置组
        params_group = QGroupBox("处理参数")
        params_layout = QVBoxLayout(params_group)
        
        # Canny边缘检测参数
        canny_layout = QHBoxLayout()
        canny_layout.addWidget(QLabel("Canny低阈值:"))
        self.canny_low = QSpinBox()
        self.canny_low.setRange(0, 255)
        self.canny_low.setValue(50)
        canny_layout.addWidget(self.canny_low)
        params_layout.addLayout(canny_layout)
        
        canny_layout2 = QHBoxLayout()
        canny_layout2.addWidget(QLabel("Canny高阈值:"))
        self.canny_high = QSpinBox()
        self.canny_high.setRange(0, 255)
        self.canny_high.setValue(150)
        canny_layout2.addWidget(self.canny_high)
        params_layout.addLayout(canny_layout2)
        
        # 颜色分析参数
        color_layout = QHBoxLayout()
        color_layout.addWidget(QLabel("主要颜色数量:"))
        self.n_colors = QSpinBox()
        self.n_colors.setRange(2, 10)
        self.n_colors.setValue(5)
        color_layout.addWidget(self.n_colors)
        params_layout.addLayout(color_layout)
        
        layout.addWidget(params_group)
        
        # 分类器组
        classifier_group = QGroupBox("珠宝分类")
        classifier_layout = QVBoxLayout(classifier_group)
        
        self.btn_train = QPushButton("训练分类器")
        self.btn_train.clicked.connect(self.train_classifier)
        classifier_layout.addWidget(self.btn_train)
        
        self.btn_predict = QPushButton("预测珠宝类型")
        self.btn_predict.clicked.connect(self.predict_jewelry)
        classifier_layout.addWidget(self.btn_predict)
        
        # 分类结果展示
        self.lbl_prediction = QLabel("预测结果: 未预测")
        classifier_layout.addWidget(self.lbl_prediction)
        
        self.lbl_confidence = QLabel("置信度: 0%")
        classifier_layout.addWidget(self.lbl_confidence)
        
        layout.addWidget(classifier_group)
        
        # 进度条
        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)
        
        layout.addStretch()
        
        return panel
    
    def create_display_area(self):
        """创建显示区域"""
        tab_widget = QTabWidget()
        
        # 原始图像标签
        self.original_canvas = ImageCanvas(self, width=8, height=6)
        tab_widget.addTab(self.original_canvas, "原始图像")
        
        # 处理结果标签
        self.result_canvas = ImageCanvas(self, width=8, height=6)
        tab_widget.addTab(self.result_canvas, "处理结果")
        
        # 特征可视化标签
        self.feature_widget = QWidget()
        feature_layout = QVBoxLayout(self.feature_widget)
        
        self.feature_text = QTextEdit()
        self.feature_text.setReadOnly(True)
        feature_layout.addWidget(self.feature_text)
        
        tab_widget.addTab(self.feature_widget, "特征信息")
        
        return tab_widget
    
    def open_image(self):
        """打开图像文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "打开图像", "", 
            "图像文件 (*.png *.jpg *.jpeg *.bmp *.tiff)"
        )
        
        if file_path:
            self.image_path = file_path
            self.current_image = cv2.imread(file_path)
            
            if self.current_image is not None:
                self.original_canvas.display_image(self.current_image, "原始图像")
                self.statusBar().showMessage(f"已加载图像: {os.path.basename(file_path)}")
            else:
                QMessageBox.warning(self, "错误", "无法加载图像文件")
    
    def process_image(self, operation):
        """处理图像"""
        if self.current_image is None:
            QMessageBox.warning(self, "警告", "请先打开图像")
            return
        
        # 获取参数
        parameters = {
            "canny_low": self.canny_low.value(),
            "canny_high": self.canny_high.value(),
            "n_colors": self.n_colors.value()
        }
        
        # 创建并启动处理线程
        self.processing_thread = ImageProcessingThread(
            self.image_path, operation, parameters
        )
        self.processing_thread.progress_updated.connect(self.update_progress)
        self.processing_thread.processing_finished.connect(self.on_processing_finished)
        self.processing_thread.error_occurred.connect(self.on_processing_error)
        self.processing_thread.start()
        
        self.statusBar().showMessage(f"正在执行 {operation}...")
    
    def update_progress(self, value):
        """更新进度条"""
        self.progress_bar.setValue(value)
    
    def on_processing_finished(self, result):
        """处理完成回调"""
        self.processing_result = result
        
        # 显示处理结果
        if "gray" in result:
            self.result_canvas.display_image(result["gray"], "处理结果")
        
        # 显示特征信息
        if "features" in result:
            self.display_features(result["features"])
        
        self.statusBar().showMessage("处理完成")
    
    def on_processing_error(self, error_msg):
        """处理错误回调"""
        QMessageBox.critical(self, "处理错误", error_msg)
        self.statusBar().showMessage("处理出错")
    
    def display_features(self, features):
        """显示特征信息"""
        feature_text = "提取到的特征:\n\n"
        
        for key, value in features.items():
            if key == "hu_moments":
                feature_text += f"{key}:\n"
                for i, moment in enumerate(value):
                    feature_text += f"  M{i+1}: {moment:.6f}\n"
            elif key == "color_mean" or key == "color_std":
                feature_text += f"{key}: [{value[0]:.2f}, {value[1]:.2f}, {value[2]:.2f}]\n"
            elif key != "contour":
                feature_text += f"{key}: {value:.2f}\n"
        
        self.feature_text.setText(feature_text)
    
    def train_classifier(self):
        """训练分类器"""
        if not self.features_db:
            QMessageBox.warning(self, "警告", "特征数据库为空，请先提取特征并添加到数据库")
            return
        
        # 准备训练数据
        features = []
        labels = []
        
        for item in self.features_db.values():
            features.append([
                item["area"],
                item["perimeter"],
                item["aspect_ratio"],
                item["circularity"],
                *item["color_mean"],
                *item["color_std"]
            ])
            labels.append(item["label"])
        
        # 训练分类器
        if self.classifier.train(features, labels):
            QMessageBox.information(self, "成功", "分类器训练完成")
            self.statusBar().showMessage("分类器已训练")
        else:
            QMessageBox.warning(self, "错误", "分类器训练失败")
    
    def predict_jewelry(self):
        """预测珠宝类型"""
        if not self.classifier.is_trained:
            QMessageBox.warning(self, "警告", "请先训练分类器")
            return
        
        if "features" not in self.processing_result:
            QMessageBox.warning(self, "警告", "请先提取特征")
            return
        
        features = self.processing_result["features"]
        
        # 准备特征向量
        feature_vector = [
            features["area"],
            features["perimeter"],
            features["aspect_ratio"],
            features["circularity"],
            *features["color_mean"],
            *features["color_std"]
        ]
        
        # 预测
        prediction, confidence = self.classifier.predict(feature_vector)
        
        if prediction is not None:
            self.lbl_prediction.setText(f"预测结果: {prediction}")
            self.lbl_confidence.setText(f"置信度: {confidence*100:.2f}%")
            self.statusBar().showMessage(f"预测完成: {prediction} (置信度: {confidence*100:.2f}%)")
        else:
            QMessageBox.warning(self, "错误", "预测失败")
    
    def save_results(self):
        """保存结果"""
        if self.processing_result is None:
            QMessageBox.warning(self, "警告", "没有可保存的结果")
            return
        
        # 选择保存路径
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存结果", "", "JSON文件 (*.json)"
        )
        
        if file_path:
            # 准备保存数据
            save_data = {
                "image_path": self.image_path,
                "timestamp": datetime.now().isoformat(),
                "features": self.processing_result.get("features", {})
            }
            
            # 保存到文件
            with open(file_path, 'w') as f:
                json.dump(save_data, f, indent=2)
            
            self.statusBar().showMessage(f"结果已保存: {file_path}")
    
    def load_feature_database(self):
        """加载特征数据库"""
        # 这里可以改为从文件加载
        # 目前使用空数据库
        self.features_db = {}
    
    def closeEvent(self, event):
        """关闭事件"""
        if self.processing_thread and self.processing_thread.isRunning():
            self.processing_thread.terminate()
            self.processing_thread.wait()
        
        event.accept()


def main():
    """主函数"""
    app = QApplication(sys.argv)
    
    # 设置应用样式
    app.setStyle('Fusion')
    
    # 创建主窗口
    window = JewelryDetectionToolkit()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()