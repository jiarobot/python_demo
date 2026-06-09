import sys
import os
import json
import ast
import re
import time
import subprocess
import webbrowser
from collections import defaultdict, OrderedDict
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QSplitter, QTreeWidget, QTreeWidgetItem, QTextEdit, QListWidget,
                             QTabWidget, QToolBar, QStatusBar, QAction, QFileDialog, QMessageBox,
                             QLabel, QLineEdit, QPushButton, QComboBox, QProgressBar, QStyleFactory,
                             QDockWidget, QToolBox, QGroupBox, QFormLayout, QCheckBox, QSpinBox,
                             QInputDialog, QMenu, QMenuBar, QDialog, QDialogButtonBox, QPlainTextEdit,
                             QListWidgetItem, QToolButton, QStackedWidget, QSizePolicy, QHeaderView,
                             QTableWidget, QTableWidgetItem, QAbstractItemView)
from PyQt5.QtCore import Qt, QSize, QThread, pyqtSignal, QSettings, QTimer, QRegExp, QModelIndex
from PyQt5.QtGui import (QIcon, QFont, QSyntaxHighlighter, QTextCharFormat, QColor, QPalette,
                         QKeySequence, QTextCursor, QRegExpValidator, QPixmap, QStandardItemModel,
                         QStandardItem)
import pygments
from pygments.lexers import get_lexer_by_name, guess_lexer, ClassNotFound
from pygments.formatters import HtmlFormatter
import markdown
from bs4 import BeautifulSoup


# 插件系统基类
class PluginBase:
    """插件基类"""
    def __init__(self, main_window):
        self.main_window = main_window
        self.name = "Base Plugin"
        self.version = "1.0"
        
    def initialize(self):
        """初始化插件"""
        pass
        
    def shutdown(self):
        """关闭插件"""
        pass


# 代码分析器线程
class CodeAnalyzer(QThread):
    """代码分析线程"""
    analysis_complete = pyqtSignal(dict)
    progress_update = pyqtSignal(int, str)
    
    def __init__(self, file_path, analysis_types=None):
        super().__init__()
        self.file_path = file_path
        self.analysis_types = analysis_types or ["imports", "classes", "functions", "complexity"]
        
    def run(self):
        """分析代码文件"""
        result = {
            "imports": [],
            "classes": [],
            "functions": [],
            "variables": [],
            "lines": 0,
            "complexity": 0,
            "issues": []
        }
        
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                result["lines"] = len(content.split('\n'))
                
                self.progress_update.emit(20, "正在分析代码结构...")
                
                # 尝试解析Python代码
                if self.file_path.endswith('.py'):
                    try:
                        tree = ast.parse(content)
                        
                        # 提取导入
                        if "imports" in self.analysis_types:
                            for node in ast.walk(tree):
                                if isinstance(node, ast.Import):
                                    for alias in node.names:
                                        result["imports"].append({
                                            "name": alias.name,
                                            "alias": alias.asname,
                                            "line": node.lineno
                                        })
                                elif isinstance(node, ast.ImportFrom):
                                    module = node.module if node.module else ""
                                    for alias in node.names:
                                        result["imports"].append({
                                            "name": f"{module}.{alias.name}",
                                            "alias": alias.asname,
                                            "line": node.lineno
                                        })
                        
                        # 提取类定义
                        if "classes" in self.analysis_types:
                            for node in ast.walk(tree):
                                if isinstance(node, ast.ClassDef):
                                    result["classes"].append({
                                        "name": node.name,
                                        "line": node.lineno,
                                        "methods": []
                                    })
                            
                        # 提取函数定义
                        if "functions" in self.analysis_types:
                            for node in ast.walk(tree):
                                if isinstance(node, ast.FunctionDef):
                                    # 计算函数复杂度
                                    complexity = self.calculate_complexity(node)
                                    
                                    result["functions"].append({
                                        "name": node.name,
                                        "line": node.lineno,
                                        "complexity": complexity
                                    })
                                    
                                    # 添加到对应的类中
                                    parent = node
                                    while hasattr(parent, 'parent'):
                                        parent = parent.parent
                                        if isinstance(parent, ast.ClassDef):
                                            for cls in result["classes"]:
                                                if cls["name"] == parent.name:
                                                    cls["methods"].append(node.name)
                                                    break
                                            break
                        
                        # 计算整体复杂度
                        if "complexity" in self.analysis_types:
                            result["complexity"] = self.calculate_file_complexity(tree)
                            
                        # 查找常见问题
                        if "issues" in self.analysis_types:
                            result["issues"] = self.find_issues(tree, content)
                            
                    except SyntaxError as e:
                        result["issues"].append({
                            "type": "syntax",
                            "message": f"语法错误: {e.msg}",
                            "line": e.lineno,
                            "severity": "high"
                        })
                        
                # 其他文件类型的分析可以在这里添加
                
        except Exception as e:
            result["issues"].append({
                "type": "io",
                "message": f"文件读取错误: {str(e)}",
                "line": 0,
                "severity": "high"
            })
            
        self.progress_update.emit(100, "分析完成")
        self.analysis_complete.emit(result)
        
    def calculate_complexity(self, node):
        """计算函数复杂度"""
        complexity = 1  # 起始复杂度为1
        
        # 遍历AST节点，增加复杂度
        for n in ast.walk(node):
            if isinstance(n, (ast.If, ast.While, ast.For, ast.ExceptHandler, 
                             ast.With, ast.AsyncWith, ast.AsyncFor)):
                complexity += 1
            elif isinstance(n, ast.BoolOp):
                complexity += len(n.values) - 1
                
        return complexity
        
    def calculate_file_complexity(self, tree):
        """计算文件整体复杂度"""
        total_complexity = 0
        function_count = 0
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                total_complexity += self.calculate_complexity(node)
                function_count += 1
                
        return total_complexity / function_count if function_count > 0 else 0
        
    def find_issues(self, tree, content):
        """查找代码中的问题"""
        issues = []
        lines = content.split('\n')
        
        # 检查过长的行
        for i, line in enumerate(lines, 1):
            if len(line) > 100:  # 超过100字符的行
                issues.append({
                    "type": "style",
                    "message": f"行过长 ({len(line)} 字符)",
                    "line": i,
                    "severity": "low"
                })
                
        # 检查TODO注释
        for i, line in enumerate(lines, 1):
            if re.search(r'#.*TODO', line, re.IGNORECASE):
                issues.append({
                    "type": "todo",
                    "message": "发现TODO注释",
                    "line": i,
                    "severity": "info"
                })
                
        # 检查未使用的导入 (简化版)
        # 实际实现需要更复杂的分析
        
        return issues


# 代码编辑器组件
class CodeEditor(QPlainTextEdit):
    """高级代码编辑器"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.setTabStopDistance(40)  # 设置制表符宽度
        
        # 行号区域
        self.line_number_area = LineNumberArea(self)
        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.cursorPositionChanged.connect(self.highlight_current_line)
        
        self.update_line_number_area_width(0)
        self.highlight_current_line()
        
        # 高亮器
        self.highlighter = None
        
    def set_highlighter(self, language):
        """设置语法高亮器"""
        if self.highlighter:
            self.highlighter.setDocument(None)
            
        self.highlighter = PythonHighlighter(self.document())
        
    def line_number_area_width(self):
        """计算行号区域宽度"""
        digits = len(str(max(1, self.blockCount())))
        space = 3 + self.fontMetrics().horizontalAdvance('9') * digits
        return space
        
    def update_line_number_area_width(self, new_block_count):
        """更新行号区域宽度"""
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)
        
    def update_line_number_area(self, rect, dy):
        """更新行号区域"""
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(0, rect.y(), 
                                        self.line_number_area.width(), rect.height())
            
        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width(0)
            
    def resizeEvent(self, event):
        """重写 resize 事件"""
        super().resizeEvent(event)
        
        cr = self.contentsRect()
        self.line_number_area.setGeometry(
            cr.left(), cr.top(), 
            self.line_number_area_width(), cr.height()
        )
        
    def highlight_current_line(self):
        """高亮当前行"""
        extra_selections = []
        
        if not self.isReadOnly():
            selection = QTextEdit.ExtraSelection()
            line_color = QColor(Qt.yellow).lighter(160)
            selection.format.setBackground(line_color)
            selection.format.setProperty(QTextCharFormat.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extra_selections.append(selection)
            
        self.setExtraSelections(extra_selections)
        
    def line_number_area_paint_event(self, event):
        """绘制行号区域"""
        painter = QPainter(self.line_number_area)
        painter.fillRect(event.rect(), Qt.lightGray)
        
        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        bottom = top + self.blockBoundingRect(block).height()
        
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                painter.setPen(Qt.black)
                painter.drawText(
                    0, top, 
                    self.line_number_area.width(), 
                    self.fontMetrics().height(),
                    Qt.AlignRight, number
                )
                
            block = block.next()
            top = bottom
            bottom = top + self.blockBoundingRect(block).height()
            block_number += 1


class LineNumberArea(QWidget):
    """行号区域组件"""
    def __init__(self, editor):
        super().__init__(editor)
        self.code_editor = editor
        
    def sizeHint(self):
        return QSize(self.code_editor.line_number_area_width(), 0)
        
    def paintEvent(self, event):
        self.code_editor.line_number_area_paint_event(event)


# 高级语法高亮器
class PythonHighlighter(QSyntaxHighlighter):
    """Python语法高亮器"""
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.highlighting_rules = []
        
        # 关键字格式
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor(200, 120, 50))
        keyword_format.setFontWeight(QFont.Bold)
        
        keywords = [
            'and', 'as', 'assert', 'break', 'class', 'continue', 'def', 'del',
            'elif', 'else', 'except', 'False', 'finally', 'for', 'from', 'global',
            'if', 'import', 'in', 'is', 'lambda', 'None', 'nonlocal', 'not', 'or',
            'pass', 'raise', 'return', 'True', 'try', 'while', 'with', 'yield',
            'async', 'await'
        ]
        
        for word in keywords:
            pattern = QRegExp(r'\b' + word + r'\b')
            rule = (pattern, keyword_format)
            self.highlighting_rules.append(rule)
            
        # 类名格式
        class_format = QTextCharFormat()
        class_format.setForeground(QColor(40, 120, 200))
        class_format.setFontWeight(QFont.Bold)
        pattern = QRegExp(r'\b[A-Z][a-zA-Z0-9_]*\b')
        rule = (pattern, class_format)
        self.highlighting_rules.append(rule)
        
        # 函数名格式
        function_format = QTextCharFormat()
        function_format.setForeground(QColor(50, 150, 150))
        pattern = QRegExp(r'\b[a-zA-Z0-9_]+(?=\()')
        rule = (pattern, function_format)
        self.highlighting_rules.append(rule)
        
        # 字符串格式
        string_format = QTextCharFormat()
        string_format.setForeground(QColor(50, 150, 100))
        pattern = QRegExp(r'\"[^\"]*\"')
        rule = (pattern, string_format)
        self.highlighting_rules.append(rule)
        pattern = QRegExp(r"'[^']*'")
        rule = (pattern, string_format)
        self.highlighting_rules.append(rule)
        
        # 注释格式
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor(150, 150, 150))
        comment_format.setFontItalic(True)
        pattern = QRegExp(r'#.*')
        rule = (pattern, comment_format)
        self.highlighting_rules.append(rule)
        
        # 数字格式
        number_format = QTextCharFormat()
        number_format.setForeground(QColor(180, 100, 180))
        pattern = QRegExp(r'\b\d+\b')
        rule = (pattern, number_format)
        self.highlighting_rules.append(rule)
        
    def highlightBlock(self, text):
        """高亮文本块"""
        for pattern, format in self.highlighting_rules:
            expression = QRegExp(pattern)
            index = expression.indexIn(text)
            while index >= 0:
                length = expression.matchedLength()
                self.setFormat(index, length, format)
                index = expression.indexIn(text, index + length)
                
        self.setCurrentBlockState(0)


# 插件管理器
class PluginManager:
    """插件管理器"""
    def __init__(self, main_window):
        self.main_window = main_window
        self.plugins = {}
        self.plugin_dir = "plugins"
        
    def load_plugins(self):
        """加载所有插件"""
        if not os.path.exists(self.plugin_dir):
            os.makedirs(self.plugin_dir)
            return
            
        # 加载插件目录中的Python文件
        for filename in os.listdir(self.plugin_dir):
            if filename.endswith('.py') and filename != '__init__.py':
                plugin_name = filename[:-3]  # 移除.py扩展名
                self.load_plugin(plugin_name)
                
    def load_plugin(self, plugin_name):
        """加载单个插件"""
        try:
            # 动态导入插件模块
            spec = importlib.util.spec_from_file_location(
                plugin_name, 
                os.path.join(self.plugin_dir, f"{plugin_name}.py")
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # 查找插件类
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and 
                    issubclass(attr, PluginBase) and 
                    attr != PluginBase):
                    plugin_instance = attr(self.main_window)
                    plugin_instance.initialize()
                    self.plugins[plugin_name] = plugin_instance
                    self.main_window.status_bar.showMessage(f"已加载插件: {plugin_name}")
                    break
                    
        except Exception as e:
            self.main_window.status_bar.showMessage(f"加载插件 {plugin_name} 失败: {str(e)}")
            
    def unload_plugin(self, plugin_name):
        """卸载插件"""
        if plugin_name in self.plugins:
            self.plugins[plugin_name].shutdown()
            del self.plugins[plugin_name]
            self.main_window.status_bar.showMessage(f"已卸载插件: {plugin_name}")
            
    def get_plugin(self, plugin_name):
        """获取插件实例"""
        return self.plugins.get(plugin_name)


# 代码库主窗口
class CodeLibrary(QMainWindow):
    """代码库主窗口"""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("高级代码分类系统")
        self.setGeometry(100, 100, 1400, 900)
        
        # 存储代码文件信息
        self.code_files = OrderedDict()
        self.categories = defaultdict(list)
        self.tags = defaultdict(list)
        
        # 当前项目路径
        self.project_path = None
        
        # 插件管理器
        self.plugin_manager = PluginManager(self)
        
        # 设置和状态
        self.settings = QSettings("CodeLibrary", "AdvancedCodeManager")
        self.dark_theme = self.settings.value("dark_theme", True, type=bool)
        
        # 初始化UI
        self.init_ui()
        
        # 加载插件
        self.plugin_manager.load_plugins()
        
        # 应用主题
        if self.dark_theme:
            self.apply_dark_theme()
        else:
            self.apply_light_theme()
            
        # 恢复窗口状态
        self.restore_state()
        
    def init_ui(self):
        """初始化用户界面"""
        # 创建中央部件和主布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # 创建主分割器
        main_splitter = QSplitter(Qt.Horizontal)
        
        # 左侧面板 - 文件树和分类
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # 项目信息
        project_group = QGroupBox("项目")
        project_layout = QVBoxLayout(project_group)
        
        self.project_label = QLabel("无项目")
        self.project_label.setWordWrap(True)
        project_layout.addWidget(self.project_label)
        
        project_btn_layout = QHBoxLayout()
        open_btn = QPushButton("打开项目")
        open_btn.clicked.connect(self.open_project)
        project_btn_layout.addWidget(open_btn)
        
        new_btn = QPushButton("新建项目")
        new_btn.clicked.connect(self.new_project)
        project_btn_layout.addWidget(new_btn)
        
        project_layout.addLayout(project_btn_layout)
        left_layout.addWidget(project_group)
        
        # 搜索框
        search_group = QGroupBox("搜索")
        search_layout = QVBoxLayout(search_group)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索代码...")
        self.search_input.textChanged.connect(self.search_code)
        search_layout.addWidget(self.search_input)
        
        # 搜索选项
        search_options = QHBoxLayout()
        self.search_content = QCheckBox("内容")
        self.search_content.setChecked(True)
        search_options.addWidget(self.search_content)
        
        self.search_filename = QCheckBox("文件名")
        self.search_filename.setChecked(True)
        search_options.addWidget(self.search_filename)
        
        self.search_tags = QCheckBox("标签")
        search_options.addWidget(self.search_tags)
        
        search_layout.addLayout(search_options)
        
        # 分类过滤器
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("分类:"))
        
        self.category_filter = QComboBox()
        self.category_filter.addItem("所有分类")
        self.category_filter.currentTextChanged.connect(self.filter_by_category)
        filter_layout.addWidget(self.category_filter)
        
        search_layout.addLayout(filter_layout)
        
        # 标签过滤器
        tag_layout = QHBoxLayout()
        tag_layout.addWidget(QLabel("标签:"))
        
        self.tag_filter = QComboBox()
        self.tag_filter.addItem("所有标签")
        self.tag_filter.currentTextChanged.connect(self.filter_by_tag)
        tag_layout.addWidget(self.tag_filter)
        
        search_layout.addLayout(tag_layout)
        
        left_layout.addWidget(search_group)
        
        # 文件树
        file_group = QGroupBox("文件")
        file_layout = QVBoxLayout(file_group)
        
        self.file_tree = QTreeWidget()
        self.file_tree.setHeaderLabels(["名称", "类型", "大小"])
        self.file_tree.setColumnWidth(0, 200)
        self.file_tree.itemClicked.connect(self.on_file_selected)
        self.file_tree.itemDoubleClicked.connect(self.on_file_double_clicked)
        file_layout.addWidget(self.file_tree)
        
        left_layout.addWidget(file_group)
        
        # 添加到主分割器
        main_splitter.addWidget(left_panel)
        main_splitter.setStretchFactor(0, 1)
        
        # 中央面板 - 代码查看和编辑
        central_panel = QWidget()
        central_layout = QVBoxLayout(central_panel)
        
        # 标签页
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        
        central_layout.addWidget(self.tabs)
        
        # 添加到主分割器
        main_splitter.addWidget(central_panel)
        main_splitter.setStretchFactor(1, 3)
        
        # 右侧面板 - 信息和工具
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # 信息面板
        info_group = QGroupBox("文件信息")
        info_layout = QVBoxLayout(info_group)
        
        self.info_text = QTextEdit()
        self.info_text.setReadOnly(True)
        info_layout.addWidget(self.info_text)
        
        right_layout.addWidget(info_group)
        
        # 分析面板
        analysis_group = QGroupBox("代码分析")
        analysis_layout = QVBoxLayout(analysis_group)
        
        self.analysis_text = QTextEdit()
        self.analysis_text.setReadOnly(True)
        analysis_layout.addWidget(self.analysis_text)
        
        analyze_btn = QPushButton("分析当前文件")
        analyze_btn.clicked.connect(self.analyze_current_file)
        analysis_layout.addWidget(analyze_btn)
        
        right_layout.addWidget(analysis_group)
        
        # 标签面板
        tags_group = QGroupBox("标签管理")
        tags_layout = QVBoxLayout(tags_group)
        
        self.tags_list = QListWidget()
        self.tags_list.itemClicked.connect(self.on_tag_selected)
        tags_layout.addWidget(self.tags_list)
        
        tag_btn_layout = QHBoxLayout()
        add_tag_btn = QPushButton("添加标签")
        add_tag_btn.clicked.connect(self.add_tag_to_file)
        tag_btn_layout.addWidget(add_tag_btn)
        
        remove_tag_btn = QPushButton("移除标签")
        remove_tag_btn.clicked.connect(self.remove_tag_from_file)
        tag_btn_layout.addWidget(remove_tag_btn)
        
        tags_layout.addLayout(tag_btn_layout)
        
        right_layout.addWidget(tags_group)
        
        # 添加到主分割器
        main_splitter.addWidget(right_panel)
        main_splitter.setStretchFactor(2, 1)
        
        # 添加到主布局
        main_layout.addWidget(main_splitter)
        
        # 创建菜单栏
        self.create_menu_bar()
        
        # 创建工具栏
        self.create_toolbar()
        
        # 创建状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪")
        
        # 创建进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(200)
        self.progress_bar.setVisible(False)
        self.status_bar.addPermanentWidget(self.progress_bar)
        
        # 创建底部信息栏
        self.info_label = QLabel()
        self.status_bar.addPermanentWidget(self.info_label)
        
        # 初始化文件树上下文菜单
        self.file_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.file_tree.customContextMenuRequested.connect(self.show_file_tree_context_menu)
        
    def create_menu_bar(self):
        """创建菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu("文件")
        
        new_project_action = QAction("新建项目", self)
        new_project_action.triggered.connect(self.new_project)
        file_menu.addAction(new_project_action)
        
        open_project_action = QAction("打开项目", self)
        open_project_action.triggered.connect(self.open_project)
        file_menu.addAction(open_project_action)
        
        file_menu.addSeparator()
        
        save_action = QAction("保存", self)
        save_action.setShortcut(QKeySequence.Save)
        save_action.triggered.connect(self.save_current_file)
        file_menu.addAction(save_action)
        
        save_all_action = QAction("全部保存", self)
        save_all_action.setShortcut(QKeySequence("Ctrl+Shift+S"))
        save_all_action.triggered.connect(self.save_all_files)
        file_menu.addAction(save_all_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("退出", self)
        exit_action.setShortcut(QKeySequence.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 编辑菜单
        edit_menu = menubar.addMenu("编辑")
        
        undo_action = QAction("撤销", self)
        undo_action.setShortcut(QKeySequence.Undo)
        undo_action.triggered.connect(self.undo)
        edit_menu.addAction(undo_action)
        
        redo_action = QAction("重做", self)
        redo_action.setShortcut(QKeySequence.Redo)
        redo_action.triggered.connect(self.redo)
        edit_menu.addAction(redo_action)
        
        edit_menu.addSeparator()
        
        cut_action = QAction("剪切", self)
        cut_action.setShortcut(QKeySequence.Cut)
        cut_action.triggered.connect(self.cut)
        edit_menu.addAction(cut_action)
        
        copy_action = QAction("复制", self)
        copy_action.setShortcut(QKeySequence.Copy)
        copy_action.triggered.connect(self.copy)
        edit_menu.addAction(copy_action)
        
        paste_action = QAction("粘贴", self)
        paste_action.setShortcut(QKeySequence.Paste)
        paste_action.triggered.connect(self.paste)
        edit_menu.addAction(paste_action)
        
        # 查看菜单
        view_menu = menubar.addMenu("查看")
        
        theme_action = QAction("切换主题", self)
        theme_action.triggered.connect(self.toggle_theme)
        view_menu.addAction(theme_action)
        
        # 工具菜单
        tools_menu = menubar.addMenu("工具")
        
        analyze_action = QAction("分析代码", self)
        analyze_action.triggered.connect(self.analyze_current_file)
        tools_menu.addAction(analyze_action)
        
        # 插件菜单
        self.plugin_menu = menubar.addMenu("插件")
        
        manage_plugins_action = QAction("管理插件", self)
        manage_plugins_action.triggered.connect(self.manage_plugins)
        self.plugin_menu.addAction(manage_plugins_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu("帮助")
        
        about_action = QAction("关于", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
    def create_toolbar(self):
        """创建工具栏"""
        toolbar = QToolBar("主工具栏")
        toolbar.setIconSize(QSize(16, 16))
        self.addToolBar(toolbar)
        
        # 添加动作
        open_action = QAction(QIcon.fromTheme("document-open"), "打开项目", self)
        open_action.triggered.connect(self.open_project)
        toolbar.addAction(open_action)
        
        save_action = QAction(QIcon.fromTheme("document-save"), "保存", self)
        save_action.triggered.connect(self.save_current_file)
        toolbar.addAction(save_action)
        
        toolbar.addSeparator()
        
        analyze_action = QAction(QIcon.fromTheme("tools-check-spelling"), "分析代码", self)
        analyze_action.triggered.connect(self.analyze_current_file)
        toolbar.addAction(analyze_action)
        
        toolbar.addSeparator()
        
        undo_action = QAction(QIcon.fromTheme("edit-undo"), "撤销", self)
        undo_action.triggered.connect(self.undo)
        toolbar.addAction(undo_action)
        
        redo_action = QAction(QIcon.fromTheme("edit-redo"), "重做", self)
        redo_action.triggered.connect(self.redo)
        toolbar.addAction(redo_action)
        
        toolbar.addSeparator()
        
        theme_action = QAction(QIcon.fromTheme("preferences-desktop-theme"), "切换主题", self)
        theme_action.triggered.connect(self.toggle_theme)
        toolbar.addAction(theme_action)
        
    def apply_dark_theme(self):
        """应用暗色主题"""
        dark_palette = QPalette()
        dark_palette.setColor(QPalette.Window, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.WindowText, Qt.white)
        dark_palette.setColor(QPalette.Base, QColor(25, 25, 25))
        dark_palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ToolTipBase, Qt.white)
        dark_palette.setColor(QPalette.ToolTipText, Qt.white)
        dark_palette.setColor(QPalette.Text, Qt.white)
        dark_palette.setColor(QPalette.Button, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ButtonText, Qt.white)
        dark_palette.setColor(QPalette.BrightText, Qt.red)
        dark_palette.setColor(QPalette.Link, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.HighlightedText, Qt.black)
        
        self.setPalette(dark_palette)
        self.dark_theme = True
        self.settings.setValue("dark_theme", True)
        
        # 更新代码编辑器样式
        for i in range(self.tabs.count()):
            editor = self.tabs.widget(i)
            if hasattr(editor, 'setStyleSheet'):
                editor.setStyleSheet("""
                    QPlainTextEdit {
                        background-color: #1e1e1e;
                        color: #d4d4d4;
                        selection-background-color: #264f78;
                    }
                """)
        
    def apply_light_theme(self):
        """应用亮色主题"""
        self.setPalette(QApplication.style().standardPalette())
        self.dark_theme = False
        self.settings.setValue("dark_theme", False)
        
        # 更新代码编辑器样式
        for i in range(self.tabs.count()):
            editor = self.tabs.widget(i)
            if hasattr(editor, 'setStyleSheet'):
                editor.setStyleSheet("")
        
    def toggle_theme(self):
        """切换主题"""
        if self.dark_theme:
            self.apply_light_theme()
        else:
            self.apply_dark_theme()
            
    def restore_state(self):
        """恢复窗口状态"""
        # 恢复窗口几何状态
        geometry = self.settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
            
        # 恢复窗口状态
        state = self.settings.value("windowState")
        if state:
            self.restoreState(state)
            
    def closeEvent(self, event):
        """关闭事件"""
        # 保存窗口状态
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("windowState", self.saveState())
        
        # 关闭所有插件
        for plugin_name in list(self.plugin_manager.plugins.keys()):
            self.plugin_manager.unload_plugin(plugin_name)
            
        # 保存所有文件
        self.save_all_files()
        
        event.accept()
        
    def new_project(self):
        """新建项目"""
        project_path = QFileDialog.getExistingDirectory(self, "选择项目文件夹")
        if project_path:
            # 创建项目文件
            project_file = os.path.join(project_path, ".codelibrary")
            with open(project_file, 'w') as f:
                json.dump({
                    "name": os.path.basename(project_path),
                    "created": datetime.now().isoformat(),
                    "files": [],
                    "categories": [],
                    "tags": []
                }, f, indent=2)
                
            self.load_project(project_path)
            
    def open_project(self):
        """打开项目"""
        project_path = QFileDialog.getExistingDirectory(self, "选择项目文件夹")
        if project_path:
            self.load_project(project_path)
            
    def load_project(self, project_path):
        """加载项目"""
        self.project_path = project_path
        self.project_label.setText(f"项目: {os.path.basename(project_path)}")
        
        # 加载项目文件
        project_file = os.path.join(project_path, ".codelibrary")
        if os.path.exists(project_file):
            try:
                with open(project_file, 'r') as f:
                    project_data = json.load(f)
                    
                # 加载文件列表
                self.code_files = OrderedDict()
                for file_info in project_data.get("files", []):
                    file_path = os.path.join(project_path, file_info["path"])
                    if os.path.exists(file_path):
                        self.code_files[file_path] = file_info
                        
                # 加载分类
                self.categories = defaultdict(list)
                for category in project_data.get("categories", []):
                    self.categories[category["name"]] = category["files"]
                    
                # 加载标签
                self.tags = defaultdict(list)
                for tag in project_data.get("tags", []):
                    self.tags[tag["name"]] = tag["files"]
                    
            except Exception as e:
                QMessageBox.warning(self, "错误", f"加载项目文件失败: {str(e)}")
        else:
            # 扫描项目文件夹
            self.scan_project_folder(project_path)
            
        # 更新UI
        self.update_file_tree()
        self.update_category_list()
        self.update_tag_list()
        
        self.status_bar.showMessage(f"已加载项目: {os.path.basename(project_path)}")
        
    def scan_project_folder(self, folder_path):
        """扫描项目文件夹"""
        self.file_tree.clear()
        self.code_files.clear()
        self.categories.clear()
        self.tags.clear()
        
        # 支持的文件扩展名
        code_extensions = [
            '.py', '.java', '.cpp', '.c', '.h', '.hpp', 
            '.js', '.html', '.css', '.php', '.rb', '.go',
            '.rs', '.ts', '.vue', '.json', '.xml', '.yml',
            '.yaml', '.md', '.txt'
        ]
        
        # 遍历文件夹
        for root, dirs, files in os.walk(folder_path):
            # 忽略隐藏文件夹和虚拟环境
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['venv', 'env', 'node_modules']]
            
            for file in files:
                if any(file.endswith(ext) for ext in code_extensions):
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, folder_path)
                    
                    # 添加到代码文件列表
                    self.code_files[file_path] = {
                        'path': rel_path,
                        'name': file,
                        'category': '未分类',
                        'tags': [],
                        'last_modified': os.path.getmtime(file_path)
                    }
                    
                    # 添加到未分类
                    self.categories['未分类'].append(file_path)
        
        # 保存项目文件
        self.save_project_file()
        
    def save_project_file(self):
        """保存项目文件"""
        if not self.project_path:
            return
            
        project_file = os.path.join(self.project_path, ".codelibrary")
        
        # 准备项目数据
        project_data = {
            "name": os.path.basename(self.project_path),
            "created": datetime.now().isoformat(),
            "files": [],
            "categories": [],
            "tags": []
        }
        
        # 添加文件信息
        for file_path, file_info in self.code_files.items():
            project_data["files"].append({
                "path": file_info["path"],
                "name": file_info["name"],
                "category": file_info["category"],
                "tags": file_info["tags"],
                "last_modified": file_info["last_modified"]
            })
            
        # 添加分类信息
        for category, files in self.categories.items():
            project_data["categories"].append({
                "name": category,
                "files": files
            })
            
        # 添加标签信息
        for tag, files in self.tags.items():
            project_data["tags"].append({
                "name": tag,
                "files": files
            })
            
        # 保存到文件
        with open(project_file, 'w') as f:
            json.dump(project_data, f, indent=2)
            
    def update_file_tree(self):
        """更新文件树"""
        self.file_tree.clear()
        
        # 按目录结构组织文件
        file_structure = {}
        
        for file_path, file_info in self.code_files.items():
            rel_path = file_info["path"]
            parts = rel_path.split(os.sep)
            
            current_level = file_structure
            for part in parts[:-1]:
                if part not in current_level:
                    current_level[part] = {}
                current_level = current_level[part]
                
            current_level[parts[-1]] = file_path
            
        # 递归添加项目到树中
        self.add_tree_items(file_structure, self.file_tree.invisibleRootItem())
        
        # 展开第一级
        for i in range(self.file_tree.topLevelItemCount()):
            self.file_tree.topLevelItem(i).setExpanded(True)
            
    def add_tree_items(self, structure, parent_item):
        """递归添加树项目"""
        for name, value in structure.items():
            if isinstance(value, dict):
                # 这是一个文件夹
                item = QTreeWidgetItem([name, "文件夹", ""])
                parent_item.addChild(item)
                self.add_tree_items(value, item)
            else:
                # 这是一个文件
                file_path = value
                file_info = self.code_files[file_path]
                size = os.path.getsize(file_path)
                
                item = QTreeWidgetItem([
                    name, 
                    "文件", 
                    self.format_file_size(size)
                ])
                item.setData(0, Qt.UserRole, file_path)
                parent_item.addChild(item)
                
    def format_file_size(self, size):
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
    
    def update_category_list(self):
        """更新分类列表"""
        self.category_filter.clear()
        self.category_filter.addItem("所有分类")
        
        for category in sorted(self.categories.keys()):
            count = len(self.categories[category])
            self.category_filter.addItem(f"{category} ({count})")
            
    def update_tag_list(self):
        """更新标签列表"""
        self.tag_filter.clear()
        self.tag_filter.addItem("所有标签")
        self.tags_list.clear()
        
        for tag in sorted(self.tags.keys()):
            count = len(self.tags[tag])
            self.tag_filter.addItem(f"{tag} ({count})")
            self.tags_list.addItem(f"{tag} ({count})")
            
    def on_file_selected(self, item, column):
        """当文件被选中时"""
        file_path = item.data(0, Qt.UserRole)
        if file_path:
            self.show_file_info(file_path)
            
    def on_file_double_clicked(self, item, column):
        """当文件被双击时"""
        file_path = item.data(0, Qt.UserRole)
        if file_path:
            self.open_file_in_tab(file_path)
            
    def show_file_info(self, file_path):
        """显示文件信息"""
        if file_path not in self.code_files:
            return
            
        file_info = self.code_files[file_path]
        file_stats = os.stat(file_path)
        
        info_text = f"""
        <b>文件信息:</b><br>
        名称: {file_info['name']}<br>
        路径: {file_info['path']}<br>
        大小: {self.format_file_size(file_stats.st_size)}<br>
        修改时间: {datetime.fromtimestamp(file_stats.st_mtime).strftime('%Y-%m-%d %H:%M:%S')}<br>
        分类: {file_info['category']}<br>
        标签: {', '.join(file_info['tags'])}<br>
        """
        
        self.info_text.setHtml(info_text)
        
    def open_file_in_tab(self, file_path):
        """在标签页中打开文件"""
        # 检查文件是否已经打开
        for i in range(self.tabs.count()):
            if self.tabs.tabToolTip(i) == file_path:
                self.tabs.setCurrentIndex(i)
                return
                
        # 创建新的代码编辑器
        editor = CodeEditor()
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                editor.setPlainText(content)
                
            # 根据文件扩展名设置高亮
            if file_path.endswith('.py'):
                editor.set_highlighter("python")
            # 可以添加其他语言的支持
            
            # 添加到标签页
            tab_index = self.tabs.addTab(editor, os.path.basename(file_path))
            self.tabs.setTabToolTip(tab_index, file_path)
            self.tabs.setCurrentIndex(tab_index)
            
            # 连接文本修改信号
            editor.modificationChanged.connect(lambda modified, editor=editor: 
                self.on_editor_modified(editor, modified))
                
        except Exception as e:
            QMessageBox.warning(self, "错误", f"无法读取文件: {str(e)}")
            
    def on_editor_modified(self, editor, modified):
        """当编辑器内容修改时"""
        tab_index = self.tabs.indexOf(editor)
        if tab_index >= 0:
            tab_text = self.tabs.tabText(tab_index)
            if modified and not tab_text.endswith('*'):
                self.tabs.setTabText(tab_index, tab_text + '*')
            elif not modified and tab_text.endswith('*'):
                self.tabs.setTabText(tab_index, tab_text[:-1])
                
    def close_tab(self, index):
        """关闭标签页"""
        editor = self.tabs.widget(index)
        if editor.document().isModified():
            reply = QMessageBox.question(
                self, "保存文件", 
                "文件已修改，是否保存？",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel
            )
            
            if reply == QMessageBox.Save:
                self.save_editor_content(editor)
            elif reply == QMessageBox.Cancel:
                return
                
        self.tabs.removeTab(index)
        
    def save_current_file(self):
        """保存当前文件"""
        current_editor = self.tabs.currentWidget()
        if current_editor:
            self.save_editor_content(current_editor)
            
    def save_all_files(self):
        """保存所有文件"""
        for i in range(self.tabs.count()):
            editor = self.tabs.widget(i)
            if editor.document().isModified():
                self.save_editor_content(editor)
                
    def save_editor_content(self, editor):
        """保存编辑器内容"""
        file_path = self.tabs.tabToolTip(self.tabs.indexOf(editor))
        if not file_path:
            return
            
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(editor.toPlainText())
                
            editor.document().setModified(False)
            self.status_bar.showMessage(f"已保存: {os.path.basename(file_path)}")
            
            # 更新文件信息
            if file_path in self.code_files:
                self.code_files[file_path]['last_modified'] = os.path.getmtime(file_path)
                
        except Exception as e:
            QMessageBox.warning(self, "错误", f"保存文件失败: {str(e)}")
            
    def analyze_current_file(self):
        """分析当前文件"""
        current_editor = self.tabs.currentWidget()
        if current_editor:
            file_path = self.tabs.tabToolTip(self.tabs.indexOf(current_editor))
            if file_path:
                self.status_bar.showMessage(f"正在分析: {os.path.basename(file_path)}")
                self.progress_bar.setVisible(True)
                
                self.analyzer = CodeAnalyzer(file_path)
                self.analyzer.progress_update.connect(self.on_analysis_progress)
                self.analyzer.analysis_complete.connect(self.on_analysis_complete)
                self.analyzer.start()
                
    def on_analysis_progress(self, progress, message):
        """分析进度更新"""
        self.progress_bar.setValue(progress)
        self.status_bar.showMessage(message)
        
    def on_analysis_complete(self, result):
        """当分析完成时"""
        self.progress_bar.setVisible(False)
        self.status_bar.showMessage("分析完成")
        
        # 显示分析结果
        analysis_text = f"<h3>文件分析结果:</h3>"
        analysis_text += f"<p><b>行数:</b> {result['lines']}</p>"
        
        analysis_text += f"<p><b>导入 ({len(result['imports'])}):</b></p><ul>"
        for imp in result['imports']:
            analysis_text += f"<li>行 {imp['line']}: {imp['name']}"
            if imp['alias']:
                analysis_text += f" as {imp['alias']}"
            analysis_text += "</li>"
        analysis_text += "</ul>"
        
        analysis_text += f"<p><b>类 ({len(result['classes'])}):</b></p><ul>"
        for cls in result['classes']:
            analysis_text += f"<li>行 {cls['line']}: {cls['name']}"
            if cls['methods']:
                analysis_text += f" ({len(cls['methods'])} 方法)"
            analysis_text += "</li>"
        analysis_text += "</ul>"
        
        analysis_text += f"<p><b>函数 ({len(result['functions'])}):</b></p><ul>"
        for func in result['functions']:
            analysis_text += f"<li>行 {func['line']}: {func['name']} (复杂度: {func['complexity']})</li>"
        analysis_text += "</ul>"
        
        if result['complexity'] > 0:
            analysis_text += f"<p><b>平均复杂度:</b> {result['complexity']:.2f}</p>"
            
        if result['issues']:
            analysis_text += f"<p><b>发现问题 ({len(result['issues'])}):</b></p><ul>"
            for issue in result['issues']:
                severity_color = {
                    'high': 'red',
                    'medium': 'orange',
                    'low': 'yellow',
                    'info': 'blue'
                }.get(issue['severity'], 'black')
                
                analysis_text += f"<li style='color: {severity_color}'>行 {issue['line']}: {issue['message']}</li>"
            analysis_text += "</ul>"
            
        self.analysis_text.setHtml(analysis_text)
        
    def search_code(self):
        """搜索代码"""
        query = self.search_input.text().lower()
        if not query:
            self.update_file_tree()
            return
            
        # 确定搜索范围
        search_content = self.search_content.isChecked()
        search_filename = self.search_filename.isChecked()
        search_tags = self.search_tags.isChecked()
        
        results = []
        for file_path, file_info in self.code_files.items():
            matched = False
            
            # 搜索文件名
            if search_filename and query in file_info['name'].lower():
                matched = True
                
            # 搜索标签
            if not matched and search_tags:
                for tag in file_info['tags']:
                    if query in tag.lower():
                        matched = True
                        break
                        
            # 搜索内容
            if not matched and search_content:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read().lower()
                        if query in content:
                            matched = True
                except:
                    pass
                    
            if matched:
                results.append(file_path)
                
        # 显示搜索结果
        self.file_tree.clear()
        
        for file_path in results:
            file_info = self.code_files[file_path]
            rel_path = file_info['path']
            parts = rel_path.split(os.sep)
            
            parent = self.file_tree.invisibleRootItem()
            for part in parts[:-1]:
                found = False
                for i in range(parent.childCount()):
                    if parent.child(i).text(0) == part:
                        parent = parent.child(i)
                        found = True
                        break
                if not found:
                    new_item = QTreeWidgetItem([part, "文件夹", ""])
                    parent.addChild(new_item)
                    parent = new_item
            
            size = os.path.getsize(file_path)
            file_item = QTreeWidgetItem([
                parts[-1], 
                "文件", 
                self.format_file_size(size)
            ])
            file_item.setData(0, Qt.UserRole, file_path)
            parent.addChild(file_item)
            
        self.status_bar.showMessage(f"找到 {len(results)} 个匹配结果")
        
    def filter_by_category(self, category_text):
        """通过分类过滤器过滤"""
        if category_text == "所有分类":
            self.update_file_tree()
        else:
            category = category_text.split(' (')[0]
            self.filter_files_by_category(category)
            
    def filter_files_by_category(self, category):
        """按分类过滤文件"""
        self.file_tree.clear()
        
        if category not in self.categories:
            return
            
        for file_path in self.categories[category]:
            if file_path not in self.code_files:
                continue
                
            file_info = self.code_files[file_path]
            rel_path = file_info['path']
            parts = rel_path.split(os.sep)
            
            parent = self.file_tree.invisibleRootItem()
            for part in parts[:-1]:
                found = False
                for i in range(parent.childCount()):
                    if parent.child(i).text(0) == part:
                        parent = parent.child(i)
                        found = True
                        break
                if not found:
                    new_item = QTreeWidgetItem([part, "文件夹", ""])
                    parent.addChild(new_item)
                    parent = new_item
            
            size = os.path.getsize(file_path)
            file_item = QTreeWidgetItem([
                parts[-1], 
                "文件", 
                self.format_file_size(size)
            ])
            file_item.setData(0, Qt.UserRole, file_path)
            parent.addChild(file_item)
            
    def filter_by_tag(self, tag_text):
        """通过标签过滤器过滤"""
        if tag_text == "所有标签":
            self.update_file_tree()
        else:
            tag = tag_text.split(' (')[0]
            self.filter_files_by_tag(tag)
            
    def filter_files_by_tag(self, tag):
        """按标签过滤文件"""
        self.file_tree.clear()
        
        if tag not in self.tags:
            return
            
        for file_path in self.tags[tag]:
            if file_path not in self.code_files:
                continue
                
            file_info = self.code_files[file_path]
            rel_path = file_info['path']
            parts = rel_path.split(os.sep)
            
            parent = self.file_tree.invisibleRootItem()
            for part in parts[:-1]:
                found = False
                for i in range(parent.childCount()):
                    if parent.child(i).text(0) == part:
                        parent = parent.child(i)
                        found = True
                        break
                if not found:
                    new_item = QTreeWidgetItem([part, "文件夹", ""])
                    parent.addChild(new_item)
                    parent = new_item
            
            size = os.path.getsize(file_path)
            file_item = QTreeWidgetItem([
                parts[-1], 
                "文件", 
                self.format_file_size(size)
            ])
            file_item.setData(0, Qt.UserRole, file_path)
            parent.addChild(file_item)
            
    def on_tag_selected(self, item):
        """当标签被选中时"""
        tag_text = item.text()
        tag = tag_text.split(' (')[0]
        self.filter_files_by_tag(tag)
        
    def add_tag_to_file(self):
        """为当前文件添加标签"""
        current_item = self.file_tree.currentItem()
        if not current_item:
            return
            
        file_path = current_item.data(0, Qt.UserRole)
        if not file_path or file_path not in self.code_files:
            return
            
        tag, ok = QInputDialog.getText(self, "添加标签", "请输入标签名称:")
        if ok and tag:
            if tag not in self.code_files[file_path]['tags']:
                self.code_files[file_path]['tags'].append(tag)
                
            if file_path not in self.tags[tag]:
                self.tags[tag].append(file_path)
                
            self.update_tag_list()
            self.save_project_file()
            self.show_file_info(file_path)
            
    def remove_tag_from_file(self):
        """从当前文件移除标签"""
        current_item = self.file_tree.currentItem()
        if not current_item:
            return
            
        file_path = current_item.data(0, Qt.UserRole)
        if not file_path or file_path not in self.code_files:
            return
            
        current_tag_item = self.tags_list.currentItem()
        if not current_tag_item:
            return
            
        tag_text = current_tag_item.text()
        tag = tag_text.split(' (')[0]
        
        if tag in self.code_files[file_path]['tags']:
            self.code_files[file_path]['tags'].remove(tag)
            
        if file_path in self.tags[tag]:
            self.tags[tag].remove(file_path)
            
        # 如果标签没有文件了，删除标签
        if not self.tags[tag]:
            del self.tags[tag]
            
        self.update_tag_list()
        self.save_project_file()
        self.show_file_info(file_path)
        
    def show_file_tree_context_menu(self, position):
        """显示文件树上下文菜单"""
        item = self.file_tree.itemAt(position)
        if not item:
            return
            
        file_path = item.data(0, Qt.UserRole)
        if not file_path:
            return
            
        menu = QMenu()
        
        open_action = menu.addAction("打开")
        open_action.triggered.connect(lambda: self.open_file_in_tab(file_path))
        
        menu.addSeparator()
        
        analyze_action = menu.addAction("分析")
        analyze_action.triggered.connect(self.analyze_current_file)
        
        menu.addSeparator()
        
        category_menu = menu.addMenu("设置分类")
        
        # 添加现有分类
        for category in sorted(self.categories.keys()):
            category_action = category_menu.addAction(category)
            category_action.triggered.connect(
                lambda checked, c=category: self.set_file_category(file_path, c)
            )
            
        # 添加新分类选项
        category_menu.addSeparator()
        new_category_action = category_menu.addAction("新建分类...")
        new_category_action.triggered.connect(
            lambda: self.create_new_category_for_file(file_path)
        )
        
        menu.exec_(self.file_tree.viewport().mapToGlobal(position))
        
    def set_file_category(self, file_path, category):
        """设置文件分类"""
        if file_path not in self.code_files:
            return
            
        old_category = self.code_files[file_path]['category']
        
        # 从旧分类中移除
        if file_path in self.categories[old_category]:
            self.categories[old_category].remove(file_path)
            
        # 添加到新分类
        self.categories[category].append(file_path)
        self.code_files[file_path]['category'] = category
        
        self.update_category_list()
        self.save_project_file()
        self.show_file_info(file_path)
        
    def create_new_category_for_file(self, file_path):
        """为文件创建新分类"""
        category, ok = QInputDialog.getText(self, "新建分类", "请输入分类名称:")
        if ok and category:
            self.set_file_category(file_path, category)
            
    def manage_plugins(self):
        """管理插件"""
        dialog = QDialog(self)
        dialog.setWindowTitle("插件管理")
        dialog.setModal(True)
        dialog.resize(500, 400)
        
        layout = QVBoxLayout(dialog)
        
        # 插件列表
        plugin_list = QListWidget()
        for plugin_name, plugin in self.plugin_manager.plugins.items():
            item = QListWidgetItem(f"{plugin.name} (v{plugin.version})")
            item.setData(Qt.UserRole, plugin_name)
            plugin_list.addItem(item)
            
        layout.addWidget(plugin_list)
        
        # 按钮
        button_box = QDialogButtonBox()
        load_button = button_box.addButton("加载插件", QDialogButtonBox.ActionRole)
        unload_button = button_box.addButton("卸载插件", QDialogButtonBox.ActionRole)
        close_button = button_box.addButton("关闭", QDialogButtonBox.RejectRole)
        
        load_button.clicked.connect(self.load_new_plugin)
        unload_button.clicked.connect(lambda: self.unload_selected_plugin(plugin_list))
        close_button.clicked.connect(dialog.accept)
        
        layout.addWidget(button_box)
        
        dialog.exec_()
        
    def load_new_plugin(self):
        """加载新插件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择插件文件", 
            self.plugin_manager.plugin_dir, 
            "Python文件 (*.py)"
        )
        
        if file_path:
            plugin_name = os.path.basename(file_path)[:-3]  # 移除.py扩展名
            self.plugin_manager.load_plugin(plugin_name)
            
    def unload_selected_plugin(self, plugin_list):
        """卸载选中的插件"""
        current_item = plugin_list.currentItem()
        if not current_item:
            return
            
        plugin_name = current_item.data(Qt.UserRole)
        self.plugin_manager.unload_plugin(plugin_name)
        plugin_list.takeItem(plugin_list.row(current_item))
        
    def show_about(self):
        """显示关于对话框"""
        about_text = """
        <h2>高级代码分类系统</h2>
        <p>版本: 2.0</p>
        <p>一个功能强大的代码管理和分析工具</p>
        <p>特性:</p>
        <ul>
            <li>多语言代码高亮</li>
            <li>代码结构分析</li>
            <li>项目管理和分类</li>
            <li>标签系统</li>
            <li>高级搜索功能</li>
            <li>插件系统</li>
        </ul>
        <p>版权所有 © 2023 代码库团队</p>
        """
        
        QMessageBox.about(self, "关于", about_text)
        
    # 编辑功能
    def undo(self):
        """撤销"""
        current_editor = self.tabs.currentWidget()
        if current_editor:
            current_editor.undo()
            
    def redo(self):
        """重做"""
        current_editor = self.tabs.currentWidget()
        if current_editor:
            current_editor.redo()
            
    def cut(self):
        """剪切"""
        current_editor = self.tabs.currentWidget()
        if current_editor:
            current_editor.cut()
            
    def copy(self):
        """复制"""
        current_editor = self.tabs.currentWidget()
        if current_editor:
            current_editor.copy()
            
    def paste(self):
        """粘贴"""
        current_editor = self.tabs.currentWidget()
        if current_editor:
            current_editor.paste()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 设置应用程序样式
    app.setStyle(QStyleFactory.create("Fusion"))
    
    window = CodeLibrary()
    window.show()
    
    sys.exit(app.exec_())