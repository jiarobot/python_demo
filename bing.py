# -*- coding: utf-8 -*-
"""
Created on Tue Jun 17 23:09:02 2025

@author: 10166
"""

import sys
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QPushButton, QTextEdit, QLabel, QTabWidget, QFileDialog, QSlider,
                            QGroupBox, QDoubleSpinBox, QComboBox, QSplitter, QProgressBar)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QColor
from collections import Counter
import random
import time
from scipy.fft import fft
from scipy.stats import gaussian_kde
import networkx as nx
from mpl_toolkits.mplot3d import Axes3D
import pygame
import io

# DNA序列生成函数（模拟真实基因序列）
def generate_dna_sequence(length=1000):
    bases = ['A', 'T', 'C', 'G']
    return ''.join(random.choices(bases, weights=[0.3, 0.3, 0.2, 0.2], k=length))

# DNA序列分析类
class DNAAnalyzer:
    def __init__(self, sequence):
        self.sequence = sequence.upper()
        self.length = len(sequence)
        
    def base_composition(self):
        counts = Counter(self.sequence)
        total = sum(counts.values())
        return {base: count/total for base, count in counts.items()}
    
    def gc_content(self):
        gc = self.sequence.count('G') + self.sequence.count('C')
        return gc / self.length
    
    def sequence_to_numeric(self):
        mapping = {'A': 0.0, 'T': 1.0, 'C': 2.0, 'G': 3.0}
        return [mapping.get(base, 0.0) for base in self.sequence]
    
    def find_patterns(self, pattern):
        pattern = pattern.upper()
        positions = []
        start = 0
        while start < self.length:
            pos = self.sequence.find(pattern, start)
            if pos == -1:
                break
            positions.append(pos)
            start = pos + 1
        return positions
    
    def generate_audio_wave(self):
        mapping = {'A': 261.63, 'T': 329.63, 'C': 392.00, 'G': 493.88}  # 音符频率 (C, E, G, B)
        sample_rate = 44100
        duration_per_base = 0.05  # 每个碱基的持续时间（秒）
        audio_data = []
        
        for base in self.sequence:
            if base in mapping:
                freq = mapping[base]
                t = np.linspace(0, duration_per_base, int(sample_rate * duration_per_base), endpoint=False)
                wave = 0.5 * np.sin(2 * np.pi * freq * t)
                audio_data.extend(wave)
        
        # 添加淡入淡出效果
        fade_samples = 500
        for i in range(fade_samples):
            audio_data[i] *= i / fade_samples
            audio_data[-(i+1)] *= i / fade_samples
            
        return np.array(audio_data)
    
    def calculate_entropy(self, window_size=100):
        entropy = []
        for i in range(0, self.length, window_size):
            segment = self.sequence[i:i+window_size]
            if len(segment) == 0:
                continue
            counts = Counter(segment)
            probs = [count/len(segment) for count in counts.values()]
            segment_entropy = -sum(p * np.log2(p) for p in probs if p > 0)
            entropy.append(segment_entropy)
        return entropy
    
    def predict_3d_structure(self):
        # 简化的3D结构预测（实际中会使用更复杂的生物信息学方法）
        length = min(100, self.length)
        x = np.linspace(0, 10, length)
        y = np.sin(x)
        z = np.cos(x) * np.sin(x)
        
        # 根据碱基类型调整颜色
        colors = []
        for base in self.sequence[:length]:
            if base == 'A': colors.append('red')
            elif base == 'T': colors.append('blue')
            elif base == 'C': colors.append('green')
            elif base == 'G': colors.append('yellow')
            else: colors.append('gray')
        
        return x, y, z, colors
    
    def evolutionary_analysis(self, sequences):
        # 简化的进化分析（实际中会使用更复杂的算法如UPGMA或Neighbor-Joining）
        graph = nx.Graph()
        graph.add_node("Original")
        
        for i, seq in enumerate(sequences):
            graph.add_node(f"Seq{i+1}")
            graph.add_edge("Original", f"Seq{i+1}", weight=random.uniform(0.1, 0.9))
            
        return graph


class DNAVisualizer(FigureCanvas):
    def __init__(self, parent=None, width=10, height=8, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        super().__init__(self.fig)
        self.setParent(parent)
        self.ax = self.fig.add_subplot(111)
        self.ax.set_facecolor('#0f1a26')
        self.fig.set_facecolor('#0f1a26')
        self.ax.tick_params(axis='both', colors='white')
        
    def plot_sequence(self, sequence):
        self.ax.clear()
        numeric_seq = DNAAnalyzer(sequence).sequence_to_numeric()
        
        # 创建热图式可视化
        bases = list(sequence)
        unique_bases = sorted(set(bases))
        base_to_index = {base: idx for idx, base in enumerate(unique_bases)}
        
        # 创建二维矩阵表示序列
        matrix = np.zeros((len(unique_bases), len(sequence)))
        for i, base in enumerate(sequence):
            matrix[base_to_index[base], i] = 1
            
        # 绘制热图
        cmap = plt.get_cmap('viridis')
        self.ax.imshow(matrix, aspect='auto', cmap=cmap)
        
        # 设置坐标轴标签
        self.ax.set_yticks(range(len(unique_bases)))
        self.ax.set_yticklabels(unique_bases, color='white', fontsize=12)
        self.ax.set_xlabel('Sequence Position', color='white', fontsize=12)
        self.ax.set_title('DNA Sequence Visualization', color='white', fontsize=14)
        
        self.draw()
        
    def plot_composition(self, composition):
        self.ax.clear()
        bases = list(composition.keys())
        percentages = [composition[base] * 100 for base in bases]
        
        # 设置颜色
        colors = {'A': '#FF6B6B', 'T': '#4ECDC4', 'C': '#45B7D1', 'G': '#FFD166'}
        bar_colors = [colors.get(base, '#888888') for base in bases]
        
        # 绘制条形图
        bars = self.ax.bar(bases, percentages, color=bar_colors)
        
        # 添加数值标签
        for bar in bars:
            height = bar.get_height()
            self.ax.text(bar.get_x() + bar.get_width()/2., height,
                        f'{height:.1f}%', ha='center', va='bottom', color='white', fontsize=12)
        
        self.ax.set_ylim(0, 60)
        self.ax.set_ylabel('Percentage (%)', color='white', fontsize=12)
        self.ax.set_title('Base Composition', color='white', fontsize=14)
        self.ax.set_facecolor('#0f1a26')
        self.ax.tick_params(axis='x', colors='white')
        self.ax.tick_params(axis='y', colors='white')
        
        self.draw()
        
    def plot_entropy(self, entropy):
        self.ax.clear()
        x = np.arange(len(entropy))
        self.ax.plot(x, entropy, color='#FF6B6B', linewidth=2)
        self.ax.fill_between(x, entropy, color='#FF6B6B', alpha=0.3)
        
        self.ax.set_xlabel('Segment', color='white', fontsize=12)
        self.ax.set_ylabel('Entropy', color='white', fontsize=12)
        self.ax.set_title('Sequence Entropy (Information Content)', color='white', fontsize=14)
        self.ax.grid(True, linestyle='--', alpha=0.3)
        self.ax.set_facecolor('#0f1a26')
        
        self.draw()
    
    def plot_audio_wave(self, audio_data):
        self.ax.clear()
        
        # 只绘制前5000个样本点
        plot_data = audio_data[:5000]
        x = np.arange(len(plot_data))
        
        self.ax.plot(x, plot_data, color='#45B7D1', linewidth=1)
        self.ax.fill_between(x, plot_data, color='#45B7D1', alpha=0.3)
        
        self.ax.set_xlabel('Sample', color='white', fontsize=12)
        self.ax.set_ylabel('Amplitude', color='white', fontsize=12)
        self.ax.set_title('DNA Sonification', color='white', fontsize=14)
        self.ax.grid(True, linestyle='--', alpha=0.2)
        self.ax.set_facecolor('#0f1a26')
        
        self.draw()
    
    def plot_3d_structure(self, x, y, z, colors):
        self.ax = self.fig.add_subplot(111, projection='3d')
        self.ax.clear()
        
        # 绘制3D结构
        self.ax.scatter(x, y, z, c=colors, s=50, alpha=0.8, depthshade=True)
        
        # 连接点
        for i in range(len(x)-1):
            self.ax.plot([x[i], x[i+1]], [y[i], y[i+1]], [z[i], z[i+1]], 
                        color='white', alpha=0.4, linewidth=1)
        
        # 设置图表属性
        self.ax.set_title('Predicted 3D Structure', color='white', fontsize=14)
        self.ax.set_facecolor('#0f1a26')
        self.ax.xaxis.pane.fill = False
        self.ax.yaxis.pane.fill = False
        self.ax.zaxis.pane.fill = False
        self.ax.grid(True, linestyle='--', alpha=0.2)
        
        # 设置坐标轴颜色
        self.ax.xaxis._axinfo["grid"].update({"color": (0.3, 0.3, 0.3, 0.2)})
        self.ax.yaxis._axinfo["grid"].update({"color": (0.3, 0.3, 0.3, 0.2)})
        self.ax.zaxis._axinfo["grid"].update({"color": (0.3, 0.3, 0.3, 0.2)})
        
        self.ax.tick_params(axis='x', colors='white')
        self.ax.tick_params(axis='y', colors='white')
        self.ax.tick_params(axis='z', colors='white')
        
        self.draw()
    
    def plot_evolution(self, graph):
        self.ax.clear()
        
        # 绘制进化树
        pos = nx.spring_layout(graph, seed=42)
        colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFD166', '#9B5DE5', '#F15BB5']
        node_colors = [colors[i % len(colors)] for i in range(len(graph.nodes))]
        
        nx.draw(graph, pos, ax=self.ax, with_labels=True, node_size=1200, 
               node_color=node_colors, font_size=10, font_color='white',
               edge_color='gray', width=2, alpha=0.8)
        
        self.ax.set_title('Evolutionary Relationships', color='white', fontsize=14)
        self.ax.set_facecolor('#0f1a26')
        
        self.draw()


class DNAAnalyzerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DNA Sequence Analyzer")
        self.setGeometry(100, 100, 1200, 800)
        self.setStyleSheet("background-color: #0f1a26; color: white;")
        
        # 初始化序列
        self.sequence = generate_dna_sequence(1000)
        self.analyzer = DNAAnalyzer(self.sequence)
        self.audio_data = None
        self.playing_audio = False
        
        # 初始化UI
        self.init_ui()
        
        # 初始化音频
        pygame.mixer.init()
        
        # 分析初始序列
        self.analyze_sequence()
        
    def init_ui(self):
        # 创建主布局
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)
        
        # 标题
        title = QLabel("DNA SEQUENCE ANALYZER")
        title.setFont(QFont("Arial", 20, QFont.Bold))
        title.setStyleSheet("color: #4ECDC4; padding: 10px;")
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)
        
        # 创建标签页
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: 0; }
            QTabBar::tab { 
                background: #1a2a3a; 
                color: white; 
                padding: 10px 20px;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
            }
            QTabBar::tab:selected { 
                background: #2a3a4a; 
                border-bottom: 2px solid #4ECDC4;
            }
        """)
        
        # 添加标签页
        self.overview_tab = QWidget()
        self.visualization_tab = QWidget()
        self.audio_tab = QWidget()
        self.structure_tab = QWidget()
        self.evolution_tab = QWidget()
        
        self.tabs.addTab(self.overview_tab, "Overview")
        self.tabs.addTab(self.visualization_tab, "Visualization")
        self.tabs.addTab(self.audio_tab, "Sonification")
        self.tabs.addTab(self.structure_tab, "3D Structure")
        self.tabs.addTab(self.evolution_tab, "Evolution")
        
        # 设置标签页内容
        self.setup_overview_tab()
        self.setup_visualization_tab()
        self.setup_audio_tab()
        self.setup_structure_tab()
        self.setup_evolution_tab()
        
        main_layout.addWidget(self.tabs)
        
        # 状态栏
        self.status_bar = self.statusBar()
        self.status_bar.setStyleSheet("background-color: #1a2a3a; color: white;")
        
        # 序列信息标签
        self.sequence_info = QLabel()
        self.sequence_info.setStyleSheet("padding: 5px; font-size: 12px;")
        self.status_bar.addPermanentWidget(self.sequence_info)
        
        # 更新序列信息
        self.update_sequence_info()
    
    def setup_overview_tab(self):
        layout = QVBoxLayout(self.overview_tab)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 序列显示区域
        seq_group = QGroupBox("DNA Sequence")
        seq_group.setStyleSheet("QGroupBox { color: #4ECDC4; font-size: 14px; }")
        seq_layout = QVBoxLayout()
        
        self.sequence_edit = QTextEdit()
        self.sequence_edit.setFont(QFont("Courier New", 10))
        self.sequence_edit.setStyleSheet("background-color: #1a2a3a; color: #FFD166;")
        self.sequence_edit.setPlainText(self.sequence)
        self.sequence_edit.textChanged.connect(self.sequence_updated)
        
        # 设置序列显示格式（每行80个字符）
        self.format_sequence_display()
        
        seq_layout.addWidget(self.sequence_edit)
        seq_group.setLayout(seq_layout)
        
        # 控制按钮
        btn_layout = QHBoxLayout()
        
        generate_btn = QPushButton("Generate Random Sequence")
        generate_btn.setStyleSheet(self.get_button_style())
        generate_btn.clicked.connect(self.generate_random_sequence)
        
        import_btn = QPushButton("Import Sequence")
        import_btn.setStyleSheet(self.get_button_style())
        import_btn.clicked.connect(self.import_sequence)
        
        analyze_btn = QPushButton("Analyze Sequence")
        analyze_btn.setStyleSheet(self.get_button_style("#FFD166"))
        analyze_btn.clicked.connect(self.analyze_sequence)
        
        btn_layout.addWidget(generate_btn)
        btn_layout.addWidget(import_btn)
        btn_layout.addWidget(analyze_btn)
        
        # 添加控件
        layout.addWidget(seq_group)
        layout.addLayout(btn_layout)
        
        # 添加统计信息面板
        stats_layout = QHBoxLayout()
        
        # 基本信息
        info_group = QGroupBox("Sequence Information")
        info_group.setStyleSheet("QGroupBox { color: #4ECDC4; font-size: 14px; }")
        info_layout = QVBoxLayout()
        
        self.length_label = QLabel("Length: ")
        self.gc_label = QLabel("GC Content: ")
        self.entropy_label = QLabel("Information Entropy: ")
        
        for label in [self.length_label, self.gc_label, self.entropy_label]:
            label.setStyleSheet("font-size: 12px; padding: 5px;")
            info_layout.addWidget(label)
        
        info_group.setLayout(info_layout)
        
        # 碱基组成
        comp_group = QGroupBox("Base Composition")
        comp_group.setStyleSheet("QGroupBox { color: #4ECDC4; font-size: 14px; }")
        comp_layout = QVBoxLayout()
        
        self.a_label = QLabel("A: ")
        self.t_label = QLabel("T: ")
        self.c_label = QLabel("C: ")
        self.g_label = QLabel("G: ")
        
        for label in [self.a_label, self.t_label, self.c_label, self.g_label]:
            label.setStyleSheet("font-size: 12px; padding: 5px;")
            comp_layout.addWidget(label)
        
        comp_group.setLayout(comp_layout)
        
        stats_layout.addWidget(info_group, 1)
        stats_layout.addWidget(comp_group, 1)
        
        layout.addLayout(stats_layout)
        
        # 添加可视化区域
        self.overview_canvas = DNAVisualizer(self.overview_tab, width=10, height=4)
        layout.addWidget(self.overview_canvas)
    
    def setup_visualization_tab(self):
        layout = QVBoxLayout(self.visualization_tab)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 创建可视化区域
        self.visual_canvas = DNAVisualizer(self.visualization_tab, width=10, height=6)
        layout.addWidget(self.visual_canvas)
        
        # 控制面板
        control_layout = QHBoxLayout()
        
        # 模式选择
        mode_label = QLabel("Visualization Mode:")
        mode_label.setStyleSheet("font-size: 12px;")
        
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Sequence Map", "Base Composition", "Entropy Analysis"])
        self.mode_combo.setStyleSheet("background-color: #1a2a3a; color: white;")
        self.mode_combo.currentIndexChanged.connect(self.update_visualization)
        
        # 窗口大小滑块（用于熵分析）
        self.window_slider = QSlider(Qt.Horizontal)
        self.window_slider.setRange(10, 500)
        self.window_slider.setValue(100)
        self.window_slider.setTickInterval(50)
        self.window_slider.setTickPosition(QSlider.TicksBelow)
        self.window_slider.valueChanged.connect(self.update_entropy_analysis)
        self.window_slider_label = QLabel("Window Size: 100")
        self.window_slider_label.setStyleSheet("font-size: 12px;")
        
        control_layout.addWidget(mode_label)
        control_layout.addWidget(self.mode_combo)
        control_layout.addStretch()
        control_layout.addWidget(self.window_slider_label)
        control_layout.addWidget(self.window_slider)
        
        layout.addLayout(control_layout)
    
    def setup_audio_tab(self):
        layout = QVBoxLayout(self.audio_tab)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 创建音频可视化区域
        self.audio_canvas = DNAVisualizer(self.audio_tab, width=10, height=4)
        layout.addWidget(self.audio_canvas)
        
        # 控制面板
        audio_control_layout = QHBoxLayout()
        
        # 播放/停止按钮
        self.play_btn = QPushButton("Play DNA Sonification")
        self.play_btn.setStyleSheet(self.get_button_style("#FF6B6B"))
        self.play_btn.clicked.connect(self.toggle_audio_playback)
        
        # 音调控制
        pitch_label = QLabel("Pitch Adjustment:")
        pitch_label.setStyleSheet("font-size: 12px;")
        
        self.pitch_slider = QSlider(Qt.Horizontal)
        self.pitch_slider.setRange(80, 120)
        self.pitch_slider.setValue(100)
        self.pitch_slider.setTickInterval(10)
        self.pitch_slider.setTickPosition(QSlider.TicksBelow)
        self.pitch_slider.valueChanged.connect(self.update_audio)
        
        audio_control_layout.addWidget(self.play_btn)
        audio_control_layout.addStretch()
        audio_control_layout.addWidget(pitch_label)
        audio_control_layout.addWidget(self.pitch_slider)
        
        layout.addLayout(audio_control_layout)
        
        # 描述文本
        desc_label = QLabel(
            "DNA Sonification: Each base (A, T, C, G) is mapped to a different musical note. "
            "The sequence is played as a melody to create an auditory representation of the DNA."
        )
        desc_label.setStyleSheet("font-size: 11px; font-style: italic; padding: 10px;")
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
    
    def setup_structure_tab(self):
        layout = QVBoxLayout(self.structure_tab)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 创建3D可视化区域
        self.structure_canvas = DNAVisualizer(self.structure_tab, width=10, height=8)
        layout.addWidget(self.structure_canvas)
        
        # 控制面板
        control_layout = QHBoxLayout()
        
        predict_btn = QPushButton("Predict 3D Structure")
        predict_btn.setStyleSheet(self.get_button_style("#9B5DE5"))
        predict_btn.clicked.connect(self.predict_structure)
        
        self.structure_info = QLabel("Predicted structure based on simplified model")
        self.structure_info.setStyleSheet("font-size: 12px; padding: 5px;")
        
        control_layout.addWidget(predict_btn)
        control_layout.addStretch()
        control_layout.addWidget(self.structure_info)
        
        layout.addLayout(control_layout)
    
    def setup_evolution_tab(self):
        layout = QVBoxLayout(self.evolution_tab)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 创建进化树可视化区域
        self.evolution_canvas = DNAVisualizer(self.evolution_tab, width=10, height=8)
        layout.addWidget(self.evolution_canvas)
        
        # 控制面板
        control_layout = QHBoxLayout()
        
        simulate_btn = QPushButton("Simulate Evolutionary Relationships")
        simulate_btn.setStyleSheet(self.get_button_style("#F15BB5"))
        simulate_btn.clicked.connect(self.simulate_evolution)
        
        self.evolution_info = QLabel("Evolutionary relationships based on sequence similarity")
        self.evolution_info.setStyleSheet("font-size: 12px; padding: 5px;")
        
        control_layout.addWidget(simulate_btn)
        control_layout.addStretch()
        control_layout.addWidget(self.evolution_info)
        
        layout.addLayout(control_layout)
    
    def get_button_style(self, color="#4ECDC4"):
        return f"""
            QPushButton {{
                background-color: {color};
                color: #0f1a26;
                border: none;
                padding: 8px 16px;
                font-size: 12px;
                font-weight: bold;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: #FFD166;
            }}
            QPushButton:pressed {{
                background-color: #FF6B6B;
            }}
        """
    
    def format_sequence_display(self):
        """格式化序列显示，每行80个字符"""
        seq = self.sequence_edit.toPlainText().replace('\n', '')
        formatted = '\n'.join(seq[i:i+80] for i in range(0, len(seq), 80))
        self.sequence_edit.blockSignals(True)  # 防止递归触发
        self.sequence_edit.setPlainText(formatted)
        self.sequence_edit.blockSignals(False)
    
    def sequence_updated(self):
        """当序列文本更新时调用"""
        # 移除所有非ATCG字符
        cleaned = ''.join(filter(lambda c: c in 'ATCGatcg', self.sequence_edit.toPlainText()))
        self.sequence = cleaned.upper()
        self.format_sequence_display()
        self.update_sequence_info()
    
    def generate_random_sequence(self):
        """生成随机DNA序列"""
        self.sequence = generate_dna_sequence(1000)
        self.sequence_edit.setPlainText(self.sequence)
        self.format_sequence_display()
        self.analyze_sequence()
    
    def import_sequence(self):
        """从文件导入序列"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open DNA Sequence", "", "FASTA Files (*.fasta *.fa);;Text Files (*.txt);;All Files (*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'r') as f:
                    # 跳过FASTA头部
                    lines = f.readlines()
                    sequence = ''.join(line.strip() for line in lines if not line.startswith('>'))
                    self.sequence = sequence.upper()
                    self.sequence_edit.setPlainText(self.sequence)
                    self.format_sequence_display()
                    self.analyze_sequence()
                    self.status_bar.showMessage(f"Loaded sequence from {file_path}", 3000)
            except Exception as e:
                self.status_bar.showMessage(f"Error loading file: {str(e)}", 5000)
    
    def analyze_sequence(self):
        """分析当前序列"""
        self.analyzer = DNAAnalyzer(self.sequence)
        self.update_sequence_info()
        
        # 更新可视化
        self.update_visualization()
        
        # 仅当序列不为空时生成音频
        if self.sequence:
            self.audio_data = self.analyzer.generate_audio_wave()
        else:
            self.audio_data = None
        
        # 更新音频可视化
        self.update_audio()
        
        # 更新状态
        self.status_bar.showMessage("Sequence analysis complete", 3000)
    
    def update_sequence_info(self):
        """更新序列信息显示"""
        self.analyzer = DNAAnalyzer(self.sequence)
        
        # 基本信息
        self.length_label.setText(f"Length: {len(self.sequence)} bases")
        gc_content = self.analyzer.gc_content()
        self.gc_label.setText(f"GC Content: {gc_content:.2%}")
        
        # 碱基组成
        composition = self.analyzer.base_composition()
        self.a_label.setText(f"A: {composition.get('A', 0):.2%}")
        self.t_label.setText(f"T: {composition.get('T', 0):.2%}")
        self.c_label.setText(f"C: {composition.get('C', 0):.2%}")
        self.g_label.setText(f"G: {composition.get('G', 0):.2%}")
        
        # 熵计算
        entropy = self.analyzer.calculate_entropy(100)
        avg_entropy = np.mean(entropy) if entropy else 0
        self.entropy_label.setText(f"Information Entropy: {avg_entropy:.4f} bits/base")
        
        # 状态栏信息
        self.sequence_info.setText(f"Sequence Length: {len(self.sequence)} bases | GC Content: {gc_content:.2%}")
    
    def update_visualization(self):
        """更新可视化标签页的内容"""
        if not self.sequence:
            return
            
        mode = self.mode_combo.currentIndex()
        
        if mode == 0:  # Sequence Map
            self.visual_canvas.plot_sequence(self.sequence)
            self.window_slider.setEnabled(False)
            self.window_slider_label.setEnabled(False)
        elif mode == 1:  # Base Composition
            composition = self.analyzer.base_composition()
            self.visual_canvas.plot_composition(composition)
            self.window_slider.setEnabled(False)
            self.window_slider_label.setEnabled(False)
        elif mode == 2:  # Entropy Analysis
            self.update_entropy_analysis()
            self.window_slider.setEnabled(True)
            self.window_slider_label.setEnabled(True)
    
    def update_entropy_analysis(self):
        """更新熵分析可视化"""
        if not self.sequence:
            return
            
        window_size = self.window_slider.value()
        self.window_slider_label.setText(f"Window Size: {window_size}")
        
        entropy = self.analyzer.calculate_entropy(window_size)
        self.visual_canvas.plot_entropy(entropy)
    
    def update_audio(self):
        """更新音频可视化"""
        # 修改为检查数组是否为空
        if self.audio_data is None or self.audio_data.size == 0:
            return
            
        # 调整音调
        pitch_factor = self.pitch_slider.value() / 100.0
        adjusted_audio = self.audio_data * pitch_factor
        
        # 绘制音频波形
        self.audio_canvas.plot_audio_wave(adjusted_audio)
    
    # 在 toggle_audio_playback 方法中也需要同样的修改
    def toggle_audio_playback(self):
        """切换音频播放状态"""
        # 修改为检查数组是否为空
        if self.audio_data is None or self.audio_data.size == 0:
            return
            
        if self.playing_audio:
            pygame.mixer.stop()  # 停止所有声音
            self.play_btn.setText("Play DNA Sonification")
            self.playing_audio = False
        else:
            # 调整音调
            pitch_factor = self.pitch_slider.value() / 100.0
            adjusted_audio = (self.audio_data * pitch_factor * 32767).astype(np.int16)
            
            # 将单声道转换为立体声格式
            stereo_audio = np.column_stack((adjusted_audio, adjusted_audio))
            
            # 重新初始化混音器
            pygame.mixer.quit()
            pygame.mixer.init(frequency=44100, size=-16, channels=2)  # 立体声
            
            # 创建并播放声音
            sound = pygame.sndarray.make_sound(stereo_audio)
            sound.play()
            
            self.play_btn.setText("Stop Playback")
            self.playing_audio = True
    
    def predict_structure(self):
        """预测并显示3D结构"""
        if not self.sequence:
            return
            
        # 显示进度
        self.structure_info.setText("Predicting 3D structure...")
        QApplication.processEvents()
        
        # 模拟预测过程
        time.sleep(1)
        
        # 获取预测结果
        x, y, z, colors = self.analyzer.predict_3d_structure()
        self.structure_canvas.plot_3d_structure(x, y, z, colors)
        
        self.structure_info.setText("Predicted 3D structure based on simplified model")
    
    def simulate_evolution(self):
        """模拟进化关系"""
        if not self.sequence:
            return
            
        # 显示进度
        self.evolution_info.setText("Simulating evolutionary relationships...")
        QApplication.processEvents()
        
        # 模拟进化分析
        time.sleep(1)
        
        # 生成一些随机序列作为"相关物种"
        sequences = [generate_dna_sequence(500) for _ in range(5)]
        graph = self.analyzer.evolutionary_analysis(sequences)
        
        self.evolution_canvas.plot_evolution(graph)
        self.evolution_info.setText("Evolutionary relationships based on sequence similarity")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 设置全局字体
    font = QFont("Arial", 10)
    app.setFont(font)
    
    # 创建并显示主窗口
    window = DNAAnalyzerApp()
    window.show()
    
    sys.exit(app.exec_())