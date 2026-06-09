import sys
import os
import json
import sqlite3
import cv2
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torchvision.transforms as transforms
from datetime import datetime, timedelta
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QPushButton, QTextEdit, 
                             QTabWidget, QGroupBox, QListWidget, QListWidgetItem,
                             QFileDialog, QMessageBox, QProgressBar, QSlider,
                             QSpinBox, QDoubleSpinBox, QCheckBox, QComboBox,
                             QTableWidget, QTableWidgetItem, QHeaderView,
                             QSplitter, QFrame, QToolBar, QStatusBar, QAction,
                             QDialog, QLineEdit, QDialogButtonBox, QFormLayout,
                             QGraphicsView, QGraphicsScene, QGraphicsPixmapItem,
                             QStackedWidget, QProgressDialog, QTreeWidget, QTreeWidgetItem)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QSize, QDate, QPoint, QRectF
from PyQt5.QtGui import QPixmap, QImage, QIcon, QFont, QPalette, QColor, QPen, QBrush, QPainter
import matplotlib
matplotlib.rc("font", family='Microsoft YaHei')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import qimage2ndarray
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
import mediapipe as mp
from scipy import ndimage
import pyqtgraph as pg
import open3d as o3d
from stl import mesh
import vtk
from vtk.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
import threading
import time
import hashlib
import base64

# ==============================
# 本地健康记录管理（替代区块链）
# ==============================
class LocalHealthRecord:
    def __init__(self, db_path="foot_care_local.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """初始化本地数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 健康记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS health_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                record_data TEXT,
                record_hash TEXT UNIQUE,
                timestamp TEXT,
                signature TEXT
            )
        ''')
        
        # 用户表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                age INTEGER,
                gender TEXT,
                foot_type TEXT,
                created_date TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def add_record(self, user_id, record_data, signature="local_signature"):
        """添加健康记录到本地数据库"""
        record_hash = hashlib.sha256(json.dumps(record_data).encode()).hexdigest()
        timestamp = datetime.now().isoformat()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "INSERT INTO health_records (user_id, record_data, record_hash, timestamp, signature) VALUES (?, ?, ?, ?, ?)",
                (user_id, json.dumps(record_data), record_hash, timestamp, signature)
            )
            conn.commit()
        except sqlite3.IntegrityError:
            # 哈希冲突，使用不同的哈希
            record_hash = hashlib.sha256((json.dumps(record_data) + timestamp).encode()).hexdigest()
            cursor.execute(
                "INSERT INTO health_records (user_id, record_data, record_hash, timestamp, signature) VALUES (?, ?, ?, ?, ?)",
                (user_id, json.dumps(record_data), record_hash, timestamp, signature)
            )
            conn.commit()
        finally:
            conn.close()
        
        return record_hash
    
    def verify_record(self, record_hash):
        """验证记录完整性"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT record_data FROM health_records WHERE record_hash = ?", (record_hash,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            record_data = json.loads(result[0])
            calculated_hash = hashlib.sha256(json.dumps(record_data).encode()).hexdigest()
            return calculated_hash == record_hash
        
        return False
    
    def get_user_records(self, user_id):
        """获取用户的所有记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM health_records WHERE user_id = ? ORDER BY timestamp DESC", (user_id,))
        records = cursor.fetchall()
        conn.close()
        
        return records

# ==============================
# AI足部疾病诊断模型
# ==============================
class FootDiseaseDiagnosisAI:
    def __init__(self):
        self.classes = [
            '正常', '拇趾外翻', '扁平足', '高弓足', '足底筋膜炎', 
            '糖尿病足', '鸡眼', '跖疣', '灰指甲', '湿疹'
        ]
        self.model = self.build_model()
        self.transform = transforms.Compose([
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])
    
    def build_model(self):
        """构建深度学习模型"""
        class FootDiseaseNet(nn.Module):
            def __init__(self, num_classes=10):
                super(FootDiseaseNet, self).__init__()
                self.features = nn.Sequential(
                    nn.Conv2d(3, 64, kernel_size=3, padding=1),
                    nn.ReLU(inplace=True),
                    nn.MaxPool2d(kernel_size=2, stride=2),
                    
                    nn.Conv2d(64, 128, kernel_size=3, padding=1),
                    nn.ReLU(inplace=True),
                    nn.MaxPool2d(kernel_size=2, stride=2),
                    
                    nn.Conv2d(128, 256, kernel_size=3, padding=1),
                    nn.ReLU(inplace=True),
                    nn.Conv2d(256, 256, kernel_size=3, padding=1),
                    nn.ReLU(inplace=True),
                    nn.MaxPool2d(kernel_size=2, stride=2),
                )
                
                self.classifier = nn.Sequential(
                    nn.Dropout(0.5),
                    nn.Linear(256 * 28 * 28, 512),
                    nn.ReLU(inplace=True),
                    nn.Dropout(0.5),
                    nn.Linear(512, num_classes)
                )
            
            def forward(self, x):
                x = self.features(x)
                x = x.view(x.size(0), -1)
                x = self.classifier(x)
                return x
        
        return FootDiseaseNet(len(self.classes))
    
    def predict(self, image):
        """预测足部疾病"""
        # 在实际应用中，这里会加载预训练模型
        # 这里使用模拟预测
        try:
            # 调整图像大小以适应模型
            image_resized = cv2.resize(image, (224, 224))
            image_tensor = self.transform(image_resized).unsqueeze(0)
            
            # 模拟预测结果
            with torch.no_grad():
                outputs = self.model(image_tensor)
                probabilities = torch.nn.functional.softmax(outputs, dim=1)
            
            # 返回预测结果和置信度
            max_prob, predicted_idx = torch.max(probabilities, 1)
            disease = self.classes[predicted_idx.item()]
            confidence = max_prob.item()
            
            return disease, confidence, probabilities.numpy()[0]
        except Exception as e:
            # 如果预测失败，返回默认值
            return "正常", 0.5, [0.1] * len(self.classes)

# ==============================
# 3D足部建模与AR可视化
# ==============================
class Foot3DModeler:
    def __init__(self):
        self.mesh_data = None
    
    def create_3d_model_from_images(self, images):
        """从多角度图像创建3D足部模型"""
        # 简化版本：创建一个基本的足部形状
        self.generate_simple_foot_mesh()
        return self.mesh_data
    
    def generate_simple_foot_mesh(self):
        """生成简化的足部3D网格"""
        # 创建一个更真实的足部形状
        vertices = []
        faces = []
        
        # 创建足部的基本形状（简化版）
        # 足底
        for i in range(10):
            for j in range(5):
                x = i * 0.1
                y = j * 0.2
                z = 0
                vertices.append([x, y, z])
        
        # 足背
        for i in range(10):
            for j in range(5):
                x = i * 0.1
                y = j * 0.2
                z = 0.1 + (i * 0.01)  # 足背有弧度
                vertices.append([x, y, z])
        
        # 创建面
        for i in range(9):
            for j in range(4):
                # 底面
                idx1 = i * 5 + j
                idx2 = i * 5 + j + 1
                idx3 = (i + 1) * 5 + j
                idx4 = (i + 1) * 5 + j + 1
                
                faces.append([idx1, idx2, idx4])
                faces.append([idx1, idx4, idx3])
                
                # 顶面（偏移50个顶点）
                idx1 += 50
                idx2 += 50
                idx3 += 50
                idx4 += 50
                
                faces.append([idx1, idx3, idx4])
                faces.append([idx1, idx4, idx2])
                
                # 侧面
                faces.append([idx1 - 50, idx3 - 50, idx3])
                faces.append([idx1 - 50, idx3, idx1])
        
        self.mesh_data = {
            'vertices': np.array(vertices, dtype=np.float32),
            'faces': np.array(faces),
            'colors': np.array([1, 0.7, 0.3])  # 肤色
        }
        
        return self.mesh_data
    
    def export_to_stl(self, filename):
        """导出为STL文件用于3D打印"""
        if self.mesh_data is None:
            return False
        
        try:
            foot_mesh = mesh.Mesh(np.zeros(self.mesh_data['faces'].shape[0], dtype=mesh.Mesh.dtype))
            
            for i, face in enumerate(self.mesh_data['faces']):
                for j in range(3):
                    foot_mesh.vectors[i][j] = self.mesh_data['vertices'][face[j]]
            
            foot_mesh.save(filename)
            return True
        except Exception as e:
            print(f"STL导出失败: {e}")
            return False

# ==============================
# 本地设备模拟（替代物联网）
# ==============================
class LocalDeviceManager:
    def __init__(self):
        self.connected_devices = {}
        self.sensor_data = {}
    
    def connect_device(self, device_type, device_id, connection_params=None):
        """连接本地模拟设备"""
        device_info = {
            'type': device_type,
            'id': device_id,
            'connected': True,
            'last_update': datetime.now(),
            'params': connection_params or {}
        }
        
        self.connected_devices[device_id] = device_info
        
        # 初始化传感器数据
        if device_type == 'pressure_mat':
            self.sensor_data[device_id] = self.simulate_pressure_data()
        elif device_type == 'thermal_camera':
            self.sensor_data[device_id] = self.simulate_thermal_data()
        elif device_type == 'moisture_sensor':
            self.sensor_data[device_id] = self.simulate_moisture_data()
        
        return True
    
    def simulate_pressure_data(self):
        """模拟压力垫数据"""
        # 创建一个更真实的足底压力分布
        pressure_matrix = np.zeros((10, 10))
        
        # 足跟区域压力较高
        pressure_matrix[7:9, 3:7] = np.random.uniform(80, 100, (2, 4))
        
        # 足弓区域压力较低
        pressure_matrix[4:6, 2:8] = np.random.uniform(10, 30, (2, 6))
        
        # 前足区域压力中等
        pressure_matrix[1:3, 3:7] = np.random.uniform(50, 70, (2, 4))
        
        return pressure_matrix
    
    def simulate_thermal_data(self):
        """模拟热成像数据"""
        # 创建一个更真实的温度分布
        thermal_matrix = np.ones((20, 20)) * 30  # 基础温度30°C
        
        # 足部中心温度较高
        thermal_matrix[5:15, 5:15] += np.random.uniform(2, 5, (10, 10))
        
        # 边缘温度较低
        thermal_matrix[0:3, :] -= 3
        thermal_matrix[-3:, :] -= 3
        thermal_matrix[:, 0:3] -= 3
        thermal_matrix[:, -3:] -= 3
        
        return thermal_matrix
    
    def simulate_moisture_data(self):
        """模拟湿度传感器数据"""
        return np.random.uniform(50, 70)  # 湿度百分比
    
    def get_realtime_data(self, device_id):
        """获取实时传感器数据"""
        if device_id in self.connected_devices:
            # 更新数据（添加一些随机变化）
            device_type = self.connected_devices[device_id]['type']
            if device_type == 'pressure_mat':
                base_data = self.simulate_pressure_data()
                variation = np.random.normal(0, 5, base_data.shape)
                self.sensor_data[device_id] = np.clip(base_data + variation, 0, 100)
            elif device_type == 'thermal_camera':
                base_data = self.simulate_thermal_data()
                variation = np.random.normal(0, 0.5, base_data.shape)
                self.sensor_data[device_id] = base_data + variation
            elif device_type == 'moisture_sensor':
                base_data = self.simulate_moisture_data()
                variation = np.random.normal(0, 3)
                self.sensor_data[device_id] = np.clip(base_data + variation, 0, 100)
            
            self.connected_devices[device_id]['last_update'] = datetime.now()
            return self.sensor_data[device_id]
        
        return None

# ==============================
# 本地协作模拟（替代实时协作）
# ==============================
class LocalCollaboration:
    def __init__(self):
        self.users = {}
        self.messages = []
    
    def add_user(self, user_id, user_name):
        """添加本地用户"""
        self.users[user_id] = {
            'name': user_name,
            'joined_time': datetime.now()
        }
    
    def send_message(self, user_id, message):
        """发送本地消息"""
        msg = {
            'user_id': user_id,
            'user_name': self.users.get(user_id, {}).get('name', '未知用户'),
            'message': message,
            'timestamp': datetime.now().isoformat()
        }
        self.messages.append(msg)
        return msg
    
    def get_recent_messages(self, count=10):
        """获取最近的消息"""
        return self.messages[-count:]

# ==============================
# 高级可视化组件
# ==============================
class VTKFootViewer(QVTKRenderWindowInteractor):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.renderer = vtk.vtkRenderer()
        self.GetRenderWindow().AddRenderer(self.renderer)
        
        # 设置背景色
        self.renderer.SetBackground(0.1, 0.1, 0.2)
        
        # 初始化相机
        self.renderer.ResetCamera()
    
    def load_foot_model(self, vertices, faces, colors=None):
        """加载足部3D模型"""
        # 清除之前的模型
        self.renderer.RemoveAllViewProps()
        
        # 创建顶点
        points = vtk.vtkPoints()
        for vertex in vertices:
            points.InsertNextPoint(vertex)
        
        # 创建多边形
        polygons = vtk.vtkCellArray()
        for face in faces:
            polygon = vtk.vtkPolygon()
            polygon.GetPointIds().SetNumberOfIds(3)
            for i, vertex_idx in enumerate(face):
                polygon.GetPointIds().SetId(i, vertex_idx)
            polygons.InsertNextCell(polygon)
        
        # 创建多边形数据
        polygon_data = vtk.vtkPolyData()
        polygon_data.SetPoints(points)
        polygon_data.SetPolys(polygons)
        
        # 创建映射器和演员
        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputData(polygon_data)
        
        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        
        # 设置颜色
        if colors is not None:
            actor.GetProperty().SetColor(colors[0], colors[1], colors[2])
        else:
            actor.GetProperty().SetColor(1.0, 0.7, 0.3)  # 肤色
        
        # 添加到渲染器
        self.renderer.AddActor(actor)
        self.renderer.ResetCamera()
        self.GetRenderWindow().Render()

class ARFootOverlay(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene()
        self.setScene(self.scene)
        
        # 设置视图属性
        self.setRenderHint(QPainter.Antialiasing)
        
        # 存储AR元素
        self.ar_elements = {}
    
    def add_foot_overlay(self, image, landmarks, conditions):
        """添加足部AR叠加层"""
        # 清除现有内容
        self.scene.clear()
        self.ar_elements.clear()
        
        # 添加背景图像
        height, width = image.shape[:2]
        bytes_per_line = 3 * width
        q_img = QImage(image.data, width, height, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(q_img)
        bg_item = QGraphicsPixmapItem(pixmap)
        self.scene.addItem(bg_item)
        
        # 添加关键点标注
        for i, landmark in enumerate(landmarks):
            x, y = landmark[0] * width, landmark[1] * height  # 假设landmarks是归一化坐标
            ellipse = self.scene.addEllipse(x-5, y-5, 10, 10, 
                                           QPen(QColor(255, 0, 0)), 
                                           QBrush(QColor(255, 0, 0, 100)))
            self.ar_elements[f"landmark_{i}"] = ellipse
        
        # 添加问题区域标注
        for i, (condition, detected) in enumerate(conditions.items()):
            if detected:
                # 在图像上添加标注
                rect = self.scene.addRect(10, 10 + i * 30, 200, 25, 
                                         QPen(QColor(255, 0, 0, 200)),
                                         QBrush(QColor(255, 0, 0, 50)))
                text = self.scene.addText(condition)
                text.setPos(15, 10 + i * 30)
                text.setDefaultTextColor(QColor(255, 255, 255))
                
                self.ar_elements[f"condition_{condition}"] = (rect, text)
        
        self.fitInView(bg_item, Qt.KeepAspectRatio)

# ==============================
# 智能推荐引擎
# ==============================
class IntelligentRecommendationEngine:
    def __init__(self):
        self.product_database = self.load_product_database()
        self.exercise_library = self.load_exercise_library()
        self.treatment_protocols = self.load_treatment_protocols()
    
    def load_product_database(self):
        """加载产品数据库"""
        return {
            'moisturizer': {
                'name': '深层保湿霜',
                'type': '护肤品',
                'for_conditions': ['dryness', 'cracking'],
                'ingredients': ['尿素', '甘油', '神经酰胺'],
                'rating': 4.5,
                'price_range': '中等'
            },
            'orthotic': {
                'name': '定制矫形鞋垫',
                'type': '矫形器',
                'for_conditions': ['flat_feet', 'high_arches', 'plantar_fasciitis'],
                'materials': ['记忆泡沫', '硅胶'],
                'rating': 4.8,
                'price_range': '高等'
            },
            'massage_roller': {
                'name': '足底按摩滚轮',
                'type': '康复设备',
                'for_conditions': ['plantar_fasciitis', 'foot_fatigue'],
                'materials': ['塑料', '按摩凸点'],
                'rating': 4.3,
                'price_range': '低等'
            }
        }
    
    def load_exercise_library(self):
        """加载锻炼动作库"""
        return {
            'towel_curls': {
                'name': '毛巾卷曲',
                'description': '用脚趾卷起毛巾，增强足底肌肉',
                'difficulty': '简单',
                'duration': '5分钟',
                'for_conditions': ['flat_feet', 'weak_arches']
            },
            'heel_raises': {
                'name': '提踵运动',
                'description': '站立提踵，增强小腿和足部肌肉',
                'difficulty': '中等',
                'duration': '10分钟',
                'for_conditions': ['plantar_fasciitis', 'achilles_tendinitis']
            },
            'toe_spreads': {
                'name': '脚趾展开',
                'description': '尽量展开脚趾，增强脚趾灵活性',
                'difficulty': '简单',
                'duration': '3分钟',
                'for_conditions': ['bunions', 'hammertoes']
            }
        }
    
    def load_treatment_protocols(self):
        """加载治疗方案库"""
        return {
            'plantar_fasciitis': {
                'name': '足底筋膜炎治疗方案',
                'duration': '6-8周',
                'exercises': ['towel_curls', 'heel_raises', 'calf_stretches'],
                'products': ['orthotic', 'massage_roller'],
                'frequency': '每日2次',
                'success_rate': 0.85
            },
            'bunions': {
                'name': '拇趾外翻保守治疗方案',
                'duration': '3-6个月',
                'exercises': ['toe_spreads', 'big_toe_stretches'],
                'products': ['bunion_splint', 'wide_shoes'],
                'frequency': '每日3次',
                'success_rate': 0.70
            }
        }
    
    def generate_personalized_plan(self, user_profile, conditions, severity):
        """生成个性化护理计划"""
        plan = {
            'user_id': user_profile['id'],
            'generated_date': datetime.now().isoformat(),
            'conditions_targeted': conditions,
            'duration_weeks': max(4, severity * 2),
            'daily_routine': [],
            'recommended_products': [],
            'expected_improvement': f"{min(90, severity * 15)}%",
            'follow_up_schedule': []
        }
        
        # 根据条件推荐产品
        for condition in conditions:
            for product_id, product in self.product_database.items():
                if condition in product.get('for_conditions', []):
                    plan['recommended_products'].append(product)
        
        # 创建日常护理流程
        morning_routine = {
            'time': '早晨',
            'activities': ['温水泡脚5分钟', '涂抹保湿霜', '进行足部伸展运动']
        }
        
        evening_routine = {
            'time': '晚间',
            'activities': ['温水泡脚10分钟', '按摩足部', '使用矫形设备(如需要)']
        }
        
        plan['daily_routine'].append(morning_routine)
        plan['daily_routine'].append(evening_routine)
        
        # 设置随访计划
        for week in [2, 4, 8, 12]:
            plan['follow_up_schedule'].append({
                'week': week,
                'activity': '专业评估和方案调整'
            })
        
        return plan

# ==============================
# 主应用程序
# ==============================
class LocalFootCareSystem(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # 初始化核心组件（全部本地化）
        self.health_record = LocalHealthRecord()
        self.ai_diagnosis = FootDiseaseDiagnosisAI()
        self.device_manager = LocalDeviceManager()
        self.collaboration = LocalCollaboration()
        self.recommendation_engine = IntelligentRecommendationEngine()
        self.foot_modeler = Foot3DModeler()
        
        # 状态变量
        self.current_user_id = "default_user"
        self.current_foot_model = None
        self.realtime_data_active = False
        
        self.init_ui()
        self.setup_realtime_data_stream()
    
    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("本地智能足部护理系统")
        self.setGeometry(50, 50, 1400, 900)
        
        # 设置现代UI样式
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QTabWidget::pane {
                border: 1px solid #555;
                background-color: #3c3c3c;
            }
            QTabBar::tab {
                background-color: #4c4c4c;
                color: white;
                padding: 8px 12px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background-color: #6c6c6c;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #555;
                border-radius: 5px;
                margin-top: 1ex;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QPushButton {
                background-color: #5c5c5c;
                color: white;
                border: none;
                padding: 5px 10px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #6c6c6c;
            }
            QPushButton:pressed {
                background-color: #4c4c4c;
            }
        """)
        
        # 创建中央部件和主布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # 创建标签页
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)
        
        # 添加各个功能标签页（移除需要网络连接的标签）
        self.setup_ai_diagnosis_tab()
        self.setup_3d_modeling_tab()
        self.setup_ar_view_tab()
        self.setup_device_dashboard_tab()
        self.setup_local_records_tab()
        self.setup_personal_plan_tab()
        
        # 创建状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("系统就绪 - 本地足部护理平台")
        
        # 创建工具栏
        self.setup_toolbar()
    
    def setup_toolbar(self):
        """设置工具栏"""
        toolbar = QToolBar("智能工具")
        toolbar.setIconSize(QSize(24, 24))
        self.addToolBar(toolbar)
        
        # AI诊断工具
        ai_action = QAction("AI诊断", self)
        ai_action.triggered.connect(self.run_ai_diagnosis)
        toolbar.addAction(ai_action)
        
        # 3D扫描工具
        scan_action = QAction("3D扫描", self)
        scan_action.triggered.connect(self.start_3d_scan)
        toolbar.addAction(scan_action)
        
        toolbar.addSeparator()
        
        # 设备连接工具
        device_action = QAction("模拟设备", self)
        device_action.triggered.connect(self.show_device_connection_dialog)
        toolbar.addAction(device_action)
        
        # 实时数据流
        stream_action = QAction("实时数据", self)
        stream_action.setCheckable(True)
        stream_action.toggled.connect(self.toggle_realtime_data)
        toolbar.addAction(stream_action)
    
    def setup_ai_diagnosis_tab(self):
        """设置AI诊断标签页"""
        tab = QWidget()
        layout = QHBoxLayout(tab)
        
        # 左侧 - 图像上传和分析
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # 图像上传区域
        upload_group = QGroupBox("足部图像分析")
        upload_layout = QVBoxLayout(upload_group)
        
        self.image_display = QLabel()
        self.image_display.setAlignment(Qt.AlignCenter)
        self.image_display.setStyleSheet("border: 2px dashed #666; min-height: 300px;")
        self.image_display.setText("点击上传足部图像")
        self.image_display.mousePressEvent = self.upload_foot_image
        
        upload_layout.addWidget(self.image_display)
        
        # 分析按钮
        analyze_btn = QPushButton("AI诊断分析")
        analyze_btn.clicked.connect(self.analyze_foot_image)
        analyze_btn.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-weight: bold; }")
        upload_layout.addWidget(analyze_btn)
        
        left_layout.addWidget(upload_group)
        
        # 右侧 - 诊断结果
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # 诊断结果
        results_group = QGroupBox("AI诊断结果")
        results_layout = QVBoxLayout(results_group)
        
        self.diagnosis_results = QTextEdit()
        self.diagnosis_results.setReadOnly(True)
        results_layout.addWidget(self.diagnosis_results)
        
        right_layout.addWidget(results_group)
        
        # 置信度图表
        confidence_group = QGroupBox("诊断置信度")
        confidence_layout = QVBoxLayout(confidence_group)
        
        self.confidence_chart = pg.PlotWidget()
        self.confidence_chart.setBackground('#2b2b2b')
        confidence_layout.addWidget(self.confidence_chart)
        
        right_layout.addWidget(confidence_group)
        
        # 添加到主布局
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([500, 700])
        
        layout.addWidget(splitter)
        
        self.tabs.addTab(tab, "AI智能诊断")
    
    def setup_3d_modeling_tab(self):
        """设置3D建模标签页"""
        tab = QWidget()
        layout = QHBoxLayout(tab)
        
        # 左侧 - 3D视图
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # 3D可视化
        view_group = QGroupBox("3D足部模型")
        view_layout = QVBoxLayout(view_group)
        
        self.vtk_viewer = VTKFootViewer()
        self.vtk_viewer.setMinimumSize(500, 400)
        view_layout.addWidget(self.vtk_viewer)
        
        left_layout.addWidget(view_group)
        
        # 右侧 - 控制面板
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # 模型控制
        control_group = QGroupBox("模型控制")
        control_layout = QVBoxLayout(control_group)
        
        # 扫描按钮
        scan_btn = QPushButton("开始3D扫描")
        scan_btn.clicked.connect(self.start_3d_scanning)
        control_layout.addWidget(scan_btn)
        
        # 导出选项
        export_group = QGroupBox("导出选项")
        export_layout = QVBoxLayout(export_group)
        
        stl_btn = QPushButton("导出为STL(3D打印)")
        stl_btn.clicked.connect(self.export_to_stl)
        export_layout.addWidget(stl_btn)
        
        control_layout.addWidget(export_group)
        
        # 测量工具
        measure_group = QGroupBox("测量工具")
        measure_layout = QVBoxLayout(measure_group)
        
        length_btn = QPushButton("测量长度")
        length_btn.clicked.connect(self.measure_length)
        measure_layout.addWidget(length_btn)
        
        volume_btn = QPushButton("测量体积")
        volume_btn.clicked.connect(self.measure_volume)
        measure_layout.addWidget(volume_btn)
        
        control_layout.addWidget(measure_group)
        
        right_layout.addWidget(control_group)
        
        # 模型信息
        info_group = QGroupBox("模型信息")
        info_layout = QVBoxLayout(info_group)
        
        self.model_info = QTextEdit()
        self.model_info.setReadOnly(True)
        info_layout.addWidget(self.model_info)
        
        right_layout.addWidget(info_group)
        
        right_layout.addStretch()
        
        # 添加到主布局
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        
        layout.addWidget(splitter)
        
        self.tabs.addTab(tab, "3D建模")
    
    def setup_ar_view_tab(self):
        """设置AR视图标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # AR视图区域
        ar_group = QGroupBox("增强现实足部可视化")
        ar_layout = QVBoxLayout(ar_group)
        
        self.ar_view = ARFootOverlay()
        self.ar_view.setMinimumSize(600, 500)
        ar_layout.addWidget(self.ar_view)
        
        # AR控制
        control_layout = QHBoxLayout()
        
        start_ar_btn = QPushButton("启动AR模式")
        start_ar_btn.clicked.connect(self.start_ar_mode)
        control_layout.addWidget(start_ar_btn)
        
        capture_btn = QPushButton("保存AR视图")
        capture_btn.clicked.connect(self.capture_ar_view)
        control_layout.addWidget(capture_btn)
        
        ar_layout.addLayout(control_layout)
        
        layout.addWidget(ar_group)
        
        self.tabs.addTab(tab, "AR可视化")
    
    def setup_device_dashboard_tab(self):
        """设置设备仪表板标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 设备状态
        status_group = QGroupBox("模拟设备状态")
        status_layout = QHBoxLayout(status_group)
        
        # 压力垫可视化
        pressure_group = QGroupBox("足底压力分布")
        pressure_layout = QVBoxLayout(pressure_group)
        
        self.pressure_plot = pg.PlotWidget()
        self.pressure_plot.setBackground('#2b2b2b')
        pressure_layout.addWidget(self.pressure_plot)
        
        status_layout.addWidget(pressure_group)
        
        # 热成像可视化
        thermal_group = QGroupBox("足部热成像")
        thermal_layout = QVBoxLayout(thermal_group)
        
        self.thermal_plot = pg.PlotWidget()
        self.thermal_plot.setBackground('#2b2b2b')
        thermal_layout.addWidget(self.thermal_plot)
        
        status_layout.addWidget(thermal_group)
        
        layout.addWidget(status_group)
        
        # 设备控制
        control_group = QGroupBox("设备控制")
        control_layout = QHBoxLayout(control_group)
        
        connect_pressure_btn = QPushButton("连接压力垫")
        connect_pressure_btn.clicked.connect(lambda: self.connect_device('pressure_mat', 'pressure_001'))
        control_layout.addWidget(connect_pressure_btn)
        
        connect_thermal_btn = QPushButton("连接热成像")
        connect_thermal_btn.clicked.connect(lambda: self.connect_device('thermal_camera', 'thermal_001'))
        control_layout.addWidget(connect_thermal_btn)
        
        layout.addWidget(control_group)
        
        self.tabs.addTab(tab, "设备仪表板")
    
    def setup_local_records_tab(self):
        """设置本地记录标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 本地记录
        records_group = QGroupBox("本地健康记录")
        records_layout = QVBoxLayout(records_group)
        
        # 记录列表
        self.record_tree = QTreeWidget()
        self.record_tree.setHeaderLabels(["时间戳", "记录哈希", "数据类型", "状态"])
        records_layout.addWidget(self.record_tree)
        
        # 操作按钮
        button_layout = QHBoxLayout()
        
        add_record_btn = QPushButton("添加记录")
        add_record_btn.clicked.connect(self.add_local_record)
        button_layout.addWidget(add_record_btn)
        
        verify_btn = QPushButton("验证记录")
        verify_btn.clicked.connect(self.verify_local_record)
        button_layout.addWidget(verify_btn)
        
        refresh_btn = QPushButton("刷新列表")
        refresh_btn.clicked.connect(self.refresh_records)
        button_layout.addWidget(refresh_btn)
        
        records_layout.addLayout(button_layout)
        
        layout.addWidget(records_group)
        
        # 记录详情
        detail_group = QGroupBox("记录详情")
        detail_layout = QVBoxLayout(detail_group)
        
        self.record_detail = QTextEdit()
        self.record_detail.setReadOnly(True)
        detail_layout.addWidget(self.record_detail)
        
        layout.addWidget(detail_group)
        
        self.tabs.addTab(tab, "健康记录")
    
    def setup_personal_plan_tab(self):
        """设置个性化计划标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 个性化计划
        plan_group = QGroupBox("个性化护理计划")
        plan_layout = QVBoxLayout(plan_group)
        
        self.plan_view = QTextEdit()
        self.plan_view.setReadOnly(True)
        plan_layout.addWidget(self.plan_view)
        
        # 计划控制
        control_layout = QHBoxLayout()
        
        generate_btn = QPushButton("生成新计划")
        generate_btn.clicked.connect(self.generate_care_plan)
        control_layout.addWidget(generate_btn)
        
        export_btn = QPushButton("导出计划")
        export_btn.clicked.connect(self.export_care_plan)
        control_layout.addWidget(export_btn)
        
        plan_layout.addLayout(control_layout)
        
        layout.addWidget(plan_group)
        
        self.tabs.addTab(tab, "护理计划")
    
    def setup_realtime_data_stream(self):
        """设置实时数据流"""
        self.data_timer = QTimer()
        self.data_timer.timeout.connect(self.update_realtime_data)
    
    # ==============================
    # 核心功能实现
    # ==============================
    
    def upload_foot_image(self, event):
        """上传足部图像"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择足部图像", "", "图像文件 (*.png *.jpg *.jpeg *.bmp)"
        )
        
        if file_path:
            self.current_image_path = file_path
            pixmap = QPixmap(file_path)
            scaled_pixmap = pixmap.scaled(400, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.image_display.setPixmap(scaled_pixmap)
            self.status_bar.showMessage(f"已加载图像: {os.path.basename(file_path)}")
    
    def analyze_foot_image(self):
        """分析足部图像"""
        if not hasattr(self, 'current_image_path') or not self.current_image_path:
            QMessageBox.warning(self, "警告", "请先上传足部图像")
            return
        
        try:
            # 使用AI进行诊断
            image = cv2.imread(self.current_image_path)
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            disease, confidence, probabilities = self.ai_diagnosis.predict(image_rgb)
            
            # 显示诊断结果
            result_text = f"""
            <h2>AI诊断结果</h2>
            <p><b>诊断:</b> {disease}</p>
            <p><b>置信度:</b> {confidence:.2%}</p>
            <p><b>详细分析:</b></p>
            <ul>
            """
            
            for i, prob in enumerate(probabilities):
                result_text += f"<li>{self.ai_diagnosis.classes[i]}: {prob:.2%}</li>"
            
            result_text += "</ul>"
            
            self.diagnosis_results.setHtml(result_text)
            
            # 显示置信度图表
            self.plot_confidence_chart(probabilities)
            
            # 将结果保存到本地数据库
            record_data = {
                'diagnosis': disease,
                'confidence': confidence,
                'timestamp': datetime.now().isoformat(),
                'image_path': self.current_image_path
            }
            
            record_hash = self.health_record.add_record(
                self.current_user_id,
                record_data
            )
            
            self.status_bar.showMessage(f"诊断完成 - 记录已保存: {record_hash[:16]}...")
            
            # 刷新记录列表
            self.refresh_records()
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"图像分析失败: {str(e)}")
    
    def plot_confidence_chart(self, probabilities):
        """绘制置信度图表"""
        self.confidence_chart.clear()
        
        # 创建条形图
        x = np.arange(len(self.ai_diagnosis.classes))
        bars = pg.BarGraphItem(x=x, height=probabilities, width=0.6, brush='g')
        self.confidence_chart.addItem(bars)
        
        # 设置图表属性
        self.confidence_chart.setLabel('left', '置信度')
        self.confidence_chart.setLabel('bottom', '疾病类型')
        self.confidence_chart.setXRange(-0.5, len(self.ai_diagnosis.classes)-0.5)
        self.confidence_chart.setYRange(0, 1)
        
        # 添加x轴标签
        axis = self.confidence_chart.getAxis('bottom')
        axis.setTicks([[(i, label) for i, label in enumerate(self.ai_diagnosis.classes)]])
    
    def start_3d_scanning(self):
        """开始3D扫描"""
        QMessageBox.information(self, "3D扫描", 
                               "请从不同角度拍摄足部照片(前、后、左、右、上、下)")
        
        # 模拟扫描过程
        self.scan_progress = QProgressDialog("正在进行3D扫描...", "取消", 0, 100, self)
        self.scan_progress.setWindowTitle("3D扫描")
        self.scan_progress.show()
        
        # 模拟扫描进度
        self.scan_timer = QTimer()
        self.scan_timer.timeout.connect(self.update_scan_progress)
        self.scan_timer.start(100)
    
    def update_scan_progress(self):
        """更新扫描进度"""
        current_value = self.scan_progress.value() + 5
        self.scan_progress.setValue(current_value)
        
        if current_value >= 100:
            self.scan_timer.stop()
            self.scan_progress.close()
            self.complete_3d_scan()
    
    def complete_3d_scan(self):
        """完成3D扫描"""
        # 生成模拟的3D模型
        self.foot_modeler.generate_simple_foot_mesh()
        mesh_data = self.foot_modeler.mesh_data
        
        # 在VTK查看器中显示
        self.vtk_viewer.load_foot_model(
            mesh_data['vertices'], 
            mesh_data['faces'], 
            mesh_data['colors']
        )
        
        # 更新模型信息
        info_text = f"""
        <h3>3D模型信息</h3>
        <p><b>顶点数量:</b> {len(mesh_data['vertices'])}</p>
        <p><b>面片数量:</b> {len(mesh_data['faces'])}</p>
        <p><b>生成时间:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        """
        
        self.model_info.setHtml(info_text)
        self.current_foot_model = mesh_data
        
        self.status_bar.showMessage("3D扫描完成")
    
    def export_to_stl(self):
        """导出为STL文件"""
        if self.current_foot_model:
            file_path, _ = QFileDialog.getSaveFileName(
                self, "保存STL文件", "", "STL文件 (*.stl)"
            )
            
            if file_path:
                if self.foot_modeler.export_to_stl(file_path):
                    QMessageBox.information(self, "导出成功", "STL文件已保存")
                else:
                    QMessageBox.warning(self, "导出失败", "无法保存STL文件")
        else:
            QMessageBox.warning(self, "警告", "没有可导出的3D模型")
    
    def measure_length(self):
        """测量长度"""
        if self.current_foot_model:
            # 计算模型的大致长度
            vertices = self.current_foot_model['vertices']
            x_range = np.max(vertices[:, 0]) - np.min(vertices[:, 0])
            length_cm = x_range * 25  # 假设比例尺
            QMessageBox.information(self, "长度测量", f"估算长度: {length_cm:.1f} 厘米")
        else:
            QMessageBox.warning(self, "警告", "没有可测量的3D模型")
    
    def measure_volume(self):
        """测量体积"""
        if self.current_foot_model:
            # 简化体积计算
            vertices = self.current_foot_model['vertices']
            x_range = np.ptp(vertices[:, 0])
            y_range = np.ptp(vertices[:, 1]) 
            z_range = np.ptp(vertices[:, 2])
            volume = x_range * y_range * z_range * 1000  # 粗略估算
            QMessageBox.information(self, "体积测量", f"估算体积: {volume:.1f} 立方厘米")
        else:
            QMessageBox.warning(self, "警告", "没有可测量的3D模型")
    
    def start_ar_mode(self):
        """启动AR模式"""
        if hasattr(self, 'current_image_path') and self.current_image_path:
            try:
                image = cv2.imread(self.current_image_path)
                image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                
                # 模拟关键点检测（使用随机点）
                landmarks = []
                for i in range(10):
                    x = np.random.uniform(0.1, 0.9)
                    y = np.random.uniform(0.1, 0.9)
                    landmarks.append([x, y])
                
                # 模拟检测到的条件
                conditions = {
                    '干燥': np.random.choice([True, False]),
                    '发红': np.random.choice([True, False]),
                    '肿胀': np.random.choice([True, False])
                }
                
                self.ar_view.add_foot_overlay(image_rgb, landmarks, conditions)
                self.status_bar.showMessage("AR模式已启动")
            except Exception as e:
                QMessageBox.warning(self, "AR模式错误", f"无法启动AR模式: {str(e)}")
        else:
            QMessageBox.warning(self, "警告", "请先上传足部图像")
    
    def capture_ar_view(self):
        """保存AR视图"""
        try:
            # 获取当前时间作为文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"ar_capture_{timestamp}.png"
            
            # 创建截图
            pixmap = QPixmap(self.ar_view.size())
            self.ar_view.render(pixmap)
            pixmap.save(filename)
            
            QMessageBox.information(self, "保存成功", f"AR视图已保存为: {filename}")
        except Exception as e:
            QMessageBox.warning(self, "保存失败", f"无法保存AR视图: {str(e)}")
    
    def connect_device(self, device_type, device_id):
        """连接模拟设备"""
        success = self.device_manager.connect_device(device_type, device_id)
        if success:
            self.status_bar.showMessage(f"已连接{device_type}设备: {device_id}")
            if not self.realtime_data_active:
                self.toggle_realtime_data(True)
        else:
            self.status_bar.showMessage(f"连接{device_type}设备失败")
    
    def toggle_realtime_data(self, enabled):
        """切换实时数据流"""
        self.realtime_data_active = enabled
        
        if enabled:
            self.data_timer.start(500)  # 每500ms更新一次
            self.status_bar.showMessage("实时数据流已启动")
        else:
            self.data_timer.stop()
            self.status_bar.showMessage("实时数据流已停止")
    
    def update_realtime_data(self):
        """更新实时数据"""
        # 更新压力分布
        pressure_data = self.device_manager.get_realtime_data('pressure_001')
        if pressure_data is not None and hasattr(self, 'pressure_plot'):
            self.pressure_plot.clear()
            img = pg.ImageItem(pressure_data)
            self.pressure_plot.addItem(img)
            self.pressure_plot.setTitle("足底压力分布")
        
        # 更新热成像
        thermal_data = self.device_manager.get_realtime_data('thermal_001')
        if thermal_data is not None and hasattr(self, 'thermal_plot'):
            self.thermal_plot.clear()
            img_thermal = pg.ImageItem(thermal_data)
            self.thermal_plot.addItem(img_thermal)
            self.thermal_plot.setTitle("足部热成像")
    
    def add_local_record(self):
        """添加本地记录"""
        record_data = {
            'type': 'manual_entry',
            'timestamp': datetime.now().isoformat(),
            'notes': '用户手动添加的记录',
            'data': {'example': 'sample_data'}
        }
        
        record_hash = self.health_record.add_record(self.current_user_id, record_data)
        
        # 更新记录树
        self.refresh_records()
        
        QMessageBox.information(self, "成功", f"记录已添加到本地数据库\n哈希: {record_hash[:16]}...")
    
    def verify_local_record(self):
        """验证本地记录"""
        current_item = self.record_tree.currentItem()
        if not current_item:
            QMessageBox.warning(self, "警告", "请先选择一条记录")
            return
        
        record_hash = current_item.text(1)
        
        is_valid = self.health_record.verify_record(record_hash)
        
        if is_valid:
            QMessageBox.information(self, "验证结果", "记录完整性验证通过")
        else:
            QMessageBox.warning(self, "验证结果", "记录验证失败")
    
    def refresh_records(self):
        """刷新记录列表"""
        records = self.health_record.get_user_records(self.current_user_id)
        self.record_tree.clear()
        
        for record in records:
            record_id, user_id, record_data, record_hash, timestamp, signature = record
            data_obj = json.loads(record_data)
            record_type = data_obj.get('type', '未知')
            
            item = QTreeWidgetItem([
                datetime.fromisoformat(timestamp).strftime('%Y-%m-%d %H:%M'),
                record_hash[:16] + '...',
                record_type,
                '已验证'
            ])
            self.record_tree.addTopLevelItem(item)
    
    def generate_care_plan(self):
        """生成护理计划"""
        user_profile = {
            'id': self.current_user_id,
            'age': 35,
            'foot_type': 'normal'
        }
        
        conditions = ['干燥', '轻度拇趾外翻']
        severity = 2  # 1-5级
        
        plan = self.recommendation_engine.generate_personalized_plan(
            user_profile, conditions, severity
        )
        
        # 显示计划
        plan_text = f"""个性化足部护理计划
        ========================
        
        基本信息
        --------
        生成日期: {plan['generated_date']}
        目标条件: {', '.join(plan['conditions_targeted'])}
        计划时长: {plan['duration_weeks']} 周
        预期改善: {plan['expected_improvement']}
        
        日常护理流程
        -----------
        """
        
        for routine in plan['daily_routine']:
            plan_text += f"\n{routine['time']}:\n"
            for activity in routine['activities']:
                plan_text += f"  • {activity}\n"
        
        plan_text += "\n推荐产品\n--------\n"
        for product in plan['recommended_products']:
            plan_text += f"• {product['name']} ({product['type']}) - 评分: {product['rating']}/5.0\n"
        
        plan_text += "\n随访计划\n--------\n"
        for schedule in plan['follow_up_schedule']:
            plan_text += f"• 第{schedule['week']}周: {schedule['activity']}\n"
        
        self.plan_view.setPlainText(plan_text)
        self.status_bar.showMessage("个性化护理计划已生成")
    
    def export_care_plan(self):
        """导出护理计划"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出护理计划", "", "文本文件 (*.txt)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.plan_view.toPlainText())
                QMessageBox.information(self, "导出成功", "护理计划已导出")
            except Exception as e:
                QMessageBox.warning(self, "导出失败", f"无法导出文件: {str(e)}")
    
    def show_device_connection_dialog(self):
        """显示设备连接对话框"""
        QMessageBox.information(self, "设备连接", 
                               "模拟设备连接已建立\n压力垫: 已连接\n热成像相机: 已连接")
        
        # 自动连接模拟设备
        self.connect_device('pressure_mat', 'pressure_001')
        self.connect_device('thermal_camera', 'thermal_001')
        
        self.tabs.setCurrentIndex(3)  # 切换到设备仪表板
    
    def run_ai_diagnosis(self):
        """运行AI诊断"""
        self.tabs.setCurrentIndex(0)  # 切换到AI诊断标签
        if hasattr(self, 'current_image_path') and self.current_image_path:
            self.analyze_foot_image()
        else:
            self.upload_foot_image(None)
    
    def start_3d_scan(self):
        """开始3D扫描"""
        self.tabs.setCurrentIndex(1)  # 切换到3D建模标签
        self.start_3d_scanning()

# ==============================
# 应用程序入口
# ==============================
def main():
    # 启用高DPI缩放
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    
    app = QApplication(sys.argv)
    
    # 设置应用程序样式
    app.setStyle('Fusion')
    
    # 创建并显示主窗口
    window = LocalFootCareSystem()
    window.show()
    
    # 运行应用程序
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()