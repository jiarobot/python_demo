import sys
import os
import json
import subprocess
import shutil
import tempfile
import hashlib
import platform
import webbrowser
import zipfile
import tarfile
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
import requests
from packaging import version

from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                             QWidget, QLabel, QLineEdit, QTextEdit, QPushButton, 
                             QListWidget, QListWidgetItem, QCheckBox, QGroupBox,
                             QFileDialog, QMessageBox, QTabWidget, QSpinBox,
                             QComboBox, QProgressBar, QTreeWidget, QTreeWidgetItem,
                             QSplitter, QDialog, QDialogButtonBox, QAction, QMenu,
                             QToolBar, QStatusBar, QSystemTrayIcon, QStyle, QMenuBar,
                             QInputDialog, QFontDialog, QColorDialog, QTableWidget,
                             QTableWidgetItem, QHeaderView, QToolButton, QStackedWidget,
                             QFormLayout, QDoubleSpinBox, QSlider, QProgressDialog)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSettings, QTimer, QSize, QUrl
from PyQt5.QtGui import (QFont, QIcon, QPixmap, QKeySequence, QDesktopServices, 
                         QPalette, QColor, QTextCursor, QSyntaxHighlighter, 
                         QTextCharFormat, QTextDocument)
from PyQt5.QtPrintSupport import QPrintDialog, QPrinter


class EnhancedPackagerConfig:
    """增强的打包配置类"""
    
    def __init__(self):
        self.project_name = "MyApp"
        self.version = "1.0.0"
        self.author = ""
        self.description = ""
        self.script_path = ""
        self.icon_path = ""
        self.output_dir = ""
        self.hidden_imports = []
        self.data_files = []
        self.include_modules = []
        self.exclude_modules = []
        self.onefile = True
        self.console = False
        self.optimize = 0
        self.packager = "pyinstaller"
        self.additional_args = ""
        self.upx_enable = False
        self.upx_path = ""
        self.version_info = {}
        self.manifest_path = ""
        self.splash_screen = ""
        self.license_file = ""
        self.requirements_file = ""
        self.environment_vars = {}
        self.runtime_hooks = []
        self.hook_paths = []
        self.pathex = []
        self.no_confirm = True
        self.clean_build = True
        self.strip = True
        self.noupx = False
        self.debug = False
        self.target_arch = "auto"
        self.python_version = ""
        self.custom_spec = ""
        
    def to_dict(self):
        """转换为字典"""
        return {k: v for k, v in self.__dict__.items() if not k.startswith('_')}
    
    def from_dict(self, data):
        """从字典加载"""
        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def generate_spec_content(self):
        """生成PyInstaller spec文件内容"""
        spec_content = f"""
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['{self.script_path}'],
    pathex={self.pathex or [os.path.dirname(self.script_path)]},
    binaries=[],
    datas={self.data_files},
    hiddenimports={self.hidden_imports},
    hookspath={self.hook_paths},
    runtime_hooks={self.runtime_hooks},
    excludes={self.exclude_modules},
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive={'False' if self.onefile else 'True'}
)

{'pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)' if not self.onefile else ''}

exe = EXE(
    {'pyz,' if not self.onefile else 'a.scripts,'}
    a.binaries,
    a.zipfiles,
    a.datas,
    {'[]' if self.onefile else 'name=os.path.join("dist", "' + self.project_name + '"),'},
    debug={str(self.debug)},
    strip={str(self.strip)},
    upx={str(self.upx_enable and not self.noupx)},
    runtime_tmpdir=None,
    console={str(self.console)},
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None
)
"""
        return spec_content


class DependencyChecker:
    """依赖检查器"""
    
    @staticmethod
    def check_python_version():
        """检查Python版本"""
        return platform.python_version()
    
    @staticmethod
    def check_package_installed(package_name):
        """检查包是否安装"""
        try:
            __import__(package_name)
            return True
        except ImportError:
            return False
    
    @staticmethod
    def get_installed_packages():
        """获取已安装的包"""
        try:
            import pkg_resources
            return {pkg.key: pkg.version for pkg in pkg_resources.working_set}
        except:
            return {}


class ProjectTemplate:
    """项目模板"""
    
    def __init__(self, name, description, files):
        self.name = name
        self.description = description
        self.files = files  # Dict of {file_path: content}
    
    def create_project(self, target_dir, project_name):
        """创建项目"""
        target_path = Path(target_dir) / project_name
        target_path.mkdir(parents=True, exist_ok=True)
        
        for file_path, content in self.files.items():
            full_path = target_path / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            if callable(content):
                content = content(project_name)
            
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
        
        return str(target_path)


class TemplateManager:
    """模板管理器"""
    
    def __init__(self):
        self.templates = {}
        self.load_builtin_templates()
    
    def load_builtin_templates(self):
        """加载内置模板"""
        # PyQt5 应用模板
        pyqt_template = ProjectTemplate(
            "pyqt5_app",
            "PyQt5 桌面应用程序",
            {
                "main.py": lambda name: f'''
import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget
from PyQt5.QtCore import Qt

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("{name}")
        self.setGeometry(100, 100, 800, 600)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        label = QLabel("欢迎使用 {name}!")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
''',
                "requirements.txt": "PyQt5>=5.15.0"
            }
        )
        
        # 控制台应用模板
        console_template = ProjectTemplate(
            "console_app",
            "控制台应用程序",
            {
                "main.py": lambda name: f'''
#!/usr/bin/env python3
"""
{name} - 控制台应用程序
"""

import argparse
import sys

def main():
    parser = argparse.ArgumentParser(description="{name}")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")
    args = parser.parse_args()
    
    if args.verbose:
        print("正在运行 {name}...")
    
    print("应用程序执行完成!")

if __name__ == "__main__":
    main()
'''
            }
        )
        
        self.templates = {
            "pyqt5_app": pyqt_template,
            "console_app": console_template
        }
    
    def get_template_names(self):
        """获取模板名称列表"""
        return list(self.templates.keys())
    
    def get_template(self, name):
        """获取模板"""
        return self.templates.get(name)


class AdvancedPackagingThread(QThread):
    """增强的打包线程"""
    
    progress_signal = pyqtSignal(str, int)
    finished_signal = pyqtSignal(bool, str, str)
    log_signal = pyqtSignal(str)
    
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.output_dir = ""
        self.temp_dir = ""
    
    def run(self):
        try:
            self.progress_signal.emit("初始化打包环境...", 0)
            
            # 创建临时目录
            self.temp_dir = tempfile.mkdtemp()
            
            if self.config.packager == "pyinstaller":
                success, message, output_path = self._run_pyinstaller()
            elif self.config.packager == "cx_freeze":
                success, message, output_path = self._run_cx_freeze()
            elif self.config.packager == "nuitka":
                success, message, output_path = self._run_nuitka()
            else:
                success, message, output_path = False, f"不支持的打包工具: {self.config.packager}", ""
            
            self.finished_signal.emit(success, message, output_path)
            
        except Exception as e:
            self.finished_signal.emit(False, f"打包过程中发生错误: {str(e)}", "")
        finally:
            # 清理临时目录
            if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
    
    def _run_pyinstaller(self):
        """使用PyInstaller打包"""
        self.progress_signal.emit("准备PyInstaller命令...", 10)
        
        cmd = ["pyinstaller"]
        
        # 基本选项
        if self.config.onefile:
            cmd.append("--onefile")
        
        if not self.config.console:
            cmd.append("--windowed")
        
        if self.config.icon_path:
            cmd.extend(["--icon", self.config.icon_path])
        
        # 添加隐藏导入
        for imp in self.config.hidden_imports:
            cmd.extend(["--hidden-import", imp])
        
        # 添加数据文件
        for data in self.config.data_files:
            cmd.extend(["--add-data", data])
        
        # 添加包含模块
        for mod in self.config.include_modules:
            cmd.extend(["--include-module", mod])
        
        # 排除模块
        for mod in self.config.exclude_modules:
            cmd.extend(["--exclude-module", mod])
        
        # UPX压缩
        if self.config.upx_enable and self.config.upx_path:
            cmd.extend(["--upx-dir", self.config.upx_path])
        
        # 其他选项
        if self.config.clean_build:
            cmd.append("--clean")
        
        if self.config.strip:
            cmd.append("--strip")
        
        if self.config.noupx:
            cmd.append("--noupx")
        
        if self.config.debug:
            cmd.append("--debug")
        
        # 输出目录
        if self.config.output_dir:
            self.output_dir = self.config.output_dir
            cmd.extend(["--distpath", self.output_dir])
            cmd.extend(["--workpath", os.path.join(self.output_dir, "build")])
            cmd.extend(["--specpath", self.output_dir])
        else:
            self.output_dir = os.path.join(os.path.dirname(self.config.script_path), "dist")
        
        # 额外参数
        if self.config.additional_args:
            cmd.extend(self.config.additional_args.split())
        
        # 添加脚本路径
        cmd.append(self.config.script_path)
        
        self.progress_signal.emit(f"执行命令: {' '.join(cmd)}", 30)
        self.log_signal.emit(f"执行命令: {' '.join(cmd)}")
        
        # 执行命令
        process = subprocess.Popen(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        # 实时输出
        for line in iter(process.stdout.readline, ''):
            self.log_signal.emit(line.strip())
            self.progress_signal.emit("正在打包...", 40)
        
        process.wait()
        
        if process.returncode == 0:
            # 确定输出文件路径
            if self.config.onefile:
                exe_name = f"{self.config.project_name}.exe" if os.name == 'nt' else self.config.project_name
                output_path = os.path.join(self.output_dir, exe_name)
            else:
                output_path = os.path.join(self.output_dir, self.config.project_name)
            
            # 验证输出文件
            if os.path.exists(output_path):
                file_size = os.path.getsize(output_path)
                self.log_signal.emit(f"生成文件: {output_path} ({file_size} 字节)")
                return True, "打包成功完成!", output_path
            else:
                return False, "打包完成但未找到输出文件", ""
        else:
            return False, "打包失败", ""
    
    def _run_cx_freeze(self):
        """使用cx_Freeze打包"""
        self.progress_signal.emit("cx_Freeze打包功能待实现", 50)
        return False, "cx_Freeze打包功能尚未完全实现", ""
    
    def _run_nuitka(self):
        """使用Nuitka打包"""
        self.progress_signal.emit("Nuitka打包功能待实现", 50)
        return False, "Nuitka打包功能尚未完全实现", ""


class CodeEditor(QTextEdit):
    """简单的代码编辑器"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFont(QFont("Consolas", 10))
        self.highlighter = PythonHighlighter(self.document())
    
    def load_file(self, file_path):
        """加载文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                self.setPlainText(f.read())
            return True
        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法加载文件: {str(e)}")
            return False
    
    def save_file(self, file_path):
        """保存文件"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(self.toPlainText())
            return True
        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法保存文件: {str(e)}")
            return False


class PythonHighlighter(QSyntaxHighlighter):
    """Python语法高亮"""
    
    def __init__(self, document):
        super().__init__(document)
        
        self.highlighting_rules = []
        
        # 关键字
        keywords = [
            "and", "as", "assert", "break", "class", "continue", "def", "del",
            "elif", "else", "except", "False", "finally", "for", "from", "global",
            "if", "import", "in", "is", "lambda", "None", "nonlocal", "not", "or",
            "pass", "raise", "return", "True", "try", "while", "with", "yield"
        ]
        
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor(200, 120, 50))
        keyword_format.setFontWeight(QFont.Bold)
        
        for word in keywords:
            pattern = r"\b" + word + r"\b"
            self.highlighting_rules.append((pattern, keyword_format))
        
        # 字符串
        string_format = QTextCharFormat()
        string_format.setForeground(QColor(0, 150, 0))
        self.highlighting_rules.append((r"\"[^\"]*\"", string_format))
        self.highlighting_rules.append((r"'[^']*'", string_format))
        
        # 注释
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor(150, 150, 150))
        self.highlighting_rules.append((r"#[^\n]*", comment_format))
        
        # 数字
        number_format = QTextCharFormat()
        number_format.setForeground(QColor(100, 150, 250))
        self.highlighting_rules.append((r"\b[0-9]+\b", number_format))
    
    def highlightBlock(self, text):
        for pattern, format in self.highlighting_rules:
            expression = QtCore.QRegExp(pattern)
            index = expression.indexIn(text)
            while index >= 0:
                length = expression.matchedLength()
                self.setFormat(index, length, format)
                index = expression.indexIn(text, index + length)


class ProjectExplorer(QTreeWidget):
    """项目资源管理器"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHeaderLabel("项目文件")
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        self.itemDoubleClicked.connect(self.on_item_double_clicked)
        
        self.project_path = ""
        self.main_window = parent
    
    def load_project(self, project_path):
        """加载项目"""
        self.project_path = project_path
        self.clear()
        
        if not os.path.exists(project_path):
            return
        
        root_item = QTreeWidgetItem(self, [os.path.basename(project_path)])
        root_item.setData(0, Qt.UserRole, project_path)
        self.addTopLevelItem(root_item)
        
        self.add_directory_contents(root_item, project_path)
        self.expandItem(root_item)
    
    def add_directory_contents(self, parent_item, directory):
        """添加目录内容"""
        try:
            for item in sorted(os.listdir(directory)):
                if item.startswith('.'):
                    continue
                
                full_path = os.path.join(directory, item)
                child_item = QTreeWidgetItem(parent_item, [item])
                child_item.setData(0, Qt.UserRole, full_path)
                
                if os.path.isdir(full_path):
                    self.add_directory_contents(child_item, full_path)
                    child_item.setIcon(0, self.style().standardIcon(QStyle.SP_DirIcon))
                else:
                    child_item.setIcon(0, self.style().standardIcon(QStyle.SP_FileIcon))
        except PermissionError:
            pass
    
    def show_context_menu(self, position):
        """显示右键菜单"""
        item = self.currentItem()
        if not item:
            return
        
        menu = QMenu(self)
        
        open_action = menu.addAction("打开")
        open_action.triggered.connect(lambda: self.open_file(item))
        
        menu.addSeparator()
        
        new_file_action = menu.addAction("新建文件")
        new_file_action.triggered.connect(self.new_file)
        
        new_dir_action = menu.addAction("新建文件夹")
        new_dir_action.triggered.connect(self.new_directory)
        
        menu.addSeparator()
        
        delete_action = menu.addAction("删除")
        delete_action.triggered.connect(lambda: self.delete_item(item))
        
        menu.exec_(self.mapToGlobal(position))
    
    def on_item_double_clicked(self, item, column):
        """双击项目"""
        self.open_file(item)
    
    def open_file(self, item):
        """打开文件"""
        file_path = item.data(0, Qt.UserRole)
        if os.path.isfile(file_path):
            if hasattr(self.main_window, 'code_editor'):
                self.main_window.code_editor.load_file(file_path)
    
    def new_file(self):
        """新建文件"""
        item = self.currentItem()
        if not item:
            return
        
        path = item.data(0, Qt.UserRole)
        if os.path.isfile(path):
            path = os.path.dirname(path)
        
        file_name, ok = QInputDialog.getText(self, "新建文件", "文件名:")
        if ok and file_name:
            full_path = os.path.join(path, file_name)
            try:
                with open(full_path, 'w') as f:
                    f.write("")
                
                # 刷新树形视图
                self.load_project(self.project_path)
            except Exception as e:
                QMessageBox.critical(self, "错误", f"无法创建文件: {str(e)}")
    
    def new_directory(self):
        """新建文件夹"""
        item = self.currentItem()
        if not item:
            return
        
        path = item.data(0, Qt.UserRole)
        if os.path.isfile(path):
            path = os.path.dirpath(path)
        
        dir_name, ok = QInputDialog.getText(self, "新建文件夹", "文件夹名:")
        if ok and dir_name:
            full_path = os.path.join(path, dir_name)
            try:
                os.makedirs(full_path, exist_ok=True)
                self.load_project(self.project_path)
            except Exception as e:
                QMessageBox.critical(self, "错误", f"无法创建文件夹: {str(e)}")
    
    def delete_item(self, item):
        """删除项目"""
        path = item.data(0, Qt.UserRole)
        
        reply = QMessageBox.question(
            self, "确认删除", 
            f"确定要删除 '{os.path.basename(path)}' 吗？",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                if os.path.isfile(path):
                    os.remove(path)
                else:
                    shutil.rmtree(path)
                self.load_project(self.project_path)
            except Exception as e:
                QMessageBox.critical(self, "错误", f"无法删除: {str(e)}")


class EnhancedPackagingDialog(QDialog):
    """增强的打包进度对话框"""
    
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.packaging_thread = None
        self.output_path = ""
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("打包进度")
        self.setModal(True)
        self.resize(700, 500)
        
        layout = QVBoxLayout()
        
        # 进度标签
        self.progress_label = QLabel("准备开始打包...")
        layout.addWidget(self.progress_label)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        layout.addWidget(self.progress_bar)
        
        # 输出日志
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 9))
        layout.addWidget(self.log_text)
        
        # 按钮
        self.button_box = QDialogButtonBox()
        self.cancel_btn = self.button_box.addButton("取消", QDialogButtonBox.RejectRole)
        self.open_btn = self.button_box.addButton("打开输出目录", QDialogButtonBox.ActionRole)
        self.open_btn.setVisible(False)
        self.close_btn = self.button_box.addButton("关闭", QDialogButtonBox.AcceptRole)
        self.close_btn.setVisible(False)
        
        self.cancel_btn.clicked.connect(self.cancel_packaging)
        self.open_btn.clicked.connect(self.open_output_dir)
        self.close_btn.clicked.connect(self.accept)
        
        layout.addWidget(self.button_box)
        
        self.setLayout(layout)
    
    def start_packaging(self):
        self.packaging_thread = AdvancedPackagingThread(self.config)
        self.packaging_thread.progress_signal.connect(self.update_progress)
        self.packaging_thread.finished_signal.connect(self.packaging_finished)
        self.packaging_thread.log_signal.connect(self.update_log)
        self.packaging_thread.start()
    
    def update_progress(self, message, value):
        self.progress_label.setText(message)
        self.progress_bar.setValue(value)
    
    def update_log(self, message):
        self.log_text.append(message)
        # 自动滚动到底部
        cursor = self.log_text.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.log_text.setTextCursor(cursor)
    
    def packaging_finished(self, success, message, output_path):
        self.output_path = output_path
        
        if success:
            self.progress_bar.setValue(100)
            self.progress_label.setText("打包成功!")
            self.log_text.append(f"输出文件: {output_path}")
            
            self.cancel_btn.setVisible(False)
            self.open_btn.setVisible(True)
            self.close_btn.setVisible(True)
        else:
            self.progress_label.setText("打包失败!")
            self.log_text.append(f"错误: {message}")
            
            self.cancel_btn.setVisible(False)
            self.close_btn.setVisible(True)
    
    def cancel_packaging(self):
        if self.packaging_thread and self.packaging_thread.isRunning():
            reply = QMessageBox.question(
                self, "确认取消", 
                "确定要取消打包过程吗？",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.packaging_thread.terminate()
                self.packaging_thread.wait()
                self.reject()
    
    def open_output_dir(self):
        if self.output_path and os.path.exists(os.path.dirname(self.output_path)):
            if os.name == 'nt':
                os.startfile(os.path.dirname(self.output_path))
            elif os.name == 'posix':
                subprocess.run(['open', os.path.dirname(self.output_path)])
            elif os.name == 'mac':
                subprocess.run(['xdg-open', os.path.dirname(self.output_path)])


class EnhancedMainWindow(QMainWindow):
    """增强的主窗口"""
    
    def __init__(self):
        super().__init__()
        self.config = EnhancedPackagerConfig()
        self.settings = QSettings("PyQtPackager", "EnhancedPyQtPackager")
        self.template_manager = TemplateManager()
        self.dependency_checker = DependencyChecker()
        self.current_project_path = ""
        self.init_ui()
        self.load_settings()
    
    def init_ui(self):
        self.setWindowTitle("PyQt 可执行文件生成系统 - 增强版")
        self.setGeometry(100, 100, 1200, 800)
        
        # 创建菜单栏
        self.create_menu_bar()
        
        # 创建工具栏
        self.create_tool_bar()
        
        # 创建状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # 创建中央部件和主布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        # 左侧：项目资源管理器
        self.project_explorer = ProjectExplorer(self)
        self.project_explorer.setMaximumWidth(300)
        splitter.addWidget(self.project_explorer)
        
        # 右侧：选项卡区域
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        # 创建选项卡
        tab_widget = QTabWidget()
        right_layout.addWidget(tab_widget)
        
        # 基本设置选项卡
        basic_tab = self.create_basic_tab()
        tab_widget.addTab(basic_tab, "基本设置")
        
        # 高级设置选项卡
        advanced_tab = self.create_advanced_tab()
        tab_widget.addTab(advanced_tab, "高级设置")
        
        # 数据文件选项卡
        data_tab = self.create_data_tab()
        tab_widget.addTab(data_tab, "数据文件")
        
        # 代码编辑器选项卡
        self.code_editor = CodeEditor()
        tab_widget.addTab(self.code_editor, "代码编辑器")
        
        # 依赖管理选项卡
        deps_tab = self.create_dependencies_tab()
        tab_widget.addTab(deps_tab, "依赖管理")
        
        splitter.addWidget(right_widget)
        
        # 设置分割器比例
        splitter.setSizes([200, 1000])
        
        # 按钮区域
        button_layout = QHBoxLayout()
        
        self.save_btn = QPushButton("保存配置")
        self.load_btn = QPushButton("加载配置")
        self.package_btn = QPushButton("开始打包")
        self.test_btn = QPushButton("测试运行")
        
        self.save_btn.clicked.connect(self.save_config)
        self.load_btn.clicked.connect(self.load_config)
        self.package_btn.clicked.connect(self.start_packaging)
        self.test_btn.clicked.connect(self.test_application)
        
        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.load_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.test_btn)
        button_layout.addWidget(self.package_btn)
        
        right_layout.addLayout(button_layout)
        
        # 应用样式
        self.apply_style()
    
    def create_menu_bar(self):
        menu_bar = self.menuBar()
        
        # 文件菜单
        file_menu = menu_bar.addMenu("文件")
        
        new_project_action = QAction("新建项目", self)
        new_project_action.setShortcut("Ctrl+N")
        new_project_action.triggered.connect(self.new_project)
        file_menu.addAction(new_project_action)
        
        open_project_action = QAction("打开项目", self)
        open_project_action.setShortcut("Ctrl+O")
        open_project_action.triggered.connect(self.open_project)
        file_menu.addAction(open_project_action)
        
        file_menu.addSeparator()
        
        save_action = QAction("保存", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.save_current_file)
        file_menu.addAction(save_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("退出", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 项目菜单
        project_menu = menu_bar.addMenu("项目")
        
        build_action = QAction("构建", self)
        build_action.setShortcut("F5")
        build_action.triggered.connect(self.start_packaging)
        project_menu.addAction(build_action)
        
        run_action = QAction("运行", self)
        run_action.setShortcut("Ctrl+R")
        run_action.triggered.connect(self.test_application)
        project_menu.addAction(run_action)
        
        # 工具菜单
        tools_menu = menu_bar.addMenu("工具")
        
        check_deps_action = QAction("检查依赖", self)
        check_deps_action.triggered.connect(self.check_dependencies)
        tools_menu.addAction(check_deps_action)
        
        settings_action = QAction("设置", self)
        settings_action.triggered.connect(self.show_settings)
        tools_menu.addAction(settings_action)
        
        # 帮助菜单
        help_menu = menu_bar.addMenu("帮助")
        
        about_action = QAction("关于", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def create_tool_bar(self):
        tool_bar = QToolBar("主工具栏")
        self.addToolBar(tool_bar)
        
        new_project_btn = QAction(QIcon.fromTheme("document-new"), "新建项目", self)
        new_project_btn.triggered.connect(self.new_project)
        tool_bar.addAction(new_project_btn)
        
        open_project_btn = QAction(QIcon.fromTheme("document-open"), "打开项目", self)
        open_project_btn.triggered.connect(self.open_project)
        tool_bar.addAction(open_project_btn)
        
        tool_bar.addSeparator()
        
        save_btn = QAction(QIcon.fromTheme("document-save"), "保存", self)
        save_btn.triggered.connect(self.save_current_file)
        tool_bar.addAction(save_btn)
        
        tool_bar.addSeparator()
        
        run_btn = QAction(QIcon.fromTheme("media-playback-start"), "运行", self)
        run_btn.triggered.connect(self.test_application)
        tool_bar.addAction(run_btn)
        
        build_btn = QAction(QIcon.fromTheme("system-run"), "构建", self)
        build_btn.triggered.connect(self.start_packaging)
        tool_bar.addAction(build_btn)
    
    def create_basic_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 项目信息组
        info_group = QGroupBox("项目信息")
        info_layout = QFormLayout(info_group)
        
        self.name_edit = QLineEdit()
        self.name_edit.textChanged.connect(self.update_config)
        info_layout.addRow("项目名称:", self.name_edit)
        
        self.version_edit = QLineEdit()
        self.version_edit.textChanged.connect(self.update_config)
        info_layout.addRow("版本:", self.version_edit)
        
        self.author_edit = QLineEdit()
        self.author_edit.textChanged.connect(self.update_config)
        info_layout.addRow("作者:", self.author_edit)
        
        self.desc_edit = QLineEdit()
        self.desc_edit.textChanged.connect(self.update_config)
        info_layout.addRow("描述:", self.desc_edit)
        
        layout.addWidget(info_group)
        
        # 文件选择组
        file_group = QGroupBox("文件设置")
        file_layout = QVBoxLayout(file_group)
        
        self.script_selector = FileSelectorWidget("主脚本文件:", "Python Files (*.py)")
        file_layout.addWidget(self.script_selector)
        
        self.icon_selector = FileSelectorWidget("图标文件:", "Icon Files (*.ico *.icns)")
        file_layout.addWidget(self.icon_selector)
        
        self.output_selector = FileSelectorWidget("输出目录:", is_directory=True)
        file_layout.addWidget(self.output_selector)
        
        layout.addWidget(file_group)
        
        # 打包选项组
        options_group = QGroupBox("打包选项")
        options_layout = QVBoxLayout(options_group)
        
        self.tool_combo = QComboBox()
        self.tool_combo.addItems(["pyinstaller", "cx_freeze", "nuitka"])
        self.tool_combo.currentTextChanged.connect(self.update_config)
        options_layout.addWidget(QLabel("打包工具:"))
        options_layout.addWidget(self.tool_combo)
        
        self.onefile_check = QCheckBox("打包为单个可执行文件")
        self.onefile_check.setChecked(True)
        self.onefile_check.stateChanged.connect(self.update_config)
        options_layout.addWidget(self.onefile_check)
        
        self.console_check = QCheckBox("显示控制台窗口")
        self.console_check.stateChanged.connect(self.update_config)
        options_layout.addWidget(self.console_check)
        
        layout.addWidget(options_group)
        
        layout.addStretch()
        
        return widget
    
    def create_advanced_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 高级选项组
        advanced_group = QGroupBox("高级选项")
        advanced_layout = QFormLayout(advanced_group)
        
        self.optimize_spin = QSpinBox()
        self.optimize_spin.setRange(0, 2)
        self.optimize_spin.valueChanged.connect(self.update_config)
        advanced_layout.addRow("优化级别:", self.optimize_spin)
        
        self.upx_check = QCheckBox("使用UPX压缩")
        self.upx_check.stateChanged.connect(self.update_config)
        advanced_layout.addRow("UPX压缩:", self.upx_check)
        
        self.upx_selector = FileSelectorWidget("UPX路径:", is_directory=True)
        advanced_layout.addRow("UPX目录:", self.upx_selector)
        
        self.debug_check = QCheckBox("启用调试模式")
        self.debug_check.stateChanged.connect(self.update_config)
        advanced_layout.addRow("调试模式:", self.debug_check)
        
        self.clean_check = QCheckBox("清理构建缓存")
        self.clean_check.setChecked(True)
        self.clean_check.stateChanged.connect(self.update_config)
        advanced_layout.addRow("清理缓存:", self.clean_check)
        
        layout.addWidget(advanced_group)
        
        # 隐藏导入
        self.hidden_imports_manager = ListManagerWidget("隐藏导入", "添加模块", "移除模块")
        layout.addWidget(self.hidden_imports_manager)
        
        # 包含/排除模块
        modules_group = QGroupBox("模块设置")
        modules_layout = QHBoxLayout(modules_group)
        
        include_layout = QVBoxLayout()
        include_layout.addWidget(QLabel("包含模块:"))
        self.include_edit = QLineEdit()
        self.include_edit.setPlaceholderText("用逗号分隔的模块名")
        include_layout.addWidget(self.include_edit)
        modules_layout.addLayout(include_layout)
        
        exclude_layout = QVBoxLayout()
        exclude_layout.addWidget(QLabel("排除模块:"))
        self.exclude_edit = QLineEdit()
        self.exclude_edit.setPlaceholderText("用逗号分隔的模块名")
        exclude_layout.addWidget(self.exclude_edit)
        modules_layout.addLayout(exclude_layout)
        
        layout.addWidget(modules_group)
        
        # 额外参数
        args_group = QGroupBox("额外参数")
        args_layout = QVBoxLayout(args_group)
        self.args_edit = QLineEdit()
        self.args_edit.setPlaceholderText("额外的命令行参数")
        args_layout.addWidget(self.args_edit)
        layout.addWidget(args_group)
        
        layout.addStretch()
        return widget
    
    def create_data_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 数据文件管理器
        self.data_files_manager = ListManagerWidget("数据文件", "添加文件", "移除文件")
        layout.addWidget(self.data_files_manager)
        
        # 版本信息
        version_group = QGroupBox("版本信息")
        version_layout = QVBoxLayout(version_group)
        
        version_btn_layout = QHBoxLayout()
        self.version_edit_btn = QPushButton("编辑版本信息")
        self.version_edit_btn.clicked.connect(self.edit_version_info)
        version_btn_layout.addWidget(self.version_edit_btn)
        version_btn_layout.addStretch()
        version_layout.addLayout(version_btn_layout)
        
        self.version_text = QTextEdit()
        self.version_text.setReadOnly(True)
        self.version_text.setMaximumHeight(100)
        version_layout.addWidget(self.version_text)
        
        layout.addWidget(version_group)
        
        layout.addStretch()
        return widget
    
    def create_dependencies_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 依赖检查
        deps_group = QGroupBox("依赖检查")
        deps_layout = QVBoxLayout(deps_group)
        
        self.deps_text = QTextEdit()
        self.deps_text.setReadOnly(True)
        deps_layout.addWidget(self.deps_text)
        
        check_btn_layout = QHBoxLayout()
        self.check_deps_btn = QPushButton("检查依赖")
        self.check_deps_btn.clicked.connect(self.check_dependencies)
        check_btn_layout.addWidget(self.check_deps_btn)
        check_btn_layout.addStretch()
        deps_layout.addLayout(check_btn_layout)
        
        layout.addWidget(deps_group)
        
        # 需求文件
        req_group = QGroupBox("需求文件")
        req_layout = QVBoxLayout(req_group)
        
        self.req_selector = FileSelectorWidget("requirements.txt:", "Text Files (*.txt)")
        req_layout.addWidget(self.req_selector)
        
        req_btn_layout = QHBoxLayout()
        self.generate_req_btn = QPushButton("生成需求文件")
        self.generate_req_btn.clicked.connect(self.generate_requirements)
        req_btn_layout.addWidget(self.generate_req_btn)
        req_btn_layout.addStretch()
        req_layout.addLayout(req_btn_layout)
        
        layout.addWidget(req_group)
        
        layout.addStretch()
        return widget
    
    def apply_style(self):
        """应用样式"""
        style = """
        QMainWindow {
            background-color: #f0f0f0;
        }
        QTabWidget::pane {
            border: 1px solid #c0c0c0;
            background-color: white;
        }
        QTabBar::tab {
            background-color: #e0e0e0;
            padding: 8px 12px;
            margin-right: 2px;
        }
        QTabBar::tab:selected {
            background-color: white;
            border-bottom: 2px solid #0078d7;
        }
        QGroupBox {
            font-weight: bold;
            margin-top: 10px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px 0 5px;
        }
        QPushButton {
            background-color: #0078d7;
            color: white;
            border: none;
            padding: 5px 10px;
            border-radius: 3px;
        }
        QPushButton:hover {
            background-color: #106ebe;
        }
        QPushButton:pressed {
            background-color: #005a9e;
        }
        """
        self.setStyleSheet(style)
    
    def update_config(self):
        """更新配置对象"""
        self.config.project_name = self.name_edit.text()
        self.config.version = self.version_edit.text()
        self.config.author = self.author_edit.text()
        self.config.description = self.desc_edit.text()
        self.config.script_path = self.script_selector.get_path()
        self.config.icon_path = self.icon_selector.get_path()
        self.config.output_dir = self.output_selector.get_path()
        self.config.packager = self.tool_combo.currentText()
        self.config.onefile = self.onefile_check.isChecked()
        self.config.console = self.console_check.isChecked()
        self.config.optimize = self.optimize_spin.value()
        self.config.hidden_imports = self.hidden_imports_manager.get_items()
        self.config.data_files = self.data_files_manager.get_items()
        self.config.include_modules = [m.strip() for m in self.include_edit.text().split(',') if m.strip()]
        self.config.exclude_modules = [m.strip() for m in self.exclude_edit.text().split(',') if m.strip()]
        self.config.additional_args = self.args_edit.text()
        self.config.upx_enable = self.upx_check.isChecked()
        self.config.upx_path = self.upx_selector.get_path()
        self.config.debug = self.debug_check.isChecked()
        self.config.clean_build = self.clean_check.isChecked()
    
    def apply_config_to_ui(self):
        """将配置应用到UI"""
        self.name_edit.setText(self.config.project_name)
        self.version_edit.setText(self.config.version)
        self.author_edit.setText(self.config.author)
        self.desc_edit.setText(self.config.description)
        self.script_selector.set_path(self.config.script_path)
        self.icon_selector.set_path(self.config.icon_path)
        self.output_selector.set_path(self.config.output_dir)
        self.tool_combo.setCurrentText(self.config.packager)
        self.onefile_check.setChecked(self.config.onefile)
        self.console_check.setChecked(self.config.console)
        self.optimize_spin.setValue(self.config.optimize)
        self.hidden_imports_manager.set_items(self.config.hidden_imports)
        self.data_files_manager.set_items(self.config.data_files)
        self.include_edit.setText(','.join(self.config.include_modules))
        self.exclude_edit.setText(','.join(self.config.exclude_modules))
        self.args_edit.setText(self.config.additional_args)
        self.upx_check.setChecked(self.config.upx_enable)
        self.upx_selector.set_path(self.config.upx_path)
        self.debug_check.setChecked(self.config.debug)
        self.clean_check.setChecked(self.config.clean_build)
    
    def new_project(self):
        """新建项目"""
        template_names = self.template_manager.get_template_names()
        if not template_names:
            QMessageBox.information(self, "提示", "没有可用的项目模板")
            return
        
        template_name, ok = QInputDialog.getItem(
            self, "选择模板", "项目模板:", template_names, 0, False
        )
        
        if not ok:
            return
        
        project_name, ok = QInputDialog.getText(
            self, "新建项目", "项目名称:"
        )
        
        if not ok or not project_name:
            return
        
        project_dir = QFileDialog.getExistingDirectory(
            self, "选择项目目录"
        )
        
        if not project_dir:
            return
        
        template = self.template_manager.get_template(template_name)
        if template:
            project_path = template.create_project(project_dir, project_name)
            self.current_project_path = project_path
            self.project_explorer.load_project(project_path)
            self.status_bar.showMessage(f"已创建项目: {project_path}")
    
    def open_project(self):
        """打开项目"""
        project_dir = QFileDialog.getExistingDirectory(
            self, "选择项目目录"
        )
        
        if project_dir:
            self.current_project_path = project_dir
            self.project_explorer.load_project(project_dir)
            self.status_bar.showMessage(f"已打开项目: {project_dir}")
    
    def save_current_file(self):
        """保存当前文件"""
        if hasattr(self, 'code_editor'):
            # 这里需要实现保存当前编辑的文件
            pass
    
    def test_application(self):
        """测试运行应用程序"""
        if not self.config.script_path or not os.path.exists(self.config.script_path):
            QMessageBox.warning(self, "警告", "请先选择有效的主脚本文件!")
            return
        
        try:
            subprocess.Popen([sys.executable, self.config.script_path])
            self.status_bar.showMessage("应用程序已启动")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法启动应用程序: {str(e)}")
    
    def check_dependencies(self):
        """检查依赖"""
        python_version = self.dependency_checker.check_python_version()
        installed_packages = self.dependency_checker.get_installed_packages()
        
        report = f"Python版本: {python_version}\n\n"
        report += "已安装的包:\n"
        for pkg, ver in installed_packages.items():
            report += f"  {pkg}: {ver}\n"
        
        self.deps_text.setPlainText(report)
        self.status_bar.showMessage("依赖检查完成")
    
    def generate_requirements(self):
        """生成需求文件"""
        installed_packages = self.dependency_checker.get_installed_packages()
        
        requirements = "# 自动生成的需求文件\n"
        for pkg, ver in installed_packages.items():
            requirements += f"{pkg}=={ver}\n"
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存需求文件", "requirements.txt", "Text Files (*.txt)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w') as f:
                    f.write(requirements)
                QMessageBox.information(self, "成功", "需求文件已生成!")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"无法保存需求文件: {str(e)}")
    
    def edit_version_info(self):
        """编辑版本信息"""
        # 这里可以实现版本信息编辑器
        QMessageBox.information(self, "提示", "版本信息编辑功能待实现")
    
    def show_settings(self):
        """显示设置对话框"""
        # 这里可以实现设置对话框
        QMessageBox.information(self, "提示", "设置功能待实现")
    
    def show_about(self):
        """显示关于对话框"""
        about_text = """
        <h3>PyQt 可执行文件生成系统 - 增强版</h3>
        <p>版本: 2.0</p>
        <p>一个功能强大的Python应用程序打包工具，支持多种打包方式和高级配置选项。</p>
        <p>特性:</p>
        <ul>
            <li>支持 PyInstaller, cx_Freeze, Nuitka</li>
            <li>项目模板系统</li>
            <li>代码编辑器</li>
            <li>依赖管理</li>
            <li>高级打包选项</li>
        </ul>
        """
        QMessageBox.about(self, "关于", about_text)
    
    def save_config(self):
        """保存配置到文件"""
        self.update_config()
        
        path, _ = QFileDialog.getSaveFileName(
            self, "保存配置", f"{self.config.project_name}.json", "JSON Files (*.json)"
        )
        
        if path:
            try:
                with open(path, 'w') as f:
                    json.dump(self.config.to_dict(), f, indent=4)
                self.status_bar.showMessage("配置已保存")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"保存配置失败: {str(e)}")
    
    def load_config(self):
        """从文件加载配置"""
        path, _ = QFileDialog.getOpenFileName(self, "加载配置", "", "JSON Files (*.json)")
        
        if path:
            try:
                with open(path, 'r') as f:
                    data = json.load(f)
                
                self.config.from_dict(data)
                self.apply_config_to_ui()
                self.status_bar.showMessage("配置已加载")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"加载配置失败: {str(e)}")
    
    def start_packaging(self):
        """开始打包过程"""
        self.update_config()
        
        # 验证必要字段
        if not self.config.script_path or not os.path.exists(self.config.script_path):
            QMessageBox.warning(self, "警告", "请选择有效的主脚本文件!")
            return
        
        if not self.config.output_dir:
            QMessageBox.warning(self, "警告", "请选择输出目录!")
            return
        
        # 显示打包对话框
        dialog = EnhancedPackagingDialog(self.config, self)
        dialog.show()
        dialog.start_packaging()
        dialog.exec_()
    
    def load_settings(self):
        """加载设置"""
        self.restoreGeometry(self.settings.value("geometry", b""))
        self.restoreState(self.settings.value("windowState", b""))
    
    def closeEvent(self, event):
        """关闭事件处理"""
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("windowState", self.saveState())
        super().closeEvent(event)


# 保留之前的辅助类
class FileSelectorWidget(QWidget):
    """文件选择器组件"""
    
    def __init__(self, label, file_filter="All Files (*)", is_directory=False):
        super().__init__()
        self.is_directory = is_directory
        self.file_filter = file_filter
        self.init_ui(label)
    
    def init_ui(self, label):
        layout = QHBoxLayout()
        
        self.label = QLabel(label)
        self.path_edit = QLineEdit()
        self.browse_btn = QPushButton("浏览...")
        self.browse_btn.clicked.connect(self.browse)
        
        layout.addWidget(self.label)
        layout.addWidget(self.path_edit, 1)
        layout.addWidget(self.browse_btn)
        
        self.setLayout(layout)
    
    def browse(self):
        if self.is_directory:
            path = QFileDialog.getExistingDirectory(self, "选择目录")
        else:
            path, _ = QFileDialog.getOpenFileName(self, "选择文件", filter=self.file_filter)
        
        if path:
            self.path_edit.setText(path)
    
    def get_path(self):
        return self.path_edit.text()
    
    def set_path(self, path):
        self.path_edit.setText(path)


class ListManagerWidget(QWidget):
    """列表管理器组件"""
    
    def __init__(self, title, add_button_text="添加", remove_button_text="移除"):
        super().__init__()
        self.init_ui(title, add_button_text, remove_button_text)
    
    def init_ui(self, title, add_button_text, remove_button_text):
        layout = QVBoxLayout()
        
        title_label = QLabel(title)
        layout.addWidget(title_label)
        
        h_layout = QHBoxLayout()
        
        self.list_widget = QListWidget()
        self.add_btn = QPushButton(add_button_text)
        self.remove_btn = QPushButton(remove_button_text)
        
        self.add_btn.clicked.connect(self.add_item)
        self.remove_btn.clicked.connect(self.remove_item)
        
        button_layout = QVBoxLayout()
        button_layout.addWidget(self.add_btn)
        button_layout.addWidget(self.remove_btn)
        button_layout.addStretch()
        
        h_layout.addWidget(self.list_widget)
        h_layout.addLayout(button_layout)
        
        layout.addLayout(h_layout)
        self.setLayout(layout)
    
    def add_item(self):
        item, ok = QFileDialog.getOpenFileName(self, "选择文件")
        if ok and item:
            self.list_widget.addItem(item)
    
    def remove_item(self):
        current_row = self.list_widget.currentRow()
        if current_row >= 0:
            self.list_widget.takeItem(current_row)
    
    def get_items(self):
        return [self.list_widget.item(i).text() for i in range(self.list_widget.count())]
    
    def set_items(self, items):
        self.list_widget.clear()
        for item in items:
            self.list_widget.addItem(item)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Enhanced PyQt Packager")
    app.setApplicationVersion("2.0")
    
    # 设置应用程序样式
    app.setStyle("Fusion")
    
    window = EnhancedMainWindow()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()