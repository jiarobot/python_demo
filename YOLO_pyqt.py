import sys
import os
import yaml
from pathlib import Path
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QPushButton, QComboBox, QLineEdit, QTextEdit, 
                             QTabWidget, QFileDialog, QMessageBox, QProgressBar, QGroupBox,
                             QListWidget, QSpinBox, QDoubleSpinBox, QCheckBox)
from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PyQt5.QtGui import QPixmap, QImage
import cv2
from ultralytics import YOLO
import torch
from sklearn.model_selection import KFold
import pandas as pd
from collections import Counter

class YOLOTrainingThread(QThread):
    """用于在后台线程中运行YOLO训练，避免界面卡顿"""
    progress_update = pyqtSignal(str)
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, model, data_cfg, epochs, batch_size, device, project_dir):
        super().__init__()
        self.model = model
        self.data_cfg = data_cfg
        self.epochs = epochs
        self.batch_size = batch_size
        self.device = device
        self.project_dir = project_dir

    def run(self):
        try:
            self.progress_update.emit("Starting YOLO training...")
            # 直接使用YOLO的train方法
            results = self.model.train(
                data=self.data_cfg,
                epochs=self.epochs,
                batch=self.batch_size,
                device=self.device,
                project=self.project_dir,
                exist_ok=True
            )
            self.progress_update.emit("Training completed successfully!")
            self.finished_signal.emit(True, "Training completed")
        except Exception as e:
            self.progress_update.emit(f"Training error: {str(e)}")
            self.finished_signal.emit(False, str(e))

class YOLOPredictionThread(QThread):
    """用于在后台线程中运行YOLO预测"""
    progress_update = pyqtSignal(str)
    image_result = pyqtSignal(QImage)
    finished_signal = pyqtSignal()

    def __init__(self, model_path, source, conf_threshold=0.25):
        super().__init__()
        self.model_path = model_path
        self.source = source
        self.conf_threshold = conf_threshold
        self.is_running = True

    def run(self):
        try:
            model = YOLO(self.model_path)
            results = model(self.source, stream=True, conf=self.conf_threshold)
            
            for result in results:
                if not self.is_running:
                    break
                # 将结果图像转换为QImage用于显示
                plot_result = result.plot()
                plot_result_rgb = cv2.cvtColor(plot_result, cv2.COLOR_BGR2RGB)
                h, w, ch = plot_result_rgb.shape
                bytes_per_line = ch * w
                qt_image = QImage(plot_result_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
                self.image_result.emit(qt_image)
                
            self.finished_signal.emit()
        except Exception as e:
            self.progress_update.emit(f"Prediction error: {str(e)}")

    def stop(self):
        self.is_running = False

class YOLOAITool(QMainWindow):
    def __init__(self):
        super().__init__()
        self.model = None
        self.current_project_dir = ""
        self.prediction_thread = None
        self.initUI()

    def initUI(self):
        self.setWindowTitle('YOLO AI 全流程工具')
        self.setGeometry(100, 100, 1200, 800)

        # 创建主选项卡
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # 初始化各个功能选项卡
        self.setup_data_tab()
        self.setup_train_tab()
        self.setup_eval_tab()
        self.setup_predict_tab()
        self.setup_advanced_tab()

        # 状态栏
        self.statusBar().showMessage('就绪')

    def setup_data_tab(self):
        """设置数据管理选项卡"""
        data_tab = QWidget()
        layout = QVBoxLayout()

        # 项目设置
        project_group = QGroupBox("项目设置")
        project_layout = QHBoxLayout()
        self.project_path_edit = QLineEdit()
        self.project_path_edit.setPlaceholderText("选择项目目录...")
        browse_project_btn = QPushButton("浏览")
        browse_project_btn.clicked.connect(self.browse_project_dir)
        create_project_btn = QPushButton("创建项目结构")
        create_project_btn.clicked.connect(self.create_project_structure)
        project_layout.addWidget(QLabel("项目目录:"))
        project_layout.addWidget(self.project_path_edit)
        project_layout.addWidget(browse_project_btn)
        project_layout.addWidget(create_project_btn)
        project_group.setLayout(project_layout)
        layout.addWidget(project_group)

        # 数据集操作
        data_ops_group = QGroupBox("数据集操作")
        data_ops_layout = QVBoxLayout()
        
        # 数据集分割
        split_layout = QHBoxLayout()
        self.train_ratio_edit = QLineEdit("70")
        self.val_ratio_edit = QLineEdit("20")
        self.test_ratio_edit = QLineEdit("10")
        split_dataset_btn = QPushButton("分割数据集")
        split_dataset_btn.clicked.connect(self.split_dataset)
        split_layout.addWidget(QLabel("训练集(%):"))
        split_layout.addWidget(self.train_ratio_edit)
        split_layout.addWidget(QLabel("验证集(%):"))
        split_layout.addWidget(self.val_ratio_edit)
        split_layout.addWidget(QLabel("测试集(%):"))
        split_layout.addWidget(self.test_ratio_edit)
        split_layout.addWidget(split_dataset_btn)
        data_ops_layout.addLayout(split_layout)

        # 格式转换
        convert_layout = QHBoxLayout()
        xml_to_txt_btn = QPushButton("XML转TXT格式")
        xml_to_txt_btn.clicked.connect(self.convert_xml_to_txt)
        convert_layout.addWidget(xml_to_txt_btn)
        data_ops_layout.addLayout(convert_layout)

        data_ops_group.setLayout(data_ops_layout)
        layout.addWidget(data_ops_group)

        # 数据预览
        preview_group = QGroupBox("数据预览")
        preview_layout = QVBoxLayout()
        self.data_list = QListWidget()
        preview_layout.addWidget(self.data_list)
        preview_group.setLayout(preview_layout)
        layout.addWidget(preview_group)

        data_tab.setLayout(layout)
        self.tabs.addTab(data_tab, "数据管理")

    def setup_train_tab(self):
        """设置训练选项卡"""
        train_tab = QWidget()
        layout = QVBoxLayout()

        # 模型选择
        model_group = QGroupBox("模型配置")
        model_layout = QHBoxLayout()
        self.model_type_combo = QComboBox()
        self.model_type_combo.addItems(["yolov8n", "yolov8s", "yolov8m", "yolov8l", "yolov8x"])
        self.pretrained_check = QCheckBox("使用预训练权重")
        self.pretrained_check.setChecked(True)
        model_layout.addWidget(QLabel("模型类型:"))
        model_layout.addWidget(self.model_type_combo)
        model_layout.addWidget(self.pretrained_check)
        model_group.setLayout(model_layout)
        layout.addWidget(model_group)

        # 训练参数
        params_group = QGroupBox("训练参数")
        params_layout = QVBoxLayout()
        
        epochs_layout = QHBoxLayout()
        self.epochs_spin = QSpinBox()
        self.epochs_spin.setRange(1, 1000)
        self.epochs_spin.setValue(100)
        epochs_layout.addWidget(QLabel("训练轮次:"))
        epochs_layout.addWidget(self.epochs_spin)
        params_layout.addLayout(epochs_layout)
        
        batch_layout = QHBoxLayout()
        self.batch_spin = QSpinBox()
        self.batch_spin.setRange(1, 128)
        self.batch_spin.setValue(16)
        batch_layout.addWidget(QLabel("批次大小:"))
        batch_layout.addWidget(self.batch_spin)
        params_layout.addLayout(batch_layout)
        
        device_layout = QHBoxLayout()
        self.device_combo = QComboBox()
        self.device_combo.addItems(["cpu", "cuda:0", "cuda:1"])
        device_layout.addWidget(QLabel("训练设备:"))
        device_layout.addWidget(self.device_combo)
        params_layout.addLayout(device_layout)

        params_group.setLayout(params_layout)
        layout.addWidget(params_group)

        # 数据配置
        data_config_group = QGroupBox("数据配置")
        data_config_layout = QHBoxLayout()
        self.data_yaml_edit = QLineEdit()
        self.data_yaml_edit.setPlaceholderText("data.yaml路径...")
        browse_data_btn = QPushButton("浏览")
        browse_data_btn.clicked.connect(self.browse_data_yaml)
        data_config_layout.addWidget(QLabel("数据配置文件:"))
        data_config_layout.addWidget(self.data_yaml_edit)
        data_config_layout.addWidget(browse_data_btn)
        data_config_group.setLayout(data_config_layout)
        layout.addWidget(data_config_group)

        # 训练控制
        train_control_group = QGroupBox("训练控制")
        train_control_layout = QVBoxLayout()
        
        self.train_progress = QProgressBar()
        self.train_log = QTextEdit()
        self.train_log.setMaximumHeight(150)
        
        button_layout = QHBoxLayout()
        start_train_btn = QPushButton("开始训练")
        start_train_btn.clicked.connect(self.start_training)
        stop_train_btn = QPushButton("停止训练")
        stop_train_btn.clicked.connect(self.stop_training)
        button_layout.addWidget(start_train_btn)
        button_layout.addWidget(stop_train_btn)
        
        train_control_layout.addWidget(self.train_progress)
        train_control_layout.addWidget(self.train_log)
        train_control_layout.addLayout(button_layout)
        train_control_group.setLayout(train_control_layout)
        layout.addWidget(train_control_group)

        train_tab.setLayout(layout)
        self.tabs.addTab(train_tab, "模型训练")

    def setup_eval_tab(self):
        """设置评估选项卡"""
        eval_tab = QWidget()
        layout = QVBoxLayout()

        # 模型选择评估
        model_select_group = QGroupBox("模型选择")
        model_select_layout = QHBoxLayout()
        self.eval_model_path = QLineEdit()
        self.eval_model_path.setPlaceholderText("选择模型权重文件...")
        browse_eval_model_btn = QPushButton("浏览")
        browse_eval_model_btn.clicked.connect(self.browse_eval_model)
        model_select_layout.addWidget(QLabel("模型文件:"))
        model_select_layout.addWidget(self.eval_model_path)
        model_select_layout.addWidget(browse_eval_model_btn)
        model_select_group.setLayout(model_select_layout)
        layout.addWidget(model_select_group)

        # 评估按钮
        eval_btn = QPushButton("开始评估")
        eval_btn.clicked.connect(self.start_evaluation)
        layout.addWidget(eval_btn)

        # 评估结果显示
        self.eval_results = QTextEdit()
        layout.addWidget(self.eval_results)

        eval_tab.setLayout(layout)
        self.tabs.addTab(eval_tab, "模型评估")

    def setup_predict_tab(self):
        """设置预测选项卡"""
        predict_tab = QWidget()
        layout = QVBoxLayout()

        # 预测配置
        predict_config_group = QGroupBox("预测配置")
        predict_config_layout = QVBoxLayout()
        
        # 模型选择
        model_layout = QHBoxLayout()
        self.predict_model_path = QLineEdit()
        self.predict_model_path.setPlaceholderText("选择模型权重文件...")
        browse_predict_model_btn = QPushButton("浏览")
        browse_predict_model_btn.clicked.connect(self.browse_predict_model)
        model_layout.addWidget(QLabel("模型文件:"))
        model_layout.addWidget(self.predict_model_path)
        model_layout.addWidget(browse_predict_model_btn)
        predict_config_layout.addLayout(model_layout)
        
        # 置信度阈值
        conf_layout = QHBoxLayout()
        self.conf_threshold = QDoubleSpinBox()
        self.conf_threshold.setRange(0.01, 1.0)
        self.conf_threshold.setValue(0.25)
        self.conf_threshold.setSingleStep(0.05)
        conf_layout.addWidget(QLabel("置信度阈值:"))
        conf_layout.addWidget(self.conf_threshold)
        predict_config_layout.addLayout(conf_layout)
        
        predict_config_group.setLayout(predict_config_layout)
        layout.addWidget(predict_config_group)

        # 预测源选择
        source_group = QGroupBox("预测源")
        source_layout = QHBoxLayout()
        image_btn = QPushButton("图像")
        image_btn.clicked.connect(lambda: self.select_source('image'))
        video_btn = QPushButton("视频")
        video_btn.clicked.connect(lambda: self.select_source('video'))
        camera_btn = QPushButton("摄像头")
        camera_btn.clicked.connect(lambda: self.select_source('camera'))
        stop_btn = QPushButton("停止预测")
        stop_btn.clicked.connect(self.stop_prediction)
        source_layout.addWidget(image_btn)
        source_layout.addWidget(video_btn)
        source_layout.addWidget(camera_btn)
        source_layout.addWidget(stop_btn)
        source_group.setLayout(source_layout)
        layout.addWidget(source_group)

        # 结果显示
        result_group = QGroupBox("预测结果")
        result_layout = QVBoxLayout()
        self.result_label = QLabel()
        self.result_label.setAlignment(Qt.AlignCenter)
        self.result_label.setMinimumSize(640, 480)
        self.result_label.setText("预测结果将显示在这里")
        result_layout.addWidget(self.result_label)
        result_group.setLayout(result_layout)
        layout.addWidget(result_group)

        predict_tab.setLayout(layout)
        self.tabs.addTab(predict_tab, "模型预测")

    def setup_advanced_tab(self):
        """设置高级功能选项卡"""
        advanced_tab = QWidget()
        layout = QVBoxLayout()

        # K折交叉验证
        kfold_group = QGroupBox("K折交叉验证")
        kfold_layout = QVBoxLayout()
        
        k_config_layout = QHBoxLayout()
        self.k_folds = QSpinBox()
        self.k_folds.setRange(2, 10)
        self.k_folds.setValue(5)
        k_config_layout.addWidget(QLabel("折数:"))
        k_config_layout.addWidget(self.k_folds)
        kfold_layout.addLayout(k_config_layout)
        
        start_kfold_btn = QPushButton("开始K折交叉验证")
        start_kfold_btn.clicked.connect(self.start_kfold_validation)
        kfold_layout.addWidget(start_kfold_btn)
        
        self.kfold_results = QTextEdit()
        self.kfold_results.setMaximumHeight(200)
        kfold_layout.addWidget(self.kfold_results)
        
        kfold_group.setLayout(kfold_layout)
        layout.addWidget(kfold_group)

        # 模型导出
        export_group = QGroupBox("模型导出")
        export_layout = QVBoxLayout()
        
        export_config_layout = QHBoxLayout()
        self.export_model_path = QLineEdit()
        self.export_model_path.setPlaceholderText("选择要导出的模型...")
        browse_export_btn = QPushButton("浏览")
        browse_export_btn.clicked.connect(self.browse_export_model)
        export_config_layout.addWidget(QLabel("模型文件:"))
        export_config_layout.addWidget(self.export_model_path)
        export_config_layout.addWidget(browse_export_btn)
        export_layout.addLayout(export_config_layout)
        
        format_layout = QHBoxLayout()
        self.export_format = QComboBox()
        self.export_format.addItems(["onnx", "torchscript", "tensorrt"])
        export_btn = QPushButton("导出模型")
        export_btn.clicked.connect(self.export_model)
        format_layout.addWidget(QLabel("导出格式:"))
        format_layout.addWidget(self.export_format)
        format_layout.addWidget(export_btn)
        export_layout.addLayout(format_layout)
        
        export_group.setLayout(export_layout)
        layout.addWidget(export_group)

        advanced_tab.setLayout(layout)
        self.tabs.addTab(advanced_tab, "高级功能")

    # 以下是各个按钮的槽函数实现
    def browse_project_dir(self):
        dir_path = QFileDialog.getExistingDirectory(self, "选择项目目录")
        if dir_path:
            self.project_path_edit.setText(dir_path)
            self.current_project_dir = dir_path

    def create_project_structure(self):
        project_dir = self.project_path_edit.text()
        if not project_dir:
            QMessageBox.warning(self, "警告", "请先选择项目目录")
            return
        
        # 创建YOLO标准数据集目录结构[citation:5]
        dirs = [
            "images/train",
            "images/val", 
            "images/test",
            "labels/train",
            "labels/val",
            "labels/test",
            "models",
            "configs"
        ]
        
        for dir_name in dirs:
            os.makedirs(os.path.join(project_dir, dir_name), exist_ok=True)
        
        # 创建默认的data.yaml文件
        data_yaml = {
            'path': project_dir,
            'train': 'images/train',
            'val': 'images/val',
            'test': 'images/test',
            'names': {0: 'object'}
        }
        
        with open(os.path.join(project_dir, 'data.yaml'), 'w') as f:
            yaml.dump(data_yaml, f)
        
        QMessageBox.information(self, "成功", "项目结构创建成功！")

    def split_dataset(self):
        # 实现数据集分割逻辑[citation:3]
        QMessageBox.information(self, "信息", "数据集分割功能待实现")

    def convert_xml_to_txt(self):
        # 实现XML到TXT格式转换[citation:3]
        QMessageBox.information(self, "信息", "格式转换功能待实现")

    def browse_data_yaml(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "选择data.yaml文件", "", "YAML Files (*.yaml *.yml)")
        if file_path:
            self.data_yaml_edit.setText(file_path)

    def start_training(self):
        if not self.data_yaml_edit.text() or not os.path.exists(self.data_yaml_edit.text()):
            QMessageBox.warning(self, "警告", "请选择有效的数据配置文件")
            return
        
        # 获取训练参数
        model_type = self.model_type_combo.currentText()
        use_pretrained = self.pretrained_check.isChecked()
        epochs = self.epochs_spin.value()
        batch_size = self.batch_spin.value()
        device = self.device_combo.currentText()
        
        # 初始化模型[citation:1]
        if use_pretrained:
            self.model = YOLO(f"{model_type}.pt")
        else:
            self.model = YOLO(f"{model_type}.yaml")
        
        # 在后台线程中开始训练
        project_dir = self.current_project_dir if self.current_project_dir else "runs/detect"
        self.training_thread = YOLOTrainingThread(
            self.model, 
            self.data_yaml_edit.text(),
            epochs,
            batch_size,
            device,
            project_dir
        )
        self.training_thread.progress_update.connect(self.update_train_log)
        self.training_thread.finished_signal.connect(self.training_finished)
        self.training_thread.start()
        
        self.train_progress.setRange(0, 0)  # 无限进度条

    def stop_training(self):
        # 停止训练逻辑
        if hasattr(self, 'training_thread') and self.training_thread.isRunning():
            self.training_thread.terminate()
            self.train_log.append("训练已停止")

    def update_train_log(self, message):
        self.train_log.append(message)
        self.statusBar().showMessage(message)

    def training_finished(self, success, message):
        self.train_progress.setRange(0, 100)
        self.train_progress.setValue(100)
        if success:
            QMessageBox.information(self, "成功", "训练完成！")
        else:
            QMessageBox.warning(self, "错误", f"训练失败: {message}")

    def browse_eval_model(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "选择模型文件", "", "Model Files (*.pt)")
        if file_path:
            self.eval_model_path.setText(file_path)

    def start_evaluation(self):
        model_path = self.eval_model_path.text()
        if not model_path or not os.path.exists(model_path):
            QMessageBox.warning(self, "警告", "请选择有效的模型文件")
            return
        
        try:
            model = YOLO(model_path)
            # 这里需要根据数据集进行验证[citation:1]
            results = model.val()
            self.eval_results.setText(f"""
            验证结果:
            mAP50: {results.box.map50:.4f}
            mAP50-95: {results.box.map:.4f}
            精确度: {results.box.mp:.4f}
            召回率: {results.box.mr:.4f}
            """)
        except Exception as e:
            QMessageBox.warning(self, "错误", f"验证失败: {str(e)}")

    def browse_predict_model(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "选择模型文件", "", "Model Files (*.pt)")
        if file_path:
            self.predict_model_path.setText(file_path)

    def select_source(self, source_type):
        if self.prediction_thread and self.prediction_thread.isRunning():
            self.prediction_thread.stop()
        
        model_path = self.predict_model_path.text()
        if not model_path or not os.path.exists(model_path):
            QMessageBox.warning(self, "警告", "请选择有效的模型文件")
            return
        
        if source_type == 'image':
            file_path, _ = QFileDialog.getOpenFileName(self, "选择图像", "", "Image Files (*.jpg *.png *.jpeg)")
            if file_path:
                self.start_prediction(model_path, file_path)
        elif source_type == 'video':
            file_path, _ = QFileDialog.getOpenFileName(self, "选择视频", "", "Video Files (*.mp4 *.avi *.mov)")
            if file_path:
                self.start_prediction(model_path, file_path)
        elif source_type == 'camera':
            self.start_prediction(model_path, 0)  # 0 表示默认摄像头

    def start_prediction(self, model_path, source):
        self.prediction_thread = YOLOPredictionThread(
            model_path, 
            source, 
            self.conf_threshold.value()
        )
        self.prediction_thread.image_result.connect(self.update_prediction_result)
        self.prediction_thread.progress_update.connect(self.statusBar().showMessage)
        self.prediction_thread.finished_signal.connect(self.prediction_finished)
        self.prediction_thread.start()

    def update_prediction_result(self, image):
        pixmap = QPixmap.fromImage(image)
        self.result_label.setPixmap(pixmap.scaled(
            self.result_label.width(), 
            self.result_label.height(),
            Qt.KeepAspectRatio
        ))

    def stop_prediction(self):
        if self.prediction_thread and self.prediction_thread.isRunning():
            self.prediction_thread.stop()

    def prediction_finished(self):
        self.statusBar().showMessage("预测完成")

    def start_kfold_validation(self):
        # 实现K折交叉验证[citation:2]
        QMessageBox.information(self, "信息", "K折交叉验证功能待实现")

    def browse_export_model(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "选择要导出的模型", "", "Model Files (*.pt)")
        if file_path:
            self.export_model_path.setText(file_path)

    def export_model(self):
        model_path = self.export_model_path.text()
        if not model_path or not os.path.exists(model_path):
            QMessageBox.warning(self, "警告", "请选择有效的模型文件")
            return
        
        try:
            model = YOLO(model_path)
            export_format = self.export_format.currentText()
            model.export(format=export_format)
            QMessageBox.information(self, "成功", f"模型已导出为 {export_format.upper()} 格式")
        except Exception as e:
            QMessageBox.warning(self, "错误", f"导出失败: {str(e)}")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = YOLOAITool()
    window.show()
    sys.exit(app.exec_())