import torch
import cv2
import numpy as np
from PIL import Image
import matplotlib.pyplot as plt
from sklearn.cluster import HDBSCAN, DBSCAN
from sklearn.metrics.pairwise import cosine_similarity, euclidean_distances
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
from sklearn.preprocessing import StandardScaler
from sklearn.mixture import GaussianMixture
import torchvision.transforms as T
import torch.nn as nn
import torch.nn.functional as F
import os
import json
import pickle
from datetime import datetime
from collections import defaultdict, deque
import warnings
warnings.filterwarnings('ignore')

# 高级机器学习库
import umap
#import faiss
from scipy.spatial import cKDTree
from scipy.stats import entropy

# PyQt相关导入
import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QFileDialog, 
                             QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox,
                             QGroupBox, QProgressBar, QMessageBox, QTabWidget,
                             QListWidget, QSplitter, QSlider, QCheckBox, QTableWidget,
                             QTableWidgetItem, QHeaderView, QTreeWidget, QTreeWidgetItem,
                             QDockWidget, QToolBar, QAction, QStatusBar, QMenu, QToolButton,
                             QDialog, QLineEdit, QDialogButtonBox, QFormLayout)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, pyqtSlot, QTimer, QSize, QPoint
from PyQt5.QtGui import QPixmap, QImage, QFont, QIcon, QColor, QPalette, QBrush
import matplotlib
matplotlib.use('Agg')  # 使用非交互式后端

# 设置随机种子以确保可重复性
torch.manual_seed(42)
np.random.seed(42)

class AdvancedFeatureExtractor(nn.Module):
    """高级特征提取器，结合多个预训练模型"""
    def __init__(self, device):
        super(AdvancedFeatureExtractor, self).__init__()
        self.device = device
        
        # 加载多个预训练模型
        self.resnet50 = torch.hub.load('pytorch/vision:v0.10.0', 'resnet50', pretrained=True)
        self.efficientnet = torch.hub.load('NVIDIA/DeepLearningExamples:torchhub', 'nvidia_efficientnet_b0', pretrained=True)
        
        # 移除分类头
        self.resnet50 = nn.Sequential(*list(self.resnet50.children())[:-2])  # 保留更多层
        self.efficientnet = nn.Sequential(*list(self.efficientnet.children())[:-1])
        
        # 自适应平均池化
        self.adaptive_pool = nn.AdaptiveAvgPool2d((1, 1))
        
        # 特征融合层
        self.feature_fusion = nn.Sequential(
            nn.Linear(2048 + 1280, 1024),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(1024, 512),
            nn.ReLU()
        )
        
        # 移动到设备
        self.to(device)
        self.eval()
    
    def forward(self, x):
        # ResNet50特征
        resnet_features = self.resnet50(x)
        resnet_features = self.adaptive_pool(resnet_features)
        resnet_features = torch.flatten(resnet_features, 1)
        
        # EfficientNet特征
        efficientnet_features = self.efficientnet(x)
        efficientnet_features = self.adaptive_pool(efficientnet_features)
        efficientnet_features = torch.flatten(efficientnet_features, 1)
        
        # 特征融合
        combined_features = torch.cat([resnet_features, efficientnet_features], dim=1)
        fused_features = self.feature_fusion(combined_features)
        
        # L2归一化
        fused_features = F.normalize(fused_features, p=2, dim=1)
        
        return fused_features

class DynamicYOLOHead(nn.Module):
    """动态YOLO检测头，支持在线增加类别"""
    def __init__(self, original_head, initial_classes):
        super(DynamicYOLOHead, self).__init__()
        self.initial_classes = initial_classes
        self.current_classes = initial_classes.copy()
        self.num_classes = len(initial_classes)
        
        # 分析原始检测头结构
        self.original_head = original_head
        self.analyze_head_structure()
        
        # 创建动态检测头
        self.create_dynamic_head()
        
        # 初始化权重
        self.initialize_weights()
    
    def analyze_head_structure(self):
        """分析YOLO检测头结构"""
        # 这里需要根据具体的YOLO版本调整
        # 假设YOLOv11的检测头是model.model[-1]
        try:
            # 获取输出通道数
            if hasattr(self.original_head, 'm'):
                # Ultralytics YOLO结构
                last_conv = None
                for module in self.original_head.modules():
                    if isinstance(module, nn.Conv2d):
                        last_conv = module
                
                if last_conv:
                    self.in_channels = last_conv.in_channels
                    self.out_channels = last_conv.out_channels
                    
                    # 计算每个锚点的输出维度
                    self.out_per_anchor = self.out_channels // 3  # 假设3个锚点
                    self.num_anchors = 3
                    
                    # 计算原始类别数
                    self.orig_num_classes = (self.out_per_anchor - 5)  # 5个坐标/置信度参数
            else:
                # 标准YOLO结构
                self.in_channels = 256  # 默认值
                self.out_channels = (5 + len(self.initial_classes)) * 3  # 默认值
                self.num_anchors = 3
                self.out_per_anchor = 5 + len(self.initial_classes)
                self.orig_num_classes = len(self.initial_classes)
                
        except Exception as e:
            print(f"分析检测头结构时出错: {e}")
            # 使用默认值
            self.in_channels = 256
            self.num_anchors = 3
            self.orig_num_classes = len(self.initial_classes)
            self.out_per_anchor = 5 + self.orig_num_classes
            self.out_channels = self.out_per_anchor * self.num_anchors
    
    def create_dynamic_head(self):
        """创建动态检测头"""
        # 创建新的检测头层
        self.dynamic_convs = nn.ModuleList()
        
        # 添加几个卷积层增强特征提取
        self.dynamic_convs.append(nn.Sequential(
            nn.Conv2d(self.in_channels, 512, 3, padding=1),
            nn.BatchNorm2d(512),
            nn.LeakyReLU(0.1),
            nn.Dropout2d(0.1)
        ))
        
        self.dynamic_convs.append(nn.Sequential(
            nn.Conv2d(512, 256, 3, padding=1),
            nn.BatchNorm2d(256),
            nn.LeakyReLU(0.1),
            nn.Dropout2d(0.1)
        ))
        
        # 最终输出层
        self.output_conv = nn.Conv2d(256, self.out_per_anchor * self.num_anchors, 1)
    
    def initialize_weights(self):
        """初始化权重"""
        # 尝试从原始检测头复制权重
        try:
            if hasattr(self.original_head, 'state_dict'):
                original_state = self.original_head.state_dict()
                new_state = self.state_dict()
                
                # 复制匹配的权重
                for name, param in original_state.items():
                    if name in new_state:
                        if param.shape == new_state[name].shape:
                            new_state[name].data.copy_(param.data)
                        else:
                            # 部分复制权重
                            if len(param.shape) == 4:  # 卷积权重
                                min_in = min(param.shape[1], new_state[name].shape[1])
                                min_out = min(param.shape[0], new_state[name].shape[0])
                                new_state[name].data[:min_out, :min_in, :, :] = param.data[:min_out, :min_in, :, :]
                            elif len(param.shape) == 1:  # 偏置
                                min_dim = min(param.shape[0], new_state[name].shape[0])
                                new_state[name].data[:min_dim] = param.data[:min_dim]
                
                self.load_state_dict(new_state)
        except Exception as e:
            print(f"复制权重时出错: {e}")
            # 使用随机初始化
            for m in self.modules():
                if isinstance(m, nn.Conv2d):
                    nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='leaky_relu', a=0.1)
                    if m.bias is not None:
                        nn.init.constant_(m.bias, 0)
                elif isinstance(m, nn.BatchNorm2d):
                    nn.init.constant_(m.weight, 1)
                    nn.init.constant_(m.bias, 0)
    
    def add_new_class(self, class_name):
        """添加新类别"""
        if class_name not in self.current_classes:
            self.current_classes.append(class_name)
            self.num_classes = len(self.current_classes)
            
            # 保存旧权重
            old_output_conv = self.output_conv
            old_out_per_anchor = self.out_per_anchor
            
            # 更新输出维度
            self.out_per_anchor = 5 + self.num_classes
            self.out_channels = self.out_per_anchor * self.num_anchors
            
            # 创建新的输出层
            new_output_conv = nn.Conv2d(256, self.out_channels, 1)
            
            # 复制旧权重到新层
            with torch.no_grad():
                # 复制坐标和置信度权重
                new_output_conv.weight.data[:old_out_per_anchor * self.num_anchors, :, :, :] = \
                    old_output_conv.weight.data
                
                # 复制偏置
                new_output_conv.bias.data[:old_out_per_anchor * self.num_anchors] = \
                    old_output_conv.bias.data
                
                # 初始化新类别的权重
                for i in range(self.num_anchors):
                    start_idx = old_out_per_anchor * i + 5  # 5个坐标/置信度参数
                    new_start_idx = self.out_per_anchor * i + 5
                    
                    # 使用小随机值初始化新类别的权重
                    nn.init.normal_(new_output_conv.weight.data[new_start_idx:new_start_idx + (self.num_classes - old_out_per_anchor + 5), :, :, :], 
                                   mean=0, std=0.01)
                    nn.init.constant_(new_output_conv.bias.data[new_start_idx:new_start_idx + (self.num_classes - old_out_per_anchor + 5)], 0)
            
            self.output_conv = new_output_conv
            self.output_conv.to(old_output_conv.weight.device)
            
            print(f"已添加新类别: {class_name}, 当前类别数: {self.num_classes}")
    
    def forward(self, x):
        """前向传播"""
        for conv in self.dynamic_convs:
            x = conv(x)
        
        return self.output_conv(x)

class AdvancedMemoryBank:
    """高级记忆库，用于存储和管理已知特征"""
    def __init__(self, max_size=10000, feature_dim=512):
        self.max_size = max_size
        self.feature_dim = feature_dim
        self.features = np.zeros((max_size, feature_dim), dtype=np.float32)
        self.labels = np.full(max_size, -1, dtype=np.int32)  # -1表示空槽位
        self.ptr = 0
        self.size = 0
        self.label_to_indices = defaultdict(list)
        
        # 使用 scikit-learn 的最近邻算法替代 FAISS
        from sklearn.neighbors import NearestNeighbors
        self.nn_index = NearestNeighbors(n_neighbors=5, metric='cosine')
        self.index_features = None
        
        # 特征标准化器
        self.scaler = StandardScaler()
        self.is_scaler_fitted = False
    
    def add(self, features, label):
        """添加特征到记忆库"""
        if not isinstance(features, np.ndarray):
            features = np.array(features, dtype=np.float32)
        
        if features.ndim == 1:
            features = features.reshape(1, -1)
        
        # 标准化特征
        if not self.is_scaler_fitted and self.size > 0:
            self.scaler.partial_fit(self.features[:self.size])
            self.is_scaler_fitted = True
        
        if self.is_scaler_fitted:
            features = self.scaler.transform(features)
        
        # 添加到存储数组
        num_to_add = features.shape[0]
        if self.ptr + num_to_add > self.max_size:
            # 循环缓冲区，覆盖最旧的条目
            wrap_around = self.ptr + num_to_add - self.max_size
            self.features[self.ptr:] = features[:num_to_add - wrap_around]
            self.features[:wrap_around] = features[num_to_add - wrap_around:]
            
            # 更新标签
            self.labels[self.ptr:] = label
            self.labels[:wrap_around] = label
            
            # 更新索引映射
            for i in range(self.ptr, self.max_size):
                self.label_to_indices[self.labels[i]].append(i)
            for i in range(wrap_around):
                self.label_to_indices[self.labels[i]].append(i)
            
            self.ptr = wrap_around
        else:
            self.features[self.ptr:self.ptr + num_to_add] = features
            self.labels[self.ptr:self.ptr + num_to_add] = label
            
            # 更新索引映射
            for i in range(self.ptr, self.ptr + num_to_add):
                self.label_to_indices[label].append(i)
            
            self.ptr += num_to_add
        
        self.size = min(self.size + num_to_add, self.max_size)
        
        # 更新最近邻索引
        if self.size > 0:
            self.index_features = self.features[:self.size]
            self.nn_index.fit(self.index_features)
    
    def query(self, query_features, k=5):
        """查询最相似的k个特征"""
        if not isinstance(query_features, np.ndarray):
            query_features = np.array(query_features, dtype=np.float32)
        
        if query_features.ndim == 1:
            query_features = query_features.reshape(1, -1)
        
        # 标准化查询特征
        if self.is_scaler_fitted:
            query_features = self.scaler.transform(query_features)
        
        # 使用最近邻搜索
        if self.size == 0:
            # 返回空结果
            return [{'indices': [], 'distances': [], 'labels': [], 'features': []}]
        
        distances, indices = self.nn_index.kneighbors(query_features, n_neighbors=min(k, self.size))
        
        # 转换为相似度（1 - 余弦距离）
        similarities = 1 - distances
        
        # 获取对应的标签和特征
        results = []
        for i in range(query_features.shape[0]):
            result = {
                'indices': indices[i],
                'distances': similarities[i],  # 注意：这里返回的是相似度，不是距离
                'labels': [self.labels[idx] for idx in indices[i]],
                'features': [self.features[idx] for idx in indices[i]]
            }
            results.append(result)
        
        return results
    
    def get_class_centroids(self):
        """计算每个类别的质心"""
        centroids = {}
        for label, indices in self.label_to_indices.items():
            if label == -1 or not indices:
                continue
            class_features = self.features[indices]
            centroids[label] = np.mean(class_features, axis=0)
        
        return centroids
    
    def get_class_stats(self):
        """获取每个类别的统计信息"""
        stats = {}
        for label, indices in self.label_to_indices.items():
            if label == -1 or not indices:
                continue
            class_features = self.features[indices]
            stats[label] = {
                'count': len(indices),
                'centroid': np.mean(class_features, axis=0),
                'std': np.std(class_features, axis=0),
                'max_similarity': np.max(cosine_similarity(class_features, class_features)),
                'min_similarity': np.min(cosine_similarity(class_features, class_features))
            }
        
        return stats

class AdvancedUnknownDetector:
    def __init__(self, yolo_weights_path, known_classes=None, 
                 confidence_threshold=0.5, unknown_threshold=0.3,
                 feature_dim=512, memory_size=10000, active_learning=True):
        # 设备配置
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        print(f"使用设备: {self.device}")
        
        # 加载YOLOv11模型
        self.base_model = self.load_yolo_model(yolo_weights_path)
        
        # 参数设置
        self.known_classes = known_classes if known_classes else []
        self.class_to_id = {cls: i for i, cls in enumerate(self.known_classes)}
        self.id_to_class = {i: cls for i, cls in enumerate(self.known_classes)}
        self.confidence_threshold = confidence_threshold
        self.unknown_threshold = unknown_threshold
        self.feature_dim = feature_dim
        self.active_learning = active_learning
        
        # 创建带动态检测头的YOLO模型
        self.model = DynamicYOLOHead(self.get_detection_head(), self.known_classes)
        self.model.to(self.device)
        
        # 高级特征提取器
        self.feature_extractor = AdvancedFeatureExtractor(self.device)
        
        # 高级记忆库
        self.memory_bank = AdvancedMemoryBank(max_size=memory_size, feature_dim=feature_dim)
        
        # 初始化记忆库
        self.initialize_memory_bank()
        
        # 聚类和异常检测
        self.clusterer = HDBSCAN(min_cluster_size=3, cluster_selection_epsilon=0.5)
        self.pca = PCA(n_components=50)
        self.pca_fitted = False
        
        # 主动学习队列
        self.active_learning_queue = deque(maxlen=100)
        self.uncertainty_threshold = 0.2
        
        # 图像预处理
        self.transform = T.Compose([
            T.Resize((224, 224)),
            T.ToTensor(),
            T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])
        
        # 创建存储目录
        os.makedirs('unknown_objects', exist_ok=True)
        os.makedirs('known_features', exist_ok=True)
        os.makedirs('saved_models', exist_ok=True)
        os.makedirs('active_learning', exist_ok=True)
        
        # 加载已知特征
        self.load_known_features()
        
        # 训练状态
        self.is_training = False
    
    def load_yolo_model(self, weights_path):
        """加载YOLO模型"""
        try:
            # 尝试使用ultralytics YOLO
            from ultralytics import YOLO
            model = YOLO(weights_path)
            print("成功加载YOLOv11模型")
            return model
        except ImportError:
            # 回退到torch hub
            print("未找到ultralytics库，使用torch hub加载YOLOv5")
            model = torch.hub.load('ultralytics/yolov5', 'custom', path=weights_path)
            return model
    
    def get_detection_head(self):
        """获取YOLO的检测头"""
        try:
            # 尝试获取Ultralytics YOLO的检测头
            if hasattr(self.base_model, 'model'):
                return self.base_model.model[-1]
            else:
                # 对于YOLOv5，检测头是model.model[-1]
                return self.base_model.model[-1]
        except:
            print("无法获取检测头，使用默认结构")
            return None
    
    def initialize_memory_bank(self):
        """初始化记忆库"""
        # 如果有预训练的已知特征，加载到记忆库
        if hasattr(self, 'known_features') and self.known_features:
            for class_name, features_list in self.known_features.items():
                if class_name in self.class_to_id:
                    class_id = self.class_to_id[class_name]
                    for features in features_list:
                        self.memory_bank.add(features, class_id)
        
        print(f"记忆库初始化完成，当前大小: {self.memory_bank.size}")
    
    def extract_features(self, img_crop):
        """提取图像区域的特征"""
        img = Image.fromarray(img_crop)
        img_tensor = self.transform(img).unsqueeze(0).to(self.device)
        
        with torch.no_grad():
            features = self.feature_extractor(img_tensor)
            
        return features.cpu().numpy()
    
    def is_known_object(self, features):
        """判断是否为已知物体"""
        if self.memory_bank.size == 0:
            return False, 0.0, None, None
        
        # 查询记忆库
        results = self.memory_bank.query(features, k=5)
        result = results[0]  # 单个查询
        
        # 计算与最近邻的相似度
        max_similarity = np.max(result['distances'])
        best_match_idx = np.argmax(result['distances'])
        best_class_id = result['labels'][best_match_idx]
        
        # 计算不确定性（基于最近邻的距离分布）
        distances = 1 - result['distances']  # 转换为距离（1 - 相似度）
        uncertainty = np.std(distances) / (np.mean(distances) + 1e-8)
        
        # 如果最大相似度高于阈值，则认为是已知物体
        if max_similarity > self.unknown_threshold:
            best_class = self.id_to_class.get(best_class_id, f"未知ID_{best_class_id}")
            return True, max_similarity, best_class, uncertainty
        else:
            return False, max_similarity, None, uncertainty
    
    def cluster_unknown_features(self, features_array):
        """对未知特征进行聚类"""
        if len(features_array) < 3:  # 至少需要3个样本才能聚类
            return {}
        
        # 使用PCA降维
        if not self.pca_fitted:
            self.pca.fit(features_array)
            self.pca_fitted = True
        
        features_pca = self.pca.transform(features_array)
        
        # 使用HDBSCAN进行聚类
        clustering = self.clusterer.fit(features_pca)
        labels = clustering.labels_
        
        # 组织聚类结果
        clusters = {}
        for i, label in enumerate(labels):
            if label == -1:  # 噪声点
                continue
                
            if label not in clusters:
                clusters[label] = []
            clusters[label].append(i)
        
        return clusters
    
    def visualize_clusters(self, features_array, clusters):
        """可视化特征聚类"""
        if len(features_array) < 3:
            return None
            
        # 使用UMAP进行降维可视化（比t-SNE更快)
        reducer = umap.UMAP(n_components=2, random_state=42)
        features_2d = reducer.fit_transform(features_array)
        
        # 创建颜色映射
        colors = plt.cm.tab10(np.linspace(0, 1, len(clusters) if clusters else 1))
        
        plt.figure(figsize=(10, 8))
        
        if clusters:
            # 绘制聚类点
            for cluster_id, indices in clusters.items():
                plt.scatter(features_2d[indices, 0], features_2d[indices, 1], 
                           c=[colors[cluster_id % len(colors)]], label=f'Cluster {cluster_id}', alpha=0.7)
            
            # 绘制噪声点
            all_indices = set(range(len(features_2d)))
            clustered_indices = set()
            for indices in clusters.values():
                clustered_indices.update(indices)
            noise_indices = list(all_indices - clustered_indices)
            
            if noise_indices:
                plt.scatter(features_2d[noise_indices, 0], features_2d[noise_indices, 1], 
                           c='gray', label='Noise', alpha=0.5)
                
            plt.legend()
        else:
            # 没有聚类，绘制所有点
            plt.scatter(features_2d[:, 0], features_2d[:, 1], alpha=0.7)
            
        plt.title('UMAP Visualization of Unknown Features')
        plt.xlabel('UMAP 1')
        plt.ylabel('UMAP 2')
        
        # 保存图像到内存
        plt.savefig('cluster_visualization.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        return 'cluster_visualization.png'
    
    def detect_objects(self, image_path, detect_only=False):
        """检测图像中的物体"""
        # 使用YOLO进行目标检测
        if hasattr(self.base_model, 'predict'):  # ultralytics YOLO
            results = self.base_model.predict(image_path, conf=self.confidence_threshold)
            detections = results[0].boxes.data.cpu().numpy()
            class_names = self.base_model.names
        else:  # YOLOv5
            results = self.base_model(image_path)
            detections = results.pandas().xyxy[0]
        
        # 读取原始图像
        img = cv2.imread(image_path)
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        result_img = img_rgb.copy()
        
        detected_objects = []
        unknown_objects = []
        unknown_features = []
        
        # 处理每个检测结果
        for i, det in enumerate(detections):
            if hasattr(self.base_model, 'predict'):  # ultralytics YOLO
                x1, y1, x2, y2 = map(int, det[:4])
                confidence = det[4]
                class_id = int(det[5])
                class_name = class_names[class_id]
            else:  # YOLOv5
                x1, y1, x2, y2 = int(det['xmin']), int(det['ymin']), int(det['xmax']), int(det['ymax'])
                confidence = det['confidence']
                class_name = det['name']
            
            if confidence < self.confidence_threshold:
                continue
                
            # 裁剪检测区域
            crop_img = img_rgb[y1:y2, x1:x2]
            if crop_img.size == 0:
                continue
                
            # 提取特征
            features = self.extract_features(crop_img)
            
            # 判断是否为已知物体
            is_known, similarity, known_class, uncertainty = self.is_known_object(features)
            
            if is_known:
                # 标记为已知物体
                cv2.rectangle(result_img, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(result_img, f"{known_class}: {confidence:.2f}", (x1, y1-10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                
                detected_objects.append({
                    'bbox': (x1, y1, x2, y2),
                    'class': known_class,
                    'confidence': confidence,
                    'features': features,
                    'similarity': similarity,
                    'uncertainty': uncertainty,
                    'image': crop_img,
                    'is_known': True
                })
            else:
                # 标记为未知物体
                cv2.rectangle(result_img, (x1, y1), (x2, y2), (255, 0, 0), 3)
                cv2.putText(result_img, f"Unknown: {similarity:.2f}", (x1, y1-10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
                
                # 添加到未知物体列表
                obj_data = {
                    'bbox': (x1, y1, x2, y2),
                    'class': 'unknown',
                    'confidence': confidence,
                    'features': features,
                    'similarity': similarity,
                    'uncertainty': uncertainty,
                    'image': crop_img,
                    'is_known': False,
                    'index': len(unknown_features)
                }
                
                detected_objects.append(obj_data)
                unknown_objects.append(obj_data)
                unknown_features.append(features)
                
                # 如果启用主动学习且不确定性高，添加到主动学习队列
                if self.active_learning and uncertainty > self.uncertainty_threshold:
                    self.active_learning_queue.append({
                        'image': crop_img,
                        'features': features,
                        'uncertainty': uncertainty,
                        'timestamp': datetime.now()
                    })
                    
                    # 保存高不确定性样本
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    uncertain_path = f"active_learning/uncertain_{timestamp}_{i}.jpg"
                    cv2.imwrite(uncertain_path, cv2.cvtColor(crop_img, cv2.COLOR_RGB2BGR))
        
        # 保存结果图像
        result_path = 'detection_result.jpg'
        cv2.imwrite(result_path, cv2.cvtColor(result_img, cv2.COLOR_RGB2BGR))
        
        # 如果不是仅检测模式，处理未知物体
        if not detect_only and unknown_objects:
            # 对未知特征进行聚类
            unknown_features_array = np.vstack(unknown_features)
            clusters = self.cluster_unknown_features(unknown_features_array)
            
            # 可视化聚类结果
            cluster_image_path = self.visualize_clusters(unknown_features_array, clusters)
        else:
            clusters = {}
            cluster_image_path = None
        
        return detected_objects, unknown_objects, clusters, result_path, cluster_image_path
    
    def add_new_class(self, class_name, features_list, update_model=True):
        """添加新类别"""
        if class_name not in self.known_classes:
            # 添加新类别
            self.known_classes.append(class_name)
            class_id = len(self.known_classes) - 1
            self.class_to_id[class_name] = class_id
            self.id_to_class[class_id] = class_name
            
            # 添加到记忆库
            for features in features_list:
                self.memory_bank.add(features, class_id)
            
            # 更新模型检测头
            if update_model:
                self.model.add_new_class(class_name)
            
            # 保存更新后的已知特征
            self.save_known_features()
            
            print(f"已添加新类别: {class_name}, 当前类别数: {len(self.known_classes)}")
        else:
            # 添加到现有类别
            class_id = self.class_to_id[class_name]
            for features in features_list:
                self.memory_bank.add(features, class_id)
            
            print(f"已添加到现有类别: {class_name}")
    
    def fine_tune_model(self, learning_rate=0.001, epochs=10, batch_size=32):
        """微调模型"""
        if self.memory_bank.size < batch_size:
            print("记忆库中的样本不足，无法微调")
            return
        
        self.is_training = True
        
        # 准备训练数据
        features = self.memory_bank.features[:self.memory_bank.size]
        labels = self.memory_bank.labels[:self.memory_bank.size]
        
        # 转换为PyTorch张量
        features_tensor = torch.tensor(features, dtype=torch.float32).to(self.device)
        labels_tensor = torch.tensor(labels, dtype=torch.long).to(self.device)
        
        # 创建数据加载器
        dataset = torch.utils.data.TensorDataset(features_tensor, labels_tensor)
        dataloader = torch.utils.data.DataLoader(dataset, batch_size=batch_size, shuffle=True)
        
        # 创建分类头
        classifier = nn.Linear(self.feature_dim, len(self.known_classes)).to(self.device)
        
        # 优化器和损失函数
        optimizer = torch.optim.Adam(classifier.parameters(), lr=learning_rate)
        criterion = nn.CrossEntropyLoss()
        
        # 训练循环
        for epoch in range(epochs):
            total_loss = 0
            for batch_features, batch_labels in dataloader:
                optimizer.zero_grad()
                
                # 前向传播
                outputs = classifier(batch_features)
                loss = criterion(outputs, batch_labels)
                
                # 反向传播
                loss.backward()
                optimizer.step()
                
                total_loss += loss.item()
            
            print(f"Epoch {epoch+1}/{epochs}, Loss: {total_loss/len(dataloader):.4f}")
        
        self.is_training = False
        print("模型微调完成")
    
    def active_learning_query(self, top_k=10):
        """主动学习查询，返回最不确定的样本"""
        if not self.active_learning_queue:
            return []
        
        # 按不确定性排序
        sorted_queue = sorted(self.active_learning_queue, key=lambda x: x['uncertainty'], reverse=True)
        
        return sorted_queue[:top_k]
    
    def save_model(self, file_path):
        """保存模型权重"""
        torch.save({
            'model_state_dict': self.model.state_dict(),
            'known_classes': self.known_classes,
            'class_to_id': self.class_to_id,
            'id_to_class': self.id_to_class,
            'memory_bank': {
                'features': self.memory_bank.features,
                'labels': self.memory_bank.labels,
                'ptr': self.memory_bank.ptr,
                'size': self.memory_bank.size,
                'label_to_indices': dict(self.memory_bank.label_to_indices)
            },
            'pca': self.pca if self.pca_fitted else None
        }, file_path)
        
        print(f"模型已保存到: {file_path}")
    
    def load_model(self, file_path):
        """加载模型权重"""
        checkpoint = torch.load(file_path, map_location=self.device)
        self.model.load_state_dict(checkpoint['model_state_dict'])
        self.known_classes = checkpoint['known_classes']
        self.class_to_id = checkpoint['class_to_id']
        self.id_to_class = checkpoint['id_to_class']
        
        # 恢复记忆库
        memory_data = checkpoint['memory_bank']
        self.memory_bank.features = memory_data['features']
        self.memory_bank.labels = memory_data['labels']
        self.memory_bank.ptr = memory_data['ptr']
        self.memory_bank.size = memory_data['size']
        self.memory_bank.label_to_indices = defaultdict(list, memory_data['label_to_indices'])
        
        # 恢复PCA
        if checkpoint['pca'] is not None:
            self.pca = checkpoint['pca']
            self.pca_fitted = True
        
        print(f"模型已从 {file_path} 加载")
    
    def save_known_features(self):
        """保存已知特征到文件"""
        # 转换为可序列化的格式
        features_dict = {}
        for class_name in self.known_classes:
            class_id = self.class_to_id[class_name]
            indices = self.memory_bank.label_to_indices[class_id]
            if indices:
                features_dict[class_name] = [self.memory_bank.features[idx].tolist() for idx in indices]
        
        # 保存到JSON文件
        with open('known_features/known_features.json', 'w') as f:
            json.dump(features_dict, f)
        
        # 保存类别列表
        with open('known_features/known_classes.json', 'w') as f:
            json.dump(self.known_classes, f)
        
        print("已知特征已保存")
    
    def load_known_features(self):
        """从文件加载已知特征"""
        try:
            # 加载特征
            with open('known_features/known_features.json', 'r') as f:
                features_dict = json.load(f)
            
            # 加载类别列表
            with open('known_features/known_classes.json', 'r') as f:
                self.known_classes = json.load(f)
            
            # 重建类别映射
            self.class_to_id = {cls: i for i, cls in enumerate(self.known_classes)}
            self.id_to_class = {i: cls for i, cls in enumerate(self.known_classes)}
            
            # 添加到记忆库
            for class_name, features_list in features_dict.items():
                class_id = self.class_to_id[class_name]
                for features in features_list:
                    self.memory_bank.add(np.array(features), class_id)
            
            print("已知特征已加载")
        except FileNotFoundError:
            print("未找到已知特征文件，将从头开始学习")

# PyQt界面
class DetectionThread(QThread):
    """检测线程"""
    finished = pyqtSignal(list, list, dict, str, str)
    progress = pyqtSignal(int)
    
    def __init__(self, detector, image_path, detect_only=False):
        super().__init__()
        self.detector = detector
        self.image_path = image_path
        self.detect_only = detect_only
    
    def run(self):
        detected_objects, unknown_objects, clusters, result_path, cluster_image_path = \
            self.detector.detect_objects(self.image_path, self.detect_only)
        self.finished.emit(detected_objects, unknown_objects, clusters, result_path, cluster_image_path)

class TrainingThread(QThread):
    """训练线程"""
    finished = pyqtSignal()
    progress = pyqtSignal(int)
    
    def __init__(self, detector, learning_rate=0.001, epochs=10, batch_size=32):
        super().__init__()
        self.detector = detector
        self.learning_rate = learning_rate
        self.epochs = epochs
        self.batch_size = batch_size
    
    def run(self):
        self.detector.fine_tune_model(self.learning_rate, self.epochs, self.batch_size)
        self.finished.emit()

class AddClassDialog(QDialog):
    """添加类别对话框"""
    def __init__(self, parent=None, class_name="", cluster_size=0):
        super().__init__(parent)
        self.setWindowTitle("添加新类别")
        self.setModal(True)
        
        layout = QFormLayout(self)
        
        self.class_name_edit = QLineEdit(class_name)
        layout.addRow("类别名称:", self.class_name_edit)
        
        self.cluster_size_label = QLabel(f"{cluster_size} 个物体")
        layout.addRow("聚类大小:", self.cluster_size_label)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)
    
    def get_class_name(self):
        return self.class_name_edit.text().strip()

class AdvancedYOLODetectorApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.detector = None
        self.current_image_path = None
        self.detected_objects = []
        self.unknown_objects = []
        self.current_clusters = {}
        
        self.initUI()
        
    def initUI(self):
        self.setWindowTitle('高级YOLO未知物体检测与学习系统')
        self.setGeometry(100, 100, 1400, 900)
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QHBoxLayout(central_widget)
        
        # 左侧面板
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_panel.setMaximumWidth(350)
        
        # 模型设置组
        model_group = QGroupBox("模型设置")
        model_layout = QVBoxLayout(model_group)
        
        self.load_model_btn = QPushButton("加载模型权重")
        self.load_model_btn.clicked.connect(self.load_model)
        model_layout.addWidget(self.load_model_btn)
        
        self.model_status = QLabel("未加载模型")
        model_layout.addWidget(self.model_status)
        
        # 参数设置
        params_layout = QHBoxLayout()
        params_layout.addWidget(QLabel("置信度:"))
        self.confidence_spin = QDoubleSpinBox()
        self.confidence_spin.setRange(0.0, 1.0)
        self.confidence_spin.setValue(0.5)
        self.confidence_spin.setSingleStep(0.05)
        self.confidence_spin.valueChanged.connect(self.update_confidence)
        params_layout.addWidget(self.confidence_spin)
        
        params_layout.addWidget(QLabel("未知阈值:"))
        self.unknown_spin = QDoubleSpinBox()
        self.unknown_spin.setRange(0.0, 1.0)
        self.unknown_spin.setValue(0.3)
        self.unknown_spin.setSingleStep(0.05)
        self.unknown_spin.valueChanged.connect(self.update_unknown_threshold)
        params_layout.addWidget(self.unknown_spin)
        
        model_layout.addLayout(params_layout)
        
        left_layout.addWidget(model_group)
        
        # 图像操作组
        image_group = QGroupBox("图像操作")
        image_layout = QVBoxLayout(image_group)
        
        self.load_image_btn = QPushButton("加载图像")
        self.load_image_btn.clicked.connect(self.load_image)
        self.load_image_btn.setEnabled(False)
        image_layout.addWidget(self.load_image_btn)
        
        self.detect_btn = QPushButton("检测物体")
        self.detect_btn.clicked.connect(self.detect_objects)
        self.detect_btn.setEnabled(False)
        image_layout.addWidget(self.detect_btn)
        
        self.detect_only_check = QCheckBox("仅检测模式")
        self.detect_only_check.setChecked(False)
        image_layout.addWidget(self.detect_only_check)
        
        left_layout.addWidget(image_group)
        
        # 学习设置组
        learn_group = QGroupBox("学习设置")
        learn_layout = QVBoxLayout(learn_group)
        
        self.active_learning_check = QCheckBox("启用主动学习")
        self.active_learning_check.setChecked(True)
        self.active_learning_check.stateChanged.connect(self.toggle_active_learning)
        learn_layout.addWidget(self.active_learning_check)
        
        self.uncertainty_label = QLabel("不确定性阈值: 0.2")
        learn_layout.addWidget(self.uncertainty_label)
        
        self.uncertainty_slider = QSlider(Qt.Horizontal)
        self.uncertainty_slider.setMinimum(0)
        self.uncertainty_slider.setMaximum(100)
        self.uncertainty_slider.setValue(20)
        self.uncertainty_slider.valueChanged.connect(self.update_uncertainty_threshold)
        learn_layout.addWidget(self.uncertainty_slider)
        
        self.cluster_btn = QPushButton("聚类未知物体")
        self.cluster_btn.clicked.connect(self.cluster_unknowns)
        self.cluster_btn.setEnabled(False)
        learn_layout.addWidget(self.cluster_btn)
        
        self.train_btn = QPushButton("微调模型")
        self.train_btn.clicked.connect(self.fine_tune_model)
        self.train_btn.setEnabled(False)
        learn_layout.addWidget(self.train_btn)
        
        self.save_model_btn = QPushButton("保存模型")
        self.save_model_btn.clicked.connect(self.save_model)
        self.save_model_btn.setEnabled(False)
        learn_layout.addWidget(self.save_model_btn)
        
        left_layout.addWidget(learn_group)
        
        # 已知类别列表
        known_classes_group = QGroupBox("已知类别")
        known_classes_layout = QVBoxLayout(known_classes_group)
        
        self.known_classes_list = QListWidget()
        known_classes_layout.addWidget(self.known_classes_list)
        
        left_layout.addWidget(known_classes_group)
        
        # 右侧面板
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # 创建标签页
        self.tab_widget = QTabWidget()
        
        # 检测结果标签页
        self.detection_tab = QWidget()
        detection_layout = QVBoxLayout(self.detection_tab)
        
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setMinimumSize(640, 480)
        self.image_label.setText("请加载图像")
        self.image_label.setStyleSheet("border: 1px solid gray;")
        detection_layout.addWidget(self.image_label)
        
        # 结果显示
        self.result_text = QTextEdit()
        self.result_text.setMaximumHeight(150)
        detection_layout.addWidget(self.result_text)
        
        self.tab_widget.addTab(self.detection_tab, "检测结果")
        
        # 聚类分析标签页
        self.cluster_tab = QWidget()
        cluster_layout = QVBoxLayout(self.cluster_tab)
        
        self.cluster_label = QLabel()
        self.cluster_label.setAlignment(Qt.AlignCenter)
        self.cluster_label.setMinimumSize(640, 480)
        self.cluster_label.setText("聚类分析结果将显示在这里")
        self.cluster_label.setStyleSheet("border: 1px solid gray;")
        cluster_layout.addWidget(self.cluster_label)
        
        self.cluster_table = QTableWidget()
        self.cluster_table.setColumnCount(3)
        self.cluster_table.setHorizontalHeaderLabels(["聚类ID", "物体数量", "操作"])
        cluster_layout.addWidget(self.cluster_table)
        
        self.tab_widget.addTab(self.cluster_tab, "聚类分析")
        
        # 主动学习标签页
        self.active_learning_tab = QWidget()
        active_learning_layout = QVBoxLayout(self.active_learning_tab)
        
        self.active_learning_table = QTableWidget()
        self.active_learning_table.setColumnCount(4)
        self.active_learning_table.setHorizontalHeaderLabels(["图像", "不确定性", "时间", "操作"])
        active_learning_layout.addWidget(self.active_learning_table)
        
        self.tab_widget.addTab(self.active_learning_tab, "主动学习")
        
        right_layout.addWidget(self.tab_widget)
        
        # 添加到主布局
        main_layout.addWidget(left_panel)
        main_layout.addWidget(right_panel)
        
        # 状态栏
        self.statusBar().showMessage('就绪')
        
        # 创建工具栏
        self.create_toolbar()
    
    def create_toolbar(self):
        """创建工具栏"""
        toolbar = QToolBar("主工具栏")
        toolbar.setIconSize(QSize(16, 16))
        self.addToolBar(toolbar)
        
        # 添加工具栏动作
        load_model_action = QAction(QIcon("icons/load.png"), "加载模型", self)
        load_model_action.triggered.connect(self.load_model)
        toolbar.addAction(load_model_action)
        
        load_image_action = QAction(QIcon("icons/image.png"), "加载图像", self)
        load_image_action.triggered.connect(self.load_image)
        toolbar.addAction(load_image_action)
        
        detect_action = QAction(QIcon("icons/detect.png"), "检测物体", self)
        detect_action.triggered.connect(self.detect_objects)
        toolbar.addAction(detect_action)
        
        toolbar.addSeparator()
        
        save_model_action = QAction(QIcon("icons/save.png"), "保存模型", self)
        save_model_action.triggered.connect(self.save_model)
        toolbar.addAction(save_model_action)
        
        train_action = QAction(QIcon("icons/train.png"), "微调模型", self)
        train_action.triggered.connect(self.fine_tune_model)
        toolbar.addAction(train_action)
    
    def load_model(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择YOLO权重文件", "", "PyTorch Model Files (*.pt)")
        
        if file_path:
            try:
                # 获取已知类别列表（这里需要根据实际模型调整）
                known_classes = ['person', 'car', 'bicycle', 'motorcycle', 'bus', 'truck']
                
                self.detector = AdvancedUnknownDetector(
                    yolo_weights_path=file_path,
                    known_classes=known_classes,
                    confidence_threshold=0.5,
                    unknown_threshold=0.3
                )
                
                self.model_status.setText(f"已加载模型: {os.path.basename(file_path)}")
                self.load_image_btn.setEnabled(True)
                self.save_model_btn.setEnabled(True)
                self.train_btn.setEnabled(True)
                
                # 更新已知类别列表
                self.update_known_classes_list()
                
                self.statusBar().showMessage('模型加载成功')
            except Exception as e:
                QMessageBox.critical(self, "错误", f"加载模型失败: {str(e)}")
    
    def load_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择图像文件", "", "Image Files (*.png *.jpg *.jpeg *.bmp)")
        
        if file_path:
            self.current_image_path = file_path
            pixmap = QPixmap(file_path)
            scaled_pixmap = pixmap.scaled(self.image_label.width(), self.image_label.height(), 
                                         Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.image_label.setPixmap(scaled_pixmap)
            self.detect_btn.setEnabled(True)
            self.statusBar().showMessage(f'已加载图像: {os.path.basename(file_path)}')
    
    def detect_objects(self):
        if not self.detector or not self.current_image_path:
            return
        
        self.detect_btn.setEnabled(False)
        self.statusBar().showMessage('正在检测物体...')
        
        # 创建检测线程
        detect_only = self.detect_only_check.isChecked()
        self.detection_thread = DetectionThread(self.detector, self.current_image_path, detect_only)
        self.detection_thread.finished.connect(self.on_detection_finished)
        self.detection_thread.start()
    
    @pyqtSlot(list, list, dict, str, str)
    def on_detection_finished(self, detected_objects, unknown_objects, clusters, result_path, cluster_image_path):
        self.detected_objects = detected_objects
        self.unknown_objects = unknown_objects
        self.current_clusters = clusters
        
        # 显示结果图像
        pixmap = QPixmap(result_path)
        scaled_pixmap = pixmap.scaled(self.image_label.width(), self.image_label.height(), 
                                     Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.image_label.setPixmap(scaled_pixmap)
        
        # 显示检测结果
        known_count = sum(1 for obj in detected_objects if obj['is_known'])
        unknown_count = len(unknown_objects)
        
        self.result_text.clear()
        self.result_text.append(f"检测完成! 发现 {known_count} 个已知物体, {unknown_count} 个未知物体")
        
        if unknown_objects:
            self.cluster_btn.setEnabled(True)
            self.result_text.append(f"\n发现 {unknown_count} 个未知物体，请点击'聚类未知物体'进行分析")
            
            # 显示不确定性信息
            uncertainties = [obj['uncertainty'] for obj in unknown_objects]
            avg_uncertainty = np.mean(uncertainties) if uncertainties else 0
            self.result_text.append(f"平均不确定性: {avg_uncertainty:.3f}")
            
            # 如果有高不确定性样本，提示用户
            if self.detector.active_learning and avg_uncertainty > self.detector.uncertainty_threshold:
                self.result_text.append("\n检测到高不确定性样本，已添加到主动学习队列")
        
        self.detect_btn.setEnabled(True)
        self.statusBar().showMessage('检测完成')
        
        # 如果有聚类结果，显示聚类标签页
        if cluster_image_path:
            cluster_pixmap = QPixmap(cluster_image_path)
            scaled_cluster_pixmap = cluster_pixmap.scaled(self.cluster_label.width(), self.cluster_label.height(), 
                                                         Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.cluster_label.setPixmap(scaled_cluster_pixmap)
            
            # 更新聚类表格
            self.update_cluster_table()
            
            # 切换到聚类分析标签页
            self.tab_widget.setCurrentIndex(1)
    
    def cluster_unknowns(self):
        if not self.detector or not self.unknown_objects:
            return
        
        self.statusBar().showMessage('正在聚类未知物体...')
        
        # 提取特征
        unknown_features = [obj['features'] for obj in self.unknown_objects]
        unknown_features_array = np.vstack(unknown_features)
        
        # 对未知特征进行聚类
        clusters = self.detector.cluster_unknown_features(unknown_features_array)
        self.current_clusters = clusters
        
        # 可视化聚类结果
        cluster_image_path = self.detector.visualize_clusters(unknown_features_array, clusters)
        
        if cluster_image_path:
            # 显示聚类结果
            cluster_pixmap = QPixmap(cluster_image_path)
            scaled_cluster_pixmap = cluster_pixmap.scaled(self.cluster_label.width(), self.cluster_label.height(), 
                                                         Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.cluster_label.setPixmap(scaled_cluster_pixmap)
            
            # 更新聚类表格
            self.update_cluster_table()
            
            # 切换到聚类分析标签页
            self.tab_widget.setCurrentIndex(1)
            
            self.statusBar().showMessage('聚类完成')
        else:
            self.result_text.append("\n未知物体数量不足，无法聚类")
            self.statusBar().showMessage('聚类失败: 未知物体数量不足')
    
    def update_cluster_table(self):
        """更新聚类表格"""
        self.cluster_table.setRowCount(len(self.current_clusters))
        
        for row, (cluster_id, indices) in enumerate(self.current_clusters.items()):
            # 聚类ID
            self.cluster_table.setItem(row, 0, QTableWidgetItem(str(cluster_id)))
            
            # 物体数量
            self.cluster_table.setItem(row, 1, QTableWidgetItem(str(len(indices))))
            
            # 操作按钮
            add_button = QPushButton("添加类别")
            add_button.clicked.connect(lambda checked, cid=cluster_id: self.add_cluster_class(cid))
            self.cluster_table.setCellWidget(row, 2, add_button)
        
        self.cluster_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
    
    def add_cluster_class(self, cluster_id):
        """添加聚类类别"""
        if cluster_id not in self.current_clusters:
            return
        
        indices = self.current_clusters[cluster_id]
        cluster_size = len(indices)
        
        # 创建对话框
        dialog = AddClassDialog(self, f"cluster_{cluster_id}", cluster_size)
        if dialog.exec_() == QDialog.Accepted:
            class_name = dialog.get_class_name()
            if class_name:
                # 获取聚类中的特征
                features_list = [self.unknown_objects[idx]['features'] for idx in indices]
                
                # 添加新类别
                self.detector.add_new_class(class_name, features_list)
                
                # 更新界面
                self.update_known_classes_list()
                
                # 从未知物体列表中移除已添加的物体
                for idx in sorted(indices, reverse=True):
                    if idx < len(self.unknown_objects):
                        self.unknown_objects.pop(idx)
                
                # 更新聚类表格
                self.update_cluster_table()
                
                self.result_text.append(f"\n已添加新类别: {class_name}")
                self.statusBar().showMessage(f'已添加新类别: {class_name}')
    
    def fine_tune_model(self):
        """微调模型"""
        if not self.detector:
            return
        
        self.statusBar().showMessage('正在微调模型...')
        
        # 创建训练线程
        self.training_thread = TrainingThread(self.detector)
        self.training_thread.finished.connect(self.on_training_finished)
        self.training_thread.start()
    
    @pyqtSlot()
    def on_training_finished(self):
        self.statusBar().showMessage('模型微调完成')
        QMessageBox.information(self, "完成", "模型微调完成!")
    
    def save_model(self):
        if not self.detector:
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存模型", "saved_models/model.pt", "PyTorch Model Files (*.pt)")
        
        if file_path:
            self.detector.save_model(file_path)
            self.statusBar().showMessage(f'模型已保存: {os.path.basename(file_path)}')
    
    def update_confidence(self, value):
        if self.detector:
            self.detector.confidence_threshold = value
    
    def update_unknown_threshold(self, value):
        if self.detector:
            self.detector.unknown_threshold = value
    
    def update_uncertainty_threshold(self, value):
        threshold = value / 100.0
        self.uncertainty_label.setText(f"不确定性阈值: {threshold:.2f}")
        
        if self.detector:
            self.detector.uncertainty_threshold = threshold
    
    def toggle_active_learning(self, state):
        if self.detector:
            self.detector.active_learning = state == Qt.Checked
    
    def update_known_classes_list(self):
        if self.detector:
            self.known_classes_list.clear()
            for class_name in self.detector.known_classes:
                # 获取类别统计信息
                class_id = self.detector.class_to_id[class_name]
                indices = self.detector.memory_bank.label_to_indices[class_id]
                count = len(indices) if indices else 0
                
                self.known_classes_list.addItem(f"{class_name} ({count} 样本)")

def main():
    app = QApplication(sys.argv)
    window = AdvancedYOLODetectorApp()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()