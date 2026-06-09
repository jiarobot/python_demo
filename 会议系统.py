import sys
import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Callable

from PyQt5.QtCore import (Qt, QObject, pyqtSignal, QTimer, QSize, QRect, 
                         QPoint, QByteArray, QBuffer, QIODevice)
from PyQt5.QtGui import (QImage, QPixmap, QPainter, QPen, QBrush, QColor, 
                        QFont, QIcon, QKeySequence)
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QGridLayout, QLabel, QPushButton, 
                            QTextEdit, QLineEdit, QListWidget, QListWidgetItem,
                            QSlider, QComboBox, QCheckBox, QSpinBox, QToolBar,
                            QAction, QMenu, QDialog, QMessageBox, QSplitter,
                            QFrame, QScrollArea, QSizePolicy, QFileDialog,
                            QInputDialog, QProgressBar, QStatusBar)

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MeetingSystem")

# 模拟视频和音频处理库
try:
    import cv2
    import numpy as np
    HAS_OPENCV = True
except ImportError:
    HAS_OPENCV = False
    logger.warning("OpenCV not installed, video features will be limited")

try:
    import pyaudio
    import wave
    HAS_PYAUDIO = True
except ImportError:
    HAS_PYAUDIO = False
    logger.warning("PyAudio not installed, audio features will be limited")


class VideoFrame:
    """视频帧数据类"""
    def __init__(self, frame_id: int, timestamp: datetime, image_data: QImage):
        self.frame_id = frame_id
        self.timestamp = timestamp
        self.image_data = image_data
        
    def to_jpeg_bytes(self, quality: int = 80) -> QByteArray:
        """将帧转换为JPEG字节数据"""
        byte_array = QByteArray()
        buffer = QBuffer(byte_array)
        buffer.open(QIODevice.WriteOnly)
        self.image_data.save(buffer, "JPEG", quality)
        return byte_array
    
    @staticmethod
    def from_jpeg_bytes(frame_id: int, timestamp: datetime, data: QByteArray) -> 'VideoFrame':
        """从JPEG字节数据创建视频帧"""
        image = QImage()
        image.loadFromData(data, "JPEG")
        return VideoFrame(frame_id, timestamp, image)


class AudioPacket:
    """音频数据包类"""
    def __init__(self, packet_id: int, timestamp: datetime, audio_data: bytes, 
                 sample_rate: int = 44100, channels: int = 1):
        self.packet_id = packet_id
        self.timestamp = timestamp
        self.audio_data = audio_data
        self.sample_rate = sample_rate
        self.channels = channels


class Participant:
    """参会者类"""
    def __init__(self, user_id: str, name: str, is_host: bool = False):
        self.user_id = user_id
        self.name = name
        self.is_host = is_host
        self.is_muted = False
        self.is_video_on = False
        self.is_screen_sharing = False
        self.connection_quality = 100  # 0-100百分比
        
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'user_id': self.user_id,
            'name': self.name,
            'is_host': self.is_host,
            'is_muted': self.is_muted,
            'is_video_on': self.is_video_on,
            'is_screen_sharing': self.is_screen_sharing,
            'connection_quality': self.connection_quality
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Participant':
        """从字典创建参会者"""
        participant = cls(data['user_id'], data['name'], data.get('is_host', False))
        participant.is_muted = data.get('is_muted', False)
        participant.is_video_on = data.get('is_video_on', False)
        participant.is_screen_sharing = data.get('is_screen_sharing', False)
        participant.connection_quality = data.get('connection_quality', 100)
        return participant


class VideoWidget(QLabel):
    """视频显示组件"""
    video_clicked = pyqtSignal(str)  # 发射用户ID
    
    def __init__(self, participant: Participant, parent=None):
        super().__init__(parent)
        self.participant = participant
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("background-color: black; border: 1px solid gray;")
        self.setMinimumSize(160, 120)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # 显示用户信息
        self.info_label = QLabel(self)
        self.info_label.setStyleSheet("background-color: rgba(0, 0, 0, 128); color: white; padding: 2px;")
        self.info_label.setText(f"{participant.name}\n{'静音' if participant.is_muted else ''}")
        self.info_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.info_label.adjustSize()
        
    def resizeEvent(self, event):
        """调整大小时重新定位信息标签"""
        super().resizeEvent(event)
        self.info_label.move(5, 5)
        
    def mousePressEvent(self, event):
        """点击事件"""
        super().mousePressEvent(event)
        self.video_clicked.emit(self.participant.user_id)
        
    def update_video_frame(self, frame: VideoFrame):
        """更新视频帧"""
        pixmap = QPixmap.fromImage(frame.image_data)
        if not pixmap.isNull():
            scaled_pixmap = pixmap.scaled(
                self.size(), 
                Qt.KeepAspectRatio, 
                Qt.SmoothTransformation
            )
            self.setPixmap(scaled_pixmap)
            
    def update_participant_info(self, participant: Participant):
        """更新参会者信息"""
        self.participant = participant
        self.info_label.setText(
            f"{participant.name}\n"
            f"{'静音' if participant.is_muted else ''}\n"
            f"{'屏幕共享中' if participant.is_screen_sharing else ''}"
        )
        self.info_label.adjustSize()


class WhiteboardWidget(QWidget):
    """白板组件"""
    drawing_data = pyqtSignal(dict)  # 发射绘图数据
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(400, 300)
        self.setStyleSheet("background-color: white; border: 1px solid gray;")
        
        # 绘图属性
        self.drawing = False
        self.last_point = QPoint()
        self.pen_color = Qt.black
        self.pen_width = 3
        self.history = []
        self.current_path = []
        
        # 临时图像
        self.temp_image = QImage(self.size(), QImage.Format_RGB32)
        self.temp_image.fill(Qt.white)
        
    def set_pen_color(self, color):
        """设置画笔颜色"""
        self.pen_color = color
        
    def set_pen_width(self, width):
        """设置画笔宽度"""
        self.pen_width = width
        
    def clear(self):
        """清除白板"""
        self.temp_image.fill(Qt.white)
        self.history.append(self.temp_image.copy())
        self.update()
        self.drawing_data.emit({"type": "clear"})
        
    def undo(self):
        """撤销上一步"""
        if self.history:
            self.temp_image = self.history.pop()
            self.update()
            self.drawing_data.emit({"type": "undo"})
            
    def mousePressEvent(self, event):
        """鼠标按下事件"""
        if event.button() == Qt.LeftButton:
            self.drawing = True
            self.last_point = event.pos()
            self.current_path = [{
                "type": "start",
                "x": event.pos().x(),
                "y": event.pos().y(),
                "color": self.pen_color.rgb(),
                "width": self.pen_width
            }]
            
    def mouseMoveEvent(self, event):
        """鼠标移动事件"""
        if event.buttons() & Qt.LeftButton and self.drawing:
            painter = QPainter(self.temp_image)
            painter.setPen(QPen(self.pen_color, self.pen_width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            painter.drawLine(self.last_point, event.pos())
            self.last_point = event.pos()
            self.update()
            
            # 记录路径
            self.current_path.append({
                "type": "move",
                "x": event.pos().x(),
                "y": event.pos().y()
            })
            
    def mouseReleaseEvent(self, event):
        """鼠标释放事件"""
        if event.button() == Qt.LeftButton and self.drawing:
            self.drawing = False
            self.history.append(self.temp_image.copy())
            
            # 发送绘图数据
            if len(self.current_path) > 1:
                self.drawing_data.emit({
                    "type": "draw",
                    "path": self.current_path
                })
                
    def paintEvent(self, event):
        """绘制事件"""
        painter = QPainter(self)
        painter.drawImage(QRect(0, 0, self.width(), self.height()), self.temp_image)
        
    def apply_drawing_data(self, data: Dict):
        """应用绘图数据"""
        if data["type"] == "clear":
            self.temp_image.fill(Qt.white)
            self.update()
        elif data["type"] == "undo":
            if self.history:
                self.temp_image = self.history.pop()
                self.update()
        elif data["type"] == "draw" and "path" in data:
            path = data["path"]
            if len(path) < 2:
                return
                
            # 设置画笔
            start_point = path[0]
            color = QColor(start_point["color"]) if "color" in start_point else self.pen_color
            width = start_point["width"] if "width" in start_point else self.pen_width
            
            painter = QPainter(self.temp_image)
            painter.setPen(QPen(color, width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            
            # 绘制路径
            prev_point = QPoint(start_point["x"], start_point["y"])
            for point in path[1:]:
                if point["type"] == "move":
                    current_point = QPoint(point["x"], point["y"])
                    painter.drawLine(prev_point, current_point)
                    prev_point = current_point
                    
            self.update()
            self.history.append(self.temp_image.copy())


class ChatWidget(QWidget):
    """聊天组件"""
    message_sent = pyqtSignal(str)  # 发射消息内容
    
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        
        # 消息显示区域
        self.message_area = QTextEdit()
        self.message_area.setReadOnly(True)
        layout.addWidget(self.message_area)
        
        # 输入区域
        input_layout = QHBoxLayout()
        self.message_input = QLineEdit()
        self.message_input.returnPressed.connect(self.send_message)
        input_layout.addWidget(self.message_input)
        
        self.send_button = QPushButton("发送")
        self.send_button.clicked.connect(self.send_message)
        input_layout.addWidget(self.send_button)
        
        layout.addLayout(input_layout)
        
    def send_message(self):
        """发送消息"""
        message = self.message_input.text().strip()
        if message:
            self.message_sent.emit(message)
            self.message_input.clear()
            
    def add_message(self, sender: str, message: str, is_me: bool = False):
        """添加消息到聊天区域"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        if is_me:
            formatted_message = f"[{timestamp}] <b>我</b>: {message}"
        else:
            formatted_message = f"[{timestamp}] <b>{sender}</b>: {message}"
            
        self.message_area.append(formatted_message)
        
    def add_system_message(self, message: str):
        """添加系统消息"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f'<font color="gray">[{timestamp}] 系统: {message}</font>'
        self.message_area.append(formatted_message)


class ParticipantsWidget(QWidget):
    """参会者列表组件"""
    participant_action = pyqtSignal(str, str)  # 发射用户ID和动作类型
    
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        
        # 标题
        title = QLabel("参会者")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title)
        
        # 参会者列表
        self.participants_list = QListWidget()
        layout.addWidget(self.participants_list)
        
        # 设置右键菜单
        self.participants_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.participants_list.customContextMenuRequested.connect(self.show_context_menu)
        
    def update_participants(self, participants: Dict[str, Participant]):
        """更新参会者列表"""
        self.participants_list.clear()
        
        for participant in participants.values():
            item = QListWidgetItem()
            item.setText(f"{participant.name} {'(主持人)' if participant.is_host else ''}")
            item.setData(Qt.UserRole, participant.user_id)
            
            # 设置图标和状态
            if participant.is_muted:
                item.setIcon(QIcon.fromTheme("audio-volume-muted"))
            elif participant.is_video_on:
                item.setIcon(QIcon.fromTheme("camera-on"))
            else:
                item.setIcon(QIcon.fromTheme("user-available"))
                
            self.participants_list.addItem(item)
            
    def show_context_menu(self, position):
        """显示右键菜单"""
        item = self.participants_list.itemAt(position)
        if not item:
            return
            
        user_id = item.data(Qt.UserRole)
        menu = QMenu()
        
        # 添加菜单项
        mute_action = menu.addAction("静音/取消静音")
        video_action = menu.addAction("关闭/开启视频")
        make_host_action = menu.addAction("设为主持人")
        remove_action = menu.addAction("移除会议")
        
        # 显示菜单并获取选择
        action = menu.exec_(self.participants_list.mapToGlobal(position))
        if action == mute_action:
            self.participant_action.emit(user_id, "mute")
        elif action == video_action:
            self.participant_action.emit(user_id, "video")
        elif action == make_host_action:
            self.participant_action.emit(user_id, "make_host")
        elif action == remove_action:
            self.participant_action.emit(user_id, "remove")


class VideoProcessor(QObject):
    """视频处理器"""
    frame_processed = pyqtSignal(VideoFrame)  # 发射处理后的视频帧
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_processing = False
        self.effects = {
            "normal": self.apply_normal,
            "grayscale": self.apply_grayscale,
            "blur": self.apply_blur,
            "sharpen": self.apply_sharpen
        }
        self.current_effect = "normal"
        
    def process_frame(self, frame: VideoFrame):
        """处理视频帧"""
        if not self.is_processing:
            self.frame_processed.emit(frame)
            return
            
        # 应用效果
        effect_func = self.effects.get(self.current_effect, self.apply_normal)
        processed_image = effect_func(frame.image_data)
        
        # 创建新帧
        processed_frame = VideoFrame(
            frame.frame_id,
            frame.timestamp,
            processed_image
        )
        
        self.frame_processed.emit(processed_frame)
        
    def set_effect(self, effect_name: str):
        """设置视频效果"""
        if effect_name in self.effects:
            self.current_effect = effect_name
            
    def set_processing(self, enabled: bool):
        """启用/禁用处理"""
        self.is_processing = enabled
        
    def apply_normal(self, image: QImage) -> QImage:
        """正常效果"""
        return image
        
    def apply_grayscale(self, image: QImage) -> QImage:
        """灰度效果"""
        if HAS_OPENCV:
            # 使用OpenCV处理
            ptr = image.bits()
            ptr.setsize(image.byteCount())
            arr = np.array(ptr).reshape(image.height(), image.width(), 4)
            gray = cv2.cvtColor(arr, cv2.COLOR_RGBA2GRAY)
            gray_rgba = cv2.cvtColor(gray, cv2.COLOR_GRAY2RGBA)
            return QImage(gray_rgba.data, image.width(), image.height(), QImage.Format_RGB32)
        else:
            # 使用Qt处理
            return image.convertToFormat(QImage.Format_Grayscale8)
            
    def apply_blur(self, image: QImage) -> QImage:
        """模糊效果"""
        if HAS_OPENCV:
            ptr = image.bits()
            ptr.setsize(image.byteCount())
            arr = np.array(ptr).reshape(image.height(), image.width(), 4)
            blurred = cv2.GaussianBlur(arr, (15, 15), 0)
            return QImage(blurred.data, image.width(), image.height(), QImage.Format_RGB32)
        else:
            # 简单的Qt模糊实现
            return image
            
    def apply_sharpen(self, image: QImage) -> QImage:
        """锐化效果"""
        if HAS_OPENCV:
            ptr = image.bits()
            ptr.setsize(image.byteCount())
            arr = np.array(ptr).reshape(image.height(), image.width(), 4)
            kernel = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]])
            sharpened = cv2.filter2D(arr, -1, kernel)
            return QImage(sharpened.data, image.width(), image.height(), QImage.Format_RGB32)
        else:
            return image


class AudioProcessor(QObject):
    """音频处理器"""
    audio_processed = pyqtSignal(AudioPacket)  # 发射处理后的音频数据包
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_processing = False
        self.effects = {
            "normal": self.apply_normal,
            "noise_suppression": self.apply_noise_suppression,
            "gain": self.apply_gain,
            "echo": self.apply_echo
        }
        self.current_effect = "normal"
        
    def process_audio(self, packet: AudioPacket):
        """处理音频数据包"""
        if not self.is_processing:
            self.audio_processed.emit(packet)
            return
            
        # 应用效果
        effect_func = self.effects.get(self.current_effect, self.apply_normal)
        processed_audio = effect_func(packet.audio_data)
        
        # 创建新数据包
        processed_packet = AudioPacket(
            packet.packet_id,
            packet.timestamp,
            processed_audio,
            packet.sample_rate,
            packet.channels
        )
        
        self.audio_processed.emit(processed_packet)
        
    def set_effect(self, effect_name: str):
        """设置音频效果"""
        if effect_name in self.effects:
            self.current_effect = effect_name
            
    def set_processing(self, enabled: bool):
        """启用/禁用处理"""
        self.is_processing = enabled
        
    def apply_normal(self, audio_data: bytes) -> bytes:
        """正常效果"""
        return audio_data
        
    def apply_noise_suppression(self, audio_data: bytes) -> bytes:
        """噪声抑制"""
        # 简化实现 - 实际应用中需要使用专业音频处理库
        return audio_data
        
    def apply_gain(self, audio_data: bytes) -> bytes:
        """增益效果"""
        # 简化实现
        return audio_data
        
    def apply_echo(self, audio_data: bytes) -> bytes:
        """回声效果"""
        # 简化实现
        return audio_data


class MeetingClient(QObject):
    """会议客户端核心类"""
    # 信号定义
    participant_joined = pyqtSignal(Participant)
    participant_left = pyqtSignal(str)  # user_id
    participant_updated = pyqtSignal(Participant)
    message_received = pyqtSignal(str, str)  # sender, message
    video_frame_received = pyqtSignal(str, VideoFrame)  # user_id, frame
    whiteboard_data_received = pyqtSignal(dict)  # drawing_data
    
    def __init__(self, user_id: str, user_name: str, is_host: bool = False):
        super().__init__()
        self.user_id = user_id
        self.user_name = user_name
        self.is_host = is_host
        
        self.participants = {}  # user_id -> Participant
        self.video_widgets = {}  # user_id -> VideoWidget
        self.is_connected = False
        
        # 添加自己作为参会者
        self.add_participant(Participant(user_id, user_name, is_host))
        
        # 初始化处理器
        self.video_processor = VideoProcessor()
        self.audio_processor = AudioProcessor()
        
        # 连接处理器信号
        self.video_processor.frame_processed.connect(self.send_video_frame)
        self.audio_processor.audio_processed.connect(self.send_audio_packet)
        
    def connect_to_meeting(self, meeting_id: str):
        """连接到会议"""
        # 模拟连接过程
        logger.info(f"Connecting to meeting {meeting_id}")
        self.is_connected = True
        logger.info("Connected successfully")
        
    def disconnect_from_meeting(self):
        """断开会议连接"""
        logger.info("Disconnecting from meeting")
        self.is_connected = False
        logger.info("Disconnected successfully")
        
    def add_participant(self, participant: Participant):
        """添加参会者"""
        self.participants[participant.user_id] = participant
        self.participant_joined.emit(participant)
        
    def remove_participant(self, user_id: str):
        """移除参会者"""
        if user_id in self.participants:
            del self.participants[user_id]
            self.participant_left.emit(user_id)
            
    def update_participant(self, participant: Participant):
        """更新参会者信息"""
        if participant.user_id in self.participants:
            self.participants[participant.user_id] = participant
            self.participant_updated.emit(participant)
            
    def send_message(self, message: str):
        """发送消息"""
        if self.is_connected:
            # 模拟网络发送
            logger.info(f"Sending message: {message}")
            # 这里应该通过网络发送消息，然后接收方会触发message_received信号
            # 模拟接收自己的消息
            self.message_received.emit(self.user_id, message)
            
    def send_video_frame(self, frame: VideoFrame):
        """发送视频帧"""
        if self.is_connected:
            # 模拟网络发送
            logger.debug(f"Sending video frame {frame.frame_id}")
            # 这里应该通过网络发送帧，然后接收方会触发video_frame_received信号
            # 模拟接收自己的帧
            self.video_frame_received.emit(self.user_id, frame)
            
    def send_audio_packet(self, packet: AudioPacket):
        """发送音频数据包"""
        if self.is_connected:
            # 模拟网络发送
            logger.debug(f"Sending audio packet {packet.packet_id}")
            
    def send_whiteboard_data(self, data: Dict):
        """发送白板数据"""
        if self.is_connected:
            # 模拟网络发送
            logger.info("Sending whiteboard data")
            # 模拟接收自己的数据
            self.whiteboard_data_received.emit(data)
            
    def toggle_mute(self):
        """切换静音状态"""
        my_participant = self.participants.get(self.user_id)
        if my_participant:
            my_participant.is_muted = not my_participant.is_muted
            self.update_participant(my_participant)
            
    def toggle_video(self):
        """切换视频状态"""
        my_participant = self.participants.get(self.user_id)
        if my_participant:
            my_participant.is_video_on = not my_participant.is_video_on
            self.update_participant(my_participant)
            
    def toggle_screen_share(self):
        """切换屏幕共享状态"""
        my_participant = self.participants.get(self.user_id)
        if my_participant:
            my_participant.is_screen_sharing = not my_participant.is_screen_sharing
            self.update_participant(my_participant)
            
    def make_host(self, user_id: str):
        """设为主持人"""
        if self.is_host and user_id in self.participants:
            # 取消原主持人的权限
            for participant in self.participants.values():
                if participant.is_host:
                    participant.is_host = False
                    self.update_participant(participant)
                    
            # 设置新主持人
            participant = self.participants[user_id]
            participant.is_host = True
            self.update_participant(participant)


class MeetingWindow(QMainWindow):
    """会议主窗口"""
    def __init__(self, user_id: str, user_name: str, meeting_id: str, is_host: bool = False):
        super().__init__()
        self.user_id = user_id
        self.user_name = user_name
        self.meeting_id = meeting_id
        self.is_host = is_host
        
        # 初始化客户端
        self.client = MeetingClient(user_id, user_name, is_host)
        
        # 设置UI
        self.setup_ui()
        self.setup_signals()
        
        # 连接到会议
        self.client.connect_to_meeting(meeting_id)
        
        # 启动模拟视频
        self.setup_video_capture()
        
    def setup_ui(self):
        """设置用户界面"""
        self.setWindowTitle(f"会议系统 - {self.meeting_id}")
        self.setGeometry(100, 100, 1200, 800)
        
        # 中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QHBoxLayout(central_widget)
        
        # 左侧视频区域
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        # 视频网格
        self.video_grid = QGridLayout()
        self.video_grid.setSpacing(5)
        
        # 添加自己的视频窗口
        my_video = VideoWidget(self.client.participants[self.user_id])
        my_video.video_clicked.connect(self.on_video_clicked)
        self.video_grid.addWidget(my_video, 0, 0)
        self.client.video_widgets[self.user_id] = my_video
        
        video_container = QWidget()
        video_container.setLayout(self.video_grid)
        
        # 可滚动的视频区域
        scroll_area = QScrollArea()
        scroll_area.setWidget(video_container)
        scroll_area.setWidgetResizable(True)
        left_layout.addWidget(scroll_area)
        
        # 控制工具栏
        control_bar = QToolBar()
        control_bar.setIconSize(QSize(24, 24))
        
        # 控制按钮
        self.mute_action = QAction(QIcon.fromTheme("audio-volume-high"), "静音/取消静音", self)
        self.mute_action.triggered.connect(self.client.toggle_mute)
        control_bar.addAction(self.mute_action)
        
        self.video_action = QAction(QIcon.fromTheme("camera-video"), "开启/关闭视频", self)
        self.video_action.triggered.connect(self.client.toggle_video)
        control_bar.addAction(self.video_action)
        
        self.screen_share_action = QAction(QIcon.fromTheme("screen-shared"), "共享屏幕", self)
        self.screen_share_action.triggered.connect(self.client.toggle_screen_share)
        control_bar.addAction(self.screen_share_action)
        
        control_bar.addSeparator()
        
        self.record_action = QAction(QIcon.fromTheme("media-record"), "开始录制", self)
        self.record_action.triggered.connect(self.toggle_recording)
        control_bar.addAction(self.record_action)
        
        self.settings_action = QAction(QIcon.fromTheme("settings-configure"), "设置", self)
        self.settings_action.triggered.connect(self.show_settings)
        control_bar.addAction(self.settings_action)
        
        left_layout.addWidget(control_bar)
        
        # 右侧边栏
        sidebar = QSplitter(Qt.Vertical)
        
        # 参会者列表
        self.participants_widget = ParticipantsWidget()
        sidebar.addWidget(self.participants_widget)
        
        # 聊天组件
        self.chat_widget = ChatWidget()
        sidebar.addWidget(self.chat_widget)
        
        # 白板组件
        self.whiteboard_widget = WhiteboardWidget()
        sidebar.addWidget(self.whiteboard_widget)
        
        # 设置边栏大小
        sidebar.setSizes([200, 300, 300])
        
        # 添加到主布局
        main_layout.addWidget(left_widget, 70)  # 70%宽度
        main_layout.addWidget(sidebar, 30)      # 30%宽度
        
        # 状态栏
        self.statusBar().showMessage(f"已连接到会议: {self.meeting_id} | 用户: {self.user_name}")
        
    def setup_signals(self):
        """设置信号连接"""
        # 参会者相关信号
        self.client.participant_joined.connect(self.on_participant_joined)
        self.client.participant_left.connect(self.on_participant_left)
        self.client.participant_updated.connect(self.on_participant_updated)
        
        # 消息相关信号
        self.client.message_received.connect(self.on_message_received)
        self.chat_widget.message_sent.connect(self.client.send_message)
        
        # 视频相关信号
        self.client.video_frame_received.connect(self.on_video_frame_received)
        
        # 白板相关信号
        self.whiteboard_widget.drawing_data.connect(self.client.send_whiteboard_data)
        self.client.whiteboard_data_received.connect(self.on_whiteboard_data_received)
        
        # 参会者操作信号
        self.participants_widget.participant_action.connect(self.on_participant_action)
        
    def setup_video_capture(self):
        """设置视频捕获"""
        if HAS_OPENCV:
            self.capture = cv2.VideoCapture(0)
            self.video_timer = QTimer()
            self.video_timer.timeout.connect(self.capture_frame)
            self.video_timer.start(33)  # ~30 FPS
            
    def capture_frame(self):
        """捕获视频帧"""
        if self.client.participants[self.user_id].is_video_on:
            ret, frame = self.capture.read()
            if ret:
                # 转换OpenCV帧到QImage
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb_frame.shape
                bytes_per_line = ch * w
                qt_image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
                
                # 创建视频帧并处理
                video_frame = VideoFrame(
                    frame_id=0,  # 在实际应用中应该有递增的帧ID
                    timestamp=datetime.now(),
                    image_data=qt_image
                )
                
                # 发送到处理器
                self.client.video_processor.process_frame(video_frame)
                
    def on_participant_joined(self, participant: Participant):
        """处理参会者加入"""
        # 创建视频窗口
        video_widget = VideoWidget(participant)
        video_widget.video_clicked.connect(self.on_video_clicked)
        
        # 添加到网格
        row = len(self.client.video_widgets) // 3
        col = len(self.client.video_widgets) % 3
        self.video_grid.addWidget(video_widget, row, col)
        
        # 保存引用
        self.client.video_widgets[participant.user_id] = video_widget
        
        # 更新参会者列表
        self.participants_widget.update_participants(self.client.participants)
        
        # 显示系统消息
        self.chat_widget.add_system_message(f"{participant.name} 加入了会议")
        
    def on_participant_left(self, user_id: str):
        """处理参会者离开"""
        # 移除视频窗口
        if user_id in self.client.video_widgets:
            video_widget = self.client.video_widgets[user_id]
            self.video_grid.removeWidget(video_widget)
            video_widget.deleteLater()
            del self.client.video_widgets[user_id]
            
        # 更新参会者列表
        self.participants_widget.update_participants(self.client.participants)
        
        # 显示系统消息
        participant_name = self.client.participants.get(user_id, Participant(user_id, "未知用户")).name
        self.chat_widget.add_system_message(f"{participant_name} 离开了会议")
        
    def on_participant_updated(self, participant: Participant):
        """处理参会者更新"""
        # 更新视频窗口
        if participant.user_id in self.client.video_widgets:
            video_widget = self.client.video_widgets[participant.user_id]
            video_widget.update_participant_info(participant)
            
        # 更新参会者列表
        self.participants_widget.update_participants(self.client.participants)
        
    def on_message_received(self, sender_id: str, message: str):
        """处理接收到的消息"""
        sender = self.client.participants.get(sender_id, Participant(sender_id, "未知用户"))
        is_me = sender_id == self.user_id
        self.chat_widget.add_message(sender.name, message, is_me)
        
    def on_video_frame_received(self, user_id: str, frame: VideoFrame):
        """处理接收到的视频帧"""
        if user_id in self.client.video_widgets:
            video_widget = self.client.video_widgets[user_id]
            video_widget.update_video_frame(frame)
            
    def on_whiteboard_data_received(self, data: Dict):
        """处理接收到的白板数据"""
        self.whiteboard_widget.apply_drawing_data(data)
        
    def on_video_clicked(self, user_id: str):
        """处理视频点击事件"""
        if user_id != self.user_id and self.is_host:
            # 主持人可以点击其他参会者的视频进行操作
            menu = QMenu(self)
            mute_action = menu.addAction("静音/取消静音")
            make_host_action = menu.addAction("设为主持人")
            remove_action = menu.addAction("移除会议")
            
            action = menu.exec_(QCursor.pos())
            if action == mute_action:
                self.client.participant_action.emit(user_id, "mute")
            elif action == make_host_action:
                self.client.participant_action.emit(user_id, "make_host")
            elif action == remove_action:
                self.client.participant_action.emit(user_id, "remove")
                
    def on_participant_action(self, user_id: str, action: str):
        """处理参会者操作"""
        if action == "mute":
            # 在实际应用中应该通过网络发送静音指令
            participant = self.client.participants.get(user_id)
            if participant:
                participant.is_muted = not participant.is_muted
                self.client.update_participant(participant)
        elif action == "video":
            # 在实际应用中应该通过网络发送视频控制指令
            participant = self.client.participants.get(user_id)
            if participant:
                participant.is_video_on = not participant.is_video_on
                self.client.update_participant(participant)
        elif action == "make_host" and self.is_host:
            self.client.make_host(user_id)
        elif action == "remove" and self.is_host:
            self.client.remove_participant(user_id)
            
    def toggle_recording(self):
        """切换录制状态"""
        # 实现录制功能
        pass
        
    def show_settings(self):
        """显示设置对话框"""
        dialog = QDialog(self)
        dialog.setWindowTitle("设置")
        dialog.setModal(True)
        layout = QVBoxLayout(dialog)
        
        # 视频设置
        video_group = QFrame()
        video_group.setFrameStyle(QFrame.StyledPanel)
        video_layout = QVBoxLayout(video_group)
        video_layout.addWidget(QLabel("视频设置"))
        
        # 视频效果选择
        effect_layout = QHBoxLayout()
        effect_layout.addWidget(QLabel("视频效果:"))
        effect_combo = QComboBox()
        effect_combo.addItems(["正常", "灰度", "模糊", "锐化"])
        effect_combo.currentTextChanged.connect(
            lambda text: self.client.video_processor.set_effect(text.lower())
        )
        effect_layout.addWidget(effect_combo)
        video_layout.addLayout(effect_layout)
        
        layout.addWidget(video_group)
        
        # 音频设置
        audio_group = QFrame()
        audio_group.setFrameStyle(QFrame.StyledPanel)
        audio_layout = QVBoxLayout(audio_group)
        audio_layout.addWidget(QLabel("音频设置"))
        
        # 音频效果选择
        audio_effect_layout = QHBoxLayout()
        audio_effect_layout.addWidget(QLabel("音频效果:"))
        audio_effect_combo = QComboBox()
        audio_effect_combo.addItems(["正常", "噪声抑制", "增益", "回声"])
        audio_effect_combo.currentTextChanged.connect(
            lambda text: self.client.audio_processor.set_effect(text.lower())
        )
        audio_effect_layout.addWidget(audio_effect_combo)
        audio_layout.addLayout(audio_effect_layout)
        
        layout.addWidget(audio_group)
        
        # 确定按钮
        ok_button = QPushButton("确定")
        ok_button.clicked.connect(dialog.accept)
        layout.addWidget(ok_button)
        
        dialog.exec_()
        
    def closeEvent(self, event):
        """处理窗口关闭事件"""
        reply = QMessageBox.question(
            self, "确认退出",
            "确定要退出会议吗?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            if HAS_OPENCV and hasattr(self, 'capture'):
                self.capture.release()
            self.client.disconnect_from_meeting()
            event.accept()
        else:
            event.ignore()


class MeetingSystem:
    """会议系统主类"""
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.current_window = None
        
    def start_meeting(self, user_id: str, user_name: str, meeting_id: str, is_host: bool = False):
        """启动会议"""
        self.current_window = MeetingWindow(user_id, user_name, meeting_id, is_host)
        self.current_window.show()
        return self.app.exec_()
        
    def join_meeting(self, user_id: str, user_name: str, meeting_id: str):
        """加入会议"""
        return self.start_meeting(user_id, user_name, meeting_id, False)
        
    def create_meeting(self, user_id: str, user_name: str):
        """创建会议"""
        meeting_id = f"meeting_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        return self.start_meeting(user_id, user_name, meeting_id, True)


# 使用示例
if __name__ == "__main__":
    # 创建会议系统实例
    meeting_system = MeetingSystem()
    
    # 模拟用户信息
    user_id = "user_001"
    user_name = "张三"
    
    # 创建并启动会议
    exit_code = meeting_system.create_meeting(user_id, user_name)
    
    # 退出程序
    sys.exit(exit_code)