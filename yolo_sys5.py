import sys
import os
import cv2
import numpy as np
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QComboBox, 
                             QSlider, QSpinBox, QDoubleSpinBox, QCheckBox,
                             QFileDialog, QMessageBox, QProgressBar, QTabWidget,
                             QGroupBox, QListWidget, QSplitter, QFrame)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt5.QtGui import QPixmap, QImage, QFont
import torch
import torchvision
from PIL import Image, ImageDraw, ImageFont

class YOLODetector:
    """YOLO检测器类"""
    def __init__(self, model_path=None, model_type='yolov5'):
        self.model_type = model_type
        self.model = None
        self.classes = None
        self.colors = None
        
        if model_path:
            self.load_model(model_path)
    
    def load_model(self, model_path):
        """加载YOLO模型"""
        try:
            if self.model_type == 'yolov5':
                self.model = torch.hub.load('ultralytics/yolov5', 'custom', path=model_path)
                self.classes = self.model.names
            elif self.model_type == 'yolov8':
                from ultralytics import YOLO
                self.model = YOLO(model_path)
                self.classes = self.model.names
            
            # 生成随机颜色
            np.random.seed(42)
            self.colors = np.random.randint(0, 255, size=(len(self.classes), 3), dtype=np.uint8)
            return True
        except Exception as e:
            print(f"加载模型失败: {e}")
            return False
    
    def detect(self, image, conf_threshold=0.25, iou_threshold=0.45):
        """执行目标检测"""
        if self.model is None:
            return image, []
        
        try:
            if self.model_type == 'yolov5':
                # 设置参数
                self.model.conf = conf_threshold
                self.model.iou = iou_threshold
                
                # 执行推理
                results = self.model(image)
                
                # 解析结果
                detections = []
                for *xyxy, conf, cls in results.xyxy[0]:
                    x1, y1, x2, y2 = map(int, xyxy)
                    class_id = int(cls)
                    class_name = self.classes[class_id]
                    confidence = float(conf)
                    
                    detections.append({
                        'bbox': [x1, y1, x2, y2],
                        'class_id': class_id,
                        'class_name': class_name,
                        'confidence': confidence
                    })
                
                # 绘制检测结果
                result_image = self.draw_detections(image, detections)
                return result_image, detections
                
            elif self.model_type == 'yolov8':
                results = self.model(image, conf=conf_threshold, iou=iou_threshold)
                detections = []
                
                for result in results:
                    boxes = result.boxes
                    for box in boxes:
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        class_id = int(box.cls[0])
                        class_name = self.classes[class_id]
                        confidence = float(box.conf[0])
                        
                        detections.append({
                            'bbox': [x1, y1, x2, y2],
                            'class_id': class_id,
                            'class_name': class_name,
                            'confidence': confidence
                        })
                
                # 绘制检测结果
                result_image = self.draw_detections(image, detections)
                return result_image, detections
                
        except Exception as e:
            print(f"检测失败: {e}")
            return image, []
    
    def draw_detections(self, image, detections):
        """在图像上绘制检测结果"""
        if isinstance(image, np.ndarray):
            pil_image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        else:
            pil_image = image.convert('RGB')
        
        draw = ImageDraw.Draw(pil_image)
        
        # 尝试加载字体
        try:
            font = ImageFont.truetype("arial.ttf", 16)
        except:
            font = ImageFont.load_default()
        
        for detection in detections:
            x1, y1, x2, y2 = detection['bbox']
            class_name = detection['class_name']
            confidence = detection['confidence']
            class_id = detection['class_id']
            
            # 获取颜色
            color = tuple(self.colors[class_id].tolist())
            
            # 绘制边界框
            draw.rectangle([x1, y1, x2, y2], outline=color, width=2)
            
            # 绘制标签
            label = f"{class_name}: {confidence:.2f}"
            label_bbox = draw.textbbox((x1, y1), label, font=font)
            draw.rectangle([label_bbox[0], label_bbox[1], label_bbox[2], label_bbox[3]], fill=color)
            draw.text((x1, y1), label, fill=(255, 255, 255), font=font)
        
        return cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)

class DetectionThread(QThread):
    """检测线程"""
    finished = pyqtSignal(object, list)  # 发送检测结果
    progress = pyqtSignal(int)  # 发送进度
    
    def __init__(self, detector, image, conf_threshold, iou_threshold):
        super().__init__()
        self.detector = detector
        self.image = image
        self.conf_threshold = conf_threshold
        self.iou_threshold = iou_threshold
    
    def run(self):
        result_image, detections = self.detector.detect(
            self.image, self.conf_threshold, self.iou_threshold
        )
        self.finished.emit(result_image, detections)

class VideoDetectionThread(QThread):
    """视频检测线程"""
    frame_processed = pyqtSignal(object, list)  # 发送处理后的帧和检测结果
    
    def __init__(self, detector, video_path, conf_threshold, iou_threshold):
        super().__init__()
        self.detector = detector
        self.video_path = video_path
        self.conf_threshold = conf_threshold
        self.iou_threshold = iou_threshold
        self.is_running = True
    
    def run(self):
        cap = cv2.VideoCapture(self.video_path)
        if not cap.isOpened():
            self.frame_processed.emit(None, [])
            return
        
        while self.is_running:
            ret, frame = cap.read()
            if not ret:
                break
            
            # 执行检测
            result_frame, detections = self.detector.detect(
                frame, self.conf_threshold, self.iou_threshold
            )
            
            self.frame_processed.emit(result_frame, detections)
        
        cap.release()
    
    def stop(self):
        self.is_running = False

class CameraDetectionThread(QThread):
    """摄像头检测线程"""
    frame_processed = pyqtSignal(object, list)  # 发送处理后的帧和检测结果
    
    def __init__(self, detector, camera_id, conf_threshold, iou_threshold):
        super().__init__()
        self.detector = detector
        self.camera_id = camera_id
        self.conf_threshold = conf_threshold
        self.iou_threshold = iou_threshold
        self.is_running = True
    
    def run(self):
        cap = cv2.VideoCapture(self.camera_id)
        if not cap.isOpened():
            self.frame_processed.emit(None, [])
            return
        
        while self.is_running:
            ret, frame = cap.read()
            if not ret:
                break
            
            # 执行检测
            result_frame, detections = self.detector.detect(
                frame, self.conf_threshold, self.iou_threshold
            )
            
            self.frame_processed.emit(result_frame, detections)
        
        cap.release()
    
    def stop(self):
        self.is_running = False

class YOLOInferenceTool(QMainWindow):
    """YOLO推理工具主窗口"""
    def __init__(self):
        super().__init__()
        self.detector = YOLODetector()
        self.current_image = None
        self.video_thread = None
        self.camera_thread = None
        
        self.init_ui()
        self.init_model_list()
    
    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("YOLO算法推理工具")
        self.setGeometry(100, 100, 1200, 800)
        
        # 创建中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        main_layout = QHBoxLayout(central_widget)
        
        # 创建左侧控制面板
        control_panel = self.create_control_panel()
        main_layout.addWidget(control_panel, 1)
        
        # 创建右侧显示区域
        display_panel = self.create_display_panel()
        main_layout.addWidget(display_panel, 3)
        
        # 状态栏
        self.statusBar().showMessage("就绪")
    
    def create_control_panel(self):
        """创建控制面板"""
        control_frame = QFrame()
        control_frame.setFrameShape(QFrame.StyledPanel)
        control_layout = QVBoxLayout(control_frame)
        
        # 模型管理组
        model_group = QGroupBox("模型管理")
        model_layout = QVBoxLayout(model_group)
        
        self.model_combo = QComboBox()
        self.model_combo.currentTextChanged.connect(self.on_model_changed)
        model_layout.addWidget(QLabel("选择模型:"))
        model_layout.addWidget(self.model_combo)
        
        self.model_type_combo = QComboBox()
        self.model_type_combo.addItems(['yolov5', 'yolov8'])
        model_layout.addWidget(QLabel("模型类型:"))
        model_layout.addWidget(self.model_type_combo)
        
        load_model_btn = QPushButton("加载自定义模型")
        load_model_btn.clicked.connect(self.load_custom_model)
        model_layout.addWidget(load_model_btn)
        
        control_layout.addWidget(model_group)
        
        # 检测设置组
        settings_group = QGroupBox("检测设置")
        settings_layout = QVBoxLayout(settings_group)
        
        # 置信度阈值
        conf_layout = QHBoxLayout()
        conf_layout.addWidget(QLabel("置信度阈值:"))
        self.conf_spinbox = QDoubleSpinBox()
        self.conf_spinbox.setRange(0.0, 1.0)
        self.conf_spinbox.setValue(0.25)
        self.conf_spinbox.setSingleStep(0.05)
        conf_layout.addWidget(self.conf_spinbox)
        settings_layout.addLayout(conf_layout)
        
        # IOU阈值
        iou_layout = QHBoxLayout()
        iou_layout.addWidget(QLabel("IOU阈值:"))
        self.iou_spinbox = QDoubleSpinBox()
        self.iou_spinbox.setRange(0.0, 1.0)
        self.iou_spinbox.setValue(0.45)
        self.iou_spinbox.setSingleStep(0.05)
        iou_layout.addWidget(self.iou_spinbox)
        settings_layout.addLayout(iou_layout)
        
        control_layout.addWidget(settings_group)
        
        # 输入源组
        input_group = QGroupBox("输入源")
        input_layout = QVBoxLayout(input_group)
        
        image_btn = QPushButton("打开图像")
        image_btn.clicked.connect(self.open_image)
        input_layout.addWidget(image_btn)
        
        video_btn = QPushButton("打开视频")
        video_btn.clicked.connect(self.open_video)
        input_layout.addWidget(video_btn)
        
        camera_btn = QPushButton("打开摄像头")
        camera_btn.clicked.connect(self.open_camera)
        input_layout.addWidget(camera_btn)
        
        control_layout.addWidget(input_group)
        
        # 检测控制组
        detect_group = QGroupBox("检测控制")
        detect_layout = QVBoxLayout(detect_group)
        
        self.detect_btn = QPushButton("开始检测")
        self.detect_btn.clicked.connect(self.start_detection)
        detect_layout.addWidget(self.detect_btn)
        
        self.stop_btn = QPushButton("停止检测")
        self.stop_btn.clicked.connect(self.stop_detection)
        self.stop_btn.setEnabled(False)
        detect_layout.addWidget(self.stop_btn)
        
        control_layout.addWidget(detect_group)
        
        # 结果导出组
        export_group = QGroupBox("结果导出")
        export_layout = QVBoxLayout(export_group)
        
        save_image_btn = QPushButton("保存图像结果")
        save_image_btn.clicked.connect(self.save_image_result)
        export_layout.addWidget(save_image_btn)
        
        save_video_btn = QPushButton("保存视频结果")
        save_video_btn.clicked.connect(self.save_video_result)
        export_layout.addWidget(save_video_btn)
        
        export_report_btn = QPushButton("导出检测报告")
        export_report_btn.clicked.connect(self.export_detection_report)
        export_layout.addWidget(export_report_btn)
        
        control_layout.addWidget(export_group)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        control_layout.addWidget(self.progress_bar)
        
        control_layout.addStretch()
        
        return control_frame
    
    def create_display_panel(self):
        """创建显示面板"""
        display_frame = QFrame()
        display_frame.setFrameShape(QFrame.StyledPanel)
        display_layout = QVBoxLayout(display_frame)
        
        # 创建标签页
        self.tabs = QTabWidget()
        
        # 图像/视频显示标签页
        self.display_tab = QWidget()
        display_tab_layout = QVBoxLayout(self.display_tab)
        
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setMinimumSize(640, 480)
        self.image_label.setText("请选择输入源")
        self.image_label.setStyleSheet("border: 1px solid gray;")
        display_tab_layout.addWidget(self.image_label)
        
        self.tabs.addTab(self.display_tab, "检测结果")
        
        # 检测结果标签页
        self.results_tab = QWidget()
        results_tab_layout = QVBoxLayout(self.results_tab)
        
        self.results_list = QListWidget()
        results_tab_layout.addWidget(self.results_list)
        
        self.tabs.addTab(self.results_tab, "检测详情")
        
        display_layout.addWidget(self.tabs)
        
        # 统计信息
        self.stats_label = QLabel("检测统计: 无")
        self.stats_label.setStyleSheet("font-weight: bold;")
        display_layout.addWidget(self.stats_label)
        
        return display_frame
    
    def init_model_list(self):
        """初始化模型列表"""
        # 添加一些预训练模型选项
        self.model_combo.addItem("yolov5s.pt")
        self.model_combo.addItem("yolov5m.pt")
        self.model_combo.addItem("yolov5l.pt")
        self.model_combo.addItem("yolov5x.pt")
        
        # 尝试加载默认模型
        self.on_model_changed(self.model_combo.currentText())
    
    def on_model_changed(self, model_name):
        """模型选择改变时的回调"""
        if model_name:
            try:
                # 这里应该根据模型名称加载对应的模型文件
                # 简化处理，实际使用时需要根据模型路径加载
                model_path = model_name
                model_type = self.model_type_combo.currentText()
                
                self.detector = YOLODetector(model_path, model_type)
                self.statusBar().showMessage(f"已加载模型: {model_name}")
            except Exception as e:
                QMessageBox.warning(self, "错误", f"加载模型失败: {e}")
    
    def load_custom_model(self):
        """加载自定义模型"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择模型文件", "", "模型文件 (*.pt *.pth)"
        )
        
        if file_path:
            model_name = os.path.basename(file_path)
            self.model_combo.addItem(model_name)
            self.model_combo.setCurrentText(model_name)
    
    def open_image(self):
        """打开图像文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择图像文件", "", "图像文件 (*.jpg *.jpeg *.png *.bmp)"
        )
        
        if file_path:
            self.current_image = cv2.imread(file_path)
            if self.current_image is not None:
                self.display_image(self.current_image)
                self.statusBar().showMessage(f"已加载图像: {file_path}")
            else:
                QMessageBox.warning(self, "错误", "无法加载图像文件")
    
    def open_video(self):
        """打开视频文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择视频文件", "", "视频文件 (*.mp4 *.avi *.mov)"
        )
        
        if file_path:
            self.video_path = file_path
            # 显示视频的第一帧
            cap = cv2.VideoCapture(file_path)
            ret, frame = cap.read()
            if ret:
                self.display_image(frame)
                self.statusBar().showMessage(f"已加载视频: {file_path}")
            cap.release()
    
    def open_camera(self):
        """打开摄像头"""
        self.camera_id = 0  # 默认摄像头
        # 显示摄像头画面
        cap = cv2.VideoCapture(self.camera_id)
        ret, frame = cap.read()
        if ret:
            self.display_image(frame)
            self.statusBar().showMessage(f"已打开摄像头: {self.camera_id}")
        cap.release()
    
    def start_detection(self):
        """开始检测"""
        if self.detector.model is None:
            QMessageBox.warning(self, "错误", "请先加载模型")
            return
        
        conf_threshold = self.conf_spinbox.value()
        iou_threshold = self.iou_spinbox.value()
        
        # 根据当前输入源类型执行不同的检测
        if hasattr(self, 'current_image') and self.current_image is not None:
            # 图像检测
            self.detect_btn.setEnabled(False)
            self.progress_bar.setVisible(True)
            
            self.detection_thread = DetectionThread(
                self.detector, self.current_image, conf_threshold, iou_threshold
            )
            self.detection_thread.finished.connect(self.on_detection_finished)
            self.detection_thread.start()
            
        elif hasattr(self, 'video_path'):
            # 视频检测
            self.detect_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            
            self.video_thread = VideoDetectionThread(
                self.detector, self.video_path, conf_threshold, iou_threshold
            )
            self.video_thread.frame_processed.connect(self.on_video_frame_processed)
            self.video_thread.start()
            
        elif hasattr(self, 'camera_id'):
            # 摄像头检测
            self.detect_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            
            self.camera_thread = CameraDetectionThread(
                self.detector, self.camera_id, conf_threshold, iou_threshold
            )
            self.camera_thread.frame_processed.connect(self.on_camera_frame_processed)
            self.camera_thread.start()
        
        else:
            QMessageBox.warning(self, "错误", "请先选择输入源")
    
    def stop_detection(self):
        """停止检测"""
        if self.video_thread and self.video_thread.isRunning():
            self.video_thread.stop()
            self.video_thread.wait()
        
        if self.camera_thread and self.camera_thread.isRunning():
            self.camera_thread.stop()
            self.camera_thread.wait()
        
        self.detect_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.statusBar().showMessage("检测已停止")
    
    def on_detection_finished(self, result_image, detections):
        """图像检测完成回调"""
        self.detect_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        if result_image is not None:
            self.display_image(result_image)
            self.update_results_list(detections)
            self.update_stats(detections)
            self.statusBar().showMessage("图像检测完成")
        else:
            QMessageBox.warning(self, "错误", "检测失败")
    
    def on_video_frame_processed(self, frame, detections):
        """视频帧处理完成回调"""
        if frame is not None:
            self.display_image(frame)
            self.update_results_list(detections)
            self.update_stats(detections)
    
    def on_camera_frame_processed(self, frame, detections):
        """摄像头帧处理完成回调"""
        if frame is not None:
            self.display_image(frame)
            self.update_results_list(detections)
            self.update_stats(detections)
    
    def display_image(self, image):
        """显示图像"""
        if image is None:
            return
        
        # 调整图像大小以适应显示区域
        h, w = image.shape[:2]
        label_width = self.image_label.width()
        label_height = self.image_label.height()
        
        # 计算缩放比例
        scale = min(label_width / w, label_height / h)
        new_w = int(w * scale)
        new_h = int(h * scale)
        
        # 调整图像大小
        resized_image = cv2.resize(image, (new_w, new_h))
        
        # 转换颜色空间
        rgb_image = cv2.cvtColor(resized_image, cv2.COLOR_BGR2RGB)
        
        # 转换为QImage
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        
        # 显示图像
        self.image_label.setPixmap(QPixmap.fromImage(qt_image))
    
    def update_results_list(self, detections):
        """更新检测结果列表"""
        self.results_list.clear()
        
        for i, detection in enumerate(detections):
            bbox = detection['bbox']
            class_name = detection['class_name']
            confidence = detection['confidence']
            
            item_text = f"{i+1}. {class_name}: {confidence:.2f} [{bbox[0]}, {bbox[1]}, {bbox[2]}, {bbox[3]}]"
            self.results_list.addItem(item_text)
    
    def update_stats(self, detections):
        """更新检测统计信息"""
        if not detections:
            self.stats_label.setText("检测统计: 无检测结果")
            return
        
        # 统计各类别的数量
        class_counts = {}
        for detection in detections:
            class_name = detection['class_name']
            if class_name in class_counts:
                class_counts[class_name] += 1
            else:
                class_counts[class_name] = 1
        
        stats_text = "检测统计: "
        for class_name, count in class_counts.items():
            stats_text += f"{class_name}: {count} "
        
        self.stats_label.setText(stats_text)
    
    def save_image_result(self):
        """保存图像检测结果"""
        if not hasattr(self, 'current_image') or self.current_image is None:
            QMessageBox.warning(self, "错误", "没有可保存的图像结果")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存图像结果", "", "图像文件 (*.jpg *.png)"
        )
        
        if file_path:
            cv2.imwrite(file_path, self.current_image)
            self.statusBar().showMessage(f"图像结果已保存: {file_path}")
    
    def save_video_result(self):
        """保存视频检测结果"""
        QMessageBox.information(self, "提示", "视频保存功能需要额外的实现")
    
    def export_detection_report(self):
        """导出检测报告"""
        QMessageBox.information(self, "提示", "检测报告导出功能需要额外的实现")

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("YOLO推理工具")
    
    window = YOLOInferenceTool()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()