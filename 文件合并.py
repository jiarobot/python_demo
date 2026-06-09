import os
import sys
import hashlib
import chardet
import json
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QListWidget, QFileDialog, QLabel, QMessageBox,
                             QProgressBar, QTextEdit, QComboBox, QCheckBox, QSplitter,
                             QGroupBox, QLineEdit, QTabWidget, QListWidgetItem, QTreeWidget,
                             QTreeWidgetItem, QHeaderView, QToolBar, QAction, QStatusBar,
                             QDialog, QDialogButtonBox, QFormLayout, QSpinBox, QFontComboBox,
                             QTextBrowser, QMenu, QInputDialog, QToolButton, QSizePolicy)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSettings, QSize, QTimer, QMimeData
from PyQt5.QtGui import QFont, QIcon, QPalette, QColor, QTextCursor, QDragEnterEvent, QDropEvent
import logging
import csv
import pandas as pd
from PIL import Image
import fitz  # PyMuPDF for PDF handling

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SettingsDialog(QDialog):
    """设置对话框"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置")
        self.setModal(True)
        self.resize(500, 400)
        
        self.settings = QSettings("AdvancedFileMerger", "Settings")
        
        self.init_ui()
        self.load_settings()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # 创建选项卡
        tabs = QTabWidget()
        layout.addWidget(tabs)
        
        # 常规设置
        general_tab = QWidget()
        general_layout = QFormLayout(general_tab)
        
        self.default_output_dir = QLineEdit()
        self.browse_dir_btn = QPushButton("浏览...")
        self.browse_dir_btn.clicked.connect(self.browse_output_dir)
        dir_layout = QHBoxLayout()
        dir_layout.addWidget(self.default_output_dir)
        dir_layout.addWidget(self.browse_dir_btn)
        general_layout.addRow("默认输出目录:", dir_layout)
        
        self.auto_detect_encoding = QCheckBox("自动检测文件编码")
        general_layout.addRow("编码检测:", self.auto_detect_encoding)
        
        self.remember_window_size = QCheckBox("记住窗口大小和位置")
        general_layout.addRow("窗口设置:", self.remember_window_size)
        
        tabs.addTab(general_tab, "常规")
        
        # 文本合并设置
        text_tab = QWidget()
        text_layout = QFormLayout(text_tab)
        
        self.default_separator = QLineEdit()
        text_layout.addRow("默认分隔符:", self.default_separator)
        
        self.add_file_info = QCheckBox("在分隔符中包含文件信息")
        text_layout.addRow("文件信息:", self.add_file_info)
        
        self.preserve_empty_lines = QCheckBox("保留空行")
        text_layout.addRow("空行处理:", self.preserve_empty_lines)
        
        tabs.addTab(text_tab, "文本合并")
        
        # 按钮
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
    def browse_output_dir(self):
        directory = QFileDialog.getExistingDirectory(self, "选择默认输出目录")
        if directory:
            self.default_output_dir.setText(directory)
            
    def load_settings(self):
        """加载设置"""
        # 窗口几何信息
        if self.settings.value("remember_window_size", True, type=bool):
            geometry = self.settings.value("window_geometry")
            if geometry:  # 只在有保存的几何信息时才恢复
                self.restoreGeometry(geometry)
        
        # 默认输出目录
        default_output_dir = self.settings.value("default_output_dir", "")
        if default_output_dir:
            self.default_output_dir.setText(default_output_dir)
            
        # 文本选项
        self.default_separator.setText(self.settings.value("default_separator", "=" * 50))
        self.add_file_info.setChecked(self.settings.value("add_file_info", True, type=bool))
        self.preserve_empty_lines.setChecked(self.settings.value("preserve_empty_lines", False, type=bool))
        self.auto_detect_encoding.setChecked(self.settings.value("auto_detect_encoding", True, type=bool))
        
    def save_settings(self):
        self.settings.setValue("default_output_dir", self.default_output_dir.text())
        self.settings.setValue("auto_detect_encoding", self.auto_detect_encoding.isChecked())
        self.settings.setValue("remember_window_size", self.remember_window_size.isChecked())
        self.settings.setValue("default_separator", self.default_separator.text())
        self.settings.setValue("add_file_info", self.add_file_info.isChecked())
        self.settings.setValue("preserve_empty_lines", self.preserve_empty_lines.isChecked())


class FileInfoDialog(QDialog):
    """文件信息对话框"""
    def __init__(self, file_path, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.setWindowTitle(f"文件信息 - {os.path.basename(file_path)}")
        self.setModal(True)
        self.resize(500, 400)
        
        self.init_ui()
        self.load_file_info()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        self.info_browser = QTextBrowser()
        layout.addWidget(self.info_browser)
        
        button_box = QDialogButtonBox(QDialogButtonBox.Ok)
        button_box.accepted.connect(self.accept)
        layout.addWidget(button_box)
        
    def load_file_info(self):
        try:
            info = f"文件名: {os.path.basename(self.file_path)}\n"
            info += f"完整路径: {self.file_path}\n"
            
            # 文件大小
            size = os.path.getsize(self.file_path)
            info += f"大小: {self.format_file_size(size)}\n"
            
            # 修改时间
            mtime = os.path.getmtime(self.file_path)
            info += f"修改时间: {datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')}\n"
            
            # 文件类型
            _, ext = os.path.splitext(self.file_path)
            info += f"类型: {ext[1:].upper() if ext else '未知'}\n"
            
            # 如果是文本文件，尝试检测编码和行数
            if self.is_text_file(self.file_path):
                try:
                    with open(self.file_path, 'rb') as f:
                        content = f.read()
                        result = chardet.detect(content)
                        encoding = result['encoding'] or '未知'
                        info += f"编码: {encoding}\n"
                        
                        # 计算行数
                        lines = content.count(b'\n')
                        info += f"行数: {lines + 1}\n"
                        
                        # 预览前几行
                        try:
                            text_content = content.decode(encoding or 'utf-8', errors='ignore')
                            preview_lines = text_content.split('\n')[:5]
                            info += "\n预览:\n" + "\n".join(preview_lines)
                            if lines > 5:
                                info += "\n..."
                        except:
                            info += "\n预览: [无法解码内容]"
                except Exception as e:
                    info += f"\n文本分析错误: {str(e)}"
            
            self.info_browser.setPlainText(info)
            
        except Exception as e:
            self.info_browser.setPlainText(f"无法获取文件信息: {str(e)}")
            
    def is_text_file(self, file_path):
        """简单判断是否为文本文件"""
        text_extensions = ['.txt', '.csv', '.json', '.xml', '.html', '.htm', 
                          '.js', '.css', '.py', '.java', '.c', '.cpp', '.h']
        _, ext = os.path.splitext(file_path)
        return ext.lower() in text_extensions
        
    def format_file_size(self, size):
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} TB"


class FileMergerWorker(QThread):
    """后台文件合并工作线程"""
    progress_updated = pyqtSignal(int, str)
    status_message = pyqtSignal(str)
    finished = pyqtSignal(bool, str)
    file_processed = pyqtSignal(str, int)  # 文件路径, 文件大小
    
    def __init__(self, file_paths, output_path, merge_mode, options, parent=None):
        super().__init__(parent)
        self.file_paths = file_paths
        self.output_path = output_path
        self.merge_mode = merge_mode
        self.options = options
        self.is_cancelled = False
        
    def run(self):
        try:
            total_files = len(self.file_paths)
            if total_files == 0:
                self.finished.emit(False, "没有选择任何文件")
                return
                
            self.status_message.emit(f"开始合并 {total_files} 个文件...")
            
            # 根据合并模式选择处理方法
            if self.merge_mode == "binary":
                success, message = self.merge_binary_files()
            elif self.merge_mode == "text":
                success, message = self.merge_text_files()
            elif self.merge_mode == "csv":
                success, message = self.merge_csv_files()
            elif self.merge_mode == "pdf":
                success, message = self.merge_pdf_files()
            elif self.merge_mode == "image":
                success, message = self.merge_images()
            else:
                success, message = False, f"不支持的合并模式: {self.merge_mode}"
                
            self.finished.emit(success, message)
            
        except Exception as e:
            logger.error(f"合并过程中发生错误: {str(e)}")
            self.finished.emit(False, f"合并过程中发生错误: {str(e)}")
    
    def cancel(self):
        self.is_cancelled = True
        self.status_message.emit("取消操作...")
    
    def merge_binary_files(self):
        """合并二进制文件"""
        try:
            total_size = sum(os.path.getsize(f) for f in self.file_paths)
            processed_size = 0
            
            with open(self.output_path, 'wb') as outfile:
                for i, file_path in enumerate(self.file_paths):
                    if self.is_cancelled:
                        return False, "操作已取消"
                        
                    file_size = os.path.getsize(file_path)
                    self.status_message.emit(f"处理文件: {os.path.basename(file_path)} ({self.format_file_size(file_size)})")
                    
                    with open(file_path, 'rb') as infile:
                        # 分块读取和写入，避免内存占用过大
                        chunk_size = 1024 * 1024  # 1MB
                        while True:
                            chunk = infile.read(chunk_size)
                            if not chunk:
                                break
                            outfile.write(chunk)
                            processed_size += len(chunk)
                            
                            # 更新进度
                            progress = int(processed_size / total_size * 100)
                            self.progress_updated.emit(progress, f"处理中: {os.path.basename(file_path)}")
                    
                    self.file_processed.emit(file_path, file_size)
            
            # 验证合并后的文件大小
            output_size = os.path.getsize(self.output_path)
            if output_size != total_size:
                return False, f"文件大小不匹配: 预期 {self.format_file_size(total_size)}, 实际 {self.format_file_size(output_size)}"
            
            return True, f"成功合并 {len(self.file_paths)} 个二进制文件到 {self.output_path}"
            
        except Exception as e:
            return False, f"二进制文件合并失败: {str(e)}"
    
    def merge_text_files(self):
        """合并文本文件"""
        try:
            encoding = self.options.get('encoding', 'utf-8')
            separator = self.options.get('separator', '')
            add_file_info = self.options.get('add_file_info', True)
            
            with open(self.output_path, 'w', encoding=encoding) as outfile:
                for i, file_path in enumerate(self.file_paths):
                    if self.is_cancelled:
                        return False, "操作已取消"
                        
                    self.status_message.emit(f"处理文件: {os.path.basename(file_path)}")
                    
                    # 检测文件编码
                    file_encoding = encoding
                    if self.options.get('auto_detect_encoding', True):
                        detected_encoding = self.detect_file_encoding(file_path)
                        if detected_encoding:
                            file_encoding = detected_encoding
                    
                    try:
                        with open(file_path, 'r', encoding=file_encoding) as infile:
                            content = infile.read()
                            
                            # 如果不保留空行，移除末尾的空行
                            if not self.options.get('preserve_empty_lines', False):
                                content = content.rstrip()
                                
                            outfile.write(content)
                    except UnicodeDecodeError:
                        # 如果编码检测失败，尝试使用备用编码
                        try:
                            with open(file_path, 'r', encoding='latin-1') as infile:
                                content = infile.read()
                                if not self.options.get('preserve_empty_lines', False):
                                    content = content.rstrip()
                                outfile.write(content)
                        except Exception as e:
                            self.status_message.emit(f"警告: 文件 {os.path.basename(file_path)} 解码失败: {str(e)}")
                            continue
                    
                    # 添加分隔符
                    if separator and i < len(self.file_paths) - 1:
                        sep_text = separator
                        if add_file_info:
                            file_size = os.path.getsize(file_path)
                            file_info = f"文件: {os.path.basename(file_path)} | 大小: {self.format_file_size(file_size)} | 完成时间: {datetime.now().strftime('%H:%M:%S')}"
                            sep_text = sep_text.replace("{file_info}", file_info)
                        outfile.write(sep_text)
                    
                    progress = int((i + 1) / len(self.file_paths) * 100)
                    self.progress_updated.emit(progress, f"处理中: {os.path.basename(file_path)}")
                    self.file_processed.emit(file_path, os.path.getsize(file_path))
            
            return True, f"成功合并 {len(self.file_paths)} 个文本文件到 {self.output_path}"
            
        except Exception as e:
            return False, f"文本文件合并失败: {str(e)}"
    
    def merge_csv_files(self):
        """合并CSV文件"""
        try:
            # 读取所有CSV文件
            dataframes = []
            for i, file_path in enumerate(self.file_paths):
                if self.is_cancelled:
                    return False, "操作已取消"
                    
                self.status_message.emit(f"读取CSV文件: {os.path.basename(file_path)}")
                
                try:
                    df = pd.read_csv(file_path)
                    dataframes.append(df)
                    self.file_processed.emit(file_path, os.path.getsize(file_path))
                except Exception as e:
                    self.status_message.emit(f"警告: 无法读取CSV文件 {os.path.basename(file_path)}: {str(e)}")
                    continue
                
                progress = int((i + 1) / len(self.file_paths) * 100)
                self.progress_updated.emit(progress, f"读取中: {os.path.basename(file_path)}")
            
            if not dataframes:
                return False, "没有有效的CSV文件可合并"
            
            # 合并数据框
            self.status_message.emit("合并CSV数据...")
            merged_df = pd.concat(dataframes, ignore_index=True)
            
            # 保存合并后的CSV
            merged_df.to_csv(self.output_path, index=False)
            
            return True, f"成功合并 {len(dataframes)} 个CSV文件到 {self.output_path}"
            
        except Exception as e:
            return False, f"CSV文件合并失败: {str(e)}"
    
    def merge_pdf_files(self):
        """合并PDF文件"""
        try:
            output_pdf = fitz.open()
            
            for i, file_path in enumerate(self.file_paths):
                if self.is_cancelled:
                    return False, "操作已取消"
                    
                self.status_message.emit(f"处理PDF文件: {os.path.basename(file_path)}")
                
                try:
                    pdf = fitz.open(file_path)
                    output_pdf.insert_pdf(pdf)
                    pdf.close()
                    self.file_processed.emit(file_path, os.path.getsize(file_path))
                except Exception as e:
                    self.status_message.emit(f"警告: 无法处理PDF文件 {os.path.basename(file_path)}: {str(e)}")
                    continue
                
                progress = int((i + 1) / len(self.file_paths) * 100)
                self.progress_updated.emit(progress, f"处理中: {os.path.basename(file_path)}")
            
            # 保存合并后的PDF
            output_pdf.save(self.output_path)
            output_pdf.close()
            
            return True, f"成功合并 {len(self.file_paths)} 个PDF文件到 {self.output_path}"
            
        except Exception as e:
            return False, f"PDF文件合并失败: {str(e)}"
    
    def merge_images(self):
        """合并图片文件（创建图片网格）"""
        try:
            # 读取所有图片
            images = []
            for i, file_path in enumerate(self.file_paths):
                if self.is_cancelled:
                    return False, "操作已取消"
                    
                self.status_message.emit(f"读取图片: {os.path.basename(file_path)}")
                
                try:
                    img = Image.open(file_path)
                    images.append(img)
                    self.file_processed.emit(file_path, os.path.getsize(file_path))
                except Exception as e:
                    self.status_message.emit(f"警告: 无法读取图片文件 {os.path.basename(file_path)}: {str(e)}")
                    continue
                
                progress = int((i + 1) / len(self.file_paths) * 100)
                self.progress_updated.emit(progress, f"读取中: {os.path.basename(file_path)}")
            
            if not images:
                return False, "没有有效的图片文件可合并"
            
            # 计算网格大小
            cols = self.options.get('image_cols', 2)
            rows = (len(images) + cols - 1) // cols
            
            # 获取最大宽度和高度
            max_width = max(img.width for img in images)
            max_height = max(img.height for img in images)
            
            # 创建新图片
            new_image = Image.new('RGB', (cols * max_width, rows * max_height), (255, 255, 255))
            
            # 粘贴所有图片
            for i, img in enumerate(images):
                x = (i % cols) * max_width
                y = (i // cols) * max_height
                new_image.paste(img, (x, y))
            
            # 保存合并后的图片
            new_image.save(self.output_path)
            
            return True, f"成功合并 {len(images)} 个图片文件到 {self.output_path}"
            
        except Exception as e:
            return False, f"图片合并失败: {str(e)}"
    
    def detect_file_encoding(self, file_path):
        """检测文件编码"""
        try:
            with open(file_path, 'rb') as f:
                raw_data = f.read(1024)  # 只读取前1KB用于检测
                result = chardet.detect(raw_data)
                return result['encoding']
        except:
            return None
    
    def format_file_size(self, size):
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} TB"


class FileMerger(QMainWindow):
    """主窗口类"""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("高级多文件合并工具")
        self.setGeometry(100, 100, 1000, 700)
        
        # 初始化变量
        self.file_paths = []
        self.worker_thread = None
        self.settings = QSettings("AdvancedFileMerger", "Settings")
        
        # 设置UI
        self.init_ui()
        self.load_settings()
        
    def init_ui(self):
        """初始化用户界面"""
        # 创建中央部件和主布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        # 左侧面板 - 文件列表和操作
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # 文件列表
        file_group = QGroupBox("文件列表")
        file_layout = QVBoxLayout(file_group)
        
        # 工具栏
        file_toolbar = QToolBar()
        file_toolbar.setIconSize(QSize(16, 16))
        
        self.add_file_action = QAction(QIcon.fromTheme("document-new"), "添加文件", self)
        self.add_file_action.triggered.connect(self.add_files)
        file_toolbar.addAction(self.add_file_action)
        
        self.add_folder_action = QAction(QIcon.fromTheme("folder"), "添加文件夹", self)
        self.add_folder_action.triggered.connect(self.add_folder)
        file_toolbar.addAction(self.add_folder_action)
        
        self.remove_action = QAction(QIcon.fromTheme("edit-delete"), "移除选中", self)
        self.remove_action.triggered.connect(self.remove_selected)
        file_toolbar.addAction(self.remove_action)
        
        self.clear_action = QAction(QIcon.fromTheme("edit-clear"), "清空列表", self)
        self.clear_action.triggered.connect(self.clear_list)
        file_toolbar.addAction(self.clear_action)
        
        file_toolbar.addSeparator()
        
        self.move_up_action = QAction(QIcon.fromTheme("go-up"), "上移", self)
        self.move_up_action.triggered.connect(self.move_up)
        file_toolbar.addAction(self.move_up_action)
        
        self.move_down_action = QAction(QIcon.fromTheme("go-down"), "下移", self)
        self.move_down_action.triggered.connect(self.move_down)
        file_toolbar.addAction(self.move_down_action)
        
        file_layout.addWidget(file_toolbar)
        
        # 文件树形视图
        self.file_tree = QTreeWidget()
        self.file_tree.setHeaderLabels(["文件名", "大小", "类型", "修改时间"])
        self.file_tree.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.file_tree.setSelectionMode(QTreeWidget.ExtendedSelection)
        self.file_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.file_tree.customContextMenuRequested.connect(self.show_file_context_menu)
        self.file_tree.itemDoubleClicked.connect(self.show_file_info)
        file_layout.addWidget(self.file_tree)
        
        left_layout.addWidget(file_group)
        
        # 文件统计
        self.stats_label = QLabel("文件数: 0 | 总大小: 0 B")
        left_layout.addWidget(self.stats_label)
        
        # 添加到分割器
        splitter.addWidget(left_panel)
        
        # 右侧面板 - 选项和日志
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # 选项选项卡
        self.options_tabs = QTabWidget()
        right_layout.addWidget(self.options_tabs)
        
        # 合并选项
        merge_options = QWidget()
        merge_layout = QFormLayout(merge_options)
        
        # 合并模式
        self.merge_mode_combo = QComboBox()
        self.merge_mode_combo.addItems(["文本", "二进制", "CSV", "PDF", "图片"])
        self.merge_mode_combo.currentTextChanged.connect(self.on_merge_mode_changed)
        merge_layout.addRow("合并模式:", self.merge_mode_combo)
        
        # 输出路径
        output_layout = QHBoxLayout()
        self.output_path_edit = QLineEdit()
        self.output_path_edit.setPlaceholderText("选择输出文件路径")
        output_layout.addWidget(self.output_path_edit)
        
        self.browse_output_btn = QPushButton("浏览...")
        self.browse_output_btn.clicked.connect(self.select_output_file)
        output_layout.addWidget(self.browse_output_btn)
        
        merge_layout.addRow("输出路径:", output_layout)
        
        # 文本选项
        self.text_options_group = QGroupBox("文本选项")
        text_options_layout = QFormLayout(self.text_options_group)
        
        self.encoding_combo = QComboBox()
        self.encoding_combo.addItems(["utf-8", "gbk", "gb2312", "latin-1", "ascii"])
        text_options_layout.addRow("编码:", self.encoding_combo)
        
        self.separator_edit = QLineEdit()
        self.separator_edit.setPlaceholderText("输入分隔符内容")
        text_options_layout.addRow("分隔符:", self.separator_edit)
        
        self.add_file_info_check = QCheckBox("在分隔符中包含文件信息")
        self.add_file_info_check.setChecked(True)
        text_options_layout.addRow(self.add_file_info_check)
        
        self.preserve_empty_check = QCheckBox("保留空行")
        text_options_layout.addRow(self.preserve_empty_check)
        
        self.auto_detect_check = QCheckBox("自动检测文件编码")
        self.auto_detect_check.setChecked(True)
        text_options_layout.addRow(self.auto_detect_check)
        
        merge_layout.addRow(self.text_options_group)
        
        # CSV选项
        self.csv_options_group = QGroupBox("CSV选项")
        self.csv_options_group.setVisible(False)
        csv_options_layout = QFormLayout(self.csv_options_group)
        
        self.skip_header_check = QCheckBox("跳过首行(标题)")
        csv_options_layout.addRow(self.skip_header_check)
        
        merge_layout.addRow(self.csv_options_group)
        
        # 图片选项
        self.image_options_group = QGroupBox("图片选项")
        self.image_options_group.setVisible(False)
        image_options_layout = QFormLayout(self.image_options_group)
        
        self.image_cols_spin = QSpinBox()
        self.image_cols_spin.setRange(1, 10)
        self.image_cols_spin.setValue(2)
        image_options_layout.addRow("每行图片数:", self.image_cols_spin)
        
        merge_layout.addRow(self.image_options_group)
        
        self.options_tabs.addTab(merge_options, "合并选项")
        
        # 排序和过滤选项
        sort_filter_options = QWidget()
        sort_filter_layout = QVBoxLayout(sort_filter_options)
        
        # 排序选项
        sort_group = QGroupBox("排序")
        sort_layout = QHBoxLayout(sort_group)
        
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["按文件名", "按修改时间", "按文件大小", "按文件类型"])
        sort_layout.addWidget(self.sort_combo)
        
        self.sort_order_btn = QToolButton()
        self.sort_order_btn.setText("升序")
        self.sort_order_btn.setCheckable(True)
        self.sort_order_btn.clicked.connect(self.toggle_sort_order)
        sort_layout.addWidget(self.sort_order_btn)
        
        self.sort_btn = QPushButton("排序")
        self.sort_btn.clicked.connect(self.sort_files)
        sort_layout.addWidget(self.sort_btn)
        
        sort_filter_layout.addWidget(sort_group)
        
        # 过滤选项
        filter_group = QGroupBox("过滤")
        filter_layout = QFormLayout(filter_group)
        
        self.filter_ext_edit = QLineEdit()
        self.filter_ext_edit.setPlaceholderText("例如: txt, pdf, jpg (逗号分隔)")
        filter_layout.addRow("文件扩展名:", self.filter_ext_edit)
        
        self.filter_min_size = QSpinBox()
        self.filter_min_size.setSuffix(" KB")
        self.filter_min_size.setRange(0, 1024000)
        filter_layout.addRow("最小大小:", self.filter_min_size)
        
        self.filter_max_size = QSpinBox()
        self.filter_max_size.setSuffix(" KB")
        self.filter_max_size.setRange(0, 1024000)
        self.filter_max_size.setValue(1024000)
        filter_layout.addRow("最大大小:", self.filter_max_size)
        
        filter_btn_layout = QHBoxLayout()
        self.apply_filter_btn = QPushButton("应用过滤")
        self.apply_filter_btn.clicked.connect(self.apply_filter)
        filter_btn_layout.addWidget(self.apply_filter_btn)
        
        self.reset_filter_btn = QPushButton("重置过滤")
        self.reset_filter_btn.clicked.connect(self.reset_filter)
        filter_btn_layout.addWidget(self.reset_filter_btn)
        
        filter_layout.addRow(filter_btn_layout)
        
        sort_filter_layout.addWidget(filter_group)
        sort_filter_layout.addStretch()
        
        self.options_tabs.addTab(sort_filter_options, "排序和过滤")
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        right_layout.addWidget(self.progress_bar)
        
        # 状态标签
        self.status_label = QLabel("就绪")
        right_layout.addWidget(self.status_label)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        
        self.merge_btn = QPushButton("开始合并")
        self.merge_btn.clicked.connect(self.start_merge)
        button_layout.addWidget(self.merge_btn)
        
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.cancel_merge)
        self.cancel_btn.setEnabled(False)
        button_layout.addWidget(self.cancel_btn)
        
        right_layout.addLayout(button_layout)
        
        # 日志区域
        log_group = QGroupBox("操作日志")
        log_layout = QVBoxLayout(log_group)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)
        
        # 日志工具栏
        log_toolbar = QToolBar()
        log_toolbar.setIconSize(QSize(16, 16))
        
        self.clear_log_action = QAction(QIcon.fromTheme("edit-clear"), "清空日志", self)
        self.clear_log_action.triggered.connect(self.clear_log)
        log_toolbar.addAction(self.clear_log_action)
        
        self.save_log_action = QAction(QIcon.fromTheme("document-save"), "保存日志", self)
        self.save_log_action.triggered.connect(self.save_log)
        log_toolbar.addAction(self.save_log_action)
        
        log_layout.addWidget(log_toolbar)
        
        right_layout.addWidget(log_group)
        
        # 添加到分割器
        splitter.addWidget(right_panel)
        
        # 设置分割器比例
        splitter.setSizes([300, 700])
        
        # 创建菜单栏
        self.create_menu()
        
        # 创建状态栏
        self.statusBar().showMessage("就绪")
        
        # 启用拖放
        self.setAcceptDrops(True)
        
        # 设置样式
        self.apply_style()
        
    def create_menu(self):
        """创建菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu("文件")
        
        new_action = QAction("新建项目", self)
        new_action.setShortcut("Ctrl+N")
        file_menu.addAction(new_action)
        
        open_action = QAction("打开项目", self)
        open_action.setShortcut("Ctrl+O")
        file_menu.addAction(open_action)
        
        save_action = QAction("保存项目", self)
        save_action.setShortcut("Ctrl+S")
        file_menu.addAction(save_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("退出", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 编辑菜单
        edit_menu = menubar.addMenu("编辑")
        
        settings_action = QAction("设置", self)
        settings_action.setShortcut("Ctrl+,")
        settings_action.triggered.connect(self.show_settings)
        edit_menu.addAction(settings_action)
        
        # 工具菜单
        tools_menu = menubar.addMenu("工具")
        
        batch_action = QAction("批量处理", self)
        batch_action.triggered.connect(self.show_batch_dialog)
        tools_menu.addAction(batch_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu("帮助")
        
        about_action = QAction("关于", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
    def apply_style(self):
        """应用样式"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f0f0f0;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #cccccc;
                border-radius: 4px;
                margin-top: 1ex;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QTreeWidget {
                border: 1px solid #cccccc;
                border-radius: 3px;
                background-color: white;
            }
            QTextEdit {
                border: 1px solid #cccccc;
                border-radius: 3px;
                background-color: white;
            }
            QProgressBar {
                border: 1px solid #cccccc;
                border-radius: 3px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                width: 10px;
            }
        """)
        
    def load_settings(self):
        """加载设置"""
        # 窗口几何信息 - 添加对 None 值的检查
        if self.settings.value("remember_window_size", True, type=bool):
            geometry = self.settings.value("window_geometry")
            if geometry:  # 只在有保存的几何信息时才恢复
                self.restoreGeometry(geometry)
        
        # 默认输出目录
        default_output_dir = self.settings.value("default_output_dir", "")
        if default_output_dir:
            self.output_path_edit.setText(default_output_dir)
            
        # 文本选项
        self.separator_edit.setText(self.settings.value("default_separator", "=" * 50))
        self.add_file_info_check.setChecked(self.settings.value("add_file_info", True, type=bool))
        self.preserve_empty_check.setChecked(self.settings.value("preserve_empty_lines", False, type=bool))
        self.auto_detect_check.setChecked(self.settings.value("auto_detect_encoding", True, type=bool))
        
    def save_settings(self):
        """保存设置"""
        # 窗口几何信息
        if self.settings.value("remember_window_size", True, type=bool):
            self.settings.setValue("window_geometry", self.saveGeometry())
            
    def on_merge_mode_changed(self, mode):
        """合并模式改变时的处理"""
        # 隐藏所有选项组
        self.text_options_group.setVisible(False)
        self.csv_options_group.setVisible(False)
        self.image_options_group.setVisible(False)
        
        # 显示当前模式的选项组
        if mode == "文本":
            self.text_options_group.setVisible(True)
        elif mode == "CSV":
            self.csv_options_group.setVisible(True)
        elif mode == "图片":
            self.image_options_group.setVisible(True)
            
        # 更新输出文件扩展名
        self.update_output_extension()
        
    def update_output_extension(self):
        """根据合并模式更新输出文件扩展名"""
        if not hasattr(self, 'output_path_edit') or not self.output_path_edit.text():
            return
            
        current_path = self.output_path_edit.text()
        base, _ = os.path.splitext(current_path)
        
        mode = self.merge_mode_combo.currentText()
        if mode == "文本":
            new_path = base + ".txt"
        elif mode == "二进制":
            new_path = base + ".bin"
        elif mode == "CSV":
            new_path = base + ".csv"
        elif mode == "PDF":
            new_path = base + ".pdf"
        elif mode == "图片":
            new_path = base + ".jpg"
        else:
            new_path = current_path
            
        self.output_path_edit.setText(new_path)
        
    def add_files(self):
        """添加文件到列表"""
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择要合并的文件", "", "所有文件 (*.*);;文本文件 (*.txt *.log *.csv *.json *.xml);;PDF文件 (*.pdf);;图片文件 (*.jpg *.jpeg *.png *.bmp *.gif)"
        )
        
        if files:
            self.add_files_to_list(files)
            
    def add_files_to_list(self, files):
        """将文件添加到列表"""
        for file in files:
            if file not in self.file_paths:
                self.file_paths.append(file)
                self.add_file_to_tree(file)
        
        self.update_stats()
        self.log_message(f"添加了 {len(files)} 个文件")
        
    def add_file_to_tree(self, file_path):
        """添加文件到树形视图"""
        try:
            file_name = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)
            _, file_ext = os.path.splitext(file_path)
            mtime = os.path.getmtime(file_path)
            mtime_str = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M')
            
            item = QTreeWidgetItem(self.file_tree)
            item.setText(0, file_name)
            item.setText(1, self.format_file_size(file_size))
            item.setText(2, file_ext[1:].upper() if file_ext else "未知")
            item.setText(3, mtime_str)
            item.setData(0, Qt.UserRole, file_path)
            
        except Exception as e:
            self.log_message(f"无法添加文件 {file_path}: {str(e)}")
            
    def add_folder(self):
        """添加文件夹中的所有文件到列表"""
        folder = QFileDialog.getExistingDirectory(self, "选择文件夹")
        
        if folder:
            files = []
            for root, _, filenames in os.walk(folder):
                for filename in filenames:
                    files.append(os.path.join(root, filename))
            
            if files:
                self.add_files_to_list(files)
    
    def remove_selected(self):
        """移除选中的文件"""
        selected_items = self.file_tree.selectedItems()
        if not selected_items:
            return
            
        for item in selected_items:
            file_path = item.data(0, Qt.UserRole)
            if file_path in self.file_paths:
                self.file_paths.remove(file_path)
            self.file_tree.takeTopLevelItem(self.file_tree.indexOfTopLevelItem(item))
        
        self.update_stats()
        self.log_message(f"移除了 {len(selected_items)} 个文件")
    
    def clear_list(self):
        """清空文件列表"""
        if self.file_paths:
            self.file_paths.clear()
            self.file_tree.clear()
            self.update_stats()
            self.log_message("已清空文件列表")
    
    def move_up(self):
        """上移选中文件"""
        selected_items = self.file_tree.selectedItems()
        if not selected_items:
            return
            
        for item in selected_items:
            index = self.file_tree.indexOfTopLevelItem(item)
            if index > 0:
                # 移动列表中的文件路径
                file_path = self.file_paths.pop(index)
                self.file_paths.insert(index - 1, file_path)
                
                # 移动树中的项目
                self.file_tree.takeTopLevelItem(index)
                self.file_tree.insertTopLevelItem(index - 1, item)
                item.setSelected(True)
    
    def move_down(self):
        """下移选中文件"""
        selected_items = self.file_tree.selectedItems()
        if not selected_items:
            return
            
        # 需要从底部开始处理，以免影响索引
        for item in reversed(selected_items):
            index = self.file_tree.indexOfTopLevelItem(item)
            if index < self.file_tree.topLevelItemCount() - 1:
                # 移动列表中的文件路径
                file_path = self.file_paths.pop(index)
                self.file_paths.insert(index + 1, file_path)
                
                # 移动树中的项目
                self.file_tree.takeTopLevelItem(index)
                self.file_tree.insertTopLevelItem(index + 1, item)
                item.setSelected(True)
    
    def show_file_context_menu(self, position):
        """显示文件上下文菜单"""
        item = self.file_tree.itemAt(position)
        if not item:
            return
            
        menu = QMenu()
        
        open_action = menu.addAction("打开文件")
        info_action = menu.addAction("文件信息")
        remove_action = menu.addAction("移除")
        
        action = menu.exec_(self.file_tree.viewport().mapToGlobal(position))
        
        if action == open_action:
            self.open_file(item)
        elif action == info_action:
            self.show_file_info(item)
        elif action == remove_action:
            self.remove_selected()
    
    def open_file(self, item):
        """打开文件"""
        file_path = item.data(0, Qt.UserRole)
        try:
            if sys.platform == "win32":
                os.startfile(file_path)
            elif sys.platform == "darwin":
                os.system(f"open '{file_path}'")
            else:
                os.system(f"xdg-open '{file_path}'")
        except Exception as e:
            self.log_message(f"无法打开文件: {str(e)}")
    
    def show_file_info(self, item):
        """显示文件信息"""
        file_path = item.data(0, Qt.UserRole)
        dialog = FileInfoDialog(file_path, self)
        dialog.exec_()
    
    def select_output_file(self):
        """选择输出文件路径"""
        mode = self.merge_mode_combo.currentText()
        if mode == "文本":
            filter = "文本文件 (*.txt)"
        elif mode == "二进制":
            filter = "二进制文件 (*.bin)"
        elif mode == "CSV":
            filter = "CSV文件 (*.csv)"
        elif mode == "PDF":
            filter = "PDF文件 (*.pdf)"
        elif mode == "图片":
            filter = "图片文件 (*.jpg *.png)"
        else:
            filter = "所有文件 (*.*)"
            
        default_dir = self.settings.value("default_output_dir", "")
        file_path, _ = QFileDialog.getSaveFileName(
            self, "选择输出文件", default_dir, filter
        )
        
        if file_path:
            self.output_path_edit.setText(file_path)
            self.log_message(f"输出文件设置为: {file_path}")
    
    def start_merge(self):
        """开始合并文件"""
        output_path = self.output_path_edit.text()
        if not output_path:
            QMessageBox.warning(self, "警告", "请先选择输出文件路径")
            return
            
        if not self.file_paths:
            QMessageBox.warning(self, "警告", "请先添加要合并的文件")
            return
        
        # 检查输出文件是否已存在
        if os.path.exists(output_path):
            reply = QMessageBox.question(
                self, "确认覆盖", 
                f"输出文件 {output_path} 已存在，是否覆盖？", 
                QMessageBox.Yes | QMessageBox.No, 
                QMessageBox.No
            )
            if reply == QMessageBox.No:
                return
        
        # 禁用UI控件
        self.set_ui_enabled(False)
        
        # 获取选项
        merge_mode = self.merge_mode_combo.currentText().lower()
        
        options = {
            'encoding': self.encoding_combo.currentText(),
            'separator': self.separator_edit.text(),
            'add_file_info': self.add_file_info_check.isChecked(),
            'preserve_empty_lines': self.preserve_empty_check.isChecked(),
            'auto_detect_encoding': self.auto_detect_check.isChecked(),
            'image_cols': self.image_cols_spin.value()
        }
        
        # 创建并启动工作线程
        self.worker_thread = FileMergerWorker(
            self.file_paths, output_path, merge_mode, options
        )
        self.worker_thread.progress_updated.connect(self.update_progress)
        self.worker_thread.status_message.connect(self.update_status)
        self.worker_thread.finished.connect(self.merge_finished)
        self.worker_thread.file_processed.connect(self.on_file_processed)
        self.worker_thread.start()
        
        self.log_message("开始文件合并操作...")
    
    def on_file_processed(self, file_path, file_size):
        """文件处理完成回调"""
        # 在文件树中标记已处理的文件
        for i in range(self.file_tree.topLevelItemCount()):
            item = self.file_tree.topLevelItem(i)
            if item.data(0, Qt.UserRole) == file_path:
                # 更改项目颜色以标记已完成
                item.setForeground(0, QColor(0, 128, 0))  # 绿色
                break
    
    def cancel_merge(self):
        """取消合并操作"""
        if self.worker_thread and self.worker_thread.isRunning():
            self.worker_thread.cancel()
    
    def merge_finished(self, success, message):
        """合并完成回调"""
        # 启用UI控件
        self.set_ui_enabled(True)
        
        # 显示结果消息
        if success:
            self.log_message(message)
            QMessageBox.information(self, "成功", message)
        else:
            self.log_message(f"错误: {message}")
            QMessageBox.critical(self, "错误", message)
        
        # 重置进度条
        self.progress_bar.setVisible(False)
        self.progress_bar.setValue(0)
        
        # 更新状态
        self.status_label.setText("就绪")
        self.statusBar().showMessage("就绪")
    
    def update_progress(self, value, message):
        """更新进度条"""
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(value)
        self.statusBar().showMessage(message)
    
    def update_status(self, message):
        """更新状态标签"""
        self.status_label.setText(message)
        self.log_message(message)
    
    def log_message(self, message):
        """添加日志消息"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
        # 自动滚动到底部
        self.log_text.moveCursor(QTextCursor.End)
    
    def clear_log(self):
        """清空日志"""
        self.log_text.clear()
    
    def save_log(self):
        """保存日志到文件"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存日志", "", "文本文件 (*.txt)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.log_text.toPlainText())
                self.log_message(f"日志已保存到: {file_path}")
            except Exception as e:
                self.log_message(f"保存日志失败: {str(e)}")
    
    def set_ui_enabled(self, enabled):
        """启用或禁用UI控件"""
        self.add_file_action.setEnabled(enabled)
        self.add_folder_action.setEnabled(enabled)
        self.remove_action.setEnabled(enabled)
        self.clear_action.setEnabled(enabled)
        self.move_up_action.setEnabled(enabled)
        self.move_down_action.setEnabled(enabled)
        self.merge_btn.setEnabled(enabled)
        self.browse_output_btn.setEnabled(enabled)
        self.cancel_btn.setEnabled(not enabled)
        self.file_tree.setEnabled(enabled)
        self.options_tabs.setEnabled(enabled)
    
    def update_stats(self):
        """更新文件统计信息"""
        count = len(self.file_paths)
        total_size = sum(os.path.getsize(f) for f in self.file_paths)
        self.stats_label.setText(f"文件数: {count} | 总大小: {self.format_file_size(total_size)}")
        
    def format_file_size(self, size):
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} TB"
    
    def toggle_sort_order(self):
        """切换排序顺序"""
        if self.sort_order_btn.isChecked():
            self.sort_order_btn.setText("降序")
        else:
            self.sort_order_btn.setText("升序")
    
    def sort_files(self):
        """排序文件"""
        if not self.file_paths:
            return
            
        sort_by = self.sort_combo.currentText()
        ascending = not self.sort_order_btn.isChecked()
        
        if sort_by == "按文件名":
            self.file_paths.sort(key=lambda x: os.path.basename(x).lower(), reverse=not ascending)
        elif sort_by == "按修改时间":
            self.file_paths.sort(key=os.path.getmtime, reverse=not ascending)
        elif sort_by == "按文件大小":
            self.file_paths.sort(key=os.path.getsize, reverse=not ascending)
        elif sort_by == "按文件类型":
            self.file_paths.sort(key=lambda x: os.path.splitext(x)[1].lower(), reverse=not ascending)
        
        # 更新文件树
        self.file_tree.clear()
        for file_path in self.file_paths:
            self.add_file_to_tree(file_path)
            
        self.log_message(f"文件已按{sort_by}{'升序' if ascending else '降序'}排序")
    
    def apply_filter(self):
        """应用文件过滤"""
        if not self.file_paths:
            return
            
        # 获取过滤条件
        ext_filter = self.filter_ext_edit.text().strip()
        min_size = self.filter_min_size.value() * 1024  # 转换为字节
        max_size = self.filter_max_size.value() * 1024  # 转换为字节
        
        # 处理扩展名过滤
        extensions = []
        if ext_filter:
            extensions = [ext.strip().lower() for ext in ext_filter.split(',')]
            # 确保扩展名以点开头
            extensions = [ext if ext.startswith('.') else f'.{ext}' for ext in extensions]
        
        # 应用过滤
        filtered_files = []
        for file_path in self.file_paths:
            # 检查扩展名
            if extensions:
                _, ext = os.path.splitext(file_path)
                if ext.lower() not in extensions:
                    continue
                    
            # 检查文件大小
            file_size = os.path.getsize(file_path)
            if file_size < min_size or file_size > max_size:
                continue
                
            filtered_files.append(file_path)
        
        # 更新文件列表
        self.file_paths = filtered_files
        self.file_tree.clear()
        for file_path in self.file_paths:
            self.add_file_to_tree(file_path)
            
        self.update_stats()
        self.log_message(f"应用过滤后剩余 {len(self.file_paths)} 个文件")
    
    def reset_filter(self):
        """重置文件过滤"""
        # 清空过滤条件
        self.filter_ext_edit.clear()
        self.filter_min_size.setValue(0)
        self.filter_max_size.setValue(1024000)
        
        self.log_message("过滤条件已重置")
    
    def show_settings(self):
        """显示设置对话框"""
        dialog = SettingsDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            dialog.save_settings()
            self.load_settings()
            self.log_message("设置已保存")
    
    def show_batch_dialog(self):
        """显示批量处理对话框"""
        # 这里可以实现批量处理功能
        QMessageBox.information(self, "批量处理", "批量处理功能尚未实现")
    
    def show_about(self):
        """显示关于对话框"""
        about_text = """
        <h2>高级多文件合并工具</h2>
        <p>版本: 2.0</p>
        <p>一个功能强大的多文件合并工具，支持多种文件格式和合并选项。</p>
        <p>功能特点:</p>
        <ul>
            <li>支持文本、二进制、CSV、PDF和图片文件合并</li>
            <li>智能编码检测和转换</li>
            <li>文件排序和过滤</li>
            <li>自定义分隔符和文件信息</li>
            <li>批量处理能力</li>
            <li>拖放支持</li>
        </ul>
        <p>版权所有 © 2023</p>
        """
        QMessageBox.about(self, "关于", about_text)
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        """拖放进入事件"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    
    def dropEvent(self, event: QDropEvent):
        """拖放事件"""
        urls = event.mimeData().urls()
        if urls:
            files = [url.toLocalFile() for url in urls]
            self.add_files_to_list(files)
    
    def closeEvent(self, event):
        """窗口关闭事件"""
        if self.worker_thread and self.worker_thread.isRunning():
            reply = QMessageBox.question(
                self, "确认退出", 
                "文件合并仍在进行中，确定要退出吗？", 
                QMessageBox.Yes | QMessageBox.No, 
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.worker_thread.cancel()
                self.worker_thread.wait()
                event.accept()
            else:
                event.ignore()
        else:
            self.save_settings()
            event.accept()


def main():
    """主函数"""
    app = QApplication(sys.argv)
    app.setApplicationName("高级多文件合并工具")
    app.setApplicationVersion("2.0")
    
    # 设置字体
    font = QFont("Microsoft YaHei", 9)
    app.setFont(font)
    
    window = FileMerger()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()