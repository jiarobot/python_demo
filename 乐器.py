import sys
import os
import numpy as np
import json
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QSlider, QLabel, 
                             QComboBox, QGroupBox, QTabWidget, QMessageBox,
                             QFileDialog, QProgressBar, QSpinBox, QDoubleSpinBox,
                             QGridLayout, QCheckBox, QTextEdit, QListWidget, QListWidgetItem)
from PyQt5.QtCore import QPointF, QTimer, Qt, QThread, pyqtSignal, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QFont, QPalette, QColor, QPainter, QLinearGradient, QPen
import pyaudio
import wave
import math
from scipy import signal
import threading
import time

class AudioRecorderThread(QThread):
    """录音线程"""
    update_signal = pyqtSignal(int)  # 更新录音进度的信号
    finished_signal = pyqtSignal(str)  # 录音完成信号
    
    def __init__(self, filename, duration=10, sample_rate=44100, channels=1):
        super().__init__()
        self.filename = filename
        self.duration = duration
        self.sample_rate = sample_rate
        self.channels = channels
        self.is_recording = False
        self.frames = []
        
    def run(self):
        self.is_recording = True
        audio = pyaudio.PyAudio()
        
        # 设置音频流参数
        stream = audio.open(
            format=pyaudio.paInt16,
            channels=self.channels,
            rate=self.sample_rate,
            input=True,
            frames_per_buffer=1024
        )
        
        # 开始录音
        self.frames = []
        for i in range(0, int(self.sample_rate / 1024 * self.duration)):
            if not self.is_recording:
                break
            data = stream.read(1024)
            self.frames.append(data)
            self.update_signal.emit(int(i / (self.sample_rate / 1024 * self.duration) * 100))
        
        # 停止录音
        stream.stop_stream()
        stream.close()
        audio.terminate()
        
        # 保存录音文件
        if self.is_recording:  # 只有正常结束才保存
            wf = wave.open(self.filename, 'wb')
            wf.setnchannels(self.channels)
            wf.setsampwidth(audio.get_sample_size(pyaudio.paInt16))
            wf.setframerate(self.sample_rate)
            wf.writeframes(b''.join(self.frames))
            wf.close()
            self.finished_signal.emit(self.filename)
    
    def stop(self):
        self.is_recording = False

class EffectProcessor:
    """音效处理器"""
    
    @staticmethod
    def reverb(audio_data, sample_rate, room_size=0.5, damping=0.5, wet_level=0.3):
        """添加混响效果"""
        # 将音频数据转换为numpy数组
        audio_array = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32)
        
        # 创建混响冲激响应
        length = int(sample_rate * room_size)
        impulse = np.zeros(length)
        
        # 生成衰减的噪声作为混响
        for i in range(length):
            impulse[i] = (1 - i/length) * np.random.normal(0, 1) * np.exp(-i/(sample_rate * damping))
        
        # 应用卷积
        reverb_signal = np.convolve(audio_array, impulse, mode='same')
        
        # 混合原始信号和混响信号
        wet = reverb_signal * wet_level
        dry = audio_array * (1 - wet_level)
        result = dry + wet
        
        # 归一化并转换回int16
        result = result / np.max(np.abs(result)) * 32767
        return result.astype(np.int16).tobytes()
    
    @staticmethod
    def delay(audio_data, sample_rate, delay_time=0.3, feedback=0.5, wet_level=0.5):
        """添加延迟效果"""
        audio_array = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32)
        delay_samples = int(delay_time * sample_rate)
        
        # 创建延迟缓冲区
        delayed = np.zeros(len(audio_array) + delay_samples)
        delayed[:len(audio_array)] = audio_array
        
        # 应用反馈
        for i in range(1, 5):  # 4次反馈
            start = i * delay_samples
            end = start + len(audio_array)
            if end < len(delayed):
                delayed[start:end] += audio_array * (feedback ** i)
        
        # 混合原始信号和延迟信号
        wet = delayed[:len(audio_array)] * wet_level
        dry = audio_array * (1 - wet_level)
        result = dry + wet
        
        # 归一化并转换回int16
        result = result / np.max(np.abs(result)) * 32767
        return result.astype(np.int16).tobytes()
    
    @staticmethod
    def distortion(audio_data, gain=2.0, level=0.5):
        """添加失真效果"""
        audio_array = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32)
        
        # 应用软削波失真
        distorted = np.tanh(audio_array / 32767 * gain) * 32767 * level
        
        # 混合原始信号和失真信号
        result = audio_array * (1 - level) + distorted * level
        return result.astype(np.int16).tobytes()

class ToneGenerator:
    """音调生成器"""
    
    def __init__(self, sample_rate=44100, amplitude=0.5):
        self.sample_rate = sample_rate
        self.amplitude = amplitude
        self.effects = {
            'reverb': {'enabled': False, 'room_size': 0.5, 'damping': 0.5, 'wet_level': 0.3},
            'delay': {'enabled': False, 'delay_time': 0.3, 'feedback': 0.5, 'wet_level': 0.5},
            'distortion': {'enabled': False, 'gain': 2.0, 'level': 0.5}
        }
        
    def generate_tone(self, frequency, duration, wave_type='sine', attack=0.01, decay=0.1):
        """生成指定频率和时长的音调"""
        t = np.linspace(0, duration, int(self.sample_rate * duration), False)
        
        # 根据波形类型生成不同的波形
        if wave_type == 'sine':
            wave_data = np.sin(2 * np.pi * frequency * t)
        elif wave_type == 'square':
            wave_data = signal.square(2 * np.pi * frequency * t)
        elif wave_type == 'sawtooth':
            wave_data = signal.sawtooth(2 * np.pi * frequency * t)
        elif wave_type == 'triangle':
            wave_data = signal.sawtooth(2 * np.pi * frequency * t, width=0.5)
        elif wave_type == 'noise':
            wave_data = np.random.normal(0, 1, len(t))
        else:
            wave_data = np.sin(2 * np.pi * frequency * t)
        
        # 应用包络（ADSR简化版）
        envelope = self._apply_envelope(len(wave_data), attack, decay)
        wave_data = wave_data * envelope
        
        # 归一化并应用振幅
        wave_data = wave_data * self.amplitude
        wave_data = (wave_data * 32767).astype(np.int16)
        
        # 转换为字节
        audio_data = wave_data.tobytes()
        
        # 应用音效
        if self.effects['reverb']['enabled']:
            audio_data = EffectProcessor.reverb(audio_data, self.sample_rate,
                                              self.effects['reverb']['room_size'],
                                              self.effects['reverb']['damping'],
                                              self.effects['reverb']['wet_level'])
        
        if self.effects['delay']['enabled']:
            audio_data = EffectProcessor.delay(audio_data, self.sample_rate,
                                             self.effects['delay']['delay_time'],
                                             self.effects['delay']['feedback'],
                                             self.effects['delay']['wet_level'])
        
        if self.effects['distortion']['enabled']:
            audio_data = EffectProcessor.distortion(audio_data,
                                                  self.effects['distortion']['gain'],
                                                  self.effects['distortion']['level'])
        
        return audio_data
    
    def _apply_envelope(self, length, attack, decay):
        """应用ADSR包络（简化版）"""
        envelope = np.ones(length)
        attack_len = int(length * attack)
        decay_len = int(length * decay)
        
        # 起音阶段
        if attack_len > 0:
            envelope[:attack_len] = np.linspace(0, 1, attack_len)
        
        # 衰减阶段
        if decay_len > 0:
            sustain_level = 0.7
            envelope[attack_len:attack_len+decay_len] = np.linspace(1, sustain_level, decay_len)
            envelope[attack_len+decay_len:] = sustain_level
        
        return envelope
    
    def set_effect(self, effect_name, enabled, **params):
        """设置音效参数"""
        if effect_name in self.effects:
            self.effects[effect_name]['enabled'] = enabled
            for key, value in params.items():
                if key in self.effects[effect_name]:
                    self.effects[effect_name][key] = value

class Instrument:
    """基础乐器类"""
    
    def __init__(self, name, sample_rate=44100):
        self.name = name
        self.sample_rate = sample_rate
        self.generator = ToneGenerator(sample_rate)
        self.notes = {}  # 音符频率映射表
        
    def load_scale(self, base_freq=440.0):
        """加载标准音阶"""
        # 基于A4=440Hz的十二平均律
        self.notes = {
            'C': base_freq * (2 ** (-9/12)),
            'C#': base_freq * (2 ** (-8/12)),
            'D': base_freq * (2 ** (-7/12)),
            'D#': base_freq * (2 ** (-6/12)),
            'E': base_freq * (2 ** (-5/12)),
            'F': base_freq * (2 ** (-4/12)),
            'F#': base_freq * (2 ** (-3/12)),
            'G': base_freq * (2 ** (-2/12)),
            'G#': base_freq * (2 ** (-1/12)),
            'A': base_freq,
            'A#': base_freq * (2 ** (1/12)),
            'B': base_freq * (2 ** (2/12))
        }
    
    def play_note(self, note, duration=1.0, octave=4, wave_type='sine'):
        """播放指定音符"""
        if not self.notes:
            self.load_scale()
        
        if note in self.notes:
            freq = self.notes[note] * (2 ** (octave - 4))
            return self.generator.generate_tone(freq, duration, wave_type)
        return None

class Piano(Instrument):
    """钢琴类"""
    
    def __init__(self, sample_rate=44100):
        super().__init__("Piano", sample_rate)
        self.load_scale()
    
    def play_note(self, note, duration=1.0, octave=4, wave_type='sine'):
        """钢琴音色 - 使用复合波形"""
        if note in self.notes:
            freq = self.notes[note] * (2 ** (octave - 4))
            
            # 钢琴音色包含基波和多个谐波
            t = np.linspace(0, duration, int(self.sample_rate * duration), False)
            
            # 基波
            fundamental = np.sin(2 * np.pi * freq * t)
            
            # 谐波
            harmonic1 = 0.6 * np.sin(2 * np.pi * 2 * freq * t)  # 二次谐波
            harmonic2 = 0.3 * np.sin(2 * np.pi * 3 * freq * t)  # 三次谐波
            harmonic3 = 0.1 * np.sin(2 * np.pi * 4 * freq * t)  # 四次谐波
            
            # 组合波形
            wave_data = fundamental + harmonic1 + harmonic2 + harmonic3
            
            # 应用包络
            envelope = self.generator._apply_envelope(len(wave_data), 0.01, 0.3)
            wave_data = wave_data * envelope
            
            # 归一化并转换为字节
            wave_data = wave_data / np.max(np.abs(wave_data)) * 0.5
            wave_data = (wave_data * 32767).astype(np.int16)
            
            audio_data = wave_data.tobytes()
            
            # 应用音效
            if self.generator.effects['reverb']['enabled']:
                audio_data = EffectProcessor.reverb(audio_data, self.sample_rate,
                                                  self.generator.effects['reverb']['room_size'],
                                                  self.generator.effects['reverb']['damping'],
                                                  self.generator.effects['reverb']['wet_level'])
            
            return audio_data
        return None

class Guitar(Instrument):
    """吉他类"""
    
    def __init__(self, sample_rate=44100):
        super().__init__("Guitar", sample_rate)
        self.load_scale()
    
    def play_note(self, note, duration=1.0, octave=4, wave_type='sine'):
        """吉他音色 - 使用锯齿波和滤波器"""
        if note in self.notes:
            freq = self.notes[note] * (2 ** (octave - 4))
            
            # 生成锯齿波
            t = np.linspace(0, duration, int(self.sample_rate * duration), False)
            wave_data = signal.sawtooth(2 * np.pi * freq * t)
            
            # 应用低通滤波器模拟吉他音色
            b, a = signal.butter(4, 2000/(self.sample_rate/2), btype='low')
            wave_data = signal.lfilter(b, a, wave_data)
            
            # 应用包络
            envelope = self.generator._apply_envelope(len(wave_data), 0.02, 0.2)
            wave_data = wave_data * envelope
            
            # 归一化并转换为字节
            wave_data = wave_data / np.max(np.abs(wave_data)) * 0.5
            wave_data = (wave_data * 32767).astype(np.int16)
            
            audio_data = wave_data.tobytes()
            
            # 应用音效
            if self.generator.effects['reverb']['enabled']:
                audio_data = EffectProcessor.reverb(audio_data, self.sample_rate,
                                                  self.generator.effects['reverb']['room_size'],
                                                  self.generator.effects['reverb']['damping'],
                                                  self.generator.effects['reverb']['wet_level'])
            
            return audio_data
        return None

class Violin(Instrument):
    """小提琴类"""
    
    def __init__(self, sample_rate=44100):
        super().__init__("Violin", sample_rate)
        self.load_scale()
    
    def play_note(self, note, duration=1.0, octave=4, wave_type='sine'):
        """小提琴音色 - 使用复杂的谐波结构"""
        if note in self.notes:
            freq = self.notes[note] * (2 ** (octave - 4))
            
            t = np.linspace(0, duration, int(self.sample_rate * duration), False)
            
            # 小提琴音色包含丰富的谐波
            fundamental = np.sin(2 * np.pi * freq * t)
            harmonic1 = 0.8 * np.sin(2 * np.pi * 2 * freq * t)
            harmonic2 = 0.6 * np.sin(2 * np.pi * 3 * freq * t)
            harmonic3 = 0.4 * np.sin(2 * np.pi * 4 * freq * t)
            harmonic4 = 0.2 * np.sin(2 * np.pi * 5 * freq * t)
            
            # 组合波形
            wave_data = fundamental + harmonic1 + harmonic2 + harmonic3 + harmonic4
            
            # 应用缓慢起音的包络
            envelope = self.generator._apply_envelope(len(wave_data), 0.1, 0.3)
            wave_data = wave_data * envelope
            
            # 添加颤音效果
            vibrato = 0.005 * np.sin(2 * np.pi * 5 * t)  # 5Hz颤音
            wave_data = wave_data * (1 + vibrato)
            
            # 归一化并转换为字节
            wave_data = wave_data / np.max(np.abs(wave_data)) * 0.5
            wave_data = (wave_data * 32767).astype(np.int16)
            
            audio_data = wave_data.tobytes()
            
            # 应用音效
            if self.generator.effects['reverb']['enabled']:
                audio_data = EffectProcessor.reverb(audio_data, self.sample_rate,
                                                  self.generator.effects['reverb']['room_size'],
                                                  self.generator.effects['reverb']['damping'],
                                                  self.generator.effects['reverb']['wet_level'])
            
            return audio_data
        return None

class Bass(Instrument):
    """贝斯类"""
    
    def __init__(self, sample_rate=44100):
        super().__init__("Bass", sample_rate)
        self.load_scale()
    
    def play_note(self, note, duration=1.0, octave=2, wave_type='sine'):
        """贝斯音色 - 低音增强"""
        if note in self.notes:
            freq = self.notes[note] * (2 ** (octave - 4))
            
            t = np.linspace(0, duration, int(self.sample_rate * duration), False)
            
            # 使用锯齿波和方波的混合
            sawtooth_wave = signal.sawtooth(2 * np.pi * freq * t)
            square_wave = signal.square(2 * np.pi * freq * t)
            
            # 混合波形
            wave_data = 0.7 * sawtooth_wave + 0.3 * square_wave
            
            # 应用包络
            envelope = self.generator._apply_envelope(len(wave_data), 0.05, 0.2)
            wave_data = wave_data * envelope
            
            # 归一化并转换为字节
            wave_data = wave_data / np.max(np.abs(wave_data)) * 0.5
            wave_data = (wave_data * 32767).astype(np.int16)
            
            audio_data = wave_data.tobytes()
            
            # 应用音效
            if self.generator.effects['distortion']['enabled']:
                audio_data = EffectProcessor.distortion(audio_data,
                                                      self.generator.effects['distortion']['gain'],
                                                      self.generator.effects['distortion']['level'])
            
            return audio_data
        return None

class Synthesizer(Instrument):
    """合成器类"""
    
    def __init__(self, sample_rate=44100):
        super().__init__("Synthesizer", sample_rate)
        self.load_scale()
        self.oscillators = 2  # 振荡器数量
        self.detune = 0.1     # 失谐量
    
    def play_note(self, note, duration=1.0, octave=4, wave_type='sine'):
        """合成器音色 - 可配置的振荡器"""
        if note in self.notes:
            freq = self.notes[note] * (2 ** (octave - 4))
            
            t = np.linspace(0, duration, int(self.sample_rate * duration), False)
            
            # 多个振荡器
            wave_data = np.zeros(len(t))
            
            for i in range(self.oscillators):
                # 每个振荡器有轻微失谐
                osc_freq = freq * (1 + (i - (self.oscillators-1)/2) * self.detune)
                
                if wave_type == 'sine':
                    oscillator = np.sin(2 * np.pi * osc_freq * t)
                elif wave_type == 'square':
                    oscillator = signal.square(2 * np.pi * osc_freq * t)
                elif wave_type == 'sawtooth':
                    oscillator = signal.sawtooth(2 * np.pi * osc_freq * t)
                elif wave_type == 'triangle':
                    oscillator = signal.sawtooth(2 * np.pi * osc_freq * t, width=0.5)
                elif wave_type == 'noise':
                    oscillator = np.random.normal(0, 1, len(t))
                else:
                    oscillator = np.sin(2 * np.pi * osc_freq * t)
                
                # 混合振荡器
                wave_data += oscillator / self.oscillators
            
            # 应用包络
            envelope = self.generator._apply_envelope(len(wave_data), 0.01, 0.3)
            wave_data = wave_data * envelope
            
            # 归一化并转换为字节
            wave_data = wave_data / np.max(np.abs(wave_data)) * 0.5
            wave_data = (wave_data * 32767).astype(np.int16)
            
            audio_data = wave_data.tobytes()
            
            # 应用音效
            for effect_name, effect_params in self.generator.effects.items():
                if effect_params['enabled']:
                    if effect_name == 'reverb':
                        audio_data = EffectProcessor.reverb(audio_data, self.sample_rate,
                                                          effect_params['room_size'],
                                                          effect_params['damping'],
                                                          effect_params['wet_level'])
                    elif effect_name == 'delay':
                        audio_data = EffectProcessor.delay(audio_data, self.sample_rate,
                                                         effect_params['delay_time'],
                                                         effect_params['feedback'],
                                                         effect_params['wet_level'])
                    elif effect_name == 'distortion':
                        audio_data = EffectProcessor.distortion(audio_data,
                                                              effect_params['gain'],
                                                              effect_params['level'])
            
            return audio_data
        return None

class Drum(Instrument):
    """鼓类"""
    
    def __init__(self, sample_rate=44100):
        super().__init__("Drum", sample_rate)
    
    def play_note(self, note, duration=0.5, octave=4):
        """鼓声 - 使用噪声和包络"""
        # 生成噪声
        t = np.linspace(0, duration, int(self.sample_rate * duration), False)
        noise = np.random.normal(0, 1, len(t))
        
        # 应用带通滤波器
        low_freq = 50 + octave * 50
        high_freq = 200 + octave * 100
        b, a = signal.butter(4, [low_freq/(self.sample_rate/2), high_freq/(self.sample_rate/2)], btype='band')
        wave_data = signal.lfilter(b, a, noise)
        
        # 应用快速衰减包络
        envelope = np.exp(-t * 10)  # 指数衰减
        wave_data = wave_data * envelope
        
        # 归一化并转换为字节
        wave_data = wave_data / np.max(np.abs(wave_data)) * 0.7
        wave_data = (wave_data * 32767).astype(np.int16)
        
        return wave_data.tobytes()

class AudioPlayer:
    """音频播放器"""
    
    def __init__(self):
        self.audio = pyaudio.PyAudio()
        self.stream = None
        self.is_playing = False
    
    def play_audio(self, audio_data, sample_rate=44100):
        """播放音频数据"""
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        
        self.stream = self.audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=sample_rate,
            output=True
        )
        
        self.is_playing = True
        self.stream.write(audio_data)
        self.is_playing = False
    
    def stop(self):
        """停止播放"""
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None
            self.is_playing = False
    
    def __del__(self):
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        self.audio.terminate()

class VisualizerWidget(QWidget):
    """音频可视化组件"""
    
    def __init__(self):
        super().__init__()
        self.setMinimumHeight(100)
        self.setMinimumWidth(300)
        self.audio_data = None
        self.timer = QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.start(50)  # 20 FPS
    
    def set_audio_data(self, audio_data):
        """设置音频数据用于可视化"""
        if audio_data:
            self.audio_data = np.frombuffer(audio_data, dtype=np.int16)
        else:
            self.audio_data = None
    
    def paintEvent(self, event):
        """绘制音频波形"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 绘制背景
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0, QColor(30, 30, 50))
        gradient.setColorAt(1, QColor(10, 10, 20))
        painter.fillRect(self.rect(), gradient)
        
        if self.audio_data is not None and len(self.audio_data) > 0:
            # 绘制波形
            painter.setPen(QPen(QColor(0, 200, 255), 2))
            
            # 简化波形数据
            step = max(1, len(self.audio_data) // 500)  # 最多500个点
            points = []
            
            for i in range(0, len(self.audio_data), step):
                x = (i / len(self.audio_data)) * self.width()
                y = (self.audio_data[i] / 32768) * (self.height() / 2) + (self.height() / 2)
                points.append((x, y))
            
            # 绘制波形线
            for i in range(len(points) - 1):
                painter.drawLine(QPointF(points[i][0], points[i][1]), QPointF(points[i+1][0], points[i+1][1]))
            
            # 绘制频谱（简化版）
            if len(self.audio_data) > 1024:
                fft_data = np.abs(np.fft.rfft(self.audio_data[:1024]))
                fft_data = np.log(fft_data + 1)  # 对数缩放
                
                painter.setPen(QPen(QColor(255, 100, 0), 1))
                
                for i in range(1, min(100, len(fft_data))):
                    x1 = (i-1) / 100 * self.width()
                    x2 = i / 100 * self.width()
                    y1 = self.height() - (fft_data[i-1] / np.max(fft_data)) * (self.height() / 3)
                    y2 = self.height() - (fft_data[i] / np.max(fft_data)) * (self.height() / 3)
                    
                    painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))

class EffectsPanel(QWidget):
    """音效控制面板"""
    
    def __init__(self, instrument):
        super().__init__()
        self.instrument = instrument
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 混响效果
        reverb_group = QGroupBox("混响")
        reverb_layout = QVBoxLayout()
        
        self.reverb_enable = QCheckBox("启用混响")
        self.reverb_enable.toggled.connect(self.toggle_reverb)
        reverb_layout.addWidget(self.reverb_enable)
        
        room_layout = QHBoxLayout()
        room_layout.addWidget(QLabel("房间大小:"))
        self.room_slider = QSlider(Qt.Horizontal)
        self.room_slider.setRange(1, 100)
        self.room_slider.setValue(50)
        self.room_slider.valueChanged.connect(self.update_reverb)
        room_layout.addWidget(self.room_slider)
        reverb_layout.addLayout(room_layout)
        
        damping_layout = QHBoxLayout()
        damping_layout.addWidget(QLabel("阻尼:"))
        self.damping_slider = QSlider(Qt.Horizontal)
        self.damping_slider.setRange(1, 100)
        self.damping_slider.setValue(50)
        self.damping_slider.valueChanged.connect(self.update_reverb)
        damping_layout.addWidget(self.damping_slider)
        reverb_layout.addLayout(damping_layout)
        
        wet_layout = QHBoxLayout()
        wet_layout.addWidget(QLabel("混响强度:"))
        self.wet_slider = QSlider(Qt.Horizontal)
        self.wet_slider.setRange(1, 100)
        self.wet_slider.setValue(30)
        self.wet_slider.valueChanged.connect(self.update_reverb)
        wet_layout.addWidget(self.wet_slider)
        reverb_layout.addLayout(wet_layout)
        
        reverb_group.setLayout(reverb_layout)
        layout.addWidget(reverb_group)
        
        # 延迟效果
        delay_group = QGroupBox("延迟")
        delay_layout = QVBoxLayout()
        
        self.delay_enable = QCheckBox("启用延迟")
        self.delay_enable.toggled.connect(self.toggle_delay)
        delay_layout.addWidget(self.delay_enable)
        
        time_layout = QHBoxLayout()
        time_layout.addWidget(QLabel("延迟时间:"))
        self.time_slider = QSlider(Qt.Horizontal)
        self.time_slider.setRange(1, 100)
        self.time_slider.setValue(30)
        self.time_slider.valueChanged.connect(self.update_delay)
        time_layout.addWidget(self.time_slider)
        delay_layout.addLayout(time_layout)
        
        feedback_layout = QHBoxLayout()
        feedback_layout.addWidget(QLabel("反馈:"))
        self.feedback_slider = QSlider(Qt.Horizontal)
        self.feedback_slider.setRange(1, 100)
        self.feedback_slider.setValue(50)
        self.feedback_slider.valueChanged.connect(self.update_delay)
        feedback_layout.addWidget(self.feedback_slider)
        delay_layout.addLayout(feedback_layout)
        
        delay_wet_layout = QHBoxLayout()
        delay_wet_layout.addWidget(QLabel("延迟强度:"))
        self.delay_wet_slider = QSlider(Qt.Horizontal)
        self.delay_wet_slider.setRange(1, 100)
        self.delay_wet_slider.setValue(50)
        self.delay_wet_slider.valueChanged.connect(self.update_delay)
        delay_wet_layout.addWidget(self.delay_wet_slider)
        delay_layout.addLayout(delay_wet_layout)
        
        delay_group.setLayout(delay_layout)
        layout.addWidget(delay_group)
        
        # 失真效果
        distortion_group = QGroupBox("失真")
        distortion_layout = QVBoxLayout()
        
        self.distortion_enable = QCheckBox("启用失真")
        self.distortion_enable.toggled.connect(self.toggle_distortion)
        distortion_layout.addWidget(self.distortion_enable)
        
        gain_layout = QHBoxLayout()
        gain_layout.addWidget(QLabel("增益:"))
        self.gain_slider = QSlider(Qt.Horizontal)
        self.gain_slider.setRange(1, 100)
        self.gain_slider.setValue(20)
        self.gain_slider.valueChanged.connect(self.update_distortion)
        gain_layout.addWidget(self.gain_slider)
        distortion_layout.addLayout(gain_layout)
        
        dist_level_layout = QHBoxLayout()
        dist_level_layout.addWidget(QLabel("失真强度:"))
        self.dist_level_slider = QSlider(Qt.Horizontal)
        self.dist_level_slider.setRange(1, 100)
        self.dist_level_slider.setValue(50)
        self.dist_level_slider.valueChanged.connect(self.update_distortion)
        dist_level_layout.addWidget(self.dist_level_slider)
        distortion_layout.addLayout(dist_level_layout)
        
        distortion_group.setLayout(distortion_layout)
        layout.addWidget(distortion_group)
        
        self.setLayout(layout)
    
    def toggle_reverb(self, enabled):
        """切换混响效果"""
        self.instrument.generator.set_effect('reverb', enabled)
    
    def update_reverb(self):
        """更新混响参数"""
        room_size = self.room_slider.value() / 100.0
        damping = self.damping_slider.value() / 100.0
        wet_level = self.wet_slider.value() / 100.0
        
        self.instrument.generator.set_effect('reverb', self.reverb_enable.isChecked(),
                                           room_size=room_size, damping=damping, wet_level=wet_level)
    
    def toggle_delay(self, enabled):
        """切换延迟效果"""
        self.instrument.generator.set_effect('delay', enabled)
    
    def update_delay(self):
        """更新延迟参数"""
        delay_time = self.time_slider.value() / 100.0 * 0.5  # 最大0.5秒
        feedback = self.feedback_slider.value() / 100.0
        wet_level = self.delay_wet_slider.value() / 100.0
        
        self.instrument.generator.set_effect('delay', self.delay_enable.isChecked(),
                                           delay_time=delay_time, feedback=feedback, wet_level=wet_level)
    
    def toggle_distortion(self, enabled):
        """切换失真效果"""
        self.instrument.generator.set_effect('distortion', enabled)
    
    def update_distortion(self):
        """更新失真参数"""
        gain = self.gain_slider.value() / 10.0  # 1-10倍增益
        level = self.dist_level_slider.value() / 100.0
        
        self.instrument.generator.set_effect('distortion', self.distortion_enable.isChecked(),
                                           gain=gain, level=level)

class SequencerWidget(QWidget):
    """音序器组件"""
    
    def __init__(self, instrument, player):
        super().__init__()
        self.instrument = instrument
        self.player = player
        self.sequence = []  # 序列数据
        self.is_playing = False
        self.timer = QTimer()
        self.timer.timeout.connect(self.play_sequence)
        self.current_step = 0
        self.bpm = 120
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 控制面板
        control_layout = QHBoxLayout()
        
        self.play_btn = QPushButton("播放")
        self.play_btn.clicked.connect(self.toggle_play)
        control_layout.addWidget(self.play_btn)
        
        self.stop_btn = QPushButton("停止")
        self.stop_btn.clicked.connect(self.stop)
        control_layout.addWidget(self.stop_btn)
        
        control_layout.addWidget(QLabel("BPM:"))
        self.bpm_spin = QSpinBox()
        self.bpm_spin.setRange(40, 240)
        self.bpm_spin.setValue(120)
        self.bpm_spin.valueChanged.connect(self.set_bpm)
        control_layout.addWidget(self.bpm_spin)
        
        self.record_btn = QPushButton("录制")
        self.record_btn.clicked.connect(self.toggle_record)
        control_layout.addWidget(self.record_btn)
        
        control_layout.addStretch()
        layout.addLayout(control_layout)
        
        # 音序器网格
        self.grid_layout = QGridLayout()
        self.create_grid()
        layout.addLayout(self.grid_layout)
        
        self.setLayout(layout)
    
    def create_grid(self):
        """创建音序器网格"""
        # 清空现有网格
        for i in reversed(range(self.grid_layout.count())): 
            self.grid_layout.itemAt(i).widget().setParent(None)
        
        # 创建音符标签
        notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        
        for i, note in enumerate(reversed(notes)):  # 从高音到低音
            self.grid_layout.addWidget(QLabel(note), i+1, 0)
        
        # 创建步骤按钮
        self.step_buttons = []
        for step in range(16):  # 16步音序器
            self.grid_layout.addWidget(QLabel(str(step+1)), 0, step+1)
            
            for note_idx, note in enumerate(reversed(notes)):
                btn = QPushButton()
                btn.setCheckable(True)
                btn.setFixedSize(20, 20)
                btn.clicked.connect(lambda checked, s=step, n=note: self.toggle_step(s, n))
                self.grid_layout.addWidget(btn, note_idx+1, step+1)
                self.step_buttons.append((step, note, btn))
    
    def toggle_step(self, step, note):
        """切换步骤状态"""
        # 查找或创建步骤记录
        step_record = next((s for s in self.sequence if s['step'] == step and s['note'] == note), None)
        
        if step_record:
            self.sequence.remove(step_record)
        else:
            self.sequence.append({'step': step, 'note': note, 'octave': 4})
    
    def set_bpm(self, bpm):
        """设置BPM"""
        self.bpm = bpm
        if self.is_playing:
            self.timer.stop()
            self.timer.start(60000 / (self.bpm * 4))  # 16分音符间隔
    
    def toggle_play(self):
        """开始/停止播放序列"""
        if self.is_playing:
            self.stop()
        else:
            self.play()
    
    def play(self):
        """播放序列"""
        self.is_playing = True
        self.play_btn.setText("停止")
        self.current_step = 0
        interval = 60000 / (self.bpm * 4)  # 16分音符间隔（毫秒）
        self.timer.start()
    
    def stop(self):
        """停止播放"""
        self.is_playing = False
        self.play_btn.setText("播放")
        self.timer.stop()
        self.current_step = 0
    
    def play_sequence(self):
        """播放当前步骤的音符"""
        # 播放当前步骤的音符
        for step_record in self.sequence:
            if step_record['step'] == self.current_step:
                audio_data = self.instrument.play_note(
                    step_record['note'], 
                    0.2,  # 短音符
                    step_record['octave']
                )
                if audio_data:
                    self.player.play_audio(audio_data)
        
        # 更新到下一步
        self.current_step = (self.current_step + 1) % 16
    
    def toggle_record(self):
        """开始/停止录制"""
        if self.record_btn.text() == "录制":
            self.record_btn.setText("停止录制")
            # 这里可以添加录制逻辑
        else:
            self.record_btn.setText("录制")
            # 停止录制逻辑

class InstrumentPanel(QWidget):
    """乐器控制面板"""
    
    def __init__(self, instrument, player):
        super().__init__()
        self.instrument = instrument
        self.player = player
        self.current_octave = 4
        self.visualizer = VisualizerWidget()
        self.init_ui()
    
    def init_ui(self):
        main_layout = QHBoxLayout()
        
        # 左侧：乐器控制
        left_layout = QVBoxLayout()
        
        # 乐器名称
        title = QLabel(self.instrument.name)
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        left_layout.addWidget(title)
        
        # 八度控制
        octave_layout = QHBoxLayout()
        octave_layout.addWidget(QLabel("八度:"))
        self.octave_spin = QSpinBox()
        self.octave_spin.setRange(1, 7)
        self.octave_spin.setValue(self.current_octave)
        self.octave_spin.valueChanged.connect(self.change_octave)
        octave_layout.addWidget(self.octave_spin)
        octave_layout.addStretch()
        left_layout.addLayout(octave_layout)
        
        # 音符按钮
        notes_group = QGroupBox("音符")
        notes_layout = QHBoxLayout()
        
        # 钢琴键布局
        white_notes = ['C', 'D', 'E', 'F', 'G', 'A', 'B']
        black_notes = ['C#', 'D#', 'F#', 'G#', 'A#']
        
        # 创建白键和黑键
        white_keys_layout = QHBoxLayout()
        for note in white_notes:
            btn = QPushButton(note)
            btn.setFixedSize(40, 100)
            btn.setStyleSheet("QPushButton { background-color: white; color: black; border: 1px solid black; }")
            btn.clicked.connect(lambda checked, n=note: self.play_note(n))
            white_keys_layout.addWidget(btn)
        
        # 添加黑键（需要特殊布局）
        black_keys_layout = QHBoxLayout()
        black_keys_layout.setContentsMargins(20, 0, 0, 0)  # 左边距使黑键对齐
        
        # 在正确的位置插入黑键
        black_positions = [0, 1, 3, 4, 5]  # 黑键在白键之间的位置
        for i, note in enumerate(black_notes):
            # 添加占位符使黑键对齐
            if i > 0:
                black_keys_layout.addSpacing(10)
            
            btn = QPushButton(note)
            btn.setFixedSize(30, 60)
            btn.setStyleSheet("QPushButton { background-color: black; color: white; border: 1px solid #555; }")
            btn.clicked.connect(lambda checked, n=note: self.play_note(n))
            black_keys_layout.addWidget(btn)
        
        # 将白键和黑键组合
        notes_layout.addLayout(white_keys_layout)
        notes_layout.addLayout(black_keys_layout)
        notes_group.setLayout(notes_layout)
        left_layout.addWidget(notes_group)
        
        # 音色控制
        if not isinstance(self.instrument, Drum):  # 鼓没有音色控制
            tone_group = QGroupBox("音色控制")
            tone_layout = QVBoxLayout()
            
            # 波形选择
            wave_layout = QHBoxLayout()
            wave_layout.addWidget(QLabel("波形:"))
            self.wave_combo = QComboBox()
            self.wave_combo.addItems(["正弦波", "方波", "锯齿波", "三角波", "噪声"])
            wave_layout.addWidget(self.wave_combo)
            tone_layout.addLayout(wave_layout)
            
            # 振幅控制
            amp_layout = QHBoxLayout()
            amp_layout.addWidget(QLabel("振幅:"))
            self.amp_slider = QSlider(Qt.Horizontal)
            self.amp_slider.setRange(1, 100)
            self.amp_slider.setValue(50)
            self.amp_slider.valueChanged.connect(self.update_amplitude)
            amp_layout.addWidget(self.amp_slider)
            tone_layout.addLayout(amp_layout)
            
            tone_group.setLayout(tone_layout)
            left_layout.addWidget(tone_group)
        
        # 持续时间控制
        duration_layout = QHBoxLayout()
        duration_layout.addWidget(QLabel("持续时间:"))
        self.duration_spin = QDoubleSpinBox()
        self.duration_spin.setRange(0.1, 5.0)
        self.duration_spin.setValue(1.0)
        self.duration_spin.setSingleStep(0.1)
        duration_layout.addWidget(self.duration_spin)
        duration_layout.addWidget(QLabel("秒"))
        left_layout.addLayout(duration_layout)
        
        left_layout.addStretch()
        
        # 右侧：音效和可视化
        right_layout = QVBoxLayout()
        
        # 音效面板
        self.effects_panel = EffectsPanel(self.instrument)
        right_layout.addWidget(self.effects_panel)
        
        # 可视化
        right_layout.addWidget(QLabel("音频可视化:"))
        right_layout.addWidget(self.visualizer)
        
        right_layout.addStretch()
        
        # 组合左右布局
        main_layout.addLayout(left_layout)
        main_layout.addLayout(right_layout)
        
        self.setLayout(main_layout)
    
    def change_octave(self, value):
        """改变八度"""
        self.current_octave = value
    
    def update_amplitude(self, value):
        """更新振幅"""
        self.instrument.generator.amplitude = value / 100.0
    
    def play_note(self, note):
        """播放音符"""
        wave_type_map = {
            "正弦波": "sine",
            "方波": "square",
            "锯齿波": "sawtooth",
            "三角波": "triangle",
            "噪声": "noise"
        }
        
        if isinstance(self.instrument, Drum):
            audio_data = self.instrument.play_note(note, self.duration_spin.value(), self.current_octave)
        else:
            wave_type = wave_type_map.get(self.wave_combo.currentText(), "sine")
            amplitude = self.amp_slider.value() / 100.0
            self.instrument.generator.amplitude = amplitude
            audio_data = self.instrument.play_note(note, self.duration_spin.value(), self.current_octave, wave_type)
        
        if audio_data:
            self.player.play_audio(audio_data)
            self.visualizer.set_audio_data(audio_data)

class RecordingTab(QWidget):
    """录音选项卡"""
    
    def __init__(self, player):
        super().__init__()
        self.player = player
        self.recorder = None
        self.recording_file = "recording.wav"
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 录音控制
        record_group = QGroupBox("录音控制")
        record_layout = QVBoxLayout()
        
        # 文件选择
        file_layout = QHBoxLayout()
        file_layout.addWidget(QLabel("文件名:"))
        self.file_label = QLabel(self.recording_file)
        file_layout.addWidget(self.file_label)
        self.file_btn = QPushButton("浏览...")
        self.file_btn.clicked.connect(self.choose_file)
        file_layout.addWidget(self.file_btn)
        record_layout.addLayout(file_layout)
        
        # 录音时长
        duration_layout = QHBoxLayout()
        duration_layout.addWidget(QLabel("录音时长:"))
        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(1, 60)
        self.duration_spin.setValue(10)
        duration_layout.addWidget(self.duration_spin)
        duration_layout.addWidget(QLabel("秒"))
        record_layout.addLayout(duration_layout)
        
        # 录音按钮
        self.record_btn = QPushButton("开始录音")
        self.record_btn.clicked.connect(self.toggle_recording)
        record_layout.addWidget(self.record_btn)
        
        # 录音进度
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        record_layout.addWidget(self.progress_bar)
        
        record_group.setLayout(record_layout)
        layout.addWidget(record_group)
        
        # 播放控制
        playback_group = QGroupBox("播放控制")
        playback_layout = QHBoxLayout()
        
        self.play_btn = QPushButton("播放录音")
        self.play_btn.clicked.connect(self.play_recording)
        playback_layout.addWidget(self.play_btn)
        
        self.stop_btn = QPushButton("停止播放")
        self.stop_btn.clicked.connect(self.stop_playback)
        playback_layout.addWidget(self.stop_btn)
        
        playback_group.setLayout(playback_layout)
        layout.addWidget(playback_group)
        
        # 录音列表
        recordings_group = QGroupBox("录音列表")
        recordings_layout = QVBoxLayout()
        
        self.recordings_list = QListWidget()
        self.load_recordings()
        recordings_layout.addWidget(self.recordings_list)
        
        # 操作按钮
        list_buttons_layout = QHBoxLayout()
        self.delete_btn = QPushButton("删除选中")
        self.delete_btn.clicked.connect(self.delete_recording)
        list_buttons_layout.addWidget(self.delete_btn)
        
        self.rename_btn = QPushButton("重命名")
        self.rename_btn.clicked.connect(self.rename_recording)
        list_buttons_layout.addWidget(self.rename_btn)
        
        recordings_layout.addLayout(list_buttons_layout)
        recordings_group.setLayout(recordings_layout)
        layout.addWidget(recordings_group)
        
        layout.addStretch()
        self.setLayout(layout)
    
    def load_recordings(self):
        """加载录音文件列表"""
        self.recordings_list.clear()
        recordings_dir = "recordings"
        if not os.path.exists(recordings_dir):
            os.makedirs(recordings_dir)
        
        for file in os.listdir(recordings_dir):
            if file.endswith('.wav'):
                item = QListWidgetItem(file)
                self.recordings_list.addItem(item)
    
    def choose_file(self):
        """选择录音文件"""
        filename, _ = QFileDialog.getSaveFileName(self, "保存录音", "recordings/", "WAV文件 (*.wav)")
        if filename:
            if not filename.endswith('.wav'):
                filename += '.wav'
            self.recording_file = filename
            self.file_label.setText(os.path.basename(filename))
    
    def toggle_recording(self):
        """开始/停止录音"""
        if self.recorder and self.recorder.is_recording:
            # 停止录音
            self.recorder.stop()
            self.recorder.wait()
            self.record_btn.setText("开始录音")
            self.progress_bar.setVisible(False)
            self.load_recordings()  # 刷新列表
        else:
            # 开始录音
            self.recorder = AudioRecorderThread(
                self.recording_file, 
                self.duration_spin.value()
            )
            self.recorder.update_signal.connect(self.update_progress)
            self.recorder.finished_signal.connect(self.recording_finished)
            self.recorder.start()
            self.record_btn.setText("停止录音")
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)
    
    def recording_finished(self, filename):
        """录音完成"""
        self.load_recordings()  # 刷新列表
    
    def update_progress(self, value):
        """更新录音进度"""
        self.progress_bar.setValue(value)
    
    def play_recording(self):
        """播放录音"""
        if self.recordings_list.currentItem():
            filename = "recordings/" + self.recordings_list.currentItem().text()
        else:
            filename = self.recording_file
            
        if os.path.exists(filename):
            # 读取WAV文件并播放
            wf = wave.open(filename, 'rb')
            audio_data = wf.readframes(wf.getnframes())
            wf.close()
            self.player.play_audio(audio_data, wf.getframerate())
        else:
            QMessageBox.warning(self, "错误", "录音文件不存在！")
    
    def stop_playback(self):
        """停止播放"""
        self.player.stop()
    
    def delete_recording(self):
        """删除选中的录音"""
        if self.recordings_list.currentItem():
            filename = "recordings/" + self.recordings_list.currentItem().text()
            if os.path.exists(filename):
                os.remove(filename)
                self.load_recordings()
    
    def rename_recording(self):
        """重命名选中的录音"""
        if self.recordings_list.currentItem():
            old_filename = "recordings/" + self.recordings_list.currentItem().text()
            new_name, ok = QFileDialog.getSaveFileName(self, "重命名录音", "recordings/", "WAV文件 (*.wav)")
            if ok and new_name:
                if not new_name.endswith('.wav'):
                    new_name += '.wav'
                os.rename(old_filename, new_name)
                self.load_recordings()

class SequencerTab(QWidget):
    """音序器选项卡"""
    
    def __init__(self, player):
        super().__init__()
        self.player = player
        self.instruments = {
            "钢琴": Piano(),
            "吉他": Guitar(),
            "小提琴": Violin(),
            "贝斯": Bass(),
            "合成器": Synthesizer(),
            "鼓": Drum()
        }
        self.current_instrument = "钢琴"
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 乐器选择
        instrument_layout = QHBoxLayout()
        instrument_layout.addWidget(QLabel("选择乐器:"))
        self.instrument_combo = QComboBox()
        self.instrument_combo.addItems(self.instruments.keys())
        self.instrument_combo.currentTextChanged.connect(self.change_instrument)
        instrument_layout.addWidget(self.instrument_combo)
        instrument_layout.addStretch()
        layout.addLayout(instrument_layout)
        
        # 音序器
        self.sequencer = SequencerWidget(self.instruments[self.current_instrument], self.player)
        layout.addWidget(self.sequencer)
        
        self.setLayout(layout)
    
    def change_instrument(self, instrument_name):
        """改变乐器"""
        self.current_instrument = instrument_name
        self.sequencer.instrument = self.instruments[instrument_name]

class SettingsTab(QWidget):
    """设置选项卡"""
    
    def __init__(self, studio):
        super().__init__()
        self.studio = studio
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 预设管理
        preset_group = QGroupBox("预设管理")
        preset_layout = QVBoxLayout()
        
        preset_buttons_layout = QHBoxLayout()
        self.save_preset_btn = QPushButton("保存预设")
        self.save_preset_btn.clicked.connect(self.save_preset)
        preset_buttons_layout.addWidget(self.save_preset_btn)
        
        self.load_preset_btn = QPushButton("加载预设")
        self.load_preset_btn.clicked.connect(self.load_preset)
        preset_buttons_layout.addWidget(self.load_preset_btn)
        
        preset_layout.addLayout(preset_buttons_layout)
        
        self.preset_list = QListWidget()
        self.load_preset_list()
        preset_layout.addWidget(self.preset_list)
        
        preset_group.setLayout(preset_layout)
        layout.addWidget(preset_group)
        
        # 音频设置
        audio_group = QGroupBox("音频设置")
        audio_layout = QVBoxLayout()
        
        sample_rate_layout = QHBoxLayout()
        sample_rate_layout.addWidget(QLabel("采样率:"))
        self.sample_rate_combo = QComboBox()
        self.sample_rate_combo.addItems(["44100", "48000", "96000"])
        self.sample_rate_combo.setCurrentText("44100")
        sample_rate_layout.addWidget(self.sample_rate_combo)
        audio_layout.addLayout(sample_rate_layout)
        
        buffer_layout = QHBoxLayout()
        buffer_layout.addWidget(QLabel("缓冲区大小:"))
        self.buffer_combo = QComboBox()
        self.buffer_combo.addItems(["256", "512", "1024", "2048"])
        self.buffer_combo.setCurrentText("1024")
        buffer_layout.addWidget(self.buffer_combo)
        audio_layout.addLayout(buffer_layout)
        
        audio_group.setLayout(audio_layout)
        layout.addWidget(audio_group)
        
        layout.addStretch()
        self.setLayout(layout)
    
    def load_preset_list(self):
        """加载预设列表"""
        self.preset_list.clear()
        presets_dir = "presets"
        if not os.path.exists(presets_dir):
            os.makedirs(presets_dir)
        
        for file in os.listdir(presets_dir):
            if file.endswith('.json'):
                item = QListWidgetItem(file[:-5])  # 去掉.json扩展名
                self.preset_list.addItem(item)
    
    def save_preset(self):
        """保存预设"""
        name, ok = QInputDialog.getText(self, "保存预设", "预设名称:")
        if ok and name:
            # 这里应该保存所有乐器和效果的设置
            preset_data = {
                "version": "1.0",
                "timestamp": time.time(),
                # 可以添加更多设置数据
            }
            
            with open(f"presets/{name}.json", "w") as f:
                json.dump(preset_data, f)
            
            self.load_preset_list()
    
    def load_preset(self):
        """加载预设"""
        if self.preset_list.currentItem():
            preset_name = self.preset_list.currentItem().text()
            try:
                with open(f"presets/{preset_name}.json", "r") as f:
                    preset_data = json.load(f)
                # 这里应该应用预设数据
                QMessageBox.information(self, "成功", f"已加载预设: {preset_name}")
            except Exception as e:
                QMessageBox.warning(self, "错误", f"加载预设失败: {str(e)}")

class MusicStudio(QMainWindow):
    """音乐工作室主窗口"""
    
    def __init__(self):
        super().__init__()
        self.player = AudioPlayer()
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("增强版音乐工作室")
        self.setGeometry(100, 100, 1000, 700)
        
        # 设置样式
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QTabWidget::pane {
                border: 1px solid #444;
                background-color: #3c3f41;
            }
            QTabBar::tab {
                background-color: #3c3f41;
                color: #ffffff;
                padding: 8px 12px;
                border: 1px solid #444;
            }
            QTabBar::tab:selected {
                background-color: #4c4f51;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #555;
                border-radius: 5px;
                margin-top: 1ex;
                padding-top: 10px;
                color: #ffffff;
                background-color: #3c3f41;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #bbbbbb;
            }
            QPushButton {
                background-color: #5c5c5c;
                border: 1px solid #555;
                color: white;
                padding: 6px 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #6c6c6c;
            }
            QPushButton:pressed {
                background-color: #4c4c4c;
            }
            QPushButton:checked {
                background-color: #4a6ea9;
            }
            QSlider::groove:horizontal {
                border: 1px solid #555;
                height: 5px;
                background: #4a4a4a;
                margin: 2px 0;
            }
            QSlider::handle:horizontal {
                background: #6c6c6c;
                border: 1px solid #555;
                width: 12px;
                margin: -5px 0;
                border-radius: 6px;
            }
            QComboBox, QSpinBox, QDoubleSpinBox {
                background-color: #4a4a4a;
                border: 1px solid #555;
                color: white;
                padding: 3px;
            }
            QListWidget {
                background-color: #4a4a4a;
                color: white;
                border: 1px solid #555;
            }
            QProgressBar {
                border: 1px solid #555;
                text-align: center;
                color: white;
            }
            QProgressBar::chunk {
                background-color: #4a6ea9;
            }
        """)
        
        # 创建选项卡
        self.tabs = QTabWidget()
        
        # 创建各种乐器
        piano = Piano()
        guitar = Guitar()
        violin = Violin()
        bass = Bass()
        synthesizer = Synthesizer()
        drum = Drum()
        
        # 添加乐器面板
        self.tabs.addTab(InstrumentPanel(piano, self.player), "钢琴")
        self.tabs.addTab(InstrumentPanel(guitar, self.player), "吉他")
        self.tabs.addTab(InstrumentPanel(violin, self.player), "小提琴")
        self.tabs.addTab(InstrumentPanel(bass, self.player), "贝斯")
        self.tabs.addTab(InstrumentPanel(synthesizer, self.player), "合成器")
        self.tabs.addTab(InstrumentPanel(drum, self.player), "鼓")
        
        # 添加音序器选项卡
        self.tabs.addTab(SequencerTab(self.player), "音序器")
        
        # 添加录音选项卡
        self.tabs.addTab(RecordingTab(self.player), "录音")
        
        # 添加设置选项卡
        self.tabs.addTab(SettingsTab(self), "设置")
        
        self.setCentralWidget(self.tabs)
    
    def closeEvent(self, event):
        """关闭应用程序时停止所有音频播放"""
        self.player.stop()
        event.accept()

def main():
    app = QApplication(sys.argv)
    
    # 设置应用程序样式
    app.setStyle('Fusion')
    
    # 创建并显示主窗口
    studio = MusicStudio()
    studio.show()
    
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()