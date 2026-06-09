import sys
import math
import numpy as np
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PIL import Image, ImageDraw, ImageFilter
import cv2
import json
import os
from datetime import datetime

class CalligraphyToolkit:
    """智能书法系统核心工具库"""
    
    def __init__(self):
        self.brush_presets = {
            "毛笔": {"size": 20, "hardness": 0.3, "opacity": 0.9},
            "钢笔": {"size": 5, "hardness": 0.9, "opacity": 1.0},
            "铅笔": {"size": 3, "hardness": 0.5, "opacity": 0.7},
            "马克笔": {"size": 15, "hardness": 0.1, "opacity": 0.8}
        }
        
        self.paper_textures = {
            "宣纸": "textures/xuan_paper.jpg",
            "绢布": "textures/silk_texture.jpg",
            "普通纸": "textures/plain_paper.jpg",
            "水彩纸": "textures/watercolor_paper.jpg"
        }
        
        self.ink_colors = {
            "浓墨": QColor(0, 0, 0),
            "淡墨": QColor(50, 50, 50),
            "焦墨": QColor(20, 20, 20),
            "朱墨": QColor(180, 0, 0)
        }
        
        self.history = []
        self.max_history = 50
        
    def create_brush_texture(self, brush_type, size_factor=1.0):
        """创建毛笔纹理效果"""
        preset = self.brush_presets[brush_type]
        size = int(preset["size"] * size_factor)
        hardness = preset["hardness"]
        
        # 创建画笔纹理
        brush_texture = QImage(size, size, QImage.Format_ARGB32)
        brush_texture.fill(Qt.transparent)
        
        painter = QPainter(brush_texture)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 创建渐变效果模拟毛笔
        gradient = QRadialGradient(size/2, size/2, size/2)
        gradient.setColorAt(0, QColor(0, 0, 0, int(255 * preset["opacity"])))
        gradient.setColorAt(hardness, QColor(0, 0, 0, int(200 * preset["opacity"])))
        gradient.setColorAt(1, QColor(0, 0, 0, 0))
        
        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(0, 0, size, size)
        painter.end()
        
        return brush_texture
    
    def apply_paper_texture(self, image, paper_type):
        """应用纸张纹理效果"""
        if paper_type not in self.paper_textures:
            return image
        
        # 加载纸张纹理
        texture_path = self.paper_textures[paper_type]
        if os.path.exists(texture_path):
            texture_img = QImage(texture_path)
            texture_img = texture_img.scaled(image.size(), Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
            
            # 混合图像
            result = QImage(image.size(), QImage.Format_ARGB32)
            painter = QPainter(result)
            painter.drawImage(0, 0, image)
            painter.setCompositionMode(QPainter.CompositionMode_Multiply)
            painter.drawImage(0, 0, texture_img)
            painter.end()
            
            return result
        
        return image
    
    def analyze_stroke_quality(self, stroke_points):
        """分析笔画质量"""
        if len(stroke_points) < 3:
            return {"score": 0, "feedback": "笔画太短"}
        
        # 计算笔画速度变化
        speeds = []
        for i in range(1, len(stroke_points)):
            p1 = stroke_points[i-1]
            p2 = stroke_points[i]
            distance = math.sqrt((p2.x() - p1.x())**2 + (p2.y() - p1.y())**2)
            speeds.append(distance)
        
        avg_speed = sum(speeds) / len(speeds)
        speed_variance = sum((s - avg_speed)**2 for s in speeds) / len(speeds)
        
        # 计算笔画平滑度
        angles = []
        for i in range(1, len(stroke_points)-1):
            p1 = stroke_points[i-1]
            p2 = stroke_points[i]
            p3 = stroke_points[i+1]
            
            v1 = QPointF(p2.x() - p1.x(), p2.y() - p1.y())
            v2 = QPointF(p3.x() - p2.x(), p3.y() - p2.y())
            
            dot = v1.x() * v2.x() + v1.y() * v2.y()
            mag1 = math.sqrt(v1.x()**2 + v1.y()**2)
            mag2 = math.sqrt(v2.x()**2 + v2.y()**2)
            
            if mag1 * mag2 > 0:
                angle = math.acos(min(max(dot / (mag1 * mag2), -1), 1))
                angles.append(angle)
        
        avg_angle = sum(angles) / len(angles) if angles else 0
        
        # 计算综合评分
        speed_score = max(0, 1 - speed_variance / (avg_speed + 0.1))
        smooth_score = max(0, 1 - avg_angle / (math.pi / 4))
        
        total_score = (speed_score + smooth_score) / 2 * 100
        
        # 生成反馈
        feedback = []
        if speed_variance > avg_speed * 0.5:
            feedback.append("笔画速度不均匀")
        if avg_angle > math.pi / 6:
            feedback.append("笔画转折不够平滑")
        if total_score > 80:
            feedback.append("笔画质量优秀")
        elif total_score > 60:
            feedback.append("笔画质量良好")
        else:
            feedback.append("需要更多练习")
        
        return {
            "score": int(total_score),
            "feedback": feedback,
            "speed_variance": speed_variance,
            "smoothness": avg_angle
        }
    
    def generate_calligraphy_style(self, base_style, intensity=0.5):
        """生成书法风格变换"""
        styles = {
            "楷书": {"regularity": 0.9, "boldness": 0.5, "flow": 0.3},
            "行书": {"regularity": 0.6, "boldness": 0.6, "flow": 0.7},
            "草书": {"regularity": 0.3, "boldness": 0.7, "flow": 0.9},
            "隶书": {"regularity": 0.8, "boldness": 0.8, "flow": 0.4}
        }
        
        if base_style not in styles:
            base_style = "楷书"
        
        base_params = styles[base_style]
        
        # 应用强度变换
        transformed_params = {}
        for key, value in base_params.items():
            # 在基础风格上添加随机变化
            variation = (np.random.random() - 0.5) * intensity
            transformed_params[key] = max(0.1, min(1.0, value + variation))
        
        return transformed_params
    
    def save_calligraphy_data(self, strokes, metadata, filename):
        """保存书法数据"""
        data = {
            "metadata": metadata,
            "strokes": [],
            "timestamp": datetime.now().isoformat()
        }
        
        for stroke in strokes:
            stroke_data = {
                "points": [(p.x(), p.y()) for p in stroke["points"]],
                "brush_type": stroke["brush_type"],
                "color": stroke["color"].getRgb(),
                "pressure": stroke.get("pressure", [1.0] * len(stroke["points"]))
            }
            data["strokes"].append(stroke_data)
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def load_calligraphy_data(self, filename):
        """加载书法数据"""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            strokes = []
            for stroke_data in data["strokes"]:
                stroke = {
                    "points": [QPointF(p[0], p[1]) for p in stroke_data["points"]],
                    "brush_type": stroke_data["brush_type"],
                    "color": QColor(*stroke_data["color"]),
                    "pressure": stroke_data.get("pressure", [1.0] * len(stroke_data["points"]))
                }
                strokes.append(stroke)
            
            return strokes, data.get("metadata", {})
        except Exception as e:
            print(f"加载书法数据失败: {e}")
            return [], {}


class IntelligentCalligraphyCanvas(QWidget):
    """智能书法画布"""
    
    def __init__(self):
        super().__init__()
        self.toolkit = CalligraphyToolkit()
        
        # 画布设置
        self.canvas_size = QSize(800, 600)
        self.canvas = QImage(self.canvas_size, QImage.Format_ARGB32)
        self.canvas.fill(Qt.white)
        
        # 绘制状态
        self.drawing = False
        self.last_point = QPoint()
        self.current_stroke = []
        self.strokes = []
        self.redo_strokes = []
        
        # 工具设置
        self.current_brush = "毛笔"
        self.current_paper = "宣纸"
        self.current_ink = "浓墨"
        self.brush_size = 1.0
        self.opacity = 1.0
        
        # 智能辅助
        self.stroke_smoothing = True
        self.pressure_simulation = True
        self.guideline_display = True
        
        self.setMinimumSize(self.canvas_size)
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawImage(0, 0, self.canvas)
        
        # 绘制辅助线
        if self.guideline_display:
            self.draw_guidelines(painter)
    
    def draw_guidelines(self, painter):
        """绘制书法辅助线"""
        painter.setPen(QPen(QColor(200, 200, 200, 100), 1, Qt.DashLine))
        
        width, height = self.width(), self.height()
        
        # 田字格
        cell_size = min(width, height) // 8
        for i in range(1, 8):
            # 垂直线
            painter.drawLine(i * cell_size, 0, i * cell_size, height)
            # 水平线
            painter.drawLine(0, i * cell_size, width, i * cell_size)
        
        # 中心线
        painter.setPen(QPen(QColor(255, 0, 0, 100), 2, Qt.DashLine))
        painter.drawLine(width // 2, 0, width // 2, height)
        painter.drawLine(0, height // 2, width, height // 2)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drawing = True
            self.last_point = event.pos()
            self.current_stroke = {
                "points": [event.pos()],
                "brush_type": self.current_brush,
                "color": self.toolkit.ink_colors[self.current_ink],
                "pressure": [1.0]
            }
            
            # 清除重做历史
            self.redo_strokes.clear()
    
    def mouseMoveEvent(self, event):
        if self.drawing and event.buttons() & Qt.LeftButton:
            current_point = event.pos()
            
            # 智能平滑处理
            if self.stroke_smoothing and len(self.current_stroke["points"]) > 2:
                # 简单的移动平均平滑
                last_point = self.current_stroke["points"][-1]
                smoothed_x = (last_point.x() + current_point.x()) / 2
                smoothed_y = (last_point.y() + current_point.y()) / 2
                current_point = QPoint(int(smoothed_x), int(smoothed_y))
            
            # 压力模拟
            pressure = 1.0
            if self.pressure_simulation:
                # 基于速度模拟压力变化
                if len(self.current_stroke["points"]) > 1:
                    last_point = self.current_stroke["points"][-1]
                    distance = math.sqrt((current_point.x() - last_point.x())**2 + 
                                       (current_point.y() - last_point.y())**2)
                    # 速度越快，压力越小
                    pressure = max(0.3, min(1.0, 2.0 / (distance + 1)))
            
            self.current_stroke["points"].append(current_point)
            self.current_stroke["pressure"].append(pressure)
            
            # 实时绘制
            self.draw_stroke_segment(self.last_point, current_point, pressure)
            self.last_point = current_point
            self.update()
    
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.drawing:
            self.drawing = False
            
            if len(self.current_stroke["points"]) > 1:
                self.strokes.append(self.current_stroke.copy())
                
                # 分析笔画质量
                analysis = self.toolkit.analyze_stroke_quality(self.current_stroke["points"])
                print(f"笔画质量评分: {analysis['score']}/100")
                print("反馈:", ", ".join(analysis["feedback"]))
            
            self.current_stroke.clear()
    
    def draw_stroke_segment(self, start_point, end_point, pressure):
        """绘制笔画片段"""
        painter = QPainter(self.canvas)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 创建画笔
        brush_texture = self.toolkit.create_brush_texture(
            self.current_brush, 
            self.brush_size * pressure
        )
        
        # 设置合成模式
        painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
        
        # 绘制笔画
        pen = QPen(QBrush(brush_texture), 1)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        painter.drawLine(start_point, end_point)
        
        painter.end()
    
    def clear_canvas(self):
        """清空画布"""
        self.canvas.fill(Qt.white)
        self.strokes.clear()
        self.redo_strokes.clear()
        self.update()
    
    def undo(self):
        """撤销上一步操作"""
        if self.strokes:
            last_stroke = self.strokes.pop()
            self.redo_strokes.append(last_stroke)
            self.redraw_all_strokes()
    
    def redo(self):
        """重做上一步操作"""
        if self.redo_strokes:
            stroke = self.redo_strokes.pop()
            self.strokes.append(stroke)
            self.redraw_all_strokes()
    
    def redraw_all_strokes(self):
        """重绘所有笔画"""
        self.canvas.fill(Qt.white)
        
        painter = QPainter(self.canvas)
        painter.setRenderHint(QPainter.Antialiasing)
        
        for stroke in self.strokes:
            points = stroke["points"]
            brush_type = stroke["brush_type"]
            color = stroke["color"]
            pressures = stroke.get("pressure", [1.0] * len(points))
            
            for i in range(1, len(points)):
                brush_texture = self.toolkit.create_brush_texture(
                    brush_type, 
                    self.brush_size * pressures[i]
                )
                
                pen = QPen(QBrush(brush_texture), 1)
                pen.setCapStyle(Qt.RoundCap)
                painter.setPen(pen)
                painter.drawLine(points[i-1], points[i])
        
        painter.end()
        self.update()
    
    def save_image(self, filename):
        """保存图像"""
        # 应用纸张纹理
        final_image = self.toolkit.apply_paper_texture(self.canvas, self.current_paper)
        final_image.save(filename)
        print(f"图像已保存: {filename}")
    
    def save_calligraphy_data(self, filename):
        """保存书法数据"""
        metadata = {
            "brush_type": self.current_brush,
            "paper_type": self.current_paper,
            "ink_color": self.current_ink,
            "brush_size": self.brush_size
        }
        self.toolkit.save_calligraphy_data(self.strokes, metadata, filename)
        print(f"书法数据已保存: {filename}")
    
    def load_calligraphy_data(self, filename):
        """加载书法数据"""
        strokes, metadata = self.toolkit.load_calligraphy_data(filename)
        if strokes:
            self.strokes = strokes
            if "brush_type" in metadata:
                self.current_brush = metadata["brush_type"]
            if "paper_type" in metadata:
                self.current_paper = metadata["paper_type"]
            if "ink_color" in metadata:
                self.current_ink = metadata["ink_color"]
            if "brush_size" in metadata:
                self.brush_size = metadata["brush_size"]
            
            self.redraw_all_strokes()
            print(f"书法数据已加载: {filename}")


class CalligraphyToolsPanel(QWidget):
    """书法工具面板"""
    
    def __init__(self, canvas):
        super().__init__()
        self.canvas = canvas
        self.toolkit = canvas.toolkit
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 画笔选择
        brush_group = QGroupBox("画笔设置")
        brush_layout = QVBoxLayout()
        
        self.brush_combo = QComboBox()
        self.brush_combo.addItems(self.toolkit.brush_presets.keys())
        self.brush_combo.currentTextChanged.connect(self.change_brush)
        brush_layout.addWidget(QLabel("画笔类型:"))
        brush_layout.addWidget(self.brush_combo)
        
        self.size_slider = QSlider(Qt.Horizontal)
        self.size_slider.setRange(1, 100)
        self.size_slider.setValue(50)
        self.size_slider.valueChanged.connect(self.change_brush_size)
        brush_layout.addWidget(QLabel("画笔大小:"))
        brush_layout.addWidget(self.size_slider)
        
        brush_group.setLayout(brush_layout)
        layout.addWidget(brush_group)
        
        # 纸张选择
        paper_group = QGroupBox("纸张设置")
        paper_layout = QVBoxLayout()
        
        self.paper_combo = QComboBox()
        self.paper_combo.addItems(self.toolkit.paper_textures.keys())
        self.paper_combo.currentTextChanged.connect(self.change_paper)
        paper_layout.addWidget(QLabel("纸张类型:"))
        paper_layout.addWidget(self.paper_combo)
        
        paper_group.setLayout(paper_layout)
        layout.addWidget(paper_group)
        
        # 墨色选择
        ink_group = QGroupBox("墨色设置")
        ink_layout = QVBoxLayout()
        
        self.ink_combo = QComboBox()
        self.ink_combo.addItems(self.toolkit.ink_colors.keys())
        self.ink_combo.currentTextChanged.connect(self.change_ink)
        ink_layout.addWidget(QLabel("墨色:"))
        ink_layout.addWidget(self.ink_combo)
        
        ink_group.setLayout(ink_layout)
        layout.addWidget(ink_group)
        
        # 智能辅助设置
        ai_group = QGroupBox("智能辅助")
        ai_layout = QVBoxLayout()
        
        self.smoothing_check = QCheckBox("笔画平滑")
        self.smoothing_check.setChecked(True)
        self.smoothing_check.stateChanged.connect(self.toggle_smoothing)
        ai_layout.addWidget(self.smoothing_check)
        
        self.pressure_check = QCheckBox("压力模拟")
        self.pressure_check.setChecked(True)
        self.pressure_check.stateChanged.connect(self.toggle_pressure)
        ai_layout.addWidget(self.pressure_check)
        
        self.guideline_check = QCheckBox("显示辅助线")
        self.guideline_check.setChecked(True)
        self.guideline_check.stateChanged.connect(self.toggle_guidelines)
        ai_layout.addWidget(self.guideline_check)
        
        ai_group.setLayout(ai_layout)
        layout.addWidget(ai_group)
        
        # 操作按钮
        btn_layout = QHBoxLayout()
        
        clear_btn = QPushButton("清空画布")
        clear_btn.clicked.connect(self.canvas.clear_canvas)
        btn_layout.addWidget(clear_btn)
        
        undo_btn = QPushButton("撤销")
        undo_btn.clicked.connect(self.canvas.undo)
        btn_layout.addWidget(undo_btn)
        
        redo_btn = QPushButton("重做")
        redo_btn.clicked.connect(self.canvas.redo)
        btn_layout.addWidget(redo_btn)
        
        layout.addLayout(btn_layout)
        
        # 保存按钮
        save_layout = QHBoxLayout()
        
        save_img_btn = QPushButton("保存图像")
        save_img_btn.clicked.connect(self.save_image)
        save_layout.addWidget(save_img_btn)
        
        save_data_btn = QPushButton("保存数据")
        save_data_btn.clicked.connect(self.save_calligraphy_data)
        save_layout.addWidget(save_data_btn)
        
        load_btn = QPushButton("加载数据")
        load_btn.clicked.connect(self.load_calligraphy_data)
        save_layout.addWidget(load_btn)
        
        layout.addLayout(save_layout)
        
        layout.addStretch()
        self.setLayout(layout)
    
    def change_brush(self, brush_type):
        self.canvas.current_brush = brush_type
    
    def change_brush_size(self, value):
        self.canvas.brush_size = value / 50.0  # 标准化到0.02-2.0范围
    
    def change_paper(self, paper_type):
        self.canvas.current_paper = paper_type
        self.canvas.redraw_all_strokes()
    
    def change_ink(self, ink_type):
        self.canvas.current_ink = ink_type
    
    def toggle_smoothing(self, state):
        self.canvas.stroke_smoothing = (state == Qt.Checked)
    
    def toggle_pressure(self, state):
        self.canvas.pressure_simulation = (state == Qt.Checked)
    
    def toggle_guidelines(self, state):
        self.canvas.guideline_display = (state == Qt.Checked)
        self.canvas.update()
    
    def save_image(self):
        filename, _ = QFileDialog.getSaveFileName(
            self, "保存图像", "", "PNG图像 (*.png);;JPEG图像 (*.jpg)"
        )
        if filename:
            self.canvas.save_image(filename)
    
    def save_calligraphy_data(self):
        filename, _ = QFileDialog.getSaveFileName(
            self, "保存书法数据", "", "书法数据文件 (*.json)"
        )
        if filename:
            self.canvas.save_calligraphy_data(filename)
    
    def load_calligraphy_data(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, "加载书法数据", "", "书法数据文件 (*.json)"
        )
        if filename:
            self.canvas.load_calligraphy_data(filename)


class IntelligentCalligraphySystem(QMainWindow):
    """智能书法系统主窗口"""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("智能书法系统 - 高级工具库")
        self.setGeometry(100, 100, 1200, 800)
        
        # 创建中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建布局
        layout = QHBoxLayout()
        central_widget.setLayout(layout)
        
        # 创建画布
        self.canvas = IntelligentCalligraphyCanvas()
        layout.addWidget(self.canvas, 4)  # 画布占4份空间
        
        # 创建工具面板
        self.tools_panel = CalligraphyToolsPanel(self.canvas)
        layout.addWidget(self.tools_panel, 1)  # 工具面板占1份空间
        
        # 创建菜单栏
        self.create_menubar()
        
        # 状态栏
        self.statusBar().showMessage("智能书法系统已就绪")
    
    def create_menubar(self):
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu("文件")
        
        new_action = QAction("新建", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self.canvas.clear_canvas)
        file_menu.addAction(new_action)
        
        open_action = QAction("打开", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.tools_panel.load_calligraphy_data)
        file_menu.addAction(open_action)
        
        save_action = QAction("保存", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.tools_panel.save_image)
        file_menu.addAction(save_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("退出", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 编辑菜单
        edit_menu = menubar.addMenu("编辑")
        
        undo_action = QAction("撤销", self)
        undo_action.setShortcut("Ctrl+Z")
        undo_action.triggered.connect(self.canvas.undo)
        edit_menu.addAction(undo_action)
        
        redo_action = QAction("重做", self)
        redo_action.setShortcut("Ctrl+Y")
        redo_action.triggered.connect(self.canvas.redo)
        edit_menu.addAction(redo_action)
        
        # 视图菜单
        view_menu = menubar.addMenu("视图")
        
        guidelines_action = QAction("显示辅助线", self, checkable=True)
        guidelines_action.setChecked(True)
        guidelines_action.triggered.connect(
            lambda: self.canvas.set_guideline_display(guidelines_action.isChecked())
        )
        view_menu.addAction(guidelines_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu("帮助")
        
        about_action = QAction("关于", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def show_about(self):
        QMessageBox.about(self, "关于智能书法系统", 
                         "智能书法系统 v1.0\n\n"
                         "基于PyQt5的高级书法创作工具，提供智能笔画分析、"
                         "多种书法风格模拟和专业的书法创作体验。")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 设置应用程序样式
    app.setStyle("Fusion")
    
    # 创建并显示主窗口
    window = IntelligentCalligraphySystem()
    window.show()
    
    sys.exit(app.exec_())