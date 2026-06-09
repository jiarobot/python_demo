import sys
import numpy as np
import pyqtgraph as pg
from PyQt6.QtCore import QTimer, QThread, pyqtSignal, QObject, Qt
from PyQt6.QtGui import QIcon, QFont, QPalette, QColor, QLinearGradient, QAction
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QSlider, 
                             QComboBox, QGroupBox, QSpinBox, QDoubleSpinBox,
                             QFileDialog, QMessageBox, QStatusBar,
                             QSplitter, QCheckBox, QTabWidget, QTextEdit,
                             QDial, QProgressBar, QListView, QTreeView,
                             QDockWidget, QToolBar, QToolButton, QMenu,
                             QGridLayout, QSizePolicy, QFrame, QScrollArea,
                             QInputDialog, QLineEdit, QListWidget, QListWidgetItem)
import pyaudio
import wave
import scipy.signal as signal
from scipy.io import wavfile
import scipy.fft as fft
import librosa
import librosa.display
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import soundfile as sf
import noisereduce as nr
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
import pickle
import os
import time
import tempfile
from pathlib import Path
from scipy import interpolate
import sounddevice as sd
# import aubio
# import vamp
import json


class AudioRecorder(QObject):
    """增强的音频录制线程"""
    data_available = pyqtSignal(np.ndarray)
    level_updated = pyqtSignal(float)
    
    def __init__(self, sample_rate=44100, chunk_size=1024, channels=1, device_index=None):
        super().__init__()
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.channels = channels
        self.device_index = device_index
        self.audio = pyaudio.PyAudio()
        self.stream = None
        self.recording = False
        self.frames = []
        self.peak_level = 0
        self.rms_level = 0
        
    def get_input_devices(self):
        """获取可用的输入设备列表"""
        devices = []
        for i in range(self.audio.get_device_count()):
            device_info = self.audio.get_device_info_by_index(i)
            if device_info['maxInputChannels'] > 0:
                devices.append((i, device_info['name']))
        return devices
        
    def start_recording(self):
        """开始录制音频"""
        if self.recording:
            return
            
        self.frames = []
        self.peak_level = 0
        self.rms_level = 0
        
        # 设置设备参数
        input_device_info = None
        if self.device_index is not None:
            input_device_info = self.audio.get_device_info_by_index(self.device_index)
            
        self.stream = self.audio.open(
            format=pyaudio.paInt16,
            channels=self.channels,
            rate=self.sample_rate,
            input=True,
            input_device_index=self.device_index,
            frames_per_buffer=self.chunk_size,
            stream_callback=self.callback
        )
        self.stream.start_stream()
        self.recording = True
        
    def stop_recording(self):
        """停止录制音频"""
        if not self.recording:
            return
            
        self.recording = False
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        self.stream = None
        
    def callback(self, in_data, frame_count, time_info, status):
        """音频数据回调函数"""
        if self.recording:
            audio_data = np.frombuffer(in_data, dtype=np.int16)
            self.data_available.emit(audio_data)
            self.frames.append(in_data)
            
            # 计算音频电平
            self.peak_level = np.max(np.abs(audio_data)) / 32768.0  # 16位音频的最大值
            self.rms_level = np.sqrt(np.mean(audio_data**2)) / 32768.0
            self.level_updated.emit(self.rms_level)
            
        return (in_data, pyaudio.paContinue)
    
    def save_to_file(self, filename):
        """保存录制的音频到文件"""
        if not self.frames:
            return False
            
        wf = wave.open(filename, 'wb')
        wf.setnchannels(self.channels)
        wf.setsampwidth(self.audio.get_sample_size(pyaudio.paInt16))
        wf.setframerate(self.sample_rate)
        wf.writeframes(b''.join(self.frames))
        wf.close()
        return True
        
    def get_audio_data(self):
        """获取完整的音频数据"""
        if not self.frames:
            return None
            
        audio_data = np.frombuffer(b''.join(self.frames), dtype=np.int16)
        return audio_data


class AudioPlayer(QObject):
    """音频播放线程"""
    playback_finished = pyqtSignal()
    playback_position = pyqtSignal(int)
    
    def __init__(self, sample_rate=44100, chunk_size=1024, channels=1):
        super().__init__()
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.channels = channels
        self.audio = pyaudio.PyAudio()
        self.stream = None
        self.playing = False
        self.audio_data = None
        self.position = 0
        
    def load_audio(self, audio_data):
        """加载音频数据"""
        self.audio_data = audio_data
        self.position = 0
        
    def start_playback(self):
        """开始播放音频"""
        if self.playing or self.audio_data is None:
            return
            
        self.stream = self.audio.open(
            format=pyaudio.paInt16,
            channels=self.channels,
            rate=self.sample_rate,
            output=True,
            frames_per_buffer=self.chunk_size,
            stream_callback=self.callback
        )
        self.stream.start_stream()
        self.playing = True
        
    def stop_playback(self):
        """停止播放音频"""
        if not self.playing:
            return
            
        self.playing = False
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        self.stream = None
        self.playback_finished.emit()
        
    def callback(self, in_data, frame_count, time_info, status):
        """音频播放回调函数"""
        if not self.playing:
            return (None, pyaudio.paComplete)
            
        # 计算要发送的数据量
        remaining = len(self.audio_data) - self.position
        if remaining == 0:
            self.stop_playback()
            return (None, pyaudio.paComplete)
            
        # 获取当前块的数据
        chunk_size = min(frame_count * self.channels, remaining)
        chunk = self.audio_data[self.position:self.position + chunk_size]
        self.position += chunk_size
        
        # 如果数据不足，用零填充
        if len(chunk) < frame_count * self.channels:
            padding = np.zeros(frame_count * self.channels - len(chunk), dtype=np.int16)
            chunk = np.concatenate((chunk, padding))
            
        # 发送位置更新信号
        self.playback_position.emit(self.position)
            
        return (chunk.tobytes(), pyaudio.paContinue)


class AudioAnalyzer(QThread):
    """增强的音频分析线程"""
    analysis_complete = pyqtSignal(dict)
    progress_updated = pyqtSignal(int)
    
    def __init__(self, audio_data, sample_rate, analysis_types=None):
        super().__init__()
        self.audio_data = audio_data
        self.sample_rate = sample_rate
        self.analysis_types = analysis_types or ['spectrum', 'mfcc', 'chroma', 'tempogram', 'pitch', 'beat']
        
    def run(self):
        """执行音频分析"""
        if self.audio_data is None:
            return
            
        result = {}
        
        # 转换为浮点格式用于分析
        audio_float = self.audio_data.astype(np.float32) / 32768.0
        
        # 计算频谱
        if 'spectrum' in self.analysis_types:
            self.progress_updated.emit(10)
            freqs, power = self.calculate_spectrum(audio_float)
            result['spectrum'] = {'freqs': freqs, 'power': power}
            
        # 计算MFCC
        if 'mfcc' in self.analysis_types:
            self.progress_updated.emit(20)
            mfccs = self.calculate_mfcc(audio_float)
            result['mfcc'] = mfccs
            
        # 计算色度特征
        if 'chroma' in self.analysis_types:
            self.progress_updated.emit(30)
            chroma = self.calculate_chroma(audio_float)
            result['chroma'] = chroma
            
        # 计算节奏特征
        if 'tempogram' in self.analysis_types:
            self.progress_updated.emit(40)
            tempogram = self.calculate_tempogram(audio_float)
            result['tempogram'] = tempogram
            
        # 计算音高
        # if 'pitch' in self.analysis_types:
        #     self.progress_updated.emit(50)
        #     pitch = self.calculate_pitch(audio_float)
        #     result['pitch'] = pitch
            
        # 计算节拍
        if 'beat' in self.analysis_types:
            self.progress_updated.emit(60)
            beats = self.calculate_beats(audio_float)
            result['beats'] = beats
            
        # 计算基本统计特征
        self.progress_updated.emit(80)
        result['stats'] = self.calculate_statistics(audio_float)
        
        # 计算谐波和冲击成分
        self.progress_updated.emit(90)
        result['hpr'] = self.calculate_harmonic_percussive(audio_float)
        
        self.progress_updated.emit(100)
        self.analysis_complete.emit(result)
        
    def calculate_spectrum(self, audio_data):
        """计算音频频谱"""
        # 使用汉宁窗
        window = np.hanning(len(audio_data))
        windowed_data = audio_data * window
        
        # 计算FFT
        fft_data = fft.rfft(windowed_data)
        fft_magnitude = np.abs(fft_data)
        
        # 计算频率和功率
        freqs = fft.rfftfreq(len(windowed_data), 1.0/self.sample_rate)
        power = fft_magnitude ** 2
        
        # 只保留正频率部分
        mask = freqs > 0
        return freqs[mask], power[mask]
        
    def calculate_mfcc(self, audio_data, n_mfcc=13):
        """计算MFCC特征"""
        mfccs = librosa.feature.mfcc(
            y=audio_data, 
            sr=self.sample_rate, 
            n_mfcc=n_mfcc,
            n_fft=2048,
            hop_length=512
        )
        return mfccs
        
    def calculate_chroma(self, audio_data):
        """计算色度特征"""
        chroma = librosa.feature.chroma_stft(
            y=audio_data,
            sr=self.sample_rate,
            n_fft=2048,
            hop_length=512
        )
        return chroma
        
    def calculate_tempogram(self, audio_data):
        """计算节奏特征"""
        onset_env = librosa.onset.onset_strength(
            y=audio_data, 
            sr=self.sample_rate,
            hop_length=512
        )
        tempogram = librosa.feature.tempogram(
            onset_envelope=onset_env,
            sr=self.sample_rate,
            hop_length=512
        )
        return tempogram
        
    # def calculate_pitch(self, audio_data):
    #     """计算音高"""
    #     # 使用aubio进行音高检测
    #     win_s = 2048
    #     hop_s = 512
    #     tolerance = 0.8
        
    #     pitch_o = aubio.pitch("default", win_s, hop_s, self.sample_rate)
    #     pitch_o.set_unit("midi")
    #     pitch_o.set_tolerance(tolerance)
        
    #     pitches = []
    #     confidences = []
        
    #     total_frames = len(audio_data) // hop_s
        
    #     for i in range(total_frames):
    #         frame = audio_data[i*hop_s:(i+1)*hop_s]
    #         pitch = pitch_o(frame)[0]
    #         confidence = pitch_o.get_confidence()
            
    #         pitches.append(pitch)
    #         confidences.append(confidence)
            
    #     return {'pitches': np.array(pitches), 'confidences': np.array(confidences)}
        
    def calculate_beats(self, audio_data):
        """计算节拍"""
        tempo, beat_frames = librosa.beat.beat_track(
            y=audio_data, 
            sr=self.sample_rate,
            hop_length=512
        )
        
        beat_times = librosa.frames_to_time(beat_frames, sr=self.sample_rate, hop_length=512)
        
        return {'tempo': tempo, 'beat_times': beat_times}
        
    def calculate_harmonic_percussive(self, audio_data):
        """分离谐波和冲击成分"""
        harmonic, percussive = librosa.effects.hpss(audio_data)
        return {'harmonic': harmonic, 'percussive': percussive}
        
    def calculate_statistics(self, audio_data):
        """计算音频统计特征"""
        # RMS能量
        rms = np.sqrt(np.mean(audio_data**2))
        
        # 零交叉率
        zero_crossings = np.sum(np.diff(np.sign(audio_data)) != 0) / len(audio_data)
        
        # 频谱中心
        freqs, power = self.calculate_spectrum(audio_data)
        spectral_centroid = np.sum(freqs * power) / np.sum(power) if np.sum(power) > 0 else 0
        
        # 频谱滚降点
        spectral_rolloff = librosa.feature.spectral_rolloff(
            y=audio_data, 
            sr=self.sample_rate
        )[0]
        
        # 频谱带宽
        spectral_bandwidth = librosa.feature.spectral_bandwidth(
            y=audio_data, 
            sr=self.sample_rate
        )[0]
        
        # 频谱平坦度
        spectral_flatness = librosa.feature.spectral_flatness(
            y=audio_data
        )[0]
        
        # 频谱对比度
        spectral_contrast = librosa.feature.spectral_contrast(
            y=audio_data, 
            sr=self.sample_rate
        )[0]
        
        return {
            'rms': rms,
            'zero_crossings': zero_crossings,
            'spectral_centroid': spectral_centroid,
            'spectral_rolloff': np.mean(spectral_rolloff),
            'spectral_bandwidth': np.mean(spectral_bandwidth),
            'spectral_flatness': np.mean(spectral_flatness),
            'spectral_contrast': np.mean(spectral_contrast)
        }


class AudioEffects:
    """音频效果处理器"""
    @staticmethod
    def apply_reverb(audio_data, sample_rate, decay=0.5, wet_level=0.3):
        """应用混响效果"""
        # 创建冲激响应
        length = int(sample_rate * decay)
        t = np.linspace(0, decay, length)
        impulse = np.exp(-5 * t) * np.sin(2 * np.pi * 5 * t)
        
        # 归一化
        impulse = impulse / np.max(np.abs(impulse))
        
        # 应用卷积
        reverberated = signal.convolve(audio_data, impulse, mode='same')
        
        # 混合原始和混响信号
        result = (1 - wet_level) * audio_data + wet_level * reverberated
        
        # 防止削波
        result = result / np.max(np.abs(result)) * 0.99
        
        return result
        
    @staticmethod
    def apply_delay(audio_data, sample_rate, delay_time=0.3, feedback=0.5, wet_level=0.5):
        """应用延迟效果"""
        delay_samples = int(delay_time * sample_rate)
        result = np.copy(audio_data)
        
        # 应用延迟
        for i in range(delay_samples, len(audio_data)):
            result[i] += feedback * result[i - delay_samples]
            
        # 混合原始和延迟信号
        result = (1 - wet_level) * audio_data + wet_level * result
        
        # 防止削波
        result = result / np.max(np.abs(result)) * 0.99
        
        return result
        
    @staticmethod
    def apply_distortion(audio_data, gain=2.0, level=0.8):
        """应用失真效果"""
        # 应用增益
        distorted = audio_data * gain
        
        # 应用非线性函数（软削波）
        distorted = np.tanh(distorted)
        
        # 混合原始和失真信号
        result = (1 - level) * audio_data + level * distorted
        
        # 防止削波
        result = result / np.max(np.abs(result)) * 0.99
        
        return result
        
    @staticmethod
    def apply_compressor(audio_data, threshold=0.5, ratio=4.0, attack=0.01, release=0.1, sample_rate=44100):
        """应用压缩器效果"""
        # 转换为分贝
        db_threshold = 20 * np.log10(threshold + 1e-10)
        
        # 初始化增益减少
        gain_reduction = 0
        attack_coeff = np.exp(-1 / (attack * sample_rate))
        release_coeff = np.exp(-1 / (release * sample_rate))
        
        result = np.zeros_like(audio_data)
        
        for i in range(len(audio_data)):
            # 计算当前样本的dB值
            db = 20 * np.log10(np.abs(audio_data[i]) + 1e-10)
            
            # 如果超过阈值，计算需要的增益减少
            if db > db_threshold:
                excess = db - db_threshold
                target_reduction = excess * (1 - 1/ratio)
                
                # 应用攻击和释放时间
                if target_reduction > gain_reduction:
                    gain_reduction = attack_coeff * gain_reduction + (1 - attack_coeff) * target_reduction
                else:
                    gain_reduction = release_coeff * gain_reduction + (1 - release_coeff) * target_reduction
            else:
                # 释放增益减少
                gain_reduction = release_coeff * gain_reduction
            
            # 应用增益减少
            linear_reduction = 10 ** (-gain_reduction / 20)
            result[i] = audio_data[i] * linear_reduction
            
        return result
        
    @staticmethod
    def apply_tremolo(audio_data, sample_rate, freq=5, depth=0.8):
        """应用颤音效果"""
        t = np.arange(len(audio_data)) / sample_rate
        modulator = 1 - depth + depth * np.sin(2 * np.pi * freq * t)
        return audio_data * modulator
        
    @staticmethod
    def apply_chorus(audio_data, sample_rate, delay=0.03, depth=0.004, freq=0.5, mix=0.5):
        """应用合唱效果"""
        t = np.arange(len(audio_data)) / sample_rate
        delay_mod = delay + depth * np.sin(2 * np.pi * freq * t)
        
        # 创建延迟信号
        delayed = np.zeros_like(audio_data)
        for i in range(len(audio_data)):
            delay_samples = int(delay_mod[i] * sample_rate)
            if i >= delay_samples:
                delayed[i] = audio_data[i - delay_samples]
        
        # 混合原始和延迟信号
        return (1 - mix) * audio_data + mix * delayed
        
    @staticmethod
    def apply_phaser(audio_data, sample_rate, rate=0.5, depth=0.8, feedback=0.7, mix=0.5):
        """应用相位效果"""
        # 创建全通滤波器链
        n_allpass = 4  # 4个全通滤波器
        delays = np.zeros(n_allpass)
        outputs = np.zeros(n_allpass)
        
        result = np.zeros_like(audio_data)
        t = np.arange(len(audio_data)) / sample_rate
        
        # LFO调制
        lfo = depth * np.sin(2 * np.pi * rate * t)
        
        for i in range(len(audio_data)):
            # 计算当前延迟
            delay = 1 + int(10 * (1 + lfo[i]))  # 1-21个样本的延迟
            
            # 处理全通滤波器链
            x = audio_data[i]
            for j in range(n_allpass):
                # 全通滤波器计算
                y = -x + delays[j]
                delays[j] = x + feedback * delays[j]
                x = y
                outputs[j] = y
            
            # 混合原始和效果信号
            result[i] = (1 - mix) * audio_data[i] + mix * np.sum(outputs)
            
        return result


class AudioFilter:
    """增强的音频滤波器类"""
    @staticmethod
    def apply_highpass(audio_data, sample_rate, cutoff_freq, order=5):
        """应用高通滤波器"""
        nyquist = 0.5 * sample_rate
        normal_cutoff = cutoff_freq / nyquist
        b, a = signal.butter(order, normal_cutoff, btype='high', analog=False)
        filtered_data = signal.filtfilt(b, a, audio_data)
        return filtered_data
        
    @staticmethod
    def apply_lowpass(audio_data, sample_rate, cutoff_freq, order=5):
        """应用低通滤波器"""
        nyquist = 0.5 * sample_rate
        normal_cutoff = cutoff_freq / nyquist
        b, a = signal.butter(order, normal_cutoff, btype='low', analog=False)
        filtered_data = signal.filtfilt(b, a, audio_data)
        return filtered_data
        
    @staticmethod
    def apply_bandpass(audio_data, sample_rate, low_cut, high_cut, order=5):
        """应用带通滤波器"""
        nyquist = 0.5 * sample_rate
        low = low_cut / nyquist
        high = high_cut / nyquist
        b, a = signal.butter(order, [low, high], btype='band', analog=False)
        filtered_data = signal.filtfilt(b, a, audio_data)
        return filtered_data
        
    @staticmethod
    def apply_bandstop(audio_data, sample_rate, low_cut, high_cut, order=5):
        """应用带阻滤波器"""
        nyquist = 0.5 * sample_rate
        low = low_cut / nyquist
        high = high_cut / nyquist
        b, a = signal.butter(order, [low, high], btype='bandstop', analog=False)
        filtered_data = signal.filtfilt(b, a, audio_data)
        return filtered_data
        
    @staticmethod
    def apply_eq(audio_data, sample_rate, center_freq, gain, q=1.0):
        """应用均衡器"""
        nyquist = 0.5 * sample_rate
        center = center_freq / nyquist
        
        # 设计峰值滤波器
        b, a = signal.iirpeak(center, q)
        
        # 应用滤波器
        filtered_data = signal.lfilter(b, a, audio_data)
        
        # 应用增益
        result = audio_data + (filtered_data * gain)
        
        # 防止削波
        result = result / np.max(np.abs(result)) * 0.99
        
        return result
        
    @staticmethod
    def apply_high_shelf(audio_data, sample_rate, cutoff_freq, gain, q=0.707):
        """应用高架滤波器"""
        nyquist = 0.5 * sample_rate
        normal_cutoff = cutoff_freq / nyquist
        
        # 设计高架滤波器
        b, a = signal.iirfilter(2, normal_cutoff, btype='high', 
                               ftype='butter', output='ba')
        
        # 应用增益
        if gain > 0:
            # 提升
            k = 10**(gain/20)
            b = b * k
        else:
            # 削减
            k = 10**(-gain/20)
            a[1:] = a[1:] * k
            
        filtered_data = signal.lfilter(b, a, audio_data)
        return filtered_data
        
    @staticmethod
    def apply_low_shelf(audio_data, sample_rate, cutoff_freq, gain, q=0.707):
        """应用低架滤波器"""
        nyquist = 0.5 * sample_rate
        normal_cutoff = cutoff_freq / nyquist
        
        # 设计低架滤波器
        b, a = signal.iirfilter(2, normal_cutoff, btype='low', 
                               ftype='butter', output='ba')
        
        # 应用增益
        if gain > 0:
            # 提升
            k = 10**(gain/20)
            b = b * k
        else:
            # 削减
            k = 10**(-gain/20)
            a[1:] = a[1:] * k
            
        filtered_data = signal.lfilter(b, a, audio_data)
        return filtered_data


class NoiseReducer:
    """噪声消除器"""
    @staticmethod
    def reduce_noise(audio_data, sample_rate, noise_start=0, noise_end=1000, prop_decrease=1.0):
        """使用noisereduce库减少噪声"""
        # 提取噪声样本
        noise_clip = audio_data[noise_start:noise_end]
        
        # 应用噪声减少
        reduced_noise = nr.reduce_noise(
            y=audio_data,
            sr=sample_rate,
            y_noise=noise_clip,
            prop_decrease=prop_decrease
        )
        
        return reduced_noise
        
    @staticmethod
    def reduce_noise_spectral_subtraction(audio_data, sample_rate, noise_threshold=0.1):
        """使用谱减法减少噪声"""
        # 计算STFT
        f, t, stft = signal.stft(audio_data, fs=sample_rate, nperseg=1024)
        
        # 计算幅度谱和相位谱
        magnitude = np.abs(stft)
        phase = np.angle(stft)
        
        # 估计噪声谱
        noise_estimate = np.mean(magnitude[:, :10], axis=1)
        
        # 应用谱减法
        magnitude_reduced = np.maximum(magnitude - noise_estimate[:, np.newaxis] * noise_threshold, 0)
        
        # 重建STFT
        stft_reduced = magnitude_reduced * np.exp(1j * phase)
        
        # 逆STFT
        _, reduced_noise = signal.istft(stft_reduced, fs=sample_rate)
        
        # 确保长度匹配
        if len(reduced_noise) > len(audio_data):
            reduced_noise = reduced_noise[:len(audio_data)]
        elif len(reduced_noise) < len(audio_data):
            reduced_noise = np.pad(reduced_noise, (0, len(audio_data) - len(reduced_noise)))
            
        return reduced_noise
        
    @staticmethod
    def reduce_noise_wavelet(audio_data, threshold=0.1, wavelet='db4', level=5):
        """使用小波变换减少噪声"""
        # 执行小波变换
        coeffs = pywt.wavedec(audio_data, wavelet, level=level)
        
        # 应用阈值
        sigma = np.median(np.abs(coeffs[-level])) / 0.6745
        uthresh = sigma * np.sqrt(2 * np.log(len(audio_data)))
        coeffs = [pywt.threshold(c, uthresh, mode='soft') for c in coeffs]
        
        # 重建信号
        reconstructed = pywt.waverec(coeffs, wavelet)
        
        # 确保长度匹配
        if len(reconstructed) > len(audio_data):
            reconstructed = reconstructed[:len(audio_data)]
        elif len(reconstructed) < len(audio_data):
            reconstructed = np.pad(reconstructed, (0, len(audio_data) - len(reconstructed)))
            
        return reconstructed


class MLProcessor:
    """机器学习处理器"""
    def __init__(self):
        self.scaler = StandardScaler()
        self.pca = PCA(n_components=2)
        self.kmeans = KMeans(n_clusters=3)
        self.models = {}
        
    def extract_features(self, audio_data, sample_rate):
        """提取音频特征用于机器学习"""
        features = []
        
        # MFCC特征
        mfccs = librosa.feature.mfcc(y=audio_data, sr=sample_rate, n_mfcc=13)
        features.extend(np.mean(mfccs, axis=1))
        features.extend(np.std(mfccs, axis=1))
        
        # 色度特征
        chroma = librosa.feature.chroma_stft(y=audio_data, sr=sample_rate)
        features.extend(np.mean(chroma, axis=1))
        features.extend(np.std(chroma, axis=1))
        
        # 频谱特征
        spectral_centroid = librosa.feature.spectral_centroid(y=audio_data, sr=sample_rate)
        features.append(np.mean(spectral_centroid))
        features.append(np.std(spectral_centroid))
        
        spectral_rolloff = librosa.feature.spectral_rolloff(y=audio_data, sr=sample_rate)
        features.append(np.mean(spectral_rolloff))
        features.append(np.std(spectral_rolloff))
        
        spectral_bandwidth = librosa.feature.spectral_bandwidth(y=audio_data, sr=sample_rate)
        features.append(np.mean(spectral_bandwidth))
        features.append(np.std(spectral_bandwidth))
        
        spectral_flatness = librosa.feature.spectral_flatness(y=audio_data)
        features.append(np.mean(spectral_flatness))
        features.append(np.std(spectral_flatness))
        
        # 零交叉率
        zero_crossing_rate = librosa.feature.zero_crossing_rate(audio_data)
        features.append(np.mean(zero_crossing_rate))
        features.append(np.std(zero_crossing_rate))
        
        # RMS能量
        rms = librosa.feature.rms(y=audio_data)
        features.append(np.mean(rms))
        features.append(np.std(rms))
        
        # 节奏特征
        onset_env = librosa.onset.onset_strength(y=audio_data, sr=sample_rate)
        features.append(np.mean(onset_env))
        features.append(np.std(onset_env))
        
        return np.array(features)
        
    def train_model(self, features, model_type='kmeans'):
        """训练机器学习模型"""
        # 标准化特征
        features_scaled = self.scaler.fit_transform(features)
        
        if model_type == 'kmeans':
            # 训练K-means模型
            labels = self.kmeans.fit_predict(features_scaled)
            
            # 应用PCA进行可视化
            features_pca = self.pca.fit_transform(features_scaled)
            
            return labels, features_pca
            
        elif model_type == 'pca':
            # 只应用PCA
            features_pca = self.pca.fit_transform(features_scaled)
            return features_pca
            
    def save_model(self, filename):
        """保存模型到文件"""
        with open(filename, 'wb') as f:
            pickle.dump({
                'scaler': self.scaler,
                'pca': self.pca,
                'kmeans': self.kmeans
            }, f)
            
    def load_model(self, filename):
        """从文件加载模型"""
        with open(filename, 'rb') as f:
            models = pickle.load(f)
            self.scaler = models['scaler']
            self.pca = models['pca']
            self.kmeans = models['kmeans']


class SpectrogramWidget(FigureCanvas):
    """频谱图显示部件"""
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        super().__init__(self.fig)
        self.setParent(parent)
        
        self.axes = self.fig.add_subplot(111)
        self.fig.tight_layout()
        
    def plot_spectrogram(self, audio_data, sample_rate):
        """绘制频谱图"""
        self.axes.clear()
        
        # 计算并绘制频谱图
        n_fft = 2048
        hop_length = 512
        
        # 使用librosa计算频谱图
        D = librosa.amplitude_to_db(
            np.abs(librosa.stft(audio_data.astype(np.float32), n_fft=n_fft, hop_length=hop_length)),
            ref=np.max
        )
        
        # 绘制频谱图
        img = librosa.display.specshow(
            D, 
            sr=sample_rate, 
            hop_length=hop_length, 
            x_axis='time', 
            y_axis='log', 
            ax=self.axes
        )
        
        self.fig.colorbar(img, ax=self.axes, format="%+2.0f dB")
        self.axes.set_title('频谱图')
        self.draw()
        
    def plot_mel_spectrogram(self, audio_data, sample_rate):
        """绘制梅尔频谱图"""
        self.axes.clear()
        
        # 计算梅尔频谱图
        mel_spec = librosa.feature.melspectrogram(
            y=audio_data.astype(np.float32), 
            sr=sample_rate,
            n_fft=2048,
            hop_length=512,
            n_mels=128
        )
        mel_spec_db = librosa.power_to_db(mel_spec, ref=np.max)
        
        # 绘制梅尔频谱图
        img = librosa.display.specshow(
            mel_spec_db, 
            sr=sample_rate, 
            hop_length=512, 
            x_axis='time', 
            y_axis='mel', 
            ax=self.axes
        )
        
        self.fig.colorbar(img, ax=self.axes, format="%+2.0f dB")
        self.axes.set_title('梅尔频谱图')
        self.draw()


class WaveformWidget(pg.PlotWidget):
    """波形显示部件"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setBackground('w')
        self.showGrid(x=True, y=True)
        self.setLabel('left', '振幅')
        self.setLabel('bottom', '时间', 's')
        
    def plot_waveform(self, audio_data, sample_rate):
        """绘制波形"""
        self.clear()
        
        # 创建时间轴
        time_axis = np.linspace(0, len(audio_data) / sample_rate, len(audio_data))
        
        # 绘制波形
        self.plot(time_axis, audio_data, pen=pg.mkPen('b', width=1))
        
    def plot_comparison(self, original_data, processed_data, sample_rate):
        """绘制原始和处理后的波形对比"""
        self.clear()
        
        # 创建时间轴
        time_axis = np.linspace(0, len(original_data) / sample_rate, len(original_data))
        
        # 绘制原始波形
        self.plot(time_axis, original_data, pen=pg.mkPen('b', width=1), name='原始')
        
        # 绘制处理后的波形
        self.plot(time_axis, processed_data, pen=pg.mkPen('r', width=1), name='处理')
        
        # 添加图例
        self.addLegend()


class SpectrumWidget(pg.PlotWidget):
    """频谱显示部件"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setBackground('w')
        self.showGrid(x=True, y=True)
        self.setLabel('left', '功率')
        self.setLabel('bottom', '频率', 'Hz')
        self.setLogMode(x=True, y=True)
        
    def plot_spectrum(self, freqs, power):
        """绘制频谱"""
        self.clear()
        self.plot(freqs, power, pen=pg.mkPen('b', width=1))
        
    def plot_comparison(self, freqs_orig, power_orig, freqs_proc, power_proc):
        """绘制原始和处理后的频谱对比"""
        self.clear()
        
        # 绘制原始频谱
        self.plot(freqs_orig, power_orig, pen=pg.mkPen('b', width=1), name='原始')
        
        # 绘制处理后的频谱
        self.plot(freqs_proc, power_proc, pen=pg.mkPen('r', width=1), name='处理')
        
        # 添加图例
        self.addLegend()


class AudioRecorderApp(QMainWindow):
    """主应用程序窗口"""
    def __init__(self):
        super().__init__()
        self.recorder = None
        self.player = None
        self.audio_data = None
        self.processed_data = None
        self.sample_rate = 44100
        self.chunk_size = 1024
        self.ml_processor = MLProcessor()
        self.init_ui()
        self.init_audio()
        
    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("高级音频处理与分析工具")
        self.setGeometry(100, 100, 1400, 900)
        
        # 设置应用程序样式
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2b2b2b;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #555;
                border-radius: 5px;
                margin-top: 1ex;
                padding-top: 10px;
                background-color: #3c3c3c;
                color: #ddd;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #6af;
            }
            QPushButton {
                background-color: #505050;
                border: 1px solid #555;
                border-radius: 3px;
                padding: 5px;
                color: #ddd;
            }
            QPushButton:hover {
                background-color: #606060;
            }
            QPushButton:pressed {
                background-color: #404040;
            }
            QPushButton:disabled {
                background-color: #353535;
                color: #777;
            }
            QLabel {
                color: #ddd;
            }
            QComboBox, QSpinBox, QDoubleSpinBox, QLineEdit {
                background-color: #454545;
                border: 1px solid #555;
                border-radius: 3px;
                padding: 3px;
                color: #ddd;
            }
            QSlider::groove:horizontal {
                border: 1px solid #555;
                height: 8px;
                background: #454545;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #6af;
                border: 1px solid #5a5;
                width: 18px;
                margin: -5px 0;
                border-radius: 9px;
            }
            QTabWidget::pane {
                border: 1px solid #555;
                background: #3c3c3c;
            }
            QTabBar::tab {
                background: #454545;
                color: #ddd;
                padding: 8px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background: #505050;
                border-bottom-color: #6af;
            }
        """)
        
        # 创建中央部件和主布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # 创建左侧控制面板
        control_panel = QWidget()
        control_panel.setMaximumWidth(350)
        control_layout = QVBoxLayout(control_panel)
        
        # 创建选项卡控件
        self.tab_widget = QTabWidget()
        control_layout.addWidget(self.tab_widget)
        
        # 录制选项卡
        record_tab = QWidget()
        record_layout = QVBoxLayout(record_tab)
        
        # 录制设置组
        record_group = QGroupBox("录制设置")
        record_group_layout = QVBoxLayout(record_group)
        
        # 设备选择
        device_layout = QHBoxLayout()
        device_layout.addWidget(QLabel("输入设备:"))
        self.device_combo = QComboBox()
        device_layout.addWidget(self.device_combo)
        record_group_layout.addLayout(device_layout)
        
        # 采样率和块大小
        sample_rate_layout = QHBoxLayout()
        sample_rate_layout.addWidget(QLabel("采样率:"))
        self.sample_rate_combo = QComboBox()
        self.sample_rate_combo.addItems(["44100", "48000", "22050", "11025", "96000"])
        self.sample_rate_combo.setCurrentText("44100")
        sample_rate_layout.addWidget(self.sample_rate_combo)
        record_group_layout.addLayout(sample_rate_layout)
        
        chunk_size_layout = QHBoxLayout()
        chunk_size_layout.addWidget(QLabel("块大小:"))
        self.chunk_size_spin = QSpinBox()
        self.chunk_size_spin.setRange(256, 4096)
        self.chunk_size_spin.setValue(1024)
        self.chunk_size_spin.setSingleStep(256)
        chunk_size_layout.addWidget(self.chunk_size_spin)
        record_group_layout.addLayout(chunk_size_layout)
        
        # 电平表
        level_layout = QHBoxLayout()
        level_layout.addWidget(QLabel("电平:"))
        self.level_meter = QProgressBar()
        self.level_meter.setRange(0, 100)
        self.level_meter.setTextVisible(False)
        level_layout.addWidget(self.level_meter)
        record_group_layout.addLayout(level_layout)
        
        record_layout.addWidget(record_group)
        
        # 控制按钮
        self.record_btn = QPushButton("开始录制")
        self.stop_btn = QPushButton("停止录制")
        self.stop_btn.setEnabled(False)
        self.play_btn = QPushButton("播放")
        self.play_btn.setEnabled(False)
        self.stop_play_btn = QPushButton("停止播放")
        self.stop_play_btn.setEnabled(False)
        
        button_layout = QGridLayout()
        button_layout.addWidget(self.record_btn, 0, 0)
        button_layout.addWidget(self.stop_btn, 0, 1)
        button_layout.addWidget(self.play_btn, 1, 0)
        button_layout.addWidget(self.stop_play_btn, 1, 1)
        record_layout.addLayout(button_layout)
        
        # 添加到选项卡
        self.tab_widget.addTab(record_tab, "录制")
        
        # 处理选项卡
        process_tab = QWidget()
        process_layout = QVBoxLayout(process_tab)
        
        # 滤波器组
        filter_group = QGroupBox("滤波器")
        filter_layout = QVBoxLayout(filter_group)
        
        self.filter_type_combo = QComboBox()
        self.filter_type_combo.addItems(["无", "高通", "低通", "带通", "带阻", "均衡器", "高架", "低架"])
        filter_layout.addWidget(QLabel("滤波器类型:"))
        filter_layout.addWidget(self.filter_type_combo)
        
        self.cutoff_freq_spin = QDoubleSpinBox()
        self.cutoff_freq_spin.setRange(20, 20000)
        self.cutoff_freq_spin.setValue(1000)
        self.cutoff_freq_spin.setSuffix(" Hz")
        filter_layout.addWidget(QLabel("截止频率:"))
        filter_layout.addWidget(self.cutoff_freq_spin)
        
        self.high_cut_spin = QDoubleSpinBox()
        self.high_cut_spin.setRange(20, 20000)
        self.high_cut_spin.setValue(5000)
        self.high_cut_spin.setSuffix(" Hz")
        filter_layout.addWidget(QLabel("高截止频率:"))
        filter_layout.addWidget(self.high_cut_spin)
        
        self.eq_gain_slider = QSlider(Qt.Orientation.Horizontal)
        self.eq_gain_slider.setRange(-20, 20)
        self.eq_gain_slider.setValue(0)
        filter_layout.addWidget(QLabel("均衡器增益:"))
        filter_layout.addWidget(self.eq_gain_slider)
        
        self.apply_filter_btn = QPushButton("应用滤波器")
        self.apply_filter_btn.setEnabled(False)
        filter_layout.addWidget(self.apply_filter_btn)
        
        process_layout.addWidget(filter_group)
        
        # 效果器组
        effect_group = QGroupBox("效果器")
        effect_layout = QVBoxLayout(effect_group)
        
        self.effect_type_combo = QComboBox()
        self.effect_type_combo.addItems(["无", "混响", "延迟", "失真", "压缩器", "颤音", "合唱", "相位"])
        effect_layout.addWidget(QLabel("效果类型:"))
        effect_layout.addWidget(self.effect_type_combo)
        
        self.reverb_decay_slider = QSlider(Qt.Orientation.Horizontal)
        self.reverb_decay_slider.setRange(1, 100)
        self.reverb_decay_slider.setValue(50)
        effect_layout.addWidget(QLabel("混响衰减:"))
        effect_layout.addWidget(self.reverb_decay_slider)
        
        self.delay_time_slider = QSlider(Qt.Orientation.Horizontal)
        self.delay_time_slider.setRange(1, 100)
        self.delay_time_slider.setValue(30)
        effect_layout.addWidget(QLabel("延迟时间:"))
        effect_layout.addWidget(self.delay_time_slider)
        
        self.apply_effect_btn = QPushButton("应用效果")
        self.apply_effect_btn.setEnabled(False)
        effect_layout.addWidget(self.apply_effect_btn)
        
        process_layout.addWidget(effect_group)
        
        # 噪声消除组
        noise_group = QGroupBox("噪声消除")
        noise_layout = QVBoxLayout(noise_group)
        
        self.noise_reduction_combo = QComboBox()
        self.noise_reduction_combo.addItems(["无", "谱减法", "NoiseReduce", "小波变换"])
        noise_layout.addWidget(QLabel("降噪方法:"))
        noise_layout.addWidget(self.noise_reduction_combo)
        
        self.noise_start_spin = QSpinBox()
        self.noise_start_spin.setRange(0, 10000)
        self.noise_start_spin.setValue(0)
        noise_layout.addWidget(QLabel("噪声开始样本:"))
        noise_layout.addWidget(self.noise_start_spin)
        
        self.noise_end_spin = QSpinBox()
        self.noise_end_spin.setRange(0, 10000)
        self.noise_end_spin.setValue(1000)
        noise_layout.addWidget(QLabel("噪声结束样本:"))
        noise_layout.addWidget(self.noise_end_spin)
        
        self.apply_noise_reduction_btn = QPushButton("应用降噪")
        self.apply_noise_reduction_btn.setEnabled(False)
        noise_layout.addWidget(self.apply_noise_reduction_btn)
        
        process_layout.addWidget(noise_group)
        process_layout.addStretch()
        
        self.tab_widget.addTab(process_tab, "处理")
        
        # 分析选项卡
        analysis_tab = QWidget()
        analysis_layout = QVBoxLayout(analysis_tab)
        
        # 分析选项组
        analysis_options_group = QGroupBox("分析选项")
        analysis_options_layout = QVBoxLayout(analysis_options_group)
        
        self.analysis_type_combo = QComboBox()
        self.analysis_type_combo.addItems(["频谱", "MFCC", "色度特征", "节奏分析", "音高检测", "节拍检测", "全部"])
        analysis_options_layout.addWidget(QLabel("分析类型:"))
        analysis_options_layout.addWidget(self.analysis_type_combo)
        
        self.analyze_btn = QPushButton("分析音频")
        self.analyze_btn.setEnabled(False)
        analysis_options_layout.addWidget(self.analyze_btn)
        
        analysis_layout.addWidget(analysis_options_group)
        
        # 分析结果显示
        analysis_results_group = QGroupBox("分析结果")
        analysis_results_layout = QVBoxLayout(analysis_results_group)
        
        self.analysis_results_text = QTextEdit()
        self.analysis_results_text.setReadOnly(True)
        analysis_results_layout.addWidget(self.analysis_results_text)
        
        analysis_layout.addWidget(analysis_results_group)
        
        self.tab_widget.addTab(analysis_tab, "分析")
        
        # 机器学习选项卡
        ml_tab = QWidget()
        ml_layout = QVBoxLayout(ml_tab)
        
        # 特征提取组
        feature_group = QGroupBox("特征提取")
        feature_layout = QVBoxLayout(feature_group)
        
        self.extract_features_btn = QPushButton("提取特征")
        self.extract_features_btn.setEnabled(False)
        feature_layout.addWidget(self.extract_features_btn)
        
        self.features_text = QTextEdit()
        self.features_text.setReadOnly(True)
        feature_layout.addWidget(self.features_text)
        
        ml_layout.addWidget(feature_group)
        
        # 模型训练组
        model_group = QGroupBox("模型训练")
        model_layout = QVBoxLayout(model_group)
        
        self.model_type_combo = QComboBox()
        self.model_type_combo.addItems(["K-means聚类", "PCA降维"])
        model_layout.addWidget(QLabel("模型类型:"))
        model_layout.addWidget(self.model_type_combo)
        
        self.train_model_btn = QPushButton("训练模型")
        self.train_model_btn.setEnabled(False)
        model_layout.addWidget(self.train_model_btn)
        
        ml_layout.addWidget(model_group)
        ml_layout.addStretch()
        
        self.tab_widget.addTab(ml_tab, "机器学习")
        
        # 添加到主布局
        main_layout.addWidget(control_panel)
        
        # 创建右侧图形显示区域
        display_tabs = QTabWidget()
        main_layout.addWidget(display_tabs, 1)
        
        # 波形选项卡
        waveform_tab = QWidget()
        waveform_layout = QVBoxLayout(waveform_tab)
        
        self.waveform_widget = WaveformWidget()
        waveform_layout.addWidget(self.waveform_widget)
        
        display_tabs.addTab(waveform_tab, "波形")
        
        # 频谱选项卡
        spectrum_tab = QWidget()
        spectrum_layout = QVBoxLayout(spectrum_tab)
        
        self.spectrum_widget = SpectrumWidget()
        spectrum_layout.addWidget(self.spectrum_widget)
        
        display_tabs.addTab(spectrum_tab, "频谱")
        
        # 频谱图选项卡
        spectrogram_tab = QWidget()
        spectrogram_layout = QVBoxLayout(spectrogram_tab)
        
        self.spectrogram_widget = SpectrogramWidget()
        spectrogram_layout.addWidget(self.spectrogram_widget)
        
        display_tabs.addTab(spectrogram_tab, "频谱图")
        
        # 创建状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪")
        
        # 创建菜单
        self.create_menu()
        
        # 连接信号和槽
        self.record_btn.clicked.connect(self.start_recording)
        self.stop_btn.clicked.connect(self.stop_recording)
        self.play_btn.clicked.connect(self.start_playback)
        self.stop_play_btn.clicked.connect(self.stop_playback)
        self.analyze_btn.clicked.connect(self.analyze_audio)
        self.apply_filter_btn.clicked.connect(self.apply_filter)
        self.apply_effect_btn.clicked.connect(self.apply_effect)
        self.apply_noise_reduction_btn.clicked.connect(self.apply_noise_reduction)
        self.extract_features_btn.clicked.connect(self.extract_features)
        self.train_model_btn.clicked.connect(self.train_model)
        
        # 更新设备列表
        self.update_device_list()
        
    def create_menu(self):
        """创建菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu('文件')
        
        open_action = QAction('打开', self)
        open_action.setShortcut('Ctrl+O')
        open_action.triggered.connect(self.open_audio)
        file_menu.addAction(open_action)
        
        save_action = QAction('保存', self)
        save_action.setShortcut('Ctrl+S')
        save_action.triggered.connect(self.save_audio)
        file_menu.addAction(save_action)
        
        exit_action = QAction('退出', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 工具菜单
        tool_menu = menubar.addMenu('工具')
        
        batch_action = QAction('批量处理', self)
        batch_action.triggered.connect(self.batch_process)
        tool_menu.addAction(batch_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu('帮助')
        
        about_action = QAction('关于', self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
    def init_audio(self):
        """初始化音频系统"""
        # 设置定时器用于实时更新
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_display)
        self.timer.start(50)  # 20 Hz更新频率
        
    def update_device_list(self):
        """更新输入设备列表"""
        if not self.recorder:
            self.recorder = AudioRecorder()
            
        devices = self.recorder.get_input_devices()
        self.device_combo.clear()
        
        for index, name in devices:
            self.device_combo.addItem(name, index)
            
    def start_recording(self):
        """开始录制音频"""
        self.sample_rate = int(self.sample_rate_combo.currentText())
        self.chunk_size = self.chunk_size_spin.value()
        device_index = self.device_combo.currentData()
        
        self.recorder = AudioRecorder(
            sample_rate=self.sample_rate,
            chunk_size=self.chunk_size,
            device_index=device_index
        )
        self.recorder.data_available.connect(self.update_waveform)
        self.recorder.level_updated.connect(self.update_level_meter)
        
        self.recorder.start_recording()
        self.record_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.play_btn.setEnabled(False)
        self.status_bar.showMessage("正在录制...")
        
    def stop_recording(self):
        """停止录制音频"""
        self.recorder.stop_recording()
        self.audio_data = self.recorder.get_audio_data()
        self.processed_data = None
        
        # 显示录制的音频
        if self.audio_data is not None:
            self.waveform_widget.plot_waveform(self.audio_data, self.sample_rate)
            
            # 启用相关按钮
            self.play_btn.setEnabled(True)
            self.analyze_btn.setEnabled(True)
            self.apply_filter_btn.setEnabled(True)
            self.apply_effect_btn.setEnabled(True)
            self.apply_noise_reduction_btn.setEnabled(True)
            self.extract_features_btn.setEnabled(True)
            self.train_model_btn.setEnabled(True)
        
        self.record_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.status_bar.showMessage("录制完成")
        
    def update_waveform(self, data):
        """更新波形显示"""
        self.latest_data = data
        
    def update_level_meter(self, level):
        """更新电平表"""
        self.level_meter.setValue(int(level * 100))
        
    def update_display(self):
        """更新显示"""
        if hasattr(self, 'latest_data'):
            time_axis = np.linspace(0, len(self.latest_data) / self.sample_rate, len(self.latest_data))
            self.waveform_widget.plot(time_axis, self.latest_data, clear=True)
            
    def start_playback(self):
        """开始播放音频"""
        if self.player and self.player.playing:
            return
            
        # 确定要播放的数据
        data_to_play = self.processed_data if self.processed_data is not None else self.audio_data
        
        if data_to_play is None:
            return
            
        self.player = AudioPlayer(
            sample_rate=self.sample_rate,
            chunk_size=self.chunk_size
        )
        self.player.load_audio(data_to_play)
        self.player.playback_finished.connect(self.on_playback_finished)
        self.player.playback_position.connect(self.on_playback_position)
        
        self.player.start_playback()
        self.play_btn.setEnabled(False)
        self.stop_play_btn.setEnabled(True)
        self.status_bar.showMessage("正在播放...")
        
    def stop_playback(self):
        """停止播放音频"""
        if self.player:
            self.player.stop_playback()
            
    def on_playback_finished(self):
        """播放完成回调"""
        self.play_btn.setEnabled(True)
        self.stop_play_btn.setEnabled(False)
        self.status_bar.showMessage("播放完成")
        
    def on_playback_position(self, position):
        """播放位置更新回调"""
        # 可以在这里实现播放进度显示
        pass
        
    def analyze_audio(self):
        """分析音频"""
        if self.audio_data is None:
            return
            
        self.status_bar.showMessage("正在分析音频...")
        
        # 确定分析类型
        analysis_type = self.analysis_type_combo.currentText()
        analysis_types = []
        
        if analysis_type == "频谱" or analysis_type == "全部":
            analysis_types.append('spectrum')
        if analysis_type == "MFCC" or analysis_type == "全部":
            analysis_types.append('mfcc')
        if analysis_type == "色度特征" or analysis_type == "全部":
            analysis_types.append('chroma')
        if analysis_type == "节奏分析" or analysis_type == "全部":
            analysis_types.append('tempogram')
        if analysis_type == "音高检测" or analysis_type == "全部":
            analysis_types.append('pitch')
        if analysis_type == "节拍检测" or analysis_type == "全部":
            analysis_types.append('beat')
            
        # 创建分析线程
        self.analyzer = AudioAnalyzer(self.audio_data, self.sample_rate, analysis_types)
        self.analyzer.progress_updated.connect(self.on_analysis_progress)
        self.analyzer.analysis_complete.connect(self.on_analysis_complete)
        self.analyzer.start()
        
    def on_analysis_progress(self, progress):
        """分析进度更新"""
        self.status_bar.showMessage(f"分析中... {progress}%")
        
    def on_analysis_complete(self, result):
        """分析完成回调"""
        self.status_bar.showMessage("分析完成")
        
        # 显示频谱
        if 'spectrum' in result:
            freqs, power = result['spectrum']['freqs'], result['spectrum']['power']
            self.spectrum_widget.plot_spectrum(freqs, power)
            
        # 显示频谱图
        self.spectrogram_widget.plot_spectrogram(
            self.audio_data, 
            self.sample_rate
        )
        
        # 显示分析结果
        results_text = "音频分析结果:\n\n"
        
        if 'stats' in result:
            stats = result['stats']
            results_text += f"RMS能量: {stats['rms']:.4f}\n"
            results_text += f"零交叉率: {stats['zero_crossings']:.4f}\n"
            results_text += f"频谱中心: {stats['spectral_centroid']:.2f} Hz\n"
            results_text += f"频谱滚降: {stats['spectral_rolloff']:.2f} Hz\n"
            results_text += f"频谱带宽: {stats['spectral_bandwidth']:.2f} Hz\n"
            results_text += f"频谱平坦度: {stats['spectral_flatness']:.4f}\n"
            results_text += f"频谱对比度: {stats['spectral_contrast']:.4f}\n\n"
            
        if 'mfcc' in result:
            results_text += f"MFCC特征维度: {result['mfcc'].shape}\n"
            
        if 'chroma' in result:
            results_text += f"色度特征维度: {result['chroma'].shape}\n"
            
        if 'tempogram' in result:
            results_text += f"节奏特征维度: {result['tempogram'].shape}\n"
            
        if 'pitch' in result:
            pitches = result['pitch']['pitches']
            confidences = result['pitch']['confidences']
            avg_pitch = np.mean(pitches[confidences > 0.8]) if np.any(confidences > 0.8) else 0
            results_text += f"平均音高: {avg_pitch:.2f} MIDI\n"
            
        if 'beats' in result:
            results_text += f"检测到的BPM: {result['beats']['tempo']:.2f}\n"
            results_text += f"检测到的节拍数: {len(result['beats']['beat_times'])}\n"
            
        self.analysis_results_text.setPlainText(results_text)
        
    def apply_filter(self):
        """应用滤波器"""
        if self.audio_data is None:
            return
            
        filter_type = self.filter_type_combo.currentText()
        cutoff = self.cutoff_freq_spin.value()
        high_cut = self.high_cut_spin.value()
        gain = self.eq_gain_slider.value()
        
        # 转换为浮点格式用于处理
        audio_float = self.audio_data.astype(np.float32) / 32768.0
        
        if filter_type == "无":
            self.processed_data = self.audio_data
        elif filter_type == "高通":
            filtered = AudioFilter.apply_highpass(audio_float, self.sample_rate, cutoff)
            self.processed_data = (filtered * 32768.0).astype(np.int16)
        elif filter_type == "低通":
            filtered = AudioFilter.apply_lowpass(audio_float, self.sample_rate, cutoff)
            self.processed_data = (filtered * 32768.0).ast(np.int16)
        elif filter_type == "带通":
            filtered = AudioFilter.apply_bandpass(audio_float, self.sample_rate, cutoff, high_cut)
            self.processed_data = (filtered * 32768.0).astype(np.int16)
        elif filter_type == "带阻":
            filtered = AudioFilter.apply_bandstop(audio_float, self.sample_rate, cutoff, high_cut)
            self.processed_data = (filtered * 32768.0).astype(np.int16)
        elif filter_type == "均衡器":
            filtered = AudioFilter.apply_eq(audio_float, self.sample_rate, cutoff, gain/10.0)
            self.processed_data = (filtered * 32768.0).astype(np.int16)
        elif filter_type == "高架":
            filtered = AudioFilter.apply_high_shelf(audio_float, self.sample_rate, cutoff, gain)
            self.processed_data = (filtered * 32768.0).astype(np.int16)
        elif filter_type == "低架":
            filtered = AudioFilter.apply_low_shelf(audio_float, self.sample_rate, cutoff, gain)
            self.processed_data = (filtered * 32768.0).astype(np.int16)
            
        # 显示处理后的波形
        self.waveform_widget.plot_comparison(self.audio_data, self.processed_data, self.sample_rate)
        
        # 显示处理后的频谱
        analyzer = AudioAnalyzer(self.processed_data, self.sample_rate, ['spectrum'])
        analyzer.analysis_complete.connect(self.on_filter_analysis_complete)
        analyzer.start()
        
        self.status_bar.showMessage(f"已应用{filter_type}滤波器")
        
    def on_filter_analysis_complete(self, result):
        """滤波器分析完成回调"""
        if 'spectrum' in result:
            freqs, power = result['spectrum']['freqs'], result['spectrum']['power']
            
            # 获取原始音频的频谱用于比较
            analyzer = AudioAnalyzer(self.audio_data, self.sample_rate, ['spectrum'])
            analyzer.analysis_complete.connect(
                lambda orig_result: self.show_spectrum_comparison(orig_result, result)
            )
            analyzer.start()
            
    def show_spectrum_comparison(self, orig_result, proc_result):
        """显示频谱对比"""
        if 'spectrum' in orig_result and 'spectrum' in proc_result:
            orig_freqs, orig_power = orig_result['spectrum']['freqs'], orig_result['spectrum']['power']
            proc_freqs, proc_power = proc_result['spectrum']['freqs'], proc_result['spectrum']['power']
            
            self.spectrum_widget.plot_comparison(orig_freqs, orig_power, proc_freqs, proc_power)
            
    def apply_effect(self):
        """应用音频效果"""
        if self.audio_data is None:
            return
            
        effect_type = self.effect_type_combo.currentText()
        decay = self.reverb_decay_slider.value() / 100.0
        delay_time = self.delay_time_slider.value() / 100.0
        
        # 转换为浮点格式用于处理
        audio_float = self.audio_data.astype(np.float32) / 32768.0
        
        if effect_type == "无":
            self.processed_data = self.audio_data
        elif effect_type == "混响":
            effected = AudioEffects.apply_reverb(audio_float, self.sample_rate, decay)
            self.processed_data = (effected * 32768.0).astype(np.int16)
        elif effect_type == "延迟":
            effected = AudioEffects.apply_delay(audio_float, self.sample_rate, delay_time)
            self.processed_data = (effected * 32768.0).astype(np.int16)
        elif effect_type == "失真":
            effected = AudioEffects.apply_distortion(audio_float)
            self.processed_data = (effected * 32768.0).astype(np.int16)
        elif effect_type == "压缩器":
            effected = AudioEffects.apply_compressor(audio_float, self.sample_rate)
            self.processed_data = (effected * 32768.0).astype(np.int16)
        elif effect_type == "颤音":
            effected = AudioEffects.apply_tremolo(audio_float, self.sample_rate)
            self.processed_data = (effected * 32768.0).astype(np.int16)
        elif effect_type == "合唱":
            effected = AudioEffects.apply_chorus(audio_float, self.sample_rate)
            self.processed_data = (effected * 32768.0).astype(np.int16)
        elif effect_type == "相位":
            effected = AudioEffects.apply_phaser(audio_float, self.sample_rate)
            self.processed_data = (effected * 32768.0).astype(np.int16)
            
        # 显示处理后的波形
        self.waveform_widget.plot_comparison(self.audio_data, self.processed_data, self.sample_rate)
        self.status_bar.showMessage(f"已应用{effect_type}效果")
        
    def apply_noise_reduction(self):
        """应用噪声消除"""
        if self.audio_data is None:
            return
            
        reduction_type = self.noise_reduction_combo.currentText()
        noise_start = self.noise_start_spin.value()
        noise_end = self.noise_end_spin.value()
        
        # 转换为浮点格式用于处理
        audio_float = self.audio_data.astype(np.float32) / 32768.0
        
        if reduction_type == "无":
            self.processed_data = self.audio_data
        elif reduction_type == "谱减法":
            reduced = NoiseReducer.reduce_noise_spectral_subtraction(audio_float, self.sample_rate)
            self.processed_data = (reduced * 32768.0).astype(np.int16)
        elif reduction_type == "NoiseReduce":
            reduced = NoiseReducer.reduce_noise(audio_float, self.sample_rate, noise_start, noise_end)
            self.processed_data = (reduced * 32768.0).astype(np.int16)
        elif reduction_type == "小波变换":
            reduced = NoiseReducer.reduce_noise_wavelet(audio_float)
            self.processed_data = (reduced * 32768.0).astype(np.int16)
            
        # 显示处理后的波形
        self.waveform_widget.plot_comparison(self.audio_data, self.processed_data, self.sample_rate)
        self.status_bar.showMessage(f"已应用{reduction_type}降噪")
        
    def extract_features(self):
        """提取音频特征"""
        if self.audio_data is None:
            return
            
        # 转换为浮点格式用于处理
        audio_float = self.audio_data.astype(np.float32) / 32768.0
        
        # 提取特征
        features = self.ml_processor.extract_features(audio_float, self.sample_rate)
        
        # 显示特征
        features_text = "提取的音频特征:\n\n"
        for i, feature in enumerate(features):
            features_text += f"特征 {i+1}: {feature:.6f}\n"
            
        self.features_text.setPlainText(features_text)
        self.status_bar.showMessage("特征提取完成")
        
    def train_model(self):
        """训练机器学习模型"""
        # 这里只是示例，实际应用中需要多个音频样本
        QMessageBox.information(self, "信息", "此功能需要多个音频样本进行训练。在实际应用中，您需要先收集多个样本。")
        
    def open_audio(self):
        """打开音频文件"""
        filename, _ = QFileDialog.getOpenFileName(
            self, "打开音频文件", "", "音频文件 (*.wav *.mp3 *.flac *.ogg)"
        )
        
        if filename:
            try:
                # 使用librosa加载音频文件，保持原始采样率
                self.audio_data, self.sample_rate = librosa.load(filename, sr=None)
                
                # 转换为16位整数格式
                self.audio_data = (self.audio_data * 32768.0).astype(np.int16)
                
                self.processed_data = None
                
                # 显示波形
                self.waveform_widget.plot_waveform(self.audio_data, self.sample_rate)
                
                # 启用相关按钮
                self.play_btn.setEnabled(True)
                self.analyze_btn.setEnabled(True)
                self.apply_filter_btn.setEnabled(True)
                self.apply_effect_btn.setEnabled(True)
                self.apply_noise_reduction_btn.setEnabled(True)
                self.extract_features_btn.setEnabled(True)
                self.train_model_btn.setEnabled(True)
                
                self.status_bar.showMessage(f"已加载: {filename}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"无法加载音频文件: {str(e)}")
                
    def save_audio(self):
        """保存音频到文件"""
        if self.audio_data is None:
            return
            
        data_to_save = self.processed_data if self.processed_data is not None else self.audio_data
            
        filename, _ = QFileDialog.getSaveFileName(
            self, "保存音频文件", "", "WAV文件 (*.wav)"
        )
        
        if filename:
            try:
                # 转换为浮点格式
                audio_float = data_to_save.astype(np.float32) / 32768.0
                
                # 使用soundfile保存文件
                sf.write(filename, audio_float, self.sample_rate)
                
                self.status_bar.showMessage(f"音频已保存到: {filename}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"无法保存音频文件: {str(e)}")
                
    def batch_process(self):
        """批量处理音频文件"""
        QMessageBox.information(self, "信息", "批量处理功能将在未来版本中实现")
        
    def show_about(self):
        """显示关于对话框"""
        about_text = """
        <h2>高级音频处理与分析工具</h2>
        <p>基于PyQt6、PyAudio和Librosa的强大音频工具</p>
        <p>功能包括:</p>
        <ul>
            <li>音频录制和播放</li>
            <li>实时波形和频谱显示</li>
            <li>多种滤波器（高通、低通、带通、带阻、均衡器、高架、低架）</li>
            <li>音频效果（混响、延迟、失真、压缩器、颤音、合唱、相位）</li>
            <li>噪声消除（谱减法、NoiseReduce、小波变换）</li>
            <li>高级音频分析（频谱、MFCC、色度特征、节奏分析、音高检测、节拍检测）</li>
            <li>机器学习特征提取</li>
        </ul>
        <p>版本: 3.0 (PyQt6版本)</p>
        """
        QMessageBox.about(self, "关于", about_text)
        
    def closeEvent(self, event):
        """应用程序关闭事件"""
        if self.recorder and self.recorder.recording:
            self.recorder.stop_recording()
        if self.player and self.player.playing:
            self.player.stop_playback()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("高级音频处理与分析工具")
    
    # 设置应用程序样式
    app.setStyle("Fusion")
    
    window = AudioRecorderApp()
    window.show()
    
    sys.exit(app.exec())