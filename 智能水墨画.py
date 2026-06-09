import sys
import numpy as np
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QSlider, 
                             QComboBox, QGroupBox, QFileDialog, QMessageBox,
                             QColorDialog, QSpinBox, QCheckBox, QTabWidget,
                             QListWidget, QListWidgetItem, QSplitter, QToolBar,
                             QAction, QToolButton, QMenu, QProgressDialog,
                             QInputDialog, QDialog, QDialogButtonBox, QFormLayout,
                             QLineEdit, QTextEdit)
from PyQt5.QtCore import Qt, QPoint, QRect, QSize, QTimer, pyqtSignal, QThread
from PyQt5.QtGui import (QPainter, QPen, QBrush, QColor, QImage, QPixmap, 
                         QFont, QLinearGradient, QRadialGradient, QPainterPath,
                         QIcon, QPalette, QFontMetrics, QKeySequence, QTransform,
                         QCursor)
from PyQt5.QtPrintSupport import QPrintDialog, QPrinter
import cv2
from scipy import ndimage
import random
import json
import time
import os
from datetime import datetime
from PIL import Image, ImageFilter, ImageEnhance
import torch
import torch.nn as nn
import torchvision.transforms as transforms
import torchvision.models as models
import numpy as np
from collections import deque


# ============================ AI 风格转换模块 ============================

class StyleTransferModel(nn.Module):
    """简化的风格迁移模型"""
    def __init__(self):
        super(StyleTransferModel, self).__init__()
        # 使用预训练的VGG19作为特征提取器
        self.vgg = models.vgg19(pretrained=True).features[:26]
        for param in self.parameters():
            param.requires_grad = False
    
    def forward(self, x):
        features = []
        for layer in self.vgg:
            x = layer(x)
            if isinstance(layer, nn.Conv2d):
                features.append(x)
        return features


class AIStyleTransfer(QThread):
    """AI风格转换线程"""
    progress = pyqtSignal(int)
    finished = pyqtSignal(QImage)
    
    def __init__(self, content_image, style_image, intensity=0.5):
        super().__init__()
        self.content_image = content_image
        self.style_image = style_image
        self.intensity = intensity
        self.model = StyleTransferModel()
        
    def run(self):
        try:
            # 简化版风格迁移实现
            self.progress.emit(10)
            
            # 转换图像格式
            content_arr = self.qimage_to_array(self.content_image)
            style_arr = self.qimage_to_array(self.style_image)
            
            self.progress.emit(30)
            
            # 调整风格图像大小以匹配内容图像
            style_resized = cv2.resize(style_arr, (content_arr.shape[1], content_arr.shape[0]))
            
            self.progress.emit(50)
            
            # 简单的风格融合（实际应用中应使用更复杂的算法）
            alpha = self.intensity
            result_arr = cv2.addWeighted(content_arr, 1-alpha, style_resized, alpha, 0)
            
            self.progress.emit(80)
            
            # 转换为水墨风格
            result_arr = self.apply_ink_effect(result_arr)
            
            self.progress.emit(90)
            
            # 转换回QImage
            result_image = self.array_to_qimage(result_arr)
            
            self.progress.emit(100)
            self.finished.emit(result_image)
            
        except Exception as e:
            print(f"AI风格转换错误: {e}")
            self.finished.emit(QImage())
    
    def qimage_to_array(self, qimage):
        """将QImage转换为numpy数组"""
        qimage = qimage.convertToFormat(QImage.Format_RGB32)
        width = qimage.width()
        height = qimage.height()
        ptr = qimage.bits()
        ptr.setsize(height * width * 4)
        arr = np.frombuffer(ptr, np.uint8).reshape((height, width, 4))
        return cv2.cvtColor(arr, cv2.COLOR_RGBA2RGB)
    
    def array_to_qimage(self, arr):
        """将numpy数组转换为QImage"""
        height, width, channel = arr.shape
        bytes_per_line = 3 * width
        qimage = QImage(arr.data, width, height, bytes_per_line, QImage.Format_RGB888)
        return qimage.copy()
    
    def apply_ink_effect(self, arr):
        """应用水墨效果"""
        # 转换为灰度
        gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
        
        # 边缘检测
        edges = cv2.Canny(gray, 50, 150)
        
        # 创建水墨效果
        ink_effect = np.zeros_like(arr)
        ink_effect[edges > 0] = [0, 0, 0]  # 黑色边缘
        
        # 添加一些水墨扩散效果
        ink_effect = cv2.GaussianBlur(ink_effect, (5, 5), 0)
        
        return ink_effect


# ============================ 高级水墨笔刷系统 ============================

class AdvancedInkBrush:
    """高级水墨笔刷类"""
    def __init__(self):
        self.size = 20
        self.opacity = 0.8
        self.wetness = 0.5
        self.ink_density = 0.7
        self.color = QColor(0, 0, 0, 180)
        self.brush_type = "常规"  # 常规、干笔、湿笔、飞白、泼墨
        self.pressure_sensitivity = True
        self.texture_intensity = 0.3
        
    def set_size(self, size):
        self.size = size
        
    def set_opacity(self, opacity):
        self.opacity = opacity
        
    def set_wetness(self, wetness):
        self.wetness = wetness
        
    def set_ink_density(self, density):
        self.ink_density = density
        
    def set_color(self, color):
        self.color = color
        
    def set_brush_type(self, brush_type):
        self.brush_type = brush_type
        
    def set_pressure_sensitivity(self, enabled):
        self.pressure_sensitivity = enabled
        
    def set_texture_intensity(self, intensity):
        self.texture_intensity = intensity
        
    def create_brush_texture(self, size):
        """创建笔刷纹理"""
        texture = QImage(size, size, QImage.Format_ARGB32)
        texture.fill(Qt.transparent)
        
        painter = QPainter(texture)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 根据笔刷类型创建不同纹理
        if self.brush_type == "干笔":
            # 干笔效果 - 不连续的笔触
            for i in range(0, size, 3):
                for j in range(0, size, 3):
                    if random.random() < 0.7:
                        alpha = random.randint(50, 200)
                        pen_size = random.randint(1, 3)
                        color = QColor(self.color)
                        color.setAlpha(alpha)
                        painter.setPen(QPen(color, pen_size))
                        painter.drawPoint(i, j)
                        
        elif self.brush_type == "湿笔":
            # 湿笔效果 - 有扩散的笔触
            center = size // 2
            gradient = QRadialGradient(center, center, center)
            gradient.setColorAt(0, self.color)
            gradient.setColorAt(1, QColor(self.color.red(), self.color.green(), 
                                         self.color.blue(), 0))
            painter.setBrush(QBrush(gradient))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(0, 0, size, size)
            
        elif self.brush_type == "飞白":
            # 飞白效果 - 有纹理的干笔
            for i in range(0, size, 2):
                for j in range(0, size, 2):
                    if random.random() < 0.5:
                        alpha = random.randint(100, 255)
                        length = random.randint(2, 5)
                        color = QColor(self.color)
                        color.setAlpha(alpha)
                        painter.setPen(QPen(color, 1))
                        painter.drawLine(i, j, i+length, j)
                        
        elif self.brush_type == "泼墨":
            # 泼墨效果 - 随机墨点
            for _ in range(size // 2):
                x = random.randint(0, size-1)
                y = random.randint(0, size-1)
                radius = random.randint(1, size//4)
                alpha = random.randint(50, 200)
                color = QColor(self.color)
                color.setAlpha(alpha)
                painter.setBrush(QBrush(color))
                painter.setPen(Qt.NoPen)
                painter.drawEllipse(x, y, radius, radius)
                
        else:  # 常规笔刷
            gradient = QRadialGradient(size//2, size//2, size//2)
            gradient.setColorAt(0, self.color)
            gradient.setColorAt(1, QColor(self.color.red(), self.color.green(), 
                                         self.color.blue(), 0))
            painter.setBrush(QBrush(gradient))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(0, 0, size, size)
        
        painter.end()
        return texture


# ============================ 智能构图系统 ============================

class CompositionGuide:
    """构图指导系统"""
    def __init__(self):
        self.guide_type = "无"  # 无、三分法、黄金分割、对称、对角线
        self.visible = False
        
    def set_guide_type(self, guide_type):
        self.guide_type = guide_type
        
    def set_visible(self, visible):
        self.visible = visible
        
    def paint_guide(self, painter, rect):
        """绘制构图指导线"""
        if not self.visible or self.guide_type == "无":
            return
            
        painter.save()
        pen = QPen(QColor(255, 0, 0, 100))
        pen.setWidth(1)
        pen.setStyle(Qt.DashLine)
        painter.setPen(pen)
        
        width = rect.width()
        height = rect.height()
        
        if self.guide_type == "三分法":
            # 三分法构图线
            h1 = height // 3
            h2 = 2 * height // 3
            w1 = width // 3
            w2 = 2 * width // 3
            
            painter.drawLine(w1, 0, w1, height)
            painter.drawLine(w2, 0, w2, height)
            painter.drawLine(0, h1, width, h1)
            painter.drawLine(0, h2, width, h2)
            
        elif self.guide_type == "黄金分割":
            # 黄金分割线 (近似)
            phi = 0.618
            h1 = int(height * phi)
            w1 = int(width * phi)
            
            painter.drawLine(w1, 0, w1, height)
            painter.drawLine(0, h1, width, h1)
            
        elif self.guide_type == "对称":
            # 对称线
            center_x = width // 2
            center_y = height // 2
            
            painter.drawLine(center_x, 0, center_x, height)
            painter.drawLine(0, center_y, width, center_y)
            
        elif self.guide_type == "对角线":
            # 对角线
            painter.drawLine(0, 0, width, height)
            painter.drawLine(width, 0, 0, height)
            
        painter.restore()


# ============================ 历史记录系统 ============================

class HistoryManager:
    """历史记录管理器"""
    def __init__(self, max_history=50):
        self.history_stack = deque(maxlen=max_history)
        self.redo_stack = deque()
        self.max_history = max_history
        
    def save_state(self, image, description=""):
        """保存状态到历史记录"""
        # 复制图像
        image_copy = QImage(image)
        
        # 保存时间戳和描述
        timestamp = datetime.now().strftime("%H:%M:%S")
        if not description:
            description = f"操作 {len(self.history_stack) + 1}"
            
        history_item = {
            'image': image_copy,
            'timestamp': timestamp,
            'description': description
        }
        
        self.history_stack.append(history_item)
        self.redo_stack.clear()  # 清空重做栈
        
    def undo(self):
        """撤销操作"""
        if len(self.history_stack) > 1:
            # 将当前状态移到重做栈
            current = self.history_stack.pop()
            self.redo_stack.append(current)
            
            # 返回上一个状态
            return self.history_stack[-1]['image'].copy()
        return None
        
    def redo(self):
        """重做操作"""
        if self.redo_stack:
            # 从重做栈恢复状态
            redo_item = self.redo_stack.pop()
            self.history_stack.append(redo_item)
            return redo_item['image'].copy()
        return None
        
    def get_history_list(self):
        """获取历史记录列表"""
        return list(self.history_stack)
        
    def clear_history(self):
        """清空历史记录"""
        if self.history_stack:
            current = self.history_stack[-1]
            self.history_stack.clear()
            self.history_stack.append(current)
            self.redo_stack.clear()


# ============================ 高级水墨画布 ============================

class AdvancedInkCanvas(QWidget):
    """高级水墨画布"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(1000, 700)
        self.setMouseTracking(True)
        
        # 初始化画布
        self.canvas = QImage(self.size(), QImage.Format_ARGB32)
        self.canvas.fill(Qt.white)
        
        # 初始化工具
        self.brush = AdvancedInkBrush()
        self.paper = InkPaper(self.width(), self.height())
        self.temp_canvas = QImage(self.size(), QImage.Format_ARGB32)
        self.temp_canvas.fill(Qt.transparent)
        
        # 绘制状态
        self.drawing = False
        self.last_point = QPoint()
        self.current_stroke = []
        self.pressure = 1.0  # 模拟压力
        
        # 效果设置
        self.enable_diffusion = True
        self.diffusion_intensity = 0.5
        self.enable_paper_texture = True
        self.enable_auto_complete = False
        
        # 高级功能
        self.composition_guide = CompositionGuide()
        self.history_manager = HistoryManager()
        self.history_manager.save_state(self.canvas, "初始画布")
        
        # AI功能
        self.style_transfer_worker = None
        
        # 定时器用于自动保存
        self.auto_save_timer = QTimer()
        self.auto_save_timer.timeout.connect(self.auto_save)
        self.auto_save_timer.start(30000)  # 每30秒自动保存
        
        # 笔刷预览
        self.brush_preview = QImage(100, 100, QImage.Format_ARGB32)
        self.update_brush_preview()
        
    def set_diffusion_enabled(self, enabled):
        self.enable_diffusion = enabled
        
    def set_diffusion_intensity(self, intensity):
        self.diffusion_intensity = intensity
        
    def set_paper_texture_enabled(self, enabled):
        self.enable_paper_texture = enabled
        
    def clear_canvas(self):
        self.canvas.fill(Qt.white)
        self.history_manager.save_state(self.canvas, "清除画布")
        self.update()
        
    def load_image(self, filename):
        image = QImage(filename)
        if not image.isNull():
            self.canvas = image.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.history_manager.save_state(self.canvas, "加载图像")
            self.update()
            
    def save_painting(self, filename):
        self.canvas.save(filename)
        
    def update_brush_preview(self):
        """更新笔刷预览"""
        self.brush_preview.fill(Qt.transparent)
        painter = QPainter(self.brush_preview)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 绘制笔刷预览
        brush_texture = self.brush.create_brush_texture(self.brush.size * 2)
        painter.drawImage(50 - self.brush.size, 50 - self.brush.size, brush_texture)
        
        painter.end()
        
    def set_brush_type(self, brush_type):
        self.brush.set_brush_type(brush_type)
        self.update_brush_preview()
        
    def set_pressure_sensitivity(self, enabled):
        self.brush.set_pressure_sensitivity(enabled)
        
    def set_auto_complete(self, enabled):
        self.enable_auto_complete = enabled
        
    def set_composition_guide(self, guide_type):
        self.composition_guide.set_guide_type(guide_type)
        self.update()
        
    def toggle_guide_visibility(self):
        self.composition_guide.set_visible(not self.composition_guide.visible)
        self.update()
        
    def undo(self):
        image = self.history_manager.undo()
        if image is not None:
            self.canvas = image
            self.update()
            
    def redo(self):
        image = self.history_manager.redo()
        if image is not None:
            self.canvas = image
            self.update()
            
    def auto_save(self):
        """自动保存"""
        if len(self.history_manager.history_stack) > 1:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"autosave_{timestamp}.png"
            self.save_painting(filename)
            
    def apply_ai_style_transfer(self, style_image, intensity=0.5):
        """应用AI风格转换"""
        if self.style_transfer_worker and self.style_transfer_worker.isRunning():
            return
            
        # 创建进度对话框
        progress = QProgressDialog("AI风格转换中...", "取消", 0, 100, self)
        progress.setWindowTitle("AI处理")
        progress.setWindowModality(Qt.WindowModal)
        
        # 创建AI工作线程
        self.style_transfer_worker = AIStyleTransfer(self.canvas, style_image, intensity)
        self.style_transfer_worker.progress.connect(progress.setValue)
        self.style_transfer_worker.finished.connect(
            lambda result: self.on_style_transfer_finished(result, progress))
        
        # 连接取消按钮
        progress.canceled.connect(self.style_transfer_worker.terminate)
        
        self.style_transfer_worker.start()
        progress.exec_()
        
    def on_style_transfer_finished(self, result_image, progress):
        """AI风格转换完成"""
        progress.close()
        
        if not result_image.isNull():
            self.history_manager.save_state(self.canvas, "AI风格转换前")
            self.canvas = result_image
            self.update()
            QMessageBox.information(self, "完成", "AI风格转换已完成！")
        else:
            QMessageBox.warning(self, "错误", "AI风格转换失败！")
            
    def apply_auto_complete(self):
        """自动补全 - 基于简单算法模拟水墨画补全"""
        if not self.enable_auto_complete:
            return
            
        # 简化版的自动补全 - 实际应用中应使用更复杂的AI算法
        temp_image = self.canvas.copy()
        
        # 转换为numpy数组进行处理
        ptr = temp_image.bits()
        ptr.setsize(temp_image.height() * temp_image.width() * 4)
        arr = np.frombuffer(ptr, np.uint8).reshape((temp_image.height(), temp_image.width(), 4))
        
        # 简单的图像处理来模拟补全效果
        # 这里只是一个示例，实际应用需要更复杂的算法
        gray = cv2.cvtColor(arr, cv2.COLOR_RGBA2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        
        # 在边缘附近添加一些随机笔触
        painter = QPainter(temp_image)
        painter.setRenderHint(QPainter.Antialiasing)
        
        for y in range(0, edges.shape[0], 10):
            for x in range(0, edges.shape[1], 10):
                if edges[y, x] > 0 and random.random() < 0.1:
                    # 在边缘附近添加随机笔触
                    bx = x + random.randint(-20, 20)
                    by = y + random.randint(-20, 20)
                    if 0 <= bx < edges.shape[1] and 0 <= by < edges.shape[0]:
                        size = random.randint(5, 15)
                        alpha = random.randint(50, 150)
                        color = QColor(0, 0, 0, alpha)
                        painter.setPen(QPen(color, size))
                        painter.drawPoint(bx, by)
        
        painter.end()
        
        self.history_manager.save_state(self.canvas, "自动补全前")
        self.canvas = temp_image
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 绘制背景
        if self.enable_paper_texture:
            painter.drawImage(0, 0, self.paper.texture)
        else:
            painter.fillRect(self.rect(), QBrush(QColor(240, 230, 210)))
            
        # 绘制画布内容
        painter.drawImage(0, 0, self.canvas)
        
        # 绘制临时笔触
        painter.drawImage(0, 0, self.temp_canvas)
        
        # 绘制构图指导
        self.composition_guide.paint_guide(painter, self.rect())
        
        # 绘制笔刷预览（在光标位置）
        if self.underMouse() and not self.drawing:
            cursor_pos = self.mapFromGlobal(QCursor.pos())
            painter.drawImage(cursor_pos.x() - 50, cursor_pos.y() - 50, self.brush_preview)
        
        painter.end()
        
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drawing = True
            self.last_point = event.pos()
            self.current_stroke = [self.last_point]
            
            # 根据位置模拟压力（靠近画布边缘压力小）
            center = self.rect().center()
            dist_to_center = ((event.x() - center.x())**2 + (event.y() - center.y())**2)**0.5
            max_dist = (self.width()**2 + self.height()**2)**0.5 / 2
            self.pressure = 1.0 - (dist_to_center / max_dist) * 0.5
            
    def mouseMoveEvent(self, event):
        if self.drawing and event.buttons() & Qt.LeftButton:
            # 绘制临时笔触
            self.temp_canvas.fill(Qt.transparent)
            painter = QPainter(self.temp_canvas)
            painter.setRenderHint(QPainter.Antialiasing)
            
            # 设置笔刷
            brush_size = int(self.brush.size * self.pressure)
            color = self.brush.color
            if self.brush.pressure_sensitivity:
                alpha = int(color.alpha() * self.pressure)
                color.setAlpha(alpha)
                
            pen = QPen(color)
            pen.setWidth(brush_size)
            pen.setCapStyle(Qt.RoundCap)
            pen.setJoinStyle(Qt.RoundJoin)
            painter.setPen(pen)
            
            # 绘制当前笔触
            if len(self.current_stroke) > 1:
                path = QPainterPath()
                path.moveTo(self.current_stroke[0])
                for point in self.current_stroke[1:]:
                    path.lineTo(point)
                path.lineTo(event.pos())
                painter.drawPath(path)
            
            painter.end()
            self.update()
            
            self.current_stroke.append(event.pos())
            
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.drawing:
            self.drawing = False
            
            # 保存状态到历史记录
            self.history_manager.save_state(self.canvas, "笔触绘制")
            
            # 绘制最终笔触到主画布
            painter = QPainter(self.canvas)
            painter.setRenderHint(QPainter.Antialiasing)
            
            # 设置笔刷
            brush_size = int(self.brush.size * self.pressure)
            color = self.brush.color
            if self.brush.pressure_sensitivity:
                alpha = int(color.alpha() * self.pressure)
                color.setAlpha(alpha)
                
            pen = QPen(color)
            pen.setWidth(brush_size)
            pen.setCapStyle(Qt.RoundCap)
            pen.setJoinStyle(Qt.RoundJoin)
            painter.setPen(pen)
            
            # 绘制笔触路径
            if len(self.current_stroke) > 1:
                path = QPainterPath()
                path.moveTo(self.current_stroke[0])
                for point in self.current_stroke[1:]:
                    path.lineTo(point)
                painter.drawPath(path)
            
            painter.end()
            
            # 应用墨迹扩散效果
            if self.enable_diffusion:
                self.canvas = InkDiffusionEffect.apply_diffusion(
                    self.canvas, self.diffusion_intensity)
            
            # 清空临时画布
            self.temp_canvas.fill(Qt.transparent)
            self.update()


# ============================ 高级工具面板 ============================

class AdvancedInkTools(QWidget):
    """高级水墨工具面板"""
    def __init__(self, canvas):
        super().__init__()
        self.canvas = canvas
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 创建选项卡
        tabs = QTabWidget()
        
        # 笔刷选项卡
        brush_tab = self.create_brush_tab()
        tabs.addTab(brush_tab, "笔刷设置")
        
        # 效果选项卡
        effect_tab = self.create_effect_tab()
        tabs.addTab(effect_tab, "水墨效果")
        
        # AI功能选项卡
        ai_tab = self.create_ai_tab()
        tabs.addTab(ai_tab, "AI功能")
        
        # 工具选项卡
        tool_tab = self.create_tool_tab()
        tabs.addTab(tool_tab, "工具")
        
        layout.addWidget(tabs)
        self.setLayout(layout)
        
    def create_brush_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()
        
        # 笔刷类型
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("笔刷类型:"))
        self.brush_type_combo = QComboBox()
        self.brush_type_combo.addItems(["常规", "干笔", "湿笔", "飞白", "泼墨"])
        self.brush_type_combo.currentTextChanged.connect(self.canvas.set_brush_type)
        type_layout.addWidget(self.brush_type_combo)
        layout.addLayout(type_layout)
        
        # 笔刷大小
        size_layout = QHBoxLayout()
        size_layout.addWidget(QLabel("笔刷大小:"))
        self.size_slider = QSlider(Qt.Horizontal)
        self.size_slider.setRange(1, 100)
        self.size_slider.setValue(20)
        self.size_slider.valueChanged.connect(self.canvas.brush.set_size)
        self.size_slider.valueChanged.connect(self.canvas.update_brush_preview)
        size_layout.addWidget(self.size_slider)
        layout.addLayout(size_layout)
        
        # 墨水浓度
        density_layout = QHBoxLayout()
        density_layout.addWidget(QLabel("墨水浓度:"))
        self.density_slider = QSlider(Qt.Horizontal)
        self.density_slider.setRange(1, 100)
        self.density_slider.setValue(70)
        self.density_slider.valueChanged.connect(
            lambda v: self.canvas.brush.set_ink_density(v/100))
        self.density_slider.valueChanged.connect(self.canvas.update_brush_preview)
        density_layout.addWidget(self.density_slider)
        layout.addLayout(density_layout)
        
        # 笔刷颜色
        color_layout = QHBoxLayout()
        color_layout.addWidget(QLabel("笔刷颜色:"))
        self.color_btn = QPushButton("选择颜色")
        self.color_btn.clicked.connect(self.choose_color)
        color_layout.addWidget(self.color_btn)
        layout.addLayout(color_layout)
        
        # 压力感应
        pressure_layout = QHBoxLayout()
        self.pressure_check = QCheckBox("启用压力感应")
        self.pressure_check.setChecked(True)
        self.pressure_check.stateChanged.connect(
            lambda s: self.canvas.set_pressure_sensitivity(s == Qt.Checked))
        pressure_layout.addWidget(self.pressure_check)
        layout.addLayout(pressure_layout)
        
        # 笔刷纹理强度
        texture_layout = QHBoxLayout()
        texture_layout.addWidget(QLabel("笔刷纹理:"))
        self.texture_slider = QSlider(Qt.Horizontal)
        self.texture_slider.setRange(0, 100)
        self.texture_slider.setValue(30)
        self.texture_slider.valueChanged.connect(
            lambda v: self.canvas.brush.set_texture_intensity(v/100))
        self.texture_slider.valueChanged.connect(self.canvas.update_brush_preview)
        texture_layout.addWidget(self.texture_slider)
        layout.addLayout(texture_layout)
        
        tab.setLayout(layout)
        return tab
        
    def create_effect_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()
        
        # 墨迹扩散
        diffusion_layout = QHBoxLayout()
        self.diffusion_check = QCheckBox("启用墨迹扩散")
        self.diffusion_check.setChecked(True)
        self.diffusion_check.stateChanged.connect(
            lambda s: self.canvas.set_diffusion_enabled(s == Qt.Checked))
        diffusion_layout.addWidget(self.diffusion_check)
        
        self.diffusion_intensity = QSlider(Qt.Horizontal)
        self.diffusion_intensity.setRange(1, 100)
        self.diffusion_intensity.setValue(50)
        self.diffusion_intensity.valueChanged.connect(
            lambda v: self.canvas.set_diffusion_intensity(v/100))
        diffusion_layout.addWidget(QLabel("强度:"))
        diffusion_layout.addWidget(self.diffusion_intensity)
        layout.addLayout(diffusion_layout)
        
        # 宣纸纹理
        paper_layout = QHBoxLayout()
        self.paper_check = QCheckBox("启用宣纸纹理")
        self.paper_check.setChecked(True)
        self.paper_check.stateChanged.connect(
            lambda s: self.canvas.set_paper_texture_enabled(s == Qt.Checked))
        paper_layout.addWidget(self.paper_check)
        layout.addLayout(paper_layout)
        
        # 自动补全
        auto_complete_layout = QHBoxLayout()
        self.auto_complete_check = QCheckBox("启用自动补全")
        self.auto_complete_check.setChecked(False)
        self.auto_complete_check.stateChanged.connect(
            lambda s: self.canvas.set_auto_complete(s == Qt.Checked))
        auto_complete_layout.addWidget(self.auto_complete_check)
        
        self.auto_complete_btn = QPushButton("执行补全")
        self.auto_complete_btn.clicked.connect(self.canvas.apply_auto_complete)
        auto_complete_layout.addWidget(self.auto_complete_btn)
        layout.addLayout(auto_complete_layout)
        
        tab.setLayout(layout)
        return tab
        
    def create_ai_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()
        
        # AI风格转换
        ai_style_layout = QVBoxLayout()
        ai_style_layout.addWidget(QLabel("AI风格转换:"))
        
        self.style_load_btn = QPushButton("加载风格图像")
        self.style_load_btn.clicked.connect(self.load_style_image)
        ai_style_layout.addWidget(self.style_load_btn)
        
        style_intensity_layout = QHBoxLayout()
        style_intensity_layout.addWidget(QLabel("风格强度:"))
        self.style_intensity_slider = QSlider(Qt.Horizontal)
        self.style_intensity_slider.setRange(1, 100)
        self.style_intensity_slider.setValue(50)
        style_intensity_layout.addWidget(self.style_intensity_slider)
        ai_style_layout.addLayout(style_intensity_layout)
        
        self.style_apply_btn = QPushButton("应用风格转换")
        self.style_apply_btn.clicked.connect(self.apply_style_transfer)
        ai_style_layout.addWidget(self.style_apply_btn)
        
        layout.addLayout(ai_style_layout)
        
        # 风格图像预览
        self.style_preview = QLabel("未加载风格图像")
        self.style_preview.setMinimumSize(150, 150)
        self.style_preview.setAlignment(Qt.AlignCenter)
        self.style_preview.setStyleSheet("border: 1px solid gray;")
        layout.addWidget(self.style_preview)
        
        tab.setLayout(layout)
        return tab
        
    def create_tool_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()
        
        # 构图指导
        composition_layout = QHBoxLayout()
        composition_layout.addWidget(QLabel("构图指导:"))
        self.composition_combo = QComboBox()
        self.composition_combo.addItems(["无", "三分法", "黄金分割", "对称", "对角线"])
        self.composition_combo.currentTextChanged.connect(self.canvas.set_composition_guide)
        composition_layout.addWidget(self.composition_combo)
        
        self.guide_visibility_btn = QPushButton("显示/隐藏")
        self.guide_visibility_btn.clicked.connect(self.canvas.toggle_guide_visibility)
        composition_layout.addWidget(self.guide_visibility_btn)
        layout.addLayout(composition_layout)
        
        # 历史记录
        history_layout = QHBoxLayout()
        self.undo_btn = QPushButton("撤销")
        self.undo_btn.clicked.connect(self.canvas.undo)
        history_layout.addWidget(self.undo_btn)
        
        self.redo_btn = QPushButton("重做")
        self.redo_btn.clicked.connect(self.canvas.redo)
        history_layout.addWidget(self.redo_btn)
        layout.addLayout(history_layout)
        
        # 画布操作
        canvas_layout = QHBoxLayout()
        self.clear_btn = QPushButton("清除画布")
        self.clear_btn.clicked.connect(self.canvas.clear_canvas)
        canvas_layout.addWidget(self.clear_btn)
        
        self.load_btn = QPushButton("加载图片")
        self.load_btn.clicked.connect(self.load_image)
        canvas_layout.addWidget(self.load_btn)
        
        self.save_btn = QPushButton("保存作品")
        self.save_btn.clicked.connect(self.save_painting)
        canvas_layout.addWidget(self.save_btn)
        layout.addLayout(canvas_layout)
        
        tab.setLayout(layout)
        return tab
        
    def choose_color(self):
        color = QColorDialog.getColor(self.canvas.brush.color, self, "选择墨色")
        if color.isValid():
            self.canvas.brush.set_color(color)
            self.canvas.update_brush_preview()
            
    def load_image(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, "打开图片", "", "图片文件 (*.png *.jpg *.jpeg *.bmp)")
        if filename:
            self.canvas.load_image(filename)
            
    def load_style_image(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, "打开风格图片", "", "图片文件 (*.png *.jpg *.jpeg *.bmp)")
        if filename:
            self.style_image = QImage(filename)
            if not self.style_image.isNull():
                # 缩放预览
                preview = self.style_image.scaled(150, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.style_preview.setPixmap(QPixmap.fromImage(preview))
            else:
                self.style_preview.setText("加载失败")
                
    def apply_style_transfer(self):
        if hasattr(self, 'style_image') and not self.style_image.isNull():
            intensity = self.style_intensity_slider.value() / 100
            self.canvas.apply_ai_style_transfer(self.style_image, intensity)
        else:
            QMessageBox.warning(self, "警告", "请先加载风格图像！")
            
    def save_painting(self):
        filename, _ = QFileDialog.getSaveFileName(
            self, "保存作品", "", "PNG文件 (*.png);;JPEG文件 (*.jpg)")
        if filename:
            self.canvas.save_painting(filename)
            QMessageBox.information(self, "保存成功", "作品已保存成功！")


# ============================ 智能水墨画系统主窗口 ============================

class SmartInkPaintingSystem(QMainWindow):
    """智能水墨画系统主窗口"""
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("智能水墨画系统 - 高级版")
        self.setGeometry(100, 100, 1400, 900)
        
        # 创建中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        main_layout = QHBoxLayout()
        central_widget.setLayout(main_layout)
        
        # 创建画布
        self.canvas = AdvancedInkCanvas()
        
        # 创建工具面板
        self.tools = AdvancedInkTools(self.canvas)
        
        # 使用分割器，使工具面板可以调整大小
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self.canvas)
        splitter.addWidget(self.tools)
        splitter.setStretchFactor(0, 1)  # 画布可拉伸
        splitter.setStretchFactor(1, 0)  # 工具面板固定宽度
        
        main_layout.addWidget(splitter)
        
        # 创建菜单栏
        self.create_menubar()
        
        # 创建工具栏
        self.create_toolbar()
        
        # 状态栏
        self.statusBar().showMessage("智能水墨画系统已就绪 - 高级版")
        
    def create_menubar(self):
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu('文件')
        
        new_action = QAction('新建', self)
        new_action.setShortcut('Ctrl+N')
        new_action.triggered.connect(self.new_file)
        file_menu.addAction(new_action)
        
        open_action = QAction('打开', self)
        open_action.setShortcut('Ctrl+O')
        open_action.triggered.connect(self.open_file)
        file_menu.addAction(open_action)
        
        save_action = QAction('保存', self)
        save_action.setShortcut('Ctrl+S')
        save_action.triggered.connect(self.save_file)
        file_menu.addAction(save_action)
        
        file_menu.addSeparator()
        
        print_action = QAction('打印', self)
        print_action.setShortcut('Ctrl+P')
        print_action.triggered.connect(self.print_canvas)
        file_menu.addAction(print_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction('退出', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 编辑菜单
        edit_menu = menubar.addMenu('编辑')
        
        undo_action = QAction('撤销', self)
        undo_action.setShortcut('Ctrl+Z')
        undo_action.triggered.connect(self.canvas.undo)
        edit_menu.addAction(undo_action)
        
        redo_action = QAction('重做', self)
        redo_action.setShortcut('Ctrl+Y')
        redo_action.triggered.connect(self.canvas.redo)
        edit_menu.addAction(redo_action)
        
        edit_menu.addSeparator()
        
        clear_action = QAction('清除画布', self)
        clear_action.triggered.connect(self.canvas.clear_canvas)
        edit_menu.addAction(clear_action)
        
        # 视图菜单
        view_menu = menubar.addMenu('视图')
        
        guide_action = QAction('显示构图指导', self, checkable=True)
        guide_action.triggered.connect(self.canvas.toggle_guide_visibility)
        view_menu.addAction(guide_action)
        
        texture_action = QAction('显示宣纸纹理', self, checkable=True, checked=True)
        texture_action.triggered.connect(lambda: self.canvas.set_paper_texture_enabled(texture_action.isChecked()))
        view_menu.addAction(texture_action)
        
        # AI菜单
        ai_menu = menubar.addMenu('AI功能')
        
        style_transfer_action = QAction('AI风格转换', self)
        style_transfer_action.triggered.connect(self.open_style_transfer)
        ai_menu.addAction(style_transfer_action)
        
        auto_complete_action = QAction('智能补全', self)
        auto_complete_action.triggered.connect(self.canvas.apply_auto_complete)
        ai_menu.addAction(auto_complete_action)
        
    def create_toolbar(self):
        toolbar = QToolBar("主工具栏")
        self.addToolBar(Qt.LeftToolBarArea, toolbar)
        
        # 笔刷工具
        brush_tool = QToolButton()
        brush_tool.setText("笔刷")
        brush_tool.setPopupMode(QToolButton.InstantPopup)
        
        brush_menu = QMenu(self)
        brush_types = ["常规", "干笔", "湿笔", "飞白", "泼墨"]
        for brush_type in brush_types:
            action = QAction(brush_type, self)
            action.triggered.connect(lambda checked, bt=brush_type: self.canvas.set_brush_type(bt))
            brush_menu.addAction(action)
        
        brush_tool.setMenu(brush_menu)
        toolbar.addWidget(brush_tool)
        
        # 分隔符
        toolbar.addSeparator()
        
        # 撤销重做
        undo_btn = QAction("撤销", self)
        undo_btn.triggered.connect(self.canvas.undo)
        toolbar.addAction(undo_btn)
        
        redo_btn = QAction("重做", self)
        redo_btn.triggered.connect(self.canvas.redo)
        toolbar.addAction(redo_btn)
        
        # 分隔符
        toolbar.addSeparator()
        
        # 清除画布
        clear_btn = QAction("清除", self)
        clear_btn.triggered.connect(self.canvas.clear_canvas)
        toolbar.addAction(clear_btn)
        
    def new_file(self):
        reply = QMessageBox.question(self, '新建画布', 
                                    '是否保存当前作品？', 
                                    QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
        
        if reply == QMessageBox.Yes:
            self.save_file()
            self.canvas.clear_canvas()
        elif reply == QMessageBox.No:
            self.canvas.clear_canvas()
            
    def open_file(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, "打开作品", "", "水墨画文件 (*.png *.jpg *.jpeg);;所有文件 (*)")
        if filename:
            self.canvas.load_image(filename)
            
    def save_file(self):
        filename, _ = QFileDialog.getSaveFileName(
            self, "保存作品", "", "PNG文件 (*.png);;JPEG文件 (*.jpg)")
        if filename:
            self.canvas.save_painting(filename)
            
    def print_canvas(self):
        printer = QPrinter(QPrinter.HighResolution)
        dialog = QPrintDialog(printer, self)
        if dialog.exec_() == QPrintDialog.Accepted:
            painter = QPainter(printer)
            rect = painter.viewport()
            size = self.canvas.canvas.size()
            size.scale(rect.size(), Qt.KeepAspectRatio)
            painter.setViewport(rect.x(), rect.y(), size.width(), size.height())
            painter.setWindow(self.canvas.canvas.rect())
            painter.drawImage(0, 0, self.canvas.canvas)
            painter.end()
            
    def open_style_transfer(self):
        # 打开风格转换对话框
        if hasattr(self.tools, 'style_image') and not self.tools.style_image.isNull():
            intensity = self.tools.style_intensity_slider.value() / 100
            self.canvas.apply_ai_style_transfer(self.tools.style_image, intensity)
        else:
            QMessageBox.information(self, "提示", "请先在AI功能选项卡中加载风格图像")


# ============================ 辅助类（从上一个版本保留） ============================

class InkPaper:
    """宣纸效果类"""
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.texture = None
        self.color = QColor(240, 230, 210)  # 宣纸底色
        self.texture_intensity = 0.3  # 纹理强度
        self.generate_texture()
        
    def generate_texture(self):
        """生成宣纸纹理"""
        self.texture = QImage(self.width, self.height, QImage.Format_ARGB32)
        self.texture.fill(self.color)
        
        painter = QPainter(self.texture)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 添加宣纸纹理
        for i in range(0, self.width, 2):
            for j in range(0, self.height, 2):
                if random.random() < self.texture_intensity:
                    alpha = random.randint(5, 20)
                    size = random.randint(1, 3)
                    color = QColor(220, 210, 190, alpha)
                    painter.setBrush(QBrush(color))
                    painter.setPen(Qt.NoPen)
                    painter.drawEllipse(i, j, size, size)
        
        painter.end()
        
    def apply_texture(self, image):
        """将纹理应用到图像上"""
        result = QImage(self.width, self.height, QImage.Format_ARGB32)
        painter = QPainter(result)
        painter.drawImage(0, 0, image)
        painter.setCompositionMode(QPainter.CompositionMode_Overlay)
        painter.drawImage(0, 0, self.texture)
        painter.end()
        return result


class InkDiffusionEffect:
    """墨迹扩散效果"""
    @staticmethod
    def apply_diffusion(image, intensity=0.5):
        """应用墨迹扩散效果"""
        # 将QImage转换为numpy数组
        width = image.width()
        height = image.height()
        ptr = image.bits()
        ptr.setsize(height * width * 4)
        arr = np.frombuffer(ptr, np.uint8).reshape((height, width, 4))
        
        # 提取alpha通道作为墨迹
        ink_layer = arr[:, :, 3]
        
        # 应用高斯模糊模拟扩散
        kernel_size = max(1, int(10 * intensity))
        if kernel_size % 2 == 0:
            kernel_size += 1
            
        diffused = cv2.GaussianBlur(ink_layer, (kernel_size, kernel_size), 0)
        
        # 合并回原图像
        result = arr.copy()
        result[:, :, 3] = np.maximum(arr[:, :, 3], diffused)
        
        # 转换回QImage
        diffused_image = QImage(result.data, width, height, width * 4, QImage.Format_ARGB32)
        return diffused_image.copy()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # 设置应用程序字体
    font = QFont("Microsoft YaHei", 10)
    app.setFont(font)
    
    # 设置应用程序样式
    app.setStyle('Fusion')
    
    window = SmartInkPaintingSystem()
    window.show()
    
    sys.exit(app.exec_())