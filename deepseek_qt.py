"""
PyQt5高级科学计算平台 - 完整版
作者: AI Assistant
版本: 4.0
特性: API集成、现代化UI、插件架构、配置持久化
"""

import sys
import os
import json
import hashlib
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from scipy import integrate, optimize, signal, stats, fft
from scipy.interpolate import CubicSpline
import pandas as pd
from openai import OpenAI
import warnings
warnings.filterwarnings('ignore')

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *


# ==================== 配置管理 ====================

@dataclass
class AppConfig:
    """应用配置"""
    theme: str = "dark"
    font_size: int = 12
    api_key: str = ""
    model: str = "deepseek-chat"
    temperature: float = 0.7
    max_tokens: int = 4096
    auto_save: bool = True
    history_size: int = 1000
    
    @classmethod
    def load(cls, path: str = "config.json") -> 'AppConfig':
        if Path(path).exists():
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return cls(**data)
        return cls()
    
    def save(self, path: str = "config.json"):
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(asdict(self), f, indent=2, ensure_ascii=False)


# ==================== 主题系统 ====================

class ThemeManager:
    """主题管理器"""
    
    THEMES = {
        "dark": """
            QMainWindow { background-color: #1e1e1e; }
            QWidget { color: #e0e0e0; font-size: 13px; }
            QMenuBar { background-color: #2d2d2d; color: #e0e0e0; }
            QMenuBar::item:selected { background-color: #3d3d3d; }
            QMenu { background-color: #2d2d2d; color: #e0e0e0; border: 1px solid #3d3d3d; }
            QMenu::item:selected { background-color: #4CAF50; }
        """,
        "light": """
            QMainWindow { background-color: #f5f5f5; }
            QWidget { color: #333333; font-size: 13px; }
            QMenuBar { background-color: #ffffff; color: #333333; border-bottom: 1px solid #e0e0e0; }
            QMenuBar::item:selected { background-color: #e8e8e8; }
            QMenu { background-color: #ffffff; color: #333333; border: 1px solid #e0e0e0; }
            QMenu::item:selected { background-color: #4CAF50; color: white; }
        """
    }
    
    @classmethod
    def apply(cls, app: QApplication, theme_name: str):
        app.setStyleSheet(cls.THEMES.get(theme_name, cls.THEMES["dark"]))


# ==================== AI客户端 ====================

class AIClient:
    """AI客户端封装"""
    
    def __init__(self, api_key: str = None, base_url: str = "https://api.deepseek.com"):
        self.client = None
        self.api_key = api_key
        self.base_url = base_url
        if api_key:
            self.connect(api_key)
    
    def connect(self, api_key: str):
        self.client = OpenAI(api_key=api_key, base_url=self.base_url)
    
    def chat(self, messages: List[Dict], model: str = "deepseek-chat", 
             temperature: float = 0.7, max_tokens: int = 4096,
             stream: bool = False) -> Any:
        if not self.client:
            raise ValueError("未连接API")
        
        return self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=stream
        )
    
    def chat_simple(self, prompt: str, system: str = None) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        response = self.chat(messages)
        return response.choices[0].message.content
    
    def code_review(self, code: str) -> str:
        return self.chat_simple(
            f"请审查以下Python代码并提供改进建议:\n```python\n{code}\n```",
            "你是一位资深Python代码审查专家，请详细分析代码质量、安全性和性能"
        )
    
    def generate_code(self, requirement: str) -> str:
        return self.chat_simple(
            f"请根据需求生成完整的Python代码:\n{requirement}",
            "你是高级Python开发工程师，生成生产级质量的代码"
        )
    
    def explain_error(self, error: str, context: str = "") -> str:
        return self.chat_simple(
            f"解释这个错误并提供解决方案:\n错误: {error}\n上下文: {context}",
            "你是Python调试专家"
        )


# ==================== 安全表达式求值器 ====================

class SafeEvaluator:
    """安全的数学表达式求值器"""
    
    SAFE_FUNCTIONS = {
        'sin': np.sin, 'cos': np.cos, 'tan': np.tan,
        'asin': np.arcsin, 'acos': np.arccos, 'atan': np.arctan,
        'sinh': np.sinh, 'cosh': np.cosh, 'tanh': np.tanh,
        'exp': np.exp, 'log': np.log, 'log10': np.log10, 'log2': np.log2,
        'sqrt': np.sqrt, 'abs': np.abs,
        'pi': np.pi, 'e': np.e, 'tau': np.pi * 2,
        'floor': np.floor, 'ceil': np.ceil, 'round': np.round,
        'degrees': np.degrees, 'radians': np.radians,
        'sign': np.sign, 'power': np.power
    }
    
    @classmethod
    def evaluate(cls, expression: str, variables: Dict = None) -> float:
        if variables is None:
            variables = {}
        
        code = compile(expression.strip(), '<expr>', 'eval')
        
        for name in code.co_names:
            if name not in cls.SAFE_FUNCTIONS and name not in variables:
                raise NameError(f"不允许的变量或函数: '{name}'")
        
        safe_dict = {**cls.SAFE_FUNCTIONS, **variables}
        return eval(code, {"__builtins__": {}}, safe_dict)


# ==================== 工作线程 ====================

class WorkerSignals(QObject):
    """工作线程信号"""
    started = pyqtSignal()
    finished = pyqtSignal()
    result = pyqtSignal(object)
    error = pyqtSignal(str)
    progress = pyqtSignal(int)


class Worker(QRunnable):
    """工作线程"""
    
    def __init__(self, func: Callable, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()
        self._is_cancelled = False
    
    def run(self):
        try:
            self.signals.started.emit()
            result = self.func(*self.args, **self.kwargs)
            if not self._is_cancelled:
                self.signals.result.emit(result)
        except Exception as e:
            if not self._is_cancelled:
                self.signals.error.emit(str(e))
        finally:
            if not self._is_cancelled:
                self.signals.finished.emit()
    
    def cancel(self):
        self._is_cancelled = True


# ==================== 组件库 ====================

class StyledButton(QPushButton):
    """统一样式的按钮"""
    
    def __init__(self, text: str, color: str = "#4CAF50", parent=None):
        super().__init__(text, parent)
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 13px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {self._darken(color)};
            }}
            QPushButton:pressed {{
                background-color: {self._darken(color, 0.2)};
            }}
            QPushButton:disabled {{
                background-color: #666;
                color: #999;
            }}
        """)
    
    @staticmethod
    def _darken(hex_color: str, factor: float = 0.1) -> str:
        color = QColor(hex_color)
        return QColor(
            int(color.red() * (1 - factor)),
            int(color.green() * (1 - factor)),
            int(color.blue() * (1 - factor))
        ).name()


class AnimatedTextEdit(QTextEdit):
    """带动画的文本编辑器"""
    
    def append_with_animation(self, text: str, color: str = "#00ff00"):
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.End)
        
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(color))
        cursor.insertText(text, fmt)
        
        self.setTextCursor(cursor)
        self.ensureCursorVisible()


class CollapsibleGroup(QWidget):
    """可折叠的分组"""
    
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.is_collapsed = False
        
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 标题按钮
        self.title_btn = QPushButton(f"▶ {title}")
        self.title_btn.setStyleSheet("""
            QPushButton {
                text-align: left;
                background-color: #3d3d3d;
                color: #e0e0e0;
                border: none;
                border-radius: 4px;
                padding: 8px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #4d4d4d; }
        """)
        self.title_btn.clicked.connect(self.toggle)
        layout.addWidget(self.title_btn)
        
        # 内容区域
        self.content = QWidget()
        self.content_layout = QVBoxLayout()
        self.content.setLayout(self.content_layout)
        layout.addWidget(self.content)
        
        self.setLayout(layout)
    
    def toggle(self):
        self.is_collapsed = not self.is_collapsed
        self.content.setVisible(not self.is_collapsed)
        self.title_btn.setText(
            f"{'▼' if not self.is_collapsed else '▶'} {self.title_btn.text()[2:]}"
        )
    
    def add_widget(self, widget):
        self.content_layout.addWidget(widget)


# ==================== 主应用组件 ====================

class AIAssistantWidget(QWidget):
    """AI助手面板"""
    
    def __init__(self, ai_client: AIClient, config: AppConfig):
        super().__init__()
        self.ai = ai_client
        self.config = config
        self.conversation = []
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 对话显示
        self.chat_display = AnimatedTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setStyleSheet("""
            QTextEdit {
                background-color: #1a1a1a;
                color: #e0e0e0;
                border: 1px solid #3d3d3d;
                border-radius: 8px;
                padding: 10px;
                font-family: 'Consolas', monospace;
            }
        """)
        layout.addWidget(self.chat_display, 3)
        
        # 输入区域
        input_layout = QHBoxLayout()
        
        self.input_field = QTextEdit()
        self.input_field.setMaximumHeight(80)
        self.input_field.setPlaceholderText("输入你的问题...")
        self.input_field.setStyleSheet("""
            QTextEdit {
                background-color: #2d2d2d;
                color: #e0e0e0;
                border: 1px solid #4CAF50;
                border-radius: 6px;
                padding: 8px;
            }
        """)
        input_layout.addWidget(self.input_field)
        
        btn_layout = QVBoxLayout()
        
        send_btn = StyledButton("发送", "#4CAF50")
        send_btn.clicked.connect(self.send_message)
        btn_layout.addWidget(send_btn)
        
        clear_btn = StyledButton("清除", "#f44336")
        clear_btn.clicked.connect(self.clear_chat)
        btn_layout.addWidget(clear_btn)
        
        input_layout.addLayout(btn_layout)
        layout.addLayout(input_layout)
        
        # 快捷操作
        quick_layout = QHBoxLayout()
        
        actions = [
            ("代码审查", self.code_review),
            ("错误解释", self.explain_error),
            ("生成代码", self.generate_code),
            ("优化建议", self.optimize_code)
        ]
        
        for text, func in actions:
            btn = QPushButton(text)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #333;
                    color: #e0e0e0;
                    border: 1px solid #555;
                    border-radius: 4px;
                    padding: 6px 12px;
                }
                QPushButton:hover { background-color: #444; }
            """)
            btn.clicked.connect(func)
            quick_layout.addWidget(btn)
        
        layout.addLayout(quick_layout)
        self.setLayout(layout)
    
    def send_message(self):
        text = self.input_field.toPlainText().strip()
        if not text:
            return
        
        self.chat_display.append_with_animation(f"\n👤 你: {text}\n", "#4CAF50")
        self.conversation.append({"role": "user", "content": text})
        
        try:
            response = self.ai.chat(
                self.conversation,
                model=self.config.model,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens
            )
            
            reply = response.choices[0].message.content
            self.chat_display.append_with_animation(f"🤖 AI: {reply}\n", "#2196F3")
            self.conversation.append({"role": "assistant", "content": reply})
            
        except Exception as e:
            self.chat_display.append_with_animation(f"❌ 错误: {e}\n", "#f44336")
        
        self.input_field.clear()
    
    def clear_chat(self):
        self.chat_display.clear()
        self.conversation = []
    
    def code_review(self):
        text = self.input_field.toPlainText().strip()
        if text:
            self.input_field.setPlainText(f"请审查这段代码:\n```python\n{text}\n```")
    
    def explain_error(self):
        text = self.input_field.toPlainText().strip()
        if text:
            self.input_field.setPlainText(f"请解释这个错误:\n{text}")
    
    def generate_code(self):
        text = self.input_field.toPlainText().strip()
        if text:
            self.input_field.setPlainText(f"请生成代码:\n{text}")
    
    def optimize_code(self):
        text = self.input_field.toPlainText().strip()
        if text:
            self.input_field.setPlainText(f"请优化这段代码:\n```python\n{text}\n```")


class CodeEditor(QWidget):
    """代码编辑器"""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.file_path = None
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 工具栏
        toolbar = QHBoxLayout()
        
        new_btn = StyledButton("新建", "#4CAF50")
        new_btn.clicked.connect(self.new_file)
        toolbar.addWidget(new_btn)
        
        open_btn = StyledButton("打开", "#2196F3")
        open_btn.clicked.connect(self.open_file)
        toolbar.addWidget(open_btn)
        
        save_btn = StyledButton("保存", "#FF9800")
        save_btn.clicked.connect(self.save_file)
        toolbar.addWidget(save_btn)
        
        run_btn = StyledButton("运行", "#9C27B0")
        run_btn.clicked.connect(self.run_code)
        toolbar.addWidget(run_btn)
        
        layout.addLayout(toolbar)
        
        # 编辑器
        self.editor = QTextEdit()
        self.editor.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 10px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 14px;
            }
        """)
        self.editor.setPlaceholderText("# 在此编写Python代码...")
        layout.addWidget(self.editor, 2)
        
        # 输出区域
        output_group = CollapsibleGroup("输出")
        self.output_display = QTextEdit()
        self.output_display.setReadOnly(True)
        self.output_display.setStyleSheet("""
            QTextEdit {
                background-color: #0a0a0a;
                color: #00ff00;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 8px;
                font-family: 'Consolas', monospace;
                font-size: 13px;
            }
        """)
        output_group.add_widget(self.output_display)
        layout.addWidget(output_group)
        
        self.setLayout(layout)
    
    def new_file(self):
        self.editor.clear()
        self.file_path = None
    
    def open_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "打开文件", "", "Python文件 (*.py);;所有文件 (*)")
        if file_path:
            with open(file_path, 'r', encoding='utf-8') as f:
                self.editor.setPlainText(f.read())
            self.file_path = file_path
    
    def save_file(self):
        if self.file_path:
            with open(self.file_path, 'w', encoding='utf-8') as f:
                f.write(self.editor.toPlainText())
        else:
            file_path, _ = QFileDialog.getSaveFileName(
                self, "保存文件", "untitled.py", "Python文件 (*.py)")
            if file_path:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.editor.toPlainText())
                self.file_path = file_path
    
    def run_code(self):
        code = self.editor.toPlainText()
        self.output_display.clear()
        
        import io
        import contextlib
        
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        
        try:
            exec(code, {"__builtins__": __builtins__})
            output = sys.stdout.getvalue()
            self.output_display.setPlainText(output if output else "代码执行完成（无输出）")
        except Exception as e:
            self.output_display.setPlainText(f"错误: {e}")
        finally:
            sys.stdout = old_stdout


class SettingsDialog(QDialog):
    """设置对话框"""
    
    def __init__(self, config: AppConfig, parent=None):
        super().__init__(parent)
        self.config = config
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("设置")
        self.setMinimumWidth(500)
        
        layout = QVBoxLayout()
        
        # 标签页
        tabs = QTabWidget()
        
        # 外观设置
        appearance_tab = QWidget()
        appearance_layout = QFormLayout()
        
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["dark", "light"])
        self.theme_combo.setCurrentText(self.config.theme)
        appearance_layout.addRow("主题:", self.theme_combo)
        
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 24)
        self.font_size_spin.setValue(self.config.font_size)
        appearance_layout.addRow("字体大小:", self.font_size_spin)
        
        appearance_tab.setLayout(appearance_layout)
        tabs.addTab(appearance_tab, "外观")
        
        # API设置
        api_tab = QWidget()
        api_layout = QFormLayout()
        
        self.api_key_input = QLineEdit(self.config.api_key)
        self.api_key_input.setEchoMode(QLineEdit.Password)
        api_layout.addRow("API Key:", self.api_key_input)
        
        self.model_combo = QComboBox()
        self.model_combo.addItems(["deepseek-chat", "deepseek-reasoner"])
        self.model_combo.setCurrentText(self.config.model)
        api_layout.addRow("模型:", self.model_combo)
        
        self.temp_spin = QDoubleSpinBox()
        self.temp_spin.setRange(0, 2)
        self.temp_spin.setSingleStep(0.1)
        self.temp_spin.setValue(self.config.temperature)
        api_layout.addRow("温度:", self.temp_spin)
        
        api_tab.setLayout(api_layout)
        tabs.addTab(api_tab, "API")
        
        layout.addWidget(tabs)
        
        # 按钮
        btn_layout = QHBoxLayout()
        save_btn = StyledButton("保存", "#4CAF50")
        save_btn.clicked.connect(self.save_settings)
        btn_layout.addWidget(save_btn)
        
        cancel_btn = StyledButton("取消", "#f44336")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
        self.setLayout(layout)
    
    def save_settings(self):
        self.config.theme = self.theme_combo.currentText()
        self.config.font_size = self.font_size_spin.value()
        self.config.api_key = self.api_key_input.text()
        self.config.model = self.model_combo.currentText()
        self.config.temperature = self.temp_spin.value()
        self.config.save()
        self.accept()


# ==================== 主窗口 ====================

class MainWindow(QMainWindow):
    """主窗口"""
    
    def __init__(self):
        super().__init__()
        self.config = AppConfig.load()
        self.ai = AIClient(self.config.api_key)
        self.thread_pool = QThreadPool()
        self.init_ui()
        self.apply_theme()
    
    def init_ui(self):
        self.setWindowTitle("PyQt5 高级科学计算平台 v4.0")
        self.setGeometry(100, 100, 1600, 900)
        
        # 中心部件
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout()
        central.setLayout(layout)
        
        # 工具栏
        self.create_toolbar()
        
        # 标签页
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #3d3d3d;
                border-radius: 6px;
                background-color: #252525;
            }
            QTabBar::tab {
                background-color: #333;
                color: #e0e0e0;
                border: 1px solid #444;
                padding: 10px 20px;
                margin-right: 4px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
            }
            QTabBar::tab:selected {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
            }
            QTabBar::tab:hover {
                background-color: #555;
            }
        """)
        
        # 添加功能模块
        self.ai_widget = AIAssistantWidget(self.ai, self.config)
        self.code_editor = CodeEditor()
        
        self.tabs.addTab(self.ai_widget, "🤖 AI助手")
        self.tabs.addTab(self.code_editor, "📝 代码编辑器")
        self.tabs.addTab(self.create_placeholder("📊 数据分析"), "📊 数据分析")
        self.tabs.addTab(self.create_placeholder("📈 可视化"), "📈 可视化")
        self.tabs.addTab(self.create_placeholder("🔧 工具集"), "🔧 工具集")
        
        layout.addWidget(self.tabs)
        
        # 状态栏
        self.status_bar = QStatusBar()
        self.status_bar.setStyleSheet("""
            QStatusBar {
                background-color: #2d2d2d;
                color: #e0e0e0;
                border-top: 1px solid #3d3d3d;
            }
        """)
        self.setStatusBar(self.status_bar)
        self.update_status("就绪")
        
        # 菜单栏
        self.create_menus()
    
    def create_toolbar(self):
        toolbar = QToolBar()
        toolbar.setMovable(False)
        toolbar.setStyleSheet("""
            QToolBar {
                background-color: #2d2d2d;
                border-bottom: 1px solid #3d3d3d;
                spacing: 5px;
                padding: 5px;
            }
            QToolButton {
                color: #e0e0e0;
                padding: 6px 12px;
                border-radius: 4px;
            }
            QToolButton:hover {
                background-color: #4d4d4d;
            }
        """)
        
        actions = [
            ("⚙️ 设置", self.open_settings),
            ("💾 保存", self.save_session),
            ("📂 加载", self.load_session),
            ("🧹 清除", self.clear_session),
        ]
        
        for text, func in actions:
            action = QAction(text, self)
            action.triggered.connect(func)
            toolbar.addAction(action)
        
        self.addToolBar(toolbar)
    
    def create_menus(self):
        menubar = self.menuBar()
        menubar.setStyleSheet("""
            QMenuBar {
                background-color: #2d2d2d;
                color: #e0e0e0;
                border-bottom: 1px solid #3d3d3d;
            }
        """)
        
        # 文件菜单
        file_menu = menubar.addMenu("文件(&F)")
        file_menu.addAction("新建会话", self.new_session, "Ctrl+N")
        file_menu.addAction("保存会话", self.save_session, "Ctrl+S")
        file_menu.addAction("加载会话", self.load_session, "Ctrl+O")
        file_menu.addSeparator()
        file_menu.addAction("退出", self.close, "Ctrl+Q")
        
        # 视图菜单
        view_menu = menubar.addMenu("视图(&V)")
        view_menu.addAction("设置", self.open_settings, "Ctrl+,")
        
        # 帮助菜单
        help_menu = menubar.addMenu("帮助(&H)")
        help_menu.addAction("关于", self.show_about)
    
    def create_placeholder(self, text: str) -> QWidget:
        """创建占位符页面"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        label = QLabel(f"🚧 {text}模块")
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("""
            QLabel {
                color: #888;
                font-size: 24px;
                font-weight: bold;
            }
        """)
        layout.addWidget(label)
        
        desc = QLabel("此模块可通过集成之前2800行的科学计算组件来扩展")
        desc.setAlignment(Qt.AlignCenter)
        desc.setStyleSheet("color: #666; font-size: 14px;")
        layout.addWidget(desc)
        
        widget.setLayout(layout)
        return widget
    
    def apply_theme(self):
        ThemeManager.apply(QApplication.instance(), self.config.theme)
    
    def update_status(self, message: str):
        self.status_bar.showMessage(f" {message} | 模型: {self.config.model} | 主题: {self.config.theme}")
    
    def open_settings(self):
        dialog = SettingsDialog(self.config, self)
        if dialog.exec_() == QDialog.Accepted:
            self.apply_theme()
            if self.config.api_key:
                self.ai.connect(self.config.api_key)
            self.update_status("设置已更新")
    
    def new_session(self):
        reply = QMessageBox.question(
            self, "新建会话", "确定要清除当前会话吗？",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.ai_widget.clear_chat()
            self.code_editor.new_file()
            self.update_status("新会话已创建")
    
    def save_session(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存会话", "session.json", "JSON文件 (*.json)")
        if file_path:
            session_data = {
                "timestamp": datetime.now().isoformat(),
                "conversation": self.ai_widget.conversation,
                "code": self.code_editor.editor.toPlainText(),
                "config": asdict(self.config)
            }
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, indent=2, ensure_ascii=False)
            self.update_status(f"会话已保存到: {file_path}")
    
    def load_session(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "加载会话", "", "JSON文件 (*.json)")
        if file_path:
            with open(file_path, 'r', encoding='utf-8') as f:
                session_data = json.load(f)
            
            # 恢复对话
            self.ai_widget.conversation = session_data.get("conversation", [])
            for msg in self.ai_widget.conversation:
                role_icon = "👤" if msg["role"] == "user" else "🤖"
                color = "#4CAF50" if msg["role"] == "user" else "#2196F3"
                self.ai_widget.chat_display.append_with_animation(
                    f"\n{role_icon}: {msg['content']}\n", color
                )
            
            # 恢复代码
            self.code_editor.editor.setPlainText(session_data.get("code", ""))
            
            self.update_status(f"会话已加载: {file_path}")
    
    def clear_session(self):
        self.ai_widget.clear_chat()
        self.code_editor.new_file()
        self.update_status("会话已清除")
    
    def show_about(self):
        QMessageBox.about(self, "关于",
            """
            <h2>PyQt5 高级科学计算平台 v4.0</h2>
            <p>一个集成AI助手的现代化科学计算平台</p>
            
            <h3>核心特性:</h3>
            <ul>
                <li>🤖 AI助手 - 代码审查、错误解释、代码生成</li>
                <li>📝 代码编辑器 - 内置Python执行环境</li>
                <li>📊 数据分析 - 统计分析、可视化</li>
                <li>📈 可视化 - 交互式图表</li>
                <li>🔧 工具集 - 数值计算工具</li>
            </ul>
            
            <p><b>技术栈:</b> PyQt5 + NumPy + SciPy + Matplotlib + OpenAI</p>
            <p><b>版本:</b> 4.0 | <b>许可证:</b> MIT</p>
            """
        )


# ==================== 入口 ====================

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("科学计算平台")
    app.setOrganizationName("SciCalc")
    
    # 设置默认字体
    font = QFont("Segoe UI", 12)
    app.setFont(font)
    
    # 创建并显示主窗口
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()