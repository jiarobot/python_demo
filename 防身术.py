import sys
import json
import random
import math
import csv
import os
from datetime import datetime, timedelta
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QListWidget, QTextEdit, QLineEdit, 
                             QCalendarWidget, QTimeEdit, QSplitter, QTabWidget, QFrame,
                             QMessageBox, QProgressBar, QSlider, QSpinBox, QComboBox,
                             QGroupBox, QGridLayout, QFileDialog, QCheckBox, QRadioButton,
                             QStackedWidget, QTableWidget, QTableWidgetItem, QHeaderView,
                             QDialog, QDialogButtonBox, QFormLayout, QDoubleSpinBox, QStyle,
                             QGraphicsView, QGraphicsScene, QGraphicsEllipseItem, QGraphicsLineItem,
                             QGraphicsTextItem, QSizePolicy, QMenu, QAction, QSystemTrayIcon)
from PyQt5.QtCore import Qt, QTimer, QSize, pyqtSignal, QPoint, QRectF, QDateTime,  QSettings
from PyQt5.QtGui import (QFont, QIcon, QPixmap, QColor, QPalette, QPainter, QPen, QBrush, 
                         QLinearGradient, QRadialGradient, QKeySequence, QMovie)
from PyQt5.QtMultimedia import QSound, QMediaPlayer, QMediaContent
from PyQt5.QtMultimediaWidgets import QVideoWidget
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply

class SelfDefenseDatabase:
    """防身术数据库管理类"""
    def __init__(self):
        self.techniques = {
            "basic": ["直拳", "踢腿", "格挡", "闪避"],
            "advanced": ["关节锁", "摔法", "反击技巧", "多人应对"],
            "weapon_defense": ["刀具防御", "棍棒防御", "枪支防御"]
        }
        
        self.training_plans = []
        self.emergency_contacts = []
        
    def load_data(self):
        """加载数据"""
        try:
            with open('self_defense_data.json', 'r') as f:
                data = json.load(f)
                self.training_plans = data.get('training_plans', [])
                self.emergency_contacts = data.get('emergency_contacts', [])
        except FileNotFoundError:
            self.training_plans = []
            self.emergency_contacts = []
    
    def save_data(self):
        """保存数据"""
        data = {
            'training_plans': self.training_plans,
            'emergency_contacts': self.emergency_contacts
        }
        with open('self_defense_data.json', 'w') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    
    def add_training_plan(self, plan):
        """添加训练计划"""
        self.training_plans.append(plan)
        self.save_data()
    
    def add_emergency_contact(self, contact):
        """添加紧急联系人"""
        self.emergency_contacts.append(contact)
        self.save_data()

# 模拟AI分析服务
class AIAnalysisService:
    def __init__(self):
        self.technique_db = self.load_technique_database()
    
    def load_technique_database(self):
        """加载防身术技术数据库"""
        techniques = {
            "punch": {
                "name": "直拳",
                "key_points": ["shoulder", "elbow", "wrist"],
                "ideal_angles": {
                    "elbow": 180,
                    "shoulder_rotation": 45
                }
            },
            "kick": {
                "name": "前踢",
                "key_points": ["hip", "knee", "ankle"],
                "ideal_angles": {
                    "knee": 160,
                    "hip_flexion": 90
                }
            },
            "block": {
                "name": "上格挡",
                "key_points": ["shoulder", "elbow", "wrist"],
                "ideal_angles": {
                    "elbow": 135,
                    "shoulder_abduction": 75
                }
            }
        }
        return techniques
    
    def analyze_pose(self, pose_data, technique):
        """分析姿势并给出反馈"""
        if technique not in self.technique_db:
            return {"error": "未知技术"}
        
        # 模拟AI分析过程
        score = random.uniform(60, 95)
        feedback = []
        
        if score < 70:
            feedback.append("姿势需要改进：注意保持身体平衡")
        if score < 80:
            feedback.append("动作幅度可以更大一些")
        if score > 90:
            feedback.append("优秀！保持这个姿势")
        
        # 随机生成一些详细数据
        details = {
            "power": random.uniform(70, 100),
            "speed": random.uniform(60, 95),
            "accuracy": random.uniform(75, 98),
            "balance": random.uniform(65, 95)
        }
        
        return {
            "score": round(score, 1),
            "feedback": feedback,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
    
    def compare_with_expert(self, technique):
        """获取专家示范数据"""
        if technique not in self.technique_db:
            return None
        
        return {
            "video_url": f"https://example.com/videos/{technique}_expert.mp4",
            "key_points": self.technique_db[technique]["key_points"],
            "ideal_angles": self.technique_db[technique]["ideal_angles"]
        }


# 云同步服务
class CloudSyncService:
    def __init__(self):
        self.settings = QSettings("SelfDefenseApp", "CloudSync")
        self.network_manager = QNetworkAccessManager()
        self.is_connected = False
        self.check_connection()
    
    def check_connection(self):
        """检查网络连接"""
        # 模拟网络检查
        self.is_connected = random.random() > 0.2  # 80%的连接成功率
        return self.is_connected
    
    def upload_data(self, data_type, data):
        """上传数据到云端"""
        if not self.check_connection():
            return False, "网络连接失败"
        
        # 模拟上传过程
        success = random.random() > 0.3  # 70%的上传成功率
        
        if success:
            # 保存上次同步时间
            self.settings.setValue(f"last_sync_{data_type}", datetime.now().toString())
            return True, "数据上传成功"
        else:
            return False, "上传失败，请重试"
    
    def download_data(self, data_type):
        """从云端下载数据"""
        if not self.check_connection():
            return False, "网络连接失败", None
        
        # 模拟下载过程
        success = random.random() > 0.3  # 70%的下载成功率
        
        if success:
            # 模拟一些数据
            sample_data = {
                "training_plans": [
                    {
                        "name": "高级防身术训练",
                        "date": datetime.now().date().toString(),
                        "duration": 60,
                        "exercises": ["直拳训练", "踢腿训练", "模拟实战"]
                    }
                ],
                "progress": {
                    "last_week": 12,
                    "last_month": 42,
                    "total_score": 87
                }
            }
            
            return True, "数据下载成功", sample_data.get(data_type, {})
        else:
            return False, "下载失败，请重试", None


# 增强的姿势检测器
class EnhancedPoseDetector:
    def __init__(self):
        self.current_pose = None
        self.pose_history = []
        self.ai_service = AIAnalysisService()
        
        # 预定义的姿势数据
        self.poses = {
            "punch": {
                "name": "直拳",
                "description": "基本直拳攻击技术",
                "difficulty": "初级",
                "muscles": ["三角肌", "胸大肌", "三头肌"],
                "common_mistakes": [
                    "肘部过度外展",
                    "肩膀未完全伸展",
                    "身体重心不稳"
                ]
            },
            "kick": {
                "name": "前踢",
                "description": "向前踢击技术",
                "difficulty": "中级",
                "muscles": ["股四头肌", "髂腰肌", "腹肌"],
                "common_mistakes": [
                    "膝盖未抬高足够",
                    "踢击时失去平衡",
                    "脚部位置不正确"
                ]
            },
            "block": {
                "name": "上格挡",
                "description": "防御上方攻击的技术",
                "difficulty": "初级",
                "muscles": ["三角肌", "斜方肌", "二头肌"],
                "common_mistakes": [
                    "手臂角度不正确",
                    "格挡位置太高或太低",
                    "身体未保持稳定"
                ]
            }
        }
    
    def detect_pose(self, pose_name):
        """检测姿势并返回结果"""
        if pose_name not in self.poses:
            return False, "未知姿势", {}
        
        # 模拟姿势检测
        success = random.random() > 0.2  # 80%的成功率
        
        if success:
            # 生成模拟的姿势数据
            pose_data = {
                "angles": {
                    "elbow": random.uniform(160, 190),
                    "shoulder": random.uniform(40, 50),
                    "wrist": random.uniform(-10, 10)
                },
                "timing": random.uniform(0.8, 1.5),
                "power": random.uniform(70, 95)
            }
            
            # 使用AI分析姿势
            analysis = self.ai_service.analyze_pose(pose_data, pose_name)
            
            # 记录历史
            self.pose_history.append({
                "pose": pose_name,
                "timestamp": datetime.now(),
                "data": pose_data,
                "analysis": analysis
            })
            
            return True, "姿势检测成功", {
                "pose_info": self.poses[pose_name],
                "pose_data": pose_data,
                "analysis": analysis
            }
        else:
            return False, "无法检测到有效姿势", {}


# 增强的紧急警报系统
class EnhancedEmergencyAlert:
    def __init__(self):
        self.is_active = False
        self.alert_sound = "emergency_alert.wav"
        self.contacts = []
        self.location = "未知位置"
        self.alert_history = []
        
        # 创建网络管理器用于发送警报
        self.network_manager = QNetworkAccessManager()
    
    def update_location(self, location):
        """更新当前位置"""
        self.location = location
    
    def add_contact(self, name, phone, relation):
        """添加紧急联系人"""
        self.contacts.append({
            "name": name,
            "phone": phone,
            "relation": relation,
            "notified": False
        })
    
    def activate(self, reason="手动激活"):
        """激活紧急警报"""
        self.is_active = True
        activation_time = datetime.now()
        
        # 模拟发送警报给联系人
        notifications_sent = 0
        for contact in self.contacts:
            # 这里模拟发送通知
            contact["notified"] = True
            contact["notification_time"] = activation_time
            notifications_sent += 1
        
        # 记录警报历史
        self.alert_history.append({
            "time": activation_time,
            "reason": reason,
            "location": self.location,
            "notifications_sent": notifications_sent,
            "status": "active"
        })
        
        # 播放警报声
        QSound.play(self.alert_sound)
        
        return f"警报已激活！已通知{notifications_sent}位联系人。位置：{self.location}"
    
    def deactivate(self):
        """解除警报"""
        if self.is_active:
            self.is_active = False
            deactivation_time = datetime.now()
            
            # 更新最近的警报记录
            if self.alert_history:
                self.alert_history[-1]["status"] = "resolved"
                self.alert_history[-1]["resolved_time"] = deactivation_time
            
            return "警报已解除"
        return "没有活动的警报"
    
    def simulate_emergency(self, emergency_type):
        """模拟紧急情况"""
        emergencies = {
            "followed": {"name": "被跟踪", "level": "high"},
            "harassment": {"name": "被骚扰", "level": "medium"},
            "threat": {"name": "受到威胁", "level": "high"},
            "other": {"name": "其他紧急情况", "level": "unknown"}
        }
        
        if emergency_type in emergencies:
            emergency = emergencies[emergency_type]
            return self.activate(f"模拟紧急情况: {emergency['name']}")
        
        return self.activate("模拟紧急情况")


# 人体姿势可视化组件
class PoseVisualizationWidget(QGraphicsView):
    def __init__(self):
        super().__init__()
        self.scene = QGraphicsScene()
        self.setScene(self.scene)
        self.setRenderHint(QPainter.Antialiasing)
        
        # 设置背景
        self.setBackgroundBrush(QBrush(QColor(240, 240, 240)))
        
        # 人体关键点
        self.key_points = {
            "head": QPoint(0, -80),
            "shoulder_left": QPoint(-30, -40),
            "shoulder_right": QPoint(30, -40),
            "elbow_left": QPoint(-50, -20),
            "elbow_right": QPoint(50, -20),
            "wrist_left": QPoint(-60, 0),
            "wrist_right": QPoint(60, 0),
            "hip_left": QPoint(-20, 20),
            "hip_right": QPoint(20, 20),
            "knee_left": QPoint(-25, 60),
            "knee_right": QPoint(25, 60),
            "ankle_left": QPoint(-25, 100),
            "ankle_right": QPoint(25, 100)
        }
        
        # 骨骼连接
        self.bones = [
            ("head", "shoulder_left"),
            ("head", "shoulder_right"),
            ("shoulder_left", "elbow_left"),
            ("shoulder_right", "elbow_right"),
            ("elbow_left", "wrist_left"),
            ("elbow_right", "wrist_right"),
            ("shoulder_left", "hip_left"),
            ("shoulder_right", "hip_right"),
            ("hip_left", "knee_left"),
            ("hip_right", "knee_right"),
            ("knee_left", "ankle_left"),
            ("knee_right", "ankle_right"),
            ("hip_left", "hip_right")
        ]
        
        self.draw_skeleton()
    
    def draw_skeleton(self):
        """绘制人体骨架"""
        self.scene.clear()
        
        # 绘制骨骼
        for bone in self.bones:
            start_point = self.key_points[bone[0]]
            end_point = self.key_points[bone[1]]
            
            line = QGraphicsLineItem(start_point.x(), start_point.y(), 
                                    end_point.x(), end_point.y())
            line.setPen(QPen(QColor(0, 0, 0), 3))
            self.scene.addItem(line)
        
        # 绘制关节点
        for point_name, point in self.key_points.items():
            ellipse = QGraphicsEllipseItem(point.x() - 5, point.y() - 5, 10, 10)
            
            # 根据点类型设置颜色
            if "head" in point_name:
                ellipse.setBrush(QBrush(QColor(255, 200, 200)))
            elif "left" in point_name:
                ellipse.setBrush(QBrush(QColor(200, 200, 255)))
            elif "right" in point_name:
                ellipse.setBrush(QBrush(QColor(200, 255, 200)))
            else:
                ellipse.setBrush(QBrush(QColor(255, 255, 200)))
                
            self.scene.addItem(ellipse)
            
            # 添加文本标签
            text = QGraphicsTextItem(point_name.replace("_", "\n"))
            text.setPos(point.x() - 15, point.y() - 20)
            text.setScale(0.7)
            self.scene.addItem(text)
    
    def update_pose(self, pose_data):
        """根据姿势数据更新可视化"""
        # 这里可以根据实际的姿势数据更新关键点位置
        # 目前使用静态数据作为示例
        
        # 模拟一些变化
        for point_name in self.key_points:
            if "left" in point_name:
                new_x = self.key_points[point_name].x() - random.randint(0, 10)
                new_y = self.key_points[point_name].y() + random.randint(-5, 5)
                self.key_points[point_name] = QPoint(new_x, new_y)
            elif "right" in point_name:
                new_x = self.key_points[point_name].x() + random.randint(0, 10)
                new_y = self.key_points[point_name].y() + random.randint(-5, 5)
                self.key_points[point_name] = QPoint(new_x, new_y)
        
        self.draw_skeleton()


# 增强的姿势训练组件
class EnhancedPoseTrainingWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.pose_detector = EnhancedPoseDetector()
        self.current_technique = None
        self.training_history = []
        self.init_ui()
    
    def init_ui(self):
        layout = QHBoxLayout()
        
        # 左侧 - 技术选择和说明
        left_panel = QWidget()
        left_layout = QVBoxLayout()
        
        # 技术选择
        technique_group = QGroupBox("选择训练技术")
        technique_layout = QVBoxLayout()
        
        self.technique_combo = QComboBox()
        for tech_id, tech_info in self.pose_detector.poses.items():
            self.technique_combo.addItem(tech_info["name"], tech_id)
        technique_layout.addWidget(self.technique_combo)
        
        # 技术详情
        self.technique_details = QTextEdit()
        self.technique_details.setReadOnly(True)
        technique_layout.addWidget(self.technique_details)
        
        technique_group.setLayout(technique_layout)
        left_layout.addWidget(technique_group)
        
        # 训练控制
        control_group = QGroupBox("训练控制")
        control_layout = QVBoxLayout()
        
        self.start_training_btn = QPushButton("开始训练")
        self.analyze_btn = QPushButton("分析姿势")
        self.analyze_btn.setEnabled(False)
        
        control_layout.addWidget(self.start_training_btn)
        control_layout.addWidget(self.analyze_btn)
        
        control_group.setLayout(control_layout)
        left_layout.addWidget(control_group)
        
        left_panel.setLayout(left_layout)
        left_panel.setMaximumWidth(300)
        
        # 右侧 - 姿势可视化和反馈
        right_panel = QWidget()
        right_layout = QVBoxLayout()
        
        # 姿势可视化
        visualization_group = QGroupBox("姿势可视化")
        visualization_layout = QVBoxLayout()
        
        self.pose_visualization = PoseVisualizationWidget()
        self.pose_visualization.setMinimumSize(400, 500)
        visualization_layout.addWidget(self.pose_visualization)
        
        visualization_group.setLayout(visualization_layout)
        right_layout.addWidget(visualization_group)
        
        # 训练反馈
        feedback_group = QGroupBox("训练反馈")
        feedback_layout = QVBoxLayout()
        
        self.feedback_label = QLabel("请选择技术并开始训练")
        self.feedback_label.setWordWrap(True)
        self.feedback_label.setAlignment(Qt.AlignCenter)
        self.feedback_label.setStyleSheet("min-height: 100px; background-color: #f0f0f0; padding: 10px;")
        feedback_layout.addWidget(self.feedback_label)
        
        # 分数显示
        self.score_bar = QProgressBar()
        self.score_bar.setFormat("得分: %p%")
        feedback_layout.addWidget(self.score_bar)
        
        # 详细指标
        metrics_group = QGroupBox("详细指标")
        metrics_layout = QGridLayout()
        
        self.power_label = QLabel("力量: N/A")
        self.speed_label = QLabel("速度: N/A")
        self.accuracy_label = QLabel("准确度: N/A")
        self.balance_label = QLabel("平衡性: N/A")
        
        metrics_layout.addWidget(self.power_label, 0, 0)
        metrics_layout.addWidget(self.speed_label, 0, 1)
        metrics_layout.addWidget(self.accuracy_label, 1, 0)
        metrics_layout.addWidget(self.balance_label, 1, 1)
        
        metrics_group.setLayout(metrics_layout)
        feedback_layout.addWidget(metrics_group)
        
        feedback_group.setLayout(feedback_layout)
        right_layout.addWidget(feedback_group)
        
        right_panel.setLayout(right_layout)
        
        # 添加到主布局
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([300, 700])
        
        layout.addWidget(splitter)
        self.setLayout(layout)
        
        # 连接信号
        self.technique_combo.currentIndexChanged.connect(self.update_technique_details)
        self.start_training_btn.clicked.connect(self.start_training)
        self.analyze_btn.clicked.connect(self.analyze_pose)
        
        # 初始化
        self.update_technique_details(0)
    
    def update_technique_details(self, index):
        """更新技术详情"""
        tech_id = self.technique_combo.currentData()
        tech_info = self.pose_detector.poses[tech_id]
        
        details_text = f"""
        <h3>{tech_info['name']}</h3>
        <p><b>描述:</b> {tech_info['description']}</p>
        <p><b>难度:</b> {tech_info['difficulty']}</p>
        <p><b>主要肌肉群:</b> {', '.join(tech_info['muscles'])}</p>
        <p><b>常见错误:</b></p>
        <ul>
        """
        
        for mistake in tech_info['common_mistakes']:
            details_text += f"<li>{mistake}</li>"
        
        details_text += "</ul>"
        
        self.technique_details.setHtml(details_text)
        self.current_technique = tech_id
    
    def start_training(self):
        """开始训练"""
        self.feedback_label.setText("准备检测姿势...")
        self.feedback_label.setStyleSheet("color: blue; background-color: #f0f0f0; padding: 10px;")
        self.analyze_btn.setEnabled(True)
        
        # 重置指标
        self.power_label.setText("力量: 检测中...")
        self.speed_label.setText("速度: 检测中...")
        self.accuracy_label.setText("准确度: 检测中...")
        self.balance_label.setText("平衡性: 检测中...")
        self.score_bar.setValue(0)
    
    def analyze_pose(self):
        """分析当前姿势"""
        if not self.current_technique:
            return
        
        success, message, result = self.pose_detector.detect_pose(self.current_technique)
        
        if success:
            # 更新可视化
            self.pose_visualization.update_pose(result["pose_data"])
            
            # 显示分析结果
            analysis = result["analysis"]
            self.score_bar.setValue(int(analysis["score"]))
            
            feedback_text = f"<h3>分析结果: {analysis['score']}分</h3>"
            for fb in analysis["feedback"]:
                feedback_text += f"<p>• {fb}</p>"
            
            self.feedback_label.setText(feedback_text)
            
            if analysis["score"] >= 90:
                self.feedback_label.setStyleSheet("color: green; background-color: #f0f0f0; padding: 10px;")
            elif analysis["score"] >= 70:
                self.feedback_label.setStyleSheet("color: orange; background-color: #f0f0f0; padding: 10px;")
            else:
                self.feedback_label.setStyleSheet("color: red; background-color: #f0f0f0; padding: 10px;")
            
            # 更新详细指标
            details = analysis["details"]
            self.power_label.setText(f"力量: {details['power']:.1f}%")
            self.speed_label.setText(f"速度: {details['speed']:.1f}%")
            self.accuracy_label.setText(f"准确度: {details['accuracy']:.1f}%")
            self.balance_label.setText(f"平衡性: {details['balance']:.1f}%")
            
            # 记录训练历史
            self.training_history.append({
                "technique": self.current_technique,
                "timestamp": datetime.now(),
                "score": analysis["score"],
                "details": details
            })
        else:
            self.feedback_label.setText(f"错误: {message}")
            self.feedback_label.setStyleSheet("color: red; background-color: #f0f0f0; padding: 10px;")


# 增强的模拟训练组件
class EnhancedSimulationTrainingWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.scenarios = self.load_scenarios()
        self.current_scenario = None
        self.current_step = 0
        self.score = 0
        self.init_ui()
    
    def load_scenarios(self):
        """加载训练场景"""
        return [
            {
                "id": "night_walk",
                "name": "夜间行走",
                "difficulty": "中等",
                "description": "模拟夜间独自行走时遇到陌生人的情况",
                "steps": [
                    {
                        "description": "你晚上独自回家，注意到有人跟在后面。",
                        "options": [
                            {"text": "加快步伐", "result": "你加快了步伐，但对方也加快了速度。"},
                            {"text": "改变路线", "result": "你转向更亮的主路，对方仍然跟着。"},
                            {"text": "打电话给朋友", "result": "你假装打电话，对方稍微拉开了距离。"}
                        ],
                        "correct_option": 2,
                        "score": 10
                    },
                    {
                        "description": "对方加快脚步接近你，并喊你停下。",
                        "options": [
                            {"text": "停下来面对对方", "result": "你停下来，对方迅速接近。"},
                            {"text": "开始奔跑", "result": "你开始奔跑，对方追赶你。"},
                            {"text": "大声呼救并准备防御", "result": "你大声呼救，并采取防御姿势，对方犹豫了。"}
                        ],
                        "correct_option": 2,
                        "score": 15
                    },
                    {
                        "description": "对方继续接近，似乎有不良意图。",
                        "options": [
                            {"text": "尝试谈判", "result": "你试图谈判，但对方不理会。"},
                            {"text": "使用防身喷雾", "result": "你使用防身喷雾，对方暂时失去行动能力。"},
                            {"text": "进行物理防御", "result": "你使用防身术技巧阻止对方接近。"}
                        ],
                        "correct_option": 1,
                        "score": 20
                    }
                ]
            },
            {
                "id": "public_transport",
                "name": "公共交通",
                "difficulty": "简单",
                "description": "模拟在公共交通上遇到骚扰的情况",
                "steps": [
                    {
                        "description": "在拥挤的地铁上，有人不适当地触碰你。",
                        "options": [
                            {"text": "忽略并移开", "result": "你移开了，但对方继续靠近。"},
                            {"text": "大声指责", "result": "你大声指责，吸引了周围人的注意。"},
                            {"text": "通知司机/保安", "result": "你通知了工作人员，对方被制止。"}
                        ],
                        "correct_option": 2,
                        "score": 10
                    }
                ]
            },
            {
                "id": "parking_lot",
                "name": "停车场",
                "difficulty": "困难",
                "description": "模拟在停车场遇到潜在危险的情况",
                "steps": [
                    {
                        "description": "在停车场，有陌生人主动提出帮助你拿行李。",
                        "options": [
                            {"text": "礼貌拒绝", "result": "你礼貌拒绝，但对方坚持要帮忙。"},
                            {"text": "接受帮助", "result": "你接受了帮助，对方借机接近你。"},
                            {"text": "坚决拒绝并保持距离", "result": "你坚决拒绝并保持安全距离。"}
                        ],
                        "correct_option": 2,
                        "score": 10
                    }
                ]
            }
        ]
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 场景选择
        scenario_group = QGroupBox("选择训练场景")
        scenario_layout = QVBoxLayout()
        
        self.scenario_combo = QComboBox()
        for scenario in self.scenarios:
            self.scenario_combo.addItem(f"{scenario['name']} ({scenario['difficulty']})", scenario["id"])
        scenario_layout.addWidget(self.scenario_combo)
        
        self.scenario_description = QLabel()
        self.scenario_description.setWordWrap(True)
        self.scenario_description.setStyleSheet("background-color: #f0f0f0; padding: 10px;")
        scenario_layout.addWidget(self.scenario_description)
        
        self.start_scenario_btn = QPushButton("开始模拟训练")
        scenario_layout.addWidget(self.start_scenario_btn)
        
        scenario_group.setLayout(scenario_layout)
        layout.addWidget(scenario_group)
        
        # 训练显示区域
        training_group = QGroupBox("模拟训练")
        training_layout = QVBoxLayout()
        
        self.training_display = QTextEdit()
        self.training_display.setReadOnly(True)
        training_layout.addWidget(self.training_display)
        
        # 选项按钮
        self.option_buttons = []
        options_layout = QHBoxLayout()
        for i in range(3):
            btn = QPushButton()
            btn.setVisible(False)
            btn.clicked.connect(lambda checked, idx=i: self.handle_choice(idx))
            self.option_buttons.append(btn)
            options_layout.addWidget(btn)
        
        training_layout.addLayout(options_layout)
        
        # 分数显示
        score_layout = QHBoxLayout()
        score_layout.addWidget(QLabel("当前分数:"))
        self.score_label = QLabel("0")
        score_layout.addWidget(self.score_label)
        score_layout.addStretch()
        
        training_layout.addLayout(score_layout)
        training_group.setLayout(training_layout)
        layout.addWidget(training_group)
        
        self.setLayout(layout)
        
        # 连接信号
        self.scenario_combo.currentIndexChanged.connect(self.update_scenario_description)
        self.start_scenario_btn.clicked.connect(self.start_scenario)
        
        # 初始化
        self.update_scenario_description(0)
    
    def update_scenario_description(self, index):
        """更新场景描述"""
        if 0 <= index < len(self.scenarios):
            scenario_id = self.scenario_combo.currentData()
            scenario = next((s for s in self.scenarios if s["id"] == scenario_id), None)
            if scenario:
                self.scenario_description.setText(scenario['description'])
    
    def start_scenario(self):
        """开始场景训练"""
        scenario_id = self.scenario_combo.currentData()
        self.current_scenario = next((s for s in self.scenarios if s["id"] == scenario_id), None)
        
        if not self.current_scenario:
            return
        
        self.current_step = 0
        self.score = 0
        self.update_score()
        self.show_step(0)
    
    def show_step(self, step_index):
        """显示当前步骤"""
        if not self.current_scenario or step_index >= len(self.current_scenario["steps"]):
            self.end_scenario()
            return
        
        step = self.current_scenario["steps"][step_index]
        self.training_display.setText(step["description"])
        
        # 设置选项按钮
        for i, option in enumerate(step["options"]):
            if i < len(self.option_buttons):
                self.option_buttons[i].setText(option["text"])
                self.option_buttons[i].setVisible(True)
    
    def handle_choice(self, choice_index):
        """处理用户选择"""
        if not self.current_scenario or self.current_step >= len(self.current_scenario["steps"]):
            return
        
        step = self.current_scenario["steps"][self.current_step]
        
        if choice_index < len(step["options"]):
            result = step["options"][choice_index]["result"]
            self.training_display.append(f"\n\n你的选择: {result}")
            
            # 检查是否正确选择
            if choice_index == step["correct_option"]:
                self.score += step["score"]
                self.training_display.append(f"\n✓ 正确选择! +{step['score']}分")
            else:
                self.training_display.append(f"\n✗ 这不是最佳选择")
            
            self.update_score()
            
            # 隐藏选项按钮
            for btn in self.option_buttons:
                btn.setVisible(False)
            
            # 下一步
            self.current_step += 1
            QTimer.singleShot(2000, lambda: self.show_step(self.current_step))
    
    def update_score(self):
        """更新分数显示"""
        self.score_label.setText(str(self.score))
    
    def end_scenario(self):
        """结束场景训练"""
        total_possible = sum(step["score"] for step in self.current_scenario["steps"])
        percentage = (self.score / total_possible) * 100 if total_possible > 0 else 0
        
        self.training_display.append(f"\n\n=== 训练结束 ===")
        self.training_display.append(f"最终得分: {self.score}/{total_possible} ({percentage:.1f}%)")
        
        if percentage >= 80:
            self.training_display.append("优秀! 你做出了大多数正确决定。")
        elif percentage >= 60:
            self.training_display.append("良好! 但还有一些改进空间。")
        else:
            self.training_display.append("需要更多练习。考虑复习防身术基础知识。")


# 增强的紧急联系人组件
class EnhancedEmergencyContactWidget(QWidget):
    def __init__(self, database, emergency_alert):
        super().__init__()
        self.database = database
        self.emergency_alert = emergency_alert
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 标题
        title = QLabel("紧急联系人 & 警报系统")
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont("Arial", 16, QFont.Bold))
        layout.addWidget(title)
        
        # 联系人管理
        contact_group = QGroupBox("紧急联系人管理")
        contact_layout = QGridLayout()
        
        contact_layout.addWidget(QLabel("姓名:"), 0, 0)
        self.contact_name_edit = QLineEdit()
        contact_layout.addWidget(self.contact_name_edit, 0, 1)
        
        contact_layout.addWidget(QLabel("电话:"), 1, 0)
        self.contact_phone_edit = QLineEdit()
        contact_layout.addWidget(self.contact_phone_edit, 1, 1)
        
        contact_layout.addWidget(QLabel("关系:"), 2, 0)
        self.contact_relation_edit = QLineEdit()
        contact_layout.addWidget(self.contact_relation_edit, 2, 1)
        
        self.add_contact_btn = QPushButton("添加联系人")
        contact_layout.addWidget(self.add_contact_btn, 3, 1)
        
        contact_group.setLayout(contact_layout)
        layout.addWidget(contact_group)
        
        # 联系人列表
        contact_list_group = QGroupBox("紧急联系人列表")
        contact_list_layout = QVBoxLayout()
        
        self.contact_list = QListWidget()
        contact_list_layout.addWidget(self.contact_list)
        
        self.delete_contact_btn = QPushButton("删除选中联系人")
        contact_list_layout.addWidget(self.delete_contact_btn)
        
        contact_list_group.setLayout(contact_list_layout)
        layout.addWidget(contact_list_group)
        
        # 紧急警报部分
        emergency_group = QGroupBox("紧急警报")
        emergency_layout = QVBoxLayout()
        
        # 模拟紧急情况按钮
        simulate_layout = QHBoxLayout()
        simulate_layout.addWidget(QLabel("模拟紧急情况:"))
        
        self.emergency_combo = QComboBox()
        self.emergency_combo.addItems(["被跟踪", "被骚扰", "受到威胁", "其他"])
        simulate_layout.addWidget(self.emergency_combo)
        
        self.simulate_btn = QPushButton("模拟")
        simulate_layout.addWidget(self.simulate_btn)
        
        emergency_layout.addLayout(simulate_layout)
        
        # 真实紧急按钮
        self.real_emergency_btn = QPushButton("真实紧急求助!")
        self.real_emergency_btn.setStyleSheet("background-color: red; color: white; font-weight: bold; font-size: 18px;")
        self.real_emergency_btn.setMinimumHeight(60)
        emergency_layout.addWidget(self.real_emergency_btn)
        
        # 警报状态
        self.alert_status = QLabel("警报状态: 未激活")
        self.alert_status.setAlignment(Qt.AlignCenter)
        self.alert_status.setStyleSheet("padding: 10px; font-weight: bold;")
        emergency_layout.addWidget(self.alert_status)
        
        emergency_group.setLayout(emergency_layout)
        layout.addWidget(emergency_group)
        
        # 警报历史
        history_group = QGroupBox("警报历史")
        history_layout = QVBoxLayout()
        
        self.alert_history = QListWidget()
        history_layout.addWidget(self.alert_history)
        
        history_group.setLayout(history_layout)
        layout.addWidget(history_group)
        
        self.setLayout(layout)
        
        # 连接信号
        self.add_contact_btn.clicked.connect(self.add_contact)
        self.delete_contact_btn.clicked.connect(self.delete_contact)
        self.simulate_btn.clicked.connect(self.simulate_emergency)
        self.real_emergency_btn.clicked.connect(self.trigger_real_emergency)
        
        # 加载联系人
        self.load_contacts()
        self.load_alert_history()
    
    def load_contacts(self):
        """加载联系人"""
        self.contact_list.clear()
        for contact in self.database.emergency_contacts:
            item_text = f"{contact['name']} ({contact['relation']}): {contact['phone']}"
            self.contact_list.addItem(item_text)
    
    def load_alert_history(self):
        """加载警报历史"""
        self.alert_history.clear()
        for alert in self.emergency_alert.alert_history:
            status_text = "激活" if alert["status"] == "active" else "已解决"
            item_text = f"{alert['time'].toString()} - {alert['reason']} ({status_text})"
            self.alert_history.addItem(item_text)
    
    def add_contact(self):
        """添加联系人"""
        name = self.contact_name_edit.text()
        phone = self.contact_phone_edit.text()
        relation = self.contact_relation_edit.text()
        
        if not name or not phone:
            QMessageBox.warning(self, "警告", "请输入姓名和电话")
            return
        
        contact = {
            "name": name,
            "phone": phone,
            "relation": relation
        }
        
        self.database.add_emergency_contact(contact)
        self.emergency_alert.add_contact(name, phone, relation)
        self.load_contacts()
        
        # 清空输入框
        self.contact_name_edit.clear()
        self.contact_phone_edit.clear()
        self.contact_relation_edit.clear()
    
    def delete_contact(self):
        """删除联系人"""
        current_row = self.contact_list.currentRow()
        if current_row < 0:
            return
        
        self.database.emergency_contacts.pop(current_row)
        self.database.save_data()
        self.load_contacts()
    
    def simulate_emergency(self):
        """模拟紧急情况"""
        emergency_type = self.emergency_combo.currentText().lower()
        if emergency_type == "被跟踪":
            result = self.emergency_alert.simulate_emergency("followed")
        elif emergency_type == "被骚扰":
            result = self.emergency_alert.simulate_emergency("harassment")
        elif emergency_type == "受到威胁":
            result = self.emergency_alert.simulate_emergency("threat")
        else:
            result = self.emergency_alert.simulate_emergency("other")
        
        self.alert_status.setText("警报状态: 模拟激活中")
        self.alert_status.setStyleSheet("color: orange; padding: 10px; font-weight: bold;")
        self.load_alert_history()
        
        QMessageBox.information(self, "模拟紧急情况", result)
        
        # 5秒后自动解除模拟警报
        QTimer.singleShot(5000, self.deactivate_simulated_alert)
    
    def deactivate_simulated_alert(self):
        """解除模拟警报"""
        result = self.emergency_alert.deactivate()
        self.alert_status.setText("警报状态: 未激活")
        self.alert_status.setStyleSheet("color: green; padding: 10px; font-weight: bold;")
        self.load_alert_history()
        
        QMessageBox.information(self, "模拟结束", result)
    
    def trigger_real_emergency(self):
        """触发真实紧急警报"""
        if not self.database.emergency_contacts:
            QMessageBox.warning(self, "警告", "请先添加紧急联系人")
            return
        
        result = self.emergency_alert.activate()
        self.alert_status.setText("警报状态: 已激活!")
        self.alert_status.setStyleSheet("color: red; padding: 10px; font-weight: bold;")
        self.load_alert_history()
        
        QMessageBox.information(self, "紧急求助", result)


# 统计和进度跟踪组件
class StatisticsWidget(QWidget):
    def __init__(self, database):
        super().__init__()
        self.database = database
        self.cloud_service = CloudSyncService()
        self.init_ui()
        self.load_statistics()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 标题
        title = QLabel("训练统计和进度")
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont("Arial", 16, QFont.Bold))
        layout.addWidget(title)
        
        # 云同步按钮
        sync_layout = QHBoxLayout()
        self.sync_btn = QPushButton("同步到云端")
        self.sync_status = QLabel("就绪")
        sync_layout.addWidget(self.sync_btn)
        sync_layout.addWidget(self.sync_status)
        sync_layout.addStretch()
        
        layout.addLayout(sync_layout)
        
        # 统计卡片
        stats_grid = QGridLayout()
        
        # 总训练时间
        self.total_time_card = self.create_stat_card("总训练时间", "0 小时", "#4CAF50")
        stats_grid.addWidget(self.total_time_card, 0, 0)
        
        # 掌握技术数
        self.techniques_card = self.create_stat_card("掌握技术", "0", "#2196F3")
        stats_grid.addWidget(self.techniques_card, 0, 1)
        
        # 平均得分
        self.avg_score_card = self.create_stat_card("平均得分", "0%", "#FF9800")
        stats_grid.addWidget(self.avg_score_card, 1, 0)
        
        # 训练次数
        self.sessions_card = self.create_stat_card("训练次数", "0", "#F44336")
        stats_grid.addWidget(self.sessions_card, 1, 1)
        
        layout.addLayout(stats_grid)
        
        # 详细统计表格
        table_group = QGroupBox("详细统计")
        table_layout = QVBoxLayout()
        
        self.stats_table = QTableWidget()
        self.stats_table.setColumnCount(4)
        self.stats_table.setHorizontalHeaderLabels(["日期", "技术", "得分", "持续时间"])
        self.stats_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        table_layout.addWidget(self.stats_table)
        table_group.setLayout(table_layout)
        layout.addWidget(table_group)
        
        self.setLayout(layout)
        
        # 连接信号
        self.sync_btn.clicked.connect(self.sync_to_cloud)
    
    def create_stat_card(self, title, value, color):
        """创建统计卡片"""
        card = QFrame()
        card.setFrameStyle(QFrame.StyledPanel)
        card.setStyleSheet(f"background-color: {color}; color: white; border-radius: 5px;")
        card.setMinimumHeight(100)
        
        layout = QVBoxLayout()
        
        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        
        value_label = QLabel(value)
        value_label.setAlignment(Qt.AlignCenter)
        value_label.setStyleSheet("font-size: 24px; font-weight: bold;")
        
        layout.addWidget(title_label)
        layout.addWidget(value_label)
        
        card.setLayout(layout)
        return card
    
    def load_statistics(self):
        """加载统计数据"""
        # 模拟一些统计数据
        total_time = 12.5
        techniques = 8
        avg_score = 82
        sessions = 15
        
        # 更新卡片
        self.total_time_card.layout().itemAt(1).widget().setText(f"{total_time} 小时")
        self.techniques_card.layout().itemAt(1).widget().setText(f"{techniques}")
        self.avg_score_card.layout().itemAt(1).widget().setText(f"{avg_score}%")
        self.sessions_card.layout().itemAt(1).widget().setText(f"{sessions}")
        
        # 更新表格
        self.stats_table.setRowCount(5)
        sample_data = [
            ["2023-10-15", "直拳", "85%", "30分钟"],
            ["2023-10-16", "前踢", "78%", "45分钟"],
            ["2023-10-18", "格挡", "92%", "35分钟"],
            ["2023-10-20", "组合技巧", "88%", "60分钟"],
            ["2023-10-22", "模拟训练", "95%", "40分钟"]
        ]
        
        for row, data in enumerate(sample_data):
            for col, value in enumerate(data):
                self.stats_table.setItem(row, col, QTableWidgetItem(value))
    
    def sync_to_cloud(self):
        """同步数据到云端"""
        self.sync_status.setText("同步中...")
        
        # 模拟同步过程
        success, message = self.cloud_service.upload_data("statistics", {})
        
        if success:
            self.sync_status.setText("同步成功")
            QMessageBox.information(self, "同步成功", "数据已成功同步到云端")
        else:
            self.sync_status.setText("同步失败")
            QMessageBox.warning(self, "同步失败", message)


# 设置组件
class SettingsWidget(QWidget):
    def __init__(self, database):
        super().__init__()
        self.database = database
        self.settings = QSettings("SelfDefenseApp", "Settings")
        self.init_ui()
        self.load_settings()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 标题
        title = QLabel("系统设置")
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont("Arial", 16, QFont.Bold))
        layout.addWidget(title)
        
        # 常规设置
        general_group = QGroupBox("常规设置")
        general_layout = QFormLayout()
        
        self.auto_save = QCheckBox("自动保存进度")
        general_layout.addRow("自动保存:", self.auto_save)
        
        self.cloud_sync = QCheckBox("启用云同步")
        general_layout.addRow("云同步:", self.cloud_sync)
        
        self.alert_sound = QComboBox()
        self.alert_sound.addItems(["默认警报", "响亮警报", "静音"])
        general_layout.addRow("警报声音:", self.alert_sound)
        
        general_group.setLayout(general_layout)
        layout.addWidget(general_group)
        
        # 训练设置
        training_group = QGroupBox("训练设置")
        training_layout = QFormLayout()
        
        self.difficulty = QComboBox()
        self.difficulty.addItems(["初级", "中级", "高级", "专家"])
        training_layout.addRow("难度级别:", self.difficulty)
        
        self.feedback_level = QComboBox()
        self.feedback_level.addItems(["简洁", "标准", "详细"])
        training_layout.addRow("反馈级别:", self.feedback_level)
        
        self.voice_guidance = QCheckBox("启用语音指导")
        training_layout.addRow("语音指导:", self.voice_guidance)
        
        training_group.setLayout(training_layout)
        layout.addWidget(training_group)
        
        # 紧急设置
        emergency_group = QGroupBox("紧急设置")
        emergency_layout = QFormLayout()
        
        self.auto_alert = QCheckBox("危险时自动警报")
        emergency_layout.addRow("自动警报:", self.auto_alert)
        
        self.alert_delay = QSpinBox()
        self.alert_delay.setRange(0, 60)
        self.alert_delay.setSuffix(" 秒")
        emergency_layout.addRow("警报延迟:", self.alert_delay)
        
        self.location_sharing = QCheckBox("启用位置共享")
        emergency_layout.addRow("位置共享:", self.location_sharing)
        
        emergency_group.setLayout(emergency_layout)
        layout.addWidget(emergency_group)
        
        # 按钮
        button_layout = QHBoxLayout()
        self.save_btn = QPushButton("保存设置")
        self.reset_btn = QPushButton("恢复默认")
        
        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.reset_btn)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        layout.addStretch()
        
        self.setLayout(layout)
        
        # 连接信号
        self.save_btn.clicked.connect(self.save_settings)
        self.reset_btn.clicked.connect(self.reset_settings)
    
    def load_settings(self):
        """加载设置"""
        self.auto_save.setChecked(self.settings.value("auto_save", True, type=bool))
        self.cloud_sync.setChecked(self.settings.value("cloud_sync", True, type=bool))
        self.alert_sound.setCurrentText(self.settings.value("alert_sound", "默认警报"))
        self.difficulty.setCurrentText(self.settings.value("difficulty", "中级"))
        self.feedback_level.setCurrentText(self.settings.value("feedback_level", "标准"))
        self.voice_guidance.setChecked(self.settings.value("voice_guidance", False, type=bool))
        self.auto_alert.setChecked(self.settings.value("auto_alert", False, type=bool))
        self.alert_delay.setValue(self.settings.value("alert_delay", 10, type=int))
        self.location_sharing.setChecked(self.settings.value("location_sharing", True, type=bool))
    
    def save_settings(self):
        """保存设置"""
        self.settings.setValue("auto_save", self.auto_save.isChecked())
        self.settings.setValue("cloud_sync", self.cloud_sync.isChecked())
        self.settings.setValue("alert_sound", self.alert_sound.currentText())
        self.settings.setValue("difficulty", self.difficulty.currentText())
        self.settings.setValue("feedback_level", self.feedback_level.currentText())
        self.settings.setValue("voice_guidance", self.voice_guidance.isChecked())
        self.settings.setValue("auto_alert", self.auto_alert.isChecked())
        self.settings.setValue("alert_delay", self.alert_delay.value())
        self.settings.setValue("location_sharing", self.location_sharing.isChecked())
        
        QMessageBox.information(self, "设置已保存", "您的设置已成功保存")
    
    def reset_settings(self):
        """恢复默认设置"""
        reply = QMessageBox.question(self, "确认重置", 
                                    "确定要恢复默认设置吗？",
                                    QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.settings.clear()
            self.load_settings()
            QMessageBox.information(self, "设置已重置", "已恢复默认设置")


# 主窗口
class EnhancedSelfDefenseMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.database = SelfDefenseDatabase()
        self.database.load_data()
        self.emergency_alert = EnhancedEmergencyAlert()
        
        self.init_ui()
        self.setup_tray_icon()
    
    def init_ui(self):
        self.setWindowTitle("高级防身术训练系统")
        self.setGeometry(100, 100, 1200, 800)
        
        # 创建中心部件和主布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # 创建标签页
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)
        
        # 添加各个功能标签页
        self.pose_training_tab = EnhancedPoseTrainingWidget()
        self.tabs.addTab(self.pose_training_tab, "姿势训练")
        
        self.simulation_tab = EnhancedSimulationTrainingWidget()
        self.tabs.addTab(self.simulation_tab, "情景模拟")
        
        self.emergency_tab = EnhancedEmergencyContactWidget(self.database, self.emergency_alert)
        self.tabs.addTab(self.emergency_tab, "紧急求助")
        
        self.statistics_tab = StatisticsWidget(self.database)
        self.tabs.addTab(self.statistics_tab, "统计进度")
        
        self.settings_tab = SettingsWidget(self.database)
        self.tabs.addTab(self.settings_tab, "系统设置")
        
        # 状态栏
        self.statusBar().showMessage("就绪")
        
        # 显示窗口
        self.show()
    
    def setup_tray_icon(self):
        """设置系统托盘图标"""
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        
        # 创建托盘图标
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.style().standardIcon(QStyle.SP_ComputerIcon))
        
        # 创建托盘菜单
        tray_menu = QMenu()
        
        show_action = QAction("显示", self)
        show_action.triggered.connect(self.show)
        
        hide_action = QAction("隐藏", self)
        hide_action.triggered.connect(self.hide)
        
        emergency_action = QAction("紧急求助", self)
        emergency_action.triggered.connect(self.quick_emergency)
        
        quit_action = QAction("退出", self)
        quit_action.triggered.connect(QApplication.quit)
        
        tray_menu.addAction(show_action)
        tray_menu.addAction(hide_action)
        tray_menu.addSeparator()
        tray_menu.addAction(emergency_action)
        tray_menu.addSeparator()
        tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()
        self.tray_icon.activated.connect(self.tray_icon_activated)
    
    def tray_icon_activated(self, reason):
        """托盘图标激活处理"""
        if reason == QSystemTrayIcon.DoubleClick:
            self.show()
    
    def quick_emergency(self):
        """快速紧急求助"""
        if not self.database.emergency_contacts:
            QMessageBox.warning(self, "警告", "请先添加紧急联系人")
            return
        
        result = self.emergency_alert.activate("快速求助")
        QMessageBox.information(self, "紧急求助", result)
    
    def closeEvent(self, event):
        """处理关闭事件"""
        if self.tray_icon.isVisible():
            self.hide()
            event.ignore()
        else:
            reply = QMessageBox.question(self, '确认退出',
                "确定要退出防身术系统吗？", 
                QMessageBox.Yes | QMessageBox.No, 
                QMessageBox.No)
            
            if reply == QMessageBox.Yes:
                self.database.save_data()
                event.accept()
            else:
                event.ignore()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # 设置应用程序样式
    app.setStyle('Fusion')
    
    # 创建并显示主窗口
    window = EnhancedSelfDefenseMainWindow()
    
    sys.exit(app.exec_())