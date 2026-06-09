import sys
import json
import math
import numpy as np
import os
from datetime import datetime, timedelta
from collections import deque

os.environ['QT_MULTIMEDIA_PREFERRED_PLUGINS'] = 'windowsmediafoundation'

from PyQt5.QtCore import (QPointF, Qt, QTimer, QUrl, pyqtSignal, QThread, 
                         QBuffer, QIODevice, QSettings, QSize, QRectF)
from PyQt5.QtGui import (QPainter, QColor, QLinearGradient, QPen, QFont, 
                        QPalette, QPixmap, QIcon, QKeySequence, QBrush,
                        QRadialGradient, QFontMetrics)
from PyQt5.QtMultimedia import QAudioFormat, QMediaPlayer, QMediaContent, QMediaPlaylist, QAudioProbe, QAudioBuffer
from PyQt5.QtMultimediaWidgets import QVideoWidget
from PyQt5.QtWidgets import (QApplication, QMainWindow, QStyle, QWidget, QVBoxLayout, 
                            QHBoxLayout, QPushButton, QSlider, QLabel, 
                            QListWidget, QListWidgetItem, QFileDialog, 
                            QMessageBox, QProgressBar, QSplitter, QFrame,
                            QGroupBox, QComboBox, QSpinBox, QCheckBox,
                            QScrollArea, QSizePolicy, QTabWidget, QAction,
                            QSystemTrayIcon, QMenu, QToolBar, QStatusBar,
                            QDialog, QDialogButtonBox, QFormLayout, QDoubleSpinBox,
                            QTextEdit, QGraphicsView, QGraphicsScene, QGraphicsPixmapItem,
                            QShortcut, QToolButton, QStackedWidget, QButtonGroup)

class PlaylistManager(QWidget):
    playlist_changed = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.playlist = QMediaPlaylist()
        self.current_playlist_file = None
        
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 播放列表标题
        title_label = QLabel("播放列表")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: white;")
        layout.addWidget(title_label)
        
        # 播放列表控件
        self.playlist_widget = QListWidget()
        self.playlist_widget.setStyleSheet("""
            QListWidget {
                background-color: #2a2a2a;
                color: white;
                border: 1px solid #555;
                border-radius: 5px;
            }
            QListWidget::item {
                padding: 5px;
                border-bottom: 1px solid #444;
            }
            QListWidget::item:selected {
                background-color: #4a4a4a;
            }
        """)
        self.playlist_widget.itemDoubleClicked.connect(self.play_selected_item)
        layout.addWidget(self.playlist_widget)
        
        # 播放列表控制按钮
        button_layout = QHBoxLayout()
        
        self.add_button = QPushButton("添加文件")
        self.add_button.clicked.connect(self.add_files)
        button_layout.addWidget(self.add_button)
        
        self.add_folder_button = QPushButton("添加文件夹")
        self.add_folder_button.clicked.connect(self.add_folder)
        button_layout.addWidget(self.add_folder_button)
        
        self.remove_button = QPushButton("移除选中")
        self.remove_button.clicked.connect(self.remove_selected)
        button_layout.addWidget(self.remove_button)
        
        self.clear_button = QPushButton("清空列表")
        self.clear_button.clicked.connect(self.clear_playlist)
        button_layout.addWidget(self.clear_button)
        
        layout.addLayout(button_layout)
        
        # 播放列表操作按钮
        playlist_ops_layout = QHBoxLayout()
        
        self.save_button = QPushButton("保存列表")
        self.save_button.clicked.connect(self.save_playlist)
        playlist_ops_layout.addWidget(self.save_button)
        
        self.load_button = QPushButton("加载列表")
        self.load_button.clicked.connect(self.load_playlist)
        playlist_ops_layout.addWidget(self.load_button)
        
        layout.addLayout(playlist_ops_layout)
        
        self.setLayout(layout)
        
    def add_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择音频文件", "", 
            "音频文件 (*.mp3 *.wav *.flac *.ogg *.m4a *.aac);;所有文件 (*)"
        )
        
        if files:
            for file in files:
                self.add_to_playlist(file)
                
    def add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "选择文件夹")
        
        if folder:
            # 支持的音频格式
            audio_extensions = ['.mp3', '.wav', '.flac', '.ogg', '.m4a', '.aac']
            
            for root, dirs, files in os.walk(folder):
                for file in files:
                    if any(file.lower().endswith(ext) for ext in audio_extensions):
                        file_path = os.path.join(root, file)
                        self.add_to_playlist(file_path)
                        
    def add_to_playlist(self, file_path):
        # 添加到QMediaPlaylist
        url = QUrl.fromLocalFile(file_path)
        content = QMediaContent(url)
        self.playlist.addMedia(content)
        
        # 添加到列表控件
        file_name = os.path.basename(file_path)
        item = QListWidgetItem(file_name)
        item.setData(Qt.UserRole, file_path)
        self.playlist_widget.addItem(item)
        
        self.playlist_changed.emit()
        
    def remove_selected(self):
        current_row = self.playlist_widget.currentRow()
        if current_row >= 0:
            self.playlist.removeMedia(current_row)
            self.playlist_widget.takeItem(current_row)
            self.playlist_changed.emit()
            
    def clear_playlist(self):
        self.playlist.clear()
        self.playlist_widget.clear()
        self.playlist_changed.emit()
        
    def play_selected_item(self, item):
        row = self.playlist_widget.row(item)
        self.playlist.setCurrentIndex(row)
        
    def save_playlist(self):
        if self.playlist_widget.count() == 0:
            QMessageBox.warning(self, "警告", "播放列表为空，无法保存")
            return
            
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存播放列表", "", "播放列表文件 (*.m3u)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write("#EXTM3U\n")
                    for i in range(self.playlist_widget.count()):
                        item = self.playlist_widget.item(i)
                        file_path = item.data(Qt.UserRole)
                        f.write(f"{file_path}\n")
                
                self.current_playlist_file = file_path
                QMessageBox.information(self, "成功", "播放列表保存成功")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"保存播放列表失败: {str(e)}")
                
    def load_playlist(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "加载播放列表", "", "播放列表文件 (*.m3u)"
        )
        
        if file_path:
            try:
                self.clear_playlist()
                
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                for line in lines:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        if os.path.exists(line):
                            self.add_to_playlist(line)
                
                self.current_playlist_file = file_path
                QMessageBox.information(self, "成功", "播放列表加载成功")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"加载播放列表失败: {str(e)}")

# 音频控制面板
class AudioControlPanel(QWidget):
    def __init__(self, player):
        super().__init__()
        self.player = player
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 音量控制
        volume_group = QGroupBox("音量控制")
        volume_layout = QVBoxLayout()
        
        volume_label_layout = QHBoxLayout()
        volume_label = QLabel("音量:")
        volume_label.setStyleSheet("color: white;")
        volume_label_layout.addWidget(volume_label)
        
        self.volume_value = QLabel("50%")
        self.volume_value.setStyleSheet("color: white;")
        volume_label_layout.addWidget(self.volume_value)
        volume_label_layout.addStretch()
        
        volume_layout.addLayout(volume_label_layout)
        
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(50)
        self.volume_slider.valueChanged.connect(self.set_volume)
        volume_layout.addWidget(self.volume_slider)
        
        volume_group.setLayout(volume_layout)
        layout.addWidget(volume_group)
        
        # 平衡控制
        balance_group = QGroupBox("声道平衡")
        balance_layout = QVBoxLayout()
        
        balance_label_layout = QHBoxLayout()
        balance_label = QLabel("平衡:")
        balance_label.setStyleSheet("color: white;")
        balance_label_layout.addWidget(balance_label)
        
        self.balance_value = QLabel("居中")
        self.balance_value.setStyleSheet("color: white;")
        balance_label_layout.addWidget(self.balance_value)
        balance_label_layout.addStretch()
        
        balance_layout.addLayout(balance_label_layout)
        
        self.balance_slider = QSlider(Qt.Horizontal)
        self.balance_slider.setRange(-100, 100)
        self.balance_slider.setValue(0)
        self.balance_slider.valueChanged.connect(self.set_balance)
        balance_layout.addWidget(self.balance_slider)
        
        balance_group.setLayout(balance_layout)
        layout.addWidget(balance_group)
        
        # 播放模式
        playback_group = QGroupBox("播放模式")
        playback_layout = QVBoxLayout()
        
        self.playback_mode = QComboBox()
        self.playback_mode.addItems(["顺序播放", "单曲循环", "随机播放"])
        self.playback_mode.currentIndexChanged.connect(self.set_playback_mode)
        playback_layout.addWidget(self.playback_mode)
        
        playback_group.setLayout(playback_layout)
        layout.addWidget(playback_group)
        
        # 音效设置
        effects_group = QGroupBox("音效设置")
        effects_layout = QVBoxLayout()
        
        # 低音增强
        bass_layout = QHBoxLayout()
        bass_label = QLabel("低音增强:")
        bass_label.setStyleSheet("color: white;")
        bass_layout.addWidget(bass_label)
        
        self.bass_boost = QCheckBox()
        self.bass_boost.stateChanged.connect(self.toggle_bass_boost)
        bass_layout.addWidget(self.bass_boost)
        bass_layout.addStretch()
        
        effects_layout.addLayout(bass_layout)
        
        # 均衡器预设
        eq_layout = QHBoxLayout()
        eq_label = QLabel("均衡器:")
        eq_label.setStyleSheet("color: white;")
        eq_layout.addWidget(eq_label)
        
        self.eq_preset = QComboBox()
        self.eq_preset.addItems(["无", "流行", "摇滚", "古典", "爵士", "自定义"])
        self.eq_preset.currentIndexChanged.connect(self.set_eq_preset)
        eq_layout.addWidget(self.eq_preset)
        
        effects_layout.addLayout(eq_layout)
        
        effects_group.setLayout(effects_layout)
        layout.addWidget(effects_group)
        
        layout.addStretch()
        self.setLayout(layout)
        
    def set_volume(self, value):
        self.player.setVolume(value)
        self.volume_value.setText(f"{value}%")
        
    def set_balance(self, value):
        # 注意：QMediaPlayer的平衡控制可能在某些平台上不可用
        if hasattr(self.player, 'setBalance'):
            self.player.setBalance(value / 100.0)
            
        if value == 0:
            self.balance_value.setText("居中")
        elif value < 0:
            self.balance_value.setText(f"左 {abs(value)}%")
        else:
            self.balance_value.setText(f"右 {value}%")
            
    def set_playback_mode(self, index):
        # 播放模式映射
        modes = [
            QMediaPlaylist.Sequential,
            QMediaPlaylist.CurrentItemInLoop,
            QMediaPlaylist.Random
        ]
        
        if index < len(modes):
            playlist = self.player.playlist()
            if playlist:
                playlist.setPlaybackMode(modes[index])
                
    def toggle_bass_boost(self, state):
        # 在实际应用中，这里应该实现低音增强算法
        if state == Qt.Checked:
            print("低音增强已启用")
        else:
            print("低音增强已禁用")
            
    def set_eq_preset(self, index):
        presets = {
            0: "无", 1: "流行", 2: "摇滚", 3: "古典", 4: "爵士", 5: "自定义"
        }
        print(f"均衡器预设: {presets.get(index, '未知')}")

# 音频分析线程（使用真实音频数据）
class AudioAnalyzerThread(QThread):
    analysis_updated = pyqtSignal(object)
    
    def __init__(self, player):
        super().__init__()
        self.player = player
        self.running = True
        self.audio_probe = QAudioProbe()
        self.audio_probe.setSource(player)
        self.audio_probe.audioBufferProbed.connect(self.process_buffer)
        
        # 音频数据缓冲区
        self.audio_data = deque(maxlen=2048)
        
    def process_buffer(self, buffer):
        """处理音频缓冲区数据"""
        if not self.running:
            return
            
        # 获取音频数据
        format = buffer.format()
        data = buffer.data()
        
        # 转换为numpy数组进行处理
        if format.sampleType() == QAudioFormat.SignedInt:
            dtype = np.int16
        elif format.sampleType() == QAudioFormat.UnSignedInt:
            dtype = np.uint8
        elif format.sampleType() == QAudioFormat.Float:
            dtype = np.float32
        else:
            return
            
        # 将 sip.voidptr 转换为 bytes
        byte_count = buffer.byteCount()
        if byte_count == 0:
            return
            
        # 将数据转换为字节数组
        data_bytes = data.asstring(byte_count)  # 使用 asstring 方法
        
        # 将数据转换为numpy数组
        audio_array = np.frombuffer(data_bytes, dtype=dtype)
        
        # 如果是多声道，取第一个声道
        if format.channelCount() > 1:
            audio_array = audio_array[::format.channelCount()]
            
        # 归一化
        if dtype == np.int16:
            audio_array = audio_array.astype(np.float32) / 32768.0
        elif dtype == np.uint8:
            audio_array = (audio_array.astype(np.float32) - 128) / 128.0
            
        self.audio_data.extend(audio_array)
        
    def run(self):
        while self.running:
            if len(self.audio_data) >= 1024 and self.player.state() == QMediaPlayer.PlayingState:
                # 获取最新的1024个样本
                data = np.array(list(self.audio_data)[-1024:])
                
                # 应用汉宁窗
                window = np.hanning(len(data))
                data = data * window
                
                # 执行FFT
                fft_data = np.abs(np.fft.rfft(data))
                fft_data = 20 * np.log10(fft_data + 1e-8)  # 转换为dB
                
                # 将频谱分为64个频段
                spectrum = []
                bands = 64
                for i in range(bands):
                    start = int(i * len(fft_data) / bands)
                    end = int((i + 1) * len(fft_data) / bands)
                    band_energy = np.mean(fft_data[start:end])
                    # 转换为0-100的范围
                    normalized = max(0, min(100, (band_energy + 80) * 100 / 80))
                    spectrum.append(normalized)
                
                # 计算RMS和峰值
                rms = np.sqrt(np.mean(data**2))
                peak = np.max(np.abs(data))
                
                analysis_data = {
                    'spectrum': spectrum,
                    'waveform': data.tolist(),
                    'rms': rms * 100,
                    'peak': peak * 100
                }
                
                self.analysis_updated.emit(analysis_data)
            
            self.msleep(30)  # 约33Hz更新频率
    
    def stop_analysis(self):
        self.running = False

# 高级频谱可视化
class AdvancedSpectrumWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumHeight(200)
        self.spectrum_data = [0] * 64
        self.waveform_data = [0] * 1024
        self.rms_value = 0
        self.peak_value = 0
        self.history = deque(maxlen=10)  # 历史数据用于平滑
        
        # 可视化模式
        self.mode = "bars"  # bars, circles, waves
        
        # 颜色主题
        self.theme = "default"
        
    def update_spectrum(self, analysis_data):
        self.spectrum_data = analysis_data['spectrum']
        self.waveform_data = analysis_data['waveform']
        self.rms_value = analysis_data['rms']
        self.peak_value = analysis_data['peak']
        
        # 添加到历史记录用于平滑
        self.history.append(self.spectrum_data)
        self.update()
        
    def set_visualization_mode(self, mode):
        self.mode = mode
        self.update()
        
    def set_theme(self, theme):
        self.theme = theme
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        width = self.width()
        height = self.height()
        
        # 设置颜色主题
        if self.theme == "default":
            bg_color = QColor(30, 30, 30)
            spectrum_colors = [QColor(255, 0, 0), QColor(255, 255, 0), QColor(0, 255, 0)]
            waveform_color = QColor(0, 200, 255)
        elif self.theme == "ocean":
            bg_color = QColor(0, 20, 40)
            spectrum_colors = [QColor(0, 100, 255), QColor(0, 200, 255), QColor(100, 255, 255)]
            waveform_color = QColor(0, 255, 200)
        else:  # fire
            bg_color = QColor(40, 20, 0)
            spectrum_colors = [QColor(255, 100, 0), QColor(255, 200, 0), QColor(255, 255, 100)]
            waveform_color = QColor(255, 100, 100)
        
        # 绘制背景
        painter.fillRect(0, 0, width, height, bg_color)
        
        if self.mode == "bars":
            self.draw_bar_spectrum(painter, width, height, spectrum_colors)
        elif self.mode == "circles":
            self.draw_circle_spectrum(painter, width, height, spectrum_colors)
        else:  # waves
            self.draw_wave_spectrum(painter, width, height, spectrum_colors)
            
        # 绘制波形
        self.draw_waveform(painter, width, height, waveform_color)
        
        # 绘制音频信息
        self.draw_audio_info(painter, width, height)
        
    def draw_bar_spectrum(self, painter, width, height, colors):
        """绘制柱状频谱"""
        bar_width = width / len(self.spectrum_data)
        gradient = QLinearGradient(0, 0, 0, height)
        gradient.setColorAt(0, colors[0])
        gradient.setColorAt(0.5, colors[1])
        gradient.setColorAt(1, colors[2])
        
        painter.setBrush(gradient)
        painter.setPen(Qt.NoPen)
        
        for i, value in enumerate(self.spectrum_data):
            # 使用平滑的历史数据
            if self.history:
                # 计算平均值
                avg_value = sum(hist[i] for hist in self.history) / len(self.history)
                bar_height = avg_value / 100 * height * 0.8
            else:
                bar_height = value / 100 * height * 0.8
                
            x = i * bar_width
            y = height - bar_height
            
            # 绘制圆角矩形
            painter.drawRoundedRect(int(x), int(y), int(bar_width - 1), int(bar_height), 2, 2)
            
    def draw_circle_spectrum(self, painter, width, height, colors):
        """绘制圆形频谱"""
        center_x = width / 2
        center_y = height / 2
        max_radius = min(width, height) * 0.4
        
        for i, value in enumerate(self.spectrum_data):
            # 使用平滑的历史数据
            if self.history:
                avg_value = sum(hist[i] for hist in self.history) / len(self.history)
                radius = avg_value / 100 * max_radius
            else:
                radius = value / 100 * max_radius
                
            angle = i * 2 * math.pi / len(self.spectrum_data)
            x = center_x + radius * math.cos(angle)
            y = center_y + radius * math.sin(angle)
            
            # 创建径向渐变
            gradient = QRadialGradient(x, y, 10)
            color_idx = int(value / 100 * (len(colors) - 1))
            gradient.setColorAt(0, colors[min(color_idx, len(colors)-1)])
            gradient.setColorAt(1, Qt.transparent)
            
            painter.setBrush(gradient)
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(QPointF(x, y), 10, 10)
            
    def draw_wave_spectrum(self, painter, width, height, colors):
        """绘制波形频谱"""
        if len(self.spectrum_data) < 2:
            return
            
        points_upper = []
        points_lower = []
        
        for i, value in enumerate(self.spectrum_data):
            # 使用平滑的历史数据
            if self.history:
                avg_value = sum(hist[i] for hist in self.history) / len(self.history)
                amplitude = avg_value / 100 * height * 0.4
            else:
                amplitude = value / 100 * height * 0.4
                
            x = i * width / len(self.spectrum_data)
            y_upper = height / 2 - amplitude
            y_lower = height / 2 + amplitude
            
            points_upper.append(QPointF(x, y_upper))
            points_lower.append(QPointF(x, y_lower))
            
        # 绘制上部波形
        gradient_upper = QLinearGradient(0, 0, 0, height/2)
        gradient_upper.setColorAt(0, colors[0])
        gradient_upper.setColorAt(1, Qt.transparent)
        
        painter.setBrush(gradient_upper)
        painter.setPen(QPen(colors[1], 2))
        
        upper_path = []
        for point in points_upper:
            upper_path.append(point)
        for point in reversed(points_lower):
            upper_path.append(point)
            
        if len(upper_path) > 1:
            painter.drawPolygon(*upper_path)
            
    def draw_waveform(self, painter, width, height, color):
        """绘制音频波形"""
        if len(self.waveform_data) < 2:
            return
            
        painter.setPen(QPen(color, 1))
        
        path_points = []
        for i, value in enumerate(self.waveform_data):
            if i >= len(self.waveform_data) * width / (width + 200):  # 限制点数以提高性能
                break
            x = i / len(self.waveform_data) * width
            y = height / 2 + value * height / 2
            path_points.append((x, y))
        
        for i in range(len(path_points) - 1):
            painter.drawLine(QPointF(path_points[i][0], path_points[i][1]), 
                            QPointF(path_points[i+1][0], path_points[i+1][1]))
            
    def draw_audio_info(self, painter, width, height):
        """绘制音频信息"""
        painter.setPen(QPen(QColor(255, 255, 255), 1))
        font = QFont("Arial", 10)
        painter.setFont(font)
        
        info_text = [
            f"RMS: {self.rms_value:.1f}",
            f"Peak: {self.peak_value:.1f}",
            f"Mode: {self.mode.title()}"
        ]
        
        for i, text in enumerate(info_text):
            painter.drawText(10, 20 + i * 20, text)

# 均衡器实现
class Equalizer(QWidget):
    def __init__(self, player):
        super().__init__()
        self.player = player
        self.bands = [0] * 10  # 10段均衡器
        self.presets = {
            "Flat": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            "Pop": [2, 1, 0, -1, -1, 0, 1, 2, 2, 1],
            "Rock": [4, 3, 2, 1, 0, 1, 2, 3, 4, 3],
            "Jazz": [1, 2, 3, 2, 1, 0, -1, -1, 0, 1],
            "Classical": [3, 2, 1, 0, -1, -1, 0, 1, 2, 3],
            "Bass Boost": [6, 5, 4, 2, 0, -2, -3, -4, -5, -6],
            "Treble Boost": [-6, -5, -4, -2, 0, 2, 4, 5, 6, 5]
        }
        
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 预设选择
        preset_layout = QHBoxLayout()
        preset_label = QLabel("预设:")
        preset_label.setStyleSheet("color: white;")
        preset_layout.addWidget(preset_label)
        
        self.preset_combo = QComboBox()
        self.preset_combo.addItems(self.presets.keys())
        self.preset_combo.currentTextChanged.connect(self.apply_preset)
        preset_layout.addWidget(self.preset_combo)
        
        preset_layout.addStretch()
        layout.addLayout(preset_layout)
        
        # 均衡器滑块
        bands_layout = QHBoxLayout()
        
        # 频率标签
        freqs = ["32", "64", "125", "250", "500", "1K", "2K", "4K", "8K", "16K"]
        freqs_layout = QHBoxLayout()
        for freq in freqs:
            label = QLabel(freq)
            label.setStyleSheet("color: white; font-size: 10px;")
            label.setAlignment(Qt.AlignCenter)
            freqs_layout.addWidget(label)
        
        layout.addLayout(freqs_layout)
        
        # 创建滑块
        self.sliders = []
        for i in range(10):
            band_layout = QVBoxLayout()
            
            # 值标签
            value_label = QLabel("0 dB")
            value_label.setStyleSheet("color: white; font-size: 10px;")
            value_label.setAlignment(Qt.AlignCenter)
            band_layout.addWidget(value_label)
            
            # 滑块
            slider = QSlider(Qt.Vertical)
            slider.setRange(-12, 12)
            slider.setValue(0)
            slider.setTickPosition(QSlider.TicksBothSides)
            slider.setTickInterval(3)
            slider.valueChanged.connect(lambda value, idx=i: self.band_changed(idx, value))
            self.sliders.append(slider)
            band_layout.addWidget(slider)
            
            # 频段标签
            band_label = QLabel(f"Band {i+1}")
            band_label.setStyleSheet("color: white; font-size: 10px;")
            band_label.setAlignment(Qt.AlignCenter)
            band_layout.addWidget(band_label)
            
            bands_layout.addLayout(band_layout)
        
        layout.addLayout(bands_layout)
        self.setLayout(layout)
        
    def band_changed(self, band_idx, value):
        self.bands[band_idx] = value
        self.sliders[band_idx].setToolTip(f"{value} dB")
        
        # 更新标签
        layout = self.sliders[band_idx].parent().layout()
        if layout:
            value_label = layout.itemAt(0).widget()
            if value_label:
                value_label.setText(f"{value} dB")
                
        # 在实际应用中，这里应该应用均衡器设置到音频流
        print(f"Band {band_idx+1} set to {value} dB")
        
    def apply_preset(self, preset_name):
        if preset_name in self.presets:
            preset_values = self.presets[preset_name]
            for i, value in enumerate(preset_values):
                self.sliders[i].setValue(value)

# 歌词显示组件
class LyricsWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.current_lyrics = []
        self.current_index = -1
        self.lyrics_file = None
        
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 歌词显示区域
        self.lyrics_display = QTextEdit()
        self.lyrics_display.setReadOnly(True)
        self.lyrics_display.setStyleSheet("""
            QTextEdit {
                background-color: #1a1a1a;
                color: white;
                border: 1px solid #555;
                border-radius: 5px;
                font-size: 14px;
            }
        """)
        layout.addWidget(self.lyrics_display)
        
        # 控制按钮
        control_layout = QHBoxLayout()
        
        self.load_button = QPushButton("加载歌词")
        self.load_button.clicked.connect(self.load_lyrics_file)
        control_layout.addWidget(self.load_button)
        
        self.sync_button = QPushButton("同步歌词")
        self.sync_button.clicked.connect(self.sync_lyrics)
        control_layout.addWidget(self.sync_button)
        
        layout.addLayout(control_layout)
        self.setLayout(layout)
        
    def load_lyrics_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择歌词文件", "", "歌词文件 (*.lrc *.txt)"
        )
        
        if file_path:
            self.lyrics_file = file_path
            self.parse_lyrics(file_path)
            
    def parse_lyrics(self, file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            self.current_lyrics = []
            lines = content.split('\n')
            
            for line in lines:
                line = line.strip()
                if line and ']' in line:
                    # 解析时间标签和歌词
                    parts = line.split(']')
                    time_str = parts[0][1:]  # 去掉开头的[
                    lyric = parts[-1]
                    
                    # 解析时间 (格式: [mm:ss.xx])
                    if ':' in time_str and '.' in time_str:
                        try:
                            minutes, rest = time_str.split(':')
                            seconds, milliseconds = rest.split('.')
                            total_ms = (int(minutes) * 60 + int(seconds)) * 1000 + int(milliseconds) * 10
                            self.current_lyrics.append((total_ms, lyric))
                        except ValueError:
                            continue
                            
            # 按时间排序
            self.current_lyrics.sort(key=lambda x: x[0])
            
            # 显示歌词
            self.display_lyrics()
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载歌词文件失败: {str(e)}")
            
    def display_lyrics(self):
        if not self.current_lyrics:
            self.lyrics_display.setPlainText("暂无歌词")
            return
            
        text = ""
        for time_ms, lyric in self.current_lyrics:
            minutes = time_ms // 60000
            seconds = (time_ms % 60000) // 1000
            text += f"[{minutes:02d}:{seconds:02d}] {lyric}\n"
            
        self.lyrics_display.setPlainText(text)
        
    def sync_lyrics(self, position):
        if not self.current_lyrics:
            return
            
        # 查找当前时间对应的歌词
        new_index = -1
        for i, (time_ms, lyric) in enumerate(self.current_lyrics):
            if position >= time_ms:
                new_index = i
            else:
                break
                
        if new_index != self.current_index and new_index >= 0:
            self.current_index = new_index
            self.highlight_current_lyric()
            
    def highlight_current_lyric(self):
        if not self.current_lyrics or self.current_index < 0:
            return
            
        # 在实际应用中，这里应该高亮显示当前歌词
        time_ms, lyric = self.current_lyrics[self.current_index]
        print(f"当前歌词: {lyric}")

# 专辑封面显示
class AlbumCoverWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.cover_pixmap = None
        self.default_cover = self.create_default_cover()
        
        self.setMinimumSize(200, 200)
        
    def create_default_cover(self):
        """创建默认专辑封面"""
        pixmap = QPixmap(200, 200)
        pixmap.fill(QColor(50, 50, 50))
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 绘制音乐图标
        painter.setPen(QPen(QColor(100, 100, 100), 2))
        painter.drawEllipse(50, 50, 100, 100)
        
        # 绘制音符
        painter.drawLine(80, 70, 80, 130)
        painter.drawLine(80, 70, 100, 90)
        painter.drawLine(100, 90, 120, 70)
        
        painter.end()
        return pixmap
        
    def set_cover(self, file_path):
        """设置专辑封面"""
        if file_path and os.path.exists(file_path):
            self.cover_pixmap = QPixmap(file_path)
        else:
            self.cover_pixmap = None
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 绘制背景
        painter.fillRect(self.rect(), QColor(40, 40, 40))
        
        # 绘制专辑封面
        if self.cover_pixmap and not self.cover_pixmap.isNull():
            pixmap = self.cover_pixmap.scaled(
                self.width() - 20, self.height() - 20, 
                Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            
            x = (self.width() - pixmap.width()) // 2
            y = (self.height() - pixmap.height()) // 2
            
            # 绘制阴影
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(0, 0, 0, 100))
            painter.drawRoundedRect(x + 3, y + 3, pixmap.width(), pixmap.height(), 5, 5)
            
            # 绘制封面
            painter.drawPixmap(x, y, pixmap)
        else:
            # 绘制默认封面
            pixmap = self.default_cover.scaled(
                self.width() - 20, self.height() - 20,
                Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            x = (self.width() - pixmap.width()) // 2
            y = (self.height() - pixmap.height()) // 2
            painter.drawPixmap(x, y, pixmap)

# 睡眠定时器
class SleepTimerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("睡眠定时器")
        self.setModal(True)
        
        self.init_ui()
        
    def init_ui(self):
        layout = QFormLayout()
        
        # 时间设置
        self.minutes_spin = QSpinBox()
        self.minutes_spin.setRange(1, 180)
        self.minutes_spin.setValue(30)
        self.minutes_spin.setSuffix(" 分钟")
        layout.addRow("定时时间:", self.minutes_spin)
        
        # 动作选择
        self.action_combo = QComboBox()
        self.action_combo.addItems(["暂停播放", "停止播放", "关闭程序"])
        layout.addRow("定时动作:", self.action_combo)
        
        # 按钮
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addRow(button_box)
        
        self.setLayout(layout)
        
    def get_settings(self):
        return {
            'minutes': self.minutes_spin.value(),
            'action': self.action_combo.currentText()
        }

# 播放统计
class PlaybackStatistics(QWidget):
    def __init__(self):
        super().__init__()
        self.stats = {
            'total_play_time': 0,  # 总播放时间（秒）
            'songs_played': 0,     # 播放歌曲数量
            'favorite_songs': [],  # 最喜欢的歌曲
        }
        
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 统计信息显示
        self.stats_display = QTextEdit()
        self.stats_display.setReadOnly(True)
        self.stats_display.setStyleSheet("""
            QTextEdit {
                background-color: #1a1a1a;
                color: white;
                border: 1px solid #555;
                border-radius: 5px;
                font-size: 12px;
            }
        """)
        layout.addWidget(self.stats_display)
        
        self.setLayout(layout)
        self.update_display()
        
    def update_display(self):
        hours = self.stats['total_play_time'] // 3600
        minutes = (self.stats['total_play_time'] % 3600) // 60
        
        text = f"""播放统计:
总播放时间: {hours}小时{minutes}分钟
播放歌曲数: {self.stats['songs_played']}
最喜欢的歌曲: {', '.join(self.stats['favorite_songs'][:5]) if self.stats['favorite_songs'] else '无'}
"""
        self.stats_display.setPlainText(text)
        
    def add_play_time(self, seconds):
        self.stats['total_play_time'] += seconds
        self.update_display()
        
    def add_song_played(self, song_name):
        self.stats['songs_played'] += 1
        # 简单的喜好统计（播放次数最多的歌曲）
        if song_name not in self.stats['favorite_songs']:
            self.stats['favorite_songs'].append(song_name)
        self.update_display()

# 增强的播放列表管理器
class EnhancedPlaylistManager(PlaylistManager):
    def __init__(self):
        super().__init__()
        # 添加快捷键支持
        self.setup_shortcuts()
        
    def setup_shortcuts(self):
        # 添加快捷键
        self.delete_shortcut = QShortcut(QKeySequence.Delete, self.playlist_widget)
        self.delete_shortcut.activated.connect(self.remove_selected)
        
        self.clear_shortcut = QShortcut(QKeySequence("Ctrl+Shift+Delete"), self.playlist_widget)
        self.clear_shortcut.activated.connect(self.clear_playlist)

# 主题管理器
class ThemeManager:
    @staticmethod
    def get_theme(theme_name):
        themes = {
            "dark": """
                QMainWindow, QWidget {
                    background-color: #2b2b2b;
                    color: #ffffff;
                }
                QPushButton {
                    background-color: #404040;
                    color: white;
                    border: 1px solid #555;
                    padding: 5px 10px;
                    border-radius: 3px;
                }
                QPushButton:hover {
                    background-color: #505050;
                }
                QPushButton:pressed {
                    background-color: #606060;
                }
                QSlider::groove:horizontal {
                    border: 1px solid #555;
                    height: 5px;
                    background: #404040;
                    border-radius: 2px;
                }
                QSlider::handle:horizontal {
                    background: #ddd;
                    border: 1px solid #777;
                    width: 12px;
                    margin: -5px 0;
                    border-radius: 6px;
                }
                QGroupBox {
                    border: 1px solid #555;
                    border-radius: 5px;
                    margin-top: 10px;
                    padding-top: 10px;
                    color: white;
                    font-weight: bold;
                }
                QListWidget {
                    background-color: #2a2a2a;
                    color: white;
                    border: 1px solid #555;
                    border-radius: 5px;
                }
            """,
            "light": """
                QMainWindow, QWidget {
                    background-color: #f0f0f0;
                    color: #000000;
                }
                QPushButton {
                    background-color: #e0e0e0;
                    color: black;
                    border: 1px solid #ccc;
                    padding: 5px 10px;
                    border-radius: 3px;
                }
                QPushButton:hover {
                    background-color: #d0d0d0;
                }
                QPushButton:pressed {
                    background-color: #c0c0c0;
                }
                QSlider::groove:horizontal {
                    border: 1px solid #ccc;
                    height: 5px;
                    background: #e0e0e0;
                    border-radius: 2px;
                }
                QSlider::handle:horizontal {
                    background: #fff;
                    border: 1px solid #aaa;
                    width: 12px;
                    margin: -5px 0;
                    border-radius: 6px;
                }
                QGroupBox {
                    border: 1px solid #ccc;
                    border-radius: 5px;
                    margin-top: 10px;
                    padding-top: 10px;
                    color: black;
                    font-weight: bold;
                }
                QListWidget {
                    background-color: #ffffff;
                    color: black;
                    border: 1px solid #ccc;
                    border-radius: 5px;
                }
            """,
            "blue": """
                QMainWindow, QWidget {
                    background-color: #1e3a5f;
                    color: #ffffff;
                }
                QPushButton {
                    background-color: #2a4a7a;
                    color: white;
                    border: 1px solid #3a5a8a;
                    padding: 5px 10px;
                    border-radius: 3px;
                }
                QPushButton:hover {
                    background-color: #3a5a9a;
                }
                QPushButton:pressed {
                    background-color: #4a6aaa;
                }
                QSlider::groove:horizontal {
                    border: 1px solid #3a5a8a;
                    height: 5px;
                    background: #2a4a7a;
                    border-radius: 2px;
                }
                QSlider::handle:horizontal {
                    background: #4a8aff;
                    border: 1px solid #2a6aff;
                    width: 12px;
                    margin: -5px 0;
                    border-radius: 6px;
                }
                QGroupBox {
                    border: 1px solid #3a5a8a;
                    border-radius: 5px;
                    margin-top: 10px;
                    padding-top: 10px;
                    color: white;
                    font-weight: bold;
                }
                QListWidget {
                    background-color: #2a4a7a;
                    color: white;
                    border: 1px solid #3a5a8a;
                    border-radius: 5px;
                }
            """
        }
        
        return themes.get(theme_name, themes["dark"])

# 主播放器界面（增强版）
class EnhancedMusicPlayer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("高级音乐播放器 - 增强版")
        self.setGeometry(100, 100, 1400, 900)
        
        # 设置和状态
        self.settings = QSettings("MusicPlayer", "EnhancedMusicPlayer")
        self.sleep_timer = None
        self.current_theme = "dark"
        
        # 初始化组件
        self.init_components()
        self.init_ui()
        self.connect_signals()
        self.apply_settings()
        
        # 系统托盘
        self.init_tray_icon()
        
    def init_components(self):
        # 媒体播放器
        self.player = QMediaPlayer()
        self.playlist_manager = EnhancedPlaylistManager()
        self.player.setPlaylist(self.playlist_manager.playlist)
        
        # 音频分析器
        self.analyzer_thread = AudioAnalyzerThread(self.player)
        self.analyzer_thread.analysis_updated.connect(self.update_visualization)
        
        # 其他组件
        self.spectrum_widget = AdvancedSpectrumWidget()
        self.equalizer = Equalizer(self.player)
        self.lyrics_widget = LyricsWidget()
        self.album_cover = AlbumCoverWidget()
        self.stats_widget = PlaybackStatistics()
        
    def init_ui(self):
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        main_layout = QHBoxLayout(central_widget)
        
        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        
        # 左侧面板（播放列表和音频控制）
        left_panel = self.create_left_panel()
        splitter.addWidget(left_panel)
        
        # 右侧面板（播放控制和可视化）
        right_panel = self.create_right_panel()
        splitter.addWidget(right_panel)
        
        # 设置分割器比例
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        
        main_layout.addWidget(splitter)
        
        # 创建菜单栏
        self.create_menubar()
        
        # 创建工具栏
        self.create_toolbar()
        
        # 创建状态栏
        self.create_statusbar()
        
    def create_left_panel(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 播放列表
        layout.addWidget(self.playlist_manager)
        
        # 音频控制面板
        audio_control = AudioControlPanel(self.player)
        layout.addWidget(audio_control)
        
        # 均衡器
        eq_group = QGroupBox("均衡器")
        eq_layout = QVBoxLayout()
        eq_layout.addWidget(self.equalizer)
        eq_group.setLayout(eq_layout)
        layout.addWidget(eq_group)
        
        return widget
        
    def create_right_panel(self):
        # 使用选项卡组织右侧内容
        tab_widget = QTabWidget()
        
        # 播放选项卡
        play_tab = self.create_play_tab()
        tab_widget.addTab(play_tab, "播放")
        
        # 可视化选项卡
        viz_tab = self.create_visualization_tab()
        tab_widget.addTab(viz_tab, "可视化")
        
        # 歌词选项卡
        tab_widget.addTab(self.lyrics_widget, "歌词")
        
        # 统计选项卡
        tab_widget.addTab(self.stats_widget, "统计")
        
        return tab_widget
        
    def create_play_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 专辑封面
        layout.addWidget(self.album_cover)
        
        # 歌曲信息
        info_group = QGroupBox("歌曲信息")
        info_layout = QVBoxLayout()
        
        self.song_title = QLabel("未播放")
        self.song_title.setStyleSheet("font-size: 18px; font-weight: bold;")
        self.song_title.setAlignment(Qt.AlignCenter)
        info_layout.addWidget(self.song_title)
        
        self.song_artist = QLabel("艺术家未知")
        self.song_artist.setAlignment(Qt.AlignCenter)
        info_layout.addWidget(self.song_artist)
        
        self.song_album = QLabel("专辑未知")
        self.song_album.setAlignment(Qt.AlignCenter)
        info_layout.addWidget(self.song_album)
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # 播放进度
        progress_layout = QVBoxLayout()
        
        self.progress_slider = QSlider(Qt.Horizontal)
        self.progress_slider.setRange(0, 100)
        self.progress_slider.sliderMoved.connect(self.set_position)
        progress_layout.addWidget(self.progress_slider)
        
        # 时间显示
        time_layout = QHBoxLayout()
        self.current_time = QLabel("00:00")
        self.total_time = QLabel("00:00")
        time_layout.addWidget(self.current_time)
        time_layout.addStretch()
        time_layout.addWidget(self.total_time)
        progress_layout.addLayout(time_layout)
        
        layout.addLayout(progress_layout)
        
        # 播放控制
        control_layout = self.create_control_buttons()
        layout.addLayout(control_layout)
        
        layout.addStretch()
        return widget
        
    def create_visualization_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 可视化控制
        viz_control_layout = QHBoxLayout()
        
        # 可视化模式选择
        mode_label = QLabel("可视化模式:")
        mode_label.setStyleSheet("color: white;")
        viz_control_layout.addWidget(mode_label)
        
        self.viz_mode_combo = QComboBox()
        self.viz_mode_combo.addItems(["柱状图", "圆形", "波形"])
        self.viz_mode_combo.currentTextChanged.connect(self.change_viz_mode)
        viz_control_layout.addWidget(self.viz_mode_combo)
        
        # 主题选择
        theme_label = QLabel("主题:")
        theme_label.setStyleSheet("color: white;")
        viz_control_layout.addWidget(theme_label)
        
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["默认", "海洋", "火焰"])
        self.theme_combo.currentTextChanged.connect(self.change_theme)
        viz_control_layout.addWidget(self.theme_combo)
        
        viz_control_layout.addStretch()
        layout.addLayout(viz_control_layout)
        
        # 频谱显示
        layout.addWidget(self.spectrum_widget)
        
        return widget
        
    def create_control_buttons(self):
        layout = QHBoxLayout()
        
        # 播放控制按钮
        buttons = [
            ("上一首", self.previous_song, "Ctrl+Left"),
            ("播放", self.toggle_play, "Space"),
            ("暂停", self.pause, "Ctrl+P"),
            ("停止", self.stop, "Ctrl+S"),
            ("下一首", self.next_song, "Ctrl+Right"),
        ]
        
        for text, slot, shortcut in buttons:
            btn = QPushButton(text)
            btn.clicked.connect(slot)
            if shortcut:
                QShortcut(QKeySequence(shortcut), self).activated.connect(slot)
            layout.addWidget(btn)
            
            # 保存播放按钮的引用
            if text == "播放":
                self.play_button = btn
                
        return layout
        
    def create_menubar(self):
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu("文件")
        
        open_file_action = QAction("打开文件", self)
        open_file_action.setShortcut("Ctrl+O")
        open_file_action.triggered.connect(self.playlist_manager.add_files)
        file_menu.addAction(open_file_action)
        
        open_folder_action = QAction("打开文件夹", self)
        open_folder_action.setShortcut("Ctrl+Shift+O")
        open_folder_action.triggered.connect(self.playlist_manager.add_folder)
        file_menu.addAction(open_folder_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("退出", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 播放菜单
        play_menu = menubar.addMenu("播放")
        
        play_action = QAction("播放/暂停", self)
        play_action.setShortcut("Space")
        play_action.triggered.connect(self.toggle_play)
        play_menu.addAction(play_action)
        
        stop_action = QAction("停止", self)
        stop_action.setShortcut("Ctrl+S")
        stop_action.triggered.connect(self.stop)
        play_menu.addAction(stop_action)
        
        play_menu.addSeparator()
        
        prev_action = QAction("上一首", self)
        prev_action.setShortcut("Ctrl+Left")
        prev_action.triggered.connect(self.previous_song)
        play_menu.addAction(prev_action)
        
        next_action = QAction("下一首", self)
        next_action.setShortcut("Ctrl+Right")
        next_action.triggered.connect(self.next_song)
        play_menu.addAction(next_action)
        
        # 工具菜单
        tools_menu = menubar.addMenu("工具")
        
        sleep_timer_action = QAction("睡眠定时器", self)
        sleep_timer_action.triggered.connect(self.show_sleep_timer)
        tools_menu.addAction(sleep_timer_action)
        
        # 视图菜单
        view_menu = menubar.addMenu("视图")
        
        theme_menu = view_menu.addMenu("主题")
        
        dark_theme_action = QAction("深色", self)
        dark_theme_action.triggered.connect(lambda: self.change_application_theme("dark"))
        theme_menu.addAction(dark_theme_action)
        
        light_theme_action = QAction("浅色", self)
        light_theme_action.triggered.connect(lambda: self.change_application_theme("light"))
        theme_menu.addAction(light_theme_action)
        
        blue_theme_action = QAction("蓝色", self)
        blue_theme_action.triggered.connect(lambda: self.change_application_theme("blue"))
        theme_menu.addAction(blue_theme_action)
        
    def create_toolbar(self):
        toolbar = QToolBar("主工具栏")
        self.addToolBar(toolbar)
        
        # 添加常用工具按钮
        play_btn = QToolButton()
        play_btn.setText("播放")
        play_btn.clicked.connect(self.toggle_play)
        toolbar.addWidget(play_btn)
        
        stop_btn = QToolButton()
        stop_btn.setText("停止")
        stop_btn.clicked.connect(self.stop)
        toolbar.addWidget(stop_btn)
        
        toolbar.addSeparator()
        
        # 音量控制
        volume_label = QLabel("音量:")
        toolbar.addWidget(volume_label)
        
        volume_slider = QSlider(Qt.Horizontal)
        volume_slider.setRange(0, 100)
        volume_slider.setValue(50)
        volume_slider.setFixedWidth(100)
        volume_slider.valueChanged.connect(self.player.setVolume)
        toolbar.addWidget(volume_slider)
        
    def create_statusbar(self):
        statusbar = QStatusBar()
        self.setStatusBar(statusbar)
        
        # 播放状态
        self.status_label = QLabel("就绪")
        statusbar.addWidget(self.status_label)
        
        # 歌曲信息
        self.song_info_label = QLabel("")
        statusbar.addPermanentWidget(self.song_info_label)
        
    def init_tray_icon(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
            
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        
        # 创建托盘菜单
        tray_menu = QMenu(self)
        
        play_action = tray_menu.addAction("播放/暂停")
        play_action.triggered.connect(self.toggle_play)
        
        stop_action = tray_menu.addAction("停止")
        stop_action.triggered.connect(self.stop)
        
        tray_menu.addSeparator()
        
        show_action = tray_menu.addAction("显示窗口")
        show_action.triggered.connect(self.show)
        
        hide_action = tray_menu.addAction("隐藏窗口")
        hide_action.triggered.connect(self.hide)
        
        tray_menu.addSeparator()
        
        quit_action = tray_menu.addAction("退出")
        quit_action.triggered.connect(self.close)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.tray_icon_activated)
        self.tray_icon.show()
        
    def tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            if self.isVisible():
                self.hide()
            else:
                self.show()
                self.raise_()
                self.activateWindow()
                
    def connect_signals(self):
        # 播放器信号
        self.player.positionChanged.connect(self.position_changed)
        self.player.durationChanged.connect(self.duration_changed)
        self.player.stateChanged.connect(self.state_changed)
        self.player.currentMediaChanged.connect(self.media_changed)
        self.player.error.connect(self.player_error)
        
        # 播放列表信号
        self.playlist_manager.playlist_changed.connect(self.playlist_updated)
        
    def toggle_play(self):
        if self.player.state() == QMediaPlayer.PlayingState:
            self.player.pause()
        else:
            self.player.play()
            if not self.analyzer_thread.isRunning():
                self.analyzer_thread.start()
                
    def pause(self):
        self.player.pause()
        
    def stop(self):
        self.player.stop()
        
    def previous_song(self):
        playlist = self.player.playlist()
        if playlist and playlist.currentIndex() > 0:
            playlist.previous()
            
    def next_song(self):
        playlist = self.player.playlist()
        if playlist and playlist.currentIndex() < playlist.mediaCount() - 1:
            playlist.next()
            
    def set_position(self, position):
        if self.player.duration() > 0:
            self.player.setPosition(position * self.player.duration() // 100)
            
    def position_changed(self, position):
        if self.player.duration() > 0:
            self.progress_slider.setValue(position * 100 // self.player.duration())
            
        # 更新时间显示
        minutes = position // 60000
        seconds = (position % 60000) // 1000
        self.current_time.setText(f"{minutes:02d}:{seconds:02d}")
        
        # 更新歌词同步
        self.lyrics_widget.sync_lyrics(position)
        
    def duration_changed(self, duration):
        if duration > 0:
            minutes = duration // 60000
            seconds = (duration % 60000) // 1000
            self.total_time.setText(f"{minutes:02d}:{seconds:02d}")
            
    def state_changed(self, state):
        if state == QMediaPlayer.PlayingState:
            if hasattr(self, 'play_button') and self.play_button:
                self.play_button.setText("暂停")
            self.status_label.setText("播放中")
            self.tray_icon.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        elif state == QMediaPlayer.PausedState:
            if hasattr(self, 'play_button') and self.play_button:
                self.play_button.setText("播放")
            self.status_label.setText("已暂停")
            self.tray_icon.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))
        else:
            if hasattr(self, 'play_button') and self.play_button:
                self.play_button.setText("播放")
            self.status_label.setText("已停止")
            self.tray_icon.setIcon(self.style().standardIcon(QStyle.SP_MediaStop))
            
    def media_changed(self, media):
        if not media.isNull():
            url = media.canonicalUrl()
            file_path = url.toLocalFile()
            file_name = os.path.basename(file_path)
            
            # 更新歌曲信息
            self.song_title.setText(file_name)
            self.song_info_label.setText(f"正在播放: {file_name}")
            
            # 尝试加载专辑封面
            self.load_album_cover(file_path)
            
            # 尝试加载歌词
            lyrics_file = os.path.splitext(file_path)[0] + '.lrc'
            if os.path.exists(lyrics_file):
                self.lyrics_widget.parse_lyrics(lyrics_file)
                
            # 更新统计
            self.stats_widget.add_song_played(file_name)
            
    def player_error(self, error):
        QMessageBox.warning(self, "播放错误", f"播放器发生错误: {error}")
        
    def playlist_updated(self):
        count = self.playlist_manager.playlist_widget.count()
        self.status_label.setText(f"播放列表已更新，共{count}首歌曲")
        
    def update_visualization(self, analysis_data):
        self.spectrum_widget.update_spectrum(analysis_data)
        
    def change_viz_mode(self, mode):
        mode_map = {
            "柱状图": "bars",
            "圆形": "circles", 
            "波形": "waves"
        }
        self.spectrum_widget.set_visualization_mode(mode_map.get(mode, "bars"))
        
    def change_theme(self, theme):
        theme_map = {
            "默认": "default",
            "海洋": "ocean",
            "火焰": "fire"
        }
        self.spectrum_widget.set_theme(theme_map.get(theme, "default"))
        
    def change_application_theme(self, theme_name):
        self.current_theme = theme_name
        theme_style = ThemeManager.get_theme(theme_name)
        self.setStyleSheet(theme_style)
        self.settings.setValue("theme", theme_name)
        
    def load_album_cover(self, file_path):
        # 在实际应用中，这里应该从音频文件读取内嵌封面
        # 这里简化实现，从文件所在目录查找封面图片
        directory = os.path.dirname(file_path)
        cover_files = ['cover.jpg', 'folder.jpg', 'album.jpg', 'front.jpg']
        
        for cover_file in cover_files:
            cover_path = os.path.join(directory, cover_file)
            if os.path.exists(cover_path):
                self.album_cover.set_cover(cover_path)
                return
                
        # 如果没有找到封面，清空显示
        self.album_cover.set_cover(None)
        
    def show_sleep_timer(self):
        dialog = SleepTimerDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            settings = dialog.get_settings()
            self.setup_sleep_timer(settings['minutes'], settings['action'])
            
    def setup_sleep_timer(self, minutes, action):
        # 取消现有定时器
        if self.sleep_timer:
            self.sleep_timer.stop()
            
        # 创建新定时器
        self.sleep_timer = QTimer(self)
        self.sleep_timer.setSingleShot(True)
        self.sleep_timer.timeout.connect(lambda: self.execute_sleep_action(action))
        self.sleep_timer.start(minutes * 60 * 1000)  # 转换为毫秒
        
        self.status_label.setText(f"睡眠定时器已设置: {minutes}分钟后{action}")
        
    def execute_sleep_action(self, action):
        if action == "暂停播放":
            self.player.pause()
        elif action == "停止播放":
            self.player.stop()
        elif action == "关闭程序":
            self.close()
            
        self.status_label.setText("睡眠定时器已触发")
        
    def apply_settings(self):
        # 应用保存的设置
        theme = self.settings.value("theme", "dark")
        self.change_application_theme(theme)
        
    def closeEvent(self, event):
        # 保存设置
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("windowState", self.saveState())
        
        # 停止分析线程
        self.analyzer_thread.stop_analysis()
        self.analyzer_thread.wait(1000)
        
        event.accept()

# 应用程序入口
if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 设置应用程序属性
    app.setApplicationName("高级音乐播放器 - 增强版")
    app.setApplicationVersion("2.0")
    app.setOrganizationName("MusicPlayer Inc.")
    app.setWindowIcon(QIcon.fromTheme("media-playback-start"))
    
    # 创建并显示播放器
    player = EnhancedMusicPlayer()
    player.show()
    
    sys.exit(app.exec_())