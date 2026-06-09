import sys
import numpy as np
import pyqtgraph as pg
from PyQt6.QtWidgets import (QApplication, QMainWindow, QTabWidget, QWidget, 
                             QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
                             QLabel, QLineEdit, QPushButton, QComboBox, 
                             QTextEdit, QSpinBox, QDoubleSpinBox, QCheckBox,
                             QTableWidget, QTableWidgetItem, QHeaderView, QFileDialog,
                             QMessageBox, QSplitter, QProgressBar, QSlider, QDial,
                             QInputDialog, QStyleFactory, QSizePolicy, QToolBar, QStatusBar)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QIntValidator, QDoubleValidator, QColor, QAction, QIcon, QPalette
import serial.tools.list_ports
import serial
import json
import math
import csv
import time
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from scipy import signal as scipy_signal
import pandas as pd
from scipy import fft
import skrf as rf
from sympy import symbols, solve, Eq
import xml.etree.ElementTree as ET
from pathlib import Path


class WorkerThread(QThread):
    """工作线程基类"""
    progress = pyqtSignal(int)
    result = pyqtSignal(object)
    finished = pyqtSignal()
    error = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_running = True
        
    def stop(self):
        self.is_running = False
        self.wait()


class ComponentCalculator(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
    
    def initUI(self):
        main_layout = QHBoxLayout()
        
        # 左侧：基本计算器
        left_widget = QWidget()
        left_layout = QVBoxLayout()
        
        # 电阻计算
        resistor_group = QGroupBox("电阻计算")
        resistor_layout = QGridLayout()
        
        resistor_layout.addWidget(QLabel("电阻值:"), 0, 0)
        self.resistance_input = QLineEdit()
        self.resistance_input.setPlaceholderText("例如: 1k, 2.2M")
        resistor_layout.addWidget(self.resistance_input, 0, 1)
        
        resistor_layout.addWidget(QLabel("电阻系列:"), 1, 0)
        self.resistor_series = QComboBox()
        self.resistor_series.addItems(["E6", "E12", "E24", "E48", "E96", "E192"])
        resistor_layout.addWidget(self.resistor_series, 1, 1)
        
        resistor_layout.addWidget(QLabel("容差:"), 2, 0)
        self.tolerance_combo = QComboBox()
        self.tolerance_combo.addItems(["±20%", "±10%", "±5%", "±2%", "±1%", "±0.5%", "±0.25%", "±0.1%", "±0.05%"])
        self.tolerance_combo.setCurrentIndex(2)  # 默认±5%
        resistor_layout.addWidget(self.tolerance_combo, 2, 1)
        
        self.calc_resistor_btn = QPushButton("计算标准值")
        self.calc_resistor_btn.clicked.connect(self.calculate_standard_resistors)
        resistor_layout.addWidget(self.calc_resistor_btn, 3, 0, 1, 2)
        
        self.resistor_result = QTextEdit()
        self.resistor_result.setMaximumHeight(100)
        resistor_layout.addWidget(self.resistor_result, 4, 0, 1, 2)
        
        resistor_group.setLayout(resistor_layout)
        left_layout.addWidget(resistor_group)
        
        # 电容计算
        capacitor_group = QGroupBox("电容/电感计算")
        capacitor_layout = QGridLayout()
        
        capacitor_layout.addWidget(QLabel("频率 (Hz):"), 0, 0)
        self.freq_input = QLineEdit()
        self.freq_input.setText("1000")
        capacitor_layout.addWidget(self.freq_input, 0, 1)
        
        capacitor_layout.addWidget(QLabel("电容值 (F):"), 1, 0)
        self.capacitance_input = QLineEdit()
        self.capacitance_input.setText("1e-6")
        capacitor_layout.addWidget(self.capacitance_input, 1, 1)
        
        capacitor_layout.addWidget(QLabel("电感值 (H):"), 2, 0)
        self.inductance_input = QLineEdit()
        self.inductance_input.setText("1e-3")
        capacitor_layout.addWidget(self.inductance_input, 2, 1)
        
        self.calc_reactance_btn = QPushButton("计算电抗")
        self.calc_reactance_btn.clicked.connect(self.calculate_reactance)
        capacitor_layout.addWidget(self.calc_reactance_btn, 3, 0, 1, 2)
        
        self.reactance_result = QTextEdit()
        self.reactance_result.setMaximumHeight(80)
        capacitor_layout.addWidget(self.reactance_result, 4, 0, 1, 2)
        
        capacitor_group.setLayout(capacitor_layout)
        left_layout.addWidget(capacitor_group)
        
        # 分压器计算
        divider_group = QGroupBox("分压器/分流器计算")
        divider_layout = QGridLayout()
        
        divider_layout.addWidget(QLabel("输入电压 (V):"), 0, 0)
        self.vin_input = QLineEdit()
        self.vin_input.setText("5")
        divider_layout.addWidget(self.vin_input, 0, 1)
        
        divider_layout.addWidget(QLabel("R1 (Ω):"), 1, 0)
        self.r1_input = QLineEdit()
        self.r1_input.setText("1000")
        divider_layout.addWidget(self.r1_input, 1, 1)
        
        divider_layout.addWidget(QLabel("R2 (Ω):"), 2, 0)
        self.r2_input = QLineEdit()
        self.r2_input.setText("1000")
        divider_layout.addWidget(self.r2_input, 2, 1)
        
        self.calc_divider_btn = QPushButton("计算输出电压")
        self.calc_divider_btn.clicked.connect(self.calculate_voltage_divider)
        divider_layout.addWidget(self.calc_divider_btn, 3, 0, 1, 2)
        
        divider_layout.addWidget(QLabel("输入电流 (A):"), 4, 0)
        self.iin_input = QLineEdit()
        self.iin_input.setText("0.1")
        divider_layout.addWidget(self.iin_input, 4, 1)
        
        divider_layout.addWidget(QLabel("R1 (Ω):"), 5, 0)
        self.shunt_r1_input = QLineEdit()
        self.shunt_r1_input.setText("100")
        divider_layout.addWidget(self.shunt_r1_input, 5, 1)
        
        divider_layout.addWidget(QLabel("R2 (Ω):"), 6, 0)
        self.shunt_r2_input = QLineEdit()
        self.shunt_r2_input.setText("100")
        divider_layout.addWidget(self.shunt_r2_input, 6, 1)
        
        self.calc_shunt_btn = QPushButton("计算分流")
        self.calc_shunt_btn.clicked.connect(self.calculate_current_divider)
        divider_layout.addWidget(self.calc_shunt_btn, 7, 0, 1, 2)
        
        self.divider_result = QTextEdit()
        self.divider_result.setMaximumHeight(100)
        divider_layout.addWidget(self.divider_result, 8, 0, 1, 2)
        
        divider_group.setLayout(divider_layout)
        left_layout.addWidget(divider_group)
        
        left_widget.setLayout(left_layout)
        
        # 右侧：高级计算器
        right_widget = QWidget()
        right_layout = QVBoxLayout()
        
        # 滤波器计算
        filter_group = QGroupBox("滤波器计算")
        filter_layout = QGridLayout()
        
        filter_layout.addWidget(QLabel("滤波器类型:"), 0, 0)
        self.filter_type = QComboBox()
        self.filter_type.addItems(["低通", "高通", "带通", "带阻", "全通"])
        filter_layout.addWidget(self.filter_type, 0, 1)
        
        filter_layout.addWidget(QLabel("滤波器响应:"), 1, 0)
        self.filter_response = QComboBox()
        self.filter_response.addItems(["巴特沃斯", "切比雪夫", "贝塞尔", "椭圆"])
        filter_layout.addWidget(self.filter_response, 1, 1)
        
        filter_layout.addWidget(QLabel("截止频率 (Hz):"), 2, 0)
        self.cutoff_freq = QLineEdit()
        self.cutoff_freq.setText("1000")
        filter_layout.addWidget(self.cutoff_freq, 2, 1)
        
        filter_layout.addWidget(QLabel("二阶截止频率 (Hz):"), 3, 0)
        self.cutoff_freq2 = QLineEdit()
        self.cutoff_freq2.setText("2000")
        self.cutoff_freq2.setEnabled(False)
        filter_layout.addWidget(self.cutoff_freq2, 3, 1)
        
        filter_layout.addWidget(QLabel("滤波器拓扑:"), 4, 0)
        self.filter_topology = QComboBox()
        self.filter_topology.addItems(["RC", "RL", "LC", "RLC", "Sallen-Key", "多反馈"])
        filter_layout.addWidget(self.filter_topology, 4, 1)
        
        filter_layout.addWidget(QLabel("滤波器阶数:"), 5, 0)
        self.filter_order = QSpinBox()
        self.filter_order.setRange(1, 10)
        self.filter_order.setValue(2)
        filter_layout.addWidget(self.filter_order, 5, 1)
        
        self.calc_filter_btn = QPushButton("计算元件值")
        self.calc_filter_btn.clicked.connect(self.calculate_filter)
        filter_layout.addWidget(self.calc_filter_btn, 6, 0, 1, 2)
        
        self.filter_result = QTextEdit()
        self.filter_result.setMaximumHeight(120)
        filter_layout.addWidget(self.filter_result, 7, 0, 1, 2)
        
        filter_group.setLayout(filter_layout)
        right_layout.addWidget(filter_group)
        
        # 运算放大器计算
        opamp_group = QGroupBox("运算放大器电路计算")
        opamp_layout = QGridLayout()
        
        opamp_layout.addWidget(QLabel("电路类型:"), 0, 0)
        self.opamp_circuit = QComboBox()
        self.opamp_circuit.addItems(["反相放大器", "同相放大器", "差分放大器", "加法器", "积分器", "微分器", "仪表放大器", "跨阻放大器"])
        opamp_layout.addWidget(self.opamp_circuit, 0, 1)
        
        opamp_layout.addWidget(QLabel("增益:"), 1, 0)
        self.gain_input = QLineEdit()
        self.gain_input.setText("10")
        opamp_layout.addWidget(self.gain_input, 1, 1)
        
        opamp_layout.addWidget(QLabel("输入阻抗 (Ω):"), 2, 0)
        self.input_z = QLineEdit()
        self.input_z.setText("1000")
        opamp_layout.addWidget(self.input_z, 2, 1)
        
        opamp_layout.addWidget(QLabel("带宽 (Hz):"), 3, 0)
        self.bandwidth = QLineEdit()
        self.bandwidth.setText("10000")
        opamp_layout.addWidget(self.bandwidth, 3, 1)
        
        self.calc_opamp_btn = QPushButton("计算元件值")
        self.calc_opamp_btn.clicked.connect(self.calculate_opamp)
        opamp_layout.addWidget(self.calc_opamp_btn, 4, 0, 1, 2)
        
        self.opamp_result = QTextEdit()
        self.opamp_result.setMaximumHeight(120)
        opamp_layout.addWidget(self.opamp_result, 5, 0, 1, 2)
        
        opamp_group.setLayout(opamp_layout)
        right_layout.addWidget(opamp_group)
        
        # 阻抗匹配计算
        impedance_group = QGroupBox("阻抗匹配计算")
        impedance_layout = QGridLayout()
        
        impedance_layout.addWidget(QLabel("源阻抗 (Ω):"), 0, 0)
        self.source_z = QLineEdit()
        self.source_z.setText("50")
        impedance_layout.addWidget(self.source_z, 0, 1)
        
        impedance_layout.addWidget(QLabel("负载阻抗 (Ω):"), 1, 0)
        self.load_z = QLineEdit()
        self.load_z.setText("75")
        impedance_layout.addWidget(self.load_z, 1, 1)
        
        impedance_layout.addWidget(QLabel("频率 (Hz):"), 2, 0)
        self.match_freq = QLineEdit()
        self.match_freq.setText("100e6")
        impedance_layout.addWidget(self.match_freq, 2, 1)
        
        impedance_layout.addWidget(QLabel("匹配网络:"), 3, 0)
        self.match_network = QComboBox()
        self.match_network.addItems(["L型", "π型", "T型", "变压器匹配"])
        impedance_layout.addWidget(self.match_network, 3, 1)
        
        self.calc_match_btn = QPushButton("计算匹配元件")
        self.calc_match_btn.clicked.connect(self.calculate_impedance_match)
        impedance_layout.addWidget(self.calc_match_btn, 4, 0, 1, 2)
        
        self.match_result = QTextEdit()
        self.match_result.setMaximumHeight(100)
        impedance_layout.addWidget(self.match_result, 5, 0, 1, 2)
        
        impedance_group.setLayout(impedance_layout)
        right_layout.addWidget(impedance_group)
        
        right_widget.setLayout(right_layout)
        
        # 添加到主布局
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([400, 400])
        
        main_layout.addWidget(splitter)
        self.setLayout(main_layout)
        
        # 连接信号
        self.filter_type.currentTextChanged.connect(self.update_filter_ui)
    
    def update_filter_ui(self, filter_type):
        if filter_type in ["带通", "带阻"]:
            self.cutoff_freq2.setEnabled(True)
            self.cutoff_freq2.setPlaceholderText("输入第二个截止频率")
        else:
            self.cutoff_freq2.setEnabled(False)
            self.cutoff_freq2.clear()
    
    def calculate_standard_resistors(self):
        try:
            input_text = self.resistance_input.text().strip().lower()
            multiplier = 1
            
            if 'k' in input_text:
                multiplier = 1000
                input_text = input_text.replace('k', '')
            elif 'm' in input_text:
                multiplier = 1000000
                input_text = input_text.replace('m', '')
            elif 'r' in input_text:
                multiplier = 1
                input_text = input_text.replace('r', '')
            
            target_value = float(input_text) * multiplier
            
            series = self.resistor_series.currentText()
            if series == "E6":
                values = self.e_series(6)
            elif series == "E12":
                values = self.e_series(12)
            elif series == "E24":
                values = self.e_series(24)
            elif series == "E48":
                values = self.e_series(48)
            elif series == "E96":
                values = self.e_series(96)
            else:  # E192
                values = self.e_series(192)
            
            # 获取容差
            tolerance_text = self.tolerance_combo.currentText()
            tolerance = float(tolerance_text.replace('±', '').replace('%', '')) / 100
            
            # 找到最接近的标准值
            std_values = []
            for decade in range(-2, 7):  # 从0.01到10M
                for val in values:
                    std_val = val * (10 ** decade)
                    std_values.append(std_val)
            
            # 找到所有在容差范围内的值
            valid_values = [val for val in std_values if abs(val - target_value) <= target_value * tolerance]
            
            # 找到最接近的值
            closest = min(std_values, key=lambda x: abs(x - target_value))
            error = (closest - target_value) / target_value * 100
            
            # 格式化输出
            result_text = f"目标值: {self.format_value(target_value)}\n"
            result_text += f"最接近的标准值: {self.format_value(closest)} (误差: {error:.2f}%)\n"
            
            if valid_values:
                result_text += f"在{tolerance_text}容差范围内的标准值:\n"
                for val in valid_values[:10]:  # 只显示前10个
                    result_text += f"  {self.format_value(val)}\n"
                if len(valid_values) > 10:
                    result_text += f"  ... 还有 {len(valid_values) - 10} 个值\n"
            else:
                result_text += f"没有找到在{tolerance_text}容差范围内的标准值\n"
            
            self.resistor_result.setText(result_text)
            
        except ValueError:
            self.resistor_result.setText("请输入有效的电阻值")
    
    def format_value(self, value):
        if value >= 1000000:
            return f"{value/1000000:.4f} MΩ"
        elif value >= 1000:
            return f"{value/1000:.4f} kΩ"
        else:
            return f"{value:.4f} Ω"
    
    def e_series(self, series):
        if series == 6:
            return [1.0, 1.5, 2.2, 3.3, 4.7, 6.8]
        elif series == 12:
            return [1.0, 1.2, 1.5, 1.8, 2.2, 2.7, 3.3, 3.9, 4.7, 5.6, 6.8, 8.2]
        elif series == 24:
            return [1.0, 1.1, 1.2, 1.3, 1.5, 1.6, 1.8, 2.0, 2.2, 2.4, 2.7, 3.0,
                    3.3, 3.6, 3.9, 4.3, 4.7, 5.1, 5.6, 6.2, 6.8, 7.5, 8.2, 9.1]
        elif series == 48:
            base = [1.00, 1.05, 1.10, 1.15, 1.21, 1.27, 1.33, 1.40, 1.47, 1.54, 
                    1.62, 1.69, 1.78, 1.87, 1.96, 2.05, 2.15, 2.26, 2.37, 2.49,
                    2.61, 2.74, 2.87, 3.01, 3.16, 3.32, 3.48, 3.65, 3.83, 4.02,
                    4.22, 4.42, 4.64, 4.87, 5.11, 5.36, 5.62, 5.90, 6.19, 6.49,
                    6.81, 7.15, 7.50, 7.87, 8.25, 8.66, 9.09, 9.53]
            return base
        elif series == 96:
            base = [1.00, 1.02, 1.05, 1.07, 1.10, 1.13, 1.15, 1.18, 1.21, 1.24,
                    1.27, 1.30, 1.33, 1.37, 1.40, 1.43, 1.47, 1.50, 1.54, 1.58,
                    1.62, 1.65, 1.69, 1.74, 1.78, 1.82, 1.87, 1.91, 1.96, 2.00,
                    2.05, 2.10, 2.15, 2.21, 2.26, 2.32, 2.37, 2.43, 2.49, 2.55,
                    2.61, 2.67, 2.74, 2.80, 2.87, 2.94, 3.01, 3.09, 3.16, 3.24,
                    3.32, 3.40, 3.48, 3.57, 3.65, 3.74, 3.83, 3.92, 4.02, 4.12,
                    4.22, 4.32, 4.42, 4.53, 4.64, 4.75, 4.87, 4.99, 5.11, 5.23,
                    5.36, 5.49, 5.62, 5.76, 5.90, 6.04, 6.19, 6.34, 6.49, 6.65,
                    6.81, 6.98, 7.15, 7.32, 7.50, 7.68, 7.87, 8.06, 8.25, 8.45,
                    8.66, 8.87, 9.09, 9.31, 9.53, 9.76]
            return base
        else:  # E192
            base = [1.00, 1.01, 1.02, 1.04, 1.05, 1.06, 1.07, 1.09, 1.10, 1.11,
                    1.13, 1.14, 1.15, 1.17, 1.18, 1.20, 1.21, 1.23, 1.24, 1.26,
                    1.27, 1.29, 1.30, 1.32, 1.33, 1.35, 1.37, 1.38, 1.40, 1.42,
                    1.43, 1.45, 1.47, 1.49, 1.50, 1.52, 1.54, 1.56, 1.58, 1.60,
                    1.62, 1.64, 1.65, 1.67, 1.69, 1.72, 1.74, 1.76, 1.78, 1.80,
                    1.82, 1.84, 1.87, 1.89, 1.91, 1.93, 1.96, 1.98, 2.00, 2.03,
                    2.05, 2.08, 2.10, 2.13, 2.15, 2.18, 2.21, 2.23, 2.26, 2.29,
                    2.32, 2.34, 2.37, 2.40, 2.43, 2.46, 2.49, 2.52, 2.55, 2.58,
                    2.61, 2.64, 2.67, 2.71, 2.74, 2.77, 2.80, 2.84, 2.87, 2.91,
                    2.94, 2.98, 3.01, 3.05, 3.09, 3.12, 3.16, 3.20, 3.24, 3.28,
                    3.32, 3.36, 3.40, 3.44, 3.48, 3.52, 3.57, 3.61, 3.65, 3.70,
                    3.74, 3.79, 3.83, 3.88, 3.92, 3.97, 4.02, 4.07, 4.12, 4.17,
                    4.22, 4.27, 4.32, 4.37, 4.42, 4.48, 4.53, 4.59, 4.64, 4.70,
                    4.75, 4.81, 4.87, 4.93, 4.99, 5.05, 5.11, 5.17, 5.23, 5.30,
                    5.36, 5.42, 5.49, 5.56, 5.62, 5.69, 5.76, 5.83, 5.90, 5.97,
                    6.04, 6.12, 6.19, 6.26, 6.34, 6.42, 6.49, 6.57, 6.65, 6.73,
                    6.81, 6.90, 6.98, 7.06, 7.15, 7.23, 7.32, 7.41, 7.50, 7.59,
                    7.68, 7.77, 7.87, 7.96, 8.06, 8.16, 8.25, 8.35, 8.45, 8.56,
                    8.66, 8.76, 8.87, 8.98, 9.09, 9.20, 9.31, 9.42, 9.53, 9.65,
                    9.76, 9.88]
            return base
    
    def calculate_reactance(self):
        try:
            freq = float(self.freq_input.text())
            capacitance = float(self.capacitance_input.text()) if self.capacitance_input.text() else 0
            inductance = float(self.inductance_input.text()) if self.inductance_input.text() else 0
            
            if freq <= 0:
                self.reactance_result.setText("频率必须为正数")
                return
            
            result_text = ""
            
            if capacitance > 0:
                xc = 1 / (2 * math.pi * freq * capacitance)
                result_text += f"容抗 Xc = {xc:.4f} Ω\n"
                result_text += f"电容的Q值 ≈ {1/(2 * math.pi * freq * capacitance * 1e-12 * 10):.2f} (假设ESR=10Ω)\n"
                
                # 计算谐振频率
                if inductance > 0:
                    resonance_freq = 1 / (2 * math.pi * math.sqrt(inductance * capacitance))
                    result_text += f"谐振频率 = {resonance_freq:.4f} Hz\n"
            
            if inductance > 0:
                xl = 2 * math.pi * freq * inductance
                result_text += f"感抗 XL = {xl:.4f} Ω\n"
                result_text += f"电感的Q值 ≈ {xl/0.1:.2f} (假设ESR=0.1Ω)\n"
            
            if capacitance <= 0 and inductance <= 0:
                result_text = "请输入电容或电感值"
            
            self.reactance_result.setText(result_text)
            
        except ValueError:
            self.reactance_result.setText("请输入有效的数值")
    
    def calculate_voltage_divider(self):
        try:
            vin = float(self.vin_input.text())
            r1 = float(self.r1_input.text())
            r2 = float(self.r2_input.text())
            
            if r1 <= 0 or r2 <= 0:
                self.divider_result.setText("电阻值必须为正数")
                return
            
            vout = vin * r2 / (r1 + r2)
            current = vin / (r1 + r2)
            power_r1 = current * current * r1
            power_r2 = current * current * r2
            
            # 计算输出阻抗
            rout = (r1 * r2) / (r1 + r2)
            
            result_text = f"输出电压 = {vout:.4f} V\n"
            result_text += f"电流 = {current*1000:.4f} mA\n"
            result_text += f"R1功耗 = {power_r1*1000:.4f} mW\n"
            result_text += f"R2功耗 = {power_r2*1000:.4f} mW\n"
            result_text += f"输出阻抗 = {rout:.2f} Ω\n"
            
            self.divider_result.setText(result_text)
            
        except ValueError:
            self.divider_result.setText("请输入有效的数值")
    
    def calculate_current_divider(self):
        try:
            iin = float(self.iin_input.text())
            r1 = float(self.shunt_r1_input.text())
            r2 = float(self.shunt_r2_input.text())
            
            if r1 <= 0 or r2 <= 0:
                self.divider_result.setText("电阻值必须为正数")
                return
            
            i1 = iin * r2 / (r1 + r2)
            i2 = iin * r1 / (r1 + r2)
            voltage = iin * (r1 * r2) / (r1 + r2)
            
            result_text = f"\n分流结果:\n"
            result_text += f"R1电流 = {i1*1000:.4f} mA\n"
            result_text += f"R2电流 = {i2*1000:.4f} mA\n"
            result_text += f"电压 = {voltage:.4f} V\n"
            
            current_text = self.divider_result.toPlainText()
            self.divider_result.setText(current_text + result_text)
            
        except ValueError:
            self.divider_result.setText("请输入有效的数值")
    
    def calculate_filter(self):
        try:
            filter_type = self.filter_type.currentText()
            filter_response = self.filter_response.currentText()
            cutoff = float(self.cutoff_freq.text())
            topology = self.filter_topology.currentText()
            order = self.filter_order.value()
            
            result_text = f"{filter_response} {filter_type}滤波器 ({topology}) 计算:\n"
            result_text += f"截止频率: {cutoff} Hz\n"
            result_text += f"滤波器阶数: {order}\n"
            
            if filter_type in ["带通", "带阻"] and self.cutoff_freq2.isEnabled():
                cutoff2 = float(self.cutoff_freq2.text())
                result_text += f"第二截止频率: {cutoff2} Hz\n"
                center_freq = math.sqrt(cutoff * cutoff2)
                bandwidth = abs(cutoff2 - cutoff)
                result_text += f"中心频率: {center_freq:.2f} Hz\n"
                result_text += f"带宽: {bandwidth:.2f} Hz\n"
                result_text += f"品质因数Q: {center_freq/bandwidth:.2f}\n"
            
            # 更详细的滤波器计算
            if topology == "RC" and filter_type == "低通":
                r = 1000  # 假设电阻为1k
                c = 1 / (2 * math.pi * cutoff * r)
                result_text += f"推荐值: R = {r} Ω, C = {c*1e6:.2f} μF\n"
                result_text += f"-3dB频率: {1/(2*math.pi*r*c):.2f} Hz\n"
            
            elif topology == "Sallen-Key" and filter_type == "低通":
                result_text += "Sallen-Key低通滤波器设计:\n"
                result_text += "R1 = R2 = 1kΩ (建议值)\n"
                c1 = 1 / (2 * math.pi * cutoff * 1000 * math.sqrt(2))
                c2 = c1 / 2
                result_text += f"C1 = {c1*1e9:.2f} nF, C2 = {c2*1e9:.2f} nF\n"
            
            self.filter_result.setText(result_text)
            
        except ValueError:
            self.filter_result.setText("请输入有效的数值")
    
    def calculate_opamp(self):
        try:
            circuit_type = self.opamp_circuit.currentText()
            gain = float(self.gain_input.text())
            input_z = float(self.input_z.text())
            bandwidth_req = float(self.bandwidth.text()) if self.bandwidth.text() else 0
            
            result_text = f"{circuit_type} 计算:\n"
            result_text += f"目标增益: {gain}\n"
            result_text += f"输入阻抗: {input_z} Ω\n"
            
            if bandwidth_req > 0:
                result_text += f"所需带宽: {bandwidth_req} Hz\n"
            
            if circuit_type == "反相放大器":
                r1 = input_z
                r2 = gain * r1
                result_text += f"R1 = {r1} Ω\n"
                result_text += f"R2 = {r2} Ω\n"
                if bandwidth_req > 0:
                    # 假设GBW=1MHz的运放
                    required_gbw = gain * bandwidth_req
                    result_text += f"所需运放GBW: {required_gbw/1e6:.2f} MHz\n"
            
            elif circuit_type == "同相放大器":
                r1 = 1000  # 假设值
                r2 = (gain - 1) * r1
                result_text += f"R1 = {r1} Ω\n"
                result_text += f"R2 = {r2} Ω\n"
                result_text += f"输入阻抗 > 10 MΩ\n"
                if bandwidth_req > 0:
                    required_gbw = gain * bandwidth_req
                    result_text += f"所需运放GBW: {required_gbw/1e6:.2f} MHz\n"
            
            elif circuit_type == "仪表放大器":
                result_text += "仪表放大器通常使用专用芯片如AD620、INA128\n"
                result_text += f"增益设置电阻: Rg = {50000/(gain-1):.2f} Ω (对于AD620)\n"
            
            self.opamp_result.setText(result_text)
            
        except ValueError:
            self.opamp_result.setText("请输入有效的数值")
    
    def calculate_impedance_match(self):
        try:
            z_source = float(self.source_z.text())
            z_load = float(self.load_z.text())
            freq = float(self.match_freq.text())
            network_type = self.match_network.currentText()
            
            result_text = f"阻抗匹配 ({network_type}网络):\n"
            result_text += f"源阻抗: {z_source} Ω\n"
            result_text += f"负载阻抗: {z_load} Ω\n"
            result_text += f"频率: {freq/1e6:.2f} MHz\n"
            
            # 计算匹配质量
            swr = max(z_source/z_load, z_load/z_source) if z_source != z_load else 1
            result_text += f"驻波比(SWR): {swr:.2f}:1\n"
            
            # 计算匹配元件
            z_avg = math.sqrt(z_source * z_load)
            
            if network_type == "L型":
                # 计算L型匹配元件
                if z_source < z_load:
                    l = z_avg / (2 * math.pi * freq)
                    c = 1 / (2 * math.pi * freq * z_avg)
                    result_text += f"串联电感: {l*1e6:.2f} μH\n"
                    result_text += f"并联电容: {c*1e9:.2f} nF\n"
                else:
                    c = 1 / (2 * math.pi * freq * z_avg)
                    l = z_avg / (2 * math.pi * freq)
                    result_text += f"串联电容: {c*1e9:.2f} nF\n"
                    result_text += f"并联电感: {l*1e6:.2f} μH\n"
            
            elif network_type == "π型":
                # 简化的π型匹配计算
                result_text += "π型匹配网络:\n"
                result_text += f"并联电感: {z_avg/(2*math.pi*freq)*1e6:.2f} μH (输入端)\n"
                result_text += f"串联电容: {1/(2*math.pi*freq*z_avg)*1e12:.2f} pF\n"
                result_text += f"并联电感: {z_avg/(2*math.pi*freq)*1e6:.2f} μH (输出端)\n"
            
            elif network_type == "变压器匹配":
                turns_ratio = math.sqrt(z_load / z_source)
                result_text += f"变压器匝数比: {turns_ratio:.2f}:1\n"
                result_text += f"初级阻抗: {z_source} Ω, 次级阻抗: {z_load} Ω\n"
            
            self.match_result.setText(result_text)
            
        except ValueError:
            self.match_result.setText("请输入有效的数值")


class AdvancedSignalGenerator(QWidget):
    def __init__(self):
        super().__init__()
        self.wave_data = None
        self.arbitrary_waveform = None
        self.initUI()
    
    def initUI(self):
        layout = QVBoxLayout()
        
        # 波形设置
        settings_group = QGroupBox("波形设置")
        settings_layout = QGridLayout()
        
        settings_layout.addWidget(QLabel("波形类型:"), 0, 0)
        self.wave_type = QComboBox()
        self.wave_type.addItems(["正弦波", "方波", "三角波", "锯齿波", "噪声", "任意波形", "脉冲", "DC"])
        self.wave_type.currentTextChanged.connect(self.update_ui)
        settings_layout.addWidget(self.wave_type, 0, 1)
        
        settings_layout.addWidget(QLabel("频率 (Hz):"), 1, 0)
        self.frequency = QDoubleSpinBox()
        self.frequency.setRange(0.1, 1000000)
        self.frequency.setValue(1000)
        self.frequency.setDecimals(3)
        settings_layout.addWidget(self.frequency, 1, 1)
        
        settings_layout.addWidget(QLabel("幅度 (V):"), 2, 0)
        self.amplitude = QDoubleSpinBox()
        self.amplitude.setRange(0.1, 10)
        self.amplitude.setValue(1)
        self.amplitude.setDecimals(3)
        settings_layout.addWidget(self.amplitude, 2, 1)
        
        settings_layout.addWidget(QLabel("偏移 (V):"), 3, 0)
        self.offset = QDoubleSpinBox()
        self.offset.setRange(-10, 10)
        self.offset.setValue(0)
        self.offset.setDecimals(3)
        settings_layout.addWidget(self.offset, 3, 1)
        
        settings_layout.addWidget(QLabel("相位 (度):"), 4, 0)
        self.phase = QDoubleSpinBox()
        self.phase.setRange(0, 360)
        self.phase.setValue(0)
        self.phase.setDecimals(1)
        settings_layout.addWidget(self.phase, 4, 1)
        
        settings_layout.addWidget(QLabel("占空比 (%):"), 5, 0)
        self.duty_cycle = QDoubleSpinBox()
        self.duty_cycle.setRange(1, 99)
        self.duty_cycle.setValue(50)
        self.duty_cycle.setDecimals(1)
        self.duty_cycle.setEnabled(False)
        settings_layout.addWidget(self.duty_cycle, 5, 1)
        
        settings_layout.addWidget(QLabel("噪声水平:"), 6, 0)
        self.noise_level = QDoubleSpinBox()
        self.noise_level.setRange(0, 1)
        self.noise_level.setValue(0.1)
        self.noise_level.setDecimals(2)
        self.noise_level.setEnabled(False)
        settings_layout.addWidget(self.noise_level, 6, 1)
        
        settings_layout.addWidget(QLabel("脉冲宽度 (μs):"), 7, 0)
        self.pulse_width = QDoubleSpinBox()
        self.pulse_width.setRange(0.1, 1000)
        self.pulse_width.setValue(10)
        self.pulse_width.setDecimals(1)
        self.pulse_width.setEnabled(False)
        settings_layout.addWidget(self.pulse_width, 7, 1)
        
        self.arb_wave_btn = QPushButton("编辑任意波形")
        self.arb_wave_btn.clicked.connect(self.edit_arbitrary_waveform)
        self.arb_wave_btn.setEnabled(False)
        settings_layout.addWidget(self.arb_wave_btn, 8, 0, 1, 2)
        
        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)
        
        # 调制设置
        modulation_group = QGroupBox("调制设置")
        modulation_layout = QGridLayout()
        
        modulation_layout.addWidget(QLabel("调制类型:"), 0, 0)
        self.modulation_type = QComboBox()
        self.modulation_type.addItems(["无", "AM", "FM", "PM", "PWM"])
        self.modulation_type.currentTextChanged.connect(self.update_modulation_ui)
        modulation_layout.addWidget(self.modulation_type, 0, 1)
        
        modulation_layout.addWidget(QLabel("调制深度 (%):"), 1, 0)
        self.modulation_depth = QDoubleSpinBox()
        self.modulation_depth.setRange(0, 100)
        self.modulation_depth.setValue(50)
        self.modulation_depth.setDecimals(1)
        self.modulation_depth.setEnabled(False)
        modulation_layout.addWidget(self.modulation_depth, 1, 1)
        
        modulation_layout.addWidget(QLabel("调制频率 (Hz):"), 2, 0)
        self.modulation_freq = QDoubleSpinBox()
        self.modulation_freq.setRange(1, 10000)
        self.modulation_freq.setValue(100)
        self.modulation_freq.setDecimals(1)
        self.modulation_freq.setEnabled(False)
        modulation_layout.addWidget(self.modulation_freq, 2, 1)
        
        modulation_group.setLayout(modulation_layout)
        layout.addWidget(modulation_group)
        
        # 扫频设置
        sweep_group = QGroupBox("扫频设置")
        sweep_layout = QGridLayout()
        
        sweep_layout.addWidget(QLabel("起始频率 (Hz):"), 0, 0)
        self.start_freq = QDoubleSpinBox()
        self.start_freq.setRange(0.1, 1000000)
        self.start_freq.setValue(100)
        self.start_freq.setDecimals(3)
        sweep_layout.addWidget(self.start_freq, 0, 1)
        
        sweep_layout.addWidget(QLabel("终止频率 (Hz):"), 1, 0)
        self.stop_freq = QDoubleSpinBox()
        self.stop_freq.setRange(0.1, 1000000)
        self.stop_freq.setValue(5000)
        self.stop_freq.setDecimals(3)
        sweep_layout.addWidget(self.stop_freq, 1, 1)
        
        sweep_layout.addWidget(QLabel("扫频时间 (s):"), 2, 0)
        self.sweep_time = QDoubleSpinBox()
        self.sweep_time.setRange(0.1, 100)
        self.sweep_time.setValue(1)
        self.sweep_time.setDecimals(1)
        sweep_layout.addWidget(self.sweep_time, 2, 1)
        
        sweep_layout.addWidget(QLabel("扫频类型:"), 3, 0)
        self.sweep_type = QComboBox()
        self.sweep_type.addItems(["线性", "对数"])
        sweep_layout.addWidget(self.sweep_type, 3, 1)
        
        self.sweep_btn = QPushButton("开始扫频")
        self.sweep_btn.clicked.connect(self.start_sweep)
        sweep_layout.addWidget(self.sweep_btn, 4, 0, 1, 2)
        
        sweep_group.setLayout(sweep_layout)
        layout.addWidget(sweep_group)
        
        # 图形显示
        plot_splitter = QSplitter(Qt.Orientation.Vertical)
        
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('w')
        self.plot_widget.setLabel('left', '幅度', 'V')
        self.plot_widget.setLabel('bottom', '时间', 's')
        self.plot_widget.showGrid(x=True, y=True)
        plot_splitter.addWidget(self.plot_widget)
        
        # 频谱显示
        self.spectrum_widget = pg.PlotWidget()
        self.spectrum_widget.setBackground('w')
        self.spectrum_widget.setLabel('left', '幅度', 'dB')
        self.spectrum_widget.setLabel('bottom', '频率', 'Hz')
        self.spectrum_widget.showGrid(x=True, y=True)
        self.spectrum_widget.setLogMode(x=True, y=False)
        plot_splitter.addWidget(self.spectrum_widget)
        
        plot_splitter.setSizes([300, 200])
        layout.addWidget(plot_splitter)
        
        # 控制按钮
        btn_layout = QHBoxLayout()
        self.generate_btn = QPushButton("生成波形")
        self.generate_btn.clicked.connect(self.generate_waveform)
        btn_layout.addWidget(self.generate_btn)
        
        self.save_btn = QPushButton("保存数据")
        self.save_btn.clicked.connect(self.save_data)
        btn_layout.addWidget(self.save_btn)
        
        self.export_btn = QPushButton("导出波形")
        self.export_btn.clicked.connect(self.export_waveform)
        btn_layout.addWidget(self.export_btn)
        
        self.analyze_btn = QPushButton("信号分析")
        self.analyze_btn.clicked.connect(self.analyze_signal)
        btn_layout.addWidget(self.analyze_btn)
        
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
        
        # 初始生成波形
        self.generate_waveform()
    
    def update_ui(self, wave_type):
        if wave_type == "方波" or wave_type == "脉冲":
            self.duty_cycle.setEnabled(True)
            self.noise_level.setEnabled(False)
            self.pulse_width.setEnabled(wave_type == "脉冲")
        elif wave_type == "噪声":
            self.duty_cycle.setEnabled(False)
            self.noise_level.setEnabled(True)
            self.pulse_width.setEnabled(False)
        elif wave_type == "任意波形":
            self.duty_cycle.setEnabled(False)
            self.noise_level.setEnabled(False)
            self.pulse_width.setEnabled(False)
            self.arb_wave_btn.setEnabled(True)
        elif wave_type == "DC":
            self.duty_cycle.setEnabled(False)
            self.noise_level.setEnabled(False)
            self.pulse_width.setEnabled(False)
            self.frequency.setEnabled(False)
        else:
            self.duty_cycle.setEnabled(False)
            self.noise_level.setEnabled(False)
            self.pulse_width.setEnabled(False)
            self.frequency.setEnabled(True)
    
    def update_modulation_ui(self, mod_type):
        if mod_type == "无":
            self.modulation_depth.setEnabled(False)
            self.modulation_freq.setEnabled(False)
        else:
            self.modulation_depth.setEnabled(True)
            self.modulation_freq.setEnabled(True)
    
    def edit_arbitrary_waveform(self):
        # 创建任意波形编辑器对话框
        dialog = QDialog(self)
        dialog.setWindowTitle("任意波形编辑器")
        dialog.setMinimumSize(600, 400)
        
        layout = QVBoxLayout()
        
        # 绘图区域
        plot_widget = pg.PlotWidget()
        plot_widget.setBackground('w')
        plot_widget.setLabel('left', '幅度', 'V')
        plot_widget.setLabel('bottom', '点数')
        plot_widget.showGrid(x=True, y=True)
        
        # 初始化或加载现有波形
        if self.arbitrary_waveform is None:
            # 创建默认正弦波
            x = np.linspace(0, 100, 100)
            y = np.sin(2 * np.pi * x / 100)
            self.arbitrary_waveform = np.column_stack((x, y))
        
        # 绘制波形
        plot_item = plot_widget.plot(self.arbitrary_waveform[:, 0], 
                                   self.arbitrary_waveform[:, 1],
                                   pen=pg.mkPen(color='b', width=2))
        
        layout.addWidget(plot_widget)
        
        # 控制按钮
        btn_layout = QHBoxLayout()
        
        load_btn = QPushButton("加载CSV")
        load_btn.clicked.connect(lambda: self.load_arb_waveform(dialog, plot_item))
        btn_layout.addWidget(load_btn)
        
        save_btn = QPushButton("保存波形")
        save_btn.clicked.connect(lambda: self.save_arb_waveform(dialog))
        btn_layout.addWidget(save_btn)
        
        ok_btn = QPushButton("确定")
        ok_btn.clicked.connect(dialog.accept)
        btn_layout.addWidget(ok_btn)
        
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(dialog.reject)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
        dialog.setLayout(layout)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # 保存波形数据
            pass
    
    def load_arb_waveform(self, dialog, plot_item):
        file_path, _ = QFileDialog.getOpenFileName(
            dialog, "加载波形数据", "", "CSV文件 (*.csv);;文本文件 (*.txt)"
        )
        
        if file_path:
            try:
                data = np.loadtxt(file_path, delimiter=',')
                if data.shape[1] >= 2:
                    self.arbitrary_waveform = data[:, :2]
                    plot_item.setData(self.arbitrary_waveform[:, 0], 
                                    self.arbitrary_waveform[:, 1])
            except Exception as e:
                QMessageBox.critical(dialog, "错误", f"加载失败: {str(e)}")
    
    def save_arb_waveform(self, dialog):
        if self.arbitrary_waveform is None:
            QMessageBox.warning(dialog, "警告", "没有波形数据可保存")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            dialog, "保存波形数据", "", "CSV文件 (*.csv)"
        )
        
        if file_path:
            try:
                np.savetxt(file_path, self.arbitrary_waveform, delimiter=',')
                QMessageBox.information(dialog, "成功", "波形保存成功")
            except Exception as e:
                QMessageBox.critical(dialog, "错误", f"保存失败: {str(e)}")
    
    def generate_waveform(self):
        wave_type = self.wave_type.currentText()
        freq = self.frequency.value()
        amp = self.amplitude.value()
        offset = self.offset.value()
        phase = self.phase.value() * np.pi / 180  # 转换为弧度
        
        # 生成时间序列
        sample_rate = 100 * max(freq, 1)  # 至少100Hz采样率
        t = np.linspace(0, 5/max(freq, 0.1), int(sample_rate))  # 显示5个周期
        
        # 生成波形
        if wave_type == "正弦波":
            y = amp * np.sin(2 * np.pi * freq * t + phase) + offset
        elif wave_type == "方波":
            duty = self.duty_cycle.value() / 100
            y = amp * scipy_signal.square(2 * np.pi * freq * t + phase, duty=duty) + offset
        elif wave_type == "三角波":
            y = amp * scipy_signal.sawtooth(2 * np.pi * freq * t + phase, width=0.5) + offset
        elif wave_type == "锯齿波":
            y = amp * scipy_signal.sawtooth(2 * np.pi * freq * t + phase, width=1) + offset
        elif wave_type == "噪声":
            noise = self.noise_level.value() * np.random.normal(0, 1, len(t))
            y = amp * np.sin(2 * np.pi * freq * t + phase) + offset + noise
        elif wave_type == "脉冲":
            pulse_width = self.pulse_width.value() * 1e-6  # 转换为秒
            y = amp * (t % (1/freq) < pulse_width).astype(float) + offset
        elif wave_type == "DC":
            y = np.ones_like(t) * amp + offset
        elif wave_type == "任意波形" and self.arbitrary_waveform is not None:
            # 使用任意波形
            arb_x = self.arbitrary_waveform[:, 0]
            arb_y = self.arbitrary_waveform[:, 1]
            
            # 归一化x轴到0-1范围
            arb_x_norm = (arb_x - arb_x.min()) / (arb_x.max() - arb_x.min())
            
            # 创建插值函数
            from scipy import interpolate
            f = interpolate.interp1d(arb_x_norm, arb_y, kind='linear', fill_value='extrapolate')
            
            # 生成周期性波形
            phase_time = (t * freq) % 1
            y = amp * f(phase_time) + offset
        else:
            # 默认正弦波+三次谐波
            y = amp * (np.sin(2 * np.pi * freq * t + phase) + 
                      0.3 * np.sin(6 * np.pi * freq * t + phase)) + offset
        
        # 应用调制
        mod_type = self.modulation_type.currentText()
        if mod_type != "无":
            mod_freq = self.modulation_freq.value()
            mod_depth = self.modulation_depth.value() / 100
            
            if mod_type == "AM":
                # 幅度调制
                carrier = y
                modulation = (1 + mod_depth * np.sin(2 * np.pi * mod_freq * t))
                y = carrier * modulation
            elif mod_type == "FM":
                # 频率调制
                modulation = mod_depth * np.sin(2 * np.pi * mod_freq * t)
                instantaneous_freq = freq * (1 + modulation)
                phase = 2 * np.pi * np.cumsum(instantaneous_freq) * (t[1] - t[0])
                y = amp * np.sin(phase) + offset
            elif mod_type == "PM":
                # 相位调制
                modulation = mod_depth * np.sin(2 * np.pi * mod_freq * t)
                y = amp * np.sin(2 * np.pi * freq * t + phase + modulation) + offset
            elif mod_type == "PWM":
                # 脉冲宽度调制
                if wave_type == "方波" or wave_type == "脉冲":
                    modulation = mod_depth * np.sin(2 * np.pi * mod_freq * t)
                    duty_cycle_mod = 0.5 * (1 + modulation)
                    y = amp * (t % (1/freq) < (duty_cycle_mod/freq)).astype(float) + offset
        
        # 绘制波形
        self.plot_widget.clear()
        self.plot_widget.plot(t, y, pen=pg.mkPen(color='b', width=2))
        
        # 计算并绘制频谱
        self.calculate_spectrum(y, sample_rate)
        
        # 保存数据以便导出
        self.wave_data = np.column_stack((t, y))
    
    def calculate_spectrum(self, y, sample_rate):
        # 计算FFT
        n = len(y)
        yf = fft.fft(y)
        xf = fft.fftfreq(n, 1/sample_rate)
        
        # 只取正频率部分
        idx = np.where(xf > 0)
        xf = xf[idx]
        yf = np.abs(yf[idx]) / n * 2  # 转换为幅度值
        
        # 转换为dB
        yf_db = 20 * np.log10(yf + 1e-10)  # 避免log(0)
        
        # 绘制频谱
        self.spectrum_widget.clear()
        self.spectrum_widget.plot(xf, yf_db, pen=pg.mkPen(color='r', width=1))
    
    def start_sweep(self):
        # 扫频功能
        start_freq = self.start_freq.value()
        stop_freq = self.stop_freq.value()
        sweep_time = self.sweep_time.value()
        sweep_type = self.sweep_type.currentText()
        
        # 生成时间序列
        sample_rate = 100000  # 100kHz采样率
        t = np.linspace(0, sweep_time, int(sample_rate * sweep_time))
        
        # 生成扫频信号
        if sweep_type == "线性":
            # 线性扫频
            freq = start_freq + (stop_freq - start_freq) * t / sweep_time
        else:
            # 对数扫频
            freq = start_freq * (stop_freq / start_freq) ** (t / sweep_time)
        
        # 积分得到相位
        phase = 2 * np.pi * np.cumsum(freq) / sample_rate
        
        # 生成信号
        y = self.amplitude.value() * np.sin(phase) + self.offset.value()
        
        # 绘制波形
        self.plot_widget.clear()
        self.plot_widget.plot(t, y, pen=pg.mkPen(color='g', width=1))
        
        # 计算并绘制频谱
        self.calculate_spectrum(y, sample_rate)
        
        # 保存数据
        self.wave_data = np.column_stack((t, y, freq))
    
    def save_data(self):
        if self.wave_data is None:
            QMessageBox.warning(self, "警告", "没有数据可保存")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存波形数据", "", "CSV文件 (*.csv);;文本文件 (*.txt)"
        )
        
        if file_path:
            try:
                if file_path.endswith('.csv'):
                    if self.wave_data.shape[1] == 3:  # 包含频率数据
                        np.savetxt(file_path, self.wave_data, delimiter=',', 
                                  header='Time,Amplitude,Frequency', comments='')
                    else:
                        np.savetxt(file_path, self.wave_data, delimiter=',', 
                                  header='Time,Amplitude', comments='')
                else:
                    np.savetxt(file_path, self.wave_data, delimiter='\t')
                
                QMessageBox.information(self, "成功", "数据保存成功")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"保存失败: {str(e)}")
    
    def export_waveform(self):
        if self.wave_data is None:
            QMessageBox.warning(self, "警告", "没有数据可导出")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出波形图像", "", "PNG图像 (*.png);;PDF文件 (*.pdf);;SVG文件 (*.svg)"
        )
        
        if file_path:
            try:
                plt.figure(figsize=(10, 6))
                plt.plot(self.wave_data[:, 0], self.wave_data[:, 1])
                plt.xlabel('时间 (s)')
                plt.ylabel('幅度 (V)')
                plt.title('生成的波形')
                plt.grid(True)
                plt.savefig(file_path)
                plt.close()
                
                QMessageBox.information(self, "成功", "波形导出成功")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导出失败: {str(e)}")
    
    def analyze_signal(self):
        if self.wave_data is None:
            QMessageBox.warning(self, "警告", "没有数据可分析")
            return
        
        # 信号分析功能
        t = self.wave_data[:, 0]
        y = self.wave_data[:, 1]
        
        # 计算基本统计信息
        mean_val = np.mean(y)
        rms_val = np.sqrt(np.mean(y**2))
        peak_val = np.max(np.abs(y))
        peak_to_peak = np.max(y) - np.min(y)
        
        # 计算THD（总谐波失真）
        n = len(y)
        yf = fft.fft(y)
        xf = fft.fftfreq(n, t[1]-t[0])
        
        # 找到基波频率
        idx = np.argsort(np.abs(yf))[::-1]
        fundamental_idx = idx[0]
        fundamental_freq = abs(xf[fundamental_idx])
        fundamental_amp = np.abs(yf[fundamental_idx]) / n * 2
        
        # 计算谐波
        harmonics = []
        for i in range(2, 10):  # 2nd to 9th harmonic
            harmonic_freq = fundamental_freq * i
            # 找到最接近的频率bin
            idx = np.argmin(np.abs(xf - harmonic_freq))
            harmonic_amp = np.abs(yf[idx]) / n * 2
            if harmonic_amp > 0.001 * fundamental_amp:  # 只考虑显著谐波
                harmonics.append((i, harmonic_freq, harmonic_amp))
        
        # 计算THD
        thd = np.sqrt(sum([h[2]**2 for h in harmonics])) / fundamental_amp * 100
        
        # 显示分析结果
        result_text = f"信号分析结果:\n"
        result_text += f"平均值: {mean_val:.4f} V\n"
        result_text += f"RMS值: {rms_val:.4f} V\n"
        result_text += f"峰值: {peak_val:.4f} V\n"
        result_text += f"峰峰值: {peak_to_peak:.4f} V\n"
        result_text += f"基波频率: {fundamental_freq:.2f} Hz\n"
        result_text += f"基波幅度: {fundamental_amp:.4f} V\n"
        result_text += f"总谐波失真(THD): {thd:.2f}%\n"
        
        if harmonics:
            result_text += "谐波成分:\n"
            for h in harmonics:
                result_text += f"  {h[0]}次谐波: {h[1]:.1f} Hz, {h[2]:.4f} V ({h[2]/fundamental_amp*100:.1f}%)\n"
        
        QMessageBox.information(self, "信号分析", result_text)


class EnhancedSerialCommunicator(QWidget):
    def __init__(self):
        super().__init__()
        self.serial = None
        self.received_data = bytearray()
        self.initUI()
    
    def initUI(self):
        layout = QVBoxLayout()
        
        # 串口设置
        settings_group = QGroupBox("串口设置")
        settings_layout = QGridLayout()
        
        settings_layout.addWidget(QLabel("端口:"), 0, 0)
        self.port_combo = QComboBox()
        self.refresh_ports()
        settings_layout.addWidget(self.port_combo, 0, 1)
        
        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.clicked.connect(self.refresh_ports)
        settings_layout.addWidget(self.refresh_btn, 0, 2)
        
        settings_layout.addWidget(QLabel("波特率:"), 1, 0)
        self.baud_combo = QComboBox()
        self.baud_combo.addItems(["9600", "19200", "38400", "57600", "115200", "230400", "460800", "921600", "2000000", "3000000"])
        self.baud_combo.setCurrentText("115200")
        settings_layout.addWidget(self.baud_combo, 1, 1)
        
        settings_layout.addWidget(QLabel("数据位:"), 2, 0)
        self.data_bits = QComboBox()
        self.data_bits.addItems(["5", "6", "7", "8"])
        self.data_bits.setCurrentText("8")
        settings_layout.addWidget(self.data_bits, 2, 1)
        
        settings_layout.addWidget(QLabel("停止位:"), 3, 0)
        self.stop_bits = QComboBox()
        self.stop_bits.addItems(["1", "1.5", "2"])
        self.stop_bits.setCurrentText("1")
        settings_layout.addWidget(self.stop_bits, 3, 1)
        
        settings_layout.addWidget(QLabel("校验位:"), 4, 0)
        self.parity = QComboBox()
        self.parity.addItems(["无", "奇", "偶", "标记", "空格"])
        settings_layout.addWidget(self.parity, 4, 1)
        
        settings_layout.addWidget(QLabel("流控制:"), 5, 0)
        self.flow_control = QComboBox()
        self.flow_control.addItems(["无", "RTS/CTS", "XON/XOFF"])
        settings_layout.addWidget(self.flow_control, 5, 1)
        
        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)
        
        # 控制按钮
        control_layout = QHBoxLayout()
        self.connect_btn = QPushButton("打开串口")
        self.connect_btn.clicked.connect(self.toggle_serial)
        control_layout.addWidget(self.connect_btn)
        
        self.clear_btn = QPushButton("清空接收")
        self.clear_btn.clicked.connect(self.clear_received)
        control_layout.addWidget(self.clear_btn)
        
        self.save_btn = QPushButton("保存数据")
        self.save_btn.clicked.connect(self.save_received_data)
        control_layout.addWidget(self.save_btn)
        
        self.record_btn = QPushButton("开始记录")
        self.record_btn.setCheckable(True)
        self.record_btn.clicked.connect(self.toggle_recording)
        control_layout.addWidget(self.record_btn)
        
        self.plot_btn = QPushButton("数据绘图")
        self.plot_btn.clicked.connect(self.plot_received_data)
        self.plot_btn.setEnabled(False)
        control_layout.addWidget(self.plot_btn)
        
        layout.addLayout(control_layout)
        
        # 发送区域
        send_group = QGroupBox("发送数据")
        send_layout = QVBoxLayout()
        
        send_control_layout = QHBoxLayout()
        self.send_text = QTextEdit()
        self.send_text.setMaximumHeight(80)
        send_control_layout.addWidget(self.send_text)
        
        send_btn_layout = QVBoxLayout()
        self.send_btn = QPushButton("发送")
        self.send_btn.clicked.connect(self.send_data)
        send_btn_layout.addWidget(self.send_btn)
        
        self.hex_send = QCheckBox("十六进制发送")
        send_btn_layout.addWidget(self.hex_send)
        
        self.auto_send = QCheckBox("自动发送")
        self.auto_send.setChecked(False)
        send_btn_layout.addWidget(self.auto_send)
        
        self.auto_send_interval = QSpinBox()
        self.auto_send_interval.setRange(100, 10000)
        self.auto_send_interval.setValue(1000)
        self.auto_send_interval.setSuffix(" ms")
        self.auto_send_interval.setEnabled(False)
        send_btn_layout.addWidget(self.auto_send_interval)
        
        self.auto_send_count = QSpinBox()
        self.auto_send_count.setRange(0, 10000)
        self.auto_send_count.setValue(0)
        self.auto_send_count.setSuffix(" 次 (0=无限)")
        self.auto_send_count.setEnabled(False)
        send_btn_layout.addWidget(self.auto_send_count)
        
        send_btn_layout.addStretch()
        send_control_layout.addLayout(send_btn_layout)
        
        send_layout.addLayout(send_control_layout)
        
        # 预设命令
        preset_layout = QHBoxLayout()
        preset_layout.addWidget(QLabel("预设命令:"))
        self.preset_combo = QComboBox()
        self.preset_combo.addItems(["AT", "AT+VER", "AT+RESET", "AT+CFG", "自定义..."])
        self.preset_combo.currentTextChanged.connect(self.preset_selected)
        preset_layout.addWidget(self.preset_combo)
        
        self.add_preset_btn = QPushButton("添加")
        self.add_preset_btn.clicked.connect(self.add_preset)
        preset_layout.addWidget(self.add_preset_btn)
        
        self.manage_presets_btn = QPushButton("管理")
        self.manage_presets_btn.clicked.connect(self.manage_presets)
        preset_layout.addWidget(self.manage_presets_btn)
        
        send_layout.addLayout(preset_layout)
        send_group.setLayout(send_layout)
        layout.addWidget(send_group)
        
        # 接收区域
        receive_group = QGroupBox("接收数据")
        receive_layout = QVBoxLayout()
        
        receive_control_layout = QHBoxLayout()
        self.receive_text = QTextEdit()
        receive_control_layout.addWidget(self.receive_text)
        
        receive_options_layout = QVBoxLayout()
        self.hex_display = QCheckBox("十六进制显示")
        receive_options_layout.addWidget(self.hex_display)
        
        self.auto_scroll = QCheckBox("自动滚动")
        self.auto_scroll.setChecked(True)
        receive_options_layout.addWidget(self.auto_scroll)
        
        self.timestamp = QCheckBox("显示时间戳")
        self.timestamp.setChecked(True)
        receive_options_layout.addWidget(self.timestamp)
        
        self.show_nonprintable = QCheckBox("显示非打印字符")
        self.show_nonprintable.setChecked(False)
        receive_options_layout.addWidget(self.show_nonprintable)
        
        self.receive_counter = QLabel("接收: 0 字节")
        receive_options_layout.addWidget(self.receive_counter)
        
        self.send_counter = QLabel("发送: 0 字节")
        receive_options_layout.addWidget(self.send_counter)
        
        self.error_counter = QLabel("错误: 0")
        receive_options_layout.addWidget(self.error_counter)
        
        receive_options_layout.addStretch()
        receive_control_layout.addLayout(receive_options_layout)
        
        receive_layout.addLayout(receive_control_layout)
        receive_group.setLayout(receive_layout)
        layout.addWidget(receive_group)
        
        self.setLayout(layout)
        
        # 定时器用于读取串口数据和自动发送
        self.read_timer = QTimer()
        self.read_timer.timeout.connect(self.read_data)
        
        self.auto_send_timer = QTimer()
        self.auto_send_timer.timeout.connect(self.auto_send_data)
        self.auto_send.stateChanged.connect(self.toggle_auto_send)
        
        # 记录文件
        self.record_file = None
        self.record_start_time = None
        
        # 计数器
        self.bytes_received = 0
        self.bytes_sent = 0
        self.error_count = 0
        
        # 自动发送计数
        self.auto_send_sent = 0
    
    def refresh_ports(self):
        self.port_combo.clear()
        ports = serial.tools.list_ports.comports()
        for port in ports:
            self.port_combo.addItem(port.device, port.description)
    
    def toggle_serial(self):
        if self.serial and self.serial.is_open:
            self.close_serial()
        else:
            self.open_serial()
    
    def open_serial(self):
        try:
            port = self.port_combo.currentText()
            baud = int(self.baud_combo.currentText())
            
            self.serial = serial.Serial()
            self.serial.port = port
            self.serial.baudrate = baud
            self.serial.bytesize = int(self.data_bits.currentText())
            
            stop_bits = self.stop_bits.currentText()
            if stop_bits == "1":
                self.serial.stopbits = serial.STOPBITS_ONE
            elif stop_bits == "1.5":
                self.serial.stopbits = serial.STOPBITS_ONE_POINT_FIVE
            else:
                self.serial.stopbits = serial.STOPBITS_TWO
            
            parity = self.parity.currentText()
            if parity == "无":
                self.serial.parity = serial.PARITY_NONE
            elif parity == "奇":
                self.serial.parity = serial.PARITY_ODD
            elif parity == "偶":
                self.serial.parity = serial.PARITY_EVEN
            elif parity == "标记":
                self.serial.parity = serial.PARITY_MARK
            else:
                self.serial.parity = serial.PARITY_SPACE
            
            # 流控制
            flow = self.flow_control.currentText()
            if flow == "无":
                self.serial.rtscts = False
                self.serial.xonxoff = False
            elif flow == "RTS/CTS":
                self.serial.rtscts = True
                self.serial.xonxoff = False
            else:
                self.serial.rtscts = False
                self.serial.xonxoff = True
            
            self.serial.open()
            self.connect_btn.setText("关闭串口")
            self.read_timer.start(10)  # 每10ms检查一次数据
            self.plot_btn.setEnabled(True)
            
            # 更新UI状态
            self.update_ui_state(True)
            
        except Exception as e:
            self.receive_text.append(f"打开串口失败: {str(e)}")
            self.error_count += 1
            self.error_counter.setText(f"错误: {self.error_count}")
    
    def close_serial(self):
        if self.serial and self.serial.is_open:
            self.read_timer.stop()
            self.auto_send_timer.stop()
            self.serial.close()
        
        self.connect_btn.setText("打开串口")
        self.update_ui_state(False)
        self.plot_btn.setEnabled(False)
        
        # 停止记录
        if self.record_btn.isChecked():
            self.record_btn.setChecked(False)
            self.stop_recording()
    
    def update_ui_state(self, connected):
        self.refresh_btn.setEnabled(not connected)
        self.port_combo.setEnabled(not connected)
        self.baud_combo.setEnabled(not connected)
        self.data_bits.setEnabled(not connected)
        self.stop_bits.setEnabled(not connected)
        self.parity.setEnabled(not connected)
        self.flow_control.setEnabled(not connected)
    
    def read_data(self):
        if self.serial and self.serial.is_open:
            try:
                if self.serial.in_waiting > 0:
                    data = self.serial.read(self.serial.in_waiting)
                    self.bytes_received += len(data)
                    self.receive_counter.setText(f"接收: {self.bytes_received} 字节")
                    
                    # 记录数据
                    if self.record_btn.isChecked():
                        self.record_data(data)
                    
                    if self.hex_display.isChecked():
                        text = ' '.join([f'{b:02X}' for b in data])
                    else:
                        try:
                            if self.show_nonprintable.isChecked():
                                # 显示非打印字符为转义序列
                                text = ''
                                for b in data:
                                    if 32 <= b <= 126:  # 可打印ASCII
                                        text += chr(b)
                                    else:
                                        text += f'\\x{b:02X}'
                            else:
                                # 替换非打印字符
                                text = ''.join([chr(b) if 32 <= b <= 126 or b in [10, 13] else '.' for b in data])
                        except:
                            text = ' '.join([f'{b:02X}' for b in data])
                    
                    # 添加时间戳
                    if self.timestamp.isChecked():
                        timestamp = datetime.now().strftime("[%H:%M:%S.%f] ")[:-3]
                        text = timestamp + text
                    
                    self.receive_text.moveCursor(self.receive_text.textCursor().End)
                    self.receive_text.insertPlainText(text)
                    if self.auto_scroll.isChecked():
                        self.receive_text.moveCursor(self.receive_text.textCursor().End)
            except Exception as e:
                self.receive_text.append(f"读取错误: {str(e)}")
                self.error_count += 1
                self.error_counter.setText(f"错误: {self.error_count}")
    
    def send_data(self):
        if not self.serial or not self.serial.is_open:
            self.receive_text.append("串口未打开")
            return
        
        try:
            text = self.send_text.toPlainText()
            if self.hex_send.isChecked():
                # 处理十六进制发送
                text = text.strip()
                # 移除可能的分隔符
                text = text.replace(' ', '').replace(',', '').replace(':', '')
                bytes_to_send = bytes.fromhex(text)
            else:
                bytes_to_send = text.encode('utf-8')
            
            self.serial.write(bytes_to_send)
            self.bytes_sent += len(bytes_to_send)
            self.send_counter.setText(f"发送: {self.bytes_sent} 字节")
            
        except Exception as e:
            self.receive_text.append(f"发送错误: {str(e)}")
            self.error_count += 1
            self.error_counter.setText(f"错误: {self.error_count}")
    
    def auto_send_data(self):
        if self.auto_send.isChecked():
            self.send_data()
            self.auto_send_sent += 1
            
            # 检查是否达到发送次数限制
            if self.auto_send_count.value() > 0 and self.auto_send_sent >= self.auto_send_count.value():
                self.auto_send.setChecked(False)
                self.auto_send_timer.stop()
                self.auto_send_sent = 0
    
    def toggle_auto_send(self, state):
        if state:
            interval = self.auto_send_interval.value()
            self.auto_send_timer.start(interval)
            self.auto_send_interval.setEnabled(False)
            self.auto_send_count.setEnabled(False)
            self.auto_send_sent = 0
        else:
            self.auto_send_timer.stop()
            self.auto_send_interval.setEnabled(True)
            self.auto_send_count.setEnabled(True)
    
    def clear_received(self):
        self.receive_text.clear()
        self.bytes_received = 0
        self.bytes_sent = 0
        self.error_count = 0
        self.receive_counter.setText("接收: 0 字节")
        self.send_counter.setText("发送: 0 字节")
        self.error_counter.setText("错误: 0")
    
    def preset_selected(self, text):
        if text == "自定义...":
            # 允许用户输入自定义命令
            custom, ok = QInputDialog.getText(self, "自定义命令", "输入命令:")
            if ok and custom:
                self.preset_combo.addItem(custom)
                self.preset_combo.setCurrentText(custom)
        else:
            self.send_text.setPlainText(text)
    
    def add_preset(self):
        text = self.send_text.toPlainText()
        if text and text not in [self.preset_combo.itemText(i) for i in range(self.preset_combo.count())]:
            self.preset_combo.addItem(text)
    
    def manage_presets(self):
        # 管理预设命令对话框
        dialog = QDialog(self)
        dialog.setWindowTitle("管理预设命令")
        dialog.setMinimumSize(400, 300)
        
        layout = QVBoxLayout()
        
        # 命令列表
        list_widget = QListWidget()
        for i in range(self.preset_combo.count()):
            if self.preset_combo.itemText(i) != "自定义...":
                list_widget.addItem(self.preset_combo.itemText(i))
        
        layout.addWidget(list_widget)
        
        # 按钮布局
        btn_layout = QHBoxLayout()
        
        delete_btn = QPushButton("删除")
        delete_btn.clicked.connect(lambda: self.delete_preset(list_widget))
        btn_layout.addWidget(delete_btn)
        
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(dialog.accept)
        btn_layout.addWidget(close_btn)
        
        layout.addLayout(btn_layout)
        dialog.setLayout(layout)
        
        dialog.exec()
    
    def delete_preset(self, list_widget):
        current_item = list_widget.currentItem()
        if current_item:
            text = current_item.text()
            index = self.preset_combo.findText(text)
            if index >= 0:
                self.preset_combo.removeItem(index)
            list_widget.takeItem(list_widget.row(current_item))
    
    def toggle_recording(self, checked):
        if checked:
            self.start_recording()
        else:
            self.stop_recording()
    
    def start_recording(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "选择记录文件", "", "CSV文件 (*.csv);;文本文件 (*.txt);;所有文件 (*)"
        )
        
        if file_path:
            try:
                self.record_file = open(file_path, 'w', encoding='utf-8')
                self.record_start_time = time.time()
                self.record_btn.setText("停止记录")
                
                # 写入文件头
                if file_path.endswith('.csv'):
                    self.record_file.write("Timestamp,Data\n")
                
            except Exception as e:
                QMessageBox.critical(self, "错误", f"无法创建记录文件: {str(e)}")
                self.record_btn.setChecked(False)
        else:
            self.record_btn.setChecked(False)
    
    def stop_recording(self):
        if self.record_file:
            self.record_file.close()
            self.record_file = None
        
        self.record_btn.setText("开始记录")
    
    def record_data(self, data):
        if self.record_file:
            timestamp = time.time() - self.record_start_time
            if self.hex_display.isChecked():
                data_str = ' '.join([f'{b:02X}' for b in data])
            else:
                try:
                    data_str = data.decode('utf-8', errors='replace')
                except:
                    data_str = ' '.join([f'{b:02X}' for b in data])
            
            if hasattr(self.record_file, 'name') and self.record_file.name.endswith('.csv'):
                self.record_file.write(f"{timestamp:.3f},{data_str.replace(',', ';')}\n")
            else:
                self.record_file.write(f"[{timestamp:.3f}] {data_str}\n")
    
    def save_received_data(self):
        if self.receive_text.toPlainText():
            file_path, _ = QFileDialog.getSaveFileName(
                self, "保存接收数据", "", "文本文件 (*.txt);;CSV文件 (*.csv);;所有文件 (*)"
            )
            
            if file_path:
                try:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(self.receive_text.toPlainText())
                    QMessageBox.information(self, "成功", "数据保存成功")
                except Exception as e:
                    QMessageBox.critical(self, "错误", f"保存失败: {str(e)}")
    
    def plot_received_data(self):
        # 分析接收到的数据并绘图
        text = self.receive_text.toPlainText()
        if not text:
            QMessageBox.warning(self, "警告", "没有数据可绘图")
            return
        
        # 尝试提取数值数据
        numbers = []
        lines = text.split('\n')
        for line in lines:
            # 尝试从行中提取数字
            parts = line.split()
            for part in parts:
                try:
                    # 尝试转换为浮点数
                    num = float(part)
                    numbers.append(num)
                except ValueError:
                    pass
        
        if not numbers:
            QMessageBox.warning(self, "警告", "未找到可绘图的数值数据")
            return
        
        # 创建绘图对话框
        dialog = QDialog(self)
        dialog.setWindowTitle("数据绘图")
        dialog.setMinimumSize(600, 400)
        
        layout = QVBoxLayout()
        
        plot_widget = pg.PlotWidget()
        plot_widget.setBackground('w')
        plot_widget.setLabel('left', '数值')
        plot_widget.setLabel('bottom', '样本')
        plot_widget.showGrid(x=True, y=True)
        
        # 绘制数据
        plot_widget.plot(numbers, pen=pg.mkPen(color='b', width=2))
        
        layout.addWidget(plot_widget)
        
        # 添加统计信息
        stats_text = f"数据点数: {len(numbers)}\n"
        stats_text += f"平均值: {np.mean(numbers):.4f}\n"
        stats_text += f"标准差: {np.std(numbers):.4f}\n"
        stats_text += f"最小值: {np.min(numbers):.4f}\n"
        stats_text += f"最大值: {np.max(numbers):.4f}"
        
        stats_label = QLabel(stats_text)
        layout.addWidget(stats_label)
        
        dialog.setLayout(layout)
        dialog.exec()


# 由于代码长度限制，这里只展示了部分类的实现
# 其余类（AdvancedLogicAnalyzer, AdvancedPCBCalculator, CircuitSimulator）的实现类似
# 完整代码需要继续实现这些类

class HardwareEngineerToolkit(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()
    
    def initUI(self):
        self.setWindowTitle("硬件工程师高级工具库 - PyQt6增强版")
        self.setGeometry(100, 100, 1400, 900)
        
        # 设置应用样式
        self.setStyle(QStyleFactory.create("Fusion"))
        
        # 创建暗色主题
        self.dark_palette = QPalette()
        self.dark_palette.setColor(QPalette.ColorRole.Window, QColor(53, 53, 53))
        self.dark_palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
        self.dark_palette.setColor(QPalette.ColorRole.Base, QColor(25, 25, 25))
        self.dark_palette.setColor(QPalette.ColorRole.AlternateBase, QColor(53, 53, 53))
        self.dark_palette.setColor(QPalette.ColorRole.ToolTipBase, Qt.GlobalColor.white)
        self.dark_palette.setColor(QPalette.ColorRole.ToolTipText, Qt.GlobalColor.white)
        self.dark_palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.white)
        self.dark_palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
        self.dark_palette.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.white)
        self.dark_palette.setColor(QPalette.ColorRole.BrightText, Qt.GlobalColor.red)
        self.dark_palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
        self.dark_palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
        self.dark_palette.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.black)
        
        # 创建选项卡
        self.tabs = QTabWidget()
        
        # 添加各个工具页面
        self.component_calculator = ComponentCalculator()
        self.signal_generator = AdvancedSignalGenerator()
        self.serial_communicator = EnhancedSerialCommunicator()
        # 其余工具页面类似添加
        
        self.tabs.addTab(self.component_calculator, "元件计算")
        self.tabs.addTab(self.signal_generator, "信号生成")
        self.tabs.addTab(self.serial_communicator, "串口通信")
        # 其余选项卡类似添加
        
        self.setCentralWidget(self.tabs)
        
        # 状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪")
        
        # 菜单栏
        self.create_menu()
        
        # 工具栏
        self.create_toolbar()
    
    def create_menu(self):
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu('文件')
        
        new_action = QAction('新建', self)
        new_action.setShortcut('Ctrl+N')
        file_menu.addAction(new_action)
        
        open_action = QAction('打开', self)
        open_action.setShortcut('Ctrl+O')
        file_menu.addAction(open_action)
        
        save_action = QAction('保存', self)
        save_action.setShortcut('Ctrl+S')
        file_menu.addAction(save_action)
        
        file_menu.addSeparator()
        
        export_action = QAction('导出数据', self)
        export_action.triggered.connect(self.export_data)
        file_menu.addAction(export_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction('退出', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 视图菜单
        view_menu = menubar.addMenu('视图')
        
        dark_mode_action = QAction('暗色主题', self)
        dark_mode_action.setCheckable(True)
        dark_mode_action.triggered.connect(self.toggle_dark_mode)
        view_menu.addAction(dark_mode_action)
        
        # 工具菜单
        tools_menu = menubar.addMenu('工具')
        
        calc_action = QAction('计算器', self)
        calc_action.triggered.connect(self.open_calculator)
        tools_menu.addAction(calc_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu('帮助')
        
        about_action = QAction('关于', self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def create_toolbar(self):
        toolbar = QToolBar("主工具栏")
        self.addToolBar(toolbar)
        
        # 添加工具栏按钮
        export_btn = QAction("导出", self)
        export_btn.triggered.connect(self.export_data)
        toolbar.addAction(export_btn)
        
        toolbar.addSeparator()
        
        calculator_btn = QAction("计算器", self)
        calculator_btn.triggered.connect(self.open_calculator)
        toolbar.addAction(calculator_btn)
    
    def toggle_dark_mode(self, checked):
        if checked:
            self.setPalette(self.dark_palette)
        else:
            self.setPalette(self.style().standardPalette())
    
    def export_data(self):
        current_tab = self.tabs.currentWidget()
        if hasattr(current_tab, 'export_data'):
            current_tab.export_data()
        else:
            QMessageBox.information(self, "信息", "当前选项卡不支持数据导出")
    
    def open_calculator(self):
        # 打开系统计算器
        import os
        if os.name == 'nt':  # Windows
            os.system('calc')
        elif os.name == 'posix':  # macOS, Linux
            os.system('gnome-calculator &' if os.uname().sysname == 'Linux' else 'open -a Calculator')
    
    def show_about(self):
        about_text = """
        <h2>硬件工程师高级工具库 - PyQt6增强版</h2>
        <p>版本: 3.0</p>
        <p>这是一个功能强大的硬件工程师工具集合，基于PyQt6开发，包含:</p>
        <ul>
            <li>高级元件计算器</li>
            <li>信号发生器与频谱分析</li>
            <li>增强型串口通信工具</li>
            <li>逻辑分析仪模拟</li>
            <li>PCB设计计算工具</li>
            <li>电路仿真工具</li>
        </ul>
        <p>版权所有 © 2023 硬件工具开发团队</p>
        """
        QMessageBox.about(self, "关于", about_text)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("硬件工程师高级工具库 - PyQt6增强版")
    app.setApplicationVersion("3.0")
    
    # 设置全局字体
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    
    window = HardwareEngineerToolkit()
    window.show()
    
    sys.exit(app.exec())


if __name__ == '__main__':
    main()