import os
import json
import inspect
from enum import Enum
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass
from pathlib import Path

from PyQt5.QtWidgets import (QApplication, QLineEdit, QWidget, QMainWindow, QPushButton, 
                             QVBoxLayout, QHBoxLayout, QLabel, QComboBox, 
                             QScrollArea, QFrame, QMessageBox, QFileDialog,
                             QSlider, QColorDialog, QSpinBox, QCheckBox,
                             QTabWidget, QGroupBox, QTextEdit, QProgressBar)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QObject, QSize, QPoint
from PyQt5.QtGui import QFont, QPalette, QColor, QIcon, QPixmap, QFontDatabase


class SkinEffect(Enum):
    """皮肤效果枚举"""
    NONE = "none"
    FADE = "fade"
    SLIDE = "slide"
    ZOOM = "zoom"
    ROTATE = "rotate"


@dataclass
class SkinConfig:
    """皮肤配置数据类"""
    name: str
    version: str = "1.0"
    author: str = "Unknown"
    description: str = ""
    primary_color: str = "#3498db"
    secondary_color: str = "#2ecc71"
    background_color: str = "#ecf0f1"
    text_color: str = "#2c3e50"
    accent_color: str = "#e74c3c"
    border_radius: int = 5
    font_family: str = "Segoe UI"
    font_size: int = 10
    animation_speed: int = 300
    effect: SkinEffect = SkinEffect.FADE


class SkinManager(QObject):
    """皮肤管理器类"""
    
    # 信号定义
    skinChanged = pyqtSignal(str)  # 皮肤改变信号
    themeChanged = pyqtSignal(str)  # 主题改变信号（亮/暗）
    
    def __init__(self, app: QApplication):
        super().__init__()
        self.app = app
        self.current_skin = "default"
        self.current_theme = "light"
        self.skins: Dict[str, SkinConfig] = {}
        self.custom_styles: Dict[str, str] = {}
        self.widget_styles: Dict[str, Dict[str, str]] = {}
        self.animation_timer = QTimer()
        self.animation_timer.setSingleShot(True)
        self.animation_timer.timeout.connect(self._apply_animation_finish)
        self.is_animating = False
        
        # 加载默认皮肤
        self._load_default_skins()
        
    def _load_default_skins(self):
        """加载默认皮肤"""
        # 默认浅色皮肤
        default_light = SkinConfig(
            name="default_light",
            description="默认浅色主题",
            primary_color="#3498db",
            secondary_color="#2ecc71",
            background_color="#ecf0f1",
            text_color="#2c3e50",
            accent_color="#e74c3c"
        )
        self.skins["default_light"] = default_light
        
        # 默认深色皮肤
        default_dark = SkinConfig(
            name="default_dark",
            description="默认深色主题",
            primary_color="#2980b9",
            secondary_color="#27ae60",
            background_color="#2c3e50",
            text_color="#ecf0f1",
            accent_color="#c0392b"
        )
        self.skins["default_dark"] = default_dark
        
        # 蓝色主题
        blue_theme = SkinConfig(
            name="blue_ocean",
            description="蓝色海洋主题",
            primary_color="#3498db",
            secondary_color="#1abc9c",
            background_color="#34495e",
            text_color="#ecf0f1",
            accent_color="#e74c3c"
        )
        self.skins["blue_ocean"] = blue_theme
        
        # 绿色主题
        green_theme = SkinConfig(
            name="green_forest",
            description="绿色森林主题",
            primary_color="#27ae60",
            secondary_color="#2ecc71",
            background_color="#1e8449",
            text_color="#ecf0f1",
            accent_color="#e67e22"
        )
        self.skins["green_forest"] = green_theme
        
        self.current_skin = "default_light"
        
    def load_skin_from_file(self, file_path: str) -> bool:
        """从文件加载皮肤配置"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            skin_config = SkinConfig(
                name=data.get('name', 'unnamed'),
                version=data.get('version', '1.0'),
                author=data.get('author', 'Unknown'),
                description=data.get('description', ''),
                primary_color=data.get('primary_color', '#3498db'),
                secondary_color=data.get('secondary_color', '#2ecc71'),
                background_color=data.get('background_color', '#ecf0f1'),
                text_color=data.get('text_color', '#2c3e50'),
                accent_color=data.get('accent_color', '#e74c3c'),
                border_radius=data.get('border_radius', 5),
                font_family=data.get('font_family', 'Segoe UI'),
                font_size=data.get('font_size', 10),
                animation_speed=data.get('animation_speed', 300),
                effect=SkinEffect(data.get('effect', 'fade'))
            )
            
            self.skins[skin_config.name] = skin_config
            return True
        except Exception as e:
            print(f"加载皮肤文件失败: {e}")
            return False
    
    def save_skin_to_file(self, skin_name: str, file_path: str) -> bool:
        """保存皮肤配置到文件"""
        if skin_name not in self.skins:
            return False
            
        try:
            skin = self.skins[skin_name]
            data = {
                'name': skin.name,
                'version': skin.version,
                'author': skin.author,
                'description': skin.description,
                'primary_color': skin.primary_color,
                'secondary_color': skin.secondary_color,
                'background_color': skin.background_color,
                'text_color': skin.text_color,
                'accent_color': skin.accent_color,
                'border_radius': skin.border_radius,
                'font_family': skin.font_family,
                'font_size': skin.font_size,
                'animation_speed': skin.animation_speed,
                'effect': skin.effect.value
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"保存皮肤文件失败: {e}")
            return False
    
    def apply_skin(self, skin_name: str, effect: SkinEffect = None, 
                  target_widget: QWidget = None) -> bool:
        """应用指定皮肤"""
        if skin_name not in self.skins:
            return False
            
        if self.is_animating:
            return False
            
        self.current_skin = skin_name
        skin = self.skins[skin_name]
        
        # 设置效果
        applied_effect = effect if effect else skin.effect
        
        # 应用动画效果
        if applied_effect != SkinEffect.NONE and target_widget:
            self._apply_with_animation(target_widget, applied_effect, skin)
        else:
            self._apply_skin_directly(skin)
            
        self.skinChanged.emit(skin_name)
        return True
    
    def _apply_with_animation(self, widget: QWidget, effect: SkinEffect, skin: SkinConfig):
        """应用皮肤并带有动画效果"""
        self.is_animating = True
        
        if effect == SkinEffect.FADE:
            self._fade_animation(widget, skin)
        elif effect == SkinEffect.SLIDE:
            self._slide_animation(widget, skin)
        elif effect == SkinEffect.ZOOM:
            self._zoom_animation(widget, skin)
        elif effect == SkinEffect.ROTATE:
            self._rotate_animation(widget, skin)
        
        # 设置动画计时器
        self.animation_timer.start(skin.animation_speed)
    
    def _apply_animation_finish(self):
        """动画完成后的处理"""
        self.is_animating = False
    
    def _fade_animation(self, widget: QWidget, skin: SkinConfig):
        """淡入淡出动画效果"""
        # 简化实现 - 实际应用中可以使用QPropertyAnimation
        widget.setWindowOpacity(0.7)
        self._apply_skin_directly(skin)
        widget.setWindowOpacity(1.0)
    
    def _slide_animation(self, widget: QWidget, skin: SkinConfig):
        """滑动动画效果"""
        # 简化实现
        old_pos = widget.pos()
        widget.move(old_pos + QPoint(10, 0))
        self._apply_skin_directly(skin)
        widget.move(old_pos)
    
    def _zoom_animation(self, widget: QWidget, skin: SkinConfig):
        """缩放动画效果"""
        # 简化实现
        old_size = widget.size()
        widget.resize(old_size * 0.95)
        self._apply_skin_directly(skin)
        widget.resize(old_size)
    
    def _rotate_animation(self, widget: QWidget, skin: SkinConfig):
        """旋转动画效果（仅对支持旋转的控件有效）"""
        # 简化实现
        self._apply_skin_directly(skin)
    
    def _apply_skin_directly(self, skin: SkinConfig):
        """直接应用皮肤样式"""
        # 设置应用程序样式表
        stylesheet = self._generate_stylesheet(skin)
        self.app.setStyleSheet(stylesheet)
        
        # 设置字体
        font = QFont(skin.font_family, skin.font_size)
        self.app.setFont(font)
        
        # 设置调色板
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(skin.background_color))
        palette.setColor(QPalette.WindowText, QColor(skin.text_color))
        palette.setColor(QPalette.Base, QColor(skin.background_color))
        palette.setColor(QPalette.AlternateBase, QColor(skin.primary_color))
        palette.setColor(QPalette.Text, QColor(skin.text_color))
        palette.setColor(QPalette.Button, QColor(skin.primary_color))
        palette.setColor(QPalette.ButtonText, QColor(skin.text_color))
        palette.setColor(QPalette.Highlight, QColor(skin.accent_color))
        self.app.setPalette(palette)
    
    def _generate_stylesheet(self, skin: SkinConfig) -> str:
        """生成样式表"""
        return f"""
        QMainWindow, QDialog, QWidget {{
            background-color: {skin.background_color};
            color: {skin.text_color};
            font-family: "{skin.font_family}";
            font-size: {skin.font_size}px;
        }}
        
        QPushButton {{
            background-color: {skin.primary_color};
            color: {skin.text_color};
            border-radius: {skin.border_radius}px;
            padding: 5px 10px;
            border: none;
            font-weight: bold;
        }}
        
        QPushButton:hover {{
            background-color: {self._darken_color(skin.primary_color, 10)};
        }}
        
        QPushButton:pressed {{
            background-color: {self._darken_color(skin.primary_color, 20)};
        }}
        
        QLabel {{
            color: {skin.text_color};
            font-family: "{skin.font_family}";
            font-size: {skin.font_size}px;
        }}
        
        QComboBox {{
            background-color: {skin.background_color};
            color: {skin.text_color};
            border: 1px solid {skin.primary_color};
            border-radius: {skin.border_radius}px;
            padding: 5px;
        }}
        
        QSlider::groove:horizontal {{
            border: 1px solid {skin.primary_color};
            height: 5px;
            background: {skin.background_color};
            border-radius: 2px;
        }}
        
        QSlider::handle:horizontal {{
            background: {skin.accent_color};
            border: 1px solid {self._darken_color(skin.accent_color, 20)};
            width: 15px;
            margin: -5px 0;
            border-radius: 7px;
        }}
        
        QProgressBar {{
            border: 1px solid {skin.primary_color};
            border-radius: {skin.border_radius}px;
            text-align: center;
            background-color: {skin.background_color};
        }}
        
        QProgressBar::chunk {{
            background-color: {skin.secondary_color};
            border-radius: {skin.border_radius}px;
        }}
        
        QTabWidget::pane {{
            border: 1px solid {skin.primary_color};
            background-color: {skin.background_color};
        }}
        
        QTabBar::tab {{
            background-color: {skin.background_color};
            color: {skin.text_color};
            padding: 8px 12px;
            border-top-left-radius: {skin.border_radius}px;
            border-top-right-radius: {skin.border_radius}px;
            border: 1px solid {skin.primary_color};
            margin-right: 2px;
        }}
        
        QTabBar::tab:selected {{
            background-color: {skin.primary_color};
        }}
        
        QGroupBox {{
            font-weight: bold;
            border: 1px solid {skin.primary_color};
            border-radius: {skin.border_radius}px;
            margin-top: 10px;
            padding-top: 10px;
        }}
        
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px 0 5px;
        }}
        
        QScrollArea {{
            border: 1px solid {skin.primary_color};
            border-radius: {skin.border_radius}px;
            background-color: {skin.background_color};
        }}
        
        QTextEdit, QLineEdit {{
            background-color: {skin.background_color};
            color: {skin.text_color};
            border: 1px solid {skin.primary_color};
            border-radius: {skin.border_radius}px;
            padding: 5px;
        }}
        
        QCheckBox {{
            color: {skin.text_color};
            spacing: 5px;
        }}
        
        QCheckBox::indicator {{
            width: 15px;
            height: 15px;
            border: 1px solid {skin.primary_color};
            border-radius: 3px;
            background-color: {skin.background_color};
        }}
        
        QCheckBox::indicator:checked {{
            background-color: {skin.secondary_color};
            border: 1px solid {skin.secondary_color};
        }}
        """
    
    def _darken_color(self, color_hex: str, percent: int) -> str:
        """加深颜色"""
        color = QColor(color_hex)
        h, s, l, a = color.getHsl()
        l = max(0, l * (100 - percent) / 100)
        color.setHsl(h, s, int(l), a)
        return color.name()
    
    def toggle_theme(self) -> str:
        """切换亮/暗主题"""
        if self.current_theme == "light":
            # 切换到暗色主题
            dark_skin = next((skin for skin in self.skins.values() 
                             if "dark" in skin.name.lower()), None)
            if dark_skin:
                self.apply_skin(dark_skin.name)
                self.current_theme = "dark"
        else:
            # 切换到亮色主题
            light_skin = next((skin for skin in self.skins.values() 
                              if "light" in skin.name.lower()), None)
            if light_skin:
                self.apply_skin(light_skin.name)
                self.current_theme = "light"
        
        self.themeChanged.emit(self.current_theme)
        return self.current_theme
    
    def get_available_skins(self) -> List[str]:
        """获取可用皮肤列表"""
        return list(self.skins.keys())
    
    def create_custom_skin(self, name: str, **kwargs) -> bool:
        """创建自定义皮肤"""
        if name in self.skins:
            return False
            
        # 基于默认皮肤创建
        base_skin = self.skins["default_light"]
        skin_data = {
            'name': name,
            'version': kwargs.get('version', base_skin.version),
            'author': kwargs.get('author', base_skin.author),
            'description': kwargs.get('description', base_skin.description),
            'primary_color': kwargs.get('primary_color', base_skin.primary_color),
            'secondary_color': kwargs.get('secondary_color', base_skin.secondary_color),
            'background_color': kwargs.get('background_color', base_skin.background_color),
            'text_color': kwargs.get('text_color', base_skin.text_color),
            'accent_color': kwargs.get('accent_color', base_skin.accent_color),
            'border_radius': kwargs.get('border_radius', base_skin.border_radius),
            'font_family': kwargs.get('font_family', base_skin.font_family),
            'font_size': kwargs.get('font_size', base_skin.font_size),
            'animation_speed': kwargs.get('animation_speed', base_skin.animation_speed),
            'effect': kwargs.get('effect', base_skin.effect)
        }
        
        self.skins[name] = SkinConfig(**skin_data)
        return True
    
    def get_skin_info(self, skin_name: str) -> Optional[Dict[str, Any]]:
        """获取皮肤信息"""
        if skin_name not in self.skins:
            return None
            
        skin = self.skins[skin_name]
        return {
            'name': skin.name,
            'version': skin.version,
            'author': skin.author,
            'description': skin.description,
            'colors': {
                'primary': skin.primary_color,
                'secondary': skin.secondary_color,
                'background': skin.background_color,
                'text': skin.text_color,
                'accent': skin.accent_color
            },
            'border_radius': skin.border_radius,
            'font_family': skin.font_family,
            'font_size': skin.font_size,
            'animation_speed': skin.animation_speed,
            'effect': skin.effect.value
        }


class SkinPreviewWidget(QWidget):
    """皮肤预览组件"""
    
    def __init__(self, skin_manager: SkinManager):
        super().__init__()
        self.skin_manager = skin_manager
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout()
        
        # 预览标题
        title_label = QLabel("皮肤预览")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; margin: 10px;")
        layout.addWidget(title_label)
        
        # 预览区域
        preview_frame = QFrame()
        preview_frame.setFrameStyle(QFrame.Box)
        preview_layout = QVBoxLayout(preview_frame)
        
        # 添加各种控件用于预览
        button = QPushButton("示例按钮")
        preview_layout.addWidget(button)
        
        slider = QSlider(Qt.Horizontal)
        slider.setValue(50)
        preview_layout.addWidget(slider)
        
        progress = QProgressBar()
        progress.setValue(75)
        preview_layout.addWidget(progress)
        
        checkbox = QCheckBox("示例复选框")
        preview_layout.addWidget(checkbox)
        
        combo = QComboBox()
        combo.addItems(["选项1", "选项2", "选项3"])
        preview_layout.addWidget(combo)
        
        text_edit = QTextEdit()
        text_edit.setMaximumHeight(60)
        text_edit.setPlainText("示例文本编辑框")
        preview_layout.addWidget(text_edit)
        
        layout.addWidget(preview_frame)
        self.setLayout(layout)


class SkinEditor(QMainWindow):
    """皮肤编辑器窗口"""
    
    def __init__(self, skin_manager: SkinManager):
        super().__init__()
        self.skin_manager = skin_manager
        self.current_skin_name = "default_light"
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("皮肤编辑器")
        self.setGeometry(100, 100, 800, 600)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QHBoxLayout(central_widget)
        
        # 左侧编辑面板
        edit_panel = QTabWidget()
        
        # 基本设置标签页
        basic_tab = QWidget()
        basic_layout = QVBoxLayout(basic_tab)
        
        # 皮肤名称
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("皮肤名称:"))
        self.name_edit = QLineEdit()
        name_layout.addWidget(self.name_edit)
        basic_layout.addLayout(name_layout)
        
        # 颜色设置
        colors_group = QGroupBox("颜色设置")
        colors_layout = QVBoxLayout(colors_group)
        
        self.color_edits = {}
        color_names = {
            'primary_color': '主色调',
            'secondary_color': '辅助色',
            'background_color': '背景色',
            'text_color': '文字色',
            'accent_color': '强调色'
        }
        
        for color_key, color_label in color_names.items():
            color_layout = QHBoxLayout()
            color_layout.addWidget(QLabel(color_label))
            color_edit = QLineEdit()
            color_edit.setMaximumWidth(100)
            color_button = QPushButton("选择")
            color_button.clicked.connect(
                lambda checked, key=color_key, edit=color_edit: self.choose_color(key, edit)
            )
            color_layout.addWidget(color_edit)
            color_layout.addWidget(color_button)
            colors_layout.addLayout(color_layout)
            self.color_edits[color_key] = color_edit
        
        basic_layout.addWidget(colors_group)
        
        # 其他设置
        other_group = QGroupBox("其他设置")
        other_layout = QVBoxLayout(other_group)
        
        # 边框半径
        radius_layout = QHBoxLayout()
        radius_layout.addWidget(QLabel("边框半径:"))
        self.radius_spin = QSpinBox()
        self.radius_spin.setRange(0, 20)
        self.radius_spin.setValue(5)
        radius_layout.addWidget(self.radius_spin)
        other_layout.addLayout(radius_layout)
        
        # 字体大小
        font_size_layout = QHBoxLayout()
        font_size_layout.addWidget(QLabel("字体大小:"))
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 20)
        self.font_size_spin.setValue(10)
        font_size_layout.addWidget(self.font_size_spin)
        other_layout.addLayout(font_size_layout)
        
        # 动画速度
        anim_speed_layout = QHBoxLayout()
        anim_speed_layout.addWidget(QLabel("动画速度(ms):"))
        self.anim_speed_spin = QSpinBox()
        self.anim_speed_spin.setRange(100, 1000)
        self.anim_speed_spin.setValue(300)
        anim_speed_layout.addWidget(self.anim_speed_spin)
        other_layout.addLayout(anim_speed_layout)
        
        basic_layout.addWidget(other_group)
        
        # 保存按钮
        save_button = QPushButton("保存皮肤")
        save_button.clicked.connect(self.save_skin)
        basic_layout.addWidget(save_button)
        
        edit_panel.addTab(basic_tab, "基本设置")
        
        # 高级设置标签页（简化实现）
        advanced_tab = QWidget()
        advanced_layout = QVBoxLayout(advanced_tab)
        advanced_layout.addWidget(QLabel("高级皮肤设置"))
        # 这里可以添加更多高级设置选项
        edit_panel.addTab(advanced_tab, "高级设置")
        
        layout.addWidget(edit_panel, 1)
        
        # 右侧预览面板
        self.preview_widget = SkinPreviewWidget(self.skin_manager)
        layout.addWidget(self.preview_widget, 1)
        
        # 加载当前皮肤设置
        self.load_current_skin()
    
    def choose_color(self, color_key: str, edit_widget: QLineEdit):
        """选择颜色"""
        current_color = QColor(edit_widget.text())
        color = QColorDialog.getColor(current_color, self, f"选择{color_key}")
        if color.isValid():
            edit_widget.setText(color.name())
            self.preview_update()
    
    def load_current_skin(self):
        """加载当前皮肤设置到编辑器"""
        skin_info = self.skin_manager.get_skin_info(self.current_skin_name)
        if skin_info:
            self.name_edit.setText(skin_info['name'])
            colors = skin_info['colors']
            self.color_edits['primary_color'].setText(colors['primary'])
            self.color_edits['secondary_color'].setText(colors['secondary'])
            self.color_edits['background_color'].setText(colors['background'])
            self.color_edits['text_color'].setText(colors['text'])
            self.color_edits['accent_color'].setText(colors['accent'])
            self.radius_spin.setValue(skin_info['border_radius'])
            self.font_size_spin.setValue(skin_info['font_size'])
            self.anim_speed_spin.setValue(skin_info['animation_speed'])
    
    def preview_update(self):
        """预览更新"""
        # 创建临时皮肤配置进行预览
        temp_skin = SkinConfig(
            name="preview",
            primary_color=self.color_edits['primary_color'].text(),
            secondary_color=self.color_edits['secondary_color'].text(),
            background_color=self.color_edits['background_color'].text(),
            text_color=self.color_edits['text_color'].text(),
            accent_color=self.color_edits['accent_color'].text(),
            border_radius=self.radius_spin.value(),
            font_size=self.font_size_spin.value()
        )
        
        # 应用预览皮肤
        self.skin_manager._apply_skin_directly(temp_skin)
    
    def save_skin(self):
        """保存皮肤"""
        skin_name = self.name_edit.text()
        if not skin_name:
            QMessageBox.warning(self, "错误", "皮肤名称不能为空")
            return
        
        # 创建或更新皮肤
        self.skin_manager.create_custom_skin(
            skin_name,
            primary_color=self.color_edits['primary_color'].text(),
            secondary_color=self.color_edits['secondary_color'].text(),
            background_color=self.color_edits['background_color'].text(),
            text_color=self.color_edits['text_color'].text(),
            accent_color=self.color_edits['accent_color'].text(),
            border_radius=self.radius_spin.value(),
            font_size=self.font_size_spin.value(),
            animation_speed=self.anim_speed_spin.value()
        )
        
        QMessageBox.information(self, "成功", f"皮肤 '{skin_name}' 已保存")


class SkinSelector(QWidget):
    """皮肤选择器组件"""
    
    def __init__(self, skin_manager: SkinManager):
        super().__init__()
        self.skin_manager = skin_manager
        self.init_ui()
        
        # 连接信号
        self.skin_manager.skinChanged.connect(self.on_skin_changed)
    
    def init_ui(self):
        """初始化UI"""
        layout = QHBoxLayout()
        
        # 皮肤选择下拉框
        layout.addWidget(QLabel("选择皮肤:"))
        self.skin_combo = QComboBox()
        self.skin_combo.addItems(self.skin_manager.get_available_skins())
        self.skin_combo.currentTextChanged.connect(self.on_skin_selected)
        layout.addWidget(self.skin_combo)
        
        # 主题切换按钮
        self.theme_button = QPushButton("切换主题")
        self.theme_button.clicked.connect(self.skin_manager.toggle_theme)
        layout.addWidget(self.theme_button)
        
        # 皮肤编辑器按钮
        self.editor_button = QPushButton("皮肤编辑器")
        self.editor_button.clicked.connect(self.open_skin_editor)
        layout.addWidget(self.editor_button)
        
        self.setLayout(layout)
    
    def on_skin_selected(self, skin_name: str):
        """皮肤选择事件"""
        self.skin_manager.apply_skin(skin_name, target_widget=self.window())
    
    def on_skin_changed(self, skin_name: str):
        """皮肤改变事件"""
        # 更新下拉框当前选项
        index = self.skin_combo.findText(skin_name)
        if index >= 0:
            self.skin_combo.setCurrentIndex(index)
    
    def open_skin_editor(self):
        """打开皮肤编辑器"""
        self.editor = SkinEditor(self.skin_manager)
        self.editor.show()


class AdvancedSkinSystem:
    """高级皮肤系统主类"""
    
    def __init__(self, app: QApplication):
        self.app = app
        self.skin_manager = SkinManager(app)
        self.selector = None
    
    def enable_skin_selector(self, parent_widget: QWidget) -> SkinSelector:
        """启用皮肤选择器"""
        self.selector = SkinSelector(self.skin_manager)
        return self.selector
    
    def apply_skin(self, skin_name: str, effect: SkinEffect = None) -> bool:
        """应用皮肤"""
        return self.skin_manager.apply_skin(skin_name, effect)
    
    def get_available_skins(self) -> List[str]:
        """获取可用皮肤列表"""
        return self.skin_manager.get_available_skins()
    
    def create_custom_skin(self, name: str, **kwargs) -> bool:
        """创建自定义皮肤"""
        return self.skin_manager.create_custom_skin(name, **kwargs)
    
    def load_skin_file(self, file_path: str) -> bool:
        """加载皮肤文件"""
        return self.skin_manager.load_skin_from_file(file_path)
    
    def save_skin_file(self, skin_name: str, file_path: str) -> bool:
        """保存皮肤文件"""
        return self.skin_manager.save_skin_to_file(skin_name, file_path)


# 使用示例
class ExampleApp(QMainWindow):
    """示例应用程序"""
    
    def __init__(self):
        super().__init__()
        self.skin_system = AdvancedSkinSystem(QApplication.instance())
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("高级皮肤系统示例")
        self.setGeometry(100, 100, 600, 400)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        
        # 添加皮肤选择器
        skin_selector = self.skin_system.enable_skin_selector(self)
        layout.addWidget(skin_selector)
        
        # 添加示例内容
        content_layout = QHBoxLayout()
        
        # 左侧控件组
        left_group = QGroupBox("控件示例")
        left_layout = QVBoxLayout(left_group)
        
        left_layout.addWidget(QLabel("这是一个标签"))
        left_layout.addWidget(QPushButton("这是一个按钮"))
        
        slider = QSlider(Qt.Horizontal)
        slider.setValue(50)
        left_layout.addWidget(slider)
        
        progress = QProgressBar()
        progress.setValue(75)
        left_layout.addWidget(progress)
        
        checkbox = QCheckBox("这是一个复选框")
        left_layout.addWidget(checkbox)
        
        content_layout.addWidget(left_group)
        
        # 右侧控件组
        right_group = QGroupBox("更多示例")
        right_layout = QVBoxLayout(right_group)
        
        combo = QComboBox()
        combo.addItems(["选项1", "选项2", "选项3"])
        right_layout.addWidget(combo)
        
        text_edit = QTextEdit()
        text_edit.setPlainText("这是一个文本编辑框")
        right_layout.addWidget(text_edit)
        
        content_layout.addWidget(right_group)
        
        layout.addLayout(content_layout)
        
        # 应用默认皮肤
        self.skin_system.apply_skin("default_light")


if __name__ == "__main__":
    import sys
    
    app = QApplication(sys.argv)
    
    # 创建示例应用
    example = ExampleApp()
    example.show()
    
    sys.exit(app.exec_())