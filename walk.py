import sys
import math
import numpy as np
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QGroupBox, QLabel, QSlider, QPushButton, QCheckBox, QComboBox,
    QDoubleSpinBox, QTabWidget, QTableWidget, QTableWidgetItem,
    QFileDialog, QSplitter, QFrame, QStatusBar
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPainter, QColor, QPen, QFont, QFontMetrics
from PyQt5.QtCore import QLineF

import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib
matplotlib.rc("font", family='Microsoft YaHei')

# 关节类
class Joint:
    def __init__(self, x, y, z=0, radius=8, name="", color=None):
        self.x = x
        self.y = y
        self.z = z
        self.radius = radius
        self.name = name
        self.color = color if color else QColor(220, 100, 100)
        self.original_pos = (x, y, z)
        self.trail = []
        self.max_trail_length = 100
        self.highlight = False
        
    def update_position(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z
        # 更新轨迹
        self.trail.append((x, y, z))
        if len(self.trail) > self.max_trail_length:
            self.trail.pop(0)
            
    def draw(self, painter, view="side", offset_x=0, offset_y=0, scale=1.0):
        if view == "side":
            x = self.x * scale + offset_x
            y = self.y * scale + offset_y
        elif view == "front":
            x = self.z * scale + offset_x
            y = self.y * scale + offset_y
        elif view == "top":
            x = self.x * scale + offset_x
            y = self.z * scale + offset_y
        
        # 绘制轨迹
        if self.trail and self.name in ["r_foot", "l_foot", "center_of_mass"]:
            pen = QPen(QColor(100, 200, 255, 150), 2, Qt.SolidLine)
            painter.setPen(pen)
            path = []
            for point in self.trail:
                if view == "side":
                    path.append((point[0] * scale + offset_x, point[1] * scale + offset_y))
                elif view == "front":
                    path.append((point[2] * scale + offset_x, point[1] * scale + offset_y))
                elif view == "top":
                    path.append((point[0] * scale + offset_x, point[2] * scale + offset_y))
            
            for i in range(1, len(path)):
                painter.drawLine(QLineF(path[i-1][0], path[i-1][1], path[i][0], path[i][1]))
        
        # 绘制关节
        color = QColor(255, 215, 0) if self.highlight else self.color
        painter.setPen(QPen(color, 2))
        painter.setBrush(QColor(30, 30, 40))
        painter.drawEllipse(int(x - self.radius), int(y - self.radius), 
                           self.radius * 2, self.radius * 2)
        
        # 绘制名称
        if self.name:
            font = painter.font()
            font.setPointSize(10)
            painter.setFont(font)
            painter.setPen(QColor(255, 255, 255))
            fm = QFontMetrics(font)
            text_width = fm.width(self.name)
            painter.drawText(int(x - text_width/2), int(y - self.radius - 10), self.name)

# 骨骼类
class Bone:
    def __init__(self, start_joint, end_joint, thickness=5, name="", color=None):
        self.start = start_joint
        self.end = end_joint
        self.thickness = thickness
        self.name = name
        self.color = color if color else QColor(180, 200, 255)
        self.force = 0
        self.highlight = False
        
    def draw(self, painter, view="side", offset_x=0, offset_y=0, scale=1.0):
        if view == "side":
            start_x = self.start.x * scale + offset_x
            start_y = self.start.y * scale + offset_y
            end_x = self.end.x * scale + offset_x
            end_y = self.end.y * scale + offset_y
        elif view == "front":
            start_x = self.start.z * scale + offset_x
            start_y = self.start.y * scale + offset_y
            end_x = self.end.z * scale + offset_x
            end_y = self.end.y * scale + offset_y
        elif view == "top":
            start_x = self.start.x * scale + offset_x
            start_y = self.start.z * scale + offset_y
            end_x = self.end.x * scale + offset_x
            end_y = self.end.z * scale + offset_y
        
        # 根据受力调整颜色
        if self.force > 0:
            force_factor = min(1.0, self.force / 3000)
            color = QColor(
                int(180 + force_factor * 75),
                int(200 - force_factor * 100),
                int(255 - force_factor * 200)
            )
        else:
            color = QColor(255, 215, 0) if self.highlight else self.color
        
        pen = QPen(color, self.thickness)
        painter.setPen(pen)
        painter.drawLine(QLineF(start_x, start_y, end_x, end_y))
        
        # 绘制骨骼名称
        if self.name:
            mid_x = (start_x + end_x) / 2
            mid_y = (start_y + end_y) / 2
            font = painter.font()
            font.setPointSize(9)
            painter.setFont(font)
            painter.setPen(QColor(220, 220, 220))
            fm = QFontMetrics(font)
            text_width = fm.width(self.name)
            painter.drawText(int(mid_x - text_width/2), int(mid_y - 15), self.name)

# 肌肉类
class Muscle:
    def __init__(self, start_joint, end_joint, thickness=8, name="", color=None):
        self.start = start_joint
        self.end = end_joint
        self.thickness = thickness
        self.name = name
        self.activation = 0.0
        self.max_force = 1000
        self.color = color if color else QColor(255, 80, 80, 180)
        self.highlight = False
        
    def draw(self, painter, view="side", offset_x=0, offset_y=0, scale=1.0):
        if view == "side":
            start_x = self.start.x * scale + offset_x
            start_y = self.start.y * scale + offset_y
            end_x = self.end.x * scale + offset_x
            end_y = self.end.y * scale + offset_y
        elif view == "front":
            start_x = self.start.z * scale + offset_x
            start_y = self.start.y * scale + offset_y
            end_x = self.end.z * scale + offset_x
            end_y = self.end.y * scale + offset_y
        elif view == "top":
            start_x = self.start.x * scale + offset_x
            start_y = self.start.z * scale + offset_y
            end_x = self.end.x * scale + offset_x
            end_y = self.end.z * scale + offset_y
        
        # 根据激活程度调整颜色
        if self.activation > 0.1:
            color = QColor(
                int(255 * self.activation),
                int(80 + 100 * (1 - self.activation)),
                int(80 * (1 - self.activation)),
                200
            )
        else:
            color = QColor(255, 180, 60, 180) if self.highlight else self.color
        
        pen = QPen(color, max(2, int(self.thickness * self.activation)))
        painter.setPen(pen)
        painter.drawLine(QLineF(start_x, start_y, end_x, end_y))

# 人体模型类
class HumanModel:
    def __init__(self, x, y, z=0, scale=1.0):
        self.joints = {}
        self.bones = []
        self.muscles = []
        self.scale = scale
        self.offset_x = x
        self.offset_y = y
        self.offset_z = z
        self.time_passed = 0
        self.walking = True
        self.walking_speed = 0.02
        self.ground_force = {"right": 0, "left": 0}
        self.gait_cycle = {"phase": 0}
        self.joint_angles = {
            "hip": {"min": -20, "max": 30, "current": 0},
            "knee": {"min": 0, "max": 60, "current": 0},
            "ankle": {"min": -15, "max": 20, "current": 0}
        }
        self.highlighted_joint = None
        self.selected_muscle = None
        self._create_skeleton()
        
    def _create_skeleton(self):
        scale = self.scale
        x, y, z = self.offset_x, self.offset_y, self.offset_z
        
        # 创建关节
        self.joints = {
            "head": Joint(x, y-90*scale, z, 10, "头部", QColor(220, 180, 100)),
            "neck": Joint(x, y-70*scale, z, 9, "颈部", QColor(200, 160, 120)),
            "shoulder": Joint(x, y-55*scale, z, 10, "肩部"),
            "spine_mid": Joint(x, y-40*scale, z, 8, "胸椎"),
            "spine": Joint(x, y-20*scale, z, 9, "腰椎"),
            "hip": Joint(x, y, z, 12, "髋部"),
            "pelvis": Joint(x, y+5*scale, z, 10, "骨盆"),
            
            "r_shoulder": Joint(x+25*scale, y-55*scale, z, 8),
            "r_elbow": Joint(x+55*scale, y-35*scale, z, 8, "肘部"),
            "r_wrist": Joint(x+75*scale, y-10*scale, z, 7, "腕部"),
            "r_hand": Joint(x+85*scale, y+5*scale, z, 6, "手部"),
            
            "l_shoulder": Joint(x-25*scale, y-55*scale, z, 8),
            "l_elbow": Joint(x-55*scale, y-35*scale, z, 8),
            "l_wrist": Joint(x-75*scale, y-10*scale, z, 7),
            "l_hand": Joint(x-85*scale, y+5*scale, z, 6),
            
            "r_hip": Joint(x+15*scale, y+5*scale, z-5*scale, 9, "髋关节"),
            "r_knee": Joint(x+25*scale, y+55*scale, z-5*scale, 9, "膝部"),
            "r_ankle": Joint(x+20*scale, y+95*scale, z-5*scale, 8, "踝部"),
            "r_foot": Joint(x+25*scale, y+105*scale, z-5*scale, 7, "足部"),
            
            "l_hip": Joint(x-15*scale, y+5*scale, z+5*scale, 9),
            "l_knee": Joint(x-25*scale, y+55*scale, z+5*scale, 9),
            "l_ankle": Joint(x-20*scale, y+95*scale, z+5*scale, 8),
            "l_foot": Joint(x-25*scale, y+105*scale, z+5*scale, 7),
            
            "center_of_mass": Joint(x, y+10*scale, z, 6, "重心", QColor(255, 215, 0))
        }
        
        # 创建骨骼
        self.bones = [
            Bone(self.joints["head"], self.joints["neck"], 5, "颈椎", QColor(180, 200, 220)),
            Bone(self.joints["neck"], self.joints["shoulder"], 6, "锁骨"),
            Bone(self.joints["shoulder"], self.joints["spine_mid"], 7, "胸骨"),
            Bone(self.joints["spine_mid"], self.joints["spine"], 7, "胸椎"),
            Bone(self.joints["spine"], self.joints["hip"], 8, "腰椎"),
            Bone(self.joints["hip"], self.joints["pelvis"], 8, "骶骨"),
            
            # 右臂
            Bone(self.joints["shoulder"], self.joints["r_shoulder"], 6, "肱骨"),
            Bone(self.joints["r_shoulder"], self.joints["r_elbow"], 5, "肱骨"),
            Bone(self.joints["r_elbow"], self.joints["r_wrist"], 4, "尺骨"),
            Bone(self.joints["r_wrist"], self.joints["r_hand"], 3, "掌骨"),
            
            # 左臂
            Bone(self.joints["shoulder"], self.joints["l_shoulder"], 6, "肱骨"),
            Bone(self.joints["l_shoulder"], self.joints["l_elbow"], 5),
            Bone(self.joints["l_elbow"], self.joints["l_wrist"], 4),
            Bone(self.joints["l_wrist"], self.joints["l_hand"], 3),
            
            # 右腿
            Bone(self.joints["pelvis"], self.joints["r_hip"], 7, "股骨"),
            Bone(self.joints["r_hip"], self.joints["r_knee"], 7, "股骨"),
            Bone(self.joints["r_knee"], self.joints["r_ankle"], 6, "胫骨"),
            Bone(self.joints["r_ankle"], self.joints["r_foot"], 5, "跖骨"),
            
            # 左腿
            Bone(self.joints["pelvis"], self.joints["l_hip"], 7),
            Bone(self.joints["l_hip"], self.joints["l_knee"], 7),
            Bone(self.joints["l_knee"], self.joints["l_ankle"], 6),
            Bone(self.joints["l_ankle"], self.joints["l_foot"], 5),
        ]
        
        # 创建肌肉
        self.muscles = [
            Muscle(self.joints["neck"], self.joints["r_shoulder"], 6, "斜方肌"),
            Muscle(self.joints["neck"], self.joints["l_shoulder"], 6, "斜方肌"),
            Muscle(self.joints["shoulder"], self.joints["r_elbow"], 6, "三角肌"),
            Muscle(self.joints["shoulder"], self.joints["l_elbow"], 6, "三角肌"),
            Muscle(self.joints["spine_mid"], self.joints["r_hip"], 8, "腹外斜肌"),
            Muscle(self.joints["spine_mid"], self.joints["l_hip"], 8, "腹外斜肌"),
            Muscle(self.joints["pelvis"], self.joints["r_knee"], 8, "股直肌"),
            Muscle(self.joints["pelvis"], self.joints["l_knee"], 8, "股直肌"),
            Muscle(self.joints["r_hip"], self.joints["r_knee"], 7, "股二头肌"),
            Muscle(self.joints["l_hip"], self.joints["l_knee"], 7, "股二头肌"),
            Muscle(self.joints["r_knee"], self.joints["r_ankle"], 6, "腓肠肌"),
            Muscle(self.joints["l_knee"], self.joints["l_ankle"], 6, "腓肠肌"),
            Muscle(self.joints["r_hip"], self.joints["r_ankle"], 6, "比目鱼肌"),
            Muscle(self.joints["l_hip"], self.joints["l_ankle"], 6, "比目鱼肌"),
        ]
    
    def update(self):
        if not self.walking:
            return
            
        self.time_passed += self.walking_speed
        self.gait_cycle["phase"] = (self.gait_cycle["phase"] + self.walking_speed * 2) % 100
        
        # 计算运动参数
        leg_angle = math.sin(self.time_passed * 2) * 35
        arm_angle = math.sin(self.time_passed * 2 + math.pi) * 30
        body_sway = math.sin(self.time_passed) * 8
        vertical_movement = math.sin(self.time_passed * 4) * 15
        
        # 应用运动到关节
        self.joints["r_hip"].update_position(
            self.joints["r_hip"].x,
            self.joints["hip"].y + 5 + math.sin(self.time_passed) * 4,
            self.joints["r_hip"].z
        )
        
        self.joints["l_hip"].update_position(
            self.joints["l_hip"].x,
            self.joints["hip"].y + 5 - math.sin(self.time_passed) * 4,
            self.joints["l_hip"].z
        )
        
        # 右腿运动
        hip_flexion = max(-20, min(30, leg_angle * 0.8))
        knee_flexion = max(0, min(60, 30 + leg_angle * 0.7))
        ankle_dorsiflexion = max(-15, min(20, 5 - leg_angle * 0.3))
        
        self.joints["r_knee"].update_position(
            self.joints["r_hip"].x + 25 + math.sin(hip_flexion * math.pi/180) * 15,
            self.joints["r_hip"].y + 50 + math.cos(hip_flexion * math.pi/180) * 25,
            self.joints["r_knee"].z
        )
        
        self.joints["r_ankle"].update_position(
            self.joints["r_knee"].x - 5 + math.sin((knee_flexion-10) * math.pi/180) * 30,
            self.joints["r_knee"].y + 40 + math.cos((knee_flexion-10) * math.pi/180) * 25,
            self.joints["r_ankle"].z
        )
        
        self.joints["r_foot"].update_position(
            self.joints["r_ankle"].x + 5 + math.sin(ankle_dorsiflexion * math.pi/180) * 15,
            self.joints["r_ankle"].y + 10 + math.cos(ankle_dorsiflexion * math.pi/180) * 10,
            self.joints["r_foot"].z
        )
        
        # 左腿运动
        hip_flexion = max(-20, min(30, -leg_angle * 0.8))
        knee_flexion = max(0, min(60, 30 - leg_angle * 0.7))
        ankle_dorsiflexion = max(-15, min(20, 5 + leg_angle * 0.3))
        
        self.joints["l_knee"].update_position(
            self.joints["l_hip"].x - 25 + math.sin(hip_flexion * math.pi/180) * 15,
            self.joints["l_hip"].y + 50 + math.cos(hip_flexion * math.pi/180) * 25,
            self.joints["l_knee"].z
        )
        
        self.joints["l_ankle"].update_position(
            self.joints["l_knee"].x + 5 + math.sin((knee_flexion-10) * math.pi/180) * 30,
            self.joints["l_knee"].y + 40 + math.cos((knee_flexion-10) * math.pi/180) * 25,
            self.joints["l_ankle"].z
        )
        
        self.joints["l_foot"].update_position(
            self.joints["l_ankle"].x - 5 + math.sin(ankle_dorsiflexion * math.pi/180) * 15,
            self.joints["l_ankle"].y + 10 + math.cos(ankle_dorsiflexion * math.pi/180) * 10,
            self.joints["l_foot"].z
        )
        
        # 右臂运动
        self.joints["r_elbow"].update_position(
            self.joints["r_shoulder"].x + 30 + math.sin(arm_angle * math.pi/180) * 15,
            self.joints["r_shoulder"].y + 20 + math.cos(arm_angle * math.pi/180) * 20,
            self.joints["r_elbow"].z
        )
        
        self.joints["r_wrist"].update_position(
            self.joints["r_elbow"].x + 20 + math.sin((arm_angle+10) * math.pi/180) * 20,
            self.joints["r_elbow"].y + 25 + math.cos((arm_angle+10) * math.pi/180) * 15,
            self.joints["r_wrist"].z
        )
        
        self.joints["r_hand"].update_position(
            self.joints["r_wrist"].x + 10 + math.sin((arm_angle+20) * math.pi/180) * 15,
            self.joints["r_wrist"].y + 5 + math.cos((arm_angle+20) * math.pi/180) * 10,
            self.joints["r_hand"].z
        )
        
        # 左臂运动
        self.joints["l_elbow"].update_position(
            self.joints["l_shoulder"].x - 30 + math.sin(-arm_angle * math.pi/180) * 15,
            self.joints["l_shoulder"].y + 20 + math.cos(arm_angle * math.pi/180) * 20,
            self.joints["l_elbow"].z
        )
        
        self.joints["l_wrist"].update_position(
            self.joints["l_elbow"].x - 20 + math.sin((-arm_angle+10) * math.pi/180) * 20,
            self.joints["l_elbow"].y + 25 + math.cos((arm_angle+10) * math.pi/180) * 15,
            self.joints["l_wrist"].z
        )
        
        self.joints["l_hand"].update_position(
            self.joints["l_wrist"].x - 10 + math.sin((-arm_angle+20) * math.pi/180) * 15,
            self.joints["l_wrist"].y + 5 + math.cos((arm_angle+20) * math.pi/180) * 10,
            self.joints["l_hand"].z
        )
        
        # 身体轻微摆动
        self.joints["shoulder"].update_position(
            self.joints["spine_mid"].x + body_sway,
            self.joints["shoulder"].y,
            self.joints["shoulder"].z
        )
        
        self.joints["hip"].update_position(
            self.joints["spine_mid"].x - body_sway * 0.7,
            self.joints["hip"].y,
            self.joints["hip"].z
        )
        
        self.joints["spine_mid"].update_position(
            self.joints["spine_mid"].x,
            self.joints["spine"].y - 20 + vertical_movement * 0.3,
            self.joints["spine_mid"].z
        )
        
        self.joints["head"].update_position(
            self.joints["head"].x,
            self.joints["neck"].y - 20 + vertical_movement * 0.5,
            self.joints["head"].z
        )
        
        # 更新重心
        total_x, total_y, total_z, count = 0, 0, 0, 0
        for name, joint in self.joints.items():
            if name not in ["center_of_mass"]:
                total_x += joint.x
                total_y += joint.y
                total_z += joint.z
                count += 1
        self.joints["center_of_mass"].update_position(
            total_x / count,
            total_y / count,
            total_z / count
        )
        
        # 肌肉激活状态
        for muscle in self.muscles:
            # 根据步态周期激活肌肉
            if "r_" in muscle.name and "hip" in muscle.name:
                muscle.activation = max(0.3, min(1.0, abs(math.sin(self.time_passed * 2)) * 0.8))
            elif "l_" in muscle.name and "hip" in muscle.name:
                muscle.activation = max(0.3, min(1.0, abs(math.cos(self.time_passed * 2)) * 0.8))
            elif "knee" in muscle.name:
                muscle.activation = 0.4 + abs(math.sin(self.time_passed * 2)) * 0.6
            elif "ankle" in muscle.name:
                muscle.activation = 0.5 + abs(math.cos(self.time_passed * 2)) * 0.5
            else:
                muscle.activation = 0.3 + abs(math.sin(self.time_passed * 3)) * 0.4
        
        # 地面反作用力
        self.ground_force["right"] = max(0, 800 + math.sin(self.time_passed * 2) * 600)
        self.ground_force["left"] = max(0, 800 + math.cos(self.time_passed * 2) * 600)
        
        # 更新骨骼受力
        for bone in self.bones:
            # 简单模拟受力 - 实际应用中需要更复杂的生物力学计算
            if "股骨" in bone.name:
                bone.force = 1200 + abs(math.sin(self.time_passed * 2)) * 1800
            elif "胫骨" in bone.name:
                bone.force = 1000 + abs(math.sin(self.time_passed * 2)) * 1500
            else:
                bone.force = 300 + abs(math.sin(self.time_passed * 3)) * 200
    
    def reset(self):
        self.time_passed = 0
        for name, joint in self.joints.items():
            joint.x, joint.y, joint.z = joint.original_pos
            joint.trail = []
    
    def toggle_walking(self):
        self.walking = not self.walking
    
    def set_walking_speed(self, speed):
        self.walking_speed = speed / 1000.0
    
    def highlight_joint(self, joint_name):
        # 清除之前的高亮
        if self.highlighted_joint:
            self.joints[self.highlighted_joint].highlight = False
            self.highlighted_joint = None
            
        # 清除肌肉高亮
        for muscle in self.muscles:
            muscle.highlight = False
        
        if joint_name:
            self.joints[joint_name].highlight = True
            self.highlighted_joint = joint_name
    
    def highlight_muscle(self, muscle_index):
        # 清除关节高亮
        self.highlight_joint(None)
        
        # 清除之前的高亮
        for muscle in self.muscles:
            muscle.highlight = False
        
        if muscle_index is not None and 0 <= muscle_index < len(self.muscles):
            self.muscles[muscle_index].highlight = True
            self.selected_muscle = self.muscles[muscle_index]

# 自定义绘图区域
class GaitCanvas(QWidget):
    def __init__(self, human_model, view="side", parent=None):
        super().__init__(parent)
        self.human_model = human_model
        self.view = view
        self.scale = 1.0
        self.offset_x = 0
        self.offset_y = 0
        self.setMinimumSize(400, 500)
        self.setMouseTracking(True)
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 填充背景
        painter.fillRect(self.rect(), QColor(10, 15, 25))
        
        # 绘制网格
        grid_color = QColor(40, 60, 80)
        pen = QPen(grid_color, 1)
        painter.setPen(pen)
        
        for i in range(0, self.width(), 40):
            painter.drawLine(i, 0, i, self.height())
        for i in range(0, self.height(), 40):
            painter.drawLine(0, i, self.width(), i)
        
        # 计算偏移使模型居中
        self.offset_x = self.width() / 2 - self.human_model.offset_x * self.scale
        self.offset_y = self.height() / 2 - self.human_model.offset_y * self.scale
        
        # 绘制肌肉
        for muscle in self.human_model.muscles:
            muscle.draw(painter, self.view, self.offset_x, self.offset_y, self.scale)
        
        # 绘制骨骼
        for bone in self.human_model.bones:
            bone.draw(painter, self.view, self.offset_x, self.offset_y, self.scale)
        
        # 绘制关节
        for name, joint in self.human_model.joints.items():
            joint.draw(painter, self.view, self.offset_x, self.offset_y, self.scale)
        
        # 绘制地面反作用力
        if self.view == "side":
            # 右脚力量
            if self.human_model.ground_force["right"] > 10:
                force_scale = self.human_model.ground_force["right"] / 1500
                start_x = self.human_model.joints["r_foot"].x * self.scale + self.offset_x
                start_y = self.human_model.joints["r_foot"].y * self.scale + self.offset_y + 10
                end_x = start_x
                end_y = start_y - 20 - force_scale * 50
                
                pen = QPen(QColor(100, 255, 100), max(2, int(force_scale * 8)))
                painter.setPen(pen)
                painter.drawLine(QLineF(start_x, start_y, end_x, end_y))
                painter.drawLine(QLineF(end_x - 8, end_y + 5, end_x, end_y))
                painter.drawLine(QLineF(end_x + 8, end_y + 5, end_x, end_y))
                
                font = painter.font()
                font.setPointSize(9)
                painter.setFont(font)
                painter.setPen(QColor(100, 255, 100))
                force_text = f"{self.human_model.ground_force['right']:.0f}N"
                painter.drawText(int(end_x - 30), int(end_y - 20), force_text)
            
            # 左脚力量
            if self.human_model.ground_force["left"] > 10:
                force_scale = self.human_model.ground_force["left"] / 1500
                start_x = self.human_model.joints["l_foot"].x * self.scale + self.offset_x
                start_y = self.human_model.joints["l_foot"].y * self.scale + self.offset_y + 10
                end_x = start_x
                end_y = start_y - 20 - force_scale * 50
                
                pen = QPen(QColor(100, 255, 100), max(2, int(force_scale * 8)))
                painter.setPen(pen)
                painter.drawLine(QLineF(start_x, start_y, end_x, end_y))
                painter.drawLine(QLineF(end_x - 8, end_y + 5, end_x, end_y))
                painter.drawLine(QLineF(end_x + 8, end_y + 5, end_x, end_y))
                
                font = painter.font()
                font.setPointSize(9)
                painter.setFont(font)
                painter.setPen(QColor(100, 255, 100))
                force_text = f"{self.human_model.ground_force['left']:.0f}N"
                painter.drawText(int(end_x - 30), int(end_y - 20), force_text)
        
        # 绘制视图名称
        view_names = {
            "side": "侧视图",
            "front": "前视图",
            "top": "俯视图"
        }
        painter.setPen(QColor(200, 200, 200))
        font = painter.font()
        font.setPointSize(12)
        painter.setFont(font)
        painter.drawText(10, 20, view_names[self.view])
    
    def mousePressEvent(self, event):
        # 检查是否点击了关节
        mouse_x, mouse_y = event.x(), event.y()
        closest_joint = None
        min_dist = float('inf')
        
        for name, joint in self.human_model.joints.items():
            if self.view == "side":
                x = joint.x * self.scale + self.offset_x
                y = joint.y * self.scale + self.offset_y
            elif self.view == "front":
                x = joint.z * self.scale + self.offset_x
                y = joint.y * self.scale + self.offset_y
            elif self.view == "top":
                x = joint.x * self.scale + self.offset_x
                y = joint.z * self.scale + self.offset_y
            
            dist = math.sqrt((x - mouse_x)**2 + (y - mouse_y)**2)
            if dist < joint.radius + 5 and dist < min_dist:
                min_dist = dist
                closest_joint = name
        
        if closest_joint:
            self.human_model.highlight_joint(closest_joint)
            # 修改为获取顶层窗口（主窗口）
            main_window = self.window()
            if main_window:
                main_window.update_muscle_info()
            self.update()
            return
        
        # 检查是否点击了肌肉
        closest_muscle = None
        min_dist = float('inf')
        
        for i, muscle in enumerate(self.human_model.muscles):
            if self.view == "side":
                start_x = muscle.start.x * self.scale + self.offset_x
                start_y = muscle.start.y * self.scale + self.offset_y
                end_x = muscle.end.x * self.scale + self.offset_x
                end_y = muscle.end.y * self.scale + self.offset_y
            elif self.view == "front":
                start_x = muscle.start.z * self.scale + self.offset_x
                start_y = muscle.start.y * self.scale + self.offset_y
                end_x = muscle.end.z * self.scale + self.offset_x
                end_y = muscle.end.y * self.scale + self.offset_y
            elif self.view == "top":
                start_x = muscle.start.x * self.scale + self.offset_x
                start_y = muscle.start.z * self.scale + self.offset_y
                end_x = muscle.end.x * self.scale + self.offset_x
                end_y = muscle.end.z * self.scale + self.offset_y
            
            # 计算点到线段的距离
            line_len = math.sqrt((end_x - start_x)**2 + (end_y - start_y)**2)
            if line_len == 0:
                continue
            
            # 计算投影点
            t = max(0, min(1, ((mouse_x - start_x) * (end_x - start_x) + 
                              (mouse_y - start_y) * (end_y - start_y)) / (line_len**2)))
            proj_x = start_x + t * (end_x - start_x)
            proj_y = start_y + t * (end_y - start_y)
            
            dist = math.sqrt((mouse_x - proj_x)**2 + (mouse_y - proj_y)**2)
            if dist < muscle.thickness * muscle.activation + 5 and dist < min_dist:
                min_dist = dist
                closest_muscle = i
        
        if closest_muscle is not None:
            self.human_model.highlight_muscle(closest_muscle)
            # 修改为获取顶层窗口（主窗口）
            main_window = self.window()
            if main_window:
                main_window.update_muscle_info()
            self.update()
            return
        
        # 如果没有点击到任何东西，清除高亮
        self.human_model.highlight_joint(None)
        self.human_model.highlight_muscle(None)
        # 修改为获取顶层窗口（主窗口）
        main_window = self.window()
        if main_window:
            main_window.update_muscle_info()
        self.update()

# 步态分析图表
class GaitAnalysisPlot(FigureCanvas):
    def __init__(self, human_model, parent=None):
        self.fig = Figure(figsize=(5, 4), dpi=100)
        super().__init__(self.fig)
        self.human_model = human_model
        self.setParent(parent)
        self.init_ui()
    
    def init_ui(self):
        self.ax = self.fig.add_subplot(111)
        self.ax.set_title('关节角度变化')
        self.ax.set_xlabel('步态周期 (%)')
        self.ax.set_ylabel('角度 (°)')
        self.ax.grid(True)
        self.ax.set_xlim(0, 100)
        self.ax.set_ylim(-30, 70)
        
        # 初始化线条
        self.hip_line, = self.ax.plot([], [], 'r-', label='髋关节')
        self.knee_line, = self.ax.plot([], [], 'g-', label='膝关节')
        self.ankle_line, = self.ax.plot([], [], 'b-', label='踝关节')
        self.ax.legend()
        
        # 初始化数据
        self.data = {
            "phase": [],
            "hip": [],
            "knee": [],
            "ankle": []
        }
    
    def update_plot(self):
        phase = self.human_model.gait_cycle["phase"]
        hip_angle = self.human_model.joint_angles["hip"]["current"]
        knee_angle = self.human_model.joint_angles["knee"]["current"]
        ankle_angle = self.human_model.joint_angles["ankle"]["current"]
        
        # 添加新数据
        self.data["phase"].append(phase)
        self.data["hip"].append(hip_angle)
        self.data["knee"].append(knee_angle)
        self.data["ankle"].append(ankle_angle)
        
        # 限制数据长度
        if len(self.data["phase"]) > 200:
            for key in self.data:
                self.data[key].pop(0)
        
        # 更新图表
        self.hip_line.set_data(self.data["phase"], self.data["hip"])
        self.knee_line.set_data(self.data["phase"], self.data["knee"])
        self.ankle_line.set_data(self.data["phase"], self.data["ankle"])
        
        # 自动调整坐标轴范围
        min_y = min(min(self.data["hip"]), min(self.data["knee"]), min(self.data["ankle"])) - 5
        max_y = max(max(self.data["hip"]), max(self.data["knee"]), max(self.data["ankle"])) + 5
        self.ax.set_ylim(min_y, max_y)
        
        self.draw()

# 主应用程序窗口
class GaitAnalysisApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("高级人体行走生物力学模拟系统")
        self.setGeometry(100, 100, 1400, 900)
        
        # 创建人体模型
        self.human_model = HumanModel(0, 0, 0, 1.0)
        
        # 初始化UI
        self.init_ui()
        
        # 初始化定时器
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_simulation)
        self.timer.start(30)  # 约30fps
    
    def init_ui(self):
        # 创建主布局
        main_widget = QWidget()
        main_layout = QHBoxLayout()
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)
        
        # 左侧控制面板
        control_panel = QGroupBox("控制面板")
        control_layout = QVBoxLayout()
        control_panel.setLayout(control_layout)
        control_panel.setFixedWidth(300)
        
        # 行走控制
        walking_group = QGroupBox("行走控制")
        walking_layout = QVBoxLayout()
        walking_group.setLayout(walking_layout)
        
        self.walking_toggle = QPushButton("暂停")
        self.walking_toggle.setCheckable(True)
        self.walking_toggle.setChecked(True)
        self.walking_toggle.clicked.connect(self.toggle_walking)
        walking_layout.addWidget(self.walking_toggle)
        
        self.reset_button = QPushButton("重置位置")
        self.reset_button.clicked.connect(self.reset_simulation)
        walking_layout.addWidget(self.reset_button)
        
        speed_label = QLabel("行走速度:")
        walking_layout.addWidget(speed_label)
        
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setMinimum(1)
        self.speed_slider.setMaximum(100)
        self.speed_slider.setValue(20)
        self.speed_slider.valueChanged.connect(self.set_walking_speed)
        walking_layout.addWidget(self.speed_slider)
        
        self.show_trails = QCheckBox("显示运动轨迹")
        self.show_trails.setChecked(True)
        walking_layout.addWidget(self.show_trails)
        
        control_layout.addWidget(walking_group)
        
        # 视图控制
        view_group = QGroupBox("视图控制")
        view_layout = QVBoxLayout()
        view_group.setLayout(view_layout)
        
        scale_label = QLabel("缩放比例:")
        view_layout.addWidget(scale_label)
        
        self.scale_slider = QSlider(Qt.Horizontal)
        self.scale_slider.setMinimum(50)
        self.scale_slider.setMaximum(200)
        self.scale_slider.setValue(100)
        self.scale_slider.valueChanged.connect(self.update_scale)
        view_layout.addWidget(self.scale_slider)
        
        self.show_muscles = QCheckBox("显示肌肉系统")
        self.show_muscles.setChecked(True)
        view_layout.addWidget(self.show_muscles)
        
        self.show_forces = QCheckBox("显示受力情况")
        self.show_forces.setChecked(True)
        view_layout.addWidget(self.show_forces)
        
        control_layout.addWidget(view_group)
        
        # 肌肉信息
        self.muscle_group = QGroupBox("肌肉信息")
        muscle_layout = QVBoxLayout()
        self.muscle_group.setLayout(muscle_layout)
        
        self.muscle_name = QLabel("肌肉: 无")
        muscle_layout.addWidget(self.muscle_name)
        
        self.muscle_activation = QLabel("激活程度: 0%")
        muscle_layout.addWidget(self.muscle_activation)
        
        self.muscle_force = QLabel("产生力量: 0 N")
        muscle_layout.addWidget(self.muscle_force)
        
        self.muscle_function = QLabel("功能: 无")
        muscle_layout.addWidget(self.muscle_function)
        
        control_layout.addWidget(self.muscle_group)
        
        # 数据导出
        export_group = QGroupBox("数据导出")
        export_layout = QVBoxLayout()
        export_group.setLayout(export_layout)
        
        self.export_button = QPushButton("导出步态数据")
        self.export_button.clicked.connect(self.export_gait_data)
        export_layout.addWidget(self.export_button)
        
        self.export_chart = QPushButton("导出分析图表")
        self.export_chart.clicked.connect(self.export_analysis_chart)
        export_layout.addWidget(self.export_chart)
        
        control_layout.addWidget(export_group)
        control_layout.addStretch()
        
        # 右侧主区域
        main_area = QSplitter(Qt.Horizontal)
        
        # 视图区域
        views_widget = QWidget()
        views_layout = QVBoxLayout()
        views_widget.setLayout(views_layout)
        
        # 创建三个视图
        self.side_view = GaitCanvas(self.human_model, "side")
        self.front_view = GaitCanvas(self.human_model, "front")
        self.top_view = GaitCanvas(self.human_model, "top")
        
        views_layout.addWidget(QLabel("侧视图"))
        views_layout.addWidget(self.side_view)
        views_layout.addWidget(QLabel("前视图"))
        views_layout.addWidget(self.front_view)
        views_layout.addWidget(QLabel("俯视图"))
        views_layout.addWidget(self.top_view)
        
        # 分析和数据区域
        analysis_tabs = QTabWidget()
        
        # 图表分析标签
        chart_tab = QWidget()
        chart_layout = QVBoxLayout()
        chart_tab.setLayout(chart_layout)
        
        self.gait_plot = GaitAnalysisPlot(self.human_model)
        chart_layout.addWidget(self.gait_plot)
        
        # 数据表格标签
        data_tab = QWidget()
        data_layout = QVBoxLayout()
        data_tab.setLayout(data_layout)
        
        self.data_table = QTableWidget()
        self.data_table.setColumnCount(5)
        self.data_table.setHorizontalHeaderLabels(["时间", "步态相位", "髋关节角度", "膝关节角度", "踝关节角度"])
        self.data_table.setRowCount(100)
        data_layout.addWidget(self.data_table)
        
        analysis_tabs.addTab(chart_tab, "图表分析")
        analysis_tabs.addTab(data_tab, "步态数据")
        
        # 添加到主区域
        main_area.addWidget(views_widget)
        main_area.addWidget(analysis_tabs)
        main_area.setSizes([800, 400])
        
        # 添加到主布局
        main_layout.addWidget(control_panel)
        main_layout.addWidget(main_area)
        
        # 状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪 | 模拟运行中")
    
    def update_simulation(self):
        self.human_model.update()
        self.side_view.update()
        self.front_view.update()
        self.top_view.update()
        self.gait_plot.update_plot()
        self.update_data_table()
    
    def toggle_walking(self):
        self.human_model.toggle_walking()
        if self.human_model.walking:
            self.walking_toggle.setText("暂停")
            self.status_bar.showMessage("就绪 | 模拟运行中")
        else:
            self.walking_toggle.setText("开始")
            self.status_bar.showMessage("就绪 | 模拟已暂停")
    
    def set_walking_speed(self, speed):
        self.human_model.set_walking_speed(speed)
        self.status_bar.showMessage(f"就绪 | 模拟速度: {speed/10.0:.1f}%")
    
    def reset_simulation(self):
        self.human_model.reset()
        self.side_view.update()
        self.front_view.update()
        self.top_view.update()
        self.status_bar.showMessage("就绪 | 模型已重置")
    
    def update_scale(self, value):
        self.human_model.scale = value / 100.0
        self.status_bar.showMessage(f"就绪 | 缩放比例: {value}%")
    
    def update_muscle_info(self):
        if self.human_model.selected_muscle:
            muscle = self.human_model.selected_muscle
            self.muscle_name.setText(f"肌肉: {muscle.name}")
            self.muscle_activation.setText(f"激活程度: {muscle.activation*100:.1f}%")
            self.muscle_force.setText(f"产生力量: {muscle.activation * muscle.max_force:.0f} N")
            self.muscle_function.setText("功能: 下肢运动的主要动力源")
        else:
            self.muscle_name.setText("肌肉: 无")
            self.muscle_activation.setText("激活程度: 0%")
            self.muscle_force.setText("产生力量: 0 N")
            self.muscle_function.setText("功能: 无")
    
    def update_data_table(self):
        # 简化实现 - 实际应用中应记录时间序列数据
        phase = self.human_model.gait_cycle["phase"]
        hip_angle = self.human_model.joint_angles["hip"]["current"]
        knee_angle = self.human_model.joint_angles["knee"]["current"]
        ankle_angle = self.human_model.joint_angles["ankle"]["current"]
        
        # 添加新行
        row_count = self.data_table.rowCount()
        self.data_table.insertRow(row_count)
        
        # 添加数据
        self.data_table.setItem(row_count, 0, QTableWidgetItem(f"{self.human_model.time_passed:.2f}s"))
        self.data_table.setItem(row_count, 1, QTableWidgetItem(f"{phase:.1f}%"))
        self.data_table.setItem(row_count, 2, QTableWidgetItem(f"{hip_angle:.1f}°"))
        self.data_table.setItem(row_count, 3, QTableWidgetItem(f"{knee_angle:.1f}°"))
        self.data_table.setItem(row_count, 4, QTableWidgetItem(f"{ankle_angle:.1f}°"))
        
        # 滚动到最后一行
        self.data_table.scrollToBottom()
    
    def export_gait_data(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出步态数据", "", "CSV Files (*.csv);;All Files (*)"
        )
        
        if file_path:
            # 实际应用中应导出完整数据
            with open(file_path, 'w') as f:
                f.write("Time,Gait Phase,Hip Angle,Knee Angle,Ankle Angle\n")
                f.write(f"{self.human_model.time_passed:.2f},{self.human_model.gait_cycle['phase']:.1f},"
                        f"{self.human_model.joint_angles['hip']['current']:.1f},"
                        f"{self.human_model.joint_angles['knee']['current']:.1f},"
                        f"{self.human_model.joint_angles['ankle']['current']:.1f}\n")
            
            self.status_bar.showMessage(f"步态数据已导出到: {file_path}")
    
    def export_analysis_chart(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出分析图表", "", "PNG Files (*.png);;JPEG Files (*.jpg);;All Files (*)"
        )
        
        if file_path:
            # 保存当前图表
            self.gait_plot.fig.savefig(file_path, dpi=300)
            self.status_bar.showMessage(f"分析图表已导出到: {file_path}")

# 运行应用程序
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    # 设置应用程序样式
    app.setStyleSheet("""
        QMainWindow {
            background-color: #2c3e50;
        }
        QGroupBox {
            font-weight: bold;
            border: 1px solid #34495e;
            border-radius: 5px;
            margin-top: 1ex;
            background-color: #34495e;
            color: #ecf0f1;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top center;
            padding: 0 5px;
            background-color: #34495e;
            color: #3498db;
        }
        QPushButton {
            background-color: #3498db;
            color: white;
            border: none;
            padding: 8px;
            border-radius: 4px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #2980b9;
        }
        QPushButton:pressed {
            background-color: #1c638e;
        }
        QSlider::groove:horizontal {
            border: 1px solid #bbb;
            background: #34495e;
            height: 6px;
            border-radius: 3px;
        }
        QSlider::handle:horizontal {
            background: #3498db;
            border: 1px solid #2c3e50;
            width: 16px;
            margin: -5px 0;
            border-radius: 8px;
        }
        QLabel {
            color: #ecf0f1;
        }
        QTableWidget {
            background-color: #34495e;
            color: #ecf0f1;
            gridline-color: #2c3e50;
        }
        QHeaderView::section {
            background-color: #2c3e50;
            color: #ecf0f1;
            padding: 4px;
            border: 1px solid #34495e;
        }
    """)
    
    window = GaitAnalysisApp()
    window.show()
    sys.exit(app.exec_())