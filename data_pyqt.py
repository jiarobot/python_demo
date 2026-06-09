import os
import sys
import json
import csv
import random
import shutil
import logging
import threading
import time
from datetime import datetime
from collections import defaultdict, Counter
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Union

import numpy as np
from PIL import Image, ImageFilter, ImageEnhance, ImageOps, ImageDraw, ImageFont
import cv2
from sklearn.model_selection import train_test_split
from sklearn.cluster import KMeans
import pandas as pd
from tqdm import tqdm

# PyQt5 imports
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QPushButton, QLabel, QLineEdit, QTextEdit, QListWidget, 
                            QListWidgetItem, QProgressBar, QFileDialog, QMessageBox,
                            QTabWidget, QGroupBox, QCheckBox, QSpinBox, QDoubleSpinBox,
                            QComboBox, QSlider, QSplitter, QTreeWidget, QTreeWidgetItem,
                            QHeaderView, QDialog, QDialogButtonBox, QFormLayout,
                            QTableWidget, QTableWidgetItem, QScrollArea, QToolBar,
                            QAction, QStatusBar, QMenu, QInputDialog, QToolButton)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QSize, QSettings
from PyQt5.QtGui import QPixmap, QImage, QIcon, QFont, QPalette, QColor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('dataset_creator.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ImageProcessor:
    """高级图像处理类"""
    
    @staticmethod
    def apply_augmentation(image: Image.Image, augmentation_type: str, **kwargs) -> Image.Image:
        """应用数据增强"""
        try:
            if augmentation_type == "rotation":
                angle = kwargs.get('angle', random.randint(-30, 30))
                return image.rotate(angle, expand=True, resample=Image.BICUBIC)
            
            elif augmentation_type == "flip":
                flip_type = kwargs.get('flip_type', 'horizontal')
                if flip_type == 'horizontal':
                    return image.transpose(Image.FLIP_LEFT_RIGHT)
                else:
                    return image.transpose(Image.FLIP_TOP_BOTTOM)
            
            elif augmentation_type == "blur":
                radius = kwargs.get('radius', 1.0)
                return image.filter(ImageFilter.GaussianBlur(radius))
            
            elif augmentation_type == "brightness":
                factor = kwargs.get('factor', random.uniform(0.8, 1.2))
                enhancer = ImageEnhance.Brightness(image)
                return enhancer.enhance(factor)
            
            elif augmentation_type == "contrast":
                factor = kwargs.get('factor', random.uniform(0.8, 1.5))
                enhancer = ImageEnhance.Contrast(image)
                return enhancer.enhance(factor)
            
            elif augmentation_type == "saturation":
                factor = kwargs.get('factor', random.uniform(0.8, 1.5))
                enhancer = ImageEnhance.Color(image)
                return enhancer.enhance(factor)
            
            elif augmentation_type == "hue":
                # Convert to HSV, adjust hue, convert back
                hsv = np.array(image.convert('HSV'))
                hue_shift = kwargs.get('hue_shift', random.randint(-30, 30))
                hsv[:, :, 0] = (hsv[:, :, 0] + hue_shift) % 256
                return Image.fromarray(hsv, 'HSV').convert('RGB')
            
            elif augmentation_type == "scale":
                scale_factor = kwargs.get('scale_factor', random.uniform(0.8, 1.2))
                new_size = (int(image.width * scale_factor), int(image.height * scale_factor))
                return image.resize(new_size, Image.LANCZOS)
            
            elif augmentation_type == "translation":
                x_shift = kwargs.get('x_shift', random.randint(-50, 50))
                y_shift = kwargs.get('y_shift', random.randint(-50, 50))
                result = Image.new('RGB', image.size)
                result.paste(image, (x_shift, y_shift))
                return result
            
            elif augmentation_type == "noise":
                # Add Gaussian noise
                img_array = np.array(image)
                noise = np.random.normal(0, 25, img_array.shape).astype(np.uint8)
                noisy_array = np.clip(img_array + noise, 0, 255)
                return Image.fromarray(noisy_array.astype(np.uint8))
            
            elif augmentation_type == "cutout":
                # Random erasing / cutout
                img_array = np.array(image)
                h, w = img_array.shape[:2]
                mask_h, mask_w = random.randint(h//10, h//3), random.randint(w//10, w//3)
                top = random.randint(0, h - mask_h)
                left = random.randint(0, w - mask_w)
                img_array[top:top+mask_h, left:left+mask_w] = 0
                return Image.fromarray(img_array)
            
            else:
                return image
                
        except Exception as e:
            logger.error(f"Augmentation failed: {str(e)}")
            return image

    @staticmethod
    def analyze_image_characteristics(image_path: str) -> Dict:
        """分析图像特征"""
        try:
            img = Image.open(image_path)
            img_array = np.array(img)
            
            # Basic statistics
            stats = {
                'width': img.width,
                'height': img.height,
                'aspect_ratio': img.width / img.height,
                'mode': img.mode,
                'size_kb': os.path.getsize(image_path) / 1024,
                'brightness': np.mean(img_array) if len(img_array.shape) == 3 else img_array.mean(),
                'contrast': np.std(img_array)
            }
            
            # Color analysis for RGB images
            if len(img_array.shape) == 3:
                stats.update({
                    'red_mean': np.mean(img_array[:, :, 0]),
                    'green_mean': np.mean(img_array[:, :, 1]),
                    'blue_mean': np.mean(img_array[:, :, 2]),
                    'colorfulness': ImageProcessor.calculate_colorfulness(img_array)
                })
            
            img.close()
            return stats
            
        except Exception as e:
            logger.error(f"Image analysis failed for {image_path}: {str(e)}")
            return {}

    @staticmethod
    def calculate_colorfulness(image_array: np.ndarray) -> float:
        """计算图像色彩丰富度"""
        try:
            # Split the image into its respective RGB components
            (R, G, B) = cv2.split(image_array.astype("float"))
            
            # Compute rg = R - G
            rg = np.absolute(R - G)
            
            # Compute yb = 0.5 * (R + G) - B
            yb = np.absolute(0.5 * (R + G) - B)
            
            # Compute the mean and standard deviation of both `rg` and `yb`
            (rbMean, rbStd) = (np.mean(rg), np.std(rg))
            (ybMean, ybStd) = (np.mean(yb), np.std(yb))
            
            # Combine the mean and standard deviations
            stdRoot = np.sqrt((rbStd ** 2) + (ybStd ** 2))
            meanRoot = np.sqrt((rbMean ** 2) + (ybMean ** 2))
            
            # Derive the "colorfulness" metric
            return stdRoot + (0.3 * meanRoot)
            
        except Exception as e:
            logger.error(f"Colorfulness calculation failed: {str(e)}")
            return 0.0

class DatasetStatistics:
    """数据集统计分析类"""
    
    def __init__(self, dataset_path: str):
        self.dataset_path = dataset_path
        self.supported_formats = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif']
    
    def generate_comprehensive_stats(self) -> Dict:
        """生成全面的数据集统计信息"""
        stats = {
            'summary': {},
            'class_distribution': {},
            'image_characteristics': {},
            'quality_metrics': {},
            'split_statistics': {}
        }
        
        # Get all splits
        splits = ['train', 'val', 'test', 'raw_data']
        
        for split in splits:
            split_path = os.path.join(self.dataset_path, split)
            if not os.path.exists(split_path):
                continue
                
            stats['split_statistics'][split] = self._analyze_split(split_path)
        
        # Overall summary
        stats['summary'] = self._generate_summary(stats['split_statistics'])
        
        # Image quality analysis
        stats['quality_metrics'] = self._analyze_quality()
        
        return stats
    
    def _analyze_split(self, split_path: str) -> Dict:
        """分析单个数据集划分"""
        split_stats = {
            'total_images': 0,
            'classes': {},
            'image_sizes': [],
            'file_sizes': [],
            'formats': defaultdict(int)
        }
        
        if os.path.isdir(split_path):
            # For classified datasets
            for class_name in os.listdir(split_path):
                class_path = os.path.join(split_path, class_name)
                if os.path.isdir(class_path):
                    class_images = self._get_image_files(class_path)
                    split_stats['classes'][class_name] = len(class_images)
                    split_stats['total_images'] += len(class_images)
                    
                    # Analyze sample images from this class
                    for img_path in class_images[:10]:  # Sample 10 images
                        self._analyze_single_image(img_path, split_stats)
        
        else:
            # For unclassified datasets
            images = self._get_image_files(split_path)
            split_stats['total_images'] = len(images)
            split_stats['classes']['unclassified'] = len(images)
            
            for img_path in images[:20]:  # Sample 20 images
                self._analyze_single_image(img_path, split_stats)
        
        return split_stats
    
    def _analyze_single_image(self, image_path: str, stats: Dict):
        """分析单个图像文件"""
        try:
            # File format
            ext = os.path.splitext(image_path)[1].lower()
            stats['formats'][ext] += 1
            
            # File size
            file_size = os.path.getsize(image_path) / 1024  # KB
            stats['file_sizes'].append(file_size)
            
            # Image dimensions
            with Image.open(image_path) as img:
                stats['image_sizes'].append((img.width, img.height))
                
        except Exception as e:
            logger.warning(f"Could not analyze image {image_path}: {str(e)}")
    
    def _get_image_files(self, directory: str) -> List[str]:
        """获取目录中的所有图像文件"""
        image_files = []
        for root, _, files in os.walk(directory):
            for file in files:
                if any(file.lower().endswith(ext) for ext in self.supported_formats):
                    image_files.append(os.path.join(root, file))
        return image_files
    
    def _generate_summary(self, split_stats: Dict) -> Dict:
        """生成摘要统计"""
        summary = {
            'total_images': 0,
            'total_classes': 0,
            'avg_image_size': (0, 0),
            'avg_file_size_kb': 0,
            'dominant_format': ''
        }
        
        all_sizes = []
        all_file_sizes = []
        format_counter = Counter()
        
        for split, stats in split_stats.items():
            summary['total_images'] += stats['total_images']
            summary['total_classes'] = max(summary['total_classes'], len(stats['classes']))
            
            all_sizes.extend(stats['image_sizes'])
            all_file_sizes.extend(stats['file_sizes'])
            format_counter.update(stats['formats'])
        
        # Calculate averages
        if all_sizes:
            avg_width = np.mean([size[0] for size in all_sizes])
            avg_height = np.mean([size[1] for size in all_sizes])
            summary['avg_image_size'] = (int(avg_width), int(avg_height))
        
        if all_file_sizes:
            summary['avg_file_size_kb'] = np.mean(all_file_sizes)
        
        if format_counter:
            summary['dominant_format'] = format_counter.most_common(1)[0][0]
        
        return summary
    
    def _analyze_quality(self) -> Dict:
        """分析图像质量指标"""
        # This would implement more sophisticated quality analysis
        # For now, return basic metrics
        return {
            'brightness_variance': 'N/A',
            'contrast_quality': 'N/A',
            'sharpness_score': 'N/A',
            'noise_level': 'N/A'
        }

class WorkerThread(QThread):
    """工作线程基类"""
    
    progress_updated = pyqtSignal(int)
    status_updated = pyqtSignal(str)
    task_completed = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self._is_running = True
    
    def stop(self):
        """停止线程"""
        self._is_running = False

class DataCollectionWorker(WorkerThread):
    """数据收集工作线程"""
    
    def __init__(self, source_paths: List[str], target_path: str, max_images: int = None):
        super().__init__()
        self.source_paths = source_paths
        self.target_path = target_path
        self.max_images = max_images
        self.supported_formats = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif']
    
    def run(self):
        """运行数据收集任务"""
        try:
            total_collected = 0
            collected_files = []
            
            for source_path in self.source_paths:
                if not self._is_running:
                    break
                    
                self.status_updated.emit(f"Processing: {source_path}")
                
                if os.path.isfile(source_path):
                    if self._is_image_file(source_path):
                        collected_files.append(source_path)
                        total_collected += 1
                        
                elif os.path.isdir(source_path):
                    for root, _, files in os.walk(source_path):
                        for file in files:
                            if not self._is_running:
                                break
                                
                            if self._is_image_file(file):
                                collected_files.append(os.path.join(root, file))
                                total_collected += 1
                                
                                # Update progress
                                progress = min(90, int((len(collected_files) / (self.max_images or 1000)) * 90))
                                self.progress_updated.emit(progress)
                                
                                if self.max_images and len(collected_files) >= self.max_images:
                                    break
                        
                        if self.max_images and len(collected_files) >= self.max_images:
                            break
                
                if self.max_images and len(collected_files) >= self.max_images:
                    collected_files = collected_files[:self.max_images]
                    break
            
            # Copy files
            self.status_updated.emit("Copying files...")
            for i, file_path in enumerate(collected_files):
                if not self._is_running:
                    break
                    
                ext = os.path.splitext(file_path)[1]
                new_name = f"image_{i:06d}{ext}"
                target_file = os.path.join(self.target_path, new_name)
                shutil.copy2(file_path, target_file)
                
                # Update progress
                progress = 90 + int((i + 1) / len(collected_files) * 10)
                self.progress_updated.emit(progress)
            
            self.status_updated.emit("Data collection completed")
            self.task_completed.emit({
                'collected_count': len(collected_files),
                'target_path': self.target_path
            })
            
        except Exception as e:
            self.error_occurred.emit(f"Data collection error: {str(e)}")
    
    def _is_image_file(self, filename: str) -> bool:
        """检查文件是否为支持的图像格式"""
        return any(filename.lower().endswith(ext) for ext in self.supported_formats)

class ClassificationWorker(WorkerThread):
    """分类工作线程"""
    
    def __init__(self, source_path: str, target_path: str, class_names: List[str], classification_type: str = "manual"):
        super().__init__()
        self.source_path = source_path
        self.target_path = target_path
        self.class_names = class_names
        self.classification_type = classification_type
    
    def run(self):
        """运行分类任务"""
        try:
            if self.classification_type == "manual":
                self._run_manual_classification()
            elif self.classification_type == "auto_color":
                self._run_auto_color_classification()
            elif self.classification_type == "auto_cluster":
                self._run_auto_cluster_classification()
                
        except Exception as e:
            self.error_occurred.emit(f"Classification error: {str(e)}")
    
    def _run_manual_classification(self):
        """手动分类（这里只是模拟，实际在GUI中实现）"""
        # 在实际GUI中，这个功能会在主线程中实现
        self.status_updated.emit("Manual classification should be done in main UI")
        self.task_completed.emit({'status': 'manual_ui_required'})
    
    def _run_auto_color_classification(self):
        """基于颜色的自动分类"""
        self.status_updated.emit("Starting color-based classification...")
        
        # Create class directories
        for class_name in self.class_names:
            os.makedirs(os.path.join(self.target_path, class_name), exist_ok=True)
        
        # Color categories (simplified)
        color_categories = {
            'red': [(-10, 10), (100, 255), (100, 255)],
            'green': [(35, 85), (100, 255), (100, 255)],
            'blue': [(85, 135), (100, 255), (100, 255)],
            'yellow': [(25, 35), (100, 255), (100, 255)],
            'other': [(0, 180), (0, 255), (0, 255)]
        }
        
        image_files = [f for f in os.listdir(self.source_path) 
                      if any(f.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.bmp'])]
        
        classified_count = 0
        
        for i, filename in enumerate(image_files):
            if not self._is_running:
                break
                
            try:
                img_path = os.path.join(self.source_path, filename)
                img = cv2.imread(img_path)
                
                if img is None:
                    continue
                
                # Convert to HSV
                hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
                
                # Calculate average color
                avg_h = np.mean(hsv[:,:,0])
                avg_s = np.mean(hsv[:,:,1])
                avg_v = np.mean(hsv[:,:,2])
                
                # Classify
                predicted_class = 'other'
                for class_name, (h_range, s_range, v_range) in color_categories.items():
                    if class_name in self.class_names:
                        if (h_range[0] <= avg_h <= h_range[1] and 
                            s_range[0] <= avg_s <= s_range[1] and 
                            v_range[0] <= avg_v <= v_range[1]):
                            predicted_class = class_name
                            break
                
                # Copy to class directory
                target_dir = os.path.join(self.target_path, predicted_class)
                shutil.copy2(img_path, os.path.join(target_dir, filename))
                classified_count += 1
                
                # Update progress
                progress = int((i + 1) / len(image_files) * 100)
                self.progress_updated.emit(progress)
                self.status_updated.emit(f"Classified {i+1}/{len(image_files)} images")
                
            except Exception as e:
                logger.warning(f"Failed to classify {filename}: {str(e)}")
                continue
        
        self.status_updated.emit("Color-based classification completed")
        self.task_completed.emit({
            'classified_count': classified_count,
            'method': 'color_based'
        })
    
    def _run_auto_cluster_classification(self):
        """基于聚类的自动分类"""
        self.status_updated.emit("Starting cluster-based classification...")
        
        # This would implement K-means clustering based classification
        # For now, just create placeholder
        self.status_updated.emit("Cluster-based classification not yet implemented")
        self.task_completed.emit({'status': 'not_implemented'})

class AugmentationWorker(WorkerThread):
    """数据增强工作线程"""
    
    def __init__(self, source_path: str, target_path: str, augmentations: List[str], 
                 augmentation_factor: int = 1, image_size: Tuple[int, int] = (256, 256)):
        super().__init__()
        self.source_path = source_path
        self.target_path = target_path
        self.augmentations = augmentations
        self.augmentation_factor = augmentation_factor
        self.image_size = image_size
    
    def run(self):
        """运行数据增强任务"""
        try:
            os.makedirs(self.target_path, exist_ok=True)
            
            # Get all images
            image_files = []
            for root, _, files in os.walk(self.source_path):
                for file in files:
                    if any(file.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.bmp']):
                        image_files.append(os.path.join(root, file))
            
            total_images = len(image_files)
            total_augmented = 0
            
            for img_idx, img_path in enumerate(image_files):
                if not self._is_running:
                    break
                
                try:
                    # Open and preprocess image
                    original_img = Image.open(img_path)
                    if original_img.mode != 'RGB':
                        original_img = original_img.convert('RGB')
                    original_img = original_img.resize(self.image_size, Image.LANCZOS)
                    
                    # Get base filename
                    base_name = os.path.splitext(os.path.basename(img_path))[0]
                    
                    # Save original
                    original_img.save(os.path.join(self.target_path, f"{base_name}_original.jpg"), 
                                    quality=95)
                    total_augmented += 1
                    
                    # Apply augmentations
                    for aug_idx in range(self.augmentation_factor):
                        if not self._is_running:
                            break
                            
                        augmented_img = original_img.copy()
                        
                        # Apply random augmentations
                        for augmentation in self.augmentations:
                            if random.random() > 0.5:  # 50% chance to apply each augmentation
                                augmented_img = ImageProcessor.apply_augmentation(
                                    augmented_img, augmentation
                                )
                        
                        # Save augmented image
                        aug_name = f"{base_name}_aug_{aug_idx:02d}.jpg"
                        augmented_img.save(os.path.join(self.target_path, aug_name), quality=95)
                        total_augmented += 1
                    
                    # Update progress
                    progress = int((img_idx + 1) / total_images * 100)
                    self.progress_updated.emit(progress)
                    self.status_updated.emit(f"Augmented {img_idx+1}/{total_images} images")
                    
                except Exception as e:
                    logger.warning(f"Failed to augment {img_path}: {str(e)}")
                    continue
            
            self.status_updated.emit("Data augmentation completed")
            self.task_completed.emit({
                'original_count': total_images,
                'augmented_count': total_augmented,
                'total_count': total_augmented
            })
            
        except Exception as e:
            self.error_occurred.emit(f"Augmentation error: {str(e)}")

class DatasetCreatorGUI(QMainWindow):
    """数据集创建工具的主GUI界面"""
    
    def __init__(self):
        super().__init__()
        self.dataset_creator = EnhancedDatasetCreator()
        self.current_dataset_path = None
        self.worker_thread = None
        self.settings = QSettings("DatasetCreator", "DatasetTool")
        
        self.init_ui()
        self.load_settings()
    
    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("Advanced Dataset Creator")
        self.setGeometry(100, 100, 1400, 900)
        
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Create toolbar
        self.create_toolbar()
        
        # Create tab widget
        tab_widget = QTabWidget()
        main_layout.addWidget(tab_widget)
        
        # Create tabs
        self.setup_tab = self.create_setup_tab()
        self.collection_tab = self.create_collection_tab()
        self.preprocessing_tab = self.create_preprocessing_tab()
        self.classification_tab = self.create_classification_tab()
        self.augmentation_tab = self.create_augmentation_tab()
        self.analysis_tab = self.create_analysis_tab()
        
        tab_widget.addTab(self.setup_tab, "Dataset Setup")
        tab_widget.addTab(self.collection_tab, "Data Collection")
        tab_widget.addTab(self.preprocessing_tab, "Preprocessing")
        tab_widget.addTab(self.classification_tab, "Classification")
        tab_widget.addTab(self.augmentation_tab, "Augmentation")
        tab_widget.addTab(self.analysis_tab, "Analysis")
        
        # Create status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
        
        # Create progress bar
        self.progress_bar = QProgressBar()
        self.status_bar.addPermanentWidget(self.progress_bar)
        self.progress_bar.setVisible(False)
    
    def create_toolbar(self):
        """创建工具栏"""
        toolbar = QToolBar("Main Toolbar")
        toolbar.setIconSize(QSize(16, 16))
        self.addToolBar(toolbar)
        
        # New dataset action
        new_action = QAction("New Dataset", self)
        new_action.triggered.connect(self.new_dataset)
        toolbar.addAction(new_action)
        
        # Open dataset action
        open_action = QAction("Open Dataset", self)
        open_action.triggered.connect(self.open_dataset)
        toolbar.addAction(open_action)
        
        toolbar.addSeparator()
        
        # Save action
        save_action = QAction("Save Project", self)
        save_action.triggered.connect(self.save_project)
        toolbar.addAction(save_action)
        
        # Export action
        export_action = QAction("Export Dataset", self)
        export_action.triggered.connect(self.export_dataset)
        toolbar.addAction(export_action)
    
    def create_setup_tab(self):
        """创建数据集设置标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Dataset configuration group
        config_group = QGroupBox("Dataset Configuration")
        config_layout = QFormLayout(config_group)
        
        self.dataset_name_edit = QLineEdit()
        self.dataset_name_edit.setText("my_dataset")
        config_layout.addRow("Dataset Name:", self.dataset_name_edit)
        
        self.base_path_edit = QLineEdit()
        self.base_path_edit.setText(os.path.expanduser("~/datasets"))
        config_layout.addRow("Base Path:", self.base_path_edit)
        
        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self.browse_base_path)
        config_layout.addRow("", browse_btn)
        
        self.class_names_edit = QTextEdit()
        self.class_names_edit.setPlaceholderText("Enter class names, one per line\nExample:\ncat\ndog\nbird")
        config_layout.addRow("Class Names:", self.class_names_edit)
        
        self.description_edit = QTextEdit()
        self.description_edit.setPlaceholderText("Dataset description...")
        config_layout.addRow("Description:", self.description_edit)
        
        layout.addWidget(config_group)
        
        # Split ratios group
        split_group = QGroupBox("Dataset Split Ratios")
        split_layout = QHBoxLayout(split_group)
        
        self.train_ratio_spin = QDoubleSpinBox()
        self.train_ratio_spin.setRange(0.0, 1.0)
        self.train_ratio_spin.setValue(0.7)
        self.train_ratio_spin.setSingleStep(0.05)
        split_layout.addWidget(QLabel("Train:"))
        split_layout.addWidget(self.train_ratio_spin)
        
        self.val_ratio_spin = QDoubleSpinBox()
        self.val_ratio_spin.setRange(0.0, 1.0)
        self.val_ratio_spin.setValue(0.15)
        self.val_ratio_spin.setSingleStep(0.05)
        split_layout.addWidget(QLabel("Validation:"))
        split_layout.addWidget(self.val_ratio_spin)
        
        self.test_ratio_spin = QDoubleSpinBox()
        self.test_ratio_spin.setRange(0.0, 1.0)
        self.test_ratio_spin.setValue(0.15)
        self.test_ratio_spin.setSingleStep(0.05)
        split_layout.addWidget(QLabel("Test:"))
        split_layout.addWidget(self.test_ratio_spin)
        
        layout.addWidget(split_group)
        
        # Create button
        create_btn = QPushButton("Create Dataset Structure")
        create_btn.clicked.connect(self.create_dataset_structure)
        layout.addWidget(create_btn)
        
        layout.addStretch()
        return widget
    
    def create_collection_tab(self):
        """创建数据收集标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Source paths group
        source_group = QGroupBox("Source Paths")
        source_layout = QVBoxLayout(source_group)
        
        self.source_list = QListWidget()
        source_layout.addWidget(self.source_list)
        
        source_buttons_layout = QHBoxLayout()
        add_file_btn = QPushButton("Add Files")
        add_file_btn.clicked.connect(self.add_source_files)
        source_buttons_layout.addWidget(add_file_btn)
        
        add_folder_btn = QPushButton("Add Folder")
        add_folder_btn.clicked.connect(self.add_source_folder)
        source_buttons_layout.addWidget(add_folder_btn)
        
        remove_btn = QPushButton("Remove Selected")
        remove_btn.clicked.connect(self.remove_source_path)
        source_buttons_layout.addWidget(remove_btn)
        
        source_layout.addLayout(source_buttons_layout)
        
        layout.addWidget(source_group)
        
        # Collection options
        options_group = QGroupBox("Collection Options")
        options_layout = QFormLayout(options_group)
        
        self.max_images_spin = QSpinBox()
        self.max_images_spin.setRange(0, 100000)
        self.max_images_spin.setValue(1000)
        self.max_images_spin.setSpecialValueText("No limit")
        options_layout.addRow("Max Images per Source:", self.max_images_spin)
        
        self.recursive_check = QCheckBox("Include subdirectories")
        self.recursive_check.setChecked(True)
        options_layout.addRow("", self.recursive_check)
        
        layout.addWidget(options_group)
        
        # Start collection button
        collect_btn = QPushButton("Start Data Collection")
        collect_btn.clicked.connect(self.start_data_collection)
        layout.addWidget(collect_btn)
        
        layout.addStretch()
        return widget
    
    def create_preprocessing_tab(self):
        """创建预处理标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Preprocessing options
        preprocess_group = QGroupBox("Preprocessing Options")
        preprocess_layout = QFormLayout(preprocess_group)
        
        self.resize_check = QCheckBox("Resize images")
        self.resize_check.setChecked(True)
        preprocess_layout.addRow("", self.resize_check)
        
        resize_layout = QHBoxLayout()
        self.width_spin = QSpinBox()
        self.width_spin.setRange(1, 4096)
        self.width_spin.setValue(256)
        resize_layout.addWidget(QLabel("Width:"))
        resize_layout.addWidget(self.width_spin)
        
        self.height_spin = QSpinBox()
        self.height_spin.setRange(1, 4096)
        self.height_spin.setValue(256)
        resize_layout.addWidget(QLabel("Height:"))
        resize_layout.addWidget(self.height_spin)
        preprocess_layout.addRow("Image Size:", resize_layout)
        
        self.format_combo = QComboBox()
        self.format_combo.addItems(["JPEG", "PNG", "BMP"])
        preprocess_layout.addRow("Output Format:", self.format_combo)
        
        self.quality_slider = QSlider(Qt.Horizontal)
        self.quality_slider.setRange(1, 100)
        self.quality_slider.setValue(95)
        preprocess_layout.addRow("Quality:", self.quality_slider)
        
        self.enhance_check = QCheckBox("Enhance image quality")
        self.enhance_check.setChecked(True)
        preprocess_layout.addRow("", self.enhance_check)
        
        layout.addWidget(preprocess_group)
        
        # Start preprocessing button
        preprocess_btn = QPushButton("Start Preprocessing")
        preprocess_btn.clicked.connect(self.start_preprocessing)
        layout.addWidget(preprocess_btn)
        
        layout.addStretch()
        return widget
    
    def create_classification_tab(self):
        """创建分类标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Classification type
        type_group = QGroupBox("Classification Type")
        type_layout = QVBoxLayout(type_group)
        
        self.classification_type_combo = QComboBox()
        self.classification_type_combo.addItems([
            "Manual Classification", 
            "Auto Classification (Color-based)",
            "Auto Classification (Cluster-based)"
        ])
        type_layout.addWidget(self.classification_type_combo)
        
        layout.addWidget(type_group)
        
        # Manual classification instructions
        manual_group = QGroupBox("Manual Classification")
        manual_layout = QVBoxLayout(manual_group)
        
        instructions = QLabel(
            "For manual classification:\n"
            "1. Click 'Start Manual Classification'\n"
            "2. Images will be shown one by one\n"
            "3. Use number keys to assign classes\n"
            "4. Use 'D' to delete, 'S' to skip\n"
            "5. Use 'Q' to quit\n\n"
            "Class assignments:\n"
            "1: First class, 2: Second class, etc."
        )
        instructions.setWordWrap(True)
        manual_layout.addWidget(instructions)
        
        start_manual_btn = QPushButton("Start Manual Classification")
        start_manual_btn.clicked.connect(self.start_manual_classification)
        manual_layout.addWidget(start_manual_btn)
        
        layout.addWidget(manual_group)
        
        # Auto classification
        auto_group = QGroupBox("Auto Classification")
        auto_layout = QVBoxLayout(auto_group)
        
        start_auto_btn = QPushButton("Start Auto Classification")
        start_auto_btn.clicked.connect(self.start_auto_classification)
        auto_layout.addWidget(start_auto_btn)
        
        layout.addWidget(auto_group)
        
        layout.addStretch()
        return widget
    
    def create_augmentation_tab(self):
        """创建数据增强标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Augmentation options
        aug_group = QGroupBox("Augmentation Techniques")
        aug_layout = QVBoxLayout(aug_group)
        
        self.rotation_check = QCheckBox("Rotation (±30°)")
        aug_layout.addWidget(self.rotation_check)
        
        self.flip_check = QCheckBox("Random Flip")
        aug_layout.addWidget(self.flip_check)
        
        self.brightness_check = QCheckBox("Brightness Adjustment")
        aug_layout.addWidget(self.brightness_check)
        
        self.contrast_check = QCheckBox("Contrast Adjustment")
        aug_layout.addWidget(self.contrast_check)
        
        self.blur_check = QCheckBox("Gaussian Blur")
        aug_layout.addWidget(self.blur_check)
        
        self.noise_check = QCheckBox("Add Noise")
        aug_layout.addWidget(self.noise_check)
        
        self.cutout_check = QCheckBox("Random Cutout")
        aug_layout.addWidget(self.cutout_check)
        
        layout.addWidget(aug_group)
        
        # Augmentation parameters
        param_group = QGroupBox("Augmentation Parameters")
        param_layout = QFormLayout(param_group)
        
        self.augmentation_factor_spin = QSpinBox()
        self.augmentation_factor_spin.setRange(1, 20)
        self.augmentation_factor_spin.setValue(5)
        param_layout.addRow("Augmentations per Image:", self.augmentation_factor_spin)
        
        layout.addWidget(param_group)
        
        # Start augmentation button
        augment_btn = QPushButton("Start Data Augmentation")
        augment_btn.clicked.connect(self.start_augmentation)
        layout.addWidget(augment_btn)
        
        layout.addStretch()
        return widget
    
    def create_analysis_tab(self):
        """创建分析标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Analysis controls
        controls_group = QGroupBox("Analysis Controls")
        controls_layout = QHBoxLayout(controls_group)
        
        analyze_btn = QPushButton("Analyze Dataset")
        analyze_btn.clicked.connect(self.analyze_dataset)
        controls_layout.addWidget(analyze_btn)
        
        generate_report_btn = QPushButton("Generate Report")
        generate_report_btn.clicked.connect(self.generate_report)
        controls_layout.addWidget(generate_report_btn)
        
        layout.addWidget(controls_group)
        
        # Results display
        self.analysis_text = QTextEdit()
        self.analysis_text.setReadOnly(True)
        layout.addWidget(self.analysis_text)
        
        return widget
    
    def browse_base_path(self):
        """浏览选择基础路径"""
        path = QFileDialog.getExistingDirectory(self, "Select Base Directory")
        if path:
            self.base_path_edit.setText(path)
    
    def add_source_files(self):
        """添加源文件"""
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select Image Files", "", 
            "Image Files (*.jpg *.jpeg *.png *.bmp *.tiff *.tif)"
        )
        for file in files:
            self.source_list.addItem(file)
    
    def add_source_folder(self):
        """添加源文件夹"""
        folder = QFileDialog.getExistingDirectory(self, "Select Source Folder")
        if folder:
            self.source_list.addItem(folder)
    
    def remove_source_path(self):
        """移除选中的源路径"""
        current_row = self.source_list.currentRow()
        if current_row >= 0:
            self.source_list.takeItem(current_row)
    
    def create_dataset_structure(self):
        """创建数据集结构"""
        try:
            dataset_name = self.dataset_name_edit.text().strip()
            base_path = self.base_path_edit.text().strip()
            class_names_text = self.class_names_edit.toPlainText().strip()
            
            if not dataset_name:
                QMessageBox.warning(self, "Warning", "Please enter a dataset name")
                return
            
            if not base_path:
                QMessageBox.warning(self, "Warning", "Please select a base path")
                return
            
            if not class_names_text:
                QMessageBox.warning(self, "Warning", "Please enter class names")
                return
            
            class_names = [name.strip() for name in class_names_text.split('\n') if name.strip()]
            
            dataset_path = self.dataset_creator.create_folder_structure(base_path, dataset_name)
            self.current_dataset_path = dataset_path
            
            # Save dataset configuration
            config = {
                'dataset_name': dataset_name,
                'base_path': base_path,
                'class_names': class_names,
                'description': self.description_edit.toPlainText(),
                'train_ratio': self.train_ratio_spin.value(),
                'val_ratio': self.val_ratio_spin.value(),
                'test_ratio': self.test_ratio_spin.value(),
                'created_date': datetime.now().isoformat()
            }
            
            config_path = os.path.join(dataset_path, 'dataset_config.json')
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            
            QMessageBox.information(self, "Success", 
                                  f"Dataset structure created at:\n{dataset_path}")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create dataset: {str(e)}")
    
    def start_data_collection(self):
        """开始数据收集"""
        if not self.current_dataset_path:
            QMessageBox.warning(self, "Warning", "Please create a dataset first")
            return
        
        source_paths = []
        for i in range(self.source_list.count()):
            source_paths.append(self.source_list.item(i).text())
        
        if not source_paths:
            QMessageBox.warning(self, "Warning", "Please add source paths")
            return
        
        target_path = os.path.join(self.current_dataset_path, 'raw_data')
        max_images = self.max_images_spin.value()
        if max_images == 0:
            max_images = None
        
        self.worker_thread = DataCollectionWorker(source_paths, target_path, max_images)
        self.connect_worker_signals(self.worker_thread)
        self.worker_thread.start()
        
        self.progress_bar.setVisible(True)
        self.status_bar.showMessage("Collecting data...")
    
    def start_preprocessing(self):
        """开始预处理"""
        if not self.current_dataset_path:
            QMessageBox.warning(self, "Warning", "Please create a dataset first")
            return
        
        # This would start preprocessing in a worker thread
        QMessageBox.information(self, "Info", "Preprocessing would start here")
    
    def start_manual_classification(self):
        """开始手动分类"""
        if not self.current_dataset_path:
            QMessageBox.warning(self, "Warning", "Please create a dataset first")
            return
        
        # This would open a manual classification dialog
        QMessageBox.information(self, "Info", "Manual classification dialog would open here")
    
    def start_auto_classification(self):
        """开始自动分类"""
        if not self.current_dataset_path:
            QMessageBox.warning(self, "Warning", "Please create a dataset first")
            return
        
        classification_type = self.classification_type_combo.currentText()
        if "Color-based" in classification_type:
            auto_type = "auto_color"
        elif "Cluster-based" in classification_type:
            auto_type = "auto_cluster"
        else:
            auto_type = "auto_color"
        
        source_path = os.path.join(self.current_dataset_path, 'processed_data', 'images')
        target_path = os.path.join(self.current_dataset_path, 'processed_data', 'classified')
        
        # Get class names from configuration
        config_path = os.path.join(self.current_dataset_path, 'dataset_config.json')
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = json.load(f)
                class_names = config.get('class_names', [])
        else:
            class_names = ["class_1", "class_2", "class_3"]  # Default
        
        self.worker_thread = ClassificationWorker(source_path, target_path, class_names, auto_type)
        self.connect_worker_signals(self.worker_thread)
        self.worker_thread.start()
        
        self.progress_bar.setVisible(True)
        self.status_bar.showMessage("Running auto classification...")
    
    def start_augmentation(self):
        """开始数据增强"""
        if not self.current_dataset_path:
            QMessageBox.warning(self, "Warning", "Please create a dataset first")
            return
        
        # Get selected augmentations
        augmentations = []
        if self.rotation_check.isChecked():
            augmentations.append("rotation")
        if self.flip_check.isChecked():
            augmentations.append("flip")
        if self.brightness_check.isChecked():
            augmentations.append("brightness")
        if self.contrast_check.isChecked():
            augmentations.append("contrast")
        if self.blur_check.isChecked():
            augmentations.append("blur")
        if self.noise_check.isChecked():
            augmentations.append("noise")
        if self.cutout_check.isChecked():
            augmentations.append("cutout")
        
        if not augmentations:
            QMessageBox.warning(self, "Warning", "Please select at least one augmentation technique")
            return
        
        source_path = os.path.join(self.current_dataset_path, 'processed_data', 'classified')
        target_path = os.path.join(self.current_dataset_path, 'processed_data', 'augmented')
        augmentation_factor = self.augmentation_factor_spin.value()
        image_size = (self.width_spin.value(), self.height_spin.value())
        
        self.worker_thread = AugmentationWorker(source_path, target_path, augmentations, 
                                              augmentation_factor, image_size)
        self.connect_worker_signals(self.worker_thread)
        self.worker_thread.start()
        
        self.progress_bar.setVisible(True)
        self.status_bar.showMessage("Running data augmentation...")
    
    def analyze_dataset(self):
        """分析数据集"""
        if not self.current_dataset_path:
            QMessageBox.warning(self, "Warning", "Please create a dataset first")
            return
        
        try:
            analyzer = DatasetStatistics(self.current_dataset_path)
            stats = analyzer.generate_comprehensive_stats()
            
            # Display results
            result_text = "Dataset Analysis Results:\n\n"
            result_text += f"Total Images: {stats['summary']['total_images']}\n"
            result_text += f"Total Classes: {stats['summary']['total_classes']}\n"
            result_text += f"Average Image Size: {stats['summary']['avg_image_size']}\n"
            result_text += f"Average File Size: {stats['summary']['avg_file_size_kb']:.1f} KB\n"
            result_text += f"Dominant Format: {stats['summary']['dominant_format']}\n\n"
            
            result_text += "Class Distribution:\n"
            for split, split_stats in stats['split_statistics'].items():
                result_text += f"\n{split.upper()}:\n"
                for class_name, count in split_stats['classes'].items():
                    result_text += f"  {class_name}: {count}\n"
            
            self.analysis_text.setPlainText(result_text)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Analysis failed: {str(e)}")
    
    def generate_report(self):
        """生成报告"""
        if not self.current_dataset_path:
            QMessageBox.warning(self, "Warning", "Please create a dataset first")
            return
        
        # This would generate a comprehensive PDF report
        QMessageBox.information(self, "Info", "Report generation would start here")
    
    def connect_worker_signals(self, worker):
        """连接工作线程信号"""
        worker.progress_updated.connect(self.progress_bar.setValue)
        worker.status_updated.connect(self.status_bar.showMessage)
        worker.task_completed.connect(self.on_task_completed)
        worker.error_occurred.connect(self.on_worker_error)
    
    def on_task_completed(self, result):
        """任务完成处理"""
        self.progress_bar.setVisible(False)
        self.status_bar.showMessage("Task completed successfully")
        
        # Show completion message
        task_type = result.get('method', 'task')
        if 'collected_count' in result:
            QMessageBox.information(self, "Success", 
                                  f"Collected {result['collected_count']} images")
        elif 'classified_count' in result:
            QMessageBox.information(self, "Success",
                                  f"Classified {result['classified_count']} images")
        elif 'augmented_count' in result:
            QMessageBox.information(self, "Success",
                                  f"Generated {result['augmented_count']} images "
                                  f"({result['original_count']} original + "
                                  f"{result['augmented_count'] - result['original_count']} augmented)")
    
    def on_worker_error(self, error_message):
        """工作线程错误处理"""
        self.progress_bar.setVisible(False)
        self.status_bar.showMessage("Task failed")
        QMessageBox.critical(self, "Error", error_message)
    
    def new_dataset(self):
        """新建数据集"""
        # Reset UI fields
        self.dataset_name_edit.clear()
        self.class_names_edit.clear()
        self.description_edit.clear()
        self.source_list.clear()
        self.current_dataset_path = None
        
        self.status_bar.showMessage("New dataset ready")
    
    def open_dataset(self):
        """打开现有数据集"""
        path = QFileDialog.getExistingDirectory(self, "Open Dataset Directory")
        if path and os.path.exists(os.path.join(path, 'dataset_config.json')):
            self.current_dataset_path = path
            
            # Load configuration
            config_path = os.path.join(path, 'dataset_config.json')
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            # Update UI
            self.dataset_name_edit.setText(config.get('dataset_name', ''))
            self.base_path_edit.setText(config.get('base_path', ''))
            self.class_names_edit.setPlainText('\n'.join(config.get('class_names', [])))
            self.description_edit.setPlainText(config.get('description', ''))
            
            ratios = config.get('train_ratio', 0.7), config.get('val_ratio', 0.15), config.get('test_ratio', 0.15)
            self.train_ratio_spin.setValue(ratios[0])
            self.val_ratio_spin.setValue(ratios[1])
            self.test_ratio_spin.setValue(ratios[2])
            
            self.status_bar.showMessage(f"Opened dataset: {path}")
        else:
            QMessageBox.warning(self, "Warning", "Selected directory is not a valid dataset")
    
    def save_project(self):
        """保存项目"""
        QMessageBox.information(self, "Info", "Project save functionality would be implemented here")
    
    def export_dataset(self):
        """导出数据集"""
        QMessageBox.information(self, "Info", "Dataset export functionality would be implemented here")
    
    def load_settings(self):
        """加载设置"""
        self.settings.beginGroup("MainWindow")
        geometry = self.settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
        self.settings.endGroup()
    
    def closeEvent(self, event):
        """关闭事件处理"""
        self.settings.beginGroup("MainWindow")
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.endGroup()
        
        # Stop any running worker threads
        if self.worker_thread and self.worker_thread.isRunning():
            self.worker_thread.stop()
            self.worker_thread.wait(2000)  # Wait up to 2 seconds
        
        event.accept()

class EnhancedDatasetCreator:
    """增强的数据集创建器，包含更多高级功能"""
    
    def __init__(self):
        self.supported_formats = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif']
        self.default_image_size = (256, 256)
        
    def create_folder_structure(self, base_path, dataset_name):
        """创建增强的文件夹结构"""
        dataset_path = os.path.join(base_path, dataset_name)
        
        folders = [
            'raw_data',                    # 原始数据
            'processed_data/images',       # 处理后的图像
            'processed_data/augmented',    # 增强后的图像
            'processed_data/classified',   # 分类后的图像
            'train',                       # 训练集
            'val',                         # 验证集
            'test',                        # 测试集
            'annotations',                 # 标注文件
            'metadata',                    # 元数据
            'exports',                     # 导出文件
            'backups',                     # 备份
            'logs'                         # 日志文件
        ]
        
        # 创建主文件夹
        os.makedirs(dataset_path, exist_ok=True)
        
        # 创建子文件夹
        for folder in folders:
            os.makedirs(os.path.join(dataset_path, folder), exist_ok=True)
            
        return dataset_path
    
    # 其他方法保持不变，但可以添加更多增强功能...
    # 这里可以添加更多高级功能，如智能数据平衡、自动标注等

def main():
    """主函数"""
    app = QApplication(sys.argv)
    app.setApplicationName("Advanced Dataset Creator")
    app.setApplicationVersion("2.0")
    app.setOrganizationName("DatasetTools")
    
    # 设置现代风格
    app.setStyle('Fusion')
    
    window = DatasetCreatorGUI()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()