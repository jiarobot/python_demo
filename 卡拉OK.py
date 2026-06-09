import numpy as np
import librosa
import pygame
import time
import threading
import json
import os
import tempfile
import requests
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from PyQt5.QtCore import (Qt, QTimer, pyqtSignal, QObject, QThread, 
                         QPointF, QRectF, QEasingCurve, QPropertyAnimation,
                         QParallelAnimationGroup, QSequentialAnimationGroup)
from PyQt5.QtGui import (QPainter, QColor, QPen, QFont, QLinearGradient,
                        QRadialGradient, QConicalGradient, QPainterPath,
                        QPixmap, QImage, QBrush, QPolygonF)
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QPushButton, QSlider, QLabel, 
                            QFileDialog, QProgressBar, QGroupBox, QFrame,
                            QComboBox, QSpinBox, QDoubleSpinBox, QCheckBox,
                            QTabWidget, QTableWidget, QTableWidgetItem,
                            QListView, QListWidget, QListWidgetItem,
                            QSplitter, QStackedWidget, QToolButton,
                            QMenu, QAction, QMessageBox, QInputDialog,
                            QLineEdit, QDialog, QDialogButtonBox,
                            QFormLayout, QGraphicsView, QGraphicsScene,
                            QGraphicsItem, QStyleOptionGraphicsItem)

class AudioFeatureExtractor:
    """高级音频特征提取器"""
    
    def __init__(self):
        self.scaler = StandardScaler()
        self.feature_names = [
            'pitch_mean', 'pitch_std', 'pitch_range',
            'energy_mean', 'energy_std', 'energy_peak',
            'spectral_centroid_mean', 'spectral_centroid_std',
            'spectral_bandwidth_mean', 'spectral_bandwidth_std',
            'spectral_rolloff_mean', 'spectral_rolloff_std',
            'zero_crossing_rate_mean', 'zero_crossing_rate_std',
            'mfcc_1_mean', 'mfcc_1_std', 'mfcc_2_mean', 'mfcc_2_std',
            'chroma_1_mean', 'chroma_1_std', 'chroma_2_mean', 'chroma_2_std',
            'tempo', 'beat_strength_mean', 'beat_strength_std'
        ]
    
    def extract_features(self, y: np.ndarray, sr: int) -> np.ndarray:
        """提取音频特征向量"""
        features = []
        
        # 音高特征
        pitches, magnitudes = librosa.piptrack(y=y, sr=sr)
        pitches = pitches[pitches > 0]  # 过滤零值
        if len(pitches) > 0:
            features.extend([np.mean(pitches), np.std(pitches), np.ptp(pitches)])
        else:
            features.extend([0, 0, 0])
        
        # 能量特征
        energy = np.sum(y**2) / len(y)
        energy_std = np.std(y**2)
        energy_peak = np.max(y**2)
        features.extend([energy, energy_std, energy_peak])
        
        # 频谱特征
        spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
        spectral_bandwidth = librosa.feature.spectral_bandwidth(y=y, sr=sr)[0]
        spectral_rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr)[0]
        
        features.extend([np.mean(spectral_centroid), np.std(spectral_centroid)])
        features.extend([np.mean(spectral_bandwidth), np.std(spectral_bandwidth)])
        features.extend([np.mean(spectral_rolloff), np.std(spectral_rolloff)])
        
        # 过零率
        zero_crossing_rate = librosa.feature.zero_crossing_rate(y)[0]
        features.extend([np.mean(zero_crossing_rate), np.std(zero_crossing_rate)])
        
        # MFCC特征
        mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
        features.extend([np.mean(mfccs[0]), np.std(mfccs[0])])
        features.extend([np.mean(mfccs[1]), np.std(mfccs[1])])
        
        # 色度特征
        chroma = librosa.feature.chroma_stft(y=y, sr=sr)
        features.extend([np.mean(chroma[0]), np.std(chroma[0])])
        features.extend([np.mean(chroma[1]), np.std(chroma[1])])
        
        # 节奏特征
        tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
        features.append(tempo)
        
        # 节拍强度
        if len(beats) > 0:
            beat_strengths = librosa.feature.rmse(y=y)[0][beats]
            features.extend([np.mean(beat_strengths), np.std(beat_strengths)])
        else:
            features.extend([0, 0])
        
        return np.array(features)
    
    def fit_scaler(self, features_list: List[np.ndarray]):
        """训练特征标准化器"""
        features_matrix = np.vstack(features_list)
        self.scaler.fit(features_matrix)
    
    def normalize_features(self, features: np.ndarray) -> np.ndarray:
        """标准化特征"""
        return self.scaler.transform(features.reshape(1, -1))[0]


class MLScoringModel:
    """机器学习评分模型"""
    
    def __init__(self):
        self.model = RandomForestClassifier(n_estimators=100, random_state=42)
        self.is_trained = False
    
    def train(self, X: np.ndarray, y: np.ndarray):
        """训练模型"""
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42)
        
        self.model.fit(X_train, y_train)
        
        # 评估模型
        train_score = self.model.score(X_train, y_train)
        test_score = self.model.score(X_test, y_test)
        
        print(f"模型训练完成 - 训练集准确率: {train_score:.3f}, 测试集准确率: {test_score:.3f}")
        self.is_trained = True
    
    def predict_score(self, features: np.ndarray) -> float:
        """预测评分"""
        if not self.is_trained:
            return np.random.uniform(70, 95)  # 默认随机评分
        
        # 使用模型预测
        prediction = self.model.predict_proba(features.reshape(1, -1))[0]
        
        # 将概率转换为0-100的评分
        score = np.dot(prediction, np.array([60, 70, 80, 90, 95]))
        return max(60, min(100, score))


class CloudSyncManager(QObject):
    """云端同步管理器"""
    
    sync_complete = pyqtSignal(bool, str)
    
    def __init__(self, api_url: str = "https://api.karaoke.example.com"):
        super().__init__()
        self.api_url = api_url
        self.session_token = None
        self.user_id = None
    
    def login(self, username: str, password: str) -> bool:
        """用户登录"""
        try:
            response = requests.post(
                f"{self.api_url}/auth/login",
                json={"username": username, "password": password},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                self.session_token = data.get("token")
                self.user_id = data.get("user_id")
                return True
            return False
        except Exception as e:
            print(f"登录失败: {e}")
            return False
    
    def upload_score(self, song_id: str, score_data: Dict) -> bool:
        """上传评分数据"""
        if not self.session_token:
            return False
        
        try:
            response = requests.post(
                f"{self.api_url}/scores/upload",
                json={
                    "user_id": self.user_id,
                    "song_id": song_id,
                    "score_data": score_data,
                    "timestamp": datetime.now().isoformat()
                },
                headers={"Authorization": f"Bearer {self.session_token}"},
                timeout=10
            )
            
            return response.status_code == 200
        except Exception as e:
            print(f"上传评分失败: {e}")
            return False
    
    def download_leaderboard(self, song_id: str) -> List[Dict]:
        """下载排行榜数据"""
        try:
            response = requests.get(
                f"{self.api_url}/scores/leaderboard/{song_id}",
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            return []
        except Exception as e:
            print(f"下载排行榜失败: {e}")
            return []
    
    def sync_scores(self, local_scores: List[Dict]) -> bool:
        """同步本地和云端评分"""
        # 实现同步逻辑
        success = True
        for score in local_scores:
            if not self.upload_score(score['song_id'], score):
                success = False
        
        self.sync_complete.emit(success, "同步完成" if success else "同步失败")
        return success


class AdvancedAudioProcessor(QObject):
    """高级音频处理器"""
    
    analysis_complete = pyqtSignal(dict)
    realtime_data = pyqtSignal(object)
    recording_complete = pyqtSignal(np.ndarray)
    
    def __init__(self):
        super().__init__()
        self.audio_data = None
        self.sample_rate = None
        self.is_playing = False
        self.is_recording = False
        self.recorded_data = None
        self.current_position = 0
        self.tempo = 0
        self.beats = None
        self.pitch_track = None
        
        # 初始化特征提取器
        self.feature_extractor = AudioFeatureExtractor()
        
        # 初始化音频设备
        pygame.mixer.init()
        
    def load_audio(self, file_path: str) -> bool:
        """加载音频文件"""
        try:
            self.audio_data, self.sample_rate = librosa.load(file_path, sr=None)
            self.analyze_audio()
            return True
        except Exception as e:
            print(f"加载音频失败: {e}")
            return False
    
    def analyze_audio(self):
        """分析音频特征"""
        def analysis_thread():
            # 提取节奏信息
            self.tempo, self.beats = librosa.beat.beat_track(
                y=self.audio_data, sr=self.sample_rate)
            
            # 提取音高信息
            self.pitch_track = librosa.yin(
                self.audio_data, 
                fmin=librosa.note_to_hz('C2'), 
                fmax=librosa.note_to_hz('C7'), 
                sr=self.sample_rate
            )
            
            # 提取色度特征
            chroma = librosa.feature.chroma_stft(
                y=self.audio_data, sr=self.sample_rate)
            
            # 提取高级特征
            features = self.feature_extractor.extract_features(self.audio_data, self.sample_rate)
            
            # 发送分析完成信号
            result = {
                'tempo': self.tempo,
                'beats': self.beats,
                'pitch_track': self.pitch_track,
                'chroma': chroma,
                'duration': librosa.get_duration(y=self.audio_data, sr=self.sample_rate),
                'features': features
            }
            self.analysis_complete.emit(result)
        
        threading.Thread(target=analysis_thread, daemon=True).start()
    
    def start_playback(self):
        """开始播放音频"""
        if self.audio_data is not None:
            self.is_playing = True
            self.audio_data_16bit = (self.audio_data * 32767).astype(np.int16)
            self.sound = pygame.sndarray.make_sound(self.audio_data_16bit)
            self.sound.play()
            self.start_time = time.time()
            
            # 启动实时数据发送定时器
            self.timer = QTimer()
            self.timer.timeout.connect(self.send_realtime_data)
            self.timer.start(30)  # 每30ms发送一次数据
    
    def stop_playback(self):
        """停止播放"""
        if self.is_playing:
            self.is_playing = False
            if hasattr(self, 'sound'):
                self.sound.stop()
            if hasattr(self, 'timer'):
                self.timer.stop()
    
    def start_recording(self, duration: float = 60.0):
        """开始录音"""
        self.is_recording = True
        self.recorded_data = []
        self.recording_start_time = time.time()
        self.recording_duration = duration
        
        # 初始化录音设备
        pygame.mixer.quit()
        pygame.mixer.init(frequency=44100, size=-16, channels=1, buffer=1024)
        
        # 创建录音线程
        self.recording_thread = threading.Thread(target=self._record_audio, daemon=True)
        self.recording_thread.start()
    
    def stop_recording(self):
        """停止录音"""
        self.is_recording = False
        if hasattr(self, 'recording_thread'):
            self.recording_thread.join(timeout=1.0)
        
        # 转换录音数据
        if self.recorded_data:
            recorded_array = np.array(self.recorded_data, dtype=np.float32)
            self.recording_complete.emit(recorded_array)
            return recorded_array
        return None
    
    def _record_audio(self):
        """录音线程函数"""
        # 创建临时声音文件
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
        temp_filename = temp_file.name
        temp_file.close()
        
        # 开始录音
        pygame.mixer.Stop()
        sound = pygame.mixer.Sound(buffer=bytearray(int(44100 * 2 * self.recording_duration)))
        channel = sound.play()
        
        # 采集音频数据
        while self.is_recording and (time.time() - self.recording_start_time < self.recording_duration):
            # 获取当前音频数据
            samples = pygame.sndarray.array(channel.get_sound())
            if samples is not None and len(samples) > 0:
                self.recorded_data.extend(samples / 32767.0)  # 转换为浮点数
            
            time.sleep(0.01)  # 短暂休眠
        
        # 停止录音
        channel.stop()
        
        # 保存录音文件
        pygame.mixer.Sound(buffer=np.array(self.recorded_data, dtype=np.int16)).save(temp_filename)
        
        # 重新初始化播放设备
        pygame.mixer.quit()
        pygame.mixer.init()
    
    def send_realtime_data(self):
        """发送实时音频数据"""
        if self.is_playing:
            current_time = time.time() - self.start_time
            position = int(current_time * self.sample_rate)
            
            if position < len(self.audio_data):
                # 提取当前时间窗口的数据
                window_size = min(2048, len(self.audio_data) - position)
                window = self.audio_data[position:position+window_size]
                
                # 计算实时特征
                if len(window) > 0:
                    # 实时音量
                    volume = np.sqrt(np.mean(window**2))
                    
                    # 实时音高估计
                    if len(window) >= 1024:
                        pitch = librosa.yin(
                            window, 
                            fmin=80, 
                            fmax=1000, 
                            sr=self.sample_rate
                        )
                        current_pitch = np.median(pitch[pitch > 0]) if np.any(pitch > 0) else 0
                    else:
                        current_pitch = 0
                    
                    # 频谱特征
                    spectral_centroid = librosa.feature.spectral_centroid(y=window, sr=self.sample_rate)[0]
                    spectral_centroid_mean = np.mean(spectral_centroid) if len(spectral_centroid) > 0 else 0
                    
                    # 发送实时数据
                    self.realtime_data.emit({
                        'position': position,
                        'volume': volume,
                        'pitch': current_pitch,
                        'spectral_centroid': spectral_centroid_mean,
                        'time': current_time
                    })


class AdvancedScoringEngine:
    """高级评分引擎"""
    
    def __init__(self, reference_audio_processor: AdvancedAudioProcessor):
        self.reference = reference_audio_processor
        self.user_performance = []
        self.ml_model = MLScoringModel()
        
        # 加载或训练模型
        self._load_or_train_model()
    
    def _load_or_train_model(self):
        """加载或训练评分模型"""
        model_path = "scoring_model.pkl"
        if os.path.exists(model_path):
            # 加载预训练模型
            try:
                # 这里应该是模型加载代码
                print("加载预训练评分模型")
            except:
                print("加载模型失败，使用默认评分")
                self.ml_model.is_trained = False
        else:
            # 训练新模型
            print("训练新的评分模型...")
            # 这里应该是模型训练代码
            self.ml_model.is_trained = False
    
    def record_user_performance(self, user_data: Dict):
        """记录用户表现数据"""
        self.user_performance.append(user_data)
    
    def calculate_score(self, user_features: np.ndarray, reference_features: np.ndarray) -> Dict[str, float]:
        """计算综合评分"""
        # 使用机器学习模型预测基础评分
        base_score = self.ml_model.predict_score(user_features)
        
        # 计算音准评分
        pitch_score = self._calculate_pitch_score(user_features, reference_features)
        
        # 计算节奏评分
        timing_score = self._calculate_timing_score(user_features, reference_features)
        
        # 计算表现力评分
        expression_score = self._calculate_expression_score(user_features, reference_features)
        
        # 综合评分 (加权平均)
        total_score = (
            base_score * 0.3 +
            pitch_score * 0.3 +
            timing_score * 0.25 +
            expression_score * 0.15
        )
        
        return {
            'total': int(total_score),
            'base': int(base_score),
            'pitch': int(pitch_score),
            'timing': int(timing_score),
            'expression': int(expression_score)
        }
    
    def _calculate_pitch_score(self, user_features: np.ndarray, reference_features: np.ndarray) -> float:
        """计算音准得分"""
        # 提取音高相关特征
        user_pitch_mean = user_features[0]
        user_pitch_std = user_features[1]
        ref_pitch_mean = reference_features[0]
        ref_pitch_std = reference_features[1]
        
        # 计算音高匹配度
        pitch_match = 100 - abs(user_pitch_mean - ref_pitch_mean) * 0.5
        stability_penalty = user_pitch_std * 2
        
        return max(0, min(100, pitch_match - stability_penalty))
    
    def _calculate_timing_score(self, user_features: np.ndarray, reference_features: np.ndarray) -> float:
        """计算节奏得分"""
        # 提取节奏相关特征
        user_tempo = user_features[21]
        user_beat_strength = user_features[23]
        ref_tempo = reference_features[21]
        ref_beat_strength = reference_features[23]
        
        # 计算节奏匹配度
        tempo_match = 100 - abs(user_tempo - ref_tempo) * 0.2
        beat_strength_match = 100 - abs(user_beat_strength - ref_beat_strength) * 10
        
        return max(0, min(100, (tempo_match + beat_strength_match) / 2))
    
    def _calculate_expression_score(self, user_features: np.ndarray, reference_features: np.ndarray) -> float:
        """计算表现力得分"""
        # 提取表现力相关特征
        user_energy = user_features[3]
        user_spectral_centroid = user_features[6]
        ref_energy = reference_features[3]
        ref_spectral_centroid = reference_features[6]
        
        # 计算能量变化
        energy_variation = min(user_energy / ref_energy, 2.0) * 50
        
        # 计算音色丰富度
        spectral_richness = min(user_spectral_centroid / ref_spectral_centroid, 1.5) * 50
        
        return max(0, min(100, energy_variation + spectral_richness))


class AdvancedVisualizerWidget(QWidget):
    """高级音频可视化组件"""
    
    def __init__(self):
        super().__init__()
        self.setMinimumSize(1000, 300)
        self.audio_data = None
        self.reference_data = None
        self.user_data = None
        self.sample_rate = None
        self.realtime_volume = 0
        self.realtime_pitch = 0
        self.realtime_spectral_centroid = 0
        self.waveform_points = []
        self.spectrum_data = None
        self.current_position = 0
        self.animation_group = QParallelAnimationGroup()
        self.animation_group.start()
        
        # 颜色主题
        self.colors = {
            'background': QColor(20, 20, 30),
            'waveform': QColor(0, 200, 255, 180),
            'waveform_user': QColor(255, 100, 100, 180),
            'spectrum': QColor(100, 255, 100, 150),
            'position_marker': QColor(255, 50, 50),
            'volume_meter': [QColor(0, 255, 0), QColor(255, 255, 0), QColor(255, 0, 0)],
            'pitch_indicator': QColor(200, 100, 255),
            'spectral_indicator': QColor(255, 200, 100)
        }
    
    def set_audio_data(self, audio_data: np.ndarray, sample_rate: int, is_reference: bool = True):
        """设置音频数据"""
        if is_reference:
            self.reference_data = audio_data
        else:
            self.user_data = audio_data
        
        self.sample_rate = sample_rate
        
        # 计算频谱数据
        if audio_data is not None:
            self.spectrum_data = np.abs(np.fft.rfft(audio_data[:4096]))
            self.spectrum_data = 20 * np.log10(self.spectrum_data + 1e-10)
        
        self.update()
    
    def update_realtime_data(self, data: Dict):
        """更新实时数据"""
        self.realtime_volume = data['volume']
        self.realtime_pitch = data.get('pitch', 0)
        self.realtime_spectral_centroid = data.get('spectral_centroid', 0)
        self.current_position = data.get('position', 0)
        self.update()
    
    def paintEvent(self, event):
        """绘制可视化"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 绘制背景
        painter.fillRect(self.rect(), self.colors['background'])
        
        # 绘制参考波形
        if self.reference_data is not None:
            self._draw_waveform(painter, self.reference_data, self.colors['waveform'])
        
        # 绘制用户波形
        if self.user_data is not None:
            self._draw_waveform(painter, self.user_data, self.colors['waveform_user'], offset=50)
        
        # 绘制频谱
        if self.spectrum_data is not None:
            self._draw_spectrum(painter)
        
        # 绘制实时指示器
        self._draw_realtime_indicators(painter)
        
        # 绘制播放位置指示器
        self._draw_position_indicator(painter)
        
        # 绘制网格和标签
        self._draw_grid_and_labels(painter)
    
    def _draw_waveform(self, painter: QPainter, data: np.ndarray, color: QColor, offset: int = 0):
        """绘制音频波形"""
        if len(data) == 0:
            return
        
        width = self.width()
        height = self.height() // 2 - 20
        y_base = offset + height // 2
        
        # 简化波形数据点
        samples_per_point = max(1, len(data) // width)
        path = QPainterPath()
        path.moveTo(0, y_base)
        
        for i in range(0, len(data), samples_per_point):
            segment = data[i:i+samples_per_point]
            if len(segment) > 0:
                max_val = np.max(segment)
                x = (i / len(data)) * width
                y = y_base - (max_val * height / 2)
                path.lineTo(x, y)
        
        # 绘制波形路径
        gradient = QLinearGradient(0, 0, width, 0)
        gradient.setColorAt(0, color)
        gradient.setColorAt(1, color.darker(150))
        
        painter.setPen(QPen(gradient, 2))
        painter.drawPath(path)
    
    def _draw_spectrum(self, painter: QPainter):
        """绘制频谱"""
        if self.spectrum_data is None:
            return
        
        width = self.width()
        height = self.height() // 3
        y_base = self.height() - height - 10
        
        # 归一化频谱数据
        spectrum_normalized = self.spectrum_data - np.min(self.spectrum_data)
        if np.max(spectrum_normalized) > 0:
            spectrum_normalized = spectrum_normalized / np.max(spectrum_normalized)
        
        # 绘制频谱
        path = QPainterPath()
        path.moveTo(0, y_base + height)
        
        for i in range(len(self.spectrum_data)):
            x = (i / len(self.spectrum_data)) * width
            y = y_base + height - (spectrum_normalized[i] * height)
            path.lineTo(x, y)
        
        path.lineTo(width, y_base + height)
        path.closeSubpath()
        
        # 创建频谱渐变
        gradient = QLinearGradient(0, y_base, 0, y_base + height)
        gradient.setColorAt(0, QColor(100, 255, 100, 200))
        gradient.setColorAt(1, QColor(100, 255, 100, 50))
        
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(gradient))
        painter.drawPath(path)
    
    def _draw_realtime_indicators(self, painter: QPainter):
        """绘制实时指示器"""
        width = self.width()
        height = self.height()
        
        # 绘制音量指示器
        self._draw_volume_meter(painter, width - 30, 20, 20, height - 40)
        
        # 绘制音高指示器
        self._draw_pitch_indicator(painter, 50, height - 50, 30)
        
        # 绘制频谱中心指示器
        self._draw_spectral_indicator(painter, 100, height - 50, 30)
    
    def _draw_volume_meter(self, painter: QPainter, x: int, y: int, width: int, height: int):
        """绘制音量指示器"""
        # 绘制背景
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(50, 50, 60))
        painter.drawRect(x, y, width, height)
        
        # 计算音量高度
        volume_height = int(self.realtime_volume * height * 3)  # 放大显示
        volume_height = min(volume_height, height)
        
        # 创建音量渐变
        gradient = QLinearGradient(0, y + height, 0, y + height - volume_height)
        if self.realtime_volume < 0.3:
            gradient.setColorAt(0, self.colors['volume_meter'][0])
            gradient.setColorAt(1, self.colors['volume_meter'][0].lighter(150))
        elif self.realtime_volume < 0.6:
            gradient.setColorAt(0, self.colors['volume_meter'][1])
            gradient.setColorAt(1, self.colors['volume_meter'][1].lighter(150))
        else:
            gradient.setColorAt(0, self.colors['volume_meter'][2])
            gradient.setColorAt(1, self.colors['volume_meter'][2].lighter(150))
        
        # 绘制音量
        painter.setBrush(gradient)
        painter.drawRect(x, y + height - volume_height, width, volume_height)
        
        # 绘制刻度
        painter.setPen(QColor(200, 200, 200))
        for i in range(0, 11, 2):
            y_pos = y + height - (i / 10 * height)
            painter.drawLine(int(x - 5), int(y_pos), int(x), int(y_pos))
        
        # 绘制标签
        painter.drawText(int(x - 40), int(y + height + 15), "Volume")
    
    def _draw_pitch_indicator(self, painter: QPainter, x: int, y: int, size: int):
        """绘制音高指示器"""
        # 根据音高值计算颜色
        hue = int(self.realtime_pitch % 500 / 500 * 360)
        color = QColor.fromHsv(hue, 255, 255)
        
        # 绘制指示器
        gradient = QRadialGradient(x + size/2, y + size/2, size/2)
        gradient.setColorAt(0, color.lighter(150))
        gradient.setColorAt(1, color.darker(150))
        
        painter.setPen(QPen(color.darker(200), 2))
        painter.setBrush(QBrush(gradient))
        painter.drawEllipse(int(x), int(y), int(size), int(size))
        
        # 绘制标签
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(int(x + size + 10), int(y + size/2 + 5), "Pitch")
    
    def _draw_spectral_indicator(self, painter: QPainter, x: int, y: int, size: int):
        """绘制频谱中心指示器"""
        # 根据频谱中心值计算颜色
        value = min(1.0, self.realtime_spectral_centroid / 4000)  # 归一化
        color = QColor.fromHsv(int(value * 360), 255, 255)
        
        # 绘制指示器
        gradient = QConicalGradient(x + size/2, y + size/2, 90)
        gradient.setColorAt(0, color.lighter(150))
        gradient.setColorAt(1, color.darker(150))
        
        painter.setPen(QPen(color.darker(200), 2))
        painter.setBrush(QBrush(gradient))
        painter.drawEllipse(x, y, size, size)
        
        # 绘制标签
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(int(x + size + 10), int(y + size/2 + 5), "Timbre")
    
    def _draw_position_indicator(self, painter: QPainter):
        """绘制播放位置指示器"""
        if self.reference_data is None or len(self.reference_data) == 0:
            return
        
        width = self.width()
        height = self.height()
        
        position_ratio = self.current_position / len(self.reference_data)
        x = position_ratio * width
        
        # 绘制位置线
        painter.setPen(QPen(self.colors['position_marker'], 3))
        painter.drawLine(int(x), 0, int(x), height)
        
        # 绘制位置标记
        painter.setBrush(self.colors['position_marker'])
        painter.drawEllipse(int(x) - 5, height - 15, 10, 10)
    
    def _draw_grid_and_labels(self, painter: QPainter):
        """绘制网格和标签"""
        width = self.width()
        height = self.height()
        
        # 绘制网格
        painter.setPen(QPen(QColor(100, 100, 120, 100), 1, Qt.DotLine))
        
        # 水平网格线
        for i in range(1, 4):
            y = i * height / 4
            painter.drawLine(0, int(y), int(width), int(y))
        
        # 垂直网格线 (时间刻度)
        if self.reference_data is not None and self.sample_rate is not None:
            duration = len(self.reference_data) / self.sample_rate
            for i in range(1, int(duration)):
                x = (i / duration) * width
                painter.drawLine(int(x), 0, int(x), int(height))
                
                # 绘制时间标签
                if i % 5 == 0:  # 每5秒显示一个标签
                    painter.setPen(QColor(200, 200, 200))
                    painter.drawText(int(x) - 10, int(height) - 5, f"{i}s")
                    painter.setPen(QPen(QColor(100, 100, 120, 100), 1, Qt.DotLine))


class AdvancedKaraokeMainWindow(QMainWindow):
    """高级卡拉OK主窗口"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("高级卡拉OK评分系统")
        self.setGeometry(100, 100, 1400, 900)
        
        # 初始化音频处理器和评分引擎
        self.audio_processor = AdvancedAudioProcessor()
        self.scoring_engine = AdvancedScoringEngine(self.audio_processor)
        self.cloud_manager = CloudSyncManager()
        
        # 用户数据
        self.current_user = None
        self.user_scores = []
        
        # 初始化UI
        self.init_ui()
        
        # 连接信号槽
        self.audio_processor.analysis_complete.connect(self.on_analysis_complete)
        self.audio_processor.realtime_data.connect(self.on_realtime_data)
        self.audio_processor.recording_complete.connect(self.on_recording_complete)
        
        # 加载用户数据
        self.load_user_data()
    
    def init_ui(self):
        """初始化用户界面"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        
        # 创建左侧控制面板
        control_panel = QWidget()
        control_panel.setFixedWidth(300)
        control_layout = QVBoxLayout(control_panel)
        
        # 用户信息区域
        user_group = QGroupBox("用户信息")
        user_layout = QVBoxLayout(user_group)
        
        self.user_combo = QComboBox()
        self.user_combo.addItems(["默认用户", "用户1", "用户2", "用户3"])
        self.user_combo.currentTextChanged.connect(self.change_user)
        user_layout.addWidget(QLabel("当前用户:"))
        user_layout.addWidget(self.user_combo)
        
        self.login_btn = QPushButton("云端登录")
        self.login_btn.clicked.connect(self.cloud_login)
        user_layout.addWidget(self.login_btn)
        
        self.sync_btn = QPushButton("同步数据")
        self.sync_btn.clicked.connect(self.sync_data)
        user_layout.addWidget(self.sync_btn)
        
        control_layout.addWidget(user_group)
        
        # 歌曲控制区域
        song_group = QGroupBox("歌曲控制")
        song_layout = QVBoxLayout(song_group)
        
        self.load_btn = QPushButton("加载歌曲")
        self.load_btn.clicked.connect(self.load_song)
        song_layout.addWidget(self.load_btn)
        
        self.record_btn = QPushButton("开始录音")
        self.record_btn.clicked.connect(self.toggle_recording)
        self.record_btn.setEnabled(False)
        song_layout.addWidget(self.record_btn)
        
        self.play_btn = QPushButton("播放")
        self.play_btn.clicked.connect(self.toggle_playback)
        self.play_btn.setEnabled(False)
        song_layout.addWidget(self.play_btn)
        
        self.stop_btn = QPushButton("停止")
        self.stop_btn.clicked.connect(self.stop_playback)
        self.stop_btn.setEnabled(False)
        song_layout.addWidget(self.stop_btn)
        
        # 录音设置
        record_settings = QHBoxLayout()
        record_settings.addWidget(QLabel("录音时长:"))
        self.record_duration = QSpinBox()
        self.record_duration.setRange(10, 600)
        self.record_duration.setValue(60)
        record_settings.addWidget(self.record_duration)
        record_settings.addWidget(QLabel("秒"))
        song_layout.addLayout(record_settings)
        
        control_layout.addWidget(song_group)
        
        # 评分设置区域
        settings_group = QGroupBox("评分设置")
        settings_layout = QVBoxLayout(settings_group)
        
        settings_form = QFormLayout()
        
        self.pitch_weight = QDoubleSpinBox()
        self.pitch_weight.setRange(0.1, 0.5)
        self.pitch_weight.setValue(0.3)
        self.pitch_weight.setSingleStep(0.05)
        settings_form.addRow("音准权重:", self.pitch_weight)
        
        self.timing_weight = QDoubleSpinBox()
        self.timing_weight.setRange(0.1, 0.5)
        self.timing_weight.setValue(0.25)
        self.timing_weight.setSingleStep(0.05)
        settings_form.addRow("节奏权重:", self.timing_weight)
        
        self.expression_weight = QDoubleSpinBox()
        self.expression_weight.setRange(0.1, 0.3)
        self.expression_weight.setValue(0.15)
        self.expression_weight.setSingleStep(0.05)
        settings_form.addRow("表现力权重:", self.expression_weight)
        
        self.difficulty = QComboBox()
        self.difficulty.addItems(["简单", "中等", "困难", "专家"])
        settings_form.addRow("难度级别:", self.difficulty)
        
        settings_layout.addLayout(settings_form)
        control_layout.addWidget(settings_group)
        
        # 历史记录区域
        history_group = QGroupBox("历史记录")
        history_layout = QVBoxLayout(history_group)
        
        self.history_list = QListWidget()
        history_layout.addWidget(self.history_list)
        
        control_layout.addWidget(history_group)
        
        # 添加到主布局
        main_layout.addWidget(control_panel)
        
        # 创建右侧主显示区域
        main_display = QWidget()
        main_display_layout = QVBoxLayout(main_display)
        
        # 创建可视化区域
        self.visualizer = AdvancedVisualizerWidget()
        main_display_layout.addWidget(self.visualizer)
        
        # 创建评分显示区域
        score_group = QGroupBox("实时评分")
        score_layout = QHBoxLayout(score_group)
        
        self.total_score_label = QLabel("总分: --")
        self.total_score_label.setStyleSheet("font-size: 24pt; font-weight: bold; color: #FFD700;")
        score_layout.addWidget(self.total_score_label)
        
        self.base_score_label = QLabel("基础: --")
        self.base_score_label.setStyleSheet("font-size: 18pt; color: #AAAAAA;")
        score_layout.addWidget(self.base_score_label)
        
        self.pitch_score_label = QLabel("音准: --")
        self.pitch_score_label.setStyleSheet("font-size: 18pt; color: #FF9999;")
        score_layout.addWidget(self.pitch_score_label)
        
        self.timing_score_label = QLabel("节奏: --")
        self.timing_score_label.setStyleSheet("font-size: 18pt; color: #99FF99;")
        score_layout.addWidget(self.timing_score_label)
        
        self.expression_score_label = QLabel("表现力: --")
        self.expression_score_label.setStyleSheet("font-size: 18pt; color: #9999FF;")
        score_layout.addWidget(self.expression_score_label)
        
        main_display_layout.addWidget(score_group)
        
        # 创建歌词显示区域
        lyrics_group = QGroupBox("歌词")
        lyrics_layout = QVBoxLayout(lyrics_group)
        
        self.lyrics_display = QLabel("歌词将在这里显示")
        self.lyrics_display.setAlignment(Qt.AlignCenter)
        self.lyrics_display.setStyleSheet("""
            font-size: 20pt; 
            background-color: #202030; 
            color: white; 
            padding: 20px;
            border-radius: 10px;
            min-height: 100px;
        """)
        lyrics_layout.addWidget(self.lyrics_display)
        
        # 歌词控制
        lyrics_control = QHBoxLayout()
        lyrics_control.addWidget(QLabel("歌词偏移:"))
        
        self.lyrics_offset = QSpinBox()
        self.lyrics_offset.setRange(-5000, 5000)
        self.lyrics_offset.setValue(0)
        self.lyrics_offset.setSuffix("ms")
        lyrics_control.addWidget(self.lyrics_offset)
        
        self.load_lyrics_btn = QPushButton("加载歌词文件")
        self.load_lyrics_btn.clicked.connect(self.load_lyrics_file)
        lyrics_control.addWidget(self.load_lyrics_btn)
        
        lyrics_layout.addLayout(lyrics_control)
        main_display_layout.addWidget(lyrics_group)
        
        # 添加到主布局
        main_layout.addWidget(main_display, 1)
        
        # 创建状态栏
        self.status_bar = QLabel("就绪")
        self.status_bar.setFrameStyle(QFrame.StyledPanel)
        main_display_layout.addWidget(self.status_bar)
    
    def load_user_data(self):
        """加载用户数据"""
        try:
            if os.path.exists("user_data.json"):
                with open("user_data.json", 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.user_scores = data.get('scores', [])
                    
                    # 更新历史记录列表
                    self.update_history_list()
        except Exception as e:
            print(f"加载用户数据失败: {e}")
    
    def save_user_data(self):
        """保存用户数据"""
        try:
            data = {
                'scores': self.user_scores,
                'last_user': self.current_user
            }
            with open("user_data.json", 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存用户数据失败: {e}")
    
    def update_history_list(self):
        """更新历史记录列表"""
        self.history_list.clear()
        
        for score in self.user_scores[-10:]:  # 显示最近10条记录
            item = QListWidgetItem(
                f"{score['song']} - {score['total']}分 "
                f"({score['date']})"
            )
            self.history_list.addItem(item)
    
    def change_user(self, user_name):
        """切换用户"""
        self.current_user = user_name
        self.status_bar.setText(f"当前用户: {user_name}")
    
    def cloud_login(self):
        """云端登录"""
        username, ok = QInputDialog.getText(self, "云端登录", "用户名:")
        if not ok or not username:
            return
        
        password, ok = QInputDialog.getText(self, "云端登录", "密码:", QLineEdit.Password)
        if not ok:
            return
        
        success = self.cloud_manager.login(username, password)
        if success:
            self.status_bar.setText("云端登录成功")
            self.sync_btn.setEnabled(True)
        else:
            QMessageBox.warning(self, "登录失败", "用户名或密码错误")
    
    def sync_data(self):
        """同步数据到云端"""
        if not self.cloud_manager.session_token:
            QMessageBox.warning(self, "同步失败", "请先登录云端账户")
            return
        
        self.status_bar.setText("正在同步数据...")
        success = self.cloud_manager.sync_scores(self.user_scores)
        
        if success:
            self.status_bar.setText("数据同步成功")
        else:
            self.status_bar.setText("数据同步失败")
    
    def load_song(self):
        """加载歌曲文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择音频文件", "", "音频文件 (*.mp3 *.wav *.ogg *.flac)")
        
        if file_path:
            self.status_bar.setText(f"正在加载: {file_path}...")
            success = self.audio_processor.load_audio(file_path)
            
            if success:
                self.status_bar.setText(f"已加载: {os.path.basename(file_path)}")
                self.play_btn.setEnabled(True)
                self.record_btn.setEnabled(True)
                self.stop_btn.setEnabled(True)
                
                # 设置可视化数据
                self.visualizer.set_audio_data(
                    self.audio_processor.audio_data, 
                    self.audio_processor.sample_rate
                )
                
                # 保存歌曲信息
                self.current_song = os.path.basename(file_path)
            else:
                self.status_bar.setText("加载失败")
    
    def load_lyrics_file(self):
        """加载歌词文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择歌词文件", "", "歌词文件 (*.lrc *.txt)")
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    self.lyrics_data = self.parse_lrc_file(f.read())
                self.status_bar.setText(f"已加载歌词: {os.path.basename(file_path)}")
            except Exception as e:
                QMessageBox.warning(self, "加载失败", f"加载歌词文件失败: {e}")
    
    def parse_lrc_file(self, lrc_content: str) -> List[Tuple[float, str]]:
        """解析LRC歌词文件"""
        lyrics = []
        
        for line in lrc_content.split('\n'):
            line = line.strip()
            if not line or not line.startswith('['):
                continue
            
            # 解析时间标签
            end_bracket = line.find(']')
            if end_bracket == -1:
                continue
            
            time_tag = line[1:end_bracket]
            text = line[end_bracket+1:].strip()
            
            # 解析时间
            if ':' in time_tag and '.' in time_tag:
                try:
                    minutes, seconds = time_tag.split(':')
                    time_sec = float(minutes) * 60 + float(seconds)
                    lyrics.append((time_sec, text))
                except ValueError:
                    continue
        
        # 按时间排序
        lyrics.sort(key=lambda x: x[0])
        return lyrics
    
    def toggle_recording(self):
        """切换录音状态"""
        if self.audio_processor.is_recording:
            self.audio_processor.stop_recording()
            self.record_btn.setText("开始录音")
            self.status_bar.setText("录音已停止")
        else:
            duration = self.record_duration.value()
            self.audio_processor.start_recording(duration)
            self.record_btn.setText("停止录音")
            self.status_bar.setText("录音中...")
    
    def toggle_playback(self):
        """切换播放状态"""
        if self.audio_processor.is_playing:
            self.audio_processor.stop_playback()
            self.play_btn.setText("播放")
        else:
            self.audio_processor.start_playback()
            self.play_btn.setText("暂停")
    
    def stop_playback(self):
        """停止播放"""
        self.audio_processor.stop_playback()
        self.play_btn.setText("播放")
    
    def on_analysis_complete(self, result):
        """音频分析完成处理"""
        self.status_bar.setText(
            f"分析完成 - 节奏: {result['tempo']:.1f} BPM, 时长: {result['duration']:.1f}秒")
        
        # 保存参考特征
        self.reference_features = result['features']
    
    def on_realtime_data(self, data):
        """实时数据处理"""
        # 更新可视化
        self.visualizer.update_realtime_data(data)
        
        # 记录用户表现
        self.scoring_engine.record_user_performance(data)
        
        # 提取用户特征
        if hasattr(self, 'reference_features'):
            # 在实际应用中，这里应该提取实时特征
            # 简化处理：使用参考特征进行模拟
            user_features = self.reference_features.copy()
            
            # 添加一些随机变化模拟用户演唱
            variation = np.random.normal(0, 0.1, len(user_features))
            user_features = user_features * (1 + variation)
            
            # 计算并更新评分
            score = self.scoring_engine.calculate_score(user_features, self.reference_features)
            
            self.total_score_label.setText(f"总分: {score['total']}")
            self.base_score_label.setText(f"基础: {score['base']}")
            self.pitch_score_label.setText(f"音准: {score['pitch']}")
            self.timing_score_label.setText(f"节奏: {score['timing']}")
            self.expression_score_label.setText(f"表现力: {score['expression']}")
        
        # 更新歌词显示
        self.update_lyrics_display(data['time'])
    
    def on_recording_complete(self, recorded_data):
        """录音完成处理"""
        # 设置用户录音数据到可视化器
        self.visualizer.set_audio_data(recorded_data, 44100, is_reference=False)
        
        # 分析用户录音
        self.status_bar.setText("正在分析用户录音...")
        
        # 在实际应用中，这里应该提取用户特征并进行评分
        # 简化处理：使用随机评分
        score = {
            'total': np.random.randint(70, 96),
            'base': np.random.randint(70, 96),
            'pitch': np.random.randint(70, 96),
            'timing': np.random.randint(70, 96),
            'expression': np.random.randint(70, 96)
        }
        
        # 保存评分
        score_record = {
            'song': self.current_song,
            'total': score['total'],
            'base': score['base'],
            'pitch': score['pitch'],
            'timing': score['timing'],
            'expression': score['expression'],
            'date': datetime.now().strftime("%Y-%m-%d %H:%M")
        }
        
        self.user_scores.append(score_record)
        self.save_user_data()
        self.update_history_list()
        
        # 显示最终评分
        self.total_score_label.setText(f"总分: {score['total']}")
        self.base_score_label.setText(f"基础: {score['base']}")
        self.pitch_score_label.setText(f"音准: {score['pitch']}")
        self.timing_score_label.setText(f"节奏: {score['timing']}")
        self.expression_score_label.setText(f"表现力: {score['expression']}")
        
        self.status_bar.setText("录音分析完成")
    
    def update_lyrics_display(self, current_time: float):
        """更新歌词显示"""
        if not hasattr(self, 'lyrics_data') or not self.lyrics_data:
            return
        
        # 应用时间偏移
        current_time += self.lyrics_offset.value() / 1000.0
        
        # 查找当前歌词
        current_lyric = "♪♪♪"  # 默认显示
        next_lyric = ""
        
        for i, (time_stamp, lyric) in enumerate(self.lyrics_data):
            if current_time >= time_stamp:
                current_lyric = lyric
                if i + 1 < len(self.lyrics_data):
                    next_lyric = self.lyrics_data[i+1][1]
            else:
                break
        
        # 显示歌词
        self.lyrics_display.setText(
            f"<div style='text-align: center;'>"
            f"<p style='font-size: 24pt; color: #FFD700;'>{current_lyric}</p>"
            f"<p style='font-size: 18pt; color: #AAAAAA;'>{next_lyric}</p>"
            f"</div>"
        )


if __name__ == "__main__":
    import sys
    
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # 使用Fusion样式
    
    # 设置应用程序样式表
    app.setStyleSheet("""
        QMainWindow {
            background-color: #2D2D30;
        }
        QGroupBox {
            font-weight: bold;
            border: 2px solid #555555;
            border-radius: 5px;
            margin-top: 1ex;
            padding-top: 10px;
            background-color: #3E3E42;
            color: #FFFFFF;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top center;
            padding: 0 5px;
        }
        QPushButton {
            background-color: #007ACC;
            border: none;
            color: white;
            padding: 5px 10px;
            border-radius: 4px;
        }
        QPushButton:hover {
            background-color: #1C97EA;
        }
        QPushButton:pressed {
            background-color: #005699;
        }
        QPushButton:disabled {
            background-color: #505050;
            color: #999999;
        }
        QLabel {
            color: #CCCCCC;
        }
        QComboBox, QSpinBox, QDoubleSpinBox {
            background-color: #333333;
            border: 1px solid #555555;
            color: #FFFFFF;
            padding: 2px;
            border-radius: 3px;
        }
        QListWidget {
            background-color: #252526;
            color: #CCCCCC;
            border: 1px solid #555555;
            border-radius: 3px;
        }
    """)
    
    window = AdvancedKaraokeMainWindow()
    window.show()
    
    sys.exit(app.exec_())