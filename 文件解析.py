import sys
import os
import json
import csv
import xml.etree.ElementTree as ET
import yaml
import pickle
import struct
import numpy as np
import pandas as pd
from PIL import Image, ImageOps
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QTextEdit, QTreeWidget, QTreeWidgetItem, QTabWidget,
                             QFileDialog, QLabel, QSplitter, QMessageBox, QProgressBar,
                             QTableWidget, QTableWidgetItem, QHeaderView, QComboBox,
                             QLineEdit, QGroupBox, QFormLayout, QCheckBox, QListWidget,
                             QListWidgetItem, QGraphicsView, QGraphicsScene, QGraphicsPixmapItem,
                             QToolBar, QAction, QToolButton, QMenu, QSpinBox, QDoubleSpinBox,
                             QScrollArea, QSizePolicy, QDialog, QDialogButtonBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize, QTimer, QRectF
from PyQt5.QtGui import QFont, QIcon, QPixmap, QImage, QPainter, QPen, QColor, QPalette
import torch
import chardet
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import seaborn as sns
import warnings
warnings.filterwarnings('ignore')

# 尝试导入可选依赖
try:
    import scipy.io
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False

try:
    import h5py
    H5PY_AVAILABLE = True
except ImportError:
    H5PY_AVAILABLE = False

class MplCanvas(FigureCanvas):
    """Matplotlib画布"""
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_subplot(111)
        super().__init__(self.fig)
        self.setParent(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.updateGeometry()

class FileParserThread(QThread):
    """文件解析线程"""
    progress_updated = pyqtSignal(int, str)
    parsing_finished = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, file_path, file_type, options):
        super().__init__()
        self.file_path = file_path
        self.file_type = file_type
        self.options = options
    
    def run(self):
        try:
            data = {}
            file_size = os.path.getsize(self.file_path)
            
            self.progress_updated.emit(10, "开始解析文件...")
            
            if self.file_type == "JSON":
                data = self.parse_json()
            elif self.file_type == "CSV":
                data = self.parse_csv()
            elif self.file_type == "XML":
                data = self.parse_xml()
            elif self.file_type == "YAML":
                data = self.parse_yaml()
            elif self.file_type == "TXT":
                data = self.parse_txt()
            elif self.file_type == "Pickle":
                data = self.parse_pickle()
            elif self.file_type == "NPY":
                data = self.parse_npy()
            elif self.file_type == "NPZ":
                data = self.parse_npz()
            elif self.file_type == "PT/PTH":
                data = self.parse_pytorch()
            elif self.file_type == "Image":
                data = self.parse_image()
            elif self.file_type == "MAT" and SCIPY_AVAILABLE:
                data = self.parse_mat()
            elif self.file_type == "HDF5" and H5PY_AVAILABLE:
                data = self.parse_hdf5()
            elif self.file_type == "Binary":
                data = self.parse_binary()
            else:
                raise Exception(f"不支持的文件格式: {self.file_type}")
            
            self.progress_updated.emit(100, "解析完成")
            self.parsing_finished.emit(data)
        except Exception as e:
            self.error_occurred.emit(str(e))
    
    def parse_json(self):
        with open(self.file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
            self.progress_updated.emit(50, "JSON解析中...")
            return {
                "type": "JSON", 
                "data": data, 
                "raw": json.dumps(data, indent=2, ensure_ascii=False),
                "metadata": {
                    "size": os.path.getsize(self.file_path),
                    "encoding": "UTF-8"
                }
            }
    
    def parse_csv(self):
        # 检测编码
        with open(self.file_path, 'rb') as file:
            raw_data = file.read()
            encoding = chardet.detect(raw_data)['encoding'] or 'utf-8'
        
        # 解析CSV
        data = []
        with open(self.file_path, 'r', encoding=encoding) as file:
            # 尝试不同的分隔符
            sample = file.read(4096)
            file.seek(0)
            
            sniffer = csv.Sniffer()
            dialect = sniffer.sniff(sample)
            has_header = sniffer.has_header(sample)
            
            csv_reader = csv.reader(file, dialect)
            
            if has_header:
                headers = next(csv_reader)
            else:
                # 如果没有标题，使用默认标题
                first_row = next(csv_reader)
                headers = [f"Column_{i}" for i in range(len(first_row))]
                data.append(first_row)  # 添加第一行数据
            
            data.extend([row for row in csv_reader])
            
            self.progress_updated.emit(50, "CSV解析中...")
            
            # 创建表格数据
            table_data = {
                "headers": headers,
                "rows": data,
                "dialect": {
                    "delimiter": dialect.delimiter,
                    "quotechar": dialect.quotechar,
                    "doublequote": dialect.doublequote
                }
            }
            
            return {
                "type": "CSV", 
                "data": table_data, 
                "raw": self.csv_to_string(headers, data, dialect),
                "metadata": {
                    "size": os.path.getsize(self.file_path),
                    "encoding": encoding,
                    "has_header": has_header,
                    "rows": len(data),
                    "columns": len(headers)
                }
            }
    
    def csv_to_string(self, headers, rows, dialect):
        result = dialect.delimiter.join(headers) + "\n"
        for row in rows:
            result += dialect.delimiter.join(row) + "\n"
        return result
    
    def parse_xml(self):
        tree = ET.parse(self.file_path)
        root = tree.getroot()
        
        self.progress_updated.emit(50, "XML解析中...")
        
        # 转换为字典格式
        xml_dict = self.xml_to_dict(root)
        
        return {
            "type": "XML", 
            "data": xml_dict, 
            "raw": ET.tostring(root, encoding='unicode'),
            "metadata": {
                "size": os.path.getsize(self.file_path),
                "root_tag": root.tag,
                "encoding": "UTF-8"
            }
        }
    
    def xml_to_dict(self, element):
        result = {}
        result['tag'] = element.tag
        result['attributes'] = element.attrib
        result['text'] = element.text.strip() if element.text else ""
        result['children'] = [self.xml_to_dict(child) for child in element]
        return result
    
    def parse_yaml(self):
        with open(self.file_path, 'r', encoding='utf-8') as file:
            data = yaml.safe_load(file)
            self.progress_updated.emit(50, "YAML解析中...")
            return {
                "type": "YAML", 
                "data": data, 
                "raw": yaml.dump(data, default_flow_style=False, allow_unicode=True),
                "metadata": {
                    "size": os.path.getsize(self.file_path),
                    "encoding": "UTF-8"
                }
            }
    
    def parse_txt(self):
        # 检测编码
        with open(self.file_path, 'rb') as file:
            raw_data = file.read()
            encoding = chardet.detect(raw_data)['encoding'] or 'utf-8'
        
        with open(self.file_path, 'r', encoding=encoding) as file:
            content = file.read()
            self.progress_updated.emit(50, "文本解析中...")
            return {
                "type": "TXT", 
                "data": content, 
                "raw": content,
                "metadata": {
                    "size": os.path.getsize(self.file_path),
                    "encoding": encoding,
                    "lines": len(content.splitlines()),
                    "words": len(content.split())
                }
            }
    
    def parse_pickle(self):
        with open(self.file_path, 'rb') as file:
            data = pickle.load(file)
            self.progress_updated.emit(50, "Pickle解析中...")
            
            # 尝试将数据转换为可序列化的格式
            try:
                raw_repr = str(data)
            except:
                raw_repr = "<无法显示原始内容>"
                
            return {
                "type": "Pickle", 
                "data": data, 
                "raw": raw_repr,
                "metadata": {
                    "size": os.path.getsize(self.file_path),
                    "python_version": getattr(data, '__version__', 'Unknown')
                }
            }
    
    def parse_npy(self):
        data = np.load(self.file_path, allow_pickle=True)
        self.progress_updated.emit(50, "NPY解析中...")
        
        return {
            "type": "NPY", 
            "data": data, 
            "raw": self.numpy_to_string(data),
            "metadata": {
                "size": os.path.getsize(self.file_path),
                "shape": data.shape,
                "dtype": str(data.dtype),
                "ndim": data.ndim
            }
        }
    
    def parse_npz(self):
        data = np.load(self.file_path, allow_pickle=True)
        self.progress_updated.emit(50, "NPZ解析中...")
        
        # 提取所有数组
        arrays = {}
        for key in data.files:
            arrays[key] = data[key]
        
        return {
            "type": "NPZ", 
            "data": arrays, 
            "raw": "\n".join([f"{key}: {arr.shape} {arr.dtype}" for key, arr in arrays.items()]),
            "metadata": {
                "size": os.path.getsize(self.file_path),
                "files": list(arrays.keys()),
                "total_arrays": len(arrays)
            }
        }
    
    def parse_pytorch(self):
        data = torch.load(self.file_path, map_location='cpu')
        self.progress_updated.emit(50, "PyTorch模型解析中...")
        
        # 分析模型结构
        model_info = self.analyze_pytorch_model(data)
        
        return {
            "type": "PT/PTH", 
            "data": data, 
            "raw": str(data),
            "metadata": {
                "size": os.path.getsize(self.file_path),
                "model_info": model_info
            }
        }
    
    def analyze_pytorch_model(self, model_data):
        """分析PyTorch模型结构"""
        info = {}
        
        if isinstance(model_data, dict):
            info["type"] = "状态字典"
            info["keys"] = list(model_data.keys())
            info["tensor_count"] = sum(1 for v in model_data.values() if torch.is_tensor(v))
            info["total_parameters"] = sum(v.numel() for v in model_data.values() if torch.is_tensor(v))
        elif hasattr(model_data, 'state_dict'):
            info["type"] = "模型对象"
            state_dict = model_data.state_dict()
            info["keys"] = list(state_dict.keys())
            info["tensor_count"] = len(state_dict)
            info["total_parameters"] = sum(p.numel() for p in model_data.parameters())
        else:
            info["type"] = "未知类型"
            
        return info
    
    def parse_image(self):
        image = Image.open(self.file_path)
        self.progress_updated.emit(50, "图像解析中...")
        
        # 转换为RGB模式（如果需要）
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # 获取图像信息
        width, height = image.size
        mode = image.mode
        
        # 转换为numpy数组进行进一步分析
        img_array = np.array(image)
        
        return {
            "type": "Image", 
            "data": image, 
            "raw": f"图像尺寸: {width}x{height}, 模式: {mode}",
            "metadata": {
                "size": os.path.getsize(self.file_path),
                "width": width,
                "height": height,
                "mode": mode,
                "format": image.format,
                "array_shape": img_array.shape,
                "array_dtype": str(img_array.dtype)
            }
        }
    
    def parse_mat(self):
        data = scipy.io.loadmat(self.file_path)
        self.progress_updated.emit(50, "MAT文件解析中...")
        
        # 过滤掉MATLAB内部变量
        useful_data = {k: v for k, v in data.items() if not k.startswith('__')}
        
        return {
            "type": "MAT", 
            "data": useful_data, 
            "raw": "\n".join([f"{k}: {v.shape} {v.dtype}" for k, v in useful_data.items()]),
            "metadata": {
                "size": os.path.getsize(self.file_path),
                "variables": list(useful_data.keys()),
                "total_variables": len(useful_data)
            }
        }
    
    def parse_hdf5(self):
        data = {}
        with h5py.File(self.file_path, 'r') as f:
            # 递归读取所有数据集
            def read_datasets(name, obj):
                if isinstance(obj, h5py.Dataset):
                    data[name] = obj[()]
            
            f.visititems(read_datasets)
        
        self.progress_updated.emit(50, "HDF5文件解析中...")
        
        return {
            "type": "HDF5", 
            "data": data, 
            "raw": "\n".join([f"{k}: {v.shape} {v.dtype}" for k, v in data.items()]),
            "metadata": {
                "size": os.path.getsize(self.file_path),
                "datasets": list(data.keys()),
                "total_datasets": len(data)
            }
        }
    
    def parse_binary(self):
        with open(self.file_path, 'rb') as file:
            raw_data = file.read()
        
        self.progress_updated.emit(50, "二进制文件解析中...")
        
        # 分析二进制文件结构
        file_size = len(raw_data)
        hex_dump = self.create_hex_dump(raw_data[:1024])  # 只显示前1024字节
        
        return {
            "type": "Binary", 
            "data": raw_data, 
            "raw": hex_dump,
            "metadata": {
                "size": file_size,
                "first_100_bytes": raw_data[:100]
            }
        }
    
    def create_hex_dump(self, data, bytes_per_line=16):
        """创建十六进制转储"""
        result = ""
        for i in range(0, min(len(data), 256), bytes_per_line):
            # 十六进制部分
            hex_part = " ".join(f"{b:02x}" for b in data[i:i+bytes_per_line])
            # ASCII部分
            ascii_part = "".join(chr(b) if 32 <= b < 127 else "." for b in data[i:i+bytes_per_line])
            result += f"{i:08x}: {hex_part:<48} {ascii_part}\n"
        return result
    
    def numpy_to_string(self, arr):
        """将numpy数组转换为字符串表示"""
        if arr.size > 1000:  # 限制大型数组的输出
            return f"数组形状: {arr.shape}, 数据类型: {arr.dtype}\n前10个元素: {arr.flatten()[:10]}"
        else:
            return str(arr)

class DataTreeWidget(QTreeWidget):
    """自定义树形控件用于显示结构化数据"""
    def __init__(self):
        super().__init__()
        self.setHeaderLabel("数据结构")
        self.setColumnCount(3)
        self.setHeaderLabels(["键", "值", "类型"])
        
    def display_data(self, data, parent=None, path=""):
        if parent is None:
            self.clear()
            parent = self.invisibleRootItem()
        
        if isinstance(data, dict):
            for key, value in data.items():
                item = QTreeWidgetItem(parent)
                item.setText(0, str(key))
                item.setText(2, type(value).__name__)
                if isinstance(value, (dict, list)):
                    self.display_data(value, item, f"{path}.{key}" if path else key)
                else:
                    item.setText(1, self.format_value(value))
        elif isinstance(data, list):
            for i, value in enumerate(data):
                item = QTreeWidgetItem(parent)
                item.setText(0, f"[{i}]")
                item.setText(2, type(value).__name__)
                if isinstance(value, (dict, list)):
                    self.display_data(value, item, f"{path}[{i}]")
                else:
                    item.setText(1, self.format_value(value))
        elif hasattr(data, 'shape'):  # numpy数组
            item = QTreeWidgetItem(parent)
            item.setText(0, path if path else "数组")
            item.setText(1, f"形状: {data.shape}, 类型: {data.dtype}")
            item.setText(2, "ndarray")
        else:
            item = QTreeWidgetItem(parent)
            item.setText(0, path if path else "值")
            item.setText(1, self.format_value(data))
            item.setText(2, type(data).__name__)
    
    def format_value(self, value):
        """格式化显示值"""
        if isinstance(value, str):
            return value[:100] + "..." if len(value) > 100 else value
        elif isinstance(value, (int, float, bool)):
            return str(value)
        elif value is None:
            return "None"
        else:
            return str(type(value))

class DataTableView(QTableWidget):
    """自定义表格视图用于显示表格数据"""
    def __init__(self):
        super().__init__()
        
    def display_table_data(self, headers, rows):
        self.setRowCount(len(rows))
        self.setColumnCount(len(headers))
        self.setHorizontalHeaderLabels(headers)
        
        for row_idx, row in enumerate(rows):
            for col_idx, value in enumerate(row):
                item = QTableWidgetItem(str(value))
                self.setItem(row_idx, col_idx, item)
        
        # 自动调整列宽
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)

class ImageViewer(QGraphicsView):
    """图像查看器"""
    def __init__(self):
        super().__init__()
        self.scene = QGraphicsScene()
        self.setScene(self.scene)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.pixmap_item = None
        self.zoom_factor = 1.0
        
    def display_image(self, image):
        """显示图像"""
        self.scene.clear()
        
        if isinstance(image, Image.Image):
            # 转换PIL图像为QPixmap
            image = image.convert("RGBA")
            data = image.tobytes("raw", "RGBA")
            qimage = QImage(data, image.size[0], image.size[1], QImage.Format_RGBA8888)
            pixmap = QPixmap.fromImage(qimage)
        else:
            pixmap = QPixmap(image)
            
        self.pixmap_item = QGraphicsPixmapItem(pixmap)
        self.scene.addItem(self.pixmap_item)
        self.fitInView(self.pixmap_item, Qt.KeepAspectRatio)
        self.zoom_factor = 1.0
    
    def wheelEvent(self, event):
        """鼠标滚轮缩放"""
        zoom_in_factor = 1.25
        zoom_out_factor = 1 / zoom_in_factor
        
        # 保存场景位置
        old_pos = self.mapToScene(event.pos())
        
        # 缩放
        if event.angleDelta().y() > 0:
            zoom_factor = zoom_in_factor
            self.zoom_factor *= zoom_in_factor
        else:
            zoom_factor = zoom_out_factor
            self.zoom_factor *= zoom_out_factor
        
        self.scale(zoom_factor, zoom_factor)
        
        # 获取新位置
        new_pos = self.mapToScene(event.pos())
        
        # 移动场景以保持鼠标下的点不变
        delta = new_pos - old_pos
        self.translate(delta.x(), delta.y())
    
    def fitToWindow(self):
        """适应窗口大小"""
        if self.pixmap_item:
            self.fitInView(self.pixmap_item, Qt.KeepAspectRatio)
            self.zoom_factor = 1.0

class VisualizationDialog(QDialog):
    """数据可视化对话框"""
    def __init__(self, data, parent=None):
        super().__init__(parent)
        self.data = data
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("数据可视化")
        self.setGeometry(100, 100, 800, 600)
        
        layout = QVBoxLayout(self)
        
        # 可视化类型选择
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("可视化类型:"))
        self.viz_type = QComboBox()
        self.viz_type.addItems(["折线图", "柱状图", "散点图", "直方图", "热力图"])
        self.viz_type.currentTextChanged.connect(self.update_visualization)
        type_layout.addWidget(self.viz_type)
        type_layout.addStretch()
        
        layout.addLayout(type_layout)
        
        # 画布
        self.canvas = MplCanvas(self, width=5, height=4, dpi=100)
        layout.addWidget(self.canvas)
        
        # 按钮
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.update_visualization()
    
    def update_visualization(self):
        """更新可视化"""
        viz_type = self.viz_type.currentText()
        self.canvas.axes.clear()
        
        try:
            # 提取数值数据
            numeric_data = self.extract_numeric_data(self.data)
            
            if viz_type == "折线图":
                if numeric_data.ndim == 1:
                    self.canvas.axes.plot(numeric_data)
                else:
                    for i in range(min(numeric_data.shape[1], 10)):  # 最多显示10条线
                        self.canvas.axes.plot(numeric_data[:, i])
                self.canvas.axes.set_title("折线图")
                
            elif viz_type == "柱状图":
                if numeric_data.ndim == 1:
                    self.canvas.axes.bar(range(len(numeric_data)), numeric_data)
                else:
                    # 显示前10行
                    data_to_show = numeric_data[:10] if numeric_data.shape[0] > 10 else numeric_data
                    for i in range(data_to_show.shape[1]):
                        self.canvas.axes.bar(np.arange(data_to_show.shape[0]) + i*0.2, 
                                            data_to_show[:, i], width=0.2)
                self.canvas.axes.set_title("柱状图")
                
            elif viz_type == "散点图":
                if numeric_data.shape[1] >= 2:
                    self.canvas.axes.scatter(numeric_data[:, 0], numeric_data[:, 1])
                    self.canvas.axes.set_xlabel("X")
                    self.canvas.axes.set_ylabel("Y")
                self.canvas.axes.set_title("散点图")
                
            elif viz_type == "直方图":
                if numeric_data.ndim == 1:
                    self.canvas.axes.hist(numeric_data, bins=20)
                else:
                    self.canvas.axes.hist(numeric_data.flatten(), bins=20)
                self.canvas.axes.set_title("直方图")
                
            elif viz_type == "热力图":
                if numeric_data.ndim == 2:
                    im = self.canvas.axes.imshow(numeric_data, cmap='hot', aspect='auto')
                    self.canvas.fig.colorbar(im, ax=self.canvas.axes)
                self.canvas.axes.set_title("热力图")
            
            self.canvas.draw()
        except Exception as e:
            self.canvas.axes.text(0.5, 0.5, f"无法创建可视化: {str(e)}", 
                                 ha='center', va='center', transform=self.canvas.axes.transAxes)
            self.canvas.draw()
    
    def extract_numeric_data(self, data):
        """从数据中提取数值数据"""
        if hasattr(data, 'shape'):  # numpy数组
            return data
        elif isinstance(data, dict):
            # 尝试找到第一个数值数组
            for value in data.values():
                if hasattr(value, 'shape'):
                    return value
            # 如果没有找到，尝试将字典转换为数组
            return np.array(list(data.values()))
        elif isinstance(data, list):
            return np.array(data)
        else:
            return np.array([data])

class FileFormatParser(QMainWindow):
    """主窗口类"""
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.current_file = None
        self.parsed_data = None
        self.recent_files = []
        self.max_recent_files = 10
        
    def init_ui(self):
        self.setWindowTitle("高级文件数据格式解析器")
        self.setGeometry(100, 100, 1400, 900)
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QVBoxLayout(central_widget)
        
        # 创建工具栏
        self.create_toolbar()
        
        # 创建顶部控制面板
        control_layout = QHBoxLayout()
        
        # 文件选择区域
        file_group = QGroupBox("文件操作")
        file_layout = QHBoxLayout(file_group)
        
        self.file_path_edit = QLineEdit()
        self.file_path_edit.setPlaceholderText("选择文件路径...")
        browse_btn = QPushButton("浏览")
        browse_btn.clicked.connect(self.browse_file)
        
        self.file_type_combo = QComboBox()
        self.file_type_combo.addItems(["自动检测", "JSON", "CSV", "XML", "YAML", "TXT", 
                                      "Pickle", "NPY", "NPZ", "PT/PTH", "Image", 
                                      "MAT", "HDF5", "Binary"])
        
        parse_btn = QPushButton("解析文件")
        parse_btn.clicked.connect(self.parse_file)
        
        file_layout.addWidget(QLabel("文件路径:"))
        file_layout.addWidget(self.file_path_edit)
        file_layout.addWidget(browse_btn)
        file_layout.addWidget(QLabel("文件类型:"))
        file_layout.addWidget(self.file_type_combo)
        file_layout.addWidget(parse_btn)
        
        # 选项区域
        options_group = QGroupBox("解析选项")
        options_layout = QHBoxLayout(options_group)
        
        self.pretty_print_check = QCheckBox("美化输出")
        self.pretty_print_check.setChecked(True)
        
        self.validate_check = QCheckBox("验证格式")
        self.validate_check.setChecked(True)
        
        self.auto_visualize_check = QCheckBox("自动可视化")
        self.auto_visualize_check.setChecked(False)
        
        options_layout.addWidget(self.pretty_print_check)
        options_layout.addWidget(self.validate_check)
        options_layout.addWidget(self.auto_visualize_check)
        options_layout.addStretch()
        
        control_layout.addWidget(file_group)
        control_layout.addWidget(options_group)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_label = QLabel("就绪")
        
        # 创建分割器用于显示数据
        main_splitter = QSplitter(Qt.Horizontal)
        
        # 左侧：文件信息和导航
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        # 文件信息
        info_group = QGroupBox("文件信息")
        info_layout = QVBoxLayout(info_group)
        self.file_info_text = QTextEdit()
        self.file_info_text.setMaximumHeight(150)
        info_layout.addWidget(self.file_info_text)
        
        # 数据导航
        nav_group = QGroupBox("数据导航")
        nav_layout = QVBoxLayout(nav_group)
        self.tree_widget = DataTreeWidget()
        nav_layout.addWidget(self.tree_widget)
        
        left_layout.addWidget(info_group)
        left_layout.addWidget(nav_group)
        
        # 右侧：标签页显示不同视图
        self.tab_widget = QTabWidget()
        
        # 原始数据标签页
        self.raw_text_edit = QTextEdit()
        self.raw_text_edit.setFont(QFont("Consolas", 10))
        self.tab_widget.addTab(self.raw_text_edit, "原始数据")
        
        # 表格视图标签页
        self.table_view = DataTableView()
        self.tab_widget.addTab(self.table_view, "表格视图")
        
        # 图像视图标签页
        self.image_viewer = ImageViewer()
        self.tab_widget.addTab(self.image_viewer, "图像视图")
        
        # 统计信息标签页
        self.stats_text_edit = QTextEdit()
        self.stats_text_edit.setFont(QFont("Consolas", 10))
        self.tab_widget.addTab(self.stats_text_edit, "统计信息")
        
        # 十六进制视图标签页
        self.hex_text_edit = QTextEdit()
        self.hex_text_edit.setFont(QFont("Consolas", 10))
        self.tab_widget.addTab(self.hex_text_edit, "十六进制视图")
        
        main_splitter.addWidget(left_widget)
        main_splitter.addWidget(self.tab_widget)
        main_splitter.setSizes([300, 1100])
        
        # 添加到主布局
        main_layout.addLayout(control_layout)
        main_layout.addWidget(self.progress_label)
        main_layout.addWidget(self.progress_bar)
        main_layout.addWidget(main_splitter)
        
        # 状态栏
        self.statusBar().showMessage("就绪")
        
        # 加载最近文件列表
        self.load_recent_files()
    
    def create_toolbar(self):
        """创建工具栏"""
        toolbar = QToolBar("主工具栏")
        toolbar.setIconSize(QSize(16, 16))
        self.addToolBar(toolbar)
        
        # 文件操作
        open_action = QAction("打开", self)
        open_action.triggered.connect(self.browse_file)
        toolbar.addAction(open_action)
        
        toolbar.addSeparator()
        
        # 可视化操作
        viz_action = QAction("可视化", self)
        viz_action.triggered.connect(self.show_visualization)
        toolbar.addAction(viz_action)
        
        export_action = QAction("导出", self)
        export_action.triggered.connect(self.export_data)
        toolbar.addAction(export_action)
        
        toolbar.addSeparator()
        
        # 工具菜单
        tools_menu = QToolButton()
        tools_menu.setText("工具")
        tools_menu.setPopupMode(QToolButton.InstantPopup)
        tools_menu.setMenu(self.create_tools_menu())
        toolbar.addWidget(tools_menu)
    
    def create_tools_menu(self):
        """创建工具菜单"""
        menu = QMenu(self)
        
        # 数据转换操作
        convert_action = menu.addAction("数据转换")
        convert_action.triggered.connect(self.convert_data)
        
        menu.addSeparator()
        
        # 分析操作
        analyze_action = menu.addAction("数据分析")
        analyze_action.triggered.connect(self.analyze_data)
        
        return menu
    
    def browse_file(self):
        """浏览文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "选择文件", 
            "", 
            "所有支持的文件 (*.json *.csv *.xml *.yaml *.yml *.txt *.pkl *.pickle *.npy *.npz *.pt *.pth *.jpg *.jpeg *.png *.bmp *.tiff *.mat *.h5 *.hdf5);;"
            "JSON 文件 (*.json);;CSV 文件 (*.csv);;XML 文件 (*.xml);;"
            "YAML 文件 (*.yaml *.yml);;文本文件 (*.txt);;"
            "Pickle 文件 (*.pkl *.pickle);;NumPy 文件 (*.npy *.npz);;"
            "PyTorch 模型 (*.pt *.pth);;图像文件 (*.jpg *.jpeg *.png *.bmp *.tiff);;"
            "MATLAB 文件 (*.mat);;HDF5 文件 (*.h5 *.hdf5);;"
            "所有文件 (*.*)"
        )
        
        if file_path:
            self.file_path_edit.setText(file_path)
            # 尝试自动检测文件类型
            self.auto_detect_file_type(file_path)
            # 添加到最近文件列表
            self.add_to_recent_files(file_path)
    
    def auto_detect_file_type(self, file_path):
        """自动检测文件类型"""
        _, ext = os.path.splitext(file_path)
        ext = ext.lower()
        
        type_mapping = {
            '.json': 'JSON',
            '.csv': 'CSV',
            '.xml': 'XML',
            '.yaml': 'YAML',
            '.yml': 'YAML',
            '.txt': 'TXT',
            '.pkl': 'Pickle',
            '.pickle': 'Pickle',
            '.npy': 'NPY',
            '.npz': 'NPZ',
            '.pt': 'PT/PTH',
            '.pth': 'PT/PTH',
            '.jpg': 'Image',
            '.jpeg': 'Image',
            '.png': 'Image',
            '.bmp': 'Image',
            '.tiff': 'Image',
            '.mat': 'MAT',
            '.h5': 'HDF5',
            '.hdf5': 'HDF5'
        }
        
        if ext in type_mapping:
            self.file_type_combo.setCurrentText(type_mapping[ext])
        else:
            self.file_type_combo.setCurrentText('自动检测')
    
    def parse_file(self):
        """解析文件"""
        file_path = self.file_path_edit.text()
        if not file_path or not os.path.exists(file_path):
            QMessageBox.warning(self, "错误", "请选择有效的文件路径")
            return
        
        file_type = self.file_type_combo.currentText()
        if file_type == "自动检测":
            _, ext = os.path.splitext(file_path)
            ext = ext.lower()
            
            type_mapping = {
                '.json': 'JSON',
                '.csv': 'CSV',
                '.xml': 'XML',
                '.yaml': 'YAML',
                '.yml': 'YAML',
                '.txt': 'TXT',
                '.pkl': 'Pickle',
                '.pickle': 'Pickle',
                '.npy': 'NPY',
                '.npz': 'NPZ',
                '.pt': 'PT/PTH',
                '.pth': 'PT/PTH',
                '.jpg': 'Image',
                '.jpeg': 'Image',
                '.png': 'Image',
                '.bmp': 'Image',
                '.tiff': 'Image',
                '.mat': 'MAT',
                '.h5': 'HDF5',
                '.hdf5': 'HDF5'
            }
            
            if ext in type_mapping:
                file_type = type_mapping[ext]
            else:
                # 尝试通过内容检测
                file_type = self.detect_file_type_by_content(file_path)
        
        # 检查依赖
        if file_type == "MAT" and not SCIPY_AVAILABLE:
            QMessageBox.warning(self, "依赖缺失", "解析MAT文件需要scipy库，请安装: pip install scipy")
            return
        if file_type == "HDF5" and not H5PY_AVAILABLE:
            QMessageBox.warning(self, "依赖缺失", "解析HDF5文件需要h5py库，请安装: pip install h5py")
            return
        
        self.current_file = file_path
        self.statusBar().showMessage(f"正在解析 {file_path}...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # 创建解析选项
        options = {
            "pretty_print": self.pretty_print_check.isChecked(),
            "validate": self.validate_check.isChecked()
        }
        
        # 创建解析线程
        self.parser_thread = FileParserThread(file_path, file_type, options)
        self.parser_thread.progress_updated.connect(self.update_progress)
        self.parser_thread.parsing_finished.connect(self.on_parsing_finished)
        self.parser_thread.error_occurred.connect(self.on_parsing_error)
        self.parser_thread.start()
    
    def detect_file_type_by_content(self, file_path):
        """通过文件内容检测文件类型"""
        try:
            with open(file_path, 'rb') as f:
                header = f.read(4)
                
            # 检查常见文件类型的魔数
            if header.startswith(b'\x89PNG'):
                return 'Image'
            elif header.startswith(b'\xff\xd8\xff'):
                return 'Image'  # JPEG
            elif header.startswith(b'BM'):
                return 'Image'  # BMP
            elif header.startswith(b'\x49\x49\x2a\x00') or header.startswith(b'\x4d\x4d\x00\x2a'):
                return 'Image'  # TIFF
            elif header.startswith(b'\x93NUMPY'):
                return 'NPY'
            elif header.startswith(b'PK'):  # ZIP格式，可能是NPZ
                return 'NPZ'
            elif header.startswith(b'{') or header.startswith(b'['):
                return 'JSON'
            elif header.startswith(b'<?xml'):
                return 'XML'
            else:
                # 尝试作为文本文件读取
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read(100)
                        if '\x00' not in content:  # 不包含空字符，可能是文本
                            return 'TXT'
                except:
                    pass
                
                return 'Binary'
        except:
            return 'Binary'
    
    def update_progress(self, value, message):
        """更新进度条"""
        self.progress_bar.setValue(value)
        self.progress_label.setText(message)
    
    def on_parsing_finished(self, data):
        """解析完成处理"""
        self.progress_bar.setVisible(False)
        self.progress_label.setText("解析完成")
        self.statusBar().showMessage("解析完成")
        self.parsed_data = data
        
        # 显示数据
        self.display_parsed_data(data)
        
        # 如果启用了自动可视化，显示可视化对话框
        if self.auto_visualize_check.isChecked():
            QTimer.singleShot(100, self.show_visualization)
    
    def on_parsing_error(self, error_msg):
        """解析错误处理"""
        self.progress_bar.setVisible(False)
        self.progress_label.setText("解析错误")
        self.statusBar().showMessage("解析错误")
        QMessageBox.critical(self, "解析错误", f"解析文件时发生错误:\n{error_msg}")
    
    def display_parsed_data(self, data):
        """显示解析后的数据"""
        file_type = data.get("type", "未知")
        parsed_data = data.get("data", {})
        raw_data = data.get("raw", "")
        metadata = data.get("metadata", {})
        
        # 显示文件信息
        self.display_file_info(metadata, file_type)
        
        # 显示原始数据
        if self.pretty_print_check.isChecked():
            self.raw_text_edit.setText(raw_data)
        else:
            # 如果是JSON，可以压缩显示
            if file_type == "JSON":
                self.raw_text_edit.setText(json.dumps(parsed_data))
            else:
                self.raw_text_edit.setText(raw_data)
        
        # 在树形视图中显示结构化数据
        if file_type in ["JSON", "XML", "YAML", "Pickle", "NPY", "NPZ", "PT/PTH", "MAT", "HDF5"]:
            self.tree_widget.display_data(parsed_data)
        elif file_type == "CSV":
            # 对于CSV，显示表格数据
            headers = parsed_data.get("headers", [])
            rows = parsed_data.get("rows", [])
            self.table_view.display_table_data(headers, rows)
            # 同时在树形视图中显示基本信息
            self.tree_widget.display_data({
                "文件类型": "CSV",
                "列数": len(headers),
                "行数": len(rows),
                "列名": headers
            })
        elif file_type == "Image":
            # 显示图像
            self.image_viewer.display_image(parsed_data)
            # 在树形视图中显示图像信息
            self.tree_widget.display_data(metadata)
        else:  # TXT, Binary
            self.tree_widget.display_data({
                "文件类型": file_type,
                "文件大小": metadata.get("size", 0),
                "编码": metadata.get("encoding", "未知")
            })
        
        # 显示统计信息
        self.display_statistics(data)
        
        # 显示十六进制视图（如果是二进制文件）
        if file_type == "Binary":
            self.hex_text_edit.setText(raw_data)
        else:
            self.hex_text_edit.setText("非二进制文件")
    
    def display_file_info(self, metadata, file_type):
        """显示文件信息"""
        info_text = f"文件类型: {file_type}\n"
        info_text += f"文件大小: {metadata.get('size', 0)} 字节\n"
        
        # 添加特定于文件类型的信息
        if file_type == "JSON":
            info_text += f"编码: {metadata.get('encoding', '未知')}\n"
        elif file_type == "CSV":
            info_text += f"编码: {metadata.get('encoding', '未知')}\n"
            info_text += f"行数: {metadata.get('rows', 0)}\n"
            info_text += f"列数: {metadata.get('columns', 0)}\n"
            info_text += f"包含标题: {'是' if metadata.get('has_header') else '否'}\n"
        elif file_type == "XML":
            info_text += f"根标签: {metadata.get('root_tag', '未知')}\n"
            info_text += f"编码: {metadata.get('encoding', '未知')}\n"
        elif file_type == "TXT":
            info_text += f"编码: {metadata.get('encoding', '未知')}\n"
            info_text += f"行数: {metadata.get('lines', 0)}\n"
            info_text += f"单词数: {metadata.get('words', 0)}\n"
        elif file_type == "NPY":
            info_text += f"形状: {metadata.get('shape', '未知')}\n"
            info_text += f"数据类型: {metadata.get('dtype', '未知')}\n"
            info_text += f"维度: {metadata.get('ndim', '未知')}\n"
        elif file_type == "NPZ":
            info_text += f"数组数量: {metadata.get('total_arrays', 0)}\n"
            info_text += f"数组名: {', '.join(metadata.get('files', []))}\n"
        elif file_type == "PT/PTH":
            model_info = metadata.get('model_info', {})
            info_text += f"类型: {model_info.get('type', '未知')}\n"
            info_text += f"张量数量: {model_info.get('tensor_count', 0)}\n"
            info_text += f"参数总数: {model_info.get('total_parameters', 0)}\n"
        elif file_type == "Image":
            info_text += f"尺寸: {metadata.get('width', 0)}x{metadata.get('height', 0)}\n"
            info_text += f"模式: {metadata.get('mode', '未知')}\n"
            info_text += f"格式: {metadata.get('format', '未知')}\n"
        elif file_type == "MAT":
            info_text += f"变量数量: {metadata.get('total_variables', 0)}\n"
            info_text += f"变量名: {', '.join(metadata.get('variables', []))}\n"
        elif file_type == "HDF5":
            info_text += f"数据集数量: {metadata.get('total_datasets', 0)}\n"
            info_text += f"数据集名: {', '.join(metadata.get('datasets', []))}\n"
        
        self.file_info_text.setText(info_text)
    
    def display_statistics(self, data):
        """显示统计信息"""
        file_type = data.get("type", "未知")
        parsed_data = data.get("data", {})
        raw_data = data.get("raw", "")
        metadata = data.get("metadata", {})
        
        stats_text = f"文件类型: {file_type}\n"
        stats_text += f"文件大小: {len(raw_data) if isinstance(raw_data, str) else metadata.get('size', 0)} 字符/字节\n"
        
        if file_type == "JSON":
            if isinstance(parsed_data, dict):
                stats_text += f"顶级键数量: {len(parsed_data)}\n"
                stats_text += self.get_json_stats(parsed_data)
        elif file_type == "CSV":
            headers = parsed_data.get("headers", [])
            rows = parsed_data.get("rows", [])
            stats_text += f"列数: {len(headers)}\n"
            stats_text += f"行数: {len(rows)}\n"
            
            # 添加列统计信息
            if rows:
                stats_text += "\n列统计:\n"
                for i, header in enumerate(headers):
                    try:
                        col_data = [float(row[i]) for row in rows if row[i] and row[i].replace('.', '').replace('-', '').isdigit()]
                        if col_data:
                            stats_text += f"  {header}: 最小值={min(col_data):.2f}, 最大值={max(col_data):.2f}, 平均值={sum(col_data)/len(col_data):.2f}\n"
                    except:
                        pass
        elif file_type == "XML":
            stats_text += self.get_xml_stats(parsed_data)
        elif file_type == "TXT":
            lines = raw_data.split('\n')
            stats_text += f"行数: {len(lines)}\n"
            stats_text += f"单词数: {len(raw_data.split())}\n"
            stats_text += f"字符数: {len(raw_data)}\n"
        elif file_type == "NPY":
            stats_text += f"形状: {metadata.get('shape', '未知')}\n"
            stats_text += f"数据类型: {metadata.get('dtype', '未知')}\n"
            if hasattr(parsed_data, 'shape'):
                stats_text += f"元素数量: {parsed_data.size}\n"
                if parsed_data.size > 0:
                    stats_text += f"最小值: {np.min(parsed_data)}\n"
                    stats_text += f"最大值: {np.max(parsed_data)}\n"
                    stats_text += f"平均值: {np.mean(parsed_data)}\n"
                    stats_text += f"标准差: {np.std(parsed_data)}\n"
        elif file_type == "NPZ":
            arrays = parsed_data
            stats_text += f"数组数量: {len(arrays)}\n"
            for key, arr in arrays.items():
                stats_text += f"\n{key}:\n"
                stats_text += f"  形状: {arr.shape}\n"
                stats_text += f"  数据类型: {arr.dtype}\n"
                if arr.size > 0:
                    stats_text += f"  元素数量: {arr.size}\n"
                    stats_text += f"  最小值: {np.min(arr)}\n"
                    stats_text += f"  最大值: {np.max(arr)}\n"
        
        self.stats_text_edit.setText(stats_text)
    
    def get_json_stats(self, data, depth=0):
        """获取JSON数据的统计信息"""
        if depth > 3:  # 限制递归深度
            return ""
        
        stats = ""
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, dict):
                    stats += f"{'  ' * depth}{key}: 对象({len(value)}个键)\n"
                    stats += self.get_json_stats(value, depth + 1)
                elif isinstance(value, list):
                    stats += f"{'  ' * depth}{key}: 数组({len(value)}个元素)\n"
                    if value and isinstance(value[0], (dict, list)):
                        stats += self.get_json_stats(value[0], depth + 1)
                else:
                    stats += f"{'  ' * depth}{key}: {type(value).__name__}\n"
        elif isinstance(data, list) and data:
            if isinstance(data[0], dict):
                stats += f"{'  ' * depth}数组元素: 对象({len(data[0])}个键)\n"
                stats += self.get_json_stats(data[0], depth + 1)
            else:
                stats += f"{'  ' * depth}数组元素: {type(data[0]).__name__}\n"
        
        return stats
    
    def get_xml_stats(self, element):
        """获取XML数据的统计信息"""
        if not isinstance(element, dict):
            return ""
        
        stats = f"标签名: {element.get('tag', '未知')}\n"
        stats += f"属性数量: {len(element.get('attributes', {}))}\n"
        stats += f"子元素数量: {len(element.get('children', []))}\n"
        
        if element.get('text'):
            stats += f"文本长度: {len(element.get('text', ''))}\n"
        
        # 递归统计子元素
        for child in element.get('children', []):
            stats += self.get_xml_stats(child)
        
        return stats
    
    def show_visualization(self):
        """显示数据可视化对话框"""
        if not self.parsed_data:
            QMessageBox.warning(self, "错误", "没有可可视化的数据")
            return
        
        data = self.parsed_data.get("data")
        if data is None:
            QMessageBox.warning(self, "错误", "无法可视化此类型的数据")
            return
        
        dialog = VisualizationDialog(data, self)
        dialog.exec_()
    
    def export_data(self):
        """导出数据"""
        if not self.parsed_data:
            QMessageBox.warning(self, "错误", "没有可导出的数据")
            return
        
        file_path, selected_filter = QFileDialog.getSaveFileName(
            self, 
            "导出数据", 
            "", 
            "JSON 文件 (*.json);;CSV 文件 (*.csv);;文本文件 (*.txt);;"
            "NumPy 文件 (*.npy);;图像文件 (*.png);;所有文件 (*.*)"
        )
        
        if file_path:
            try:
                file_type = self.parsed_data.get("type", "")
                data = self.parsed_data.get("data", {})
                
                if file_path.endswith('.json') or selected_filter == "JSON 文件 (*.json)":
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump(data, f, indent=2, ensure_ascii=False)
                elif file_path.endswith('.csv') or selected_filter == "CSV 文件 (*.csv)":
                    if file_type == "CSV":
                        headers = data.get("headers", [])
                        rows = data.get("rows", [])
                        with open(file_path, 'w', encoding='utf-8', newline='') as f:
                            writer = csv.writer(f)
                            writer.writerow(headers)
                            writer.writerows(rows)
                    else:
                        # 尝试将数据转换为CSV
                        self.export_data_as_csv(data, file_path)
                elif file_path.endswith('.npy') or selected_filter == "NumPy 文件 (*.npy)":
                    if hasattr(data, 'shape'):  # numpy数组
                        np.save(file_path, data)
                    else:
                        QMessageBox.warning(self, "错误", "数据不是NumPy数组，无法保存为NPY格式")
                        return
                elif file_path.endswith('.png') or selected_filter == "图像文件 (*.png)":
                    if isinstance(data, Image.Image):
                        data.save(file_path)
                    else:
                        QMessageBox.warning(self, "错误", "数据不是图像，无法保存为PNG格式")
                        return
                else:  # 文本文件
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(self.parsed_data.get("raw", ""))
                
                QMessageBox.information(self, "成功", f"数据已导出到 {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "导出错误", f"导出数据时发生错误:\n{str(e)}")
    
    def export_data_as_csv(self, data, file_path):
        """将数据导出为CSV格式"""
        # 这是一个简单的实现，实际应用中可能需要更复杂的逻辑
        if isinstance(data, dict):
            # 如果是字典，尝试转换为表格形式
            with open(file_path, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                for key, value in data.items():
                    if isinstance(value, (list, tuple)) and all(isinstance(x, (int, float, str)) for x in value):
                        writer.writerow([key] + list(value))
                    else:
                        writer.writerow([key, str(value)])
        else:
            # 其他情况直接保存为文本
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(str(data))
    
    def convert_data(self):
        """数据转换功能"""
        QMessageBox.information(self, "功能提示", "数据转换功能正在开发中...")
    
    def analyze_data(self):
        """数据分析功能"""
        QMessageBox.information(self, "功能提示", "数据分析功能正在开发中...")
    
    def add_to_recent_files(self, file_path):
        """添加到最近文件列表"""
        if file_path in self.recent_files:
            self.recent_files.remove(file_path)
        
        self.recent_files.insert(0, file_path)
        
        # 限制最近文件数量
        if len(self.recent_files) > self.max_recent_files:
            self.recent_files = self.recent_files[:self.max_recent_files]
        
        # 保存到设置
        self.save_recent_files()
    
    def load_recent_files(self):
        """加载最近文件列表"""
        # 这里可以从配置文件或注册表加载
        # 简化实现：使用临时列表
        pass
    
    def save_recent_files(self):
        """保存最近文件列表"""
        # 这里可以保存到配置文件或注册表
        # 简化实现：暂时不保存
        pass

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("高级文件数据格式解析器")
    app.setApplicationVersion("2.0")
    
    # 设置应用程序样式
    app.setStyle('Fusion')
    
    # 设置高DPI支持
    if hasattr(Qt, 'AA_EnableHighDpiScaling'):
        app.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
        app.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    parser = FileFormatParser()
    parser.show()
    
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()