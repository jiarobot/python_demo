import sys
import math
import numpy as np
import random
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QSlider, QPushButton, 
                             QGroupBox, QComboBox, QSpinBox, QDoubleSpinBox,
                             QCheckBox, QColorDialog, QTextEdit, QLineEdit,
                             QTabWidget, QSplitter, QProgressBar, QMessageBox,
                             QFileDialog, QTableWidget, QTableWidgetItem,
                             QHeaderView, QListWidget, QListWidgetItem)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt5.QtGui import QColor, QPalette, QFont, QPixmap, QIcon
import pyqtgraph.opengl as gl
from pyqtgraph import Vector, mkColor
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import pandas as pd
from collections import Counter
import json

# DNA序列生成和分析工具类
class DNATools:
    @staticmethod
    def generate_random_sequence(length):
        """生成随机DNA序列"""
        return ''.join(random.choice('ATCG') for _ in range(length))
    
    @staticmethod
    def validate_sequence(sequence):
        """验证DNA序列是否有效"""
        return all(base in 'ATCG' for base in sequence.upper())
    
    @staticmethod
    def get_complementary_sequence(sequence):
        """获取互补序列"""
        complement = {'A': 'T', 'T': 'A', 'C': 'G', 'G': 'C'}
        return ''.join(complement[base] for base in sequence.upper())
    
    @staticmethod
    def calculate_gc_content(sequence):
        """计算GC含量"""
        sequence = sequence.upper()
        gc_count = sequence.count('G') + sequence.count('C')
        return (gc_count / len(sequence)) * 100 if sequence else 0
    
    @staticmethod
    def find_motifs(sequence, motif):
        """查找序列中的模体"""
        sequence = sequence.upper()
        motif = motif.upper()
        positions = []
        start = 0
        while True:
            pos = sequence.find(motif, start)
            if pos == -1:
                break
            positions.append(pos)
            start = pos + 1
        return positions
    
    @staticmethod
    def transcribe(sequence):
        """转录DNA到RNA"""
        return sequence.upper().replace('T', 'U')
    
    @staticmethod
    def translate(sequence):
        """翻译DNA到蛋白质"""
        # 简化的遗传密码表
        codon_table = {
            'ATA':'I', 'ATC':'I', 'ATT':'I', 'ATG':'M',
            'ACA':'T', 'ACC':'T', 'ACG':'T', 'ACT':'T',
            'AAC':'N', 'AAT':'N', 'AAA':'K', 'AAG':'K',
            'AGC':'S', 'AGT':'S', 'AGA':'R', 'AGG':'R',
            'CTA':'L', 'CTC':'L', 'CTG':'L', 'CTT':'L',
            'CCA':'P', 'CCC':'P', 'CCG':'P', 'CCT':'P',
            'CAC':'H', 'CAT':'H', 'CAA':'Q', 'CAG':'Q',
            'CGA':'R', 'CGC':'R', 'CGG':'R', 'CGT':'R',
            'GTA':'V', 'GTC':'V', 'GTG':'V', 'GTT':'V',
            'GCA':'A', 'GCC':'A', 'GCG':'A', 'GCT':'A',
            'GAC':'D', 'GAT':'D', 'GAA':'E', 'GAG':'E',
            'GGA':'G', 'GGC':'G', 'GGG':'G', 'GGT':'G',
            'TCA':'S', 'TCC':'S', 'TCG':'S', 'TCT':'S',
            'TTC':'F', 'TTT':'F', 'TTA':'L', 'TTG':'L',
            'TAC':'Y', 'TAT':'Y', 'TAA':'*', 'TAG':'*',
            'TGC':'C', 'TGT':'C', 'TGA':'*', 'TGG':'W'
        }
        
        protein = ""
        for i in range(0, len(sequence)-2, 3):
            codon = sequence[i:i+3].upper()
            if len(codon) == 3:
                protein += codon_table.get(codon, '?')
        return protein

# DNA分析线程
class DNAAnalysisThread(QThread):
    progress_updated = pyqtSignal(int)
    analysis_completed = pyqtSignal(dict)
    
    def __init__(self, sequence):
        super().__init__()
        self.sequence = sequence
    
    def run(self):
        results = {}
        
        # 序列长度
        results['length'] = len(self.sequence)
        
        # 碱基组成
        base_count = Counter(self.sequence.upper())
        results['base_composition'] = dict(base_count)
        
        # GC含量
        results['gc_content'] = DNATools.calculate_gc_content(self.sequence)
        
        # 互补序列
        results['complementary'] = DNATools.get_complementary_sequence(self.sequence)
        
        # 转录
        results['transcribed'] = DNATools.transcribe(self.sequence)
        
        # 翻译
        results['translated'] = DNATools.translate(self.sequence)
        
        # 发送结果
        self.analysis_completed.emit(results)

# 高级DNA可视化组件
class AdvancedDNAHelixViewer(gl.GLViewWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('高级DNA双螺旋结构可视化')
        self.setCameraPosition(distance=40)
        
        # DNA参数
        self.helix_radius = 2.0
        self.helix_pitch = 5.0
        self.base_pairs = 20
        self.twist_angle = 36.0  # 螺旋扭曲角度
        self.show_backbone = True
        self.show_bases = True
        self.show_hydrogen_bonds = True
        self.show_base_labels = False
        self.sequence = DNATools.generate_random_sequence(20)
        self.animation_mode = "none"  # none, replication, transcription
        
        # 颜色设置
        self.backbone_color1 = (0.2, 0.6, 1.0, 1.0)  # 蓝色
        self.backbone_color2 = (1.0, 0.2, 0.2, 1.0)  # 红色
        self.base_colors = {
            'A': (1.0, 0.2, 0.2, 1.0),  # 红色
            'T': (0.2, 1.0, 0.2, 1.0),  # 绿色
            'C': (0.2, 0.6, 1.0, 1.0),  # 蓝色
            'G': (1.0, 0.8, 0.2, 1.0)   # 黄色
        }
        self.hbond_color = (1.0, 1.0, 1.0, 0.7)
        
        # 存储图形项
        self.backbone1 = None
        self.backbone2 = None
        self.bases1 = []
        self.bases2 = []
        self.hbonds = []
        self.base_labels = []
        
        # 动画状态
        self.animation_progress = 0
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self.update_animation)
        
        # 初始化DNA
        self.update_dna()
        
    def update_dna(self):
        # 清除现有项目
        self.clear()
        self.bases1.clear()
        self.bases2.clear()
        self.hbonds.clear()
        self.base_labels.clear()
        
        # 确保序列长度与碱基对数匹配
        if len(self.sequence) < self.base_pairs:
            self.sequence += DNATools.generate_random_sequence(self.base_pairs - len(self.sequence))
        elif len(self.sequence) > self.base_pairs:
            self.sequence = self.sequence[:self.base_pairs]
        
        # 计算DNA点
        points1 = []
        points2 = []
        base_points1 = []
        base_points2 = []
        hbond_points = []
        
        for i in range(self.base_pairs):
            # 计算螺旋位置，考虑扭曲角度
            t = i / self.base_pairs * 4 * math.pi + math.radians(self.twist_angle * i)
            
            # 主链点
            x1 = self.helix_radius * math.cos(t)
            y1 = i * self.helix_pitch / self.base_pairs
            z1 = self.helix_radius * math.sin(t)
            
            x2 = self.helix_radius * math.cos(t + math.pi)
            y2 = i * self.helix_pitch / self.base_pairs
            z2 = self.helix_radius * math.sin(t + math.pi)
            
            points1.append([x1, y1, z1])
            points2.append([x2, y2, z2])
            
            # 碱基对点
            if self.show_bases:
                base_points1.append([x1, y1, z1])
                base_points2.append([x2, y2, z2])
                hbond_points.append([(x1+x2)/2, y1, (z1+z2)/2])
        
        # 创建主链
        if self.show_backbone:
            self.backbone1 = gl.GLLinePlotItem(
                pos=np.array(points1), 
                color=self.backbone_color1, 
                width=3, 
                antialias=True
            )
            self.backbone2 = gl.GLLinePlotItem(
                pos=np.array(points2), 
                color=self.backbone_color2, 
                width=3, 
                antialias=True
            )
            self.addItem(self.backbone1)
            self.addItem(self.backbone2)
        
        # 创建碱基对
        if self.show_bases:
            for i in range(len(base_points1)):
                # 获取当前碱基
                base1 = self.sequence[i] if i < len(self.sequence) else 'A'
                base2 = DNATools.get_complementary_sequence(base1)
                
                # 碱基对连接线
                base_line = gl.GLLinePlotItem(
                    pos=np.array([base_points1[i], base_points2[i]]),
                    color=self.base_colors.get(base1, (0.5, 0.5, 0.5, 1.0)),
                    width=2,
                    antialias=True
                )
                self.bases1.append(base_line)
                self.addItem(base_line)
                
                # 碱基球体
                base_sphere1 = gl.MeshData.sphere(rows=4, cols=8, radius=0.3)
                base_mesh1 = gl.GLMeshItem(
                    meshdata=base_sphere1,
                    color=self.base_colors.get(base1, (0.5, 0.5, 0.5, 1.0)),
                    shader='balloon',
                    glOptions='opaque'
                )
                base_mesh1.translate(*base_points1[i])
                self.bases2.append(base_mesh1)
                self.addItem(base_mesh1)
                
                base_sphere2 = gl.MeshData.sphere(rows=4, cols=8, radius=0.3)
                base_mesh2 = gl.GLMeshItem(
                    meshdata=base_sphere2,
                    color=self.base_colors.get(base2, (0.5, 0.5, 0.5, 1.0)),
                    shader='balloon',
                    glOptions='opaque'
                )
                base_mesh2.translate(*base_points2[i])
                self.bases2.append(base_mesh2)
                self.addItem(base_mesh2)
                
                # 氢键
                if self.show_hydrogen_bonds:
                    hbond = gl.GLScatterPlotItem(
                        pos=np.array([hbond_points[i]]),
                        color=self.hbond_color,
                        size=5,
                        pxMode=False
                    )
                    self.hbonds.append(hbond)
                    self.addItem(hbond)
                
                # 碱基标签
                if self.show_base_labels:
                    # 注意：GLTextItem在pyqtgraph中可能有问题，这里简化处理
                    pass
        
        # 根据动画模式更新显示
        self.update_animation_display()
    
    def update_animation_display(self):
        if self.animation_mode == "none":
            return
        
        # 复制动画：部分分离DNA链
        elif self.animation_mode == "replication":
            progress = self.animation_progress / 100.0
            
            # 计算分离的位置
            separation_point = int(self.base_pairs * progress)
            
            # 更新碱基对的显示
            for i, base_line in enumerate(self.bases1):
                if i >= separation_point:
                    # 分离的碱基对
                    pos = base_line.pos()
                    if pos is not None and len(pos) == 2:
                        # 计算分离后的位置
                        separation_distance = 1.0
                        pos1 = pos[0].copy()
                        pos2 = pos[1].copy()
                        
                        # 向外移动
                        direction1 = pos1 / np.linalg.norm(pos1) if np.linalg.norm(pos1) > 0 else np.array([1, 0, 0])
                        direction2 = pos2 / np.linalg.norm(pos2) if np.linalg.norm(pos2) > 0 else np.array([-1, 0, 0])
                        
                        pos1 += direction1 * separation_distance
                        pos2 += direction2 * separation_distance
                        
                        base_line.setData(pos=np.array([pos1, pos2]))
        
        # 转录动画：RNA聚合酶沿DNA移动
        elif self.animation_mode == "transcription":
            progress = self.animation_progress / 100.0
            
            # 计算RNA聚合酶位置
            polymerase_pos = int(self.base_pairs * progress)
            
            # 添加RNA聚合酶可视化
            if hasattr(self, 'polymerase'):
                self.removeItem(self.polymerase)
            
            if polymerase_pos < self.base_pairs:
                # 创建RNA聚合酶模型
                polymerase_data = gl.MeshData.cylinder(rows=10, cols=10, radius=[0.5, 0.8, 0.5], length=1.0)
                self.polymerase = gl.GLMeshItem(
                    meshdata=polymerase_data,
                    color=(0.8, 0.2, 0.8, 1.0),  # 紫色
                    shader='balloon',
                    glOptions='opaque'
                )
                
                # 定位RNA聚合酶
                t = polymerase_pos / self.base_pairs * 4 * math.pi + math.radians(self.twist_angle * polymerase_pos)
                x = self.helix_radius * math.cos(t)
                y = polymerase_pos * self.helix_pitch / self.base_pairs
                z = self.helix_radius * math.sin(t)
                
                self.polymerase.translate(x, y, z)
                self.addItem(self.polymerase)
    
    def set_sequence(self, sequence):
        if DNATools.validate_sequence(sequence):
            self.sequence = sequence.upper()
            self.base_pairs = len(sequence)
            self.update_dna()
            return True
        return False
    
    def set_animation_mode(self, mode):
        self.animation_mode = mode
        self.animation_progress = 0
        self.update_dna()
        
        if mode != "none":
            self.animation_timer.start(50)  # 20fps
        else:
            self.animation_timer.stop()
    
    def update_animation(self):
        self.animation_progress = (self.animation_progress + 1) % 101
        self.update_animation_display()
    
    def set_helix_radius(self, radius):
        self.helix_radius = radius
        self.update_dna()
    
    def set_helix_pitch(self, pitch):
        self.helix_pitch = pitch
        self.update_dna()
    
    def set_base_pairs(self, pairs):
        self.base_pairs = pairs
        if len(self.sequence) < pairs:
            self.sequence += DNATools.generate_random_sequence(pairs - len(self.sequence))
        elif len(self.sequence) > pairs:
            self.sequence = self.sequence[:pairs]
        self.update_dna()
    
    def set_twist_angle(self, angle):
        self.twist_angle = angle
        self.update_dna()
    
    def set_show_backbone(self, show):
        self.show_backbone = show
        self.update_dna()
    
    def set_show_bases(self, show):
        self.show_bases = show
        self.update_dna()
    
    def set_show_hydrogen_bonds(self, show):
        self.show_hydrogen_bonds = show
        self.update_dna()
    
    def set_show_base_labels(self, show):
        self.show_base_labels = show
        self.update_dna()
    
    def set_backbone_color1(self, color):
        self.backbone_color1 = color
        self.update_dna()
    
    def set_backbone_color2(self, color):
        self.backbone_color2 = color
        self.update_dna()
    
    def set_base_color(self, base, color):
        if base in self.base_colors:
            self.base_colors[base] = color
            self.update_dna()

# 序列分析面板
class SequenceAnalysisPanel(QWidget):
    def __init__(self, dna_viewer):
        super().__init__()
        self.dna_viewer = dna_viewer
        self.analysis_thread = None
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 序列输入
        sequence_group = QGroupBox("DNA序列")
        sequence_layout = QVBoxLayout()
        
        sequence_input_layout = QHBoxLayout()
        sequence_input_layout.addWidget(QLabel("序列:"))
        self.sequence_input = QTextEdit()
        self.sequence_input.setMaximumHeight(80)
        self.sequence_input.setText(self.dna_viewer.sequence)
        sequence_input_layout.addWidget(self.sequence_input)
        
        sequence_buttons_layout = QHBoxLayout()
        self.load_sequence_btn = QPushButton("加载序列")
        self.load_sequence_btn.clicked.connect(self.load_sequence)
        sequence_buttons_layout.addWidget(self.load_sequence_btn)
        
        self.random_sequence_btn = QPushButton("随机序列")
        self.random_sequence_btn.clicked.connect(self.generate_random_sequence)
        sequence_buttons_layout.addWidget(self.random_sequence_btn)
        
        self.analyze_btn = QPushButton("分析序列")
        self.analyze_btn.clicked.connect(self.analyze_sequence)
        sequence_buttons_layout.addWidget(self.analyze_btn)
        
        sequence_layout.addLayout(sequence_input_layout)
        sequence_layout.addLayout(sequence_buttons_layout)
        sequence_group.setLayout(sequence_layout)
        layout.addWidget(sequence_group)
        
        # 分析结果
        results_group = QGroupBox("分析结果")
        results_layout = QVBoxLayout()
        
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(2)
        self.results_table.setHorizontalHeaderLabels(["属性", "值"])
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        results_layout.addWidget(self.results_table)
        
        results_group.setLayout(results_layout)
        layout.addWidget(results_group)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        self.setLayout(layout)
    
    def load_sequence(self):
        sequence = self.sequence_input.toPlainText().strip().upper()
        if DNATools.validate_sequence(sequence):
            self.dna_viewer.set_sequence(sequence)
            QMessageBox.information(self, "成功", "序列已加载到可视化中")
        else:
            QMessageBox.warning(self, "错误", "无效的DNA序列，只能包含A、T、C、G字符")
    
    def generate_random_sequence(self):
        length = 50  # 默认长度
        sequence = DNATools.generate_random_sequence(length)
        self.sequence_input.setText(sequence)
        self.dna_viewer.set_sequence(sequence)
    
    def analyze_sequence(self):
        sequence = self.sequence_input.toPlainText().strip()
        if not sequence:
            QMessageBox.warning(self, "错误", "请输入DNA序列")
            return
        
        if not DNATools.validate_sequence(sequence):
            QMessageBox.warning(self, "错误", "无效的DNA序列，只能包含A、T、C、G字符")
            return
        
        # 禁用按钮并显示进度条
        self.analyze_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        
        # 在后台线程中执行分析
        self.analysis_thread = DNAAnalysisThread(sequence)
        self.analysis_thread.progress_updated.connect(self.update_progress)
        self.analysis_thread.analysis_completed.connect(self.display_results)
        self.analysis_thread.start()
    
    def update_progress(self, value):
        self.progress_bar.setValue(value)
    
    def display_results(self, results):
        # 启用按钮并隐藏进度条
        self.analyze_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        # 清空表格
        self.results_table.setRowCount(0)
        
        # 添加结果到表格
        row = 0
        
        # 序列长度
        self.add_table_row(row, "序列长度", str(results['length']))
        row += 1
        
        # 碱基组成
        base_comp = results['base_composition']
        self.add_table_row(row, "A碱基数量", str(base_comp.get('A', 0)))
        row += 1
        self.add_table_row(row, "T碱基数量", str(base_comp.get('T', 0)))
        row += 1
        self.add_table_row(row, "C碱基数量", str(base_comp.get('C', 0)))
        row += 1
        self.add_table_row(row, "G碱基数量", str(base_comp.get('G', 0)))
        row += 1
        
        # GC含量
        self.add_table_row(row, "GC含量", f"{results['gc_content']:.2f}%")
        row += 1
        
        # 互补序列
        self.add_table_row(row, "互补序列", results['complementary'])
        row += 1
        
        # 转录结果
        self.add_table_row(row, "转录RNA", results['transcribed'])
        row += 1
        
        # 翻译结果
        self.add_table_row(row, "翻译蛋白质", results['translated'])
        row += 1
    
    def add_table_row(self, row, key, value):
        self.results_table.insertRow(row)
        self.results_table.setItem(row, 0, QTableWidgetItem(key))
        self.results_table.setItem(row, 1, QTableWidgetItem(value))

# 高级控制面板
class AdvancedControlPanel(QWidget):
    def __init__(self, dna_viewer):
        super().__init__()
        self.dna_viewer = dna_viewer
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 纪念标题
        title = QLabel("DNA双螺旋结构高级可视化")
        title.setStyleSheet("font-size: 16px; font-weight: bold; margin: 10px; color: #2c3e50;")
        layout.addWidget(title)
        
        memorial = QLabel("纪念詹姆斯·沃森 (1928-2023)\nDNA双螺旋结构共同发现者")
        memorial.setStyleSheet("font-size: 12px; color: #7f8c8d; margin: 5px; padding: 5px; background-color: #ecf0f1; border-radius: 5px;")
        memorial.setAlignment(Qt.AlignCenter)
        layout.addWidget(memorial)
        
        # 创建标签页
        tabs = QTabWidget()
        
        # 结构参数标签页
        structure_tab = QWidget()
        structure_layout = QVBoxLayout()
        structure_tab.setLayout(structure_layout)
        
        # 螺旋参数组
        helix_group = QGroupBox("螺旋参数")
        helix_layout = QVBoxLayout()
        
        # 螺旋半径
        radius_layout = QHBoxLayout()
        radius_layout.addWidget(QLabel("螺旋半径:"))
        self.radius_slider = QSlider(Qt.Horizontal)
        self.radius_slider.setMinimum(1)
        self.radius_slider.setMaximum(10)
        self.radius_slider.setValue(int(self.dna_viewer.helix_radius * 2))
        self.radius_slider.valueChanged.connect(self.radius_changed)
        radius_layout.addWidget(self.radius_slider)
        self.radius_value = QLabel(f"{self.dna_viewer.helix_radius:.1f}")
        radius_layout.addWidget(self.radius_value)
        helix_layout.addLayout(radius_layout)
        
        # 螺距
        pitch_layout = QHBoxLayout()
        pitch_layout.addWidget(QLabel("螺距:"))
        self.pitch_slider = QSlider(Qt.Horizontal)
        self.pitch_slider.setMinimum(1)
        self.pitch_slider.setMaximum(20)
        self.pitch_slider.setValue(int(self.dna_viewer.helix_pitch))
        self.pitch_slider.valueChanged.connect(self.pitch_changed)
        pitch_layout.addWidget(self.pitch_slider)
        self.pitch_value = QLabel(f"{self.dna_viewer.helix_pitch:.1f}")
        pitch_layout.addWidget(self.pitch_value)
        helix_layout.addLayout(pitch_layout)
        
        # 扭曲角度
        twist_layout = QHBoxLayout()
        twist_layout.addWidget(QLabel("扭曲角度:"))
        self.twist_slider = QSlider(Qt.Horizontal)
        self.twist_slider.setMinimum(0)
        self.twist_slider.setMaximum(72)
        self.twist_slider.setValue(int(self.dna_viewer.twist_angle))
        self.twist_slider.valueChanged.connect(self.twist_changed)
        twist_layout.addWidget(self.twist_slider)
        self.twist_value = QLabel(f"{self.dna_viewer.twist_angle:.1f}°")
        twist_layout.addWidget(self.twist_value)
        helix_layout.addLayout(twist_layout)
        
        # 碱基对数量
        pairs_layout = QHBoxLayout()
        pairs_layout.addWidget(QLabel("碱基对数量:"))
        self.pairs_spin = QSpinBox()
        self.pairs_spin.setMinimum(5)
        self.pairs_spin.setMaximum(100)
        self.pairs_spin.setValue(self.dna_viewer.base_pairs)
        self.pairs_spin.valueChanged.connect(self.pairs_changed)
        pairs_layout.addWidget(self.pairs_spin)
        helix_layout.addLayout(pairs_layout)
        
        helix_group.setLayout(helix_layout)
        structure_layout.addWidget(helix_group)
        
        # 显示选项组
        display_group = QGroupBox("显示选项")
        display_layout = QVBoxLayout()
        
        # 显示主链
        self.backbone_check = QCheckBox("显示主链")
        self.backbone_check.setChecked(self.dna_viewer.show_backbone)
        self.backbone_check.stateChanged.connect(self.backbone_changed)
        display_layout.addWidget(self.backbone_check)
        
        # 显示碱基对
        self.bases_check = QCheckBox("显示碱基对")
        self.bases_check.setChecked(self.dna_viewer.show_bases)
        self.bases_check.stateChanged.connect(self.bases_changed)
        display_layout.addWidget(self.bases_check)
        
        # 显示氢键
        self.hbonds_check = QCheckBox("显示氢键")
        self.hbonds_check.setChecked(self.dna_viewer.show_hydrogen_bonds)
        self.hbonds_check.stateChanged.connect(self.hbonds_changed)
        display_layout.addWidget(self.hbonds_check)
        
        # 显示碱基标签
        self.labels_check = QCheckBox("显示碱基标签")
        self.labels_check.setChecked(self.dna_viewer.show_base_labels)
        self.labels_check.stateChanged.connect(self.labels_changed)
        display_layout.addWidget(self.labels_check)
        
        display_group.setLayout(display_layout)
        structure_layout.addWidget(display_group)
        
        # 动画控制组
        animation_group = QGroupBox("动画模拟")
        animation_layout = QVBoxLayout()
        
        animation_buttons_layout = QHBoxLayout()
        
        self.no_animation_btn = QPushButton("无动画")
        self.no_animation_btn.setCheckable(True)
        self.no_animation_btn.setChecked(True)
        self.no_animation_btn.clicked.connect(lambda: self.set_animation_mode("none"))
        animation_buttons_layout.addWidget(self.no_animation_btn)
        
        self.replication_btn = QPushButton("DNA复制")
        self.replication_btn.setCheckable(True)
        self.replication_btn.clicked.connect(lambda: self.set_animation_mode("replication"))
        animation_buttons_layout.addWidget(self.replication_btn)
        
        self.transcription_btn = QPushButton("DNA转录")
        self.transcription_btn.setCheckable(True)
        self.transcription_btn.clicked.connect(lambda: self.set_animation_mode("transcription"))
        animation_buttons_layout.addWidget(self.transcription_btn)
        
        animation_layout.addLayout(animation_buttons_layout)
        
        # 动画速度
        speed_layout = QHBoxLayout()
        speed_layout.addWidget(QLabel("动画速度:"))
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setMinimum(1)
        self.speed_slider.setMaximum(10)
        self.speed_slider.setValue(5)
        self.speed_slider.valueChanged.connect(self.speed_changed)
        speed_layout.addWidget(self.speed_slider)
        animation_layout.addLayout(speed_layout)
        
        animation_group.setLayout(animation_layout)
        structure_layout.addWidget(animation_group)
        
        structure_layout.addStretch()
        
        # 颜色设置标签页
        color_tab = QWidget()
        color_layout = QVBoxLayout()
        color_tab.setLayout(color_layout)
        
        # 主链颜色
        backbone_color_group = QGroupBox("主链颜色")
        backbone_color_layout = QVBoxLayout()
        
        # 主链1颜色
        backbone1_layout = QHBoxLayout()
        backbone1_layout.addWidget(QLabel("主链1颜色:"))
        self.backbone1_color_btn = QPushButton()
        self.backbone1_color_btn.setStyleSheet(f"background-color: rgb({int(self.dna_viewer.backbone_color1[0]*255)}, {int(self.dna_viewer.backbone_color1[1]*255)}, {int(self.dna_viewer.backbone_color1[2]*255)})")
        self.backbone1_color_btn.clicked.connect(lambda: self.color_dialog('backbone1'))
        backbone1_layout.addWidget(self.backbone1_color_btn)
        backbone_color_layout.addLayout(backbone1_layout)
        
        # 主链2颜色
        backbone2_layout = QHBoxLayout()
        backbone2_layout.addWidget(QLabel("主链2颜色:"))
        self.backbone2_color_btn = QPushButton()
        self.backbone2_color_btn.setStyleSheet(f"background-color: rgb({int(self.dna_viewer.backbone_color2[0]*255)}, {int(self.dna_viewer.backbone_color2[1]*255)}, {int(self.dna_viewer.backbone_color2[2]*255)})")
        self.backbone2_color_btn.clicked.connect(lambda: self.color_dialog('backbone2'))
        backbone2_layout.addWidget(self.backbone2_color_btn)
        backbone_color_layout.addLayout(backbone2_layout)
        
        backbone_color_group.setLayout(backbone_color_layout)
        color_layout.addWidget(backbone_color_group)
        
        # 碱基颜色
        base_color_group = QGroupBox("碱基颜色")
        base_color_layout = QVBoxLayout()
        
        # A碱基颜色
        base_a_layout = QHBoxLayout()
        base_a_layout.addWidget(QLabel("A碱基颜色:"))
        self.base_a_color_btn = QPushButton()
        self.base_a_color_btn.setStyleSheet(f"background-color: rgb({int(self.dna_viewer.base_colors['A'][0]*255)}, {int(self.dna_viewer.base_colors['A'][1]*255)}, {int(self.dna_viewer.base_colors['A'][2]*255)})")
        self.base_a_color_btn.clicked.connect(lambda: self.color_dialog('A'))
        base_a_layout.addWidget(self.base_a_color_btn)
        base_color_layout.addLayout(base_a_layout)
        
        # T碱基颜色
        base_t_layout = QHBoxLayout()
        base_t_layout.addWidget(QLabel("T碱基颜色:"))
        self.base_t_color_btn = QPushButton()
        self.base_t_color_btn.setStyleSheet(f"background-color: rgb({int(self.dna_viewer.base_colors['T'][0]*255)}, {int(self.dna_viewer.base_colors['T'][1]*255)}, {int(self.dna_viewer.base_colors['T'][2]*255)})")
        self.base_t_color_btn.clicked.connect(lambda: self.color_dialog('T'))
        base_t_layout.addWidget(self.base_t_color_btn)
        base_color_layout.addLayout(base_t_layout)
        
        # C碱基颜色
        base_c_layout = QHBoxLayout()
        base_c_layout.addWidget(QLabel("C碱基颜色:"))
        self.base_c_color_btn = QPushButton()
        self.base_c_color_btn.setStyleSheet(f"background-color: rgb({int(self.dna_viewer.base_colors['C'][0]*255)}, {int(self.dna_viewer.base_colors['C'][1]*255)}, {int(self.dna_viewer.base_colors['C'][2]*255)})")
        self.base_c_color_btn.clicked.connect(lambda: self.color_dialog('C'))
        base_c_layout.addWidget(self.base_c_color_btn)
        base_color_layout.addLayout(base_c_layout)
        
        # G碱基颜色
        base_g_layout = QHBoxLayout()
        base_g_layout.addWidget(QLabel("G碱基颜色:"))
        self.base_g_color_btn = QPushButton()
        self.base_g_color_btn.setStyleSheet(f"background-color: rgb({int(self.dna_viewer.base_colors['G'][0]*255)}, {int(self.dna_viewer.base_colors['G'][1]*255)}, {int(self.dna_viewer.base_colors['G'][2]*255)})")
        self.base_g_color_btn.clicked.connect(lambda: self.color_dialog('G'))
        base_g_layout.addWidget(self.base_g_color_btn)
        base_color_layout.addLayout(base_g_layout)
        
        base_color_group.setLayout(base_color_layout)
        color_layout.addWidget(base_color_group)
        
        color_layout.addStretch()
        
        # 添加标签页
        tabs.addTab(structure_tab, "结构参数")
        tabs.addTab(color_tab, "颜色设置")
        
        layout.addWidget(tabs)
        
        # 控制按钮
        button_layout = QHBoxLayout()
        
        # 重置按钮
        reset_btn = QPushButton("重置")
        reset_btn.clicked.connect(self.reset)
        button_layout.addWidget(reset_btn)
        
        # 旋转按钮
        self.rotate_btn = QPushButton("开始旋转")
        self.rotate_btn.setCheckable(True)
        self.rotate_btn.clicked.connect(self.toggle_rotation)
        button_layout.addWidget(self.rotate_btn)
        
        # 保存按钮
        save_btn = QPushButton("保存图像")
        save_btn.clicked.connect(self.save_image)
        button_layout.addWidget(save_btn)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
        # 旋转定时器
        self.rotation_timer = QTimer()
        self.rotation_timer.timeout.connect(self.rotate_dna)
        self.rotation_angle = 0
    
    def radius_changed(self, value):
        radius = value / 2.0
        self.dna_viewer.set_helix_radius(radius)
        self.radius_value.setText(f"{radius:.1f}")
    
    def pitch_changed(self, value):
        self.dna_viewer.set_helix_pitch(value)
        self.pitch_value.setText(f"{value:.1f}")
    
    def twist_changed(self, value):
        self.dna_viewer.set_twist_angle(value)
        self.twist_value.setText(f"{value:.1f}°")
    
    def pairs_changed(self, value):
        self.dna_viewer.set_base_pairs(value)
    
    def backbone_changed(self, state):
        self.dna_viewer.set_show_backbone(state == Qt.Checked)
    
    def bases_changed(self, state):
        self.dna_viewer.set_show_bases(state == Qt.Checked)
    
    def hbonds_changed(self, state):
        self.dna_viewer.set_show_hydrogen_bonds(state == Qt.Checked)
    
    def labels_changed(self, state):
        self.dna_viewer.set_show_base_labels(state == Qt.Checked)
    
    def set_animation_mode(self, mode):
        # 更新按钮状态
        self.no_animation_btn.setChecked(mode == "none")
        self.replication_btn.setChecked(mode == "replication")
        self.transcription_btn.setChecked(mode == "transcription")
        
        # 设置动画模式
        self.dna_viewer.set_animation_mode(mode)
    
    def speed_changed(self, value):
        # 调整动画速度
        interval = 110 - value * 10  # 值越大，间隔越小，速度越快
        self.dna_viewer.animation_timer.setInterval(interval)
    
    def color_dialog(self, target):
        color = QColorDialog.getColor()
        if color.isValid():
            rgba = (color.red()/255, color.green()/255, color.blue()/255, 1.0)
            
            if target == 'backbone1':
                self.dna_viewer.set_backbone_color1(rgba)
                self.backbone1_color_btn.setStyleSheet(f"background-color: {color.name()}")
            elif target == 'backbone2':
                self.dna_viewer.set_backbone_color2(rgba)
                self.backbone2_color_btn.setStyleSheet(f"background-color: {color.name()}")
            elif target in ['A', 'T', 'C', 'G']:
                self.dna_viewer.set_base_color(target, rgba)
                btn = getattr(self, f'base_{target.lower()}_color_btn')
                btn.setStyleSheet(f"background-color: {color.name()}")
    
    def reset(self):
        # 重置参数
        self.radius_slider.setValue(4)
        self.pitch_slider.setValue(5)
        self.twist_slider.setValue(36)
        self.pairs_spin.setValue(20)
        self.backbone_check.setChecked(True)
        self.bases_check.setChecked(True)
        self.hbonds_check.setChecked(True)
        self.labels_check.setChecked(False)
        self.set_animation_mode("none")
        self.speed_slider.setValue(5)
        
        # 重置颜色
        self.dna_viewer.set_backbone_color1((0.2, 0.6, 1.0, 1.0))
        self.dna_viewer.set_backbone_color2((1.0, 0.2, 0.2, 1.0))
        self.dna_viewer.set_base_color('A', (1.0, 0.2, 0.2, 1.0))
        self.dna_viewer.set_base_color('T', (0.2, 1.0, 0.2, 1.0))
        self.dna_viewer.set_base_color('C', (0.2, 0.6, 1.0, 1.0))
        self.dna_viewer.set_base_color('G', (1.0, 0.8, 0.2, 1.0))
        
        self.backbone1_color_btn.setStyleSheet("background-color: rgb(51, 153, 255)")
        self.backbone2_color_btn.setStyleSheet("background-color: rgb(255, 51, 51)")
        self.base_a_color_btn.setStyleSheet("background-color: rgb(255, 51, 51)")
        self.base_t_color_btn.setStyleSheet("background-color: rgb(51, 255, 51)")
        self.base_c_color_btn.setStyleSheet("background-color: rgb(51, 153, 255)")
        self.base_g_color_btn.setStyleSheet("background-color: rgb(255, 204, 51)")
    
    def toggle_rotation(self, checked):
        if checked:
            self.rotation_timer.start(30)  # 约30fps
            self.rotate_btn.setText("停止旋转")
        else:
            self.rotation_timer.stop()
            self.rotate_btn.setText("开始旋转")
    
    def rotate_dna(self):
        self.rotation_angle += 1
        self.dna_viewer.setCameraPosition(
            elevation=10, 
            azimuth=self.rotation_angle, 
            distance=40
        )
    
    def save_image(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存图像", "", "PNG图像 (*.png);;JPEG图像 (*.jpg)"
        )
        if file_path:
            # 注意：pyqtgraph的GLViewWidget没有直接的截图方法
            # 这里需要根据具体实现来保存图像
            QMessageBox.information(self, "提示", "图像保存功能需要根据具体渲染后端实现")

# 主窗口
class AdvancedDNAVisualizer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle('高级DNA双螺旋结构可视化与分析工具 - 纪念詹姆斯·沃森')
        self.setGeometry(100, 100, 1400, 900)
        
        # 中央窗口
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QHBoxLayout()
        central_widget.setLayout(main_layout)
        
        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        # DNA查看器
        self.dna_viewer = AdvancedDNAHelixViewer()
        splitter.addWidget(self.dna_viewer)
        
        # 右侧面板
        right_panel = QWidget()
        right_layout = QVBoxLayout()
        right_panel.setLayout(right_layout)
        
        # 创建右侧标签页
        right_tabs = QTabWidget()
        
        # 控制面板
        self.control_panel = AdvancedControlPanel(self.dna_viewer)
        right_tabs.addTab(self.control_panel, "可视化控制")
        
        # 序列分析面板
        self.analysis_panel = SequenceAnalysisPanel(self.dna_viewer)
        right_tabs.addTab(self.analysis_panel, "序列分析")
        
        right_layout.addWidget(right_tabs)
        splitter.addWidget(right_panel)
        
        # 设置分割比例
        splitter.setSizes([1000, 400])
        
        # 状态栏信息
        self.statusBar().showMessage("纪念詹姆斯·沃森 (1928-2023) - DNA双螺旋结构共同发现者")
        
        # 添加菜单
        self.create_menus()

    def create_menus(self):
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu('文件')
        
        load_sequence_action = file_menu.addAction('加载序列文件')
        load_sequence_action.triggered.connect(self.load_sequence_file)
        
        save_settings_action = file_menu.addAction('保存设置')
        save_settings_action.triggered.connect(self.save_settings)
        
        load_settings_action = file_menu.addAction('加载设置')
        load_settings_action.triggered.connect(self.load_settings)
        
        file_menu.addSeparator()
        
        exit_action = file_menu.addAction('退出')
        exit_action.triggered.connect(self.close)
        
        # 帮助菜单
        help_menu = menubar.addMenu('帮助')
        
        about_action = help_menu.addAction('关于')
        about_action.triggered.connect(self.show_about)
        
        watson_info_action = help_menu.addAction('詹姆斯·沃森信息')
        watson_info_action.triggered.connect(self.show_watson_info)
    
    def load_sequence_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "打开DNA序列文件", "", "文本文件 (*.txt);;FASTA文件 (*.fasta);;所有文件 (*)"
        )
        if file_path:
            try:
                with open(file_path, 'r') as file:
                    content = file.read()
                    # 简单处理FASTA格式
                    if content.startswith('>'):
                        lines = content.split('\n')
                        sequence = ''.join(lines[1:])  # 跳过描述行
                    else:
                        sequence = content
                    
                    # 移除空白字符
                    sequence = ''.join(sequence.split())
                    
                    if DNATools.validate_sequence(sequence):
                        self.dna_viewer.set_sequence(sequence)
                        self.analysis_panel.sequence_input.setText(sequence)
                        self.statusBar().showMessage(f"已加载序列，长度: {len(sequence)}")
                    else:
                        QMessageBox.warning(self, "错误", "文件包含无效的DNA序列")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"无法读取文件: {str(e)}")
    
    def save_settings(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存设置", "", "JSON文件 (*.json)"
        )
        if file_path:
            settings = {
                'sequence': self.dna_viewer.sequence,
                'helix_radius': self.dna_viewer.helix_radius,
                'helix_pitch': self.dna_viewer.helix_pitch,
                'base_pairs': self.dna_viewer.base_pairs,
                'twist_angle': self.dna_viewer.twist_angle,
                'backbone_color1': self.dna_viewer.backbone_color1,
                'backbone_color2': self.dna_viewer.backbone_color2,
                'base_colors': self.dna_viewer.base_colors
            }
            try:
                with open(file_path, 'w') as file:
                    json.dump(settings, file, indent=2)
                QMessageBox.information(self, "成功", "设置已保存")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"无法保存设置: {str(e)}")
    
    def load_settings(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "加载设置", "", "JSON文件 (*.json)"
        )
        if file_path:
            try:
                with open(file_path, 'r') as file:
                    settings = json.load(file)
                
                # 应用设置
                if 'sequence' in settings:
                    self.dna_viewer.set_sequence(settings['sequence'])
                    self.analysis_panel.sequence_input.setText(settings['sequence'])
                
                # 更新其他参数...
                
                QMessageBox.information(self, "成功", "设置已加载")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"无法加载设置: {str(e)}")
    
    def show_about(self):
        about_text = """
        <h2>高级DNA双螺旋结构可视化与分析工具</h2>
        <p>版本 2.0</p>
        <p>这是一个功能强大的DNA双螺旋结构可视化与分析工具，</p>
        <p>提供3D结构可视化、序列分析、动画模拟等功能。</p>
        <p>纪念詹姆斯·沃森对DNA结构发现的重大贡献。</p>
        <p>开发基于: Python, PyQt5, PyQtGraph, NumPy</p>
        """
        QMessageBox.about(self, "关于", about_text)
    
    def show_watson_info(self):
        watson_text = """
        <h2>詹姆斯·沃森 (James Watson)</h2>
        <p><b>出生:</b> 1928年4月6日，美国芝加哥</p>
        <p><b>逝世:</b> 2025年11月8日</p>
        <p><b>著名成就:</b> 与弗朗西斯·克里克共同发现DNA双螺旋结构</p>
        <p><b>荣誉:</b> 1962年诺贝尔生理学或医学奖</p>
        <hr>
        <p>詹姆斯·沃森是一位美国分子生物学家、遗传学家和动物学家。</p>
        <p>1953年，他与弗朗西斯·克里克共同提出了DNA的双螺旋结构模型，</p>
        <p>这一发现被认为是20世纪最重要的科学成就之一，</p>
        <p>为现代分子生物学的发展奠定了基础。</p>
        <p>沃森后来还参与了人类基因组计划的领导工作。</p>
        """
        QMessageBox.information(self, "詹姆斯·沃森信息", watson_text)

def main():
    app = QApplication(sys.argv)
    
    # 设置应用程序样式
    app.setStyle('Fusion')
    
    # 设置应用程序字体
    font = QFont("Arial", 10)
    app.setFont(font)
    
    # 创建并显示主窗口
    window = AdvancedDNAVisualizer()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()