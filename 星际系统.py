import sys
import random
import math
import numpy as np
from datetime import datetime, timedelta
from PyQt5.QtCore import (Qt, QTimer, QPoint, QPropertyAnimation, QEasingCurve, 
                         QTimeLine, QRectF, QPointF, QSize, QThread, pyqtSignal)
from PyQt5.QtGui import (QPainter, QColor, QFont, QLinearGradient, QPen, QBrush, 
                        QRadialGradient, QConicalGradient, QImage, QPixmap, QPainterPath,
                        QMatrix4x4, QVector3D, QIcon)
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QPushButton, QLabel, QSlider, QProgressBar, QFrame, QGroupBox,
                            QGridLayout, QTextEdit, QListWidget, QListWidgetItem, QSplitter,
                            QTabWidget, QComboBox, QSpinBox, QDoubleSpinBox, QCheckBox,
                            QLineEdit, QToolBar, QStatusBar, QAction, QFileDialog, QMessageBox,
                            QDockWidget, QTreeWidget, QTreeWidgetItem, QHeaderView, QSizePolicy,
                            QGraphicsView, QGraphicsScene, QGraphicsItem, QGraphicsRectItem,
                            QStyleOptionGraphicsItem, QOpenGLWidget, QGraphicsEffect)

# 导入科学计算和可视化所需的库
try:
    import pyqtgraph as pg
    from pyqtgraph import PlotWidget, PlotItem
    HAS_PYQTGRAPH = True
except ImportError:
    HAS_PYQTGRAPH = False
    print("警告: 未安装pyqtgraph，部分可视化功能将不可用")

# 导入3D可视化所需的库
try:
    from PyQt5.QtDataVisualization import Q3DScatter, Q3DCamera, Q3DTheme, QScatter3DSeries, QScatterDataProxy
    HAS_QT3D = True
except ImportError:
    HAS_QT3D = False
    print("警告: 未安装QtDataVisualization，3D星空可视化功能将不可用")

class StellarButton(QPushButton):
    """星际风格按钮"""
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setMinimumHeight(40)
        self.setFont(QFont("Arial", 10, QFont.Bold))
        self.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #6a00ff, stop: 0.5 #8e2de2, stop: 1 #4a00e0);
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px;
            }
            QPushButton:hover {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #8e2de2, stop: 0.5 #6a00ff, stop: 1 #8e2de2);
            }
            QPushButton:pressed {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #4a00e0, stop: 0.5 #6a00ff, stop: 1 #4a00e0);
            }
        """)
        
        # 添加点击动画效果
        self.animation = QPropertyAnimation(self, b"geometry")
        self.animation.setDuration(150)
        self.animation.setEasingCurve(QEasingCurve.OutQuad)
        
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # 创建缩小动画
            self.animation.setStartValue(self.geometry())
            self.animation.setEndValue(self.geometry().adjusted(2, 2, -2, -2))
            self.animation.start()
        super().mousePressEvent(event)
        
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            # 恢复原状
            self.animation.setStartValue(self.geometry())
            self.animation.setEndValue(self.geometry().adjusted(-2, -2, 2, 2))
            self.animation.start()
        super().mouseReleaseEvent(event)

class StarFieldBackground(QWidget):
    """星空背景组件"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.stars = []
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_stars)
        self.timer.start(50)  # 每50毫秒更新一次
        
        # 初始化星星
        for _ in range(100):
            self.add_star()
    
    def add_star(self):
        x = random.randint(0, self.width() if self.width() > 0 else 800)
        y = random.randint(0, self.height() if self.height() > 0 else 600)
        size = random.randint(1, 3)
        speed = random.uniform(0.5, 2.0)
        self.stars.append({"x": x, "y": y, "size": size, "speed": speed})
    
    def update_stars(self):
        # 移动星星
        for star in self.stars:
            star["x"] -= star["speed"]
            if star["x"] < 0:
                star["x"] = self.width() if self.width() > 0 else 800
                star["y"] = random.randint(0, self.height() if self.height() > 0 else 600)
        
        self.update()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 绘制星空背景
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0, QColor(10, 10, 30))
        gradient.setColorAt(1, QColor(5, 5, 15))
        painter.fillRect(self.rect(), gradient)
        
        # 绘制星星
        for star in self.stars:
            brightness = int(200 + 55 * (star["speed"] / 2.0))
            painter.setPen(QColor(brightness, brightness, 255, 200))
            painter.setBrush(QColor(brightness, brightness, 255, 100))
            painter.drawEllipse(QPoint(int(star["x"]), int(star["y"])), star["size"], star["size"])
    
    def resizeEvent(self, event):
        # 调整窗口大小时重新生成星星
        if self.width() > 0 and self.height() > 0:
            self.stars = []
            for _ in range(100):
                self.add_star()
        super().resizeEvent(event)

class StellarParticleSystem(QWidget):
    """高级粒子系统 - 用于创建星际尘埃、星云等效果"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.particles = []
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_particles)
        self.timer.start(30)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
    def add_particle(self, x, y, type="star"):
        """添加粒子"""
        if type == "star":
            size = random.uniform(0.5, 3.0)
            speed = random.uniform(0.1, 0.5)
            life = random.randint(100, 300)
            color = QColor(255, 255, 200, 200)
        elif type == "nebula":
            size = random.uniform(2.0, 8.0)
            speed = random.uniform(0.05, 0.2)
            life = random.randint(200, 500)
            hue = random.randint(200, 300)  # 紫色到蓝色范围
            color = QColor.fromHsv(hue, 150, 255, 100)
        else:
            size = random.uniform(1.0, 5.0)
            speed = random.uniform(0.1, 0.8)
            life = random.randint(50, 150)
            color = QColor(200, 200, 255, 150)
            
        angle = random.uniform(0, 2 * math.pi)
        vx = math.cos(angle) * speed
        vy = math.sin(angle) * speed
        
        self.particles.append({
            'x': x, 'y': y, 'vx': vx, 'vy': vy, 
            'size': size, 'life': life, 'max_life': life,
            'color': color, 'type': type
        })
    
    def update_particles(self):
        """更新粒子状态"""
        for particle in self.particles[:]:
            particle['x'] += particle['vx']
            particle['y'] += particle['vy']
            particle['life'] -= 1
            
            # 移除生命结束的粒子
            if particle['life'] <= 0:
                self.particles.remove(particle)
                
        self.update()
    
    def paintEvent(self, event):
        """绘制粒子"""
        if not self.particles:
            return
            
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        for particle in self.particles:
            # 计算透明度基于剩余生命值
            alpha = int(255 * (particle['life'] / particle['max_life']))
            color = particle['color']
            color.setAlpha(alpha)
            
            painter.setPen(Qt.NoPen)
            painter.setBrush(color)
            
            # 绘制粒子
            size = particle['size']
            painter.drawEllipse(QPointF(particle['x'], particle['y']), size, size)
            
            # 为星云粒子添加光晕效果
            if particle['type'] == "nebula":
                gradient = QRadialGradient(particle['x'], particle['y'], size * 3)
                gradient.setColorAt(0, QColor(color.red(), color.green(), color.blue(), 50))
                gradient.setColorAt(1, QColor(color.red(), color.green(), color.blue(), 0))
                
                painter.setBrush(QBrush(gradient))
                painter.drawEllipse(QPointF(particle['x'], particle['y']), size * 3, size * 3)

class QuantumCommunicationSimulator(QThread):
    """量子通信模拟器 - 在后台线程中运行"""
    message_received = pyqtSignal(str, str)  # 信号: 发送者, 消息内容
    
    def __init__(self):
        super().__init__()
        self.messages = [
            ("星际舰队指挥部", "所有单位进入一级战备状态"),
            ("科研空间站", "发现新的宜居行星，坐标: X-734, Y-289"),
            ("资源管理AI", "第7矿区资源已枯竭，建议转移到第9矿区"),
            ("深空探测站", "检测到异常空间波动，可能为未知文明活动"),
            ("导航系统", "跃迁通道已稳定，可以安全通过"),
            ("防御系统", "能量护盾强度降至65%，需要补充能源"),
            ("医疗舱", "船员健康状况良好，无异常报告"),
            ("工程部", "曲速引擎维护完成，效率提升12%")
        ]
        self.running = True
        
    def run(self):
        """线程主循环"""
        while self.running:
            # 随机间隔发送消息
            delay = random.randint(5000, 15000)
            self.msleep(delay)
            
            if not self.running:
                break
                
            # 随机选择一条消息发送
            sender, message = random.choice(self.messages)
            self.message_received.emit(sender, message)
    
    def stop(self):
        """停止线程"""
        self.running = False
        self.wait()

class StellarAIAssistant(QWidget):
    """星际AI助手组件"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.responses = [
            "正在分析请求...",
            "访问中央数据库...",
            "计算最优解决方案...",
            "执行系统诊断...",
            "生成战略建议...",
            "模拟可能的结果...",
            "联系专家系统...",
            "验证假设..."
        ]
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # 标题
        title = QLabel("星际AI助手 - AURORA")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("""
            color: #6accef; 
            font-size: 16px; 
            font-weight: bold;
            background-color: rgba(30, 30, 60, 180);
            padding: 10px;
            border-radius: 5px;
        """)
        layout.addWidget(title)
        
        # 对话显示区域
        self.chat_display = QTextEdit()
        self.chat_display.setStyleSheet("""
            QTextEdit {
                background-color: rgba(20, 20, 40, 200);
                color: #aaccff;
                border: 1px solid #4488ff;
                border-radius: 5px;
                font-family: 'Arial';
                font-size: 12px;
            }
        """)
        self.chat_display.setReadOnly(True)
        layout.addWidget(self.chat_display)
        
        # 输入区域
        input_layout = QHBoxLayout()
        
        self.input_field = QLineEdit()
        self.input_field.setStyleSheet("""
            QLineEdit {
                background-color: rgba(30, 30, 60, 200);
                color: #ffffff;
                border: 1px solid #4488ff;
                border-radius: 3px;
                padding: 5px;
            }
        """)
        self.input_field.setPlaceholderText("输入您的问题或命令...")
        self.input_field.returnPressed.connect(self.process_input)
        input_layout.addWidget(self.input_field)
        
        send_btn = StellarButton("发送")
        send_btn.clicked.connect(self.process_input)
        input_layout.addWidget(send_btn)
        
        layout.addLayout(input_layout)
        
        # 添加初始消息
        self.add_message("AURORA", "您好，指挥官。我是您的星际AI助手AURORA，随时为您提供支持。")
        
    def add_message(self, sender, message):
        """添加消息到对话区域"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        if sender == "AURORA":
            formatted_message = f'<div style="color: #6accef; margin: 5px;">[{timestamp}] <b>{sender}:</b> {message}</div>'
        else:
            formatted_message = f'<div style="color: #ffffff; margin: 5px;">[{timestamp}] <b>{sender}:</b> {message}</div>'
        
        self.chat_display.append(formatted_message)
        self.chat_display.verticalScrollBar().setValue(
            self.chat_display.verticalScrollBar().maximum()
        )
        
    def process_input(self):
        """处理用户输入"""
        user_input = self.input_field.text().strip()
        if not user_input:
            return
            
        self.add_message("您", user_input)
        self.input_field.clear()
        
        # 模拟AI思考过程
        QTimer.singleShot(1000, lambda: self.ai_response(user_input))
        
    def ai_response(self, user_input):
        """生成AI响应"""
        # 显示"思考中"的消息
        thinking_msg = random.choice(self.responses)
        self.add_message("AURORA", thinking_msg)
        
        # 延迟后发送实际响应
        QTimer.singleShot(2000, lambda: self.send_final_response(user_input))
        
    def send_final_response(self, user_input):
        """发送最终响应"""
        user_input = user_input.lower()
        
        if any(word in user_input for word in ["状态", "情况", "报告"]):
            response = "所有系统运行正常。能源水平92%，防御系统就绪，导航系统校准完成。"
        elif any(word in user_input for word in ["威胁", "危险", "敌人"]):
            response = "未检测到即时威胁。周边星域安全等级：绿色。建议保持常规巡逻。"
        elif any(word in user_input for word in ["资源", "矿物", "能源"]):
            response = "当前资源储量：氦-3: 85%，稀有金属: 72%，水晶: 68%。建议优先补充水晶储备。"
        elif any(word in user_input for word in ["任务", "目标", "使命"]):
            response = "主要任务：探索X-734星域，建立前哨站。当前进度：42%。下一步建议：派遣侦察队调查异常能量信号。"
        elif any(word in user_input for word in ["帮助", "支持", "怎么办"]):
            response = "我可以协助您进行系统监控、资源管理、战略规划和科学研究。请告诉我您需要哪方面的帮助。"
        else:
            response = "请求已接收。需要更多上下文来提供精确回答。您可以询问关于系统状态、资源情况或任务进展的信息。"
            
        self.add_message("AURORA", response)

class CosmicMap3D(QWidget):
    """3D宇宙星图组件"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
        # 初始化星体数据
        self.stars = []
        self.generate_star_map()
        
        # 设置动画定时器
        self.rotation_timer = QTimer(self)
        self.rotation_timer.timeout.connect(self.rotate_map)
        self.rotation_timer.start(50)
        
        self.rotation_angle = 0
        self.zoom_level = 1.0
        
    def setup_ui(self):
        self.main_layout = QVBoxLayout(self)
        
        # 控制栏
        control_layout = QHBoxLayout()
        
        zoom_in_btn = StellarButton("放大")
        zoom_in_btn.clicked.connect(self.zoom_in)
        control_layout.addWidget(zoom_in_btn)
        
        zoom_out_btn = StellarButton("缩小")
        zoom_out_btn.clicked.connect(self.zoom_out)
        control_layout.addWidget(zoom_out_btn)
        
        control_layout.addStretch()
        
        # 显示模式选择
        mode_label = QLabel("显示模式:")
        mode_label.setStyleSheet("color: #aabbcc;")
        control_layout.addWidget(mode_label)
        
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["星域图", "资源分布", "战略视图", "跃迁路线"])
        self.mode_combo.setStyleSheet("""
            QComboBox {
                background-color: rgba(30, 30, 60, 200);
                color: #ffffff;
                border: 1px solid #4488ff;
                border-radius: 3px;
                padding: 5px;
            }
        """)
        control_layout.addWidget(self.mode_combo)
        
        self.main_layout.addLayout(control_layout)
        
        # 星图显示区域
        self.map_container = QWidget()
        self.map_container.setStyleSheet("background-color: rgba(10, 10, 20, 200); border-radius: 5px;")
        self.map_layout = QVBoxLayout(self.map_container)
        
        # 如果没有3D支持，使用2D替代
        if not HAS_QT3D:
            self.star_map_2d = StarMap2D()
            self.map_layout.addWidget(self.star_map_2d)
        else:
            # 这里可以添加真正的3D星图实现
            placeholder = QLabel("3D星图可视化区域")
            placeholder.setAlignment(Qt.AlignCenter)
            placeholder.setStyleSheet("color: #6688ff; font-size: 16px; padding: 40px;")
            self.map_layout.addWidget(placeholder)
        
        self.main_layout.addWidget(self.map_container)
        
    def generate_star_map(self):
        """生成随机星图数据"""
        for _ in range(200):
            distance = random.uniform(0.2, 5.0)
            angle = random.uniform(0, 2 * math.pi)
            elevation = random.uniform(-1.0, 1.0)
            
            # 计算3D位置
            x = distance * math.cos(angle)
            y = distance * math.sin(angle)
            z = elevation
            
            # 随机星体属性
            star_type = random.choice(["G", "K", "M", "F", "A", "B", "O"])
            size = random.uniform(0.5, 3.0)
            
            # 根据星型确定颜色
            if star_type in ["O", "B"]:
                color = QColor(150, 180, 255)  # 蓝色
            elif star_type in ["A", "F"]:
                color = QColor(220, 220, 255)  # 白色
            elif star_type == "G":
                color = QColor(255, 230, 150)  # 黄色
            elif star_type == "K":
                color = QColor(255, 180, 100)  # 橙色
            else:  # M型
                color = QColor(255, 100, 80)   # 红色
                
            # 随机资源丰富度
            resources = random.choice(["丰富", "中等", "贫瘠", "未知"])
            
            self.stars.append({
                'x': x, 'y': y, 'z': z,
                'type': star_type, 'size': size,
                'color': color, 'resources': resources,
                'name': f"ST-{random.randint(1000, 9999)}"
            })
    
    def rotate_map(self):
        """旋转星图"""
        self.rotation_angle = (self.rotation_angle + 0.5) % 360
        if not HAS_QT3D and hasattr(self, 'star_map_2d'):
            self.star_map_2d.rotation_angle = self.rotation_angle
            self.star_map_2d.update()
    
    def zoom_in(self):
        """放大星图"""
        self.zoom_level = min(3.0, self.zoom_level + 0.1)
        if not HAS_QT3D and hasattr(self, 'star_map_2d'):
            self.star_map_2d.zoom_level = self.zoom_level
            self.star_map_2d.update()
    
    def zoom_out(self):
        """缩小星图"""
        self.zoom_level = max(0.5, self.zoom_level - 0.1)
        if not HAS_QT3D and hasattr(self, 'star_map_2d'):
            self.star_map_2d.zoom_level = self.zoom_level
            self.star_map_2d.update()

class StarMap2D(QWidget):
    """2D星图替代实现"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.rotation_angle = 0
        self.zoom_level = 1.0
        self.stars = []
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 绘制黑色背景
        painter.fillRect(self.rect(), QColor(10, 10, 20))
        
        # 绘制星空背景
        for _ in range(100):
            x = random.randint(0, self.width())
            y = random.randint(0, self.height())
            size = random.randint(1, 2)
            brightness = random.randint(100, 200)
            painter.setPen(QColor(brightness, brightness, brightness))
            painter.drawEllipse(x, y, size, size)
        
        # 绘制中心点（代表当前位置）
        center_x, center_y = self.width() / 2, self.height() / 2
        painter.setPen(QPen(QColor(0, 200, 255), 2))
        painter.drawEllipse(QPointF(center_x, center_y), 5, 5)
        
        # 绘制星体
        for star in self.stars:
            # 简化的2D投影
            angle = self.rotation_angle * math.pi / 180
            x = center_x + star['x'] * 50 * self.zoom_level * math.cos(angle) - star['z'] * 20
            y = center_y + star['y'] * 50 * self.zoom_level * math.sin(angle) - star['z'] * 20
            
            # 只绘制在可见范围内的星体
            if 0 <= x <= self.width() and 0 <= y <= self.height():
                size = star['size'] * 3 * self.zoom_level
                color = star['color']
                
                # 绘制星体
                painter.setPen(Qt.NoPen)
                painter.setBrush(color)
                painter.drawEllipse(QPointF(x, y), size, size)
                
                # 绘制光晕
                gradient = QRadialGradient(x, y, size * 2)
                gradient.setColorAt(0, QColor(color.red(), color.green(), color.blue(), 50))
                gradient.setColorAt(1, QColor(color.red(), color.green(), color.blue(), 0))
                
                painter.setBrush(QBrush(gradient))
                painter.drawEllipse(QPointF(x, y), size * 2, size * 2)
                
                # 绘制星体名称（只对较大的星体）
                if size > 3:
                    painter.setPen(QColor(200, 200, 200))
                    painter.drawText(QRectF(x + size + 2, y - 10, 60, 20), Qt.AlignLeft, star['name'])

class MultiDimensionalAnalyzer(QWidget):
    """多维度数据分析器"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.generate_sample_data()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # 标题
        title = QLabel("多维度数据分析中心")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("""
            color: #6accef; 
            font-size: 16px; 
            font-weight: bold;
            background-color: rgba(30, 30, 60, 180);
            padding: 10px;
            border-radius: 5px;
            margin-bottom: 10px;
        """)
        layout.addWidget(title)
        
        # 如果没有pyqtgraph，显示警告
        if not HAS_PYQTGRAPH:
            warning = QLabel("需要安装pyqtgraph库以启用数据可视化功能")
            warning.setAlignment(Qt.AlignCenter)
            warning.setStyleSheet("color: #ff6666; font-size: 14px; padding: 20px;")
            layout.addWidget(warning)
            return
            
        # 创建图表区域
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground((30, 30, 60, 200))
        self.plot_widget.showGrid(x=True, y=True)
        self.plot_widget.setLabel('left', '数值', color='#aaccff')
        self.plot_widget.setLabel('bottom', '时间', color='#aaccff')
        self.plot_widget.getAxis('left').setPen(pg.mkPen(color='#6688ff'))
        self.plot_widget.getAxis('bottom').setPen(pg.mkPen(color='#6688ff'))
        
        layout.addWidget(self.plot_widget)
        
        # 控制按钮
        control_layout = QHBoxLayout()
        
        self.start_btn = StellarButton("开始分析")
        self.start_btn.clicked.connect(self.start_analysis)
        control_layout.addWidget(self.start_btn)
        
        self.pause_btn = StellarButton("暂停")
        self.pause_btn.clicked.connect(self.pause_analysis)
        control_layout.addWidget(self.pause_btn)
        
        control_layout.addStretch()
        
        # 数据分析类型选择
        analysis_label = QLabel("分析类型:")
        analysis_label.setStyleSheet("color: #aabbcc;")
        control_layout.addWidget(analysis_label)
        
        self.analysis_combo = QComboBox()
        self.analysis_combo.addItems(["能源波动", "空间异常", "资源预测", "威胁评估"])
        self.analysis_combo.setStyleSheet("""
            QComboBox {
                background-color: rgba(30, 30, 60, 200);
                color: #ffffff;
                border: 1px solid #4488ff;
                border-radius: 3px;
                padding: 5px;
            }
        """)
        self.analysis_combo.currentTextChanged.connect(self.change_analysis_type)
        control_layout.addWidget(self.analysis_combo)
        
        layout.addLayout(control_layout)
        
        # 初始化定时器
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_plot)
        self.analysis_active = False
        
    def generate_sample_data(self):
        """生成示例数据"""
        self.time_data = list(range(100))
        self.energy_data = [math.sin(x/10) * 0.5 + 0.5 + random.uniform(-0.1, 0.1) for x in self.time_data]
        self.anomaly_data = [math.cos(x/8) * 0.3 + 0.5 + random.uniform(-0.15, 0.15) for x in self.time_data]
        self.resource_data = [0.6 + math.sin(x/12) * 0.2 + random.uniform(-0.05, 0.05) for x in self.time_data]
        self.threat_data = [max(0, min(1, 0.3 + math.sin(x/15) * 0.4 + random.uniform(-0.1, 0.1))) for x in self.time_data]
        
        self.current_data = self.energy_data
        self.current_index = 0
        
    def start_analysis(self):
        """开始数据分析"""
        if not HAS_PYQTGRAPH:
            return
            
        self.analysis_active = True
        self.timer.start(100)  # 每100毫秒更新一次
        
    def pause_analysis(self):
        """暂停数据分析"""
        self.analysis_active = False
        self.timer.stop()
        
    def change_analysis_type(self, analysis_type):
        """更改分析类型"""
        if analysis_type == "能源波动":
            self.current_data = self.energy_data
        elif analysis_type == "空间异常":
            self.current_data = self.anomaly_data
        elif analysis_type == "资源预测":
            self.current_data = self.resource_data
        elif analysis_type == "威胁评估":
            self.current_data = self.threat_data
            
        self.current_index = 0
        if self.analysis_active:
            self.plot_widget.clear()
        
    def update_plot(self):
        """更新图表"""
        if not HAS_PYQTGRAPH or not self.analysis_active:
            return
            
        if self.current_index >= len(self.current_data):
            self.current_index = 0
            
        # 绘制数据
        x = self.time_data[:self.current_index+1]
        y = self.current_data[:self.current_index+1]
        
        self.plot_widget.clear()
        pen = pg.mkPen(color=(102, 136, 255), width=2)
        self.plot_widget.plot(x, y, pen=pen)
        
        self.current_index += 1

class AdvancedStellarToolkit(QMainWindow):
    """增强版星际工具库主窗口"""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("星际时代高级系统工具库")
        self.setGeometry(100, 100, 1400, 900)
        
        # 设置中央部件
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # 创建星空背景
        self.starfield = StarFieldBackground()
        self.starfield_layout = QHBoxLayout(self.central_widget)
        self.starfield_layout.addWidget(self.starfield)
        
        # 初始化UI
        self.setup_ui()
        
        # 初始化量子通信模拟器
        self.quantum_com = QuantumCommunicationSimulator()
        self.quantum_com.message_received.connect(self.handle_quantum_message)
        self.quantum_com.start()
        
        # 创建状态栏
        self.setup_statusbar()
        
    def setup_ui(self):
        # 创建主选项卡
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #444477;
                background: rgba(30, 30, 60, 180);
                border-radius: 5px;
            }
            QTabBar::tab {
                background: rgba(40, 40, 80, 200);
                color: #aabbcc;
                padding: 8px 15px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background: rgba(60, 60, 120, 220);
                color: #ffffff;
            }
        """)
        
        self.starfield_layout.addWidget(self.tab_widget)
        
        # 添加各个功能选项卡
        self.setup_dashboard_tab()
        self.setup_navigation_tab()
        self.setup_analysis_tab()
        self.setup_communication_tab()
        self.setup_systems_tab()
        
    def setup_dashboard_tab(self):
        """设置仪表板选项卡"""
        dashboard_tab = QWidget()
        layout = QVBoxLayout(dashboard_tab)
        
        # 标题
        title = QLabel("星际指挥中心仪表板")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #6accef; font-size: 24px; font-weight: bold; margin: 10px;")
        layout.addWidget(title)
        
        # 系统状态网格
        status_grid = QGridLayout()
        
        # 创建多个系统状态指示器
        systems = [
            ("推进系统", 85, "#ffaa00"),
            ("生命支持", 92, "#00cc66"),
            ("武器系统", 78, "#ff4444"),
            ("传感器", 88, "#44aaff"),
            ("通讯系统", 91, "#aa44ff"),
            ("护盾", 75, "#ff44aa")
        ]
        
        for i, (name, value, color) in enumerate(systems):
            group = QGroupBox(name)
            group.setStyleSheet("""
                QGroupBox {
                    color: #aabbcc;
                    font-weight: bold;
                    border: 1px solid #444477;
                    border-radius: 5px;
                    margin-top: 10px;
                    padding-top: 15px;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 5px 0 5px;
                }
            """)
            
            group_layout = QVBoxLayout()
            
            # 自定义进度条
            progress = QProgressBar()
            progress.setValue(value)
            progress.setTextVisible(False)
            progress.setStyleSheet(f"""
                QProgressBar {{
                    border: 1px solid #444477;
                    border-radius: 3px;
                    text-align: center;
                    background: #0f1029;
                    height: 20px;
                }}
                QProgressBar::chunk {{
                    background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                        stop: 0 {color}, stop: 1 #2B32B2);
                    border-radius: 2px;
                }}
            """)
            
            group_layout.addWidget(progress)
            
            # 百分比标签
            percent = QLabel(f"{value}%")
            percent.setAlignment(Qt.AlignCenter)
            percent.setStyleSheet("color: #aabbcc; font-size: 14px;")
            group_layout.addWidget(percent)
            
            group.setLayout(group_layout)
            
            # 添加到网格
            status_grid.addWidget(group, i // 3, i % 3)
        
        layout.addLayout(status_grid)
        
        # AI助手
        ai_assistant = StellarAIAssistant()
        layout.addWidget(ai_assistant)
        
        self.tab_widget.addTab(dashboard_tab, "仪表板")
        
    def setup_navigation_tab(self):
        """设置导航选项卡"""
        navigation_tab = QWidget()
        layout = QVBoxLayout(navigation_tab)
        
        # 3D星图
        cosmic_map = CosmicMap3D()
        layout.addWidget(cosmic_map)
        
        self.tab_widget.addTab(navigation_tab, "星图导航")
        
    def setup_analysis_tab(self):
        """设置分析选项卡"""
        analysis_tab = QWidget()
        layout = QVBoxLayout(analysis_tab)
        
        # 多维度分析器
        analyzer = MultiDimensionalAnalyzer()
        layout.addWidget(analyzer)
        
        self.tab_widget.addTab(analysis_tab, "数据分析")
        
    def setup_communication_tab(self):
        """设置通信选项卡"""
        communication_tab = QWidget()
        layout = QVBoxLayout(communication_tab)
        
        # 量子通信日志
        comms_label = QLabel("量子通信日志")
        comms_label.setAlignment(Qt.AlignCenter)
        comms_label.setStyleSheet("color: #6accef; font-size: 18px; font-weight: bold; margin: 10px;")
        layout.addWidget(comms_label)
        
        self.comms_log = QTextEdit()
        self.comms_log.setStyleSheet("""
            QTextEdit {
                background-color: rgba(20, 20, 40, 200);
                color: #aaccff;
                border: 1px solid #4488ff;
                border-radius: 5px;
                font-family: 'Courier New', monospace;
                font-size: 12px;
            }
        """)
        self.comms_log.setReadOnly(True)
        layout.addWidget(self.comms_log)
        
        # 添加初始消息
        self.comms_log.append("[系统] 量子通信系统初始化完成")
        self.comms_log.append("[系统] 正在监听跨维度通信频道...")
        
        self.tab_widget.addTab(communication_tab, "量子通信")
        
    def setup_systems_tab(self):
        """设置系统选项卡"""
        systems_tab = QWidget()
        layout = QVBoxLayout(systems_tab)
        
        # 系统管理界面
        systems_label = QLabel("高级系统管理")
        systems_label.setAlignment(Qt.AlignCenter)
        systems_label.setStyleSheet("color: #6accef; font-size: 18px; font-weight: bold; margin: 10px;")
        layout.addWidget(systems_label)
        
        # 创建系统控制网格
        controls_grid = QGridLayout()
        
        # 系统控制选项
        controls = [
            ("启动自检程序", "运行全面的系统自检"),
            ("优化能源分配", "重新分配能源以提高效率"),
            ("部署探测无人机", "发射无人机进行区域扫描"),
            ("激活隐身模式", "降低信号特征以避免检测"),
            ("启动紧急协议", "启用紧急情况应对措施"),
            ("重置网络节点", "重新初始化通信网络")
        ]
        
        for i, (name, desc) in enumerate(controls):
            group = QGroupBox(name)
            group.setStyleSheet("""
                QGroupBox {
                    color: #aabbcc;
                    font-weight: bold;
                    border: 1px solid #444477;
                    border-radius: 5px;
                    margin-top: 10px;
                    padding-top: 15px;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 5px 0 5px;
                }
            """)
            
            group_layout = QVBoxLayout()
            
            # 描述标签
            desc_label = QLabel(desc)
            desc_label.setStyleSheet("color: #8899aa; font-size: 12px;")
            desc_label.setWordWrap(True)
            group_layout.addWidget(desc_label)
            
            # 控制按钮
            button = StellarButton("执行")
            button.clicked.connect(lambda checked, n=name: self.execute_system_command(n))
            group_layout.addWidget(button)
            
            group.setLayout(group_layout)
            
            # 添加到网格
            controls_grid.addWidget(group, i // 2, i % 2)
        
        layout.addLayout(controls_grid)
        layout.addStretch()
        
        self.tab_widget.addTab(systems_tab, "系统管理")
        
    def setup_statusbar(self):
        """设置状态栏"""
        status_bar = QStatusBar()
        self.setStatusBar(status_bar)
        
        # 添加状态标签
        self.status_label = QLabel("系统就绪")
        self.status_label.setStyleSheet("color: #aabbcc;")
        status_bar.addWidget(self.status_label)
        
        # 添加时间标签
        self.time_label = QLabel()
        self.time_label.setStyleSheet("color: #8899aa;")
        status_bar.addPermanentWidget(self.time_label)
        
        # 更新时间的定时器
        self.time_timer = QTimer(self)
        self.time_timer.timeout.connect(self.update_time)
        self.time_timer.start(1000)
        self.update_time()
        
    def update_time(self):
        """更新状态栏时间"""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        stardate = f"星历 {int(datetime.now().timestamp() / 10000)}.{(datetime.now().timestamp() % 10000):04.0f}"
        self.time_label.setText(f"{current_time} | {stardate}")
        
    def handle_quantum_message(self, sender, message):
        """处理量子通信消息"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {sender}: {message}"
        self.comms_log.append(formatted_message)
        
        # 在状态栏显示通知
        self.status_label.setText(f"收到来自 {sender} 的新消息")
        QTimer.singleShot(5000, lambda: self.status_label.setText("系统就绪"))
        
    def execute_system_command(self, command):
        """执行系统命令"""
        self.status_label.setText(f"执行命令: {command}...")
        
        # 模拟命令执行延迟
        QTimer.singleShot(3000, lambda: self.status_label.setText(f"命令 {command} 执行完成"))
        
    def closeEvent(self, event):
        """应用程序关闭事件"""
        # 停止量子通信线程
        self.quantum_com.stop()
        
        # 确认退出
        reply = QMessageBox.question(self, '确认退出', 
                                    '确定要关闭星际系统工具库吗？',
                                    QMessageBox.Yes | QMessageBox.No,
                                    QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 设置应用程序样式
    app.setStyle("Fusion")
    
    # 设置应用程序字体
    font = QFont("Arial", 10)
    app.setFont(font)
    
    # 创建并显示主窗口
    window = AdvancedStellarToolkit()
    window.show()
    
    sys.exit(app.exec_())