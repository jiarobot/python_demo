#!/usr/bin/env python3
"""
高级PX4无人机反制系统 - PyQt5实现
具备多传感器融合、AI决策、实时监控等高级功能
"""

import sys
import os
import logging
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QGridLayout, QGroupBox, QLabel, QPushButton, QComboBox, 
                            QSlider, QProgressBar, QTableWidget, QTableWidgetItem,
                            QTabWidget, QTextEdit, QSplitter, QFrame, QMessageBox,
                            QHeaderView, QCheckBox, QSpinBox, QDoubleSpinBox)
from PyQt5.QtCore import QPointF, Qt, QTimer, QThread, pyqtSignal, QDateTime
from PyQt5.QtGui import QFont, QColor, QPalette, QPainter, QPen, QBrush, QFontDatabase
import numpy as np
import random
import json
import sqlite3
from enum import Enum
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple

# 导入系统核心模块
from core.drone_system import AdvancedCounterDroneSystem, AdvancedDrone, DroneType, ThreatLevel, CounterMeasure
# from core.sensor_system import SensorSystem
# from core.ai_system import AIDecisionSystem
# from core.data_recorder import DataRecorder

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("DroneDefenseGUI")

class RadarWidget(QWidget):
    """雷达显示组件"""
    def __init__(self, system):
        super().__init__()
        self.system = system
        self.setMinimumSize(500, 500)
        self.setStyleSheet("background-color: #0a121e; border: 2px solid #2d5278;")
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 获取尺寸
        width = self.width()
        height = self.height()
        center_x = width // 2
        center_y = height // 2
        radius = min(center_x, center_y) - 20
        
        # 绘制雷达背景
        painter.setPen(QPen(QColor(45, 82, 120), 2))
        painter.setBrush(QBrush(QColor(20, 35, 55)))
        painter.drawEllipse(center_x - radius, center_y - radius, radius * 2, radius * 2)
        
        # 绘制距离环
        for i in range(1, 5):
            r = radius * i // 4
            painter.setPen(QPen(QColor(60, 100, 150), 1))
            painter.drawEllipse(center_x - r, center_y - r, r * 2, r * 2)
            
            # 距离标注
            painter.setPen(QPen(Qt.white))
            painter.drawText(center_x + r - 15, center_y - 10, f"{i * 200}m")
        
        # 绘制坐标轴
        painter.setPen(QPen(QColor(80, 130, 200), 2))
        painter.drawLine(center_x - radius, center_y, center_x + radius, center_y)
        painter.drawLine(center_x, center_y - radius, center_x, center_y + radius)
        
        # 绘制扫描线
        import time
        current_time = time.time()
        angle = (current_time * 60) % 360
        end_x = center_x + radius * np.cos(np.radians(angle))
        end_y = center_y - radius * np.sin(np.radians(angle))
        
        painter.setPen(QPen(QColor(100, 255, 100, 180), 3))
        painter.drawLine(QPointF(center_x, center_y), QPointF(end_x, end_y))
        
        # 绘制无人机
        for drone in self.system.drones:
            if drone.detected:
                # 坐标转换
                scale = 0.8 * radius / self.system.detection_range
                pos_x = center_x + drone.position[0] * scale
                pos_y = center_y + drone.position[1] * scale
                
                # 检查是否在雷达范围内
                if np.linalg.norm([pos_x - center_x, pos_y - center_y]) <= radius:
                    # 根据威胁级别选择颜色
                    threat_colors = [
                        QColor(80, 255, 120),    # 低威胁
                        QColor(255, 255, 80),    # 中威胁
                        QColor(255, 160, 60),    # 高威胁
                        QColor(255, 60, 60)      # 严重威胁
                    ]
                    color = threat_colors[drone.threat_level.value]
                    size = 6 + drone.threat_level.value * 4
                    
                    # 绘制无人机
                    painter.setPen(QPen(color, 2))
                    painter.setBrush(QBrush(color))
                    painter.drawEllipse(int(pos_x - size), int(pos_y - size), size * 2, size * 2)
                    
                    # 绘制轨迹
                    if len(drone.flight_path.positions) > 1:
                        painter.setPen(QPen(color, 1))
                        points = []
                        for pos in drone.flight_path.positions[-20:]:  # 只显示最近20个点
                            point_x = center_x + pos[0] * scale
                            point_y = center_y + pos[1] * scale
                            if np.linalg.norm([point_x - center_x, point_y - center_y]) <= radius:
                                points.append((point_x, point_y))
                        
                        for i in range(len(points) - 1):
                            painter.drawLine(int(points[i][0]), int(points[i][1]), 
                                           int(points[i+1][0]), int(points[i+1][1]))
                    
                    # 干扰效果
                    if drone.interfered:
                        painter.setPen(QPen(QColor(255, 80, 80, 150), 2))
                        painter.drawEllipse(int(pos_x - size - 5), int(pos_y - size - 5), 
                                          (size + 5) * 2, (size + 5) * 2)
                        
                        painter.setPen(QPen(QColor(255, 120, 120, 100), 1))
                        painter.drawEllipse(int(pos_x - size - 10), int(pos_y - size - 10), 
                                          (size + 10) * 2, (size + 10) * 2)
                    
                    # 绘制ID
                    painter.setPen(QPen(Qt.white))
                    painter.drawText(int(pos_x + size + 5), int(pos_y), f"ID:{drone.id}")

class SpectrumWidget(QWidget):
    """频谱显示组件"""
    def __init__(self, system):
        super().__init__()
        self.system = system
        self.setMinimumHeight(150)
        self.setStyleSheet("background-color: #192841; border: 1px solid #2d5278;")
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        width = self.width()
        height = self.height()
        
        # 绘制网格
        painter.setPen(QPen(QColor(60, 100, 150), 1))
        for i in range(1, 5):
            y = i * height // 5
            painter.drawLine(0, y, width, y)
        
        for i in range(1, 10):
            x = i * width // 10
            painter.drawLine(x, 0, x, height)
        
        # 绘制频谱
        if len(self.system.spectrum_data) > 0:
            bar_width = width / len(self.system.spectrum_data)
            
            for i, value in enumerate(self.system.spectrum_data):
                bar_height = value * height * 0.85
                x = i * bar_width
                y = height - bar_height
                
                # 颜色渐变
                color_intensity = int(100 + value * 155)
                color = QColor(80, color_intensity, 255)
                
                painter.setPen(QPen(color))
                painter.setBrush(QBrush(color))
                painter.drawRect(int(x), int(y), max(2, int(bar_width - 1)), int(bar_height))
        
        # 绘制标题和刻度
        painter.setPen(QPen(Qt.white))
        painter.drawText(10, 20, "实时射频频谱监测")
        
        # 频率刻度
        for i in range(0, 11):
            freq = i * 2.4
            x = i * width // 10
            painter.drawText(x, height - 10, f"{freq:.1f}GHz")

class StatusPanel(QWidget):
    """系统状态面板"""
    def __init__(self, system):
        super().__init__()
        self.system = system
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 标题
        title = QLabel("系统状态监控")
        title.setStyleSheet("font-size: 16pt; font-weight: bold; color: #ffffff; margin: 10px;")
        layout.addWidget(title)
        
        # 状态信息
        self.status_labels = {}
        status_items = [
            ("system_status", "系统状态"),
            ("operation_mode", "工作模式"), 
            ("emergency_mode", "紧急模式"),
            ("detected_drones", "检测目标"),
            ("countered_drones", "反制目标"),
            ("critical_threats", "严重威胁"),
            ("alert_level", "警报级别"),
            ("detection_rate", "检测率"),
            ("response_time", "响应时间"),
            ("system_uptime", "运行时间")
        ]
        
        for key, name in status_items:
            group = QHBoxLayout()
            label = QLabel(f"{name}:")
            label.setStyleSheet("color: #cccccc; font-size: 12pt;")
            value = QLabel("--")
            value.setStyleSheet("color: #ffffff; font-size: 12pt; font-weight: bold;")
            
            group.addWidget(label)
            group.addStretch()
            group.addWidget(value)
            layout.addLayout(group)
            
            self.status_labels[key] = value
        
        layout.addStretch()
        self.setLayout(layout)
        self.setStyleSheet("background-color: #192841; border: 2px solid #2d5278; padding: 10px;")
    
    def update_status(self):
        """更新状态显示"""
        status = self.system.get_system_status()
        
        # 系统状态
        self.status_labels["system_status"].setText("运行中" if status['system_active'] else "已关闭")
        self.status_labels["system_status"].setStyleSheet(
            "color: #64ff96; font-size: 12pt; font-weight: bold;" if status['system_active'] else
            "color: #ff6464; font-size: 12pt; font-weight: bold;"
        )
        
        # 工作模式
        self.status_labels["operation_mode"].setText("自动" if status['auto_mode'] else "手动")
        
        # 紧急模式
        self.status_labels["emergency_mode"].setText("激活" if status['emergency_mode'] else "正常")
        self.status_labels["emergency_mode"].setStyleSheet(
            "color: #ff6464; font-size: 12pt; font-weight: bold;" if status['emergency_mode'] else
            "color: #64ff96; font-size: 12pt; font-weight: bold;"
        )
        
        # 检测信息
        self.status_labels["detected_drones"].setText(f"{status['detected_drones']}/{status['total_drones']}")
        self.status_labels["countered_drones"].setText(str(status['interfered_drones']))
        
        # 威胁信息
        self.status_labels["critical_threats"].setText(str(status['critical_threats']))
        self.status_labels["critical_threats"].setStyleSheet(
            "color: #ff6464; font-size: 12pt; font-weight: bold;" if status['critical_threats'] > 0 else
            "color: #ffffff; font-size: 12pt; font-weight: bold;"
        )
        
        # 性能指标
        self.status_labels["alert_level"].setText(f"{status['alert_level']}/100")
        alert_color = "#ff6464" if status['alert_level'] > 70 else "#ffb464" if status['alert_level'] > 30 else "#64ff96"
        self.status_labels["alert_level"].setStyleSheet(f"color: {alert_color}; font-size: 12pt; font-weight: bold;")
        
        self.status_labels["detection_rate"].setText(f"{status['detection_rate']*100:.1f}%")
        self.status_labels["response_time"].setText(f"{status['response_time']:.1f}ms")
        self.status_labels["system_uptime"].setText(f"{int(status['system_uptime'])}秒")

class ControlPanel(QWidget):
    """控制面板"""
    def __init__(self, system, main_window):
        super().__init__()
        self.system = system
        self.main_window = main_window
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 标题
        title = QLabel("系统控制")
        title.setStyleSheet("font-size: 16pt; font-weight: bold; color: #ffffff; margin: 10px;")
        layout.addWidget(title)
        
        # 系统控制按钮
        control_layout = QGridLayout()
        
        self.start_btn = QPushButton("启动系统")
        self.stop_btn = QPushButton("关闭系统")
        self.auto_btn = QPushButton("自动模式")
        self.manual_btn = QPushButton("手动模式")
        self.emergency_btn = QPushButton("紧急协议")
        self.reset_btn = QPushButton("重置系统")
        
        # 设置按钮样式
        buttons = [self.start_btn, self.stop_btn, self.auto_btn, self.manual_btn, self.emergency_btn, self.reset_btn]
        for btn in buttons:
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #2d5278;
                    color: white;
                    border: 1px solid #4a7bab;
                    padding: 8px;
                    font-size: 11pt;
                    border-radius: 5px;
                }
                QPushButton:hover {
                    background-color: #3a68a0;
                }
                QPushButton:pressed {
                    background-color: #1e3a5c;
                }
            """)
        
        # 特殊按钮样式
        self.emergency_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff6464;
                color: white;
                border: 1px solid #ff8c8c;
                padding: 8px;
                font-size: 11pt;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #ff8c8c;
            }
            QPushButton:pressed {
                background-color: #cc5050;
            }
        """)
        
        # 布局按钮
        control_layout.addWidget(self.start_btn, 0, 0)
        control_layout.addWidget(self.stop_btn, 0, 1)
        control_layout.addWidget(self.auto_btn, 1, 0)
        control_layout.addWidget(self.manual_btn, 1, 1)
        control_layout.addWidget(self.emergency_btn, 2, 0, 1, 2)
        control_layout.addWidget(self.reset_btn, 3, 0, 1, 2)
        
        layout.addLayout(control_layout)
        
        # 系统参数调节
        params_group = QGroupBox("系统参数")
        params_group.setStyleSheet("""
            QGroupBox {
                color: white;
                font-size: 12pt;
                font-weight: bold;
                border: 1px solid #4a7bab;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        params_layout = QVBoxLayout()
        
        # 干扰功率调节
        power_layout = QHBoxLayout()
        power_label = QLabel("干扰功率:")
        power_label.setStyleSheet("color: #cccccc;")
        self.power_slider = QSlider(Qt.Horizontal)
        self.power_slider.setRange(0, 100)
        self.power_slider.setValue(80)
        self.power_value = QLabel("80%")
        self.power_value.setStyleSheet("color: white; min-width: 40px;")
        
        power_layout.addWidget(power_label)
        power_layout.addWidget(self.power_slider)
        power_layout.addWidget(self.power_value)
        params_layout.addLayout(power_layout)
        
        # 检测范围调节
        range_layout = QHBoxLayout()
        range_label = QLabel("检测范围:")
        range_label.setStyleSheet("color: #cccccc;")
        self.range_slider = QSlider(Qt.Horizontal)
        self.range_slider.setRange(100, 1000)
        self.range_slider.setValue(800)
        self.range_value = QLabel("800m")
        self.range_value.setStyleSheet("color: white; min-width: 50px;")
        
        range_layout.addWidget(range_label)
        range_layout.addWidget(self.range_slider)
        range_layout.addWidget(self.range_value)
        params_layout.addLayout(range_layout)
        
        # 威胁阈值调节
        threshold_layout = QHBoxLayout()
        threshold_label = QLabel("威胁阈值:")
        threshold_label.setStyleSheet("color: #cccccc;")
        self.threshold_slider = QSlider(Qt.Horizontal)
        self.threshold_slider.setRange(10, 90)
        self.threshold_slider.setValue(50)
        self.threshold_value = QLabel("0.50")
        self.threshold_value.setStyleSheet("color: white; min-width: 40px;")
        
        threshold_layout.addWidget(threshold_label)
        threshold_layout.addWidget(self.threshold_slider)
        threshold_layout.addWidget(self.threshold_value)
        params_layout.addLayout(threshold_layout)
        
        params_group.setLayout(params_layout)
        layout.addWidget(params_group)
        
        layout.addStretch()
        self.setLayout(layout)
        self.setStyleSheet("background-color: #192841; border: 2px solid #2d5278; padding: 10px;")
        
        # 连接信号
        self.connect_signals()
    
    def connect_signals(self):
        """连接信号和槽"""
        self.start_btn.clicked.connect(self.start_system)
        self.stop_btn.clicked.connect(self.stop_system)
        self.auto_btn.clicked.connect(self.set_auto_mode)
        self.manual_btn.clicked.connect(self.set_manual_mode)
        self.emergency_btn.clicked.connect(self.emergency_protocol)
        self.reset_btn.clicked.connect(self.reset_system)
        
        self.power_slider.valueChanged.connect(self.update_power)
        self.range_slider.valueChanged.connect(self.update_range)
        self.threshold_slider.valueChanged.connect(self.update_threshold)
    
    def start_system(self):
        """启动系统"""
        self.system.system_active = True
        self.system.data_recorder.record_event("SYSTEM_START", "手动启动系统", 1)
        self.main_window.log_message("系统已启动")
    
    def stop_system(self):
        """关闭系统"""
        self.system.system_active = False
        self.system.data_recorder.record_event("SYSTEM_STOP", "手动关闭系统", 1)
        self.main_window.log_message("系统已关闭")
    
    def set_auto_mode(self):
        """设置自动模式"""
        self.system.auto_mode = True
        self.system.data_recorder.record_event("MODE_CHANGE", "切换到自动模式", 1)
        self.main_window.log_message("切换到自动模式")
    
    def set_manual_mode(self):
        """设置手动模式"""
        self.system.auto_mode = False
        self.system.data_recorder.record_event("MODE_CHANGE", "切换到手动模式", 1)
        self.main_window.log_message("切换到手动模式")
    
    def emergency_protocol(self):
        """紧急协议"""
        reply = QMessageBox.question(self, "确认紧急协议", 
                                   "确定要启动紧急反制协议吗？这将对所有检测到的无人机实施最大功率干扰。",
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.system.emergency_protocol()
            self.main_window.log_message("紧急反制协议已启动", "warning")
    
    def reset_system(self):
        """重置系统"""
        reply = QMessageBox.question(self, "确认重置", 
                                   "确定要重置系统吗？这将清除所有当前数据。",
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.main_window.reset_system()
            self.main_window.log_message("系统已重置")
    
    def update_power(self, value):
        """更新干扰功率"""
        self.system.interference_power = value
        self.power_value.setText(f"{value}%")
    
    def update_range(self, value):
        """更新检测范围"""
        self.system.detection_range = value
        self.system.sensor_system.radar_range = value
        self.range_value.setText(f"{value}m")
    
    def update_threshold(self, value):
        """更新威胁阈值"""
        threshold = value / 100.0
        self.system.threat_threshold = threshold
        self.threshold_value.setText(f"{threshold:.2f}")

class DroneListWidget(QWidget):
    """无人机列表组件"""
    def __init__(self, system, main_window):
        super().__init__()
        self.system = system
        self.main_window = main_window
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 标题
        title = QLabel("无人机监控列表")
        title.setStyleSheet("font-size: 16pt; font-weight: bold; color: #ffffff; margin: 10px;")
        layout.addWidget(title)
        
        # 表格
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(["ID", "型号", "类型", "威胁级别", "距离", "信号强度", "状态", "操作"])
        
        # 设置表格样式
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #192841;
                color: white;
                gridline-color: #2d5278;
                font-size: 10pt;
            }
            QTableWidget::item {
                border-bottom: 1px solid #2d5278;
                padding: 5px;
            }
            QTableWidget::item:selected {
                background-color: #2d5278;
            }
            QHeaderView::section {
                background-color: #1e3a5c;
                color: white;
                padding: 5px;
                border: none;
                font-weight: bold;
            }
        """)
        
        # 设置列宽
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.ResizeToContents)
        
        layout.addWidget(self.table)
        self.setLayout(layout)
        self.setStyleSheet("background-color: #192841; border: 2px solid #2d5278; padding: 10px;")
    
    def update_table(self):
        """更新表格数据"""
        detected_drones = [d for d in self.system.drones if d.detected]
        self.table.setRowCount(len(detected_drones))
        
        threat_colors = ["#64ff96", "#ffff64", "#ffa040", "#ff6464"]
        
        for row, drone in enumerate(detected_drones):
            # ID
            id_item = QTableWidgetItem(str(drone.id))
            id_item.setForeground(QColor(drone.color[0], drone.color[1], drone.color[2]))
            self.table.setItem(row, 0, id_item)
            
            # 型号
            self.table.setItem(row, 1, QTableWidgetItem(drone.model))
            
            # 类型
            self.table.setItem(row, 2, QTableWidgetItem(drone.type.value))
            
            # 威胁级别
            threat_item = QTableWidgetItem(drone.threat_level.name)
            threat_item.setForeground(QColor(threat_colors[drone.threat_level.value]))
            self.table.setItem(row, 3, threat_item)
            
            # 距离
            distance = np.linalg.norm(drone.position)
            self.table.setItem(row, 4, QTableWidgetItem(f"{distance:.0f}m"))
            
            # 信号强度
            signal_item = QTableWidgetItem(f"{drone.signal_strength:.2f}")
            self.table.setItem(row, 5, signal_item)
            
            # 状态
            status = "反制中" if drone.interfered else "已检测"
            status_item = QTableWidgetItem(status)
            status_item.setForeground(QColor("#ff6464" if drone.interfered else "#64ff96"))
            self.table.setItem(row, 6, status_item)
            
            # 操作按钮
            if not self.system.auto_mode:
                btn = QPushButton("实施干扰" if not drone.interfered else "停止干扰")
                btn.setProperty("drone_id", drone.id)
                btn.clicked.connect(self.toggle_countermeasure)
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #2d5278;
                        color: white;
                        border: none;
                        padding: 5px;
                        font-size: 9pt;
                        border-radius: 3px;
                    }
                    QPushButton:hover {
                        background-color: #3a68a0;
                    }
                """)
                self.table.setCellWidget(row, 7, btn)
            else:
                self.table.setItem(row, 7, QTableWidgetItem("自动模式"))
    
    def toggle_countermeasure(self):
        """切换反制状态"""
        btn = self.sender()
        drone_id = btn.property("drone_id")
        
        drone = self.system.drones[drone_id]
        if drone.interfered:
            # 释放干扰
            drone.interfered = False
            drone.active_countermeasures.clear()
            self.main_window.log_message(f"已释放对无人机 {drone_id} 的干扰")
        else:
            # 实施干扰
            drone.interfered = True
            drone.apply_countermeasure(CounterMeasure.RADIO_JAMMING)
            self.system.data_recorder.record_event(
                "MANUAL_COUNTER", 
                f"手动反制无人机 {drone_id}", 
                2
            )
            self.main_window.log_message(f"已对无人机 {drone_id} 实施干扰", "warning")

class AlertPanel(QWidget):
    """警报面板"""
    def __init__(self, system):
        super().__init__()
        self.system = system
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 标题
        title = QLabel("安全警报")
        title.setStyleSheet("font-size: 16pt; font-weight: bold; color: #ffffff; margin: 10px;")
        layout.addWidget(title)
        
        # 警报级别
        alert_layout = QHBoxLayout()
        alert_label = QLabel("当前警报级别:")
        alert_label.setStyleSheet("color: #cccccc; font-size: 12pt;")
        
        self.alert_level = QLabel("0/100")
        self.alert_level.setStyleSheet("color: #64ff96; font-size: 14pt; font-weight: bold;")
        
        alert_layout.addWidget(alert_label)
        alert_layout.addStretch()
        alert_layout.addWidget(self.alert_level)
        layout.addLayout(alert_layout)
        
        # 警报进度条
        self.alert_bar = QProgressBar()
        self.alert_bar.setRange(0, 100)
        self.alert_bar.setValue(0)
        self.alert_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #2d5278;
                border-radius: 5px;
                text-align: center;
                color: white;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #64ff96, stop:0.3 #ffff64, stop:0.6 #ffa040, stop:1 #ff6464);
            }
        """)
        layout.addWidget(self.alert_bar)
        
        # 活跃警报列表
        alerts_label = QLabel("活跃警报:")
        alerts_label.setStyleSheet("color: #cccccc; font-size: 12pt; margin-top: 10px;")
        layout.addWidget(alerts_label)
        
        self.alerts_list = QTextEdit()
        self.alerts_list.setReadOnly(True)
        self.alerts_list.setMaximumHeight(150)
        self.alerts_list.setStyleSheet("""
            QTextEdit {
                background-color: #0a121e;
                color: white;
                border: 1px solid #2d5278;
                font-size: 10pt;
            }
        """)
        layout.addWidget(self.alerts_list)
        
        layout.addStretch()
        self.setLayout(layout)
        self.setStyleSheet("background-color: #192841; border: 2px solid #2d5278; padding: 10px;")
    
    def update_alerts(self):
        """更新警报显示"""
        # 更新警报级别
        self.alert_level.setText(f"{self.system.alert_level}/100")
        self.alert_bar.setValue(self.system.alert_level)
        
        # 设置颜色
        if self.system.alert_level > 70:
            color = "#ff6464"
        elif self.system.alert_level > 30:
            color = "#ffb464"
        else:
            color = "#64ff96"
        
        self.alert_level.setStyleSheet(f"color: {color}; font-size: 14pt; font-weight: bold;")
        
        # 更新警报列表
        self.alerts_list.clear()
        if self.system.alerts:
            for alert in self.system.alerts:
                drone = self.system.drones[alert['drone_id']]
                threat_colors = ["#64ff96", "#ffff64", "#ffa040", "#ff6464"]
                color = threat_colors[alert['threat_level'].value]
                
                self.alerts_list.append(
                    f"<span style='color: {color}; font-weight: bold;'>●</span> "
                    f"无人机 {alert['drone_id']} - {alert['threat_level'].name}威胁 - "
                    f"距离: {np.linalg.norm(alert['position']):.0f}m"
                )
        else:
            self.alerts_list.setText("无活跃警报")

class ThreatAssessmentPanel(QWidget):
    """威胁评估面板"""
    def __init__(self, system):
        super().__init__()
        self.system = system
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 标题
        title = QLabel("威胁评估")
        title.setStyleSheet("font-size: 16pt; font-weight: bold; color: #ffffff; margin: 10px;")
        layout.addWidget(title)
        
        # 威胁级别说明
        threat_layout = QVBoxLayout()
        
        threat_levels = [
            ("低威胁", "#64ff96", "正常监控"),
            ("中威胁", "#ffff64", "警告跟踪"), 
            ("高威胁", "#ffa040", "主动干扰"),
            ("严重威胁", "#ff6464", "紧急反制")
        ]
        
        for level_name, color, action in threat_levels:
            level_layout = QHBoxLayout()
            
            # 颜色指示
            color_label = QLabel("■")
            color_label.setStyleSheet(f"color: {color}; font-size: 16pt;")
            
            # 级别名称
            name_label = QLabel(level_name)
            name_label.setStyleSheet(f"color: {color}; font-size: 12pt; font-weight: bold;")
            
            # 行动说明
            action_label = QLabel(action)
            action_label.setStyleSheet("color: #cccccc; font-size: 11pt;")
            
            level_layout.addWidget(color_label)
            level_layout.addWidget(name_label)
            level_layout.addStretch()
            level_layout.addWidget(action_label)
            
            threat_layout.addLayout(level_layout)
        
        layout.addLayout(threat_layout)
        
        # 威胁分布
        dist_title = QLabel("当前威胁分布:")
        dist_title.setStyleSheet("color: #cccccc; font-size: 12pt; margin-top: 15px;")
        layout.addWidget(dist_title)
        
        self.threat_distribution = {}
        threat_counts_layout = QVBoxLayout()
        
        for i, level in enumerate(["低", "中", "高", "严重"]):
            level_layout = QHBoxLayout()
            
            label = QLabel(f"{level}威胁:")
            label.setStyleSheet("color: #cccccc; font-size: 11pt;")
            
            count_label = QLabel("0")
            count_label.setStyleSheet(f"color: {threat_levels[i][1]}; font-size: 11pt; font-weight: bold;")
            
            # 简单条形图
            bar = QProgressBar()
            bar.setRange(0, len(self.system.drones))
            bar.setValue(0)
            bar.setMaximumHeight(10)
            bar.setStyleSheet(f"""
                QProgressBar {{
                    border: none;
                    background-color: #0a121e;
                }}
                QProgressBar::chunk {{
                    background-color: {threat_levels[i][1]};
                }}
            """)
            
            level_layout.addWidget(label)
            level_layout.addWidget(count_label)
            level_layout.addWidget(bar)
            level_layout.setStretchFactor(bar, 1)
            
            threat_counts_layout.addLayout(level_layout)
            self.threat_distribution[level] = (count_label, bar)
        
        layout.addLayout(threat_counts_layout)
        layout.addStretch()
        self.setLayout(layout)
        self.setStyleSheet("background-color: #192841; border: 2px solid #2d5278; padding: 10px;")
    
    def update_distribution(self):
        """更新威胁分布"""
        threat_counts = [0, 0, 0, 0]
        for drone in self.system.drones:
            if drone.detected:
                threat_counts[drone.threat_level.value] += 1
        
        levels = ["低", "中", "高", "严重"]
        for i, level in enumerate(levels):
            count_label, bar = self.threat_distribution[level]
            count_label.setText(str(threat_counts[i]))
            bar.setValue(threat_counts[i])

class SystemMonitor(QWidget):
    """系统监控面板"""
    def __init__(self, system):
        super().__init__()
        self.system = system
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 标题
        title = QLabel("系统性能监控")
        title.setStyleSheet("font-size: 16pt; font-weight: bold; color: #ffffff; margin: 10px;")
        layout.addWidget(title)
        
        # 性能指标
        metrics_layout = QGridLayout()
        
        # CPU使用率
        cpu_label = QLabel("CPU使用率:")
        cpu_label.setStyleSheet("color: #cccccc;")
        self.cpu_bar = QProgressBar()
        self.cpu_bar.setRange(0, 100)
        self.cpu_bar.setValue(0)
        
        # 内存使用率
        memory_label = QLabel("内存使用率:")
        memory_label.setStyleSheet("color: #cccccc;")
        self.memory_bar = QProgressBar()
        self.memory_bar.setRange(0, 100)
        self.memory_bar.setValue(0)
        
        # 网络流量
        network_label = QLabel("网络流量:")
        network_label.setStyleSheet("color: #cccccc;")
        self.network_value = QLabel("0 KB/s")
        self.network_value.setStyleSheet("color: white;")
        
        # 磁盘使用率
        disk_label = QLabel("磁盘使用率:")
        disk_label.setStyleSheet("color: #cccccc;")
        self.disk_bar = QProgressBar()
        self.disk_bar.setRange(0, 100)
        self.disk_bar.setValue(0)
        
        metrics_layout.addWidget(cpu_label, 0, 0)
        metrics_layout.addWidget(self.cpu_bar, 0, 1)
        metrics_layout.addWidget(memory_label, 1, 0)
        metrics_layout.addWidget(self.memory_bar, 1, 1)
        metrics_layout.addWidget(network_label, 2, 0)
        metrics_layout.addWidget(self.network_value, 2, 1)
        metrics_layout.addWidget(disk_label, 3, 0)
        metrics_layout.addWidget(self.disk_bar, 3, 1)
        
        layout.addLayout(metrics_layout)
        
        # 设置进度条样式
        for bar in [self.cpu_bar, self.memory_bar, self.disk_bar]:
            bar.setStyleSheet("""
                QProgressBar {
                    border: 1px solid #2d5278;
                    border-radius: 3px;
                    text-align: center;
                    color: white;
                }
                QProgressBar::chunk {
                    background-color: #2d5278;
                }
            """)
        
        layout.addStretch()
        self.setLayout(layout)
        self.setStyleSheet("background-color: #192841; border: 2px solid #2d5278; padding: 10px;")
    
    def update_metrics(self):
        """更新性能指标"""
        # 模拟系统性能数据
        import psutil
        try:
            # CPU使用率
            cpu_percent = psutil.cpu_percent()
            self.cpu_bar.setValue(int(cpu_percent))
            
            # 内存使用率
            memory_percent = psutil.virtual_memory().percent
            self.memory_bar.setValue(int(memory_percent))
            
            # 网络流量（简化）
            network_io = psutil.net_io_counters()
            bytes_sent = network_io.bytes_sent / 1024
            self.network_value.setText(f"{bytes_sent:.0f} KB/s")
            
            # 磁盘使用率
            disk_percent = psutil.disk_usage('.').percent
            self.disk_bar.setValue(int(disk_percent))
            
        except ImportError:
            # 如果没有psutil，使用模拟数据
            self.cpu_bar.setValue(random.randint(10, 40))
            self.memory_bar.setValue(random.randint(30, 70))
            self.network_value.setText(f"{random.randint(100, 500)} KB/s")
            self.disk_bar.setValue(random.randint(20, 60))

class LogPanel(QWidget):
    """日志面板"""
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 标题
        title = QLabel("系统日志")
        title.setStyleSheet("font-size: 16pt; font-weight: bold; color: #ffffff; margin: 10px;")
        layout.addWidget(title)
        
        # 日志文本框
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #0a121e;
                color: #cccccc;
                border: 1px solid #2d5278;
                font-family: 'Courier New';
                font-size: 10pt;
            }
        """)
        layout.addWidget(self.log_text)
        
        # 控制按钮
        button_layout = QHBoxLayout()
        self.clear_btn = QPushButton("清空日志")
        self.save_btn = QPushButton("保存日志")
        
        for btn in [self.clear_btn, self.save_btn]:
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #2d5278;
                    color: white;
                    border: none;
                    padding: 5px 10px;
                    font-size: 10pt;
                }
                QPushButton:hover {
                    background-color: #3a68a0;
                }
            """)
        
        button_layout.addWidget(self.clear_btn)
        button_layout.addWidget(self.save_btn)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
        self.setStyleSheet("background-color: #192841; border: 2px solid #2d5278; padding: 10px;")
        
        # 连接信号
        self.clear_btn.clicked.connect(self.clear_log)
        self.save_btn.clicked.connect(self.save_log)
    
    def add_log(self, message, level="info"):
        """添加日志消息"""
        timestamp = QDateTime.currentDateTime().toString("hh:mm:ss")
        
        if level == "warning":
            color = "#ffb464"
        elif level == "error":
            color = "#ff6464"
        else:
            color = "#64ff96"
        
        log_entry = f"<span style='color: #888888;'>[{timestamp}]</span> <span style='color: {color};'>{message}</span>"
        self.log_text.append(log_entry)
        
        # 自动滚动到底部
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def clear_log(self):
        """清空日志"""
        self.log_text.clear()
    
    def save_log(self):
        """保存日志到文件"""
        from datetime import datetime
        filename = f"drone_defense_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("<html><head><meta charset='utf-8'><title>无人机反制系统日志</title></head><body>")
                f.write(self.log_text.toHtml())
                f.write("</body></html>")
            
            self.add_log(f"日志已保存到: {filename}")
        except Exception as e:
            self.add_log(f"保存日志失败: {str(e)}", "error")

class MainWindow(QMainWindow):
    """主窗口"""
    def __init__(self):
        super().__init__()
        self.system = AdvancedCounterDroneSystem()
        self.init_ui()
        self.setup_timers()
        
    def init_ui(self):
        self.setWindowTitle("高级PX4无人机反制系统 v2.0")
        self.setGeometry(100, 100, 1600, 1000)
        
        # 设置深色主题
        self.setStyleSheet("""
            QMainWindow {
                background-color: #0a121e;
            }
            QWidget {
                background-color: #0a121e;
                color: white;
            }
        """)
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QHBoxLayout()
        central_widget.setLayout(main_layout)
        
        # 左侧面板
        left_panel = QVBoxLayout()
        left_panel.setSpacing(10)
        
        # 雷达显示
        self.radar_widget = RadarWidget(self.system)
        left_panel.addWidget(self.radar_widget)
        
        # 频谱显示
        self.spectrum_widget = SpectrumWidget(self.system)
        left_panel.addWidget(self.spectrum_widget)
        
        # 右侧面板
        right_panel = QSplitter(Qt.Vertical)
        
        # 顶部右侧 - 状态和控制
        top_right = QHBoxLayout()
        top_right_widget = QWidget()
        top_right_widget.setLayout(top_right)
        
        self.status_panel = StatusPanel(self.system)
        self.control_panel = ControlPanel(self.system, self)
        
        top_right.addWidget(self.status_panel)
        top_right.addWidget(self.control_panel)
        
        # 中部右侧 - 无人机列表和警报
        middle_right = QHBoxLayout()
        middle_right_widget = QWidget()
        middle_right_widget.setLayout(middle_right)
        
        self.drone_list = DroneListWidget(self.system, self)
        self.alert_panel = AlertPanel(self.system)
        
        middle_right.addWidget(self.drone_list)
        middle_right.addWidget(self.alert_panel)
        
        # 底部右侧 - 威胁评估和系统监控
        bottom_right = QHBoxLayout()
        bottom_right_widget = QWidget()
        bottom_right_widget.setLayout(bottom_right)
        
        self.threat_panel = ThreatAssessmentPanel(self.system)
        self.monitor_panel = SystemMonitor(self.system)
        
        bottom_right.addWidget(self.threat_panel)
        bottom_right.addWidget(self.monitor_panel)
        
        # 添加到右侧分割器
        right_panel.addWidget(top_right_widget)
        right_panel.addWidget(middle_right_widget)
        right_panel.addWidget(bottom_right_widget)
        right_panel.setSizes([300, 300, 200])
        
        # 添加到主布局
        main_layout.addLayout(left_panel, 2)
        main_layout.addWidget(right_panel, 1)
        
        # 创建底部日志面板
        self.log_panel = LogPanel()
        self.setup_dock_widget()
        
        # 状态栏
        self.statusBar().showMessage("系统就绪")
        
        # 添加菜单栏
        self.setup_menu()
    
    def setup_dock_widget(self):
        """设置停靠窗口"""
        from PyQt5.QtWidgets import QDockWidget
        
        dock = QDockWidget("系统日志", self)
        dock.setWidget(self.log_panel)
        dock.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)
        self.addDockWidget(Qt.BottomDockWidgetArea, dock)
    
    def setup_menu(self):
        """设置菜单栏"""
        menubar = self.menuBar()
        menubar.setStyleSheet("""
            QMenuBar {
                background-color: #192841;
                color: white;
                border: none;
            }
            QMenuBar::item {
                background-color: transparent;
                padding: 5px 10px;
            }
            QMenuBar::item:selected {
                background-color: #2d5278;
            }
            QMenu {
                background-color: #192841;
                color: white;
                border: 1px solid #2d5278;
            }
            QMenu::item {
                padding: 5px 20px;
            }
            QMenu::item:selected {
                background-color: #2d5278;
            }
        """)
        
        # 文件菜单
        file_menu = menubar.addMenu("文件")
        
        new_action = file_menu.addAction("新建")
        save_action = file_menu.addAction("保存配置")
        load_action = file_menu.addAction("加载配置")
        file_menu.addSeparator()
        exit_action = file_menu.addAction("退出")
        
        # 视图菜单
        view_menu = menubar.addMenu("视图")
        view_menu.addAction("全屏模式")
        view_menu.addAction("重置布局")
        
        # 帮助菜单
        help_menu = menubar.addMenu("帮助")
        help_menu.addAction("用户手册")
        help_menu.addAction("关于")
        
        # 连接动作
        exit_action.triggered.connect(self.close)
    
    def setup_timers(self):
        """设置定时器"""
        # 系统更新定时器 (30Hz)
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_system)
        self.update_timer.start(33)  # ~30Hz
        
        # UI更新定时器 (10Hz)
        self.ui_timer = QTimer()
        self.ui_timer.timeout.connect(self.update_ui)
        self.ui_timer.start(100)  # 10Hz
        
        # 状态栏更新定时器 (1Hz)
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_status_bar)
        self.status_timer.start(1000)  # 1Hz
    
    def update_system(self):
        """更新系统状态"""
        if self.system.system_active:
            self.system.update()
    
    def update_ui(self):
        """更新UI组件"""
        # 更新雷达和频谱
        self.radar_widget.update()
        self.spectrum_widget.update()
        
        # 更新状态面板
        self.status_panel.update_status()
        
        # 更新无人机列表
        self.drone_list.update_table()
        
        # 更新警报面板
        self.alert_panel.update_alerts()
        
        # 更新威胁评估
        self.threat_panel.update_distribution()
        
        # 更新系统监控
        self.monitor_panel.update_metrics()
    
    def update_status_bar(self):
        """更新状态栏"""
        status = self.system.get_system_status()
        detected = status['detected_drones']
        total = status['total_drones']
        alert_level = status['alert_level']
        
        timestamp = QDateTime.currentDateTime().toString("yyyy-MM-dd hh:mm:ss")
        
        if alert_level > 70:
            status_text = f"严重警报 - 检测到 {detected}/{total} 个目标 - {timestamp}"
        elif alert_level > 30:
            status_text = f"中等警报 - 检测到 {detected}/{total} 个目标 - {timestamp}"
        else:
            status_text = f"系统正常 - 检测到 {detected}/{total} 个目标 - {timestamp}"
        
        self.statusBar().showMessage(status_text)
    
    def log_message(self, message, level="info"):
        """记录日志消息"""
        self.log_panel.add_log(message, level)
        
        # 更新状态栏显示重要消息
        if level in ["warning", "error"]:
            self.statusBar().showMessage(f"警告: {message}", 5000)
    
    def reset_system(self):
        """重置系统"""
        self.system = AdvancedCounterDroneSystem()
        
        # 更新所有组件的系统引用
        self.radar_widget.system = self.system
        self.spectrum_widget.system = self.system
        self.status_panel.system = self.system
        self.control_panel.system = self.system
        self.drone_list.system = self.system
        self.alert_panel.system = self.system
        self.threat_panel.system = self.system
        self.monitor_panel.system = self.system
        
        self.log_message("系统已重置")
    
    def closeEvent(self, event):
        """关闭事件处理"""
        reply = QMessageBox.question(self, "确认退出", 
                                   "确定要退出无人机反制系统吗？",
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            # 记录系统关闭事件
            self.system.data_recorder.record_event("SYSTEM_SHUTDOWN", "系统正常关闭", 1)
            event.accept()
        else:
            event.ignore()

def main():
    """主函数"""
    app = QApplication(sys.argv)
    
    # 设置应用程序样式
    app.setStyle('Fusion')
    
    # 创建并显示主窗口
    window = MainWindow()
    window.show()
    
    # 记录启动日志
    window.log_message("高级PX4无人机反制系统已启动")
    window.log_message("系统初始化完成，开始监控...")
    
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()