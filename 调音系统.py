import sys
import numpy as np
import pyaudio
import pyqtgraph as pg
import wave
import time
from scipy import signal
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QSettings, QUrl
from PyQt6.QtGui import QFont, QColor, QPalette, QIcon, QPixmap, QAction, QDesktopServices
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QGroupBox, QLabel, QComboBox, 
                            QPushButton, QSlider, QSpinBox, QDoubleSpinBox,
                            QCheckBox, QTabWidget, QProgressBar, QMessageBox,
                            QFileDialog, QListWidget, QListWidgetItem, QSplitter,
                            QDial, QToolButton, QMenu, QStatusBar,
                            QGridLayout, QSizePolicy, QFrame, QTextEdit, QToolBar)
from PyQt6.QtMultimedia import QAudioSource, QAudioDevice, QMediaDevices
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtWebEngineWidgets import QWebEngineView
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

# 音符名称映射
NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

class MplCanvas(FigureCanvas):
    """Matplotlib画布用于高级频谱分析"""
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_subplot(111)
        super().__init__(self.fig)
        self.setParent(parent)

class FrequencyAnalyzer(QWidget):
    """频率分析可视化组件"""
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.audio_data = None
        self.frequency = 0
        self.volume = 0
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 波形图
        self.waveform_plot = pg.PlotWidget()
        self.waveform_plot.setTitle("音频波形")
        self.waveform_plot.setLabel('left', '振幅')
        self.waveform_plot.setLabel('bottom', '时间', units='s')
        self.waveform_curve = self.waveform_plot.plot(pen='g')
        
        # 频谱图
        self.spectrum_plot = pg.PlotWidget()
        self.spectrum_plot.setTitle("频率频谱")
        self.spectrum_plot.setLabel('left', '幅值')
        self.spectrum_plot.setLabel('bottom', '频率', units='Hz')
        self.spectrum_plot.setLogMode(x=False, y=True)
        self.spectrum_curve = self.spectrum_plot.plot(pen='b')
        
        # 频率和音量显示
        info_layout = QHBoxLayout()
        self.freq_label = QLabel("频率: 0 Hz")
        self.vol_label = QLabel("音量: 0 dB")
        info_layout.addWidget(self.freq_label)
        info_layout.addWidget(self.vol_label)
        
        layout.addWidget(self.waveform_plot, 1)
        layout.addWidget(self.spectrum_plot, 1)
        layout.addLayout(info_layout)
        
        self.setLayout(layout)
    
    def update_audio_data(self, data):
        """更新音频数据并重新绘制"""
        self.audio_data = data
        self.update_waveform()
        self.update_spectrum()
    
    def update_waveform(self):
        """更新波形图"""
        if self.audio_data is not None:
            x = np.arange(len(self.audio_data)) / 44100  # 假设采样率为44100Hz
            self.waveform_curve.setData(x, self.audio_data)
    
    def update_spectrum(self):
        """更新频谱图"""
        if self.audio_data is not None:
            # 计算FFT
            fft_data = np.fft.fft(self.audio_data)
            freq = np.fft.fftfreq(len(fft_data), 1.0/44100)
            
            # 只取正频率部分
            positive_freq = freq[:len(freq)//2]
            positive_fft = np.abs(fft_data[:len(fft_data)//2])
            
            self.spectrum_curve.setData(positive_freq, positive_fft)
    
    def update_frequency_info(self, freq, volume):
        """更新频率和音量信息"""
        self.frequency = freq
        self.volume = volume
        self.freq_label.setText(f"频率: {freq:.2f} Hz")
        self.vol_label.setText(f"音量: {volume:.2f} dB")
        
class EnhancedAudioProcessor(QThread):
    """增强的音频处理线程，支持多种分析方法和和弦检测"""
    data_ready = pyqtSignal(np.ndarray)
    frequency_detected = pyqtSignal(float, float, list)  # 基频，音量，谐波信息
    chord_detected = pyqtSignal(str, list)  # 和弦名称，音符列表
    note_played = pyqtSignal(str, int, float)  # 音符名称，八度，持续时间
    
    def __init__(self, sample_rate=44100, chunk_size=4096, analysis_method="FFT"):
        super().__init__()
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.running = False
        self.audio = pyaudio.PyAudio()
        self.stream = None
        self.analysis_method = analysis_method
        self.recording = False
        self.recorded_data = []
        self.reference_pitch = 440.0  # A4标准音高
        self.current_note = None
        self.note_start_time = 0
        self.note_duration = 0
        
    def run(self):
        self.running = True
        try:
            self.stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size
            )
            
            while self.running:
                data = self.stream.read(self.chunk_size, exception_on_overflow=False)
                audio_data = np.frombuffer(data, dtype=np.int16)
                self.data_ready.emit(audio_data)
                
                if self.recording:
                    self.recorded_data.append(audio_data.copy())
                
                # 频率检测
                if self.analysis_method == "FFT":
                    freq, volume, harmonics = self.detect_frequency_fft(audio_data)
                elif self.analysis_method == "Autocorrelation":
                    freq, volume, harmonics = self.detect_frequency_autocorrelation(audio_data)
                else:  # Cepstrum
                    freq, volume, harmonics = self.detect_frequency_cepstrum(audio_data)
                
                if freq > 0:
                    self.frequency_detected.emit(freq, volume, harmonics)
                    
                    # 音符检测和持续时间计算
                    semitones_from_a4 = 12 * np.log2(freq / self.reference_pitch)
                    note_index = int(round(semitones_from_a4)) % 12
                    note_name = NOTE_NAMES[note_index]
                    
                    if self.current_note != note_name:
                        if self.current_note is not None:
                            self.note_played.emit(self.current_note, 4 + int((semitones_from_a4 + 9) / 12), self.note_duration)
                        self.current_note = note_name
                        self.note_start_time = time.time()
                    else:
                        self.note_duration = time.time() - self.note_start_time
                    
                else:
                    if self.current_note is not None:
                        self.note_played.emit(self.current_note, 4 + int((semitones_from_a4 + 9) / 12), self.note_duration)
                    self.current_note = None
                    self.note_duration = 0
                    
                # 和弦检测 (如果有足够的数据)
                if len(self.recorded_data) > 10:  # 使用一些历史数据进行和弦分析
                    self.detect_chord()
                    
        except Exception as e:
            print(f"Audio processing error: {e}")
        finally:
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
            self.audio.terminate()
    
    def set_analysis_method(self, method):
        """设置分析方法"""
        self.analysis_method = method
    
    def set_reference_pitch(self, pitch):
        """设置参考音高"""
        self.reference_pitch = pitch
    
    def start_recording(self):
        """开始录音"""
        self.recording = True
        self.recorded_data = []
    
    def stop_recording(self):
        """停止录音"""
        self.recording = False
        return np.concatenate(self.recorded_data) if self.recorded_data else np.array([])
    
    def stop(self):
        self.running = False
        self.wait()
    
    def detect_frequency_fft(self, data):
        """使用FFT检测频率和谐波"""
        if np.max(np.abs(data)) < 100:  # 静音阈值
            return 0, 0, []
            
        # 应用窗函数
        window = np.hanning(len(data))
        windowed_data = data * window
        
        # FFT变换
        fft_data = np.fft.fft(windowed_data)
        frequencies = np.fft.fftfreq(len(fft_data), 1.0 / self.sample_rate)
        
        # 只取正频率
        positive_freq_idx = np.where(frequencies > 0)
        positive_freq = frequencies[positive_freq_idx]
        positive_fft = np.abs(fft_data[positive_freq_idx])
        
        # 找到最大幅值对应的频率 (基频)
        max_idx = np.argmax(positive_fft)
        fundamental_freq = positive_freq[max_idx]
        volume = 20 * np.log10(np.max(positive_fft) + 1e-10)  # 转换为分贝
        
        # 检测谐波
        harmonics = self.detect_harmonics(positive_freq, positive_fft, fundamental_freq)
        
        return fundamental_freq, volume, harmonics
    
    def detect_frequency_autocorrelation(self, data):
        """使用自相关方法检测频率"""
        if np.max(np.abs(data)) < 100:  # 静音阈值
            return 0, 0, []
            
        # 归一化数据
        normalized_data = data / np.max(np.abs(data))
        
        # 计算自相关
        autocorr = np.correlate(normalized_data, normalized_data, mode='full')
        autocorr = autocorr[len(autocorr)//2:]  # 只取后半部分
        
        # 找到第一个峰值之后的第一个最大峰值
        peak_indices, _ = signal.find_peaks(autocorr)
        if len(peak_indices) > 1:
            fundamental_period = peak_indices[1] - peak_indices[0]
            fundamental_freq = self.sample_rate / fundamental_period
        else:
            fundamental_freq = 0
            
        volume = 20 * np.log10(np.max(np.abs(data)) + 1e-10)
        
        return fundamental_freq, volume, []
    
    def detect_frequency_cepstrum(self, data):
        """使用倒谱分析检测频率"""
        if np.max(np.abs(data)) < 100:  # 静音阈值
            return 0, 0, []
            
        # 应用窗函数
        window = np.hanning(len(data))
        windowed_data = data * window
        
        # 计算倒谱
        fft_data = np.fft.fft(windowed_data)
        log_fft = np.log(np.abs(fft_data) + 1e-10)
        cepstrum = np.abs(np.fft.ifft(log_fft))
        
        # 找到倒谱中的峰值
        quefrencies = np.arange(len(cepstrum)) / self.sample_rate
        valid_quefrencies = quefrencies[10:len(quefrencies)//2]  # 排除直流分量和高频
        valid_cepstrum = cepstrum[10:len(cepstrum)//2]
        
        peak_idx = np.argmax(valid_cepstrum)
        fundamental_period = valid_quefrencies[peak_idx]
        fundamental_freq = 1.0 / fundamental_period if fundamental_period > 0 else 0
        
        volume = 20 * np.log10(np.max(np.abs(data)) + 1e-10)
        
        return fundamental_freq, volume, []
    
    def detect_harmonics(self, frequencies, magnitudes, fundamental_freq):
        """检测谐波成分"""
        harmonics = []
        if fundamental_freq <= 0:
            return harmonics
            
        # 检查前10个谐波
        for i in range(1, 11):
            harmonic_freq = fundamental_freq * i
            # 在谐波频率附近寻找峰值
            idx = np.where((frequencies > harmonic_freq * 0.95) & 
                          (frequencies < harmonic_freq * 1.05))
            if len(idx[0]) > 0:
                harmonic_mag = np.max(magnitudes[idx])
                harmonic_db = 20 * np.log10(harmonic_mag + 1e-10)
                harmonics.append((harmonic_freq, harmonic_db))
                
        return harmonics
    
    def detect_chord(self):
        """分析和弦"""
        if not self.recorded_data or len(self.recorded_data) < 5:
            return
            
        # 使用最近的数据进行和弦分析
        recent_data = np.concatenate(self.recorded_data[-5:])
        
        # 计算频谱
        window = np.hanning(len(recent_data))
        windowed_data = recent_data * window
        fft_data = np.fft.fft(windowed_data)
        frequencies = np.fft.fftfreq(len(fft_data), 1.0 / self.sample_rate)
        
        # 只取正频率
        positive_freq_idx = np.where(frequencies > 0)
        positive_freq = frequencies[positive_freq_idx]
        positive_fft = np.abs(fft_data[positive_freq_idx])
        
        # 找到显著的频率峰值
        peaks, _ = signal.find_peaks(positive_fft, height=np.max(positive_fft)*0.1)
        peak_freqs = positive_freq[peaks]
        peak_mags = positive_fft[peaks]
        
        # 过滤掉太弱的峰值
        strong_peaks = peak_freqs[peak_mags > np.max(peak_mags)*0.3]
        
        # 将频率转换为音符
        notes = []
        for freq in strong_peaks:
            if freq > 0:
                note_idx = int(round(12 * np.log2(freq / self.reference_pitch))) % 12
                notes.append(NOTE_NAMES[note_idx])
        
        # 简单的和弦识别逻辑
        if notes:
            # 去重并排序
            unique_notes = sorted(set(notes), key=notes.index)
            chord_name = "".join(unique_notes)
            
            # 常见和弦映射
            chord_map = {
                "CEG": "C",
                "DFA": "Dm",
                "EGB": "Em",
                "FAC": "F",
                "GBD": "G",
                "ACE": "Am",
                "ACEG": "C",
                "DFAC": "Dm",
                "EGBD": "Em",
                "FACE": "F",
                "GBDF": "G7",
                "ACEGB": "Cmaj7"
            }
            
            detected_chord = chord_map.get(chord_name, f"Unknown ({chord_name})")
            self.chord_detected.emit(detected_chord, unique_notes)

class SpectrumAnalyzer3D(pg.GraphicsLayoutWidget):
    """3D频谱分析器（瀑布图）"""
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.data = np.zeros((100, 512))
        self.ptr = 0
        
    def init_ui(self):
        # 创建3D瀑布图
        self.spectrum_plot = self.addPlot(title="频谱瀑布图")
        self.spectrum_plot.setLabel('left', '频率', units='Hz')
        self.spectrum_plot.setLabel('bottom', '时间', units='s')
        self.spectrum_img = pg.ImageItem()
        self.spectrum_plot.addItem(self.spectrum_img)
        
        # 设置颜色映射
        pos = np.array([0.0, 0.25, 0.5, 0.75, 1.0])
        color = np.array([
            [0, 0, 0, 255],
            [0, 0, 255, 255],
            [0, 255, 0, 255],
            [255, 255, 0, 255],
            [255, 0, 0, 255]
        ], dtype=np.ubyte)
        cmap = pg.ColorMap(pos, color)
        self.spectrum_img.setLookupTable(cmap.getLookupTable())
        
        self.spectrum_img.setScale(44100/512/100)  # 只设置x方向的缩放
        self.spectrum_img.setZValue(-100)
        
    def update_spectrum(self, fft_data):
        """更新频谱图"""
        # 滚动显示数据
        self.data = np.roll(self.data, -1, axis=0)
        self.data[-1] = fft_data[:512]  # 只取前512个点
        
        # 更新图像，添加levels参数
        # 计算数据的范围，避免全零数据
        if np.max(self.data) > 0:
            levels = (0, np.max(self.data))
        else:
            levels = (0, 1)  # 默认范围，避免全零数据
            
        self.spectrum_img.setImage(self.data, autoLevels=False, levels=levels)

class EnhancedTunerWidget(QWidget):
    """增强的调音器界面"""
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.target_frequency = 440.0  # A4标准音高
        self.reference_pitch = 440.0
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 频率显示和调音指示器
        display_layout = QHBoxLayout()
        
        # 频率显示
        freq_display_group = QGroupBox("频率信息")
        freq_display_layout = QVBoxLayout()
        
        self.freq_display = QLabel("440.0 Hz")
        self.freq_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.freq_display.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        freq_display_layout.addWidget(self.freq_display)
        
        self.note_display = QLabel("A4")
        self.note_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.note_display.setFont(QFont("Arial", 36, QFont.Weight.Bold))
        freq_display_layout.addWidget(self.note_display)
        
        self.cents_display = QLabel("±0 cents")
        self.cents_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.cents_display.setFont(QFont("Arial", 18))
        freq_display_layout.addWidget(self.cents_display)
        
        freq_display_group.setLayout(freq_display_layout)
        display_layout.addWidget(freq_display_group)
        
        # 调音指示器
        tuner_group = QGroupBox("调音指示")
        tuner_layout = QVBoxLayout()
        
        self.tuner_needle = QLabel()
        self.tuner_needle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # 使用内置图标代替图片文件
        self.tuner_needle.setText("↑")
        self.tuner_needle.setFont(QFont("Arial", 48))
        
        self.tuner_dial = QLabel()
        self.tuner_dial.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.tuner_dial.setText("-50    0    +50")
        self.tuner_dial.setFont(QFont("Arial", 16))
        
        tuner_layout.addWidget(self.tuner_dial)
        tuner_layout.addWidget(self.tuner_needle)
        
        self.deviation_bar = QProgressBar()
        self.deviation_bar.setRange(-50, 50)
        self.deviation_bar.setValue(0)
        self.deviation_bar.setTextVisible(False)
        tuner_layout.addWidget(self.deviation_bar)
        
        tuner_group.setLayout(tuner_layout)
        display_layout.addWidget(tuner_group)
        
        layout.addLayout(display_layout)
        
        # 目标频率和参考音高设置
        control_layout = QGridLayout()
        
        control_layout.addWidget(QLabel("目标音符:"), 0, 0)
        self.note_selector = QComboBox()
        self.note_selector.addItems(NOTE_NAMES)
        self.note_selector.setCurrentText("A")
        control_layout.addWidget(self.note_selector, 0, 1)
        
        control_layout.addWidget(QLabel("八度:"), 0, 2)
        self.octave_selector = QSpinBox()
        self.octave_selector.setRange(0, 8)
        self.octave_selector.setValue(4)
        control_layout.addWidget(self.octave_selector, 0, 3)
        
        control_layout.addWidget(QLabel("参考音高:"), 1, 0)
        self.reference_pitch_spin = QDoubleSpinBox()
        self.reference_pitch_spin.setRange(410, 480)
        self.reference_pitch_spin.setValue(440.0)
        self.reference_pitch_spin.setSingleStep(0.1)
        self.reference_pitch_spin.setSuffix(" Hz")
        control_layout.addWidget(self.reference_pitch_spin, 1, 1)
        
        control_layout.addWidget(QLabel("分析算法:"), 1, 2)
        self.algorithm_selector = QComboBox()
        self.algorithm_selector.addItems(["FFT", "Autocorrelation", "Cepstrum"])
        control_layout.addWidget(self.algorithm_selector, 1, 3)
        
        layout.addLayout(control_layout)
        
        # 谐波分析
        harmonics_group = QGroupBox("谐波分析")
        harmonics_layout = QVBoxLayout()
        
        self.harmonics_bars = []
        harmonics_bars_layout = QHBoxLayout()
        for i in range(5):  # 显示前5个谐波
            bar = QProgressBar()
            bar.setRange(0, 100)
            bar.setValue(0)
            bar.setFormat(f"H{i+1}")
            bar.setTextVisible(True)
            harmonics_bars_layout.addWidget(bar)
            self.harmonics_bars.append(bar)
            
        harmonics_layout.addLayout(harmonics_bars_layout)
        harmonics_group.setLayout(harmonics_layout)
        layout.addWidget(harmonics_group)
        
        self.setLayout(layout)
        
        # 连接信号
        self.note_selector.currentTextChanged.connect(self.update_target_frequency)
        self.octave_selector.valueChanged.connect(self.update_target_frequency)
        self.reference_pitch_spin.valueChanged.connect(self.update_reference_pitch)
    
    def update_target_frequency(self):
        """更新目标频率"""
        note = self.note_selector.currentText()
        octave = self.octave_selector.value()
        
        # 计算目标频率
        note_index = NOTE_NAMES.index(note)
        semitones_from_a4 = (octave - 4) * 12 + (note_index - 9)  # A是第9个音符(从0开始)
        
        self.target_frequency = self.reference_pitch * (2.0 ** (semitones_from_a4 / 12.0))
    
    def update_reference_pitch(self, pitch):
        """更新参考音高"""
        self.reference_pitch = pitch
        self.update_target_frequency()
    
    def update_tuner(self, frequency, volume, harmonics):
        """更新调音器显示"""
        self.freq_display.setText(f"{frequency:.1f} Hz")
        
        if volume < -50:  # 音量太低
            self.note_display.setText("--")
            self.cents_display.setText("±0 cents")
            self.deviation_bar.setValue(0)
            return
        
        # 计算音高偏差
        if frequency > 0:
            # 计算最接近的音符
            semitones_from_a4 = 12 * np.log2(frequency / self.reference_pitch)
            note_index = int(round(semitones_from_a4)) % 12
            octave = 4 + int((semitones_from_a4 + 9) / 12)  # A是第9个音符
            
            # 计算音分偏差
            cents_deviation = 100 * (semitones_from_a4 - round(semitones_from_a4))
            
            # 更新UI
            self.note_display.setText(f"{NOTE_NAMES[note_index]}{octave}")
            self.cents_display.setText(f"{cents_deviation:+.0f} cents")
            self.deviation_bar.setValue(int(cents_deviation))
            
            # 更新谐波显示
            self.update_harmonics_display(harmonics)
        else:
            self.note_display.setText("--")
            self.cents_display.setText("±0 cents")
            self.deviation_bar.setValue(0)
    
    def update_harmonics_display(self, harmonics):
        """更新谐波显示"""
        if not harmonics:
            for bar in self.harmonics_bars:
                bar.setValue(0)
            return
            
        # 找到基频
        base_freq = harmonics[0][0] if harmonics else 0
        
        for i, bar in enumerate(self.harmonics_bars):
            if i < len(harmonics):
                # 计算谐波强度 (0-100)
                harmonic_db = harmonics[i][1]
                strength = max(0, min(100, harmonic_db + 60))  # 假设-60dB到+40dB范围
                bar.setValue(int(strength))
            else:
                bar.setValue(0)

class ChordRecognitionWidget(QWidget):
    """和弦识别界面"""
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 和弦显示
        self.chord_display = QLabel("无和弦检测")
        self.chord_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.chord_display.setFont(QFont("Arial", 36, QFont.Weight.Bold))
        layout.addWidget(self.chord_display)
        
        # 音符列表
        self.notes_list = QListWidget()
        layout.addWidget(self.notes_list)
        
        # 和弦历史
        history_group = QGroupBox("和弦历史")
        history_layout = QVBoxLayout()
        
        self.chord_history = QListWidget()
        history_layout.addWidget(self.chord_history)
        
        clear_btn = QPushButton("清除历史")
        clear_btn.clicked.connect(self.chord_history.clear)
        history_layout.addWidget(clear_btn)
        
        history_group.setLayout(history_layout)
        layout.addWidget(history_group)
        
        self.setLayout(layout)
    
    def update_chord(self, chord_name, notes):
        """更新和弦显示"""
        self.chord_display.setText(chord_name)
        
        self.notes_list.clear()
        for note in notes:
            self.notes_list.addItem(note)
        
        # 添加到历史
        timestamp = time.strftime("%H:%M:%S")
        self.chord_history.addItem(f"[{timestamp}] {chord_name}: {', '.join(notes)}")

class RecordingWidget(QWidget):
    """录音和回放界面"""
    def __init__(self, audio_processor):
        super().__init__()
        self.audio_processor = audio_processor
        self.recorded_data = None
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 录音控制
        record_group = QGroupBox("录音控制")
        record_layout = QVBoxLayout()
        
        self.record_btn = QPushButton("开始录音")
        self.record_btn.clicked.connect(self.toggle_recording)
        record_layout.addWidget(self.record_btn)
        
        self.record_status = QLabel("未录音")
        record_layout.addWidget(self.record_status)
        
        record_group.setLayout(record_layout)
        layout.addWidget(record_group)
        
        # 回放控制
        playback_group = QGroupBox("回放控制")
        playback_layout = QVBoxLayout()
        
        self.playback_btn = QPushButton("播放录音")
        self.playback_btn.clicked.connect(self.play_recording)
        self.playback_btn.setEnabled(False)
        playback_layout.addWidget(self.playback_btn)
        
        self.save_btn = QPushButton("保存录音")
        self.save_btn.clicked.connect(self.save_recording)
        self.save_btn.setEnabled(False)
        playback_layout.addWidget(self.save_btn)
        
        playback_group.setLayout(playback_layout)
        layout.addWidget(playback_group)
        
        # 录音波形显示
        waveform_group = QGroupBox("录音波形")
        waveform_layout = QVBoxLayout()
        
        self.waveform_plot = pg.PlotWidget()
        self.waveform_plot.setTitle("录音波形")
        self.waveform_plot.setLabel('left', '振幅')
        self.waveform_plot.setLabel('bottom', '时间', units='s')
        self.waveform_curve = self.waveform_plot.plot(pen='b')
        
        waveform_layout.addWidget(self.waveform_plot)
        waveform_group.setLayout(waveform_layout)
        layout.addWidget(waveform_group)
        
        self.setLayout(layout)
    
    def toggle_recording(self):
        """切换录音状态"""
        if self.audio_processor.recording:
            self.stop_recording()
        else:
            self.start_recording()
    
    def start_recording(self):
        """开始录音"""
        self.audio_processor.start_recording()
        self.record_btn.setText("停止录音")
        self.record_status.setText("录音中...")
        self.playback_btn.setEnabled(False)
        self.save_btn.setEnabled(False)
    
    def stop_recording(self):
        """停止录音"""
        self.recorded_data = self.audio_processor.stop_recording()
        self.record_btn.setText("开始录音")
        self.record_status.setText("录音完成")
        self.playback_btn.setEnabled(True)
        self.save_btn.setEnabled(True)
        
        # 显示录音波形
        if self.recorded_data is not None and len(self.recorded_data) > 0:
            x = np.arange(len(self.recorded_data)) / 44100  # 假设采样率为44100Hz
            self.waveform_curve.setData(x, self.recorded_data)
    
    def play_recording(self):
        """播放录音"""
        if self.recorded_data is not None and len(self.recorded_data) > 0:
            # 使用PyAudio播放录音
            p = pyaudio.PyAudio()
            stream = p.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=44100,
                output=True
            )
            
            # 转换为字节数据
            audio_data = (self.recorded_data * 32767).astype(np.int16).tobytes()
            stream.write(audio_data)
            
            stream.stop_stream()
            stream.close()
            p.terminate()
    
    def save_recording(self):
        """保存录音到文件"""
        if self.recorded_data is not None and len(self.recorded_data) > 0:
            file_path, _ = QFileDialog.getSaveFileName(
                self, "保存录音", "", "WAV文件 (*.wav)"
            )
            
            if file_path:
                if not file_path.endswith('.wav'):
                    file_path += '.wav'
                
                # 保存为WAV文件
                with wave.open(file_path, 'wb') as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)  # 16-bit
                    wf.setframerate(44100)
                    wf.writeframes((self.recorded_data * 32767).astype(np.int16).tobytes())

class MusicTheoryWidget(QWidget):
    """音乐理论学习和参考界面"""
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 创建标签页
        tabs = QTabWidget()
        
        # 音阶参考标签页
        scale_tab = QWidget()
        scale_layout = QVBoxLayout(scale_tab)
        
        scale_info = QTextEdit()
        scale_info.setReadOnly(True)
        scale_info.setHtml("""
        <h2>常见音阶参考</h2>
        <h3>大调音阶</h3>
        <p>公式: 全全半全全全半</p>
        <p>C大调: C D E F G A B C</p>
        <p>G大调: G A B C D E F# G</p>
        
        <h3>小调音阶</h3>
        <p>自然小调公式: 全半全全半全全</p>
        <p>A小调: A B C D E F G A</p>
        
        <h3>五声音阶</h3>
        <p>大调五声音阶: 1 2 3 5 6</p>
        <p>C大调五声: C D E G A</p>
        
        <h3>蓝调音阶</h3>
        <p>公式: 1 b3 4 b5 5 b7</p>
        <p>C蓝调: C Eb F Gb G Bb</p>
        """)
        scale_layout.addWidget(scale_info)
        
        tabs.addTab(scale_tab, "音阶参考")
        
        # 和弦参考标签页
        chord_tab = QWidget()
        chord_layout = QVBoxLayout(chord_tab)
        
        chord_info = QTextEdit()
        chord_info.setReadOnly(True)
        chord_info.setHtml("""
        <h2>常见和弦参考</h2>
        <h3>三和弦</h3>
        <p>大三和弦: 根音 + 大三度 + 纯五度 (如: C E G)</p>
        <p>小三和弦: 根音 + 小三度 + 纯五度 (如: C Eb G)</p>
        <p>增三和弦: 根音 + 大三度 + 增五度 (如: C E G#)</p>
        <p>减三和弦: 根音 + 小三度 + 减五度 (如: C Eb Gb)</p>
        
        <h3>七和弦</h3>
        <p>大七和弦: 大三和弦 + 大七度 (如: C E G B)</p>
        <p>属七和弦: 大三和弦 + 小七度 (如: C E G Bb)</p>
        <p>小七和弦: 小三和弦 + 小七度 (如: C Eb G Bb)</p>
        <p>半减七和弦: 减三和弦 + 小七度 (如: C Eb Gb Bb)</p>
        """)
        chord_layout.addWidget(chord_info)
        
        tabs.addTab(chord_tab, "和弦参考")
        
        # 节奏模式标签页
        rhythm_tab = QWidget()
        rhythm_layout = QVBoxLayout(rhythm_tab)
        
        rhythm_info = QTextEdit()
        rhythm_info.setReadOnly(True)
        rhythm_info.setHtml("""
        <h2>常见节奏模式</h2>
        <h3>4/4拍常见节奏</h3>
        <p>摇滚节奏: 强拍在2和4拍</p>
        <p>华尔兹: 强-弱-弱 (3/4拍)</p>
        <p> shuffle节奏: 三连音的感觉，第一个音符长，第二个短</p>
        
        <h3>鼓点模式</h3>
        <p>基本摇滚: 底鼓在1和3拍，军鼓在2和4拍，踩镲每八分音符</p>
        <p>放克节奏: 强调16分音符的切分，底鼓复杂模式</p>
        """)
        rhythm_layout.addWidget(rhythm_info)
        
        tabs.addTab(rhythm_tab, "节奏模式")
        
        layout.addWidget(tabs)
        self.setLayout(layout)

class MetronomeWidget(QWidget):
    """节拍器功能"""
    def __init__(self):
        super().__init__()
        self.timer = QTimer()
        self.timer.timeout.connect(self.play_click)
        self.is_playing = False
        self.bpm = 120
        self.beat_count = 0
        self.time_signature = 4  # 默认4/4拍
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # BPM控制
        bpm_layout = QHBoxLayout()
        bpm_layout.addWidget(QLabel("BPM:"))
        
        self.bpm_spin = QSpinBox()
        self.bpm_spin.setRange(30, 240)
        self.bpm_spin.setValue(120)
        self.bpm_spin.valueChanged.connect(self.set_bpm)
        bpm_layout.addWidget(self.bpm_spin)
        
        self.bpm_slider = QSlider(Qt.Orientation.Horizontal)
        self.bpm_slider.setRange(30, 240)
        self.bpm_slider.setValue(120)
        self.bpm_slider.valueChanged.connect(self.bpm_spin.setValue)
        bpm_layout.addWidget(self.bpm_slider)
        
        layout.addLayout(bpm_layout)
        
        # 拍号设置
        time_sig_layout = QHBoxLayout()
        time_sig_layout.addWidget(QLabel("拍号:"))
        
        self.time_sig_combo = QComboBox()
        self.time_sig_combo.addItems(["2/4", "3/4", "4/4", "5/4", "6/8", "7/8"])
        self.time_sig_combo.currentIndexChanged.connect(self.set_time_signature)
        time_sig_layout.addWidget(self.time_sig_combo)
        
        layout.addLayout(time_sig_layout)
        
        # 节拍器控制
        control_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("开始")
        self.start_btn.clicked.connect(self.toggle_metronome)
        control_layout.addWidget(self.start_btn)
        
        self.reset_btn = QPushButton("重置")
        self.reset_btn.clicked.connect(self.reset)
        control_layout.addWidget(self.reset_btn)
        
        layout.addLayout(control_layout)
        
        # 节拍显示
        self.beat_display = QLabel("0")
        self.beat_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.beat_display.setFont(QFont("Arial", 48, QFont.Weight.Bold))
        layout.addWidget(self.beat_display)
        
        self.setLayout(layout)
    
    def set_bpm(self, bpm):
        """设置BPM"""
        self.bpm = bpm
        self.bpm_slider.setValue(bpm)
        if self.is_playing:
            # 将浮点数转换为整数
            self.timer.setInterval(int(60000 / self.bpm))  # 每分钟的毫秒数除以BPM
    
    def set_time_signature(self, index):
        """设置拍号"""
        time_sigs = [2, 3, 4, 5, 6, 7]
        self.time_signature = time_sigs[index]
    
    def toggle_metronome(self):
        """切换节拍器状态"""
        if self.is_playing:
            self.stop_metronome()
        else:
            self.start_metronome()
    
    def start_metronome(self):
        """开始节拍器"""
        # 将浮点数转换为整数
        self.timer.start(int(60000 / self.bpm))
        self.is_playing = True
        self.start_btn.setText("停止")
    
    def stop_metronome(self):
        """停止节拍器"""
        self.timer.stop()
        self.is_playing = False
        self.start_btn.setText("开始")
    
    def reset(self):
        """重置节拍计数"""
        self.beat_count = 0
        self.beat_display.setText("0")
    
    def play_click(self):
        """播放节拍声"""
        self.beat_count = (self.beat_count % self.time_signature) + 1
        self.beat_display.setText(str(self.beat_count))
        
        # 这里可以添加音频播放代码
        # 例如：播放不同的声音表示强拍和弱拍
        if self.beat_count == 1:
            print("强拍")  # 替换为播放强拍声音
        else:
            print("弱拍")  # 替换为播放弱拍声音

class AdvancedTunerSystem(QMainWindow):
    """高级调音系统主窗口"""
    def __init__(self):
        super().__init__()
        self.audio_processor = None
        self.settings = QSettings("MyCompany", "AdvancedTuner")
        self.init_ui()
        self.load_settings()
        
    def init_ui(self):
        self.setWindowTitle("高级调音系统")
        self.setGeometry(100, 100, 1400, 1000)
        
        # 创建中央部件和主布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # 创建分割器，使界面可调整
        splitter = QSplitter(Qt.Orientation.Vertical)
        main_layout.addWidget(splitter)
        
        # 标签页
        tabs = QTabWidget()
        splitter.addWidget(tabs)
        
        # 调音器标签页
        tuner_tab = QWidget()
        tuner_layout = QVBoxLayout(tuner_tab)
        
        self.tuner_widget = EnhancedTunerWidget()
        tuner_layout.addWidget(self.tuner_widget)
        
        tabs.addTab(tuner_tab, "调音器")
        
        # 频谱分析标签页
        spectrum_tab = QWidget()
        spectrum_layout = QVBoxLayout(spectrum_tab)
        
        self.freq_analyzer = FrequencyAnalyzer()
        spectrum_layout.addWidget(self.freq_analyzer)
        
        self.spectrum_3d = SpectrumAnalyzer3D()
        spectrum_layout.addWidget(self.spectrum_3d)
        
        tabs.addTab(spectrum_tab, "频谱分析")
        
        # 和弦识别标签页
        chord_tab = QWidget()
        chord_layout = QVBoxLayout(chord_tab)
        
        self.chord_widget = ChordRecognitionWidget()
        chord_layout.addWidget(self.chord_widget)
        
        tabs.addTab(chord_tab, "和弦识别")
        
        # 录音标签页
        self.recording_tab = QWidget()
        recording_layout = QVBoxLayout(self.recording_tab)
        
        # 将在初始化audio_processor后创建
        tabs.addTab(self.recording_tab, "录音回放")
        
        # 音乐理论学习标签页
        theory_tab = QWidget()
        theory_layout = QVBoxLayout(theory_tab)
        
        self.theory_widget = MusicTheoryWidget()
        theory_layout.addWidget(self.theory_widget)
        
        tabs.addTab(theory_tab, "音乐理论")
        
        # 节拍器标签页
        metronome_tab = QWidget()
        metronome_layout = QVBoxLayout(metronome_tab)
        
        self.metronome_widget = MetronomeWidget()
        metronome_layout.addWidget(self.metronome_widget)
        
        tabs.addTab(metronome_tab, "节拍器")
        
        # 音频控制栏
        control_bar = QFrame()
        control_bar.setFrameShape(QFrame.Shape.StyledPanel)
        control_bar_layout = QHBoxLayout(control_bar)
        
        self.input_device_combo = QComboBox()
        control_bar_layout.addWidget(QLabel("输入设备:"))
        control_bar_layout.addWidget(self.input_device_combo)
        
        self.sample_rate_combo = QComboBox()
        self.sample_rate_combo.addItems(["44100", "48000", "96000"])
        self.sample_rate_combo.setCurrentText("44100")
        control_bar_layout.addWidget(QLabel("采样率:"))
        control_bar_layout.addWidget(self.sample_rate_combo)
        
        self.sensitivity_slider = QSlider(Qt.Orientation.Horizontal)
        self.sensitivity_slider.setRange(1, 100)
        self.sensitivity_slider.setValue(50)
        control_bar_layout.addWidget(QLabel("灵敏度:"))
        control_bar_layout.addWidget(self.sensitivity_slider)
        
        self.start_button = QPushButton("开始监听")
        self.start_button.clicked.connect(self.toggle_audio)
        control_bar_layout.addWidget(self.start_button)
        
        main_layout.addWidget(control_bar)
        
        # 填充音频设备列表
        self.populate_audio_devices()
        
        # 创建状态栏
        self.statusBar().showMessage("就绪")
        
        # 创建菜单栏
        self.create_menus()
        
        # 创建工具栏
        self.create_toolbar()
    
    def create_toolbar(self):
        """创建工具栏"""
        toolbar = QToolBar("主工具栏")
        self.addToolBar(toolbar)
        
        # 开始/停止监听按钮
        start_action = QAction("开始监听", self)
        start_action.triggered.connect(self.toggle_audio)
        toolbar.addAction(start_action)
        
        # 分隔符
        toolbar.addSeparator()
        
        # 主题切换按钮
        theme_action = QAction("切换主题", self)
        theme_action.triggered.connect(self.toggle_theme)
        toolbar.addAction(theme_action)
        
        # 帮助按钮
        help_action = QAction("帮助", self)
        help_action.triggered.connect(self.show_help)
        toolbar.addAction(help_action)
    
    def create_menus(self):
        """创建菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu('文件')
        
        export_action = QAction('导出数据', self)
        export_action.setShortcut('Ctrl+E')
        export_action.triggered.connect(self.export_data)
        file_menu.addAction(export_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction('退出', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 设置菜单
        settings_menu = menubar.addMenu('设置')
        
        theme_action = QAction('切换主题', self)
        theme_action.triggered.connect(self.toggle_theme)
        settings_menu.addAction(theme_action)
        
        # 工具菜单
        tools_menu = menubar.addMenu('工具')
        
        metronome_action = QAction('节拍器', self)
        metronome_action.triggered.connect(self.open_metronome)
        tools_menu.addAction(metronome_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu('帮助')
        
        help_action = QAction('使用指南', self)
        help_action.triggered.connect(self.show_help)
        help_menu.addAction(help_action)
        
        about_action = QAction('关于', self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def populate_audio_devices(self):
        """填充音频设备列表"""
        self.input_device_combo.clear()
        
        try:
            audio = pyaudio.PyAudio()
            for i in range(audio.get_device_count()):
                device_info = audio.get_device_info_by_index(i)
                if device_info['maxInputChannels'] > 0:
                    self.input_device_combo.addItem(
                        f"{device_info['name']} ({int(device_info['defaultSampleRate'])}Hz)", 
                        i
                    )
            audio.terminate()
        except Exception as e:
            QMessageBox.warning(self, "错误", f"无法获取音频设备: {e}")
    
    def toggle_audio(self):
        """切换音频监听状态"""
        if self.audio_processor and self.audio_processor.isRunning():
            self.stop_audio()
        else:
            self.start_audio()
    
    def start_audio(self):
        """开始音频监听"""
        try:
            device_index = self.input_device_combo.currentData()
            sample_rate = int(self.sample_rate_combo.currentText())
            analysis_method = self.tuner_widget.algorithm_selector.currentText()
            
            self.audio_processor = EnhancedAudioProcessor(
                sample_rate=sample_rate, 
                analysis_method=analysis_method
            )
            self.audio_processor.data_ready.connect(self.freq_analyzer.update_audio_data)
            self.audio_processor.data_ready.connect(self.update_spectrum_3d)
            self.audio_processor.frequency_detected.connect(self.freq_analyzer.update_frequency_info)
            self.audio_processor.frequency_detected.connect(self.tuner_widget.update_tuner)
            self.audio_processor.chord_detected.connect(self.chord_widget.update_chord)
            self.audio_processor.note_played.connect(self.log_note)
            
            # 设置参考音高
            reference_pitch = self.tuner_widget.reference_pitch_spin.value()
            self.audio_processor.set_reference_pitch(reference_pitch)
            
            # 创建录音界面
            self.init_recording_tab()
            
            self.audio_processor.start()
            
            self.start_button.setText("停止监听")
            self.statusBar().showMessage("正在监听音频...")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法启动音频监听: {e}")
    
    def init_recording_tab(self):
        """初始化录音标签页"""
        # 清除现有布局
        if self.recording_tab.layout():
            QWidget().setLayout(self.recording_tab.layout())
        
        # 创建新的录音界面
        recording_layout = QVBoxLayout(self.recording_tab)
        self.recording_widget = RecordingWidget(self.audio_processor)
        recording_layout.addWidget(self.recording_widget)
        self.recording_tab.setLayout(recording_layout)
    
    def update_spectrum_3d(self, data):
        """更新3D频谱图"""
        # 计算FFT
        window = np.hanning(len(data))
        windowed_data = data * window
        fft_data = np.fft.fft(windowed_data)
        magnitude = np.abs(fft_data[:len(fft_data)//2])
        
        # 更新3D频谱
        self.spectrum_3d.update_spectrum(magnitude)
    
    def stop_audio(self):
        """停止音频监听"""
        if self.audio_processor:
            self.audio_processor.stop()
            self.audio_processor = None
            
        self.start_button.setText("开始监听")
        self.statusBar().showMessage("已停止监听")
    
    def toggle_theme(self):
        """切换主题"""
        current_theme = self.settings.value("theme", "dark")
        if current_theme == "dark":
            self.set_light_theme()
        else:
            self.set_dark_theme()
    
    def set_dark_theme(self):
        """设置暗色主题"""
        self.settings.setValue("theme", "dark")
        
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(53, 53, 53))
        palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.Base, QColor(25, 25, 25))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(53, 53, 53))
        palette.setColor(QPalette.ColorRole.ToolTipBase, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.ToolTipText, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
        palette.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.BrightText, Qt.GlobalColor.red)
        palette.setColor(QPalette.ColorRole.Highlight, QColor(142, 45, 197).lighter())
        palette.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.black)
        self.setPalette(palette)
    
    def set_light_theme(self):
        """设置亮色主题"""
        self.settings.setValue("theme", "light")
        self.setPalette(QApplication.style().standardPalette())
    
    def load_settings(self):
        """加载设置"""
        theme = self.settings.value("theme", "dark")
        if theme == "dark":
            self.set_dark_theme()
        else:
            self.set_light_theme()
        
        # 恢复窗口几何状态
        if self.settings.value("geometry"):
            self.restoreGeometry(self.settings.value("geometry"))
        if self.settings.value("windowState"):
            self.restoreState(self.settings.value("windowState"))
    
    def show_about(self):
        """显示关于对话框"""
        QMessageBox.about(self, "关于高级调音系统", 
                         "高级调音系统 v3.0\n\n"
                         "功能特性:\n"
                         "- 实时音频分析和频率检测\n"
                         "- 多种频率分析算法 (FFT, 自相关, 倒谱)\n"
                         "- 和弦识别功能\n"
                         "- 3D频谱瀑布图\n"
                         "- 录音和回放功能\n"
                         "- 可自定义参考音高\n"
                         "- 明暗主题切换\n"
                         "- 音乐理论学习参考\n"
                         "- 内置节拍器功能")
    
    def show_help(self):
        """显示帮助文档"""
        help_url = QUrl("https://github.com/yourusername/AdvancedTuner/wiki")
        QDesktopServices.openUrl(help_url)
    
    def export_data(self):
        """导出数据"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出数据", "", "CSV文件 (*.csv);;文本文件 (*.txt)"
        )
        
        if file_path:
            # 这里可以实现数据导出逻辑
            QMessageBox.information(self, "导出", "数据导出功能尚未实现")
    
    def open_metronome(self):
        """打开节拍器标签页"""
        self.tab_widget.setCurrentIndex(4)  # 假设节拍器是第5个标签页
    
    def log_note(self, note_name, octave, duration):
        """记录音符播放"""
        timestamp = time.strftime("%H:%M:%S")
        message = f"[{timestamp}] 音符 {note_name}{octave} 持续 {duration:.2f} 秒"
        self.statusBar().showMessage(message)
    
    def closeEvent(self, event):
        """应用关闭事件"""
        self.stop_audio()
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("windowState", self.saveState())
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 设置应用样式
    app.setStyle("Fusion")
    
    window = AdvancedTunerSystem()
    window.show()
    
    sys.exit(app.exec())