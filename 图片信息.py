#!/usr/bin/env python3
"""
Windows 图片元数据查看器 - PyQt5 图形界面版本
支持元数据读取、显示、编辑和导出功能
"""

import sys
import os
import json
from pathlib import Path
from PIL import Image, ExifTags
from PIL.ExifTags import TAGS, GPSTAGS
import exifread

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QTreeWidget, QTreeWidgetItem, QSplitter,
                            QLabel, QPushButton, QFileDialog, QMessageBox,
                            QTabWidget, QTextEdit, QProgressBar, QStatusBar,
                            QToolBar, QAction, QMenu, QHeaderView, QTableWidget,
                            QTableWidgetItem, QLineEdit, QDialog, QDialogButtonBox,
                            QFormLayout, QGroupBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSettings
from PyQt5.QtGui import QIcon, QFont, QPixmap, QPalette, QColor

class MetadataReader(QThread):
    """元数据读取线程"""
    progress_signal = pyqtSignal(int)
    result_signal = pyqtSignal(dict)
    finished_signal = pyqtSignal()
    
    def __init__(self, file_path):
        super().__init__()
        self.file_path = file_path
        self.metadata = {}
    
    def run(self):
        try:
            self.progress_signal.emit(10)
            self.metadata.update(self.read_file_metadata())
            
            self.progress_signal.emit(40)
            self.metadata.update(self.read_metadata_pil())
            
            self.progress_signal.emit(70)
            self.metadata.update(self.read_metadata_exifread())
            
            self.progress_signal.emit(90)
            self.result_signal.emit(self.metadata)
            
        except Exception as e:
            self.metadata["Error"] = str(e)
            self.result_signal.emit(self.metadata)
        
        self.progress_signal.emit(100)
        self.finished_signal.emit()
    
    def read_file_metadata(self):
        """读取文件系统元数据"""
        metadata = {}
        try:
            path = Path(self.file_path)
            stat = path.stat()
            
            metadata["文件.名称"] = path.name
            metadata["文件.路径"] = str(path.absolute())
            metadata["文件.大小"] = f"{stat.st_size} 字节"
            metadata["文件.创建时间"] = self.format_timestamp(stat.st_ctime)
            metadata["文件.修改时间"] = self.format_timestamp(stat.st_mtime)
            metadata["文件.访问时间"] = self.format_timestamp(stat.st_atime)
            
        except Exception as e:
            metadata["文件系统错误"] = str(e)
        
        return metadata
    
    def read_metadata_pil(self):
        """使用PIL读取元数据"""
        metadata = {}
        try:
            with Image.open(self.file_path) as img:
                # 基本图像信息
                metadata["图像.格式"] = img.format or "未知"
                metadata["图像.模式"] = img.mode
                metadata["图像.尺寸"] = f"{img.width} × {img.height} 像素"
                metadata["图像.色彩模式"] = img.mode
                
                # EXIF数据
                exif_data = img._getexif()
                if exif_data:
                    for tag_id, value in exif_data.items():
                        tag_name = TAGS.get(tag_id, f"未知标签_{tag_id}")
                        # 处理特殊数据类型
                        if isinstance(value, bytes):
                            try:
                                value = value.decode('utf-8', errors='ignore')
                            except:
                                value = str(value)
                        metadata[f"EXIF.{tag_name}"] = str(value)
                
        except Exception as e:
            metadata["PIL错误"] = str(e)
        
        return metadata
    
    def read_metadata_exifread(self):
        """使用exifread读取元数据"""
        metadata = {}
        try:
            with open(self.file_path, 'rb') as f:
                tags = exifread.process_file(f, details=False)
                for tag, value in tags.items():
                    metadata[f"EXIFREAD.{tag}"] = str(value)
        except Exception as e:
            metadata["EXIFREAD错误"] = str(e)
        
        return metadata
    
    def format_timestamp(self, timestamp):
        """格式化时间戳"""
        from datetime import datetime
        return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')

class EditMetadataDialog(QDialog):
    """编辑元数据对话框"""
    def __init__(self, parent=None, key="", value=""):
        super().__init__(parent)
        self.key = key
        self.value = value
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("编辑元数据")
        self.setModal(True)
        self.resize(400, 200)
        
        layout = QFormLayout()
        
        self.key_edit = QLineEdit(self.key)
        self.value_edit = QTextEdit(self.value)
        self.value_edit.setMaximumHeight(100)
        
        layout.addRow("键:", self.key_edit)
        layout.addRow("值:", self.value_edit)
        
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            Qt.Horizontal, self
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        
        layout.addRow(buttons)
        self.setLayout(layout)
    
    def get_data(self):
        return self.key_edit.text(), self.value_edit.toPlainText()

class MetadataViewer(QMainWindow):
    """主窗口类"""
    
    def __init__(self):
        super().__init__()
        self.current_file = None
        self.metadata_reader = None
        self.settings = QSettings("MetaViewer", "ImageMetadataViewer")
        self.init_ui()
        self.load_settings()
    
    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("图片元数据查看器")
        self.setGeometry(100, 100, 1200, 800)
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QVBoxLayout(central_widget)
        
        # 创建工具栏
        self.create_toolbar()
        
        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        
        # 左侧：图片预览和基本信息
        left_widget = self.create_left_panel()
        splitter.addWidget(left_widget)
        
        # 右侧：元数据详情
        right_widget = self.create_right_panel()
        splitter.addWidget(right_widget)
        
        # 设置分割比例
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        
        main_layout.addWidget(splitter)
        
        # 创建状态栏
        self.create_statusbar()
        
        # 应用样式
        self.apply_style()
    
    def create_toolbar(self):
        """创建工具栏"""
        toolbar = QToolBar("主工具栏")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        
        # 打开文件动作
        open_file_action = QAction("打开文件", self)
        open_file_action.setShortcut("Ctrl+O")
        open_file_action.triggered.connect(self.open_file)
        toolbar.addAction(open_file_action)
        
        # 打开文件夹动作
        open_folder_action = QAction("打开文件夹", self)
        open_folder_action.setShortcut("Ctrl+D")
        open_folder_action.triggered.connect(self.open_folder)
        toolbar.addAction(open_folder_action)
        
        toolbar.addSeparator()
        
        # 导出动作
        export_action = QAction("导出元数据", self)
        export_action.setShortcut("Ctrl+E")
        export_action.triggered.connect(self.export_metadata)
        toolbar.addAction(export_action)
        
        # 刷新动作
        refresh_action = QAction("刷新", self)
        refresh_action.setShortcut("F5")
        refresh_action.triggered.connect(self.refresh_metadata)
        toolbar.addAction(refresh_action)
        
        toolbar.addSeparator()
        
        # 编辑动作
        edit_action = QAction("编辑元数据", self)
        edit_action.setShortcut("Ctrl+M")
        edit_action.triggered.connect(self.edit_metadata)
        toolbar.addAction(edit_action)
    
    def create_left_panel(self):
        """创建左侧面板"""
        left_widget = QWidget()
        layout = QVBoxLayout(left_widget)
        
        # 图片预览
        preview_group = QGroupBox("图片预览")
        preview_layout = QVBoxLayout(preview_group)
        
        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setMinimumHeight(300)
        self.preview_label.setStyleSheet("""
            QLabel {
                border: 2px solid #cccccc;
                border-radius: 5px;
                background-color: #f8f8f8;
            }
        """)
        self.preview_label.setText("请选择图片文件")
        preview_layout.addWidget(self.preview_label)
        
        # 基本信息
        info_group = QGroupBox("基本信息")
        info_layout = QVBoxLayout(info_group)
        
        self.info_text = QTextEdit()
        self.info_text.setMaximumHeight(200)
        self.info_text.setReadOnly(True)
        info_layout.addWidget(self.info_text)
        
        layout.addWidget(preview_group)
        layout.addWidget(info_group)
        
        return left_widget
    
    def create_right_panel(self):
        """创建右侧面板"""
        right_widget = QWidget()
        layout = QVBoxLayout(right_widget)
        
        # 创建标签页
        self.tab_widget = QTabWidget()
        
        # 树形视图标签页
        self.tree_tab = QWidget()
        tree_layout = QVBoxLayout(self.tree_tab)
        
        self.metadata_tree = QTreeWidget()
        self.metadata_tree.setHeaderLabels(["属性", "值"])
        self.metadata_tree.setAlternatingRowColors(True)
        self.metadata_tree.header().setSectionResizeMode(QHeaderView.Interactive)
        self.metadata_tree.itemDoubleClicked.connect(self.on_item_double_clicked)
        
        tree_layout.addWidget(self.metadata_tree)
        
        # 表格视图标签页
        self.table_tab = QWidget()
        table_layout = QVBoxLayout(self.table_tab)
        
        self.metadata_table = QTableWidget()
        self.metadata_table.setColumnCount(2)
        self.metadata_table.setHorizontalHeaderLabels(["属性", "值"])
        self.metadata_table.horizontalHeader().setStretchLastSection(True)
        self.metadata_table.setAlternatingRowColors(True)
        self.metadata_table.setEditTriggers(QTableWidget.NoEditTriggers)
        
        table_layout.addWidget(self.metadata_table)
        
        # 原始数据标签页
        self.raw_tab = QWidget()
        raw_layout = QVBoxLayout(self.raw_tab)
        
        self.raw_text = QTextEdit()
        self.raw_text.setReadOnly(True)
        raw_layout.addWidget(self.raw_text)
        
        # 添加标签页
        self.tab_widget.addTab(self.tree_tab, "树形视图")
        self.tab_widget.addTab(self.table_tab, "表格视图")
        self.tab_widget.addTab(self.raw_tab, "原始数据")
        
        layout.addWidget(self.tab_widget)
        
        return right_widget
    
    def create_statusbar(self):
        """创建状态栏"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(200)
        self.progress_bar.setVisible(False)
        
        self.status_bar.addPermanentWidget(self.progress_bar)
        self.status_bar.showMessage("就绪")
    
    def apply_style(self):
        """应用样式表"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f0f0f0;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #cccccc;
                border-radius: 5px;
                margin-top: 1ex;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QTreeWidget, QTableWidget, QTextEdit {
                border: 1px solid #cccccc;
                border-radius: 3px;
                background-color: white;
            }
            QTabWidget::pane {
                border: 1px solid #cccccc;
                background-color: white;
            }
            QTabBar::tab {
                background-color: #e0e0e0;
                padding: 8px 12px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background-color: white;
                border-bottom: 2px solid #0078d7;
            }
        """)
    
    def open_file(self):
        """打开单个文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择图片文件",
            self.settings.value("last_directory", ""),
            "图片文件 (*.jpg *.jpeg *.png *.tiff *.tif *.webp *.bmp);;所有文件 (*.*)"
        )
        
        if file_path:
            self.settings.setValue("last_directory", str(Path(file_path).parent))
            self.load_file(file_path)
    
    def open_folder(self):
        """打开文件夹"""
        folder_path = QFileDialog.getExistingDirectory(
            self,
            "选择图片文件夹",
            self.settings.value("last_directory", "")
        )
        
        if folder_path:
            self.settings.setValue("last_directory", folder_path)
            # 这里可以扩展为文件夹批量处理
            QMessageBox.information(self, "提示", "文件夹批量处理功能正在开发中")
    
    def load_file(self, file_path):
        """加载文件并读取元数据"""
        self.current_file = file_path
        self.setWindowTitle(f"图片元数据查看器 - {Path(file_path).name}")
        
        # 显示图片预览
        self.show_preview(file_path)
        
        # 开始读取元数据
        self.start_metadata_reading(file_path)
    
    def show_preview(self, file_path):
        """显示图片预览"""
        try:
            pixmap = QPixmap(file_path)
            if not pixmap.isNull():
                # 缩放图片以适应预览区域
                scaled_pixmap = pixmap.scaled(
                    self.preview_label.width() - 20,
                    self.preview_label.height() - 20,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
                self.preview_label.setPixmap(scaled_pixmap)
            else:
                self.preview_label.setText("无法预览此图片格式")
        except Exception as e:
            self.preview_label.setText(f"预览错误: {str(e)}")
    
    def start_metadata_reading(self, file_path):
        """开始读取元数据"""
        self.status_bar.showMessage("正在读取元数据...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # 如果已有读取线程在运行，先停止
        if self.metadata_reader and self.metadata_reader.isRunning():
            self.metadata_reader.terminate()
            self.metadata_reader.wait()
        
        # 创建新的读取线程
        self.metadata_reader = MetadataReader(file_path)
        self.metadata_reader.progress_signal.connect(self.update_progress)
        self.metadata_reader.result_signal.connect(self.display_metadata)
        self.metadata_reader.finished_signal.connect(self.on_reading_finished)
        self.metadata_reader.start()
    
    def update_progress(self, value):
        """更新进度条"""
        self.progress_bar.setValue(value)
    
    def display_metadata(self, metadata):
        """显示元数据"""
        self.metadata = metadata
        
        # 更新基本信息
        self.update_basic_info(metadata)
        
        # 更新树形视图
        self.update_tree_view(metadata)
        
        # 更新表格视图
        self.update_table_view(metadata)
        
        # 更新原始数据视图
        self.update_raw_view(metadata)
    
    def update_basic_info(self, metadata):
        """更新基本信息显示"""
        basic_info = []
        basic_keys = [
            "文件.名称", "文件.大小", "文件.修改时间",
            "图像.格式", "图像.尺寸", "图像.色彩模式"
        ]
        
        for key in basic_keys:
            if key in metadata:
                basic_info.append(f"{key}: {metadata[key]}")
        
        self.info_text.setText("\n".join(basic_info))
    
    def update_tree_view(self, metadata):
        """更新树形视图"""
        self.metadata_tree.clear()
        
        # 按类别分组
        categories = {}
        for key, value in metadata.items():
            if '.' in key:
                category, subkey = key.split('.', 1)
            else:
                category = "其他"
                subkey = key
            
            if category not in categories:
                categories[category] = {}
            categories[category][subkey] = value
        
        # 创建树形结构
        for category, items in categories.items():
            category_item = QTreeWidgetItem(self.metadata_tree, [category, ""])
            for key, value in items.items():
                item = QTreeWidgetItem(category_item, [key, str(value)])
                category_item.addChild(item)
            
            category_item.setExpanded(True)
        
        self.metadata_tree.resizeColumnToContents(0)
    
    def update_table_view(self, metadata):
        """更新表格视图"""
        self.metadata_table.setRowCount(len(metadata))
        
        for i, (key, value) in enumerate(metadata.items()):
            self.metadata_table.setItem(i, 0, QTableWidgetItem(key))
            self.metadata_table.setItem(i, 1, QTableWidgetItem(str(value)))
        
        self.metadata_table.resizeColumnsToContents()
    
    def update_raw_view(self, metadata):
        """更新原始数据视图"""
        raw_text = json.dumps(metadata, indent=2, ensure_ascii=False)
        self.raw_text.setText(raw_text)
    
    def on_reading_finished(self):
        """元数据读取完成"""
        self.progress_bar.setVisible(False)
        self.status_bar.showMessage("元数据读取完成")
    
    def refresh_metadata(self):
        """刷新元数据"""
        if self.current_file:
            self.load_file(self.current_file)
    
    def export_metadata(self):
        """导出元数据"""
        if not hasattr(self, 'metadata') or not self.metadata:
            QMessageBox.warning(self, "警告", "没有可导出的元数据")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出元数据",
            f"{Path(self.current_file).stem}_metadata.json",
            "JSON文件 (*.json);;文本文件 (*.txt);;所有文件 (*.*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(self.metadata, f, indent=2, ensure_ascii=False)
                QMessageBox.information(self, "成功", f"元数据已导出到: {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导出失败: {str(e)}")
    
    def edit_metadata(self):
        """编辑元数据"""
        if not hasattr(self, 'metadata') or not self.metadata:
            QMessageBox.warning(self, "警告", "没有可编辑的元数据")
            return
        
        # 获取当前选中的项目
        current_item = self.metadata_tree.currentItem()
        if current_item and current_item.parent():
            key = f"{current_item.parent().text(0)}.{current_item.text(0)}"
            value = current_item.text(1)
        else:
            key = ""
            value = ""
        
        dialog = EditMetadataDialog(self, key, value)
        if dialog.exec_() == QDialog.Accepted:
            new_key, new_value = dialog.get_data()
            if new_key and new_key in self.metadata:
                self.metadata[new_key] = new_value
                self.refresh_metadata()
                QMessageBox.information(self, "成功", "元数据已更新（注意：这仅更新显示，实际文件需要额外工具保存）")
    
    def on_item_double_clicked(self, item, column):
        """双击项目事件"""
        if item and item.parent():
            self.edit_metadata()
    
    def load_settings(self):
        """加载设置"""
        geometry = self.settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
        
        state = self.settings.value("window_state")
        if state:
            self.restoreState(state)
    
    def closeEvent(self, event):
        """关闭事件"""
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("window_state", self.saveState())
        event.accept()

def main():
    """主函数"""
    app = QApplication(sys.argv)
    app.setApplicationName("图片元数据查看器")
    app.setApplicationVersion("1.0")
    
    # 设置应用程序样式
    app.setStyle('Fusion')
    
    viewer = MetadataViewer()
    viewer.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()